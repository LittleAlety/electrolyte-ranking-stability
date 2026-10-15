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


def test_frozen_numfreq_uses_analytic_first_derivatives():
    policy.require_analytic_gradient(BASE)
    assert policy.derivative_metadata()["geometry_gradient"] == "analytic"
    assert policy.derivative_metadata()["frequency_hessian"].startswith("numerical_finite_difference")


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
