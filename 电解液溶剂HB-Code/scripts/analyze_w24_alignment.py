#!/usr/bin/env python
"""Week 24 -- align the core-file promises with what the project actually delivered.

Reads the core study design (v2 sections 11/22/23/25 + the Part II reading list), the
frozen week2/3/4/5/7/8/9 artefacts, the week22-hardening bootstrap record and the paper
builder, and writes ONE alignment package:

    outputs/week24_corealign/core_alignment.md     four Chinese three-line tables and
                                                   two statements, ready to paste into
                                                   the paper
    outputs/week24_corealign/core_alignment.json   the same content, structured

It is READ-ONLY on every input.  No new electronic-structure calculation is run.

Run it a second time with ``--check`` to prove the two artefacts on disk are
byte-for-byte what a fresh run would produce.
"""

from __future__ import annotations

import argparse
import csv as _csv
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CORE_DIR = REPO_ROOT.parent / "核心文件"
PAPER_DIR = REPO_ROOT.parent / "论文"

DEFAULT_OUTDIR = REPO_ROOT / "outputs" / "week24_corealign"

CORE_V2 = CORE_DIR / "ranking-electrolyte-materials-v2.md"
CORE_READING_LIST = CORE_DIR / "ranking-electrolyte-materials-reading-list.md"
PAPER_BUILDER = PAPER_DIR / "build_paper_docx.py"

STAGE10_LADDER = REPO_ROOT / "outputs" / "week9" / "stage10_ladder.json"
C1_STATE_IDENTITY = REPO_ROOT / "outputs" / "week5" / "c1_state_identity.json"
STAGE7_RESULTS_JSON = REPO_ROOT / "outputs" / "week7" / "stage7_ml_results.json"
STAGE7_RESULTS_CSV = REPO_ROOT / "outputs" / "week7" / "stage7_ml_results.csv"
FEATURE_MANIFEST = REPO_ROOT / "outputs" / "week7" / "feature_manifest.json"
STAGE8_AL = REPO_ROOT / "outputs" / "week7" / "stage8_al_results.json"
STAGE8_AL_CURVES = REPO_ROOT / "outputs" / "week7" / "stage8_al_curves.csv"
P2_DECISION_STABILITY = REPO_ROOT / "outputs" / "week4" / "p2_decision_stability.json"
P2_SMD_CSV = REPO_ROOT / "outputs" / "week4" / "p2_core_set_smd_acetonitrile.csv"
SMD_SUMMARY = REPO_ROOT / "outputs" / "week4" / "p2_summary_smd_acetonitrile.json"
SOLUTION_ANCHOR_AUDIT = REPO_ROOT / "outputs" / "week2" / "solution_anchor_audit.json"
GAS_ANCHORS = REPO_ROOT / "data" / "anchors" / "gas_phase_anchors.csv"
SOLUTION_ANCHORS = REPO_ROOT / "data" / "anchors" / "solution_redox_anchors.csv"
CORE_SET_CSV = REPO_ROOT / "data" / "metadata" / "core_set.csv"
P0_BROAD_POOL_CSV = REPO_ROOT / "outputs" / "week3" / "p0_broad_pool.csv"
SCIENTIFIC_DEFINITIONS = REPO_ROOT / "config" / "scientific_definitions.yaml"
STAGE9_RESULTS = REPO_ROOT / "outputs" / "week8" / "stage9_results.json"
STAGE9_SHELL_SHIFTS = REPO_ROOT / "outputs" / "week8" / "stage9_shell_shifts.csv"
WEEK23_XTB = REPO_ROOT / "outputs" / "week23" / "shell3_xtb_sign_test.json"
HARDENING_STATS = REPO_ROOT / "outputs" / "week22_hardening" / "stats_b1_b2.json"
STAGE7_ML_SCRIPT = REPO_ROOT / "scripts" / "run_stage7_ml.py"
STAGE8_AL_SCRIPT = REPO_ROOT / "scripts" / "run_stage8_al.py"
BUILD_CONFORMERS_SCRIPT = REPO_ROOT / "scripts" / "build_conformers.py"

PAPER_SECTIONS = {
    "2.1": "分子集与化学空间",
    "2.2": "三层电子结构臂与唯一变量台阶设计",
    "2.3": "电子结构计算细节",
    "2.4": "决策量定义",
    "2.5": "不确定度预算与 σ 的闭式",
    "2.6": "预注册与可审计性",
    "3.1": "值误差与排序误差的解耦",
    "3.5": "条件态台阶：Li+ 配位如何改写排序",
    "3.6": "位移离散度判据与 σ 的闭式",
    "3.9": "配位饱和的证据",
    "3.11": "最小信息预算",
    "3.12": "broad pool 的实际演示：最小信息预算省下多少",
}

