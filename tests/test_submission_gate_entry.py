"""Entry-level tests: the generic submission_gate is enforced BEFORE any side effect.

Tests that the generic gate:
1. Runs before any bridge call (doctor, lock, submit)
2. Stacks with (does not replace) the EC contract
3. Rejects missing gate field, non-OPEN states, and submitted!=False
4. Allows valid OPEN gate through to reach the mock submitter

No real sbatch is invoked; all bridge calls are mocked via FakeRunner.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

MODULE = Path(__file__).resolve().parents[1] / "scripts/wp_production/submit_hpc_batch.py"
spec = importlib.util.spec_from_file_location("submit_hpc_batch_gate_entry", MODULE)
submit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(submit)

GEOM = "4\nTest\nC 0.000000000 0.000000000 0.000000000\n" \
       "O 1.400000000 0.000000000 0.000000000\nH 2.600000000 0.200000000 0.000000000\n" \
       "N 0.000000000 1.900000000 0.000000000\n"


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class FakeRunner:
    """Records all bridge calls; simulates doctor/lock/squeue success, submit stub."""
    def __init__(self, submit_output="Submitted batch job 88888", submit_rc=0):
        self.calls = []
        self.submit_output = submit_output
        self.submit_rc = submit_rc

    def __call__(self, argv):
        argv = [str(a) for a in argv]
        self.calls.append(argv)
        from types import SimpleNamespace
        action = argv[1] if len(argv) > 1 else ""
        if action == "doctor":
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        if action == "run":
            command = argv[2] if len(argv) > 2 else ""
            if command.startswith("mkdir"):
                return SimpleNamespace(returncode=0, stdout="", stderr="")
            if "squeue" in command:
                return SimpleNamespace(returncode=0, stdout="", stderr="")
            if command.startswith("rmdir"):
                return SimpleNamespace(returncode=0, stdout="", stderr="")
        if action == "submit":
            return SimpleNamespace(returncode=self.submit_rc, stdout=self.submit_output,
                                   stderr="")
        raise AssertionError("unexpected bridge call: %r" % (argv,))


def make_generic_package(tmp_path, *, gate="OPEN", submitted=False, skip_gate_field=False,
                         profile="orca_production_v1", name="test_generic_pkg"):
    """Build a non-EC package with configurable gate state."""
    pkg = tmp_path / name
    task = pkg / "tasks" / "test__state"
    task.mkdir(parents=True)
    (task / "geom.xyz").write_text(GEOM, encoding="utf-8", newline="\n")
    (task / "job.inp").write_text(
        "! wB97X-D4 def2-TZVPD Opt\n%pal nprocs 4 end\n* xyzfile 0 1 geom.xyz\n",
        encoding="utf-8", newline="\n")
    (task / "import_level.txt").write_text("production_v1_start\n", encoding="utf-8")
    (pkg / "batch_1.sbatch").write_text("#!/bin/bash\n", encoding="utf-8")
    (pkg / "batch_1.txt").write_text("tasks/test__state\n", encoding="utf-8")

    manifest = {
        "schema_version": "2.0",
        "package": pkg.name,
        "resource_profile": profile,
        "cores_per_task": 4,
        "wall_hours_per_task": 4,
        "task_count": 1,
        "reserved_core_hours": 16,
        "batches": [{"batch": 1, "count": 1}],
        "submitted": submitted,
    }
    if not skip_gate_field:
        manifest["submission_gate"] = gate
    (pkg / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return pkg


def call_submit(pkg, tmp_path, runner, ledger=None):
    """Submit with minimal boilerplate."""
    return submit.submit_batch(
        pkg, 1, "project/test/generic_pkg",
        runner=runner, bridge=tmp_path / "hpc.ps1",
        attempts_ledger=ledger if ledger is not None else []
    )


def expect_refused_before_bridge(pkg, tmp_path, runner, match, ledger=None):
    """Assert that the request is refused with zero bridge calls."""
    with pytest.raises(ValueError, match=match):
        call_submit(pkg, tmp_path, runner, ledger)
    assert runner.calls == [], \
        "refusal must happen before any bridge call; got: %r" % runner.calls


def test_valid_open_gate_reaches_the_fake_submitter(tmp_path):
    """OPEN gate with submitted=False should reach submit and set status."""
    pkg = make_generic_package(tmp_path, gate="OPEN", submitted=False)
    runner = FakeRunner()
    result = call_submit(pkg, tmp_path, runner)
    assert result["status"] == "submitted" and result["job_id"] == "88888"
    # Should have called doctor, mkdir (lock), squeue, and submit
    actions = [c[1] for c in runner.calls if len(c) > 1]
    assert "doctor" in actions
    assert "submit" in actions


def test_hold_gate_is_refused_before_any_bridge_call(tmp_path):
    """HOLD gate must be rejected before doctor, lock, or submit."""
    pkg = make_generic_package(tmp_path, gate="HOLD", submitted=False)
    runner = FakeRunner()
    expect_refused_before_bridge(pkg, tmp_path, runner, "not authorized.*HOLD")


def test_missing_gate_field_is_refused_before_any_bridge_call(tmp_path):
    """Missing submission_gate field must be rejected (never treated as permission)."""
    pkg = make_generic_package(tmp_path, skip_gate_field=True, submitted=False)
    runner = FakeRunner()
    expect_refused_before_bridge(pkg, tmp_path, runner, "no submission_gate.*missing field")


def test_unknown_gate_state_is_refused_before_any_bridge_call(tmp_path):
    """Unknown gate values (not in SUBMITTABLE_GATE_STATES) must be rejected."""
    pkg = make_generic_package(tmp_path, gate="PENDING_REVIEW", submitted=False)
    runner = FakeRunner()
    expect_refused_before_bridge(pkg, tmp_path, runner, "not authorized")


def test_whitespace_in_gate_is_refused(tmp_path):
    """Gate value with surrounding whitespace must be rejected (stripped check)."""
    pkg = make_generic_package(tmp_path, gate=" OPEN ", submitted=False)
    runner = FakeRunner()
    expect_refused_before_bridge(pkg, tmp_path, runner, "not authorized")


def test_submitted_true_is_refused_before_any_bridge_call(tmp_path):
    """submitted=True must be rejected before any bridge call."""
    pkg = make_generic_package(tmp_path, gate="OPEN", submitted=True)
    runner = FakeRunner()
    expect_refused_before_bridge(pkg, tmp_path, runner, "submitted=false")


def test_ec_hold_still_rejected_by_generic_gate_before_ec_contract(tmp_path):
    """EC package with HOLD gate is rejected by generic gate before EC contract runs."""
    # This verifies the generic gate stacks with EC contract and runs first
    pkg = make_generic_package(tmp_path, gate="HOLD", submitted=False, name="hpc_ec_test")
    # Add EC-like fields to make it look EC-ish (but generic gate rejects first)
    manifest = json.loads((pkg / "manifest.json").read_text(encoding="utf-8"))
    manifest["campaign"] = "test_campaign"
    manifest["active_candidate"] = "test_candidate"
    (pkg / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    runner = FakeRunner()
    # Should be rejected by generic gate, not even reaching EC contract checks
    expect_refused_before_bridge(pkg, tmp_path, runner, "not authorized.*HOLD")


def test_ec_open_gate_passes_generic_gate_then_reaches_ec_contract(tmp_path):
    """EC package with OPEN gate passes generic gate, then may be rejected by EC contract."""
    pkg = make_generic_package(tmp_path, gate="OPEN", submitted=False, name="hpc_ec_test_v2_p4")
    # Add EC fields
    manifest = json.loads((pkg / "manifest.json").read_text(encoding="utf-8"))
    manifest["campaign"] = "four_state_recovery_20261023"
    manifest["active_candidate"] = "ec_v2_p4"
    manifest["resource_profile"] = "orca_production_4h_v1"
    (pkg / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    runner = FakeRunner()
    # EC package requires EC contract validation, which will fail without proper ledger
    # But crucially, the generic gate passed (not rejected with "not authorized")
    with pytest.raises(ValueError) as exc_info:
        call_submit(pkg, tmp_path, runner)
    # Should NOT be the generic gate message
    assert "not authorized" not in str(exc_info.value).lower()
    # Should be EC-related rejection (any EC-specific error is fine)
    assert "ec" in str(exc_info.value).lower() or "campaign" in str(exc_info.value).lower() or "ledger" in str(exc_info.value).lower()


def test_journal_unchanged_when_gate_rejects(tmp_path):
    """No journal file should be created when gate rejects."""
    pkg = make_generic_package(tmp_path, gate="HOLD", submitted=False)
    runner = FakeRunner()
    try:
        call_submit(pkg, tmp_path, runner)
    except ValueError:
        pass
    journal_path = pkg / "submission_journal.json"
    assert not journal_path.exists(), "journal must not be created on gate rejection"


def test_ledger_unchanged_when_gate_rejects(tmp_path):
    """External ledger (attempts_ledger) must remain unchanged when gate rejects."""
    pkg = make_generic_package(tmp_path, gate="HOLD", submitted=False)
    ledger = [{"attempt_id": "test", "status": "PLANNED"}]
    original_ledger = json.dumps(ledger)
    runner = FakeRunner()
    try:
        call_submit(pkg, tmp_path, runner, ledger=ledger)
    except ValueError:
        pass
    assert json.dumps(ledger) == original_ledger, "ledger must not be modified on gate rejection"
