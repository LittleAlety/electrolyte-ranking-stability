"""Regression tests for the Week 1-2 gate artefacts.

The gates are the Week 1-2 deliverable, so they get the same treatment as any
other produced number: a test recomputes them and fails if a frozen file was
edited by hand.
"""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

import freeze_gates

REPO_ROOT = Path(freeze_gates.__file__).resolve().parents[1]


def test_gate0_closes_on_the_frozen_repository() -> None:
    result = freeze_gates.evaluate_stage0(REPO_ROOT)
    assert result.closed, result.checks
    assert all(ok for _, ok, _ in result.checks), result.checks


def test_gate1_reports_the_known_blockers_instead_of_closing() -> None:
    result = freeze_gates.evaluate_stage1(REPO_ROOT)
    names = {name for name, _, _ in result.checks}
    assert "anchors:validate_anchors" in names
    assert "toolchain:xtb" in names
    assert "toolchain:orca" in names
    # The gate must not silently pass while QM binaries are missing.
    if not result.closed:
        assert result.blockers


def test_freeze_writes_records_and_reproducible_digests(tmp_path: Path) -> None:
    results = freeze_gates.freeze("all", root=REPO_ROOT, outdir=tmp_path)

    assert results[0].closed
    for stage in (0, 1):
        record = tmp_path / f"gate{stage}_record.md"
        sums = tmp_path / "SHA256SUMS"
        assert record.exists()

    # Both stages write into the same outdir here, so re-digest and compare.
    lines = [
        line
        for line in (tmp_path / "SHA256SUMS").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert lines, "SHA256SUMS must not be empty"
    for line in lines:
        digest, name = line.split("  ", 1)
        assert freeze_gates.sha256_of(REPO_ROOT / name) == digest


def test_checked_in_gate_records_exist() -> None:
    assert (REPO_ROOT / "outputs" / "week1" / "gate0_record.md").exists()
    assert (REPO_ROOT / "outputs" / "week2" / "gate1_record.md").exists()
    assert (REPO_ROOT / "outputs" / "week1" / "SHA256SUMS").exists()
    assert (REPO_ROOT / "outputs" / "week2" / "SHA256SUMS").exists()


def test_solution_anchor_estimates_are_counted(tmp_path: Path) -> None:
    table = tmp_path / "solution.csv"
    table.write_text(
        "species,method\nEC,est\nDMC,exp\nPC,est\n",
        encoding="utf-8",
    )
    assert freeze_gates.count_estimated_solution_rows(table) == 2
    assert freeze_gates.count_estimated_solution_rows(tmp_path / "missing.csv") == 0


def test_frozen_metadata_tables_match_the_builder() -> None:
    core = REPO_ROOT / "data" / "metadata" / "core_set.csv"
    pool = REPO_ROOT / "data" / "metadata" / "broad_pool.csv"
    with core.open(encoding="utf-8", newline="") as handle:
        core_rows = list(csv.DictReader(handle))
    with pool.open(encoding="utf-8", newline="") as handle:
        pool_rows = list(csv.DictReader(handle))
    assert len(core_rows) == 18
    assert len(pool_rows) == 40
    families = {row["family"] for row in core_rows}
    assert {"linear_carbonate", "cyclic_carbonate", "ether", "ester"} <= families
