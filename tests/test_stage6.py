"""Stage 6 / T9 (uncertainty-aware ranking) pure-function tests.

The point of these tests is the plumbing the prereg depends on: that the fixed
tolerance really reaches ``ranking.resolved_mask``, that the scenario lookup maps
layer/objective names correctly, and that the family split and the probabilistic
ordering behave as declared.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
for _directory in (REPO_ROOT / "src", REPO_ROOT / "scripts"):
    if str(_directory) not in sys.path:
        sys.path.insert(0, str(_directory))

from analyze_stage6 import (  # noqa: E402
    CSV_COLUMNS,
    PAIRS,
    SCENARIOS,
    Z_PRIMARY,
    compare,
    delta_m_for,
    family_split,
    gather,
    load_c1,
    load_p2,
    mask_fraction,
    normal_cdf,
    probabilistic_ordering,
)


def _candidates():
    return {
        "p0": {
            "oxidation": {"delta_m_ev": 0.7},
            "reduction": {"delta_m_ev": 2.07},
        },
        "p1": {
            "oxidation": {"delta_m_ev": 0.7},
            "reduction": {"delta_m_ev": 2.07},
        },
    }


def test_scenarios_and_pairs_are_the_frozen_set():
    assert SCENARIOS == ("z_only", "floor_only", "docx_max")
    assert Z_PRIMARY == 1.0
    assert [pair[0] for pair in PAIRS] == ["P0_to_P1", "P1_to_P2", "C0_to_C1"]


def test_delta_m_for_each_scenario():
    candidates = _candidates()
    assert delta_m_for("p0", "oxidation", "z_only", candidates)[0] == 0.0
    assert delta_m_for("p0", "oxidation", "floor_only", candidates)[0] == pytest.approx(0.05)
    value, note = delta_m_for("p0", "oxidation", "docx_max", candidates)
    assert value == pytest.approx(0.7)
    assert "P0" in note
    value, note = delta_m_for("p1", "reduction", "docx_max", candidates)
    assert value == pytest.approx(2.07)


def test_delta_m_for_unknown_layer_falls_back_to_the_p0_proxy():
    value, note = delta_m_for("c1", "oxidation", "docx_max", _candidates())
    assert value == pytest.approx(0.7)
    assert "C1" in note


def test_delta_m_for_missing_candidates_uses_the_floor():
    value, note = delta_m_for("p0", "oxidation", "docx_max", {})
    assert value == pytest.approx(0.05)
    assert "floor" in note


def test_tolerance_reaches_resolved_mask():
    """Identical realisations give sigma = 0, so only delta_m can decide."""

    labels = ["A", "B"]
    families = ["", ""]
    lower = [(0.0,), (0.05,)]
    upper = [(0.0,), (0.05,)]

    loose = compare("X", labels, families, lower, upper, 0.0)
    strict = compare("X", labels, families, lower, upper, 0.1)

    assert loose["n_pairs"] == 1
    assert loose["f_unresolved_lower"] == 0.0      # |0.05| >= 0 -> resolved
    assert strict["f_unresolved_lower"] == 1.0     # |0.05| <  0.1 -> unresolved
    assert strict["kendall_tau_b"] == loose["kendall_tau_b"]


def test_compare_reports_both_sides_and_the_ladders():
    labels = ["A", "B", "C", "D"]
    families = ["a", "a", "b", "b"]
    lower = [(0.0,), (0.1,), (5.0,), (5.2,)]
    upper = [(0.0,), (0.15,), (5.0,), (5.25,)]
    item = compare("X", labels, families, lower, upper, 0.0)
    assert item["n"] == 4
    assert item["n_pairs"] == 6
    assert item["n_pairs_within_family"] == 2
    assert item["n_pairs_cross_family"] == 4
    assert set(item["top_k"]) == {"k=0.10", "k=0.20", "k=0.30"}
    assert item["f_robust_inv"] == 0.0
    assert item["threshold_decision_error"] is None
    assert "not_applicable" in item["threshold_decision_error_note"]


def test_family_split_partitions_pairs():
    labels = ["A", "B", "C"]
    within, cross = family_split(labels, ["x", "x", "y"])
    assert within == [(0, 1)]
    assert sorted(cross) == [(0, 2), (1, 2)]


def test_family_split_treats_blank_family_as_cross():
    labels = ["A", "B"]
    within, cross = family_split(labels, ["", ""])
    assert within == []
    assert cross == [(0, 1)]


def test_mask_fraction_counts_unresolved():
    import numpy as np

    mask = np.array([[False, True], [True, False]])
    assert mask_fraction(~mask, [(0, 1)]) == 0.0
    assert mask_fraction(~mask, []) == 0.0


def test_normal_cdf_is_centred():
    assert normal_cdf(0.0) == pytest.approx(0.5)
    assert normal_cdf(10.0) > 0.99
    assert normal_cdf(-10.0) < 0.01


def test_probabilistic_ordering_shape_and_complementarity():
    a = [0.0, 5.0, 1.0]
    b = [0.1, 5.1, 0.9]
    p = probabilistic_ordering(a, b)
    assert p.shape == (3, 3)
    for index in range(3):
        assert p[index, index] == 0.0
    assert p[1, 0] > 0.9     # A=5.0 well above C=0.0
    assert p[2, 0] > 0.9     # A=1.0 well above C=0.0
    assert p[0, 2] < 0.1
    assert p[0, 1] < 0.5     # A=0.0 below B=5.0


def test_probabilistic_ordering_handles_zero_spread():
    p = probabilistic_ordering([1.0, 2.0], [1.0, 2.0])
    assert p[1, 0] == 1.0
    assert p[0, 1] == 0.0


def test_gather_requires_both_layers_and_all_objectives():
    tables = {
        "EC": {"family": "c", "P0": {"ox": 1.0, "red": -1.0}, "P1": {"ox": 2.0, "red": -2.0}},
        "PC": {"family": "c", "P0": {"ox": 1.0, "red": None}, "P1": {"ox": 2.0, "red": -2.0}},
        "DMC": {"family": "l", "P0": {"ox": 1.0, "red": -1.0}, "P1": {"ox": 2.0, "red": -2.0}},
    }
    labels, families, lower, upper = gather("P0_to_P1", "P0", "P1", tables, ["EC", "PC", "DMC", "ZZ"])
    assert labels == ["EC", "DMC"]
    assert families == ["c", "l"]
    assert lower[0] == {"ox": 1.0, "red": -1.0}


def test_load_p2_builds_ip_and_minus_ea(tmp_path):
    path = tmp_path / "p2.csv"
    path.write_text(
        "name,state,status,final_energy_eh\n"
        "EC,neutral,ok,-100.0\n"
        "EC,cation,ok,-99.5\n"
        "EC,anion,ok,-100.2\n"
        "PC,neutral,ok,-90.0\n"
        "PC,cation,ok,-89.0\n",
        encoding="utf-8",
        newline="",
    )
    table = load_p2(path)
    assert set(table) == {"EC"}
    assert table["EC"]["ox"] == pytest.approx(0.5 * 27.211386245988)
    assert table["EC"]["red"] == pytest.approx(-0.2 * 27.211386245988)


def test_load_c1_keeps_only_the_primary_motif(tmp_path):
    path = tmp_path / "c1.csv"
    path.write_text(
        "name,family,motif_id,is_primary,ip_c0_g2_ev,ip_c1_ev,ea_c0_g2_ev,ea_c1_ev\n"
        "EC,cyclic_carbonate,m1,True,10.0,15.0,-2.0,3.0\n"
        "DMC,linear_carbonate,m2,False,10.5,15.5,-3.0,4.0\n"
        "DMC,linear_carbonate,m1,True,10.5,14.9,-3.0,4.1\n",
        encoding="utf-8",
        newline="",
    )
    table = load_c1(path)
    assert set(table) == {"EC", "DMC"}
    assert table["EC"]["C1"]["ox"] == pytest.approx(15.0)
    assert table["EC"]["C1"]["red"] == pytest.approx(-3.0)
    assert table["DMC"]["C1"]["ox"] == pytest.approx(14.9)


def test_csv_columns_are_stable():
    assert CSV_COLUMNS[:4] == ["pair", "objective", "scenario", "delta_m_ev"]
    assert "regret_20" in CSV_COLUMNS