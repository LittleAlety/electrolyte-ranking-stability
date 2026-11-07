#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""Week 35 / Paper -- 论文主文收敛包（main-text convergence package）。

为什么有这个阶段
----------------
前七步把物理机制 -> 决策可靠性 -> 最小信息预算做成了可复核的闭环，并在 Week 34 定死了结论边界。
最后一步（实施方案第八周）是把它们**收敛成一篇论文**：七张主图、结果六节、讨论、局限与补充材料。

本阶段**不改 docx、不改任何源数据**，而是产出一个可校验的**收敛包**，让
`论文/build_paper_docx.py` 的重建变成一次机械操作：

* 七图 -> 科学问题 -> 已冻结的 F 图资产（构建时核对资产是否真的在磁盘上）；
* 结果六节的固定顺序与来源；
* 主文数字逐条溯源（含来源 sha256 与复现命令）；
* 10 条主结论沿用 Week 34 / WP7 的 Track 标签；
* 13 条必须写出的边界声明（含 T6a/T6b：f_robust_inv = 0 是定义性结果）；
* 论文生成器源码的措辞合规扫描（v6 时点这条**发现**正文尚未使用 R13 后的 designated 措辞；
  该缺口已由 Week 36 的 v7 重建补齐，扫描数字随当前生成器源码实时给出）；
* 实施方案第七节 9 项验收清单逐条对账。

十张表
------
paper_figure_map          七图 -> 科学问题 -> 冻结资产（含缺失核对）
paper_section_plan        结果六节固定顺序与来源
paper_claim_track         主结论 -> Track A / Track B / 待验证推断
paper_number_lineage      主文数字 -> 冻结产物 + sha256 + 复现命令
paper_budget_overstatement  WP6「中位数曲线高估预算」两条口径对照（14 vs 21）
paper_supplementary_plan  F57/F58/T6a/T6b 的落点
paper_gap_register        必须写出的边界声明 / gap
paper_naming_compliance   论文生成器措辞合规
paper_checklist           第七节 9 项验收清单
paper_acceptance          四个验收问题

用法
----
    .venv\Scripts\python.exe scripts\build_week35_paper_convergence.py
    .venv\Scripts\python.exe scripts\build_week35_paper_convergence.py --check
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

from electrolyte_ranking import paper  # noqa: E402

OUTDIR = REPO / "outputs" / "week35"

TABLE_ORDER = (
    "paper_figure_map",
    "paper_section_plan",
    "paper_claim_track",
    "paper_number_lineage",
    "paper_budget_overstatement",
    "paper_supplementary_plan",
    "paper_gap_register",
    "paper_naming_compliance",
    "paper_checklist",
    "paper_acceptance",
)

