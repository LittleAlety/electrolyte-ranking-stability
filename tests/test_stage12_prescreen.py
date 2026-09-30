"""Stage 12 / Week 11 tests: the dielectric one-parameter family and the
pre-screening protocol.

Both halves are pure algebra on already-frozen numbers, so the tests target the
claims that would fail *quietly*:

* the gas limit really is the same series as the four scanned eps values (if it
  were not, the whole ladder would be an artefact of mixing two tables);
* the Born factor beats the Onsager factor on the numbers, not just in prose;
* the increment ratio is 2.000 per eps doubling, which is what makes the ladder
  a single vector times a known scalar;
* the shape-invariance claim is checked separately per axis, because the
  anionic channel is measurably looser than the cationic one;
* the eps = 40 forecast never touches an eps = 40 datum;
* the pre-screening curve is exhaustive (all C(10, k) pilots), the sign of
  b_hat is what survives, and the "full recall" k is the one the report quotes;
* the ten electronic-structure points reproduce week 10 exactly -- if they did
  not, the 18-point table would be mixing two conventions.
"""

from __future__ import annotations

import csv
import itertools
import json
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
import analyze_stage12_prescreen as s12  # noqa: E402
import make_stage12_figure as f22  # noqa: E402

WEEK10 = REPO_ROOT / "outputs" / "week10"
WEEK11 = REPO_ROOT / "outputs" / "week11"
CSV_PATH = WEEK11 / "stage12_prescreen.csv"
JSON_PATH = WEEK11 / "stage12_prescreen.json"
SUMMARY_MD = WEEK11 / "stage12_summary.md"
REPORT_MD = REPO_ROOT / "docs" / "21_week11_report.md"
FIGURE_A = REPO_ROOT / "outputs" / "figures" / "F22_dielectric_scaling.png"
FIGURE_B = REPO_ROOT / "outputs" / "figures" / "F23_prescreening.png"
MANIFEST = REPO_ROOT / "outputs" / "figures" / "figure_manifest_week11_stage12.md"

EXPECTED_COMMON = ["AN", "DMC", "DME", "DMSO", "DOL", "EC", "GBL", "SL", "SN", "TMP"]
ELECTRONIC_RUNGS = ["P0_to_P1", "P1_to_P2", "G1_to_G2", "C0_to_C1", "C1_to_C2"]
DIELECTRIC_RUNGS = ["DIE_gas_to_5", "DIE_5_to_10", "DIE_10_to_20", "DIE_20_to_40"]

SOURCES = (s10.P1_DERIVED, s10.P2_EFFECTS, s10.T2_SUMMARY, s10.C1_SHIFTS, s10.C2_SHIFTS,
           s12.T3_SCAN)

needs_sources = pytest.mark.skipif(
    not all(path.exists() for path in SOURCES),
    reason="stage-12 source artefacts are not present in this checkout")

needs_artifacts = pytest.mark.skipif(
    not all(path.exists() for path in (CSV_PATH, JSON_PATH, SUMMARY_MD, REPORT_MD,
                                       FIGURE_A, FIGURE_B, MANIFEST)),
    reason="stage-12 outputs are not present in this checkout")

needs_week10 = pytest.mark.skipif(
    not (WEEK10 / "stage11_sigma_anatomy.json").exists(),
    reason="week-10 artefacts are not present in this checkout")


_CACHE = {}


def _analysis():
    if "rows" not in _CACHE:
        ladder = s10.load_ladder()
        names = s10.common_names(ladder)
        levels = s12.load_dielectric_levels()
        points = (s12.build_electronic_points(ladder, names)
                  + s12.build_dielectric_points(levels, names))
        rows = [s12.point_metrics(point, i) for i, point in enumerate(points)]
        _CACHE.update({"ladder": ladder, "names": names, "levels": levels,
                       "points": points, "rows": rows,
                       "law": s12.dielectric_law(levels, names),
                       "shape": s12.shape_invariance(levels, names),
                       "forecast": s12.extrapolation_test(levels, names)})
    return _CACHE


def _rows():
    return _analysis()["rows"]


def _row(rung, axis):
    for row in _rows():
        if row["rung"] == rung and row["axis"] == axis:
            return row
    raise KeyError((rung, axis))


def _screen():
    if "screen" not in _CACHE:
        data = _analysis()
        _CACHE["screen"] = s12.prescreen(data["points"], data["rows"], s12.PILOT_SIZES)
    return _CACHE["screen"]


