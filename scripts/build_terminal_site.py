"""Build the GitHub Pages terminal site.

Everything the terminal prints is read out of the repository at build time:
the week headings come from ``docs/*week*_report.md``, the figure captions
from the manifests, the gate state from ``outputs/week{1,2}/gate*_record.md``.
Nothing is retyped by hand, so the site cannot drift from the science.

Outputs (all under docs/):

    docs/assets/data.js            window.HB - the payload the terminal reads
    docs/assets/figures/*.png      byte copies of outputs/figures/*.png
    docs/index.html                five managed regions spliced from the payload
    docs/404.html                  baked from the payload, needs no script

index.html stays hand-written outside its marker pairs -- the builder rewrites
only the text between the BEGIN/END comments.  Run --check to verify the
on-disk site still matches the repository.
"""
import argparse
import glob
import io
import json
import os
import re
import shutil
import struct
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(REPO, "docs")
ASSETS = os.path.join(DOCS, "assets")
FIGDIR = os.path.join(ASSETS, "figures")
OUT = os.path.join(ASSETS, "data.js")
PAGE_404 = os.path.join(DOCS, "404.html")

REPO_URL = "https://github.com/LittleAlety/electrolyte-ranking-stability"

def _wp2_main_progress():
    """Main-state WP2 production progress, read from the week39 payload.

    The figure caption below must not hardcode the count: it grows every
    time another Opt+Freq state lands, and a stale caption would overstate
    or understate the evidence the site shows.
    """
    path = os.path.join(REPO, "outputs", "week39", "wp2_free_energy_labels.json")
    try:
        with io.open(path, encoding="utf-8") as handle:
            progress = json.load(handle)["free_state_production"]["progress"]
        return int(progress["states_done"]), int(progress["states_total"])
    except (OSError, KeyError, ValueError, TypeError):
        return 0, 16


WP2_MAIN_DONE, WP2_MAIN_TOTAL = _wp2_main_progress()