PATH_RE = re.compile(r"([A-Za-z0-9_][A-Za-z0-9_./-]*\.(?:csv|json|yaml|yml|md|txt|py|ps1|sh))")


def relpath(path):
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def exists(rel):
    return (REPO_ROOT / rel).exists()


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def count_chars(text):
    return len(re.sub(r"\s", "", text))
# ---------------------------------------------------------------------------
# Table 1 -- v2 section 22 branch claim table (A-G)
# ---------------------------------------------------------------------------
def build_branch_table():
    verdicts = read_json(STAGE10_LADDER)["verdicts"]

    # curated one-line summaries of the verdicts field; the verbatim text is kept
    # in evidence_full so nothing is lost or re-invented.
    curated = {
        "A_cheap_proxy_already_stable": (
            "P0→P2 氧化轴 τ_b=0.673、Top-10% 重叠 0.000、f_unresolved=0.229"
        ),
        "B_large_shift_small_rank_damage": (
            "P1→P2 氧化轴位移均值 −2.393 eV、位移 std 0.302 eV、τ_b=0.895、"
            "O_20%=0.750、f_robust_inv=0.000"
        ),
        "C_structured_robust_inversion": (
            "五台阶 × 两轴 × 两口径共 20 个 (台阶, 轴) 组合中 f_robust_inv 全为 0.000；"
            "z=1.96 敏感性列同样全为 0.000"
        ),
        "D_coordination_state_identity_change": (
            "还原态 12 个中 11 个 Li_centered_or_mixed_redox、1 个 molecule_centered；"
            "氧化态 12 个中 molecule_centered=8、no_intact_minimum=4"
            "（阈值 |Li 自旋|≥0.5 或 |Δq(Li)|≥0.5 e）"
        ),
        "E_delta_learning_beats_direct": (
            "LOFO 下 Δ-learning 在 6/8 分组不劣于 direct：C/oxidation/X0 τ_b 0.111→0.644 "
            "(+0.533)、C/oxidation/X0+X1 0.244→0.644 (+0.400)；例外 C/reduction/X0 "
            "0.422→0.022 (−0.400)、C/reduction/X0+X1 0.289→0.200 (−0.089)"
        ),
        "F_delta_not_learnable_from_cheap": (
            "Δ 在 6/8 分组上可从廉价特征学出（与 E 同源）；真正学不动的仅 C0→C1 还原轴"
        ),
        "G_most_pairs_unresolved": (
            "C0→C1 还原轴 τ_b=−0.467、f_unresolved(after)=0.800、O_10%=0.000；"
            "同级氧化轴对照 τ_b=0.689、f_unresolved(after)=0.200；"
            "P0→P1 还原轴 f_unresolved(after)=0.733"
        ),
    }

    order = [
        ("A", "A_cheap_proxy_already_stable",
         "outputs/week4/p2_decision_stability.json, outputs/week9/stage10_ladder.json"),
        ("B", "B_large_shift_small_rank_damage",
         "outputs/week4/p2_decision_stability.json, outputs/week9/stage10_ladder.json"),
        ("C", "C_structured_robust_inversion",
         "outputs/week9/stage10_ladder.json"),
        ("D", "D_coordination_state_identity_change",
         "outputs/week5/c1_state_identity.json, outputs/week9/stage10_ladder.json"),
        ("E", "E_delta_learning_beats_direct",
         "outputs/week7/stage7_ml_results.json, outputs/week9/stage10_ladder.json"),
        ("F", "F_delta_not_learnable_from_cheap",
         "outputs/week7/stage7_ml_results.json, outputs/week9/stage10_ladder.json"),
        ("G", "G_most_pairs_unresolved",
         "outputs/week9/stage10_ladder.json"),
    ]

    rows = []
    for letter, key, files in order:
        verdict = verdicts[key]
        short = verdict["short"]
        if short.startswith(letter + "："):
            short = short[len(letter) + 1:]
        rows.append({
            "letter": letter,
            "branch": "%s（%s）" % (letter, short),
            "definition": verdict["definition"],
            "verdict": verdict["verdict"],
            "evidence": curated[key],
            "evidence_files": files,
            "evidence_full": verdict["evidence"],
            "reading": verdict["reading"],
        })

    return {
        "title": "§22 分支认领表（情形 A–G）",
        "columns": ["分支（A–G）", "判据定义", "本项目判决",
                    "关键证据（带数值）", "证据文件路径"],
        "rows": rows,
        "note": ("判决与证据均取自 outputs/week9/stage10_ladder.json 的 verdicts 字段，"
                 "只做如实转述，未新增任何数值。"),
    }

