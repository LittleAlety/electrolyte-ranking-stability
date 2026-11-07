"""Stage 19 tests.

Two things are pinned here, both on synthetic ORCA fragments -- no real ``.out``
file, no corpus, no network:

* the **last-block** parsers.  An ``Opt`` output prints the starting geometry and
  an initial population analysis before the first cycle, so a first-block parser
  would silently describe the wrong end of the optimisation.  The tests assert
  both halves of that statement: the last-block parser returns the final values,
  and the Stage-17 first-block parser returns the starting ones.
* the per-cell outcome table (``distinct_lower`` / ``distinct_higher`` /
  ``same_lower`` / ``same_higher`` / ``incomplete``), exercised by monkeypatching
  the job paths at synthetic files.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import analyze_stage17_solution_identity as s17  # noqa: E402
import analyze_stage19_relax as m  # noqa: E402


# ---------------------------------------------------------------------------
# synthetic ORCA output: two Opt cycles, different geometry and density
# ---------------------------------------------------------------------------

START_COORDS = ("  C   0.000000   0.000000   0.000000",
                "  O   1.200000   0.000000   0.000000")
FINAL_COORDS = ("  C   0.010000   0.010000   0.000000",
                "  O   1.250000   0.000000   0.020000")

START_CHARGES = ("   0 C :   -0.100000    0.500000",
                 "   1 O :    0.100000    0.700000")
FINAL_CHARGES = ("   0 C :   -0.300000    0.600000",
                 "   1 O :    0.300000    0.800000")

#: The first number on a SPIN row is the spin, not the charge (verified against a
#: real Stage-19 output); the trailing "s :" / "p :" column is the orbital subtotal.
SPIN_START = ("  0 C s       :    -0.003466  s :    -0.003466",
              "      pz      :     0.072941  p :     0.057641",
              "  1 O s       :     0.010000  s :     0.010000",
              "      pz      :     0.300000  p :     0.300000")
SPIN_FINAL = ("  0 C s       :    -0.021215  s :    -0.021215",
              "      pz      :     0.067706  p :     0.067706",
              "  1 O s       :     0.010486  s :     0.010486",
              "      pz      :     0.290315  p :     0.290315")


def cycle(header_energy, coords, charges, spin_rows):
    lines = ["GEOMETRY OPTIMIZATION CYCLE   1",
             "FINAL SINGLE POINT ENERGY      %.12f" % header_energy,
             s17.CARTESIAN_HEADER,
             "--------------------------------"]
    lines += list(coords)
    lines += ["", s17.MULLIKEN_ATOMIC_HEADER, "-------"]
    lines += list(charges)
    lines += ["", s17.MULLIKEN_REDUCED_HEADER, "-------", "CHARGE"]
    lines += ["  0 C s       :     3.000000", "  1 O s       :     3.800000", "SPIN"]
    lines += list(spin_rows)
    lines += ["", ""]
    return lines


OPT_TEXT = "\n".join(
    cycle(-100.000000000000, START_COORDS, START_CHARGES, SPIN_START)
    + cycle(-100.500000000000, FINAL_COORDS, FINAL_CHARGES, SPIN_FINAL)
    + ["THE OPTIMIZATION HAS CONVERGED", "ORCA TERMINATED NORMALLY"]
) + "\n"


# ---------------------------------------------------------------------------
# last-block parsers
# ---------------------------------------------------------------------------


def test_last_geometry_parser_returns_the_relaxed_geometry():
    assert m.parse_last_geometry(OPT_TEXT) == [row.strip() for row in FINAL_COORDS]


def test_first_block_parser_would_have_returned_the_starting_geometry():
    """The bug this stage had to avoid: s17's parser stops at block one."""

    assert s17.parse_geometry(OPT_TEXT) == [row.strip() for row in START_COORDS]
    assert s17.parse_geometry(OPT_TEXT) != m.parse_last_geometry(OPT_TEXT)


def test_last_population_parser_returns_the_final_charges():
    rows = m.parse_last_atomic_populations(OPT_TEXT, s17.MULLIKEN_ATOMIC_HEADER)
    assert [row[2] for row in rows] == [-0.3, 0.3]
    first = s17.parse_atomic_populations(OPT_TEXT, s17.MULLIKEN_ATOMIC_HEADER)
    assert [row[2] for row in first] == [-0.1, 0.1]


def test_last_reduced_spin_takes_the_second_spin_sub_block():
    spin = m.parse_last_reduced_spin(OPT_TEXT)
    assert spin[(1, "O", "s")] == pytest.approx(0.010486)
    assert spin[(1, "O", "pz")] == pytest.approx(0.290315)
    first = s17.parse_reduced_orbital_spin(OPT_TEXT)
    assert first[(1, "O", "pz")] == pytest.approx(0.300000)
    assert set(spin) == set(first)


def test_analyze_relaxed_outfile_keeps_the_final_energy_and_density():
    parsed = m.analyze_relaxed_outfile(OPT_TEXT)
    assert parsed["e_eh"] == pytest.approx(-100.5)
    assert [row[2] for row in parsed["mulliken"]] == [-0.3, 0.3]
    assert parsed["geometry"] == [row.strip() for row in FINAL_COORDS]


def test_analyze_relaxed_outfile_survives_an_empty_document():
    parsed = m.analyze_relaxed_outfile("")
    assert parsed["e_eh"] is None
    assert parsed["mulliken"] == []
    assert parsed["reduced_spin"] == {}
    assert parsed["geometry"] is None

