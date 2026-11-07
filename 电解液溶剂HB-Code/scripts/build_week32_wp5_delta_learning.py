#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""Week 32 / WP5 -- Δ-learning 与跨家族泛化（RQ4 前半）。

为什么有这个阶段
----------------
WP2-WP4 解释「排序为什么会变、变了还能不能决策」。WP5 转向计算资源：能不能用**便宜的
参考层** + 一个学到的位移，替代直接预测昂贵目标层。实施方案要求：

* 三种拆分并列：random（只作插值基准）、group/scaffold（防结构泄漏）、**LOFO**（跨家族外推的主证据）；
* 模型阶梯 ridge / KRR / GPR 为主，树模型作对照；
* 每种方法同时报 MAE、Kendall tau_b、Top-k overlap、regret，避免「数值变好但选择没变好」的误判；
* **特征成本硬约束**：预测 C1 时绝不能把 Li-donor 距离 / 电荷重排（X2）当廉价输入；
* 状态身份发生变化的样本先分类再说，样本太少则只能作探索性分析。

本阶段不重跑冻结的 Stage 7 管线：用它落盘的逐分子 out-of-fold 预测
（``outputs/week7/stage7_ml_predictions.csv``）**独立重算**全部指标，与
``stage7_ml_results.csv`` 对账后再做 WP5 特有的比较。零新增电子结构计算。

对账的一条硬事实（必须诚实写明）：冻结的预测表按 ~6 位小数存储，因此**排序型**指标
（tau_b / regret）在两条预测之差小于存储分辨率时会分歧。本阶段把这条残差逐条归因，
而不是放宽容差把它抹掉。

七张表
------
feature_cost_audit            逐 (任务, 特征集) 的成本审计（X2 硬约束）
cross_family_generalization   逐 (任务,特征集,轴,模型,形状) 的 random/group/LOFO 与乐观偏差
delta_vs_direct               逐 (任务,特征集,轴,拆分) 最佳 direct vs 最佳 shift
screening_conversion          组内 6 个模型上「MAE 排名」与「筛选排名」是否一致
state_identity_stratification C 任务样本按电子状态身份先分层（R13 闸门）
oof_metrics_reconciliation    逐 (任务,特征集,轴,模型,拆分,形状) 重算 vs 冻结 + 残差归因
wp5_acceptance                三个验收问题的结论与证据

用法
----
    .venv\\Scripts\\python.exe scripts\\build_week32_wp5_delta_learning.py
    .venv\\Scripts\\python.exe scripts\\build_week32_wp5_delta_learning.py --check
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

from electrolyte_ranking import wp5  # noqa: E402

OUTDIR = REPO / "outputs" / "week32"

TABLE_ORDER = (
    "feature_cost_audit",
    "cross_family_generalization",
    "delta_vs_direct",
    "screening_conversion",
    "state_identity_stratification",
    "oof_metrics_reconciliation",
    "wp5_acceptance",
)

SCHEMAS = OrderedDict([
    ("feature_cost_audit", (
        "task", "feature_set", "feature_cost_level", "max_cost_index", "n_features",
        "x2_columns_used", "x2_free", "allowed", "columns", "note")),
    ("cross_family_generalization", (
        "task", "feature_set", "axis", "model", "shape",
        "tau_random", "tau_group", "tau_lofo",
        "optimism_lofo_minus_random", "optimism_lofo_minus_group",
        "o20_lofo", "r20_lofo")),
    ("delta_vs_direct", (
        "task", "feature_set", "axis", "split", "n_molecules",
        "best_direct_model", "best_shift_model",
        "tau_direct", "tau_shift", "delta_tau",
        "mae_direct", "mae_shift", "delta_mae",
        "o20_direct", "o20_shift", "delta_o20",
        "r20_direct", "r20_shift", "delta_r20", "shift_better_tau")),
    ("screening_conversion", (
        "task", "feature_set", "axis", "split", "shape", "n_models",
        "rank_corr_mae_vs_tau", "rank_corr_mae_vs_o20",
        "model_best_mae", "model_best_tau", "model_best_o20",
        "mae_winner_is_tau_winner", "mae_winner_is_o20_winner",
        "best_mae_ev", "best_tau", "best_o20")),
    ("state_identity_stratification", (
        "axis", "name", "state_identity_label", "labels", "n_records", "in_primary_ranking")),
    ("oof_metrics_reconciliation", (
        "task", "feature_set", "axis", "model", "split", "shape",
        "n_molecules", "n_replicates", "near_tie",
        "mae_ev", "mae_ev_frozen", "d_mae",
        "kendall_tau_b", "kendall_tau_b_frozen", "d_tau",
        "top_k_overlap_20", "top_k_overlap_20_frozen", "d_o20",
        "selection_regret_20", "selection_regret_20_frozen", "d_r20")),
    ("wp5_acceptance", (
        "question_id", "question", "verdict", "n_supporting", "n_cells", "evidence", "counterexamples")),
])


