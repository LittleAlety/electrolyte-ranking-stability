"""ORCA on Windows: the ASCII-path constraints of the msmpi build.

Measured on this machine (ORCA 6.1.1 Win64 msmpi, 2026-09-29):

* ``%pal nprocs > 1`` makes ORCA launch its helpers through ``mpiexec``;
* MS-MPI rewrites a non-ASCII path into ``?????`` and then fails ("Error (5)"),
  so a non-ASCII *executable* path silently disables parallel runs;
* a serial run works from any path, Chinese directory names included;
* gas-phase EC at r2SCAN-3c gives -342.352339517519 Eh with 1 and with 8
  processes, i.e. the downgrade costs time, not accuracy.

These tests pin those facts down so a future refactor cannot quietly lose them.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
for _directory in (_REPO_ROOT / "src", _REPO_ROOT / "scripts"):
    if str(_directory) not in sys.path:
        sys.path.insert(0, str(_directory))

from electrolyte_ranking import orca  # noqa: E402
from electrolyte_ranking.toolchain import DryRunBackend  # noqa: E402

ORCA_SAMPLE = """\
                         Program Version 6.1.1  -  RELEASE   -

SCF CONVERGED AFTER 12 CYCLES
FINAL SINGLE POINT ENERGY      -342.352339517519

****ORCA TERMINATED NORMALLY****
"""

GEOMETRY = [("O", 0.0, 0.0, 0.0), ("H", 0.96, 0.0, 0.0), ("H", -0.24, 0.93, 0.0)]

CHINESE_DIR = "\u4e2d\u6587\u76ee\u5f55"


def test_is_ascii_safe_accepts_plain_paths_and_rejects_chinese_ones(tmp_path: Path) -> None:
    assert orca.is_ascii_safe("E:/ORCA/orca_6_1_1/orca.exe")
    assert not orca.is_ascii_safe(str(tmp_path / CHINESE_DIR / "orca.exe"))


def test_ascii_output_directory_keeps_the_scratch_beside_the_results(tmp_path: Path) -> None:
    assert orca.resolve_scratch_root(tmp_path) == tmp_path


def test_non_ascii_output_directory_relocates_the_scratch_to_ascii(tmp_path: Path) -> None:
    root = orca.resolve_scratch_root(tmp_path / CHINESE_DIR)

    assert str(root).isascii()
    assert "electrolyte_orca_scratch" in str(root)
    assert Path(tempfile.gettempdir()) in root.parents


def test_scratch_root_can_be_pinned_by_argument_or_environment(tmp_path: Path) -> None:
    pinned = tmp_path / "pinned"

    assert orca.resolve_scratch_root(tmp_path / CHINESE_DIR, scratch_root=pinned) == pinned
    assert (
        orca.resolve_scratch_root(tmp_path / CHINESE_DIR, environ={"ELECTROLYTE_ORCA_SCRATCH": str(pinned)})
        == pinned
    )


def test_non_ascii_executable_downgrades_the_run_to_serial(tmp_path: Path) -> None:
    backend = DryRunBackend(default_output=ORCA_SAMPLE)

    result = orca.run_orca(
        str(tmp_path / CHINESE_DIR / "orca.exe"),
        orca.JOB_SINGLE_POINT,
        input_name="EC.inp",
        charge=0,
        multiplicity=1,
        geometry=GEOMETRY,
        cwd=tmp_path,
        backend=backend,
    )

    assert result.nprocs == 1
    assert result.parallel_note == orca.NON_ASCII_PARALLEL_NOTE
    assert "nprocs 1" in (tmp_path / "EC.inp").read_text(encoding="utf-8")
    assert result.final_energy_eh == -342.352339517519


def test_ascii_executable_keeps_the_parallel_request(tmp_path: Path) -> None:
    backend = DryRunBackend(default_output=ORCA_SAMPLE)

    result = orca.run_orca(
        str(tmp_path / "orca.exe"),
        orca.JOB_SINGLE_POINT,
        input_name="EC.inp",
        charge=0,
        multiplicity=1,
        geometry=GEOMETRY,
        cwd=tmp_path,
        nprocs=4,
        backend=backend,
    )

    assert result.nprocs == 4
    assert result.parallel_note == ""
    assert "nprocs 4" in (tmp_path / "EC.inp").read_text(encoding="utf-8")


def test_scratch_execution_moves_off_a_non_ascii_output_directory(tmp_path: Path) -> None:
    backend = DryRunBackend(default_output=ORCA_SAMPLE)
    workdir = tmp_path / CHINESE_DIR
    workdir.mkdir(parents=True)

    orca.run_orca(
        str(tmp_path / "orca.exe"),
        orca.JOB_SINGLE_POINT,
        input_name="EC.inp",
        charge=0,
        multiplicity=1,
        geometry=GEOMETRY,
        cwd=workdir,
        backend=backend,
    )

    invocation_cwd = backend.invocations[0].cwd
    assert invocation_cwd is not None
    assert invocation_cwd.isascii()
    # The input file still lands in the requested output directory for traceability.
    assert (workdir / "EC.inp").exists()
