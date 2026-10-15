"""Machine-enforced ORCA derivative policy for WP2 production inputs.

``NumGrad`` is a numerical *first* derivative and is forbidden. ``NumFreq`` is
retained by the frozen protocol: for the supported DFT method it forms a
numerical Hessian from analytical gradients. Changing it to ``AnFreq`` is a
separate second-derivative/protocol change and requires an explicit, recorded
compatibility study.
"""
from __future__ import annotations

import re


PRODUCTION_FUNCTIONAL = "wb97x-d4"
OPTIMIZATION_RANK = {"normal": 0, "tight": 1, "verytight": 2}
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


def derivative_metadata() -> dict[str, str]:
    return {
        "geometry_gradient": "analytic",
        "forbidden_first_derivative_keyword": "NumGrad",
        "frequency_hessian": "numerical_finite_difference_of_analytic_gradients",
        "frequency_keyword": "NumFreq",
        "anfreq_policy": "protocol_change_requires_recorded_compatibility_study",
        "new_geometry_optimization": "VeryTightOpt",
        "legacy_tightopt_policy": "retain only if scientific QC has zero imaginary modes",
        "verytightopt_thresholds": VERY_TIGHT_THRESHOLDS,
    }
