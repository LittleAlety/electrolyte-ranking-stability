#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""Week 34 / WP7 -- 外部验证与结论边界（external reference & Gate 1 boundary）。

为什么有这个阶段
----------------
前几步（WP1-WP6）把「在指定 computational target 下，哪些缺失物理会改变筛选决策、候选能不能
被分辨、便宜模型能不能学到位移、最少要花多少昂贵标签」做成了内部可复核的闭环。WP7 不新增任何
结论，只做三件事：

1. **把 Gate 1 摆正**：既不能因为内部结果丰富就跳过它，也不能为了让论文好看而强迫它关闭。
   本阶段读出冻结的双轨判定，逐条对账预注册关闭条件，把「哪一条没过」写清楚。
2. **对现有外部 anchors 做条件一致性与 provenance 复核**，而不是为了提高 tau 人为筛掉不一致
   数据。所有 anchor 行（含 31 行 estimates、3 行 secondary、14 行 within-series）**一行不删**。
3. **给每个主结论贴轨道标签**：Track A（computational decision stability）/ Track B
   （external reference validity）/ 待验证推断。

十张表
------
anchor_inventory           逐 anchor 文件的条件一致性、provenance 与排序层可用性
anchor_row_audit           31 行绝对标定 anchor 的逐行未被升级原因（一行不少）
ordering_recheck           within-series Kendall tau_b 的独立重算 vs 冻结值
gate1_components           Gate 1 两层组件（排序一致性 / 绝对标定 / 还原轴 / 上游 / 可闭合性）
gate1_status               预注册关闭条件逐条对账（含 provenance 条件）
track_separation           Track A / Track B 的范围与结论权限
claim_track_assignment     10 条主结论 -> 轨道映射
naming_compliance          措辞合规扫描（禁用词只允许出现在规则文本里）
supplemental_compute_triggers  何时才值得新增电子结构计算（实施方案第五节）
wp7_acceptance             四个验收问题的结论与证据

用法
----
    .venv\Scripts\python.exe scripts\build_week34_wp7_external_reference_boundary.py
    .venv\Scripts\python.exe scripts\build_week34_wp7_external_reference_boundary.py --check
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

from electrolyte_ranking import wp7  # noqa: E402

OUTDIR = REPO / "outputs" / "week34"

TABLE_ORDER = (
    "anchor_inventory",
    "anchor_row_audit",
    "ordering_recheck",
    "gate1_components",
    "gate1_status",
    "track_separation",
    "claim_track_assignment",
    "naming_compliance",
    "supplemental_compute_triggers",
    "wp7_acceptance",
)