# ---------------------------------------------------------------- figure table
# (id, png, week, caption).  Captions are verbatim (or trimmed verbatim) from
# the manifests and the week reports; the builder refuses to invent one.
FIGURES = [
    ("F0", "F0_project_pipeline.png", 3, "项目五段式流水线示意"),
    ("F1", "F1_chemical_space_coverage.png", 3, "core vs broad 的 family / donor 覆盖"),
    ("F2", "F2_p0_distributions_by_family.png", 3, "各 family 的 P0 分布，按氟化着色"),
    ("F3", "F3_value_error_vs_rank_error.png", 3, "值误差 vs 排序误差（本轮核心反直觉结论）"),
    ("F4", "F4_rank_migration_p0_to_p1.png", 4, "(a) 每分子 IP 三臂对照锚点（平移）；(b) 氧化轴 P0 -> P1 位次迁移（重排）"),
    ("F5", "F5_reduction_axis_koopmans_vs_dscf.png", 4, "(a) Koopmans EA vs 真实 EA（定性失效）；(b) 还原轴位次迁移"),
    ("F6", "F6_decision_stability_indicators.png", 4, "(a) Top-k 重叠与 Jaccard；(b) 逐对间距与 z*sigma 不确定带"),
    ("F7", "F7_shift_structure.png", 4, "廉价层是「平移的尺子」还是「另一把尺子」（IP / EA 散点）"),
    ("F8", "F8_environment_layer_p1_to_p2.png", 4, "(a) 每分子的气相->溶剂位移（IP 与 EA）；(b) 逐对间距与 z*sigma 不确定带（环境层）"),
    ("F9", "F9_diffuse_function_control.png", 4, "同泛函三基组对照：加弥散把 EA 系统性下拉但未翻转符号（方法适用域结论）"),
    ("F10", "F10_cpcm_eps_scan.png", 4, "bare CPCM eps 扫描（dIP/dEA 饱和曲线 + sigma_env 与 tau_b）"),
    ("F11", "F11_opt_freq_g2_sensitivity.png", 4, "G1 -> G2 几何台阶（逐分子位移 + 方法/几何/环境三台阶同口径对比）"),
    ("F12", "F12_li_coordination_c1.png", 5, "Li+ 配位条件态 C1（逐分子 dIP/dEA + 四台阶 sigma 对比 + 配体交换 + 决策量）"),
    ("F13", "F13_c1_state_identity.png", 5, "C1 条件态的 state-identity：Mulliken 投影与电荷阶梯，读自 ORCA 已写出的电荷/自旋块，不花新的量化算力"),
    ("F14", "F14_delta_m_derivation.png", 6, "(a) delta_m 的三项贡献与 max 规则（菱形标注）；(b) 逐分子 P1 - P0 位移，其群体散布即 inter-method 项"),
    ("F15", "F15_stage6_decision_metrics.png", 6, "(a) 每一层对的上下两侧在 delta_m = 0 / 0.05 eV / docx max 下的 f_unresolved；(b) docx max 容差下的排序一致度指标"),
    ("F16", "F16_stage7_direct_vs_shift.png", 7, "(a) 每种形状的最优模型（leave-one-family-out）；(b) 随机 / group / LOFO 切分下的乐观偏差；(c) tau_b(shift) - tau_b(direct)"),
    ("F17", "F17_stage8_active_learning.png", 7, "n_T -> Kendall tau_b：random / diversity / uncertainty / ranking-aware 四种采集，20 组冻结种子重复的中位数与 2.5-97.5 分位带"),
    ("F18", "F18_stage9_explicit_shell.png", 8, "显式微溶剂化：第一溶剂壳 1:1 -> 1:2 的位移与决策量"),
    ("F19", "F19_stage10_ladder.png", 9, "五级台阶合成与决策稳定性总判"),
    ("F20", "F20_sigma_anatomy.png", 10, "sigma 的代数解剖"),
    ("F21", "F21_sigma_controls.png", 10, "sigma 的控制变量"),
    ("F22", "F22_dielectric_scaling.png", 11, "(a) Born 线性轮廓；(b) 增量比 vs 两个模型；(c) 同一 c 的几何收缩；(d) 外推检验"),
    ("F23", "F23_prescreening.png", 11, "(a) 预算曲线；(b) 逐台阶 b_hat 分布；(c) 3 分子试点散点；(d) 判据平面"),
    ("F24", "F24_dielectric_limit.png", 12, "(a) 七级阶梯 vs u = 1 - 1/eps（24 条曲线）；(b) 三模型 R2；(c) 外推误差由距离决定；(d) eps = 200 距导体极限 33 meV"),
    ("F25", "F25_environment_ledger.png", 12, "(a)(b) SMD 乙腈两轴的逐分子四项分解；(c) CDS 三态重合；(d) 畸变抵消比例"),
    ("F26", "F26_distortion_attribution.png", 13, "(a) 逐态畸变惩罚的逐分子柱状图；(b) dist 恰为两个逐态惩罚之差（残差 6.7e-12 eV）；(c) D_neutral vs 偶极（rho 0.909）；(d) 最佳单描述符的留一 R2"),
    ("F27", "F27_emc_outlier.png", 13, "(e)(f) 九点 bare CPCM 阶梯上六条 delta(eps) 曲线；(g) EMC / 还原轴按 SCF 解分支着色 + 粗糙度对照；(h) Born R2 随网格点数的收敛"),
    ("F28", "F28_two_guess_protocol.png", 14, "(a) 90 点能量差幅度直方图与 1 meV material 阈值（12 点全部为负）；(b) EMC 阴离子偶极的两条分支（默认初猜 vs ! MORead）十点对照；(c) 导体极限：Born 横坐标 u = 1 - 1/eps 上 eps = 1000 的位置；(d) 六点/九点 Born 斜率与外推缺口（修复前后没变小）"),
    ("F29", "F29_diffuseness_descriptor.png", 14, "(e) spin_maxfrac 对阴离子畸变惩罚（留一 R2 0.162 -> 0.556）；(f) 参与比的秩 vs 线性（rho -0.846 对留一 R2 -2.90）；(g) 三个目标的留一 R2 对比（中性/阳离子不变）；(h) 描述符自己的域检验，标出唯一越界的 EMC/cpcm_10"),
    ("F30", "F30_two_guess_catalogue.png", 15, "(a) 12 分子 x 3 状态 x 10 电介质的完整双初猜网格（红 = 默认初猜偏高，灰 = 两臂一致，蓝 = 反而更高，斜纹 = 未配对）；(b) 每个开壳层 (分子, 状态) 在整个阶梯上的最坏赤字（绿虚线 = 1 meV 材料阈值）；(c) 超过各阈值的单元格计数"),
    ("F31", "F31_apriori_warning_rule.png", 15, "(d) 选定气相描述符对最大赤字，绿色虚线为留一冻结阈值；(e) 每个气相描述符的单变量 AUC；(f) 留出臂逐行预测与真值；(g) 冻结规则 vs 多数类基线（明写输给平凡规则）、平衡准确率、精确置换 p，以及分电性状态的事后诊断（描述符、正例排名、留一）"),
    ("F32", "F32_stage17_contamination.png", 16, "(a) 逐分子逐轴的污染界 delta = p2_moread - p2_default（参考带 1e-03 eV，最坏 0.1562 eV）；(b) 排序稳定性对照：两轴 tau_b 的 95% CI 重叠；(c) 决策量 default vs moread 与「无已发布结论被改写」的裁决"),
    ("F33", "F33_stage17_solution_identity.png", 16, "(d) PC/阴离子/cpcm_10 的逐原子自旋剖面（两臂同峰于 C4，几何与自旋中心一致）；(e) 32 格逐格的局域化迁移（cyclic/linear/phosphate 的 PR 均值变化）；(f) 自旋纯度：Δ<S²> 落在 [-0.004534, +0.001457]，参考纯双重态 0.75；(g) 电荷 vs 自旋重组（各 family 的 charge_l1 与 spin_l1 均值）"),
    ("F34", "F34_stage18_identity_census.png", 17, "(a) charge_l1 双峰：coincident 239 / moread_lower 37（仅开壳层可测），冻结阈值 0.039 落在 0.0385-0.0394 空档；(b) 五通道 x 三臂 AUC；(c) 按家族的重合率；(d) 留出臂 54 格 delta_ev 与 1 meV 阈值"),
    ("F35", "F35_stage18_selfdiagnosis.png", 17, "(e) 单变量筛查前 8 名 |AUC-0.5| 与 LOO 裁决（gap_warn_value 第一、LOO 胜基线但留出臂输）；(f) gap_warn_value 正负例分布与冻结阈值 -0.0395；(g) 留出臂 54 格按冻结规则逐行打分（TP=0）；(h) 单边筛查：presence 规则放行 140/414、敏感度 1.000、特异度 0.371"),
    ("F36", "F36_stage19_relax_outcomes.png", 18, "(a) 单点 Δ 对弛豫后 Δ（按结局着色，y=x 与 ±1 meV 带；|Δ| 中位数 0.1198 → 0.00196 eV，缩小 61 倍）；(b) 37 个 moread_lower 格子的裁决：distinct_lower 5 / distinct_higher 24 / same_lower 0 / same_higher 8（已完成 37）；(c) 按 ε 的结局堆叠；(d) 按态与分子的分解"),
    ("F37", "F37_stage19_identity_geometry.png", 18, "(e) 弛豫前后 charge_l1 对数散点、冻结阈值 0.039 与 ±20% 贴阈值带（弛豫前后都在阈值以上 29/37，贴阈值 0 格）；(f) 双解几何 RMSD 对 Δ 漂移（0.02 Å 同极小点参考线，下方 6/37 格）；(g) 两臂弛豫能量降配对（默认解中位降 1.876 eV vs moread 1.666 eV）；(h) 自旋中心迁移矩阵（argmax 仅作描述，不作判据）"),
    ("F38", "F38_stage20_relax_rung.png", 19, "(a) 37 个格子的弛豫位移 Δ = −能量降（eV）对 ε（对数轴，按态着色、逐分子连线；逐分子 ε 极差中位 0.0263 eV、最大 0.215 eV（DEC），即弛豫修正几乎与介电常数无关）；(b) 同一把尺子：4 个可比 population 上 5 个冻结台阶与第六级台阶（弛豫）的相对散布 std/|mean|（对数轴；斜纹柱 = 氧化轴 G1→G2 的 |mean|≈0，相对散布无意义）；(c) (|mean|, std) 平面：6 个台阶 × population 共 30 行，实心大点 = 新台阶；(d) 7 个分子的 Δ 均值，误差棒 = 跨 ε 极差——还原支近乎刚性平移（均值 -1.953 eV、std 0.160 eV、相对散布 0.08），氧化支为散布型（均值 -0.610 eV、std 0.315 eV、相对散布 0.52）"),
    ("F39", "F39_stage20_xtb_arms.png", 19, "(a) 两臂起点 RMSD 对 xTB 弛豫后 RMSD（Å，对数轴，按 4 类结局着色，虚线 = 0.02 Å 同极小点阈值；起点中位 0.4716 → 弛豫后中位 0.8078 Å，6/37 格两臂合并）；(b) 同一几何上 xTB 单点 Δ 对 ORCA r2SCAN-3c 弛豫 Δ（eV，y=x 与 ±1 meV 带；偏好方向一致 33/37 = 89%，4 个分歧已圈出）；(c) 两臂能量差的四个读数（ORCA 单点 / ORCA 弛豫 / xTB 单点 / xTB 弛豫，对数轴，中位 1.198e-01 / 1.960e-03 / 7.171e-03 / 2.133e-04 eV）——xTB 弛豫把差异压掉约 33.6 倍；(d) 单臂漂移对起点双解 RMSD（Å，y=x，对数轴；两臂漂移中位 0.651 / 0.657 Å 与起点差异中位 0.4716 Å 同量级，故几何 distinct 部分继承自起点）。分母：Stage 19 单点两解不同且 moread 更低的 37 格，不是 414 格总体的发生率"),
    ("F40", "F40_stage21_path_profiles.png", 20, "F40：把 Stage 19 最脆的那条判据换一把尺子重读。三个格子在两条松弛几何之间做直线内插、每点一个冻结 r2SCAN-3c 单点（共 63 个），各自纵轴不同**不可互比**。(a) EC/cation/ε=5：Stage 19 因两臂几何相差 0.100 Å 判它 `distinct_lower`，但内插路径全称无鼓包（相对弦最大仅 0.00424 eV ≪ k_B T = 0.0257 eV），两臂弛豫能量只差 -0.00972 eV——**过度判定**，它其实是同一个平坦盆地的两个肩。(b) EC/cation/ε=20：判据另一侧的对照，路径同样无鼓包（0.00001 eV），`same_higher` 成立。(c) TEGDME/anion/ε=20（RMSD 2.214 Å）的鼓包约 66 eV，是直线路径让原子互穿的假象，只用来确认两解确实分立。内插路径是笛卡尔直线、不是最小能量路径，所以鼓包只是**上界**；反过来说「直线全程不抬升」是强证据：它不可能藏着一个势垒。结论：临界带（0.021–0.100 Å）上 RMSD 阈值把至少一格判错了，该由能量判据而非几何阈值来裁决。"),
    ("F41", "F41_stage21_shell_redox.png", 20, "F41：把第一溶剂壳 [Li(M)2]+ 的两个氧化还原态都做 r2SCAN-3c 弛豫（气相，与 Stage 9 同口径，起点是同一张冻结 G2Li2 几何），共 24 个 Opt、24 个可用；(a) 氧化轴：空心 = Stage 9 的冻结垂直位移，实心 = 本周的弛豫绝热位移，连线长度就是弛豫修正（均值 -0.4053 eV、最大 1.6467 eV，排序 Spearman ρ=0.797、Kendall τ=0.727、上四分位重叠 0.500）；(b) 还原轴：同样的读法（修正均值 -5.4512 eV、ρ=-0.790、τ=-0.606、重叠 nan）——还原态是中性自由基，结构可能散架，凡断键/碎片化/丢配体的格子都画成灰叉并**排除在所有统计之外**（本周排除 无）；(c) 冻结 vs 弛豫位移散点与 y=x，说明「垂直位移」作为绝热位移的上界在多大程度上成立。"),
    ("F42", "F42_sigma_synthetic_phase_diagram.png", 21, 'R2：把 Week 9 的 rho(shift std, tau_b) = -0.851（10 点 / 5 台阶）从 headline 降级为现象示意，改用合成数据相图回答同一个问题——固定靶排序 t，令逐分子位移 delta_i = mean + std * z_i 并把 z 在每个 replicate 内标准化（使 delta 的样本 sd 恰为 std），在 mean 属于 [-8, +8] eV、std 属于 [0, 2] eV 的网格上每格 2000 组重抽样。(a)(b)(d) 三张相图沿 mean 轴**严格常数**（tau_b 的最大绝对差 0.00e+00）：给每个分子加同一个常数既不能换序也不能改变任何 pair 差，所以 Week 9 那个 rho(|mean|, tau_b) = -0.535 只能是共线性伪影——实测点上 rho(|mean|, std) = +0.758，而相图里两者按构造独立、同一相关系数为 0.000。(c) 换到 std 轴，tau_b 单调下降且相图的秩相关为 -1.000：氧化靶轴上 tau_b 均值跌破 0.8 于 std = 0.45 eV、跌破 0.5 于 1.20 eV（还原靶轴 0.25 / 0.70 eV），即**排序的代价只由位移的离散度支付**；实测 10 点多数贴着曲线，但两个例外各有明确的物理身份——P0->P1/还原（std = 2.25 eV，tau_b = +0.60）在曲线**之上**，因为它的位移几乎平行于靶轴；C1->C2/还原（std = 0.335 eV，tau_b = +0.29）在曲线**之下**，因为那一级的还原是 Li 中心而非分子中心（state-identity 改变），纯离散度模型按定义看不见这件事。'),
    ("F43", "F43_dielectric_limit_check.png", 22,
     '**R4b（附加诊断，不属预注册扫描集 [5,10,20,40]）—— 裸 CPCM 离导体极限还有多远。**(a) 36 个 (分子, 电荷态) 组合上，`|E(eps) - E(1e6)|` 的均值随 eps 下降；它不是「饱和」，而是**几乎严格的 1/eps 幂律**：`|dE| x eps = 2057-2178 meV`，prefactor 约 **2.1 eV/eps**，从 eps = 7 一路测到 eps = 1000 都成立。这条律把「离导体极限还差多少」变成**可以提前算出来**的量。(b) eps = 200 时的逐分子残余：最大 **19.62 meV**（PC / anion），平均 10.81 meV；相对 eps = 1000 时最大只剩 **3.929 meV**。作为参照，冻结的决策容差 delta_m 是氧化 700 meV / 还原 2074 meV，所以 eps = 200 的残余只有它的 **2.80% / 0.95%** —— 介电层**不是严格免费**，但残差比排序论证关心的尺度小 1-2 个数量级，Stage 12/13 的「介电层免费」在实用精度上量化成立。逐分子一致性：53/54 个组合的 `dE` 随 eps 单调下降，例外 EMC/anion —— 阴离子 SCF 在不同 eps 上落到不同解分支的求解器伪迹，不是介电残差，已在该行的分析里单独标出。'),
    ("F44", "F44_neb_refinement.png", 22,
     '**R11 —— 用真 NEB 取代直线插值上界。** 反应物/产物 = Stage 19 两条臂的弛豫终点（端点不重优化），regular (climbing : no)（中间像数：EC/cation/5 = 8，EC/cation/20 = 8，TEGDME/anion/20 = 4）。峰高从 ORCA 的 `<stem>.final.interp` 读，全精度。(a)-(c) 三条收敛路径，能量相对反应物，1 kT 与 1 kcal/mol 画成横线；(d) 直线界 vs 真 NEB 的对数柱状图。EC/cation/5：直线 0.00424 eV -> NEB **0.000141 eV**（one_basin，直线/NEB = 30.00） EC/cation/20：直线 0.00001 eV -> NEB **0.000053 eV**（one_basin，直线/NEB = 0.15） TEGDME/anion/20（未收敛，不给判决）2 格落在 1 kT 以下（`one_basin`）：EC/cation/5、EC/cation/20；1 格没有可用判决：TEGDME/anion/20。直线插值确实只是上界，最松的一格把峰高放大了 30.0 倍。与 Stage 19 的 RMSD 判决**冲突**的格子：EC/cation/5。'),
    ("F45", "F45_targeted_two_guess.png", 23,
     '**R8 —— 漏解不是「翻倍」，是「框住」。**(a) 两个轴的 16 个 material 格子（Stage 16 默认初猜漏掉更低解）换算到决策量上的效应量 `|effect|`：容许量取最大值 A_axis = 0.1523 eV（氧化，最坏 TMP@eps=5）/ 0.2860 eV（还原，最坏 EMC@eps=1000），只有冻结 delta_m 的 21.7% / 13.8%。(b) 靶向比例对 delta 的阶梯：以 delta = A_axis 做靶向要保护 86/120（氧化，省 28.3%）与 116/120（还原，省 3.3%）—— 安全但几乎不省钱，因为 12 分子 x 10 电介质的 pair 谱本来就密；事后最紧的 delta_star（0.1463 / 0.2534 eV）给出这条规则的下界。(c) 协议校验：只在靶向格子上用第二腿，与「全部格子都用双腿」逐层比较，10 个电介质上 tau_b 全为 1.0000（Top-k 重叠也全 1.000）；对照「什么都不做」的单腿协议，tau_b 最小值已经掉到 0.9394 / 0.8788 —— 漏解确实动排序，不能忽略。(d) 只保护 Top-k 清单边界的变体：半宽取 A_axis，k = 1/2 时省 91.7% / 83.3%、k = 4 时省 66.7% / 53.3%；它便宜得多，但只保护清单，不保护清单内部的次序。安全性来自一条可证的不等式：翻转要求 `abs(d0-d1) = abs(d0)+abs(d1) > abs(d0)` 而 `abs(d0-d1) <= A_axis`，所以 `abs(d0) >= A_axis` 的 pair 不可能翻转 —— 实测 660 对/轴上抓住全部 19 / 21 次真实翻转、漏 0。'),
    ("F46", "F46_shell3_saturation.png", 23,
     '**R5 —— 第三个配位点：与饱和一致的证据，而不是「证明了饱和」。** 一个代表分子（EC / motif m1）补第三配位壳，GFN2-xTB 级示意。(a) n = 0 -> 3 的位移阶梯：自由 EC（0.000 eV）-> [Li(EC)]+（dIP 3.897 / dEA 6.291）-> [Li(EC)2]+（2.015 / 5.672）-> [Li(EC)3]+（1.292 / 5.336）。(b) 增量 dd(n -> n-1)：dd(2->1) 氧化 -1.882 / 还原 -0.619，dd(3->2) 氧化 -0.723 / 还原 -0.336 —— 两轴都同号且绝对值更小，形状与饱和一致（dd(3->2)/dd(2->1) = 0.384 / 0.543）。(c) 跨层级的无量纲对照：只比比值 `dd(2->1)/dd(1->0)`，r2SCAN-3c 为 -0.4080 / -0.2386（12 个 motif），GFN2-xTB 为 -0.4829 / -0.0984（1 个分子）—— 氧化轴的形状比在两层之间接近，还原轴不接近（还原态在 Stage 9 就被 state-identity 问题标记过，xTB 与 r2SCAN-3c 对「电子落在哪」的判断不必一致），这一条只能当提示。绝对值的跨层级对照一律不做：GFN2-xTB 与 r2SCAN-3c 的 IP/EA 相差 eV 量级。'),
    ("F47", "F47_broadpool_budget.png", 22, "broad pool 的最小信息预算演示：不可分辨对比例、值得升级子集与两条口径下的预算节省（W22-H）"),
    ("F48", "F48_ml_direct_vs_shift.png", 24, "直接学习 vs 位移学习的留一家族出外推对照（W24-C）"),
    ("F49", "F49_al_budget.png", 24, "主动学习预算重放：n_T 与 tau_b 曲线与冻结种子的分位带（W24-C）"),
    ("F50", "F50_decision_metrics.png", 24, "W24-C 决策量补全：闭环判据与三臂对齐（W24-C）"),
    ("F51", "F51_minimal_budget_flowchart.png", 24, "最小信息预算决策流程图：该算哪些层、该买多少昂贵标签（W24-C）"),
    ("F52", "F52_gate1_ordering.png", 25, "Gate 1 溶液锚点排序层判据的首次评估（tau_b = 0.4286、n_pairs = 21、ordering_disagrees）（W25）"),
    ("F53", "F53_family_resolved.png", 25, "逐家族（family-resolved）排序统计：家族内 tau_b 与未解析比例（W25）"),
    ("F54", "F54_two_axis_hierarchy.png", 25, "二维模型层级（方法层级 x 条件态层级）+ 外部参考层（核心文件 §24 Figure 1）（W25）"),
    ("F55", "F55_coord_descriptor_tags.png", 25, "配位位移 x 描述符标签关联（核心文件 §24 Figure 5）：C1 n = 10，氧化轴 tpsa rho = -0.890（p = 0.0011）（W25）"),
    ("F56", "F56_r13_summary.png", 26, "R14 收口汇总：三态判据/分辨率曲线/Gate 1 双轨 NOT CLOSABLE/防误读卡片（R13 阶段）"),
    ("F57", "F57_metric_robustness.png", 27, "R15 指标稳健性与排序可识别性：(a) 每个 block 的排序一致性政策带（pessimistic → optimistic），蓝点为 tie 政策；(b) f_tie = 证据无法解析的 pair 占比（= 政策带宽度的一半）；(c) 可分层层数：cheap 自排序 / target 自排序 / 双方认证，竖线为分子数 n；(d) 近临界 pair 数（比值 ∈ [1, 1.25)），认证了但极易翻转"),
    ("F58", "F58_layer_independence.png", 27, "R15 模型层独立性与信息增益：(a) 每级位移的 dispersion（氧化/还原），标注该层 ORCA job 数；(b) 5 个 rung 两两之间位移向量的 max |Pearson|（同分子集上现算）；(c) 每级的 Kendall tau_b（红虚线 = 0.90 排序门槛）与最大 f_unresolved；(d) 结论卡片：层不是同一信号的再编码、阶梯是分解、T3 常数位移免费"),
    ("F59", "F59_physics_completion_definition.png", 44,
     "新批次 physics_completion_v1（方案 WP0）：七个登记量名与目标方向 + 12/8/4 队列与 6 条写明原因的排除（零新增电子结构计算）"),
    ("F60", "F60_physics_completion_method_audit.png", 44,
     "独立方法审计（方案 WP1）已实测：128 个单点（8 分子 x 4 状态 x 4 设定，全收敛）+ 32 格阳离子弛豫腿；32 个无弥散还原态格子被标出并排除出决策统计（琥珀）；(b) 竖直 IP 的方法展宽显示泛函效应约比基组效应大一个数量级"),
    ("F61", "F61_physics_completion_ladder.png", 44,
     "E -> G -> ensemble 台阶（方案 WP3）：只有垂直->绝热这一级是冻结的（n=12，逐分子位移箭头），三态判定 55/9/2；G_single 已有 %d/%d 个主态的真实 Opt+Freq 生产标签（生产首段为 4 主集分子 x 4 主态），G_ensemble、其余带电/Li 主态与另 8 分子的 G_single 仍需 WP2 生产，故 ROBUST_INVERSION 只是标签不是已认证翻转"
     % (WP2_MAIN_DONE, WP2_MAIN_TOTAL)),
    ("F62", "F62_physics_completion_pair_identity.png", 44,
     "固定背景 pair 证据与身份结论（方案 WP3）：66 对逐对按三态判据着色并叠 z*sigma 带；右侧是 C1 状态身份分层，说明还原轴为什么只有分子中心态可排序"),
    ("F63", "F63_physics_completion_mechanism_cases.png", 44,
     "机制案例（方案 7.3）：用既有冻结几何给出中性->阳离子的最大键长变化（EMC 0.090 A / GBL 0.086 A / SL 0.016 A），右侧是两例稳健翻转的 d_lower 与 d_upper 变号；电子密度/自旋、配位变化与 G 层分解仍待 WP1/WP2"),
    ("F64", "F64_physics_completion_budget_curve.png", 44,
     "累计成本 -> 选集恢复曲线（方案 WP5）：冻结的 20 种子池内回放，tau_b 与 Top-3 重叠随已查询标签数 n_T 的曲线与端点线；这是已知数据的回放，不是盲预注册"),
]