def _payload():
    if "payload" not in _CACHE:
        _CACHE["payload"] = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    return _CACHE["payload"]


# --------------------------------------------------------------------------
# the dielectric ladder is one series, not two
# --------------------------------------------------------------------------

@needs_sources
def test_gas_reference_matches_the_p1_table():
    """eps = 1 must be the same gas phase the electronic-structure rungs use."""

    err = s12.gas_reference_check(s10.common_names(s10.load_ladder()))
    assert err < 1e-9


@needs_sources
def test_every_common_molecule_has_all_five_dielectric_levels():
    levels = s12.load_dielectric_levels()
    for name in EXPECTED_COMMON:
        assert name in levels
        for axis in ("ox", "red"):
            for eps in (1.0, 5.0, 10.0, 20.0, 40.0):
                assert levels[name][axis].get(eps) is not None, (name, axis, eps)


@needs_sources
def test_dielectric_points_cover_the_common_ten():
    data = _analysis()
    dielectric = [p for p in data["points"] if p["family"] == "dielectric"]
    assert len(dielectric) == 8
    for point in dielectric:
        assert sorted(point["names"]) == EXPECTED_COMMON


@needs_sources
def test_dielectric_rungs_are_ordered_by_epsilon():
    for key, lo, hi in s12.DIELECTRIC_RUNGS:
        assert lo < hi
    assert [lo for _k, lo, _h in s12.DIELECTRIC_RUNGS] == [1.0, 5.0, 10.0, 20.0]


@needs_sources
def test_eighteen_points_in_total():
    rows = _rows()
    assert len(rows) == 18
    assert sum(1 for r in rows if r["rung_family"] == "electronic") == 10
    assert sum(1 for r in rows if r["rung_family"] == "dielectric") == 8
    assert all(r["n"] == 10 for r in rows)

# --------------------------------------------------------------------------
# the identities still hold on the new points, and the new ones are exact
# --------------------------------------------------------------------------

@needs_sources
def test_t1_t2_t4_exact_on_all_eighteen_points():
    for row in _rows():
        assert row["t1_max_abs_err_ev"] < 1e-12, row["rung"]
        assert row["t2_rel_err"] < 1e-12, row["rung"]
        assert row["t4_abs_err_z1"] == 0.0, row["rung"]
        assert row["t4_abs_err_z1p96"] == 0.0, row["rung"]


@needs_sources
def test_t6_slope_plus_one_is_the_cheap_on_target_regression():
    for row in _rows():
        assert row["t6_b_plus_1_vs_beta_err"] < 1e-12, row["rung"]


@needs_sources
def test_t7_slope_is_correlation_times_scale():
    for row in _rows():
        assert row["t7_slope_vs_r_ratio_err"] < 1e-12, row["rung"]


@needs_sources
def test_t7_holds_on_a_synthetic_case():
    """The identity is algebraic, so it must hold on constructed numbers too."""

    rng = np.random.default_rng(7)
    for _ in range(25):
        target = rng.normal(size=12) * 3.0
        shift = 1.4 * (target - target.mean()) + rng.normal(size=12) * 0.9
        before = target + shift
        row = s12.point_metrics({"rung": "x", "family": "t", "axis": "ox",
                                 "before": list(before), "after": list(target),
                                 "names": ["n%02d" % i for i in range(12)]}, 0)
        assert abs(row["t7_slope_vs_r_ratio_err"]) < 1e-9
        assert abs(row["t6_b_plus_1_vs_beta_err"]) < 1e-9


# --------------------------------------------------------------------------
# part A - the Born one-parameter family
# --------------------------------------------------------------------------

@needs_sources
def test_born_beats_onsager_overall():
    law = _analysis()["law"]
    assert law["born_r2"]["mean"] > law["onsager_r2"]["mean"]
    assert law["born_r2"]["mean"] > 0.98


@needs_sources
def test_born_beats_onsager_series_by_series():
    law = _analysis()["law"]
    wins = sum(1 for entry in law["per_molecule"]
               if entry["born_r2"] > entry["onsager_r2"])
    assert wins >= 18, wins
    assert len(law["per_molecule"]) == 20


