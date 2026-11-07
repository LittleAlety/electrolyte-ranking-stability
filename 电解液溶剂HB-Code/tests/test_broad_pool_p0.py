"""Unit tests for the Week-3 broad-pool P0 pipeline helpers.

The real xTB runs are not exercised here (they belong to the pipeline run); the
pure helpers that assemble P0 rows, decide resume behaviour, bin the chemical
space and compute decision-stability arithmetic are pinned against
hand-checkable input. One end-to-end test runs against the real binary when it
is available and is skipped otherwise.
"""

from __future__ import annotations

import csv
import math
from pathlib import Path

import pytest

from run_broad_pool_p0 import (
    P0_COLUMNS,
    build_coverage_tables,
    build_p0_row,
    decision_analysis,
    descriptor_stats,
    family_counts,
    is_cyclic,
    is_flexible,
    is_fluorinated,
    jaccard,
    k_abs_for_n,
    kendall,
    load_pool,
    mw_bin,
    normalise_row,
    p0_descriptors,
    rotatable_bin,
    select_molecules,
    should_reuse,
    summarise_rows,
    tag_set,
    top_k_ids,
)

BROAD_COLUMNS = [
    "mol_id",
    "name",
    "smiles",
    "family",
    "role",
    "donor_atoms",
    "donor_count",
    "heteroatom_count",
    "n_heavy",
    "mw",
    "rotatable_bonds",
    "tpsa",
    "functionalization_tags",
    "pool_reason",
]

CORE_COLUMNS = BROAD_COLUMNS[:-1] + ["reason_included"]


def _write_csv(path: Path, columns, rows) -> Path:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    return path


def _broad_row(mol_id, name, family, *, donor=2, mw=100.0, rot=1, tags="linear"):
    return {
        "mol_id": mol_id,
        "name": name,
        "smiles": "CCO",
        "family": family,
        "role": "co-solvent",
        "donor_atoms": "O-",
        "donor_count": donor,
        "heteroatom_count": donor,
        "n_heavy": 5,
        "mw": mw,
        "rotatable_bonds": rot,
        "tpsa": 20.0,
        "functionalization_tags": tags,
        "pool_reason": "test",
    }


def _ok_row(mol_id, name, ox, red, *, family="ether", tags="linear", mw=100.0, rot=1, alpha=50.0, dipole=1.0, status="ok"):
    return {
        "mol_id": mol_id,
        "name": name,
        "family": family,
        "role": "co-solvent",
        "donor_count": 2,
        "functionalization_tags": tags,
        "status": status,
        "p0_ox_ev": ox,
        "p0_red_ev": red,
        "hl_gap_ev": None if ox is None else ox - red,
        "dipole_debye": dipole,
        "aux_alpha_bohr3": alpha,
        "qc_flags": "",
        "xtb_version": "6.7.1pre",
        "geometry_source": "test",
        "smiles": "CCO",
        "pool": "test",
        "homo_ev": None if ox is None else -ox,
        "lumo_ev": red,
        "total_energy_eh": -1.0,
        "atom_count": 5,
        "error": "",
    }


# ---------------------------------------------------------------------------
# argument parsing
# ---------------------------------------------------------------------------
def test_parse_args_defaults() -> None:
    from run_broad_pool_p0 import parse_args

    args = parse_args([])
    assert args.pool == "broad"
    assert args.jobs == 4
    assert args.limit is None
    assert args.only is None
    assert args.force is False
    assert args.alpha_limit == 5
    assert args.seed == 0xC0FFEE


def test_parse_args_overrides() -> None:
    from run_broad_pool_p0 import parse_args

    args = parse_args([
        "--pool", "both", "--limit", "5", "--only", "B01,B02",
        "--jobs", "2", "--force", "--seed", "0x1", "--alpha-limit", "0",
    ])
    assert args.pool == "both"
    assert args.limit == 5
    assert args.only == "B01,B02"
    assert args.jobs == 2
    assert args.force is True
    assert args.seed == 1
    assert args.alpha_limit == 0