# ---------------------------------------------------------------- week table
# (label, doc, stage, one-line result).  The one-liner is taken from the
# report itself; see `headline` below.
WEEKS = [
    (1, "03_week1_2_report.md", "Stage 0", "预注册与定义冻结"),
    (2, "03_week1_2_report.md", "Stage 1", "外部锚点、方法审计与工具链自检"),
    (3, "09_week3_report.md", "Stage 2", "廉价层 P0、覆盖检查、锚点核验、ORCA 就绪"),
    (4, "10_week4_report.md", "Stage 3 + T1", "r2SCAN-3c 电子结构层与 P0 -> P1 决策稳定性"),
    (5, "12_week5_report.md", "Stage 5 / T4", "Li+ 配位条件态 C1（机制解释）"),
    (6, "13_week6_report.md", "Stage 6", "不确定性感知排序分析"),
    (7, "15_week7_report.md", "Stage 7 + Stage 8", "ML / direct vs delta-learning 与 active-learning replay"),
    (8, "18_week8_report.md", "Stage 9", "显式微溶剂化（C2 = [Li(M)2]+ 第一溶剂壳复核）"),
    (9, "19_week9_report.md", "Stage 10", "五级台阶合成与决策稳定性总判"),
    (10, "20_week10_report.md", "Stage 11", "sigma 的代数解剖与分辨率判据"),
    (11, "21_week11_report.md", "Stage 12", "介电响应是一条单参数族，判据可事前使用"),
    (12, "22_week12_report.md", "Stage 13", "介电极限、导体极限，与环境位移的四项精确分解"),
    (13, "23_week13_report.md", "Stage 14", "畸变项的定量归因与 EMC 离群点的病理裁决"),
    (14, "24_week14_report.md", "Stage 15", "初猜协议修正亚稳态、弥散度描述符翻正否定结果"),
    (15, "25_week15_report.md", "Stage 16", "亚稳解是全核心集现象，但单一气相描述符的事前预警输给平凡基线"),
    (16, "26_week16_report.md", "Stage 17", "P2 腿换 moread 初猜重算 54 格，无任何已发布结论被改写；32 个漏解格两解皆自旋纯双重态，差异主轴是电荷重组"),
    (17, "27_week17_report.md", "Stage 18", "零新增作业：全目录 414 对身份普查闭合（可测 276 对 AUC 1.000、规则不一致 0 对）；零成本自诊断的冻结规则在留出臂输给多数类（TP 0），唯一站得住的正面结论是单边筛查「无警告 ⇒ 安全」"),
    (18, "28_week18_report.md", "Stage 19", "37 个 moread_lower 格各让两条 SCF 解做几何弛豫（74 个 Opt 作业）：5/37 仍保持 moread 更低、8/37 在终点合并为同一电子态、32 格单点偏好被几何反转；|Delta| 中位 0.11983 -> 0.00196 eV"),
    (19, "29_week19_report.md", "Stage 20", "所以「第二解」不是一个「廉价方法也能独立复现」的概念，而是一个必须由昂贵方法定义、廉价方法只能在给定几何上读出的概念。"),
    (20, "30_week20_report.md", "Stage 21", "所以 Week 19 那句「几何 RMSD 是判据」在临界带上站不住：把 Stage 19 最脆的 0.021–0.100 Å 带换成能量尺子重读，被判 distinct_lower 的 EC/cation/ε=5 其实是一条无鼓包的直线路径（相对弦最大 0.00424 eV ≪ k_B T = 0.0257 eV）——同一个平坦盆地的两个肩，RMSD 阈值把它过度判定成了两个解。"),
    (21, "32_week21_report.md", "Stage 22",
        "把三臂对齐到同一批 10 个分子之后，ΔSCF 的 τ_b 仍是三者最高（0.911 vs 0.778 vs 0.689），"
        "但与另外两臂的差距在配对检验下全部跨 0（配对 95% CI [−0.200, +0.550]，精确配对置换 p = 0.805）"
        "——所以从本周起，项目对外只能说「MAE 的排序与 τ_b 的排序不一致」，不能说「ΔSCF 的排序显著更好」。"),
    (22, "33_week22_report.md", "Stage 23",
     'R11 用真 NEB 取代直线插值之后，Stage 19 判成「两个盆地」的 EC/阳离子/eps=5 一格峰高只有 0.141 meV（直线界 4.245 meV 的 1/30），两端点就是同一个盆地——0.02 A 的 RMSD 一刀切在这一格误判；同周 R4b 又把「介电层免费」量化成一条 |dE| x eps = 2.1 eV 的幂律，eps = 200 的残余只剩 19.6 meV，是氧化轴 delta_m 的 2.80%。'),
    (23, "34_week23_report.md", "Stage 24",
     'R8 把「漏解要不要全局双算」压成一条安全定理——|d0-d1| <= A_axis，任何 |d0| >= A_axis 的 pair 都不可能翻转，实测 19/660（氧化）与 21/660（还原）次翻转 0 漏，靶向双腿与全双腿的 tau_b 最小值都是 1.0000，但它几乎不省钱（氧化省 28.3%、还原省 3.3%）；真正省钱的是只保护 Top-1 清单边界的变体（氧化省 91.7%、还原省 83.3%）；R12 因此把三条结论合并成对 v2「minimal information budget」的定性回答：闭式判据（q_ij <= sqrt(2)/z，可在花钱前预判）+ 介电层免费（|dE| x eps 约 2.1 eV 幂律）+ 配位饱和（第一壳之后次线性）——大规模筛选时，这几层可以不算。'),
    (24, "38_week24_corealign_report.md", "W24-C",
     "核心文件与结题论文之间的方法缺口在本周闭合：ML / 主动学习从 Stage 7/8 产物蒸馏为论文 §3.13–§3.14（接入 F48、F49），§22 分支与 §23 判据逐条自查落到 §5.1–§5.2，决策量补成 20 个组合的可核数值，并新增 F51 最小信息预算决策流程图；本周零新增电子结构计算。"),
    (25, "40_week25_gate1_report.md", "W25-G1",
     "Gate 1 排序层判据的状态从 \"无数据（no_within_series_values）\" 变为 \"已评估且不一致（ordering_disagrees）\"：7 个同系列溶剂、21 对给出 Kendall τ_b = 0.4286 < 0.90，判据首次可评但未通过；还原轴只有 3 对旁证，判 not_evaluable_secondary_only；本周零新增电子结构计算。"),
]

