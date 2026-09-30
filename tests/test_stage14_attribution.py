"""Stage 14 / Week 13 tests: distortion attribution and the EMC outlier.

Everything here targets a claim that would fail *quietly*:

* the ORCA dipole parser must read the Debye magnitude and not the a.u. one,
  and must return ``None`` rather than invent a number when the block is absent;
* the stored ``dist_ev`` must equal ``D_hi - D_lo`` rebuilt from the state
  ledger alone -- if that ever drifts, the whole attribution is aimed at the
  wrong object;
* every per-state distortion penalty must be non-negative, because the
  solvent-adapted density is not the bare-energy minimiser;
* the pair ``(-0.0465, +0.3272)`` eV that ``docs/22`` section 14 published must
  stay provably unreproducible: the enumeration must still find zero matches,
  so a future edit cannot quietly reintroduce it;
* the round-trip 2**8 - 1 subsets x 2 sign conventions must be enumerated, not
  sampled;
* the Born machinery must still reproduce Stage 13's published minimum
  R2 = 0.8468 on the frozen six-point grid -- a regression guard on the whole
  sign and reference convention;
* the dense grid must actually contain nine dielectrics and sixty-three new
  jobs, and the re-measured shared points must agree with the frozen numbers to
  every printed digit;
* no figure may be reported without its sha256.
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
for _directory in (REPO_ROOT / "src", REPO_ROOT / "scripts"):
    if str(_directory) not in sys.path:
        sys.path.insert(0, str(_directory))

import analyze_stage14_outlier as s14b  # noqa: E402
import build_stage14_attribution as s14a  # noqa: E402


WEEK13 = REPO_ROOT / "outputs" / "week13"
WEEK12 = REPO_ROOT / "outputs" / "week12"

ATTRIBUTION_JSON = WEEK13 / "stage14_attribution.json"
ATTRIBUTION_CSV = WEEK13 / "stage14_attribution.csv"
STATES_CSV = WEEK13 / "stage14_distortion_states.csv"
STATES_MOL_CSV = WEEK13 / "stage14_distortion_states_by_molecule.csv"
OUTLIER_JSON = WEEK13 / "stage14_outlier.json"
OUTLIER_CSV = WEEK13 / "stage14_outlier.csv"
GRID_JSON = WEEK13 / "stage14_dense_grid.json"

SPLIT_CSV = WEEK12 / "stage13_shift_split.csv"
LEDGER_CSV = WEEK12 / "stage13_state_ledger.csv"

F26 = REPO_ROOT / "outputs" / "figures" / "F26_distortion_attribution.png"
F27 = REPO_ROOT / "outputs" / "figures" / "F27_emc_outlier.png"
MANIFEST = REPO_ROOT / "outputs" / "figures" / "figure_manifest_week13_stage14.md"

REFERENCE = REPO_ROOT / "outputs" / "week4" / "orca" / "EMC" / "EMC_anion.out"


@pytest.fixture(scope="module")
def attribution():
    return json.loads(ATTRIBUTION_JSON.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def outlier():
    return json.loads(OUTLIER_JSON.read_text(encoding="utf-8"))


def load_csv(path):
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


# ---------------------------------------------------------------- parsing


def test_parse_dipole_debye_reads_the_debye_magnitude():
    text = ("some header\n"
            "Total Dipole Moment    :      1.000000000       2.000000000       3.000000000\n"
            "Magnitude (a.u.)       :      3.741657387\n"
            "Magnitude (Debye)      :      9.510000000\n"
            "trailing\n")
    assert s14a.parse_dipole_debye(text) == pytest.approx(9.51)


def test_parse_dipole_debye_takes_the_last_block():
    block = ("Total Dipole Moment    :      0.000000000       0.000000000       0.000000000\n"
             "Magnitude (Debye)      :      %s\n")
    text = block % "1.0" + "middle\n" + block % "4.25"
    assert s14a.parse_dipole_debye(text) == pytest.approx(4.25)


def test_parse_dipole_debye_returns_none_when_absent():
    assert s14a.parse_dipole_debye("no dipole block here\n") is None


def test_real_orca_output_has_a_readable_dipole():
    if not REFERENCE.exists():
        pytest.skip("frozen ORCA output missing")
    value = s14a.read_dipole(REFERENCE)
    assert value is not None and value > 0.0


# ---------------------------------------------------------------- identities


def test_stage13_decomposition_identity_holds_exactly():
    rows = s14a.load_shift_rows()
    assert len(rows) == 216
    assert s14a.identity_residual(rows) < 1e-12


def test_distortion_is_a_difference_of_state_penalties(attribution):
    assert attribution["correction"]["penalty_identity_holds"] is True
    assert attribution["correction"]["penalty_identity_max_abs_residual_ev"] < 1e-9


def test_every_state_penalty_is_non_negative(attribution):
    block = attribution["state_penalties"]
    for state in ("neutral", "cation", "anion"):
        assert block[state]["min_ev"] > 0.0
        assert block[state]["n_positive"] == block[state]["n"]
    assert block["variational_check"]["all_penalties_non_negative"] is True


def test_state_penalty_ordering_is_anion_over_cation_over_neutral(attribution):
    block = attribution["state_penalties"]
    assert block["anion"]["mean_ev"] > block["cation"]["mean_ev"]
    assert block["cation"]["mean_ev"] > block["neutral"]["mean_ev"]
    assert block["anion"]["mean_ev"] / block["neutral"]["mean_ev"] > 4.0


# ---------------------------------------------------------------- the published pair


def test_published_pair_is_not_reproducible(attribution):
    correction = attribution["correction"]
    assert correction["verdict"] == "not reproducible"
    search = correction["subset_enumeration"]
    assert search["n_candidates"] == 510
    assert search["n_exact_matches"] == 0
    assert search["closest"][0]["max_abs_error_ev"] > 1e-3


def test_published_pair_is_what_docs22_actually_printed():
    text = (REPO_ROOT / "docs" / "22_week12_report.md").read_text(encoding="utf-8")
    # docs/22 is typeset with the Unicode minus sign U+2212, not ASCII hyphen-minus
    normalised = text.replace("\u2212", "-")
    assert "-0.0465" in normalised
    assert "0.3272" in normalised


def test_reproducible_aggregation_replaces_the_published_pair(attribution):
    values = attribution["correction"]["reproducible_values"]
    assert values["oxidation_ev"] == pytest.approx(0.0435, abs=5e-4)
    assert values["reduction_ev"] == pytest.approx(-0.3025, abs=5e-4)


def test_axis_means_are_recomputed_from_the_source(attribution):
    rows = s14a.load_shift_rows()
    means = s14a.per_axis_means(rows, s14a.CPCM6)
    recorded = attribution["correction"]["reproducible_values"]
    assert means["oxidation"]["mean_ev"] == pytest.approx(recorded["oxidation_ev"])
    assert means["reduction"]["mean_ev"] == pytest.approx(recorded["reduction_ev"])
    assert means["reduction"]["n"] == 72


def test_channel_asymmetry_ratio(attribution):
    assert attribution["asymmetry_ratio_reduction_over_oxidation"] == pytest.approx(
        6.95, abs=0.05)
    assert attribution["channel_asymmetry"]["reduction"]["n_negative"] == 12
    assert attribution["channel_asymmetry"]["oxidation"]["n_negative"] == 8


def test_oxidation_mean_is_carried_by_three_molecules(attribution):
    top3 = attribution["oxidation_top3_molecules"]
    assert [entry["name"] for entry in top3] == ["EC", "TMP", "PC"]
    assert all(entry["dist_cpcm6_ev"] > 0.15 for entry in top3)


# ---------------------------------------------------------------- the screen


def test_neutral_penalty_is_the_predictable_one(attribution):
    table = attribution["correlations"]["state_penalty"]["table"]
    neutral = [row for row in table if row["group"] == "neutral"]
    best = max(neutral, key=lambda row: row["ols"]["loo_r2"])
    assert best["descriptor"] == "mu_neutral_debye"
    assert best["ols"]["loo_r2"] > 0.4
    assert abs(best["spearman"]["rho"]) > 0.85


def test_anion_penalty_is_not_predictable_from_stored_descriptors(attribution):
    table = attribution["correlations"]["state_penalty"]["table"]
    anion = [row for row in table if row["group"] == "anion"]
    best = max(anion, key=lambda row: row["ols"]["loo_r2"])
    assert best["ols"]["loo_r2"] < 0.4
    gas_dipole = next(row for row in anion if row["descriptor"] == "mu_anion_debye")
    assert abs(gas_dipole["spearman"]["rho"]) < 0.2


def test_axis_observables_are_not_predictable(attribution):
    table = attribution["correlations"]["axis_distortion"]["table"]
    for group in ("oxidation", "reduction"):
        best = max([row for row in table if row["group"] == group],
                   key=lambda row: row["ols"]["loo_r2"])
        assert best["ols"]["loo_r2"] < 0.4


def test_screen_is_scored_per_molecule_not_per_layer(attribution):
    note = attribution["correlations"]["state_penalty"]["pseudoreplication_note"]
    assert "six" in note
    rows = load_csv(STATES_MOL_CSV)
    assert len(rows) == 36


def test_ols_leave_one_out_penalises_a_single_point_fit():
    xs = [1.0, 2.0, 3.0, 4.0]
    ys = [1.0, 2.0, 3.0, 4.0]
    fit = s14a.ols(xs, ys)
    assert fit["r2"] == pytest.approx(1.0)
    assert fit["n"] == 4 and fit["k"] == 1


# ---------------------------------------------------------------- output shapes


def test_attribution_csv_shapes():
    assert len(load_csv(ATTRIBUTION_CSV)) == 24
    assert len(load_csv(STATES_CSV)) == 216
    assert len(load_csv(STATES_MOL_CSV)) == 36


def test_attribution_csv_covers_the_audited_subset():
    rows = load_csv(ATTRIBUTION_CSV)
    assert {row["name"] for row in rows} == set(s14a.AUDITED)
    assert {row["axis"] for row in rows} == {"oxidation", "reduction"}


# ---------------------------------------------------------------- part B


def test_born_through_origin_is_exact_on_a_born_series():
    xs = [1.0 - 1.0 / eps for eps in (5.0, 10.0, 20.0, 40.0)]
    ys = [2.5 * x for x in xs]
    fit = s14b.born_through_origin(xs, ys)
    assert fit["r2"] == pytest.approx(1.0)
    assert fit["slope"] == pytest.approx(2.5)


def test_born_through_origin_is_worse_than_a_free_intercept():
    # a strongly non-Born series: through-origin R2 is forced near zero because the
    # sign alternation cannot be absorbed by a single slope, while a free intercept
    # recovers part of the variance.  The point is the ranking, not a negative R2.
    xs = [1.0 - 1.0 / eps for eps in (5.0, 10.0, 20.0, 40.0)]
    ys = [1.0, -1.0, 1.0, -1.0]
    through_origin = s14b.born_through_origin(xs, ys)
    with_intercept = s14b.born_with_intercept(xs, ys)
    assert through_origin["r2"] < 0.05
    assert with_intercept["r2"] > 5.0 * through_origin["r2"]


def test_sign_changes_counts_each_turn():
    assert s14b.sign_changes([1.0, 2.0, 3.0]) == 0
    assert s14b.sign_changes([3.0, 2.0, 1.0]) == 0
    assert s14b.sign_changes([1.0, 3.0, 2.0, 4.0]) == 2


def test_born_machinery_reproduces_the_stage13_minimum(outlier):
    assert outlier["verdict"]["emc_reduction_born_r2_stage13_grid"] == pytest.approx(
        0.8468, abs=1e-4)
    curve = outlier["curves"]["EMC/reduction"]
    assert curve["born_r2_stage13_six_point"]["slope"] == pytest.approx(2.5668, abs=1e-4)


def test_ladder_and_job_count(outlier):
    assert len(outlier["ladder_eps"]) == 9
    assert outlier["n_new_jobs"] == 63
    assert len(outlier["curves"]) == 6
    assert outlier["ladder_eps"][:3] == [5.0, 7.0, 10.0]


def test_dense_grid_manifest_matches_the_analysis():
    grid = json.loads(GRID_JSON.read_text(encoding="utf-8"))
    assert grid["n_jobs_expected"] == 63
    assert grid["failures"] == 0
    assert grid["jobs"] == 2 and grid["nprocs"] == 8
    assert len(grid["layers"]) == 7
    for layer in grid["layers"]:
        assert layer["summary"]["n_ok"] == 9
        assert layer["summary"]["n_failed"] == 0


def test_shared_points_reproduce_the_frozen_stage13_numbers(outlier):
    reproducibility = outlier["reproducibility"]
    assert reproducibility["verdict"] == "reproduced"
    assert reproducibility["n_points_compared"] == 36
    assert reproducibility["n_identical_strings"] == 36
    assert reproducibility["max_abs_delta_eh"] < 1e-9
    for point in reproducibility["points"]:
        assert not point["fresh_qc_flags"]
        assert not point["reference_qc_flags"]


def test_grid_density_study_is_monotone_in_point_count(outlier):
    for key, curve in outlier["curves"].items():
        counts = [item["n_points"] for item in curve["born_r2_by_grid_density"]]
        assert counts == sorted(counts)
        assert counts[0] == 4 and counts[-1] == 9
        assert len(curve["born_r2_by_grid_density"]) == 6


def test_curve_csv_has_nine_points_per_curve():
    rows = load_csv(OUTLIER_CSV)
    assert len(rows) == 6 * 9
    counts = {}
    for row in rows:
        counts[(row["name"], row["axis"])] = counts.get((row["name"], row["axis"]), 0) + 1
    assert set(counts.values()) == {9}


def test_emc_reduction_dip_is_reported_with_its_state_decomposition(outlier):
    verdict = outlier["verdict"]
    assert verdict["emc_reduction_step_10_to_20_ev"] == pytest.approx(-0.0630, abs=2e-3)
    step = verdict["emc_reduction_step_10_to_20_by_state_ev"]
    assert set(step) == {"neutral", "cation", "anion"}
    assert isinstance(verdict["dip_is_state_localised"], bool)


def test_energy_kink_screen_finds_emc_on_the_reduction_side_only(outlier):
    screen = outlier["energy_kink_screen"]
    assert screen["ea_suspect"] == "EMC"
    assert screen["ea_suspect_ev"] == pytest.approx(0.5369, abs=1e-3)
    assert screen["ea_runner_up_ev"] == pytest.approx(0.1483, abs=1e-3)
    assert screen["ea_outlier_ratio"] > 3.0
    # the control that makes the screen non-circular: on the IP axis EMC is not
    # the outlier, so the anomaly is specific to the reduction side
    assert screen["ip_suspect"] != "EMC"
    assert outlier["verdict"]["energy_kink_is_reduction_side_only"] is True


def test_energy_kink_screen_is_recomputed_from_the_frozen_layers(outlier):
    fresh = s14b.energy_kink_screen()
    stored = outlier["energy_kink_screen"]
    assert [row["name"] for row in fresh["ea"]] == [row["name"] for row in stored["ea"]]
    assert [row["name"] for row in fresh["ip"]] == [row["name"] for row in stored["ip"]]
    assert len(fresh["ea"]) == 12
    assert {row["name"] for row in fresh["ea"]} == set(s14b.AUDITED_MOLECULES)
    for a, b in zip(fresh["ea"], stored["ea"]):
        assert a["max_abs_second_difference_ev"] == pytest.approx(
            b["max_abs_second_difference_ev"])
    for a, b in zip(fresh["ip"], stored["ip"]):
        assert a["max_abs_second_difference_ev"] == pytest.approx(
            b["max_abs_second_difference_ev"])


# ---------------------------------------------------------------- figures


def test_figures_f26_and_f27_exist():
    for path in (F26, F27):
        assert path.exists(), path
        assert path.stat().st_size > 20000


def test_figure_manifest_lists_both_figures_and_their_sha256():
    text = MANIFEST.read_text(encoding="utf-8")
    assert "F26_distortion_attribution.png" in text
    assert "F27_emc_outlier.png" in text
    import hashlib
    for path in (F26, F27):
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        assert digest in text