# ---------------------------------------------------------------------------
# CSV -> P0 row assembly
# ---------------------------------------------------------------------------
def test_load_pool_normalises_reason_columns(tmp_path: Path) -> None:
    broad = _write_csv(tmp_path / "b.csv", BROAD_COLUMNS, [_broad_row("B01", "MPC", "linear_carbonate")])
    core_base = _broad_row("C01", "DMC", "linear_carbonate")
    core_base.pop("pool_reason")
    core_base["reason_included"] = "core reason"
    core = _write_csv(tmp_path / "c.csv", CORE_COLUMNS, [core_base])
    broad_rows = load_pool(broad, "broad")
    core_rows = load_pool(core, "core")
    assert broad_rows[0]["reason"] == "test"
    assert broad_rows[0]["pool"] == "broad"
    assert core_rows[0]["reason"] == "core reason"
    assert broad_rows[0]["donor_count"] == 2
    assert broad_rows[0]["mw"] == 100.0


def test_normalise_row_handles_missing_numeric_fields() -> None:
    row = normalise_row({"mol_id": "X", "name": "x", "mw": "", "donor_count": "n/a"}, "broad")
    assert row["mw"] is None
    assert row["donor_count"] is None
    assert row["family"] == ""


def test_select_molecules_applies_only_then_limit() -> None:
    rows = [{"mol_id": mid} for mid in ("B01", "B02", "B03", "B04")]
    assert [r["mol_id"] for r in select_molecules(rows, only="B02,B04")] == ["B02", "B04"]
    assert [r["mol_id"] for r in select_molecules(rows, limit=2)] == ["B01", "B02"]
    assert [r["mol_id"] for r in select_molecules(rows, only="B03,B04", limit=1)] == ["B03"]


def test_p0_descriptors_from_result() -> None:
    result = {"homo_ev": -12.0, "lumo_ev": -5.0, "hl_gap_ev": 7.0, "dipole_debye": 2.5, "polarizability_alpha0": 40.0, "total_energy_eh": -20.0}
    descriptors = p0_descriptors(result)
    assert descriptors["p0_ox_ev"] == pytest.approx(12.0)
    assert descriptors["p0_red_ev"] == pytest.approx(-5.0)
    assert descriptors["hl_gap_ev"] == pytest.approx(7.0)
    assert descriptors["aux_alpha_bohr3"] == pytest.approx(40.0)


def test_p0_descriptors_missing_result_is_all_none() -> None:
    descriptors = p0_descriptors(None)
    assert all(value is None for value in descriptors.values())


def test_build_p0_row_success() -> None:
    meta = normalise_row({**_broad_row("B01", "MPC", "linear_carbonate"), "mol_id": "B01"}, "broad")
    record = {
        "status": "ok",
        "charge": 0,
        "multiplicity": 1,
        "atom_count": 18,
        "result": {"homo_ev": -11.9, "lumo_ev": -5.7, "hl_gap_ev": 6.2, "dipole_debye": 0.9, "polarizability_alpha0": 74.7},
        "qc_flags": [],
        "provenance": {"software_version": "6.7.1pre"},
    }
    row = build_p0_row(meta, record, geometry_source="test")
    assert row["status"] == "ok"
    assert row["p0_ox_ev"] == pytest.approx(11.9)
    assert row["p0_red_ev"] == pytest.approx(-5.7)
    assert row["xtb_version"] == "6.7.1pre"
    assert row["aux_alpha_bohr3"] == pytest.approx(74.7)
    assert set(P0_COLUMNS).issubset(row.keys())


def test_build_p0_row_failed_molecule_is_kept() -> None:
    meta = normalise_row(_broad_row("B09", "DEE", "ether"), "broad")
    record = {"status": "failed", "error": "RuntimeError: RDKit embedding failed", "charge": 0, "multiplicity": 1}
    row = build_p0_row(meta, record, geometry_source="test")
    assert row["status"] == "failed"
    assert row["p0_ox_ev"] is None
    assert "embedding failed" in row["error"]


def test_build_p0_row_missing_fields_is_flagged() -> None:
    meta = normalise_row(_broad_row("B10", "G2", "ether"), "broad")
    record = {"status": "ok", "charge": 0, "multiplicity": 1, "result": {"homo_ev": None, "lumo_ev": -5.0}, "qc_flags": [], "provenance": {}}
    row = build_p0_row(meta, record, geometry_source="test")
    assert row["status"] == "missing_p0_fields"
    assert row["p0_ox_ev"] is None
    assert row["p0_red_ev"] == pytest.approx(-5.0)


