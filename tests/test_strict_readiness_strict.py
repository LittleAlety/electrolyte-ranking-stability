"""G0: the strict readiness gate must REFUSE bad evidence.

The measured defect (2026-10-22, independent reviewer): in-memory substitution of
six kinds of broken input still made every check return True:

* coverage row with no ``verdict``   (``None != ""`` is True -- the key width bug)
* identity table with ONE ``computed`` row (``computed == len(rows)`` -- no cohort)
* sampling ``not_computed`` carrying a reason (any reason counted as a decision)
* WP3 / WP5 status ``invalid_input``  (any non-empty status counted)
* cost ``NaN``                        (non-empty string counted)
* ``wp6_triggered`` / ``pool_extension_triggered`` hard-coded ``False``

These tests are written to FAIL on that implementation and PASS on the strict
one.  Each bad-evidence case pins one specific looseness; the positive controls
exist so "reject everything" is not mistaken for strictness.
"""
import csv
import importlib.util
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
WIRING = REPO / "scripts" / "wp_production" / "strict_readiness_wiring.py"
OUT = REPO / "outputs" / "physics_completion"


def _load():
    spec = importlib.util.spec_from_file_location("srw", WIRING)
    m = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(WIRING.parent))
    spec.loader.exec_module(m)
    return m


@pytest.fixture(scope="module")
def wiring():
    return _load()


def _patch_source(monkeypatch, wiring, tmp_path, flag, bad_rows):
    """Bad rows for the flag under test; every other source stays REAL.

    The cohort checks read the real labels/weights, so they must keep working:
    patching ``_rows`` globally would corrupt the context and make the test
    unable to tell "rejected because bad" from "rejected because no context".
    """
    source = tmp_path / "evidence.csv"
    source.write_text("x\n", encoding="utf-8")
    real = wiring._rows

    def fake(path):
        return bad_rows if Path(path) == source else real(Path(path))

    monkeypatch.setitem(wiring.SOURCES, flag, source)
    monkeypatch.setattr(wiring, "_rows", fake)
    return source


# ---- 1) the five measured loosenesses (these FAIL on the old wiring) --------

@pytest.mark.parametrize(("flag", "bad_rows"), [
    ("coverage_reviews_valid", [{}]),
    ("identity_all_members_complete", [{"status": "computed"}]),
    ("sampling_audit_complete",
     [{"ceiling_status": "not_computed", "ceiling_reason": "missing"}]),
    ("wp3_evidence_complete", [{"status": "invalid_input"}]),
    ("wp5_full_target_pool_evaluated", [{"stop_budget_status": "invalid_input"}]),
    ("execution_cost_provenance_complete", [{"core_hours": "NaN"}]),
])
def test_bad_evidence_must_not_pass(wiring, monkeypatch, tmp_path, flag, bad_rows):
    _patch_source(monkeypatch, wiring, tmp_path, flag, bad_rows)
    assert wiring.derive_checks()[flag] is False


# ---- 2) additional strictness the plan requires ----------------------------

def test_coverage_missing_verdict_is_rejected(wiring, monkeypatch, tmp_path):
    """A row with name/state but no verdict is not a review."""
    rows = [{"name": "DMC", "state": "M_plus", "route": "unresolved_qc"}]
    _patch_source(monkeypatch, wiring, tmp_path, "coverage_reviews_valid", rows)
    assert wiring.derive_checks()["coverage_reviews_valid"] is False


def test_coverage_unknown_route_or_verdict_is_rejected(wiring, monkeypatch, tmp_path):
    rows = [{"name": "DMC", "state": "M_plus", "route": "made_up_route",
             "verdict": "resolved", "review_version": "1", "n_unique_after": "2"}]
    _patch_source(monkeypatch, wiring, tmp_path, "coverage_reviews_valid", rows)
    assert wiring.derive_checks()["coverage_reviews_valid"] is False
    rows[0]["route"] = "multi_basin_coverage"
    rows[0]["verdict"] = "definitely_resolved"
    _patch_source(monkeypatch, wiring, tmp_path, "coverage_reviews_valid", rows)
    assert wiring.derive_checks()["coverage_reviews_valid"] is False


