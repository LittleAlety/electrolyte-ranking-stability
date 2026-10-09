#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""Week 28 / WP1 -- 统一科学证据主表 (unified scientific evidence master table).

为什么有这个阶段
----------------
Week 27 (R15) 收口了第三轮对抗审计；外部评审把下一阶段重定义为七个工作包
WP1..WP7，并要求按 WP1 -> WP2 -> WP3 -> WP4 顺序推进、优先复用冻结产物，而不是
继续第四轮审计。WP1 是它们共同的前提：把目前散落在 outputs/week1..week27 的
物理量、状态身份、排序指标与计算成本，整理成一份可被论文直接引用的、版本冻结的
主表，且每一行都对应一个明确的 molecule x model x charge state x conformer/motif
计算对象。

WP1 要求的六张表
----------------
molecule_registry  化学空间（core 18 + broad 40）
state_registry     每个计算对象：电荷/多重度/化学计量/motif + QC 与 state identity
property_table     每个 (对象, rung, 轴) 一行：统一物理目标、值、单位、方向、来源
pairwise_table     每个 (i, j, rung-A, rung-B, 轴) 一行：两个模型下的 pair 差、
                   冻结的双臂不确定度 sigma_ij、两侧 resolved/UNRESOLVED 掩码、
                   R13 三态判据给出的 decision_state
decision_table     每个 (对比, 轴, k) 一行：Top-k overlap、Jaccard、selection regret
                   与 decision state 构成
cost_table         每个 rung：feature availability、job 数、wall seconds、失败数

另有 data_dictionary.md、sample_flow.md（样本流转图）与四项一致性审计，逐条回答
评审指定的四个必查问题。

复用的冻结口径（不重新发明）
----------------------------
* 方向：两轴 higher_is_better，ox = IP、red = -EA
  (config/scientific_definitions.yaml:axis_A_proxy_hierarchy)；
* pair 不确定度：sigma_ij = std([dP_A_ij, dP_B_ij], ddof=1)，即两个 realization
  A/B 的 pair 差的样本标准差，等价于 |dP_A - dP_B| / sqrt(2)
  (electrolyte_ranking.uncertainty.quantify_method_sigma)；
* 证据门槛：|dP_ij| >= max(z * sigma_ij, tolerance)，z = 1.0 为主判据
  (config/prereg.yaml)，z_only 场景 tolerance = 0；
* decision state：STABLE / UNRESOLVED / ROBUST_INVERSION
  (electrolyte_ranking.decision_state)；
* 还原轴的 state-identity 闸门：C1/C2 的还原轴只允许 molecule_centered_redox 进入
  主 ranking (R13，docs/state_identity_protocol.md)。

两个 scope
----------
all      不做 state-identity 过滤 —— 这是 Week 5/6 的原始口径，用于复核已有冻结数字
         （本脚本必须逐位复现 outputs/week6 的 stored pair 数值）。
primary  R13 口径，只让 molecule_centered_redox 进入主 ranking —— 论文主结果集合。

用法
----
    .venv\Scripts\python.exe scripts\build_week28_evidence_table.py
    .venv\Scripts\python.exe scripts\build_week28_evidence_table.py --check
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import statistics
import sys
from collections import Counter, OrderedDict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

import numpy as np  # noqa: E402

from electrolyte_ranking import decision_state, ranking, uncertainty  # noqa: E402

OUTDIR = REPO / "outputs" / "week28"
HARTREE_TO_EV = 27.211386245988

Z_PRIMARY = 1.0
Z_SENSITIVITY = 1.96
TOP_K_FRACTIONS = (0.10, 0.20, 0.30)

#: value_status 词表（check #4 要求四类分别编码，不得混用）
OK = "ok"
MISSING = "missing"
NOT_CONVERGED = "not_converged"
NOT_APPLICABLE = "not_applicable"
VALUE_STATUSES = (OK, MISSING, NOT_CONVERGED, NOT_APPLICABLE)

#: Week 6 起冻结的 12 分子审计子集。
AUDIT_SUBSET = (
    "EC", "PC", "DMC", "EMC", "DME", "DOL",
    "GBL", "AN", "SN", "DMSO", "SL", "TMP",
)

SCOPE_ALL = "all"
SCOPE_PRIMARY = "primary"

#: state identity 词表（R13）
MOLECULE_CENTERED = "molecule_centered_redox"
LI_CENTERED = "Li_centered_or_mixed_redox"
NO_INTACT_MINIMUM = "no_intact_minimum_found"

AXIS_OXIDATION = "oxidation"
AXIS_REDUCTION = "reduction"
AXES = (AXIS_OXIDATION, AXIS_REDUCTION)

#: 每个轴的统一目标量。两个模型只有在声明了同一个 (quantity, units, direction)
#: 三元组时才允许进入同一个 pair（check #1）。
TARGET_QUANTITY = {
    AXIS_OXIDATION: {"quantity": "IP", "units": "eV", "direction": "maximise"},
    AXIS_REDUCTION: {"quantity": "-EA", "units": "eV", "direction": "maximise"},
}


def _rung(axis_a, label, geometry_policy, thermochemistry, solvent, cost_class,
          source, scope, parameter=None, extra_note="", source_field="derived"):
    """One frozen rung of the ladder, with its own declared property definition."""

    return OrderedDict([
        ("rung", None),  # filled by the caller
        ("axis_A", axis_a),
        ("label", label),
        ("geometry_policy", geometry_policy),
        ("thermochemistry", thermochemistry),
        ("solvent", solvent),
        ("cost_class", cost_class),
        ("source", source),
        ("source_field", source_field),
        ("scope", scope),
        ("parameter", parameter),
        ("note", extra_note),
    ])


#: 冻结的 rung 注册表（R13 命名）。键是主表里 rung 的实际取值。
RUNG_REGISTRY = OrderedDict()
RUNG_REGISTRY["P0"] = _rung(
    "P0", "cheap scalar proxy (GFN2-xTB Koopmans orbital energy)",
    "G1 (single shared geometry, RDKit/MMFF seed, xTB single point)",
    "none (orbital energy)",
    "gas-phase (no continuum)",
    "cheap (GFN2-xTB only)",
    "outputs/week3/p0_core_set.csv", "core 18 + broad 40",
    source_field="p0_ox_ev | p0_red_ev",
)
RUNG_REGISTRY["P1v"] = _rung(
    "P1v", "gas-phase vertical redox-energy proxy (r2SCAN-3c, three states on one geometry)",
    "G1 shared by neutral/cation/anion (single point only)",
    "vertical: no relaxation and no ZPE for the charged state",
    "gas-phase (no continuum)",
    "expensive (r2SCAN-3c single point)",
    "outputs/week4/p1_core_set_derived.csv", "core 18",
    source_field="p1_ox_ev | p1_red_ev",
    extra_note="R13 alias: the early layer named P1 is this rung (config/scientific_definitions.yaml:legacy_aliases).",
)
RUNG_REGISTRY["P1a"] = _rung(
    "P1a", "gas-phase adiabatic redox thermodynamics (r2SCAN-3c, each charged state relaxed)",
    "G2 (per-charge-state r2SCAN-3c Opt started from G1)",
    "adiabatic: relaxed charged state, no ZPE",
    "gas-phase (no continuum)",
    "expensive (r2SCAN-3c geometry optimisation)",
    "outputs/phase2_p1a/p1a_adiabatic.csv", "audit 12",
    source_field="ip_p1a_ev | ea_p1a_ev",
    extra_note="Oxidation axis only: the frozen unbound_anion failure rule excludes the reduction axis.",
)
RUNG_REGISTRY["P2a"] = _rung(
    "P2a", "fixed continuum target: CPCM(SMD, acetonitrile) at G1",
    "G1 (shared, unchanged)",
    "vertical single points inside the production solvent model",
    "CPCM(SMD, acetonitrile)",
    "expensive (r2SCAN-3c single point in solvent)",
    "outputs/week4/p2_core_set_smd_acetonitrile.csv", "core 18",
    source_field="final_energy_eh(neutral,cation,anion) -> IP, EA",
)
RUNG_REGISTRY["C0"] = _rung(
    "C0", "free molecule at the G2 geometry (vertical single points)",
    "G2 (T2 relaxed neutral geometry)",
    "vertical single points at the relaxed neutral geometry",
    "gas-phase (no continuum)",
    "expensive (r2SCAN-3c single point)",
    "outputs/week4/t2_opt_freq.csv", "audit 12",
    source_field="ip_g2_ev | ea_g2_ev",
)
RUNG_REGISTRY["C1"] = _rung(
    "C1", "conditional state [LiM]+ (primary motif), vertical at the optimised complex geometry",
    "optimised [LiM]+ motif geometry (m_primary)",
    "vertical single points on the complex",
    "gas-phase (no continuum)",
    "expensive (r2SCAN-3c single point on the complex)",
    "outputs/week5/c1_coord_shifts.csv", "primary motif per molecule",
    source_field="ip_c1_ev | ea_c1_ev",
)
RUNG_REGISTRY["C2"] = _rung(
    "C2", "first-shell microsolvation [Li(M)2]+ (coordination number 2)",
    "optimised [Li(M)2]+ geometry",
    "vertical single points on the 1:2 complex",
    "gas-phase (no continuum)",
    "expensive (r2SCAN-3c single point on the 1:2 complex)",
    "outputs/week8/stage9_shell_shifts.csv", "audit 12",
    source_field="ip_shell2_ev | ea_shell2_ev",
    extra_note="R13 rename: C2 is the first solvation shell at coordination number 2, not a second shell.",
)
_P2EPS_SOURCES = {
    5.0: "outputs/week4/p2_core_set_cpcm_5.csv",
    10.0: "outputs/week4/p2_core_set_cpcm_10.csv",
    20.0: "outputs/week4/p2_core_set_cpcm_20.csv",
    40.0: "outputs/week4/p2_core_set_cpcm_40.csv",
}
for _eps, _src in _P2EPS_SOURCES.items():
    RUNG_REGISTRY["P2eps@%.1f" % _eps] = _rung(
        "P2eps", "bare CPCM dielectric scan (eps = %.1f) at G1" % _eps,
        "G1 (shared, unchanged)",
        "vertical single points, dielectric-only continuum (no SMD non-electrostatic terms)",
        "bare CPCM, eps = %.1f" % _eps,
        "expensive (r2SCAN-3c single point in solvent)",
        _src, "audit 12", parameter=_eps,
        source_field="final_energy_eh(neutral,cation,anion) -> IP, EA",
    )
for _key, _spec in RUNG_REGISTRY.items():
    _spec["rung"] = _key

#: 冻结的阶梯对比（WP2 的四个分析都落在这张表上）。
COMPARISONS = (
    ("P0_to_P1v", "P0", "P1v"),
    ("P1v_to_P1a", "P1v", "P1a"),
    ("P1v_to_P2a", "P1v", "P2a"),
    ("P1v_to_P2eps10", "P1v", "P2eps@10.0"),
    ("P0_to_P2a", "P0", "P2a"),
    ("C0_to_C1", "C0", "C1"),
    ("C1_to_C2", "C1", "C2"),
)

#: rung 是否带条件态（带条件态的 rung 需要 state-identity 闸门）。
CONDITIONAL_RUNGS = ("C1", "C2")

