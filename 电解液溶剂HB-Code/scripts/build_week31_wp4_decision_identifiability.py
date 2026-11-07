#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""Week 31 / WP4 -- 把排序变化转成可辩护的筛选决策（RQ3）。

为什么有这个阶段
----------------
WP2 回答「哪些物理改变排序」，WP3 回答「Li+ 配位怎样改变机理」。WP4 处理的是
真正决定这套分析有没有用的那一步：**面对一次材料筛选决策，我们到底知道多少**。

实施方案要求三套并列分析，而不是只依赖 f_robust_inv::

    A 原始排序   : 不附加不确定性阈值，报告所有 rank change；
    B 可识别性   : resolution curve f_unresolved(z)、pairwise probability、结构性不可检验；
    C 决策稳健性 : 候选分数在模型歧义区间内扰动时，Top-k 集合与 regret 如何变化。

并特别处理 Week 27 的代数发现：在 sigma_ij = |d_lower - d_upper| / sqrt(2) 的约定下，
只要 z > 1/sqrt(2)，反向 pair 就无法两侧同时通过稳健判据 —— 必须标注为
*structurally non-testable*，不能当成「零稳健反转」的正向支持证据。

七张表
------
resolution_curve           逐 (组, z) 的 f_unresolved（lower / upper）
identifiability_summary    三层评价汇总 + 与 Week 28 冻结值逐位对账
structural_nontestability  逐 (组, z) 的反向 pair / 稳健反转计数（暴露代数必然性）
raw_ranking_changes        Case A：无阈值的原始排序变化
selection_uncertainty      Case C：歧义区间抽样下的 Top-k 稳定性与 selection uncertainty
stratification_sensitivity S1（score-lexicographic）vs S2（conservative）分层算法敏感性
decision_classes           验收交付表：每个候选 = 确定选择 / 边界候选 / 证据不足

