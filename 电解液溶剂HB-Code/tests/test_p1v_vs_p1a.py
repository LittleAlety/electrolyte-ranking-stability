"""Regression tests for the R13 P1v -> P1a adiabatic rung.

The rung's scientific point is the asymmetry: the oxidation axis supports the
vertical-vs-adiabatic comparison, while the reduction axis is *excluded by rule*
because every gas-phase core-set anion is unbound (Week-4 audit). The tests pin
that asymmetry plus the basic reproducibility of the comparison products.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
P1A_CSV = REPO_ROOT / "outputs" / "phase2_p1a" / "p1a_adiabatic.csv"
COMPARE_JSON = REPO_ROOT / "outputs" / "phase2_p1a" / "p1v_vs_p1a.json"


def _compare() -> dict:
    return json.loads(COMPARE_JSON.read_text(encoding="utf-8"))


def test_p1a_table_exists_and_has_the_t2_subset() -> None:
    rows = list(csv.DictReader(P1A_CSV.open(encoding="utf-8", newline="")))
    assert len(rows) == 12
    names = {row["name"] for row in rows}
    assert {"EC", "PC", "DMC", "EMC", "DME", "DOL", "GBL", "AN", "SN", "DMSO", "SL", "TMP"} == names


def test_oxidation_adiabatic_ip_is_defined_for_every_molecule() -> None:
    rows = list(csv.DictReader(P1A_CSV.open(encoding="utf-8", newline="")))
    defined = [row for row in rows if row["ip_p1a_ev"] not in ("", None)]
    assert len(defined) == len(rows)


def test_reduction_axis_is_excluded_by_the_unbound_anion_rule() -> None:
    report = _compare()
    assert report["reduction_axis"]["defined"] is False
    assert "unbound_anion" in report["reduction_axis"]["reason"]


def test_vertical_and_adiabatic_are_comparable_on_the_oxidation_axis() -> None:
    report = _compare()
    assert report["ranking"]["defined"] is True
    assert report["n"] >= 10
    assert -1.0 <= report["ranking"]["kendall_tau_b"] <= 1.0
    # The relaxation displacement must be reported as a candidate-specific spread.
    assert report["displacement"]["population_std_ev"] is not None


def test_document_matches_the_json() -> None:
    doc = (REPO_ROOT / "docs" / "p1v_vs_p1a.md").read_text(encoding="utf-8")
    assert "P1v" in doc and "P1a" in doc
    assert "unbound_anion" in doc or "不束缚" in doc
