# -*- coding: utf-8 -*-
"""WP6 (Week 33) 可复用分析原语：最小昂贵信息预算（RQ4 后半）。

只读 Week 7 的 Stage 8 冻结 replay 产物（``stage8_al_curves.csv`` / ``stage8_al_runs.csv`` /
``stage8_al_trajectories.csv`` / ``stage8_al_results.json``），以及 Stage 7 的
``stage7_ml_results.csv``（``feature_set=X0`` + ``split=lofo`` + ``shape=direct`` 作静态
held-out 参照）。**零新增电子结构计算，也不重跑 acquisition loop。**

实施方案 WP6 的口径
-------------------
* 目标不是找 MAE 最小的学习器，而是回答 ``n_T -> {tau_b, O_k, R_k}``；
* 四个冻结 baseline：random / diversity / uncertainty / ranking_aware；
* 每轮只暴露已查询标签，标准化与拟合只在可见数据内完成（Stage 8 已保证）；
* 多种子重复报 median 与 2.5/97.5 百分位；
* 成功标准必须**预先定义**、对全部 (task, axis, baseline, n_T) 一律适用，且要求「在多数
  重复中成立」而不是只在中位数曲线上成立；
* 池内插值（in-pool）与 family-held-out 是两种情景 —— 冻结的 Stage 8 只有池内插值，
  本阶段如实标注 family-held-out **不可用**，并用 Stage 7 的 LOFO 静态结果作对照。

存储精度：冻结的曲线表用 ``%.6g`` 写出，因此曲线值只能在发布精度内复现。本模块对
tau_b / overlap / regret 的 median 与 2.5/97.5 百分位逐格重算并给出残差与容差判定。
"""

from __future__ import annotations

import csv
import json
import math
import statistics
from collections import OrderedDict
from pathlib import Path

import numpy as np

TASKS = ("M", "E", "C")
AXES = ("oxidation", "reduction")
BASELINES = ("random", "diversity", "uncertainty", "ranking_aware")
K_FRACTIONS = (0.1, 0.2, 0.3)

#: 每个任务的「廉价」特征集（与 Week 32 / Stage 7 的 feature manifest 一致）。
TASK_FEATURE_SET = OrderedDict([("M", "X0"), ("E", "X0+P1"), ("C", "X0")])

#: 预注册的操作性成功标准（内部研究口径，无外部依据；对所有单元格一律适用）。
TARGET_TAU = 0.80
STRONG_TAU = 0.90
REGRET_TARGET_SCALE = 0.05
SUCCESS_FRACTION = 0.80

SIGFIGS = 6
TAU_TOL = 1e-6
OVERLAP_TOL = 1e-6
REGRET_TOL = 1e-5

CURVE_FIELDS = OrderedDict([
    ("tau_b", "kendall_tau_b"),
    ("o20", "top_k_overlap_20%"),
    ("o30", "top_k_overlap_30%"),
    ("r20", "selection_regret_20%"),
])
TOLERANCE = OrderedDict([
    ("tau_b", TAU_TOL), ("o20", OVERLAP_TOL), ("o30", OVERLAP_TOL), ("r20", REGRET_TOL),
])

WEEK7 = ("outputs", "week7")