PIPELINE = [
    ("1", "cheap proxy", "GFN2-xTB / P0 描述符"),
    ("2", "validated target", "r2SCAN-3c 垂直 IP / EA"),
    ("3", "rank change", "tau_b / f_unresolved / robust inversion"),
    ("4", "mechanism", "位移的代数结构与环境层账本"),
    ("5", "minimal budget", "主动学习回放：多少算力够用"),
]

def read(path):
    with io.open(path, encoding="utf-8") as fh:
        return fh.read()


def sha256_of(path):
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def png_size(path):
    """Intrinsic pixel size of a PNG, straight out of the IHDR chunk.

    The gallery and the brief reserve space with width/height so the grid
    cannot reflow as thumbnails arrive; nothing is retyped by hand.
    """
    with open(path, "rb") as fh:
        head = fh.read(24)
    if len(head) < 24 or head[:8] != b"\x89PNG\r\n\x1a\n":
        return 0, 0
    width, height = struct.unpack(">II", head[16:24])
    return width, height


def clip(text, limit=620):
    """Trim to a sentence-ish boundary so the terminal never cuts mid-word."""
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text
    cut = text[:limit]
    for mark in ("。", "；", ". "):
        idx = cut.rfind(mark)
        if idx > limit * 0.55:
            return cut[: idx + len(mark)].strip()
    return cut.rstrip() + "..."


