"""Stage 20 / Part 1 tests.

Everything here is either synthetic arithmetic or an assertion on frozen
artefacts that already exist in the repository -- no quantum chemistry is run.

Two things are pinned:

* the *definition* of the new rung.  A geometry relaxation lowers the charged
  state, so ``delta = -energy_drop`` on both axes, and both axes are "higher is
  better"; if the sign convention ever flips, the whole comparison against the
  five frozen rungs silently inverts.
* the *refusal*.  The catalogue gives the oxidation axis three molecules and
  the reduction axis four, so every row must carry
  ``rank_metrics = omitted: n_molecules=... < 5`` instead of a tau_b.
"""

from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import analyze_stage20_relax_rung as m  # noqa: E402


def make_cell(name, state, epsilon, drop, arm_set="discovery", outcome="distinct_higher"):
    """One synthetic cell record with the module's own sign convention."""

    return {
        "name": name,
        "state": state,
        "axis": m.AXIS_OF_STATE[state],
        "epsilon": float(epsilon),
        "arm_set": arm_set,
        "outcome": outcome,
        "energy_drop_default_ev": drop,
        "energy_drop_moread_ev": drop - 0.1,
        "delta_ev": -drop,
        "delta_moread_ev": -(drop - 0.1),
        "two_arm_delta_ev": 0.02,
        "rmsd_relaxed_arms": 0.3,
    }


# ---------------------------------------------------------------------------
# the rung definition
# ---------------------------------------------------------------------------

def test_relaxation_lowers_the_axis_so_delta_is_negative():
    cells = m.cell_records()
    assert cells, "Stage 19 cell analysis must be on disk"
    for cell in cells:
        assert cell["delta_ev"] == -cell["energy_drop_default_ev"]
        assert cell["delta_ev"] < 0
    assert {cell["state"] for cell in cells} == {"anion", "cation"}


def test_axis_of_state_mapping_is_the_frozen_one():
    assert m.AXIS_OF_STATE == {"cation": "oxidation", "anion": "reduction"}


# ---------------------------------------------------------------------------
# the scale block
# ---------------------------------------------------------------------------

def test_scale_of_reports_sample_and_population_std():
    block = m.scale_of([1.0, 2.0, 3.0])
    assert block["n"] == 3
    assert block["shift_mean_ev"] == 2.0
    assert block["shift_std_ev"] == 1.0
    assert block["shift_std_pop_ev"] == pytest.approx(statistics.pstdev([1.0, 2.0, 3.0]))
    assert block["shift_min_ev"] == 1.0 and block["shift_max_ev"] == 3.0
    assert block["relative_dispersion"] == 0.5


def test_scale_of_single_value_has_no_sample_std_but_no_crash():
    block = m.scale_of([-2.0])
    assert block["n"] == 1
    assert block["shift_std_ev"] is None
    assert block["shift_std_pop_ev"] == 0.0
    assert block["relative_dispersion"] is None


def test_scale_of_empty_is_all_none():
    block = m.scale_of([])
    assert block["n"] == 0
    assert block["shift_mean_ev"] is None and block["shift_std_ev"] is None


# ---------------------------------------------------------------------------
# population selection
# ---------------------------------------------------------------------------

def test_population_values_honours_the_epsilon_selector():
    cells = [
        make_cell("PC", "anion", 5, 1.90),
        make_cell("PC", "anion", 20, 2.10),
        make_cell("EMC", "anion", 5, 1.94),
        make_cell("EMC", "anion", 20, 1.96),
    ]
    values, labels = m.population_values(cells, "reduction", ("PC", "EMC"), 5.0)
    assert labels == ["PC", "EMC"]
    assert values == [-1.90, -1.94]


def test_population_values_averages_across_eps_when_selector_is_none():
    cells = [
        make_cell("PC", "anion", 5, 1.90),
        make_cell("PC", "anion", 20, 2.10),
    ]
    values, labels = m.population_values(cells, "reduction", ("PC",), None)
    assert labels == ["PC"]
    assert values == [-2.0]


def test_population_values_skips_molecules_without_that_epsilon():
    cells = [make_cell("DMC", "cation", 5, 0.335),
             make_cell("EC", "cation", 20, 0.19)]
    values, labels = m.population_values(cells, "oxidation", ("DMC", "EC"), 5.0)
    assert labels == ["DMC"]
    assert values == [-0.335]