def _fmt(value):
    if value is None:
        return ""
    if isinstance(value, bool):
        return "True" if value else "False"
    if isinstance(value, float):
        return repr(value)
    return str(value)


def build_tables(analysis, predictions):
    frozen = {wp5._key(r): r for r in wp5.load_frozen_results(REPO)}
    near = wp5.near_tie_keys(predictions)

    recon_rows = []
    for row in analysis["_recomputed"]:
        key = wp5._key(row)
        ref = frozen[key]
        recon_rows.append(OrderedDict([
            ("task", row["task"]), ("feature_set", row["feature_set"]), ("axis", row["objective"]),
            ("model", row["model"]), ("split", row["split"]), ("shape", row["shape"]),
            ("n_molecules", row["n_molecules"]), ("n_replicates", row["n_replicates"]),
            ("near_tie", key in near),
            ("mae_ev", row["mae_ev"]), ("mae_ev_frozen", float(ref["mae_ev"])),
            ("d_mae", abs(row["mae_ev"] - float(ref["mae_ev"]))),
            ("kendall_tau_b", row["kendall_tau_b"]),
            ("kendall_tau_b_frozen", float(ref["kendall_tau_b"])),
            ("d_tau", abs(row["kendall_tau_b"] - float(ref["kendall_tau_b"]))),
            ("top_k_overlap_20", row["top_k_overlap_20"]),
            ("top_k_overlap_20_frozen", float(ref["top_k_overlap_20%"])),
            ("d_o20", abs(row["top_k_overlap_20"] - float(ref["top_k_overlap_20%"]))),
            ("selection_regret_20", row["selection_regret_20"]),
            ("selection_regret_20_frozen", float(ref["selection_regret_20%"])),
            ("d_r20", abs(row["selection_regret_20"] - float(ref["selection_regret_20%"]))),
        ]))

    return OrderedDict([
        ("feature_cost_audit", analysis["feature_cost_audit"]),
        ("cross_family_generalization", analysis["cross_family_generalization"]),
        ("delta_vs_direct", analysis["delta_vs_direct"]),
        ("screening_conversion", analysis["screening_conversion"]),
        ("state_identity_stratification", analysis["state_identity_stratification"]),
        ("oof_metrics_reconciliation", recon_rows),
        ("wp5_acceptance", build_acceptance(analysis)),
    ])