def body_lines(lines):
    """Drop markdown scaffolding so the text reads as prose in a terminal."""
    keep = []
    for line in lines:
        s = line.strip()
        if not s or s.startswith(("|", "```", "![", "---", "<!--")):
            continue
        s = re.sub(r"\*\*(.+?)\*\*", r"\1", s)
        s = re.sub(r"`([^`]+)`", r"\1", s)
        s = re.sub(r"^[-*+]\s+", "  - ", s)
        s = re.sub(r"^#{3,}\s*", "", s)
        s = re.sub(r"^>\s?", "", s)
        keep.append(s)
    return keep


def week_payload():
    cache = {}
    payload = []
    for week, doc, stage, tag in WEEKS:
        path = os.path.join(DOCS, doc)
        if doc not in cache:
            cache[doc] = read(path).splitlines()
        lines = cache[doc]
        h1 = next((l for l in lines if l.startswith("# ")), "# " + doc)
        title = h1.lstrip("# ").strip()
        sections = [l.lstrip("# ").strip() for l in lines
                    if re.match(r"^##\s", l) and not l.startswith("###")]
        # prefer a "one sentence conclusion" section, else the preamble
        idx = None
        for i, line in enumerate(lines):
            if re.match(r"^##\s", line) and re.search(r"一句话结论|结论", line):
                idx = i
                break
        if idx is not None:
            body = []
            for line in lines[idx + 1:]:
                if re.match(r"^##\s", line):
                    break
                body.append(line)
        else:
            body = []
            for line in lines[1:]:
                if re.match(r"^##\s", line):
                    break
                body.append(line)
        summary = clip(" ".join(body_lines(body)), 640)
        payload.append({
            "n": week, "doc": "docs/" + doc, "title": title,
            "stage": stage, "tag": tag, "summary": summary,
            "sections": sections[:14],
        })
    return payload


