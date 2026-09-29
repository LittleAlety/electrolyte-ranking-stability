"""Tests for electrolyte_ranking.uncertainty (v2 sections 7.1, 9.1, 12, 13.3)."""
import math
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from electrolyte_ranking.ranking import kendall_tau_b  # noqa: E402
from electrolyte_ranking.uncertainty import (  # noqa: E402
    bootstrap_ci,
    bootstrap_statistic,
    bootstrap_tau_b_ci,
    conditional_shift,
    conditional_shift_prediction,
    delta_learning_shift,
    quantify_method_sigma,
)


# --------------------------------------------------------------------------- #
# Generic bootstrap CI (v2 §13.3)
# --------------------------------------------------------------------------- #
def test_bootstrap_ci_covers_value_and_is_reproducible():
    rng = np.random.default_rng(123)
    data = rng.normal(0.0, 1.0, 300)
    values_fn = bootstrap_statistic(lambda x: float(np.mean(x)), data)

    lo, hi = bootstrap_ci(values_fn, n_boot=2000, seed=7, alpha=0.05)
    assert lo < data.mean() < hi  # interval covers the sample estimate
    assert 0.0 <= 1.0 - 0.05  # sanity on the nominal level

    # identical seed -> identical interval (reproducible)
    assert bootstrap_ci(values_fn, 2000, 7, 0.05) == (lo, hi)
    # a different seed moves the bounds
    assert bootstrap_ci(values_fn, 2000, 8, 0.05) != (lo, hi)


def test_bootstrap_ci_alpha_controls_width():
    rng = np.random.default_rng(0)
    data = rng.normal(0.0, 1.0, 200)
    values_fn = bootstrap_statistic(lambda x: float(np.mean(x)), data)

    lo90, hi90 = bootstrap_ci(values_fn, 2000, 1, 0.10)
    lo99, hi99 = bootstrap_ci(values_fn, 2000, 1, 0.01)
    assert (hi99 - lo99) > (hi90 - lo90)


def test_bootstrap_ci_rejects_invalid_arguments():
    with pytest.raises(ValueError):
        bootstrap_ci(lambda rng: 0.0, n_boot=10, seed=0, alpha=1.5)
    with pytest.raises(ValueError):
        bootstrap_ci(lambda rng: 0.0, n_boot=0, seed=0, alpha=0.05)


def test_bootstrap_tau_b_ci_covers_point_estimate_and_is_reproducible():
    rng = np.random.default_rng(42)
    a = rng.normal(size=80)
    b = 0.6 * a + rng.normal(size=80)
    point = kendall_tau_b(a, b)

    lo, hi = bootstrap_tau_b_ci(a, b, n_boot=1000, seed=11, alpha=0.05)
    assert lo <= point <= hi
    assert -1.0 <= lo <= hi <= 1.0
    assert bootstrap_tau_b_ci(a, b, 1000, 11, 0.05) == (lo, hi)


# --------------------------------------------------------------------------- #
# Method / conformer uncertainty sigma_ij (v2 §7.1, §9.1)
# --------------------------------------------------------------------------- #
def test_quantify_method_sigma_zero_when_methods_agree():
    vals = np.array([[1.0, 2.0, 3.0, 4.0], [1.0, 2.0, 3.0, 4.0]])
    sigma = quantify_method_sigma(vals)
    assert sigma.shape == (4, 4)
    assert np.allclose(sigma, 0.0)


def test_quantify_method_sigma_matches_hand_value():
    vals = np.array([[1.0, 2.0, 3.0], [1.1, 2.0, 3.1]])
    sigma = quantify_method_sigma(vals)
    # pair (0,1) differences are {-1.0, -0.9}; sample std = 0.1 / sqrt(2)
    assert sigma[0, 1] == pytest.approx(0.1 / math.sqrt(2.0))
    assert np.allclose(sigma, sigma.T)
    assert np.allclose(np.diag(sigma), 0.0)
    assert np.all(sigma >= 0.0)


def test_quantify_method_sigma_flattens_methods_and_conformers():
    methods = np.array([[[1.0, 2.0], [1.0, 2.0]], [[3.0, 2.0], [3.0, 2.0]]])
    sigma = quantify_method_sigma(methods)
    assert sigma.shape == (2, 2)
    assert sigma[0, 1] > 0.0  # methods disagree on pair (0, 1)


def test_quantify_method_sigma_stat_options():
    vals = np.array([[1.0, 2.0], [3.0, 2.0]])
    assert quantify_method_sigma(vals, stat="range")[0, 1] == pytest.approx(1.0)
    assert quantify_method_sigma(vals, stat="mad")[0, 1] == pytest.approx(1.0)
    with pytest.raises(ValueError):
        quantify_method_sigma(vals, stat="nope")


# --------------------------------------------------------------------------- #
# Delta-learning / conditional shift definitions (v2 §12)
# --------------------------------------------------------------------------- #
def test_delta_learning_shift_definition():
    target = np.array([5.0, 6.0])
    low = np.array([4.0, 4.5])
    assert np.allclose(delta_learning_shift(target, low), [1.0, 1.5])


def test_conditional_shift_and_prediction_roundtrip():
    c0 = np.array([1.0, 2.0])
    c1 = np.array([1.5, 1.0])
    delta = conditional_shift(c1, c0)
    assert np.allclose(delta, [0.5, -1.0])
    # P_hat(C1) = P(C0) + Delta_hat  recovers C1 exactly when Delta is exact
    assert np.allclose(conditional_shift_prediction(c0, delta), c1)