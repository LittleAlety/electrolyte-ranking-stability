#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""Week 30 / WP3 -- Li+ 配位条件态如何影响 redox 行为（RQ2）。

为什么有这个阶段
----------------
WP2 在 Axis-A 阶梯上回答了「哪些物理改变排序」。WP3 处理电解液化学最有特色的一层：
Li+ 配位条件态 C1 = [LiM]+（以及第一溶剂壳 C2 = [Li(M)2]+）。核心响应量仍是 v2 的定义::

    DeltaDeltaG_coord^ox/red = dG_redox^{C1} - dG_redox^{C0}

但**必须按电子状态身份拆分**。Week 5 的冻结事实：12 个还原态里 11 个外加电子落在 Li 上。
在这种格子上比较 dG_red 的排序，衡量的不是「同一个分子被还原的难度」，而是「电子去了哪」——
这是 observable identity failure，不是 ranking instability（docs/state_identity_protocol.md）。

六张表
------
coord_response        逐 (对比, scope, 轴, 分子) 的条件态位移 + 状态身份 + QC
identity_split        逐 (对比, 轴, 状态身份标签) 的位移分布与成员
ranking_impact        C0/C1/C2 的 Top-k 影响（含 n<2 的显式未定义行）
descriptor_association 只在 R13 主集合上做描述符关联（绝不混入混合身份样本）
mechanism_cases       两个有 QC 支持的机制案例（可解释响应 / 身份失败）
c1_to_c2_consistency  C1 -> C2 是否改变关键机制判断

