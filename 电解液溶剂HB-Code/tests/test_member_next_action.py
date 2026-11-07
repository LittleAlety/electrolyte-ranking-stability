"""The three unmixable branches of member next-action routing (frozen contract)."""
import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "wp_production" / "member_next_action.py"


def _module():
    spec = importlib.util.spec_from_file_location("member_next_action", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(SCRIPT.parent))
    spec.loader.exec_module(module)
    return module


def _row(status="technical_complete_qc_failed", failure="", flags=""):
    return {"status": status, "failure_class": failure, "qc_flags": flags}


# ── branch 1: technical fault is NOT a science failure ──────────────────────

def test_segfault_is_a_technical_retry_not_a_budget_charge():
    m = _module()
    row = _row(failure="abnormal_termination")
    assert m.next_action(row, attempts=[{"attempt": "0", "log_sha256": "x"}]) == \
        "technical_retry_after_diagnosis"
    # Even a lineage that already burned one real attempt gets the technical
    # path: the segfault attempt itself never counted against the budget.
    assert m.next_action(row, attempts=[{"attempt": "1", "log_sha256": "y"}]) == \
        "technical_retry_after_diagnosis"


# ── branch 2: species drift is never continued / never a budget answer ──────

def test_species_drift_stops_even_with_budget_left():
    m = _module()
    for flag in ("candidate_bond_graph_changed",
                 "candidate_species_changed",
                 "candidate_atom_order_changed"):
        row = _row(failure="max_cycles_exhausted", flags=flag)
        # zero prior attempts, budget fully available -- drift still wins:
        assert m.next_action(row, attempts=[]) == "stop_species_drift"


def test_species_drift_outranks_every_other_branch():
    m = _module()
    # computed + drift flag cannot happen in practice, but if it ever did the
    # drift answer must not silently pass a foreign species into dedup.
    row = _row(status="computed", failure="", flags="candidate_bond_graph_changed")
    assert m.next_action(row, attempts=[]) == "stop_species_drift"
    # abnormal termination + drift: identity question again outranks retry.
    row = _row(failure="abnormal_termination", flags="candidate_atom_order_changed")
    assert m.next_action(row, attempts=[]) == "stop_species_drift"


# ── branch 3: exhausted budget is limited, never "no minimum exists" ────────

def test_budget_exhausted_after_two_real_attempts():
    m = _module()
    row = _row(failure="verytight_convergence")
    two = [{"attempt": "0", "log_sha256": "a"}, {"attempt": "1", "log_sha256": "b"}]
    assert m.next_action(row, attempts=two) == "limited_rescue_budget_exhausted"
    # The decision NAME must never be phrased as an absence of minima.
    assert "no_minimum" not in m.next_action(row, attempts=two)


def test_budget_counts_distinct_attempt_log_pairs_not_rows():
    m = _module()
    # A re-imported identical log is ONE real attempt, not two.
    same_log = [{"attempt": "0", "log_sha256": "a"},
                {"attempt": "0", "log_sha256": "a"}]
    row = _row(failure="max_cycles_exhausted")
    assert m.next_action(row, attempts=same_log) == \
        "continuation_only_if_restart_identity_matches"
    # The importer deduplicates before calling; the function trusts distinct pairs.
    distinct = [{"attempt": "0", "log_sha256": "a"},
                {"attempt": "1", "log_sha256": "b"}]
    assert m.next_action(_row(failure="max_cycles_exhausted"), attempts=distinct) == \
        "limited_rescue_budget_exhausted"


# ── the two evidence-based rescues ──────────────────────────────────────────

def test_strict_reopt_routes_from_own_converged_geometry():
    m = _module()
    for failure in ("strict_reopt_required", "verytight_convergence"):
        row = _row(failure=failure)
        assert m.next_action(row, attempts=[{"attempt": "0", "log_sha256": "x"}]) == \
            "reopt_from_own_converged_geometry"


def test_max_cycles_routes_to_identity_gated_continuation():
    m = _module()
    row = _row(failure="max_cycles_exhausted")
    assert m.next_action(row, attempts=[]) == \
        "continuation_only_if_restart_identity_matches"


# ── the clean pass and the fallback ─────────────────────────────────────────

def test_computed_goes_to_dedup():
    m = _module()
    assert m.next_action(_row(status="computed"), attempts=[{"attempt": "0", "log_sha256": "x"}]) == \
        "accept_for_dedup"


def test_unknown_failure_asks_for_a_human():
    m = _module()
    row = _row(failure="orca_error_in_log")
    assert m.next_action(row, attempts=[]) == "manual_review"
    assert m.next_action(_row(failure=""), attempts=[]) == "manual_review"


# ── duplicate-submission interception (routing must not double-charge) ─────

def test_duplicate_resubmission_is_not_a_new_real_attempt():
    """The caller passes the lineage; re-running the SAME calculation must not
    make the lineage look like it used three attempts."""
    m = _module()
    lineage = [{"attempt": "0", "log_sha256": "a"},
               {"attempt": "1", "log_sha256": "b"}]
    # A duplicate submission would add (attempt=1, log_sha256=b) again; the
    # importer dedups, and the budget gate keys on distinct pairs:
    deduped = {(a["attempt"], a["log_sha256"]) for a in lineage}
    assert len(deduped) == 2
    assert m.next_action(_row(failure="verytight_convergence"), attempts=sorted(
        [{"attempt": k[0], "log_sha256": k[1]} for k in deduped], key=str)) == \
        "limited_rescue_budget_exhausted"
