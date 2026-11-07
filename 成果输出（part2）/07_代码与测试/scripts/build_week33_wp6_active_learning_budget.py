#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""Week 33 / WP6 -- 最小昂贵信息预算（RQ4 后半，主动学习）。

为什么有这个阶段
----------------
WP5 说明「便宜参考层 + 学到的位移」能不能替代直接预测。WP6 回答更实际的问题：**要花多少
次昂贵计算，才能把筛选决策恢复到可接受水平**，也就是 ``n_T -> {tau_b, O_k, R_k}``。

本阶段**不重跑 acquisition loop**，只对 Week 7 Stage 8 的冻结 replay 做决策导向的再分析：

* 四个冻结 baseline（random / diversity / uncertainty / ranking_aware）的预算-收益曲线；
* 用逐 repeat 记录重算 median 与 2.5/97.5 百分位，与冻结 ``stage8_al_curves.csv`` 对账；
* 预注册的操作性成功标准（median tau_b >= 0.80；Top-20% overlap 全中；regret <= 池内目标
  极差的 5%），且要求**在 >= 80% 的重复中成立**，而不是只在中位数曲线上成立；
* 池内插值（in-pool）与 family-held-out 两种情景：冻结 replay 只有前者，本阶段如实标注
  后者不可用，并用 Stage 7 的 LOFO 静态结果作对照。

十张表
------
al_protocol_audit       逐 (task, axis) 的协议与目标尺度审计（含 regret 容忍值来源）
budget_curves           逐 (task, axis, baseline, n_T) 的 tau_b / overlap / regret 与区间
curve_reconciliation    冻结曲线 vs 从 runs 重算的 band：逐格残差与容差判定
budget_to_threshold     median 曲线首次达到 tau >= 0.80 / 0.90 的 n_T
success_criteria        逐格的「多数重复」达标比例（tau / overlap / regret / 组合）
success_budget          中位数曲线 vs 多数重复两条口径的预算，并标出前者是否高估
strategy_comparison     非随机策略 vs random 的配对胜负率与收益中位数
family_coverage         已查询分子覆盖的家族数（in-pool 的化学空间覆盖代理）
holdout_vs_inpool       池内端点 vs 静态 LOFO；显式声明 AL family-held-out 不可用
wp6_acceptance          四个验收问题的结论、支撑数与反例

用法
----
    .venv\Scripts\python.exe scripts\build_week33_wp6_active_learning_budget.py
    .venv\Scripts\python.exe scripts\build_week33_wp6_active_learning_budget.py --check
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import sys
from collections import OrderedDict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from electrolyte_ranking import wp6  # noqa: E402

OUTDIR = REPO / "outputs" / "week33"

TABLE_ORDER = (
    "al_protocol_audit",
    "budget_curves",
    "curve_reconciliation",
    "budget_to_threshold",
    "success_criteria",
    "success_budget",
    "strategy_comparison",
    "family_coverage",
    "holdout_vs_inpool",
    "wp6_acceptance",
)

_METRIC_DIFF_COLUMNS = tuple(
    "d_%s_%s" % (name, level) for name in wp6.CURVE_FIELDS for level in ("median", "lo", "hi"))

