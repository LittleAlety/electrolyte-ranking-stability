"""Stage 13 / Week 12 tests: the dielectric limit and ORCA's energy ledger.

Everything here targets a claim that would fail *quietly*:

* the ledger parser must read ORCA's four printed numbers and refuse to invent
  the ones that are absent (gas has no solvation terms, bare CPCM has no CDS);
* the printed identity ``FINAL = Total + D4 + gCP`` must hold, because the whole
  stage rests on ORCA really decomposing its own energy;
* the four-term split of a shift must be exact, not approximate;
* the Born form must win on six dielectrics as it did on four, and the
  two-parameter family must fit its own ``k`` back to zero;
* the SMD CDS term must be state-independent, which is what makes it invisible;
* no check may be reported as passing when a number is missing.
"""

from __future__ import annotations

import csv
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

import analyze_stage13_dielectric_limit as s13  # noqa: E402
import build_stage13_ladder as b13  # noqa: E402
import orca_energy_ledger as ledger  # noqa: E402


WEEK12 = REPO_ROOT / "outputs" / "week12"


LADDER_CSV = WEEK12 / "stage13_dielectric_ladder.csv"


STATE_CSV = WEEK12 / "stage13_state_ledger.csv"


SPLIT_CSV = WEEK12 / "stage13_shift_split.csv"


LADDER_JSON = WEEK12 / "stage13_ladder.json"


ANALYSIS_JSON = WEEK12 / "stage13_analysis.json"


SUMMARY_MD = WEEK12 / "stage13_summary.md"


F24 = REPO_ROOT / "outputs" / "figures" / "F24_dielectric_limit.png"


F25 = REPO_ROOT / "outputs" / "figures" / "F25_environment_ledger.png"


ARTIFACTS = pytest.mark.skipif(
    not (LADDER_CSV.exists() and ANALYSIS_JSON.exists()),
    reason="Stage 13 artefacts not built yet")


def _orca_text(*, total, dispersion, gcp, final, cpcm=None, cds=None,
               cds_kcal=None, epsilon=None, solvent=None):
    """A minimal ORCA output carrying exactly the lines the parser reads."""

    lines = []
    if epsilon is not None:
        lines += ["CPCM SOLVATION MODEL", "--------------------", "CPCM parameters:",
                  "  Epsilon                                         ...      %.4f" % epsilon,
                  "  Refrac                                          ...       1.3442"]
        if solvent:
            lines.append("Solvent:                                          ... %s" % solvent)
    lines += ["", "----------------", "TOTAL SCF ENERGY", "----------------", ""]
    lines.append("Total Energy       :       %.14f Eh           %.5f eV"
                 % (total, total * ledger.HARTREE_TO_EV))
    if cpcm is not None or cds is not None:
        lines.append("Components:")
        if cpcm is not None:
            lines.append("CPCM Dielectric    :         %.14f Eh             %.5f eV"
                         % (cpcm, cpcm * ledger.HARTREE_TO_EV))
        if cds is not None:
            lines.append("SMD CDS (Gcds)     :         %.14f Eh             %.5f eV"
                         % (cds, cds * ledger.HARTREE_TO_EV))
    if cds_kcal is not None:
        lines += ["", "SMD CDS free energy correction energy :                %.5f     Kcal/mol"
                  % cds_kcal,
                  "Total Energy after SMD CDS correction =              %.9f Eh" % total]
    lines += ["", "DFT DISPERSION CORRECTION", "DFT V3.4.0",
              "Dispersion correction           %.9f" % dispersion,
              "------------------   ----------------",
              "gCP correction             %.9f" % gcp,
              "-------------------------   --------------------",
              "FINAL SINGLE POINT ENERGY      %.12f" % final]
    return "\n".join(lines) + "\n"


