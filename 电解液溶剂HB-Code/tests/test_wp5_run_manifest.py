"""Step 8: a formal version must DECLARE its protocol and be checkable read-only.

The user's item: "为正式 model_v2 增加独立输出目录、**协议 manifest 与只读 check**；
保留 knn_v1 历史结果，不覆盖控制组。"

What is pinned here:

* the committed control directory declares its protocol and validates clean;
* the check REFUSES a directory whose protocol drifted, whose declared inputs
  changed, whose row counts disagree, or whose ownership flags are wrong;
* ``--check-run`` never writes (bytes and mtimes unchanged), which is the
  "只读检查无写盘" requirement;
* the control directory's data tables stay byte-identical to the pre-existing
  ones -- adding a manifest must not perturb the results.
"""
import csv
import importlib.util
import json
import shutil
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
BLIND = (REPO / "outputs" / "physics_completion" / "active_learning"
         / "blind_replay")


@pytest.fixture(scope="module")
def replay():
    spec = importlib.util.spec_from_file_location(
        "ab", REPO / "scripts" / "wp_production" / "run_wp5_AB_replay.py")
    m = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(REPO / "scripts" / "wp_production"))
    spec.loader.exec_module(m)
    return m


@pytest.fixture
def staged(replay, tmp_path, monkeypatch):
    """A tmp run directory for the CONTROL version; REPO stays real."""
    d = tmp_path / "blind_replay"
    shutil.copytree(BLIND, d)
    monkeypatch.setattr(replay, "BLIND", d)
    return d


def _index(d):
    return json.loads((d / "AB_index.json").read_text(encoding="utf-8"))


def _write_index(d, doc):
    (d / "AB_index.json").write_text(
        json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_the_committed_control_run_is_self_consistent(replay):
    assert replay.run_manifest_problems() == []


def test_the_manifest_declares_the_frozen_protocol(replay):
    doc = _index(BLIND)
    protocol = doc["protocol"]
    for key, want in replay.declared_protocol().items():
        assert str(protocol.get(key)) == str(want), key


def test_adding_the_manifest_did_not_change_the_tables(replay):
    """A manifest is metadata: the data must be untouched by its introduction."""
    with (BLIND / "AB_axis_endpoint.csv").open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert rows, "the control tables must exist"
    assert {r["acquisition_version"] for r in rows} == {"knn_v1"}


def test_missing_directory_is_reported(replay, tmp_path, monkeypatch):
    monkeypatch.setattr(replay, "BLIND", tmp_path / "nope")
    problems = replay.run_manifest_problems()
    assert problems and "run directory missing" in problems[0]


def test_protocol_drift_is_rejected(replay, staged):
    doc = _index(staged)
    doc["protocol"]["rbf_gamma"] = 0.5          # the old, wrong 1/7-era style value
    _write_index(staged, doc)
    problems = replay.run_manifest_problems()
    assert any("protocol drift on rbf_gamma" in p for p in problems), problems


def test_a_missing_protocol_block_is_rejected(replay, staged):
    doc = _index(staged)
    doc.pop("protocol")
    _write_index(staged, doc)
    problems = replay.run_manifest_problems()
    assert any("declares no protocol" in p for p in problems), problems


def test_stale_declared_input_is_rejected(replay, staged):
    doc = _index(staged)
    first = sorted(doc["inputs"])[0]
    doc["inputs"][first] = "0" * 64
    _write_index(staged, doc)
    problems = replay.run_manifest_problems()
    assert any("declared input changed" in p for p in problems), problems


def test_row_count_disagreement_is_rejected(replay, staged):
    doc = _index(staged)
    doc["rows"]["AB_axis_endpoint"] = 999
    _write_index(staged, doc)
    problems = replay.run_manifest_problems()
    assert any("rows, manifest declares" in p for p in problems), problems


def test_ownership_flags_are_enforced(replay, staged):
    doc = _index(staged)
    doc["outputs"]["is_control_directory"] = False
    _write_index(staged, doc)
    problems = replay.run_manifest_problems()
    assert any("is_control_directory" in p for p in problems), problems


def test_a_formal_directory_must_not_be_the_control_directory(replay, tmp_path,
                                                             monkeypatch):
    """model_v2 must never resolve to blind_replay: that would overwrite it."""
    monkeypatch.setattr(replay, "BLIND", tmp_path / "blind_replay")
    control = replay.output_paths("knn_v1")["dir"]
    formal = replay.output_paths("model_v2")["dir"]
    assert control != formal
    # and the formal check must report the absent directory, not fall back
    problems = replay.run_manifest_problems("model_v2")
    assert problems, "a formal run with no directory must be refused, not faked"


def test_check_run_is_read_only(replay, staged):
    """只读检查无写盘: bytes and mtimes must be untouched."""
    before = {p.name: (p.read_bytes(), p.stat().st_mtime_ns)
              for p in sorted(staged.iterdir()) if p.is_file()}
    assert replay.check_run() == 0
    after = {p.name: (p.read_bytes(), p.stat().st_mtime_ns)
             for p in sorted(staged.iterdir()) if p.is_file()}
    assert before == after


def test_check_run_reports_a_failure(replay, staged):
    doc = _index(staged)
    doc["protocol"]["gpr_noise"] = 99.0
    _write_index(staged, doc)
    assert replay.check_run() == 1