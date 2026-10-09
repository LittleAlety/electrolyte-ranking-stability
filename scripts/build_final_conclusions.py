#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Deterministic builder for FINAL_CONCLUSIONS.md -- the 10-question research index.

Round-2 external review, item 5: the Week 1-25 log is information-dense, so what
is missing is not another calculation but one document that answers exactly ten
questions, each as 结论 -> 数字 -> evidence path -> limitation.

Every number is read back from a frozen product under ``outputs/``; the builder
never recomputes electronic structure and never invents a value.  A missing
product renders as ``n/a`` rather than a guess, so the document degrades
honestly instead of silently.

Usage
-----
    python scripts/build_final_conclusions.py            # (re)write FINAL_CONCLUSIONS.md
    python scripts/build_final_conclusions.py --check    # compare, never write
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TARGET = REPO / "FINAL_CONCLUSIONS.md"

RESOLVED: "list[tuple[str, bool]]" = []


def rd(rel: str) -> dict:
    path = REPO / rel
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def dig(obj, path: str, default=None):
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
    RESOLVED.append((path, ok))
    return cur if ok else default


def fnum(v, nd: int = 3) -> str:
    try:
        return ("%%.%df" % nd) % float(v)
    except (TypeError, ValueError):
        return "n/a"


def fint(v) -> str:
    try:
        return "%d" % int(v)
    except (TypeError, ValueError):
        return "n/a"


def fpct(v, nd: int = 1) -> str:
    try:
        return ("%." + str(nd) + "f%%") % (float(v) * 100.0)
    except (TypeError, ValueError):
        return "n/a"


def fci(pair) -> str:
    if isinstance(pair, (list, tuple)) and len(pair) == 2:
        return "[%s, %s]" % (fnum(pair[0], 2), fnum(pair[1], 2))
    return "n/a"


def row(ladder, rung: str, axis: str, population: str = "native") -> dict:
    for entry in ladder:
        if (entry.get("rung") == rung and entry.get("axis") == axis
                and entry.get("population") == population):
            return entry
    return {}


def q(n: int, question: str, conclusion: str, numbers: str, evidence: str, limitation: str):
    return [
        "## Q%d. %s" % (n, question),
        "",
        "**结论**：" + conclusion,
        "",
        "**数字**：" + numbers,
        "",
        "**Evidence path**：" + evidence,
        "",
        "**Limitation**：" + limitation,
        "",
    ]


