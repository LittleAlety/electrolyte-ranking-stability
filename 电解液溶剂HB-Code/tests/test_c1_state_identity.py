"""Stage 5 / T4 (C1): unit tests for ``scripts/analyze_c1_state_identity.py``.

Nothing here runs ORCA.  The script only re-reads Mulliken blocks that the C1
jobs already wrote, so the parts worth pinning are:

* ``last_mulliken`` must pick the *final* block of an ORCA optimisation (the
  first one is the input guess) and must tolerate both the ``C :`` and ``Li:``
  column widths ORCA emits, closed shell and open shell alike;
* ``electron_label`` must apply the frozen thresholds inclusively and by
  absolute value;
* ``geometry_label`` must fire before the electronic rule;
* ``reaction_path_verified`` must never be produced, because the frozen rule
  only allows it with reaction-path / TS / dynamics evidence this project does
  not have;
* ``write_table`` must go through ``csv`` so a field such as ``O5:+0.283``
  cannot shift a row;
* the delivered table must still carry the counts the report quotes.
"""

from __future__ import annotations

import csv
import sys
from collections import Counter
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))
sys.path.insert(0, str(REPO_ROOT / "src"))

import analyze_c1_state_identity as identity  # noqa: E402


# ---------------------------------------------------------------------------
# synthetic ORCA helpers
# ---------------------------------------------------------------------------
def _orca_row(index, element, charge, spin=None):
    """One Mulliken table row in the exact column layout ORCA prints."""

    if spin is None:
        return "%4d %-2s: %12.6f" % (index, element, charge)
    return "%4d %-2s: %12.6f %12.6f" % (index, element, charge, spin)


def _orca_block(header, atoms, total_charge, total_spin=None):
    """A whole ``MULLIKEN ATOMIC CHARGES [...]`` block as a list of lines."""

    lines = [header, "-" * 44]
    for index, element, charge, spin in atoms:
        lines.append(_orca_row(index, element, charge, spin))
    lines.append("Sum of atomic charges         : %14.7f" % total_charge)
    if total_spin is not None:
        lines.append("Sum of atomic spin populations: %14.7f" % total_spin)
    lines.append("")
    return lines


def _li_atoms(q_li, spin_li):
    """Three atoms whose last entry is the Li the classifier keys on."""

    return [
        (0, "C", -0.067403, 0.041538),
        (1, "O", -0.019482, 0.282303),
        (2, "Li", q_li, spin_li),
    ]


# ---------------------------------------------------------------------------
# last_mulliken
# ---------------------------------------------------------------------------
def test_last_mulliken_returns_none_without_a_block():
    assert identity.last_mulliken("SCF done\nno charges here\n") is None


def test_last_mulliken_keeps_only_the_last_block_of_two():
    """An ORCA optimisation prints two blocks; the last one is the answer."""

    first = _orca_block(
        "MULLIKEN ATOMIC CHARGES AND SPIN POPULATIONS",
        _li_atoms(0.111111, 0.222222), 2.0, 1.0,
    )
    last = _orca_block(
        "MULLIKEN ATOMIC CHARGES AND SPIN POPULATIONS",
        _li_atoms(0.981256, -0.000148), 2.0, 1.0,
    )
    text = "\n".join(first + ["TOTAL RUN TIME: 1.0 sec"] + last)
    rows = identity.last_mulliken(text)
    assert rows == [
        (0, "C", -0.067403, 0.041538),
        (1, "O", -0.019482, 0.282303),
        (2, "Li", 0.981256, -0.000148),
    ]


def test_mulliken_row_layout_has_spaced_c_and_unspaced_li():
    """The fixture itself must reproduce ``C :`` and ``Li:`` before it is trusted."""

    assert _orca_row(0, "C", 0.0).startswith("   0 C :")
    assert _orca_row(10, "Li", 0.0).startswith("  10 Li:")


def test_last_mulliken_reads_spaced_and_unspaced_element_fields():
    atoms = [(0, "C", -0.049140, 0.036716), (10, "Li", 0.966530, -0.000256)]
    text = "\n".join(
        _orca_block("MULLIKEN ATOMIC CHARGES AND SPIN POPULATIONS", atoms, 2.0, 1.0)
    )
    rows = identity.last_mulliken(text)
    assert [row[0] for row in rows] == [0, 10]
    assert [row[1] for row in rows] == ["C", "Li"]
    assert rows[0][2] == -0.049140
    assert rows[1][3] == -0.000256


