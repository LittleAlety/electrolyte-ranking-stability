"""队列收尾（run_to_closure）：腿算完 ≠ 交付层更新，这一步把两者接上。

纪律是「20/20 全齐才折入」，所以这里钉住三件事：未齐时不跑收口链（退出码 3）、
齐了才调用 finalize_wp2.ps1、`--commit` 只在显式给出时透传给收口链。
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "wp_production" / "run_to_closure.py"


def _load():
    spec = importlib.util.spec_from_file_location("run_to_closure_under_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _rows(pending):
    """构造 inventory() 的返回：pending 里的 (name, state) 未 computed，其余 computed。"""
    rows = []
    for state, _owner in _load().queue.LEGS:
        for name in ("DMC", "EMC", "GBL", "SL"):
            status = "partial" if (name, state) in pending else "computed"
            rows.append({"mol_id": name, "name": name, "state": state,
                         "owner": "prod", "status": status})
    return rows


def test_pending_legs_reports_everything_not_computed(monkeypatch):
    module = _load()
    monkeypatch.setattr(module.queue, "inventory",
                        lambda: _rows({("DMC", "M_tzvpd"), ("SL", "LiM_plus")}))
    assert module.pending_legs() == [("DMC", "M_tzvpd"), ("SL", "LiM_plus")]


def test_missing_legs_do_not_run_the_chain(monkeypatch, capsys):
    module = _load()
    monkeypatch.setattr(module.queue, "inventory", lambda: _rows({("GBL", "LiM_2plus")}))
    called = []
    monkeypatch.setattr(module.subprocess, "run", lambda *a, **k: called.append(a))
    assert module.main(["--commit"]) == module.PENDING_EXIT
    assert called == [], "腿没齐就不应触碰收口链"
    assert "GBL|LiM_2plus" in capsys.readouterr().out


def test_check_passes_only_when_all_legs_are_computed(monkeypatch, capsys):
    module = _load()
    monkeypatch.setattr(module.queue, "inventory", lambda: _rows(set()))
    assert module.main(["--check"]) == 0
    assert "all 20 legs computed" in capsys.readouterr().out


def test_dry_run_prints_the_chain_without_running_it(monkeypatch, capsys):
    module = _load()
    monkeypatch.setattr(module.queue, "inventory", lambda: _rows(set()))
    called = []
    monkeypatch.setattr(module.subprocess, "run", lambda *a, **k: called.append(a))
    assert module.main(["--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "finalize_wp2.ps1" in out
    assert called == []


def test_commit_flag_is_the_only_thing_that_reaches_the_chain(monkeypatch):
    module = _load()
    monkeypatch.setattr(module.queue, "inventory", lambda: _rows(set()))
    seen = {}

    class _Done:
        returncode = 0

    def fake_run(command, **kwargs):
        seen["command"] = command
        return _Done()

    monkeypatch.setattr(module.subprocess, "run", fake_run)
    assert module.main([]) == 0
    assert "-Commit" not in seen["command"], "没有要求就不要提交"
    assert module.main(["--commit"]) == 0
    assert seen["command"][-1] == "-Commit"