# -*- coding: utf-8 -*-
"""physics_completion_v1 批次共享工具。

本模块服务于**新阶段**（评审实施方案 WP0-WP6）的确定性产物生成：装载仓库既有冻结输入、
登记新批次的量名/方向/状态身份语义、并以固定编码（UTF-8 / LF）写出产物。

设计纪律（与仓库既有约定一致）：
  * 方向语义只在 OBJECTIVE_DIRECTION 里定义一次，任何排序/判据代码都从这里取；
  * 缺值/不合格态一律表示为 None，绝不被替换成 0；
  * 旧别名只作**映射**存在，不会被静默当成新量名使用。
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

BATCH_ID = "physics_completion_v1"
BASELINE_COMMIT = "d5217a1f1f7e85c3e117b29d734efc2a8e535ecd"
FROZEN_DATE = "2026-10-09"

# ---------------------------------------------------------------------------
# 新批次量名登记表（WP0）
# 每一个量都必须同时给出：定义、单位、方向、量类、几何/热/系综政策、介质、
# 状态身份资格与所属分析 cohort。--check 会逐条复核这些字段。
# ---------------------------------------------------------------------------
QUANTITIES = [
    {
        "name": "Eox_vertical",
        "definition": "E(M+) - E(M) on the same initial geometry",
        "unit": "eV",
        "quantity_kind": "electronic_energy_difference",
        "objective_direction": "maximize",
        "geometry_policy": "single shared geometry (vertical)",
        "thermal_policy": "none",
        "ensemble_policy": "none",
        "solvent": "gas_phase",
        "state_identity_eligibility": "any",
        "analysis_cohort": "cheap_reference",
        "role": "cheap / vertical reference",
    },
    {
        "name": "Eox_adiabatic",
        "definition": "electronic-energy difference between the two relaxed states",
        "unit": "eV",
        "quantity_kind": "electronic_energy_difference",
        "objective_direction": "maximize",
        "geometry_policy": "each charge state relaxed independently",
        "thermal_policy": "none",
        "ensemble_policy": "single lowest structure per state",
        "solvent": "gas_phase",
        "state_identity_eligibility": "any",
        "analysis_cohort": "relaxation_effect",
        "role": "relaxation effect",
    },
    {
        "name": "Gox_single",
        "definition": "free-energy difference from one representative minimum per state",
        "unit": "eV",
        "quantity_kind": "gibbs_free_energy_difference",
        "objective_direction": "maximize",
        "geometry_policy": "each charge state relaxed independently",
        "thermal_policy": "qRRHO thermal correction on solution frequencies",
        "ensemble_policy": "single lowest structure per state",
        "solvent": "SMD_acetonitrile",
        "state_identity_eligibility": "any",
        "analysis_cohort": "thermochemical_correction",
        "role": "thermal correction check",
    },
    {
        "name": "Gox_ensemble",
        "definition": "conformer-ensemble free-energy difference, -RT ln sum g_i exp(-G_i/RT)",
        "unit": "eV",
        "quantity_kind": "gibbs_free_energy_difference",
        "objective_direction": "maximize",
        "geometry_policy": "each charge state relaxed independently",
        "thermal_policy": "qRRHO thermal correction on solution frequencies",
        "ensemble_policy": "conformer ensemble within a frozen energy window",
        "solvent": "SMD_acetonitrile",
        "state_identity_eligibility": "any",
        "analysis_cohort": "main_target",
        "role": "main target",
    },
    {
        "name": "Gox_Li_ensemble",
        "definition": "G([LiM]2+) - G([LiM]+) using per-state ensembles",
        "unit": "eV",
        "quantity_kind": "gibbs_free_energy_difference",
        "objective_direction": "maximize",
        "geometry_policy": "each charge state relaxed independently",
        "thermal_policy": "qRRHO thermal correction on solution frequencies",
        "ensemble_policy": "conformer/motif ensemble within a frozen energy window",
        "solvent": "SMD_acetonitrile",
        "state_identity_eligibility": "molecule_centered_oxidation",
        "analysis_cohort": "conditional_coordination_target",
        "role": "conditional Li-coordination target",
    },
    {
        "name": "coordination_shift",
        "definition": "Gox_Li_ensemble - Gox_free_ensemble",
        "unit": "eV",
        "quantity_kind": "conditional_shift",
        "objective_direction": "maximize",
        "geometry_policy": "difference of two independently relaxed conditional species",
        "thermal_policy": "inherits both legs",
        "ensemble_policy": "inherits both legs",
        "solvent": "SMD_acetonitrile",
        "state_identity_eligibility": "molecule_centered_oxidation",
        "analysis_cohort": "conditional_coordination_target",
        "role": "environment response",
    },
    {
        "name": "Sred",
        "definition": "G(reduced) - G(parent) = -EA (unified reduction-resistance score)",
        "unit": "eV",
        "quantity_kind": "gibbs_free_energy_difference",
        "objective_direction": "maximize",
        "geometry_policy": "each charge state relaxed independently",
        "thermal_policy": "qRRHO thermal correction on solution frequencies",
        "ensemble_policy": "conformer ensemble within a frozen energy window",
        "solvent": "SMD_acetonitrile",
        "state_identity_eligibility": "molecule_centered_redox",
        "analysis_cohort": "conditional_reduction_secondary",
        "role": "conditional secondary axis",
    },
]

#: 旧别名 -> 新量名。只用于追溯，不允许被当作新量名直接使用。
LEGACY_ALIASES = {
    "P1": "P1v",
    "P2": "P2a",
    "EA_raw": "raw electron affinity (stored separately; minimize)",
    "reduction_resistance_score": "Sred",
}

#: 原始 EA 的方向与统一 score 的方向。二者必须选出同一集合。
OBJECTIVE_DIRECTION = {
    "EA": "minimize",
    "Sred": "maximize",
}

#: 新批次固定的三个 cohort（分子 id 按 core set 命名）。
COHORTS = {
    "main": ["C01", "C02", "C03", "C04", "C05", "C08", "C09", "C13", "C14", "C15", "C16", "C17"],
    "method_audit": ["C01", "C02", "C04", "C08", "C13", "C14", "C16", "C17"],
    "sampling_audit": ["C02", "C03", "C08", "C17"],
}

COHORT_NAMES = {
    "C01": "DMC", "C02": "EMC", "C03": "DEC", "C04": "EC", "C05": "PC",
    "C08": "DME", "C09": "DOL", "C13": "GBL", "C14": "SL", "C15": "DMSO",
    "C16": "AN", "C17": "TMP",
}

#: 每个分子的四个主状态（WP2）。
FOUR_STATES = ["M", "M_plus", "LiM_plus", "LiM_2plus"]

#: 每个分子只对 C1 代表 motif 的 [LiM]+ / [LiM]2+ 做配位态。
LI_STATES = ["LiM_plus", "LiM_2plus"]

#: 未进入主配对集的 core-set 分子与原因（方案 3.1 / 15.3 的「排除原因规则」）。
MAIN_SET_EXCLUSIONS = {
    "C06": "fluorinated additive FEC - reserved for later expansion (plan 3.1)",
    "C07": "unsaturated additive VC - reserved for later expansion (plan 3.1)",
    "C10": "long flexible TEGDME - avoided in round 1 to protect the compute budget",
    "C11": "ester EA - ester family already represented by GBL; reserved for later expansion",
    "C12": "simplest ester MA - same family-redundancy control as EA",
    "C18": "dinitrile SN - reserved for later expansion (plan 3.1)",
}

#: method_audit 只含 8 个；其余主集分子留作冻结方法后的检验对象。
METHOD_AUDIT_HOLDOUTS = {
    "C03": "held out as a post-freeze check; must not be used to select the method",
    "C05": "held out as a post-freeze check; must not be used to select the method",
    "C09": "held out as a post-freeze check; must not be used to select the method",
    "C15": "held out as a post-freeze check; must not be used to select the method",
}

#: WP5 冻结的模型族（方案 9.1：主模型只用岭回归/核岭与 GPR 两类）。
#: 既有 stage7 复算表还含 gbdt/rf/constant；任何进入新批次主结论的选型都必须先
#: 限制在本族内，越族的既有最优只作旁证并显式标记。
FROZEN_MODEL_FAMILY = ["ridge", "krr", "gpr"]

#: WP5 冻结族复算的冻结输入（零新增电子结构计算）。
FROZEN_OOF_METRICS = "outputs/week32/oof_metrics_reconciliation.csv"

#: WP3 机制案例的原始结构来源（均为既有冻结产物，本批次不新算）。
MECHANISM_NEUTRAL_GEOMETRY = "outputs/week4/t2_opt_freq/{name}/{name}_G2.xyz"
MECHANISM_CATION_GEOMETRY = "outputs/phase2_p1a/geometry_relaxation/{name}/{name}_cation_opt.xyz"
MECHANISM_ADIABATIC_TABLE = "outputs/phase2_p1a/p1a_adiabatic.csv"
#: 只用于枚举重原子成键对的几何截断（Angstrom）；不是力常数判据。
GEOMETRY_BOND_CUTOFF_ANG = 1.8


def load_json(path):
    with io.open(path, encoding="utf-8") as handle:
        return json.load(handle)


def load_rows(path):
    with io.open(path, encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_text(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with io.open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def write_json(path, obj):
    write_text(path, json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=False) + "\n")


def write_csv(path, fieldnames, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with io.open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def sha256_file(path):
    digest = hashlib.sha256()
    with io.open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def direction_selection(candidates, direction):
    """给定 candidate -> score 与方向，返回最优 candidate（数值比较一律 float()）。

    找不到有限 score 时返回 None；**不会**把缺值当成 0 参与比较。
    """
    usable = {}
    for name, value in candidates.items():
        if value is None or value == "":
            continue
        try:
            number = float(value)
        except (TypeError, ValueError):
            continue
        usable[name] = number
    if not usable:
        return None
    if direction == "maximize":
        return max(usable, key=lambda key: usable[key])
    if direction == "minimize":
        return min(usable, key=lambda key: usable[key])
    raise ValueError("unknown objective direction: %r" % direction)


def quantity_by_name(name):
    for item in QUANTITIES:
        if item["name"] == name:
            return item
    return None
