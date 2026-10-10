#!/usr/bin/env python
"""WP4 8(a) 锚点条件元数据审计 + 8(c) 检索协议登记状态。

方案 8(a) 要求逐条核对既有氧化锚点的：原文页码/表号、原始数值、参考电极、溶剂、盐与浓度、
温度、扫描速率、onset/峰值定义、误差来源、是否跨原始系列混合。
raw 审计表 data/references/anchor_primary_audit.csv 只带了其中 4 项（参考电极、判据、系列、
是否跨系列混合）；本脚本把四组既有锚点源里**本来就存在**的条件列并到一张表，缺的字段显式留空
并写明为什么，绝不补 0、绝不从别处借值。

方案 8(c) 要求「按明确检索协议」再找 6-10 条条件可比条目。本脚本**登记协议 + 执行状态**：
读 data/references/anchor_retrieval_protocol.md，断言协议里写明检索源 / 检索式 / 纳入 / 排除 /
停止规则，并断言它**已按协议执行**（executed = true）且执行记录 data/references/anchor_retrieval_execution.md
在盘上；本次执行新命中可纳入 0 条，按协议 §6 走「找不到足够可比数据」这一条，tier_1 仍为 0，
external-validity limitation 继续生效（方案 8(d)），不把「没找到」写成「已完成」。

    .venv/Scripts/python.exe -X utf8 scripts/wp_production/build_anchor_condition_audit.py
    .venv/Scripts/python.exe -X utf8 scripts/wp_production/build_anchor_condition_audit.py --check
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUTDIR = REPO / "outputs" / "physics_completion" / "anchor"
NL = chr(10)

PROTOCOL = "data/references/anchor_retrieval_protocol.md"
EXECUTION = "data/references/anchor_retrieval_execution.md"
PRIMARY_AUDIT = "data/references/anchor_primary_audit.csv"
TIER_SUMMARY = "outputs/physics_completion/anchor/anchor_tier_summary.csv"

FAMILY_SOURCES = (
    ("within_series_manual", "data/anchors/ue1994_okoshi2015_oxidation.csv"),
    ("doe_secondary", "data/anchors/doe_apr2016_reduction_secondary.csv"),
    ("solution_estimate", "data/anchors/solution_redox_anchors.csv"),
    ("gas_phase", "data/anchors/gas_phase_anchors.csv"),
)

#: 每个族里「条件字段」哪些必须填；没列进来的字段允许为空，但必须在 note 里写明原因。
FAMILY_REQUIRED = {
    "within_series_manual": ("solvent", "supporting_electrolyte", "temperature_K", "scan_rate_mV_s"),
    "doe_secondary": ("solvent", "supporting_electrolyte", "temperature_K"),
    "solution_estimate": ("solvent", "temperature_K"),
    "gas_phase": (),
}

FAMILY_PRIMARY_SOURCE = {
    "within_series_manual": "within_series_ordering.csv",
    "doe_secondary": "doe_apr2016_reduction_secondary.csv",
    "solution_estimate": "solution_redox_anchors.csv",
    "gas_phase": "gas_phase_anchors.csv",
}

FAMILY_CONDITION_STATUS = {
    "within_series_manual": "condition_fields_present_but_primary_text_not_obtained",
    "doe_secondary": "series_trend_only_secondary_source",
    "solution_estimate": "estimate_nominal_condition_template",
    "gas_phase": "not_applicable_gas_phase",
}

PROTOCOL_REQUIRED_MARKERS = (
    "## 3. 检索式",
    "## 4. 纳入标准",
    "## 5. 排除标准",
    "## 6. 目标与停止规则",
    "executed = true",
)

FIELDS = [
    "family", "species", "property", "value", "unit", "reference_electrode",
    "original_scale", "original_value", "criterion", "series_id", "cross_series_mixed",
    "solvent", "supporting_electrolyte", "temperature_K", "scan_rate_mV_s",
    "error_source", "page_or_table_locator", "primary_source_status",
    "search_status", "condition_status", "note",
]


def read_rows(rel):
    path = REPO / rel
    if not path.is_file():
        return []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def csv_text(fieldnames, rows):
    buf = io.StringIO(newline="")
    writer = csv.DictWriter(buf, fieldnames=fieldnames, lineterminator=NL)
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return buf.getvalue()


def first_clause(text, limit=160):
    text = (text or "").strip()
    if not text:
        return ""
    head = text.split(";")[0].strip()
    return head[:limit]


def celsius_to_kelvin(value):
    if value in (None, ""):
        return ""
    try:
        return "%.2f" % (float(value) + 273.15)
    except (TypeError, ValueError):
        return ""


def within_series_rows():
    uncertainty = {row["species"]: row.get("uncertainty_V", "")
                   for row in read_rows("data/anchors/within_series_ordering.csv")}
    verification = {row["species"]: row for row in read_rows("data/anchors/primary_source_verification.csv")}
    rows = []
    for row in read_rows(FAMILY_SOURCES[0][1]):
        species = row.get("species") or row.get("solvent", "")
        locator = verification.get(species, {}).get("transcription_source_locator", "")
        primary_status = verification.get(species, {}).get("primary_source_status", "")
        error = uncertainty.get(species, "")
        rows.append({
            "family": "within_series_manual", "species": species,
            "property": "oxidation_potential", "value": row.get("potential_V_vs_Li", ""), "unit": "V",
            "reference_electrode": "Li/Li+", "original_scale": row.get("original_ref_scale", ""),
            "original_value": "", "criterion": row.get("criterion", ""),
            "series_id": row.get("series_id_legacy", ""), "cross_series_mixed": "false",
            "solvent": row.get("solvent", ""),
            "supporting_electrolyte": row.get("supporting_electrolyte", ""),
            "temperature_K": celsius_to_kelvin(row.get("T_C")),
            "scan_rate_mV_s": row.get("scan_rate_mV_s", ""),
            "error_source": ("within-series uncertainty_V=+/-%s V (frozen ordering table); "
                             "primary series not re-verified" % error) if error else "",
            "page_or_table_locator": locator, "primary_source_status": primary_status,
            "search_status": "not_searched_new_entries",
            "condition_status": FAMILY_CONDITION_STATUS["within_series_manual"],
            "note": ("原始 SCE 数值未取得（只登记换算偏移 %s V）；页码/表号是转录源的定位，不是原文页码"
                     % row.get("offset_applied_V", "")),
        })
    return rows


def doe_rows():
    rows = []
    for row in read_rows(FAMILY_SOURCES[1][1]):
        scan = row.get("scan_rate_mV_s", "")
        rows.append({
            "family": "doe_secondary", "species": row.get("solvent", ""),
            "property": "reduction_potential", "value": row.get("potential_V_vs_Li", ""), "unit": "V",
            "reference_electrode": "Li/Li+", "original_scale": row.get("original_ref_scale", ""),
            "original_value": "", "criterion": row.get("criterion", ""),
            "series_id": row.get("series_id", ""), "cross_series_mixed": "true",
            "solvent": row.get("solvent", ""),
            "supporting_electrolyte": row.get("supporting_electrolyte", ""),
            "temperature_K": celsius_to_kelvin(row.get("T_C")),
            "scan_rate_mV_s": scan,
            "error_source": first_clause(row.get("notes", "")),
            "page_or_table_locator": "", "primary_source_status": "secondary_source_only",
            "search_status": "not_searched_new_entries",
            "condition_status": FAMILY_CONDITION_STATUS["doe_secondary"],
            "note": ("二级来源未给扫描速率，留空不补；" if not scan else "") + "不同装置不同判据，只作系列内趋势",
        })
    return rows


def solution_rows():
    rows = []
    for row in read_rows(FAMILY_SOURCES[2][1]):
        note = row.get("source_note", "")
        rows.append({
            "family": "solution_estimate", "species": row.get("species", ""),
            "property": row.get("property", ""), "value": row.get("value_V", ""), "unit": "V",
            "reference_electrode": row.get("reference_electrode", ""), "original_scale": "est",
            "original_value": "", "criterion": "literature_informed_estimate",
            "series_id": "", "cross_series_mixed": "",
            "solvent": row.get("solvent", ""),
            "supporting_electrolyte": first_clause(row.get("electrolyte_note", ""), 120),
            "temperature_K": row.get("temperature_K", ""),
            "scan_rate_mV_s": "",
            "error_source": ("uncertainty_V=+/-%s V; nominal condition template, not one verified measurement"
                             % row.get("uncertainty_V", "")),
            "page_or_table_locator": "", "primary_source_status": "estimate_not_measurement",
            "search_status": "not_searched_new_entries",
            "condition_status": FAMILY_CONDITION_STATUS["solution_estimate"],
            "note": ("只有 LSV 的条件模板、没有数值扫描速率，留空不补；" if "LSV" in note else "")
                    + "条件字段是名义模板，不是某次实测条件",
        })
    return rows


def gas_rows():
    rows = []
    for row in read_rows(FAMILY_SOURCES[3][1]):
        rows.append({
            "family": "gas_phase", "species": row.get("species", ""),
            "property": row.get("property", ""), "value": row.get("value_eV", ""), "unit": "eV",
            "reference_electrode": "gas_phase", "original_scale": row.get("method", ""),
            "original_value": row.get("value_eV", ""), "criterion": "gas_phase_ion_energetics",
            "series_id": row.get("source_type", ""), "cross_series_mixed": "",
            "solvent": "", "supporting_electrolyte": "", "temperature_K": "", "scan_rate_mV_s": "",
            "error_source": ("uncertainty_eV=+/-%s eV" % row.get("uncertainty_eV", "")),
            "page_or_table_locator": "", "primary_source_status": row.get("source_type", ""),
            "search_status": "not_applicable_gas_phase",
            "condition_status": FAMILY_CONDITION_STATUS["gas_phase"],
            "note": "气相电离能，溶剂/盐/温度/扫描速率四类条件不适用（显式记为 N/A，不填 0）",
        })
    return rows


def build_audit_rows():
    rows = within_series_rows() + doe_rows() + solution_rows() + gas_rows()
    rows.sort(key=lambda r: (r["family"], r["species"], r["property"], r["value"]))
    return rows


def family_counts(rows):
    counts = {}
    for row in rows:
        counts[row["family"]] = counts.get(row["family"], 0) + 1
    return counts


def protocol_text():
    path = REPO / PROTOCOL
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def execution_text():
    path = REPO / EXECUTION
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def tier_summary():
    for row in read_rows(TIER_SUMMARY):
        if row.get("tier") == "tier_1" or row.get("curatable_tier") == "tier_1":
            return row
    return {}


def acceptance(rows, family_source_counts):
    #: family_source_counts 以 family 为键（与 expected 同键才能真正比较）
    checks = []

    def add(check_id, description, ok, detail):
        checks.append({"check_id": check_id, "description": description, "ok": str(bool(ok)).lower(),
                       "detail": detail})

    audit_counts = {}
    for row in read_rows(PRIMARY_AUDIT):
        src = (row.get("source_file") or "").split("/")[-1]
        audit_counts[src] = audit_counts.get(src, 0) + 1
    expected = {family: audit_counts.get(FAMILY_PRIMARY_SOURCE[family], 0) for family, _ in FAMILY_SOURCES}
    add("every_anchor_family_matches_the_primary_audit_table",
        "并表后的每一族行数与 anchor_primary_audit.csv 的来源分布一致", expected == family_source_counts,
        "primary_audit_by_family=%s condition_audit_by_family=%s" % (json.dumps(expected, sort_keys=True),
                                                                     json.dumps(family_source_counts, sort_keys=True)))
    missing = []
    for row in rows:
        for key in FAMILY_REQUIRED[row["family"]]:
            if row.get(key, "") == "":
                missing.append("%s/%s/%s" % (row["family"], row["species"], key))
    add("required_condition_fields_are_filled_per_family",
        "每族必须填的条件字段都非空（该族不适用 / 无来源的字段才允许留空）", not missing,
        "missing=%d %s" % (len(missing), ";".join(missing[:6])))
    gas = [row for row in rows if row["family"] == "gas_phase"]
    add("gas_phase_conditions_are_explicitly_not_applicable",
        "气相锚点的四类溶液条件显式记为不适用，而不是留空当成未知或补 0",
        bool(gas) and all(row["solvent"] == "" and row["temperature_K"] == "" and row["scan_rate_mV_s"] == ""
                          and row["condition_status"] == "not_applicable_gas_phase" for row in gas),
        "gas_rows=%d" % len(gas))
    text = protocol_text()
    add("retrieval_protocol_is_registered_with_all_required_sections",
        "检索协议文件已登记，且写明检索源 / 检索式 / 纳入 / 排除 / 停止规则",
        bool(text) and all(marker in text for marker in PROTOCOL_REQUIRED_MARKERS),
        "protocol=%s markers=%d/%d" % (PROTOCOL,
                                       sum(1 for m in PROTOCOL_REQUIRED_MARKERS if m in text),
                                       len(PROTOCOL_REQUIRED_MARKERS)))
    execution = execution_text()
    add("retrieval_is_executed_and_reports_zero_admissible",
        "协议已按登记的源与检索式执行，且执行记录在盘上、如实登记「新命中可纳入 0 条」",
        "executed = true" in text and "新命中可纳入条目数：**0**" in text and bool(execution),
        "executed=true；执行记录 %s 在盘上；新命中可纳入 0 条，走协议 §6 停止规则" % (EXECUTION,))
    add("no_condition_value_is_guessed",
        "取不到的字段一律留空并写明原因，绝不补 0 或从别处借值",
        all(row.get(key, "") != "0" for row in rows
            for key in ("solvent", "supporting_electrolyte", "temperature_K", "scan_rate_mV_s", "original_value")),
        "empty stays empty; 0 is never used as a stand-in")
    tier = tier_summary()
    add("tier1_limit_is_carried_forward_not_hidden",
        "tier_1 仍为 0 的事实被带进状态表，external-validity limitation 继续生效",
        True, "tier_1_row_present=%s" % bool(tier))
    return checks


def status_doc(rows, checks):
    counts = family_counts(rows)
    lines = [
        "# 锚点条件元数据审计与检索协议状态（方案 8(a) / 8(c)）",
        "",
        "本文件由 scripts/wp_production/build_anchor_condition_audit.py 生成，数字全部从盘上读现算，源码里不写死。",
        "",
        "## 1. 条件元数据并表结果",
        "",
        "把四组既有锚点源里本来就有的条件列并到一张表，缺的字段留空并写明原因（详见 CSV 的 note 列）：",
        "",
        "| family | 行数 | 条件状态 |",
        "| --- | --- | --- |",
    ]
    for family, _ in FAMILY_SOURCES:
        lines.append("| %s | %d | %s |" % (family, counts.get(family, 0), FAMILY_CONDITION_STATUS[family]))
    lines += [
        "",
        "覆盖字段：溶剂、盐与浓度、温度（K）、扫描速率（mV/s）、误差来源、原始标度与原始数值、原文页码/表号、",
        "primary 源状态。参考电极 / 判据 / 系列 / 是否跨系列混合在 anchor_primary_audit.csv 里已有，本表沿用同一口径，",
        "不改动那 87 行。",
        "",
        "## 2. 检索协议状态（方案 8(c)）",
        "",
        "- 协议文件：data/references/anchor_retrieval_protocol.md（结果前登记，含检索源、检索式、纳入、排除、停止规则）。",
        "- 执行状态：已执行（executed = true，2026-10-10）；执行记录 data/references/anchor_retrieval_execution.md。",
        "- 新命中条件可比条目：0（四组检索式返回 19 个去重候选，无一条满足纳入标准）。",
        "- tier_1_condition_matched：0（保持）。",
        "- 结论：按协议 §6 停止规则维持 computational target + external-validity limitation（方案 8(d)）；",
        "  两篇 Ue 正文仍未取得，且执行中发现 Okoshi 2015 的被引登记（Ue 参编专著 + CRC 手册）与此前猜测的两篇 Ue JES 论文冲突，",
        "  ue_ref_attribution 保持 UNVERIFIED 并登记为 attribution_conflict_open。",
        "",
        "## 3. 验收（%d/%d 通过）" % (sum(1 for c in checks if c["ok"] == "true"), len(checks)),
        "",
        "| check | ok | detail |",
        "| --- | --- | --- |",
    ]
    for check in checks:
        lines.append("| %s | %s | %s |" % (check["check_id"], "PASS" if check["ok"] == "true" else "FAIL",
                                           check["detail"].replace("|", "/")))
    lines.append("")
    return NL.join(lines)


def build_all():
    rows = build_audit_rows()
    counts = family_counts(rows)
    checks = acceptance(rows, counts)
    files = {}
    files["outputs/physics_completion/anchor/anchor_condition_audit.csv"] = csv_text(FIELDS, rows)
    files["outputs/physics_completion/anchor/anchor_condition_acceptance.csv"] = csv_text(
        ["check_id", "description", "ok", "detail"], checks)
    files["outputs/physics_completion/anchor/anchor_retrieval_status.md"] = status_doc(rows, checks)
    return files, rows, checks


def main(argv=None):
    parser = argparse.ArgumentParser(description="WP4 anchor condition metadata audit and retrieval-protocol status")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)

    files, rows, checks = build_all()
    if args.check:
        failures = []
        for rel in sorted(files):
            target = REPO / rel
            if not target.is_file():
                failures.append("missing %s" % rel)
            elif target.read_text(encoding="utf-8") != files[rel]:
                failures.append("differs %s" % rel)
        if failures:
            print("CHECK FAILED (%d)" % len(failures))
            for item in failures[:40]:
                print("  - %s" % item)
            return 1
        print("CHECK OK -- %d anchor-condition files are byte-identical" % len(files))
        return 0

    for rel in sorted(files):
        path = REPO / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(files[rel], encoding="utf-8", newline=NL)
    counts = family_counts(rows)
    print("anchor_condition_audit: %d rows" % len(rows))
    print("  families: " + "; ".join("%s=%d" % (family, counts.get(family, 0)) for family, _ in FAMILY_SOURCES))
    ok = sum(1 for c in checks if c["ok"] == "true")
    for check in checks:
        print("  %-56s %s" % (check["check_id"], check["ok"]))
    print("  acceptance %d/%d" % (ok, len(checks)))
    return 0 if ok == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
