"""WP3's R4 rung must absorb recovery members automatically (plan item 6).

The rung is computed from the ensemble LABELS, so when a new independent
minimum lands:

* ``g_ensemble_eh`` shifts (the Boltzmann sum gains a member), and
* ``acceptance_status`` may flip limited -> accepted,

both of which change the rung.  These tests pin that the rung is driven by the
labels -- if someone ever hard-codes the member set, the rung would silently
keep reporting the pre-recovery value and this test would fail.
"""
import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CLOSURE = REPO / "scripts" / "wp_production" / "build_wp2_closure.py"


def _m():
    spec = importlib.util.spec_from_file_location("closure", CLOSURE)
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(CLOSURE.parent))
    spec.loader.exec_module(mod)
    return mod


def _labels(dec_m_status="limited", dec_m_g="-265093.249150", dec_m_n="2"):
    base = {
        ("DEC", "M_plus"): {"g_ensemble_eh": "-264925.087287", "acceptance_status": "accepted",
                            "n_unique": "2", "limitation_reason": ""},
        ("DEC", "M"): {"g_ensemble_eh": dec_m_g, "acceptance_status": dec_m_status,
                       "n_unique": dec_m_n, "limitation_reason": "rescue_budget_exhausted"},
        ("DME", "M_plus"): {"g_ensemble_eh": "-308.858000", "acceptance_status": "accepted",
                            "n_unique": "2", "limitation_reason": ""},
        ("DME", "M"): {"g_ensemble_eh": "-300.000000", "acceptance_status": "accepted",
                       "n_unique": "2", "limitation_reason": ""},
    }
    return base


def test_limited_state_makes_the_rung_limited_not_computed():
    m = _m()
    row = m.r4_row("DEC vs DME", "DEC", "DME", _labels())
    assert row["status"] == "limited"
    assert "NOT counted as computed" in row["note"]
    assert "rescue_budget_exhausted" in row["note"]   # reason carried verbatim


def test_accepted_state_flips_the_rung_to_computed():
    m = _m()
    row = m.r4_row("DEC vs DME", "DEC", "DME", _labels(dec_m_status="accepted"))
    assert row["status"] == "computed"
    assert row["delta_ev"] != ""


def test_a_new_ensemble_member_changes_the_rung_value():
    """The Boltzmann sum gains the recovery member, so g_ensemble shifts."""
    m = _m()
    before = m.r4_row("DEC vs DME", "DEC", "DME", _labels(dec_m_status="accepted"))
    after = m.r4_row("DEC vs DME", "DEC", "DME",
                     _labels(dec_m_status="accepted", dec_m_g="-265093.310000",
                             dec_m_n="3"))
    assert before["delta_ev"] != after["delta_ev"]
    assert "n_unique M_plus" in after["note"]


def test_provisional_is_kept_distinct_from_limited():
    m = _m()
    row = m.r4_row("DEC vs DME", "DEC", "DME", _labels(dec_m_status="provisional"))
    assert row["status"] == "provisional"
    assert "sampling still in progress" in row["note"]
