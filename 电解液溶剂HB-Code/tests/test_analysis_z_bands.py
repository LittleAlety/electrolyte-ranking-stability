"""Z-band semantics for ``analyze_p1_core_set.layer_stability``.

``config/prereg.yaml`` freezes ``pair_comparison.z_factor.value = 1.0``. The
analysis must therefore report z = 1.0 as the *primary* decision criterion and,
alongside it, the conservative 95% two-sided band z = 1.96. These tests pin the
two bands, the backwards-compatible key names, and the monotonicity that a wider
band can only ever make more pairs unresolved.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
for _directory in (REPO_ROOT / "src", REPO_ROOT / "scripts"):
    if str(_directory) not in sys.path:
        sys.path.insert(0, str(_directory))

from analyze_p1_core_set import layer_stability  # noqa: E402
from electrolyte_ranking import ranking, uncertainty  # noqa: E402

# Six candidates, two layers. The per-molecule difference is the method spread,
# so sigma_ij = |shift_i - shift_j| / sqrt(2). The values are chosen so that one
# pair flips from resolved (z = 1.0) to unresolved (z = 1.96) on the P0 axis and
# another does so on the P1 axis.
LABELS = ["m0", "m1", "m2", "m3", "m4", "m5"]
P0_VALUES = [0.0, 0.6, 1.0, 1.2, 2.2, 2.5]
P1_VALUES = [0.0, 0.3, 1.0, 1.6, 2.2, 2.5]
FRACTION_KEYS = (
    "f_unresolved_p0", "f_unresolved_p1", "f_robust_inv",
    "f_unresolved_p0_z1p96", "f_unresolved_p1_z1p96", "f_robust_inv_z1p96",
)


def _block() -> dict:
    return layer_stability(P0_VALUES, P1_VALUES, LABELS, higher_is_better=True)


def test_reports_primary_and_sensitivity_bands():
    block = _block()
    assert block["z_primary"] == 1.0
    assert block["z_sensitivity"] == 1.96


def test_unsuffixed_keys_stay_backward_compatible():
    block = _block()
    for key in FRACTION_KEYS:
        assert key in block
        assert 0.0 <= block[key] <= 1.0
    assert block["sigma_median_ev"] is not None


def test_unsuffixed_keys_carry_the_primary_band():
    block = _block()
    # If the unsuffixed keys still meant z = 1.96 these pairs would be equal.
    assert block["f_unresolved_p0"] < block["f_unresolved_p0_z1p96"]
    assert block["f_unresolved_p1"] < block["f_unresolved_p1_z1p96"]


@pytest.mark.parametrize("values", [P0_VALUES, P1_VALUES])
def test_wider_band_never_unresolves_fewer_pairs(values):
    sigma = uncertainty.quantify_method_sigma([P0_VALUES, P1_VALUES], ddof=1, stat="std")
    diff = ranking.pair_differences(values)
    fractions = [
        ranking.unresolved_pair_fraction(ranking.resolved_mask(diff, sigma, z=z))
        for z in (0.0, 0.5, 1.0, 1.5, 1.96, 3.0, 5.0)
    ]
    assert fractions == sorted(fractions)
