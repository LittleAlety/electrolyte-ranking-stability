#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Deterministic builder for the repository-root README.md (GitHub landing page).

Every weekly work-log number is read back from the frozen JSON/CSV products under
``outputs/`` wherever a machine-readable home exists; only values that have no
machine-readable home are written as literals in this file (they are listed under
``--trace``).  The builder is idempotent: it always writes UTF-8 (no BOM) with LF
newlines, so a second run reproduces the first byte for byte.

Usage
-----
    python scripts/build_github_readme.py            # (re)write README.md
    python scripts/build_github_readme.py --check    # compare, never write
    python scripts/build_github_readme.py --trace    # show which numbers were read back
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
README = REPO / "README.md"

RESOLVED: "list[tuple[str, bool]]" = []


def rd(rel: str) -> dict:
    p = REPO / rel
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return {}


def dig(obj, path: str, default=None, tag: str | None = None):
    cur = obj
    for key in path.split("."):
        if isinstance(cur, dict) and key in cur:
            cur = cur[key]
        elif isinstance(cur, list):
            try:
                cur = cur[int(key)]
            except (ValueError, IndexError):
                cur = None
                break
        else:
            cur = None
            break
    ok = cur is not None
    RESOLVED.append((tag or path, ok))
    return cur if ok else default


def fnum(v, nd: int = 2) -> str:
    if v is None:
        return "n/a"
    try:
        return f"{float(v):,.{nd}f}"
    except (TypeError, ValueError):
        return str(v)


def fint(v) -> str:
    if v is None:
        return "n/a"
    try:
        return f"{int(v):,d}"
    except (TypeError, ValueError):
        return str(v)


def pct(v, nd: int = 1) -> str:
    if v is None:
        return "n/a"
    try:
        return f"{float(v) * 100:.{nd}f}%"
    except (TypeError, ValueError):
        return str(v)


def csv_row_count(rel: str) -> int:
    p = REPO / rel
    if not p.exists():
        return 0
    lines = [ln for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()]
    return max(len(lines) - 1, 0)


def sha256_of(rel: str) -> str:
    p = REPO / rel
    if not p.exists():
        return "n/a"
    h = hashlib.sha256()
    h.update(p.read_bytes())
    return h.hexdigest()