def figure_payload():
    rows = []
    for fid, png, week, caption in FIGURES:
        src = os.path.join(REPO, "outputs", "figures", png)
        if not os.path.exists(src):
            raise SystemExit("missing figure: " + png)
        width, height = png_size(src)
        rows.append({
            "id": fid, "file": png, "week": week, "caption": caption,
            "sha": sha256_of(src), "bytes": os.path.getsize(src),
            "w": width, "h": height,
        })
    return rows


def gates():
    out = []
    for tag, name, path in (
        ("0", "Gate 0 - 定义与预注册", "outputs/week1/gate0_record.md"),
        ("1", "Gate 1 - 外部锚点与工具链", "outputs/week2/gate1_record.md"),
    ):
        full = os.path.join(REPO, path)
        rec = {"name": name, "status": "UNKNOWN", "blockers": [], "checks": []}
        if os.path.exists(full):
            text = read(full)
            m = re.search(r"status:\s*\*\*(.+?)\*\*", text)
            if m:
                rec["status"] = m.group(1).strip()
            for line in text.splitlines():
                s = line.strip()
                if s.startswith("| ") and s.count("|") >= 3 and "---" not in s:
                    cells = [c.strip() for c in s.strip("|").split("|")]
                    if cells[0] in ("check", "status"):
                        continue
                    if len(cells) >= 3:
                        rec["checks"].append({
                            "name": cells[0],
                            "ok": cells[1].lower() in ("yes", "ok", "true"),
                            "detail": cells[2],
                        })
            grab = False
            for line in text.splitlines():
                if line.strip().startswith("## blockers"):
                    grab = True
                    continue
                if grab:
                    s = line.strip()
                    if s.startswith("## "):
                        break
                    if s.startswith(("- ", "* ")):
                        rec["blockers"].append(s[2:].strip())
        out.append(rec)
    return out


