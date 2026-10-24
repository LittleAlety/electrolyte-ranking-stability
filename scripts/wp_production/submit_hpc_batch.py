"""Capacity-gated, idempotent submission through the protected WHU HPC bridge.

This helper does not upload task payloads and never retries a batch.  It reads the live
Slurm queue immediately before submission, enforces the account's active+pending cap,
and writes an auditable local journal.  Scientific QC is deliberately outside its scope.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess


DEFAULT_BRIDGE = Path(r"E:\软件\超算连接\hpc\hpc.ps1")
MAX_ACTIVE_PENDING = 20
CORES_PER_TASK = 4                  # project production allocation (sacct: AllocCPUS=4)
WALL_HOURS = 24
RESOURCE_PROFILES = {
    # Missing resource_profile remains the historical ORCA contract so every
    # existing, already-versioned package keeps identical submission semantics.
    "orca_production_v1": {"engine": "orca", "cores": 4, "wall_hours": 24,
                           "budget_cap_core_hours": "800",
                           "attempts_ledger_required": False},
    # The frozen recovery plan caps the GFN2 screening layer at 2 cores/task.
    "xtb_screening_v1": {"engine": "xtb", "cores": 2, "wall_hours": 2,
                         "budget_cap_core_hours": "32",
                         "attempts_ledger_required": True},
}
DEFAULT_RESOURCE_PROFILE = "orca_production_v1"
ORCA_NPROCS_RE = re.compile(r"%pal\s+nprocs\s+(\d+)", re.I)
DEFAULT_BUDGET_CAP_CORE_HOURS = "800"
REMOTE_SUBMISSION_LOCK = "~/project/electrolyte_wp2/.wp2_submit.lock"
USER_RE = re.compile(r"[A-Za-z0-9_.-]+\Z")
JOB_RE = re.compile(r"\d+(?:_(?:\d+|\[[0-9,%\-]+\]))?\Z")
TERMINAL_STATES = {"COMPLETED", "FAILED", "TIMEOUT", "OUT_OF_MEMORY", "NODE_FAIL",
                   "CANCELLED", "PREEMPTED", "BOOT_FAIL", "DEADLINE", "REVOKED"}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def default_runner(argv):
    command = [str(value) for value in argv]
    if command[0].lower().endswith(".ps1"):
        shell = shutil.which("pwsh")
        if not shell:
            raise RuntimeError("PowerShell 7 (pwsh) is required by the protected HPC bridge")
        command = [shell, "-NoProfile", "-File"] + command
    return subprocess.run(command, text=True, capture_output=True, encoding="utf-8")


def _array_count(token: str) -> int:
    if "_[" not in token:
        return 1
    body = token.split("_[", 1)[1][:-1]
    body = body.split("%", 1)[0]
    total = 0
    for part in body.split(","):
        if "-" in part:
            first, last = part.split("-", 1)
            if not first.isdigit() or not last.isdigit() or int(last) < int(first):
                raise ValueError("invalid squeue array range %r" % token)
            total += int(last) - int(first) + 1
        elif part.isdigit():
            total += 1
        else:
            raise ValueError("invalid squeue array member %r" % token)
    return total


def count_squeue_jobs(output: str) -> int:
    tokens = [line.strip() for line in output.splitlines() if line.strip()]
    for token in tokens:
        if not JOB_RE.fullmatch(token):
            raise ValueError("unexpected protected-bridge squeue output: %r" % token)
    return sum(_array_count(token) for token in tokens)


def _run(runner, argv, label):
    result = runner([str(value) for value in argv])
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "no output").strip()
        raise RuntimeError("%s failed: %s" % (label, detail))
    return result.stdout


def _load_package(package: Path, batch: int):
    manifest_path = package / "manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("package manifest is missing or malformed") from exc
    matches = [row for row in manifest.get("batches", []) if row.get("batch") == batch]
    if len(matches) != 1:
        raise ValueError("manifest must contain exactly one requested batch")
    count = matches[0].get("count")
    if not isinstance(count, int) or not 1 <= count <= 20:
        raise ValueError("manifest batch count is invalid")
    script = package / ("batch_%d.sbatch" % batch)
    listing = package / ("batch_%d.txt" % batch)
    if not script.is_file() or not listing.is_file():
        raise ValueError("batch script/list is missing")
    listed = [line for line in listing.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(listed) != count:
        raise ValueError("batch list count disagrees with manifest")
    return count, script, listing, manifest_path


def submission_resources(manifest_path: Path) -> dict:
    """Resolve an immutable, manifest-declared resource profile.

    Callers cannot override this at the CLI: the resource identity travels with
    the hashed package manifest.  Unknown profiles fail closed.  Manifests from
    the pre-profile era retain the historical ORCA 4-core/24-hour allocation.
    """
    try:
        manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("package manifest is missing or malformed") from exc
    name = manifest.get("resource_profile", DEFAULT_RESOURCE_PROFILE)
    if name not in RESOURCE_PROFILES:
        raise ValueError("unknown manifest resource_profile: %r" % name)
    return {"name": name, **RESOURCE_PROFILES[name]}


def _write_journal(path: Path, payload):
    temporary = path.with_name(path.name + ".tmp.%d" % os.getpid())
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                         encoding="utf-8", newline="\n")
    os.replace(temporary, path)


def _read_evidence_map(path: Path):
    values = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or "=" not in line:
            raise ValueError("malformed scheduler_state.request")
        key, value = line.split("=", 1)
        if not re.fullmatch(r"[a-z][a-z0-9_]*", key) or key in values:
            raise ValueError("malformed or duplicate scheduler_state.request key")
        values[key] = value
    required = {"slurm_array_job_id", "slurm_array_task_id", "slurm_job_id",
                "required_for_automatic_technical_retry"}
    if set(values) != required or values["required_for_automatic_technical_retry"] != "true":
        raise ValueError("scheduler_state.request contract mismatch")
    if not all(re.fullmatch(r"\d+(?:_\d+)?", values[key])
               for key in ("slurm_array_job_id", "slurm_array_task_id", "slurm_job_id")):
        raise ValueError("scheduler_state.request has invalid Slurm IDs")
    return values


def collect_sacct(attempt_dir, *, runner=default_runner, bridge=DEFAULT_BRIDGE):
    """Collect terminal scheduler evidence through the bridge; never run Python remotely."""
    attempt_dir = Path(attempt_dir)
    target = attempt_dir / "sacct.terminal"
    if target.exists():
        raise ValueError("sacct.terminal already exists; refusing to overwrite immutable evidence")
    request = _read_evidence_map(attempt_dir / "scheduler_state.request")
    bridge = Path(bridge)
    _run(runner, [bridge, "doctor"], "HPC bridge doctor")
    job_id = request["slurm_job_id"]
    output = _run(runner, [bridge, "run",
                           "sacct -n -X -j %s -o JobIDRaw,State,ExitCode -P" % job_id],
                  "terminal sacct query")
    rows = []
    for line in output.splitlines():
        if not line.strip():
            continue
        parts = line.strip().split("|")
        if len(parts) != 3:
            raise ValueError("unexpected sacct output row: %r" % line)
        if parts[0] == job_id:
            rows.append(parts)
    if len(rows) != 1:
        raise ValueError("sacct must return exactly one row for job %s" % job_id)
    _, state, exit_code = rows[0]
    state = state.rstrip("+")
    if state not in TERMINAL_STATES:
        raise ValueError("sacct job is not in a recognized terminal state: %s" % state)
    if not re.fullmatch(r"\d+:\d+", exit_code):
        raise ValueError("sacct ExitCode is malformed")
    collected = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    lines = ["source=sacct", "slurm_array_job_id=" + request["slurm_array_job_id"],
             "slurm_array_task_id=" + request["slurm_array_task_id"],
             "slurm_job_id=" + job_id, "state=" + state, "exit_code=" + exit_code,
             "collected_at_utc=" + collected]
    with target.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(lines) + "\n")
    return {"state": state, "exit_code": exit_code, "path": str(target)}


def declared_task_cores(package: Path, listing, *, engine=None) -> int:
    """The core count every task's ORCA input declares (``%pal nprocs N``).

    ``listing`` may be the batch list FILE (what ``_load_package`` returns) or an
    iterable of task relpaths -- measured: assuming a list raises
    "TypeError: 'WindowsPath' object is not iterable".

    Plan P4 requires "输入核数与 allocation 一致".  Submitting a task whose input
    declares a different core count silently changes the resource the run uses, so
    a mismatch (or a missing declaration, or inconsistent tasks) is refused.
    """
    package = Path(package)
    if isinstance(listing, (str, Path)):
        listing = [line for line in Path(listing).read_text(encoding="utf-8").splitlines()
                   if line.strip()]
    cores = set()
    for rel in listing:
        inp = package / rel / "job.inp"
        if not inp.is_file():
            raise ValueError("task input missing: %s/job.inp" % rel)
        text = inp.read_text(encoding="utf-8")
        match = ORCA_NPROCS_RE.search(text)
        if engine == "xtb" and match is not None:
            raise ValueError("xtB resource profile refuses ORCA %%pal input: %s" % rel)
        if engine == "xtb" and not (re.search(r"(?im)^\s*\$chrg\b", text)
                                     and re.search(r"(?im)^\s*\$spin\b", text)):
            raise ValueError("xtB task input lacks $chrg/$spin contract: %s" % rel)
        if match is not None:
            cores.add(int(match.group(1)))
            continue
        # Non-ORCA engines (an xtB/GFN2 screening package) have no %pal block, so
        # they must declare their core count explicitly instead.  Fail closed:
        # without a declaration the resource is unknown.
        declared = package / rel / "cores.txt"
        if engine == "orca":
            raise ValueError("ORCA resource profile requires %%pal nprocs: %s" % rel)
        if declared.is_file():
            value = declared.read_text(encoding="utf-8").strip()
            if not value.isdigit() or int(value) < 1:
                raise ValueError("invalid cores.txt for %s" % rel)
            cores.add(int(value))
            continue
        raise ValueError("task declares no core count (no %%pal nprocs and no "
                         "cores.txt): %s" % rel)
    if not cores:
        raise ValueError("batch listing is empty; nothing to submit")
    if len(cores) != 1:
        raise ValueError("tasks declare inconsistent %%pal nprocs: %s" % sorted(cores))
    return cores.pop()


def committed_core_hours(attempts) -> "Decimal":
    """Committed + in-flight core-hours, deduplicated by Slurm allocation."""
    from decimal import Decimal
    seen = set()
    total = Decimal("0")
    for a in attempts or []:
        status = str(a.get("status", ""))
        if status in ("planned", "rejected", "superseded_unsubmitted"):
            continue
        if status in ("pending", "running", "submitting"):
            # an unfinished attempt cannot release the remainder of its allocation
            total += Decimal(str(a["cores"])) * Decimal(str(a["wall_hours_reserved"]))
            continue
        allocation = a.get("slurm_allocation_id")
        measured = a.get("measured_core_hours")
        if not allocation or measured is None:
            raise ValueError("terminal cost provenance missing: %s"
                             % a.get("attempt_id", "<unknown attempt>"))
        if allocation in seen:
            continue                 # a shared job must not be billed per leg
        seen.add(allocation)
        total += Decimal(str(measured))
    return total


def budget_headroom(attempts, *, cap, cores, wall_hours, task_count) -> dict:
    """The plan's invariant: committed + reserved must not exceed the cap."""
    from decimal import Decimal
    reserved = (Decimal(str(cores)) * Decimal(str(wall_hours))
                * Decimal(str(task_count)))
    committed = committed_core_hours(attempts)
    cap = Decimal(str(cap))
    if committed + reserved > cap:
        raise ValueError("core-hour budget exceeded: committed %s + reserved %s > cap %s"
                         % (committed, reserved, cap))
    return {"committed_core_hours": str(committed), "reserved_core_hours": str(reserved),
            "cap_core_hours": str(cap),
            "remaining_after_core_hours": str(cap - committed - reserved)}


