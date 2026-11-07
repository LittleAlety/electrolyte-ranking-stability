from __future__ import annotations

"""Offline forensic probe: submitter budget-gate bypass holes H1-H5.

Runs entirely in-memory (temp dirs). Writes only REPORT.json and REPORT.md
to this audit directory. No bridge, no network, no cluster calls.
"""

import hashlib
import importlib.util
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
SUBMITTER = REPO / "scripts" / "wp_production" / "submit_hpc_batch.py"
NONBRIDGE = Path("E:/nonexistent/hpc.ps1")
REMOTE = "~/project/electrolyte_wp2/audit_probe_only"

sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location("submit_hpc_batch_probe", SUBMITTER)
sub = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sub)

results = []
SPAWN_ATTEMPTS = []


def _forbidden_spawn(*args, **kwargs):
    SPAWN_ATTEMPTS.append((args, kwargs))
    raise AssertionError("OFFLINE GUARD: real subprocess attempted: %r" % (args,))


def _forbidden_which(*args, **kwargs):
    SPAWN_ATTEMPTS.append(("which", args))
    raise AssertionError("OFFLINE GUARD: real pwsh lookup attempted: %r" % (args,))


sub.subprocess.run = _forbidden_spawn
sub.shutil.which = _forbidden_which


class Reply:
    def __init__(self, rc=0, out="", err=""):
        self.returncode, self.stdout, self.stderr = rc, out, err


def make_runner():
    calls = []

    def runner(argv):
        a = [str(v) for v in argv]
        calls.append(a)
        if "doctor" in a:
            return Reply(0, "bridge doctor OK (MOCK)")
        if "submit" in a:
            return Reply(0, "Submitted batch job 987654\n")
        if len(a) >= 3 and a[1] == "run" and a[2].startswith("squeue"):
            return Reply(0, "")
        return Reply(0, "")

    return runner, calls


def check(cid, ok, detail):
    results.append((cid, bool(ok), detail))
    print("%-58s %-6s %s" % (cid, "PASS" if ok else "FAIL", detail))


def refused(cid, fn, expect):
    try:
        fn()
    except expect as err:
        check(cid, True, "refused: %s" % str(err)[:110])
        return err
    check(cid, False, "NOT refused (expected %s)" % expect.__name__)
    return None


PLAIN_SCRIPT = "#!/bin/bash\n#SBATCH --job-name=audit_probe\necho probe\n"
TAMPERED_SCRIPT = "#!/bin/bash\n#SBATCH --array=0-99%2\n#SBATCH --cpus-per-task=16\n#SBATCH --time=24:00:00\n#SBATCH --mem=0\necho tampered probe\n"