#: Week 6 冻结对比 -> 本表对比名（用于逐位复核 stored pair 数值）。
STAGE6_EQUIVALENTS = {
    "P0_to_P1": "P0_to_P1v",
    "P1_to_P2": "P1v_to_P2eps10",
    "C0_to_C1": "C0_to_C1",
}
STAGE6_JSON = "outputs/week6/stage6_decision_stability.json"
# ---------------------------------------------------------------------------
# 表结构（data_dictionary.md 由这里生成，保持同步）
# ---------------------------------------------------------------------------
SCHEMAS = OrderedDict()
SCHEMAS["molecule_registry"] = [
    ("mol_id", "项目内唯一分子 ID（core C01..C18 / broad B01..B40）"),
    ("name", "分子名（主表所有其它表的连接键）"),
    ("smiles", "SMILES"),
    ("family", "化学家族（linear_carbonate / ether / ester / sulfone / ...）"),
    ("role", "用途角色（solvent / co-solvent / additive）"),
    ("population", "所属分子池：core（18，双方法）或 broad（40，仅廉价层）"),
    ("donor_atoms", "给体原子标记（O=;O- 等）"),
    ("donor_count", "给体原子数"),
    ("donor_types", "去重后的给体元素类型（O / N / P / S）"),
    ("heteroatom_count", "杂原子数"),
    ("n_heavy", "重原子数"),
    ("mw", "分子量"),
    ("rotatable_bonds", "可旋转键数"),
    ("tpsa", "拓扑极性表面积"),
    ("functionalization_tags", "官能化标签（cyclic / fluorinated / chelating / ...）"),
    ("source_file", "该行元数据的来源文件"),
]
SCHEMAS["state_registry"] = [
    ("state_id", "计算对象唯一 ID：<mol_id>:<geometry/motif>:<charge_state>"),
    ("mol_id", "所属分子 ID"),
    ("name", "分子名"),
    ("family", "化学家族"),
    ("object_class", "C0_free_molecule / C1_conditional_LiM / C2_firstshell_microsolvation"),
    ("geometry_label", "几何标签（G1 = xTB 共享几何；G2 = T2 Opt+Freq 中性几何；motif id）"),
    ("charge", "形式电荷"),
    ("multiplicity", "自旋多重度"),
    ("stoichiometry", "该对象的化学计量（free molecule / LiM / Li(M)2）"),
    ("motif_id", "Li+ 配位 motif ID（C0 为空）"),
    ("coord_number", "第一配位壳 Li 的接触数（C2 为 2）"),
    ("state_identity_label", "R13 state identity 标签（仅条件态；C0 为空）"),
    ("label_source", "state identity 的判定依据（electron / ...）"),
    ("energy_reference", "该对象能量所在文件与字段（无独立能量时标 derived_only）"),
    ("energy_availability", "explicit / derived_only"),
    ("qc_state", "来源表里的 status 字段"),
    ("qc_flags", "QC flag 词表（v2 §20）"),
    ("parent_bonds_intact", "优化后母体分子键是否完整（条件态）"),
    ("source_file", "该行来源文件"),
]
SCHEMAS["property_table"] = [
    ("mol_id", "分子 ID"),
    ("name", "分子名（pair 连接键）"),
    ("family", "化学家族"),
    ("population", "core / broad"),
    ("rung", "物理层级：P0 / P1v / P1a / P2a / P2eps@e / C0 / C1 / C2"),
    ("axis_A", "该 rung 在 Axis A 上的归属（P0 / P1v / P1a / P2a / P2eps；条件态同其父层）"),
    ("axis", "oxidation（IP，越大越难氧化）或 reduction（-EA，越大越难还原）"),
    ("quantity", "统一目标量名（IP / -EA）"),
    ("units", "单位（eV）"),
    ("direction", "优化方向（maximise）"),
    ("value", "数值（eV）；非 ok 状态为空"),
    ("value_status", "ok / missing / not_converged / not_applicable"),
    ("status_reason", "非 ok 状态的原因（可追溯）"),
    ("qc_flags", "该对象的 QC flag"),
    ("state_id", "对应 state_registry.state_id（无条件态时为空）"),
    ("state_identity_label", "条件态的 state identity 标签"),
    ("in_primary_ranking", "是否进入 R13 主 ranking（条件态还原轴闸门）"),
    ("source_file", "数值来源文件（相对仓库根）"),
    ("source_field", "数值来源字段"),
]
SCHEMAS["pairwise_table"] = [
    ("comparison", "阶梯对比名（P0_to_P1v / P1v_to_P1a / P1v_to_P2a / P1v_to_P2eps10 / P0_to_P2a / C0_to_C1 / C1_to_C2）"),
    ("scope", "all（无 state-identity 过滤）或 primary（R13 主 ranking 集合）"),
    ("axis", "oxidation / reduction"),
    ("n_molecules", "该对比在该 scope 下的**实际候选数**（= 两个 rung 都有 ok 数值的分子，再按 scope 过滤）"),
    ("common_set_label", "候选集合的可读名字：core18 / audit12 / subsetNN / single_candidate；跨行比较 f_unresolved 前必须先看这一列"),
    ("rung_lower", "下台阶 rung"),
    ("rung_upper", "上台阶 rung"),
    ("i", "候选 i（高值优先）"),
    ("j", "候选 j"),
    ("d_lower_ev", "下台阶的 pair 差 P_i - P_j（eV）"),
    ("d_upper_ev", "上台阶的 pair 差 P_i - P_j（eV）"),
    ("delta_shift_ev", "(d_upper - d_lower)，即差异性位移 delta_i - delta_j（eV）"),
    ("sigma_ev", "冻结的双臂 pair 不确定度 sigma_ij = |d_lower - d_upper| / sqrt(2)（eV）"),
    ("z_primary", "主判据的 z（1.0，config/prereg.yaml）"),
    ("threshold_ev", "z * sigma_ij（eV）"),
    ("resolution_ratio_lower", "|d_lower| / threshold（无量纲）"),
    ("resolution_ratio_upper", "|d_upper| / threshold（无量纲）"),
    ("resolved_lower", "下台阶是否 resolve（|d| >= z*sigma）"),
    ("resolved_upper", "上台阶是否 resolve"),
    ("resolved_both", "两侧是否都 resolve（f_robust_inv 的分母成员）"),
    ("decision_state", "STABLE / UNRESOLVED / ROBUST_INVERSION"),
    ("structurally_non_testable", "Week 27 的代数约束：两侧都用同一 sigma_ij 且 z > 1/sqrt(2) 时不可能出现反向 pair"),
]
SCHEMAS["decision_table"] = [
    ("comparison", "阶梯对比名"),
    ("scope", "all / primary"),
    ("axis", "oxidation / reduction"),
    ("n_molecules", "候选数 n（该对比在该 scope 下的实际候选数；跨行不可比，见 common_set_label）"),
    ("common_set_label", "候选集合名字：core18 / audit12 / subsetNN / single_candidate"),
    ("n_pairs", "C(n,2)"),
    ("k_fraction", "Top-k 的 k/n（0.10 / 0.20 / 0.30）"),
    ("k", "Top-k 的绝对 k（四舍五入，至少 1）"),
    ("selected_lower", "下台阶选出的候选 ID（分号分隔）"),
    ("selected_upper", "上台阶选出的候选 ID"),
    ("overlap", "Top-k 集合重叠数 / k"),
    ("jaccard", "Top-k Jaccard 系数"),
    ("selection_regret_ev", "以更深一层为目标、以浅一层为代理的 selection regret（eV）"),
    ("kendall_tau_b", "Kendall tau_b"),
    ("spearman_rho", "Spearman rho"),
    ("f_unresolved_lower", "下台阶 UNRESOLVED pair 占比 (z=1.0)"),
    ("f_unresolved_upper", "上台阶 UNRESOLVED pair 占比 (z=1.0)"),
    ("f_unresolved_lower_z1p96", "下台阶 UNRESOLVED pair 占比 (z=1.96)"),
    ("f_unresolved_upper_z1p96", "上台阶 UNRESOLVED pair 占比 (z=1.96)"),
    ("n_stable", "decision state = STABLE 的 pair 数"),
    ("n_unresolved", "decision state = UNRESOLVED 的 pair 数"),
    ("n_robust_inversion", "decision state = ROBUST_INVERSION 的 pair 数"),
    ("f_robust_inversion", "ROBUST_INVERSION / 两侧都 resolve 的 pair 数（分母可为 0）"),
]
SCHEMAS["cost_table"] = [
    ("rung", "物理层级"),
    ("axis_A", "Axis A 归属"),
    ("cost_class", "cheap（仅 GFN2-xTB）或 expensive（r2SCAN-3c）"),
    ("feature_availability", "该 rung 作为特征时在建模时是否可得（廉价代理可用 / 必须完成该层计算后才可得）"),
    ("n_objects", "该 rung 有 property 行的**分子**数"),
    ("n_property_rows", "property_table 中该 rung 的总行数（= 分子 x 轴）"),
    ("n_value_rows", "property_table 中该 rung 的 ok 数值行数"),
    ("n_missing", "missing 行数"),
    ("n_not_converged", "not_converged 行数"),
    ("n_not_applicable", "not_applicable 行数"),
    ("n_qc_flagged", "带 QC flag 的对象数"),
    ("wall_seconds", "来源表记录的 wall seconds 之和（0.0 可能表示未记录）"),
    ("wall_seconds_note", "wall_seconds 的口径说明（未记录时明确写出，避免读成 0 成本）"),
    ("n_failed_jobs", "来源表 status != ok 的作业数"),
    ("source_file", "成本统计的来源文件"),
]


