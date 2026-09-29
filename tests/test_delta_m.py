"""T8 (delta_m assembly) pure-function tests.

The tests pin the parts a silent change could break: the max rule, the two
contributions, the unit conversion, the source-rule availability check and the
scenario set the Stage 6 analysis consumes.
"""

from __future__ import annotations

import statistics
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
for _directory in (REPO_ROOT / "src", REPO_ROOT / "scripts"):
    if str(_directory) not in sys.path:
        sys.path.insert(0, str(_directory))

from analyze_delta_m import (  # noqa: E402
    AUDIT_SUBSET,
    EV_TO_KJ_PER_MOL,
    FLOOR_EV,
    PREREG_DEFAULT_KJ,
    anchor_evidence,
    assemble,
    conformer_term,
    load_derived,
    method_term,
    quantile,
)


def _derived():
    return {
        "EC": {"p0_ox_ev": 10.0, "p0_red_ev": -5.0, "p1_ox_ev": 9.0, "p1_red_ev": 3.0},
        "PC": {"p0_ox_ev": 11.0, "p0_red_ev": -6.0, "p1_ox_ev": 9.5, "p1_red_ev": 4.0},
        "DMC": {"p0_ox_ev": 12.0, "p0_red_ev": -7.0, "p1_ox_ev": 12.5, "p1_red_ev": 5.0},
    }


def test_subset_and_constants_are_frozen_values():
    assert len(AUDIT_SUBSET) == 12
    assert "SL" in AUDIT_SUBSET and "TMP" in AUDIT_SUBSET
    assert FLOOR_EV == 0.05
    assert PREREG_DEFAULT_KJ == 2.0
    assert FLOOR_EV * EV_TO_KJ_PER_MOL == pytest.approx(4.8242666, rel=1e-6)


def test_method_term_is_pstdev_of_the_shift():
    block = method_term(_derived(), ["EC", "PC", "DMC"])["oxidation"]
    shifts = [-1.0, -1.5, 0.5]
    assert block["n"] == 3
    assert block["sigma_method_ev"] == pytest.approx(statistics.pstdev(shifts))
    assert block["max_abs_shift_ev"] == pytest.approx(1.5)
    assert [row["name"] for row in block["per_molecule"]] == ["EC", "PC", "DMC"]


def test_method_term_skips_molecules_with_missing_values():
    derived = _derived()
    derived["PC"]["p1_red_ev"] = None
    block = method_term(derived, ["EC", "PC", "DMC"])["reduction"]
    assert block["n"] == 2
    assert [row["name"] for row in block["per_molecule"]] == ["EC", "DMC"]


def test_method_term_empty_subset():
    assert method_term(_derived(), ["ZZZ"])["oxidation"] == {"n": 0}


def _spread(p90_ox, p90_red):
    return {
        "layers": {
            "p0": {
                "aggregate": {
                    "oxidation": {"p90_spread_ev": p90_ox, "sigma_conf_ev": 0.01,
                                  "median_spread_ev": 0.0, "max_spread_ev": p90_ox, "n_molecules": 12},
                    "reduction": {"p90_spread_ev": p90_red, "sigma_conf_ev": 0.02,
                                  "median_spread_ev": 0.0, "max_spread_ev": p90_red, "n_molecules": 12},
                }
            }
        }
    }


def test_conformer_term_reads_the_aggregate():
    term = conformer_term(_spread(0.03, 0.22), "p0")
    assert term["available"] is True
    assert term["oxidation"]["p90_spread_ev"] == pytest.approx(0.03)
    assert term["reduction"]["p90_spread_ev"] == pytest.approx(0.22)
    assert conformer_term(_spread(0.03, 0.22), "p9")["available"] is False


