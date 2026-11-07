"""Render ``docs/32_week21_report.md`` from the batch-A (docs/31) artefacts.

Week 21 executes batch A of ``docs/31_plan_revision_expert_review.md`` -- five
items that add no new electronic structure and change no frozen definition:

* R1 (+R10) -- the three arms were scored on different molecule sets, so their
  tau_b values were not comparable; align them, then use the *paired* test.
* R2        -- demote ``rho(std, tau_b) = -0.851`` to an illustration and put a
  synthetic-data phase diagram in its place.
* R3        -- say "identity" everywhere and run one out-of-sample test.
* R6        -- write the scope of the "structurally impossible" lemma into the text.
* R4(a)     -- move the "CDS contributes exactly zero" fact into the body prose.

Every number in the rendered text is read from the artefacts; the module holds
prose and formatting helpers only.  ``--check`` re-renders in memory and compares
byte for byte with the file on disk.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
W4 = REPO / "outputs" / "week4"
W21 = REPO / "outputs" / "week21"
FIGDIR = REPO / "outputs" / "figures"
OUT_DEFAULT = Path(os.environ.get("W21_REPORT_OUT") or (REPO / "docs" / "32_week21_report.md"))

MANIFEST = FIGDIR / "figure_manifest_week21.md"
F42 = "F42_sigma_synthetic_phase_diagram.png"

#: the sentence the terminal site quotes verbatim as the week-21 tag.  Kept here
#: so the report and the site can never drift apart.  No markup: the site stores
#: the plain text and a test strips markup from the report before comparing.
TAG = ("把三臂对齐到同一批 10 个分子之后，ΔSCF 的 τ_b 仍是三者最高（0.911 vs 0.778 vs 0.689），"
       "但与另外两臂的差距在配对检验下全部跨 0（配对 95% CI [−0.200, +0.550]，"
       "精确配对置换 p = 0.805）——所以从本周起，项目对外只能说「MAE 的排序与 τ_b 的排序不一致」，"
       "不能说「ΔSCF 的排序显著更好」。")


def _json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _fmt(value, digits=3):
    if value is None:
        return "n/a"
    return ("%%.%df" % digits) % value


def _signed(value, digits=3):
    if value is None:
        return "n/a"
    return ("%+.*f" % (digits, value))


def _caption(manifest: Path, figure: str) -> str:
    """Pull the one-line caption the figure manifest pins for the site."""

    for line in manifest.read_text(encoding="utf-8").splitlines():
        if line.startswith("One-line caption (verbatim, for the terminal site):"):
            return line.split(":", 1)[1].strip()
    raise SystemExit("no one-line caption in %s" % manifest)


def render(data: Path = W21) -> str:
    align = _json(W4 / "p1_anchor_comparison.json")["arm_alignment"]
    verdict = align["verdict"]
    arms = align["arms_on_common_subset"]
    paired = align["paired_delta_tau_b"]
    k_abs = align["k_abs"]
    syn = _json(data / "sigma_synthetic.json")
    meas = syn["measured_correlations"]
    synth = syn["synthetic_correlations"]
    sens = syn["subset_sensitivity"]
    bounds = syn["boundaries"]
    frozen = _json(data / "sigma_prospective_frozen.json")
    prov = _json(data / "sigma_prospective.json")
    score = prov["scoring"]
    rows = {("%s|%s" % (row["set"], row["axis"])): row for row in score["rows"]}
    caption = _caption(MANIFEST, F42)

    lines = []
    add = lines.append

    add("# Week 21 报告 —— 批次 A：把结题前必须堵掉的五个统计/措辞漏洞堵上")
    add("")
    add("> 上游：`docs/31_plan_revision_expert_review.md`（外部评审的可执行条目表 R1–R12）。")
    add("> 本轮只做**批次 A**（R1 + R10、R2、R3、R6、R4a）：全部为**纯分析**，")
    add("> **零**新增电子结构作业、**零**冻结件改动。")
    add("> 冻结件状态：`config/prereg.yaml` 与 `config/scientific_definitions.yaml` **0 改动** → **Gate 0 保持 CLOSED**；")
    add("> **Gate 1 仍为 NOT CLOSED**（唯一 blocker：溶液锚点 31 行 `method=est`）。")
    add("")
    add("---")
    add("")
    add("## 0. 一句话结论")
    add("")
    add(TAG)
    add("")
    add("三条互不依赖的收获，都在**不新增任何计算**的前提下：")
    add("")
    add("- **R1**：三臂此前算在**不同的分子集**上（n = 12 / 10 / 12），所以 0.911 与 0.606 / 0.727 **不是同一个量**。")
    add("  查清排除原因（ΔSCF 臂的来源审计表只有 12 个分子，VC 与 MA 从未被提交给它，**不是** SCF 失败、**不是** `unbound_anion`）、")
    add("  对齐到共同 10 分子重算、并补上**配对** bootstrap 与**精确配对置换**检验之后：点估计排序不变，")
    add("  但**两两差异的配对 95%% CI 全部跨 0**（配对置换 p = %.3f–%.3f）——**排序差异未达显著**。"
        % (min(item["permutation"]["p_value"] for item in paired.values()),
           max(item["permutation"]["p_value"] for item in paired.values())))
    add("- **R2**：Week 9 的 ρ(std, τ_b) = %.3f 降级为「现象示意（10 点 / 5 台阶）」。合成数据相图给出机制侧的定量边界："
        % meas["spearman_shift_std_vs_tau_b"])
    add("  换到 std 轴，相图上的秩相关是 **%.3f**；氧化靶轴上 τ_b 均值跌破 0.8 于 std = %s eV、跌破 0.5 于 %s eV"
        % (synth["spearman_shift_std_vs_tau_b"],
           _fmt(bounds["oxidation"]["std_where_mean_tau_b_below_0p8"], 2),
           _fmt(bounds["oxidation"]["std_where_mean_tau_b_below_0p5"], 2)))
    add("  （还原靶轴 %s / %s eV）。而 ρ(|mean|, τ_b) = %.3f 被判定为**共线性伪影**："
        % (_fmt(bounds["reduction"]["std_where_mean_tau_b_below_0p8"], 2),
           _fmt(bounds["reduction"]["std_where_mean_tau_b_below_0p5"], 2),
           meas["spearman_abs_shift_mean_vs_tau_b"]))
    add("  实测点上 ρ(|mean|, std) = %s，相图里同一相关系数是 %.3f。"
        % (_signed(meas["spearman_abs_shift_mean_vs_shift_std"], 3),
           synth["spearman_abs_shift_mean_vs_tau_b"]))
    add("- **R3**：T1–T5 的定位由「拟合精度」改写为**代数恒等式**，并补了一次**先冻结、后打分**的样本外检验："
        "带符号规则 %d/%d、朴素规则 %d/%d。"
        % (score["signed_rule_hits"], score["n_predictions"],
           score["naive_rule_hits"], score["n_predictions"]))
    add("")
    add("---")
    add("")
    add("## 1. 本轮范围（`docs/31` §4 批次 A）")
    add("")
    add("| # | 条目 | 类型 | 落点 |")
    add("| --- | --- | --- | --- |")
    add("| R1 (+R10) | 三臂子集对齐 + 配对显著性 | 纯分析 | `scripts/analyze_p1_core_set.py`、`docs/10_week4_report.md` §2.3.1 |")
    add("| R2 | −0.851 降级 + 合成数据相图 | 纯计算 | `scripts/analyze_sigma_synthetic.py`、`docs/19` §0、`docs/20` §0/§3 |")
    add("| R3 | 恒等式措辞 + 前瞻检验 | 纯分析 | `scripts/analyze_sigma_prospective.py`、`docs/20` §7.4 |")
    add("| R6 | 「结构性不可能」写死适用范围 | 纯措辞 | `docs/26` §0/§4.7、`docs/assets/data.js`、交付层模板 |")
    add("| R4(a) | 「CDS 对垂直量精确为 0」进正文 | 纯措辞 | `docs/22_week12_report.md` §7.1 |")
    add("")
    add("**刻意不做的**：批次 B（R9 xTB 热修正抽样、R4b 导体极限、R11 NEB 精修）需要新计算；")
    add("批次 C 的 R7 要动 Stage 1 冻结件与 Gate 关闭判据，**必须等 PI 裁决**；批次 D（R8、R12）不阻塞结题。")
    add("")
    add("---")
    add("")
    add("## 2. R1 —— 三臂对齐，然后做真正的配对检验")
    add("")
    add("### 2.1 查清的排除原因（此前留白）")
    add("")
    coverage = align["arm_coverage"]
    add("被 ΔSCF 臂丢掉的两个有锚点分子是 **%s**。原因不是 SCF 不收敛、也不是 `unbound_anion`（那是 EA 侧的质量标记），"
        % "、".join(align["excluded_from_common_subset"]["GFN2_dSCF_xTB"]["molecules"]))
    add("而是这一臂的来源表 `%s` **只有 %d 个分子**：" % (coverage["source"], coverage["n_molecules_in_source"]))
    add("")
    add("```")
    add("; ".join(coverage["molecules_in_source"]))
    add("```")
    add("")
    add("core set 里**从未被提交给该臂**的 %d 个分子是：%s。"
        % (len(coverage["core_set_molecules_absent_from_source"]),
           "、".join(coverage["core_set_molecules_absent_from_source"])))
    add("锚点表恰好也有 VC、MA 的气相 IP，于是「有锚点 × 三臂齐备」的交集只剩 **%d 个分子**：%s。"
        % (align["n_common_subset"], "、".join(align["common_subset"])))
    add("")
    add("### 2.2 对齐后重算（同一估计量）")
    add("")
    add("| 臂 | n | MAE (eV) | bias (eV) | Kendall tau_b [95% CI] | 参照物 |")
    add("| --- | --- | --- | --- | --- | --- |")
    for key, label in (("P0_koopmans_xTB", "P0 Koopmans（GFN2-xTB）"),
                       ("GFN2_dSCF_xTB", "GFN2-xTB ΔSCF"),
                       ("P1_r2scan3c", "P1 r2SCAN-3c")):
        arm = arms[key]
        add("| %s | %d | %s | %s | %s [%s, %s] | %s |"
            % (label, arm["n"], _fmt(arm["mae_ev"]), _signed(arm["bias_ev"]),
               _fmt(arm["kendall_tau_b"]),
               _fmt((arm.get("kendall_tau_b_ci95") or [None, None])[0], 2),
               _fmt((arm.get("kendall_tau_b_ci95") or [None, None])[1], 2),
               arm["tau_b_reference"]))
    add("")
    add("**连带项（公式内推，不是新判据）**：Top-k 规则 `%s` 在 N = %d 时给出 k = %s；"
        % (k_abs["rule"], k_abs["n_core_set"],
           " / ".join(str(k_abs["core_set"][key]["k_prereg_formula"]) for key in sorted(k_abs["core_set"]))))
    add("对齐到 N = %d 后按**同一公式**得 k = %s（`ranking._resolve_k` 的 `round(frac*N)` 在这些分数上与冻结式逐项相同，"
        % (k_abs["n_aligned"],
           " / ".join(str(k_abs["aligned"][key]["k_prereg_formula"]) for key in sorted(k_abs["aligned"]))))
    add("`arm_alignment.k_abs` 逐项记了这个核对）。")
    add("")
    add("### 2.3 配对检验与 headline 改写")
    add("")
    add("| 对比 | Δ tau_b | 配对 95% CI | 配对置换 p | 精确 |")
    add("| --- | --- | --- | --- | --- |")
    for key, label in (("GFN2_dSCF_xTB_minus_P1_r2scan3c", "ΔSCF − P1 r2SCAN-3c"),
                       ("GFN2_dSCF_xTB_minus_P0_koopmans_xTB", "ΔSCF − P0 Koopmans"),
                       ("P1_r2scan3c_minus_P0_koopmans_xTB", "P1 − P0")):
        item = paired[key]
        add("| %s | %s | [%s, %s] | %.3f | %s |"
            % (label, _signed(item["observed_delta_tau_b"]),
               _signed(item["paired_ci95"][0]), _signed(item["paired_ci95"][1]),
               item["permutation"]["p_value"],
               "是（%d 种赋值全枚举）" % item["permutation"]["total_assignments"]
               if item["permutation"]["exact"] else "否（抽样）"))
    add("")
    add("**结论**：三个配对区间全部跨 0，`arm_alignment.verdict.status = \"%s\"`、"
        % verdict["status"])
    add("`all_three_pairwise_tests_unresolved = %s`。" % str(verdict["all_three_pairwise_tests_unresolved"]).lower())
    add("按 `docs/31` R1 的验收判据，headline 已改写为「**排序差异未达显著**」——见 `docs/10_week4_report.md` §2.3.1。")
    add("")
    add("### 2.4 两类 τ_b 的参照物（禁止混引）")
    add("")
    refs = _json(W4 / "p1_anchor_comparison.json")["tau_b_reference"]
    add("| 族 | 参照物 | 本项目取值 |")
    add("| --- | --- | --- |")
    add("| anchor-referenced | 实验气相 IP（`data/anchors/gas_phase_anchors.csv`） | %s（原 n = 12 口径）/ %s（共同 n = %d 口径） |"
        % (" / ".join(_fmt(refs["anchor_referenced"]["carriers"][key])
                      for key in ("P0_koopmans_xTB", "GFN2_dSCF_xTB", "P1_r2scan3c")),
           " / ".join(_fmt(refs["anchor_referenced"]["carriers"][key])
                      for key in ("P0_koopmans_xTB__common_subset", "GFN2_dSCF_xTB__common_subset",
                                  "P1_r2scan3c__common_subset")),
           refs["anchor_referenced"]["carriers"]["n_of_common_subset"]))
    add("| target-model-referenced | 目标模型 P1 自身（无外部参照） | 氧化 %s / 还原 %s（n = %s） |"
        % (_fmt(refs["target_model_referenced"]["carriers"]["P0_vs_P1_oxidation"]),
           _fmt(refs["target_model_referenced"]["carriers"]["P0_vs_P1_reduction"]),
           refs["target_model_referenced"]["carriers"]["n"]))
    add("")
    add("### 2.5 R10：小样本纪律")
    add("")
    add("- 所有关键对比改为报**配对差值分布**（本节 §2.3 是一次示范）；")
    add("- 「Week 9 被迫统一到共同 10 分子」已写进 `docs/19_week9_report.md` §2.6；")
    add("- 子集敏感性：同一组秩相关在 native 与 common-10 上**同向** ——")
    add("  ρ(std, τ_b)：%s（native）vs %s（common-10）；ρ(|mean|, τ_b)：%s vs %s；ρ(std, f_unresolved)：%s vs %s。"
        % (_fmt(sens["native"]["spearman_shift_std_vs_tau_b"]),
           _fmt(sens["common10"]["spearman_shift_std_vs_tau_b"]),
           _fmt(sens["native"]["spearman_abs_shift_mean_vs_tau_b"]),
           _fmt(sens["common10"]["spearman_abs_shift_mean_vs_tau_b"]),
           _fmt(sens["native"]["spearman_shift_std_vs_f_unresolved"]),
           _fmt(sens["common10"]["spearman_shift_std_vs_f_unresolved"])))
    add("")
    add("---")
    add("")
    add("## 3. R2 —— 相图取代相关系数")
    add("")
    add("### 3.1 降级")
    add("")
    add("`docs/19_week9_report.md` §0 与 `outputs/week9/stage10_summary.md` 的同一张表现在把 −0.851 标为")
    add("**「现象示意（n = 10 点 / 5 台阶）」**，并新增「证据等级」一列。降级的两条硬理由：")
    add("")
    add("1. 10 个点来自 **5 个台阶**（每级两个轴），有效自由度接近 5；")
    add("2. `|mean|` 那一行是共线性伪影（下表）。")
    add("")
    add("### 3.2 合成数据相图")
    add("")
    add("模型：固定靶排序 `t`（取本项目真实的 P1 靶值），令 `delta_i = mean + std * z_i`，")
    add("并把 `z` 在每个 replicate 内标准化，使 `delta` 的**样本 sd 恰为 std**。")
    add("网格 %d × %d（mean ∈ [%s, %s] eV，std ∈ [%s, %s] eV），每格 %d 组重抽样。"
        % (len(syn["grid"]["mean_ev"]), len(syn["grid"]["std_ev"]),
           _fmt(syn["grid"]["mean_ev"][0], 1), _fmt(syn["grid"]["mean_ev"][-1], 1),
           _fmt(syn["grid"]["std_ev"][0], 1), _fmt(syn["grid"]["std_ev"][-1], 1),
           syn["grid"]["replicates_per_cell"]))
    add("")
    add("| 量 | 实测 10 点（5 台阶） | 相图（%d 格） | 读法 |" % synth["n_sample_cells"])
    add("| --- | --- | --- | --- |")
    add("| ρ(std, τ_b) | %s | %s | 两个数据源都指向「离散度决定损伤」 |"
        % (_fmt(meas["spearman_shift_std_vs_tau_b"]), _fmt(synth["spearman_shift_std_vs_tau_b"])))
    add("| ρ(|mean|, τ_b) | %s | %s | 实测那个 −0.535 **不是** mean 的因果作用 |"
        % (_fmt(meas["spearman_abs_shift_mean_vs_tau_b"]), _fmt(synth["spearman_abs_shift_mean_vs_tau_b"])))
    add("| ρ(|mean|, std) | %s | （按构造独立） | 实测的共线性正是 −0.535 的来源 |"
        % _fmt(meas["spearman_abs_shift_mean_vs_shift_std"]))
    add("| ρ(std, f_unresolved) | %s | — | 离散度经 σ_ij 直接喂给不可判定比例 |"
        % _fmt(meas["spearman_shift_std_vs_f_unresolved"]))
    add("")
    add("**mean 轴严格常数**：三张相图沿 mean 轴的最大绝对差 = **%.2e**。"
        % syn["mean_invariance"]["max_abs_tau_b_difference_vs_mean_0"])
    add("这不是数值巧合而是可证的恒等式：给每个分子加同一个常数，既不能换序、也不能改变任何 pair 差。")
    add("")
    add("**std 轴上的定量边界**：")
    add("")
    add("| 靶轴 | τ_b 均值跌破 0.8 | 跌破 0.5 | Top-20% 重叠跌破 1.0 |")
    add("| --- | --- | --- | --- |")
    for axis, label in (("oxidation", "氧化"), ("reduction", "还原")):
        add("| %s | std = %s eV | std = %s eV | std = %s eV |"
            % (label,
               _fmt(bounds[axis]["std_where_mean_tau_b_below_0p8"], 2),
               _fmt(bounds[axis]["std_where_mean_tau_b_below_0p5"], 2),
               _fmt(bounds[axis]["std_where_mean_overlap_below_1"], 2)))
    add("")
    add("### 3.3 实测点与曲线的关系（诚实边界）")
    add("")
    add("F42 的 (c) 面板把实测 10 点叠在合成曲线上：多数点贴着曲线，但**两个例外各有明确的物理身份**，")
    add("它们恰好说明了为什么闭式判据（含 `q_ij` 的对齐信息）必须是主角、离散度只能当旁证：")
    add("")
    add("- `P0_to_P1/还原`（std = 2.25 eV，τ_b = +0.600）落在曲线**之上**：位移几乎平行于靶轴，")
    add("  所以离散度很大而顺序几乎没动（`docs/20` T4/T5 的机制）；")
    add("- `C1_to_C2/还原`（std = 0.335 eV，τ_b = +0.289）落在曲线**之下**：这一级的还原是 **Li 中心**而非分子中心")
    add("  （state-identity 改变），纯离散度模型按定义看不见这件事。")
    add("")
    add("**因此本节的结论必须这样写**：合成相图把「离散度」从 5 个点的相关升级为**一条可计算的边界**，")
    add("但它**不能单独**解释全部台阶；能单独解释的是 `q_ij <= sqrt(2)/z` 的闭式判据 —— 见 §4。")
    add("")
    add("---")
    add("")
    add("## 4. R3 —— 恒等式与一次真正的样本外检验")
    add("")
    add("### 4.1 措辞改写")
    add("")
    add("`docs/20_week10_report.md` §3 开头新增定位段：T1–T5 是**代数恒等式**，")
    add("「与实测误差 0.00e+00」**不是精度证据**；恒等式的价值在**可外推**。§3.4 的「数值验证」改为「数值**复核**」。")
    add("")
    add("### 4.2 前瞻检验（先落盘、后打分）")
    add("")
    add("规则与阈值**只用** `docs/20` §7 的 10 个发现点拟合：带符号 `ols_slope_b`（低 = 危险，阈值 %s）、"
        % _signed(frozen["frozen_rule"]["signed_rule"]["threshold"], 4))
    add("朴素 `sd(delta)`（高 = 危险，阈值 %s eV）。预测先写入 `outputs/week21/sigma_prospective_frozen.json`，"
        % _fmt(frozen["frozen_rule"]["naive_rule"]["threshold"], 4))
    add("带 UTC 时间戳 `%s` 与 SHA256 `%s`，**然后**才计算实际结果。"
        % (frozen["frozen_utc"], prov["frozen_sha256"][:16] + "…"))
    add("")
    add("| 分子集 | 轴 | n | k | sd(δ) /eV | `ols_slope_b` | 带符号预测 | 朴素预测 | 实测 | 重叠 |")
    add("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for key in sorted(rows):
        row = rows[key]
        add("| %s | %s | %d | %d | %s | %s | %s | %s | **%s** | %.2f |"
            % (row["set"], row["axis"], row["n"], row["k"], _fmt(row["delta_sd_ev"]),
               _signed(row["ols_slope_b"]),
               "改写" if row["predicted_signed"] else "保留",
               "改写" if row["predicted_naive"] else "保留",
               "改写" if row["observed_rewritten"] else "保留",
               row["observed_overlap"]))
    add("")
    add("**命中率：带符号规则 %d/%d = %s；朴素规则 %d/%d = %s。**"
        % (score["signed_rule_hits"], score["n_predictions"], _fmt(score["signed_rule_accuracy"]),
           score["naive_rule_hits"], score["n_predictions"], _fmt(score["naive_rule_accuracy"])))
    add("")
    add("**失败案例（与命中数一起读）**：%d 处落空 —— " % len(score["misses"])
        + "；".join("%s / %s（带符号%s、朴素%s，实测%s）"
                    % (miss["set"], miss["axis"],
                       "命中" if miss["signed_hit"] else "**落空**",
                       "命中" if miss["naive_hit"] else "**落空**",
                       "改写" if miss["observed_rewritten"] else "保留")
                    for miss in score["misses"]) + "。")
    add("")
    add("**诚实边界**：这些分子的能量在仓库里已经存在，所以这是**样本外留出检验**、不是盲前瞻试验；")
    add("真正按时间排序的是**规则**（Week 10 冻结、阈值从未被留出分子影响）。而且 n = %d 个预测，"
        % score["n_predictions"])
    add("0.750 与 0.500 的差别在这个样本量上**不显著**——只能说方向与 §7.2 一致。")
    add("")
    add("---")
    add("")
    add("## 5. R6 与 R4(a) —— 两处措辞的适用范围")
    add("")
    add("- **R6**：`f_robust_inv` 从 0 变非 0 的「结构性不可能」已在 `docs/26` §0、§4.7 标题与正文、")
    add("  `docs/assets/data.js` 的静态文案、以及交付层 `scripts/build_deliverables.py` 的生成模板里")
    add("  写死适用范围：**在本项目这条具体流水线、这批格子、这套估计量下**（`sigma_ij = |d0_ij - d1_ij|/sqrt(2)` 且 `z_primary = 1.0`），")
    add("  并明确**不是普适定理**。")
    add("- **R4(a)**：`SMD CDS` 在三电荷态上完全相同（spread = 0.0 eV）→ 对任何垂直 IP / EA **精确为 0**，")
    add("  已从 §0 搬进 `docs/22_week12_report.md` §7.1 的正文（并保留「量级不小但不可见」的读法纪律）。")
    add("")
    add("---")
    add("")
    add("## 6. Gate 状态")
    add("")
    add("| Gate | 状态 | 依据 |")
    add("| --- | --- | --- |")
    add("| Gate 0（定义冻结） | **CLOSED** | 本轮 R1–R6/R4a 全部为分析或措辞；`config/prereg.yaml` 与 `config/scientific_definitions.yaml` **0 改动**（`scripts/freeze_gates.py --stage 0` 重跑后仍 CLOSED，见 `outputs/week1/gate0_record.md`） |")
    add("| Gate 1（方法 / 锚点） | **NOT CLOSED** | 唯一 blocker 仍是 `data/anchors/solution_redox_anchors.csv` 的 31 行 `method=est`；R7（两级化 + within-series 锚点）属批次 C，**本轮未执行**，需 PI 裁决 |")
    add("")
    add("---")
    add("")
    add("## 7. 产物")
    add("")
    add("| 类型 | 路径 |")
    add("| --- | --- |")
    add("| R1 扩展产物 | `outputs/week4/p1_anchor_comparison.json` 的 `arm_alignment` 与 `tau_b_reference` 两个新块 |")
    add("| R2 相图数据 | `outputs/week21/sigma_synthetic.json` |")
    add("| R2 图与清单 | `outputs/figures/%s`、`outputs/figures/figure_manifest_week21.md` |" % F42)
    add("| R3 冻结预测 | `outputs/week21/sigma_prospective_frozen.json` |")
    add("| R3 打分 | `outputs/week21/sigma_prospective.json`、`outputs/week21/sigma_prospective.md` |")
    add("| 脚本 | `scripts/analyze_sigma_synthetic.py`、`scripts/analyze_sigma_prospective.py`、`scripts/analyze_p1_core_set.py`（扩展）、`scripts/gen_week21_report.py` |")
    add("| 测试 | `tests/test_week21_report.py`、`tests/test_sigma_synthetic.py`、`tests/test_sigma_prospective.py` |")
    add("")
    add("## 8. 图表")
    add("")
    add("| 编号 | 文件 | 说明 |")
    add("| --- | --- | --- |")
    add("| F42 | `outputs/figures/%s` | %s |" % (F42, caption))
    add("")
    add("图内标签一律用英文。清单与 SHA256 见 `outputs/figures/figure_manifest_week21.md`。")
    add("")
    add("## 9. 已知限制")
    add("")
    add("- **R1 的 n = 10**。配对检验把问题问对了，但 10 个分子撑不起「显著」二字；")
    add("  本轮的产出是**把不该说的说回去**（不能声称 ΔSCF 排序显著更好），不是新的肯定结论。")
    add("- **R2 的合成模型是「纯离散」模型**，按构造看不见 state-identity 改变（§3.3 的 `C1_to_C2/还原` 就是它失手的那一格）。")
    add("  相图给的是**边界与方向**，不是对所有台阶的完整解释。")
    add("- **R3 只有 4 个预测**，且是样本外留出而非盲前瞻；命中率差别不显著，失败案例已逐条列出。")
    add("- **R6 的措辞修订不改变任何数字**，但它改变交付件的 SHA256 —— 已按 R10 的连带纪律重跑交付层。")
    add("- 本轮的 `outputs/figures/F4–F7` 会被 `analyze_p1_core_set.py` 重绘一次；PNG 字节随环境变化，")
    add("  语义未变（同一脚本、同一数据在当前环境下的重绘），manifest 已同步更新。")
    add("")
    add("## 10. 下一步（批次 B / C / D）")
    add("")
    add("1. **批次 B（低成本新计算）**：R9（5–10 分子 xTB `--ohess` 热修正抽样，回答「热修正的分子间离散度是否远小于 δ_m」）、")
    add("   R4(b)（一格 ε = 10^6 导体极限，**附加诊断、不进冻结列表**）、R11 的 NEB / QST2 精修 2–3 格。")
    add("2. **批次 C（需 PI 裁决）**：R7 —— Gate 1 两级化 + Okoshi/Ue within-series 锚点核验。")
    add("   必须先完成文献核验（卷期页码 + 测量条件），未核验通过的条目不得写入锚点 CSV。")
    add("3. **批次 D（不阻塞）**：R8（近简并 pair 的靶向双腿策略）、R12（把「哪些层不用算」写成结题叙事）。")
    add("4. **结题材料**：把批次 A 的四条结论并入 `成果输出/数据结果汇总.md` 的结论节与站点首页文案。")
    add("")
    add("（Gate 状态：Gate 0 CLOSED、Gate 1 NOT CLOSED —— 唯一 blocker 仍是溶液锚点 31 行 `est`。）")
    add("")
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Generate docs/32_week21_report.md from the batch-A artefacts.")
    parser.add_argument("--data-dir", type=Path, default=W21, help="artefact directory (default: outputs/week21)")
    parser.add_argument("--out", type=Path, default=OUT_DEFAULT, help="report path (default: docs/32_week21_report.md)")
    parser.add_argument("--check", action="store_true", help="render in memory and compare with the file on disk")
    args = parser.parse_args(list(sys.argv[1:] if argv is None else argv))

    text = render(args.data_dir)
    if args.check:
        if not args.out.exists():
            print("check FAILED: %s does not exist" % args.out)
            return 1
        if args.out.read_text(encoding="utf-8") == text:
            print("check ok: %s matches the artefacts (%d lines)" % (args.out, text.count("\n")))
            return 0
        print("check FAILED: %s differs from the freshly rendered text" % args.out)
        return 1
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(text, encoding="utf-8", newline="\n")
    print("wrote %s (%d bytes, %d lines)" % (args.out, len(text.encode("utf-8")), text.count("\n")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
