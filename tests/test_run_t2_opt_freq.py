"""T2 (Opt+Freq at G2, then P1 at G2) pure-function tests.

Nothing here runs ORCA. The subset contract, the P1 sign convention, the
population spread, the CARTESIAN-block parser, the optimiser step counter and
the per-molecule row builder are all exercised on hand-written text, so the
suite stays green on a machine with no engine installed.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
for _directory in (REPO_ROOT / "src", REPO_ROOT / "scripts"):
    if str(_directory) not in sys.path:
        sys.path.insert(0, str(_directory))

from analyze_cpcm_eps_scan import SUBSET_NAMES as T3_SUBSET  # noqa: E402
from run_t2_opt_freq import (  # noqa: E402
    COLUMNS,
    G2_BLOCK,
    HARTREE_TO_EV,
    STATES,
    T2_SUBSET_NAMES,
    build_row,
    build_summary,
    count_opt_cycles,
    final_geometry,
    load_core_set,
    opt_converged,
    population_spread,
    select_rows,
    vertical_layer,
    write_xyz,
)

CORE_SET = REPO_ROOT / "data" / "metadata" / "core_set.csv"


def _core_rows() -> list[dict]:
    return load_core_set(CORE_SET)


def _orca_text(blocks: int, *, converged: bool = True, cycles: int = 1, imaginary: bool = False) -> str:
    text = "ORCA 6.1.1\n"
    if converged:
        text += "THE OPTIMIZATION HAS CONVERGED\n"
    text += "GEOMETRY OPTIMIZATION CYCLE" * cycles
    for step in range(blocks):
        text += G2_BLOCK + chr(10) + "-" * 20 + chr(10)
        text += "  C   %10.6f %10.6f %10.6f" % (0.0 + step, 0.0, 0.0) + chr(10)
        text += "  O   %10.6f %10.6f %10.6f" % (1.2, 0.0, 0.0) + chr(10)
        text += chr(10)
    if imaginary:
        text += "     6:    -118.16 cm**-1  ***imaginary mode***" + chr(10)
    return text


# --------------------------------------------------------------------------- #
# A. the subset contract: 12 molecules, the same sample as the T3 scan
# --------------------------------------------------------------------------- #
def test_t2_subset_is_the_same_twelve_molecules_as_the_t3_scan():
    assert T2_SUBSET_NAMES == tuple(T3_SUBSET)
    assert len(T2_SUBSET_NAMES) == 12


def test_t2_subset_spans_every_core_set_family():
    cores = _core_rows()
    families = {row["family"] for row in cores if row["name"] in T2_SUBSET_NAMES}
    all_families = {row["family"] for row in cores}
    assert families == all_families
    assert len(families) == 8


def test_select_rows_uses_the_fixed_order_and_honours_only_and_limit():
    rows = select_rows(_core_rows())
    assert [row["name"] for row in rows] == list(T2_SUBSET_NAMES)
    assert [row["mol_id"] for row in rows][:2] == ["C04", "C05"]
    assert [row["name"] for row in select_rows(_core_rows(), only="EC,SL")] == ["EC", "SL"]
    assert [row["name"] for row in select_rows(_core_rows(), only="C17")] == ["TMP"]
    assert len(select_rows(_core_rows(), limit=3)) == 3


def test_a_subset_molecule_missing_from_the_core_set_is_reported_not_dropped():
    cores = [row for row in _core_rows() if row["name"] != "AN"]
    with pytest.raises(SystemExit):
        select_rows(cores)


# --------------------------------------------------------------------------- #
# B. the P1 sign convention and the population spread
# --------------------------------------------------------------------------- #
def test_vertical_layer_uses_the_frozen_ip_and_ea_sign_convention():
    energies = {"neutral": -100.0, "cation": -99.5, "anion": -100.25}
    ip, ea = vertical_layer(energies, hartree_to_ev=1.0)
    assert ip == pytest.approx(0.5)
    assert ea == pytest.approx(0.25)
    assert vertical_layer({"neutral": -100.0}, hartree_to_ev=1.0) == (None, None)


def test_vertical_layer_converts_hartree_to_ev():
    ip, ea = vertical_layer({"neutral": -100.0, "cation": -99.0, "anion": -101.0})
    assert ip == pytest.approx(1.0 * HARTREE_TO_EV)
    assert ea == pytest.approx(1.0 * HARTREE_TO_EV)


def test_population_spread_is_the_population_std_and_needs_two_points():
    assert population_spread([1.0, 3.0]) == pytest.approx(1.0)
    assert population_spread([0.0, 0.0, 0.0]) == pytest.approx(0.0)
    assert population_spread([2.0]) is None
    assert population_spread([None, None]) is None


def test_a_pure_common_translation_gives_zero_sigma_geom():
    deltas = [0.31, 0.31, 0.31, 0.31]
    assert population_spread(deltas) == pytest.approx(0.0)


# --------------------------------------------------------------------------- #
# C. parsing the Opt output
# --------------------------------------------------------------------------- #
def test_final_geometry_returns_the_last_cartesian_block():
    geometry = final_geometry(_orca_text(blocks=3))
    assert geometry is not None
    lines = geometry.splitlines()
    assert len(lines) == 2
    assert lines[0].split()[0] == "C"
    assert float(lines[0].split()[1]) == pytest.approx(2.0)


def test_final_geometry_returns_none_without_a_cartesian_block():
    assert final_geometry("nothing to see here" + chr(10)) is None


def test_opt_cycle_counter_and_the_convergence_marker():
    text = _orca_text(blocks=1, cycles=6)
    assert count_opt_cycles(text) == 6
    assert opt_converged(text) is True
    assert opt_converged(_orca_text(blocks=1, converged=False, cycles=1)) is False


def test_write_xyz_header_counts_the_atoms(tmp_path: Path):
    target = tmp_path / "EC_G2.xyz"
    write_xyz(target, "EC G2", "C   0.0 0.0 0.0" + chr(10) + "O   1.2 0.0 0.0", 0, 1)
    lines = target.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "2"
    assert "EC G2" in lines[1]
    assert len(lines) == 4


# --------------------------------------------------------------------------- #
# D. the per-molecule row and the summary
# --------------------------------------------------------------------------- #
def _sp(*energies):
    states = ("neutral", "cation", "anion")
    return [{"state": state, "status": "ok", "energy_eh": value, "qc_flags": [], "error": ""}
            for state, value in zip(states, energies)]


def test_build_row_reports_the_g1_to_g2_shift_and_the_flags():
    row = {"mol_id": "C04", "name": "EC", "family": "cyclic_carbonate"}
    option = {"opt_status": "ok", "imaginary_modes": True, "opt_seconds": 68.0,
              "n_opt_cycles": 6, "opt_converged": True, "qc_flags": [],
              "g2_geometry": "outputs/week4/t2_opt_freq/EC/EC_G2.xyz", "error": ""}
    g1_layer = (-9.0, 1.0)
    built = build_row(row, option, _sp(-100.0, -99.5, -101.0), g1_layer, 10)
    assert built["ip_g2_ev"] == pytest.approx(0.5 * HARTREE_TO_EV)
    assert built["d_ip_ev"] == pytest.approx(0.5 * HARTREE_TO_EV - (-9.0))
    assert built["d_ea_ev"] == pytest.approx(1.0 * HARTREE_TO_EV - 1.0)
    assert "imaginary_mode_unresolved" in built["qc_flags"]
    assert built["sp_status"] == "ok"


def test_build_row_marks_a_failed_opt_as_geometry_failed():
    row = {"mol_id": "C04", "name": "EC", "family": "cyclic_carbonate"}
    option = {"opt_status": "geometry_failed", "qc_flags": ["geometry_failed"],
              "imaginary_modes": None, "opt_seconds": 1.0, "n_opt_cycles": 0,
              "opt_converged": False, "g2_geometry": None, "error": "boom"}
    built = build_row(row, option, [], (None, None), None)
    assert built["opt_status"] == "geometry_failed"
    assert "geometry_failed" in built["qc_flags"]
    assert built["d_ip_ev"] is None
    assert built["sp_status"] == "skipped"


def test_build_summary_defines_sigma_geom_and_counts_the_jobs(_args):
    rows = []
    for index, (name, d_ip, d_ea) in enumerate(
            [("EC", 0.10, -0.20), ("PC", 0.30, -0.40), ("DMC", 0.20, -0.30)]):
        rows.append({
            "mol_id": "C%02d" % index, "name": name, "family": "f",
            "opt_status": "ok", "sp_status": "ok", "imaginary_modes": False,
            "d_ip_ev": d_ip, "d_ea_ev": d_ea, "ip_g1_ev": 0.0, "ea_g1_ev": 0.0,
            "ip_g2_ev": d_ip, "ea_g2_ev": d_ea, "qc_flags": "", "g2_geometry": "", "error": "",
        })
    summary = build_summary(rows, _args, "6.1.1", "2026-09-29T00:00:00Z")
    assert summary["stage"] == "T2"
    assert summary["n_molecules"] == 3
    assert summary["n_opt_ok"] == 3
    assert summary["sigma_geom"]["d_ip_ev"]["population_std_ev"] == pytest.approx(
        population_spread([0.10, 0.30, 0.20]))
    assert "pstdev" in summary["definitions"]["sigma_geom"]


T2_SUMMARY = REPO_ROOT / "outputs" / "week4" / "t2_opt_freq_summary.json"


@pytest.mark.skipif(not T2_SUMMARY.exists(), reason="T2 summary not produced yet")
def test_produced_t2_summary_covers_the_whole_subset_without_failures():
    payload = json.loads(T2_SUMMARY.read_text(encoding="utf-8"))
    assert payload["n_molecules"] == len(T2_SUBSET_NAMES) == 12
    assert payload["n_opt_jobs"] == 12
    assert payload["n_opt_ok"] == 12
    assert payload["n_failed"] == 0
    assert payload["subset"] == list(T2_SUBSET_NAMES)
    for row in payload["per_molecule"]:
        assert row["opt_status"] == "ok"
        assert row["opt_converged"] is True
        assert row["d_ip_ev"] is not None and row["d_ea_ev"] is not None
        assert set(row) >= set(COLUMNS)


@pytest.fixture
def _args():
    class Args:
        skip_sp = False
        jobs = 2
        nprocs = 8
        csv = "outputs/week4/t2_opt_freq.csv"
        summary = "outputs/week4/t2_opt_freq_summary.json"
        outdir = "outputs/week4"
    return Args()
