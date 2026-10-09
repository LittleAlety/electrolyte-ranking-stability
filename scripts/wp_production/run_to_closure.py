# -*- coding: utf-8 -*-
"""队列收尾：队列停止后，把已 computed 的腿折进交付层（一键收口链）。

为什么需要这一步：无人值守链只到 `run_wp2_queue.py --run` 为止，而队列只负责**把腿算完**。
「腿算完」不等于「交付层更新」：production_ledger / 四分子闭环表 / 四分子标签 /
week37-week44 镜像都要靠 `finalize_wp2.ps1` 折进去。缺了这一步，机器算完后会停在一个
「原始结果已在、交付层还是旧数」的中间态。

折入口径（对齐方案的纪律：不合格状态明确记录，不补数、不替换结构）
--------------------------------------------------------------------
* 队列已经停止（supervisor 只在驱动退出、队列轮次结束后调本脚本）就折入**当前已 computed 的腿**，
  未齐的腿在交付层留空并标 `not_computed`，同时在日志里显式列出。
* 不把「20/20 全齐」当硬门禁：若某条腿反复失败，硬门禁会让交付层**永远**停在旧数，
  那才是真正的失败模式。需要严格门禁时用 `--require-complete`。

用法
----
    .venv\\Scripts\\python.exe -X utf8 scripts\\wp_production\\run_to_closure.py --check
    .venv\\Scripts\\python.exe -X utf8 scripts\\wp_production\\run_to_closure.py --dry-run
    .venv\\Scripts\\python.exe -X utf8 scripts\\wp_production\\run_to_closure.py --commit
    .venv\\Scripts\\python.exe -X utf8 scripts\\wp_production\\run_to_closure.py --require-complete --commit

退出码
------
    0  收口链 ALL GREEN（或 `--check`/`--dry-run` 下腿已全齐）
    3  仍有腿未 computed（`--check` 报告；或 `--require-complete` 拒绝折入）
    其它  收口链自身的非零退出码（ABORT）
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))

import run_wp2_queue as queue  # noqa: E402

#: 仍有腿没算完时的退出码；与收口链自身的失败码区分开。
PENDING_EXIT = 3


def pending_legs():
    """按队列自己的口径列出未 computed 的腿（computed 才算数）。"""
    return [(row["name"], row["state"]) for row in queue.inventory()
            if row["status"] != "computed"]


def finalize_command(commit):
    """要执行的收口命令；`-Commit` 只在收口链 ALL GREEN 时才会真正提交。"""
    command = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
               "-File", str(HERE / "finalize_wp2.ps1")]
    if commit:
        command.append("-Commit")
    return command


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Fold the completed WP2 legs into the deliverables (idempotent).")
    parser.add_argument("--check", action="store_true", help="只报告腿的齐备情况，不跑收口链")
    parser.add_argument("--dry-run", action="store_true", help="只打印将执行的收口命令")
    parser.add_argument("--commit", action="store_true", help="收口链 ALL GREEN 后提交")
    parser.add_argument("--require-complete", action="store_true",
                        help="只有 20/20 全 computed 才折入（默认：队列已停就折入，并列出未齐的腿）")
    args = parser.parse_args(argv)

    pending = pending_legs()
    total = len(queue.MOL_IDS) * len(queue.LEGS)
    done = total - len(pending)

    if args.check:
        if pending:
            print("computed %d/%d；未 computed：" % (done, total))
            for name, state in pending:
                print("  %s|%s" % (name, state))
            return PENDING_EXIT
        print("all %d legs computed" % total)
        return 0

    if pending and args.require_complete:
        print("仍有 %d/%d 条腿未 computed，--require-complete 拒绝折入：" % (len(pending), total))
        for name, state in pending:
            print("  %s|%s" % (name, state))
        return PENDING_EXIT

    if pending:
        print("注意：折入的是**部分**腿集（%d/%d computed，%d 条未齐）："
              % (done, total, len(pending)))
        for name, state in pending:
            print("  未 computed: %s|%s" % (name, state))
        print("未齐的腿在交付层留空并标 not_computed；不补数、不替换结构。")
    else:
        print("computed %d/%d：折入完整腿集。" % (done, total))

    command = finalize_command(args.commit)
    print("收口链: %s" % " ".join(command))
    if args.dry_run:
        return 0
    finished = subprocess.run(command, cwd=str(REPO))
    print("收口链 exit=%d" % finished.returncode)
    return finished.returncode


if __name__ == "__main__":
    raise SystemExit(main())