def submit_batch(package, batch, remote_workdir, *, runner=default_runner,
                 bridge=DEFAULT_BRIDGE, user="pengqihang",
                 attempts_ledger=None, budget_cap_core_hours=None):
    package = Path(package).resolve()
    bridge = Path(bridge)
    if not USER_RE.fullmatch(user):
        raise ValueError("invalid HPC user")
    if not remote_workdir or any(ch in remote_workdir for ch in "\r\n"):
        raise ValueError("invalid remote workdir")
    count, script, listing, manifest_path = _load_package(package, batch)
    resources = submission_resources(manifest_path)
    profile_cap = resources["budget_cap_core_hours"]
    if budget_cap_core_hours is not None and str(budget_cap_core_hours) != profile_cap:
        raise ValueError("CLI budget cap %s disagrees with manifest resource profile cap %s"
                         % (budget_cap_core_hours, profile_cap))
    effective_budget_cap = profile_cap
    if resources["attempts_ledger_required"] and attempts_ledger is None:
        raise ValueError("resource profile %s requires an attempts ledger"
                         % resources["name"])
    journal_path = package / "submission_journal.json"
    reservation_path = package / (".batch_%d.submission.lock" % batch)
    if journal_path.exists():
        journal = json.loads(journal_path.read_text(encoding="utf-8"))
    else:
        journal = {"schema_version": 1, "submissions": []}
    previous = [row for row in journal.get("submissions", []) if row.get("batch") == batch]
    if previous:
        status = previous[-1].get("status")
        wording = "already submitted" if status == "submitted" else "already attempted"
        raise ValueError("batch %d was %s; refusing duplicate submission" % (batch, wording))
    if reservation_path.exists():
        raise ValueError("batch %d already has a submission reservation; refusing duplicate"
                         % batch)

    _run(runner, [bridge, "doctor"], "HPC bridge doctor")
    acquire = runner([str(bridge), "run", "mkdir %s" % REMOTE_SUBMISSION_LOCK])
    if acquire.returncode != 0:
        detail = (acquire.stderr or acquire.stdout or "lock already exists").strip()
        raise RuntimeError("account-wide remote submission lock unavailable; stale/concurrent "
                           "lock must be inspected, never deleted automatically: %s (%s)"
                           % (REMOTE_SUBMISSION_LOCK, detail))
    record = None
    try:
        queue_output = _run(
            runner, [bridge, "run", "squeue -h -u %s -o %%i" % user], "live squeue query")
        active_pending = count_squeue_jobs(queue_output)
        headroom = MAX_ACTIVE_PENDING - active_pending
        if count > headroom:
            raise ValueError("batch count %d exceeds live headroom %d under the <=20 cap"
                             % (count, headroom))

        # the input's declared core count must match what we allocate
        declared_cores = declared_task_cores(package, listing, engine=resources["engine"])
        if declared_cores != resources["cores"]:
            raise ValueError(
                "task inputs declare %d cores but the protected submitter allocates %d; "
                "refusing to silently change the resource (version the submitter instead)"
                % (declared_cores, resources["cores"]))

        budget_record = {"budget_checked": False}
        if attempts_ledger is not None:
            budget_record = budget_headroom(
                attempts_ledger, cap=effective_budget_cap, cores=resources["cores"],
                wall_hours=resources["wall_hours"], task_count=count)
            budget_record["budget_checked"] = True
        else:
            print("NOTE: no --attempts-ledger given; the core-hour budget invariant "
                  "was NOT checked for this submission")

        record = {
            "batch": batch, "batch_count": count, "observed_active_pending": active_pending,
            "resource_profile": resources["name"], "resource_engine": resources["engine"],
            "declared_task_cores": declared_cores,
            "allocated_wall_hours": resources["wall_hours"], **budget_record,
            "headroom_before_submit": headroom, "remote_workdir": remote_workdir,
            "remote_submission_lock": REMOTE_SUBMISSION_LOCK,
            "batch_script_sha256": sha256(script), "batch_list_sha256": sha256(listing),
            "manifest_sha256": sha256(manifest_path),
            "started_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "status": "submitting",
        }
        try:
            with reservation_path.open("x", encoding="utf-8", newline="\n") as handle:
                handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
        except FileExistsError as exc:
            raise ValueError("batch %d was already attempted by another submission process"
                             % batch) from exc
        journal["submissions"].append(record)
        _write_journal(journal_path, journal)
        wall = "%02d:00:00" % resources["wall_hours"]
        result = runner([str(bridge), "submit", str(script), "--cores",
                         str(resources["cores"]), "--time", wall,
                         "--workdir", remote_workdir])
        combined = "\n".join(part for part in (result.stdout, result.stderr) if part)
        if result.returncode != 0:
            record.update(status="submit_failed", bridge_exit_code=result.returncode,
                          finished_at_utc=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                          bridge_message=combined.strip())
            _write_journal(journal_path, journal)
            raise RuntimeError("HPC bridge submit failed: %s" % (combined.strip() or "no output"))
        match = re.search(r"(?:JobID\s*=|Submitted batch job)\s*(\d+)", combined)
        if not match:
            record.update(status="submit_result_unparseable", bridge_exit_code=0,
                          finished_at_utc=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                          bridge_message=combined.strip())
            _write_journal(journal_path, journal)
            raise RuntimeError("HPC bridge returned success without a parseable JobID")
        record.update(status="submitted", job_id=match.group(1), bridge_exit_code=0,
                      finished_at_utc=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"))
        _write_journal(journal_path, journal)
        return dict(record)
    finally:
        release = runner([str(bridge), "run", "rmdir %s" % REMOTE_SUBMISSION_LOCK])
        if release.returncode != 0:
            if record is not None and journal_path.exists():
                record["remote_lock_release"] = "failed"
                record["remote_lock_release_message"] = (release.stderr or release.stdout).strip()
                _write_journal(journal_path, journal)
            raise RuntimeError("account-wide remote submission lock release failed; inspect %s"
                               % REMOTE_SUBMISSION_LOCK)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", type=Path, nargs="?")
    parser.add_argument("--batch", type=int)
    parser.add_argument("--remote-workdir")
    parser.add_argument("--collect-sacct", type=Path, metavar="ATTEMPT_DIR")
    parser.add_argument("--attempts-ledger", type=Path, metavar="JSON",
                        help="attempt ledger; enables the core-hour budget invariant")
    parser.add_argument("--budget-cap-core-hours",
                        help="optional assertion; must equal the manifest profile's hard cap")
    parser.add_argument("--bridge", type=Path, default=DEFAULT_BRIDGE)
    parser.add_argument("--user", default="pengqihang")
    args = parser.parse_args(argv)
    try:
        if args.collect_sacct:
            if args.package is not None or args.batch is not None or args.remote_workdir is not None:
                raise ValueError("--collect-sacct cannot be combined with submission arguments")
            result = collect_sacct(args.collect_sacct, bridge=args.bridge)
        else:
            if args.package is None or args.batch is None or args.remote_workdir is None:
                raise ValueError("submission requires package, --batch, and --remote-workdir")
            ledger = None
            if args.attempts_ledger is not None:
                doc = json.loads(Path(args.attempts_ledger).read_text(encoding="utf-8"))
                ledger = doc.get("attempts") if isinstance(doc, dict) else doc
                if ledger is None:
                    raise ValueError("attempts ledger has no 'attempts' list: %s"
                                     % args.attempts_ledger)
            result = submit_batch(args.package, args.batch, args.remote_workdir,
                                  bridge=args.bridge, user=args.user,
                                  attempts_ledger=ledger,
                                  budget_cap_core_hours=args.budget_cap_core_hours)
    except (ValueError, RuntimeError) as exc:
        print("REFUSED: %s" % exc)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
