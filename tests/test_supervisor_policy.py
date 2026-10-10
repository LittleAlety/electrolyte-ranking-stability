"""无人值守链的收敛判据（supervisor_policy）+ 监守脚本本身。

本阶段唯一的目标是「把四分子 20 条腿算完」，所以这里钉两件事：
1. 判据不能把「还在推进」误判成「该放弃」——旧版固定跑 N 轮就退出、删锁、不再有人拉起，
   一轮里撞上 smpd 刚死的窗口，整条链就静默停在半路；
2. 监守不能为了赶时间偷偷放宽用户的硬要求（全机最多 2 个 ORCA 作业）。
"""

from __future__ import annotations

import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "wp_production" / "supervisor_policy.py"
SUPERVISOR = REPO_ROOT / "scripts" / "wp_production" / "supervise_pending.ps1"


def _load():
    spec = importlib.util.spec_from_file_location("supervisor_policy_under_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_counting_uses_the_queue_inventory_vocabulary():
    module = _load()
    rows = [{"status": "computed"}, {"status": "failed"}, {"status": "partial"},
            {"status": "missing"}, {"status": "computed"}]
    assert module.computed_count(rows) == 2
    assert module.computed_count([]) == 0


def test_progress_resets_the_stall_counter():
    module = _load()
    # before=10 -> after=12：涨了，就该清零 stalled 并继续，不被之前的 2 次无进展拖累
    assert module.decide(10, 12, 20, 1, 2, 6, 3) == (module.CONTINUE, 0)
    # 连续无进展才累加
    assert module.decide(12, 12, 20, 2, 0, 6, 3) == (module.CONTINUE, 1)
    assert module.decide(12, 12, 20, 3, 1, 6, 3) == (module.CONTINUE, 2)
    assert module.decide(12, 12, 20, 4, 2, 6, 3) == (module.STOP_STALLED, 3)


def test_complete_target_is_always_done():
    module = _load()
    assert module.decide(19, 20, 20, 1, 0, 6, 3) == (module.DONE, 0)
    # 已经全齐时即使 stalled 很多也不能判成停：先判 DONE
    assert module.decide(20, 20, 20, 5, 99, 6, 3) == (module.DONE, 99)


def test_round_cap_only_backstops_and_never_ends_a_productive_run_early():
    module = _load()
    # 有进展但在轮数上限：报 stop_round_cap（而不是停摆），调用方据此提示「重新拉起即可继续」
    assert module.decide(18, 19, 20, 6, 0, 6, 3) == (module.STOP_ROUND_CAP, 0)
    assert module.INCOMPLETE_EXIT == 3


def _parse_errors():
    """用 PowerShell 自己的解析器检查监守脚本语法；没有 powershell 就跳过。"""
    if shutil.which("powershell") is None:
        return None
    command = ("$errs=$null;"
               "[void][System.Management.Automation.Language.Parser]::ParseFile('%s',"
               "[ref]$null,[ref]$errs); Write-Output $errs.Count" % SUPERVISOR)
    done = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", command],
                          capture_output=True, text=True, errors="replace")
    assert done.returncode == 0, done.stderr
    return int(done.stdout.strip())


def test_supervisor_script_is_syntactically_valid():
    errors = _parse_errors()
    if errors is None:
        return
    assert errors == 0


def test_supervisor_waits_for_drivers_inside_every_round():
    text = SUPERVISOR.read_text(encoding="utf-8-sig")
    loop = text.index("while ($round -lt $MaxRounds)")
    assert text.index("Wait-ForDrivers", loop) > loop, \
        "每轮开跑前都要重新等驱动退出，否则残留的旧驱动会让队列拒绝启动、被误判成无进展"
    assert "for ($round = 1; $round -le 3" not in text, "旧的固定轮数循环必须已被移除"


def test_supervisor_never_raises_the_orca_concurrency_cap():
    text = SUPERVISOR.read_text(encoding="utf-8-sig")
    assert "run_wp2_queue.py --run" in text
    assert "--max-jobs" not in text, "监守不得放宽并发上限（用户硬要求：不要占满机器）"
    assert "--force" not in text, "监守不得绕过「已有作业在跑」的保护"
    assert "_supervisor.lock" in text, "单实例锁必须在，否则两个监守会把并发叠成 4 个"


def test_supervisor_uses_the_tested_policy_and_reports_incomplete():
    text = SUPERVISOR.read_text(encoding="utf-8-sig")
    assert "supervisor_policy.py" in text, "收敛判据必须走有单测的模块，不能埋回 .ps1 分支"
    assert "--decide" in text and "--computed-count" in text
    assert "run_to_closure.py --commit" in text
    assert "INCOMPLETE" in text and "exit 3" in text, "没算完必须以非零退出并写清楚，好让调用方重新拉起"