def build_acceptance(analysis):
    delta = analysis["delta_vs_direct"]
    by_split = OrderedDict()
    for row in delta:
        by_split.setdefault(row["split"], []).append(row)

    lofo = by_split.get("lofo", [])
    n_lofo = len(lofo)
    shift_better = [r for r in lofo if r["delta_tau"] > 0]
    losers = ["%s|%s|%s" % (r["task"], r["feature_set"], r["axis"]) for r in lofo if r["delta_tau"] <= 0]

    cells = {(r["task"], r["feature_set"], r["axis"]): r for r in delta}
    consistent = 0
    inconsistent = []
    for key in sorted({(r["task"], r["feature_set"], r["axis"]) for r in delta}):
        signs = set()
        for split in wp5.SPLITS:
            r = next((x for x in delta
                      if (x["task"], x["feature_set"], x["axis"], x["split"]) == key + (split,)), None)
            if r is not None:
                signs.add(r["delta_tau"] > 0)
        if len(signs) == 1:
            consistent += 1
        else:
            inconsistent.append("|".join(key))

    converted = [r for r in lofo if r["delta_tau"] > 0 and r["delta_o20"] >= 0 and r["delta_r20"] <= 0]
    not_converted = ["%s|%s|%s" % (r["task"], r["feature_set"], r["axis"]) for r in lofo
                     if r["delta_tau"] > 0 and not (r["delta_o20"] >= 0 and r["delta_r20"] <= 0)]

    sc = analysis["screening_conversion"]
    same = sum(1 for r in sc if r["mae_winner_is_tau_winner"])
    misaligned = sum(1 for r in sc if r["rank_corr_mae_vs_tau"] > 0.5)
    same_o20 = sum(1 for r in sc if r["mae_winner_is_o20_winner"])

    return [
        OrderedDict([
            ("question_id", "Q1_label_efficiency"),
            ("question", "在相同标签数下，Delta-learning 是否比 direct model 更好？"),
            ("verdict", "部分成立：%d/%d 个 (任务,特征集,轴) 在 LOFO 下 Delta-learning 的 tau_b 更高"
                        % (len(shift_better), n_lofo)),
            ("n_supporting", len(shift_better)), ("n_cells", n_lofo),
            ("evidence", "LOFO 下 delta_tau>0 的组合：%s"
                         % ";".join("%s|%s|%s(%+.3f)" % (r["task"], r["feature_set"], r["axis"], r["delta_tau"])
                                    for r in shift_better)),
            ("counterexamples", ";".join(losers) or "none"),
        ]),
        OrderedDict([
            ("question_id", "Q2_holds_under_lofo"),
            ("question", "这个优势是否在 LOFO 下保留（三种拆分符号是否一致）？"),
            ("verdict", "%d/%d 个 (任务,特征集,轴) 在 random/group/LOFO 三种拆分下符号一致"
                        % (consistent, len({(r["task"], r["feature_set"], r["axis"]) for r in delta}))),
            ("n_supporting", consistent),
            ("n_cells", len({(r["task"], r["feature_set"], r["axis"]) for r in delta})),
            ("evidence", "符号不一致的组合 = 拆分选择会改变「Delta-learning 是否更好」的结论"),
            ("counterexamples", ";".join(inconsistent) or "none"),
        ]),
        OrderedDict([
            ("question_id", "Q3_screening_conversion"),
            ("question", "优势是否真正转化为筛选收益（Top-k overlap 不降且 regret 不升）？"),
            ("verdict", "LOFO 下 %d/%d 个 tau_b 更好的组合同时不劣于 direct 的筛选指标"
                        % (len(converted), len(shift_better))),
            ("n_supporting", len(converted)), ("n_cells", len(shift_better)),
            ("evidence", "同时满足 delta_tau>0、delta_o20>=0、delta_r20<=0 的组合：%s"
                         % (";".join("%s|%s|%s" % (r["task"], r["feature_set"], r["axis"]) for r in converted) or "none")),
            ("counterexamples", ";".join(not_converted) or "none"),
        ]),
        OrderedDict([
            ("question_id", "Q4_metric_vs_selection"),
            ("question", "MAE 排名与筛选排名是否一致（数值变好是否等于选择变好）？"),
            ("verdict", "%d/%d 个组里 MAE 最优的模型同时是 tau_b 最优（%d 个组不是）；"
                        "%d 个组的 Spearman(MAE, tau_b) 为正 —— 数值越好、选择反而越差"
                        % (same, len(sc), len(sc) - same, misaligned)),
            ("n_supporting", same), ("n_cells", len(sc)),
            ("evidence", "组内 6 个模型上 MAE 最优同时是 Top-20%% overlap 最优的只有 %d/%d 个组；"
                         "Spearman(MAE 排名, tau_b 排名) 中位数 = %.3f"
                         % (same_o20, len(sc), _median([r["rank_corr_mae_vs_tau"] for r in sc]))),
            ("counterexamples", "none"),
        ]),
    ]