# ---------------------------------------------------------------------------
# resume behaviour
# ---------------------------------------------------------------------------
def test_should_reuse_existing_nonempty_record(tmp_path: Path) -> None:
    mol_dir = tmp_path / "B01"
    mol_dir.mkdir()
    (mol_dir / "MPC_xtb.json").write_text("{}", encoding="utf-8")
    assert should_reuse(mol_dir, "MPC", force=False) == mol_dir / "MPC_xtb.json"
    assert should_reuse(mol_dir, "MPC", force=True) is None


def test_should_reuse_missing_or_empty(tmp_path: Path) -> None:
    mol_dir = tmp_path / "B01"
    mol_dir.mkdir()
    assert should_reuse(mol_dir, "MPC", force=False) is None
    (mol_dir / "MPC_xtb.json").write_text("", encoding="utf-8")
    assert should_reuse(mol_dir, "MPC", force=False) is None


# ---------------------------------------------------------------------------
# summary statistics
# ---------------------------------------------------------------------------
def test_descriptor_stats_ignores_none() -> None:
    stats = descriptor_stats([1.0, None, 3.0, 2.0])
    assert stats["n"] == 3
    assert stats["min"] == 1.0
    assert stats["median"] == 2.0
    assert stats["max"] == 3.0


def test_descriptor_stats_empty() -> None:
    stats = descriptor_stats([None, None])
    assert stats == {"n": 0, "min": None, "median": None, "max": None}


def test_summarise_rows_counts_and_failures() -> None:
    rows = [
        {"mol_id": "A", "name": "a", "status": "ok", "p0_ox_ev": 1.0, "p0_red_ev": -1.0},
        {"mol_id": "B", "name": "b", "status": "failed", "error": "boom"},
        {"mol_id": "C", "name": "c", "status": "missing_p0_fields"},
    ]
    summary = summarise_rows(rows)
    assert summary["n_total"] == 3
    assert summary["n_ok"] == 1
    assert summary["n_failed"] == 1
    assert summary["n_missing_p0_fields"] == 1
    assert {f["mol_id"] for f in summary["failures"]} == {"B", "C"}
    assert summary["descriptor_stats"]["p0_ox_ev"]["n"] == 1


# ---------------------------------------------------------------------------
# coverage binning
# ---------------------------------------------------------------------------
def test_tag_helpers() -> None:
    row = {"functionalization_tags": "linear|fluorinated|cyclic", "rotatable_bonds": 3}
    assert tag_set(row) == {"linear", "fluorinated", "cyclic"}
    assert is_fluorinated(row) is True
    assert is_cyclic(row) is True
    assert is_flexible(row) is False
    assert is_flexible({"functionalization_tags": "flexible", "rotatable_bonds": 1}) is True
    assert is_flexible({"functionalization_tags": "", "rotatable_bonds": 5}) is True


def test_mw_and_rotatable_bins() -> None:
    assert mw_bin(50.0) == "<90"
    assert mw_bin(90.0) == "90-120"
    assert mw_bin(219.9) == "160-220"
    assert mw_bin(400.0) == ">=220"
    assert mw_bin(None) is None
    assert rotatable_bin(0) == "0"
    assert rotatable_bin(2) == "1-2"
    assert rotatable_bin(4) == "3-4"
    assert rotatable_bin(12) == "5+"
    assert rotatable_bin(None) is None


def test_family_counts_and_coverage_tables() -> None:
    core = [normalise_row(_broad_row("C01", "DMC", "linear_carbonate", mw=90.0), "core")]
    broad = [
        normalise_row(_broad_row("B01", "MPC", "linear_carbonate", mw=118.0, tags="linear"), "broad"),
        normalise_row(_broad_row("B03", "FEMC", "linear_carbonate", mw=158.0, tags="linear|fluorinated"), "broad"),
        normalise_row(_broad_row("B39", "HMDSO", "siloxane", mw=162.0, tags="linear|silicon_containing"), "broad"),
    ]
    assert family_counts(broad) == {"linear_carbonate": 2, "siloxane": 1}
    tables = build_coverage_tables(core, broad)
    assert "siloxane" in tables["families"]
    assert tables["family_counts_broad"]["siloxane"] == 1
    assert tables["flag_broad"]["fluorinated"] == {"yes": 1, "no": 2}
    assert tables["flag_core"]["fluorinated"] == {"yes": 0, "no": 1}
    assert tables["mw_bins_broad"]["90-120"] == 1
    assert tables["mw_bins_broad"]["160-220"] == 1


