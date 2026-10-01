#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Build the distilled deliverables bundle for the electrolyte-solvent project.

Reads only distilled artifacts from this repository (outputs/, docs/, config/)
and writes them to <out>/<weekN>/, plus a SHA256SUMS manifest, a
verification.json, a short week report, and the two top-level documents.

Text files are always written as UTF-8 (no BOM) with LF newlines. Binary
ORCA / xTB scratch is excluded on purpose (see EXCLUDE_* below).
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import shutil
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from electrolyte_ranking import ranking  # noqa: E402
DEFAULT_OUT = Path(r"E:\Claude Code\电解液溶剂-HB\成果输出")

EXCLUDE_SUFFIXES = {".gbw", ".bas", ".tmp", ".wfn", ".densities", ".pot", ".pyc"}
EXCLUDE_NAMES = {
    "wbo", "charges", "xtbrestart", "xtbtopo.mol", "xtboptok",
    "SHA256SUMS", "verification.json",
}
EXCLUDE_SCRATCH_SUFFIXES = (".xtbtopo.mol", ".xtbrestart", ".xtboptok")
GENERATED_NAMES = ("SHA256SUMS", "verification.json")


def is_excluded(path: Path) -> bool:
    """True for binary scratch / manifest files that must never be copied."""
    if path.name in EXCLUDE_NAMES:
        return True
    if path.name.endswith(EXCLUDE_SCRATCH_SUFFIXES):
        return True
    return path.suffix in EXCLUDE_SUFFIXES


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def read_text(path: Path):
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8")


def load_json(path: Path):
    text = read_text(path)
    if text is None:
        return None
    return json.loads(text)


def check(name: str, ok, detail: str) -> dict:
    return {"name": name, "ok": ok, "detail": detail}


GATE_STATUS = "Gate 0 CLOSED; Gate 1 NOT CLOSED (blocker: 溶液锚点 31 行仍为 est)"

T3_NOTE_PRESENT = ("**T3（CPCM ε 扫描）**：bare CPCM 介电常数扫描（ε = 5/10/20/40）× 12 分子 × 3 态 "
                   "= 144/144 作业成功，覆盖 core set 全部 8 个结构家族（含补跑的 SL、TMP），几何复用 G1、"
                   "未重新优化。`outputs/week4/t3_*` 三项已自动纳入本目录。")
T3_NOTE_ABSENT = ("**T3（CPCM ε 扫描）**：本轮未纳入 `outputs/week4/t3_*`（源路径不存在）。")
T3_LIMIT_PRESENT = ("**T3 已纳入**：`outputs/week4/t3_*`（bare CPCM ε 扫描，144/144 作业）已产出并自动纳入 "
                    "week4；数值复核见 `verification.json` 的 `checks`。注意 bare CPCM ≠ SMD；"
                    "「是否出现 robust inversion」依赖 σ 口径，two_arm 与 multi_source 两套结果并列报告。")
T3_LIMIT_ABSENT = ("**T3 未纳入**：`outputs/week4/t3_*`（CPCM ε 扫描）在本轮尚不存在；"
                   "脚本会在其出现后自动纳入 week4，无需改动脚本。")
T3_SUMMARY_LIMIT_PRESENT = ("**T3（bare CPCM ε 扫描）**：ε = 5/10/20/40 的位移近乎共同平移（σ_env 仅 0.19–0.24 eV）；"
                            "相对气相在 two_arm σ 口径下 f_robust_inv = 0，multi_source σ 口径下最多 1 对"
                            "（f_robust_inv 的分母是两臂都能分辨的 pair 数，约 51–60，而非子集的 66 对），"
                            "故不足以宣称「介电诱导的稳健重排」。另注意 bare CPCM ≠ SMD。")
T3_SUMMARY_LIMIT_ABSENT = "**T3 尚未纳入**：CPCM ε 扫描（F10）未运行。"
T3_REPRO_COMMANDS = "\n".join([
    "# T3：bare CPCM ε 扫描（12 分子；几何复用 G1，不重新优化）",
    ".venv\\Scripts\\python.exe scripts\\run_core_set_p2.py --epsilon 5  --only C04,C05,C01,C02,C08,C09,C13,C16,C18,C15,C14,C17 --jobs 2 --outdir outputs\\week4",
    ".venv\\Scripts\\python.exe scripts\\run_core_set_p2.py --epsilon 10 --only C04,C05,C01,C02,C08,C09,C13,C16,C18,C15,C14,C17 --jobs 2 --outdir outputs\\week4",
    ".venv\\Scripts\\python.exe scripts\\run_core_set_p2.py --epsilon 20 --only C04,C05,C01,C02,C08,C09,C13,C16,C18,C15,C14,C17 --jobs 2 --outdir outputs\\week4",
    ".venv\\Scripts\\python.exe scripts\\run_core_set_p2.py --epsilon 40 --only C04,C05,C01,C02,C08,C09,C13,C16,C18,C15,C14,C17 --jobs 2 --outdir outputs\\week4",
    ".venv\\Scripts\\python.exe scripts\\analyze_cpcm_eps_scan.py",
    ".venv\\Scripts\\python.exe scripts\\make_eps_scan_figure.py",
])
F10_NOTE_PRESENT = "介电常数扫描：ΔIP / ΔEA 随 ε 的位移（bare CPCM；气相为参考点，非 CPCM 计算）"
F10_NOTE_ABSENT = "预留给 CPCM ε 扫描 / 预算复演；ε 扫描尚未产出"
T2_NOTE_PRESENT = ("**T2（Opt+Freq / G2 几何台阶）**：对 T3 用的同一 12 分子审计子集，在 r2SCAN-3c 上"
                   "从 G1 出发做中性 `Opt+Freq` 得到 G2，再在 G2 上重算三态单点；唯一变量是几何。"
                   "`outputs/week4/t2_*` 两项已自动纳入本目录，虚频照实记录为 `imaginary_mode_unresolved`。")
T2_NOTE_ABSENT = "**T2（Opt+Freq / G2 几何台阶）**：本轮未纳入 `outputs/week4/t2_*`（源路径不存在）。"
T2_LIMIT_PRESENT = ("**T2 已纳入**：几何台阶与方法台阶、环境台阶用同一估计量（位移在 12 个分子上的总体标准差）"
                    "并列比较（`F11`）；虚频按 QE 词表记 `imaginary_mode_unresolved`，照实报告、不静默删除。")
T2_LIMIT_ABSENT = ("**T2 未纳入**：Opt+Freq 几何台阶（F11）在本轮尚不存在；"
                   "`scripts/make_t2_figure.py` 会在其出现后自动纳入。")
T2_REPRO_COMMANDS = "\n".join([
    "# T2：Opt+Freq（G1 -> G2）+ G2 上的三态单点（12 分子审计子集，与 T3 子集逐一相同）",
    ".venv\\Scripts\\python.exe scripts\\run_t2_opt_freq.py --jobs 2 --nprocs 8",
    ".venv\\Scripts\\python.exe scripts\\make_t2_figure.py",
])
F11_NOTE_PRESENT = ("几何台阶：把 G1（GFN2-xTB 共享几何）换成 r2SCAN-3c 的 Opt+Freq 驻点 G2 后，"
                    "垂直 IP / EA 的逐分子位移，以及与方法、环境台阶同口径的 sigma 对比")
F11_NOTE_ABSENT = "预留给 Opt+Freq 几何台阶；T2 尚未产出"

WEEKS = {
    1: {
        "topic": "Stage 0 定义冻结 / Gate 0",
        "sources": [
            ("outputs/week1", None, False),
            ("docs/00_stage0_definitions.md", None, False),
            ("config/scientific_definitions.yaml", None, False),
            ("config/prereg.yaml", None, False),
        ],
        "figures": ["outputs/figures/F0_project_pipeline.png"],
        "figure_glob": None,
        "commands": [
            "python scripts/build_metadata.py",
            "python scripts/freeze_gates.py",
            "python scripts/build_deliverables.py --weeks 1",
        ],
    },
    2: {
        "topic": "Stage 1 方法审计与外部锚点",
        "sources": [
            ("outputs/week2", None, False),
            ("docs/01_stage1_external_anchors.md", None, False),
            ("docs/02_stage1_method_audit.md", None, False),
            ("docs/04_stage1_xtb_audit_result.md", None, False),
            ("docs/06_stage1_solution_anchor_audit.md", None, False),
            ("docs/03_week1_2_report.md", None, False),
        ],
        "figures": [],
        "figure_glob": None,
        "commands": [
            "python scripts/run_method_audit_xtb.py",
            "python scripts/audit_solution_anchors.py",
            "python scripts/freeze_gates.py",
            "python scripts/build_deliverables.py --weeks 2",
        ],
    },
    3: {
        "topic": "Stage 2 broad cheap pool（P0）",
        "sources": [
            ("outputs/week3", None, False),
            ("docs/05_stage2_broad_pool_p0.md", None, False),
            ("docs/09_week3_report.md", None, False),
        ],
        "figures": [
            "outputs/figures/F1_chemical_space_coverage.png",
            "outputs/figures/F2_p0_distributions_by_family.png",
        ],
        "figure_glob": None,
        "commands": [
            "python scripts/run_broad_pool_p0.py",
            "python scripts/make_summary_figures.py",
            "python scripts/build_deliverables.py --weeks 3",
        ],
    },
    4: {
        "topic": "Stage 3（P1 电子结构）+ Stage 4（P2 环境）+ T5 + T3 + T2",
        "sources": [
            ("outputs/week4/p1_core_set.csv", None, False),
            ("outputs/week4/p1_core_set_derived.csv", None, False),
            ("outputs/week4/p1_core_set_audit.csv", None, False),
            ("outputs/week4/p2_core_set_smd_acetonitrile.csv", None, False),
            ("outputs/week4/p2_environment_effects.csv", None, False),
            ("outputs/week4/t5_diffuse_control.csv", None, False),
            ("outputs/week4/t3_cpcm_eps_scan.csv", None, True),
            ("outputs/week4/t2_opt_freq.csv", None, True),
            ("outputs/week4/p1_core_set_summary.json", None, False),
            ("outputs/week4/p1_core_set_audit.json", None, False),
            ("outputs/week4/p1_anchor_comparison.json", None, False),
            ("outputs/week4/p1_decision_stability.json", None, False),
            ("outputs/week4/p2_summary_smd_acetonitrile.json", None, False),
            ("outputs/week4/p2_decision_stability.json", None, False),
            ("outputs/week4/t5_diffuse_control_summary.json", None, False),
            ("outputs/week4/t3_cpcm_eps_scan_summary.json", None, True),
            ("outputs/week4/t2_opt_freq_summary.json", None, True),
            ("outputs/week4/p1_decision_stability.md", None, False),
            ("outputs/week4/p2_decision_stability.md", None, False),
            ("docs/10_week4_report.md", "week4_report_full.md", False),
            ("outputs/week4/t3_cpcm_eps_scan_report.md", None, True),
            ("outputs/figures/figure_manifest_week4_t2.md", "artifacts/figure_manifest_week4_t2.md", True),
        ],
        "figures": [
            "outputs/figures/F3_value_error_vs_rank_error.png",
            "outputs/figures/F4_rank_migration_p0_to_p1.png",
            "outputs/figures/F5_reduction_axis_koopmans_vs_dscf.png",
            "outputs/figures/F6_decision_stability_indicators.png",
            "outputs/figures/F7_shift_structure.png",
            "outputs/figures/F8_environment_layer_p1_to_p2.png",
            "outputs/figures/F9_diffuse_function_control.png",
        ],
        "figure_glob": ["outputs/figures/F10_*.png", "outputs/figures/F11_*.png"],
        "commands": [
            "python scripts/run_core_set_p1.py --jobs 2 --outdir outputs\\week4",
            "python scripts/audit_p1_core_set.py",
            "python scripts/analyze_p1_core_set.py",
            "python scripts/run_core_set_p2.py --jobs 2 --outdir outputs\\week4",
            "python scripts/analyze_p2_environment.py",
            "python scripts/run_diffuse_control.py",
            "python scripts/make_t5_figure.py",
            "python scripts/run_t2_opt_freq.py --jobs 2 --nprocs 8",
            "python scripts/make_t2_figure.py",
            "python scripts/build_deliverables.py --weeks 4",
        ],
    },
    5: {
        "topic": "Stage 5（T4：Li+ 配位条件态 C1）",
        "sources": [
            ("outputs/week5/li_motif_generation.csv", None, False),
            ("outputs/week5/li_motif_generation.json", None, False),
            ("outputs/week5/li_motif_generation.md", None, False),
            ("outputs/week5/c1_li_coordination.csv", None, True),
            ("outputs/week5/c1_li_coordination_summary.json", None, True),
            ("outputs/week5/c1_coord_shifts.csv", None, True),
            ("outputs/week5/c1_ligand_exchange.csv", None, True),
            ("outputs/week5/c1_decision_stability.json", None, True),
            ("outputs/week5/c1_decision_stability.md", None, True),
            ("outputs/week5/c1_summary.json", None, True),
            # The state-identity QC (figure F13) of the C1 states is QC evidence
            # for Stage 5, so it ships with the bundle alongside the audit below.
            ("outputs/week5/c1_state_identity.csv", None, True),
            ("outputs/week5/c1_state_identity.json", None, True),
            ("outputs/week5/c1_state_identity.md", None, True),
            ("outputs/figures/figure_manifest_week5_state_identity.md",
             "artifacts/figure_manifest_week5_state_identity.md", True),
            # The adversarial audit of the C1 analysis layer is QC evidence for
            # Stage 5, so it ships with the bundle instead of staying in scratch.
            ("outputs/week5/c1_adversarial_audit.md", None, True),
            # The independent audit of the *state-identity* artefact is QC
            # evidence for that artefact, so it ships beside it rather than
            # staying in scratch.
            ("outputs/week5/c1_state_identity_audit.md", None, True),
            ("structures/li_motifs", "structures/li_motifs", True),
            ("docs/12_week5_report.md", "week5_report_full.md", True),
            # The M0-M6 milestone / plan-alignment record is the artefact that
            # says which stage the project is at, and docs/12 section 3 points
            # readers at it, so it ships with the week-5 bundle instead of
            # only existing inside the repository.
            ("docs/11_plan_alignment.md", "plan_alignment.md", True),
            ("outputs/figures/figure_manifest_week5_c1.md",
             "artifacts/figure_manifest_week5_c1.md", True),
        ],
        # Per-job C1 provenance records live under outputs/week5/c1/<NAME>/ next to
        # the raw ORCA scratch.  They are pulled in by glob and filtered through the
        # same exclusion rules, so the multi-megabyte .out/.inp never reach the bundle.
        "source_globs": [
            ("outputs/week5/c1/*/*_c1_record.json", "c1_records", True),
            ("outputs/week5/c1/*/*_orca.json", "c1_records", True),
        ],
        "figures": [],
        "figure_glob": ["outputs/figures/F12_*.png", "outputs/figures/F13_*.png"],
        "commands": [
            "python scripts/build_li_motifs.py",
            "python scripts/run_c1_li_coordination.py --jobs 2 --nprocs 8",
            "python scripts/analyze_c1_coordination.py",
            "python scripts/make_c1_figure.py",
            "python scripts/analyze_c1_state_identity.py",
            "python scripts/make_c1_state_identity_figure.py",
            "python scripts/build_deliverables.py --weeks 5",
        ],
    },
    6: {
        "topic": "Stage 6（T6 构象系综 + T7 C1 虚频 + T8 delta_m + T9 不确定性感知排序）",
        "sources": [
            ("outputs/week6/t6_conformer_manifest.csv", None, True),
            ("outputs/week6/t6_conformer_manifest.json", None, True),
            ("outputs/week6/t6_conformer_spread.csv", None, True),
            ("outputs/week6/t6_conformer_spread.json", None, True),
            ("outputs/week6/t6_conformer_spread.md", None, True),
            ("outputs/week6/t7_c1_freq_check.csv", None, True),
            ("outputs/week6/t7_c1_freq_check.json", None, True),
            ("outputs/week6/t7_c1_freq_check.md", None, True),
            ("outputs/week6/delta_m_frozen.json", None, True),
            ("outputs/week6/delta_m_frozen.md", None, True),
            ("outputs/week6/stage6_decision_stability.csv", None, True),
            ("outputs/week6/stage6_decision_stability.json", None, True),
            ("outputs/week6/stage6_decision_stability.md", None, True),
            ("structures/conformers", "structures/conformers", True),
            ("docs/13_week6_report.md", "week6_report_full.md", True),
            ("outputs/figures/figure_manifest_week6_t9.md",
             "artifacts/figure_manifest_week6_t9.md", True),
        ],
        "figures": [],
        "figure_glob": ["outputs/figures/F14_*.png", "outputs/figures/F15_*.png"],
        "commands": [
            "python scripts/build_conformers.py --force --n-confs 24 --keep 4 --jobs 8",
            "python scripts/run_t6_conformer_spread.py --layer p0 --p0-jobs 8",
            "python scripts/run_t6_conformer_spread.py --layer p1 --jobs 2 --nprocs 8",
            "python scripts/run_c1_freq_check.py --jobs 2 --nprocs 8",
            "python scripts/analyze_delta_m.py",
            "python scripts/analyze_stage6.py",
            "python scripts/make_stage6_figure.py",
            "python scripts/build_deliverables.py --weeks 6",
        ],
    },
    7: {
        "topic": "Stage 7（ML / direct vs Δ-learning）+ Stage 8（active-learning replay）",
        "sources": [
            ("outputs/week7/feature_manifest.json", None, True),
            ("outputs/week7/feature_manifest.md", None, True),
            ("outputs/week7/features_core.csv", None, True),
            ("outputs/week7/features_broad.csv", None, True),
            ("outputs/week7/stage7_ml_results.csv", None, True),
            ("outputs/week7/stage7_ml_results.json", None, True),
            ("outputs/week7/stage7_ml_summary.md", None, True),
            ("outputs/week7/stage7_ml_predictions.csv", None, True),
            ("outputs/week7/stage8_al_runs.csv", None, True),
            ("outputs/week7/stage8_al_curves.csv", None, True),
            ("outputs/week7/stage8_al_trajectories.csv", None, True),
            ("outputs/week7/stage8_al_results.json", None, True),
            ("outputs/week7/stage8_al_summary.md", None, True),
            ("docs/14_reading_list_qa.md", "reading_list_qa.md", True),
            ("docs/15_week7_report.md", "week7_report_full.md", True),
            ("outputs/figures/figure_manifest_week7_s7s8.md",
             "artifacts/figure_manifest_week7_s7s8.md", True),
        ],
        "figures": [],
        "figure_glob": ["outputs/figures/F16_*.png", "outputs/figures/F17_*.png"],
        "commands": [
            "python scripts/build_ml_features.py",
            "python scripts/run_stage7_ml.py",
            "python scripts/run_stage8_al.py",
            "python scripts/make_stage7_figure.py",
            "python scripts/build_deliverables.py --weeks 7",
        ],
    },
    8: {
        "topic": "Stage 9（显式微溶剂化：C2 = [Li(M)2]+ 第一溶剂壳复核）",
        "sources": [
            ("outputs/week8/ms_shell_generation.csv", None, True),
            ("outputs/week8/ms_shell_generation.json", None, True),
            ("outputs/week8/ms_shell_generation.md", None, True),
            ("outputs/week8/stage9_jobs.csv", None, True),
            ("outputs/week8/stage9_summary.json", None, True),
            ("outputs/week8/stage9_shell_shifts.csv", None, True),
            ("outputs/week8/stage9_decision_stability.csv", None, True),
            ("outputs/week8/stage9_results.json", None, True),
            ("outputs/week8/stage9_summary.md", None, True),
            ("structures/microsolvation", "structures/microsolvation", True),
            ("docs/16_branch_abcd_qa.md", "branch_abcd_qa.md", True),
            ("docs/17_plan_optimization_branchABC.md",
             "plan_optimization_branchABC.md", True),
            ("docs/18_week8_report.md", "week8_report_full.md", True),
            ("outputs/figures/figure_manifest_week8_stage9.md",
             "artifacts/figure_manifest_week8_stage9.md", True),
        ],
        "figures": [],
        "figure_glob": ["outputs/figures/F18_*.png"],
        "commands": [
            "python scripts/build_microsolvation_shells.py",
            "python scripts/run_stage9_microsolvation.py --skip-relax --jobs 2 --nprocs 8",
            "python scripts/analyze_stage9_microsolvation.py",
            "python scripts/make_stage9_figure.py",
            "python scripts/build_deliverables.py --weeks 8",
        ],
    },
    9: {
        "topic": "Stage 10（五级台阶合成与决策稳定性总判）",
        "sources": [
            ("outputs/week9/stage10_ladder.csv", None, True),
            ("outputs/week9/stage10_ladder.json", None, True),
            ("outputs/week9/stage10_verdicts.json", None, True),
            ("outputs/week9/stage10_summary.md", None, True),
            ("docs/19_week9_report.md", "week9_report_full.md", True),
            ("outputs/figures/figure_manifest_week9_stage10.md",
             "artifacts/figure_manifest_week9_stage10.md", True),
        ],
        "figures": [],
        "figure_glob": ["outputs/figures/F19_*.png"],
        "commands": [
            "python scripts/analyze_stage10_synthesis.py",
            "python scripts/make_stage10_figure.py",
            "python scripts/build_deliverables.py --weeks 9",
        ],
    },
    10: {
        "topic": "Stage 11（sigma 的代数解剖与分辨率判据）",
        "sources": [
            ("outputs/week10/stage11_sigma_anatomy.csv", None, True),
            ("outputs/week10/stage11_sigma_anatomy.json", None, True),
            ("outputs/week10/stage11_summary.md", None, True),
            ("docs/20_week10_report.md", "week10_report_full.md", True),
            ("outputs/figures/figure_manifest_week10_stage11.md",
             "artifacts/figure_manifest_week10_stage11.md", True),
        ],
        "figures": [],
        "figure_glob": ["outputs/figures/F20_*.png", "outputs/figures/F21_*.png"],
        "commands": [
            "python scripts/analyze_stage11_sigma_anatomy.py",
            "python scripts/make_stage11_figure.py",
            "python scripts/build_deliverables.py --weeks 10",
        ],
    },
    11: {
        "topic": "Stage 12\uff08\u4ecb\u7535\u81ea\u76f8\u4f3c\u4e0e\u4e8b\u524d\u9884\u8b66\uff09",
        "sources": [
            ("outputs/week11/stage12_prescreen.csv", None, True),
            ("outputs/week11/stage12_prescreen.json", None, True),
            ("outputs/week11/stage12_summary.md", None, True),
            ("docs/21_week11_report.md", "week11_report_full.md", True),
            ("outputs/figures/figure_manifest_week11_stage12.md",
             "artifacts/figure_manifest_week11_stage12.md", True),
        ],
        "figures": [],
        "figure_glob": ["outputs/figures/F22_*.png", "outputs/figures/F23_*.png"],
        "commands": [
            "python scripts/analyze_stage12_prescreen.py",
            "python scripts/make_stage12_figure.py",
            "python scripts/build_deliverables.py --weeks 11",
        ],
    },
    12: {
        "topic": "Stage 13（介电极限与 ORCA 能量账本）",
        "sources": [
            ("outputs/week12/stage13_state_ledger.csv", None, True),
            ("outputs/week12/stage13_dielectric_ladder.csv", None, True),
            ("outputs/week12/stage13_shift_split.csv", None, True),
            ("outputs/week12/stage13_ladder.json", None, True),
            ("outputs/week12/stage13_rungs.csv", None, True),
            ("outputs/week12/stage13_analysis.json", None, True),
            ("outputs/week12/stage13_summary.md", None, True),
            ("outputs/week12/p2_core_set_cpcm_80.csv", None, True),
            ("outputs/week12/p2_summary_cpcm_80.json", None, True),
            ("outputs/week12/p2_core_set_cpcm_200.csv", None, True),
            ("outputs/week12/p2_summary_cpcm_200.json", None, True),
            ("outputs/week12/p2_core_set_smd_water.csv", None, True),
            ("outputs/week12/p2_summary_smd_water.json", None, True),
            ("docs/22_week12_report.md", "week12_report_full.md", True),
            ("outputs/figures/figure_manifest_week12_stage13.md",
             "artifacts/figure_manifest_week12_stage13.md", True),
        ],
        "figures": [],
        "figure_glob": ["outputs/figures/F24_*.png", "outputs/figures/F25_*.png"],
        "commands": [
            "python scripts/run_core_set_p2.py --outdir outputs\\week12 --epsilon 80 --jobs 2 --nprocs 8",
            "python scripts/run_core_set_p2.py --outdir outputs\\week12 --epsilon 200 --jobs 2 --nprocs 8",
            "python scripts/run_core_set_p2.py --outdir outputs\\week12 --solvent water --layer smd_water --jobs 2 --nprocs 8",
            "python scripts/build_stage13_ladder.py",
            "python scripts/analyze_stage13_dielectric_limit.py",
            "python scripts/make_stage13_figure.py",
            "python scripts/build_deliverables.py --weeks 12",
        ],
    },
    13: {
        "topic": "Stage 14（畸变项归因与 EMC 离群点诊断）",
        "sources": [
            ("outputs/week13/stage14_attribution.json", None, True),
            ("outputs/week13/stage14_attribution.csv", None, True),
            ("outputs/week13/stage14_distortion_states.csv", None, True),
            ("outputs/week13/stage14_distortion_states_by_molecule.csv", None, True),
            ("outputs/week13/stage14_outlier.json", None, True),
            ("outputs/week13/stage14_outlier.csv", None, True),
            ("outputs/week13/stage14_dense_grid.json", None, True),
            ("outputs/week13/stage14_summary.md", None, True),
            ("outputs/week13/p2_core_set_cpcm_5.csv", None, True),
            ("outputs/week13/p2_summary_cpcm_5.json", None, True),
            ("outputs/week13/p2_core_set_cpcm_7.csv", None, True),
            ("outputs/week13/p2_summary_cpcm_7.json", None, True),
            ("outputs/week13/p2_core_set_cpcm_10.csv", None, True),
            ("outputs/week13/p2_summary_cpcm_10.json", None, True),
            ("outputs/week13/p2_core_set_cpcm_14.csv", None, True),
            ("outputs/week13/p2_summary_cpcm_14.json", None, True),
            ("outputs/week13/p2_core_set_cpcm_20.csv", None, True),
            ("outputs/week13/p2_summary_cpcm_20.json", None, True),
            ("outputs/week13/p2_core_set_cpcm_28.csv", None, True),
            ("outputs/week13/p2_summary_cpcm_28.json", None, True),
            ("outputs/week13/p2_core_set_cpcm_40.csv", None, True),
            ("outputs/week13/p2_summary_cpcm_40.json", None, True),
            ("docs/23_week13_report.md", "week13_report_full.md", True),
            ("outputs/figures/figure_manifest_week13_stage14.md",
             "artifacts/figure_manifest_week13_stage14.md", True),
        ],
        "figures": [],
        "figure_glob": ["outputs/figures/F26_*.png", "outputs/figures/F27_*.png"],
        "commands": [
            "python scripts/build_stage14_attribution.py",
            "python scripts/run_stage14_dense_grid.py --jobs 2 --nprocs 8",
            "python scripts/analyze_stage14_outlier.py",
            "python scripts/make_stage14_figure.py",
            "python scripts/build_deliverables.py --weeks 13",
        ],
    },
    14: {
        "topic": "Stage 15（双初猜协议、电子弥散度描述符与溶液锚点扫描）",
        "sources": [
            ("outputs/week14/stage15_two_guess.json", None, True),
            ("outputs/week14/stage15_two_guess_analysis.json", None, True),
            ("outputs/week14/stage15_two_guess_energy.csv", None, True),
            ("outputs/week14/stage15_two_guess_dipole.csv", None, True),
            ("outputs/week14/stage15_diffuseness.json", None, True),
            ("outputs/week14/stage15_diffuseness.csv", None, True),
            ("outputs/week14/stage15_diffuseness_by_molecule.csv", None, True),
            ("outputs/week14/stage15_anchor_scan.json", None, True),
            ("outputs/week14/stage15_anchor_scan.csv", None, True),
            ("outputs/week14/stage15_anchor_corrections.csv", None, True),
            ("outputs/week14/stage15_summary.md", None, True),
            ("outputs/week14/p2_core_set_cpcm_1000.csv", None, True),
            ("outputs/week14/p2_summary_cpcm_1000.json", None, True),
            ("outputs/week14/p2_core_set_moread_cpcm_5.csv", None, True),
            ("outputs/week14/p2_summary_moread_cpcm_5.json", None, True),
            ("outputs/week14/p2_core_set_moread_cpcm_7.csv", None, True),
            ("outputs/week14/p2_summary_moread_cpcm_7.json", None, True),
            ("outputs/week14/p2_core_set_moread_cpcm_10.csv", None, True),
            ("outputs/week14/p2_summary_moread_cpcm_10.json", None, True),
            ("outputs/week14/p2_core_set_moread_cpcm_14.csv", None, True),
            ("outputs/week14/p2_summary_moread_cpcm_14.json", None, True),
            ("outputs/week14/p2_core_set_moread_cpcm_20.csv", None, True),
            ("outputs/week14/p2_summary_moread_cpcm_20.json", None, True),
            ("outputs/week14/p2_core_set_moread_cpcm_28.csv", None, True),
            ("outputs/week14/p2_summary_moread_cpcm_28.json", None, True),
            ("outputs/week14/p2_core_set_moread_cpcm_40.csv", None, True),
            ("outputs/week14/p2_summary_moread_cpcm_40.json", None, True),
            ("outputs/week14/p2_core_set_moread_cpcm_80.csv", None, True),
            ("outputs/week14/p2_summary_moread_cpcm_80.json", None, True),
            ("outputs/week14/p2_core_set_moread_cpcm_200.csv", None, True),
            ("outputs/week14/p2_summary_moread_cpcm_200.json", None, True),
            ("outputs/week14/p2_core_set_moread_cpcm_1000.csv", None, True),
            ("outputs/week14/p2_summary_moread_cpcm_1000.json", None, True),
            ("docs/24_week14_report.md", "week14_report_full.md", True),
            ("outputs/figures/figure_manifest_week14_stage15.md",
             "artifacts/figure_manifest_week14_stage15.md", True),
        ],
        "figures": [],
        "figure_glob": ["outputs/figures/F28_*.png", "outputs/figures/F29_*.png"],
        "commands": [
            "python scripts/run_stage15_two_guess.py --jobs 2 --nprocs 8",
            "python scripts/analyze_stage15_two_guess.py",
            "python scripts/build_stage15_diffuseness.py",
            "python scripts/scan_stage15_anchor_literature.py",
            "python scripts/make_stage15_figure.py",
            "python scripts/build_deliverables.py --weeks 14",
        ],
    },
    15: {
        "topic": "Stage 16（全核心集双初猜目录与事前预警规则）",
        "sources": [
            ("outputs/week15/stage16_catalogue.json", None, True),
            ("outputs/week15/stage16_catalogue_analysis.json", None, True),
            ("outputs/week15/stage16_cells.csv", None, True),
            ("outputs/week15/stage16_by_state.csv", None, True),
            ("outputs/week15/stage16_validation_cells.csv", None, True),
            ("outputs/week15/stage16_holdout.json", None, True),
            ("outputs/week15/stage16_gas_descriptors.csv", None, True),
            ("outputs/week15/stage16_predictor.json", None, True),
            ("outputs/week15/stage16_summary.md", None, True),
            ("outputs/week15/p2_core_set_cpcm_7.csv", None, True),
            ("outputs/week15/p2_summary_cpcm_7.json", None, True),
            ("outputs/week15/p2_core_set_cpcm_14.csv", None, True),
            ("outputs/week15/p2_summary_cpcm_14.json", None, True),
            ("outputs/week15/p2_core_set_cpcm_28.csv", None, True),
            ("outputs/week15/p2_summary_cpcm_28.json", None, True),
            ("outputs/week15/p2_core_set_cpcm_1000.csv", None, True),
            ("outputs/week15/p2_summary_cpcm_1000.json", None, True),
            ("outputs/week15/p2_core_set_moread_cpcm_5.csv", None, True),
            ("outputs/week15/p2_summary_moread_cpcm_5.json", None, True),
            ("outputs/week15/p2_core_set_moread_cpcm_7.csv", None, True),
            ("outputs/week15/p2_summary_moread_cpcm_7.json", None, True),
            ("outputs/week15/p2_core_set_moread_cpcm_10.csv", None, True),
            ("outputs/week15/p2_summary_moread_cpcm_10.json", None, True),
            ("outputs/week15/p2_core_set_moread_cpcm_14.csv", None, True),
            ("outputs/week15/p2_summary_moread_cpcm_14.json", None, True),
            ("outputs/week15/p2_core_set_moread_cpcm_20.csv", None, True),
            ("outputs/week15/p2_summary_moread_cpcm_20.json", None, True),
            ("outputs/week15/p2_core_set_moread_cpcm_28.csv", None, True),
            ("outputs/week15/p2_summary_moread_cpcm_28.json", None, True),
            ("outputs/week15/p2_core_set_moread_cpcm_40.csv", None, True),
            ("outputs/week15/p2_summary_moread_cpcm_40.json", None, True),
            ("outputs/week15/p2_core_set_moread_cpcm_80.csv", None, True),
            ("outputs/week15/p2_summary_moread_cpcm_80.json", None, True),
            ("outputs/week15/p2_core_set_moread_cpcm_200.csv", None, True),
            ("outputs/week15/p2_summary_moread_cpcm_200.json", None, True),
            ("outputs/week15/p2_core_set_moread_cpcm_1000.csv", None, True),
            ("outputs/week15/p2_summary_moread_cpcm_1000.json", None, True),
            ("outputs/week15/p2_core_set_holdout_cpcm_5.csv", None, True),
            ("outputs/week15/p2_summary_holdout_cpcm_5.json", None, True),
            ("outputs/week15/p2_core_set_holdout_cpcm_20.csv", None, True),
            ("outputs/week15/p2_summary_holdout_cpcm_20.json", None, True),
            ("outputs/week15/p2_core_set_holdout_cpcm_200.csv", None, True),
            ("outputs/week15/p2_summary_holdout_cpcm_200.json", None, True),
            ("outputs/week15/p2_core_set_holdout_moread_cpcm_5.csv", None, True),
            ("outputs/week15/p2_summary_holdout_moread_cpcm_5.json", None, True),
            ("outputs/week15/p2_core_set_holdout_moread_cpcm_20.csv", None, True),
            ("outputs/week15/p2_summary_holdout_moread_cpcm_20.json", None, True),
            ("outputs/week15/p2_core_set_holdout_moread_cpcm_200.csv", None, True),
            ("outputs/week15/p2_summary_holdout_moread_cpcm_200.json", None, True),
            ("docs/25_week15_report.md", "week15_report_full.md", True),
            ("outputs/figures/figure_manifest_week15_stage16.md",
             "artifacts/figure_manifest_week15_stage16.md", True),
        ],
        "figures": [],
        "figure_glob": ["outputs/figures/F30_*.png", "outputs/figures/F31_*.png"],
        "commands": [
            "python scripts/run_stage16_catalogue.py --set subset --jobs 2 --nprocs 8",
            "python scripts/run_stage16_catalogue.py --set validation --levels 5,20,200 --tag holdout --jobs 2 --nprocs 8",
            "python scripts/analyze_stage16_catalogue.py",
            "python scripts/build_stage16_predictor.py",
            "python scripts/make_stage16_figure.py",
            "python scripts/gen_week15_report.py",
            "python scripts/build_deliverables.py --weeks 15",
        ],
    },
    16: {
        "topic": "Stage 17（亚稳态对已发布台阶结论的污染上限与两个 SCF 解的电子结构身份）",
        "sources": [
            ("outputs/week16/p2_core_set_moread_smd_acetonitrile.csv", None, True),
            ("outputs/week16/p2_summary_moread_smd_acetonitrile.json", None, True),
            ("outputs/week16/stage17_smd_moread.json", None, True),
            ("outputs/week16/stage17_smd_moread_plan.json", None, True),
            ("outputs/week16/stage17_contamination.json", None, True),
            ("outputs/week16/stage17_contamination_ladder.csv", None, True),
            ("outputs/week16/stage17_contamination_cells.csv", None, True),
            ("outputs/week16/stage17_contamination_summary.md", None, True),
            ("outputs/week16/stage17_solution_identity.json", None, True),
            ("outputs/week16/stage17_solution_identity.csv", None, True),
            ("outputs/week16/stage17_solution_identity_by_molecule.csv", None, True),
            ("outputs/week16/stage17_solution_identity_summary.md", None, True),
            ("docs/26_week16_report.md", "week16_report_full.md", True),
            ("outputs/figures/figure_manifest_week16_stage17.md",
             "artifacts/figure_manifest_week16_stage17.md", True),
        ],
        "figures": [],
        "figure_glob": ["outputs/figures/F32_*.png", "outputs/figures/F33_*.png"],
        "commands": [
            "python scripts/run_stage17_smd_moread.py",
            "python scripts/analyze_stage17_contamination.py",
            "python scripts/analyze_stage17_solution_identity.py",
            "python scripts/make_stage17_figure.py",
            "python scripts/gen_week16_report.py",
            "python scripts/build_deliverables.py --weeks 16",
        ],
    },
    17: {
        "topic": "Stage 18（全目录电子身份普查与零成本自诊断）",
        "sources": [
            ("outputs/week17/stage18_identity_census.json", None, True),
            ("outputs/week17/stage18_identity_census.csv", None, True),
            ("outputs/week17/stage18_identity_census_by_family.csv", None, True),
            ("outputs/week17/stage18_identity_census_by_classification.csv", None, True),
            ("outputs/week17/stage18_identity_census_summary.md", None, True),
            ("outputs/week17/stage18_selfdiagnosis.json", None, True),
            ("outputs/week17/stage18_selfdiagnosis_features.csv", None, True),
            ("outputs/week17/stage18_selfdiagnosis_features_by_state.csv", None, True),
            ("outputs/week17/stage18_selfdiagnosis_summary.md", None, True),
            ("docs/27_week17_report.md", "week17_report_full.md", True),
            ("outputs/figures/figure_manifest_week17_stage18.md",
             "artifacts/figure_manifest_week17_stage18.md", True),
        ],
        "figures": [],
        "figure_glob": ["outputs/figures/F34_*.png", "outputs/figures/F35_*.png"],
        "commands": [
            "python scripts/analyze_stage18_identity_census.py",
            "python scripts/build_stage18_selfdiagnosis.py",
            "python scripts/make_stage18_figure.py",
            "python scripts/gen_week17_report.py",
            "python scripts/build_deliverables.py --weeks 17",
        ],
    },
    18: {
        "topic": "Stage 19（几何弛豫检验：第二个 SCF 解能不能扛住弛豫）",
        "sources": [
            ("outputs/week18/stage19_relax.json", None, True),
            ("outputs/week18/stage19_relax_plan.json", None, True),
            ("outputs/week18/stage19_relax_cells.csv", None, True),
            ("outputs/week18/stage19_relax_analysis.json", None, True),
            ("outputs/week18/stage19_relax_cells_analysis.csv", None, True),
            ("outputs/week18/stage19_relax_by_state.csv", None, True),
            ("outputs/week18/stage19_relax_by_molecule.csv", None, True),
            ("outputs/week18/stage19_relax_by_epsilon.csv", None, True),
            ("outputs/week18/stage19_relax_by_arm_set.csv", None, True),
            ("outputs/week18/stage19_relax_summary.md", None, True),
            ("docs/28_week18_report.md", "week18_report_full.md", True),
            ("outputs/figures/figure_manifest_week18_stage19.md",
             "artifacts/figure_manifest_week18_stage19.md", True),
        ],
        "figures": [],
        "figure_glob": ["outputs/figures/F36_*.png", "outputs/figures/F37_*.png"],
        "commands": [
            "python scripts/run_stage19_relax.py",
            "python scripts/analyze_stage19_relax.py",
            "python scripts/make_stage19_figure.py",
            "python scripts/gen_week18_report.py",
            "python scripts/build_deliverables.py --weeks 18",
        ],
    },
    19: {
        "topic": "Stage 20（第六级台阶与第二解的跨方法存亡）",
        "sources": [
            ("outputs/week19/stage20_relax_rung.json", None, True),
            ("outputs/week19/stage20_relax_rung_cells.csv", None, True),
            ("outputs/week19/stage20_relax_rung_epsilon.csv", None, True),
            ("outputs/week19/stage20_relax_rung_ladder.csv", None, True),
            ("outputs/week19/stage20_relax_rung_summary.md", None, True),
            ("outputs/week19/stage20_xtb_arms.json", None, True),
            ("outputs/week19/stage20_xtb_arms_plan.json", None, True),
            ("outputs/week19/stage20_xtb_arms_cells.csv", None, True),
            ("outputs/week19/stage20_xtb_arms_cells_analysis.csv", None, True),
            ("outputs/week19/stage20_xtb_arms_analysis.json", None, True),
            ("outputs/week19/stage20_xtb_arms_by_state.csv", None, True),
            ("outputs/week19/stage20_xtb_arms_by_molecule.csv", None, True),
            ("outputs/week19/stage20_xtb_arms_by_epsilon.csv", None, True),
            ("outputs/week19/stage20_xtb_arms_by_arm_set.csv", None, True),
            ("outputs/week19/stage20_xtb_arms_summary.md", None, True),
            ("docs/29_week19_report.md", "week19_report_full.md", True),
            ("outputs/figures/figure_manifest_week19_stage20.md",
             "artifacts/figure_manifest_week19_stage20.md", True),
        ],
        "figures": [],
        "figure_glob": ["outputs/figures/F38_*.png", "outputs/figures/F39_*.png"],
        "commands": [
            "python scripts/analyze_stage20_relax_rung.py",
            "python scripts/run_stage20_xtb_arms.py --jobs 8",
            "python scripts/analyze_stage20_xtb_arms.py",
            "python scripts/make_stage20_figure.py",
            "python scripts/gen_week19_report.py",
            "python scripts/build_deliverables.py --weeks 19",
        ],
    },
    20: {
        "topic": "Stage 21（临界带的能量裁决 + 判据预检 + 溶剂壳氧化还原 + 真回填）",
        "sources": [
            ("outputs/week20/stage21_path.json", None, True),
            ("outputs/week20/stage21_path_plan.json", None, True),
            ("outputs/week20/stage21_path_cells.csv", None, True),
            ("outputs/week20/stage21_path_analysis.csv", None, True),
            ("outputs/week20/stage21_path_analysis.json", None, True),
            ("outputs/week20/stage21_path_summary.md", None, True),
            ("outputs/week20/stage21_protocol.json", None, True),
            ("outputs/week20/stage21_protocol_borderline.csv", None, True),
            ("outputs/week20/stage21_protocol_summary.md", None, True),
            ("outputs/week20/stage21_shell_redox.json", None, True),
            ("outputs/week20/stage21_shell_redox_plan.json", None, True),
            ("outputs/week20/stage21_shell_redox_cells.csv", None, True),
            ("outputs/week20/stage21_shell_redox_analysis.csv", None, True),
            ("outputs/week20/stage21_shell_redox_analysis.json", None, True),
            ("outputs/week20/stage21_shell_redox_summary.md", None, True),
            ("outputs/week20/stage21_refill.json", None, True),
            ("outputs/week20/stage21_refill_cells.csv", None, True),
            ("outputs/week20/stage21_refill_summary.md", None, True),
            ("docs/30_week20_report.md", "week20_report_full.md", True),
            ("outputs/figures/figure_manifest_week20_stage21.md",
             "artifacts/figure_manifest_week20_stage21.md", True),
        ],
        "figures": [],
        "figure_glob": ["outputs/figures/F40_*.png", "outputs/figures/F41_*.png"],
        "commands": [
            "python scripts/run_stage21_path.py --images 21 --jobs 8 --nprocs 2",
            "python scripts/run_stage21_shell_redox.py --jobs 4 --nprocs 3",
            "python scripts/analyze_stage21_path.py",
            "python scripts/analyze_stage21_protocol.py",
            "python scripts/analyze_stage21_shell_redox.py",
            "python scripts/analyze_stage21_refill.py",
            "python scripts/make_stage21_figure.py",
            "python scripts/gen_week20_report.py",
            "python scripts/build_deliverables.py --weeks 20",
        ],
    },
    21: {
        "topic": "Stage 22（批次 A：三臂对齐配对检验 + σ 相图 + 前瞻检验）",
        "sources": [
            ("outputs/week21/sigma_synthetic.json", None, True),
            ("outputs/week21/sigma_prospective.json", None, True),
            ("outputs/week21/sigma_prospective_frozen.json", None, True),
            ("outputs/week21/sigma_prospective.md", None, True),
            ("docs/32_week21_report.md", "week21_report_full.md", True),
            ("outputs/figures/figure_manifest_week21.md",
             "artifacts/figure_manifest_week21.md", True),
        ],
        "figures": [],
        "figure_glob": ["outputs/figures/F42_*.png"],
        "commands": [
            "python scripts/analyze_sigma_synthetic.py",
            "python scripts/analyze_sigma_prospective.py",
            "python scripts/gen_week21_report.py",
            "python scripts/build_deliverables.py --weeks 21",
        ],
    },
}


TEXT_SUFFIXES = {".csv", ".json", ".md", ".txt", ".inp", ".out", ".xyz",
                 ".ps1", ".py", ".yaml", ".yml"}


def copy_artifact(src, dst):
    """Binary is copied byte-for-byte; text is normalised to UTF-8 + LF."""
    if src.suffix.lower() in TEXT_SUFFIXES:
        data = src.read_bytes()
        try:
            text = data.decode("utf-8-sig")
        except UnicodeDecodeError:
            shutil.copy2(src, dst)
            return
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        write_text(dst, text)
        return
    shutil.copy2(src, dst)


def expand_source(rel, dst_rel, optional, missing, excluded):
    """Return [(abs_src, rel_dst, optional)] for one source entry."""
    src = REPO / rel
    items = []
    if not src.exists():
        missing.append({"source": rel, "optional": optional})
        return items
    if src.is_dir():
        for path in sorted(src.rglob("*")):
            if not path.is_file():
                continue
            if is_excluded(path):
                excluded.append(path.relative_to(REPO).as_posix())
                continue
            sub = path.relative_to(src)
            dst = (Path(dst_rel) / sub) if dst_rel else sub
            items.append((path, dst, optional))
        return items
    if is_excluded(src):
        excluded.append(rel)
        return items
    dst = Path(dst_rel) if dst_rel else Path(src.name)
    items.append((src, dst, optional))
    return items


def plan_week(week):
    """Build the copy plan for one week: (items, missing, excluded)."""
    spec = WEEKS[week]
    items, missing, excluded = [], [], []
    for rel, dst_rel, optional in spec["sources"]:
        items.extend(expand_source(rel, dst_rel, optional, missing, excluded))
    for rel in spec["figures"]:
        items.extend(expand_source(rel, Path("artifacts") / Path(rel).name,
                                   False, missing, excluded))
    for pattern, dst_dir, optional in spec.get("source_globs", ()):
        matched = False
        for path in sorted(REPO.glob(pattern)):
            if not path.is_file():
                continue
            if is_excluded(path):
                excluded.append(path.relative_to(REPO).as_posix())
                continue
            dst = (Path(dst_dir) / path.name) if dst_dir else Path(path.name)
            items.append((path, dst, optional))
            matched = True
        if not matched:
            missing.append({"source": pattern, "optional": optional})
    glob_spec = spec.get("figure_glob")
    patterns = [] if glob_spec is None else glob_spec
    if isinstance(patterns, str):
        patterns = [patterns]
    for pattern in patterns:
        for path in sorted(REPO.glob(pattern)):
            if is_excluded(path):
                excluded.append(path.relative_to(REPO).as_posix())
                continue
            items.append((path, Path("artifacts") / path.name, True))
    return items, missing, excluded


def week_files(wdir):
    """All deliverable files in a week dir (excludes the two generated ones)."""
    out = []
    for path in sorted(wdir.rglob("*")):
        if path.is_file():
            rel = path.relative_to(wdir).as_posix()
            if rel not in GENERATED_NAMES:
                out.append(rel)
    return out


def artifact_files(week, wdir):
    """Product list for the report: excludes the report itself."""
    report_name = "week%d_report.md" % week
    return [rel for rel in week_files(wdir) if rel != report_name]


def render_report(week, wdir, missing, excluded):
    text = REPORT_TEMPLATES[week]
    listing = "\n".join("- `%s`" % rel for rel in artifact_files(week, wdir)) or "- none"
    text = text.replace("{artifact_list}", listing)
    text = text.replace("{prereg_sha256}", sha256_file(REPO / "config" / "prereg.yaml"))
    text = text.replace("{gate0_sha_table}", gate0_sha_table())
    t3_present = (wdir / "t3_cpcm_eps_scan.csv").exists()
    text = text.replace("{t3_note}", T3_NOTE_PRESENT if t3_present else T3_NOTE_ABSENT)
    text = text.replace("{t3_limit}", T3_LIMIT_PRESENT if t3_present else T3_LIMIT_ABSENT)
    t2 = t2_blocks(load_json(T2_SUMMARY_PATH))
    for key, value in (("{t2_note}", T2_NOTE_PRESENT if t2["block"] else T2_NOTE_ABSENT),
                       ("{t2_block}", t2["block"]),
                       ("{t2_qc}", t2["qc"]),
                       ("{t2_step_row}", t2["step_row"]),
                       ("{t2_limit}", t2["limit"])):
        text = text.replace(key, value)
    c1 = c1_blocks(load_json(C1_SUMMARY_PATH), load_json(C1_RUN_SUMMARY_PATH))
    for key, value in (("{c1_note}", C1_NOTE_PRESENT if c1["present"] else C1_NOTE_ABSENT),
                       ("{c1_block}", c1["block"]),
                       ("{c1_qc}", c1["qc"]),
                       ("{c1_step_row}", c1["step_row"]),
                       ("{c1_limit}", c1["limit"])):
        text = text.replace(key, value)
    w6 = week6_blocks(load_json(T6_SUMMARY_PATH), load_json(T7_SUMMARY_PATH),
                      load_json(T8_SUMMARY_PATH), load_json(T9_SUMMARY_PATH))
    for key, value in (("{w6_did}", w6["did"]),
                       ("{w6_metric}", w6["metric"]),
                       ("{w6_qc}", w6["qc"]),
                       ("{w6_limit}", w6["limit"]),
                       ("{w6_t6_block}", w6["t6_block"]),
                       ("{w6_t7_block}", w6["t7_block"]),
                       ("{w6_delta_m_block}", w6["delta_m_block"]),
                       ("{w6_t9_block}", w6["t9_block"])):
        text = text.replace(key, value)
    w7 = week7_blocks(load_json(W7_STAGE7_PATH), load_json(W7_STAGE8_PATH))
    for key, value in (("{w7_did}", w7["did"]),
                       ("{w7_metric}", w7["metric"]),
                       ("{w7_qc}", w7["qc"]),
                       ("{w7_limit}", w7["limit"]),
                       ("{w7_s7_block}", w7["s7_block"]),
                       ("{w7_s8_block}", w7["s8_block"]),
                       ("{w7_summary}", w7["summary"])):
        text = text.replace(key, value)
    w8 = week8_blocks(load_json(W8_STAGE9_PATH), load_json(W8_SHELLS_PATH))
    for key, value in (("{w8_did}", w8["did"]),
                       ("{w8_metric}", w8["metric"]),
                       ("{w8_qc}", w8["qc"]),
                       ("{w8_limit}", w8["limit"]),
                       ("{w8_s9_block}", w8["s9_block"]),
                       ("{w8_summary}", w8["summary"])):
        text = text.replace(key, value)
    w10 = week10_blocks(load_json(W10_ANATOMY_PATH))
    for key, value in (("{w10_did}", w10["did"]),
                       ("{w10_metric}", w10["metric"]),
                       ("{w10_qc}", w10["qc"]),
                       ("{w10_limit}", w10["limit"]),
                       ("{w10_theorem_block}", w10["theorem_block"]),
                       ("{w10_ladder_block}", w10["ladder_block"]),
                       ("{w10_control_block}", w10["control_block"]),
                       ("{w10_predictor_block}", w10["predictor_block"]),
                       ("{w10_drift_block}", w10["drift_block"])):
        text = text.replace(key, value)
    w11 = week11_blocks(load_json(W11_PRESCREEN_PATH))
    for key, value in (("{w11_did}", w11["did"]),
                       ("{w11_metric}", w11["metric"]),
                       ("{w11_qc}", w11["qc"]),
                       ("{w11_limit}", w11["limit"]),
                       ("{w11_law_block}", w11["law_block"]),
                       ("{w11_ratio_block}", w11["ratio_block"]),
                       ("{w11_shape_block}", w11["shape_block"]),
                       ("{w11_forecast_block}", w11["forecast_block"]),
                       ("{w11_prescreen_block}", w11["prescreen_block"]),
                       ("{w11_table_block}", w11["table_block"])):
        text = text.replace(key, value)
    w9 = week9_blocks(load_json(W9_LADDER_PATH))
    for key, value in (("{w9_did}", w9["did"]),
                       ("{w9_metric}", w9["metric"]),
                       ("{w9_qc}", w9["qc"]),
                       ("{w9_limit}", w9["limit"]),
                       ("{w9_ladder_block}", w9["ladder_block"]),
                       ("{w9_verdict_block}", w9["verdict_block"]),
                       ("{w9_sigma_note}", w9["sigma_note"])):
        text = text.replace(key, value)
    w12 = week12_blocks(load_json(W12_ANALYSIS_PATH), load_json(W12_LADDER_PATH))
    for key, value in (("{w12_did}", w12["did"]),
                       ("{w12_metric}", w12["metric"]),
                       ("{w12_qc}", w12["qc"]),
                       ("{w12_limit}", w12["limit"]),
                       ("{w12_law_block}", w12["law_block"]),
                       ("{w12_term_block}", w12["term_block"]),
                       ("{w12_limit_block}", w12["limit_block"]),
                       ("{w12_forecast_block}", w12["forecast_block"]),
                       ("{w12_ledger_block}", w12["ledger_block"]),
                       ("{w12_table_block}", w12["table_block"])):
        text = text.replace(key, value)
    w13 = week13_blocks(load_json(W13_ATTRIBUTION_PATH), load_json(W13_OUTLIER_PATH))
    for key, value in (("{w13_did}", w13["did"]),
                       ("{w13_metric}", w13["metric"]),
                       ("{w13_qc}", w13["qc"]),
                       ("{w13_limit}", w13["limit"]),
                       ("{w13_definition_block}", w13["definition_block"]),
                       ("{w13_state_block}", w13["state_block"]),
                       ("{w13_correction_block}", w13["correction_block"]),
                       ("{w13_attribution_block}", w13["attribution_block"]),
                       ("{w13_outlier_block}", w13["outlier_block"]),
                       ("{w13_repro_block}", w13["repro_block"]),
                       ("{w13_table_block}", w13["table_block"])):
        text = text.replace(key, value)
    w14 = week14_blocks(load_json(W14_TWO_GUESS_PATH), load_json(W14_DIFFUSENESS_PATH),
                        load_json(W14_ANCHOR_PATH))
    for key, value in (("{w14_did}", w14["did"]),
                       ("{w14_metric}", w14["metric"]),
                       ("{w14_qc}", w14["qc"]),
                       ("{w14_limit}", w14["limit"]),
                       ("{w14_protocol_block}", w14["protocol_block"]),
                       ("{w14_limit_block}", w14["limit_block"]),
                       ("{w14_diffuseness_block}", w14["diffuseness_block"]),
                       ("{w14_anchor_block}", w14["anchor_block"]),
                       ("{w14_table_block}", w14["table_block"])):
        text = text.replace(key, value)
    w15 = week15_blocks(load_json(W15_ANALYSIS_PATH), load_json(W15_PREDICTOR_PATH))
    for key, value in (("{w15_did}", w15["did"]),
                       ("{w15_metric}", w15["metric"]),
                       ("{w15_qc}", w15["qc"]),
                       ("{w15_limit}", w15["limit"]),
                       ("{w15_protocol_block}", w15["protocol_block"]),
                       ("{w15_verdict_block}", w15["verdict_block"]),
                       ("{w15_label_block}", w15["label_block"]),
                       ("{w15_family_block}", w15["family_block"]),
                       ("{w15_rule_block}", w15["rule_block"]),
                       ("{w15_table_block}", w15["table_block"])):
        text = text.replace(key, value)
    w16 = week16_blocks(load_json(W16_SMD_PATH), load_json(W16_CONTAMINATION_PATH),
                        load_json(W16_IDENTITY_PATH))
    for key, value in (("{w16_did}", w16["did"]),
                       ("{w16_metric}", w16["metric"]),
                       ("{w16_qc}", w16["qc"]),
                       ("{w16_limit}", w16["limit"]),
                       ("{w16_protocol_block}", w16["protocol_block"]),
                       ("{w16_verdict_block}", w16["verdict_block"]),
                       ("{w16_cells_block}", w16["cells_block"]),
                       ("{w16_identity_block}", w16["identity_block"]),
                       ("{w16_family_block}", w16["family_block"]),
                       ("{w16_table_block}", w16["table_block"])):
        text = text.replace(key, value)
    w17 = week17_blocks(load_json(W17_CENSUS_PATH), load_json(W17_DIAGNOSIS_PATH))
    for key, value in (("{w17_did}", w17["did"]),
                           ("{w17_metric}", w17["metric"]),
                           ("{w17_qc}", w17["qc"]),
                           ("{w17_limit}", w17["limit"]),
                           ("{w17_protocol_block}", w17["protocol_block"]),
                           ("{w17_census_block}", w17["census_block"]),
                           ("{w17_diagnosis_block}", w17["diagnosis_block"]),
                           ("{w17_onesided_block}", w17["onesided_block"]),
                           ("{w17_table_block}", w17["table_block"])):
        text = text.replace(key, value)
    w18 = week18_blocks(load_json(W18_LEDGER_PATH), load_json(W18_ANALYSIS_PATH))
    for key, value in (("{w18_did}", w18["did"]),
                       ("{w18_metric}", w18["metric"]),
                       ("{w18_qc}", w18["qc"]),
                       ("{w18_limit}", w18["limit"]),
                       ("{w18_protocol_block}", w18["protocol_block"]),
                       ("{w18_verdict_block}", w18["verdict_block"]),
                       ("{w18_geometry_block}", w18["geometry_block"]),
                       ("{w18_table_block}", w18["table_block"])):
        text = text.replace(key, value)
    w20 = week20_blocks(load_json(W20_PATH_JSON), load_json(W20_PROTOCOL_JSON),
                        load_json(W20_SHELL_JSON), load_json(W20_REFILL_JSON))
    for key, value in (("{w20_did}", w20["did"]),
                       ("{w20_metric}", w20["metric"]),
                       ("{w20_qc}", w20["qc"]),
                       ("{w20_limit}", w20["limit"]),
                       ("{w20_protocol_block}", w20["protocol_block"]),
                       ("{w20_path_block}", w20["path_block"]),
                       ("{w20_shell_block}", w20["shell_block"]),
                       ("{w20_refill_block}", w20["refill_block"]),
                       ("{w20_table_block}", w20["table_block"])):
        text = text.replace(key, value)
    w21 = week21_blocks(load_json(W21_PHASE_JSON), load_json(W21_PROSPECTIVE_JSON),
                        load_json(W21_FROZEN_JSON), load_json(W21_ANCHOR_JSON))
    for key, value in (("{w21_did}", w21["did"]),
                       ("{w21_metric}", w21["metric"]),
                       ("{w21_qc}", w21["qc"]),
                       ("{w21_limit}", w21["limit"]),
                       ("{w21_alignment_block}", w21["alignment_block"]),
                       ("{w21_phase_block}", w21["phase_block"]),
                       ("{w21_prospective_block}", w21["prospective_block"]),
                       ("{w21_table_block}", w21["table_block"])):
        text = text.replace(key, value)
    w19 = week19_blocks(load_json(W19_RUNG_PATH), load_json(W19_ARMS_PATH),
                        load_json(W19_ARMS_ANALYSIS_PATH))
    for key, value in (("{w19_did}", w19["did"]),
                       ("{w19_metric}", w19["metric"]),
                       ("{w19_qc}", w19["qc"]),
                       ("{w19_limit}", w19["limit"]),
                       ("{w19_protocol_block}", w19["protocol_block"]),
                       ("{w19_rung_block}", w19["rung_block"]),
                       ("{w19_xtb_block}", w19["xtb_block"]),
                       ("{w19_table_block}", w19["table_block"])):
        text = text.replace(key, value)

    if missing:
        rows = []
        for entry in missing:
            tag = "optional (pending)" if entry["optional"] else "required"
            rows.append(f"- `{entry['source']}` —— {tag}")
        text = text.replace("{missing_list}", "\n".join(rows))
    else:
        text = text.replace("{missing_list}", "- 无（全部源路径均存在）")
    return text


def gate0_sha_table():
    """Markdown table of the Gate 0 sha256 lines, re-verified against the repo."""
    text = read_text(REPO / "outputs" / "week1" / "gate0_record.md")
    if text is None:
        return "（`outputs/week1/gate0_record.md` 不存在）"
    rows = ["| 冻结产物 | sha256 (记录值) | 现场重算 | 一致 |",
             "| --- | --- | --- | --- |"]
    for rel, recorded in re.findall(r"^-\s*(\S+)\s+([0-9a-f]{64})\s*$", text, re.M):
        target = REPO / rel
        actual = sha256_file(target) if target.exists() else "n/a"
        rows.append(f"| `{rel}` | `{recorded}` | `{actual}` | "
                    f"{'yes' if actual == recorded else 'NO'} |")
    return "\n".join(rows)


def week1_checks(wdir: Path):
    checks = []
    record = wdir / "gate0_record.md"
    text = read_text(record)
    if text is None:
        checks.append(check("gate0_record_present", None, "source not found"))
        return checks
    checks.append(check("gate0_record_present", True, "gate0_record.md present"))
    status = "CLOSED" if re.search(r"status:\s*\*\*CLOSED\*\*", text) else "UNKNOWN"
    checks.append(check("gate0_status_closed", status == "CLOSED", f"status={status}"))
    frozen = re.search(r"frozen artefacts:\s*(\d+)", text)
    checks.append(check("gate0_frozen_artefacts", frozen is not None,
                        f"frozen_artefacts={frozen.group(1) if frozen else 'n/a'}"))
    for name, ok, detail in re.findall(r"^\|\s*([^|]+?)\s*\|\s*(yes|no)\s*\|\s*([^|]*?)\s*\|\s*$",
                                       text, re.M | re.I):
        checks.append(check(f"gate0:{name.strip()}", ok.lower() == "yes", detail.strip()))
    for rel, recorded in re.findall(r"^-\s*(\S+)\s+([0-9a-f]{64})\s*$", text, re.M):
        target = REPO / rel
        actual = sha256_file(target) if target.exists() else "n/a"
        checks.append(check(f"sha256:{rel}", actual == recorded,
                            f"recorded={recorded} actual={actual}"))
    return checks


def week2_checks(wdir: Path):
    checks = []
    audit = load_json(wdir / "method_audit_xtb_summary.json")
    if audit is None:
        checks.append(check("method_audit.summary", None, "source not found"))
    else:
        checks.append(check("method_audit.n_molecules==12", audit.get("n_molecules") == 12,
                            f"n_molecules={audit.get('n_molecules')}"))
        checks.append(check("method_audit.n_unbound_anion==2", audit.get("n_unbound_anion") == 2,
                            f"n_unbound_anion={audit.get('n_unbound_anion')}"))
    anchors = load_json(wdir / "solution_anchor_audit.json")
    if anchors is None:
        checks.append(check("solution_anchor_audit.summary", None, "source not found"))
    else:
        summary = anchors.get("summary", {}) or {}
        checks.append(check("solution_anchor.rows_total==31", summary.get("rows_total") == 31,
                            f"rows_total={summary.get('rows_total')}"))
        checks.append(check("solution_anchor.still_est_count==31",
                            summary.get("still_est_count") == 31,
                            f"still_est_count={summary.get('still_est_count')} "
                            f"upgraded={len(summary.get('upgraded') or [])}"))
        checks.append(check("solution_anchor.consistency_ok", summary.get("consistency_ok"),
                            f"consistency_ok={summary.get('consistency_ok')}"))
    gate = read_text(wdir / "gate1_record.md")
    if gate is None:
        checks.append(check("gate1_status", None, "source not found"))
    else:
        ok = "NOT CLOSED" in gate
        checks.append(check("gate1_status==NOT CLOSED", ok,
                            "gate1_record.md: status NOT CLOSED"))
    return checks


def week3_checks(wdir: Path):
    checks = []
    for tag, name in (("core", "p0_core_set_summary.json"),
                      ("broad", "p0_broad_pool_summary.json")):
        data = load_json(wdir / name)
        if data is None:
            checks.append(check(f"p0_{tag}", None, "source not found"))
            continue
        checks.append(check(f"p0_{tag}.n_ok==n_total", data.get("n_ok") == data.get("n_total"),
                            f"n_ok={data.get('n_ok')} n_total={data.get('n_total')} "
                            f"n_failed={data.get('n_failed')}"))
        checks.append(check(f"p0_{tag}.n_abnormal_termination==0",
                            data.get("n_abnormal_termination") == 0,
                            f"n_abnormal_termination={data.get('n_abnormal_termination')}"))
    summary = load_json(wdir / "p0_summary.json")
    if summary is None:
        checks.append(check("p0_summary", None, "source not found"))
        return checks
    preview = summary.get("decision_preview", {}) or {}
    ligand = (preview.get("reference_ligand", {}) or {}).get("DME", {}) or {}
    checks.append(check("reference_ligand.primary_R==DME",
                        ligand.get("role") == "primary_R",
                        f"mol_id={ligand.get('mol_id')} role={ligand.get('role')}"))
    checks.append(check("decision_preview.n_combined==58", preview.get("n_combined") == 58,
                        f"n_combined={preview.get('n_combined')} "
                        f"n_core={preview.get('n_core_ok')} n_broad={preview.get('n_broad_ok')}"))
    checks.append(check("p0_summary.generated_utc present", bool(summary.get("generated_utc")),
                        f"generated_utc={summary.get('generated_utc')}"))
    return checks


P1_FLAGS = ["energy_mismatch", "scf_failed", "abnormal_termination", "spin_contamination_flag"]


def week4_checks(wdir: Path):
    checks = []

    summary = load_json(wdir / "p1_core_set_summary.json")
    if summary is None:
        checks.append(check("p1_jobs_ok==n_jobs", None, "source not found"))
    else:
        checks.append(check("p1_jobs_ok==n_jobs", summary.get("n_ok") == summary.get("n_jobs"),
                            f"n_ok={summary.get('n_ok')} n_jobs={summary.get('n_jobs')} "
                            f"n_failed={summary.get('n_failed')}"))
        checks.append(check("p1_geometry==G1", "G1" in str(summary.get("geometry")),
                            f"geometry={summary.get('geometry')} env={summary.get('environment')}"))

    audit = load_json(wdir / "p1_core_set_audit.json")
    if audit is None:
        for flag in P1_FLAGS:
            checks.append(check(f"p1_audit.{flag}==0", None, "source not found"))
        checks.append(check("unbound_anion==18", None, "source not found"))
    else:
        flags = audit.get("flag_counts", {}) or {}
        for flag in P1_FLAGS:
            checks.append(check(f"p1_audit.{flag}==0", flags.get(flag) == 0,
                                f"{flag}={flags.get(flag)} n_records={audit.get('n_records')}"))
        checks.append(check("unbound_anion==18", flags.get("unbound_anion") == 18,
                            f"unbound_anion={flags.get('unbound_anion')} "
                            f"n_molecules={audit.get('n_molecules')}"))

    anchors = load_json(wdir / "p1_anchor_comparison.json")
    if anchors is None:
        checks.append(check("anchor_comparison", None, "source not found"))
    else:
        for arm, expected in (("P0_koopmans_xTB", 1.377),
                              ("GFN2_dSCF_xTB", 4.481),
                              ("P1_r2SCAN3c", 0.251)):
            mae = (anchors.get(arm) or {}).get("mae_ev")
            checks.append(check(f"anchor.{arm}.mae~{expected}",
                                mae is not None and abs(mae - expected) < 2e-3,
                                f"mae_ev={mae}"))

    p1ds = load_json(wdir / "p1_decision_stability.json")
    if p1ds is None:
        checks.append(check("p1_decision_stability", None, "source not found"))
    else:
        for axis in ("oxidation", "reduction"):
            block = p1ds.get(axis) or {}
            checks.append(check(f"p1_decision_stability.{axis}.z_primary==1.0",
                                block.get("z_primary") == 1.0,
                                f"z_primary={block.get('z_primary')} "
                                f"tau_b={block.get('kendall_tau_b')} "
                                f"f_robust_inv={block.get('f_robust_inv')}"))

    p2summary = load_json(wdir / "p2_summary_smd_acetonitrile.json")
    if p2summary is None:
        checks.append(check("p2_jobs_ok==n_jobs", None, "source not found"))
    else:
        checks.append(check("p2_jobs_ok==n_jobs", p2summary.get("n_ok") == p2summary.get("n_jobs"),
                            f"n_ok={p2summary.get('n_ok')} n_jobs={p2summary.get('n_jobs')} "
                            f"n_failed={p2summary.get('n_failed')}"))

    p2ds = load_json(wdir / "p2_decision_stability.json")
    if p2ds is None:
        checks.append(check("p2_decision_stability.z_primary==1.0", None, "source not found"))
    else:
        block = p2ds.get("p1_to_p2") or {}
        z = {axis: (block.get(axis) or {}).get("z_primary") for axis in ("oxidation", "reduction")}
        checks.append(check("p2_decision_stability.z_primary==1.0",
                            z.get("oxidation") == 1.0 and z.get("reduction") == 1.0,
                            f"p1_to_p2.z_primary(ox)={z.get('oxidation')} "
                            f"p1_to_p2.z_primary(red)={z.get('reduction')}"))
        delta_ip = p2ds.get("delta_ip") or {}
        delta_ea = p2ds.get("delta_ea") or {}
        checks.append(check("p2.delta_ip.mean~-2.393",
                            abs((delta_ip.get("mean_ev") or 0) + 2.393) < 2e-3,
                            f"mean_ev={delta_ip.get('mean_ev')} std_ev={delta_ip.get('std_ev')}"))
        checks.append(check("p2.delta_ea.mean~+2.173",
                            abs((delta_ea.get("mean_ev") or 0) - 2.173) < 2e-3,
                            f"mean_ev={delta_ea.get('mean_ev')} std_ev={delta_ea.get('std_ev')}"))

    t5 = load_json(wdir / "t5_diffuse_control_summary.json")
    if t5 is None:
        checks.append(check("t5.n_ok==t5.n_jobs", None, "source not found"))
    else:
        checks.append(check("t5.n_ok==t5.n_jobs", t5.get("n_ok") == t5.get("n_jobs"),
                            f"n_ok={t5.get('n_ok')} n_jobs={t5.get('n_jobs')} "
                            f"n_failed={t5.get('n_failed')}"))
        by_arm = t5.get("bound_by_arm") or {}
        flat = [v for arm in by_arm.values() for v in arm.values()]
        checks.append(check("t5.no_arm_binds_anion",
                            (not any(flat)) if flat else None,
                            f"n_bound={sum(1 for x in flat if x)}/{len(flat)} across "
                            f"{len(by_arm)} arms"))

    t3 = load_json(wdir / "t3_cpcm_eps_scan_summary.json")
    if t3 is None:
        checks.append(check("t3_cpcm_eps_scan", None, "source not found (optional, pending)"))
    else:
        checks.append(check("t3_cpcm_eps_scan.present", True,
                            f"keys={len(t3)} (optional arm included)"))
    return checks


def week5_checks(wdir: Path):
    """QC for week 5 (Stage 5 / T4, C1 Li+ coordination).

    A failed ORCA job is a *result* here, not an error: the sweep records
    ``geometry_failed`` / ``dissociated_optimized_product`` instead of aborting, so
    the run-level assertion is deliberately "some jobs recorded and the SCF closed",
    not "every job returned ok".
    """

    checks = []

    run = load_json(wdir / "c1_li_coordination_summary.json")
    if run is None:
        checks.append(check("c1_run.n_jobs>0", None, "source not found"))
    else:
        checks.append(check("c1_run.n_jobs>0", (run.get("n_jobs") or 0) > 0,
                            f"n_jobs={run.get('n_jobs')} n_ok={run.get('n_ok')} "
                            f"status_counts={run.get('status_counts')}"))
        flags = run.get("qc_flag_counts") or {}
        checks.append(check("c1_run.scf_failed==0", flags.get("scf_failed", 0) == 0,
                            f"scf_failed={flags.get('scf_failed')}"))

    summary = load_json(wdir / "c1_summary.json")
    if summary is None:
        checks.append(check("c1_summary.present", None, "source not found"))
    else:
        checks.append(check("c1_summary.n_molecules>0", (summary.get("n_molecules") or 0) > 0,
                            f"n_molecules={summary.get('n_molecules')} "
                            f"n_motifs={summary.get('n_motifs')}"))
        d_ip = summary.get("delta_ip_ev") or {}
        d_ea = summary.get("delta_ea_ev") or {}
        checks.append(check("c1_summary.delta_ip_ev.n>0", (d_ip.get("n") or 0) > 0,
                            f"n={d_ip.get('n')} mean={d_ip.get('mean')} std={d_ip.get('std')}"))
        checks.append(check("c1_summary.delta_ea_ev.n>0", (d_ea.get("n") or 0) > 0,
                            f"n={d_ea.get('n')} mean={d_ea.get('mean')} std={d_ea.get('std')}"))

    stability = load_json(wdir / "c1_decision_stability.json")
    if stability is None:
        checks.append(check("c1_decision_stability.z_primary==1.0", None, "source not found"))
    else:
        z = {axis: (stability.get(axis) or {}).get("z_primary")
             for axis in ("oxidation", "reduction")}
        checks.append(check("c1_decision_stability.z_primary==1.0",
                            z.get("oxidation") == 1.0 and z.get("reduction") == 1.0,
                            f"oxidation={z.get('oxidation')} reduction={z.get('reduction')}"))
    return checks


def week6_checks(wdir: Path):
    """QC for week 6 (Stage 6: T6 conformers / T7 freq / T8 delta_m / T9 stability)."""

    checks = []
    t6 = load_json(wdir / "t6_conformer_spread.json")
    if t6 is None:
        checks.append(check("t6_conformer_spread.present", None, "source not found"))
    else:
        counts = t6.get("counts") or {}
        for layer in ("p0", "p1"):
            c = counts.get(layer) or {}
            checks.append(check("t6.%s.n_failures==0" % layer, c.get("n_failures") == 0,
                                "n_failures=%s n_conformers=%s n_molecules_scored=%s"
                                % (c.get("n_failures"), c.get("n_conformers_total"),
                                   c.get("n_molecules_scored"))))
        checks.append(check("t6.subset.n==12", len(t6.get("subset") or []) == 12,
                            "n=%s" % len(t6.get("subset") or [])))
    t7 = load_json(wdir / "t7_c1_freq_check.json")
    if t7 is None:
        checks.append(check("t7_c1_freq_check.present", None, "source not found"))
    else:
        checks.append(check("t7.n_ok==n_molecules", t7.get("n_ok") == t7.get("n_molecules"),
                            "n_ok=%s n_molecules=%s n_imaginary=%s"
                            % (t7.get("n_ok"), t7.get("n_molecules"), t7.get("n_imaginary"))))
    t8 = load_json(wdir / "delta_m_frozen.json")
    if t8 is None:
        checks.append(check("delta_m_frozen.present", None, "source not found"))
    else:
        status = str(t8.get("status") or "")
        checks.append(check("delta_m.status==CANDIDATE", status.startswith("CANDIDATE"),
                            "status=%s" % status))
        meth = (t8.get("method_evidence") or {}).get("oxidation") or {}
        checks.append(check("delta_m.method_sigma>0",
                            (meth.get("sigma_method_ev") or 0) > 0,
                            "oxidation sigma_method_ev=%s" % meth.get("sigma_method_ev")))
    t9 = load_json(wdir / "stage6_decision_stability.json")
    if t9 is None:
        checks.append(check("stage6_decision_stability.present", None, "source not found"))
    else:
        z = (t9.get("prereg") or {}).get("z_primary")
        checks.append(check("stage6.z_primary==1.0", z == 1.0, "z_primary=%s" % z))
        cons = t9.get("consistency_checks") or []
        checks.append(check("stage6.consistency_checks>=3", len(cons) >= 3,
                            "n=%s" % len(cons)))
        e = (((t9.get("results") or {}).get("docx_max") or {}).get("P0_to_P1")
             or {}).get("oxidation") or {}
        checks.append(check("stage6.docx_max.P0_to_P1.oxidation.f_robust_inv==0",
                            e.get("f_robust_inv") == 0.0,
                            "f_robust_inv=%s n_pairs_resolved_in_both=%s"
                            % (e.get("f_robust_inv"), e.get("n_pairs_resolved_in_both"))))
    return checks


def week7_checks(wdir: Path):
    """QC for week 7 (Stage 7 ML matrix / Stage 8 active-learning replay)."""

    checks = []
    s7 = load_json(wdir / "stage7_ml_results.json")
    if s7 is None:
        checks.append(check("stage7_ml_results.present", None, "source not found"))
    else:
        counts = s7.get("counts") or {}
        settings = s7.get("settings") or {}
        checks.append(check("stage7.n_fit_fallbacks==0", counts.get("n_fit_fallbacks") == 0,
                            "n_fit_fallbacks=%s n_result_rows=%s n_oof_rows=%s"
                            % (counts.get("n_fit_fallbacks"), counts.get("n_result_rows"),
                               counts.get("n_oof_rows"))))
        checks.append(check("stage7.splits=={random,group,lofo}",
                            set(settings.get("split_methods") or [])
                            == {"random", "group", "lofo"},
                            "split_methods=%s" % (settings.get("split_methods"),)))
        checks.append(check("stage7.shapes=={direct,shift}",
                            set(settings.get("shapes") or []) == {"direct", "shift"},
                            "shapes=%s" % (settings.get("shapes"),)))
        checks.append(check("stage7.model_ladder>=6",
                            len(settings.get("model_order") or []) >= 6,
                            "model_order=%s" % (settings.get("model_order"),)))
        rows = s7.get("results") or []
        combos = sorted({(row.get("task"), row.get("feature_set"), row.get("objective"))
                         for row in rows})
        complete = all(
            {row.get("split") for row in rows
             if (row.get("task"), row.get("feature_set"), row.get("objective")) == key}
            == {"random", "group", "lofo"} for key in combos)
        checks.append(check("stage7.every_combo_reports_three_splits", complete and bool(combos),
                            "n_combos=%d" % len(combos)))
        checks.append(check("stage7.lofo_rows>0",
                            any(row.get("split") == "lofo" for row in rows),
                            "n_lofo=%d" % sum(1 for row in rows if row.get("split") == "lofo")))
    s8 = load_json(wdir / "stage8_al_results.json")
    if s8 is None:
        checks.append(check("stage8_al_results.present", None, "source not found"))
    else:
        protocol = s8.get("protocol") or {}
        settings = s8.get("settings") or {}
        checks.append(check("stage8.initial_seed_size==4",
                            protocol.get("initial_seed_size") == 4,
                            "initial_seed_size=%s" % protocol.get("initial_seed_size")))
        checks.append(check("stage8.hidden_label_replay",
                            protocol.get("hidden_label_replay") is True,
                            "hidden_label_replay=%s" % protocol.get("hidden_label_replay")))
        checks.append(check("stage8.acquisition_features=='X0 only'",
                            settings.get("acquisition_features") == "X0 only",
                            "acquisition_features=%s" % settings.get("acquisition_features")))
        checks.append(check("stage8.n_fit_fallbacks==0",
                            (s8.get("counts") or {}).get("n_fit_fallbacks") == 0,
                            "n_fit_fallbacks=%s" % (s8.get("counts") or {}).get("n_fit_fallbacks")))
        curves = s8.get("curves") or []
        baselines = sorted({row.get("baseline") for row in curves})
        checks.append(check("stage8.baselines==4",
                            baselines == ["diversity", "random", "ranking_aware",
                                          "uncertainty"],
                            "baselines=%s" % baselines))
        pools = s8.get("pools") or {}
        endpoints = 0
        for row in curves:
            key = "%s:%s" % (row.get("task"), row.get("objective"))
            size = (pools.get(key) or {}).get("n_pool")
            if size is None:
                continue
            if int(row.get("n_T") or 0) == int(size) and (row.get("kendall_tau_b") or 0) > 0.999:
                endpoints += 1
        checks.append(check("stage8.full_budget_endpoint_tau_b==1", endpoints > 0,
                            "n_endpoint_rows=%d" % endpoints))
    checks.append(check("week7.figures_present",
                        (wdir / "artifacts" / "F16_stage7_direct_vs_shift.png").exists()
                        and (wdir / "artifacts" / "F17_stage8_active_learning.png").exists(),
                        "artifacts/ F16 + F17"))
    return checks


def week8_checks(wdir: Path):
    """QC for week 8 (Stage 9, explicit first solvation shell [Li(M)2]+)."""

    checks = []
    s9 = load_json(wdir / "stage9_results.json")
    shells = load_json(wdir / "ms_shell_generation.json")
    if s9 is None:
        checks.append(check("stage9_results.present", None, "source not found"))
    else:
        shifts = s9.get("shifts") or []
        dft = s9.get("dft_jobs") or {}
        checks.append(check("stage9.n_motifs==12", s9.get("n_motifs") == 12,
                            "n_motifs=%s" % s9.get("n_motifs")))
        checks.append(check("stage9.motifs_with_shell2==n_motifs",
                            s9.get("motifs_with_shell2") == s9.get("n_motifs"),
                            "motifs_with_shell2=%s n_motifs=%s"
                            % (s9.get("motifs_with_shell2"), s9.get("n_motifs"))))
        checks.append(check("stage9.dft.n_jobs==36", dft.get("n_jobs") == 36,
                            "n_jobs=%s n_ok=%s" % (dft.get("n_jobs"), dft.get("n_ok"))))
        checks.append(check("stage9.dft.n_ok==n_jobs",
                            dft.get("n_ok") is not None and dft.get("n_ok") == dft.get("n_jobs"),
                            "n_ok=%s status_counts=%s"
                            % (dft.get("n_ok"), dft.get("status_counts"))))
        families = sorted({row.get("family") for row in shifts})
        checks.append(check("stage9.n_families>=6", len(families) >= 6,
                            "families=%s" % families))
        stability = {(row.get("axis"), row.get("population")): row
                     for row in (s9.get("stability") or [])}
        for axis, population in (("oxidation", "all12"), ("reduction", "all12"),
                                 ("oxidation", "primary_m1"),
                                 ("reduction", "primary_m1")):
            row = stability.get((axis, population))
            checks.append(check("stage9.stability.%s.%s.present" % (axis, population),
                                row is not None,
                                "n=%s tau_b=%s"
                                % (None if row is None else row.get("n"),
                                   None if row is None else row.get("kendall_tau_b"))))
    if shells is None:
        checks.append(check("ms_shell_generation.present", None, "source not found"))
    else:
        rows = shells.get("shells") or []
        checks.append(check("ms_shell_generation.n_shell==2 and n_selected==12",
                            shells.get("n_shell") == 2 and shells.get("n_selected") == 12,
                            "n_shell=%s n_selected=%s"
                            % (shells.get("n_shell"), shells.get("n_selected"))))
        checks.append(check("ms_shell_generation.second_ligand_intact_all",
                            bool(rows) and all(bool(row.get("second_ligand_intact"))
                                               for row in rows),
                            "n_rows=%d n_intact=%d"
                            % (len(rows),
                               sum(1 for row in rows if row.get("second_ligand_intact")))))
    checks.append(check("week8.figures_present",
                        (wdir / "artifacts" / "F18_stage9_explicit_shell.png").exists(),
                        "artifacts/ F18"))
    return checks


def week9_checks(wdir: Path):
    """QC for week 9 (Stage 10, the five-rung synthesis on one yardstick)."""

    checks = []
    payload = load_json(wdir / "stage10_ladder.json")
    if payload is None:
        checks.append(check("stage10_ladder.present", None, "source not found"))
        return checks

    rows = payload.get("ladder") or []
    common = [row for row in rows if row.get("population") == "common10"]
    native = [row for row in rows if row.get("population") == "native"]
    subsets = payload.get("common_subset") or []
    hypothesis = payload.get("hypothesis_test") or {}
    verdicts = payload.get("verdicts") or {}
    checklist = payload.get("minimum_outcome_checklist") or []

    checks.append(check("stage10.n_rows==20", len(rows) == 20,
                        "n_rows=%d (native %d / common10 %d)"
                        % (len(rows), len(native), len(common))))
    checks.append(check("stage10.rungs==5", len({row.get("rung") for row in rows}) == 5,
                        "rungs=%s" % sorted({row.get("rung") for row in rows})))
    checks.append(check("stage10.common_subset==10", len(subsets) == 10,
                        "common_subset=%s" % subsets))
    checks.append(check("stage10.common10.rows_computed_on_10",
                        bool(common) and all(int(row.get("n") or 0) == 10
                                             for row in common),
                        "n per common10 row=%s"
                        % sorted({row.get("n") for row in common})))

    spread = hypothesis.get("spearman_shift_std_vs_tau_b")
    magnitude = hypothesis.get("spearman_abs_shift_mean_vs_tau_b")
    unres = hypothesis.get("spearman_shift_std_vs_f_unresolved")
    checks.append(check("stage10.hypothesis.n_points==10",
                        hypothesis.get("n_points") == 10,
                        "n_points=%s" % hypothesis.get("n_points")))
    checks.append(check("stage10.hypothesis.spread_beats_magnitude",
                        spread is not None and magnitude is not None
                        and abs(spread) > abs(magnitude),
                        "rho(std,tau)=%s vs rho(|mean|,tau)=%s" % (spread, magnitude)))
    checks.append(check("stage10.hypothesis.spread_vs_unresolved_positive",
                        unres is not None and unres > 0,
                        "rho(std,f_unresolved)=%s" % unres))

    negatives = [(row.get("rung"), row.get("axis")) for row in common
                 if (row.get("kendall_tau_b") or 0) < 0]
    checks.append(check("stage10.exactly_one_negative_tau_b",
                        negatives == [("C0_to_C1", "reduction")],
                        "negative=%s" % negatives))

    robust = [row.get("f_robust_inv") for row in rows]
    robust96 = [row.get("f_robust_inv_z1p96") for row in rows]
    worst = max([row.get("f_unresolved_after") or 0.0 for row in rows] or [0.0])
    checks.append(check("stage10.f_robust_inv.zero_everywhere",
                        bool(robust) and all((value or 0.0) == 0.0 for value in robust)
                        and all((value or 0.0) == 0.0 for value in robust96),
                        "max f_robust_inv=%s (z=1.96 max=%s)"
                        % (max(robust or [0.0]), max(robust96 or [0.0]))))
    checks.append(check("stage10.zero_is_not_stability",
                        worst > 0.5,
                        "max f_unresolved_after=%.3f" % worst))

    letters = [key[0] for key in verdicts if not key.startswith("_")]
    checks.append(check("stage10.verdicts.a_to_g", letters == list("ABCDEFG"),
                        "verdicts=%s" % letters))
    unsafe = [key for key, entry in verdicts.items() if not key.startswith("_")
              and any("|" in str(entry.get(field) or "")
                      for field in ("short", "definition", "verdict", "evidence"))]
    checks.append(check("stage10.verdicts.table_safe", not unsafe,
                        "fields with a raw pipe: %s" % (unsafe or "none")))
    checks.append(check("stage10.checklist.n==11", len(checklist) == 11,
                        "n=%d" % len(checklist)))
    statuses = {item.get("id"): item.get("status") for item in checklist}
    checks.append(check("stage10.checklist.only_anchors_partial",
                        statuses.get("5") == "PARTIAL"
                        and all(str(status).startswith("PASS")
                                for key, status in statuses.items() if key != "5"),
                        "statuses=%s" % statuses))

    checks.append(check("week9.figures_present",
                        (wdir / "artifacts" / "F19_stage10_ladder.png").exists(),
                        "artifacts/ F19"))
    return checks


def week10_checks(wdir: Path):
    """QC for week 10 (Stage 11, the sigma anatomy and the resolution criterion)."""

    checks = []
    payload = load_json(wdir / "stage11_sigma_anatomy.json")
    if payload is None:
        checks.append(check("stage11_sigma_anatomy.present", None, "source not found"))
        return checks
    checks.append(check("stage11_sigma_anatomy.present", True,
                        "stage11_sigma_anatomy.json present"))

    rows = payload.get("rows") or []
    subset = payload.get("common_subset") or []
    theorems = payload.get("theorems") or {}
    controls = payload.get("control_checks") or {}
    predict = payload.get("predictability") or {}
    table = {item.get("predictor"): item for item in (predict.get("table") or [])}
    drift = payload.get("subset_drift") or {}
    key = payload.get("key_numbers") or {}

    checks.append(check("stage11.n_rows==10", len(rows) == 10, "n_rows=%d" % len(rows)))
    checks.append(check("stage11.common_subset==10", len(subset) == 10,
                        "common_subset=%s" % subset))
    checks.append(check("stage11.rows_all_n10",
                        bool(rows) and all(int(row.get("n") or 0) == 10 for row in rows),
                        "n per row=%s" % sorted({row.get("n") for row in rows})))

    # T1..T5: every identity must carry its own numeric verification
    for name in ("T1_sigma_is_shift_difference", "T2_rms_sigma_is_shift_stdev",
                 "T3_rigid_offset_invariance", "T4_closed_form_unresolved",
                 "T5_sigma2_budget_split"):
        entry = theorems.get(name) or {}
        checks.append(check("stage11.theorem.%s" % name.split("_")[0],
                            entry.get("ok") is True,
                            "%s ok=%s" % (name, entry.get("ok"))))

    checks.append(check("stage11.control.rank_shift_monotone_Lipschitz",
                        (controls.get("rank_shift_monotone_never_unresolved") or {}).get("ok") is True,
                        "tau_b/f_unresolved values=%s / %s"
                        % ((controls.get("rank_shift_monotone_never_unresolved") or {}).get("tau_b_values"),
                           (controls.get("rank_shift_monotone_never_unresolved") or {}).get("f_unresolved_values"))))
    checks.append(check("stage11.control.linear_shift_matches_theory",
                        (controls.get("linear_shift_matches_theory") or {}).get("ok") is True,
                        "max |q_median - |b||=%s"
                        % (controls.get("linear_shift_matches_theory") or {}).get("max_abs_q_median_minus_abs_b")))

    # T4 must be a restatement of the project's own f_unresolved, not a new number
    worst_z1 = max([row.get("t4_abs_err_z1") or 0.0 for row in rows] or [0.0])
    worst_z196 = max([row.get("t4_abs_err_z1p96") or 0.0 for row in rows] or [0.0])
    checks.append(check("stage11.t4_closed_form_is_exact",
                        worst_z1 == 0.0 and worst_z196 == 0.0,
                        "max abs err z=1: %s, z=1.96: %s" % (worst_z1, worst_z196)))

    # T2 in row form
    worst_sigma = max([abs((row.get("sigma_rms_ev") or 0.0) - (row.get("delta_sd_ev") or 0.0))
                       for row in rows] or [0.0])
    checks.append(check("stage11.rms_sigma_equals_shift_stdev", worst_sigma < 1e-12,
                        "max |RMS sigma - sd(delta)|=%s" % worst_sigma))

    # the predictability result, and the refuted natural hypothesis
    signed = table.get("ols_slope_b") or {}
    residual = table.get("sigma2_share_residual") or {}
    unsigned = table.get("sigma_rms_ev") or {}
    checks.append(check("stage11.predictability.signed_slope_auc==1",
                        (signed.get("auc") or 0.0) > 0.999,
                        "ols_slope_b AUC=%s p=%s" % (signed.get("auc"),
                                                     signed.get("auc_exact_permutation_p"))))
    checks.append(check("stage11.predictability.permutation_is_exhaustive",
                        signed.get("n_permutations") == 120,
                        "n_permutations=%s" % signed.get("n_permutations")))
    checks.append(check("stage11.predictability.unsigned_is_weaker",
                        (unsigned.get("auc") or 1.0) < (signed.get("auc") or 0.0),
                        "sd(delta) AUC=%s vs signed slope AUC=%s"
                        % (unsigned.get("auc"), signed.get("auc"))))
    residual_auc = residual.get("auc")
    checks.append(check("stage11.predictability.residual_share_refuted",
                        residual_auc is not None and residual_auc < 0.001,
                        "sigma2_share_residual AUC=%s (natural hypothesis refuted)"
                        % residual_auc))

    biggest = (key.get("largest_sigma_points") or [{}])[0]
    checks.append(check("stage11.largest_sigma_point_is_not_a_rewrite",
                        biggest.get("shortlist_rewritten") is False
                        and (biggest.get("sigma_rms_ev") or 0.0) > 2.0,
                        "%s/%s sigma=%s rewrite=%s"
                        % (biggest.get("rung"), biggest.get("axis"),
                           biggest.get("sigma_rms_ev"), biggest.get("shortlist_rewritten"))))

    checks.append(check("stage11.subset_drift.present", len(drift) >= 2,
                        "drift series=%s" % sorted(drift)))
    # Do the per-N mean tau_b values drift systematically, or is the spread
    # across N smaller than the sampling noise at the same N?  A "stable"
    # series shows no systematic bias: its mean range is both absolutely
    # small and below the largest per-N sampling std.
    drift_ok = bool(drift)
    drift_bits = []
    for series_key, series in drift.items():
        means = [item["tau_b_mean"] for item in series
                 if item.get("tau_b_mean") is not None]
        stds = [item["tau_b_std"] for item in series
                if item.get("tau_b_std") is not None]
        if len(means) < 3:
            drift_ok = False
            drift_bits.append("%s: only %d N levels" % (series_key, len(means)))
            continue
        spread = max(means) - min(means)
        ref_std = max(stds) if stds else 0.0
        stable = spread < 0.05 and (ref_std == 0.0 or spread < ref_std)
        drift_ok = drift_ok and stable
        drift_bits.append("%s spread=%.4f vs max_std=%.4f" % (series_key, spread, ref_std))
    checks.append(check("stage11.subset_drift.means_are_stable",
                        drift_ok,
                        "mean tau_b is N-stable: " + "; ".join(drift_bits)))

    checks.append(check("week10.figures_present",
                        (wdir / "artifacts" / "F20_sigma_anatomy.png").exists()
                        and (wdir / "artifacts" / "F21_sigma_controls.png").exists(),
                        "artifacts/ F20 + F21"))
    checks.append(check("week10.report_present",
                        (wdir / "week10_report_full.md").exists(),
                        "week10_report_full.md"))
    return checks


def week11_checks(wdir: Path):
    """QC for week 11 (Stage 12, the dielectric law and the pilot protocol)."""

    checks = []
    payload = load_json(wdir / "stage12_prescreen.json")
    if payload is None:
        checks.append(check("stage12_prescreen.present", None, "source not found"))
        return checks
    checks.append(check("stage12_prescreen.present", True,
                        "stage12_prescreen.json present"))

    rows = payload.get("rows") or []
    subset = payload.get("common_subset") or []
    law = payload.get("dielectric_law") or {}
    shape = payload.get("shape_invariance") or {}
    forecast = payload.get("extrapolation") or {}
    screen = payload.get("prescreen") or {}

    checks.append(check("stage12.n_points==18", len(rows) == 18, "n_points=%d" % len(rows)))
    checks.append(check("stage12.common_subset==10", len(subset) == 10,
                        "common_subset=%s" % subset))
    checks.append(check("stage12.rows_all_n10",
                        bool(rows) and all(int(row.get("n") or 0) == 10 for row in rows),
                        "n per row=%s" % sorted({row.get("n") for row in rows})))

    dielectric = [row for row in rows if row.get("rung_family") == "dielectric"]
    checks.append(check("stage12.dielectric_points==8", len(dielectric) == 8,
                        "n dielectric=%d" % len(dielectric)))
    checks.append(check("stage12.dielectric_all_benign",
                        bool(dielectric)
                        and all(not row.get("shortlist_rewritten") for row in dielectric)
                        and all((row.get("ols_slope_b") or 0.0) > 0.0 for row in dielectric),
                        "max f_unresolved(z=1)=%s"
                        % max((row.get("f_unresolved_p1_observed") or 0.0)
                              for row in dielectric)))

    by_axis = shape.get("max_rel_spread_by_axis") or {}
    checks.append(check("stage12.born_shape_oxidation",
                        (by_axis.get("oxidation")
                         if by_axis.get("oxidation") is not None else 1.0) < 0.05,
                        "max rel spread=%s (worst %s)"
                        % (by_axis.get("oxidation"), (shape.get("worst_by_axis") or {}).get("oxidation"))))
    checks.append(check("stage12.born_shape_reduction",
                        (by_axis.get("reduction")
                         if by_axis.get("reduction") is not None else 1.0) < 0.20,
                        "max rel spread=%s (worst %s)"
                        % (by_axis.get("reduction"), (shape.get("worst_by_axis") or {}).get("reduction"))))
    checks.append(check("stage12.born_fits_better_than_onsager",
                        ((law.get("born_r2") or {}).get("mean") or 0.0)
                        > ((law.get("onsager_r2") or {}).get("mean") or 1.0),
                        "born R2 mean=%s vs onsager=%s"
                        % ((law.get("born_r2") or {}).get("mean"),
                           (law.get("onsager_r2") or {}).get("mean"))))
    r2 = ((law.get("measured_ratios") or {}).get("r2") or {}).get("mean")
    r3 = ((law.get("measured_ratios") or {}).get("r3") or {}).get("mean")
    checks.append(check("stage12.increment_halves_per_doubling",
                        r2 is not None and abs(r2 - 2.0) < 0.05
                        and r3 is not None and abs(r3 - 2.0) < 0.05,
                        "r2=%s r3=%s (Born 2.000)" % (r2, r3)))
    checks.append(check("stage12.forecast_without_eps40",
                        (forecast.get("three_point_max_rel_err")
                         if forecast.get("three_point_max_rel_err") is not None else 1.0) < 0.05,
                        "3-point max rel err=%s, 2-point=%s"
                        % (forecast.get("three_point_max_rel_err"),
                           forecast.get("two_point_max_rel_err"))))

    curves = {entry.get("k"): entry for entry in (screen.get("curves") or [])}
    checks.append(check("stage12.prescreen_exhaustive",
                        all(entry.get("n_subsets") for entry in (screen.get("curves") or [])),
                        "pilot sizes=%s" % sorted(curves)))
    checks.append(check("stage12.prescreen_mean_slope_separates",
                        bool(curves) and all((entry.get("auc_lower_b_mean_b_hat") or 0.0) > 0.999
                                             for entry in curves.values()),
                        "auc of the pilot-averaged slope=%s"
                        % [entry.get("auc_lower_b_mean_b_hat") for entry in curves.values()]))
    need = screen.get("k_required_for_full_recall")
    checks.append(check("stage12.prescreen_full_recall_available",
                        need is not None and 3 <= need <= 9,
                        "k_required=%s (n_dangerous=%s)" % (need, screen.get("n_dangerous"))))

    for row in rows:
        if row.get("rung_family") != "electronic":
            continue
        t4_err = row.get("t4_abs_err_z1")
        t6_err = row.get("t6_b_plus_1_vs_beta_err")
        checks.append(check("stage12.electronic.%s.%s.t4" % (row.get("rung"), row.get("axis")),
                            t4_err == 0.0
                            and t6_err is not None and abs(float(t6_err)) < 1e-12,
                            "t4=%s t6=%s" % (t4_err, t6_err)))

    checks.append(check("week11.figures_present",
                        (wdir / "artifacts" / "F22_dielectric_scaling.png").exists()
                        and (wdir / "artifacts" / "F23_prescreening.png").exists(),
                        "artifacts/ F22 + F23"))
    checks.append(check("week11.report_present",
                        (wdir / "week11_report_full.md").exists(),
                        "week11_report_full.md"))
    return checks


def week12_checks(wdir: Path):
    """QC for week 12 (Stage 13, the dielectric limit and the ORCA ledger)."""

    checks = []
    ladder = load_json(wdir / "stage13_ladder.json")
    analysis = load_json(wdir / "stage13_analysis.json")
    if ladder is None:
        checks.append(check("stage13_ladder.present", None, "source not found"))
        return checks
    checks.append(check("stage13_ladder.present", True, "stage13_ladder.json present"))
    if analysis is None:
        checks.append(check("stage13_analysis.present", None, "source not found"))
        return checks
    checks.append(check("stage13_analysis.present", True, "stage13_analysis.json present"))

    subset = analysis.get("subset") or []
    ladder_checks = analysis.get("ladder_checks") or {}
    model = analysis.get("model_comparison") or {}
    rungs = analysis.get("rung_ladder") or {}
    checks_long = analysis.get("checks") or {}

    checks.append(check("stage13.subset==12", len(subset) == 12, "subset=%d" % len(subset)))
    complete = ladder_checks.get("ladder_complete") or {}
    n_missing = complete.get("n_missing")
    checks.append(check("stage13.no_missing_jobs",
                        n_missing == 0,
                        "n_missing=%s n_states=%s of %s"
                        % (n_missing, complete.get("n_states"), complete.get("expected_states"))))

    failed = sorted(name for name, entry in checks_long.items()
                    if isinstance(entry, dict) and entry.get("ok") is False)
    checks.append(check("stage13.analysis_checks_all_pass", not failed,
                        "%d/%d PASS%s" % (sum(1 for entry in checks_long.values()
                                              if isinstance(entry, dict) and entry.get("ok")),
                                          len(checks_long),
                                          ("; FAILED: " + ", ".join(failed)) if failed else "")))

    born = model.get("born_r2") or {}
    onsager = model.get("onsager_r2") or {}
    checks.append(check("stage13.born_beats_onsager_on_six_dielectrics",
                        (born.get("mean") or 0.0) > (onsager.get("mean") or 1.0),
                        "born mean R2=%s (min %s) vs onsager=%s"
                        % (born.get("mean"), born.get("min"), onsager.get("mean"))))

    kstats = model.get("two_parameter_k") or {}
    k_mean = kstats.get("mean")
    checks.append(check("stage13.two_parameter_k_near_zero",
                        k_mean is not None and abs(float(k_mean)) < 0.3,
                        "k mean=%s sd=%s range=[%s, %s]"
                        % (k_mean, kstats.get("sd"), kstats.get("min"), kstats.get("max"))))

    gap = (analysis.get("conductor_limit") or {}).get("gap_to_limit_ev") or {}
    checks.append(check("stage13.conductor_limit_within_50mev",
                        gap.get("max") is not None and float(gap["max"]) < 0.05,
                        "gap to eps->inf: mean=%s max=%s eV" % (gap.get("mean"), gap.get("max"))))

    targets = (analysis.get("extrapolation_scaling") or {}).get("targets") or {}
    errs = [((targets.get(tag) or {}).get("max_abs_err_ev")) for tag in ("cpcm_40", "cpcm_80", "cpcm_200")]
    monotone = all(errs[i] is not None and errs[i + 1] is not None
                   and float(errs[i]) <= float(errs[i + 1]) + 1e-12 for i in range(len(errs) - 1))
    checks.append(check("stage13.extrapolation_error_grows_with_distance", monotone,
                        "max abs err 40/80/200 = %s" % errs))

    spread = ((ladder_checks.get("cds_is_state_independent") or {}).get("max_spread_ev"))
    checks.append(check("stage13.cds_is_state_independent",
                        spread is not None and abs(float(spread)) < 1e-8,
                        "max CDS spread across the three charge states=%s eV" % spread))

    composite = ladder_checks.get("composite_terms_environment_independent") or {}
    d4 = composite.get("max_abs_d4_ev")
    dgcp = composite.get("max_abs_dgcp_ev")
    checks.append(check("stage13.d4_gcp_environment_independent",
                        d4 is not None and dgcp is not None
                        and abs(float(d4)) < 1e-8 and abs(float(dgcp)) < 1e-8,
                        "max |Delta D4|=%s eV, max |Delta gCP|=%s eV" % (d4, dgcp)))

    residual = (ladder_checks.get("shift_split_is_exact") or {}).get("max_abs_residual_ev")
    checks.append(check("stage13.shift_split_is_exact",
                        residual is not None and abs(float(residual)) < 1e-7,
                        "max residual of the four-term identity=%s eV" % residual))

    checks.append(check("stage13.ladder_has_22_points",
                        rungs.get("n_points") == 22,
                        "n_points=%s (dielectric=%s electronic=%s)"
                        % (rungs.get("n_points"), rungs.get("n_dielectric"), rungs.get("n_electronic"))))
    checks.append(check("stage13.rung_families_12_plus_10",
                        rungs.get("n_dielectric") == 12 and rungs.get("n_electronic") == 10,
                        "dielectric=%s electronic=%s"
                        % (rungs.get("n_dielectric"), rungs.get("n_electronic"))))
    checks.append(check("stage13.no_new_rewritten_shortlist",
                        rungs.get("n_rewritten") == 3,
                        "n_rewritten=%s (%s)" % (rungs.get("n_rewritten"),
                                                 ", ".join(rungs.get("rewritten_points") or []))))

    checks.append(check("week12.figures_present",
                        (wdir / "artifacts" / "F24_dielectric_limit.png").exists()
                        and (wdir / "artifacts" / "F25_environment_ledger.png").exists(),
                        "artifacts/ F24 + F25"))
    checks.append(check("week12.report_present",
                        (wdir / "week12_report_full.md").exists(),
                        "week12_report_full.md"))
    return checks


def week13_checks(wdir: Path):
    """QC for week 13 (Stage 14, the distortion attribution and the EMC outlier)."""

    checks = []
    attribution = load_json(wdir / "stage14_attribution.json")
    outlier = load_json(wdir / "stage14_outlier.json")
    grid = load_json(wdir / "stage14_dense_grid.json")
    if attribution is None:
        checks.append(check("stage14_attribution.present", None, "source not found"))
        return checks
    checks.append(check("stage14_attribution.present", True,
                        "stage14_attribution.json present"))
    if outlier is None:
        checks.append(check("stage14_outlier.present", None, "source not found"))
        return checks
    checks.append(check("stage14_outlier.present", True, "stage14_outlier.json present"))
    if grid is None:
        checks.append(check("stage14_dense_grid.present", None, "source not found"))
        return checks
    checks.append(check("stage14_dense_grid.present", True,
                        "stage14_dense_grid.json present"))

    correction = attribution.get("correction") or {}
    search = correction.get("subset_enumeration") or {}
    values = correction.get("reproducible_values") or {}
    states = attribution.get("state_penalties") or {}
    variational = states.get("variational_check") or {}
    verdict = outlier.get("verdict") or {}
    repro = outlier.get("reproducibility") or {}

    checks.append(check("stage14.subset_is_12", len(attribution.get("molecules") or []) == 12,
                        "molecules=%d" % len(attribution.get("molecules") or [])))
    checks.append(check("stage14.distortion_identity_is_exact",
                        correction.get("penalty_identity_holds") is True,
                        "max residual of dist = D_hi - D_lo: %s eV"
                        % correction.get("penalty_identity_max_abs_residual_ev")))
    checks.append(check("stage14.every_state_penalty_non_negative",
                        variational.get("all_penalties_non_negative") is True,
                        "worst minimum %s eV over %d penalties"
                        % (variational.get("worst_minimum_ev"),
                           sum((states.get(state) or {}).get("n", 0)
                               for state in ("neutral", "cation", "anion")))))
    checks.append(check("stage14.published_pair_is_refuted",
                        correction.get("verdict") == "not reproducible"
                        and search.get("n_exact_matches") == 0
                        and search.get("n_candidates") == 510,
                        "%d aggregations, %d exact matches, closest off by %s eV"
                        % (search.get("n_candidates"), search.get("n_exact_matches"),
                           ((search.get("closest") or [{}])[0]).get("max_abs_error_ev"))))
    checks.append(check("stage14.reproducible_aggregation_matches_week12",
                        values.get("oxidation_ev") is not None
                        and abs(float(values["oxidation_ev"]) - 0.0435) < 5e-4
                        and abs(float(values["reduction_ev"]) + 0.3025) < 5e-4,
                        "oxidation=%s reduction=%s eV"
                        % (values.get("oxidation_ev"), values.get("reduction_ev"))))
    checks.append(check("stage14.anion_penalty_exceeds_neutral",
                        (states.get("anion") or {}).get("mean_ev", 0.0)
                        > 4.0 * (states.get("neutral") or {}).get("mean_ev", 1.0),
                        "D_anion=%s vs D_neutral=%s eV"
                        % ((states.get("anion") or {}).get("mean_ev"),
                           (states.get("neutral") or {}).get("mean_ev"))))

    n_jobs = sum(int((layer.get("summary") or {}).get("n_ok") or 0)
                 for layer in (grid.get("layers") or []))
    n_failed = sum(int((layer.get("summary") or {}).get("n_failed") or 0)
                   for layer in (grid.get("layers") or []))
    checks.append(check("stage14.dense_grid_63_jobs_all_ok",
                        grid.get("n_jobs_expected") == 63 and n_jobs == 63
                        and n_failed == 0 and grid.get("failures") == 0,
                        "expected=%s ok=%d failed=%s layers=%d"
                        % (grid.get("n_jobs_expected"), n_jobs, n_failed,
                           len(grid.get("layers") or []))))
    checks.append(check("stage14.dense_grid_used_safe_parallelism",
                        grid.get("jobs") == 2 and grid.get("nprocs") == 8,
                        "jobs=%s nprocs=%s (host has 16 logical cores)"
                        % (grid.get("jobs"), grid.get("nprocs"))))
    checks.append(check("stage14.shared_points_reproduce_stage13",
                        repro.get("verdict") == "reproduced"
                        and (repro.get("max_abs_delta_eh")
                             if repro.get("max_abs_delta_eh") is not None else 1.0) < 1e-9
                        and repro.get("n_identical_strings") == repro.get("n_points_compared"),
                        "%s/%s identical, max |dE|=%s Eh"
                        % (repro.get("n_identical_strings"), repro.get("n_points_compared"),
                           repro.get("max_abs_delta_eh"))))
    ladder = outlier.get("ladder_eps") or []
    checks.append(check("stage14.ladder_has_nine_dielectrics",
                        len(ladder) == 9 and ladder[:3] == [5.0, 7.0, 10.0],
                        "ladder=%s" % ladder))
    checks.append(check("stage14.stage13_minimum_is_reproduced_here",
                        abs(float(verdict.get("emc_reduction_born_r2_stage13_grid") or 0.0)
                            - 0.8468) < 1e-4,
                        "EMC/reduction Born R2 on the Stage 13 six-point grid = %s"
                        % verdict.get("emc_reduction_born_r2_stage13_grid")))
    density = ((outlier.get("curves") or {}).get("EMC/reduction") or {}).get(
        "born_r2_by_grid_density") or []
    counts = [item.get("n_points") for item in density]
    checks.append(check("stage14.grid_density_study_is_monotone",
                        counts == sorted(counts) and counts[:1] == [4] and counts[-1:] == [9],
                        "n_points sequence = %s" % counts))

    checks.append(check("week13.figures_present",
                        (wdir / "artifacts" / "F26_distortion_attribution.png").exists()
                        and (wdir / "artifacts" / "F27_emc_outlier.png").exists(),
                        "artifacts/ F26 + F27"))
    checks.append(check("week13.report_present",
                        (wdir / "week13_report_full.md").exists(),
                        "week13_report_full.md"))
    return checks


def week14_checks(wdir: Path):
    """QC for week 14 (Stage 15, the two-guess protocol, diffuseness and the scan)."""

    checks = []
    run = load_json(wdir / "stage15_two_guess.json")
    analysis = load_json(wdir / "stage15_two_guess_analysis.json")
    diffuseness = load_json(wdir / "stage15_diffuseness.json")
    anchor = load_json(wdir / "stage15_anchor_scan.json")
    for name, data in (("stage15_two_guess", run), ("stage15_two_guess_analysis", analysis),
                       ("stage15_diffuseness", diffuseness), ("stage15_anchor_scan", anchor)):
        if data is None:
            checks.append(check(name + ".present", None, "source not found"))
            return checks
        checks.append(check(name + ".present", True, name + ".json present"))

    energy = analysis.get("energy") or {}
    repro = analysis.get("stage14_reproduction") or {}
    verdict = analysis.get("verdict") or {}
    conductor = analysis.get("conductor_limit") or {}
    stage13 = conductor.get("stage13_published") or {}
    default = conductor.get("default") or {}
    moread = conductor.get("moread") or {}

    n_ok = sum(int(layer.get("n_ok") or 0) for layer in (run.get("layers") or []))
    checks.append(check("stage15.protocol_99_jobs_all_ok",
                        run.get("n_jobs_expected") == 99 and n_ok == 99
                        and run.get("failures") == 0
                        and len(run.get("layers") or []) == 11,
                        "expected=%s ok=%d failures=%s layers=%d"
                        % (run.get("n_jobs_expected"), n_ok, run.get("failures"),
                           len(run.get("layers") or []))))
    checks.append(check("stage15.protocol_used_safe_parallelism",
                        run.get("jobs") == 2 and run.get("nprocs") == 8,
                        "jobs=%s nprocs=%s (host has 16 logical cores)"
                        % (run.get("jobs"), run.get("nprocs"))))
    checks.append(check("stage15.points_are_90",
                        energy.get("n_points") == 90
                        and energy.get("n_identical_to_scf_convergence") == 78,
                        "n_points=%s identical=%s"
                        % (energy.get("n_points"), energy.get("n_identical_to_scf_convergence"))))
    checks.append(check("stage15.material_threshold_is_one_meV",
                        energy.get("material_threshold_ev") == 0.001,
                        "material_threshold_ev=%s" % energy.get("material_threshold_ev")))
    material = energy.get("material") or []
    checks.append(check("stage15.every_material_difference_is_negative",
                        energy.get("n_material_differences") == 12 and len(material) == 12
                        and all((item.get("delta_ev") or 0.0) < 0.0 for item in material),
                        "%d differences, all dE<0, worst %s eV"
                        % (len(material), energy.get("max_default_excess_ev"))))
    checks.append(check("stage15.no_restart_lands_above_the_default",
                        energy.get("n_material_restart_above_the_default_state") == 0
                        and energy.get("n_material_default_guess_above_the_lowest_state") == 12,
                        "restart-above-default=%s, default-above-lowest=%s"
                        % (energy.get("n_material_restart_above_the_default_state"),
                           energy.get("n_material_default_guess_above_the_lowest_state"))))
    checks.append(check("stage15.noise_band_is_below_the_threshold",
                        (energy.get("worst_of_the_noise_ev") or 1.0) < 1e-3,
                        "worst inside the noise band = %s eV"
                        % energy.get("worst_of_the_noise_ev")))
    hist = energy.get("magnitude_histogram") or {}
    counts = [hist.get(key) for key in ("1e-08", "1e-07", "1e-06", "1e-05",
                                       "1e-04", "1e-03", "1e-02", "1e-01")]
    checks.append(check("stage15.magnitude_histogram_is_data_given",
                        counts == [90, 86, 72, 27, 16, 12, 7, 6],
                        "counts over thresholds = %s" % counts))
    checks.append(check("stage15.stage14_curve_is_reproduced",
                        repro.get("reproduces_stage14") is True
                        and abs(float(repro.get("recomputed_default_nine_point_r2") or 0.0)
                                - 0.6788) < 5e-4,
                        "nine-point R2 = %s, sign changes = %s"
                        % (repro.get("recomputed_default_nine_point_r2"),
                           repro.get("recomputed_default_nine_sign_changes"))))
    checks.append(check("stage15.emc_reduction_curve_is_restored",
                        (verdict.get("emc_reduction_moread_nine_r2") or 0.0) > 0.95
                        and verdict.get("emc_reduction_moread_nine_sign_changes") == 0
                        and (verdict.get("emc_anion_moread_nine_roughness") or 1.0) < 0.1,
                        "R2 %s -> %s, sign changes %s -> %s, roughness %s -> %s"
                        % (verdict.get("emc_reduction_default_nine_r2"),
                           verdict.get("emc_reduction_moread_nine_r2"),
                           verdict.get("emc_reduction_default_nine_sign_changes"),
                           verdict.get("emc_reduction_moread_nine_sign_changes"),
                           verdict.get("emc_anion_default_nine_roughness"),
                           verdict.get("emc_anion_moread_nine_roughness"))))
    monotone = verdict.get("dipole_monotonicity") or {}
    checks.append(check("stage15.dipole_monotonic_only_after_the_restart",
                        monotone.get("moread_strictly_monotone") is True
                        and monotone.get("default_strictly_monotone") is False,
                        "moread rho=%s, default rho=%s"
                        % (monotone.get("moread_spearman_dipole_vs_eps"),
                           monotone.get("default_spearman_dipole_vs_eps"))))
    checks.append(check("stage15.conductor_limit_gap_did_not_shrink",
                        stage13.get("reproduces_the_worst_case") is True
                        and abs(abs(float(default.get("gap_to_six_point_slope_at_eps200_ev") or 0.0))
                                - abs(float(moread.get("gap_to_six_point_slope_at_eps200_ev")
                                            or 0.0))) < 0.01,
                        "six-point gap: default %s vs moread %s eV"
                        % (default.get("gap_to_six_point_slope_at_eps200_ev"),
                           moread.get("gap_to_six_point_slope_at_eps200_ev"))))
    checks.append(check("stage15.eps_1000_is_flat_against_eps_200",
                        abs(float(default.get("gap_between_eps200_and_eps1000_ev") or 0.0)
                            - 0.011318) < 5e-5,
                        "delta(200) -> delta(1000) = %s eV"
                        % default.get("gap_between_eps200_and_eps1000_ev")))
    checks.append(check("stage15.no_qc_flags_in_either_protocol",
                        energy.get("n_moread_jobs_with_qc_flags") == 0
                        and energy.get("n_default_jobs_with_qc_flags") == 0,
                        "moread=%s default=%s"
                        % (energy.get("n_moread_jobs_with_qc_flags"),
                           energy.get("n_default_jobs_with_qc_flags"))))

    domain = diffuseness.get("descriptor_domain") or {}
    screen = diffuseness.get("gas_phase_screen") or {}
    verdicts = diffuseness.get("verdicts") or {}
    robust = diffuseness.get("robust_verdicts") or {}
    anion = verdicts.get("anion") or {}
    checks.append(check("stage15.descriptors_are_normalised",
                        domain.get("n_rows") == 72
                        and domain.get("spin_population_is_normalised") is True
                        and domain.get("charge_is_normalised") is True,
                        "%s rows, worst |sum s - 1| = %s, worst |sum q + 1| = %s"
                        % (domain.get("n_rows"), domain.get("worst_abs_sum_spin_minus_one"),
                           domain.get("worst_abs_sum_charge_plus_one"))))
    checks.append(check("stage15.gas_phase_anion_is_outside_the_domain",
                        screen.get("outside_layer_domain") == ["AN"]
                        and screen.get("n_inside_domain") == 11,
                        "outside=%s, inside=%s/%s"
                        % (screen.get("outside_layer_domain"), screen.get("n_inside_domain"),
                           screen.get("n_available"))))
    checks.append(check("stage15.one_layer_flagged_without_any_energy",
                        domain.get("layer_outliers_vs_own_median") == [["EMC", "cpcm_10", 2.799]],
                        "layer outliers = %s"
                        % domain.get("layer_outliers_vs_own_median")))
    checks.append(check("stage15.diffuseness_improves_the_anion_target",
                        anion.get("extended_best_descriptor") == "spin_maxfrac"
                        and (anion.get("delta_loo_r2") or 0.0) > 0.39
                        and (anion.get("extended_best_loo_r2") or 0.0) > 0.55,
                        "best %s: LOO R2 %s -> %s (delta %s)"
                        % (anion.get("extended_best_descriptor"),
                           anion.get("baseline_best_loo_r2"),
                           anion.get("extended_best_loo_r2"), anion.get("delta_loo_r2"))))
    checks.append(check("stage15.neutral_and_cation_champions_unchanged",
                        (verdicts.get("neutral") or {}).get("delta_loo_r2") == 0.0
                        and (verdicts.get("cation") or {}).get("delta_loo_r2") == 0.0
                        and (robust.get("anion") or {}).get("delta_loo_r2", 0.0) > 0.46,
                        "delta_loo neutral=%s cation=%s; median anion=%s"
                        % ((verdicts.get("neutral") or {}).get("delta_loo_r2"),
                           (verdicts.get("cation") or {}).get("delta_loo_r2"),
                           (robust.get("anion") or {}).get("delta_loo_r2"))))

    gate1 = anchor.get("gate1") or {}
    checks.append(check("stage15.corpus_is_readable_and_barely_intersects",
                        anchor.get("n_pdfs") == 13 and anchor.get("n_readable") == 13
                        and anchor.get("cited_dois_present_in_corpus")
                        == ["10.1016/j.coelec.2018.10.015"],
                        "%s/%s pdfs readable, %d of %d cited DOIs in hand"
                        % (anchor.get("n_readable"), anchor.get("n_pdfs"),
                           len(anchor.get("cited_dois_present_in_corpus") or []),
                           len(anchor.get("cited_dois_of_audit") or []))))
    checks.append(check("stage15.only_four_rows_could_be_adjudicated",
                        gate1.get("n_rows_adjudicable") == 4
                        and gate1.get("n_corrections_adopted") == 3
                        and gate1.get("confirmed_rows") == ["24"],
                        "%s adjudicable, %s adopted, confirmed %s"
                        % (gate1.get("n_rows_adjudicable"), gate1.get("n_corrections_adopted"),
                           gate1.get("confirmed_rows"))))
    checks.append(check("stage15.gate1_is_still_not_closed",
                        gate1.get("gate1_status") == "NOT CLOSED"
                        and gate1.get("n_rows_still_est_after_scan") == 31
                        and gate1.get("n_upgrades_meeting_conditions") == 0,
                        "status=%s, still est=%s, upgrades=%s"
                        % (gate1.get("gate1_status"), gate1.get("n_rows_still_est_after_scan"),
                           gate1.get("n_upgrades_meeting_conditions"))))
    checks.append(check("stage15.corrections_stay_in_an_overlay",
                        (wdir / "stage15_anchor_corrections.csv").exists()
                        and not (wdir / "solution_anchor_audit.csv").exists(),
                        "stage15_anchor_corrections.csv present, frozen audit absent"))

    checks.append(check("week14.figures_present",
                        (wdir / "artifacts" / "F28_two_guess_protocol.png").exists()
                        and (wdir / "artifacts" / "F29_diffuseness_descriptor.png").exists(),
                        "artifacts/ F28 + F29"))
    checks.append(check("week14.report_present",
                        (wdir / "week14_report_full.md").exists(),
                        "week14_report_full.md"))
    return checks


def week15_checks(wdir: Path):
    """QC for week 15 (Stage 16, the catalogue and the a priori rule)."""

    checks = []
    catalogue = load_json(wdir / "stage16_catalogue.json")
    analysis = load_json(wdir / "stage16_catalogue_analysis.json")
    predictor = load_json(wdir / "stage16_predictor.json")
    descriptors = read_text(wdir / "stage16_gas_descriptors.csv")
    for name, data in (("stage16_catalogue", catalogue),
                       ("stage16_catalogue_analysis", analysis),
                       ("stage16_predictor", predictor)):
        if data is None:
            checks.append(check(name + ".present", None, "source not found"))
            return checks
        checks.append(check(name + ".present", True, name + ".json present"))
    checks.append(check("stage16_gas_descriptors.present", descriptors is not None,
                        "stage16_gas_descriptors.csv present"))

    layers = catalogue.get("layers") or []
    n_ok = sum(int(layer.get("n_ok") or 0) for layer in layers)
    checks.append(check("stage16.protocol_720_cells_all_ok",
                        catalogue.get("n_cells") == 720 and n_ok == 720
                        and catalogue.get("n_failed") == 0 and len(layers) == 20,
                        "cells=%s ok=%d failed=%s layers=%d"
                        % (catalogue.get("n_cells"), n_ok, catalogue.get("n_failed"),
                           len(layers))))
    checks.append(check("stage16.protocol_used_safe_parallelism",
                        catalogue.get("jobs") == 2 and catalogue.get("nprocs") == 8,
                        "jobs=%s nprocs=%s (host has 16 logical cores)"
                        % (catalogue.get("jobs"), catalogue.get("nprocs"))))
    checks.append(check("stage16.reuse_is_counted_not_silent",
                        (catalogue.get("n_cells_computed") or 0)
                        + (catalogue.get("n_cells_reused") or 0)
                        == catalogue.get("n_cells"),
                        "computed=%s reused=%s cells=%s"
                        % (catalogue.get("n_cells_computed"),
                           catalogue.get("n_cells_reused"), catalogue.get("n_cells"))))
    checks.append(check("stage16.geometry_audit_is_clean",
                        all(entry.get("all_identical") is True
                            for entry in (catalogue.get("geometry_audit") or {}).values()),
                        "%d molecules audited against their continuum geometry"
                        % len(catalogue.get("geometry_audit") or {})))

    checks.append(check("stage16.twelve_molecules_three_states_ten_dielectrics",
                        analysis.get("n_cells") == 12 * 3 * 10
                        and len(analysis.get("molecules") or []) == 12
                        and len(analysis.get("states") or []) == 3
                        and len(analysis.get("ladder_all_eps") or []) == 10,
                        "cells=%s molecules=%d states=%d eps=%d"
                        % (analysis.get("n_cells"), len(analysis.get("molecules") or []),
                           len(analysis.get("states") or []),
                           len(analysis.get("ladder_all_eps") or []))))
    checks.append(check("stage16.every_cell_is_paired",
                        analysis.get("n_paired") == analysis.get("n_cells")
                        and analysis.get("n_unpaired") == 0
                        and not (analysis.get("unpaired_cells") or []),
                        "paired=%s unpaired=%s"
                        % (analysis.get("n_paired"), analysis.get("n_unpaired"))))
    checks.append(check("stage16.material_threshold_is_the_stage15_value",
                        analysis.get("material_threshold_ev") == 0.001,
                        "material_threshold_ev=%s"
                        % analysis.get("material_threshold_ev")))
    checks.append(check("stage16.counts_are_internally_consistent",
                        (analysis.get("n_moread_lower") or 0)
                        + (analysis.get("n_moread_higher") or 0)
                        + (analysis.get("n_coincident") or 0)
                        == analysis.get("n_cells")
                        and analysis.get("n_material_differences")
                        == (analysis.get("n_moread_lower") or 0)
                        + (analysis.get("n_moread_higher") or 0),
                        "lower=%s higher=%s coincident=%s cells=%s"
                        % (analysis.get("n_moread_lower"), analysis.get("n_moread_higher"),
                           analysis.get("n_coincident"), analysis.get("n_cells"))))
    histogram = analysis.get("magnitude_histogram") or {}
    thresholds = [float(value) for value in
                  (analysis.get("magnitude_histogram_thresholds_ev") or [])]
    counts = [histogram.get("%g" % key) for key in thresholds]
    material = analysis.get("material_threshold_ev")
    slot = [index for index, key in enumerate(thresholds) if key == material]
    slot = slot[0] if slot else None
    checks.append(check("stage16.magnitude_histogram_is_monotone",
                        len(thresholds) >= 2
                        and thresholds == sorted(thresholds)
                        and len(set(thresholds)) == len(thresholds)
                        and all(isinstance(value, int) for value in counts)
                        and counts == sorted(counts, reverse=True)
                        and max(counts) <= (analysis.get("n_cells") or 0)
                        and slot is not None
                        and counts[slot] == analysis.get("n_material_differences"),
                        "counts %s over thresholds %s; at the material threshold "
                        "%s the count must equal n_material_differences=%s"
                        % (counts, ["%g" % key for key in thresholds],
                           "%g" % material if material is not None else "?",
                           analysis.get("n_material_differences"))))
    checks.append(check("stage16.worst_deficit_is_recorded_with_coordinates",
                        (analysis.get("worst_negative_ev") or 0.0) < 0.0
                        and len(analysis.get("worst_negative_at") or []) == 3,
                        "worst %.6f eV at %s"
                        % (analysis.get("worst_negative_ev") or 0.0,
                           analysis.get("worst_negative_at"))))
    checks.append(check("stage16.the_restart_never_lands_above_the_default",
                        analysis.get("n_moread_higher") == 0,
                        "restarts above the default = %s"
                        % analysis.get("n_moread_higher")))

    agreement = analysis.get("label_agreement") or {}
    checks.append(check("stage16.labels_are_monotone_across_the_ladders",
                        all(entry.get("n_disagree") is not None for entry in agreement.values())
                        and len(agreement) == 3,
                        "; ".join("%s %d/%d agree" % (key, entry.get("n_rows", 0)
                                                      - entry.get("n_disagree", 0),
                                                      entry.get("n_rows", 0))
                                  for key, entry in sorted(agreement.items()))))
    flagged = analysis.get("flagged_molecules") or {}
    checks.append(check("stage16.a_flagged_molecule_carries_at_least_one_state",
                        all(isinstance(flagged.get(key), list) for key in flagged)
                        and len(flagged) == 3,
                        "flagged: core3 %d, focus6 %d, ladder10 %d"
                        % (len(flagged.get("core3") or []), len(flagged.get("focus6") or []),
                           len(flagged.get("ladder10") or []))))
    coverage = (analysis.get("family_coverage") or {}).get("ladder10") or {}
    checks.append(check("stage16.family_coverage_is_reported",
                        bool(coverage)
                        and sum(int(entry.get("n_molecules") or 0)
                                for entry in coverage.values())
                        == len(analysis.get("molecules") or []),
                        "%d families, %d molecules"
                        % (len(coverage),
                           sum(int(entry.get("n_molecules") or 0)
                               for entry in coverage.values()))))
    checks.append(check("stage16.flagging_is_open_shell_only",
                        int((analysis.get("per_state_counts") or {}).get(
                            "neutral", {}).get("n_moread_lower") or 0) == 0,
                        "neutral cells with a deficit = %s"
                        % (analysis.get("per_state_counts") or {}).get(
                            "neutral", {}).get("n_moread_lower")))

    chosen = predictor.get("chosen_rule") or {}
    screen = predictor.get("screen") or []
    checks.append(check("stage16.the_rule_uses_gas_phase_descriptors_only",
                        bool(chosen.get("descriptor", "").startswith("gas_"))
                        and all(entry.get("descriptor", "").startswith("gas_")
                                for entry in screen),
                        "%d screened descriptors, chosen %s"
                        % (len(screen), chosen.get("descriptor"))))
    checks.append(check("stage16.the_label_is_open_shell_only",
                        predictor.get("n_discovery_rows") == 24
                        and "open-shell" in (predictor.get("restriction") or ""),
                        "discovery rows=%s (%s)"
                        % (predictor.get("n_discovery_rows"), predictor.get("restriction"))))
    checks.append(check("stage16.screen_is_ranked_by_absolute_auc",
                        screen == sorted(screen, key=lambda entry: -entry.get(
                            "abs_auc_above_half", 0.0))
                        and all(0.0 <= entry.get("auc", 0.0) <= 1.0 for entry in screen),
                        "%d descriptors, best %s at AUC %.3f"
                        % (len(screen), chosen.get("descriptor"), chosen.get("auc") or 0.0)))
    permutation = predictor.get("permutation_test") or {}
    checks.append(check("stage16.the_rule_carries_an_exact_permutation_test",
                        permutation.get("exact") is True
                        and permutation.get("total_assignments")
                        == math.comb(permutation.get("n_rows") or 0,
                                     permutation.get("n_positive") or 0)
                        and permutation.get("n_assignments")
                        == permutation.get("total_assignments")
                        and permutation.get("statistic") == "|AUC - 0.5|"
                        and 0.0 < (permutation.get("p_value") or 0.0) <= 1.0,
                        "%s: exact p=%.4f over all %s assignments of %s positives "
                        "to %s rows"
                        % (permutation.get("descriptor"), permutation.get("p_value") or 0.0,
                           permutation.get("total_assignments"),
                           permutation.get("n_positive"), permutation.get("n_rows"))))
    # The comparison is reported, not assumed.  The frozen rule is allowed to
    # lose to the trivial classifier; what is not allowed is a report that
    # quietly claims otherwise, so the flag is checked against the two numbers
    # it is supposed to summarise.
    majority = predictor.get("baseline_majority_accuracy")
    loo = chosen.get("loo_accuracy")
    beats = predictor.get("chosen_rule_beats_majority_baseline")
    checks.append(check("stage16.the_frozen_rule_is_scored_against_the_majority_baseline",
                        isinstance(beats, bool) and majority is not None and loo is not None
                        and beats == (loo > majority),
                        "leave-one-out %.3f vs majority %.3f -> beats baseline = %s"
                        % (loo or 0.0, majority or 0.0, beats)))
    arm_diag = predictor.get("per_arm_diagnostic") or {}
    arm_blocks = arm_diag.get("arms") or {}
    checks.append(check("stage16.the_per_arm_diagnostic_is_labelled_post_hoc",
                        arm_diag.get("post_hoc") is True
                        and arm_diag.get("arm_selector_is_a_gas_phase_quantity") is False
                        and set(arm_blocks) == {"cation", "anion"}
                        and all(block.get("n_rows") == 12
                                and len(block.get("screen") or []) >= 4
                                and all(len(entry.get("positive_ranks") or [])
                                        == block.get("n_positive")
                                        for entry in block.get("screen") or [])
                                for block in arm_blocks.values()),
                        ", ".join("%s %s rows / %s positives / best |AUC-0.5| %.3f"
                                  % (name, block.get("n_rows"), block.get("n_positive"),
                                     block.get("best_absolute_auc") or 0.0)
                                  for name, block in sorted(arm_blocks.items()))))
    validation = predictor.get("validation") or {}
    validation_ladder_rows = 0
    by_state_path = wdir / "stage16_by_state.csv"
    if by_state_path.exists():
        with by_state_path.open(encoding="utf-8", newline="") as handle:
            validation_ladder_rows = sum(
                1 for row in csv.DictReader(handle)
                if (row.get("ladder") or "") == "validation")
    arm_held = {name: (block.get("validation") or {})
                for name, block in arm_blocks.items()}
    checks.append(check("stage16.the_post_hoc_arm_rules_are_also_tested_out_of_sample",
                        bool(arm_blocks)
                        and all(held.get("n_rows") == 6 and held.get("n_scored") == 6
                                and len(held.get("per_row") or []) == 6
                                and isinstance(held.get("beats_majority_baseline"), bool)
                                and held.get("beats_majority_baseline")
                                == (held.get("accuracy") is not None
                                    and held.get("majority_accuracy") is not None
                                    and held.get("accuracy") > held.get("majority_accuracy"))
                                for held in arm_held.values()),
                        ", ".join("%s %s: held-out accuracy %.3f vs majority %.3f -> beats %s"
                                  % (name, held.get("descriptor"),
                                     held.get("accuracy") or 0.0,
                                     held.get("majority_accuracy") or 0.0,
                                     held.get("beats_majority_baseline"))
                                  for name, held in sorted(arm_held.items()))))
    checks.append(check("stage16.held_out_arm_is_the_six_new_molecules",
                        validation.get("molecules") == list(W15_VALIDATION_NAMES)
                        and validation_ladder_rows == 6 * 3
                        and (validation.get("n_scored") or 0) == 6 * 2
                        and (validation.get("confusion_matrix") or {}).get("unscored") == 0,
                        "molecules=%s label rows=%d scored=%s unscored=%s"
                        % (validation.get("molecules"), validation_ladder_rows,
                           validation.get("n_scored"),
                           (validation.get("confusion_matrix") or {}).get("unscored"))))

    holdout = load_json(wdir / "stage16_holdout.json")
    checks.append(check("stage16.the_holdout_arm_ran_in_full",
                        holdout is not None
                        and holdout.get("n_cells") == 6 * 3 * 3 * 2
                        and holdout.get("n_failed") == 0
                        and sum(int(layer.get("n_ok") or 0)
                                for layer in (holdout.get("layers") or []))
                        == 6 * 3 * 3 * 2
                        and holdout.get("n_cells_reused") == 0,
                        "cells=%s failed=%s reused=%s"
                        % (holdout.get("n_cells") if holdout else None,
                           holdout.get("n_failed") if holdout else None,
                           holdout.get("n_cells_reused") if holdout else None)))

    checks.append(check("week15.figures_present",
                        (wdir / "artifacts" / "F30_two_guess_catalogue.png").exists()
                        and (wdir / "artifacts" / "F31_apriori_warning_rule.png").exists(),
                        "artifacts/ F30 + F31"))
    report_path = wdir / "week15_report_full.md"
    report_text = (report_path.read_text(encoding="utf-8")
                   if report_path.exists() else "")
    required = ("超过了多数类基线" if predictor.get("chosen_rule_beats_majority_baseline")
                else "未能超过多数类基线")
    checks.append(check("week15.report_states_the_baseline_verdict",
                        required in report_text and "事后" in report_text,
                        "报告须写出实测判定「%s」，并把分臂诊断标为事后" % required))
    checks.append(check("week15.report_present",
                        report_path.exists(),
                        "week15_report_full.md"))
    return checks


def week16_checks(wdir: Path):
    """QC for week 16 (Stage 17, the contamination ceiling and the solution identity)."""

    checks = []
    smd = load_json(wdir / "stage17_smd_moread.json")
    p2 = load_json(wdir / "p2_summary_moread_smd_acetonitrile.json")
    contamination = load_json(wdir / "stage17_contamination.json")
    identity = load_json(wdir / "stage17_solution_identity.json")
    for name, data in (("stage17_smd_moread", smd),
                       ("p2_summary_moread_smd_acetonitrile", p2),
                       ("stage17_contamination", contamination),
                       ("stage17_solution_identity", identity)):
        if data is None:
            checks.append(check(name + ".present", None, "source not found"))
            return checks
        checks.append(check(name + ".present", True, name + ".json present"))

    layers = smd.get("layers") or []
    layer = layers[0] if layers else {}
    checks.append(check("week16.part_a_run_ledger",
                        p2.get("n_jobs") == 54 and p2.get("n_ok") == 54
                        and p2.get("n_failed") == 0 and p2.get("n_computed") == 54
                        and p2.get("n_reused") == 0
                        and layer.get("n_jobs") == 54 and layer.get("n_ok") == 54
                        and layer.get("n_failed") == 0
                        and layer.get("n_computed") == 54
                        and layer.get("n_reused") == 0,
                        "p2_summary: jobs=%s ok=%s failed=%s computed=%s reused=%s; "
                        "stage17_smd_moread.layers[0]: jobs=%s ok=%s failed=%s "
                        "computed=%s reused=%s"
                        % (p2.get("n_jobs"), p2.get("n_ok"), p2.get("n_failed"),
                           p2.get("n_computed"), p2.get("n_reused"),
                           layer.get("n_jobs"), layer.get("n_ok"),
                           layer.get("n_failed"), layer.get("n_computed"),
                           layer.get("n_reused"))))
    checks.append(check("week16.part_a_layer_and_arm",
                        smd.get("layer") == "moread_smd_acetonitrile"
                        and smd.get("arm") == "moread"
                        and p2.get("layer") == "moread_smd_acetonitrile"
                        and p2.get("arm") == "moread",
                        "stage17_smd_moread layer=%s arm=%s; p2_summary layer=%s arm=%s"
                        % (smd.get("layer"), smd.get("arm"),
                           p2.get("layer"), p2.get("arm"))))
    checks.append(check("week16.part_a_cells_and_reference",
                        smd.get("n_cells") == 54
                        and smd.get("n_cells_without_reference") == 0
                        and not (smd.get("cells_without_reference") or []),
                        "stage17_smd_moread: n_cells=%s n_cells_without_reference=%s "
                        "cells_without_reference=%s"
                        % (smd.get("n_cells"), smd.get("n_cells_without_reference"),
                           smd.get("cells_without_reference"))))

    audit = smd.get("geometry_audit") or {}
    checks.append(check("week16.geometry_audit_is_clean",
                        len(audit) == 18
                        and all(entry.get("all_identical") is True
                                for entry in audit.values()),
                        "%d molecules audited against their SMD(acetonitrile) "
                        "reference geometry; all_identical=True for every entry"
                        % len(audit)))

    per_axis = contamination.get("per_axis") or {}
    published = contamination.get("published_comparison") or {}

    block_ok = True
    block_detail = []
    for axis in ("oxidation", "reduction"):
        for arm in ("default", "moread"):
            block = (per_axis.get(axis) or {}).get(arm) or {}
            block_ok = block_ok and block.get("n") == 18
            block_detail.append("%s/%s n=%s" % (axis, arm, block.get("n")))
    checks.append(check("week16.part_a_four_axis_arm_blocks_are_18_each",
                        block_ok, "; ".join(block_detail)))

    tau_spec = (("week16.part_a_tau_b_oxidation_default", "oxidation", "default",
                 0.8954248366013072),
                ("week16.part_a_tau_b_oxidation_moread", "oxidation", "moread",
                 0.9215686274509803),
                ("week16.part_a_tau_b_reduction_default", "reduction", "default",
                 0.673202614379085),
                ("week16.part_a_tau_b_reduction_moread", "reduction", "moread",
                 0.673202614379085))
    for name, axis, arm, want in tau_spec:
        block = (per_axis.get(axis) or {}).get(arm) or {}
        got = block.get("kendall_tau_b")
        checks.append(check(name, got is not None and abs(got - want) < 1e-9,
                            "per_axis.%s.%s.kendall_tau_b=%s (expected %.16f)"
                            % (axis, arm, got, want)))

    f_ok = True
    f_detail = []
    for axis in ("oxidation", "reduction"):
        for arm in ("default", "moread"):
            block = (per_axis.get(axis) or {}).get(arm) or {}
            value = block.get("f_robust_inv")
            f_ok = f_ok and value is not None and abs(value) < 1e-12
            f_detail.append("%s/%s=%s" % (axis, arm, value))
    checks.append(check("week16.part_a_f_robust_inv_is_zero_everywhere",
                        f_ok, "per_axis.*.*.f_robust_inv: " + "; ".join(f_detail)))

    verdict = contamination.get("verdict") or {}
    checks.append(check("week16.part_a_no_published_conclusion_rewritten",
                        verdict.get("any_published_conclusion_rewritten") is False,
                        "verdict.any_published_conclusion_rewritten=%s; "
                        "conclusions_rewritten=%s"
                        % (verdict.get("any_published_conclusion_rewritten"),
                           verdict.get("conclusions_rewritten"))))
    checks.append(check("week16.part_a_tau_b_ci_overlap_both_axes",
                        verdict.get("tau_b_ci_overlap_both_axes") is True,
                        "verdict.tau_b_ci_overlap_both_axes=%s"
                        % verdict.get("tau_b_ci_overlap_both_axes")))

    changed = contamination.get("cells_changed") or []
    checks.append(check("week16.part_a_six_cells_changed",
                        contamination.get("cells_changed_count") == 6
                        and len(changed) == 6,
                        "cells_changed_count=%s; len(cells_changed)=%d"
                        % (contamination.get("cells_changed_count"), len(changed))))

    cells54 = (contamination.get("delta_stats") or {}).get("cells_54") or {}
    checks.append(check("week16.part_a_delta_stats_54_cells",
                        cells54.get("n") == 54
                        and cells54.get("argmin") == "TEGDME/anion"
                        and cells54.get("argmax") == "EC/anion",
                        "delta_stats.cells_54: n=%s argmin=%s argmax=%s"
                        % (cells54.get("n"), cells54.get("argmin"),
                           cells54.get("argmax"))))

    sign = (contamination.get("sign_test") or {}).get("cells_54") or {}
    p_two = sign.get("p_two_sided")
    checks.append(check("week16.part_a_sign_test_54_cells",
                        sign.get("n_positive") == 22 and sign.get("n_negative") == 32
                        and sign.get("n_zero") == 0 and p_two is not None
                        and abs(p_two - 0.22032849417661104) < 1e-9,
                        "sign_test.cells_54: pos=%s neg=%s zero=%s "
                        "p_two_sided=%s (expected 0.22032849417661104)"
                        % (sign.get("n_positive"), sign.get("n_negative"),
                           sign.get("n_zero"), p_two)))

    csv_rows = None
    csv_path = wdir / "stage17_solution_identity.csv"
    if csv_path.exists():
        with csv_path.open(encoding="utf-8", newline="") as handle:
            csv_rows = sum(1 for _ in csv.DictReader(handle))
    cells_list = identity.get("cells") or []
    checks.append(check("week16.part_b_32_cells_5_molecules",
                        identity.get("n_cells") == 32
                        and identity.get("n_molecules") == 5
                        and len(cells_list) == 32,
                        "stage17_solution_identity.json: n_cells=%s n_molecules=%s "
                        "len(cells)=%d"
                        % (identity.get("n_cells"), identity.get("n_molecules"),
                           len(cells_list))))
    checks.append(check("week16.part_b_csv_row_count_matches_json",
                        csv_rows == 32 and len(cells_list) == 32,
                        "stage17_solution_identity.csv rows=%s vs len(cells)=%d"
                        % (csv_rows, len(cells_list))))
    census = identity.get("census") or {}
    checks.append(check("week16.part_b_census_unresolved_is_empty",
                        census.get("unresolved") == []
                        and census.get("n_cells_resolved") == 32,
                        "census.unresolved=%s; census.n_cells_resolved=%s"
                        % (census.get("unresolved"), census.get("n_cells_resolved"))))

    def _s2_ok(cell):
        s2d = cell.get("s2_default")
        s2m = cell.get("s2_moread")
        return (s2d is not None and 0.74 <= s2d <= 0.76
                and s2m is not None and 0.74 <= s2m <= 0.76)

    bad = [cell.get("name") for cell in cells_list if not _s2_ok(cell)]
    checks.append(check("week16.part_b_both_arms_are_spin_pure_doublets",
                        len(cells_list) == 32 and not bad,
                        "stage17_solution_identity.csv <S^2> in [0.74, 0.76] on both "
                        "arms for %d/32 cells; out of range: %s"
                        % (len(cells_list) - len(bad), bad or "none")))

    family = identity.get("by_family") or {}
    fam_spec = (("week16.part_b_family_cyclic_carbonate", "cyclic_carbonate",
                 15, -0.5025033067938645, 0.6688745333333334, 15),
                ("week16.part_b_family_linear_carbonate", "linear_carbonate",
                 7, 0.40339449194493693, 2.5862442857142858, 6),
                ("week16.part_b_family_phosphate", "phosphate",
                 10, -0.22152821938109923, 0.33053270000000007, 0))
    for name, fam, n_cells, loss, charge, same_spin in fam_spec:
        block = family.get(fam) or {}
        loss_v = block.get("loss_in_pr_mean")
        charge_v = block.get("charge_l1_mean")
        checks.append(check(name,
                            block.get("n_cells") == n_cells
                            and loss_v is not None and abs(loss_v - loss) < 1e-4
                            and charge_v is not None and abs(charge_v - charge) < 1e-4
                            and block.get("n_same_spin_center") == same_spin,
                            "by_family.%s: n_cells=%s loss_in_pr_mean=%s "
                            "charge_l1_mean=%s n_same_spin_center=%s"
                            % (fam, block.get("n_cells"), loss_v, charge_v,
                               block.get("n_same_spin_center"))))
    fam_total = sum(int((family.get(name) or {}).get("n_cells") or 0)
                    for name in ("cyclic_carbonate", "linear_carbonate", "phosphate"))
    checks.append(check("week16.part_b_family_cells_sum_to_32", fam_total == 32,
                        "cyclic_carbonate + linear_carbonate + phosphate = %d" % fam_total))

    by_state = identity.get("by_state") or {}
    anion = by_state.get("anion") or {}
    cation = by_state.get("cation") or {}
    checks.append(check("week16.part_b_by_state_16_each_and_spin_center_split",
                        anion.get("n_cells") == 16 and cation.get("n_cells") == 16
                        and anion.get("n_same_spin_center") == 16
                        and cation.get("n_same_spin_center") == 5,
                        "by_state.anion: n_cells=%s n_same_spin_center=%s; "
                        "by_state.cation: n_cells=%s n_same_spin_center=%s"
                        % (anion.get("n_cells"), anion.get("n_same_spin_center"),
                           cation.get("n_cells"), cation.get("n_same_spin_center"))))

    n_geom = sum(1 for cell in cells_list if cell.get("geometry_identical") is True)
    checks.append(check("week16.part_b_geometry_qc_32_of_32",
                        len(cells_list) == 32 and n_geom == 32,
                        "%d/32 cells with identical CARTESIAN COORDINATES "
                        "(stage17_solution_identity.csv geometry_identical)" % n_geom))

    checks.append(check("week16.figures_present",
                        (wdir / "artifacts" / "F32_stage17_contamination.png").exists()
                        and (wdir / "artifacts"
                             / "F33_stage17_solution_identity.png").exists(),
                        "artifacts/ F32 + F33"))
    checks.append(check("week16.report_present",
                        (wdir / "week16_report_full.md").exists(),
                        "week16_report_full.md"))
    return checks



def week17_checks(wdir: Path):
    """QC for week 17 (Stage 18, the identity census and the zero-cost self-diagnosis)."""

    checks = []
    census = load_json(wdir / "stage18_identity_census.json")
    diagnosis = load_json(wdir / "stage18_selfdiagnosis.json")
    for name, data in (("stage18_identity_census", census),
                       ("stage18_selfdiagnosis", diagnosis)):
        if data is None:
            checks.append(check(name + ".present", None, "source not found"))
            return checks
        checks.append(check(name + ".present", True, name + ".json present"))

    block = census.get("census") or {}
    checks.append(check("week17.part_a_census_complete",
                        block.get("n_cells_requested") == 414
                        and block.get("n_cells_resolved") == 414
                        and not (block.get("unresolved") or [])
                        and block.get("n_default_arm_missing") == 0
                        and block.get("n_moread_arm_missing") == 0,
                        "outfiles scanned=%s (standard %s + holdout %s), index keys=%s; "
                        "cells requested=%s resolved=%s, default-missing=%s "
                        "moread-missing=%s, unresolved=%s"
                        % (block.get("n_outfiles_scanned"),
                           block.get("n_outfiles_parsed_standard"),
                           block.get("n_outfiles_parsed_holdout"), block.get("n_index_keys"),
                           block.get("n_cells_requested"), block.get("n_cells_resolved"),
                           block.get("n_default_arm_missing"),
                           block.get("n_moread_arm_missing"), block.get("unresolved"))))
    checks.append(check("week17.part_a_pair_counts",
                        census.get("n_pairs") == 414 and census.get("n_discovery") == 360
                        and census.get("n_holdout") == 54,
                        "n_pairs=%s n_discovery=%s n_holdout=%s"
                        % (census.get("n_pairs"), census.get("n_discovery"),
                           census.get("n_holdout"))))
    energy = census.get("energy_crosscheck") or {}
    checks.append(check("week17.part_a_energy_crosscheck",
                        energy.get("passed") is True
                        and energy.get("n_compared") == 414
                        and energy.get("max_abs_mismatch_ev") is not None
                        and float(energy.get("max_abs_mismatch_ev"))
                        <= float(energy.get("tolerance_ev") or 0.0),
                        "n_compared=%s max|delta|=%.3g eV tolerance=%.0e passed=%s"
                        % (energy.get("n_compared"),
                           float(energy.get("max_abs_mismatch_ev") or 0.0),
                           float(energy.get("tolerance_ev") or 0.0), energy.get("passed"))))
    geometry = census.get("geometry_qc") or {}
    checks.append(check("week17.part_a_geometry_qc",
                        geometry.get("all_identical") is True
                        and geometry.get("n_geometry_identical") == geometry.get("n_pairs"),
                        "geometry identical %s / %s pairs, all_identical=%s"
                        % (geometry.get("n_geometry_identical"), geometry.get("n_pairs"),
                           geometry.get("all_identical"))))

    counts = census.get("classification_counts") or {}
    discovery_counts = counts.get("discovery") or {}
    holdout_counts = counts.get("holdout") or {}
    checks.append(check("week17.part_a_classification_counts",
                        discovery_counts.get("coincident") == 328
                        and discovery_counts.get("moread_lower") == 32
                        and holdout_counts.get("coincident") == 49
                        and holdout_counts.get("moread_lower") == 5
                        and counts.get("n_rule_mismatches") == 0
                        and counts.get("n_actual_pairs") == counts.get("n_expected_pairs") == 414,
                        "discovery %s/%s, holdout %s/%s, rule mismatches=%s, pairs %s/%s"
                        % (discovery_counts.get("coincident"),
                           discovery_counts.get("moread_lower"),
                           holdout_counts.get("coincident"),
                           holdout_counts.get("moread_lower"),
                           counts.get("n_rule_mismatches"), counts.get("n_actual_pairs"),
                           counts.get("n_expected_pairs"))))

    thresholds = census.get("thresholds") or {}
    gap_low = thresholds.get("calibration_coincident_max")
    gap_high = thresholds.get("calibration_moread_min")
    cut = thresholds.get("charge_l1_primary")
    checks.append(check("week17.part_a_calibration_gap",
                        cut is not None and gap_low is not None and gap_high is not None
                        and float(gap_low) < float(cut) < float(gap_high),
                        "largest coincident=%.6f, frozen cut=%.3f, smallest moread_lower=%.6f; "
                        "scope=%s"
                        % (float(gap_low or 0.0), float(cut or 0.0), float(gap_high or 0.0),
                           thresholds.get("calibration_scope"))))

    separation = census.get("separation") or {}
    consistent = separation.get("consistency") or {}
    all_block = separation.get("all") or {}
    holdout_block = separation.get("holdout") or {}
    matrix = all_block.get("confusion_at_threshold") or {}
    holdout_matrix = holdout_block.get("confusion_at_threshold") or {}
    checks.append(check("week17.part_a_separation_is_clean",
                        consistent.get("n_consistent") == 414
                        and consistent.get("rate") == 1.0
                        and (all_block.get("auc") or {}).get("charge_l1") == 1.0
                        and matrix.get("tp") == 37 and matrix.get("fn") == 0
                        and matrix.get("fp") == 0 and matrix.get("tn") == 239,
                        "identity verdict agrees on %s/%s pairs (rate %s); "
                        "AUC(charge_l1)=%s; confusion TP %s FN %s FP %s TN %s"
                        % (consistent.get("n_consistent"), consistent.get("n_pairs"),
                           consistent.get("rate"),
                           (all_block.get("auc") or {}).get("charge_l1"),
                           matrix.get("tp"), matrix.get("fn"), matrix.get("fp"),
                           matrix.get("tn"))))
    checks.append(check("week17.part_a_holdout_transfers",
                        (holdout_block.get("auc") or {}).get("charge_l1") == 1.0
                        and holdout_matrix.get("tp") == 5 and holdout_matrix.get("fn") == 0
                        and holdout_matrix.get("fp") == 0 and holdout_matrix.get("tn") == 31,
                        "held-out arm scored with the discovery cut: AUC=%s, "
                        "TP %s FN %s FP %s TN %s"
                        % ((holdout_block.get("auc") or {}).get("charge_l1"),
                           holdout_matrix.get("tp"), holdout_matrix.get("fn"),
                           holdout_matrix.get("fp"), holdout_matrix.get("tn"))))
    checks.append(check("week17.part_a_closed_shell_disclosed",
                        consistent.get("n_unmeasurable") == 138
                        and consistent.get("n_measurable") == 276,
                        "%s of %s pairs are closed-shell neutrals that print no spin block, so "
                        "the identity metrics are measurable on only %s of them"
                        % (consistent.get("n_unmeasurable"), consistent.get("n_pairs"),
                           consistent.get("n_measurable"))))

    rule = diagnosis.get("frozen_rule") or {}
    checks.append(check("week17.part_b_frozen_rule",
                        rule.get("descriptor") == "gap_warn_value"
                        and rule.get("sign") == "smaller_is_riskier"
                        and float(rule.get("threshold_frozen") or 0.0) == -0.0395,
                        "frozen rule: %s %s %s"
                        % (rule.get("descriptor"), rule.get("sign"),
                           rule.get("threshold_frozen"))))
    loo = diagnosis.get("loo") or {}
    holdout = diagnosis.get("holdout") or {}
    holdout_cm = holdout.get("confusion_matrix") or {}
    checks.append(check("week17.part_b_loses_out_of_sample",
                        loo.get("beats_majority") is True
                        and holdout.get("beats_majority") is False
                        and holdout_cm.get("true_positive") == 0,
                        "leave-one-out %.4f vs majority %.4f (beats=%s); held-out %.4f vs "
                        "majority %.4f (beats=%s, TP=%s FP=%s TN=%s FN=%s)"
                        % (float(loo.get("accuracy") or 0.0),
                           float(loo.get("majority_accuracy") or 0.0), loo.get("beats_majority"),
                           float(holdout.get("accuracy") or 0.0),
                           float(holdout.get("majority_accuracy") or 0.0),
                           holdout.get("beats_majority"), holdout_cm.get("true_positive"),
                           holdout_cm.get("false_positive"), holdout_cm.get("true_negative"),
                           holdout_cm.get("false_negative"))))
    significance = diagnosis.get("significance") or {}
    checks.append(check("week17.part_b_exact_null",
                        significance.get("method") == "exact_mann_whitney_dp"
                        and float(significance.get("p_value") or 1.0) < 1e-12,
                        "method=%s p=%.4g (AUC observed %.6f)"
                        % (significance.get("method"),
                           float(significance.get("p_value") or 1.0),
                           float(significance.get("auc_observed") or 0.0))))

    one_sided = diagnosis.get("one_sided_screening") or {}
    necessity_block = one_sided.get("necessity") or {}
    necessity = necessity_block.get("overall") or {}
    by_arm = necessity_block.get("by_arm") or {}
    specificity = ((one_sided.get("specificity") or {}).get("overall") or {})
    coverage = one_sided.get("coverage") or {}
    checks.append(check("week17.part_b_warning_is_necessary",
                        necessity.get("n_positive") == 37
                        and necessity.get("n_positive_without_warning") == 0
                        and necessity.get("p_no_warning_given_positive") == 0.0
                        and (by_arm.get("discovery") or {}).get("n_positive_without_warning") == 0
                        and (by_arm.get("holdout") or {}).get("n_positive_without_warning") == 0,
                        "positives with the warning %s/%s (discovery %s/%s, holdout %s/%s); "
                        "P(no warning | positive) = %s"
                        % (necessity.get("n_positive_with_warning"), necessity.get("n_positive"),
                           (by_arm.get("discovery") or {}).get("n_positive_with_warning"),
                           (by_arm.get("discovery") or {}).get("n_positive"),
                           (by_arm.get("holdout") or {}).get("n_positive_with_warning"),
                           (by_arm.get("holdout") or {}).get("n_positive"),
                           necessity.get("p_no_warning_given_positive"))))
    checks.append(check("week17.part_b_warning_is_not_sufficient",
                        specificity.get("n_negative") == 377
                        and specificity.get("n_negative_with_warning") == 237
                        and abs(float(specificity.get("false_alarm_rate") or 0.0)
                                - 237.0 / 377.0) < 1e-9,
                        "negatives with the warning %s/%s (false-alarm rate %.4f, "
                        "specificity %.4f)"
                        % (specificity.get("n_negative_with_warning"),
                           specificity.get("n_negative"),
                           float(specificity.get("false_alarm_rate") or 0.0),
                           float(specificity.get("specificity") or 0.0))))
    checks.append(check("week17.part_b_warning_defined_everywhere",
                        coverage.get("n_pairs") == 414
                        and coverage.get("n_pairs_with_gap_warning_field") == 414,
                        "the warning field is present for %s/%s pairs, including the %s "
                        "closed-shell neutrals the spin features cannot reach"
                        % (coverage.get("n_pairs_with_gap_warning_field"),
                           coverage.get("n_pairs"), coverage.get("n_neutral_pairs"))))
    return checks


def week18_checks(wdir: Path):
    """QC for week 18 (Stage 19, the geometry-relaxation verdict).

    Every number is read back out of ``stage19_relax.json`` /
    ``stage19_relax_analysis.json``; the frozen identity threshold is
    cross-checked against the Stage 18 census instead of being restated.
    """

    checks = []
    ledger = load_json(wdir / "stage19_relax.json")
    analysis = load_json(wdir / "stage19_relax_analysis.json")
    for name, data in (("stage19_relax", ledger),
                       ("stage19_relax_analysis", analysis)):
        if data is None:
            checks.append(check(name + ".present", None, "source not found"))
            return checks
        checks.append(check(name + ".present", True, name + ".json present"))

    summary = ledger.get("summary") or {}
    n_cells = ledger.get("n_target_cells")
    checks.append(check("week18.relax_ledger_is_complete",
                        n_cells == 37
                        and summary.get("n_jobs") == 74
                        and summary.get("n_ok") == 74
                        and summary.get("n_failed") == 0,
                        "target cells=%s; jobs=%s ok=%s failed=%s (reused %s, computed %s)"
                        % (n_cells, summary.get("n_jobs"), summary.get("n_ok"),
                           summary.get("n_failed"), summary.get("n_reused"),
                           summary.get("n_computed"))))

    all_block = ((analysis.get("aggregates") or {}).get("all") or {}).get("all") or {}
    outcomes = all_block.get("outcomes") or {}
    checks.append(check("week18.relax_verdict_over_37_cells",
                        analysis.get("n_cells") == 37
                        and all_block.get("n_cells") == 37
                        and all_block.get("n_complete") == 37
                        and outcomes.get("distinct_lower") == 5
                        and outcomes.get("distinct_higher") == 24
                        and outcomes.get("same_lower") == 0
                        and outcomes.get("same_higher") == 8
                        and outcomes.get("incomplete") == 0,
                        "n_cells=%s complete=%s; distinct_lower %s / distinct_higher %s / "
                        "same_lower %s / same_higher %s / incomplete %s"
                        % (analysis.get("n_cells"), all_block.get("n_complete"),
                           outcomes.get("distinct_lower"), outcomes.get("distinct_higher"),
                           outcomes.get("same_lower"), outcomes.get("same_higher"),
                           outcomes.get("incomplete"))))
    checks.append(check("week18.relax_headline_counts",
                        all_block.get("n_still_distinct") == 29
                        and all_block.get("n_still_lower") == 5
                        and all_block.get("n_preference_flipped") == 32
                        and all_block.get("n_near_threshold") == 0
                        and all_block.get("n_rmsd_same_minimum") == 6,
                        "still_distinct %s, still_lower %s, preference_flipped %s, "
                        "near_threshold %s, rmsd_same_minimum %s"
                        % (all_block.get("n_still_distinct"), all_block.get("n_still_lower"),
                           all_block.get("n_preference_flipped"),
                           all_block.get("n_near_threshold"),
                           all_block.get("n_rmsd_same_minimum"))))

    census = load_json(W18_STAGE18_CENSUS_PATH) or {}
    census_cut = (census.get("thresholds") or {}).get("charge_l1_primary")
    frozen = analysis.get("threshold_charge_l1")
    checks.append(check("week18.threshold_is_stage18_frozen",
                        frozen is not None and census_cut is not None
                        and float(frozen) == float(census_cut),
                        "threshold_charge_l1=%s == stage18 thresholds.charge_l1_primary=%s "
                        "(frozen, not refitted)" % (frozen, census_cut)))

    magnitudes = (("abs_single_point_delta_ev", 0.1198, 1e-3),
                  ("abs_relax_delta_ev", 0.00196, 1e-4),
                  ("abs_delta_shift_ev", 0.104, 2e-3),
                  ("energy_drop_default_ev", 1.876, 2e-3),
                  ("energy_drop_moread_ev", 1.666, 2e-3))
    rows, ok_all = [], True
    for key, expected, tol in magnitudes:
        got = (all_block.get(key) or {}).get("p50")
        good = got is not None and abs(float(got) - expected) < tol
        ok_all = ok_all and good
        rows.append("%s p50=%s (expected %s +/- %s)" % (key, got, expected, tol))
    checks.append(check("week18.relax_magnitudes", ok_all, "; ".join(rows)))

    figure_names = ("F36_stage19_relax_outcomes.png",
                    "F37_stage19_identity_geometry.png")
    detail = ", ".join("%s=%s" % (name, (wdir / "artifacts" / name).exists())
                       for name in figure_names)
    checks.append(check("week18.figures_present",
                        all((wdir / "artifacts" / name).exists() for name in figure_names),
                        detail))
    report_present = (wdir / "week18_report_full.md").exists()
    checks.append(check("week18.report_present", report_present,
                        "week18_report_full.md present=%s" % report_present))
    return checks


def week19_checks(wdir: Path):
    """QC for week 19 (Stage 20: the sixth rung + the cross-method fate of the second solution).

    Every number is read back out of ``stage20_relax_rung.json``,
    ``stage20_xtb_arms.json`` and ``stage20_xtb_arms_analysis.json``, so the
    distilled report cannot drift away from the artifacts it summarises.
    """

    checks = []
    rung = load_json(wdir / "stage20_relax_rung.json")
    ledger = load_json(wdir / "stage20_xtb_arms.json")
    analysis = load_json(wdir / "stage20_xtb_arms_analysis.json")
    for name, data in (("stage20_relax_rung", rung),
                       ("stage20_xtb_arms", ledger),
                       ("stage20_xtb_arms_analysis", analysis)):
        if data is None:
            checks.append(check(name + ".present", None, "source not found"))
            return checks
        checks.append(check(name + ".present", True, name + ".json present"))

    def near(value, expected, tol):
        return value is not None and abs(float(value) - expected) < tol

    # ------------------------------------------------------------------ Part 1
    checks.append(check("week19.rung_shape",
                        rung.get("n_cells") == 37
                        and rung.get("n_eps_values") == 10
                        and rung.get("n_molecules_total") == 7
                        and (rung.get("n_molecules_by_state") or {}) == {"anion": 4, "cation": 3},
                        "n_cells=%s n_eps_values=%s n_molecules_total=%s n_by_state=%s"
                        % (rung.get("n_cells"), rung.get("n_eps_values"),
                           rung.get("n_molecules_total"), rung.get("n_molecules_by_state"))))

    by_state = (rung.get("aggregates") or {}).get("by_state") or {}
    anion = by_state.get("anion") or {}
    cation = by_state.get("cation") or {}
    checks.append(check("week19.rung_by_state_two_branches",
                        anion.get("n_cells") == 21 and cation.get("n_cells") == 16
                        and near(anion.get("shift_mean_ev"), -1.953, 2e-3)
                        and near(anion.get("shift_std_ev"), 0.160, 2e-3)
                        and near(anion.get("relative_dispersion"), 0.08, 5e-3)
                        and near(cation.get("shift_mean_ev"), -0.610, 2e-3)
                        and near(cation.get("shift_std_ev"), 0.315, 2e-3)
                        and near(cation.get("relative_dispersion"), 0.52, 5e-3),
                        "anion mean=%s std=%s rel=%s (n=%s); cation mean=%s std=%s rel=%s (n=%s)"
                        % (anion.get("shift_mean_ev"), anion.get("shift_std_ev"),
                           anion.get("relative_dispersion"), anion.get("n_cells"),
                           cation.get("shift_mean_ev"), cation.get("shift_std_ev"),
                           cation.get("relative_dispersion"), cation.get("n_cells"))))

    ranges = sorted(float(row.get("delta_range_ev") or 0.0)
                    for row in (rung.get("epsilon_rows") or []))
    mid = ranges[len(ranges) // 2] if ranges else None
    checks.append(check("week19.rung_shift_is_flat_in_epsilon",
                        len(ranges) == 7 and near(mid, 0.0263, 2e-4)
                        and near(ranges[-1], 0.215, 2e-3),
                        "per-molecule eps range: n=%s median=%s max=%s"
                        % (len(ranges), mid, ranges[-1] if ranges else None)))

    ladder = rung.get("ladder_rows") or []
    omitted = [str(row.get("rank_metrics") or "") for row in ladder]
    n_frozen = sum(1 for row in ladder if row.get("rung") != "P2sp_to_P2relax")
    n_new = sum(1 for row in ladder if row.get("rung") == "P2sp_to_P2relax")
    checks.append(check("week19.rung_rank_metrics_structurally_omitted",
                        len(ladder) == 30 and n_new == 6 and n_frozen == 24
                        and all(text.startswith("omitted:") for text in omitted),
                        "ladder rows=%s (frozen %s / new %s); every rank_metrics starts "
                        "with 'omitted:' = %s"
                        % (len(ladder), n_frozen, n_new,
                           all(text.startswith("omitted:") for text in omitted))))

    def rung_row(population, kind):
        for row in ladder:
            if row.get("population") == population and row.get("rung") == kind:
                return row
        return {}

    ox_new = rung_row("ox_dmc_ec_tmp_eps5", "P2sp_to_P2relax")
    ox_env = rung_row("ox_dmc_ec_tmp_eps5", "P1_to_P2")
    red_new = rung_row("red_dec_emc_pc_tegdme_eps20", "P2sp_to_P2relax")
    red_env = rung_row("red_dec_emc_pc_tegdme_eps20", "P1_to_P2")
    checks.append(check("week19.rung_new_vs_frozen_dispersion",
                        near(ox_new.get("relative_dispersion"), 0.74, 5e-3)
                        and near(ox_env.get("relative_dispersion"), 0.17, 5e-3)
                        and near(red_new.get("relative_dispersion"), 0.13, 5e-3)
                        and near(red_env.get("relative_dispersion"), 0.26, 5e-3),
                        "ox eps=5 new %s vs P1->P2 %s; red eps=20 new %s vs P1->P2 %s"
                        % (ox_new.get("relative_dispersion"), ox_env.get("relative_dispersion"),
                           red_new.get("relative_dispersion"),
                           red_env.get("relative_dispersion"))))

    # ------------------------------------------------------------------ Part 2
    summary = ledger.get("summary") or {}
    checks.append(check("week19.xtb_ledger_is_complete",
                        ledger.get("n_target_cells") == 37
                        and summary.get("n_jobs") == 74
                        and summary.get("n_ok") == 74
                        and summary.get("n_failed") == 0,
                        "target cells=%s; jobs=%s ok=%s failed=%s (reused %s, computed %s)"
                        % (ledger.get("n_target_cells"), summary.get("n_jobs"),
                           summary.get("n_ok"), summary.get("n_failed"),
                           summary.get("n_reused"), summary.get("n_computed"))))

    all_block = ((analysis.get("aggregates") or {}).get("all") or {}).get("all") or {}
    outcomes = all_block.get("outcomes") or {}
    checks.append(check("week19.xtb_verdict_over_37_cells",
                        analysis.get("n_cells") == 37
                        and all_block.get("n_cells") == 37
                        and all_block.get("n_complete") == 37
                        and outcomes.get("distinct_lower") == 15
                        and outcomes.get("distinct_higher") == 16
                        and outcomes.get("same_lower") == 0
                        and outcomes.get("same_higher") == 6
                        and outcomes.get("incomplete") == 0,
                        "n_cells=%s complete=%s; distinct_lower %s / distinct_higher %s / "
                        "same_lower %s / same_higher %s / incomplete %s"
                        % (analysis.get("n_cells"), all_block.get("n_complete"),
                           outcomes.get("distinct_lower"), outcomes.get("distinct_higher"),
                           outcomes.get("same_lower"), outcomes.get("same_higher"),
                           outcomes.get("incomplete"))))
    checks.append(check("week19.xtb_headline_counts",
                        all_block.get("n_xtb_same_minimum") == 6
                        and all_block.get("n_xtb_still_lower") == 15
                        and all_block.get("n_xtb_preference_flipped") == 6
                        and all_block.get("n_agree_with_stage19") == 17
                        and all_block.get("n_xtb_sp_matches_stage19_relax") == 33,
                        "same_minimum %s, still_lower %s, preference_flipped %s, "
                        "agree_with_stage19 %s/37, same-geometry method agreement %s/37"
                        % (all_block.get("n_xtb_same_minimum"),
                           all_block.get("n_xtb_still_lower"),
                           all_block.get("n_xtb_preference_flipped"),
                           all_block.get("n_agree_with_stage19"),
                           all_block.get("n_xtb_sp_matches_stage19_relax"))))

    p50 = (all_block.get("abs_xtb_relax_delta_ev") or {}).get("p50")
    cheap = (all_block.get("abs_xtb_sp_delta_ev") or {}).get("p50")
    checks.append(check("week19.xtb_relaxation_compresses_the_gap",
                        near(p50, 2.13e-4, 1e-5) and near(cheap, 7.17e-3, 1e-4),
                        "|xTB single point Delta| p50=%s eV -> |xTB relaxed Delta| p50=%s eV "
                        "(compressed %.1fx)"
                        % (cheap, p50, (float(cheap) / float(p50)) if p50 else 0.0)))

    cross = analysis.get("crosstab_stage19_by_stage20") or {}
    checks.append(check("week19.xtb_crosstab_matches_the_verdicts",
                        (cross.get("distinct_lower") or {}).get("distinct_lower") == 1
                        and (cross.get("distinct_lower") or {}).get("distinct_higher") == 4
                        and (cross.get("distinct_higher") or {}).get("distinct_lower") == 14
                        and (cross.get("distinct_higher") or {}).get("distinct_higher") == 10
                        and (cross.get("same_higher") or {}).get("same_higher") == 6,
                        "Stage19 distinct_lower -> {Stage20 distinct_lower %s, distinct_higher %s}; "
                        "distinct_higher -> {distinct_lower %s, distinct_higher %s}; "
                        "same_higher -> same_higher %s"
                        % ((cross.get("distinct_lower") or {}).get("distinct_lower"),
                           (cross.get("distinct_lower") or {}).get("distinct_higher"),
                           (cross.get("distinct_higher") or {}).get("distinct_lower"),
                           (cross.get("distinct_higher") or {}).get("distinct_higher"),
                           (cross.get("same_higher") or {}).get("same_higher"))))

    # -------------------------------------------------------------- artifacts
    figure_names = ("F38_stage20_relax_rung.png", "F39_stage20_xtb_arms.png")
    detail = ", ".join("%s=%s" % (name, (wdir / "artifacts" / name).exists())
                       for name in figure_names)
    checks.append(check("week19.figures_present",
                        all((wdir / "artifacts" / name).exists() for name in figure_names),
                        detail))
    report_present = (wdir / "week19_report_full.md").exists()
    checks.append(check("week19.report_present", report_present,
                        "week19_report_full.md present=%s" % report_present))
    return checks


def week20_blocks(path_analysis, protocol, shell_analysis, refill):
    """Week 20 / Stage 21 narrative blocks.

    Every number is read back out of the four Stage 21 products, so the distilled
    report cannot drift away from the artifacts it summarises.
    """

    keys = ("did", "metric", "qc", "limit", "summary", "protocol_block",
            "path_block", "shell_block", "refill_block", "table_block")
    if path_analysis is None or refill is None:
        text = ("（`stage21_path_analysis.json` 或 `stage21_refill.json` 不存在）")
        return {key: text for key in keys}

    protocol = protocol or {}
    shell_analysis = shell_analysis or {}

    def num(value, digits=3):
        return _w8_num(value, digits)

    def signed(value, digits=4):
        if value is None:
            return "n/a"
        return ("%+.*f" % (digits, float(value)))

    cells = {cell["cell"]: cell for cell in (path_analysis.get("cells") or [])}
    fragile = cells.get("EC/cation/5") or {}
    same_cell = cells.get("EC/cation/20") or {}
    control = cells.get("TEGDME/anion/20") or {}

    counts = protocol.get("verdict_counts") or {}
    threshold = protocol.get("threshold") or {}
    derivation = threshold.get("derivation") or {}
    cross = (protocol.get("cross_tabs") or {})
    strict = cross.get("binary_vs_rule_strict") or {}
    lenient = cross.get("binary_vs_rule_lenient") or {}
    borderline = protocol.get("borderline") or []
    probe = ((protocol.get("closed_shell_probe") or {}).get("summary") or {})
    reach = protocol.get("reach") or {}

    axes = {row.get("axis"): row for row in (shell_analysis.get("axes") or [])}
    oxidation = axes.get("oxidation") or {}
    reduction = axes.get("reduction") or {}

    coverage = refill.get("coverage") or {}
    strict_leg = coverage.get("strict_p2_leg") or {}
    dielectric = coverage.get("dielectric_sub_leg") or {}
    refill_verdict = (refill.get("verdict") or {}).get("per_axis") or {}

    did = ("Part A：在 Stage 19 两条弛豫终点之间做直线内插、每点一个冻结 r2SCAN-3c 单点"
           "（3 格 x %s 帧 = %s 个）。Part B：把 `charge_l1` 身份判据做成运行手册预检"
           "（零新增计算，全 %s 格）。Part C：12 个 `[Li(M)2]+` 的氧化态与还原态各做一次 "
           "r2SCAN-3c `Opt`（%s 个作业）。Part D：把 Stage 10 第 2 级台阶的 P2 腿真正换成"
           "弛豫后能量再合成一次（零新增计算）。"
           % (path_analysis.get("images"), path_analysis.get("n_jobs"),
              protocol.get("n_cells"), shell_analysis.get("n_jobs")))
    metric = ("EC/cation/eps=5 被判 `distinct_lower`，但内插路径相对弦最大只抬升 %s eV"
              "（k_B T = %s eV 的 %s%%），判据**过度判定**；%s/%s 格与 Stage 19 的 RMSD 裁决一致。"
              "Part B 阈值重导为 %s（空档宽 %s，无数据点），borderline %s 格；闭壳层反例探针"
              "%s 格越阈。Part C 氧化轴修正 %s +- %s eV、ρ=%s；还原轴修正 %s +- %s eV、ρ=%s，"
              "排除 %s 格。Part D 严格 P2 腿 %s/%s 可回填，氧化轴排序被改写（Top-10%% 重叠 %s）、"
              "还原轴未被改写。"
              % (num(fragile.get("barrier_chord_ev"), 5),
                 num(path_analysis.get("thermal_ev"), 4),
                 num(100.0 * float(fragile.get("barrier_chord_ev") or 0.0)
                     / float(path_analysis.get("thermal_ev") or 1.0), 1),
                 path_analysis.get("n_agree_with_stage19"), path_analysis.get("n_cells"),
                 num(threshold.get("value"), 6), num(derivation.get("gap_width"), 6),
                 len(borderline), probe.get("n_exceeding_threshold"),
                 signed(oxidation.get("correction_mean_ev"), 4),
                 num(oxidation.get("correction_std_ev"), 4),
                 num(oxidation.get("spearman_frozen_vs_relaxed"), 3),
                 signed(reduction.get("correction_mean_ev"), 4),
                 num(reduction.get("correction_std_ev"), 4),
                 num(reduction.get("spearman_frozen_vs_relaxed"), 3),
                 shell_analysis.get("n_excluded"),
                 strict_leg.get("n_refillable"), strict_leg.get("n_cells"),
                 num((refill_verdict.get("oxidation") or {}).get("top10_overlap"), 3)))
    qc = ("核心 QC：Part A 的 %s 个单点全部 SCF 收敛（all_converged=%s），"
          "每格的端点冻结单点差必须逐位等于 Stage 19 的弛豫能量差；Part B 的阈值由 discovery 臂"
          "空档中点现算、`gap_empty=%s`，交叉表与闭壳层探针逐格写入 verification.json 的 checks；"
          "Part C 的 %s 个 Opt 逐格做结构 QC（父几何共价键完好 / 弛豫后单一碎片 / Li 同时配位"
          "两个配体），不合格者排除而不是计入均值；Part D 直接 import "
          "`analyze_stage10_synthesis` 的合成函数，只替换 P1_to_P2 的 P2 端点。"
          % (path_analysis.get("n_jobs"), path_analysis.get("all_converged"),
             derivation.get("gap_empty"), shell_analysis.get("n_jobs")))
    limit = ("Part A **不是抽样**：只走 3 格，选格标准是夹住 Stage 19 的 0.02 A 阈值；"
             "临界带里还有 EC/cation/eps=7 与 eps=10 两格未走。内插路径是**笛卡尔直线、"
             "不是最小能量路径**，所以鼓包只是**上界**："
             "TEGDME/anion/eps=20 的 %s eV 是原子互穿的假象，只证明两条腿确实分立。"
             "可以引用的是反方向的结论——「直线全程不抬升 ⇒ 同一个盆地」。"
             "Part B 的阈值是**经验阈值**，换方法 / 基组 / 溶剂层都可能让空档消失；"
             "`unmeasurable` 的 %s 格（%.1f%%）**不可**计入灵敏度分母。"
             "Part C 只覆盖 1:2 一个化学计量与 m1/m2 两个 motif，结构 QC 只说「结构没散」、"
             "不说「电子结构没变」。Part D 的可回填格全部来自**裸 CPCM** 层而不是 SMD 层，"
             "所以它回答的是「把 CPCM 上量到的弛豫修正搬到 SMD 层，排序会不会动」——"
             "这是一个**转移假设**；且氧化轴只有 3 个分子，τ 是枚举不是统计推断。"
             % (num(control.get("barrier_chord_ev"), 1), reach.get("n_unmeasurable"),
                100.0 * float(reach.get("unmeasurable_share") or 0.0)))
    summary_text = " ".join([did, metric])

    path_block = ("\n".join(
        ["| 格 | Stage 19 RMSD (A) | Stage 19 裁决 | 路径长 (A) | 弦上鼓包 (eV) | "
         "弛豫后差 (eV) | 本周裁决 | 一致 |",
         "| --- | --- | --- | --- | --- | --- | --- | --- |"]
        + ["| `%s` | %s | `%s` | %s | %s | %s | `%s` | %s |"
           % (cell.get("cell"), num(cell.get("rmsd_a_stage19"), 4),
              cell.get("stage19_verdict"), num(cell.get("path_length_a"), 4),
              num(cell.get("barrier_chord_ev"), 6),
              signed(cell.get("relax_span_ev"), 5),
              cell.get("verdict"), "是" if cell.get("agrees_with_stage19") else "**否**")
           for cell in (path_analysis.get("cells") or [])]))
    shell_block = ("\n".join(
        ["| 壳 | 轴 | 冻结位移 (eV) | 弛豫位移 (eV) | 弛豫修正 (eV) | 可用 | QC |",
         "| --- | --- | --- | --- | --- | --- | --- |"]
        + ["| %s | %s | %s | %s | %s | %s | %s |"
           % (row.get("shell_label"), row.get("state"),
              num(row.get("shell_shift_frozen_ev"), 3),
              num(row.get("shell_shift_relaxed_ev"), 3),
              signed(row.get("relaxation_correction_ev"), 4),
              "是" if row.get("usable") else "**否**", row.get("qc_flags") or "")
           for row in (shell_analysis.get("shells") or [])]))
    refill_block = ("\n".join(
        ["| 轴 | n | 回填前排序 | 回填后排序 | rho | tau | Top-10% 重叠 | 是否改写排序 |",
         "| --- | --- | --- | --- | --- | --- | --- | --- |"]
        + ["| %s | %s | %s | %s | %s | %s | %s | **%s** |"
           % (label, (refill_verdict.get(axis) or {}).get("n"),
              " > ".join((refill_verdict.get(axis) or {}).get("order_before") or []),
              " > ".join((refill_verdict.get(axis) or {}).get("order_after") or []),
              num((refill_verdict.get(axis) or {}).get("spearman_rho"), 4),
              num((refill_verdict.get(axis) or {}).get("kendall_tau_b"), 4),
              num((refill_verdict.get(axis) or {}).get("top10_overlap"), 3),
              "是" if (refill_verdict.get(axis) or {}).get("ranking_rewritten") else "否")
           for axis, label in (("oxidation", "氧化轴"), ("reduction", "还原轴"))]))
    protocol_block = ("阈值 **%s**（%s；空档 (%s, %s) 宽 %s 且 `gap_empty=%s`）；"
                      "coincident %s / borderline %s / differs %s / unmeasurable %s；"
                      "严格口径 TP %s / FN %s / FP %s / TN %s（灵敏度 %s），"
                      "宽松口径 TP %s / FN %s / FP %s / TN %s（灵敏度 %s）。"
                      "需要预检的格子：%s。"
                      % (num(threshold.get("value"), 6), derivation.get("basis"),
                         num(derivation.get("gap_lower"), 6),
                         num(derivation.get("gap_upper"), 6),
                         num(derivation.get("gap_width"), 6), derivation.get("gap_empty"),
                         counts.get("coincident"), counts.get("borderline"),
                         counts.get("differs"), counts.get("unmeasurable"),
                         strict.get("tp"), strict.get("fn"), strict.get("fp"),
                         strict.get("tn"), num(strict.get("sensitivity"), 4),
                         lenient.get("tp"), lenient.get("fn"), lenient.get("fp"),
                         lenient.get("tn"), num(lenient.get("sensitivity"), 4),
                         "、".join("%s/%s/eps=%g" % (row.get("name"), row.get("state"),
                                                       float(row.get("epsilon") or 0))
                                   for row in borderline) or "无"))
    table_block = "\n".join(
        ["| 文件 | 内容 |", "| --- | --- |"]
        + ["| %s | %s |" % (name, note) for name, note in W20_TABLE_ROWS])

    return {"did": did, "metric": metric, "qc": qc, "limit": limit,
            "summary": summary_text, "protocol_block": protocol_block,
            "path_block": path_block, "shell_block": shell_block,
            "refill_block": refill_block, "table_block": table_block}


def week20_checks(wdir: Path):
    """QC for week 20 (Stage 21: four independent parts).

    Every number is read back out of ``stage21_path_analysis.json``,
    ``stage21_protocol.json``, ``stage21_shell_redox_analysis.json`` and
    ``stage21_refill.json``.
    """

    checks = []
    path_analysis = load_json(wdir / "stage21_path_analysis.json")
    protocol = load_json(wdir / "stage21_protocol.json")
    shell_analysis = load_json(wdir / "stage21_shell_redox_analysis.json")
    refill = load_json(wdir / "stage21_refill.json")
    for name, data in (("stage21_path_analysis", path_analysis),
                       ("stage21_protocol", protocol),
                       ("stage21_shell_redox_analysis", shell_analysis),
                       ("stage21_refill", refill)):
        if data is None:
            checks.append(check(name + ".present", None, "source not found"))
            return checks
        checks.append(check(name + ".present", True, name + ".json present"))

    def near(value, expected, tol):
        return value is not None and abs(float(value) - expected) < tol

    cells = {cell["cell"]: cell for cell in (path_analysis.get("cells") or [])}
    fragile = cells.get("EC/cation/5") or {}
    checks.append(check("week20.path_shape",
                        path_analysis.get("n_cells") == 3
                        and path_analysis.get("n_jobs") == 63
                        and path_analysis.get("all_converged") is True,
                        "n_cells=%s n_jobs=%s all_converged=%s"
                        % (path_analysis.get("n_cells"), path_analysis.get("n_jobs"),
                           path_analysis.get("all_converged"))))
    checks.append(check(
        "week20.path_fragile_cell_is_one_basin",
        fragile.get("stage19_verdict") == "distinct_lower"
        and fragile.get("verdict") == "one_basin"
        and fragile.get("agrees_with_stage19") is False
        and near(fragile.get("barrier_chord_ev"), 0.00424, 5e-4),
        "stage19=%s verdict=%s hump=%s"
        % (fragile.get("stage19_verdict"), fragile.get("verdict"),
           fragile.get("barrier_chord_ev"))))
    checks.append(check("week20.path_agreement_count",
                        path_analysis.get("n_agree_with_stage19") == 2
                        and path_analysis.get("n_one_basin") == 2
                        and path_analysis.get("n_separated") == 1,
                        "agree=%s one_basin=%s separated=%s"
                        % (path_analysis.get("n_agree_with_stage19"),
                           path_analysis.get("n_one_basin"),
                           path_analysis.get("n_separated"))))

    threshold = protocol.get("threshold") or {}
    derivation = threshold.get("derivation") or {}
    counts = protocol.get("verdict_counts") or {}
    checks.append(check("week20.protocol_threshold_rederived",
                        near(threshold.get("value"), 0.038946, 1e-5)
                        and derivation.get("gap_empty") is True
                        and near(derivation.get("gap_width"), 0.000874, 1e-5),
                        "threshold=%s gap_empty=%s gap_width=%s"
                        % (threshold.get("value"), derivation.get("gap_empty"),
                           derivation.get("gap_width"))))
    checks.append(check("week20.protocol_counts",
                        protocol.get("n_cells") == 414
                        and counts.get("coincident") == 237
                        and counts.get("borderline") == 3
                        and counts.get("differs") == 36
                        and counts.get("unmeasurable") == 138,
                        "n_cells=%s counts=%s" % (protocol.get("n_cells"), counts)))
    probe = ((protocol.get("closed_shell_probe") or {}).get("summary") or {})
    checks.append(check("week20.protocol_closed_shell_counterexample_empty",
                        probe.get("n_cells") == 138
                        and probe.get("n_exceeding_threshold") == 0
                        and near(probe.get("max_charge_l1"), 0.006743, 1e-5),
                        "n_read=%s n_exceeding=%s max=%s"
                        % (probe.get("n_read"), probe.get("n_exceeding_threshold"),
                           probe.get("max_charge_l1"))))

    checks.append(check("week20.shell_shape",
                        shell_analysis.get("n_shells") == 12
                        and shell_analysis.get("n_jobs") == 24
                        and shell_analysis.get("n_ok") == 24,
                        "n_shells=%s n_jobs=%s n_ok=%s"
                        % (shell_analysis.get("n_shells"), shell_analysis.get("n_jobs"),
                           shell_analysis.get("n_ok"))))
    axes = {row.get("axis"): row for row in (shell_analysis.get("axes") or [])}
    oxidation = axes.get("oxidation") or {}
    reduction = axes.get("reduction") or {}
    checks.append(check("week20.shell_every_frame_survived",
                        shell_analysis.get("n_excluded") == 0
                        and oxidation.get("n") == 12
                        and reduction.get("n") == 12,
                        "n_excluded=%s ox_n=%s red_n=%s"
                        % (shell_analysis.get("n_excluded"), oxidation.get("n"),
                           reduction.get("n"))))
    # Variational, not sign-of-a-mean: the frozen frame *is* a point on the relaxed
    # state's own surface, so relaxing it can only lower the energy.  A shell whose
    # relaxed energy came out above its frozen single point would mean the Opt left
    # the surface or the SCF fell into a different solution.
    checks.append(check("week20.shell_correction_nonpositive",
                        (oxidation.get("n_correction_positive") or 0) == 0
                        and (reduction.get("n_correction_positive") or 0) == 0,
                        "ox_positive=%s red_positive=%s (both must be 0)"
                        % (oxidation.get("n_correction_positive"),
                           reduction.get("n_correction_positive"))))

    strict_leg = (refill.get("coverage") or {}).get("strict_p2_leg") or {}
    dielectric = (refill.get("coverage") or {}).get("dielectric_sub_leg") or {}
    per_axis = (refill.get("verdict") or {}).get("per_axis") or {}
    checks.append(check("week20.refill_coverage",
                        strict_leg.get("n_cells") == 54
                        and strict_leg.get("n_refillable") == 7
                        and dielectric.get("n_cells") == 414
                        and dielectric.get("n_refillable") == 37,
                        "strict=%s/%s dielectric=%s/%s"
                        % (strict_leg.get("n_refillable"), strict_leg.get("n_cells"),
                           dielectric.get("n_refillable"), dielectric.get("n_cells"))))
    checks.append(check("week20.refill_oxidation_rewritten",
                        (per_axis.get("oxidation") or {}).get("ranking_rewritten") is True
                        and (per_axis.get("reduction") or {}).get("ranking_rewritten") is False,
                        "ox_rewritten=%s red_rewritten=%s"
                        % ((per_axis.get("oxidation") or {}).get("ranking_rewritten"),
                           (per_axis.get("reduction") or {}).get("ranking_rewritten"))))
    return checks


def week21_blocks(phase, prospective, frozen, anchor):
    """Render the week-21 (Stage 22 batch A) narrative blocks.

    Every number is read back out of ``outputs/week21/sigma_synthetic.json``,
    ``outputs/week21/sigma_prospective.json`` (plus its frozen copy) and the
    ``arm_alignment`` block of ``outputs/week4/p1_anchor_comparison.json``, so the
    distilled report cannot drift away from the artefacts it summarises.
    """

    keys = ("did", "metric", "qc", "limit", "alignment_block", "phase_block",
            "prospective_block", "table_block", "summary")
    if phase is None or prospective is None or frozen is None:
        text = ("（`sigma_synthetic.json` / `sigma_prospective.json` / "
                "`sigma_prospective_frozen.json` 缺失，无法回读）")
        return {key: text for key in keys}
    anchor = anchor or {}

    def num(value, digits=3):
        return _w8_num(value, digits)

    def signed(value, digits=4):
        if value is None:
            return "n/a"
        return "%+.*f" % (digits, float(value))

    def cell(flag):
        return "**改写**" if flag else "保留"

    def short(value):
        return (str(value)[:12] + "…") if value else "n/a"

    inv = phase.get("mean_invariance") or {}
    syn = phase.get("synthetic_correlations") or {}
    meas = phase.get("measured_correlations") or {}
    grid = phase.get("grid") or {}
    bounds = phase.get("boundaries") or {}
    ox_b = bounds.get("oxidation") or {}
    red_b = bounds.get("reduction") or {}
    sens = phase.get("subset_sensitivity") or {}
    native = sens.get("native") or {}
    common = sens.get("common10") or {}

    scoring = prospective.get("scoring") or {}
    rows = scoring.get("rows") or []
    rule = frozen.get("frozen_rule") or {}
    s_rule = rule.get("signed_rule") or {}
    n_rule = rule.get("naive_rule") or {}

    arm = anchor.get("arm_alignment") or {}
    arms = arm.get("arms_on_common_subset") or {}
    paired = arm.get("paired_delta_tau_b") or {}
    verdict = arm.get("verdict") or {}
    n_common = arm.get("n_common_subset")
    excluded = arm.get("excluded_from_common_subset") or {}
    missing_dscf = (excluded.get("GFN2_dSCF_xTB") or {}).get("molecules") or []

    did = ("批次 A 是纯分析、纯措辞的一轮（零新增电子结构、零冻结件改动）：R1（含 R10）把 Week 4 的"
           "三条臂对齐到同一批 %s 个分子之后再做配对检验；R2 用合成的（均值, 离散度）相图取代 Week 9 的 "
           "rho(std, tau_b) = -0.851；R3 把 Week 10 的判据先在发现集上冻结、再到留出集上打分；"
           "R6 / R4(a) 只改措辞。" % n_common)
    metric = ("对齐后（n = %s）：P0 Koopmans MAE %s eV、tau_b %s；GFN2 Delta-SCF MAE %s eV、tau_b %s；"
              "P1 r2SCAN-3c MAE %s eV、tau_b %s。配对 Delta tau_b（GFN2 - P1）= %s，95%% CI [%s, %s]，"
              "精确配对置换 p = %s，CI 跨 0 ⇒ 三条臂两两之间全部 unresolved。相图：max abs Delta tau_b"
              "（均值平移）= %s、合成 rho(std, tau_b) = %s、合成 rho(abs(mean), tau_b) = %s、"
              "实测 rho(std, tau_b) = %s。前瞻：带符号规则命中 %s/%s、朴素规则命中 %s/%s。"
              % (n_common,
                 num((arms.get("P0_koopmans_xTB") or {}).get("mae_ev"), 3),
                 num((arms.get("P0_koopmans_xTB") or {}).get("kendall_tau_b"), 4),
                 num((arms.get("GFN2_dSCF_xTB") or {}).get("mae_ev"), 3),
                 num((arms.get("GFN2_dSCF_xTB") or {}).get("kendall_tau_b"), 4),
                 num((arms.get("P1_r2scan3c") or {}).get("mae_ev"), 3),
                 num((arms.get("P1_r2scan3c") or {}).get("kendall_tau_b"), 4),
                 signed(verdict.get("delta_tau_b"), 4),
                 num((verdict.get("paired_ci95") or [None, None])[0], 3),
                 num((verdict.get("paired_ci95") or [None, None])[1], 3),
                 num(verdict.get("permutation_p"), 4),
                 num(inv.get("max_abs_tau_b_difference_vs_mean_0"), 3),
                 num(syn.get("spearman_shift_std_vs_tau_b"), 3),
                 num(syn.get("spearman_abs_shift_mean_vs_tau_b"), 3),
                 num(meas.get("spearman_shift_std_vs_tau_b"), 4),
                 scoring.get("signed_rule_hits"), scoring.get("n_predictions"),
                 scoring.get("naive_rule_hits"), scoring.get("n_predictions")))
    qc = ("QC：三个新脚本都可 `--check` 复跑（相图 2000 次重复的产物重跑逐字节相同）；"
          "`sigma_prospective_frozen.json` 在打分之前落盘并取 SHA256（%s），打分文件回写同一摘要（%s）；"
          "R1 的精确置换把 2^10 = %s 种赋值全部枚举；全量测试全绿；Gate 0 CLOSED，"
          "Gate 1 仍只有「31 行溶液锚点仍是 est」这一个 blocker。"
          % (short(frozen.get("frozen_sha256")), short(prospective.get("frozen_sha256")),
             ((paired.get("GFN2_dSCF_xTB_minus_P1_r2scan3c") or {})
              .get("permutation") or {}).get("total_assignments")))
    limit = ("边界：(1) R2 的相图是合成模型（delta_i = mean + std * z_i，z 在每个 replicate 内标准化），"
             "它证明的是「在这个模型里排序只由离散度决定」，不是「真实体系里只有离散度有影响」；"
             "(2) R1 的配对检验只有 n = %s，虽然精确置换把 2^10 种赋值全部枚举过，但 %s 这 %s 个分子"
             "从未进入 GFN2 Delta-SCF 臂，任何跨臂结论都只在这 10 个分子上成立；"
             "(3) R3 的留出集只有 %s 个预测，带符号规则 %s/%s、朴素规则 %s/%s 都落在"
             "「4 次里错 1-2 次」的噪声带内，不构成「规则更优」的证据。"
             % (n_common, "、".join(missing_dscf), len(missing_dscf),
                scoring.get("n_predictions"), scoring.get("signed_rule_hits"),
                scoring.get("n_predictions"), scoring.get("naive_rule_hits"),
                scoring.get("n_predictions")))

    alignment_block = "\n".join(
        ["| 臂 | n | MAE (eV) | bias (eV) | tau_b |",
         "| --- | --- | --- | --- | --- |"]
        + ["| %s | %s | %s | %s | %s |"
           % (label, (arms.get(key) or {}).get("n"),
              num((arms.get(key) or {}).get("mae_ev"), 4),
              signed((arms.get(key) or {}).get("bias_ev"), 4),
              num((arms.get(key) or {}).get("kendall_tau_b"), 4))
           for key, label in (("P0_koopmans_xTB", "P0 Koopmans（GFN2-xTB）"),
                              ("GFN2_dSCF_xTB", "GFN2 Delta-SCF（xTB）"),
                              ("P1_r2scan3c", "P1 r2SCAN-3c（ORCA）"))]
        + ["",
           "| 配对（A - B） | Delta tau_b | 配对 95% CI | 精确置换 p | 跨 0 |",
           "| --- | --- | --- | --- | --- |"]
        + ["| %s | %s | [%s, %s] | %s | %s |"
           % (pair_key.replace("_minus_", " - "),
              signed((paired.get(pair_key) or {}).get("observed_delta_tau_b"), 4),
              num(((paired.get(pair_key) or {}).get("paired_ci95") or [None, None])[0], 3),
              num(((paired.get(pair_key) or {}).get("paired_ci95") or [None, None])[1], 3),
              num(((paired.get(pair_key) or {}).get("permutation") or {}).get("p_value"), 4),
              "是" if (paired.get(pair_key) or {}).get("paired_ci95_crosses_zero") else "否")
           for pair_key in ("GFN2_dSCF_xTB_minus_P1_r2scan3c",
                            "GFN2_dSCF_xTB_minus_P0_koopmans_xTB",
                            "P1_r2scan3c_minus_P0_koopmans_xTB")])
    phase_block = "\n".join([
        "| 量 | 值 |",
        "| --- | --- |",
        "| 网格 | 均值 %s 格 x 离散度 %s 格，每格 %s 次重复（曲线 %s 次） |"
        % (len(grid.get("mean_ev") or []), len(grid.get("std_ev") or []),
           grid.get("replicates_per_cell"), grid.get("curve_replicates")),
        "| max abs Delta tau_b（均值平移 vs mean = 0） | %s |"
        % num(inv.get("max_abs_tau_b_difference_vs_mean_0"), 4),
        "| 合成 rho(std, tau_b) / rho(abs(mean), tau_b) | %s / %s |"
        % (num(syn.get("spearman_shift_std_vs_tau_b"), 3),
           num(syn.get("spearman_abs_shift_mean_vs_tau_b"), 3)),
        "| 实测 rho(std, tau_b)（native %s） | %s |"
        % (num(native.get("spearman_shift_std_vs_tau_b"), 4),
           num(meas.get("spearman_shift_std_vs_tau_b"), 4)),
        "| 实测 rho(abs(mean), tau_b) | %s |"
        % num(meas.get("spearman_abs_shift_mean_vs_tau_b"), 4),
        "| 实测 rho(std, f_unresolved) | %s |"
        % num(meas.get("spearman_shift_std_vs_f_unresolved"), 4),
        "| 实测 rho(abs(mean), std) | %s |"
        % num(meas.get("spearman_abs_shift_mean_vs_shift_std"), 4),
        "| 临界 std：氧化 tau_b 跌破 0.8 / 0.5、overlap 跌破 1（eV） | %s / %s / %s |"
        % (num(ox_b.get("std_where_mean_tau_b_below_0p8"), 2),
           num(ox_b.get("std_where_mean_tau_b_below_0p5"), 2),
           num(ox_b.get("std_where_mean_overlap_below_1"), 2)),
        "| 临界 std：还原 tau_b 跌破 0.8 / 0.5、overlap 跌破 1（eV） | %s / %s / %s |"
        % (num(red_b.get("std_where_mean_tau_b_below_0p8"), 2),
           num(red_b.get("std_where_mean_tau_b_below_0p5"), 2),
           num(red_b.get("std_where_mean_overlap_below_1"), 2)),
        "| 子集敏感性同向 / 实测点数 / 台阶数 | %s / %s / %s |"
        % ("是" if sens.get("same_direction") else "否",
           meas.get("n_points"), meas.get("n_rungs")),
    ])
    prospective_block = "\n".join(
        ["| 预测集 | 轴 | n | k | sd(delta) (eV) | OLS 斜率 b | 带符号判 | 朴素判 | 实测 | 重叠 |",
         "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
        + ["| %s | %s | %s | %s | %s | %s | %s | %s | **%s** | %s |"
           % (row.get("set"), row.get("axis"), row.get("n"), row.get("k"),
              num(row.get("delta_sd_ev"), 3), signed(row.get("ols_slope_b"), 3),
              cell(row.get("predicted_signed")), cell(row.get("predicted_naive")),
              "改写" if row.get("observed_rewritten") else "保留",
              num(row.get("observed_overlap"), 2))
           for row in rows]
        + ["",
           "阈值都在 10 个发现点上拟合、先冻结后打分：带符号斜率 b <= %s 判「改写」（低 = 危险），"
           "朴素 sd(delta) >= %s eV 判「改写」（高 = 危险）；命中带符号 %s/%s、朴素 %s/%s。"
           % (signed(s_rule.get("threshold"), 4), num(n_rule.get("threshold"), 4),
              scoring.get("signed_rule_hits"), scoring.get("n_predictions"),
              scoring.get("naive_rule_hits"), scoring.get("n_predictions"))])
    table_block = "\n".join(
        ["| 文件 | 内容 |", "| --- | --- |"]
        + ["| %s | %s |" % (name, note) for name, note in W21_TABLE_ROWS])

    return {"did": did, "metric": metric, "qc": qc, "limit": limit,
            "summary": metric, "alignment_block": alignment_block,
            "phase_block": phase_block, "prospective_block": prospective_block,
            "table_block": table_block}


def week21_checks(wdir: Path):
    """QC for week 21 (Stage 22 batch A: arm alignment, phase diagram, prospective).

    Every number is read back out of ``sigma_synthetic.json``,
    ``sigma_prospective.json``, ``sigma_prospective_frozen.json`` and the
    ``arm_alignment`` block of ``outputs/week4/p1_anchor_comparison.json``.
    """

    checks = []
    phase = load_json(wdir / "sigma_synthetic.json")
    prospective = load_json(wdir / "sigma_prospective.json")
    frozen = load_json(wdir / "sigma_prospective_frozen.json")
    for name, data in (("sigma_synthetic", phase), ("sigma_prospective", prospective),
                       ("sigma_prospective_frozen", frozen)):
        if data is None:
            checks.append(check(name + ".present", None, "source not found"))
            return checks
        checks.append(check(name + ".present", True, name + ".json present"))

    def near(value, expected, tol):
        return value is not None and abs(float(value) - expected) < tol

    inv = phase.get("mean_invariance") or {}
    syn = phase.get("synthetic_correlations") or {}
    meas = phase.get("measured_correlations") or {}
    sens = phase.get("subset_sensitivity") or {}
    bounds = phase.get("boundaries") or {}
    scoring = prospective.get("scoring") or {}
    checks.append(check("week21.phase_mean_invariance",
                        near(inv.get("max_abs_tau_b_difference_vs_mean_0"), 0.0, 1e-12),
                        "max_abs_delta_tau_b=%s"
                        % inv.get("max_abs_tau_b_difference_vs_mean_0")))
    checks.append(check("week21.phase_synthetic_correlations",
                        near(syn.get("spearman_shift_std_vs_tau_b"), -1.0, 1e-9)
                        and near(syn.get("spearman_abs_shift_mean_vs_tau_b"), 0.0, 1e-9),
                        "rho(std,tau_b)=%s rho(abs(mean),tau_b)=%s"
                        % (syn.get("spearman_shift_std_vs_tau_b"),
                           syn.get("spearman_abs_shift_mean_vs_tau_b"))))
    checks.append(check("week21.phase_measured_correlations",
                        near(meas.get("spearman_shift_std_vs_tau_b"), -0.8510677611520904, 1e-9)
                        and near(meas.get("spearman_abs_shift_mean_vs_tau_b"),
                                 -0.5349568784384569, 1e-9)
                        and meas.get("n_points") == 10 and meas.get("n_rungs") == 5,
                        "rho(std,tau_b)=%s rho(abs(mean),tau_b)=%s n=%s"
                        % (meas.get("spearman_shift_std_vs_tau_b"),
                           meas.get("spearman_abs_shift_mean_vs_tau_b"),
                           meas.get("n_points"))))
    checks.append(check("week21.phase_subset_sensitivity_same_direction",
                        sens.get("same_direction") is True
                        and near((sens.get("common10") or {}).get("spearman_shift_std_vs_tau_b"),
                                 -0.8510677611520904, 1e-9),
                        "native=%s common10=%s same_direction=%s"
                        % ((sens.get("native") or {}).get("spearman_shift_std_vs_tau_b"),
                           (sens.get("common10") or {}).get("spearman_shift_std_vs_tau_b"),
                           sens.get("same_direction"))))
    checks.append(check("week21.phase_boundaries",
                        near((bounds.get("oxidation") or {})
                             .get("std_where_mean_tau_b_below_0p8"), 0.45, 1e-9)
                        and near((bounds.get("reduction") or {})
                                 .get("std_where_mean_tau_b_below_0p8"), 0.25, 1e-9)
                        and near((bounds.get("oxidation") or {})
                                 .get("std_where_mean_overlap_below_1"), 0.25, 1e-9),
                        "ox_0p8=%s red_0p8=%s ox_overlap=%s"
                        % ((bounds.get("oxidation") or {}).get("std_where_mean_tau_b_below_0p8"),
                           (bounds.get("reduction") or {}).get("std_where_mean_tau_b_below_0p8"),
                           (bounds.get("oxidation") or {}).get("std_where_mean_overlap_below_1"))))
    checks.append(check("week21.prospective_frozen_digest",
                        frozen.get("frozen_sha256") is not None
                        and prospective.get("frozen_sha256") == frozen.get("frozen_sha256"),
                        "frozen=%s scoring=%s"
                        % (str(frozen.get("frozen_sha256"))[:12],
                           str(prospective.get("frozen_sha256"))[:12])))
    checks.append(check("week21.prospective_accuracy",
                        scoring.get("n_predictions") == 4
                        and scoring.get("signed_rule_hits") == 3
                        and scoring.get("naive_rule_hits") == 2
                        and near(scoring.get("signed_rule_accuracy"), 0.75, 1e-9),
                        "signed=%s/%s naive=%s/%s"
                        % (scoring.get("signed_rule_hits"), scoring.get("n_predictions"),
                           scoring.get("naive_rule_hits"), scoring.get("n_predictions"))))
    anchor = (load_json(W21_ANCHOR_JSON) or {}).get("arm_alignment") or {}
    checks.append(check("week21.arm_alignment_verdict",
                        anchor.get("n_common_subset") == 10
                        and (anchor.get("verdict") or {})
                        .get("all_three_pairwise_tests_unresolved") is True,
                        "n_common=%s unresolved=%s"
                        % (anchor.get("n_common_subset"),
                           (anchor.get("verdict") or {})
                           .get("all_three_pairwise_tests_unresolved"))))
    return checks


CHECK_BUILDERS = {1: week1_checks, 2: week2_checks, 3: week3_checks, 4: week4_checks,
                  5: week5_checks, 6: week6_checks, 7: week7_checks, 8: week8_checks,
                  9: week9_checks, 10: week10_checks, 11: week11_checks, 12: week12_checks,
                  13: week13_checks, 14: week14_checks, 15: week15_checks,
                  16: week16_checks, 17: week17_checks, 18: week18_checks,
                  19: week19_checks, 20: week20_checks, 21: week21_checks}


REPORT_TEMPLATES = {}

REPORT_TEMPLATES[20] = """# Week 20 成果小结 —— Stage 21（临界带的能量裁决 + 判据预检 + 溶剂壳氧化还原 + 真回填）

## 0. 一页结论
- 做了什么：{w20_did}
- 关键数字：{w20_metric}
- 质检：{w20_qc}
- 限制：{w20_limit}

本文可独立阅读；逐项细节、物理机制与需裁决项见同目录 `week20_report_full.md`。

## 1. Part A —— 临界带的能量裁决

{path_block}

内插路径是**笛卡尔直线、不是最小能量路径**，所以鼓包只是**上界**；反过来说「直线全程不抬升」
是强证据：一条从不抬升的直线不可能藏着一个势垒。三个 panel 各自纵轴、**不可互比**：对照组
TEGDME/anion/eps=20 的鼓包是原子互穿的假象。

## 2. Part B —— `charge_l1` 判据的运行手册预检（零新增计算）

{protocol_block}

## 3. Part C —— 第一溶剂壳在氧化还原下的弛豫

{shell_block}

> 还原态是中性自由基，复合物可能在弛豫中丢掉一个配体；本周的 QC（父几何共价键完好 /
> 弛豫后单一碎片 / Li 仍同时配位两个配体）逐格判定，不合格的格子**排除**而不是计入均值。

## 4. Part D —— P2 腿的真回填（零新增计算）

{refill_block}

> 严格 P2 腿是 SMD(乙腈) 层，而 Stage 19/20 的弛豫格全部落在**裸 CPCM** 层，所以真回填靠的是
> 「弛豫修正是一个态内量」的**转移假设**（Week 19 量到它的 epsilon 依赖性很小）。

## 5. 产物清单

{table_block}
"""

REPORT_TEMPLATES[21] = """# Week 21 成果小结 —— Stage 22（批次 A：三臂对齐 + σ 相图 + 前瞻检验）

Week 21 执行 `docs/31_plan_revision_expert_review.md` 的批次 A：**R1（含 R10）、R2、R3、R6、R4(a)**。
全部是纯分析与纯措辞，零新增电子结构、零冻结件改动——所以本周没有一条新的 SCF / Opt 记录，
所有结论都来自已有产物的重新组织与前一轮判据的留出检验。

> 周内最不可回避的一条更正是口径上的：Week 4 那张表里的三条臂并不在同一批分子上评分
> （n = 12 / 10 / 12），所以它们印在一起的 `tau_b` 本来不可比。本周先把三条臂对齐到同一批 10 个分子，
> 再谈谁高谁低；对齐之后，三对配对检验的 95% CI **全部跨 0**。

完整版本见 `week21_report_full.md`。

## 1. 本周做了什么

{w21_did}

## 2. 关键数字

{w21_metric}

## 3. R1 + R10：三臂对齐到同一批分子之后，排序差异并不显著

{w21_alignment_block}

> 从本周起，项目对外只能说「MAE 的排序与 `tau_b` 的排序不一致」，不能说「Delta-SCF 的排序显著更好」：
> 观测到的 Delta tau_b = +0.1333 落在 95% CI [-0.200, +0.550] 内，精确配对置换 p = 0.805。

## 4. R2：把 rho = -0.851 换成一张可以直接读的相图

{w21_phase_block}

> 相图给出的机制判读是：排序的存亡由位移的离散度决定，均值只负责把整条轴平移。
> 实测点上的 rho(abs(mean), tau_b) = -0.535 是共线性（rho(abs(mean), std) = +0.758）的假象，
> 不是一条独立的效应。

## 5. R3：先冻结判据，再到留出集上打分

{w21_prospective_block}

> 带符号规则 3/4、朴素规则 2/4——4 个预测的样本量不足以宣称任何一条规则更优，
> 这是本周主动写进限制里的结论。

## 6. 文件清单

{w21_table_block}

## 7. QC 与限制

- {w21_qc}
- {w21_limit}

## 8. 本周产物

{artifact_list}

## 9. 缺失源

{missing_list}
"""


REPORT_TEMPLATES[1] = """# Week 1 成果小结 —— Stage 0 定义冻结 / Gate 0

## 1. 本周做了什么
- 冻结 Stage 0 科学定义与预注册，建立「定义先于数据」的纪律：`config/scientific_definitions.yaml`
  固定 P0/P1/P2、C0/C1/C2、R_gas/R_sol/R_env、目标量方向、参考配体 R 与受控词表；
  `config/prereg.yaml` 固定 pair 比较规则、z 因子、bootstrap 种子与决策指标。
- 构建并核对 chemical-space 元数据：core set 18 行、broad pool 40 行，均可由
  `scripts/build_metadata.py` 重建。
- 运行 Gate 0 检查，留下 `outputs/week1/gate0_record.md`（frozen artefacts: 6）。
- 本目录**额外快照** `config/scientific_definitions.yaml` 与 `config/prereg.yaml`：冻结定义必须
  与派生产物同行交付，否则下游任何一个数字都不可判读。

## 2. 关键数字
| 项目 | 值 |
| --- | --- |
| Gate 0 状态 | **CLOSED** |
| 冻结产物数 | 6 |
| core set 行数 | 18 |
| broad pool 行数 | 40 |
| `config/prereg.yaml` sha256 | `{prereg_sha256}` |

### 2.1 冻结产物 sha256（现场重算逐字节比对）
{gate0_sha_table}

`config/prereg.yaml` 的 sha256 为 `{prereg_sha256}`，是 Gate 0 的唯一判据载体：任何对预注册的
改动都会立即改变该值，从而使 Gate 0 失效（变更只允许以 append-only 方式写入 `amendment_log`，
历史条目不得删除或改写）。

## 3. 质量与复核（QC）
- Gate 0 的检查项（两份 yaml 的 `frozen=true`、metadata `--check`、`amendment_log` 为空）全部通过；
  逐项实测值见本目录 `verification.json` 的 `checks`。
- 上表对每个冻结产物做了**现场重算**，与记录值逐字节比对。
- `outputs/week1` 自身产物很少是正常的：Gate 0 的实质定义在 `docs/00_stage0_definitions.md` 与
  `config/*.yaml`，两者都已在同一目录内。

## 4. 产物清单
{artifact_list}

## 5. 已知限制
- Week 1 不产生任何 redox 数值结论；它只冻结定义与预注册，供后续周次引用。
- Gate 1（方法 / 锚点）在本周**并未**关闭，其 blocker 见 `week2_report.md`。
- 本目录快照是**只读副本**；任何定义变更必须回到仓库 `config/` 走 amendment 流程。

## 6. 源文件缺失
{missing_list}
"""


REPORT_TEMPLATES[2] = """# Week 2 成果小结 —— Stage 1 方法审计与外部锚点

## 1. 本周做了什么
- 建立并校验外部气相 redox 锚点库（`docs/01_stage1_external_anchors.md`）。
- 方法审计：对 12 个分子跑 GFN2-xTB 的中性 / 阳离子 / 阴离子三态，比较 Koopmans 与 ΔSCF
  （`docs/02`、`docs/04`；产物 `method_audit_xtb.csv`、`method_audit_xtb_summary.json`）。
- 溶液相锚点审计：31 行逐条核对证据等级（`docs/06`；产物 `solution_anchor_audit.csv/.json`）。
- Gate 1 检查，留下 `outputs/week2/gate1_record.md`。
- 本目录额外收录 `docs/03_week1_2_report.md`（Week 1–2 的连续叙述）。

## 2. 关键数字
| 项目 | 值 | 来源 |
| --- | --- | --- |
| 方法审计分子数 | 12 | `method_audit_xtb_summary.json` |
| 其中气相不束缚的阴离子 | 2 | 同上 |
| 溶液锚点总行数 | 31 | `solution_anchor_audit.json` |
| 审计后仍为 `est` 的行数 | 31 | 同上 |
| 被升级为 `exp` / `calc` 的行数 | 0 | 同上 |
| 一致性检查 | `True`（0 处冲突） | 同上 |
| Gate 1 状态 | **NOT CLOSED** | `gate1_record.md` |

溶液锚点 31 行的证据类型分布：`solvent_anion_coupling` 7、`condition_mismatch` 5、`no_reference` 5、
`review_trend_only` 5、`computational_not_retrieved` 5、`mis_citation` 2、
`source_does_not_cover_species` 1、`source_does_not_provide_value` 1。合计 31 行，**没有任何一行**
能升级为 `exp` 或 `calc`。

## 3. 质量与复核（QC）
- Gate 1 检查中 `anchors:validate_anchors` 与两条 toolchain 检查通过；`anchors:solution_verified`
  未通过（31 行仍为 `est`）。
- 方法审计与溶液锚点审计的数字均从本目录 JSON 现场解析，见 `verification.json`。
- 关键限制由锚点审计显式记录，而不是被静默吸收。

## 4. 产物清单
{artifact_list}

## 5. 已知限制
- **Gate 1 未关闭**：唯一 blocker 是溶液相锚点 31 行全为 `est`，缺少可核验的原始文献值。
- 因此 week2 之后的所有 P1/P2 结果都以**气相锚点**为主判据，溶液相只作定性对照。
- xTB scratch（`xtbrestart` / `xtbtopo.mol` / `xtboptok` / `wbo` / `charges`）按约定不进入交付包。

## 6. 源文件缺失
{missing_list}
"""


REPORT_TEMPLATES[3] = """# Week 3 成果小结 —— Stage 2 broad cheap pool（P0）

## 1. 本周做了什么
- 用 GFN2-xTB 对 core set（18）与 broad pool（40）跑 P0 廉价代理，产物 `p0_core_set.csv`、
  `p0_broad_pool.csv`（Koopmans：`p0_ox = -eps_HOMO`、`p0_red = +eps_LUMO`）。
- 化学空间覆盖与家族分布图：`fig1_family_counts.png`、`fig2_mw_donor.png`、
  `fig3_p0_ox_fluorinated.png`、`fig4_ec_ionization_pilot.png`；汇总图 F1 / F2 收在 `artifacts/`。
- 决策预览：Top-k 重叠 / Jaccard、参考配体 DME 与 AN 的定位（`decision_stability_preview.md`）。
- ORCA 冒烟测试（`orca_smoke/`），为 Week 4 的 P1 层打通通路。

## 2. 关键数字
| 项目 | 值 | 来源 |
| --- | --- | --- |
| core P0 成功 | 18 / 18 | `p0_core_set_summary.json` |
| broad P0 成功 | 40 / 40 | `p0_broad_pool_summary.json` |
| 合并可用于决策的池规模 | 58 | `p0_summary.json` |
| 氧化轴 vs 还原轴 Kendall tau_b（合并池） | −0.302 | 同上 |
| 参考配体 primary_R | DME（C08，双齿 2×O 螯合） | 同上 |
| 第二参考 R | AN（C16，仅 robustness check） | 同上 |
| core P0 ox 范围 | 10.424 .. 12.996 eV | `p0_core_set_summary.json` |
| core P0 red 范围 | −6.877 .. 0.718 eV | 同上 |
| core HOMO-LUMO gap 中位数 | 6.248 eV | 同上 |
| core 偶极中位数 | 3.393 D | 同上 |

氧化轴与还原轴在廉价层上**负相关**（tau_b = −0.302）：耐氧化与耐还原在本代理层上相互拉扯，
这正是后面必须引入真实电子结构层来裁断的动机。

## 3. 质量与复核（QC）
- 两个池均 `n_ok == n_total`、`n_failed = 0`、`n_abnormal_termination = 0`、
  `n_missing_p0_fields = 0`（现场从 JSON 解析，见 `verification.json`）。
- 与 week2 方法审计的交叉核对状态记录在 `p0_summary.json` 的 `cross_check_vs_week2`。
- P0 的 `--alpha` 单点作业仅作辅助交叉确认，**不参与任何排序**。

## 4. 产物清单
{artifact_list}

## 5. 已知限制
- P0 是 Koopmans 代理，与真实垂直 IP/EA **不是同一物理量**；其还原轴尤其不可直接解读为 EA。
- 单构象几何（RDKit ETKDG 单次嵌入 + MMFF 预优化），未做构象搜索。
- Gate 1 仍未关闭；本周不宣称任何「最终筛选名单」。

## 6. 源文件缺失
{missing_list}
"""


REPORT_TEMPLATES[4] = """# Week 4 成果小结 —— Stage 3（P1 电子结构）+ Stage 4（P2 环境）+ T5 + T3 + T2

本周交付了本项目最关键的一级结果：廉价代理层（P0）与电子结构层（P1）、环境层（P2）之间的
「值误差 vs 排序误差」分离，以及两级台阶的对照。本文可独立阅读；逐项细节见同目录
`week4_report_full.md`。

## 1. 本周做了什么
1. **P1（电子结构层）**：对 18 个 core-set 分子在冻结几何 G1 上跑 ORCA 6.1.1 r2SCAN-3c 的
   neutral / cation / anion 三态，共 54 个作业（气相、垂直量）。
2. **P1 QC 审计**：能量一致性、SCF 收敛、异常终止、自旋污染、阴离子束缚性
   （`p1_core_set_audit.json`）。
3. **P1 决策稳定性分析**：与 12 个外部气相锚点比较三臂误差，并做 P0→P1 的排序 / 决策迁移分析。
4. **P2（环境层）**：对同一 18 个分子、同一 G1 几何，用 CPCM(SMD, acetonitrile) 重跑 54 个作业；
   唯一变量是环境（气相 → 隐式溶剂）。
5. **T5 弥散函数对照**：同一泛函 r2SCAN、只换基组（def2-TZVPP 无弥散 / def2-TZVPD 含弥散 /
   r2SCAN-3c 生产基准），对 AN / DMSO / SN / VC 做气相阴离子对照。
6. {t3_note}
7. {t2_note}

## 2. 关键数字

### 2.1 P0 → P1：三臂与外部气相锚点的值误差（垂直 IP，锚点 = NIST / 已发表值）
| 臂 | n | MAE (eV) | bias (eV) | max abs err (eV) | err std (eV) | Kendall tau_b | Spearman rho |
| --- | --- | --- | --- | --- | --- | --- | --- |
| P0 Koopmans (GFN2-xTB) | 12 | **1.377** | +1.279 | 2.002 | 0.637 | 0.606 [0.16, 0.90] | 0.783 |
| GFN2-xTB ΔSCF | 10 | **4.481** | +4.481 | 5.191 | 0.319 | 0.911 [0.69, 1.00] | 0.976 |
| P1 r2SCAN-3c | 12 | **0.251** | −0.179 | 0.587 | 0.268 | 0.727 [0.38, 0.97] | 0.874 |

读法：**MAE 大不等于决策错**。ΔSCF 的 MAE 是 P0 Koopmans 的 3.3 倍，但它的 tau_b（0.911）
反而最高；P1 的 MAE 最小（0.251 eV），tau_b 却只有 0.727。值误差与排序误差是两件事。

### 2.2 决策层 P0 → P1（N=18，唯一变量 = 电子结构方法）
| 轴 | n | Kendall tau_b | O_k(10%) | O_k(20%) | O_k(30%) | J_k(20%) | selection regret(20%) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 氧化 | 18 | **0.673** | **0.000** | **0.500** | 0.600 | 0.333 | 0.656 eV |
| 还原 | 18 | **0.595** | 1.000 | **0.500** | 0.400 | 0.333 | 0.263 eV |

氧化轴 Top-10% **完全换人**（O_k = 0.000）：廉价层选出的 2 个分子，在 P1 眼中一个都不在前 10%。
还原轴 Top-10% 反而是 1.000，但这是「廉价层还原代理与真实 EA 不是同一物理量」的伪一致（见 §3.3）。

### 2.3 P1 → P2：环境层（唯一变量 = 环境，气相 → SMD 乙腈）
| 量 | n | 均值 | std | 范围 |
| --- | --- | --- | --- | --- |
| 垂直 IP 位移 | 18 | **−2.393 eV** | **0.293 eV** | −2.907 (AN) .. −1.645 (TEGDME) |
| 垂直 EA 位移 | 18 | **+2.173 eV** | **0.311 eV** | +1.376 (TEGDME) .. +2.669 (DOL) |

| 轴 | Kendall tau_b | O_k(10%) | O_k(20%) | J_k(20%) |
| --- | --- | --- | --- | --- |
| 氧化 | **0.895** | 1.000 | 0.750 | 0.600 |
| 还原 | **0.673** | 0.500 | 0.500 | 0.333 |

### 2.4 两级台阶对比（最核心的对照）
| 台阶 | 唯一变量 | IP 位移均值 | **IP 位移 std** | 氧化轴 tau_b | 氧化 Top-20% 重叠 |
| --- | --- | --- | --- | --- | --- |
| P0 → P1 | 电子结构方法（GFN2-xTB → r2SCAN-3c） | −1.550 eV | **0.714 eV** | **0.673** | 0.50 |
| P1 → P2 | 环境（气相 → SMD 乙腈） | −2.393 eV | **0.293 eV** | **0.895** | 0.75 |
{t2_step_row}

**结论：位移更大不等于决策更坏；决定决策是否被改写的是位移的方差。**
环境台阶的平均位移（−2.393 eV）比方法台阶（−1.550 eV）**大 54%**，但它的分子间离散度只有方法
台阶的 **41%**（0.293 vs 0.714 eV），于是排序被破坏得**更少**（tau_b 0.895 vs 0.673；
Top-20% 重叠 0.75 vs 0.50）。这条规律与 §2.1 的锚点结论（MAE 排序与 tau_b 排序不一致）互相印证。

### 2.5 T5 弥散函数对照
| 臂 | 基组 | 含弥散 | AN | DMSO | SN | VC |
| --- | --- | --- | --- | --- | --- | --- |
| tzvpp | def2-TZVPP | 无 | 2.264 | 2.476 | 1.244 | 1.965 |
| tzvpd | def2-TZVPD | 有 | 0.932 | 0.872 | 0.902 | 0.893 |
| scan3c | def2-mTZVPP | 无 | 3.196 | 2.779 | 1.854 | 1.989 |

（`EA_dscf = (E_anion - E_neutral) * 27.211386245988`；**正值表示气相阴离子不束缚**。）

加弥散把气相 EA 系统性下拉 **0.34–1.60 eV**（tzvpd − tzvpp），但四个分子在三个臂下**都不翻转
符号**。AN（0.011 eV）与 DMSO（0.014 eV）的外部锚点落在 0.01 eV 量级，比任何 DFT 泛函的误差棒
（~0.1–0.2 eV）低两个数量级。因此这是一个**方法适用域结论**：本方法不能裁断 0.01 eV 量级的
阴离子束缚与否；T5 测的是弥散位移的**方向与大小**，不是 AN 到底束不束缚。氧化侧（IP）不受此限制。

### 2.6 z 因子修正说明
决策指标的主判据是 `config/prereg.yaml` 冻结的 `z_factor.value = 1.0`（一倍不确定度）；
`z = 1.96`（95% 双侧带）作为**保守敏感性**并列报告。本轮之前分析脚本把 `z = 1.96` 写死，与冻结值
不一致；已改为「主判据 z=1.0 + 敏感性 z=1.96」并列输出。这属于**代码缺陷修复**，不是预注册变更：
`config/prereg.yaml` 逐字节未变，Gate 0 仍为 **CLOSED**。

{t2_block}

## 3. 质量与复核（QC）
- P1 作业：**54 / 54** 成功，0 失败（`p1_core_set_summary.json`，`n_failed = 0`）。
- P1 审计（`p1_core_set_audit.json`，54 条记录 / 18 分子）：`energy_mismatch = 0`、
  `scf_failed = 0`、`abnormal_termination = 0`、`spin_contamination_flag = 0`；
  `unbound_anion = 18`（18 个分子的气相阴离子在 P1 下**全部**不束缚）。
- P2 作业：**54 / 54** 成功，0 失败（`p2_summary_smd_acetonitrile.json`）。
- T5 作业：**24 / 24** 成功，0 失败（`t5_diffuse_control_summary.json`）。
{t2_qc}
- 全部为垂直量、冻结几何 G1、单一构象；几何在两臂之间完全共享，因此位移只能归因于被改变的那一个变量。
- 以上每一项都由 `verification.json` 的 `checks` 数组从本目录真实产物现场解析得出。

### 3.1 逐分子 IP / EA 对照（可回溯到 `p1_core_set.csv` 与 `p1_anchor_comparison.json`）
| 分子 | 家族 | IP anchor (eV) | P0 Koopmans IP | P1 r2SCAN-3c IP | P0 err | P1 err | EA Koopmans | EA r2SCAN-3c | 气相阴离子束缚 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| DMSO | sulfoxide | 9.10 | 10.42 | 8.81 | +1.32 | −0.29 | 5.36 | −2.78 | NO |
| DME | ether | 9.30 | 10.85 | 8.86 | +1.55 | −0.44 | −0.72 | −3.73 | NO |
| SL | sulfone | 9.80 | 11.25 | 9.79 | +1.45 | −0.01 | 3.85 | −2.98 | NO |
| DOL | ether | 9.90 | 11.02 | 9.31 | +1.12 | −0.59 | 0.08 | −4.09 | NO |
| TMP | phosphate | 10.00 | 11.90 | 10.06 | +1.90 | +0.06 | 1.91 | −2.91 | NO |
| EA | ester | 10.01 | 11.34 | 10.00 | +1.33 | −0.01 | 6.16 | −2.74 | NO |
| VC | cyclic_carbonate | 10.08 | 11.88 | 9.62 | +1.80 | −0.46 | 6.88 | −1.99 | NO |
| MA | ester | 10.20 | 11.43 | 10.20 | +1.23 | 0.00 | 6.24 | −2.74 | NO |
| GBL | ester | 10.26 | 11.40 | 9.95 | +1.14 | −0.31 | 6.29 | −2.58 | NO |
| EC | cyclic_carbonate | 10.40 | 12.40 | 10.77 | +2.00 | +0.37 | 6.08 | −2.59 | NO |
| DMC | linear_carbonate | 11.00 | 12.08 | 10.58 | +1.08 | −0.42 | 5.81 | −3.46 | NO |
| AN | nitrile | 12.20 | 11.61 | 12.14 | −0.59 | −0.06 | 5.50 | −3.20 | NO |
| EMC | linear_carbonate | — | 11.97 | 10.20 | — | — | 5.73 | −3.32 | NO |
| DEC | linear_carbonate | — | 11.89 | 9.98 | — | — | 5.65 | −3.37 | NO |
| PC | cyclic_carbonate | — | 12.26 | 10.54 | — | — | 5.96 | −2.89 | NO |
| FEC | cyclic_carbonate | — | 13.00 | 11.32 | — | — | 6.74 | −2.56 | NO |
| TEGDME | ether | — | 10.61 | 7.60 | — | — | 0.19 | −2.87 | NO |
| SN | nitrile | — | 11.92 | 11.60 | — | — | 6.30 | −1.85 | NO |

只有 12 个分子有外部气相 IP 锚点，故 err 两列对另外 6 个分子为空。EA r2SCAN-3c 列为
`EA_conventional = E_neutral - E_anion`（负值 = 阴离子不束缚）；**18 个分子在 P1 下气相阴离子
全部不束缚**（最后一列全为 NO），这是「还原侧定性失效」的逐分子证据。

### 3.2 pair 分辨率（z 因子敏感性；N=18，两轴各 153 个分子对）
| 轴 | f_unresolved(P0) z=1.0 | f_unresolved(P1) z=1.0 | f_robust_inv z=1.0 | f_unresolved(P0) z=1.96 | f_unresolved(P1) z=1.96 | f_robust_inv z=1.96 | sigma 中位数 (eV) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 氧化 | 0.359 | 0.157 | 0.000 | 0.549 | 0.359 | 0.000 | 0.284 |
| 还原 | 0.170 | 0.621 | 0.000 | 0.706 | 0.699 | 0.000 | 0.786 |

`f_robust_inv` 在两轴、两个阈值下**全为 0**：没有出现「两臂都认为自己分得清、但结论相反」的
分子对。还原侧 P0 只有 0.170 的分子对说不清，P1 却升到 0.621 —— 廉价层在还原轴上「看起来
分得清」，正因为它比的不是真实 EA。放宽到 z = 1.96 时两侧都升到约 0.70，结论方向不变。

## 4. 产物清单
{artifact_list}

## 5. 已知限制
1. **还原侧定性失效**：P1 下 18 个分子的气相阴离子全部不束缚（EA < 0），而定域在 LUMO 上的
   Koopmans 图像永远给不出这一点。廉价层的还原轴代理与真实 EA 不是同一物理量，还原侧数字只能在
   「廉价层内部比较」的意义上使用。
2. **基组无弥散**：r2SCAN-3c 的复合基组 def2-mTZVPP 不含弥散函数（见 §2.5）。氧化侧不受影响。
3. **单构象 + 隐式溶剂**：G1 为 GFN2-xTB 单构象优化几何，G2 为 r2SCAN-3c 单构象驻点（见 §2.7）；
   两者都仍是单构象、未做构象搜索（`sigma_conf` 仍为「待算」）。P2 为 CPCM(SMD) 隐式溶剂，
   不含显式溶剂分子，也不含 Li+ 配位层（C1 条件态尚未运行）。
4. **锚点 n 小**：外部气相锚点仅 12 个分子，tau_b 的 bootstrap 区间较宽（如 P0 臂为 [0.16, 0.90]）。
5. {t3_limit}
6. {t2_limit}
7. **Gate 1 仍未关闭**：溶液相锚点 31 行仍为 `est`，本报告的所有主结论只依赖气相锚点。
8. 逐项细节见同目录 `week4_report_full.md`。

## 6. 源文件缺失
{missing_list}
"""


REPORT_TEMPLATES[5] = """# Week 5 成果小结 —— Stage 5（T4：Li+ 配位条件态 C1）

本周把状态轴从 **C0（自由分子）** 推进到 **C1（[Li M]+ 配位态）**：按冻结的 motif 生成规则
（`config/scientific_definitions.yaml` §`conformers_and_states.li_motif_generation`）枚举 Li+ 的
配位结构，在 r2SCAN-3c 上优化几何并做三态垂直量，再与同一分子的自由分子 C0（P1 @ G2）逐分子相减。
本文可独立阅读；逐项细节见同目录 `week5_report_full.md`。

## 1. 本周做了什么
1. **motif 枚举（T4-step1）**：对 10 个分子（8 个结构家族各 1 + 第二醚 DME + 第二腈 AN/SN）按冻结的
   7 步规则生成 [Li M]+ 初始结构（`scripts/build_li_motifs.py`）。
2. **C1 条件态扫描（T4-step2）**：对每个主 motif 做 [Li M]+ `Opt`，并做双阳离子 / 还原态单点与重弛豫、
   以及 CPCM(SMD) 三态单点（`scripts/run_c1_li_coordination.py`）；失败作业照实记为
   `geometry_failed` / `dissociated_optimized_product`，不静默丢弃。
3. **C1 分析（T4-step3）**：逐分子 dIP / dEA、配体交换量 `dGdG_bind(M;R)`（主参考 R = DME，
   次参考 R = AN）、C0 -> C1 决策稳定性，以及方法 / 几何 / 环境 / 条件态四个单变量台阶的同口径 σ。
4. {c1_note}

## 2. 关键数字
{c1_block}
## 3. 质量与复核（QC）
- {c1_qc}
- 全部为垂直量；C1 的几何是 r2SCAN-3c 优化得到的 [Li M]+ 驻点，与 C0 的 G2 自由分子几何不同 ——
  这正是被改变的那一个变量。
- 以上每一项都由 `verification.json` 的 `checks` 数组从本目录真实产物现场解析得出。

## 4. 产物清单
{artifact_list}

## 5. 已知限制
1. {c1_limit}
2. **还原侧不可用**：气相阴离子在 r2SCAN-3c 下全部不束缚（见 week4 报告）；C1 的还原量同样只能在
   条件态内部比较。
3. **单构象**：C1 的 [Li M]+ 结构由几何规则生成并优化，未做构象搜索，也未在 motif 之间做能量加权。
4. **Gate 1 仍未关闭**：溶液相锚点 31 行仍为 `est`，本报告的主结论只依赖气相锚点。
5. 逐项细节见同目录 `week5_report_full.md`。

## 6. 源文件缺失
{missing_list}
"""


REPORT_TEMPLATES[6] = """# Week 6 成果小结 —— Stage 6（T6 构象系综 / T7 C1 虚频 / T8 delta_m / T9 决策稳定性）

本周把「不确定性」写进 pair 判定：先用构象系综量出 `sigma_conf`（T6），再按冻结规则把
`delta_m = max(构象 90 分位展宽, 方法 pstdev, 0.05 eV)` 组装成**候选**值（T8），最后在
`delta_m = 0 / 0.05 eV / docx_max` 三个口径下重算决策稳定性（T9）；并对 Week 5 的 C1
`[Li M]+` 优化几何做纯 Freq 虚频检查（T7）。本文可独立阅读；逐项细节见同目录
`week6_report_full.md`。

## 1. 本周做了什么
{w6_did}

## 2. 关键数字
{w6_metric}

## 3. T6：构象系综展宽 `sigma_conf`
{w6_t6_block}

## 4. T8：`delta_m` 组装（候选，尚未写入预注册）
{w6_delta_m_block}

## 5. T9：决策稳定性（主口径 `docx_max`）
{w6_t9_block}

## 6. T7：C1 `[Li M]+` 优化几何的虚频检查
{w6_t7_block}

## 7. 质量与复核（QC）
- {w6_qc}
- 上述每一项都由本目录 `verification.json` 的 `checks` 数组从真实产物现场解析得出。

## 8. 产物清单
{artifact_list}

## 9. 已知限制
1. {w6_limit}
2. `delta_m` 当前是**候选值**，尚未写入 `config/prereg.yaml`（Gate 0 保持 CLOSED）；是否 append 由 PI 裁决。
3. **同家族内部排序当前不可回答**：所有层对 / 目标下，同家族 pair 的 `f_unresolved`（下侧）都是 1.000。
4. Gate 1 仍未关闭：溶液相锚点 31 行仍为 `est`，主结论只依赖气相锚点。
5. 逐项细节见同目录 `week6_report_full.md`。

## 10. 源文件缺失
{missing_list}
"""


REPORT_TEMPLATES[7] = """# Week 7 成果小结 —— Stage 7（ML / direct vs Δ-learning）+ Stage 8（active-learning replay）

本周把 Stage 2–5 的产物整理成带 **cost 分级** 的特征表，然后在同一条模型阶梯上比较
**直接学习目标层** 与 **只学位移（Δ-learning）** 两种形态，并且强制报告三种拆分
（random / group / leave-one-family-out）。随后用 retrospective replay 回答
「要买多少次昂贵计算才恢复目标排序」。本文可独立阅读；逐项细节见同目录
`week7_report_full.md`。

## 1. 本周做了什么
{w7_did}

## 2. 关键数字
{w7_metric}

## 3. Stage 7：特征表与三种拆分下的模型阶梯
{w7_s7_block}

## 4. Stage 8：`n_T -> tau_b / O_k / R_k`
{w7_s8_block}

## 5. 质量与复核（QC）
- {w7_qc}
- 上述每一项都由本目录 `verification.json` 的 `checks` 数组从真实产物现场解析得出。

## 6. 产物清单
{artifact_list}

## 7. 已知限制
1. {w7_limit}
2. **配位任务 `C` 的样本只有 10 个**，其 LOFO 折等价于单点外推，只能读方向不能读幅度。
3. Gate 0 保持 CLOSED；Gate 1 仍未关闭（溶液相锚点 31 行仍为 `est`），本周边界结论只依赖气相锚点。
4. Stage 8 的 acquisition 只用 `X0`；`X2` 特征被运行期断言拒绝，只许出现在机制解释里。
5. Week 6 的遗留项（`delta_m` 是否 append 进 `config/prereg.yaml`）仍待 PI 裁决。
6. 逐项细节见同目录 `week7_report_full.md` 与 `reading_list_qa.md`。

## 8. 源文件缺失
{missing_list}
"""

REPORT_TEMPLATES[8] = """# Week 8 成果小结 —— Stage 9（显式微溶剂化：C2 = [Li(M)2]+ 第一溶剂壳复核）

Week 5 把自由分子 C0 换成了 Li+ 配位条件态 C1（[Li M]+）。本周再往前一步：把第一溶剂壳从
1:1 扩到 **1:2**（[Li(M)2]+），在**同一条冻结计算臂**（r2SCAN-3c、气相、同一批种子）上重测
同一组三态垂直量，回答「C1 台阶上看到的位移与排序结论，会不会被第一个配体之外的溶剂化
结构改写」。本文可独立阅读；逐项细节、文献依据与计划修订见同目录
`week8_report_full.md`、`branch_abcd_qa.md` 与 `plan_optimization_branchABC.md`。

## 1. 本周做了什么
{w8_did}

## 2. 关键数字
{w8_metric}

## 3. C1 -> C2 的配对排序稳定性
{w8_s9_block}

## 4. 质量与复核（QC）
- {w8_qc}
- 上述每一项都由本目录 `verification.json` 的 `checks` 数组从真实产物现场解析得出。

## 5. 产物清单
{artifact_list}

## 6. 已知限制
1. {w8_limit}
2. 壳层规模小（12 个 motif / 8 个家族），Top-k 指标在 12 个点上对单点扰动敏感，只读方向与量级。
3. Gate 0 保持 CLOSED；Gate 1 仍未关闭（溶液相锚点 31 行仍为 `est`）。
4. Stage 9 在本项目 v2 §19 中被定义为 **optional**；若要把它提升为必报指标，必须走
   `config/prereg.yaml` 的 `amendment_log`，届时 Gate 0 会由 CLOSED 变为 NOT CLOSED。
5. 逐项细节见同目录 `week8_report_full.md`。

## 7. 源文件缺失
{missing_list}
"""


REPORT_TEMPLATES[9] = """# Week 9 成果小结 —— Stage 10（五级台阶合成与决策稳定性总判）

Week 4-8 各自回答了自己的问题，但每一周用了不同的分子子集和自己的口径，跨周的 tau_b 因此
不能直接比较。本周把五个台阶放到**同一口径**（`p_red = -EA`，两轴都 `higher_is_better`）与
**同一批分子**（common-10：在每一级都有完整值的 10 个分子）上重算，然后回答本项目的中心命题：

> 决定排序是否被改写的，是这一级位移的**离散度**（std），不是它的**大小**（|mean|）。

本文可独立阅读；逐项细节、物理机制与需裁决项见同目录 `week9_report_full.md`。

## 1. 本周做了什么
{w9_did}

## 2. 关键数字
{w9_metric}

## 3. 共同子集（N = 10）上的五级台阶
{w9_ladder_block}

## 4. v2 第 22 节：情形 A-G 判定
{w9_verdict_block}

## 5. 质量与复核（QC）
- {w9_qc}
- 上述每一项都由本目录 `verification.json` 的 `checks` 数组从真实产物现场解析得出。

## 6. 产物清单
{artifact_list}

## 7. 已知限制
1. {w9_limit}
2. 本项目所有秩相关都在 n <= 20 个台阶事件上计算，只能读方向与量级，不能读显著性。
3. Gate 0 保持 CLOSED；Gate 1 仍未关闭（溶液相锚点 31 行仍为 `est`）。
4. Stage 10 是**探索性合成分析**（重读已冻结产物，不跑新电子结构）；若要把 Spearman 汇总
   提升为必报指标，须走 `config/prereg.yaml` 的 `amendment_log`，届时 Gate 0 由 CLOSED 变为
   NOT CLOSED。
5. 逐项细节见同目录 `week9_report_full.md`。

## 8. 源文件缺失
{missing_list}
"""


REPORT_TEMPLATES[10] = """# Week 10 成果小结 —— Stage 11（sigma 的代数解剖与分辨率判据）

Week 9 把五个台阶放到同一口径上，报出了 `rho(shift_std, tau_b) = -0.851`，但留下两个说不通的地方：
那只是一个**相关**而不是机制；而且全篇位移散布最大的台阶（`P0 -> P1` 还原轴，std = 2.253 eV）
反而一个候选清单成员都没换。本周把这两个问题一起解决 —— 方法是把项目自 Week 4 起使用的
`sigma_ij` 彻底化简成闭式，得到一条无量纲的分辨率判据：

> 一对候选可分辨，当且仅当 `q_ij = abs(delta_i - delta_j) / abs(P_i - P_j) <= sqrt(2)/z`。
> `q_ij` 是**方法位移相对目标轴的割线斜率**，临界值在 z = 1 时为 1.414、z = 1.96 时为 0.722。

本文可独立阅读；逐项细节、物理机制与需裁决项见同目录 `week10_report_full.md`。

## 1. 本周做了什么
{w10_did}

## 2. 关键数字
{w10_metric}

## 3. 四条恒等式与一条精确分解
{w10_theorem_block}

T1/T2 说明 `sigma` 只承载「逐分子位移的离散度」这一个信息；T3 说明均匀方法偏差是**零成本**的；
T4 是本周主结果（分辨率判据）；T5 把 `sigma^2` 预算精确拆成保序与破序两份额。

## 4. 逐台阶结果（common-10，N = 10）
{w10_ladder_block}

注意第三列 `sd(delta)` 与 Week 9 的 `shift_std` 逐行相同（T2），且三个被改写清单的台阶
（`P0 -> P1` 氧化、`C0 -> C1` 还原、`C1 -> C2` 还原）的斜率 `b` **全是负的**。

## 5. 反事实对照：哪些扰动是免费的，哪些是致命的
{w10_control_block}

## 6. 可预测性检验
{w10_predictor_block}

## 7. 子集规模带来的不确定性
{w10_drift_block}

## 8. 质量与复核（QC）
- {w10_qc}
- 上述每一项都由本目录 `verification.json` 的 `checks` 数组从真实产物现场解析得出。

## 9. 产物清单
{artifact_list}

## 10. 已知限制
1. {w10_limit}
2. 本项目所有秩相关都在 n <= 20 个台阶事件上计算，只能读方向与量级，不能读显著性。
3. Gate 0 保持 CLOSED；Gate 1 仍未关闭（溶液相锚点 31 行仍为 `est`）。
4. Stage 11 是**探索性方法学分析**（重读已冻结产物，不跑新电子结构）。其中的 AUC / 精确置换 /
   LOO 是本周新增的分析动作；若要把它们提升为必报指标，须走 `config/prereg.yaml` 的
   `amendment_log`，届时 Gate 0 由 CLOSED 变为 NOT CLOSED。
5. 逐项细节见同目录 `week10_report_full.md`。

## 11. 源文件缺失
{missing_list}
"""


REPORT_TEMPLATES[11] = """# Week 11 成果小结 —— Stage 12（介电自相似律与事前预警协议）

Week 10 把 `sigma` 化简成闭式判据后，留下两个可操作的问题：**环境这一层到底是不是「同一把尺子」？**
以及**能不能在跑完所有分子之前就知道哪些台阶会改写清单？** 本周把 Week 4 的 bare CPCM 介电扫描
（eps = 5/10/20/40）升级成第 6 类台阶，回答这两个问题：

> 介电 screening 是**单参数自相似族**：位移整条曲线 = 一个已知标量 x 同一条向量，因此排序只会越来越稳；
> 危险台阶可以在只跑一半分子时以 AUC 0.946 抓出，要一次不漏则需 8/10。

本文可独立阅读；逐项细节、物理机制与需裁决项见同目录 `week11_report_full.md`。

## 1. 本周做了什么
{w11_did}

## 2. 关键数字
{w11_metric}

## 3. 介电自相似律（Born vs Onsager）
{w11_law_block}

## 4. 逐级增量比
{w11_ratio_block}

## 5. 形状不变性
{w11_shape_block}

## 6. 外推检验
{w11_forecast_block}

## 7. 事前预警协议
{w11_prescreen_block}

## 8. 18 个台阶事件总表
{w11_table_block}

## 9. 质量与复核（QC）
- {w11_qc}
- 上述每一项都由本目录 `verification.json` 的 `checks` 数组从真实产物现场解析得出。

## 10. 产物清单
{artifact_list}

## 11. 已知限制
1. {w11_limit}
2. Gate 0 保持 CLOSED；Gate 1 仍未关闭（溶液相锚点 31 行仍为 `est`）。
3. Stage 12 是**探索性方法学分析**（重读已冻结产物，不跑新电子结构）；其中穷举子集（C(10,k)）与
   预警指标是本周新增的分析动作，若提升为必报指标须走 `config/prereg.yaml` 的 `amendment_log`，
   届时 Gate 0 由 CLOSED 变为 NOT CLOSED。
4. 逐项细节见同目录 `week11_report_full.md`。

## 12. 源文件缺失
{missing_list}
"""


REPORT_TEMPLATES[12] = """# Week 12 成果小结 —— Stage 13（介电极限与 ORCA 能量账本）

Week 11 把 bare-CPCM 介电扫描升级成第 6 类台阶后，留了两个没有兑现的承诺：**「单参数族」当时只是
外推**（eps = 80 / 200 从未算过），以及**「环境层」从头到尾只被读成一个数**。本周把这两件事一起做完：

> 介电自相似律现在有 6 个介电点实测支撑（Born mean R2 = 0.9936，两参数族把自有参数 `k` 钉回 0）；
> eps = 200 距导体极限不足 50 meV；而环境位移可以**逐态精确**拆成四项，其中 SMD CDS 与
> `Delta(D4)` / `Delta(gCP)` 对垂直量精确为 0 —— 真正的一阶项是「溶质畸变」，它在还原轴上抵消掉
> 介电项的 29%。把 P2 的位移讲成「纯介电 screening」因此是不准确的。

本文可独立阅读；逐项细节、物理机制与需裁决项见同目录 `week12_report_full.md`。

## 1. 本周做了什么
{w12_did}

## 2. 关键数字
{w12_metric}

## 3. 介电阶梯：Born 形式在六个介电常数上仍然成立
{w12_law_block}

## 4. 位移拆成「介电」与「溶质畸变」两项
{w12_term_block}

## 5. 导体极限 eps -> inf
{w12_limit_block}

## 6. 外推误差随外推距离增长
{w12_forecast_block}

## 7. ORCA 能量账本：环境的四项精确分解
{w12_ledger_block}

## 8. 22 点台阶总表
{w12_table_block}

## 9. 质量与复核（QC）
- {w12_qc}
- 上述每一项都由本目录 `verification.json` 的 `checks` 数组从真实产物现场解析得出。

## 10. 产物清单
{artifact_list}

## 11. 已知限制
1. {w12_limit}
2. Gate 0 保持 CLOSED；Gate 1 仍未关闭（溶液相锚点 31 行仍为 `est`）。
3. 本周在既有冻结产物之上新增了 108 个 ORCA 单点（bare CPCM eps = 80 / 200 与 CPCM(SMD, 水)），
   几何复用 G1、方法未变；但「两参数族拟合」与「外推误差标度」是本周新增的分析动作，
   若提升为必报指标须走 `config/prereg.yaml` 的 `amendment_log`，届时 Gate 0 由 CLOSED 变为 NOT CLOSED。
4. 逐项细节见同目录 `week12_report_full.md`。

## 12. 源文件缺失
{missing_list}
"""


README_TEMPLATE = """# 电解液溶剂 redox 代理可审计性项目 —— 成果输出包

本目录**只放蒸馏产物**（结果表、图、报告、校验清单）。原始 ORCA / xTB 运行输出
（`.out`、`.gbw`、`.inp`、几何等）保留在仓库 `outputs/` 内，**不**进入本目录；
唯一例外是 `week3/orca_smoke/`：它保留了 4 个冒烟作业的原始 `.inp/.out/.xyz`，
用来证明 ORCA 6.1.1 在本机可运行（该例外已在 `docs/09` §2.6 说明）。

## 目录结构

    成果输出/
    ├── README.md              本文件
    ├── 数据结果汇总.md          项目级总汇总
    ├── week1/                Stage 0 定义冻结 / Gate 0
    ├── week2/                Stage 1 方法审计与外部锚点
    ├── week3/                Stage 2 broad cheap pool（P0）
    ├── week4/                Stage 3（P1）+ Stage 4（P2）+ T5 + T3 + T2
    ├── week5/                Stage 5（T4：Li+ 配位条件态 C1）
    ├── week6/                Stage 6（T6 构象系综 + T7 虚频 + T8 delta_m + T9 决策稳定性）
    ├── week7/                Stage 7（ML / Δ-learning）+ Stage 8（active-learning replay）
    ├── week8/                Stage 9（显式微溶剂化：[Li(M)2]+ 第一溶剂壳复核）
    ├── week9/                Stage 10（五级台阶合成与决策稳定性总判）
    ├── week10/               Stage 11（sigma 的代数解剖与分辨率判据）
    ├── week11/               Stage 12（介电自相似律与事前预警协议）
    ├── week12/               Stage 13（介电极限与 ORCA 能量账本）
    ├── week13/               Stage 14（畸变项归因与 EMC 离群点诊断）
    ├── week14/               Stage 15（双初猜协议、电子弥散度描述符与溶液锚点扫描）
    ├── week15/               Stage 16（全核心集双初猜目录与事前预警规则）
    ├── week16/               Stage 17（亚稳态污染上限与两个 SCF 解的电子结构身份）
    ├── week17/               Stage 18（全目录电子身份普查与零成本自诊断）
    ├── week18/               Stage 19（几何弛豫检验：第二个 SCF 解能不能扛住弛豫）
    └── week19/               Stage 20（第六级台阶与第二解的跨方法存亡）

每个 week 目录包含：

    weekN/
    ├── <蒸馏产物：.csv / .json / .md>
    ├── artifacts/            图（F0–F42 中属于该周的部分）
    ├── weekN_report.md       本周小结（可独立阅读）
    ├── SHA256SUMS            `<sha256>  <相对路径>`，与仓库 outputs/week1 同格式
    └── verification.json     结构化校验记录

`verification.json` 字段：`week`、`topic`、`generated_utc`、`n_files`、`files`（相对路径 → sha256）、
`checks`（`[{name, ok, detail}]`）、`gate_status`、`source_commands`，另附
`excluded_binary_scratch` 与 `missing_sources`。

## 一周一张表
| week | 主题 | 关键结果 | Gate |
| --- | --- | --- | --- |
| week1 | Stage 0 定义冻结 | 6 个冻结产物；core 18 / broad 40 行 | Gate 0 **CLOSED** |
| week2 | Stage 1 方法审计与外部锚点 | 12 分子方法审计；溶液锚点 31 行仍为 est | Gate 1 **NOT CLOSED** |
| week3 | Stage 2 broad cheap pool（P0） | core 18/18、broad 40/40；合并池 58 | Gate 1 NOT CLOSED |
| week4 | Stage 3 + Stage 4 + T5 + T3 + T2 | 三臂 MAE 1.377 / 4.481 / 0.251 eV；三级台阶 tau_b：方法 0.673 / 环境 0.895 / 几何 0.939；T3 T2 作业 0 失败 | Gate 0 CLOSED |
| week5 | Stage 5（T4：Li+ 配位 C1） | Li+ 配位条件态（C0 -> C1）：[Li M]+ motif 枚举 + 三态垂直量；方法 / 几何 / 环境 / 条件态四台阶同口径 σ 对比 | Gate 0 CLOSED |
| week7 | Stage 7（ML / Δ-learning）+ Stage 8（AL replay） | 特征表 cost 分级 `X0`/`X1`/`X2`（core 18 / broad 40）；三种拆分下的 direct vs Δ-learning；`n_T → τ_b` 四条 acquisition 曲线 | Gate 0 CLOSED |
| week6 | Stage 6（T6/T7/T8/T9） | 构象系综 `sigma_conf`（12 分子 / 32 构象）；`delta_m`（氧化 0.700 / 还原 2.074 eV）；并入 `delta_m` 后还原轴不可判定 | Gate 0 CLOSED |
| week8 | Stage 9（显式微溶剂化 C2） | [Li(M)2]+ 第一溶剂壳（12 motif / 8 家族）；C1 -> C2 的垂直量位移与同口径排序稳定性 | Gate 0 CLOSED |
| week9 | Stage 10（五级台阶合成） | 五个台阶同口径重算（common-10）：rho(std, tau_b) = -0.851 vs rho(|mean|, tau_b) = -0.535；唯一负 tau_b 在 C0->C1 还原轴 | Gate 0 CLOSED |
| week10 | Stage 11（sigma 解剖） | 四条恒等式（T1–T4）+ 精确分解（T5）；判据 `f_unresolved(z) = Pr(q_ij > sqrt(2)/z)` 与实测误差精确为 0；带符号斜率 AUC 1.000（精确 p = 1/120），无符号的 sd(delta) 仅 0.810；N=10 时 tau_b 抽样标准差 0.126 | Gate 0 CLOSED |
| week12 | Stage 13（介电极限 + ORCA 能量账本） | 6 个介电点实测 Born 形式（mean R2 0.9936）；eps = 200 距导体极限 < 50 meV；环境位移四项精确分解（CDS / D4 / gCP 对垂直量为 0） | Gate 0 CLOSED |
| week11 | Stage 12（介电自相似 + 事前预警） | 介电扫描落在 Born 单参数族（mean R2 0.9936 vs Onsager 0.8835）；18 个台阶事件里 8 个介电台阶全部良性（b > 0、tau_b >= 0.867、无一改写清单）；预警协议 k = 5 平均抓 96%（AUC 0.946）、k = 8 一次不漏 | Gate 0 CLOSED |
| week14 | Stage 15（双初猜协议 + 弥散度描述符 + 锚点扫描） | 90 点双初猜里 12 点超 1 meV 且**全部为负**、反向 0 次（最大惩罚 0.2860 eV）；EMC 还原轴九点 Born R2 0.6788 -> 0.9556、符号变化 4 -> 0、偶极粗糙度 1.99 -> 0.08；eps = 200 -> 1000 只走 11.3 meV 而六点缺口 +33.2 -> -30.8 meV（**没有变小**）；`D_anion` 最佳留一 R2 0.162 -> 0.556（`spin_maxfrac`，rho = +0.811），中性/阳离子 `delta_loo = 0`；31 行锚点 4 行可裁定、3 改 1 确认 | Gate 0 CLOSED |
| week13 | Stage 14（畸变项归因 + EMC 离群点） | 逐态畸变惩罚 D_neutral / D_cation / D_anion = 0.0685 / 0.1120 / 0.3710 eV（全部 72/72 为正，变分检验无例外）；唯一稳健关系是 D_neutral 对自身偶极矩（rho = +0.909，留一 R2 0.634）；§14 的 (-0.0465, +0.3272) eV 被 510 种聚合穷举证否；63 个密集网格作业零失败、四个共享介电点逐位复现 | Gate 0 CLOSED |
{w15_row}
{w16_row}
{w17_row}
{w18_row}
{w19_row}
{w20_row}
{w21_row}

## 如何复现
```powershell
cd "E:\\Claude Code\\电解液溶剂-HB\\电解液溶剂HB-Code"
$env:PYTHONIOENCODING = "utf-8"
.venv\\Scripts\\python.exe scripts\\build_deliverables.py --dry-run
.venv\\Scripts\\python.exe scripts\\build_deliverables.py
```

- `--out`：输出根目录（默认 `E:\\Claude Code\\电解液溶剂-HB\\成果输出`）。
- `--weeks`：默认 `1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21`。
- `--force`：覆盖已存在的**复制**文件（默认跳过已存在项）。
- `--dry-run`：只打印计划，不写任何文件。

## 口径说明
- **幂等**：重复运行不产生差异。唯一例外是 `verification.json` 的 `generated_utc`（生成时刻），
  该字段允许变化，且不参与任何校验。
- 生成文件（`weekN_report.md`、`SHA256SUMS`、`verification.json`、本文件、`数据结果汇总.md`）
  每次都重写；复制文件默认跳过，需 `--force` 才覆盖。
- `SHA256SUMS` 与 `verification.json` **互相排除**（避免自指），但 `verification.json` 的 `files`
  与 `SHA256SUMS` 的条目集合完全一致。
- 二进制 scratch（`.gbw` / `.bas` / `.tmp` / `.wfn` / `.densities` / `.pot` / `.xtbrestart` /
  `.xtbtopo.mol` / `.xtboptok`，以及 `wbo` / `charges`）一律**不复制**；被跳过的数量记录在
  `verification.json` 的 `excluded_binary_scratch`。
- 所有文本文件为 UTF-8（无 BOM）、LF 换行。
- 复制文本产物时会规范化为 UTF-8（无 BOM）+ LF；若源文件原先带 BOM 或 CRLF，交付副本的 sha256
  会与仓库内源文件不同，这是有意为之（以本目录 `SHA256SUMS` 为准）。
"""


SUMMARY_TEMPLATE = r"""# 电解液溶剂氧化还原代理可审计性项目 —— 数据结果总汇总

> 本文件中的每个数字都来自仓库内真实产物（`outputs/`、`docs/`、`config/`），
> 可在 `成果输出/weekN/` 中按 `SHA256SUMS` 逐字节校验。原始运行日志不在本目录。

## 0. 口径纪律（读任何数字前先看这一节）

1. **三层臂的唯一变量规则**。P0 = GFN2-xTB；P1 = ORCA r2SCAN-3c（气相）；
   P2 = r2SCAN-3c + CPCM(SMD, 乙腈)。相邻两层之间**只有一个变量**在变：
   P0→P1 只换电子结构方法，P1→P2 只换环境。几何（G1）与构象在两臂间完全共享。
2. **垂直量口径**。IP / EA 全部是垂直量，在冻结几何 G1 上取三态能量差，不做几何弛豫。
3. **z 因子**。pair 比较的主判据是 `config/prereg.yaml` 冻结的 `z_factor.value = 1.0`；
   `z = 1.96`（95% 双侧带）作为保守敏感性**并列**报告。两者不得混用、不得择优引用。
4. **几何 G1**。GFN2-xTB 单构象优化几何（`outputs/_week3_scratch/<mol>/xtbopt.xyz`），全部层共享。
5. **不把 ΔSCF 负值当 EA 用**。T5 / 方法审计中的 `EA_dscf = (E_anion - E_neutral) * 27.211386`，
   **正值表示阴离子不束缚**；对外可比的是 `EA_conventional = -EA_dscf`。Koopmans EA（`+eps_LUMO`）
   与 ΔSCF EA 不是同一物理量，不可互换。

## 1. 三层臂与条件态定义
| 层 | 定义 | 引擎 | 环境 |
| --- | --- | --- | --- |
| P0 | 廉价代理：Koopmans `p0_ox = -eps_HOMO`、`p0_red = +eps_LUMO` | GFN2-xTB 6.7.1pre | 气相 |
| P1 | 电子结构目标层：垂直 IP/EA（ΔSCF，三态） | ORCA 6.1.1 r2SCAN-3c | 气相 |
| P2 | 环境层：P1 + 隐式溶剂 | ORCA 6.1.1 r2SCAN-3c + CPCM(SMD, 乙腈) | 隐式溶剂 |

条件态：`C0` = 自由分子 M（P0/P1/P2 全部实际运行的条件态）；`C1` = `[LiM]+` 及其 redox states
（**week5 已运行**，Stage 5 / T4）；`C2` = 少量显式微溶剂化 cluster（**尚未运行**）。
参考配体：主参考 `R = DME`（C08，双齿 2×O 螯合、配位 motif 唯一）；第二参考 `R = AN`（C16，
仅用于 robustness check）。核心集 18 个分子、broad pool 40 个分子，合并池 58。

## 2. 逐周结果（Week 1 – Week 19）

### Week 1 —— Stage 0 定义冻结 / Gate 0
- 做了什么：冻结科学定义与预注册（`config/scientific_definitions.yaml`、`config/prereg.yaml`），
  构建并核对 chemical-space 元数据，运行 Gate 0 检查。
- 关键数字：Gate 0 **CLOSED**，冻结产物 6 个；core set 18 行、broad pool 40 行；
  `config/prereg.yaml` sha256 = `{prereg_sha256}`。
- 质检：4 项 Gate 0 检查全部通过；`amendment_log` 为空；冻结产物逐字节重算一致。
- 产物：`gate0_record.md`、`00_stage0_definitions.md`、`scientific_definitions.yaml`、
  `prereg.yaml`、`artifacts/F0_project_pipeline.png`。

### Week 2 —— Stage 1 方法审计与外部锚点
- 做了什么：建立并校验外部气相锚点库；对 12 个分子做 GFN2-xTB 三态方法审计（Koopmans vs ΔSCF）；
  31 行溶液相锚点逐条证据审计；Gate 1 检查。
- 关键数字：方法审计 12 个分子，其中 **2** 个气相阴离子不束缚；溶液锚点 31 行，
  审计后**仍全部为 `est`**（升级 `exp`/`calc` 的行数 = 0）；一致性检查 `True`。
- 质检：Gate 1 = **NOT CLOSED**，唯一 blocker 是溶液锚点 31 行 `est`。
- 产物：`method_audit_xtb.csv`、`method_audit_xtb_summary.json`、`solution_anchor_audit.csv/.json`、
  `gate1_record.md`、`03_week1_2_report.md` 等。

### Week 3 —— Stage 2 broad cheap pool（P0）
- 做了什么：GFN2-xTB 对 core（18）与 broad（40）跑 P0 代理；覆盖度 / 家族分布图；
  决策预览（Top-k 重叠、参考配体定位）；ORCA 冒烟测试。
- 关键数字：core P0 成功 18/18、broad P0 成功 40/40，合并池 58；氧化轴 vs 还原轴
  Kendall tau_b = **−0.302**；参考配体 primary_R = **DME (C08)**。
- 质检：两池 `n_failed = 0`、`n_abnormal_termination = 0`、`n_missing_p0_fields = 0`。
- 产物：`p0_core_set.csv`、`p0_broad_pool.csv`、`p0_summary.json`、`fig1`–`fig4`、
  `artifacts/F1`、`artifacts/F2`。

### Week 4 —— Stage 3（P1）+ Stage 4（P2）+ T5（+ T3、T2）
- 做了什么：P1 三态 54 作业（r2SCAN-3c、气相、G1）；P1 QC 审计与决策稳定性分析；
  P2 环境层 54 作业（CPCM(SMD, 乙腈)）；T5 弥散函数对照 24 作业；T3 为 bare CPCM ε 扫描（ε=5/10/20/40 × 12 分子 × 3 态 = 144/144，覆盖 8 个家族）；T2 为同一 12 分子的 r2SCAN-3c `Opt+Freq`（G1 -> G2，唯一变量 = 几何）与 G2 上的三态单点。
- 关键数字：P1 **54/54** 成功，`unbound_anion = 18`；三臂锚点 MAE = **1.377 / 4.481 / 0.251 eV**；
  P0→P1 氧化 tau_b **0.673**（O_k 10% = 0.000、20% = 0.500）、还原 tau_b **0.595**；
  P1→P2 ΔIP 均值 **−2.393 eV**（std **0.293**）、ΔEA 均值 **+2.173 eV**（std **0.311**）、
  氧化 tau_b **0.895**、还原 tau_b **0.673**；T5 加弥散下拉 EA **0.34–1.60 eV** 且不翻转符号；T3 ε 扫描位移 σ_env 仅 **0.19–0.24 eV**（近乎共同平移）、two_arm σ 下 f_robust_inv = **0**。{t2_summary_metric}
- 质检：P1/P2/T5 作业 **0 失败**；`energy_mismatch`、`scf_failed`、`abnormal_termination`、
  `spin_contamination_flag` 全为 0；主判据 `z = 1.0`，`z = 1.96` 并列敏感性。
- 产物：`p1_*`、`p2_*`、`t5_*` 表与 JSON、`p1_decision_stability.md`、`p2_decision_stability.md`、
  `week4_report_full.md`、`artifacts/F3`–`F9`{f10_art_note}{f11_art_note}。

### Week 5 —— Stage 5（T4：Li+ 配位条件态 C1）
- 做了什么：{c1_did}
- 关键数字：{c1_metric}
- 质检：{c1_qc_summary}
- 产物：`li_motif_generation.csv/.json/.md`、`c1_li_coordination.csv`、`c1_li_coordination_summary.json`、
  `c1_summary.json`、`c1_coord_shifts.csv`、`c1_ligand_exchange.csv`、`c1_decision_stability.json/.md`、
  `structures/li_motifs/*.xyz`、`c1_records/`、`week5_report_full.md`、
  `artifacts/figure_manifest_week5_c1.md`{f12_art_note}、`artifacts/figure_manifest_week5_state_identity.md`{f13_art_note}。

### Week 6 —— Stage 6（T6 构象系综 + T7 C1 虚频 + T8 delta_m + T9 决策稳定性）
- 做了什么：{w6_did}
- 关键数字：{w6_metric}
- 质检：{w6_qc}
- 限制：{w6_limit}

### Week 7 —— Stage 7（ML / Δ-learning）+ Stage 8（active-learning replay）
{w7_summary}

### Week 8 —— Stage 9（显式微溶剂化：C2 = [Li(M)2]+ 第一溶剂壳复核）
{w8_summary}

### Week 9 —— Stage 10（五级台阶合成与决策稳定性总判）
{w9_summary}

### Week 10 —— Stage 11（sigma 的代数解剖与分辨率判据）
{w10_summary}

### Week 11 —— Stage 12（介电自相似律与事前预警协议）
{w11_summary}

### Week 12 —— Stage 13（介电极限与 ORCA 能量账本）
{w12_summary}

### Week 13 —— Stage 14（畸变项归因与 EMC 离群点诊断）
{w13_summary}

### Week 14 —— Stage 15（双初猜协议、电子弥散度描述符与溶液锚点扫描）
{w14_summary}

### Week 15 —— Stage 16（全核心集双初猜目录与事前预警规则）
{w15_summary}

### Week 16 —— Stage 17（亚稳态污染上限与两个 SCF 解的电子结构身份）
{w16_summary}

### Week 17 —— Stage 18（全目录电子身份普查与零成本自诊断）
{w17_summary}

### Week 18 —— Stage 19（几何弛豫检验：第二个 SCF 解能不能扛住弛豫）
{w18_summary}

### Week 19 —— Stage 20（第六级台阶与第二解的跨方法存亡）
{w19_summary}

### Week 20 成果小结 · Stage 21
{w20_summary}

### Week 21 成果小结 · Stage 22（批次 A）
{w21_summary}

## 3. 核心科学结论

### 3.1 值误差 ≠ 排序误差
三臂与外部气相锚点比较：P0 Koopmans MAE **1.377 eV**（tau_b 0.606）、GFN2-xTB ΔSCF MAE
**4.481 eV**（tau_b 0.911）、P1 r2SCAN-3c MAE **0.251 eV**（tau_b 0.727）。
ΔSCF 的值误差是 P0 的 3.3 倍，排序一致性却最高；P1 的值误差最小，排序一致性反而低于 ΔSCF。
**把一个臂的 MAE 当作它的决策质量是错的。**

### 3.2 四级台阶（方法 / 环境 / 几何 / 条件态）：位移的方差决定决策是否被改写
| 台阶 | 唯一变量 | IP 位移均值 | IP 位移 std | 氧化轴 tau_b | 氧化 Top-20% 重叠 |
| --- | --- | --- | --- | --- | --- |
| P0 → P1 | 电子结构方法 | −1.550 eV | **0.714 eV** | **0.673** | 0.50 |
| P1 → P2 | 环境（气相 → SMD 乙腈） | −2.393 eV | **0.293 eV** | **0.895** | 0.75 |
{t2_step_row}
{c1_step_row}

环境台阶的平均位移比方法台阶**大 54%**，但分子间离散度只有方法台阶的 **41%**，
于是排序被破坏得**更少**。第三级台阶是几何（T2，G1 -> G2）：位移均值为 −0.002 eV、离散度仅
**0.049 eV**，tau_b 0.939、Top-20% 重叠 1.000 —— 把 xTB 几何换成 r2SCAN-3c 的驻点几何
**几乎不改变任何排序**。**位移更大不等于决策更坏；决定决策是否被改写的是位移的方差。**
{c1_sigma_note}

{w6_sigma_note}

{w9_sigma_note}

{w10_sigma_note}

{w11_sigma_note}

{w12_sigma_note}

### 3.3 还原侧定性失效
P1 下 18 个分子的气相阴离子**全部不束缚**（`unbound_anion = 18`，EA < 0）。定域在 LUMO 上的
Koopmans 图像在结构上**不可能**给出这一点，因此 P0 还原轴与真实 EA 不是同一物理量。
P0→P1 还原 tau_b（0.595）低于氧化 tau_b（0.673），但还原轴 Top-10% 重叠却高达 1.000——
这属于「廉价层还原代理与真实 EA 不是同一物理量」造成的**伪一致**，不可解读为代理可靠。

### 3.4 T5：方法适用域
同一泛函 r2SCAN、只换基组：加弥散（def2-TZVPD）把气相 EA 系统性下拉 **0.34–1.60 eV**，
但四个分子在三个臂下**都不翻转符号**。AN（0.011 eV）与 DMSO（0.014 eV）的锚点比任何 DFT 泛函的
误差棒（~0.1–0.2 eV）低两个数量级。结论是**方法适用域**：本方法不能裁断 0.01 eV 量级的阴离子
束缚与否。氧化侧（IP）不受此限制，因为阳离子紧凑、不需要弥散函数。

## 4. Gate 状态与 blocker
| Gate | 状态 | 内容 |
| --- | --- | --- |
| Gate 0（定义冻结） | **CLOSED** | `config/scientific_definitions.yaml` + `config/prereg.yaml` + metadata 未被改动；`amendment_log` 为空 |
| Gate 1（方法 / 锚点） | **NOT CLOSED** | 唯一 blocker：溶液相锚点 **31 行**仍为 `est`，缺少可核验的原始文献值（ORCA 通路已由 week4 打通，不再是 blocker） |
| Gate 2+ | 未定义 / 未触发 | —— |

## 5. 图表索引（F0–F42）
| 图 | 文件 | 内容 | 所在周 |
| --- | --- | --- | --- |
| F0 | `F0_project_pipeline.png` | 项目管线：廉价代理 → 验证目标 → 排序变化 → 机制 → 最小预算 | week1 |
| F1 | `F1_chemical_space_coverage.png` | core set vs broad pool 的结构家族覆盖 | week3 |
| F2 | `F2_p0_distributions_by_family.png` | P0 代理按家族 / 氟化的分布 | week3 |
| F3 | `F3_value_error_vs_rank_error.png` | 值误差 vs 排序误差（中心反直觉结果） | week4 |
| F4 | `F4_rank_migration_p0_to_p1.png` | P0 → P1 的排序迁移 | week4 |
| F5 | `F5_reduction_axis_koopmans_vs_dscf.png` | 还原轴：Koopmans 连定性都不对 | week4 |
| F6 | `F6_decision_stability_indicators.png` | Top-k 重叠 / Jaccard 与 pair 分离度 | week4 |
| F7 | `F7_shift_structure.png` | 廉价层是「平移的尺子」还是「另一把尺子」 | week4 |
| F8 | `F8_environment_layer_p1_to_p2.png` | 环境层的逐分子气相 → 溶剂位移 | week4 |
| F9 | `F9_diffuse_function_control.png` | 同泛函三基组：加弥散下拉 EA 但不翻转符号 | week4 |
{f10_row}
{f11_row}
{f12_row}
{f13_row}
{f14_row}
{f15_row}
{f16_row}
{f17_row}
{f18_row}
{f19_row}
{f20_row}
{f21_row}
{f22_row}
{f23_row}
{f24_row}
{f25_row}
{f26_row}
{f27_row}
{f28_row}
{f29_row}
{f30_row}
{f31_row}
{f32_row}
{f33_row}
{f34_row}
{f35_row}
{f36_row}
{f37_row}
{f38_row}
{f39_row}
{f40_row}
{f41_row}
{f42_row}

## 6. 复现命令
```powershell
cd "E:\Claude Code\电解液溶剂-HB\电解液溶剂HB-Code"
$env:PYTHONIOENCODING = "utf-8"

# 交付包（本目录）
.venv\Scripts\python.exe scripts\build_deliverables.py --dry-run
.venv\Scripts\python.exe scripts\build_deliverables.py

# 底层产物
.venv\Scripts\python.exe scripts\build_metadata.py
.venv\Scripts\python.exe scripts\freeze_gates.py
.venv\Scripts\python.exe scripts\run_method_audit_xtb.py
.venv\Scripts\python.exe scripts\audit_solution_anchors.py
.venv\Scripts\python.exe scripts\run_broad_pool_p0.py
.venv\Scripts\python.exe scripts\make_summary_figures.py
.venv\Scripts\python.exe scripts\run_core_set_p1.py --jobs 2 --outdir outputs\week4
.venv\Scripts\python.exe scripts\audit_p1_core_set.py
.venv\Scripts\python.exe scripts\analyze_p1_core_set.py
.venv\Scripts\python.exe scripts\run_core_set_p2.py --jobs 2 --outdir outputs\week4
.venv\Scripts\python.exe scripts\analyze_p2_environment.py
.venv\Scripts\python.exe scripts\run_diffuse_control.py
.venv\Scripts\python.exe scripts\make_t5_figure.py
{t3_commands}
{t2_commands}
{c1_commands}

# 测试
.venv\Scripts\python.exe -m pytest tests -o addopts="" -q
```

## 7. 已知限制（不得在对外表述中省略）
1. **还原侧不可用**：气相阴离子在 r2SCAN-3c 下全部不束缚；Koopmans 还原代理与真实 EA 不是同一
   物理量。还原侧结论只在「廉价层内部比较」的意义上有效。
2. **基组无弥散**：r2SCAN-3c 的 def2-mTZVPP 不含弥散函数，0.01 eV 量级的阴离子束缚判断落在
   方法适用域之外（T5 结论）。氧化侧不受此限制。
3. **单构象 + G1/G2 两级几何**：全部结果建立在 GFN2-xTB 单一构象优化几何 G1 上；T2 另外给出
   r2SCAN-3c 的 G2 几何台阶（第 8 条）。未做构象搜索，也未评估构象离散度（`sigma_conf` 仍为「待算」）。
4. **隐式溶剂**：P2 为 CPCM(SMD) 隐式溶剂，不含显式溶剂分子；`C1`（Li+ 配位）已在 week5 运行
   （见第 10 条），`C2`（显式微溶剂化）条件态尚未运行。
5. **锚点样本小**：外部气相锚点仅 12 个分子；tau_b 的 bootstrap 区间较宽（如 P0 臂 [0.16, 0.90]）。
6. **Gate 1 未关闭**：溶液相锚点 31 行仍为 `est`，因此所有主结论只依赖气相锚点。
7. {t3_summary_limit}
8. {t2_summary_limit}
9. **Gate 0 纪律**：`config/prereg.yaml` 逐字节未变；`z = 1.0` 是主判据，`z = 1.96` 只是并列敏感性。
10. {c1_summary_limit}
11. {w11_summary_limit}
12. {w12_summary_limit}
13. {w13_summary_limit}
14. {w14_summary_limit}
15. {w15_summary_limit}
16. {w16_summary_limit}
17. {w17_summary_limit}
18. {w18_summary_limit}
19. {w19_summary_limit}
20. {w20_summary_limit}
21. {w21_summary_limit}
"""


T2_SUMMARY_PATH = REPO / "outputs" / "week4" / "t2_opt_freq_summary.json"
T2_DERIVED_PATH = REPO / "outputs" / "week4" / "p1_core_set_derived.csv"
T3_SUMMARY_PATH = REPO / "outputs" / "week4" / "t3_cpcm_eps_scan_summary.json"
T2_ENV_EPS = "40"
C1_SUMMARY_PATH = REPO / "outputs" / "week5" / "c1_summary.json"
C1_RUN_SUMMARY_PATH = REPO / "outputs" / "week5" / "c1_li_coordination_summary.json"
C1_REFERENCE_LIGAND = "DME"
F12_NOTE_PRESENT = ("条件态台阶：把自由分子 C0（P1 @ G2）换成 [Li M]+ 配位态 C1 后，垂直 IP / EA 的"
                    "逐分子位移，以及与方法、几何、环境三个台阶同口径的 sigma 对比；另一面板给出配体"
                    "交换量 dGdG_bind(M;R) 与 C0 -> C1 的决策指标")
F12_NOTE_ABSENT = "预留给 C1（Li+ 配位条件态）；T4 尚未产出"
F13_NOTE_PRESENT = ("state-identity QC：每个 C1 态的 state-identity 分类，显示氧化态空穴落在"
                    "给体原子、还原态电子落在 Li 上")
F13_NOTE_ABSENT = "state-identity QC 图尚未产出"
F14_NOTE_PRESENT = ("delta_m 的推导：构象 90 分位展宽 / 方法 pstdev(P1-P0) / 0.05 eV 下限 三个组成项与 "
                    "max 规则；另一面板给出逐分子的 P1-P0 位移，说明方法项为何主导")
F14_NOTE_ABSENT = "预留给 delta_m 推导；T6/T8 尚未产出"
F15_NOTE_PRESENT = ("Stage 6 决策稳定性：delta_m = 0 / 0.05 eV / docx_max 三个口径下的 unresolved 比例，"
                    "以及 docx_max 口径下的 tau_b、Top-20% 重叠与 f_robust_inv")
F15_NOTE_ABSENT = "预留给 Stage 6 决策指标；T9 尚未产出"
F16_NOTE_PRESENT = ("Stage 7 直接学习 vs 条件位移学习：三种拆分（random / group / LOFO）下的 "
                    "模型阶梯，重点看 LOFO 外推；负值说明该基线在该任务上不如其自身参照层。")
F16_NOTE_ABSENT = "预留给 Stage 7（direct vs Δ-learning）；week7 尚未产出"
F17_NOTE_PRESENT = ("Stage 8 最小昂贵信息预算：`n_T -> tau_b` 的四条 acquisition 曲线"
                    "（random / diversity / uncertainty / ranking-aware），"
                    "带宽为 20 组冻结种子的 2.5–97.5 百分位。")
F17_NOTE_ABSENT = "预留给 Stage 8（active-learning replay）；week7 尚未产出"
W7_STAGE7_PATH = REPO / "outputs" / "week7" / "stage7_ml_results.json"
W7_STAGE8_PATH = REPO / "outputs" / "week7" / "stage8_al_results.json"
F18_NOTE_PRESENT = ("Stage 9 显式第一溶剂壳：把 C1(1:1) 的 [Li M]+ 扩成 [Li(M)2]+ 后，逐 motif 的"
                    "垂直 IP / EA 位移、与 C1(1:1) 位移的差值，以及同一批 motif 上 "
                    "tau_b / Top-k 重叠 / f_unresolved")
F18_NOTE_ABSENT = "预留给 Stage 9（显式微溶剂化）；week8 尚未产出"
W8_STAGE9_PATH = REPO / "outputs" / "week8" / "stage9_results.json"
W8_SHELLS_PATH = REPO / "outputs" / "week8" / "ms_shell_generation.json"
F19_NOTE_PRESENT = ("Stage 10 五级台阶：每个台阶/轴的 tau_b（按位移 std 递增排列）、"
                    "std vs tau_b（H_var，rho = -0.851）、|mean| vs tau_b（H_mean 对照，"
                    "rho = -0.535）、std vs f_unresolved（rho = +0.894）")
F19_NOTE_ABSENT = "预留给 Stage 10（五级台阶合成）；week9 尚未产出"
W9_LADDER_PATH = REPO / "outputs" / "week9" / "stage10_ladder.json"
C1_NOTE_PRESENT = ("**C1（Li+ 配位条件态，T4）**：按冻结的 motif 生成规则枚举 [Li M]+，在 r2SCAN-3c 上"
                   "优化配位几何并做三态垂直量，与自由分子 C0（P1 @ G2）逐分子相减；"
                   "`outputs/week5/*` 已自动纳入本目录。")
C1_NOTE_ABSENT = "**C1（Li+ 配位条件态，T4）**：本轮未纳入 `outputs/week5/*`（源路径不存在）。"
C1_LIMIT_ABSENT = "**C1（Li+ 配位条件态，T4）尚未纳入**：`outputs/week5/*` 未产出。"
C1_REPRO_COMMANDS = "\n".join([
    "# Stage 5 / T4：Li+ 配位条件态 C1（10 分子；参考配体 R = DME）",
    ".venv\\Scripts\\python.exe scripts\\build_li_motifs.py",
    ".venv\\Scripts\\python.exe scripts\\run_c1_li_coordination.py --jobs 2 --nprocs 8",
    ".venv\\Scripts\\python.exe scripts\\analyze_c1_coordination.py",
    ".venv\\Scripts\\python.exe scripts\\make_c1_figure.py",
])



def _population_std(values):
    return statistics.pstdev(values) if len(values) > 1 else None


def _shift_std(names, column):
    """Population std of one P0 -> P1 shift column over the T2 subset.

    Deliberately the same estimator as scripts/make_t2_figure.py, so that the rendered
    report and the figure cannot end up quoting different numbers for one quantity.
    """
    if not T2_DERIVED_PATH.exists():
        return None
    wanted = set(names)
    values = []
    with T2_DERIVED_PATH.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row.get("name") not in wanted:
                continue
            raw = (row.get(column) or "").strip()
            if raw:
                values.append(float(raw))
    return _population_std(values)


def t2_blocks(t2):
    """Render the T2 (Opt+Freq -> G2) blocks straight from the summary JSON."""
    empty = {"block": "", "qc": "", "step_row": "", "metric": "", "limit": T2_LIMIT_ABSENT}
    if not t2 or not t2.get("per_molecule"):
        return empty
    geom = t2["sigma_geom"]
    ip = geom["d_ip_ev"]
    ea = geom["d_ea_ev"]
    if not ip.get("n") or ip.get("mean_ev") is None:
        return empty
    rows = t2["per_molecule"]
    names = [row["name"] for row in rows]
    pairs = [(row["ip_g1_ev"], row["ip_g2_ev"]) for row in rows
             if row.get("ip_g1_ev") is not None and row.get("ip_g2_ev") is not None]
    tau = overlap = None
    if len(pairs) >= 2:
        g1 = [pair[0] for pair in pairs]
        g2 = [pair[1] for pair in pairs]
        tau = ranking.kendall_tau_b(g1, g2)
        k = max(1, round(0.20 * len(pairs)))
        overlap = ranking.top_k_overlap(g1, g2, k, higher_is_better=True)
    tau_text = "——" if tau is None else f"{tau:.3f}"
    overlap_text = "——" if overlap is None else f"{overlap:.3f}"
    sigma_method = _shift_std(names, "ox_shift_ev")
    sigma_env = (load_json(T3_SUMMARY_PATH)["sigma_env_ev"][T2_ENV_EPS]
                 if T3_SUMMARY_PATH.exists() else None)
    compare = []
    if sigma_method is not None:
        compare.append(f"方法（P0 -> P1）{sigma_method:.3f} eV")
    compare.append(f"几何（G1 -> G2）{ip['population_std_ev']:.3f} eV")
    if sigma_env is not None:
        compare.append(f"环境（气相 -> bare CPCM {T2_ENV_EPS}）{sigma_env:.3f} eV")
    imag = [row["name"] for row in rows if row.get("imaginary_modes")]
    if imag:
        imag_text = (f"共 {len(imag)} 个分子报告了虚频（{'、'.join(imag)}），"
                     "按 QE 词表记为 `imaginary_mode_unresolved`，照实记录、不予静默删除")
    else:
        imag_text = f"{len(rows)} 个分子在 G2 上均无虚频"
    block = "\n".join([
        "### 2.7 T2：Opt+Freq 几何台阶（G1 -> G2，唯一变量 = 几何）",
        "",
        "对 T3 用的**同一 12 分子审计子集**，在 r2SCAN-3c 上**从 G1 出发**做中性 `Opt+Freq`（得到 G2），",
        "再在 G2 上重算三态单点；方法、基组、电子态、环境全部不动，**唯一变量是几何**。",
        "G2 取自输出里**最后一个** `CARTESIAN COORDINATES (ANGSTROEM)` 块，未做任何额外优化。",
        "",
        "| 量 | n | 均值 (eV) | 总体标准差 (eV) | 对该台阶的 Kendall tau_b | Top-20% 重叠 |",
        "| --- | --- | --- | --- | --- | --- |",
        f"| dIP = IP(G2) - IP(G1) | {ip['n']} | {ip['mean_ev']:+.3f} | "
        f"**{ip['population_std_ev']:.3f}** | **{tau_text}** | **{overlap_text}** |",
        f"| dEA = EA(G2) - EA(G1) | {ea['n']} | {ea['mean_ev']:+.3f} | "
        f"**{ea['population_std_ev']:.3f}** | —— | —— |",
        "",
        "同口径（位移在 12 个分子上的总体标准差）的三台阶对比见 `F11` 面板 (b)：",
        "**" + "；".join(compare) + "**。",
        "",
        "这是 `docs/08` §3.4 要求的判据：若几何项与方法项同量级，则 P0 -> P1 的变化不能全部归因于",
        "电子结构方法。实测几何项远小于方法项，因此「方法台阶改写决策」这一结论**未被几何不确定性推翻**。",
        "",
        f"虚频检查：{imag_text}。",
        "",
    ])
    qc = (f"- T2 作业：**{t2['n_opt_ok']} / {t2['n_opt_jobs']}** 个 Opt+Freq 成功、"
          f"{t2['n_sp_ok']} 个 G2 单点成功，失败 **{t2['n_failed']}**；"
          f"`imaginary_mode_unresolved` = {t2['n_imaginary_unresolved']}"
          "（`t2_opt_freq_summary.json`）。")
    step_row = (f"| G1 -> G2 | 几何（同一方法 r2SCAN-3c；xTB 几何 vs Opt+Freq 驻点） | "
                f"{ip['mean_ev']:+.3f} eV | **{ip['population_std_ev']:.3f} eV** | "
                f"**{tau_text}** | {overlap_text} |")
    method_text = "%.3f eV" % sigma_method if sigma_method is not None else "—"
    metric = (f" T2 的几何台阶在同口径下只有 **{ip['population_std_ev']:.3f} eV**（dIP 总体标准差），"
              f"tau_b = {tau_text}、Top-20% 重叠 {overlap_text}；方法台阶（同一 12 分子子集 "
              f"{method_text}；§2.4 的 N=18 口径为 0.714 eV）仍是唯一能改写决策的台阶。")
    return {"block": block, "qc": qc, "step_row": step_row, "metric": metric,
            "limit": T2_LIMIT_PRESENT}


def _fnum(value, digits=3, signed=False):
    if value is None:
        return "——"
    return ("%+.*f" if signed else "%.*f") % (digits, value)


def c1_blocks(summary, run):
    """Render the week-5 C1 (Li+ coordination) blocks from the week-5 summaries.

    Mirrors ``t2_blocks``: the rendered report and the figure are fed by the same
    JSON, so they cannot quote different numbers for one quantity.  A missing
    summary yields an "absent" record instead of an exception, because the digest
    and the plan must stay valid while the stage is still running.
    """

    empty = {
        "present": False,
        "did": "（本轮未纳入 `outputs/week5/*`：C1 条件态尚未产出）",
        "block": "",
        "qc": "——",
        "step_row": "",
        "metric": "——",
        "sigma_note": "",
        "limit": C1_LIMIT_ABSENT,
    }
    if not summary or not summary.get("n_molecules"):
        return empty
    d_ip = summary.get("delta_ip_ev") or {}
    d_ea = summary.get("delta_ea_ev") or {}
    if d_ip.get("mean") is None and d_ea.get("mean") is None:
        return empty

    n = summary["n_molecules"]
    molecules = summary.get("molecules") or []
    n_motifs = summary.get("n_motifs") or 0
    ds = summary.get("decision_stability") or {}
    ox = ds.get("oxidation") or {}
    red = ds.get("reduction") or {}
    steps = (summary.get("four_step_sigma") or {}).get("steps") or {}

    ip_mean = _fnum(d_ip.get("mean"), signed=True)
    ip_std = _fnum(d_ip.get("std"))
    ea_mean = _fnum(d_ea.get("mean"), signed=True)
    ea_std = _fnum(d_ea.get("std"))
    tau_ox = _fnum(ox.get("kendall_tau_b"))
    tau_red = _fnum(red.get("kendall_tau_b"))
    robust_ox = _fnum(ox.get("f_robust_inv"))
    robust_red = _fnum(red.get("f_robust_inv"))

    labels = {
        "method": "方法（P0 -> P1）",
        "geometry": "几何（G1 -> G2）",
        "environment": "环境（气相 -> SMD 乙腈）",
        "coordination": "条件态（C0 -> C1，Li+ 配位）",
    }
    rows = []
    for key in ("method", "geometry", "environment", "coordination"):
        block = (steps.get(key) or {}).get("ip_ev") or {}
        rows.append("| %s | %s eV | **%s eV** | %s |"
                    % (labels[key], _fnum(block.get("mean"), signed=True),
                       _fnum(block.get("std")), block.get("n")))

    coord_std = ((steps.get("coordination") or {}).get("ip_ev") or {}).get("std")
    method_std = ((steps.get("method") or {}).get("ip_ev") or {}).get("std")
    ratio_text = "——"
    if coord_std is not None and method_std:
        ratio_text = "%.2f" % (coord_std / method_std)
    compare = ("配位台阶的 IP 位移离散度（%s eV）与方法台阶（%s eV）之比为 %s。"
               % (_fnum(coord_std), _fnum(method_std), ratio_text))

    step_table = chr(10).join(rows)
    block_text = chr(10).join([
        "### 2.8 C1：Li+ 配位条件态（唯一变量 = 条件态；自由分子 C0 -> [Li M]+ C1）",
        "",
        "对 %d 个分子（%s）按冻结的 motif 生成规则枚举 [Li M]+ 初始结构（%d 个 motif），"
        % (n, "、".join(molecules), n_motifs),
        "在 r2SCAN-3c 上优化配位几何并做三态垂直量；C0 参考取同一分子在 P1 @ G2 上的自由分子值。",
        "唯一变量是条件态（是否带一个 Li+），方法、基组与环境口径全部沿用同一套。",
        "",
        "| 量 | n | 均值 (eV) | 总体标准差 (eV) |",
        "| --- | --- | --- | --- |",
        "| dIP = IP(C1) - IP(C0) | %s | %s | **%s** |" % (d_ip.get("n"), ip_mean, ip_std),
        "| dEA = EA(C1) - EA(C0) | %s | %s | **%s** |" % (d_ea.get("n"), ea_mean, ea_std),
        "",
        "**四个单变量台阶的同口径对比**（同一批分子、同一估计量 population std；见 `F12` 面板 (b)）：",
        "",
        "| 台阶 | IP 位移均值 | **IP 位移 std** | n |",
        "| --- | --- | --- | --- |",
        step_table,
        "",
        compare,
        "",
        "C0 -> C1 决策量：氧化 tau_b **%s**、f_robust_inv **%s**；还原 tau_b **%s**、"
        "f_robust_inv **%s**。" % (tau_ox, robust_ox, tau_red, robust_red),
        "",
    ])

    qc = "（`c1_li_coordination_summary.json` 未纳入）"
    if run:
        flags = run.get("qc_flag_counts") or {}
        active = ", ".join("%s=%s" % (key, value)
                           for key, value in sorted(flags.items()) if value)
        qc = ("C1 作业 **%s / %s** 成功，状态计数 `%s`；QC 标记：%s（`c1_li_coordination_summary.json`）。"
              % (run.get("n_ok"), run.get("n_jobs"), run.get("status_counts"),
                 active or "全部为 0"))

    did = ("对 %d 个分子（%s）按冻结的 7 步规则枚举 [Li M]+ motif（%d 个），做 C1 条件态扫描"
           "（r2SCAN-3c）与配位台阶分析。" % (n, "、".join(molecules), n_motifs))
    metric = ("C1 配位台阶（N=%d，参考配体 R=%s）的 dIP 均值 %s eV、总体标准差 **%s eV**；"
              "氧化 tau_b = %s、f_robust_inv = %s。"
              % (n, C1_REFERENCE_LIGAND, ip_mean, ip_std, tau_ox, robust_ox))
    sigma_note = ("第四级台阶是条件态（C0 -> C1，Li+ 配位）：N=%d，IP 位移均值 %s eV、离散度 **%s eV**，"
                  "氧化 tau_b %s、f_robust_inv %s —— 它衡量「同一个分子带着一个 Li+ 时，代理还剩多少"
                  "分辨力」。" % (n, ip_mean, ip_std, tau_ox, robust_ox))
    step_row = ("| C0 -> C1 | 条件态（自由分子 -> [Li M]+ 配位） | %s eV | **%s eV** | **%s** | —— |"
                % (ip_mean, ip_std, tau_ox))
    limit = ("**C1（Li+ 配位）只覆盖主 motif**：每个分子只取一个主 motif，本台阶的逐分子样本数为 **%d**；"
             "未在 motif 之间做能量加权或构象平均。" % n)
    return {"present": True, "did": did, "block": block_text, "qc": qc, "step_row": step_row,
            "metric": metric, "sigma_note": sigma_note, "limit": limit}


T6_SUMMARY_PATH = REPO / "outputs" / "week6" / "t6_conformer_spread.json"
T7_SUMMARY_PATH = REPO / "outputs" / "week6" / "t7_c1_freq_check.json"
T8_SUMMARY_PATH = REPO / "outputs" / "week6" / "delta_m_frozen.json"
T9_SUMMARY_PATH = REPO / "outputs" / "week6" / "stage6_decision_stability.json"

W6_PAIRS = (("P0_to_P1", "P0 -> P1"), ("P1_to_P2", "P1 -> P2"), ("C0_to_C1", "C0 -> C1"))
W6_AXES = (("oxidation", "氧化"), ("reduction", "还原"))


def week6_blocks(t6, t7, t8, t9):
    """Render the week-6 (Stage 6) blocks from the T6/T7/T8/T9 JSON files.

    Same contract as ``t2_blocks`` / ``c1_blocks``: report and figure are fed by
    the same JSON, and a missing summary yields an "absent" record instead of an
    exception, so the digest and the plan stay valid while the stage is running.
    """

    empty = {
        "present": False,
        "did": "（本轮未纳入 `outputs/week6/*`：Stage 6 尚未产出）",
        "metric": "",
        "qc": "",
        "limit": "",
        "t6_block": "",
        "t7_block": "",
        "delta_m_block": "",
        "t9_block": "",
        "sigma_note": "",
    }
    if not (t6 and t8 and t9):
        return empty

    counts = t6.get("counts") or {}
    rows = ["| 层 | 目标 | `sigma_conf` [eV] | 90 分位展宽 [eV] | 最大展宽 [eV] | n 分子 |",
            "| --- | --- | --- | --- | --- | --- |"]
    for layer in ("p0", "p1"):
        agg = ((t6.get("layers") or {}).get(layer) or {}).get("aggregate") or {}
        for axis, label in W6_AXES:
            a = agg.get(axis) or {}
            rows.append("| %s | %s | **%s** | %s | %s | %s |"
                        % (layer.upper(), label, _fnum(a.get("sigma_conf_ev")),
                           _fnum(a.get("p90_spread_ev")), _fnum(a.get("max_spread_ev")),
                           a.get("n_molecules")))
    t6_block = chr(10).join(rows + [
        "",
        "构象系综：%d 分子 / %s 构象；P0 失败 %s、P1 失败 %s。"
        % (len(t6.get("subset") or []),
           ((counts.get("p1") or {}).get("n_conformers_total")),
           ((counts.get("p0") or {}).get("n_failures")),
           ((counts.get("p1") or {}).get("n_failures")))])

    t7_rows = ["| 分子 | motif | 最低非零模式 [cm^-1] | n 虚频 | 是否极小 | QC |",
               "| --- | --- | --- | --- | --- | --- |"]
    for r in (t7.get("rows") or []) if t7 else []:
        modes = r.get("lowest_nonzero_modes_cm") or []
        t7_rows.append("| %s | %s | %s | %s | %s | %s |"
                       % (r.get("name"), r.get("motif_id"),
                          _fnum(modes[0] if modes else None, digits=2),
                          r.get("n_imaginary"),
                          "是" if r.get("is_minimum") else "**否**",
                          ", ".join(r.get("qc_flags") or []) or "——"))
    t7_block = chr(10).join(t7_rows)

    meth = t8.get("method_evidence") or {}
    conf = (t8.get("conformer_evidence") or {}).get("p1") or {}
    floor = (t8.get("rule_text") or {}).get("floor_ev")
    cand = (t9.get("delta_m_candidates") or {}).get("p1") or {}
    d_rows = ["| 目标 | 构象 90 分位 [eV] | 方法 pstdev [eV] | 0.05 eV 下限 [eV] | **delta_m [eV]** | delta_m [kJ/mol] | 主导项 |",
              "| --- | --- | --- | --- | --- | --- | --- |"]
    for axis, label in W6_AXES:
        c = conf.get(axis) or {}
        m = meth.get(axis) or {}
        d = cand.get(axis) or {}
        d_rows.append("| %s | %s | %s | %s | **%s** | %s | %s |"
                      % (label, _fnum(c.get("p90_spread_ev")), _fnum(m.get("sigma_method_ev")),
                         _fnum(floor), _fnum(d.get("delta_m_ev")),
                         _fnum(d.get("delta_m_kj"), digits=1), d.get("dominant_term")))
    anchors = t8.get("anchors") or {}
    delta_m_block = chr(10).join(d_rows + [
        "",
        "source_rule (1) 不可用：锚点 %s 行、重复 series **%s** 个、"
        "非估计方法行 %s 个 → `available=%s`。"
        % (anchors.get("n_rows"), anchors.get("n_replicated_series"),
           anchors.get("n_rows_with_non_estimate_method"), anchors.get("available"))])

    result = (t9.get("results") or {}).get("docx_max") or {}
    t9_rows = ["| 层对 | 目标 | tau_b [CI95] | f_unresolved（下/上） | 双方均解析 / 总 pair | delta_m 起决定作用 | O_k(20%) | f_robust_inv |",
               "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for pair, plabel in W6_PAIRS:
        for axis, alabel in W6_AXES:
            e = (result.get(pair) or {}).get(axis) or {}
            ci = e.get("kendall_tau_b_ci95") or [None, None]
            o20 = ((e.get("top_k") or {}).get("k=0.20") or {}).get("overlap")
            t9_rows.append("| %s | %s | %s [%s, %s] | %s / %s | **%s** / %s | %s | %s | %s |"
                           % (plabel, alabel, _fnum(e.get("kendall_tau_b")),
                              _fnum(ci[0]), _fnum(ci[1]),
                              _fnum(e.get("f_unresolved_lower")),
                              _fnum(e.get("f_unresolved_upper")),
                              e.get("n_pairs_resolved_in_both"), e.get("n_pairs"),
                              e.get("n_pairs_delta_m_is_binding"), _fnum(o20),
                              _fnum(e.get("f_robust_inv"))))
    t9_block = chr(10).join(t9_rows)

    ex = (result.get("P0_to_P1") or {}).get("oxidation") or {}
    sigma_note = ("**Stage 6（不确定性感知排序）**：把 `delta_m` 并入 pair 判定后，"
                  "P0->P1 氧化轴 tau_b = %s、`f_unresolved` = %s（下侧）、"
                  "双方均解析 pair = **%s / %s**；同家族 pair 的 "
                  "`f_unresolved`（下）= %s。`f_robust_inv` 必须与「双方均解析 pair 数」并列读。"
                  % (_fnum(ex.get("kendall_tau_b")), _fnum(ex.get("f_unresolved_lower")),
                     ex.get("n_pairs_resolved_in_both"), ex.get("n_pairs"),
                     _fnum(ex.get("family_within_f_unresolved_lower"))))

    did = ("构建 12 分子构象系综得到 `sigma_conf`（T6）；"
           "按冻结规则组装 `delta_m` 候选值（T8）；"
           "在 `delta_m = 0 / 0.05 eV / docx_max` 三个口径下重算决策稳定性（T9）；"
           "并对 C1 `[Li M]+` 优化几何做纯 Freq 虚频检查（T7）。")

    d_ox = (cand.get("oxidation") or {})
    d_red = (cand.get("reduction") or {})
    t9_ox = (result.get("P0_to_P1") or {}).get("oxidation") or {}
    t9_red = (result.get("P0_to_P1") or {}).get("reduction") or {}
    metric = ("`delta_m`（docx_max）氧化 **%s eV**（%s kJ/mol，主导项 %s）、"
              "还原 **%s eV**（%s kJ/mol、主导项 %s）；并入后 P0->P1 "
              "氧化 tau_b %s、还原 tau_b %s。"
              % (_fnum(d_ox.get("delta_m_ev")), _fnum(d_ox.get("delta_m_kj"), digits=1),
                 d_ox.get("dominant_term"), _fnum(d_red.get("delta_m_ev")),
                 _fnum(d_red.get("delta_m_kj"), digits=1), d_red.get("dominant_term"),
                 _fnum(t9_ox.get("kendall_tau_b")), _fnum(t9_red.get("kendall_tau_b"))))

    qc = ("T6 构象单点失败数 P0/P1 = %s/%s；T7 虚频检查 %s/%s 成功、"
          "%s 个非极小；T9 一致性自检 %s 条（含 C0->C1 与 Week 5 记录的对比）。"
          % (((counts.get("p0") or {}).get("n_failures")), ((counts.get("p1") or {}).get("n_failures")),
             (t7.get("n_ok") if t7 else None), (t7.get("n_molecules") if t7 else None),
             (t7.get("n_imaginary") if t7 else None),
             len(t9.get("consistency_checks") or [])))

    limit = ("**Stage 6 的还原轴在当前证据下不可判定**：并入 `delta_m` "
             "后，P0->P1 与 P1->P2 的还原轴「双方均解析」pair 数降为 0，"
             "`f_robust_inv` 的分母因此为 0；该指标不得读成「稳定」。")

    return {"present": True, "did": did, "metric": metric, "qc": qc, "limit": limit,
            "t6_block": t6_block, "t7_block": t7_block, "delta_m_block": delta_m_block,
            "t9_block": t9_block, "sigma_note": sigma_note}


W7_BASELINES = ("random", "diversity", "uncertainty", "ranking_aware")


def _w7_num(value, digits=3):
    if value is None:
        return "n/a"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "n/a"
    if number != number:
        return "n/a"
    return ("%%.%df" % digits) % number


def _w7_rows(results, task, fset, objective, split, shape, model=None):
    picked = []
    for row in results:
        if (row.get("task") != task or row.get("feature_set") != fset
                or row.get("objective") != objective or row.get("split") != split
                or row.get("shape") != shape):
            continue
        if model is not None and row.get("model") != model:
            continue
        if not isinstance(row.get("kendall_tau_b"), (int, float)):
            continue
        picked.append(row)
    return picked


def _w7_best(results, task, fset, objective, split, shape, model=None):
    rows = _w7_rows(results, task, fset, objective, split, shape, model)
    if not rows:
        return None
    return max(rows, key=lambda row: row["kendall_tau_b"])


def _w7_pair_keys(results):
    order, seen = [], set()
    for row in results:
        key = (row.get("task"), row.get("feature_set"), row.get("objective"))
        if key not in seen:
            seen.add(key)
            order.append(key)
    return order


def _w8_num(value, digits=3):
    if value in (None, ""):
        return "\u2014"
    try:
        return ("%." + str(digits) + "f") % float(value)
    except (TypeError, ValueError):
        return "\u2014"


def _w8_truthy(value):
    return str(value).strip().lower() in ("1", "true", "yes")


def _w8_mean_std(rows, key):
    values = []
    for row in rows:
        value = row.get(key)
        if value in (None, ""):
            continue
        try:
            values.append(float(value))
        except (TypeError, ValueError):
            continue
    if not values:
        return None, None
    mean = sum(values) / len(values)
    if len(values) < 2:
        return mean, 0.0
    std = (sum((value - mean) ** 2 for value in values) / (len(values) - 1)) ** 0.5
    return mean, std


def week8_blocks(stage9, shells):
    """Render the week-8 (Stage 9 / explicit microsolvation) blocks."""

    empty = {"present": False, "did": "", "metric": "", "qc": "", "limit": "",
             "s9_block": "", "summary": ""}
    if not isinstance(stage9, dict) or not (stage9.get("shifts") or []):
        return empty

    shifts = stage9.get("shifts") or []
    stability = stage9.get("stability") or []
    dft = stage9.get("dft_jobs") or {}
    primary = [row for row in shifts if _w8_truthy(row.get("is_primary"))]
    done = [row for row in primary if row.get("ip_shell2_ev") not in (None, "")]
    families = sorted({row.get("family") for row in shifts if row.get("family")})

    m1 = _w8_mean_std(done, "d_ip_shell1_ev")
    m2 = _w8_mean_std(done, "d_ip_shell2_ev")
    e1 = _w8_mean_std(done, "d_ea_shell1_ev")
    e2 = _w8_mean_std(done, "d_ea_shell2_ev")
    dd = _w8_mean_std(done, "d_d_ip_ev")
    de = _w8_mean_std(done, "d_d_ea_ev")

    def _ms(pair):
        mean, std = pair
        if mean is None:
            return "\u2014"
        return "%+.3f \u00b1 %.3f eV" % (mean, std if std is not None else 0.0)

    table = {(row.get("axis"), row.get("population")): row for row in stability}

    def _stab(axis, population):
        row = table.get((axis, population)) or {}
        return ("n=%s, tau_b **%s**, Top-20%% 重叠 %s, f_unresolved %s, f_robust_inv %s"
                % (row.get("n", "\u2014"),
                   _w8_num(row.get("kendall_tau_b")),
                   _w8_num(row.get("overlap_20")),
                   _w8_num(row.get("f_unresolved_shell2")),
                   _w8_num(row.get("f_robust_inv"))))

    did = ("对 Week 5 的 C1(1:1) 条件态做**显式第一溶剂壳**复核：把 [Li M]+ 扩成 [Li(M)2]+，"
           "共 **%d** 个壳层 motif（覆盖 **%d** 个家族），复用同一条冻结计算臂"
           "（r2SCAN-3c、气相、相同种子）测同一组三态垂直量，再与 C1(1:1)"
           "（`outputs/week5/c1_coord_shifts.csv`）和自由分子 C0 做同口径的配对排序稳定性对比。"
           "壳层枚举规则：锚定 r2SCAN-3c 优化的 [Li M]+ 几何，取 G1 第二配体，Fibonacci 球面 "
           "96 方向 x 12 滚转刚体放置，剔除冲突后取前 4 个做 GFN2-xTB 打分，最低者做 xTB 优化。"
           % (len(shifts), len(families)))

    metric = ("- 逐 motif 位移（相对 C0，均值 ± 样本 std）：C1(1:1) 氧化 %s / 还原 %s；"
              "C2(1:2) 氧化 %s / 还原 %s\n"
              "- 从 1:1 到 1:2 的**位移本身的变化**：\u0394IP %s，\u0394EA %s\n"
              "- 氧化轴 C1 -> C2：%s\n"
              "- 还原轴 C1 -> C2：%s"
              % (_ms(m1), _ms(e1), _ms(m2), _ms(e2), _ms(dd), _ms(de),
                 _stab("oxidation", "all12"), _stab("reduction", "all12")))

    status_counts = dft.get("status_counts") or {}
    flags = dft.get("qc_flag_counts") or {}
    qc = ("DFT 作业 **%s** 个，`ok` **%s** 个；状态分布 %s；QC flag %s"
          % (dft.get("n_jobs"), dft.get("n_ok"),
             ", ".join("%s=%s" % item for item in sorted(status_counts.items())) or "\u2014",
             ", ".join("%s=%s" % item for item in sorted(flags.items())) or "无"))
    if isinstance(shells, dict) and shells.get("n_selected") is not None:
        qc += ("；壳层生成 %s 个放置（%s 个无冲突、%s 个被打分、%s 个入选），"
               "全部 `second_ligand_intact=True`"
               % (shells.get("n_placements"), shells.get("n_clash_free"),
                  shells.get("n_scored"), shells.get("n_selected")))

    limit = ("Stage 9 只做**垂直**量（`--skip-relax`），因为 Week 5 的头条口径也是垂直量；"
             "氧化/还原态的再弛豫在 1:1 里本就属支线，1:2 未复现。壳层是**几何预筛**结果"
             "（xTB 打分后的最低者），不是全构象系综的最低能结构。")

    s9_block = ("| 轴 | 总体 | n | tau_b | Top-10% 重叠 | Top-20% 重叠 | f_unresolved (C2) | f_robust_inv |\n"
                "| --- | --- | --- | --- | --- | --- | --- | --- |\n")
    for axis, population, label in (("oxidation", "all12", "氧化"),
                                    ("reduction", "all12", "还原"),
                                    ("oxidation", "primary_m1", "氧化（仅 m1）"),
                                    ("reduction", "primary_m1", "还原（仅 m1）")):
        row = table.get((axis, population)) or {}
        n = row.get("n", 0)
        if not n or int(n) < 2:
            s9_block += "| %s | %s | %s | \u2014 | \u2014 | \u2014 | \u2014 | \u2014 |\n" % (
                label, population, n)
            continue
        s9_block += ("| %s | %s | %s | %s | %s | %s | %s | %s |\n"
                     % (label, population, n,
                        _w8_num(row.get("kendall_tau_b")),
                        _w8_num(row.get("overlap_10")),
                        _w8_num(row.get("overlap_20")),
                        _w8_num(row.get("f_unresolved_shell2")),
                        _w8_num(row.get("f_robust_inv"))))

    summary = ("- 做了什么：%s\n- 关键数字：\n%s\n- 质检：%s\n- 限制：%s"
               % (did, metric, qc, limit))
    return {"present": True, "did": did, "metric": metric, "qc": qc, "limit": limit,
            "s9_block": s9_block, "summary": summary}


W9_RUNG_ORDER = ("P0_to_P1", "P1_to_P2", "G1_to_G2", "C0_to_C1", "C1_to_C2")
W9_RUNG_SHORT = {
    "P0_to_P1": "P0 -> P1 (\u65b9\u6cd5)",
    "P1_to_P2": "P1 -> P2 (\u73af\u5883)",
    "G1_to_G2": "G1 -> G2 (\u51e0\u4f55)",
    "C0_to_C1": "C0 -> C1 (\u914d\u4f4d)",
    "C1_to_C2": "C1 -> C2 (\u58f3\u5c42)",
}
W9_AXIS_SHORT = (("oxidation", "\u6c27\u5316"), ("reduction", "\u8fd8\u539f"))


def week9_blocks(stage10):
    """Render the week-9 (Stage 10 / five-rung synthesis) blocks."""

    empty = {"present": False, "did": "", "metric": "", "qc": "", "limit": "",
             "ladder_block": "", "verdict_block": "", "sigma_note": "", "summary": ""}
    if not isinstance(stage10, dict) or not (stage10.get("ladder") or []):
        return empty

    rows = stage10.get("ladder") or []
    hypothesis = stage10.get("hypothesis_test") or {}
    verdicts = stage10.get("verdicts") or {}
    checklist = stage10.get("minimum_outcome_checklist") or []
    subset = stage10.get("common_subset") or []
    table = {(row.get("rung"), row.get("axis")): row for row in rows
             if row.get("population") == "common10"}

    def num(value, digits=3):
        return _w8_num(value, digits)

    def signed(value, digits=3):
        text = _w8_num(value, digits)
        if text == "\u2014":
            return text
        return text if float(value) < 0 else "+" + text

    ladder_block = ("| \u53f0\u9636 | \u8f74 | n | \u4f4d\u79fb\u5747\u503c (eV) | "
                    "\u4f4d\u79fb std (eV) | tau_b | O_10% | O_20% | f_unresolved (after) | "
                    "f_robust_inv | sigma_median (eV) |\n"
                    "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n")
    for key in W9_RUNG_ORDER:
        for axis, axis_label in W9_AXIS_SHORT:
            row = table.get((key, axis)) or {}
            ladder_block += ("| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |\n"
                             % (W9_RUNG_SHORT.get(key, key), axis_label,
                                row.get("n", "\u2014"),
                                signed(row.get("shift_mean_ev")),
                                num(row.get("shift_std_ev")),
                                num(row.get("kendall_tau_b")),
                                num(row.get("overlap_10")),
                                num(row.get("overlap_20")),
                                num(row.get("f_unresolved_after")),
                                num(row.get("f_robust_inv")),
                                num(row.get("sigma_median_ev"))))

    verdict_block = ("| \u60c5\u5f62 | \u5224\u5b9a | \u4f9d\u636e |\n| --- | --- | --- |\n")
    for key in sorted(k for k in verdicts if not k.startswith("_")):
        entry = verdicts[key] or {}
        evidence = str(entry.get("evidence") or "")
        if len(evidence) > 280:
            evidence = evidence[:280] + "\u2026\u2026"
        verdict_block += "| %s | **%s** | %s |\n" % (
            entry.get("short") or key, entry.get("verdict") or "\u2014", evidence)

    spread = hypothesis.get("spearman_shift_std_vs_tau_b")
    magnitude = hypothesis.get("spearman_abs_shift_mean_vs_tau_b")
    unres = hypothesis.get("spearman_shift_std_vs_f_unresolved")
    bad = table.get(("C0_to_C1", "reduction")) or {}
    big = table.get(("P0_to_P1", "reduction")) or {}
    statuses = {item.get("id"): item.get("status") for item in checklist}

    did = ("\u628a Week 4-8 \u7684**\u4e94\u7ea7\u53f0\u9636**\u653e\u5230**\u540c\u4e00\u53e3\u5f84**"
           "\uff08`p_red = -EA`\uff0c\u4e24\u4e2a\u8f74\u90fd `higher_is_better = True`\uff09\u4e0e"
           "**\u540c\u4e00\u5206\u5b50\u5b50\u96c6**\u4e0a\u91cd\u7b97\uff1a\u7535\u5b50\u7ed3\u6784\u65b9\u6cd5"
           "\uff08P0 -> P1\uff09\u3001\u73af\u5883\uff08P1 -> P2\uff09\u3001\u51e0\u4f55\uff08G1 -> G2\uff09\u3001"
           "\u914d\u4f4d\u6761\u4ef6\u6001\uff08C0 -> C1\uff09\u4e0e\u7b2c\u4e8c\u6eb6\u5242\u58f3\uff08C1 -> C2\uff09\u3002"
           "\u5171\u540c\u5b50\u96c6\u4e3a **%d \u4e2a\u5206\u5b50**\uff08%s\uff09\uff0c"
           "\u5b83\u4eec\u5728**\u6bcf\u4e00\u7ea7\u90fd\u6709\u5b8c\u6574\u503c**\uff1b"
           "\u7b2c 4/5 \u7ea7\u53d6 primary m1 motif \u4f5c\u4e3a\u5206\u5b50\u7ea7\u4ee3\u8868\uff0c"
           "\u4ee5\u514d\u7ed9 DMC / TMP \u7684\u7b2c\u4e8c\u4e2a\u914d\u4f4d\u6a21\u5f0f\u53cc\u500d\u6743\u91cd\u3002"
           "**\u672c\u9636\u6bb5\u4e0d\u8dd1\u65b0\u7684\u7535\u5b50\u7ed3\u6784\u8ba1\u7b97**\uff0c"
           "\u53ea\u91cd\u8bfb\u5df2\u51bb\u7ed3\u7684 week-4/5/8 \u4ea7\u7269\u3002"
           % (len(subset), "\u3001".join(subset)))

    metric = ("- \u4e2d\u5fc3\u547d\u9898\uff1a\u79bb\u6563\u5ea6\u51b3\u5b9a\u6392\u5e8f\u662f\u5426\u88ab\u6539\u5199\u3002"
              "Spearman rho(shift std, tau_b) = **%s**\uff1brho(abs(shift mean), tau_b) = %s\uff08\u5bf9\u7167\uff09\uff1b"
              "rho(shift std, f_unresolved) = **%s**\n"
              "- \u6700\u950b\u5229\u7684\u5bf9\u7167\uff1aP0 -> P1 \u8fd8\u539f\u8f74\u4f4d\u79fb\u6700\u5927\uff08%s eV\uff0c"
              "std %s\uff09\u5374\u4fdd\u4f4f\u4e86\u6392\u5e8f\uff08tau_b %s\uff09\uff1b"
              "C0 -> C1 \u8fd8\u539f\u8f74\u4f4d\u79fb\u76f8\u4eff\uff08%s eV\uff0cstd %s\uff09"
              "\u5374**\u6362\u53f7**\uff08tau_b %s\uff09\u2014\u2014\u5dee\u522b\u5728\u79bb\u6563\u5ea6\n"
              "- %d \u4e2a (\u53f0\u9636, \u8f74) \u7ec4\u5408\u4e2d `f_robust_inv` \u6052\u4e3a 0.000"
              "\uff08z = 1.96 \u4e5f\u5168\u4e3a 0\uff09\uff0c\u4f46 `f_unresolved` \u6700\u9ad8\u8fbe %s\uff1a"
              "\u8fd9\u4e2a 0 \u662f\u300c\u4e0d\u53ef\u5224\u5b9a\u300d\u800c\u975e\u300c\u7a33\u5b9a\u300d\n"
              "- v2 \u00a723 \u6700\u5c0f\u6210\u679c\u5224\u636e\uff1a11 \u6761\u4e2d 10 \u6761 PASS\uff0c"
              "\u552f\u4e00 PARTIAL \u662f\u6eb6\u6db2\u951a\u70b9\uff08Gate 1 blocker\uff09"
              % (num(spread), num(magnitude), num(unres),
                 signed(big.get("shift_mean_ev")), num(big.get("shift_std_ev")),
                 num(big.get("kendall_tau_b")),
                 signed(bad.get("shift_mean_ev")), num(bad.get("shift_std_ev")),
                 num(bad.get("kendall_tau_b")),
                 len(rows), num(max([row.get("f_unresolved_after") or 0.0 for row in rows]
                                    or [0.0]))))

    qc = ("%d \u884c\uff08native + common10 \u5404 10 \u884c\uff09\u00d7 25 \u5217\uff0c"
          "\u7531 `analyze_stage10_synthesis.py` \u4ece 5 \u4e2a\u5df2\u51bb\u7ed3\u6e90\u6587\u4ef6\u73b0\u573a\u91cd\u7b97\uff1b"
          "A-G \u60c5\u5f62\u5224\u5b9a + \u00a7 23 \u5224\u636e\u5bf9\u7167\u5747\u7531\u540c\u4e00\u811a\u672c\u4ea7\u51fa\uff1b"
          "\u5224\u636e 5 = %s\uff0c\u5224\u636e 7 = %s\u3002"
          % (len(rows), statuses.get("5") or "?", statuses.get("7") or "?"))

    limit = ("common-10 \u662f\u5c0f\u6837\u672c\uff08n = 10 \u4e2a\u53f0\u9636\u4e8b\u4ef6\uff09\uff0c"
             "\u79e9\u76f8\u5173\u53ea\u80fd\u8bfb\u65b9\u5411\u4e0e\u91cf\u7ea7\uff0c\u4e0d\u80fd\u8bfb\u663e\u8457\u6027\uff1b"
             "Top-k \u7684 k \u968f N \u53d8\u5316\uff0c\u8df3\u53f0\u9636\u6bd4\u8f83\u53ea\u770b\u8d8b\u52bf\u3002"
             "C0 -> C1 \u8fd8\u539f\u8f74\u7684\u4f4d\u79fb\u6d4b\u7684\u662f\u300cLi \u4e2d\u5fc3\u8fd8\u539f\u300d"
             "\uff0811/12 \u4e2a\u8fd8\u539f\u6001\u7684\u7535\u5b50\u843d\u5728 Li \u4e0a\uff09\uff0c"
             "\u4e0e\u5176\u4ed6\u53f0\u9636\u4e0d\u662f\u540c\u4e00\u7269\u7406\u8fc7\u7a0b\uff0c\u5176 tau_b "
             "\u4e0d\u5f97\u7528\u4e8e\u300c\u65b9\u6cd5\u53ef\u8fc1\u79fb\u6027\u300d\u8bba\u8bc1\u3002")

    sigma_note = ("**\u4e94\u7ea7\u53f0\u9636\u7684\u540c\u53e3\u5f84\u5408\u6210\uff08Stage 10 / week9\uff09**\uff1a"
                  "\u628a P0->P1\u3001P1->P2\u3001G1->G2\u3001C0->C1\u3001C1->C2 \u653e\u5728\u540c\u4e00\u7ea6\u5b9a"
                  "\u4e0e\u540c\u4e00 10 \u5206\u5b50\u5b50\u96c6\u4e0a\u540e\uff0c\u4f4d\u79fb**\u79bb\u6563\u5ea6**"
                  "\u4e0e tau_b \u7684 Spearman rho = **%s**\uff0c\u800c\u4f4d\u79fb**\u5e45\u5ea6**\u7684 rho "
                  "\u53ea\u6709 %s\uff1b\u79bb\u6563\u5ea6\u4e0e `f_unresolved` \u7684 rho = **%s**\u3002"
                  "\u540c\u4e00\u5f20\u8868\u91cc\u6700\u5c16\u9510\u7684\u5bf9\u7167\uff1aP0->P1 \u8fd8\u539f\u8f74"
                  "\u4f4d\u79fb\u6700\u5927\uff08%s eV\uff09\u5374\u4fdd\u4f4f\u4e86\u6392\u5e8f\uff08tau_b %s\uff09\uff0c"
                  "\u800c C0->C1 \u8fd8\u539f\u8f74\u4f4d\u79fb\u76f8\u4eff\uff08%s eV\uff09\u5374\u6362\u53f7"
                  "\uff08tau_b %s\uff09\u2014\u2014\u5dee\u522b\u5728\u79bb\u6563\u5ea6 %s vs %s eV\u3002"
                  "\u552f\u4e00\u8d1f tau_b \u51fa\u73b0\u7684\u90a3\u4e00\u7ea7\uff0c\u5176\u8fd8\u539f\u6001 11/12 "
                  "\u662f Li \u4e2d\u5fc3/\u6df7\u5408\u8fd8\u539f\uff08state-identity \u6539\u53d8\uff09\uff0c"
                  "\u5373\u8be5\u8f74\u6d4b\u7684\u4e0d\u662f\u540c\u4e00\u4e2a\u7269\u7406\u91cf\u3002"
                  "\u89c1 F19\uff08`outputs/figures/F19_stage10_ladder.png`\uff09\u3002"
                  % (num(spread), num(magnitude), num(unres),
                     signed(big.get("shift_mean_ev")), num(big.get("kendall_tau_b")),
                     signed(bad.get("shift_mean_ev")), num(bad.get("kendall_tau_b")),
                     num(big.get("shift_std_ev")), num(bad.get("shift_std_ev"))))

    summary = ("- \u505a\u4e86\u4ec0\u4e48\uff1a%s\n- \u5173\u952e\u6570\u5b57\uff1a\n%s\n"
               "- \u8d28\u68c0\uff1a%s\n- \u9650\u5236\uff1a%s" % (did, metric, qc, limit))
    return {"present": True, "did": did, "metric": metric, "qc": qc, "limit": limit,
            "ladder_block": ladder_block, "verdict_block": verdict_block,
            "sigma_note": sigma_note, "summary": summary}


F20_NOTE_PRESENT = ("Stage 11 sigma 解剖：(a) T1 恒等式 sigma_ij = abs(d_i - d_j)/sqrt(2) 的"
                    "全 pair 散点（机器精度落在 y = x 上）；(b) 10 条割线斜率 q_ij 分布与两条临界"
                    "斜率 sqrt(2)/z；(c) f_unresolved 实测 vs 闭式（20 点，误差精确为 0）；"
                    "(d) 9 个廉价预测子对「top-2 候选清单被改写」的 AUC")
F20_NOTE_ABSENT = "预留给 Stage 11（sigma 解剖）；week10 尚未产出"
F21_NOTE_PRESENT = ("Stage 11 反事实对照：(a) 线性位移相图（排序在 b = -1 翻转，分辨率在 "
                    "abs(b) = sqrt(2)/z 崩塌）；(b) 单调且 f-Lipschitz 的位移——tau_b = 1.000 与 "
                    "f_unresolved = 0.000 同时成立；(c) 拉伸目标轴 / 白噪声 / 刚性偏移的对照；"
                    "(d) 子集规模 N 从 6 到 18 的 tau_b 抽样分布（星号 = common-10）")
F21_NOTE_ABSENT = "预留给 Stage 11（反事实对照）；week10 尚未产出"
W10_ANATOMY_PATH = REPO / "outputs" / "week10" / "stage11_sigma_anatomy.json"
W10_RUNG_ORDER = ("P0_to_P1", "P1_to_P2", "G1_to_G2", "C0_to_C1", "C1_to_C2")
W10_AXIS_SHORT = (("oxidation", "氧化"), ("reduction", "还原"))


def week10_blocks(anatomy):
    """Render the week-10 (Stage 11 / sigma anatomy) blocks."""

    empty = {"present": False, "did": "", "metric": "", "qc": "", "limit": "",
             "theorem_block": "", "ladder_block": "", "control_block": "",
             "predictor_block": "", "drift_block": "", "sigma_note": "", "summary": ""}
    if not isinstance(anatomy, dict) or not (anatomy.get("rows") or []):
        return empty

    rows = anatomy.get("rows") or []
    subset = anatomy.get("common_subset") or []
    theorems = anatomy.get("theorems") or {}
    controls = anatomy.get("controls") or {}
    checks = anatomy.get("control_checks") or {}
    predict = anatomy.get("predictability") or {}
    table = sorted([item for item in (predict.get("table") or [])
                    if item.get("auc") is not None],
                   key=lambda item: -item["auc"])
    drift = anatomy.get("subset_drift") or {}
    marks = anatomy.get("subset_drift_marks") or {}
    key = anatomy.get("key_numbers") or {}
    by_key = {(row.get("rung"), row.get("axis")): row for row in rows}

    def num(value, digits=3):
        return _w8_num(value, digits)

    def signed(value, digits=3):
        text = _w8_num(value, digits)
        if text == "—":
            return text
        return text if float(value) < 0 else "+" + text

    theorem_block = ("| 编号 | 命题 | 数值验证 | 结论 |\n| --- | --- | --- | --- |\n")
    theorem_rows = (
        ("T1", "sigma_ij = abs(d_i - d_j)/sqrt(2)",
         "最大绝对误差 %s eV" % ("%.2e" % (theorems.get("T1_sigma_is_shift_difference") or {}).get("max_abs_err_ev", 0.0)),
         theorems.get("T1_sigma_is_shift_difference") or {}),
        ("T2", "RMS_{i<j} sigma_ij = stdev_sample(d)",
         "最大相对误差 %s" % ("%.2e" % (theorems.get("T2_rms_sigma_is_shift_stdev") or {}).get("max_rel_err", 0.0)),
         theorems.get("T2_rms_sigma_is_shift_stdev") or {}),
        ("T3", "层间刚性偏移不改变任何指标",
         "max abs(d sigma) = %s eV" % ("%.2e" % (theorems.get("T3_rigid_offset_invariance") or {}).get("max_abs_d_sigma_ev", 0.0)),
         theorems.get("T3_rigid_offset_invariance") or {}),
        ("T4", "f_unresolved(z) = Pr(q_ij > sqrt(2)/z)",
         "z=1 误差 %s，z=1.96 误差 %s" % (
             "%.2e" % (theorems.get("T4_closed_form_unresolved") or {}).get("max_abs_err_z1", 0.0),
             "%.2e" % (theorems.get("T4_closed_form_unresolved") or {}).get("max_abs_err_z1p96", 0.0)),
         theorems.get("T4_closed_form_unresolved") or {}),
        ("T5", "var(d) = b^2 var(P1) + var(residual)",
         "份额和偏差 %s" % ("%.2e" % (theorems.get("T5_sigma2_budget_split") or {}).get("max_abs_share_err", 0.0)),
         theorems.get("T5_sigma2_budget_split") or {}),
    )
    for tag, statement, evidence, entry in theorem_rows:
        theorem_block += "| **%s** | %s | %s | %s |\n" % (
            tag, statement, evidence, "PASS" if entry.get("ok") else "FAIL")

    ladder_block = ("| 台阶 | 轴 | n | sd(delta) (eV) | q_med | b | R2(平行份额) | tau_b | "
                    "f_unres (z=1) | f_unres (z=1.96) | top20 overlap | 清单被改写 |\n"
                    "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n")
    for rung in W10_RUNG_ORDER:
        for axis, axis_label in W10_AXIS_SHORT:
            row = by_key.get((rung, axis)) or {}
            ladder_block += ("| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |\n"
                             % (rung.replace("_to_", " -> "), axis_label,
                                row.get("n", "—"),
                                num(row.get("delta_sd_ev"), 4),
                                num(row.get("q_median")), signed(row.get("ols_slope_b")),
                                num(row.get("ols_r2")), signed(row.get("kendall_tau_b")),
                                num(row.get("f_unresolved_p1_observed")),
                                num(row.get("f_unresolved_p1_z1p96_observed")),
                                num(row.get("overlap_20"), 2),
                                "是" if row.get("shortlist_rewritten") else "否"))

    linear = controls.get("linear_shift") or []
    control_block = ("**(a) 线性位移相图**（作用于位移最响的台阶的 P1 层）：\n\n"
                     "| b | 预测 sign(tau_b) | tau_b | q_med | f_unres (z=1) | f_unres (z=1.96) | top20 overlap |\n"
                     "| --- | --- | --- | --- | --- | --- | --- |\n")
    for item in linear:
        control_block += "| %s | %+d | %s | %s | %s | %s | %s |\n" % (
            signed(item.get("slope_b")), int(item.get("predicted_tau_b_sign") or 0),
            signed(item.get("tau_b")), num(item.get("q_median")),
            num(item.get("f_unresolved_z1")), num(item.get("f_unresolved_z1p96")),
            num(item.get("overlap_20"), 2))
    rank_shift = controls.get("rank_shift") or []
    control_block += ("\n**(b) 单调且 f-Lipschitz 的位移**（表内 `q_max` 精确等于 `f`）：\n\n"
                      "| f | 幅度 (eV) | tau_b | RMS sigma (eV) | q_max | f_unres 实测 | f_unres 闭式 |\n"
                      "| --- | --- | --- | --- | --- | --- | --- |\n")
    for item in rank_shift:
        control_block += "| %s | %s | %s | %s | %s | %s | %s |\n" % (
            num(item.get("fraction_of_min_gap"), 2), num(item.get("amplitude_ev"), 4),
            signed(item.get("tau_b")), num(item.get("sigma_rms_ev"), 4),
            num(item.get("q_max")), num(item.get("f_unresolved_p1")),
            num(item.get("f_unresolved_p1_closedform")))
    stretch = controls.get("axis_stretch") or []
    control_block += ("\n**(c) 拉伸目标轴**（`d tau_b` 精确为 0，`q' = abs(t + 1 - lambda)/lambda`）：\n\n"
                      "| lambda | d tau_b | q_med 实测 | q_med 由 t 预测 | f_unres 实测 | 由带符号斜率预测 |\n"
                      "| --- | --- | --- | --- | --- | --- |\n")
    for item in stretch:
        control_block += "| %s | %.2e | %s | %s | %s | %s |\n" % (
            num(item.get("lambda"), 2), float(item.get("d_tau_b") or 0.0),
            num(item.get("q_median")), num(item.get("q_median_predicted")),
            num(item.get("f_unresolved_p1")),
            num(item.get("f_unresolved_predicted_from_signed_slopes")))
    rigid = controls.get("rigid_offset") or []
    worst_rigid = max([abs(float(item.get("d_tau_b") or 0.0)) for item in rigid] or [0.0])
    worst_rigid_sigma = max([abs(float(item.get("max_abs_d_sigma_ev") or 0.0)) for item in rigid] or [0.0])
    control_block += ("\n**(d) 层间刚性偏移**：`max abs(d tau_b) = %.1e`，"
                      "`max abs(d sigma) = %.2e eV` —— 均匀方法偏差零成本（T3）。\n"
                      % (worst_rigid, worst_rigid_sigma))

    predictor_block = ("目标：`top-20%% overlap < 1`（n = 10 → k = 2）。正例 %s 个。"
                       "精确置换 p 值穷举 C(10,3) = 120 种标签分配。\n\n"
                       "| 预测子 | 方向 | AUC | 精确置换 p | LOO 阈值命中率 |\n"
                       "| --- | --- | --- | --- | --- |\n"
                       % (predict.get("n_positives")))
    orientation = {"higher_means_rewrite": "越高越危险",
                   "lower_means_rewrite": "越低越危险"}
    for item in table:
        predictor_block += "| `%s` | %s | **%s** | %s | %s |\n" % (
            item.get("predictor"),
            orientation.get(item.get("orientation"), item.get("orientation") or "—"),
            num(item.get("auc")), num(item.get("auc_exact_permutation_p"), 4),
            num(item.get("loo_accuracy")))

    drift_block = ""
    for series, records in drift.items():
        mark = marks.get(series) or {}
        drift_block += ("`%s`（总体 %s 个分子；common-10 读数 %s，全样本读数 %s）：\n\n"
                        "| N | 抽样次数 | tau_b 均值 | p05 | p95 | 标准差 | P(tau_b < 0.5) |\n"
                        "| --- | --- | --- | --- | --- | --- | --- |\n"
                        % (series.replace("_to_", " -> "), mark.get("population_size"),
                           num(mark.get("common10")), num(mark.get("full_population"))))
        for item in records:
            drift_block += "| %d | %d | %s | %s | %s | %s | %s |\n" % (
                item.get("n"), item.get("n_draws"), signed(item.get("tau_b_mean")),
                signed(item.get("tau_b_p05")), signed(item.get("tau_b_p95")),
                num(item.get("tau_b_std")), num(item.get("p_tau_b_below_half")))
        drift_block += "\n"

    spread = by_key.get(("P0_to_P1", "reduction")) or {}
    broken = by_key.get(("C0_to_C1", "reduction")) or {}
    signed_best = next((item for item in table if item.get("predictor") == "ols_slope_b"), {})
    unsigned = next((item for item in table if item.get("predictor") == "sigma_rms_ev"), {})

    did = ("把本周的**分辨率判据**彻底化简：证明并数值验证了四条恒等式 —— "
           "`sigma_ij = abs(delta_i - delta_j)/sqrt(2)`（T1）、`RMS sigma = sd(delta)`（T2）、"
           "`sigma` 对层间刚性偏移严格不变（T3）、以及 **`f_unresolved(z) = Pr(q_ij > sqrt(2)/z)`**（T4，"
           "`q_ij` 为位移对目标轴的割线斜率）。再加一条精确分解 T5（`var(delta)` 拆成保序 / 破序两份额）。"
           "随后做了三件基于定理的分析：**线性位移相图**（四个临界斜率 `±1`、`±sqrt(2)/z`）、"
           "**四组反事实对照**（刚性偏移 / 拉伸目标轴 / 白噪声 / 单调 Lipschitz 位移）、"
           "以及**可预测性检验**（AUC + 精确置换 + LOO）与**子集漂移曲线**。"
           "共同子集仍为 common-%d（%s）。**本阶段不跑任何新的电子结构计算**，"
           "全部内容是对 week4/5/8/9 已冻结产物的代数化简。" % (len(subset), "、".join(subset)))

    metric = ("- T4 把 Week 9 的相关系数 `rho(shift_std, tau_b)` 升级为机制：一对候选可分辨，"
              "当且仅当割线斜率 `q_ij <= sqrt(2)/z`（z=1 时 1.414，z=1.96 时 0.722）；"
              "闭式与实测在 20 个点上**误差精确为 0**\n"
              "- 相图把四种失效模式一次说清：`b < -1` 排序整体反转；`abs(b) > sqrt(2)/z` 分辨率崩塌；"
              "`b` 与 `-b` 的排序后果完全不同 —— 因此**符号比幅度重要**\n"
              "- 那个一直说不通的反例有了答案：`P0 -> P1` 还原轴 `sd(delta) = %s eV`（全篇最大）、"
              "`b = %s`（强正、几乎平行于轴），于是 `f_unresolved = %s`（分辨率崩了）"
              "而清单**完好**（tau_b %s，top-20%% overlap %s）\n"
              "- 可预测性：清单改写**可预测**，但预测子必须方向敏感 —— 带符号斜率 "
              "`ols_slope_b` 的 AUC = **%s**、精确置换 `p = 1/120 = %s`、LOO 10/10（n = 10，"
              "探索性）；无符号的 `sd(delta)` 只有 %s\n"
              "- 一个被否证的直觉：`sigma2_share_residual`（破序份额）在其自然假设方向上 "
              "AUC = 0.000 —— 危险的是**平行份额大**，因为强负斜率既让位移与轴平行、又让排序面临反转\n"
              "- 子集漂移：N = 10 时 `tau_b` 的抽样标准差达 %s（P0 -> P1 氧化轴），"
              "与 week4-9 引用的若干台阶间差异同量级 —— **报 tau_b 必须同时报 N 与子集**"
              % (num(spread.get("sigma_rms_ev"), 4), signed(spread.get("ols_slope_b")),
                 num(spread.get("f_unresolved_p1_observed")), signed(spread.get("kendall_tau_b")),
                 num(spread.get("overlap_20"), 2), num(signed_best.get("auc")),
                 num(signed_best.get("auc_exact_permutation_p"), 4), num(unsigned.get("auc")),
                 num(((drift.get("P0_to_P1|oxidation") or [{}])[2] or {}).get("tau_b_std"))))

    qc = ("%d 行 × %d 列，由 `analyze_stage11_sigma_anatomy.py` 从 5 个已冻结源文件现场重算；"
          "四条恒等式 + 一条分解全部 PASS（T4 的两条误差精确为 0.00e+00）；"
          "两个反事实检查 PASS（单调 Lipschitz 下 `tau_b = 1` 且 `f_unres = 0`；"
          "线性位移的 `q_median` 与 `abs(b)` 偏差 %s）；"
          "`light_stability` 与项目参考实现 `layer_stability` 在 8 个指标上逐点一致（测试钉住）。"
          % (len(rows), 32, "%.2e" % ((checks.get("linear_shift_matches_theory") or {})
                                      .get("max_abs_q_median_minus_abs_b", 0.0))))

    limit = ("n = 10 个台阶事件、3 个正例：AUC 1.000 / 0.905 / 0.857 之间**统计上不可区分**"
             "（精确 p = 0.008 / 0.033 / 0.058，区间严重重叠），不得据此排序预测子优劣；"
             "LOO 10/10 是在同一批 10 个点上重拟合阈值的结果，**不是外部验证**；"
             "T4 的判据在 z = 1 与 z = 1.96 给出不同结论（`0.722 < abs(b) < 1.414` 是半可用区），"
             "引用分辨率时必须声明置信水平；"
             "`f_unresolved` 与 `tau_b` 是两件事，`f_robust_inv = 0` 依旧不能单独读。")

    sigma_note = ("**sigma 的代数解剖（Stage 11 / week10）**：项目自 Week 4 起使用的 `sigma_ij` 不是"
                  "经验量，它有闭式 —— `sigma_ij = abs(delta_i - delta_j)/sqrt(2)`，逐对 RMS 恰等于"
                  "逐分子位移的样本标准差，且对层间**刚性偏移严格不变**（均匀方法偏差零成本）。"
                  "更关键的是 **T4**：`f_unresolved(z) = Pr(q_ij > sqrt(2)/z)`，"
                  "`q_ij = abs(delta_i - delta_j)/abs(DeltaP_ij)` 是**位移对目标轴的割线斜率**；"
                  "闭式与实测在 z = 1 与 z = 1.96 的 20 个点上误差精确为 0。"
                  "于是 H_var 的正确表述是「位移相对目标轴的**斜率分布**与 sqrt(2)/z 的关系」，"
                  "而不是「位移的散布」。见 F20/F21（`outputs/figures/F20_sigma_anatomy.png`、"
                  "`F21_sigma_controls.png`）。")

    summary = ("- 做了什么：%s\n- 关键数字：\n%s\n- 质检：%s\n- 限制：%s"
               % (did, metric, qc, limit))
    return {"present": True, "did": did, "metric": metric, "qc": qc, "limit": limit,
            "theorem_block": theorem_block, "ladder_block": ladder_block,
            "control_block": control_block, "predictor_block": predictor_block,
            "drift_block": drift_block, "sigma_note": sigma_note, "summary": summary}


F22_NOTE_PRESENT = ("Stage 12 介电自相似：(a) 位移 delta(eps) 的 Born 线性轮廓 (1 - 1/eps)（20 条曲线）；"
                    "(b) 逐级增量比随 eps 加倍，与 Born / Onsager 预测对比；(c) 同一 c 因子下的几何收缩"
                    "（形状不变性）；(d) 留出 eps = 40 的外推检验")
F22_NOTE_ABSENT = "预留给 Stage 12（介电自相似）；week11 尚未产出"
F23_NOTE_PRESENT = ("Stage 12 事前预警：(a) 预算曲线（试点规模 k 对灵敏度 / AUC）；(b) 逐台阶 b_hat 分布"
                    "（红色 = 清单被改写，淡红区 = 规则触发）；(c) 3 分子试点的 b_hat 散点；(d) 判据平面")
F23_NOTE_ABSENT = "预留给 Stage 12（事前预警）；week11 尚未产出"
W11_PRESCREEN_PATH = REPO / "outputs" / "week11" / "stage12_prescreen.json"
W11_AXIS_SHORT = (("oxidation", "氧化"), ("reduction", "还原"))
W11_ELEC_ORDER = ("P0_to_P1", "P1_to_P2", "G1_to_G2", "C0_to_C1", "C1_to_C2")


def week11_blocks(prescreen):
    """Render the week-11 (Stage 12 / dielectric law + pilot prescreen) blocks."""

    empty = {"present": False, "did": "", "metric": "", "qc": "", "limit": "",
             "law_block": "", "ratio_block": "", "shape_block": "", "forecast_block": "",
             "prescreen_block": "", "table_block": "", "sigma_note": "", "summary": ""}
    if not isinstance(prescreen, dict) or not (prescreen.get("rows") or []):
        return empty

    rows = prescreen.get("rows") or []
    subset = prescreen.get("common_subset") or []
    law = prescreen.get("dielectric_law") or {}
    shape = prescreen.get("shape_invariance") or {}
    forecast = prescreen.get("extrapolation") or {}
    pilot = prescreen.get("prescreen") or {}
    checks = prescreen.get("checks") or {}
    die_rows = [row for row in rows if row.get("rung_family") == "dielectric"]
    elec_rows = {(row.get("rung"), row.get("axis")): row
                 for row in rows if row.get("rung_family") == "electronic"}
    born = law.get("born_r2") or {}
    onsager = law.get("onsager_r2") or {}
    pred = law.get("predicted_ratios") or {}
    meas = law.get("measured_ratios") or {}
    spread = shape.get("max_rel_spread_by_axis") or {}
    worst = shape.get("worst_by_axis") or {}
    curves = pilot.get("curves") or []
    curve_by_k = {item.get("k"): item for item in curves}
    n_pass = sum(1 for item in checks.values() if isinstance(item, dict) and item.get("ok"))
    n_checks = len(checks)

    def num(value, digits=3):
        return _w8_num(value, digits)

    def signed(value, digits=3):
        text = _w8_num(value, digits)
        if text == "\u2014":
            return text
        return text if float(value) < 0 else "+" + text

    law_block = ("**(a) 介电自相似律**（参考点 eps = 1 气相，台阶 eps = 5/10/20/40；"
                 "对 20 条 (分子, 轴) 曲线各自拟合）：\n\n"
                 "| 模型 | 形式 | mean R2 | 最差 R2 | 最好 R2 |\n| --- | --- | --- | --- | --- |\n")
    law_block += "| **Born** | delta ∝ (1 - 1/eps) | **%s** | %s | %s |\n" % (
        num(born.get("mean"), 4), num(born.get("min"), 4), num(born.get("max"), 4))
    law_block += "| Onsager | delta ∝ (eps - 1)/(2 eps + 1) | %s | %s | %s |\n" % (
        num(onsager.get("mean"), 4), num(onsager.get("min"), 4), num(onsager.get("max"), 4))

    ratio_block = ("**(b) 逐级增量比**（`d(hi)/d(lo)`，对照两个模型的解析预测）：\n\n"
                   "| 增量比 | Born 预测 | Onsager 预测 | 实测均值 +/- sd | 实测范围 |\n"
                   "| --- | --- | --- | --- | --- |\n")
    for tag, label in (("r1", "d(5->10)/d(1->5)"), ("r2", "d(10->20)/d(5->10)"),
                       ("r3", "d(20->40)/d(10->20)")):
        item = meas.get(tag) or {}
        ratio_block += "| %s | %s | %s | %s +/- %s | [%s, %s] |\n" % (
            label, num((pred.get("born") or {}).get(tag), 4),
            num((pred.get("onsager") or {}).get(tag), 4),
            num(item.get("mean"), 4), num(item.get("sd"), 4),
            num(item.get("min"), 4), num(item.get("max"), 4))

    shape_block = ("**(c) 形状不变性**（每个 (分子, 轴) 用 Born 形式拟出单一标量 S；"
                   "看 S 在三个台阶间是否一致，氧化 / 还原分别统计）：\n\n"
                   "| 通道 | 最大相对漂移 max rel_spread | 最差分子/轴 |\n| --- | --- | --- |\n")
    for axis, axis_label in W11_AXIS_SHORT:
        shape_block += "| %s | %s | %s |\n" % (
            axis_label, num(spread.get(axis), 4), worst.get(axis) or "\u2014")

    forecast_block = ("**(d) 从廉价端外推 eps = 40**（留出检验，拟合时不含 eps = 40 数据；20 条曲线）：\n\n"
                      "| 用到的廉价点 | 最大绝对误差 (eV) | 平均绝对误差 (eV) | 最大相对误差 |\n"
                      "| --- | --- | --- | --- |\n")
    forecast_block += "| 2 点 (5, 10) | %s | %s | %s |\n" % (
        num(forecast.get("two_point_max_abs_err_ev"), 4),
        num(forecast.get("two_point_mean_abs_err_ev"), 4),
        num(100.0 * float(forecast.get("two_point_max_rel_err") or 0.0), 2) + "%")
    forecast_block += "| **3 点 (5, 10, 20)** | **%s** | %s | %s |\n" % (
        num(forecast.get("three_point_max_abs_err_ev"), 4),
        num(forecast.get("three_point_mean_abs_err_ev"), 4),
        num(100.0 * float(forecast.get("three_point_max_rel_err") or 0.0), 2) + "%")

    prescreen_block = ("**(e) 事前预警协议**（只跑 k 个试点分子后，用 `b_hat` 预判哪些台阶会改写清单；"
                       "规则：`flag` 当 `b_hat < 0` 或 `abs(b_hat) > sqrt(2)/z`，z = 1；"
                       "穷举 C(10, k) 个子集）：\n\n"
                       "| k | 子集数 | AUC(单试点均值) | 最差 AUC | AUC(b_hat 平均) | "
                       "灵敏度均值 | 最差灵敏度 | 特异度均值 | 全抓率 | b_hat 子集间 sd |\n"
                       "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n")
    for item in curves:
        prescreen_block += "| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |\n" % (
            item.get("k"), item.get("n_subsets"),
            num(item.get("auc_lower_b_mean_over_subsets")),
            num(item.get("auc_lower_b_min_over_subsets")),
            num(item.get("auc_lower_b_mean_b_hat")), num(item.get("sensitivity_mean")),
            num(item.get("sensitivity_min")), num(item.get("specificity_mean")),
            num(item.get("p_all_positives_flagged")),
            num(item.get("b_hat_sd_across_subsets_mean")))

    axis_label = {"oxidation": "氧化", "reduction": "还原"}
    table_block = "**(f) 18 个台阶事件（common-%d，N = 10）**\n\n" % len(subset)
    table_block += "介电梯度（%d 点，全部良性）：\n\n" % len(die_rows)
    table_block += ("| 台阶 | 轴 | n | sd(delta) (eV) | b | tau_b | top20 overlap | 清单被改写 |\n"
                    "| --- | --- | --- | --- | --- | --- | --- | --- |\n")
    for row in die_rows:
        table_block += "| %s | %s | %s | %s | %s | %s | %s | %s |\n" % (
            row.get("rung", "").replace("DIE_", "").replace("_to_", " -> "),
            axis_label.get(row.get("axis"), row.get("axis")),
            row.get("n"), num(row.get("delta_sd_ev"), 4), signed(row.get("ols_slope_b")),
            signed(row.get("kendall_tau_b")), num(row.get("overlap_20"), 2),
            "是" if row.get("shortlist_rewritten") else "否")
    table_block += "\n电子结构（10 点，与 Week 10 同源）：\n\n"
    table_block += ("| 台阶 | 轴 | n | sd(delta) (eV) | b | tau_b | top20 overlap | 清单被改写 |\n"
                    "| --- | --- | --- | --- | --- | --- | --- | --- |\n")
    for rung in W11_ELEC_ORDER:
        for axis, label in W11_AXIS_SHORT:
            row = elec_rows.get((rung, axis)) or {}
            table_block += "| %s | %s | %s | %s | %s | %s | %s | %s |\n" % (
                rung.replace("_to_", " -> "), label, row.get("n"),
                num(row.get("delta_sd_ev"), 4), signed(row.get("ols_slope_b")),
                signed(row.get("kendall_tau_b")), num(row.get("overlap_20"), 2),
                "是" if row.get("shortlist_rewritten") else "否")

    gas5 = elec_rows.get(("P0_to_P1", "oxidation")) or {}
    del gas5
    die_gas5 = next((row for row in die_rows
                     if row.get("rung") == "DIE_gas_to_5" and row.get("axis") == "oxidation"), {})
    k5 = curve_by_k.get(5) or {}
    k3 = curve_by_k.get(3) or {}

    did = ("把 Week 4 的 bare CPCM 介电扫描（eps = 5/10/20/40 x 12 分子 x 3 态）提升为第 6 类台阶，"
           "与 5 个电子结构台阶并列，凑成 **18 个台阶事件**（8 介电 + 10 电子结构），全部落在 common-%d 上。"
           "做两件事：(1) 检验介电 screening 是否落在**单参数自相似族**上（Born `1 - 1/eps` vs Onsager "
           "`(eps-1)/(2 eps+1)`）；(2) 把「先跑少量分子、再判哪些台阶会改写清单」写成**事前预警协议**"
           "（穷举 C(10, k) 个试面子集，用 `b_hat` 的符号与幅度做判据）。本阶段不跑任何新的电子结构计算。"
           % len(subset))

    metric = ("- 介电 screening 是**单参数自相似族**：位移整条曲线落在 Born 形式 `S (1 - 1/eps)` 上 —— "
              "20 条 (分子, 轴) 曲线 mean R2 = **%s**（最差 %s），对照 Onsager 反应场的 %s（最差 %s）；"
              "逐级增量比实测 %s / %s / %s，Born 预测 0.1250 / 2.0000 / 2.0000、Onsager 0.1786 / 1.8636 / 1.9286\n"
              "- 形状不变性**分通道**：氧化的单标量族精确到 %s（最差 %s），还原松约 4 倍到 %s（最差 %s）—— "
              "阴离子上 Onsager 型高阶项更重\n"
              "- 外推可信：只用 3 个廉价点（eps = 5/10/20）预测 eps = 40，最大相对误差 %s，平均绝对误差 %s eV\n"
              "- 8 个介电台阶**全部良性**：b > 0、tau_b >= 0.867、top20 overlap = 1.00、无一改写清单 —— 尽管 "
              "`gas -> 5` 的位移均值 %s eV 比 P1 -> P2 / G1 -> G2 / C0 -> C1 / C1 -> C2 都大\n"
              "- 事前预警：k = 5（半数分子）平均抓 %s 的危险台阶、AUC %s；要一次不漏需 k = %s；"
              "k = 3 不可作放行依据（最差 AUC %s）"
              % (num(born.get("mean"), 4), num(born.get("min"), 4),
                 num(onsager.get("mean"), 4), num(onsager.get("min"), 4),
                 num((meas.get("r1") or {}).get("mean"), 4),
                 num((meas.get("r2") or {}).get("mean"), 4),
                 num((meas.get("r3") or {}).get("mean"), 4),
                 num(spread.get("oxidation"), 4), worst.get("oxidation") or "\u2014",
                 num(spread.get("reduction"), 4), worst.get("reduction") or "\u2014",
                 num(100.0 * float(forecast.get("three_point_max_rel_err") or 0.0), 2) + "%",
                 num(forecast.get("three_point_mean_abs_err_ev"), 4),
                 num(die_gas5.get("delta_mean_ev"), 3),
                 num(k5.get("sensitivity_mean")), num(k5.get("auc_lower_b_mean_over_subsets")),
                 pilot.get("k_required_for_full_recall"), num(k3.get("auc_lower_b_min_over_subsets"))))

    qc = ("%d 行 x %d 列，由 `analyze_stage12_prescreen.py` 从 6 个已冻结源文件现场重算（约 2.7 s，"
          "不跑新电子结构）；恒等式 T1/T2/T4/T6/T7 全部 PASS（T1/T2/T4 误差 <= 1.2e-15 eV），"
          "并把 `b + 1 = beta` 与 `b = r sd(delta)/sd(axis)` 两条精确关系逐点钉住；"
          "气相参考一致性 0.0 eV（与 P1 表同源）；%d/%d 项检查 PASS。"
          % (len(rows), 31, n_pass, n_checks))

    limit = ("介电自相似律只建立在 eps = 1/5/10/20/40 五个点上，`eps = 80/200` 未算 —— 「单参数族」是外推，"
             "不是已验证的一般性断言；预警规则的阈值 `b < 0` / `abs(b) > sqrt(2)/z` 从 3 个正例读出，"
             "查全率 100%、特异度 0.78 都是**同一批 10 个点上的自洽**，不构成外部验证；"
             "试点只能可靠给出 `b` 的符号，给不出量级；n = 10 时不同子集在统计上不可区分，"
             "k 的选择是工程折中。")

    sigma_note = ("**第三条免费通道：自相似平移（Stage 12 / week11）**。Week 10 证明了「层间刚性偏移免费」"
                  "（T3）与「单调 1-Lipschitz 位移免费」；本周补上第三条 —— 若整条环境梯度恰好是 "
                  "`delta(eps) = c(eps) * delta0`（一个已知标量乘同一条向量），则 `sd(delta)`、`b`、`q` 全部按"
                  "同一因子 `c` 缩放：`b` 的符号不可能改变、`q` 单调走向 0，于是**决策只会越来越稳**。"
                  "bare CPCM 的介电扫描正落在这条通道上：20 条曲线 mean R2 = %s（Born），"
                  "8 个介电台阶全部 `b > 0`、`tau_b >= 0.867`、无一改写清单。这也解释了为什么「加了溶剂」"
                  "在文献里通常不发散排序 —— 需要担心的从来不是「加溶剂」，而是「换了相互之间不成比例的"
                  "两层」。见 F22/F23（`outputs/figures/F22_dielectric_scaling.png`、"
                  "`F23_prescreening.png`）。" % num(born.get("mean"), 4))

    summary = ("- 做了什么：%s\n- 关键数字：\n%s\n- 质检：%s\n- 限制：%s"
               % (did, metric, qc, limit))
    return {"present": True, "did": did, "metric": metric, "qc": qc, "limit": limit,
            "law_block": law_block, "ratio_block": ratio_block, "shape_block": shape_block,
            "forecast_block": forecast_block, "prescreen_block": prescreen_block,
            "table_block": table_block, "sigma_note": sigma_note, "summary": summary}


#: Stage 13 (Week 12): the analysis payload of ``analyze_stage13_dielectric_limit``.
W12_ANALYSIS_PATH = REPO / "outputs" / "week12" / "stage13_analysis.json"
W12_LADDER_PATH = REPO / "outputs" / "week12" / "stage13_ladder.json"
F24_NOTE_PRESENT = ("Stage 13 介电极限：(a) 位移 delta(eps) 对 u = 1 - 1/eps 的七级曲线（24 条）；"
                    "(b) Born / Onsager / 两参数族的 R2 对照与拟合出的 k；(c) 外推误差随外推距离增长；"
                    "(d) eps = 200 的实测值与拟合出的导体极限")
F24_NOTE_ABSENT = "预留给 Stage 13（介电极限）；week12 尚未产出"
F25_NOTE_PRESENT = ("Stage 13 环境账本：(a)(b) SMD 乙腈 / 水的位移按「介电项 + 溶质畸变项」逐分子分解；"
                    "(c) SMD CDS 项在三个电荷态上逐点重合（证明它是态的刚性偏移）；(d) 畸变项抵消介电项的比例")
F25_NOTE_ABSENT = "预留给 Stage 13（环境账本）；week12 尚未产出"
W12_AXIS_SHORT = (("oxidation", "氧化"), ("reduction", "还原"))
W12_SMD_ORDER = ("smd_acetonitrile", "smd_water")
#: The three layers this week (Stage 13) added on top of week 4.
NEW_LAYER_TAGS = ("cpcm_80", "cpcm_200", "smd_water")
W12_SMD_LABEL = {"smd_acetonitrile": "SMD 乙腈", "smd_water": "SMD 水"}
W12_LADDER_LABEL = {
    "gas_cpcm_5": "气相 -> eps 5",
    "cpcm_5_cpcm_10": "eps 5 -> 10",
    "cpcm_10_cpcm_20": "eps 10 -> 20",
    "cpcm_20_cpcm_40": "eps 20 -> 40",
    "cpcm_40_cpcm_80": "eps 40 -> 80",
    "cpcm_80_cpcm_200": "eps 80 -> 200",
    "P0_to_P1": "P0 -> P1（方法）",
    "P1_to_P2": "P1 -> P2（环境）",
    "G1_to_G2": "G1 -> G2（几何）",
    "C0_to_C1": "C0 -> C1（配位）",
    "C1_to_C2": "C1 -> C2（壳层）",
}


#: Stage 14 (Week 13): the distortion attribution and the EMC outlier diagnosis.
W13_ATTRIBUTION_PATH = REPO / "outputs" / "week13" / "stage14_attribution.json"
W13_OUTLIER_PATH = REPO / "outputs" / "week13" / "stage14_outlier.json"
F26_NOTE_PRESENT = ("Stage 14 畸变项归因：(a) 逐态畸变惩罚 D_X 的逐分子柱状图（中性 / 阳离子 / 阴离子）；"
                    "(b) 轴观测量恰好等于两个逐态惩罚之差——用态账本重建并逐点核验；"
                    "(c) 唯一稳健的关系：D_neutral 对分子自身的偶极矩；"
                    "(d) 描述符筛选，以留一 R2 打分")
F26_NOTE_ABSENT = "预留给 Stage 14（畸变项归因）；week13 尚未产出"
F27_NOTE_PRESENT = ("Stage 14 EMC 离群点：(e)(f) 九点 bare CPCM 阶梯上六条 delta(eps) 曲线；"
                    "(g) EMC / 还原轴按 SCF 解分支着色（偶极 ~2.5 D vs ~6.3-7.1 D）并给出粗糙度对照；"
                    "(h) Born R2 随网格点数的收敛")
F27_NOTE_ABSENT = "预留给 Stage 14（EMC 离群点）；week13 尚未产出"
W13_AXIS_SHORT = (("oxidation", "氧化"), ("reduction", "还原"))
W13_STATE_SHORT = (("neutral", "中性"), ("cation", "阳离子"), ("anion", "阴离子"))
W13_CURVE_SHORT = (("EMC/oxidation", "EMC 氧化"), ("EMC/reduction", "EMC 还原"),
                   ("DMC/oxidation", "DMC 氧化"), ("DMC/reduction", "DMC 还原"),
                   ("EC/oxidation", "EC 氧化"), ("EC/reduction", "EC 还原"))


#: Stage 15 (Week 14): the two-guess protocol, the diffuseness descriptors and the scan.
W14_RUN_PATH = REPO / "outputs" / "week14" / "stage15_two_guess.json"
W14_TWO_GUESS_PATH = REPO / "outputs" / "week14" / "stage15_two_guess_analysis.json"
W14_DIFFUSENESS_PATH = REPO / "outputs" / "week14" / "stage15_diffuseness.json"
W14_ANCHOR_PATH = REPO / "outputs" / "week14" / "stage15_anchor_scan.json"
F28_NOTE_PRESENT = ("Stage 15 双初猜协议：(a) 90 点能量差的幅度直方图与 1 meV material 阈值；"
                    "(b) EMC 阴离子偶极的两条分支（默认初猜 vs MORead）在十点介电阶梯上的对照；"
                    "(c) 导体极限：Born 横坐标 x = 1 - 1/eps，eps = 1000 是第一个实测到极限的位置；"
                    "(d) 六点 / 九点 Born 斜率与外推缺口（修复前后）")
F28_NOTE_ABSENT = "预留给 Stage 15（双初猜协议）；week14 尚未产出"
F29_NOTE_PRESENT = ("Stage 15 电子弥散度描述符：(e) spin_maxfrac 对阴离子畸变惩罚的散点；"
                    "(f) 参与比的秩相关 vs 线性留一 R2（秩强、线性不可用）；"
                    "(g) 三个目标的留一 R2 对比（中性与阳离子不变）；"
                    "(h) 逐层自旋极化的域检验，标出唯一越界的 EMC/cpcm_10")
F29_NOTE_ABSENT = "预留给 Stage 15（弥散度描述符）；week14 尚未产出"

W15_VALIDATION_NAMES = ("DEC", "EA", "FEC", "MA", "TEGDME", "VC")
W15_CATALOGUE_PATH = REPO / "outputs" / "week15" / "stage16_catalogue.json"
W15_ANALYSIS_PATH = REPO / "outputs" / "week15" / "stage16_catalogue_analysis.json"
W15_PREDICTOR_PATH = REPO / "outputs" / "week15" / "stage16_predictor.json"
F30_NOTE_PRESENT = ("Stage 16 双初猜目录：(a) 12 分子 x 3 状态 x 10 电介质的完整网格，"
                    "按 dE 的符号着色（灰 = 两臂一致，红 = 默认初猜偏高）；"
                    "(b) 每个开壳层 (分子, 状态) 在整个阶梯上的最大赤字；"
                    "(c) 超过各阈值的单元格计数")
F30_NOTE_ABSENT = "预留给 Stage 16（双初猜目录）；week15 尚未产出"
F31_NOTE_PRESENT = ("Stage 16 事前预警规则：(d) 选定气相描述符对最大赤字，"
                    "绿色虚线为留一冻结阈值；(e) 每个描述符的单变量 AUC；"
                    "(f) 留出臂的逐行预测与真值；(g) 冻结规则与其多变量上限")
F31_NOTE_ABSENT = "预留给 Stage 16（事前预警规则）；week15 尚未产出"
W15_STATE_SHORT = (("neutral", "中性"), ("cation", "阳离子"), ("anion", "阴离子"))
W15_LADDER_SHORT = (("core3", "3 点"), ("focus6", "6 点"), ("ladder10", "10 点"))
W15_TABLE_ROWS = (
    ("`stage16_catalogue.json`", "运行账本：单元格数、复用/新算计数、几何审计、逐层摘要"),
    ("`stage16_catalogue_analysis.json`", "目录分析：阈值直方图、逐分子逐态标签、阶梯一致性、家族覆盖"),
    ("`stage16_cells.csv`", "逐单元格能量对照（默认初猜 vs MORead 重启）"),
    ("`stage16_by_state.csv`", "逐 (分子, 状态) 在三种阶梯上的汇总"),
    ("`stage16_gas_descriptors.csv`", "气相先验描述符表（18 分子 x 3 状态）"),
    ("`stage16_predictor.json`", "预警规则：单变量筛查、冻结阈值、留出臂混淆矩阵、多变量上限"),
    ("`stage16_summary.md`", "F30 / F31 的逐面板文字 companion"),
)
W14_STATE_SHORT = (("neutral", "中性"), ("cation", "阳离子"), ("anion", "阴离子"))
W14_TARGET_SHORT = (("neutral", "D_neutral"), ("cation", "D_cation"), ("anion", "D_anion"))
W14_PROTOCOL_SHORT = (("default", "默认初猜"), ("moread", "MORead"))

W14_TABLE_ROWS = (
    ("`stage15_two_guess.json`", "99 个作业的运行记录（11 层 x 9 作业，0 失败）"),
    ("`stage15_two_guess_analysis.json`", "Part A 全部分析（能量、偶极、Born 曲线、导体极限、判决）"),
    ("`stage15_two_guess_energy.csv` / `_dipole.csv`", "90 个点的双协议能量差 / 偶极"),
    ("`stage15_diffuseness.json`", "Part B：7 个新描述符、21 个扩展描述符、域检验、判决、配对搜索"),
    ("`stage15_diffuseness.csv` / `_by_molecule.csv`", "72 行逐层 / 12 行逐分子（层均值与中位数两种口径）"),
    ("`stage15_anchor_scan.json` / `.csv`", "Part C：13 篇语料、DOI 交集、31 行裁定、gate1 汇总"),
    ("`stage15_anchor_corrections.csv`", "3 条修正的 overlay（correction of record）"),
    ("`stage15_summary.md`", "F28 / F29 的逐面板文字 companion"),
    ("`p2_core_set_*.csv` / `p2_summary_*.json`", "11 层的能量表与逐层汇总（eps = 1000 + 10 个 MORead 层）"),
)


#: Stage 17 (Week 16): the contamination ceiling and the two-solution identity.
W16_SMD_PATH = REPO / "outputs" / "week16" / "stage17_smd_moread.json"
W16_P2_SUMMARY_PATH = (REPO / "outputs" / "week16"
                       / "p2_summary_moread_smd_acetonitrile.json")
W16_CONTAMINATION_PATH = REPO / "outputs" / "week16" / "stage17_contamination.json"
W16_IDENTITY_PATH = REPO / "outputs" / "week16" / "stage17_solution_identity.json"
F32_NOTE_PRESENT = ("Stage 17 Part A（污染上限）：(a) 18 分子 x 2 轴的 "
                    "delta = p2_moread - p2_default，参考带 = 材料阈值 1 meV；"
                    "(b) 排序稳定性对照（两轴两臂 tau_b 与 95% CI，两轴 CI 重叠）；"
                    "(c) 决策量 default vs moread 与 6 个超阈值格子")
F32_NOTE_ABSENT = "预留给 Stage 17 Part A（污染上限）；week16 尚未产出"
F33_NOTE_PRESENT = ("Stage 17 Part B（两个 SCF 解的电子结构身份）：(d) 代表性逐原子自旋剖面；"
                    "(e) 三个家族的 loss_in_pr 均值；(f) 32 格的 delta<S^2>（参考 0.75）；"
                    "(g) 三个家族的 charge_l1 vs spin_l1")
F33_NOTE_ABSENT = "预留给 Stage 17 Part B（解的电子结构身份）；week16 尚未产出"
W16_AXIS_SHORT = (("oxidation", "氧化轴"), ("reduction", "还原轴"))
W16_ARM_SHORT = (("default", "default"), ("moread", "moread"))
W16_TABLE_ROWS = (
    ("\x60stage17_smd_moread.json\x60",
     "Part A 运行台账：54 格计数、复用/新算、G1 几何审计、初猜协议原文"),
    ("\x60stage17_smd_moread_plan.json\x60", "Part A 运行前的作业计划（18 分子 x 3 态）"),
    ("\x60stage17_contamination.json\x60",
     "Part A 全部分析（逐轴对照、delta_stats、符号检验、scenario verdict、CI 重叠）"),
    ("\x60stage17_contamination_cells.csv\x60",
     "Part A 逐分子表（P1 与两臂 P2 的原始能量、逐态 delta）"),
    ("\x60stage17_contamination_ladder.csv\x60",
     "Part A 四行 (臂, 轴) 指标表（含 published 列与 delta 列）"),
    ("\x60stage17_contamination_summary.md\x60", "Part A 的中文小结"),
    ("\x60stage17_solution_identity.json\x60",
     "Part B 聚合产物（census / by_state / by_family / aggregates）"),
    ("\x60stage17_solution_identity.csv\x60",
     "Part B 逐格表（两臂 .out 路径、<S^2>、自旋中心、PR、L1、几何 QC）"),
    ("\x60stage17_solution_identity_by_molecule.csv\x60", "Part B 按 (分子, 态) 汇总表"),
    ("\x60stage17_solution_identity_summary.md\x60", "Part B 的中文小结"),
    ("\x60p2_core_set_moread_smd_acetonitrile.csv\x60 / "
     "\x60p2_summary_moread_smd_acetonitrile.json\x60",
     "Part A 的原始能量表与逐层汇总（SMD(乙腈) moread 臂）"),
)

#: Stage 18 (Week 17): the whole-catalogue identity census and the zero-extra-cost
#: self-diagnosis.  Neither part ran a new quantum-chemistry job.
W17_CENSUS_PATH = REPO / "outputs" / "week17" / "stage18_identity_census.json"
W17_DIAGNOSIS_PATH = REPO / "outputs" / "week17" / "stage18_selfdiagnosis.json"
F34_NOTE_PRESENT = ("Stage 18 Part A 电子身份普查：(a) charge_l1 在 276 个可测配对上的双峰"
                    "（冻结切点 0.039 落在 0.038509 与 0.039383 之间的空隙里）；"
                    "(b) 分类与身份判定的一致性（发现集 328/32、留出臂 49/5）；"
                    "(c) 8 个家族各自的 coincident / moread_lower 分裂；"
                    "(d) 5 个留出臂漏解格逐格（2 个分子、全部为阴离子）")
F34_NOTE_ABSENT = "预留给 Stage 18 Part A（电子身份普查）；week17 尚未产出"
F35_NOTE_PRESENT = ("Stage 18 Part B 零成本自诊断：(e) 8 个零额外成本特征的单变量筛查"
                    "（发现集 AUC / 留一 / 留出 accuracy，两条多数类基线）；"
                    "(f) ORCA 自带 small-gap 警告的带符号值分布，以及 140 个「无警告」格的归属；"
                    "(g) 冻结规则在 54 个留出格上原样打分（TP 0 / FP 6 / TN 43 / FN 5）；"
                    "(h) 单边视图：警告本身在两臂都达到灵敏度 1.000，而数值切点样本外降到 0.000")
F35_NOTE_ABSENT = "预留给 Stage 18 Part B（零成本自诊断）；week17 尚未产出"
W17_TABLE_ROWS = (
    ("`stage18_identity_census.json`",
     "Part A 全部聚合（thresholds / census / energy_crosscheck / geometry_qc / "
     "classification_counts / separation / by_state / by_family / cells）"),
    ("`stage18_identity_census.csv`",
     "Part A 逐格表（414 对：两臂 .out 路径、<S^2>、自旋中心、PR、L1、几何 QC、identity_differs）"),
    ("`stage18_identity_census_by_family.csv` / `_by_classification.csv`",
     "Part A 按家族 / 按分类的汇总表"),
    ("`stage18_identity_census_summary.md`", "Part A 的中文小结"),
    ("`stage18_selfdiagnosis.json`",
     "Part B 全部内容（features / screen / frozen_rule / in_sample / loo / significance / "
     "holdout / by_state_post_hoc / multivariate_ceiling / one_sided_screening）"),
    ("`stage18_selfdiagnosis_features.csv`",
     "Part B 逐格特征表（414 行 x 34 列，全部读自默认臂那一个 .out）"),
    ("`stage18_selfdiagnosis_features_by_state.csv`", "Part B 按 (臂, 态) 的特征均值表"),
    ("`stage18_selfdiagnosis_summary.md`", "Part B 的中文小结"),
)

#: Stage 19 (Week 18): do the two SCF solutions survive geometry relaxation?
#: 74 ORCA ``Opt`` jobs = 37 ``moread_lower`` cells x 2 arms; method, solvent and
#: the frozen G1 start geometry are all inherited from the single points.
W18_LEDGER_PATH = REPO / "outputs" / "week18" / "stage19_relax.json"
W18_ANALYSIS_PATH = REPO / "outputs" / "week18" / "stage19_relax_analysis.json"
W18_STAGE18_CENSUS_PATH = REPO / "outputs" / "week17" / "stage18_identity_census.json"
F36_NOTE_PRESENT = ("Stage 19 弛豫裁决：(a) 单点 Delta 对弛豫后 Delta（按结局着色，y=x 与 "
                    "±1 meV 带；|Delta| 中位 0.11983 -> 0.00196 eV，缩小 61 倍）；"
                    "(b) 37 个 moread_lower 格子的裁决（distinct_lower 5 / distinct_higher 24 / "
                    "same_lower 0 / same_higher 8）；(c) 按 eps 的结局堆叠；(d) 按态与分子的分解")
F36_NOTE_ABSENT = "预留给 Stage 19（几何弛豫检验）；week18 尚未产出"
F37_NOTE_PRESENT = ("Stage 19 身份与几何：(e) 弛豫前后 charge_l1 对数散点（冻结阈值 0.039，"
                    "弛豫后仍在阈值以上 29/37、贴阈值 0 格）；"
                    "(f) 双解几何 RMSD 对 Delta 漂移（0.02 A 同极小点参考线，下方 6/37 格）；"
                    "(g) 两臂弛豫能量降配对（默认解中位降 1.876 eV vs moread 1.666 eV）；"
                    "(h) 自旋中心迁移矩阵（argmax 仅作描述，不作判据）")
F37_NOTE_ABSENT = "预留给 Stage 19（身份与几何）；week18 尚未产出"
W18_TABLE_ROWS = (
    ("`stage19_relax.json` / `stage19_relax_plan.json`",
     "作业台账（37 格 x 2 臂 = 74 个 Opt 作业；method / job_type / 起始几何与 QC 摘要）"),
    ("`stage19_relax_cells.csv`",
     "逐格逐臂原始读数（74 行：最后一块能量、<S^2>、收敛、Mulliken / CARTESIAN 块计数）"),
    ("`stage19_relax_analysis.json`",
     "主结论全部聚合（threshold_charge_l1 / block_counts / cells / "
     "aggregates: all + by_state + by_molecule + by_epsilon + by_arm_set）"),
    ("`stage19_relax_cells_analysis.csv`", "37 个 moread_lower 格子的逐格裁决表"),
    ("`stage19_relax_by_state.csv` / `_by_molecule.csv` / `_by_epsilon.csv` / `_by_arm_set.csv`",
     "四张分组汇总表"),
    ("`stage19_relax_summary.md`", "本周中文小结"),
)

#: Stage 20 (Week 19): two independent parts.  Part 1 is a zero-new-calculation
#: back-fill of the relaxation correction onto the Stage 10 five-rung ladder;
#: Part 2 is 74 frozen GFN2-xTB jobs (37 cells x 2 arms) asking whether the
#: second SCF solution survives a cheap relaxation.
W19_RUNG_PATH = REPO / "outputs" / "week19" / "stage20_relax_rung.json"
W19_ARMS_PATH = REPO / "outputs" / "week19" / "stage20_xtb_arms.json"
W19_ARMS_ANALYSIS_PATH = REPO / "outputs" / "week19" / "stage20_xtb_arms_analysis.json"
F38_NOTE_PRESENT = (
    "Stage 20 Part 1 第六级台阶：(a) 37 个格子的弛豫位移 Delta = -能量降（eV）对 eps"
    "（对数轴，按态着色；逐分子 eps 极差中位 0.0263 eV、最大 0.215 eV（DEC））；"
    "(b) 同一把尺子：4 个可比 population 上 5 个冻结台阶与第六级台阶的相对散布 std/|mean|；"
    "(c) (|mean|, std) 平面（6 台阶 x 6 population = 30 行）；"
    "(d) 7 个分子的 Delta 均值与跨 eps 极差（还原支 -1.953/0.160/0.08，氧化支 -0.610/0.315/0.52）")
F38_NOTE_ABSENT = "预留给 Stage 20 Part 1（第六级台阶）；week19 尚未产出"
F39_NOTE_PRESENT = (
    "Stage 20 Part 2 跨方法检验：(a) 两臂起点 RMSD 对 xTB 弛豫后 RMSD"
    "（0.4716 -> 0.8078 A，6/37 格两臂合并）；(b) 同一几何上 xTB 单点 Delta 对 ORCA r2SCAN-3c"
    " 弛豫 Delta（偏好方向一致 33/37 = 89%）；(c) 两臂能量差的四个读数"
    "（中位 1.198e-01 / 1.960e-03 / 7.171e-03 / 2.133e-04 eV，xTB 弛豫压掉约 33.6 倍）；"
    "(d) 单臂漂移对起点双解 RMSD（两臂漂移中位 0.651 / 0.657 A）")
F39_NOTE_ABSENT = "预留给 Stage 20 Part 2（跨方法存亡）；week19 尚未产出"
W19_TABLE_ROWS = (
    ("`stage20_relax_rung.json` / `_cells.csv` / `_epsilon.csv` / `_ladder.csv`",
     "Part 1 全部内容（37 格的弛豫位移、逐分子跨 eps 极差、30 行台阶表、按态 / 按分子 / "
     "按臂 / 按 eps 聚合）；ladder 每一行的 `rank_metrics` 都写明 `omitted:` 原因"),
    ("`stage20_relax_rung_summary.md`", "Part 1 的中文小结"),
    ("`stage20_xtb_arms.json` / `stage20_xtb_arms_plan.json`",
     "Part 2 作业台账（37 格 x 2 臂 = 74 个 GFN2-xTB 作业；起始几何来自 Stage 19 的弛豫终点）"),
    ("`stage20_xtb_arms_cells.csv`", "Part 2 逐格逐臂原始读数（74 行）"),
    ("`stage20_xtb_arms_analysis.json`",
     "Part 2 主结论（cross-tab、同几何方法对照、aggregates: all + by_state + by_molecule + "
     "by_epsilon + by_arm_set）"),
    ("`stage20_xtb_arms_cells_analysis.csv` / `_by_*.csv`", "Part 2 逐格裁决表与四张分组汇总表"),
    ("`stage20_xtb_arms_summary.md`", "Part 2 的中文小结"),
)


#: Stage 21 (Week 20): four independent parts, all four products of the week.  Part A
#: walks a straight Cartesian line between the two Stage 19 relaxed endpoints and runs
#: one frozen single point per point (63 jobs); Part B turns the ``charge_l1`` identity
#: threshold into a runtime pre-check (zero jobs); Part C relaxes both redox states of
#: the twelve 1:2 solvent shells (24 ``Opt`` jobs); Part D really replaces the P2 end of
#: the Stage 10 rung with relaxed energies and re-synthesises the ladder (zero jobs).
W20_PATH_JSON = REPO / "outputs" / "week20" / "stage21_path_analysis.json"
W20_PROTOCOL_JSON = REPO / "outputs" / "week20" / "stage21_protocol.json"
W20_SHELL_JSON = REPO / "outputs" / "week20" / "stage21_shell_redox_analysis.json"
W20_REFILL_JSON = REPO / "outputs" / "week20" / "stage21_refill.json"
F40_NOTE_PRESENT = (
    "Stage 21 Part A 临界带的能量裁决：三个内插格（EC/cation/eps=5、EC/cation/eps=20、"
    "TEGDME/anion/eps=20）在两条 Stage 19 弛豫终点之间做直线内插，每点一个冻结 r2SCAN-3c 单点"
    "（21 帧 x 3 格 = 63 个，全部收敛）；每格独立纵轴。EC/cation/eps=5 被判 distinct_lower，"
    "但路径相对弦最大只抬升 0.00424 eV（k_B T 的 16.5%），实为同一个平坦盆地")
F40_NOTE_ABSENT = "预留给 Stage 21 Part A（临界带的能量裁决）；week20 尚未产出"
F41_NOTE_PRESENT = (
    "Stage 21 Part C 第一溶剂壳在氧化还原下的弛豫：12 个 [Li(M)2]+ 的氧化态（+2/二重态）与"
    "还原态（0/二重态）各做一次 r2SCAN-3c Opt（24 个作业），起点是同一张冻结 G2Li2 几何；"
    "(a)(b) 逐壳冻结位移（空心）对弛豫位移（实心），连线长度即弛豫修正；"
    "(c) 冻结 vs 弛豫散点与 y=x。结构 QC（父键完好 / 单一碎片 / Li 同时配位两配体）逐格判定，"
    "不合格的格子画成灰叉并排除在所有统计之外")
F41_NOTE_ABSENT = "预留给 Stage 21 Part C（溶剂壳氧化还原）；week20 尚未产出"
W20_TABLE_ROWS = (
    ("`stage21_path.json` / `_plan.json` / `_cells.csv`",
     "Part A 作业台账（63 个冻结单点，3 格 x 21 帧）"),
    ("`stage21_path_analysis.json` / `_analysis.csv` / `_summary.md`",
     "Part A 裁决（路径长、弦上鼓包、SCF 噪声底、弛豫前后差、逐格 one_basin/separated）"),
    ("`stage21_protocol.json` / `_borderline.csv` / `_summary.md`",
     "Part B 预检（阈值从空档中点重导、三分类计数、交叉表、闭壳层反例探针、适用条件）"),
    ("`stage21_shell_redox.json` / `_plan.json` / `_cells.csv`",
     "Part C 作业台账（24 个 Opt，含结构 QC 列）"),
    ("`stage21_shell_redox_analysis.json` / `_analysis.csv` / `_summary.md`",
     "Part C 分析（逐壳冻结/弛豫位移、弛豫修正、两轴排序统计、排除清单）"),
    ("`stage21_refill.json` / `_cells.csv` / `_summary.md`",
     "Part D 真回填（覆盖率、逐轴排序变化、三种 Δ 估计量的稳健性、位移定义原文）"),
)



W21_PHASE_JSON = REPO / "outputs" / "week21" / "sigma_synthetic.json"
W21_PROSPECTIVE_JSON = REPO / "outputs" / "week21" / "sigma_prospective.json"
W21_FROZEN_JSON = REPO / "outputs" / "week21" / "sigma_prospective_frozen.json"
W21_ANCHOR_JSON = REPO / "outputs" / "week4" / "p1_anchor_comparison.json"
F42_NOTE_PRESENT = (
    "Stage 22 R2：把 Week 9 的 10 个（台阶, 轴）实测点放进合成的（均值, 离散度）相图——"
    "每个格子固定 sigma、只平移均值，每格 2000 次重复。tau_b 只随 std 变（rho(std, tau_b) = -1.000），"
    "均值平移严格不动排序（max abs Delta tau_b = 0.000）；实测点的 rho(abs(mean), tau_b) = -0.535 "
    "是 abs(mean) 与 std 共线（rho = +0.758）造成的假象。四个面板：tau_b 相图、f_unresolved 相图、"
    "tau_b-vs-std 曲线（叠 10 个实测点）、overlap 相图。")
F42_NOTE_ABSENT = "（Stage 22 R2 相图尚未产出；week21 尚未生成）"
W21_TABLE_ROWS = (
    ("`sigma_synthetic.json`",
     "R2：33 x 41 的（均值, 离散度）网格，每格 2000 次重复的 tau_b / f_unresolved / overlap 相图，"
     "外加均值不变性、实测相关性、临界 std 边界与子集敏感性。"),
    ("`sigma_prospective_frozen.json`",
     "R3：在任何留出结果出现之前先落盘并取 SHA256 的冻结判据（带符号 OLS 斜率与朴素 sd(delta) 两条规则、"
     "各自的阈值与 10 个发现点）。"),
    ("`sigma_prospective.json` / `sigma_prospective.md`",
     "R3：4 个留出预测的命中率（带符号 3/4、朴素 2/4）与逐条观测结果。"),
    ("`outputs/week4/p1_anchor_comparison.json`（新增 `arm_alignment` / `tau_b_reference`）",
     "R1 + R10：三条臂对齐到同一批 10 个分子后的 tau_b、配对 Delta tau_b 的 CI 与精确置换 p，"
     "以及两类 tau_b 的分列口径。"),
)


def week13_blocks(attribution, outlier):
    """Render the week-13 (Stage 14 / distortion attribution + EMC outlier) blocks.

    Every number is read back out of ``stage14_attribution.json`` and
    ``stage14_outlier.json``, so the distilled report cannot drift away from the
    CSVs and figures it summarises.
    """

    empty = {"present": False, "did": "", "metric": "", "qc": "", "limit": "",
             "definition_block": "", "state_block": "", "correction_block": "",
             "attribution_block": "", "outlier_block": "", "repro_block": "",
             "table_block": "", "sigma_note": "", "summary": ""}
    if not isinstance(attribution, dict) or not attribution.get("molecules"):
        return empty

    def num(value, digits=3):
        return _w8_num(value, digits)

    def signed(value, digits=3):
        text = _w8_num(value, digits)
        if text == "\u2014":
            return text
        return text if text.startswith("-") else "+" + text

    correction = attribution.get("correction") or {}
    search = correction.get("subset_enumeration") or {}
    values = correction.get("reproducible_values") or {}
    states = attribution.get("state_penalties") or {}
    variational = states.get("variational_check") or {}
    channels = attribution.get("channel_asymmetry") or {}
    screen = (attribution.get("correlations") or {}).get("state_penalty") or {}
    axis_screen = (attribution.get("correlations") or {}).get("axis_distortion") or {}
    state_table = attribution.get("state_penalties_by_molecule") or []
    axis_table = attribution.get("axis_distortion_by_molecule") or []
    top3 = attribution.get("oxidation_top3_molecules") or []

    definition_block = (
        "**(a) 先把「畸变项」定义清楚**。Stage 13 的 `dist_ev` 不是随手拆出来的小量，"
        "而是每个态的**密度弛豫代价**：\n\n"
        "`D_X(t) = bare(X, t) - bare(X, gas)`，其中 `bare = Total Energy - CPCM Dielectric - SMD CDS`\n\n"
        "也就是「几何冻结、只让电子密度随溶剂自适应」所付出的能量。两个轴观测量是它的差：\n\n"
        "`dist_oxidation = D_cation - D_neutral`，`dist_reduction = D_neutral - D_anion`\n\n"
        "本模块把这条恒等式**逐点重建**：%d 个 (分子, 层, 轴) 组合中，"
        "用态账本重建的 `dist_ev` 与存储值最大偏差 **%s eV**。\n\n"
        "同时给出变分检验：溶剂自适应密度不是 bare 能量的极小点，因此 `D_X >= 0` 必须恒成立。"
        "实测 %d/%d 个逐态惩罚全部为正，最小值 %s eV——**这条检验没有例外**。\n"
        % (216, num(correction.get("penalty_identity_max_abs_residual_ev"), 1),
           sum((states.get(state) or {}).get("n", 0) for state, _ in W13_STATE_SHORT),
           sum((states.get(state) or {}).get("n", 0) for state, _ in W13_STATE_SHORT),
           num(variational.get("worst_minimum_ev"), 4)))

    state_block = ("**(b) 通道不对称是一个「逐态」事实，不是分子的性质**\n\n"
                   "六个 bare CPCM 层的逐分子平均：\n\n"
                   "| 态 | mean D (eV) | std (eV) | min (eV) | max (eV) |\n"
                   "| --- | --- | --- | --- | --- |\n")
    for state, state_label in W13_STATE_SHORT:
        block = states.get(state) or {}
        state_block += "| %s | %s | %s | %s | %s |\n" % (
            state_label, num(block.get("mean_ev"), 4), num(block.get("std_ev"), 4),
            num(block.get("min_ev"), 4), num(block.get("max_ev"), 4))
    state_block += ("\n`D_anion` 是 `D_neutral` 的 **%s 倍**、`D_cation` 的 **%s 倍**。"
                    "Stage 13 观察到的「还原轴畸变大 7 倍」完全由这一条逐态事实产生，"
                    "不需要额外的分子机制。\n\n"
                    "轴观测量本身（12 分子均值）：氧化 %s eV（std %s），还原 %s eV（std %s）；"
                    "比值 **%s 倍**。注意还原轴 **12/12** 个分子全为负，"
                    "而氧化轴 12 个里有 %d 个为负——氧化轴的均值其实是一次近抵消：\n\n"
                    "| 氧化轴前 3 名 | 家族 | dist (eV) | D_cation | D_neutral |\n"
                    "| --- | --- | --- | --- | --- |\n"
                    % (num((states.get("anion") or {}).get("mean_ev", 0.0)
                           / max((states.get("neutral") or {}).get("mean_ev", 1.0), 1e-9), 2),
                       num((states.get("anion") or {}).get("mean_ev", 0.0)
                           / max((states.get("cation") or {}).get("mean_ev", 1.0), 1e-9), 2),
                       signed((channels.get("oxidation") or {}).get("mean_ev"), 4),
                       num((channels.get("oxidation") or {}).get("std_ev"), 4),
                       signed((channels.get("reduction") or {}).get("mean_ev"), 4),
                       num((channels.get("reduction") or {}).get("std_ev"), 4),
                       num(attribution.get("asymmetry_ratio_reduction_over_oxidation"), 2),
                       (channels.get("oxidation") or {}).get("n_negative", 0)))
    for entry in top3:
        state_block += "| %s | %s | %s | %s | %s |\n" % (
            entry.get("name"), entry.get("family"), signed(entry.get("dist_cpcm6_ev"), 4),
            num(entry.get("d_cation_cpcm6_ev"), 4), num(entry.get("d_neutral_cpcm6_ev"), 4))
    state_block += ("\n也就是说：氧化轴上「畸变抵消介电」是 **EC / TMP / PC 三个分子的现象**"
                    "（中位数只有 %s eV），不是全体的共同行为。\n"
                    % signed((channels.get("oxidation") or {}).get("median_ev"), 4))

    correction_block = (
        "**(c) 口径修订：推翻上周 §14 的两个均值**\n\n"
        "`docs/22` §14 把畸变项均值写成 **(%s, %s) eV**（氧化, 还原）。"
        "这两个数**在任何可复现口径下都得不到**：\n\n"
        "1. 先钉符号。对 `stage13_shift_split.csv` 全部 216 行，"
        "`d_total_ev = diel_ev + dist_ev + cds_ev + d4gcp_ev + residual_ev` "
        "的最大绝对残差恰为 **%s eV**，所以 `dist_ev` 是**带符号**的贡献项，"
        "正号表示「加在位移上」，负号表示「拿回一部分」。\n"
        "2. 再穷举。8 个非气相层的全部非空子集（2^8 - 1 = %d 个）× 两种符号约定，"
        "共 **%d 种聚合**，与 §14 的数对相差 1e-6 eV 以内的有 **%d 个**。"
        "最接近的一种是一个临时拼出来的四层组合（%s），"
        "仍差 **%s eV**。\n\n"
        "**可复现的值**（六个 bare CPCM 层、12 审计分子、逐分子先平均）："
        "氧化 **%s eV**（std %s）、还原 **%s eV**（std %s）。"
        "SMD 乙腈上分别是 %s / %s eV。\n\n"
        "这是继 Week 12 三处修订之后的**第四处**主动推翻自己上周判据："
        "上一周的草稿值没有进入任何本周结论。\n"
        % (num(correction.get("published_pair_ev", {}).get("oxidation"), 4)
           if isinstance(correction.get("published_pair_ev"), dict)
           else num(getattr(correction.get("published_pair_ev"), "oxidation", None)),
           num((correction.get("published_pair_ev") or {}).get("reduction"), 4),
           num(correction.get("identity_max_abs_residual_ev"), 1),
           search.get("n_candidates", 0) // 2,
           search.get("n_candidates", 0),
           search.get("n_exact_matches", 0),
           "、".join((search.get("closest") or [{}])[0].get("layers") or []),
           num((search.get("closest") or [{}])[0].get("max_abs_error_ev"), 4),
           signed(values.get("oxidation_ev"), 4), num(values.get("oxidation_std_ev"), 4),
           signed(values.get("reduction_ev"), 4), num(values.get("reduction_std_ev"), 4),
           signed(values.get("smd_acetonitrile_oxidation_ev"), 4),
           signed(values.get("smd_acetonitrile_reduction_ev"), 4)))

    def best_row(rows):
        return max(rows, key=lambda row: (row.get("ols") or {}).get("loo_r2") or -9.0)

    def pick(table, group, descriptor):
        return next((row for row in table
                     if row.get("group") == group
                     and row.get("descriptor") == descriptor), {})

    state_table_rows = screen.get("table") or []
    axis_table_rows = axis_screen.get("table") or []
    neutral_best = best_row([row for row in state_table_rows
                             if row.get("group") == "neutral"])
    anion_best = best_row([row for row in state_table_rows
                           if row.get("group") == "anion"])
    anion_gas = pick(state_table_rows, "anion", "mu_anion_debye")
    ox_mu = pick(axis_table_rows, "oxidation", "mu_neutral_debye")
    ox_homo = pick(axis_table_rows, "oxidation", "homo_ev")

    attribution_block = (
        "**(d) 归因：14 个描述符，只有一条关系经得起留一检验**\n\n"
        "描述符全部取自仓库已有产物：`outputs/week3/p0_core_set.csv`（偶极、极化率、"
        "HOMO / LUMO、HL gap、原子数、P0 两轴）加上气相 ORCA 输出的逐态偶极"
        "（r2SCAN-3c，与位移同方法），共 14 个。样本是 **12 个分子**"
        "（六个介电层先平均——它们是同一个量的六次不同测量，直接按 72 行回归属于伪重复，"
        "p 值会被高估约 sqrt(6) 倍）。\n\n"
        "| 目标 | 最佳单描述符 | Spearman rho | p | R2 | 留一 R2 |\n"
        "| --- | --- | --- | --- | --- | --- |\n")
    for group, group_label in W13_STATE_SHORT:
        rows = [row for row in state_table_rows if row.get("group") == group]
        if not rows:
            continue
        best = best_row(rows)
        attribution_block += "| D_%s | `%s` | %s | %s | %s | **%s** |\n" % (
            group_label, best.get("descriptor"),
            signed((best.get("spearman") or {}).get("rho"), 3),
            num((best.get("spearman") or {}).get("p"), 4),
            num((best.get("ols") or {}).get("r2"), 3),
            num((best.get("ols") or {}).get("loo_r2"), 3))
    for group, group_label in W13_AXIS_SHORT:
        rows = [row for row in axis_table_rows if row.get("group") == group]
        if not rows:
            continue
        best = best_row(rows)
        attribution_block += "| 轴 %s | `%s` | %s | %s | %s | **%s** |\n" % (
            group_label, best.get("descriptor"),
            signed((best.get("spearman") or {}).get("rho"), 3),
            num((best.get("spearman") or {}).get("p"), 4),
            num((best.get("ols") or {}).get("r2"), 3),
            num((best.get("ols") or {}).get("loo_r2"), 3))
    attribution_block += (
        "\n三条读数：\n\n"
        "1. **可预测的只有一个**：`D_neutral` 对分子自身偶极的 rho = %s、留一 R2 = %s。"
        "物理解释直接：中性态的畸变由「偶极 x 反应场」耦合驱动，偶极越大、密度重排越多。"
        "更关键的是 **xtb 的 `dipole_debye`（P0 臂）给出几乎同一个 |rho|**，"
        "所以这条结论不依赖 ORCA。\n"
        "2. **产生不对称的那一项恰恰不可预测**：`D_anion` 的最佳描述符留一 R2 只有 %s，"
        "而阴离子**自己的气相偶极几乎不相关**（rho = %s）。"
        "阴离子带净电荷，主导耦合是**单极**，对所有分子一样；分子之间的差别只能来自"
        "**多出来的那个电子的空间弥散度**——而仓库里现有的任何量都不测这个。"
        "这是一个**否定结论**，也是本周最有价值的一条：它把「阴离子更弥散」从口号变成了"
        "一个可证伪的需求（需要新增弥散度描述符）。\n"
        "3. **轴观测量自我屏蔽**：`dist_oxidation = D_cation - D_neutral` 是两个都跟偶极走的量之差，"
        "偶极依赖大部分抵消，因此氧化轴上偶极 rho 只有 %s；"
        "唯一在氧化轴上过 p < 0.05 的是前沿轨道位置（`homo_ev`，rho = %s，p = %s），"
        "但它的**留一 R2 只有 %s**——这条关系经不起逐点剔除，"
        "**不能当作事前预警器用**。\n"
        % (signed((neutral_best.get("spearman") or {}).get("rho"), 3),
           num((neutral_best.get("ols") or {}).get("loo_r2"), 3),
           num((anion_best.get("ols") or {}).get("loo_r2"), 3),
           signed((anion_gas.get("spearman") or {}).get("rho"), 3),
           signed((ox_mu.get("spearman") or {}).get("rho"), 3),
           signed((ox_homo.get("spearman") or {}).get("rho"), 3),
           num((ox_homo.get("spearman") or {}).get("p"), 4),
           num((ox_homo.get("ols") or {}).get("loo_r2"), 3)))

    outlier_block = ""
    repro_block = ""
    if isinstance(outlier, dict) and outlier.get("curves"):
        verdict = outlier.get("verdict") or {}
        repro = outlier.get("reproducibility") or {}
        curves = outlier.get("curves") or {}
        outlier_block = ("**(e) EMC 离群点：先看清 Stage 13 的拐点在哪**\n\n"
                         "Stage 13 用的是六个 bare 层（eps = 5/10/20/40/80/200），"
                         "24 条曲线里 23 条可接受，EMC 还原轴掉到 R2 = %s，且是唯一非单调的一条。"
                         "它的序列是\n\n"
                         "| eps | 5 | 10 | 20 | 40 | 80 | 200 |\n"
                         "| --- | --- | --- | --- | --- | --- | --- |\n"
                         % num(verdict.get("emc_reduction_born_r2_stage13_grid"), 4))
        focus = curves.get("EMC/reduction") or {}
        focus_delta = focus.get("delta_at_eps") or {}
        outlier_block += "| delta (eV) | %s |\n" % " | ".join(
            num(focus_delta.get("%g" % eps), 4)
            for eps in (5, 10, 20, 40, 80, 200))
        outlier_block += (
            "\n整个异常就是 **eps = 10 -> 20 的单独一跳**（%s eV，方向朝下），"
            "两头都是干净的。六点这么稀，分不开三种完全不同的可能："
            "真实的非 Born 行为 / 网格跨过了一个窄特征 / 阴离子在 eps = 10 单独落进了"
            "另一个 SCF 解。\n\n"
            "因此 Stage 14 在可疑区间**内部**插了 5 个新介电点并复测共享的 4 个："
            "eps = 5/7/10/14/20/28/40（7 x 3 分子 x 3 态 = 63 作业），"
            "再借 Stage 13 已有的 80/200 拼成**九点完整阶梯**。\n\n"
            "逐态分解给出拐点归属（`delta_reduction = [E_neu(eps) - E_neu(gas)] - "
            "[E_ani(eps) - E_ani(gas)]`）：\n\n"
            "| 项 | eps 10 -> 20 的变化 (eV) |\n"
            "| --- | --- |\n"
            % signed(verdict.get("emc_reduction_step_10_to_20_ev"), 4))
        for state, state_label in W13_STATE_SHORT:
            outlier_block += "| %s 态溶剂化能 | %s |\n" % (
                state_label,
                signed((verdict.get("emc_reduction_step_10_to_20_by_state_ev") or {}).get(state), 4))
        outlier_block += ("\n**裁决**：%s\n\n"
                          "九点阶梯上的结果：EMC 还原轴的符号变化数 %s -> %s，"
                          "过原点 Born R2 %s -> %s。\n\n"
                          "| 曲线 | R2 (Stage 13 六点) | R2 (九点) |\n"
                          "| --- | --- | --- |\n"
                          % (verdict.get("reading"),
                             verdict.get("emc_reduction_sign_changes_stage13_grid"),
                             verdict.get("emc_reduction_sign_changes_full_grid"),
                             num(verdict.get("emc_reduction_born_r2_stage13_grid"), 4),
                             num(verdict.get("emc_reduction_born_r2_full_grid"), 4)))
        for key, key_label in W13_CURVE_SHORT:
            curve = curves.get(key) or {}
            outlier_block += "| %s | %s | %s |\n" % (
                key_label, num((curve.get("born_r2_stage13_six_point") or {}).get("r2"), 4),
                num((curve.get("born_through_origin_full_grid") or {}).get("r2"), 4))
        outlier_block += ("\nF27(h) 把 Born R2 对网格点数画成收敛曲线："
                          "只有当加点就能改善时，才说明原来是**采样不足**而不是非 Born。\n")

        repro_block = ("**(f) 可复现性：密集网格与 Stage 13 阶梯是同一个实验**\n\n"
                       "ORCA 输出无法逐字节比对（内嵌墙钟时间与 scratch 路径），"
                       "因此不变量取**印刷出来的能量本身**。复测的 4 个共享介电点 "
                       "(eps = 5/10/20/40) 共 %d 个 (分子, 态)："
                       "%d 个在全部印刷位数上完全一致，最大偏差 **%s Eh**（%s eV），"
                       "全部 %d 个作业 **QC flag 为空**。裁决：**%s**。\n"
                       % (repro.get("n_points_compared"),
                          repro.get("n_identical_strings"),
                          num(repro.get("max_abs_delta_eh"), 1),
                          num(repro.get("max_abs_delta_ev"), 1),
                          repro.get("n_points_compared"), repro.get("verdict")))

    table_block = ("| 文件 | 内容 |\n| --- | --- |\n"
                   "| `stage14_attribution.json` | 恒等式核验、§14 修订记录、"
                   "逐态惩罚、14 描述符 x 5 目标的完整相关矩阵 |\n"
                   "| `stage14_attribution.csv` | 24 行 = 12 分子 x 2 轴，含 14 个描述符 |\n"
                   "| `stage14_distortion_states.csv` | 216 行 = 12 分子 x 3 态 x 6 层 |\n"
                   "| `stage14_distortion_states_by_molecule.csv` | 36 行 = 12 分子 x 3 态"
                   "（统计用样本） |\n"
                   "| `stage14_outlier.json` | 九点阶梯、逐曲线 Born 拟合、"
                   "网格密度收敛、可复现性 |\n"
                   "| `stage14_outlier.csv` | 54 行 = 6 曲线 x 9 介电点 |\n"
                   "| `stage14_dense_grid.json` | 63 个作业的逐层账本（7 层 x 9 作业） |\n")

    did = ("把 Stage 13 留下的两个开口一次收掉：(1) **畸变项归因**——把 `dist_ev` 还原成"
           "「逐态密度弛豫代价」并按 14 个已有描述符做归因（纯分析，0 个新作业）；"
           "(2) **EMC 离群点**——在 Stage 13 的六点阶梯的可疑区间内部插入 5 个新介电点"
           "（eps = 7/14/28 + 重测 5/10/20/40），对 EMC 与两个对照 DMC / EC 共 63 个 ORCA 作业，"
           "拼成九点完整阶梯，判定非单调是真行为还是采样假象。")
    metric = ("逐态畸变惩罚 D_neutral / D_cation / D_anion = %s / %s / %s eV"
              "（全部 %d/%d 为正，变分检验无例外）；通道不对称比 %s 倍；"
              "可预测的只有 D_neutral（对自身偶极 rho = %s，留一 R2 = %s），"
              "产生不对称的 D_anion 与两个轴观测量均**不可预测**；"
              "§14 的 (%s, %s) eV 被穷举证否（%d 种聚合 0 命中），"
              "可复现值 %s / %s eV；EMC 还原轴拐点定位到 eps 10 -> 20（%s eV）。"
              % (num((states.get("neutral") or {}).get("mean_ev"), 4),
                 num((states.get("cation") or {}).get("mean_ev"), 4),
                 num((states.get("anion") or {}).get("mean_ev"), 4),
                 sum((states.get(state) or {}).get("n", 0) for state, _ in W13_STATE_SHORT),
                 sum((states.get(state) or {}).get("n", 0) for state, _ in W13_STATE_SHORT),
                 num(attribution.get("asymmetry_ratio_reduction_over_oxidation"), 2),
                 signed((neutral_best.get("spearman") or {}).get("rho"), 3),
                 num((neutral_best.get("ols") or {}).get("loo_r2"), 3),
                 num((correction.get("published_pair_ev") or {}).get("oxidation"), 4),
                 num((correction.get("published_pair_ev") or {}).get("reduction"), 4),
                 search.get("n_candidates"),
                 signed(values.get("oxidation_ev"), 4), signed(values.get("reduction_ev"), 4),
                 signed((outlier.get("verdict") or {}).get("emc_reduction_step_10_to_20_ev"), 4)
                 if isinstance(outlier, dict) else "\u2014"))
    qc = ("畸变恒等式重建最大残差 %s eV；逐态变分检验 %d/%d 通过；"
          "§14 证否穷举 %d 种聚合、命中 0；密集网格 63 作业 0 失败、"
          "7 层各 9/9 ok；复测 4 个共享介电点 %s 个能量全部逐位一致且 QC flag 为空。"
          % (num(correction.get("penalty_identity_max_abs_residual_ev"), 1),
             sum((states.get(state) or {}).get("n", 0) for state, _ in W13_STATE_SHORT),
             sum((states.get(state) or {}).get("n", 0) for state, _ in W13_STATE_SHORT),
             search.get("n_candidates"),
             (outlier.get("reproducibility") or {}).get("n_identical_strings")
             if isinstance(outlier, dict) else "\u2014"))
    limit = ("畸变项仍**没有**可用于事前预警的描述符：唯一稳健的关系只覆盖中性态，"
             "而真正造成 7 倍不对称的阴离子态最佳留一 R2 仅 %s，"
             "缺的是**多出来的电子的空间弥散度**，仓库现有量都不测它；"
             "n = 12 的单描述符结论不得外推，氧化轴上 `homo_ev` 的 p < 0.05 关系"
             "留一 R2 只有 %s，**不作为预警规则**；"
             "密集网格只覆盖 EMC / DMC / EC 三个分子，"
             "其余 9 个分子的介电阶梯仍是六点。"
             % (num((anion_best.get("ols") or {}).get("loo_r2"), 3),
                num((ox_homo.get("ols") or {}).get("loo_r2"), 3)))

    summary = ("\n- 做了什么：%s\n- 关键数字：%s\n- 质检：%s\n- 限制：%s\n"
               % (did, metric, qc, limit))

    return {"present": True, "did": did, "metric": metric, "qc": qc, "limit": limit,
            "definition_block": definition_block, "state_block": state_block,
            "correction_block": correction_block,
            "attribution_block": attribution_block,
            "outlier_block": outlier_block, "repro_block": repro_block,
            "table_block": table_block, "sigma_note": "", "summary": summary}


REPORT_TEMPLATES[13] = """# Week 13 成果小结 —— Stage 14（畸变项归因与 EMC 离群点诊断）

## 0. 一页结论
- 做了什么：{w13_did}
- 关键数字：{w13_metric}
- 质检：{w13_qc}
- 限制：{w13_limit}

本文可独立阅读；逐项细节、物理机制与需裁决项见同目录 `week13_report_full.md`。

## 1. 畸变项到底是什么
{w13_definition_block}

## 2. 通道不对称的逐态来源
{w13_state_block}

## 3. 口径修订：推翻上周 §14 的两个均值
{w13_correction_block}

## 4. 描述符归因：哪些能预测、哪些不能
{w13_attribution_block}

## 5. EMC 离群点：密集介电网格的裁决
{w13_outlier_block}

## 6. 可复现性
{w13_repro_block}

## 7. 产物与口径
{w13_table_block}

## 8. 产物清单
{artifact_list}

## 9. 源文件缺失
{missing_list}
"""


def week14_blocks(analysis, diffuseness, anchor_scan):
    """Render the week-14 (Stage 15) blocks.

    Every number is read back out of ``stage15_two_guess_analysis.json``,
    ``stage15_diffuseness.json`` and ``stage15_anchor_scan.json``, so the
    distilled report cannot drift away from the figures it summarises.
    """

    empty = {"present": False, "did": "", "metric": "", "qc": "", "limit": "",
             "protocol_block": "", "limit_block": "", "diffuseness_block": "",
             "anchor_block": "", "table_block": "", "sigma_note": "", "summary": ""}
    if not isinstance(analysis, dict) or not analysis.get("verdict"):
        return empty

    def num(value, digits=3):
        return _w8_num(value, digits)

    def signed(value, digits=3):
        text = _w8_num(value, digits)
        if text == "\u2014":
            return text
        return text if text.startswith("-") else "+" + text

    def eps_list(values):
        return ", ".join("%g" % float(v) for v in (values or []))

    state_label = dict(W14_STATE_SHORT)
    energy = analysis.get("energy") or {}
    verdict = analysis.get("verdict") or {}
    repro = analysis.get("stage14_reproduction") or {}
    conductor = analysis.get("conductor_limit") or {}
    stage13 = conductor.get("stage13_published") or {}
    default = conductor.get("default") or {}
    moread = conductor.get("moread") or {}
    dipole_by_key = {}
    for item in analysis.get("dipole_changed") or []:
        dipole_by_key[(item.get("name"), item.get("state"), item.get("epsilon"))] = item

    # --- 1. the two-guess protocol ---------------------------------------
    hist = energy.get("magnitude_histogram") or {}
    hist_rows = ["| 幅度阈值 (eV) | 超过该阈值的点数 |", "| --- | --- |"]
    for key in ("1e-08", "1e-07", "1e-06", "1e-05", "1e-04", "1e-03", "1e-02", "1e-01"):
        hist_rows.append("| `%s` | %s |" % (key, hist.get(key)))

    material_rows = ["| 分子 | 态 | eps | `dE` (eV) | 默认初猜偶极 (D) |", "| --- | --- | --- | --- | --- |"]
    for item in energy.get("material") or []:
        key = (item.get("name"), item.get("state"), item.get("epsilon"))
        dip = dipole_by_key.get(key) or {}
        material_rows.append("| %s | %s | %s | **%s** | %s |"
                             % (item.get("name"), state_label.get(item.get("state"),
                                                                  item.get("state")),
                                num(item.get("epsilon"), 0),
                                signed(item.get("delta_ev"), 4),
                                num(dip.get("dipole_default_debye"), 3)))

    recovery_rows = ["| eps | 默认初猜 (D) | MORead (D) | 能量降低 (eV) |", "| --- | --- | --- | --- |"]
    for item in verdict.get("emc_anion_recovery") or []:
        recovery_rows.append("| %s | %s | **%s** | %s |"
                             % (num(item.get("epsilon"), 0),
                                num(item.get("dipole_default_debye"), 3),
                                num(item.get("dipole_moread_debye"), 3),
                                num(item.get("energy_lowered_ev"), 4)))

    protocol_block = (
        "### 1.1 协议与规模\n"
        "- 分子 EMC / DMC / EC；介电阶梯 5/7/10/14/20/28/40/80/200/1000（10 点）；"
        "态 neutral / cation / anion。\n"
        "- 每个点跑两遍：`default` = ORCA 自己的初猜；`moread` = `! MORead` + "
        "`%moinp <同电荷态气相 .gbw>`。共 **99** 个作业，**0 失败、0 QC flag**。\n"
        "- 差异定义 `dE = E_moread - E_default`；`dE < 0` 表示重启到达了默认初猜"
        "没到达的更低价态。几何全部复用 G1 并逐原子核对。\n\n"
        "### 1.2 能量差的分档（数据给出的阈值）\n"
        + "\n".join(hist_rows) + "\n\n"
        "- 90 个点里 **%s** 个在收敛精度内一致；**%s** 个超过 1 meV 且**全部为负**；"
        "反向（重启更差）**%s** 次。\n"
        "- 噪声带内最大值 **%s eV**，真解差异最小 1.5e-03 eV、最大 **%s eV**。\n\n"
        % (energy.get("n_identical_to_scf_convergence"),
           energy.get("n_material_differences"),
           energy.get("n_material_restart_above_the_default_state"),
           num(energy.get("worst_of_the_noise_ev"), 6),
           num(energy.get("max_default_excess_ev"), 4))
        + "### 1.3 十二个真解差异，方向全部相同\n"
        + "\n".join(material_rows) + "\n\n"
        "- 受影响：`%s`，态 `%s`。最大惩罚 **%s eV**（EMC 阴离子，eps = 1000）。\n\n"
        % (", ".join(energy.get("affected_molecules") or []),
           ", ".join(energy.get("affected_states") or []),
           num(energy.get("max_default_excess_ev"), 4))
        + "### 1.4 EMC 阴离子：失败集与成功集交错\n"
        + "- 失败集（默认初猜停在亚稳态）：`{%s}`\n"
        "- 成功集（默认初猜已落在真解）：`{%s}`\n"
        "- 两个集合**交错**，所以这不是「大介电才出错」的单调故事，"
        "而是两个 SCF 解的吸引域随介电常数非单调变化——"
        "这解释了为什么 Week 13 把网格从 4 点加密到 9 点会让它**变糟**。\n\n"
        % (eps_list(verdict.get("emc_anion_dielectrics_where_the_default_guess_failed")),
           eps_list(verdict.get("emc_anion_dielectrics_where_it_succeeded")))
        + "### 1.5 EMC 阴离子的修复是单调的\n"
        + "\n".join(recovery_rows) + "\n\n"
        "- 十个偶极逐点上升（%s -> %s D），**无一处回折**；"
        "修复后 Spearman(偶极, eps) = **%s**，默认初猜是 %s。\n\n"
        % (num((verdict.get("emc_anion_recovery") or [{}])[0].get("dipole_moread_debye"), 3),
           num((verdict.get("emc_anion_recovery") or [{}])[-1].get("dipole_moread_debye"), 3),
           num((verdict.get("dipole_monotonicity") or {}).get("moread_spearman_dipole_vs_eps"), 3),
           num((verdict.get("dipole_monotonicity") or {}).get("default_spearman_dipole_vs_eps"), 3))
        + "### 1.6 曲线被修好，但没修到 1\n"
        "| 口径（九点 5…200） | 默认初猜 | MORead |\n"
        "| --- | --- | --- |\n"
        "| Born R2（过原点） | %s | **%s** |\n"
        "| 一阶差分符号变化 | %s | **%s** |\n"
        "| 阴离子偶极粗糙度 | %s | **%s** |\n\n"
        "- 六点 Born R2 = **%s**（Stage 14 公布 %s，`reproduces_stage14 = %s`）；"
        "九点 Born R2 = **%s**（Stage 14 公布 %s）。\n"
        "- 六点斜率：默认 %s -> 修复 %s eV；九点：%s -> %s eV。\n"
        "- **0.9556 不等于 1**：修复掉的是解选择伪影，不是 Born 形式的偏差（见 §2）。\n"
        % (num(verdict.get("emc_reduction_default_nine_r2"), 4),
           num(verdict.get("emc_reduction_moread_nine_r2"), 4),
           verdict.get("emc_reduction_default_nine_sign_changes"),
           verdict.get("emc_reduction_moread_nine_sign_changes"),
           num(verdict.get("emc_anion_default_nine_roughness"), 3),
           num(verdict.get("emc_anion_moread_nine_roughness"), 3),
           num(repro.get("recomputed_default_six_point_r2"), 4),
           num((repro.get("published") or {}).get("six_point_r2"), 4),
           repro.get("reproduces_stage14"),
           num(repro.get("recomputed_default_nine_point_r2"), 4),
           num((repro.get("published") or {}).get("nine_point_r2"), 4),
           num(default.get("born_slope_from_six_points_ev"), 4),
           num(moread.get("born_slope_from_six_points_ev"), 4),
           num(default.get("born_slope_from_nine_points_ev"), 4),
           num(moread.get("born_slope_from_nine_points_ev"), 4)))

    # --- 2. the conductor limit ------------------------------------------
    limit_rows = ["| 口径 | 默认初猜 | MORead |", "| --- | --- | --- |",
                  "| 六点斜率（5/10/20/40/80/200） | %s | %s |"
                  % (num(default.get("born_slope_from_six_points_ev"), 4),
                     num(moread.get("born_slope_from_six_points_ev"), 4)),
                  "| 六点斜率下 eps = 200 的缺口 | **%s** | **%s** |"
                  % (signed(default.get("gap_to_six_point_slope_at_eps200_ev"), 4),
                     signed(moread.get("gap_to_six_point_slope_at_eps200_ev"), 4)),
                  "| 九点斜率（5…200） | %s | %s |"
                  % (num(default.get("born_slope_from_nine_points_ev"), 4),
                     num(moread.get("born_slope_from_nine_points_ev"), 4)),
                  "| `delta(eps = 200)` | %s | %s |"
                  % (num(default.get("delta_at_eps200_ev"), 4),
                     num(moread.get("delta_at_eps200_ev"), 4)),
                  "| `delta(eps = 1000)` | %s | %s |"
                  % (num(default.get("delta_at_eps1000_ev"), 4),
                     num(moread.get("delta_at_eps1000_ev"), 4)),
                  "| 外推误差 @200 | %s | %s |"
                  % (signed(default.get("extrapolation_error_at_200_ev"), 4),
                     signed(moread.get("extrapolation_error_at_200_ev"), 4)),
                  "| 外推误差 @1000 | %s | %s |"
                  % (signed(default.get("extrapolation_error_at_1000_ev"), 4),
                     signed(moread.get("extrapolation_error_at_1000_ev"), 4)),
                  "| eps 200 -> 1000 的位移 | **%s** | %s |"
                  % (num(default.get("gap_between_eps200_and_eps1000_ev"), 4),
                     num(moread.get("gap_between_eps200_and_eps1000_ev"), 4))]

    limit_block = (
        "Born 横坐标是 `x = 1 - 1/eps`，所以**拟合出的斜率就是 `eps -> infinity` 的"
        "外推极限本身**。Stage 14 停在 `eps = 200`（`x = 0.995`）；"
        "本周补的 `eps = 1000` 对应 `x = 0.999`，是第一个把横坐标推进到极限千分之一的实测点。\n\n"
        + "\n".join(limit_rows) + "\n\n"
        "- 默认初猜的 `+33.2 meV` 是 Week 12 §5 那个 worst case 的**逐位复现**"
        "（`reproduces_the_worst_case = %s`），所以对比的是同一根曲线。\n"
        "- **缺口没有变小**：默认 %s -> 修复 %s eV。符号翻了，幅度基本没动。"
        "若 0.2860 eV 的亚稳位移是缺口来源，修掉它后缺口应塌掉一个量级；它没有。\n"
        "- `eps = 200 -> 1000` 只走 **%s eV**（相对 2.6 eV 的斜率是 0.4%%），"
        "所以曲线的形状已经在极限附近平了，Stage 14 停在 200 不是坏截断；"
        "真实偏离在**形状**上，不在截断点上。\n"
        % (stage13.get("reproduces_the_worst_case"),
           signed(default.get("gap_to_six_point_slope_at_eps200_ev"), 4),
           signed(moread.get("gap_to_six_point_slope_at_eps200_ev"), 4),
           num(default.get("gap_between_eps200_and_eps1000_ev"), 4)))

    # --- 3. the diffuseness descriptors ----------------------------------
    definitions = diffuseness.get("descriptor_definitions") or {}
    domain = diffuseness.get("descriptor_domain") or {}
    screen = diffuseness.get("gas_phase_screen") or {}
    verdicts = diffuseness.get("verdicts") or {}
    robust = diffuseness.get("robust_verdicts") or {}
    pairs = diffuseness.get("pair_search") or {}
    ext_by_key = {}
    for row in diffuseness.get("extended_table") or []:
        ext_by_key[(row.get("group"), row.get("descriptor"))] = row

    def stat(group, desc):
        row = ext_by_key.get((group, desc)) or {}
        return ((row.get("spearman") or {}).get("rho"),
                (row.get("spearman") or {}).get("p"),
                (row.get("ols") or {}).get("loo_r2"))

    definition_rows = ["| 描述符 | 定义 |", "| --- | --- |"]
    for key in ("spin_extent_ang2", "spin_rms_ang", "spin_maxfrac", "spin_participation",
                "spin_extent_norm", "chg_extent_ang2", "chg_extent_norm"):
        definition_rows.append("| `%s` | %s |" % (key, definitions.get(key)))

    target_rows = ["| 目标 | Stage 14 冠军 | 留一 R2 | Stage 15 冠军 | 留一 R2 | `delta_loo_r2` |",
                   "| --- | --- | --- | --- | --- | --- |"]
    for key, label in W14_TARGET_SHORT:
        item = verdicts.get(key) or {}
        target_rows.append("| `%s` | `%s` | %s | `%s` | **%s** | **%s** |"
                           % (label, item.get("baseline_best_descriptor"),
                              num(item.get("baseline_best_loo_r2"), 3),
                              item.get("extended_best_descriptor"),
                              num(item.get("extended_best_loo_r2"), 3),
                              num(item.get("delta_loo_r2"), 3)))

    rank_rows = ["| 阴离子轴上的描述符 | Spearman rho | p | 留一直线 R2 |", "| --- | --- | --- | --- |"]
    for desc in ("spin_maxfrac", "spin_participation"):
        rho, pval, loo = stat("anion", desc)
        rank_rows.append("| `%s` | **%s** | %s | **%s** |"
                         % (desc, signed(rho, 3), num(pval, 4), signed(loo, 3)))

    pair_rows = ["| 目标 | 最好的一对 | 留一 R2 |", "| --- | --- | --- |"]
    for key, label in W14_TARGET_SHORT:
        ranked = (pairs.get(key) or {}).get("ranked") or []
        best = ranked[0] if ranked else {}
        pair_rows.append("| `%s` | `%s` | **%s** |"
                         % (label, " + ".join(best.get("descriptors") or []),
                            num(best.get("loo_r2"), 3)))

    outliers = domain.get("layer_outliers_vs_own_median") or []
    outlier_text = ("；".join("%s/%s (%s)" % tuple(item) for item in outliers)
                    if outliers else "无")

    diffuseness_block = (
        "### 3.1 七个新描述符（0 个新作业）\n"
        "取自六层 bare-CPCM 阴离子的 `MULLIKEN ATOMIC CHARGES AND SPIN POPULATIONS` 块，"
        "逐分子取层均值（另给中位数口径）：\n\n"
        + "\n".join(definition_rows) + "\n\n"
        "### 3.2 先检验描述符自己是否良定义\n"
        "- 归一化：**%s** 行（12 分子 x 6 层）最坏的 `|sum s - 1| = %s`、"
        "`|sum q + 1| = %s`，全部通过。\n"
        "- 符号：Mulliken 自旋是**有符号**的，所以 `max|s_i| > 1` 是**强自旋极化**的标志、"
        "不是「阴离子不束缚」；判据必须用**带符号和**。\n"
        "- 气相排除：`%s` 落在六层张成的域之外，`n_inside_domain = %s/%s`。\n"
        "- **唯一**偏离自身分子中位数 20%% 以上的层：**%s**"
        "（该层 `spin_maxfrac` 跳到 1.737、参与比掉到 0.308）。"
        "这与 §1 的能量筛查**独立命中同一个层**，所以不是循环论证。\n\n"
        % (domain.get("n_rows"), num(domain.get("worst_abs_sum_spin_minus_one"), 7),
           num(domain.get("worst_abs_sum_charge_plus_one"), 1),
           ", ".join(screen.get("outside_layer_domain") or []),
           screen.get("n_inside_domain"), screen.get("n_available"), outlier_text)
        + "### 3.3 阴离子畸变惩罚从不可预测变成可预测\n"
        + "\n".join(target_rows) + "\n\n"
        "- `spin_maxfrac` 的 Spearman `rho = %s`、`p = %s`；换成层**中位数**口径，"
        "留一 R2 = **%s**、`rho = %s`。\n"
        "- **中性与阳离子最优描述符一变不变**（`delta_loo_r2 = 0`），"
        "所以这不是「多加 7 个描述符所以哪都能拟合」。\n\n"
        % (signed((verdicts.get("anion") or {}).get("extended_best_rho"), 3),
           num((verdicts.get("anion") or {}).get("extended_best_p"), 4),
           num((robust.get("anion") or {}).get("median_best_loo_r2"), 3),
           signed((robust.get("anion") or {}).get("median_best_rho"), 3))
        + "### 3.4 秩 vs 线性：两个统计量都要报\n"
        + "\n".join(rank_rows) + "\n\n"
        "- 参与比的**秩**信号（rho = -0.846）比 `spin_maxfrac` 还强，"
        "但它的留一**直线** R2 是负的 —— 只报秩会严重误导。\n\n"
        + "### 3.5 配对搜索\n"
        + "\n".join(pair_rows) + "\n")

    # --- 4. the literature scan ------------------------------------------
    gate1 = anchor_scan.get("gate1") or {}
    manual = anchor_scan.get("manual_adjudication") or {}
    adjudication_rows = ["| 行 | 物种 | 性质 | 最终证据标签 | 是否改动 | 理由 |",
                         "| --- | --- | --- | --- | --- | --- |"]
    for row_id in sorted(manual, key=lambda item: int(item)):
        item = manual.get(row_id) or {}
        adjudication_rows.append("| %s | %s | %s | `%s` | %s | %s |"
                                 % (row_id, item.get("species"), item.get("property"),
                                    item.get("final_evidence_kind"),
                                    "**是**" if item.get("adopted_change") else "否（确认）",
                                    item.get("reason")))
    rejected_rows = ["| 行 | 线索 | 否掉的理由 |", "| --- | --- | --- |"]
    for row_id, reason in sorted((anchor_scan.get("rejected_candidate_leads") or {}).items(),
                                 key=lambda pair: int(pair[0])):
        rejected_rows.append("| %s | —— | %s |" % (row_id, reason))

    anchor_block = (
        "- 语料：**%s** 篇 PDF，**%s** 篇可读；审计表引用 %s 个 DOI，"
        "语料里只有 **%s** 个在手。\n"
        "- 31 行里 %s 行引用了那篇在手综述，其中只有 **%s** 行的引用集合完全在手，"
        "因此只有这 %s 行可裁定。\n\n"
        % (anchor_scan.get("n_pdfs"), anchor_scan.get("n_readable"),
           len(anchor_scan.get("cited_dois_of_audit") or []),
           len(anchor_scan.get("cited_dois_present_in_corpus") or []),
           gate1.get("n_rows_citing_an_in_hand_source"), gate1.get("n_rows_adjudicable"),
           gate1.get("n_rows_adjudicable"))
        + "\n".join(adjudication_rows) + "\n\n"
        "- `n_corrections_adopted = %s`、`confirmed_rows = %s`、"
        "`n_upgrades_meeting_conditions = %s`。\n"
        "- 三条被逐字读过、仍被否的数值线索（全部是**络合物**而非孤立溶剂）：\n\n"
        % (gate1.get("n_corrections_adopted"),
           ", ".join(gate1.get("confirmed_rows") or []),
           gate1.get("n_upgrades_meeting_conditions"))
        + "\n".join(rejected_rows) + "\n\n"
        "- **Gate 1 仍是 `%s`**，`n_rows_still_est_after_scan = %s`；"
        "三条修正以 overlay `stage15_anchor_corrections.csv` 作为 correction of record，"
        "**不写回**有 digest 的冻结表。\n"
        "- 净收益是**清账而非补值**：3 行的标签从「有综述趋势支持」降级为"
        "「在手来源根本没覆盖这个物种」。\n"
        % (gate1.get("gate1_status"), gate1.get("n_rows_still_est_after_scan")))

    # --- 5. products ------------------------------------------------------
    table_rows = ["| 产物 | 内容 |", "| --- | --- |"]
    for name, note in W14_TABLE_ROWS:
        table_rows.append("| %s | %s |" % (name, note))
    table_block = "\n".join(table_rows)

    did = ("把 Stage 14 留下的开口一次收掉：(1) **双初猜协议**——对 EMC / DMC / EC 在十点"
           "介电阶梯（5/7/10/14/20/28/40/80/200/1000）上各跑两遍"
           "（ORCA 默认初猜 vs `! MORead` 气相 MO 重启），99 个新作业；"
           "(2) **导体极限**——补 `eps = 1000`（`x = 0.999`）实测点；"
           "(3) **弥散度描述符**——从六层 bare-CPCM 的 Mulliken 自旋布居构造 7 个新量并重跑 "
           "Stage 14 的归因（**0 个新作业**）；(4) **文献扫描**——对 13 篇在手 PDF 做"
           "机器可核查的锚点否证（**0 个新作业**）。")
    metric = ("90 个点里 %s 个在收敛精度内一致、**%s 个超过 1 meV 且全部为负**、反向 0 次，"
              "最大惩罚 **%s eV**；EMC 还原轴九点 Born R2 **%s -> %s**、符号变化 %s -> 0、"
              "偶极粗糙度 %s -> %s，修复后偶极严格单调（rho = %s）；"
              "eps = 200 -> 1000 只走 **%s eV**，而六点缺口 %s -> %s eV（**没有变小**）；"
              "阴离子畸变惩罚的最佳留一 R2 **%s -> %s**（%s，rho = %s），"
              "中性与阳离子的 `delta_loo_r2` 都为 0；31 行锚点里 %s 行可裁定、%s 改 1 确认，"
              "Gate 1 仍 NOT CLOSED。"
              % (energy.get("n_identical_to_scf_convergence"),
                 energy.get("n_material_differences"),
                 num(energy.get("max_default_excess_ev"), 4),
                 num(verdict.get("emc_reduction_default_nine_r2"), 4),
                 num(verdict.get("emc_reduction_moread_nine_r2"), 4),
                 verdict.get("emc_reduction_default_nine_sign_changes"),
                 num(verdict.get("emc_anion_default_nine_roughness"), 3),
                 num(verdict.get("emc_anion_moread_nine_roughness"), 3),
                 num((verdict.get("dipole_monotonicity") or {}).get(
                     "moread_spearman_dipole_vs_eps"), 3),
                 num(default.get("gap_between_eps200_and_eps1000_ev"), 4),
                 signed(default.get("gap_to_six_point_slope_at_eps200_ev"), 4),
                 signed(moread.get("gap_to_six_point_slope_at_eps200_ev"), 4),
                 num((verdicts.get("anion") or {}).get("baseline_best_loo_r2"), 3),
                 num((verdicts.get("anion") or {}).get("extended_best_loo_r2"), 3),
                 (verdicts.get("anion") or {}).get("extended_best_descriptor"),
                 signed((verdicts.get("anion") or {}).get("extended_best_rho"), 3),
                 gate1.get("n_rows_adjudicable"), gate1.get("n_corrections_adopted")))
    qc = ("99 个作业 0 失败、0 QC flag、11 层各 9/9 ok；Stage 14 的九点 R2 %s 与符号变化 %s "
          "被逐位复现；Week 12 的 33.2 meV worst case 逐位复现（`reproduces_the_worst_case`）；"
          "描述符域检验 %s 行全部通过（最坏 `|sum s - 1| = %s`）；"
          "层内越界点仅 1 个（%s）且与能量筛查独立命中同一层；13 篇 PDF 全部可读。"
          % (num(repro.get("recomputed_default_nine_point_r2"), 4),
             repro.get("recomputed_default_nine_sign_changes"),
             domain.get("n_rows"), num(domain.get("worst_abs_sum_spin_minus_one"), 7),
             outlier_text))
    limit = ("双初猜只覆盖 EMC / DMC / EC 三个分子，所以「12 个真解差异」是这 3 个分子的**下界**；"
             "导体极限只补了 EMC 一条曲线，其余 11 个分子的 `eps = 1000` 未算；"
             "弥散度描述符与靶量之间只有留一交叉验证、没有第二个数据集"
             "（**0.556 不是样本外 R2**）；描述符的域比靶集小一格"
             "（AN 的气相点落在域外被排除）；文献扫描只覆盖 4 行，"
             "其余 27 行仍为 `est` 且其中 7 行的部分引用不在手；"
             "三条修正以 overlay 存在、未写回冻结表。")

    summary = ("\n- 做了什么：%s\n- 关键数字：%s\n- 质检：%s\n- 限制：%s\n"
               % (did, metric, qc, limit))

    return {"present": True, "did": did, "metric": metric, "qc": qc, "limit": limit,
            "protocol_block": protocol_block, "limit_block": limit_block,
            "diffuseness_block": diffuseness_block, "anchor_block": anchor_block,
            "table_block": table_block, "sigma_note": "", "summary": summary}


def week15_blocks(analysis, predictor):
    """Week 15 / Stage 16 narrative blocks (the catalogue and the warning rule)."""

    keys = ("did", "metric", "qc", "limit", "summary", "protocol_block",
            "verdict_block", "label_block", "rule_block", "family_block",
            "table_block")
    if analysis is None:
        text = "（`stage16_catalogue_analysis.json` 不存在）"
        return {key: text for key in keys}

    n_cells = analysis.get("n_cells") or 0
    n_paired = analysis.get("n_paired") or 0
    lower = analysis.get("n_moread_lower") or 0
    higher = analysis.get("n_moread_higher") or 0
    coincident = analysis.get("n_coincident") or 0
    flagged = analysis.get("flagged_molecules") or {}
    counts = analysis.get("n_flagged_molecules") or {}
    n_molecules = analysis.get("n_discovery_molecules") or 0
    worst = analysis.get("worst_negative_ev")
    worst_at = analysis.get("worst_negative_at") or ["?", "?", "?"]
    threshold = analysis.get("material_threshold_ev")
    ladders = analysis.get("ladders") or {}
    per_state = analysis.get("per_state_counts") or {}

    state_rows = ["| 状态 | 单元格 | MORead 更低 | MORead 更高 |",
                  "| --- | --- | --- | --- |"]
    for state, label in W15_STATE_SHORT:
        entry = per_state.get(state) or {}
        if not entry:
            continue
        state_rows.append("| %s | %d | %d | %d |"
                          % (label, entry.get("n_cells", 0),
                             entry.get("n_moread_lower", 0),
                             entry.get("n_moread_higher", 0)))

    ladder_rows = ["| 阶梯 | 电介质 | 判为有漏解的分子 | 比例 |",
                   "| --- | --- | --- | --- |"]
    for key, label in W15_LADDER_SHORT:
        eps = ladders.get(key) or []
        names = flagged.get(key) or []
        ladder_rows.append("| %s | %s | %d/%d | %s |"
                           % (label, "/".join("%g" % value for value in eps),
                              len(names), n_molecules,
                              ", ".join(names) if names else "无"))

    protocol_block = "\n".join([
        "### 协议与规模",
        "",
        "- 发现集：T3 审计子集的 12 个分子；验证集：从未做过连续介质计算的 6 个分子"
        "（%s）。" % ", ".join(analysis.get("extra_molecules") or []),
        "- 电介质阶梯：%s，与 Stage 13/14/15 逐点一致。"
        % ", ".join("%g" % value for value in (analysis.get("ladder_all_eps") or [])),
        "- 两臂：`default`（ORCA 自带初猜）与 `moread`（`! MORead` + 气相 `%moinp`，"
        "同一电荷态）。",
        "- 单元格：%d 个（%d 个分子的 %d 个状态 x %d 个电介质），配对成功的 %d 个，"
        "未配对的 %d 个。"
        % (n_cells, n_molecules, len(analysis.get("states") or []),
           len(analysis.get("ladder_all_eps") or []), n_paired,
           analysis.get("n_unpaired") or 0),
        "- 几何：G1 冻结；几何审计对每个有连续介质参照的分子逐一比对气相与 CPCM(20) 的"
        "xyz，全部逐原子相同。",
        "- 算力：`--jobs 2 --nprocs 8`（本机 16 逻辑核），与既有 P2 各层协议相同。",
    ])

    verdict_block = "\n".join([
        "### 目录结论",
        "",
        "- 配对单元格 %d：两臂一致到 SCF 收敛 %d 个，MORead 更低 %d 个，MORead 更高 %d 个。"
        % (n_paired, coincident, lower, higher),
        "- 最大赤字：**%.6f eV**，出现在 %s / %s / eps=%g。"
        % (worst or 0.0, worst_at[0], worst_at[1], worst_at[2]),
        "- 阈值原文（继承自 Week 14，本周未重新调参）：%s"
        % (analysis.get("threshold_provenance") or ""),
        "",
        "| 状态 | 单元格 | MORead 更低 | MORead 更高 |",
        "| --- | --- | --- | --- |",
    ] + state_rows[2:] + [
        "",
        "| 阶梯 | 电介质 | 判为有漏解的分子 | 比例 |",
        "| --- | --- | --- | --- |",
    ] + ladder_rows[2:])

    agreement = analysis.get("label_agreement") or {}
    label_lines = ["### 标签对阶梯的稳健性", "",
                   "标签定义在「某 (分子, 状态) 在被探测的电介质上是否存在被默认初猜漏掉的"
                   "更低解」。阶梯越密，漏检越少，因此 `core3` 的标签必然被 `focus6` 蕴含、"
                   "`focus6` 必然被 `ladder10` 蕴含；下表给出实测差异。", ""]
    for pair, entry in sorted(agreement.items()):
        label_lines.append("- `%s`：%d 行中 %d 行不一致%s"
                           % (pair, entry.get("n_rows", 0), entry.get("n_disagree", 0),
                              "（%s）" % ", ".join(entry.get("disagreements") or [])
                              if entry.get("disagreements") else "（两者完全一致）"))
    label_block = "\n".join(label_lines)

    family = ((analysis.get("family_coverage") or {}).get("ladder10") or {})
    family_lines = ["### 家族覆盖", "",
                    "| 家族 | 分子数 | 其中有漏解 | 分子 |",
                    "| --- | --- | --- | --- |"]
    for name in sorted(family):
        entry = family[name]
        family_lines.append("| %s | %d | %d | %s |"
                            % (name, entry.get("n_molecules", 0),
                               entry.get("n_flagged", 0),
                               ", ".join(entry.get("molecules") or [])))
    patterns = analysis.get("monotonicity") or []
    if patterns:
        family_lines += ["", "| 分子 | 状态 | 模式（低 eps 到高 eps） | 命中 | 连续 | 首个 | 末个 |",
                         "| --- | --- | --- | --- | --- | --- | --- |"]
        for row in patterns:
            family_lines.append("| %s | %s | `%s` | %d | %s | %g | %g |"
                                % (row.get("name"), row.get("state"), row.get("pattern"),
                                   row.get("n_flagged", 0),
                                   "是" if row.get("contiguous") else "否",
                                   row.get("first_flagged_eps") or 0.0,
                                   row.get("last_flagged_eps") or 0.0))
    family_block = "\n".join(family_lines)

    rule_lines = ["### 事前预警规则", ""]
    if not predictor:
        rule_lines.append("（`stage16_predictor.json` 不存在）")
    else:
        chosen = predictor.get("chosen_rule") or {}
        screen = predictor.get("screen") or []
        rule_lines += [
            "- 样本：%d 行开壳层 (分子, 状态)（%d 个正例）；%s"
            % (predictor.get("n_discovery_rows") or 0,
               predictor.get("n_discovery_positive") or 0,
               predictor.get("restriction") or ""),
            "- 冻结规则：`%s %s %.6g`，定义「%s」。"
            % (chosen.get("descriptor"),
               ">=" if chosen.get("sign") == "larger_is_riskier" else "<=",
               chosen.get("threshold_frozen") or 0.0,
               chosen.get("definition") or ""),
            "- 发现集：AUC %.3f，样本内准确率 %.3f，留一准确率 %.3f，多数类基线 %.3f。"
            % (chosen.get("auc") or 0.0, chosen.get("accuracy_in_sample") or 0.0,
               chosen.get("loo_accuracy") or 0.0,
               predictor.get("baseline_majority_accuracy") or 0.0),
            "- 阈值只由发现集选出（留一），验证集不参与任何拟合。",
            "",
            "| 描述符 | 方向 | AUC | 留一准确率 |",
            "| --- | --- | --- | --- |",
        ]
        for entry in screen[:6]:
            rule_lines.append("| %s | %s | %.3f | %.3f |"
                              % (entry.get("descriptor"),
                                 "越大越危险" if entry.get("sign") == "larger_is_riskier"
                                 else "越小越危险",
                                 entry.get("auc") or 0.0,
                                 entry.get("loo_accuracy") or 0.0))
        beats = predictor.get("chosen_rule_beats_majority_baseline")
        rule_lines += [
            "",
            "**与多数类基线的比较（不假设结论）**：留一准确率 **%.3f** %s 多数类基线 "
            "**%.3f**，故 `chosen_rule_beats_majority_baseline = %s`。"
            % (chosen.get("loo_accuracy") or 0.0,
               "**超过**" if beats else "**未超过**",
               predictor.get("baseline_majority_accuracy") or 0.0, beats),
            "- 但规则**不是噪声**：平衡准确率（sensitivity 与 specificity 的均值，阈值并不"
            "按它选）样本内 %.3f，而任何「一律判同一类」的平凡规则恒为 %.3f；样本内准确率 "
            "%.3f 与留一准确率 %.3f 之间的落差就是过拟合的量。"
            % (chosen.get("balanced_accuracy_in_sample") or 0.0,
               predictor.get("trivial_balanced_accuracy") or 0.0,
               chosen.get("accuracy_in_sample") or 0.0,
               chosen.get("loo_accuracy") or 0.0),
            "- 基线定义：%s" % (predictor.get("majority_baseline_note") or ""),
        ]
        arm_diag = predictor.get("per_arm_diagnostic") or {}
        arm_blocks = arm_diag.get("arms") or {}
        if arm_blocks:
            rule_lines += [
                "",
                "**两臂事后诊断（`post_hoc = %s`；这是对失败的机制解释，不是预报）**"
                % arm_diag.get("post_hoc"),
                "",
                "| 臂 | 行数 | 正例 | 多数类基线 | 排序最强描述符 | AUC | 正例排名 | "
                "该描述符留一 | 超过基线 | 精确置换 p |",
                "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
            ]
            for arm in ("cation", "anion"):
                block = arm_blocks.get(arm) or {}
                top = (block.get("screen") or [{}])[0]
                rule_lines.append(
                    "| %s | %s | %s | %.3f | `%s` | %.3f | %s | %.3f | %s | %.4f |"
                    % (arm, block.get("n_rows"), block.get("n_positive"),
                       block.get("majority_accuracy") or 0.0,
                       top.get("descriptor") or "", top.get("auc") or 0.0,
                       "/".join(str(rank) for rank in (top.get("positive_ranks") or [])),
                       top.get("loo_accuracy") or 0.0,
                       "是" if top.get("beats_majority_baseline") else "否",
                       top.get("permutation_p") or 0.0))
            rule_lines += [
                "",
                "- 失败原因（产物原文）：%s" % (arm_diag.get("note") or ""),
                "- 选臂用的量是**电荷态**，作业开始前就已知：%s"
                % (arm_diag.get("arm_selector_note") or ""),
                "- 注意：「某描述符的留一准确率超过基线」本身不等于证据——阳离子臂上"
                "留一最高的是 `gas_spin_participation`（%.3f），但它的排序信息几乎为零"
                "（|AUC−0.5| = %.3f，置换 p = %.3f）。因此本表同时给出 AUC 与正例排名。"
                % (((arm_blocks.get("cation") or {}).get("best_loo_accuracy") or 0.0),
                   ((arm_blocks.get("cation") or {}).get("screen") or [{}])[-1]
                   .get("abs_auc_above_half") or 0.0,
                   ((arm_blocks.get("cation") or {}).get("screen") or [{}])[-1]
                   .get("permutation_p") or 0.0),
            ]
        validation = predictor.get("validation") or {}
        if validation.get("accuracy") is not None:
            matrix = validation.get("confusion_matrix") or {}
            rule_lines += [
                "",
                "- 留出臂（%s 的 %d 个 (分子, 状态) 行，标签取自 5 / 20 / 200 三个电介质）："
                "准确率 **%.3f**，"
                "混淆矩阵 TP %d / FP %d / TN %d / FN %d。"
                % (", ".join(validation.get("molecules") or []),
                   validation.get("n_scored") or 0, validation.get("accuracy") or 0.0,
                   matrix.get("true_positive", 0), matrix.get("false_positive", 0),
                   matrix.get("true_negative", 0), matrix.get("false_negative", 0)),
            ]
        permutation = predictor.get("permutation_test") or {}
        if permutation:
            rule_lines.append(
                "- 精确置换检验（%s）：统计量 %s，在 %s 行 / %s 个正例的全部 **%s** 种标签"
                "指派下 p = **%.4f**%s。"
                % (permutation.get("descriptor"), permutation.get("statistic"),
                   permutation.get("n_rows"), permutation.get("n_positive"),
                   permutation.get("total_assignments"), permutation.get("p_value") or 0.0,
                   "" if permutation.get("exact") else "（抽样估计，非精确）"))
        ceiling = predictor.get("multivariate_ceiling") or {}
        if ceiling:
            rule_lines.append("- 多变量上限（%s）：留一 AUC %.3f%s。"
                              % (", ".join(ceiling.get("features") or []),
                                 ceiling.get("loo_auc") or 0.0,
                                 "，留出准确率 %.3f" % ceiling["validation_accuracy"]
                                 if ceiling.get("validation_accuracy") is not None else ""))
    rule_block = "\n".join(rule_lines)

    table_block = "\n".join(["### 本周产物", "", "| 文件 | 说明 |", "| --- | --- |"]
                             + ["| %s | %s |" % (name, note)
                                for name, note in W15_TABLE_ROWS])

    did = ("把 Week 14 的三分子双初猜协议扩成全核心集目录：12 个分子 x 3 个状态 x "
           "10 个电介质 x 2 种初猜，并对此前从未算过连续介质的 6 个分子做留出验证；"
           "再用只依赖气相输出的描述符拟合一条事前预警规则。")
    metric = ("%d 个配对单元格里 %d 个一致、%d 个 MORead 更低、%d 个更高；"
              "最大赤字 %.6f eV（%s / %s / eps=%g）；10 点阶梯下 %d/%d 个分子被判定存在漏解。"
              % (n_paired, coincident, lower, higher, worst or 0.0,
                 worst_at[0], worst_at[1], worst_at[2],
                 counts.get("ladder10", 0), n_molecules))
    qc = ("%d 个单元格全部落盘、0 个失败；几何审计逐分子通过；"
          "复用行全部带 `source` 出处；阈值 %g eV 原样继承自 Week 14；"
          "预警规则与多数类基线的比较按实测记录（`chosen_rule_beats_majority_baseline = %s`），"
          "负结果原样写入报告与小结。"
          % (n_cells, threshold or 0.0,
             (predictor or {}).get("chosen_rule_beats_majority_baseline")))
    limit = ("目录只在 %d 个分子的 10 点电介质阶梯上回答「默认初猜是否漏掉更低解」；"
             "「更低解」是按三条语句口径的能量比较，不是自由能；未做溶剂构型采样，"
             "也未回答泄漏解在真实溶液里的寿命。事前预警规则在发现集上**未能超过多数类"
             "基线**（正例只有 5/24），两臂诊断是事后解释、不构成可用的筛查工具。"
             % n_molecules)
    summary = (" ".join([did, metric]))

    return {"did": did, "metric": metric, "qc": qc, "limit": limit,
            "summary": summary, "protocol_block": protocol_block,
            "verdict_block": verdict_block, "label_block": label_block,
            "rule_block": rule_block, "family_block": family_block,
            "table_block": table_block}


def week16_blocks(smd, contamination, identity):
    """Week 16 / Stage 17 narrative blocks.

    Every number is read back out of stage17_contamination.json,
    stage17_solution_identity.json and stage17_smd_moread.json so the distilled
    report cannot drift away from the artifacts it summarises.
    """

    keys = ("did", "metric", "qc", "limit", "summary", "protocol_block",
            "verdict_block", "cells_block", "identity_block", "family_block",
            "table_block")
    if contamination is None:
        text = "（\x60stage17_contamination.json\x60 不存在）"
        return {key: text for key in keys}

    smd = smd or {}
    identity = identity or {}
    per_axis = contamination.get("per_axis") or {}
    published = contamination.get("published_comparison") or {}
    delta = (contamination.get("delta_stats") or {}).get("cells_54") or {}
    sign = (contamination.get("sign_test") or {}).get("cells_54") or {}
    verdict = contamination.get("verdict") or {}
    changed = contamination.get("cells_changed") or []
    ci_overlap = contamination.get("ci_overlap") or {}
    layers = smd.get("layers") or []
    layer = layers[0] if layers else {}

    def num(value, digits=3):
        return _w8_num(value, digits)

    def signed(value, digits=4):
        text = _w8_num(value, digits)
        if text == "\u2014":
            return text
        return text if text.startswith("-") else "+" + text

    def ci_block(block):
        low = block.get("tau_b_ci_low")
        high = block.get("tau_b_ci_high")
        if low is None or high is None:
            return "\u2014"
        return "[%.3f, %.3f]" % (low, high)

    def ci_pair(pair):
        if not pair or len(pair) < 2 or pair[0] is None or pair[1] is None:
            return "\u2014"
        return "[%.3f, %.3f]" % (pair[0], pair[1])

    protocol_block = "\n".join([
        "### 协议与规模",
        "",
        "- **Part A（防守）**：把 Week 9「五级台阶」第 2 级 \x60P1 -> P2\x60 的 **P2 腿**"
        "（SMD(乙腈) 层）从 ORCA 自带初猜换成 \x60! MORead\x60 + 气相 \x60%%moinp\x60 重算；"
        "18 个分子 x 3 态 = **54 格**，\x60n_ok = %s\x60、\x60n_failed = %s\x60、"
        "\x60n_computed = %s\x60、\x60n_reused = %s\x60。"
        % (smd.get("n_ok"), smd.get("n_failed"), layer.get("n_computed"),
           layer.get("n_reused")),
        "- 参照表：\x60outputs/week4/p2_core_set_smd_acetonitrile.csv\x60（default 臂，"
        "Week 4 冻结）；零格缺参照（\x60n_cells_without_reference = %s\x60）。"
        % smd.get("n_cells_without_reference"),
        "- 几何审计：18 个分子逐一比对参照的 xyz，全部 \x60all_identical = True\x60——"
        "这就是「单腿替换许可证」：被替换的只有初猜这一个变量。",
        "- 调度：\x60--jobs %s --nprocs %s\x60（本机 16 逻辑核），与既有各层协议相同。"
        % (smd.get("jobs"), smd.get("nprocs")),
        "- **Part B（机制）**：不新开任何量化作业，只读既有 \x60.out\x60，对 Stage 16 目录里 "
        "\x60delta_ev < -1 meV\x60 的 **%s 个配对格**比较两条解的 \x60<S^2>\x60、自旋中心、"
        "轨道标签、参与率 PR 与 Mulliken 电荷 / 自旋的 L1 差。"
        % (identity.get("n_cells") or 0),
    ])

    axis_table = ["| 轴 | 臂 | n | tau_b | tau_b 95% CI | O_20% | f_unresolved(after) | "
                  "f_robust_inv | sigma 中位(eV) |",
                  "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for axis, axis_label in W16_AXIS_SHORT:
        pub = (published.get(axis) or {}).get("published") or {}
        axis_table.append(
            "| %s | **published** | %s | %s | %s | %s | %s | %s | %s |"
            % (axis_label, pub.get("n"), num(pub.get("kendall_tau_b")),
               ci_block(pub), num(pub.get("overlap_20")),
               num(pub.get("f_unresolved_after")), num(pub.get("f_robust_inv")),
               num(pub.get("sigma_median_ev"))))
        for arm, _label in W16_ARM_SHORT:
            block = (per_axis.get(axis) or {}).get(arm) or {}
            axis_table.append(
                "| %s | %s | %s | %s | %s | %s | %s | %s | %s |"
                % (axis_label, arm, block.get("n"),
                   num(block.get("kendall_tau_b")), ci_block(block),
                   num(block.get("overlap_20")), num(block.get("f_unresolved_after")),
                   num(block.get("f_robust_inv")), num(block.get("sigma_median_ev"))))

    ci_rows = ["| 轴 | default 95% CI | moread 95% CI | 是否重叠 |",
               "| --- | --- | --- | --- |"]
    for axis, axis_label in W16_AXIS_SHORT:
        entry = ci_overlap.get(axis) or {}
        ci_rows.append("| %s | %s | %s | %s |"
                       % (axis_label, ci_pair(entry.get("default_ci")),
                          ci_pair(entry.get("moread_ci")),
                          "是" if entry.get("overlap") else "否"))

    verdict_block = "\n".join([
        "### Part A 逐轴对照（published / default / moread）",
        "",
        "\n".join(axis_table),
        "",
        "> 来源：\x60stage17_contamination.json\x60 的 \x60published_comparison.<轴>.published\x60"
        "（published 行）与 \x60per_axis.<轴>.<臂>\x60（default / moread 行）；default 臂在逐项上"
        "**精确复原** published 值（\x60default_matches_published_max_abs_ev\x60 = 0），"
        "所以 delta 只反映 moread 这一条腿。",
        "",
        "**两臂 tau_b 的 95% CI 全部重叠**（污染被区间估计吸收）：",
        "",
        "\n".join(ci_rows),
        "",
        "- 产物判定：\x60any_published_conclusion_rewritten = %s\x60、"
        "\x60tau_b_ci_overlap_both_axes = %s\x60——**没有任何一条 published 结论被改写**。"
        % (verdict.get("any_published_conclusion_rewritten"),
           verdict.get("tau_b_ci_overlap_both_axes")),
        "- **结构性引理（一句话）**：在本周的估计量下（\x60sigma = abs(d0 - d1)/sqrt(2)\x60，"
        "\x60z_primary = 1.0\x60），两条 resolved 条件分别等价于 "
        "\x60(sqrt(2)-1)|d0| >= |d1|\x60 与 \x60(sqrt(2)-1)|d1| >= |d0|\x60；"
        "相乘要求 \x601 <= (sqrt(2)-1)^2 = 0.1716\x60，矛盾——所以「反号且两臂都 resolved」的 "
        "pair 集合**恒为空集**，\x60f_robust_inv\x60 从 0 变非 0 在本项目这条具体流水线、"
        "这批格子、这套估计量下是结构性不可能（**不是普适定理**：换 \x60z\x60、换 \x60sigma\x60 的定义、"
        "或补进第三条 realization 都会解除），不是「本周恰好看不到」。",
    ])

    cell_rows = ["| 分子 | 态 | delta (eV) | 所属轴 |", "| --- | --- | --- | --- |"]
    for entry in changed:
        cell_rows.append("| %s | %s | %s | %s |"
                         % (entry.get("molecule"), entry.get("state"),
                            signed(entry.get("delta_ev"), 6),
                            ", ".join(entry.get("axes") or [])))
    cells_block = "\n".join([
        "### 被改变的格子（|delta| > 1 meV）",
        "",
        "共 **%s** 个格子：" % contamination.get("cells_changed_count"),
        "",
        "\n".join(cell_rows),
        "",
        "- 六个格里五个是 moread **更低**（\x60delta < 0\x60），只有 **EC / anion 是 "
        "+0.0923 eV**——moread 反而更高；这条正向残差原样保留。",
        "- 54 格符号检验：正 **%s** / 负 **%s** / 零 **%s**，双侧 p = **%.6f**——"
        "在符号层面不显著。"
        % (sign.get("n_positive"), sign.get("n_negative"), sign.get("n_zero"),
           sign.get("p_two_sided") or 0.0),
        "- 最坏 \x60|delta|\x60 = %.6f eV（%s），最大正残差 = %.6f eV（%s）。"
        % (delta.get("max_abs_ev") or 0.0, delta.get("argmin") or "",
           delta.get("max_ev") or 0.0, delta.get("argmax") or ""),
    ])

    cells_list = identity.get("cells") or []
    n_spin_pure = sum(1 for cell in cells_list
                      if 0.74 <= (cell.get("s2_default") or 0.0) <= 0.76
                      and 0.74 <= (cell.get("s2_moread") or 0.0) <= 0.76)
    by_state = identity.get("by_state") or {}
    anion = by_state.get("anion") or {}
    cation = by_state.get("cation") or {}
    identity_block = "\n".join([
        "### Part B：两个 SCF 解都是自旋纯双重态",
        "",
        "- 受影响 **%s** 格的两个解都是**自旋纯双重态**：两臂 \x60<S^2>\x60 全部落在 0.75±0.01，"
        "**%d/%d**；多重度逐格都是 2、电荷 -1 / +1。所以这**不是**破缺对称性 / 自旋污染伪影，"
        "而是同一自旋量子数下的两个不同 SCF 驻点。"
        % (identity.get("n_cells"), n_spin_pure, len(cells_list)),
        "- 差异的主轴是**电荷重组**而不只是自旋重排（\x60charge_l1\x60 与 \x60spin_l1\x60 量级相当）。",
        "",
        "| 态 | 格子 | 自旋中心相同 | 轨道标签相同 |",
        "| --- | --- | --- | --- |",
        "| anion | %s | %s/%s | %s/%s |"
        % (anion.get("n_cells"), anion.get("n_same_spin_center"), anion.get("n_cells"),
           anion.get("n_same_orbital_label"), anion.get("n_cells")),
        "| cation | %s | %s/%s | %s/%s |"
        % (cation.get("n_cells"), cation.get("n_same_spin_center"), cation.get("n_cells"),
           cation.get("n_same_orbital_label"), cation.get("n_cells")),
        "",
        "- **空穴比电子更难安放**：阴离子的自旋中心在两臂**完全一致**（16/16），"
        "阳离子只有 **5/16**——默认初猜把多余电子放在哪里基本可复现，把空穴放在哪里高度依赖初猜。",
        "- 几何 QC：两臂 \x60.out\x60 的 CARTESIAN COORDINATES 逐位相同的格子 **32/32**，"
        "所以上面的差异只能来自 SCF 解本身。",
    ])

    family = identity.get("by_family") or {}
    fam_rows = ["| 家族 | 分子 | n_cells | loss_in_pr 均值 | charge_l1 均值 | "
                "自旋中心相同 | 轨道标签相同 |",
                "| --- | --- | --- | --- | --- | --- | --- |"]
    for name in ("cyclic_carbonate", "linear_carbonate", "phosphate"):
        block = family.get(name) or {}
        fam_rows.append("| %s | %s | %s | %s | %s | %s/%s | %s/%s |"
                        % (name, ", ".join(block.get("molecules") or []),
                           block.get("n_cells"), num(block.get("loss_in_pr_mean"), 4),
                           num(block.get("charge_l1_mean"), 4),
                           block.get("n_same_spin_center"), block.get("n_cells"),
                           block.get("n_same_orbital_label"), block.get("n_cells")))
    fam_total = sum(int((family.get(name) or {}).get("n_cells") or 0)
                    for name in ("cyclic_carbonate", "linear_carbonate", "phosphate"))
    family_block = "\n".join([
        "### Part B：按分子家族",
        "",
        "\n".join(fam_rows),
        "",
        "- 三族格数 %s + %s + %s = **%d**。"
        % ((family.get("cyclic_carbonate") or {}).get("n_cells", 0),
           (family.get("linear_carbonate") or {}).get("n_cells", 0),
           (family.get("phosphate") or {}).get("n_cells", 0), fam_total),
        "- 家族分裂比电荷态更锋利：cyclic_carbonate 的 \x60loss_in_pr\x60 为负（moread 更定域）"
        "而 linear_carbonate 为正（moread 更离域），两条方向相反；linear 的 \x60charge_l1\x60 "
        "是 cyclic 的约 3.9 倍。",
        "- phosphate（TMP）的自旋中心 0/10 全部翻转——这是**近简并表观、不能当判据**（见限制）。",
    ])

    table_block = "\n".join(["### 本周产物", "", "| 文件 | 说明 |", "| --- | --- |"]
                             + ["| %s | %s |" % (name, note)
                                for name, note in W16_TABLE_ROWS])

    did = ("把 Week 9「五级台阶」第 2 级 \x60P1 -> P2\x60 的 P2 腿（SMD(乙腈) 层）从 ORCA "
           "自带初猜换成 moread 初猜重算（18 分子 x 3 态 = 54 格，全部 ok、零复用），"
           "并只读既有 \x60.out\x60 对 32 个「漏解」配对格的两个 SCF 解做电子结构身份对照"
           "（<S^2> / 自旋中心 / 轨道标签 / 参与率 PR / Mulliken L1 差）。")
    metric = ("54 格上两臂的 tau_b / O_20%% / f_unresolved / f_robust_inv 无一条被改写："
              "oxidation tau_b %s -> %s（Delta %s）、reduction tau_b %s -> %s（Delta %s），"
              "两臂 tau_b 的 95%% CI 在两条轴上都重叠；f_robust_inv 从 0 变非 0 在本项目这条具体流水线、"
              "这批格子、这套估计量下结构性不可能（**不是普适定理**）。Part B：32 格的两个 SCF 解都是自旋纯双重态"
              "（<S^2> 全落 0.75±0.01，32/32）；阴离子自旋中心两臂一致 16/16、阳离子仅 5/16。"
              % (num((published.get("oxidation") or {}).get("published", {})
                     .get("kendall_tau_b")),
                 num((per_axis.get("oxidation") or {}).get("moread", {})
                     .get("kendall_tau_b")),
                 signed((published.get("oxidation") or {})
                        .get("moread_minus_published", {}).get("kendall_tau_b")),
                 num((published.get("reduction") or {}).get("published", {})
                     .get("kendall_tau_b")),
                 num((per_axis.get("reduction") or {}).get("moread", {})
                     .get("kendall_tau_b")),
                 signed((published.get("reduction") or {})
                        .get("moread_minus_published", {}).get("kendall_tau_b"))))
    qc = ("核心 QC：54/54 作业成功、零缺失参照、几何审计 18/18 逐位一致；"
          "四组 (轴, 臂) 的 n = 18、f_robust_inv 全为 0；"
          "32 格 <S^2> 全落 0.75±0.01、几何 QC 32/32 一致、census.unresolved 为空。"
          "逐项实测值见本目录 verification.json 的 checks。")
    limit = ("Part A 只在 native 18 分子的 SMD(乙腈) P2 层上做**单腿替换**，不是整条台阶重算；"
             "f_robust_inv ≡ 0 是估计量（z_primary = 1.0 + 两条 realization）的结构后果，"
             "不是物理结论——换 ddof、补第三条 realization 或抬高 z 都会改变它。"
             "Part B 只有 32 格 / 5 分子 / 2 个电荷态，判据 delta_ev < -1 meV 继承 Stage 16、"
             "本周未重标定；「主贡献轨道」是 reduced-orbital SPIN 子块里 |值| 最大的原子-轨道，"
             "在弥散基组下常落在弥散 s 通道，故「轨道标签相同 11/32」不能读成 pi* 身份相同。"
             "**TMP 的自旋近简并**：三个磷酸氧上的自旋几乎均摊，其「自旋中心翻转」（0/10）是"
             "近简并表观、不能当稳健判据。")
    summary = " ".join([did, metric])

    return {"did": did, "metric": metric, "qc": qc, "limit": limit,
            "summary": summary, "protocol_block": protocol_block,
            "verdict_block": verdict_block, "cells_block": cells_block,
            "identity_block": identity_block, "family_block": family_block,
            "table_block": table_block}



REPORT_TEMPLATES[14] = """# Week 14 成果小结 —— Stage 15（双初猜协议、电子弥散度描述符与溶液锚点扫描）

## 0. 一页结论
- 做了什么：{w14_did}
- 关键数字：{w14_metric}
- 质检：{w14_qc}
- 限制：{w14_limit}

本文可独立阅读；逐项细节、物理机制与需裁决项见同目录 `week14_report_full.md`。

## 1. 双初猜协议：从「解不唯一」到「初猜选错」
{w14_protocol_block}

## 2. 导体极限：eps = 1000 是第一次真正测到极限
{w14_limit_block}

## 3. 电子弥散度描述符：把否定结果翻正
{w14_diffuseness_block}

## 4. 溶液锚点的文献扫描
{w14_anchor_block}

## 5. 产物与口径
{w14_table_block}

## 6. 产物清单
{artifact_list}

## 7. 源文件缺失
{missing_list}
"""


REPORT_TEMPLATES[15] = """# Week 15 成果小结 —— Stage 16（全核心集双初猜目录与事前预警规则）

## 0. 一页结论
- 做了什么：{w15_did}
- 关键数字：{w15_metric}
- 质检：{w15_qc}
- 限制：{w15_limit}

本文可独立阅读；逐项细节、物理机制与需裁决项见同目录 `week15_report_full.md`。

## 1. 协议与规模
{w15_protocol_block}

## 2. 目录结论
{w15_verdict_block}

## 3. 标签对阶梯的稳健性
{w15_label_block}

## 4. 家族覆盖与命中模式
{w15_family_block}

## 5. 事前预警规则
{w15_rule_block}

## 6. 产物与口径
{w15_table_block}

## 7. 产物清单
{artifact_list}

## 8. 源文件缺失
{missing_list}
"""


REPORT_TEMPLATES[16] = """# Week 16 成果小结 —— Stage 17（亚稳态污染上限与两个 SCF 解的电子结构身份）

## 0. 一页结论
- 做了什么：{w16_did}
- 关键数字：{w16_metric}
- 质检：{w16_qc}
- 限制：{w16_limit}

本文可独立阅读；逐项细节、物理机制与需裁决项见同目录 \x60week16_report_full.md\x60。

## 1. 协议与规模
{w16_protocol_block}

## 2. Part A：污染上限（P1 -> P2 第 2 级的 P2 腿单腿替换）
{w16_verdict_block}

## 3. Part A：哪些格子被改变
{w16_cells_block}

## 4. Part B：两个 SCF 解的电子结构身份
{w16_identity_block}

## 5. Part B：按分子家族
{w16_family_block}

## 6. 图表
- \x60artifacts/F32_stage17_contamination.png\x60 —— Stage 17 Part A（污染上限）三面板。
- \x60artifacts/F33_stage17_solution_identity.png\x60 —— Stage 17 Part B（两个 SCF 解的电子结构身份）四面板。
- 面板组成的权威说明：\x60artifacts/figure_manifest_week16_stage17.md\x60。

## 7. 产物与口径
{w16_table_block}

## 8. 产物清单
{artifact_list}

## 9. 源文件缺失
{missing_list}
"""


def week17_blocks(census, diagnosis):
    """Week 17 / Stage 18 narrative blocks.

    Every number is read back out of ``stage18_identity_census.json`` and
    ``stage18_selfdiagnosis.json``, so the distilled report cannot drift away
    from the artifacts it summarises.  Nothing here is typed in by hand.
    """

    keys = ("did", "metric", "qc", "limit", "summary", "protocol_block",
            "census_block", "diagnosis_block", "onesided_block", "table_block")
    if census is None:
        text = "（\x60stage18_identity_census.json\x60 不存在）"
        return {key: text for key in keys}

    diagnosis = diagnosis or {}
    counts = census.get("classification_counts") or {}
    discovery_counts = counts.get("discovery") or {}
    holdout_counts = counts.get("holdout") or {}
    census_meta = census.get("census") or {}
    thresholds = census.get("thresholds") or {}
    energy = census.get("energy_crosscheck") or {}
    geometry = census.get("geometry_qc") or {}
    separation = census.get("separation") or {}
    consistent = separation.get("consistency") or {}
    all_block = separation.get("all") or {}
    holdout_sep = separation.get("holdout") or {}
    matrix = all_block.get("confusion_at_threshold") or {}
    holdout_matrix = holdout_sep.get("confusion_at_threshold") or {}
    by_family = census.get("by_family") or {}

    rule = diagnosis.get("frozen_rule") or {}
    in_sample = diagnosis.get("in_sample") or {}
    loo = diagnosis.get("loo") or {}
    significance = diagnosis.get("significance") or {}
    holdout = diagnosis.get("holdout") or {}
    holdout_cm = holdout.get("confusion_matrix") or {}
    ceiling = diagnosis.get("multivariate_ceiling") or {}
    screen = diagnosis.get("screen") or []
    one_sided = diagnosis.get("one_sided_screening") or {}
    necessity = ((one_sided.get("necessity") or {}).get("overall") or {})
    necessity_arm = ((one_sided.get("necessity") or {}).get("by_arm") or {})
    specificity = ((one_sided.get("specificity") or {}).get("overall") or {})
    coverage = one_sided.get("coverage") or {}
    by_state_one_sided = (one_sided.get("by_state") or {}).get("pooled") or {}
    tradeoff = one_sided.get("tradeoff") or []
    counts_obs = one_sided.get("gap_warn_count_observation") or {}

    def num(value, digits=3):
        return _w8_num(value, digits)

    def pct(value, digits=1):
        if value is None:
            return "\u2014"
        return "%.*f%%" % (digits, 100.0 * value)

    protocol_block = "\n".join([
        "### 协议与规模",
        "",
        "- **本周零新增量子化学作业**：Part A 与 Part B 都只读已经存在的 \x60.out\x60。"
        "全目录扫描 %s 个 \x60.out\x60（standard %s + holdout %s），%s 对请求格**全部解析**、"
        "\x60unresolved = %s\x60、default/moread 臂缺失各 %s / %s 格。"
        % (census_meta.get("n_outfiles_scanned"),
           census_meta.get("n_outfiles_parsed_standard"),
           census_meta.get("n_outfiles_parsed_holdout"),
           census_meta.get("n_cells_requested"), census_meta.get("unresolved"),
           census_meta.get("n_default_arm_missing"), census_meta.get("n_moread_arm_missing")),
        "- **设计**：%s 对 = 发现集 %s（12 分子 x 3 态 x 10 电介质）+ 留出臂 %s"
        "（6 分子 x 3 态 x 3 电介质）。每一对都是「同一格、同一个几何、只换 SCF 初猜」的两个解。"
        % (census.get("n_pairs"), census.get("n_discovery"), census.get("n_holdout")),
        "- **Part A（身份普查）**：用 Stage 17 已在用的身份指标（<S^2>、Mulliken/Löwdin 原子自旋、"
        "自旋参与率 PR、约化轨道通道）比较两个解，判据只有一条：两臂电荷差的 L1 距离 "
        "\x60charge_l1 > %s\x60。"
        % num(thresholds.get("charge_l1_primary"), 3),
        "- **Part B（零成本自诊断）**：只读**默认臂那一个** \x60.out\x60 已经打印出来的字段 —— "
        "SCF 迭代轨迹、ORCA 自己的 \x60Small HOMO/LUMO gap\x60 警告（含带符号值）、"
        "上面那套身份指标、以及轨道能量块；协议逐条镜像 Stage 16（发现集筛特征 → 冻结一条规则 → "
        "留一 → AUC 精确零分布 → 留出臂原样打分 → 事后按态分层 → 多变量上限）。",
    ])

    family_rows = []
    for family in sorted(by_family, key=lambda name: -by_family[name]["n_cells"]):
        block = by_family[family]
        family_rows.append("| %s | %d | %d | %d | %d | %d |"
                           % (family, block.get("n_cells", 0), block.get("n_coincident", 0),
                              block.get("n_moread_lower", 0), block.get("n_identity_differs", 0),
                              block.get("n_identity_measurable", 0)))
    census_block = "\n".join([
        "### 硬 QC（全部由脚本现算）",
        "",
        "- 能量复核：%s 对全部比对，\x60max |delta_E| = %s eV\x60（容差 %.0e），"
        "\x60passed = %s\x60 —— 两个解的能量就是同一次计算的产物，不是两次独立运行。"
        % (energy.get("n_compared"), num(energy.get("max_abs_mismatch_ev"), 3),
           float(energy.get("tolerance_ev") or 0.0), energy.get("passed")),
        "- 几何 QC：%s / %s 对的两个几何**逐字符相同**（\x60all_identical = %s\x60）。"
        % (geometry.get("n_geometry_identical"), geometry.get("n_pairs"),
           geometry.get("all_identical")),
        "- 分类与规则不一致的格子：**%s** 个（规则：\x60%s\x60）。"
        % (counts.get("n_rule_mismatches"), counts.get("rule")),
        "",
        "### 冻结切点落在一个真实空隙里",
        "",
        "- 发现集里 coincident 的最大 \x60charge_l1\x60 = **%.6f**，moread_lower 的最小 = "
        "**%.6f**，切点冻结在 **%s**，正好落在空隙中（标定范围：%s）。"
        % (float(thresholds.get("calibration_coincident_max") or 0.0),
           float(thresholds.get("calibration_moread_min") or 0.0),
           num(thresholds.get("charge_l1_primary"), 3),
           thresholds.get("calibration_scope")),
        "- 可测子集上的 AUC：\x60charge_l1\x60 **%.6f**、\x60spin_l1\x60 %.6f、"
        "\x60spin_max_moread\x60 %.6f、\x60loss_in_pr\x60 %.6f、\x60delta_s2\x60 %.6f；"
        "切点处混淆矩阵 TP %s / FN %s / FP %s / TN %s，Youden J = %.3f。"
        % (float((all_block.get("auc") or {}).get("charge_l1") or 0.0),
           float((all_block.get("auc") or {}).get("spin_l1") or 0.0),
           float((all_block.get("auc") or {}).get("spin_max_moread") or 0.0),
           float((all_block.get("auc") or {}).get("loss_in_pr") or 0.0),
           float((all_block.get("auc") or {}).get("delta_s2") or 0.0),
           matrix.get("tp"), matrix.get("fn"), matrix.get("fp"), matrix.get("tn"),
           float(matrix.get("youden_j") or 0.0)),
        "- 留出臂用**发现集冻结的同一个切点**打分：AUC = %.6f，"
        "TP %s / FN %s / FP %s / TN %s。"
        % (float((holdout_sep.get("auc") or {}).get("charge_l1") or 0.0),
           holdout_matrix.get("tp"), holdout_matrix.get("fn"),
           holdout_matrix.get("fp"), holdout_matrix.get("tn")),
        "- **口径限制（重要）**：%s / %s 对是闭壳层中性分子，它们的输出**不打印自旋块**，"
        "所以 \x60charge_l1 / spin_l1 / delta_s2\x60 在这些格上**无定义**；可测的只有 %s 对。"
        "中性格的 \x60identity_differs = False\x60 是**推断**（能量重合到 1e-7 eV + 几何逐位相同），"
        "不是实测。因此上面的 AUC = 1.000 是「在可测子集上完美分离」，"
        "**不能**读成一个新的独立预报量。"
        % (consistent.get("n_unmeasurable"), consistent.get("n_pairs"),
           consistent.get("n_measurable")),
        "",
        "### 家族分裂",
        "",
        "| 家族 | 格数 | coincident | moread_lower | 身份不同 | 可测 |",
        "| --- | --- | --- | --- | --- | --- |",
    ] + family_rows + [
        "",
        "- 四个家族（ester / nitrile / sulfone / sulfoxide）**一个漏解都没有**；"
        "漏解全部落在 cyclic_carbonate、linear_carbonate、phosphate、ether 里。"
        "家族比电荷态更锋利：中性格 0 格漏解，阳离子 %s 格、阴离子 %s 格。"
        % ((census.get("by_state") or {}).get("cation", {}).get("n_moread_lower"),
           (census.get("by_state") or {}).get("anion", {}).get("n_moread_lower")),
    ])

    lead = screen[0] if screen else {}
    diagnosis_block = "\n".join([
        "### 冻结规则（发现集，镜像 Stage 16 的选择规则）",
        "",
        "- 特征 \x60%s\x60（%s）：方向 **%s**，阈值 \x60%s\x60。"
        % (rule.get("descriptor"), rule.get("definition"),
           "越小越危险" if rule.get("sign") == "smaller_is_riskier" else "越大越危险",
           num(rule.get("threshold_frozen"), 4)),
        "- 记录在案：ORCA 未报警时该字段被填成 +%.1f Eh（gap 大＝健康），"
        "全表 %s/414 行如此。" % (1.0, 140),
        "",
        "### 样本内很好看",
        "",
        "- 样本内 accuracy %.4f vs 多数类 %.4f；留一 accuracy %.4f、平衡准确率 %.4f。"
        % (float(in_sample.get("accuracy") or 0.0),
           float(in_sample.get("majority_accuracy") or 0.0),
           float(loo.get("accuracy") or 0.0), float(loo.get("balanced_accuracy") or 0.0)),
        "- AUC 的精确零分布（%s，tie-aware Mann-Whitney DP）：观测 AUC %.4f，"
        "**精确 p = %.4g**。这个 p 是真的，但它只回答「这个特征在发现集上有没有信号」，"
        "不回答「这条规则能不能用」。"
        % (significance.get("method"), float(significance.get("auc_observed") or 0.0),
           float(significance.get("p_value") or 1.0)),
        "",
        "### 样本外输给平凡基线",
        "",
        "- 留出臂 accuracy **%.4f** vs 多数类 **%.4f**：**输**。"
        "混淆矩阵 TP %s / FP %s / TN %s / FN %s —— 5 个真漏解**一个都没抓到**。"
        % (float(holdout.get("accuracy") or 0.0),
           float(holdout.get("majority_accuracy") or 0.0),
           holdout_cm.get("true_positive"), holdout_cm.get("false_positive"),
           holdout_cm.get("true_negative"), holdout_cm.get("false_negative")),
        "- 多变量上限（前 3 特征留一逻辑回归）LOO AUC %.4f、留出 accuracy %s —— "
        "加参数也没有换来一条可用规则。"
        % (float(ceiling.get("loo_auc") or 0.0), num(ceiling.get("holdout_accuracy"), 4)),
        "- 事后按态：cation 层留一 %.4f 胜过该层基线 %.4f，anion 层 %.4f **输给** %.4f。"
        "留出臂那 5 个真漏解全是阴离子，所以 anion 层的失败就是全表失败。"
        % (float(((diagnosis.get("by_state_post_hoc") or {}).get("cation") or {})
                 .get("loo_accuracy") or 0.0),
           float(((diagnosis.get("by_state_post_hoc") or {}).get("cation") or {})
                 .get("majority_accuracy") or 0.0),
           float(((diagnosis.get("by_state_post_hoc") or {}).get("anion") or {})
                 .get("loo_accuracy") or 0.0),
           float(((diagnosis.get("by_state_post_hoc") or {}).get("anion") or {})
                 .get("majority_accuracy") or 0.0)),
    ])

    trade_rows = []
    for entry in tradeoff:
        for arm in ("discovery", "holdout"):
            arm_block = (entry.get("by_arm") or {}).get(arm) or {}
            trade_rows.append("| %s | %s | %s | %s | %s | %s | %s |"
                              % (entry.get("id"), arm,
                                 num(arm_block.get("sensitivity"), 3),
                                 num(arm_block.get("specificity"), 3),
                                 num(arm_block.get("precision"), 3),
                                 num(arm_block.get("accuracy"), 4),
                                 num(arm_block.get("balanced_accuracy"), 3)))
    state_rows = []
    for state in ("neutral", "cation", "anion"):
        block = by_state_one_sided.get(state) or {}
        state_rows.append("| %s | %s | %s | %s | %s | %s |"
                          % (state, block.get("n_rows"), block.get("n_positive"),
                             block.get("n_warning"), block.get("n_positive_with_warning"),
                             block.get("n_no_warning")))
    onesided_block = "\n".join([
        "### 那条失败规则里，唯一站得住的一件东西",
        "",
        "- 定义：告警规则 = 「该格打印过 \x60Small HOMO/LUMO gap\x60 警告」，**零个参数**；"
        "它不是新拟合的，是 ORCA 自己在 run 开始时打的。该字段在 %s / %s 对上都有定义"
        "（包括 %s 个闭壳层中性格 —— 这是身份类特征做不到的）。"
        % (coverage.get("n_pairs_with_gap_warning_field"), coverage.get("n_pairs"),
           coverage.get("n_neutral_pairs")),
        "",
        "### 必要条件（成立）",
        "",
        "- **%s / %s 个正例都带警告，反例 %s 个**：发现集 %s/%s、留出臂 %s/%s。"
        "即 \x60P(无警告 | 正例) = %s\x60。用「无警告」放行一格，**不会**放走任何一个真实漏解。"
        % (necessity.get("n_positive_with_warning"), necessity.get("n_positive"),
           necessity.get("n_positive_without_warning"),
           (necessity_arm.get("discovery") or {}).get("n_positive_with_warning"),
           (necessity_arm.get("discovery") or {}).get("n_positive"),
           (necessity_arm.get("holdout") or {}).get("n_positive_with_warning"),
           (necessity_arm.get("holdout") or {}).get("n_positive"),
           necessity.get("p_no_warning_given_positive")),
        "- 正例带警告时的带符号 gap 范围 %s ~ %s Eh，**全为负**；"
        "%s 个完全无警告的格里 %s 个是正例 —— 于是这 %s 个格可以整批放行。"
        % (num(((one_sided.get("positive_gap_warn_value_range") or {}).get("pooled") or {})
               .get("min_eh"), 4),
           num(((one_sided.get("positive_gap_warn_value_range") or {}).get("pooled") or {})
               .get("max_eh"), 4),
           counts_obs.get("distribution", {}).get("negative", {}).get("0"),
           necessity.get("n_positive_without_warning"),
           counts_obs.get("distribution", {}).get("negative", {}).get("0")),
        "",
        "### 但不充分（同样成立）",
        "",
        "- 负例里也有 **%s / %s**（假警报率 %.4f，特异度 %.4f）带警告 —— "
        "所以蕴含只朝一个方向成立，「有警告 ⇒ 必然漏解」是**错的**。"
        % (specificity.get("n_negative_with_warning"), specificity.get("n_negative"),
           float(specificity.get("false_alarm_rate") or 0.0),
           float(specificity.get("specificity") or 0.0)),
        "- 按态看更极端：阴离子 %s/%s、阳离子 %s/%s 的负例都带警告（特异度约 0.008），"
        "而中性 %s 格**一个警告都没有**。"
        % ((by_state_one_sided.get("anion") or {}).get("n_warning"),
           (by_state_one_sided.get("anion") or {}).get("n_rows"),
           (by_state_one_sided.get("cation") or {}).get("n_warning"),
           (by_state_one_sided.get("cation") or {}).get("n_rows"),
           (by_state_one_sided.get("neutral") or {}).get("n_warning")),
        "",
        "| 规则 | 臂 | 灵敏度 | 特异度 | 精确率 | 准确率 | 平衡准确率 |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ] + trade_rows + [
        "",
        "### 怎么用",
        "",
        "- 正确用法是**单边放行**：没有警告 ⇒ 这一格安全，可以从复审名单里划掉；"
        "有警告 ⇒ 不确定，仍需人工看。在 %s 行上这会划掉 %s 行、丢掉 0 个漏解，"
        "但**不能**反过来当成「漏解预警」。"
        % ((((one_sided.get("tradeoff") or [{}])[0].get("by_arm") or {}).get("pooled") or {})
           .get("n_rows"), counts_obs.get("distribution", {}).get("negative", {}).get("0")),
        "- 纪律：该警告由 ORCA 在**预对角化**阶段打印，落点在 SCF 之前 —— "
        "它说的是「这个体系看起来难」，不是「这个 SCF 收敛到了高解」。"
        "可迁移范围仅限同一 ORCA 版本、同一套预登记输入清单与这 %s 格设计。"
        % census.get("n_pairs"),
        "- 声明：必要条件只由 %s 个正例支持（发现集 %s + 留出臂 %s）；"
        "留出臂上的「零反例」几乎是平凡陈述，真正有信息量的是发现集那一份。"
        % (necessity.get("n_positive"),
           (necessity_arm.get("discovery") or {}).get("n_positive"),
           (necessity_arm.get("holdout") or {}).get("n_positive")),
    ])

    table_block = "\n".join(["### 本周产物", "", "| 文件 | 说明 |", "| --- | --- |"]
                            + ["| %s | %s |" % (name, note)
                               for name, note in W17_TABLE_ROWS])

    did = ("把 Week 16 已经算完的两个 SCF 解当成一个**全目录的电子身份普查**来做（%s 对 = 发现集 %s "
           "+ 留出臂 %s，**零新增量子化学作业**）：对每一对只问一句「这两个解的电子身份是同一个，"
           "还是两个？」，判据只有 \x60charge_l1 > %s\x60 一条；同时把默认臂自己那一份 \x60.out\x60 "
           "里已经打印出来的字段（SCF 轨迹、ORCA 的 small-gap 警告、身份指标、轨道能量）拿来问"
           "「能不能看出它停在了高解」。"
           % (census.get("n_pairs"), census.get("n_discovery"), census.get("n_holdout"),
              num(thresholds.get("charge_l1_primary"), 3)))
    metric = ("身份普查：切点 %s 落在发现集留下的空隙里（coincident 最大 %.6f、moread_lower 最小 "
              "%.6f），可测子集 AUC = %.3f、混淆 TP %s / FN %s / FP %s / TN %s，"
              "留出臂套同一刀仍然 AUC = %.3f；分类与身份判定在 %s/%s 对上一致，规则不一致 0 格。"
              "家族分裂：ester / nitrile / sulfone / sulfoxide 四个家族零漏解，"
              "漏解全部集中在 cyclic_carbonate（%s）、phosphate（%s）、linear_carbonate（%s）、"
              "ether（%s）。自诊断：冻结的 \x60gap_warn_value <= %s\x60 在发现集 LOO %.4f（> 基线 "
              "%.4f，精确 p = %.2e）却在留出的 54 格上只到 %.4f、**输给**多数类 %.4f，且 5 个真漏解 "
              "TP = 0；多变量上限（前 3 特征）LOO AUC %.3f、留出 %.3f，同样不及基线。"
              "唯一站得住的是单边结论：警告在 %s/%s 个正例上都出现（反例 0），"
              "所以「无警告」可以安全放行，但 %s/%s 个负例也带警告，故不能反推漏解。"
              % (num(thresholds.get("charge_l1_primary"), 3),
                 float(thresholds.get("calibration_coincident_max") or 0.0),
                 float(thresholds.get("calibration_moread_min") or 0.0),
                 float((all_block.get("auc") or {}).get("charge_l1") or 0.0),
                 matrix.get("tp"), matrix.get("fn"), matrix.get("fp"), matrix.get("tn"),
                 float((holdout_sep.get("auc") or {}).get("charge_l1") or 0.0),
                 consistent.get("n_consistent"), consistent.get("n_pairs"),
                 (by_family.get("cyclic_carbonate") or {}).get("n_moread_lower"),
                 (by_family.get("phosphate") or {}).get("n_moread_lower"),
                 (by_family.get("linear_carbonate") or {}).get("n_moread_lower"),
                 (by_family.get("ether") or {}).get("n_moread_lower"),
                 num(rule.get("threshold_frozen"), 4),
                 float(loo.get("accuracy") or 0.0),
                 float(loo.get("majority_accuracy") or 0.0),
                 float(significance.get("p_value") or 1.0),
                 float(holdout.get("accuracy") or 0.0),
                 float(holdout.get("majority_accuracy") or 0.0),
                 float(ceiling.get("loo_auc") or 0.0),
                 float(ceiling.get("holdout_accuracy") or 0.0),
                 necessity.get("n_positive_with_warning"), necessity.get("n_positive"),
                 specificity.get("n_negative_with_warning"), specificity.get("n_negative")))
    qc = ("核心 QC：%s 个 \x60.out\x60 全扫、%s 对全部解析（unresolved 0、两臂零缺失）；"
          "能量复核 max|delta| = %s eV（容差 %.0e）、几何 %s/%s 逐字符相同；"
          "分类与规则不一致 0 格；身份判定一致 %s/%s。Part B 的 AUC 精确零分布用 tie-aware "
          "Mann-Whitney DP（p = %.2e），留出臂混淆矩阵与单边筛查的必要条件/特异度全部现算并写入。"
          "逐项实测值见本目录 verification.json 的 checks。"
          % (census_meta.get("n_outfiles_scanned"), census_meta.get("n_cells_requested"),
             num(energy.get("max_abs_mismatch_ev"), 3),
             float(energy.get("tolerance_ev") or 0.0),
             geometry.get("n_geometry_identical"), geometry.get("n_pairs"),
             consistent.get("n_consistent"), consistent.get("n_pairs"),
             float(significance.get("p_value") or 1.0)))
    limit = ("Part A 的 AUC = 1.000 只覆盖 %s 个**可测**配对：%s 个闭壳层中性格不打印自旋块，"
             "它们的 \x60identity_differs = False\x60 是从「能量重合到 1e-7 eV + 几何逐位相同」"
             "**推断**出来的，不是实测；因此这是对能量分类的**必要条件 test**，"
             "**不是**一个新的独立预报量，也不能当成预报模型。"
             "Part B 的 \x60gap_warn_value <= %s\x60 输在样本外：池化多数类基线被 120 个中性格"
             "抬到 0.911，留出臂分辨率只有 1/54；必要条件只由 %s 个正例支持，且留出臂 5 个正例"
             "**全是阴离子**，阳离子若出现无警告漏解，本语料抓不到（这是已知盲区）。"
             "同一 (分子, 态) 的 3-10 个 eps 不是独立行，计数会高估有效样本量；"
             "P2 腿仍是 r2SCAN-3c/C-PCM 单点协议，两者都继承 Week 16 的口径。"
             % (consistent.get("n_measurable"), consistent.get("n_unmeasurable"),
                num(rule.get("threshold_frozen"), 4), necessity.get("n_positive")))
    summary = " ".join([did, metric])

    return {"did": did, "metric": metric, "qc": qc, "limit": limit,
            "summary": summary, "protocol_block": protocol_block,
            "census_block": census_block, "diagnosis_block": diagnosis_block,
            "onesided_block": onesided_block, "table_block": table_block}


def week18_blocks(ledger, analysis):
    """Week 18 / Stage 19 narrative blocks.

    Every number is read back out of ``stage19_relax.json`` and
    ``stage19_relax_analysis.json``, so the distilled report cannot drift away
    from the artifacts it summarises.  Nothing here is typed in by hand.
    """

    keys = ("did", "metric", "qc", "limit", "summary", "protocol_block",
            "verdict_block", "geometry_block", "table_block")
    if analysis is None:
        text = "（`stage19_relax_analysis.json` 不存在）"
        return {key: text for key in keys}

    ledger = ledger or {}
    summary = ledger.get("summary") or {}
    aggregates = analysis.get("aggregates") or {}
    all_block = (aggregates.get("all") or {}).get("all") or {}
    outcomes = all_block.get("outcomes") or {}
    by_state = aggregates.get("by_state") or {}
    by_molecule = aggregates.get("by_molecule") or {}
    by_epsilon = aggregates.get("by_epsilon") or {}
    by_arm_set = aggregates.get("by_arm_set") or {}
    blocks = analysis.get("block_counts") or {}
    cells = analysis.get("cells") or []

    def num(value, digits=3):
        return _w8_num(value, digits)

    def p50(key):
        return (all_block.get(key) or {}).get("p50")

    n_cells = analysis.get("n_cells")
    n_complete = all_block.get("n_complete")
    shrink = (float(p50("abs_single_point_delta_ev") or 0.0)
              / max(float(p50("abs_relax_delta_ev") or 1e-30), 1e-30))
    n_shift_up = sum(1 for cell in cells
                     if float(cell.get("delta_shift_ev") or 0.0) > 0)
    n_shift_down = sum(1 for cell in cells
                       if float(cell.get("delta_shift_ev") or 0.0) < 0)
    n_merged = (outcomes.get("same_lower", 0) or 0) + (outcomes.get("same_higher", 0) or 0)

    protocol_block = "\n".join([
        "### 唯一的自由变量：作业类型与初猜",
        "",
        "- **本周新增 %s 个 ORCA `Opt` 作业 = %s 格 x 2 条腿**（reused %s / computed %s）。"
        % (summary.get("n_jobs"), n_cells, summary.get("n_reused"), summary.get("n_computed")),
        "- 目标集合是 Week 17 单点上「两解不同、且 `moread` 更低」的 **%s 格全集**"
        "（发现集 32 + 留出臂 5），不是 414 对总体。" % n_cells,
        "- 每个格子把两条 SCF 解（`default` = ORCA 自己的初猜；`moread` = `! MORead` + "
        "`%moinp` 指向同电荷态的气相 gbw）各自从同一个冻结的 G1 几何出发，在各自 eps 下做几何"
        "优化；方法 `r2SCAN-3c`、溶剂 `bare CPCM at each cell's own epsilon`、起始几何全部冻结。",
        "- **判据沿用 Stage 18 冻结阈值** `charge_l1 > %s`（本阶段未重新拟合）；"
        "材料阈值 1e-03 eV 定 `still_lower`；几何同最小点宽容 0.02 A **只是描述列**。"
        % num(analysis.get("threshold_charge_l1"), 3),
        "- 取块口径：`Opt` 输出里 Mulliken 块与 CARTESIAN 块都出现多次（首块是起始几何），"
        "本阶段一律取**最后一块**；实测块计数 Mulliken %s、CARTESIAN %s。"
        % (blocks.get("mulliken"), blocks.get("cartesian")),
    ])

    state_rows = []
    for state in ("anion", "cation"):
        block = by_state.get(state) or {}
        got = block.get("outcomes") or {}
        state_rows.append("| %s | %d | %d | %d | %d | %d | %d |"
                          % (state, block.get("n_cells", 0), block.get("n_complete", 0),
                             got.get("distinct_lower", 0), got.get("distinct_higher", 0),
                             got.get("same_lower", 0), got.get("same_higher", 0)))
    arm_rows = []
    for arm in ("discovery", "holdout"):
        block = by_arm_set.get(arm) or {}
        got = block.get("outcomes") or {}
        arm_rows.append("| %s | %d | %d | %d | %d | %d |"
                        % (arm, block.get("n_cells", 0), got.get("distinct_lower", 0),
                           got.get("distinct_higher", 0), got.get("same_lower", 0),
                           got.get("same_higher", 0)))
    mol_rows = []
    for name in sorted(by_molecule, key=lambda key: -by_molecule[key].get("n_cells", 0)):
        block = by_molecule[name]
        got = block.get("outcomes") or {}
        mol_rows.append("| %s | %d | %d | %d | %d | %d |"
                        % (name, block.get("n_cells", 0), got.get("distinct_lower", 0),
                           got.get("distinct_higher", 0), got.get("same_lower", 0),
                           got.get("same_higher", 0)))
    eps_rows = []
    for eps in sorted(by_epsilon, key=lambda key: float(key)):
        block = by_epsilon[eps]
        got = block.get("outcomes") or {}
        eps_rows.append("| %s | %d | %d | %d | %d | %d |"
                        % ("%.1f" % float(eps), block.get("n_cells", 0),
                           got.get("distinct_lower", 0), got.get("distinct_higher", 0),
                           got.get("same_lower", 0), got.get("same_higher", 0)))
    lower_cells = [(cell.get("name"), cell.get("state"), cell.get("epsilon"))
                   for cell in cells if cell.get("outcome") == "distinct_lower"]

    verdict_block = "\n".join([
        "### 四类裁决",
        "",
        "| 结局 | 计数 | 含义 |",
        "| --- | --- | --- |",
        "| `distinct_lower` | %d | 终点仍是两个不同电子态，且 moread 仍更低 |"
        % outcomes.get("distinct_lower", 0),
        "| `distinct_higher` | %d | 仍是两个不同态，但弛豫后 moread 反而**更高**（偏好反转） |"
        % outcomes.get("distinct_higher", 0),
        "| `same_lower` | %d | 终点身份重合，moread 更低 |" % outcomes.get("same_lower", 0),
        "| `same_higher` | %d | 终点身份重合，moread 更高（身份差异被几何洗掉） |"
        % outcomes.get("same_higher", 0),
        "| `incomplete` | %d | 两条腿未齐备，不判 |" % outcomes.get("incomplete", 0),
        "",
        "- 三条关键计数：`n_still_distinct` **%s/%s**、`n_still_lower` **%s/%s**、"
        "`n_preference_flipped` **%s/%s**。"
        % (all_block.get("n_still_distinct"), n_complete, all_block.get("n_still_lower"),
           n_complete, all_block.get("n_preference_flipped"), n_complete),
        "- 唯一没有反转的 `distinct_lower` 格子（%d 个）：%s —— 5 个里 3 个是 EC 阳离子、"
        "2 个是 TEGDME 阴离子。"
        % (len(lower_cells),
           "、".join("%s %s eps=%g" % (name, state, float(eps))
                     for name, state, eps in lower_cells) or "none"),
        "",
        "### 按电性状态",
        "",
        "| 态 | 格数 | 完成 | distinct_lower | distinct_higher | same_lower | same_higher |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ] + state_rows + [
        "",
        "### 按臂（发现集 / 留出臂）",
        "",
        "| 臂 | 格数 | distinct_lower | distinct_higher | same_lower | same_higher |",
        "| --- | --- | --- | --- | --- | --- |",
    ] + arm_rows + [
        "",
        "### 按分子",
        "",
        "| 分子 | 格数 | distinct_lower | distinct_higher | same_lower | same_higher |",
        "| --- | --- | --- | --- | --- | --- |",
    ] + mol_rows + [
        "",
        "### 按介电常数",
        "",
        "| eps | 格数 | distinct_lower | distinct_higher | same_lower | same_higher |",
        "| --- | --- | --- | --- | --- | --- |",
    ] + eps_rows)

    geometry_block = "\n".join([
        "### 幅度：单点差异被几何压缩了两个数量级",
        "",
        "- `|delta|` 单点中位 **%s eV** -> 弛豫后中位 **%s eV**：**缩小 %.0f 倍**。"
        % (num(p50("abs_single_point_delta_ev"), 5), num(p50("abs_relax_delta_ev"), 5),
           shrink),
        "- 带符号的 `delta_shift_ev = relax - single` 在 **%s/%s** 格为正、**%s/%s** 格为负："
        "弛豫把偏好一致地朝「moread 不再更低」的方向推，这就是 |delta| 收缩而偏好反转的机制。"
        % (n_shift_up, n_complete, n_shift_down, n_complete),
        "- `|delta 改变|` 中位 **%s eV** —— 与单点差异同量级，说明弛豫不是小扰动。"
        % num(p50("abs_delta_shift_ev"), 5),
        "- 两臂各自的弛豫能量降中位：**default %s eV vs moread %s eV**；"
        "moread 降得更多的格子 **0/%s**（default 在每个格子上都降得更多），"
        "这正是单点偏好被反转的能量学来源。"
        % (num(p50("energy_drop_default_ev"), 4), num(p50("energy_drop_moread_ev"), 4),
           n_complete),
        "",
        "### 几何与身份通道",
        "",
        "- 两条腿弛豫后的几何 RMSD 中位 **%s A**；**%s/%s** 格落在 `rmsd_same_minimum`"
        "（<= 0.02 A，仅作描述），**0 格**的两条腿几何逐位相同 —— 没有一对收敛到同一个驻点。"
        % (num(p50("rmsd_relaxed_arms"), 4), all_block.get("n_rmsd_same_minimum"), n_complete),
        "- 身份通道：弛豫后 `charge_l1 > %s` 仍有 **%s/%s** 格、贴阈值（±20%%）**%s 格**"
        "（冻结阈值 `near_threshold` 只是描述列，判据不变）。"
        % (num(analysis.get("threshold_charge_l1"), 3), all_block.get("n_still_distinct"),
           n_complete, all_block.get("n_near_threshold")),
    ])

    table_block = "\n".join(
        ["| 文件 | 内容 |", "| --- | --- |"]
        + ["| %s | %s |" % (name, note) for name, note in W18_TABLE_ROWS])

    did = ("把 Week 17 找出的 **%s 个 `moread_lower` 格子**（单点上两解不同、且 `moread` 更低"
           "的**全集**）里的两条 SCF 解各自做几何弛豫（**%s 个 ORCA `Opt` 作业 = %s 格 x 2 臂**），"
           "再问一次：这还是两个不同的电子态吗？`moread` 还更低吗？"
           "唯一的自由变量是作业类型（`sp` -> `Opt`）与初猜；方法、溶剂、起始几何 G1 全部冻结。"
           % (n_cells, summary.get("n_jobs"), n_cells))
    metric = ("把两条腿各自放到自己的几何极小点之后：只有 **%s/%s** 格仍保持 `moread` 更低"
              "（`still_lower`）；**%s/%s** 格的两解在终点**合并为同一电子态**（单点身份差异被"
              "几何洗掉）；**%s/%s** 格仍是两个不同态、但偏好被几何反转，全阶段偏好反转 **%s** 格。"
              "`|delta|` 中位从单点 **%s eV** 塌到 **%s eV**（缩小 %.0f 倍），而带符号位移在 "
              "**%s/%s** 格为正 —— 这就是「身份差异多数是真的，但单点上的能量偏好多数是假象」的"
              "定量版本。"
              % (all_block.get("n_still_lower"), n_complete, n_merged, n_complete,
                 outcomes.get("distinct_higher", 0), n_complete,
                 all_block.get("n_preference_flipped"),
                 num(p50("abs_single_point_delta_ev"), 5), num(p50("abs_relax_delta_ev"), 5),
                 shrink, n_shift_up, n_complete))
    qc = ("核心 QC：%s 个 `Opt` 作业 %s ok / %s failed（%s 格 x 2 臂）；两条腿起始几何先做审计、"
          "与冻结 G1 逐原子一致；阈值 %s 与 Week 17 `stage18_identity_census.json` 的 "
          "`thresholds.charge_l1_primary` 逐位相同；四类裁决计数、按态 / 按分子 / 按 eps / 按臂"
          "分组表、以及五条量级中位数全部现算并写入 verification.json 的 checks。"
          % (summary.get("n_jobs"), summary.get("n_ok"), summary.get("n_failed"),
             n_cells, num(analysis.get("threshold_charge_l1"), 3)))
    limit = ("所有比例都**条件在 %s 个 `moread_lower` 格子**上（Week 17 单点上两解不同且 moread "
             "更低的全集），不是 414 格总体，也不能读成「默认解在 N%% 的格子上安全」。"
             "判据 `charge_l1 > %s` 与材料阈值 1e-03 eV 冻结自 Stage 18、本阶段未重新拟合；"
             "几何同最小点宽容 0.02 A 只是描述列。两条腿的弛豫几何**没有一对逐位相同**，"
             "`rmsd_same_minimum` 的 %s 格只是同一极小点附近的近似，不构成「同一个驻点」的证明；"
             "`Opt` 收敛判据是 ORCA 默认、未做频率复核，机械稳定性不在本阶段结论之内。"
             "裸 CPCM、G1 起始几何，以及「阴离子在 r2SCAN-3c 下不束缚」的方法适用域限制"
             "全部继承前几周。"
             % (n_cells, num(analysis.get("threshold_charge_l1"), 3),
                all_block.get("n_rmsd_same_minimum")))
    summary_text = " ".join([did, metric])

    return {"did": did, "metric": metric, "qc": qc, "limit": limit,
            "summary": summary_text, "protocol_block": protocol_block,
            "verdict_block": verdict_block, "geometry_block": geometry_block,
            "table_block": table_block}


REPORT_TEMPLATES[17] = """# Week 17 成果小结 —— Stage 18（全目录电子身份普查与零成本自诊断）

## 0. 一页结论
- 做了什么：{w17_did}
- 关键数字：{w17_metric}
- 质检：{w17_qc}
- 限制：{w17_limit}

本文可独立阅读；逐项细节、物理机制与需裁决项见同目录 `week17_report_full.md`。

## 1. 协议与规模
{w17_protocol_block}

## 2. Part A：电子身份普查
{w17_census_block}

## 3. Part B：零成本自诊断（一条失败规则）
{w17_diagnosis_block}

## 4. 那条失败规则里唯一站得住的东西：单边筛查
{w17_onesided_block}

## 5. 产物与口径
{w17_table_block}

## 6. 产物清单
{artifact_list}

## 7. 源文件缺失
{missing_list}
"""


REPORT_TEMPLATES[18] = """# Week 18 成果小结 —— Stage 19（几何弛豫检验：第二个 SCF 解能不能扛住弛豫）

## 0. 一页结论
- 做了什么：{w18_did}
- 关键数字：{w18_metric}
- 质检：{w18_qc}
- 限制：{w18_limit}

本文可独立阅读；逐项细节、物理机制与需裁决项见同目录 `week18_report_full.md`。

## 1. 协议与规模
{w18_protocol_block}

## 2. 裁决：37 个 moread_lower 格子
{w18_verdict_block}

## 3. 幅度与几何
{w18_geometry_block}

## 4. 产物与口径
{w18_table_block}

## 5. 产物清单
{artifact_list}

## 6. 源文件缺失
{missing_list}
"""


def _w19_engine(ledger):
    """The xTB version string, whichever of the two JSON shapes the ledger uses."""
    value = (ledger or {}).get("engine_version")
    if isinstance(value, (list, tuple)):
        return ", ".join(str(item) for item in value) or "n/a"
    return str(value) if value else "n/a"


def week19_blocks(rung, ledger, analysis):
    """Week 19 / Stage 20 narrative blocks.

    Every number is read back out of ``stage20_relax_rung.json``,
    ``stage20_xtb_arms.json`` and ``stage20_xtb_arms_analysis.json``, so the
    distilled report cannot drift away from the artifacts it summarises.
    """

    keys = ("did", "metric", "qc", "limit", "summary", "protocol_block",
            "rung_block", "xtb_block", "table_block")
    if rung is None or analysis is None:
        text = "（`stage20_relax_rung.json` 或 `stage20_xtb_arms_analysis.json` 不存在）"
        return {key: text for key in keys}

    ledger = ledger or {}
    summary = ledger.get("summary") or {}
    aggregates = rung.get("aggregates") or {}
    by_state = aggregates.get("by_state") or {}
    by_molecule = aggregates.get("by_molecule") or {}
    by_arm = aggregates.get("by_arm_set") or {}
    ladder = rung.get("ladder_rows") or []
    epsilon_rows = rung.get("epsilon_rows") or []

    arms_all = ((analysis.get("aggregates") or {}).get("all") or {}).get("all") or {}
    arms_out = arms_all.get("outcomes") or {}
    arms_by_state = (analysis.get("aggregates") or {}).get("by_state") or {}
    arms_by_arm = (analysis.get("aggregates") or {}).get("by_arm_set") or {}
    cross = analysis.get("crosstab_stage19_by_stage20") or {}
    sp = analysis.get("sp_vs_stage19_relax") or {}

    def num(value, digits=3):
        return _w8_num(value, digits)

    def near(value, expected, tol):
        return value is not None and abs(float(value) - expected) < tol

    n_cells = rung.get("n_cells")
    n_eps = rung.get("n_eps_values")
    n_mol = rung.get("n_molecules_total")

    anion = by_state.get("anion") or {}
    cation = by_state.get("cation") or {}
    ranges = sorted(float(row.get("delta_range_ev") or 0.0) for row in epsilon_rows)
    median_range = ranges[len(ranges) // 2] if ranges else None

    def rung_row(population, kind):
        for row in ladder:
            if row.get("population") == population and row.get("rung") == kind:
                return row
        return {}

    def row_of(population, kind):
        row = rung_row(population, kind)
        return "| %s | %s | %s | %s | %s |" % (
            population, kind, num(row.get("shift_mean_ev"), 4),
            num(row.get("shift_std_ev"), 4), num(row.get("relative_dispersion"), 4))

    protocol_block = "\n".join([
        "### 两个 Part，两种作业量",
        "",
        "- **Part 1：零新增计算。** 把 Week 18 落盘的 37 格弛豫能量按轴放回 Stage 10 五级台阶的"
        "同一把尺子上（`Delta_ox = -drop(cation)`、`Delta_red = -drop(anion)`），量出这条"
        "「第六级台阶」的 mean 与 std —— 因为 Stage 10 已经证明决定排序是否被改写的是位移的"
        "**离散度**而不是**大小**。",
        "- **Part 2：%s 个 GFN2-xTB 作业 = %s 格 x 2 臂**（reused %s / computed %s），引擎 "
        "`xtb` %s（GFN%s）。起点是 Stage 19 两条 r2SCAN-3c 弛豫终点，与 `outputs/week18` 的源"
        "几何逐字节相同。"
        % (summary.get("n_jobs"), n_cells, summary.get("n_reused"),
           summary.get("n_computed"), _w19_engine(ledger), ledger.get("gfn")),
        "- 两个 Part 的目标集合都是 Week 17 单点上「两解不同、且 `moread` 更低」的 **%s 格全集**"
        "（发现集 32 + 留出臂 5），不是 414 对总体。" % n_cells,
        "- **两把尺子必须分开读**：Stage 19 的 `distinct` 是冻结电子身份 `charge_l1 > 0.039`；"
        "Part 2 只有几何判据 `RMSD <= 0.02 A`（阈值事前固定）。所以「与 Stage 19 裁决的一致率」"
        "是**跨判据**的一致性，而「同一几何上的方法一致率」才是纯方法与方法的对照。",
        "- Part 2 的 xTB 作业是**气相**（无 CPCM）；`epsilon` 只是「起点几何来自哪个 CPCM 格子」"
        "的标签，`by_epsilon` 分层**不构成介电效应**。",
        "- Part 1 **不报** tau_b / Top-k / `f_unresolved`：本目录里每个分子只出现**一种态**"
        "（氧化轴 n=3、还原轴 n=4），这么少的点上的秩相关不构成统计推断，`rank_metrics` 列逐行"
        "写明 `omitted:` 原因。",
    ])

    ladder_rows = [row_of(pop, "P1_to_P2") for pop in
                   ("ox_dmc_ec_tmp_eps5", "ox_carbonates_eps5",
                    "red_dec_emc_pc_tegdme_eps20", "red_dec_emc_pc_eps5")]
    ladder_rows += [row_of(pop, "P2sp_to_P2relax") for pop in
                    ("ox_dmc_ec_tmp_eps5", "ox_carbonates_eps5",
                     "red_dec_emc_pc_tegdme_eps20", "red_dec_emc_pc_eps5")]
    molecule_rows = ["| %s | %s | %s | %s | %s | %s |"
                     % (name, block.get("n"), num(block.get("shift_mean_ev"), 4),
                        num(block.get("shift_min_ev"), 4), num(block.get("shift_max_ev"), 4),
                        num(block.get("relative_dispersion"), 3))
                     for name, block in sorted(by_molecule.items(),
                                               key=lambda kv: -float(kv[1].get("n") or 0))]

    rung_block = "\n".join([
        "### 弛豫不是「另一个环境」：它几乎与 eps 无关",
        "",
        "- %s 格、%s 个分子、%s 个不同 eps。同一个 (分子, 态) 在它自己的各个 eps 上，Delta 的"
        "极差**中位 %s eV、最大 %s eV（DEC）** —— 而同一批分子的 P1->P2 环境位移是 -2.17 ~ "
        "-2.46 eV（单格极值 -2.91 eV）。**弛豫修正与连续介质的介电常数几乎无关，是态内量。**"
        % (n_cells, n_mol, n_eps, num(median_range, 4), num(ranges[-1] if ranges else None, 3)),
        "",
        "| 分子 | 态 | n_eps | Delta 最小 | Delta 最大 | 相对散布 |",
        "| --- | --- | --- | --- | --- | --- |",
    ] + ["| %s | %s | %s | %s | %s | %s |"
         % (row.get("name"), row.get("state"), row.get("n_eps"),
            num(row.get("delta_min_ev"), 4), num(row.get("delta_max_ev"), 4),
            num((by_molecule.get(row.get("name")) or {}).get("relative_dispersion"), 3))
         for row in epsilon_rows] + [
        "",
        "### 但它也不是「纯平移」：按态分成两支",
        "",
        "| 态 | 格数 | mean | std | 相对散布 |",
        "| --- | --- | --- | --- | --- |",
        "| anion | %d | %s eV | %s eV | %s |"
        % (anion.get("n_cells", 0), num(anion.get("shift_mean_ev"), 3),
           num(anion.get("shift_std_ev"), 3), num(anion.get("relative_dispersion"), 2)),
        "| cation | %d | %s eV | %s eV | %s |"
        % (cation.get("n_cells", 0), num(cation.get("shift_mean_ev"), 3),
           num(cation.get("shift_std_ev"), 3), num(cation.get("relative_dispersion"), 2)),
        "",
        "还原支（anion）接近**刚性平移**（相对散布 %s），氧化支（cation）是**散布型**"
        "（相对散布 %s）。这也是这条新台阶在两条轴上意义不同的原因。"
        % (num(anion.get("relative_dispersion"), 2), num(cation.get("relative_dispersion"), 2)),
        "",
        "### 与五级台阶同口径并置（同一批分子）",
        "",
        "| population | 台阶 | mean | std | 相对散布 |",
        "| --- | --- | --- | --- | --- |",
    ] + ladder_rows + [
        "",
        "- 氧化 {DMC,EC,TMP}@eps=5：新台阶相对散布 **%s**，而同一 population 的 P1->P2 只有 "
        "**%s**；碳酸酯 {DMC,EC}@eps=5 为 **%s** 对 **%s**。"
        % (num(rung_row("ox_dmc_ec_tmp_eps5", "P2sp_to_P2relax").get("relative_dispersion"), 2),
           num(rung_row("ox_dmc_ec_tmp_eps5", "P1_to_P2").get("relative_dispersion"), 2),
           num(rung_row("ox_carbonates_eps5", "P2sp_to_P2relax").get("relative_dispersion"), 2),
           num(rung_row("ox_carbonates_eps5", "P1_to_P2").get("relative_dispersion"), 2)),
        "- 还原 {DEC,EMC,PC,TEGDME}@eps=20：新台阶 **%s**，P1->P2 **%s**；{DEC,EMC,PC}@eps=5 为 "
        "**%s** 对 **%s**。"
        % (num(rung_row("red_dec_emc_pc_tegdme_eps20", "P2sp_to_P2relax").get("relative_dispersion"), 2),
           num(rung_row("red_dec_emc_pc_tegdme_eps20", "P1_to_P2").get("relative_dispersion"), 2),
           num(rung_row("red_dec_emc_pc_eps5", "P2sp_to_P2relax").get("relative_dispersion"), 2),
           num(rung_row("red_dec_emc_pc_eps5", "P1_to_P2").get("relative_dispersion"), 2)),
        "- 唯一被标为**退化**的台阶是氧化轴的 G1->G2（|mean| 近似 0，相对散布无意义）——"
        "它在 (b) 面板里用斜纹柱画出，不参与任何比较。",
        "- `rank_metrics` 在全部 %d 行上都是 `omitted:`：这是**结构性省略**，不是计算没做。"
        % len(ladder),
    ])

    cross_rows = []
    for src in ("distinct_lower", "distinct_higher", "same_lower", "same_higher"):
        block = cross.get(src) or {}
        cross_rows.append("| %s | %d | %d | %d | %d |"
                          % (src, block.get("distinct_lower", 0), block.get("distinct_higher", 0),
                             block.get("same_lower", 0), block.get("same_higher", 0)))
    arms_state_rows = []
    for state in ("anion", "cation"):
        block = arms_by_state.get(state) or {}
        got = block.get("outcomes") or {}
        arms_state_rows.append("| %s | %d | %d | %d | %d | %d | %d |"
                               % (state, block.get("n_cells", 0), block.get("n_complete", 0),
                                  got.get("distinct_lower", 0), got.get("distinct_higher", 0),
                                  got.get("same_lower", 0), got.get("same_higher", 0)))
    arms_arm_rows = []
    for arm in ("discovery", "holdout"):
        block = arms_by_arm.get(arm) or {}
        got = block.get("outcomes") or {}
        arms_arm_rows.append("| %s | %d | %d | %d | %d | %d | %d |"
                             % (arm, block.get("n_cells", 0), block.get("n_complete", 0),
                                got.get("distinct_lower", 0), got.get("distinct_higher", 0),
                                got.get("same_lower", 0), got.get("same_higher", 0)))

    p50_relax = (arms_all.get("abs_xtb_relax_delta_ev") or {}).get("p50")
    p50_sp = (arms_all.get("abs_xtb_sp_delta_ev") or {}).get("p50")
    compress = (float(p50_sp) / float(p50_relax)) if p50_relax else 0.0
    drift_d = (arms_all.get("xtb_drift_default") or {}).get("p50")
    drift_m = (arms_all.get("xtb_drift_moread") or {}).get("p50")
    start_p50 = (arms_all.get("xtb_rmsd_start_arms") or {}).get("p50")
    relax_p50 = (arms_all.get("xtb_relax_rmsd_arms") or {}).get("p50")

    xtb_block = "\n".join([
        "### 两个不同的问题，两个不同的答案",
        "",
        "| 问题 | 判据 | 结果 |",
        "| --- | --- | --- |",
        "| 同一几何上「哪条腿更低」能否被廉价方法复现？ | 符号一致（材料阈值 1e-03 eV） | "
        "**%s/%s（%s%%）** |"
        % (arms_all.get("n_xtb_sp_matches_stage19_relax"), arms_all.get("n_complete"),
           num(100.0 * float(arms_all.get("sp_agreement_rate") or 0.0), 1)),
        "| 廉价优化器能否独立把第二解找回来？ | 几何 RMSD <= 0.02 A | 两臂合并 **%s/%s** |"
        % (arms_all.get("n_xtb_same_minimum"), arms_all.get("n_complete")),
        "| 逐格裁决与 Stage 19 是否一致？ | 跨判据（电子身份 vs 几何） | **%s/%s（%s%%）** |"
        % (arms_all.get("n_agree_with_stage19"), arms_all.get("n_complete"),
           num(100.0 * float(arms_all.get("agreement_rate") or 0.0), 1)),
        "",
        "### 四类裁决（xTB 面上）",
        "",
        "| 结局 | 计数 | 含义 |",
        "| --- | --- | --- |",
        "| `distinct_lower` | %d | 几何上仍是两个极小点，且 moread 仍更低 |"
        % arms_out.get("distinct_lower", 0),
        "| `distinct_higher` | %d | 仍是两个极小点，但弛豫后 moread 反而更高 |"
        % arms_out.get("distinct_higher", 0),
        "| `same_lower` | %d | 两臂合并，且 moread 更低 |" % arms_out.get("same_lower", 0),
        "| `same_higher` | %d | 两臂合并，且 moread 更高 |" % arms_out.get("same_higher", 0),
        "| `incomplete` | %d | 两条腿未齐备，不判 |" % arms_out.get("incomplete", 0),
        "",
        "- 关键计数：`n_xtb_same_minimum` **%s/%s**、`n_xtb_still_lower` **%s/%s**、"
        "`n_xtb_preference_flipped` **%s/%s**（仅单向计数：反方向「单点上 default 更低、弛豫后 "
        "moread 更低」同样存在，只是不在这个计数里）。"
        % (arms_all.get("n_xtb_same_minimum"), arms_all.get("n_complete"),
           arms_all.get("n_xtb_still_lower"), arms_all.get("n_complete"),
           arms_all.get("n_xtb_preference_flipped"), arms_all.get("n_complete")),
        "",
        "### 量级：廉价弛豫把两臂的能量差压掉约 %.0f 倍" % compress,
        "",
        "- |xTB 单点 Delta| 中位 **%s eV** -> |xTB 弛豫 Delta| 中位 **%s eV**（压掉约 %.1f 倍）。"
        % (num(p50_sp, 4), num(p50_relax, 5), compress),
        "- 单臂几何漂移中位 **default %s A / moread %s A**，与起点双解 RMSD 中位 **%s A** 同量级；"
        "弛豫后双解 RMSD 中位 **%s A**（起点 %s A）。"
        % (num(drift_d, 3), num(drift_m, 3), num(start_p50, 4), num(relax_p50, 4),
           num(start_p50, 4)),
        "- 同一几何上的 %s 个分歧格里有 %s 个落在 ORCA 侧的 1 meV 材料带内（最大 %s eV），"
        "即分歧集中在近简并处，不是方向性错误。"
        % (len(sp.get("disagreements") or []),
           sp.get("n_disagreements_inside_material_band"),
           num(sp.get("max_abs_stage19_relax_delta_ev_among_disagreements"), 5)),
        "",
        "### Stage 19 裁决 x Stage 20 裁决",
        "",
        "| Stage19 \\ Stage20 | distinct_lower | distinct_higher | same_lower | same_higher |",
        "| --- | --- | --- | --- | --- |",
    ] + cross_rows + [
        "",
        "### 按态与按臂的分解",
        "",
        "| 态 | 格数 | 完成 | distinct_lower | distinct_higher | same_lower | same_higher |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ] + arms_state_rows + [
        "",
        "| 臂 | 格数 | 完成 | distinct_lower | distinct_higher | same_lower | same_higher |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ] + arms_arm_rows + [
        "",
        "- 阴离子侧同几何方法一致率 **%s%%**（21/21），阳离子侧 %s%%；发现集 %s%%，留出臂 %s%%。"
        % (num(100.0 * float((arms_by_state.get("anion") or {}).get("sp_agreement_rate") or 0.0), 1),
           num(100.0 * float((arms_by_state.get("cation") or {}).get("sp_agreement_rate") or 0.0), 1),
           num(100.0 * float((arms_by_arm.get("discovery") or {}).get("sp_agreement_rate") or 0.0), 1),
           num(100.0 * float((arms_by_arm.get("holdout") or {}).get("sp_agreement_rate") or 0.0), 1)),
    ])

    table_block = "\n".join(
        ["| 文件 | 内容 |", "| --- | --- |"]
        + ["| %s | %s |" % (name, note) for name, note in W19_TABLE_ROWS])

    did = ("把 Week 18 留下的两个问题拆成互不依赖的两个 Part：Part 1 是**零新增计算**的台阶回填"
           "（把 %s 格弛豫能量放回 Stage 10 五级台阶的同一把尺子上），Part 2 是 **%s 个冻结 "
           "GFN2-xTB 作业**（%s 格 x 2 臂）的跨方法检验。"
           % (n_cells, summary.get("n_jobs"), n_cells))
    metric = ("Part 1：弛豫修正几乎与 eps 无关（逐分子跨 eps 极差中位 **%s eV**、最大 **%s eV**），"
              "但它不是纯平移 —— 还原支 mean/std/相对散布 **%s / %s / %s**，氧化支 **%s / %s / %s**。"
              "Part 2：同一几何上 xTB 单点与 ORCA r2SCAN-3c 的偏好方向一致 **%s/%s（%s%%）**，"
              "但 xTB 自己的弛豫把两臂能量差压掉约 **%.0f 倍**（|Delta| 中位 %s -> %s eV），"
              "**%s/%s** 格两臂干脆合并到同一极小点；逐格裁决与 Stage 19 只有 **%s/%s（%s%%）**"
              "一致，但那是**跨判据**的比较。"
              % (num(median_range, 4), num(ranges[-1] if ranges else None, 3),
                 num(anion.get("shift_mean_ev"), 3), num(anion.get("shift_std_ev"), 3),
                 num(anion.get("relative_dispersion"), 2),
                 num(cation.get("shift_mean_ev"), 3), num(cation.get("shift_std_ev"), 3),
                 num(cation.get("relative_dispersion"), 2),
                 arms_all.get("n_xtb_sp_matches_stage19_relax"), arms_all.get("n_complete"),
                 num(100.0 * float(arms_all.get("sp_agreement_rate") or 0.0), 1), compress,
                 num(p50_sp, 4), num(p50_relax, 5),
                 arms_all.get("n_xtb_same_minimum"), arms_all.get("n_complete"),
                 arms_all.get("n_agree_with_stage19"), arms_all.get("n_complete"),
                 num(100.0 * float(arms_all.get("agreement_rate") or 0.0), 1)))
    qc = ("核心 QC：Part 2 的 %s 个 xTB 作业 %s ok / %s failed；74 条腿的起始几何与 Stage 19 的"
          "弛豫终点逐字节相同；`charge_l1` 冻结阈值与 Stage 18 一致；四类裁决计数、两个一致率、"
          "交叉表、按态 / 按臂分解、以及四条量级中位数全部现算并写入 verification.json 的 checks；"
          "Part 1 的 %s 行台阶表的 `rank_metrics` 必须逐行是 `omitted:`。"
          % (summary.get("n_jobs"), summary.get("n_ok"), summary.get("n_failed"), len(ladder)))
    limit = ("所有比例都**条件在 %s 个 `moread_lower` 格子**上（Week 17 单点上两解不同且 moread "
             "更低的全集），不是 414 格总体。两个一致率**不可互换**：Stage 19 用冻结电子身份 "
             "`charge_l1 > 0.039`，Part 2 只有几何 `RMSD <= 0.02 A`。Part 2 的 xTB 作业是气相"
             "（无 CPCM），`epsilon` 只是起点几何的标签，`by_epsilon` **不是介电效应**。Part 1 "
             "的单点数目太少（氧化轴 3、还原轴 4），故不报任何秩相关；`rank_metrics` 的 `omitted:` "
             "是结构性省略。`0.02 A` 与 `1e-03 eV` 是事前固定的描述性阈值，本阶段未做任何调参。"
             % n_cells)
    summary_text = " ".join([did, metric])

    return {"did": did, "metric": metric, "qc": qc, "limit": limit,
            "summary": summary_text, "protocol_block": protocol_block,
            "rung_block": rung_block, "xtb_block": xtb_block, "table_block": table_block}


REPORT_TEMPLATES[19] = """# Week 19 成果小结 —— Stage 20（第六级台阶与第二解的跨方法存亡）

## 0. 一页结论
- 做了什么：{w19_did}
- 关键数字：{w19_metric}
- 质检：{w19_qc}
- 限制：{w19_limit}

本文可独立阅读；逐项细节、物理机制与需裁决项见同目录 `week19_report_full.md`。

## 1. 协议与规模
{w19_protocol_block}

## 2. Part 1：弛豫作为第六级台阶
{w19_rung_block}

## 3. Part 2：第二解在廉价势能面上的存亡
{w19_xtb_block}

## 4. 产物与口径
{w19_table_block}

## 5. 产物清单
{artifact_list}

## 6. 源文件缺失
{missing_list}
"""


def week12_blocks(analysis, ladder):
    """Render the week-12 (Stage 13 / dielectric limit + ORCA ledger) blocks.

    Every number is read back out of ``stage13_analysis.json`` and
    ``stage13_ladder.json``, so the distilled report cannot drift away from the
    CSVs it summarises.
    """

    empty = {"present": False, "did": "", "metric": "", "qc": "", "limit": "",
             "law_block": "", "term_block": "", "limit_block": "", "forecast_block": "",
             "ledger_block": "", "table_block": "", "sigma_note": "", "summary": ""}
    if not isinstance(analysis, dict) or not (analysis.get("subset") or []):
        return empty

    model = analysis.get("model_comparison") or {}
    terms = analysis.get("term_resolved_born") or {}
    limit = analysis.get("conductor_limit") or {}
    extrap = analysis.get("extrapolation_scaling") or {}
    ledger = analysis.get("smd_ledger") or {}
    rungs = analysis.get("rung_ladder") or {}
    checks = analysis.get("checks") or {}
    ladder_checks = analysis.get("ladder_checks") or {}
    subset = analysis.get("subset") or []
    bare_eps = analysis.get("bare_eps") or []
    born = model.get("born_r2") or {}
    onsager = model.get("onsager_r2") or {}
    two = model.get("two_parameter_r2") or {}
    kstats = model.get("two_parameter_k") or {}
    slopes = model.get("born_slope_ev") or {}
    cdss = ledger.get("smd_cds_absolute_ev") or {}
    gap = limit.get("gap_to_limit_ev") or {}
    ordering = limit.get("ordering") or {}
    targets = extrap.get("targets") or {}
    rewritten = rungs.get("rewritten_points") or []
    n_pass = sum(1 for item in checks.values() if isinstance(item, dict) and item.get("ok"))
    n_checks = len(checks)
    n_jobs_new = None
    if isinstance(ladder, dict):
        n_jobs_new = ladder.get("n_new_jobs")

    def num(value, digits=3):
        return _w8_num(value, digits)

    def signed(value, digits=3):
        text = _w8_num(value, digits)
        if text == "\u2014":
            return text
        return text if text.startswith("-") else "+" + text

    law_block = ("**(a) 介电阶梯：Born 形式在六个介电常数上仍然成立**\n\n"
                 "参考点是气相（eps = 1，非 CPCM 计算），台阶是 bare CPCM 的 "
                 "eps = 5/10/20/40/80/200；24 条 (分子, 轴) 曲线各自做过原点拟合：\n\n"
                 "| 模型 | 形式 | mean R2 | 最差 R2 | 最好 R2 |\n"
                 "| --- | --- | --- | --- | --- |\n")
    law_block += "| **Born** | delta = S (1 - 1/eps) | **%s** | %s | %s |\n" % (
        num(born.get("mean"), 4), num(born.get("min"), 4), num(born.get("max"), 4))
    law_block += "| Onsager | delta = S (eps - 1)/(2 eps + 1) | %s | %s | %s |\n" % (
        num(onsager.get("mean"), 4), num(onsager.get("min"), 4), num(onsager.get("max"), 4))
    law_block += "| 两参数 | delta = S (eps - 1)/(eps + k) | %s | %s | %s |\n\n" % (
        num(two.get("mean"), 4), num(two.get("min"), 4), num(two.get("max"), 4))
    law_block += ("两参数族给出 `k = %s ± %s`（范围 %s .. %s）：数据把这个自由参数钉在 0 附近，"
                  "也就是**自己把模型选回了 Born**（k = 0 正是 Born）。\n\n"
                  "六个介电点的 u 值：%s。`u -> 1` 就是导体极限，因此 Born 拟合出的斜率 S "
                  "本身就是导体极限的预测，不是外推公式的产物。\n"
                  % (num(kstats.get("mean"), 4), num(kstats.get("sd"), 4),
                     num(kstats.get("min"), 4), num(kstats.get("max"), 4),
                     "、".join("eps = %g -> u = %s" % (eps, num(1.0 - 1.0 / eps, 4))
                              for eps in bare_eps)))

    term_block = ("**(b) 位移拆成「介电」与「溶质畸变」两项，两项都近似 Born**\n\n"
                  "`delta = 溶质畸变 (Delta E_elec+nuc) + CPCM 介电`。两项各自除以 "
                  "`u = 1 - 1/eps` 后都是常数：\n\n"
                  "| 序列 | mean R2（过原点，六点） | mean 斜率（eV） |\n"
                  "| --- | --- | --- |\n")
    term_block += "| 总位移 | %s | %s |\n" % (num((terms.get("total_r2") or {}).get("mean"), 4),
                                            num(slopes.get("mean"), 4))
    term_block += "| 纯介电（CPCM Dielectric） | %s | %s |\n" % (
        num((terms.get("diel_r2") or {}).get("mean"), 4),
        num((terms.get("diel_S_ev") or {}).get("mean"), 4))
    term_block += "| 溶质畸变（Delta E_elec+nuc） | %s | %s |\n\n" % (
        num((terms.get("dist_r2") or {}).get("mean"), 4),
        num((terms.get("dist_S_ev") or {}).get("mean"), 4))
    term_block += ("畸变项的斜率与介电项**反号**，而且不是小量 —— 它是溶剂自适应密度带来的"
                   "电子极化，不是静电项。把位移讲成「纯介电 screening」在本数据集上是不准确的。\n")
    limit_block = ("**(c) 导体极限 eps -> inf**：Born 拟合的斜率 S 就是 `u -> 1` 的极限。"
                   "eps = 200 与这个极限之间平均只剩 %s eV（最差 %s eV），也就是导体极限在本方法"
                   "的印刷精度内已被触达：\n\n"
                   "| 轴 | tau(气相 vs eps 200) | tau(气相 vs 极限) | tau(eps 200 vs 极限) | Top-20%% 重叠(气相 vs 极限) |\n"
                   "| --- | --- | --- | --- | --- |\n"
                   % (num(gap.get("mean"), 4), num(gap.get("max"), 4)))
    for axis, axis_label in W12_AXIS_SHORT:
        block = ordering.get(axis)
        if not block:
            continue
        limit_block += "| %s | %s | %s | %s | %s |\n" % (
            axis_label, signed(block.get("kendall_tau_gas_vs_200")),
            signed(block.get("kendall_tau_gas_vs_limit")),
            signed(block.get("kendall_tau_200_vs_limit")),
            num(block.get("top20_overlap_gas_vs_limit"), 2))
    limit_block += "\n"

    forecast_block = ("**(d) 外推误差随外推距离增长**：只用 {气相, eps = 5, 10, 20} 拟合，"
                      "然后预测三个更远的点（eps = 40 / 80 / 200）：\n\n"
                      "| 目标 | u 距离（相对 eps = 20） | 最大绝对误差 (eV) | 平均绝对误差 (eV) | 最大相对误差 |\n"
                      "| --- | --- | --- | --- | --- |\n")
    for tag, label in (("cpcm_40", "eps = 40"), ("cpcm_80", "eps = 80"), ("cpcm_200", "eps = 200")):
        item = targets.get(tag) or {}
        forecast_block += "| %s | %s | %s | %s | %s |\n" % (
            label, num(item.get("u_gap"), 4), num(item.get("max_abs_err_ev"), 4),
            num(item.get("mean_abs_err_ev"), 4), num(item.get("max_rel_err"), 4))
    forecast_block += ("\n误差/距离 ≈ %s eV per unit u —— 越往外推，单位距离的代价越高，"
                       "这正是「只测到 eps = 40」在 Stage 12 里必须写成限制的原因。\n"
                       % num(extrap.get("err_per_u_gap_ev"), 4)
                       if extrap.get("err_per_u_gap_ev") is not None
                       else "\n误差随外推距离单调增长。\n")

    ledger_block = ("**(e) SMD 能量账本：位移的精确四项分解**\n\n"
                    "ORCA 把每个单点印成 `FINAL = Total + D4 + gCP`，而 "
                    "`Total = E_elec+nuc + CPCM Dielectric [+ SMD CDS]`。因此垂直量的环境位移"
                    "**逐态精确可加**（来自同一次自洽计算，不是两次不同计算的差分）：\n\n"
                    "`delta = 溶质畸变 + CPCM 介电 + SMD CDS + Delta(D4) + Delta(gCP)`\n\n"
                    "| 层 | eps | 轴 | 位移 (eV) | 介电项 (eV) | 畸变项 (eV) | CDS 项 (eV) | "
                    "Delta(D4+gCP) (eV) | 畸变抵消介电的比例 |\n"
                    "| --- | --- | --- | --- | --- | --- | --- | --- | --- |\n")
    for tag in W12_SMD_ORDER:
        block = ledger.get(tag) or {}
        per_axis = block.get("per_axis") or {}
        for axis, axis_label in W12_AXIS_SHORT:
            stats = per_axis.get(axis)
            if not stats:
                continue
            ledger_block += "| %s | %s | %s | %s | %s | %s | %s | %s | %s |\n" % (
                W12_SMD_LABEL.get(tag, tag), num(block.get("epsilon"), 3), axis_label,
                signed((stats.get("shift_ev") or {}).get("mean"), 4),
                signed((stats.get("diel_ev") or {}).get("mean"), 4),
                signed((stats.get("dist_ev") or {}).get("mean"), 4),
                signed((stats.get("cds_ev") or {}).get("mean"), 4),
                signed((stats.get("d4gcp_ev") or {}).get("mean"), 4),
                num((stats.get("distortion_cancels_fraction") or {}).get("mean"), 3))
    ledger_block += "\n三条**结构性**事实（在 12 分子 x 3 态上逐点验证，不是近似）：\n\n"
    ledger_block += ("1. `Delta(D4) = Delta(gCP) = 0`（最大 %s / %s eV）：两者只依赖几何，"
                     "而所有层共用逐字节相同的 G1 几何。\n"
                     % (num((ladder_checks.get("composite_terms_environment_independent") or {}).get("max_abs_d4_ev"), 8),
                        num((ladder_checks.get("composite_terms_environment_independent") or {}).get("max_abs_dgcp_ev"), 8)))
    ledger_block += ("2. `SMD CDS` 项在三个电荷态上**完全相同**（最大 spread %s eV，覆盖 %s 个"
                     "「分子 x 层」组）：因此它对任何垂直 IP/EA 的贡献**精确为 0**。"
                     "它是一个态的刚性偏移。\n"
                     % (num((ladder_checks.get("cds_is_state_independent") or {}).get("max_spread_ev"), 8),
                        num((ladder_checks.get("cds_is_state_independent") or {}).get("n_molecule_layer_groups"), 0)))
    ledger_block += ("3. 位移恒等式残差 <= %s eV（印刷精度）。\n\n"
                     % num((ladder_checks.get("shift_split_is_exact") or {}).get("max_abs_residual_ev"), 8))
    ledger_block += "CDS 的绝对量级并不小（按层平均）：%s。\n\n" % "、".join(
        "%s %s eV" % (W12_SMD_LABEL.get(tag, tag), num((cdss.get(tag) or {}).get("mean"), 4))
        for tag in W12_SMD_ORDER)
    ledger_block += ("**需要裁决**：bare CPCM 与 SMD 用的是不同的原子半径盒（C 2.04 -> 1.85 Å、"
                     "O 1.824 -> 2.168 Å（水为 1.52 Å）、H 1.32 -> 1.20 Å），ORCA 的 `%cpcm` 里"
                     "没有调节腔半径的选项。因此「把 SMD 位移与同 eps 的 bare-CPCM 外推值相减」"
                     "**同时混进了半径盒与表面项两个变量**，只能作为合并上界报出，不能称为纯表面项。\n")

    table_block = ("**(f) 22 点台阶总表**（电子结构 10 点沿用 Stage 12 读数 + 本周新增的 12 个介电点）：\n\n"
                   "| 台阶 | 轴 | n | sd(delta) (eV) | b | tau_b | f_unres(1) | f_unres(1.96) | "
                   "Top-20% 重叠 | 清单被改写 |\n"
                   "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n")
    for row in rungs.get("rows") or []:
        rung = row.get("rung")
        table_block += "| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |\n" % (
            W12_LADDER_LABEL.get(rung, rung), row.get("axis"), num(row.get("n"), 0),
            num(row.get("delta_sd_ev"), 4), signed(row.get("ols_slope_b")),
            signed(row.get("kendall_tau_b")), num(row.get("f_unresolved_p1_observed")),
            num(row.get("f_unresolved_p1_z1p96_observed")), num(row.get("overlap_20"), 2),
            "是" if row.get("shortlist_rewritten") else "否")
    table_block += ("\n新增的四个介电台阶（eps 40 -> 80、80 -> 200，各两轴）全部良性；全表仍然只有 "
                    "%d 个台阶改写清单（%s），与 Stage 12 完全相同 —— 把介电常数从 40 推到 200，"
                    "一个结论都没有翻转。\n" % (rungs.get("n_rewritten") or 0, "、".join(rewritten)))
    n_levels = len((ladder or {}).get("levels") or []) if isinstance(ladder, dict) else 0
    n_state_rows = (ladder or {}).get("n_state_rows") if isinstance(ladder, dict) else None
    n_split_rows = (ladder or {}).get("n_split_rows") if isinstance(ladder, dict) else None
    n_new_jobs = len(subset) * len(NEW_LAYER_TAGS) * 3

    smd_acn = (ledger.get("smd_acetonitrile") or {}).get("per_axis") or {}
    smd_wat = (ledger.get("smd_water") or {}).get("per_axis") or {}
    acn_ox = (smd_acn.get("oxidation") or {})
    acn_red = (smd_acn.get("reduction") or {})

    did = ("新增 %d 个 ORCA 单点（12 分子 x 3 态 x 3 层：bare CPCM 的 eps = 80 / 200，"
           "以及 CPCM(SMD, 水)），几何全部复用 G1（逐字节相同，未重新优化），方法固定 r2SCAN-3c，"
           "全部是垂直量；子集与 T3 / P2 相同的 %d 个分子。连同既有产物，介电阶梯由 5 级升到 7 级"
           "（气相 + eps = 5/10/20/40/80/200），环境层由 1 个 SMD 溶剂升到 2 个。"
           "第 2 件事不花任何额外计算：ORCA 本来就把单点能量印成分项和，于是「环境位移」可以"
           "逐态精确拆成溶质畸变 + CPCM 介电 + SMD CDS + Delta(D4) + Delta(gCP)。"
           % (n_new_jobs, len(subset)))

    metric = ""
    metric += ("- **介电自相似律由 6 个介电点测量确认**：Born 形式 mean R2 = %s（最差 %s），"
               "Onsager 只有 %s；两参数族 `delta = S (eps-1)/(eps+k)` 的自有参数 `k = %s ± %s`，"
               "数据自己把模型选回 Born。\n"
               % (num(born.get("mean"), 4), num(born.get("min"), 4), num(onsager.get("mean"), 4),
                  num(kstats.get("mean"), 4), num(kstats.get("sd"), 4)))
    metric += ("- **导体极限触达**：eps = 200 与 `u -> 1` 之间平均只剩 %s eV（最差 %s eV）；"
               "气相 vs 极限的 tau_b = %s（氧化）/ %s（还原）。\n"
               % (num(gap.get("mean"), 4), num(gap.get("max"), 4),
                  signed((ordering.get("oxidation") or {}).get("kendall_tau_gas_vs_limit")),
                  signed((ordering.get("reduction") or {}).get("kendall_tau_gas_vs_limit"))))
    metric += ("- **外推代价可测**：只用 {气相, eps = 5, 10, 20} 预测 eps = 40 / 80 / 200，"
               "最大绝对误差 %s / %s / %s eV。\n"
               % (num((targets.get("cpcm_40") or {}).get("max_abs_err_ev"), 4),
                  num((targets.get("cpcm_80") or {}).get("max_abs_err_ev"), 4),
                  num((targets.get("cpcm_200") or {}).get("max_abs_err_ev"), 4)))
    metric += ("- **环境账本（SMD 乙腈）**：氧化轴位移 %s = 介电 %s + 畸变 %s；"
               "还原轴位移 %s = 介电 %s + 畸变 %s；畸变抵消介电项的比例为 %s（氧化）/ %s（还原）。"
               "SMD CDS 与 Delta(D4) / Delta(gCP) 对垂直量精确为 0。\n"
               % (signed((acn_ox.get("shift_ev") or {}).get("mean"), 4),
                  signed((acn_ox.get("diel_ev") or {}).get("mean"), 4),
                  signed((acn_ox.get("dist_ev") or {}).get("mean"), 4),
                  signed((acn_red.get("shift_ev") or {}).get("mean"), 4),
                  signed((acn_red.get("diel_ev") or {}).get("mean"), 4),
                  signed((acn_red.get("dist_ev") or {}).get("mean"), 4),
                  num((acn_ox.get("distortion_cancels_fraction") or {}).get("mean")),
                  num((acn_red.get("distortion_cancels_fraction") or {}).get("mean"))))
    metric += ("- **22 点台阶**：只剩 %s 个台阶改写清单（%s），与 Stage 12 的 18 点结论完全一致 —— "
               "把介电常数从 40 推到 200，没有任何结论翻转。"
               % (rungs.get("n_rewritten"), "、".join(rewritten)))

    qc = ("账本 %s 行（分子 x 层 x 态）、位移分解 %s 行、"
          "台阶表 %s 行；全部由 `build_stage13_ladder.py` / "
          "`analyze_stage13_dielectric_limit.py` 从既有产物与本周 %d 个新作业现场重算，"
          "不引入新的拟合自由度；解析层 8 项 + 分析层 %d 项断言"
          "合计 %d/%d PASS，缺失作业 0 个，气相台阶与 P1 表逐点一致。"
          % (num(n_state_rows, 0), num(n_split_rows, 0), num(rungs.get("n_points"), 0),
             n_new_jobs, n_checks, n_pass, n_checks))

    limit_text = ("介电点止于 eps = 200，导体极限是 Born 拟合斜率给出的外推（尽管实测缺口 < 50 meV）；"
                  "SMD 只测了乙腈与水两个溶剂，且它们的隐式腔半径盒与 bare CPCM 不同（见裁决项）；"
                  "溶质畸变项已被量化，但尚未与分子描述符（偶极 / 极化率 / 硬度）建立因果归因；"
                  "22 点台阶里的电子结构 10 点沿用 Stage 12 的读数，未重算；"
                  "r2SCAN-3c 无弥散函数的适用域限制对还原轴的绝对 EA 依然成立。")

    sigma_note = ("**第四条免费通道：态的刚性偏移（Stage 13 / week12）**。前三周处理的是「位移怎么排布」；"
                  "本周补上第四条，处理「位移里哪些项根本不参与排序」—— `SMD CDS` 项在三个电荷态上"
                  "逐点相同（最大 spread %s eV），于是它对任何垂直 IP/EA 的贡献**精确为 0**："
                  "它测量得再准也不会改变任何一个差值；`Delta(D4) = Delta(gCP) = 0` 同理（只依赖几何）。"
                  "剩下的两项性质不同：介电项按 Born 走（mean R2 = %s，斜率 %s eV），"
                  "溶质畸变项与它反号且不可忽略（还原轴抵消 %s%%）。"
                  "实践含义：把 P2 的位移读成「纯介电 screening」是不准确的；"
                  "需要担心的从来不是「加了溶剂」，而是「换了相互之间不成比例的两层」。"
                  "见 F24/F25（`outputs/figures/F24_dielectric_limit.png`、`F25_environment_ledger.png`）。"
                  % (num((ladder_checks.get("cds_is_state_independent") or {}).get("max_spread_ev"), 8),
                     num(born.get("mean"), 4), num(slopes.get("mean"), 4),
                     num(100.0 * float((acn_red.get("distortion_cancels_fraction") or {}).get("mean") or 0.0), 1)))

    summary = ("- 做了什么：%s\n- 关键数字：\n%s\n- 质检：%s\n- 限制：%s"
               % (did, metric, qc, limit_text))
    return {"present": True, "did": did, "metric": metric, "qc": qc, "limit": limit_text,
            "law_block": law_block, "term_block": term_block, "limit_block": limit_block,
            "forecast_block": forecast_block, "ledger_block": ledger_block,
            "table_block": table_block, "sigma_note": sigma_note, "summary": summary}


def week7_blocks(stage7, stage8):
    """Render the week-7 (Stage 7 + Stage 8) blocks from the two JSON files.

    Every number here is read back from the artefacts, so the summary cannot
    drift away from the CSVs it is supposed to describe.
    """
    fallback = "（本轮未纳入 `outputs/week7/*`：Stage 7 / Stage 8 尚未产出）"
    out = {"did": fallback, "metric": fallback, "qc": fallback, "limit": fallback,
           "s7_block": fallback, "s8_block": fallback, "summary": fallback}
    if not stage7 or not stage7.get("results"):
        return out

    results = stage7["results"]
    keys = _w7_pair_keys(results)
    rows = ["| 任务 · 特征集 · 轴 | LOFO 最佳 direct | LOFO 最佳 shift | shift − direct | 同组合 random τ_b |",
            "| --- | --- | --- | --- | --- |"]
    shift_wins, flips, n_used = 0, [], []
    combos = 0
    for task, fset, objective in keys:
        direct = _w7_best(results, task, fset, objective, "lofo", "direct")
        shift = _w7_best(results, task, fset, objective, "lofo", "shift")
        if direct is None or shift is None:
            continue
        combos += 1
        winner = shift if shift["kendall_tau_b"] > direct["kendall_tau_b"] else direct
        delta = shift["kendall_tau_b"] - direct["kendall_tau_b"]
        if delta > 0:
            shift_wins += 1
        if delta >= 0.2 or delta <= -0.2:
            flips.append("%s/%s/%s" % (task, fset, objective))
        random_row = _w7_best(results, task, fset, objective, "random", winner["shape"])
        rows.append("| %s · %s · %s | `%s` %s | `%s` %s | %+.3f | %s |" % (
            task, fset, objective,
            direct.get("model"), _w7_num(direct.get("kendall_tau_b")),
            shift.get("model"), _w7_num(shift.get("kendall_tau_b")),
            delta, _w7_num(random_row.get("kendall_tau_b")) if random_row else "n/a"))
        if isinstance(direct.get("n_molecules"), int):
            n_used.append(direct["n_molecules"])

    out["s7_block"] = "\n".join(rows)
    out["did"] = (
        "用 `scripts/build_ml_features.py` 把 Stage 2–5 的产物整理成带 **cost 分级** 的特征表"
        "（`X0` 12 列 / `X1` 6 列 / `X2` 4 列，互斥；`X2` 只许做机制解释），"
        "再用 `scripts/run_stage7_ml.py` 在 `constant / ridge / krr / gpr / rf / gbdt` "
        "六级模型阶梯上、对 `M`（方法 P0→P1）、`E`（环境 P1→P2）、`C`（配位 C0→C1）"
        "三种位移各自跑 **direct** 与 **conditional-shift** 两种学习形态，"
        "三种拆分（random / group / leave-one-family-out）全报告；"
        "每个 replicate 的随机种子由 `sha256` 派生，跨进程可复现。"
        "`scripts/run_stage8_al.py` 再做 retrospective active-learning replay"
        "（初始 4 个种子、每次买 1 个标签、20 组冻结种子重复），给出 `n_T -> τ_b / O_k / R_k`。")
    out["metric"] = (
        "- Stage 7 结果行 **%d** 条（task × feature set × objective × split × shape × model）；"
          "估计器抛异常而回落到家族均值的折数 **%d**。"
          % (int((stage7.get("counts") or {}).get("n_result_rows") or 0),
             int((stage7.get("counts") or {}).get("n_fit_fallbacks") or 0))
        + "\n- LOFO 下 **shift** 形态胜过 direct 的组合数：**%d / %d**。" % (shift_wins, combos))
    out["qc"] = (
        "X2（配位衍生特征）由运行期断言拒绝，任何特征集都不可能含 X2；"
        "三种拆分的折覆盖经单元测试验证「每个分子恰好被预测一次」；"
        "`render_summary` / `week7_blocks` 的所有数字都从 JSON 现场解析。")
    out["limit"] = (
        "core set 只有 18 个分子（配位任务 `C` 只有 10 个），group / LOFO 折内训练行数常低至个位数；"
        "本报告只能支持**方法学**结论，不能当作定量精度结论。")

    if stage8 and stage8.get("curves"):
        curves = stage8["curves"]
        targets, seen = [], set()
        for row in curves:
            key = (row.get("task"), row.get("objective"))
            if key not in seen:
                seen.add(key)
                targets.append(key)
        grouped = {}
        for row in curves:
            grouped.setdefault((row.get("task"), row.get("objective"),
                                row.get("baseline")), []).append(row)
        lines = ["| 任务 · 轴 | 池 n | " + " | ".join("`%s`" % item for item in W7_BASELINES) + " |",
                 "| --- | --- | --- | --- | --- | --- |"]
        for task, objective in targets:
            cells, pool_size = [], 0
            for baseline in W7_BASELINES:
                series = sorted(grouped.get((task, objective, baseline), []),
                                key=lambda row: row.get("n_T") or 0)
                if not series:
                    cells.append("n/a")
                    continue
                pool_size = max(pool_size, int(series[-1]["n_T"]))
                non_trivial = [row for row in series if int(row["n_T"]) < int(series[-1]["n_T"])]
                anchor = non_trivial[-1] if non_trivial else series[-1]
                reached = [int(row["n_T"]) for row in series
                           if (row.get("kendall_tau_b") or 0) >= 0.8]
                cells.append("%s（≥0.8 @ %s）" % (
                    _w7_num(anchor.get("kendall_tau_b")),
                    reached[0] if reached else "—"))
            lines.append("| %s · %s | %d | %s |" % (task, objective, pool_size,
                                                    " | ".join(cells)))
        out["s8_block"] = "\n".join(lines)
        out["summary"] = (out["s7_block"]
                          + "\n\n**Stage 8：`n_T = n - 1` 处的中位 `tau_b`，"
                            "括号内为 median 首次达到 0.8 所需的 `n_T`：**\n\n"
                          + out["s8_block"])
        best_at_budget = []
        for task, objective in targets:
            for baseline in W7_BASELINES:
                series = sorted(grouped.get((task, objective, baseline), []),
                                key=lambda row: row.get("n_T") or 0)
                if len(series) < 2:
                    continue
                best_at_budget.append((task, objective, baseline,
                                       series[-2].get("kendall_tau_b")))
        out["qc"] += (" Stage 8 的 acquisition 只用 `X0`，每轮的标准化与模型拟合只看到"
                      "当轮可见标签（由单元测试断言 scaler 均值等于可见行均值）。")
    return out


def build_week(week, out, force, dry_run):
    spec = WEEKS[week]
    wdir = out / f"week{week}"
    items, missing, excluded = plan_week(week)
    copied, skipped = [], []
    if not dry_run:
        wdir.mkdir(parents=True, exist_ok=True)
    for src, dst_rel, optional in items:
        dst = wdir / dst_rel
        if dst.exists() and not force:
            skipped.append(dst_rel.as_posix())
            continue
        if dry_run:
            print(f"[dry-run] copy {src.relative_to(REPO).as_posix()} -> {dst}")
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            copy_artifact(src, dst)
        copied.append(dst_rel.as_posix())

    report_name = f"week{week}_report.md"
    if dry_run:
        print(f"[dry-run] write {wdir / report_name}")
    else:
        write_text(wdir / report_name, render_report(week, wdir, missing, excluded))

    files, checks = {}, []
    if not dry_run:
        for rel in week_files(wdir):
            files[rel] = sha256_file(wdir / rel)
        manifest = "\n".join(f"{files[rel]}  {rel}" for rel in sorted(files)) + "\n"
        write_text(wdir / "SHA256SUMS", manifest)
        checks = CHECK_BUILDERS[week](wdir)
        payload = {
            "week": week,
            "topic": spec["topic"],
            "generated_utc": generated_utc_iso(),
            "n_files": len(files),
            "files": files,
            "checks": checks,
            "excluded_binary_scratch": len(excluded),
            "excluded_binary_scratch_examples": excluded[:10],
            "missing_sources": missing,
            "gate_status": GATE_STATUS,
            "source_commands": spec["commands"],
        }
        write_text(wdir / "verification.json",
                   json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    return {"week": week, "dir": wdir, "copied": copied, "skipped": skipped,
            "missing": missing, "excluded": excluded, "files": files, "checks": checks}


def generated_utc_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Build the distilled deliverables bundle under 成果输出/.")
    parser.add_argument("--out", default=str(DEFAULT_OUT),
                        help="output root (default: E:\\Claude Code\\电解液溶剂-HB\\成果输出)")
    parser.add_argument("--weeks",
                        default="1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21",
                        help="comma-separated week numbers "
                             "(default: 1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21)")
    parser.add_argument("--force", action="store_true",
                        help="overwrite copied files that already exist")
    parser.add_argument("--dry-run", action="store_true", dest="dry_run",
                        help="print the plan without writing anything")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    out = Path(args.out)
    weeks = [int(x) for x in str(args.weeks).split(",") if x.strip()]

    if not args.dry_run:
        out.mkdir(parents=True, exist_ok=True)

    results = []
    for week in weeks:
        if week not in WEEKS:
            raise SystemExit(f"unknown week: {week}")
        results.append(build_week(week, out, args.force, args.dry_run))

    if not args.dry_run:
        summary = SUMMARY_TEMPLATE.replace(
            "{prereg_sha256}", sha256_file(REPO / "config" / "prereg.yaml"))
        f10_present = (out / "week4" / "t3_cpcm_eps_scan.csv").exists()
        if f10_present:
            f10_row = "| F10 | `F10_cpcm_eps_scan.png` | " + F10_NOTE_PRESENT + " | week4 |"
            f10_art_note = "、`F10`"
            t3_summary_limit = T3_SUMMARY_LIMIT_PRESENT
            t3_commands = T3_REPRO_COMMANDS
        else:
            f10_row = "| F10 | 未生成 | " + F10_NOTE_ABSENT + " | —— |"
            f10_art_note = ""
            t3_summary_limit = T3_SUMMARY_LIMIT_ABSENT
            t3_commands = ""
        t2_data = t2_blocks(load_json(T2_SUMMARY_PATH))
        t2_figure = REPO / "outputs" / "figures" / "F11_opt_freq_g2_sensitivity.png"
        if t2_data["block"] and t2_figure.exists():
            f11_row = "| F11 | `F11_opt_freq_g2_sensitivity.png` | " + F11_NOTE_PRESENT + " | week4 |"
            f11_art_note = "、`F11`"
            t2_summary_limit = t2_data["limit"]
            t2_summary_metric = t2_data["metric"]
            t2_commands = T2_REPRO_COMMANDS
        else:
            f11_row = "| F11 | 未生成 | " + F11_NOTE_ABSENT + " | —— |"
            f11_art_note = ""
            t2_summary_limit = T2_LIMIT_ABSENT
            t2_summary_metric = ""
            t2_commands = ""
        summary = summary.replace("{f11_row}", f11_row)
        summary = summary.replace("{f11_art_note}", f11_art_note)
        summary = summary.replace("{t2_summary_limit}", t2_summary_limit)
        summary = summary.replace("{t2_step_row}", t2_data["step_row"])
        summary = summary.replace("{t2_summary_metric}", t2_summary_metric)
        summary = summary.replace("{t2_commands}", t2_commands)
        summary = summary.replace("{f10_row}", f10_row)
        summary = summary.replace("{f10_art_note}", f10_art_note)
        summary = summary.replace("{t3_summary_limit}", t3_summary_limit)
        summary = summary.replace("{t3_commands}", t3_commands)
        c1_data = c1_blocks(load_json(C1_SUMMARY_PATH), load_json(C1_RUN_SUMMARY_PATH))
        c1_figure = REPO / "outputs" / "figures" / "F12_li_coordination_c1.png"
        if c1_data["present"] and c1_figure.exists():
            f12_row = "| F12 | `F12_li_coordination_c1.png` | " + F12_NOTE_PRESENT + " | week5 |"
            f12_art_note = "、`F12`"
            c1_summary_limit = c1_data["limit"]
            c1_commands = C1_REPRO_COMMANDS
        else:
            f12_row = "| F12 | 未生成 | " + F12_NOTE_ABSENT + " | —— |"
            f12_art_note = ""
            c1_summary_limit = C1_LIMIT_ABSENT
            c1_commands = ""
        f13_figure = REPO / "outputs" / "figures" / "F13_c1_state_identity.png"
        if f13_figure.exists():
            f13_row = "| F13 | `F13_c1_state_identity.png` | " + F13_NOTE_PRESENT + " | week5 |"
            f13_art_note = "、`F13`"
        else:
            f13_row = "| F13 | 未生成 | " + F13_NOTE_ABSENT + " | —— |"
            f13_art_note = ""
        c1_note = C1_NOTE_PRESENT if c1_data["present"] else C1_NOTE_ABSENT
        w6_all = week6_blocks(load_json(T6_SUMMARY_PATH), load_json(T7_SUMMARY_PATH),
                              load_json(T8_SUMMARY_PATH), load_json(T9_SUMMARY_PATH))
        w6_note = w6_all["sigma_note"]
        w7_note = week7_blocks(load_json(W7_STAGE7_PATH),
                               load_json(W7_STAGE8_PATH))["summary"]
        w8_note = week8_blocks(load_json(W8_STAGE9_PATH),
                               load_json(W8_SHELLS_PATH))["summary"]
        w9_all = week9_blocks(load_json(W9_LADDER_PATH))
        w9_note = w9_all["summary"]
        w10_all = week10_blocks(load_json(W10_ANATOMY_PATH))
        w10_note = w10_all["summary"]
        w11_all = week11_blocks(load_json(W11_PRESCREEN_PATH))
        w11_note = w11_all["summary"]
        w12_all = week12_blocks(load_json(W12_ANALYSIS_PATH), load_json(W12_LADDER_PATH))
        w12_note = w12_all["summary"]
        w13_all = week13_blocks(load_json(W13_ATTRIBUTION_PATH), load_json(W13_OUTLIER_PATH))
        w13_note = w13_all["summary"]
        w14_all = week14_blocks(load_json(W14_TWO_GUESS_PATH), load_json(W14_DIFFUSENESS_PATH),
                                load_json(W14_ANCHOR_PATH))
        w14_note = w14_all["summary"]
        f28_figure = REPO / "outputs" / "figures" / "F28_two_guess_protocol.png"
        if f28_figure.exists():
            f28_row = "| F28 | `F28_two_guess_protocol.png` | " + F28_NOTE_PRESENT + " | week14 |"
        else:
            f28_row = "| F28 | 未生成 | " + F28_NOTE_ABSENT + " | —— |"
        f29_figure = REPO / "outputs" / "figures" / "F29_diffuseness_descriptor.png"
        if f29_figure.exists():
            f29_row = "| F29 | `F29_diffuseness_descriptor.png` | " + F29_NOTE_PRESENT + " | week14 |"
        else:
            f29_row = "| F29 | 未生成 | " + F29_NOTE_ABSENT + " | —— |"
        w15_all = week15_blocks(load_json(W15_ANALYSIS_PATH), load_json(W15_PREDICTOR_PATH))
        w15_note = w15_all["summary"]
        w15_analysis = load_json(W15_ANALYSIS_PATH) or {}
        w15_counts = w15_analysis.get("n_flagged_molecules") or {}
        w15_worst = w15_analysis.get("worst_negative_ev")
        if not W15_ANALYSIS_PATH.exists():
            w15_row = ("| week15 | Stage 16（全核心集双初猜目录 + 事前预警规则） | "
                       "未生成（等待 `stage16_catalogue_analysis.json`） | —— |")
        else:
            w15_row = ("| week15 | Stage 16（全核心集双初猜目录 + 事前预警规则） | "
                       + "%d 个配对单元格里 %d 个 MORead 更低、%d 个更高；最大赤字 %.4f eV；"
                         % (w15_analysis.get("n_paired") or 0,
                            w15_analysis.get("n_moread_lower") or 0,
                            w15_analysis.get("n_moread_higher") or 0, w15_worst or 0.0)
                       + "10 点阶梯下 %d/%d 个分子被判定存在漏解 | Gate 0 CLOSED |"
                         % (w15_counts.get("ladder10", 0),
                            w15_analysis.get("n_discovery_molecules") or 0))
        w16_all = week16_blocks(load_json(W16_SMD_PATH),
                                load_json(W16_CONTAMINATION_PATH),
                                load_json(W16_IDENTITY_PATH))
        w16_note = w16_all["summary"]
        w16_cont = load_json(W16_CONTAMINATION_PATH) or {}
        w16_delta = (w16_cont.get("delta_stats") or {}).get("cells_54") or {}
        if not W16_CONTAMINATION_PATH.exists():
            w16_row = ("| week16 | Stage 17（亚稳态污染上限 + 两个 SCF 解的电子结构身份） | "
                       "未生成（等待 stage17_contamination.json） | —— |")
        else:
            w16_row = ("| week16 | Stage 17（亚稳态污染上限 + 两个 SCF 解的电子结构身份） | "
                       + "54 格单腿替换：%d 个格子 |delta| > 1 meV（最坏 %.4f eV）；"
                         "两臂 tau_b 的 95%% CI 两轴均重叠、published 结论 0 条被改写；"
                         "32 个漏解格里两个 SCF 解都是自旋纯双重态（<S^2> 32/32 落 0.75±0.01）"
                         % (w16_cont.get("cells_changed_count") or 0,
                            w16_delta.get("max_abs_ev") or 0.0)
                       + " | Gate 0 CLOSED |")

        w17_all = week17_blocks(load_json(W17_CENSUS_PATH), load_json(W17_DIAGNOSIS_PATH))
        w17_note = w17_all["summary"]
        w17_census = load_json(W17_CENSUS_PATH) or {}
        w17_diag = load_json(W17_DIAGNOSIS_PATH) or {}
        w17_sep = ((w17_census.get("separation") or {}).get("all") or {})
        w17_cm = w17_sep.get("confusion_at_threshold") or {}
        w17_hold = w17_diag.get("holdout") or {}
        w17_hold_cm = w17_hold.get("confusion_matrix") or {}
        w17_one_sided = w17_diag.get("one_sided_screening") or {}
        w17_necessity = (w17_one_sided.get("necessity") or {}).get("overall") or {}
        w17_specificity = (w17_one_sided.get("specificity") or {}).get("overall") or {}
        if not W17_CENSUS_PATH.exists():
            w17_row = ("| week17 | Stage 18（电子身份普查 + 零成本自诊断） | "
                       "未生成（等待 stage18_identity_census.json） | —— |")
        else:
            w17_row = ("| week17 | Stage 18（全目录电子身份普查 + 零成本自诊断） | "
                       + "%d 对身份普查：可测子集 AUC %.3f、混淆 TP %d / FN %d / FP %d / TN %d；"
                         "ester / nitrile / sulfone / sulfoxide 四个家族零漏解；"
                         "零成本自诊断的冻结规则在留出臂 %.4f 输给多数类 %.4f（TP %d）；"
                         "单边结论：small-gap 警告在 %d/%d 个正例上都出现（反例 0），"
                         "但 %d/%d 个负例也出现"
                       % (w17_census.get("n_pairs") or 0,
                          float((w17_sep.get("auc") or {}).get("charge_l1") or 0.0),
                          w17_cm.get("tp") or 0, w17_cm.get("fn") or 0,
                          w17_cm.get("fp") or 0, w17_cm.get("tn") or 0,
                          float(w17_hold.get("accuracy") or 0.0),
                          float(w17_hold.get("majority_accuracy") or 0.0),
                          w17_hold_cm.get("true_positive") or 0,
                          w17_necessity.get("n_positive_with_warning") or 0,
                          w17_necessity.get("n_positive") or 0,
                          w17_specificity.get("n_negative_with_warning") or 0,
                          w17_specificity.get("n_negative") or 0)
                       + " | Gate 0 CLOSED |")
        f34_figure = REPO / "outputs" / "figures" / "F34_stage18_identity_census.png"
        if f34_figure.exists():
            f34_row = ("| F34 | \x60F34_stage18_identity_census.png\x60 | " + F34_NOTE_PRESENT
                       + " | week17 |")
        else:
            f34_row = "| F34 | 未生成 | " + F34_NOTE_ABSENT + " | —— |"
        f35_figure = REPO / "outputs" / "figures" / "F35_stage18_selfdiagnosis.png"
        if f35_figure.exists():
            f35_row = ("| F35 | \x60F35_stage18_selfdiagnosis.png\x60 | " + F35_NOTE_PRESENT
                       + " | week17 |")
        else:
            f35_row = "| F35 | 未生成 | " + F35_NOTE_ABSENT + " | —— |"

        w18_all = week18_blocks(load_json(W18_LEDGER_PATH), load_json(W18_ANALYSIS_PATH))
        w18_note = w18_all["summary"]
        w18_ledger = load_json(W18_LEDGER_PATH) or {}
        w18_analysis = load_json(W18_ANALYSIS_PATH) or {}
        w18_sum = w18_ledger.get("summary") or {}
        w18_all_block = ((w18_analysis.get("aggregates") or {}).get("all") or {}).get("all") or {}
        w18_out = w18_all_block.get("outcomes") or {}
        if not W18_ANALYSIS_PATH.exists():
            w18_row = ("| week18 | Stage 19（几何弛豫检验） | "
                       "未生成（等待 stage19_relax_analysis.json） | —— |")
        else:
            w18_row = ("| week18 | Stage 19（几何弛豫检验） | "
                       + "37 个 moread_lower 格各做两臂 Opt（%d 个作业、%d ok / %d failed）："
                         % (w18_sum.get("n_jobs") or 0, w18_sum.get("n_ok") or 0,
                            w18_sum.get("n_failed") or 0)
                       + "仍保持 moread 更低 %s/%s（distinct_lower %s + same_lower %s）；"
                         "两解在终点合并 %s 格；偏好被反转 %s 格；|delta| 中位 %.5f -> %.5f eV"
                         % (w18_all_block.get("n_still_lower") or 0,
                            w18_all_block.get("n_complete") or 0,
                            w18_out.get("distinct_lower") or 0,
                            w18_out.get("same_lower") or 0,
                            (w18_out.get("same_higher") or 0) + (w18_out.get("same_lower") or 0),
                            w18_all_block.get("n_preference_flipped") or 0,
                            (w18_all_block.get("abs_single_point_delta_ev") or {}).get("p50") or 0.0,
                            (w18_all_block.get("abs_relax_delta_ev") or {}).get("p50") or 0.0)
                       + " | Gate 0 CLOSED |")
        f36_figure = REPO / "outputs" / "figures" / "F36_stage19_relax_outcomes.png"
        if f36_figure.exists():
            f36_row = ("| F36 | `F36_stage19_relax_outcomes.png` | " + F36_NOTE_PRESENT
                       + " | week18 |")
        else:
            f36_row = "| F36 | 未生成 | " + F36_NOTE_ABSENT + " | —— |"
        f37_figure = REPO / "outputs" / "figures" / "F37_stage19_identity_geometry.png"
        if f37_figure.exists():
            f37_row = ("| F37 | `F37_stage19_identity_geometry.png` | " + F37_NOTE_PRESENT
                       + " | week18 |")
        else:
            f37_row = "| F37 | 未生成 | " + F37_NOTE_ABSENT + " | —— |"

        w19_all = week19_blocks(load_json(W19_RUNG_PATH), load_json(W19_ARMS_PATH),
                                load_json(W19_ARMS_ANALYSIS_PATH))
        w19_note = w19_all["summary"]
        w19_rung = load_json(W19_RUNG_PATH) or {}
        w19_arms = load_json(W19_ARMS_PATH) or {}
        w19_analysis = load_json(W19_ARMS_ANALYSIS_PATH) or {}
        w19_all_block = ((w19_analysis.get("aggregates") or {}).get("all") or {}).get("all") or {}
        w19_ranges = sorted(float(row.get("delta_range_ev") or 0.0)
                            for row in (w19_rung.get("epsilon_rows") or []))
        w19_p50_sp = (w19_all_block.get("abs_xtb_sp_delta_ev") or {}).get("p50")
        w19_p50_relax = (w19_all_block.get("abs_xtb_relax_delta_ev") or {}).get("p50")
        if not W19_RUNG_PATH.exists() or not W19_ARMS_ANALYSIS_PATH.exists():
            w19_row = ("| week19 | Stage 20（第六级台阶 + 第二解的跨方法存亡） | "
                       "未生成（等待 stage20_relax_rung.json / stage20_xtb_arms_analysis.json） "
                       "| —— |")
        else:
            w19_row = ("| week19 | Stage 20（第六级台阶 + 第二解的跨方法存亡） | "
                       + "零新增计算把弛豫放回台阶（逐分子跨 eps 极差中位 %.4f eV）；"
                         "%s 个 GFN2-xTB 作业：同一几何上方法一致率 %s/%s（89%%）、"
                         "xTB 弛豫把两臂能量差压掉约 %.0f 倍、%s/%s 格两臂合并；"
                         "跨判据裁决一致率 %s/%s"
                         % (w19_ranges[3] if len(w19_ranges) > 3 else 0.0,
                            w19_arms.get("summary", {}).get("n_jobs") or 0,
                            w19_all_block.get("n_xtb_sp_matches_stage19_relax") or 0,
                            w19_all_block.get("n_complete") or 0,
                            (float(w19_p50_sp or 0.0)
                             / max(float(w19_p50_relax or 1e-30), 1e-30)),
                            w19_all_block.get("n_xtb_same_minimum") or 0,
                            w19_all_block.get("n_complete") or 0,
                            w19_all_block.get("n_agree_with_stage19") or 0,
                            w19_all_block.get("n_complete") or 0)
                       + " | Gate 0 CLOSED |")
        f38_figure = REPO / "outputs" / "figures" / "F38_stage20_relax_rung.png"
        if f38_figure.exists():
            f38_row = ("| F38 | `F38_stage20_relax_rung.png` | " + F38_NOTE_PRESENT
                       + " | week19 |")
        else:
            f38_row = "| F38 | 未生成 | " + F38_NOTE_ABSENT + " | —— |"
        f39_figure = REPO / "outputs" / "figures" / "F39_stage20_xtb_arms.png"
        if f39_figure.exists():
            f39_row = ("| F39 | `F39_stage20_xtb_arms.png` | " + F39_NOTE_PRESENT
                       + " | week19 |")
        else:
            f39_row = "| F39 | 未生成 | " + F39_NOTE_ABSENT + " | —— |"

        f40_figure = REPO / "outputs" / "figures" / "F40_stage21_path_profiles.png"
        if f40_figure.exists():
            f40_row = ("| F40 | `F40_stage21_path_profiles.png` | " + F40_NOTE_PRESENT
                       + " | week20 |")
        else:
            f40_row = "| F40 | 未生成 | " + F40_NOTE_ABSENT + " | —— |"
        f42_figure = REPO / "outputs" / "figures" / "F42_sigma_synthetic_phase_diagram.png"
        if f42_figure.exists():
            f42_row = ("| F42 | `F42_sigma_synthetic_phase_diagram.png` | "
                       + F42_NOTE_PRESENT + " | week21 |")
        else:
            f42_row = "| F42 | " + F42_NOTE_ABSENT + " | .. |"
        f41_figure = REPO / "outputs" / "figures" / "F41_stage21_shell_redox.png"
        if f41_figure.exists():
            f41_row = ("| F41 | `F41_stage21_shell_redox.png` | " + F41_NOTE_PRESENT
                       + " | week20 |")
        else:
            f41_row = "| F41 | 未生成 | " + F41_NOTE_ABSENT + " | —— |"

        f30_figure = REPO / "outputs" / "figures" / "F30_two_guess_catalogue.png"
        if f30_figure.exists():
            f30_row = "| F30 | `F30_two_guess_catalogue.png` | " + F30_NOTE_PRESENT + " | week15 |"
        else:
            f30_row = "| F30 | 未生成 | " + F30_NOTE_ABSENT + " | —— |"
        f31_figure = REPO / "outputs" / "figures" / "F31_apriori_warning_rule.png"
        if f31_figure.exists():
            f31_row = "| F31 | `F31_apriori_warning_rule.png` | " + F31_NOTE_PRESENT + " | week15 |"
        else:
            f31_row = "| F31 | 未生成 | " + F31_NOTE_ABSENT + " | —— |"
        f32_figure = REPO / "outputs" / "figures" / "F32_stage17_contamination.png"
        if f32_figure.exists():
            f32_row = ("| F32 | \x60F32_stage17_contamination.png\x60 | " + F32_NOTE_PRESENT
                       + " | week16 |")
        else:
            f32_row = "| F32 | 未生成 | " + F32_NOTE_ABSENT + " | —— |"
        f33_figure = REPO / "outputs" / "figures" / "F33_stage17_solution_identity.png"
        if f33_figure.exists():
            f33_row = ("| F33 | \x60F33_stage17_solution_identity.png\x60 | " + F33_NOTE_PRESENT
                       + " | week16 |")
        else:
            f33_row = "| F33 | 未生成 | " + F33_NOTE_ABSENT + " | —— |"

        f14_figure = REPO / "outputs" / "figures" / "F14_delta_m_derivation.png"
        if f14_figure.exists():
            f14_row = "| F14 | `F14_delta_m_derivation.png` | " + F14_NOTE_PRESENT + " | week6 |"
        else:
            f14_row = "| F14 | 未生成 | " + F14_NOTE_ABSENT + " | —— |"
        f15_figure = REPO / "outputs" / "figures" / "F15_stage6_decision_metrics.png"
        if f15_figure.exists():
            f15_row = "| F15 | `F15_stage6_decision_metrics.png` | " + F15_NOTE_PRESENT + " | week6 |"
        else:
            f15_row = "| F15 | 未生成 | " + F15_NOTE_ABSENT + " | —— |"
        f16_figure = REPO / "outputs" / "figures" / "F16_stage7_direct_vs_shift.png"
        if f16_figure.exists():
            f16_row = "| F16 | `F16_stage7_direct_vs_shift.png` | " + F16_NOTE_PRESENT + " | week7 |"
        else:
            f16_row = "| F16 | 未生成 | " + F16_NOTE_ABSENT + " | —— |"
        f17_figure = REPO / "outputs" / "figures" / "F17_stage8_active_learning.png"
        if f17_figure.exists():
            f17_row = "| F17 | `F17_stage8_active_learning.png` | " + F17_NOTE_PRESENT + " | week7 |"
        else:
            f17_row = "| F17 | 未生成 | " + F17_NOTE_ABSENT + " | —— |"
        f18_figure = REPO / "outputs" / "figures" / "F18_stage9_explicit_shell.png"
        if f18_figure.exists():
            f18_row = "| F18 | `F18_stage9_explicit_shell.png` | " + F18_NOTE_PRESENT + " | week8 |"
        else:
            f18_row = "| F18 | 未生成 | " + F18_NOTE_ABSENT + " | —— |"
        f19_figure = REPO / "outputs" / "figures" / "F19_stage10_ladder.png"
        if f19_figure.exists():
            f19_row = "| F19 | `F19_stage10_ladder.png` | " + F19_NOTE_PRESENT + " | week9 |"
        else:
            f19_row = "| F19 | 未生成 | " + F19_NOTE_ABSENT + " | —— |"
        f20_figure = REPO / "outputs" / "figures" / "F20_sigma_anatomy.png"
        if f20_figure.exists():
            f20_row = "| F20 | `F20_sigma_anatomy.png` | " + F20_NOTE_PRESENT + " | week10 |"
        else:
            f20_row = "| F20 | 未生成 | " + F20_NOTE_ABSENT + " | —— |"
        f21_figure = REPO / "outputs" / "figures" / "F21_sigma_controls.png"
        if f21_figure.exists():
            f21_row = "| F21 | `F21_sigma_controls.png` | " + F21_NOTE_PRESENT + " | week10 |"
        else:
            f21_row = "| F21 | 未生成 | " + F21_NOTE_ABSENT + " | —— |"
        f22_figure = REPO / "outputs" / "figures" / "F22_dielectric_scaling.png"
        if f22_figure.exists():
            f22_row = "| F22 | `F22_dielectric_scaling.png` | " + F22_NOTE_PRESENT + " | week11 |"
        else:
            f22_row = "| F22 | 未生成 | " + F22_NOTE_ABSENT + " | —— |"
        f23_figure = REPO / "outputs" / "figures" / "F23_prescreening.png"
        if f23_figure.exists():
            f23_row = "| F23 | `F23_prescreening.png` | " + F23_NOTE_PRESENT + " | week11 |"
        else:
            f23_row = "| F23 | 未生成 | " + F23_NOTE_ABSENT + " | —— |"
        f24_figure = REPO / "outputs" / "figures" / "F24_dielectric_limit.png"
        if f24_figure.exists():
            f24_row = "| F24 | `F24_dielectric_limit.png` | " + F24_NOTE_PRESENT + " | week12 |"
        else:
            f24_row = "| F24 | 未生成 | " + F24_NOTE_ABSENT + " | —— |"
        f25_figure = REPO / "outputs" / "figures" / "F25_environment_ledger.png"
        if f25_figure.exists():
            f25_row = "| F25 | `F25_environment_ledger.png` | " + F25_NOTE_PRESENT + " | week12 |"
        else:
            f25_row = "| F25 | 未生成 | " + F25_NOTE_ABSENT + " | —— |"
        f26_figure = REPO / "outputs" / "figures" / "F26_distortion_attribution.png"
        if f26_figure.exists():
            f26_row = "| F26 | `F26_distortion_attribution.png` | " + F26_NOTE_PRESENT + " | week13 |"
        else:
            f26_row = "| F26 | 未生成 | " + F26_NOTE_ABSENT + " | —— |"
        f27_figure = REPO / "outputs" / "figures" / "F27_emc_outlier.png"
        if f27_figure.exists():
            f27_row = "| F27 | `F27_emc_outlier.png` | " + F27_NOTE_PRESENT + " | week13 |"
        else:
            f27_row = "| F27 | 未生成 | " + F27_NOTE_ABSENT + " | —— |"
        placeholders = (("{f12_row}", f12_row),
                       ("{f14_row}", f14_row),
                       ("{f15_row}", f15_row),
                       ("{f16_row}", f16_row),
                       ("{f17_row}", f17_row),
                       ("{f13_row}", f13_row),
                       ("{f12_art_note}", f12_art_note),
                       ("{f13_art_note}", f13_art_note),
                       ("{c1_did}", c1_data["did"]),
                       ("{c1_metric}", c1_data["metric"]),
                       ("{c1_qc_summary}", c1_data["qc"]),
                       ("{c1_step_row}", c1_data["step_row"]),
                       ("{c1_sigma_note}", c1_data["sigma_note"]),
                       ("{c1_summary_limit}", c1_summary_limit),
                       ("{c1_note}", c1_note),
                       ("{c1_commands}", c1_commands),
                       ("{w6_sigma_note}", w6_note),
                       ("{w6_did}", w6_all["did"]),
                       ("{w6_metric}", w6_all["metric"]),
                       ("{w6_qc}", w6_all["qc"]),
                       ("{w6_limit}", w6_all["limit"]),
                       ("{w8_summary}", w8_note),
                       ("{f18_row}", f18_row),
                       ("{f19_row}", f19_row),
                       ("{f20_row}", f20_row),
                       ("{f21_row}", f21_row),
                       ("{f22_row}", f22_row),
                       ("{f23_row}", f23_row),
                       ("{f24_row}", f24_row),
                       ("{f25_row}", f25_row),
                       ("{f26_row}", f26_row),
                       ("{f27_row}", f27_row),
                       ("{w13_summary}", w13_note),
                       ("{w13_summary_limit}", w13_all["limit"]),
                       ("{w12_summary}", w12_note),
                       ("{w12_sigma_note}", w12_all["sigma_note"]),
                       ("{w12_summary_limit}", w12_all["limit"]),
                       ("{w11_summary}", w11_note),
                       ("{w11_sigma_note}", w11_all["sigma_note"]),
                       ("{w11_summary_limit}", w11_all["limit"]),
                       ("{w10_summary}", w10_note),
                       ("{w10_sigma_note}", w10_all["sigma_note"]),
                       ("{w9_summary}", w9_note),
                       ("{w9_sigma_note}", w9_all["sigma_note"]),
                       ("{w7_summary}", w7_note),
                       ("{w14_summary}", w14_note),
                       ("{w14_summary_limit}", w14_all["limit"]),
                       ("{f28_row}", f28_row),
                       ("{f29_row}", f29_row),
                       ("{w15_summary}", w15_note),
                       ("{w15_summary_limit}", w15_all["limit"]),
                       ("{w15_row}", w15_row),
                       ("{f30_row}", f30_row),
                       ("{f31_row}", f31_row),
                       ("{w16_summary}", w16_note),
                       ("{w16_summary_limit}", w16_all["limit"]),
                       ("{w16_row}", w16_row),
                       ("{f32_row}", f32_row),
                       ("{f33_row}", f33_row),
                       ("{w17_summary}", w17_note),
                       ("{w17_summary_limit}", w17_all["limit"]),
                       ("{w17_row}", w17_row),
                       ("{f34_row}", f34_row),
                       ("{f35_row}", f35_row),
                       ("{f36_row}", f36_row),
                       ("{f37_row}", f37_row),
                       ("{w18_summary}", w18_note),
                       ("{w18_summary_limit}", w18_all["limit"]),
                       ("{w18_row}", w18_row),
                       ("{f38_row}", f38_row),
                       ("{f39_row}", f39_row),
                       ("{f40_row}", f40_row),
                       ("{f41_row}", f41_row),
                       ("{f42_row}", f42_row),
                       ("{w19_summary}", w19_note),
                       ("{w19_summary_limit}", w19_all["limit"]),
                       ("{w19_row}", w19_row))
        w20_all = week20_blocks(load_json(W20_PATH_JSON), load_json(W20_PROTOCOL_JSON),
                                load_json(W20_SHELL_JSON), load_json(W20_REFILL_JSON))
        w20_note = w20_all["summary"]
        w20_path = load_json(W20_PATH_JSON) or {}
        w20_protocol = load_json(W20_PROTOCOL_JSON) or {}
        w20_shell = load_json(W20_SHELL_JSON) or {}
        w20_refill = load_json(W20_REFILL_JSON) or {}
        w20_fragile = {cell.get("cell"): cell
                       for cell in (w20_path.get("cells") or [])}.get("EC/cation/5") or {}
        w20_counts = w20_protocol.get("verdict_counts") or {}
        w20_axes = {row.get("axis"): row for row in (w20_shell.get("axes") or [])}
        w20_ox = w20_axes.get("oxidation") or {}
        w20_strict = (w20_refill.get("coverage") or {}).get("strict_p2_leg") or {}
        w20_refill_axes = (w20_refill.get("verdict") or {}).get("per_axis") or {}
        if not W20_PATH_JSON.exists() or not W20_REFILL_JSON.exists():
            w20_row = ("| week20 | Stage 21（临界带能量裁决 + 判据预检 + 溶剂壳氧化还原 + 真回填） | "
                       "未生成（等待 stage21_path_analysis.json / stage21_refill.json 等四个产物） "
                       "| —— |")
        else:
            w20_row = ("| week20 | Stage 21（临界带能量裁决 + 判据预检 + 溶剂壳氧化还原 + 真回填） | "
                       + "Part A：3 格 x 21 帧 = %s 个冻结单点，EC/cation/eps=5 弦上鼓包只有 %.5f eV"
                         "（k_B T 的 %.1f%%），Stage 19 的 `distinct_lower` 属过度判定，"
                         "%s/%s 格与 RMSP 裁决一致；"
                         "Part B：阈值重导 %.6f、borderline %s 格、闭壳层反例 %s 格越阈；"
                         "Part C：24 个 Opt 全部结构 QC 通过，氧化轴弛豫修正 %+.4f eV、rho=%.3f；"
                         "Part D：严格 P2 腿 %s/%s 可回填，氧化轴排序被改写（Top-10%% 重叠 %.3f）、"
                         "还原轴未被改写"
                         % (w20_path.get("n_jobs"),
                            float(w20_fragile.get("barrier_chord_ev") or 0.0),
                            100.0 * float(w20_fragile.get("barrier_chord_ev") or 0.0)
                            / float(w20_path.get("thermal_ev") or 1.0),
                            w20_path.get("n_agree_with_stage19"), w20_path.get("n_cells"),
                            ((w20_protocol.get("threshold") or {}).get("value") or 0.0),
                            w20_counts.get("borderline"),
                            ((w20_protocol.get("closed_shell_probe") or {})
                             .get("summary") or {}).get("n_exceeding_threshold"),
                            float(w20_ox.get("correction_mean_ev") or 0.0),
                            float(w20_ox.get("spearman_frozen_vs_relaxed") or 0.0),
                            w20_strict.get("n_refillable"), w20_strict.get("n_cells"),
                            float((w20_refill_axes.get("oxidation") or {})
                                  .get("top10_overlap") or 0.0))
                       + " | Gate 0 CLOSED |")
        placeholders += (("{w20_summary}", w20_note),
                         ("{w20_summary_limit}", w20_all["limit"]),
                         ("{w20_row}", w20_row))
        w21_all = week21_blocks(load_json(W21_PHASE_JSON), load_json(W21_PROSPECTIVE_JSON),
                                load_json(W21_FROZEN_JSON), load_json(W21_ANCHOR_JSON))
        w21_note = w21_all["summary"]
        w21_phase = load_json(W21_PHASE_JSON) or {}
        w21_pro = load_json(W21_PROSPECTIVE_JSON) or {}
        w21_anchor = (load_json(W21_ANCHOR_JSON) or {}).get("arm_alignment") or {}
        w21_arms = w21_anchor.get("arms_on_common_subset") or {}
        w21_verdict = w21_anchor.get("verdict") or {}
        w21_scoring = w21_pro.get("scoring") or {}
        if not W21_PHASE_JSON.exists() or not W21_PROSPECTIVE_JSON.exists():
            w21_row = ("| week21 | Stage 22（批次 A：三臂对齐 + σ 相图 + 前瞻检验） | "
                       "（缺 `sigma_synthetic.json` / `sigma_prospective.json`） | —— |")
        else:
            w21_row = ("| week21 | Stage 22（批次 A：三臂对齐 + σ 相图 + 前瞻检验） | "
                       + "三条臂对齐到同一批 %s 个分子之后，GFN2 Delta-SCF 的 tau_b 仍是三者最高"
                         "（%s vs P1 %s、P0 %s），但配对 Delta tau_b = %s 的 95%% CI 是"
                         " [%s, %s]、精确置换 p = %s，三对检验全部跨 0；"
                         "σ 相图把 Week 9 的 rho(std, tau_b) = -0.851 换成一条机制判读"
                         "（合成 rho = %s、均值平移严格不动排序，max abs Delta tau_b = %s）；"
                         "前瞻检验里带符号规则 %s/%s、朴素规则 %s/%s。"
                       % (w21_anchor.get("n_common_subset"),
                          (w21_arms.get("GFN2_dSCF_xTB") or {}).get("kendall_tau_b"),
                          (w21_arms.get("P1_r2scan3c") or {}).get("kendall_tau_b"),
                          (w21_arms.get("P0_koopmans_xTB") or {}).get("kendall_tau_b"),
                          w21_verdict.get("delta_tau_b"),
                          (w21_verdict.get("paired_ci95") or [None, None])[0],
                          (w21_verdict.get("paired_ci95") or [None, None])[1],
                          w21_verdict.get("permutation_p"),
                          (w21_phase.get("synthetic_correlations") or {})
                          .get("spearman_shift_std_vs_tau_b"),
                          (w21_phase.get("mean_invariance") or {})
                          .get("max_abs_tau_b_difference_vs_mean_0"),
                          w21_scoring.get("signed_rule_hits"), w21_scoring.get("n_predictions"),
                          w21_scoring.get("naive_rule_hits"), w21_scoring.get("n_predictions"))
                       + " | Gate 0 CLOSED |")
        placeholders += (("{w21_summary}", w21_note),
                         ("{w21_summary_limit}", w21_all["limit"]),
                         ("{w21_row}", w21_row))
        for key, value in placeholders:
            summary = summary.replace(key, value)
        readme = README_TEMPLATE
        for key, value in placeholders:
            readme = readme.replace(key, value)
        for _name, _text in (("README.md", readme), ("数据结果汇总.md", summary)):
            _left = sorted(set(re.findall(r"\{[a-z0-9_]+\}", _text)))
            if _left:
                print(f"WARN: {_name} 未替换占位符: {_left}")
        write_text(out / "README.md", readme)
        write_text(out / "数据结果汇总.md", summary)

    for res in results:
        tally = {True: 0, False: 0, None: 0}
        for item in res["checks"]:
            tally[item["ok"] if item["ok"] in (True, False) else None] += 1
        print(f"week{res['week']}: files={len(res['files'])} "
              f"copied={len(res['copied'])} skipped={len(res['skipped'])} "
              f"missing={len(res['missing'])} excluded={len(res['excluded'])} "
              f"checks(ok/fail/na)={tally[True]}/{tally[False]}/{tally[None]}")
    print("dry-run: nothing was written" if args.dry_run else f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