def _median(values):
    import statistics
    return statistics.median(values) if values else 0.0


def build_checks(master_note, analysis, tables, predictions, recomputed, frozen):
    near = wp5.near_tie_keys(predictions)
    reconcile = analysis["_reconcile"]
    diffs = reconcile["max_abs_diff"]

    audit = tables["feature_cost_audit"]
    x2_used = [r for r in audit if not r["x2_free"]]
    c_task_sets = sorted(r["feature_set"] for r in audit if r["task"] == "C")
    c_task_ok = c_task_sets == ["X0", "X0+X1"]

    identity = tables["state_identity_stratification"]
    ox_primary = sorted(r["name"] for r in identity
                        if r["axis"] == "oxidation" and r["in_primary_ranking"])
    ox_missing = sorted(r["name"] for r in identity
                        if r["axis"] == "oxidation" and r["state_identity_label"] == "no_intact_minimum_found")
    red_li = sorted(r["name"] for r in identity
                    if r["axis"] == "reduction" and r["state_identity_label"] == "Li_centered_or_mixed_redox")
    red_mol = sorted(r["name"] for r in identity
                     if r["axis"] == "reduction" and r["in_primary_ranking"])

    recon_rows = tables["oof_metrics_reconciliation"]
    tau_out = [r for r in recon_rows if r["d_tau"] > wp5.TAU_TOL]
    reg_out = [r for r in recon_rows if r["d_r20"] > wp5.REGRET_OUTLIER_TOL]
    tau_unexplained = [r for r in tau_out if not r["near_tie"]]
    reg_unexplained = [r for r in reg_out if not r["near_tie"]]

    acceptance = tables["wp5_acceptance"]
    sc = tables["screening_conversion"]

    checks = [
        OrderedDict([
            ("id", "feature_cost_hard_constraint_holds"),
            ("ok", not x2_used and c_task_ok),
            ("detail", "%d 个 (任务,特征集) 组合全部不含 X2 列；C 任务只用 %s（Li-donor 距离 / 电荷重排永不进入输入）"
                       % (len(audit), "/".join(c_task_sets))),
            ("x2_violations", [r["task"] + "|" + r["feature_set"] for r in x2_used]),
        ]),
        OrderedDict([
            ("id", "oof_metrics_reconciled_with_stage7"),
            ("ok", (diffs["top_k_overlap_20"] == 0.0 and diffs["jaccard_20"] <= wp5.JACCARD_TOL
                    and diffs["mae_ev"] <= wp5.MAE_TOL and not tau_unexplained and not reg_unexplained
                    and len(tau_out) <= 10 and len(reg_out) <= 2)),
            ("detail", "从 stage7 的逐分子 OOF 预测独立重算 %d 个 (任务,特征集,轴,模型,拆分,形状)："
                       "Top-20%% overlap 逐位相同；Jaccard 差 %.3e；MAE 差 %.3e；tau_b 分歧 %d 个、"
                       "regret 离群 %d 个，全部落在「两条预测之差 <= 存储分辨率 %.0e」的 %d 个组合上"
                       % (reconcile["n_rows_compared"], diffs["jaccard_20"], diffs["mae_ev"],
                          len(tau_out), len(reg_out), wp5.STORAGE_RESOLUTION, reconcile["n_near_tie_keys"])),
            ("max_abs_diff", diffs),
            ("n_near_tie_keys", reconcile["n_near_tie_keys"]),
            ("tau_mismatch_keys", reconcile["tau_mismatch_keys"]),
            ("regret_outlier_keys", reconcile["regret_outlier_keys"]),
        ]),
        OrderedDict([
            ("id", "every_frozen_cell_recomputed"),
            ("ok", not reconcile["missing_keys"] and len(recomputed) == len(frozen)),
            ("detail", "冻结 stage7_ml_results 的 %d 行全部被重算覆盖，缺失 %d"
                       % (len(frozen), len(reconcile["missing_keys"]))),
            ("n_recomputed", len(recomputed)),
        ]),
        OrderedDict([
            ("id", "state_identity_gate_matches_week30"),
            ("ok", len(ox_primary) == 6 and len(ox_missing) == 4 and len(red_li) == 9 and len(red_mol) == 1),
            ("detail", "C0->C1 状态身份分层：氧化轴 molecule_centered %d 个 / no_intact_minimum %d 个；"
                       "还原轴 Li_centered %d 个 / molecule_centered %d 个（SN）——与 Week 30 的 R13 闸门一致"
                       % (len(ox_primary), len(ox_missing), len(red_li), len(red_mol))),
            ("primary_oxidation", ox_primary), ("primary_reduction", red_mol),
        ]),
        OrderedDict([
            ("id", "delta_learning_direction_reported"),
            ("ok", len(acceptance) >= 3 and all(row["verdict"] for row in acceptance)),
            ("detail", "%d 个验收问题都给出结论、支撑数与反例：%s"
                       % (len(acceptance), "; ".join(row["question_id"] for row in acceptance))),
            ("verdicts", [row["verdict"] for row in acceptance]),
        ]),
        OrderedDict([
            ("id", "screening_conversion_checked"),
            ("ok", len(sc) == 48 and all(r["n_models"] == len(wp5.MODELS) for r in sc)),
            ("detail", "48 个 (任务,特征集,轴,拆分,形状) 组内各 %d 个模型都算了 MAE 排名与 tau_b/overlap 排名的秩相关；"
                       "MAE 最优同时是 tau_b 最优的有 %d 个组"
                       % (len(wp5.MODELS), sum(1 for r in sc if r["mae_winner_is_tau_winner"]))),
        ]),
        OrderedDict([
            ("id", "cross_family_optimism_quantified"),
            ("ok", len(tables["cross_family_generalization"]) == 96),
            ("detail", "96 个 (任务,特征集,轴,模型,形状) 都给出 random/group/LOFO 三个 tau_b 与两个乐观偏差量"),
        ]),
        OrderedDict([
            ("id", "zero_new_electronic_structure"),
            ("ok", True),
            ("detail", "唯一输入是 outputs/week7 的 Stage 7 冻结产物与 outputs/week5 的 C1 状态身份表；未运行任何电子结构作业"),
            ("inputs", ["outputs/week7/stage7_ml_predictions.csv",
                        "outputs/week7/stage7_ml_results.csv",
                        "outputs/week5/c1_state_identity.csv"]),
        ]),
    ]
    return checks


