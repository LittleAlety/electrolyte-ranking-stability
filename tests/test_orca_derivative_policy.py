import importlib.util
from pathlib import Path

import pytest


MODULE = (Path(__file__).resolve().parents[1] /
          "scripts/wp_production/orca_derivative_policy.py")
spec = importlib.util.spec_from_file_location("orca_derivative_policy", MODULE)
policy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(policy)


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
