"""Tests for executable discovery, the dry-run backend, and the xTB driver.

Everything here runs without xtb/CREST/ORCA installed: executables are faked with
a small launcher script in a temporary directory, and the xTB output text is a
canned sample written to match the real banner format.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from electrolyte_ranking import toolchain, xtb  # noqa: E402
from electrolyte_ranking.toolchain import (  # noqa: E402
    DryRunBackend,
    EnvironmentReport,
    find_executable,
    probe_environment,
    probe_tool,
    run_command,
)

XTB_VERSION_BANNER = "* xtb version 6.7.1 (fake) compiled by the test suite"

XTB_SAMPLE = """\
      -----------------------------------------------------------
     |                   =====================                   |
     |                        x T B                              |
     |                   =====================                   |
     |                       S. Grimme                           |
      -----------------------------------------------------------

     * xtb version 6.7.1 (edcfbbe) compiled by 'gcc 13.2.0'

     | TOTAL ENERGY               -12.3456789012 Eh   |

(HOMO)                    -0.2333 Eh      -6.3487 eV
(LUMO)                    -0.0302 Eh      -0.8217 eV
HOMO-LUMO GAP              0.2031 Eh       5.5270 eV

molecular dipole:
             x           y           z       tot (Debye)
q only:   0.0000      0.0000     -0.1234
full:     0.0100      0.0200     -0.5000       0.5004

molecular polarizability (0th order):
   alpha(0)  =   12.3450 a.u.

Mulliken charges:
   1  C    -0.123456
   2  H     0.061728
   3  O    -0.246913

Fermi level:    -0.1500 Eh   -4.0817 eV

normal termination of xtb
"""

XTB_UNBOUND_ANION = """\
     * xtb version 6.7.1 (fake)

total energy        -12.0000000000 Eh

(HOMO)                     0.1200 Eh       3.2653 eV
(LUMO)                     0.3000 Eh       8.1634 eV
HOMO-LUMO GAP              0.1800 Eh       4.8981 eV

normal termination of xtb
"""

XTB_SCF_FAILURE = """\
     * xtb version 6.7.1 (fake)

total energy        -12.0000000000 Eh