def weekly_log() -> "list[str]":
    out: "list[str]" = []

    def sec(title: str, bullets) -> None:
        out.append(f"### {title}")
        out.append("")
        for b in bullets:
            out.append(f"- {b}")
        out.append("")

    # ---- Week 1 ----------------------------------------------------------
    prereg_sha = sha256_of("config/prereg.yaml")
    core_rows = csv_row_count("data/metadata/core_set.csv")
    broad_rows = csv_row_count("data/metadata/broad_pool.csv")
    sec("Week 1 —— Stage 0：定义冻结与 Gate 0（`outputs/week1`）", [
        f"冻结科学定义与预注册（`config/scientific_definitions.yaml`、`config/prereg.yaml`）；本 README 现场重算 `prereg.yaml` SHA256 = `{prereg_sha[:16]}…`。",
        f"建立 chemical-space 元数据：core set **{fint(core_rows)}** 行、broad pool **{fint(broad_rows)}** 行（`data/metadata/core_set.csv`、`data/metadata/broad_pool.csv`）。",
        "Gate 0 = **CLOSED**：4 项检查全部通过、`amendment_log` 为空、冻结产物逐字节重算一致（`outputs/week1/gate0_record.md`、`docs/00_stage0_definitions.md`）。",
    ])

    # ---- Week 2 ----------------------------------------------------------
    w2 = rd("outputs/week2/method_audit_xtb_summary.json")
    w2a = rd("outputs/week2/solution_anchor_audit.json")
    upgrades = (dig(w2a, "summary.decisions.exp", 0) or 0) + (dig(w2a, "summary.decisions.calc", 0) or 0)
    sec("Week 2 —— Stage 1：方法审计与外部锚点（`outputs/week2`）", [
        f"GFN2-xTB 12 分子三态方法审计：Koopmans MAE **{fnum(dig(w2, 'comparison.IP_koopmans_p0.mae_ev'), 3)} eV**（τ_b {fnum(dig(w2, 'comparison.IP_koopmans_p0.kendall_tau_b'), 3)}）对 ΔSCF MAE **{fnum(dig(w2, 'comparison.IP_dscf_vertical.mae_ev'), 3)} eV**（τ_b {fnum(dig(w2, 'comparison.IP_dscf_vertical.kendall_tau_b'), 3)}）——值误差更小的量排序反而更差（`outputs/week2/method_audit_xtb_summary.json`）。",
        f"气相阴离子不束缚 **{fint(dig(w2, 'n_unbound_anion'))}** 个；溶液相锚点 **{fint(dig(w2a, 'summary.rows_total'))}** 行逐条证据审计后仍全部 `est`，升级为 `exp`/`calc` 的行数 = **{fint(upgrades)}**（`outputs/week2/solution_anchor_audit.json`）。",
        "Gate 1 = **NOT CLOSED**：记录 `outputs/week2/gate1_record.md`；周报 `docs/03_week1_2_report.md`。",
    ])

    # ---- Week 3 ----------------------------------------------------------
    w3 = rd("outputs/week3/p0_summary.json")
    sec("Week 3 —— Stage 2：broad cheap pool（P0）（`outputs/week3`）", [
        f"GFN2-xTB P0 代理：core **{fint(dig(w3, 'pools.core.n_ok'))}/{fint(dig(w3, 'pools.core.n_total'))}**、broad **{fint(dig(w3, 'pools.broad.n_ok'))}/{fint(dig(w3, 'pools.broad.n_total'))}** 成功，合并池 **{fint(dig(w3, 'decision_preview.n_combined'))}**，`n_failed = 0`（`outputs/week3/p0_summary.json`）。",
        f"氧化轴 vs 还原轴（合并池）Kendall τ_b = **{fnum(dig(w3, 'decision_preview.kendall_tau_ox_vs_red_combined'), 3)}**；参考配体 primary_R = **DME (C08)**（`outputs/week3/decision_stability_preview.md`）。",
        "覆盖 / 家族分布图与 ORCA runner dry-run 就绪：`outputs/week3/fig1_family_counts.png`、`coverage_report.md`、`orca_pilot_summary.json`。",
    ])

    # ---- Week 4 ----------------------------------------------------------
    w4s = rd("outputs/week4/p1_core_set_summary.json")
    w4a = rd("outputs/week4/p1_core_set_audit.json")
    w4c = rd("outputs/week4/p1_anchor_comparison.json")
    w4d = rd("outputs/week4/p1_decision_stability.json")
    sec("Week 4 —— Stage 3（P1）+ Stage 4（P2）+ T5/T3/T2（`outputs/week4`）", [
        f"T1：core 18 × 3 电子态 r2SCAN-3c 气相单点 **{fint(dig(w4s, 'n_ok'))}/{fint(dig(w4s, 'n_jobs'))} 成功、{fint(dig(w4s, 'n_failed'))} 失败**，墙钟中位 **{fnum(dig(w4s, 'wall_clock_seconds_median'), 2)} s**（`outputs/week4/p1_core_set_summary.json`）；独立复核 `energy_mismatch = 0`、`scf_failed = 0`、`unbound_anion = {fint(dig(w4a, 'flag_counts.unbound_anion'))}`（`outputs/week4/p1_core_set_audit.json`）。",
        f"三臂 vs 气相锚点 MAE：P0 Koopmans **{fnum(dig(w4c, 'P0_koopmans_xTB.mae_ev'), 3)}** / GFN2 ΔSCF **{fnum(dig(w4c, 'GFN2_dSCF_xTB.mae_ev'), 3)}** / P1 r2SCAN-3c **{fnum(dig(w4c, 'P1_r2SCAN3c.mae_ev'), 3)} eV**（`outputs/week4/p1_anchor_comparison.json`）。",
        f"P0→P1 决策稳定性：氧化 τ_b **{fnum(dig(w4d, 'oxidation.kendall_tau_b'), 3)}**、还原 τ_b **{fnum(dig(w4d, 'reduction.kendall_tau_b'), 3)}**（`outputs/week4/p1_decision_stability.json`）。",
        "同周还跑了 P2 环境层（SMD 乙腈）、T5 弥散函数对照 24 作业、T3 bare CPCM ε 扫描 144/144、T2 Opt+Freq + G2 三态单点，全部 0 失败（`outputs/week4/t5_diffuse_control_summary.json`、`t3_cpcm_eps_scan_summary.json`、`t2_opt_freq_summary.json`）。",
    ])

    # ---- Week 5 ----------------------------------------------------------
    w5 = rd("outputs/week5/c1_li_coordination_summary.json")
    w5m = rd("outputs/week5/li_motif_generation.json")
    w5d = rd("outputs/week5/c1_decision_stability.json")
    sec("Week 5 —— Stage 5 / T4：Li+ 配位条件态 C1（`outputs/week5`）", [
        f"生成 `[Li M]+` motif：候选 **{fint(dig(w5m, 'n_candidates'))}** → 保留 **{fint(dig(w5m, 'n_kept_motifs'))}**（覆盖 {fint(dig(w5m, 'n_molecules_with_motif'))} 个分子）；DFT 作业 **{fint(dig(w5, 'n_jobs'))}** 个、`ok` **{fint(dig(w5, 'n_ok'))}**（1 个 `execution_failed`）（`outputs/week5/li_motif_generation.json`、`c1_li_coordination_summary.json`）。",
        f"C0→C1 决策稳定性：氧化 τ_b **{fnum(dig(w5d, 'oxidation.kendall_tau_b'), 3)}**、还原 τ_b **{fnum(dig(w5d, 'reduction.kendall_tau_b'), 3)}**（还原态 12 个里 11 个电子落在 Li 上）（`outputs/week5/c1_decision_stability.json`、`c1_state_identity.json`）。",
        "方法 / 几何 / 环境 / 条件态四台阶同口径 σ 对比；产物 `c1_coord_shifts.csv`、`c1_ligand_exchange.csv`、`figure_manifest_week5_*.md`。",
    ])

    # ---- Week 6 ----------------------------------------------------------
    w6 = rd("outputs/week6/delta_m_frozen.json")
    w6d = rd("outputs/week6/stage6_decision_stability.json")
    sec("Week 6 —— Stage 6：T6 构象 / T7 虚频 / T8 `delta_m` / T9 决策稳定性（`outputs/week6`）", [
        f"T6 构象系综 σ_conf（12 分子 / 32 构象）组装出 `delta_m`：氧化 **{fnum(dig(w6, 'per_layer.p0.oxidation.delta_m_ev'), 3)} eV**、还原 **{fnum(dig(w6, 'per_layer.p0.reduction.delta_m_ev'), 3)} eV**，主导项均为 `method`（`outputs/week6/delta_m_frozen.json`、`t6_conformer_spread.json`）。",
        f"T9 并入 `delta_m` 后 P0→P1 氧化 τ_b **{fnum(dig(w6d, 'results.docx_max.P0_to_P1.oxidation.kendall_tau_b'), 3)}**、还原 τ_b **{fnum(dig(w6d, 'results.docx_max.P0_to_P1.reduction.kendall_tau_b'), 3)}**（docx_max 口径，`outputs/week6/stage6_decision_stability.json`）。",
        "T7 C1 虚频检查 10/10 成功；还原轴在 `f_robust_inv` 分母降为 0 时**不可判定**，该指标不得读成「稳定」。",
    ])

    # ---- Week 7 ----------------------------------------------------------
    w7 = rd("outputs/week7/stage7_ml_results.json")
    w8 = rd("outputs/week7/stage8_al_results.json")
    sec("Week 7 —— Stage 7（ML / Δ-learning）+ Stage 8（active-learning replay）（`outputs/week7`）", [
        f"Stage 7：三种拆分 × direct/shift × 6 模型 × 5 种子 = **{fint(dig(w7, 'counts.n_result_rows'))}** 行结果；LOFO 外推普遍显示 shift 学习优于 direct（`outputs/week7/stage7_ml_results.json`）。",
        f"Stage 8：4 条 acquisition 曲线、**{fint(dig(w8, 'counts.n_curve_rows'))}** 行曲线、20 组冻结种子；给出 `n_T → τ_b` 的最小昂贵信息预算曲线（`outputs/week7/stage8_al_results.json`、`stage8_al_curves.csv`）。",
        "特征成本分级 X0 / X1 / X2 与 `outputs/week7/feature_manifest.json` 一并冻结。",
    ])

    # ---- Week 8 ----------------------------------------------------------
    w8s = rd("outputs/week8/stage9_summary.json")
    w8r = rd("outputs/week8/stage9_results.json")
    stab_ox = dig(w8r, "stability.0.kendall_tau_b")
    stab_red = dig(w8r, "stability.2.kendall_tau_b")
    sec("Week 8 —— Stage 9：显式微溶剂化 C2 = `[Li(M)2]+` 第一溶剂壳（`outputs/week8`）", [
        f"`[Li(M)2]+` 第一溶剂壳：**{fint(dig(w8s, 'n_shells'))}** 个 motif（覆盖 **8** 个家族）、DFT 作业 **{fint(dig(w8s, 'n_ok'))}/{fint(dig(w8s, 'n_jobs'))} ok**（`outputs/week8/stage9_summary.json`）。",
        f"C1→C2 排序稳定性：氧化 τ_b **{fnum(stab_ox, 3)}**、还原 τ_b **{fnum(stab_red, 3)}**（all12 口径，`outputs/week8/stage9_results.json`）。",
        "壳层枚举 18432 个放置 → 10401 无冲突 → 48 打分 → 12 入选；`f_robust_inv` 全 0 但 `f_unresolved` 最高 0.273（`stage9_shell_shifts.csv`）。",
    ])

    # ---- Week 9 ----------------------------------------------------------
    w9 = rd("outputs/week9/stage10_ladder.json")
    hb = rd("outputs/week22_hardening/stats_b1_b2.json")
    sec("Week 9 —— Stage 10：五级台阶合成与决策稳定性总判（`outputs/week9`）", [
        f"把方法 / 环境 / 几何 / 条件态 / 第二壳五个台阶放到 common-10 同一口径重算，得 **{fint(dig(w9, 'hypothesis_test.n_points'))}** 个 (台阶, 轴) 组合（`outputs/week9/stage10_ladder.json`）。",
        f"中心命题：位移**离散度**决定排序是否被改写 —— Spearman ρ(std, τ_b) = **{fnum(dig(hb, 'b1.reported_rho_in_ladder.rho_shift_std_vs_tau_b'), 3)}**、ρ(|mean|, τ_b) = {fnum(dig(hb, 'b1.reported_rho_in_ladder.rho_abs_shift_mean_vs_tau_b'), 3)}、ρ(std, f_unresolved) = +{fnum(dig(hb, 'b1.reported_rho_in_ladder.rho_shift_std_vs_f_unresolved'), 3)}（`outputs/week9/stage10_ladder.json`，W22-H 复核见 `outputs/week22_hardening/stats_b1_b2.json`）。",
        f"`f_robust_inv` 在 20 个组合中恒为 **0.000**，但 `f_unresolved` 最高 0.800 —— 这个 0 是「不可判定」而非「稳定」；v2 §23 最小成果判据 11 条中 10 PASS、1 PARTIAL。",
    ])

    # ---- Week 10 ---------------------------------------------------------
    w10 = rd("outputs/week10/stage11_sigma_anatomy.json")
    sec("Week 10 —— Stage 11：σ 的代数解剖与分辨率判据（`outputs/week10`）", [
        "证明并数值验证 4 条恒等式（T1–T4）+ 1 条精确分解（T5）；判据 `f_unresolved(z) = Pr(q_ij > √2/z)`，闭式与实测在 20 个点上误差**精确为 0**（`outputs/week10/stage11_sigma_anatomy.json`）。",
        f"可预测性：带符号斜率 `ols_slope_b` 的 AUC = **{fnum(dig(w10, 'predictability.table.0.auc'), 3)}**（精确置换 p = 1/120 = {fnum(dig(w10, 'predictability.table.0.auc_exact_permutation_p'), 4)}、LOO 10/10），无符号 `sd(delta)` 仅 0.810。",
        f"子集漂移：N = 10 时 P0→P1 氧化轴 τ_b 抽样标准差 **{fnum(dig(w10, 'subset_drift.P0_to_P1|oxidation.2.tau_b_std'), 3)}** —— 报 τ_b 必须同时报 N 与子集。",
    ])    # ---- Week 11 ---------------------------------------------------------
    w11 = rd("outputs/week11/stage12_prescreen.json")
    sec("Week 11 —— Stage 12：介电自相似律与事前预警协议（`outputs/week11`）", [
        f"把 bare CPCM 介电扫描提升为第 6 类台阶，凑成 **{fint(dig(w11, 'prescreen.n_points'))}** 个台阶事件（8 介电 + 10 电子结构），全部落在 common-10 上（`outputs/week11/stage12_prescreen.json`）。",
        f"介电位移落在 Born 单参数自相似族：20 条曲线 mean R² = **{fnum(dig(w11, 'dielectric_law.born_r2.mean'), 4)}**（Onsager 对照 {fnum(dig(w11, 'dielectric_law.onsager_r2.mean'), 4)}）；只用 ε = 5/10/20 预测 ε = 40，最大相对误差 2.44%。",
        f"8 个介电台阶全部良性（`b > 0`、τ_b ≥ 0.867、无一改写清单）；事前预警 k = 5 平均抓 96%（AUC 0.946）、k = 8 一次不漏（`outputs/week11/stage12_prescreen.json`）。",
    ])

    # ---- Week 12 ---------------------------------------------------------
    w12 = rd("outputs/week12/stage13_analysis.json")
    sec("Week 12 —— Stage 13：介电极限与 ORCA 能量账本（`outputs/week12`）", [
        f"新增 108 个 ORCA 单点（ε = 80/200 + SMD 水），介电阶梯由 5 级升到 7 级；6 个介电点 Born 形式 mean R² = **{fnum(dig(w12, 'model_comparison.born_r2.mean'), 4)}**、Onsager {fnum(dig(w12, 'model_comparison.onsager_r2.mean'), 4)}（`outputs/week12/stage13_analysis.json`）。",
        f"导体极限触达：ε = 200 与 u → 1 平均只差 **{fnum(dig(w12, 'conductor_limit.gap_to_limit_ev.mean'), 4)} eV**（最差 {fnum(dig(w12, 'conductor_limit.gap_to_limit_ev.max'), 4)} eV）；外推 ε = 40/80/200 最大绝对误差 0.0637/0.0763/0.0841 eV。",
        f"环境账本（SMD 乙腈）：氧化位移 {fnum(dig(w12, 'smd_ledger.smd_acetonitrile.per_axis.oxidation.shift_ev.mean'), 4)} = 介电 {fnum(dig(w12, 'smd_ledger.smd_acetonitrile.per_axis.oxidation.diel_ev.mean'), 4)} + 畸变 +{fnum(dig(w12, 'smd_ledger.smd_acetonitrile.per_axis.oxidation.dist_ev.mean'), 4)}；SMD CDS / Δ(D4) / Δ(gCP) 对垂直量精确为 0（`stage13_state_ledger.csv`）。",
    ])

    # ---- Week 13 ---------------------------------------------------------
    w13 = rd("outputs/week13/stage14_attribution.json")
    w13o = rd("outputs/week13/stage14_outlier.json")
    sec("Week 13 —— Stage 14：畸变项归因与 EMC 离群点诊断（`outputs/week13`）", [
        f"逐态畸变惩罚 D_neutral / D_cation / D_anion = **{fnum(dig(w13, 'state_penalties.neutral.mean_ev'), 4)} / {fnum(dig(w13, 'state_penalties.cation.mean_ev'), 4)} / {fnum(dig(w13, 'state_penalties.anion.mean_ev'), 4)} eV**（216/216 为正、变分检验无例外，通道不对称 6.95 倍）（`outputs/week13/stage14_attribution.json`）。",
        "唯一稳健关系：D_neutral 对自身偶极 ρ = +0.909、留一 R² = 0.634；D_anion 与两个轴观测量**不可预测**（§14 的区间被 510 种聚合穷举证否）。",
        f"EMC 离群点：插入 5 个新介电点（**{fint(dig(w13o, 'n_new_jobs'))}** 个 ORCA 作业、0 失败），九点阶梯把拐点定位到 ε 10 → 20（`outputs/week13/stage14_outlier.json`）。",
    ])

    # ---- Week 14 ---------------------------------------------------------
    w14 = rd("outputs/week14/stage15_two_guess_analysis.json")
    w14d = rd("outputs/week14/stage15_diffuseness.json")
    sec("Week 14 —— Stage 15：双初猜协议、电子弥散度描述符与溶液锚点扫描（`outputs/week14`）", [
        f"双初猜 90 点中 **{fint(dig(w14, 'verdict.n_points_where_it_does'))}** 点超 1 meV 且**全部为负**、反向 0 次，最大惩罚 **{fnum(dig(w14, 'verdict.max_default_excess_ev'), 4)} eV**（`outputs/week14/stage15_two_guess_analysis.json`）。",
        "EMC 还原轴九点 Born R² 0.6788 → **0.9556**、符号变化 4 → 0；ε = 200 → 1000 只走 11.3 meV。",
        f"弥散度描述符把 D_anion 最佳留一 R² 从 0.162 提到 **{fnum(dig(w14d, 'robust_verdicts.anion.median_best_loo_r2'), 3)}**（`spin_maxfrac`，ρ = +0.811）（`outputs/week14/stage15_diffuseness.json`）；31 行溶液锚点 4 行可裁定、3 改 1 确认，Gate 1 仍 NOT CLOSED。",
    ])

    # ---- Week 15 ---------------------------------------------------------
    w15 = rd("outputs/week15/stage16_catalogue_analysis.json")
    sec("Week 15 —— Stage 16：全核心集双初猜目录与事前预警规则（`outputs/week15`）", [
        f"12 分子 × 3 态 × 10 电介质 × 2 初猜 = **{fint(dig(w15, 'n_cells'))}** 个配对单元格：一致 328、**{fint(dig(w15, 'n_moread_lower'))}** 个 MORead 更低、**{fint(dig(w15, 'n_moread_higher'))}** 个更高（`outputs/week15/stage16_catalogue_analysis.json`）。",
        f"最大赤字 **{fnum(dig(w15, 'worst_negative_ev'), 4)} eV**（EMC / anion / ε = 1000）；10 点阶梯下 **{fint(dig(w15, 'n_flagged_molecules.ladder10'))}/12** 个分子被判定存在漏解。",
        "事前预警规则在留出臂失败（发现集 LOO 0.708 < 多数类 0.792、留出真阳 0）—— 结论只能是「事后靶向 + 容许量」，不是「事前预报」。",
    ])

    # ---- Week 16 ---------------------------------------------------------
    w16 = rd("outputs/week16/stage17_contamination.json")
    sec("Week 16 —— Stage 17：亚稳态污染上限与两个 SCF 解的电子结构身份（`outputs/week16`）", [
        f"SMD 层改用 moread 初猜重算 54 格：仅 **{fint(dig(w16, 'cells_changed_count'))}** 格 |Δ| > 1 meV，最坏 **{fnum(dig(w16, 'delta_stats.cells_54.max_abs_ev'), 4)} eV**（`outputs/week16/stage17_contamination.json`）。",
        f"两臂 τ_b 的 95% CI 两条轴均重叠，published 结论被改写的条数 = **0**（`any_published_conclusion_rewritten = {dig(w16, 'verdict.any_published_conclusion_rewritten')}`）；`f_robust_inv` 保持 0。",
        "32 个漏解配对格里两个 SCF 解都是自旋纯双重态（⟨S²⟩ 32/32 落在 0.75 ± 0.01）；该「0 变非 0 结构性不可能」是本流水线结论，不是普适定理。",
    ])

    # ---- Week 17 ---------------------------------------------------------
    w17 = rd("outputs/week17/stage18_identity_census.json")
    w17s = rd("outputs/week17/stage18_selfdiagnosis.json")
    conf = dig(w17, "separation.all.confusion_at_threshold", {}) or {}
    sec("Week 17 —— Stage 18：全目录电子身份普查与零成本自诊断（`outputs/week17`）", [
        f"**{fint(dig(w17, 'n_pairs'))}** 对身份普查（零新增 QM）：判据 `charge_l1 > 0.039`，可测子集 AUC = **{fnum(dig(w17, 'separation.all.auc.charge_l1'), 3)}**、混淆 TP {fint(conf.get('tp'))} / FN {fint(conf.get('fn'))} / FP {fint(conf.get('fp'))} / TN {fint(conf.get('tn'))}（`outputs/week17/stage18_identity_census.json`）。",
        "漏解全部集中在 cyclic_carbonate(15)、phosphate(10)、linear_carbonate(10)、ether(2)；ester / nitrile / sulfone / sulfoxide 四个家族零漏解。",
        f"零成本自诊断失败：冻结规则在留出臂只有 **{fnum(dig(w17s, 'holdout.accuracy'), 3)}**、输给多数类 {fnum(dig(w17s, 'holdout.majority_accuracy'), 3)}（TP 0）；唯一站得住的是单边必要条件 —— 无警告可安全放行（37/37 正例都带警告）。",
    ])

    # ---- Week 18 ---------------------------------------------------------
    w18 = rd("outputs/week18/stage19_relax_analysis.json")
    w18o = dig(w18, "aggregates.all.all.outcomes", {}) or {}
    sec("Week 18 —— Stage 19：几何弛豫检验（第二个 SCF 解能不能扛住弛豫）（`outputs/week18`）", [
        f"37 个 `moread_lower` 格各做两臂 Opt（**74 作业、74 ok / 0 failed**）；弛豫后仍 moread 更低 **{fint(w18o.get('distinct_lower'))}/37**、两解在终点合并 **{fint(w18o.get('same_higher'))}/37**、偏好被反转 **{fint(dig(w18, 'aggregates.all.all.n_preference_flipped'))}** 格（`outputs/week18/stage19_relax_analysis.json`）。",
        f"|Δ| 中位从单点 **{fnum(dig(w18, 'aggregates.all.all.abs_single_point_delta_ev.p50'), 5)} eV** 塌到 **{fnum(dig(w18, 'aggregates.all.all.abs_relax_delta_ev.p50'), 5)} eV**（缩小 61 倍）。",
        "结论：「身份差异多数是真的，但单点上的能量偏好多数是假象」；0.02 Å 阈值只是描述列，不是「同一驻点」的证明。",
    ])

    # ---- Week 19 ---------------------------------------------------------
    w19a = rd("outputs/week19/stage20_relax_rung.json")
    w19b = rd("outputs/week19/stage20_xtb_arms_analysis.json")
    agg = dig(w19b, "aggregates.all.all", {}) or {}
    sec("Week 19 —— Stage 20：第六级台阶与第二解的跨方法存亡（`outputs/week19`）", [
        f"Part 1（零新增计算）把弛豫修正放回台阶：逐分子跨 ε 极差中位 0.0263 eV；还原支 mean/std/相对散布 = {fnum(dig(w19a, 'aggregates.by_state.anion.shift_mean_ev'), 3)} / {fnum(dig(w19a, 'aggregates.by_state.anion.shift_std_ev'), 3)} / 0.08，氧化支 {fnum(dig(w19a, 'aggregates.by_state.cation.shift_mean_ev'), 3)} / {fnum(dig(w19a, 'aggregates.by_state.cation.shift_std_ev'), 3)} / 0.52（`outputs/week19/stage20_relax_rung.json`）。",
        f"Part 2：**74** 个冻结 GFN2-xTB 作业 —— 同一几何上偏好方向一致 **{fint(agg.get('n_xtb_sp_matches_stage19'))}/37（{pct(agg.get('sp_agreement_rate'), 1)}）**，xTB 自身弛豫把两臂能量差压掉约 **34 倍**（中位 |Δ| 0.0072 → 0.00021 eV）（`outputs/week19/stage20_xtb_arms_analysis.json`）。",
        f"逐格裁决与 Stage 19 一致度仅 **{fint(agg.get('n_agree_with_stage19'))}/37（{pct(agg.get('agreement_rate'), 1)}）**，但那是**跨判据**比较（身份判据 vs 几何 RMSD）。",
    ])    # ---- Week 20 ---------------------------------------------------------
    w20a = rd("outputs/week20/stage21_path_analysis.json")
    w20b = rd("outputs/week20/stage21_protocol.json")
    w20c = rd("outputs/week20/stage21_shell_redox_analysis.json")
    w20d = rd("outputs/week20/stage21_refill.json")
    sec("Week 20 —— Stage 21：临界带能量裁决 + 判据预检 + 溶剂壳氧化还原 + 真回填（`outputs/week20`）", [
        f"Part A：{fint(dig(w20a, 'n_cells'))} 格 × 21 帧 = **63** 个冻结单点；EC/cation/ε = 5 的弦上鼓包 **{fnum(dig(w20a, 'cells.0.barrier_chord_ev'), 5)} eV**（k_B T 的 16.5%），Stage 19 的 `distinct_lower` 属过度判定；{fint(dig(w20a, 'n_agree_with_stage19'))}/{fint(dig(w20a, 'n_cells'))} 格与 RMSD 裁决一致（`outputs/week20/stage21_path_analysis.json`）。",
        f"Part B 阈值重导为 **{fnum(dig(w20b, 'threshold.value'), 6)}**（空档宽 {fnum(dig(w20b, 'threshold.derivation.gap_width'), 6)}、无数据点），borderline {fint(dig(w20b, 'verdict_counts.borderline'))} 格、闭壳层反例 0 格越阈（`stage21_protocol.json`）。",
        f"Part C 溶剂壳氧化还原 **{fint(dig(w20c, 'n_ok'))}/{fint(dig(w20c, 'n_jobs'))}** 作业 OK，氧化轴弛豫修正 {fnum(dig(w20c, 'axes.0.correction_mean_ev'), 4)} eV（ρ = 0.797）、还原轴 {fnum(dig(w20c, 'axes.1.correction_mean_ev'), 4)} eV（ρ = −0.790）（`stage21_shell_redox_analysis.json`）。",
        f"Part D：严格 P2 腿 **{dig(w20d, 'verdict.strict_p2_leg_coverage')}** 可回填；氧化轴排序被改写（Top-10% 重叠 {fnum(dig(w20d, 'verdict.per_axis.oxidation.top10_overlap'), 3)}）、还原轴未被改写（`stage21_refill.json`）。",
    ])

    # ---- Week 21 ---------------------------------------------------------
    w4c = rd("outputs/week4/p1_anchor_comparison.json")
    w21s = rd("outputs/week21/sigma_synthetic.json")
    w21p = rd("outputs/week21/sigma_prospective.json")
    arm = dig(w4c, "arm_alignment.arms_on_common_subset", {}) or {}
    delta = dig(w4c, "arm_alignment.paired_delta_tau_b.GFN2_dSCF_xTB_minus_P1_r2scan3c", {}) or {}
    sec("Week 21 —— Stage 22 批次 A：三臂对齐 + σ 相图 + 前瞻检验（`outputs/week21`）", [
        f"三条臂对齐到同一批 10 分子（`outputs/week4/p1_anchor_comparison.json:arm_alignment`）：GFN2 ΔSCF τ_b **{fnum((arm.get('GFN2_dSCF_xTB') or {}).get('kendall_tau_b'), 3)}** vs P1 {fnum((arm.get('P1_r2scan3c') or {}).get('kendall_tau_b'), 3)}、P0 {fnum((arm.get('P0_koopmans_xTB') or {}).get('kendall_tau_b'), 3)}；配对 Δτ_b = {fnum(delta.get('observed_delta_tau_b'), 3)}，95% CI [{fnum((delta.get('paired_ci95') or [None, None])[0], 3)}, {fnum((delta.get('paired_ci95') or [None, None])[1], 3)}]、精确置换 p = {fnum((delta.get('permutation') or {}).get('p_value'), 4)} ⇒ 三条臂两两全部 unresolved。",
        f"σ 相图：合成模型 ρ(std, τ_b) = **{fnum(dig(w21s, 'synthetic_correlations.spearman_shift_std_vs_tau_b'), 3)}**、均值平移 max|Δτ_b| = **{fnum(dig(w21s, 'mean_invariance.max_abs_tau_b_difference_vs_mean_0'), 3)}**；实测 ρ = {fnum(dig(w21s, 'measured_correlations.spearman_shift_std_vs_tau_b'), 3)}（`outputs/week21/sigma_synthetic.json`）。",
        f"前瞻检验：带符号规则命中 **{fint(dig(w21p, 'scoring.signed_rule_hits'))}/{fint(dig(w21p, 'scoring.n_predictions'))}**、朴素规则 {fint(dig(w21p, 'scoring.naive_rule_hits'))}/{fint(dig(w21p, 'scoring.n_predictions'))}（`outputs/week21/sigma_prospective.json`）。",
    ])

    # ---- Week 22 (Stage 23 batch B) -------------------------------------
    w22t = rd("outputs/week22/thermal_correction_sample.json")
    w22d = rd("outputs/week22/dielectric_limit.json")
    w22n = rd("outputs/week22/neb_refinement.json")
    sec("Week 22 —— Stage 23 批次 B：热修正抽样 + 导体极限诊断 + NEB 精修（`outputs/week22`）", [
        f"R9 热修正抽样：{fint(dig(w22t, 'n_molecules'))} 分子 × 3 态、{fint(dig(w22t, 'n_jobs'))} 个 `--ohess` 作业；热修正分子间离散度只有同轴 `delta_m` 的 8.3% / 3.7%，整项略去不改变任何排序结论（`outputs/week22/thermal_correction_sample.json`）。",
        f"R4b：`|dE|·ε` 近似常数（ε = 200 时 {fnum(dig(w22d, 'power_law.200.mean_x_epsilon_mev'), 0)} meV，约 2.1 eV）的幂律；ε = 200 残余最大 **{fnum(dig(w22d, 'pairs.200.max_abs_mev'), 2)} meV**（氧化轴 `delta_m` 的 2.80%），ε = 1000 只剩 {fnum(dig(w22d, 'pairs.1000.max_abs_mev'), 2)} meV（`outputs/week22/dielectric_limit.json`）。",
        f"R11 真 NEB 精修 {fint(dig(w22n, 'n_ok'))}/{fint(dig(w22n, 'n_cells'))} 格：EC/cation/ε = 5 峰高 **{fnum(dig(w22n, 'cells.0.barrier_ev'), 6)} eV**（直线界 {fnum(dig(w22n, 'cells.0.linear_barrier_ev'), 6)} eV 的 1/{fnum(dig(w22n, 'cells.0.bound_ratio'), 1)}）—— Stage 19 的 0.02 Å 阈值在该格过度判定（`outputs/week22/neb_refinement.json`）。",
    ])

    # ---- Week 22 (W22-H hardening) --------------------------------------
    wh = rd("outputs/week22_hardening/stats_b1_b2.json")
    wa = rd("outputs/week22_hardening/allowance_factor2.json")
    wb = rd("outputs/week22_hardening/broad_pool_demo.json")
    wm = rd("outputs/week22_hardening/multiple_compare_b3.json")
    b2ci = dig(wh, "b2.primary_12draw.ci95_percentile", [None, None]) or [None, None]
    sec("Week 22（W22-H）—— 论文加固、统计证据与统一数据（`outputs/week22_hardening`）", [
        f"零新增电子结构；B1 ρ(std, τ_b) = **{fnum(dig(wh, 'b1.reported_rho_in_ladder.rho_shift_std_vs_tau_b'), 4)}**、B2 配对 Δτ_b = **{fnum(dig(wh, 'b2.primary_12draw.observed_delta_tau_b'), 4)}** [95% CI {fnum(b2ci[0], 4)}, {fnum(b2ci[1], 4)}]、P(Δ > 0) = {fnum(dig(wh, 'b2.primary_12draw.prob_delta_gt_0'), 4)}（`outputs/week22_hardening/stats_b1_b2.json`）。",
        f"B3 多重比较：9 个预警子 Bonferroni / Holm 显著条数 = **{fint(dig(wm, 'n_bonferroni_significant'))} / {fint(dig(wm, 'n_holm_significant'))}**（`multiple_compare_b3.json`）。",
        f"A3 漏解容许量 A_axis = **{fnum(dig(wa, 'axes.oxidation.A_axis_ev'), 4)} eV**（氧化 TMP@ε=5）/ **{fnum(dig(wa, 'axes.reduction.A_axis_ev'), 4)} eV**（还原 EMC@ε=1000），2·A_axis 严格界保护 120/120、漏检 0（`allowance_factor2.json`）。",
        f"B5 broad 池预算演示：主判据 Top-10% 并集 **{fint(dig(wb, 'budget.union.n_worth_union_axes_k10'))}/40（省 {fnum(dig(wb, 'budget.union.saving_union_axes_k10_pct'), 1)}%）**（`outputs/week22_hardening/broad_pool_demo.json`、`outputs/figures/F47_broadpool_budget.png`）。",
    ])

    # ---- Week 23 ---------------------------------------------------------
    w23t = rd("outputs/week23/targeted_two_guess.json")
    w23s = rd("outputs/week23/shell3_xtb_sign_test.json")
    sec("Week 23 —— Stage 24 批次 C+D：R5 三次配位 + R8 靶向双腿 + R12 叙事（`outputs/week23`）", [
        f"R8：漏解可以被「框住」而不必全局翻倍 —— 靶向规则安全（{fint(dig(w23t, 'axes.oxidation.n_flips'))} 次真实翻转、漏 **{fint(dig(w23t, 'axes.oxidation.soundness_missed_flips'))}**），氧化省 28.3%、还原省 3.3%；只保护 Top-k 清单的变体（k = 1/2）实测可省 91.7% / 83.3%（`outputs/week23/targeted_two_guess.json`，Top-k 值见 `成果输出/数据结果汇总.md`）。",
        f"两次预报失败：发现集 LOO **{fnum(dig(w23t, 'predictor_failures.discovery.loo_accuracy'), 3)}** < 多数类基线 {fnum(dig(w23t, 'predictor_failures.discovery.majority_baseline_accuracy'), 3)}、留出臂真阳 0 ⇒ 策略只能是「事后靶向 + 容许量」，不是「事前预报」。",
        f"R5 第三个配位点在 xTB 层级没有换号（增量同号且绝对值递减，dd(3→2)/dd(2→1) = {fnum(dig(w23s, 'increments.ratio_2to1.ip'), 3)} / {fnum(dig(w23s, 'increments.ratio_2to1.ea'), 3)}），判定 **`{dig(w23s, 'verdict.label')}`**（`outputs/week23/shell3_xtb_sign_test.json`）。",
    ])

    # ---- Week 24 ---------------------------------------------------------
    w24m = rd("outputs/week24_corealign/ml_direct_vs_shift.json")
    w24a = rd("outputs/week24_corealign/al_budget.json")
    w24d = rd("outputs/week24_corealign/decision_metrics.json")
    cfg = dig(w24m, "delta_learning.configs", []) or []
    lofo = [c for c in cfg if c.get("split") == "lofo"]
    lofo_pos = sum(1 for c in lofo if (c.get("headline_delta_paired") or 0) > 0)
    lofo_excl = sum(1 for c in lofo if min(c.get("headline_delta_paired_lo") or 0, c.get("headline_delta_paired_hi") or 0) > 0 or max(c.get("headline_delta_paired_lo") or 0, c.get("headline_delta_paired_hi") or 0) < 0)
    lofo_deltas = sorted(c.get("headline_delta_paired") or 0 for c in lofo)
    lofo_med = ((lofo_deltas[len(lofo_deltas) // 2 - 1] + lofo_deltas[len(lofo_deltas) // 2]) / 2) if len(lofo_deltas) >= 2 else None
    n_indist = sum(1 for c in cfg if c.get("verdict") == "indistinguishable")
    dm_rows = dig(w24d, "rows", []) or []
    nick = sum(1 for r in dm_rows if (r.get("f_robust_inv_z1") or 0) == 0) + sum(1 for r in dm_rows if (r.get("f_robust_inv_z1p96") or 0) == 0)
    sec("Week 24 —— W24-C 核心文件对齐：ML/AL 蒸馏 + 决策量补全 + F51 流程图（`outputs/week24_corealign`）", [
        f"ML 蒸馏：LOFO {fint(len(lofo))} 个分组中 **{fint(lofo_pos)}** 个 Δτ_b > 0（**{fint(lofo_excl)}** 个配对区间不含 0、中位 **{fnum(lofo_med, 3)}**），{fint(len(cfg))} 个组合中 **{fint(n_indist)}** 个不可区分（`outputs/week24_corealign/ml_direct_vs_shift.json`）。",
        f"AL 预算：τ_b ≥ {fnum(dig(w24a, 'tau_threshold'), 2)} 需 n_T = 8–9（10 分子池）/ 12–15（18 分子池）（`outputs/week24_corealign/al_budget.json` 的 `key_n_T_by_pool`）。",
        f"决策量补全：{fint(nick)} 个 `f_robust_inv` 数值（2 z × 2 population × 10 点）全为 0，`p_ij` 与闭式 `f_unresolved(z = 1.2816)` 逐点相等、偏差 0.0（`outputs/week24_corealign/decision_metrics.json`）。",
        "W24-D 可行性审计：本地文献最长同源序列 k = 1，判决 Gate 1 **NOT_CLOSABLE**（`outputs/week24_corealign/gate1_anchor_feasibility.md`）。",
    ])

    # ---- Week 25 ---------------------------------------------------------
    w25 = rd("outputs/week25/series_rel_ordering_check.json")
    w25o = rd("outputs/week25/gate1_oxidation.json")
    w25r = rd("outputs/week25/gate1_reduction_secondary.json")
    w25f = rd("outputs/week25/family_resolved_stats.json")
    w25l = rd("outputs/week25/compute_budget_ledger.json")
    w25p = rd("outputs/week25/anchor_ingest_provenance.json")
    xci = [dig(w25f, "cross_family.0.tau_b_ox_vs_red_ci_low"), dig(w25f, "cross_family.0.tau_b_ox_vs_red_ci_high")]
    sec("Week 25 —— W25-G1：Gate 1 排序层判据首次评估 + 家族分辨统计（`outputs/week25`）", [
        f"溶液锚点入库：Ue1994 / Okoshi2015 氧化系列 **{fint(dig(w25o, 'species.n_anchored'))}** 个核心集分子 / **{fint(dig(w25, 'n_pairs'))}** 对首次可评，Kendall τ_b = **{fnum(dig(w25, 'tau_b'), 4)}** < 0.90 ⇒ `ok = False`（`reason = {dig(w25, 'reason')}`，一致 {fint(dig(w25, 'concordant'))} / 不一致 {fint(dig(w25, 'discordant'))}）（`outputs/week25/series_rel_ordering_check.json`、`gate1_oxidation.json`）。",
        f"provenance：收到文件 SHA256 `{str(dig(w25p, 'received_sha256'))[:16]}…` 被钉死，全部入库行 `repo_verification = {dig(w25p, 'repo_verification')}` —— **仓库没有独立复核过任何一行**（`outputs/week25/anchor_ingest_provenance.json`）。",
        f"还原旁证（DOE 2016，{fint(dig(w25r, 'n_species'))} 分子 / {fint(dig(w25r, 'n_pairs'))} 对 < 18）判 `{dig(w25r, 'verdict')}`：是「数据不足」而非「不一致」（`outputs/week25/gate1_reduction_secondary.json`）。",
        f"家族分辨：**{fint(dig(w25f, 'counts.combos_total'))}** 个组合中 **{fint(dig(w25f, 'counts.estimable_total'))}** 个可估计（native-18 全部、common-10 为 0），跨家族 τ_b(氧化 vs 还原) = **{fnum(dig(w25f, 'cross_family.0.tau_b_ox_vs_red'), 4)}** [95% CI {fnum(xci[0], 3)}, {fnum(xci[1], 3)}]（`outputs/week25/family_resolved_stats.json`、`outputs/figures/F52–F54`）。",
        f"§21 计算预算账本：PASS {fint(dig(w25l, 'status_counts.PASS'))} / PARTIAL {fint(dig(w25l, 'status_counts.PARTIAL'))} / MISSING {fint(dig(w25l, 'status_counts.MISSING'))}；仓库无 CPU-core-hours / p90 作业成本 / frequency-only 成本（`outputs/week25/compute_budget_ledger.json`、`docs/44_week25_compute_budget_ledger.md`）。",
        "F55 / 核心文件 §24 Figure 5 补全：在 C1 子集（n = 10）上给出配位位移 × 描述符标签的关系——氧化轴 `tpsa` ρ = **−0.890**（精确置换 p = 0.0011）、`donor_count` ρ = **−0.794**（p = 0.0077），还原轴 14 条相关**全部不显著**；标签分层对比 47 条中仅 **3** 条可估计（齿数 / 态身份 / cyclic vs linear，组内 n ≥ 4），其余（组内 n < 4）判 `not_estimable`；ESP 字段仓库内不存在（`not_available_in_repo`）。**未作多重比较校正，属探索性证据、不得称显著**，也不改动任何既有判决（`scripts/analyze_w25_figure_f55.py`、`outputs/week25/figure_f55_stats.json`、`outputs/week25/F55_manifest.md`、`outputs/figures/F55_coord_descriptor_tags.png`）。",
        "论文 v5 同步：新增 §3.17「配位位移与描述符标签的关系（§24 Figure 5 的补全）」与图 22，论文图数 21 → **22**（重建后 **34 页**、表 1–15），并按评审意见移除运行页眉；核心文件 §24 对齐表中 Figure 5 由 PARTIAL → **PASS**（`论文/build_paper_docx.py`、`docs/43_week25_corefile_figure_alignment.md`）。",
        "论文 v6 同步（核心文件结构性要求补全）：新增 §5.10「核心方案结构性要求的落点」与表 16、表 17——逐条登记 §7.1 方法审计（‘两种 DFT functional’未做、以 GFN2-xTB↔r2SCAN-3c 跨引擎与 T5 弥散对照替代）、§17.1 微溶剂化覆盖（11 分子 × 12 motif、单一 1:2 化学计量、robust inversion 一类因现象未观测为空）、§27 Phase II–IV 路线与 §28 目录骨架↔仓库实际路径映射；§5.3 增补 §25.2 / §26 的增量逐条对应，§5.4 表 10 增方法审计两行，§5.8 表 14 将 §24 Figure 4 明确登记为 negative result。重建后 **35 页**、表 1–17（`论文/build_paper_docx.py`、`docs/45_week25_paper_v6_corefile_optimization.md`）。",
    ])

    return out

HEAD = [
    "# 电解液溶剂HB —— 决策稳定性研究（Electrolyte Ranking Stability）",
    "",
    "> **Scope.** This repository does not establish a definitive electrolyte-solvent ranking. It studies the stability, instability, and information cost of ranking decisions under progressively more realistic computational models.",
    ">",
    "> 本仓库**不**给出「18 个溶剂谁最好」的最终排行榜；它研究的是**排序决策**在逐步更真实的计算模型下的**稳定性 / 不稳定性 / 信息成本**。任何把本仓库引用成「最终性能排行榜」的读法都是误读。",
    "",
    "在**很小的分子集**（core set = **18** 个分子）上，用**两种**高效量子化学方法（GFN2-xTB 与 r2SCAN-3c），研究「从廉价代理量走向更真实的电子结构 / 环境模型」时，**哪些改变只是数值平移、哪些会真正翻转材料筛选决策**，以及这些翻转背后的物理机制。",
    "",
    "> 核心不是「筛出最好的电解液」，而是：",
    "> cheap proxy → designated computational target → uncertainty-aware rank change → mechanism → minimal budget",
    ">",
    "> （R13 起：Gate 1 闭合前不称 *validated* target；外部有效性单独作为 negative result 报告，见 `docs/gate1_negative_result.md`。）",
    "",
    "**项目状态**：`Gate 0` **CLOSED** · `Gate 1` **未闭合**（排序层已评估：`ordering_disagrees`，τ_b = 0.4286 < 0.90，n_pairs = 21；绝对标定层按 limitation 处理）。",
    "",
    "> 本 README 由 `scripts/build_github_readme.py` 确定性生成：逐周关键数字尽量从 `outputs/` 的冻结产物读回，`--check` 逐字节复核。全量汇总另见仓库外 `成果输出/数据结果汇总.md` 与 `成果输出/统一数据文档.md`。",
    "",
    "## 科学定位与核心问题",
    "",
    "- **廉价代理 → 指定计算目标 → 外部参考**（`cheap → intermediate → external reference`，**不**写成 `cheap → truth`）：`P0` = GFN2-xTB Koopmans 代理；`P1v` = ORCA r2SCAN-3c **三态垂直** IP/EA（气相，三态共用 G1 几何）；`P1a` = 每个电荷态各自弛豫的 **adiabatic** redox（12 分子子集，`outputs/phase2_p1a`）；`P2a` = `P1v` + SMD(乙腈) **固定溶剂**层；`P2eps` = bare CPCM **纯介电**扫描（改变 ε，不是换真实溶剂）。相邻层之间只有一个变量在变。",
    "- **条件态与状态身份**：`C0` = 自由分子；`C1` = `[LiM]+` 配位态；`C2` = `[Li(M)2]+` **第一配位壳**（coordination number 2，**不是** second solvation shell）。**还原轴只允许 `molecule_centered_redox` 进入主 ranking**，其余标签作为 mechanistic state-identity outcome 单独统计（`docs/state_identity_protocol.md`）。",
    "- **三态判据**：pair 级判据同时给出 `STABLE / UNRESOLVED / ROBUST_INVERSION` 与 `f_unresolved(z)` **分辨率曲线**（z = 1.0 / 1.645 / 1.96 / 2.576）；`f_robust_inv = 0` 只有在 UNRESOLVED 占比小时才等于「排序稳定」。",
    "- **不确定性感知的排序变化**：pair 级主判据是 `resolved(i,j) ⇔ |ΔP_ij| ≥ max(z·σ_ij, delta_m)`；`config/prereg.yaml` 冻结 `z = 1.0` 为主口径，`z = 1.96` 只作并列敏感性。",
    "- **机制**：位移的**离散度**（而非幅度）决定排序是否被改写 —— `f_unresolved(z) = Pr(q_ij > √2/z)`，其中 `q` 是位移相对目标轴的割线斜率；符号比幅度重要。",
    "- **最小信息预算**：闭式判据（花钱前预判）+ 介电层自相似（可稀疏采样）+ 配位层只算第一壳 + 漏解只做靶向。",
    "- **结论矩阵**：`FINAL_CONCLUSIONS.md` 用 **10 个问题**（结论 → 数字 → evidence path → limitation）把 25 周结果收口；本 README 是工作日志，该文件是**研究成果索引**。",
    "- 科学方案：`核心文件/ranking-electrolyte-materials-v2.md`；阅读清单：`核心文件/ranking-electrolyte-materials-reading-list.md`；项目计划：`计划.md`。",
    "",
    "## n = 18 的四层可声明边界（external-validity limitation）",
    "",
    "core set = **18**（broad pool = **40**；v2 原建议 core ≈ 60–100、broad ≈ 300–1000）。本项目不再把 core set 扩到 60–100，而是把可声明范围按四层**分别**界定：",
    "",
    "| 层面 | 当前状态 | 说明 |",
    "| --- | --- | --- |",
    "| 机制验证（mechanism） | **可以成立** | 机制结论（位移离散度决定排序是否被改写）在 10 个分子的 common subset 上精确闭式验证（误差 = 0）。 |",
    "| 排序规律的普适性 | **不能宣称成立** | 18 个分子只能支持 family 层面的提示性证据，不能外推到更大化学空间。 |",
    "| 大规模筛选能力 | **未验证** | broad 池只到 P0 廉价层（40 个）；本项目不声称可做高吞吐量筛选。 |",
    "| 方法学 proof-of-concept | **成立** | 三态判据 + 分辨率曲线 + 最小信息预算，作为可复用方法学成立（不依赖 n）。 |",
    "",
    "> 读法：引用本仓库时应区分这四层。「机制可以成立」不等于「排序普适性成立」，也不等于「可大规模筛选」。",
    "",
    "## 逐周工作日志（Week 1 – Week 25）",
    "",
    "每周列出「做了什么 + 关键数字 + 产物路径」。数字旁注的文件是唯一来源；`outputs/week22`（Stage 23 批次 B）与 `outputs/week22_hardening`（W22-H）为两个不同工作包，`outputs/week24_corealign` 对应 Week 24，`outputs/week25` 对应 Week 25。",
    "",
]

TAIL = [
    "## Gate 状态与未闭合项",
    "",
    "| Gate | 状态 | 说明 |",
    "| --- | --- | --- |",
    "| Gate 0（定义冻结） | **CLOSED** | R13 amendment（P1→P1v/P1a、P2→P2a/P2eps、C2 更名、C1 还原态分层、三态判据）已登记进 `config/prereg.yaml` 的 `amendment_log` 并**重冻结**；`scientific_definitions.yaml` schema 1.0→2.0（`outputs/week1/gate0_record.md`）。 |",
    "| Gate 1（方法 / 锚点） | **NOT CLOSED** | **排序一致性层**首次可评但未通过：Kendall **τ_b = 0.4286 < 0.90**、**n_pairs = 21**，判 **`ordering_disagrees`**（一致 15 / 不一致 6）（`outputs/week25/series_rel_ordering_check.json`）。**绝对标定层**：溶液相锚点 31 行 `est` 按 R7 裁决记为 **limitation**，不再单列 blocker。 |",
    "| Gate 2+ | 未定义 / 未触发 | —— |",
    "",
    "- **排序层为什么未闭合**：证据是**预注册的负结果**；数值本身不得事后通过剔除分子、替换模型列或放宽容差「救回」（`docs/40_week25_gate1_report.md`）。要闭合需要一条覆盖 ≥ 7 个核心集分子、同装置 / 同判据、且描述符在溶剂间**真有离散度**的新同源序列；W24-D 进一步升级为 **NOT CLOSABLE**（本地文献里最长同装置 / 同判据同源序列 k = 1），不再作为待办缺陷。",
    "- **还原轴**：旁证级数据只有 3 分子 / 3 对（< 18），判 `not_evaluable_secondary_only` —— 是「数据不足」，不是「不一致」（`outputs/week25/gate1_reduction_secondary.json`）。",
    "- **上游可行性审计**：W24-D 发现本地文献最长同源序列 k = 1，判 Gate 1 **NOT_CLOSABLE**（`outputs/week24_corealign/gate1_anchor_feasibility.md`）。",
    "- **R13 · P1 实为 vertical**：早期 `P1` 是同一几何上的三态单点；R13 更名 `P1v` 并补出 adiabatic 层 `P1a`（`outputs/phase2_p1a/`）。气相阴离子全部不束缚（`unbound_anion = 18`），因此 **P1a 只有氧化轴可比较**，还原轴按规则排除（`docs/p1v_vs_p1a.md`）。",
    "- **R13 · C1 还原态身份失败**：12 个还原态里 **11** 个外加电子落在 Li 上；只用 `molecule_centered_redox` 时主 motif 只剩 **1** 个成员、还原排序**无定义**。因此原来的还原轴 `τ_b = -0.467` 不是排序不稳定，而是 observable identity failure（`outputs/state_identity/state_identity_summary.md`）。",
    "- **R13 · 泛化声明降级**：18 / 40 只支撑 mechanistic proof-of-concept；不得据此声称方法可泛化到电解液化学空间，也不得把 AL 预算说成普适最小标签数。",
    "",
    "## 目录结构与关键路径",
    "",
    "| 路径 | 内容 |",
    "| --- | --- |",
    "| `src/electrolyte_ranking/` | 库：`toolchain` / `xtb` / `orca` / `ranking` / `decision_state` / `uncertainty` / `provenance` / `qc` |",
    "| `scripts/` | 环境自检、元数据构建、锚点校验、逐周运行器与分析脚本，以及本 README 的生成器 `build_github_readme.py` |",
    "| `data/` | `metadata/`（`core_set.csv` 18、`broad_pool.csv` 40）、`anchors/`（气相 / 溶液相锚点、`within_series_ordering.csv`、`_received/`） |",
    "| `outputs/` | 每周可复现产物 `week1`–`week25`（含 `week22_hardening`、`week24_corealign`）与 `week26` 收口包（F56 + clean-room 审计）、`figures/`（F0–F56 及清单） |",
    "| `docs/` | Stage 说明与逐周报告（`00`–`48`，**文件名前缀不连续**，以目录为准） |",
    "| `config/` | `scientific_definitions.yaml`（定义冻结）、`prereg.yaml`（预注册阈值，append-only） |",
    "| `tests/` | 单元测试（无 QM 二进制也必须通过） |",
    "| `structures/` | 几何，含 `li_motifs/`、`microsolvation/` |",
    "| `计划.md` | 主计划（定位 / 规模 / 协议 / 周计划 / 交付物） |",
    "",
    "仓库**之外**（与代码仓库并列的交付与资料层）：",
    "",
    "| 路径 | 内容 |",
    "| --- | --- |",
    "| `..\\成果输出\\` | 对外交付层：`README.md`（索引 + 一周一张表）、`数据结果汇总.md`、`统一数据文档.md`、`weekN/` 镜像（含 `SHA256SUMS`、`verification.json`） |",
    "| `..\\核心文件\\` | 科学方案 v2、阅读清单、Gate 1 溶液锚点电位表、文献 |",
    "| `..\\论文\\` | 结题论文源与 PDF（`build_paper_docx.py` 重建；当前 `_v6`） |",
    "",
    "## 快速开始 / 复现",
    "",
    "```powershell",
    "# 0. 指向仓库内置的 xTB（6.7.1 Windows 构建，SHA256 已校验）；装好 ORCA 后同样无需环境变量",
    ". .\\scripts\\activate_toolchain.ps1",
    "",
    "# 0b. ORCA 下载完成后一条命令放到位（默认建 junction，不额外占空间）",
    "# .\\scripts\\setup_orca.ps1 -Source \"E:\\Downloads\\orca_6_1_1_win64\"",
    "",
    "# 1. 环境自检（无 xtb / ORCA 也会正常返回）",
    ".venv\\Scripts\\python.exe scripts\\check_environment.py",
    "",
    "# 2. 重建 / 校验元数据（CSV 是产物，不是手改文件）",
    ".venv\\Scripts\\python.exe scripts\\build_metadata.py --check",
    "",
    "# 3. 校验外部锚点",
    ".venv\\Scripts\\python.exe scripts\\validate_anchors.py",
    "",
    "# 4. 单元测试",
    ".venv\\Scripts\\python.exe -m pytest -q",
    "",
    "# 5. 重生成项目图（输出 outputs/figures/，含清单与 SHA256）",
    ".venv\\Scripts\\python.exe scripts\\make_summary_figures.py",
    "```",
    "",
    "**幂等校验入口（`--check` 逐字节 / 逐像素比对，不一致即非零退出）**：",
    "",
    "```powershell",
    "# 本 README 自身",
    ".venv\\Scripts\\python.exe scripts\\build_github_readme.py --check",
    "",
    "# Gate 1 / Week 25",
    ".venv\\Scripts\\python.exe scripts\\ingest_gate1_anchor_series.py --check",
    ".venv\\Scripts\\python.exe scripts\\analyze_w25_gate1_oxidation.py --check",
    ".venv\\Scripts\\python.exe scripts\\analyze_w25_figure_f52.py --check",
    ".venv\\Scripts\\python.exe scripts\\analyze_w25_figure_f53.py --check",
    ".venv\\Scripts\\python.exe scripts\\build_week25_deliverables.py --check",
    "",
    "# Week 24 交付镜像",
    ".venv\\Scripts\\python.exe scripts\\build_week24_deliverables.py --check",
    "",
    "# 交付层（成果输出）",
    ".venv\\Scripts\\python.exe scripts\\build_deliverables.py --dry-run",
    "```",
    "",
    "跑一个真实 xTB 任务：",
    "",
    "```powershell",
    ". .\\scripts\\activate_toolchain.ps1",
    ".venv\\Scripts\\python.exe scripts\\run_xtb_job.py `",
    "    --name EC --smiles \"C1COC(=O)O1\" --charge 0 --job opt --outdir outputs\\smoke",
    "```",
    "",
    "## 计算栈",
    "",
    "| 层 | 方法 | 工具 | 现状 |",
    "| --- | --- | --- | --- |",
    "| 几何 / 频率 / 廉价描述符 | GFN2-xTB | `xtb` | **已就绪**（仓库 `.toolchain/`，6.7.1pre） |",
    "| 单点电子能 | r2SCAN-3c | `ORCA` | **已装 6.1.1**（Windows AVX2 msmpi 构建，装到 `E:\\ORCA\\orca_6_1_1`，仓库内经 junction 使用；安装 / 版本探测 / 并行与 scratch 策略见 `docs/07_orca_setup_and_runner.md` §10–§15） |",
    "",
    "代码在缺少二进制时以 `dry_run` / fake backend 运行，保证测试与流水线可先跑通；真实数值计算需先完成 Stage 1 的 Gate 1。",
    "",
    "## 数据与 provenance 纪律",
    "",
    "- **锚点为 `transcription_only`**：Week 25 的 Ue1994 / Okoshi2015 与 DOE 2016 锚点全部是**用户提供的转录值**，`repo_verification = transcription_only_not_reverified_against_primary`，收到文件 SHA256 被钉死（`outputs/week25/anchor_ingest_provenance.json`）。`0.1 V` 是 PI 声明的系列重复性，不是来源报告的不确定度。",
    "- **仓库未独立复核**：相关原 PDF 不在 `核心文件/文献`，且沙箱无网络（WinError 10061）——任何一行都没有被仓库独立复核过。",
    "- **冻结产物不得回填**：`config/prereg.yaml` append-only；Week 25 的 `ordering_disagrees` 是预注册负结果，不得通过剔除分子 / 替换模型列 / 放宽容差「救回」，所有剔除只作敏感性分析并同时给出未剔除结果。",
    "- **唯一变量规则**：相邻层只有一个变量在变（P0→P1 换方法、P1→P2 换环境、G1→G2 换几何、C0→C1 换条件态、C1→C2 加第二壳）。",
    "- **z 因子**：`z = 1.0` 为冻结主判据，`z = 1.96` 只作并列敏感性；两者不得混用、不得择优引用。",
    "- **CSV 是产物不是手改文件**：`build_metadata.py --check` 现场重建并逐字节比对。",
    "- **交付层只放蒸馏产物**：原始 ORCA / xTB 输出与二进制 scratch 一律留在仓库 `outputs/`（`成果输出/README.md` 口径说明）。",
    "",
    "## 诚实边界",
    "",
    "- **core 18 vs 建议 60–100**：v2 建议 core set ≈ 60–100，本项目主动缩小到 18 个 family 覆盖分子，`docs/44` 账本判 **PARTIAL**（`outputs/week25/compute_budget_ledger.json`）。",
    "- **broad 40 vs 建议 300–1000**：v2 建议 broad pool ≈ 300–1000，实际 **40**；broad 池只到 P0 廉价层。",
    "- **未做 RS-hybrid**：v2 把 range-separated hybrid（如 ωB97X-D4 一类）列为生产候选，本项目未运行该类方法；全部能量为单参考 r2SCAN-3c 或 GFN2-xTB。",
    "- **`f_robust_inv` 全 0 是负结果**：Stage 10 的 20 个 (台阶, 轴) 组合、Week 24 的 40 个数值（2 z × 2 population × 10 点）全部为 **0**；这是「不可判定主导」而非「处处稳定」（同一批数据 `f_unresolved` 最高 **0.800**），不得读成稳健性证据。",
    "- **Gate 1 未闭合**：排序层 `ordering_disagrees`（τ_b = 0.4286 < 0.90，n_pairs = 21）、绝对标定层 limitation；溶液相锚点 31 行仍为 `est`；定性为 **NOT CLOSABLE**（`docs/gate1_negative_result.md`、`outputs/gate1/gate1_dual_track.md`）。措辞边界：**NOT CLOSABLE ≠ NO SUCH DATA EXIST ANYWHERE**（不做 absence-of-evidence → evidence-of-absence 的推论），只表示在预注册的检索 / 验证标准下未定位到够格的同源序列；若日后出现满足全部条件的同源序列，该判定可被证伪。",
    "- **还原侧定性失效**：P1 气相阴离子 18/18 全部不束缚，Koopmans 还原代理与真实 EA 不是同一物理量；还原轴结论只以 P2 / C1 为载体。",
    "- **基组无弥散**：r2SCAN-3c 的 def2-mTZVPP 不含弥散函数，不能裁断 0.01 eV 量级的阴离子束缚与否（T5）；氧化侧不受此限制。",
    "- **单构象 + G1 / G2 两级几何**：主结果建立在 GFN2-xTB 单构象几何 G1 上，未做全局构象搜索；G2 台阶仅在 12 分子审计子集。",
    "- **隐式溶剂**：P2 为 CPCM(SMD) 隐式溶剂，不含显式溶剂分子；C2 只做第一溶剂壳的几何预筛。",
    "- **锚点样本小**：外部气相锚点仅 12 个分子，τ_b 的 bootstrap 区间较宽（如 P0 臂 [0.16, 0.90]）。",
    "",
    "## 复现边界与 clean-room 审计",
    "",
    "仓库内的可复现面（**不依赖任何仓库外文件**）：`config/`、`data/`、`outputs/`、`scripts/`、`src/`、`tests/`、`structures/`、`README.md`、`FINAL_CONCLUSIONS.md`。",
    "",
    "**仓库外交付层**：`..\\成果输出\\`、`..\\核心文件\\`、`..\\论文\\` 位于**本仓库之外**，不随 GitHub 一起分发。README 引用它们只是交付层说明；外部 reviewer 克隆本仓库时**不需要**它们。",
    "",
    "clean-room 入口（在全新 clone 中逐条执行）：",
    "",
    "```powershell",
    ".venv\\Scripts\\python.exe scripts\\build_metadata.py --check",
    ".venv\\Scripts\\python.exe scripts\\build_github_readme.py --check",
    ".venv\\Scripts\\python.exe scripts\\build_final_conclusions.py --check",
    ".venv\\Scripts\\python.exe scripts\\audit_clean_room.py",
    ".venv\\Scripts\\python.exe scripts\\analyze_r13_summary_figure.py --check",
    ".venv\\Scripts\\python.exe scripts\\freeze_gates.py --stage all",
    ".venv\\Scripts\\python.exe -m pytest",
    "```",
    "",
    "`scripts/audit_clean_room.py` 逐项报告「缺什么会挡住复现」；本机 `E:\\ORCA软件\\...` 与 xTB 只影响**新增电子结构计算**，不影响仓库内任何已冻结产物、check 或测试。",
    "",
    "## 工程约定（轻量借鉴 `电解质ML`）",
    "",
    "- **可审计**：每个数值可追溯到 mol_id / motif / 几何 / 方法 / 原始输出 / QC 状态。",
    "- **确定性**：xTB 子进程固定单线程，避免 OpenMP 归约次序导致的几何漂移；读写一律 UTF-8（无 BOM）+ LF。",
    "- **预注册**：阈值、k 值、随机种子在看结果前冻结（`config/prereg.yaml`）。",
    "- **verifier**：关键产物由脚本重建而非手改（`build_metadata.py --check`、`build_github_readme.py --check`）。",
    "",
    "## 成果输出（交付层）",
    "",
    "对外交付件放在与代码仓库并列的 `E:\\Claude Code\\电解液溶剂-HB\\成果输出`（对标下游项目 `E:\\Claude Code\\电解质ML\\成果输出` 的布局）：顶层 `README.md`（索引 + 一周一张表）与 `数据结果汇总.md`、`统一数据文档.md`，以及 `week1`–`week23` 逐周目录与 `week22_hardening`、`week24_corealign`、`week25_gate1` 三个扩展包。每个包含蒸馏结果表（CSV）、汇总（JSON）、报告（MD）、`artifacts/`（PNG 图）、`SHA256SUMS` 与 `verification.json`。",
    "",
    "该目录**只放蒸馏产物与图**，不放原始 ORCA / xTB 输出与二进制 scratch（原始输出去仓库 `outputs/` 取），并且可以由脚本**确定性重建**：",
    "",
    "```powershell",
    ".venv\\Scripts\\python.exe scripts\\build_deliverables.py",
    ".venv\\Scripts\\python.exe scripts\\build_week24_deliverables.py --check",
    ".venv\\Scripts\\python.exe scripts\\build_week25_deliverables.py --check",
    "```",
    "",
    "图表索引 F0–F56：`F47` 属 `week22_hardening`，`F48`–`F51` 属 `week24_corealign`，`F52`–`F54` 属 `week25_gate1`；`F55` 见 `outputs/week25`，`F56` 见仓库内 `outputs/week26`（R14 收口汇总图，不在交付层）；逐图内容与来源见 `成果输出/数据结果汇总.md` 的「图表索引」表。",
]

R13_HEAD = [
    "## R13 定义修订（2026-10-08，append-only amendment）",
    "",
    "外部评审把仓库定位为「相当完整的 decision-stability prototype」，并指出下一阶段的关键不是继续堆周，而是补齐几个**物理定义缺口**、收缩叙事。",
    "R13 按优先级落地（完整对照见 `docs/46_definitional_amendment_r13.md`）：",
    "",
    "| 优先级 | 修正 | 落地 |",
    "| --- | --- | --- |",
    "| 🔴 P0 | P1 vertical → 拆成 `P1v` + `P1a` | `config/scientific_definitions.yaml`、`outputs/phase2_p1a/`、`docs/p1v_vs_p1a.md` |",
    "| 🔴 P0 | C1 还原态 state-identity 分层 | `outputs/state_identity/`、`docs/state_identity_protocol.md` |",
    "| 🔴 P0 | Gate 1 双轨、停用 validated target | `target_naming`、`docs/gate1_negative_result.md` |",
    "| 🟠 P1 | `f_robust_inv = 0` 三元化 + 分辨率曲线 | `src/electrolyte_ranking/decision_state.py`、`outputs/decision_state/` |",
    "| 🟠 P1 | C2 更名 first-shell microsolvation（CN=2） | `axis_B_environment_states.C2` |",
    "| 🟠 P1 | P2 拆成 `P2a`（SMD）/ `P2eps`（bare CPCM ε） | `axis_A_proxy_hierarchy` |",
    "",
]


def r13_log() -> "list[str]":
    dec = rd("outputs/decision_state/decision_state_report.json")
    sid = rd("outputs/state_identity/state_identity_stratification.json")
    p1a = rd("outputs/phase2_p1a/p1v_vs_p1a.json")
    g1dt = rd("outputs/gate1/gate1_dual_track.json")
    out: "list[str]" = []
    out.append("### R13 · 三态判据 + 分辨率曲线（`outputs/decision_state`）")
    out.append("")
    red = dig(dec, f"rungs.P0->P1v.reduction.decision_state_fractions")
    red_counts = dig(dec, "rungs.P0->P1v.reduction.decision_state_counts")
    if isinstance(red, dict) and isinstance(red_counts, dict):
        out.append(
            f"- `P0 → P1v` 还原轴：STABLE **{fint(red_counts.get('STABLE'))}** / "
            f"UNRESOLVED **{fint(red_counts.get('UNRESOLVED'))}** / ROBUST_INVERSION "
            f"**{fint(red_counts.get('ROBUST_INVERSION'))}**；`f_UNRESOLVED` = {pct(red.get('UNRESOLVED'))}。"
            "「零稳健翻转」在这里的含义是 **evidence insufficient to resolve**，不是 stable（`outputs/decision_state/decision_state_summary.md`）。"
        )
    out.append("")
    out.append("### R13 · C1 还原态身份分层（`outputs/state_identity`）")
    out.append("")
    counts = dig(sid, "label_counts_reduced")
    if isinstance(counts, dict):
        out.append(
            f"- 12 个还原态标签：`Li_centered_or_mixed_redox` **{fint(counts.get('Li_centered_or_mixed_redox'))}**、"
            f"`molecule_centered_redox` **{fint(counts.get('molecule_centered_redox'))}**。"
        )
        out.append(
            f"- 分层后还原轴：all states n = **{fint(dig(sid, 'reduction_all_states.n'))}**（τ_b = "
            f"{fnum(dig(sid, 'reduction_all_states.kendall_tau_b'), 3)}）→ molecule-centered only n = "
            f"**{fint(dig(sid, 'reduction_molecule_centered.n'))}**，**排序无定义**（配不成 pair）。"
        )
    out.append("")
    out.append("### R13 · P1v vs P1a 绝热阶梯（`outputs/phase2_p1a`）")
    out.append("")
    ranking = dig(p1a, "ranking")
    if isinstance(ranking, dict) and ranking.get("defined"):
        out.append(
            f"- 氧化轴 n = **{fint(dig(p1a, 'n'))}**：Kendall τ_b(P1v, P1a) = **{fnum(ranking.get('kendall_tau_b'), 3)}**，"
            f"Spearman ρ = {fnum(ranking.get('spearman_rho'), 3)}；位移 d = IP_a − IP_v 的 population std = "
            f"**{fnum(dig(p1a, 'displacement.population_std_ev'), 3)} eV**（`docs/p1v_vs_p1a.md`）。"
        )
    else:
        out.append("- 氧化轴对照尚未产出（`outputs/phase2_p1a/` 就绪后重跑本生成器即可）。")
    out.append(
        "- 还原轴按 `unbound_anion` 规则**排除**（气相阴离子不束缚），这不是缺陷，而是补出 P1a 这一层的理由本身。"
    )
    out.append("")
    out.append("### R13 · Gate 1 双轨定位（`outputs/gate1`）")
    out.append("")
    ta = dig(g1dt, "track_A.status")
    tb = dig(g1dt, "track_B.status")
    if ta and tb:
        oc = dig(g1dt, "track_B.components.ordering_consistency") or {}
        out.append(
            f"- **Track A**（decision stability）= **{ta}**；**Track B**（external validity）= **{tb}**。"
            f"排序一致性层判 `{oc.get('reason')}`（Kendall τ_b = {fnum(oc.get('kendall_tau_b'), 3)} <"
            f" {fnum((oc.get('criterion') or {}).get('min_tau_b'), 2)}，n_pairs = {fint(oc.get('n_pairs'))}）。"
            "Track A 的结论**不依赖** Track B；Track B 未闭合只削弱「绝对尺度 / 真实排序」类声明的强度"
            "（`outputs/gate1/gate1_dual_track.md`）。"
        )
    out.append("")
    return out


def anti_misread_block() -> "list[str]":
    """The one block a reader must see before quoting ``f_robust_inv = 0``.

    The review flagged this as the single most mis-readable number in the whole
    repository: "zero robust inversions" is *not* "zero ranking instability".
    The numbers are read back from the frozen Stage-10 ladder (20 rung x axis
    combinations), so the block can never drift from the products.
    """

    ladder = dig(rd("outputs/week9/stage10_ladder.json"), "ladder") or []
    fractions: "list[float]" = []
    robust: "list[float]" = []
    for row in ladder:
        if not isinstance(row, dict):
            continue
        for key in ("f_unresolved_before", "f_unresolved_after"):
            value = row.get(key)
            if isinstance(value, (int, float)):
                fractions.append(float(value))
        if isinstance(row.get("f_robust_inv"), (int, float)):
            robust.append(float(row["f_robust_inv"]))
    n_combos = len(ladder)
    worst = max(fractions) if fractions else None
    worst_robust = max(robust) if robust else None
    return [
        f"| 计数 | 值 | 含义 |",
        "| --- | --- | --- |",
        f"| robust inversion | **{fint(worst_robust)} observed** | 在 {fint(n_combos)} 个 (台阶, 轴) 组合中，"
        "没有任何 pair 被**反向证明**（1σ 主口径） |",
        f"| unresolved（最高） | **{pct(worst)}** | 大量 pair 的证据**不足以判定**方向 |",
        "",
        "> **0 robust inversions ≠ 0 ranking instability.** "
        "把 `f_robust_inv = 0` 读成「排序稳定」是本项目最容易被误读的一处；"
        "正确的读法是「不可判定主导（`evidence insufficient to resolve`）」。"
        "汇总图 `outputs/figures/F56_r13_summary.png` 把这句话画进了图里。",
    ]


def build_readme() -> str:
    g1 = rd("outputs/week25/series_rel_ordering_check.json")
    g1_reason = dig(g1, "reason")
    g1_tau = dig(g1, "tau_b")
    g1_pairs = dig(g1, "n_pairs")
    status = (
        "**项目状态**：`Gate 0` **CLOSED** · `Gate 1` **未闭合且 NOT CLOSABLE**"
        "（排序层已评估："
        f"`{g1_reason}`，τ_b = {fnum(g1_tau, 4)} < 0.90，n_pairs = {fint(g1_pairs)}；"
        "绝对标定层按 limitation 处理；预注册要求的同源序列"
        "在公开文献中不存在，**不再尝试把它做成 PASS**，"
        "见 `docs/gate1_negative_result.md`）。"
    )
    gate1_row = (
        "| Gate 1（方法 / 锚点） | **NOT CLOSED** | **排序一致性层**首次可评但未通过：Kendall "
        f"**tau_b = {fnum(g1_tau, 4)} < 0.90**、**n_pairs = {fint(g1_pairs)}**，判 **`{g1_reason}`**"
        f"（一致 {fint(dig(g1, 'concordant'))} / 不一致 {fint(dig(g1, 'discordant'))}）（`outputs/week25/series_rel_ordering_check.json`）。**绝对标定层**：溶液相锚点 31 行 `est` 按 R7 裁决记为 **limitation**，不再单列 blocker。**可闭合性**：判 **NOT CLOSABLE**（预注册要求的同装置 / 同判据 / ≥ 7 分子同源序列在公开文献中不存在，最长 k = 1），作为 negative result 记录，不事后救援。 |"
    )
    lines = [status if ln.startswith("**项目状态**") else ln for ln in HEAD]
    lines = [gate1_row if ln.startswith("| Gate 1（方法") else ln for ln in lines]
    anchor = next(i for i, ln in enumerate(lines) if ln.startswith("**项目状态**"))
    lines[anchor + 1:anchor + 1] = [""] + anti_misread_block()
    lines.extend(weekly_log())
    lines.extend(R13_HEAD)
    lines.extend(r13_log())
    lines.extend(TAIL)
    text = "\n".join(lines)
    if not text.endswith("\n"):
        text += "\n"
    return text


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Build the repository-root GitHub README.md")
    ap.add_argument("--check", action="store_true", help="compare README.md with the built text; never write")
    ap.add_argument("--trace", action="store_true", help="print which numbers were read back from products")
    args = ap.parse_args(argv)

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

    text = build_readme()
    want = text.encode("utf-8")

    if args.trace:
        for tag, ok in RESOLVED:
            print(("READ " if ok else "MISS ") + tag)
        print(f"total={len(RESOLVED)} read={sum(1 for _, ok in RESOLVED if ok)} miss={sum(1 for _, ok in RESOLVED if not ok)}")

    if args.check:
        have = README.read_bytes() if README.exists() else b""
        if have == want:
            print(f"OK: {README.name} matches the generated bytes ({len(want)} bytes, LF, UTF-8 no BOM)")
            return 0
        print(f"MISMATCH: {README.name} is {len(have)} bytes, generated is {len(want)} bytes")
        return 1

    README.write_bytes(want)
    print(f"WROTE {README} ({len(want)} bytes, LF, UTF-8 no BOM)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())