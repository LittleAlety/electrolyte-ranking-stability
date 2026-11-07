"""The .toolchain fallback: dropping a binary must be enough, with no environment setup.

check_environment promises zero configuration, and that promise is only true if the
discovery rule lives in electrolyte_ranking.toolchain, because every caller
(check_environment, run_xtb_job, run_orca_job) goes through find_executable.
freeze_gates used to be the only caller that searched .toolchain itself, which is
how the gap stayed hidden.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from electrolyte_ranking import toolchain  # noqa: E402


def make_fake_binary(root: Path, relative: str) -> Path:
    binary = root / relative
    binary.parent.mkdir(parents=True, exist_ok=True)
    binary.write_text("fake engine\n", encoding="utf-8")
    return binary


def test_bundled_binary_is_found_without_environment_or_path(tmp_path: Path) -> None:
    root = tmp_path / ".toolchain"
    expected = make_fake_binary(root, "orca/orca_6_1_1/orca.exe")

    found = toolchain.find_executable("orca", environ={}, search_path="", bundled_root=root)

    assert found is not None
    assert Path(found.path) == expected
    assert found.source == toolchain.SOURCE_BUNDLED


def test_bundled_lookup_ignores_a_directory_with_the_tool_name(tmp_path: Path) -> None:
    root = tmp_path / ".toolchain"
    (root / "orca" / "orca").mkdir(parents=True)

    assert toolchain.find_executable("orca", environ={}, search_path="", bundled_root=root) is None


def test_environment_variable_still_wins_over_bundled(tmp_path: Path) -> None:
    root = tmp_path / ".toolchain"
    make_fake_binary(root, "orca/orca.exe")
    preferred = make_fake_binary(tmp_path / "elsewhere", "orca.exe")

    found = toolchain.find_executable(
        "orca",
        environ={"ELECTROLYTE_ORCA": str(preferred)},
        search_path="",
        bundled_root=root,
    )

    assert found is not None
    assert Path(found.path) == preferred
    assert found.source == toolchain.SOURCE_ENVIRONMENT_VARIABLE


def test_absent_bundled_binary_reports_none_instead_of_raising(tmp_path: Path) -> None:
    (tmp_path / ".toolchain").mkdir()

    assert toolchain.find_executable("orca", environ={}, search_path="", bundled_root=tmp_path / "missing") is None
    assert toolchain.find_executable("crest", environ={}, search_path="", bundled_root=tmp_path / ".toolchain") is None


def test_bundled_root_defaults_to_the_repository_toolchain() -> None:
    assert toolchain.bundled_toolchain_root() == _REPO_ROOT / ".toolchain"


@pytest.mark.skipif(
    not (toolchain.bundled_toolchain_root() / "xtb").is_dir(),
    reason="the bundled xTB tree is gitignored, so a fresh clone legitimately has none",
)
def test_the_probe_finds_the_bundled_xtb_with_no_environment_at_all() -> None:
    reports = toolchain.probe_environment(("xtb",), environ={}, search_path="")

    assert reports and reports[0].found
    assert reports[0].source == toolchain.SOURCE_BUNDLED

def test_toolchain_root_can_be_relocated_by_environment(tmp_path: Path) -> None:
    """ELECTROLYTE_TOOLCHAIN_ROOT isolates the bundled layer (used by the test suite)."""

    relocated = tmp_path / "somewhere-else"
    make_fake_binary(relocated, "orca/orca.exe")

    assert toolchain.bundled_toolchain_root(environ={"ELECTROLYTE_TOOLCHAIN_ROOT": str(relocated)}) == relocated
    found = toolchain.find_executable("orca", environ={"ELECTROLYTE_TOOLCHAIN_ROOT": str(relocated)}, search_path="")
    assert found is not None and found.source == toolchain.SOURCE_BUNDLED