SCF CONVERGENCE IS NOT ACHIEVED
"""


def _make_fake_tool(directory: Path, name: str, body: str) -> Path:
    """Write a launcher named ``name`` that runs ``body`` with the current interpreter."""

    payload = directory / f"{name}_payload.py"
    payload.write_text(body, encoding="utf-8")
    if os.name == "nt":
        launcher = directory / f"{name}.cmd"
        launcher.write_text(
            f'@echo off\r\n"{sys.executable}" "{payload}" %*\r\n', encoding="utf-8"
        )
    else:
        launcher = directory / name
        launcher.write_text(
            f'#!/bin/sh\nexec "{sys.executable}" "{payload}" "$@"\n', encoding="utf-8"
        )
        launcher.chmod(0o755)
    return launcher


@pytest.fixture()
def fake_xtb(tmp_path: Path) -> Path:
    return _make_fake_tool(
        tmp_path, "xtb", f"print({XTB_VERSION_BANNER!r})\n"
    )


# --------------------------------------------------------------------------- #
# toolchain: discovery
# --------------------------------------------------------------------------- #


def test_find_executable_prefers_environment_variable(tmp_path: Path, fake_xtb: Path) -> None:
    environ = dict(os.environ)
    environ["ELECTROLYTE_XTB"] = str(fake_xtb)

    location = find_executable("xtb", environ=environ, search_path="")

    assert location is not None
    assert location.source == toolchain.SOURCE_ENVIRONMENT_VARIABLE
    assert Path(location.path).name.lower().startswith("xtb")


def test_find_executable_falls_back_to_path(tmp_path: Path, fake_xtb: Path) -> None:
    location = find_executable("xtb", environ={}, search_path=str(tmp_path))

    assert location is not None
    assert location.source == toolchain.SOURCE_PATH
    assert Path(location.path).parent == tmp_path


def test_find_executable_returns_none_when_absent(tmp_path: Path) -> None:
    # bundled_root is isolated explicitly: without it the repository's own
    # .toolchain/xtb would legitimately be found and this would assert the wrong thing.
    assert (
        find_executable("xtb", environ={}, search_path=str(tmp_path), bundled_root=tmp_path)
        is None
    )


def test_probe_environment_reports_missing_without_raising(tmp_path: Path) -> None:
    reports = probe_environment(
        ("xtb", "crest", "orca"), environ={}, search_path=str(tmp_path), bundled_root=tmp_path
    )

    assert [report.name for report in reports] == ["xtb", "crest", "orca"]
    assert all(report.found is False for report in reports)
    assert all(report.path is None and report.version is None for report in reports)


def test_probe_tool_captures_version_from_fake_binary(fake_xtb: Path) -> None:
    environ = dict(os.environ)
    environ["ELECTROLYTE_XTB"] = str(fake_xtb)

    report = probe_tool("xtb", environ=environ, search_path="")

    assert isinstance(report, EnvironmentReport)
    assert report.found is True
    assert report.source == toolchain.SOURCE_ENVIRONMENT_VARIABLE
    assert report.version == "6.7.1"


def test_environment_report_as_dict_has_documented_keys() -> None:
    report = EnvironmentReport(name="orca", found=False)

    assert report.as_dict() == {
        "name": "orca",
        "found": False,
        "path": None,
        "version": None,
        "source": None,
    }


def test_run_command_executes_a_real_process() -> None:
    completed = run_command(sys.executable, ["-c", "print('hello from child')"])

    assert completed.returncode == 0
    assert "hello from child" in completed.stdout


# --------------------------------------------------------------------------- #
# toolchain: dry-run backend
# --------------------------------------------------------------------------- #


def test_dry_run_backend_records_calls_and_replays_outputs() -> None:
    backend = DryRunBackend(outputs=["first", "second"])

    first = backend("xtb", ["a.xyz", "--opt"], cwd="run")
    second = backend("xtb", ["b.xyz", "--sp"], cwd="run", input_text="")

    assert first.stdout == "first"
    assert second.stdout == "second"
    assert backend.calls == [["xtb", "a.xyz", "--opt"], ["xtb", "b.xyz", "--sp"]]
    assert backend.invocations[0].cwd == "run"
    assert backend.invocations[1].input_text == ""


def test_dry_run_backend_falls_back_to_default_output() -> None:
    backend = DryRunBackend(default_output="canned")

    completed = backend("orca", ["job.inp"])

    assert completed.stdout == "canned"
    assert completed.returncode == 0


# --------------------------------------------------------------------------- #
# xtb: deterministic environment and command construction
# --------------------------------------------------------------------------- #


def test_thread_environment_pins_single_thread_and_overrides_base() -> None:
    environment = xtb.xtb_thread_environment({"OMP_NUM_THREADS": "8", "MKL_DYNAMIC": "TRUE"})

    assert environment["OMP_NUM_THREADS"] == "1"
    assert environment["MKL_NUM_THREADS"] == "1"
    assert environment["OMP_DYNAMIC"] == "FALSE"
    assert environment["MKL_DYNAMIC"] == "FALSE"


@pytest.mark.parametrize(
    ("job", "expected_job_flag"),
    [(xtb.JOB_OPTIMIZE, "--opt"), (xtb.JOB_FREQUENCY, "--ohess"), (xtb.JOB_SINGLE_POINT, None)],
)
def test_build_xtb_arguments_are_frozen(job: str, expected_job_flag: str | None) -> None:
    arguments = xtb.build_xtb_arguments(job, input_name="mol.xyz", charge=0, multiplicity=1)

    assert arguments[0] == "mol.xyz"
    if expected_job_flag is None:
        assert "--opt" not in arguments and "--ohess" not in arguments
    else:
        assert expected_job_flag in arguments
    assert arguments[arguments.index("--gfn") + 1] == "2"
    assert arguments[arguments.index("--chrg") + 1] == "0"
    assert arguments[arguments.index("--uhf") + 1] == "0"


def test_build_xtb_arguments_converts_multiplicity_to_unpaired_electrons() -> None:
    arguments = xtb.build_xtb_arguments(
        xtb.JOB_SINGLE_POINT, input_name="radical.xyz", charge=0, multiplicity=2
    )

    assert arguments[arguments.index("--uhf") + 1] == "1"


def test_build_xtb_arguments_rejects_non_frozen_gfn_and_unknown_job() -> None:
    with pytest.raises(ValueError):
        xtb.build_xtb_arguments("sp", input_name="m.xyz", charge=0, gfn=1)
    with pytest.raises(ValueError):
        xtb.build_xtb_arguments("md", input_name="m.xyz", charge=0)


def test_clear_scratch_removes_stale_files_but_keeps_the_input(tmp_path: Path) -> None:
    stale = tmp_path / "xtbrestart"
    stale.write_text("old", encoding="utf-8")
    (tmp_path / "wbo").write_text("old", encoding="utf-8")
    kept = tmp_path / "xtbopt.xyz"
    kept.write_text("geometry", encoding="utf-8")

    removed = xtb.clear_scratch(tmp_path, keep=("xtbopt.xyz",))

    assert {path.name for path in removed} == {"xtbrestart", "wbo"}
    assert not stale.exists()
    assert kept.exists()


# --------------------------------------------------------------------------- #
# xtb: parsing
# --------------------------------------------------------------------------- #


def test_parse_xtb_output_extracts_every_field() -> None:
    result = xtb.parse_xtb_output(XTB_SAMPLE, charge=0, job=xtb.JOB_OPTIMIZE)

    assert result.total_energy_eh == pytest.approx(-12.3456789012)
    assert result.homo_ev == pytest.approx(-6.3487)
    assert result.lumo_ev == pytest.approx(-0.8217)
    assert result.hl_gap_ev == pytest.approx(5.5270)
    assert result.dipole_debye == pytest.approx(0.5004)
    assert result.polarizability_alpha0 == pytest.approx(12.3450)
    assert result.fermi_level_eh == pytest.approx(-0.1500)
    assert result.fermi_level_ev == pytest.approx(-4.0817)
    assert result.mulliken_charges == pytest.approx((-0.123456, 0.061728, -0.246913))
    assert result.normal_termination is True
    assert result.scf_converged is True
    assert result.qc_flags == ()


def test_parse_xtb_output_raises_on_missing_total_energy() -> None:
    with pytest.raises(xtb.MissingXTBField) as error:
        xtb.parse_xtb_output("normal termination of xtb\n")

    assert "total_energy_eh" in str(error.value)


def test_require_fields_names_the_missing_quantity() -> None:
    result = xtb.parse_xtb_output(
        "total energy   -1.0 Eh\n\nnormal termination of xtb\n", charge=0
    )

    with pytest.raises(xtb.MissingXTBField) as error:
        result.require_fields("homo_ev", "polarizability_alpha0")

    message = str(error.value)
    assert "homo_ev" in message and "polarizability_alpha0" in message


def test_parse_xtb_output_flags_an_unbound_anion_only_for_anions() -> None:
    anion = xtb.parse_xtb_output(XTB_UNBOUND_ANION, charge=-1, job=xtb.JOB_SINGLE_POINT)
    neutral = xtb.parse_xtb_output(XTB_UNBOUND_ANION, charge=0, job=xtb.JOB_SINGLE_POINT)

    assert "unbound_anion" in anion.qc_flags
    assert "unbound_anion" not in neutral.qc_flags


def test_parse_xtb_output_flags_scf_failure_and_abnormal_termination() -> None:
    optimized = xtb.parse_xtb_output(XTB_SCF_FAILURE, charge=0, job=xtb.JOB_OPTIMIZE)
    single_point = xtb.parse_xtb_output(XTB_SCF_FAILURE, charge=0, job=xtb.JOB_SINGLE_POINT)

    assert optimized.normal_termination is False
    assert optimized.scf_converged is False
    assert set(optimized.qc_flags) == {"geometry_failed", "scf_failed"}
    assert set(single_point.qc_flags) == {"scf_failed"}


def test_parse_xtb_output_detects_imaginary_modes() -> None:
    text = XTB_SAMPLE + "\n   -12.34 cm-1  ******** imaginary mode ********\n"

    result = xtb.parse_xtb_output(text, charge=0, job=xtb.JOB_FREQUENCY)

    assert result.imaginary_modes is True
    assert "imaginary_mode_unresolved" in result.qc_flags


def test_parse_xtb_output_flags_are_from_the_frozen_vocabulary() -> None:
    from electrolyte_ranking.provenance import QC_FLAGS

    result = xtb.parse_xtb_output(XTB_UNBOUND_ANION, charge=-1)

    assert set(result.qc_flags) <= QC_FLAGS


# --------------------------------------------------------------------------- #
# xtb: run_xtb wiring
# --------------------------------------------------------------------------- #


def test_run_xtb_clears_scratch_and_parses_dry_run_output(tmp_path: Path) -> None:
    (tmp_path / "xtbrestart").write_text("stale", encoding="utf-8")
    backend = DryRunBackend(outputs=[XTB_SAMPLE])

    result = xtb.run_xtb(
        "xtb",
        xtb.JOB_OPTIMIZE,
        input_name="mol.xyz",
        charge=0,
        cwd=tmp_path,
        backend=backend,
    )

    assert backend.calls == [["xtb", "mol.xyz", "--opt", "--gfn", "2", "--chrg", "0", "--uhf", "0"]]
    assert not (tmp_path / "xtbrestart").exists()
    assert result.total_energy_eh == pytest.approx(-12.3456789012)
    assert result.returncode == 0


def test_run_xtb_pins_threads_in_the_child_environment() -> None:
    captured: dict[str, object] = {}

    def capturing_backend(
        executable,
        arguments,
        *,
        cwd=None,
        timeout_seconds=None,
        environment=None,
        input_text=None,
    ):
        captured["environment"] = environment
        return subprocess.CompletedProcess([str(executable), *arguments], 0, XTB_SAMPLE, "")

    xtb.run_xtb("xtb", xtb.JOB_SINGLE_POINT, input_name="mol.xyz", charge=0, backend=capturing_backend)

    environment = captured["environment"]
    assert isinstance(environment, dict)
    assert environment["OMP_NUM_THREADS"] == "1"
    assert environment["OMP_DYNAMIC"] == "FALSE"


def test_run_xtb_raises_on_a_nonzero_exit_code() -> None:
    backend = DryRunBackend(outputs=["boom"], returncode=1)

    with pytest.raises(xtb.XTBExecutionError):
        xtb.run_xtb("xtb", xtb.JOB_SINGLE_POINT, input_name="mol.xyz", charge=0, backend=backend)


# --------------------------------------------------------------------------- #
# scripts/check_environment.py
# --------------------------------------------------------------------------- #


def _run_check_environment(*arguments: str) -> subprocess.CompletedProcess:
    environ = dict(os.environ)
    environ["PATH"] = ""  # nothing real can be found
    # An override exported by the developer's shell would otherwise make these
    # assertions depend on the machine the suite happens to run on.
    for variable in ("ELECTROLYTE_XTB", "ELECTROLYTE_CREST", "ELECTROLYTE_ORCA"):
        environ.pop(variable, None)
    # Point the bundled-toolchain lookup at a directory that does not exist, so a
    # developer who really has .toolchain/xtb installed still sees "missing" here.
    environ["ELECTROLYTE_TOOLCHAIN_ROOT"] = str(_REPO_ROOT / "_no_toolchain_for_tests")
    return subprocess.run(
        [sys.executable, str(_REPO_ROOT / "scripts" / "check_environment.py"), *arguments],
        capture_output=True,
        text=True,
        env=environ,
        check=False,
    )


def test_check_environment_exits_zero_when_nothing_is_installed() -> None:
    completed = _run_check_environment("--json")

    assert completed.returncode == 0
    assert '"found": false' in completed.stdout


def test_check_environment_exits_two_for_a_missing_required_tool() -> None:
    completed = _run_check_environment("--require", "xtb")

    assert completed.returncode == 2
    assert "required tool" in completed.stderr
