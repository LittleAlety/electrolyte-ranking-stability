"""The submission gate is exercised with an injected runner; no HPC call is made."""
from __future__ import annotations

import importlib.util
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import threading
from types import SimpleNamespace

import pytest


MODULE = Path(__file__).resolve().parents[1] / "scripts/wp_production/submit_hpc_batch.py"
README = MODULE.parent / "README.md"
spec = importlib.util.spec_from_file_location("submit_hpc_batch", MODULE)
submit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(submit)


def package(tmp_path, count=3):
    root = tmp_path / "package"
    root.mkdir(parents=True)
    (root / "batch_1.sbatch").write_text("#!/bin/bash\n", encoding="utf-8")
    (root / "batch_1.txt").write_text("".join("tasks/X%d/M\n" % i for i in range(count)),
                                       encoding="utf-8")
    (root / "manifest.json").write_text(json.dumps({
        "schema_version": 2, "batches": [{"batch": 1, "count": count}], "legs": []}),
        encoding="utf-8")
    return root


class Runner:
    def __init__(self, jobs, submitted="作业已提交，JobID = 987654"):
        self.jobs = jobs
        self.submitted = submitted
        self.calls = []
        self.remote_locked = False

    def __call__(self, argv):
        self.calls.append([str(value) for value in argv])
        if "doctor" in argv:
            return SimpleNamespace(returncode=0, stdout="doctor ok", stderr="")
        if "run" in argv:
            command = argv[argv.index("run") + 1]
            if command.startswith("mkdir ~/project/electrolyte_wp2/.wp2_submit.lock"):
                if self.remote_locked:
                    return SimpleNamespace(returncode=1, stdout="", stderr="File exists")
                self.remote_locked = True
                return SimpleNamespace(returncode=0, stdout="", stderr="")
            if command.startswith("rmdir ~/project/electrolyte_wp2/.wp2_submit.lock"):
                self.remote_locked = False
                return SimpleNamespace(returncode=0, stdout="", stderr="")
            if command.startswith("squeue "):
                return SimpleNamespace(returncode=0, stdout=self.jobs, stderr="")
            raise AssertionError(command)
        if "submit" in argv:
            return SimpleNamespace(returncode=0, stdout=self.submitted, stderr="")
        raise AssertionError(argv)


def test_squeue_array_ranges_count_as_individual_jobs():
    assert submit.count_squeue_jobs("367_[0-3]\n400_1\n401\n") == 6
    assert submit.count_squeue_jobs("367_[0-8%3]\n") == 9
    with pytest.raises(ValueError):
        submit.count_squeue_jobs("not a job id\n")


def test_submission_refuses_when_batch_would_exceed_twenty(tmp_path):
    root = package(tmp_path, count=3)
    runner = Runner("".join("%d\n" % i for i in range(100, 118)))
    with pytest.raises(ValueError, match="20|headroom"):
        submit.submit_batch(root, 1, "~/project/pkg", runner=runner,
                            bridge=Path("E:/software/hpc/hpc.ps1"))
    assert runner.calls[0][1] == "doctor"
    assert len(runner.calls) == 4
    assert not (root / "submission_journal.json").exists()


def test_success_records_job_id_and_refuses_duplicate(tmp_path):
    root = package(tmp_path, count=3)
    runner = Runner("100\n101_0\n")
    result = submit.submit_batch(root, 1, "~/project/pkg", runner=runner,
                                 bridge=Path("E:/software/hpc/hpc.ps1"))
    assert result["job_id"] == "987654"
    journal = json.loads((root / "submission_journal.json").read_text(encoding="utf-8"))
    assert journal["submissions"][0]["job_id"] == "987654"
    assert journal["submissions"][0]["observed_active_pending"] == 2
    assert journal["submissions"][0]["batch_count"] == 3
    assert runner.calls[0][1] == "doctor"
    assert all("ssh" not in " ".join(call).lower() and "scp" not in " ".join(call).lower()
               for call in runner.calls)
    assert any("hpc.ps1" in call[0] and "submit" in call for call in runner.calls)

    calls = len(runner.calls)
    with pytest.raises(ValueError, match="already submitted"):
        submit.submit_batch(root, 1, "~/project/pkg", runner=runner,
                            bridge=Path("E:/software/hpc/hpc.ps1"))
    assert len(runner.calls) == calls


def test_exclusive_reservation_prevents_concurrent_or_crash_duplicate(tmp_path):
    root = package(tmp_path, count=1)
    (root / ".batch_1.submission.lock").write_text("prior reservation\n", encoding="utf-8")
    runner = Runner("")
    with pytest.raises(ValueError, match="already attempted|reservation"):
        submit.submit_batch(root, 1, "~/project/pkg", runner=runner,
                            bridge=Path("E:/software/hpc/hpc.ps1"))
    assert runner.calls == []


