"""Machine-enforced ORCA derivative policy for WP2 production inputs.

``NumGrad`` is a numerical *first* derivative and is forbidden. The frequency
Hessian keyword was ``NumFreq`` (numerical finite difference of analytical
gradients) up to protocol v1.2; the 2026-10-17 amendment (v1.3) switched it to
``AnFreq`` (analytical Hessian) cohort-wide.

Why the switch is not a per-leg convenience
-------------------------------------------
A 60/60 paired audit on identical converged geometries found 54 legs agreeing
between the two Hessian algorithms and 6 disagreeing -- and every disagreement
was a leg whose NumFreq imaginary mode vanished or shrank under AnFreq.  A DX
step-size probe on one of them (AN/LiM_2plus) gave -127.20 cm**-1 at DX=0.005
and -57.21 cm**-1 at DX=0.010 while AnFreq gave zero: a genuine saddle does not
halve its imaginary frequency when the finite-difference step changes, so those
modes were discretisation noise.  The amendment is therefore global, per plan
v1.2 item 4, and the whole cohort is recomputed with one algorithm.
"""
from __future__ import annotations

import re


PRODUCTION_FUNCTIONAL = "wb97x-d4"
OPTIMIZATION_RANK = {"normal": 0, "tight": 1, "verytight": 2}
# Frequency Hessian keyword per protocol v1.3 (was NumFreq in v1.2).
PRODUCTION_FREQUENCY_KEYWORD = "anfreq"
SUPERSEDED_FREQUENCY_KEYWORD = "numfreq"
VERY_TIGHT_THRESHOLDS = {
    "TolE_Eh": "2e-7",
    "TolMaxG_Eh_per_Bohr": "3e-5",
    "TolRMSG_Eh_per_Bohr": "8e-6",
    "TolMaxD_Bohr": "2e-4",
    "TolRMSD_Bohr": "1e-4",
}


def optimization_tier(text: str) -> str:
    tokens = [token for line in text.splitlines() if line.lstrip().startswith("!")
              for token in line.strip()[1:].lower().split()]
    selected = [name for name, keyword in (("tight", "tightopt"),
                                            ("verytight", "verytightopt"))
                if keyword in tokens]
    if len(selected) > 1:
        raise ValueError("conflicting geometry convergence keywords")
    return selected[0] if selected else "normal"


def require_analytic_gradient(text: str, *, require_opt: bool = True,
                              minimum_optimization_tier: str | None = None) -> None:
    """Reject an ORCA input that could request numerical first derivatives."""
    keyword_lines = [line.strip() for line in text.splitlines()
                     if line.lstrip().startswith("!")]
    if len(keyword_lines) != 1:
        raise ValueError("analytic-gradient policy requires exactly one ORCA keyword line")
    tokens = keyword_lines[0][1:].lower().split()
    if PRODUCTION_FUNCTIONAL not in tokens:
        raise ValueError("analytic-gradient policy only covers frozen wB97X-D4 production")
    if "numgrad" in tokens or re.search(r"(?im)^\s*%numgrad\b", text):
        raise ValueError("NumGrad is forbidden: WP2 requires analytical first derivatives")
    if require_opt and "opt" not in tokens:
        raise ValueError("production geometry input must request Opt")
    tier = optimization_tier(text)
    if minimum_optimization_tier is not None:
        if minimum_optimization_tier not in OPTIMIZATION_RANK:
            raise ValueError("unknown minimum optimization tier")
        if OPTIMIZATION_RANK[tier] < OPTIMIZATION_RANK[minimum_optimization_tier]:
            raise ValueError("geometry convergence must be %s or stricter" %
                             minimum_optimization_tier)


def require_frequency_keyword(text: str, *, allow_superseded: bool = False) -> str:
    """Return the frequency keyword, enforcing the frozen protocol version.

    Under v1.3 a new production input must request ``AnFreq``.  ``NumFreq``
    inputs are still ACCEPTED when ``allow_superseded`` is set, because the
    already-finished v1.2 legs must stay readable as Hessian-method sensitivity
    evidence -- they are superseded for label purposes, not deleted.
    """
    tokens = [token for line in text.splitlines() if line.lstrip().startswith("!")
              for token in line.strip()[1:].lower().split()]
    if PRODUCTION_FREQUENCY_KEYWORD in tokens:
        return PRODUCTION_FREQUENCY_KEYWORD
    if SUPERSEDED_FREQUENCY_KEYWORD in tokens:
        if allow_superseded:
            return SUPERSEDED_FREQUENCY_KEYWORD
        raise ValueError(
            "NumFreq was superseded by protocol v1.3 (analytical Hessian); new "
            "production inputs must request AnFreq")
    raise ValueError("production input must request a frequency calculation")


def derivative_metadata() -> dict[str, str]:
    return {
        "geometry_gradient": "analytic",
        "forbidden_first_derivative_keyword": "NumGrad",
        "frequency_hessian": "analytical_hessian",
        "frequency_keyword": "AnFreq",
        "superseded_frequency_keyword": "NumFreq",
        "superseded_frequency_hessian": "numerical_finite_difference_of_analytic_gradients",
        "protocol_version": "1.3",
        "anfreq_policy": ("adopted cohort-wide on 2026-10-17 after a 60/60 paired audit and a "
                          "DX step-size probe showed the NumFreq imaginary modes were "
                          "finite-difference noise"),
        "new_geometry_optimization": "VeryTightOpt",
        "legacy_tightopt_policy": "retain only if scientific QC has zero imaginary modes",
        "verytightopt_thresholds": VERY_TIGHT_THRESHOLDS,
    }
