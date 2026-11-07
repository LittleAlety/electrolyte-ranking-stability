"""R2 unit tests: the synthetic shift model and the phase-diagram artefacts.

The heavy grid is a frozen artefact, so these tests check the *pieces* on tiny
inputs and then check the artefact's own invariants (exact mean invariance, a
monotone std axis, the collinearity story) rather than re-running 1353 cells.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import analyze_sigma_synthetic as m  # noqa: E402

ARTEFACT = REPO_ROOT / "outputs" / "week21" / "sigma_synthetic.json"


# --- the pieces ---------------------------------------------------------------

def test_standardised_draws_have_unit_sample_sd_per_row():
    draws = m.standardised_draws(64, 7, 11)
    assert draws.shape == (64, 7)
    assert np.allclose(draws.mean(axis=1), 0.0, atol=1e-12)
    assert np.allclose(draws.std(axis=1, ddof=1), 1.0, atol=1e-12)


def test_tau_b_batch_matches_the_project_estimator():
    from electrolyte_ranking import ranking

    rng = np.random.default_rng(3)
    target = np.arange(6, dtype=float)
    values = target[None, :] + rng.normal(scale=0.4, size=(5, 6))
    batch = m.tau_b_batch(values, target)
    for index in range(values.shape[0]):
        assert batch[index] == pytest.approx(ranking.kendall_tau_b(values[index], target))


def test_a_pure_constant_shift_cannot_change_anything():
    target = np.arange(8, dtype=float)
    values = target[None, :] + 123.0
    assert m.tau_b_batch(values, target)[0] == pytest.approx(1.0)
    block = m.decision_batch(values, target, k=2, z=1.0)
    assert block["f_unresolved"][0] == 0.0
    assert block["f_robust_inv"][0] == 0.0
    assert block["overlap"][0] == 1.0


def test_large_dispersion_wrecks_the_ranking():
    target = np.arange(10, dtype=float)
    rng = np.random.default_rng(5)
    draws = m.standardised_draws(400, 10, 7)
    low = m.tau_b_batch(target[None, :] + 0.1 * draws, target).mean()
    high = m.tau_b_batch(target[None, :] + 3.0 * draws, target).mean()
    assert low > high
    assert high < 0.6


def test_boundary_finds_the_first_crossing():
    points = [{"std_ev": 0.0, "tau_b_mean": 0.99}, {"std_ev": 0.5, "tau_b_mean": 0.70}]
    assert m.boundary(points, 0.8) == 0.5
    assert m.boundary(points, 0.1) is None


# --- the frozen artefact ------------------------------------------------------

def test_artefact_exists_and_is_self_consistent():
    data = json.loads(ARTEFACT.read_text(encoding="utf-8"))
    assert data["stage"] == "R2-synthetic-phase-diagram"
    assert data["grid"]["replicates_per_cell"] == m.GRID_REPLICATES
    for axis in ("oxidation", "reduction"):
        block = data["grid_values"][axis]
        shape = (len(data["grid"]["mean_ev"]), len(data["grid"]["std_ev"]))
        assert np.asarray(block["tau_b"]).shape == shape
        assert np.asarray(block["f_unresolved"]).shape == shape
        assert np.asarray(block["overlap"]).shape == shape


def test_artefact_shows_exact_mean_invariance():
    data = json.loads(ARTEFACT.read_text(encoding="utf-8"))
    assert data["mean_invariance"]["max_abs_tau_b_difference_vs_mean_0"] == 0.0


def test_artefact_shows_a_monotone_std_axis():
    data = json.loads(ARTEFACT.read_text(encoding="utf-8"))
    assert data["synthetic_correlations"]["spearman_shift_std_vs_tau_b"] == pytest.approx(-1.0)
    assert data["synthetic_correlations"]["spearman_abs_shift_mean_vs_tau_b"] == pytest.approx(0.0)
    for axis in ("oxidation", "reduction"):
        bounds = data["boundaries"][axis]
        assert bounds["std_where_mean_tau_b_below_0p8"] is not None
        assert bounds["std_where_mean_tau_b_below_0p5"] is not None
        assert bounds["std_where_mean_tau_b_below_0p8"] <= bounds["std_where_mean_tau_b_below_0p5"]


def test_artefact_keeps_the_measured_collinearity():
    data = json.loads(ARTEFACT.read_text(encoding="utf-8"))
    measured = data["measured_correlations"]
    assert measured["n_points"] == 10
    assert measured["n_rungs"] == 5
    assert measured["spearman_shift_std_vs_tau_b"] == pytest.approx(-0.8510677611520904)
    assert measured["spearman_abs_shift_mean_vs_shift_std"] > 0.7


def test_artefact_reports_subset_sensitivity_in_one_direction():
    data = json.loads(ARTEFACT.read_text(encoding="utf-8"))
    sensitivity = data["subset_sensitivity"]
    assert sensitivity["same_direction"] is True
    for population in ("native", "common10"):
        assert sensitivity[population]["n_points"] == 10
        assert sensitivity[population]["spearman_shift_std_vs_tau_b"] < 0
    assert sensitivity["native"]["n_molecules_per_rung"] == [10, 12, 18]


def test_figure_manifest_pins_the_figure_and_the_inputs():
    manifest = REPO_ROOT / "outputs" / "figures" / "figure_manifest_week21.md"
    text = manifest.read_text(encoding="utf-8")
    assert m.F42 in text
    assert "One-line caption (verbatim, for the terminal site):" in text
    assert "outputs/week9/stage10_ladder.json" in text
    assert "outputs/week4/p1_core_set_derived.csv" in text


# --- the panel-(c) label layout ------------------------------------------------

CROWDED_LABELS = (
    "G1_to_G2/oxi", "P1_to_P2/oxi", "G1_to_G2/red", "C1_to_C2/oxi", "P1_to_P2/red",
)


def test_crowded_label_cluster_is_resolved_without_overlap():
    """Five measured points sit inside 0.25 eV x 0.19, so the old fixed offset
    printed four labels on top of each other.  The placement must hand back
    disjoint boxes even for a deliberately tight cluster."""
    anchors = [(120.0 + 18.0 * index, 424.0 - 8.0 * index) for index in range(len(CROWDED_LABELS))]
    placed = m.assign_label_offsets(anchors, list(CROWDED_LABELS), reserved=[], dpi=100.0)
    assert len(placed) == len(CROWDED_LABELS)
    assert sorted(index for index, _offset in placed) == list(range(len(CROWDED_LABELS)))
    boxes = [m._label_box(anchors[index], CROWDED_LABELS[index], offset, m.LABEL_FONTSIZE, 100.0)
             for index, offset in placed]
    for first in range(len(boxes)):
        for second in range(first + 1, len(boxes)):
            assert not m._overlaps(boxes[first], [boxes[second]], pad=0.0), (first, second)


def test_label_placement_respects_the_axes_bounds_and_the_reserved_boxes():
    bounds = (80.0, 60.0, 670.0, 450.0)
    reserved = [(620.0, 330.0, 668.0, 452.0)]  # stands in for the legend
    anchors = [(120.0 + 55.0 * index, 430.0 - 25.0 * index) for index in range(len(CROWDED_LABELS))]
    for index, offset in m.assign_label_offsets(anchors, list(CROWDED_LABELS), reserved,
                                                bounds=bounds, dpi=100.0):
        box = m._label_box(anchors[index], CROWDED_LABELS[index], offset, m.LABEL_FONTSIZE, 100.0)
        assert bounds[0] <= box[0] and box[2] <= bounds[2], box
        assert bounds[1] <= box[1] and box[3] <= bounds[3], box
        assert not m._overlaps(box, reserved, pad=0.0), box


def test_threshold_label_is_centred_above_the_threshold_line():
    assert m.LINE_LABEL.startswith("$\\tau_b$")
    assert 0.8 < m.LINE_LABEL_Y <= 0.9