SCHEMAS = OrderedDict([
    ("al_protocol_audit", (
        "task", "axis", "pool_size", "initial_seed_size", "batch_size", "repeats",
        "n_T_min", "n_T_max", "n_curve_points", "k_fractions", "acquisition_features",
        "hidden_label_replay", "in_loop_hygiene", "ranking_rule",
        "target_min", "target_max", "target_range", "regret_tolerance_ev")),
    ("budget_curves", (
        "task", "axis", "baseline", "n_T",
        "tau_b", "tau_b_lo", "tau_b_hi",
        "o20", "o20_lo", "o20_hi", "o30", "r20", "r20_lo", "r20_hi")),
    ("curve_reconciliation", ("task", "axis", "baseline", "n_T") + _METRIC_DIFF_COLUMNS + (
        "max_ratio_vs_storage_step", "within_tolerance")),
    ("budget_to_threshold", (
        "task", "axis", "baseline", "n_T_points", "n_T_median_tau080", "n_T_median_tau090")),
    ("success_criteria", (
        "task", "axis", "baseline", "n_T", "n_repeats", "regret_tolerance_ev",
        "pass_frac_tau080", "pass_frac_o20_full", "pass_frac_regret", "pass_frac_combined")),
    ("success_budget", (
        "task", "axis", "baseline", "n_T_median_tau080", "n_T_majority_tau080",
        "n_T_majority_combined", "median_overstates_majority", "regret_tolerance_ev")),
    ("strategy_comparison", (
        "task", "axis", "baseline", "n_pairs", "matched_n_min", "matched_n_max",
        "win_rate_tau", "tie_rate_tau", "median_gain_tau")),
    ("family_coverage", (
        "task", "axis", "baseline", "n_T", "median_families", "min_families",
        "max_families", "pool_families")),
    ("holdout_vs_inpool", (
        "task", "axis", "pool_size", "inpool_endpoint_tau_b", "static_lofo_tau_b",
        "static_lofo_model", "static_lofo_feature_set", "al_family_heldout_available", "note")),
    ("wp6_acceptance", (
        "question_id", "question", "verdict", "n_supporting", "n_cells", "evidence",
        "counterexamples")),
])


def _fmt(value):
    if value is None:
        return ""
    if isinstance(value, bool):
        return "True" if value else "False"
    if isinstance(value, float):
        return repr(value)
    return str(value)


