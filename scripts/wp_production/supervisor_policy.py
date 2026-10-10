# -*- coding: utf-8 -*-
"""无人值守链的收敛判据（纯函数 + 一个取数入口，都可单测）。

为什么单独成文件：本阶段唯一的目标是「把四分子 20 条腿算完」，所以「腿没算完绝不停」
这件事的判据不能埋在 .ps1 的分支里——那段无法单测，而它一旦写错，整条链会在半路静默停摆
（旧版就是跑满固定轮数就退出、删锁、不再有人拉起）。

PowerShell 的 supervise_pending.ps1 只负责取数、调用、落盘；「要不要再来一轮」
「什么时候该放弃」由这里决定，并在这里被测试钉住。

用法
----
    python scripts/wp_production/supervisor_policy.py --computed-count
    python scripts/wp_production/supervisor_policy.py --decide --before 10 --after 12 --round 1 \
        --stalled 0 --max-rounds 6 --max-stalled 3
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

DONE = "done"
CONTINUE = "continue"
STOP_STALLED = "stop_stalled"
STOP_ROUND_CAP = "stop_round_cap"

#: 仍未算完时的退出码；与收口链自身的失败码区分开。
INCOMPLETE_EXIT = 3


def computed_count(rows):
    """按队列器自己的口径数已 computed 的腿。口径只有一处（run_wp2_queue.inventory）。"""
    return sum(1 for row in rows if row.get("status") == "computed")


def decide(before, after, target, round_index, stalled, max_rounds, max_stalled_rounds):
    """下一轮该继续还是停。

    * 已经全齐 -> DONE；
    * 本轮 computed 数**涨了** -> 清零 stalled 并继续（有进展就不停，慢不等于失败）；
    * 本轮**没涨** -> stalled + 1，连续 max_stalled_rounds 轮无进展才停（不在确定性失败上烧机时）；
    * 轮数上限只作兜底，且**只在无进展计数之外**生效，避免把「还在推进」误判成「该放弃」。

    返回 (decision, stalled)。
    """
    if after >= target:
        return DONE, stalled
    stalled = 0 if after > before else stalled + 1
    if stalled >= max_stalled_rounds:
        return STOP_STALLED, stalled
    if round_index >= max_rounds:
        return STOP_ROUND_CAP, stalled
    return CONTINUE, stalled


def inventory_rows():
    import run_wp2_queue as queue  # noqa: E402  (延迟导入：模块导入时会解析 ORCA 路径)

    return queue.inventory()


def main(argv=None):
    parser = argparse.ArgumentParser(description="Supervisor convergence policy.")
    parser.add_argument("--computed-count", action="store_true")
    parser.add_argument("--decide", action="store_true")
    parser.add_argument("--before", type=int, default=0)
    parser.add_argument("--after", type=int, default=0)
    parser.add_argument("--target", type=int, default=20)
    parser.add_argument("--round", type=int, default=0)
    parser.add_argument("--stalled", type=int, default=0)
    parser.add_argument("--max-rounds", type=int, default=6)
    parser.add_argument("--max-stalled", type=int, default=3)
    args = parser.parse_args(argv)

    if args.computed_count:
        print(computed_count(inventory_rows()))
        return 0
    if args.decide:
        decision, stalled = decide(args.before, args.after, args.target, args.round,
                                   args.stalled, args.max_rounds, args.max_stalled)
        print("%s %d" % (decision, stalled))
        return 0
    parser.error("需要 --computed-count 或 --decide 之一")


if __name__ == "__main__":
    raise SystemExit(main())