def test_assemble_takes_the_max_and_reports_the_winner():
    conformer = {"p0": conformer_term(_spread(0.03, 0.22), "p0"),
                 "p1": {"available": False}}
    method = method_term(_derived(), ["EC", "PC", "DMC"])
    per_layer = assemble(method, conformer)

    ox = per_layer["p0"]["oxidation"]
    # method sigma is far above both the conformer term and the floor
    assert ox["dominant_term"] == "method"
    assert ox["delta_m_ev"] == pytest.approx(method["oxidation"]["sigma_method_ev"])
    assert ox["delta_m_kj"] == pytest.approx(ox["delta_m_ev"] * EV_TO_KJ_PER_MOL)

    red = per_layer["p0"]["reduction"]
    assert red["delta_m_ev"] == pytest.approx(method["reduction"]["sigma_method_ev"])

    p1 = per_layer["p1"]["oxidation"]
    assert "conformer_p90_ev" not in p1["terms"]
    assert p1["delta_m_ev"] == pytest.approx(method["oxidation"]["sigma_method_ev"])


def test_assemble_falls_back_to_the_floor_when_nothing_is_measurable():
    conformer = {"p0": {"available": False}, "p1": {"available": False}}
    per_layer = assemble({}, conformer)
    block = per_layer["p0"]["oxidation"]
    assert block["dominant_term"] == "floor"
    assert block["delta_m_ev"] == pytest.approx(FLOOR_EV)


def test_scenarios_are_present_and_ordered_correctly():
    conformer = {"p0": conformer_term(_spread(0.03, 0.22), "p0"), "p1": {"available": False}}
    per_layer = assemble(method_term(_derived(), ["EC", "PC", "DMC"]), conformer)
    scenarios = per_layer["p0"]["oxidation"]["scenarios_ev"]
    assert scenarios["z_only"] == 0.0
    assert scenarios["floor_only"] == pytest.approx(FLOOR_EV)
    assert scenarios["conformer_p90"] == pytest.approx(0.03)
    assert scenarios["docx_max"] == pytest.approx(per_layer["p0"]["oxidation"]["delta_m_ev"])
    assert scenarios["method_only"] == pytest.approx(per_layer["p0"]["oxidation"]["terms"]["method_sigma_ev"])


def test_anchor_evidence_reports_series_without_replicates(tmp_path):
    path = tmp_path / "anchors.csv"
    path.write_text(
        "species,property,value_V,method\n"
        "EC,oxidation_potential,6.0,est\n"
        "EC,reduction_potential,0.9,est\n"
        "DMC,oxidation_potential,6.1,est\n",
        encoding="utf-8",
        newline="",
    )
    block = anchor_evidence(path)
    assert block["available"] is False
    assert block["n_replicated_series"] == 0
    assert block["n_rows_with_non_estimate_method"] == 0


def test_anchor_evidence_detects_a_replicated_series(tmp_path):
    path = tmp_path / "anchors.csv"
    path.write_text(
        "species,property,value_V,method\n"
        "EC,oxidation_potential,6.0,exp\n"
        "EC,oxidation_potential,6.2,exp\n",
        encoding="utf-8",
        newline="",
    )
    block = anchor_evidence(path)
    assert block["available"] is True
    assert block["n_replicated_series"] == 1
    assert block["n_rows_with_non_estimate_method"] == 2


def test_anchor_evidence_missing_file(tmp_path):
    block = anchor_evidence(tmp_path / "nope.csv")
    assert block["available"] is False
    assert "missing" in block["reason"]


def test_load_derived_skips_non_ok_rows_and_reads_blanks_as_none(tmp_path):
    path = tmp_path / "derived.csv"
    path.write_text(
        "name,family,status,p0_ox_ev,p0_red_ev,p1_ox_ev,p1_red_ev\n"
        "EC,cyclic_carbonate,ok,10.0,-5.0,9.0,3.0\n"
        "PC,cyclic_carbonate,failed,11.0,-6.0,9.5,4.0\n"
        "DMC,linear_carbonate,ok,12.0,,-7.0,\n",
        encoding="utf-8",
        newline="",
    )
    table = load_derived(path)
    assert set(table) == {"EC", "DMC"}
    assert table["DMC"]["p1_ox_ev"] == pytest.approx(-7.0)
    assert table["DMC"]["p0_red_ev"] is None


def test_quantile_local_helper():
    assert quantile([1.0, 2.0, 3.0, 4.0], 0.9) == pytest.approx(3.7)