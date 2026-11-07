"""strict_readiness: the itemised final gate (pure-function tests).

Every case is derived from the plan's own spec: the gate fails closed, lists
concrete reasons, treats a not-yet-triggered follow-on as non-blocking, and a
triggered-but-incomplete one as blocking.
"""
import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MOD = REPO / "scripts" / "wp_production" / "strict_readiness.py"


def _m():
    spec = importlib.util.spec_from_file_location("strict_readiness", MOD)
    m = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(MOD.parent))
    spec.loader.exec_module(m)
    return m


def _labels(pairs, status="accepted"):
    return [{"name": n, "state": s, "acceptance_status": status} for n, s in pairs]


PAIRS = [("M0", "s"), ("M1", "s")]
KEYS = {("M0", "s"), ("M1", "s")}
ALL_TRUE = {
    "coverage_reviews_valid": True,
    "identity_all_members_complete": True,
    "sampling_audit_complete": True,
    "wp3_evidence_complete": True,
    "wp5_full_target_pool_evaluated": True,
    "execution_cost_provenance_complete": True,
}


def test_complete_when_everything_checks_out():
    m = _m()
    out = m.strict_readiness(_labels(PAIRS), KEYS, dict(ALL_TRUE))
    assert out == {"complete": True, "blocked_by": []}


def test_non_accepted_state_blocks_with_reason():
    m = _m()
    labels = _labels(PAIRS)
    labels[0]["acceptance_status"] = "limited"
    out = m.strict_readiness(labels, KEYS, dict(ALL_TRUE))
    assert out["complete"] is False
    assert "ensemble_not_48_accepted" in out["blocked_by"]


def test_duplicate_or_wrong_state_set_blocks():
    m = _m()
    out = m.strict_readiness(_labels([("M0", "s"), ("M0", "s")]), KEYS, dict(ALL_TRUE))
    assert "state_set_mismatch" in out["blocked_by"]
    out = m.strict_readiness(_labels([("M0", "s"), ("OTHER", "s")]), KEYS, dict(ALL_TRUE))
    assert "state_set_mismatch" in out["blocked_by"]


def test_absent_check_is_named_and_blocks():
    """A required flag that is missing entirely reads as unsatisfied."""
    m = _m()
    checks = dict(ALL_TRUE)
    del checks["coverage_reviews_valid"]
    out = m.strict_readiness(_labels(PAIRS), KEYS, checks)
    assert "coverage_reviews_valid" in out["blocked_by"]
    assert out["complete"] is False


def test_falsy_check_is_named_and_blocks():
    m = _m()
    checks = dict(ALL_TRUE, sampling_audit_complete=False)
    out = m.strict_readiness(_labels(PAIRS), KEYS, checks)
    assert "sampling_audit_complete" in out["blocked_by"]


def test_untriggered_followons_do_not_block():
    """WP6 / pool extension only count once their precondition has fired."""
    m = _m()
    out = m.strict_readiness(_labels(PAIRS), KEYS, dict(ALL_TRUE))
    assert out["complete"] is True          # no wp6_triggered key at all


def test_triggered_but_incomplete_followon_blocks():
    m = _m()
    out = m.strict_readiness(_labels(PAIRS), KEYS, dict(ALL_TRUE, wp6_triggered=True))
    assert "wp6_incomplete" in out["blocked_by"]
    out = m.strict_readiness(_labels(PAIRS), KEYS, dict(ALL_TRUE, pool_extension_triggered=True))
    assert "pool_extension_incomplete" in out["blocked_by"]


def test_triggered_and_complete_followon_does_not_block():
    m = _m()
    out = m.strict_readiness(_labels(PAIRS), KEYS,
                             dict(ALL_TRUE, wp6_triggered=True, wp6_complete=True))
    assert out["complete"] is True
