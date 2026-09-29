"""T6 (conformer-ensemble spread) pure-function tests.

No xTB and no ORCA run here: the quantile helper, the P0/P1 value builders, the
per-molecule aggregation and the aggregate estimator definitions are exercised
on hand-written numbers, so the suite stays green on a machine with no engine.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
for _directory in (REPO_ROOT / "src", REPO_ROOT / "scripts"):
    if str(_directory) not in sys.path:
        sys.path.insert(0, str(_directory))

from run_t6_conformer_spread import (  # noqa: E402
    CSV_COLUMNS,
    HARTREE_TO_EV,
    PSTDEV,
    STATES,
    conformers_of,
    p0_values,
    p1_values,
    quantile,
    summarise_layer,
)


def _entry(name="EC", mol_id="C04", n_confs=3, family="cyclic_carbonate"):
    return {
        "name": name,
        "mol_id": mol_id,
        "family": family,
        "conformers": [
            {"conf_id": "conf_%d" % index, "path": "structures/conformers/%s/conf_%d.xyz" % (name, index),
             "is_g1_reference": index == 0, "rel_kj": float(index)}
            for index in range(n_confs)
        ],
    }


def test_quantile_matches_linear_interpolation():
    data = [0.0, 1.0, 2.0, 3.0, 4.0]
    assert quantile(data, 0.0) == 0.0
    assert quantile(data, 1.0) == 4.0
    assert quantile(data, 0.5) == 2.0
    assert quantile(data, 0.25) == pytest.approx(1.0)
    assert quantile([7.0], 0.9) == 7.0


def test_quantile_rejects_empty():
    with pytest.raises(ValueError):
        quantile([], 0.5)


def test_states_are_the_t1_triple():
    assert STATES == (("neutral", 0, 1), ("cation", 1, 2), ("anion", -1, 2))


def test_p0_values_sign_convention():
    rows = [
        {"name": "EC", "conf_id": "conf_0", "status": "ok", "p0_ox_ev": 12.4, "p0_red_ev": -5.8},
        {"name": "EC", "conf_id": "conf_1", "status": "failed", "p0_ox_ev": None, "p0_red_ev": None},
    ]
    values = p0_values(rows)
    assert values[("EC", "conf_0")] == {"ip": 12.4, "ea": -5.8}
    assert values[("EC", "conf_1")] is None


def test_p1_values_are_vertical_differences():
    def row(state, energy, status="ok"):
        return {"name": "EC", "conf_id": "conf_0", "state": state, "status": status,
                "final_energy_eh": energy}

    rows = [
        row("neutral", -100.0),
        row("cation", -99.5),
        row("anion", -100.2),
    ]
    values = p1_values(rows)
    assert values[("EC", "conf_0")]["ip"] == pytest.approx(0.5 * HARTREE_TO_EV)
    assert values[("EC", "conf_0")]["ea"] == pytest.approx(0.2 * HARTREE_TO_EV)


def test_p1_values_none_when_one_state_failed():
    rows = [
        {"name": "EC", "conf_id": "conf_0", "state": "neutral", "status": "ok", "final_energy_eh": -100.0},
        {"name": "EC", "conf_id": "conf_0", "state": "cation", "status": "failed", "final_energy_eh": None},
        {"name": "EC", "conf_id": "conf_0", "state": "anion", "status": "ok", "final_energy_eh": -100.2},
    ]
    assert p1_values(rows)[("EC", "conf_0")] is None


def test_summarise_layer_estimators():
    entry = _entry(n_confs=3)
    values = {
        ("EC", "conf_0"): {"ip": 10.0, "ea": 2.0},
        ("EC", "conf_1"): {"ip": 11.0, "ea": 2.5},
        ("EC", "conf_2"): {"ip": 12.0, "ea": 3.0},
    }
    payload = summarise_layer([entry], values, "p0", [])
    molecule = payload["molecules"][0]
    assert molecule["n_scored"] == 3
    assert molecule["complete"] is True
    assert molecule["sigma_ip_ev"] == pytest.approx(PSTDEV([10.0, 11.0, 12.0]))
    assert molecule["range_ip_ev"] == pytest.approx(2.0)
    assert molecule["sigma_ea_ev"] == pytest.approx(PSTDEV([2.0, 2.5, 3.0]))
    assert molecule["range_ea_ev"] == pytest.approx(1.0)

    aggregate = payload["aggregate"]["oxidation"]
    assert aggregate["sigma_conf_ev"] == 0.0            # one molecule -> pstdev of one value
    assert aggregate["n_molecules"] == 1
    assert aggregate["p90_spread_ev"] == pytest.approx(2.0)
    assert aggregate["median_spread_ev"] == pytest.approx(2.0)
    assert aggregate["max_spread_ev"] == pytest.approx(2.0)


def test_summarise_layer_flags_incomplete_and_failures():
    entry = _entry(n_confs=2)
    values = {("EC", "conf_0"): {"ip": 10.0, "ea": 2.0}, ("EC", "conf_1"): None}
    rows = [{"name": "EC", "conf_id": "conf_1", "layer": "p0", "status": "execution_failed", "error": "boom"}]
    payload = summarise_layer([entry], values, "p0", rows)
    assert payload["molecules"][0]["complete"] is False
    assert payload["molecules"][0]["n_scored"] == 1
    assert payload["failures"][0]["conf_id"] == "conf_1"


def test_conformers_of_is_defensive():
    assert conformers_of({}) == []
    assert len(conformers_of(_entry())) == 3


def test_csv_columns_are_stable():
    assert CSV_COLUMNS[:5] == ["name", "mol_id", "family", "conf_id", "layer"]
    assert CSV_COLUMNS[-1] == "status"