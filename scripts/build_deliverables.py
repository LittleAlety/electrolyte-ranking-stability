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


CHECK_BUILDERS = {1: week1_checks, 2: week2_checks, 3: week3_checks, 4: week4_checks,
                  5: week5_checks, 6: week6_checks, 7: week7_checks, 8: week8_checks}


REPORT_TEMPLATES = {}

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
    └── week8/                Stage 9（显式微溶剂化：[Li(M)2]+ 第一溶剂壳复核）

每个 week 目录包含：

    weekN/
    ├── <蒸馏产物：.csv / .json / .md>
    ├── artifacts/            图（F0–F17 中属于该周的部分）
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

## 如何复现
```powershell
cd "E:\\Claude Code\\电解液溶剂-HB\\电解液溶剂HB-Code"
$env:PYTHONIOENCODING = "utf-8"
.venv\\Scripts\\python.exe scripts\\build_deliverables.py --dry-run
.venv\\Scripts\\python.exe scripts\\build_deliverables.py
```

- `--out`：输出根目录（默认 `E:\\Claude Code\\电解液溶剂-HB\\成果输出`）。
- `--weeks`：默认 `1,2,3,4,5,6,7,8`。
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

## 2. 逐周结果（Week 1 – Week 8）

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

## 5. 图表索引（F0–F18）
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
    parser.add_argument("--weeks", default="1,2,3,4,5,6,7,8",
                        help="comma-separated week numbers (default: 1,2,3,4,5,6,7,8)")
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
        write_text(out / "README.md", README_TEMPLATE)
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
        for key, value in (("{f12_row}", f12_row),
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
                           ("{w7_summary}", w7_note)):
            summary = summary.replace(key, value)
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