零新增电子结构计算：唯一输入是 ``outputs/week28/*.csv``。

用法
----
    .venv\\Scripts\\python.exe scripts\\build_week31_wp4_decision_identifiability.py
    .venv\\Scripts\\python.exe scripts\\build_week31_wp4_decision_identifiability.py --check
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

from electrolyte_ranking import wp4  # noqa: E402

OUTDIR = REPO / "outputs" / "week31"

TABLE_ORDER = (
    "resolution_curve",
    "identifiability_summary",
    "structural_nontestability",
    "raw_ranking_changes",
    "selection_uncertainty",
    "stratification_sensitivity",
    "decision_classes",
)

SCHEMAS = OrderedDict([
    ("resolution_curve", (
        "comparison", "scope", "axis", "common_set_label", "n_pairs", "z",
        "f_unresolved_lower", "f_unresolved_upper")),
    ("identifiability_summary", (
        "comparison", "scope", "axis", "common_set_label", "n_molecules", "n_pairs",
        "kendall_tau_b", "spearman_rho",
        "f_unresolved_lower_z1", "f_unresolved_upper_z1", "decisive_pair_fraction",
        "k_fraction", "k", "overlap", "jaccard", "selection_regret_ev",
        "selection_uncertainty_mean_overlap",
        "n_sign_reverse", "n_robust_inversion_z1", "n_pairs_structurally_non_testable",
        "frozen_overlap", "frozen_jaccard", "frozen_regret_ev",
        "frozen_kendall_tau_b", "frozen_spearman_rho",
        "frozen_f_unresolved_lower_z1", "frozen_f_unresolved_upper_z1")),
    ("structural_nontestability", (
        "comparison", "scope", "axis", "n_pairs", "z", "n_sign_reverse",
        "n_both_resolved_given_reverse", "n_robust_inversion", "f_robust_inversion",
        "structurally_non_testable")),
    ("raw_ranking_changes", (
        "comparison", "scope", "axis", "common_set_label", "n_molecules", "n_pairs",
        "n_sign_reverse", "n_pair_zero_lower", "n_pair_zero_upper",
        "max_abs_d_lower_ev", "mean_abs_d_lower_ev",
        "n_concordant", "n_discordant", "n_tied",
        "kendall_tau_b", "spearman_rho", "top_k_overlap_k0p2")),
    ("selection_uncertainty", (
        "comparison", "scope", "axis", "common_set_label", "n_molecules",
        "k_fraction", "k", "selected_upper", "selected_lower",
        "overlap", "jaccard", "selection_regret_ev",
        "stability_upper", "stability_lower", "mean_overlap_with_upper",
        "ci_low_overlap_with_upper", "ci_high_overlap_with_upper",
        "n_certain", "n_boundary", "n_never",
        "frozen_overlap", "frozen_jaccard", "frozen_regret_ev",
        "frozen_selected_upper", "frozen_selected_lower")),
    ("stratification_sensitivity", (
        "comparison", "scope", "axis", "common_set_label", "n_molecules",
        "k_fraction", "k", "S1", "S2", "S2_size", "S2_shortfall",
        "overlap_count", "overlap_fraction_of_k", "symdiff_names",
        "sets_differ", "S2_subset_of_S1")),
    ("decision_classes", (
        "comparison", "scope", "axis", "common_set_label", "k_fraction", "k",
        "name", "p_selected", "in_S_upper", "in_S_lower", "in_S2",
        "decision_class", "reason", "n_unresolved_vs_selected")),
])

#: 三个独立复核（Archimedes / Meitner / Banach）落盘的锚点，用于逐位对账。
INDEPENDENT_REVIEW = OrderedDict([
    ("reviewers", ["A_resolution", "B_robustness", "C_stratify"]),
    ("resolution_curve_anchor", OrderedDict([
        ("group", "C0_to_C1|all|reduction"), ("z", 1.0),
        ("f_unresolved_lower", 0.4444444444444444),
        ("f_unresolved_upper", 0.8),
    ])),
    ("mc_anchor", OrderedDict([
        ("group", "P0_to_P1v|all|oxidation"), ("k_fraction", 0.2),
        ("S_upper", "AN;SN;FEC;EC"), ("S_lower", "FEC;EC;PC;DMC"),
        ("deterministic_overlap", 0.5),
        ("stability_upper", 0.1785), ("stability_lower", 0.0115),
        ("mean_overlap_with_upper", 0.7335),
        ("p_selected", {"AN": 0.889, "SN": 0.7445, "FEC": 0.8305, "EC": 0.47}),
    ])),
    ("stratification_anchor", OrderedDict([
        ("group", "P0_to_P1v|all|oxidation"), ("k_fraction", 0.2),
        ("S1", "AN;FEC;EC;SN"), ("S2", "EC;FEC"),
        ("sets_differ_at_k0p2_total", 12),
    ])),
    ("structural_anchor", OrderedDict([
        ("sign_reverse_total", 209),
        ("both_resolved_by_z", {"0.0": 209, "0.5": 63,
                                "0.7071067811865476": 0, "1.0": 0}),
    ])),
])


def _fmt(value):
    if value is None:
        return ""
    if isinstance(value, bool):
        return "True" if value else "False"
    if isinstance(value, float):
        return repr(value)
    return str(value)


def _max_abs(a, b):
    if a is None or b is None:
        return 0.0
    return abs(float(a) - float(b))


def build_checks(master, tables):
    pairwise = master["pairwise"]
    curve = tables["resolution_curve"]
    summary = tables["identifiability_summary"]
    structural = tables["structural_nontestability"]
    raw = tables["raw_ranking_changes"]
    sel = tables["selection_uncertainty"]
    strat = tables["stratification_sensitivity"]
    decisions = tables["decision_classes"]

    # 1. pair 恒等式
    max_shift_err = 0.0
    max_sigma_err = 0.0
    for row in pairwise:
        delta = float(row["delta_shift_ev"])
        max_shift_err = max(max_shift_err, abs(float(row["d_upper_ev"]) - float(row["d_lower_ev"]) - delta))
        max_sigma_err = max(max_sigma_err, abs(float(row["sigma_ev"]) - abs(delta) / (2.0 ** 0.5)))

    # 2. 分辨率曲线：单调 + 与冻结值对账
    monotonicity_violations = []
    by_group = OrderedDict()
    for row in curve:
        by_group.setdefault((row["comparison"], row["scope"], row["axis"]), []).append(row)
    for key, rows in by_group.items():
        rows = sorted(rows, key=lambda r: r["z"])
        for prev, nxt in zip(rows, rows[1:]):
            if nxt["f_unresolved_lower"] < prev["f_unresolved_lower"] - 1e-15:
                monotonicity_violations.append("%s lower z=%.4f" % ("|".join(key), nxt["z"]))
            if nxt["f_unresolved_upper"] < prev["f_unresolved_upper"] - 1e-15:
                monotonicity_violations.append("%s upper z=%.4f" % ("|".join(key), nxt["z"]))

    frozen_curve_err = 0.0
    frozen_curve_rows = 0
    for row in summary:
        frozen_curve_err = max(frozen_curve_err,
                               _max_abs(row["f_unresolved_lower_z1"], row["frozen_f_unresolved_lower_z1"]),
                               _max_abs(row["f_unresolved_upper_z1"], row["frozen_f_unresolved_upper_z1"]))
        frozen_curve_rows += 2

    # 3. Top-k 集合与冻结的 selected_upper / selected_lower 一致
    set_mismatch = [r["comparison"] + "|" + r["scope"] + "|" + r["axis"]
                    for r in sel
                    if set(r["selected_upper"].split(";")) != (set(r["frozen_selected_upper"].split(";"))
                                                               if r["frozen_selected_upper"] else set())
                    or set(r["selected_lower"].split(";")) != (set(r["frozen_selected_lower"].split(";"))
                                                                if r["frozen_selected_lower"] else set())]

    # 4. 排序指标与冻结值
    metric_diffs = OrderedDict()
    metric_rows = 0
    for row in summary:
        for metric, frozen in (("overlap", "frozen_overlap"), ("jaccard", "frozen_jaccard"),
                              ("selection_regret_ev", "frozen_regret_ev"),
                              ("kendall_tau_b", "frozen_kendall_tau_b"),
                              ("spearman_rho", "frozen_spearman_rho")):
            if row[frozen] is None or row[metric] is None:
                continue
            metric_diffs[metric] = max(metric_diffs.get(metric, 0.0),
                                       abs(row[metric] - row[frozen]))
            metric_rows += 1

    # 5. 结构性不可检验（代数必然）
    robust_at = OrderedDict()
    for row in structural:
        key = str(float(row["z"]))
        robust_at[key] = robust_at.get(key, 0) + row["n_robust_inversion"]
    frozen_robust = sum(int(r["n_robust_inversion"]) for r in master["decision"])
    algebra_bound = 1.0 / (2.0 ** 0.5)
    above_bound = all(v == 0 for k, v in robust_at.items() if float(k) > algebra_bound + 1e-12)
    all_struct_nontestable = all(r["structurally_non_testable"] for r in structural)

    # 6. Case C 内部一致：端点 overlap == 冻结 overlap；certain 必须落在 S1 内
    endpoint_err = 0.0
    certain_outside_s1 = []
    for row in sel:
        endpoint_err = max(endpoint_err, _max_abs(row["overlap"], row["frozen_overlap"]))
        if row["stability_upper"] > row["mean_overlap_with_upper"] + 1e-12:
            certain_outside_s1.append("stability>mean " + row["comparison"])
    for row in decisions:
        if row["decision_class"] == "certain" and not row["in_S_upper"]:
            certain_outside_s1.append("%s|%s|%s|%g|%s" % (row["comparison"], row["scope"],
                                                          row["axis"], row["k_fraction"], row["name"]))

    # 7. 分层算法敏感性
    s2_not_subset = [r for r in strat if not r["S2_subset_of_S1"]]
    differ_by_k = OrderedDict()
    for row in strat:
        key = "%g" % row["k_fraction"]
        differ_by_k[key] = differ_by_k.get(key, 0) + (1 if row["sets_differ"] else 0)

    certain_sets = OrderedDict()
    for row in decisions:
        if row["decision_class"] == "certain":
            key = (row["comparison"], row["scope"], row["axis"], "%g" % row["k_fraction"])
            certain_sets.setdefault(key, set()).add(row["name"])
    s2_sets = {(r["comparison"], r["scope"], r["axis"], "%g" % r["k_fraction"]):
               (set(r["S2"].split(";")) if r["S2"] else set())
               for r in strat}
    divergent = OrderedDict()
    for key, s2 in s2_sets.items():
        c = certain_sets.get(key, set())
        divergent[key[3]] = divergent.get(key[3], 0) + (1 if (s2 ^ c) else 0)

    # 8. 决策分类完整分区
    partition_ok = True
    partition_detail = []
    counts = {}
    for row in decisions:
        key = (row["comparison"], row["scope"], row["axis"], row["k_fraction"])
        counts.setdefault(key, {"n": 0, "certain": 0, "boundary": 0, "insufficient": 0})
        counts[key]["n"] += 1
        counts[key][row["decision_class"]] += 1
    n_rows_by_group = {}
    for row in sel:
        n_rows_by_group[(row["comparison"], row["scope"], row["axis"], row["k_fraction"])] = row["n_molecules"]
    for key, info in counts.items():
        if info["n"] != n_rows_by_group.get(key):
            partition_ok = False
            partition_detail.append("%s: classified %d of %d" % ("|".join(map(str, key)), info["n"],
                                                                 n_rows_by_group.get(key)))
        if info["certain"] + info["boundary"] + info["insufficient"] != info["n"]:
            partition_ok = False
            partition_detail.append("%s: class counts do not sum" % ("|".join(map(str, key)),))

    # 9. 独立复核对账
    anchor = INDEPENDENT_REVIEW["resolution_curve_anchor"]
    row = next(r for r in summary
               if "%s|%s|%s" % (r["comparison"], r["scope"], r["axis"]) == anchor["group"])
    z_row = next(r for r in curve
                 if "%s|%s|%s" % (r["comparison"], r["scope"], r["axis"]) == anchor["group"]
                 and abs(r["z"] - anchor["z"]) < 1e-12)
    anchor_err = max(_max_abs(row["f_unresolved_lower_z1"], anchor["f_unresolved_lower"]),
                     _max_abs(row["f_unresolved_upper_z1"], anchor["f_unresolved_upper"]),
                     _max_abs(z_row["f_unresolved_lower"], anchor["f_unresolved_lower"]),
                     _max_abs(z_row["f_unresolved_upper"], anchor["f_unresolved_upper"]))
    mc = INDEPENDENT_REVIEW["mc_anchor"]
    mc_row = next(r for r in sel
                  if "%s|%s|%s" % (r["comparison"], r["scope"], r["axis"]) == mc["group"]
                  and abs(r["k_fraction"] - mc["k_fraction"]) < 1e-12)
    anchor_err = max(anchor_err, _max_abs(mc_row["stability_upper"], mc["stability_upper"]),
                     _max_abs(mc_row["stability_lower"], mc["stability_lower"]),
                     _max_abs(mc_row["mean_overlap_with_upper"], mc["mean_overlap_with_upper"]),
                     _max_abs(mc_row["overlap"], mc["deterministic_overlap"]))
    if mc_row["selected_upper"] != mc["S_upper"] or mc_row["selected_lower"] != mc["S_lower"]:
        anchor_err = max(anchor_err, 1.0)
    for name, value in mc["p_selected"].items():
        got = next(r["p_selected"] for r in decisions
                   if "%s|%s|%s" % (r["comparison"], r["scope"], r["axis"]) == mc["group"]
                   and abs(r["k_fraction"] - mc["k_fraction"]) < 1e-12 and r["name"] == name)
        anchor_err = max(anchor_err, abs(got - value))
    st = INDEPENDENT_REVIEW["stratification_anchor"]
    st_row = next(r for r in strat
                  if "%s|%s|%s" % (r["comparison"], r["scope"], r["axis"]) == st["group"]
                  and abs(r["k_fraction"] - st["k_fraction"]) < 1e-12)
    anchor_ok = (anchor_err <= 1e-12 and set(st_row["S1"].split(";")) == set(st["S1"].split(";"))
                 and set(st_row["S2"].split(";")) == set(st["S2"].split(";"))
                 and differ_by_k.get("0.2", 0) == st["sets_differ_at_k0p2_total"])
    sa = INDEPENDENT_REVIEW["structural_anchor"]
    anchor_ok = anchor_ok and (sum(r["n_sign_reverse"] for r in raw) == sa["sign_reverse_total"]
                               and robust_at.get("0.0") == sa["both_resolved_by_z"]["0.0"]
                               and robust_at.get("0.5") == sa["both_resolved_by_z"]["0.5"]
                               and robust_at.get("0.7071067811865476") == 0)

    checks = [
        OrderedDict([
            ("id", "pair_shift_identity_holds"),
            ("ok", max_shift_err <= 1e-12 and max_sigma_err <= 1e-12),
            ("detail", "d_upper = d_lower + delta_shift（max %.3e）且 sigma = |delta_shift|/sqrt(2)（max %.3e），%d 行"
                       % (max_shift_err, max_sigma_err, len(pairwise))),
            ("max_shift_error", max_shift_err), ("max_sigma_error", max_sigma_err),
        ]),
        OrderedDict([
            ("id", "resolution_curve_monotone_and_matches_week28"),
            ("ok", not monotonicity_violations and frozen_curve_err <= 1e-12),
            ("detail", "f_unresolved 随 z 单调不减（违例 %d）；z=1.0 时与 Week 28 decision_table 最大绝对差 %.3e（%d 个比较）"
                       % (len(monotonicity_violations), frozen_curve_err, frozen_curve_rows // 2)),
            ("violations", monotonicity_violations), ("max_abs_diff", frozen_curve_err),
        ]),
        OrderedDict([
            ("id", "topk_sets_match_week28_decision_table"),
            ("ok", not set_mismatch),
            ("detail", "%d 行 (key,k) 的 selected_upper/lower 与冻结值一致（按集合比较；冻结列组内顺序来自 CPython set 迭代，无语义）；不一致 %d"
                       % (len(sel), len(set_mismatch))),
            ("mismatches", set_mismatch),
        ]),
        OrderedDict([
            ("id", "ranking_metrics_match_week28"),
            ("ok", bool(metric_diffs) and all(v <= 1e-9 for v in metric_diffs.values())),
            ("detail", "overlap/Jaccard/regret/tau_b/rho 对齐冻结值，最大绝对差 %s（%d 个 metric 行）"
                       % (", ".join("%s=%.3e" % (k, v) for k, v in metric_diffs.items()), metric_rows)),
            ("max_abs_diff", metric_diffs),
        ]),
        OrderedDict([
            ("id", "robust_inversion_is_structurally_impossible"),
            ("ok", frozen_robust == 0 and above_bound and all_struct_nontestable
                   and robust_at.get("1.0", None) == 0),
            ("detail", "1326 个 pair 全部 structurally_non_testable；decision_table 的 n_robust_inversion 合计 %d；"
                       "z>1/sqrt(2) 时反向 pair 两侧同时 resolved 恒为 0。按 z 的计数：%s"
                       % (frozen_robust, ", ".join("%s:%d" % kv for kv in robust_at.items()))),
            ("z_algebra_bound", algebra_bound), ("robust_inversion_by_z", robust_at),
            ("n_decision_robust_inversion", frozen_robust),
        ]),
        OrderedDict([
            ("id", "selection_uncertainty_internally_consistent"),
            ("ok", endpoint_err <= 1e-12 and not certain_outside_s1),
            ("detail", "端点 overlap 与冻结 overlap 最大差 %.3e；确定性保证的候选（p=1）必须落在 score Top-k 内 —— 违例 %d"
                       % (endpoint_err, len(certain_outside_s1))),
            ("max_endpoint_error", endpoint_err), ("violations", certain_outside_s1),
        ]),
        OrderedDict([
            ("id", "stratification_sensitivity_surfaced"),
            ("ok", not s2_not_subset and set(differ_by_k) == {"0.1", "0.2", "0.3"}),
            ("detail", "S2 ⊆ S1 恒成立（反例 %d）；S1 != S2 的 (组,k) 数按 k_fraction：%s（k=0.2 时 %d 组，与独立复核一致）"
                       % (len(s2_not_subset), ", ".join("%s:%d" % kv for kv in differ_by_k.items()),
                          differ_by_k.get("0.2", 0))),
            ("sets_differ_by_k", differ_by_k), ("certain_vs_S2_divergence_by_k", divergent),
        ]),
        OrderedDict([
            ("id", "decision_classes_partition_every_selection"),
            ("ok", partition_ok and len(counts) == len(sel)),
            ("detail", "%d 个 (组,k) 决策全部被划分为 certain / boundary / insufficient；每个决策的候选数之和等于该组分子数"
                       % len(counts)),
            ("detail_list", partition_detail),
        ]),
        OrderedDict([
            ("id", "independent_review_reconciled"),
            ("ok", anchor_ok),
            ("detail", "三个独立复核（A 分辨率 / B 稳健性 / C 分层）的锚点与本规范实现逐位一致："
                       "锚点最大差 %.3e；sign_reverse 合计 %d；k=0.2 的 S1!=S2 组数 %d"
                       % (anchor_err, sum(r["n_sign_reverse"] for r in raw), differ_by_k.get("0.2", 0))),
            ("anchor_max_abs_diff", anchor_err),
        ]),
        OrderedDict([
            ("id", "zero_new_electronic_structure"),
            ("ok", True),
            ("detail", "唯一输入是 outputs/week28/*.csv；未运行任何电子结构作业"),
            ("inputs", ["outputs/week28/property_table.csv", "outputs/week28/pairwise_table.csv",
                        "outputs/week28/decision_table.csv", "outputs/week28/molecule_registry.csv"]),
        ]),
    ]
    return checks


def collect():
    master = wp4.load(REPO)
    tables = wp4.analyse(master)
    checks = build_checks(master, tables)

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
            ("file", "outputs/week31/%s.csv" % table),
            ("n_rows", len(tables[table])),
            ("columns", columns),
            ("sha256", hashlib.sha256(text.encode("utf-8")).hexdigest()),
        ])

    payload = OrderedDict([
        ("stage", "Week 31 / WP4"),
        ("title", "turning ranking changes into defensible screening decisions (RQ3)"),
        ("plane", "next-phase implementation plan, work package WP4 (RQ3)"),
        ("inputs", OrderedDict([
            ("master_table", "outputs/week28/evidence_master_table.json"),
            ("comparisons", list(wp4.WP4_COMPARISONS)),
            ("z_grid", list(wp4.Z_GRID)),
            ("z_preregistered", wp4.Z_PREREG),
            ("k_fractions", list(wp4.K_FRACTIONS)),
            ("mc_draws", wp4.MC_B), ("mc_seed", wp4.MC_SEED),
            ("new_electronic_structure_jobs", 0),
        ])),
        ("conventions", OrderedDict([
            ("case_a", "raw ordering changes, no uncertainty threshold"),
            ("case_b", "f_unresolved(z) = #{|d_x| < z*sigma}/n_pairs ; sigma = |d_upper-d_lower|/sqrt(2)"),
            ("case_c", "score_i ~ Uniform[min(P_lower,P_upper), max(...)] ; Top-k by descending score"),
            ("stratification_S1", "score-lexicographic: Top-k by the upper-rung score"),
            ("stratification_S2", "conservative: i is selected iff it beats >= n-k rivals by resolved comparisons at both rungs"),
            ("decision_class", "certain p=1 ; boundary 0<p<1 ; insufficient p=0"),
            ("structural_nontestability", "z > 1/sqrt(2) forbids a reverse pair being resolved on both sides"),
            ("gate1_status", "Gate 1 remains NOT CLOSED; WP4 is a computational-target statement"),
        ])),
        ("independent_review", INDEPENDENT_REVIEW),
        ("checks", checks),
        ("checks_by_id", OrderedDict((c["id"], c) for c in checks)),
        ("manifest", manifest),
        ("n_rows_total", sum(len(tables[t]) for t in TABLE_ORDER)),
    ])

    texts = OrderedDict(csv_texts)
    texts["wp4_decision_identifiability.json"] = (
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=False) + "\n")
    texts["wp4_summary.md"] = render_summary(payload, tables)
    texts["manifest.json"] = json.dumps(
        OrderedDict([("stage", "Week 31 / WP4"), ("tables", manifest)]),
        ensure_ascii=False, indent=2, sort_keys=False) + "\n"
    return payload, texts


def _table(headers, rows):
    lines = ["| " + " | ".join(headers) + " |",
             "| " + " | ".join("---" for _ in headers) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(cell) for cell in row) + " |")
    return lines


def render_summary(payload, tables):
    summary = tables["identifiability_summary"]
    curve = tables["resolution_curve"]
    structural = tables["structural_nontestability"]
    raw = tables["raw_ranking_changes"]
    sel = tables["selection_uncertainty"]
    strat = tables["stratification_sensitivity"]
    decisions = tables["decision_classes"]

    lines = [
        "# Week 31 / WP4：把排序变化转成可辩护的筛选决策（RQ3）",
        "",
        "> 阶段：下一阶段实施方案 WP4（RQ3）。产物目录 `outputs/week31/`，交付镜像",
        "> `..\\成果输出（part2）\\week31/`。本文件由 `scripts/build_week31_wp4_decision_identifiability.py`",
        "> 确定性生成，`--check` 逐字节复核。**零新增电子结构计算**：唯一输入是 Week 28 冻结主表。",
        "",
        "## 0. 一句话结论",
        "",
        "对每一个 Top-k 筛选决策，都可以给出「确定选择 / 边界候选 / 证据不足」的区分，而且这个区分",
        "**依赖不确定性假设与分层算法**：同一份数据下，「端点区间抽样」的确定选择与「rung-wise 已解析」",
        "的保守选择在 %d 个 (组,k) 上给出不同答案。因此 WP4 不能只报 f_robust_inv —— 它在 z=1.0 下"
        "恒为 0，是 sigma=|d_upper-d_lower|/sqrt(2) 与 z>1/sqrt(2) 的**代数必然**，不是稳定性证据。"
        % payload["checks_by_id"]["stratification_sensitivity_surfaced"]["certain_vs_S2_divergence_by_k"].get("0.2", 0),
        "",
        "## 1. 三层评价总表（k_fraction=0.2）",
        "",
    ]
    lines += _table(
        ["对比", "scope", "轴", "n", "τ_b", "ρ", "f_unres(lo)", "f_unres(up)", "决策重叠", "regret(eV)", "选择不确定度"],
        [[r["comparison"], r["scope"], r["axis"], r["n_molecules"],
          "%.3f" % r["kendall_tau_b"], "%.3f" % r["spearman_rho"],
          "%.3f" % r["f_unresolved_lower_z1"], "%.3f" % r["f_unresolved_upper_z1"],
          "%.3f" % r["overlap"], "%.4f" % r["selection_regret_ev"],
          "%.3f" % r["selection_uncertainty_mean_overlap"]] for r in summary])
    lines += [
        "",
        "τ_b/ρ 是全局排序层；f_unres(lo/up) 与 decisive 比例是统计分辨率层；决策重叠/regret/选择不确定度",
        "是筛选决策层。三层一起读：全局排序看起来还行，但不代表 Top-k 决策可识别。",
        "",
        "## 2. 分辨率曲线（f_unresolved vs z）",
        "",
    ]
    z_show = (1.0, 1.6448536269514722, 1.959963984540054)
    lines += _table(
        ["对比", "scope", "轴"] + ["f(lo)@%.4g" % z for z in z_show] + ["f(up)@1.0"],
        [[r["comparison"], r["scope"], r["axis"]]
         + ["%.3f" % next(c["f_unresolved_lower"] for c in curve
                          if c["comparison"] == r["comparison"] and c["scope"] == r["scope"]
                          and c["axis"] == r["axis"] and abs(c["z"] - z) < 1e-12) for z in z_show]
         + ["%.3f" % r["f_unresolved_upper_z1"]] for r in summary])
    lines += [
        "",
        "还原轴的 f_unresolved 明显高于氧化轴，且随 z 上升快得多：还原排序本身就更不可识别。",
        "",
        "## 3. 结构性不可检验（algebra）",
        "",
        "```",
        "sigma_ij = |d_lower - d_upper| / sqrt(2)",
        "z > 1/sqrt(2)  =>  反向 pair 两侧不可能同时 resolved",
        "```",
        "",
    ]
    robust_by_z = payload["checks_by_id"]["robust_inversion_is_structurally_impossible"]["robust_inversion_by_z"]
    lines += [
        "按 z 统计反向 pair 两侧同时 resolved 的个数：%s。"
        % ", ".join("%s->%d" % kv for kv in robust_by_z.items()),
        "",
        "因此 Week 28 的 `f_robust_inversion == 0` **不能**读成「排序稳定」；它只是 z=1.0 > 1/sqrt(2) 的必然结果。",
        "全部 1326 个 pair 都标注为 `structurally_non_testable`。",
        "",
        "## 4. Case A：原始排序变化（不设阈值）",
        "",
    ]
    lines += _table(
        ["对比", "scope", "轴", "n", "反向 pair", "τ_b(原始)", "ρ(原始)", "Top-20% 重叠"],
        [[r["comparison"], r["scope"], r["axis"], r["n_molecules"], r["n_sign_reverse"],
          "%.3f" % r["kendall_tau_b"], "%.3f" % r["spearman_rho"],
          "%.3f" % r["top_k_overlap_k0p2"]] for r in raw])
    lines += [
        "",
        "反向 pair 合计 %d 个：原始排序确实发生了互换，只是这些互换在后面被判为不可检验。"
        % sum(r["n_sign_reverse"] for r in raw),
        "",
        "## 5. Case C：决策稳健性（歧义区间抽样）",
        "",
    ]
    lines += _table(
        ["对比", "轴", "k/N", "S_upper", "S_lower", "端点重叠", "P(S_upper 全中)", "平均∩S_upper"],
        [[r["comparison"], r["axis"], "%d/%d" % (r["k"], r["n_molecules"]),
          r["selected_upper"], r["selected_lower"],
          "%.3f" % r["overlap"], "%.3f" % r["stability_upper"],
          "%.3f" % r["mean_overlap_with_upper"]]
         for r in sel if abs(r["k_fraction"] - 0.2) < 1e-12])
    lines += [
        "",
        "## 6. 分层算法敏感性（S1 vs S2）",
        "",
    ]
    lines += _table(
        ["对比", "轴", "k", "S1（score）", "S2（conservative）", "|S2|", "缺口", "对称差"],
        [[r["comparison"], r["axis"], r["k"], r["S1"], r["S2"] or "(空)",
          r["S2_size"], r["S2_shortfall"], r["symdiff_names"] or "-"]
         for r in strat if abs(r["k_fraction"] - 0.2) < 1e-12])
    lines += [
        "",
        "`S2 ⊆ S1` 恒成立（已断言）；但两者在 k=0.2 的 %d 组上不一致。还原轴尤其严重："
        % sum(1 for r in strat if abs(r["k_fraction"] - 0.2) < 1e-12 and r["sets_differ"]),
        "大量 |S2|=0，意味着保守算法在还原轴上给不出任何「确定选择」。",
        "",
        "## 7. 验收交付表：确定选择 / 边界候选 / 证据不足",
        "",
    ]
    for r in sel:
        if abs(r["k_fraction"] - 0.2) > 1e-12:
            continue
        rows = [d for d in decisions if d["comparison"] == r["comparison"] and d["scope"] == r["scope"]
                and d["axis"] == r["axis"] and abs(d["k_fraction"] - 0.2) < 1e-12]
        certain = [d["name"] for d in rows if d["decision_class"] == "certain"]
        boundary = [d["name"] for d in rows if d["decision_class"] == "boundary"]
        lines.append("- **%s / %s / %s**（k=%d）：确定选择 %s；边界候选 %s；证据不足 %d 个。"
                     % (r["comparison"], r["scope"], r["axis"], r["k"],
                        ", ".join(certain) or "（无）", ", ".join(boundary) or "（无）",
                        r["n_never"]))
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
        "- 不确定性只用「两端模型输出的歧义区间」这一个独立来源；来源不足的地方如实报为 sensitivity range。",
        "- `f_robust_inversion == 0` 是代数必然，不得当作稳定性证据。",
        "- 「确定选择」是相对某一套不确定性假设与分层算法而言的；换假设会改变结论（见第 6 节）。",
        "- core18 上的结论不可外推到其他分子集：每组 n 随对比变化（18/12/10/6），跨行不可比。",
        "",
        "## 10. 复现命令",
        "",
        "```powershell",
        ".venv\\Scripts\\python.exe scripts\\build_week31_wp4_decision_identifiability.py",
        ".venv\\Scripts\\python.exe scripts\\build_week31_wp4_decision_identifiability.py --check",
        ".venv\\Scripts\\python.exe -m pytest tests/test_week31_wp4_decision_identifiability.py -q",
        "```",
    ]
    return "\n".join(lines) + "\n"


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Week 31 / WP4: decision identifiability and selection robustness.")
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

    print("Week 31 / WP4 -- decision identifiability and selection robustness")
    print("-" * 78)
    for table in TABLE_ORDER:
        info = payload["manifest"][table]
        print("  %-28s %5d rows  %s" % (table, info["n_rows"], info["sha256"][:12]))
    print("  %-28s %5d rows total" % ("(all tables)", payload["n_rows_total"]))
    print("-" * 78)
    for check in payload["checks"]:
        print("  %-46s %s" % (check["id"], "PASS" if check["ok"] else "FAIL"))
    print("-" * 78)
    print("wrote outputs/week31/ (%d files)" % len(texts))
    return 0


if __name__ == "__main__":
    sys.exit(main())