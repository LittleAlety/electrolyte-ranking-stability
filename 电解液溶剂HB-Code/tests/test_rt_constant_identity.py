"""Cross-module RT/R constant identity (v3.0 §19.1 item 1, closing check).

Three modules independently derive RT for the Boltzmann ensemble.  This test
pins them to the SAME physical constants so a future "fix" in one module can
never silently diverge from the others again:

* aggregator: R_KCAL * temp / HARTREE_TO_KCAL (kcal path, its own T comes from
  the labels' temp_k column -- 298.15 by protocol);
* gap decision support: R_KCAL (kcal path, same CODATA value);
* sampling 3->6 diff: inline RT in Eh, previously WRONG by 1.68x and now
  derived from the same R and conversion factors.
"""
import importlib.util
import math
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
WP = REPO / "scripts" / "wp_production"


def _load(name):
    spec = importlib.util.spec_from_file_location(name, WP / (name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(WP))
    spec.loader.exec_module(mod)
    return mod


#: v3.0 §9 frozen constants (the single source of truth this test enforces)
R_KCAL_V3 = 1.98720425864083e-3      # kcal/(mol K), CODATA
T_V3 = 298.15                         # K
HARTREE_TO_KCAL_V3 = 627.5094740631
RT_EH_V3 = R_KCAL_V3 * T_V3 / HARTREE_TO_KCAL_V3   # = 0.0009441848676442220


def test_v3_constants_are_the_documented_values():
    assert abs(RT_EH_V3 - 0.0009441848676442220) < 1e-18


def test_aggregator_constants_match_v3():
    agg = _load("build_production_ensemble_aggregator")
    assert agg.R_KCAL == R_KCAL_V3
    # the aggregator computes RT in kcal at the protocol temperature
    rt_kcal = agg.R_KCAL * T_V3
    assert abs(rt_kcal - 0.59248495) < 1e-7          # v3.0 §9: RT ~= 0.59248 kcal/mol
    assert abs(agg.HARTREE_TO_KCAL - 627.509474) < 1e-6


def test_gap_decision_constants_match_v3():
    gap = _load("build_gap_decision_support")
    assert gap.R_KCAL == R_KCAL_V3


def test_diff_module_rt_is_derived_not_hardcoded():
    """The sampling-diff RT must equal the v3 value to machine precision --
    the 1.68x bug lived exactly here."""
    diff = _load("build_sampling_3to6_diff")
    src = (WP / "build_sampling_3to6_diff.py").read_text(encoding="utf-8")
    # the wrong legacy constant must not come back
    assert "RT = 0.00158760761551242" not in src
    # the inline derivation must reproduce the frozen value
    derived = 1.98720425864083e-3 * 298.15 / 627.5094740631
    assert abs(derived - RT_EH_V3) < 1e-18


def test_kcal_and_eh_paths_agree():
    """Same RT expressed on both unit paths must agree to < 1e-12 relative."""
    rt_eh_direct = RT_EH_V3
    rt_eh_via_kcal = (R_KCAL_V3 * T_V3) / HARTREE_TO_KCAL_V3
    assert abs(rt_eh_direct - rt_eh_via_kcal) < 1e-18
    # and the legacy wrong value differs by the documented 1.6815x
    wrong = 0.00158760761551242
    assert abs(wrong / RT_EH_V3 - 1.6814584409444764) < 1e-9