SCHEMAS = OrderedDict([
    ("anchor_inventory", (
        "anchor_file", "phase", "purpose", "n_rows", "n_series_ids", "series_ids", "properties",
        "n_distinct_reference_electrode", "n_distinct_electrode", "n_distinct_criterion",
        "n_distinct_supporting_electrolyte", "same_apparatus", "same_criterion", "single_series",
        "provenance_kinds", "admissible_for_ordering_tier", "admissibility_reason")),
    ("anchor_row_audit", (
        "row_id", "species", "property", "value_V", "reference_electrode", "declared_method",
        "audit_species", "evidence_kind", "adjudication")),
    ("ordering_recheck", (
        "series_id", "property", "source_doi", "n_rows", "n_species_usable",
        "n_species_missing_model_value", "n_pairs", "n_pairs_usable", "n_pairs_tied_experiment",
        "n_pairs_tied_model", "concordant", "discordant", "tau_b", "verdict", "matches_frozen")),
    ("gate1_components", (
        "component", "track", "status", "observed", "threshold", "decision_relevance", "source")),
    ("gate1_status", ("condition", "required", "observed", "met", "note")),
    ("track_separation", (
        "track", "name", "status", "question", "scope", "may_conclude", "promotion_condition")),
    ("claim_track_assignment", (
        "claim_id", "claim", "track", "verdict", "source", "scope_note")),
    ("naming_compliance", (
        "file", "n_lines", "n_forbidden_occurrences", "n_violations",
        "n_allowed_occurrences", "classification")),
    ("supplemental_compute_triggers", ("trigger", "priority_action", "not_recommended")),
    ("wp7_acceptance", (
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
    recompute = analysis["recompute"]
    rows = []
    for item in recompute["detail"]:
        row = OrderedDict([(key, item[key]) for key in (
            "series_id", "property", "source_doi", "n_rows", "n_species_usable",
            "n_species_missing_model_value", "n_pairs", "n_pairs_usable",
            "n_pairs_tied_experiment", "n_pairs_tied_model", "concordant", "discordant",
            "tau_b")])
        row["verdict"] = recompute["verdict"]
        row["matches_frozen"] = recompute["matches_frozen"]
        rows.append(row)
    overall = recompute["recomputed"]
    rows.append(OrderedDict([
        ("series_id", "(all)"), ("property", "(pooled)"), ("source_doi", ""),
        ("n_rows", overall["n_rows"]),
        ("n_species_usable", sum(item["n_species_usable"] for item in recompute["detail"])),
        ("n_species_missing_model_value", overall["n_skipped_missing_model_value"]),
        ("n_pairs", overall["n_pairs"]),
        ("n_pairs_usable", overall["n_pairs"]),
        ("n_pairs_tied_experiment", overall["n_pairs_tied_experiment"]),
        ("n_pairs_tied_model", overall["n_pairs_tied_model"]),
        ("concordant", overall["concordant"]),
        ("discordant", overall["discordant"]),
        ("tau_b", overall["tau_b"]),
        ("verdict", recompute["verdict"]),
        ("matches_frozen", recompute["matches_frozen"]),
    ]))

    return OrderedDict([
        ("anchor_inventory", analysis["inventory"]),
        ("anchor_row_audit", analysis["row_audit"]),
        ("ordering_recheck", rows),
        ("gate1_components", analysis["components"]),
        ("gate1_status", analysis["status_rows"]),
        ("track_separation", analysis["tracks"]),
        ("claim_track_assignment", analysis["claims"]),
        ("naming_compliance", analysis["compliance_rows"]),
        ("supplemental_compute_triggers", analysis["triggers"]),
        ("wp7_acceptance", analysis["acceptance"]),
    ])


def build_checks(analysis, tables):
    recompute = analysis["recompute"]
    inventory = tables["anchor_inventory"]
    row_audit = tables["anchor_row_audit"]
    status_rows = tables["gate1_status"]
    claims = tables["claim_track_assignment"]
    compliance = analysis["compliance_summary"]
    gate1 = analysis["gate1"]
    frozen_ordering = analysis["frozen_ordering"]
    triggers = tables["supplemental_compute_triggers"]

    anchor_row_total = sum(row["n_rows"] for row in inventory)
    frozen_rows_total = (frozen_ordering["n_rows"] + 14 + 3 + 31 + 39)
    unmet = [row["condition"] for row in status_rows if not row["met"]]
    decisive = next((row for row in status_rows if row["condition"] == "min_tau_b"), None)
    tracks = {row["track"] for row in claims}
    caveat = gate1["track_B"]["components"]["closability"]["scope_caveat"]

    return [
        OrderedDict([
            ("id", "zero_new_electronic_structure_and_zero_row_deletion"),
            ("ok", anchor_row_total == 101 and len(row_audit) == 31 and anchor_row_total == frozen_rows_total),
            ("detail", "%d 个 anchor 文件共 %d 行全部保留（含 31 行 est、3 行 secondary、14 行 "
                       "within-series、39 行 gas-phase）；未被升级 = 未被删除；零新增电子结构计算"
                       % (len(inventory), anchor_row_total)),
            ("anchor_rows_total", anchor_row_total),
        ]),
        OrderedDict([
            ("id", "ordering_recheck_reproduces_the_frozen_value"),
            ("ok", bool(recompute["matches_frozen"])),
            ("detail", "独立重算 within-series tau_b=%.6f、concordant=%d / discordant=%d / "
                       "n_pairs=%d，与冻结 week25 判定逐位一致（最大差 %.3g）"
                       % (recompute["recomputed"]["tau_b"], recompute["recomputed"]["concordant"],
                          recompute["recomputed"]["discordant"], recompute["recomputed"]["n_pairs"],
                          max(v for v in recompute["diffs"].values() if v is not None))),
            ("diffs", recompute["diffs"]),
        ]),
        OrderedDict([
            ("id", "no_row_or_threshold_was_touched_to_raise_tau"),
            ("ok", bool(recompute["recomputed"]["n_rows"] == frozen_ordering["n_rows"] == 14
                        and wp7.MIN_PAIRS == 18 and wp7.MIN_TAU_B == 0.9
                        and frozen_ordering["criterion"]["min_pairs"] == 18
                        and frozen_ordering["criterion"]["min_tau_b"] == 0.9)),
            ("detail", "within-series 仍为 14 行；阈值仍为 n_pairs>=18 / tau_b>=0.9（未新造、未放宽）；"
                       "本阶段未剔除任何行、未替换任何模型列"),
            ("n_rows_within_series", recompute["recomputed"]["n_rows"]),
        ]),
        OrderedDict([
            ("id", "gate1_is_neither_skipped_nor_forced_closed"),
            ("ok", gate1["gate1_status"] == "NOT CLOSED"
                   and gate1["gate1_closability"] == "NOT CLOSABLE"
                   and bool(unmet) and decisive is not None and not decisive["met"]),
            ("detail", "Gate 1 维持 %s / %s；未达成条件 %d 条（%s），其中决定性项为 min_tau_b"
                       % (gate1["gate1_status"], gate1["gate1_closability"], len(unmet),
                          ", ".join(unmet))),
            ("unmet_conditions", unmet),
        ]),
        OrderedDict([
            ("id", "closure_conditions_fully_reported"),
            ("ok", len(status_rows) == 8
                   and {row["condition"] for row in status_rows} >= {
                       "same_apparatus", "same_criterion", "same_state",
                       "min_species_covering_core_set", "min_pairs", "min_tau_b",
                       "primary_source_provenance", "absolute_calibration_upgrade"}),
            ("detail", "8 条预注册关闭条件逐条对账（含 provenance 条件）：满足 %d 条、未满足 %d 条"
                       % (len(status_rows) - len(unmet), len(unmet))),
            ("n_conditions", len(status_rows)),
        ]),
        OrderedDict([
            ("id", "every_main_claim_carries_a_track_label"),
            ("ok", tracks == {"Track A", "Track B", "待验证推断"} and len(claims) == 10),
            ("detail", "%d 条主结论全部标注轨道：Track A %d / Track B %d / 待验证推断 %d"
                       % (len(claims),
                          sum(1 for c in claims if c["track"] == "Track A"),
                          sum(1 for c in claims if c["track"] == "Track B"),
                          sum(1 for c in claims if c["track"] == "待验证推断"))),
            ("tracks", sorted(tracks)),
        ]),
        OrderedDict([
            ("id", "naming_compliance_has_no_violations"),
            ("ok", compliance["n_violations"] == 0 and compliance["n_files_scanned"] > 0),
            ("detail", "扫描 %d 个交付文件：禁用词出现 %d 次全部属于规则文本（禁用->允许 对照），"
                       "违规 0 处；允许措辞出现 %d 次"
                       % (compliance["n_files_scanned"], compliance["n_forbidden_occurrences"],
                          compliance["n_allowed_occurrences"])),
            ("summary", compliance),
        ]),
        OrderedDict([
            ("id", "closability_scope_caveat_preserved"),
            ("ok", "NOT CLOSABLE" in caveat and "NO SUCH DATA" in caveat),
            ("detail", "负结果的可证伪边界随产物一起发布：NOT CLOSABLE != NO SUCH DATA EXIST "
                       "ANYWHERE（若日后出现满足全部预注册条件的同源序列，本判定应被推翻）"),
        ]),
        OrderedDict([
            ("id", "supplemental_compute_triggers_are_the_plan_table"),
            ("ok", len(triggers) == 5 and all(row["trigger"] and row["priority_action"]
                                              and row["not_recommended"] for row in triggers)),
            ("detail", "5 条「何时才值得新增电子结构计算」的触发条件与「不建议做什么」全部列出，"
                       "含「不为关闭 Gate 1 调整阈值」"),
            ("n_triggers", len(triggers)),
        ]),
        OrderedDict([
            ("id", "acceptance_questions_answered"),
            ("ok", len(tables["wp7_acceptance"]) == 4
                   and all(row["question_id"].startswith("Q") and row["verdict"]
                           for row in tables["wp7_acceptance"])),
            ("detail", "4 个 WP7 验收问题全部作答，附支撑数与反例"),
        ]),
    ]


def collect():
    analysis = wp7.analyse(REPO)
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

    recompute = analysis["recompute"]
    gate1 = analysis["gate1"]
    counts = OrderedDict([
        ("n_anchor_files", len(analysis["inventory"])),
        ("n_anchor_rows", sum(row["n_rows"] for row in analysis["inventory"])),
        ("n_anchor_rows_audited", len(analysis["row_audit"])),
        ("n_gate1_conditions", len(analysis["status_rows"])),
        ("n_gate1_conditions_met", sum(1 for r in analysis["status_rows"] if r["met"])),
        ("n_gate1_components", len(analysis["components"])),
        ("n_claims", len(analysis["claims"])),
        ("n_claims_track_a", sum(1 for c in analysis["claims"] if c["track"] == "Track A")),
        ("n_claims_track_b", sum(1 for c in analysis["claims"] if c["track"] == "Track B")),
        ("n_claims_pending", sum(1 for c in analysis["claims"] if c["track"] == "待验证推断")),
        ("n_files_scanned_for_naming", analysis["compliance_summary"]["n_files_scanned"]),
        ("n_naming_violations", analysis["compliance_summary"]["n_violations"]),
        ("n_triggers", len(analysis["triggers"])),
    ])

    payload = OrderedDict([
        ("stage", "Week 34 / WP7"),
        ("label", "external reference & conclusion boundary (Gate 1 re-audit)"),
        ("gate_status", "Gate 0 CLOSED；Gate 1 NOT CLOSED / NOT CLOSABLE（WP7 只复核、不关闭、不跳过）"),
        ("inputs", OrderedDict([
            ("gate1_dual_track", "/".join(wp7.GATE1_JSON)),
            ("ordering_consistency", "/".join(wp7.ORDERING_JSON)),
            ("anchor_audit", "/".join(wp7.ANCHOR_AUDIT_JSON)),
            ("reduction_secondary", "/".join(wp7.REDUCTION_SECONDARY_JSON)),
            ("within_series_table", "/".join(wp7.WITHIN_SERIES)),
            ("target_model", "/".join(wp7.TARGET_MODEL)),
            ("anchor_files", [rel for rel, _, _ in wp7.ANCHOR_FILES]),
            ("new_electronic_structure_jobs", 0),
            ("anchor_rows_deleted", 0),
            ("thresholds_modified", 0),
        ])),
        ("conventions", OrderedDict([
            ("tracks", "Track A = computational decision stability; "
                       "Track B = external reference validity (NOT CLOSED / NOT CLOSABLE)"),
            ("thresholds", "n_pairs >= %d, Kendall tau_b >= %.1f (frozen, not re-tuned)"
                           % (wp7.MIN_PAIRS, wp7.MIN_TAU_B)),
            ("removal_rule", "no anchor row and no candidate pair was removed to raise tau"),
            ("naming", "designated computational target / designated reference model only; "
                       "validated target is forbidden until Gate 1 closes"),
            ("negative_result", "NOT CLOSABLE != NO SUCH DATA EXIST ANYWHERE "
                                "(falsifiable negative result)"),
            ("gate1_status_verbatim", "%s / %s" % (gate1["gate1_status"],
                                                   gate1["gate1_closability"])),
        ])),
        ("recompute", recompute),
        ("counts", counts),
        ("checks", checks),
        ("checks_by_id", OrderedDict((c["id"], c) for c in checks)),
        ("naming_hits", analysis["compliance_hits"]),
        ("manifest", manifest),
        ("n_rows_total", sum(len(tables[t]) for t in TABLE_ORDER)),
    ])

    texts = OrderedDict(csv_texts)
    texts["wp7_external_reference.json"] = (
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=False) + "\n")
    texts["wp7_summary.md"] = render_summary(payload, tables).replace("@@BT@@", "`")
    texts["manifest.json"] = json.dumps(
        OrderedDict([("stage", "Week 34 / WP7"), ("tables", manifest)]),
        ensure_ascii=False, indent=2, sort_keys=False) + "\n"
    return payload, texts


def _table(headers, rows):
    lines = ["| " + " | ".join(headers) + " |",
             "| " + " | ".join("---" for _ in headers) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(cell) for cell in row) + " |")
    return lines


def render_summary(payload, tables):
    inventory = tables["anchor_inventory"]
    recompute = payload["recompute"]
    status_rows = tables["gate1_status"]
    components = tables["gate1_components"]
    tracks = tables["track_separation"]
    claims = tables["claim_track_assignment"]
    naming_rows = tables["naming_compliance"]
    triggers = tables["supplemental_compute_triggers"]
    acceptance = tables["wp7_acceptance"]
    counts = payload["counts"]
    unmet = [row["condition"] for row in status_rows if not row["met"]]
    n_allowed = sum(int(row["n_allowed_occurrences"]) for row in naming_rows)
    n_forbidden = len(payload["naming_hits"])
    status_verbatim = payload["conventions"]["gate1_status_verbatim"]
    gate1_status, gate1_closability = status_verbatim.split(" / ")
    tau_b = recompute["recomputed"]["tau_b"]

    lines = []

    lines.append("\n".join([
        "# Week 34 / WP7：外部验证与结论边界",
        "",
        "> 阶段：下一阶段实施方案 WP7。产物目录 @@BT@@outputs/week34/@@BT@@，交付镜像",
        "> @@BT@@..\\成果输出（part2）\\week34/@@BT@@。本文件由",
        "> @@BT@@scripts/build_week34_wp7_external_reference_boundary.py@@BT@@ 确定性生成，",
        "> @@BT@@--check@@BT@@ 逐字节复核。**零新增电子结构计算、零数据剔除、零阈值改动**。",
        "",
        "## 0. 一句话结论",
        "",
        "Gate 1 维持 **%s / %s**：它既没有被跳过，也没有被强迫关闭。预注册的 8 条关闭条件里有 "
        "**%d 条**未达成（%s），其中决定性的一条是排序一致性 **tau_b = %.4f < %.2f**。"
        % (gate1_status, gate1_closability, len(unmet), "、".join(unmet), tau_b, 0.9),
        "",
        "与之独立的是 Track A：WP1-WP6 的排序、选择与预算结论在 designated computational "
        "target 下成立，不受 Track B 未闭合影响。",
        "",
        "## 1. 两条轨道：范围与结论权限",
        "",
    ]))

    lines += _table(["轨道", "名称", "状态", "问题", "可以下什么结论", "升级条件"],
                    [[r["track"], r["name"], r["status"], r["question"], r["may_conclude"],
                      r["promotion_condition"]] for r in tracks])

    lines.append("\n".join([
        "",
        "**独立性规则**：Track B 未闭合**不**使 Track A 失效；它只限制「绝对尺度 / 真实排序」",
        "这类声明的强度。",
        "",
        "## 2. Gate 1 组件状态",
        "",
    ]))

    lines += _table(["组件", "状态", "观测值", "阈值", "对决策的意义"],
                    [[r["component"], r["status"], r["observed"], r["threshold"],
                      r["decision_relevance"]] for r in components])

    lines.append("\n".join([
        "",
        "## 3. 预注册关闭条件逐条对账",
        "",
    ]))

    lines += _table(["条件", "要求", "现状", "是否满足", "备注"],
                    [[r["condition"], r["required"], r["observed"],
                      "是" if r["met"] else "**否**", r["note"]] for r in status_rows])

    lines.append("\n".join([
        "",
        "未达成：%s。注意「数据不足」不等于「数据不一致」：还原轴旁证只有 3 个 pair（门槛 18），"
        % "、".join(unmet),
        "是**不足**而非**不一致**；唯一给出 ordering_disagrees 的是氧化轴。",
        "",
        "## 4. anchor 条件一致性与 provenance 复核（一行未删）",
        "",
    ]))

    lines += _table(["anchor 文件", "相", "行数", "series", "同装置", "同判据",
                     "可用于排序层", "provenance"],
                    [[r["anchor_file"], r["phase"], r["n_rows"], r["series_ids"] or "(none)",
                      "是" if r["same_apparatus"] else "否",
                      "是" if r["same_criterion"] else "否",
                      "是" if r["admissible_for_ordering_tier"] else "否",
                      r["provenance_kinds"] or "(none)"] for r in inventory])

    lines.append("\n".join([
        "",
        "31 行绝对标定 anchor 逐行保留、逐行给出未升级原因（见 @@BT@@anchor_row_audit.csv@@BT@@）；",
        "**没有任何一行因为「不一致」被删掉**——它们本来就只是 estimates，不是条件匹配的测量。",
        "",
        "## 5. 排序一致性层：独立重算 vs 冻结值",
        "",
        "| 量 | 独立重算 | 冻结值 | 绝对差 |",
        "| --- | --- | --- | --- |",
        "| n_rows | %d | %d | %.3g |",
        "| n_pairs | %d | %d | %.3g |",
        "| concordant | %d | %d | %.3g |",
        "| discordant | %d | %d | %.3g |",
        "| tau_b | %.6f | %.6f | %.3g |",
    ]) % (recompute["recomputed"]["n_rows"], recompute["frozen"]["n_rows"],
          recompute["diffs"]["n_rows"],
          recompute["recomputed"]["n_pairs"], recompute["frozen"]["n_pairs"],
          recompute["diffs"]["n_pairs"],
          recompute["recomputed"]["concordant"], recompute["frozen"]["concordant"],
          recompute["diffs"]["concordant"],
          recompute["recomputed"]["discordant"], recompute["frozen"]["discordant"],
          recompute["diffs"]["discordant"],
          recompute["recomputed"]["tau_b"], recompute["frozen"]["tau_b"],
          recompute["diffs"]["tau_b"]))

    lines.append("\n".join([
        "",
        "重算只读 @@BT@@data/anchors/within_series_ordering.csv@@BT@@ 与",
        "@@BT@@outputs/week4/p1_core_set_derived.csv@@BT@@，口径与冻结阈值一致，逐位对账通过。",
        "因此「tau_b = %.4f」不是一次报告事故，而是可复现的判定。" % tau_b,
        "",
        "## 6. 结论-轨道映射（每个主结论都要贴标签）",
        "",
    ]))

    lines += _table(["ID", "主结论", "轨道", "判定"],
                    [[r["claim_id"], r["claim"], r["track"], r["verdict"]] for r in claims])

    lines.append("\n".join([
        "",
        "计数：Track A %d 条 / Track B %d 条 / 待验证推断 %d 条。"
        % (counts["n_claims_track_a"], counts["n_claims_track_b"], counts["n_claims_pending"]),
        "Track B 的两条（B1 绝对标定、B2 排序一致性）是**未建立**，不是「已否证」；",
        "待验证推断的两条（P1 / P2）只有在 Gate 1 CLOSED 之后才可检验。",
        "",
        "## 7. 措辞合规",
        "",
        "扫描 %d 个交付文件：禁用词出现 %d 次，全部是**规则文本本身**（禁用->允许 对照），",
        "违规 **%d** 处；允许措辞 @@BT@@designated computational target / designated reference "
        "model@@BT@@ 出现 %d 次。",
        "",
    ]) % (counts["n_files_scanned_for_naming"], n_forbidden,
          counts["n_naming_violations"], n_allowed))

    lines.append("\n".join([
        "",
        "## 8. 何时才值得新增电子结构计算",
        "",
    ]))

    lines += _table(["触发条件", "优先补充什么", "不建议做什么"],
                    [[r["trigger"], r["priority_action"], r["not_recommended"]] for r in triggers])

    lines.append("\n".join([
        "",
        "真正要扩大的首先应当是**信息覆盖度**，而不只是任务数量；并且**不允许**为关闭 Gate 1",
        "而调整阈值。",
        "",
        "## 9. 验收",
        "",
    ]))

    lines += _table(["问题", "结论", "支撑", "证据"],
                    [[r["question_id"] + ". " + r["question"], r["verdict"],
                      "%s/%s" % (r["n_supporting"], r["n_cells"]), r["evidence"]]
                     for r in acceptance])

    lines.append("\n".join([
        "",
        "## 10. 限制",
        "",
        "- 零新增计算；Gate 1 仍 NOT CLOSED / NOT CLOSABLE。本阶段不产生任何新的物理结论。",
        "- **NOT CLOSABLE != NO SUCH DATA EXIST ANYWHERE**：这是可被证伪的负结果，若日后出现满足",
        "  全部预注册条件（同装置 · 同判据 · 同态 · >=7 个核心集分子的同源序列）的数据，应被推翻。",
        "- within-series 表的 14 行 provenance 均为 @@BT@@transcription_only_not_reverified_"
        "against_primary@@BT@@：排序层的输入本身尚未回溯到一次可复现的原始测量。",
        "- 本阶段的 10 条主结论标签是**边界声明**，不是新的证据；下一阶段（Week 35 / Paper）",
        "  必须沿用这些标签。",
        "",
        "## 11. 复现命令",
        "",
        "@@BT@@@@BT@@@@BT@@powershell",
        "cd 电解液溶剂HB-Code",
        ".venv\\Scripts\\python.exe scripts\\build_week34_wp7_external_reference_boundary.py",
        ".venv\\Scripts\\python.exe scripts\\build_week34_wp7_external_reference_boundary.py --check",
        ".venv\\Scripts\\python.exe -m pytest tests/test_week34_wp7_external_reference_boundary.py -q",
        "@@BT@@@@BT@@@@BT@@",
        "",
    ]))

    return "\n".join(lines) + "\n"


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Week 34 / WP7: external reference & gate-1 conclusion boundary.")
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

    print("Week 34 / WP7 -- external reference & conclusion boundary")
    print("-" * 78)
    for table in TABLE_ORDER:
        info = payload["manifest"][table]
        print("  %-32s %4d rows  %s" % (table, info["n_rows"], info["sha256"][:16]))
    print("-" * 78)
    print("  rows total : %d" % payload["n_rows_total"])
    print("  checks     : %d passed / %d failed"
          % (sum(1 for c in payload["checks"] if c["ok"]),
             sum(1 for c in payload["checks"] if not c["ok"])))
    for check in payload["checks"]:
        print("    %-52s %s" % (check["id"], "PASS" if check["ok"] else "FAIL"))
    return 0 if all(c["ok"] for c in payload["checks"]) else 1


if __name__ == "__main__":
    sys.exit(main())
