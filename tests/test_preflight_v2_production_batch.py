"""preflight schema-2 validation: the dol_ec 12h production batch.

Pins the v2 rules from the execution plan ("两条合法、第三条拒绝、错误态拒绝、
超过 96 CH 拒绝"): the 12h wall exception is valid ONLY for the two authorized
states and ONLY at the exact authorized 4c x 12h x 2 = 96 CH reservation.  A
third state, a state that is not a recovery target, a changed resource profile,
or a reservation above 96 CH must all be rejected.
"""
import importlib.util
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
PREFLIGHT = REPO / "docs" / "handoffs" / "four_state_recovery_20261023" / "preflight.py"


def _load():
    spec = importlib.util.spec_from_file_location("preflight_under_test", PREFLIGHT)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


@pytest.fixture(scope="module")
def pf():
    return _load()


def _authorized_batch(pf):
    """A budget dict carrying the exact authorized dol_ec batch (mutations stay local)."""
    return {"production_batches": {"dol_ec_recovery_v1": {
        "resource_profile": pf.P4V2_BATCH["resource_profile"],
        "states": list(pf.P4V2_BATCH["states"]),
        "cores": pf.P4V2_BATCH["cores"],
        "wall_hours": pf.P4V2_BATCH["wall_hours"],
        "max_legs": pf.P4V2_BATCH["max_legs"],
        "max_per_state": pf.P4V2_BATCH["max_per_state"],
        "reserved_core_hours": pf.P4V2_BATCH["reserved_core_hours"],
        "paid_from": pf.P4V2_BATCH["paid_from"],
        "start_geometry": pf.P4V2_BATCH["start_geometry"],
        "second_start_and_rescue": pf.P4V2_BATCH["second_start_and_rescue"],
        }}}


def test_the_two_authorized_states_pass(pf):
    pf.validate_production_batches(_authorized_batch(pf))  # must not raise


def test_a_third_state_is_rejected(pf):
    batch = _authorized_batch(pf)
    batch["production_batches"]["dol_ec_recovery_v1"]["states"].append("DMC|M_plus")
    with pytest.raises(ValueError):
        pf.validate_production_batches(batch)


def test_a_non_target_state_is_rejected(pf):
    batch = _authorized_batch(pf)
    batch["production_batches"]["dol_ec_recovery_v1"]["states"] = ["EMC|M", "EC|LiM_2plus"]
    with pytest.raises(ValueError):
        pf.validate_production_batches(batch)


def test_reservation_above_96_ch_is_rejected(pf):
    batch = _authorized_batch(pf)
    batch["production_batches"]["dol_ec_recovery_v1"]["reserved_core_hours"] = 97
    with pytest.raises(ValueError):
        pf.validate_production_batches(batch)


def test_wall_hours_widened_breaks_the_authorization(pf):
    batch = _authorized_batch(pf)
    # 4c x 24h x 2 = 192 CH would match the OLD draft-package error, not 96.
    batch["production_batches"]["dol_ec_recovery_v1"]["wall_hours"] = 24
    batch["production_batches"]["dol_ec_recovery_v1"]["reserved_core_hours"] = 192
    with pytest.raises(ValueError):
        pf.validate_production_batches(batch)


def test_wrong_resource_profile_is_rejected(pf):
    batch = _authorized_batch(pf)
    batch["production_batches"]["dol_ec_recovery_v1"]["resource_profile"] = "orca_production_v1"
    with pytest.raises(ValueError):
        pf.validate_production_batches(batch)


def test_a_missing_v2_batch_is_rejected(pf):
    # validate_contract only calls this for schema >= 2; when it does, the
    # authorized batch must be present.  A budget missing it is rejected.
    with pytest.raises(ValueError):
        pf.validate_production_batches({})
