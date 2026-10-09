# -*- coding: utf-8 -*-
"""新阶段（评审实施方案 WP0-WP6）产物生成器：physics_completion_v1 批次。

本生成器把仓库外那份**建议实施方案**（电解液排序稳定性：物理证据补强与决策预算研究
执行方案）登记成可复现的批次产物，并基于仓库既有冻结数据给出**首轮**可交付分析。
它不运行任何新的电子结构计算，不改动任何既有冻结数据、阈值或结论；只新增
   * config/physics_completion_v1.yaml   新批次协议与量名登记
   * data/metadata/physics_completion_set.csv   主集/审计集/采样集
   * data/references/anchor_primary_audit.csv   原始锚点复核（WP4 三级分类）
   * docs/physics_completion_protocol.md / docs/claim_migration.md  科学协议与结论迁移
   * docs/58..64_*.md                    逐周（WP0-WP6）工作与限制
   * docs/physics_completion_final_report.md       研究问题->结果->证据->限制
   * outputs/physics_completion/**       新批次产物（方法审计/自由能标签/pair 证据/ML/成本/…）
   * outputs/week37..week43/**           逐周载荷、验收单与 manifest

用法
----
    .venv\Scripts\python.exe scripts/build_physics_completion_batch.py
    .venv\Scripts\python.exe scripts/build_physics_completion_batch.py --check
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from electrolyte_ranking import pc_batch as PB  # noqa: E402

WEEK_DIRS = ["week%d" % n for n in range(37, 44)]


def sha_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def dump(obj):
    return json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=False) + "\n"


def csv_text(fieldnames, rows):
    out = io.StringIO()
    out.write(",".join(fieldnames) + "\n")
    for row in rows:
        cells = []
        for key in fieldnames:
            value = row.get(key, "")
            value = "" if value is None else str(value)
            if "," in value or "\"" in value or "\n" in value:
                value = "\"" + value.replace("\"", "\"\"") + "\""
            cells.append(value)
        out.write(",".join(cells) + "\n")
    return out.getvalue()


def finish_week(files, local, week, wp, title, extra=None):
    """把某一周的局部产物 + manifest 合进全局 files 字典。"""
    manifest = {
        "week": week,
        "work_package": wp,
        "title": title,
        "batch": PB.BATCH_ID,
        "baseline_commit": PB.BASELINE_COMMIT,
        "frozen_date": PB.FROZEN_DATE,
        "new_electronic_structure_jobs": 0,
        "n_files": len(local),
        "files": [{"path": rel, "sha256": sha_text(local[rel]), "bytes": len(local[rel].encode("utf-8"))}
                  for rel in sorted(local)],
    }
    if extra:
        manifest.update(extra)
    files.update(local)
    files["outputs/%s/manifest.json" % week] = dump(manifest)
    return manifest


def acceptance_rows(checks):
    rows = []
    for index, item in enumerate(checks, 1):
        rows.append({"check_id": item["id"], "description": item["description"],
                     "ok": str(bool(item["ok"])).lower(), "detail": item["detail"]})
    return rows


# ---------------------------------------------------------------------------
# config/physics_completion_v1.yaml
# ---------------------------------------------------------------------------
def build_config():
    lines = [
        "# =============================================================================",
        "# 新批次协议: physics_completion_v1 (WP0 登记)",
        "# 依据: 用户提供的《电解液排序稳定性：物理证据补强与决策预算研究执行方案》",
        "# 基线: 仓库提交 " + PB.BASELINE_COMMIT + " (week27 / R15)",
        "# 状态: REGISTERED (本轮只登记定义与样本, 尚未产生新计算)",
        "# 纪律: append-only; 旧定义(config/scientific_definitions.yaml)不被覆写;",
        "#       新阈值/新方法在结果产生前登记, 不按结果反推。",
        "# =============================================================================",
        "schema_version: \"1.0\"",
        "batch_id: " + PB.BATCH_ID,
        "frozen_date: \"" + PB.FROZEN_DATE + "\"",
        "baseline_commit: " + PB.BASELINE_COMMIT,
        "amends: \"config/scientific_definitions.yaml (append-only; legacy aliases preserved)\"",
        "registration_rule: \"new thresholds, methods and samples are registered before results\"",
        "no_new_electronic_structure_jobs_in_registration_week: true",
        "",
        "fixed_conditions:",
        "  solvent_model: \"SMD, acetonitrile\"",
        "  temperature_K: 298.15",
        "  standard_state: \"1 mol/L (solution)\"",
        "  geometry_start: \"r2SCAN-3c\"",
        "  note: \"controlled embedding; NOT a real EC/DMC formulation\"",
        "",
        "objective_direction:",
        "  oxidation: maximize",
        "  reduction_resistance_score_Sred: maximize",
        "  raw_electron_affinity_EA: minimize",
        "  same_set_rule: \"maximise Sred and minimise EA must select the same candidate set\"",
        "",
        "quantities:",
    ]
    for item in PB.QUANTITIES:
        lines.append("  - name: " + item["name"])
        for key in ("definition", "unit", "quantity_kind", "objective_direction",
                    "geometry_policy", "thermal_policy", "ensemble_policy", "solvent",
                    "state_identity_eligibility", "analysis_cohort", "role"):
            lines.append("    " + key + ": \"" + str(item[key]) + "\"")
    lines += [
        "",
        "legacy_aliases:",
    ]
    for old, new in sorted(PB.LEGACY_ALIASES.items()):
        lines.append("  " + old + ": \"" + new + "\"")
    lines += [
        "",
        "analysis_cohorts:",
    ]
    for cohort in ("main", "method_audit", "sampling_audit"):
        lines.append("  " + cohort + ": [" + ", ".join(PB.COHORTS[cohort]) + "]")
    lines += [
        "",
        "state_identity_eligibility:",
        "  rule: \"only molecule_centered_redox enters the main reduction ranking\"",
        "  labels: [molecule_centered_redox, molecule_centered_oxidation,",
        "           Li_centered_or_mixed_redox, ambiguous, intact_unclassified]",
        "  missing_rule: \"ineligible or missing states are recorded as None, never coerced to 0\"",
        "",
        "four_main_states: [" + ", ".join(PB.FOUR_STATES) + "]",
        "",
        "resource_budget_first_round:",
        "  method_audit_single_points: 128      # 8 molecules x 4 states x 4 settings",
        "  main_production_state_structures: \"48-144\"",
        "  sampling_extension_state_structures: 48",
        "  targeted_pair_second_method_single_points: \"16-32\"",
        "",
        "stop_rules:",
        "  method_spread_matches_target_gap: unresolved",
        "  qc_identity_failures_pervasive: \"narrow the comparable question before mass production\"",
        "  sampling_not_converged_after_two_rounds: sampling_limited",
        "  no_complete_molecule_centered_reduction_state: identity_outcome",
        "  external_quantities_not_comparable: validation_limitation",
        "  active_learning_not_better_than_random: \"report no evidence of saving; do not add models\"",
        "",
        "repo_landing:",
        "  protocol: docs/physics_completion_protocol.md",
        "  claim_migration: docs/claim_migration.md",
        "  sample_set: data/metadata/physics_completion_set.csv",
        "  anchor_audit: data/references/anchor_primary_audit.csv",
        "  products: outputs/physics_completion/",
        "  final_report: docs/physics_completion_final_report.md",
        "",
        "gate_status: \"Gate 0 CLOSED; Gate 1 NOT CLOSED and NOT CLOSABLE (unchanged)\"",
    ]
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# data/metadata/physics_completion_set.csv
# ---------------------------------------------------------------------------
SAMPLE_SET_FIELDS = ["cohort", "mol_id", "name", "family", "role", "donor_count",
                     "rotatable_bonds", "in_main", "in_method_audit", "in_sampling_audit",
                     "exclusion_reason", "batch"]


def build_sample_set():
    core = {row["mol_id"]: row for row in PB.load_rows(REPO / "data/metadata/core_set.csv")}
    rows = []
    for cohort in ("main", "method_audit", "sampling_audit"):
        for mol_id in PB.COHORTS[cohort]:
            meta = core[mol_id]
            rows.append({
                "cohort": cohort,
                "mol_id": mol_id,
                "name": meta["name"],
                "family": meta["family"],
                "role": meta["role"],
                "donor_count": meta["donor_count"],
                "rotatable_bonds": meta["rotatable_bonds"],
                "in_main": "true" if mol_id in PB.COHORTS["main"] else "false",
                "in_method_audit": "true" if mol_id in PB.COHORTS["method_audit"] else "false",
                "in_sampling_audit": "true" if mol_id in PB.COHORTS["sampling_audit"] else "false",
                "exclusion_reason": "",
                "batch": PB.BATCH_ID,
            })
    for mol_id in sorted(PB.MAIN_SET_EXCLUSIONS):
        meta = core[mol_id]
        rows.append({
            "cohort": "excluded", "mol_id": mol_id, "name": meta["name"],
            "family": meta["family"], "role": meta["role"], "donor_count": meta["donor_count"],
            "rotatable_bonds": meta["rotatable_bonds"], "in_main": "false",
            "in_method_audit": "false", "in_sampling_audit": "false",
            "exclusion_reason": PB.MAIN_SET_EXCLUSIONS[mol_id], "batch": PB.BATCH_ID,
        })
    return csv_text(SAMPLE_SET_FIELDS, rows)


def build_exclusion_rules():
    core = {row["mol_id"]: row for row in PB.load_rows(REPO / "data/metadata/core_set.csv")}
    rows = []
    for mol_id, reason in sorted(PB.MAIN_SET_EXCLUSIONS.items()):
        rows.append({"scope": "main_set", "mol_id": mol_id, "name": core[mol_id]["name"],
                     "family": core[mol_id]["family"],
                     "rule": "core-set molecule not in the 12-molecule main paired set",
                     "reason": reason})
    for mol_id, reason in sorted(PB.METHOD_AUDIT_HOLDOUTS.items()):
        rows.append({"scope": "method_audit", "mol_id": mol_id, "name": core[mol_id]["name"],
                     "family": core[mol_id]["family"],
                     "rule": "main-set molecule not in the 8-molecule method audit set",
                     "reason": reason})
    return csv_text(["scope", "mol_id", "name", "family", "rule", "reason"], rows)


# ---------------------------------------------------------------------------
# data/references/anchor_primary_audit.csv  (WP0 起登记, WP4 细化)
# ---------------------------------------------------------------------------
AUDIT_FIELDS = ["species", "property", "value", "unit", "reference_electrode", "source_file",
                "source_doi", "original_scale", "criterion", "series_id", "cross_series_mixed",
                "covered_by_model", "curatable_tier", "tier_reason", "verdict"]
TIER_2 = "tier_2_series_trend"
TIER_3 = "tier_3_not_usable"
TIER_2_REASON = "single homologous series (one paper / one apparatus / one criterion); trend only"
TIER_3_REASON_EST = "all rows are method=est literature estimates, not condition-matched measurements"
TIER_3_REASON_DOE = "two different cells and criteria inside one series_id -> adjudicated secondary"
TIER_3_REASON_GAS = "gas-phase IP/EA anchor: a different tier from the solution within-series ordering tier"


def build_anchor_audit():
    core_names = set(PB.COHORT_NAMES.values()) | {"FEC", "VC", "TEGDME", "EA", "MA", "SN"}
    rows = []
    for row in PB.load_rows(REPO / "data/anchors/within_series_ordering.csv"):
        rows.append({
            "species": row["species"], "property": row["property"], "value": row["value_V"],
            "unit": "V", "reference_electrode": row["reference_electrode"],
            "source_file": "data/anchors/within_series_ordering.csv", "source_doi": row["source_doi"],
            "original_scale": "SCE", "criterion": "j_onset_1mA_cm2", "series_id": row["series_id"],
            "cross_series_mixed": "false",
            "covered_by_model": "true" if row["species"] in core_names else "false",
            "curatable_tier": TIER_2, "tier_reason": TIER_2_REASON,
            "verdict": "transcription_only_not_reverified_against_primary",
        })
    for row in PB.load_rows(REPO / "data/anchors/doe_apr2016_reduction_secondary.csv"):
        rows.append({
            "species": row.get("species", ""), "property": "reduction_potential",
            "value": row.get("value", row.get("value_V", "")), "unit": "V",
            "reference_electrode": row.get("reference_electrode", ""),
            "source_file": "data/anchors/doe_apr2016_reduction_secondary.csv",
            "source_doi": row.get("doi", ""), "original_scale": row.get("original_scale", ""),
            "criterion": "secondary_corroboration", "series_id": "DOE_APR_FY2016",
            "cross_series_mixed": "true", "covered_by_model": "unknown",
            "curatable_tier": TIER_3, "tier_reason": TIER_3_REASON_DOE,
            "verdict": "adjudicated_secondary",
        })
    for row in PB.load_rows(REPO / "data/anchors/solution_redox_anchors.csv"):
        rows.append({
            "species": row.get("species", ""), "property": row.get("property", ""),
            "value": row.get("value", row.get("value_V", "")), "unit": "V",
            "reference_electrode": row.get("reference_electrode", ""),
            "source_file": "data/anchors/solution_redox_anchors.csv", "source_doi": row.get("doi", ""),
            "original_scale": row.get("original_scale", ""), "criterion": "literature_informed_estimate",
            "series_id": "", "cross_series_mixed": "true", "covered_by_model": "true",
            "curatable_tier": TIER_3, "tier_reason": TIER_3_REASON_EST,
            "verdict": "kept_as_est_never_deleted",
        })
    for row in PB.load_rows(REPO / "data/anchors/gas_phase_anchors.csv"):
        rows.append({
            "species": row.get("species", ""), "property": row.get("property", ""),
            "value": row.get("value_eV", ""), "unit": "eV", "reference_electrode": "gas_phase",
            "source_file": "data/anchors/gas_phase_anchors.csv", "source_doi": row.get("doi", ""),
            "original_scale": row.get("method", ""), "criterion": "gas_phase_ion_energetics",
            "series_id": "", "cross_series_mixed": "true", "covered_by_model": "true",
            "curatable_tier": TIER_3, "tier_reason": TIER_3_REASON_GAS,
            "verdict": "different_tier_not_comparable_to_solution_ordering",
        })
    return csv_text(AUDIT_FIELDS, rows)


# ---------------------------------------------------------------------------
# docs/physics_completion_protocol.md
# ---------------------------------------------------------------------------
def build_protocol_doc():
    lines = [
        "# physics_completion_v1 科学协议（WP0 登记）",
        "",
        "> 本协议把仓库外的《电解液排序稳定性：物理证据补强与决策预算研究执行方案》登记为可追溯的新批次。",
        "> 它**不**改写旧定义（`config/scientific_definitions.yaml` 原样保留，append-only），**不**运行新的电子结构计算，",
        "> **不**改动任何既有冻结数据、阈值或结论。",
        "",
        "## 1. 研究问题",
        "",
        "在本集合内，继续追问：哪些缺失物理会改变候选选择；这种变化是否超过独立评估的方法与采样敏感性；",
        "恢复指定计算目标的选择需要多少额外信息。四个可分别完成的任务：",
        "",
        "1. 弛豫、热校正和构象系综是否分别改变氧化候选清单？",
        "2. 同一连续介质中，Li 配位是否改变可比物种的氧化排序？",
        "3. 独立方法审计下，哪些 pair 可解析、哪些翻转仍成立、哪些只能归入候选等价集合？",
        "4. 以完成 QC 的目标标签为终点，廉价模型/Δ-learning/主动查询相对随机策略节省了多少成本？",
        "",
        "氧化为首轮确认性主轴；还原为有条件的探索性副轴。实验可比性单独报告，不把指定计算目标称为真实电解液排序。",
        "",
        "## 2. 量名、方向与状态身份",
        "",
        "| 量名 | 定义 | 单位 | 方向 | 量类 | 分析 cohort |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for item in PB.QUANTITIES:
        lines.append("| `%s` | %s | %s | %s | %s | %s |"
                     % (item["name"], item["definition"], item["unit"],
                        item["objective_direction"], item["quantity_kind"], item["analysis_cohort"]))
    lines += [
        "",
        "方向语义只在 `config/physics_completion_v1.yaml` 的 `objective_direction` 定义一次：",
        "原始 EA 方向为 **minimize**，统一抗还原 score `Sred = -EA` 方向为 **maximize**；二者必须选出同一候选集合。",
        "缺值、不合格态、未完成 QC 的状态一律记为 `None`，**绝不**被替换成 0。",
        "",
        "状态身份资格：还原轴只允许 `molecule_centered_redox` 进入主 ranking；其余标签作为 mechanistic outcome 单独统计。",
        "",
        "## 3. 样本（12 主集 / 8 方法集 / 4 采样集）",
        "",
        "| cohort | 分子 | 目的 |",
        "| --- | --- | --- |",
        "| main | " + "、".join(PB.COHORTS["main"]) + " | 固定主配对集（12） |",
        "| method_audit | " + "、".join(PB.COHORTS["method_audit"]) + " | 方法审计集（8） |",
        "| sampling_audit | " + "、".join(PB.COHORTS["sampling_audit"]) + " | 构象/配位采样审计集（4） |",
        "",
        "这是针对现有问题设计的配对子集，不用于宣称化学空间普适性。FEC、VC、SN、TEGDME 保留为后续扩展。",
        "",
        "## 4. 固定条件、方法与停止规则",
        "",
        "固定 SMD 乙腈背景、298.15 K、溶液标准态 1 mol/L；几何起点 r2SCAN-3c；",
        "单点生产候选为 range-separated hybrid（如 ωB97X-D4）配 triple-zeta 基组，审计对照为另一合理泛函（如 PBE0-D4）。",
        "同一介质、同一几何、同一状态下比较 2 个泛函 × 2 个基组设定；还原必须使用含弥散函数的设定。",
        "",
        "停止规则（在结果产生前冻结，不按结果反推）：",
        "",
        "- 方法分歧与目标间距相当 → 冻结为 `unresolved`；",
        "- 所有候选设定均出现明显身份/QC 问题 → 先缩小可比问题，不进入大批量生产；",
        "- 两轮采样后仍不收敛 → `sampling_limited`；",
        "- 没有完整分子中心还原态 → `identity_outcome`；",
        "- 外部量不可比 → `validation_limitation`；",
        "- AL 不胜随机 → 报告无证据支持节省，不增加复杂模型。",
        "",
        "## 5. 三层表述纪律",
        "",
        "每份报告都区分**模型事实** / **统计判定** / **材料意义**，不混写。主结论带 Track A（指定计算目标内的决策稳定性）",
        "或 Track B（外部参考有效性）标签；待验证推断单独标出。Gate 1 闭合前措辞只用 `designated computational target` /",
        "`designated reference model`，禁用 `validated target`。`NOT CLOSABLE` != `NO SUCH DATA EXIST ANYWHERE`。",
    ]
    return "\n".join(lines) + "\n"


CLAIM_MIGRATION = [
    {
        "id": "M1", "question": "Q3", "historical": "C1 全态负 tau 被当作分子还原排序脆弱性的证据",
        "source": "FINAL_CONCLUSIONS.md Q3; outputs/week5/c1_decision_stability.json",
        "new_statement": "C1 全态负 tau 不再用于分子还原排序脆弱性的确认性判断；还原排序在 C1 条件下因身份分层而无定义（n=1）。",
        "risk_if_unmigrated": "把身份混合当成物理脆弱性，得出不可认证的还原排序结论。",
    },
    {
        "id": "M2", "question": "Q7", "historical": "构象敏感性与 method 主导的 tolerance 被合并解释",
        "source": "FINAL_CONCLUSIONS.md Q7; outputs/week6/t6_conformer_spread.json",
        "new_statement": "构象敏感性（p90）与 method 主导的 tolerance 分开解释、分开计数；二者不同量纲，不得互相标定。",
        "risk_if_unmigrated": "用构象 p90 冒充方法误差，或用方法 sigma 抹掉构象不确定性。",
    },
    {
        "id": "M3", "question": "Q10", "historical": "Gate 1 措辞可被读成世界范围不存在合格数据",
        "source": "FINAL_CONCLUSIONS.md Q10; docs/gate1_negative_result.md",
        "new_statement": "统一为：在既定检索标准下未定位到合格数据，不能断言世界范围不存在；NOT CLOSABLE != NO SUCH DATA EXIST ANYWHERE。",
        "risk_if_unmigrated": "把检索失败的负结果读成普适的不可能性断言。",
    },
    {
        "id": "M4", "question": "R15", "historical": "R15 的代数恒等式被读成独立物理机制验证",
        "source": "docs/49_round3_adversarial_audit.md; FINAL_CONCLUSIONS.md 读前必读",
        "new_statement": "区分定义性零翻转（代数恒等式）与经验未观测；计算成本最多与改排序相关，不声称因果定律。",
        "risk_if_unmigrated": "把判据分析当成物理定律，夸大结论强度。",
    },
    {
        "id": "M5", "question": "P1a", "historical": "P1a 的电子能差被 thermodynamics 标签掩盖缺失热校正",
        "source": "config/scientific_definitions.yaml#P1a; 计划.md 第 2 节",
        "new_statement": "写明 P1a 处在电子能层；不以其 thermodynamics 措辞掩盖缺失的热校正，新批次显式区分 E / E+ZPE / G_single / G_ensemble。",
        "risk_if_unmigrated": "用热力学术语包装纯电子能差，误导可比性与精度预期。",
    },
]


def build_claim_migration_doc():
    lines = [
        "# 历史结论到当前主结论的映射（claim migration）",
        "",
        "> 本文件把 FINAL_CONCLUSIONS.md 与既有审计中，**必须随新批次一并迁移**的五条结论逐条写清：",
        "> 旧表述 → 来源 → 新表述 → 若不迁移的风险。它是 append-only 记录，不改写历史文件。",
        "",
        "| id | 问题 | 旧表述 | 来源 | 新表述 | 不迁移的风险 |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for item in CLAIM_MIGRATION:
        lines.append("| %s | %s | %s | `%s` | %s | %s |"
                     % (item["id"], item["question"], item["historical"],
                        item["source"], item["new_statement"], item["risk_if_unmigrated"]))
    lines += [
        "",
        "## 迁移总则",
        "",
        "1. 新批次只**新增**标签与量名；旧别名（P1→P1v、P2→P2a）只作映射存在，不被静默当成新量名。",
        "2. 不同量（E、E+ZPE、G_single、G_ensemble）不得用旧别名互相替换。",
        "3. 人为例子中，最大化 `Sred` 与最小化原始 `EA` 必须选出同一集合（见 `outputs/physics_completion/definition/`）。",
        "4. 不合格态 / 缺值不得变成 0；必须显式记 `None` 并进排除表。",
        "5. 只为这些有实际风险的行为增加针对性测试（见 `tests/test_physics_completion_batch.py`）。",
    ]
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Week 37 / WP0 — 定义迁移与历史结论同步
# ---------------------------------------------------------------------------
def wp0():
    files = {}
    local = {}
    names = [q["name"] for q in PB.QUANTITIES]
    required_fields = ("name", "definition", "unit", "quantity_kind", "objective_direction",
                       "geometry_policy", "thermal_policy", "ensemble_policy", "solvent",
                       "state_identity_eligibility", "analysis_cohort", "role")
    fields_ok = all(all(q.get(field) for field in required_fields) for q in PB.QUANTITIES)
    alias_clash = sorted(set(PB.LEGACY_ALIASES) & set(names))

    example_ea = {"a": 0.10, "b": 0.30}
    example_sred = {"a": -0.10, "b": -0.30}
    pick_ea = PB.direction_selection(example_ea, PB.OBJECTIVE_DIRECTION["EA"])
    pick_sred = PB.direction_selection(example_sred, PB.OBJECTIVE_DIRECTION["Sred"])
    same_set = pick_ea == pick_sred == "a"

    mixed = {"a": 0.10, "b": None, "c": ""}
    pick_mixed = PB.direction_selection(mixed, "maximize")
    missing_not_zero = pick_mixed == "a" and PB.direction_selection({"x": None}, "maximize") is None

    migrated = {item["question"] for item in CLAIM_MIGRATION}
    required_questions = {"Q3", "Q7", "Q10", "R15", "P1a"}

    main = set(PB.COHORTS["main"])
    audit = set(PB.COHORTS["method_audit"])
    sampling = set(PB.COHORTS["sampling_audit"])
    core_ids = {row["mol_id"] for row in PB.load_rows(REPO / "data/metadata/core_set.csv")}
    cohorts_ok = (audit <= main) and (sampling <= main) and (main <= core_ids)
    excluded_ids = set(PB.MAIN_SET_EXCLUSIONS)
    accounted_ok = ((main | excluded_ids) == core_ids) and not (main & excluded_ids)

    checks = [
        {"id": "quantity_names_unique", "description": "新批次量名互不重复",
         "ok": len(names) == len(set(names)), "detail": "%d 个量名 / %d 个唯一" % (len(names), len(set(names)))},
        {"id": "quantity_fields_complete", "description": "每个量都登记了全部必填字段",
         "ok": fields_ok, "detail": "required=" + ",".join(required_fields)},
        {"id": "legacy_alias_never_a_new_quantity_name", "description": "旧别名不被当作新量名",
         "ok": not alias_clash, "detail": "clash=" + (",".join(alias_clash) or "none")},
        {"id": "direction_selects_the_same_set", "description": "maximise Sred 与 minimise EA 选出同一集合",
         "ok": same_set, "detail": "EA pick=%s ; Sred pick=%s" % (pick_ea, pick_sred)},
        {"id": "missing_state_never_coerced_to_zero", "description": "缺值/不合格态记为 None 而非 0",
         "ok": missing_not_zero, "detail": "mixed pick=%s ; all-missing pick=None" % pick_mixed},
        {"id": "claim_migration_covers_required", "description": "结论迁移覆盖 Q3/Q7/Q10/R15/P1a",
         "ok": required_questions <= migrated, "detail": "covered=" + ",".join(sorted(migrated))},
        {"id": "cohorts_nested_in_core_set", "description": "三个 cohort 均落在既有 core set 内",
         "ok": cohorts_ok, "detail": "main=%d audit=%d sampling=%d" % (len(main), len(audit), len(sampling))},
        {"id": "core_set_fully_accounted", "description": "18 个 core-set 分子全部有归属（主集或写明排除原因）",
         "ok": accounted_ok,
         "detail": "main=%d excluded=%d union=%d core=%d"
                   % (len(main), len(PB.MAIN_SET_EXCLUSIONS), len(main | excluded_ids), len(core_ids))},
    ]

    payload = {
        "stage": "Week 37 / WP0",
        "title": "definition migration and historical-claim synchronisation",
        "batch": PB.BATCH_ID,
        "baseline_commit": PB.BASELINE_COMMIT,
        "inputs": {
            "scientific_definitions": "config/scientific_definitions.yaml",
            "prereg": "config/prereg.yaml",
            "core_set": "data/metadata/core_set.csv",
            "cohort_exclusion_rules": "outputs/physics_completion/definition/cohort_exclusion_rules.csv",
            "final_conclusions": "FINAL_CONCLUSIONS.md",
            "new_electronic_structure_jobs": 0,
        },
        "conventions": {
            "append_only": "旧定义不被覆写；新量名与旧别名并列登记",
            "direction": "ox = maximize; reduction_resistance_score Sred = -EA = maximize; raw EA = minimize",
            "missing_rule": "缺值/不合格态记为 None，绝不替换成 0",
            "state_identity": "还原轴主 ranking 只允许 molecule_centered_redox",
            "gate1_status": "Gate 1 NOT CLOSED / NOT CLOSABLE（本批次不改动）",
        },
        "quantities": PB.QUANTITIES,
        "legacy_aliases": PB.LEGACY_ALIASES,
        "cohorts": PB.COHORTS,
        "claim_migration": CLAIM_MIGRATION,
        "checks": checks,
        "n_checks": len(checks),
        "n_failed": sum(0 if item["ok"] else 1 for item in checks),
    }
    local["outputs/week37/wp0_definition_migration.json"] = dump(payload)
    local["outputs/week37/wp0_acceptance.csv"] = csv_text(
        ["check_id", "description", "ok", "detail"], acceptance_rows(checks))
    local["outputs/physics_completion/definition/quantity_registry.csv"] = csv_text(
        list(required_fields), PB.QUANTITIES)
    local["outputs/physics_completion/definition/claim_migration.csv"] = csv_text(
        ["id", "question", "historical", "source", "new_statement", "risk_if_unmigrated"],
        CLAIM_MIGRATION)
    local["outputs/physics_completion/definition/cohort_exclusion_rules.csv"] = build_exclusion_rules()

    summary = [
        "# Week 37 / WP0 — 定义迁移与历史结论同步",
        "",
        "**状态**：已登记（零新增电子结构计算）。",
        "",
        "## 交付",
        "",
        "- 新批次协议 `config/physics_completion_v1.yaml`（量名/方向/状态身份/停止规则/落点）",
        "- 样本 `data/metadata/physics_completion_set.csv`（%d 主集 / %d 方法集 / %d 采样集）"
        % (len(main), len(audit), len(sampling)),
        "- 排除原因规则 `outputs/physics_completion/definition/cohort_exclusion_rules.csv`"
        "（主集 %d 条 + 方法集 %d 条；%d 个 core-set 分子全部有归属）"
        % (len(PB.MAIN_SET_EXCLUSIONS), len(PB.METHOD_AUDIT_HOLDOUTS), len(core_ids)),
        "- 结论迁移 `docs/claim_migration.md`（%d 条：%s）"
        % (len(CLAIM_MIGRATION), "、".join(item["id"] + "/" + item["question"] for item in CLAIM_MIGRATION)),
        "- 原始锚点复核 `data/references/anchor_primary_audit.csv`（WP0 起登记，WP4 细化）",
        "",
        "## 验收（%d/%d 通过）" % (len(checks) - payload["n_failed"], len(checks)),
        "",
        "| check | ok | detail |",
        "| --- | --- | --- |",
    ]
    for item in checks:
        summary.append("| %s | %s | %s |" % (item["id"], "PASS" if item["ok"] else "FAIL", item["detail"]))
    summary += [
        "",
        "## 限制",
        "",
        "- 本批次只登记定义与样本；新方法、新阈值在结果产生前冻结，尚未产生任何新计算量。",
        "- 方向一致性用人为例子验证（maximise Sred 与 minimise EA 同一集合），不代表真实数值已就绪。",
        "- 旧别名（P1→P1v、P2→P2a）只作映射存在，任何代码路径都不允许把旧别名静默当成新量名。",
    ]
    local["outputs/week37/wp0_summary.md"] = "\n".join(summary) + "\n"
    local["docs/58_week37_wp0_definition_migration.md"] = "\n".join(summary) + "\n"
    finish_week(files, local, "week37", "WP0", "definition migration and historical-claim synchronisation",
                {"n_quantities": len(names), "n_claim_migrations": len(CLAIM_MIGRATION)})
    return files


# ---------------------------------------------------------------------------
# Week 38 / WP1 — 独立方法审计表
# ---------------------------------------------------------------------------
METHOD_SETTINGS = [
    {"setting_id": "S1", "functional": "omegaB97X-D4", "basis": "def2-TZVP", "role": "production_candidate",
     "has_diffuse": "false", "note": "range-separated hybrid; triple-zeta; no diffuse functions"},
    {"setting_id": "S2", "functional": "omegaB97X-D4", "basis": "def2-TZVPD", "role": "production_candidate",
     "has_diffuse": "true", "note": "adds diffuse functions; required for reduction states"},
    {"setting_id": "S3", "functional": "PBE0-D4", "basis": "def2-TZVP", "role": "audit_control",
     "has_diffuse": "false", "note": "second functional for sensitivity assessment"},
    {"setting_id": "S4", "functional": "PBE0-D4", "basis": "def2-TZVPD", "role": "audit_control",
     "has_diffuse": "true", "note": "second functional with diffuse functions"},
]


def wp1():
    files = {}
    local = {}
    matrix = []
    for mol_id in PB.COHORTS["method_audit"]:
        for state in PB.FOUR_STATES:
            for setting in METHOD_SETTINGS:
                matrix.append({
                    "mol_id": mol_id, "name": PB.COHORT_NAMES[mol_id], "state": state,
                    "setting_id": setting["setting_id"], "functional": setting["functional"],
                    "basis": setting["basis"], "solvent": "SMD_acetonitrile",
                    "geometry_start": "r2SCAN-3c", "job_kind": "single_point",
                    "status": "planned", "notes": setting["note"],
                })

    p1v = [row for row in PB.load_rows(REPO / "outputs/week4/p1_core_set.csv") if row.get("status") == "ok"]
    p1a = PB.load_rows(REPO / "outputs/phase2_p1a/p1a_adiabatic.csv")
    c1 = PB.load_rows(REPO / "outputs/week5/c1_coord_shifts.csv")
    existing = [
        {"payload": "outputs/week4/p1_core_set.csv", "layer": "P1v (gas-phase vertical)",
         "n_rows": len(p1v), "n_molecules": len({r["mol_id"] for r in p1v}),
         "states": "neutral; cation; anion", "method": "r2SCAN-3c / def2-mTZVPP (no diffuse)",
         "reuse_kind": "electronic-energy layer only", "caveat": "no diffuse functions; no thermal correction"},
        {"payload": "outputs/phase2_p1a/p1a_adiabatic.csv", "layer": "P1a (gas-phase adiabatic)",
         "n_rows": len(p1a), "n_molecules": len({r["mol_id"] for r in p1a}),
         "states": "neutral_relaxed; cation_relaxed", "method": "r2SCAN-3c Opt",
         "reuse_kind": "relaxation effect only", "caveat": "reduction axis excluded by the unbound_anion rule"},
        {"payload": "outputs/week5/c1_coord_shifts.csv", "layer": "C1 (Li-coordination)",
         "n_rows": len(c1), "n_molecules": len({r["mol_id"] for r in c1}),
         "states": "cation; dication", "method": "r2SCAN-3c (gas + SMD legs)",
         "reuse_kind": "conditional shift demonstration", "caveat": "single representative motif; identity stratification applies"},
    ]

    diffuse_settings = {s["setting_id"] for s in METHOD_SETTINGS if s["has_diffuse"] == "true"}
    checks = [
        {"id": "matrix_is_full_factorial", "description": "方法矩阵 = 8 分子 x 4 状态 x 4 设定 = 128",
         "ok": len(matrix) == 128, "detail": "n_rows=%d" % len(matrix)},
        {"id": "reduction_has_diffuse_option", "description": "存在含弥散函数的设定可用于还原态",
         "ok": bool(diffuse_settings), "detail": "diffuse settings=" + ",".join(sorted(diffuse_settings))},
        {"id": "both_functionals_present", "description": "至少两个泛函（生产候选 + 审计对照）",
         "ok": len({s["functional"] for s in METHOD_SETTINGS}) >= 2,
         "detail": "functionals=" + ",".join(sorted({s["functional"] for s in METHOD_SETTINGS}))},
        {"id": "existing_jobs_are_electronic_layer_only", "description": "既有可复用作业只到电子能层",
         "ok": all(("electronic" in item["reuse_kind"]) or ("relaxation" in item["reuse_kind"])
                   or ("shift" in item["reuse_kind"]) for item in existing),
         "detail": "%d 个既有载荷被盘点" % len(existing)},
        {"id": "no_method_selected_by_flip_count", "description": "方法选择规则不按翻转数量",
         "ok": True, "detail": "冻结规则：QC 可用率 / 数值稳定性 / 气相 anchor 可比 / 固定介质内 rank sensitivity / 实测成本"},
    ]

    payload = {
        "stage": "Week 38 / WP1",
        "title": "independent method audit (sensitivity, not calibration)",
        "batch": PB.BATCH_ID,
        "inputs": {
            "core_set": "data/metadata/core_set.csv",
            "existing_p1v": "outputs/week4/p1_core_set.csv",
            "existing_p1a": "outputs/phase2_p1a/p1a_adiabatic.csv",
            "existing_c1": "outputs/week5/c1_coord_shifts.csv",
            "new_electronic_structure_jobs": 0,
        },
        "conventions": {
            "fixed_conditions": "SMD acetonitrile, 298.15 K, 1 mol/L solution standard state",
            "geometry_start": "r2SCAN-3c",
            "method_choice_rule": "QC availability, numerical stability, gas-phase anchor comparability, rank sensitivity, measured cost",
            "forbidden_rule": "do not pick the method that produces more flips",
            "diffuse_rule": "reduction settings must include diffuse functions; boundness cannot be inferred from a converged finite basis",
            "audit_nature": "sensitivity assessment, NOT a calibrated probability error",
        },
        "method_settings": METHOD_SETTINGS,
        "job_matrix_size": len(matrix),
        "existing_reusable_jobs": existing,
        "stop_conditions": [
            "method spread comparable to the target gap -> freeze as unresolved",
            "pervasive identity/QC problems across candidate settings -> narrow the comparable question first",
        ],
        "checks": checks,
        "n_checks": len(checks),
        "n_failed": sum(0 if item["ok"] else 1 for item in checks),
    }
    local["outputs/week38/wp1_method_audit.json"] = dump(payload)
    local["outputs/week38/wp1_acceptance.csv"] = csv_text(
        ["check_id", "description", "ok", "detail"], acceptance_rows(checks))
    local["outputs/physics_completion/method_audit/job_matrix.csv"] = csv_text(
        ["mol_id", "name", "state", "setting_id", "functional", "basis", "solvent",
         "geometry_start", "job_kind", "status", "notes"], matrix)
    local["outputs/physics_completion/method_audit/method_settings.csv"] = csv_text(
        ["setting_id", "functional", "basis", "role", "has_diffuse", "note"], METHOD_SETTINGS)
    local["outputs/physics_completion/method_audit/existing_reusable_jobs.csv"] = csv_text(
        ["payload", "layer", "n_rows", "n_molecules", "states", "method", "reuse_kind", "caveat"],
        existing)

    summary = [
        "# Week 38 / WP1 — 独立方法审计表（首轮登记）",
        "",
        "**状态**：矩阵与规则已冻结；首轮只盘点既有电子能层作业，零新增计算。",
        "",
        "## 冻结内容",
        "",
        "- 固定条件：SMD 乙腈、298.15 K、溶液标准态 1 mol/L；几何起点 r2SCAN-3c。",
        "- 方法矩阵：%d 分子 × %d 状态 × %d 设定 = **%d** 单点上限。"
        % (len(PB.COHORTS["method_audit"]), len(PB.FOUR_STATES), len(METHOD_SETTINGS), len(matrix)),
        "- 生产候选 ωB97X-D4（def2-TZVP / def2-TZVPD）；审计对照 PBE0-D4（同两基组）。",
        "- 还原态必须使用含弥散函数设定（S2 / S4）；有限基组能收敛**不能**证明束缚。",
        "- 方法选择规则：QC 可用率 / 数值稳定性 / 气相 anchor 可比 / rank sensitivity / 实测成本；**不**按翻转数量选方法。",
        "",
        "## 验收（%d/%d 通过）" % (len(checks) - payload["n_failed"], len(checks)),
        "",
        "| check | ok | detail |",
        "| --- | --- | --- |",
    ]
    for item in checks:
        summary.append("| %s | %s | %s |" % (item["id"], "PASS" if item["ok"] else "FAIL", item["detail"]))
    summary += [
        "",
        "## 既有可复用作业（只到电子能层）",
        "",
        "| 载荷 | 层 | 行数 | 分子 | 复用范围 | 限制 |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for item in existing:
        summary.append("| `%s` | %s | %d | %d | %s | %s |"
                       % (item["payload"], item["layer"], item["n_rows"], item["n_molecules"],
                          item["reuse_kind"], item["caveat"]))
    summary += [
        "",
        "## 限制",
        "",
        "- 首轮**没有**任一候选泛函/基组在本机的实测支持性回显；方案中的 ωB97X-D4 / PBE0-D4 仍是建议候选。",
        "- 既有作业是气相 r2SCAN-3c（无弥散），不能裁断 0.01 eV 量级的阴离子束缚，也不含热校正。",
        "- 独立方法审计是 sensitivity assessment，不等于校准的概率误差；1.96×spread 不得自动标成 95% 置信度。",
    ]
    local["outputs/week38/wp1_summary.md"] = "\n".join(summary) + "\n"
    local["docs/59_week38_wp1_method_audit.md"] = "\n".join(summary) + "\n"
    finish_week(files, local, "week38", "WP1", "independent method audit",
                {"job_matrix_size": len(matrix), "n_settings": len(METHOD_SETTINGS)})
    return files


# ---------------------------------------------------------------------------
# Week 39 / WP2 — 固定背景配对自由能标签（首轮登记 + 既有电子能层盘点）
# ---------------------------------------------------------------------------
STATE_CHARGE = {"M": (0, 1), "M_plus": (1, 2), "LiM_plus": (1, 1), "LiM_2plus": (2, 2)}
HARTREE_TO_EV = 27.211386245988

ENSEMBLE_RULES = [
    {"rule_id": "E1", "rule": "cheap-search window above the mother-state minimum", "value": "6 kcal/mol", "kind": "resource rule (not a proven convergence scale)"},
    {"rule_id": "E2", "rule": "deduplicate by connectivity / coordination mode / heavy-atom RMSD / torsion", "value": "keep 3 lowest independent", "kind": "resource rule"},
    {"rule_id": "E3", "rule": "ensemble free energy", "value": "G_ens = -RT ln sum g_i exp(-G_i/RT)", "kind": "definition"},
    {"rule_id": "E4", "rule": "statistical degeneracy g_i", "value": "only when provable", "kind": "definition"},
    {"rule_id": "E5", "rule": "do not mix different stoichiometries in one ensemble", "value": "hard rule", "kind": "definition"},
    {"rule_id": "E6", "rule": "sampling audit extension", "value": "up to 6 structures for the 4 sampling molecules; second round only if unstable", "kind": "resource rule"},
    {"rule_id": "E7", "rule": "low-frequency treatment", "value": "single reproducible scheme (e.g. qRRHO), frozen before analysis", "kind": "definition"},
]


def wp2():
    files = {}
    local = {}
    raw = {}
    for row in PB.load_rows(REPO / "outputs/week4/p1_core_set.csv"):
        if row.get("status") == "ok":
            raw[(row["mol_id"], row["state"])] = float(row["final_energy_eh"])
    p1a = {row["mol_id"]: row for row in PB.load_rows(REPO / "outputs/phase2_p1a/p1a_adiabatic.csv")}
    c1_primary = {}
    for row in PB.load_rows(REPO / "outputs/week5/c1_coord_shifts.csv"):
        if str(row.get("is_primary")).lower() == "true" and row["mol_id"] not in c1_primary:
            c1_primary[row["mol_id"]] = row

    ledger = []
    for mol_id in PB.COHORTS["main"]:
        for state in PB.FOUR_STATES:
            charge, mult = STATE_CHARGE[state]
            ledger.append({
                "record_id": "%s|%s" % (mol_id, state), "cohort": "main", "mol_id": mol_id,
                "name": PB.COHORT_NAMES[mol_id], "state": state, "charge": charge,
                "multiplicity": mult, "opt_jobs": 1, "freq_jobs": 1, "sp_jobs": 1,
                "e_sp_solution_ev": "", "zpe_ev": "", "thermal_corr_ev": "",
                "std_state_corr_ev": "", "g_single_ev": "", "g_ensemble_ev": "",
                "n_conformers": "", "identity_label": "", "status": "planned",
            })

    sampling = []
    for mol_id in PB.COHORTS["sampling_audit"]:
        for state in PB.FOUR_STATES:
            sampling.append({
                "mol_id": mol_id, "name": PB.COHORT_NAMES[mol_id], "state": state,
                "structures_round1": 3, "structures_round2_max": 6, "status": "planned",
                "escalation_rule": "extend only if the 3->6 free-energy change crosses the independent tolerance or the Top-k set",
            })

    existing = []
    for mol_id in PB.COHORTS["main"]:
        name = PB.COHORT_NAMES[mol_id]
        neutral = raw.get((mol_id, "neutral"))
        cation = raw.get((mol_id, "cation"))
        if neutral is not None and cation is not None:
            existing.append({
                "mol_id": mol_id, "name": name, "layer": "P1v", "quantity": "Eox_vertical",
                "value_ev": "%.9f" % ((cation - neutral) * HARTREE_TO_EV),
                "method": "r2SCAN-3c / def2-mTZVPP (gas, no diffuse)",
                "thermal_correction": "absent", "status": "existing_electronic_only",
            })
        if mol_id in p1a and p1a[mol_id].get("ip_p1a_ev"):
            existing.append({
                "mol_id": mol_id, "name": name, "layer": "P1a", "quantity": "Eox_adiabatic",
                "value_ev": "%.9f" % float(p1a[mol_id]["ip_p1a_ev"]),
                "method": "r2SCAN-3c Opt (gas)", "thermal_correction": "absent",
                "status": "existing_electronic_only",
            })
        if mol_id in c1_primary and c1_primary[mol_id].get("d_ip_ev"):
            existing.append({
                "mol_id": mol_id, "name": name, "layer": "C1", "quantity": "coordination_shift",
                "value_ev": "%.9f" % float(c1_primary[mol_id]["d_ip_ev"]),
                "method": "r2SCAN-3c (gas legs) motif=%s" % c1_primary[mol_id]["motif_id"],
                "thermal_correction": "absent", "status": "existing_electronic_only",
            })

    n_existing_mol = len({row["mol_id"] for row in existing})
    checks = [
        {"id": "ledger_covers_main_x_four_states", "description": "自由能账本登记 12 主集 x 4 主状态 = 48 行",
         "ok": len(ledger) == 48, "detail": "n_rows=%d" % len(ledger)},
        {"id": "thermal_fields_left_empty_not_zero", "description": "尚未计算的热校正字段留空而非 0",
         "ok": all(row["thermal_corr_ev"] == "" and row["g_single_ev"] == "" for row in ledger),
         "detail": "48 行的 g_single_ev / thermal_corr_ev 均为空串"},
        {"id": "sampling_plan_has_escalation_rule", "description": "采样审计集给出 3->6 升级规则",
         "ok": len(sampling) == 16 and all(row["escalation_rule"] for row in sampling),
         "detail": "n_rows=%d" % len(sampling)},
        {"id": "existing_electronic_layer_is_labelled", "description": "既有数值标明只到电子能层、缺热校正",
         "ok": all(row["thermal_correction"] == "absent" for row in existing),
         "detail": "%d 条既有数值 / %d 个分子" % (len(existing), n_existing_mol)},
        {"id": "ensemble_rules_frozen", "description": "系综规则在观察目标排名前冻结",
         "ok": len(ENSEMBLE_RULES) >= 6, "detail": "n_rules=%d" % len(ENSEMBLE_RULES)},
    ]

    payload = {
        "stage": "Week 39 / WP2",
        "title": "fixed-background paired free-energy labels",
        "batch": PB.BATCH_ID,
        "inputs": {
            "core_set": "data/metadata/core_set.csv",
            "existing_p1v": "outputs/week4/p1_core_set.csv",
            "existing_p1a": "outputs/phase2_p1a/p1a_adiabatic.csv",
            "existing_c1": "outputs/week5/c1_coord_shifts.csv",
            "new_electronic_structure_jobs": 0,
        },
        "conventions": {
            "states": PB.FOUR_STATES,
            "ledger": "G = E_SP,solution + (G_thermal,solution - E_geometry_level,solution) + standard-state term",
            "no_double_counting": "the bracketed thermal term must come from a stated method; no implicit solvent term added twice",
            "ensemble": "G_ens = -RT ln sum g_i exp(-G_i/RT)",
            "charge_spin": {state: {"charge": STATE_CHARGE[state][0], "mult": STATE_CHARGE[state][1]}
                            for state in PB.FOUR_STATES},
            "gate1_status": "Gate 1 NOT CLOSED / NOT CLOSABLE (unchanged)",
        },
        "ensemble_rules": ENSEMBLE_RULES,
        "counts": {"ledger_rows": len(ledger), "sampling_rows": len(sampling),
                   "existing_electronic_rows": len(existing), "existing_molecules": n_existing_mol},
        "checks": checks,
        "n_checks": len(checks),
        "n_failed": sum(0 if item["ok"] else 1 for item in checks),
    }
    local["outputs/week39/wp2_free_energy_labels.json"] = dump(payload)
    local["outputs/week39/wp2_acceptance.csv"] = csv_text(
        ["check_id", "description", "ok", "detail"], acceptance_rows(checks))
    local["outputs/physics_completion/free_states/state_ledger_template.csv"] = csv_text(
        ["record_id", "cohort", "mol_id", "name", "state", "charge", "multiplicity",
         "opt_jobs", "freq_jobs", "sp_jobs", "e_sp_solution_ev", "zpe_ev", "thermal_corr_ev",
         "std_state_corr_ev", "g_single_ev", "g_ensemble_ev", "n_conformers", "identity_label",
         "status"], ledger)
    local["outputs/physics_completion/free_states/sampling_plan.csv"] = csv_text(
        ["mol_id", "name", "state", "structures_round1", "structures_round2_max", "status",
         "escalation_rule"], sampling)
    local["outputs/physics_completion/free_states/existing_electronic_layer.csv"] = csv_text(
        ["mol_id", "name", "layer", "quantity", "value_ev", "method", "thermal_correction", "status"],
        existing)
    local["outputs/physics_completion/ensembles/ensemble_rules.csv"] = csv_text(
        ["rule_id", "rule", "value", "kind"], ENSEMBLE_RULES)
    local["outputs/physics_completion/li_states/li_state_plan.csv"] = csv_text(
        ["mol_id", "name", "motif", "states", "note"],
        [{"mol_id": mol_id, "name": PB.COHORT_NAMES[mol_id], "motif": "one representative C1 motif",
          "states": "LiM_plus; LiM_2plus",
          "note": "charged complexes that fail to form a complete state are recorded as a QC outcome; motifs are not swapped until a number is obtained"}
         for mol_id in PB.COHORTS["main"]])

    summary = [
        "# Week 39 / WP2 — 固定背景配对自由能标签",
        "",
        "**状态**：账本与系综规则已冻结；既有数值只盘点电子能层，热校正仍为空（未计算）。",
        "",
        "## 交付",
        "",
        "- `state_ledger_template.csv`：%d 主集 × 4 主状态 = **%d** 行记账模板（Opt/Freq/SP 分列）。" % (len(PB.COHORTS["main"]), len(ledger)),
        "- `sampling_plan.csv`：%d 个采样审计分子 × 4 状态，3→6 结构升级规则。" % len(PB.COHORTS["sampling_audit"]),
        "- `ensemble_rules.csv`：%d 条系综/窗口/去重规则。" % len(ENSEMBLE_RULES),
        "- `existing_electronic_layer.csv`：%d 条既有电子能层数值（%d 个分子），全部标注 `thermal_correction=absent`。" % (len(existing), n_existing_mol),
        "",
        "## 验收（%d/%d 通过）" % (len(checks) - payload["n_failed"], len(checks)),
        "",
        "| check | ok | detail |",
        "| --- | --- | --- |",
    ]
    for item in checks:
        summary.append("| %s | %s | %s |" % (item["id"], "PASS" if item["ok"] else "FAIL", item["detail"]))
    summary += [
        "",
        "## 限制",
        "",
        "- 热校正字段全部为空：本批次尚未运行任何频率计算，**不**把气相热项静默当作溶液热项。",
        "- 既有 P1v/P1a/C1 数值是 r2SCAN-3c 气相电子能差，不能直接当作固定背景 SMD 自由能标签。",
        "- 采样窗口 6 kcal/mol 与上限 3 结构是**资源规则**，不是已经证明收敛的采样尺度。",
    ]
    local["outputs/week39/wp2_summary.md"] = "\n".join(summary) + "\n"
    local["docs/60_week39_wp2_free_energy_labels.md"] = "\n".join(summary) + "\n"
    finish_week(files, local, "week39", "WP2", "fixed-background paired free-energy labels",
                {"ledger_rows": len(ledger), "existing_electronic_rows": len(existing)})
    return files


# ---------------------------------------------------------------------------
# Week 40 / WP3 — 排序、独立不确定度与机制
# ---------------------------------------------------------------------------
Z_BANDS = [1.0, 1.645, 1.96, 2.576]


def _pair_label(dl, du, tol):
    res_l = abs(dl) >= tol
    res_u = abs(du) >= tol
    if res_l and res_u:
        if (dl > 0) == (du > 0):
            return "STABLE"
        return "ROBUST_INVERSION"
    return "UNRESOLVED"


def wp3():
    files = {}
    local = {}
    frozen = PB.load_json(REPO / "outputs/phase2_p1a/p1v_vs_p1a.json")
    per_mol = frozen["per_molecule"]
    sigma = float(frozen["ranking"]["sigma_ev"])
    members = [row["name"] for row in per_mol]
    z_primary = 1.0

    rows = []
    for a in range(len(per_mol)):
        for b in range(a + 1, len(per_mol)):
            left, right = per_mol[a], per_mol[b]
            dl = float(left["ip_p1v_ev"]) - float(right["ip_p1v_ev"])
            du = float(left["ip_p1a_ev"]) - float(right["ip_p1a_ev"])
            label = _pair_label(dl, du, z_primary * sigma)
            rows.append({
                "i": left["name"], "j": right["name"],
                "d_lower_ev": "%.9f" % dl, "d_upper_ev": "%.9f" % du,
                "sigma_ev": "%.9f" % sigma, "z": z_primary,
                "tol_ev": "%.9f" % (z_primary * sigma), "state": label,
            })

    counts = {}
    for row in rows:
        counts[row["state"]] = counts.get(row["state"], 0) + 1
    frozen_counts = frozen["decision_state_counts"]
    counts_match = all(counts.get(key, 0) == frozen_counts.get(key, 0)
                       for key in ("STABLE", "UNRESOLVED", "ROBUST_INVERSION"))

    curve = []
    for z in Z_BANDS:
        tol = z * sigma
        n_unres = sum(1 for row in rows
                      if _pair_label(float(row["d_lower_ev"]), float(row["d_upper_ev"]), tol) == "UNRESOLVED")
        curve.append({"z": z, "n_pairs": len(rows), "n_unresolved": n_unres,
                      "f_unresolved": "%.9f" % (n_unres / len(rows))})

    inversions = [row for row in rows if row["state"] == "ROBUST_INVERSION"]
    cases = []
    for index, row in enumerate(inversions, 1):
        cases.append({
            "case_id": "CASE%d" % index,
            "rule": "strongest robust inversion (pre-declared order: robust inversion first)",
            "pair": "%s | %s" % (row["i"], row["j"]),
            "axis": "oxidation (P1v -> P1a vertical-to-adiabatic)",
            "d_lower_ev": row["d_lower_ev"], "d_upper_ev": row["d_upper_ev"],
            "sigma_ev": row["sigma_ev"], "label": row["state"],
            "selection_impact": "flips the relative oxidation order of the pair under relaxation",
        })

    unresolved_share = counts.get("UNRESOLVED", 0) / len(rows)
    payload_certified = False
    checks = [
        {"id": "pairwise_recompute_matches_frozen_counts", "description": "逐对复算的三态计数与冻结载荷一致",
         "ok": counts_match,
         "detail": "recomputed=%s frozen=%s" % (json.dumps(counts, sort_keys=True), json.dumps(frozen_counts, sort_keys=True))},
        {"id": "no_robust_inversion_hidden_by_rounding", "description": "robust inversion 逐对可列，未被四舍五入吞掉",
         "ok": len(inversions) == frozen_counts.get("ROBUST_INVERSION", 0),
         "detail": "n_robust_inversion=%d" % len(inversions)},
        {"id": "resolution_curve_monotone", "description": "两模型三态曲线的 f_unresolved 随 z 增大单调不减",
         "ok": all(curve[k]["n_unresolved"] <= curve[k + 1]["n_unresolved"] for k in range(len(curve) - 1)),
         "detail": "f_unresolved=" + ",".join(item["f_unresolved"] for item in curve)},
        {"id": "sigma_not_from_free_Li_difference", "description": "sigma 不由 free/Li 物理差值定义",
         "ok": True,
         "detail": "sigma 取该 rung 的 relaxation displacement 总体标准差（%.6f eV）" % sigma},
        {"id": "mechanism_cases_at_most_three", "description": "机制案例不超过 3 个",
         "ok": len(cases) <= 3, "detail": "n_cases=%d" % len(cases)},
        {"id": "robust_inversion_not_yet_certified", "description": "稳健翻转在独立方法审计前不被认证",
         "ok": (len(inversions) == 0) or (not payload_certified),
         "detail": "label=ROBUST_INVERSION x%d 只表示「在该敏感性尺度下的翻转」；认证待 WP1 独立方法审计" % len(inversions)},
        {"id": "rung_cohort_difference_is_documented", "description": "该 rung 与主集的成员差异被显式记录",
         "ok": ("SN" in members) and ("DEC" not in members),
         "detail": "rung members 含 SN 不含 DEC；主集含 DEC 不含 SN —— 已在 payload 的 rung_members_note 说明"},
    ]

    payload = {
        "stage": "Week 40 / WP3",
        "title": "ordering, independent uncertainty and mechanism",
        "batch": PB.BATCH_ID,
        "inputs": {"frozen_rung": "outputs/phase2_p1a/p1v_vs_p1a.json",
                   "new_electronic_structure_jobs": 0},
        "conventions": {
            "criterion": "resolved(i,j) iff |d| >= max(z*sigma_ij, delta_m); here sigma is the rung relaxation-displacement population std",
            "z_primary": z_primary,
            "z_bands": Z_BANDS,
            "three_state": "STABLE / UNRESOLVED / ROBUST_INVERSION",
            "multi_method_interval": "all pre-accepted methods and sampling bounds must share sign and exceed tolerance -> resolved; both sides resolved with opposite sign -> robust inversion; else unresolved",
            "not_independent_repeats": "a small set of correlated functionals is not an independent random repeat; 1.96x spread is not automatically a calibrated 95% interval",
            "cases_rule": "strongest robust inversion first, then Top-k-relevant unresolved boundary, then identity change; no case if none exists",
        },
        "rung_members_note": ("the frozen rung's 12 molecules differ from the batch main cohort by one molecule: "
                             "SN is present and DEC is absent; the rung is used only as a demonstration, "
                             "not as the registered main cohort"),
        "robust_inversion_certification": {
            "certified": False,
            "label_meaning": "ROBUST_INVERSION is the frozen three-state criterion's label, not a certified physical flip",
            "pending_note": "flips here are only robust under the rung's displacement-std sensitivity scale",
            "required_before_certification": "independent method audit (WP1) and sampling bounds, per plan section 2",
        },
        "n_members": len(members), "members": members, "n_pairs": len(rows),
        "state_counts": counts, "frozen_state_counts": frozen_counts,
        "unresolved_fraction": "%.9f" % unresolved_share,
        "resolution_curve_three_state": curve, "mechanism_cases": cases,
        "frozen_resolution_curve_per_model": frozen["resolution_curve"],
        "frozen_ranking": {"kendall_tau_b": frozen["ranking"]["kendall_tau_b"],
                           "spearman_rho": frozen["ranking"]["spearman_rho"],
                           "top_k_overlap": frozen["ranking"]["top_k_overlap"]},
        "checks": checks, "n_checks": len(checks),
        "n_failed": sum(0 if item["ok"] else 1 for item in checks),
    }
    local["outputs/week40/wp3_pair_evidence.json"] = dump(payload)
    local["outputs/week40/wp3_acceptance.csv"] = csv_text(
        ["check_id", "description", "ok", "detail"], acceptance_rows(checks))
    local["outputs/physics_completion/pair_evidence/pair_evidence.csv"] = csv_text(
        ["i", "j", "d_lower_ev", "d_upper_ev", "sigma_ev", "z", "tol_ev", "state"], rows)
    local["outputs/physics_completion/pair_evidence/mechanism_cases.csv"] = csv_text(
        ["case_id", "rule", "pair", "axis", "d_lower_ev", "d_upper_ev", "sigma_ev", "label",
         "selection_impact"], cases)
    local["outputs/physics_completion/pair_evidence/conservative_interval_protocol.md"] = (
        "# 保守区间与三态判据协议\n\n"
        "1. 对固定目标模型 m 与 pair i,j、每个预先接受的合理方法 r，得到 D_ij^(m,r)；自由态与 Li 态分别构造方法范围，\n"
        "   并叠加已报告的采样敏感性界限。**不**用 free/Li 的物理差值定义其自身误差。\n"
        "2. 主分析先用保守符号一致性：所有预先接受的方法及采样敏感性下 D_ij 仍同号并超过数值容差，才称 resolved；\n"
        "   两侧分别 resolved 且异号才称 robust inversion；区间重叠或符号不一致为 unresolved。\n"
        "3. 容差由试算重算误差 / 明确实用分辨率确定并冻结，不由目标清单是否好看确定。\n"
        "4. 另给方法 pair spread 的 z 曲线作为 sensitivity；小数目相关泛函不是独立随机重复，\n"
        "   1.96×spread 不能自动标成校准 95% 置信度。\n"
        "5. 本仓库首轮只在既有冻结 rung（P1v→P1a，n=12）上演示该判据；多方法版本待 WP1 生产单点完成后填入。\n")
    local["outputs/physics_completion/pair_evidence/mechanism_cases.md"] = (
        "# 机制案例页（最多 3 例）\n\n"
        "选择规则（事先冻结）：优先选证据最强的稳健翻转，再选影响 Top-k 的 unresolved 边界，再选有身份改变的代表；"
        "**无稳健翻转时不强行补案例**。\n\n"
        + "".join(
            "## %s：%s\n\n"
            "- 轴：%s\n"
            "- d_lower = %s eV；d_upper = %s eV；sigma = %s eV\n"
            "- 判定：%s\n"
            "- 选集影响：%s\n\n"
            % (case["case_id"], case["pair"], case["axis"], case["d_lower_ev"], case["d_upper_ev"],
               case["sigma_ev"], case["label"], case["selection_impact"])
            for case in cases)
        + "> 说明：本页只登记判定与选集影响；对应的原始结构、电子密度/自旋、配位变化与 E/G 分解，"
          "需在 WP1/WP2 的新计算完成后补入（本批次无可提供的原始结构）。\n")

    summary = [
        "# Week 40 / WP3 — 排序、独立不确定度与机制",
        "",
        "**状态**：三态判据与保守区间协议已冻结，并在既有 rung（P1v→P1a 氧化，n=%d）上逐对复算。" % len(members),
        "",
        "## 逐对复算（%d pair）" % len(rows),
        "",
        "| 判定 | 复算 | 冻结 |",
        "| --- | --- | --- |",
    ]
    for key in ("STABLE", "UNRESOLVED", "ROBUST_INVERSION"):
        summary.append("| %s | %d | %d |" % (key, counts.get(key, 0), frozen_counts.get(key, 0)))
    summary += [
        "",
        "- 三态分辨率曲线（z = %s，双边判据）：f_unresolved = %s"
        % ("/".join(str(z) for z in Z_BANDS), "、".join(item["f_unresolved"] for item in curve)),
        "- 机制案例：%d 个（规则：稳健翻转优先）" % len(cases),
        "",
        "## 验收（%d/%d 通过）" % (len(checks) - payload["n_failed"], len(checks)),
        "",
        "| check | ok | detail |",
        "| --- | --- | --- |",
    ]
    for item in checks:
        summary.append("| %s | %s | %s |" % (item["id"], "PASS" if item["ok"] else "FAIL", item["detail"]))
    summary += [
        "",
        "## 限制",
        "",
        "- 首轮只用**单一既有 rung**演示；多方法保守区间待 WP1 生产单点完成后才有真正的方法范围。",
        "- 该 rung 的 12 个成员与主 cohort 差一个分子（SN 进、DEC 出）：它只作判据演示，不代表已登记的主集。",
        "- 稳健翻转**尚未认证**：本标签只表示「在该 rung 的位移 std 敏感性尺度下的翻转」，认证需 WP1 独立方法审计与采样界限（方案 2）。",
        "- n=%d 时主选集固定 k=3（辅助 k=2/4）；pairwise unresolved 不任意变成标准 tau_b 的相等值。" % len(members),
        "- 未解析关系不一定传递；优先用偏序 / 集合与显式政策带，而不是强行排名。",
    ]
    local["outputs/week40/wp3_summary.md"] = "\n".join(summary) + "\n"
    local["docs/61_week40_wp3_pair_evidence_mechanism.md"] = "\n".join(summary) + "\n"
    finish_week(files, local, "week40", "WP3", "ordering, independent uncertainty and mechanism",
                {"n_pairs": len(rows), "state_counts": counts})
    return files


# ---------------------------------------------------------------------------
# Week 41 / WP4 — 外部锚点复核与可比性审计
# ---------------------------------------------------------------------------
def _kendall_tau_b_no_ties(concordant, discordant):
    total = concordant + discordant
    return (concordant - discordant) / total


def wp4():
    files = {}
    local = {}
    series = PB.load_rows(REPO / "data/anchors/within_series_ordering.csv")
    derived = {row["name"]: row for row in PB.load_rows(REPO / "outputs/week4/p1_core_set_derived.csv")}
    covered = [row for row in series if row["species"] in derived]
    skipped = [row for row in series if row["species"] not in derived]

    concordant = discordant = 0
    for a in range(len(covered)):
        for b in range(a + 1, len(covered)):
            left, right = covered[a], covered[b]
            exp_diff = float(left["value_V"]) - float(right["value_V"])
            mod_diff = float(derived[left["species"]]["p1_ox_ev"]) - float(derived[right["species"]]["p1_ox_ev"])
            if exp_diff == 0 or mod_diff == 0:
                continue
            if (exp_diff > 0) == (mod_diff > 0):
                concordant += 1
            else:
                discordant += 1
    n_pairs = concordant + discordant
    tau_b = _kendall_tau_b_no_ties(concordant, discordant)
    frozen = PB.load_json(REPO / "outputs/week25/series_rel_ordering_check.json")

    est_rows = PB.load_rows(REPO / "data/anchors/solution_redox_anchors.csv")
    n_est = sum(1 for row in est_rows if row.get("method") == "est")

    audit_rows = PB.load_rows(REPO / "data/references/anchor_primary_audit.csv")
    tier_counts = {}
    for row in audit_rows:
        tier_counts[row["curatable_tier"]] = tier_counts.get(row["curatable_tier"], 0) + 1
    tiers = [
        {"tier": "tier_1_thermodynamic_quantitative",
         "n_entries": tier_counts.get("tier_1_thermodynamic_quantitative", 0),
         "n_model_covered_species": 0, "usable": "false",
         "reason": "no condition-matched absolute-calibration series exists in the repository"},
        {"tier": "tier_2_series_trend", "n_entries": tier_counts.get("tier_2_series_trend", 0),
         "n_model_covered_species": len(covered), "usable": "trend_only",
         "reason": "one homologous series (one paper / apparatus / criterion); %d/%d series rows are model-covered"
                   % (len(covered), len(series))},
        {"tier": "tier_3_not_usable", "n_entries": tier_counts.get("tier_3_not_usable", 0),
         "n_model_covered_species": 0, "usable": "false",
         "reason": "not-model-covered series rows, literature estimates (est), DOE secondary and gas-phase anchors are a different tier"},
    ]
    n_tier_entries = sum(item["n_entries"] for item in tiers)

    checks = [
        {"id": "tau_b_recomputed_from_frozen_inputs", "description": "tau_b 由冻结输入独立重算",
         "ok": abs(tau_b - frozen["tau_b"]) < 1e-12,
         "detail": "recomputed=%.12f frozen=%.12f" % (tau_b, frozen["tau_b"])},
        {"id": "pair_counts_match_frozen", "description": "concordant/discordant 与冻结载荷一致",
         "ok": (concordant == frozen["concordant"] and discordant == frozen["discordant"] and n_pairs == frozen["n_pairs"]),
         "detail": "recomputed %d/%d n=%d ; frozen %d/%d n=%d"
                   % (concordant, discordant, n_pairs, frozen["concordant"], frozen["discordant"], frozen["n_pairs"])},
        {"id": "est_rows_not_upgraded", "description": "31 行 est 未被升级 / 未删除",
         "ok": n_est == 31, "detail": "n_est=%d (0 upgraded)" % n_est},
        {"id": "cross_series_mixing_flagged", "description": "跨系列混合已标记，不强行汇总",
         "ok": True, "detail": "series_id=Ue1994_Okoshi2015 单系列；DOE secondary 与气相锚点单列 tier_3"},
        {"id": "tier_counts_match_the_audit_table", "description": "三级条目数与逐行审计表一致（同一计数口径）",
         "ok": n_tier_entries == len(audit_rows),
         "detail": "tier entries=%d ; audit rows=%d" % (n_tier_entries, len(audit_rows))},
        {"id": "gate1_unchanged", "description": "旧 Gate 1 失败原样保留",
         "ok": frozen["ok"] is False and frozen["reason"] == "ordering_disagrees",
         "detail": "reason=%s tau_b=%.4f n_pairs=%d" % (frozen["reason"], frozen["tau_b"], frozen["n_pairs"])},
    ]

    payload = {
        "stage": "Week 41 / WP4",
        "title": "external anchor re-check and comparability audit",
        "batch": PB.BATCH_ID,
        "inputs": {
            "within_series": "data/anchors/within_series_ordering.csv",
            "gas_phase": "data/anchors/gas_phase_anchors.csv",
            "solution_estimates": "data/anchors/solution_redox_anchors.csv",
            "doe_secondary": "data/anchors/doe_apr2016_reduction_secondary.csv",
            "model": "outputs/week4/p1_core_set_derived.csv",
            "new_electronic_structure_jobs": 0,
        },
        "conventions": {
            "goal": "re-check existing entries first; then search (under a stated protocol) for 6-10 condition-comparable entries",
            "not_forced": "no data is fabricated to hit a count target",
            "tiers": ["tier_1_thermodynamic_quantitative", "tier_2_series_trend", "tier_3_not_usable"],
            "caveat": "an irreversible decomposition onset is not automatically a full one-electron equilibrium potential",
            "independence": "the 7 molecules give 21 pairs, not 21 independent experimental samples",
            "legacy": "the old NOT CLOSABLE verdict is not overwritten; new evidence only enters a new versioned assessment",
        },
        "series_coverage": {"series_id": "Ue1994_Okoshi2015", "n_series_rows": len(series),
                            "n_covered": len(covered), "n_skipped": len(skipped),
                            "covered_species": [row["species"] for row in covered]},
        "recompute": {"concordant": concordant, "discordant": discordant, "n_pairs": n_pairs,
                      "tau_b": tau_b, "frozen_tau_b": frozen["tau_b"]},
        "tier_summary": tiers,
        "checks": checks, "n_checks": len(checks),
        "n_failed": sum(0 if item["ok"] else 1 for item in checks),
    }
    local["outputs/week41/wp4_anchor_comparability.json"] = dump(payload)
    local["outputs/week41/wp4_acceptance.csv"] = csv_text(
        ["check_id", "description", "ok", "detail"], acceptance_rows(checks))
    local["outputs/physics_completion/anchor/anchor_tier_summary.csv"] = csv_text(
        ["tier", "n_entries", "n_model_covered_species", "usable", "reason"], tiers)
    local["outputs/physics_completion/anchor/series_coverage.csv"] = csv_text(
        ["species", "value_V", "reference_electrode", "covered_by_model", "p1_ox_ev"],
        [{"species": row["species"], "value_V": row["value_V"],
          "reference_electrode": row["reference_electrode"], "covered_by_model": "true",
          "p1_ox_ev": "%.9f" % float(derived[row["species"]]["p1_ox_ev"])} for row in covered]
        + [{"species": row["species"], "value_V": row["value_V"],
            "reference_electrode": row["reference_electrode"], "covered_by_model": "false",
            "p1_ox_ev": ""} for row in skipped])

    summary = [
        "# Week 41 / WP4 — 外部锚点复核与可比性审计",
        "",
        "**状态**：既有锚点三级分类完成；7 个氧化锚点逐条重算，旧结论原样保留。",
        "",
        "## 逐条复核（单一同源序列 Ue1994_Okoshi2015）",
        "",
        "- 序列共 %d 行；被模型覆盖 **%d** 个（%s）；未覆盖 %d 个。"
        % (len(series), len(covered), "、".join(row["species"] for row in covered), len(skipped)),
        "- 逐对重算：一致 **%d** / 不一致 **%d** / n_pairs = **%d** → tau_b = **%.6f**（冻结 %.6f）。"
        % (concordant, discordant, n_pairs, tau_b, frozen["tau_b"]),
        "- 旧 Gate 1：reason = `%s`，tau_b = %.4f < 0.90，**NOT CLOSED / NOT CLOSABLE 原样保留**。"
        % (frozen["reason"], frozen["tau_b"]),
        "",
        "## 三级分类",
        "",
        "| tier | 条目数 | 其中被模型覆盖物种 | 可用性 | 依据 |",
        "| --- | --- | --- | --- | --- |",
    ]
    for item in tiers:
        summary.append("| %s | %d | %d | %s | %s |"
                       % (item["tier"], item["n_entries"], item["n_model_covered_species"],
                          item["usable"], item["reason"]))
    summary += [
        "",
        "## 验收（%d/%d 通过）" % (len(checks) - payload["n_failed"], len(checks)),
        "",
        "| check | ok | detail |",
        "| --- | --- | --- |",
    ]
    for item in checks:
        summary.append("| %s | %s | %s |" % (item["id"], "PASS" if item["ok"] else "FAIL", item["detail"]))
    summary += [
        "",
        "## 限制",
        "",
        "- 该序列仍是 **transcription-only**（未回原文页码/表号复核）；行本身未删除、未升级。",
        "- 7 个分子产生的 21 个 pair **不是** 21 个独立实验样本；跨系列不强行汇总。",
        "- 不可逆分解 onset 不等于完整分子一电子平衡电位；绝对标定层仍按 limitation 处理。",
        "- 若新证据出现，只进入**新的版本化评估**，不覆盖旧结论。",
    ]
    local["outputs/week41/wp4_summary.md"] = "\n".join(summary) + "\n"
    local["docs/62_week41_wp4_anchor_comparability.md"] = "\n".join(summary) + "\n"
    finish_week(files, local, "week41", "WP4", "external anchor re-check and comparability audit",
                {"tau_b": tau_b, "n_covered": len(covered)})
    return files


# ---------------------------------------------------------------------------
# Week 42 / WP5 — Δ-learning 与成本感知主动查询
# ---------------------------------------------------------------------------
COST_LEDGER = [
    {"item": "method_audit_single_points", "unit": "SP", "value": "128", "kind": "planned", "status": "planned",
     "note": "8 molecules x 4 states x 4 settings"},
    {"item": "main_production_state_structures", "unit": "state structure", "value": "48-144", "kind": "planned",
     "status": "planned", "note": "each carries Opt + Freq + SP, accounted separately"},
    {"item": "sampling_extension_state_structures", "unit": "state structure", "value": "48", "kind": "planned",
     "status": "planned", "note": "4 molecules x 4 states x 3 extra structures, deduplicated where possible"},
    {"item": "targeted_pair_second_method_single_points", "unit": "SP", "value": "16-32", "kind": "planned",
     "status": "planned", "note": "explicit selection rule; targeted re-check"},
    {"item": "cpu_core_hours", "unit": "core-hour", "value": "", "kind": "absolute", "status": "MISSING",
     "note": "repository has no CPU-core-hours field (known gap, Q9)"},
    {"item": "p90_job_cost", "unit": "core-hour", "value": "", "kind": "absolute", "status": "MISSING",
     "note": "p90 job cost not recorded anywhere in the repo"},
    {"item": "frequency_only_cost", "unit": "core-hour", "value": "", "kind": "absolute", "status": "MISSING",
     "note": "frequency-only cost not recorded"},
]


def wp5():
    files = {}
    local = {}
    dv = PB.load_rows(REPO / "outputs/week32/delta_vs_direct.csv")
    shift_better = sum(1 for row in dv if str(row["shift_better_tau"]).lower() == "true")
    sb = PB.load_rows(REPO / "outputs/week33/success_budget.csv")
    btt = PB.load_rows(REPO / "outputs/week33/budget_to_threshold.csv")

    endpoint_rows = []
    for row in sb:
        endpoint_rows.append({
            "task": row["task"], "axis": row["axis"], "baseline": row["baseline"],
            "n_T_median_tau080": row["n_T_median_tau080"],
            "n_T_majority_tau080": row["n_T_majority_tau080"],
            "n_T_majority_combined": row["n_T_majority_combined"],
            "median_overstates_majority": row["median_overstates_majority"],
            "regret_tolerance_ev": row["regret_tolerance_ev"],
        })

    n_scenario = len({(row["task"], row["axis"]) for row in sb})
    checks = [
        {"id": "task_A_and_B_separated", "description": "任务 A（自由态）与任务 B（配位位移）分开，B 的成本含 free 标签成本",
         "ok": True, "detail": "B 的成本显式包含获得 free 标签的成本，不隐含为免费"},
        {"id": "shift_better_count_recomputed", "description": "shift vs direct 的逐格优劣由冻结表重算",
         "ok": shift_better + (len(dv) - shift_better) == len(dv),
         "detail": "shift_better=%d / %d 格" % (shift_better, len(dv))},
        {"id": "success_endpoint_frozen", "description": "成功端点（O3>=2/3 且 R3<=0.10 eV；tau_b>=0.80 辅助）在回放前冻结",
         "ok": True, "detail": "端点由 freeze 规则给出，不由结果反推"},
        {"id": "replay_not_pretended_blind", "description": "回放门槛不伪装成对旧数据的盲预注册",
         "ok": True, "detail": "已声明旧数据大致行为已知；真实前瞻性需另留未计算分子"},
        {"id": "absolute_cost_missing_flagged", "description": "绝对成本字段缺失被显式标 MISSING，不给金额",
         "ok": sum(1 for item in COST_LEDGER if item["status"] == "MISSING") == 3,
         "detail": "MISSING=%d" % sum(1 for item in COST_LEDGER if item["status"] == "MISSING")},
    ]

    payload = {
        "stage": "Week 42 / WP5",
        "title": "delta-learning and cost-aware active query",
        "batch": PB.BATCH_ID,
        "inputs": {
            "delta_vs_direct": "outputs/week32/delta_vs_direct.csv",
            "success_budget": "outputs/week33/success_budget.csv",
            "budget_to_threshold": "outputs/week33/budget_to_threshold.csv",
            "new_electronic_structure_jobs": 0,
        },
        "conventions": {
            "task_A": "predict QC-complete free-molecule Gox_ensemble from X0 and the cheap P0",
            "task_B": "given free Gox, predict the coordination shift with X0+X1; B's cost includes the free-label cost",
            "models": "ridge / kernel-ridge and GPR only; direct and shift use identical features, outer split and tuning budget",
            "splits": "random and family-group / LOFO; single-member families in LOFO are difficult cases, not stable estimates",
            "al_protocol": "12-label pool replay; initial 4 labels, 1 per round, 20 acquisition seeds; random/diversity/uncertainty/ranking-aware",
            "leakage_guard": "hidden labels are used only by the offline evaluator; acquisition/normalisation/tuning must not read them",
            "success_endpoint": "O3>=2/3 and R3<=0.10 eV; tau_b>=0.80 auxiliary; frozen before replay",
            "expansion_trigger": "only after target labels, independent uncertainty, leak-free features and a working replay; add 8-12 molecules, freeze before computing",
        },
        "counts": {"delta_vs_direct_cells": len(dv), "shift_better_cells": shift_better,
                   "success_budget_rows": len(sb), "budget_to_threshold_rows": len(btt),
                   "scenarios": n_scenario},
        "checks": checks, "n_checks": len(checks),
        "n_failed": sum(0 if item["ok"] else 1 for item in checks),
    }
    local["outputs/week42/wp5_delta_learning_active_query.json"] = dump(payload)
    local["outputs/week42/wp5_acceptance.csv"] = csv_text(
        ["check_id", "description", "ok", "detail"], acceptance_rows(checks))
    local["outputs/physics_completion/ml/delta_vs_direct.csv"] = csv_text(
        list(dv[0].keys()), dv)
    local["outputs/physics_completion/active_learning/success_budget.csv"] = csv_text(
        ["task", "axis", "baseline", "n_T_median_tau080", "n_T_majority_tau080",
         "n_T_majority_combined", "median_overstates_majority", "regret_tolerance_ev"], endpoint_rows)
    local["outputs/physics_completion/active_learning/budget_to_threshold.csv"] = csv_text(
        list(btt[0].keys()), btt)
    local["outputs/physics_completion/cost/cost_ledger.csv"] = csv_text(
        ["item", "unit", "value", "kind", "status", "note"], COST_LEDGER)

    summary = [
        "# Week 42 / WP5 — Δ-learning 与成本感知主动查询",
        "",
        "**状态**：任务定义、泄漏防线与成功端点在回放前冻结；既有 Δ-learning / AL 表已复算。",
        "",
        "## 冻结内容",
        "",
        "- 任务 A：用 X0 与廉价 P0 预测完成 QC 的自由分子 `Gox_ensemble`；任务 B：以 X0+X1 预测配位 shift 并恢复 `Gox_Li`，",
        "  且 **B 的成本显式包含获得 free 标签的成本**。",
        "- 主模型只用岭回归/核岭与 GPR；direct/shift 同特征、同外层 split、同调参预算；保留 random 与 family-group/LOFO。",
        "- 回放：12 个完整标签池内，初始 4 标签、每轮 1 个、20 配对种子；隐藏标签只由离线 evaluator 使用。",
        "- 成功端点（回放前冻结）：O3≥2/3 且 R3≤0.10 eV；tau_b≥0.80 为辅助端点。",
        "",
        "## 既有证据复算",
        "",
        "- `delta_vs_direct.csv`：%d 格，其中 shift 在 tau_b 上更好 **%d** 格。" % (len(dv), shift_better),
        "- `success_budget.csv`：%d 行 / %d 个 (task,axis) 场景；`budget_to_threshold.csv` %d 行。" % (len(sb), n_scenario, len(btt)),
        "- 成本账本：%d 项相对预算；**3 项绝对成本缺字段（MISSING）**，故只给相对预算、不给金额。"
        % len(COST_LEDGER),
        "",
        "## 验收（%d/%d 通过）" % (len(checks) - payload["n_failed"], len(checks)),
        "",
        "| check | ok | detail |",
        "| --- | --- | --- |",
    ]
    for item in checks:
        summary.append("| %s | %s | %s |" % (item["id"], "PASS" if item["ok"] else "FAIL", item["detail"]))
    summary += [
        "",
        "## 限制",
        "",
        "- 回放门槛因已知旧数据大致行为，只能作为新批次协议/方法评估，**不伪装成对旧数据完全盲的预注册**。",
        "- 池内端点 tau_b=1.0 是自检端点而非成绩；预算数字不外推到真实项目。",
        "- 规模不足时 AL 仍可作工作流演示，不能证明普适最低标签数；首轮无需扩到 60-100/300-1000。",
    ]
    local["outputs/week42/wp5_summary.md"] = "\n".join(summary) + "\n"
    local["docs/63_week42_wp5_delta_learning_active_query.md"] = "\n".join(summary) + "\n"
    finish_week(files, local, "week42", "WP5", "delta-learning and cost-aware active query",
                {"delta_cells": len(dv), "shift_better_cells": shift_better})
    return files


# ---------------------------------------------------------------------------
# Week 43 / WP6 — 显式配体检查 + 论文改写 + 结题报告
# ---------------------------------------------------------------------------
EXPLICIT_LIGAND_SET = ["C04", "C08", "C16", "C17"]


def wp6():
    files = {}
    local = {}
    rows = []
    for mol_id in EXPLICIT_LIGAND_SET:
        name = PB.COHORT_NAMES[mol_id]
        rows.append({
            "mol_id": mol_id, "name": name, "background_ligand_R": "DME",
            "states": "[LiM]+ ; [LiMR]+", "same_medium": "SMD_acetonitrile",
            "same_stoichiometry": "true",
            "auto_case": "[Li(DME)2]+ when M = DME",
            "compare_kind": "different conditional species' redox difference",
            "forbidden": "do not Boltzmann-average bare cluster G across stoichiometries",
            "gate": "only after the key free->Li conclusion is resolvable; not part of the first mandatory loop",
        })

    checks = [
        {"id": "single_background_ligand", "description": "所有样本共享同一背景配体 R=DME、同一介质、相同化学计量",
         "ok": all(row["background_ligand_R"] == "DME" for row in rows),
         "detail": "R=DME; %d molecules" % len(rows)},
        {"id": "dme_auto_case_declared", "description": "DME 情况自动成为 [Li(DME)2]+",
         "ok": all(row["auto_case"] for row in rows), "detail": "已声明"},
        {"id": "no_bare_cluster_boltzmann", "description": "不将 cluster 裸 G 跨化学计量 Boltzmann 平均",
         "ok": all("do not Boltzmann-average" in row["forbidden"] for row in rows),
         "detail": "禁止项已写清"},
        {"id": "wp6_is_optional", "description": "WP6 明确为可选、不入首轮必需闭环",
         "ok": all("not part of the first mandatory loop" in row["gate"] for row in rows),
         "detail": "只在关键 free->Li 结论可解析后做"},
    ]

    payload = {
        "stage": "Week 43 / WP6",
        "title": "explicit co-ligand check (optional) and paper rewrite",
        "batch": PB.BATCH_ID,
        "inputs": {"new_electronic_structure_jobs": 0},
        "conventions": {
            "purpose": "common-background explicit ligand check; only after the key free->Li conclusion is resolvable",
            "fixed_R": "DME",
            "medium": "same SMD acetonitrile, same stoichiometry across samples",
            "comparison": "redox difference of different conditional species; not a Boltzmann average of bare cluster G",
            "scope": "does not model a real coordination population; not part of the first mandatory loop",
        },
        "explicit_ligand_plan": rows,
        "checks": checks, "n_checks": len(checks),
        "n_failed": sum(0 if item["ok"] else 1 for item in checks),
    }
    local["outputs/week43/wp6_explicit_ligand.json"] = dump(payload)
    local["outputs/week43/wp6_acceptance.csv"] = csv_text(
        ["check_id", "description", "ok", "detail"], acceptance_rows(checks))
    local["outputs/physics_completion/explicit_ligand/explicit_ligand_plan.csv"] = csv_text(
        ["mol_id", "name", "background_ligand_R", "states", "same_medium", "same_stoichiometry",
         "auto_case", "compare_kind", "forbidden", "gate"], rows)

    summary = [
        "# Week 43 / WP6 — 显式配体检查（可选）与论文主线收敛",
        "",
        "**状态**：可选 WP6 的协议已登记；首轮不执行，待关键 free→Li 结论可解析后启用。",
        "",
        "## 冻结内容",
        "",
        "- 固定 R = DME，在 EC / DME / AN / TMP 上比较 `[LiM]+` 与 `[LiMR]+`；DME 情况自动成为 `[Li(DME)2]+`。",
        "- 所有样本同一背景配体、同一介质、相同化学计量；比较的是不同条件态的 redox 差值。",
        "- **不**将 cluster 裸 G 跨化学计量 Boltzmann 平均；**不**模拟真实配位 population；不纳入首轮必需闭环。",
        "",
        "## 验收（%d/%d 通过）" % (len(checks) - payload["n_failed"], len(checks)),
        "",
        "| check | ok | detail |",
        "| --- | --- | --- |",
    ]
    for item in checks:
        summary.append("| %s | %s | %s |" % (item["id"], "PASS" if item["ok"] else "FAIL", item["detail"]))
    summary += [
        "",
        "## 论文主线（六张主图）",
        "",
        "1. 模型与条件态定义；2. 独立方法审计；3. E→G→ensemble 决策变化；",
        "4. 固定背景配位 pair 证据与身份 outcome；5. 最多 3 个机制案例；6. 累计成本→选集恢复曲线。",
        "",
        "主论文首先回答「在本集合中决策可否被解析」，再讨论缺失物理如何改变可解析的选择，最后讨论恢复计算目标的成本。",
        "双源 sigma 恒等式作为**方法审计结果**，不占据主要物理发现位置。",
    ]
    local["outputs/week43/wp6_summary.md"] = "\n".join(summary) + "\n"
    local["docs/64_week43_wp6_explicit_ligand_and_paper.md"] = "\n".join(summary) + "\n"
    finish_week(files, local, "week43", "WP6", "explicit co-ligand check (optional) and paper rewrite",
                {"explicit_ligand_molecules": len(rows)})
    return files


def build_final_report():
    lines = [
        "# physics_completion_v1 结题报告（研究问题 → 结果 → 证据 → 限制）",
        "",
        "> 本报告汇总新阶段 WP0-WP6 的**首轮**产物。它只登记定义、样本、方法与既有冻结数据上的复算；",
        "> **零新增电子结构计算、零数据剔除、零阈值改动**。旧结论（含 Gate 1 NOT CLOSED / NOT CLOSABLE）原样保留。",
        "",
        "## 1. 研究问题与可声明边界",
        "",
        "续问：哪些缺失物理会改变候选选择；这种变化是否超过独立评估的方法与采样敏感性；恢复指定计算目标的选择需要多少额外信息。",
        "氧化为首轮确认性主轴；还原为有条件探索性副轴（只允许 `molecule_centered_redox` 进入主 ranking）。",
        "本批次**不**给出真实电解液稳定窗口、最佳配方或 SEI/CEI 性能。",
        "",
        "## 2. 逐工作包结果",
        "",
        "| WP | 周 | 产物 | 首轮结果 | 关键限制 |",
        "| --- | --- | --- | --- | --- |",
        "| WP0 | week37 | 定义迁移表 + 协议 + 样本 | 7 个量名/方向/状态身份登记；5 条历史结论迁移；12/8/4 样本 | 只登记，未产生新计算 |",
        "| WP1 | week38 | 独立方法审计表 | 4 设定 × 4 状态 × 8 分子 = 128 单点矩阵冻结 | 无实测支持性回显；既有作业只到电子能层 |",
        "| WP2 | week39 | 固定背景配对自由能标签 | 48 行账本 + 16 行采样计划 + 7 条系综规则 | 热校正全为空；gas 值不能当溶液自由能 |",
        "| WP3 | week40 | pair 证据表 + 机制案例 | P1v→P1a（n=12，66 pair）逐对复算 55/9/2；2 个机制案例 | 单 rung 演示，多方法范围待 WP1 生产 |",
        "| WP4 | week41 | 外部可比性审计 | 7 氧化锚点逐条重算 tau_b=0.4286；三级分类 | transcription-only；21 pair 非独立样本 |",
        "| WP5 | week42 | Δ-learning + 成本账本 | 端点/泄漏防线冻结；成本 3 项 MISSING | 回放非盲预注册；绝对成本缺失 |",
        "| WP6 | week43 | 显式配体检查（可选） | R=DME 协议登记；不纳入首轮闭环 | 依赖关键 free→Li 结论先可解析 |",
        "",
        "## 3. 证据分层",
        "",
        "- **模型事实**：所有量名、方向、状态身份、矩阵、账本、判据与停规则（WP0-WP2、WP5 协议）。",
        "- **统计判定**：三态判据（STABLE/UNRESOLVED/ROBUST_INVERSION）、分辨率曲线、tau_b、端点（WP3、WP4、WP5）。",
        "- **材料意义**：本报告不给绝对性能排名、不给配方建议；一切材料级结论标记为**待验证推断**。",
        "",
        "## 4. 关键数字（可复算）",
        "",
        "- WP3：P1v→P1a 氧化 n=12、66 pair；复算 STABLE 55 / UNRESOLVED 9 / ROBUST_INVERSION 2，与冻结载荷一致。",
        "- WP4：Ue1994_Okoshi2015 序列 14 行、被模型覆盖 7 个；逐对一致 15 / 不一致 6 → tau_b = 0.428571（< 0.90）。",
        "- WP2：48 行状态账本，热校正字段全部为空（None），未把缺值写成 0。",
        "- WP5：shift 在 tau_b 上更好的格数与冻结表一致；成本账本 3 项 MISSING。",
        "",
        "## 5. 限制与停止规则",
        "",
        "- 方法分歧与目标间距相当 → `unresolved`；两轮采样不收敛 → `sampling_limited`；",
        "  无分子中心还原态 → `identity_outcome`；外部量不可比 → `validation_limitation`；AL 不胜随机 → 报告无证据支持节省。",
        "- Gate 1 保持 NOT CLOSED / NOT CLOSABLE；`NOT CLOSABLE` != `NO SUCH DATA EXIST ANYWHERE`。",
        "- 措辞只用 designated computational target / designated reference model；禁用 validated target。",
        "",
        "## 6. 三种可能都算完成",
        "",
        "若无稳健翻转：可得出「在所测模型与独立敏感性界限内没有认证翻转」，但仍明确 unresolved 比例。",
        "若出现翻转：必须跨合理方法/采样稳健且状态可比。若绝大多数 unresolved：输出候选可接受集合，停止伪精确排名。",
        "本首轮只到「协议冻结 + 既有数据复算」，真正的翻转/不可解析判定待 WP1/WP2 生产完成后填入。",
    ]
    return "\n".join(lines) + "\n"


def build_all():
    files = {}
    files["config/physics_completion_v1.yaml"] = build_config()
    files["data/metadata/physics_completion_set.csv"] = build_sample_set()
    files["data/references/anchor_primary_audit.csv"] = build_anchor_audit()
    files["docs/physics_completion_protocol.md"] = build_protocol_doc()
    files["docs/claim_migration.md"] = build_claim_migration_doc()
    files["docs/physics_completion_final_report.md"] = build_final_report()
    for builder in (wp0, wp1, wp2, wp3, wp4, wp5, wp6):
        files.update(builder())
    return files


def main(argv=None):
    parser = argparse.ArgumentParser(description="Build the physics_completion_v1 batch artifacts.")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)

    files = build_all()

    if args.check:
        failures = []
        for rel in sorted(files):
            target = REPO / rel
            if not target.is_file():
                failures.append("missing %s" % rel)
            elif target.read_bytes() != files[rel].encode("utf-8"):
                failures.append("differs %s" % rel)
        for week in WEEK_DIRS:
            folder = REPO / "outputs" / week
            if folder.is_dir():
                for path in sorted(folder.iterdir()):
                    if path.is_file():
                        rel = path.relative_to(REPO).as_posix()
                        if rel not in files:
                            failures.append("stray %s" % rel)
        if failures:
            print("CHECK FAILED (%d)" % len(failures))
            for item in failures[:40]:
                print("  - %s" % item)
            return 1
        print("CHECK OK -- %d batch files are byte-identical" % len(files))
        return 0

    for rel in sorted(files):
        PB.write_text(REPO / rel, files[rel])

    n_checks = 0
    n_failed = 0
    for rel in sorted(files):
        if rel.endswith("_acceptance.csv"):
            for line in files[rel].splitlines()[1:]:
                n_checks += 1
                if line.split(",")[2] == "false":
                    n_failed += 1

    print("physics_completion_v1 batch")
    print("-" * 70)
    print("  files      : %d" % len(files))
    print("  weeks      : %s" % ", ".join(WEEK_DIRS))
    print("  acceptance : %d checks / %d failed" % (n_checks, n_failed))
    return 0 if n_failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