def _entry(final, total, cpcm=None, cds=None, dispersion=0.0, gcp=0.0):
    return {"final_single_point_eh": final, "total_energy_eh": total,
            "cpcm_dielectric_eh": cpcm, "smd_cds_eh": cds,
            "dispersion_eh": dispersion, "gcp_eh": gcp}


# --------------------------------------------------------------------------- #
# the parser
# --------------------------------------------------------------------------- #
def test_parser_reads_a_gas_run():
    text = _orca_text(total=-100.0, dispersion=-0.002, gcp=0.009, final=-99.993)
    parsed = ledger.parse_ledger(text)
    assert parsed["final_single_point_eh"] == pytest.approx(-99.993, abs=1e-12)
    assert parsed["total_energy_eh"] == pytest.approx(-100.0, abs=1e-12)
    assert parsed["dispersion_eh"] == pytest.approx(-0.002, abs=1e-9)
    assert parsed["gcp_eh"] == pytest.approx(0.009, abs=1e-9)
    assert parsed["cpcm_dielectric_eh"] is None
    assert parsed["smd_cds_eh"] is None
    assert parsed["cpcm_epsilon"] is None
    assert parsed["cpcm_solvent"] is None


def test_parser_reads_a_bare_cpcm_run():
    text = _orca_text(total=-100.0, dispersion=-0.002, gcp=0.009, final=-100.006,
                      cpcm=-0.013, epsilon=5.0, solvent="CUSTOM")
    parsed = ledger.parse_ledger(text)
    assert parsed["cpcm_dielectric_eh"] == pytest.approx(-0.013, abs=1e-12)
    assert parsed["smd_cds_eh"] is None
    assert parsed["cpcm_epsilon"] == pytest.approx(5.0)
    assert ledger.environment_is_bare_cpcm(parsed)
    assert not ledger.environment_is_smd(parsed)


def test_parser_reads_an_smd_run():
    text = _orca_text(total=-100.0, dispersion=-0.002, gcp=0.009, final=-100.02,
                      cpcm=-0.02, cds=0.0074, cds_kcal=4.64357, epsilon=78.355,
                      solvent="WATER")
    parsed = ledger.parse_ledger(text)
    assert parsed["cpcm_dielectric_eh"] == pytest.approx(-0.02, abs=1e-12)
    assert parsed["smd_cds_eh"] == pytest.approx(0.0074, abs=1e-12)
    assert parsed["cpcm_solvent"] == "WATER"
    assert parsed["cpcm_epsilon"] == pytest.approx(78.355)
    assert ledger.environment_is_smd(parsed)


def test_energy_identity_holds_on_parsed_text():
    text = _orca_text(total=-100.0, dispersion=-0.002, gcp=0.009, final=-99.993)
    parsed = ledger.parse_ledger(text)
    assert abs(parsed["identity_residual_eh"]) < 1e-9


def test_cds_printed_in_kcal_and_eh_agrees():
    text = _orca_text(total=-100.0, dispersion=-0.002, gcp=0.009, final=-100.02,
                      cpcm=-0.02, cds=0.0074, cds_kcal=4.64357, epsilon=78.355,
                      solvent="WATER")
    parsed = ledger.parse_ledger(text)
    assert abs(parsed["cds_kcal_vs_eh_residual_eh"]) < 1e-6


def test_absent_terms_are_none_not_zero():
    text = _orca_text(total=-100.0, dispersion=-0.002, gcp=0.009, final=-99.993)
    parsed = ledger.parse_ledger(text)
    assert parsed["cpcm_dielectric_eh"] is None
    assert parsed["smd_cds_eh"] is None
    assert parsed["identity_residual_eh"] is not None


