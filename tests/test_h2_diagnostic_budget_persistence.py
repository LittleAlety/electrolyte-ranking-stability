"""End-to-end ledger persistence for h2_single_point_diagnostic_v1.

Tests that:
1. Batch 1 submission persists its reservation to the shared ledger on disk.
2. Batch 2 re-reads the ledger and sees batch 1's committed cost.
3. Cumulative (1.3333 + 1.3333) <= cap 2.6667 passes.
4. A hypothetical 9th element (+0.3333 CH) exceeds the cap and is rejected.
5. The test does NOT manually inject running records; it uses real persistence.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

MODULE = Path(__file__).resolve().parents[1] / "scripts/wp_production/submit_hpc_batch.py"
spec = importlib.util.spec_from_file_location("submit_batch_persist", MODULE)
submit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(submit)

REPO = Path(__file__).resolve().parents[1]
PKG = REPO / "work" / "hpc_dmc_adjacent_step_v1"


class FakeRunner:
    """Records all calls and simulates a successful submission with auto-incrementing job IDs."""
    def __init__(self, start_job_id=99001):
        self.calls = []
        self.next_job_id = start_job_id

    def __call__(self, argv):
        argv = [str(a) for a in argv]
        self.calls.append(argv)
        from types import SimpleNamespace
        action = argv[1] if len(argv) > 1 else ""
        if action == "doctor":
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        if action == "run":
            cmd = argv[2] if len(argv) > 2 else ""
            if cmd.startswith("mkdir"):
                return SimpleNamespace(returncode=0, stdout="", stderr="")
            if "squeue" in cmd:
                return SimpleNamespace(returncode=0, stdout="", stderr="")
            if cmd.startswith("rmdir"):
                return SimpleNamespace(returncode=0, stdout="", stderr="")
        if action == "submit":
            job_id = self.next_job_id
            self.next_job_id += 1
            return SimpleNamespace(returncode=0,
                                   stdout="Submitted batch job %d\n" % job_id,
                                   stderr="")
        raise AssertionError("unexpected bridge call: %r" % (argv,))


def _load_ledger(path):
    doc = json.loads(path.read_text(encoding="utf-8"))
    return doc.get("attempts", []), doc


def test_batch1_persists_batch2_sees_committed_then_ninth_rejected(tmp_path):
    """End-to-end: batch 1 persists, batch 2 reads from disk, 9th element rejected."""
    # Copy the real package into tmp_path so _load_package can find it
    import shutil
    pkg = tmp_path / "hpc_dmc_adjacent_step_v1"
    shutil.copytree(PKG, pkg)
    # The real package carries a REAL batch-1 submission journal (it was actually
    # submitted).  The fixture must start pre-submission, otherwise the duplicate-
    # submission guard correctly refuses -- that guard is not being weakened; the
    # repo's journal stays untouched and only the tmp copy is reset.
    (pkg / 'submission_journal.json').unlink(missing_ok=True)
    for stale in pkg.glob('*.submission.lock'):
        stale.unlink()  # tmp fixture: drop the real reservation marker too

    # Write an initially empty attempts ledger
    ledger_path = pkg / "attempts_ledger.json"
    ledger_path.write_text(json.dumps({"schema_version": 2, "attempts": []},
                                      ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")

    # Flip the gate to OPEN for the test (the gate itself is verified elsewhere)
    manifest_path = pkg / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["submission_gate"] = "OPEN"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                             encoding="utf-8")

    runner = FakeRunner(start_job_id=99001)

    # --- Batch 1 submission ---
    ledger_b1, doc_b1 = _load_ledger(ledger_path)
    result_b1 = submit.submit_batch(
        pkg, 1, "project/test/remote1",
        runner=runner, bridge=tmp_path / "hpc.ps1",
        attempts_ledger=ledger_b1,
        attempts_ledger_path=ledger_path,
        budget_cap_core_hours="2.6667"
    )
    assert result_b1["status"] == "submitted"
    assert result_b1["job_id"] == "99001"

    # Reload ledger from disk (simulates the second CLI invocation)
    ledger_b2, doc_b2 = _load_ledger(ledger_path)
    assert len(ledger_b2) == 4  # 4 elements x 4 cores x 5/60 h
    assert all(e["status"] == "pending" for e in ledger_b2)
    assert all(e["batch"] == 1 for e in ledger_b2)

    # --- Batch 2 submission ---
    result_b2 = submit.submit_batch(
        pkg, 2, "project/test/remote2",
        runner=runner, bridge=tmp_path / "hpc.ps1",
        attempts_ledger=ledger_b2,
        attempts_ledger_path=ledger_path,
        budget_cap_core_hours="2.6667"
    )
    assert result_b2["status"] == "submitted"
    assert result_b2["job_id"] == "99002"

    # Verify cumulative occupancy on disk
    ledger_b3, doc_b3 = _load_ledger(ledger_path)
    assert len(ledger_b3) == 8  # 4 + 4
    assert all(e["status"] == "pending" for e in ledger_b3)
    batches = {e["batch"] for e in ledger_b3}
    assert batches == {1, 2}

    # committed_core_hours should now include both batches
    from decimal import Decimal
    committed = submit.committed_core_hours(ledger_b3)
    # 8 elements x 4 cores x 5/60 h = 2.6666...
    assert committed >= Decimal("2.6660"), "committed too low: %s" % committed
    assert committed <= Decimal("2.6667"), "committed exceeded cap: %s" % committed

    # --- 9th element must be rejected ---
    with pytest.raises(ValueError, match="budget exceeded"):
        submit.budget_headroom(
            ledger_b3,
            cap="2.6667",
            cores=4,
            wall_hours=1/12.0,
            task_count=1
        )


def test_ledger_preserves_other_keys(tmp_path):
    """Persistence must not drop keys outside 'attempts'."""
    import shutil
    pkg = tmp_path / "hpc_dmc_adjacent_step_v1"
    shutil.copytree(PKG, pkg)
    # The real package carries a REAL batch-1 submission journal (it was actually
    # submitted).  The fixture must start pre-submission, otherwise the duplicate-
    # submission guard correctly refuses -- that guard is not being weakened; the
    # repo's journal stays untouched and only the tmp copy is reset.
    (pkg / 'submission_journal.json').unlink(missing_ok=True)
    for stale in pkg.glob('*.submission.lock'):
        stale.unlink()  # tmp fixture: drop the real reservation marker too

    ledger_path = pkg / "attempts_ledger.json"
    original_doc = {
        "schema_version": 2,
        "campaign_id": "four_state_recovery_20261023",
        "scope": "DMC adjacent-step differential",
        "attempts": []
    }
    ledger_path.write_text(json.dumps(original_doc, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")

    # Flip the gate to OPEN for the test
    manifest_path = pkg / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["submission_gate"] = "OPEN"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                             encoding="utf-8")

    runner = FakeRunner()
    ledger, _ = _load_ledger(ledger_path)
    submit.submit_batch(
        pkg, 1, "project/test/remote",
        runner=runner, bridge=tmp_path / "hpc.ps1",
        attempts_ledger=ledger,
        attempts_ledger_path=ledger_path,
        budget_cap_core_hours="2.6667"
    )

    persisted = json.loads(ledger_path.read_text(encoding="utf-8"))
    assert persisted["campaign_id"] == original_doc["campaign_id"]
    assert persisted["scope"] == original_doc["scope"]
    assert len(persisted["attempts"]) == 4  # one entry per element in batch 1