def test_last_mulliken_reads_a_closed_shell_block():
    atoms = [(0, "C", -0.049140, None), (1, "O", -0.382140, None)]
    text = "\n".join(_orca_block("MULLIKEN ATOMIC CHARGES", atoms, -1.0))
    rows = identity.last_mulliken(text)
    assert rows == [(0, "C", -0.049140, None), (1, "O", -0.382140, None)]


# ---------------------------------------------------------------------------
# electron_label (frozen thresholds)
# ---------------------------------------------------------------------------
def test_electron_label_has_three_branches():
    assert identity.electron_label(0.02, -0.10) == "molecule_centered_redox"
    assert identity.electron_label(1.01, -0.99) == "Li_centered_or_mixed_redox"
    assert identity.electron_label(0.30, 0.30) == "state_identity_ambiguous"


def test_electron_label_threshold_edges_are_inclusive():
    """Both cutoffs are inclusive, checked with the two indicators in step.

    A cutoff is only meaningful when the second indicator does not contradict
    it: ``electron_label(0.5, 0.0)`` mixes a Li-scale reading with a
    molecule-scale one, which is a disagreement rather than a boundary case
    (see ``test_electron_label_disagreeing_indicators_are_ambiguous``).
    """

    # |spin| <= 0.15 and |dq| <= 0.25 -> molecule centred, both at the edge
    assert identity.electron_label(0.15, 0.25) == "molecule_centered_redox"
    # one indicator inside the molecule band, the other just below Li
    assert identity.electron_label(0.15, 0.20) == "molecule_centered_redox"
    assert identity.electron_label(0.10, 0.25) == "molecule_centered_redox"
    # |spin| >= 0.5 or |dq| >= 0.5 -> Li centred, both at the edge
    assert identity.electron_label(0.5, 0.5) == "Li_centered_or_mixed_redox"
    assert identity.electron_label(0.7, 0.5) == "Li_centered_or_mixed_redox"


def test_electron_label_uses_absolute_values():
    assert identity.electron_label(-1.01, -0.99) == "Li_centered_or_mixed_redox"
    assert identity.electron_label(-0.02, -0.10) == "molecule_centered_redox"
    assert identity.electron_label(1.01, 0.99) == "Li_centered_or_mixed_redox"


def test_electron_label_disagreeing_indicators_are_ambiguous():
    """A clean indicator must not be overruled by an opposing clean one.

    Regression: the published branch ``li_side and molecule_side`` was
    unreachable, so ``electron_label(0.8, 0.0)`` -- spin says Li, charge says
    the molecule never changed -- used to come back as
    ``Li_centered_or_mixed_redox``.  On the 24 frozen rows the two indicators
    agree everywhere, so this correction changes no label; it only makes the
    frozen sentence about a disagreement reachable.
    """

    assert identity.electron_label(0.8, 0.0) == "state_identity_ambiguous"
    assert identity.electron_label(0.0, 0.8) == "state_identity_ambiguous"
    assert identity.electron_label(0.5, 0.0) == "state_identity_ambiguous"
    # both grey: neither rule resolves it either
    assert identity.electron_label(0.3, 0.3) == "state_identity_ambiguous"


CONVERGENCE_CASES = (
    "                         ****ORCA TERMINATED NORMALLY****\n"
    "THE OPTIMIZATION HAS CONVERGED AFTER 12 CYCLES\n",
    "The optimization did not converge but reached the maximum number of\n"
    "optimization cycles\n",
    "TOTAL SCF ENERGY\n  -271.6 Eh\n",
)


def test_opt_convergence_reads_the_output_instead_of_the_exit_status():
    """True / False / None come from the text, never from ``status``.

    Audit finding: four dication re-optimisations and one cation reference
    stopped at ORCA's optimisation-cycle cap yet were recorded ``status=ok``,
    so convergence has to be proved by the file itself.
    """

    assert identity.opt_convergence(CONVERGENCE_CASES[0]) is True
    assert identity.opt_convergence(CONVERGENCE_CASES[1]) is False
    assert identity.opt_convergence(CONVERGENCE_CASES[2]) is None


def test_job_evidence_carries_the_convergence_flag(tmp_path):
    outdir = tmp_path
    jobdir = outdir / "c1" / "EC"
    jobdir.mkdir(parents=True)
    (jobdir / "EC_m1_dication_opt.out").write_text(
        CONVERGENCE_CASES[1]
        + "\nMULLIKEN ATOMIC CHARGES AND SPIN POPULATIONS\n"
        + "   0 C :   -0.123456    0.000000\n"
        + "   1 Li:    0.900000    1.000000\n"
        + "\nSum of atomic charges =   0.776544\n",
        encoding="utf-8",
    )

    evidence = identity.job_evidence(outdir, "EC", "EC_m1_dication_opt")
    assert evidence["converged"] is False
    assert evidence["q_li"] == 0.9


