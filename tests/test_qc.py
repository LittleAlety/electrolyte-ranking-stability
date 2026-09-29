"""Tests for the v2 section 20 QC state machine."""

from __future__ import annotations

import pytest

from electrolyte_ranking.qc import (
    ABNORMAL_STATES,
    HAPPY_PATH,
    CalculationObject,
    QcState,
    QcTransitionError,
    abnormal_incidence_by_family,
    classify_qm_signals,
    next_happy_state,
    summarize,
)


def _obj(calc_id: str = "c1", family: str = "linear_carbonate") -> CalculationObject:
    return CalculationObject(
        calc_id=calc_id,
        mol_id="C01",
        charge=0,
        multiplicity=1,
        family=family,
    )


def _advance_to(record: CalculationObject, target: QcState) -> CalculationObject:
    """Walk the happy path up to `target` (inclusive), rejecting skips."""

    for state in HAPPY_PATH[1:]:
        record.advance(state)
        if state is target:
            return record
    raise AssertionError(f"{target.value} is not on the happy path")


def test_happy_path_is_walkable_to_accepted() -> None:
    record = _obj()
    for state in HAPPY_PATH[1:]:
        record.advance(state)
    assert record.state is QcState.ACCEPTED
    assert record.is_accepted
    assert not record.is_abnormal


def test_skipping_a_happy_state_is_rejected() -> None:
    record = _obj()
    with pytest.raises(QcTransitionError):
        record.advance(QcState.SCF_CONVERGED)


def test_reversing_the_happy_path_is_rejected() -> None:
    record = _obj()
    record.advance(QcState.PRESCREENED)
    with pytest.raises(QcTransitionError):
        record.advance(QcState.GENERATED)


def test_accepted_is_terminal() -> None:
    record = _obj()
    for state in HAPPY_PATH[1:]:
        record.advance(state)
    with pytest.raises(QcTransitionError):
        record.advance(QcState.MOTIF_SWITCH)


@pytest.mark.parametrize("branch", ABNORMAL_STATES)
def test_every_abnormal_branch_is_reachable(branch: QcState) -> None:
    record = _advance_to(_obj(), QcState.SUBMITTED)
    record.advance(branch, note="probe")
    assert record.state is branch
    assert record.is_abnormal
    assert record.notes == ["probe"]


def test_next_happy_state_terminates_at_accepted() -> None:
    assert next_happy_state(QcState.GENERATED) is QcState.PRESCREENED
    with pytest.raises(QcTransitionError):
        next_happy_state(QcState.ACCEPTED)


def test_scf_failure_outranks_every_other_signal() -> None:
    assert (
        classify_qm_signals(
            normal_termination=False,
            scf_converged=True,
            geometry_converged=True,
            imaginary_modes=2,
        )
        is QcState.SCF_FAILED
    )


def test_clean_signals_return_none() -> None:
    assert (
        classify_qm_signals(
            normal_termination=True,
            scf_converged=True,
            geometry_converged=True,
        )
        is None
    )


def test_anion_unbound_is_flagged_not_dropped() -> None:
    state = classify_qm_signals(
        normal_termination=True,
        scf_converged=True,
        geometry_converged=True,
        anion_unbound=True,
    )
    assert state is QcState.UNBOUND_ANION


def test_imaginary_mode_precedes_connectivity_change() -> None:
    state = classify_qm_signals(
        normal_termination=True,
        scf_converged=True,
        geometry_converged=True,
        imaginary_modes=1,
        connectivity_changed=True,
    )
    assert state is QcState.IMAGINARY_MODE_UNRESOLVED


def test_summary_keeps_abnormal_records_in_the_denominator() -> None:
    records = []
    for index in range(3):
        record = _obj(f"ok{index}", family="ether")
        for state in HAPPY_PATH[1:]:
            record.advance(state)
        records.append(record)
    broken = _advance_to(_obj("bad0", family="ether"), QcState.SUBMITTED)
    broken.advance(QcState.UNBOUND_ANION)
    records.append(broken)

    summary = summarize(records)
    assert summary.total == 4
    assert summary.accepted_fraction == pytest.approx(0.75)
    assert summary.abnormal_fraction == pytest.approx(0.25)
    assert summary.per_family["ether"][QcState.UNBOUND_ANION.value] == 1


def test_abnormal_incidence_by_family() -> None:
    good = _obj("g1", family="nitrile")
    for state in HAPPY_PATH[1:]:
        good.advance(state)
    bad = _advance_to(_obj("b1", family="nitrile"), QcState.SUBMITTED)
    bad.advance(QcState.SCF_FAILED)

    incidence = abnormal_incidence_by_family([good, bad])
    assert incidence["nitrile"] == pytest.approx(0.5)


def test_empty_summary_is_defined() -> None:
    summary = summarize([])
    assert summary.total == 0
    assert summary.abnormal_fraction == 0.0
    assert summary.accepted_fraction == 0.0
