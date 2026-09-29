"""Tests for electrolyte_ranking.ranking (v2 sections 9 and 10).

Every expected value is either an exact hand-computation or a boundary
condition from the v2 plan; nothing here depends on a magic constant.
"""
import math
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from electrolyte_ranking.ranking import (  # noqa: E402
    jaccard_at_k,
    kendall_tau_b,
    pair_differences,
    probabilistic_pair_ordering,
    resolved_mask,
    robust_inversion_fraction,
    selection_regret,
    spearman_rho,
    threshold_decision_error,
    top_k_overlap,
    unresolved_pair_fraction,
)


# --------------------------------------------------------------------------- #
# v2 §9.1 -- pair differences and the resolved / unresolved criterion
# --------------------------------------------------------------------------- #
def test_pair_differences_shape_values_antisymmetry():
    d = pair_differences([3.0, 1.0, 2.0])
    assert d.shape == (3, 3)
    assert np.allclose(np.diag(d), 0.0)
    assert np.allclose(d, -d.T)
    assert d[0, 1] == pytest.approx(2.0)   # P_0 - P_1
    assert d[2, 0] == pytest.approx(-1.0)  # P_2 - P_0


def test_pair_differences_stacked_models():
    d = pair_differences([[1.0, 2.0], [5.0, 3.0]])
    assert d.shape == (2, 2, 2)
    assert d[0, 0, 1] == pytest.approx(-1.0)  # model 0: P_0 - P_1
    assert d[0, 1, 0] == pytest.approx(1.0)
    assert d[1, 0, 1] == pytest.approx(2.0)   # model 1: P_0 - P_1
    assert d[1, 1, 0] == pytest.approx(-2.0)


def test_resolved_mask_thresholds_and_diagonal():
    d = pair_differences([1.0, 1.05, 3.0])
    sigma = np.full((3, 3), 0.1)
    mask = resolved_mask(d, sigma, z=2.0)  # threshold = 0.2

    assert mask.dtype == bool
    assert not np.any(np.diag(mask))
    assert not mask[0, 1] and not mask[1, 0]  # |0.05| < 0.2 -> unresolved
    assert mask[0, 2] and mask[2, 0]
    assert mask[1, 2]
    # one unresolved pair out of C(3, 2) = 3
    assert unresolved_pair_fraction(mask) == pytest.approx(1 / 3)


def test_resolved_mask_exact_tie_and_tolerance():
    sigma = np.zeros((3, 3))
    tie = pair_differences([1.0, 1.0, 5.0])
    mask = resolved_mask(tie, sigma, z=2.0)
    assert not mask[0, 1]  # exact tie carries no ordering
    assert mask[0, 2]

    # a pre-registered tolerance can also declare a small separation unresolved
    small = pair_differences([1.0, 1.5, 5.0])
    mask2 = resolved_mask(small, sigma, z=2.0, tolerance=1.0)
    assert not mask2[0, 1]
    assert mask2[0, 2]


def test_resolved_mask_rejects_negative_sigma():
    with pytest.raises(ValueError):
        resolved_mask(np.zeros((2, 2)), np.full((2, 2), -1.0), z=2.0)


# --------------------------------------------------------------------------- #
# v2 §9.2 -- unresolved fraction and robust inversion
# --------------------------------------------------------------------------- #
def test_unresolved_fraction_denominator_is_c_n_2():
    mask = np.ones((4, 4), dtype=bool)
    np.fill_diagonal(mask, False)
    mask[0, 1] = mask[1, 0] = False
    mask[2, 3] = mask[3, 2] = False
    assert unresolved_pair_fraction(mask) == pytest.approx(2 / 6)


def test_unresolved_fraction_all_resolved_is_zero():
    mask = np.ones((5, 5), dtype=bool)
    np.fill_diagonal(mask, False)
    assert unresolved_pair_fraction(mask) == 0.0


