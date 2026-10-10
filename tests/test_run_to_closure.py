"""队列收尾（run_to_closure）：腿算完 ≠ 交付层更新，这一步把两者接上。

纪律是方案的「不合格状态明确记录，不补数、不替换结构」，所以这里钉住：
未齐的腿**照样折入但必须显式列出**（否则某条腿反复失败就会让交付层永远停在旧数），
`--require-complete` 才拒绝折入，`--commit` 只在显式给出时透传给收口链。
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


def _no_chain(monkeypatch):
    module = _load()
    called = []
    monkeypatch.setattr(module.subprocess, "run", lambda *a, **k: called.append(a))
    return module, called


def test_pending_legs_reports_everything_not_computed(monkeypatch):
    module = _load()
    monkeypatch.setattr(module.queue, "inventory",
                        lambda: _rows({("DMC", "M_tzvpd"), ("SL", "LiM_plus")}))
    assert module.pending_legs() == [("DMC", "M_tzvpd"), ("SL", "LiM_plus")]


def test_check_reports_pending_and_passes_when_complete(monkeypatch, capsys):
    module = _load()
    monkeypatch.setattr(module.queue, "inventory", lambda: _rows({("GBL", "LiM_2plus")}))
    assert module.main(["--check"]) == module.PENDING_EXIT
    assert "GBL|LiM_2plus" in capsys.readouterr().out

    monkeypatch.setattr(module.queue, "inventory", lambda: _rows(set()))
    assert module.main(["--check"]) == 0
    assert "all 20 legs computed" in capsys.readouterr().out


def test_require_complete_refuses_to_fold(monkeypatch, capsys):
    module = _load()
    monkeypatch.setattr(module.queue, "inventory", lambda: _rows({("GBL", "LiM_2plus")}))
    called = []
    monkeypatch.setattr(module.subprocess, "run", lambda *a, **k: called.append(a))
    assert module.main(["--require-complete", "--commit"]) == module.PENDING_EXIT
    assert called == [], "--require-complete 下腿没齐就不应触碰收口链"
    assert "GBL|LiM_2plus" in capsys.readouterr().out


def test_partial_legs_still_fold_and_are_flagged(monkeypatch, capsys):
    """硬门禁的失败模式：一条腿反复失败就让交付层永远停在旧数。未齐也要折、但要写清。"""
    module, called = _no_chain(monkeypatch)
    monkeypatch.setattr(module.queue, "inventory",
                        lambda: _rows({("SL", "LiM_2plus"), ("EMC", "M_tzvpd")}))
    assert module.main(["--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "部分" in out and "SL|LiM_2plus" in out and "EMC|M_tzvpd" in out
    assert "finalize_wp2.ps1" in out
    assert called == [], "--dry-run 不应执行收口链"


def _label(command):
    joined = " ".join(command)
    for token in ("build_pair_recheck_plan.py", "run_pair_recheck.py",
                  "emit_pair_recheck.py", "finalize_wp2.ps1"):
        if token in joined:
            return token
    return joined


def _recorder(monkeypatch, code_of=None):
    """记录每一步标签，并按 code_of(label) 返回退出码（默认 0）。"""
    module = _load()
    monkeypatch.setattr(module.queue, "inventory", lambda: _rows(set()))
    seen = []

    class _Done:
        def __init__(self, rc):
            self.returncode = rc

    def fake_run(command, **kwargs):
        label = _label(command)
        seen.append(label)
        return _Done(code_of(label) if code_of else 0)

    monkeypatch.setattr(module.subprocess, "run", fake_run)
    return module, seen


def test_recheck_chain_runs_before_the_finalize_chain(monkeypatch):
    """腿一落地 ready 行就变多：必须先补跑第二泛函复核，再把交付层折进去。"""
    module, seen = _recorder(monkeypatch)
    assert module.main([]) == 0
    assert seen == ["build_pair_recheck_plan.py", "run_pair_recheck.py",
                    "emit_pair_recheck.py", "finalize_wp2.ps1"], seen


def test_plan_generator_exit_one_alone_does_not_block_the_fold(monkeypatch):
    """计划生成器在「还有 ready 行没结果」时按设计返回 1，它只是把缺口说清楚，不是失败。"""
    module, seen = _recorder(monkeypatch,
                             code_of=lambda label: 1 if label == "build_pair_recheck_plan.py" else 0)
    assert module.main([]) == 0
    assert seen[-1] == "finalize_wp2.ps1"


def test_failed_recheck_refuses_to_fold(monkeypatch, capsys):
    """复核没跑完就不折入：否则收口链的「结果表恰好覆盖 ready 行」验收必失败。"""
    module, seen = _recorder(monkeypatch,
                             code_of=lambda label: 7 if label == "run_pair_recheck.py" else 0)
    assert module.main([]) == 7
    assert "finalize_wp2.ps1" not in seen, "复核没完成时不应触碰收口链"
    assert "靶向复核未完成" in capsys.readouterr().out


def test_skip_recheck_rebuilds_only(monkeypatch):
    module, seen = _recorder(monkeypatch)
    assert module.main(["--skip-recheck"]) == 0
    assert seen == ["finalize_wp2.ps1"], seen


def test_dry_run_does_not_run_the_recheck(monkeypatch):
    module, called = _no_chain(monkeypatch)
    monkeypatch.setattr(module.queue, "inventory", lambda: _rows(set()))
    assert module.main(["--dry-run"]) == 0
    assert called == [], "--dry-run 不应触碰复核或收口链"


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