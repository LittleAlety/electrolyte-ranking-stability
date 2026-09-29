"""Tests for the ORCA driver (``run_orca``) and the runner CLI.

No ORCA binary is required: a fake ``orca`` launcher (a ``.cmd``/shim around a
small Python payload, the same trick ``tests/test_toolchain.py`` uses) echoes the
generated input file and then prints canned ORCA text. That exercises the whole
driver -- scratch directory, invocation, artifact collection, parsing and QC
flags -- against realistic stdout; only the real binary is missing. One test is
skipped unless a real ``orca`` executable is installed.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SRC = _REPO_ROOT / "src"
_SCRIPTS = _REPO_ROOT / "scripts"
for _directory in (_SRC, _SCRIPTS):
    if str(_directory) not in sys.path:
        sys.path.insert(0, str(_directory))

from electrolyte_ranking import orca, toolchain  # noqa: E402
from electrolyte_ranking.provenance import QC_FLAGS  # noqa: E402

ORCA_SAMPLE = """\
                                 *****************
                                 * O   R   C   A *
                                 *****************

Program Version 6.0.1 - RELEASE

---------------------
SCF ITERATIONS
---------------------
...
SCF CONVERGED AFTER  12 CYCLES

-------------
TOTAL SCF ENERGY
-------------
FINAL SINGLE POINT ENERGY  -412.345678901

                             ****ORCA TERMINATED NORMALLY****
"""

ORCA_SCF_FAILURE = """\
Program Version 6.0.1 - RELEASE

SCF ITERATIONS
...
SCF NOT CONVERGED
FINAL SINGLE POINT ENERGY  -412.000000000
"""

ORCA_NO_ENERGY = """\
Program Version 6.0.1 - RELEASE

SCF CONVERGED AFTER   5 CYCLES

****ORCA TERMINATED NORMALLY****
"""

ORCA_IMAGINARY = ORCA_SAMPLE + """
VIBRATIONAL FREQUENCIES
-----------------------
   0:     -12.34 cm-1   ***imaginary mode***
   1:      45.67 cm-1
