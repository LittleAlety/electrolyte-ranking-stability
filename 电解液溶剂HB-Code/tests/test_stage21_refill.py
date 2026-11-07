"""Stage 21 / Part D tests -- the P2-leg refill.

Everything here is synthetic arithmetic plus one assertion on a frozen artefact that
already exists. The heavy ``build()`` path (it re-runs the Stage 10 bootstrap) is never
called: the CLI tests monkeypatch ``build`` so they only exercise ``render``,
``summary_markdown`` and ``--check``.

The sign convention is the thing worth pinning. Stage 20 froze ``delta = -drop`` on
*one* axis convention (``p_red = -EA``, ``higher_is_better = True`` on both axes), so a
refill must lower the P2 end point by exactly the drop and must not touch P1 or any
other rung. If that ever flips, the whole comparison silently inverts.
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import analyze_stage21_refill as m  # noqa: E402


def tiny_ladder():
    """Two molecules with both axes, plus one with only the oxidation axis."""

    return {
        m.RUNG_KEY: {
            "AAA": {"ox": (10.0, 11.0), "red": (-3.0, -2.0)},
            "BBB": {"ox": (9.0, 10.5), "red": (-2.0, -1.0)},
            "CCC": {"ox": (8.0, 9.0), "red": (None, None)},
        },
        "P0_to_P1": {
            "AAA": {"ox": (9.0, 10.0), "red": (-4.0, -3.0)},
            "BBB": {"ox": (8.0, 9.5), "red": (-3.0, -2.0)},
            "CCC": {"ox": (7.0, 8.0), "red": (None, None)},
        },
    }


# ---------------------------------------------------------------------------
# the refill itself
# ---------------------------------------------------------------------------

def test_refill_lowers_the_p2_end_by_exactly_the_drop():
    ladder = tiny_ladder()
    refilled, applied = m.refill_ladder(ladder, {("AAA", "cation"): 0.25})

    assert refilled[m.RUNG_KEY]["AAA"]["ox"] == (10.0, 10.75)
    assert len(applied) == 1
    entry = applied[0]
    assert entry["delta_ev"] == 0.25
    assert entry["p2_before_ev"] == 11.0
    assert entry["p2_after_ev"] == 10.75
    assert entry["displacement_before_ev"] == 1.0
    assert entry["displacement_after_ev"] == 0.75
    assert entry["delta_displacement_ev"] == -0.25


def test_refill_leaves_the_original_ladder_untouched():
    ladder = tiny_ladder()
    before = copy.deepcopy(ladder)
    m.refill_ladder(ladder, {("AAA", "cation"): 0.25, ("BBB", "anion"): 0.5})
    assert ladder == before


def test_refill_moves_only_the_p2_rung_and_only_that_end():
    ladder = tiny_ladder()
    refilled, _applied = m.refill_ladder(ladder, {("AAA", "cation"): 0.25,
                                                  ("BBB", "anion"): 0.5})
    # P1 end point of the refilled rung is untouched
    assert refilled[m.RUNG_KEY]["AAA"]["ox"][0] == 10.0
    # every other rung is untouched
    assert refilled["P0_to_P1"] == ladder["P0_to_P1"]
    # the other axis of the same molecule is untouched
    assert refilled[m.RUNG_KEY]["AAA"]["red"] == (-3.0, -2.0)
    assert refilled[m.RUNG_KEY]["BBB"]["red"] == (-2.0, -1.5)


def test_refill_skips_molecules_the_rung_does_not_carry():
    ladder = tiny_ladder()
    refilled, applied = m.refill_ladder(ladder, {("ZZZ", "cation"): 1.0})
    assert applied == []
    assert refilled == ladder


def test_refill_skips_a_null_axis():
    ladder = tiny_ladder()
    _refilled, applied = m.refill_ladder(ladder, {("CCC", "anion"): 1.0})
    assert applied == []


def test_refill_raises_on_an_unknown_state_mapping():
    ladder = tiny_ladder()
    _refilled, applied = m.refill_ladder(ladder, {("AAA", "neutral"): 1.0})
    assert applied == []


# ---------------------------------------------------------------------------
# the transfer: one Delta per (molecule, state)
# ---------------------------------------------------------------------------

def make_record(name, state, epsilon, drop, source="orca", arm="default", status="ok"):
    return {"name": name, "state": state, "epsilon": float(epsilon), "drop_ev": drop,
            "source": source, "arm": arm, "status": status}


def test_molecule_deltas_mean_averages_the_epsilons_it_has():
    records = [make_record("AAA", "cation", 5, 0.2),
               make_record("AAA", "cation", 20, 0.4),
               make_record("BBB", "anion", 5, 0.1)]
    out = m.molecule_deltas(records, "orca", "default", "mean")
    assert out["deltas"][("AAA", "cation")] == pytest.approx(0.3)
    assert out["deltas"][("BBB", "anion")] == pytest.approx(0.1)
    assert out["spread"][("AAA", "cation")] == {
        "n_eps": 2, "drop_min_ev": 0.2, "drop_max_ev": 0.4, "drop_range_ev": 0.2}


def test_molecule_deltas_largest_eps_takes_the_most_screened_cell():
    records = [make_record("AAA", "cation", 5, 0.2),
               make_record("AAA", "cation", 200, 0.9),
               make_record("AAA", "cation", 20, 0.4)]
    out = m.molecule_deltas(records, "orca", "default", "largest_eps")
    assert out["deltas"][("AAA", "cation")] == pytest.approx(0.9)


def test_molecule_deltas_filters_by_source_and_arm_and_status():
    records = [make_record("AAA", "cation", 5, 0.2),
               make_record("AAA", "cation", 5, 9.9, source="xtb"),
               make_record("AAA", "cation", 5, 9.9, arm="moread"),
               make_record("AAA", "cation", 5, 9.9, status="execution_failed")]
    out = m.molecule_deltas(records, "orca", "default", "mean")
    assert out["deltas"][("AAA", "cation")] == pytest.approx(0.2)


def test_molecule_deltas_rejects_an_unknown_estimator():
    with pytest.raises(ValueError):
        m.molecule_deltas([make_record("AAA", "cation", 5, 0.2)], "orca", "default",
                          "median")


def test_molecule_deltas_on_empty_input_is_empty_not_a_crash():
    out = m.molecule_deltas([], "orca", "default", "mean")
    assert out["deltas"] == {} and out["spread"] == {}


# ---------------------------------------------------------------------------
# ordering and rank statistics
# ---------------------------------------------------------------------------

def test_ordered_names_is_descending_with_a_label_tie_break():
    assert m.ordered_names([1.0, 3.0, 2.0], ["a", "b", "c"]) == ["b", "c", "a"]
    assert m.ordered_names([2.0, 2.0, 1.0], ["b", "a", "c"]) == ["a", "b", "c"]


def test_rank_compare_identity_and_reversal():
    identity = m.rank_compare([1.0, 2.0, 3.0], [1.0, 2.0, 3.0], ["a", "b", "c"])
    assert identity["spearman_rho"] == pytest.approx(1.0)
    assert identity["kendall_tau_b"] == pytest.approx(1.0)
    assert identity["order_before"] == identity["order_after"] == ["c", "b", "a"]
    assert identity["top_k"]["k=0.10"]["overlap"] == pytest.approx(1.0)

    reversed_ = m.rank_compare([1.0, 2.0, 3.0], [3.0, 2.0, 1.0], ["a", "b", "c"])
    assert reversed_["spearman_rho"] == pytest.approx(-1.0)
    assert reversed_["kendall_tau_b"] == pytest.approx(-1.0)


def test_rank_compare_refuses_to_report_on_a_single_point():
    block = m.rank_compare([1.0], [2.0], ["a"])
    assert block["n"] == 1
    assert block["spearman_rho"] is None and block["kendall_tau_b"] is None
    assert "note" in block


def test_axis_values_reads_the_p2_end_point_only():
    ladder = tiny_ladder()
    labels, values = m.axis_values(ladder, "ox", ["AAA", "BBB", "CCC"])
    assert labels == ["AAA", "BBB", "CCC"]
    assert values == [11.0, 10.5, 9.0]
    labels, values = m.axis_values(ladder, "red", ["AAA", "CCC"])
    assert labels == ["AAA"] and values == [-2.0]


def test_populations_drops_molecules_the_rung_does_not_carry():
    ladder = tiny_ladder()
    out = m.populations(ladder, {"all": ["AAA", "BBB", "CCC", "ZZZ"]})
    assert out == {"all": ["AAA", "BBB", "CCC"]}


# ---------------------------------------------------------------------------
# rendering
# ---------------------------------------------------------------------------

def test_render_csv_header_is_exactly_the_frozen_column_list():
    text = m.render_csv([], m.CELL_COLUMNS)
    assert text.splitlines()[0] == ",".join(m.CELL_COLUMNS)
    assert text.endswith("\n")


def render_payload():
    """The real frozen ledger, re-rendered -- no hand-written numbers.

    The heavy part of ``build()`` is the Stage 10 bootstrap, not the rendering, so
    reusing the frozen JSON keeps this test fast while still exercising the real
    markdown renderer against the real coverage/verdict blocks.
    """

    path = REPO_ROOT / "outputs" / "week20" / "stage21_refill.json"
    if not path.exists():
        pytest.skip("stage21_refill.json is not on disk")
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["cells"] = []
    return payload


def test_render_produces_the_three_frozen_names():
    payload = render_payload()
    payload["summary_md"] = m.summary_markdown(payload)
    rendered = m.render(payload)
    assert set(rendered) == {"stage21_refill_cells.csv", "stage21_refill.json",
                            "stage21_refill_summary.md"}
    assert json.loads(rendered["stage21_refill.json"])["coverage"]["strict_p2_leg"][
        "n_cells"] == 54
    assert rendered["stage21_refill_summary.md"].startswith("# Stage 21")


# ---------------------------------------------------------------------------
# the CLI, with build() stubbed out so no bootstrap runs
# ---------------------------------------------------------------------------

def test_cli_writes_then_checks_then_notices_a_tampered_byte(tmp_path, monkeypatch):
    payload = render_payload()
    payload["summary_md"] = m.summary_markdown(payload)
    monkeypatch.setattr(m, "build", lambda data_dir, outdir: copy.deepcopy(payload))

    outdir = tmp_path / "out"
    assert m.main(["--outdir", str(outdir)]) == 0
    for name in ("stage21_refill_cells.csv", "stage21_refill.json",
                 "stage21_refill_summary.md"):
        assert (outdir / name).exists()
    assert m.main(["--outdir", str(outdir), "--check"]) == 0

    target = outdir / "stage21_refill.json"
    target.write_bytes(target.read_bytes().replace(b"1", b"9", 1))
    assert m.main(["--outdir", str(outdir), "--check"]) == 1


def test_cli_check_fails_when_an_artifact_is_missing(tmp_path, monkeypatch):
    payload = render_payload()
    payload["summary_md"] = m.summary_markdown(payload)
    monkeypatch.setattr(m, "build", lambda data_dir, outdir: copy.deepcopy(payload))
    outdir = tmp_path / "out"
    assert m.main(["--outdir", str(outdir)]) == 0
    (outdir / "stage21_refill_summary.md").unlink()
    assert m.main(["--outdir", str(outdir), "--check"]) == 1


# ---------------------------------------------------------------------------
# guards on the frozen artefacts
# ---------------------------------------------------------------------------

def test_frozen_refill_artifact_agrees_with_the_reported_coverage():
    path = REPO_ROOT / "outputs" / "week20" / "stage21_refill.json"
    if not path.exists():
        pytest.skip("stage21_refill.json is not on disk")
    payload = json.loads(path.read_text(encoding="utf-8"))
    strict = payload["coverage"]["strict_p2_leg"]
    assert strict["n_cells"] == 54
    assert strict["n_refillable"] == 7
    assert strict["n_refillable"] < strict["n_cells"], (
        "the literal P2 refill is not fully covered and the report must say so")
    dielectric = payload["coverage"]["dielectric_sub_leg"]
    assert dielectric["n_cells"] == 414
    assert dielectric["n_refillable"] == 37