def test_shift_components_splits_one_state():
    gas = _entry(-100.0, -100.0)
    smd = _entry(-100.02, -100.0, cpcm=-0.02, cds=0.0)
    parts = ledger.shift_components(smd, gas)
    assert parts["electrostatic_eh"] == pytest.approx(-0.02, abs=1e-12)
    assert parts["non_electrostatic_eh"] == pytest.approx(0.0, abs=1e-12)


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- #
# the ladder artefact
# --------------------------------------------------------------------------- #
@ARTIFACTS
def test_ladder_json_reports_twelve_molecules():
    payload = _load(LADDER_JSON)
    assert payload["subset"] == list(b13.SUBSET_NAMES)
    assert payload["n_split_rows"] == len(payload["subset"]) * len(b13.LEVELS) * 2


@ARTIFACTS
def test_ladder_json_has_no_missing_jobs():
    payload = _load(LADDER_JSON)
    assert payload["missing"] == []
    assert payload["checks"]["ladder_complete"]["ok"] is True
    assert payload["checks"]["ladder_complete"]["n_missing"] == 0


@ARTIFACTS
def test_ladder_json_all_checks_pass():
    payload = _load(LADDER_JSON)
    failed = sorted(name for name, entry in payload["checks"].items() if entry.get("ok") is False)
    assert failed == []


@ARTIFACTS
def test_ladder_json_state_rows_equal_twelve_by_nine_by_three():
    payload = _load(LADDER_JSON)
    expected = len(payload["subset"]) * len(b13.LEVELS) * 3
    assert payload["n_state_rows"] == expected == 324
    assert payload["checks"]["ladder_complete"]["expected_states"] == expected


@ARTIFACTS
def test_ladder_json_levels_match_the_module():
    payload = _load(LADDER_JSON)
    tags = [entry["tag"] for entry in payload["levels"]]
    assert tags == [level["tag"] for level in b13.LEVELS]
    assert payload["bare_levels"] == list(b13.BARE_TAGS)
    assert payload["smd_levels"] == list(b13.SMD_TAGS)


@ARTIFACTS
def test_ladder_gas_level_matches_the_p1_table():
    entry = _load(LADDER_JSON)["checks"]["gas_level_matches_p1_table"]
    assert entry["ok"] is True
    assert entry["max_abs_ip_diff_ev"] == 0.0
    assert entry["max_abs_ea_diff_ev"] == 0.0


@ARTIFACTS
def test_ladder_shift_split_is_exact():
    entry = _load(LADDER_JSON)["checks"]["shift_split_is_exact"]
    assert entry["ok"] is True
    assert abs(entry["max_abs_residual_ev"]) < 1e-7


@ARTIFACTS
def test_ladder_cds_is_state_independent():
    entry = _load(LADDER_JSON)["checks"]["cds_is_state_independent"]
    assert entry["ok"] is True
    assert entry["max_spread_ev"] == 0.0
    assert entry["n_molecule_layer_groups"] == 12 * 2


@ARTIFACTS
def test_ladder_d4_and_gcp_are_environment_independent():
    entry = _load(LADDER_JSON)["checks"]["composite_terms_environment_independent"]
    assert entry["ok"] is True
    assert entry["max_abs_d4_ev"] == 0.0
    assert entry["max_abs_dgcp_ev"] == 0.0


@ARTIFACTS
def test_ladder_printed_epsilon_matches_nominal():
    entry = _load(LADDER_JSON)["checks"]["printed_epsilon_matches_nominal"]
    assert entry["ok"] is True
    assert entry["max_abs_diff"] < 1e-3


@ARTIFACTS
def test_ladder_cds_kcal_consistency():
    entry = _load(LADDER_JSON)["checks"]["cds_kcal_consistency"]
    assert entry["ok"] is True
    assert abs(entry["max_abs_residual_ev"]) < 1e-6


# --------------------------------------------------------------------------- #
# the analysis artefact
# --------------------------------------------------------------------------- #
@ARTIFACTS
def test_analysis_all_checks_pass():
    payload = _load(ANALYSIS_JSON)
    failed = sorted(name for name, entry in payload["checks"].items() if entry.get("ok") is False)
    assert failed == []


