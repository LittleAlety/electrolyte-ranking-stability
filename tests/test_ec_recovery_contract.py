"""L02: the EC campaign machine contract must fail closed on every bad shape.

These are negative tests for the four refusal classes named by the execution
supplement (wrong candidate, third leg, low-reported reservation, missing ledger
requirement) plus the budget / in-flight / resource-shape guards.
"""
from __future__ import annotations

import pytest

from wp_production import ec_recovery_contract as contract
from wp_production import submit_hpc_batch as submit


def test_ec_profile_has_fixed_resource_shape_and_real_ledger():
    profile = submit.RESOURCE_PROFILES[contract.EC_PROFILE]
    assert profile["cores"] == 4
    assert profile["wall_hours"] == 4
    assert profile["budget_cap_core_hours"] == "32"
    assert profile["attempts_ledger_required"] is True


def test_historical_profiles_keep_their_own_ledger_semantics():
    # Tightening the new EC profile must not rewrite already-versioned history.
    assert submit.RESOURCE_PROFILES["orca_production_v1"]["attempts_ledger_required"] is False
    assert submit.RESOURCE_PROFILES["xtb_screening_v2"]["attempts_ledger_required"] is True


def test_campaign_constants_match_the_supplement():
    assert contract.EC_CANDIDATES == ("ec_v2_p4", "ec_v2_p7")
    assert contract.EC_ELEMENT_CORE_HOURS == 16
    assert contract.EC_CAP_CORE_HOURS == 32
    assert contract.EC_MAX_SUBMITTED_ELEMENTS == 2


def test_first_submission_must_be_p4():
    assert contract.next_candidate([]) == "ec_v2_p4"


def test_p4_in_flight_blocks_the_next_submission():
    history = [{"candidate": "ec_v2_p4", "submitted": True, "terminal": False}]
    assert contract.next_candidate(history) is None


def test_p4_accepted_ends_the_campaign():
    history = [{"candidate": "ec_v2_p4", "submitted": True, "terminal": True,
                "accepted": True}]
    assert contract.next_candidate(history) is None


def test_p4_failure_activates_p7():
    history = [{"candidate": "ec_v2_p4", "submitted": True, "terminal": True,
                "accepted": False}]
    assert contract.next_candidate(history) == "ec_v2_p7"


def test_p7_submitted_ends_the_campaign():
    history = [
        {"candidate": "ec_v2_p4", "submitted": True, "terminal": True,
         "accepted": False},
        {"candidate": "ec_v2_p7", "submitted": True, "terminal": True,
         "accepted": False},
    ]
    assert contract.next_candidate(history) is None


def test_first_p4_reserves_sixteen_of_thirty_two():
    accepted = contract.check_campaign_contract(
        candidate="ec_v2_p4", profile=contract.EC_PROFILE, cores=4, wall_hours=4,
        element_count=1, declared_reservation_core_hours=16,
    )
    assert accepted["new_reservation_core_hours"] == 16
    assert accepted["remaining_after_this_core_hours"] == 16


def test_second_leg_fits_exactly_when_the_first_is_settled():
    accepted = contract.check_campaign_contract(
        candidate="ec_v2_p7", profile=contract.EC_PROFILE, cores=4, wall_hours=4,
        element_count=1, declared_reservation_core_hours=16,
        settled_core_hours=16.0, ec_submitted_elements=1,
        history=[{"candidate": "ec_v2_p4", "submitted": True, "terminal": True,
                  "accepted": False}],
    )
    assert accepted["remaining_after_this_core_hours"] == 0


def test_unregistered_candidate_is_refused():
    with pytest.raises(contract.ContractViolation, match="not registered"):
        contract.check_campaign_contract(
            candidate="ec_v2_p3", profile=contract.EC_PROFILE, cores=4,
            wall_hours=4, element_count=1, declared_reservation_core_hours=16,
        )


def test_p7_before_p4_is_refused():
    with pytest.raises(contract.ContractViolation, match="next campaign step"):
        contract.check_campaign_contract(
            candidate="ec_v2_p7", profile=contract.EC_PROFILE, cores=4,
            wall_hours=4, element_count=1, declared_reservation_core_hours=16,
        )


def test_low_reported_reservation_is_refused():
    with pytest.raises(contract.ContractViolation, match="low-reported reservation"):
        contract.check_campaign_contract(
            candidate="ec_v2_p4", profile=contract.EC_PROFILE, cores=4,
            wall_hours=4, element_count=1, declared_reservation_core_hours=8,
        )


def test_third_leg_is_refused():
    with pytest.raises(contract.ContractViolation, match="third leg refused"):
        contract.check_campaign_contract(
            candidate="ec_v2_p4", profile=contract.EC_PROFILE, cores=4,
            wall_hours=4, element_count=1, declared_reservation_core_hours=16,
            ec_submitted_elements=2,
        )


def test_campaign_cap_is_enforced():
    with pytest.raises(contract.ContractViolation, match="budget exceeded"):
        contract.check_campaign_contract(
            candidate="ec_v2_p4", profile=contract.EC_PROFILE, cores=4,
            wall_hours=4, element_count=1, declared_reservation_core_hours=16,
            unsettled_reserved_core_hours=16.5,
        )


def test_active_pending_element_blocks_submission():
    with pytest.raises(contract.ContractViolation, match="active/pending"):
        contract.check_campaign_contract(
            candidate="ec_v2_p4", profile=contract.EC_PROFILE, cores=4,
            wall_hours=4, element_count=1, declared_reservation_core_hours=16,
            ec_active_pending=1,
        )


def test_wrong_profile_is_refused():
    with pytest.raises(contract.ContractViolation, match="authorised EC profile"):
        contract.check_campaign_contract(
            candidate="ec_v2_p4", profile="orca_production_v1", cores=4,
            wall_hours=4, element_count=1, declared_reservation_core_hours=16,
        )


def test_wrong_core_count_is_refused():
    with pytest.raises(contract.ContractViolation, match="cores"):
        contract.check_campaign_contract(
            candidate="ec_v2_p4", profile=contract.EC_PROFILE, cores=8,
            wall_hours=4, element_count=1, declared_reservation_core_hours=32,
        )


def test_more_than_one_element_in_flight_is_refused():
    with pytest.raises(contract.ContractViolation, match="exactly one element"):
        contract.check_campaign_contract(
            candidate="ec_v2_p4", profile=contract.EC_PROFILE, cores=4,
            wall_hours=4, element_count=2, declared_reservation_core_hours=32,
        )
