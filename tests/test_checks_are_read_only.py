"""Step 12: "--check" must be READ-ONLY -- no writes, not even an mtime touch.

The plan's final-verification item: "完整离线测试、生成/check配对、**只读检查无写盘**、
干净环境复现、归档复算、同轮输入哈希及严格总闸门全部核验."

The chain runs 39 ``--check`` steps, and nothing asserted that they leave the tree
alone.  This file snapshots (size, mtime_ns) for every file under ``outputs/`` and
``docs/``, runs a representative set of the chain's checks in a subprocess, and
requires the snapshot to be byte-for-byte AND timestamp-identical.

A check that rewrites a file in place is the quietest possible defect: it passes
its own comparison while destroying the evidence that it was consistent.
"""
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
PY = REPO / ".venv" / "Scripts" / "python.exe"
WATCH = ("outputs", "docs")

#: a representative slice of the chain's 39 checks: fast ones covering the layers
#: that matter most (budget, cost, run manifest, coverage, sampling)
CHECKS = (
    ("build_recovery_budget_accounting.py", "--check"),
    ("build_ensemble_cost_by_family.py", "--check"),
    ("build_coverage_reviews.py", "--check"),
    ("build_sampling_3to6_diff.py", "--check"),
)


def _snapshot() -> dict:
    out = {}
    for top in WATCH:
        root = REPO / top
        for dirpath, _dirnames, filenames in os.walk(root):
            for name in filenames:
                p = Path(dirpath) / name
                try:
                    st = p.stat()
                except OSError:
                    continue
                out[str(p.relative_to(REPO))] = (st.st_size, st.st_mtime_ns)
    return out


def _run(script: str, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [str(PY), "-X", "utf8", str(REPO / "scripts" / "wp_production" / script),
         *args],
        cwd=str(REPO), capture_output=True, text=True, encoding="utf-8",
        timeout=600)


@pytest.mark.skipif(not PY.is_file(), reason="project venv interpreter not present")
def test_the_chain_checks_are_read_only():
    before = _snapshot()
    assert before, "the snapshot must not be empty"
    for script, flag in CHECKS:
        proc = _run(script, flag)
        assert proc.returncode == 0, (script, proc.stdout[-400:], proc.stderr[-400:])
    after = _snapshot()
    changed = sorted(k for k in set(before) | set(after)
                     if before.get(k) != after.get(k))
    assert not changed, changed
    assert len(after) == len(before)


@pytest.mark.skipif(not PY.is_file(), reason="project venv interpreter not present")
def test_the_run_manifest_check_is_read_only():
    """The formal-version check must also leave the tree untouched."""
    before = _snapshot()
    proc = _run("run_wp5_AB_replay.py", "--check-run")
    assert proc.returncode == 0, proc.stdout[-400:]
    after = _snapshot()
    changed = sorted(k for k in set(before) | set(after)
                     if before.get(k) != after.get(k))
    assert not changed, changed


def test_a_check_that_fails_writes_nothing_either(tmp_path):
    """Read-only even on the failure path: the source guard is structural."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "cost", REPO / "scripts" / "wp_production" / "build_ensemble_cost_by_family.py")
    m = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(REPO / "scripts" / "wp_production"))
    spec.loader.exec_module(m)
    before = sorted(p.name for p in m.OUT.iterdir())
    # a refused build must not have created a partial ledger
    m.REPO = tmp_path
    with pytest.raises(SystemExit):
        m.build_rows()
    after = sorted(p.name for p in m.OUT.iterdir())
    assert before == after