def test_robust_inversion_requires_both_resolved_and_opposite_sign():
    d_a = pair_differences([3.0, 2.0, 1.0])  # pair signs: +, +, +
    d_b = pair_differences([3.0, 1.0, 2.0])  # pair signs: +, +, - (only (1,2) flips)
    sigma = np.zeros((3, 3))
    mask_a = resolved_mask(d_a, sigma, z=2.0)
    mask_b = resolved_mask(d_b, sigma, z=2.0)
    assert robust_inversion_fraction(d_a, d_b, mask_a, mask_b) == pytest.approx(1 / 3)


def test_robust_inversion_excludes_pairs_unresolved_in_one_model():
    d_a = pair_differences([3.0, 2.0, 1.0])
    d_b = pair_differences([3.0, 1.0, 2.0])
    sigma_a = np.zeros((3, 3))
    sigma_a[1, 2] = sigma_a[2, 1] = 0.6  # |ΔP|=1 < z*σ=1.2 -> unresolved in A
    mask_a = resolved_mask(d_a, sigma_a, z=2.0)
    mask_b = resolved_mask(d_b, np.zeros((3, 3)), z=2.0)

    assert not mask_a[1, 2] and mask_b[1, 2]
    # the only sign-flipping pair is unresolved in A: numerator 0, denominator 2
    assert robust_inversion_fraction(d_a, d_b, mask_a, mask_b) == 0.0


def test_robust_inversion_zero_when_signs_agree():
    d_a = pair_differences([3.0, 2.0, 1.0])
    d_b = pair_differences([30.0, 20.0, 10.0])
    sigma = np.zeros((3, 3))
    mask_a = resolved_mask(d_a, sigma, z=2.0)
    mask_b = resolved_mask(d_b, sigma, z=2.0)
    assert robust_inversion_fraction(d_a, d_b, mask_a, mask_b) == 0.0


def test_robust_inversion_zero_when_nothing_resolved_in_both():
    d = pair_differences([1.0, 1.0, 1.0])
    mask = resolved_mask(d, np.zeros((3, 3)), z=2.0)
    assert robust_inversion_fraction(d, d, mask, mask) == 0.0


# --------------------------------------------------------------------------- #
# v2 §9.3 -- Kendall tau_b and Spearman rho
# --------------------------------------------------------------------------- #
def test_kendall_tau_b_identical_ordering_is_one():
    a = [1.0, 2.0, 3.0, 4.0]
    assert kendall_tau_b(a, a) == pytest.approx(1.0)


def test_kendall_tau_b_reversed_ordering_is_minus_one():
    assert kendall_tau_b([1.0, 2.0, 3.0], [3.0, 2.0, 1.0]) == pytest.approx(-1.0)


def test_kendall_tau_b_ties_hand_computed():
    # a = [1, 2, 2], b = [3, 4, 5]:
    # concordant pairs (0,1) and (0,2); pair (1,2) tied in a only.
    # tau_b = (C - D) / sqrt((C+D+n_a)(C+D+n_b)) = 2 / sqrt(3*2)
    tau = kendall_tau_b([1.0, 2.0, 2.0], [3.0, 4.0, 5.0])
    assert tau == pytest.approx(2.0 / math.sqrt(6.0))


def test_kendall_tau_b_atol_merges_near_ties():
    a = [1.0, 2.0, 3.0]
    b = [1.0, 1.05, 3.0]
    assert kendall_tau_b(a, b) == pytest.approx(1.0)
    assert kendall_tau_b(a, b, atol=0.1) == pytest.approx(2.0 / math.sqrt(6.0))


def test_kendall_tau_b_degenerate_returns_nan():
    assert math.isnan(kendall_tau_b([1.0, 2.0, 3.0], [5.0, 5.0, 5.0]))


def test_spearman_monotone_and_reversed():
    assert spearman_rho([1, 2, 3, 4], [10, 20, 30, 40]) == pytest.approx(1.0)
    assert spearman_rho([1, 2, 3, 4], [4, 3, 2, 1]) == pytest.approx(-1.0)


def test_spearman_handles_ties_via_midranks():
    rho = spearman_rho([1, 2, 2, 3], [1, 2, 2, 3])
    assert 0.0 < rho <= 1.0