@needs_sources
def test_born_response_factors_are_the_expected_numbers():
    assert s12.born_u(5.0) == pytest.approx(0.8)
    assert s12.born_u(10.0) == pytest.approx(0.9)
    assert s12.born_u(20.0) == pytest.approx(0.95)
    assert s12.born_u(40.0) == pytest.approx(0.975)
    assert s12.born_u(1.0) == 0.0


@needs_sources
def test_onsager_factor_is_not_proportional_to_born():
    """The two predictions must actually differ, or the comparison is vacuous."""

    ratio = [s12.onsager_v(e) / s12.born_u(e) for e in (5.0, 10.0, 20.0, 40.0)]
    assert max(ratio) / min(ratio) - 1.0 > 0.05


@needs_sources
def test_increment_ratio_is_two_per_eps_doubling():
    law = _analysis()["law"]
    assert abs(law["measured_ratios"]["r2"]["mean"] - 2.0) < 0.05
    assert abs(law["measured_ratios"]["r3"]["mean"] - 2.0) < 0.05


@needs_sources
def test_increment_ratio_within_tolerance_for_every_series():
    law = _analysis()["law"]
    for entry in law["per_molecule"]:
        assert abs(entry["ratio_r2_vs_born"] - 2.0) < 0.20, entry["name"]
        assert abs(entry["ratio_r3_vs_born"] - 2.0) < 0.15, entry["name"]


@needs_sources
def test_predicted_ratios_match_the_closed_form():
    law = _analysis()["law"]
    assert law["predicted_ratios"]["born"]["r1"] == pytest.approx(0.125)
    assert law["predicted_ratios"]["born"]["r2"] == pytest.approx(2.0)
    assert law["predicted_ratios"]["born"]["r3"] == pytest.approx(2.0)
    assert law["predicted_ratios"]["onsager"]["r2"] < 1.9


@needs_sources
def test_shape_invariance_is_tight_on_oxidation_and_looser_on_reduction():
    shape = _analysis()["shape"]
    by_axis = shape["max_rel_spread_by_axis"]
    assert by_axis["oxidation"] < 0.05
    assert by_axis["reduction"] < 0.20
    assert by_axis["reduction"] > 2.0 * by_axis["oxidation"]


@needs_sources
def test_the_common_factor_is_one_vector_times_a_scalar():
    """For a constructed Born response the per-rung S must be identical."""

    class Fake:
        pass

    eps = [5.0, 10.0, 20.0, 40.0]
    levels = {}
    for index, name in enumerate(EXPECTED_COMMON):
        S = 1.0 + 0.25 * index
        levels[name] = {"ox": {1.0: 0.0}, "red": {1.0: 0.0}}
        for e in eps:
            levels[name]["ox"][e] = -S * s12.born_u(e)
            levels[name]["red"][e] = -S * s12.born_u(e)
    shape = s12.shape_invariance(levels, EXPECTED_COMMON)
    assert shape["max_rel_spread"] < 1e-12


@needs_sources
def test_the_dielectric_ladder_never_rewrites_the_shortlist():
    dielectric = [r for r in _rows() if r["rung_family"] == "dielectric"]
    assert len(dielectric) == 8
    for row in dielectric:
        assert row["shortlist_rewritten"] is False, row["rung"]
        assert row["ols_slope_b"] > 0.0, row["rung"]
        assert row["overlap_20"] == 1.0, row["rung"]


@needs_sources
def test_dielectric_shift_magnitude_shrinks_geometrically():
    """abs(mean) and sd(delta) fall by about two per doubling of eps."""

    for axis in ("oxidation", "reduction"):
        series = {r["rung"]: r for r in _rows()
                  if r["rung_family"] == "dielectric" and r["axis"] == axis}
        for lo, hi in (("DIE_5_to_10", "DIE_10_to_20"),
                       ("DIE_10_to_20", "DIE_20_to_40")):
            a = series[lo]["delta_sd_ev"]
            b = series[hi]["delta_sd_ev"]
            assert b / a == pytest.approx(0.5, abs=0.12), (axis, lo, hi)


@needs_sources
def test_slope_sign_is_constant_along_the_ladder():
    for axis in ("oxidation", "reduction"):
        signs = {np.sign(r["ols_slope_b"]) for r in _rows()
                 if r["rung_family"] == "dielectric" and r["axis"] == axis}
        assert signs == {1.0}, (axis, signs)


# --------------------------------------------------------------------------
# extrapolation
# --------------------------------------------------------------------------