# ---------------------------------------------------------------------------
# Table 2 -- v2 section 23 minimum-outcome checklist (11 items)
# ---------------------------------------------------------------------------
CHECKLIST_PAPER_SECTION = {
    "1": "2.1 分子集与化学空间",
    "2": "2.1 分子集与化学空间（另见 3.12）",
    "3": "2.2 三层电子结构臂与唯一变量台阶设计 / 2.4 决策量定义",
    "4": "3.5 条件态台阶：Li+ 配位如何改写排序",
    "5": "2.3 电子结构计算细节（气相锚点）；溶液锚点 Gate 1 未关，待补外部锚点/局限声明",
    "6": "2.4 决策量定义 / 3.1 值误差与排序误差的解耦 / 3.6 位移离散度判据",
    "7": "3.5 条件态台阶 / 3.6 位移离散度判据（negative 结果）",
    "8": "待补（论文缺 ML 章：random/group/LOFO 拆分）",
    "9": "待补（论文缺 ML 章：direct vs Δ-learning）",
    "10": "待补（论文缺 ML / 主动学习章：feature-cost-aware active-learning replay）",
    "11": "3.11 最小信息预算 / 3.12 broad pool 的实际演示",
}

# concrete artefacts each checklist item actually resolves to (verified on disk)
CHECKLIST_ARTIFACTS = {
    "1": ["data/metadata/core_set.csv"],
    "2": ["outputs/week3/p0_broad_pool.csv"],
    "3": ["config/scientific_definitions.yaml"],
    "4": ["outputs/week5/c1_state_identity.json", "outputs/week5/c1_coord_shifts.csv"],
    "5": ["data/anchors/gas_phase_anchors.csv", "data/anchors/solution_redox_anchors.csv",
          "outputs/week2/solution_anchor_audit.json"],
    "6": ["outputs/week4/p2_decision_stability.json", "outputs/week9/stage10_ladder.json"],
    "7": ["outputs/week9/stage10_ladder.json"],
    "8": ["outputs/week7/stage7_ml_results.json"],
    "9": ["outputs/week7/stage7_ml_results.json"],
    "10": ["outputs/week7/stage8_al_results.json"],
    "11": ["outputs/week7/stage8_al_curves.csv"],
}


def build_checklist_table():
    checklist = read_json(STAGE10_LADDER)["minimum_outcome_checklist"]

    rows = []
    for item in checklist:
        cid = str(item["id"])
        cited = [{"path": c, "exists": exists(c)} for c in PATH_RE.findall(item["evidence"])]
        artifacts = [{"path": a, "exists": exists(a)}
                     for a in CHECKLIST_ARTIFACTS.get(cid, [])]
        note = ""
        missing = [c["path"] for c in cited if not c["exists"]]
        if missing:
            note = "evidence 引用路径不存在：" + "、".join(missing) + "，已改列实际产物"
        if not cited:
            note = (note + "；" if note else "") + "evidence 未给出文件路径，已补列实际产物"
        artifacts_ok = all(a["exists"] for a in artifacts)
        rows.append({
            "id": cid,
            "item": item["item"],
            "status": item["status"],
            "evidence": item["evidence"],
            "cited_evidence_paths": cited,
            "resolved_artifacts": artifacts,
            "artifact_check": "OK" if (artifacts_ok and not missing) else "CHECK",
            "paper_section": CHECKLIST_PAPER_SECTION[cid],
            "note": note,
        })

    partial = [r["id"] for r in rows if r["status"].strip().upper() == "PARTIAL"]
    return {
        "title": "§23 最小成果判据自查表（11 条）",
        "columns": ["id", "条目", "status", "evidence（原文）", "证据文件校验", "论文中的落点"],
        "rows": rows,
        "note": ("status / item / evidence 取自 outputs/week9/stage10_ladder.json 的 "
                 "minimum_outcome_checklist，未改动；PARTIAL 条目按原文如实保留。"),
        "partial_ids": partial,
    }