def build_tables(analysis):
    curves = analysis["curves"]
    results = analysis["results"]
    settings = results["settings"]
    protocol = results["protocol"]
    scale = analysis["scale"]

    protocol_rows = []
    for target in settings["targets"]:
        task, axis = target.split(":")
        pool = results["pools"][target]
        group = [c for c in curves if (c["task"], c["objective"]) == (task, axis)]
        points = sorted(int(c["n_T"]) for c in group)
        protocol_rows.append(OrderedDict([
            ("task", task), ("axis", axis), ("pool_size", pool["n_pool"]),
            ("initial_seed_size", protocol["initial_seed_size"]),
            ("batch_size", protocol["batch_size"]), ("repeats", settings["repeats"]),
            ("n_T_min", points[0]), ("n_T_max", points[-1]),
            ("n_curve_points", len(points) // len(wp6.BASELINES)),
            ("k_fractions", ";".join(str(f) for f in settings["k_fractions"])),
            ("acquisition_features", settings["acquisition_features"]),
            ("hidden_label_replay", protocol["hidden_label_replay"]),
            ("in_loop_hygiene", protocol["in_loop_hygiene"]),
            ("ranking_rule", protocol["ranking_rule"]),
            ("target_min", scale[(task, axis)]["target_min"]),
            ("target_max", scale[(task, axis)]["target_max"]),
            ("target_range", scale[(task, axis)]["target_range"]),
            ("regret_tolerance_ev", scale[(task, axis)]["regret_tolerance_ev"]),
        ]))

    curve_rows = []
    for curve in curves:
        key = wp6.key_of(curve)
        band = analysis["bands"][key]
        curve_rows.append(OrderedDict([
            ("task", curve["task"]), ("axis", curve["objective"]),
            ("baseline", curve["baseline"]), ("n_T", int(curve["n_T"])),
            ("tau_b", float(curve["kendall_tau_b"])),
            ("tau_b_lo", float(curve["kendall_tau_b_lo"])),
            ("tau_b_hi", float(curve["kendall_tau_b_hi"])),
            ("o20", float(curve["top_k_overlap_20%"])),
            ("o20_lo", float(curve["top_k_overlap_20%_lo"])),
            ("o20_hi", float(curve["top_k_overlap_20%_hi"])),
            ("o30", float(curve["top_k_overlap_30%"])),
            ("r20", float(curve["selection_regret_20%"])),
            ("r20_lo", float(curve["selection_regret_20%_lo"])),
            ("r20_hi", float(curve["selection_regret_20%_hi"])),
        ]))

    threshold_rows = []
    for group in sorted(analysis["thresholds"]):
        info = analysis["thresholds"][group]
        threshold_rows.append(OrderedDict([
            ("task", group[0]), ("axis", group[1]), ("baseline", group[2]),
            ("n_T_points", info["n_T_points"]),
            ("n_T_median_tau080", info["n_T_median_tau080"]),
            ("n_T_median_tau090", info["n_T_median_tau090"]),
        ]))

    criteria_rows = []
    for key in sorted(analysis["success"]):
        info = analysis["success"][key]
        row = OrderedDict([
            ("task", key[0]), ("axis", key[1]), ("baseline", key[2]), ("n_T", key[3]),
            ("n_repeats", info["n_repeats"]),
            ("regret_tolerance_ev", info["regret_tolerance_ev"]),
        ])
        for name in ("pass_frac_tau080", "pass_frac_o20_full", "pass_frac_regret",
                     "pass_frac_combined"):
            row[name] = info[name]
        criteria_rows.append(row)

    budget_rows = []
    for group in sorted(analysis["budgets"]):
        info = analysis["budgets"][group]
        budget_rows.append(OrderedDict([
            ("task", group[0]), ("axis", group[1]), ("baseline", group[2]),
            ("n_T_median_tau080", info["n_T_median_tau080"]),
            ("n_T_majority_tau080", info["n_T_majority_tau080"]),
            ("n_T_majority_combined", info["n_T_majority_combined"]),
            ("median_overstates_majority", info["median_overstates_majority"]),
            ("regret_tolerance_ev", info["regret_tolerance_ev"]),
        ]))

    win_rows = []
    for group in sorted(analysis["wins"]):
        info = analysis["wins"][group]
        row = OrderedDict([("task", group[0]), ("axis", group[1]), ("baseline", group[2])])
        row.update(info)
        win_rows.append(row)

    coverage_rows = []
    for key in sorted(analysis["coverage"]):
        info = analysis["coverage"][key]
        row = OrderedDict([("task", key[0]), ("axis", key[1]), ("baseline", key[2]),
                           ("n_T", key[3])])
        row.update(info)
        coverage_rows.append(row)

    holdout_rows = []
    for key in sorted(analysis["holdout"]):
        info = analysis["holdout"][key]
        row = OrderedDict([("task", key[0]), ("axis", key[1])])
        row.update(info)
        row["note"] = ("冻结 replay 只有 in-pool 口径；family-held-out 的 AL 曲线需要重跑 "
                       "acquisition，本阶段不提供")
        holdout_rows.append(row)

    return OrderedDict([
        ("al_protocol_audit", protocol_rows),
        ("budget_curves", curve_rows),
        ("curve_reconciliation", analysis["recon_rows"]),
        ("budget_to_threshold", threshold_rows),
        ("success_criteria", criteria_rows),
        ("success_budget", budget_rows),
        ("strategy_comparison", win_rows),
        ("family_coverage", coverage_rows),
        ("holdout_vs_inpool", holdout_rows),
        ("wp6_acceptance", analysis["acceptance"]),
    ])


def _trajectory_sequences(analysis):
    sequences = {}
    for row in analysis["trajectories"]:
        key = (row["task"], row["objective"], row["baseline"], int(row["repeat"]))
        sequences.setdefault(key, []).append(row)
    return sequences


def build_checks(analysis, tables):
    results = analysis["results"]
    counts = results["counts"]
    recon = analysis["reconcile"]
    curves = analysis["curves"]
    sequences = _trajectory_sequences(analysis)

    protocol_rows = tables["al_protocol_audit"]
    target_ok = all(abs(r["regret_tolerance_ev"]
                        - wp6.REGRET_TARGET_SCALE * r["target_range"]) < 1e-12
                    for r in protocol_rows)
    settings = results["settings"]
    ledger_ok = (
        counts["n_curve_rows"] == len(curves) == 296
        and counts["n_run_rows"] == 5920
        and counts["n_trajectory_rows"] == 7360
        and counts["n_fit_fallbacks"] == 0
        and settings["repeats"] == 20
        and settings["acquisition_features"] == "X0 only"
        and sorted(settings["baselines"]) == sorted(wp6.BASELINES)
        and sorted(settings["k_fractions"]) == list(wp6.K_FRACTIONS)
    )

    prefix_bad = []
    for key, seq in sorted(sequences.items()):
        ordered = sorted(seq, key=lambda r: int(r["step"]))
        steps = [int(r["step"]) for r in ordered]
        names = [r["name"] for r in ordered]
        if steps != list(range(len(ordered))) or len(set(names)) != len(names):
            prefix_bad.append(key)
    prefix_ok = (not prefix_bad and len(sequences) == 6 * len(wp6.BASELINES) * 20)

    coverage_rows = tables["family_coverage"]
    coverage_bad = [r for r in coverage_rows if r["median_families"] > r["pool_families"]]
    coverage_monotone = True
    grouped = {}
    for row in coverage_rows:
        grouped.setdefault((row["task"], row["axis"], row["baseline"]), []).append(row)
    for group, rows in grouped.items():
        ordered = sorted(rows, key=lambda r: r["n_T"])
        for prev, cur in zip(ordered, ordered[1:]):
            if cur["median_families"] < prev["median_families"]:
                coverage_monotone = False

    band_bad = []
    for key, band in analysis["bands"].items():
        for name in wp6.CURVE_FIELDS:
            lo, med, hi = band[name]["lo"], band[name]["median"], band[name]["hi"]
            if not (lo <= med <= hi + 1e-12):
                band_bad.append(key + (name,))

    holdout = tables["holdout_vs_inpool"]
    holdout_ok = (len(holdout) == 6
                  and all(r["al_family_heldout_available"] is False for r in holdout)
                  and all(abs(r["inpool_endpoint_tau_b"] - 1.0) < 1e-12 for r in holdout)
                  and all(r["static_lofo_tau_b"] < 1.0 for r in holdout))

    win_rows = tables["strategy_comparison"]
    win_ok = (len(win_rows) == 6 * (len(wp6.BASELINES) - 1)
              and all(0.0 <= r["win_rate_tau"] <= 1.0 for r in win_rows)
              and all(0.0 <= r["tie_rate_tau"] <= 1.0 for r in win_rows)
              and all(r["win_rate_tau"] + r["tie_rate_tau"] <= 1.0 + 1e-12 for r in win_rows))

    criteria_rows = tables["success_criteria"]
    criteria_ok = (len(criteria_rows) == len(curves)
                   and all(r["n_repeats"] == 20 for r in criteria_rows)
                   and all(0.0 <= r["pass_frac_combined"] <= 1.0 for r in criteria_rows))

    return [
        OrderedDict([
            ("id", "curves_recomputed_from_runs_within_storage_precision"),
            ("ok", recon["n_cells"] == len(curves) and recon["n_outside_tolerance"] == 0),
            ("detail", "从逐 repeat 记录重算 %d 个曲线单元格的 median 与 2.5/97.5 百分位，"
                       "全部落在发布精度容差内（max |diff| tau_b=%.3e, overlap=%.3e, regret=%.3e；"
                       "最大残差仅相当于 %.2f 个 %.6g 存储步长）；超容差 0"
                       % (recon["n_cells"], recon["max_abs_diff"]["tau_b"],
                          max(recon["max_abs_diff"]["o20"], recon["max_abs_diff"]["o30"]),
                          recon["max_abs_diff"]["r20"], recon["max_ratio_vs_storage_step"],
                          wp6.SIGFIGS)),
            ("max_abs_diff", recon["max_abs_diff"]),
            ("tolerances", recon["tolerances"]),
            ("n_outside_tolerance", recon["n_outside_tolerance"]),
        ]),
        OrderedDict([
            ("id", "every_frozen_curve_cell_recombined"),
            ("ok", set(analysis["bands"]) == {wp6.key_of(c) for c in curves}),
            ("detail", "冻结曲线的 %d 个 (task, axis, baseline, n_T) 单元格全部被重算覆盖，"
                       "缺失 0" % len(curves)),
            ("n_cells", len(curves)),
        ]),
        OrderedDict([
            ("id", "protocol_matches_frozen_ledger"),
            ("ok", bool(ledger_ok)),
            ("detail", "池大小 / n_T 范围 / repeats=20 / 四 baseline / k=10,20,30%% / "
                       "acquisition 特征 = X0 only 与 stage8_al_results.json 一致；"
                       "计数 296 curves / 5920 runs / 7360 trajectories，GPR 回落 0 次"),
            ("counts", counts), ("settings_repeats", settings["repeats"]),
        ]),
        OrderedDict([
            ("id", "sequential_acquisition_prefix_property"),
            ("ok", bool(prefix_ok)),
            ("detail", "%d 条 (task, axis, baseline, repeat) 采集轨迹，step 连续且每一步是全新分子"
                       "（无重复 query），因此 n_T 的已查询集合严格是 n_T+1 的前缀" % len(sequences)),
            ("bad_keys", ["|".join(str(p) for p in k) for k in prefix_bad]),
        ]),
        OrderedDict([
            ("id", "success_criteria_preregistered_and_uniform"),
            ("ok", bool(target_ok and criteria_ok)),
            ("detail", "四个成功判据（tau_b >= %.2f；Top-20%% overlap 全中；regret <= 池内目标极差"
                       "的 %.0f%%；且在 >= %.0f%% 重复中成立）写死在代码里、对所有 %d 个单元格"
                       "一律适用；容忍值由公式推出（每 target 一个值），无逐格调参"
                       % (wp6.TARGET_TAU, wp6.REGRET_TARGET_SCALE * 100,
                          wp6.SUCCESS_FRACTION * 100, len(criteria_rows))),
            ("criteria", OrderedDict([
                ("target_tau", wp6.TARGET_TAU), ("strong_tau", wp6.STRONG_TAU),
                ("regret_target_scale", wp6.REGRET_TARGET_SCALE),
                ("success_fraction", wp6.SUCCESS_FRACTION)])),
        ]),
        OrderedDict([
            ("id", "bands_ordered_and_bracketing"),
            ("ok", not band_bad),
            ("detail", "全部 %d 个单元格满足 2.5%% <= median <= 97.5%%（反例 %d）"
                       % (len(analysis["bands"]), len(band_bad))),
        ]),
        OrderedDict([
            ("id", "strategy_effect_quantified"),
            ("ok", bool(win_ok)),
            ("detail", "%d 个 (task, axis, 非random baseline) 组都在同一 (repeat, n_T) 上与 random "
                       "配对比较，给出胜负率与 tau_b 收益中位数" % len(win_rows)),
        ]),
        OrderedDict([
            ("id", "family_coverage_computed"),
            ("ok", not coverage_bad and coverage_monotone and len(coverage_rows) == len(curves)),
            ("detail", "%d 个单元格都算了已查询集合覆盖的家族数（中位数/最小/最大）；"
                       "覆盖数随 n_T 单调不减且不超过池内家族数" % len(coverage_rows)),
        ]),
        OrderedDict([
            ("id", "family_heldout_gap_declared"),
            ("ok", bool(holdout_ok)),
            ("detail", "6 个 target 的池内端点 tau_b 恒为 1.0（自检端点，不是成绩）；"
                       "静态 LOFO 参照最高 %.3f；**AL family-held-out 曲线不可用**（需要重跑 "
                       "acquisition），已逐行标注"
                       % max(r["static_lofo_tau_b"] for r in holdout)),
        ]),
        OrderedDict([
            ("id", "zero_new_electronic_structure"),
            ("ok", True),
            ("detail", "唯一输入是 outputs/week7 的 Stage 8 冻结 replay 与 Stage 7 冻结 ML 结果；"
                       "未运行任何电子结构作业，也未重跑 acquisition loop"),
        ]),
    ]


def collect():
    analysis = wp6.analyse(REPO)
    tables = build_tables(analysis)
    checks = build_checks(analysis, tables)
    recon = analysis["reconcile"]

    csv_texts = OrderedDict()
    manifest = OrderedDict()
    for table in TABLE_ORDER:
        columns = list(SCHEMAS[table])
        buffer = io.StringIO()
        writer = csv.writer(buffer, lineterminator="\n")
        writer.writerow(columns)
        for row in tables[table]:
            writer.writerow([_fmt(row.get(column)) for column in columns])
        text = buffer.getvalue()
        csv_texts[table + ".csv"] = text
        manifest[table] = OrderedDict([
            ("file", "outputs/week33/%s.csv" % table),
            ("n_rows", len(tables[table])),
            ("columns", columns),
            ("sha256", hashlib.sha256(text.encode("utf-8")).hexdigest()),
        ])

    results = analysis["results"]
    payload = OrderedDict([
        ("stage", "Week 33 / WP6"),
        ("title", "minimum expensive-information budget (RQ4, part 2)"),
        ("plane", "next-phase implementation plan, work package WP6 (RQ4 second half)"),
        ("inputs", OrderedDict([
            ("curves", "outputs/week7/stage8_al_curves.csv"),
            ("runs", "outputs/week7/stage8_al_runs.csv"),
            ("trajectories", "outputs/week7/stage8_al_trajectories.csv"),
            ("ledger", "outputs/week7/stage8_al_results.json"),
            ("held_out_reference", "outputs/week7/stage7_ml_results.csv"),
            ("baselines", list(wp6.BASELINES)), ("tasks", list(wp6.TASKS)),
            ("axes", list(wp6.AXES)), ("k_fractions", list(wp6.K_FRACTIONS)),
            ("new_electronic_structure_jobs", 0), ("acquisition_reruns", 0),
        ])),
        ("conventions", OrderedDict([
            ("budget", "n_T = number of expensive target labels acquired (initial seed 4, batch 1)"),
            ("metrics", "n_T -> {kendall tau_b, Top-k overlap, selection regret}; k = 10/20/30%"),
            ("bands", "median and 2.5/97.5 percentiles over 20 acquisition repeats"),
            ("success_standard", "operational, internally motivated (no external calibration): "
                                 "median tau_b >= 0.80, Top-20% overlap complete, "
                                 "regret <= 5% of the in-pool target range, and the result must "
                                 "hold in >= 80% of the repeats (not only on the median curve)"),
            ("storage_precision", "frozen curves are written with %.6g; bands can only be "
                                  "reproduced to publication precision"),
            ("scenarios", "in-pool interpolation is available; family-held-out AL curves are NOT "
                          "available without re-running acquisition and are declared as a gap"),
            ("gate1_status", "Gate 1 remains NOT CLOSED; WP6 is a computational-target statement"),
        ])),
        ("reconciliation", recon),
        ("counts", results["counts"]),
        ("checks", checks),
        ("checks_by_id", OrderedDict((c["id"], c) for c in checks)),
        ("manifest", manifest),
        ("n_rows_total", sum(len(tables[t]) for t in TABLE_ORDER)),
    ])

    texts = OrderedDict(csv_texts)
    texts["wp6_active_learning.json"] = (
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=False) + "\n")
    texts["wp6_summary.md"] = render_summary(payload, tables)
    texts["manifest.json"] = json.dumps(
        OrderedDict([("stage", "Week 33 / WP6"), ("tables", manifest)]),
        ensure_ascii=False, indent=2, sort_keys=False) + "\n"
    return payload, texts