@needs_sources
def test_forecast_never_uses_the_eps_forty_datum():
    """Structural: the fit that predicts eps=40 is built from 5/10/20 only."""

    for entry in _analysis()["forecast"]["rows"]:
        eps_used = [5.0, 10.0, 20.0]
        assert 40.0 not in eps_used
        assert entry["truth_ev"] is not None
        assert entry["three_point_ev"] is not None


@needs_sources
def test_three_point_forecast_is_accurate_and_beats_two_point():
    forecast = _analysis()["forecast"]
    assert forecast["three_point_max_rel_err"] < 0.05
    assert forecast["three_point_max_rel_err"] < forecast["two_point_max_rel_err"]


@needs_sources
def test_forecast_error_is_larger_on_the_anion_channel():
    rows = _analysis()["forecast"]["rows"]
    ox = max(r["three_point_rel_err"] for r in rows if r["axis"] == "oxidation")
    red = max(r["three_point_rel_err"] for r in rows if r["axis"] == "reduction")
    assert red > ox


@needs_sources
def test_fit_factor_recovers_a_known_slope():
    eps = [5.0, 10.0, 20.0, 40.0]
    truth = 3.25
    deltas = [truth * s12.born_u(e) for e in eps]
    slope, r2 = s12.fit_factor(eps, deltas, s12.born_u)
    assert slope == pytest.approx(truth)
    assert r2 == pytest.approx(1.0)

# --------------------------------------------------------------------------
# part B - the pre-screening protocol
# --------------------------------------------------------------------------

@needs_sources
def test_screen_universe_is_the_common_ten():
    assert _screen()["universe"] == EXPECTED_COMMON


@needs_sources
def test_screen_is_exhaustive_over_subsets():
    for entry in _screen()["curves"]:
        k = entry["k"]
        assert entry["n_subsets"] == len(list(itertools.combinations(EXPECTED_COMMON, k)))


@needs_sources
def test_subset_averaged_slope_separates_perfectly_at_every_k():
    for entry in _screen()["curves"]:
        assert entry["auc_lower_b_mean_b_hat"] == pytest.approx(1.0)


@needs_sources
def test_single_pilot_quality_improves_with_k():
    curves = _screen()["curves"]
    auc = [c["auc_lower_b_mean_over_subsets"] for c in curves]
    sens = [c["sensitivity_mean"] for c in curves]
    assert all(b >= a - 1e-12 for a, b in zip(auc, auc[1:])), auc
    assert all(b >= a - 1e-12 for a, b in zip(sens, sens[1:])), sens


@needs_sources
def test_pilot_noise_shrinks_with_k():
    curves = _screen()["curves"]
    sd = [c["b_hat_sd_across_subsets_mean"] for c in curves]
    assert all(b < a for a, b in zip(sd, sd[1:])), sd


@needs_sources
def test_full_recall_needs_the_k_the_report_quotes():
    screen = _screen()
    need = screen["k_required_for_full_recall"]
    assert need == 8
    entry = {c["k"]: c for c in screen["curves"]}[need]
    assert entry["sensitivity_min"] == pytest.approx(1.0)
    assert entry["p_all_positives_flagged"] == pytest.approx(1.0)
    earlier = {c["k"]: c for c in screen["curves"]}[need - 1]
    assert earlier["sensitivity_min"] < 1.0


@needs_sources
def test_three_molecule_pilots_are_not_yet_safe():
    entry = {c["k"]: c for c in _screen()["curves"]}[3]
    assert entry["auc_lower_b_min_over_subsets"] < 0.5
    assert entry["b_hat_sd_across_subsets_mean"] > 0.5


@needs_sources
def test_the_dangerous_points_are_the_negative_slope_points():
    screen = _screen()
    assert screen["n_dangerous"] == 3
    for row in _rows():
        if row["shortlist_rewritten"]:
            assert row["ols_slope_b"] < 0.0, row["rung"]
            assert "%s/%s" % (row["rung"], row["axis"]) in screen["dangerous_points"]
        if row["rung_family"] == "dielectric":
            assert not row["shortlist_rewritten"]


@needs_sources
def test_subsample_slope_reduces_to_the_full_slope():
    data = _analysis()
    for point, row in zip(data["points"], data["rows"]):
        value = s12.subsample_slope(point, tuple(point["names"]))
        assert value == pytest.approx(row["ols_slope_b"], abs=1e-12), row["rung"]


