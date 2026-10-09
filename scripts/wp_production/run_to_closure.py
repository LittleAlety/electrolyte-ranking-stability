# -*- coding: utf-8 -*-
"""队列收尾：20 条腿全 computed 后，把结果折进交付层（一键收口链）。

为什么需要这一步：无人值守链只到 `run_wp2_queue.py --run` 为止，而队列只负责**把腿算完**。
「腿算完」不等于「交付层更新」：production_ledger / 四分子闭环表 / 四分子标签 /
week37-week44 镜像都要靠 `finalize_wp2.ps1` 折进去。缺了这一步，机器算完后会停在一个
「原始结果已在、交付层还是旧数」的中间态，四分子闭环看起来仍未完成。

纪律：**只有 20/20 全齐才折入**。少一条腿就退出码 3，不折、不补数、不替换结构。

用法
----
    .venv\\Scripts\\python.exe -X utf8 scripts\\wp_production\\run_to_closure.py --check
    .venv\\Scripts\\python.exe -X utf8 scripts\\wp_production\\run_to_closure.py --dry-run
    .venv\\Scripts\\python.exe -X utf8 scripts\\wp_production\\run_to_closure.py
    .venv\\Scripts\\python.exe -X utf8 scripts\\wp_production\\run_to_closure.py --commit

退出码
------
    0  收口链 ALL GREEN（或 `--check`/`--dry-run` 下 20/20 全齐）
    3  还有腿未 computed，本轮不折入
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

#: 还有腿没算完时的退出码；与收口链自身的失败码区分开。
PENDING_EXIT = 3


def pending_legs():
    """按队列自己的口径列出未 computed 的腿（computed 才算数）。"""
    return [(row["name"], row["state"]) for row in queue.inventory()
            if row["status"] != "computed"]


def finalize_command(commit):
    """要执行的收口命令；`--commit` 只在收口链 ALL GREEN 时才会真正提交。"""
    command = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
               "-File", str(HERE / "finalize_wp2.ps1")]
    if commit:
        command.append("-Commit")
    return command


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Fold the completed WP2 legs into the deliverables (idempotent).")
    parser.add_argument("--check", action="store_true", help="只报告是否 20 条腿全齐，不跑收口链")
    parser.add_argument("--dry-run", action="store_true", help="只打印将执行的收口命令")
    parser.add_argument("--commit", action="store_true", help="收口链 ALL GREEN 后提交")
    args = parser.parse_args(argv)

    pending = pending_legs()
    total = len(queue.MOL_IDS) * len(queue.LEGS)
    if pending:
        print("还有 %d/%d 条腿未 computed，本轮不折入：" % (len(pending), total))
        for name, state in pending:
            print("  %s|%s" % (name, state))
        return PENDING_EXIT

    if args.check:
        print("all %d legs computed" % total)
        return 0

    command = finalize_command(args.commit)
    print("收口链: %s" % " ".join(command))
    if args.dry_run:
        return 0
    done = subprocess.run(command, cwd=str(REPO))
    print("收口链 exit=%d" % done.returncode)
    return done.returncode


if __name__ == "__main__":
    raise SystemExit(main())