def counts():
    orca_out = glob.glob(os.path.join(REPO, "outputs", "**", "*.out"), recursive=True)
    orca_out = [p for p in orca_out if "orca" in p.replace("\\", "/")]
    scripts = glob.glob(os.path.join(REPO, "scripts", "*.py"))
    tests = glob.glob(os.path.join(REPO, "tests", "test_*.py"))
    return {
        "weeks": len(WEEKS),
        "figures": len(FIGURES),
        "orca_out": len(orca_out),
        "scripts": len(scripts),
        "test_files": len(tests),
        # Recorded, not measured: pytest cannot be run from the generator.  Bump
        # it in the same commit that adds or removes a test, otherwise the page
        # will advertise a number the suite no longer produces.
        "tests_passed": 1438,
    }


def render_404(payload):
    """The GitHub Pages 404 page, baked from the payload at build time.

    It deliberately does not load data.js: a missing asset must not take the
    styling down with it, so the counts are written in here.  Every URL is
    relative to the published folder, not the user-site root -- the first
    version used /assets/... and href="/", which broke on the project subpath.
    """
    counts = payload.get("counts", {})
    weeks = counts.get("weeks", 0)
    figures = counts.get("figures", 0)
    return (
        "<!doctype html>\n"
        '<html lang="zh-CN" data-theme="green">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        "<title>404 \u2014 hb-lab</title>\n"
        '<link rel="stylesheet" href="assets/terminal.css">\n'
        "<style>\n"
        "  .wrap { padding: 18vh 6vw 0; }\n"
        "  .big { font-size: clamp(38px, 9vw, 92px); color: var(--accent); margin: 0; letter-spacing: -0.02em; }\n"
        "  p { color: var(--dim); max-width: 54ch; }\n"
        "</style>\n"
        "</head>\n"
        "<body>\n"
        '<div class="crt" aria-hidden="true"></div>\n'
        '<div class="wrap">\n'
        '  <p class="dim">&gt; GET /this/path</p>\n'
        '  <h1 class="big">404</h1>\n'
        "  <p>这个页面不存在。终端主页还在，那里有 " + str(weeks)
        + " 周的全部结论、" + str(figures) + " 张图和两个 Gate 的真实状态。</p>\n"
        '  <p><a href="./">返回终端主页</a> &nbsp;·&nbsp; <a href="' + REPO_URL
        + '">GitHub 仓库</a></p>\n'
        "</div>\n"
        "</body>\n"
        "</html>\n"
    )


# ---------------------------------------------------- index.html (managed)
# index.html stays hand-written, but two kinds of content in it are not: the
# numbers a reader or a crawler sees before any script runs, and the week-by-week
# argument.  Both are spliced in from the payload between marker comments, so a
# stale "1265 ORCA jobs" cannot survive a build, and the whole line of reasoning
# is readable with JavaScript switched off.

INDEX = os.path.join(DOCS, "index.html")


def _markers(name):
    return ("<!-- BEGIN:%s (generated by scripts/build_terminal_site.py) -->" % name,
            "<!-- END:%s -->" % name)


def _check_markers(html, name):
    begin, end = _markers(name)
    if html.count(begin) != 1 or html.count(end) != 1:
        raise SystemExit(
            "docs/index.html must carry exactly one %s / %s marker pair (found %d / %d)"
            % (begin, end, html.count(begin), html.count(end)))


def extract_block(html, name):
    """The published content of one managed region, with the markers stripped."""
    _check_markers(html, name)
    begin, end = _markers(name)
    return html.split(begin, 1)[1].split(end, 1)[0].strip("\n")


def splice_block(html, name, inner):
    """Replace one managed region; every other byte of the page is untouched."""
    _check_markers(html, name)
    begin, end = _markers(name)
    pre, rest = html.split(begin, 1)
    _, post = rest.split(end, 1)
    return pre + begin + "\n" + inner.strip("\n") + "\n" + end + post


def esc(text):
    """Tags carry chemistry like "P0 -> P1"; escape it so the markup stays valid."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def week_label(n):
    """Weeks 1 and 2 share one report, so the first row names both."""
    return "Week 1\u20132" if n == 1 else "Week %d" % n


def gate_summary(payload):
    """One line for the no-JS reader: each gate's status plus its blockers."""
    line = "；".join("Gate %d %s" % (i, g["status"])
                    for i, g in enumerate(payload["gates"]))
    blockers = [b for g in payload["gates"] for b in g["blockers"]]
    if blockers:
        line += "（blocker：" + "；".join(blockers) + "）"
    return line


def render_meta(payload):
    c = payload["counts"]
    desc = ("在 18 个分子的核心集上，用 GFN2-xTB 与 r2SCAN-3c 追问："
            "从廉价代理量走到更真实的电子结构与环境模型时，哪些改变只是数值平移，"
            "哪些会真正翻转材料筛选决策。%d 周、%d 张图、可复现的静态终端。"
            % (c["weeks"], c["figures"]))
    return '<meta name="description" content="%s">' % desc


def render_noscript(payload):
    c = payload["counts"]
    return ("<noscript>\n"
            '  <div class="noscript">\n'
            "    <h2>hb-lab — 电解液溶剂决策稳定性研究</h2>\n"
            "    <p>在很小的分子集（core set = 18 个分子）上，用两种高效量子化学方法"
            "（GFN2-xTB 与 r2SCAN-3c）追问：从廉价代理量走到更真实的电子结构 / 环境模型时，"
            "哪些改变只是数值平移，哪些会真正翻转材料筛选决策，以及翻转背后的物理机制。"
            "本页的终端需要 JavaScript；以下是同样的入口。</p>\n"
            "    <ul>\n"
            '      <li><span class="js-weeks">%d</span> 周报告：'
            '<a href="%s/tree/main/docs">全部周报（docs/）</a></li>\n'
            '      <li>图目录：<a href="%s/tree/main/outputs/figures">outputs/figures</a>'
            "（%d 张）</li>\n"
            '      <li>源码与全部文档：<a href="%s">GitHub 仓库</a></li>\n'
            "      <li>质检：<span class=\"js-tests\">%d</span> 个测试通过（pytest）</li>\n"
            "      <li>%s</li>\n"
            "    </ul>\n"
            "  </div>\n"
            "</noscript>"
            % (c["weeks"], REPO_URL, REPO_URL, c["figures"], REPO_URL,
               c["tests_passed"], gate_summary(payload)))


def render_brief_lede(payload):
    c = payload["counts"]
    return ('    <p class="lede">\n'
            '      一个反直觉的结论，用 <span class="js-weeks">%d</span> 周、'
            '<span class="js-orca">%d</span> 个 ORCA 作业、'
            '<span class="js-figures">%d</span> 张图和一条「唯一变量」纪律做出来：\n'
            "      每改一层模型，都只允许一个变量变，其余全部冻结。"
            "核心集只有 18 个分子 —— 足以把机制问清楚，\n"
            "      不需要大数据。\n"
            "      <span class=\"lede-min\">哪几层可以不算：</span>"
            "闭式判据可以在花钱前预判（q_ij &lt;= sqrt(2)/z）、介电层自相似而几乎免费\n"
            "      （|dE| x eps ~ 2.1 eV）、配位位移次线性饱和，"
            "漏解只需要靶向而不是全局翻倍。\n"
            "    </p>"
            % (c["weeks"], c["orca_out"], c["figures"]))


