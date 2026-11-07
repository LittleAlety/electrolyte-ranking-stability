"""Stage 11 / Week 10 tests: the four identities, the counterfactual controls, the
predictability test and the subset drift.

The stage is pure algebra applied to already-frozen numbers, so the tests
concentrate on the claims that would be silently wrong rather than loudly
broken:

* T1-T5 really hold to machine precision on every one of the ten points, and the
  closed form of T4 reproduces the project's own ``f_unresolved`` exactly (i.e.
  the new criterion is a restatement, not a different quantity);
* ``light_stability`` (used for the cheap controls) agrees with
  ``layer_stability`` (the project's reference implementation) on every decision
  metric -- a divergence there would silently invalidate all the controls;
* the rigid-offset control is *exactly* free while the monotone-Lipschitz control
  is exactly resolved: two zeros with completely different meanings;
* monotonicity alone is NOT enough (the rank control only works because it is
  f-Lipschitz), which is the trap the report warns about;
* the predictand is the SIGNED slope, and the exact permutation p-value is
  enumerated over all 120 label assignments rather than sampled;
* subset drift shrinks with N but keeps the mean, i.e. the common-10 choice is
  unbiased even though a single draw is noisy;
* the emitted markdown can be pasted into a table without a stray pipe.
"""

from __future__ import annotations

import io
import re
import sys
from pathlib import Path

import numpy as np
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
for _directory in (REPO_ROOT / "src", REPO_ROOT / "scripts"):
    if str(_directory) not in sys.path:
        sys.path.insert(0, str(_directory))

import analyze_stage10_synthesis as s10  # noqa: E402
import analyze_stage11_sigma_anatomy as s11  # noqa: E402
import analyze_p1_core_set as s3  # noqa: E402
import make_stage11_figure as f20  # noqa: E402

WEEK10 = REPO_ROOT / "outputs" / "week10"
ANATOMY_CSV = WEEK10 / "stage11_sigma_anatomy.csv"
ANATOMY_JSON = WEEK10 / "stage11_sigma_anatomy.json"
SUMMARY_MD = WEEK10 / "stage11_summary.md"
FIGURE_A = REPO_ROOT / "outputs" / "figures" / "F20_sigma_anatomy.png"
FIGURE_B = REPO_ROOT / "outputs" / "figures" / "F21_sigma_controls.png"
MANIFEST = REPO_ROOT / "outputs" / "figures" / "figure_manifest_week10_stage11.md"

EXPECTED_COMMON = ["AN", "DMC", "DME", "DMSO", "DOL", "EC", "GBL", "SL", "SN", "TMP"]

SOURCES = (s10.P1_DERIVED, s10.P2_EFFECTS, s10.T2_SUMMARY, s10.C1_SHIFTS, s10.C2_SHIFTS)

needs_sources = pytest.mark.skipif(
    not all(path.exists() for path in SOURCES),
    reason="stage-11 source artefacts are not present in this checkout")

needs_artifacts = pytest.mark.skipif(
    not all(path.exists() for path in (ANATOMY_CSV, ANATOMY_JSON, SUMMARY_MD,
                                       FIGURE_A, FIGURE_B, MANIFEST)),
    reason="stage-11 outputs are not present in this checkout")


_CACHE = {}


def _ladder():
    if "ladder" not in _CACHE:
        _CACHE["ladder"] = s11.load_ladder()
    return _CACHE["ladder"]


def _names():
    return s11.common_names(_ladder())


def _rows():
    if "rows" not in _CACHE:
        rows, detail = s11.analyse(_ladder(), _names())
        _CACHE["rows"] = rows
        _CACHE["detail"] = detail
    return _CACHE["rows"]


def _series(rung, axis):
    return s11.axis_series(_ladder(), rung, axis, _names())


def _axes():
    return [("P0_to_P1", "ox"), ("P0_to_P1", "red"), ("P1_to_P2", "ox"),
            ("P1_to_P2", "red"), ("G1_to_G2", "ox"), ("G1_to_G2", "red"),
            ("C0_to_C1", "ox"), ("C0_to_C1", "red"), ("C1_to_C2", "ox"),
            ("C1_to_C2", "red")]


# --------------------------------------------------------------------------
# the common subset is what the rest of the week assumes it is
# --------------------------------------------------------------------------

@needs_sources
def test_common_subset_is_the_expected_ten():
    assert _names() == EXPECTED_COMMON


@needs_sources
def test_every_row_uses_all_ten_names():
    assert len(_rows()) == 10
    for row in _rows():
        assert row["n"] == 10


# --------------------------------------------------------------------------
# T1-T5
# --------------------------------------------------------------------------