def build() -> str:
    p1d = rd("outputs/week4/p1_decision_stability.json")
    p2d = rd("outputs/week4/p2_decision_stability.json")
    ladder_doc = rd("outputs/week9/stage10_ladder.json")
    ladder = dig(ladder_doc, "ladder") or []
    verdicts = dig(ladder_doc, "verdicts") or {}
    b1 = dig(rd("outputs/week22_hardening/stats_b1_b2.json"), "b1") or {}
    t3 = rd("outputs/week4/t3_cpcm_eps_scan_summary.json")
    c1 = rd("outputs/week5/c1_decision_stability.json")
    sid = rd("outputs/state_identity/state_identity_stratification.json")
    s9 = rd("outputs/week8/stage9_results.json")
    dm = rd("outputs/week6/delta_m_frozen.json")
    t6 = rd("outputs/week6/t6_conformer_spread.json")
    s19 = dig(rd("outputs/week18/stage19_relax_analysis.json"), "aggregates.all.all") or {}
    budget = rd("outputs/week25/compute_budget_ledger.json")
    pre = rd("outputs/week11/stage12_prescreen.json")
    p1a = rd("outputs/phase2_p1a/p1v_vs_p1a.json")
    g1 = rd("outputs/week25/series_rel_ordering_check.json")
    g1dt = rd("outputs/gate1/gate1_dual_track.json")
    s3 = rd("outputs/week23/shell3_xtb_sign_test.json")
    s11 = rd("outputs/week10/stage11_sigma_anatomy.json")

    # --- the one number the whole repository is easiest to misread ----------
    fractions, robust = [], []
    for entry in ladder:
        for key in ("f_unresolved_before", "f_unresolved_after"):
            value = entry.get(key)
            if isinstance(value, (int, float)):
                fractions.append(float(value))
        if isinstance(entry.get("f_robust_inv"), (int, float)):
            robust.append(float(entry["f_robust_inv"]))
    worst_unresolved = max(fractions) if fractions else None
    worst_robust = max(robust) if robust else None

    drift = [
        entry for entry in (dig(s11, "subset_drift.P0_to_P1|oxidation") or [])
        if entry.get("n") == 10
    ]
    drift_sd = drift[0].get("tau_b_std") if drift else None

    s9_all12 = {}
    for entry in (dig(s9, "stability") or []):
        if entry.get("axis") == "oxidation" and entry.get("population") == "all12":
            s9_all12["oxidation"] = entry
        if entry.get("axis") == "reduction" and entry.get("population") == "all12":
            s9_all12["reduction"] = entry

    outcomes = dig(s19, "outcomes") or {}
    status = dig(budget, "status_counts") or {}
    prescreen = dig(pre, "prescreen") or {}
    danger = prescreen.get("dangerous_points") or []
    shape = dig(pre, "shape_invariance") or {}
    extrap = dig(pre, "extrapolation") or {}
    closability = dig(g1dt, "track_B.components.closability") or {}
    clos_evidence = dig(closability, "evidence") or {}

    ratio = "n/a"
    p50_single = dig(s19, "abs_single_point_delta_ev.p50")
    p50_relax = dig(s19, "abs_relax_delta_ev.p50")
    if p50_single and p50_relax:
        ratio = fnum(float(p50_single) / float(p50_relax), 0)

    lines: "list[str]" = [
        "# FINAL CONCLUSIONS \u2014 10 个问题（结论 \u2192 数字 \u2192 evidence path \u2192 limitation）",
        "",
        "> 由 `scripts/build_final_conclusions.py` 从 `outputs/` 的冻结产物确定性生成；`--check` 逐字节复核。",
        "> 本文件是**研究成果索引**（只回答 10 个问题）；逐周工作日志见 `README.md`。",
        "> **Scope**：本仓库不建立电解液溶剂的最终排行榜（见 `README.md` 顶部 Scope）。",
        "",
        "## 读前必读（两个最容易误读的点）",
        "",
        "1. **`f_robust_inv = 0` 不等于「排序稳定」。** Stage 10 的 20 个 (台阶, 轴) 组合里，"
        "robust inversion 最大值 = **%s observed**（没有任何 pair 被**反向证明**），同一批数据 "
        "`f_unresolved` 最高 **%s**（证据**不足以判定**方向）。正确读法：「不可判定主导」。"
        "唯一真正出现 robust inversion 的地方是 **P1v \u2192 P1a 绝热阶梯**（n = %s，robust inversion = %s）。"
        % (fint(worst_robust), fpct(worst_unresolved), fint(dig(p1a, "n")),
           fint(dig(p1a, "decision_state_counts.ROBUST_INVERSION"))),
        "",
        "2. **`n = 18` 只支持四层里的三层。** 机制验证 = 可以成立；排序普适性 = 不能宣称；"
        "大规模筛选 = 未验证；方法学 proof-of-concept = 成立（完整表格见 `README.md`）。"
        "本文件所有结论都受此限制。",
        "",
        "---",
        "",
    ]
    # ---------------------------------------------------------------- Q1 ----
    lines += q(
        1,
        "cheap \u2192 target 会不会改变排序？",
        "**会。** 廉价代理量不能替代指定计算目标：P0 \u2192 P1v 已经把排序改写，终点 P0 \u2192 P2a 同样不一致；"
        "预注册判词 `A_cheap_proxy_already_stable` 被判 **%s**。"
        % str(verdicts.get("A_cheap_proxy_already_stable", {}).get("verdict")),
        "P0\u2192P1v 氧化 \u03c4_b = **%s**、还原 \u03c4_b = **%s**（n = %s，CI95 氧化 %s）；"
        "P1v\u2192P2a 氧化 \u03c4_b = %s（唯一接近阈值的一级）、还原 \u03c4_b = %s；"
        "P0\u2192P2a 氧化 \u03c4_b = %s、还原 \u03c4_b = %s。判词证据原文：\u300c%s\u300d"
        % (
            fnum(dig(p1d, "oxidation.kendall_tau_b")), fnum(dig(p1d, "reduction.kendall_tau_b")),
            fint(dig(p1d, "oxidation.n")), fci(dig(p1d, "oxidation.kendall_tau_b_ci95")),
            fnum(dig(p2d, "p1_to_p2.oxidation.kendall_tau_b")),
            fnum(dig(p2d, "p1_to_p2.reduction.kendall_tau_b")),
            fnum(dig(p2d, "p0_to_p2.oxidation.kendall_tau_b")),
            fnum(dig(p2d, "p0_to_p2.reduction.kendall_tau_b")),
            str(verdicts.get("A_cheap_proxy_already_stable", {}).get("evidence", "n/a")),
        ),
        "`outputs/week4/p1_decision_stability.json`、`outputs/week4/p2_decision_stability.json`、"
        "`outputs/week9/stage10_ladder.json`（verdicts）、`outputs/decision_state/decision_state_report.json`",
        "n = 18；\u03c4_b 的 bootstrap CI 宽；子集抽样 N = 10 时 P0\u2192P1 氧化 \u03c4_b 抽样标准差 = **%s**"
        "（`outputs/week10/stage11_sigma_anatomy.json`）——报 \u03c4_b 必须同时报 N 与子集。"
        "本文件不给出任何绝对性能排名结论。"
        % fnum(drift_sd),
    )

    # ---------------------------------------------------------------- Q2 ----
    full10 = dig(b1, "full_10_points") or {}
    dropped = dig(b1, "sensitivity_drop_all_conditional") or {}
    lines += q(
        2,
        "改变主要来自 mean shift 还是 dispersion？",
        "**离散度（dispersion）。** 排序是否被改写由位移的**离散度**主导；位移的平均幅度与 \u03c4_b 的关系"
        "统计上不稳健。",
        "\u03c1(shift std, \u03c4_b) = **%s**（percentile CI95 %s，**不含 0**）；"
        "\u03c1(|mean shift|, \u03c4_b) = **%s**（CI95 %s，**跨 0**）；"
        "\u03c1(shift std, f_unresolved) = **%s**。闭式恒等 `f_unresolved(z) = Pr(q_ij > \u221a2/z)` "
        "在 20 个点上与实测误差精确为 0（T4）。"
        % (
            fnum(dig(b1, "reported_rho_in_ladder.rho_shift_std_vs_tau_b")),
            fci(dig(full10, "rho_shift_std_vs_tau_b.ci95_percentile")),
            fnum(dig(b1, "reported_rho_in_ladder.rho_abs_shift_mean_vs_tau_b")),
            fci(dig(full10, "rho_abs_shift_mean_vs_tau_b.ci95_percentile")),
            fnum(dig(b1, "reported_rho_in_ladder.rho_shift_std_vs_f_unresolved")),
        ),
        "`outputs/week22_hardening/stats_b1_b2.json`、`outputs/week9/stage10_ladder.json`（hypothesis_test）、"
        "`outputs/week10/stage11_sigma_anatomy.json`（theorems T1\u2013T5）",
        "10 个点**不独立**：同一 rung 的两轴共享分子、相邻 rung 共享分子；bootstrap CI 把点当可交换 "
        "\u2192 **乐观**，只作 within-sample 稳定性检查。剔除条件态后 n = %s、\u03c1 = %s（更强）"
        "——结论对子集选择不稳。"
        % (fint(dig(dropped, "n_points")), fnum(dig(dropped, "rho_shift_std_vs_tau_b.observed"))),
    )
    # ---------------------------------------------------------------- Q3 ----
    lines += q(
        3,
        "哪个轴更脆弱？",
        "**还原轴。** 还原轴的 \u03c3 更大、unresolved 更高，是决策稳定性最脆弱的一侧"
        "（C0\u2192C1 还原轴甚至出现负的 \u03c4_b）。",
        "P0\u2192P1v 还原轴 f_unresolved(P_target) = **%s**（氧化 %s）；"
        "P0\u2192P2a 还原轴 **%s**（氧化 %s）；"
        "\u03c3_median（P1v\u2192P2a）还原 **%s eV** 对 氧化 %s eV；"
        "C0\u2192C1 还原轴 \u03c4_b = **%s**。"
        % (
            fpct(dig(p1d, "reduction.f_unresolved_p1")), fpct(dig(p1d, "oxidation.f_unresolved_p1")),
            fpct(dig(p2d, "p0_to_p2.reduction.f_unresolved_p1")),
            fpct(dig(p2d, "p0_to_p2.oxidation.f_unresolved_p1")),
            fnum(dig(p2d, "p1_to_p2.reduction.sigma_median_ev")),
            fnum(dig(p2d, "p1_to_p2.oxidation.sigma_median_ev")),
            fnum(dig(c1, "reduction.kendall_tau_b")),
        ),
        "`outputs/week4/p1_decision_stability.json`、`outputs/week4/p2_decision_stability.json`、"
        "`outputs/week5/c1_decision_stability.json`、`outputs/decision_state/decision_state_report.json`",
        "气相阴离子不束缚（T1 里 18/18 阴离子 `unbound_anion`），因此还原轴在 P0/P1 层的代理量不是同一"
        "物理量；还原轴结论只以 P2 / C1 为载体。r2SCAN-3c 的 def2-mTZVPP 无弥散函数，不能裁断 0.01 eV "
        "量级的阴离子束缚。",
    )

    # ---------------------------------------------------------------- Q4 ----
    eps = dig(t3, "eps_values") or []
    lines += q(
        4,
        "dielectric 是否真的导致 ranking inversion？",
        "**没有观察到。** 介电层主要是数值平移，且不同 \u03b5 之间自相似；但「没有 robust inversion」"
        "\u2260「排序稳定」。",
        "bare CPCM 扫描 \u03b5 \u2208 {%s}、n = %s 分子、%s/%s 作业 ok；"
        "两种 \u03c3 约定下 max f_robust_inv（z = 1.0 / 1.96）= **%s**（any_gt_0 = false）。"
        "\u03b5 = 5 时氧化 \u03c4_b = %s（CI95 %s）；SMD 乙腈层 P1v\u2192P2a 氧化 \u03c4_b = %s / 还原 %s。"
        % (
            "、".join("%g" % e for e in eps), fint(dig(t3, "n_molecules")),
            fint(dig(t3, "n_ok")), fint(dig(t3, "n_jobs")),
            fnum(dig(t3, "robust_inversion.sigma_conventions.two_arm.max_f_robust_inv_z1p0"), 2),
            fnum(dig(t3, "decisions.5.oxidation.kendall_tau_b")),
            fci(dig(t3, "decisions.5.oxidation.kendall_tau_b_ci95")),
            fnum(dig(p2d, "p1_to_p2.oxidation.kendall_tau_b")),
            fnum(dig(p2d, "p1_to_p2.reduction.kendall_tau_b")),
        ),
        "`outputs/week4/t3_cpcm_eps_scan_summary.json`、`outputs/week4/p2_decision_stability.json`、"
        "`outputs/week11/stage12_prescreen.json`",
        "bare CPCM 只含静电项（无 SMD 非静电项）；几何为 G1（vertical，未弛豫）；n = 12 子集；"
        "`f_robust_inv = 0` 的含义是「不可判定主导」，不是「稳定」。",
    )
    # ---------------------------------------------------------------- Q5 ----
    c0c1_ox = row(ladder, "C0_to_C1", "oxidation")
    c0c1_red = row(ladder, "C0_to_C1", "reduction")
    labels = dig(sid, "label_counts_reduced") or {}
    c1sum = rd("outputs/week5/c1_li_coordination_summary.json")
    lines += q(
        5,
        "Li+ coordination 是否改变结论？",
        "**会，而且改变了量的身份。** Li\u207a 配位把还原轴从「分子还原」变成「Li 中心 / 混合还原」，"
        "主 ranking 必须只用 `molecule_centered_redox`。",
        "C0\u2192C1 氧化位移均值 %s eV（std %s）、\u03c4_b = %s；还原位移均值 %s eV（std %s）、"
        "\u03c4_b = **%s**；12 个还原态标签：`Li_centered_or_mixed_redox` %s / "
        "`molecule_centered_redox` %s \u2192 分层后还原轴 n = %s，**排序无定义**。"
        % (
            fnum(c0c1_ox.get("shift_mean_ev")), fnum(c0c1_ox.get("shift_std_ev")),
            fnum(c0c1_ox.get("kendall_tau_b")),
            fnum(c0c1_red.get("shift_mean_ev")), fnum(c0c1_red.get("shift_std_ev")),
            fnum(c0c1_red.get("kendall_tau_b")),
            fint(labels.get("Li_centered_or_mixed_redox")), fint(labels.get("molecule_centered_redox")),
            fint(dig(sid, "reduction_molecule_centered.n")),
        ),
        "`outputs/week9/stage10_ladder.json`、`outputs/week5/c1_decision_stability.json`、"
        "`outputs/state_identity/state_identity_stratification.json`、`docs/state_identity_protocol.md`",
        "C1 只覆盖 10 个分子 / 12 motif；C1 DFT 作业 %s/%s ok（1 个 execution_failed）；"
        "分层后还原轴只剩 %s 个分子，无法给任何还原排序结论。"
        % (fint(dig(c1sum, "n_ok")), fint(dig(c1sum, "n_jobs")),
           fint(dig(sid, "reduction_molecule_centered.n"))),
    )

    # ---------------------------------------------------------------- Q6 ----
    s9sum = rd("outputs/week8/stage9_summary.json")
    lines += q(
        6,
        "microsolvation 是否改变结论？",
        "**不推翻氧化轴结论，但它自己的偏移已让相当一部分 pair 不可判定。**",
        "C1\u2192C2（all12）氧化 \u03c4_b = **%s**、还原 \u03c4_b = %s；%s/%s 作业 ok；"
        "f_unresolved(shell2) 最高 **%s**；第三壳靶向符号检验（GFN2-xTB）n_jobs = %s，裁决 = `%s`。"
        % (
            fnum(dig(s9_all12, "oxidation.kendall_tau_b")),
            fnum(dig(s9_all12, "reduction.kendall_tau_b")),
            fint(dig(s9sum, "n_ok")), fint(dig(s9sum, "n_jobs")),
            fpct(dig(s9_all12, "oxidation.f_unresolved_shell2")),
            fint(dig(s3, "n_jobs")), str(dig(s3, "verdict.label")),
        ),
        "`outputs/week8/stage9_results.json`、`outputs/week8/stage9_summary.json`、"
        "`outputs/week23/shell3_xtb_sign_test.json`",
        "C2 是 **first-shell microsolvation（CN = 2）**，不是 second solvation shell；n = 12；"
        "第三壳只做 GFN2-xTB 符号 / 形状检验（`level_caveat`：绝对值不得与 r2SCAN-3c 阶梯并列）。",
    )
    # ---------------------------------------------------------------- Q7 ----
    t6p1 = dig(t6, "counts.p1") or {}
    p0term = dig(dm, "per_layer.p0") or {}
    method = dig(dm, "method_evidence") or {}
    lines += q(
        7,
        "conformer uncertainty 是否足以覆盖 ranking gap？",
        "**是（还原轴）。** 构象系综给出的不确定度 floor 足以覆盖还原轴的排序 gap，这正是还原轴不可判定的"
        "机制来源。",
        "T6 构象系综 %s 构象 / %s 分子；组装出的 delta_m：氧化 **%s eV**、还原 **%s eV**，"
        "主导项均为 `%s`；方法 \u03c3：氧化 %s eV、还原 %s eV；构象 p90：氧化 %s eV、还原 %s eV。"
        % (
            fint(t6p1.get("n_conformers_total")), fint(t6p1.get("n_molecules")),
            fnum(dig(p0term, "oxidation.delta_m_ev")), fnum(dig(p0term, "reduction.delta_m_ev")),
            str(dig(p0term, "oxidation.dominant_term")),
            fnum(dig(method, "oxidation.sigma_method_ev")), fnum(dig(method, "reduction.sigma_method_ev")),
            fnum(dig(t6, "layers.p1.aggregate.oxidation.p90_spread_ev")),
            fnum(dig(t6, "layers.p1.aggregate.reduction.p90_spread_ev")),
        ),
        "`outputs/week6/t6_conformer_spread.json`、`outputs/week6/delta_m_frozen.json`",
        "T6 只做 12 分子子集、单分子平均 2\u20134 个构象（不是全局构象搜索）；delta_m 是**候选值**"
        "（`delta_m_frozen.json.status` = %s）；构象分布来自 GFN2-xTB 优化的中性几何。"
        % str(dig(dm, "status")),
    )

    # ---------------------------------------------------------------- Q8 ----
    lines += q(
        8,
        "SCF alternative 是否是真实物理态差异？",
        "**大多数是假象，少数是真不同态。** 单点能量差主要来自 SCF 落在不同（或较高）的局域解；"
        "一旦两条腿都允许几何弛豫，偏好大多反转。",
        "%s 个 `moread_lower` 格：|\u0394| 单点中位 **%s eV** \u2192 弛豫后 **%s eV**（缩小 ~%s\u00d7）；"
        "偏好反转 **%s / %s**；结局 distinct_lower %s / distinct_higher %s / same_higher %s。"
        % (
            fint(dig(s19, "n_cells")), fnum(p50_single, 5), fnum(p50_relax, 5), ratio,
            fint(dig(s19, "n_preference_flipped")), fint(dig(s19, "n_cells")),
            fint(outcomes.get("distinct_lower")), fint(outcomes.get("distinct_higher")),
            fint(outcomes.get("same_higher")),
        ),
        "`outputs/week18/stage19_relax_analysis.json`、`docs/28_week18_report.md`、"
        "`outputs/week23/targeted_two_guess.json`",
        "只对 `moread_lower` 的 %s 格做（非全量）；材料阈值 1 meV；仍有 %s 格弛豫后仍是不同态"
        "（真差异），未做路径 / NEB 级别的判定；结论限于 r2SCAN-3c 与这些 \u03b5。"
        % (fint(dig(s19, "n_cells")), fint(outcomes.get("distinct_higher"))),
    )
    # ---------------------------------------------------------------- Q9 ----
    lines += q(
        9,
        "哪些额外计算最值得花预算？",
        "**先用 0 计算量的闭式判据 + 自相似律筛掉可预测的层级，再把预算集中到还原轴的构象 / 态身份"
        "靶向复核。**",
        "预算账本 \u00a721（%s 条）：PASS %s / PARTIAL %s / MISSING %s；"
        "判据预筛（z = 1.0）在 18 个点上标出 %s 个「预测不可用」点：%s；"
        "介电自相似（Born 因子）最大相对散布 %s（氧化 %s）；三点点外推最大绝对误差 %s eV；"
        "AL 预算关键点 n_T = %s（C 轴）/ %s（E 轴）。"
        % (
            fint(len(dig(budget, "items") or [])),
            fint(status.get("PASS")), fint(status.get("PARTIAL")), fint(status.get("MISSING")),
            fint(prescreen.get("n_dangerous")),
            " / ".join("`%s`" % p for p in danger) or "n/a",
            fpct(shape.get("max_rel_spread")),
            fpct(dig(shape, "max_rel_spread_by_axis.oxidation")),
            fnum(extrap.get("three_point_max_abs_err_ev")),
            fint(dig(budget, "totals.al_budget_key_n_T_C_oxidation")),
            fint(dig(budget, "totals.al_budget_key_n_T_E_oxidation")),
        ),
        "`outputs/week25/compute_budget_ledger.json`、`outputs/week11/stage12_prescreen.json`、"
        "`outputs/week7/stage8_al_results.json`、`outputs/week10/stage11_sigma_anatomy.json`",
        "仓库内**没有** CPU-core-hours / p90 作业成本 / frequency-only 成本字段（账本中 2 条 MISSING）"
        "\u2192 只能给相对预算，不能给绝对金额；AL 曲线只在 10 分子 common subset 上。",
    )

    # --------------------------------------------------------------- Q10 ----
    red2 = rd("outputs/week25/gate1_reduction_secondary.json")
    lines += q(
        10,
        "Gate 1 最终为什么不能闭合？",
        "**因为预注册要求的同源序列在公开可验证数据里不存在。** Gate 1 = NOT CLOSED **且** "
        "NOT CLOSABLE，作为 negative result 记录。",
        "排序一致性层：\u03c4_b = **%s < %s**、n_pairs = %s（一致 %s / 不一致 %s）\u2192 `%s`；"
        "覆盖层：最长同装置 / 同判据同源序列 **k = %s**（要求 \u2265 %s）；"
        "还原轴只有 %s 个 pair（门槛 %s）= 数据不足，不是不一致；"
        "绝对标定层：%s 行仍 `est`，升级 %s 行。"
        % (
            fnum(dig(g1, "tau_b"), 4), fnum(dig(g1, "criterion.min_tau_b"), 2),
            fint(dig(g1, "n_pairs")), fint(dig(g1, "concordant")), fint(dig(g1, "discordant")),
            str(dig(g1, "reason")),
            fint(clos_evidence.get("longest_homologous_series_k")),
            fint(dig(closability, "prereg_requirement.min_species_covering_core_set")),
            fint(dig(red2, "n_pairs")), fint(dig(red2, "criterion.min_pairs")),
            fint(clos_evidence.get("anchor_rows_total")),
            fint(clos_evidence.get("upgraded_anchor_rows")),
        ),
        "`outputs/week25/series_rel_ordering_check.json`、`outputs/week24_corealign/gate1_anchor_feasibility.md`、"
        "`outputs/gate1/gate1_dual_track.json`、`docs/gate1_negative_result.md`",
        "数值本身不得事后通过剔除分子 / 替换模型列 / 放宽容差「救回」；要闭合需要一条覆盖 \u2265 %s 个"
        "核心集分子、同装置 / 同判据、描述符在溶剂间真有离散度的新同源序列 —— 这属于**新的实验数据**，"
        "不是新的计算量。"
        % fint(dig(closability, "prereg_requirement.min_species_covering_core_set")),
    )
    # ------------------------------------------------------------- closing --
    lines += [
        "---",
        "",
        "## 收口清单",
        "",
        "**可以声称的**：机制（位移离散度决定排序是否被改写）、方法学（三态判据 + 分辨率曲线 + "
        "最小信息预算）、已冻结产物的可复现性。",
        "",
        "**不能声称的**：任何形式的绝对性能排名、排序规律的普适性、大规模筛选能力、"
        "`validated target` 一类措辞（Gate 1 闭合前禁用）。",
        "",
        "**未决 / 下一步若有资源**：先补预算账本的 2 条 MISSING（CPU-core-hours、p90 作业成本），"
        "再做还原轴构象 / 态身份的靶向复核；不建议为 Gate 1 继续堆周次计算（它是 NOT CLOSABLE）。",
        "",
        "**工程入口**：`scripts/build_final_conclusions.py --check`、`outputs/figures/F56_r13_summary.png`、"
        "`docs/47_clean_room_reproduction_audit.md`、`scripts/audit_clean_room.py`。",
        "",
        "## 新阶段批次登记（physics_completion_v1）",
        "",
        "本仓库另登记了一个**新批次** `physics_completion_v1`（`config/physics_completion_v1.yaml`，week37-week44）：",
        "它把《电解液排序稳定性：物理证据补强与决策预算研究执行方案》登记为可追溯产物，**零新增电子结构计算**、",
        "零数据剔除、零阈值改动，逐周镜像见仓库外 `成果输出（part2）/week37..week44`。",
        "该批次**不改变本文件 10 个问题的任何答案**（Gate 1 仍为 NOT CLOSED / NOT CLOSABLE）；",
        "其研究问题→结果→证据→限制另见 `docs/physics_completion_final_report.md`。",
        "",
    ]

    text = "\n".join(lines)
    if not text.endswith("\n"):
        text += "\n"
    return text


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Build FINAL_CONCLUSIONS.md")
    parser.add_argument("--check", action="store_true", help="compare, never write")
    parser.add_argument("--trace", action="store_true", help="print which numbers were read back")
    args = parser.parse_args(argv)

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

    text = build()
    want = text.encode("utf-8")

    if args.trace:
        for tag, ok in RESOLVED:
            print(("READ " if ok else "MISS ") + tag)
        print("total=%d read=%d miss=%d"
              % (len(RESOLVED), sum(1 for _, ok in RESOLVED if ok),
                 sum(1 for _, ok in RESOLVED if not ok)))

    if args.check:
        have = TARGET.read_bytes() if TARGET.exists() else b""
        if have == want:
            print("OK: %s matches the generated bytes (%d bytes, LF, UTF-8 no BOM)"
                  % (TARGET.name, len(want)))
            return 0
        print("MISMATCH: %s is %d bytes, generated is %d bytes"
              % (TARGET.name, len(have), len(want)))
        return 1

    TARGET.write_bytes(want)
    print("WROTE %s (%d bytes, LF, UTF-8 no BOM)" % (TARGET, len(want)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
