import importlib.util
import json
from pathlib import Path

import pytest


MODULE = (Path(__file__).resolve().parents[1] /
          "scripts/wp_production/orca_derivative_policy.py")
spec = importlib.util.spec_from_file_location("orca_derivative_policy", MODULE)
policy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(policy)

CONTRACT = (Path(__file__).resolve().parents[1] / "docs" / "handoffs"
            / "four_state_recovery_20261023" / "recovery_contract.json")

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"

#: The five VeryTightOpt thresholds, written out as literals *on purpose*: the
#: plan forbids relaxing them, so an edit here has to be deliberate and visible.
FROZEN_FIVE = {
    "TolE_Eh": "2e-7",
    "TolMaxG_Eh_per_Bohr": "3e-5",
    "TolRMSG_Eh_per_Bohr": "8e-6",
    "TolMaxD_Bohr": "2e-4",
    "TolRMSD_Bohr": "1e-4",
}


BASE = """! wB97X-D4 def2-TZVPD Opt NumFreq SMD(acetonitrile) TightOpt TightSCF SlowConv
%maxcore 2000
%pal nprocs 4 end
* xyzfile 0 1 geom.xyz
"""

# Protocol v1.3 (2026-10-17) moved the frequency Hessian from the numerical
# NumFreq to the analytical AnFreq cohort-wide.
CURRENT = """! wB97X-D4 def2-TZVPD Opt AnFreq SMD(acetonitrile) VeryTightOpt TightSCF SlowConv
%maxcore 2000
%pal nprocs 4 end
* xyzfile 0 1 geom.xyz
"""


def test_frozen_frequency_hessian_is_analytical_under_v13():
    """v1.3: the frozen Hessian is AnFreq; NumFreq is recorded as superseded."""
    policy.require_analytic_gradient(CURRENT)
    meta = policy.derivative_metadata()
    assert meta["geometry_gradient"] == "analytic"
    assert meta["frequency_hessian"] == "analytical_hessian"
    assert meta["frequency_keyword"] == "AnFreq"
    assert meta["superseded_frequency_keyword"] == "NumFreq"
    assert meta["protocol_version"] == "1.3"


def test_analytic_first_derivative_rule_survives_the_hessian_amendment():
    """The amendment changed the SECOND derivative only: NumGrad stays banned."""
    policy.require_analytic_gradient(BASE)
    assert policy.derivative_metadata()["forbidden_first_derivative_keyword"] == "NumGrad"


def test_new_inputs_must_use_anfreq_but_superseded_legs_stay_readable():
    """New production inputs need AnFreq; v1.2 NumFreq legs remain readable."""
    assert policy.require_frequency_keyword(CURRENT) == "anfreq"
    with pytest.raises(ValueError, match="superseded by protocol v1.3"):
        policy.require_frequency_keyword(BASE)
    assert policy.require_frequency_keyword(BASE, allow_superseded=True) == "numfreq"
    with pytest.raises(ValueError, match="must request a frequency calculation"):
        policy.require_frequency_keyword("! wB97X-D4 def2-TZVPD Opt SMD(acetonitrile)\n")


def test_new_jobs_require_very_tight_geometry_convergence():
    with pytest.raises(ValueError, match="verytight"):
        policy.require_analytic_gradient(BASE, minimum_optimization_tier="verytight")
    upgraded = BASE.replace("TightOpt", "VeryTightOpt")
    policy.require_analytic_gradient(upgraded, minimum_optimization_tier="verytight")
    assert policy.optimization_tier(upgraded) == "verytight"


@pytest.mark.parametrize("bad", [
    BASE.replace("NumFreq", "NumFreq NumGrad"),
    BASE + "%numgrad\n  CentralDiff true\nend\n",
])
def test_numerical_gradient_is_forbidden(bad):
    with pytest.raises(ValueError, match="NumGrad"):
        policy.require_analytic_gradient(bad)


def test_unfrozen_method_is_not_silently_accepted():
    with pytest.raises(ValueError, match="only covers"):
        policy.require_analytic_gradient(BASE.replace("wB97X-D4", "DLPNO-CCSD(T)"))


# --------------------------------------------------------------------------- #
# the five frozen VeryTightOpt thresholds and their single source of truth
# --------------------------------------------------------------------------- #


def test_the_five_optimization_thresholds_are_the_frozen_literals():
    """Pinned as literals: relaxing them is a red line, so it must be deliberate."""
    assert policy.VERY_TIGHT_THRESHOLDS == FROZEN_FIVE


def test_the_code_thresholds_and_the_frozen_campaign_contract_agree():
    """No drifting copy: the code constant and the campaign contract must agree.

    Measured 2026-10-24: NOTHING in tests/ referenced either
    ``recovery_contract`` or ``VERY_TIGHT_THRESHOLDS``, so the five numbers lived
    in two authoritative places with no guard between them -- editing one alone
    would silently make the acceptance gate implement different thresholds from
    the contract it claims to implement.  This test is that missing guard.
    """
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert contract["thresholds"] == policy.VERY_TIGHT_THRESHOLDS, (
        "recovery_contract.json and orca_derivative_policy.VERY_TIGHT_THRESHOLDS "
        "have drifted apart")
    assert contract["thresholds"] == FROZEN_FIVE


def test_the_prose_copies_of_the_thresholds_cannot_drift():
    """Two generators restate the five numbers as protocol prose.

    Those restatements are documentation, not enforcement -- but a drifted one
    would publish a protocol nobody implements.  Rebuild the exact block from
    the frozen literals and require it verbatim in both generators.
    """
    block = ("{TolE_Eh: %s, TolMaxG_Eh_per_Bohr: %s, TolRMSG_Eh_per_Bohr: %s, "
             "TolMaxD_Bohr: %s, TolRMSD_Bohr: %s}"
             % (FROZEN_FIVE["TolE_Eh"], FROZEN_FIVE["TolMaxG_Eh_per_Bohr"],
                FROZEN_FIVE["TolRMSG_Eh_per_Bohr"], FROZEN_FIVE["TolMaxD_Bohr"],
                FROZEN_FIVE["TolRMSD_Bohr"]))
    for name in ("build_physics_completion_batch.py", "wp_production/emit_wp2.py"):
        source = (SCRIPTS / name).read_text(encoding="utf-8")
        assert block in source, (
            "%s restates the five thresholds differently from the frozen "
            "literals: expected %r" % (name, block))
