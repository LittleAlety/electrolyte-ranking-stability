"""Stage 17 / week 16 tests: the solution-identity parsers.

The 32 real ORCA files this analysis runs on are not in a bare checkout, so
every test here builds a small but structurally faithful ``.out`` fragment in
``tmp_path`` and drives the parser functions directly.  What is being protected:

* the sections are located by keyword rather than by line number, and the
  ``(idx, element, charge, spin)`` rows survive both the header underline and
  the "Sum of atomic charges" line that closes the table;
* the reduced-orbital reader must return the SPIN sub-block and not the CHARGE
  sub-block printed above it.  Swapping them would silently relabel the unpaired
  electron from a spin channel to a charge channel, and the two prints disagree:
  the fixture makes the CHARGE value distinct so the test can tell them apart;
* PR and n90 are pinned at their analytic edge (all weight on one atom gives
  PR = 1 and n90 = 1), because that limit is what the "which solution is more
  localised" reading leans on;
* the filename parser carries the whole census: the ``moread`` arm, the state
  token and a float epsilon all have to come back, and a non-C-PCM file (smd,
  holdout, smoke) must return ``None`` rather than a guess.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "scripts"))

import analyze_stage17_solution_identity as mod


# ---------------------------------------------------------------------------
# fixture builders -- synthetic but section-faithful ORCA fragments
# ---------------------------------------------------------------------------


def _mulliken(rows, header):
    lines = [header, "-" * len(header)]
    for idx, element, charge, spin in rows:
        lines.append(f"  {idx} {element} :   {charge:.6f}   {spin:.6f}")
    lines.append("Sum of atomic charges         :   -1.0000000")
    lines.append("Sum of atomic spin populations:    1.0000000")
    return lines


def _reduced(spin_spec, charge_value=9.999999):
    """CHARGE then SPIN sub-blocks.  The CHARGE value is deliberately distinct
    from every SPIN value so a reader that grabs the wrong block is caught."""
    lines = [mod.MULLIKEN_REDUCED_HEADER, "-" * len(mod.MULLIKEN_REDUCED_HEADER)]
    for label, constant in (("CHARGE", charge_value), ("SPIN", None)):
        lines.append(label)
        for idx in sorted(spin_spec):
            element, orbitals = spin_spec[idx]
            shown = constant if constant is not None else orbitals["s"]
            lines.append(
                f"  {idx} {element} s       :     {shown:.6f}  s :     {shown:.6f}"
            )
            for orbital in ("pz", "px", "py"):
                if orbital in orbitals:
                    shown = constant if constant is not None else orbitals[orbital]
                    lines.append(
                        f"      {orbital}      :     {shown:.6f}  p :     {shown:.6f}"
                    )
        lines.append("")
    return lines


def _geometry(rows):
    lines = [mod.CARTESIAN_HEADER, "-" * len(mod.CARTESIAN_HEADER)]
    for element, x, y, z in rows:
        lines.append(f"  {element}   {x:.6f}   {y:.6f}   {z:.6f}")
    return lines


DEFAULT_MULLIKEN = [
    (0, "C", -0.630632, 1.0),
    (1, "O", 0.208438, 0.0),
    (2, "H", 0.159466, 0.0),
]
DEFAULT_SPIN = {
    0: ("C", {"s": 1.0, "pz": 0.10}),
    1: ("O", {"s": 0.0, "pz": 0.0}),
    2: ("H", {"s": 0.0}),
}
DEFAULT_GEOMETRY = [
    ("C", 0.0, 0.0, 0.0),
    ("O", 1.2, 0.0, 0.0),
    ("H", 0.0, 1.0, 0.0),
]


def build_out(
    energy=-381.648935874298,
    s2=0.751419,
    multiplicity=2,
    charge=-1,
    mulliken=None,
    spin_spec=None,
    geometry=None,
):
    mulliken = DEFAULT_MULLIKEN if mulliken is None else mulliken
    spin_spec = DEFAULT_SPIN if spin_spec is None else spin_spec
    geometry = DEFAULT_GEOMETRY if geometry is None else geometry
    lines = [
        f" Total Charge           Charge          ....   {charge}",
        f" Multiplicity           Mult            ....    {multiplicity}",
        "",
        f"Expectation value of <S**2>     :     {s2:.6f}",
        "",
        "MULLIKEN POPULATION ANALYSIS",
        "",
    ]
    lines += _mulliken(mulliken, mod.MULLIKEN_ATOMIC_HEADER)
    lines.append("")
    lines += _reduced(spin_spec)
    lines += _mulliken(
        [(idx, el, q + 0.1, s * 0.5) for idx, el, q, s in mulliken],
        mod.LOEWDIN_ATOMIC_HEADER,
    )
    lines.append("")
    lines += _geometry(geometry)
    lines.append("")
    lines.append(f"FINAL SINGLE POINT ENERGY      {energy:.12f}")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# 1. scalar sections
# ---------------------------------------------------------------------------


def test_scalar_sections_are_found_by_keyword():
    text = build_out(energy=-381.648935874298, s2=0.751419, multiplicity=2, charge=-1)
    assert mod.parse_final_energy(text) == pytest.approx(-381.648935874298)
    assert mod.parse_s2(text) == pytest.approx(0.751419)
    assert mod.parse_multiplicity(text) == 2
    assert mod.parse_total_charge(text) == -1


def test_scalar_sections_use_the_last_occurrence():
    text = build_out() + build_out(energy=-1.5, s2=0.8, multiplicity=4, charge=1)
    assert mod.parse_final_energy(text) == pytest.approx(-1.5)
    assert mod.parse_s2(text) == pytest.approx(0.8)
    assert mod.parse_multiplicity(text) == 4
    assert mod.parse_total_charge(text) == 1


def test_missing_sections_return_none_or_empty():
    assert mod.parse_final_energy("no energy here") is None
    assert mod.parse_s2("no s2 here") is None
    assert mod.parse_multiplicity("nothing") is None
    assert mod.parse_total_charge("nothing") is None
    assert mod.parse_atomic_populations("nothing", mod.MULLIKEN_ATOMIC_HEADER) == []
    assert mod.parse_reduced_orbital_spin("nothing") == {}
    assert mod.parse_geometry("nothing") is None


# ---------------------------------------------------------------------------
# 2. Mulliken and Loewdin atomic population tables
# ---------------------------------------------------------------------------


def test_mulliken_atomic_populations_round_trip():
    text = build_out()
    rows = mod.parse_atomic_populations(text, mod.MULLIKEN_ATOMIC_HEADER)
    assert [(r[0], r[1]) for r in rows] == [(0, "C"), (1, "O"), (2, "H")]
    assert rows[0][2] == pytest.approx(-0.630632)
    assert rows[0][3] == pytest.approx(1.0)
    assert rows[1][2] == pytest.approx(0.208438)
    assert rows[1][3] == pytest.approx(0.0)
    assert rows[2][3] == pytest.approx(0.0)


def test_loewdin_atomic_populations_are_a_separate_table():
    text = build_out()
    rows = mod.parse_atomic_populations(text, mod.LOEWDIN_ATOMIC_HEADER)
    assert [r[0] for r in rows] == [0, 1, 2]
    # the fixture prints Loewdin as charge + 0.1 and spin * 0.5
    assert rows[0][2] == pytest.approx(DEFAULT_MULLIKEN[0][2] + 0.1)
    assert rows[0][3] == pytest.approx(DEFAULT_MULLIKEN[0][3] * 0.5)
    assert rows[1][2] == pytest.approx(DEFAULT_MULLIKEN[1][2] + 0.1)


# ---------------------------------------------------------------------------
# 3. reduced-orbital SPIN sub-block
# ---------------------------------------------------------------------------


def test_reduced_orbital_reader_returns_the_spin_sub_block():
    spin_spec = {
        0: ("C", {"s": 0.10, "pz": 0.10}),
        1: ("O", {"s": 0.20, "pz": -1.200000}),
        2: ("H", {"s": 0.002}),
    }
    text = build_out(spin_spec=spin_spec)
    reduced = mod.parse_reduced_orbital_spin(text)
    assert reduced[(0, "C", "s")] == pytest.approx(0.10)
    assert reduced[(0, "C", "pz")] == pytest.approx(0.10)
    assert reduced[(1, "O", "s")] == pytest.approx(0.20)
    assert reduced[(1, "O", "pz")] == pytest.approx(-1.200000)
    assert reduced[(2, "H", "s")] == pytest.approx(0.002)
    # the CHARGE block printed above SPIN uses 9.999999 everywhere; if the reader
    # had consumed it instead, none of the values above would match.


def test_top_atom_orbital_picks_the_largest_absolute_contribution():
    spin_spec = {
        0: ("C", {"s": 0.10, "pz": 0.10}),
        1: ("O", {"s": 0.20, "pz": -1.200000}),
        2: ("H", {"s": 0.002}),
    }
    reduced = mod.parse_reduced_orbital_spin(build_out(spin_spec=spin_spec))
    label, value = mod.top_atom_orbital(reduced)
    assert label == "O1 pz"
    assert value == pytest.approx(1.200000)


def test_top_atom_orbital_is_none_for_empty_input():
    assert mod.top_atom_orbital({}) == (None, 0.0)


# ---------------------------------------------------------------------------
# 4. participation ratio and n90 edge cases
# ---------------------------------------------------------------------------


def test_all_spin_on_one_atom_gives_pr_one_and_n90_one():
    concentrated = [0.0, 1.0, 0.0]
    assert mod.participation_ratio(concentrated) == pytest.approx(1.0)
    assert mod.atoms_to_fraction(concentrated) == 1


def test_flat_spin_distribution_gives_pr_equal_to_atom_count():
    even = [0.25, 0.25, 0.25, 0.25]
    assert mod.participation_ratio(even) == pytest.approx(4.0)
    assert mod.atoms_to_fraction(even) == 4


def test_ninety_percent_boundary_and_empty_input():
    assert mod.atoms_to_fraction([0.5, 0.4, 0.1]) == 2
    assert mod.participation_ratio([0.0, 0.0, 0.0]) == 0.0
    assert mod.atoms_to_fraction([0.0, 0.0, 0.0]) == 0


def test_larger_pr_means_more_delocalised():
    localised = [0.9, 0.05, 0.05]
    delocalised = [0.4, 0.3, 0.3]
    assert mod.participation_ratio(delocalised) > mod.participation_ratio(localised)


# ---------------------------------------------------------------------------
# 5. filename parsing
# ---------------------------------------------------------------------------


def test_parse_outfile_name_arm_state_and_epsilon():
    assert mod.parse_outfile_name("PC_anion_cpcm_10.out") == (
        "default",
        "PC",
        "anion",
        10.0,
    )
    assert mod.parse_outfile_name("PC_anion_moread_cpcm_10.out") == (
        "moread",
        "PC",
        "anion",
        10.0,
    )
    assert mod.parse_outfile_name("TMP_cation_moread_cpcm_1000.out") == (
        "moread",
        "TMP",
        "cation",
        1000.0,
    )
    assert mod.parse_outfile_name("EC_neutral_cpcm_5.out") == (
        "default",
        "EC",
        "neutral",
        5.0,
    )


def test_parse_outfile_name_rejects_non_cpcm_files():
    for name in (
        "AN_anion_smd_water.out",
        "DEC_cation_holdout_cpcm_20.out",
        "EC_gas.out",
        "EC_smd.out",
        "notes.txt",
    ):
        assert mod.parse_outfile_name(name) is None


# ---------------------------------------------------------------------------
# 6. two arms: same vs different spin centre and orbital label
# ---------------------------------------------------------------------------


def test_compare_arms_flags_same_spin_center_and_orbital():
    default = mod.analyze_outfile(build_out(s2=0.751419))
    moread = mod.analyze_outfile(
        build_out(
            energy=-381.649000000000,
            s2=0.751179,
            mulliken=[
                (0, "C", -0.610000, 0.98),
                (1, "O", 0.190000, 0.01),
                (2, "H", 0.150000, 0.00),
            ],
            spin_spec={
                0: ("C", {"s": 0.98, "pz": 0.12}),
                1: ("O", {"s": 0.01}),
                2: ("H", {"s": 0.00}),
            },
        )
    )
    result = mod.compare_arms(default, moread)
    assert result["spin_atom_default"] == "C0"
    assert result["spin_atom_moread"] == "C0"
    assert result["same_spin_center"] is True
    assert result["orbital_default"] == "C0 s"
    assert result["orbital_moread"] == "C0 s"
    assert result["same_orbital_label"] is True
    assert result["geometry_identical"] is True
    assert result["spin_n90_default"] == 1
    assert result["spin_n90_moread"] == 1
    assert result["spin_pr_default"] == pytest.approx(1.0)
    assert result["spin_max_default"] == pytest.approx(1.0)
    assert result["spin_max_moread"] == pytest.approx(0.98)
    assert result["delta_s2"] == pytest.approx(0.751179 - 0.751419)
    assert result["charge_l1"] > 0.0
    assert result["loss_in_pr"] > 0.0


def test_compare_arms_flags_different_spin_center_and_orbital():
    default = mod.analyze_outfile(build_out())
    moread = mod.analyze_outfile(
        build_out(
            mulliken=[
                (0, "C", -0.600000, 0.10),
                (1, "O", 0.500000, 0.90),
                (2, "H", 0.150000, 0.00),
            ],
            spin_spec={
                0: ("C", {"s": 0.10}),
                1: ("O", {"s": 0.90, "px": 0.05}),
                2: ("H", {"s": 0.00}),
            },
        )
    )
    result = mod.compare_arms(default, moread)
    assert result["spin_atom_default"] == "C0"
    assert result["spin_atom_moread"] == "O1"
    assert result["same_spin_center"] is False
    assert result["orbital_default"] == "C0 s"
    assert result["orbital_moread"] == "O1 s"
    assert result["same_orbital_label"] is False


def test_compare_arms_detects_different_geometry():
    default = mod.analyze_outfile(build_out())
    shifted = [
        ("C", 0.0, 0.0, 0.0),
        ("O", 1.250000, 0.0, 0.0),
        ("H", 0.0, 1.0, 0.0),
    ]
    moread = mod.analyze_outfile(build_out(geometry=shifted))
    assert mod.compare_arms(default, moread)["geometry_identical"] is False


# ---------------------------------------------------------------------------
# file-driven smoke test and the real anchor regression
# ---------------------------------------------------------------------------


def test_analyze_outfile_reads_a_file_from_disk(tmp_path):
    path = tmp_path / "PC_anion_moread_cpcm_10.out"
    path.write_text(
        build_out(energy=-381.648935874298, s2=0.751179), encoding="utf-8"
    )
    record = mod.analyze_outfile(mod.read_text(path))
    assert record["e_eh"] == pytest.approx(-381.648935874298)
    assert record["s2"] == pytest.approx(0.751179)
    assert record["mult"] == 2
    assert record["charge"] == -1
    assert len(record["mulliken"]) == 3
    assert len(record["loewdin"]) == 3
    assert record["reduced_spin"]
    assert record["geometry"]


ANCHOR_DEFAULT = Path("outputs/week4/orca_cpcm_10/PC/PC_anion_cpcm_10.out")
ANCHOR_MOREAD = Path(
    "outputs/week15/orca_moread_cpcm_10/PC/PC_anion_moread_cpcm_10.out"
)


@pytest.mark.skipif(
    not (REPO_ROOT / ANCHOR_DEFAULT).exists()
    or not (REPO_ROOT / ANCHOR_MOREAD).exists(),
    reason="real ORCA anchor outputs are absent from this checkout",
)
def test_real_anchor_pair_regression():
    default = mod.analyze_outfile(mod.read_text(REPO_ROOT / ANCHOR_DEFAULT))
    moread = mod.analyze_outfile(mod.read_text(REPO_ROOT / ANCHOR_MOREAD))
    assert default["e_eh"] == pytest.approx(-381.645612097205)
    assert moread["e_eh"] == pytest.approx(-381.648935874298)
    assert default["s2"] == pytest.approx(0.751419)
    assert moread["s2"] == pytest.approx(0.751179)
    result = mod.compare_arms(default, moread)
    assert result["spin_atom_default"] == "C4"
    assert result["spin_atom_moread"] == "C4"
    assert result["spin_max_default"] == pytest.approx(1.48, abs=0.02)
    assert result["spin_max_moread"] == pytest.approx(1.47, abs=0.02)
    assert result["geometry_identical"] is True
