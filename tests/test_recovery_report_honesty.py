"""The recovery report must not let a planned row stand in for a real result.

A queued remedy inserts a PENDING row at a higher attempt index.  Reporting only
the highest attempt made a batch that had already produced eight completed
failures read as "12 pending, nothing has run" -- which would have hidden the
very evidence the plan requires us to preserve.
"""
import csv
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
GEN = REPO / "scripts" / "wp_production" / "build_strict_recovery_report.py"
REPORT = REPO / "outputs" / "physics_completion" / "recovery" / "strict_recovery_v1_report.md"
STRUCTS = (REPO / "outputs" / "physics_completion" / "ensembles"
           / "production_ensemble_structures.csv")


def test_generator_separates_latest_attempt_from_last_result():
    src = GEN.read_text(encoding="utf-8")
    assert '"latest"' in src and '"result"' in src
    assert 'if r.get("log_sha256")' in src


def test_report_counts_completed_failures_not_only_pending():
    if not REPORT.is_file() or not STRUCTS.is_file():
        return
    with STRUCTS.open(encoding="utf-8") as fh:
        rows = [r for r in csv.DictReader(fh)
                if r.get("member_role") == "recovery_v1_start" and r.get("log_sha256")]
    text = REPORT.read_text(encoding="utf-8")
    if rows:
        # every completed result class must be visible in the report
        assert "technical_complete_qc_failed" in text
        # The pending bucket must NOT claim the rows were submitted: measured
        # 2026-10-24, the two pending EC rows were rejected C=O pseudo-torsions
        # that were never submitted, yet the report said "已提交".
        assert "pending 行（`status=pending`）" in text
        assert "本报告不校验它是否真的提交过" in text
        assert "在飞补救（已提交" not in text


def test_no_unescaped_pipe_in_the_detail_table():
    if not REPORT.is_file():
        return
    text = REPORT.read_text(encoding="utf-8")
    for line in text.splitlines():
        if line.startswith("| DEC") or line.startswith("| DME"):
            # a raw pipe inside a leg cell would split the row into extra cells
            assert "M|r2" not in line.replace("\\|", ""), line