def test_electron_label_conflicting_indicators_are_ambiguous():
    """One indicator is clearly molecular while the other sits in the gap.

    The frozen rule needs ``|spin| <= 0.15`` *and* ``|dq| <= 0.25`` before it
    will call a state molecule centred, so a single clean indicator next to a
    grey one is a disagreement and must not be forced into a category.
    """

    assert identity.electron_label(0.05, 0.30) == "state_identity_ambiguous"
    assert identity.electron_label(0.30, 0.05) == "state_identity_ambiguous"
    assert identity.electron_label(0.30, 0.30) == "state_identity_ambiguous"


# ---------------------------------------------------------------------------
# geometry_label (geometry outranks the electrons)
# ---------------------------------------------------------------------------
def test_geometry_label_missing_minimum_is_no_intact_minimum_found():
    record = {"parent_bonds_intact": True, "li_contacts": "", "li_min_distance_a": 7.9}
    assert identity.geometry_label(record, {1, 4}) == "no_intact_minimum_found"


def test_geometry_label_broken_parent_is_dissociated_product():
    record = {"parent_bonds_intact": False, "li_contacts": "4:O:2.03"}
    assert identity.geometry_label(record, {1}) == "dissociated_optimized_product"


def test_geometry_label_disjoint_donors_is_motif_switch():
    record = {"parent_bonds_intact": True, "li_contacts": "2:O:2.10"}
    assert identity.geometry_label(record, {1, 4}) == "motif_switch"


def test_geometry_label_intact_minimum_is_none():
    record = {"parent_bonds_intact": True, "li_contacts": "1:O:2.02;4:O:2.05"}
    assert identity.geometry_label(record, {1, 4}) is None
    assert identity.geometry_label(None, {1, 4}) is None


def test_geometry_outranks_the_electronic_label_end_to_end(tmp_path: Path):
    """``build_rows`` must take the geometric label even when the density on
    the relaxed state looks molecule centred, and must never claim a path."""

    out = tmp_path / "out"
    name, motif_id = "MOL1", "m1"
    c1 = out / "c1" / name
    c1.mkdir(parents=True)

    (out / "li_motif_generation.csv").write_text(
        "mol_id,name,family,motif_id,contact_donor_indices,kept\n"
        "X01,MOL1,cyclic_carbonate,m1,1;4,True\n",
        encoding="utf-8", newline="",
    )

    # reference [Li M]+: q_Li = 0.940242
    (c1 / ("%s_%s_cation_opt.out" % (name, motif_id))).write_text(
        "\n".join(_orca_block(
            "MULLIKEN ATOMIC CHARGES AND SPIN POPULATIONS",
            _li_atoms(0.940242, 0.05), 1.0, 1.0,
        )),
        encoding="utf-8", newline="",
    )

    # dication: relaxed geometry threw Li+ off (no contacts) ...
    (c1 / ("%s_%s_dication_opt_c1_record.json" % (name, motif_id))).write_text(
        '{"status": "ok", "li_contacts": "", "li_min_distance_a": 7.9, '
        '"parent_bonds_intact": true}',
        encoding="utf-8",
    )
    # ... yet its relaxed density looks molecule centred (spin 0.0, dq 0.0)
    (c1 / ("%s_%s_dication_opt.out" % (name, motif_id))).write_text(
        "\n".join(_orca_block(
            "MULLIKEN ATOMIC CHARGES AND SPIN POPULATIONS",
            _li_atoms(0.940242, 0.0), 2.0, 1.0,
        )),
        encoding="utf-8", newline="",
    )

    # reduced: minimum intact and the electron sits on Li
    (c1 / ("%s_%s_reduced_opt_c1_record.json" % (name, motif_id))).write_text(
        '{"status": "ok", "li_contacts": "1:O:2.00;4:O:2.05", '
        '"li_min_distance_a": 2.0, "parent_bonds_intact": true}',
        encoding="utf-8",
    )
    (c1 / ("%s_%s_reduced_opt.out" % (name, motif_id))).write_text(
        "\n".join(_orca_block(
            "MULLIKEN ATOMIC CHARGES AND SPIN POPULATIONS",
            _li_atoms(-0.054203, 1.012085), 0.0, 1.0,
        )),
        encoding="utf-8", newline="",
    )

    rows = identity.build_rows(out, out / "li_motif_generation.csv")
    assert len(rows) == 2
    by_state = {row["redox_state"]: row for row in rows}

    dication = by_state["dication"]
    assert dication["state_identity_label"] == "no_intact_minimum_found"
    assert dication["label_source"] == "geometry"
    # the electronic rule alone would have said molecule centred
    assert dication["relaxed_label"] == "molecule_centered_redox"

    reduced = by_state["reduced"]
    assert reduced["state_identity_label"] == "Li_centered_or_mixed_redox"
    assert reduced["label_source"] == "electron"
    assert reduced["dq_li"] == -0.994445
    assert reduced["spin_li_state"] == 1.012085

    for row in rows:
        assert row["state_identity_label"] in identity.VOCABULARY
        assert row["state_identity_label"] != "reaction_path_verified"