def test_identity_cohort_must_cover_every_weighted_member(wiring, monkeypatch, tmp_path):
    """One computed row cannot stand for the 80-member weighted cohort."""
    rows = [{"member_key": "X|M|primary", "name": "X", "status": "computed",
             "identity_qc_status": "verified", "molden_status": "computed",
             "fmopop_status": "computed", "wavefunction": "R"}]
    _patch_source(monkeypatch, wiring, tmp_path, "identity_all_members_complete", rows)
    assert wiring.derive_checks()["identity_all_members_complete"] is False


def test_sampling_not_computed_must_not_carry_a_number(wiring, monkeypatch, tmp_path):
    """A not_computed row with a filled G is fabricated evidence -- 空值不是零."""
    rows = [{"name": "DMC", "state": "M_plus", "ceiling_status": "not_computed",
             "ceiling_reason": "pool_has_no_independent_structure",
             "g_ensemble_ceiling_kcal": "-1.234",
             "delta_g_ensemble_kcal": "-1.234"}]
    _patch_source(monkeypatch, wiring, tmp_path, "sampling_audit_complete", rows)
    assert wiring.derive_checks()["sampling_audit_complete"] is False


def test_sampling_complete_must_satisfy_the_print_identity(wiring, monkeypatch, tmp_path):
    """delta must equal ceiling - round1 in the printed precision (hand-checkable)."""
    rows = [{"name": "DMC", "state": "M_plus", "ceiling_status": "complete",
             "ceiling_reason": "", "g_ensemble_round1_kcal": "-100.000",
             "g_ensemble_ceiling_kcal": "-101.000",
             "delta_g_ensemble_kcal": "-0.500"}]
    _patch_source(monkeypatch, wiring, tmp_path, "sampling_audit_complete", rows)
    assert wiring.derive_checks()["sampling_audit_complete"] is False


def test_wp5_subset_pool_is_not_the_full_cohort(wiring, monkeypatch, tmp_path):
    """A=11 / B=9 is a QUALIFIED SUBSET, not the 12-molecule acceptance."""
    rows = [{"task": "A", "baseline": "uncertainty", "executed_model": "ridge_std",
             "acquisition_version": "knn_v1", "n_pool": "11", "repeats": "20",
             "stop_budget_status": "not_reached_within_pool", "stop_budget_n_T": ""}]
    _patch_source(monkeypatch, wiring, tmp_path, "wp5_full_target_pool_evaluated", rows)
    assert wiring.derive_checks()["wp5_full_target_pool_evaluated"] is False


def test_cost_rejects_nan_inf_negative_blank_and_unknown_status(wiring, monkeypatch, tmp_path):
    for bad in ({"core_hours": "NaN"}, {"core_hours": "inf"},
                {"core_hours": "-3.0"}, {"core_hours": ""},
                {"core_hours": "12.0", "cost_status": "guessed"},
                {"core_hours": "12.0", "status": "computed", "cores": "0"}):
    # the valid baseline row (so only the bad field can fail the check)
        row = {"job_id": "1", "name": "DEC", "state": "M", "cores": "4",
               "cost_status": "complete", "status": "computed"}
        row.update(bad)
        _patch_source(monkeypatch, wiring, tmp_path,
                      "execution_cost_provenance_complete", [row])
        assert wiring.derive_checks()["execution_cost_provenance_complete"] is False, bad


def test_cost_missing_must_not_become_zero(wiring, monkeypatch, tmp_path):
    """Empty cost with no alternative column is MISSING, never 0."""
    row = {"job_id": "1", "name": "DEC", "state": "M", "cores": "4",
           "core_hours": "", "hpc_core_hours": "", "cost_status": "complete",
           "status": "computed"}
    _patch_source(monkeypatch, wiring, tmp_path,
                  "execution_cost_provenance_complete", [row])
    checks = wiring.derive_checks()
    assert checks["execution_cost_provenance_complete"] is False


# ---- 3) positive controls: strict must not mean "reject everything" --------

