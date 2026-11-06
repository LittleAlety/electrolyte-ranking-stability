"""Entry-level tests: the EC contract is enforced inside the REAL submit path.

Each negative case asserts that the fake runner recorded **zero** calls, i.e. the
request was refused before doctor, before the remote lock and before submission.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

MODULE = Path(__file__).resolve().parents[1] / "scripts/wp_production/submit_hpc_batch.py"
spec = importlib.util.spec_from_file_location("submit_hpc_batch_ec_entry", MODULE)
submit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(submit)

GEOM = "4\nEC|LiM_2plus\nC 0.000000000 0.000000000 0.000000000\n" \
       "O 1.400000000 0.000000000 0.000000000\nC 2.600000000 0.200000000 0.000000000\n" \
       "Li 0.000000000 1.900000000 0.000000000\n"


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class FakeRunner:
    def __init__(self, submit_output="Submitted batch job 777", submit_rc=0):
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


def make_package(tmp_path, *, profile="orca_production_4h_v1", candidate="ec_v2_p4",
                 reserved=16, geom=GEOM, active_candidate=None, manifest_extra=None,
                 gate="OPEN", name="hpc_ec_recovery_v2_p4_20261029",
                 submitted=False):
    pkg = tmp_path / name
    task = pkg / "tasks" / "EC__LiM_2plus" / candidate
    task.mkdir(parents=True)
    (task / "geom.xyz").write_text(geom, encoding="utf-8", newline="\n")
    cand = {
        "candidate_id": candidate, "leaf": candidate, "state_key": "EC|LiM_2plus",
        "charge": 2, "multiplicity": 2, "spin": 1,
        "geometry_sha256": sha(geom),
    }
    (task / "candidate.json").write_text(json.dumps(cand), encoding="utf-8")
    (task / "job.inp").write_text(
        "! wB97X-D4 def2-TZVPD Opt AnFreq SMD(acetonitrile)\n%pal nprocs 4 end\n"
        "* xyzfile 2 2 geom.xyz\n", encoding="utf-8", newline="\n")
    (task / "import_level.txt").write_text("recovery_v1_start\n", encoding="utf-8")
    (pkg / "batch_1.sbatch").write_text("#!/bin/bash\n", encoding="utf-8")
    (pkg / "batch_1.txt").write_text("tasks/EC__LiM_2plus/%s\n" % candidate,
                                     encoding="utf-8")
    (pkg / "attempts_ledger.json").write_text(
        json.dumps({"schema_version": 2, "attempts": [
            {"attempt_id": "ec_v2_recovery_p4", "status": "PLANNED"}]}),
        encoding="utf-8")
    manifest = {
        "schema_version": "2.0",
        "package": pkg.name,
        "campaign": "four_state_recovery_20261023",
        "resource_profile": profile,
        "cores_per_task": 4,
        "wall_hours_per_task": 4,
        "task_count": 1,
        "reserved_core_hours": reserved,
        "active_candidate": candidate if active_candidate is None else active_candidate,
        "batches": [{"batch": 1, "count": 1}],
        "submission_gate": gate,
        "submitted": submitted,
    }
    if manifest_extra:
        manifest.update(manifest_extra)
    (pkg / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return pkg


def write_campaign(tmp_path, entries):
    path = tmp_path / "ec_recovery_v2_campaign" / "campaign_ledger.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"schema_version": 1,
                                "campaign_id": "four_state_recovery_20261023",
                                "attempts": entries}), encoding="utf-8")
    return path


def entry(candidate="ec_v2_p4", *, submitted=True, terminal=False, accepted=None,
          evidence_complete=None, settled=0.0, geometry_sha=None):
    record = {"candidate": candidate, "submitted": submitted, "terminal": terminal,
              "settled_core_hours": settled}
    if accepted is not None:
        record["accepted"] = accepted
    if evidence_complete is not None:
        record["evidence_complete"] = evidence_complete
    if geometry_sha is not None:
        record["geometry_sha256"] = geometry_sha
    return record


def call_submit(pkg, tmp_path, runner, ledger=None):
    return submit.submit_batch(
        pkg, 1, "project/electrolyte_wp2/hpc_ec_recovery_v2_p4_20261029",
        runner=runner, bridge=tmp_path / "hpc.ps1",
        attempts_ledger=ledger if ledger is not None else [{"status": "planned"}])


def expect_refused(pkg, tmp_path, runner, match, ledger=None):
    with pytest.raises(ValueError, match=match):
        call_submit(pkg, tmp_path, runner, ledger)
    assert runner.calls == [], "refusal must happen before any bridge call: %r" % runner.calls


def test_valid_p4_reaches_the_fake_submitter(tmp_path):
    pkg = make_package(tmp_path)
    runner = FakeRunner()
    result = call_submit(pkg, tmp_path, runner)
    assert result["status"] == "submitted" and result["job_id"] == "777"
    assert any("submit" in c for c in runner.calls)
    ledger = json.loads((tmp_path / "ec_recovery_v2_campaign" / "campaign_ledger.json")
                        .read_text(encoding="utf-8"))
    row = ledger["attempts"][-1]
    assert row["candidate"] == "ec_v2_p4" and row["submitted"] is True
    assert row["terminal"] is False and row["accepted"] is None


def test_p7_before_p4_is_refused_before_any_bridge_call(tmp_path):
    pkg = make_package(tmp_path, candidate="ec_v2_p7", reserved=16)
    runner = FakeRunner()
    expect_refused(pkg, tmp_path, runner, "next campaign step")


def test_p7_after_accepted_p4_is_refused(tmp_path):
    pkg = make_package(tmp_path, candidate="ec_v2_p7")
    write_campaign(tmp_path, [entry(accepted=True, terminal=True, evidence_complete=True)])
    runner = FakeRunner()
    expect_refused(pkg, tmp_path, runner, "next campaign step")


def test_p7_when_p4_result_is_unknown_is_refused(tmp_path):
    pkg = make_package(tmp_path, candidate="ec_v2_p7")
    write_campaign(tmp_path, [entry(terminal=True, accepted=None)])
    runner = FakeRunner()
    expect_refused(pkg, tmp_path, runner, "next campaign step")


def test_p7_when_accepted_field_is_missing_is_refused(tmp_path):
    pkg = make_package(tmp_path, candidate="ec_v2_p7")
    write_campaign(tmp_path, [entry(terminal=True)])
    runner = FakeRunner()
    expect_refused(pkg, tmp_path, runner, "next campaign step")


def test_p7_when_evidence_is_incomplete_is_refused(tmp_path):
    pkg = make_package(tmp_path, candidate="ec_v2_p7")
    write_campaign(tmp_path, [entry(terminal=True, accepted=False, evidence_complete=False)])
    runner = FakeRunner()
    expect_refused(pkg, tmp_path, runner, "next campaign step")


def test_third_leg_is_refused(tmp_path):
    pkg = make_package(tmp_path, candidate="ec_v2_p7")
    write_campaign(tmp_path, [
        entry("ec_v2_p4", terminal=True, accepted=False, evidence_complete=True,
              settled=16.0),
        entry("ec_v2_p7", terminal=True, accepted=False, evidence_complete=True,
              settled=16.0),
    ])
    runner = FakeRunner()
    expect_refused(pkg, tmp_path, runner, "next campaign step")


def test_over_budget_p4_after_settled_spend_is_refused(tmp_path):
    pkg = make_package(tmp_path, candidate="ec_v2_p7")
    write_campaign(tmp_path, [entry(terminal=True, accepted=False, evidence_complete=True,
                                    settled=20.0)])
    runner = FakeRunner()
    expect_refused(pkg, tmp_path, runner, "budget exceeded")


def test_low_reported_reservation_is_refused(tmp_path):
    pkg = make_package(tmp_path, reserved=8)
    runner = FakeRunner()
    expect_refused(pkg, tmp_path, runner, "low-reported reservation")


def test_missing_ledger_is_refused(tmp_path):
    pkg = make_package(tmp_path)
    runner = FakeRunner()
    with pytest.raises(ValueError, match="requires an attempts ledger"):
        submit.submit_batch(pkg, 1, "remote/dir", runner=runner,
                            bridge=tmp_path / "hpc.ps1", attempts_ledger=None)
    assert runner.calls == []


def test_second_element_in_flight_is_refused(tmp_path):
    pkg = make_package(tmp_path)
    write_campaign(tmp_path, [entry(submitted=True, terminal=False)])
    runner = FakeRunner()
    expect_refused(pkg, tmp_path, runner, "next campaign step")


def test_swapped_input_geometry_is_refused(tmp_path):
    pkg = make_package(tmp_path)
    geom = pkg / "tasks" / "EC__LiM_2plus" / "ec_v2_p4" / "geom.xyz"
    geom.write_text(GEOM.replace("Li 0.000000000 1.900000000 0.000000000",
                                 "Li 0.000000000 9.900000000 0.000000000"),
                    encoding="utf-8")
    runner = FakeRunner()
    expect_refused(pkg, tmp_path, runner, "geometry hash mismatch")


def test_swapped_candidate_identity_is_refused(tmp_path):
    pkg = make_package(tmp_path, candidate="ec_v2_p4", active_candidate="ec_v2_p7")
    runner = FakeRunner()
    expect_refused(pkg, tmp_path, runner, "active_candidate disagrees")


def test_campaign_geometry_mismatch_is_refused(tmp_path):
    pkg = make_package(tmp_path)
    write_campaign(tmp_path, [entry("ec_v2_p4", submitted=False, terminal=True,
                                    accepted=False, evidence_complete=True,
                                    geometry_sha="deadbeef")])
    runner = FakeRunner()
    expect_refused(pkg, tmp_path, runner, "geometry differs from the campaign record")


def test_historical_profile_still_submits_and_gets_no_campaign_ledger(tmp_path):
    pkg = make_package(tmp_path, profile="orca_production_v1", reserved=16,
                        name="hpc_production_ensemble_r1_999")
    runner = FakeRunner()
    result = submit.submit_batch(pkg, 1, "remote/dir", runner=runner,
                                 bridge=tmp_path / "hpc.ps1", attempts_ledger=None)
    assert result["status"] == "submitted"
    assert not (tmp_path / "ec_recovery_v2_campaign").exists()


def test_refusal_leaves_no_journal_and_no_campaign_entry(tmp_path):
    pkg = make_package(tmp_path)
    write_campaign(tmp_path, [entry(terminal=True)])
    runner = FakeRunner()
    expect_refused(pkg, tmp_path, runner, "next campaign step")
    assert not (pkg / "submission_journal.json").exists()
    ledger = json.loads((tmp_path / "ec_recovery_v2_campaign" / "campaign_ledger.json")
                        .read_text(encoding="utf-8"))
    assert len(ledger["attempts"]) == 1  # unchanged


def test_hold_package_is_refused_at_the_entry(tmp_path):
    pkg = make_package(tmp_path, gate="HOLD")
    runner = FakeRunner()
    expect_refused(pkg, tmp_path, runner, "is HOLD")


def test_wrong_profile_cannot_bypass_the_ec_contract(tmp_path):
    pkg = make_package(tmp_path, profile="orca_production_v1")
    runner = FakeRunner()
    expect_refused(pkg, tmp_path, runner, "must use profile")


def test_manifest_already_marked_submitted_is_refused(tmp_path):
    pkg = make_package(tmp_path, submitted=True)
    runner = FakeRunner()
    expect_refused(pkg, tmp_path, runner, "submitted=false")


def test_missing_campaign_id_is_refused(tmp_path):
    pkg = make_package(tmp_path, manifest_extra={"campaign": None})
    runner = FakeRunner()
    expect_refused(pkg, tmp_path, runner, "must declare its campaign id")


def test_under_reported_job_level_reservation_is_refused(tmp_path):
    pkg = make_package(tmp_path, manifest_extra={"first_batch_reserved_core_hours": 8})
    runner = FakeRunner()
    expect_refused(pkg, tmp_path, runner, "under-reports")