@ARTIFACTS
def test_analysis_subset_is_the_twelve_molecule_audit_set():
    payload = _load(ANALYSIS_JSON)
    assert payload["subset"] == list(b13.SUBSET_NAMES)


@ARTIFACTS
def test_analysis_born_beats_onsager_on_six_dielectrics():
    model = _load(ANALYSIS_JSON)["model_comparison"]
    assert model["n_points_per_curve"] == 7
    assert model["born_r2"]["mean"] > model["onsager_r2"]["mean"]
    assert model["born_r2"]["mean"] > 0.95


@ARTIFACTS
def test_analysis_born_wins_the_curve_majority_with_a_documented_tail():
    """The 4-point criterion ``min R2 > 0.95`` was falsified at 6 dielectrics."""

    checks = _load(ANALYSIS_JSON)["checks"]
    tail = checks["born_tail_is_an_outlier_not_a_trend"]
    majority = checks["born_wins_the_curve_majority"]
    assert tail["ok"] is True
    assert majority["share_of_curves_where_born_wins"] >= 0.8
    assert tail["non_monotone_curves"] == ["EMC/reduction"]
    assert [label for label, _ in tail["curves_below_r2_0p95"]] == ["EMC/reduction"]
    # Onsager only wins on three curves, all of them on the reduction axis
    assert len(majority["onsager_wins_on"]) == 3
    assert all(entry.endswith("/reduction") for entry in majority["onsager_wins_on"])


@ARTIFACTS
def test_analysis_two_parameter_k_is_pinned_to_zero():
    stats = _load(ANALYSIS_JSON)["model_comparison"]["two_parameter_k"]
    assert abs(stats["mean"]) < 0.3
    assert stats["max"] < 1.0


@ARTIFACTS
def test_analysis_total_shift_is_more_born_like_than_its_parts():
    """The parts fit worse than their sum: the two terms are coupled."""

    entry = _load(ANALYSIS_JSON)["checks"]["total_shift_is_more_born_like_than_its_parts"]
    assert entry["ok"] is True
    assert entry["total_mean_r2"] > entry["dielectric_mean_r2"]
    assert entry["total_mean_r2"] > entry["distortion_mean_r2"]


@ARTIFACTS
def test_analysis_distortion_is_not_born_like():
    entry = _load(ANALYSIS_JSON)["checks"]["distortion_is_not_born_like"]
    assert entry["ok"] is True
    assert entry["distortion_mean_r2"] < 0.2


@ARTIFACTS
def test_analysis_distortion_slope_has_the_opposite_sign():
    terms = _load(ANALYSIS_JSON)["term_resolved_born"]
    assert terms["diel_S_ev"]["mean"] * terms["dist_S_ev"]["mean"] < 0.0


@ARTIFACTS
def test_analysis_conductor_limit_is_reached_by_eps_200():
    gap = _load(ANALYSIS_JSON)["conductor_limit"]["gap_to_limit_ev"]
    assert gap["max"] < 0.05


@ARTIFACTS
def test_analysis_ordering_is_stable_all_the_way_to_the_limit():
    ordering = _load(ANALYSIS_JSON)["conductor_limit"]["ordering"]
    for axis in ("oxidation", "reduction"):
        block = ordering[axis]
        assert block["kendall_tau_gas_vs_limit"] > 0.5
        assert block["kendall_tau_200_vs_limit"] > 0.9
        assert abs(block["top20_overlap_gas_vs_limit"] - 1.0) < 1e-12


@ARTIFACTS
def test_analysis_extrapolation_is_measured_on_three_targets():
    targets = _load(ANALYSIS_JSON)["extrapolation_scaling"]["targets"]
    assert sorted(targets) == ["cpcm_200", "cpcm_40", "cpcm_80"]
    for entry in targets.values():
        assert entry["max_abs_err_ev"] is not None
        assert entry["u_gap"] > 0.0


