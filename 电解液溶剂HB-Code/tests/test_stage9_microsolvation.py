"""Stage 9 / T10 tests: shell construction geometry, the redox arithmetic, and
the shell-size decision-stability layer.

The builder is pure geometry plus a written-down rule, so it is tested on
synthetic coordinates rather than on the shipped 18 MB of ORCA output; the
shipped artefacts are checked separately (and only when they exist) for the
things that would be silently wrong: stoichiometry, uniqueness, and the fact
that both shell columns share one C0 reference.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
for _directory in (REPO_ROOT / "src", REPO_ROOT / "scripts"):
    if str(_directory) not in sys.path:
        sys.path.insert(0, str(_directory))

import analyze_stage9_microsolvation as s9  # noqa: E402
import build_microsolvation_shells as shell  # noqa: E402

SHIFT_CSV = REPO_ROOT / "outputs" / "week8" / "stage9_shell_shifts.csv"
SHELL_DIR = REPO_ROOT / "structures" / "microsolvation"


def _water():
    symbols = ["O", "H", "H"]
    coords = np.array([[0.0, 0.0, 0.0], [0.96, 0.0, 0.0], [-0.24, 0.93, 0.0]])
    return symbols, coords


# --------------------------------------------------------------------------- #
# geometry primitives
# --------------------------------------------------------------------------- #

def test_fibonacci_directions_are_unit_and_distinct():
    directions = shell.fibonacci_directions(32)
    assert len(directions) == 32
    for direction in directions:
        assert abs(float(np.linalg.norm(direction)) - 1.0) < 1e-9
    stacked = np.array(directions)
    assert np.min(np.linalg.norm(stacked[:, None, :] - stacked[None, :, :], axis=2)
                  + np.eye(32)) > 0.01


def test_rotation_matrix_is_orthogonal_with_unit_determinant():
    rotation = shell.rotation_matrix([1.0, 2.0, -0.5], 0.7)
    assert np.allclose(rotation @ rotation.T, np.eye(3), atol=1e-12)
    assert abs(float(np.linalg.det(rotation)) - 1.0) < 1e-12


def test_align_rotation_maps_source_onto_target():
    source = np.array([0.3, -0.4, 0.5])
    target = np.array([-0.7, 0.1, 0.9])
    rotation = shell.align_rotation(source, target)
    mapped = rotation @ (source / np.linalg.norm(source))
    assert np.allclose(mapped, target / np.linalg.norm(target), atol=1e-12)


def test_align_rotation_handles_antiparallel_vectors():
    rotation = shell.align_rotation([1.0, 0.0, 0.0], [-1.0, 0.0, 0.0])
    assert np.allclose(rotation @ np.array([1.0, 0.0, 0.0]), [-1.0, 0.0, 0.0],
                       atol=1e-12)


def test_covalent_radii_falls_back_for_unknown_elements():
    radii = shell.covalent_radii(["O", "Xx"])
    assert radii[0] == pytest.approx(shell.COVALENT_RADIUS["O"])
    assert radii[1] == pytest.approx(0.8)


def test_minimal_clearance_is_smallest_cross_ratio():
    # Two unit-separated points with radii 1 each -> 1.0 / (1 + 1) = 0.5
    value = shell.minimal_clearance(
        np.array([[0.0, 0.0, 0.0]]), np.array([[1.0, 0.0, 0.0]]),
        np.array([1.0]), np.array([1.0]),
    )
    assert value == pytest.approx(0.5)


# --------------------------------------------------------------------------- #
# placement rule
# --------------------------------------------------------------------------- #

def test_place_second_ligand_puts_every_donor_at_the_frozen_distance():
    symbols, coords = _water()
    li = np.array([0.0, 0.0, 0.0])
    placements = shell.place_second_ligand(
        li, ["Li"], np.array([[0.0, 0.0, 0.0]]), symbols, coords, [0]
    )
    assert len(placements) == shell.N_DIRECTIONS * shell.N_ROLLS
    for item in placements:
        distance = float(np.linalg.norm(item["coords"][0] - li))
        assert distance == pytest.approx(shell.PLACEMENT_DISTANCE["O"], abs=1e-9)
        assert np.isfinite(item["min_clearance"])


def test_place_second_ligand_keeps_the_ligand_rigid():
    symbols, coords = _water()
    placements = shell.place_second_ligand(
        np.zeros(3), ["Li"], np.zeros((1, 3)), symbols, coords, [0]
    )
    reference = coords[1] - coords[0]
    for item in placements[:40]:
        moved = item["coords"][1] - item["coords"][0]
        assert np.linalg.norm(moved) == pytest.approx(np.linalg.norm(reference), abs=1e-9)


def test_place_second_ligand_covers_more_than_one_donor():
    symbols = ["O", "C", "O", "H"]
    coords = np.array([[0.0, 0.0, 0.0], [1.4, 0.0, 0.0], [2.6, 0.6, 0.0], [3.2, 1.2, 0.0]])
    placements = shell.place_second_ligand(
        np.zeros(3), ["Li"], np.zeros((1, 3)), symbols, coords, [0, 2]
    )
    assert {item["donor_index"] for item in placements} == {0, 2}
    assert {item["donor_symbol"] for item in placements} == {"O"}


def test_ligand_bonds_intact_detects_a_stretched_bond():
    from collections import defaultdict

    symbols = ["O", "H"]
    neighbours = defaultdict(list)
    neighbours[0].append((1, 1.0))
    neighbours[1].append((0, 1.0))
    close = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]])
    far = np.array([[0.0, 0.0, 0.0], [9.0, 0.0, 0.0]])
    # water's O-H covalent sum is small, so the bond limit is well below 9 A
    assert shell.ligand_bonds_intact(symbols, neighbours, close) is True
    assert shell.ligand_bonds_intact(symbols, neighbours, far) is False


# --------------------------------------------------------------------------- #
# redox arithmetic
# --------------------------------------------------------------------------- #

def test_vertical_ip_ea_use_the_cation_as_the_common_reference():
    ip, ea = s9.vertical_ip_ea(-10.0, -9.5, -10.4)
    assert ip == pytest.approx(0.5 * s9.HARTREE_TO_EV)
    assert ea == pytest.approx(0.4 * s9.HARTREE_TO_EV)
    assert s9.vertical_ip_ea(None, -9.5, -10.4) == (None, None)


def test_shell_energies_skips_rows_that_are_not_ok():
    jobs = [
        {"name": "M", "motif_id": "m1", "state": "cation", "job": "opt",
         "status": "ok", "final_energy_eh": "-1.0"},
        {"name": "M", "motif_id": "m1", "state": "dication", "job": "sp",
         "status": "execution_failed", "final_energy_eh": ""},
    ]
    table = s9.shell_energies(jobs)
    assert table[("M", "m1")]["cation"]["opt"] == pytest.approx(-1.0)
    assert "dication" not in table[("M", "m1")]


def _c1_row(name, motif, ip1, ea1, ip0=10.0, ea0=-2.0):
    return {
        "mol_id": "C0" + str(len(name)), "name": name, "family": "f",
        "motif_id": motif, "is_primary": "True",
        "ip_c0_g2_ev": str(ip0), "ea_c0_g2_ev": str(ea0),
        "ip_c1_ev": str(ip1), "ea_c1_ev": str(ea1), "qc_flags": "",
    }


def test_build_shift_rows_shares_one_c0_reference_between_the_two_shells():
    jobs = [{
        "name": "A", "motif_id": "m1", "state": "cation", "job": "opt",
        "status": "ok", "final_energy_eh": "-100.0",
    }, {
        "name": "A", "motif_id": "m1", "state": "dication", "job": "sp",
        "status": "ok", "final_energy_eh": "-99.5",
    }, {
        "name": "A", "motif_id": "m1", "state": "reduced", "job": "sp",
        "status": "ok", "final_energy_eh": "-100.4",
    }]
    rows = s9.build_shift_rows(jobs, [_c1_row("A", "m1", ip1=15.0, ea1=4.0)])
    row = rows[0]
    assert row["d_ip_shell1_ev"] == pytest.approx(5.0)
    assert row["d_ip_shell2_ev"] == pytest.approx(0.5 * s9.HARTREE_TO_EV - 10.0)
    assert row["d_ea_shell1_ev"] == pytest.approx(6.0)
    assert row["d_ea_shell2_ev"] == pytest.approx(0.4 * s9.HARTREE_TO_EV + 2.0)
    assert row["d_d_ip_ev"] == pytest.approx(
        row["d_ip_shell2_ev"] - row["d_ip_shell1_ev"]
    )


def test_build_shift_rows_reports_missing_shell2_as_none():
    rows = s9.build_shift_rows([], [_c1_row("A", "m1", ip1=15.0, ea1=4.0)])
    assert rows[0]["ip_shell2_ev"] is None
    assert rows[0]["d_ip_shell2_ev"] is None
    assert rows[0]["d_d_ip_ev"] is None


# --------------------------------------------------------------------------- #
# decision stability
# --------------------------------------------------------------------------- #

def test_stability_row_is_identity_when_the_two_shells_agree():
    values = [1.0, 2.0, 3.0, 4.0, 5.0]
    labels = ["a", "b", "c", "d", "e"]
    row = s9.stability_row("oxidation", "all", values, values, labels, True)
    assert row["kendall_tau_b"] == pytest.approx(1.0)
    assert row["overlap_10"] == pytest.approx(1.0)
    assert row["f_unresolved_shell1"] == pytest.approx(0.0)
    assert row["f_robust_inv"] == pytest.approx(0.0)
    # identical realisations give a zero method spread; the summary statistic
    # drops zero off-diagonal entries, so it is None rather than 0.0
    assert row["sigma_median_ev"] in (None, 0.0)


def test_stability_row_marks_a_fully_reversed_ordering_unresolved():
    """The two-realisation sigma is deliberately conservative.

    A complete reversal makes the method spread as large as the separation
    itself, so no pair stays resolved and the inversion is *not* counted as a
    robust inversion (v2 section 9.2).  Asserting this pins the convention.
    """

    labels = ["a", "b", "c", "d", "e"]
    row = s9.stability_row("oxidation", "all", [1, 2, 3, 4, 5],
                           [5, 4, 3, 2, 1], labels, True)
    assert row["kendall_tau_b"] == pytest.approx(-1.0)
    assert row["f_unresolved_shell2"] == pytest.approx(1.0)
    assert row["f_robust_inv"] == pytest.approx(0.0)
    assert row["overlap_10"] == pytest.approx(0.0)


def test_stability_row_keeps_a_small_change_resolved():
    labels = ["a", "b", "c", "d", "e"]
    row = s9.stability_row("oxidation", "all", [1.0, 2.0, 3.0, 4.0, 5.0],
                           [1.0, 2.0, 3.0, 4.5, 5.0], labels, True)
    assert row["kendall_tau_b"] == pytest.approx(1.0)
    assert row["f_unresolved_shell2"] < 0.5


def test_stability_row_returns_short_record_below_two_points():
    row = s9.stability_row("oxidation", "all", [1.0], [2.0], ["a"], True)
    assert row["n"] == 1
    assert "kendall_tau_b" not in row


# --------------------------------------------------------------------------- #
# shipped artefacts (skipped before the stage has produced them)
# --------------------------------------------------------------------------- #

@pytest.mark.skipif(not SHELL_DIR.is_dir(), reason="Stage 9 shells not built yet")
def test_shipped_shells_have_the_frozen_stoichiometry():
    files = sorted(SHELL_DIR.glob("*_shell2.xyz"))
    assert files, "no shell structures found"
    for path in files:
        lines = path.read_text(encoding="utf-8").splitlines()
        count = int(lines[0].split()[0])
        atoms = [line.split()[0] for line in lines[2:2 + count]]
        assert atoms.count("Li") == 1, path.name
        assert (len(atoms) - 1) % 2 == 0, path.name
        assert atoms[len(atoms) // 2] == "Li", path.name


@pytest.mark.skipif(not SHIFT_CSV.exists(), reason="Stage 9 analysis not run yet")
def test_shipped_shift_table_has_unique_motifs_and_sane_shifts():
    import csv
    import io

    with io.open(SHIFT_CSV, encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows
    keys = [(row["name"], row["motif_id"]) for row in rows]
    assert len(set(keys)) == len(keys)
    for row in rows:
        if row["d_ip_shell1_ev"] and row["d_ip_shell2_ev"]:
            # the 1:1 coordination shift is large and positive on both axes
            assert float(row["d_ip_shell1_ev"]) > 0
            assert float(row["d_ip_shell2_ev"]) > 0