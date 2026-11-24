"""Capacity-gated, idempotent submission through the protected WHU HPC bridge.

This helper does not upload task payloads and never retries a batch.  It reads the live
Slurm queue immediately before submission, enforces the account's active+pending cap,
and writes an auditable local journal.  Scientific QC is deliberately outside its scope.
"""
from __future__ import annotations

from pathlib import Path as _ReorgPath
import sys as _reorg_sys

_reorg_sys.path.insert(0, str(_ReorgPath(__file__).resolve().parents[1]))
import _paths  # noqa: F401,E402  (仓库根 + scripts/production/* 注册到 sys.path)

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess


SUBMITTABLE_GATE_STATES = ("OPEN",)

DEFAULT_BRIDGE = Path(r"E:\软件\超算连接\hpc\hpc.ps1")
MAX_ACTIVE_PENDING = 20
CORES_PER_TASK = 4                  # project production allocation (sacct: AllocCPUS=4)
WALL_HOURS = 24
RESOURCE_PROFILES = {
    # Research-completion 2026-11-20: six fixed-geometry electronic SP, cap 6 CH total.
    "research_method_sp_4c_15m_6ch_v1": {
        "engine": "orca", "cores": 4, "wall_hours": 0.25,
        "budget_cap_core_hours": "6", "attempts_ledger_required": True},
    "orca_grid_gradient_4c_15m_v1": {
        "engine": "orca", "cores": 4, "wall_hours": 0.25,
        "budget_cap_core_hours": "3", "attempts_ledger_required": True},
    "orca_conformer_probe_4c_90m_v1": {
        "engine": "orca", "cores": 4, "wall_hours": 1.5,
        "budget_cap_core_hours": "12", "attempts_ledger_required": True},
    # Two declared Li-coordination probe validations, 4 cores x 90 min each.
    "orca_li_probe_4c_90m_v1": {
        "engine": "orca", "cores": 4, "wall_hours": 1.5,
        "budget_cap_core_hours": "12", "attempts_ledger_required": True},
    # 2026-11-01 user authorised the prepared fixed-geometry AnFreq diagnostics.
    # Three elements x 4 cores x 1 h = 12 CH; no legacy profile is changed.
    "orca_anfreq_diagnostic_4c_1h_v1": {
        "engine": "orca", "cores": 4, "wall_hours": 1,
        "budget_cap_core_hours": "12", "attempts_ledger_required": True},
    # 2026-11-01 user asked for a longer EC wall clock, then issued a standing
    # instruction that calculations carry no time limit unless they hang. This
    # 4-hour entry is kept only so already-versioned packages (3945470) keep
    # their original semantics; new EC work uses orca_ec_strict_4c_24h_v1.
    "orca_ec_strict_4c_4h_v1": {
        "engine": "orca", "cores": 4, "wall_hours": 4,
        "budget_cap_core_hours": "48", "attempts_ledger_required": True},
    # 2026-11-01 user standing instruction: "以后的计算都不加入时间限制，除非陷入卡死"
    # (no time limit on calculations unless they hang). hpxg MaxTime is 1-00:00:00,
    # so 24 h is the largest allocation the partition accepts; it is a scheduling
    # bound, not a scientific cut-off. The driver carries NO internal deadline any
    # more -- 3944659 killed both elements at its own 89-minute mark while they were
    # still converging, which is exactly the failure this removes. Budget is still
    # capped in core-hours, and unused hours are released at settlement.
    "orca_ec_strict_4c_24h_v1": {
        "engine": "orca", "cores": 4, "wall_hours": 24,
        "budget_cap_core_hours": "288", "attempts_ledger_required": True},
    # Frequency-only completion, same no-deadline policy. One element only:
    # cap 96 = 4 cores x 24 h, so this profile cannot smuggle in a second task.
    "orca_anfreq_only_4c_24h_v1": {
        "engine": "orca", "cores": 4, "wall_hours": 24,
        "budget_cap_core_hours": "96", "attempts_ledger_required": True},
    # Missing resource_profile remains the historical ORCA contract so every
    # existing, already-versioned package keeps identical submission semantics.
    "orca_production_v1": {"engine": "orca", "cores": 4, "wall_hours": 24,
                           "budget_cap_core_hours": "800",
                           "attempts_ledger_required": False},
    # 2026-10-28 EC v2 recovery专用：4核×4小时=16 CH/腿，最多2腿共32 CH。
    # 仅用于本批次EC恢复，不影响既有orca_production_v1语义。
    "orca_production_4h_v1": {"engine": "orca", "cores": 4, "wall_hours": 4,
                              "budget_cap_core_hours": "32",
                              # Execution supplement 20261029 §5.2: the EC campaign
                              # must settle from a REAL attempts ledger, never from a
                              # planning estimate.  Historical profiles keep their own
                              # semantics; only this new batch profile is tightened.
                              "attempts_ledger_required": True},
    # 2026-10-30 DMC M_plus VeryTightSCF bounded optimization：4核×4小时=16 CH。
    # 独立救援池预留，单次提交，Opt->AnFreq两阶段门控。
    "orca_dmc_vtscf_4h_v1": {"engine": "orca", "cores": 4, "wall_hours": 4,
                             "budget_cap_core_hours": "16",
                             "attempts_ledger_required": True},
    # 2026-10-30 EC forced strict-convergence experiment：4核×4小时=16 CH，单元素。
    # 独立 16 CH 授权（与 DMC M_plus 的救援额度分开登记，不可互相挪用）。
    # cap 固定为 16 而不是 32：本次授权的上限就是一条腿的最坏预留，任何
    # 第二次提交都会被 budget_headroom 直接拒绝，避免额度被静默放大。
    "orca_ec_strict_conv_4h_v1": {"engine": "orca", "cores": 4, "wall_hours": 4,
                                  "budget_cap_core_hours": "16",
                                  "attempts_ledger_required": True},
    # 2026-10-30 retry profile (user ruling: technical repair may be re-run ONCE
    # inside the SAME 16 CH EC experiment cap).  The first attempt (3895037) was a
    # protocol mismatch that still consumed 0.2244 CH, so the retry may only
    # reserve the REMAINDER: 4 cores x 3h55m = 15.6667 CH, giving 0.2244 + 15.6667
    # = 15.8911 CH against the 16 CH cap.  Wall clock is 3h55m (not 4h) precisely
    # so the two attempts together cannot exceed the authorised ceiling.
    "orca_ec_strict_conv_3h55_v1": {"engine": "orca", "cores": 4,
                                    "wall_hours": 235 / 60.0,
                                    "budget_cap_core_hours": "16",
                                    "attempts_ledger_required": True},
    # The frozen recovery plan caps the GFN2 screening layer at 2 cores/task.
    "xtb_screening_v1": {"engine": "xtb", "cores": 2, "wall_hours": 2,
                         "budget_cap_core_hours": "32",
                         "attempts_ledger_required": True},
    # 2026-10-25 ruling: the v2 screening batch is budgeted EXPLICITLY at the 4 cores
    # Slurm actually allocates.  Measured cause of the v1 mismatch: hpc.ps1:589-595
    # rewrites #SBATCH --ntasks from --cores and leaves --cpus-per-task alone, so
    # allocated = cores x cpus-per-task (v1: 2 x 2 = 4 while only 2 were budgeted).
    # v2 therefore pairs --cores 4 with a script that declares
    # `#SBATCH --ntasks=4` + `#SBATCH --cpus-per-task=1` => 4 allocated == 4 declared
    # == 4 budgeted.  Cap 16 CH = the worst case in which all four states run
    # (4 states x 4 cores x 1 h); the first submission reserves only 8 CH (DOL/EC).
    "xtb_screening_v2": {"engine": "xtb", "cores": 4, "wall_hours": 1,
                         "budget_cap_core_hours": "16",
                         "attempts_ledger_required": True},
    # 2026-10-27 H2 (single-point) profile.  Measured (not assumed): this helper does
    # NOT read the script's `#SBATCH --time` -- it REWRITES the wall clock from the
    # profile (`:424-426`) and budgets the profile's value (`budget_headroom`).  So a
    # script that says 5 minutes still reserves 4 cores x 1 h x 6 = **24 CH**, which the
    # user's 2 CH ceiling rejects.  The wall clock therefore has to live in the PROFILE:
    # 5 min/point (measured median 81 s, ~4x headroom) => 4 x (5/60) x 6 = 1.999 CH.
    # H2 runs ORCA single points, so the engine is orca while the profile stays cheap.
    "h2_single_point_v1": {"engine": "orca", "cores": 4, "wall_hours": 1 / 12.0,
                           "budget_cap_core_hours": "2",
                           "attempts_ledger_required": True},
    # 2026-10-29 DMC adjacent-step diagnostic profile.  h2_single_point_v1 caps at 2 CH,
    # but this ONE experiment is 8 elements submitted as TWO batches of 4
    # (4 x 4 cores x 5/60 h = 1.3333 CH each => 2.6667 CH worst case).  Because
    # budget_headroom() adds committed (which already counts pending/running
    # reservations) to the new reservation, batch 2 against a 2 CH cap would be
    # rejected as soon as batch 1 is in flight -- correct behaviour, wrong ceiling.
    # The ceiling therefore has to express the EXPERIMENT total, not one batch.
    # Nothing else changes: 4 cores, 5 min, real attempts ledger required.
    "h2_single_point_diagnostic_v1": {
        "engine": "orca", "cores": 4, "wall_hours": 1 / 12.0,
        # 8 elements x 4 cores x 5/60 h = 2.6667 CH; ~0.0000333 CH headroom absorbs
        # float->Decimal conversion of 1/12 (2.6666666666666665...) so the last
        # batch is not spuriously rejected when the first batch is already in-flight.
        "budget_cap_core_hours": "2.6667",
        "attempts_ledger_required": True},
    # 2026-10-27 ruling (C+D): a DEDICATED profile for the dol_ec_recovery_v1 batch.
    # The v1 contract's production wall clock is 4 h, which cannot be paired with the
    # 24 h orca_production_v1 profile; the ruling therefore authorises BOTH a batch
    # profile (C) and a versioned contract revision (D).  12 h is engineering headroom
    # over the longest observed production leg (~8 h) -- NOT a completion guarantee.
    # Cap 96 CH = the exact reservation for the authorised 2 legs (4 cores x 12 h x 2);
    # the ledger is REQUIRED so the actual spend settles from terminal sacct, never
    # from the 36.8 CH p90 planning estimate.
    "orca_production_12h_v1": {"engine": "orca", "cores": 4, "wall_hours": 12,
                               "budget_cap_core_hours": "96",
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

# EC v2 campaign: the machine contract is enforced HERE, inside the real
# submission path (not only when the package is built).  The contract module is
# loaded lazily from the same directory so this file stays importable by path
# (the tests load it with importlib and do not install the package).
EC_CAMPAIGN_PROFILE = "orca_production_4h_v1"
EC_CAMPAIGN_LEDGER_DIR = "ec_recovery_v2_campaign"
EC_CAMPAIGN_LEDGER_FILE = "campaign_ledger.json"
_EC_CONTRACT = None


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
    """The plan's invariant: committed + reserved must not exceed the cap.

    ``task_count`` is the number of ARRAY ELEMENTS in the batch.  Since 2026-10-25
    (ruling) the reserved figure is computed per array element and multiplied by
    ``fraction_of_hour``: an xtb screening array of 20 elements at 4 cores x 1 h
    would nominally be 80 CH, but the ruling budgets per JOB (state), i.e.
    2 jobs x 4 cores x 1 h = 8 CH.  When the manifest carries
    ``first_batch_reserved_core_hours``, that value is used verbatim instead of
    the per-element product -- the caller asserts it against the cap.
    """
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


def _ec_contract():
    global _EC_CONTRACT
    if _EC_CONTRACT is None:
        import importlib.util
        path = Path(__file__).with_name("ec_recovery_contract.py")
        spec = importlib.util.spec_from_file_location("_ec_recovery_contract", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _EC_CONTRACT = module
    return _EC_CONTRACT


def ec_campaign_ledger_path(package: Path) -> Path:
    """The campaign-wide ledger lives NEXT TO the package, not inside it.

    A per-package ledger would let a replacement package restart the campaign
    accounting (losing the p4 record when p7 is submitted), which is exactly what
    the contract must prevent.
    """
    return Path(package).resolve().parent / EC_CAMPAIGN_LEDGER_DIR / EC_CAMPAIGN_LEDGER_FILE


def read_ec_campaign_history(path: Path):
    """Read the campaign ledger; return normalised history plus the raw document.

    Missing file == no attempt yet (p4 may proceed).  A malformed file raises:
    an unreadable campaign state must never be read as "nothing submitted".
    """
    if not path.is_file():
        return [], None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("EC campaign ledger is unreadable: %s" % path) from exc
    entries = data.get("attempts")
    if not isinstance(entries, list):
        raise ValueError("EC campaign ledger has no attempts list: %s" % path)
    history = []
    for entry in entries:
        if not isinstance(entry, dict) or not entry.get("candidate"):
            raise ValueError("malformed EC campaign ledger entry in %s" % path)
        history.append({
            "candidate": str(entry["candidate"]),
            "submitted": bool(entry.get("submitted", False)),
            "terminal": bool(entry.get("terminal", False)),
            "accepted": entry["accepted"] if "accepted" in entry else None,
            "evidence_complete": (entry["evidence_complete"]
                                  if "evidence_complete" in entry else None),
            "geometry_sha256": entry.get("geometry_sha256"),
            "settled_core_hours": float(entry.get("settled_core_hours") or 0.0),
        })
    return history, data


def _package_candidate_identity(package: Path, listing: Path, manifest: dict):
    """Derive the candidate id and input hash from the PACKAGE, then cross-check."""
    listed = [line for line in listing.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(listed) != 1:
        raise ValueError("EC package must contain exactly one task element, got %d" % len(listed))
    task = package / listed[0]
    candidate_file = task / "candidate.json"
    geom_file = task / "geom.xyz"
    if not candidate_file.is_file() or not geom_file.is_file():
        raise ValueError("EC task is missing candidate.json/geom.xyz: %s" % task)
    try:
        candidate = json.loads(candidate_file.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("EC candidate.json is unreadable: %s" % candidate_file) from exc
    candidate_id = candidate.get("candidate_id") or candidate.get("leaf")
    if not candidate_id:
        raise ValueError("EC candidate.json does not name a candidate")
    declared_sha = candidate.get("geometry_sha256")
    actual_sha = sha256(geom_file)
    if declared_sha != actual_sha:
        raise ValueError(
            "EC input geometry hash mismatch (%s declared, %s on disk); refusing a "
            "swapped/tampered input" % (declared_sha, actual_sha))
    if manifest.get("active_candidate") not in (None, candidate_id):
        raise ValueError("EC manifest active_candidate disagrees with the task candidate")
    return candidate_id, actual_sha


def _enforce_submission_gate(manifest: dict, package: Path) -> None:
    """Generic submission gate: checks the submission_gate field BEFORE any side effect.

    This gate is independent of EC contract and runs first. It enforces that:
    - submission_gate field exists (missing field is never authorization)
    - submission_gate value is exactly "OPEN" (whitespace stripped, case-sensitive)
    - submitted field must be False (not truthy, not missing)
    """
    if "submission_gate" not in manifest:
        raise ValueError(
            "manifest declares no submission_gate (package %r); a missing field "
            "is never an authorization -- migrate the package explicitly" % package.name
        )
    gate = manifest["submission_gate"]
    if not isinstance(gate, str) or gate.strip() != gate or gate not in SUBMITTABLE_GATE_STATES:
        raise ValueError(
            "package %r is not authorized for submission (submission_gate=%r)" % (package.name, gate)
        )
    if manifest.get("submitted") is not False:
        raise ValueError(
            "manifest must declare submitted=false before submission, got %r" % (manifest.get("submitted"),)
        )


def _enforce_ec_contract(package, listing, manifest, resources, count, attempts_ledger):
    """Re-derive the campaign state and refuse an invalid EC submission.

    Runs BEFORE the bridge doctor call, the remote lock and any submission, so an
    invalid request has no side effect at all.  Everything is derived from the
    package bytes, the shared campaign ledger and the resource profile; caller
    booleans are not trusted.
    """
    contract = _ec_contract()
    if resources["name"] != EC_CAMPAIGN_PROFILE:
        # Identity is NOT selectable by the package: a package named like the EC
        # campaign must use the EC profile, otherwise switching the manifest's
        # resource_profile would silently drop every EC constraint.
        raise ValueError("EC campaign package must use profile %s, manifest says %s"
                         % (EC_CAMPAIGN_PROFILE, resources["name"]))
    if attempts_ledger is None:
        raise ValueError("EC campaign requires a real attempts ledger")
    if manifest.get("submission_gate") != "OPEN":
        raise ValueError("EC package is HOLD (submission_gate=%r); an explicit "
                         "authorization must open it before submission"
                         % manifest.get("submission_gate"))
    if manifest.get("submitted") is not False:
        raise ValueError("EC manifest must declare submitted=false, got %r"
                         % manifest.get("submitted"))
    if not manifest.get("campaign"):
        raise ValueError("EC manifest must declare its campaign id")
    if count != 1:
        raise ValueError("EC campaign submits one element at a time; batch lists %d" % count)
    candidate_id, geometry_sha = _package_candidate_identity(package, listing, manifest)
    ledger_path = ec_campaign_ledger_path(package)
    history, ledger_doc = read_ec_campaign_history(ledger_path)
    if ledger_doc is not None and manifest.get("campaign") != ledger_doc.get("campaign_id"):
        raise ValueError("EC campaign ledger belongs to a different campaign")
    submitted_count = sum(1 for e in history if e["submitted"])
    pending_count = sum(1 for e in history if e["submitted"] and not e["terminal"])
    settled = sum(e["settled_core_hours"] for e in history)
    unsettled = contract.EC_ELEMENT_CORE_HOURS * pending_count
    reserved = manifest.get("reserved_core_hours")
    if reserved is None:
        raise ValueError("EC manifest must declare reserved_core_hours")
    job_level = manifest.get("first_batch_reserved_core_hours")
    if job_level is not None and float(job_level) < contract.EC_ELEMENT_CORE_HOURS * count:
        raise ValueError("EC manifest under-reports the job-level reservation: %r < %d"
                         % (job_level, contract.EC_ELEMENT_CORE_HOURS * count))
    contract.check_campaign_contract(
        candidate=candidate_id,
        profile=resources["name"],
        cores=resources["cores"],
        wall_hours=resources["wall_hours"],
        element_count=count,
        declared_reservation_core_hours=reserved,
        settled_core_hours=settled,
        unsettled_reserved_core_hours=unsettled,
        ec_active_pending=pending_count,
        ec_submitted_elements=submitted_count,
        history=history,
    )
    for entry in history:
        if (entry["candidate"] == candidate_id and entry.get("geometry_sha256")
                and entry["geometry_sha256"] != geometry_sha):
            raise ValueError(
                "EC candidate %s geometry differs from the campaign record; refusing a "
                "swapped start" % candidate_id)
    return {"candidate": candidate_id, "geometry_sha256": geometry_sha,
            "ledger_path": ledger_path, "campaign_id": manifest.get("campaign"),
            "contract_sha256": sha256(Path(contract.__file__))}


def _append_ec_campaign_entry(session, record):
    """Record the attempt after the submit call, conservatively.

    Unknown responses (no JobID, bridge error) stay ``submitted=True`` and
    ``terminal=False``: only journal + scheduler evidence may later release the
    occupancy.  ``accepted`` is written as an explicit ``null`` (unknown), never
    ``false``, so a missing result cannot open p7.
    """
    path = Path(session["ledger_path"])
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RuntimeError("EC campaign ledger became unreadable; campaign state "
                               "unknown, refusing to continue: %s" % path) from exc
    else:
        data = {"schema_version": 1, "campaign_id": session.get("campaign_id"),
                "attempts": []}
    attempts = data.setdefault("attempts", [])
    status = str(record.get("status", "unknown"))
    attempts.append({
        "candidate": session["candidate"],
        "submitted": True,
        "terminal": False,
        "accepted": None,
        "evidence_complete": False,
        "geometry_sha256": session["geometry_sha256"],
        "job_id": record.get("job_id"),
        "state": "submitted" if status == "submitted" else "submission_unknown",
        "reserved_core_hours": _ec_contract().EC_ELEMENT_CORE_HOURS,
        "settled_core_hours": 0.0,
        "contract_sha256": session.get("contract_sha256"),
        "recorded_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    })
    temporary = path.with_name(path.name + ".tmp.%d" % os.getpid())
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                         encoding="utf-8", newline="\n")
    os.replace(temporary, path)


def _persist_attempts_ledger(attempts_ledger, attempts_ledger_path, reservation_record,
                             profile, task_count):
    """Persist THIS batch's reservation into the shared attempts ledger on disk.

    Called after a submission whose outcome we cannot prove was refused (success,
    or a response we could not parse) so the reserved capacity stays visible to
    the next batch.  Two invariants matter:

    * the status MUST be one that ``committed_core_hours`` counts as occupying
      (``pending`` / ``running`` / ``submitting``).  A terminal-looking status
      such as ``submitted`` is not recognised there and would either be ignored
      or raise for missing sacct provenance -- either way batch 2 would see a
      zero-cost batch 1 and be allowed to overrun the experiment cap.
    * the existing document's other keys are preserved; only ``attempts`` grows.
    """
    if attempts_ledger is None or attempts_ledger_path is None:
        return
    path = Path(attempts_ledger_path)
    try:
        original = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        original = {}
    document = dict(original) if isinstance(original, dict) else {}
    base = {
        # Queued-but-not-terminal: occupies the reservation, releases nothing.
        "status": "pending",
        "cores": reservation_record.get("declared_task_cores") or profile.get("cores", 4),
        "wall_hours_reserved": reservation_record.get("allocated_wall_hours",
                                                      profile.get("wall_hours")),
        "batch": reservation_record.get("batch"),
        "resource_profile": reservation_record.get("resource_profile"),
        "submission_status": reservation_record.get("status"),
        "diagnostic_only": True,
        "recorded_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    if reservation_record.get("job_id"):
        base["slurm_job_id"] = reservation_record["job_id"]
    document.setdefault("attempts", attempts_ledger)
    # Write one entry per element so ``committed_core_hours`` (which sums
    # cores * wall_hours per entry) sees the full reservation.
    for idx in range(task_count):
        entry = dict(base)
        entry["attempt_id"] = "%s__b%d_e%d" % (
            reservation_record.get("resource_profile", "batch"),
            reservation_record.get("batch", 0), idx)
        document["attempts"].append(entry)
    temporary = path.with_name(path.name + ".tmp.%d" % os.getpid())
    temporary.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n",
                         encoding="utf-8", newline="\n")
    os.replace(temporary, path)


def submit_batch(package, batch, remote_workdir, *, runner=default_runner,
                 bridge=DEFAULT_BRIDGE, user="pengqihang",
                 attempts_ledger=None, attempts_ledger_path=None, budget_cap_core_hours=None):
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

    # Generic submission gate: must run BEFORE any side effect (journal read, doctor, lock)
    # so a forbidden request never touches the remote system.
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    _enforce_submission_gate(manifest, package)

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

    # EC campaign contract: re-derived from the package bytes, the shared campaign
    # ledger and the resource profile.  Placed BEFORE doctor/lock/submit so a bad
    # request produces no side effect at all.
    ec_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    ec_identity = (resources["name"] == EC_CAMPAIGN_PROFILE
                   or package.name.startswith("hpc_ec_recovery_v2")
                   or ec_manifest.get("campaign_contract") == "ec_recovery_v2")
    ec_session = None
    if ec_identity:
        ec_session = _enforce_ec_contract(
            package, listing, ec_manifest, resources, count, attempts_ledger)

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
            from decimal import Decimal
            committed = committed_core_hours(attempts_ledger)
            # 2026-10-25 ruling: an xtb screening array is budgeted PER JOB (state),
            # not per array element.  When the manifest declares the job-level
            # reservation explicitly, honour it and check THAT against the cap;
            # otherwise fall back to the per-element product (historical ORCA
            # semantics, where one element == one job).
            job_reserved = None
            try:
                _m = json.loads(manifest_path.read_text(encoding="utf-8"))
                job_reserved = _m.get("first_batch_reserved_core_hours")
            except (OSError, ValueError):
                pass
            per_element = budget_headroom(
                attempts_ledger, cap=effective_budget_cap, cores=resources["cores"],
                wall_hours=resources["wall_hours"], task_count=count)
            if isinstance(job_reserved, (int, float)) and job_reserved > 0:
                reserved = Decimal(str(job_reserved))
            else:
                reserved = Decimal(per_element["reserved_core_hours"])
            cap = Decimal(str(effective_budget_cap))
            if committed + reserved > cap:
                raise ValueError("core-hour budget exceeded: committed %s + reserved %s > cap %s"
                                 % (committed, reserved, cap))
            budget_record = {"committed_core_hours": str(committed),
                             "reserved_core_hours": str(reserved),
                             "cap_core_hours": str(cap),
                             "remaining_after_core_hours": str(cap - committed - reserved),
                             "budget_checked": True}
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
        # fractional wall hours must survive (H2 = 5 min); "%02d:00:00" would
        # truncate 1/12 h to 00:00:00 and Slurm would kill the job instantly.
        _wh = float(resources["wall_hours"])
        _mins = int(round(_wh * 60))
        wall = "%02d:%02d:00" % (_mins // 60, _mins % 60)
        result = None
        try:
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
                _persist_attempts_ledger(attempts_ledger, attempts_ledger_path, record, resources, count)
                raise RuntimeError("HPC bridge returned success without a parseable JobID")
            record.update(status="submitted", job_id=match.group(1), bridge_exit_code=0,
                          finished_at_utc=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"))
            _write_journal(journal_path, journal)
            _persist_attempts_ledger(attempts_ledger, attempts_ledger_path, record, resources, count)
            return dict(record)
        finally:
            if ec_session is not None:
                # Conservative occupancy: any response we cannot prove was NOT
                # accepted stays submitted-but-not-terminal, occupying the slot.
                _append_ec_campaign_entry(ec_session, record)
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
                try:
                    doc = json.loads(Path(args.attempts_ledger).read_text(encoding="utf-8"))
                except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                    raise ValueError("attempts ledger is unreadable: %s"
                                     % args.attempts_ledger) from exc
                ledger = doc.get("attempts") if isinstance(doc, dict) else doc
                if ledger is None:
                    raise ValueError("attempts ledger has no 'attempts' list: %s"
                                     % args.attempts_ledger)
            result = submit_batch(args.package, args.batch, args.remote_workdir,
                                  bridge=args.bridge, user=args.user,
                                  attempts_ledger=ledger,
                                  attempts_ledger_path=args.attempts_ledger,
                                  budget_cap_core_hours=args.budget_cap_core_hours)
    except (ValueError, RuntimeError) as exc:
        print("REFUSED: %s" % exc)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