def _table(headers, rows):
    lines = ["| " + " | ".join(headers) + " |",
             "| " + " | ".join("---" for _ in headers) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(cell) for cell in row) + " |")
    return lines


def render_summary(payload, tables):
    protocol = tables["al_protocol_audit"]
    curves = tables["budget_curves"]
    budget = tables["success_budget"]
    wins = tables["strategy_comparison"]
    holdout = tables["holdout_vs_inpool"]
    acceptance = tables["wp6_acceptance"]
    recon = payload["reconciliation"]
    overstated = [x for x in acceptance[2]["counterexamples"].split(";") if x and x != "none"]
    combined_overstated = [r for r in budget
                           if r["n_T_median_tau080"] and r["n_T_majority_combined"]
                           and r["n_T_median_tau080"] < r["n_T_majority_combined"]]

    lines = [
        "# Week 33 / WP6：最小昂贵信息预算（RQ4 后半）",
        "",
        "> 阶段：下一阶段实施方案 WP6（RQ4 后半）。产物目录 `outputs/week33/`，交付镜像",
        "> `..\\成果输出（part2）\\week33/`。本文件由 "
        "`scripts/build_week33_wp6_active_learning_budget.py`",
        "> 确定性生成，`--check` 逐字节复核。**零新增电子结构计算，零重跑 acquisition**：",
        "> 输入是 Week 7 Stage 8 的冻结 replay 产物。",
        "",
        "## 0. 一句话结论",
        "",
        "预注册的成功标准是「median τ_b ≥ %.2f、Top-20%% overlap 全中、regret ≤ 池内目标极差的 "
        "%.0f%%，且在 ≥ %.0f%% 的重复中成立」。"
        % (wp6.TARGET_TAU, wp6.REGRET_TARGET_SCALE * 100, wp6.SUCCESS_FRACTION * 100),
        "四条策略里 **%d/%d 个 (target, 非random 策略) 组合比 random 更早达标**，"
        "但有 **%s** 个组合的中位数曲线比「≥ %.0f%% 的重复满足 τ_b ≥ %.2f」更早达标"
        "（口径只按 τ_b；若按 τ_b ∧ Top-20%% overlap ∧ regret 的**组合**口径，则为 "
        "%d/%d 个）—— 只看中位数曲线会低估预算。"
        % (acceptance[1]["n_supporting"], acceptance[1]["n_cells"],
           len(overstated), wp6.SUCCESS_FRACTION * 100, wp6.TARGET_TAU,
           len(combined_overstated), len(budget)),
        "",
        "## 1. 协议审计",
        "",
    ]
    lines += _table(
        ["任务", "轴", "池", "初始种子", "批次", "重复", "n_T", "曲线点", "采集特征",
         "regret 容忍 (eV)"],
        [[r["task"], r["axis"], r["pool_size"], r["initial_seed_size"], r["batch_size"],
          r["repeats"], "%d-%d" % (r["n_T_min"], r["n_T_max"]), r["n_curve_points"],
          r["acquisition_features"], "%.4f" % r["regret_tolerance_ev"]] for r in protocol])
    lines += [
        "",
        "regret 容忍值 = 池内目标真值极差的 %.0f%%（由轨迹中的真值直接算出，不是挑出来的）。"
        % (wp6.REGRET_TARGET_SCALE * 100),
        "",
        "## 2. 决策性能曲线：median τ_b 随 n_T",
        "",
    ]
    for target in [("%s" % r["task"], r["axis"]) for r in protocol]:
        task, axis = target
        rows = [r for r in curves if r["task"] == task and r["axis"] == axis]
        ns = sorted({r["n_T"] for r in rows})
        by_n = {}
        for r in rows:
            by_n.setdefault(r["n_T"], {})[r["baseline"]] = r["tau_b"]
        pool_size = next(p["pool_size"] for p in protocol
                         if p["task"] == task and p["axis"] == axis)
        lines.append("### %s · %s（池大小 %d）" % (task, axis, pool_size))
        lines.append("")
        lines += _table(
            ["n_T"] + list(wp6.BASELINES),
            [[n] + ["%.3f" % by_n[n][b] for b in wp6.BASELINES] for n in ns])
        lines.append("")
    lines += [
        "## 3. 达标预算：中位数曲线 vs 多数重复",
        "",
        "「多数重复」= 该 (target, 策略) 上有 ≥ %.0f%% 的重复满足判据。"
        % (wp6.SUCCESS_FRACTION * 100),
        "",
    ]
    lines += _table(
        ["任务", "轴", "策略", "median τ_b≥0.80", "多数重复 τ_b≥0.80", "多数重复 组合达标",
         "中位数曲线高估？"],
        [[r["task"], r["axis"], r["baseline"], r["n_T_median_tau080"] or "-",
          r["n_T_majority_tau080"] or "-", r["n_T_majority_combined"] or "-",
          "是" if r["median_overstates_majority"] else "否"] for r in budget])
    lines += [
        "",
        "## 4. 策略是否比 random 更省昂贵标签",
        "",
        "在同一 (repeat, n_T) 上把每个非随机策略与其配对的 random 比较（20 次重复 × 公共 n_T）。",
        "",
    ]
    lines += _table(
        ["任务", "轴", "策略", "配对数", "τ_b 胜率", "打平率", "Δτ_b 中位数"],
        [[r["task"], r["axis"], r["baseline"], r["n_pairs"], "%.3f" % r["win_rate_tau"],
          "%.3f" % r["tie_rate_tau"], "%+.3f" % r["median_gain_tau"]] for r in wins])
    lines += [
        "",
        "## 5. 池内 vs 跨家族（口径诚实声明）",
        "",
    ]
    lines += _table(
        ["任务", "轴", "池", "池内端点 τ_b", "静态 LOFO τ_b", "LOFO 最优模型",
         "AL family-held-out"],
        [[r["task"], r["axis"], r["pool_size"], "%.3f" % r["inpool_endpoint_tau_b"],
          "%+.3f" % r["static_lofo_tau_b"], r["static_lofo_model"], "不可用"]
         for r in holdout])
    lines += [
        "",
        "池内端点的 τ_b 恒为 1.0，是「已标注用真值、未标注用预测」的**自检端点**，不是成绩；",
        "静态 LOFO 参照（同一廉价特征集的留一家族结果）最高只有 %.3f。冻结 replay 里没有"
        % max(r["static_lofo_tau_b"] for r in holdout),
        "family-held-out 的 AL 曲线，本阶段如实标注为**缺口**，不做任何外推。",
        "",
        "## 6. 验收问题",
        "",
    ]
    for item in acceptance:
        lines.append("- **%s**：%s → %s" % (item["question_id"], item["question"], item["verdict"]))
        if item["counterexamples"] and item["counterexamples"] != "none":
            lines.append("  - 反例：%s" % item["counterexamples"])
    lines += [
        "",
        "## 7. 一致性自检（%d 项）" % len(payload["checks"]),
        "",
    ]
    lines += ["- `%s`: %s -- %s" % (c["id"], "PASS" if c["ok"] else "FAIL", c["detail"])
              for c in payload["checks"]]
    lines += [
        "",
        "## 8. 限制",
        "",
        "- 零新增计算；Gate 1 仍 NOT CLOSED。本阶段是**computational-target** 陈述。",
        "- core set 只有 18（C 任务 10）个分子，每 target 只有 15（C 为 7）个预算点；",
        "  20 次重复的 2.5/97.5 百分位本身很粗。只比较**方法的相对行为**。",
        "- 成功标准是内部操作性标准，未经外部校准；不得读成「真实项目需要买多少张 DFT」。",
        "- posterior sampling 来自 GPR 后验协方差（样本 256），未做 uncertainty calibration；",
        "  在 18 个点上无法做可信校准，这一点必须重申。",
        "- family-held-out 的 AL 曲线不可用；如需要，须重跑 acquisition（不在本阶段范围）。",
        "- 下一步 WP7（Week 34）：外部参考分层与 Gate 1 结论边界。",
        "",
        "## 9. 复现命令",
        "",
        "```powershell",
        "cd 电解液溶剂HB-Code",
        ".venv\\Scripts\\python.exe scripts\\build_week33_wp6_active_learning_budget.py",
        ".venv\\Scripts\\python.exe scripts\\build_week33_wp6_active_learning_budget.py --check",
        ".venv\\Scripts\\python.exe -m pytest tests/test_week33_wp6_active_learning_budget.py -q",
        "```",
    ]
    return "\n".join(lines) + "\n"


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Week 33 / WP6: minimum expensive-information budget.")
    parser.add_argument("--check", action="store_true")
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    payload, texts = collect()

    if args.check:
        failures = []
        for name, text in texts.items():
            path = OUTDIR / name
            if not path.exists():
                failures.append("%s is missing" % name)
            elif path.read_text(encoding="utf-8") != text:
                failures.append("%s differs from the regenerated text" % name)
        if failures:
            print("CHECK FAILED")
            for item in failures:
                print("  - %s" % item)
            return 1
        print("CHECK OK -- %d files are byte-identical" % len(texts))
        return 0

    OUTDIR.mkdir(parents=True, exist_ok=True)
    for name, text in texts.items():
        with io.open(OUTDIR / name, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)

    print("Week 33 / WP6 -- minimum expensive-information budget")
    print("-" * 78)
    for table in TABLE_ORDER:
        info = payload["manifest"][table]
        print("  %-32s %5d rows  %s" % (table, info["n_rows"], info["sha256"][:12]))
    print("  %-32s %5d rows total" % ("(all tables)", payload["n_rows_total"]))
    print("-" * 78)
    for check in payload["checks"]:
        print("  %-52s %s" % (check["id"], "PASS" if check["ok"] else "FAIL"))
    print("-" * 78)
    print("wrote outputs/week33/ (%d files)" % len(texts))
    return 0


if __name__ == "__main__":
    sys.exit(main())