# ---------------------------------------------------------------------------
# Table 3 -- v2 section 11 feature-cost accounting (X0/X1/X2)
# ---------------------------------------------------------------------------
def build_feature_cost_table():
    manifest = read_json(FEATURE_MANIFEST)
    levels = manifest["feature_cost_levels"]
    x2_policy = manifest["x2_policy"]

    with STAGE7_RESULTS_CSV.open(encoding="utf-8", newline="") as handle:
        level_values = []
        for row in _csv.DictReader(handle):
            if row["feature_cost_level"] not in level_values:
                level_values.append(row["feature_cost_level"])

    rows = [
        {
            "tier": "X0（cheap，query 前可得）",
            "features": "、".join(levels["X0"]) + "（共 %d 个）" % len(levels["X0"]),
            "availability": "query 前：分子式/结构描述符 + GFN2-xTB 单点即可，无需任何 DFT",
            "allowed_use": ("可作为任何预测器与 acquisition 的输入；active-learning "
                            "acquisition 只允许用 X0；可支撑「低成本预测」的主张"),
        },
        {
            "tier": "X1（free-molecule DFT 已知后可得）",
            "features": "、".join(levels["X1"]) + "（共 %d 个）" % len(levels["X1"]),
            "availability": "free-molecule DFT（P1）或 P2 环境势已知之后",
            "allowed_use": ("可用来预测昂贵的 C1 Li-配位响应，因为这些量在做新的 C1 "
                            "计算前已经可得；但不得据此宣称「无需 C1 就能得到 C1 结果」"),
        },
        {
            "tier": "X2（需 Li-complex DFT 后才能获得）",
            "features": "、".join(levels["X2"]) + "（共 %d 个）" % len(levels["X2"]),
            "availability": "必须做完 Li-complex（C1）DFT 之后",
            "allowed_use": ("仅机制解释（mechanism-only）；绝不进特征集，"
                            "不能用于证明「低成本预测 C1」"),
        },
    ]

    note = ("x2_policy 原文：" + x2_policy
            + " ｜ 所有 ML 表格均带 feature_cost_level 列："
            "outputs/week7/stage7_ml_results.csv 的表头含该列，实际取值为 "
            + " / ".join(level_values) + "（不含 X2）。")
    return {
        "title": "§11 feature-cost accounting（X0 / X1 / X2）",
        "columns": ["成本档", "特征清单", "何时可得", "允许用途（可否用于证明「低成本预测」）"],
        "rows": rows,
        "note": note,
        "feature_cost_level_values": level_values,
        "x2_policy": x2_policy,
    }