def read_csv(path):
    with open(path, encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def load_curves(repo):
    return read_csv(Path(repo).joinpath(*WEEK7, "stage8_al_curves.csv"))


def load_runs(repo):
    return read_csv(Path(repo).joinpath(*WEEK7, "stage8_al_runs.csv"))


def load_trajectories(repo):
    return read_csv(Path(repo).joinpath(*WEEK7, "stage8_al_trajectories.csv"))


def load_results(repo):
    path = Path(repo).joinpath(*WEEK7, "stage8_al_results.json")
    return json.loads(path.read_text(encoding="utf-8"))


def load_stage7_results(repo):
    return read_csv(Path(repo).joinpath(*WEEK7, "stage7_ml_results.csv"))


def key_of(row):
    return (row["task"], row["objective"], row["baseline"], int(row["n_T"]))


def display_step(value):
    """冻结 CSV 用 ``%.6g`` 存储：返回该量级下的一个存储步长。"""
    magnitude = abs(float(value))
    if magnitude < 1e-12:
        return 10.0 ** (-(SIGFIGS - 1))
    return 10.0 ** (math.floor(math.log10(magnitude)) - (SIGFIGS - 1))


def recompute_bands(runs):
    """从逐 repeat 记录重算每个 (task, objective, baseline, n_T) 的 median 与 2.5/97.5。"""
    grouped = {}
    for row in runs:
        grouped.setdefault(key_of(row), []).append(row)
    bands = OrderedDict()
    for key in sorted(grouped):
        rows = grouped[key]
        band = OrderedDict()
        for name, column in CURVE_FIELDS.items():
            values = [float(r[column]) for r in rows]
            band[name] = OrderedDict([
                ("median", float(statistics.median(values))),
                ("lo", float(np.percentile(values, 2.5))),
                ("hi", float(np.percentile(values, 97.5))),
            ])
        band["n_repeats"] = len(rows)
        bands[key] = band
    return bands


def reconcile_curves(curves, bands):
    """冻结曲线 vs 从 runs 重算的 band：逐格残差与容差判定。"""
    rows = []
    worst = OrderedDict((name, 0.0) for name in CURVE_FIELDS)
    worst_ratio = 0.0
    outside = []
    for curve in curves:
        key = key_of(curve)
        band = bands[key]
        record = OrderedDict([
            ("task", curve["task"]), ("axis", curve["objective"]),
            ("baseline", curve["baseline"]), ("n_T", int(curve["n_T"])),
        ])
        max_ratio = 0.0
        ok = True
        for name, column in CURVE_FIELDS.items():
            for level, suffix in (("median", ""), ("lo", "_lo"), ("hi", "_hi")):
                frozen = float(curve[column + suffix])
                diff = abs(frozen - band[name][level])
                record["d_%s_%s" % (name, level)] = diff
                worst[name] = max(worst[name], diff)
                max_ratio = max(max_ratio, diff / display_step(frozen))
                if diff > TOLERANCE[name]:
                    ok = False
        worst_ratio = max(worst_ratio, max_ratio)
        record["max_ratio_vs_storage_step"] = max_ratio
        record["within_tolerance"] = ok
        if not ok:
            outside.append(key)
        rows.append(record)
    summary = OrderedDict([
        ("n_cells", len(curves)),
        ("max_abs_diff", worst),
        ("max_ratio_vs_storage_step", worst_ratio),
        ("tolerances", TOLERANCE),
        ("n_outside_tolerance", len(outside)),
        ("outside_keys", ["|".join(str(part) for part in key) for key in outside]),
    ])
    return rows, summary


def target_scale(trajectories):
    """每个 target 的池内真值极差，以及由此推出的 regret 容忍值（预注册公式）。"""
    span = {}
    for row in trajectories:
        key = (row["task"], row["objective"])
        value = float(row["y_true_ev"])
        low, high = span.get(key, (value, value))
        span[key] = (min(low, value), max(high, value))
    out = OrderedDict()
    for key in sorted(span):
        low, high = span[key]
        out[key] = OrderedDict([
            ("target_min", low), ("target_max", high), ("target_range", high - low),
            ("regret_tolerance_ev", REGRET_TARGET_SCALE * (high - low)),
        ])
    return out


def _group(items, depth=3):
    grouped = {}
    for key, value in items.items():
        grouped.setdefault(key[:depth], []).append((key[depth:], value))
    return grouped


def budget_thresholds(curves):
    """median 曲线首次达到 tau >= TARGET_TAU / STRONG_TAU 的 n_T。"""
    grouped = {}
    for curve in curves:
        grouped.setdefault(key_of(curve)[:3], []).append(curve)
    out = OrderedDict()
    for group in sorted(grouped):
        rows = sorted(grouped[group], key=lambda r: int(r["n_T"]))
        tau = [float(r["kendall_tau_b"]) for r in rows]
        out[group] = OrderedDict([
            ("n_T_points", len(rows)),
            ("n_T_median_tau080", _first_at_least(rows, tau, TARGET_TAU)),
            ("n_T_median_tau090", _first_at_least(rows, tau, STRONG_TAU)),
        ])
    return out


def _first_at_least(rows, values, target):
    for row, value in zip(rows, values):
        if value >= target:
            return int(row["n_T"])
    return None


def monotonicity(curves):
    """median tau_b 随 n_T 是否单调不减；返回违例清单。"""
    grouped = {}
    for curve in curves:
        grouped.setdefault(key_of(curve)[:3], []).append(curve)
    violations = []
    for group in sorted(grouped):
        rows = sorted(grouped[group], key=lambda r: int(r["n_T"]))
        for prev, cur in zip(rows, rows[1:]):
            if float(cur["kendall_tau_b"]) < float(prev["kendall_tau_b"]) - 1e-12:
                violations.append(group + (int(prev["n_T"]), int(cur["n_T"])))
    return violations


def success_by_repeat(runs, scale):
    """逐 (task, axis, baseline, n_T)：20 次重复里满足各判据的比例。"""
    grouped = {}
    for row in runs:
        grouped.setdefault(key_of(row), []).append(row)
    out = OrderedDict()
    for key in sorted(grouped):
        rows = grouped[key]
        tolerance = scale[(key[0], key[1])]["regret_tolerance_ev"]
        n = len(rows)
        passes = OrderedDict([
            ("pass_frac_tau080", sum(1 for r in rows if float(r["kendall_tau_b"]) >= TARGET_TAU) / n),
            ("pass_frac_o20_full", sum(1 for r in rows if float(r["top_k_overlap_20%"]) == 1.0) / n),
            ("pass_frac_regret", sum(1 for r in rows if float(r["selection_regret_20%"]) <= tolerance) / n),
            ("pass_frac_combined", sum(
                1 for r in rows
                if float(r["kendall_tau_b"]) >= TARGET_TAU
                and float(r["top_k_overlap_20%"]) == 1.0
                and float(r["selection_regret_20%"]) <= tolerance) / n),
        ])
        record = OrderedDict([("regret_tolerance_ev", tolerance), ("n_repeats", n)])
        record.update(passes)
        out[key] = record
    return out


def success_budgets(success, thresholds):
    """中位数曲线 vs 「多数重复」两条口径下的预算，并标出前者是否高估。"""
    grouped = {}
    for key, value in success.items():
        grouped.setdefault(key[:3], []).append((key[3], value))
    out = OrderedDict()
    for group in sorted(grouped):
        items = sorted(grouped[group])
        majority_tau = next((n for n, v in items
                             if v["pass_frac_tau080"] >= SUCCESS_FRACTION), None)
        majority_combined = next((n for n, v in items
                                  if v["pass_frac_combined"] >= SUCCESS_FRACTION), None)
        median_tau = thresholds[group]["n_T_median_tau080"]
        overstates = (median_tau is not None and majority_tau is not None
                      and median_tau < majority_tau)
        out[group] = OrderedDict([
            ("n_T_median_tau080", median_tau),
            ("n_T_majority_tau080", majority_tau),
            ("n_T_majority_combined", majority_combined),
            ("median_overstates_majority", overstates),
            ("regret_tolerance_ev", items[0][1]["regret_tolerance_ev"]),
        ])
    return out


def strategy_wins(runs):
    """逐 (task, axis, baseline!=random)：与 random 在同一 (repeat, n_T) 上配对比较。"""
    grid = {}
    for row in runs:
        grid.setdefault((row["task"], row["objective"], row["baseline"], int(row["repeat"])), {})[
            int(row["n_T"])] = row
    out = OrderedDict()
    for task in TASKS:
        for axis in AXES:
            for baseline in BASELINES:
                if baseline == "random":
                    continue
                pairs = []
                for repeat in range(20):
                    cand = grid.get((task, axis, baseline, repeat), {})
                    ref = grid.get((task, axis, "random", repeat), {})
                    for n_T in sorted(set(cand) & set(ref)):
                        pairs.append((cand[n_T], ref[n_T]))
                if not pairs:
                    continue
                gains = [float(a["kendall_tau_b"]) - float(b["kendall_tau_b"]) for a, b in pairs]
                wins = sum(1 for g in gains if g > 1e-12)
                ties = sum(1 for g in gains if abs(g) <= 1e-12)
                out[(task, axis, baseline)] = OrderedDict([
                    ("n_pairs", len(pairs)),
                    ("matched_n_min", min(int(a["n_T"]) for a, _ in pairs)),
                    ("matched_n_max", max(int(a["n_T"]) for a, _ in pairs)),
                    ("win_rate_tau", wins / len(pairs)),
                    ("tie_rate_tau", ties / len(pairs)),
                    ("median_gain_tau", statistics.median(gains)),
                ])
    return out


def family_coverage(trajectories, pools):
    """逐 (task, axis, baseline, n_T)：已查询分子覆盖的家族数（20 次重复的中位数）。"""
    traj = {}
    for row in trajectories:
        traj.setdefault((row["task"], row["objective"], row["baseline"], int(row["repeat"])), []).append(row)
    for key in traj:
        traj[key].sort(key=lambda r: int(r["step"]))
    out = OrderedDict()
    for task in TASKS:
        for axis in AXES:
            pool = pools["%s:%s" % (task, axis)]
            pool_families = len(set(pool["families"]))
            for baseline in BASELINES:
                sequences = [traj[(task, axis, baseline, repeat)] for repeat in range(20)]
                n_max = len(sequences[0])
                for n_T in range(4, n_max + 1):
                    counts = [len({r["family"] for r in seq[:n_T]}) for seq in sequences]
                    out[(task, axis, baseline, n_T)] = OrderedDict([
                        ("median_families", statistics.median(counts)),
                        ("min_families", min(counts)),
                        ("max_families", max(counts)),
                        ("pool_families", pool_families),
                    ])
    return out


def holdout_reference(curves, stage7):
    """池内端点 vs Stage 7 静态 LOFO；并显式标注 AL family-held-out 不可用。"""
    endpoint = {}
    for curve in curves:
        endpoint.setdefault((curve["task"], curve["objective"]), []).append(
            (int(curve["n_T"]), float(curve["kendall_tau_b"])))
    out = OrderedDict()
    for key in sorted(endpoint):
        rows = sorted(endpoint[key])
        n_end, tau_end = rows[-1]
        feature_set = TASK_FEATURE_SET[key[0]]
        candidates = [r for r in stage7
                      if r["task"] == key[0] and r["objective"] == key[1]
                      and r["feature_set"] == feature_set and r["split"] == "lofo"
                      and r["shape"] == "direct"]
        best = max(candidates, key=lambda r: float(r["kendall_tau_b"]))
        out[key] = OrderedDict([
            ("pool_size", n_end),
            ("inpool_endpoint_tau_b", tau_end),
            ("static_lofo_tau_b", float(best["kendall_tau_b"])),
            ("static_lofo_model", best["model"]),
            ("static_lofo_feature_set", feature_set),
            ("al_family_heldout_available", False),
        ])
    return out


def acceptance(curves, success, budgets, thresholds, holdout, scale):
    """WP6 四个验收问题的结论、支撑数与反例。"""
    violations = monotonicity(curves)
    n_curves = len(thresholds)

    better, worse, ties = [], [], []
    for group in sorted(thresholds):
        if group[2] == "random":
            continue
        ref = budgets[(group[0], group[1], "random")]["n_T_majority_combined"]
        mine = budgets[group]["n_T_majority_combined"]
        tag = "%s|%s|%s" % (group[0], group[1], group[2])
        if ref is None and mine is None:
            ties.append(tag + "(both never reach)")
        elif mine is None:
            worse.append(tag + "(never reaches; random at n_T=%d)" % ref)
        elif ref is None:
            better.append(tag + "(reaches at n_T=%d; random never)" % mine)
        elif mine < ref:
            better.append(tag + "(saves %d)" % (ref - mine))
        elif mine > ref:
            worse.append(tag + "(costs +%d)" % (mine - ref))
        else:
            ties.append(tag + "(tie at n_T=%d)" % mine)

    overstate = ["%s|%s|%s" % (g[0], g[1], g[2]) for g in sorted(budgets)
                 if budgets[g]["median_overstates_majority"]]

    gaps = ["%s|%s(inpool %.3f vs lofo %+.3f)" % (key[0], key[1],
                                                  holdout[key]["inpool_endpoint_tau_b"],
                                                  holdout[key]["static_lofo_tau_b"])
            for key in sorted(holdout)]

    return [
        OrderedDict([
            ("question_id", "Q1_budget_curve_improves"),
            ("question", "四个策略的 median tau_b 是否都随 n_T 单调改善？"),
            ("verdict", "%d/%d 条 median tau_b 曲线单调不减（违例 %d 处）"
                        % (n_curves - len({v[:3] for v in violations}), n_curves, len(violations))),
            ("n_supporting", n_curves - len({v[:3] for v in violations})),
            ("n_cells", n_curves),
            ("evidence", "违例（task|axis|baseline|n_T_prev|n_T_next）：%s"
                         % (";".join("%s|%s|%s|%d|%d" % v for v in violations) or "none")),
            ("counterexamples", ";".join(sorted({"%s|%s|%s" % v[:3] for v in violations})) or "none"),
        ]),
        OrderedDict([
            ("question_id", "Q2_strategy_beats_random"),
            ("question", "非随机策略是否比 random 更省昂贵标签（用「多数重复达标」预算衡量）？"),
            ("verdict", "更省 %d 个组合 / 更贵 %d 个 / 打平 %d 个" % (len(better), len(worse), len(ties))),
            ("n_supporting", len(better)),
            ("n_cells", len(better) + len(worse) + len(ties)),
            ("evidence", "更省：%s" % (";".join(better) or "none")),
            ("counterexamples", ";".join(worse) or "none"),
        ]),
        OrderedDict([
            ("question_id", "Q3_majority_of_repeats"),
            ("question", "达标是否在多数重复中成立，而不是只在中位数曲线上成立？"),
            ("verdict", "%d/%d 个 (task, axis, baseline) 的中位数曲线比「多数重复」更早达标（高估）"
                        % (len(overstate), n_curves)),
            ("n_supporting", n_curves - len(overstate)),
            ("n_cells", n_curves),
            ("evidence", "中位数曲线高估的组合：%s" % (";".join(overstate) or "none")),
            ("counterexamples", ";".join(overstate) or "none"),
        ]),
        OrderedDict([
            ("question_id", "Q4_inpool_vs_family_heldout"),
            ("question", "池内（in-pool）曲线饱和是否等于跨家族泛化？"),
            ("verdict", "不等价：冻结 replay 只有池内插值，family-held-out 的 AL 曲线不可用；"
                        "池内端点 tau_b 恒为 1.0（自检端点），静态 LOFO 参照最高也只有 %+.3f"
                        % max(holdout[key]["static_lofo_tau_b"] for key in holdout)),
            ("n_supporting", sum(1 for key in holdout if not holdout[key]["al_family_heldout_available"])),
            ("n_cells", len(holdout)),
            ("evidence", ";".join(gaps)),
            ("counterexamples", "none"),
        ]),
    ]


def analyse(repo):
    curves = load_curves(repo)
    runs = load_runs(repo)
    trajectories = load_trajectories(repo)
    results = load_results(repo)
    stage7 = load_stage7_results(repo)

    scale = target_scale(trajectories)
    bands = recompute_bands(runs)
    recon_rows, recon = reconcile_curves(curves, bands)
    thresholds = budget_thresholds(curves)
    success = success_by_repeat(runs, scale)
    budgets = success_budgets(success, thresholds)
    wins = strategy_wins(runs)
    coverage = family_coverage(trajectories, results["pools"])
    holdout = holdout_reference(curves, stage7)

    return OrderedDict([
        ("curves", curves), ("runs", runs), ("trajectories", trajectories),
        ("results", results), ("stage7", stage7),
        ("scale", scale), ("bands", bands),
        ("recon_rows", recon_rows), ("reconcile", recon),
        ("thresholds", thresholds), ("success", success), ("budgets", budgets),
        ("wins", wins), ("coverage", coverage), ("holdout", holdout),
        ("monotonicity_violations", monotonicity(curves)),
        ("acceptance", acceptance(curves, success, budgets, thresholds, holdout, scale)),
    ])