@needs_sources
@pytest.mark.parametrize("rung,axis", _axes())
def test_t1_sigma_is_the_shift_difference(rung, axis):
    before, after, _, _ = _series(rung, axis)
    delta = np.asarray(before) - np.asarray(after)
    sigma = s11.sigma_matrix(before, after)
    assert s11.theorem_t1_max_err(sigma, delta) < 1e-12


@needs_sources
@pytest.mark.parametrize("rung,axis", _axes())
def test_t2_rms_sigma_is_the_shift_stdev(rung, axis):
    before, after, _, _ = _series(rung, axis)
    rms, sd, rel = s11.theorem_t2(before, after)
    assert rel < 1e-12
    assert rms == pytest.approx(sd, rel=1e-12)


@needs_sources
@pytest.mark.parametrize("rung,axis", _axes())
def test_t3_rigid_offset_is_exactly_free(rung, axis):
    before, after, _, _ = _series(rung, axis)
    labels = [str(index) for index in range(len(before))]
    rows = s11.control_rigid_offset(before, after, labels, (-2.0, 0.5, 2.0))
    for item in rows:
        assert item["max_abs_d_sigma_ev"] < 1e-12
        assert item["d_tau_b"] == pytest.approx(0.0, abs=1e-15)
        assert item["d_f_unresolved_p1"] == pytest.approx(0.0, abs=1e-15)
        assert item["d_f_robust_inv"] == pytest.approx(0.0, abs=1e-15)


@needs_sources
@pytest.mark.parametrize("rung,axis", _axes())
def test_t4_closed_form_reproduces_the_project_f_unresolved(rung, axis):
    before, after, _, _ = _series(rung, axis)
    state = s11.light_stability(before, after)
    q, dp = s11.secant_slopes(before, after)
    for z, key in ((s11.Z_PRIMARY, "f_unresolved_p1"),
                   (s11.Z_SENSITIVITY, "f_unresolved_p1_z1p96")):
        predicted, crit = s11.closed_form_unresolved(q, dp, z)
        assert crit == pytest.approx(s11.SQRT2 / z)
        assert predicted == pytest.approx(state[key], abs=1e-15)


@needs_sources
@pytest.mark.parametrize("rung,axis", _axes())
def test_t5_sigma2_budget_splits_exactly(rung, axis):
    before, after, _, _ = _series(rung, axis)
    delta = np.asarray(before, dtype=float) - np.asarray(after, dtype=float)
    dec = s11.ols_decomposition(delta, np.asarray(after, dtype=float))
    assert dec["split_abs_err"] < 1e-12
    assert dec["share_parallel"] + dec["share_residual"] == pytest.approx(1.0, abs=1e-12)
    # r2 is by construction the rank-preserving share
    assert dec["r2"] == pytest.approx(dec["share_parallel"], abs=1e-12)


# --------------------------------------------------------------------------
# the cheap path must agree with the project's reference implementation
# --------------------------------------------------------------------------

@needs_sources
@pytest.mark.parametrize("rung,axis", _axes())
def test_light_stability_matches_layer_stability(rung, axis):
    before, after, labels, _ = _series(rung, axis)
    fast = s11.light_stability(before, after)
    ref = s3.layer_stability(before, after, labels, higher_is_better=True)
    for key in ("kendall_tau_b", "spearman_rho", "f_unresolved_p0", "f_unresolved_p1",
                "f_robust_inv", "f_unresolved_p1_z1p96", "f_robust_inv_z1p96",
                "sigma_median_ev"):
        assert fast[key] == pytest.approx(ref[key], abs=1e-15), key
    for fraction in ("k=0.10", "k=0.20", "k=0.30"):
        for field in ("overlap", "jaccard", "selection_regret"):
            assert fast["top_k"][fraction][field] == pytest.approx(
                ref["top_k"][fraction][field], abs=1e-15), (fraction, field)


# --------------------------------------------------------------------------
# the linear-shift phase diagram
# --------------------------------------------------------------------------

@needs_sources
def test_linear_shift_phase_diagram_matches_theory():
    before, after, _, _ = _series("P0_to_P1", "red")
    rows = s11.control_linear_shift(after, (-2.5, -1.05, -0.95, -0.722, 0.0,
                                           0.722, 1.0, 1.414, 1.8, 2.5))
    sqrt2 = s11.SQRT2
    for item in rows:
        b = item["slope_b"]
        assert item["q_median"] == pytest.approx(abs(b), abs=1e-9)
        assert item["q_spread"] < 1e-9, "every secant slope must equal |b| exactly"
        # tau_b flips sign exactly at b = -1
        expected = 1.0 if b > -1.0 else -1.0
        assert item["tau_b"] == pytest.approx(expected, abs=1e-9)
        # resolution steps exactly at |b| = sqrt(2)/z
        assert item["f_unresolved_z1"] == pytest.approx(
            1.0 if abs(b) > sqrt2 else 0.0, abs=1e-12)
        assert item["f_unresolved_z1p96"] == pytest.approx(
            1.0 if abs(b) > sqrt2 / s11.Z_SENSITIVITY else 0.0, abs=1e-12)
        assert item["f_unresolved_z1"] == item["f_unresolved_z1_closedform"]
        assert item["f_unresolved_z1p96"] == item["f_unresolved_z1p96_closedform"]


