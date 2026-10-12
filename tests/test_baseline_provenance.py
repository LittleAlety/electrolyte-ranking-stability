"""Contract tests for the immutable implementation-plan baseline manifest."""
from __future__ import annotations

import csv
import hashlib
import importlib.util
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "wp_production" / "build_compute_provenance.py"
MANIFEST = REPO / "outputs" / "physics_completion" / "provenance" / "baseline_artifact_manifest.csv"


def _module():
    spec = importlib.util.spec_from_file_location("baseline_provenance_under_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_manifest_hashes_commit_objects_not_mutable_worktree_bytes():
    module = _module()
    rows = module.baseline_manifest()
    assert rows and all(r["baseline_commit"] == module.BASELINE_COMMIT for r in rows)
    assert all(r["verification_status"] == "verified_from_git_object" for r in rows)
    target = next(r for r in rows if r["artifact_path"] == "FINAL_CONCLUSIONS.md")
    content = subprocess.run(
        ["git", "show", "%s:%s" % (module.BASELINE_COMMIT, target["artifact_path"])],
        cwd=str(REPO), stdout=subprocess.PIPE, check=True).stdout
    assert target["sha256"] == hashlib.sha256(content).hexdigest()
    assert int(target["bytes"]) == len(content)


def test_checked_in_manifest_has_explicit_scope_and_time_boundary():
    with MANIFEST.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows
    assert all(r["commit_time"] and r["time_boundary"] for r in rows)
    assert all(r["verification_status"] in {"verified_from_git_object", "unverifiable"}
               for r in rows)
    assert all((r["sha256"] and len(r["sha256"]) == 64)
               if r["verification_status"] == "verified_from_git_object"
               else not r["sha256"] for r in rows)