# ---------------------------------------------------------------------------
# Table 4 -- v2 section 25 innovation boundary + RL Part II mapping
# ---------------------------------------------------------------------------
RL_ROWS = [
    {
        "entry": "A1 SMD",
        "source": "Marenich, Cramer & Truhlar 2009，DOI 10.1021/jp810292n（阅读清单 Part II §A1）",
        "used_where": ("已使用：P2 环境臂 = ORCA 6.1.1 r2SCAN-3c 的 CPCM(SMD, 乙腈 ε=35.688)，"
                       "54/54 作业成功（outputs/week4/p2_summary_smd_acetonitrile.json）"),
        "cite_at": "论文 2.3 电子结构计算细节；3.3 环境台阶（P1→P2）",
        "direct_evidence": True,
        "evidence_files": ["outputs/week4/p2_core_set_smd_acetonitrile.csv",
                           "outputs/week4/p2_summary_smd_acetonitrile.json"],
    },
    {
        "entry": "A2 association entropy",
        "source": "Rebollar-Zepeda et al., JCTC 2026，DOI 10.1021/acs.jctc.6c00575（阅读清单 Part II §A2）",
        "used_where": ("未直接使用，仅方法学背景：项目识别了 Li+ + M → [LiM]+ 的平动熵 artifact"
                       "（config/scientific_definitions.yaml 的 molecularity_warning），并以配体交换"
                       "相对量 dGdG_bind 规避；未显式建模 condensed-phase association entropy"),
        "cite_at": "论文 2.3 / 2.4 的方法学说明与局限",
        "direct_evidence": False,
        "evidence_files": ["config/scientific_definitions.yaml"],
    },
    {
        "entry": "A3 qRRHO",
        "source": "Grimme 2012，DOI 10.1002/chem.201200497（阅读清单 Part II §A3）",
        "used_where": ("未直接使用，仅方法学背景：热修正抽样用的是 xtb --ohess 的谐近似 RRHO 项 "
                       "G(RRHO)（scripts/run_thermal_correction_sample.py），未使用 quasi-RRHO 熵插值"),
        "cite_at": "论文 2.5 不确定度预算（热修正抽样）",
        "direct_evidence": False,
        "evidence_files": ["scripts/run_thermal_correction_sample.py"],
    },
    {
        "entry": "B1 GFN2-xTB",
        "source": "Bannwarth, Ehlert & Grimme 2019，DOI 10.1021/acs.jctc.8b01176（阅读清单 Part II §B1）",
        "used_where": ("已使用：P0 Koopmans 层（xtb 6.7.1pre）、G1 几何、构象系综弛豫，"
                       "以及 week23 第三配位壳符号检验（engine=GFN2-xTB，14 作业）"),
        "cite_at": "论文 2.2 / 2.3 / 3.9",
        "direct_evidence": True,
        "evidence_files": ["outputs/week23/shell3_xtb_sign_test.json",
                           "outputs/week3/p0_broad_pool.csv"],
    },
    {
        "entry": "B2 CREST",
        "source": "CREST, JCP 2024，DOI 10.1063/5.0197592（阅读清单 Part II §B2）",
        "used_where": ("未直接使用，仅方法学背景：仓库内无 CREST 运行产物（无 crest.exe、无 "
                       "crest_conformers.xyz）；构象系综实际由 RDKit ETKDGv3 + MMFF + GFN2-xTB 弛豫构建"
                       "（scripts/build_conformers.py）。注：论文 2.3 现写有「低能构象空间搜索使用 "
                       "CREST[7]」，与实际实现不一致"),
        "cite_at": "论文 2.3（需与 build_conformers.py 实际做法核对/修正）",
        "direct_evidence": False,
        "evidence_files": ["scripts/build_conformers.py", "config/scientific_definitions.yaml"],
    },    {
        "entry": "C1 electrolyte speciation",
        "source": "Chem. Rev. 2022，DOI 10.1021/acs.chemrev.1c00904（阅读清单 Part II §C1，真实 speciation / MD）",
        "used_where": ("未直接使用，仅方法学背景：项目停留在单一 [LiM]+ conditional state"
                       "（week5 T4，12 motif / 8 家族），未做 p(C) 配位环境分布或 MD speciation"),
        "cite_at": "论文 3.5 的局限声明 / 4 展望（Phase II 真实配位 population）",
        "direct_evidence": False,
        "evidence_files": ["outputs/week5/c1_state_identity.json"],
    },
    {
        "entry": "C2 solvation structure",
        "source": "ACS Energy Lett. 2022，DOI 10.1021/acsenergylett.1c02425（阅读清单 Part II §C2）",
        "used_where": ("间接使用：C1→C2 显式微溶剂化 [Li(M)2]+ 簇（week8 Stage 9，10 分子），"
                       "week23 追加 EC 第三配位壳符号检验；对应第一溶剂化壳，"
                       "但未涉及 Li–溶剂–阴离子竞争或界面结构"),
        "cite_at": "论文 3.5 / 3.9 配位饱和的证据",
        "direct_evidence": "partial",
        "evidence_files": ["outputs/week8/stage9_results.json",
                           "outputs/week8/stage9_shell_shifts.csv"],
    },
    {
        "entry": "D1 Gaussian Process",
        "source": "Rasmussen & Williams, Gaussian Processes for Machine Learning（阅读清单 Part II §D1）",
        "used_where": ("已使用：Stage 7 模型阶梯含 sklearn GaussianProcessRegressor"
                       "（scripts/run_stage7_ml.py），与 Stage 8 acquisition 同源"),
        "cite_at": "论文待补 ML 章",
        "direct_evidence": True,
        "evidence_files": ["scripts/run_stage7_ml.py", "outputs/week7/stage7_ml_results.json"],
    },
    {
        "entry": "D2 Active learning",
        "source": "Settles 2009, Active Learning Literature Survey（阅读清单 Part II §D2）",
        "used_where": ("已使用：Stage 8 retrospective active-learning replay，4 种 acquisition"
                       "（random / diversity / uncertainty / ranking-aware，ranking-aware 用二元熵），"
                       "acquisition 只用 X0（outputs/week7/stage8_al_results.json）"),
        "cite_at": "论文待补 ML / 主动学习章",
        "direct_evidence": True,
        "evidence_files": ["scripts/run_stage8_al.py", "outputs/week7/stage8_al_results.json"],
    },
    {
        "entry": "D3 Multi-fidelity",
        "source": "Peherstorfer, Willcox & Gunzburger 2018，DOI 10.1137/16M1082469（阅读清单 Part II §D3）",
        "used_where": ("未直接使用，仅方法学背景：仓库无 multi-fidelity 实现；Δ-learning 的 "
                       "P_H = P_L + Δ 形式相同，但按阅读清单定义 P(M) → P([LiM]+) 属 environment "
                       "perturbation，不是数值 fidelity 校正"),
        "cite_at": "论文待补 ML 章的方法学说明（与 2.2 条件态定义呼应）",
        "direct_evidence": False,
        "evidence_files": ["outputs/week7/stage7_ml_results.json"],
    },
    {
        "entry": "E Efron & Tibshirani (bootstrap)",
        "source": "Efron & Tibshirani, An Introduction to the Bootstrap（阅读清单 Part II §E）",
        "used_where": ("已使用：Week 22 hardening 对 ladder 的 10 个 (台阶, 轴) 点做 bootstrap"
                       "（percentile 主口径 + BCa 并列，n_boot=20000，固定种子）"
                       "（outputs/week22_hardening/stats_b1_b2.json）"),
        "cite_at": "论文 2.5 / 3.6（τ_b 的 bootstrap 置信区间）",
        "direct_evidence": True,
        "evidence_files": ["outputs/week22_hardening/stats_b1_b2.json"],
    },
]


