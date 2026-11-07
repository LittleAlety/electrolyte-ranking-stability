"""Regression tests for the xTB method-audit comparison logic.

The audit itself needs a real engine, but the part that decides whether a proxy
is offset or re-ordered is pure arithmetic and is what the Stage 1 conclusion
rests on, so it is pinned here against hand-checkable input.
"""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from run_method_audit_xtb import _load_anchors, compare


def _write_anchors(tmp_path: Path, rows: list[dict]) -> Path:
    path = tmp_path / "anchors.csv"
    columns = ["species", "smiles", "property", "value_eV", "uncertainty_eV", "method"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    return path


def test_anchor_rows_without_a_value_are_skipped(tmp_path: Path) -> None:
    path = _write_anchors(tmp_path, [
        {"species": "EC", "smiles": "x", "property": "IP", "value_eV": "10.4", "uncertainty_eV": "0.1", "method": "exp"},
        {"species": "PC", "smiles": "y", "property": "IP", "value_eV": "", "uncertainty_eV": "", "method": "na"},
    ])
    grouped = _load_anchors(path)
    assert ("EC", "IP") in grouped
    assert ("PC", "IP") not in grouped


def test_several_determinations_are_averaged_and_their_spread_kept(tmp_path: Path) -> None:
    path = _write_anchors(tmp_path, [
        {"species": "DME", "smiles": "x", "property": "IP", "value_eV": "9.3", "uncertainty_eV": "0.1", "method": "exp"},
        {"species": "DME", "smiles": "x", "property": "IP", "value_eV": "9.9", "uncertainty_eV": "0.1", "method": "exp"},
    ])
    anchors = _load_anchors(path)
    records = [{"mol_id": "DME", "vertical_ip_ev": 10.6, "ip_koopmans_ev": 10.0, "vertical_ea_ev": None, "ea_koopmans_ev": None}]
    summary = compare(records, anchors)["IP_dscf_vertical"]
    assert summary["n"] == 1
    assert summary["pairs"][0]["anchor_ev"] == pytest.approx(9.6)
    assert summary["anchor_spread_ev"] == pytest.approx(0.3)


def test_a_pure_offset_keeps_a_perfect_rank_correlation(tmp_path: Path) -> None:
    # v2 section 22.2: identical ordering, large constant shift.
    path = _write_anchors(tmp_path, [
        {"species": name, "smiles": "x", "property": "IP", "value_eV": str(value), "uncertainty_eV": "0.1", "method": "exp"}
        for name, value in (("A", 8.0), ("B", 9.0), ("C", 10.0), ("D", 11.0))
    ])
    anchors = _load_anchors(path)
    offset = 4.0
    records = [
        {"mol_id": name, "vertical_ip_ev": value + offset, "vertical_ea_ev": None,
         "ip_koopmans_ev": None, "ea_koopmans_ev": None}
        for name, value in (("A", 8.0), ("B", 9.0), ("C", 10.0), ("D", 11.0))
    ]
    summary = compare(records, anchors)["IP_dscf_vertical"]
    assert summary["mae_ev"] == pytest.approx(4.0)
    assert summary["error_std_ev"] == pytest.approx(0.0)
    assert summary["kendall_tau_b"] == pytest.approx(1.0)


def test_a_reordered_pair_breaks_the_rank_correlation(tmp_path: Path) -> None:
    path = _write_anchors(tmp_path, [
        {"species": name, "smiles": "x", "property": "IP", "value_eV": str(value), "uncertainty_eV": "0.1", "method": "exp"}
        for name, value in (("A", 8.0), ("B", 9.0))
    ])
    anchors = _load_anchors(path)
    records = [
        {"mol_id": "A", "vertical_ip_ev": 12.0, "vertical_ea_ev": None, "ip_koopmans_ev": None, "ea_koopmans_ev": None},
        {"mol_id": "B", "vertical_ip_ev": 11.0, "vertical_ea_ev": None, "ip_koopmans_ev": None, "ea_koopmans_ev": None},
    ]
    summary = compare(records, anchors)["IP_dscf_vertical"]
    assert summary["kendall_tau_b"] == pytest.approx(-1.0)
    assert summary["mae_ev"] > 0


def test_missing_computed_values_are_not_counted(tmp_path: Path) -> None:
    path = _write_anchors(tmp_path, [
        {"species": "EC", "smiles": "x", "property": "IP", "value_eV": "10.4", "uncertainty_eV": "0.1", "method": "exp"},
    ])
    anchors = _load_anchors(path)
    records = [{"mol_id": "EC", "vertical_ip_ev": None, "vertical_ea_ev": None, "ip_koopmans_ev": None, "ea_koopmans_ev": None}]
    summary = compare(records, anchors)
    assert summary["IP_dscf_vertical"]["n"] == 0
    assert summary["IP_koopmans_p0"]["n"] == 0
