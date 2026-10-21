"""The limited->accepted decision as a pure function (plan item ②).

The coverage-review mechanism is the ONLY sanctioned path out of `limited`.
These tests exercise it directly, including the exact scenario the running
strict_recovery_v1 batch will produce for DEC/M:

    DEC|M has one historical QC-failed member (n_limited = 1);
    a new independent minimum DEC|M|r2_c23 is computed and survives dedup;
    the coverage review certifies it -> the state may become accepted.

and the anti-cheat cases that must NOT upgrade.
"""
import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
AGG = REPO / "scripts" / "wp_production" / "build_production_ensemble_aggregator.py"


def _m():
    spec = importlib.util.spec_from_file_location("agg_acceptance", AGG)
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(AGG.parent))
    spec.loader.exec_module(mod)
    return mod


def _cov(verdict="resolved", members="DEC|M|r2_c23"):
    return {"review_id": "coverage_review_v1|strict_recovery_v1|DEC|M",
            "verdict": verdict, "computed_new_members": members}


def test_no_limited_means_accepted():
    m = _m()
    status, sampling, resolved, rid = m.acceptance_decision(
        unresolved=0, n_limited=0, cov=None, kept_keys={"DEC|M|primary"})
    assert (status, sampling, resolved) == ("accepted", "complete", False)


def test_unresolved_work_always_wins():
    m = _m()
    status, sampling, resolved, _ = m.acceptance_decision(
        unresolved=2, n_limited=1, cov=_cov(), kept_keys={"DEC|M|r2_c23"})
    assert status == "provisional" and sampling == "in_progress"
    assert resolved is False


def test_limited_without_review_stays_limited():
    m = _m()
    status, sampling, _, _ = m.acceptance_decision(
        unresolved=0, n_limited=1, cov=None, kept_keys={"DEC|M|r2_c23"})
    assert status == "limited" and sampling == "sampling_limited"


def test_limited_with_resolved_review_and_member_in_pool_becomes_accepted():
    """The DEC/M scenario the recovery batch is running right now."""
    m = _m()
    status, sampling, resolved, rid = m.acceptance_decision(
        unresolved=0, n_limited=1, cov=_cov(),
        kept_keys={"DEC|M|primary", "DEC|M|r2_c23"})
    assert status == "accepted" and sampling == "complete"
    assert resolved is True and rid.startswith("coverage_review_v1")


def test_review_naming_a_member_absent_from_the_pool_cannot_upgrade():
    """Anti-cheat: the claimed member must actually be in `kept`."""
    m = _m()
    status, sampling, resolved, _ = m.acceptance_decision(
        unresolved=0, n_limited=1, cov=_cov(),
        kept_keys={"DEC|M|primary"})       # r2_c23 NOT in the kept pool
    assert status == "limited" and resolved is False


def test_review_with_no_claimed_members_cannot_upgrade():
    m = _m()
    status, _, resolved, _ = m.acceptance_decision(
        unresolved=0, n_limited=1, cov=_cov(members=""), kept_keys={"DEC|M|r2_c23"})
    assert status == "limited" and resolved is False


def test_pending_or_unresolved_review_cannot_upgrade():
    m = _m()
    for verdict in ("pending", "unresolved", "search_exhausted"):
        status, _, resolved, _ = m.acceptance_decision(
            unresolved=0, n_limited=1, cov=_cov(verdict=verdict),
            kept_keys={"DEC|M|r2_c23"})
        assert status == "limited", verdict
        assert resolved is False, verdict


def test_clearing_n_limited_is_the_only_other_route_and_it_is_not_used():
    """Sanity: with n_limited=0 the state accepts WITHOUT any review -- which
    is exactly why the historical counts must never be zeroed to fake a pass.
    The real pipeline keeps them (verified by the label-level test)."""
    m = _m()
    status, _, resolved, _ = m.acceptance_decision(
        unresolved=0, n_limited=0, cov=None, kept_keys={"DEC|M|primary"})
    assert status == "accepted" and resolved is False