STATUS_PREFIXES = ("已使用：", "间接使用：", "未直接使用，仅方法学背景：")


def build_rl_mapping_table():
    rows = []
    for row in RL_ROWS:
        if row["direct_evidence"] is True:
            marker = "✅ 已使用"
        elif row["direct_evidence"] == "partial":
            marker = "◐ 间接使用"
        else:
            marker = "○ 未直接使用，仅方法学背景"
        body = row["used_where"]
        for prefix in STATUS_PREFIXES:
            if body.startswith(prefix):
                body = body[len(prefix):]
                break
        rows.append({
            "entry": row["entry"],
            "source": row["source"],
            "used_where": body,
            "cite_at": row["cite_at"],
            "direct_evidence": row["direct_evidence"],
            "marker": marker,
            "evidence_files": [{"path": p, "exists": exists(p)} for p in row["evidence_files"]],
        })

    no_direct = [r["entry"] for r in rows if r["direct_evidence"] is False]
    return {
        "title": "§25.1/§25.2 RL Part II 方法依据映射",
        "columns": ["RL Part II 条目", "出处", "本项目在哪个环节用到", "建议引用位置"],
        "rows": rows,
        "note": ("marker：✅ 已使用 / ◐ 间接使用 / ○ 未直接使用，仅方法学背景。"
                 "找不到真实使用证据的条目已如实标注，未硬凑。"),
        "without_direct_evidence": no_direct,
    }

# ---------------------------------------------------------------------------
# statements
# ---------------------------------------------------------------------------
BRANCH_SUMMARY = (
    "本项目最终落在 B、D、E 三个分支（并以 G 的还原轴部分触发）：B——P1→P2 位移大而排序稳"
    "（τ_b=0.895、f_robust_inv=0.000），环境主要贡献 common/family-level offset；"
    "D——Li+ 配位改写态身份（还原态 11/12 为 Li 中心或混合还原）；"
    "E——Δ-learning 在 6/8 分组上不劣于 direct。A、C、F 均被如实否定：A 廉价 proxy 不能替代目标层"
    "（P0→P2 τ_b=0.673、Top-10% 重叠 0.000）；C 的 robust inversion 从未出现"
    "（20 个台阶-轴组合 f_robust_inv 全为 0.000，且必须与 G 的 f_unresolved 同读，"
    "不等于排序处处可靠）；F 的「Δ 不可学」不成立。真正 unresolved 的只有还原轴的 C0→C1"
    "（τ_b=−0.467、f_unresolved=0.800），即 G。"
)

INNOVATION_BOUNDARY = (
    "本项目不以「ranking/selection 本身」为创新（Husch et al. 2015），也不以「Li+ 配位改变 redox」"
    "为创新（Yang et al. 2025 已用 ML）。增量有三：①决策可靠性——τ_b 与 f_unresolved/f_robust_inv "
    "并列，区分两类误差；②稳健翻转须超出方法不确定度——全部台阶 f_robust_inv=0；"
    "③最小信息预算——复现目标排序所需的昂贵信息量。"
)