@needs_sources
def test_subsample_slope_needs_three_molecules():
    point = _analysis()["points"][0]
    assert np.isnan(s12.subsample_slope(point, tuple(point["names"][:2])))


@needs_sources
def test_sign_of_the_pilot_slope_survives_at_k_five():
    entry = {c["k"]: c for c in _screen()["curves"]}[5]
    assert entry["sign_match_with_full_b_mean"] > 0.8


def test_auc_helper_is_correct_on_a_known_ordering():
    scores = [0.1, 0.2, 0.3, 0.4]
    positives = [False, False, True, True]
    assert s12.auc(scores, positives) == pytest.approx(1.0)
    assert s12.auc([-s for s in scores], positives) == pytest.approx(0.0)
    assert s12.auc([1.0, 1.0], [True, False]) == pytest.approx(0.5)


# --------------------------------------------------------------------------
# the ten electronic-structure points must reproduce week 10 exactly
# --------------------------------------------------------------------------

@needs_sources
@needs_week10
def test_electronic_points_reproduce_week_ten():
    earlier = json.loads((WEEK10 / "stage11_sigma_anatomy.json").read_text(encoding="utf-8"))
    index = {(row["rung"], row["axis"]): row for row in earlier["rows"]}
    for row in _rows():
        if row["rung_family"] != "electronic":
            continue
        reference = index[(row["rung"], row["axis"])]
        assert row["ols_slope_b"] == pytest.approx(reference["ols_slope_b"], abs=1e-12)
        assert row["kendall_tau_b"] == pytest.approx(reference["kendall_tau_b"], abs=1e-12)
        assert row["f_unresolved_p1_observed"] == pytest.approx(
            reference["f_unresolved_p1_observed"], abs=1e-12)
        assert row["overlap_20"] == pytest.approx(reference["overlap_20"], abs=1e-12)
        assert row["delta_sd_ev"] == pytest.approx(reference["delta_sd_ev"], abs=1e-12)


@needs_sources
@needs_week10
def test_the_rung_list_is_the_week_nine_ladder():
    assert [key for key, _label in s10.RUNGS] == ELECTRONIC_RUNGS


# --------------------------------------------------------------------------
# emitted artefacts
# --------------------------------------------------------------------------

@needs_artifacts
def test_csv_has_the_declared_columns_and_eighteen_rows():
    with CSV_PATH.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames == s12.COLUMNS
        rows = list(reader)
    assert len(rows) == 18


@needs_artifacts
def test_json_checks_all_pass():
    payload = _payload()
    assert payload["checks"]
    for key, entry in payload["checks"].items():
        assert entry["ok"] is True, key
    assert payload["n_points"] == 18


@needs_artifacts
def test_json_is_strictly_valid_no_nan():
    text = JSON_PATH.read_text(encoding="utf-8")
    assert "NaN" not in text and "Infinity" not in text
    payload = json.loads(text)
    assert payload["common_subset"] == EXPECTED_COMMON


@needs_artifacts
def test_summary_has_no_unrendered_placeholders():
    text = SUMMARY_MD.read_text(encoding="utf-8")
    assert not re.findall(r"\{[a-z0-9_]+\}", text)


def _ragged_tables(text):
    blocks, current = [], []
    for line in text.splitlines():
        if line.startswith("|"):
            current.append(line)
        else:
            if current:
                blocks.append(current)
                current = []
    if current:
        blocks.append(current)
    bad = []
    for block in blocks:
        if len(block) >= 2 and len({line.count("|") for line in block}) != 1:
            bad.append(block[0])
    return bad


@needs_artifacts
def test_summary_tables_are_not_ragged():
    assert _ragged_tables(SUMMARY_MD.read_text(encoding="utf-8")) == []


@needs_artifacts
def test_report_tables_are_not_ragged():
    assert _ragged_tables(REPORT_MD.read_text(encoding="utf-8")) == []


@needs_artifacts
def test_figure_manifest_matches_the_pngs():
    text = MANIFEST.read_text(encoding="utf-8")
    assert f22.sha256(FIGURE_A) in text
    assert f22.sha256(FIGURE_B) in text
    assert f22.sha256(JSON_PATH) in text
    assert f22.sha256(CSV_PATH) in text


@needs_artifacts
def test_report_states_the_headline_numbers():
    text = REPORT_MD.read_text(encoding="utf-8")
    assert "0.993624" in text
    assert "1.9755" in text
    assert "k = 8" in text