def test_synthetic_legal_coverage_fixture_passes(wiring, monkeypatch, tmp_path):
    """Exactly the non-accepted states, each with a valid route+verdict."""
    real = wiring._rows
    labels = real(wiring.CONTEXT["labels"])
    open_states = {(r["name"], r["state"]) for r in labels
                   if r["acceptance_status"] != "accepted"}
    assert open_states, "the real project must currently have open states"
    rows = [{"name": n, "state": s, "route": "unresolved_qc", "verdict": "unresolved",
             "review_version": "1", "n_unique_after": "1",
             "historical_limitation": "x", "kept_pool_evidence": ""}
            for n, s in sorted(open_states)]
    _patch_source(monkeypatch, wiring, tmp_path, "coverage_reviews_valid", rows)
    assert wiring.derive_checks()["coverage_reviews_valid"] is True


def test_real_artifacts_produce_a_mixed_verdict(wiring):
    """Every check False would mean the validator is broken, not strict."""
    checks = wiring.derive_checks()
    required = [k for k in wiring.REQUIRED_CHECKS]
    assert all(isinstance(checks[k], bool) for k in required)
    assert any(checks[k] for k in required), checks


# ---- 4) dynamic triggers must not be hard-coded ---------------------------

def test_wp6_trigger_is_unknown_without_li_pair_evidence(wiring):
    labels = [{"name": "A", "state": "M", "acceptance_status": "accepted"}]
    assert wiring.derive_wp6_trigger(labels, set("ABCDEFGHIJKL"), None) == "unknown"


def test_wp6_trigger_fires_only_with_both_preconditions(wiring):
    mols = list("ABCDEFGHIJKL")
    states = ("M", "M_plus", "LiM_plus", "LiM_2plus")
    labels = [{"name": m, "state": s, "acceptance_status": "accepted"}
              for m in mols for s in states]
    assert wiring.derive_wp6_trigger(labels, set(mols), list("ABCDEFGHI")) == "triggered"
    # 8 pairs is below the plan's >=9 threshold
    assert wiring.derive_wp6_trigger(labels, set(mols),
                                     list("ABCDEFGH")) == "not_triggered"
    # one state not accepted -> the ensemble precondition has not fired
    labels[0]["acceptance_status"] = "limited"
    assert wiring.derive_wp6_trigger(labels, set(mols), list("ABCDEFGHI")) == "not_triggered"


def test_wp6_trigger_unknown_on_broken_input(wiring):
    mols = list("ABCDEFGHIJKL")
    # duplicate keys
    labels = [{"name": "A", "state": "M", "acceptance_status": "accepted"}] * 2
    assert wiring.derive_wp6_trigger(labels, set(mols), list("ABCDEFGHI")) == "unknown"
    # unknown status token
    states = ("M", "M_plus", "LiM_plus", "LiM_2plus")
    labels = [{"name": m, "state": s, "acceptance_status": "accepted"}
              for m in mols for s in states]
    labels[0]["acceptance_status"] = "blorp"
    assert wiring.derive_wp6_trigger(labels, set(mols), list("ABCDEFGHI")) == "unknown"


def test_triggers_are_derived_not_constants(wiring):
    src = WIRING.read_text(encoding="utf-8")
    assert 'checks["wp6_triggered"] = False' not in src
    assert 'checks["pool_extension_triggered"] = False' not in src
    assert "derive_wp6_trigger" in src


# ---- 5) the gate must block on an unknown trigger --------------------------

def test_unknown_trigger_blocks_the_gate(wiring):
    rd = _load_readiness()
    labels = [{"name": "A", "state": "M", "acceptance_status": "accepted"}]
    checks = {k: True for k in wiring.REQUIRED_CHECKS}
    checks["wp6_trigger_state"] = "unknown"
    checks["pool_extension_trigger_state"] = "not_triggered"
    out = rd.strict_readiness(labels, {("A", "M")}, checks)
    assert out["complete"] is False
    assert "wp6_trigger_unknown" in out["blocked_by"]


def _load_readiness():
    spec = importlib.util.spec_from_file_location(
        "sr", REPO / "scripts" / "wp_production" / "strict_readiness.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m