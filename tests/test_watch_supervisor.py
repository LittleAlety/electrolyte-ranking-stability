"""监守的看护（watch_supervisor.ps1）：监守有意会退出，必须有人接住那个信号。

为什么单独一个测试文件：本阶段唯一的目标是「把四分子 20 条腿算完」，而这条链上唯一的
长跑进程就是监守。监守在连续无进展时会写 INCOMPLETE 并 exit 3（把「要不要再来一轮」
交给外部）——没有看护，这个信号就没人接，闭环会静默停在半路。这里钉三件事：

1. 判据（watch_decide）不会在「还有腿没算完、又没有活跃监守」时选择不管；
2. 看护不为了赶时间放宽用户的硬要求（只调 supervise_pending.ps1，不加 --max-jobs / --force）；
3. 看护脚本本身语法有效，且是有上限的常驻进程（不会无限期活着）。
"""

from __future__ import annotations

import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
POLICY = REPO_ROOT / "scripts" / "wp_production" / "supervisor_policy.py"
WATCHER = REPO_ROOT / "scripts" / "wp_production" / "watch_supervisor.ps1"


def _load():
    spec = importlib.util.spec_from_file_location("supervisor_policy_watch_under_test", POLICY)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_watch_decide_relaunches_while_legs_remain_and_nobody_is_running():
    module = _load()
    assert module.watch_decide(10, 20, False) == module.RELAUNCH
    assert module.watch_decide(0, 20, False) == module.RELAUNCH


def test_watch_decide_never_stacks_a_second_supervisor():
    module = _load()
    assert module.watch_decide(10, 20, True) == module.WAIT
    assert module.watch_decide(20, 20, True) == module.WAIT


def test_watch_decide_exits_only_when_the_legs_are_complete():
    module = _load()
    assert module.watch_decide(20, 20, False) == module.WATCH_EXIT
    assert module.watch_decide(19, 20, False) == module.RELAUNCH


def test_watch_decide_cli_matches_the_pure_function(capsys):
    module = _load()
    assert module.main(["--watch-decide", "--computed", "10", "--target", "20", "--active", "false"]) == 0
    assert capsys.readouterr().out.strip() == module.RELAUNCH
    assert module.main(["--watch-decide", "--computed", "10", "--target", "20", "--active", "true"]) == 0
    assert capsys.readouterr().out.strip() == module.WAIT
    assert module.main(["--watch-decide", "--computed", "20", "--active", "0"]) == 0
    assert capsys.readouterr().out.strip() == module.WATCH_EXIT


def _parse_errors():
    """用 PowerShell 自己的解析器检查看护脚本语法；没有 powershell 就跳过。"""
    if shutil.which("powershell") is None:
        return None
    command = ("$errs=$null;"
               "[void][System.Management.Automation.Language.Parser]::ParseFile('%s',"
               "[ref]$null,[ref]$errs); Write-Output $errs.Count" % WATCHER)
    done = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", command],
                          capture_output=True, text=True, errors="replace")
    assert done.returncode == 0, done.stderr
    return int(done.stdout.strip())


def test_watcher_script_is_syntactically_valid():
    errors = _parse_errors()
    if errors is None:
        return
    assert errors == 0


def test_watcher_never_raises_the_orca_concurrency_cap():
    text = WATCHER.read_text(encoding="utf-8-sig")
    assert "supervise_pending.ps1" in text, "看护只负责把监守拉起来"
    assert "run_wp2_queue.py" not in text, "看护不得自己碰队列，并发上限仍由监守守"
    assert "--max-jobs" not in text and "--force" not in text, \
        "看护不得放宽并发上限（用户硬要求：不要占满机器）"
    assert "supervisor_policy.py" in text and "--watch-decide" in text, \
        "判据必须走有单测的模块，不能埋回 .ps1 分支"
    assert "-WindowStyle Hidden" in text, "常驻看护必须是隐藏窗口"


def test_watcher_is_bounded_and_logs_where_it_stops():
    text = WATCHER.read_text(encoding="utf-8-sig")
    assert "MaxHours" in text and "$deadline" in text, "常驻进程必须有上限，不能无限期活着"
    assert "_supervisor_watch.log" in text
    assert "watch_supervisor exit" in text and "relaunch this script to continue" in text, \
        "到期退出必须写清楚「还有多少腿没算完、重新拉起即可继续」"