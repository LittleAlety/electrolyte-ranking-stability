"""Parser regression against a real xTB run (see tests/fixtures/README.md).

The first version of the parser was written against an imagined layout and
returned ``None`` for HOMO/LUMO on a genuine 6.7.1 output.  This module pins the
values from the checked-in fixture so that layout drift fails loudly.
"""

from __future__ import annotations

from pathlib import Path

from electrolyte_ranking import xtb

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "xtb_6.7.1_ec_opt.out"


def _parse():
    text = FIXTURE.read_text(encoding="utf-8")
    return xtb.parse_xtb_output(text, charge=0, job=xtb.JOB_OPTIMIZE, required=())


def test_fixture_exists() -> None:
    assert FIXTURE.exists(), "the real-output fixture is missing"


def test_orbital_energies_come_from_the_orbital_table() -> None:
    result = _parse()
    # Final (post-optimisation) orbital block of the checked-in run.
    assert result.homo_ev == -12.4023
    assert result.lumo_ev == -6.0834
    assert result.hl_gap_ev == 6.3189


def test_total_energy_is_the_final_optimised_value() -> None:
    result = _parse()
    assert result.total_energy_eh == -20.686419864444
    # The pre-optimisation SCF block must not win: it is less negative.
    assert result.total_energy_eh < -20.6798


def test_dipole_comes_from_the_dipole_block_not_the_quadrupole_block() -> None:
    result = _parse()
    assert result.dipole_debye == 5.786


def test_fermi_level_is_read_in_both_units() -> None:
    result = _parse()
    assert result.fermi_level_eh == -0.3396669
    assert result.fermi_level_ev == -9.2428


def test_fixture_terminates_normally_and_is_not_an_unbound_anion() -> None:
    result = _parse()
    assert result.normal_termination
    assert result.qc_flags == ()


def test_required_fields_raise_when_absent() -> None:
    try:
        xtb.parse_xtb_output("nothing useful here", charge=0, required=("total_energy_eh",))
    except xtb.MissingXTBField:
        pass
    else:
        raise AssertionError("a text without any energy must raise MissingXTBField")


def test_last_match_semantics_for_repeated_blocks() -> None:
    text = "total energy  -1.0 Eh\ntotal energy  -2.0 Eh\n"
    result = xtb.parse_xtb_output(text, charge=0, required=())
    assert result.total_energy_eh == -2.0


def test_fortran_exponent_is_accepted() -> None:
    text = "total energy   -1.234567890123D+01 Eh\n"
    result = xtb.parse_xtb_output(text, charge=0, required=())
    assert result.total_energy_eh == -12.34567890123
