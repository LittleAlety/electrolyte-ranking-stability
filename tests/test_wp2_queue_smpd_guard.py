"""smpd 守卫：长跑里 smpd 中途死亡会让后续腿在几秒内全败，并白烧 MAX_ATTEMPTS。

2026-10-10 事故（5 条腿在 00:17 一起失败）的根因就是 smpd 失联。队列原来只在
``main()`` 里查一次 smpd，长跑期间不再复查；这里把「开跑前 / 每个作业开跑前 /
每 SMPD_RECHECK_POLLS 次轮询」三处复查与「拉不起来就不新开作业」的行为钉住。
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
QUEUE = REPO_ROOT / "scripts" / "wp_production" / "run_wp2_queue.py"


def _load():
    spec = importlib.util.spec_from_file_location("run_wp2_queue_under_test", QUEUE)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_recheck_cadence_covers_startup_and_periodic_polls():
    queue = _load()
    assert queue.SMPD_RECHECK_POLLS >= 2, "轮询节拍过密会把 PowerShell 调用变成瓶颈"
    assert queue.smpd_recheck_due(0) is True, "开跑前必须复查"
    assert queue.smpd_recheck_due(queue.SMPD_RECHECK_POLLS) is True
    assert queue.smpd_recheck_due(1) is False


def test_guard_returns_availability_and_only_reports_trouble(capsys):
    queue = _load()
    queue.ensure_smpd = lambda: "smpd alive"
    assert queue.guard_smpd("unit") is True
    assert capsys.readouterr().out == "", "smpd 正常时不应刷屏"

    queue.ensure_smpd = lambda: "smpd restarted"
    assert queue.guard_smpd("unit") is True, "成功拉起后应视为可用"
    assert "smpd restarted" in capsys.readouterr().out

    queue.ensure_smpd = lambda: "smpd NOT found at X"
    assert queue.guard_smpd("unit") is False, "连可执行文件都没有时应判为不可用"
    assert "smpd guard (unit)" in capsys.readouterr().out


class _FakeProc:
    pid = 4242

    def poll(self):
        return 0


def _drive_schedule(queue, monkeypatch, tmp_path, smpd_states, recheck_polls=None):
    """跑一遍 schedule(1)，把外部依赖全部替换掉；返回 (Popen 次数, ensure_smpd 次数)。"""
    calls = {"popen": 0, "ensure": 0}
    seen = {"inventory": 0}
    pending_states = list(smpd_states)

    def fake_inventory():
        seen["inventory"] += 1
        status = "pending" if seen["inventory"] == 1 else "computed"
        return [{"mol_id": "C01", "name": "DMC", "state": "LiM_plus",
                 "owner": "prod", "status": status}]

    def fake_ensure():
        calls["ensure"] += 1
        return pending_states.pop(0) if len(pending_states) > 1 else pending_states[0]

    def fake_popen(*args, **kwargs):
        calls["popen"] += 1
        return _FakeProc()

    monkeypatch.setattr(queue, "OUT", tmp_path)
    monkeypatch.setattr(queue, "inventory", fake_inventory)
    monkeypatch.setattr(queue, "leg_status", lambda name, state: "computed")
    monkeypatch.setattr(queue, "ensure_smpd", fake_ensure)
    monkeypatch.setattr(queue.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(queue.time, "sleep", lambda *_: None)
    if recheck_polls is not None:
        monkeypatch.setattr(queue, "SMPD_RECHECK_POLLS", recheck_polls)

    assert queue.schedule(1) == 0
    return calls


def test_healthy_smpd_launches_the_leg(monkeypatch, tmp_path):
    queue = _load()
    calls = _drive_schedule(queue, monkeypatch, tmp_path, ["smpd alive"])
    assert calls["popen"] == 1
    assert calls["ensure"] >= 1


def test_missing_smpd_holds_off_then_recovers(monkeypatch, tmp_path):
    queue = _load()
    # 前两轮复查拉不起来 -> 不新开作业；第三轮恢复 -> 正常开跑。
    calls = _drive_schedule(queue, monkeypatch, tmp_path,
                            ["smpd NOT found at X", "smpd NOT found at X", "smpd alive"])
    assert calls["popen"] == 1, "基础设施没就绪时不应启动 ORCA 作业"
    assert calls["ensure"] >= 3, "应持续复查直到 smpd 恢复"


def test_periodic_poll_rechecks_smpd(monkeypatch, tmp_path):
    queue = _load()
    calls = _drive_schedule(queue, monkeypatch, tmp_path, ["smpd alive"], recheck_polls=1)
    assert calls["ensure"] >= 2, "轮询到点时也要复查，而不是只在开跑前查一次"