"""T3 (bare-CPCM dielectric scan) pure-function tests.

Nothing here runs ORCA: the eps label round-trip, the core-set subset
resolution, the long-table column contract, the sigma_env definition, the row
builder and the decision metrics are all exercised on hand-written numbers, so
the suite stays green on a machine with no engine installed.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
for _directory in (REPO_ROOT / "src", REPO_ROOT / "scripts"):
    if str(_directory) not in sys.path:
        sys.path.insert(0, str(_directory))

from analyze_cpcm_eps_scan import (  # noqa: E402
    COLUMNS,
    EPS_VALUES,
    HARTREE_TO_EV,
    SUBSET_NAMES,
    TARGET_NAMES,
    decision_metrics,
    eps_label,
    family_coverage,
    load_core_set,
    load_rows,
    parse_eps_label,
    ranking_vectors,
    resolve_subset,
    scan_row,
    shift_stats,
    sigma_env,
    write_rows,
)

LABELS = ["m0", "m1", "m2", "m3"]


def _core_rows() -> list[dict]:
    return load_core_set(REPO_ROOT / "data" / "metadata" / "core_set.csv")


def _layer(ip: float | None, ea: float | None, *, name: str = "EC", status: str = "ok") -> dict:
    """A layer whose vertical IP / EA are exactly (ip, ea), built from Eh energies."""

    def record(energy, state):
        return {
            "status": status,
            "result": {"final_energy_eh": energy},
            "qc_flags": [],
        }

    neutral = 0.0
    cation = None if ip is None else ip / HARTREE_TO_EV
    anion = None if ea is None else -ea / HARTREE_TO_EV
    records = {
        (name, "neutral"): record(neutral, "neutral"),
        (name, "cation"): record(cation, "cation"),
        (name, "anion"): record(anion, "anion"),
    }
    if status != "ok":
        for key in records:
            records[key]["status"] = status
    return records

# --------------------------------------------------------------------------- #
# A. the eps labels, byte-for-byte with the runner
# --------------------------------------------------------------------------- #
def test_scan_dielectrics_are_the_four_frozen_points():
    assert EPS_VALUES == (5.0, 10.0, 20.0, 40.0)


def test_eps_label_matches_the_runner_formatting():
    assert [eps_label(value) for value in EPS_VALUES] == ["cpcm_5", "cpcm_10", "cpcm_20", "cpcm_40"]


@pytest.mark.parametrize("value", [5.0, 10.0, 20.0, 40.0, 7.5])
def test_eps_label_round_trips(value):
    assert parse_eps_label(eps_label(value)) == pytest.approx(value)


def test_parse_eps_label_accepts_a_bare_number_and_whitespace():
    assert parse_eps_label("20") == pytest.approx(20.0)
    assert parse_eps_label(" cpcm_40 ") == pytest.approx(40.0)
    with pytest.raises(ValueError):
        parse_eps_label("cpcm_nan_ish")


# --------------------------------------------------------------------------- #
# B. the subset comes from core_set.csv, and it must span every family
# --------------------------------------------------------------------------- #
def test_subset_order_is_fixed_and_mol_ids_come_from_the_core_set():
    rows = resolve_subset(_core_rows())
    assert [row["name"] for row in rows] == list(SUBSET_NAMES)
    assert len(TARGET_NAMES) == 10
    assert rows[0]["name"] == "EC" and rows[0]["mol_id"] == "C04"
    assert rows[0]["family"] == "cyclic_carbonate"
    assert rows[-1]["name"] == "TMP" and rows[-1]["mol_id"] == "C17"


def test_subset_covers_every_core_set_family():
    core = _core_rows()
    coverage = family_coverage(resolve_subset(core), core)
    assert coverage["families_not_in_subset"] == []
    assert coverage["n_families_in_subset"] == len(coverage["families_in_core_set"]) == 8


def test_missing_subset_molecule_is_reported_not_silently_dropped():
    core = [row for row in _core_rows() if row["name"] != "SN"]
    with pytest.raises(SystemExit):
        resolve_subset(core)


# --------------------------------------------------------------------------- #
# C. the sigma_env definition
# --------------------------------------------------------------------------- #
def test_sigma_env_is_the_population_std_of_the_shift():
    assert sigma_env([0.0, 1.0]) == pytest.approx(0.5)
    assert sigma_env([-1.0, 1.0]) == pytest.approx(1.0)
    assert sigma_env([2.0, 2.0, 2.0]) == pytest.approx(0.0)


def test_sigma_env_skips_missing_values_and_needs_two_points():
    assert sigma_env([None, None]) is None
    assert sigma_env([0.5]) is None
    assert sigma_env([0.0, 1.0, None]) == pytest.approx(0.5)


def test_sigma_env_is_blind_to_a_common_translation():
    shift = [0.1, -0.4, 0.9, -0.6]
    assert sigma_env([value + 3.0 for value in shift]) == pytest.approx(sigma_env(shift))


def test_shift_stats_reports_population_spread_and_skips_missing():
    stats = shift_stats([0.0, 1.0, None])
    assert stats["n"] == 2
    assert stats["mean_ev"] == pytest.approx(0.5)
    assert stats["std_ev"] == pytest.approx(0.5)
    assert stats["min_ev"] == pytest.approx(0.0)
    assert stats["max_ev"] == pytest.approx(1.0)
    empty = shift_stats([None])
    assert empty["n"] == 0 and empty["mean_ev"] is None and empty["std_ev"] is None

# --------------------------------------------------------------------------- #
# D. the long-table contract
# --------------------------------------------------------------------------- #
def test_long_table_columns_are_the_frozen_contract():
    assert COLUMNS == [
        "mol_id", "name", "family", "eps", "ip_ev", "ea_ev",
        "d_ip_vs_gas_ev", "d_ea_vs_gas_ev", "status", "qc_flags",
    ]


def test_scan_row_shifts_against_the_gas_phase_layer():
    row = {"mol_id": "C04", "name": "EC", "family": "cyclic_carbonate"}
    out = scan_row(row, 20.0, _layer(10.0, 1.0), _layer(8.0, 3.0))
    assert set(out) == set(COLUMNS)
    assert out["mol_id"] == "C04" and out["family"] == "cyclic_carbonate"
    assert out["eps"] == pytest.approx(20.0)
    assert out["ip_ev"] == pytest.approx(8.0)
    assert out["ea_ev"] == pytest.approx(3.0)
    assert out["d_ip_vs_gas_ev"] == pytest.approx(-2.0)
    assert out["d_ea_vs_gas_ev"] == pytest.approx(2.0)
    assert out["status"] == "ok"


def test_scan_row_marks_incomplete_instead_of_guessing():
    row = {"mol_id": "C04", "name": "EC", "family": "cyclic_carbonate"}
    out = scan_row(row, 5.0, _layer(10.0, 1.0), _layer(None, 3.0))
    assert out["status"] == "incomplete"
    assert out["ip_ev"] is None
    assert out["d_ip_vs_gas_ev"] is None
    # the EA side is still reported: one missing state must not hide the other
    assert out["ea_ev"] == pytest.approx(3.0)
    assert out["d_ea_vs_gas_ev"] == pytest.approx(2.0)


def test_scan_row_does_not_trust_a_failed_job():
    row = {"mol_id": "C04", "name": "EC", "family": "cyclic_carbonate"}
    out = scan_row(row, 5.0, _layer(10.0, 1.0), _layer(8.0, 3.0, status="execution_failed"))
    assert out["ip_ev"] is None and out["ea_ev"] is None
    assert out["status"] == "incomplete"


def test_scan_row_carries_the_qc_flags_of_the_layer():
    row = {"mol_id": "C04", "name": "EC", "family": "cyclic_carbonate"}
    layer = _layer(8.0, 3.0)
    layer[("EC", "anion")]["qc_flags"] = ["scf_failed"]
    out = scan_row(row, 5.0, _layer(10.0, 1.0), layer)
    assert out["qc_flags"] == "scf_failed"


def test_long_table_round_trips_through_the_csv(tmp_path):
    row = {"mol_id": "C04", "name": "EC", "family": "cyclic_carbonate"}
    rows = [scan_row(row, eps, _layer(10.0, 1.0), _layer(8.0, None)) for eps in EPS_VALUES]
    path = write_rows(tmp_path / "t3.csv", rows)
    back = load_rows(path)
    assert len(back) == len(EPS_VALUES)
    assert [record["eps"] for record in back] == [5.0, 10.0, 20.0, 40.0]
    assert back[0]["ip_ev"] == pytest.approx(8.0)
    assert back[0]["d_ip_vs_gas_ev"] == pytest.approx(-2.0)
    # an empty cell must come back as None, never as 0.0
    assert back[0]["ea_ev"] is None
    assert back[0]["d_ea_vs_gas_ev"] is None


# --------------------------------------------------------------------------- #
# E. the two ranking axes
# --------------------------------------------------------------------------- #
def test_ranking_vectors_orient_both_axes_so_larger_is_better():
    rows = [{"eps": 5.0, "status": "ok", "name": "EC", "ip_ev": 8.0, "ea_ev": -0.5}]
    labels, gas_ox, cpcm_ox, gas_red, cpcm_red = ranking_vectors(rows, 5.0, {"EC": (10.0, 1.0)})
    assert labels == ["EC"]
    assert gas_ox == [10.0] and cpcm_ox == [8.0]
    assert gas_red == [-1.0] and cpcm_red == [0.5]


def test_ranking_vectors_drop_incomplete_rows_rather_than_padding():
    rows = [{"eps": 5.0, "status": "incomplete", "name": "EC", "ip_ev": None, "ea_ev": None}]
    assert ranking_vectors(rows, 5.0, {"EC": (10.0, 1.0)})[0] == []
    assert ranking_vectors(rows, 10.0, {"EC": (10.0, 1.0)})[0] == []

# --------------------------------------------------------------------------- #
# F. the decision metrics (thin re-keying of analyze_p1_core_set.layer_stability)
# --------------------------------------------------------------------------- #
def _block(gas, layer, labels=LABELS) -> dict:
    return decision_metrics(gas, layer, labels, higher_is_better=True)


def test_identical_layers_are_perfectly_resolved_and_never_invert():
    gas = [0.0, 1.0, 2.0, 3.0]
    block = _block(gas, list(gas))
    assert block["n"] == 4
    assert block["kendall_tau_b"] == pytest.approx(1.0)
    assert block["spearman_rho"] == pytest.approx(1.0)
    assert block["f_unresolved_gas"] == pytest.approx(0.0)
    assert block["f_unresolved_cpcm"] == pytest.approx(0.0)
    assert block["f_robust_inv"] == pytest.approx(0.0)
    assert block["o_k"]["0.20"] == pytest.approx(1.0)
    assert block["j_k_20"] == pytest.approx(1.0)
    assert block["selection_regret_20_ev"] == pytest.approx(0.0)


def test_the_primary_band_is_z_one_and_the_sensitivity_band_is_z_one_nine_six():
    block = _block([0.0, 1.0, 2.0, 3.0], [0.0, 1.0, 2.0, 3.0])
    assert block["z_primary"] == pytest.approx(1.0)
    assert block["z_sensitivity"] == pytest.approx(1.96)


def test_a_pure_common_translation_changes_nothing():
    gas = [0.0, 1.0, 2.0, 3.0, 4.0]
    labels = ["m%d" % index for index in range(5)]
    shift = -2.5
    block = decision_metrics(gas, [value + shift for value in gas], labels)
    assert block["kendall_tau_b"] == pytest.approx(1.0)
    assert block["f_robust_inv"] == pytest.approx(0.0)
    # the shift is constant, so its molecule-to-molecule spread is exactly zero
    assert sigma_env([shift] * 5) == pytest.approx(0.0)


def test_rank_agreement_is_non_increasing_as_the_shift_reverses_the_order():
    # layer_i = gas_i - strength*i: at strength = 0 the two layers agree, and by
    # strength = 2 the screened layer is the exact reverse of the gas phase.
    gas = [0.0, 1.0, 2.0, 3.0]
    taus = [
        _block(gas, [value - strength * index for index, value in enumerate(gas)])["kendall_tau_b"]
        for strength in (0.0, 0.5, 1.5, 2.0)
    ]
    assert None not in taus
    assert taus == sorted(taus, reverse=True)
    assert taus[0] == pytest.approx(1.0)
    assert taus[1] == pytest.approx(1.0)
    assert taus[-1] == pytest.approx(-1.0)


def test_top_k_fractions_are_reported_at_ten_twenty_and_thirty_percent():
    gas = [float(index) for index in range(10)]
    labels = ["m%d" % index for index in range(10)]
    block = decision_metrics(gas, list(gas), labels)
    assert sorted(block["o_k"]) == ["0.10", "0.20", "0.30"]
    assert all(value == pytest.approx(1.0) for value in block["o_k"].values())


@pytest.mark.parametrize("strength", [0.0, 0.25, 1.0, 2.5, 10.0])
def test_decision_fractions_stay_inside_the_unit_interval(strength):
    gas = [0.0, 1.0, 2.0, 3.0, 4.0, 5.0]
    labels = ["m%d" % index for index in range(6)]
    layer = [value - strength * index for index, value in enumerate(gas)]
    block = decision_metrics(gas, layer, labels)
    for key in ("f_unresolved_gas", "f_unresolved_cpcm", "f_robust_inv",
                "f_unresolved_gas_z1p96", "f_unresolved_cpcm_z1p96", "f_robust_inv_z1p96"):
        assert 0.0 <= block[key] <= 1.0
    tau = block["kendall_tau_b"]
    rho = block["spearman_rho"]
    assert tau is None or -1.0 <= tau <= 1.0
    assert rho is None or -1.0 <= rho <= 1.0


def test_a_wider_band_never_resolves_more_pairs():
    gas = [0.0, 1.0, 2.0, 3.0, 4.0, 5.0]
    labels = ["m%d" % index for index in range(6)]
    block = decision_metrics(gas, [0.1, 1.4, 1.9, 3.6, 4.0, 5.2], labels)
    assert block["f_unresolved_cpcm"] <= block["f_unresolved_cpcm_z1p96"]
    assert block["f_unresolved_gas"] <= block["f_unresolved_gas_z1p96"]


def test_an_all_tie_layer_reports_an_undefined_correlation_not_nan():
    # tau_b and rho are NaN when one side is constant; the report wrapper has to
    # degrade that to None, because JSON has no NaN literal.
    gas = [0.0, 1.0, 2.0, 3.0]
    block = _block(gas, [0.0, 0.0, 0.0, 0.0])
    assert block["kendall_tau_b"] is None
    assert block["spearman_rho"] is None
    assert block["f_robust_inv"] == pytest.approx(0.0)


def test_decision_metrics_refuse_to_report_a_single_molecule():
    block = decision_metrics([1.0], [2.0], ["only"])
    assert block["n"] == 1
    assert block["kendall_tau_b"] is None
    assert block["f_robust_inv"] is None