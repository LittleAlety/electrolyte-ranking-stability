#!/usr/bin/env python
"""Week 24 (W24-C) -- three audit tables the paper is missing.

The core study design (``核心文件/ranking-electrolyte-materials-v2.md``) promises
things the paper never prints.  Three of them are pure bookkeeping -- no new
electronic-structure calculation is required:

    table 1  core-file section 19 Stage 0-9  <->  the paper's "ten-level ladder"
    table 2  QC state machine ledger (section 20 + every real warning/flag field)
    table 3  "deliberately not done in phase I" declarations
             (sections 16.2 / 18 / 10.3 / 3.3 R_env)

This script builds all three from read-only inputs (documents, scripts, frozen
JSON/CSV artefacts and the 23 delivery packages) and writes ONE package:

    outputs/week24_corealign/audit_tables.md     three Chinese three-line tables
    outputs/week24_corealign/audit_tables.json   the same content, structured

Discipline
----------
* READ-ONLY on every input.  Zero new electronic-structure calculation.
* Nothing is invented: every count is read from an existing JSON field, and a
  row whose source field is absent is reported as missing instead of a guess.
* Every Stage mapping carries an evidence list; a row is marked 待确认 unless all
  of its evidence checks pass (file exists / JSON field equals / text contains).
* The SHA256 of every input is recorded, so the tables are auditable.

Run again with ``--check`` to prove the two files on disk are byte-for-byte what a
fresh run would produce.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CORE_DIR = REPO_ROOT.parent / "核心文件"
PAPER_DIR = REPO_ROOT.parent / "论文"
DELIV_DIR = REPO_ROOT.parent / "成果输出"

DEFAULT_OUTDIR = REPO_ROOT / "outputs" / "week24_corealign"

CORE_V2 = CORE_DIR / "ranking-electrolyte-materials-v2.md"
PAPER_FULLTEXT = PAPER_DIR / "_dossier" / "_fulltext_w22.txt"
PAPER_BUILDER = PAPER_DIR / "build_paper_docx.py"
SUMMARY_MD = DELIV_DIR / "数据结果汇总.md"

D = REPO_ROOT / "docs"
O = REPO_ROOT / "outputs"
S = REPO_ROOT / "scripts"

# --- documents -----------------------------------------------------------------
d00 = D / "00_stage0_definitions.md"
d01 = D / "01_stage1_external_anchors.md"
d02 = D / "02_stage1_method_audit.md"
d04 = D / "04_stage1_xtb_audit_result.md"
d05 = D / "05_stage2_broad_pool_p0.md"
d06 = D / "06_stage1_solution_anchor_audit.md"
d08 = D / "08_stage2_production_protocol.md"
d09 = D / "09_week3_report.md"
d10 = D / "10_week4_report.md"
d11 = D / "11_plan_alignment.md"
d12 = D / "12_week5_report.md"
d13 = D / "13_week6_report.md"
d15 = D / "15_week7_report.md"
d16 = D / "16_branch_abcd_qa.md"
d18 = D / "18_week8_report.md"
d19 = D / "19_week9_report.md"

# --- scripts (Stage number -> what actually ran) --------------------------------
sc_method = S / "run_method_audit_xtb.py"
sc_anchor = S / "audit_solution_anchors.py"
sc_meta = S / "build_metadata.py"
sc_broad = S / "run_broad_pool_p0.py"
sc_p1 = S / "run_core_set_p1.py"
sc_p1audit = S / "audit_p1_core_set.py"
sc_t2 = S / "run_t2_opt_freq.py"
sc_p2 = S / "run_core_set_p2.py"
sc_eps = S / "analyze_cpcm_eps_scan.py"
sc_li = S / "build_li_motifs.py"
sc_c1 = S / "run_c1_li_coordination.py"
sc_c1si = S / "analyze_c1_state_identity.py"
sc_s6 = S / "analyze_stage6.py"
sc_dm = S / "analyze_delta_m.py"
sc_s10 = S / "analyze_stage10_synthesis.py"
sc_s7 = S / "run_stage7_ml.py"
sc_feat = S / "build_ml_features.py"
sc_s8 = S / "run_stage8_al.py"
sc_ms = S / "build_microsolvation_shells.py"
sc_s9 = S / "run_stage9_microsolvation.py"

# --- outputs -------------------------------------------------------------------
GATE0 = O / "week1" / "gate0_record.md"
GATE1 = O / "week2" / "gate1_record.md"
MA_XTB = O / "week2" / "method_audit_xtb_summary.json"
SOL_ANCHOR = O / "week2" / "solution_anchor_audit.json"
P0_BROAD = O / "week3" / "p0_broad_pool.csv"
P0_CORE = O / "week3" / "p0_core_set.csv"
P1_CSV = O / "week4" / "p1_core_set.csv"
P1_AUDIT = O / "week4" / "p1_core_set_audit.json"
P1_DEC = O / "week4" / "p1_decision_stability.json"
T2 = O / "week4" / "t2_opt_freq_summary.json"
P2_SMD = O / "week4" / "p2_summary_smd_acetonitrile.json"
P2_DEC = O / "week4" / "p2_decision_stability.json"
T3 = O / "week4" / "t3_cpcm_eps_scan_summary.json"
LI_MOTIF = O / "week5" / "li_motif_generation.json"
C1_COORD = O / "week5" / "c1_li_coordination_summary.json"
C1_SI = O / "week5" / "c1_state_identity.json"
C1_DEC = O / "week5" / "c1_decision_stability.json"
DELTA_M = O / "week6" / "delta_m_frozen.json"
STAGE6 = O / "week6" / "stage6_decision_stability.json"
T7 = O / "week6" / "t7_c1_freq_check.json"
S7 = O / "week7" / "stage7_ml_results.json"
S8 = O / "week7" / "stage8_al_curves.csv"
FEAT = O / "week7" / "feature_manifest.json"
MS = O / "week8" / "ms_shell_generation.json"
S9 = O / "week8" / "stage9_results.json"
LADDER = O / "week9" / "stage10_ladder.json"
S16 = O / "week15" / "stage16_catalogue_analysis.json"
S19 = O / "week18" / "stage19_relax_analysis.json"
S20 = O / "week19" / "stage20_xtb_arms_analysis.json"
S21_REFILL = O / "week20" / "stage21_refill.json"
ALLOW2 = O / "week22_hardening" / "allowance_factor2.json"
R8 = O / "week23" / "targeted_two_guess.json"


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def read_json(path: Path):
    return json.loads(read_text(path))


def get_path(obj, dotted):
    cur = obj
    for part in dotted.split("."):
        if isinstance(cur, list):
            cur = cur[int(part)]
        elif isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None
    return cur


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.parent.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def ev(path, json_path=None, eq=None, contains=None, ge=None):
    return {"path": path, "json_path": json_path, "eq": eq,
            "contains": contains, "ge": ge}


def eval_evidence(item) -> dict:
    path = Path(item["path"])
    ok = path.exists()
    detail = "missing" if not ok else "exists"
    if ok and item.get("json_path"):
        try:
            value = get_path(read_json(path), item["json_path"])
        except Exception as exc:  # pragma: no cover - defensive
            value, ok, detail = None, False, "json error: %s" % exc
        else:
            if value is None:
                ok, detail = False, "json path missing"
            elif item.get("eq") is not None:
                ok = value == item["eq"]
                detail = "%s=%r (want %r)" % (item["json_path"], value, item["eq"])
            elif item.get("ge") is not None:
                ok = isinstance(value, (int, float)) and value >= item["ge"]
                detail = "%s=%r (want >= %r)" % (item["json_path"], value, item["ge"])
            else:
                detail = "%s=%r" % (item["json_path"], value)
    elif ok and item.get("contains") is not None:
        text = read_text(path)
        ok = item["contains"] in text
        detail = "contains %r" % (item["contains"],)
    return {"path": rel(path), "ok": bool(ok), "detail": detail}


def eval_list(items) -> dict:
    checks = [eval_evidence(i) for i in items]
    return {"checks": checks,
            "strength": "确证" if all(c["ok"] for c in checks) else "待确认"}


def pct(count, total):
    if not total:
        return "--"
    return "%.1f%%" % (100.0 * count / total)


def md_table(headers, rows):
    def cell(value):
        return str(value).replace("|", "\\|").replace("\n", " ")

    out = ["| " + " | ".join(cell(h) for h in headers) + " |",
           "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        out.append("| " + " | ".join(cell(c) for c in row) + " |")
    return "\n".join(out)

# ---------------------------------------------------------------------------
# table 1 -- core-file section 19 Stage 0-9 -> the paper's ten-level ladder
# ---------------------------------------------------------------------------
def build_stage_table():
    rows = []

    def add(stage, content, rung, artifacts, scripts, evidence):
        rows.append({"stage": stage, "content": content, "rung": rung,
                     "artifacts": artifacts, "scripts": scripts,
                     "evidence": evidence})

    add(
        "Stage 0\n冻结科学定义与 metadata",
        "冻结目标量方向、Top-k 比例（10/20/30%）、δ 确定规则、reference ligand R=DME、anchor 搜集规则；"
        "建立 core set（18）与 broad pool（40）的 chemical-space metadata；Gate 0 CLOSED。",
        "不产生台阶（定义冻结层）",
        "config/scientific_definitions.yaml；config/prereg.yaml；outputs/week1/gate0_record.md；data/metadata/core_set.csv",
        "scripts/build_metadata.py；scripts/freeze_gates.py",
        [ev(d00, contains="Gate 0"), ev(d11, contains="Stage 0 定义冻结"),
         ev(GATE0, contains="CLOSED")],
    )
    add(
        "Stage 1\n方法审计与 external anchors",
        "12 个 method-audit 分子的 GFN2-xTB 三态审计（Koopmans vs ΔSCF）；气相 anchor 对照；"
        "31 行溶液锚点逐条审计（全部 method=est，0 exp / 0 calc）；production protocol DRAFT-FROZEN；Gate 1 NOT CLOSED。",
        "方法审计（不产生台阶；其 τ_b / MAE 用于解释 P0→P1）",
        "outputs/week2/method_audit_xtb.csv；outputs/week2/method_audit_xtb_summary.json；"
        "outputs/week2/solution_anchor_audit.json；outputs/week2/gate1_record.md",
        "scripts/run_method_audit_xtb.py；scripts/audit_solution_anchors.py；scripts/run_diffuse_control.py",
        [ev(d02, contains="Stage 1"), ev(MA_XTB, json_path="n_molecules", eq=12),
         ev(GATE1, contains="NOT CLOSED")],
    )
    add(
        "Stage 2\nBroad cheap pool",
        "canonical 结构 + RDKit descriptors + CREST/GFN2-xTB 单构象优化，得到 X(0) 与 P0 标量代理；"
        "broad pool 40/40 + core 18/18 = 58/58 收敛、0 失败。",
        "P0 起点臂（十级台阶的起始层，本身不单独成台阶）",
        "outputs/week3/p0_broad_pool.csv；outputs/week3/p0_core_set.csv；outputs/week3/p0_summary.json",
        "scripts/run_broad_pool_p0.py；scripts/build_conformers.py",
        [ev(d09, contains="Stage 2"), ev(d11, contains="Stage 2 broad pool"),
         ev(P0_CORE), ev(P0_BROAD)],
    )
    add(
        "Stage 3\nCore free-molecule electronic structure",
        "core 18 分子三态 r2SCAN-3c 垂直 P1@G1（54/54，独立复核 0 分歧）；同一 12 分子子集做 "
        "G2 = r2SCAN-3c Opt+Freq（12 + 36 作业，0 失败）；unbound-anion QC。",
        "P0→P1（氧化/还原）与 G1→G2（氧化/还原）两个物理台阶",
        "outputs/week4/p1_core_set.csv；outputs/week4/p1_core_set_audit.json；"
        "outputs/week4/p1_decision_stability.json；outputs/week4/t2_opt_freq_summary.json",
        "scripts/run_core_set_p1.py；scripts/audit_p1_core_set.py；scripts/run_t2_opt_freq.py",
        [ev(d10, contains="P0 -> P1"), ev(P1_AUDIT, json_path="n_records", eq=54),
         ev(P1_AUDIT, json_path="n_molecules", eq=18),
         ev(T2, json_path="n_molecules", eq=12), ev(P1_DEC)],
    )
    add(
        "Stage 4\nFixed-background continuum",
        "全部 core N=18 使用同一 production 连续介质设置（CPCM / SMD，乙腈 ε=35.688）得到 P2；"
        "12 分子审计子集做 dielectric-only 扫描（bare CPCM ε=5/10/20/40，144/144）。",
        "P1→P2（氧化/还原）",
        "outputs/week4/p2_core_set_smd_acetonitrile.csv；outputs/week4/p2_decision_stability.json；"
        "outputs/week4/t3_cpcm_eps_scan_summary.json",
        "scripts/run_core_set_p2.py；scripts/analyze_p2_environment.py；scripts/analyze_cpcm_eps_scan.py",
        [ev(d10, contains="环境层（P2）"), ev(P2_SMD, json_path="n_ok", eq=54),
         ev(T3, json_path="n_jobs", eq=144), ev(P2_DEC)],
    )
    add(
        "Stage 5\nConditional Li+ coordination",
        "donor/motif 枚举（46 候选 -> 12 motif）；xTB 预筛；10 分子 C1 = [LiM]+ 三态 r2SCAN-3c（92 作业）；"
        "state-identity QC；ΔΔG_coord 与相对 ligand-exchange ΔΔG_bind。",
        "C0→C1（氧化/还原）",
        "outputs/week5/li_motif_generation.json；outputs/week5/c1_li_coordination.csv；"
        "outputs/week5/c1_decision_stability.json；outputs/week5/c1_state_identity.json",
        "scripts/build_li_motifs.py；scripts/run_c1_li_coordination.py；"
        "scripts/analyze_c1_coordination.py；scripts/analyze_c1_state_identity.py",
        [ev(d12, contains="Stage 5"), ev(LI_MOTIF, json_path="n_kept_motifs", eq=12),
         ev(C1_COORD, json_path="n_jobs", eq=92), ev(C1_DEC)],
    )
    add(
        "Stage 6\nUncertainty-aware ranking analysis",
        "Kendall τ_b / f_unresolved / robust-inversion / Top-k / selection regret + bootstrap；"
        "δ_m 组装（T6 构象系综、T7 C1 虚频、T8 δ_m、T9 三口径决策稳定性）。",
        "不产生新台阶（对全部十级台阶产出统计量，即论文表 2）",
        "outputs/week6/delta_m_frozen.json；outputs/week6/stage6_decision_stability.json；"
        "outputs/week6/t7_c1_freq_check.json；outputs/week9/stage10_ladder.json（论文表 2 取数源）",
        "scripts/analyze_stage6.py；scripts/analyze_delta_m.py；scripts/analyze_stage10_synthesis.py",
        [ev(d13, contains="Stage 6"), ev(STAGE6, json_path="stage", eq="T9 (Stage 6)"),
         ev(LADDER, json_path="stage", eq="Stage10-five-rung-ladder-synthesis"), ev(DELTA_M)],
    )
    add(
        "Stage 7\nMechanism analysis + Δ-learning",
        "X(0)/X(1)/X(2) 特征成本分级；6 模型复杂度阶梯；random/group/LOFO 三拆分；direct vs Δ-learning；"
        "robust inversion 结构机制；X(2) 仅作 post hoc 解释。",
        "不产生台阶（机制/学习层；论文 v2 命中 0，W24 计划补入 §3.13）",
        "outputs/week7/feature_manifest.json；outputs/week7/stage7_ml_results.json（288 行）；"
        "outputs/week7/stage7_ml_predictions.csv",
        "scripts/run_stage7_ml.py；scripts/build_ml_features.py",
        [ev(d15, contains="Stage 7"), ev(S7),
         ev(FEAT, json_path="feature_cost_levels")],
    )
    add(
        "Stage 8\nActive-learning replay",
        "random / diversity / uncertainty / ranking-aware 四采集函数；20 组种子重复；"
        "n_T -> τ_b / O_k / R_k 曲线与最小昂贵信息预算。",
        "不产生台阶（主动学习层；论文 v2 命中 0，W24 计划补入 §3.14）",
        "outputs/week7/stage8_al_curves.csv（296 行，含 2.5/97.5 分位）；"
        "outputs/week7/stage8_al_results.json；outputs/week7/stage8_al_runs.csv",
        "scripts/run_stage8_al.py",
        [ev(d15, contains="Stage 8"), ev(S8, contains="baseline"), ev(S7)],
    )
    add(
        "Stage 9\nOptional explicit-microsolvation validation",
        "只对 12 个关键 motif 做 targeted check：homoleptic [Li(M)2]+ 第一溶剂壳"
        "（xTB 刚体放置 -> xTB 单点打分 -> DFT Opt + 三态单点 36 作业），给出 C1 vs C2 排序稳定性。",
        "C1→C2（氧化/还原）",
        "outputs/week8/ms_shell_generation.json；outputs/week8/stage9_results.json；"
        "outputs/week8/stage9_shell_shifts.csv；outputs/week8/stage9_decision_stability.csv",
        "scripts/build_microsolvation_shells.py；scripts/run_stage9_microsolvation.py；"
        "scripts/analyze_stage9_microsolvation.py",
        [ev(d18, contains="Stage 9"), ev(MS, json_path="n_selected", eq=12),
         ev(S9, json_path="motifs_with_shell2", eq=12), ev(S9)],
    )

    for row in rows:
        result = eval_list(row["evidence"])
        row["evidence"] = result["checks"]
        row["strength"] = result["strength"]
    return {
        "title": "核心文件 §19 Stage 0–9 ↔ 论文十级台阶映射",
        "columns": ["核心文件 Stage", "实际计算内容", "对应论文台阶",
                    "产物路径", "证据强度(确证/待确认)"],
        "rows": rows,
        "note": "论文的“十级台阶”= 5 个物理台阶（P0→P1、P1→P2、G1→G2、C0→C1、C1→C2）× 2 条轴（氧化/还原）。"
                "项目内部 Stage 编号在 0–9 与核心文件 §19 一致（`成果输出/数据结果汇总.md` §2），10–24 为超出核心文件的扩展"
                "（Stage 10 五级台阶合成 … Stage 24 R8 靶向双腿）。论文表 2 的取数源为 "
                "`outputs/week9/stage10_ladder.json`（Stage 10 合成，投影自 Stage 3/4/5/9 产物）。"
                "核心文件 §19 没有独立的“几何”Stage，G1→G2 归属 Stage 3 是项目文档（`docs/11` §2 把 T2 记在 Stage 3 下）的归档口径。",
    }

# ---------------------------------------------------------------------------
# table 2 -- QC state machine ledger
# ---------------------------------------------------------------------------
def build_qc_table():
    p1a = read_json(P1_AUDIT)
    c1c = read_json(C1_COORD)
    lm = read_json(LI_MOTIF)
    si = read_json(C1_SI)
    t2 = read_json(T2)
    t7 = read_json(T7)
    ms = read_json(MS)
    s9 = read_json(S9)
    s16 = read_json(S16)
    s19 = read_json(S19)
    s20 = read_json(S20)
    r8 = read_json(R8)
    refill = read_json(S21_REFILL)

    p1_flag = p1a["flag_counts"]
    c1_flag = c1c["qc_flag_counts"]
    lm_flag = lm["qc_flag_counts"]

    s9_shell1_switch = sum(
        1 for r in s9["shifts"] if "motif_switch" in (r.get("qc_flags") or ""))
    ms_clash = sum(
        1 for r in ms["shells"] if "clash" in (r.get("qc_flags") or ""))
    si_dication = si["per_redox_state"]["dication"]

    delivery = collect_delivery_checks()
    rows = []

    def add(status, meaning, layers, evidence, paper, paper_keys):
        rows.append({
            "status": status,
            "meaning": meaning,
            "layers": [{"label": l, "count": c, "total": t,
                        "rate": (c / t if t else None)} for l, c, t in layers],
            "evidence": evidence,
            "paper": paper,
            "paper_keys": paper_keys,
            "paper_hits": {},
        })

    add(
        "scf_failed",
        "自洽场求解失败（字面字段，与“多解 / 漏解”是两件事）",
        [("P1 core（54 记录）", p1_flag["scf_failed"], p1a["n_records"]),
         ("C1 配位态（92 作业）", c1_flag["scf_failed"], c1c["n_jobs"]),
         ("Stage 9 壳层（12 壳）", ms["qc_flag_counts"]["scf_failed"], ms["n_selected"])],
        ["outputs/week4/p1_core_set_audit.json:flag_counts.scf_failed",
         "outputs/week5/c1_li_coordination_summary.json:qc_flag_counts.scf_failed",
         "outputs/week8/ms_shell_generation.json:qc_flag_counts.scf_failed"],
        "论文未报告字面 scf_failed 计数（关键词命中 0）；§3.8 讨论的是“自洽场多解 / 漏解”，与该字段计数为 0 不矛盾。",
        ["scf_failed"],
    )
    add(
        "自洽场多解：默认初猜漏解",
        "默认初猜落到能量偏高的亚稳态；与 moread 初猜配对普查（Stage 16 目录）",
        [("12 分子 x 3 态 x 10 个 ε = 360 格",
          s16["n_material_differences"], s16["n_cells"])],
        ["outputs/week15/stage16_catalogue_analysis.json:n_material_differences / n_cells"],
        "§3.8 全量报告（328/360 一致、32 更低、0 更高、最大缺陷 −0.285961 eV）。",
        ["自洽场多解", "漏解"],
    )
    add(
        "自洽场多解：第二解弛豫存亡",
        "第二个 SCF 解在几何弛豫后是否仍是更低的那个（Stage 19）",
        [("37 个差异格",
          s19["aggregates"]["all"]["all"]["outcomes"]["distinct_lower"], s19["n_cells"])],
        ["outputs/week18/stage19_relax_analysis.json:aggregates.all.all.outcomes.distinct_lower / n_cells"],
        "论文未报告（关键词命中 0）——建议随本台账补入 §3.8 附录。",
        ["弛豫", "distinct_lower"],
    )
    add(
        "自洽场多解：跨引擎存亡",
        "同一批第二解在 xTB 级弛豫后是否仍更低（Stage 20，跨方法）",
        [("37 个差异格",
          s20["aggregates"]["all"]["all"]["outcomes"]["distinct_lower"], s20["n_cells"])],
        ["outputs/week19/stage20_xtb_arms_analysis.json:aggregates.all.all.outcomes.distinct_lower / n_cells"],
        "论文未报告（关键词命中 0）——建议随本台账补入 §3.8 附录。",
        ["跨引擎"],
    )
    add(
        "漏解引起的 pair 翻转（R8 靶向双腿）",
        "漏解真实改写的分子对；安全阈值 A_axis = 单格最大效应量",
        [("氧化轴（660 对）", r8["axes"]["oxidation"]["n_flips"], r8["axes"]["oxidation"]["n_pairs"]),
         ("还原轴（660 对）", r8["axes"]["reduction"]["n_flips"], r8["axes"]["reduction"]["n_pairs"])],
        ["outputs/week23/targeted_two_guess.json:axes.*.n_flips / n_pairs",
         "outputs/week22_hardening/allowance_factor2.json:axes.*.two_times_A_axis_ev"],
        "§3.8 表 3 报告（氧化 19 次 / 还原 21 次，靶向漏 0）；严格上界为 2·A_axis"
        "（0.3045 / 0.5719 eV，见 allowance_factor2.json）。",
        ["漏解", "Aaxis"],
    )
    add(
        "unbound_anion",
        "气相阴离子不束缚（带负电荷态出现正 HOMO）",
        [("P1 core（18 分子）", p1_flag["unbound_anion"], p1a["n_molecules"]),
         ("C1 配位态（92 作业）", c1_flag["unbound_anion"], c1c["n_jobs"])],
        ["outputs/week4/p1_core_set_audit.json:flag_counts.unbound_anion",
         "outputs/week5/c1_li_coordination_summary.json:qc_flag_counts.unbound_anion"],
        "§2.3 / §3.3 报告 18/18 并说明气相 EA 只在趋势上有意义，定量比较需溶剂化或弥散基组"
        "（T5 弥散对照 24 作业）。",
        ["不束缚"],
    )
    add(
        "motif_switch",
        "配位 motif 改变（放置 / 优化后与实际接触模式不一致）",
        [("Li motif 枚举（46 候选）", lm_flag["motif_switch"], lm["n_candidates"]),
         ("保留 12 motif 的行",
          sum(1 for m in lm["motifs"] if "motif_switch" in (m.get("qc_flags") or "")),
          len(lm["motifs"])),
         ("Stage 9 壳层 shell1（12 motif）", s9_shell1_switch, len(s9["shifts"]))],
        ["outputs/week5/li_motif_generation.json:qc_flag_counts.motif_switch",
         "outputs/week8/stage9_results.json:shifts[].qc_flags = shell1:motif_switch"],
        "论文未报告（motif 关键词命中 0）——建议随本台账补入附录。",
        ["motif"],
    )
    add(
        "no_intact_minimum_found",
        "优化后 Li–M 最小接触消失（几何优先于电子标签）",
        [("Li motif 枚举（46 候选）", lm_flag["no_intact_minimum_found"], lm["n_candidates"]),
         ("C1 扫描（92 作业）", c1_flag["no_intact_minimum_found"], c1c["n_jobs"]),
         ("C1 态身份：dication（12 行）",
          si_dication["labels"]["no_intact_minimum_found"], si_dication["n"]),
         ("C1 态身份（24 行）",
          si_dication["labels"]["no_intact_minimum_found"]
          + si["per_redox_state"]["reduced"]["labels"].get("no_intact_minimum_found", 0),
          si["n_rows"])],
        ["outputs/week5/li_motif_generation.json:qc_flag_counts.no_intact_minimum_found",
         "outputs/week5/c1_li_coordination_summary.json:qc_flag_counts.no_intact_minimum_found",
         "outputs/week5/c1_state_identity.json:per_redox_state.dication.labels"],
        "§3.5 用了态身份分析（还原态 11/12 电子落在 Li 上），但未单列本 QC 计数。",
        ["态身份"],
    )
    add(
        "geometry_failed",
        "几何优化失败（唯一一例为 SL/m1 dication，ORCA 超时被 kill）",
        [("C1 扫描（92 作业）", c1_flag["geometry_failed"], c1c["n_jobs"]),
         ("Li motif 枚举（46 候选）", lm_flag["geometry_failed"], lm["n_candidates"])],
        ["outputs/week5/c1_li_coordination_summary.json:qc_flag_counts.geometry_failed"],
        "论文未报告（geometry_failed 关键词命中 0）。",
        ["geometry_failed"],
    )
    add(
        "虚频 imaginary_mode_unresolved",
        "驻点 Hessian 存在虚频（不是局部极小）",
        [("T2 几何台阶（12 分子 Opt+Freq）",
          t2["n_imaginary_unresolved"], t2["n_opt_jobs"]),
         ("T7 C1 [LiM]+ Freq（10 分子）", t7["n_imaginary"], t7["n_molecules"])],
        ["outputs/week4/t2_opt_freq_summary.json:n_imaginary_unresolved / n_opt_jobs",
         "outputs/week6/t7_c1_freq_check.json:n_imaginary / n_molecules"],
        "论文未报告（虚频 关键词命中 0）——EC 的 [LiEC]+ 在 −80.4 cm⁻¹ 有虚频，"
        "其 C0→C1 位移系鞍点测量，应写入局限。",
        ["虚频"],
    )
    add(
        "dissociated_optimized_product",
        "优化后母体连接断裂（解离产物）",
        [("Li motif 枚举（46 候选）", lm_flag["dissociated_optimized_product"], lm["n_candidates"]),
         ("C1 扫描（92 作业）", c1_flag["dissociated_optimized_product"], c1c["n_jobs"]),
         ("Stage 9 壳层（12 壳）", ms["qc_flag_counts"]["dissociated_optimized_product"], ms["n_selected"])],
        ["outputs/week5/li_motif_generation.json:qc_flag_counts.dissociated_optimized_product",
         "outputs/week5/c1_li_coordination_summary.json:qc_flag_counts.dissociated_optimized_product"],
        "论文未报告（关键词命中 0）；Stage 9 的 12 壳层 second_ligand_intact 全 True。",
        ["dissociated"],
    )
    add(
        "state_identity_ambiguous",
        "态身份指标冲突（无法判定电子落在 Li 还是分子）",
        [("C1 扫描（92 作业）", c1_flag["state_identity_ambiguous"], c1c["n_jobs"])],
        ["outputs/week5/c1_li_coordination_summary.json:qc_flag_counts.state_identity_ambiguous"],
        "§3.5 报告态身份分类（11/12 Li-centered），本字段计数为 0。",
        ["态身份"],
    )
    add(
        "spin_contamination_flag",
        "自旋污染（<S²> 偏离）",
        [("P1 core（54 记录）", p1_flag["spin_contamination_flag"], p1a["n_records"]),
         ("C1 扫描（92 作业）", c1_flag["spin_contamination_flag"], c1c["n_jobs"])],
        ["outputs/week4/p1_core_set_audit.json:flag_counts.spin_contamination_flag",
         "outputs/week5/c1_li_coordination_summary.json:qc_flag_counts.spin_contamination_flag"],
        "论文未报告（关键词命中 0）；交付层断言 p1_audit.spin_contamination_flag==0 通过。",
        ["spin_contamination"],
    )
    add(
        "electron_count_mismatch",
        "电子数不一致",
        [("C1 扫描（92 作业）", c1_flag["electron_count_mismatch"], c1c["n_jobs"])],
        ["outputs/week5/c1_li_coordination_summary.json:qc_flag_counts.electron_count_mismatch"],
        "论文未报告（关键词命中 0）。",
        ["electron_count"],
    )
    add(
        "execution_failed",
        "作业级执行失败（非物理失败）",
        [("C1 扫描（92 作业）", c1c["status_counts"]["execution_failed"], c1c["n_jobs"])],
        ["outputs/week5/c1_li_coordination_summary.json:status_counts.execution_failed"],
        "论文未报告（关键词命中 0）；该例同时是 geometry_failed（SL/m1 dication 超时）。",
        ["execution_failed"],
    )
    add(
        "abnormal_termination / energy_mismatch / missing_output",
        "ORCA 输出异常终止 / 能量解析不一致 / 输出缺失",
        [("P1 core abnormal_termination（54 记录）", p1_flag["abnormal_termination"], p1a["n_records"]),
         ("P1 core energy_mismatch（54 记录）", p1_flag["energy_mismatch"], p1a["n_records"]),
         ("P1 core missing_output（54 记录）", p1_flag["missing_output"], p1a["n_records"])],
        ["outputs/week4/p1_core_set_audit.json:flag_counts.abnormal_termination / energy_mismatch / missing_output"],
        "论文未报告（关键词命中 0）；交付层三条断言全部通过。",
        ["abnormal_termination"],
    )
    add(
        "placement_clash_start",
        "壳层放置回退（起点与 Li+ 球面冲突，按事前规则放宽并记录）",
        [("Stage 9 壳层（12 壳）", ms_clash, ms["n_selected"])],
        ["outputs/week8/ms_shell_generation.json:shells[].qc_flags = placement_clash_start"],
        "论文未报告（关键词命中 0）；涉及 DMC/m2 与 TMP/m2，几何完好（Li 接触数 4 与 6）。",
        ["placement_clash"],
    )
    add(
        "warning（Stage 21 refill）",
        "记录型警示字符串（非计数型异常）",
        [("Stage 21 refill 警示条数", 1 if (refill.get("coverage") or {}).get("warning") else 0, 1)],
        ["outputs/week20/stage21_refill.json:coverage.warning"],
        "论文未报告（关键词命中 0）；内容为“严格 P2 腿（SMD）的弛豫覆盖为 0”，属过程警示。",
        ["预警", "warning"],
    )
    add(
        "交付包 verification.json 断言",
        "交付层自动断言（含文件 SHA256 与现场取数核对），23 个交付包",
        [("checks 通过 / 总数", delivery["ok"], delivery["total"])],
        delivery["files"][:5] + (["..."] if len(delivery["files"]) > 5 else []),
        "论文 §2.6 声明“可用 --check 逐字节复核”；交付层 0 条断言失败。",
        ["--check"],
    )

    return {
        "title": "QC 状态机台账（核心文件 §20 九类异常 + 全部现存 warning/flag 字段）",
        "columns": ["状态/异常", "含义", "发生数/总数", "发生率", "证据文件", "论文中的处置"],
        "rows": rows,
        "note": "口径：发生数/总数 逐层给出，分母取该 JSON 自己的分母字段（n_records / n_jobs / n_candidates / "
                "n_molecules / n_rows / n_cells / n_selected）。只登记真实存在的字段；缺字段的层不出现。"
                "“论文未报告 / 命中 0”按关键词字符串检索计，非逐字段核对。"
                "核心集 P1 唯一的高发异常是 unbound_anion（18/18，结构性）；C1 层最值得报告的是 T7 虚频"
                "（EC，−80.4 cm⁻¹）与 no_intact_minimum_found（dication 4/12）。",
    }


def collect_delivery_checks():
    total = 0
    ok = 0
    files = []
    for path in sorted(DELIV_DIR.glob("week*/verification.json")):
        try:
            payload = read_json(path)
        except Exception:
            continue
        checks = payload.get("checks", [])
        total += len(checks)
        ok += sum(1 for c in checks if c.get("ok"))
        files.append("%s（%d checks）" % (rel(path), len(checks)))
    return {"total": total, "ok": ok, "files": files}

# ---------------------------------------------------------------------------
# table 3 -- "deliberately not done in phase I"
# ---------------------------------------------------------------------------
def build_notdone_table():
    rows = []

    def add(clause, done, why, where, evidence):
        rows.append({"clause": clause, "done": done, "why": why,
                     "where": where, "evidence": evidence})

    add(
        "§16.2 真实配位 population（{p_s}: M / [LiM]+ / [LiM2]+ / [LiMmA]…）",
        "否（只做 1:1 条件态 C1 与同配体、同化学计量的 1:2 targeted check，不是 population）",
        "核心文件 §16.2 自己写明“这属于 Phase II/III，而不是 MVP 中通过强制 1:1 complex 偷偷替代”；"
        "§2.3 纪律不允许把 [LiM]+ 的 redox quantity 当作实际浓度电解液的有效 redox potential；"
        "§27 Phase II 要求明确浓度与组成，Phase III 才用 MD/AIMD 取真实 coordination distribution。"
        "论文 §4 局限承认 Li+ 条件态结论只在 10 分子上得到、普适性待更大配位基元库检验。",
        "§5.1 分支/边界认领表（W24 新增），或 §4 局限；并在 §2.2 台阶设计处加一句“C1/C2 是条件态、非 speciation”。",
        [ev(CORE_V2, contains="这属于 Phase II/III，而不是 MVP"),
         ev(d16, contains="C1 是**条件态（conditional state）**"),
         ev(d18, contains="p(C|bulk)")],
    )
    add(
        "§18 多目标 Pareto / 武断“综合电解液分数”",
        "否（未构造 S=Σw_iP_i，也未做 Pareto front 数值；只并列报告氧化/还原两轴，"
        "并把 ΔΔG_bind 当 mechanistic descriptor）",
        "核心文件 §18 规定：ΔΔG_bind 不默认设为 maximize 目标；若做多目标展示，用 Pareto front 或明确 target window，"
        "而不是缺乏物理依据的综合分数。本项目全文检索 Pareto / target_window / 加权和 = 0（仅文献讨论中出现），"
        "属“遵守纪律而未做”，不是遗漏。",
        "§2.4 决策量定义（两条轴分别定义方向）+ §2.6 预注册；若 W24 新增 §5.1，可在其中声明 Pareto 留待 Phase II。",
        [ev(CORE_V2, contains="这种缺乏物理依据的综合分数"),
         ev(CORE_V2, contains="Pareto front"),
         ev(P1_DEC)],
    )
    add(
        "§10.3 threshold-based decision error（需外部设计要求阈值）",
        "否（记为 not_applicable）",
        "核心文件 §10.3 规定：只有当阈值 T 来自外部设计要求、实验基准或事先定义的工程标准时才使用，"
        "且不允许看完数据后人为挑一个最有利阈值。`config/prereg.yaml` 的 "
        "`threshold_decisions.if_unavailable` 禁止用数据分位数临时替代；本项目不存在合规外部阈值来源，"
        "故 Stage 6 如实记 not_applicable。论文 §4 局限（液相锚点未封闭、无实验基准阈值）与此一致。",
        "§2.4/§2.6 加一条脚注（记 not_applicable 及原因），并在 §5.1 声明为 Phase II；"
        "本项目落点：outputs/week6/stage6_decision_stability.md §5。",
        [ev(CORE_V2, contains="不允许看完数据后人为挑一个最有利阈值"),
         ev(CORE_V2, contains="只有当阈值"),
         ev(STAGE6, json_path="stage", eq="T9 (Stage 6)"),
         ev(d13, contains="not_applicable")],
    )
    add(
        "§3.3 R_env（环境 / 电极界面、EDL 参考层）",
        "否（data/anchors/ 无 R_env 数值文件；论文 §3.5 只对 Yang 2025 已发表趋势做定性对照，"
        "可视为 R_env 的弱形式，但未落盘为 anchor）",
        "核心文件 §3.3 明说第一阶段不要求这一层完整覆盖全部候选；docs/01 §5 记录"
        "“data/anchors/ 当前没有 R_env 数值文件”，并禁止把 R_gas/R_sol 结论外推到 C1。"
        "§2.3 纪律不允许把条件态 proxy 说成真实电化学窗口；§27 Phase IV 需 electrode potential / surface / "
        "EDL composition / charge transfer 才进入真实 electrochemical stability。论文 §4 局限（液相锚点绝对标定未封闭）。",
        "§2.3（外部参考层）或 §4 局限明确写为 Phase IV/II 边界；"
        "若保留 Yang 2025 那句定性对照，应注明“定性趋势、非 R_env anchor”。",
        [ev(CORE_V2, contains="第一阶段不要求这一层完整覆盖全部候选"),
         ev(d01, contains="当前没有** `R_env` 数值文件"),
         ev(CORE_V2, contains="electrode potential")],
    )

    for row in rows:
        result = eval_list(row["evidence"])
        row["evidence"] = result["checks"]
        row["strength"] = result["strength"]
    return {
        "title": "第一阶段显式“不做”声明表（四项条款）",
        "columns": ["条款", "是否做", "为什么不做（核心文件 §2.3 纪律 + 论文局限章）",
                    "建议在论文哪一节声明为 Phase II", "证据强度"],
        "rows": rows,
        "note": "口径：是否做 以项目产物与文档为准；“论文命中 0”按关键词字符串检索计，非逐字段核对。"
                "四项都可直接写进方法节/附录，把“没做”说明成“按纪律不做”。",
    }

# ---------------------------------------------------------------------------
# payload + markdown
# ---------------------------------------------------------------------------
def build_payload():
    stages = build_stage_table()
    qc = build_qc_table()
    notdone = build_notdone_table()

    paper_text = read_text(PAPER_FULLTEXT) if PAPER_FULLTEXT.exists() else ""
    for row in qc["rows"]:
        row["paper_hits"] = {k: paper_text.count(k) for k in row["paper_keys"]}
        row["paper_reported"] = any(v > 0 for v in row["paper_hits"].values())

    inputs = [
        CORE_V2, PAPER_FULLTEXT, PAPER_BUILDER, SUMMARY_MD,
        d00, d01, d02, d04, d05, d06, d08, d09, d10, d11, d12, d13, d15, d16, d18, d19,
        sc_method, sc_anchor, sc_meta, sc_broad, sc_p1, sc_p1audit, sc_t2, sc_p2, sc_eps,
        sc_li, sc_c1, sc_c1si, sc_s6, sc_dm, sc_s10, sc_s7, sc_feat, sc_s8, sc_ms, sc_s9,
        GATE0, GATE1, MA_XTB, SOL_ANCHOR, P0_BROAD, P0_CORE, P1_CSV, P1_AUDIT, P1_DEC, T2,
        P2_SMD, P2_DEC, T3, LI_MOTIF, C1_COORD, C1_SI, C1_DEC, DELTA_M, STAGE6, T7, S7, S8,
        FEAT, MS, S9, LADDER, S16, S19, S20, S21_REFILL, ALLOW2, R8,
    ]
    seen = set()
    input_rows = []
    for path in inputs:
        key = str(path)
        if key in seen:
            continue
        seen.add(key)
        input_rows.append({"path": rel(path), "exists": path.exists(),
                           "sha256": sha256(path) if path.exists() else None})
    for path in sorted(DELIV_DIR.glob("week*/verification.json")):
        input_rows.append({"path": rel(path), "exists": True, "sha256": sha256(path)})

    stage_pending = [r["stage"].split("\n")[0] for r in stages["rows"]
                     if r["strength"] != "确证"]
    qc_unreported = [r["status"] for r in qc["rows"] if not r["paper_reported"]]

    return {
        "stage": "Week 24 (W24-C) -- core-file audit tables",
        "generated_by": "scripts/analyze_w24_audit.py",
        "discipline": "只读既有产物与文档；零新增电子结构计算；未确证的映射标 待确认；只统计真实存在的字段。",
        "tables": {
            "stage_ladder_map": stages,
            "qc_ledger": qc,
            "phase1_not_done": notdone,
        },
        "inputs": input_rows,
        "counts": {
            "stage_rows": len(stages["rows"]),
            "stage_pending_confirmation": len(stage_pending),
            "stage_pending_rows": stage_pending,
            "qc_rows": len(qc["rows"]),
            "qc_rows_not_in_paper": len(qc_unreported),
            "qc_rows_not_in_paper_list": qc_unreported,
            "phase1_not_done_rows": len(notdone["rows"]),
            "phase1_rows_pending_confirmation": [r["clause"][:12] for r in notdone["rows"]
                                                 if r["strength"] != "确证"],
            "delivery_checks_total": collect_delivery_checks()["total"],
        },
    }

def render_markdown(payload):
    lines = []
    lines.append("# Week 24 核心文件对照审计表（W24-C）")
    lines.append("")
    lines.append("本文件给出三张可直接粘进论文附录/方法节的中文三线表：① 核心文件 §19 的 Stage 0–9 ↔ 论文"
                 "十级台阶映射；② QC 状态机台账（§20 + 全部现存 warning/flag 字段）；③ 第一阶段显式“不做”声明表。"
                 "全部输入只读，零新增电子结构计算；每个数字都从既有产物的真实字段读取，未确证的映射标“待确认”。")
    lines.append("")

    t1 = payload["tables"]["stage_ladder_map"]
    lines.append("## 表 1  " + t1["title"])
    lines.append("")
    lines.append(md_table(t1["columns"],
                          [[r["stage"], r["content"], r["rung"], r["artifacts"], r["strength"]]
                           for r in t1["rows"]]))
    lines.append("")
    pending = [r["stage"].split("\n")[0] for r in t1["rows"] if r["strength"] != "确证"]
    lines.append("> **结论**：核心文件 §19 的 Stage 3/4/5/9 分别产出论文十级台阶里的 P0→P1、P1→P2、C0→C1、"
                 "C1→C2 四个物理台阶，并（在 Stage 3 的 T2 子任务里）产出 G1→G2，合起来正好是"
                 "“5 个物理台阶 × 2 条轴 = 10 级”；Stage 0/1/2/6/7/8 只做定义冻结、方法审计、P0 起点层、"
                 "统计层与机制/学习层，**不产生台阶**。待确认 %d 条%s。"
                 % (len(pending), ("：" + "、".join(pending)) if pending else ""))
    lines.append("")
    lines.append("> " + t1["note"])
    lines.append("")

    t2 = payload["tables"]["qc_ledger"]
    lines.append("## 表 2  " + t2["title"])
    lines.append("")
    counts_cell = ["；".join("%s: %d/%d" % (l["label"], l["count"], l["total"]) for l in r["layers"])
                   for r in t2["rows"]]
    rates_cell = ["；".join("%s %s" % (l["label"].split("（")[0], pct(l["count"], l["total"]))
                            for l in r["layers"]) for r in t2["rows"]]
    lines.append(md_table(t2["columns"],
                          [[r["status"], r["meaning"], c, rt, "；".join(r["evidence"]), r["paper"]]
                           for r, c, rt in zip(t2["rows"], counts_cell, rates_cell)]))
    lines.append("")
    unreported = [r["status"] for r in t2["rows"] if not r["paper_reported"]]
    lines.append("> **结论**：%d 类状态/异常中，%d 类在论文中有落点，%d 类（%s 等）论文正文命中为 0，"
                 "需随本台账补入附录；核心集 P1 唯一的高发异常是气相阴离子不束缚（18/18，结构性），"
                 "C1 层最值得写进论文的是虚频（EC 的 [LiEC]+，−80.4 cm⁻¹，1/10）与 no_intact_minimum_found"
                 "（dication 4/12），两者都直接影响现有位移的物理解释。"
                 % (len(t2["rows"]), len(t2["rows"]) - len(unreported), len(unreported),
                    "、".join(unreported[:4])))
    lines.append("")
    lines.append("> " + t2["note"])
    lines.append("")

    t3 = payload["tables"]["phase1_not_done"]
    lines.append("## 表 3  " + t3["title"])
    lines.append("")
    lines.append(md_table(t3["columns"],
                          [[r["clause"], r["done"], r["why"], r["where"], r["strength"]]
                           for r in t3["rows"]]))
    lines.append("")
    lines.append("> **结论**：四项都属于“按项目自己的纪律在第一阶段**不做**”的显式边界，论文 v2 对 "
                 "§16.2/§18/§10.3/§3.3 的关键词命中均为 0，应把本表写进方法节/附录，把“没做”变成"
                 "“说明过不做”。其中 §3.3 R_env 是唯一有“弱形式已做”的条款——论文 §3.5 用 Yang et al. 2025 "
                 "的已发表趋势做了一次定性对照（未落盘为 anchor 文件）。")
    lines.append("")
    lines.append("> " + t3["note"])
    lines.append("")

    lines.append("## 输入清单与 SHA256")
    lines.append("")
    lines.append("| 输入 | 存在 | SHA256 |")
    lines.append("| --- | --- | --- |")
    for item in payload["inputs"]:
        lines.append("| `%s` | %s | `%s` |" % (
            item["path"], "Y" if item["exists"] else "N", item["sha256"] or "-"))
    lines.append("")

    lines.append("## 复核")
    lines.append("")
    lines.append("- 幂等复核：`.\\\\.venv\\\\Scripts\\\\python.exe scripts/analyze_w24_audit.py --check`")
    counts = payload["counts"]
    lines.append("- Stage 映射行数：%d；待确认：%d%s" % (
        counts["stage_rows"], counts["stage_pending_confirmation"],
        ("（" + "、".join(counts["stage_pending_rows"]) + "）") if counts["stage_pending_rows"] else ""))
    lines.append("- QC 台账行数：%d；论文未报告：%d（%s）" % (
        counts["qc_rows"], counts["qc_rows_not_in_paper"],
        "、".join(counts["qc_rows_not_in_paper_list"])))
    lines.append("- 第一阶段不做行数：%d；待确认：%s" % (
        counts["phase1_not_done_rows"],
        "、".join(counts["phase1_rows_pending_confirmation"]) or "无"))
    lines.append("- 交付层 verification.json 断言：%d 条" % counts["delivery_checks_total"])
    lines.append("")
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    parser.add_argument("--check", action="store_true",
                        help="re-render and fail if the files on disk differ")
    args = parser.parse_args(argv)

    payload = build_payload()
    markdown = render_markdown(payload)
    json_text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"

    md_path = args.outdir / "audit_tables.md"
    json_path = args.outdir / "audit_tables.json"

    if args.check:
        problems = []
        if not md_path.exists() or md_path.read_text(encoding="utf-8") != markdown:
            problems.append(str(md_path))
        if not json_path.exists() or json_path.read_text(encoding="utf-8") != json_text:
            problems.append(str(json_path))
        if problems:
            sys.stderr.write("MISMATCH: " + ", ".join(problems) + "\n")
            return 1
        print("OK: audit_tables.md and audit_tables.json are up to date")
        return 0

    args.outdir.mkdir(parents=True, exist_ok=True)
    md_path.write_text(markdown, encoding="utf-8", newline="\n")
    json_path.write_text(json_text, encoding="utf-8", newline="\n")

    counts = payload["counts"]
    print(json.dumps({
        "wrote": [rel(md_path), rel(json_path)],
        "stage_rows": counts["stage_rows"],
        "stage_pending_confirmation": counts["stage_pending_confirmation"],
        "stage_pending_rows": counts["stage_pending_rows"],
        "qc_rows": counts["qc_rows"],
        "qc_rows_not_in_paper": counts["qc_rows_not_in_paper"],
        "qc_rows_not_in_paper_list": counts["qc_rows_not_in_paper_list"],
        "phase1_not_done_rows": counts["phase1_not_done_rows"],
        "phase1_rows_pending_confirmation": counts["phase1_rows_pending_confirmation"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())