# --------------------------------------------------------------------------- #
# v2 §10.1 -- Top-k overlap and Jaccard
# --------------------------------------------------------------------------- #
def test_top_k_overlap_boundaries():
    a = [1.0, 2.0, 3.0, 4.0]
    b = [4.0, 3.0, 2.0, 1.0]
    assert top_k_overlap(a, b, 0) == 0.0          # empty selection
    assert top_k_overlap(a, b, 1) == 0.0          # argmax differs
    assert top_k_overlap(a, b, 4) == pytest.approx(1.0)  # k = N selects all
    assert top_k_overlap(a, a, 4) == pytest.approx(1.0)
    assert top_k_overlap(a, b, 2) == 0.0


def test_top_k_overlap_ratio_and_direction():
    a = [1.0, 2.0, 3.0, 4.0]
    b = [1.0, 2.0, 4.0, 3.0]
    assert top_k_overlap(a, b, 1, higher_is_better=True) == 0.0
    assert top_k_overlap(a, b, 1, higher_is_better=False) == pytest.approx(1.0)
    assert top_k_overlap(a, a, 0.5) == pytest.approx(1.0)  # ratio -> k = 2


def test_jaccard_at_k():
    a = [1.0, 2.0, 3.0, 4.0]
    b = [4.0, 3.0, 2.0, 1.0]
    assert jaccard_at_k(a, b, 0) == 0.0
    assert jaccard_at_k(a, b, 4) == pytest.approx(1.0)
    assert jaccard_at_k(a, b, 2) == 0.0
    b2 = [1.0, 3.0, 4.0, 2.0]  # top-2 = {1, 2}; a top-2 = {2, 3}
    assert jaccard_at_k(a, b2, 2) == pytest.approx(1 / 3)


# --------------------------------------------------------------------------- #
# v2 §10.2 -- selection regret
# --------------------------------------------------------------------------- #
def test_selection_regret_sign_and_zero():
    target = [10.0, 9.0, 8.0, 7.0]
    cheap = [9.0, 10.0, 8.0, 7.0]
    regret = selection_regret(target, cheap, 1)
    assert regret == pytest.approx(1.0)
    assert regret >= 0.0
    assert selection_regret(target, target, 1) == pytest.approx(0.0)
    assert selection_regret(target, cheap, 2) == pytest.approx(0.0)  # top-2 agree


def test_selection_regret_lower_is_better_direction():
    target = [1.0, 2.0, 3.0, 4.0]
    cheap = [2.0, 1.0, 3.0, 4.0]
    regret = selection_regret(target, cheap, 1, higher_is_better=False)
    assert regret == pytest.approx(1.0)
    assert regret >= 0.0


# --------------------------------------------------------------------------- #
# v2 §10.3 -- threshold-based decision error
# --------------------------------------------------------------------------- #
def test_threshold_decision_error():
    target = [1.0, 2.0, 3.0, 4.0]
    cheap = [1.0, 2.0, 3.0, 4.5]
    assert threshold_decision_error(target, cheap, 3.5) == 0.0
    assert threshold_decision_error(target, cheap, 4.2) == pytest.approx(0.25)
    assert threshold_decision_error(target, target, 2.5) == 0.0


# --------------------------------------------------------------------------- #
# v2 §9.4 -- probabilistic pair ordering
# --------------------------------------------------------------------------- #
def test_probabilistic_pair_ordering_counts_strict_greater():
    samples = np.array([[1.0, 2.0], [2.0, 1.0], [1.0, 3.0]])
    p = probabilistic_pair_ordering(samples)
    assert p.shape == (2, 2)
    assert p[0, 1] == pytest.approx(1 / 3)
    assert p[1, 0] == pytest.approx(2 / 3)
    assert np.allclose(np.diag(p), 0.0)


def test_probabilistic_pair_ordering_strong_evidence():
    rng = np.random.default_rng(0)
    n = 200
    samples = np.column_stack([rng.normal(0.0, 1.0, n), rng.normal(5.0, 1.0, n)])
    p = probabilistic_pair_ordering(samples)
    assert p[1, 0] > 0.9  # candidate 1 clearly above candidate 0
    assert p[0, 1] < 0.1