# ---------------------------------------------------------------------------
# decision-stability helpers
# ---------------------------------------------------------------------------
def test_k_abs_matches_preregistered_values() -> None:
    assert k_abs_for_n(18, 0.10) == 2
    assert k_abs_for_n(18, 0.20) == 4
    assert k_abs_for_n(18, 0.30) == 5
    assert k_abs_for_n(40, 0.10) == 4
    assert k_abs_for_n(40, 0.20) == 8
    assert k_abs_for_n(40, 0.30) == 12
    assert k_abs_for_n(0, 0.10) == 0


def test_top_k_ids_higher_and_lower() -> None:
    ids = ["a", "b", "c", "d"]
    values = [1.0, 4.0, 2.0, 3.0]
    assert top_k_ids(ids, values, 2, higher_is_better=True) == ["b", "d"]
    assert top_k_ids(ids, values, 2, higher_is_better=False) == ["a", "c"]
    # None values are excluded.
    assert top_k_ids(ids, [None, 4.0, None, 3.0], 5, higher_is_better=True) == ["b", "d"]


def test_jaccard_and_kendall() -> None:
    assert jaccard({"a", "b"}, {"a", "b"}) == pytest.approx(1.0)
    assert jaccard({"a", "b"}, {"b", "c"}) == pytest.approx(1 / 3)
    assert jaccard(set(), set()) == 1.0
    assert kendall([1, 2, 3], [1, 2, 3]) == pytest.approx(1.0)
    assert kendall([1, 2, 3], [3, 2, 1]) == pytest.approx(-1.0)
    assert kendall([1], [1]) is None


def test_decision_analysis_flags_objective_sensitivity() -> None:
    # Core: ox ranking [A>C>B]; red ranking is exactly reversed -> no top-k overlap.
    core = [
        _ok_row("A", "a", 12.0, -6.0),
        _ok_row("B", "b", 10.0, -4.0),
        _ok_row("C", "c", 11.0, -5.0),
    ]
    broad = [
        _ok_row("D", "d", 9.0, -3.0),
        _ok_row("E", "e", 8.0, -2.0),
    ]
    analysis = decision_analysis(core, broad)
    assert analysis["n_core_ok"] == 3
    assert analysis["n_broad_ok"] == 2
    assert analysis["n_combined"] == 5
    core_k1 = analysis["per_pool"]["core"]["k"]["0.10"]
    assert core_k1["k_abs"] == 1
    assert core_k1["ox_topk"] == ["A"]
    assert core_k1["red_topk"] == ["B"]
    assert core_k1["overlap_fraction_within_k"] == 0.0
    assert core_k1["jaccard"] == 0.0


def test_decision_analysis_excludes_failed_rows() -> None:
    core = [
        _ok_row("A", "a", 12.0, -6.0),
        _ok_row("F", "f", None, None, status="missing_p0_fields"),
        _ok_row("G", "g", 1.0, -1.0, status="failed"),
    ]
    broad = [_ok_row("D", "d", 9.0, -3.0)]
    analysis = decision_analysis(core, broad)
    assert analysis["n_core_ok"] == 1
    assert analysis["n_combined"] == 2


# ---------------------------------------------------------------------------
# real-engine smoke (skipped when xTB is absent)
# ---------------------------------------------------------------------------
def _xtb_available() -> bool:
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    from electrolyte_ranking import toolchain

    return toolchain.find_executable("xtb") is not None


@pytest.mark.skipif(not _xtb_available(), reason="xTB binary not available")
def test_run_one_real_xtb_small_molecule(tmp_path: Path) -> None:
    from run_broad_pool_p0 import run_one

    meta = normalise_row(_broad_row("B_SMOKE", "MPC", "linear_carbonate"), "broad")
    meta["smiles"] = "CCOC(=O)OC"
    row = run_one(meta, executable_path="xtb", scratch=tmp_path, timeout=300.0, seed=0xC0FFEE, force=True)
    assert row["status"] == "ok"
    assert row["p0_ox_ev"] is not None and math.isfinite(row["p0_ox_ev"])
    assert row["p0_red_ev"] is not None and math.isfinite(row["p0_red_ev"])
    assert row["xtb_version"]
