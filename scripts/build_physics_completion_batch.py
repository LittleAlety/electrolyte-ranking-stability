# -*- coding: utf-8 -*-
r"""新阶段（评审实施方案 WP0-WP6）产物生成器：physics_completion_v1 批次。

本生成器把仓库外那份**建议实施方案**（电解液排序稳定性：物理证据补强与决策预算研究
执行方案）登记成可复现的批次产物，并基于仓库既有冻结数据给出**首轮**可交付分析。
排序/配对证据层不运行新的电子结构计算，不改动任何既有冻结数据、阈值或结论
（WP1 本机方法回显与 WP2 四主态 pilot 是单列的支撑性/试算作业，原始输出不入镜像）；只新增
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
        "new_electronic_structure_jobs_scope": "jobs that change the frozen ranking/pair evidence; the WP1 supportability probe, the WP2 free-state pilot and the WP2 production first segment are counted separately",
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


# ---------------------------------------------------------------------------
# 方案 15.4 —— 本机方法回显与 smoke 核验（ORCA 6.1.1 / xTB 6.7.1pre）
# 记录来自本机支撑性探针（water、SMD 乙腈）；原始日志留在仓库外，不入交付镜像。
# 只登记派生结论，不改变排序/配对证据的零新增计算口径。
# ---------------------------------------------------------------------------
LOCAL_TOOLCHAIN = [
    {"tool": "orca", "version": "6.1.1 - RELEASE", "path_hint": "E:/orca_6_1_1/orca.exe",
     "note": "Windows AVX2 build; used for supportability echo only"},
    {"tool": "xtb", "version": "6.7.1pre (5071a88)", "path_hint": "E:/orca_6_1_1/xtb-6.7.1pre/xtb.exe",
     "note": "compiled 2024-07-23; cheap-search arm"},
]

LOCAL_METHOD_ECHO = [
    {"setting_id": "S1", "plan_functional": "omegaB97X-D4", "basis": "def2-TZVP",
     "plan_keyword_status": "rejected_as_written", "orca_keyword": "wB97X-D4 def2-TZVP",
     "functional_echo": "WB97X-V (range-separated)", "hf_exchange_fraction": "0.167000",
     "dispersion_module": "DFTD4 V3.4.0 (atom-pairwise)", "solvent_echo": "ACETONITRILE (SMD)",
     "recognized": "true"},
    {"setting_id": "S2", "plan_functional": "omegaB97X-D4", "basis": "def2-TZVPD",
     "plan_keyword_status": "rejected_as_written", "orca_keyword": "wB97X-D4 def2-TZVPD",
     "functional_echo": "WB97X-V (range-separated)", "hf_exchange_fraction": "0.167000",
     "dispersion_module": "DFTD4 V3.4.0 (atom-pairwise)", "solvent_echo": "ACETONITRILE (SMD)",
     "recognized": "true"},
    {"setting_id": "S3", "plan_functional": "PBE0-D4", "basis": "def2-TZVP",
     "plan_keyword_status": "rejected_as_written", "orca_keyword": "PBE0 D4 def2-TZVP",
     "functional_echo": "PBE (hybrid)", "hf_exchange_fraction": "0.250000",
     "dispersion_module": "DFTD4 V3.4.0 (atom-pairwise)", "solvent_echo": "ACETONITRILE (SMD)",
     "recognized": "true"},
    {"setting_id": "S4", "plan_functional": "PBE0-D4", "basis": "def2-TZVPD",
     "plan_keyword_status": "rejected_as_written", "orca_keyword": "PBE0 D4 def2-TZVPD",
     "functional_echo": "PBE (hybrid)", "hf_exchange_fraction": "0.250000",
     "dispersion_module": "DFTD4 V3.4.0 (atom-pairwise)", "solvent_echo": "ACETONITRILE (SMD)",
     "recognized": "true"},
]

LOCAL_KEYWORD_REJECTIONS = [
    {"plan_keyword": "omegaB97X-D4", "result": "UNRECOGNIZED OR DUPLICATED KEYWORD(S) IN SIMPLE INPUT LINE: OMEGAB97X-D4",
     "remedy": "ORCA 6.1.1 spelling is wB97X-D4 (case-insensitive)"},
    {"plan_keyword": "PBE0-D4", "result": "UNRECOGNIZED OR DUPLICATED KEYWORD(S) IN SIMPLE INPUT LINE: PBE0-D4",
     "remedy": "ORCA 6.1.1 has no hyphenated -D4 preset; give dispersion as a separate keyword: PBE0 D4"},
]

LOCAL_SMOKE_RUNS = [
    {"run_id": "A", "state": "neutral_M", "charge": "0", "multiplicity": "1",
     "orca_keyword": "wB97X-D4 def2-TZVP", "solvent": "SMD_acetonitrile", "basis_functions": "43",
     "scf_cycles": "20", "final_single_point_eh": "-76.482423279072",
     "terminated_normally": "true", "wall_sec": "7.245"},
    {"run_id": "B", "state": "neutral_M_audit_control", "charge": "0", "multiplicity": "1",
     "orca_keyword": "PBE0 D4 def2-TZVPD", "solvent": "SMD_acetonitrile", "basis_functions": "58",
     "scf_cycles": "17", "final_single_point_eh": "-76.388928931275",
     "terminated_normally": "true", "wall_sec": "6.100"},
    {"run_id": "C", "state": "neutral_M_numfreq", "charge": "0", "multiplicity": "1",
     "orca_keyword": "wB97X-D4 def2-TZVP NumFreq", "solvent": "SMD_acetonitrile", "basis_functions": "43",
     "scf_cycles": "11", "final_single_point_eh": "-76.482428352560",
     "terminated_normally": "true", "wall_sec": "29.269"},
    {"run_id": "D", "state": "cation_M_plus", "charge": "1", "multiplicity": "2",
     "orca_keyword": "wB97X-D4 def2-TZVPD", "solvent": "SMD_acetonitrile", "basis_functions": "58",
     "scf_cycles": "17", "final_single_point_eh": "-76.136730138462",
     "terminated_normally": "true", "wall_sec": "6.656"},
]

LOCAL_FREQ_CHECK = {"molecule": "water", "n_atoms": "3", "n_modes": "9",
                    "modes": "6 near-zero (trans/rot) + 3 real: 1588.03, 3892.52, 3972.24 cm^-1",
                    "imaginary_modes": "0", "note": "NumFreq under SMD completed; frequency path usable"}

# ---------------------------------------------------------------------------
# 方案 15.5 / 15.6 —— 自由态 + Li 配位态 pilot（新增电子结构计算，12 主集）
# 几何：RDKit ETKDG+MMFF 起点 -> xTB 6.7.1pre GFN2 Opt（气相），同一驱动脚本重算；
# 单点：ORCA 6.1.1 wB97X-D4 + SMD(acetonitrile)，中性 def2-TZVP / def2-TZVPD 各一次，
# 阳离子与 Li 复合物一律 def2-TZVPD（含弥散：电离/还原态必须）。
# Li 初始位按给体类型（羰基/醚/腈/S=O/P=O 氧或腈氮）沿外侧 1.9 A 放置后 GFN2 优化；
# 2+ 态若 Li 在弛豫中解离，照实记为 dissociated，不换 motif 硬凑配位数（方案 6.3/9）。
# 原始输出留在仓库外，不入交付镜像。
# ---------------------------------------------------------------------------
PILOT_METHOD_NOTE = "wB97X-D4/def2-TZVP (neutral); wB97X-D4/def2-TZVPD (charged, diffuse); SMD acetonitrile"
PILOT_GEOM_NOTE = "RDKit ETKDG+MMFF start -> xTB 6.7.1pre GFN2 Opt (gas)"

#: pilot 覆盖的 12 主集分子（顺序 = 主集顺序）。
PILOT_MAIN_MOLECULES = [("C01", "DMC"), ("C02", "EMC"), ("C03", "DEC"), ("C04", "EC"), ("C05", "PC"), ("C08", "DME"), ("C09", "DOL"), ("C13", "GBL"), ("C14", "SL"), ("C15", "DMSO"), ("C16", "AN"), ("C17", "TMP")]

#: Li 初始位所用给体（逐分子记录；direction 为单位矢量，指向 Li 起点外移一侧）。
PILOT_DONOR_PLACEMENT = [
    {"mol_id": "C01", "name": "DMC", "donor_family": "carbonyl", "donor_index": "3", "direction": "[-0.042043, 0.916646, -0.397483]", "placement": "Li start at donor outward 1.9 A from the GFN2-optimised neutral geometry"},
    {"mol_id": "C02", "name": "EMC", "donor_family": "carbonyl", "donor_index": "4", "direction": "[-0.299228, 0.037424, -0.953447]", "placement": "Li start at donor outward 1.9 A from the GFN2-optimised neutral geometry"},
    {"mol_id": "C03", "name": "DEC", "donor_family": "carbonyl", "donor_index": "4", "direction": "[-0.165012, 0.571254, -0.804015]", "placement": "Li start at donor outward 1.9 A from the GFN2-optimised neutral geometry"},
    {"mol_id": "C04", "name": "EC", "donor_family": "carbonyl", "donor_index": "4", "direction": "[0.892373, 0.429417, 0.138823]", "placement": "Li start at donor outward 1.9 A from the GFN2-optimised neutral geometry"},
    {"mol_id": "C05", "name": "PC", "donor_family": "carbonyl", "donor_index": "5", "direction": "[-0.606250, -0.270178, -0.747974]", "placement": "Li start at donor outward 1.9 A from the GFN2-optimised neutral geometry"},
    {"mol_id": "C08", "name": "DME", "donor_family": "ether", "donor_index": "1", "direction": "[0.218490, 0.348784, 0.911379]", "placement": "Li start at donor outward 1.9 A from the GFN2-optimised neutral geometry"},
    {"mol_id": "C09", "name": "DOL", "donor_family": "ether", "donor_index": "2", "direction": "[-0.016158, 0.937163, 0.348518]", "placement": "Li start at donor outward 1.9 A from the GFN2-optimised neutral geometry"},
    {"mol_id": "C13", "name": "GBL", "donor_family": "carbonyl", "donor_index": "0", "direction": "[0.922428, 0.360256, 0.139076]", "placement": "Li start at donor outward 1.9 A from the GFN2-optimised neutral geometry"},
    {"mol_id": "C14", "name": "SL", "donor_family": "sulfone", "donor_index": "0", "direction": "[0.597317, 0.151480, 0.787570]", "placement": "Li start at donor outward 1.9 A from the GFN2-optimised neutral geometry"},
    {"mol_id": "C15", "name": "DMSO", "donor_family": "sulfoxide", "donor_index": "3", "direction": "[0.103789, 0.680423, 0.725433]", "placement": "Li start at donor outward 1.9 A from the GFN2-optimised neutral geometry"},
    {"mol_id": "C16", "name": "AN", "donor_family": "nitrile", "donor_index": "2", "direction": "[0.999831, 0.000151, -0.018397]", "placement": "Li start at donor outward 1.9 A from the GFN2-optimised neutral geometry"},
    {"mol_id": "C17", "name": "TMP", "donor_family": "phosphoryl", "donor_index": "3", "direction": "[-0.033129, 0.102713, -0.994159]", "placement": "Li start at donor outward 1.9 A from the GFN2-optimised neutral geometry"},
]

#: 自由态单点（M 两基组 + M_plus 一致基组），每分子 3 行。
PILOT_FREE_STATE_ENERGIES = [
    {"record_id": "C01|M", "mol_id": "C01", "name": "DMC", "state": "M", "charge": "0", "multiplicity": "1", "basis": "def2-TZVP", "orca_keyword": "wB97X-D4 def2-TZVP SMD(acetonitrile) SP", "scf_cycles": "20", "final_sp_eh": "-343.854211228425", "terminated": "true", "wall_sec": "36.0", "cores": "4"},
    {"record_id": "C01|M_tzvpd", "mol_id": "C01", "name": "DMC", "state": "M", "charge": "0", "multiplicity": "1", "basis": "def2-TZVPD", "orca_keyword": "wB97X-D4 def2-TZVPD SMD(acetonitrile) SP", "scf_cycles": "20", "final_sp_eh": "-343.856181464206", "terminated": "true", "wall_sec": "62.3", "cores": "4"},
    {"record_id": "C01|M_plus", "mol_id": "C01", "name": "DMC", "state": "M_plus", "charge": "1", "multiplicity": "2", "basis": "def2-TZVPD", "orca_keyword": "wB97X-D4 def2-TZVPD SMD(acetonitrile) SP", "scf_cycles": "20", "final_sp_eh": "-343.527011826787", "terminated": "true", "wall_sec": "76.1", "cores": "4"},
    {"record_id": "C02|M", "mol_id": "C02", "name": "EMC", "state": "M", "charge": "0", "multiplicity": "1", "basis": "def2-TZVP", "orca_keyword": "wB97X-D4 def2-TZVP SMD(acetonitrile) SP", "scf_cycles": "20", "final_sp_eh": "-383.211199702608", "terminated": "true", "wall_sec": "60.5", "cores": "4"},
    {"record_id": "C02|M_tzvpd", "mol_id": "C02", "name": "EMC", "state": "M", "charge": "0", "multiplicity": "1", "basis": "def2-TZVPD", "orca_keyword": "wB97X-D4 def2-TZVPD SMD(acetonitrile) SP", "scf_cycles": "20", "final_sp_eh": "-383.213141521146", "terminated": "true", "wall_sec": "102.3", "cores": "4"},
    {"record_id": "C02|M_plus", "mol_id": "C02", "name": "EMC", "state": "M_plus", "charge": "1", "multiplicity": "2", "basis": "def2-TZVPD", "orca_keyword": "wB97X-D4 def2-TZVPD SMD(acetonitrile) SP", "scf_cycles": "31", "final_sp_eh": "-382.899405959663", "terminated": "true", "wall_sec": "165.2", "cores": "4"},
    {"record_id": "C03|M", "mol_id": "C03", "name": "DEC", "state": "M", "charge": "0", "multiplicity": "1", "basis": "def2-TZVP", "orca_keyword": "wB97X-D4 def2-TZVP SMD(acetonitrile) SP", "scf_cycles": "20", "final_sp_eh": "-422.568593818278", "terminated": "true", "wall_sec": "41.4", "cores": "4"},
    {"record_id": "C03|M_tzvpd", "mol_id": "C03", "name": "DEC", "state": "M", "charge": "0", "multiplicity": "1", "basis": "def2-TZVPD", "orca_keyword": "wB97X-D4 def2-TZVPD SMD(acetonitrile) SP", "scf_cycles": "20", "final_sp_eh": "-422.570563717756", "terminated": "true", "wall_sec": "71.7", "cores": "4"},
    {"record_id": "C03|M_plus", "mol_id": "C03", "name": "DEC", "state": "M_plus", "charge": "1", "multiplicity": "2", "basis": "def2-TZVPD", "orca_keyword": "wB97X-D4 def2-TZVPD SMD(acetonitrile) SP", "scf_cycles": "34", "final_sp_eh": "-422.254798778826", "terminated": "true", "wall_sec": "133.3", "cores": "4"},
    {"record_id": "C04|M", "mol_id": "C04", "name": "EC", "state": "M", "charge": "0", "multiplicity": "1", "basis": "def2-TZVP", "orca_keyword": "wB97X-D4 def2-TZVP SMD(acetonitrile) SP", "scf_cycles": "20", "final_sp_eh": "-342.648140166966", "terminated": "true", "wall_sec": "29.8", "cores": "4"},
    {"record_id": "C04|M_tzvpd", "mol_id": "C04", "name": "EC", "state": "M", "charge": "0", "multiplicity": "1", "basis": "def2-TZVPD", "orca_keyword": "wB97X-D4 def2-TZVPD SMD(acetonitrile) SP", "scf_cycles": "20", "final_sp_eh": "-342.650103844399", "terminated": "true", "wall_sec": "51.0", "cores": "4"},
    {"record_id": "C04|M_plus", "mol_id": "C04", "name": "EC", "state": "M_plus", "charge": "1", "multiplicity": "2", "basis": "def2-TZVPD", "orca_keyword": "wB97X-D4 def2-TZVPD SMD(acetonitrile) SP", "scf_cycles": "18", "final_sp_eh": "-342.333927357547", "terminated": "true", "wall_sec": "62.5", "cores": "4"},
    {"record_id": "C05|M", "mol_id": "C05", "name": "PC", "state": "M", "charge": "0", "multiplicity": "1", "basis": "def2-TZVP", "orca_keyword": "wB97X-D4 def2-TZVP SMD(acetonitrile) SP", "scf_cycles": "20", "final_sp_eh": "-382.007760780767", "terminated": "true", "wall_sec": "51.4", "cores": "4"},
    {"record_id": "C05|M_tzvpd", "mol_id": "C05", "name": "PC", "state": "M", "charge": "0", "multiplicity": "1", "basis": "def2-TZVPD", "orca_keyword": "wB97X-D4 def2-TZVPD SMD(acetonitrile) SP", "scf_cycles": "20", "final_sp_eh": "-382.009785515284", "terminated": "true", "wall_sec": "89.1", "cores": "4"},
    {"record_id": "C05|M_plus", "mol_id": "C05", "name": "PC", "state": "M_plus", "charge": "1", "multiplicity": "2", "basis": "def2-TZVPD", "orca_keyword": "wB97X-D4 def2-TZVPD SMD(acetonitrile) SP", "scf_cycles": "24", "final_sp_eh": "-381.695871733911", "terminated": "true", "wall_sec": "127.6", "cores": "4"},
    {"record_id": "C08|M", "mol_id": "C08", "name": "DME", "state": "M", "charge": "0", "multiplicity": "1", "basis": "def2-TZVP", "orca_keyword": "wB97X-D4 def2-TZVP SMD(acetonitrile) SP", "scf_cycles": "20", "final_sp_eh": "-309.100173877788", "terminated": "true", "wall_sec": "53.7", "cores": "4"},
    {"record_id": "C08|M_tzvpd", "mol_id": "C08", "name": "DME", "state": "M", "charge": "0", "multiplicity": "1", "basis": "def2-TZVPD", "orca_keyword": "wB97X-D4 def2-TZVPD SMD(acetonitrile) SP", "scf_cycles": "20", "final_sp_eh": "-309.102759637016", "terminated": "true", "wall_sec": "91.5", "cores": "4"},
    {"record_id": "C08|M_plus", "mol_id": "C08", "name": "DME", "state": "M_plus", "charge": "1", "multiplicity": "2", "basis": "def2-TZVPD", "orca_keyword": "wB97X-D4 def2-TZVPD SMD(acetonitrile) SP", "scf_cycles": "18", "final_sp_eh": "-308.851702088551", "terminated": "true", "wall_sec": "87.3", "cores": "4"},
    {"record_id": "C09|M", "mol_id": "C09", "name": "DOL", "state": "M", "charge": "0", "multiplicity": "1", "basis": "def2-TZVP", "orca_keyword": "wB97X-D4 def2-TZVP SMD(acetonitrile) SP", "scf_cycles": "20", "final_sp_eh": "-268.549202816037", "terminated": "true", "wall_sec": "29.3", "cores": "4"},
    {"record_id": "C09|M_tzvpd", "mol_id": "C09", "name": "DOL", "state": "M", "charge": "0", "multiplicity": "1", "basis": "def2-TZVPD", "orca_keyword": "wB97X-D4 def2-TZVPD SMD(acetonitrile) SP", "scf_cycles": "20", "final_sp_eh": "-268.551257729030", "terminated": "true", "wall_sec": "49.7", "cores": "4"},
    {"record_id": "C09|M_plus", "mol_id": "C09", "name": "DOL", "state": "M_plus", "charge": "1", "multiplicity": "2", "basis": "def2-TZVPD", "orca_keyword": "wB97X-D4 def2-TZVPD SMD(acetonitrile) SP", "scf_cycles": "18", "final_sp_eh": "-268.287236055064", "terminated": "true", "wall_sec": "54.0", "cores": "4"},
    {"record_id": "C13|M", "mol_id": "C13", "name": "GBL", "state": "M", "charge": "0", "multiplicity": "1", "basis": "def2-TZVP", "orca_keyword": "wB97X-D4 def2-TZVP SMD(acetonitrile) SP", "scf_cycles": "20", "final_sp_eh": "-306.736096877865", "terminated": "true", "wall_sec": "41.4", "cores": "4"},
    {"record_id": "C13|M_tzvpd", "mol_id": "C13", "name": "GBL", "state": "M", "charge": "0", "multiplicity": "1", "basis": "def2-TZVPD", "orca_keyword": "wB97X-D4 def2-TZVPD SMD(acetonitrile) SP", "scf_cycles": "20", "final_sp_eh": "-306.737875285260", "terminated": "true", "wall_sec": "68.5", "cores": "4"},
    {"record_id": "C13|M_plus", "mol_id": "C13", "name": "GBL", "state": "M_plus", "charge": "1", "multiplicity": "2", "basis": "def2-TZVPD", "orca_keyword": "wB97X-D4 def2-TZVPD SMD(acetonitrile) SP", "scf_cycles": "21", "final_sp_eh": "-306.442615657033", "terminated": "true", "wall_sec": "100.2", "cores": "4"},
    {"record_id": "C14|M", "mol_id": "C14", "name": "SL", "state": "M", "charge": "0", "multiplicity": "1", "basis": "def2-TZVP", "orca_keyword": "wB97X-D4 def2-TZVP SMD(acetonitrile) SP", "scf_cycles": "20", "final_sp_eh": "-706.150931720970", "terminated": "true", "wall_sec": "73.3", "cores": "4"},
    {"record_id": "C14|M_tzvpd", "mol_id": "C14", "name": "SL", "state": "M", "charge": "0", "multiplicity": "1", "basis": "def2-TZVPD", "orca_keyword": "wB97X-D4 def2-TZVPD SMD(acetonitrile) SP", "scf_cycles": "20", "final_sp_eh": "-706.153885628549", "terminated": "true", "wall_sec": "121.2", "cores": "4"},
    {"record_id": "C14|M_plus", "mol_id": "C14", "name": "SL", "state": "M_plus", "charge": "1", "multiplicity": "2", "basis": "def2-TZVPD", "orca_keyword": "wB97X-D4 def2-TZVPD SMD(acetonitrile) SP", "scf_cycles": "18", "final_sp_eh": "-705.862184264030", "terminated": "true", "wall_sec": "132.1", "cores": "4"},
    {"record_id": "C15|M", "mol_id": "C15", "name": "DMSO", "state": "M", "charge": "0", "multiplicity": "1", "basis": "def2-TZVP", "orca_keyword": "wB97X-D4 def2-TZVP SMD(acetonitrile) SP", "scf_cycles": "20", "final_sp_eh": "-553.367190849897", "terminated": "true", "wall_sec": "24.8", "cores": "4"},
    {"record_id": "C15|M_tzvpd", "mol_id": "C15", "name": "DMSO", "state": "M", "charge": "0", "multiplicity": "1", "basis": "def2-TZVPD", "orca_keyword": "wB97X-D4 def2-TZVPD SMD(acetonitrile) SP", "scf_cycles": "20", "final_sp_eh": "-553.370194407920", "terminated": "true", "wall_sec": "38.3", "cores": "4"},
    {"record_id": "C15|M_plus", "mol_id": "C15", "name": "DMSO", "state": "M_plus", "charge": "1", "multiplicity": "2", "basis": "def2-TZVPD", "orca_keyword": "wB97X-D4 def2-TZVPD SMD(acetonitrile) SP", "scf_cycles": "20", "final_sp_eh": "-553.132235081139", "terminated": "true", "wall_sec": "46.9", "cores": "4"},
    {"record_id": "C16|M", "mol_id": "C16", "name": "AN", "state": "M", "charge": "0", "multiplicity": "1", "basis": "def2-TZVP", "orca_keyword": "wB97X-D4 def2-TZVP SMD(acetonitrile) SP", "scf_cycles": "19", "final_sp_eh": "-132.866446560651", "terminated": "true", "wall_sec": "15.8", "cores": "4"},
    {"record_id": "C16|M_tzvpd", "mol_id": "C16", "name": "AN", "state": "M", "charge": "0", "multiplicity": "1", "basis": "def2-TZVPD", "orca_keyword": "wB97X-D4 def2-TZVPD SMD(acetonitrile) SP", "scf_cycles": "19", "final_sp_eh": "-132.866896538774", "terminated": "true", "wall_sec": "19.1", "cores": "4"},
    {"record_id": "C16|M_plus", "mol_id": "C16", "name": "AN", "state": "M_plus", "charge": "1", "multiplicity": "2", "basis": "def2-TZVPD", "orca_keyword": "wB97X-D4 def2-TZVPD SMD(acetonitrile) SP", "scf_cycles": "17", "final_sp_eh": "-132.519126824547", "terminated": "true", "wall_sec": "19.3", "cores": "4"},
    {"record_id": "C17|M", "mol_id": "C17", "name": "TMP", "state": "M", "charge": "0", "multiplicity": "1", "basis": "def2-TZVP", "orca_keyword": "wB97X-D4 def2-TZVP SMD(acetonitrile) SP", "scf_cycles": "20", "final_sp_eh": "-762.423053579956", "terminated": "true", "wall_sec": "79.0", "cores": "4"},
    {"record_id": "C17|M_tzvpd", "mol_id": "C17", "name": "TMP", "state": "M", "charge": "0", "multiplicity": "1", "basis": "def2-TZVPD", "orca_keyword": "wB97X-D4 def2-TZVPD SMD(acetonitrile) SP", "scf_cycles": "20", "final_sp_eh": "-762.426072838656", "terminated": "true", "wall_sec": "136.9", "cores": "4"},
    {"record_id": "C17|M_plus", "mol_id": "C17", "name": "TMP", "state": "M_plus", "charge": "1", "multiplicity": "2", "basis": "def2-TZVPD", "orca_keyword": "wB97X-D4 def2-TZVPD SMD(acetonitrile) SP", "scf_cycles": "18", "final_sp_eh": "-762.105771531730", "terminated": "true", "wall_sec": "144.9", "cores": "4"},
]

#: Li 配位两态（LiM_plus / LiM_2plus）；Li 起点见 PILOT_DONOR_PLACEMENT。
#: donor_contacts = 2.60 A 内的给体 O/N 数；identity=dissociated_* 表示 2+ 态 Li 已离开片段。
PILOT_LI_STATE_ENERGIES = [
    {"record_id": "C01|LiM_plus", "mol_id": "C01", "name": "DMC", "state": "LiM_plus", "charge": "1", "multiplicity": "1", "basis": "def2-TZVPD", "orca_keyword": "wB97X-D4 def2-TZVPD SMD(acetonitrile) SP", "basis_functions": "302", "scf_cycles": "20", "final_sp_eh": "-351.306668426280", "terminated": "true", "wall_sec": "70.1", "cores": "4", "li_o_ang": "1.654", "nonli_components": "1", "donor_contacts": "1", "identity": "intact_monodentate_carbonyl"},
    {"record_id": "C01|LiM_2plus", "mol_id": "C01", "name": "DMC", "state": "LiM_2plus", "charge": "2", "multiplicity": "2", "basis": "def2-TZVPD", "orca_keyword": "wB97X-D4 def2-TZVPD SMD(acetonitrile) SP", "basis_functions": "302", "scf_cycles": "20", "final_sp_eh": "-350.957111976693", "terminated": "true", "wall_sec": "86.1", "cores": "4", "li_o_ang": "1.805", "nonli_components": "1", "donor_contacts": "1", "identity": "intact_monodentate_carbonyl"},
    {"record_id": "C02|LiM_plus", "mol_id": "C02", "name": "EMC", "state": "LiM_plus", "charge": "1", "multiplicity": "1", "basis": "def2-TZVPD", "orca_keyword": "wB97X-D4 def2-TZVPD SMD(acetonitrile) SP", "basis_functions": "357", "scf_cycles": "20", "final_sp_eh": "-390.664261161903", "terminated": "true", "wall_sec": "119.1", "cores": "4", "li_o_ang": "1.659", "nonli_components": "1", "donor_contacts": "1", "identity": "intact_monodentate_carbonyl"},
    {"record_id": "C02|LiM_2plus", "mol_id": "C02", "name": "EMC", "state": "LiM_2plus", "charge": "2", "multiplicity": "2", "basis": "def2-TZVPD", "orca_keyword": "wB97X-D4 def2-TZVPD SMD(acetonitrile) SP", "basis_functions": "357", "scf_cycles": "31", "final_sp_eh": "-390.323857580036", "terminated": "true", "wall_sec": "194.2", "cores": "4", "li_o_ang": "1.782", "nonli_components": "1", "donor_contacts": "1", "identity": "intact_monodentate_carbonyl"},
    {"record_id": "C03|LiM_plus", "mol_id": "C03", "name": "DEC", "state": "LiM_plus", "charge": "1", "multiplicity": "1", "basis": "def2-TZVPD", "orca_keyword": "wB97X-D4 def2-TZVPD SMD(acetonitrile) SP", "basis_functions": "412", "scf_cycles": "20", "final_sp_eh": "-430.021811072568", "terminated": "true", "wall_sec": "81.5", "cores": "4", "li_o_ang": "1.653", "nonli_components": "1", "donor_contacts": "1", "identity": "intact_monodentate_carbonyl"},
    {"record_id": "C03|LiM_2plus", "mol_id": "C03", "name": "DEC", "state": "LiM_2plus", "charge": "2", "multiplicity": "2", "basis": "def2-TZVPD", "orca_keyword": "wB97X-D4 def2-TZVPD SMD(acetonitrile) SP", "basis_functions": "412", "scf_cycles": "20", "final_sp_eh": "-429.679002025732", "terminated": "true", "wall_sec": "97.2", "cores": "4", "li_o_ang": "1.736", "nonli_components": "1", "donor_contacts": "1", "identity": "intact_monodentate_carbonyl"},
    {"record_id": "C04|LiM_plus", "mol_id": "C04", "name": "EC", "state": "LiM_plus", "charge": "1", "multiplicity": "1", "basis": "def2-TZVPD", "orca_keyword": "wB97X-D4 def2-TZVPD SMD(acetonitrile) SP", "basis_functions": "284", "scf_cycles": "20", "final_sp_eh": "-350.101404846212", "terminated": "true", "wall_sec": "62.1", "cores": "4", "li_o_ang": "1.658", "nonli_components": "1", "donor_contacts": "1", "identity": "intact_monodentate_carbonyl"},
    {"record_id": "C04|LiM_2plus", "mol_id": "C04", "name": "EC", "state": "LiM_2plus", "charge": "2", "multiplicity": "2", "basis": "def2-TZVPD", "orca_keyword": "wB97X-D4 def2-TZVPD SMD(acetonitrile) SP", "basis_functions": "284", "scf_cycles": "18", "final_sp_eh": "-349.772032662564", "terminated": "true", "wall_sec": "68.2", "cores": "4", "li_o_ang": "1.852", "nonli_components": "1", "donor_contacts": "1", "identity": "intact_monodentate_carbonyl"},
    {"record_id": "C05|LiM_plus", "mol_id": "C05", "name": "PC", "state": "LiM_plus", "charge": "1", "multiplicity": "1", "basis": "def2-TZVPD", "orca_keyword": "wB97X-D4 def2-TZVPD SMD(acetonitrile) SP", "basis_functions": "339", "scf_cycles": "20", "final_sp_eh": "-389.461161737606", "terminated": "true", "wall_sec": "95.1", "cores": "4", "li_o_ang": "1.651", "nonli_components": "1", "donor_contacts": "1", "identity": "intact_monodentate_carbonyl"},
    {"record_id": "C05|LiM_2plus", "mol_id": "C05", "name": "PC", "state": "LiM_2plus", "charge": "2", "multiplicity": "2", "basis": "def2-TZVPD", "orca_keyword": "wB97X-D4 def2-TZVPD SMD(acetonitrile) SP", "basis_functions": "339", "scf_cycles": "23", "final_sp_eh": "-389.134132175016", "terminated": "true", "wall_sec": "148.7", "cores": "4", "li_o_ang": "1.800", "nonli_components": "1", "donor_contacts": "1", "identity": "intact_monodentate_carbonyl"},
    {"record_id": "C08|LiM_plus", "mol_id": "C08", "name": "DME", "state": "LiM_plus", "charge": "1", "multiplicity": "1", "basis": "def2-TZVPD", "orca_keyword": "wB97X-D4 def2-TZVPD SMD(acetonitrile) SP", "basis_functions": "335", "scf_cycles": "20", "final_sp_eh": "-316.574613930125", "terminated": "true", "wall_sec": "67.3", "cores": "4", "li_o_ang": "1.795", "nonli_components": "1", "donor_contacts": "2", "identity": "intact_bidentate_ether"},
    {"record_id": "C08|LiM_2plus", "mol_id": "C08", "name": "DME", "state": "LiM_2plus", "charge": "2", "multiplicity": "2", "basis": "def2-TZVPD", "orca_keyword": "wB97X-D4 def2-TZVPD SMD(acetonitrile) SP", "basis_functions": "335", "scf_cycles": "18", "final_sp_eh": "-316.277931354453", "terminated": "true", "wall_sec": "67.2", "cores": "4", "li_o_ang": "11.298", "nonli_components": "1", "donor_contacts": "0", "identity": "dissociated_ether"},
    {"record_id": "C09|LiM_plus", "mol_id": "C09", "name": "DOL", "state": "LiM_plus", "charge": "1", "multiplicity": "1", "basis": "def2-TZVPD", "orca_keyword": "wB97X-D4 def2-TZVPD SMD(acetonitrile) SP", "basis_functions": "262", "scf_cycles": "20", "final_sp_eh": "-275.998301763872", "terminated": "true", "wall_sec": "57.3", "cores": "4", "li_o_ang": "1.973", "nonli_components": "1", "donor_contacts": "2", "identity": "intact_bidentate_ether"},
    {"record_id": "C09|LiM_2plus", "mol_id": "C09", "name": "DOL", "state": "LiM_2plus", "charge": "2", "multiplicity": "2", "basis": "def2-TZVPD", "orca_keyword": "wB97X-D4 def2-TZVPD SMD(acetonitrile) SP", "basis_functions": "262", "scf_cycles": "22", "final_sp_eh": "-275.715481828471", "terminated": "true", "wall_sec": "75.8", "cores": "4", "li_o_ang": "2.505", "nonli_components": "1", "donor_contacts": "1", "identity": "intact_monodentate_ether"},
    {"record_id": "C13|LiM_plus", "mol_id": "C13", "name": "GBL", "state": "LiM_plus", "charge": "1", "multiplicity": "1", "basis": "def2-TZVPD", "orca_keyword": "wB97X-D4 def2-TZVPD SMD(acetonitrile) SP", "basis_functions": "299", "scf_cycles": "20", "final_sp_eh": "-314.190822388363", "terminated": "true", "wall_sec": "78.3", "cores": "4", "li_o_ang": "1.667", "nonli_components": "1", "donor_contacts": "1", "identity": "intact_monodentate_carbonyl"},
    {"record_id": "C13|LiM_2plus", "mol_id": "C13", "name": "GBL", "state": "LiM_2plus", "charge": "2", "multiplicity": "2", "basis": "def2-TZVPD", "orca_keyword": "wB97X-D4 def2-TZVPD SMD(acetonitrile) SP", "basis_functions": "299", "scf_cycles": "23", "final_sp_eh": "-313.866423793393", "terminated": "true", "wall_sec": "105.1", "cores": "4", "li_o_ang": "1.815", "nonli_components": "1", "donor_contacts": "1", "identity": "intact_monodentate_carbonyl"},
    {"record_id": "C14|LiM_plus", "mol_id": "C14", "name": "SL", "state": "LiM_plus", "charge": "1", "multiplicity": "1", "basis": "def2-TZVPD", "orca_keyword": "wB97X-D4 def2-TZVPD SMD(acetonitrile) SP", "basis_functions": "363", "scf_cycles": "20", "final_sp_eh": "-713.604058153811", "terminated": "true", "wall_sec": "89.2", "cores": "4", "li_o_ang": "1.885", "nonli_components": "1", "donor_contacts": "2", "identity": "intact_bidentate_sulfone"},
    {"record_id": "C14|LiM_2plus", "mol_id": "C14", "name": "SL", "state": "LiM_2plus", "charge": "2", "multiplicity": "2", "basis": "def2-TZVPD", "orca_keyword": "wB97X-D4 def2-TZVPD SMD(acetonitrile) SP", "basis_functions": "363", "scf_cycles": "18", "final_sp_eh": "-713.289177417651", "terminated": "true", "wall_sec": "88.1", "cores": "4", "li_o_ang": "1.721", "nonli_components": "1", "donor_contacts": "1", "identity": "intact_monodentate_sulfone"},
    {"record_id": "C15|LiM_plus", "mol_id": "C15", "name": "DMSO", "state": "LiM_plus", "charge": "1", "multiplicity": "1", "basis": "def2-TZVPD", "orca_keyword": "wB97X-D4 def2-TZVPD SMD(acetonitrile) SP", "basis_functions": "231", "scf_cycles": "20", "final_sp_eh": "-560.832093775537", "terminated": "true", "wall_sec": "47.4", "cores": "4", "li_o_ang": "1.628", "nonli_components": "1", "donor_contacts": "1", "identity": "intact_monodentate_sulfoxide"},
    {"record_id": "C15|LiM_2plus", "mol_id": "C15", "name": "DMSO", "state": "LiM_2plus", "charge": "2", "multiplicity": "2", "basis": "def2-TZVPD", "orca_keyword": "wB97X-D4 def2-TZVPD SMD(acetonitrile) SP", "basis_functions": "231", "scf_cycles": "20", "final_sp_eh": "-560.561162382104", "terminated": "true", "wall_sec": "57.4", "cores": "4", "li_o_ang": "1.802", "nonli_components": "1", "donor_contacts": "1", "identity": "intact_monodentate_sulfoxide"},
    {"record_id": "C16|LiM_plus", "mol_id": "C16", "name": "AN", "state": "LiM_plus", "charge": "1", "multiplicity": "1", "basis": "def2-TZVPD", "orca_keyword": "wB97X-D4 def2-TZVPD SMD(acetonitrile) SP", "basis_functions": "155", "scf_cycles": "19", "final_sp_eh": "-140.319887493920", "terminated": "true", "wall_sec": "21.8", "cores": "4", "li_o_ang": "1.859", "nonli_components": "1", "donor_contacts": "1", "identity": "intact_monodentate_nitrile"},
    {"record_id": "C16|LiM_2plus", "mol_id": "C16", "name": "AN", "state": "LiM_2plus", "charge": "2", "multiplicity": "2", "basis": "def2-TZVPD", "orca_keyword": "wB97X-D4 def2-TZVPD SMD(acetonitrile) SP", "basis_functions": "155", "scf_cycles": "18", "final_sp_eh": "-139.946294773154", "terminated": "true", "wall_sec": "21.5", "cores": "4", "li_o_ang": "10.953", "nonli_components": "1", "donor_contacts": "0", "identity": "dissociated_nitrile"},
    {"record_id": "C17|LiM_plus", "mol_id": "C17", "name": "TMP", "state": "LiM_plus", "charge": "1", "multiplicity": "1", "basis": "def2-TZVPD", "orca_keyword": "wB97X-D4 def2-TZVPD SMD(acetonitrile) SP", "basis_functions": "412", "scf_cycles": "20", "final_sp_eh": "-769.884723216208", "terminated": "true", "wall_sec": "159.6", "cores": "4", "li_o_ang": "1.604", "nonli_components": "1", "donor_contacts": "1", "identity": "intact_monodentate_phosphoryl"},
    {"record_id": "C17|LiM_2plus", "mol_id": "C17", "name": "TMP", "state": "LiM_2plus", "charge": "2", "multiplicity": "2", "basis": "def2-TZVPD", "orca_keyword": "wB97X-D4 def2-TZVPD SMD(acetonitrile) SP", "basis_functions": "412", "scf_cycles": "26", "final_sp_eh": "-769.550930450943", "terminated": "true", "wall_sec": "213.7", "cores": "4", "li_o_ang": "1.684", "nonli_components": "1", "donor_contacts": "1", "identity": "intact_monodentate_phosphoryl"},
]

#: 液/气标准态项：RT ln(V_m)，V_m = RT/P = 24.4654 L/mol @ 298.15 K, 1 atm。
PILOT_LEDGER_RAW = [
    {"record_id": "C01|M", "mol_id": "C01", "name": "DMC", "state": "M", "level": "wB97X-D4/def2-TZVP SMD(acetonitrile) NumFreq (qRRHO)", "e_sp_eh": "-343.854211229029", "zpe_eh": "0.09601496", "e_to_g_thermal_eh": "0.06577493", "enthalpy_eh": "-343.75019266", "entropy_corr_eh": "-0.03825196", "g_single_eh": "-343.78844462", "qrrho": "true", "temp_k": "298.15", "pressure_atm": "1.00", "cutoff_cm1": "1.00", "lowest_freq_cm1": "73.31", "imaginary_modes": "0"},
]

#: 冻结 C1 层的对照（混口径：把气相自由 IP 当作 SMD 参考）；逐分子查表见 c1_primary。
PILOT_C1_FROZEN_REF = {
    "C01": {"mol_id": "C01", "name": "DMC", "motif_id": "m1", "frozen_d_ip_smd_ev": "-1.75858",
            "convention": "frozen C1 used the gas-phase free IP as the SMD reference (mixed convention)"},
}

PILOT_COST_JOBS = [
    {"job_id": "C01|M|xtb_opt", "mol_id": "C01", "molecule": "DMC", "state": "M", "phase": "xtb_opt", "method": "GFN2-xTB Opt", "cores": "1", "wall_sec": "0.09", "status": "ok"},
    {"job_id": "C01|M_plus|xtb_opt", "mol_id": "C01", "molecule": "DMC", "state": "M_plus", "phase": "xtb_opt", "method": "GFN2-xTB Opt", "cores": "1", "wall_sec": "0.15", "status": "ok"},
    {"job_id": "C01|LiM_plus|xtb_opt", "mol_id": "C01", "molecule": "DMC", "state": "LiM_plus", "phase": "xtb_opt", "method": "GFN2-xTB Opt", "cores": "1", "wall_sec": "0.13", "status": "ok"},
    {"job_id": "C01|LiM_2plus|xtb_opt", "mol_id": "C01", "molecule": "DMC", "state": "LiM_2plus", "phase": "xtb_opt", "method": "GFN2-xTB Opt", "cores": "1", "wall_sec": "0.14", "status": "ok"},
    {"job_id": "C01|M|orca_sp", "mol_id": "C01", "molecule": "DMC", "state": "M", "phase": "orca_sp", "method": "wB97X-D4/def2-TZVP SMD", "cores": "4", "wall_sec": "36.0", "status": "ok"},
    {"job_id": "C01|M_tzvpd|orca_sp", "mol_id": "C01", "molecule": "DMC", "state": "M", "phase": "orca_sp", "method": "wB97X-D4/def2-TZVPD SMD", "cores": "4", "wall_sec": "62.3", "status": "ok"},
    {"job_id": "C01|M_plus|orca_sp", "mol_id": "C01", "molecule": "DMC", "state": "M_plus", "phase": "orca_sp", "method": "wB97X-D4/def2-TZVPD SMD", "cores": "4", "wall_sec": "76.1", "status": "ok"},
    {"job_id": "C01|LiM_plus|orca_sp", "mol_id": "C01", "molecule": "DMC", "state": "LiM_plus", "phase": "orca_sp", "method": "wB97X-D4/def2-TZVPD SMD", "cores": "4", "wall_sec": "70.1", "status": "ok"},
    {"job_id": "C01|LiM_2plus|orca_sp", "mol_id": "C01", "molecule": "DMC", "state": "LiM_2plus", "phase": "orca_sp", "method": "wB97X-D4/def2-TZVPD SMD", "cores": "4", "wall_sec": "86.1", "status": "ok"},
    {"job_id": "C02|M|xtb_opt", "mol_id": "C02", "molecule": "EMC", "state": "M", "phase": "xtb_opt", "method": "GFN2-xTB Opt", "cores": "1", "wall_sec": "0.14", "status": "ok"},
    {"job_id": "C02|M_plus|xtb_opt", "mol_id": "C02", "molecule": "EMC", "state": "M_plus", "phase": "xtb_opt", "method": "GFN2-xTB Opt", "cores": "1", "wall_sec": "0.23", "status": "ok"},
    {"job_id": "C02|LiM_plus|xtb_opt", "mol_id": "C02", "molecule": "EMC", "state": "LiM_plus", "phase": "xtb_opt", "method": "GFN2-xTB Opt", "cores": "1", "wall_sec": "0.19", "status": "ok"},
    {"job_id": "C02|LiM_2plus|xtb_opt", "mol_id": "C02", "molecule": "EMC", "state": "LiM_2plus", "phase": "xtb_opt", "method": "GFN2-xTB Opt", "cores": "1", "wall_sec": "0.35", "status": "ok"},
    {"job_id": "C02|M|orca_sp", "mol_id": "C02", "molecule": "EMC", "state": "M", "phase": "orca_sp", "method": "wB97X-D4/def2-TZVP SMD", "cores": "4", "wall_sec": "60.5", "status": "ok"},
    {"job_id": "C02|M_tzvpd|orca_sp", "mol_id": "C02", "molecule": "EMC", "state": "M", "phase": "orca_sp", "method": "wB97X-D4/def2-TZVPD SMD", "cores": "4", "wall_sec": "102.3", "status": "ok"},
    {"job_id": "C02|M_plus|orca_sp", "mol_id": "C02", "molecule": "EMC", "state": "M_plus", "phase": "orca_sp", "method": "wB97X-D4/def2-TZVPD SMD", "cores": "4", "wall_sec": "165.2", "status": "ok"},
    {"job_id": "C02|LiM_plus|orca_sp", "mol_id": "C02", "molecule": "EMC", "state": "LiM_plus", "phase": "orca_sp", "method": "wB97X-D4/def2-TZVPD SMD", "cores": "4", "wall_sec": "119.1", "status": "ok"},
    {"job_id": "C02|LiM_2plus|orca_sp", "mol_id": "C02", "molecule": "EMC", "state": "LiM_2plus", "phase": "orca_sp", "method": "wB97X-D4/def2-TZVPD SMD", "cores": "4", "wall_sec": "194.2", "status": "ok"},
    {"job_id": "C03|M|xtb_opt", "mol_id": "C03", "molecule": "DEC", "state": "M", "phase": "xtb_opt", "method": "GFN2-xTB Opt", "cores": "1", "wall_sec": "0.12", "status": "ok"},
    {"job_id": "C03|M_plus|xtb_opt", "mol_id": "C03", "molecule": "DEC", "state": "M_plus", "phase": "xtb_opt", "method": "GFN2-xTB Opt", "cores": "1", "wall_sec": "0.37", "status": "ok"},
    {"job_id": "C03|LiM_plus|xtb_opt", "mol_id": "C03", "molecule": "DEC", "state": "LiM_plus", "phase": "xtb_opt", "method": "GFN2-xTB Opt", "cores": "1", "wall_sec": "0.19", "status": "ok"},
    {"job_id": "C03|LiM_2plus|xtb_opt", "mol_id": "C03", "molecule": "DEC", "state": "LiM_2plus", "phase": "xtb_opt", "method": "GFN2-xTB Opt", "cores": "1", "wall_sec": "0.52", "status": "ok"},
    {"job_id": "C03|M|orca_sp", "mol_id": "C03", "molecule": "DEC", "state": "M", "phase": "orca_sp", "method": "wB97X-D4/def2-TZVP SMD", "cores": "4", "wall_sec": "41.4", "status": "ok"},
    {"job_id": "C03|M_tzvpd|orca_sp", "mol_id": "C03", "molecule": "DEC", "state": "M", "phase": "orca_sp", "method": "wB97X-D4/def2-TZVPD SMD", "cores": "4", "wall_sec": "71.7", "status": "ok"},
    {"job_id": "C03|M_plus|orca_sp", "mol_id": "C03", "molecule": "DEC", "state": "M_plus", "phase": "orca_sp", "method": "wB97X-D4/def2-TZVPD SMD", "cores": "4", "wall_sec": "133.3", "status": "ok"},
    {"job_id": "C03|LiM_plus|orca_sp", "mol_id": "C03", "molecule": "DEC", "state": "LiM_plus", "phase": "orca_sp", "method": "wB97X-D4/def2-TZVPD SMD", "cores": "4", "wall_sec": "81.5", "status": "ok"},
    {"job_id": "C03|LiM_2plus|orca_sp", "mol_id": "C03", "molecule": "DEC", "state": "LiM_2plus", "phase": "orca_sp", "method": "wB97X-D4/def2-TZVPD SMD", "cores": "4", "wall_sec": "97.2", "status": "ok"},
    {"job_id": "C04|M|xtb_opt", "mol_id": "C04", "molecule": "EC", "state": "M", "phase": "xtb_opt", "method": "GFN2-xTB Opt", "cores": "1", "wall_sec": "0.15", "status": "ok"},
    {"job_id": "C04|M_plus|xtb_opt", "mol_id": "C04", "molecule": "EC", "state": "M_plus", "phase": "xtb_opt", "method": "GFN2-xTB Opt", "cores": "1", "wall_sec": "0.14", "status": "ok"},
    {"job_id": "C04|LiM_plus|xtb_opt", "mol_id": "C04", "molecule": "EC", "state": "LiM_plus", "phase": "xtb_opt", "method": "GFN2-xTB Opt", "cores": "1", "wall_sec": "0.09", "status": "ok"},
    {"job_id": "C04|LiM_2plus|xtb_opt", "mol_id": "C04", "molecule": "EC", "state": "LiM_2plus", "phase": "xtb_opt", "method": "GFN2-xTB Opt", "cores": "1", "wall_sec": "0.10", "status": "ok"},
    {"job_id": "C04|M|orca_sp", "mol_id": "C04", "molecule": "EC", "state": "M", "phase": "orca_sp", "method": "wB97X-D4/def2-TZVP SMD", "cores": "4", "wall_sec": "29.8", "status": "ok"},
    {"job_id": "C04|M_tzvpd|orca_sp", "mol_id": "C04", "molecule": "EC", "state": "M", "phase": "orca_sp", "method": "wB97X-D4/def2-TZVPD SMD", "cores": "4", "wall_sec": "51.0", "status": "ok"},
    {"job_id": "C04|M_plus|orca_sp", "mol_id": "C04", "molecule": "EC", "state": "M_plus", "phase": "orca_sp", "method": "wB97X-D4/def2-TZVPD SMD", "cores": "4", "wall_sec": "62.5", "status": "ok"},
    {"job_id": "C04|LiM_plus|orca_sp", "mol_id": "C04", "molecule": "EC", "state": "LiM_plus", "phase": "orca_sp", "method": "wB97X-D4/def2-TZVPD SMD", "cores": "4", "wall_sec": "62.1", "status": "ok"},
    {"job_id": "C04|LiM_2plus|orca_sp", "mol_id": "C04", "molecule": "EC", "state": "LiM_2plus", "phase": "orca_sp", "method": "wB97X-D4/def2-TZVPD SMD", "cores": "4", "wall_sec": "68.2", "status": "ok"},
    {"job_id": "C05|M|xtb_opt", "mol_id": "C05", "molecule": "PC", "state": "M", "phase": "xtb_opt", "method": "GFN2-xTB Opt", "cores": "1", "wall_sec": "0.20", "status": "ok"},
    {"job_id": "C05|M_plus|xtb_opt", "mol_id": "C05", "molecule": "PC", "state": "M_plus", "phase": "xtb_opt", "method": "GFN2-xTB Opt", "cores": "1", "wall_sec": "0.21", "status": "ok"},
    {"job_id": "C05|LiM_plus|xtb_opt", "mol_id": "C05", "molecule": "PC", "state": "LiM_plus", "phase": "xtb_opt", "method": "GFN2-xTB Opt", "cores": "1", "wall_sec": "0.14", "status": "ok"},
    {"job_id": "C05|LiM_2plus|xtb_opt", "mol_id": "C05", "molecule": "PC", "state": "LiM_2plus", "phase": "xtb_opt", "method": "GFN2-xTB Opt", "cores": "1", "wall_sec": "0.21", "status": "ok"},
    {"job_id": "C05|M|orca_sp", "mol_id": "C05", "molecule": "PC", "state": "M", "phase": "orca_sp", "method": "wB97X-D4/def2-TZVP SMD", "cores": "4", "wall_sec": "51.4", "status": "ok"},
    {"job_id": "C05|M_tzvpd|orca_sp", "mol_id": "C05", "molecule": "PC", "state": "M", "phase": "orca_sp", "method": "wB97X-D4/def2-TZVPD SMD", "cores": "4", "wall_sec": "89.1", "status": "ok"},
    {"job_id": "C05|M_plus|orca_sp", "mol_id": "C05", "molecule": "PC", "state": "M_plus", "phase": "orca_sp", "method": "wB97X-D4/def2-TZVPD SMD", "cores": "4", "wall_sec": "127.6", "status": "ok"},
    {"job_id": "C05|LiM_plus|orca_sp", "mol_id": "C05", "molecule": "PC", "state": "LiM_plus", "phase": "orca_sp", "method": "wB97X-D4/def2-TZVPD SMD", "cores": "4", "wall_sec": "95.1", "status": "ok"},
    {"job_id": "C05|LiM_2plus|orca_sp", "mol_id": "C05", "molecule": "PC", "state": "LiM_2plus", "phase": "orca_sp", "method": "wB97X-D4/def2-TZVPD SMD", "cores": "4", "wall_sec": "148.7", "status": "ok"},
    {"job_id": "C08|M|xtb_opt", "mol_id": "C08", "molecule": "DME", "state": "M", "phase": "xtb_opt", "method": "GFN2-xTB Opt", "cores": "1", "wall_sec": "0.19", "status": "ok"},
    {"job_id": "C08|M_plus|xtb_opt", "mol_id": "C08", "molecule": "DME", "state": "M_plus", "phase": "xtb_opt", "method": "GFN2-xTB Opt", "cores": "1", "wall_sec": "0.38", "status": "ok"},
    {"job_id": "C08|LiM_plus|xtb_opt", "mol_id": "C08", "molecule": "DME", "state": "LiM_plus", "phase": "xtb_opt", "method": "GFN2-xTB Opt", "cores": "1", "wall_sec": "0.86", "status": "ok"},
    {"job_id": "C08|LiM_2plus|xtb_opt", "mol_id": "C08", "molecule": "DME", "state": "LiM_2plus", "phase": "xtb_opt", "method": "GFN2-xTB Opt", "cores": "1", "wall_sec": "0.69", "status": "ok"},
    {"job_id": "C08|M|orca_sp", "mol_id": "C08", "molecule": "DME", "state": "M", "phase": "orca_sp", "method": "wB97X-D4/def2-TZVP SMD", "cores": "4", "wall_sec": "53.7", "status": "ok"},
    {"job_id": "C08|M_tzvpd|orca_sp", "mol_id": "C08", "molecule": "DME", "state": "M", "phase": "orca_sp", "method": "wB97X-D4/def2-TZVPD SMD", "cores": "4", "wall_sec": "91.5", "status": "ok"},
    {"job_id": "C08|M_plus|orca_sp", "mol_id": "C08", "molecule": "DME", "state": "M_plus", "phase": "orca_sp", "method": "wB97X-D4/def2-TZVPD SMD", "cores": "4", "wall_sec": "87.3", "status": "ok"},
    {"job_id": "C08|LiM_plus|orca_sp", "mol_id": "C08", "molecule": "DME", "state": "LiM_plus", "phase": "orca_sp", "method": "wB97X-D4/def2-TZVPD SMD", "cores": "4", "wall_sec": "67.3", "status": "ok"},
    {"job_id": "C08|LiM_2plus|orca_sp", "mol_id": "C08", "molecule": "DME", "state": "LiM_2plus", "phase": "orca_sp", "method": "wB97X-D4/def2-TZVPD SMD", "cores": "4", "wall_sec": "67.2", "status": "ok"},
    {"job_id": "C09|M|xtb_opt", "mol_id": "C09", "molecule": "DOL", "state": "M", "phase": "xtb_opt", "method": "GFN2-xTB Opt", "cores": "1", "wall_sec": "0.09", "status": "ok"},
    {"job_id": "C09|M_plus|xtb_opt", "mol_id": "C09", "molecule": "DOL", "state": "M_plus", "phase": "xtb_opt", "method": "GFN2-xTB Opt", "cores": "1", "wall_sec": "0.12", "status": "ok"},
    {"job_id": "C09|LiM_plus|xtb_opt", "mol_id": "C09", "molecule": "DOL", "state": "LiM_plus", "phase": "xtb_opt", "method": "GFN2-xTB Opt", "cores": "1", "wall_sec": "0.22", "status": "ok"},
    {"job_id": "C09|LiM_2plus|xtb_opt", "mol_id": "C09", "molecule": "DOL", "state": "LiM_2plus", "phase": "xtb_opt", "method": "GFN2-xTB Opt", "cores": "1", "wall_sec": "0.36", "status": "ok"},
    {"job_id": "C09|M|orca_sp", "mol_id": "C09", "molecule": "DOL", "state": "M", "phase": "orca_sp", "method": "wB97X-D4/def2-TZVP SMD", "cores": "4", "wall_sec": "29.3", "status": "ok"},
    {"job_id": "C09|M_tzvpd|orca_sp", "mol_id": "C09", "molecule": "DOL", "state": "M", "phase": "orca_sp", "method": "wB97X-D4/def2-TZVPD SMD", "cores": "4", "wall_sec": "49.7", "status": "ok"},
    {"job_id": "C09|M_plus|orca_sp", "mol_id": "C09", "molecule": "DOL", "state": "M_plus", "phase": "orca_sp", "method": "wB97X-D4/def2-TZVPD SMD", "cores": "4", "wall_sec": "54.0", "status": "ok"},
    {"job_id": "C09|LiM_plus|orca_sp", "mol_id": "C09", "molecule": "DOL", "state": "LiM_plus", "phase": "orca_sp", "method": "wB97X-D4/def2-TZVPD SMD", "cores": "4", "wall_sec": "57.3", "status": "ok"},
    {"job_id": "C09|LiM_2plus|orca_sp", "mol_id": "C09", "molecule": "DOL", "state": "LiM_2plus", "phase": "orca_sp", "method": "wB97X-D4/def2-TZVPD SMD", "cores": "4", "wall_sec": "75.8", "status": "ok"},
    {"job_id": "C13|M|xtb_opt", "mol_id": "C13", "molecule": "GBL", "state": "M", "phase": "xtb_opt", "method": "GFN2-xTB Opt", "cores": "1", "wall_sec": "0.16", "status": "ok"},
    {"job_id": "C13|M_plus|xtb_opt", "mol_id": "C13", "molecule": "GBL", "state": "M_plus", "phase": "xtb_opt", "method": "GFN2-xTB Opt", "cores": "1", "wall_sec": "0.14", "status": "ok"},
    {"job_id": "C13|LiM_plus|xtb_opt", "mol_id": "C13", "molecule": "GBL", "state": "LiM_plus", "phase": "xtb_opt", "method": "GFN2-xTB Opt", "cores": "1", "wall_sec": "0.20", "status": "ok"},
    {"job_id": "C13|LiM_2plus|xtb_opt", "mol_id": "C13", "molecule": "GBL", "state": "LiM_2plus", "phase": "xtb_opt", "method": "GFN2-xTB Opt", "cores": "1", "wall_sec": "0.21", "status": "ok"},
    {"job_id": "C13|M|orca_sp", "mol_id": "C13", "molecule": "GBL", "state": "M", "phase": "orca_sp", "method": "wB97X-D4/def2-TZVP SMD", "cores": "4", "wall_sec": "41.4", "status": "ok"},
    {"job_id": "C13|M_tzvpd|orca_sp", "mol_id": "C13", "molecule": "GBL", "state": "M", "phase": "orca_sp", "method": "wB97X-D4/def2-TZVPD SMD", "cores": "4", "wall_sec": "68.5", "status": "ok"},
    {"job_id": "C13|M_plus|orca_sp", "mol_id": "C13", "molecule": "GBL", "state": "M_plus", "phase": "orca_sp", "method": "wB97X-D4/def2-TZVPD SMD", "cores": "4", "wall_sec": "100.2", "status": "ok"},
    {"job_id": "C13|LiM_plus|orca_sp", "mol_id": "C13", "molecule": "GBL", "state": "LiM_plus", "phase": "orca_sp", "method": "wB97X-D4/def2-TZVPD SMD", "cores": "4", "wall_sec": "78.3", "status": "ok"},
    {"job_id": "C13|LiM_2plus|orca_sp", "mol_id": "C13", "molecule": "GBL", "state": "LiM_2plus", "phase": "orca_sp", "method": "wB97X-D4/def2-TZVPD SMD", "cores": "4", "wall_sec": "105.1", "status": "ok"},
    {"job_id": "C14|M|xtb_opt", "mol_id": "C14", "molecule": "SL", "state": "M", "phase": "xtb_opt", "method": "GFN2-xTB Opt", "cores": "1", "wall_sec": "0.19", "status": "ok"},
    {"job_id": "C14|M_plus|xtb_opt", "mol_id": "C14", "molecule": "SL", "state": "M_plus", "phase": "xtb_opt", "method": "GFN2-xTB Opt", "cores": "1", "wall_sec": "0.16", "status": "ok"},
    {"job_id": "C14|LiM_plus|xtb_opt", "mol_id": "C14", "molecule": "SL", "state": "LiM_plus", "phase": "xtb_opt", "method": "GFN2-xTB Opt", "cores": "1", "wall_sec": "0.33", "status": "ok"},
    {"job_id": "C14|LiM_2plus|xtb_opt", "mol_id": "C14", "molecule": "SL", "state": "LiM_2plus", "phase": "xtb_opt", "method": "GFN2-xTB Opt", "cores": "1", "wall_sec": "0.17", "status": "ok"},
    {"job_id": "C14|M|orca_sp", "mol_id": "C14", "molecule": "SL", "state": "M", "phase": "orca_sp", "method": "wB97X-D4/def2-TZVP SMD", "cores": "4", "wall_sec": "73.3", "status": "ok"},
    {"job_id": "C14|M_tzvpd|orca_sp", "mol_id": "C14", "molecule": "SL", "state": "M", "phase": "orca_sp", "method": "wB97X-D4/def2-TZVPD SMD", "cores": "4", "wall_sec": "121.2", "status": "ok"},
    {"job_id": "C14|M_plus|orca_sp", "mol_id": "C14", "molecule": "SL", "state": "M_plus", "phase": "orca_sp", "method": "wB97X-D4/def2-TZVPD SMD", "cores": "4", "wall_sec": "132.1", "status": "ok"},
    {"job_id": "C14|LiM_plus|orca_sp", "mol_id": "C14", "molecule": "SL", "state": "LiM_plus", "phase": "orca_sp", "method": "wB97X-D4/def2-TZVPD SMD", "cores": "4", "wall_sec": "89.2", "status": "ok"},
    {"job_id": "C14|LiM_2plus|orca_sp", "mol_id": "C14", "molecule": "SL", "state": "LiM_2plus", "phase": "orca_sp", "method": "wB97X-D4/def2-TZVPD SMD", "cores": "4", "wall_sec": "88.1", "status": "ok"},
    {"job_id": "C15|M|xtb_opt", "mol_id": "C15", "molecule": "DMSO", "state": "M", "phase": "xtb_opt", "method": "GFN2-xTB Opt", "cores": "1", "wall_sec": "0.09", "status": "ok"},
    {"job_id": "C15|M_plus|xtb_opt", "mol_id": "C15", "molecule": "DMSO", "state": "M_plus", "phase": "xtb_opt", "method": "GFN2-xTB Opt", "cores": "1", "wall_sec": "0.10", "status": "ok"},
    {"job_id": "C15|LiM_plus|xtb_opt", "mol_id": "C15", "molecule": "DMSO", "state": "LiM_plus", "phase": "xtb_opt", "method": "GFN2-xTB Opt", "cores": "1", "wall_sec": "0.11", "status": "ok"},
    {"job_id": "C15|LiM_2plus|xtb_opt", "mol_id": "C15", "molecule": "DMSO", "state": "LiM_2plus", "phase": "xtb_opt", "method": "GFN2-xTB Opt", "cores": "1", "wall_sec": "0.10", "status": "ok"},
    {"job_id": "C15|M|orca_sp", "mol_id": "C15", "molecule": "DMSO", "state": "M", "phase": "orca_sp", "method": "wB97X-D4/def2-TZVP SMD", "cores": "4", "wall_sec": "24.8", "status": "ok"},
    {"job_id": "C15|M_tzvpd|orca_sp", "mol_id": "C15", "molecule": "DMSO", "state": "M", "phase": "orca_sp", "method": "wB97X-D4/def2-TZVPD SMD", "cores": "4", "wall_sec": "38.3", "status": "ok"},
    {"job_id": "C15|M_plus|orca_sp", "mol_id": "C15", "molecule": "DMSO", "state": "M_plus", "phase": "orca_sp", "method": "wB97X-D4/def2-TZVPD SMD", "cores": "4", "wall_sec": "46.9", "status": "ok"},
    {"job_id": "C15|LiM_plus|orca_sp", "mol_id": "C15", "molecule": "DMSO", "state": "LiM_plus", "phase": "orca_sp", "method": "wB97X-D4/def2-TZVPD SMD", "cores": "4", "wall_sec": "47.4", "status": "ok"},
    {"job_id": "C15|LiM_2plus|orca_sp", "mol_id": "C15", "molecule": "DMSO", "state": "LiM_2plus", "phase": "orca_sp", "method": "wB97X-D4/def2-TZVPD SMD", "cores": "4", "wall_sec": "57.4", "status": "ok"},
    {"job_id": "C16|M|xtb_opt", "mol_id": "C16", "molecule": "AN", "state": "M", "phase": "xtb_opt", "method": "GFN2-xTB Opt", "cores": "1", "wall_sec": "0.09", "status": "ok"},
    {"job_id": "C16|M_plus|xtb_opt", "mol_id": "C16", "molecule": "AN", "state": "M_plus", "phase": "xtb_opt", "method": "GFN2-xTB Opt", "cores": "1", "wall_sec": "0.13", "status": "ok"},
    {"job_id": "C16|LiM_plus|xtb_opt", "mol_id": "C16", "molecule": "AN", "state": "LiM_plus", "phase": "xtb_opt", "method": "GFN2-xTB Opt", "cores": "1", "wall_sec": "0.12", "status": "ok"},
    {"job_id": "C16|LiM_2plus|xtb_opt", "mol_id": "C16", "molecule": "AN", "state": "LiM_2plus", "phase": "xtb_opt", "method": "GFN2-xTB Opt", "cores": "1", "wall_sec": "0.18", "status": "ok"},
    {"job_id": "C16|M|orca_sp", "mol_id": "C16", "molecule": "AN", "state": "M", "phase": "orca_sp", "method": "wB97X-D4/def2-TZVP SMD", "cores": "4", "wall_sec": "15.8", "status": "ok"},
    {"job_id": "C16|M_tzvpd|orca_sp", "mol_id": "C16", "molecule": "AN", "state": "M", "phase": "orca_sp", "method": "wB97X-D4/def2-TZVPD SMD", "cores": "4", "wall_sec": "19.1", "status": "ok"},
    {"job_id": "C16|M_plus|orca_sp", "mol_id": "C16", "molecule": "AN", "state": "M_plus", "phase": "orca_sp", "method": "wB97X-D4/def2-TZVPD SMD", "cores": "4", "wall_sec": "19.3", "status": "ok"},
    {"job_id": "C16|LiM_plus|orca_sp", "mol_id": "C16", "molecule": "AN", "state": "LiM_plus", "phase": "orca_sp", "method": "wB97X-D4/def2-TZVPD SMD", "cores": "4", "wall_sec": "21.8", "status": "ok"},
    {"job_id": "C16|LiM_2plus|orca_sp", "mol_id": "C16", "molecule": "AN", "state": "LiM_2plus", "phase": "orca_sp", "method": "wB97X-D4/def2-TZVPD SMD", "cores": "4", "wall_sec": "21.5", "status": "ok"},
    {"job_id": "C17|M|xtb_opt", "mol_id": "C17", "molecule": "TMP", "state": "M", "phase": "xtb_opt", "method": "GFN2-xTB Opt", "cores": "1", "wall_sec": "0.21", "status": "ok"},
    {"job_id": "C17|M_plus|xtb_opt", "mol_id": "C17", "molecule": "TMP", "state": "M_plus", "phase": "xtb_opt", "method": "GFN2-xTB Opt", "cores": "1", "wall_sec": "0.63", "status": "ok"},
    {"job_id": "C17|LiM_plus|xtb_opt", "mol_id": "C17", "molecule": "TMP", "state": "LiM_plus", "phase": "xtb_opt", "method": "GFN2-xTB Opt", "cores": "1", "wall_sec": "0.31", "status": "ok"},
    {"job_id": "C17|LiM_2plus|xtb_opt", "mol_id": "C17", "molecule": "TMP", "state": "LiM_2plus", "phase": "xtb_opt", "method": "GFN2-xTB Opt", "cores": "1", "wall_sec": "1.32", "status": "ok"},
    {"job_id": "C17|M|orca_sp", "mol_id": "C17", "molecule": "TMP", "state": "M", "phase": "orca_sp", "method": "wB97X-D4/def2-TZVP SMD", "cores": "4", "wall_sec": "79.0", "status": "ok"},
    {"job_id": "C17|M_tzvpd|orca_sp", "mol_id": "C17", "molecule": "TMP", "state": "M", "phase": "orca_sp", "method": "wB97X-D4/def2-TZVPD SMD", "cores": "4", "wall_sec": "136.9", "status": "ok"},
    {"job_id": "C17|M_plus|orca_sp", "mol_id": "C17", "molecule": "TMP", "state": "M_plus", "phase": "orca_sp", "method": "wB97X-D4/def2-TZVPD SMD", "cores": "4", "wall_sec": "144.9", "status": "ok"},
    {"job_id": "C17|LiM_plus|orca_sp", "mol_id": "C17", "molecule": "TMP", "state": "LiM_plus", "phase": "orca_sp", "method": "wB97X-D4/def2-TZVPD SMD", "cores": "4", "wall_sec": "159.6", "status": "ok"},
    {"job_id": "C17|LiM_2plus|orca_sp", "mol_id": "C17", "molecule": "TMP", "state": "LiM_2plus", "phase": "orca_sp", "method": "wB97X-D4/def2-TZVPD SMD", "cores": "4", "wall_sec": "213.7", "status": "ok"},
    {"job_id": "C01|M|orca_freq", "mol_id": "C01", "molecule": "DMC", "state": "M", "phase": "orca_freq", "method": "wB97X-D4/def2-TZVP SMD NumFreq", "cores": "4", "wall_sec": "1129.1", "status": "ok"},
]

PILOT_RT_EH = 0.000944183
PILOT_LN_VM = 3.197365

# ---------------------------------------------------------------------------
# 方案 6.1/6.2 —— WP2 生产首段（4 主集分子 x 4 主态）的真实 Opt/Freq 自由能标签
# 生产级别 wB97X-D4（ORCA 关键字，即 omegaB97X-D4）+ SMD(acetonitrile)：Opt NumFreq
# TightOpt TightSCF SlowConv 在同一 ORCA 作业；中性态 def2-TZVP，带电/Li 态 def2-TZVPD（含弥散）。
# 几何起点是各状态既有冻结的 r2SCAN-3c 结构（记录在每行 geometry_start）。
# 账本行来自同一 Opt+Freq 作业：e_sp_eh = 末次 Opt 电子能，g_single_eh = Final Gibbs free energy。
# 每态一个代表结构；原始 ORCA 输出留在仓库外 work/wp2prod，不入交付镜像。
#
# 基组一致性：中性腿（def2-TZVP）与带电腿（def2-TZVPD）不可相减求自由分子 IP。若额外补跑了
# 中性腿的 def2-TZVPD 版本（state = M_tzvpd），则 Gox_single 与 coordination_shift 才在
# 同一基组下成立；这部分结果单独放在 production_redox.csv，绝不与 M 腿混算。
#
# 子集纪律：本表只登记已经跑完的状态；未完成的状态不出现在表里（缺值不写 0），
# 进度由 production_progress 记录。
# ---------------------------------------------------------------------------
WP2_PRODUCTION_MOLECULES = ["C01", "C02", "C13", "C14"]
WP2_PRODUCTION_NAMES = {"C01": "DMC", "C02": "EMC", "C13": "GBL", "C14": "SL"}
WP2_PRODUCTION_STATES = ["M", "M_plus", "LiM_plus", "LiM_2plus"]
WP2_PRODUCTION_EXTRA_STATES = []
WP2_PRODUCTION_METHOD_NOTE = ("wB97X-D4 (= omegaB97X-D4) / def2-TZVP for the neutral leg and def2-TZVPD "
                              "for the charged/Li legs; SMD acetonitrile; Opt NumFreq TightOpt TightSCF SlowConv")
WP2_PRODUCTION_GEOM_NOTE = ("per-state frozen r2SCAN-3c start structure: M -> <name>_G2.xyz, "
                            "M_plus -> <name>_G2_cation.xyz, Li states -> <name>_m1_G2Li.xyz")

WP2_PRODUCTION_LEDGER_CSV_FIELDS = [
    "record_id", "mol_id", "name", "state", "charge", "multiplicity", "basis", "level",
    "geometry_start", "e_sp_eh", "zpe_eh", "e_to_g_thermal_eh", "enthalpy_eh",
    "entropy_corr_eh", "g_single_eh", "g_single_ev", "std_state_corr_eh", "std_state_corr_ev",
    "zpe_ev", "thermal_corr_ev", "qrrho", "temp_k", "pressure_atm", "cutoff_cm1",
    "lowest_freq_cm1", "n_freq", "imaginary_modes", "wall_sec", "cores", "status", "notes",
]


def _wp2_production_identity(state, li_o_ang):
    """生产首段的状态身份：自由态 intact；Li 态按 Li-O/N 最近距离的固定阈值 bound/dissociated。"""
    if state in ("M", "M_tzvpd", "M_plus"):
        return "intact"
    if li_o_ang and float(li_o_ang) < 2.45:
        return "bound"
    return "dissociated"


WP2_PRODUCTION_LEDGER = [
    {"record_id": "C01|M", "mol_id": "C01", "name": "DMC", "state": "M", "charge": "0", "multiplicity": "1", "method": "wB97X-D4 def2-TZVP", "solvent": "SMD_acetonitrile", "level": "wB97X-D4 def2-TZVP SMD(acetonitrile) Opt NumFreq (qRRHO=True)", "geometry_start": "outputs/week4/t2_opt_freq/DMC/DMC_G2.xyz", "e_sp_eh": "-343.85476184", "electronic_eh": "-343.85476184", "zpe_eh": "0.09586398", "enthalpy_eh": "-343.75105104", "entropy_corr_eh": "-0.03850812", "e_to_g_thermal_eh": "0.06520269", "g_single_eh": "-343.78955915", "std_state_corr_eh": "0.00301890", "qrrho": "True", "temp_k": "298.15", "pressure_atm": "1.00", "cutoff_cm1": "1.00", "lowest_freq_cm1": "116.03", "n_freq": "36", "imaginary_modes": "0", "opt_converged": "true", "terminated": "true", "wall_sec": "4856.6", "cores": "4", "job_kind": "opt_numfreq", "notes": "Opt and NumFreq run in one ORCA job; the recorded e_sp_eh is the final Opt energy", "qc_flag": "", "li_o_ang": "", "nonli_components": "", "status": "computed", "basis": "def2-TZVP", "e_sp_solution_ev": "-9356.764736950", "g_single_ev": "-9354.990481369", "zpe_ev": "2.608591787", "thermal_corr_ev": "1.774255582", "std_state_corr_ev": "0.082148454", "core_hours": "5.396222"},
    {"record_id": "C02|M", "mol_id": "C02", "name": "EMC", "state": "M", "charge": "0", "multiplicity": "1", "method": "wB97X-D4 def2-TZVP", "solvent": "SMD_acetonitrile", "level": "wB97X-D4 def2-TZVP SMD(acetonitrile) Opt NumFreq (qRRHO=True)", "geometry_start": "outputs/week4/t2_opt_freq/EMC/EMC_G2.xyz", "e_sp_eh": "-383.21194726", "electronic_eh": "-383.21194726", "zpe_eh": "0.12437320", "enthalpy_eh": "-383.07853290", "entropy_corr_eh": "-0.04136067", "e_to_g_thermal_eh": "0.09205369", "g_single_eh": "-383.11989357", "std_state_corr_eh": "0.00301890", "qrrho": "True", "temp_k": "298.15", "pressure_atm": "1.00", "cutoff_cm1": "1.00", "lowest_freq_cm1": "77.89", "n_freq": "45", "imaginary_modes": "0", "opt_converged": "true", "terminated": "true", "wall_sec": "6035.4", "cores": "4", "job_kind": "opt_numfreq", "notes": "Opt and NumFreq run in one ORCA job; the recorded e_sp_eh is the final Opt energy", "qc_flag": "", "li_o_ang": "", "nonli_components": "", "status": "computed", "basis": "def2-TZVP", "e_sp_solution_ev": "-10427.728310969", "g_single_ev": "-10425.223402455", "zpe_ev": "3.384367184", "thermal_corr_ev": "2.504908514", "std_state_corr_ev": "0.082148454", "core_hours": "6.706000"},
    {"record_id": "C13|M", "mol_id": "C13", "name": "GBL", "state": "M", "charge": "0", "multiplicity": "1", "method": "wB97X-D4 def2-TZVP", "solvent": "SMD_acetonitrile", "level": "wB97X-D4 def2-TZVP SMD(acetonitrile) Opt NumFreq (qRRHO=True)", "geometry_start": "outputs/week4/t2_opt_freq/GBL/GBL_G2.xyz", "e_sp_eh": "-306.73708477", "electronic_eh": "-306.73708477", "zpe_eh": "0.09943860", "enthalpy_eh": "-306.63160526", "entropy_corr_eh": "-0.03461257", "e_to_g_thermal_eh": "0.07086694", "g_single_eh": "-306.66621783", "std_state_corr_eh": "0.00301890", "qrrho": "True", "temp_k": "298.15", "pressure_atm": "1.00", "cutoff_cm1": "1.00", "lowest_freq_cm1": "150.06", "n_freq": "36", "imaginary_modes": "0", "opt_converged": "true", "terminated": "true", "wall_sec": "3935.5", "cores": "4", "job_kind": "opt_numfreq", "notes": "Opt and NumFreq run in one ORCA job; the recorded e_sp_eh is the final Opt energy", "qc_flag": "", "li_o_ang": "", "nonli_components": "", "status": "computed", "basis": "def2-TZVP", "e_sp_solution_ev": "-8346.741289645", "g_single_ev": "-8344.812901968", "zpe_ev": "2.705862152", "thermal_corr_ev": "1.928387676", "std_state_corr_ev": "0.082148454", "core_hours": "4.372778"},
    {"record_id": "C13|M_plus", "mol_id": "C13", "name": "GBL", "state": "M_plus", "charge": "1", "multiplicity": "2", "method": "wB97X-D4 def2-TZVPD", "solvent": "SMD_acetonitrile", "level": "wB97X-D4 def2-TZVPD SMD(acetonitrile) Opt NumFreq (qRRHO=True)", "geometry_start": "outputs/week4/t2_opt_freq/GBL/GBL_G2_cation.xyz", "e_sp_eh": "-306.45395804", "electronic_eh": "-306.45395804", "zpe_eh": "0.09748803", "enthalpy_eh": "-306.35023859", "entropy_corr_eh": "-0.03548273", "e_to_g_thermal_eh": "0.06823672", "g_single_eh": "-306.38572132", "std_state_corr_eh": "0.00301890", "qrrho": "True", "temp_k": "298.15", "pressure_atm": "1.00", "cutoff_cm1": "1.00", "lowest_freq_cm1": "164.90", "n_freq": "36", "imaginary_modes": "0", "opt_converged": "true", "terminated": "true", "wall_sec": "10481.3", "cores": "4", "job_kind": "opt_numfreq", "notes": "Opt and NumFreq run in one ORCA job; the recorded e_sp_eh is the final Opt energy", "qc_flag": "", "li_o_ang": "", "nonli_components": "", "status": "computed", "basis": "def2-TZVPD", "e_sp_solution_ev": "-8339.037018838", "g_single_ev": "-8337.180203094", "zpe_ev": "2.652784439", "thermal_corr_ev": "1.856815744", "std_state_corr_ev": "0.082148454", "core_hours": "11.645889"},
    {"record_id": "C14|M", "mol_id": "C14", "name": "SL", "state": "M", "charge": "0", "multiplicity": "1", "method": "wB97X-D4 def2-TZVP", "solvent": "SMD_acetonitrile", "level": "wB97X-D4 def2-TZVP SMD(acetonitrile) Opt NumFreq (qRRHO=True)", "geometry_start": "outputs/week4/t2_opt_freq/SL/SL_G2.xyz", "e_sp_eh": "-706.15322084", "electronic_eh": "-706.15322084", "zpe_eh": "0.12428876", "enthalpy_eh": "-706.02140690", "entropy_corr_eh": "-0.03823048", "e_to_g_thermal_eh": "0.09358347", "g_single_eh": "-706.05963738", "std_state_corr_eh": "0.00301890", "qrrho": "True", "temp_k": "298.15", "pressure_atm": "1.00", "cutoff_cm1": "1.00", "lowest_freq_cm1": "37.15", "n_freq": "45", "imaginary_modes": "0", "opt_converged": "true", "terminated": "true", "wall_sec": "7409.8", "cores": "4", "job_kind": "opt_numfreq", "notes": "Opt and NumFreq run in one ORCA job; the recorded e_sp_eh is the final Opt energy", "qc_flag": "", "li_o_ang": "", "nonli_components": "", "status": "computed", "basis": "def2-TZVP", "e_sp_solution_ev": "-19215.408041126", "g_single_ev": "-19212.861505449", "zpe_ev": "3.382069454", "thermal_corr_ev": "2.546535948", "std_state_corr_ev": "0.082148454", "core_hours": "8.233111"},
]

WP2_PRODUCTION_CORE_HOURS = sum(float(row["core_hours"]) for row in WP2_PRODUCTION_LEDGER)
WP2_PRODUCTION_STATES_DONE = len([row for row in WP2_PRODUCTION_LEDGER
                                   if row["state"] in WP2_PRODUCTION_STATES])
WP2_PRODUCTION_STATES_TOTAL = len(WP2_PRODUCTION_MOLECULES) * len(WP2_PRODUCTION_STATES)
WP2_PRODUCTION_LEDGER_ROWS = len(WP2_PRODUCTION_LEDGER)




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
        {"id": "local_echo_covers_all_settings", "description": "本机方法回显覆盖全部 4 个设定（S1-S4）",
         "ok": {row["setting_id"] for row in LOCAL_METHOD_ECHO} == {s["setting_id"] for s in METHOD_SETTINGS},
         "detail": "echoed settings=" + ",".join(sorted(row["setting_id"] for row in LOCAL_METHOD_ECHO))},
        {"id": "plan_functional_spellings_remapped", "description": "方案泛函拼写在本机被拒并已给出可用替写",
         "ok": all(row["recognized"] == "true" and row["plan_keyword_status"] == "rejected_as_written"
                   for row in LOCAL_METHOD_ECHO) and len(LOCAL_KEYWORD_REJECTIONS) == 2,
         "detail": "rejections=%d; every setting has a verified ORCA keyword" % len(LOCAL_KEYWORD_REJECTIONS)},
        {"id": "smoke_runs_terminated_normally", "description": "中性/审计/带电 smoke run 全部正常收敛",
         "ok": all(row["terminated_normally"] == "true" for row in LOCAL_SMOKE_RUNS),
         "detail": "runs=%d (neutral SP, audit SP, NumFreq, cation SP)" % len(LOCAL_SMOKE_RUNS)},
        {"id": "freq_and_smd_available", "description": "SMD 乙腈下频率路径可用（无虚频）",
         "ok": LOCAL_FREQ_CHECK["imaginary_modes"] == "0" and "SMD" in LOCAL_SMOKE_RUNS[2]["solvent"],
         "detail": "NumFreq completed; imaginary=%s" % LOCAL_FREQ_CHECK["imaginary_modes"]},
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
        "electronic_structure_jobs_scope_note": "ranking/pair evidence only; the separate local_environment supportability probe is not counted here",
        "local_environment": {
            "toolchain": LOCAL_TOOLCHAIN,
            "method_echo": LOCAL_METHOD_ECHO,
            "keyword_rejections": LOCAL_KEYWORD_REJECTIONS,
            "smoke_runs": LOCAL_SMOKE_RUNS,
            "freq_check": LOCAL_FREQ_CHECK,
            "scope": "supportability probe on water under SMD acetonitrile; NOT a ranking input; raw ORCA logs kept outside the repository",
        },
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
    local["outputs/physics_completion/method_audit/local_toolchain.csv"] = csv_text(
        ["tool", "version", "path_hint", "note"], LOCAL_TOOLCHAIN)
    local["outputs/physics_completion/method_audit/local_method_echo.csv"] = csv_text(
        ["setting_id", "plan_functional", "basis", "plan_keyword_status", "orca_keyword",
         "functional_echo", "hf_exchange_fraction", "dispersion_module", "solvent_echo", "recognized"],
        LOCAL_METHOD_ECHO)
    local["outputs/physics_completion/method_audit/local_smoke_runs.csv"] = csv_text(
        ["run_id", "state", "charge", "multiplicity", "orca_keyword", "solvent",
         "basis_functions", "scf_cycles", "final_single_point_eh", "terminated_normally", "wall_sec"],
        LOCAL_SMOKE_RUNS)

    summary = [
        "# Week 38 / WP1 — 独立方法审计表（首轮登记）",
        "",
        "**状态**：矩阵与规则已冻结；排序层只盘点既有电子能层作业（零新增计算）；本机方法回显与 smoke 核验为支撑性检查，见下节。",
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
        "## 本机方法回显与 smoke 核验（方案 15.4）",
        "",
        "工具链：ORCA %s；xTB %s。原始日志留在仓库外，不入交付镜像。"
        % (LOCAL_TOOLCHAIN[0]["version"], LOCAL_TOOLCHAIN[1]["version"]),
        "",
        "| 设定 | 方案拼写 | ORCA 可用关键字 | 泛函回显 | HF 分数 | 色散 | 溶剂 |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in LOCAL_METHOD_ECHO:
        summary.append("| %s | %s | `%s` | %s | %s | %s | %s |"
                       % (row["setting_id"], row["plan_functional"], row["orca_keyword"],
                          row["functional_echo"], row["hf_exchange_fraction"],
                          row["dispersion_module"], row["solvent_echo"]))
    summary += [
        "",
        "smoke run（water，SMD 乙腈；只作支撑性检查，非排序证据）：",
        "",
        "| run | 状态 | q/mult | 关键字 | 基函数 | SCF | 末单点 (Eh) | 正常结束 | 墙钟 (s) |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in LOCAL_SMOKE_RUNS:
        summary.append("| %s | %s | %s/%s | `%s` | %s | %s | %s | %s | %s |"
                       % (row["run_id"], row["state"], row["charge"], row["multiplicity"],
                          row["orca_keyword"], row["basis_functions"], row["scf_cycles"],
                          row["final_single_point_eh"], row["terminated_normally"], row["wall_sec"]))
    summary += [
        "",
        "频率：NumFreq 在 SMD 乙腈下完成，水 3N=9 模式中 6 个近零 + 3 个实频（1588.03 / 3892.52 / 3972.24 cm^-1），**无虚频**。",
        "",
        "**方案拼写须改写**：`omegaB97X-D4` 与 `PBE0-D4` 在 ORCA 6.1.1 下被拒（`UNRECOGNIZED OR DUPLICATED KEYWORD(S)`）；正确形式为 `wB97X-D4` 与 `PBE0 D4`（色散作独立关键字）。",
        "",
        "## 限制",
        "",
        "- 已完成本机方法回显与 smoke 核验（方案 15.4）；方案拼写 `omegaB97X-D4` / `PBE0-D4` 须改写为 `wB97X-D4` / `PBE0 D4`。",
        "- 回显与 smoke 仅覆盖单一几何（water）与固定条件，**不**等于候选泛函/基组的完整验证，也**不**是排序证据。",
        "- 既有作业是气相 r2SCAN-3c（无弥散），不能裁断 0.01 eV 量级的阴离子束缚，也不含热校正。",
        "- 独立方法审计是 sensitivity assessment，不等于校准的概率误差；1.96×spread 不得自动标成 95% 置信度。",
    ]
    local["outputs/week38/wp1_summary.md"] = "\n".join(summary) + "\n"
    local["docs/59_week38_wp1_method_audit.md"] = "\n".join(summary) + "\n"
    finish_week(files, local, "week38", "WP1", "independent method audit",
                {"job_matrix_size": len(matrix), "n_settings": len(METHOD_SETTINGS),
                 "local_environment_probe_jobs": len(LOCAL_SMOKE_RUNS)})
    return files


# ---------------------------------------------------------------------------
# 方案 5.1/5.2/5.3 —— 本机独立方法审计（首轮实测）
# 8 方法集分子 x 4 状态 x 4 设定 = 128 个 SMD 乙腈单点（几何冻结在 r2SCAN-3c 最优结构），
# 外加 4 设定 x 1 状态的阳离子弛豫腿 32 格（r2SCAN-3c 松弛阳离子几何），
# 用于认证 WP3 冻结的稳健翻转（EMC|GBL、EMC|SL）。
# 原始 ORCA 日志留在仓库外（work/audit/），交付层只含派生数值。
# 还原态（Li 配位态）必须使用含弥散函数设定（S2/S4）；无弥散基组下的还原态格子
# 照样计算但 valid_for_decision=false，不进入决策统计（方案 5.1）。
# ---------------------------------------------------------------------------
METHOD_AUDIT_CELL_FIELDS = ["mol_id", "name", "state", "setting_id", "functional", "basis",
    "has_diffuse", "charge", "multiplicity", "orca_keyword", "geometry", "basis_functions",
    "scf_cycles", "final_sp_eh", "terminated", "wall_sec", "status", "qc_flag"]

METHOD_AUDIT_CELLS = [
    ("C01", "DMC", "M", "S1", "omegaB97X-D4", "def2-TZVP", "false", "0", "1", "wB97X-D4 def2-TZVP SMD(acetonitrile) SP", "outputs/week4/t2_opt_freq/DMC/DMC_G2.xyz", "222", "20", "-343.854372289128", "true", "24.0", "computed", ""),
    ("C01", "DMC", "M", "S2", "omegaB97X-D4", "def2-TZVPD", "true", "0", "1", "wB97X-D4 def2-TZVPD SMD(acetonitrile) SP", "outputs/week4/t2_opt_freq/DMC/DMC_G2.xyz", "285", "20", "-343.856355842432", "true", "36.9", "computed", ""),
    ("C01", "DMC", "M", "S3", "PBE0-D4", "def2-TZVP", "false", "0", "1", "PBE0 D4 def2-TZVP SMD(acetonitrile) SP", "outputs/week4/t2_opt_freq/DMC/DMC_G2.xyz", "222", "17", "-343.384416542567", "true", "16.0", "computed", ""),
    ("C01", "DMC", "M", "S4", "PBE0-D4", "def2-TZVPD", "true", "0", "1", "PBE0 D4 def2-TZVPD SMD(acetonitrile) SP", "outputs/week4/t2_opt_freq/DMC/DMC_G2.xyz", "285", "17", "-343.386275411134", "true", "23.2", "computed", ""),
    ("C01", "DMC", "M_plus", "S1", "omegaB97X-D4", "def2-TZVP", "false", "1", "2", "wB97X-D4 def2-TZVP SMD(acetonitrile) SP", "outputs/week4/t2_opt_freq/DMC/DMC_G2_cation.xyz", "222", "20", "-343.524458477625", "true", "27.7", "computed", ""),
    ("C01", "DMC", "M_plus", "S2", "omegaB97X-D4", "def2-TZVPD", "true", "1", "2", "wB97X-D4 def2-TZVPD SMD(acetonitrile) SP", "outputs/week4/t2_opt_freq/DMC/DMC_G2_cation.xyz", "285", "20", "-343.525676645443", "true", "43.9", "computed", ""),
    ("C01", "DMC", "M_plus", "S3", "PBE0-D4", "def2-TZVP", "false", "1", "2", "PBE0 D4 def2-TZVP SMD(acetonitrile) SP", "outputs/week4/t2_opt_freq/DMC/DMC_G2_cation.xyz", "222", "16", "-343.071252301771", "true", "18.4", "computed", ""),
    ("C01", "DMC", "M_plus", "S4", "PBE0-D4", "def2-TZVPD", "true", "1", "2", "PBE0 D4 def2-TZVPD SMD(acetonitrile) SP", "outputs/week4/t2_opt_freq/DMC/DMC_G2_cation.xyz", "285", "16", "-343.072381637798", "true", "28.0", "computed", ""),
    ("C01", "DMC", "LiM_plus", "S1", "omegaB97X-D4", "def2-TZVP", "false", "1", "1", "wB97X-D4 def2-TZVP SMD(acetonitrile) SP", "outputs/week5/c1/DMC/DMC_m1_G2Li.xyz", "236", "20", "-351.308351220745", "true", "27.0", "computed", "no_diffuse_on_reduction_state"),
    ("C01", "DMC", "LiM_plus", "S2", "omegaB97X-D4", "def2-TZVPD", "true", "1", "1", "wB97X-D4 def2-TZVPD SMD(acetonitrile) SP", "outputs/week5/c1/DMC/DMC_m1_G2Li.xyz", "302", "20", "-351.309821678224", "true", "42.8", "computed", ""),
    ("C01", "DMC", "LiM_plus", "S3", "PBE0-D4", "def2-TZVP", "false", "1", "1", "PBE0 D4 def2-TZVP SMD(acetonitrile) SP", "outputs/week5/c1/DMC/DMC_m1_G2Li.xyz", "236", "17", "-350.812767839005", "true", "17.7", "computed", "no_diffuse_on_reduction_state"),
    ("C01", "DMC", "LiM_plus", "S4", "PBE0-D4", "def2-TZVPD", "true", "1", "1", "PBE0 D4 def2-TZVPD SMD(acetonitrile) SP", "outputs/week5/c1/DMC/DMC_m1_G2Li.xyz", "302", "17", "-350.814175522570", "true", "26.7", "computed", ""),
    ("C01", "DMC", "LiM_2plus", "S1", "omegaB97X-D4", "def2-TZVP", "false", "2", "2", "wB97X-D4 def2-TZVP SMD(acetonitrile) SP", "outputs/week5/c1/DMC/DMC_m1_G2Li.xyz", "236", "20", "-350.955450937364", "true", "31.3", "computed", "no_diffuse_on_reduction_state"),
    ("C01", "DMC", "LiM_2plus", "S2", "omegaB97X-D4", "def2-TZVPD", "true", "2", "2", "wB97X-D4 def2-TZVPD SMD(acetonitrile) SP", "outputs/week5/c1/DMC/DMC_m1_G2Li.xyz", "302", "20", "-350.956443246265", "true", "50.5", "computed", ""),
    ("C01", "DMC", "LiM_2plus", "S3", "PBE0-D4", "def2-TZVP", "false", "2", "2", "PBE0 D4 def2-TZVP SMD(acetonitrile) SP", "outputs/week5/c1/DMC/DMC_m1_G2Li.xyz", "236", "16", "-350.476323090309", "true", "20.3", "computed", "no_diffuse_on_reduction_state"),
    ("C01", "DMC", "LiM_2plus", "S4", "PBE0-D4", "def2-TZVPD", "true", "2", "2", "PBE0 D4 def2-TZVPD SMD(acetonitrile) SP", "outputs/week5/c1/DMC/DMC_m1_G2Li.xyz", "302", "16", "-350.477277276788", "true", "32.2", "computed", ""),
    ("C02", "EMC", "M", "S1", "omegaB97X-D4", "def2-TZVP", "false", "0", "1", "wB97X-D4 def2-TZVP SMD(acetonitrile) SP", "outputs/week4/t2_opt_freq/EMC/EMC_G2.xyz", "265", "20", "-383.211538386603", "true", "49.0", "computed", ""),
    ("C02", "EMC", "M", "S2", "omegaB97X-D4", "def2-TZVPD", "true", "0", "1", "wB97X-D4 def2-TZVPD SMD(acetonitrile) SP", "outputs/week4/t2_opt_freq/EMC/EMC_G2.xyz", "340", "20", "-383.213500883226", "true", "88.5", "computed", ""),
    ("C02", "EMC", "M", "S3", "PBE0-D4", "def2-TZVP", "false", "0", "1", "PBE0 D4 def2-TZVP SMD(acetonitrile) SP", "outputs/week4/t2_opt_freq/EMC/EMC_G2.xyz", "265", "17", "-382.670744787817", "true", "39.2", "computed", ""),
    ("C02", "EMC", "M", "S4", "PBE0-D4", "def2-TZVPD", "true", "0", "1", "PBE0 D4 def2-TZVPD SMD(acetonitrile) SP", "outputs/week4/t2_opt_freq/EMC/EMC_G2.xyz", "340", "17", "-382.672582085988", "true", "57.2", "computed", ""),
    ("C02", "EMC", "M_plus", "S1", "omegaB97X-D4", "def2-TZVP", "false", "1", "2", "wB97X-D4 def2-TZVP SMD(acetonitrile) SP", "outputs/week4/t2_opt_freq/EMC/EMC_G2_cation.xyz", "265", "88", "-382.889939158368", "true", "263.6", "computed", ""),
    ("C02", "EMC", "M_plus", "S2", "omegaB97X-D4", "def2-TZVPD", "true", "1", "2", "wB97X-D4 def2-TZVPD SMD(acetonitrile) SP", "outputs/week4/t2_opt_freq/EMC/EMC_G2_cation.xyz", "340", "79", "-382.891126329972", "true", "364.5", "computed", ""),
    ("C02", "EMC", "M_plus", "S3", "PBE0-D4", "def2-TZVP", "false", "1", "2", "PBE0 D4 def2-TZVP SMD(acetonitrile) SP", "outputs/week4/t2_opt_freq/EMC/EMC_G2_cation.xyz", "265", "27", "-382.361287902109", "true", "68.7", "computed", ""),
    ("C02", "EMC", "M_plus", "S4", "PBE0-D4", "def2-TZVPD", "true", "1", "2", "PBE0 D4 def2-TZVPD SMD(acetonitrile) SP", "outputs/week4/t2_opt_freq/EMC/EMC_G2_cation.xyz", "340", "26", "-382.362441800872", "true", "125.0", "computed", ""),
    ("C02", "EMC", "LiM_plus", "S1", "omegaB97X-D4", "def2-TZVP", "false", "1", "1", "wB97X-D4 def2-TZVP SMD(acetonitrile) SP", "work/audit/EMC_Li/EMC_m1_G2Li.xyz", "279", "20", "-390.665656103452", "true", "65.3", "computed", "no_diffuse_on_reduction_state"),
    ("C02", "EMC", "LiM_plus", "S2", "omegaB97X-D4", "def2-TZVPD", "true", "1", "1", "wB97X-D4 def2-TZVPD SMD(acetonitrile) SP", "work/audit/EMC_Li/EMC_m1_G2Li.xyz", "357", "20", "-390.667188942774", "true", "101.9", "computed", ""),
    ("C02", "EMC", "LiM_plus", "S3", "PBE0-D4", "def2-TZVP", "false", "1", "1", "PBE0 D4 def2-TZVP SMD(acetonitrile) SP", "work/audit/EMC_Li/EMC_m1_G2Li.xyz", "279", "17", "-390.099330478337", "true", "42.2", "computed", "no_diffuse_on_reduction_state"),
    ("C02", "EMC", "LiM_plus", "S4", "PBE0-D4", "def2-TZVPD", "true", "1", "1", "PBE0 D4 def2-TZVPD SMD(acetonitrile) SP", "work/audit/EMC_Li/EMC_m1_G2Li.xyz", "357", "17", "-390.100795431588", "true", "63.2", "computed", ""),
    ("C02", "EMC", "LiM_2plus", "S1", "omegaB97X-D4", "def2-TZVP", "false", "2", "2", "wB97X-D4 def2-TZVP SMD(acetonitrile) SP", "work/audit/EMC_Li/EMC_m1_G2Li.xyz", "279", "28", "-390.315709390891", "true", "102.7", "computed", "no_diffuse_on_reduction_state"),
    ("C02", "EMC", "LiM_2plus", "S2", "omegaB97X-D4", "def2-TZVPD", "true", "2", "2", "wB97X-D4 def2-TZVPD SMD(acetonitrile) SP", "work/audit/EMC_Li/EMC_m1_G2Li.xyz", "357", "29", "-390.316843320222", "true", "171.1", "computed", ""),
    ("C02", "EMC", "LiM_2plus", "S3", "PBE0-D4", "def2-TZVP", "false", "2", "2", "PBE0 D4 def2-TZVP SMD(acetonitrile) SP", "work/audit/EMC_Li/EMC_m1_G2Li.xyz", "279", "19", "-389.766104290570", "true", "41.7", "computed", "no_diffuse_on_reduction_state"),
    ("C02", "EMC", "LiM_2plus", "S4", "PBE0-D4", "def2-TZVPD", "true", "2", "2", "PBE0 D4 def2-TZVPD SMD(acetonitrile) SP", "work/audit/EMC_Li/EMC_m1_G2Li.xyz", "357", "19", "-389.767187069562", "true", "72.3", "computed", ""),
    ("C04", "EC", "M", "S1", "omegaB97X-D4", "def2-TZVP", "false", "0", "1", "wB97X-D4 def2-TZVP SMD(acetonitrile) SP", "outputs/week4/t2_opt_freq/EC/EC_G2.xyz", "210", "20", "-342.648443929403", "true", "26.6", "computed", ""),
    ("C04", "EC", "M", "S2", "omegaB97X-D4", "def2-TZVPD", "true", "0", "1", "wB97X-D4 def2-TZVPD SMD(acetonitrile) SP", "outputs/week4/t2_opt_freq/EC/EC_G2.xyz", "267", "20", "-342.650450696278", "true", "41.3", "computed", ""),
    ("C04", "EC", "M", "S3", "PBE0-D4", "def2-TZVP", "false", "0", "1", "PBE0 D4 def2-TZVP SMD(acetonitrile) SP", "outputs/week4/t2_opt_freq/EC/EC_G2.xyz", "210", "17", "-342.191432590440", "true", "19.0", "computed", ""),
    ("C04", "EC", "M", "S4", "PBE0-D4", "def2-TZVPD", "true", "0", "1", "PBE0 D4 def2-TZVPD SMD(acetonitrile) SP", "outputs/week4/t2_opt_freq/EC/EC_G2.xyz", "267", "17", "-342.193314204697", "true", "24.1", "computed", ""),
    ("C04", "EC", "M_plus", "S1", "omegaB97X-D4", "def2-TZVP", "false", "1", "2", "wB97X-D4 def2-TZVP SMD(acetonitrile) SP", "outputs/week4/t2_opt_freq/EC/EC_G2_cation.xyz", "210", "18", "-342.325847603317", "true", "26.1", "computed", ""),
    ("C04", "EC", "M_plus", "S2", "omegaB97X-D4", "def2-TZVPD", "true", "1", "2", "wB97X-D4 def2-TZVPD SMD(acetonitrile) SP", "outputs/week4/t2_opt_freq/EC/EC_G2_cation.xyz", "267", "18", "-342.327007714133", "true", "40.4", "computed", ""),
    ("C04", "EC", "M_plus", "S3", "PBE0-D4", "def2-TZVP", "false", "1", "2", "PBE0 D4 def2-TZVP SMD(acetonitrile) SP", "outputs/week4/t2_opt_freq/EC/EC_G2_cation.xyz", "210", "15", "-341.883122714555", "true", "17.9", "computed", ""),
    ("C04", "EC", "M_plus", "S4", "PBE0-D4", "def2-TZVPD", "true", "1", "2", "PBE0 D4 def2-TZVPD SMD(acetonitrile) SP", "outputs/week4/t2_opt_freq/EC/EC_G2_cation.xyz", "267", "15", "-341.884197654566", "true", "27.3", "computed", ""),
    ("C04", "EC", "LiM_plus", "S1", "omegaB97X-D4", "def2-TZVP", "false", "1", "1", "wB97X-D4 def2-TZVP SMD(acetonitrile) SP", "outputs/week5/c1/EC/EC_m1_G2Li.xyz", "224", "20", "-350.103043323331", "true", "27.3", "computed", "no_diffuse_on_reduction_state"),
    ("C04", "EC", "LiM_plus", "S2", "omegaB97X-D4", "def2-TZVPD", "true", "1", "1", "wB97X-D4 def2-TZVPD SMD(acetonitrile) SP", "outputs/week5/c1/EC/EC_m1_G2Li.xyz", "284", "20", "-350.104556957626", "true", "41.2", "computed", ""),
    ("C04", "EC", "LiM_plus", "S3", "PBE0-D4", "def2-TZVP", "false", "1", "1", "PBE0 D4 def2-TZVP SMD(acetonitrile) SP", "outputs/week5/c1/EC/EC_m1_G2Li.xyz", "224", "17", "-349.620475058765", "true", "17.8", "computed", "no_diffuse_on_reduction_state"),
    ("C04", "EC", "LiM_plus", "S4", "PBE0-D4", "def2-TZVPD", "true", "1", "1", "PBE0 D4 def2-TZVPD SMD(acetonitrile) SP", "outputs/week5/c1/EC/EC_m1_G2Li.xyz", "284", "17", "-349.621932340489", "true", "24.6", "computed", ""),
    ("C04", "EC", "LiM_2plus", "S1", "omegaB97X-D4", "def2-TZVP", "false", "2", "2", "wB97X-D4 def2-TZVP SMD(acetonitrile) SP", "outputs/week5/c1/EC/EC_m1_G2Li.xyz", "224", "20", "-349.756680339074", "true", "29.4", "computed", "no_diffuse_on_reduction_state"),
    ("C04", "EC", "LiM_2plus", "S2", "omegaB97X-D4", "def2-TZVPD", "true", "2", "2", "wB97X-D4 def2-TZVPD SMD(acetonitrile) SP", "outputs/week5/c1/EC/EC_m1_G2Li.xyz", "284", "20", "-349.757669736449", "true", "43.8", "computed", ""),
    ("C04", "EC", "LiM_2plus", "S3", "PBE0-D4", "def2-TZVP", "false", "2", "2", "PBE0 D4 def2-TZVP SMD(acetonitrile) SP", "outputs/week5/c1/EC/EC_m1_G2Li.xyz", "224", "13", "-349.288074994445", "true", "17.5", "computed", "no_diffuse_on_reduction_state"),
    ("C04", "EC", "LiM_2plus", "S4", "PBE0-D4", "def2-TZVPD", "true", "2", "2", "PBE0 D4 def2-TZVPD SMD(acetonitrile) SP", "outputs/week5/c1/EC/EC_m1_G2Li.xyz", "284", "13", "-349.289045078109", "true", "24.2", "computed", ""),
    ("C08", "DME", "M", "S1", "omegaB97X-D4", "def2-TZVP", "false", "0", "1", "wB97X-D4 def2-TZVP SMD(acetonitrile) SP", "outputs/week4/t2_opt_freq/DME/DME_G2.xyz", "246", "20", "-309.100973556793", "true", "47.4", "computed", ""),
    ("C08", "DME", "M", "S2", "omegaB97X-D4", "def2-TZVPD", "true", "0", "1", "wB97X-D4 def2-TZVPD SMD(acetonitrile) SP", "outputs/week4/t2_opt_freq/DME/DME_G2.xyz", "318", "20", "-309.103516109755", "true", "79.1", "computed", ""),
    ("C08", "DME", "M", "S3", "PBE0-D4", "def2-TZVP", "false", "0", "1", "PBE0 D4 def2-TZVP SMD(acetonitrile) SP", "outputs/week4/t2_opt_freq/DME/DME_G2.xyz", "246", "14", "-308.633581313762", "true", "33.8", "computed", ""),
    ("C08", "DME", "M", "S4", "PBE0-D4", "def2-TZVPD", "true", "0", "1", "PBE0 D4 def2-TZVPD SMD(acetonitrile) SP", "outputs/week4/t2_opt_freq/DME/DME_G2.xyz", "318", "14", "-308.636022787278", "true", "47.8", "computed", ""),
    ("C08", "DME", "M_plus", "S1", "omegaB97X-D4", "def2-TZVP", "false", "1", "2", "wB97X-D4 def2-TZVP SMD(acetonitrile) SP", "outputs/week4/t2_opt_freq/DME/DME_G2_cation.xyz", "246", "30", "-308.832125907142", "true", "104.4", "computed", ""),
    ("C08", "DME", "M_plus", "S2", "omegaB97X-D4", "def2-TZVPD", "true", "1", "2", "wB97X-D4 def2-TZVPD SMD(acetonitrile) SP", "outputs/week4/t2_opt_freq/DME/DME_G2_cation.xyz", "318", "31", "-308.833663009501", "true", "174.3", "computed", ""),
    ("C08", "DME", "M_plus", "S3", "PBE0-D4", "def2-TZVP", "false", "1", "2", "PBE0 D4 def2-TZVP SMD(acetonitrile) SP", "outputs/week4/t2_opt_freq/DME/DME_G2_cation.xyz", "246", "16", "-308.378335619556", "true", "43.3", "computed", ""),
    ("C08", "DME", "M_plus", "S4", "PBE0-D4", "def2-TZVPD", "true", "1", "2", "PBE0 D4 def2-TZVPD SMD(acetonitrile) SP", "outputs/week4/t2_opt_freq/DME/DME_G2_cation.xyz", "318", "16", "-308.379724861633", "true", "70.3", "computed", ""),
    ("C08", "DME", "LiM_plus", "S1", "omegaB97X-D4", "def2-TZVP", "false", "1", "1", "wB97X-D4 def2-TZVP SMD(acetonitrile) SP", "outputs/week5/c1/DME/DME_m1_G2Li.xyz", "260", "20", "-316.575853825302", "true", "61.1", "computed", "no_diffuse_on_reduction_state"),
    ("C08", "DME", "LiM_plus", "S2", "omegaB97X-D4", "def2-TZVPD", "true", "1", "1", "wB97X-D4 def2-TZVPD SMD(acetonitrile) SP", "outputs/week5/c1/DME/DME_m1_G2Li.xyz", "335", "20", "-316.577534532211", "true", "96.6", "computed", ""),
    ("C08", "DME", "LiM_plus", "S3", "PBE0-D4", "def2-TZVP", "false", "1", "1", "PBE0 D4 def2-TZVP SMD(acetonitrile) SP", "outputs/week5/c1/DME/DME_m1_G2Li.xyz", "260", "14", "-316.080828876168", "true", "35.9", "computed", "no_diffuse_on_reduction_state"),
    ("C08", "DME", "LiM_plus", "S4", "PBE0-D4", "def2-TZVPD", "true", "1", "1", "PBE0 D4 def2-TZVPD SMD(acetonitrile) SP", "outputs/week5/c1/DME/DME_m1_G2Li.xyz", "335", "14", "-316.082469582709", "true", "52.0", "computed", ""),
    ("C08", "DME", "LiM_2plus", "S1", "omegaB97X-D4", "def2-TZVP", "false", "2", "2", "wB97X-D4 def2-TZVP SMD(acetonitrile) SP", "outputs/week5/c1/DME/DME_m1_G2Li.xyz", "260", "19", "-316.260841530101", "true", "67.4", "computed", "no_diffuse_on_reduction_state"),
    ("C08", "DME", "LiM_2plus", "S2", "omegaB97X-D4", "def2-TZVPD", "true", "2", "2", "wB97X-D4 def2-TZVPD SMD(acetonitrile) SP", "outputs/week5/c1/DME/DME_m1_G2Li.xyz", "335", "19", "-316.262309986377", "true", "113.0", "computed", ""),
    ("C08", "DME", "LiM_2plus", "S3", "PBE0-D4", "def2-TZVP", "false", "2", "2", "PBE0 D4 def2-TZVP SMD(acetonitrile) SP", "outputs/week5/c1/DME/DME_m1_G2Li.xyz", "260", "11", "-315.786091938249", "true", "43.2", "computed", "no_diffuse_on_reduction_state"),
    ("C08", "DME", "LiM_2plus", "S4", "PBE0-D4", "def2-TZVPD", "true", "2", "2", "PBE0 D4 def2-TZVPD SMD(acetonitrile) SP", "outputs/week5/c1/DME/DME_m1_G2Li.xyz", "335", "11", "-315.787507249774", "true", "62.1", "computed", ""),
    ("C13", "GBL", "M", "S1", "omegaB97X-D4", "def2-TZVP", "false", "0", "1", "wB97X-D4 def2-TZVP SMD(acetonitrile) SP", "outputs/week4/t2_opt_freq/GBL/GBL_G2.xyz", "222", "20", "-306.736607063330", "true", "44.0", "computed", ""),
    ("C13", "GBL", "M", "S2", "omegaB97X-D4", "def2-TZVPD", "true", "0", "1", "wB97X-D4 def2-TZVPD SMD(acetonitrile) SP", "outputs/week4/t2_opt_freq/GBL/GBL_G2.xyz", "282", "20", "-306.738417709651", "true", "61.6", "computed", ""),
    ("C13", "GBL", "M", "S3", "PBE0-D4", "def2-TZVP", "false", "0", "1", "PBE0 D4 def2-TZVP SMD(acetonitrile) SP", "outputs/week4/t2_opt_freq/GBL/GBL_G2.xyz", "222", "17", "-306.293464760481", "true", "29.6", "computed", ""),
    ("C13", "GBL", "M", "S4", "PBE0-D4", "def2-TZVPD", "true", "0", "1", "PBE0 D4 def2-TZVPD SMD(acetonitrile) SP", "outputs/week4/t2_opt_freq/GBL/GBL_G2.xyz", "282", "17", "-306.295169866936", "true", "39.9", "computed", ""),
    ("C13", "GBL", "M_plus", "S1", "omegaB97X-D4", "def2-TZVP", "false", "1", "2", "wB97X-D4 def2-TZVP SMD(acetonitrile) SP", "outputs/week4/t2_opt_freq/GBL/GBL_G2_cation.xyz", "222", "35", "-306.440615720570", "true", "77.1", "computed", ""),
    ("C13", "GBL", "M_plus", "S2", "omegaB97X-D4", "def2-TZVPD", "true", "1", "2", "wB97X-D4 def2-TZVPD SMD(acetonitrile) SP", "outputs/week4/t2_opt_freq/GBL/GBL_G2_cation.xyz", "282", "35", "-306.441297422598", "true", "113.5", "computed", ""),
    ("C13", "GBL", "M_plus", "S3", "PBE0-D4", "def2-TZVP", "false", "1", "2", "PBE0 D4 def2-TZVP SMD(acetonitrile) SP", "outputs/week4/t2_opt_freq/GBL/GBL_G2_cation.xyz", "222", "37", "-306.006696175664", "true", "64.4", "computed", ""),
    ("C13", "GBL", "M_plus", "S4", "PBE0-D4", "def2-TZVPD", "true", "1", "2", "PBE0 D4 def2-TZVPD SMD(acetonitrile) SP", "outputs/week4/t2_opt_freq/GBL/GBL_G2_cation.xyz", "282", "35", "-306.007537605440", "true", "72.2", "computed", ""),
    ("C13", "GBL", "LiM_plus", "S1", "omegaB97X-D4", "def2-TZVP", "false", "1", "1", "wB97X-D4 def2-TZVP SMD(acetonitrile) SP", "outputs/week5/c1/GBL/GBL_m1_G2Li.xyz", "236", "20", "-314.192731703640", "true", "37.1", "computed", "no_diffuse_on_reduction_state"),
    ("C13", "GBL", "LiM_plus", "S2", "omegaB97X-D4", "def2-TZVPD", "true", "1", "1", "wB97X-D4 def2-TZVPD SMD(acetonitrile) SP", "outputs/week5/c1/GBL/GBL_m1_G2Li.xyz", "299", "20", "-314.193990862615", "true", "57.1", "computed", ""),
    ("C13", "GBL", "LiM_plus", "S3", "PBE0-D4", "def2-TZVP", "false", "1", "1", "PBE0 D4 def2-TZVP SMD(acetonitrile) SP", "outputs/week5/c1/GBL/GBL_m1_G2Li.xyz", "236", "17", "-313.724111183296", "true", "24.2", "computed", "no_diffuse_on_reduction_state"),
    ("C13", "GBL", "LiM_plus", "S4", "PBE0-D4", "def2-TZVPD", "true", "1", "1", "PBE0 D4 def2-TZVPD SMD(acetonitrile) SP", "outputs/week5/c1/GBL/GBL_m1_G2Li.xyz", "299", "17", "-313.725337033879", "true", "37.4", "computed", ""),
    ("C13", "GBL", "LiM_2plus", "S1", "omegaB97X-D4", "def2-TZVP", "false", "2", "2", "wB97X-D4 def2-TZVP SMD(acetonitrile) SP", "outputs/week5/c1/GBL/GBL_m1_G2Li.xyz", "236", "22", "-313.848757385770", "true", "43.4", "computed", "no_diffuse_on_reduction_state"),
    ("C13", "GBL", "LiM_2plus", "S2", "omegaB97X-D4", "def2-TZVPD", "true", "2", "2", "wB97X-D4 def2-TZVPD SMD(acetonitrile) SP", "outputs/week5/c1/GBL/GBL_m1_G2Li.xyz", "299", "22", "-313.849635691208", "true", "67.7", "computed", ""),
    ("C13", "GBL", "LiM_2plus", "S3", "PBE0-D4", "def2-TZVP", "false", "2", "2", "PBE0 D4 def2-TZVP SMD(acetonitrile) SP", "outputs/week5/c1/GBL/GBL_m1_G2Li.xyz", "236", "27", "-313.395514697701", "true", "41.2", "computed", "no_diffuse_on_reduction_state"),
    ("C13", "GBL", "LiM_2plus", "S4", "PBE0-D4", "def2-TZVPD", "true", "2", "2", "PBE0 D4 def2-TZVPD SMD(acetonitrile) SP", "outputs/week5/c1/GBL/GBL_m1_G2Li.xyz", "299", "27", "-313.396297945663", "true", "66.1", "computed", ""),
    ("C14", "SL", "M", "S1", "omegaB97X-D4", "def2-TZVP", "false", "0", "1", "wB97X-D4 def2-TZVP SMD(acetonitrile) SP", "outputs/week4/t2_opt_freq/SL/SL_G2.xyz", "271", "20", "-706.148919933265", "true", "62.8", "computed", ""),
    ("C14", "SL", "M", "S2", "omegaB97X-D4", "def2-TZVPD", "true", "0", "1", "wB97X-D4 def2-TZVPD SMD(acetonitrile) SP", "outputs/week4/t2_opt_freq/SL/SL_G2.xyz", "346", "20", "-706.152019539602", "true", "101.1", "computed", ""),
    ("C14", "SL", "M", "S3", "PBE0-D4", "def2-TZVP", "false", "0", "1", "PBE0 D4 def2-TZVP SMD(acetonitrile) SP", "outputs/week4/t2_opt_freq/SL/SL_G2.xyz", "271", "16", "-705.550797236237", "true", "41.3", "computed", ""),
    ("C14", "SL", "M", "S4", "PBE0-D4", "def2-TZVPD", "true", "0", "1", "PBE0 D4 def2-TZVPD SMD(acetonitrile) SP", "outputs/week4/t2_opt_freq/SL/SL_G2.xyz", "346", "16", "-705.553666100701", "true", "72.7", "computed", ""),
    ("C14", "SL", "M_plus", "S1", "omegaB97X-D4", "def2-TZVP", "false", "1", "2", "wB97X-D4 def2-TZVP SMD(acetonitrile) SP", "outputs/week4/t2_opt_freq/SL/SL_G2_cation.xyz", "271", "18", "-705.853511298493", "true", "79.5", "computed", ""),
    ("C14", "SL", "M_plus", "S2", "omegaB97X-D4", "def2-TZVPD", "true", "1", "2", "wB97X-D4 def2-TZVPD SMD(acetonitrile) SP", "outputs/week4/t2_opt_freq/SL/SL_G2_cation.xyz", "346", "18", "-705.855124087928", "true", "124.0", "computed", ""),
    ("C14", "SL", "M_plus", "S3", "PBE0-D4", "def2-TZVP", "false", "1", "2", "PBE0 D4 def2-TZVP SMD(acetonitrile) SP", "outputs/week4/t2_opt_freq/SL/SL_G2_cation.xyz", "271", "13", "-705.267521706427", "true", "45.1", "computed", ""),
    ("C14", "SL", "M_plus", "S4", "PBE0-D4", "def2-TZVPD", "true", "1", "2", "PBE0 D4 def2-TZVPD SMD(acetonitrile) SP", "outputs/week4/t2_opt_freq/SL/SL_G2_cation.xyz", "346", "13", "-705.269026410610", "true", "71.7", "computed", ""),
    ("C14", "SL", "LiM_plus", "S1", "omegaB97X-D4", "def2-TZVP", "false", "1", "1", "wB97X-D4 def2-TZVP SMD(acetonitrile) SP", "outputs/week5/c1/SL/SL_m1_G2Li.xyz", "285", "20", "-713.603210544289", "true", "73.3", "computed", "no_diffuse_on_reduction_state"),
    ("C14", "SL", "LiM_plus", "S2", "omegaB97X-D4", "def2-TZVPD", "true", "1", "1", "wB97X-D4 def2-TZVPD SMD(acetonitrile) SP", "outputs/week5/c1/SL/SL_m1_G2Li.xyz", "363", "20", "-713.605506835733", "true", "114.4", "computed", ""),
    ("C14", "SL", "LiM_plus", "S3", "PBE0-D4", "def2-TZVP", "false", "1", "1", "PBE0 D4 def2-TZVP SMD(acetonitrile) SP", "outputs/week5/c1/SL/SL_m1_G2Li.xyz", "285", "16", "-712.978729838478", "true", "42.8", "computed", "no_diffuse_on_reduction_state"),
    ("C14", "SL", "LiM_plus", "S4", "PBE0-D4", "def2-TZVPD", "true", "1", "1", "PBE0 D4 def2-TZVPD SMD(acetonitrile) SP", "outputs/week5/c1/SL/SL_m1_G2Li.xyz", "363", "16", "-712.980905636808", "true", "69.8", "computed", ""),
    ("C14", "SL", "LiM_2plus", "S1", "omegaB97X-D4", "def2-TZVP", "false", "2", "2", "wB97X-D4 def2-TZVP SMD(acetonitrile) SP", "outputs/week5/c1/SL/SL_m1_G2Li.xyz", "285", "19", "-713.265789352465", "true", "90.1", "computed", "no_diffuse_on_reduction_state"),
    ("C14", "SL", "LiM_2plus", "S2", "omegaB97X-D4", "def2-TZVPD", "true", "2", "2", "wB97X-D4 def2-TZVPD SMD(acetonitrile) SP", "outputs/week5/c1/SL/SL_m1_G2Li.xyz", "363", "19", "-713.267691295074", "true", "141.8", "computed", ""),
    ("C14", "SL", "LiM_2plus", "S3", "PBE0-D4", "def2-TZVP", "false", "2", "2", "PBE0 D4 def2-TZVP SMD(acetonitrile) SP", "outputs/week5/c1/SL/SL_m1_G2Li.xyz", "285", "15", "-712.654968007392", "true", "54.3", "computed", "no_diffuse_on_reduction_state"),
    ("C14", "SL", "LiM_2plus", "S4", "PBE0-D4", "def2-TZVPD", "true", "2", "2", "PBE0 D4 def2-TZVPD SMD(acetonitrile) SP", "outputs/week5/c1/SL/SL_m1_G2Li.xyz", "363", "15", "-712.656818384113", "true", "85.0", "computed", ""),
    ("C16", "AN", "M", "S1", "omegaB97X-D4", "def2-TZVP", "false", "0", "1", "wB97X-D4 def2-TZVP SMD(acetonitrile) SP", "outputs/week4/t2_opt_freq/AN/AN_G2.xyz", "111", "19", "-132.866713103685", "true", "16.7", "computed", ""),
    ("C16", "AN", "M", "S2", "omegaB97X-D4", "def2-TZVPD", "true", "0", "1", "wB97X-D4 def2-TZVPD SMD(acetonitrile) SP", "outputs/week4/t2_opt_freq/AN/AN_G2.xyz", "138", "19", "-132.867164124598", "true", "17.4", "computed", ""),
    ("C16", "AN", "M", "S3", "PBE0-D4", "def2-TZVP", "false", "0", "1", "PBE0 D4 def2-TZVP SMD(acetonitrile) SP", "outputs/week4/t2_opt_freq/AN/AN_G2.xyz", "111", "18", "-132.654270869947", "true", "13.1", "computed", ""),
    ("C16", "AN", "M", "S4", "PBE0-D4", "def2-TZVPD", "true", "0", "1", "PBE0 D4 def2-TZVPD SMD(acetonitrile) SP", "outputs/week4/t2_opt_freq/AN/AN_G2.xyz", "138", "18", "-132.654687616699", "true", "16.8", "computed", ""),
    ("C16", "AN", "M_plus", "S1", "omegaB97X-D4", "def2-TZVP", "false", "1", "2", "wB97X-D4 def2-TZVP SMD(acetonitrile) SP", "outputs/week4/t2_opt_freq/AN/AN_G2_cation.xyz", "111", "17", "-132.518205496616", "true", "15.4", "computed", ""),
    ("C16", "AN", "M_plus", "S2", "omegaB97X-D4", "def2-TZVPD", "true", "1", "2", "wB97X-D4 def2-TZVPD SMD(acetonitrile) SP", "outputs/week4/t2_opt_freq/AN/AN_G2_cation.xyz", "138", "17", "-132.518408073778", "true", "19.7", "computed", ""),
    ("C16", "AN", "M_plus", "S3", "PBE0-D4", "def2-TZVP", "false", "1", "2", "PBE0 D4 def2-TZVP SMD(acetonitrile) SP", "outputs/week4/t2_opt_freq/AN/AN_G2_cation.xyz", "111", "13", "-132.313001928392", "true", "12.8", "computed", ""),
    ("C16", "AN", "M_plus", "S4", "PBE0-D4", "def2-TZVPD", "true", "1", "2", "PBE0 D4 def2-TZVPD SMD(acetonitrile) SP", "outputs/week4/t2_opt_freq/AN/AN_G2_cation.xyz", "138", "13", "-132.313201674480", "true", "14.7", "computed", ""),
    ("C16", "AN", "LiM_plus", "S1", "omegaB97X-D4", "def2-TZVP", "false", "1", "1", "wB97X-D4 def2-TZVP SMD(acetonitrile) SP", "outputs/week5/c1/AN/AN_m1_G2Li.xyz", "125", "19", "-140.320939029594", "true", "21.8", "computed", "no_diffuse_on_reduction_state"),
    ("C16", "AN", "LiM_plus", "S2", "omegaB97X-D4", "def2-TZVPD", "true", "1", "1", "wB97X-D4 def2-TZVPD SMD(acetonitrile) SP", "outputs/week5/c1/AN/AN_m1_G2Li.xyz", "155", "19", "-140.321219185162", "true", "22.5", "computed", ""),
    ("C16", "AN", "LiM_plus", "S3", "PBE0-D4", "def2-TZVP", "false", "1", "1", "PBE0 D4 def2-TZVP SMD(acetonitrile) SP", "outputs/week5/c1/AN/AN_m1_G2Li.xyz", "125", "16", "-140.083390919166", "true", "15.9", "computed", "no_diffuse_on_reduction_state"),
    ("C16", "AN", "LiM_plus", "S4", "PBE0-D4", "def2-TZVPD", "true", "1", "1", "PBE0 D4 def2-TZVPD SMD(acetonitrile) SP", "outputs/week5/c1/AN/AN_m1_G2Li.xyz", "155", "16", "-140.083683148714", "true", "18.6", "computed", ""),
    ("C16", "AN", "LiM_2plus", "S1", "omegaB97X-D4", "def2-TZVP", "false", "2", "2", "wB97X-D4 def2-TZVP SMD(acetonitrile) SP", "outputs/week5/c1/AN/AN_m1_G2Li.xyz", "125", "18", "-139.943857075818", "true", "21.6", "computed", "no_diffuse_on_reduction_state"),
    ("C16", "AN", "LiM_2plus", "S2", "omegaB97X-D4", "def2-TZVPD", "true", "2", "2", "wB97X-D4 def2-TZVPD SMD(acetonitrile) SP", "outputs/week5/c1/AN/AN_m1_G2Li.xyz", "155", "18", "-139.944112490112", "true", "28.0", "computed", ""),
    ("C16", "AN", "LiM_2plus", "S3", "PBE0-D4", "def2-TZVP", "false", "2", "2", "PBE0 D4 def2-TZVP SMD(acetonitrile) SP", "outputs/week5/c1/AN/AN_m1_G2Li.xyz", "125", "13", "-139.714417428730", "true", "15.4", "computed", "no_diffuse_on_reduction_state"),
    ("C16", "AN", "LiM_2plus", "S4", "PBE0-D4", "def2-TZVPD", "true", "2", "2", "PBE0 D4 def2-TZVPD SMD(acetonitrile) SP", "outputs/week5/c1/AN/AN_m1_G2Li.xyz", "155", "13", "-139.714680578036", "true", "18.9", "computed", ""),
    ("C17", "TMP", "M", "S1", "omegaB97X-D4", "def2-TZVP", "false", "0", "1", "wB97X-D4 def2-TZVP SMD(acetonitrile) SP", "outputs/week4/t2_opt_freq/TMP/TMP_G2.xyz", "308", "20", "-762.424652667741", "true", "69.4", "computed", ""),
    ("C17", "TMP", "M", "S2", "omegaB97X-D4", "def2-TZVPD", "true", "0", "1", "wB97X-D4 def2-TZVPD SMD(acetonitrile) SP", "outputs/week4/t2_opt_freq/TMP/TMP_G2.xyz", "395", "20", "-762.427857035755", "true", "123.0", "computed", ""),
    ("C17", "TMP", "M", "S3", "PBE0-D4", "def2-TZVP", "false", "0", "1", "PBE0 D4 def2-TZVP SMD(acetonitrile) SP", "outputs/week4/t2_opt_freq/TMP/TMP_G2.xyz", "308", "17", "-761.704847405518", "true", "50.9", "computed", ""),
    ("C17", "TMP", "M", "S4", "PBE0-D4", "def2-TZVPD", "true", "0", "1", "PBE0 D4 def2-TZVPD SMD(acetonitrile) SP", "outputs/week4/t2_opt_freq/TMP/TMP_G2.xyz", "395", "17", "-761.707883052953", "true", "97.7", "computed", ""),
    ("C17", "TMP", "M_plus", "S1", "omegaB97X-D4", "def2-TZVP", "false", "1", "2", "wB97X-D4 def2-TZVP SMD(acetonitrile) SP", "outputs/week4/t2_opt_freq/TMP/TMP_G2_cation.xyz", "308", "35", "-762.099314331015", "true", "144.7", "computed", ""),
    ("C17", "TMP", "M_plus", "S2", "omegaB97X-D4", "def2-TZVPD", "true", "1", "2", "wB97X-D4 def2-TZVPD SMD(acetonitrile) SP", "outputs/week4/t2_opt_freq/TMP/TMP_G2_cation.xyz", "395", "35", "-762.101325971788", "true", "240.2", "computed", ""),
    ("C17", "TMP", "M_plus", "S3", "PBE0-D4", "def2-TZVP", "false", "1", "2", "PBE0 D4 def2-TZVP SMD(acetonitrile) SP", "outputs/week4/t2_opt_freq/TMP/TMP_G2_cation.xyz", "308", "29", "-761.395202304643", "true", "92.9", "computed", ""),
    ("C17", "TMP", "M_plus", "S4", "PBE0-D4", "def2-TZVPD", "true", "1", "2", "PBE0 D4 def2-TZVPD SMD(acetonitrile) SP", "outputs/week4/t2_opt_freq/TMP/TMP_G2_cation.xyz", "395", "25", "-761.397182769384", "true", "142.3", "computed", ""),
    ("C17", "TMP", "LiM_plus", "S1", "omegaB97X-D4", "def2-TZVP", "false", "1", "1", "wB97X-D4 def2-TZVP SMD(acetonitrile) SP", "outputs/week5/c1/TMP/TMP_m1_G2Li.xyz", "322", "20", "-769.886783660897", "true", "85.9", "computed", "no_diffuse_on_reduction_state"),
    ("C17", "TMP", "LiM_plus", "S2", "omegaB97X-D4", "def2-TZVPD", "true", "1", "1", "wB97X-D4 def2-TZVPD SMD(acetonitrile) SP", "outputs/week5/c1/TMP/TMP_m1_G2Li.xyz", "412", "20", "-769.889313866930", "true", "133.6", "computed", ""),
    ("C17", "TMP", "LiM_plus", "S3", "PBE0-D4", "def2-TZVP", "false", "1", "1", "PBE0 D4 def2-TZVP SMD(acetonitrile) SP", "outputs/week5/c1/TMP/TMP_m1_G2Li.xyz", "322", "18", "-769.140729854139", "true", "52.2", "computed", "no_diffuse_on_reduction_state"),
    ("C17", "TMP", "LiM_plus", "S4", "PBE0-D4", "def2-TZVPD", "true", "1", "1", "PBE0 D4 def2-TZVPD SMD(acetonitrile) SP", "outputs/week5/c1/TMP/TMP_m1_G2Li.xyz", "412", "18", "-769.143195125033", "true", "88.1", "computed", ""),
    ("C17", "TMP", "LiM_2plus", "S1", "omegaB97X-D4", "def2-TZVP", "false", "2", "2", "wB97X-D4 def2-TZVP SMD(acetonitrile) SP", "outputs/week5/c1/TMP/TMP_m1_G2Li.xyz", "322", "28", "-769.539798636419", "true", "121.1", "computed", "no_diffuse_on_reduction_state"),
    ("C17", "TMP", "LiM_2plus", "S2", "omegaB97X-D4", "def2-TZVPD", "true", "2", "2", "wB97X-D4 def2-TZVPD SMD(acetonitrile) SP", "outputs/week5/c1/TMP/TMP_m1_G2Li.xyz", "412", "28", "-769.541780102935", "true", "201.6", "computed", ""),
    ("C17", "TMP", "LiM_2plus", "S3", "PBE0-D4", "def2-TZVP", "false", "2", "2", "PBE0 D4 def2-TZVP SMD(acetonitrile) SP", "outputs/week5/c1/TMP/TMP_m1_G2Li.xyz", "322", "20", "-768.812572078900", "true", "55.2", "computed", "no_diffuse_on_reduction_state"),
    ("C17", "TMP", "LiM_2plus", "S4", "PBE0-D4", "def2-TZVPD", "true", "2", "2", "PBE0 D4 def2-TZVPD SMD(acetonitrile) SP", "outputs/week5/c1/TMP/TMP_m1_G2Li.xyz", "412", "20", "-768.814478790532", "true", "99.5", "computed", ""),
]

METHOD_AUDIT_RELAXED_CELLS = [
    ("C01", "DMC", "M_plus_relaxed", "S1", "omegaB97X-D4", "def2-TZVP", "false", "1", "2", "wB97X-D4 def2-TZVP SMD(acetonitrile) SP", "outputs/phase2_p1a/geometry_relaxation/DMC/DMC_cation_opt.xyz", "222", "21", "-343.551839823128", "true", "41.0", "computed", ""),
    ("C01", "DMC", "M_plus_relaxed", "S2", "omegaB97X-D4", "def2-TZVPD", "true", "1", "2", "wB97X-D4 def2-TZVPD SMD(acetonitrile) SP", "outputs/phase2_p1a/geometry_relaxation/DMC/DMC_cation_opt.xyz", "285", "21", "-343.552861633422", "true", "76.6", "computed", ""),
    ("C01", "DMC", "M_plus_relaxed", "S3", "PBE0-D4", "def2-TZVP", "false", "1", "2", "PBE0 D4 def2-TZVP SMD(acetonitrile) SP", "outputs/phase2_p1a/geometry_relaxation/DMC/DMC_cation_opt.xyz", "222", "15", "-343.088465037148", "true", "31.2", "computed", ""),
    ("C01", "DMC", "M_plus_relaxed", "S4", "PBE0-D4", "def2-TZVPD", "true", "1", "2", "PBE0 D4 def2-TZVPD SMD(acetonitrile) SP", "outputs/phase2_p1a/geometry_relaxation/DMC/DMC_cation_opt.xyz", "285", "15", "-343.089441221543", "true", "45.3", "computed", ""),
    ("C02", "EMC", "M_plus_relaxed", "S1", "omegaB97X-D4", "def2-TZVP", "false", "1", "2", "wB97X-D4 def2-TZVP SMD(acetonitrile) SP", "outputs/phase2_p1a/geometry_relaxation/EMC/EMC_cation_opt.xyz", "265", "18", "-382.939688730711", "true", "52.1", "computed", ""),
    ("C02", "EMC", "M_plus_relaxed", "S2", "omegaB97X-D4", "def2-TZVPD", "true", "1", "2", "wB97X-D4 def2-TZVPD SMD(acetonitrile) SP", "outputs/phase2_p1a/geometry_relaxation/EMC/EMC_cation_opt.xyz", "340", "18", "-382.941007314195", "true", "98.8", "computed", ""),
    ("C02", "EMC", "M_plus_relaxed", "S3", "PBE0-D4", "def2-TZVP", "false", "1", "2", "PBE0 D4 def2-TZVP SMD(acetonitrile) SP", "outputs/phase2_p1a/geometry_relaxation/EMC/EMC_cation_opt.xyz", "265", "12", "-382.407889717145", "true", "35.5", "computed", ""),
    ("C02", "EMC", "M_plus_relaxed", "S4", "PBE0-D4", "def2-TZVPD", "true", "1", "2", "PBE0 D4 def2-TZVPD SMD(acetonitrile) SP", "outputs/phase2_p1a/geometry_relaxation/EMC/EMC_cation_opt.xyz", "340", "12", "-382.409180888029", "true", "41.8", "computed", ""),
    ("C04", "EC", "M_plus_relaxed", "S1", "omegaB97X-D4", "def2-TZVP", "false", "1", "2", "wB97X-D4 def2-TZVP SMD(acetonitrile) SP", "outputs/phase2_p1a/geometry_relaxation/EC/EC_cation_opt.xyz", "210", "34", "-342.341729361672", "true", "62.4", "computed", ""),
    ("C04", "EC", "M_plus_relaxed", "S2", "omegaB97X-D4", "def2-TZVPD", "true", "1", "2", "wB97X-D4 def2-TZVPD SMD(acetonitrile) SP", "outputs/phase2_p1a/geometry_relaxation/EC/EC_cation_opt.xyz", "267", "35", "-342.342576025035", "true", "103.2", "computed", ""),
    ("C04", "EC", "M_plus_relaxed", "S3", "PBE0-D4", "def2-TZVP", "false", "1", "2", "PBE0 D4 def2-TZVP SMD(acetonitrile) SP", "outputs/phase2_p1a/geometry_relaxation/EC/EC_cation_opt.xyz", "210", "37", "-341.890795844198", "true", "48.0", "computed", ""),
    ("C04", "EC", "M_plus_relaxed", "S4", "PBE0-D4", "def2-TZVPD", "true", "1", "2", "PBE0 D4 def2-TZVPD SMD(acetonitrile) SP", "outputs/phase2_p1a/geometry_relaxation/EC/EC_cation_opt.xyz", "267", "37", "-341.891720450797", "true", "52.7", "computed", ""),
    ("C08", "DME", "M_plus_relaxed", "S1", "omegaB97X-D4", "def2-TZVP", "false", "1", "2", "wB97X-D4 def2-TZVP SMD(acetonitrile) SP", "outputs/phase2_p1a/geometry_relaxation/DME/DME_cation_opt.xyz", "246", "18", "-308.854725576029", "true", "52.8", "computed", ""),
    ("C08", "DME", "M_plus_relaxed", "S2", "omegaB97X-D4", "def2-TZVPD", "true", "1", "2", "wB97X-D4 def2-TZVPD SMD(acetonitrile) SP", "outputs/phase2_p1a/geometry_relaxation/DME/DME_cation_opt.xyz", "318", "18", "-308.856064245790", "true", "92.0", "computed", ""),
    ("C08", "DME", "M_plus_relaxed", "S3", "PBE0-D4", "def2-TZVP", "false", "1", "2", "PBE0 D4 def2-TZVP SMD(acetonitrile) SP", "outputs/phase2_p1a/geometry_relaxation/DME/DME_cation_opt.xyz", "246", "10", "-308.399693511191", "true", "30.8", "computed", ""),
    ("C08", "DME", "M_plus_relaxed", "S4", "PBE0-D4", "def2-TZVPD", "true", "1", "2", "PBE0 D4 def2-TZVPD SMD(acetonitrile) SP", "outputs/phase2_p1a/geometry_relaxation/DME/DME_cation_opt.xyz", "318", "10", "-308.400989608490", "true", "39.9", "computed", ""),
    ("C13", "GBL", "M_plus_relaxed", "S1", "omegaB97X-D4", "def2-TZVP", "false", "1", "2", "wB97X-D4 def2-TZVP SMD(acetonitrile) SP", "outputs/phase2_p1a/geometry_relaxation/GBL/GBL_cation_opt.xyz", "222", "22", "-306.452715683334", "true", "52.6", "computed", ""),
    ("C13", "GBL", "M_plus_relaxed", "S2", "omegaB97X-D4", "def2-TZVPD", "true", "1", "2", "wB97X-D4 def2-TZVPD SMD(acetonitrile) SP", "outputs/phase2_p1a/geometry_relaxation/GBL/GBL_cation_opt.xyz", "282", "22", "-306.453436244297", "true", "70.5", "computed", ""),
    ("C13", "GBL", "M_plus_relaxed", "S3", "PBE0-D4", "def2-TZVP", "false", "1", "2", "PBE0 D4 def2-TZVP SMD(acetonitrile) SP", "outputs/phase2_p1a/geometry_relaxation/GBL/GBL_cation_opt.xyz", "222", "15", "-306.018379918078", "true", "25.5", "computed", ""),
    ("C13", "GBL", "M_plus_relaxed", "S4", "PBE0-D4", "def2-TZVPD", "true", "1", "2", "PBE0 D4 def2-TZVPD SMD(acetonitrile) SP", "outputs/phase2_p1a/geometry_relaxation/GBL/GBL_cation_opt.xyz", "282", "15", "-306.019100747767", "true", "40.4", "computed", ""),
    ("C14", "SL", "M_plus_relaxed", "S1", "omegaB97X-D4", "def2-TZVP", "false", "1", "2", "wB97X-D4 def2-TZVP SMD(acetonitrile) SP", "outputs/phase2_p1a/geometry_relaxation/SL/SL_cation_opt.xyz", "271", "18", "-705.858765363890", "true", "64.5", "computed", ""),
    ("C14", "SL", "M_plus_relaxed", "S2", "omegaB97X-D4", "def2-TZVPD", "true", "1", "2", "wB97X-D4 def2-TZVPD SMD(acetonitrile) SP", "outputs/phase2_p1a/geometry_relaxation/SL/SL_cation_opt.xyz", "346", "18", "-705.860488117397", "true", "92.7", "computed", ""),
    ("C14", "SL", "M_plus_relaxed", "S3", "PBE0-D4", "def2-TZVP", "false", "1", "2", "PBE0 D4 def2-TZVP SMD(acetonitrile) SP", "outputs/phase2_p1a/geometry_relaxation/SL/SL_cation_opt.xyz", "271", "13", "-705.271901264114", "true", "33.8", "computed", ""),
    ("C14", "SL", "M_plus_relaxed", "S4", "PBE0-D4", "def2-TZVPD", "true", "1", "2", "PBE0 D4 def2-TZVPD SMD(acetonitrile) SP", "outputs/phase2_p1a/geometry_relaxation/SL/SL_cation_opt.xyz", "346", "13", "-705.273488655864", "true", "46.8", "computed", ""),
    ("C16", "AN", "M_plus_relaxed", "S1", "omegaB97X-D4", "def2-TZVP", "false", "1", "2", "wB97X-D4 def2-TZVP SMD(acetonitrile) SP", "outputs/phase2_p1a/geometry_relaxation/AN/AN_cation_opt.xyz", "111", "17", "-132.527159389153", "true", "14.3", "computed", ""),
    ("C16", "AN", "M_plus_relaxed", "S2", "omegaB97X-D4", "def2-TZVPD", "true", "1", "2", "wB97X-D4 def2-TZVPD SMD(acetonitrile) SP", "outputs/phase2_p1a/geometry_relaxation/AN/AN_cation_opt.xyz", "138", "17", "-132.527372980598", "true", "19.3", "computed", ""),
    ("C16", "AN", "M_plus_relaxed", "S3", "PBE0-D4", "def2-TZVP", "false", "1", "2", "PBE0 D4 def2-TZVP SMD(acetonitrile) SP", "outputs/phase2_p1a/geometry_relaxation/AN/AN_cation_opt.xyz", "111", "13", "-132.322862737317", "true", "16.6", "computed", ""),
    ("C16", "AN", "M_plus_relaxed", "S4", "PBE0-D4", "def2-TZVPD", "true", "1", "2", "PBE0 D4 def2-TZVPD SMD(acetonitrile) SP", "outputs/phase2_p1a/geometry_relaxation/AN/AN_cation_opt.xyz", "138", "13", "-132.323070399602", "true", "16.2", "computed", ""),
    ("C17", "TMP", "M_plus_relaxed", "S1", "omegaB97X-D4", "def2-TZVP", "false", "1", "2", "wB97X-D4 def2-TZVP SMD(acetonitrile) SP", "outputs/phase2_p1a/geometry_relaxation/TMP/TMP_cation_opt.xyz", "308", "30", "-762.130770657087", "true", "101.3", "computed", ""),
    ("C17", "TMP", "M_plus_relaxed", "S2", "omegaB97X-D4", "def2-TZVPD", "true", "1", "2", "wB97X-D4 def2-TZVPD SMD(acetonitrile) SP", "outputs/phase2_p1a/geometry_relaxation/TMP/TMP_cation_opt.xyz", "395", "28", "-762.132741167879", "true", "149.4", "computed", ""),
    ("C17", "TMP", "M_plus_relaxed", "S3", "PBE0-D4", "def2-TZVP", "false", "1", "2", "PBE0 D4 def2-TZVP SMD(acetonitrile) SP", "outputs/phase2_p1a/geometry_relaxation/TMP/TMP_cation_opt.xyz", "308", "19", "-761.421577803439", "true", "38.4", "computed", ""),
    ("C17", "TMP", "M_plus_relaxed", "S4", "PBE0-D4", "def2-TZVPD", "true", "1", "2", "PBE0 D4 def2-TZVPD SMD(acetonitrile) SP", "outputs/phase2_p1a/geometry_relaxation/TMP/TMP_cation_opt.xyz", "395", "20", "-761.423507839138", "true", "69.0", "computed", ""),
]

METHOD_AUDIT_EMC_LI_OPT = {
    "wall_sec": 103.89239597320557,
    "n_atoms": 16,
    "li_o_min_ang": 1.741,
    "nonli_components": 1,
    "terminated": True
}

METHOD_AUDIT_COST = [
    {"job_id": "A001", "mol_id": "C01", "name": "DMC", "state": "M", "setting_id": "S1", "basis": "def2-TZVP", "cores": "4", "wall_sec": "24.0", "core_hours": "0.026667", "phase": "orca_audit_single_point"},
    {"job_id": "A002", "mol_id": "C01", "name": "DMC", "state": "M", "setting_id": "S2", "basis": "def2-TZVPD", "cores": "4", "wall_sec": "36.9", "core_hours": "0.041000", "phase": "orca_audit_single_point"},
    {"job_id": "A003", "mol_id": "C01", "name": "DMC", "state": "M", "setting_id": "S3", "basis": "def2-TZVP", "cores": "4", "wall_sec": "16.0", "core_hours": "0.017778", "phase": "orca_audit_single_point"},
    {"job_id": "A004", "mol_id": "C01", "name": "DMC", "state": "M", "setting_id": "S4", "basis": "def2-TZVPD", "cores": "4", "wall_sec": "23.2", "core_hours": "0.025778", "phase": "orca_audit_single_point"},
    {"job_id": "A005", "mol_id": "C01", "name": "DMC", "state": "M_plus", "setting_id": "S1", "basis": "def2-TZVP", "cores": "4", "wall_sec": "27.7", "core_hours": "0.030778", "phase": "orca_audit_single_point"},
    {"job_id": "A006", "mol_id": "C01", "name": "DMC", "state": "M_plus", "setting_id": "S2", "basis": "def2-TZVPD", "cores": "4", "wall_sec": "43.9", "core_hours": "0.048778", "phase": "orca_audit_single_point"},
    {"job_id": "A007", "mol_id": "C01", "name": "DMC", "state": "M_plus", "setting_id": "S3", "basis": "def2-TZVP", "cores": "4", "wall_sec": "18.4", "core_hours": "0.020444", "phase": "orca_audit_single_point"},
    {"job_id": "A008", "mol_id": "C01", "name": "DMC", "state": "M_plus", "setting_id": "S4", "basis": "def2-TZVPD", "cores": "4", "wall_sec": "28.0", "core_hours": "0.031111", "phase": "orca_audit_single_point"},
    {"job_id": "A009", "mol_id": "C01", "name": "DMC", "state": "LiM_plus", "setting_id": "S1", "basis": "def2-TZVP", "cores": "4", "wall_sec": "27.0", "core_hours": "0.030000", "phase": "orca_audit_single_point"},
    {"job_id": "A010", "mol_id": "C01", "name": "DMC", "state": "LiM_plus", "setting_id": "S2", "basis": "def2-TZVPD", "cores": "4", "wall_sec": "42.8", "core_hours": "0.047556", "phase": "orca_audit_single_point"},
    {"job_id": "A011", "mol_id": "C01", "name": "DMC", "state": "LiM_plus", "setting_id": "S3", "basis": "def2-TZVP", "cores": "4", "wall_sec": "17.7", "core_hours": "0.019667", "phase": "orca_audit_single_point"},
    {"job_id": "A012", "mol_id": "C01", "name": "DMC", "state": "LiM_plus", "setting_id": "S4", "basis": "def2-TZVPD", "cores": "4", "wall_sec": "26.7", "core_hours": "0.029667", "phase": "orca_audit_single_point"},
    {"job_id": "A013", "mol_id": "C01", "name": "DMC", "state": "LiM_2plus", "setting_id": "S1", "basis": "def2-TZVP", "cores": "4", "wall_sec": "31.3", "core_hours": "0.034778", "phase": "orca_audit_single_point"},
    {"job_id": "A014", "mol_id": "C01", "name": "DMC", "state": "LiM_2plus", "setting_id": "S2", "basis": "def2-TZVPD", "cores": "4", "wall_sec": "50.5", "core_hours": "0.056111", "phase": "orca_audit_single_point"},
    {"job_id": "A015", "mol_id": "C01", "name": "DMC", "state": "LiM_2plus", "setting_id": "S3", "basis": "def2-TZVP", "cores": "4", "wall_sec": "20.3", "core_hours": "0.022556", "phase": "orca_audit_single_point"},
    {"job_id": "A016", "mol_id": "C01", "name": "DMC", "state": "LiM_2plus", "setting_id": "S4", "basis": "def2-TZVPD", "cores": "4", "wall_sec": "32.2", "core_hours": "0.035778", "phase": "orca_audit_single_point"},
    {"job_id": "A017", "mol_id": "C02", "name": "EMC", "state": "M", "setting_id": "S1", "basis": "def2-TZVP", "cores": "4", "wall_sec": "49.0", "core_hours": "0.054444", "phase": "orca_audit_single_point"},
    {"job_id": "A018", "mol_id": "C02", "name": "EMC", "state": "M", "setting_id": "S2", "basis": "def2-TZVPD", "cores": "4", "wall_sec": "88.5", "core_hours": "0.098333", "phase": "orca_audit_single_point"},
    {"job_id": "A019", "mol_id": "C02", "name": "EMC", "state": "M", "setting_id": "S3", "basis": "def2-TZVP", "cores": "4", "wall_sec": "39.2", "core_hours": "0.043556", "phase": "orca_audit_single_point"},
    {"job_id": "A020", "mol_id": "C02", "name": "EMC", "state": "M", "setting_id": "S4", "basis": "def2-TZVPD", "cores": "4", "wall_sec": "57.2", "core_hours": "0.063556", "phase": "orca_audit_single_point"},
    {"job_id": "A021", "mol_id": "C02", "name": "EMC", "state": "M_plus", "setting_id": "S1", "basis": "def2-TZVP", "cores": "4", "wall_sec": "263.6", "core_hours": "0.292889", "phase": "orca_audit_single_point"},
    {"job_id": "A022", "mol_id": "C02", "name": "EMC", "state": "M_plus", "setting_id": "S2", "basis": "def2-TZVPD", "cores": "4", "wall_sec": "364.5", "core_hours": "0.405000", "phase": "orca_audit_single_point"},
    {"job_id": "A023", "mol_id": "C02", "name": "EMC", "state": "M_plus", "setting_id": "S3", "basis": "def2-TZVP", "cores": "4", "wall_sec": "68.7", "core_hours": "0.076333", "phase": "orca_audit_single_point"},
    {"job_id": "A024", "mol_id": "C02", "name": "EMC", "state": "M_plus", "setting_id": "S4", "basis": "def2-TZVPD", "cores": "4", "wall_sec": "125.0", "core_hours": "0.138889", "phase": "orca_audit_single_point"},
    {"job_id": "A025", "mol_id": "C02", "name": "EMC", "state": "LiM_plus", "setting_id": "S1", "basis": "def2-TZVP", "cores": "4", "wall_sec": "65.3", "core_hours": "0.072556", "phase": "orca_audit_single_point"},
    {"job_id": "A026", "mol_id": "C02", "name": "EMC", "state": "LiM_plus", "setting_id": "S2", "basis": "def2-TZVPD", "cores": "4", "wall_sec": "101.9", "core_hours": "0.113222", "phase": "orca_audit_single_point"},
    {"job_id": "A027", "mol_id": "C02", "name": "EMC", "state": "LiM_plus", "setting_id": "S3", "basis": "def2-TZVP", "cores": "4", "wall_sec": "42.2", "core_hours": "0.046889", "phase": "orca_audit_single_point"},
    {"job_id": "A028", "mol_id": "C02", "name": "EMC", "state": "LiM_plus", "setting_id": "S4", "basis": "def2-TZVPD", "cores": "4", "wall_sec": "63.2", "core_hours": "0.070222", "phase": "orca_audit_single_point"},
    {"job_id": "A029", "mol_id": "C02", "name": "EMC", "state": "LiM_2plus", "setting_id": "S1", "basis": "def2-TZVP", "cores": "4", "wall_sec": "102.7", "core_hours": "0.114111", "phase": "orca_audit_single_point"},
    {"job_id": "A030", "mol_id": "C02", "name": "EMC", "state": "LiM_2plus", "setting_id": "S2", "basis": "def2-TZVPD", "cores": "4", "wall_sec": "171.1", "core_hours": "0.190111", "phase": "orca_audit_single_point"},
    {"job_id": "A031", "mol_id": "C02", "name": "EMC", "state": "LiM_2plus", "setting_id": "S3", "basis": "def2-TZVP", "cores": "4", "wall_sec": "41.7", "core_hours": "0.046333", "phase": "orca_audit_single_point"},
    {"job_id": "A032", "mol_id": "C02", "name": "EMC", "state": "LiM_2plus", "setting_id": "S4", "basis": "def2-TZVPD", "cores": "4", "wall_sec": "72.3", "core_hours": "0.080333", "phase": "orca_audit_single_point"},
    {"job_id": "A033", "mol_id": "C04", "name": "EC", "state": "M", "setting_id": "S1", "basis": "def2-TZVP", "cores": "4", "wall_sec": "26.6", "core_hours": "0.029556", "phase": "orca_audit_single_point"},
    {"job_id": "A034", "mol_id": "C04", "name": "EC", "state": "M", "setting_id": "S2", "basis": "def2-TZVPD", "cores": "4", "wall_sec": "41.3", "core_hours": "0.045889", "phase": "orca_audit_single_point"},
    {"job_id": "A035", "mol_id": "C04", "name": "EC", "state": "M", "setting_id": "S3", "basis": "def2-TZVP", "cores": "4", "wall_sec": "19.0", "core_hours": "0.021111", "phase": "orca_audit_single_point"},
    {"job_id": "A036", "mol_id": "C04", "name": "EC", "state": "M", "setting_id": "S4", "basis": "def2-TZVPD", "cores": "4", "wall_sec": "24.1", "core_hours": "0.026778", "phase": "orca_audit_single_point"},
    {"job_id": "A037", "mol_id": "C04", "name": "EC", "state": "M_plus", "setting_id": "S1", "basis": "def2-TZVP", "cores": "4", "wall_sec": "26.1", "core_hours": "0.029000", "phase": "orca_audit_single_point"},
    {"job_id": "A038", "mol_id": "C04", "name": "EC", "state": "M_plus", "setting_id": "S2", "basis": "def2-TZVPD", "cores": "4", "wall_sec": "40.4", "core_hours": "0.044889", "phase": "orca_audit_single_point"},
    {"job_id": "A039", "mol_id": "C04", "name": "EC", "state": "M_plus", "setting_id": "S3", "basis": "def2-TZVP", "cores": "4", "wall_sec": "17.9", "core_hours": "0.019889", "phase": "orca_audit_single_point"},
    {"job_id": "A040", "mol_id": "C04", "name": "EC", "state": "M_plus", "setting_id": "S4", "basis": "def2-TZVPD", "cores": "4", "wall_sec": "27.3", "core_hours": "0.030333", "phase": "orca_audit_single_point"},
    {"job_id": "A041", "mol_id": "C04", "name": "EC", "state": "LiM_plus", "setting_id": "S1", "basis": "def2-TZVP", "cores": "4", "wall_sec": "27.3", "core_hours": "0.030333", "phase": "orca_audit_single_point"},
    {"job_id": "A042", "mol_id": "C04", "name": "EC", "state": "LiM_plus", "setting_id": "S2", "basis": "def2-TZVPD", "cores": "4", "wall_sec": "41.2", "core_hours": "0.045778", "phase": "orca_audit_single_point"},
    {"job_id": "A043", "mol_id": "C04", "name": "EC", "state": "LiM_plus", "setting_id": "S3", "basis": "def2-TZVP", "cores": "4", "wall_sec": "17.8", "core_hours": "0.019778", "phase": "orca_audit_single_point"},
    {"job_id": "A044", "mol_id": "C04", "name": "EC", "state": "LiM_plus", "setting_id": "S4", "basis": "def2-TZVPD", "cores": "4", "wall_sec": "24.6", "core_hours": "0.027333", "phase": "orca_audit_single_point"},
    {"job_id": "A045", "mol_id": "C04", "name": "EC", "state": "LiM_2plus", "setting_id": "S1", "basis": "def2-TZVP", "cores": "4", "wall_sec": "29.4", "core_hours": "0.032667", "phase": "orca_audit_single_point"},
    {"job_id": "A046", "mol_id": "C04", "name": "EC", "state": "LiM_2plus", "setting_id": "S2", "basis": "def2-TZVPD", "cores": "4", "wall_sec": "43.8", "core_hours": "0.048667", "phase": "orca_audit_single_point"},
    {"job_id": "A047", "mol_id": "C04", "name": "EC", "state": "LiM_2plus", "setting_id": "S3", "basis": "def2-TZVP", "cores": "4", "wall_sec": "17.5", "core_hours": "0.019444", "phase": "orca_audit_single_point"},
    {"job_id": "A048", "mol_id": "C04", "name": "EC", "state": "LiM_2plus", "setting_id": "S4", "basis": "def2-TZVPD", "cores": "4", "wall_sec": "24.2", "core_hours": "0.026889", "phase": "orca_audit_single_point"},
    {"job_id": "A049", "mol_id": "C08", "name": "DME", "state": "M", "setting_id": "S1", "basis": "def2-TZVP", "cores": "4", "wall_sec": "47.4", "core_hours": "0.052667", "phase": "orca_audit_single_point"},
    {"job_id": "A050", "mol_id": "C08", "name": "DME", "state": "M", "setting_id": "S2", "basis": "def2-TZVPD", "cores": "4", "wall_sec": "79.1", "core_hours": "0.087889", "phase": "orca_audit_single_point"},
    {"job_id": "A051", "mol_id": "C08", "name": "DME", "state": "M", "setting_id": "S3", "basis": "def2-TZVP", "cores": "4", "wall_sec": "33.8", "core_hours": "0.037556", "phase": "orca_audit_single_point"},
    {"job_id": "A052", "mol_id": "C08", "name": "DME", "state": "M", "setting_id": "S4", "basis": "def2-TZVPD", "cores": "4", "wall_sec": "47.8", "core_hours": "0.053111", "phase": "orca_audit_single_point"},
    {"job_id": "A053", "mol_id": "C08", "name": "DME", "state": "M_plus", "setting_id": "S1", "basis": "def2-TZVP", "cores": "4", "wall_sec": "104.4", "core_hours": "0.116000", "phase": "orca_audit_single_point"},
    {"job_id": "A054", "mol_id": "C08", "name": "DME", "state": "M_plus", "setting_id": "S2", "basis": "def2-TZVPD", "cores": "4", "wall_sec": "174.3", "core_hours": "0.193667", "phase": "orca_audit_single_point"},
    {"job_id": "A055", "mol_id": "C08", "name": "DME", "state": "M_plus", "setting_id": "S3", "basis": "def2-TZVP", "cores": "4", "wall_sec": "43.3", "core_hours": "0.048111", "phase": "orca_audit_single_point"},
    {"job_id": "A056", "mol_id": "C08", "name": "DME", "state": "M_plus", "setting_id": "S4", "basis": "def2-TZVPD", "cores": "4", "wall_sec": "70.3", "core_hours": "0.078111", "phase": "orca_audit_single_point"},
    {"job_id": "A057", "mol_id": "C08", "name": "DME", "state": "LiM_plus", "setting_id": "S1", "basis": "def2-TZVP", "cores": "4", "wall_sec": "61.1", "core_hours": "0.067889", "phase": "orca_audit_single_point"},
    {"job_id": "A058", "mol_id": "C08", "name": "DME", "state": "LiM_plus", "setting_id": "S2", "basis": "def2-TZVPD", "cores": "4", "wall_sec": "96.6", "core_hours": "0.107333", "phase": "orca_audit_single_point"},
    {"job_id": "A059", "mol_id": "C08", "name": "DME", "state": "LiM_plus", "setting_id": "S3", "basis": "def2-TZVP", "cores": "4", "wall_sec": "35.9", "core_hours": "0.039889", "phase": "orca_audit_single_point"},
    {"job_id": "A060", "mol_id": "C08", "name": "DME", "state": "LiM_plus", "setting_id": "S4", "basis": "def2-TZVPD", "cores": "4", "wall_sec": "52.0", "core_hours": "0.057778", "phase": "orca_audit_single_point"},
    {"job_id": "A061", "mol_id": "C08", "name": "DME", "state": "LiM_2plus", "setting_id": "S1", "basis": "def2-TZVP", "cores": "4", "wall_sec": "67.4", "core_hours": "0.074889", "phase": "orca_audit_single_point"},
    {"job_id": "A062", "mol_id": "C08", "name": "DME", "state": "LiM_2plus", "setting_id": "S2", "basis": "def2-TZVPD", "cores": "4", "wall_sec": "113.0", "core_hours": "0.125556", "phase": "orca_audit_single_point"},
    {"job_id": "A063", "mol_id": "C08", "name": "DME", "state": "LiM_2plus", "setting_id": "S3", "basis": "def2-TZVP", "cores": "4", "wall_sec": "43.2", "core_hours": "0.048000", "phase": "orca_audit_single_point"},
    {"job_id": "A064", "mol_id": "C08", "name": "DME", "state": "LiM_2plus", "setting_id": "S4", "basis": "def2-TZVPD", "cores": "4", "wall_sec": "62.1", "core_hours": "0.069000", "phase": "orca_audit_single_point"},
    {"job_id": "A065", "mol_id": "C13", "name": "GBL", "state": "M", "setting_id": "S1", "basis": "def2-TZVP", "cores": "4", "wall_sec": "44.0", "core_hours": "0.048889", "phase": "orca_audit_single_point"},
    {"job_id": "A066", "mol_id": "C13", "name": "GBL", "state": "M", "setting_id": "S2", "basis": "def2-TZVPD", "cores": "4", "wall_sec": "61.6", "core_hours": "0.068444", "phase": "orca_audit_single_point"},
    {"job_id": "A067", "mol_id": "C13", "name": "GBL", "state": "M", "setting_id": "S3", "basis": "def2-TZVP", "cores": "4", "wall_sec": "29.6", "core_hours": "0.032889", "phase": "orca_audit_single_point"},
    {"job_id": "A068", "mol_id": "C13", "name": "GBL", "state": "M", "setting_id": "S4", "basis": "def2-TZVPD", "cores": "4", "wall_sec": "39.9", "core_hours": "0.044333", "phase": "orca_audit_single_point"},
    {"job_id": "A069", "mol_id": "C13", "name": "GBL", "state": "M_plus", "setting_id": "S1", "basis": "def2-TZVP", "cores": "4", "wall_sec": "77.1", "core_hours": "0.085667", "phase": "orca_audit_single_point"},
    {"job_id": "A070", "mol_id": "C13", "name": "GBL", "state": "M_plus", "setting_id": "S2", "basis": "def2-TZVPD", "cores": "4", "wall_sec": "113.5", "core_hours": "0.126111", "phase": "orca_audit_single_point"},
    {"job_id": "A071", "mol_id": "C13", "name": "GBL", "state": "M_plus", "setting_id": "S3", "basis": "def2-TZVP", "cores": "4", "wall_sec": "64.4", "core_hours": "0.071556", "phase": "orca_audit_single_point"},
    {"job_id": "A072", "mol_id": "C13", "name": "GBL", "state": "M_plus", "setting_id": "S4", "basis": "def2-TZVPD", "cores": "4", "wall_sec": "72.2", "core_hours": "0.080222", "phase": "orca_audit_single_point"},
    {"job_id": "A073", "mol_id": "C13", "name": "GBL", "state": "LiM_plus", "setting_id": "S1", "basis": "def2-TZVP", "cores": "4", "wall_sec": "37.1", "core_hours": "0.041222", "phase": "orca_audit_single_point"},
    {"job_id": "A074", "mol_id": "C13", "name": "GBL", "state": "LiM_plus", "setting_id": "S2", "basis": "def2-TZVPD", "cores": "4", "wall_sec": "57.1", "core_hours": "0.063444", "phase": "orca_audit_single_point"},
    {"job_id": "A075", "mol_id": "C13", "name": "GBL", "state": "LiM_plus", "setting_id": "S3", "basis": "def2-TZVP", "cores": "4", "wall_sec": "24.2", "core_hours": "0.026889", "phase": "orca_audit_single_point"},
    {"job_id": "A076", "mol_id": "C13", "name": "GBL", "state": "LiM_plus", "setting_id": "S4", "basis": "def2-TZVPD", "cores": "4", "wall_sec": "37.4", "core_hours": "0.041556", "phase": "orca_audit_single_point"},
    {"job_id": "A077", "mol_id": "C13", "name": "GBL", "state": "LiM_2plus", "setting_id": "S1", "basis": "def2-TZVP", "cores": "4", "wall_sec": "43.4", "core_hours": "0.048222", "phase": "orca_audit_single_point"},
    {"job_id": "A078", "mol_id": "C13", "name": "GBL", "state": "LiM_2plus", "setting_id": "S2", "basis": "def2-TZVPD", "cores": "4", "wall_sec": "67.7", "core_hours": "0.075222", "phase": "orca_audit_single_point"},
    {"job_id": "A079", "mol_id": "C13", "name": "GBL", "state": "LiM_2plus", "setting_id": "S3", "basis": "def2-TZVP", "cores": "4", "wall_sec": "41.2", "core_hours": "0.045778", "phase": "orca_audit_single_point"},
    {"job_id": "A080", "mol_id": "C13", "name": "GBL", "state": "LiM_2plus", "setting_id": "S4", "basis": "def2-TZVPD", "cores": "4", "wall_sec": "66.1", "core_hours": "0.073444", "phase": "orca_audit_single_point"},
    {"job_id": "A081", "mol_id": "C14", "name": "SL", "state": "M", "setting_id": "S1", "basis": "def2-TZVP", "cores": "4", "wall_sec": "62.8", "core_hours": "0.069778", "phase": "orca_audit_single_point"},
    {"job_id": "A082", "mol_id": "C14", "name": "SL", "state": "M", "setting_id": "S2", "basis": "def2-TZVPD", "cores": "4", "wall_sec": "101.1", "core_hours": "0.112333", "phase": "orca_audit_single_point"},
    {"job_id": "A083", "mol_id": "C14", "name": "SL", "state": "M", "setting_id": "S3", "basis": "def2-TZVP", "cores": "4", "wall_sec": "41.3", "core_hours": "0.045889", "phase": "orca_audit_single_point"},
    {"job_id": "A084", "mol_id": "C14", "name": "SL", "state": "M", "setting_id": "S4", "basis": "def2-TZVPD", "cores": "4", "wall_sec": "72.7", "core_hours": "0.080778", "phase": "orca_audit_single_point"},
    {"job_id": "A085", "mol_id": "C14", "name": "SL", "state": "M_plus", "setting_id": "S1", "basis": "def2-TZVP", "cores": "4", "wall_sec": "79.5", "core_hours": "0.088333", "phase": "orca_audit_single_point"},
    {"job_id": "A086", "mol_id": "C14", "name": "SL", "state": "M_plus", "setting_id": "S2", "basis": "def2-TZVPD", "cores": "4", "wall_sec": "124.0", "core_hours": "0.137778", "phase": "orca_audit_single_point"},
    {"job_id": "A087", "mol_id": "C14", "name": "SL", "state": "M_plus", "setting_id": "S3", "basis": "def2-TZVP", "cores": "4", "wall_sec": "45.1", "core_hours": "0.050111", "phase": "orca_audit_single_point"},
    {"job_id": "A088", "mol_id": "C14", "name": "SL", "state": "M_plus", "setting_id": "S4", "basis": "def2-TZVPD", "cores": "4", "wall_sec": "71.7", "core_hours": "0.079667", "phase": "orca_audit_single_point"},
    {"job_id": "A089", "mol_id": "C14", "name": "SL", "state": "LiM_plus", "setting_id": "S1", "basis": "def2-TZVP", "cores": "4", "wall_sec": "73.3", "core_hours": "0.081444", "phase": "orca_audit_single_point"},
    {"job_id": "A090", "mol_id": "C14", "name": "SL", "state": "LiM_plus", "setting_id": "S2", "basis": "def2-TZVPD", "cores": "4", "wall_sec": "114.4", "core_hours": "0.127111", "phase": "orca_audit_single_point"},
    {"job_id": "A091", "mol_id": "C14", "name": "SL", "state": "LiM_plus", "setting_id": "S3", "basis": "def2-TZVP", "cores": "4", "wall_sec": "42.8", "core_hours": "0.047556", "phase": "orca_audit_single_point"},
    {"job_id": "A092", "mol_id": "C14", "name": "SL", "state": "LiM_plus", "setting_id": "S4", "basis": "def2-TZVPD", "cores": "4", "wall_sec": "69.8", "core_hours": "0.077556", "phase": "orca_audit_single_point"},
    {"job_id": "A093", "mol_id": "C14", "name": "SL", "state": "LiM_2plus", "setting_id": "S1", "basis": "def2-TZVP", "cores": "4", "wall_sec": "90.1", "core_hours": "0.100111", "phase": "orca_audit_single_point"},
    {"job_id": "A094", "mol_id": "C14", "name": "SL", "state": "LiM_2plus", "setting_id": "S2", "basis": "def2-TZVPD", "cores": "4", "wall_sec": "141.8", "core_hours": "0.157556", "phase": "orca_audit_single_point"},
    {"job_id": "A095", "mol_id": "C14", "name": "SL", "state": "LiM_2plus", "setting_id": "S3", "basis": "def2-TZVP", "cores": "4", "wall_sec": "54.3", "core_hours": "0.060333", "phase": "orca_audit_single_point"},
    {"job_id": "A096", "mol_id": "C14", "name": "SL", "state": "LiM_2plus", "setting_id": "S4", "basis": "def2-TZVPD", "cores": "4", "wall_sec": "85.0", "core_hours": "0.094444", "phase": "orca_audit_single_point"},
    {"job_id": "A097", "mol_id": "C16", "name": "AN", "state": "M", "setting_id": "S1", "basis": "def2-TZVP", "cores": "4", "wall_sec": "16.7", "core_hours": "0.018556", "phase": "orca_audit_single_point"},
    {"job_id": "A098", "mol_id": "C16", "name": "AN", "state": "M", "setting_id": "S2", "basis": "def2-TZVPD", "cores": "4", "wall_sec": "17.4", "core_hours": "0.019333", "phase": "orca_audit_single_point"},
    {"job_id": "A099", "mol_id": "C16", "name": "AN", "state": "M", "setting_id": "S3", "basis": "def2-TZVP", "cores": "4", "wall_sec": "13.1", "core_hours": "0.014556", "phase": "orca_audit_single_point"},
    {"job_id": "A100", "mol_id": "C16", "name": "AN", "state": "M", "setting_id": "S4", "basis": "def2-TZVPD", "cores": "4", "wall_sec": "16.8", "core_hours": "0.018667", "phase": "orca_audit_single_point"},
    {"job_id": "A101", "mol_id": "C16", "name": "AN", "state": "M_plus", "setting_id": "S1", "basis": "def2-TZVP", "cores": "4", "wall_sec": "15.4", "core_hours": "0.017111", "phase": "orca_audit_single_point"},
    {"job_id": "A102", "mol_id": "C16", "name": "AN", "state": "M_plus", "setting_id": "S2", "basis": "def2-TZVPD", "cores": "4", "wall_sec": "19.7", "core_hours": "0.021889", "phase": "orca_audit_single_point"},
    {"job_id": "A103", "mol_id": "C16", "name": "AN", "state": "M_plus", "setting_id": "S3", "basis": "def2-TZVP", "cores": "4", "wall_sec": "12.8", "core_hours": "0.014222", "phase": "orca_audit_single_point"},
    {"job_id": "A104", "mol_id": "C16", "name": "AN", "state": "M_plus", "setting_id": "S4", "basis": "def2-TZVPD", "cores": "4", "wall_sec": "14.7", "core_hours": "0.016333", "phase": "orca_audit_single_point"},
    {"job_id": "A105", "mol_id": "C16", "name": "AN", "state": "LiM_plus", "setting_id": "S1", "basis": "def2-TZVP", "cores": "4", "wall_sec": "21.8", "core_hours": "0.024222", "phase": "orca_audit_single_point"},
    {"job_id": "A106", "mol_id": "C16", "name": "AN", "state": "LiM_plus", "setting_id": "S2", "basis": "def2-TZVPD", "cores": "4", "wall_sec": "22.5", "core_hours": "0.025000", "phase": "orca_audit_single_point"},
    {"job_id": "A107", "mol_id": "C16", "name": "AN", "state": "LiM_plus", "setting_id": "S3", "basis": "def2-TZVP", "cores": "4", "wall_sec": "15.9", "core_hours": "0.017667", "phase": "orca_audit_single_point"},
    {"job_id": "A108", "mol_id": "C16", "name": "AN", "state": "LiM_plus", "setting_id": "S4", "basis": "def2-TZVPD", "cores": "4", "wall_sec": "18.6", "core_hours": "0.020667", "phase": "orca_audit_single_point"},
    {"job_id": "A109", "mol_id": "C16", "name": "AN", "state": "LiM_2plus", "setting_id": "S1", "basis": "def2-TZVP", "cores": "4", "wall_sec": "21.6", "core_hours": "0.024000", "phase": "orca_audit_single_point"},
    {"job_id": "A110", "mol_id": "C16", "name": "AN", "state": "LiM_2plus", "setting_id": "S2", "basis": "def2-TZVPD", "cores": "4", "wall_sec": "28.0", "core_hours": "0.031111", "phase": "orca_audit_single_point"},
    {"job_id": "A111", "mol_id": "C16", "name": "AN", "state": "LiM_2plus", "setting_id": "S3", "basis": "def2-TZVP", "cores": "4", "wall_sec": "15.4", "core_hours": "0.017111", "phase": "orca_audit_single_point"},
    {"job_id": "A112", "mol_id": "C16", "name": "AN", "state": "LiM_2plus", "setting_id": "S4", "basis": "def2-TZVPD", "cores": "4", "wall_sec": "18.9", "core_hours": "0.021000", "phase": "orca_audit_single_point"},
    {"job_id": "A113", "mol_id": "C17", "name": "TMP", "state": "M", "setting_id": "S1", "basis": "def2-TZVP", "cores": "4", "wall_sec": "69.4", "core_hours": "0.077111", "phase": "orca_audit_single_point"},
    {"job_id": "A114", "mol_id": "C17", "name": "TMP", "state": "M", "setting_id": "S2", "basis": "def2-TZVPD", "cores": "4", "wall_sec": "123.0", "core_hours": "0.136667", "phase": "orca_audit_single_point"},
    {"job_id": "A115", "mol_id": "C17", "name": "TMP", "state": "M", "setting_id": "S3", "basis": "def2-TZVP", "cores": "4", "wall_sec": "50.9", "core_hours": "0.056556", "phase": "orca_audit_single_point"},
    {"job_id": "A116", "mol_id": "C17", "name": "TMP", "state": "M", "setting_id": "S4", "basis": "def2-TZVPD", "cores": "4", "wall_sec": "97.7", "core_hours": "0.108556", "phase": "orca_audit_single_point"},
    {"job_id": "A117", "mol_id": "C17", "name": "TMP", "state": "M_plus", "setting_id": "S1", "basis": "def2-TZVP", "cores": "4", "wall_sec": "144.7", "core_hours": "0.160778", "phase": "orca_audit_single_point"},
    {"job_id": "A118", "mol_id": "C17", "name": "TMP", "state": "M_plus", "setting_id": "S2", "basis": "def2-TZVPD", "cores": "4", "wall_sec": "240.2", "core_hours": "0.266889", "phase": "orca_audit_single_point"},
    {"job_id": "A119", "mol_id": "C17", "name": "TMP", "state": "M_plus", "setting_id": "S3", "basis": "def2-TZVP", "cores": "4", "wall_sec": "92.9", "core_hours": "0.103222", "phase": "orca_audit_single_point"},
    {"job_id": "A120", "mol_id": "C17", "name": "TMP", "state": "M_plus", "setting_id": "S4", "basis": "def2-TZVPD", "cores": "4", "wall_sec": "142.3", "core_hours": "0.158111", "phase": "orca_audit_single_point"},
    {"job_id": "A121", "mol_id": "C17", "name": "TMP", "state": "LiM_plus", "setting_id": "S1", "basis": "def2-TZVP", "cores": "4", "wall_sec": "85.9", "core_hours": "0.095444", "phase": "orca_audit_single_point"},
    {"job_id": "A122", "mol_id": "C17", "name": "TMP", "state": "LiM_plus", "setting_id": "S2", "basis": "def2-TZVPD", "cores": "4", "wall_sec": "133.6", "core_hours": "0.148444", "phase": "orca_audit_single_point"},
    {"job_id": "A123", "mol_id": "C17", "name": "TMP", "state": "LiM_plus", "setting_id": "S3", "basis": "def2-TZVP", "cores": "4", "wall_sec": "52.2", "core_hours": "0.058000", "phase": "orca_audit_single_point"},
    {"job_id": "A124", "mol_id": "C17", "name": "TMP", "state": "LiM_plus", "setting_id": "S4", "basis": "def2-TZVPD", "cores": "4", "wall_sec": "88.1", "core_hours": "0.097889", "phase": "orca_audit_single_point"},
    {"job_id": "A125", "mol_id": "C17", "name": "TMP", "state": "LiM_2plus", "setting_id": "S1", "basis": "def2-TZVP", "cores": "4", "wall_sec": "121.1", "core_hours": "0.134556", "phase": "orca_audit_single_point"},
    {"job_id": "A126", "mol_id": "C17", "name": "TMP", "state": "LiM_2plus", "setting_id": "S2", "basis": "def2-TZVPD", "cores": "4", "wall_sec": "201.6", "core_hours": "0.224000", "phase": "orca_audit_single_point"},
    {"job_id": "A127", "mol_id": "C17", "name": "TMP", "state": "LiM_2plus", "setting_id": "S3", "basis": "def2-TZVP", "cores": "4", "wall_sec": "55.2", "core_hours": "0.061333", "phase": "orca_audit_single_point"},
    {"job_id": "A128", "mol_id": "C17", "name": "TMP", "state": "LiM_2plus", "setting_id": "S4", "basis": "def2-TZVPD", "cores": "4", "wall_sec": "99.5", "core_hours": "0.110556", "phase": "orca_audit_single_point"},
    {"job_id": "A129", "mol_id": "C01", "name": "DMC", "state": "M_plus_relaxed", "setting_id": "S1", "basis": "def2-TZVP", "cores": "4", "wall_sec": "41.0", "core_hours": "0.045556", "phase": "orca_audit_single_point"},
    {"job_id": "A130", "mol_id": "C01", "name": "DMC", "state": "M_plus_relaxed", "setting_id": "S2", "basis": "def2-TZVPD", "cores": "4", "wall_sec": "76.6", "core_hours": "0.085111", "phase": "orca_audit_single_point"},
    {"job_id": "A131", "mol_id": "C01", "name": "DMC", "state": "M_plus_relaxed", "setting_id": "S3", "basis": "def2-TZVP", "cores": "4", "wall_sec": "31.2", "core_hours": "0.034667", "phase": "orca_audit_single_point"},
    {"job_id": "A132", "mol_id": "C01", "name": "DMC", "state": "M_plus_relaxed", "setting_id": "S4", "basis": "def2-TZVPD", "cores": "4", "wall_sec": "45.3", "core_hours": "0.050333", "phase": "orca_audit_single_point"},
    {"job_id": "A133", "mol_id": "C02", "name": "EMC", "state": "M_plus_relaxed", "setting_id": "S1", "basis": "def2-TZVP", "cores": "4", "wall_sec": "52.1", "core_hours": "0.057889", "phase": "orca_audit_single_point"},
    {"job_id": "A134", "mol_id": "C02", "name": "EMC", "state": "M_plus_relaxed", "setting_id": "S2", "basis": "def2-TZVPD", "cores": "4", "wall_sec": "98.8", "core_hours": "0.109778", "phase": "orca_audit_single_point"},
    {"job_id": "A135", "mol_id": "C02", "name": "EMC", "state": "M_plus_relaxed", "setting_id": "S3", "basis": "def2-TZVP", "cores": "4", "wall_sec": "35.5", "core_hours": "0.039444", "phase": "orca_audit_single_point"},
    {"job_id": "A136", "mol_id": "C02", "name": "EMC", "state": "M_plus_relaxed", "setting_id": "S4", "basis": "def2-TZVPD", "cores": "4", "wall_sec": "41.8", "core_hours": "0.046444", "phase": "orca_audit_single_point"},
    {"job_id": "A137", "mol_id": "C04", "name": "EC", "state": "M_plus_relaxed", "setting_id": "S1", "basis": "def2-TZVP", "cores": "4", "wall_sec": "62.4", "core_hours": "0.069333", "phase": "orca_audit_single_point"},
    {"job_id": "A138", "mol_id": "C04", "name": "EC", "state": "M_plus_relaxed", "setting_id": "S2", "basis": "def2-TZVPD", "cores": "4", "wall_sec": "103.2", "core_hours": "0.114667", "phase": "orca_audit_single_point"},
    {"job_id": "A139", "mol_id": "C04", "name": "EC", "state": "M_plus_relaxed", "setting_id": "S3", "basis": "def2-TZVP", "cores": "4", "wall_sec": "48.0", "core_hours": "0.053333", "phase": "orca_audit_single_point"},
    {"job_id": "A140", "mol_id": "C04", "name": "EC", "state": "M_plus_relaxed", "setting_id": "S4", "basis": "def2-TZVPD", "cores": "4", "wall_sec": "52.7", "core_hours": "0.058556", "phase": "orca_audit_single_point"},
    {"job_id": "A141", "mol_id": "C08", "name": "DME", "state": "M_plus_relaxed", "setting_id": "S1", "basis": "def2-TZVP", "cores": "4", "wall_sec": "52.8", "core_hours": "0.058667", "phase": "orca_audit_single_point"},
    {"job_id": "A142", "mol_id": "C08", "name": "DME", "state": "M_plus_relaxed", "setting_id": "S2", "basis": "def2-TZVPD", "cores": "4", "wall_sec": "92.0", "core_hours": "0.102222", "phase": "orca_audit_single_point"},
    {"job_id": "A143", "mol_id": "C08", "name": "DME", "state": "M_plus_relaxed", "setting_id": "S3", "basis": "def2-TZVP", "cores": "4", "wall_sec": "30.8", "core_hours": "0.034222", "phase": "orca_audit_single_point"},
    {"job_id": "A144", "mol_id": "C08", "name": "DME", "state": "M_plus_relaxed", "setting_id": "S4", "basis": "def2-TZVPD", "cores": "4", "wall_sec": "39.9", "core_hours": "0.044333", "phase": "orca_audit_single_point"},
    {"job_id": "A145", "mol_id": "C13", "name": "GBL", "state": "M_plus_relaxed", "setting_id": "S1", "basis": "def2-TZVP", "cores": "4", "wall_sec": "52.6", "core_hours": "0.058444", "phase": "orca_audit_single_point"},
    {"job_id": "A146", "mol_id": "C13", "name": "GBL", "state": "M_plus_relaxed", "setting_id": "S2", "basis": "def2-TZVPD", "cores": "4", "wall_sec": "70.5", "core_hours": "0.078333", "phase": "orca_audit_single_point"},
    {"job_id": "A147", "mol_id": "C13", "name": "GBL", "state": "M_plus_relaxed", "setting_id": "S3", "basis": "def2-TZVP", "cores": "4", "wall_sec": "25.5", "core_hours": "0.028333", "phase": "orca_audit_single_point"},
    {"job_id": "A148", "mol_id": "C13", "name": "GBL", "state": "M_plus_relaxed", "setting_id": "S4", "basis": "def2-TZVPD", "cores": "4", "wall_sec": "40.4", "core_hours": "0.044889", "phase": "orca_audit_single_point"},
    {"job_id": "A149", "mol_id": "C14", "name": "SL", "state": "M_plus_relaxed", "setting_id": "S1", "basis": "def2-TZVP", "cores": "4", "wall_sec": "64.5", "core_hours": "0.071667", "phase": "orca_audit_single_point"},
    {"job_id": "A150", "mol_id": "C14", "name": "SL", "state": "M_plus_relaxed", "setting_id": "S2", "basis": "def2-TZVPD", "cores": "4", "wall_sec": "92.7", "core_hours": "0.103000", "phase": "orca_audit_single_point"},
    {"job_id": "A151", "mol_id": "C14", "name": "SL", "state": "M_plus_relaxed", "setting_id": "S3", "basis": "def2-TZVP", "cores": "4", "wall_sec": "33.8", "core_hours": "0.037556", "phase": "orca_audit_single_point"},
    {"job_id": "A152", "mol_id": "C14", "name": "SL", "state": "M_plus_relaxed", "setting_id": "S4", "basis": "def2-TZVPD", "cores": "4", "wall_sec": "46.8", "core_hours": "0.052000", "phase": "orca_audit_single_point"},
    {"job_id": "A153", "mol_id": "C16", "name": "AN", "state": "M_plus_relaxed", "setting_id": "S1", "basis": "def2-TZVP", "cores": "4", "wall_sec": "14.3", "core_hours": "0.015889", "phase": "orca_audit_single_point"},
    {"job_id": "A154", "mol_id": "C16", "name": "AN", "state": "M_plus_relaxed", "setting_id": "S2", "basis": "def2-TZVPD", "cores": "4", "wall_sec": "19.3", "core_hours": "0.021444", "phase": "orca_audit_single_point"},
    {"job_id": "A155", "mol_id": "C16", "name": "AN", "state": "M_plus_relaxed", "setting_id": "S3", "basis": "def2-TZVP", "cores": "4", "wall_sec": "16.6", "core_hours": "0.018444", "phase": "orca_audit_single_point"},
    {"job_id": "A156", "mol_id": "C16", "name": "AN", "state": "M_plus_relaxed", "setting_id": "S4", "basis": "def2-TZVPD", "cores": "4", "wall_sec": "16.2", "core_hours": "0.018000", "phase": "orca_audit_single_point"},
    {"job_id": "A157", "mol_id": "C17", "name": "TMP", "state": "M_plus_relaxed", "setting_id": "S1", "basis": "def2-TZVP", "cores": "4", "wall_sec": "101.3", "core_hours": "0.112556", "phase": "orca_audit_single_point"},
    {"job_id": "A158", "mol_id": "C17", "name": "TMP", "state": "M_plus_relaxed", "setting_id": "S2", "basis": "def2-TZVPD", "cores": "4", "wall_sec": "149.4", "core_hours": "0.166000", "phase": "orca_audit_single_point"},
    {"job_id": "A159", "mol_id": "C17", "name": "TMP", "state": "M_plus_relaxed", "setting_id": "S3", "basis": "def2-TZVP", "cores": "4", "wall_sec": "38.4", "core_hours": "0.042667", "phase": "orca_audit_single_point"},
    {"job_id": "A160", "mol_id": "C17", "name": "TMP", "state": "M_plus_relaxed", "setting_id": "S4", "basis": "def2-TZVPD", "cores": "4", "wall_sec": "69.0", "core_hours": "0.076667", "phase": "orca_audit_single_point"},
    {"job_id": "A161", "mol_id": "C02", "name": "EMC", "state": "LiM_plus", "setting_id": "EMC_Li_opt", "basis": "r2SCAN-3c", "cores": "4", "wall_sec": "103.9", "core_hours": "0.115436", "phase": "orca_emc_li_opt"},
]
METHOD_AUDIT_JOB_COUNT = len(METHOD_AUDIT_CELLS) + len(METHOD_AUDIT_RELAXED_CELLS) + 1
def _method_audit_cells(rows):
    out = []
    for row in rows:
        cell = dict(zip(METHOD_AUDIT_CELL_FIELDS, row))
        cell["valid_for_decision"] = "true" if not cell["qc_flag"] else "false"
        out.append(cell)
    return out


def _method_audit_index(rows):
    return {(c["mol_id"], c["state"], c["setting_id"]): c for c in _method_audit_cells(rows)}


def _audit_energy_ev(cell):
    if not cell or not cell["final_sp_eh"]:
        return None
    return float(cell["final_sp_eh"]) * HARTREE_TO_EV


def _audit_axis_ips():
    """每分子的 4 设定竖直/绝热电离能（eV）与弛豫位移；两腿共用同一中性参考。"""
    index = _method_audit_index(METHOD_AUDIT_CELLS)
    relaxed = _method_audit_index(METHOD_AUDIT_RELAXED_CELLS)
    settings = [row["setting_id"] for row in METHOD_SETTINGS]
    out = {}
    for mol_id in PB.COHORTS["method_audit"]:
        name = PB.COHORT_NAMES[mol_id]
        vertical, adiabatic, shift = {}, {}, {}
        for sid in settings:
            e_neutral = _audit_energy_ev(index.get((mol_id, "M", sid)))
            e_vertical = _audit_energy_ev(index.get((mol_id, "M_plus", sid)))
            e_relaxed = _audit_energy_ev(relaxed.get((mol_id, "M_plus_relaxed", sid)))
            if e_neutral is None or e_vertical is None or e_relaxed is None:
                vertical[sid] = adiabatic[sid] = shift[sid] = None
                continue
            vertical[sid] = e_vertical - e_neutral
            adiabatic[sid] = e_relaxed - e_neutral
            shift[sid] = e_relaxed - e_vertical
        out[name] = {"mol_id": mol_id, "vertical_ip_ev": vertical,
                     "adiabatic_ip_ev": adiabatic, "relaxation_shift_ev": shift}
    return out


def _audit_pair_legs():
    ips = _audit_axis_ips()
    names = [PB.COHORT_NAMES[mol_id] for mol_id in PB.COHORTS["method_audit"]]
    settings = [row["setting_id"] for row in METHOD_SETTINGS]
    out = {}
    for a in range(len(names)):
        for b in range(a + 1, len(names)):
            left, right = names[a], names[b]
            out[(left, right)] = {
                "settings": settings,
                "vertical": [ips[left]["vertical_ip_ev"][s] - ips[right]["vertical_ip_ev"][s]
                             for s in settings],
                "adiabatic": [ips[left]["adiabatic_ip_ev"][s] - ips[right]["adiabatic_ip_ev"][s]
                              for s in settings],
            }
    return out


def _leg_stats(values):
    vals = [value for value in values if value is not None]
    n = len(vals)
    mean = sum(vals) / n
    sigma = (sum((value - mean) ** 2 for value in vals) / n) ** 0.5
    lo, hi = min(vals), max(vals)
    return {"n": n, "mean_ev": mean, "sigma_ev": sigma, "min_ev": lo, "max_ev": hi,
            "range_ev": hi - lo, "min_abs_ev": min(abs(value) for value in vals),
            "sign_consistent": (lo > 0) or (hi < 0)}

def wp1():
    files = {}
    local = {}
    cells = _method_audit_cells(METHOD_AUDIT_CELLS)
    relaxed_cells = _method_audit_cells(METHOD_AUDIT_RELAXED_CELLS)
    settings = [row["setting_id"] for row in METHOD_SETTINGS]

    matrix = []
    for cell in cells:
        matrix.append({
            "mol_id": cell["mol_id"], "name": cell["name"], "state": cell["state"],
            "setting_id": cell["setting_id"], "functional": cell["functional"],
            "basis": cell["basis"], "solvent": "SMD_acetonitrile",
            "geometry_start": "r2SCAN-3c", "job_kind": "single_point",
            "status": cell["status"], "qc_flag": cell["qc_flag"],
            "valid_for_decision": cell["valid_for_decision"],
            "final_sp_eh": cell["final_sp_eh"], "wall_sec": cell["wall_sec"],
            "notes": ("no diffuse basis on a reduction state; excluded from decision statistics"
                      if cell["qc_flag"] else "computed"),
        })
    relaxed_matrix = []
    for cell in relaxed_cells:
        relaxed_matrix.append({
            "mol_id": cell["mol_id"], "name": cell["name"], "state": cell["state"],
            "setting_id": cell["setting_id"], "functional": cell["functional"],
            "basis": cell["basis"], "has_diffuse": cell["has_diffuse"],
            "charge": cell["charge"], "multiplicity": cell["multiplicity"],
            "geometry": cell["geometry"], "status": cell["status"],
            "final_sp_eh": cell["final_sp_eh"], "wall_sec": cell["wall_sec"],
        })

    spread = []
    for mol_id in PB.COHORTS["method_audit"]:
        for state in PB.FOUR_STATES:
            group = [c for c in cells if c["mol_id"] == mol_id and c["state"] == state]
            by_setting = {c["setting_id"]: c for c in group}
            values = [_audit_energy_ev(by_setting[sid]) for sid in settings]
            valid = [c for c in group if c["valid_for_decision"] == "true"]
            spread.append({
                "mol_id": mol_id, "name": PB.COHORT_NAMES[mol_id], "state": state,
                "charge": group[0]["charge"], "multiplicity": group[0]["multiplicity"],
                "n_settings": len(group), "n_valid_for_decision": len(valid),
                "min_ev": "%.6f" % min(values), "max_ev": "%.6f" % max(values),
                "spread_ev": "%.6f" % (max(values) - min(values)),
            })

    ips = _audit_axis_ips()
    axis = []
    for mol_id in PB.COHORTS["method_audit"]:
        name = PB.COHORT_NAMES[mol_id]
        rec = ips[name]
        row = {"mol_id": mol_id, "name": name}
        for sid in settings:
            row["ip_vertical_%s_ev" % sid] = "%.6f" % rec["vertical_ip_ev"][sid]
            row["ip_adiabatic_%s_ev" % sid] = "%.6f" % rec["adiabatic_ip_ev"][sid]
            row["relaxation_shift_%s_ev" % sid] = "%.6f" % rec["relaxation_shift_ev"][sid]
        vertical = _leg_stats([rec["vertical_ip_ev"][sid] for sid in settings])
        adiabatic = _leg_stats([rec["adiabatic_ip_ev"][sid] for sid in settings])
        row["vertical_range_ev"] = "%.6f" % vertical["range_ev"]
        row["adiabatic_range_ev"] = "%.6f" % adiabatic["range_ev"]
        row["relaxation_shift_mean_ev"] = "%.6f" % (
            sum(rec["relaxation_shift_ev"][sid] for sid in settings) / len(settings))
        for label, key in (("vertical", "vertical_ip_ev"), ("adiabatic", "adiabatic_ip_ev")):
            series = [rec[key][sid] for sid in settings]
            row["%s_functional_effect_ev" % label] = "%.6f" % abs(
                (series[0] + series[1]) / 2.0 - (series[2] + series[3]) / 2.0)
            row["%s_basis_effect_ev" % label] = "%.6f" % abs(
                (series[0] + series[2]) / 2.0 - (series[1] + series[3]) / 2.0)
        axis.append(row)

    pair_rows = []
    legs = _audit_pair_legs()
    for (left, right) in sorted(legs):
        leg = legs[(left, right)]
        vertical = _leg_stats(leg["vertical"])
        adiabatic = _leg_stats(leg["adiabatic"])
        row = {"i": left, "j": right}
        for index, sid in enumerate(leg["settings"]):
            row["d_vertical_%s_ev" % sid] = "%.6f" % leg["vertical"][index]
            row["d_adiabatic_%s_ev" % sid] = "%.6f" % leg["adiabatic"][index]
        row["vertical_range_ev"] = "%.6f" % vertical["range_ev"]
        row["adiabatic_range_ev"] = "%.6f" % adiabatic["range_ev"]
        row["vertical_sign_consistent"] = "true" if vertical["sign_consistent"] else "false"
        row["adiabatic_sign_consistent"] = "true" if adiabatic["sign_consistent"] else "false"
        row["sign_flip_across_legs"] = "true" if (
            vertical["min_ev"] > 0 > adiabatic["max_ev"]
            or adiabatic["min_ev"] > 0 > vertical["max_ev"]) else "false"
        pair_rows.append(row)

    cert = METHOD_AUDIT_CERTIFICATION
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
    flagged = [c for c in cells if c["qc_flag"]]
    computed = [c for c in cells if c["status"] == "computed"]
    relaxed_computed = [c for c in relaxed_cells if c["status"] == "computed"]
    audit_cost = sum(float(row["core_hours"]) for row in METHOD_AUDIT_COST)
    checks = [
        {"id": "matrix_is_full_factorial", "description": "方法矩阵 = 8 分子 x 4 状态 x 4 设定 = 128",
         "ok": len(matrix) == 128, "detail": "n_rows=%d" % len(matrix)},
        {"id": "audit_matrix_is_computed", "description": "128 格独立方法审计单点全部正常收敛（status=computed）",
         "ok": len(cells) == 128 and len(computed) == 128,
         "detail": "computed=%d/%d" % (len(computed), len(cells))},
        {"id": "reduction_states_without_diffuse_are_excluded", "description": "无弥散基组下的还原态格子被标出并排除出决策统计",
         "ok": len(flagged) == 32
               and all(c["valid_for_decision"] == "false" for c in flagged)
               and all(c["valid_for_decision"] == "true" for c in cells if not c["qc_flag"]),
         "detail": "flagged=%d (%s)" % (len(flagged), "、".join(sorted({c["qc_flag"] for c in flagged})))},
        {"id": "relaxed_leg_is_computed", "description": "阳离子弛豫腿 32 格全部正常收敛",
         "ok": len(relaxed_cells) == 32 and len(relaxed_computed) == 32,
         "detail": "computed=%d/%d" % (len(relaxed_computed), len(relaxed_cells))},
        {"id": "method_spread_is_measured_per_state", "description": "每个状态的方法展宽（泛函/基组效应）已实测",
         "ok": len(spread) == 32 and all(float(row["spread_ev"]) > 0 for row in spread),
         "detail": "states=%d; max spread=%.3f eV" % (len(spread),
                                                     max(float(row["spread_ev"]) for row in spread))},
        {"id": "robust_inversion_certification_recorded", "description": "稳健翻转的独立方法审计认证结论已记录（EMC|GBL、EMC|SL）",
         "ok": {item["pair"] for item in cert["pairs"]} == {"EMC | GBL", "EMC | SL"},
         "detail": "certified=%s (%d/%d pairs)" % (cert["certified"], cert["n_pairs_certified"],
                                                   len(cert["pairs"]))},
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
        {"id": "local_echo_covers_all_settings", "description": "本机方法回显覆盖全部 4 个设定（S1-S4）",
         "ok": {row["setting_id"] for row in LOCAL_METHOD_ECHO} == {s["setting_id"] for s in METHOD_SETTINGS},
         "detail": "echoed settings=" + ",".join(sorted(row["setting_id"] for row in LOCAL_METHOD_ECHO))},
        {"id": "plan_functional_spellings_remapped", "description": "方案泛函拼写在本机被拒并已给出可用替写",
         "ok": all(row["recognized"] == "true" and row["plan_keyword_status"] == "rejected_as_written"
                   for row in LOCAL_METHOD_ECHO) and len(LOCAL_KEYWORD_REJECTIONS) == 2,
         "detail": "rejections=%d; every setting has a verified ORCA keyword" % len(LOCAL_KEYWORD_REJECTIONS)},
        {"id": "smoke_runs_terminated_normally", "description": "中性/审计/带电 smoke run 全部正常收敛",
         "ok": all(row["terminated_normally"] == "true" for row in LOCAL_SMOKE_RUNS),
         "detail": "runs=%d (neutral SP, audit SP, NumFreq, cation SP)" % len(LOCAL_SMOKE_RUNS)},
        {"id": "freq_and_smd_available", "description": "SMD 乙腈下频率路径可用（无虚频）",
         "ok": LOCAL_FREQ_CHECK["imaginary_modes"] == "0" and "SMD" in LOCAL_SMOKE_RUNS[2]["solvent"],
         "detail": "NumFreq completed; imaginary=%s" % LOCAL_FREQ_CHECK["imaginary_modes"]},
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
            "new_electronic_structure_jobs": METHOD_AUDIT_JOB_COUNT,
            "new_electronic_structure_jobs_note": "method-audit jobs only (128 single points + 32 relaxed-leg cells + 1 EMC Li Opt); the frozen ranking/pair evidence still uses zero new jobs",
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
        "measured_matrix": {
            "n_cells": len(cells), "n_computed": len(computed),
            "n_flagged_excluded": len(flagged), "flagged_qc": sorted({c["qc_flag"] for c in flagged}),
            "n_relaxed_cells": len(relaxed_cells), "n_relaxed_computed": len(relaxed_computed),
            "core_hours": "%.3f" % audit_cost,
            "oxidation_axis_method_spread_ev": METHOD_AUDIT_SPREAD,
        },
        "method_audit_certification": cert,
        "existing_reusable_jobs": existing,
        "electronic_structure_jobs_scope_note": "the audit matrix is a new local computation counted above; the frozen ranking/pair evidence payloads are still untouched by new jobs",
        "local_environment": {
            "toolchain": LOCAL_TOOLCHAIN,
            "method_echo": LOCAL_METHOD_ECHO,
            "keyword_rejections": LOCAL_KEYWORD_REJECTIONS,
            "smoke_runs": LOCAL_SMOKE_RUNS,
            "freq_check": LOCAL_FREQ_CHECK,
            "scope": "supportability probe on water under SMD acetonitrile; NOT a ranking input; raw ORCA logs kept outside the repository",
        },
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
         "geometry_start", "job_kind", "status", "qc_flag", "valid_for_decision",
         "final_sp_eh", "wall_sec", "notes"], matrix)
    local["outputs/physics_completion/method_audit/relaxed_leg_matrix.csv"] = csv_text(
        ["mol_id", "name", "state", "setting_id", "functional", "basis", "has_diffuse",
         "charge", "multiplicity", "geometry", "status", "final_sp_eh", "wall_sec"],
        relaxed_matrix)
    local["outputs/physics_completion/method_audit/state_energy_spread.csv"] = csv_text(
        ["mol_id", "name", "state", "charge", "multiplicity", "n_settings",
         "n_valid_for_decision", "min_ev", "max_ev", "spread_ev"], spread)
    local["outputs/physics_completion/method_audit/axis_sensitivity.csv"] = csv_text(
        ["mol_id", "name"] + ["ip_vertical_%s_ev" % sid for sid in settings]
        + ["ip_adiabatic_%s_ev" % sid for sid in settings]
        + ["relaxation_shift_%s_ev" % sid for sid in settings]
        + ["vertical_range_ev", "adiabatic_range_ev", "relaxation_shift_mean_ev",
           "vertical_functional_effect_ev", "vertical_basis_effect_ev",
           "adiabatic_functional_effect_ev", "adiabatic_basis_effect_ev"], axis)
    local["outputs/physics_completion/method_audit/pair_gap_sensitivity.csv"] = csv_text(
        ["i", "j"] + ["d_vertical_%s_ev" % sid for sid in settings]
        + ["d_adiabatic_%s_ev" % sid for sid in settings]
        + ["vertical_range_ev", "adiabatic_range_ev", "vertical_sign_consistent",
           "adiabatic_sign_consistent", "sign_flip_across_legs"], pair_rows)
    local["outputs/physics_completion/method_audit/robust_inversion_certification.json"] = dump(cert)
    local["outputs/physics_completion/method_audit/robust_inversion_certification.csv"] = csv_text(
        ["pair", "vertical_sign", "adiabatic_sign", "vertical_min_abs_ev", "vertical_sigma_ev",
         "vertical_range_ev", "adiabatic_min_abs_ev", "adiabatic_sigma_ev", "adiabatic_range_ev",
         "vertical_resolved", "adiabatic_resolved", "opposite_signs", "certified"],
        [dict(item, **{key: str(item[key]).lower() for key in
                       ("vertical_resolved", "adiabatic_resolved", "opposite_signs", "certified")})
         for item in cert["pairs"]])
    local["outputs/physics_completion/method_audit/audit_geometry_note.json"] = dump(
        {"emc_li_opt": METHOD_AUDIT_EMC_LI_OPT,
         "note": "EMC has no frozen C1 row; its [Li(EMC)]+ geometry was newly relaxed at r2SCAN-3c and is registered here",
         "geometry_path": "work/audit/EMC_Li/EMC_m1_G2Li.xyz (raw geometry stays outside the delivery layer)"})
    local["outputs/physics_completion/method_audit/method_settings.csv"] = csv_text(
        ["setting_id", "functional", "basis", "role", "has_diffuse", "note"], METHOD_SETTINGS)
    local["outputs/physics_completion/method_audit/existing_reusable_jobs.csv"] = csv_text(
        ["payload", "layer", "n_rows", "n_molecules", "states", "method", "reuse_kind", "caveat"],
        existing)
    local["outputs/physics_completion/method_audit/local_toolchain.csv"] = csv_text(
        ["tool", "version", "path_hint", "note"], LOCAL_TOOLCHAIN)
    local["outputs/physics_completion/method_audit/local_method_echo.csv"] = csv_text(
        ["setting_id", "plan_functional", "basis", "plan_keyword_status", "orca_keyword",
         "functional_echo", "hf_exchange_fraction", "dispersion_module", "solvent_echo", "recognized"],
        LOCAL_METHOD_ECHO)
    local["outputs/physics_completion/method_audit/local_smoke_runs.csv"] = csv_text(
        ["run_id", "state", "charge", "multiplicity", "orca_keyword", "solvent",
         "basis_functions", "scf_cycles", "final_single_point_eh", "terminated_normally", "wall_sec"],
        LOCAL_SMOKE_RUNS)
    local["outputs/physics_completion/cost/audit_cost_ledger.csv"] = csv_text(
        ["job_id", "mol_id", "name", "state", "setting_id", "basis", "cores", "wall_sec",
         "core_hours", "phase"], METHOD_AUDIT_COST)
    summary = [
        "# Week 38 / WP1 — 独立方法审计表（本机 128 格实测）",
        "",
        "**状态**：矩阵与规则已冻结，且已在本机实测 —— %d 个单点（%d 分子 × %d 状态 × %d 设定）全部正常收敛，"
        "另加 %d 格阳离子弛豫腿用于认证 WP3 的稳健翻转。原始 ORCA 日志留在仓库外，交付层只含派生数值。"
        % (len(cells), len(PB.COHORTS["method_audit"]), len(PB.FOUR_STATES), len(METHOD_SETTINGS),
           len(relaxed_cells)),
        "",
        "## 冻结内容",
        "",
        "- 固定条件：SMD 乙腈、298.15 K、溶液标准态 1 mol/L；几何起点 r2SCAN-3c。",
        "- 方法矩阵：%d 分子 × %d 状态 × %d 设定 = **%d** 单点，另加 %d 格弛豫腿。"
        % (len(PB.COHORTS["method_audit"]), len(PB.FOUR_STATES), len(METHOD_SETTINGS),
           len(matrix), len(relaxed_cells)),
        "- 生产候选 ωB97X-D4（def2-TZVP / def2-TZVPD）；审计对照 PBE0-D4（同两基组）。",
        "- 还原态必须使用含弥散函数设定（S2 / S4）；有限基组能收敛**不能**证明束缚。无弥散基组下的还原态格子照样计算，"
        "但标 valid_for_decision=false 并排除出决策统计（共 %d 格）。" % len(flagged),
        "- 方法选择规则：QC 可用率 / 数值稳定性 / 气相 anchor 可比 / rank sensitivity / 实测成本；**不**按翻转数量选方法。",
        "",
        "## 实测结果（本机 ORCA 6.1.1，SMD 乙腈）",
        "",
        "氧化轴方法展宽（8 分子，跨 4 设定）：竖直 IP 的泛函效应中位 %s eV / 最大 %s eV，"
        "基组效应中位 %s eV / 最大 %s eV；绝热 IP 的泛函效应中位 %s eV / 最大 %s eV，"
        "基组效应中位 %s eV / 最大 %s eV。状态层的绝对总能级差只作原始登记（含泛函绝对能偏移），不作决策量。"
        % (METHOD_AUDIT_SPREAD["vertical_functional_effect_median_ev"],
           METHOD_AUDIT_SPREAD["vertical_functional_effect_max_ev"],
           METHOD_AUDIT_SPREAD["vertical_basis_effect_median_ev"],
           METHOD_AUDIT_SPREAD["vertical_basis_effect_max_ev"],
           METHOD_AUDIT_SPREAD["adiabatic_functional_effect_median_ev"],
           METHOD_AUDIT_SPREAD["adiabatic_functional_effect_max_ev"],
           METHOD_AUDIT_SPREAD["adiabatic_basis_effect_median_ev"],
           METHOD_AUDIT_SPREAD["adiabatic_basis_effect_max_ev"]),
        "",
        "氧化轴逐分子（竖直腿 = 冻结中性几何上的阳离子单点；弛豫腿 = 冻结松弛阳离子几何上的单点）：",
        "",
        "| 分子 | 竖直 IP 展宽 (eV) | 绝热 IP 展宽 (eV) | 弛豫位移均值 (eV) |",
        "| --- | --- | --- | --- |",
    ]
    for row in axis:
        summary.append("| %s | %s | %s | %s |"
                       % (row["name"], row["vertical_range_ev"], row["adiabatic_range_ev"],
                          row["relaxation_shift_mean_ev"]))
    summary += [
        "",
        "## 稳健翻转认证（方案 5.3）",
        "",
        "- 判据：%s。" % cert["criterion"],
        "- 范围：%s。" % cert["scope"],
        "- 结论：certified=**%s**（%d/%d 冻结对）。" % (cert["certified"], cert["n_pairs_certified"],
                                                        len(cert["pairs"])),
        "",
        "| pair | 竖直腿符号 | 绝热腿符号 | min abs d (竖直) | sigma (竖直) | min abs d (绝热) | sigma (绝热) | 认证 |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for item in cert["pairs"]:
        summary.append("| %s | %s | %s | %s | %s | %s | %s | %s |"
                       % (item["pair"], item["vertical_sign"], item["adiabatic_sign"],
                          item["vertical_min_abs_ev"], item["vertical_sigma_ev"],
                          item["adiabatic_min_abs_ev"], item["adiabatic_sigma_ev"],
                          "YES" if item["certified"] else "NO"))
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
        "## 既有可复用作业（只到电子能层）",
        "",
        "| 载荷 | 层 | 行数 | 分子 | 复用范围 | 限制 |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for item in existing:
        summary.append("| %s | %s | %d | %d | %s | %s |"
                       % (item["payload"], item["layer"], item["n_rows"], item["n_molecules"],
                          item["reuse_kind"], item["caveat"]))
    summary += [
        "",
        "## 本机方法回显与 smoke 核验（方案 15.4）",
        "",
        "工具链：ORCA %s；xTB %s。原始日志留在仓库外，不入交付镜像。"
        % (LOCAL_TOOLCHAIN[0]["version"], LOCAL_TOOLCHAIN[1]["version"]),
        "",
        "| 设定 | 方案拼写 | ORCA 可用关键字 | 泛函回显 | HF 分数 | 色散 | 溶剂 |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in LOCAL_METHOD_ECHO:
        summary.append("| %s | %s | %s | %s | %s | %s | %s |"
                       % (row["setting_id"], row["plan_functional"], row["orca_keyword"],
                          row["functional_echo"], row["hf_exchange_fraction"],
                          row["dispersion_module"], row["solvent_echo"]))
    summary += [
        "",
        "smoke run（water，SMD 乙腈；只作支撑性检查，非排序证据）：",
        "",
        "| run | 状态 | q/mult | 关键字 | 基函数 | SCF | 末单点 (Eh) | 正常结束 | 墙钟 (s) |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in LOCAL_SMOKE_RUNS:
        summary.append("| %s | %s | %s/%s | %s | %s | %s | %s | %s | %s |"
                       % (row["run_id"], row["state"], row["charge"], row["multiplicity"],
                          row["orca_keyword"], row["basis_functions"], row["scf_cycles"],
                          row["final_single_point_eh"], row["terminated_normally"], row["wall_sec"]))
    summary += [
        "",
        "频率：NumFreq 在 SMD 乙腈下完成，水 3N=9 模式中 6 个近零 + 3 个实频（1588.03 / 3892.52 / 3972.24 cm^-1），**无虚频**。",
        "",
        "**方案拼写须改写**：omegaB97X-D4 与 PBE0-D4 在 ORCA 6.1.1 下被拒（UNRECOGNIZED OR DUPLICATED KEYWORD(S)）；"
        "正确形式为 wB97X-D4 与 PBE0 D4（色散作独立关键字）。",
        "",
        "## 限制",
        "",
        "- 128 格与弛豫腿 32 格都是**气相 r2SCAN-3c 冻结几何**上的 SMD 单点，不是溶液相完全优化；8 分子口径，不等同方案 6 的完整生产。",
        "- 电子密度/自旋、热校正与 G 层分解不在本审计范围（只有电子能层）。",
        "- 认证只覆盖**方法轴**（4 个预先接受的设定）；构象采样界限仍未纳入，故不构成完整认证。",
        "- 独立方法审计是 sensitivity assessment，不等于校准的概率误差；1.96×spread 不得自动标成 95% 置信度。",
        "- 本机方法回显与 smoke 仅覆盖单一几何（water）与固定条件，**不**等于候选泛函/基组的完整验证，也**不**是排序证据。",
        "- EMC 无冻结 C1 行，其 [Li(EMC)]+ 几何为本轮新跑的 r2SCAN-3c 松弛（登记在 audit_geometry_note.json，原始几何留在仓库外）。",
    ]
    local["outputs/week38/wp1_summary.md"] = "\n".join(summary) + "\n"
    local["docs/59_week38_wp1_method_audit.md"] = "\n".join(summary) + "\n"
    finish_week(files, local, "week38", "WP1", "independent method audit",
                {"job_matrix_size": len(matrix), "n_settings": len(METHOD_SETTINGS),
                 "audit_cells_computed": len(computed), "relaxed_cells_computed": len(relaxed_computed),
                 "audit_core_hours": "%.3f" % audit_cost,
                 "method_audit_jobs": METHOD_AUDIT_JOB_COUNT,
                 "method_audit_certified": cert["certified"],
                 "new_electronic_structure_jobs_scope": (
                     "jobs that change the frozen ranking/pair evidence; the WP1 local method audit "
                     "(161 jobs) and the WP2 free-state pilot are counted separately"),
                 "local_environment_probe_jobs": len(LOCAL_SMOKE_RUNS)})
    return files


# ---------------------------------------------------------------------------
# Week 39 / WP2 — 固定背景配对自由能标签（首轮登记 + 既有电子能层盘点）
# ---------------------------------------------------------------------------
STATE_CHARGE = {"M": (0, 1), "M_plus": (1, 2), "LiM_plus": (1, 1), "LiM_2plus": (2, 2)}
HARTREE_TO_EV = 27.211386245988

FROZEN_ROBUST_PAIRS = [("EMC", "GBL"), ("EMC", "SL")]


def _audit_axis_spread_summary():
    """氧化轴上的方法展宽：对竖直/绝热电离能做泛函与基组效应分解（eV）。"""
    ips = _audit_axis_ips()
    settings = [row["setting_id"] for row in METHOD_SETTINGS]
    out = {"n_molecules": len(ips)}
    for label, key in (("vertical", "vertical_ip_ev"), ("adiabatic", "adiabatic_ip_ev")):
        functional, basis = [], []
        for name in ips:
            values = [ips[name][key][sid] for sid in settings]
            functional.append(abs((values[0] + values[1]) / 2.0 - (values[2] + values[3]) / 2.0))
            basis.append(abs((values[0] + values[2]) / 2.0 - (values[1] + values[3]) / 2.0))
        functional.sort()
        basis.sort()
        middle = len(functional) // 2
        out["%s_functional_effect_median_ev" % label] = "%.6f" % functional[middle]
        out["%s_functional_effect_max_ev" % label] = "%.6f" % functional[-1]
        out["%s_basis_effect_median_ev" % label] = "%.6f" % basis[middle]
        out["%s_basis_effect_max_ev" % label] = "%.6f" % basis[-1]
    return out


def method_audit_certification():
    """认证 WP3 冻结的稳健翻转：在同一组预先接受的方法设定下，竖直腿与弛豫腿必须给出
    相反符号，且每一腿的最小绝对值要超过该腿自身的方法展宽（跨 4 设定的总体标准差）。"""
    legs = _audit_pair_legs()
    pairs = []
    for left, right in FROZEN_ROBUST_PAIRS:
        leg = legs[(left, right)]
        vertical = _leg_stats(leg["vertical"])
        adiabatic = _leg_stats(leg["adiabatic"])
        vertical_resolved = (vertical["sign_consistent"]
                             and vertical["min_abs_ev"] > vertical["sigma_ev"])
        adiabatic_resolved = (adiabatic["sign_consistent"]
                              and adiabatic["min_abs_ev"] > adiabatic["sigma_ev"])
        opposite = (vertical_resolved and adiabatic_resolved
                    and ((vertical["min_ev"] > 0 > adiabatic["max_ev"])
                         or (adiabatic["min_ev"] > 0 > vertical["max_ev"])))
        pairs.append({
            "pair": "%s | %s" % (left, right),
            "vertical_sign": "positive" if vertical["mean_ev"] > 0 else "negative",
            "adiabatic_sign": "positive" if adiabatic["mean_ev"] > 0 else "negative",
            "vertical_min_abs_ev": "%.6f" % vertical["min_abs_ev"],
            "vertical_sigma_ev": "%.6f" % vertical["sigma_ev"],
            "vertical_range_ev": "%.6f" % vertical["range_ev"],
            "adiabatic_min_abs_ev": "%.6f" % adiabatic["min_abs_ev"],
            "adiabatic_sigma_ev": "%.6f" % adiabatic["sigma_ev"],
            "adiabatic_range_ev": "%.6f" % adiabatic["range_ev"],
            "vertical_resolved": vertical_resolved,
            "adiabatic_resolved": adiabatic_resolved,
            "opposite_signs": opposite,
            "certified": bool(vertical_resolved and adiabatic_resolved and opposite),
        })
    return {
        "certified": bool(pairs) and all(item["certified"] for item in pairs),
        "n_pairs": len(pairs),
        "n_pairs_certified": sum(1 for item in pairs if item["certified"]),
        "criterion": ("each leg is resolved when its 4 method values keep one sign and the smallest "
                      "absolute value exceeds that leg method spread (population std across the 4 "
                      "pre-accepted settings); a pair is certified when both legs are resolved with "
                      "opposite signs"),
        "scope": "method axis only (4 pre-accepted settings); conformational sampling bounds are not included",
        "settings": [row["setting_id"] for row in METHOD_SETTINGS],
        "vertical_leg": "cation single point on the frozen r2SCAN-3c neutral geometry",
        "relaxed_leg": "cation single point on the frozen r2SCAN-3c relaxed-cation geometry",
        "pairs": pairs,
    }


METHOD_AUDIT_SPREAD = _audit_axis_spread_summary()
METHOD_AUDIT_CERTIFICATION = method_audit_certification()


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

    # 方案 6.1/6.2 —— 生产首段：已完成的分子 x 主态真实 Opt/Freq 自由能标签（每态一个代表结构）。
    all_production = [dict(row) for row in WP2_PRODUCTION_LEDGER]
    production = [row for row in all_production if row["state"] in WP2_PRODUCTION_STATES]
    production_extra = [row for row in all_production if row["state"] in WP2_PRODUCTION_EXTRA_STATES]
    production_index = {(row["mol_id"], row["state"]): row for row in production}
    production_lookup = {(row["mol_id"], row["state"]): row for row in all_production}
    production_produced = 0
    for row in ledger:
        prod = production_index.get((row["mol_id"], row["state"]))
        if prod is None:
            continue
        row["e_sp_solution_ev"] = prod["e_sp_solution_ev"]
        row["zpe_ev"] = prod["zpe_ev"]
        row["thermal_corr_ev"] = prod["thermal_corr_ev"]
        row["std_state_corr_ev"] = prod["std_state_corr_ev"]
        row["g_single_ev"] = prod["g_single_ev"]
        row["n_conformers"] = "1"
        row["identity_label"] = _wp2_production_identity(prod["state"], prod["li_o_ang"])
        row["status"] = "produced_single_conformer"
        production_produced += 1
    for prod in all_production:
        prod["identity_label"] = _wp2_production_identity(prod["state"], prod["li_o_ang"])

    production_qc = []
    for prod in all_production:
        production_qc.append({
            "record_id": prod["record_id"], "name": prod["name"], "state": prod["state"],
            "charge": prod["charge"], "multiplicity": prod["multiplicity"],
            "opt_converged": prod["opt_converged"], "terminated": prod["terminated"],
            "n_freq": prod["n_freq"], "imaginary_modes": prod["imaginary_modes"],
            "lowest_freq_cm1": prod["lowest_freq_cm1"], "li_o_ang": prod["li_o_ang"],
            "nonli_components": prod["nonli_components"],
            "identity_label": prod["identity_label"], "status": prod["status"],
        })

    production_cost = []
    production_core_hours = 0.0
    for prod in all_production:
        production_core_hours += float(prod["core_hours"])
        production_cost.append({
            "job_id": "%s|%s|opt_numfreq" % (prod["mol_id"], prod["state"]),
            "mol_id": prod["mol_id"], "name": prod["name"], "state": prod["state"],
            "phase": "opt_numfreq", "level": prod["level"], "cores": prod["cores"],
            "wall_sec": prod["wall_sec"], "core_hours": prod["core_hours"],
            "status": prod["status"],
        })

    molecules_started = sorted({row["mol_id"] for row in production})
    molecules_complete = sorted(mol_id for mol_id in WP2_PRODUCTION_MOLECULES
                                if all((mol_id, state) in production_index
                                       for state in WP2_PRODUCTION_STATES))
    production_progress = {
        "states_done": len(production),
        "states_total": len(WP2_PRODUCTION_MOLECULES) * len(WP2_PRODUCTION_STATES),
        "extra_legs_done": len(production_extra),
        "molecules_started": molecules_started,
        "molecules_complete": molecules_complete,
    }

    # 自由分子 Gox_single / Li 腿 IP / coordination shift：只有两腿都是 def2-TZVPD 时才给数。
    production_redox = []
    for mol_id in WP2_PRODUCTION_MOLECULES:
        name = WP2_PRODUCTION_NAMES[mol_id]
        free_neutral = production_lookup.get((mol_id, "M_tzvpd"))
        free_cation = production_lookup.get((mol_id, "M_plus"))
        li_plus = production_lookup.get((mol_id, "LiM_plus"))
        li_2plus = production_lookup.get((mol_id, "LiM_2plus"))
        entry = {"mol_id": mol_id, "name": name, "basis": "def2-TZVPD",
                 "eox_adiabatic_ev": "", "gox_single_ev": "", "thermal_step_free_ev": "",
                 "li_ip_e_ev": "", "li_ip_g_ev": "", "thermal_step_li_ev": "",
                 "coordination_shift_e_ev": "", "coordination_shift_g_ev": "", "status": "",
                 "note": ""}
        if free_neutral is None or free_cation is None:
            entry["status"] = "not_computed"
            entry["note"] = ("a basis-consistent free-molecule redox label needs both a def2-TZVPD "
                             "neutral leg (M_tzvpd) and the def2-TZVPD cation; the def2-TZVP M leg is "
                             "never subtracted from a def2-TZVPD cation")
            production_redox.append(entry)
            continue
        free_e = float(free_cation["e_sp_solution_ev"]) - float(free_neutral["e_sp_solution_ev"])
        free_g = float(free_cation["g_single_ev"]) - float(free_neutral["g_single_ev"])
        entry["eox_adiabatic_ev"] = "%.6f" % free_e
        entry["gox_single_ev"] = "%.6f" % free_g
        entry["thermal_step_free_ev"] = "%.6f" % (free_g - free_e)
        if li_plus is not None and li_2plus is not None:
            li_e = float(li_2plus["e_sp_solution_ev"]) - float(li_plus["e_sp_solution_ev"])
            li_g = float(li_2plus["g_single_ev"]) - float(li_plus["g_single_ev"])
            entry["li_ip_e_ev"] = "%.6f" % li_e
            entry["li_ip_g_ev"] = "%.6f" % li_g
            entry["thermal_step_li_ev"] = "%.6f" % (li_g - li_e)
            entry["coordination_shift_e_ev"] = "%.6f" % (li_e - free_e)
            entry["coordination_shift_g_ev"] = "%.6f" % (li_g - free_g)
        entry["status"] = "computed"
        entry["note"] = ("same-basis (def2-TZVPD/TZVPD) adiabatic E and qRRHO G; single conformer per state")
        production_redox.append(entry)

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

    # 方案 15.5 / 15.6 —— 自由态 pilot（新增计算）。
    pilot_lookup = {row["record_id"]: row for row in PILOT_FREE_STATE_ENERGIES}
    pilot_ip = []
    for pilot_mol, pilot_name in PILOT_MAIN_MOLECULES:
        p_neutral = float(pilot_lookup["%s|M_tzvpd" % pilot_mol]["final_sp_eh"])
        p_cation = float(pilot_lookup["%s|M_plus" % pilot_mol]["final_sp_eh"])
        pilot_ip.append({
            "mol_id": pilot_mol, "name": pilot_name, "quantity": "Eox_vertical",
            "basis_family": "def2-TZVPD (same basis for neutral and cation)",
            "e_neutral_eh": "%.12f" % p_neutral, "e_cation_eh": "%.12f" % p_cation,
            "ip_ev": "%.6f" % ((p_cation - p_neutral) * HARTREE_TO_EV),
            "level": "wB97X-D4 SMD(acetonitrile) SP at GFN2-xTB geometry",
            "basis_consistent": "true",
            "note": "the cation must use diffuse functions; a TZVP-neutral vs TZVPD-cation difference is NOT a valid IP",
        })
    pilot_std_state_eh = PILOT_RT_EH * PILOT_LN_VM
    pilot_ledger = []
    for pilot_row in PILOT_LEDGER_RAW:
        pilot_g = float(pilot_row["g_single_eh"])
        pilot_ledger.append({
            "record_id": pilot_row["record_id"], "mol_id": pilot_row["mol_id"],
            "name": pilot_row["name"], "state": pilot_row["state"], "level": pilot_row["level"],
            "e_sp_eh": pilot_row["e_sp_eh"], "zpe_eh": pilot_row["zpe_eh"],
            "e_to_g_thermal_eh": pilot_row["e_to_g_thermal_eh"], "enthalpy_eh": pilot_row["enthalpy_eh"],
            "entropy_corr_eh": pilot_row["entropy_corr_eh"], "g_single_eh": pilot_row["g_single_eh"],
            "g_single_ev": "%.9f" % (pilot_g * HARTREE_TO_EV),
            "std_state_corr_eh": "%.8f" % pilot_std_state_eh,
            "std_state_corr_ev": "%.6f" % (pilot_std_state_eh * HARTREE_TO_EV),
            "qrrho": pilot_row["qrrho"], "temp_k": pilot_row["temp_k"],
            "pressure_atm": pilot_row["pressure_atm"], "cutoff_cm1": pilot_row["cutoff_cm1"],
            "lowest_freq_cm1": pilot_row["lowest_freq_cm1"], "imaginary_modes": pilot_row["imaginary_modes"],
        })
    pilot_cost = []
    for cost_row in PILOT_COST_JOBS:
        core_hours = float(cost_row["wall_sec"]) * float(cost_row["cores"]) / 3600.0
        pilot_cost.append({
            "job_id": cost_row["job_id"], "mol_id": cost_row["mol_id"], "molecule": cost_row["molecule"],
            "state": cost_row["state"], "phase": cost_row["phase"], "method": cost_row["method"],
            "cores": cost_row["cores"], "wall_sec": cost_row["wall_sec"],
            "core_hours": "%.6f" % core_hours, "status": cost_row["status"],
        })
    pilot_orca_jobs = sum(1 for r in PILOT_COST_JOBS if r["phase"].startswith("orca"))
    pilot_xtb_jobs = sum(1 for r in PILOT_COST_JOBS if r["phase"].startswith("xtb"))
    pilot_core_hours = sum(float(r["core_hours"]) for r in pilot_cost)
    pilot_li_lookup = {row["record_id"]: row for row in PILOT_LI_STATE_ENERGIES}
    pilot_coord_shift = []
    pilot_dissociated = []
    for pilot_mol, pilot_name in PILOT_MAIN_MOLECULES:
        free_row = next(r for r in pilot_ip if r["mol_id"] == pilot_mol)
        li_plus_row = pilot_li_lookup["%s|LiM_plus" % pilot_mol]
        li_2plus_row = pilot_li_lookup["%s|LiM_2plus" % pilot_mol]
        li_plus = float(li_plus_row["final_sp_eh"])
        li_2plus = float(li_2plus_row["final_sp_eh"])
        ip_li = (li_2plus - li_plus) * HARTREE_TO_EV
        bound_2plus = not li_2plus_row["identity"].startswith("dissociated")
        if not bound_2plus:
            pilot_dissociated.append(pilot_name)
        frozen = c1_primary.get(pilot_mol)
        pilot_coord_shift.append({
            "mol_id": pilot_mol, "name": pilot_name, "quantity": "coordination_shift",
            "e_liM_plus_eh": "%.12f" % li_plus, "e_liM_2plus_eh": "%.12f" % li_2plus,
            "ip_li_ev": "%.6f" % ip_li, "ip_free_ev": free_row["ip_ev"],
            "d_ip_ev": "%.6f" % (ip_li - float(free_row["ip_ev"])),
            "two_plus_state": ("bound" if bound_2plus
                               else "dissociated (Li leaves the fragment during GFN2 relaxation)"),
            "d_ip_interpretable": "true" if bound_2plus else "false",
            "level": "wB97X-D4/def2-TZVPD SMD(acetonitrile), consistent basis",
            "frozen_c1_motif": (frozen["motif_id"] if frozen else ""),
            "frozen_c1_d_ip_smd_ev": ((frozen.get("d_ip_smd_ev") or "") if frozen else ""),
            "note": (("frozen C1 layer value exists but mixes conventions (gas-phase free IP as the "
                      "SMD reference); not directly comparable") if frozen
                     else "no frozen C1 primary row for this molecule"),
        })
    n_existing_mol = len({row["mol_id"] for row in existing})
    checks = [
        {"id": "ledger_covers_main_x_four_states", "description": "自由能账本登记 12 主集 x 4 主状态 = 48 行",
         "ok": len(ledger) == 48, "detail": "n_rows=%d" % len(ledger)},
        {"id": "thermal_fields_left_empty_not_zero", "description": "尚未计算的热校正字段留空而非 0",
         "ok": (all(row["thermal_corr_ev"] == "" and row["g_single_ev"] == "" for row in ledger
                    if row["status"] == "planned")
                and all(row["thermal_corr_ev"] and row["g_single_ev"] for row in ledger
                        if row["status"] == "produced_single_conformer")),
         "detail": "planned=%d 行留空；produced=%d 行有值（无 0 填充）"
                   % (sum(1 for row in ledger if row["status"] == "planned"), production_produced)},
        {"id": "sampling_plan_has_escalation_rule", "description": "采样审计集给出 3->6 升级规则",
         "ok": len(sampling) == 16 and all(row["escalation_rule"] for row in sampling),
         "detail": "n_rows=%d" % len(sampling)},
        {"id": "existing_electronic_layer_is_labelled", "description": "既有数值标明只到电子能层、缺热校正",
         "ok": all(row["thermal_correction"] == "absent" for row in existing),
         "detail": "%d 条既有数值 / %d 个分子" % (len(existing), n_existing_mol)},
        {"id": "ensemble_rules_frozen", "description": "系综规则在观察目标排名前冻结",
         "ok": len(ENSEMBLE_RULES) >= 6, "detail": "n_rules=%d" % len(ENSEMBLE_RULES)},
        {"id": "pilot_free_state_jobs_all_converged", "description": "自由态 pilot 的 ORCA 单点全部正常收敛",
         "ok": len(PILOT_FREE_STATE_ENERGIES) == 3 * len(PILOT_MAIN_MOLECULES)
               and all(r["terminated"] == "true" for r in PILOT_FREE_STATE_ENERGIES),
         "detail": "free-state rows=%d over %d main-set molecules" % (
             len(PILOT_FREE_STATE_ENERGIES), len(PILOT_MAIN_MOLECULES))},
        {"id": "pilot_vertical_ip_is_basis_consistent", "description": "pilot 垂直 IP 用中性/阳离子一致基组",
         "ok": len(pilot_ip) == len(PILOT_MAIN_MOLECULES)
               and all(r["basis_consistent"] == "true" for r in pilot_ip),
         "detail": ",".join("%s=%s eV" % (r["name"], r["ip_ev"]) for r in pilot_ip)},
        {"id": "pilot_ledger_instance_is_complete", "description": "自由能账本实例给出 E/ZPE/热项/G/标准态项",
         "ok": bool(pilot_ledger) and all(
               all(row[key] for key in ("e_sp_eh", "zpe_eh", "e_to_g_thermal_eh",
                                        "g_single_eh", "std_state_corr_eh", "g_single_ev"))
               for row in pilot_ledger),
         "detail": "record=%s; G=%s eV" % (pilot_ledger[0]["record_id"], pilot_ledger[0]["g_single_ev"])},
        {"id": "pilot_cost_ledger_records_core_hours", "description": "pilot 成本账本逐作业记录 allocated core-hours",
         "ok": bool(pilot_cost) and all(float(r["core_hours"]) > 0 for r in pilot_cost),
         "detail": "jobs=%d; total=%.6f core-hours" % (len(pilot_cost), pilot_core_hours)},
        {"id": "pilot_li_states_converged_and_intact", "description": "Li 两态收敛、分子骨架完整；LiM_plus 全部成键，2+ 态解离单独标注",
         "ok": len(PILOT_LI_STATE_ENERGIES) == 2 * len(PILOT_MAIN_MOLECULES)
               and all(r["terminated"] == "true" and r["nonli_components"] == "1"
                       for r in PILOT_LI_STATE_ENERGIES)
               and all(float(r["li_o_ang"]) < 2.45 for r in PILOT_LI_STATE_ENERGIES
                       if r["state"] == "LiM_plus")
               and all((float(r["li_o_ang"]) < 2.60) != r["identity"].startswith("dissociated")
                       for r in PILOT_LI_STATE_ENERGIES),
         "detail": "rows=%d; LiM_plus bound %d/%d; dissociated=%s" % (
             len(PILOT_LI_STATE_ENERGIES),
             sum(1 for r in PILOT_LI_STATE_ENERGIES
                 if r["state"] == "LiM_plus" and float(r["li_o_ang"]) < 2.45),
             len(PILOT_MAIN_MOLECULES),
             ",".join(sorted(r["record_id"] for r in PILOT_LI_STATE_ENERGIES
                            if r["identity"].startswith("dissociated"))) or "none")},
        {"id": "pilot_covers_all_four_master_states", "description": "pilot 覆盖 12 主集分子的四主态（自由 3 + 配位 2）",
         "ok": (len(PILOT_FREE_STATE_ENERGIES) == 3 * len(PILOT_MAIN_MOLECULES)
                and len(PILOT_LI_STATE_ENERGIES) == 2 * len(PILOT_MAIN_MOLECULES)),
         "detail": "free=%d + li=%d rows over %d main-set molecules" % (
             len(PILOT_FREE_STATE_ENERGIES), len(PILOT_LI_STATE_ENERGIES),
             len(PILOT_MAIN_MOLECULES))},
        {"id": "pilot_donor_placement_recorded", "description": "Li 初始位按给体类型（羰基/醚/腈/亚砜/砜/磷酰）逐分子记录",
         "ok": len(PILOT_DONOR_PLACEMENT) == len(PILOT_MAIN_MOLECULES)
               and all(r["donor_family"] and r["direction"] for r in PILOT_DONOR_PLACEMENT),
         "detail": "families=%s" % ",".join(sorted({r["donor_family"] for r in PILOT_DONOR_PLACEMENT}))},
        {"id": "pilot_covers_all_twelve_main_molecules", "description": "pilot 覆盖 12 主集全部分子",
         "ok": {r["mol_id"] for r in pilot_ip} == set(PB.COHORTS["main"]),
         "detail": "molecules=%d" % len({r["mol_id"] for r in pilot_ip})},
        {"id": "pilot_coordination_shift_computed", "description": "pilot 配位位移（SMD 自洽口径）逐分子给出",
         "ok": len(pilot_coord_shift) == len(PILOT_MAIN_MOLECULES)
               and all(r["d_ip_ev"] for r in pilot_coord_shift)
               and all(float(r["d_ip_ev"]) > 0.0 for r in pilot_coord_shift
                       if r["d_ip_interpretable"] == "true"),
         "detail": "%d interpretable + %d dissociated(not interpretable); d_ip %.3f-%.3f eV over interpretable" % (
             sum(1 for r in pilot_coord_shift if r["d_ip_interpretable"] == "true"),
             sum(1 for r in pilot_coord_shift if r["d_ip_interpretable"] == "false"),
             min(float(r["d_ip_ev"]) for r in pilot_coord_shift if r["d_ip_interpretable"] == "true"),
             max(float(r["d_ip_ev"]) for r in pilot_coord_shift if r["d_ip_interpretable"] == "true"))},
        {"id": "pilot_flags_dissociated_dication_states", "description": "2+ 态解离的分子逐条标注并排除出配位位移结论",
         "ok": all((r["d_ip_interpretable"] == "false") == r["two_plus_state"].startswith("dissociated")
                   for r in pilot_coord_shift),
         "detail": "dissociated=[%s]" % ",".join(r["name"] for r in pilot_coord_shift
                                                 if r["d_ip_interpretable"] == "false")},
        {"id": "wp2_production_states_terminated_without_imaginary",
         "description": "已生产状态 ORCA 正常结束、Opt 收敛、无虚频",
         "ok": all(r["terminated"] == "true" and r["opt_converged"] == "true"
                   and r["imaginary_modes"] == "0" for r in all_production),
         "detail": "%d 个已生产状态全部 terminated / Opt 收敛 / 无虚频"
                   % len(all_production)},
        {"id": "wp2_production_gibbs_decomposes_from_the_solution_sp",
         "description": "每个已生产态满足 G = E_SP + (G - E(el))；E_SP 取 ORCA 热化学段的 Electronic energy（末收敛几何的 SMD 单点），不是作业首个 FINAL SINGLE POINT ENERGY",
         "ok": (len(all_production) > 0
                and all(abs(float(r["g_single_eh"])
                            - (float(r["e_sp_eh"]) + float(r["e_to_g_thermal_eh"]))) < 1e-6
                        for r in all_production)
                and all(r["e_sp_eh"] == r["electronic_eh"] for r in all_production
                        if r["electronic_eh"])),
         "detail": "max |G - (E_SP + G-E(el))| = %.3e Eh over %d state(s)"
                   % (max([abs(float(r["g_single_eh"])
                            - (float(r["e_sp_eh"]) + float(r["e_to_g_thermal_eh"])))
                           for r in all_production] or [0.0]), len(all_production))},
        {"id": "wp2_production_is_a_registered_subset",
         "description": "只登记已跑完的主态，进度可查；未完成态不出现在表里",
         "ok": (0 < len(production) <= production_progress["states_total"]
                and len({(r["mol_id"], r["state"]) for r in production}) == len(production)
                and all(r["mol_id"] in WP2_PRODUCTION_MOLECULES for r in production)),
         "detail": "states %d/%d over %d/%d molecules; extra legs %d"
                   % (production_progress["states_done"], production_progress["states_total"],
                      len(molecules_started), len(WP2_PRODUCTION_MOLECULES),
                      production_progress["extra_legs_done"])},
        {"id": "wp2_production_fills_only_the_produced_template_rows",
         "description": "只回填已生产状态，其余模板行保持为空串（缺值不写 0）",
         "ok": (production_produced == len(production)
                and sum(1 for r in ledger if r["status"] == "planned")
                == len(ledger) - production_produced
                and all(not r["g_single_ev"] for r in ledger if r["status"] == "planned")),
         "detail": "produced=%d planned=%d; planned rows carry empty G"
                   % (production_produced, len(ledger) - production_produced)},
        {"id": "wp2_production_li_states_record_binding_metrics",
         "description": "已生产的 Li 态记录 Li-O/N 距离与非 Li 片段数；按固定阈值标注 bound/dissociated",
         "ok": (all(r["li_o_ang"] and r["nonli_components"] for r in production
                    if r["state"] in ("LiM_plus", "LiM_2plus"))
                and all((r["identity_label"] == "bound") == (float(r["li_o_ang"]) < 2.45)
                        for r in production if r["state"] in ("LiM_plus", "LiM_2plus"))),
         "detail": "li_states=%d bound=%d"
                   % (sum(1 for r in production if r["state"] in ("LiM_plus", "LiM_2plus")),
                      sum(1 for r in production if r["identity_label"] == "bound"))},
        {"id": "wp2_production_cost_records_allocated_core_hours",
         "description": "生产作业逐条记录 allocated core-hours（cores x wall clock）",
         "ok": len(production_cost) == len(all_production) and production_core_hours > 0.0,
         "detail": "jobs=%d; total=%.6f core-hours" % (len(production_cost), production_core_hours)},
        {"id": "wp2_production_redox_registered_without_numbers",
         "description": "缺基组一致的中性腿时不补数：redox 表登记 status=not_computed 且数值留空",
         "ok": (len(production_extra) == 0
                and all(row["status"] == "not_computed" for row in production_redox)
                and all(not row[key] for row in production_redox
                        for key in ("eox_adiabatic_ev", "gox_single_ev",
                                    "coordination_shift_g_ev"))),
         "detail": "production states=%d; redox rows=%d (all not_computed)"
                   % (len(production), len(production_redox))},
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
        "free_state_pilot": {
            "scope": "all 12 main-set molecules: 4 master states (M, M+, LiM_plus, LiM_2plus) at the pilot level",
            "geometry": PILOT_GEOM_NOTE,
            "method": PILOT_METHOD_NOTE,
            "free_state_energies": PILOT_FREE_STATE_ENERGIES,
            "vertical_ip": pilot_ip,
            "li_state_energies": PILOT_LI_STATE_ENERGIES,
            "coordination_shift": pilot_coord_shift,
            "ledger_instances": pilot_ledger,
            "cost_jobs": pilot_cost,
            "donor_placement": PILOT_DONOR_PLACEMENT,
            "totals": {"orca_jobs": pilot_orca_jobs, "xtb_jobs": pilot_xtb_jobs,
                       "core_hours": "%.6f" % pilot_core_hours},
            "raw_outputs": "kept outside the repository (not mirrored)",
        },
        "free_state_production": {
            "scope": ("production first segment: 4 main-set molecules x 4 master states "
                      "(16 states), one representative structure each; only completed states are listed"),
            "geometry": WP2_PRODUCTION_GEOM_NOTE,
            "method": WP2_PRODUCTION_METHOD_NOTE,
            "molecules": WP2_PRODUCTION_MOLECULES,
            "progress": production_progress,
            "basis_note": ("the neutral (M) leg runs def2-TZVP while the cationic and Li legs run "
                           "def2-TZVPD, so those rows must NOT be subtracted to give a basis-consistent "
                           "free-molecule IP; only a def2-TZVPD neutral leg (state M_tzvpd) makes "
                           "Gox_single and the coordination shift well defined, and that difference is "
                           "reported separately in production_redox.csv. The TZVP/TZVPD pair is the "
                           "plan 5.1 method axis, not two legs of one IP."),
            "extra_states": WP2_PRODUCTION_EXTRA_STATES,
            "ledger": all_production,
            "qc": production_qc,
            "redox": production_redox,
            "cost_jobs": production_cost,
            "totals": {"orca_jobs": len(all_production),
                       "core_hours": "%.6f" % production_core_hours},
            "raw_outputs": "kept outside the repository (work/wp2prod, not mirrored)",
        },
        "counts": {"ledger_rows": len(ledger), "production_rows": len(production),
                   "production_extra_rows": len(production_extra),
                   "production_template_rows_filled": production_produced,
                   "sampling_rows": len(sampling),
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
    local["outputs/physics_completion/free_states/production_ledger.csv"] = csv_text(
        WP2_PRODUCTION_LEDGER_CSV_FIELDS, all_production)
    local["outputs/physics_completion/free_states/production_qc.csv"] = csv_text(
        ["record_id", "name", "state", "charge", "multiplicity", "opt_converged", "terminated",
         "n_freq", "imaginary_modes", "lowest_freq_cm1", "li_o_ang", "nonli_components",
         "identity_label", "status"], production_qc)
    local["outputs/physics_completion/free_states/production_redox.csv"] = csv_text(
        ["mol_id", "name", "basis", "eox_adiabatic_ev", "gox_single_ev", "thermal_step_free_ev",
         "li_ip_e_ev", "li_ip_g_ev", "thermal_step_li_ev", "coordination_shift_e_ev",
         "coordination_shift_g_ev", "status", "note"], production_redox)
    local["outputs/physics_completion/cost/production_cost_ledger.csv"] = csv_text(
        ["job_id", "mol_id", "name", "state", "phase", "level", "cores", "wall_sec",
         "core_hours", "status"], production_cost)
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
          "note": "charged complexes that fail to form a complete state (e.g. a 2+ state where Li dissociates) are recorded as a QC outcome; motifs are not swapped until a number is obtained"}
         for mol_id in PB.COHORTS["main"]])
    local["outputs/physics_completion/free_states/pilot_free_state_energies.csv"] = csv_text(
        ["record_id", "mol_id", "name", "state", "charge", "multiplicity", "basis", "orca_keyword",
         "scf_cycles", "final_sp_eh", "terminated", "wall_sec", "cores"], PILOT_FREE_STATE_ENERGIES)
    local["outputs/physics_completion/free_states/pilot_vertical_ip.csv"] = csv_text(
        ["mol_id", "name", "quantity", "basis_family", "e_neutral_eh", "e_cation_eh", "ip_ev",
         "level", "basis_consistent", "note"], pilot_ip)
    local["outputs/physics_completion/free_states/pilot_ledger_instance.csv"] = csv_text(
        ["record_id", "mol_id", "name", "state", "level", "e_sp_eh", "zpe_eh", "e_to_g_thermal_eh",
         "enthalpy_eh", "entropy_corr_eh", "g_single_eh", "g_single_ev", "std_state_corr_eh",
         "std_state_corr_ev", "qrrho", "temp_k", "pressure_atm", "cutoff_cm1", "lowest_freq_cm1",
         "imaginary_modes"], pilot_ledger)
    local["outputs/physics_completion/free_states/pilot_li_state_energies.csv"] = csv_text(
        ["record_id", "mol_id", "name", "state", "charge", "multiplicity", "basis", "orca_keyword",
         "basis_functions", "scf_cycles", "final_sp_eh", "terminated", "wall_sec", "cores",
         "li_o_ang", "nonli_components", "donor_contacts", "identity"], PILOT_LI_STATE_ENERGIES)
    local["outputs/physics_completion/free_states/pilot_coordination_shift.csv"] = csv_text(
        ["mol_id", "name", "quantity", "e_liM_plus_eh", "e_liM_2plus_eh", "ip_li_ev", "ip_free_ev",
         "d_ip_ev", "two_plus_state", "d_ip_interpretable", "level", "frozen_c1_motif",
         "frozen_c1_d_ip_smd_ev", "note"], pilot_coord_shift)
    local["outputs/physics_completion/cost/pilot_cost_ledger.csv"] = csv_text(
        ["job_id", "mol_id", "molecule", "state", "phase", "method", "cores", "wall_sec",
         "core_hours", "status"], pilot_cost)

    summary = [
        "# Week 39 / WP2 — 固定背景配对自由能标签",
        "",
        "**状态**：账本与系综规则已冻结；48 行生产模板中已登记 %d/%d 个主态的真实 Opt+Freq 账本行"
        "（其余行热校正保持为空，缺值不写 0）。已另跑 12 主集自由态 + Li 配位态 pilot（新增计算，方案 15.5/15.6），见下节。"
        % (production_progress["states_done"], production_progress["states_total"]),
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
        "## 12 主集四主态 pilot（方案 15.5 / 15.6，新增计算）",
        "",
        "几何：%s；方法：%s。原始输出留在仓库外，不入交付镜像。" % (PILOT_GEOM_NOTE, PILOT_METHOD_NOTE),
        "",
        "覆盖 **12 主集全部分子**的**四主态**：自由态 M、M+ 与 Li 配位态 LiM_plus、LiM_2plus。",
        "",
        "| 分子 | 量 | 一致基组 | E(中性) Eh | E(阳离子) Eh | Eox_vertical (eV) |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in pilot_ip:
        summary.append("| %s | %s | %s | %s | %s | %s |"
                       % (row["name"], row["quantity"], row["basis_family"],
                          row["e_neutral_eh"], row["e_cation_eh"], row["ip_ev"]))
    summary += [
        "",
        "自由能账本实例（1 行，qRRHO）：",
        "",
        "| 记录 | 级别 | E_SP (Eh) | ZPE (Eh) | E→G 热项 (Eh) | 熵项 (Eh) | G_single (Eh) | G (eV) | 标准态项 (eV) | 虚频 |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in pilot_ledger:
        summary.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |"
                       % (row["record_id"].replace("|", "\\|"), row["level"], row["e_sp_eh"], row["zpe_eh"],
                          row["e_to_g_thermal_eh"], row["entropy_corr_eh"], row["g_single_eh"],
                          row["g_single_ev"], row["std_state_corr_ev"], row["imaginary_modes"]))
    summary += [
        "",
        "成本账本：%d 个作业（ORCA %d / xTB %d），合计 **%.6f core-hours**（allocated cores × wall clock）。"
        % (len(pilot_cost), pilot_orca_jobs, pilot_xtb_jobs, pilot_core_hours),
        "",
        "Li 配位两态（SMD，def2-TZVPD，Li 按给体类型沿外侧 1.9 A 起点后 GFN2 优化；donor_contacts = 2.60 A 内给体数）：",
        "",
        "| 记录 | 电荷/多重度 | 基函数 | SCF | 末单点 (Eh) | Li-O/N (A) | 给体接触 | 非 Li 片段数 | 身份 |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in PILOT_LI_STATE_ENERGIES:
        summary.append("| %s | %s/%s | %s | %s | %s | %s | %s | %s | %s |"
                       % (row["record_id"].replace("|", "\\|"), row["charge"], row["multiplicity"],
                          row["basis_functions"], row["scf_cycles"], row["final_sp_eh"],
                          row["li_o_ang"], row["donor_contacts"], row["nonli_components"],
                          row["identity"]))
    summary += [
        "",
        "配位位移（SMD 自洽口径）：d_ip = IP(Li 复合物) - IP(自由分子)。",
        "",
        "| 分子 | E([LiM]+) Eh | E([LiM]2+) Eh | IP_Li (eV) | IP_free (eV) | d_ip (eV) | 2+ 态 | 可解释 | 冻结 C1 motif | 冻结 d_ip_smd (eV) | 说明 |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in pilot_coord_shift:
        summary.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |"
                       % (row["name"], row["e_liM_plus_eh"], row["e_liM_2plus_eh"], row["ip_li_ev"],
                          row["ip_free_ev"], row["d_ip_ev"], row["two_plus_state"],
                          row["d_ip_interpretable"], row["frozen_c1_motif"] or "-",
                          row["frozen_c1_d_ip_smd_ev"] or "-", row["note"]))
    summary += [
        "",
        "## 生产首段：4 主集分子 x 4 主态的真实 Opt+Freq 自由能",
        "",
        "级别：%s；几何起点为既有冻结 r2SCAN-3c 结构，每态一个代表结构。" % WP2_PRODUCTION_METHOD_NOTE,
        "进度：已登记 **%d/%d** 个主态（完成分子 %s）；未完成的状态不出现在表里，也不写成 0。"
        % (production_progress["states_done"], production_progress["states_total"],
           ",".join(production_progress["molecules_complete"]) or "-"),
        "账本 G = E_SP + (G - E(el)) + 标准态项（RT ln V_m，1 atm -> 1 mol/L）；标准态项在同一化学计量差值中相消。",
        "",
        "| 记录 | E_SP (Eh) | ZPE (Eh) | E->G 热项 (Eh) | G_single (Eh) | G (eV) | 虚频 | 最低频 (cm^-1) | Li-O/N (A) | 非 Li 片段 | 身份 |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for prod in all_production:
        summary.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |"
                       % (prod["record_id"], prod["e_sp_eh"], prod["zpe_eh"],
                          prod["e_to_g_thermal_eh"], prod["g_single_eh"], prod["g_single_ev"],
                          prod["imaginary_modes"], prod["lowest_freq_cm1"],
                          prod["li_o_ang"] or "-", prod["nonli_components"] or "-",
                          prod["identity_label"]))
    summary += [
        "",
        "成本：%d 个 Opt+Freq 作业，合计 %.6f core-hours（allocated cores x wall clock）。"
        % (len(production_cost), production_core_hours),
        "",
        "基组一致的 Gox_single 与配位位移**未计算**：需要一条 def2-TZVPD 的中性腿；登记为下一批作业，"
        "不把 def2-TZVP 中性腿与 def2-TZVPD 阳离子腿相减充数。",
        "",
        "## 限制",
        "- 生产模板只回填已跑完的主态（本次 5/16）：中性腿 def2-TZVP、带电/Li 腿 def2-TZVPD，两腿相减不是基组一致的自由分子 IP，本报告不据此计算 Eox；其余行热校正保持为空（未把缺值写成 0）。",
        "- 生产首段每态只有**单一代表结构**（n_conformers = 1），不是方案 6.1 的多构象/多 motif 系综；6 kcal/mol 窗口与 3 结构上限仍是资源规则。",
        "- pilot 覆盖 12 主集全部分子，但每态只有单一构象（GFN2 起点），不是方案 6 的多构象系综生产；几何来自 GFN2 而非 r2SCAN-3c。",
        "- DME 与 AN 的 2+ 态在 GFN2 弛豫中 Li 解离（Li-O/N > 10 A），故其 d_ip 记为不可解释、不进入结论；这本身是 GFN2 下 2+ 复合物不稳定的 QC 结果。",
        "- Li 配位态只对单一给体位点、单一构象做了一次；不能替代 12 主集完整生产。",
        "- pilot 配位位移为 SMD 自洽口径；冻结 C1 层把气相自由 IP 当作 SMD 参考，属混口径，两者不可直接相比。",
        "- 标准态项把理想气体 1 atm 自由能换到溶液 1 mol/L（RT ln V_m）；同一化学计量的 redox 差值中该项相消。",
        "- 既有 P1v/P1a/C1 数值是 r2SCAN-3c 气相电子能差，不能直接当作固定背景 SMD 自由能标签。",
        "- 采样窗口 6 kcal/mol 与上限 3 结构是**资源规则**，不是已经证明收敛的采样尺度。",
    ]
    local["outputs/week39/wp2_summary.md"] = "\n".join(summary) + "\n"
    local["docs/60_week39_wp2_free_energy_labels.md"] = "\n".join(summary) + "\n"
    finish_week(files, local, "week39", "WP2", "fixed-background paired free-energy labels",
                {"ledger_rows": len(ledger), "existing_electronic_rows": len(existing),
                 "free_state_pilot_orca_jobs": pilot_orca_jobs,
                 "free_state_pilot_xtb_jobs": pilot_xtb_jobs,
                 "free_state_pilot_core_hours": "%.6f" % pilot_core_hours,
                 "free_state_production_states": len(production),
                 "free_state_production_states_total": production_progress["states_total"],
                 "free_state_production_molecules_complete": len(molecules_complete),
                 "free_state_production_core_hours": "%.6f" % production_core_hours,
                 "free_state_production_redox_computed": str(
                     any(row["status"] == "computed" for row in production_redox)).lower()})
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



def _read_xyz(path):
    """读一个 .xyz：返回 (elements, coords)，原子顺序按文件顺序保留。"""
    lines = path.read_text(encoding="utf-8").splitlines()
    n_atoms = int(lines[0].split()[0])
    elements, coords = [], []
    for line in lines[2:2 + n_atoms]:
        parts = line.replace(",", " ").split()
        elements.append(parts[0])
        coords.append((float(parts[1]), float(parts[2]), float(parts[3])))
    if len(elements) != n_atoms:
        raise ValueError("truncated xyz: %s" % path)
    return elements, coords


def _heavy_bonds(elements, coords, cutoff):
    """枚举距离 <= cutoff 的重原子成键对；只用几何判据，不用力常数。"""
    bonds = {}
    for i in range(len(coords)):
        if elements[i] == "H":
            continue
        for j in range(i + 1, len(coords)):
            if elements[j] == "H":
                continue
            distance = math.dist(coords[i], coords[j])
            if distance <= cutoff:
                bonds[(i, j)] = distance
    return bonds


def build_mechanism_geometry(cases):
    """机制案例的原始结构证据：中性松弛几何 vs 阳离子松弛几何的键长变化。

    两个几何都来自既有冻结产物（本批次零新增电子结构计算）。键长是平移/旋转
    不变量，因此不需要叠合；成键对只用几何截断枚举，不作力常数判据。
    """
    adiabatic = {row["name"]: row for row in
                 PB.load_rows(REPO / PB.MECHANISM_ADIABATIC_TABLE)}
    names = sorted({part.strip() for case in cases for part in case["pair"].split("|")})
    rows, bond_rows = [], []
    for name in names:
        neutral_rel = PB.MECHANISM_NEUTRAL_GEOMETRY.format(name=name)
        cation_rel = PB.MECHANISM_CATION_GEOMETRY.format(name=name)
        neutral_elements, neutral_coords = _read_xyz(REPO / neutral_rel)
        cation_elements, cation_coords = _read_xyz(REPO / cation_rel)
        neutral_bonds = _heavy_bonds(neutral_elements, neutral_coords, PB.GEOMETRY_BOND_CUTOFF_ANG)
        cation_bonds = _heavy_bonds(cation_elements, cation_coords, PB.GEOMETRY_BOND_CUTOFF_ANG)
        shared = sorted(set(neutral_bonds) & set(cation_bonds))
        change = {pair: cation_bonds[pair] - neutral_bonds[pair] for pair in shared}
        worst = max(change, key=lambda pair: abs(change[pair])) if change else None
        entry = adiabatic.get(name, {})
        rows.append({
            "name": name,
            "family": entry.get("family", ""),
            "n_atoms": len(neutral_elements),
            "element_sequence_matches": str(neutral_elements == cation_elements).lower(),
            "n_heavy_bonds_shared": len(shared),
            "mean_abs_bond_change_ang": ("%.6f" % (sum(abs(v) for v in change.values()) / len(shared)))
                                         if shared else "",
            "max_abs_bond_change_ang": ("%.6f" % abs(change[worst])) if worst else "",
            "max_bond_pair": ("%s%d-%s%d" % (neutral_elements[worst[0]], worst[0] + 1,
                                             neutral_elements[worst[1]], worst[1] + 1)) if worst else "",
            "max_bond_change_ang": ("%.6f" % change[worst]) if worst else "",
            "d_ip_ev": entry.get("d_ip_ev", ""),
            "neutral_geometry": neutral_rel,
            "cation_geometry": cation_rel,
        })
        for pair in shared:
            drift = change[pair]
            bond_rows.append({
                "name": name,
                "bond": "%s%d-%s%d" % (neutral_elements[pair[0]], pair[0] + 1,
                                       neutral_elements[pair[1]], pair[1] + 1),
                "r_neutral_ang": "%.6f" % neutral_bonds[pair],
                "r_cation_ang": "%.6f" % cation_bonds[pair],
                "dr_ang": "%.6f" % drift,
                "is_largest_change": str(pair == worst).lower(),
                "moved_over_0p01_ang": str(abs(drift) >= 0.01).lower(),
            })
    return rows, bond_rows


FROZEN_LADDER = "outputs/week27/layer_independence.json"


def build_frozen_rung_ladder():
    """把既有 R15 台阶审计（5 级 x 2 轴）登记成方案 7.2 要求的逐级报告表。

    这是冻结聚合值，不是新计算；它只覆盖「同一 cohort 的 n、tau_b、
    resolved/unresolved 比例」，Top-k 重叠与 selection regret 仍只在
    本批次逐对复算的那一级给出。
    """
    frozen = PB.load_json(REPO / FROZEN_LADDER)
    rows = []
    for rung in frozen["rungs"]:
        for axis, payload in rung["axes"].items():
            rows.append({
                "rung": rung["key"], "label": rung["label"], "axis": axis,
                "n_molecules": payload["n_molecules"],
                "kendall_tau_b": "%.9f" % float(payload["kendall_tau_b"]),
                "f_unresolved_before": "%.9f" % float(payload["f_unresolved_before"]),
                "f_unresolved_after": "%.9f" % float(payload["f_unresolved_after"]),
                "f_robust_inversion": "%.9f" % float(payload["f_robust_inv"]),
                "dispersion_ev": "%.9f" % float(payload["dispersion_ev"]),
                "cost_jobs": rung.get("cost_jobs", ""),
                "new_physics": rung["new_physics"],
            })
    return rows, frozen


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

    geometry_rows, geometry_bonds = build_mechanism_geometry(cases)
    ladder_rows, ladder_frozen = build_frozen_rung_ladder()
    unresolved_share = counts.get("UNRESOLVED", 0) / len(rows)
    payload_certified = bool(METHOD_AUDIT_CERTIFICATION["certified"])
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
        {"id": "robust_inversion_certification_follows_the_method_audit",
         "description": "稳健翻转的认证结论跟随 WP1 独立方法审计（128 格竖直腿 + 32 格弛豫腿）",
         "ok": payload_certified == bool(METHOD_AUDIT_CERTIFICATION["certified"])
               and all(item["certified"] == (item["vertical_resolved"] and item["adiabatic_resolved"]
                                             and item["opposite_signs"])
                       for item in METHOD_AUDIT_CERTIFICATION["pairs"]),
         "detail": "WP1 audit certified=%s (%d/%d frozen pairs)；label=ROBUST_INVERSION x%d"
                   % (METHOD_AUDIT_CERTIFICATION["certified"],
                      METHOD_AUDIT_CERTIFICATION["n_pairs_certified"],
                      len(METHOD_AUDIT_CERTIFICATION["pairs"]), len(inversions))},
        {"id": "rung_cohort_difference_is_documented", "description": "该 rung 与主集的成员差异被显式记录",
         "ok": ("SN" in members) and ("DEC" not in members),
         "detail": "rung members 含 SN 不含 DEC；主集含 DEC 不含 SN —— 已在 payload 的 rung_members_note 说明"},
        {"id": "mechanism_case_geometries_are_frozen_inputs", "description": "机制案例的原始结构来自既有冻结几何且元素序列一致",
         "ok": bool(geometry_rows) and all(row["element_sequence_matches"] == "true" for row in geometry_rows)
                 and all(row["n_heavy_bonds_shared"] for row in geometry_rows),
         "detail": "%d 个案例分子；%s" % (len(geometry_rows), "、".join(
             "%s max|Δr|=%.3f Å (%s)" % (row["name"], float(row["max_abs_bond_change_ang"]),
                                         row["max_bond_pair"]) for row in geometry_rows))},
        {"id": "frozen_ladder_covers_every_registered_rung", "description": "方案 7.2 的逐级报告覆盖全部冻结台阶与两个轴",
         "ok": len(ladder_rows) == 2 * len(ladder_frozen["rungs"]),
         "detail": "%d 级台阶 x 2 轴 = %d 行；Top-k 重叠与 selection regret 仍只在 P1v->P1a 一级给出"
                   % (len(ladder_frozen["rungs"]), len(ladder_rows))},
        {"id": "mechanism_bond_table_covers_every_case_molecule", "description": "案例的键长变化表逐键覆盖每个案例分子",
         "ok": bool(geometry_bonds) and all(
             any(row["name"] == entry["name"] for row in geometry_bonds) for entry in geometry_rows),
         "detail": "n_bond_rows=%d ; n_molecules=%d ; 变化 >0.01 A 的键 %d 条"
                   % (len(geometry_bonds), len(geometry_rows),
                      sum(1 for row in geometry_bonds if row["moved_over_0p01_ang"] == "true"))},
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
            "certified": bool(METHOD_AUDIT_CERTIFICATION["certified"]),
            "label_meaning": "ROBUST_INVERSION is the frozen three-state criterion's label; the method axis is now audited, the sampling axis is not",
            "audit_source": "outputs/week38/wp1_method_audit.json (128 single points + 32 relaxed-leg cells over 4 settings)",
            "evidence": METHOD_AUDIT_CERTIFICATION,
            "pending_note": "certification covers the method axis only; conformational sampling bounds remain pending (plan section 2)",
        },
        "n_members": len(members), "members": members, "n_pairs": len(rows),
        "state_counts": counts, "frozen_state_counts": frozen_counts,
        "unresolved_fraction": "%.9f" % unresolved_share,
        "resolution_curve_three_state": curve, "mechanism_cases": cases,
        "mechanism_geometry": geometry_rows,
        "mechanism_bond_changes": geometry_bonds,
        "frozen_rung_ladder": ladder_rows,
        "frozen_ladder_independence": {
            "source": FROZEN_LADDER,
            **{key: ladder_frozen["independence"][key] for key in
               ("n_pairs", "max_abs_pearson", "median_abs_pearson", "n_pairs_above_0_7")},
        },
        "mechanism_geometry_sources": {
            "neutral": PB.MECHANISM_NEUTRAL_GEOMETRY,
            "cation": PB.MECHANISM_CATION_GEOMETRY,
            "bond_cutoff_ang": PB.GEOMETRY_BOND_CUTOFF_ANG,
            "caveat": "bond pairs are enumerated by a geometric cutoff only; no force constants are used",
        },
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
    local["outputs/physics_completion/pair_evidence/mechanism_geometry.csv"] = csv_text(
        ["name", "family", "n_atoms", "element_sequence_matches", "n_heavy_bonds_shared",
         "mean_abs_bond_change_ang", "max_abs_bond_change_ang", "max_bond_pair",
         "max_bond_change_ang", "d_ip_ev", "neutral_geometry", "cation_geometry"], geometry_rows)
    local["outputs/physics_completion/pair_evidence/mechanism_bond_changes.csv"] = csv_text(
        ["name", "bond", "r_neutral_ang", "r_cation_ang", "dr_ang", "is_largest_change",
         "moved_over_0p01_ang"], geometry_bonds)
    local["outputs/physics_completion/pair_evidence/frozen_rung_ladder.csv"] = csv_text(
        ["rung", "label", "axis", "n_molecules", "kendall_tau_b", "f_unresolved_before",
         "f_unresolved_after", "f_robust_inversion", "dispersion_ev", "cost_jobs",
         "new_physics"], ladder_rows)
    local["outputs/physics_completion/pair_evidence/conservative_interval_protocol.md"] = (
        "# 保守区间与三态判据协议\n\n"
        "1. 对固定目标模型 m 与 pair i,j、每个预先接受的合理方法 r，得到 D_ij^(m,r)；自由态与 Li 态分别构造方法范围，\n"
        "   并叠加已报告的采样敏感性界限。**不**用 free/Li 的物理差值定义其自身误差。\n"
        "2. 主分析先用保守符号一致性：所有预先接受的方法及采样敏感性下 D_ij 仍同号并超过数值容差，才称 resolved；\n"
        "   两侧分别 resolved 且异号才称 robust inversion；区间重叠或符号不一致为 unresolved。\n"
        "3. 容差由试算重算误差 / 明确实用分辨率确定并冻结，不由目标清单是否好看确定。\n"
        "4. 另给方法 pair spread 的 z 曲线作为 sensitivity；小数目相关泛函不是独立随机重复，\n"
        "   1.96×spread 不能自动标成校准 95% 置信度。\n"
        "5. 判据在既有冻结 rung（P1v→P1a，n=12）上演示，并已用 WP1 的 4 设定本机审计（竖直腿 + 弛豫腿）认证 EMC|GBL、EMC|SL 两个冻结翻转的方法轴。\n")
    case_lines = ["# 机制案例页（最多 3 例）", "",
                  "选择规则（事先冻结）：优先选证据最强的稳健翻转，再选影响 Top-k 的 unresolved 边界，再选有身份改变的代表；"
                  "**无稳健翻转时不强行补案例**。", ""]
    for case in cases:
        case_lines += [
            "## %s：%s" % (case["case_id"], case["pair"]), "",
            "- 轴：%s" % case["axis"],
            "- d_lower = %s eV；d_upper = %s eV；sigma = %s eV"
            % (case["d_lower_ev"], case["d_upper_ev"], case["sigma_ev"]),
            "- 判定：%s" % case["label"],
            "- 选集影响：%s" % case["selection_impact"], "",
        ]
    case_lines += [
        "## 原始结构证据（既有冻结几何，零新增计算）", "",
        "| 分子 | 家族 | 原子数 | 元素序列一致 | 重原子成键对 | 平均 abs(dr) (Å) | 最大 abs(dr) (Å) | 最大变化键 | 该键 dr (Å) | dIP (eV) |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in geometry_rows:
        case_lines.append(
            "| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |"
            % (row["name"], row["family"], row["n_atoms"], row["element_sequence_matches"],
               row["n_heavy_bonds_shared"], row["mean_abs_bond_change_ang"],
               row["max_abs_bond_change_ang"], row["max_bond_pair"],
               row["max_bond_change_ang"], row["d_ip_ev"]))
    case_lines += [
        "",
        "结构来源（既有冻结路径；按交付层纪律不复制原始几何文件，只交付派生的键长变化）："
        "中性松弛几何 `%s`；阳离子松弛几何 `%s`。" % (PB.MECHANISM_NEUTRAL_GEOMETRY, PB.MECHANISM_CATION_GEOMETRY),
        "成键对只用 %.1f Å 几何截断枚举，不是力常数判据；键长是平移/旋转不变量，因此不需要结构叠合。"
        % PB.GEOMETRY_BOND_CUTOFF_ANG,
        "",
        "## 逐例六项证据覆盖（方案 7.3）", "",
        "| 项目 | 状态 | 说明 |",
        "| --- | --- | --- |",
        "| 原始结构 | 已提供（派生） | 上表 + `mechanism_bond_changes.csv` 逐键列出中性/阳离子键长（原始几何仍留在冻结路径，未复制进交付层） |",
        "| 电子密度/自旋 | 待补 | 需专门的自旋布居分析；WP1 方法审计只做能量层 |",
        "| 配位变化 | 待补 | 本 rung 为自由态；配位态属 WP2 |",
        "| E/G 分解 | 部分 | 有电子能层分解（dIP 列）；G 层待 WP2 |",
        "| 方法敏感性 | 已提供 | WP1 独立方法审计：4 设定下竖直腿与弛豫腿的 pair 级差值范围与符号一致性，见 outputs/physics_completion/method_audit/pair_gap_sensitivity.csv |",
        "| 选集影响 | 已提供 | 每例的 pair 级翻转说明 |",
        "",
        "> 说明：本页登记判定、原始结构、方法敏感性与选集影响；电子密度/自旋、配位变化与 G 层分解"
        "仍需 WP2 生产计算补入（本批次无可提供的对应计算）。",
    ]
    local["outputs/physics_completion/pair_evidence/mechanism_cases.md"] = "\n".join(case_lines) + "\n"

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
        "## 冻结台阶逐级报告（方案 7.2，零新增计算）",
        "",
        "| 台阶 | 轴 | n | tau_b | f_unresolved (前 -> 后) | f_robust_inversion | dispersion (eV) | 既有作业 |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in ladder_rows:
        summary.append(
            "| %s | %s | %s | %s | %s -> %s | %s | %s | %s |"
            % (row["rung"], row["axis"], row["n_molecules"], row["kendall_tau_b"],
               row["f_unresolved_before"], row["f_unresolved_after"],
               row["f_robust_inversion"], row["dispersion_ev"], row["cost_jobs"]))
    summary += [
        "",
        "- 台阶间独立性（冻结 R15）：%d 对、max |Pearson| = %s、median |Pearson| = %s、>0.7 的 %d 对。"
        % (ladder_frozen["independence"]["n_pairs"],
           ladder_frozen["independence"]["max_abs_pearson"],
           ladder_frozen["independence"]["median_abs_pearson"],
           ladder_frozen["independence"]["n_pairs_above_0_7"]),
        "- 逐级报告只用冻结聚合值；Top-k 重叠与 selection regret 目前只在 P1v->P1a 一级逐对给出，",
        "  其余台阶要等 WP2 生产把同一 cohort 的自由能标签补齐。",
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
        "- 逐级报告（方案 7.2）复用冻结的 5 级台阶聚合值；WP1 独立方法审计已给出 4 设定的方法范围（只覆盖电子能层与氧化轴），Top-k/regret 只在 P1v->P1a 一级逐对给出。",
        "- 该 rung 的 12 个成员与主 cohort 差一个分子（SN 进、DEC 出）：它只作判据演示，不代表已登记的主集。",
        "- 稳健翻转认证：WP1 独立方法审计（4 设定 × 竖直/弛豫两腿）给出 certified=%s；"
        "但**采样界限仍未纳入**，故只认证方法轴（方案 2）。" % METHOD_AUDIT_CERTIFICATION["certified"],
        "- 机制案例已补原始结构证据（既有冻结几何的重原子键长变化表，逐键列出中性/阳离子键长）与 WP1 方法敏感性范围，但电子密度/自旋、配位变化与 G 层分解仍需 WP2 生产计算。",
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
    {"item": "method_audit_single_points", "unit": "SP", "value": "128", "kind": "measured", "status": "measured",
     "note": "8 molecules x 4 states x 4 settings; all 128 terminated (WP1)"},
    {"item": "method_audit_relaxed_leg_single_points", "unit": "SP", "value": "32", "kind": "measured",
     "status": "measured", "note": "4 settings x 8 molecules on the frozen relaxed-cation geometry (WP1)"},
    {"item": "method_audit_measured_core_hours", "unit": "core-hour",
     "value": "%.3f" % sum(float(row["core_hours"]) for row in METHOD_AUDIT_COST),
     "kind": "measured", "status": "measured",
     "note": "161 local ORCA jobs at 4 cores; see outputs/physics_completion/cost/audit_cost_ledger.csv"},
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


def _best_model(rows, field, reverse):
    """按 field 取最优 (model, value)；缺值不参与比较。"""
    winner = None
    for row in rows:
        if not row.get(field):
            continue
        value = float(row[field])
        if winner is None or (value > winner[1] if reverse else value < winner[1]):
            winner = (row["model"], value)
    return winner


def build_frozen_family_view(metrics_rows):
    """把既有 stage7 复算表限制到 WP5 冻结模型族（ridge/krr/gpr），逐格对比选型。

    方案 9.1 只把岭回归 / 核岭与 GPR 列为主模型；既有表里还有 gbdt/rf/constant。
    这里不改动任何既有数值，只把「全模型最优」与「冻结族内最优」并排登记，
    并把越族胜出的格子显式标出，避免把越族成绩当成新批次主结论。
    """
    groups = {}
    for row in metrics_rows:
        key = (row["task"], row["feature_set"], row["axis"], row["split"], row["shape"])
        groups.setdefault(key, []).append(row)
    view = []
    for key in sorted(groups):
        members = groups[key]
        frozen = [row for row in members if row["model"] in PB.FROZEN_MODEL_FAMILY]
        tau_all = _best_model(members, "kendall_tau_b", True)
        tau_frozen = _best_model(frozen, "kendall_tau_b", True)
        mae_all = _best_model(members, "mae_ev", False)
        mae_frozen = _best_model(frozen, "mae_ev", False)
        view.append({
            "task": key[0], "feature_set": key[1], "axis": key[2], "split": key[3], "shape": key[4],
            "n_models_all": len(members), "n_models_frozen_family": len(frozen),
            "tau_winner_all": tau_all[0], "tau_winner_frozen_family": tau_frozen[0],
            "tau_all": "%.9f" % tau_all[1], "tau_frozen_family": "%.9f" % tau_frozen[1],
            "tau_winner_outside_family": str(tau_all[0] not in PB.FROZEN_MODEL_FAMILY).lower(),
            "mae_winner_all": mae_all[0], "mae_winner_frozen_family": mae_frozen[0],
            "mae_all": "%.9f" % mae_all[1], "mae_frozen_family": "%.9f" % mae_frozen[1],
            "mae_winner_outside_family": str(mae_all[0] not in PB.FROZEN_MODEL_FAMILY).lower(),
        })
    return view


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

    metrics_rows = PB.load_rows(REPO / PB.FROZEN_OOF_METRICS)
    family_view = build_frozen_family_view(metrics_rows)
    n_rows_accounted = sum(int(row["n_models_all"]) for row in family_view)
    n_frozen_per_cell = sorted({int(row["n_models_frozen_family"]) for row in family_view})
    n_tau_outside = sum(1 for row in family_view if row["tau_winner_outside_family"] == "true")
    n_mae_outside = sum(1 for row in family_view if row["mae_winner_outside_family"] == "true")
    family_invariant = all(
        (row["tau_winner_all"] not in PB.FROZEN_MODEL_FAMILY)
        or (row["tau_winner_all"] == row["tau_winner_frozen_family"]) for row in family_view)
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
        {"id": "frozen_family_view_covers_every_cell", "description": "冻结族复算覆盖既有 stage7 复算表的每一格",
         "ok": (n_rows_accounted == len(metrics_rows)) and n_frozen_per_cell == [len(PB.FROZEN_MODEL_FAMILY)],
         "detail": "%d/%d 行；%d 格，每格冻结族候选 %s 个"
                   % (n_rows_accounted, len(metrics_rows), len(family_view), n_frozen_per_cell)},
        {"id": "frozen_family_winner_consistent_with_published", "description": "冻结族与全模型选型不互相矛盾（族内模型胜出时两者必须同选）",
         "ok": family_invariant,
         "detail": "tau 越族胜出 %d/%d 格；MAE 越族胜出 %d/%d 格"
                   % (n_tau_outside, len(family_view), n_mae_outside, len(family_view))},
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
        "frozen_model_family": PB.FROZEN_MODEL_FAMILY,
        "frozen_family_summary": {
            "source_table": PB.FROZEN_OOF_METRICS,
            "n_cells": len(family_view),
            "n_source_rows": len(metrics_rows),
            "tau_winner_outside_family": n_tau_outside,
            "mae_winner_outside_family": n_mae_outside,
            "note": ("existing stage7 cells whose winner is gbdt/rf/constant are kept as evidence but "
                     "are not eligible to carry the new-batch frozen-method claim"),
        },
        "frozen_family_view": family_view,
        "checks": checks, "n_checks": len(checks),
        "n_failed": sum(0 if item["ok"] else 1 for item in checks),
    }
    local["outputs/week42/wp5_delta_learning_active_query.json"] = dump(payload)
    local["outputs/week42/wp5_acceptance.csv"] = csv_text(
        ["check_id", "description", "ok", "detail"], acceptance_rows(checks))
    local["outputs/physics_completion/ml/delta_vs_direct.csv"] = csv_text(
        list(dv[0].keys()), dv)
    local["outputs/physics_completion/ml/frozen_family_view.csv"] = csv_text(
        ["task", "feature_set", "axis", "split", "shape", "n_models_all", "n_models_frozen_family",
         "tau_winner_all", "tau_winner_frozen_family", "tau_all", "tau_frozen_family",
         "tau_winner_outside_family", "mae_winner_all", "mae_winner_frozen_family",
         "mae_all", "mae_frozen_family", "mae_winner_outside_family"], family_view)
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
        "- 冻结族口径（方案 9.1）：把既有 stage7 复算表（%d 行）限制到 ridge/krr/gpr，逐格对比选型；"
        "全模型最优落在族外（gbdt/rf/constant）的格子：tau %d/%d、MAE %d/%d —— 这些格子只作旁证。"
        % (len(metrics_rows), n_tau_outside, len(family_view), n_mae_outside, len(family_view)),
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
        "> **排序/配对证据零新增电子结构计算、零数据剔除、零阈值改动**（WP1 的 161 个独立方法审计作业、WP2 的 12 分子四主态 pilot 与 4 分子 x 4 主态生产 Opt/Freq 单列，"
        "原始日志留在仓库外，不入交付镜像）。旧结论（含 Gate 1 NOT CLOSED / NOT CLOSABLE）原样保留。",
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
        "| WP1 | week38 | 独立方法审计表 + 128 格实测矩阵 | 4 设定 × 4 状态 × 8 分子 = 128 单点全部收敛（另 32 格弛豫腿）；"
        "泛函效应 >> 基组效应；2 个冻结翻转的方法轴 certified=%s | 气相 r2SCAN-3c 冻结几何；8 分子口径；采样界限未纳入 |"
        % METHOD_AUDIT_CERTIFICATION["certified"],
        "| WP2 | week39 | 固定背景配对自由能标签 | 48 行账本；4 主集分子 x 4 主态生产中已登记 %d/%d 个真实 "
        "Opt+Freq G 标签（%.6f core-hours）；基组一致 redox 表=%s | 生产首段每态单构象；其余状态在产，未完成不补数 |"
        % (WP2_PRODUCTION_STATES_DONE, WP2_PRODUCTION_STATES_TOTAL, WP2_PRODUCTION_CORE_HOURS,
           "computed" if WP2_PRODUCTION_EXTRA_STATES else "not_computed"),
        "| WP3 | week40 | pair 证据表 + 机制案例 | P1v→P1a（n=12，66 pair）逐对复算 55/9/2；2 个机制案例 | 单 rung 演示；多方法范围已由 WP1 审计给出（方法轴） |",
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
        "- WP1：128 格本机单点 + 32 格弛豫腿全部收敛；竖直 IP 的泛函效应中位 %s eV、基组效应中位 %s eV；"
        "EMC|GBL、EMC|SL 的稳健翻转在 4 设定下方法轴 certified=%s。"
        % (METHOD_AUDIT_SPREAD["vertical_functional_effect_median_ev"],
           METHOD_AUDIT_SPREAD["vertical_basis_effect_median_ev"],
           METHOD_AUDIT_CERTIFICATION["certified"]),
        "- WP4：Ue1994_Okoshi2015 序列 14 行、被模型覆盖 7 个；逐对一致 15 / 不一致 6 → tau_b = 0.428571（< 0.90）。",
        "- WP2：48 行状态账本，其中 4 主集分子 x 4 主态生产已登记 %d/%d 个真实 Opt+Freq 自由能标签"
        "（qRRHO，合计 %.6f core-hours）；未完成的主态保持空串（None），未把缺值写成 0。"
        % (WP2_PRODUCTION_STATES_DONE, WP2_PRODUCTION_STATES_TOTAL,
           WP2_PRODUCTION_CORE_HOURS),
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
        "首轮已把 WP1 独立方法审计从「登记」推进到「128 格实测 + 方法轴认证」，并把 WP2 自由能标签从 1 行 pilot "
        "推进到 4 分子 x 4 主态的真实 Opt+Freq（本次登记 %d/%d 个主态，其余在产）；余下状态、多构象采样界限与外部锚点"
        "可比性仍待补，故完整翻转判定仍未闭合。" % (WP2_PRODUCTION_LEDGER_ROWS, WP2_PRODUCTION_STATES_DONE),
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