# ---------------------------------------------------------------------------
# data flags (honest cross-checks between the core-file claims and the artefacts)
# ---------------------------------------------------------------------------
def build_data_flags():
    flags = []

    src_std = read_json(P2_DECISION_STABILITY)["delta_ip"]["std_ev"]
    flags.append({
        "id": "B_shift_std",
        "text": ("§22 情形 B 的 verdict 文字记「位移 std 0.302 eV」，而 "
                 "outputs/week4/p2_decision_stability.json 的 delta_ip.std_ev = %.6f eV；"
                 "两者口径/舍入不一致，本表按 verdicts 原文转述 0.302，建议主代理复核。" % src_std),
    })

    flags.append({
        "id": "checklist_item2_path",
        "text": ("§23 第 2 条 evidence 引用 `outputs/week3/p0_pool.csv`，该路径不存在；"
                 "实际产物为 `outputs/week3/p0_broad_pool.csv`（40 行，另有 p0_core_set.csv "
                 "18 行），两者合计 58。需要修正 evidence 路径。"),
        "missing": "outputs/week3/p0_pool.csv",
        "actual": ["outputs/week3/p0_broad_pool.csv", "outputs/week3/p0_core_set.csv"],
    })

    flags.append({
        "id": "crest_no_artifacts",
        "text": ("论文 build_paper_docx.py 的 2.3 节写有「低能构象空间搜索使用 CREST[7]」，"
                 "但仓库内没有任何 CREST 运行产物（无 crest.exe、无 crest_conformers.xyz、"
                 "无 crest 输出目录）；scripts/build_conformers.py 明确用 RDKit ETKDGv3 + MMFF + "
                 "GFN2-xTB 弛豫构建构象系综。RL Part II 的 B2（CREST）因此记「未直接使用」。"),
    })

    return flags