@ARTIFACTS
def test_analysis_extrapolation_error_grows_with_distance():
    targets = _load(ANALYSIS_JSON)["extrapolation_scaling"]["targets"]
    errs = [targets[tag]["max_abs_err_ev"] for tag in ("cpcm_40", "cpcm_80", "cpcm_200")]
    assert errs[0] <= errs[1] + 1e-12 <= errs[2] + 2e-12


@ARTIFACTS
def test_analysis_extrapolation_scales_with_the_distance_actually_covered():
    payload = _load(ANALYSIS_JSON)["extrapolation_scaling"]
    assert payload["err_per_u_gap_ev"] is not None
    assert payload["err_per_u_gap_ev"] > 0.0

@ARTIFACTS
def test_analysis_smd_ledger_covers_both_layers_and_both_axes():
    ledger_block = _load(ANALYSIS_JSON)["smd_ledger"]
    for tag in s13.SMD_TAGS:
        block = ledger_block[tag]
        assert block["epsilon"] > 1.0
        assert sorted(block["per_axis"]) == ["oxidation", "reduction"]
        assert block["per_axis"]["oxidation"]["n"] == 12


@ARTIFACTS
def test_analysis_smd_ledger_reproduces_the_shift():
    entry = _load(ANALYSIS_JSON)["checks"]["smd_ledger_reproduces_the_shift"]
    assert entry["ok"] is True
    assert abs(entry["max_split_residual_ev"]) < 1e-7
    assert entry["cds_max_spread_ev"] == 0.0
    assert entry["max_abs_d4_ev"] == 0.0
    assert entry["max_abs_dgcp_ev"] == 0.0


@ARTIFACTS
def test_analysis_solute_distortion_is_a_real_term():
    entry = _load(ANALYSIS_JSON)["checks"]["solute_distortion_is_a_real_term"]
    assert entry["ok"] is True
    assert entry["max_abs_mean_distortion_ev"] > 0.1


@ARTIFACTS
def test_analysis_cds_absolute_is_not_small():
    absolute = _load(ANALYSIS_JSON)["smd_ledger"]["smd_cds_absolute_ev"]
    assert abs(absolute[s13.SMD_TAGS[0]]["mean"]) > 1e-3
    assert abs(absolute[s13.SMD_TAGS[1]]["mean"]) > 1e-2


@ARTIFACTS
def test_analysis_records_the_cavity_radius_caveat():
    """The bare-CPCM and SMD layers use different atomic-radius boxes."""
    block = _load(ANALYSIS_JSON)["smd_ledger"]["smd_acetonitrile"]["smd_minus_bare_same_epsilon"]
    assert block["rows"]
    assert "cavity/radii" in block["note"]
    assert "radii" in block["note"] and "CDS" in block["note"]
    assert block["difference_ev"]["mean"] is not None


@ARTIFACTS
def test_analysis_rung_ladder_has_22_points():
    rungs = _load(ANALYSIS_JSON)["rung_ladder"]
    assert rungs["n_points"] == 22
    assert rungs["n_dielectric"] == 12
    assert rungs["n_electronic"] == 10


@ARTIFACTS
def test_analysis_dielectric_rungs_keep_the_shortlist():
    """The benign criterion is a decision claim, not a sign claim on ``b``."""

    rungs = _load(ANALYSIS_JSON)["rung_ladder"]["rows"]
    dielectric = [row for row in rungs if row.get("rung_family") == "dielectric"]
    assert len(dielectric) == 12
    for row in dielectric:
        assert float(row["kendall_tau_b"]) > 0.5
        assert abs(float(row["overlap_20"]) - 1.0) < 1e-12
        assert not row.get("shortlist_rewritten")