"""

GEOMETRY = [("C", 0.0, 0.0, 0.0), ("O", 1.2, 0.0, 0.0)]


def _make_fake_orca(
    directory: Path,
    body: str,
    *,
    sleep: float = 0.0,
    echo_input: bool = True,
    write_gbw: bool = True,
    exit_code: int = 0,
) -> Path:
    """A launcher named ``orca`` that replays ``body`` with the current interpreter."""

    payload = directory / "orca_payload.py"
    payload.write_text(
        "import sys, time\n"
        f"sleep = {sleep!r}\n"
        "if sleep:\n"
        "    time.sleep(sleep)\n"
        f"body = {body!r}\n"
        f"echo_input = {echo_input!r}\n"
        f"write_gbw = {write_gbw!r}\n"
        'name = sys.argv[1] if len(sys.argv) > 1 else ""\n'
        "if name and (echo_input or write_gbw):\n"
        "    stem = name.rsplit('.', 1)[0]\n"
        "    if echo_input:\n"
        "        try:\n"
        '            with open(name, encoding="utf-8") as handle:\n'
        "                sys.stdout.write(handle.read())\n"
        "        except OSError:\n"
        "            pass\n"
        "    if write_gbw:\n"
        "        try:\n"
        '            with open(stem + ".gbw", "w", encoding="utf-8") as handle:\n'
        '                handle.write("fake gbw\\n")\n'
        "        except OSError:\n"
        "            pass\n"
        "sys.stdout.write(body)\n"
        f"sys.exit({exit_code})\n",
        encoding="utf-8",
    )
    if os.name == "nt":
        launcher = directory / "orca.cmd"
        launcher.write_text(
            f'@echo off\r\n"{sys.executable}" "{payload}" %*\r\n', encoding="utf-8"
        )
    else:
        launcher = directory / "orca"
        launcher.write_text(
            f'#!/bin/sh\nexec "{sys.executable}" "{payload}" "$@"\n', encoding="utf-8"
        )
        launcher.chmod(0o755)
    return launcher


def _run_orca(tmp_path: Path, body: str, job: str = orca.JOB_SINGLE_POINT, **kwargs):
    launcher = _make_fake_orca(tmp_path, body)
    return orca.run_orca(
        launcher,
        job,
        input_name="EC.inp",
        charge=0,
        multiplicity=1,
        geometry=GEOMETRY,
        cwd=tmp_path,
        timeout_seconds=60.0,
        **kwargs,
    )


# --------------------------------------------------------------------------- #
# run_orca: the happy path
# --------------------------------------------------------------------------- #


def test_run_orca_parses_a_normal_single_point(tmp_path: Path) -> None:
    result = _run_orca(tmp_path, ORCA_SAMPLE)

    assert result.final_energy_eh == pytest.approx(-412.345678901)
    assert result.normal_termination is True
    assert result.scf_converged is True
    assert result.n_scf_cycles == 12
    assert result.version == "6.0.1"
    assert result.imaginary_modes is None
    assert result.qc_flags == ()
    assert result.returncode == 0


def test_run_orca_keeps_input_output_and_artifacts_and_clears_scratch(tmp_path: Path) -> None:
    _run_orca(tmp_path, ORCA_SAMPLE)

    assert (tmp_path / "EC.inp").exists()
    assert (tmp_path / "EC.out").exists()
    assert (tmp_path / "EC.gbw").exists()
    assert not (tmp_path / "EC_scratch").exists()

    kept = (tmp_path / "EC.out").read_text(encoding="utf-8")
    assert "! r2SCAN-3c" in kept
    assert "%pal" in kept


def test_run_orca_auto_nprocs_is_derived_from_the_machine_and_capped(tmp_path: Path) -> None:
    result = _run_orca(tmp_path, ORCA_SAMPLE)

    expected = min(os.cpu_count() or 1, orca.DEFAULT_NPROCS_CAP)
    assert result.nprocs == expected
    assert f"nprocs {expected}" in (tmp_path / "EC.inp").read_text(encoding="utf-8")


def test_run_orca_respects_an_explicit_nprocs(tmp_path: Path) -> None:
    result = _run_orca(tmp_path, ORCA_SAMPLE, nprocs=3)

    assert result.nprocs == 3
    assert "nprocs 3" in (tmp_path / "EC.inp").read_text(encoding="utf-8")


def test_resolve_nprocs_bounds_and_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(orca.os, "cpu_count", lambda: 64)

    assert orca.resolve_nprocs() == orca.DEFAULT_NPROCS_CAP
    assert orca.resolve_nprocs(cap=None) == 64
    assert orca.resolve_nprocs(cap=2) == 2
    assert orca.resolve_nprocs(5) == 5

    with pytest.raises(orca.ORCAError):
        orca.resolve_nprocs(0)


def test_run_orca_rejects_an_unknown_job(tmp_path: Path) -> None:
    with pytest.raises(orca.ORCAError):
        orca.run_orca(
            "orca",
            "ts",
            input_name="EC.inp",
            charge=0,
            multiplicity=1,
            geometry=GEOMETRY,
            cwd=tmp_path,
        )


# --------------------------------------------------------------------------- #
# run_orca: failure modes
# --------------------------------------------------------------------------- #


def test_run_orca_flags_scf_failure_for_a_single_point(tmp_path: Path) -> None:
    result = _run_orca(tmp_path, ORCA_SCF_FAILURE)

    assert result.scf_converged is False
    assert result.normal_termination is False
    assert set(result.qc_flags) == {"scf_failed"}


def test_run_orca_flags_a_geometry_failure_for_an_opt_job(tmp_path: Path) -> None:
    result = _run_orca(tmp_path, ORCA_SCF_FAILURE, job=orca.JOB_OPTIMIZE)

    assert set(result.qc_flags) == {"geometry_failed", "scf_failed"}


def test_run_orca_raises_when_the_final_energy_is_absent(tmp_path: Path) -> None:
    with pytest.raises(orca.MissingORCAField):
        _run_orca(tmp_path, ORCA_NO_ENERGY)


def test_run_orca_keeps_a_missing_energy_when_required_is_empty(tmp_path: Path) -> None:
    result = _run_orca(tmp_path, ORCA_NO_ENERGY, required=())

    assert result.final_energy_eh is None
    assert result.normal_termination is True


def test_run_orca_raises_on_a_nonzero_exit_code(tmp_path: Path) -> None:
    launcher = _make_fake_orca(tmp_path, ORCA_SAMPLE, exit_code=3)

    with pytest.raises(orca.ORCAExecutionError):
        orca.run_orca(
            launcher,
            orca.JOB_SINGLE_POINT,
            input_name="EC.inp",
            charge=0,
            multiplicity=1,
            geometry=GEOMETRY,
            cwd=tmp_path,
            timeout_seconds=60.0,
        )


def test_run_orca_raises_when_nothing_is_written(tmp_path: Path) -> None:
    launcher = _make_fake_orca(tmp_path, "", echo_input=False, write_gbw=False)

    with pytest.raises(orca.ORCAExecutionError):
        orca.run_orca(
            launcher,
            orca.JOB_SINGLE_POINT,
            input_name="EC.inp",
            charge=0,
            multiplicity=1,
            geometry=GEOMETRY,
            cwd=tmp_path,
            timeout_seconds=60.0,
        )


def test_run_orca_raises_on_timeout(tmp_path: Path) -> None:
    launcher = _make_fake_orca(tmp_path, ORCA_SAMPLE, sleep=3.0)

    with pytest.raises(orca.ORCAExecutionError):
        orca.run_orca(
            launcher,
            orca.JOB_SINGLE_POINT,
            input_name="EC.inp",
            charge=0,
            multiplicity=1,
            geometry=GEOMETRY,
            cwd=tmp_path,
            timeout_seconds=0.5,
        )


# --------------------------------------------------------------------------- #
# parsing: frequencies, versions, vocabulary
# --------------------------------------------------------------------------- #


def test_parse_orca_output_flags_imaginary_modes_only_for_frequency_jobs() -> None:
    frequency = orca.parse_orca_output(ORCA_IMAGINARY, job=orca.JOB_FREQUENCY)
    single_point = orca.parse_orca_output(ORCA_IMAGINARY, job=orca.JOB_SINGLE_POINT)

    assert frequency.imaginary_modes is True
    assert "imaginary_mode_unresolved" in frequency.qc_flags
    assert single_point.imaginary_modes is None
    assert "imaginary_mode_unresolved" not in single_point.qc_flags


def test_parse_orca_output_reports_a_clean_spectrum_as_no_imaginary_modes() -> None:
    text = ORCA_SAMPLE + "\nVIBRATIONAL FREQUENCIES\n   0:   45.67 cm-1\n"

    result = orca.parse_orca_output(text, job=orca.JOB_FREQUENCY)

    assert result.imaginary_modes is False
    assert "imaginary_mode_unresolved" not in result.qc_flags


def test_run_orca_frequency_job_reports_imaginary_modes(tmp_path: Path) -> None:
    result = _run_orca(tmp_path, ORCA_IMAGINARY, job=orca.JOB_FREQUENCY)

    assert result.imaginary_modes is True
    assert "imaginary_mode_unresolved" in result.qc_flags
    assert "Freq" in (tmp_path / "EC.inp").read_text(encoding="utf-8")


def test_read_orca_version_parses_the_logo_and_tolerates_junk() -> None:
    assert orca.read_orca_version(ORCA_SAMPLE) == "6.0.1"
    assert orca.read_orca_version("Program Version 5.0.4 - RELEASE") == "5.0.4"
    assert orca.read_orca_version("no banner here") is None
    assert orca.read_orca_version("") is None
    assert orca.read_orca_version(None) is None


def test_parse_orca_output_flags_come_from_the_frozen_vocabulary() -> None:
    for text in (ORCA_SAMPLE, ORCA_SCF_FAILURE, ORCA_NO_ENERGY, ORCA_IMAGINARY):
        for job in orca.ORCA_JOBS:
            result = orca.parse_orca_output(text, charge=0, job=job, required=())
            assert set(result.qc_flags) <= QC_FLAGS


def test_build_orca_arguments_is_just_the_input_name() -> None:
    assert orca.build_orca_arguments("EC.inp") == ["EC.inp"]


# --------------------------------------------------------------------------- #
# scripts/run_orca_job.py
# --------------------------------------------------------------------------- #


def _run_cli(*arguments: str, environ=None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(_SCRIPTS / "run_orca_job.py"), *arguments],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=environ,
        check=False,
    )


def test_cli_dry_run_writes_the_input_and_a_not_run_record(tmp_path: Path) -> None:
    completed = _run_cli(
        "--name", "EC",
        "--smiles", "O=C1OCCO1",
        "--job", "sp",
        "--solvent", "acetonitrile",
        "--outdir", str(tmp_path),
        "--dry-run",
    )

    assert completed.returncode == 0, completed.stderr
    assert "not_run" in completed.stdout
    assert (tmp_path / "EC.inp").exists()

    record = json.loads((tmp_path / "EC_orca.json").read_text(encoding="utf-8"))
    assert record["status"] == "not_run"
    assert record["input"] == (tmp_path / "EC.inp").read_text(encoding="utf-8")
    assert "! r2SCAN-3c" in record["input"]
    assert "%pal" in record["input"]
    assert record["qc_flags"] == []
    assert record["provenance"]["software"] == "ORCA"
    assert record["provenance"]["solvent_model"] == "CPCM(SMD, acetonitrile)"


def test_cli_dry_run_defaults_to_gas_phase_and_needs_no_orca(tmp_path: Path) -> None:
    environ = dict(os.environ)
    environ["PATH"] = ""
    environ.pop("ELECTROLYTE_ORCA", None)
    # A real ORCA sitting under .toolchain/ must not turn this into a live run.
    environ["ELECTROLYTE_TOOLCHAIN_ROOT"] = str(tmp_path / "no_such_toolchain")

    completed = _run_cli(
        "--name", "DMC",
        "--smiles", "COC(=O)OC",
        "--outdir", str(tmp_path),
        "--dry-run",
        environ=environ,
    )

    assert completed.returncode == 0, completed.stderr
    record = json.loads((tmp_path / "DMC_orca.json").read_text(encoding="utf-8"))
    assert record["provenance"]["solvent_model"] == "gas-phase"
    assert "%cpcm" not in record["input"]


def test_cli_without_orca_and_without_dry_run_explains_the_install(tmp_path: Path) -> None:
    environ = dict(os.environ)
    environ["PATH"] = ""
    environ.pop("ELECTROLYTE_ORCA", None)
    # A real ORCA sitting under .toolchain/ must not turn this into a live run.
    environ["ELECTROLYTE_TOOLCHAIN_ROOT"] = str(tmp_path / "no_such_toolchain")

    completed = _run_cli(
        "--name", "EC",
        "--smiles", "O=C1OCCO1",
        "--outdir", str(tmp_path),
        environ=environ,
    )

    assert completed.returncode == 2
    assert "ELECTROLYTE_ORCA" in completed.stderr
    assert ".toolchain" in completed.stderr


# --------------------------------------------------------------------------- #
# real binary (skipped until ORCA is installed)
# --------------------------------------------------------------------------- #


@pytest.mark.skipif(
    toolchain.find_executable("orca") is None,
    reason="ORCA is not installed on this machine",
)
def test_run_orca_with_a_real_binary(tmp_path: Path) -> None:
    located = toolchain.find_executable("orca")
    assert located is not None

    result = orca.run_orca(
        located.path,
        orca.JOB_SINGLE_POINT,
        input_name="water.inp",
        charge=0,
        multiplicity=1,
        geometry=[("O", 0.0, 0.0, 0.0), ("H", 0.96, 0.0, 0.0), ("H", -0.24, 0.93, 0.0)],
        cwd=tmp_path,
        timeout_seconds=900.0,
    )

    assert result.normal_termination is True
    assert result.final_energy_eh is not None



def test_run_orca_clears_a_stale_density_left_in_the_scratch_directory(
    tmp_path: Path,
) -> None:
    """Regression: a stale ``<stem>.gbw`` seeded the SCF guess of the next run.

    ``run_orca`` reuses ``<stem>_scratch`` between runs.  When an earlier attempt
    was killed, the directory survives with its ``<stem>.gbw``, and ORCA reads a
    same-named ``.gbw`` as the initial guess.  ``SN_m1_reduced_sp`` converged to
    23 of 45 electrons that way (-126.8 Eh instead of about -271.6 Eh) and still
    reported normal termination, so the number looked like a result.
    """
    scratch = tmp_path / "EC_scratch"
    scratch.mkdir()
    (scratch / "EC.gbw").write_text("density of some other state\n", encoding="utf-8")

    _run_orca(tmp_path, ORCA_SAMPLE)

    kept = (tmp_path / "EC.gbw").read_text(encoding="utf-8")
    assert "density of some other state" not in kept
    assert "fake gbw" in kept


def test_parse_orca_output_flags_a_wrong_electron_count() -> None:
    """A converged SCF can still hold the wrong number of electrons."""
    text = ORCA_SAMPLE.replace(
        "ORCA TERMINATED NORMALLY",
        "**** WARNING: LOEWDIN FINDS   23.0000000 ELECTRONS INSTEAD OF 45 ****\n"
        "ORCA TERMINATED NORMALLY",
    )
    result = orca.parse_orca_output(text)

    assert result.normal_termination is True
    assert result.scf_converged is True
    assert "electron_count_mismatch" in result.qc_flags
    assert "scf_failed" not in result.qc_flags
    assert set(result.qc_flags) <= QC_FLAGS