def read_rows(rel):
    path = REPO / rel
    with io.open(path, encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def read_json(rel):
    return json.loads((REPO / rel).read_text(encoding="utf-8"))


def num(raw):
    text = (raw or "").strip()
    if text == "":
        return None
    try:
        return float(text)
    except ValueError:
        return None


def truthy(raw):
    return (raw or "").strip().lower() in ("true", "1", "yes")


def blank():
    return OrderedDict([
        ("ox", None), ("red", None),
        ("status_ox", MISSING), ("status_red", MISSING),
        ("reason_ox", ""), ("reason_red", ""),
        ("qc_flags", ""), ("notes", {}),
    ])


def _set_value(record, axis, value, source_status, reason_ok="", reason_bad=""):
    """把来源表的一个数写进 record，并按词表定 value_status。"""

    if value is not None and (source_status or "ok").strip() == "ok":
        record[axis] = value
        record["status_" + axis] = OK
        record["reason_" + axis] = reason_ok
        return
    if value is not None:
        record[axis] = value
        record["status_" + axis] = NOT_CONVERGED
        record["reason_" + axis] = reason_bad or ("source status = %s" % source_status)
        return
    if (source_status or "ok").strip() != "ok":
        record["status_" + axis] = NOT_CONVERGED
        record["reason_" + axis] = reason_bad or ("source status = %s" % source_status)
    else:
        record["status_" + axis] = MISSING
        record["reason_" + axis] = reason_bad or "no value stored in the repository"


def load_p0():
    """P0：GFN2-xTB Koopmans（ox = -eps_HOMO，red = eps_LUMO）。"""

    table = {}
    for row in read_rows("outputs/week3/p0_core_set.csv"):
        rec = blank()
        rec["qc_flags"] = (row.get("qc_flags") or "").strip()
        rec["notes"] = {"charge": num(row.get("charge")), "multiplicity": num(row.get("multiplicity")),
                        "role": row.get("role", ""), "family": row.get("family", "")}
        _set_value(rec, "ox", num(row.get("p0_ox_ev")), row.get("status"))
        _set_value(rec, "red", num(row.get("p0_red_ev")), row.get("status"))
        table[row["name"]] = rec
    return table


def load_p1v():
    """P1v：derived 表上的 r2SCAN-3c 气相垂直量（G1 三态单点）。"""

    table = {}
    for row in read_rows("outputs/week4/p1_core_set_derived.csv"):
        rec = blank()
        rec["qc_flags"] = (row.get("qc_flags") or "").strip()
        rec["notes"] = {
            "role": row.get("role", ""), "family": row.get("family", ""),
            "ea_r2scan3c_bound": truthy(row.get("ea_r2scan3c_bound")),
        }
        _set_value(rec, "ox", num(row.get("p1_ox_ev")), row.get("status"))
        _set_value(rec, "red", num(row.get("p1_red_ev")), row.get("status"))
        table[row["name"]] = rec
    return table


def load_p1a(p1v):
    """P1a：气相绝热量；还原轴按冻结的 unbound_anion 规则排除。"""

    table = {}
    for row in read_rows("outputs/phase2_p1a/p1a_adiabatic.csv"):
        rec = blank()
        rec["qc_flags"] = (row.get("ea_qc_flags") or row.get("qc_flags") or "").strip()
        rec["notes"] = {"family": row.get("family", ""), "cation_status": (row.get("cation_status") or "").strip()}
        _set_value(rec, "ox", num(row.get("ip_p1a_ev")), "ok")
        bound = True
        sibling = p1v.get(row["name"])
        if sibling is not None:
            bound = bool(sibling["notes"].get("ea_r2scan3c_bound", True))
        if bound:
            _set_value(rec, "red", (-num(row.get("ea_p1a_ev")) if num(row.get("ea_p1a_ev")) is not None else None), "ok")
        else:
            rec["red"] = None
            rec["status_red"] = NOT_APPLICABLE
            rec["reason_red"] = ("frozen unbound_anion failure rule: the gas-phase anion is not a bound "
                                 "electronic state, so the adiabatic EA has no physical meaning; only the "
                                 "oxidation axis supports P1v -> P1a "
                                 "(config/scientific_definitions.yaml:P1a.failure_rule)")
        if rec["status_red"] != NOT_APPLICABLE and num(row.get("ea_p1a_ev")) is None:
            rec["status_red"] = MISSING
            rec["reason_red"] = "outputs/phase2_p1a/p1a_adiabatic.csv:ea_p1a_ev is empty"
        table[row["name"]] = rec
    return table


def _load_solvent_states(rel, layer_name):
    """把 ORCA 三态单点长表折算成 (ox = IP, red = -EA)，与 Week 6 的口径一致。"""

    energies = {}
    statuses = {}
    flags = {}
    seconds = {}
    for row in read_rows(rel):
        name = row["name"]
        energies.setdefault(name, {})[row["state"]] = num(row.get("final_energy_eh"))
        statuses.setdefault(name, []).append((row.get("status") or "").strip())
        if (row.get("qc_flags") or "").strip():
            flags.setdefault(name, []).append(row["qc_flags"].strip())
        seconds[name] = seconds.get(name, 0.0) + (num(row.get("seconds")) or 0.0)
    table = {}
    for name, states in energies.items():
        rec = blank()
        rec["qc_flags"] = ";".join(sorted({f for f in flags.get(name, [])}))
        worst = "ok" if all(s == "ok" for s in statuses.get(name, ["ok"])) else "failed"
        rec["notes"] = {"layer": layer_name, "family": "", "wall_seconds": seconds.get(name, 0.0),
                        "n_state_rows": len(statuses.get(name, []))}
        if {"neutral", "cation", "anion"} <= set(states) and all(
            states[k] is not None for k in ("neutral", "cation", "anion")
        ):
            ip = (states["cation"] - states["neutral"]) * HARTREE_TO_EV
            ea = (states["neutral"] - states["anion"]) * HARTREE_TO_EV
            _set_value(rec, "ox", ip, worst)
            _set_value(rec, "red", -ea, worst)
        else:
            for axis in ("ox", "red"):
                rec["status_" + axis] = NOT_CONVERGED if worst != "ok" else MISSING
                rec["reason_" + axis] = "source table lacks one of the neutral/cation/anion single points"
        table[name] = rec
    return table


def load_p2a():
    return _load_solvent_states("outputs/week4/p2_core_set_smd_acetonitrile.csv", "P2a")


def load_p2eps(eps):
    return _load_solvent_states("outputs/week4/p2_core_set_cpcm_%d.csv" % int(eps), "P2eps@%.1f" % eps)


def load_c0():
    """C0：自由分子在 G2 几何上的垂直单点。"""

    table = {}
    for row in read_rows("outputs/week4/t2_opt_freq.csv"):
        rec = blank()
        rec["qc_flags"] = (row.get("qc_flags") or "").strip()
        source_status = "ok" if (row.get("sp_status") or "").strip() == "ok" else "failed"
        rec["notes"] = {"family": row.get("family", ""), "geometry_label": "G2",
                        "opt_status": (row.get("opt_status") or "").strip(),
                        "wall_seconds": num(row.get("opt_seconds")) or 0.0}
        _set_value(rec, "ox", num(row.get("ip_g2_ev")), source_status)
        ea = num(row.get("ea_g2_ev"))
        _set_value(rec, "red", (-ea if ea is not None else None), source_status)
        table[row["name"]] = rec
    return table


def load_c1():
    """C1：主 motif 的条件态 [LiM]+。"""

    table = {}
    for row in read_rows("outputs/week5/c1_coord_shifts.csv"):
        if not truthy(row.get("is_primary")):
            continue
        rec = blank()
        rec["qc_flags"] = (row.get("qc_flags") or "").strip()
        rec["notes"] = {"family": row.get("family", ""), "motif_id": (row.get("motif_id") or "").strip(),
                        "li_contacts": (row.get("li_contacts") or "").strip()}
        _set_value(rec, "ox", num(row.get("ip_c1_ev")), "ok")
        ea = num(row.get("ea_c1_ev"))
        _set_value(rec, "red", (-ea if ea is not None else None), "ok")
        table[row["name"]] = rec
    return table


def load_c2():
    """C2：第一溶剂壳 [Li(M)2]+（配位数 2）。"""

    table = {}
    for row in read_rows("outputs/week8/stage9_shell_shifts.csv"):
        if not truthy(row.get("is_primary")):
            continue
        rec = blank()
        rec["qc_flags"] = (row.get("qc_flags") or "").strip()
        rec["notes"] = {"family": row.get("family", ""), "motif_id": (row.get("motif_id") or "").strip(),
                        "n_li_contacts_shell2": num(row.get("n_li_contacts_shell2"))}
        _set_value(rec, "ox", num(row.get("ip_shell2_ev")), "ok")
        ea = num(row.get("ea_shell2_ev"))
        _set_value(rec, "red", (-ea if ea is not None else None), "ok")
        table[row["name"]] = rec
    return table


# ---------------------------------------------------------------------------
# 主表构建
# ---------------------------------------------------------------------------
def build_molecule_registry():
    rows = []
    for rel, population in (("data/metadata/core_set.csv", "core"),
                            ("data/metadata/broad_pool.csv", "broad")):
        for row in read_rows(rel):
            donor_atoms = (row.get("donor_atoms") or "").strip()
            donor_types = "/".join(sorted({
                token for token in donor_atoms.replace("=", "").replace("-", "").split(";") if token
            }))
            rows.append(OrderedDict([
                ("mol_id", (row.get("mol_id") or "").strip()),
                ("name", (row.get("name") or "").strip()),
                ("smiles", (row.get("smiles") or "").strip()),
                ("family", (row.get("family") or "").strip()),
                ("role", (row.get("role") or "").strip()),
                ("population", population),
                ("donor_atoms", donor_atoms),
                ("donor_count", num(row.get("donor_count"))),
                ("donor_types", donor_types),
                ("heteroatom_count", num(row.get("heteroatom_count"))),
                ("n_heavy", num(row.get("n_heavy"))),
                ("mw", num(row.get("mw"))),
                ("rotatable_bonds", num(row.get("rotatable_bonds"))),
                ("tpsa", num(row.get("tpsa"))),
                ("functionalization_tags", (row.get("functionalization_tags") or "").strip()),
                ("source_file", rel),
            ]))
    return rows


def load_state_identity():
    """state_identity_stratification.csv -> (name -> row) 与 (name, motif, redox_state) 明细。"""

    summary = {}
    for row in read_rows("outputs/state_identity/state_identity_stratification.csv"):
        summary[row["name"]] = row
    detail = {}
    for row in read_rows("outputs/week5/c1_state_identity.csv"):
        detail[(row["name"], row["motif_id"], row["redox_state"])] = row
    return summary, detail


_G1_CHARGE = {"neutral": 0, "cation": 1, "anion": -1}
_G2A_CHARGE = {"neutral": 0, "cation": 1, "anion": -1}


def build_state_registry(identity_summary, identity_detail):
    rows = []

    def emit(mol_id, name, family, object_class, geometry_label, charge_state, charge,
             multiplicity, stoichiometry, motif_id, coord_number, label, label_source,
             energy_reference, availability, qc_state, qc_flags, bonds_intact, source_file):
        rows.append(OrderedDict([
            ("state_id", "%s:%s:%s" % (mol_id, geometry_label, charge_state)),
            ("mol_id", mol_id), ("name", name), ("family", family),
            ("object_class", object_class), ("geometry_label", geometry_label),
            ("charge", charge), ("multiplicity", multiplicity),
            ("stoichiometry", stoichiometry), ("motif_id", motif_id),
            ("coord_number", coord_number), ("state_identity_label", label),
            ("label_source", label_source), ("energy_reference", energy_reference),
            ("energy_availability", availability), ("qc_state", qc_state),
            ("qc_flags", qc_flags), ("parent_bonds_intact", bonds_intact),
            ("source_file", source_file),
        ]))

    # (1) 自由分子在 G1 上的三态单点（显式能量）
    for row in read_rows("outputs/week4/p1_core_set.csv"):
        emit(row["mol_id"], row["name"], row.get("family", ""), "C0_free_molecule", "G1",
             (row.get("state") or "").strip(), num(row.get("charge")), num(row.get("multiplicity")),
             "free molecule", "", 0, "", "",
             "outputs/week4/p1_core_set.csv:final_energy_eh", "explicit",
             (row.get("status") or "").strip(), (row.get("qc_flags") or "").strip(), "",
             "outputs/week4/p1_core_set.csv")

    # (2) 自由分子在 G2 上的三态单点（数值只在 t2_opt_freq.csv 里以 derived IP/EA 形式存在）
    for row in read_rows("outputs/week4/t2_opt_freq.csv"):
        for state in ("neutral", "cation", "anion"):
            emit(row["mol_id"], row["name"], row.get("family", ""), "C0_free_molecule", "G2",
                 state, _G1_CHARGE[state], 1 if state == "neutral" else 2,
                 "free molecule", "", 0, "", "",
                 "outputs/week4/t2_opt_freq.csv:ip_g2_ev|ea_g2_ev", "derived_only",
                 (row.get("sp_status") or "").strip(), (row.get("qc_flags") or "").strip(), "",
                 "outputs/week4/t2_opt_freq.csv")

    # (3) P1a 的逐电荷态弛豫（G2a）：只有阳离子能量被记录
    for row in read_rows("outputs/phase2_p1a/p1a_adiabatic.csv"):
        emit(row["mol_id"], row["name"], row.get("family", ""), "C0_free_molecule", "G2a",
             "neutral", 0, 1, "free molecule", "", 0, "", "",
             "outputs/phase2_p1a/p1a_adiabatic.csv:neutral_relaxed_eh", "explicit",
             "ok", (row.get("ea_qc_flags") or "").strip(), "",
             "outputs/phase2_p1a/p1a_adiabatic.csv")
        emit(row["mol_id"], row["name"], row.get("family", ""), "C0_free_molecule", "G2a",
             "cation", 1, 2, "free molecule", "", 0, "", "",
             "outputs/phase2_p1a/p1a_adiabatic.csv:cation_opt_eh", "explicit",
             (row.get("cation_status") or "").strip(), (row.get("ea_qc_flags") or "").strip(), "",
             "outputs/phase2_p1a/p1a_adiabatic.csv")

    # (4) C1 条件态 [LiM]+（主 motif 与非主 motif 全部登记，但标注 state identity）
    for row in read_rows("outputs/week5/c1_li_coordination.csv"):
        state = (row.get("state") or "").strip()
        motif = (row.get("motif_id") or "").strip()
        key = (row["name"], motif, state)
        detail = identity_detail.get(key, {})
        label = (detail.get("state_identity_label") or "").strip()
        if not label and state == "cation" and motif:
            label = ""
        emit(row["mol_id"], row["name"], row.get("family", ""), "C1_conditional_LiM",
             "C1:%s" % motif, state, num(row.get("charge")), num(row.get("multiplicity")),
             "LiM", motif, 1, label, (detail.get("label_source") or "").strip(),
             "outputs/week5/c1_li_coordination.csv:final_energy_eh", "explicit",
             (row.get("status") or "").strip(), (row.get("qc_flags") or "").strip(),
             (row.get("parent_bonds_intact") or "").strip(),
             "outputs/week5/c1_li_coordination.csv")

    # (5) C2 第一溶剂壳 [Li(M)2]+
    for row in read_rows("outputs/week8/stage9_jobs.csv"):
        state = (row.get("state") or "").strip()
        motif = (row.get("motif_id") or "").strip()
        emit(row["mol_id"], row["name"], row.get("family", ""), "C2_firstshell_microsolvation",
             "C2:%s" % motif, state, num(row.get("charge")), num(row.get("multiplicity")),
             "Li(M)2", motif, 2, "", "",
             "outputs/week8/stage9_jobs.csv:final_energy_eh", "explicit",
             (row.get("status") or "").strip(), (row.get("qc_flags") or "").strip(),
             (row.get("anchor_bonds_intact") or "").strip(),
             "outputs/week8/stage9_jobs.csv")
    return rows


#: rung -> (property_table 里 state_id 的角色描述)
def state_roles(rung, motif):
    if rung == "P0":
        return {"ox": "G1:neutral", "red": "G1:neutral"}
    if rung in ("P1v", "P2a") or rung.startswith("P2eps"):
        return {"ox": "G1:neutral|cation", "red": "G1:neutral|anion"}
    if rung == "P1a":
        return {"ox": "G2a:neutral|cation", "red": "G2a:neutral|anion"}
    if rung == "C0":
        return {"ox": "G2:neutral|cation", "red": "G2:neutral|anion"}
    if rung == "C1":
        return {"ox": "C1:%s:cation|dication" % motif, "red": "C1:%s:cation|reduced" % motif}
    if rung == "C2":
        return {"ox": "C2:%s:cation|dication" % motif, "red": "C2:%s:cation|reduced" % motif}
    raise KeyError(rung)


AXIS_KEY = {AXIS_OXIDATION: "ox", AXIS_REDUCTION: "red"}


def primary_gate(rung, axis, name, identity_summary):
    """R13 还原轴闸门：C1/C2 的还原轴只允许 molecule_centered_redox。"""

    if rung not in CONDITIONAL_RUNGS:
        return True, ""
    row = identity_summary.get(name)
    if row is None:
        return False, "state identity not stratified for this molecule (R13 gate)"
    label = (row["oxidation_label"] if axis == AXIS_OXIDATION else row["reduction_label"]).strip()
    return label == MOLECULE_CENTERED, label


#: 每个 rung 的声明范围出处（「缺失」只有对着一个被冻结的声明才有意义）。
DECLARED_SCOPE_SOURCE = {
    "P0": "config/scientific_definitions.yaml:dataset.core_set.purpose + dataset.broad_pool.purpose",
    "P1v": "config/scientific_definitions.yaml:dataset.core_set.n_rows = 18",
    "P1a": "config/prereg.yaml:amendment_log[R13].geometry_and_data = 'P1a 只在 T2 12 分子子集上执行'",
    "P2a": "config/scientific_definitions.yaml:dataset.core_set.n_rows = 18",
    "P2eps@5.0": "config/scientific_definitions.yaml:dataset.core_set + prereg 预注册 eps 扫描名单（12 分子审计子集）",
    "P2eps@10.0": "config/scientific_definitions.yaml:dataset.core_set + prereg 预注册 eps 扫描名单（12 分子审计子集）",
    "P2eps@20.0": "config/scientific_definitions.yaml:dataset.core_set + prereg 预注册 eps 扫描名单（12 分子审计子集）",
    "P2eps@40.0": "config/scientific_definitions.yaml:dataset.core_set + prereg 预注册 eps 扫描名单（12 分子审计子集）",
    "C0": "outputs/week4/t2_opt_freq_summary.json:subset（T2 12 分子审计子集）",
    "C1": "config/scientific_definitions.yaml:dataset.core_set.purpose = '完成 P0 / P1 / P2 以及 C1 conditional Li-coordination'",
    "C2": "config/scientific_definitions.yaml:axis_B_environment_states.C2.scope = '第一阶段只做 targeted sensitivity check'（无固定名单，上界取审计子集）",
}


def declared_scope(registry_rows):
    """每个 rung 声明覆盖的分子集合（用于把「缺失」显式编码出来）。"""

    core = [row["name"] for row in registry_rows if row["population"] == "core"]
    broad = [row["name"] for row in registry_rows if row["population"] == "broad"]
    audit = list(AUDIT_SUBSET)
    scope = OrderedDict([
        ("P0", core + broad),
        ("P1v", list(core)),
        ("P1a", list(audit)),
        ("P2a", list(core)),
        ("C0", list(audit)),
        ("C1", list(core)),
        ("C2", list(audit)),
    ])
    for eps in _P2EPS_SOURCES:
        scope["P2eps@%.1f" % eps] = list(audit)
    return scope


def build_property_table(values, registry_by_name, identity_summary, declared):
    rows = []
    for rung, spec in RUNG_REGISTRY.items():
        for name, rec in values[rung].items():
            meta = registry_by_name.get(name)
            if meta is None:
                continue
            motif = (rec["notes"].get("motif_id") or "").strip()
            roles = state_roles(rung, motif)
            for axis in AXES:
                key = AXIS_KEY[axis]
                gate_ok, gate_label = primary_gate(rung, axis, name, identity_summary)
                if rung in CONDITIONAL_RUNGS:
                    label = gate_label
                else:
                    label = ""
                rows.append(OrderedDict([
                    ("mol_id", meta["mol_id"]),
                    ("name", name),
                    ("family", meta["family"]),
                    ("population", meta["population"]),
                    ("rung", rung),
                    ("axis_A", spec["axis_A"]),
                    ("axis", axis),
                    ("quantity", TARGET_QUANTITY[axis]["quantity"]),
                    ("units", TARGET_QUANTITY[axis]["units"]),
                    ("direction", TARGET_QUANTITY[axis]["direction"]),
                    ("value", rec[key]),
                    ("value_status", rec["status_" + key]),
                    ("status_reason", rec["reason_" + key]),
                    ("qc_flags", rec["qc_flags"]),
                    ("state_id", "%s:%s" % (meta["mol_id"], roles[key])),
                    ("state_identity_label", label),
                    ("in_primary_ranking", gate_ok),
                    ("source_file", spec["source"]),
                    ("source_field", spec["source_field"]),
                ]))

    # 声明范围内但仓库里确实没有数值的对象：显式写成 missing，而不是静默丢弃。
    for rung, spec in RUNG_REGISTRY.items():
        for name in declared.get(rung, []):
            if name in values[rung]:
                continue
            meta = registry_by_name.get(name)
            if meta is None:
                continue
            roles = state_roles(rung, "none")
            for axis in AXES:
                key = AXIS_KEY[axis]
                gate_ok, _gate_label = primary_gate(rung, axis, name, identity_summary)
                reason = ("no value stored in the repository for this molecule at rung %s; "
                          "declared scope comes from config/scientific_definitions.yaml "
                          "(dataset.core_set / broad_pool) + the frozen audit subset, "
                          "source table %s has no row for it" % (rung, spec["source"]))
                if rung in CONDITIONAL_RUNGS:
                    reason += "; state identity cannot be established without the object"
                rows.append(OrderedDict([
                    ("mol_id", meta["mol_id"]),
                    ("name", name),
                    ("family", meta["family"]),
                    ("population", meta["population"]),
                    ("rung", rung),
                    ("axis_A", spec["axis_A"]),
                    ("axis", axis),
                    ("quantity", TARGET_QUANTITY[axis]["quantity"]),
                    ("units", TARGET_QUANTITY[axis]["units"]),
                    ("direction", TARGET_QUANTITY[axis]["direction"]),
                    ("value", None),
                    ("value_status", MISSING),
                    ("status_reason", reason),
                    ("qc_flags", ""),
                    ("state_id", "%s:%s" % (meta["mol_id"], roles[key])),
                    ("state_identity_label", ""),
                    ("in_primary_ranking", False if rung in CONDITIONAL_RUNGS else gate_ok),
                    ("source_file", spec["source"]),
                    ("source_field", spec["source_field"]),
                ]))
    return rows


def load_all_values():
    """把每个 rung 的数值装载成 {rung: {name: record}}。"""

    values = OrderedDict()
    values["P0"] = load_p0()
    values["P1v"] = load_p1v()
    values["P1a"] = load_p1a(values["P1v"])
    values["P2a"] = load_p2a()
    for eps in _P2EPS_SOURCES:
        values["P2eps@%.1f" % eps] = load_p2eps(eps)
    values["C0"] = load_c0()
    values["C1"] = load_c1()
    values["C2"] = load_c2()
    return values


def common_names(values, lower, upper, axis):
    key = AXIS_KEY[axis]
    names = []
    for name, rec in values[lower].items():
        if name not in values[upper]:
            continue
        if rec["status_" + key] != OK or values[upper][name]["status_" + key] != OK:
            continue
        if rec[key] is None or values[upper][name][key] is None:
            continue
        names.append(name)
    return sorted(names)


def compare_vectors(values, lower, upper, axis, names):
    """按冻结口径算一对 rung 的 pair 表：sigma_ij 来自两个 realization。"""

    a = np.asarray([values[lower][n][AXIS_KEY[axis]] for n in names], dtype=float)
    b = np.asarray([values[upper][n][AXIS_KEY[axis]] for n in names], dtype=float)
    sigma = uncertainty.quantify_method_sigma([a, b], ddof=1, stat="std")
    diff_a = ranking.pair_differences(a)
    diff_b = ranking.pair_differences(b)
    mask_a = ranking.resolved_mask(diff_a, sigma, z=Z_PRIMARY, tolerance=0.0)
    mask_b = ranking.resolved_mask(diff_b, sigma, z=Z_PRIMARY, tolerance=0.0)
    mask_a_196 = ranking.resolved_mask(diff_a, sigma, z=Z_SENSITIVITY, tolerance=0.0)
    mask_b_196 = ranking.resolved_mask(diff_b, sigma, z=Z_SENSITIVITY, tolerance=0.0)
    states = decision_state.decision_state_matrix(diff_a, diff_b, mask_a, mask_b)
    with np.errstate(divide="ignore", invalid="ignore"):
        threshold = Z_PRIMARY * sigma
        ratio_a = np.where(threshold > 0, np.abs(diff_a) / threshold, np.inf)
        ratio_b = np.where(threshold > 0, np.abs(diff_b) / threshold, np.inf)
    return {
        "names": names, "a": a, "b": b, "sigma": sigma,
        "diff_a": diff_a, "diff_b": diff_b,
        "mask_a": mask_a, "mask_b": mask_b,
        "mask_a_196": mask_a_196, "mask_b_196": mask_b_196,
        "states": states, "threshold": threshold,
        "ratio_a": ratio_a, "ratio_b": ratio_b,
    }


def _classify_common_set(names, core_names):
    """给每个对比的实际候选集合起一个可读名字，避免跨行比 f_unresolved。"""

    chosen = set(names)
    if chosen == set(AUDIT_SUBSET):
        return "audit12"
    if chosen == set(core_names):
        return "core18"
    if len(chosen) == 1:
        return "single_candidate"
    return "subset%02d" % len(chosen)


def build_pairwise_and_decision(values, scopes_by_comparison, identity_summary, core_names):
    pairwise_rows = []
    decision_rows = []
    summary = {}
    for label, lower, upper in COMPARISONS:
        summary[label] = {"rung_lower": lower, "rung_upper": upper, "axes": {}}
        for axis in AXES:
            base = common_names(values, lower, upper, axis)
            scopes = scopes_by_comparison[label][axis]
            summary[label]["axes"][axis] = {"n_common_available": len(base), "scopes": {}}
            for scope in scopes:
                if scope == SCOPE_PRIMARY:
                    names = [nm for nm in base
                             if primary_gate(lower, axis, nm, identity_summary)[0]
                             and primary_gate(upper, axis, nm, identity_summary)[0]]
                else:
                    names = list(base)
                entry = {"n_molecules": len(names)}
                if len(names) < 2:
                    entry["skipped"] = "fewer than two candidates after the %s filter" % scope
                    summary[label]["axes"][axis]["scopes"][scope] = entry
                    continue
                res = compare_vectors(values, lower, upper, axis, names)
                counts = decision_state.decision_state_counts(res["states"])
                fractions = decision_state.decision_state_fractions(res["states"])
                iu = np.triu_indices(len(names), 1)
                n_resolved_both = int(np.count_nonzero(res["mask_a"][iu] & res["mask_b"][iu]))
                f_robust = (0.0 if n_resolved_both == 0
                            else counts[decision_state.ROBUST_INVERSION] / n_resolved_both)
                for i, j in zip(iu[0], iu[1]):
                    pairwise_rows.append(OrderedDict([
                        ("comparison", label), ("scope", scope), ("axis", axis),
                        ("n_molecules", len(names)),
                        ("common_set_label", _classify_common_set(names, core_names)),
                        ("rung_lower", lower), ("rung_upper", upper),
                        ("i", names[i]), ("j", names[j]),
                        ("d_lower_ev", float(res["diff_a"][i, j])),
                        ("d_upper_ev", float(res["diff_b"][i, j])),
                        ("delta_shift_ev", float(res["diff_b"][i, j] - res["diff_a"][i, j])),
                        ("sigma_ev", float(res["sigma"][i, j])),
                        ("z_primary", Z_PRIMARY),
                        ("threshold_ev", float(res["threshold"][i, j])),
                        ("resolution_ratio_lower", float(res["ratio_a"][i, j])),
                        ("resolution_ratio_upper", float(res["ratio_b"][i, j])),
                        ("resolved_lower", bool(res["mask_a"][i, j])),
                        ("resolved_upper", bool(res["mask_b"][i, j])),
                        ("resolved_both", bool(res["mask_a"][i, j] and res["mask_b"][i, j])),
                        ("decision_state", str(res["states"][i, j])),
                        ("structurally_non_testable", Z_PRIMARY > 1.0 / (2.0 ** 0.5)),
                    ]))
                entry.update({
                    "n_pairs": int(len(names) * (len(names) - 1) // 2),
                    "kendall_tau_b": float(ranking.kendall_tau_b(res["a"], res["b"])),
                    "spearman_rho": float(ranking.spearman_rho(res["a"], res["b"])),
                    "f_unresolved_lower": float(ranking.unresolved_pair_fraction(res["mask_a"])),
                    "f_unresolved_upper": float(ranking.unresolved_pair_fraction(res["mask_b"])),
                    "f_unresolved_lower_z1p96": float(ranking.unresolved_pair_fraction(res["mask_a_196"])),
                    "f_unresolved_upper_z1p96": float(ranking.unresolved_pair_fraction(res["mask_b_196"])),
                    "n_resolved_both": n_resolved_both,
                    "f_robust_inversion": float(f_robust),
                    "decision_state_counts": {k: v for k, v in counts.items() if k != "n_pairs"},
                    "decision_state_fractions": fractions,
                    "labels": names,
                })
                for fraction in TOP_K_FRACTIONS:
                    k = ranking._resolve_k(round(fraction * len(names)), len(names))
                    k = max(1, min(k, len(names)))
                    selected_a = [names[idx] for idx in ranking._top_k_indices(res["a"], k, True)]
                    selected_b = [names[idx] for idx in ranking._top_k_indices(res["b"], k, True)]
                    decision_rows.append(OrderedDict([
                        ("comparison", label), ("scope", scope), ("axis", axis),
                        ("n_molecules", len(names)),
                        ("common_set_label", _classify_common_set(names, core_names)),
                        ("n_pairs", int(len(names) * (len(names) - 1) // 2)),
                        ("k_fraction", fraction), ("k", k),
                        ("selected_lower", ";".join(selected_a)),
                        ("selected_upper", ";".join(selected_b)),
                        ("overlap", float(ranking.top_k_overlap(res["a"], res["b"], k))),
                        ("jaccard", float(ranking.jaccard_at_k(res["a"], res["b"], k))),
                        ("selection_regret_ev", float(ranking.selection_regret(res["b"], res["a"], k))),
                        ("kendall_tau_b", entry["kendall_tau_b"]),
                        ("spearman_rho", entry["spearman_rho"]),
                        ("f_unresolved_lower", entry["f_unresolved_lower"]),
                        ("f_unresolved_upper", entry["f_unresolved_upper"]),
                        ("f_unresolved_lower_z1p96", entry["f_unresolved_lower_z1p96"]),
                        ("f_unresolved_upper_z1p96", entry["f_unresolved_upper_z1p96"]),
                        ("n_stable", counts[decision_state.STABLE]),
                        ("n_unresolved", counts[decision_state.UNRESOLVED]),
                        ("n_robust_inversion", counts[decision_state.ROBUST_INVERSION]),
                        ("f_robust_inversion", float(f_robust)),
                    ]))
                summary[label]["axes"][axis]["scopes"][scope] = entry
    return pairwise_rows, decision_rows, summary


def build_cost_table(property_rows):
    """每 rung 的成本行：feature availability / job 数 / wall seconds / 失败数。"""

    wall_sources = {
        "P0": ("outputs/week3/p0_core_set.csv", None),
        "P1v": ("outputs/week4/p1_core_set.csv", "seconds"),
        "P1a": ("outputs/phase2_p1a/p1a_adiabatic.csv", None),
        "P2a": ("outputs/week4/p2_core_set_smd_acetonitrile.csv", "seconds"),
        "C0": ("outputs/week4/t2_opt_freq.csv", "opt_seconds"),
        "C1": ("outputs/week5/c1_li_coordination.csv", "seconds"),
        "C2": ("outputs/week8/stage9_jobs.csv", "seconds"),
    }
    for eps, rel in _P2EPS_SOURCES.items():
        wall_sources["P2eps@%.1f" % eps] = (rel, "seconds")
    state_counts = Counter()
    for rel in ("outputs/week4/p1_core_set.csv", "outputs/week4/t2_opt_freq.csv",
                "outputs/phase2_p1a/p1a_adiabatic.csv", "outputs/week5/c1_li_coordination.csv",
                "outputs/week8/stage9_jobs.csv"):
        state_counts[rel] = len(read_rows(rel))

    rows = []
    for rung, spec in RUNG_REGISTRY.items():
        mine = [r for r in property_rows if r["rung"] == rung]
        rel, column = wall_sources[rung]
        if column is None:
            wall = 0.0
        else:
            wall = sum((num(r.get(column)) or 0.0) for r in read_rows(rel))
        n_failed = sum(1 for r in read_rows(rel)
                       if (r.get("status") or r.get("sp_status") or "ok").strip() != "ok")
        availability = ("usable before any expensive calculation (cheap proxy layer)"
                        if spec["cost_class"].startswith("cheap")
                        else "available only after this rung's r2SCAN-3c calculation is finished")
        rows.append(OrderedDict([
            ("rung", rung),
            ("axis_A", spec["axis_A"]),
            ("cost_class", spec["cost_class"]),
            ("feature_availability", availability),
            ("n_objects", len({r["name"] for r in mine})),
            ("n_property_rows", len(mine)),
            ("n_value_rows", sum(1 for r in mine if r["value_status"] == OK)),
            ("n_missing", sum(1 for r in mine if r["value_status"] == MISSING)),
            ("n_not_converged", sum(1 for r in mine if r["value_status"] == NOT_CONVERGED)),
            ("n_not_applicable", sum(1 for r in mine if r["value_status"] == NOT_APPLICABLE)),
            ("n_qc_flagged", sum(1 for r in mine if (r["qc_flags"] or "").strip())),
            ("wall_seconds", float(wall)),
            ("wall_seconds_note", (
                "summed from the %s column of %s" % (column, rel) if column
                else "the distilled table %s records no wall time; 0.0 means 'not recorded', not 'free'" % rel)),
            ("n_failed_jobs", n_failed),
            ("source_file", rel),
        ]))
    return rows


# ---------------------------------------------------------------------------
# 四项一致性检查（评审指定的必查项）+ 冻结数字复核
# ---------------------------------------------------------------------------
def _coverage(values, lower, upper):
    """两个 rung 在氧化/还原两轴上共同可用的分子集合。"""

    out = {}
    for axis in AXES:
        out[axis] = common_names(values, lower, upper, axis)
    return out


def reproduce_stage6(values):
    """逐位复核：本脚本必须复现 outputs/week6 已冻结的 stored pair 数值。"""

    payload = read_json(STAGE6_JSON)
    lookup = {label: (low, high) for label, low, high in COMPARISONS}
    results = []
    for stage6_label, mine_label in STAGE6_EQUIVALENTS.items():
        lower, upper = lookup[mine_label]
        for axis in AXES:
            stored = payload["results"]["z_only"][stage6_label][axis]
            names = list(stored["labels"])
            res = compare_vectors(values, lower, upper, axis, names)
            stored_pairs = {(p["i"], p["j"]): p for p in stored["pair_differences"]}
            max_abs_err = 0.0
            n_compared = 0
            mask_mismatches = []
            for i in range(len(names)):
                for j in range(i + 1, len(names)):
                    sp = stored_pairs.get((names[i], names[j]))
                    if sp is None:
                        continue
                    n_compared += 1
                    max_abs_err = max(
                        max_abs_err,
                        abs(float(res["diff_a"][i, j]) - float(sp["d_lower_ev"])),
                        abs(float(res["diff_b"][i, j]) - float(sp["d_upper_ev"])),
                        abs(float(res["sigma"][i, j]) - float(sp["sigma_ev"])),
                    )
                    if (bool(res["mask_a"][i, j]) != bool(sp["resolved_lower"])
                            or bool(res["mask_b"][i, j]) != bool(sp["resolved_upper"])):
                        mask_mismatches.append([names[i], names[j]])
            results.append({
                "stage6_label": stage6_label,
                "master_table_label": mine_label,
                "axis": axis,
                "n_molecules": len(names),
                "n_pairs_compared": n_compared,
                "max_abs_error_ev": max_abs_err,
                "n_mask_mismatches": len(mask_mismatches),
                "mask_mismatch_examples": mask_mismatches[:5],
                "ok": max_abs_err <= 1e-9 and not mask_mismatches,
            })
    return results


def reproduce_week4_p2a(values):
    """复核 P2a 的命名映射：week4 的 p2_decision_stability.json 把 "P2" 记为 SMD。

    主表把它登记为 P2a；如果映射错了，这里的 tau_b / spearman 不可能对上。
    """

    rel = "outputs/week4/p2_decision_stability.json"
    payload = read_json(rel)
    items = []
    for key, mine in (("p1_to_p2", "P1v_to_P2a"), ("p0_to_p2", "P0_to_P2a")):
        low, high = {"P1v_to_P2a": ("P1v", "P2a"), "P0_to_P2a": ("P0", "P2a")}[mine]
        for axis in AXES:
            stored = payload[key][axis]
            names = common_names(values, low, high, axis)
            res = compare_vectors(values, low, high, axis, names)
            tau = float(ranking.kendall_tau_b(res["a"], res["b"]))
            rho = float(ranking.spearman_rho(res["a"], res["b"]))
            items.append({
                "source": rel, "source_key": "%s.%s" % (key, axis),
                "master_table_label": mine, "rung_lower": low, "rung_upper": high,
                "axis": axis, "n_molecules": len(names),
                "kendall_tau_b_stored": float(stored["kendall_tau_b"]),
                "kendall_tau_b_master": tau,
                "spearman_rho_stored": float(stored["spearman_rho"]),
                "spearman_rho_master": rho,
                "max_abs_error": max(abs(tau - float(stored["kendall_tau_b"])),
                                     abs(rho - float(stored["spearman_rho"]))),
                "ok": max(abs(tau - float(stored["kendall_tau_b"])),
                          abs(rho - float(stored["spearman_rho"]))) <= 1e-9,
            })
    return items


def run_checks(property_rows, pairwise_rows, decision_rows, values, identity_summary, repro):
    checks = []

    # ---- check 0: provenance completeness -------------------------------
    absent = sorted({r["source_file"] for r in property_rows
                     if not (REPO / r["source_file"]).exists()})
    no_source = [r for r in property_rows if not (r["source_file"] or "").strip()
                 or not (r["source_field"] or "").strip()]
    checks.append({
        "id": "provenance_completeness",
        "question": "主文数字是否都能追溯到明确的分子、模型、状态和原始计算记录？",
        "ok": not absent and not no_source,
        "detail": ("%d property 行全部带 source_file + source_field；%d 个来源文件缺失"
                   % (len(property_rows), len(absent))),
        "evidence": {"n_rows": len(property_rows), "absent_sources": absent,
                     "n_rows_without_source": len(no_source)},
    })

    # ---- check 1: 同一 pair 的两个模型是否比较同一可解释目标量 ----------
    violations = []
    n_pairs_checked = len(pairwise_rows)
    per_rung_axis = {}
    for row in property_rows:
        per_rung_axis.setdefault((row["rung"], row["axis"]), set()).add(
            (row["quantity"], row["units"], row["direction"]))
    for (rung, axis), seen in sorted(per_rung_axis.items()):
        expected = (TARGET_QUANTITY[axis]["quantity"], TARGET_QUANTITY[axis]["units"],
                    TARGET_QUANTITY[axis]["direction"])
        if seen != {expected}:
            violations.append({"rung": rung, "axis": axis, "seen": sorted(seen),
                               "expected": list(expected)})
    for row in pairwise_rows:
        for side in ("rung_lower", "rung_upper"):
            if (row[side], row["axis"]) not in per_rung_axis:
                violations.append({"comparison": row["comparison"], "axis": row["axis"],
                                   "missing_rung_axis": [row[side], row["axis"]]})
    mixed = []
    by_key = {}
    for row in property_rows:
        if row["value_status"] != OK:
            continue
        by_key.setdefault((row["name"], row["axis"]), set()).add(
            (row["quantity"], row["units"], row["direction"]))
    for key, seen in by_key.items():
        if len(seen) > 1:
            mixed.append([key[0], key[1], sorted(seen)])
    declared = {label: (low, high) for label, low, high in COMPARISONS}
    comparison_defs = []
    for label, (low, high) in declared.items():
        a, b = RUNG_REGISTRY[low], RUNG_REGISTRY[high]
        differing = [field for field in ("geometry_policy", "thermochemistry", "solvent",
                                         "cost_class", "label")
                     if a[field] != b[field]]
        comparison_defs.append({"comparison": label, "rung_lower": low, "rung_upper": high,
                                "differing_fields": differing})
    checks.append({
        "id": "same_target_quantity",
        "question": "同一个 pair 的两个模型是否比较同一可解释的目标量？",
        "ok": not violations and not mixed,
        "detail": ("%d 个 pair 行全部使用 (quantity=%s / %s, units=eV, direction=maximise)；"
                   "没有任何 molecule x axis 在不同 rung 间混用不同目标量"
                   % (n_pairs_checked, TARGET_QUANTITY[AXIS_OXIDATION]["quantity"],
                      TARGET_QUANTITY[AXIS_REDUCTION]["quantity"])),
        "evidence": {"n_pair_rows": n_pairs_checked, "violations": violations[:5],
                     "n_mixed_targets": len(mixed), "mixed_examples": mixed[:5],
                     "comparison_definitions": comparison_defs},
    })

    # ---- check 2: P1v 与 P1a 是否是不同的属性定义 ------------------------
    reg_v, reg_a = RUNG_REGISTRY["P1v"], RUNG_REGISTRY["P1a"]
    definitional = (reg_v["geometry_policy"] != reg_a["geometry_policy"]
                    and reg_v["thermochemistry"] != reg_a["thermochemistry"]
                    and reg_v["label"] != reg_a["label"]
                    and reg_v["source"] != reg_a["source"])
    common = _coverage(values, "P1v", "P1a")[AXIS_OXIDATION]
    gaps = []
    for name in common:
        gaps.append({
            "name": name,
            "ip_p1v_ev": values["P1v"][name]["ox"],
            "ip_p1a_ev": values["P1a"][name]["ox"],
            "d_ip_ev": values["P1a"][name]["ox"] - values["P1v"][name]["ox"],
        })
    gap_values = [abs(g["d_ip_ev"]) for g in gaps]
    n_gap = sum(1 for g in gap_values if g > 0.0)
    n_unbound_p1v = sum(1 for n, rec in values["P1v"].items()
                        if rec["notes"].get("ea_r2scan3c_bound") is False)
    p1a_red = [rec["status_red"] for rec in values["P1a"].values()]
    n_p1a_red_values = sum(1 for s in p1a_red if s == OK)
    n_p1a_red_na = sum(1 for s in p1a_red if s == NOT_APPLICABLE)
    rule_ok = True
    for name, rec in values["P1a"].items():
        sibling = values["P1v"].get(name)
        expected_na = sibling is not None and sibling["notes"].get("ea_r2scan3c_bound") is False
        if expected_na and rec["status_red"] != NOT_APPLICABLE:
            rule_ok = False
    checks.append({
        "id": "p1v_vs_p1a_distinct",
        "question": "P1v 和 P1a 是否有不同的属性定义（而非只改了标签）？",
        "ok": bool(definitional and common and n_gap == len(common)
                   and n_p1a_red_values == 0 and rule_ok),
        "detail": ("定义层：几何策略（%s vs %s）与热化学（%s vs %s）都不同；"
                   "经验层：%d 个共同分子上 |IP(P1a)-IP(P1v)| > 0 全部成立，"
                   "中位 %.4f eV；还原轴按 unbound_anion 规则全部排除"
                   % (reg_v["geometry_policy"], reg_a["geometry_policy"],
                      reg_v["thermochemistry"], reg_a["thermochemistry"],
                      n_gap, statistics.median(gap_values) if gap_values else float("nan"))),
        "evidence": {
            "definitional_differs": bool(definitional),
            "n_molecules_compared": len(common),
            "n_with_nonzero_gap": n_gap,
            "d_ip_ev_min": min(gap_values) if gap_values else None,
            "d_ip_ev_median": statistics.median(gap_values) if gap_values else None,
            "d_ip_ev_max": max(gap_values) if gap_values else None,
            "all_gaps_negative": all(g["d_ip_ev"] < 0 for g in gaps),
            "n_p1v_unbound_anion_flagged": n_unbound_p1v,
            "n_p1a_reduction_excluded": n_p1a_red_na,
            "n_p1a_reduction_values": n_p1a_red_values,
            "per_molecule": gaps,
        },
    })

    # ---- check 3: Li-centered 还原是否被误用为分子还原 --------------------
    primary_by_axis = {}
    for axis, column in ((AXIS_OXIDATION, "oxidation_label"), (AXIS_REDUCTION, "reduction_label")):
        primary_by_axis[axis] = sorted(n for n, row in identity_summary.items()
                                       if (row[column] or "").strip() == MOLECULE_CENTERED)
    li_centered_reduction = sorted(n for n, row in identity_summary.items()
                                   if (row["reduction_label"] or "").strip() == LI_CENTERED)
    no_minimum = sorted(n for n, row in identity_summary.items()
                        if (row["oxidation_label"] or "").strip() == NO_INTACT_MINIMUM)
    c1_rows = [r for r in property_rows if r["rung"] in CONDITIONAL_RUNGS]
    gated_ok = all(r["state_identity_label"] == MOLECULE_CENTERED
                   for r in c1_rows if r["in_primary_ranking"])
    unscoped = [r for r in property_rows if r["rung"] in CONDITIONAL_RUNGS and r["value"] is not None
                and not (r["state_identity_label"] or "").strip()]
    c1_names = sorted(values["C1"])
    gate_primary_reduction = [nm for nm in c1_names
                              if primary_gate("C1", AXIS_REDUCTION, nm, identity_summary)[0]]
    excluded_reduction = [nm for nm in c1_names if nm not in gate_primary_reduction]
    misused = sorted(set(gate_primary_reduction) & set(li_centered_reduction))
    gated_ok = gated_ok and not misused
    legacy_reduction = {}
    for label, block in (("C0_to_C1", "C0_to_C1"), ("C1_to_C2", "C1_to_C2")):
        entry = None
        for row in decision_rows:
            if row["comparison"] == label and row["axis"] == AXIS_REDUCTION and row["scope"] == SCOPE_ALL:
                entry = row
                break
        legacy_reduction[label] = None if entry is None else entry["kendall_tau_b"]
    checks.append({
        "id": "li_centered_not_misused_as_molecular",
        "question": "Li-centered reduction 是否被误用为 molecule-centered reduction？",
        "ok": bool(gated_ok and not misused),
        "detail": ("C1/C2 的还原轴严格按 R13 闸门过滤：C1 的 %d 个候选里只有 %s 通过闸门，"
                   "另外 %d 个被排除在 primary scope 之外；旧的 all scope 还原排序"
                   "（含 Li-centered 对象）Kendall tau_b = %s，说明不加闸门时这条排序轴"
                   "在物理上不是同一件事"
                   % (len(c1_names), ";".join(gate_primary_reduction) or "(none)",
                      len(excluded_reduction),
                      legacy_reduction.get("C0_to_C1"))),
        "evidence": {
            "molecule_centered_oxidation": primary_by_axis[AXIS_OXIDATION],
            "molecule_centered_reduction": primary_by_axis[AXIS_REDUCTION],
            "li_centered_or_mixed_reduction": li_centered_reduction,
            "no_intact_minimum_oxidation": no_minimum,
            "n_conditional_rows_entering_primary": sum(1 for r in c1_rows if r["in_primary_ranking"]),
            "n_conditional_rows_total": len(c1_rows),
            "n_c1_molecules": len(c1_names),
            "c1_molecules": c1_names,
            "primary_reduction_after_gate": gate_primary_reduction,
            "excluded_from_primary_reduction": excluded_reduction,
            "n_excluded_from_primary_reduction": len(excluded_reduction),
            "legacy_all_scope_kendall_tau_b_reduction": legacy_reduction,
            "n_misused": len(misused),
            "misused": misused,
            "n_conditional_rows_without_identity_label": len(unscoped),
        },
    })

    # ---- check 4: 缺失 / 未收敛 / 未解析 / 不适用是否分别编码 -------------
    used = Counter(r["value_status"] for r in property_rows)
    unknown = sorted(set(used) - set(VALUE_STATUSES))
    missing_reason = [r for r in property_rows
                      if r["value_status"] != OK and not (r["status_reason"] or "").strip()]
    valued_non_ok = [r for r in property_rows
                     if r["value_status"] in (MISSING, NOT_APPLICABLE) and r["value"] is not None]
    pair_states = set(r["decision_state"] for r in pairwise_rows)
    unresolved_used = "UNRESOLVED" in pair_states
    unresolved_leak = [r for r in property_rows if r["value_status"] == "UNRESOLVED"]
    checks.append({
        "id": "status_vocabulary_separated",
        "question": "缺失、未收敛、未解析、不适用是否被分别编码？",
        "ok": (not unknown and not missing_reason and not valued_non_ok
               and unresolved_used and not unresolved_leak),
        "detail": ("property 层的 value_status 只用 %s；未解析（UNRESOLVED）只作为 "
                   "pairwise 层的 decision_state 出现，从不写进 value_status"
                   % "/".join(VALUE_STATUSES)),
        "evidence": {
            "counts": dict(used),
            "unknown_statuses": unknown,
            "n_non_ok_without_reason": len(missing_reason),
            "n_missing_or_na_with_value": len(valued_non_ok),
            "pairwise_decision_states": sorted(pair_states),
            "unresolved_used_in_pairwise": unresolved_used,
            "n_unresolved_leaked_into_value_status": len(unresolved_leak),
            "examples": [
                {"name": r["name"], "rung": r["rung"], "axis": r["axis"],
                 "value_status": r["value_status"], "status_reason": r["status_reason"][:120]}
                for r in property_rows if r["value_status"] != OK
            ][:8],
        },
    })

    # ---- reproduction of the frozen Week 6 numbers ----------------------
    p2a_items = reproduce_week4_p2a(values)
    repro = list(repro) + p2a_items
    checks.append({
        "id": "frozen_number_reproduction",
        "question": "本主表是否就是已发表冻结数字的同一个对象（而不是并行的一套定义）？",
        "ok": all(item["ok"] for item in repro),
        "detail": ("逐位复现 outputs/week6 的 6 组 stored pair 数值（最大绝对误差 %.3e eV），"
                   "并用 tau_b / spearman 复核 outputs/week4 的 4 组 P2a 数值（最大绝对误差 %.3e），"
                   "从而证明主表与已冻结数字是同一个对象、且 P2a/P2eps 的命名映射正确"
                   % (max((item.get("max_abs_error_ev", 0.0) for item in repro), default=0.0),
                      max((item.get("max_abs_error", 0.0) for item in repro), default=0.0))),
        "evidence": repro,
    })
    return checks


def build_coverage(values, declared, identity_summary, core_names):
    """逐对比逐轴对账：声明范围 / 实际可得 / scope 后真正使用的候选。

    这是回答「为什么 C0_to_C1 只有 10 个分子，而 declared_scope.C1 是 18」的唯一权威位置。
    """

    coverage = OrderedDict()
    for label, lower, upper in COMPARISONS:
        coverage[label] = OrderedDict()
        for axis in AXES:
            available = common_names(values, lower, upper, axis)
            primary = [nm for nm in available
                       if primary_gate(lower, axis, nm, identity_summary)[0]
                       and primary_gate(upper, axis, nm, identity_summary)[0]]
            declared_low = list(declared.get(lower, []))
            declared_up = list(declared.get(upper, []))
            coverage[label][axis] = OrderedDict([
                ("declared_lower", declared_low),
                ("declared_upper", declared_up),
                ("declared_intersection_size", len(set(declared_low) & set(declared_up))),
                ("available_common", available),
                ("n_available_common", len(available)),
                ("common_set_label", _classify_common_set(available, core_names)),
                ("used_all", available),
                ("used_primary", primary if len(primary) != len(available) else None),
                ("unavailable_declared", sorted(set(declared_low) & set(declared_up) - set(available))),
            ])
    return coverage


def build_scopes(values, identity_summary):
    """每个对比每个轴要输出哪些 scope（primary 与 all 相同则只输出 all）。"""

    scopes = OrderedDict()
    for label, lower, upper in COMPARISONS:
        scopes[label] = OrderedDict()
        conditional = lower in CONDITIONAL_RUNGS or upper in CONDITIONAL_RUNGS
        for axis in AXES:
            base = common_names(values, lower, upper, axis)
            entry = [SCOPE_ALL]
            if conditional:
                primary = [nm for nm in base
                           if primary_gate(lower, axis, nm, identity_summary)[0]
                           and primary_gate(upper, axis, nm, identity_summary)[0]]
                if len(primary) != len(base):
                    entry.append(SCOPE_PRIMARY)
            scopes[label][axis] = entry
    return scopes


# ---------------------------------------------------------------------------
# 渲染
# ---------------------------------------------------------------------------
def _fmt(value):
    if value is None:
        return ""
    if isinstance(value, bool):
        return "True" if value else "False"
    if isinstance(value, float):
        return repr(value)
    return str(value)


def write_csv(path, rows, columns):
    with io.open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(columns)
        for row in rows:
            writer.writerow([_fmt(row.get(column)) for column in columns])


def render_data_dictionary(payload):
    lines = [
        "# Week 28 / WP1 数据字典：统一科学证据主表",
        "",
        "> 本文件由 `scripts/build_week28_evidence_table.py` 确定性生成（`--check` 逐字节复核）。",
        "> 目录：`outputs/week28/`。上游口径：`config/scientific_definitions.yaml`、`config/prereg.yaml`。",
        "",
        "## 0. 三层口径（每一条结论都按这三层表述）",
        "",
        "- **模型事实**：两个指定计算模型给出的数值、排序或选择不同。",
        "- **统计判定**：这种差异是否超出独立、可辩护的不确定度。",
        "- **材料意义**：该差异是否影响具体筛选决策，以及目标是否具有外部参考支持。",
        "",
        "## 1. 表清单与行数",
        "",
        "| 表 | 文件 | 行数 | 说明 |",
        "| --- | --- | --- | --- |",
    ]
    descriptions = {
        "molecule_registry": "化学空间定义（core 18 + broad 40）",
        "state_registry": "每个计算对象的电荷/多重度/化学计量/motif 与 QC、state identity",
        "property_table": "每个 (对象, rung, 轴) 的统一物理目标、数值与来源",
        "pairwise_table": "每个 (i, j, 对比, 轴) 的 pair 差、sigma_ij 与 R13 三态判定",
        "decision_table": "每个 (对比, scope, 轴, k) 的 Top-k overlap / Jaccard / regret",
        "cost_table": "每个 rung 的 feature availability、job 数、wall seconds、失败数",
    }
    for table in SCHEMAS:
        lines.append("| `%s` | `outputs/week28/%s.csv` | %d | %s |"
                     % (table, table, payload["manifest"][table]["n_rows"], descriptions[table]))
    lines += ["", "## 2. value_status 词表", "",
              "| 取值 | 含义 | 是否允许带数值 |", "| --- | --- | --- |",
              "| `ok` | 来源表里有可解析的数值且来源 status 为 ok | 是 |",
              "| `missing` | 该对象在本 rung 的声明范围内，但仓库里没有存数值 | 否 |",
              "| `not_converged` | 作业跑过但 QC 未通过（SCF / 几何 / 状态） | 允许（会带 status_reason） |",
              "| `not_applicable` | 冻结规则把该对象排除出本 rung（例：`unbound_anion` 排除 P1a 还原轴） | 否 |",
              "",
              "`UNRESOLVED` **不是** value_status，它只作为 pair 层的 `decision_state` 出现。",
              "",
              "## 3. rung 注册表（把「模型」写清楚）",
              "",
              "| rung | Axis A | 目标定义 | 几何策略 | 热化学 | 溶剂 | 代价 | 来源 |",
              "| --- | --- | --- | --- | --- | --- | --- | --- |",
              ]
    for rung, spec in RUNG_REGISTRY.items():
        lines.append("| `%s` | %s | %s | %s | %s | %s | %s | `%s` |"
                     % (rung, spec["axis_A"], spec["label"], spec["geometry_policy"],
                        spec["thermochemistry"], spec["solvent"], spec["cost_class"], spec["source"]))
    lines += ["", "## 4. 逐表字段", ""]
    for table, columns in SCHEMAS.items():
        lines += ["### `%s`" % table, "", "| 字段 | 含义 |", "| --- | --- |"]
        for column, description in columns:
            lines.append("| `%s` | %s |" % (column, description))
        lines.append("")
    lines += [
        "## 5. scope 语义",
        "",
        "- `all`：不做 state-identity 过滤，即 Week 5/6 的原始口径；只用于复核冻结数字。",
        "- `primary`：R13 口径，C1/C2 的还原轴只让 `molecule_centered_redox` 进入主 ranking。",
        "- 当某个对比不含条件态 rung、或 `primary` 与 `all` 的候选集合完全相同时，只输出 `all`",
        "  行；此时“没有 `primary` 行”等价于“`primary` 与 `all` 相同”。",
        "",
        "### 5.1 连接键（跨表 join 只用 `name`）",
        "",
        "- 五张表的主连接键是 `name`（如 `EC`）；`molecule_registry` / `state_registry` / "
        "`property_table` 另外带 `mol_id`（如 `C04`）。",
        "- `pairwise_table.i` / `pairwise_table.j` 与 `decision_table.selected_*` 用的都是 `name`。",
        "- **不要拿 `mol_id` 去 join `pairwise_table`**：那张表里没有 `mol_id`，会静默失配。",
        "",
        "### 5.2 分母陷阱（本表最容易被误读的一点）",
        "",
        "- `scope='all'` **不是固定人群**：`n_molecules` 是「两个 rung 在该 scope 下都有 ok 数值」的",
        "  分子数，随对比变化（本阶段为 18 / 12 / 10）。",
        "- 因此 `f_unresolved` / `jaccard` / `overlap` / `n_pairs` 在 `decision_table` 的不同行之间",
        "  **不可直接比较**；比较前先看 `common_set_label`（`core18` / `audit12` / `subsetNN` / "
        "`single_candidate`）。",
        "- 声明范围与可得范围是两个不同的东西：`declared_scope` 是冻结设计声明的覆盖（每个 rung 的",
        "  出处见 `declared_scope_source`），`property_table` 里的 `missing` 行就是「声明了但仓库里",
        "  没有」的对象。`coverage` 块逐对比逐轴给出 declared / available / used 三者的对账。",
        "- 例：`declared_scope.C1` 是 core 18（`dataset.core_set.purpose` 明写包含 C1 conditional",
        "  Li-coordination），但 C1 实际只做到 10 个分子，所以 `C0_to_C1` 的 `n_molecules = 10`，",
        "  `PC` / `EMC` 在 property 表里是 `missing`。",
        "",
        "### 5.3 方向与符号陷阱",
        "",
        "- `pairwise_table` 的 `i`/`j` 按**字母序**排列，而 Week 6 的 stored pair 用的是它自己的顺序。",
        "  同一个无序 pair 在两张表里可能以相反方向出现，此时 `d_*` 与 `delta_shift_ev` 差一个负号；",
        "  按无序 pair 比对时应使用 `{i, j}` 并允许整体取负。`frozen_number_reproduction` 用的是",
        "  Week 6 自己的顺序，所以那里是逐位相等（误差 `0.000e+00`）。",
        "- 两轴都是 `higher_is_better`：`oxidation` 的数值是 IP，`reduction` 的数值是 `-EA`。",
        "",
        "## 6. 复用的冻结不确定度口径",
        "",
        "```",
        "sigma_ij = std([dP_A_ij, dP_B_ij], ddof=1) = |dP_A_ij - dP_B_ij| / sqrt(2)",
        "resolved <=> |dP_ij| >= max(z * sigma_ij, tolerance),  z = 1.0 (prereg), tolerance = 0 (z_only)",
        "```",
        "",
        "该口径是 Week 6 冻结的 two-arm 定义；`pairwise_table.sigma_ev` 必须能逐位复现",
        "`outputs/week6/stage6_decision_stability.json` 的 `sigma_ev`（见 check `frozen_number_reproduction`）。",
        "",
        "## 7. 结构性不可检验（Week 27 代数结论）",
        "",
        "在本约定下 `sigma_ij` 由两个模型共同定义，因此反向 pair 若两侧都要超过 `z * sigma_ij`，",
        "需要 `z <= 1/sqrt(2) = 0.7071`。主判据 `z = 1.0` 下反向 pair **不可能**同时通过两",
        "侧门槛，所以 `ROBUST_INVERSION = 0` 是**结构性的**，不能读成“排序稳定”的证据。",
        "`pairwise_table.structurally_non_testable` 对这一列逐行标注。",
        "",
    ]
    return "\n".join(lines) + "\n"


def render_sample_flow(payload):
    lines = [
        "# Week 28 / WP1 样本流转图（sample flow）",
        "",
        "> 由 `scripts/build_week28_evidence_table.py` 确定性生成。",
        "",
        "## 1. 计算对象 -> 物理层级 -> 决策的流转",
        "",
        "```mermaid",
        "flowchart TD",
        "  M[\"data/metadata/core_set.csv (18) + broad_pool.csv (40)<br/>molecule_registry\"] --> S",
        "  S[\"state_registry<br/>G1 / G2 / G2a 自由分子态 + C1/C2 条件态<br/>charge x multiplicity x motif x QC x state identity\"] --> P",
        "  SRC[\"outputs/week3, week4, week5, week8, phase2_p1a<br/>冻结的逐 rung 表格\"] --> P",
        "  P[\"property_table<br/>每行一个 (object, rung, axis)<br/>value + value_status + source_file:field\"] --> W",
        "  P --> C[\"cost_table<br/>feature availability / jobs / wall seconds / failures\"]",
        "  W[\"pairwise_table<br/>d_lower, d_upper, sigma_ij, resolved masks, decision_state<br/>scope = all | primary\"] --> D",
        "  W --> R[\"冻结数字复核<br/>= outputs/week6 stored pairs\"]",
        "  D[\"decision_table<br/>Top-k overlap / Jaccard / regret / tau_b / f_unresolved\"] --> OUT",
        "  OUT[\"WP2 (物理层级) / WP3 (条件态) / WP4 (决策可靠性) / WP5-WP6 (信息预算)\"]",
        "```",
        "",
        "## 2. 各 rung 的实际候选覆盖（common set 大小）",
        "",
        "| 对比 | 轴 | scope | 候选数 n | pair 数 |",
        "| --- | --- | --- | --- | --- |",
    ]
    for label, block in payload["comparisons"].items():
        for axis in AXES:
            for scope, entry in block["axes"][axis]["scopes"].items():
                n = entry.get("n_molecules", 0)
                lines.append("| %s | %s | %s | %d | %s |"
                             % (label, axis, scope, n,
                                entry.get("n_pairs", "—") if n >= 2 else "—"))
    lines += [
        "",
        "## 3. 被规则挡掉的样本（必须写明，不能静默丢弃）",
        "",
        "| 规则 | 挡掉的样本 | 原因 |",
        "| --- | --- | --- |",
    ]
    p1a_na = payload["checks_by_id"]["p1v_vs_p1a_distinct"]["evidence"]["n_p1a_reduction_excluded"]
    li_excluded = len(payload["checks_by_id"]["li_centered_not_misused_as_molecular"]
                      ["evidence"]["li_centered_or_mixed_reduction"])
    lines += [
        "| `unbound_anion` | P1a 还原轴 %d 个对象 | 气相阴离子不是束缚态，绝热 EA 无物理意义（冻结 failure_rule） |" % p1a_na,
        "| R13 state-identity 闸门 | 还原轴 %d 个 C1 对象 | Li-centered/mixed 还原不是分子还原，不得进入主 ranking |" % li_excluded,
        "| 数据缺失 | 见 `cost_table` 的 `n_missing` / `n_not_converged` | 仓库内确实没有数值，不强行补齐 |",
        "",
    ]
    return "\n".join(lines) + "\n"


def render_report(payload):
    checks = {c["id"]: c for c in payload["checks"]}
    lines = [
        "# Week 28 / WP1：统一科学证据主表（unified scientific evidence master table）",
        "",
        "> 阶段：下一阶段（评审实施方案）WP1。产物目录 `outputs/week28/`，交付镜像",
        "> `..\\成果输出（part2）\\week28/`。本文件由 `scripts/build_week28_evidence_table.py`",
        "> 确定性生成，`--check` 逐字节复核。零新增电子结构计算：全部数值来自 Week 1–27 的冻结产物。",
        "",
        "## 0. 一句话结论",
        "",
        "把 Week 1–27 散落的物理量、状态身份、排序指标与成本收敛成 6 张主表（共 %d 行），"
        "每一行都能追到 `molecule x model x charge state x motif` 与具体来源字段；"
        "并且在 `all` scope / `z_only` / `z = 1.0` 下**逐位复现**了 Week 6 已冻结的 pair 数字，"
        "证明这张主表就是已发表数字的同一个对象，而不是并行的一套定义。"
        % payload["n_rows_total"],
        "",
        "## 1. 主表规模",
        "",
        "| 表 | 行数 |",
        "| --- | --- |",
    ]
    for table in SCHEMAS:
        lines.append("| `%s` | %d |" % (table, payload["manifest"][table]["n_rows"]))
    lines += [
        "",
        "## 2. 四项必查结论",
        "",
        "| check | 问题 | 结论 | 关键数字 |",
        "| --- | --- | --- | --- |",
    ]
    order = ["provenance_completeness", "same_target_quantity", "p1v_vs_p1a_distinct",
             "li_centered_not_misused_as_molecular", "status_vocabulary_separated",
             "frozen_number_reproduction"]
    for cid in order:
        check = checks[cid]
        lines.append("| `%s` | %s | **%s** | %s |"
                     % (cid, check["question"], "PASS" if check["ok"] else "FAIL",
                        check["detail"].replace("\n", " ")))
    lines += ["", "## 3. 复核：主表 vs Week 6 冻结数字", "",
              "| Week 6 对比 | 主表对比 | 轴 | 分子数 | 复核 pair 数 | 最大绝对误差 (eV) | mask 不一致 |",
              "| --- | --- | --- | --- | --- | --- | --- |"]
    for item in checks["frozen_number_reproduction"]["evidence"]:
        if "stage6_label" in item:
            lines.append("| %s | %s | %s | %d | %d | %.3e | %d |"
                         % (item["stage6_label"], item["master_table_label"], item["axis"],
                            item["n_molecules"], item["n_pairs_compared"],
                            item["max_abs_error_ev"], item["n_mask_mismatches"]))
        else:
            lines.append("| %s (%s) | %s | %s | %d | metric only | %.3e | 0 |"
                         % (item["source_key"], item["source"], item["master_table_label"],
                            item["axis"], item["n_molecules"], item["max_abs_error"]))
    lines += ["", "## 4. 逐 rung 的候选与成本", "",
              "| rung | 代价 | ok 行 | missing | not_converged | not_applicable | QC 标记 | wall seconds | 失败作业 |",
              "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for row in payload["cost_table"]:
        lines.append("| `%s` | %s | %d | %d | %d | %d | %d | %.1f | %d |"
                     % (row["rung"], row["cost_class"], row["n_value_rows"], row["n_missing"],
                        row["n_not_converged"], row["n_not_applicable"], row["n_qc_flagged"],
                        row["wall_seconds"], row["n_failed_jobs"]))
    lines += [
        "",
        "## 5. 本阶段确认的七个口径事实（都带机器可查证据）",
        "",
        "1. **P1a 只有氧化轴**：`unbound_anion` 规则把 P1a 的还原轴整体排除，"
        "主表里这些行的 `value_status = not_applicable`（不是 missing、不是 0）。",
        "2. **C1/C2 还原轴的主 ranking 只剩分子中心还原**：stratification 里"
        " `molecule_centered_redox` 的还原对象是 "
        + (", ".join(checks["li_centered_not_misused_as_molecular"]["evidence"]["molecule_centered_reduction"]) or "(none)")
        + "；其余 %d 个 Li-centered/mixed 对象被排除在 `primary` scope 之外，"
        "但仍以 `all` scope 保留，供复现 Week 5/6。" % len(
            checks["li_centered_not_misused_as_molecular"]["evidence"]["li_centered_or_mixed_reduction"]),
        "3. **`ROBUST_INVERSION` 在 z = 1.0 下结构性不可检验**：`sigma_ij` 由两个模型共同定义，"
        "反向 pair 两侧同时过门槛需要 `z <= 1/sqrt(2)`，所以 `f_robust_inv = 0` 不是稳定性证据；"
        "`pairwise_table.structurally_non_testable` 逐行标注。",
        "4. **`P2` 在仓库里有两套同名含义**：Week 4 的 `p2_decision_stability.json` 把"
        " “P2” 记为 CPCM(SMD, acetonitrile)，Week 6 的 `analyze_stage6.py` 把 “P2” 记为"
        " bare CPCM ε=10。两者各自正确但同名，跨周引用时必然踩坑。R13 的 P2a / P2eps 拆分"
        "消除了歧义：主表分别登记为 `P2a` 与 `P2eps@10.0`，Week 6 的 `P1_to_P2` 对应"
        " `P1v_to_P2eps10`。该映射已用 tau_b / spearman 复核（见 check"
        " `frozen_number_reproduction` 的 metric 组）。",
        "5. **信息覆盖度显著不对称**：廉价层声明覆盖 58 个分子（core 18 + broad 40），"
        "而昂贵层只到 18（P1v / P2a）或 10–12（P1a / C0 / C1 / C2 / P2eps）。主表把 broad pool"
        " 的 P0 也登记进来，并把昂贵层的缺口显式写成 `missing`（P0 一栏 80 行），"
        "因此 WP4/WP6 的信息预算可以直接从 `cost_table` 读覆盖度，不必翻各周目录。",
        "6. **`scope='all'` 的分母随对比变化。** `n_molecules` 是两个 rung 都有 ok 数值的分子数，",
        "本阶段为 18（P0/P1v/P2a 系）、12（P1a / P2eps / C0）、10（C0→C1、C1→C2）。",
        "因此 `decision_table` 里 `f_unresolved` / `jaccard` / `overlap` **跨行不可比**，",
        "每行都带了 `common_set_label` 作为分母标签；`coverage` 块给出 declared / available / used 对账。",
        "7. **`C1` 的声明范围是 core 18，实际只做到 10。** `config/scientific_definitions.yaml:",
        "dataset.core_set.purpose` 明写 core set「完成 P0 / P1 / P2 以及 C1 conditional Li-coordination」，",
        "但仓库里 C1 只有 10 个分子（`PC` / `EMC` 没有 `[LiM]+` 对象），这 8 个缺口在主表里是",
        "`missing` 而不是被静默丢掉。这是下一阶段扩充计算时**最应该先补**的地方。",
        "",
        "## 5.1 独立复核（免费车道子智能体，只读）",
        "",
        "本阶段的主表另做过一次**独立复核**：一个只读子智能体在不知道生成代码结论的情况下自行重算，",
        "结论记录如下（它也促成了上一版的两处修正）。",
        "",
        "| 复核项 | 独立重算结果 |",
        "| --- | --- |",
        "| `sigma_ev = \\|d_lower - d_upper\\| / sqrt(2)`（P0_to_P1v / oxidation / all，153 行） | 与表内 `sigma_ev` 最大绝对误差 `4.44e-16`（浮点噪声）；`resolved_lower == (\\|d_lower\\| >= z*sigma)` 不一致 0 行 |",
        "| 对 Week 6 的 `z_only.P0_to_P1.oxidation`（66 个 pair） | 66/66 全部可见，最大绝对误差 `d_lower` 2.22e-16 / `d_upper` 4.44e-16 / `sigma` 1.11e-16；其中 24 个 pair 方向相反并整体取负 |",
        "| P1a 还原轴 | 12 行全部 `not_applicable`、`value` 全空 |",
        "| C1/C2 还原轴 `in_primary_ranking=True` | 只有 `SN`（C1 −3.207882 eV、C2 −2.818096 eV），标签均为 `molecule_centered_redox` |",
        "| 状态一致性 | `ok` 但值为空 0 行；非 `ok` 却有数值 0 行；`UNRESOLVED` 不出现在 `value_status` |",
        "",
        "它提出的两条质疑已被采纳并修正：",
        "",
        "- **方向/符号**：`pairwise_table` 按字母序排 `i`/`j`，与 Week 6 的存储顺序可能相反 →",
        "  已在数据字典 §5.3 写明。",
        "- **分母与声明范围不一致**：`declared_scope.C1` 原写作 12，与冻结声明（core 18）不符；",
        "  已改为 18 并补 `declared_scope_source` 出处与 `coverage` 对账块 → 见事实 6、7。",
        "",
        "## 6. 交给 WP2–WP4 的接口",
        "",
        "- WP2 直接用 `pairwise_table` / `decision_table` 的 `all` 与 `primary` 两个 scope；",
        "- WP3 用 `state_registry` + `property_table.in_primary_ranking` 组织 C0/C1/C2 机制案例；",
        "- WP4 用 `decision_table` 的 Top-k / regret 与 `pairwise_table` 的分辨率列；",
        "- WP5/WP6 用 `cost_table.feature_availability` 作为硬约束（不得把昂贵层的量当廉价输入）。",
        "",
        "## 7. 复现命令",
        "",
        "```powershell",
        ".venv\\Scripts\\python.exe scripts\\build_week28_evidence_table.py",
        ".venv\\Scripts\\python.exe scripts\\build_week28_evidence_table.py --check",
        ".venv\\Scripts\\python.exe -m pytest tests/test_week28_evidence_table.py -q",
        "```",
        "",
    ]
    return "\n".join(lines) + "\n"


TABLE_ORDER = ("molecule_registry", "state_registry", "property_table",
               "pairwise_table", "decision_table", "cost_table")


def collect():
    registry_rows = build_molecule_registry()
    registry_by_name = {row["name"]: row for row in registry_rows}
    identity_summary, identity_detail = load_state_identity()
    values = load_all_values()

    state_rows = build_state_registry(identity_summary, identity_detail)
    declared = declared_scope(registry_rows)
    property_rows = build_property_table(values, registry_by_name, identity_summary, declared)
    cost_rows = build_cost_table(property_rows)

    scopes = build_scopes(values, identity_summary)
    core_names = [row["name"] for row in registry_rows if row["population"] == "core"]
    pairwise_rows, decision_rows, comparisons = build_pairwise_and_decision(
        values, scopes, identity_summary, core_names)
    coverage = build_coverage(values, declared, identity_summary, core_names)
    repro = reproduce_stage6(values)
    checks = run_checks(property_rows, pairwise_rows, decision_rows, values,
                        identity_summary, repro)

    rows_by_table = OrderedDict([
        ("molecule_registry", registry_rows),
        ("state_registry", state_rows),
        ("property_table", property_rows),
        ("pairwise_table", pairwise_rows),
        ("decision_table", decision_rows),
        ("cost_table", cost_rows),
    ])

    csv_texts = OrderedDict()
    manifest = OrderedDict()
    for table in TABLE_ORDER:
        columns = [column for column, _ in SCHEMAS[table]]
        buffer = io.StringIO()
        writer = csv.writer(buffer, lineterminator="\n")
        writer.writerow(columns)
        for row in rows_by_table[table]:
            writer.writerow([_fmt(row.get(column)) for column in columns])
        text = buffer.getvalue()
        csv_texts[table + ".csv"] = text
        manifest[table] = OrderedDict([
            ("file", "outputs/week28/%s.csv" % table),
            ("n_rows", len(rows_by_table[table])),
            ("columns", columns),
            ("sha256", hashlib.sha256(text.encode("utf-8")).hexdigest()),
        ])

    payload = OrderedDict([
        ("stage", "Week 28 / WP1"),
        ("title", "unified scientific evidence master table"),
        ("plane", "next-phase implementation plan, work package WP1"),
        ("frozen_conventions", OrderedDict([
            ("direction", "oxidation: IP (eV) maximise; reduction: -EA (eV) maximise"),
            ("sigma_ij", "std([dP_A_ij, dP_B_ij], ddof=1) = |dP_A_ij - dP_B_ij| / sqrt(2)"),
            ("resolved_rule", "|dP_ij| >= max(z * sigma_ij, tolerance)"),
            ("z_primary", Z_PRIMARY), ("z_sensitivity", Z_SENSITIVITY),
            ("tolerance_z_only_ev", 0.0),
            ("decision_states", list(decision_state.DECISION_LABELS)),
            ("state_identity_gate", "C1/C2 reduction: molecule_centered_redox only (R13)"),
        ])),
        ("rung_registry", OrderedDict(
            (rung, OrderedDict((k, v) for k, v in spec.items()))
            for rung, spec in RUNG_REGISTRY.items())),
        ("declared_scope", OrderedDict((rung, names) for rung, names in declared.items())),
        ("declared_scope_source", OrderedDict(
            (rung, DECLARED_SCOPE_SOURCE[rung]) for rung in declared)),
        ("coverage", coverage),
        ("comparisons", comparisons),
        ("checks", checks),
        ("checks_by_id", OrderedDict((c["id"], c) for c in checks)),
        ("cost_table", cost_rows),
        ("manifest", manifest),
        ("n_rows_total", sum(len(rows) for rows in rows_by_table.values())),
    ])

    texts = OrderedDict(csv_texts)
    texts["evidence_master_table.json"] = (
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=False) + "\n")
    texts["data_dictionary.md"] = render_data_dictionary(payload)
    texts["sample_flow.md"] = render_sample_flow(payload)
    texts["evidence_master_table.md"] = render_report(payload)
    texts["manifest.json"] = json.dumps(
        OrderedDict([("stage", "Week 28 / WP1"), ("tables", manifest)]),
        ensure_ascii=False, indent=2, sort_keys=False) + "\n"
    return payload, texts


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Week 28 / WP1: build the unified scientific evidence master table.")
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
            on_disk = path.read_text(encoding="utf-8")
            if on_disk != text:
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
    print("Week 28 / WP1 -- unified scientific evidence master table")
    print("-" * 74)
    for table in TABLE_ORDER:
        info = payload["manifest"][table]
        print("  %-20s %5d rows  %s" % (table, info["n_rows"], info["sha256"][:12]))
    print("  %-20s %5d rows total" % ("(all tables)", payload["n_rows_total"]))
    print("-" * 74)
    for cid in ("provenance_completeness", "same_target_quantity", "p1v_vs_p1a_distinct",
                "li_centered_not_misused_as_molecular", "status_vocabulary_separated",
                "frozen_number_reproduction"):
        check = checks[cid]
        print("  %-42s %s" % (cid, "PASS" if check["ok"] else "FAIL"))
    repro = checks["frozen_number_reproduction"]["evidence"]
    pair_items = [item for item in repro if "max_abs_error_ev" in item]
    print("  reproduction max |error| = %.3e eV over %d stored pairs (%d metrics groups)"
          % (max((item["max_abs_error_ev"] for item in pair_items), default=0.0),
             sum(item["n_pairs_compared"] for item in pair_items),
             len(repro) - len(pair_items)))
    print("-" * 74)
    print("wrote outputs/week28/ (%d files)" % len(texts))
    return 0


if __name__ == "__main__":
    sys.exit(main())
