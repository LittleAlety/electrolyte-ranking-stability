"""Tests for ORCA input construction and the FINAL SINGLE POINT ENERGY parser.

No ORCA binary is required: inputs are built from explicit parameters and the
output text is a canned sample that mirrors ORCA's real banner.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from electrolyte_ranking import orca  # noqa: E402
from electrolyte_ranking.orca import (  # noqa: E402
    MissingORCAField,
    build_orca_input,
    orca_terminated_normally,
    parse_orca_energies,
    parse_orca_energy,
    write_orca_input,
)
from electrolyte_ranking.toolchain import probe_tool  # noqa: E402

ORCA_SAMPLE = """\
                                 *****************
                                 * O   R   C   A *
                                 *****************

Program Version 5.0.4 - RELEASE

-------------
SCF ITERATIONS
-------------
FINAL SINGLE POINT ENERGY     -1234.567890123456
-------------
GEOMETRY OPTIMIZATION CYCLE   1
-------------
FINAL SINGLE POINT ENERGY     -1234.890123456789

                             ****ORCA TERMINATED NORMALLY****
"""


# --------------------------------------------------------------------------- #
# input construction
# --------------------------------------------------------------------------- #


def test_build_single_point_gas_phase_input() -> None:
    text = build_orca_input(
        charge=0,
        multiplicity=1,
        geometry=[("C", 0.0, 0.0, 0.0), ("O", 1.2, 0.0, 0.0)],
    )

    assert "! r2SCAN-3c" in text
    assert "Opt" not in text and "Freq" not in text
    assert "%cpcm" not in text and "%pal" not in text
    assert "* xyz 0 1" in text
    assert text.endswith("*\n")
    assert text.count("*") >= 2


def test_build_opt_freq_input_with_smd_solvent_and_parallelism() -> None:
    text = build_orca_input(
        charge=0,
        multiplicity=1,
        geometry=[("C", 0.0, 0.0, 0.0)],
        job=orca.JOB_OPTIMIZE_FREQUENCY,
        solvent="acetonitrile",
        nprocs=4,
        maxcore_mb=2000,
        scf_convergence="TightSCF",
    )

    assert "! r2SCAN-3c Opt Freq TightSCF" in text
    assert "%pal" in text
    assert "  nprocs 4" in text
    assert "%maxcore 2000" in text
    assert "%cpcm" in text
    assert "  smd true" in text
    assert '  SMDsolvent "acetonitrile"' in text
    lines = text.splitlines()
    assert lines[lines.index("%pal") + 2] == "end"


def test_build_input_with_bare_epsilon_solvent_block() -> None:
    text = build_orca_input(
        charge=0,
        multiplicity=1,
        geometry="C 0.0 0.0 0.0\nO 1.2 0.0 0.0",
        epsilon=36.64,
    )

    assert "epsilon 36.64" in text
    assert "smd" not in text
    assert "SMDsolvent" not in text


def test_build_input_records_charge_and_multiplicity_for_an_anion() -> None:
    text = build_orca_input(
        charge=-1,
        multiplicity=2,
        geometry=[("C", 0.0, 0.0, 0.0)],
        job=orca.JOB_OPTIMIZE,
    )

    assert "* xyz -1 2" in text
    assert "! r2SCAN-3c Opt" in text


def test_build_input_can_start_from_a_stored_gbw() -> None:
    """``moinp`` must add MORead *and* the %moinp block, or the guess is ignored."""

    text = build_orca_input(
        charge=-1,
        multiplicity=2,
        geometry="C 0.0 0.0 0.0",
        epsilon=20.0,
        moinp="EMC_gas.gbw",
    )

    assert "! r2SCAN-3c MORead" in text
    assert '%moinp "EMC_gas.gbw"' in text
    # the %moinp block has to precede the coordinate block
    assert text.index("%moinp") < text.index("* xyz")


def test_build_input_without_moinp_is_unchanged() -> None:
    """The default path must not grow an MORead or a %moinp line."""

    text = build_orca_input(
        charge=0,
        multiplicity=1,
        geometry="C 0.0 0.0 0.0",
        epsilon=20.0,
    )

    assert "MORead" not in text
    assert "%moinp" not in text


def test_build_input_rejects_conflicting_solvent_specifications() -> None:
    with pytest.raises(orca.ORCAError):
        build_orca_input(
            charge=0,
            multiplicity=1,
            geometry=[("C", 0.0, 0.0, 0.0)],
            solvent="water",
            epsilon=78.4,
        )


def test_build_input_rejects_unknown_job() -> None:
    with pytest.raises(orca.ORCAError):
        build_orca_input(charge=0, multiplicity=1, geometry=[("C", 0.0, 0.0, 0.0)], job="ts")


def test_write_orca_input_round_trips_through_a_file(tmp_path: Path) -> None:
    destination = write_orca_input(
        tmp_path / "job.inp",
        charge=0,
        multiplicity=1,
        geometry=[("C", 0.0, 0.0, 0.0)],
    )

    assert destination.read_text(encoding="utf-8").startswith("! r2SCAN-3c")


# --------------------------------------------------------------------------- #
# output parsing
# --------------------------------------------------------------------------- #


def test_parse_orca_energy_returns_the_last_single_point_energy() -> None:
    assert parse_orca_energy(ORCA_SAMPLE) == pytest.approx(-1234.890123456789)


def test_parse_orca_energies_returns_every_step_in_order() -> None:
    assert parse_orca_energies(ORCA_SAMPLE) == pytest.approx(
        (-1234.567890123456, -1234.890123456789)
    )


def test_parse_orca_energy_raises_when_the_job_never_reached_scf() -> None:
    with pytest.raises(MissingORCAField) as error:
        parse_orca_energy("orca failed to start\n")

    assert "FINAL SINGLE POINT ENERGY" in str(error.value)
    assert issubclass(MissingORCAField, ValueError)


def test_termination_banner_is_detected() -> None:
    assert orca_terminated_normally(ORCA_SAMPLE) is True
    assert orca_terminated_normally("no banner here") is False


def test_parse_orca_energy_accepts_positive_and_negative_values() -> None:
    text = "FINAL SINGLE POINT ENERGY         76.123456789\n"

    assert parse_orca_energy(text) == pytest.approx(76.123456789)


# --------------------------------------------------------------------------- #
# orca version probe (fake executable, no ORCA installed)
# --------------------------------------------------------------------------- #


def test_probe_tool_reads_an_orca_version_banner(tmp_path: Path) -> None:
    payload = tmp_path / "orca_payload.py"
    payload.write_text("print('Program Version 5.0.4 - RELEASE')\n", encoding="utf-8")
    if os.name == "nt":
        launcher = tmp_path / "orca.cmd"
        launcher.write_text(
            f'@echo off\r\n"{sys.executable}" "{payload}" %*\r\n', encoding="utf-8"
        )
    else:
        launcher = tmp_path / "orca"
        launcher.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{payload}" "$@"\n', encoding="utf-8")
        launcher.chmod(0o755)

    environ = dict(os.environ)
    environ["ELECTROLYTE_ORCA"] = str(launcher)
    report = probe_tool("orca", environ=environ, search_path="")

    assert report.found is True
    assert report.version == "5.0.4"