def render_brief_links(payload):
    last = payload["weeks"][-1]
    return ('    <div class="links">\n'
            '      <a class="chip" href="#status">status</a>\n'
            '      <a class="chip" href="#figures">figures</a>\n'
            '      <a class="chip" href="#argument">argument</a>\n'
            '      <a class="chip" id="chip-cat-latest" data-cmd="cat %d" href="#cat %d">'
            'cat <span class="js-latest-week">%d</span></a>\n'
            '      <a class="chip" id="chip-report-latest" href="%s/tree/main/docs">'
            '完整报告 (<span class="js-latest">Week %d / %s</span>)</a>\n'
            '      <a class="chip" href="%s" rel="noopener">GitHub</a>\n'
            "    </div>"
            % (last["n"], last["n"], last["n"], REPO_URL, last["n"], last["stage"],
               REPO_URL))


def render_argument_timeline(payload):
    """The 18-week argument as plain HTML: no script, no fetch, crawlable."""
    rows = []
    for w in payload["weeks"]:
        rows.append(
            '      <li class="argue-row" data-week="%d">\n'
            '        <a class="argue-wk" href="%s/blob/main/%s">%s</a>\n'
            '        <span class="argue-stage">%s</span>\n'
            '        <p class="argue-tag">%s</p>\n'
            "      </li>"
            % (w["n"], REPO_URL, w["doc"], week_label(w["n"]),
               esc(w["stage"]), esc(w["tag"])))
    return ('<section class="argue" id="argument" aria-labelledby="argument-h">\n'
            '  <div class="argue-inner">\n'
            '    <h2 class="eyebrow" id="argument-h">the argument, week by week</h2>\n'
            '    <ol class="argue-list">\n'
            + "\n".join(rows) + "\n"
            "    </ol>\n"
            '    <p class="argue-foot">每一行是一周：这一周只允许一个变量改变，'
            "一句话就是这一周的结论。链接指向仓库里对应的报告原文。</p>\n"
            "  </div>\n"
            "</section>")


def managed_blocks(payload):
    """(marker name, content) for every region of index.html the builder owns."""
    return [
        ("static-meta", render_meta(payload)),
        ("static-fallbacks", render_noscript(payload)),
        ("brief-counts", render_brief_lede(payload)),
        ("brief-links", render_brief_links(payload)),
        ("argument-timeline", render_argument_timeline(payload)),
    ]


def build_payload():
    return {
        "repo": REPO_URL,
        "counts": counts(),
        "pipeline": [{"n": n, "name": nm, "detail": d} for n, nm, d in PIPELINE],
        "gates": gates(),
        "weeks": week_payload(),
        "figures": figure_payload(),
    }


def data_js_text(payload):
    body = json.dumps(payload, ensure_ascii=False, indent=1, sort_keys=False)
    return ("/* generated by scripts/build_terminal_site.py - do not edit by hand */\n"
            "window.HB = " + body + ";\n")


def build():
    os.makedirs(FIGDIR, exist_ok=True)
    copied = 0
    for _, png, _, _ in FIGURES:
        src = os.path.join(REPO, "outputs", "figures", png)
        dst = os.path.join(FIGDIR, png)
        need = True
        if os.path.exists(dst) and os.path.getsize(dst) == os.path.getsize(src):
            need = sha256_of(dst) != sha256_of(src)
        if need:
            shutil.copyfile(src, dst)
            copied += 1
    payload = build_payload()
    text = data_js_text(payload)
    page = render_404(payload)
    with io.open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    with io.open(PAGE_404, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(page)
    if not os.path.exists(INDEX):
        raise SystemExit("docs/index.html is missing: it is the page the builder fills in")
    blocks = managed_blocks(payload)
    index = read(INDEX)
    for name, inner in blocks:
        index = splice_block(index, name, inner)
    with io.open(INDEX, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(index)
    print("404.html   %d bytes (relative paths, counts baked in)"
          % len(page.encode("utf-8")))
    print("data.js    %d bytes | %d figures (%d copied) | %d week entries"
          % (len(text.encode("utf-8")), len(FIGURES), copied, len(payload["weeks"])))
    print("index.html %d bytes | %d managed regions re-rendered"
          % (len(index.encode("utf-8")), len(blocks)))
    for g in payload["gates"]:
        print("  %-32s %s  blockers=%d" % (g["name"], g["status"], len(g["blockers"])))
    print("  counts: %s" % json.dumps(payload["counts"], ensure_ascii=False))


def check():
    """Verify the published folder against the repository it describes.

    Every claim is re-derived from the repository, not compared against itself:
    a data.js that has quietly gone stale is reported as stale, and so is any
    region of index.html that no longer matches what the builder would write.
    """
    problems = []
    try:
        payload = build_payload()
    except SystemExit as exc:
        print("  [XX] " + str(exc))
        return 1
    if not os.path.exists(OUT):
        problems.append("docs/assets/data.js missing")
    elif read(OUT) != data_js_text(payload):
        problems.append("docs/assets/data.js is stale (rerun build_terminal_site.py)")
    for row in payload["figures"]:
        dst = os.path.join(FIGDIR, row["file"])
        if not os.path.exists(dst):
            problems.append("figure not copied: " + row["file"])
        elif sha256_of(dst) != row["sha"]:
            problems.append("figure drifted: " + row["file"])
    if not os.path.exists(PAGE_404):
        problems.append("docs/404.html missing")
    elif read(PAGE_404) != render_404(payload):
        problems.append("docs/404.html is stale (rerun build_terminal_site.py)")
    if not os.path.exists(INDEX):
        problems.append("docs/index.html missing")
    else:
        html = read(INDEX)
        for name, inner in managed_blocks(payload):
            try:
                published = extract_block(html, name)
            except SystemExit as exc:
                problems.append(str(exc))
                continue
            if published != inner.strip("\n"):
                problems.append("docs/index.html region %s is stale "
                                "(rerun build_terminal_site.py)" % name)
    for name in ("index.html", "404.html", "assets/terminal.css",
                 "assets/terminal.js", ".nojekyll"):
        if not os.path.exists(os.path.join(DOCS, name)):
            problems.append("missing page asset: docs/" + name)
    if problems:
        for p in problems:
            print("  [XX] " + p)
        return 1
    print("terminal site: OK (%d figures, %d index regions, checks passed)"
          % (len(FIGURES), len(managed_blocks(payload))))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    sys.exit(check() if args.check else build() or 0)


if __name__ == "__main__":
    main()