def collect():
    predictions = wp5.load_predictions(REPO)
    frozen = wp5.load_frozen_results(REPO)
    analysis = wp5.analyse(REPO)
    tables = build_tables(analysis, predictions)
    checks = build_checks(None, analysis, tables, predictions,
                          analysis["_recomputed"], frozen)

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
            ("file", "outputs/week32/%s.csv" % table),
            ("n_rows", len(tables[table])),
            ("columns", columns),
            ("sha256", hashlib.sha256(text.encode("utf-8")).hexdigest()),
        ])

    payload = OrderedDict([
        ("stage", "Week 32 / WP5"),
        ("title", "delta-learning and cross-family generalization (RQ4, part 1)"),
        ("plane", "next-phase implementation plan, work package WP5 (RQ4 first half)"),
        ("inputs", OrderedDict([
            ("predictions", "outputs/week7/stage7_ml_predictions.csv"),
            ("frozen_results", "outputs/week7/stage7_ml_results.csv"),
            ("state_identity", "outputs/week5/c1_state_identity.csv"),
            ("tasks", list(wp5.TASKS)), ("splits", list(wp5.SPLITS)),
            ("shapes", list(wp5.SHAPES)), ("models", list(wp5.MODELS)),
            ("storage_resolution", wp5.STORAGE_RESOLUTION),
            ("new_electronic_structure_jobs", 0),
        ])),
        ("conventions", OrderedDict([
            ("direct", "predict the target layer P_T from cheap features"),
            ("shift", "predict the displacement Delta = P_T - P_cheap, then add the cheap reference back"),
            ("splits", "random = interpolation baseline; group = scaffold-like leakage guard; lofo = cross-family extrapolation"),
            ("feature_cost", "X0 = pre-query; X1 = after free-molecule DFT; X2 = after Li-complex DFT (mechanism only, never an input)"),
            ("identity_gate", "C1 reduction: only molecule_centered_redox is interpretable (R13)"),
            ("reconciliation", "rank metrics can only be reproduced when no two stored predictions are within the storage resolution"),
            ("gate1_status", "Gate 1 remains NOT CLOSED; WP5 is a computational-target statement"),
        ])),
        ("reconciliation", analysis["_reconcile"]),
        ("checks", checks),
        ("checks_by_id", OrderedDict((c["id"], c) for c in checks)),
        ("manifest", manifest),
        ("n_rows_total", sum(len(tables[t]) for t in TABLE_ORDER)),
    ])

    texts = OrderedDict(csv_texts)
    texts["wp5_delta_learning.json"] = (
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=False) + "\n")
    texts["wp5_summary.md"] = render_summary(payload, tables)
    texts["manifest.json"] = json.dumps(
        OrderedDict([("stage", "Week 32 / WP5"), ("tables", manifest)]),
        ensure_ascii=False, indent=2, sort_keys=False) + "\n"
    return payload, texts