@ARTIFACTS
def test_analysis_dielectric_slope_shrinks_toward_zero():
    """At the saturated end the sign of ``b`` stops being resolvable."""

    entry = _load(ANALYSIS_JSON)["checks"]["dielectric_slope_shrinks_toward_zero"]
    assert entry["ok"] is True
    assert entry["max_abs_b_at_the_saturated_end"] < 0.01
    assert entry["max_abs_b_at_the_saturated_end"] <= entry["max_abs_b_from_the_gas"]
    assert entry["min_b_over_all_dielectric_rungs"] < 0.0


@ARTIFACTS
def test_analysis_only_three_rungs_rewrite_the_shortlist():
    rungs = _load(ANALYSIS_JSON)["rung_ladder"]
    assert rungs["n_rewritten"] == 3
    assert len(rungs["rewritten_points"]) == 3


@ARTIFACTS
def test_analysis_rewritten_set_matches_the_stage12_ladder():
    rungs = _load(ANALYSIS_JSON)["rung_ladder"]
    stage12 = REPO_ROOT / "outputs" / "week11" / "stage12_prescreen.csv"
    with stage12.open(encoding="utf-8", newline="") as handle:
        rows = [row for row in csv.DictReader(handle) if row.get("rung_family") == "electronic"]
    expected = sorted("%s/%s" % (row["rung"], row["axis"]) for row in rows
                      if float(row["overlap_20"]) < 1.0 - 1e-12)
    assert sorted(rungs["rewritten_points"]) == expected


@ARTIFACTS
def test_analysis_summary_has_no_unfilled_placeholders():
    text = SUMMARY_MD.read_text(encoding="utf-8")
    for placeholder in ("{w12_", "{artifact_list}", "{missing_list}", "{prereg_sha256}"):
        assert placeholder not in text


@ARTIFACTS
def test_analysis_summary_never_prints_a_negative_zero():
    """A tiny negative number is fine; a printed negative zero is not."""

    text = SUMMARY_MD.read_text(encoding="utf-8")
    assert re.search(r"-0\.0+(?!\d)", text) is None


@ARTIFACTS
def test_figures_f24_and_f25_exist():
    for path in (F24, F25):
        assert path.exists()
        assert path.stat().st_size > 10000


@ARTIFACTS
def test_figure_manifest_lists_both_figures():
    manifest = REPO_ROOT / "outputs" / "figures" / "figure_manifest_week12_stage13.md"
    text = manifest.read_text(encoding="utf-8")
    assert "F24_dielectric_limit.png" in text
    assert "F25_environment_ledger.png" in text
    assert "SHA256" in text.upper()


# --------------------------------------------------------------------------- #
# unit level: the parser and the algebra, with no artefacts on disk
# --------------------------------------------------------------------------- #
def test_parser_takes_the_last_printed_block():
    text = (_orca_text(total=-100.0, dispersion=0.0, gcp=0.0, final=-99.0)
            + _orca_text(total=-100.0, dispersion=0.0, gcp=0.0, final=-98.0))
    assert ledger.parse_ledger(text)["final_single_point_eh"] == pytest.approx(-98.0)


def test_hartree_conversions_are_consistent():
    assert ledger.HARTREE_TO_EV / ledger.HARTREE_TO_KCAL == pytest.approx(
        1.0 / 23.060548867, rel=1e-6)


def test_bare_electronic_removes_both_solvation_terms():
    entry = {"total_energy_eh": -100.0, "cpcm_dielectric_eh": -0.01, "smd_cds_eh": -0.17}
    assert b13.bare_electronic(entry) == pytest.approx(-100.0 + 0.01 + 0.17)
    assert b13.bare_electronic({}) == 0.0


def test_bare_electronic_is_the_bare_cpcm_total_for_a_bare_run():
    entry = {"total_energy_eh": -100.0, "cpcm_dielectric_eh": -0.013, "smd_cds_eh": None}
    assert b13.bare_electronic(entry) == pytest.approx(-100.0 + 0.013)