def write_pkg_stream(engine, manifest_extra=None, script_text=None,
                     declared_script_sha=None, ledger=None):
    tmpdir = tempfile.mkdtemp(prefix="dsh_audit_")
    pkg = Path(tmpdir) / "hpc_four_state_p4_xtb_screening_v1"
    pkg.mkdir(parents=True, exist_ok=True)
    (pkg / "tasks").mkdir(exist_ok=True)
    for i in range(8):
        d = pkg / "tasks" / ("t%02d" % i)
        d.mkdir(exist_ok=True)
        if engine == "orca":
            (d / "job.inp").write_text("%pal nprocs 4\n! probe orca input\n", encoding="utf-8")
        else:
            (d / "job.inp").write_text("$chrg 2\n$spin 1\n$opt tight\n$end\n", encoding="utf-8")
            (d / "cores.txt").write_text("2\n", encoding="utf-8")
    listing = "\n".join("tasks/t%02d" % i for i in range(8)) + "\n"
    (pkg / "batch_1.txt").write_text(listing, encoding="utf-8", newline="\n")
    st = script_text if script_text is not None else PLAIN_SCRIPT
    (pkg / "batch_1.sbatch").write_text(st, encoding="utf-8", newline="\n")
    manifest = {
        "schema_version": 1, "package": pkg.name,
        "campaign_id": "audit_probe_only_synthetic",
        "batches": [{"batch": 1, "count": 8, "array": "0-7%2",
                     "script_sha256": declared_script_sha or hashlib.sha256(st.encode()).hexdigest(),
                     "list_sha256": hashlib.sha256(listing.encode()).hexdigest()}],
        "submission_gate": "HOLD", "submitted": False,
    }
    manifest.update(manifest_extra or {})
    (pkg / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8", newline="\n")
    if ledger is not None:
        (pkg / "attempts_ledger.json").write_text(json.dumps({"attempts": ledger}, indent=2), encoding="utf-8")
    return pkg, tmpdir


def planned_ledger():
    return [{"attempt_id": "p%02d" % i, "status": "planned", "cores": 2, "wall_hours_reserved": 2} for i in range(8)]


# C1 H2
c1, tmp1 = write_pkg_stream("orca")
try:
    runner, calls = make_runner()
    rec1 = sub.submit_batch(c1, 1, REMOTE, runner=runner, bridge=NONBRIDGE)
    submit_argv1 = calls[3]
    check("C1 h2_fallback_submits_budget_unchecked",
          rec1["status"] == "submitted" and rec1["resource_profile"] == "orca_production_v1"
          and rec1.get("budget_checked") is False and "reserved_core_hours" not in rec1
          and submit_argv1[submit_argv1.index("--cores") + 1] == "4"
          and submit_argv1[submit_argv1.index("--time") + 1] == "24:00:00",
          "status=%s profile=%s budget_checked=%s" % (rec1["status"], rec1["resource_profile"], rec1.get("budget_checked")))
    check("C1 h5_hold_manifest_still_submitted",
          json.loads((c1 / "manifest.json").read_text(encoding="utf-8"))["submission_gate"] == "HOLD"
          and json.loads((c1 / "submission_journal.json").read_text(encoding="utf-8"))["submissions"][-1]["status"] == "submitted",
          "manifest holds HOLD yet journal status=submitted")
finally:
    shutil.rmtree(tmp1, ignore_errors=True)

# C2 H2
c2, tmp2 = write_pkg_stream("xtb")
try:
    runner2, calls2 = make_runner()
    try:
        sub.submit_batch(c2, 1, REMOTE, runner=runner2, bridge=NONBRIDGE)
    except ValueError as e:
        err2 = str(e)
    shape_ok = (len(calls2) == 4 and calls2[0][1:] == ["doctor"]
                and calls2[1][1:] == ["run", "mkdir %s" % sub.REMOTE_SUBMISSION_LOCK]
                and calls2[2][1:] == ["run", "squeue -h -u pengqihang -o %i"]
                and calls2[3][1:] == ["run", "rmdir %s" % sub.REMOTE_SUBMISSION_LOCK])
    check("C2 h2_rejected_only_after_3_bridge_calls",
          err2 is not None and "pal nprocs" in err2 and shape_ok,
          "refused: %s | bridge calls: %s" % (err2[:70], [c[1:3] for c in calls2]))
finally:
    shutil.rmtree(tmp2, ignore_errors=True)

# C3 H3
c3, tmp3 = write_pkg_stream("xtb",
                            manifest_extra={"resource_profile": "xtb_screening_v1"},
                            script_text=TAMPERED_SCRIPT,
                            declared_script_sha=hashlib.sha256(PLAIN_SCRIPT.encode()).hexdigest(),
                            ledger=planned_ledger())
try:
    runner3, calls3 = make_runner()
    rec3 = sub.submit_batch(c3, 1, REMOTE, runner=runner3, bridge=NONBRIDGE, attempts_ledger=planned_ledger())
    submit_argv3 = calls3[3]
    tampered_sha = hashlib.sha256(TAMPERED_SCRIPT.encode()).hexdigest()
    declared_sha = hashlib.sha256(PLAIN_SCRIPT.encode()).hexdigest()
    check("C3 h3_tampered_sbatch_budget_checked_true_reserved_32",
          rec3["status"] == "submitted" and rec3["budget_checked"] is True
          and rec3["reserved_core_hours"] == "32" and rec3["committed_core_hours"] == "0"
          and rec3["batch_script_sha256"] == tampered_sha and declared_sha != tampered_sha
          and "--array=0-99%2" in (c3 / "batch_1.sbatch").read_text(encoding="utf-8")
          and submit_argv3[submit_argv3.index("--cores") + 1] == "2"
          and submit_argv3[submit_argv3.index("--time") + 1] == "02:00:00",
          "sha_rec=%s sha_decl=%s (mismatch unnoticed)" % (rec3["batch_script_sha256"][:12], declared_sha[:12]))
finally:
    shutil.rmtree(tmp3, ignore_errors=True)

# C4 H4
c4, tmp4 = write_pkg_stream("xtb",
                            manifest_extra={"resource_profile": "xtb_screening_v1",
                                            "task_count": 100, "cores_per_task": 16,
                                            "wall_hours_per_task": 24,
                                            "budget_cap_core_hours": 999999},
                            ledger=planned_ledger())
try:
    runner4, calls4 = make_runner()
    err4 = refused("C4a h4_cli_cap_echoing_manifest_refused_by_profile",
                   lambda: sub.submit_batch(c4, 1, REMOTE, runner=runner4, bridge=NONBRIDGE,
                                            attempts_ledger=planned_ledger(), budget_cap_core_hours="999999"), ValueError)
    check("C4a h4_refusal_precedes_any_bridge_call",
          len(calls4) == 0 and err4 is not None and "disagrees" in str(err4) and "32" in str(err4),
          "bridge calls during refusal: %d" % len(calls4))
    runner4b, calls4b = make_runner()
    rec4 = sub.submit_batch(c4, 1, REMOTE, runner=runner4b, bridge=NONBRIDGE, attempts_ledger=planned_ledger())
    manifest4 = json.loads((c4 / "manifest.json").read_text(encoding="utf-8"))
    check("C4b h4_manifest_numbers_ignored_profile_wins",
          rec4["status"] == "submitted" and rec4["resource_profile"] == "xtb_screening_v1"
          and rec4["declared_task_cores"] == 2 and rec4["allocated_wall_hours"] == 2
          and rec4["cap_core_hours"] == "32" and rec4["reserved_core_hours"] == "32"
          and manifest4["task_count"] == 100 and manifest4["cores_per_task"] == 16,
          "profile 2x2, cap 32, res=%s (manifest 100/16/999999 ignored)" % rec4["reserved_core_hours"])
finally:
    shutil.rmtree(tmp4, ignore_errors=True)

# C5-C7 H1
h1_attempt = {"status": "completed", "cores": 2, "wall_hours_reserved": 2, "slurm_allocation_id": "9001", "attempt_id": "h1_leg"}
refused("C5 h1_honest_over_cap_refused",
        lambda: sub.budget_headroom([h1_attempt], cap="32", cores=2, wall_hours=2, task_count=8), ValueError)
r6 = sub.budget_headroom([dict(h1_attempt, measured_core_hours="0")], cap="32", cores=2, wall_hours=2, task_count=8)
check("C6 h1_measured_zero_passes",
      r6["committed_core_hours"] == "0",
      "committed=%s reserved=%s cap=%s remaining=%s (measured_core_hours=0 accepted -> bill zeroed)" % (r6["committed_core_hours"], r6["reserved_core_hours"], r6["cap_core_hours"], r6["remaining_after_core_hours"]))
r7 = sub.budget_headroom([dict(h1_attempt, status="planned", measured_core_hours="20")], cap="32", cores=2, wall_hours=2, task_count=8)
check("C7 h1_planned_flip_passes",
      r7["committed_core_hours"] == "0",
      "committed=%s reserved=%s cap=%s remaining=%s (completed relabeled planned -> excluded from bill)" % (r7["committed_core_hours"], r7["reserved_core_hours"], r7["cap_core_hours"], r7["remaining_after_core_hours"]))

# C8 H5
src = SUBMITTER.read_text(encoding="utf-8")
check("C8 h5_source_never_reads_gate_fields",
      "submission_gate" not in src and 'manifest.get("batches"' in src and 'manifest.get("resource_profile"' in src and src.count("manifest.get(") == 2,
      "only batches + resource_profile read from manifest")

# C9
check("C9 bridge_never_reached", not SPAWN_ATTEMPTS, "real subprocess/which attempts: %d" % len(SPAWN_ATTEMPTS))

failed = [cid for cid, ok, _ in results if not ok]
report = {
    "checks": [(cid, ok, detail) for cid, ok, detail in results],
    "failed": failed,
    "summary": {"total": len(results), "pass": len(results) - len(failed), "fail": len(failed)},
    "bridge_never_reached": not SPAWN_ATTEMPTS,
}
(HERE / "REPORT.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")

md = []
md.append("# Submit-bypass Offline Audit Report")
md.append("")
md.append("**Project state**: submission_gate=HOLD, submitted=false. NO compute authorization.")
md.append("**Status**: `bridge_never_reached` — no real bridge spawn occurred.")
md.append("")
md.append("| Hole | Confidence | Conclusion |")
md.append("|------|------------|------------|")
md.append("| H1 | high | attempts ledger is caller-supplied; `measured_core_hours=0` or status flipped to `planned` bypasses invariant |")
md.append("| H2 | critical | missing `resource_profile` → silent fallback to `orca_production_v1` (cap 800, ledger not required); budget unchecked; `budget_checked=false` |")
md.append("| H3 | critical | tampered sbatch scripts accepted; `#SBATCH` directives not parsed; `script_sha256` never cross-checked against hash |")
md.append("| H4 | medium | manifest numbers (`task_count/cores_per_task/wall_hours_per_task/budget_cap_core_hours`) ignored; profile+allocation win |")
md.append("| H5 | high | source never reads `submission_gate`/`submitted` (only `batches`, `resource_profile`); fields cosmetic |")
md.append("")
md.append("### Check summary")
md.append("Pass: %d / Fail: %d" % (report["summary"]["pass"], report["summary"]["fail"]))
md.append("")
md.append("### Details (commands/exit/bridge)")
for cid, ok, detail in results:
    md.append("- [%s] %s: %s" % ("X" if ok else " ", cid, detail))
md.append("")
md.append("## Uncovered items")
md.append("- Full sacct→measured audit loop (requires live cluster; offline-infeasible)")
md.append("- End-to-end submission path after lock/squeue beyond refusal points (gate is before cluster)")
md.append("")
md.append("## Line-level notes (submit_hpc_batch.py)")
md.append("- Fallback: `submission_resources()` lines ~116-130 reads `resource_profile` else `DEFAULT_RESOURCE_PROFILE=\"orca_production_v1\"`; `RESOURCE_PROFILES` defined ~24-34")
md.append("- Budget: `budget_headroom()` ~275-288 calls `committed_core_hours()` ~250-272; terminal requires `slurm_allocation_id` + `measured_core_hours`, else ValueError; planned/rejected/superseded_unsubmitted excluded")
md.append("- Bridge order (C2): doctor→mkdir lock→squeue→rmdir lock; rejection at `declared_task_cores` (~199-247) happens after 3 bridge calls")
md.append("- Hashes: `batch_script_sha256`/`batch_list_sha256`/`manifest_sha256` recorded (~366-368) but never verified against declared values; no sbatch parsing")
md.append("- Gate: `submission_gate`/`submitted` not referenced anywhere in submitter source (H5)")
md.append("")
md.append("## Artifacts")
md.append("- `probe_offline.py` (this run)")
md.append("- `REPORT.json`")
md.append("- `probe_output_leadrecapture.txt` (reference from earlier run)")
md.append("")
(HERE / "REPORT.md").write_text("\n".join(md) + "\n", encoding="utf-8", newline="\n")

print("\n== SUMMARY: %d checks, %d pass, %d fail ==" % (len(results), len(results)-len(failed), len(failed)))
for c in failed:
    print("  FAIL %s" % c)
sys.exit(1 if failed else 0)