def test_submit_failure_is_journaled_and_never_retried_implicitly(tmp_path):
    root = package(tmp_path, count=1)

    def runner(argv):
        if "doctor" in argv:
            return SimpleNamespace(returncode=0, stdout="doctor ok", stderr="")
        if "run" in argv:
            command = argv[argv.index("run") + 1]
            if command.startswith(("mkdir ", "rmdir ", "squeue ")):
                return SimpleNamespace(returncode=0, stdout="", stderr="")
            raise AssertionError(command)
        return SimpleNamespace(returncode=7, stdout="", stderr="bridge failed")

    with pytest.raises(RuntimeError, match="bridge failed"):
        submit.submit_batch(root, 1, "~/project/pkg", runner=runner,
                            bridge=Path("E:/software/hpc/hpc.ps1"))
    journal = json.loads((root / "submission_journal.json").read_text(encoding="utf-8"))
    assert journal["submissions"][0]["status"] == "submit_failed"
    assert "scientific" not in json.dumps(journal).lower()
    with pytest.raises(ValueError, match="already attempted"):
        submit.submit_batch(root, 1, "~/project/pkg", runner=runner,
                            bridge=Path("E:/software/hpc/hpc.ps1"))


def test_readme_requires_capacity_gated_helper_and_explicit_attempt_import():
    text = README.read_text(encoding="utf-8")
    assert "submit_hpc_batch.py" in text
    assert "不得直接调用 `hpc submit`" in text
    assert "attempts/<attempt-id>" in text
    assert "运行中 + 排队中 ≤20" in text
    assert ".wp2_submit.lock" in text
    assert "--collect-sacct" in text
    assert "自动技术重试" in text


def test_account_wide_remote_lock_closes_cross_package_22_task_race(tmp_path):
    first = package(tmp_path / "one", count=11)
    second = package(tmp_path / "two", count=11)

    class ConcurrentBridge:
        def __init__(self):
            self.guard = threading.Lock()
            self.doctor_barrier = threading.Barrier(2)
            self.second_lock_attempt = threading.Event()
            self.remote_locked = False
            self.squeue_reads = 0
            self.submits = 0
            self.calls = []

        def __call__(self, argv):
            argv = [str(value) for value in argv]
            with self.guard:
                self.calls.append(argv)
            if "doctor" in argv:
                self.doctor_barrier.wait(timeout=5)
                return SimpleNamespace(returncode=0, stdout="doctor ok", stderr="")
            if "run" in argv:
                command = argv[argv.index("run") + 1]
                if command.startswith("mkdir ~/project/electrolyte_wp2/.wp2_submit.lock"):
                    with self.guard:
                        if self.remote_locked:
                            self.second_lock_attempt.set()
                            return SimpleNamespace(returncode=1, stdout="",
                                                   stderr="File exists")
                        self.remote_locked = True
                    return SimpleNamespace(returncode=0, stdout="", stderr="")
                if command.startswith("rmdir ~/project/electrolyte_wp2/.wp2_submit.lock"):
                    with self.guard:
                        assert self.remote_locked
                        self.remote_locked = False
                    return SimpleNamespace(returncode=0, stdout="", stderr="")
                if command.startswith("squeue "):
                    with self.guard:
                        self.squeue_reads += 1
                    return SimpleNamespace(returncode=0, stdout="", stderr="")
                raise AssertionError(command)
            if "submit" in argv:
                with self.guard:
                    self.submits += 1
                assert self.second_lock_attempt.wait(timeout=5)
                return SimpleNamespace(returncode=0, stdout="作业已提交，JobID = 987654", stderr="")
            raise AssertionError(argv)

    runner = ConcurrentBridge()
    bridge = Path("E:/software/hpc/hpc.ps1")
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(submit.submit_batch, root, 1, "~/project/pkg",
                               runner=runner, bridge=bridge) for root in (first, second)]
        outcomes = []
        for future in futures:
            try:
                outcomes.append(("ok", future.result(timeout=10)))
            except RuntimeError as exc:
                outcomes.append(("refused", str(exc)))
    assert [kind for kind, _ in outcomes].count("ok") == 1
    assert [kind for kind, _ in outcomes].count("refused") == 1
    assert runner.submits == 1
    assert runner.squeue_reads == 1
    assert runner.remote_locked is False


def test_collect_sacct_uses_bridge_and_writes_immutable_terminal_evidence(tmp_path):
    attempt = tmp_path / "attempts/123_4_999"
    attempt.mkdir(parents=True)
    (attempt / "scheduler_state.request").write_text("""slurm_array_job_id=123
slurm_array_task_id=4
slurm_job_id=999
required_for_automatic_technical_retry=true
""", encoding="utf-8")
    calls = []

    def runner(argv):
        argv = [str(value) for value in argv]
        calls.append(argv)
        if "doctor" in argv:
            return SimpleNamespace(returncode=0, stdout="doctor ok", stderr="")
        assert "run" in argv and "sacct -n -X -j 999" in argv[-1]
        return SimpleNamespace(returncode=0, stdout="999|COMPLETED|0:0\n999.batch|COMPLETED|0:0\n",
                               stderr="")

    result = submit.collect_sacct(attempt, runner=runner,
                                  bridge=Path("E:/software/hpc/hpc.ps1"))
    assert result["state"] == "COMPLETED" and result["exit_code"] == "0:0"
    evidence = (attempt / "sacct.terminal").read_text(encoding="utf-8")
    assert "source=sacct\n" in evidence and "slurm_array_task_id=4\n" in evidence
    assert calls[0][1] == "doctor"
    assert all("ssh" not in " ".join(call).lower() for call in calls)
    with pytest.raises(ValueError, match="already exists"):
        submit.collect_sacct(attempt, runner=runner,
                             bridge=Path("E:/software/hpc/hpc.ps1"))