# ---------------------------------------------------------------------------
# the refusal
# ---------------------------------------------------------------------------

def test_rung_row_marks_rank_metrics_as_omitted_below_five_molecules():
    cells = [make_cell("DMC", "cation", 5, 0.335),
             make_cell("EC", "cation", 5, 0.19),
             make_cell("TMP", "cation", 5, 0.845)]
    row = m.rung_row("synthetic", "oxidation", ("DMC", "EC", "TMP"), 5.0, cells)
    assert row["n_molecules"] == 3
    assert row["rank_metrics"].startswith("omitted: n_molecules=3")
    assert row["shift_mean_ev"] == pytest.approx(-(0.335 + 0.19 + 0.845) / 3)
    assert "kendall_tau_b" not in row


def test_min_n_for_rank_metrics_is_five():
    assert m.MIN_N_FOR_RANK_METRICS == 5


# ---------------------------------------------------------------------------
# eps sensitivity
# ---------------------------------------------------------------------------

def test_epsilon_rows_report_the_range_and_the_count():
    cells = [
        make_cell("EC", "cation", 5, 0.202),
        make_cell("EC", "cation", 20, 0.191),
        make_cell("TMP", "cation", 5, 0.850),
    ]
    rows = {row["name"]: row for row in m.epsilon_rows(cells)}
    assert rows["EC"]["n_eps"] == 2
    assert rows["EC"]["delta_range_ev"] == pytest.approx(0.011, abs=1e-9)
    assert rows["TMP"]["n_eps"] == 1
    assert rows["TMP"]["delta_std_across_eps_ev"] == 0.0


# ---------------------------------------------------------------------------
# the matched ruler
# ---------------------------------------------------------------------------

def test_matched_ladder_carries_the_five_frozen_rungs_and_the_new_one():
    records = m.cell_records()
    rows = m.matched_ladder_rows(records, m.load_ladder())
    populations = {row["population"] for row in rows}
    assert populations == {p[0] for p in m.POPULATIONS}
    for population in populations:
        rungs = {row["rung"] for row in rows if row["population"] == population}
        assert {"P0_to_P1", "P1_to_P2", "G1_to_G2"} <= rungs
        assert m.RUNG_KEY in rungs
    for row in rows:
        assert row["rank_metrics"].startswith("omitted:"), row


# ---------------------------------------------------------------------------
# the frozen artefacts
# ---------------------------------------------------------------------------

def test_real_artefacts_reproduce_the_headline_numbers():
    payload = m.build(m.DEFAULT_OUTDIR)
    by_state = payload["aggregates"]["by_state"]
    assert payload["n_cells"] == 37
    assert payload["n_eps_values"] == 10
    assert by_state["cation"]["n_cells"] == 16
    assert by_state["anion"]["n_cells"] == 21
    assert by_state["cation"]["shift_mean_ev"] == pytest.approx(-0.610, abs=0.01)
    assert by_state["cation"]["shift_std_ev"] == pytest.approx(0.315, abs=0.01)
    assert by_state["anion"]["shift_mean_ev"] == pytest.approx(-1.953, abs=0.01)
    assert by_state["anion"]["shift_std_ev"] == pytest.approx(0.160, abs=0.01)
    # the reduction axis is a near-rigid translation, the oxidation axis is not
    assert by_state["anion"]["relative_dispersion"] < 0.10
    assert by_state["cation"]["relative_dispersion"] > 0.45
    ranges = [row["delta_range_ev"] for row in payload["epsilon_rows"]]
    assert statistics.median(ranges) == pytest.approx(0.0263, abs=0.002)
    assert max(ranges) == pytest.approx(0.215, abs=0.005)


def test_every_molecule_carries_exactly_one_state():
    """The structural reason the rank statistics are refused."""

    payload = m.build(m.DEFAULT_OUTDIR)
    states = {}
    for cell in payload["cells"]:
        states.setdefault(cell["name"], set()).add(cell["state"])
    assert all(len(found) == 1 for found in states.values())
    assert payload["n_molecules_by_state"]["cation"] == 3
    assert payload["n_molecules_by_state"]["anion"] == 4


def test_check_mode_is_clean():
    assert m.main(["--check"]) == 0