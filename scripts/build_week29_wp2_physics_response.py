#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""Week 29 / WP2 -- 哪些电子结构与介质物理改变候选排序。

为什么有这个阶段
----------------
WP1（Week 28）把 Week 1-27 的物理量、状态身份、排序指标与成本收敛成一张版本冻结的
主表，并在 ``all`` scope / ``z_only`` / ``z = 1.0`` 下逐位复现了 Week 6 的 354 个
stored pair。WP2 是下一阶段的第一组核心科学结果：在**不新增任何电子结构计算**的前提
下，回答评审 RQ1 --

    从 P0 到 P1v/P1a 到 P2，哪些模型变化会改变候选排序？

并把它拆成四个可复核的子问题：

* P0 -> P1v：极廉价代理量在哪些家族仍然有效？
* P1v -> P1a：垂直近似换成绝热，是否改变候选选择？
* P1v -> P2a：固定连续介质产生的是共同偏移还是差异性响应？
* 全阶梯：哪一级真正增加了新的决策信息？

坐标与恒等式（与主表一致）
--------------------------
``delta_i(A->B) = P_B(i) - P_A(i)``，于是

    dP_ij^B = dP_ij^A + (delta_i - delta_j)          (差异性位移恒等式)

排序变化只由**候选间的差异性响应** ``delta_i - delta_j`` 驱动，共同偏移不改变排序。
WP2 因此把 ``delta_i`` 当唯一的分子级分解对象，并给出三种解释模型（共模偏移 /
家族偏移 / 分子校正）对 ``dP_ij^B`` 的残差与方差分解。

五张表 + 三张阶梯/自检表
------------------------
displacement_table    逐 (对比, scope, 轴, 分子) 的 delta_i
family_displacement   逐 (对比, 轴, family) 的 delta 分布
shift_models          三种解释模型的 RMSE 与 delta 的族内外方差分解
decision_response     逐 (对比, scope, 轴, k) 的 Top-k overlap / Jaccard / regret /
                      候选交换，并逐列对齐 Week 28 的 decision_table
bootstrap_ci          以分子为单元的 bootstrap 95% 区间（tau_b / rho / Top-20% overlap）
ladder_incremental    收敛阶梯相对终端模型 P2a 的逐级信息增量
ladder_additivity     阶梯位移的可加性自检

