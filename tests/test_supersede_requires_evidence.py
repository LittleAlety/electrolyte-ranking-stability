"""A planned follow-up must never demote completed failure evidence.

The plan is explicit: "历史失败保留原状态" -- a historical failure keeps its
recorded status.  The supersede pass used to look only at attempt ORDER, so a
pending row for a queued remedial package rewrote a finished
``technical_complete_qc_failed`` row into ``superseded`` before the remedy had
produced anything.  That erased the failure's own status from the ledger and
made "did this leg fail?" unanswerable from the table.

These tests pin the corrected contract: only an attempt that ACTUALLY RAN (it
has a ``log_sha256``) may supersede an earlier one.
"""
import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
IMP = REPO / "scripts" / "wp_production" / "import_ensemble_structures.py"
ENS = REPO / "outputs" / "physics_completion" / "ensembles"


def _m():
    spec = importlib.util.spec_from_file_location("imp_supersede", IMP)
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(IMP.parent))
    spec.loader.exec_module(mod)
    return mod


def test_source_requires_evidence_for_supersede():
    """The guard must be present in the source (it is the actual fix)."""
    src = IMP.read_text(encoding="utf-8")
    assert 'with_evidence = [r for r in member_rows if r.get("log_sha256")]' in src
    assert "if len(with_evidence) < 2:" in src


def test_completed_failures_keep_their_status_in_the_live_table():
    import csv
    path = ENS / "production_ensemble_structures.csv"
    if not path.is_file():
        return
    with path.open(encoding="utf-8") as fh:
        rows = [r for r in csv.DictReader(fh)
                if r.get("member_role") == "recovery_v1_start"]
    if not rows:
        return
    # every row that carries a real log and no successor result must keep the
    # failure status, never be rewritten to "superseded"
    for row in rows:
        if row.get("status") == "superseded":
            # if it IS superseded, a real later attempt must exist
            siblings = [r for r in rows if r["member_key"] == row["member_key"]
                        and r.get("log_sha256")
                        and int(r["attempt"] or 0) > int(row["attempt"] or 0)]
            assert siblings, ("%s superseded without a real successor"
                              % row["member_key"])


def test_failure_class_survives_on_pending_lineages():
    """A leg awaiting its remedy still reports WHY it failed."""
    import csv
    path = ENS / "production_ensemble_structures.csv"
    if not path.is_file():
        return
    with path.open(encoding="utf-8") as fh:
        rows = [r for r in csv.DictReader(fh)
                if r.get("member_role") == "recovery_v1_start"
                and r.get("status") == "technical_complete_qc_failed"]
    for row in rows:
        assert row.get("failure_class"), row["member_key"]