# --------------------------------------------------------------------------
# monotone-Lipschitz vs merely monotone: the trap the report warns about
# --------------------------------------------------------------------------

@needs_sources
@pytest.mark.parametrize("rung,axis", _axes())
def test_monotone_lipschitz_shift_is_resolved_and_ordinal(rung, axis):
    before, after, _, _ = _series(rung, axis)
    rows = s11.control_rank_shift(before, after, (0.25, 0.5, 0.75, 1.0))
    assert rows, "control produced no rows"
    for item in rows:
        assert item["tau_b"] == pytest.approx(1.0, abs=1e-12), "ranking must survive"
        assert item["f_unresolved_p1"] == 0.0, "nothing may be unresolved"
        assert item["overlap_20"] == 1.0
        # q_max == f is the exact signature of the f-Lipschitz construction
        assert item["q_max"] == pytest.approx(item["fraction_of_min_gap"], abs=1e-12)
        assert item["q_max"] <= 1.0


@needs_sources
def test_monotonicity_alone_is_not_enough():
    """A shift that is monotone but NOT Lipschitz does produce unresolved pairs.

    The rank-shift control is monotone by construction; scaling its amplitude past
    the minimum gap breaks the Lipschitz bound and immediately costs resolution,
    while the ranking itself is still untouched.
    """

    before, after, _, _ = _series("P0_to_P1", "red")
    after = np.asarray(after, float)
    order = np.argsort(after, kind="stable")
    ranks = np.empty(after.size, float)
    ranks[order] = np.arange(1, after.size + 1, dtype=float)
    centred = ranks - ranks.mean()
    gap = s11.adjacent_gap(after)
    stretched = after + 3.0 * gap * centred          # monotone, but not 1-Lipschitz
    assert s11.light_stability(list(stretched), list(after))["kendall_tau_b"] == \
        pytest.approx(1.0, abs=1e-12), "the ranking is still perfectly preserved"
    q, dp = s11.secant_slopes(stretched, after)
    assert float(np.max(q)) > s11.SQRT2, "yet some secant slope must cross the threshold"
    assert s11.light_stability(list(stretched), list(after))["f_unresolved_p1"] > 0.0


# --------------------------------------------------------------------------
# axis stretch: the one control with an exact closed form
# --------------------------------------------------------------------------

@needs_sources
@pytest.mark.parametrize("rung,axis", [("P0_to_P1", "red"), ("G1_to_G2", "ox")])
def test_axis_stretch_leaves_the_ranking_and_has_a_closed_form(rung, axis):
    before, after, _, _ = _series(rung, axis)
    rows = s11.control_axis_stretch(before, after, (0.5, 0.75, 1.5, 3.0, 5.0))
    for item in rows:
        assert item["d_tau_b"] == pytest.approx(0.0, abs=1e-15)
        assert item["overlap_20"] == 1.0
        # q' = abs(t + 1 - lambda)/lambda, so the predicted median must match
        assert item["q_median"] == pytest.approx(item["q_median_predicted"], abs=1e-12)
    # stretching buys resolution: f_unresolved is non-increasing in lambda here
    values = [item["f_unresolved_p1"] for item in rows]
    assert values == sorted(values, reverse=True)


# --------------------------------------------------------------------------
# predictability
# --------------------------------------------------------------------------

@needs_sources
def test_target_is_the_two_slot_shortlist_and_the_signed_slope_wins():
    rows = _rows()
    positives = [row["shortlist_rewritten"] for row in rows]
    assert sum(positives) == 3
    assert [row["rung"] for row in rows if row["shortlist_rewritten"]] == [
        "P0_to_P1", "C0_to_C1", "C1_to_C2"]

    table = {item["predictor"]: item for item in s11.predictability_table(rows)}
    # the predictor is direction aware: the signed slope reaches the ceiling ...
    assert table["ols_slope_b"]["auc"] == pytest.approx(1.0, abs=1e-12)
    assert table["ols_slope_b"]["auc_exact_permutation_p"] == pytest.approx(
        1.0 / 120.0, abs=1e-12)
    assert table["ols_slope_b"]["n_permutations"] == 120
    # ... while the unsigned magnitude proxies do not
    assert table["sigma_rms_ev"]["auc"] < table["ols_slope_b"]["auc"]
    assert table["q_median"]["auc"] < table["ols_slope_b"]["auc"]
    # the two sigma^2 shares are complements and point opposite ways: the
    # "rank-breaking share damages the decision" hypothesis is REFUTED here
    assert table["sigma2_share_parallel"]["auc"] == pytest.approx(1.0, abs=1e-12)
    assert table["sigma2_share_residual"]["auc"] == pytest.approx(0.0, abs=1e-12)