# ---------------------------------------------------------------------------
# geometry
# ---------------------------------------------------------------------------


def test_kabsch_rmsd_is_zero_for_identical_sets():
    coords = np.asarray([[0.0, 0.0, 0.0], [1.2, 0.0, 0.0], [0.0, 1.0, 0.5]])
    assert m.kabsch_rmsd(coords, coords) == pytest.approx(0.0, abs=1e-12)


def test_kabsch_rmsd_is_invariant_under_rotation_and_translation():
    rng = np.random.default_rng(20261001)
    coords = rng.normal(size=(7, 3))
    axis = rng.normal(size=3)
    axis /= np.linalg.norm(axis)
    angle = 0.7
    cross = np.asarray([[0.0, -axis[2], axis[1]],
                        [axis[2], 0.0, -axis[0]],
                        [-axis[1], axis[0], 0.0]])
    rotation = (np.eye(3) + np.sin(angle) * cross
                + (1.0 - np.cos(angle)) * (cross @ cross))
    moved = coords @ rotation + np.asarray([3.0, -2.0, 0.5])
    assert m.kabsch_rmsd(coords, moved) == pytest.approx(0.0, abs=1e-10)


def test_kabsch_rmsd_reports_the_expected_magnitude_and_guards_bad_shapes():
    left = np.asarray([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]])
    right = np.asarray([[0.0, 0.0, 0.0], [1.1, 0.0, 0.0]])
    assert m.kabsch_rmsd(left, right) == pytest.approx(0.05, abs=1e-12)
    assert m.kabsch_rmsd(left, right[:1]) is None
    assert m.kabsch_rmsd(np.zeros((0, 3)), np.zeros((0, 3))) is None


# ---------------------------------------------------------------------------
# per-cell outcome table
# ---------------------------------------------------------------------------

IDENTICAL_CHARGES = START_CHARGES
DISTINCT_CHARGES = ("   0 C :   -2.000000    0.400000",
                    "   1 O :    2.000000    0.900000")


def make_text(energy, charges, coords=FINAL_COORDS):
    return "\n".join(
        cycle(-100.0, START_COORDS, START_CHARGES, SPIN_START)
        + cycle(energy, coords, charges, SPIN_FINAL)
        + ["THE OPTIMIZATION HAS CONVERGED", "ORCA TERMINATED NORMALLY"]
    ) + "\n"


SINGLE = {
    "name": "EC", "state": "cation", "epsilon": 5.0, "arm_set": "discovery",
    "delta_ev": -0.5, "charge_l1": "0.15",
    "e_default_eh": "-100.0", "e_moread_eh": "-100.5",
}
START = np.asarray([[0.0, 0.0, 0.0], [1.2, 0.0, 0.0]])


def build(tmp_path, monkeypatch, default_text, moread_text=None):
    paths = {"default": tmp_path / "d.out", "moread": tmp_path / "m.out"}
    paths["default"].write_text(default_text, encoding="utf-8", newline="\n")
    if moread_text is not None:
        paths["moread"].write_text(moread_text, encoding="utf-8", newline="\n")
    monkeypatch.setattr(m, "outfile_path",
                        lambda name, state, eps, arm, week18=None: paths[arm])
    cell = {"name": "EC", "state": "cation", "epsilon": 5.0, "arm_set": "discovery"}
    return m.build_cell(cell, SINGLE, {}, START, 0.039)


@pytest.mark.parametrize("moread_energy,moread_charges,expected", [
    (-100.1, DISTINCT_CHARGES, "distinct_lower"),
    (-99.9, DISTINCT_CHARGES, "distinct_higher"),
    (-100.1, IDENTICAL_CHARGES, "same_lower"),
    (-99.9, IDENTICAL_CHARGES, "same_higher"),
])
def test_outcome_table(tmp_path, monkeypatch, moread_energy, moread_charges, expected):
    record = build(tmp_path, monkeypatch,
                   make_text(-100.0, IDENTICAL_CHARGES),
                   make_text(moread_energy, moread_charges))
    assert record["both_arms_ok"] is True
    assert record["outcome"] == expected
    assert record["still_distinct"] is (expected.startswith("distinct"))
    assert record["still_lower"] is expected.endswith("lower")


def test_preference_flip_is_flagged_when_relaxation_reverses_the_order(tmp_path, monkeypatch):
    record = build(tmp_path, monkeypatch,
                   make_text(-100.0, IDENTICAL_CHARGES),
                   make_text(-99.9, DISTINCT_CHARGES))
    assert record["single_point_still_lower"] is True
    assert record["still_lower"] is False
    assert record["preference_flipped"] is True
    assert record["delta_shift_ev"] > 0.0


def test_missing_arm_is_incomplete_not_a_crash(tmp_path, monkeypatch):
    record = build(tmp_path, monkeypatch, make_text(-100.0, IDENTICAL_CHARGES))
    assert record["both_arms_ok"] is False
    assert record["outcome"] == "incomplete"
    assert "relax_delta_ev" not in record


def test_frozen_threshold_comes_from_the_stage18_census():
    if not m.CENSUS_JSON.exists():
        pytest.skip("the stage-18 census is not in this checkout")
    assert m.frozen_threshold() == pytest.approx(0.039)