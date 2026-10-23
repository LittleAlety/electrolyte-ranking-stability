"""G0: the formal overall gate must consume the itemised strict evidence.

Measured gap (independent review, 2026-10-22): ``strict_readiness_wiring`` could
be made to pass on broken evidence, and it was NOT wired into
``build_plan_compliance``'s ``plan_overall_complete`` -- so the project's formal
verdict rested on a loose checker plus one boolean.

These tests pin the wiring itself (the artifact, not a mock):

* the compliance table carries a ``strict_readiness_evidence`` item;
* the overall gate can never be ``satisfied`` while that item is unsatisfied;
* the item names WHICH checks failed, so the report says what is missing;
* the trigger booleans are derived, never constants.
"""
import csv
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
COMPLIANCE = (REPO / "outputs" / "physics_completion" / "compliance"
              / "plan_compliance.csv")
COMPLIANCE_SRC = REPO / "scripts" / "wp_production" / "build_plan_compliance.py"
WIRING_SRC = REPO / "scripts" / "wp_production" / "strict_readiness_wiring.py"


def _rows():
    return list(csv.DictReader(COMPLIANCE.open(encoding="utf-8")))


def _item(item_id):
    return next(r for r in _rows() if r["item_id"] == item_id)


def test_compliance_table_carries_the_strict_evidence_item():
    row = _item("strict_readiness_evidence")
    assert row["status"] in ("satisfied", "partial", "not_satisfied",
                             "blocked_on_production", "exempt")
    assert "checks_passed=" in row["measured"]
    assert "wp6_trigger=" in row["measured"]
    assert "pool_extension_trigger=" in row["measured"]


def test_overall_gate_cannot_be_satisfied_while_strict_evidence_fails():
    """The whole point of G0: no green overall verdict behind a loose checker."""
    strict = _item("strict_readiness_evidence")
    overall = _item("plan_overall_complete")
    if strict["status"] != "satisfied":
        assert overall["status"] != "satisfied"


def test_failed_check_names_are_listed():
    row = _item("strict_readiness_evidence")
    if row["status"] != "satisfied":
        # measured must name the failures, and the note must say why they fail
        failed = row["measured"].split("failed=", 1)[1].split(";", 1)[0].strip()
        assert failed and failed != "none"
        for flag in failed.split(","):
            assert flag in row["note"], flag


def test_overall_gate_consumes_the_strict_item():
    src = COMPLIANCE_SRC.read_text(encoding="utf-8")
    assert "strict_readiness_evidence" in src
    # the boolean must be part of the conjunction, not merely reported nearby
    assert "and strict_evidence_ok" in src
    assert "from strict_readiness_wiring import" in src


def test_trigger_booleans_are_derived_in_the_wiring():
    src = WIRING_SRC.read_text(encoding="utf-8")
    assert 'checks["wp6_triggered"] = False' not in src
    assert 'checks["pool_extension_triggered"] = False' not in src
    assert "def derive_wp6_trigger(" in src
    assert "def derive_pool_extension_trigger(" in src


def test_wp6_item_reports_a_derived_trigger_state():
    """WP6 is optional before its gate; after it fires the item must say so."""
    row = _item("wp6_explicit_ligand")
    assert "trigger_state=" in row["measured"]
    state = row["measured"].split("trigger_state=", 1)[1].split()[0]
    assert state in ("unknown", "not_triggered", "triggered")
    if state == "unknown":
        # cannot tell must block, never read as "has not fired"
        assert row["status"] == "not_satisfied"