def _synthetic_ledger():
    gas = {"final_single_point_eh": 0.0, "total_energy_eh": 0.0}
    table = {
        ("m", "gas", "neutral"): dict(gas),
        ("m", "gas", "cation"): dict(gas),
        ("m", "gas", "anion"): dict(gas),
    }
    env = {
        "neutral": {"total_energy_eh": -0.02, "cpcm_dielectric_eh": -0.01, "smd_cds_eh": -0.17},
        "cation": {"total_energy_eh": 0.04, "cpcm_dielectric_eh": -0.02, "smd_cds_eh": -0.17},
        "anion": {"total_energy_eh": -0.06, "cpcm_dielectric_eh": -0.03, "smd_cds_eh": -0.17},
    }
    for state, terms in env.items():
        entry = dict(terms)
        entry["final_single_point_eh"] = terms["total_energy_eh"]
        table[("m", "env", state)] = entry
    return table


def test_decompose_axis_splits_a_synthetic_shift_exactly():
    table = _synthetic_ledger()
    parts = b13.decompose_axis(table, "m", "env", "oxidation")
    assert parts["residual_ev"] == pytest.approx(0.0, abs=1e-12)
    assert parts["d_total_ev"] == pytest.approx(0.06 * b13.HARTREE_TO_EV, abs=1e-9)
    assert parts["diel_ev"] + parts["dist_ev"] == pytest.approx(parts["d_total_ev"], abs=1e-12)
    assert parts["cds_ev"] == 0.0


def test_decompose_axis_uses_a_state_independent_cds_term():
    table = _synthetic_ledger()
    for axis in ("oxidation", "reduction"):
        parts = b13.decompose_axis(table, "m", "env", axis)
        assert parts["cds_ev"] == 0.0


def test_decompose_axis_returns_zero_residual_for_either_axis():
    table = _synthetic_ledger()
    for axis in b13.AXIS_STATES:
        assert b13.decompose_axis(table, "m", "env", axis)["residual_ev"] == pytest.approx(0.0, abs=1e-12)


def test_fmt_never_prints_a_negative_zero():
    assert s13._fmt(-1e-12, 4) == "0.0000"
    assert s13._fmt(-0.0001, 3) == "0.000"
    assert s13._fmt(None) == "\u2014"


def test_signed_keeps_the_minus_sign_of_a_real_negative():
    assert s13._signed(-2.5, 3) == "-2.500"
    assert s13._signed(2.5, 3) == "+2.500"
    assert s13._signed(-1e-12, 3) == "+0.000"


def test_levels_are_in_report_order():
    tags = [level["tag"] for level in b13.LEVELS]
    assert tags == ["gas", "cpcm_5", "cpcm_10", "cpcm_20", "cpcm_40", "cpcm_80",
                    "cpcm_200", "smd_acetonitrile", "smd_water"]
    assert [level["nominal_epsilon"] for level in b13.LEVELS if level["kind"] == "bare_cpcm"] == [
        5.0, 10.0, 20.0, 40.0, 80.0, 200.0]


def test_the_new_layers_of_this_week_are_the_expected_three():
    new = tuple(level["tag"] for level in b13.LEVELS if level["root"] == b13.WEEK12)
    assert new == ("cpcm_80", "cpcm_200", "smd_water")


def test_subset_names_match_the_t3_audit_subset():
    assert len(b13.SUBSET_NAMES) == 12
    assert len(set(b13.SUBSET_NAMES)) == 12
    assert set(b13.COMMON10_NAMES) < set(b13.SUBSET_NAMES)


def test_bare_eps_and_tags_line_up():
    assert len(s13.BARE_EPS) == len(s13.BARE_TAGS) == 6
    assert len(b13.BARE_TAGS) == 7  # gas + the six bare dielectrics
    assert s13.BARE_TAGS == tuple(tag for tag in b13.BARE_TAGS if tag != "gas")
    assert s13.SMD_TAGS == b13.SMD_TAGS