# ---------------------------------------------------------------------------
# rendering
# ---------------------------------------------------------------------------
def md_table(headers, rows):
    def cell(value):
        return str(value).replace("|", "\\|").replace("\n", " ")

    out = ["| " + " | ".join(cell(h) for h in headers) + " |",
           "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        out.append("| " + " | ".join(cell(c) for c in row) + " |")
    return "\n".join(out)

def render_markdown(payload):
    lines = []
    lines.append("# 核心文件承诺 vs 项目已交付：Week 24 对齐")
    lines.append("")
    lines.append("本文件把核心文件（`ranking-electrolyte-materials-v2.md` §11 / §22 / §23 / §25 "
                 "与 `ranking-electrolyte-materials-reading-list.md` Part II）的承诺，逐条对齐到项目"
                 "已冻结的产物。只读输入、零新增电子结构计算；数值一律如实转述，未新增或改写。")
    lines.append("")

    t1 = payload["tables"]["s22_branch_claims"]
    lines.append("## 表 1  " + t1["title"])
    lines.append("")
    lines.append(md_table(
        t1["columns"],
        [[r["branch"], r["definition"], r["verdict"], r["evidence"], r["evidence_files"]]
         for r in t1["rows"]]))
    lines.append("")
    lines.append("> " + t1["note"])
    lines.append("")
    lines.append("**声明一（分支认领总述）**：" + payload["statements"]["branch_summary"])
    lines.append("")

    t2 = payload["tables"]["s23_minimum_outcome"]
    lines.append("## 表 2  " + t2["title"])
    lines.append("")
    lines.append(md_table(
        t2["columns"],
        [[r["id"], r["item"], r["status"], r["evidence"],
          r["artifact_check"] + "（" + "、".join(a["path"] for a in r["resolved_artifacts"])
          + (("；" + r["note"]) if r["note"] else "") + "）",
          r["paper_section"]] for r in t2["rows"]]))
    lines.append("")
    lines.append("> " + t2["note"])
    lines.append("")

    t3 = payload["tables"]["s11_feature_cost"]
    lines.append("## 表 3  " + t3["title"])
    lines.append("")
    lines.append(md_table(
        t3["columns"],
        [[r["tier"], r["features"], r["availability"], r["allowed_use"]] for r in t3["rows"]]))
    lines.append("")
    lines.append("> " + t3["note"])
    lines.append("")

    t4 = payload["tables"]["s25_rl_part2_mapping"]
    lines.append("## 表 4  " + t4["title"])
    lines.append("")
    lines.append("**声明二（创新边界，≤200 字）**：" + payload["statements"]["innovation_boundary"])
    lines.append("")
    lines.append(md_table(
        t4["columns"],
        [[r["entry"], r["source"], r["marker"] + "：" + r["used_where"], r["cite_at"]]
         for r in t4["rows"]]))
    lines.append("")
    lines.append("> " + t4["note"])
    lines.append("")

    lines.append("## 数据核查提示（data flags）")
    lines.append("")
    for flag in payload["data_flags"]:
        lines.append("- " + flag["text"])
    lines.append("")

    lines.append("## 结构计数（供程序化取数）")
    lines.append("")
    lines.append("- 分支判决：" + "；".join(
        "%s=%s" % (r["letter"], r["verdict"]) for r in t1["rows"]))
    lines.append("- §23 PARTIAL 条目：" + (", ".join(t2["partial_ids"]) or "无"))
    lines.append("- RL Part II 无真实使用证据（仅方法学背景）：%d 条 —— %s"
                 % (len(t4["without_direct_evidence"]), "、".join(t4["without_direct_evidence"])))
    lines.append("- feature_cost_level 实际取值：" + " / ".join(t3["feature_cost_level_values"]))
    lines.append("")

    return "\n".join(lines)

# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def build_payload():
    branch = build_branch_table()
    checklist = build_checklist_table()
    feature_cost = build_feature_cost_table()
    rl_mapping = build_rl_mapping_table()

    inputs = [
        ("核心文件/ranking-electrolyte-materials-v2.md", CORE_V2),
        ("核心文件/ranking-electrolyte-materials-reading-list.md", CORE_READING_LIST),
        ("论文/build_paper_docx.py", PAPER_BUILDER),
        ("outputs/week9/stage10_ladder.json", STAGE10_LADDER),
        ("outputs/week5/c1_state_identity.json", C1_STATE_IDENTITY),
        ("outputs/week7/stage7_ml_results.json", STAGE7_RESULTS_JSON),
        ("outputs/week7/stage7_ml_results.csv", STAGE7_RESULTS_CSV),
        ("outputs/week7/feature_manifest.json", FEATURE_MANIFEST),
        ("outputs/week7/stage8_al_results.json", STAGE8_AL),
        ("outputs/week4/p2_decision_stability.json", P2_DECISION_STABILITY),
        ("outputs/week22_hardening/stats_b1_b2.json", HARDENING_STATS),
        ("outputs/week23/shell3_xtb_sign_test.json", WEEK23_XTB),
        ("outputs/week8/stage9_results.json", STAGE9_RESULTS),
    ]

    def key(path):
        try:
            return path.resolve().relative_to(REPO_ROOT.parent.resolve()).as_posix()
        except ValueError:
            return path.resolve().as_posix()

    return {
        "stage": "Week 24 -- core-file promise vs delivered alignment",
        "generated_by": "scripts/analyze_w24_alignment.py",
        "read_only_inputs": [{"path": key(p), "exists": p.exists()} for _, p in inputs],
        "tables": {
            "s22_branch_claims": branch,
            "s23_minimum_outcome": checklist,
            "s11_feature_cost": feature_cost,
            "s25_rl_part2_mapping": rl_mapping,
        },
        "statements": {
            "branch_summary": BRANCH_SUMMARY,
            "innovation_boundary": INNOVATION_BOUNDARY,
            "innovation_boundary_char_count": count_chars(INNOVATION_BOUNDARY),
        },
        "data_flags": build_data_flags(),
        "counts": {
            "branch_verdicts": {r["letter"]: r["verdict"] for r in branch["rows"]},
            "checklist_partial_ids": checklist["partial_ids"],
            "checklist_artifact_missing": [r["id"] for r in checklist["rows"]
                                           if r["artifact_check"] != "OK"],
            "rl_without_direct_evidence": rl_mapping["without_direct_evidence"],
            "n_rl_without_direct_evidence": len(rl_mapping["without_direct_evidence"]),
            "feature_cost_level_values": feature_cost["feature_cost_level_values"],
        },
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    parser.add_argument("--check", action="store_true",
                        help="re-render and fail if the files on disk differ")
    args = parser.parse_args(argv)

    payload = build_payload()
    markdown = render_markdown(payload)
    json_text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"

    md_path = args.outdir / "core_alignment.md"
    json_path = args.outdir / "core_alignment.json"

    if args.check:
        problems = []
        if not md_path.exists() or md_path.read_text(encoding="utf-8") != markdown:
            problems.append(str(md_path))
        if not json_path.exists() or json_path.read_text(encoding="utf-8") != json_text:
            problems.append(str(json_path))
        if problems:
            sys.stderr.write("MISMATCH: " + ", ".join(problems) + "\n")
            return 1
        print("OK: core_alignment.md and core_alignment.json are up to date")
        return 0

    args.outdir.mkdir(parents=True, exist_ok=True)
    md_path.write_text(markdown, encoding="utf-8", newline="\n")
    json_path.write_text(json_text, encoding="utf-8", newline="\n")

    counts = payload["counts"]
    print(json.dumps({
        "wrote": [relpath(md_path), relpath(json_path)],
        "branch_verdicts": counts["branch_verdicts"],
        "checklist_partial_ids": counts["checklist_partial_ids"],
        "n_rl_without_direct_evidence": counts["n_rl_without_direct_evidence"],
        "innovation_boundary_char_count": payload["statements"]["innovation_boundary_char_count"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())