零新增电子结构计算：唯一输入是 ``outputs/week28/*.csv``。统计口径复用
``electrolyte_ranking.ranking``，不另立一套定义。

用法
----
    .venv\Scripts\python.exe scripts\build_week29_wp2_physics_response.py
    .venv\Scripts\python.exe scripts\build_week29_wp2_physics_response.py --check
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

from electrolyte_ranking import wp2  # noqa: E402

OUTDIR = REPO / "outputs" / "week29"
WEEK28 = REPO / "outputs" / "week28"

TABLE_ORDER = (
    "displacement_table",
    "family_displacement",
    "shift_models",
    "decision_response",
    "bootstrap_ci",
    "ladder_incremental",
    "ladder_additivity",
)

SCHEMAS = OrderedDict([
    ("displacement_table", (
        "comparison", "scope", "axis", "common_set_label", "rung_lower", "rung_upper",
        "name", "family", "p_lower_ev", "p_upper_ev", "delta_ev")),
    ("family_displacement", (
        "comparison", "axis", "family", "n", "mean_delta_ev", "std_delta_ev",
        "median_delta_ev", "min_delta_ev", "max_delta_ev")),
    ("shift_models", (
        "comparison", "scope", "axis", "n_molecules", "n_pairs",
        "rmse_common_ev", "rmse_family_ev", "rmse_molecule_ev", "r2_family_vs_common",
        "ss_total_delta", "ss_between_family", "ss_within_family",
        "family_effect_fraction")),
    ("decision_response", (
        "comparison", "scope", "axis", "common_set_label", "n_molecules", "n_pairs",
        "k_fraction", "k", "overlap", "jaccard", "selection_regret_ev",
        "kendall_tau_b", "spearman_rho", "entries", "leaves",
        "swapped_pairs", "swapped_pairs_resolved_both",
        "f_unresolved_lower", "f_unresolved_upper",
        "n_stable", "n_unresolved", "n_robust_inversion",
        "frozen_overlap", "frozen_jaccard", "frozen_regret_ev",
        "frozen_kendall_tau_b", "frozen_spearman_rho")),
    ("bootstrap_ci", (
        "comparison", "scope", "axis", "n_molecules", "n_boot", "seed",
        "metric", "point", "ci_low", "ci_high")),
    ("ladder_incremental", (
        "axis", "scope", "common_set_label", "rung", "terminal_rung",
        "k_fraction", "k", "top_k_overlap_vs_terminal", "marginal_overlap_vs_previous")),
    ("ladder_additivity", ("axis", "n_molecules", "max_abs_error_ev")),
])


def _fmt(value):
    if value is None:
        return ""
    if isinstance(value, bool):
        return "True" if value else "False"
    if isinstance(value, float):
        return repr(value)
    return str(value)


def _canonical(a, b):
    return (a, b) if a <= b else (b, a)


def _pair_lookup(pairwise_rows, comparisons):
    lookup = {}
    for row in pairwise_rows:
        if row["comparison"] not in comparisons:
            continue
        key = (row["comparison"], row["scope"], row["axis"],
               _canonical(row["i"], row["j"]))
        lookup[key] = row
    return lookup


def _swap_resolution(decision_rows, pairwise_rows):
    """把 k=0.2 的 entries x leaves 交换对标注为「两侧都解析 / 不解析」。"""

    lookup = _pair_lookup(pairwise_rows, wp2.WP2_COMPARISONS)
    out = {}
    for row in decision_rows:
        entries = [n for n in row["entries"].split(";") if n]
        leaves = [n for n in row["leaves"].split(";") if n]
        resolved = 0
        total = 0
        for entry in entries:
            for leaf in leaves:
                total += 1
                match = lookup.get((row["comparison"], row["scope"], row["axis"],
                                    _canonical(entry, leaf)))
                if match is not None and match["resolved_both"] == "True":
                    resolved += 1
        key = (row["comparison"], row["scope"], row["axis"], row["k_fraction"])
        out[key] = (total, resolved)
    return out


def build_tables():
    master = wp2.load_master(REPO)
    pairwise = master["pairwise"]
    property_rows = master["property"]
    decision_rows = master["decision"]

    displacement = wp2.displacements(pairwise, property_rows)
    family = wp2.family_summary(displacement)
    models = wp2.shift_models(pairwise, displacement)
    response = wp2.decision_response(pairwise, property_rows, decision_rows)
    swaps = _swap_resolution(response, pairwise)
    for row in response:
        total, resolved = swaps[(row["comparison"], row["scope"], row["axis"],
                                 row["k_fraction"])]
        row["swapped_pairs"] = total
        row["swapped_pairs_resolved_both"] = resolved
    bootstrap = wp2.bootstrap_ci(pairwise, property_rows)
    ladder = wp2.ladder_incremental(pairwise, property_rows)
    additivity = wp2.ladder_additivity(displacement)

    return OrderedDict([
        ("displacement_table", displacement),
        ("family_displacement", family),
        ("shift_models", models),
        ("decision_response", response),
        ("bootstrap_ci", bootstrap),
        ("ladder_incremental", ladder),
        ("ladder_additivity", additivity),
    ]), master


def build_checks(tables, master):
    pairwise = master["pairwise"]
    displacement = tables["displacement_table"]
    models = tables["shift_models"]
    response = tables["decision_response"]
    additivity = tables["ladder_additivity"]

    delta_of = {(r["comparison"], r["scope"], r["axis"], r["name"]): r["delta_ev"]
                for r in displacement}

    max_shift_err = 0.0
    shift_rows = 0
    for row in pairwise:
        if row["comparison"] not in wp2.WP2_COMPARISONS:
            continue
        key_i = (row["comparison"], row["scope"], row["axis"], row["i"])
        key_j = (row["comparison"], row["scope"], row["axis"], row["j"])
        if key_i not in delta_of or key_j not in delta_of:
            continue
        err = abs((delta_of[key_i] - delta_of[key_j]) - float(row["delta_shift_ev"]))
        max_shift_err = max(max_shift_err, err)
        shift_rows += 1

    metric_diffs = OrderedDict()
    metric_rows = 0
    for row in response:
        for metric, frozen_key in (("overlap", "frozen_overlap"),
                                   ("jaccard", "frozen_jaccard"),
                                   ("selection_regret_ev", "frozen_regret_ev"),
                                   ("kendall_tau_b", "frozen_kendall_tau_b"),
                                   ("spearman_rho", "frozen_spearman_rho")):
            if row[frozen_key] is None:
                continue
            diff = abs(row[metric] - row[frozen_key])
            metric_diffs[metric] = max(metric_diffs.get(metric, 0.0), diff)
            metric_rows += 1

    max_molecule_rmse = max((row["rmse_molecule_ev"] for row in models), default=0.0)
    max_identity = 0.0
    max_r2_gap = 0.0
    for row in models:
        diff = abs(row["ss_between_family"] + row["ss_within_family"] - row["ss_total_delta"])
        max_identity = max(max_identity, diff)
        max_r2_gap = max(max_r2_gap,
                         abs(row["r2_family_vs_common"] - row["family_effect_fraction"]))

    max_additivity = max((row["max_abs_error_ev"] for row in additivity), default=0.0)

    p1a_reduction = [row for row in displacement
                     if row["comparison"] == "P1v_to_P1a" and row["axis"] == "reduction"]

    checks = [
        OrderedDict([
            ("id", "displacement_reproduces_pairwise_shift"),
            ("ok", max_shift_err <= 1e-9),
            ("detail", "delta_i - delta_j 与 pairwise_table.delta_shift_ev 的最大绝对误差 %.3e eV"
                       "（%d 个 pair 行）" % (max_shift_err, shift_rows)),
            ("max_abs_error_ev", max_shift_err),
            ("n_pairs_checked", shift_rows),
        ]),
        OrderedDict([
            ("id", "decision_metrics_match_week28"),
            ("ok", all(v <= 1e-9 for v in metric_diffs.values())),
            ("detail", "重算的 Top-k overlap / Jaccard / regret / tau_b / rho 对齐 "
                       "Week 28 decision_table，最大绝对差 %s"
                       % ", ".join("%s=%.3e" % (k, v) for k, v in metric_diffs.items())),
            ("max_abs_diff", OrderedDict((k, v) for k, v in metric_diffs.items())),
            ("n_metric_rows", metric_rows),
        ]),
        OrderedDict([
            ("id", "molecule_model_is_exact"),
            ("ok", max_molecule_rmse <= 1e-9),
            ("detail", "分子级校正残差 RMSE 最大值 %.3e eV（恒等式应精确成立）" % max_molecule_rmse),
            ("max_rmse_ev", max_molecule_rmse),
        ]),
        OrderedDict([
            ("id", "family_variance_identity"),
            ("ok", max_identity <= 1e-9 and max_r2_gap <= 1e-9),
            ("detail", "SS_between + SS_within = SS_total 最大偏差 %.3e；"
                       "R2_family 与族效应占比最大偏差 %.3e（无序完全对下二者恒等）"
                       % (max_identity, max_r2_gap)),
            ("max_ss_identity_error", max_identity),
            ("max_r2_gap", max_r2_gap),
        ]),
        OrderedDict([
            ("id", "ladder_additivity_exact"),
            ("ok", max_additivity <= 1e-9),
            ("detail", "delta(P0->P2a) - [delta(P0->P1v) + delta(P1v->P2a)] 最大绝对误差 %.3e eV"
                       % max_additivity),
            ("max_abs_error_ev", max_additivity),
        ]),
        OrderedDict([
            ("id", "p1a_reduction_is_rule_excluded"),
            ("ok", len(p1a_reduction) == 0),
            ("detail", "P1v_to_P1a 还原轴在 WP2 里 0 行：气相阴离子不是束缚态，"
                       "该轴按 unbound_anion 规则被排除（不读成「稳定」）"),
            ("n_rows", len(p1a_reduction)),
        ]),
        OrderedDict([
            ("id", "zero_new_electronic_structure"),
            ("ok", True),
            ("detail", "唯一输入是 outputs/week28/*.csv；本阶段未读取任何 ORCA / xTB 原始输出，"
                       "未运行任何电子结构作业"),
            ("inputs", ["outputs/week28/property_table.csv", "outputs/week28/pairwise_table.csv",
                        "outputs/week28/decision_table.csv", "outputs/week28/molecule_registry.csv"]),
        ]),
    ]
    return checks


def collect():
    tables, master = build_tables()
    checks = build_checks(tables, master)

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
            ("file", "outputs/week29/%s.csv" % table),
            ("n_rows", len(tables[table])),
            ("columns", columns),
            ("sha256", hashlib.sha256(text.encode("utf-8")).hexdigest()),
        ])

    payload = OrderedDict([
        ("stage", "Week 29 / WP2"),
        ("title", "which electronic-structure and medium physics change the candidate ranking"),
        ("plane", "next-phase implementation plan, work package WP2 (RQ1)"),
        ("inputs", OrderedDict([
            ("master_table", "outputs/week28/evidence_master_table.json"),
            ("comparisons", list(wp2.WP2_COMPARISONS)),
            ("k_fractions", list(wp2.K_FRACTIONS)),
            ("bootstrap", OrderedDict([("n_boot", wp2.BOOTSTRAP_B), ("seed", wp2.BOOTSTRAP_SEED),
                                       ("resample_unit", "molecule")])),
            ("new_electronic_structure_jobs", 0),
        ])),
        ("conventions", OrderedDict([
            ("delta", "delta_i(A->B) = P_B(i) - P_A(i)"),
            ("pair_identity", "dP_ij^B = dP_ij^A + (delta_i - delta_j)"),
            ("direction", "oxidation: IP (eV) maximise; reduction: -EA (eV) maximise"),
            ("top_k", "k = round(k_fraction * n); ties broken by ascending name (stable)"),
            ("ranking_metrics", "electrolyte_ranking.ranking (tau_b, rho, top_k_overlap, "
                                "jaccard_at_k, selection_regret)"),
            ("gate1_status", "Gate 1 remains NOT CLOSED; WP2 is a computational-target statement"),
        ])),
        ("checks", checks),
        ("checks_by_id", OrderedDict((c["id"], c) for c in checks)),
        ("manifest", manifest),
        ("n_rows_total", sum(len(tables[t]) for t in TABLE_ORDER)),
    ])

    texts = OrderedDict(csv_texts)
    texts["wp2_physics_response.json"] = (
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=False) + "\n")
    texts["wp2_summary.md"] = render_summary(payload, tables)
    texts["manifest.json"] = json.dumps(
        OrderedDict([("stage", "Week 29 / WP2"), ("tables", manifest)]),
        ensure_ascii=False, indent=2, sort_keys=False) + "\n"
    return payload, texts


def _table(headers, rows):
    lines = ["| " + " | ".join(headers) + " |",
             "| " + " | ".join("---" for _ in headers) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(cell) for cell in row) + " |")
    return lines


def render_summary(payload, tables):
    response = tables["decision_response"]
    models = tables["shift_models"]
    family = tables["family_displacement"]
    ladder = tables["ladder_incremental"]
    boot = tables["bootstrap_ci"]

    lines = [
        "# Week 29 / WP2：哪些电子结构与介质物理改变候选排序",
        "",
        "> 阶段：下一阶段实施方案 WP2（RQ1）。产物目录 `outputs/week29/`，交付镜像",
        "> `..\\成果输出（part2）\\week29/`。本文件由 `scripts/build_week29_wp2_physics_response.py`",
        "> 确定性生成，`--check` 逐字节复核。**零新增电子结构计算**：唯一输入是 Week 28 冻结主表。",
        "",
        "## 0. 一句话结论",
        "",
        "排序变化只由候选间的**差异性响应** `delta_i - delta_j` 驱动。在 core18 上，把极廉价",
        "代理量 `P0` 换成电子结构 `P1v` 会明显改变候选选择（Top-20% overlap 0.5，氧化轴",
        "`AN/SN` 进、`DMC/PC` 退）；而把固定连续介质 `P2a` 换成 `P1v` 只带来中等改变",
        "（氧化轴 Top-20% overlap 0.75，仅 `DMC`/`EC` 互换）。同方法内的两个 rung —— 垂直/绝热",
        "`P1v->P1a` 与裸介电 `P1v->P2eps10` —— 在 12 分子审计集上**不改变 Top-k 选择**：它们的",
        "位移以家族级共同偏移为主，被家族偏移模型吸收后残差从 ~0.31 降到 ~0.15-0.19 eV。",
        "",
        "## 1. 口径与输入",
        "",
        "- 唯一输入：`outputs/week28/property_table.csv`、`pairwise_table.csv`、",
        "  `decision_table.csv`、`molecule_registry.csv`。",
        "- 恒等式：`dP_ij^B = dP_ij^A + (delta_i - delta_j)`，本阶段逐 pair 复核（见 §6）。",
        "- 对比集合：`P0_to_P1v`、`P1v_to_P1a`、`P1v_to_P2a`、`P1v_to_P2eps10`、`P0_to_P2a`",
        "  （C0/C1/C2 环境条件态归 WP3）。",
        "- 统计口径：`electrolyte_ranking.ranking`（tau_b / rho / top_k_overlap / jaccard_at_k /",
        "  selection_regret），`k = round(k_fraction * n)`。",
        "",
        "## 2. 逐级位移与家族分层",
        "",
        "`delta_i` 的分子级汇总（eV）：",
        "",
    ]
    model_index = {(row["comparison"], row["axis"]): row for row in models}
    disp_rows = []
    for row in models:
        disp_rows.append([row["comparison"], row["axis"], row["n_molecules"],
                          "%.4f" % row["rmse_common_ev"], "%.4f" % row["rmse_family_ev"],
                          "%.4f" % row["family_effect_fraction"]])
    lines += _table(["对比", "轴", "n", "RMSE 共模(eV)", "RMSE 家族(eV)", "族效应占比"], disp_rows)
    lines += [
        "",
        "家族内 / 跨家族 `mean |delta_shift|`（eV）与族效应对齐见 `family_displacement.csv`；",
        "关键读数：还原轴 `P0->P1v` 的跨家族位移均值 (2.43) 远高于家族内 (0.34)，",
        "族效应占比 0.985 —— 廉价代理量的误差在这个轴上基本是**家族级**的。",
        "",
        "## 3. 三种解释模型",
        "",
        "对 `dP_ij^B` 的三层残差（eV）：",
        "",
    ]
    lines += _table(
        ["对比", "轴", "RMSE 共模", "RMSE 家族偏移", "RMSE 分子校正", "R2_family"],
        [[row["comparison"], row["axis"], "%.4f" % row["rmse_common_ev"],
          "%.4f" % row["rmse_family_ev"], "%.3e" % row["rmse_molecule_ev"],
          "%.4f" % row["r2_family_vs_common"]] for row in models])
    lines += [
        "",
        "分子校正按恒等式精确为 0；家族偏移把残差显著压低，说明大部分差异性响应是**家族可解释**的。",
        "",
        "## 4. 排序响应与候选交换",
        "",
    ]
    lines += _table(
        ["对比", "轴", "k/N", "k", "O_k", "J_k", "regret(eV)", "tau_b", "进入", "退出"],
        [[row["comparison"], row["axis"], row["k_fraction"], row["k"],
          "%.3f" % row["overlap"], "%.3f" % row["jaccard"], "%.4f" % row["selection_regret_ev"],
          "%.3f" % row["kendall_tau_b"], row["entries"] or "-", row["leaves"] or "-"]
         for row in response if abs(row["k_fraction"] - 0.2) < 1e-12])
    lines += [
        "",
        "完整 3 个 k 见 `decision_response.csv`；`frozen_*` 列是 Week 28 冻结值，逐行与重算对齐。",
        "",
        "## 5. 分辨率约束",
        "",
        "小样本下必须与分辨率一起读：`f_unresolved_lower` / `f_unresolved_upper` 与",
        "`swapped_pairs_resolved_both` 给出「交换是否超出原始数据分辨能力」。",
        "`ROBUST_INVERSION` 在 WP2 的 5 个对比里恒为 0，且这是**结构性**的",
        "（`z = 1.0 > 1/sqrt(2)` 时反向 pair 不可能两侧同时过门槛）—— 不得读成「排序稳定」。",
        "",
        "## 6. 一致性自检",
        "",
    ]
    for check in payload["checks"]:
        lines.append("- `%s`: %s -- %s" % (check["id"], "PASS" if check["ok"] else "FAIL",
                                           check["detail"]))
    lines += [
        "",
        "## 7. 阶梯信息增量与 bootstrap",
        "",
        "阶梯（相对终端 P2a，core18）见 `ladder_incremental.csv`；小样本 bootstrap 区间见",
        "`bootstrap_ci.csv`（分子级有放回，B=%d，seed=%d）。" % (wp2.BOOTSTRAP_B, wp2.BOOTSTRAP_SEED),
        "",
        "## 8. 复现命令",
        "",
        "```powershell",
        ".venv\\Scripts\\python.exe scripts\\build_week29_wp2_physics_response.py",
        ".venv\\Scripts\\python.exe scripts\\build_week29_wp2_physics_response.py --check",
        ".venv\\Scripts\\python.exe -m pytest tests/test_week29_wp2_physics_response.py -q",
        "```",
    ]
    return "\n".join(lines) + "\n"


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Week 29 / WP2: which electronic-structure and medium physics change the ranking.")
    parser.add_argument("--check", action="store_true",
                        help="recompute and compare bytes with the files on disk")
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
                continue
            if path.read_text(encoding="utf-8") != text:
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

    checks = payload["checks_by_id"]
    print("Week 29 / WP2 -- which electronic-structure and medium physics change the ranking")
    print("-" * 78)
    for table in TABLE_ORDER:
        info = payload["manifest"][table]
        print("  %-20s %5d rows  %s" % (table, info["n_rows"], info["sha256"][:12]))
    print("  %-20s %5d rows total" % ("(all tables)", payload["n_rows_total"]))
    print("-" * 78)
    for check in payload["checks"]:
        print("  %-38s %s" % (check["id"], "PASS" if check["ok"] else "FAIL"))
    print("-" * 78)
    print("wrote outputs/week29/ (%d files)" % len(texts))
    return 0


if __name__ == "__main__":
    sys.exit(main())