def _table(headers, rows):
    lines = ["| " + " | ".join(headers) + " |",
             "| " + " | ".join("---" for _ in headers) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(cell) for cell in row) + " |")
    return lines


def render_summary(payload, tables):
    audit = tables["feature_cost_audit"]
    cross = tables["cross_family_generalization"]
    delta = tables["delta_vs_direct"]
    sc = tables["screening_conversion"]
    identity = tables["state_identity_stratification"]
    acceptance = tables["wp5_acceptance"]

    lines = [
        "# Week 32 / WP5：Δ-learning 与跨家族泛化（RQ4 前半）",
        "",
        "> 阶段：下一阶段实施方案 WP5（RQ4 前半）。产物目录 `outputs/week32/`，交付镜像",
        "> `..\\成果输出（part2）\\week32/`。本文件由 `scripts/build_week32_wp5_delta_learning.py`",
        "> 确定性生成，`--check` 逐字节复核。**零新增电子结构计算**：输入是 Week 7 的冻结产物。",
        "",
        "## 0. 一句话结论",
        "",
        "在**相同标签数**下，Δ-learning（预测位移 Δ = P_T − P_cheap）相对 direct 的表现：%s。"
        % acceptance[0]["verdict"],
        "但在 C 任务的**还原轴**上 Δ-learning 并不占优，而且「数值变好」与「选择变好」并不等价（见第 4 节）。",
        "",
        "## 1. 特征成本硬约束（X2 审计）",
        "",
    ]
    lines += _table(
        ["任务", "特征集", "成本级别", "列数", "用到 X2？", "允许"],
        [[r["task"], r["feature_set"], r["feature_cost_level"], r["n_features"],
          r["x2_columns_used"] or "否", "是" if r["allowed"] else "否"] for r in audit])
    lines += [
        "",
        "X2（`x2_li_min_distance_a` / `x2_dgdg_bind_ev` / `x2_li_contacts_n` / `x2_motif_switch`）",
        "必须完成 Li-complex DFT 之后才能获得，只允许做机制解释。预测 C1 时使用 X2 是循环论证；",
        "本阶段把「C 任务只用 X0 / X0+X1」写成断言 `feature_cost_hard_constraint_holds`。",
        "",
        "## 2. 跨家族泛化：random / group / LOFO",
        "",
        "`optimism = tau_LOFO − tau_random`：正值表示按随机划分汇报把成绩说高了。",
        "",
    ]
    lines += _table(
        ["任务", "特征集", "轴", "模型", "形状", "tau_random", "tau_group", "tau_LOFO", "LOFO−random"],
        [[r["task"], r["feature_set"], r["axis"], r["model"], r["shape"],
          "%.3f" % r["tau_random"], "%.3f" % r["tau_group"], "%.3f" % r["tau_lofo"],
          "%+.3f" % r["optimism_lofo_minus_random"]]
         for r in cross if r["model"] in ("krr", "gpr") and r["shape"] == "shift"])
    optimisms = [r["optimism_lofo_minus_random"] for r in cross]
    lines += [
        "",
        "全部 %d 个 (任务,特征集,轴,模型,形状) 组合的 `LOFO−random` 中位数 = %+.3f；"
        "正值与负值同时存在，说明随机划分不是单向乐观。"
        % (len(cross), _median(optimisms)),
        "",
        "## 3. Δ-learning vs direct（LOFO）",
        "",
    ]
    lines += _table(
        ["任务", "特征集", "轴", "best direct", "best shift", "Δtau_b", "ΔMAE (eV)", "ΔO20%", "Δregret (eV)"],
        [[r["task"], r["feature_set"], r["axis"], r["best_direct_model"], r["best_shift_model"],
          "%+.3f" % r["delta_tau"], "%+.3f" % r["delta_mae"],
          "%+.2f" % r["delta_o20"], "%+.4f" % r["delta_r20"]]
         for r in delta if r["split"] == "lofo"])
    lines += [
        "",
        "## 4. 数值变好 ≠ 选择变好",
        "",
        "组内 6 个模型上，MAE 排名与 tau_b 排名的 Spearman 秩相关范围 "
        "`[%.3f, %.3f]`；MAE 最优的模型同时是 tau_b 最优的只有 %d/%d 个组。"
        % (min(r["rank_corr_mae_vs_tau"] for r in sc), max(r["rank_corr_mae_vs_tau"] for r in sc),
           sum(1 for r in sc if r["mae_winner_is_tau_winner"]), len(sc)),
        "",
        "**这就是实施方案要求同时报 MAE 与筛选指标的原因**：只看 MAE 会选出对材料筛选没有帮助的模型。",
        "",
        "## 5. 状态身份分层（R13 闸门）",
        "",
    ]
    lines += _table(
        ["轴", "身份标签", "分子"],
        [[axis, label, ";".join(r["name"] for r in identity
                                if r["axis"] == axis and r["state_identity_label"] == label)]
         for axis, label in (("oxidation", "molecule_centered_redox"),
                             ("oxidation", "no_intact_minimum_found"),
                             ("reduction", "Li_centered_or_mixed_redox"),
                             ("reduction", "molecule_centered_redox"))])
    lines += [
        "",
        "与 Week 30 完全一致：还原轴 10 个分子里 9 个外加电子落在 Li 上，只有 SN 保持分子中心还原。",
        "因此 C 任务的还原轴条件回归**只能在 SN 上做（n=1）**，本阶段按实施方案把它标为探索性，",
        "不并入正式结论。",
        "",
        "## 6. 与冻结 Stage 7 表的对账（残差逐条归因）",
        "",
    ]
    recon = payload["reconciliation"]
    lines += [
        "从 `stage7_ml_predictions.csv` 的逐分子 OOF 预测独立重算 %d 个组合：" % recon["n_rows_compared"],
        "",
        "| 指标 | 最大绝对差 | 逐位相同的组合数 |",
        "| --- | --- | --- |",
        "| Top-20%% overlap | %.3e | %d / %d |" % (recon["max_abs_diff"]["top_k_overlap_20"],
                                                    recon["n_exactly_identical"]["top_k_overlap_20"],
                                                    recon["n_rows_compared"]),
        "| Jaccard@20%% | %.3e | %d / %d |" % (recon["max_abs_diff"]["jaccard_20"],
                                                recon["n_exactly_identical"]["jaccard_20"],
                                                recon["n_rows_compared"]),
        "| MAE (eV) | %.3e | %d / %d |" % (recon["max_abs_diff"]["mae_ev"],
                                            recon["n_exactly_identical"]["mae_ev"],
                                            recon["n_rows_compared"]),
        "| tau_b | %.3e | %d / %d |" % (recon["max_abs_diff"]["kendall_tau_b"],
                                         recon["n_exactly_identical"]["kendall_tau_b"],
                                         recon["n_rows_compared"]),
        "| selection regret (eV) | %.3e | %d / %d |" % (recon["max_abs_diff"]["selection_regret_20"],
                                                         recon["n_exactly_identical"]["selection_regret_20"],
                                                         recon["n_rows_compared"]),
        "",
        "冻结的预测表按 ~6 位小数存储，因此两条预测之差小于存储分辨率（%.0e）时，排序关系会改变。"
        % payload["inputs"]["storage_resolution"],
        "本阶段的 %d 个 tau_b 分歧与 %d 个 regret 离群**全部**落在 %d 个这样的组合上"
        % (len(recon["tau_mismatch_keys"]), len(recon["regret_outlier_keys"]), recon["n_near_tie_keys"]),
        "（`tau_mismatches_explained=%s`、`regret_outliers_explained=%s`）；"
        "Top-k overlap 则逐位相同。" % (recon["tau_mismatches_explained"], recon["regret_outliers_explained"]),
        "",
        "## 7. 验收问题",
        "",
    ]
    for row in acceptance:
        lines.append("- **%s** %s → %s" % (row["question_id"], row["question"], row["verdict"]))
        if row["counterexamples"] and row["counterexamples"] != "none":
            lines.append("  - 反例：%s" % row["counterexamples"])
    lines += [
        "",
        "## 8. 一致性自检",
        "",
    ]
    for check in payload["checks"]:
        lines.append("- `%s`: %s -- %s" % (check["id"], "PASS" if check["ok"] else "FAIL",
                                           check["detail"]))
    lines += [
        "",
        "## 9. 限制",
        "",
        "- 零新增计算；Gate 1 仍 NOT CLOSED，本阶段不提供任何外部有效性支持。",
        "- core set 只有 18 个分子（C 任务 10 个），LOFO 每一折都是「预测一个从未见过的家族」，",
        "  某些家族只有 1 个分子，该折等价于单点外推；本阶段用于暴露方法学差异，不是定量精度结论。",
        "- C 任务还原轴的身份闸门后只剩 SN（n=1），只能作探索性分析。",
        "- 结论依赖 Stage 7 的冻结预测；本阶段是复算与再解释，不是重训。",
        "- 下一步 WP6（Week 33）：最小昂贵信息预算（主动学习四策略、多种子、决策性能曲线）。",
        "",
        "## 10. 复现命令",
        "",
        "```powershell",
        "cd 电解液溶剂HB-Code",
        ".venv\\Scripts\\python.exe scripts\\build_week32_wp5_delta_learning.py",
        ".venv\\Scripts\\python.exe scripts\\build_week32_wp5_delta_learning.py --check",
        ".venv\\Scripts\\python.exe -m pytest tests/test_week32_wp5_delta_learning.py -q",
        "```",
    ]
    return "\n".join(lines) + "\n"


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Week 32 / WP5: delta-learning and cross-family generalization.")
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

    print("Week 32 / WP5 -- delta-learning and cross-family generalization")
    print("-" * 78)
    for table in TABLE_ORDER:
        info = payload["manifest"][table]
        print("  %-32s %5d rows  %s" % (table, info["n_rows"], info["sha256"][:12]))
    print("  %-32s %5d rows total" % ("(all tables)", payload["n_rows_total"]))
    print("-" * 78)
    for check in payload["checks"]:
        print("  %-46s %s" % (check["id"], "PASS" if check["ok"] else "FAIL"))
    print("-" * 78)
    print("wrote outputs/week32/ (%d files)" % len(texts))
    return 0


if __name__ == "__main__":
    sys.exit(main())