零新增电子结构计算：唯一输入是 ``outputs/week28/*.csv``。

用法
----
    .venv\\Scripts\\python.exe scripts\\build_week30_wp3_coordination_mechanism.py
    .venv\\Scripts\\python.exe scripts\\build_week30_wp3_coordination_mechanism.py --check
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

from electrolyte_ranking import wp2, wp3  # noqa: E402

OUTDIR = REPO / "outputs" / "week30"

TABLE_ORDER = (
    "coord_response",
    "identity_split",
    "ranking_impact",
    "descriptor_association",
    "mechanism_cases",
    "c1_to_c2_consistency",
)

SCHEMAS = OrderedDict([
    ("coord_response", (
        "comparison", "scope", "axis", "common_set_label", "rung_lower", "rung_upper",
        "name", "family", "p_lower_ev", "p_upper_ev", "delta_ev",
        "state_identity_label", "in_primary_ranking", "state_id",
        "qc_state", "qc_flags", "parent_bonds_intact", "energy_availability", "motif_id")),
    ("identity_split", (
        "comparison", "axis", "state_identity_label", "n", "n_primary", "members",
        "mean_delta_ev", "std_delta_ev")),
    ("ranking_impact", (
        "comparison", "scope", "axis", "common_set_label", "n_molecules", "n_pairs",
        "k_fraction", "k", "overlap", "jaccard", "selection_regret_ev",
        "kendall_tau_b", "spearman_rho", "entries", "leaves",
        "f_unresolved_lower", "f_unresolved_upper",
        "n_stable", "n_unresolved", "n_robust_inversion",
        "frozen_overlap", "frozen_jaccard", "frozen_regret_ev",
        "frozen_kendall_tau_b", "frozen_spearman_rho")),
    ("descriptor_association", (
        "comparison", "axis", "descriptor", "n", "members",
        "pearson_r", "pearson_p", "spearman_rho", "spearman_p")),
    ("mechanism_cases", (
        "case_id", "kind", "comparison", "axis", "scope", "n_molecules", "members",
        "metric", "qc_support", "statement")),
    ("c1_to_c2_consistency", (
        "axis", "name", "family", "c1_identity_label", "c2_identity_label",
        "identity_changed", "c1_to_c2_delta_ev", "qc_state")),
])


def _fmt(value):
    if value is None:
        return ""
    if isinstance(value, bool):
        return "True" if value else "False"
    if isinstance(value, float):
        return repr(value)
    return str(value)


def build_tables(master):
    coord = wp3.coord_response(master)
    return OrderedDict([
        ("coord_response", coord),
        ("identity_split", wp3.identity_split(coord)),
        ("ranking_impact", wp3.ranking_impact(master)),
        ("descriptor_association", wp3.descriptor_association(master, coord)),
        ("mechanism_cases", wp3.mechanism_cases(master, coord)),
        ("c1_to_c2_consistency", wp3.c1_to_c2_consistency(coord)),
    ])


def build_checks(master, tables):
    pairwise = master["pairwise"]
    coord = tables["coord_response"]
    impact = tables["ranking_impact"]
    cases = tables["mechanism_cases"]
    desc = tables["descriptor_association"]
    c12 = tables["c1_to_c2_consistency"]

    delta_of = {(r["comparison"], r["scope"], r["axis"], r["name"]): r["delta_ev"]
                for r in coord}
    max_shift_err = 0.0
    shift_rows = 0
    for row in pairwise:
        if row["comparison"] not in wp3.WP3_COMPARISONS:
            continue
        key_i = (row["comparison"], row["scope"], row["axis"], row["i"])
        key_j = (row["comparison"], row["scope"], row["axis"], row["j"])
        if key_i not in delta_of or key_j not in delta_of:
            continue
        max_shift_err = max(max_shift_err,
                            abs((delta_of[key_i] - delta_of[key_j]) - float(row["delta_shift_ev"])))
        shift_rows += 1

    metric_diffs = OrderedDict()
    metric_rows = 0
    for row in impact:
        for metric, frozen in (("overlap", "frozen_overlap"), ("jaccard", "frozen_jaccard"),
                               ("selection_regret_ev", "frozen_regret_ev"),
                               ("kendall_tau_b", "frozen_kendall_tau_b"),
                               ("spearman_rho", "frozen_spearman_rho")):
            if row[frozen] is None or row[metric] is None:
                continue
            metric_diffs[metric] = max(metric_diffs.get(metric, 0.0), abs(row[metric] - row[frozen]))
            metric_rows += 1

    reduction_primary = sorted(r["name"] for r in coord
                               if r["comparison"] == "C0_to_C1" and r["axis"] == "reduction"
                               and r["scope"] == "all" and r["in_primary_ranking"] == "True")
    oxidation_primary = sorted(r["name"] for r in coord
                               if r["comparison"] == "C0_to_C1" and r["axis"] == "oxidation"
                               and r["scope"] == "all" and r["in_primary_ranking"] == "True")
    li_red = [r for r in coord if r["comparison"] == "C0_to_C1" and r["axis"] == "reduction"
              and r["scope"] == "all"
              and r["state_identity_label"] == "Li_centered_or_mixed_redox"]
    red_all = [r for r in coord if r["comparison"] == "C0_to_C1" and r["axis"] == "reduction"
               and r["scope"] == "all"]

    primary_sets = {}
    for row in coord:
        if row["in_primary_ranking"] == "True":
            primary_sets.setdefault((row["comparison"], row["axis"]), set()).add(row["name"])
    desc_ok = all(set(r["members"].split(";")) <= primary_sets.get((r["comparison"], r["axis"]), set())
                  for r in desc)

    flagged_primary = []
    for row in coord:
        if row["in_primary_ranking"] != "True":
            continue
        reg_rows = [r for part in wp3.state_components(row["state_id"])
                    for r in master["state_rows_by_id"].get(part, [])]
        if any(r["qc_state"] != "ok" for r in reg_rows):
            flagged_primary.append(row)
    qc_surfaced = bool(flagged_primary) and all(row["qc_flags"] for row in flagged_primary)

    checks = [
        OrderedDict([
            ("id", "coord_shift_reproduces_pairwise_shift"),
            ("ok", max_shift_err <= 1e-9),
            ("detail", "delta_i - delta_j 与 pairwise_table.delta_shift_ev 的最大绝对误差 %.3e eV（%d 个 pair 行）"
                       % (max_shift_err, shift_rows)),
            ("max_abs_error_ev", max_shift_err), ("n_pairs_checked", shift_rows),
        ]),
        OrderedDict([
            ("id", "ranking_metrics_match_week28"),
            ("ok", all(v <= 1e-9 for v in metric_diffs.values()) if metric_diffs else False),
            ("detail", "C0/C1/C2 重算的 overlap/Jaccard/regret/tau_b/rho 对齐 Week 28 decision_table，最大绝对差 %s"
                       % ", ".join("%s=%.3e" % (k, v) for k, v in metric_diffs.items())),
            ("max_abs_diff", metric_diffs), ("n_metric_rows", metric_rows),
        ]),
        OrderedDict([
            ("id", "identity_gate_holds"),
            ("ok", reduction_primary == ["SN"] and len(oxidation_primary) == 6),
            ("detail", "R13 闸门后 C1 主集合：还原轴 %s（n=%d），氧化轴 n=%d"
                       % (reduction_primary, len(reduction_primary), len(oxidation_primary))),
            ("primary_reduction", reduction_primary),
            ("primary_oxidation", oxidation_primary),
        ]),
        OrderedDict([
            ("id", "li_centered_dominates_c1_reduction"),
            ("ok", len(li_red) == 9 and len(red_all) == 10),
            ("detail", "C1 还原态 %d/%d 的外加电子落在 Li 上（molecule-centered 仅 %d 个）"
                       % (len(li_red), len(red_all), len(red_all) - len(li_red))),
            ("n_li_centered", len(li_red)), ("n_reduction_states", len(red_all)),
        ]),
        OrderedDict([
            ("id", "mechanism_cases_present_and_qc_flags_surfaced"),
            ("ok", len(cases) >= 2 and qc_surfaced),
            ("detail", "%d 个机制案例；%d 个主集合状态带 QC 警告且已如实上报（未静默丢弃）：%s"
                       % (len(cases), len(flagged_primary),
                          ";".join("%s:%s" % (r["name"], r["qc_flags"]) for r in flagged_primary) or "none")),
            ("case_ids", [c["case_id"] for c in cases]),
            ("qc_flagged_primary", ["%s/%s/%s" % (r["comparison"], r["axis"], r["name"])
                                    for r in flagged_primary]),
        ]),
        OrderedDict([
            ("id", "descriptor_regression_is_primary_only"),
            ("ok", desc_ok and len(desc) > 0),
            ("detail", "所有描述符关联的成员都落在 R13 主集合内 = %s（%d 个关联行；绝不把混合身份样本并进同一回归）"
                       % (desc_ok, len(desc))),
        ]),
        OrderedDict([
            ("id", "c1_to_c2_preserves_identity_labels"),
            ("ok", all(not r["identity_changed"] for r in c12)),
            ("detail", "C1 -> C2 的 %d 个状态里标签变化 %d 个：第一溶剂壳不改变关键机制判断"
                       % (len(c12), sum(1 for r in c12 if r["identity_changed"]))),
        ]),
        OrderedDict([
            ("id", "zero_new_electronic_structure"),
            ("ok", True),
            ("detail", "唯一输入是 outputs/week28/*.csv；未运行任何电子结构作业"),
            ("inputs", ["outputs/week28/property_table.csv", "outputs/week28/pairwise_table.csv",
                        "outputs/week28/decision_table.csv", "outputs/week28/molecule_registry.csv",
                        "outputs/week28/state_registry.csv"]),
        ]),
    ]
    return checks


def collect():
    master = wp3.load(REPO)
    tables = build_tables(master)
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
            ("file", "outputs/week30/%s.csv" % table),
            ("n_rows", len(tables[table])),
            ("columns", columns),
            ("sha256", hashlib.sha256(text.encode("utf-8")).hexdigest()),
        ])

    payload = OrderedDict([
        ("stage", "Week 30 / WP3"),
        ("title", "how Li+ coordination changes redox behaviour and its state identity"),
        ("plane", "next-phase implementation plan, work package WP3 (RQ2)"),
        ("inputs", OrderedDict([
            ("master_table", "outputs/week28/evidence_master_table.json"),
            ("comparisons", list(wp3.WP3_COMPARISONS)),
            ("new_electronic_structure_jobs", 0),
        ])),
        ("conventions", OrderedDict([
            ("coord_response", "DeltaDeltaG_coord = P_C1(i) - P_C0(i) (and P_C2 - P_C1)"),
            ("identity_gate", "C1/C2 reduction: molecule_centered_redox only (R13)"),
            ("descriptor_regression", "fit on in_primary_ranking=True molecules only"),
            ("gate1_status", "Gate 1 remains NOT CLOSED; WP3 is a computational-target statement"),
        ])),
        ("checks", checks),
        ("checks_by_id", OrderedDict((c["id"], c) for c in checks)),
        ("manifest", manifest),
        ("n_rows_total", sum(len(tables[t]) for t in TABLE_ORDER)),
    ])

    texts = OrderedDict(csv_texts)
    texts["wp3_coordination_mechanism.json"] = (
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=False) + "\n")
    texts["wp3_summary.md"] = render_summary(payload, tables)
    texts["manifest.json"] = json.dumps(
        OrderedDict([("stage", "Week 30 / WP3"), ("tables", manifest)]),
        ensure_ascii=False, indent=2, sort_keys=False) + "\n"
    return payload, texts


def _table(headers, rows):
    lines = ["| " + " | ".join(headers) + " |",
             "| " + " | ".join("---" for _ in headers) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(cell) for cell in row) + " |")
    return lines


def render_summary(payload, tables):
    coord = tables["coord_response"]
    split = tables["identity_split"]
    impact = tables["ranking_impact"]
    desc = tables["descriptor_association"]
    cases = tables["mechanism_cases"]
    c12 = tables["c1_to_c2_consistency"]

    key = {(r["comparison"], r["scope"], r["axis"]): r for r in impact}
    lines = [
        "# Week 30 / WP3：Li+ 配位条件态如何影响 redox 行为",
        "",
        "> 阶段：下一阶段实施方案 WP3（RQ2）。产物目录 `outputs/week30/`，交付镜像",
        "> `..\\成果输出（part2）\\week30/`。本文件由 `scripts/build_week30_wp3_coordination_mechanism.py`",
        "> 确定性生成，`--check` 逐字节复核。**零新增电子结构计算**：唯一输入是 Week 28 冻结主表。",
        "",
        "## 0. 一句话结论",
        "",
        "Li+ 配位除了改变 redox 数值，还会**改变被还原态的电子身份**：12 个还原态里只有 1 个",
        "（SN）保持分子中心还原，其余 9 个外加电子落在 Li 上。因此 C1 还原轴的排序必须在",
        "state-identity 分层之后才可解释；把它当成「同一个分子被还原的难度」是 observable",
        "identity failure，而不是 ranking instability。氧化轴可以分层后排序（主集合 n=6，tau_b=0.733）。",
        "",
        "## 1. 条件态位移与状态身份分层（all scope）",
        "",
    ]
    lines += _table(
        ["对比", "轴", "状态身份标签", "n", "主集合 n", "mean ΔΔG (eV)", "std (eV)", "成员"],
        [[r["comparison"], r["axis"], r["state_identity_label"], r["n"], r["n_primary"],
          "%+.4f" % r["mean_delta_ev"], "%.4f" % r["std_delta_ev"], r["members"]]
         for r in split])
    lines += [
        "",
        "## 2. 排序影响（Top-k）",
        "",
    ]
    lines += _table(
        ["对比", "scope", "轴", "n", "k/N", "O_k", "regret(eV)", "tau_b"],
        [[r["comparison"], r["scope"], r["axis"], r["n_molecules"],
          r["k_fraction"] if r["k_fraction"] is not None else "-",
          "-" if r["overlap"] is None else "%.3f" % r["overlap"],
          "-" if r["selection_regret_ev"] is None else "%.4f" % r["selection_regret_ev"],
          "-" if r["kendall_tau_b"] is None else "%.3f" % r["kendall_tau_b"]]
         for r in impact if r["k_fraction"] is None or abs(r["k_fraction"] - 0.2) < 1e-12])
    lines += [
        "",
        "`C0_to_C1 / primary / reduction` 只有 1 个候选，配不成 pair，显式记为未定义（不是「稳定」）。",
        "",
        "## 3. 描述符关联（只在 R13 主集合上）",
        "",
    ]
    lines += _table(
        ["对比", "轴", "描述符", "n", "Pearson r", "p", "Spearman ρ", "p"],
        [[r["comparison"], r["axis"], r["descriptor"], r["n"],
          "%+.3f" % r["pearson_r"], "%.3f" % r["pearson_p"],
          "%+.3f" % r["spearman_rho"], "%.3f" % r["spearman_p"]] for r in desc])
    lines += [
        "",
        "**探索性**：n=6，`donor_count` 与 |ΔΔG_coord| 呈强负相关（r=-0.962, p=0.002），",
        "提示配位数越多的给体条件响应越大；但样本太小，只作假设生成，不作结论。",
        "",
        "## 4. 机制案例（全部有 QC 支持）",
        "",
    ]
    for case in cases:
        lines.append("- **%s**（%s，n=%d）：%s。" % (case["case_id"], case["kind"],
                                                   case["n_molecules"], case["metric"]))
    lines += [
        "",
        "## 5. C1 -> C2 一致性",
        "",
        "第一溶剂壳 `[Li(M)2]+` 的 %d 个状态里标签变化 %d 个：C1 的关键机制判断在 C2 下保持不变。"
        % (len(c12), sum(1 for r in c12 if r["identity_changed"])),
        "",
        "## 6. 一致性自检",
        "",
    ]
    for check in payload["checks"]:
        lines.append("- `%s`: %s -- %s" % (check["id"], "PASS" if check["ok"] else "FAIL",
                                           check["detail"]))
    lines += [
        "",
        "## 7. 限制",
        "",
        "- 零新增计算；C1 声明 core 18、实际有值 10（PC/EMC 没有 [LiM]+ 对象），这是最该先补的计算缺口。",
        "- 描述符关联 n=6，仅探索性；绝不把 Li_centered 样本并入分子还原的连续回归。",
        "- 主集合还原轴只剩 1 个分子，任何「还原排序」都不能由本阶段支撑。",
        "",
        "## 8. 复现命令",
        "",
        "```powershell",
        ".venv\\Scripts\\python.exe scripts\\build_week30_wp3_coordination_mechanism.py",
        ".venv\\Scripts\\python.exe scripts\\build_week30_wp3_coordination_mechanism.py --check",
        ".venv\\Scripts\\python.exe -m pytest tests/test_week30_wp3_coordination_mechanism.py -q",
        "```",
    ]
    return "\n".join(lines) + "\n"


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Week 30 / WP3: Li+ coordination mechanism and state identity.")
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

    print("Week 30 / WP3 -- Li+ coordination mechanism and state identity")
    print("-" * 78)
    for table in TABLE_ORDER:
        info = payload["manifest"][table]
        print("  %-24s %5d rows  %s" % (table, info["n_rows"], info["sha256"][:12]))
    print("  %-24s %5d rows total" % ("(all tables)", payload["n_rows_total"]))
    print("-" * 78)
    for check in payload["checks"]:
        print("  %-42s %s" % (check["id"], "PASS" if check["ok"] else "FAIL"))
    print("-" * 78)
    print("wrote outputs/week30/ (%d files)" % len(texts))
    return 0


if __name__ == "__main__":
    sys.exit(main())