# ---------------------------------------------------------------------------
# reaction_path_verified is never assigned
# ---------------------------------------------------------------------------
def test_reaction_path_verified_is_never_assigned():
    assert "reaction_path_verified" in identity.VOCABULARY
    extremes = [
        (0.0, 0.0),
        (0.15, 0.25),
        (0.5, 0.5),
        (10.0, -10.0),
        (float("inf"), 0.0),
        (-1e9, 1e9),
        (0.3, 0.3),
    ]
    for spin, dq in extremes:
        assert identity.electron_label(spin, dq) != "reaction_path_verified"

    records = [
        None,
        {},
        {"parent_bonds_intact": False},
        {"parent_bonds_intact": True, "li_contacts": ""},
        {"parent_bonds_intact": True, "li_contacts": None},
        {"parent_bonds_intact": True, "li_contacts": "7:O:1.4"},
    ]
    for record in records:
        assert identity.geometry_label(record, set()) != "reaction_path_verified"
        assert identity.geometry_label(record, {1, 4}) != "reaction_path_verified"


# ---------------------------------------------------------------------------
# write_table (CSV self-consistency)
# ---------------------------------------------------------------------------
def test_write_table_round_trips_without_shifting_a_row(tmp_path: Path):
    columns = ["name", "state_identity_label", "dq_li", "spin_li_state",
               "top_spin_carriers"]
    rows = [
        {
            "name": "EC",
            "state_identity_label": "molecule_centered_redox",
            "dq_li": 0.041014,
            "spin_li_state": -0.000148,
            "top_spin_carriers": "O5:+0.283;O2:+0.282;H9:+0.110",
        },
        {
            "name": "DME",
            "state_identity_label": "Li_centered_or_mixed_redox",
            "dq_li": -0.994445,
            "spin_li_state": 1.012085,
            "top_spin_carriers": "Li10:+1.012;C3:-0.030;C0:+0.012",
        },
    ]
    path = identity.write_table(tmp_path / "state_identity.csv", columns, rows)
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        read = list(reader)

    assert reader.fieldnames == columns
    assert len(read) == 2
    for row in read:
        assert None not in row
        assert len(row) == len(columns)
    assert read[0]["top_spin_carriers"] == "O5:+0.283;O2:+0.282;H9:+0.110"
    assert read[1]["top_spin_carriers"] == "Li10:+1.012;C3:-0.030;C0:+0.012"
    assert read[0]["dq_li"] == "0.041014"
    assert read[1]["spin_li_state"] == "1.012085"
    assert read[1]["name"] == "DME"
    assert read[1]["state_identity_label"] == "Li_centered_or_mixed_redox"


# ---------------------------------------------------------------------------
# delivered table
# ---------------------------------------------------------------------------
def test_delivered_state_identity_table_matches_the_frozen_counts():
    path = REPO_ROOT / "outputs" / "week5" / "c1_state_identity.csv"
    if not path.exists():
        pytest.skip("no week-5 state-identity table in this checkout")

    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)

    assert reader.fieldnames == identity.COLUMNS
    assert len(rows) == 24
    for row in rows:
        assert None not in row, ("ragged row", row.get("name"))
        assert row["state_identity_label"] in identity.VOCABULARY

    dication = Counter(
        row["state_identity_label"]
        for row in rows if row["redox_state"] == "dication"
    )
    reduced = Counter(
        row["state_identity_label"]
        for row in rows if row["redox_state"] == "reduced"
    )

    assert dication["molecule_centered_redox"] == 8
    assert dication["no_intact_minimum_found"] == 4
    assert sum(dication.values()) == 12

    assert reduced["Li_centered_or_mixed_redox"] == 11
    assert reduced["molecule_centered_redox"] == 1
    assert sum(reduced.values()) == 12

    assert "reaction_path_verified" not in set(dication) | set(reduced)