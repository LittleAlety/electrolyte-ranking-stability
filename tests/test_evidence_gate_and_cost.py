"""Tests for the 2026-10-27 ruling's minimum checklist (evidence gate + cost).

The ruling names EIGHT minimum cases; each maps to one test below:

 1. preflight STALE -> HOLD
 2. a submission attempt with an unclear response -> RECONCILE (never resubmit)
 3. Slurm COMPLETED but no QC yet -> FETCH/QC path (still work to do)
 4. QC failed but evidence complete -> settlement proceeds (limitation report)
 5. one array element's cost record missing -> settlement refused, not zero
 6. parent array + .batch records -> no double billing
 7. duplicate record for the same element -> refuse simple addition
 8. DMC / a third task / a reserve start mixed in -> refuse BEFORE submission
"""

from __future__ import annotations

import importlib.util
import sys
from decimal import Decimal
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
PROD = REPO / "scripts" / "wp_production"
sys.path.insert(0, str(PROD))


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, PROD / rel)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m          # dataclasses resolves cls.__module__ via this
    spec.loader.exec_module(m)
    return m


EG = _load("evidence_gate", "evidence_gate.py")
CS = _load("batch_cost_settlement", "batch_cost_settlement.py")


def _evidence(**kw):
    base = dict(preflight_ok=True, authorization_bound=True, package_verified=True,
                budget_reserved=True, submission_status="absent",
                job_mapping_verified=True, terminal_states_verified=True,
                artifacts_verified=True, qc_results_complete=True,
                cost_settled=True, downstream_checks_ok=True)
    base.update(kw)
    return EG.Evidence(**base)


# ---- 1. preflight STALE -> HOLD ---------------------------------------------
def test_preflight_stale_blocks_submission():
    assert EG.next_action(_evidence(preflight_ok=False)) is EG.NextAction.HOLD


def test_all_gates_ready_then_submit_once():
    e = _evidence(submission_status="absent", downstream_checks_ok=False,
                  cost_settled=False, qc_results_complete=False,
                  artifacts_verified=False, terminal_states_verified=False,
                  job_mapping_verified=False)
    assert EG.next_action(e) is EG.NextAction.SUBMIT_ONCE
    # everything done (a SUBMITTED batch that reached the end of the chain)
    assert EG.next_action(_evidence(submission_status="submitted")) \
        is EG.NextAction.REPORT


# ---- 2. unclear submission response -> RECONCILE, never resubmit -----------
@pytest.mark.parametrize("status", ["submitting", "submit_failed", "unknown"])
def test_unclear_submission_reconciles_never_resubmits(status):
    assert EG.next_action(_evidence(submission_status=status)) \
        is EG.NextAction.RECONCILE


# ---- 3. COMPLETED but no QC yet -> fetch / run QC --------------------------
def test_completed_without_artifacts_then_fetch_then_qc():
    e = _evidence(submission_status="submitted", artifacts_verified=False)
    assert EG.next_action(e) is EG.NextAction.FETCH
    e2 = _evidence(submission_status="submitted", artifacts_verified=True,
                   qc_results_complete=False)
    assert EG.next_action(e2) is EG.NextAction.QC


def test_not_terminal_yet_then_wait():
    assert EG.next_action(
        _evidence(submission_status="submitted", terminal_states_verified=False)) \
        is EG.NextAction.WAIT


# ---- 4. QC failed but evidence complete -> settle + report, never retry -----
def test_qc_failed_still_settles_and_reports():
    """qc_results_complete means every leg HAS a verdict, not that it passed."""
    e = _evidence(submission_status="submitted",
                  qc_results_complete=True,   # explicit FAILING verdicts count
                  cost_settled=False)
    assert EG.next_action(e) is EG.NextAction.SETTLE
    assert EG.next_action(_evidence(submission_status="submitted")) \
        is EG.NextAction.REPORT


# ---- 5. missing cost record refuses settlement ------------------------------
def test_missing_cost_record_refuses_not_zero():
    rows = [{"JobIDRaw": "1_0", "AllocCPUS": "4", "ElapsedRaw": "3610"}]
    with pytest.raises(ValueError, match="MISSING"):
        CS.allocated_core_hours(rows, expected_job_ids=["1_0", "1_1"])


