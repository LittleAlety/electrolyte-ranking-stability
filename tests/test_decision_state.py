"""Tests for electrolyte_ranking.decision_state (R13 decision-state vocabulary).

Expected values are hand-computed from the frozen assignment rule in
``config/scientific_definitions.yaml`` (``decision_state``); nothing depends on
a magic constant.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from electrolyte_ranking.decision_state import (  # noqa: E402
    DEFAULT_Z_BANDS,
    ROBUST_INVERSION,
    STABLE,
    UNRESOLVED,
    WEAK_SHIFT,
    decision_state_counts,
    decision_state_fractions,
    decision_states,
    resolution_curve,
)


def _labels(result):
    return list(result["labels"])


def test_all_pairs_robust_inversion_when_the_two_models_swap_order():
    a = [3.0, 1.0, 2.0]
    b = [1.0, 3.0, 2.0]
    zeros = [0.0, 0.0, 0.0]
    result = decision_states(a, b, zeros, zeros)
    assert result["counts"]["n_pairs"] == 3
    assert all(label == ROBUST_INVERSION for label in _labels(result))
    assert result["fractions"][ROBUST_INVERSION] == pytest.approx(1.0)


def test_identical_models_are_all_stable():
    a = [1.0, 2.0, 3.0]
    zeros = [0.0, 0.0, 0.0]
    result = decision_states(a, a, zeros, zeros)
    assert all(label == STABLE for label in _labels(result))
    assert decision_state_fractions(result["matrix"])[STABLE] == pytest.approx(1.0)


def test_unresolved_dominates_when_one_model_never_clears_its_threshold():
    a = [1.0, 2.0, 3.0]
    b = [1.0, 2.0, 3.0]
    zeros = [0.0, 0.0, 0.0]
    wide = [10.0, 10.0, 10.0]
    result = decision_states(a, b, zeros, wide)
    assert all(label == UNRESOLVED for label in _labels(result))
    assert result["fractions"][ROBUST_INVERSION] == 0.0


def test_mixed_states_and_null_inversion_are_not_read_as_stability():
    a = [1.0, 2.0, 3.0]
    b = [1.0, 2.0, 5.0]
    sigma_a = [0.0, 0.0, 0.0]
    sigma_b = [0.0, 2.0, 1.0]
    result = decision_states(a, b, sigma_a, sigma_b)
    counts = result["counts"]
    # (0,1): |dB|=1 < 2 -> unresolved; (0,2) and (1,2): resolved, same sign.
    assert counts[UNRESOLVED] == 1
    assert counts[STABLE] == 2
    assert counts[ROBUST_INVERSION] == 0
    # A zero inversion count here means "not resolvable", not "stable".
    assert result["fractions"][UNRESOLVED] == pytest.approx(1.0 / 3.0)


def test_weak_shift_band_is_descriptive_only():
    a = [1.0, 2.0]
    b = [1.0, 2.5]
    sigma = [0.4, 0.4]  # pair threshold 0.8; ratios 1.25 (A) and 1.875 (B)
    # Baseline: both resolved, same sign -> STABLE.
    assert decision_states(a, b, sigma, sigma)["labels"] == [STABLE]
    # A descriptive band tags the pair whose smaller ratio sits near threshold.
    tagged = decision_states(a, b, sigma, sigma, weak_shift_band=0.5)
    assert tagged["labels"] == [WEAK_SHIFT]
    assert tagged["fractions"][WEAK_SHIFT] == pytest.approx(1.0)


def test_resolution_curve_uses_every_frozen_band():
    diff = np.array([[0.0, -1.0, -2.0], [1.0, 0.0, -1.0], [2.0, 1.0, 0.0]])
    sigma = np.zeros((3, 3))
    sigma[0, 1] = sigma[1, 0] = 1.0
    sigma[0, 2] = sigma[2, 0] = 1.0
    sigma[1, 2] = sigma[2, 1] = 1.0
    curve = resolution_curve(diff, sigma)
    assert curve["z_bands"] == [float(z) for z in DEFAULT_Z_BANDS]
    by_z = {row["z"]: row for row in curve["rows"]}
    # Pair gaps are |1|, |2|, |1| against a pair threshold of z * 1.0.
    assert by_z[1.0]["f_unresolved"] == pytest.approx(0.0)          # all >= 1
    assert by_z[1.645]["f_unresolved"] == pytest.approx(2.0 / 3.0)  # the two |1| pairs
    assert by_z[2.576]["f_unresolved"] == pytest.approx(1.0)        # even |2| falls below
    fractions = [row["f_unresolved"] for row in curve["rows"]]
    assert fractions == sorted(fractions)


def test_counts_rejects_non_square_matrices():
    with pytest.raises(ValueError):
        decision_state_counts(np.full((2, 3), "", dtype=object))