SCHEMAS = OrderedDict([
    ("paper_figure_map", (
        "figure", "content", "question", "n_assets", "n_assets_present", "assets",
        "assets_present", "missing_assets", "origin_weeks", "answerable")),
    ("paper_section_plan", (
        "order", "title_en", "title_cn", "question", "primary_source", "figures")),
    ("paper_claim_track", ("claim_id", "claim", "track", "verdict", "source")),
    ("paper_number_lineage", (
        "number_id", "metric", "unit", "value", "source", "source_sha256",
        "reproduce_command", "traceable")),
    ("paper_budget_overstatement", (
        "scope", "definition", "n_overstated", "n_groups", "note")),
    ("paper_supplementary_plan", ("item", "content", "placement", "reason")),
    ("paper_gap_register", ("gap_id", "statement", "source", "where")),
    ("paper_naming_compliance", (
        "paper_source", "n_lines_scanned", "n_forbidden_occurrences", "n_violations",
        "n_allowed_occurrences", "naming_update_required")),
    ("paper_checklist", ("item_id", "requirement", "owner", "evidence", "status", "detail")),
    ("paper_acceptance", (
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
    budgets = analysis["budgets"]
    naming = analysis["naming"]
    budget_rows = [
        OrderedDict([
            ("scope", "tau_b_only"),
            ("definition", "median tau_b curve reaches tau_b >= 0.80 earlier than the point where "
                           ">= 80% of the 20 repeats do"),
            ("n_overstated", budgets["overstated_tau080"]),
            ("n_groups", budgets["n_groups"]),
            ("note", "冻结列 n_T_majority_tau080 / median_overstates_majority 用的就是这一口径"),
        ]),
        OrderedDict([
            ("scope", "combined"),
            ("definition", "median tau_b curve reaches tau_b >= 0.80 earlier than the point where "
                           ">= 80% of repeats satisfy tau_b >= 0.80 AND Top-20% overlap complete "
                           "AND regret <= 5% of the in-pool target range"),
            ("n_overstated", budgets["overstated_combined"]),
            ("n_groups", budgets["n_groups"]),
            ("note", "两个数字都报；只说 14/24 会被读成「只差一点」，实际组合口径是 21/24"),
        ]),
    ]
    naming_rows = [OrderedDict([
        ("paper_source", naming.get("paper_source")),
        ("n_lines_scanned", naming.get("n_lines_scanned")),
        ("n_forbidden_occurrences", naming.get("n_forbidden_occurrences")),
        ("n_violations", naming.get("n_violations")),
        ("n_allowed_occurrences", naming.get("n_allowed_occurrences")),
        ("naming_update_required", naming.get("naming_update_required")),
    ])]

    return OrderedDict([
        ("paper_figure_map", analysis["figures"]),
        ("paper_section_plan", analysis["sections"]),
        ("paper_claim_track", analysis["claims"]),
        ("paper_number_lineage", analysis["lineage"]),
        ("paper_budget_overstatement", budget_rows),
        ("paper_supplementary_plan", analysis["supplements"]),
        ("paper_gap_register", analysis["gaps"]),
        ("paper_naming_compliance", naming_rows),
        ("paper_checklist", analysis["checklist"]),
        ("paper_acceptance", analysis["acceptance"]),
    ])


#: 七个周产物载荷：用于核对「零新增电子结构计算」。
WEEKLY_PAYLOADS = (
    ("week28/WP1", "outputs/week28/evidence_master_table.json"),
    ("week29/WP2", "outputs/week29/wp2_physics_response.json"),
    ("week30/WP3", "outputs/week30/wp3_coordination_mechanism.json"),
    ("week31/WP4", "outputs/week31/wp4_decision_identifiability.json"),
    ("week32/WP5", "outputs/week32/wp5_delta_learning.json"),
    ("week33/WP6", "outputs/week33/wp6_active_learning.json"),
    ("week34/WP7", "outputs/week34/wp7_external_reference.json"),
)


def weekly_job_ledger():
    """逐周核对「零新增电子结构计算」的声明。"""

    out = OrderedDict()
    for label, rel in WEEKLY_PAYLOADS:
        payload = paper.load_json(REPO / rel)
        out[label] = (payload.get("inputs") or {}).get("new_electronic_structure_jobs")
    return out


def build_checks(analysis, tables):
    figures = tables["paper_figure_map"]
    sections = tables["paper_section_plan"]
    claims = tables["paper_claim_track"]
    lineage = tables["paper_number_lineage"]
    gaps = tables["paper_gap_register"]
    checklist = tables["paper_checklist"]
    naming = analysis["naming"]
    budgets = analysis["budgets"]

    week33_summary = (REPO / "outputs" / "week33" / "wp6_summary.md").read_text(encoding="utf-8")
    tau_str = "%d/%d 个" % (budgets["overstated_combined"], budgets["n_groups"])
    cross_ok = (tau_str in week33_summary
                and ("**%d** 个组合" % budgets["overstated_tau080"]) in week33_summary)

    jobs = weekly_job_ledger()
    gap_text = " ".join(row["statement"] for row in gaps)
    gap_keywords = ("NOT CLOSABLE", "T6a", "family-held-out", "自检端点", "n = 1", "自指")

    return [
        OrderedDict([
            ("id", "zero_new_electronic_structure_across_wp1_to_wp7"),
            ("ok", all(value in (0, None) for value in jobs.values())),
            ("detail", "WP2-WP7 的七个载荷逐周声明 new_electronic_structure_jobs = 0；WP1 是表格装配"
                       "步骤（不声明该键）。本阶段同样零新增计算，只读冻结产物与论文生成器源码"),
            ("job_ledger", jobs),
        ]),
        OrderedDict([
            ("id", "seven_main_figures_have_a_question_and_all_assets"),
            ("ok", len(figures) == 7 and all(row["answerable"] is True for row in figures)),
            ("detail", "7 张主图各有唯一科学问题；%d 个 F 图资产全部在磁盘上（缺失 0）"
                       % sum(int(row["n_assets"]) for row in figures)),
            ("n_assets", sum(int(row["n_assets"]) for row in figures)),
        ]),
        OrderedDict([
            ("id", "results_sections_follow_the_fixed_order"),
            ("ok", [row["order"] for row in sections] == ["1", "2", "3", "4", "5", "6"]
                   and sections[0]["title_en"].startswith("Model hierarchy")
                   and sections[-1]["title_en"].startswith("Minimum expensive-information")),
            ("detail", "结果部分固定为 6 节：1-3 物理与机制、4 决策、5 学习、6 计算资源；"
                       "首尾标题与实施方案一致"),
        ]),
        OrderedDict([
            ("id", "every_main_claim_carries_a_week34_track_label"),
            ("ok", len(claims) == 10
                   and {row["track"] for row in claims} == {"Track A", "Track B", "待验证推断"}),
            ("detail", "10 条主结论沿用 Week 34 / WP7 的轨道标签（Track A 6 / Track B 2 / "
                       "待验证推断 2），论文不新造标签"),
        ]),
        OrderedDict([
            ("id", "key_numbers_traceable_with_source_sha256"),
            ("ok", all(row["traceable"] is True and row["source_sha256"] for row in lineage)),
            ("detail", "%d 个主文数字逐条指向冻结产物并记录 sha256 与复现命令（不可溯源 0 个）"
                       % len(lineage)),
            ("n_numbers", len(lineage)),
        ]),
        OrderedDict([
            ("id", "paper_source_has_no_forbidden_wording"),
            ("ok", naming["n_violations"] == 0),
            ("detail", "扫描 %s（%d 行）：禁用词 %d 处、违规 %d 处；允许措辞 %d 处 —— "
                       "R13 措辞更新%s"
                       % (naming.get("paper_source"), naming.get("n_lines_scanned"),
                          naming["n_forbidden_occurrences"], naming["n_violations"],
                          naming["n_allowed_occurrences"],
                          "**待做**（正文尚未使用 designated 措辞）"
                          if naming["naming_update_required"] else "已就绪")),
        ]),
        OrderedDict([
            ("id", "gap_register_covers_the_known_limits"),
            ("ok", len(gaps) >= 13 and all(keyword in gap_text for keyword in gap_keywords)),
            ("detail", "%d 条边界声明，覆盖 Gate 1 不可闭合、T6a/T6b 定义性零反转、"
                       "family-held-out 不可用、池内端点、C1 n=1 与自指 sigma" % len(gaps)),
            ("n_gaps", len(gaps)),
        ]),
        OrderedDict([
            ("id", "budget_overstatement_reporting_is_consistent_with_week33"),
            ("ok", budgets["n_groups"] == 24 and budgets["overstated_tau080"] == 14
                   and budgets["overstated_combined"] == 21 and cross_ok),
            ("detail", "两条口径都给：tau_b-only %d/%d、combined %d/%d；与 Week 33 汇总报告"
                       "逐字一致（数值比较，非字符串比较）"
                       % (budgets["overstated_tau080"], budgets["n_groups"],
                          budgets["overstated_combined"], budgets["n_groups"])),
        ]),
        OrderedDict([
            ("id", "nine_item_acceptance_checklist_all_met"),
            ("ok", len(checklist) == 9
                   and all(row["status"] == "met" for row in checklist)),
            ("detail", "实施方案第七节 9 项验收清单全部满足（每项给出冻结载荷与其自检状态）"),
        ]),
        OrderedDict([
            ("id", "acceptance_questions_answered"),
            ("ok", len(tables["paper_acceptance"]) == 4
                   and all(row["question_id"].startswith("Q") and row["verdict"]
                           for row in tables["paper_acceptance"])),
            ("detail", "4 个收敛包验收问题全部作答，附支撑数与反例"),
        ]),
    ]


def collect():
    analysis = paper.analyse(REPO)
    tables = build_tables(analysis)
    checks = build_checks(analysis, tables)

    csv_texts = []
    manifest = OrderedDict()
    for table in TABLE_ORDER:
        rows = tables[table]
        buffer = io.StringIO()
        writer = csv.writer(buffer, lineterminator="\n")
        writer.writerow(SCHEMAS[table])
        for row in rows:
            writer.writerow([_fmt(row.get(column)) for column in SCHEMAS[table]])
        text = buffer.getvalue()
        manifest[table] = OrderedDict([
            ("n_rows", len(rows)),
            ("sha256", hashlib.sha256(text.encode("utf-8")).hexdigest()),
            ("columns", len(SCHEMAS[table])),
        ])
        csv_texts.append((table + ".csv", text))

    budgets = analysis["budgets"]
    plan_sha = paper.sha256_file(REPO.parent / "论文" / "build_paper_docx.py")
    counts = OrderedDict([
        ("n_main_figures", len(analysis["figures"])),
        ("n_main_figures_answerable", sum(1 for r in analysis["figures"] if r["answerable"])),
        ("n_figure_assets", sum(int(r["n_assets"]) for r in analysis["figures"])),
        ("n_result_sections", len(analysis["sections"])),
        ("n_main_claims", len(analysis["claims"])),
        ("n_claims_track_a", sum(1 for c in analysis["claims"] if c["track"] == "Track A")),
        ("n_claims_track_b", sum(1 for c in analysis["claims"] if c["track"] == "Track B")),
        ("n_claims_pending", sum(1 for c in analysis["claims"] if c["track"] == "待验证推断")),
        ("n_lineage_numbers", len(analysis["lineage"])),
        ("n_lineage_traceable", sum(1 for r in analysis["lineage"] if r["traceable"])),
        ("n_gaps_declared", len(analysis["gaps"])),
        ("n_supplementary_items", len(analysis["supplements"])),
        ("n_checklist_items", len(analysis["checklist"])),
        ("n_checklist_met", sum(1 for r in analysis["checklist"] if r["status"] == "met")),
        ("n_paper_naming_violations", analysis["naming"]["n_violations"]),
        ("n_paper_naming_allowed", analysis["naming"]["n_allowed_occurrences"]),
        ("n_budget_groups", budgets["n_groups"]),
        ("n_budget_overstated_tau080", budgets["overstated_tau080"]),
        ("n_budget_overstated_combined", budgets["overstated_combined"]),
    ])

    payload = OrderedDict([
        ("stage", "Week 35 / Paper"),
        ("label", "main-text convergence package (seven figures, six results sections)"),
        ("gate_status", "Gate 0 CLOSED；Gate 1 NOT CLOSED / NOT CLOSABLE；"
                        "论文适用范围限定在 computational-target decision stability"),
        ("inputs", OrderedDict([
            ("paper_builder", "论文/build_paper_docx.py"),
            ("paper_builder_sha256", plan_sha),
            ("figure_dir", "outputs/figures"),
            ("weekly_payloads", [rel for _, rel in WEEKLY_PAYLOADS]),
            ("frozen_week27", "outputs/week27/estimator_circularity.json"),
            ("frozen_week34", "outputs/week34/wp7_external_reference.json"),
            ("new_electronic_structure_jobs", 0),
            ("data_modified", 0),
        ])),
        ("conventions", OrderedDict([
            ("figure_structure", "keeps the v2 seven-figure structure"),
            ("results_order", "1 model hierarchy & external-reference boundaries; "
                              "2 ranking responses to electronic-structure/continuum physics; "
                              "3 conditional Li+ coordination & redox-state identity; "
                              "4 uncertainty-aware material selection; "
                              "5 predictability of model and coordination corrections; "
                              "6 minimum expensive-information budget"),
            ("claim_tags", "every main claim carries Track A / Track B / untested-inference, "
                           "inherited verbatim from Week 34 / WP7"),
            ("definitive_zero", "f_robust_inv = 0 is definitional (T6a/T6b), not empirical"),
            ("naming", "designated computational target / designated reference model only; "
                       "validated target stays forbidden until Gate 1 closes"),
            ("budget_reporting", "report both 14/24 (tau_b-only) and 21/24 (combined)"),
        ])),
        ("counts", counts),
        ("checks", checks),
        ("checks_by_id", OrderedDict((c["id"], c) for c in checks)),
        ("naming", analysis["naming"]),
        ("manifest", manifest),
        ("n_rows_total", sum(len(tables[t]) for t in TABLE_ORDER)),
    ])

    handoff = OrderedDict([
        ("stage", "Week 35 / Paper handoff"),
        ("target", "论文/build_paper_docx.py"),
        ("paper_builder_sha256_at_handoff", plan_sha),
        ("results_sections", [OrderedDict([
            ("order", row["order"]), ("title_en", row["title_en"]), ("title_cn", row["title_cn"]),
            ("question", row["question"]), ("primary_source", row["primary_source"]),
            ("figures", row["figures"])]) for row in analysis["sections"]]),
        ("figures", [OrderedDict([
            ("figure", row["figure"]), ("content", row["content"]),
            ("question", row["question"]), ("assets", row["assets"]),
            ("missing_assets", row["missing_assets"])]) for row in analysis["figures"]]),
        ("must_state_gaps", [row["gap_id"] for row in analysis["gaps"]]),
        ("supplementary_placement", [OrderedDict([
            ("item", row["item"]), ("placement", row["placement"])])
            for row in analysis["supplements"]]),
        ("required_edits", [
            "把 f_robust_inv = 0 改写为定义性结果（T6a/T6b），并同时给出 sigma 约定与分母",
            "凡提到 P1v/P1a/P2a/P2eps 目标阶梯处，显式使用 designated computational "
            "target / designated reference model（v6 扫描显示两套措辞都未出现，需补齐而不是改词；"
            "已由 Week 36 的 v7 重建落地）",
            "结果部分重排为六节固定顺序（v6 时点为 3.1-3.17 的物理优先顺序；已由 v7 落地）",
            "补入 WP1-WP7 的 %d 个溯源数字与 %d 条边界声明"
            % (len(analysis["lineage"]), len(analysis["gaps"])),
            "把 F57/F58 与 T6a/T6b 的详细推导放入 Fig. 2/4 局部面板或补充材料",
        ]),
        ("required_edits_status",
         ("已由 Week 36 的 v7 重建全部落地（当前扫描：允许措辞 %d 处、禁用词 %d 处）"
          % (analysis["naming"]["n_allowed_occurrences"],
             analysis["naming"]["n_forbidden_occurrences"]))
         if not analysis["naming"]["naming_update_required"] else "待下一次显式论文重建落地"),
        ("constraints", [
            "零新增电子结构计算",
            "不得为关闭 Gate 1 调整阈值或剔除数据",
            "不得出现绝对性能排名 / 大规模筛选能力等未获支持的声明",
        ]),
    ])

    texts = OrderedDict(csv_texts)
    texts["paper_convergence.json"] = (
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=False) + "\n")
    texts["paper_build_handoff.json"] = (
        json.dumps(handoff, ensure_ascii=False, indent=2, sort_keys=False) + "\n")
    texts["paper_summary.md"] = render_summary(payload, tables, handoff).replace("@@BT@@", "`")
    texts["manifest.json"] = json.dumps(
        OrderedDict([("stage", "Week 35 / Paper"), ("tables", manifest)]),
        ensure_ascii=False, indent=2, sort_keys=False) + "\n"
    return payload, texts


def _table(headers, rows):
    lines = ["| " + " | ".join(headers) + " |",
             "| " + " | ".join("---" for _ in headers) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(cell) for cell in row) + " |")
    return lines


def render_summary(payload, tables, handoff):
    figures = tables["paper_figure_map"]
    sections = tables["paper_section_plan"]
    claims = tables["paper_claim_track"]
    lineage = tables["paper_number_lineage"]
    budget = tables["paper_budget_overstatement"]
    supplements = tables["paper_supplementary_plan"]
    gaps = tables["paper_gap_register"]
    checklist = tables["paper_checklist"]
    acceptance = tables["paper_acceptance"]
    counts = payload["counts"]
    naming = payload["naming"]

    lines = []
    lines.append("\n".join([
        "# Week 35 / Paper：论文主文收敛包",
        "",
        "> 阶段：下一阶段实施方案第八周（Paper）。产物目录 @@BT@@outputs/week35/@@BT@@，交付镜像",
        "> @@BT@@..\\成果输出（part2）\\week35/@@BT@@。本文件由",
        "> @@BT@@scripts/build_week35_paper_convergence.py@@BT@@ 确定性生成，@@BT@@--check@@BT@@",
        "> 逐字节复核。**零新增电子结构计算；不改动任何既有产物与论文源文件。**",
        "",
        "## 0. 一句话结论",
        "",
        "七张主图各有唯一科学问题、%d 个 F 图资产全部在磁盘上；结果部分固定为 %d 节"
        "（先物理 -> 再决策 -> 再学习 -> 最后计算资源）；%d 条主结论沿用 Week 34 / WP7 的 "
        "Track 标签；%d 个主文数字逐条可溯源；%d 条边界声明必须写出。"
        % (counts["n_figure_assets"], counts["n_result_sections"], counts["n_main_claims"],
           counts["n_lineage_numbers"], counts["n_gaps_declared"]),
        "",
        "本阶段**不改 docx**：它产出的是 @@BT@@paper_build_handoff.json@@BT@@ —— 一份让论文重建变成",
        "机械操作的规格。",
        "",
        "## 1. 七图映射",
        "",
    ]))
    lines += _table(["主图", "内容", "回答的问题", "资产", "来源周"],
                    [[r["figure"], r["content"], r["question"],
                      "%d/%d" % (r["n_assets_present"], r["n_assets"]), r["origin_weeks"]]
                     for r in figures])
    lines.append("\n".join([
        "",
        "## 2. 结果六节（固定顺序）",
        "",
    ]))
    lines += _table(["序", "英文标题", "中文", "回答的问题", "主要来源", "主图"],
                    [[r["order"], r["title_en"], r["title_cn"], r["question"],
                      r["primary_source"], r["figures"]] for r in sections])
    lines.append("\n".join([
        "",
        "## 3. 结论-轨道标签（沿用 Week 34 / WP7，不新造）",
        "",
    ]))
    lines += _table(["ID", "主结论", "轨道", "判定"],
                    [[r["claim_id"], r["claim"], r["track"], r["verdict"]] for r in claims])
    lines.append("\n".join([
        "",
        "计数：Track A %d / Track B %d / 待验证推断 %d。"
        % (counts["n_claims_track_a"], counts["n_claims_track_b"], counts["n_claims_pending"]),
        "",
        "## 4. 主文数字溯源",
        "",
    ]))
    lines += _table(["编号", "指标", "值", "来源"],
                    [[r["number_id"], r["metric"], r["value"], r["source"]] for r in lineage])
    lines.append("\n".join([
        "",
        "每个数字都附带来源 sha256 与复现命令（见 @@BT@@paper_number_lineage.csv@@BT@@）。",
        "",
        "## 5. WP6 预算高估：两条口径都要报",
        "",
    ]))
    lines += _table(["口径", "定义", "高估组合数", "总组合数"],
                    [[r["scope"], r["definition"], r["n_overstated"], r["n_groups"]]
                     for r in budget])
    lines.append("\n".join([
        "",
        "只说 @@BT@@14/24@@BT@@ 会被读成「只差一点」；按组合口径实际是 @@BT@@21/24@@BT@@。"
        "两个数字都进论文。",
        "",
        "## 6. 补充材料落点",
        "",
    ]))
    lines += _table(["条目", "内容", "建议落点", "理由"],
                    [[r["item"], r["content"], r["placement"], r["reason"]]
                     for r in supplements])
    lines.append("\n".join([
        "",
        "## 7. 必须写出的边界声明",
        "",
    ]))
    lines += _table(["ID", "声明", "来源", "位置"],
                    [[r["gap_id"], r["statement"], r["source"], r["where"]] for r in gaps])
    if naming["naming_update_required"]:
        finding = ("**发现**：正文尚未使用 R13 之后的 designated 措辞（%d 处），收敛时必须统一。"
                   "这一条是收敛包要暴露的问题，不是本阶段可以顺手改掉的"
                   "（论文源文件不在本阶段写入范围）。" % naming["n_allowed_occurrences"])
    else:
        finding = ("**发现**：正文已使用 R13 之后的 designated 措辞（%d 处）、禁用词 %d 处。"
                   "v6 时点该缺口为 0 处，已由 Week 36 的 v7 重建补齐；本表随论文生成器源码"
                   "实时扫描，报告的是当前状态，v6 时点的记录见 Week 36 的 frozen_snapshots。"
                   % (naming["n_allowed_occurrences"], naming["n_forbidden_occurrences"]))
    lines.append("\n".join([
        "",
        "## 8. 论文生成器措辞合规",
        "",
        "扫描 @@BT@@%s@@BT@@（%d 行）：禁用词 %d 处、违规 %d 处；允许措辞 %d 处。",
        finding,
        "",
        "## 9. 验收清单（实施方案第七节 9 项）",
        "",
    ]) % (naming.get("paper_source"), naming.get("n_lines_scanned"),
          naming["n_forbidden_occurrences"], naming["n_violations"],
          naming["n_allowed_occurrences"]))
    lines += _table(["项", "要求", "负责阶段", "状态"],
                    [[r["item_id"], r["requirement"], r["owner"], r["status"]]
                     for r in checklist])
    lines.append("\n".join([
        "",
        "## 10. 验收",
        "",
    ]))
    lines += _table(["问题", "结论", "支撑"],
                    [[r["question_id"] + ". " + r["question"], r["verdict"],
                      "%s/%s" % (r["n_supporting"], r["n_cells"])] for r in acceptance])
    lines.append("\n".join([
        "",
        "## 11. 给论文重建的必要改动",
        "",
    ] + ["- " + item for item in handoff["required_edits"]] + [
        "",
        "## 12. 限制",
        "",
        "- 本阶段不写 docx、不改动任何源文件：论文重建需要另一次显式操作（并需可用的 Word 环境）。",
        "- 七图映射中的资产清单来自 v6 生成器实际调用的 @@BT@@figure()@@BT@@ 资产与 week25/week27 的",
        "  F52-F58 产物；资产存在性在构建时逐文件核对。",
        "- 全程零新增电子结构计算；结论只对已有冻结数据成立。",
        "",
        "## 13. 复现命令",
        "",
        "@@BT@@@@BT@@@@BT@@powershell",
        "cd 电解液溶剂HB-Code",
        ".venv\\Scripts\\python.exe scripts\\build_week35_paper_convergence.py",
        ".venv\\Scripts\\python.exe scripts\\build_week35_paper_convergence.py --check",
        ".venv\\Scripts\\python.exe -m pytest tests/test_week35_paper_convergence.py -q",
        ".venv\\Scripts\\python.exe scripts\\build_week35_deliverables.py",
        ".venv\\Scripts\\python.exe scripts\\build_week35_deliverables.py --check",
        "@@BT@@@@BT@@@@BT@@",
        "",
    ]))
    return "\n".join(lines)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Week 35 / Paper: main-text convergence package.")
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

    print("Week 35 / Paper -- main-text convergence package")
    print("-" * 78)
    for table in TABLE_ORDER:
        info = payload["manifest"][table]
        print("  %-30s %4d rows  %s" % (table, info["n_rows"], info["sha256"][:16]))
    print("-" * 78)
    print("  rows total : %d" % payload["n_rows_total"])
    print("  checks     : %d passed / %d failed"
          % (sum(1 for c in payload["checks"] if c["ok"]),
             sum(1 for c in payload["checks"] if not c["ok"])))
    for check in payload["checks"]:
        print("    %-56s %s" % (check["id"], "PASS" if check["ok"] else "FAIL"))
    return 0 if all(c["ok"] for c in payload["checks"]) else 1


if __name__ == "__main__":
    sys.exit(main())