@needs_sources
def test_the_largest_sigma_point_is_not_a_rewrite():
    """The week-9 counterexample, now the corner stone of T4."""

    rows = sorted(_rows(), key=lambda row: -row["sigma_rms_ev"])
    loudest = rows[0]
    assert loudest["rung"] == "P0_to_P1" and loudest["axis"] == "reduction"
    assert loudest["sigma_rms_ev"] > 2.0
    assert loudest["shortlist_rewritten"] is False
    assert loudest["overlap_20"] == 1.0
    assert loudest["ols_slope_b"] > 1.0, "its shift is strongly parallel to the axis"


# --------------------------------------------------------------------------
# subset drift
# --------------------------------------------------------------------------

@needs_sources
def test_subset_drift_shrinks_without_biasing_the_mean():
    ladder = _ladder()
    population = sorted(set(ladder["P0_to_P1"]) & set(ladder["P1_to_P2"]))
    assert len(population) == 18
    records = s11.subset_drift(ladder, "P0_to_P1", "ox", population,
                               sizes=(6, 10, 14, 18), draws=300, seed=7)
    by_n = {item["n"]: item for item in records}
    # variance shrinks monotonically in N
    spreads = [by_n[n]["tau_b_std"] for n in (6, 10, 14, 18)]
    assert spreads == sorted(spreads, reverse=True)
    assert by_n[18]["tau_b_std"] == 0.0
    # the mean is stable: the common-10 subset is not a biased pick
    means = [by_n[n]["tau_b_mean"] for n in (6, 10, 14)]
    assert max(means) - min(means) < 0.15
    assert by_n[10]["tau_b_std"] > 0.05, "a single draw must not look exact"


# --------------------------------------------------------------------------
# artifacts
# --------------------------------------------------------------------------

@needs_artifacts
def test_emitted_markdown_has_no_stray_pipes_in_tables():
    text = io.open(SUMMARY_MD, encoding="utf-8").read()
    for line in text.splitlines():
        if not line.startswith("|"):
            continue
        cells = line.strip().strip("|").split("|")
        assert len(cells) > 1
        assert not re.search(r"abs\(.*\|.*\)", line), "abs(...) must not contain a pipe"


@needs_artifacts
def test_json_payload_self_consistency():
    import json

    payload = json.loads(ANATOMY_JSON.read_text(encoding="utf-8"))
    assert payload["common_subset"] == EXPECTED_COMMON
    assert payload["theorems"]["T1_sigma_is_shift_difference"]["ok"] is True
    assert payload["theorems"]["T2_rms_sigma_is_shift_stdev"]["ok"] is True
    assert payload["theorems"]["T3_rigid_offset_invariance"]["ok"] is True
    assert payload["theorems"]["T4_closed_form_unresolved"]["ok"] is True
    assert payload["theorems"]["T5_sigma2_budget_split"]["ok"] is True
    assert payload["control_checks"]["rank_shift_monotone_never_unresolved"]["ok"] is True
    assert payload["control_checks"]["linear_shift_matches_theory"]["ok"] is True
    assert payload["key_numbers"]["n_shortlist_rewrites"] == 3
    assert len(payload["rows"]) == 10

    # the closed form is a restatement of the project's own number, not a new one
    for row in payload["rows"]:
        assert row["t4_abs_err_z1"] == 0.0
        assert row["t4_abs_err_z1p96"] == 0.0
        assert row["sigma_rms_ev"] == pytest.approx(row["delta_sd_ev"], rel=1e-12)


@needs_artifacts
def test_figure_manifest_records_hashes_of_both_figures():
    import hashlib

    text = io.open(MANIFEST, encoding="utf-8").read()
    for path in (FIGURE_A, FIGURE_B):
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        assert digest in text, "%s hash missing from the manifest" % path.name
    assert "F20" in text and "F21" in text


@needs_artifacts
def test_figure_module_helpers_are_importable():
    assert f20.SHORT["P0_to_P1"] == "P0->P1"
    assert f20.REPO_ROOT == REPO_ROOT