# ---- 6. parent array / .batch / .extern rows are not double-billed ----------
def test_parent_and_batch_rows_not_billed():
    rows = [
        {"JobIDRaw": "1",     "AllocCPUS": "4", "ElapsedRaw": "99999"},  # parent
        {"JobIDRaw": "1_0",   "AllocCPUS": "4", "ElapsedRaw": "3610"},
        {"JobIDRaw": "1_0.b", "AllocCPUS": "4", "ElapsedRaw": "3610"},   # .batch
        {"JobIDRaw": "1_0.e", "AllocCPUS": "4", "ElapsedRaw": "3610"},   # .extern
    ]
    total = CS.allocated_core_hours(rows, expected_job_ids=["1_0"])
    assert total == Decimal("4") * Decimal(3610) / Decimal(3600)


# ---- 7. duplicate record for the same element -> refuse ---------------------
def test_duplicate_record_refuses_simple_addition():
    rows = [
        {"JobIDRaw": "1_0", "AllocCPUS": "4", "ElapsedRaw": "10"},
        {"JobIDRaw": "1_0", "AllocCPUS": "4", "ElapsedRaw": "10"},
    ]
    with pytest.raises(ValueError, match="重复调度记录"):
        CS.allocated_core_hours(rows, expected_job_ids=["1_0"])


# ---- 8. batch must be EXACTLY the two activated tasks ------------------------
def test_third_task_or_dmc_mixed_in_refused(tmp_path):
    act = EG.activation_member_keys()
    assert len(act) == 2
    # build a fake package dir whose tasks.txt carries a DMC task
    pkg = tmp_path / "dol_ec_recovery_v1"
    (pkg / "tasks").mkdir(parents=True)
    keys = set(act) | {("DMC", "tors_9_0_1_2")}
    lines = ["tasks/%s/LiM_2plus__%s" % (n, s) for (n, s) in keys]
    (pkg / "tasks.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    assert EG.batch_is_exactly_activated(pkg) is False
    # and the gate holds on it
    assert EG.next_action(
        _evidence(batch_tasks_exactly_activated=False)) is EG.NextAction.HOLD


def test_real_batch_is_exactly_the_two_activated():
    pkg = REPO / "work" / "dol_ec_recovery_v1"
    if not pkg.is_dir():
        pytest.skip("machine-local work/ layer absent in this checkout")
    assert EG.batch_is_exactly_activated(pkg) is True


# ---- sacct parsing helpers ----------------------------------------------------
def test_parse_sacct_rows_and_elapsedraw():
    text = ("JobIDRaw|State|AllocCPUS|ElapsedRaw\n"
            "3782517_0|COMPLETED|4|3848\n")
    rows = CS.parse_sacct_rows(text)
    assert rows[0]["JobIDRaw"] == "3782517_0"
    assert CS.allocated_core_hours(rows, ["3782517_0"]) == Decimal("3848") * 4 / 3600
    assert CS.parse_elapsed_raw("01:04:08") == 3848
    assert CS.parse_elapsed_raw("1-02:03:04") == 93784


def test_negative_elapsed_raw_refused():
    with pytest.raises(ValueError):
        CS.parse_elapsed_raw("-5")


def test_terminal_state_verifier():
    rows = [{"JobIDRaw": "9_0", "State": "COMPLETED"},
            {"JobIDRaw": "9_1", "State": "RUNNING"}]
    assert EG.sacct_terminal_states(rows, ["9_0", "9_1"]) == {}   # still running
    rows2 = [{"JobIDRaw": "9_0", "State": "COMPLETED"},
             {"JobIDRaw": "9_1", "State": "FAILED"}]
    assert EG.sacct_terminal_states(rows2, ["9_0", "9_1"]) == \
        {"9_0": "COMPLETED", "9_1": "FAILED"}
    # a subset of expected ids present + terminal IS a valid terminal map for
    # that subset; the INCOMPLETE-set refusal is the first case (["9_0","9_1"]
    # with only 9_0 present), not this one
    assert EG.sacct_terminal_states(rows2, ["9_0"]) == {"9_0": "COMPLETED"}
    # a missing element inside a larger expectation refuses (incomplete set)
    assert EG.sacct_terminal_states([{"JobIDRaw": "9_0", "State": "COMPLETED"}],
                                    ["9_0", "9_1"]) == {}
