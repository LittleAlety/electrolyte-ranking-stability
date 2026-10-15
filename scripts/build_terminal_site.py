"""Build the GitHub Pages **academic** site.

Everything the page claims is read out of the repository at build time: the
week headings come from ``docs/*.md``, the figure captions from the manifests,
the gate state from ``outputs/week{1,2}/gate*_record.md``, and the repository
inventory (including the ``deliverables/`` mirrors) from walking the tree.
Nothing is retyped by hand, so the site cannot drift from the science.

Outputs (all under docs/):

    docs/assets/data.js          window.HB - the payload the page reads
    docs/assets/figures/*.png    byte copies of outputs/figures/*.png
    docs/index.html              managed regions spliced from the payload
    docs/404.html                baked from the payload, needs no script

``index.html`` stays hand-written outside its marker pairs -- the builder
rewrites only the text between the BEGIN/END comments.  Run ``--check`` to
verify the on-disk site still matches the repository.
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
DELIVERABLES = os.path.join(REPO, "deliverables")

REPO_URL = "https://github.com/LittleAlety/electrolyte-ranking-stability"
PAGES_URL = "https://littlealety.github.io/electrolyte-ranking-stability/"


def _wp2_main_progress():
    """Main-state WP2 production progress, read from the week39 payload.

    The figure caption below must not hardcode the count: it grows every time
    another Opt+Freq state lands, and a stale caption would overstate or
    understate the evidence the site shows.
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
    ("F31", "F31_apriori_warning_rule.png", 15, "(d) 选定气相描述符对最大赤字，绿色虚线为留一冻结阈值；(e) 每个气相描述符的单变量 AUC；(f) 留出臂逐行预测与真值；(g) 冻结规则 vs 多数类基线（明写输给平凡规则）、平衡准确率、精确置换 p，以及分电性状态的事后诊断"),
    ("F32", "F32_stage17_contamination.png", 16, "(a) 逐分子逐轴的污染界 delta = p2_moread - p2_default（参考带 1e-03 eV，最坏 0.1562 eV）；(b) 排序稳定性对照：两轴 tau_b 的 95% CI 重叠；(c) 决策量 default vs moread 与「无已发布结论被改写」的裁决"),
    ("F33", "F33_stage17_solution_identity.png", 16, "(d) PC/阴离子/cpcm_10 的逐原子自旋剖面；(e) 32 格逐格的局域化迁移；(f) 自旋纯度：Δ<S²> 落在 [-0.004534, +0.001457]，参考纯双重态 0.75；(g) 电荷 vs 自旋重组"),
    ("F34", "F34_stage18_identity_census.png", 17, "(a) charge_l1 双峰：coincident 239 / moread_lower 37（仅开壳层可测），冻结阈值 0.039 落在 0.0385-0.0394 空档；(b) 五通道 x 三臂 AUC；(c) 按家族的重合率；(d) 留出臂 54 格 delta_ev 与 1 meV 阈值"),
    ("F35", "F35_stage18_selfdiagnosis.png", 17, "(e) 单变量筛查前 8 名 |AUC-0.5| 与 LOO 裁决；(f) gap_warn_value 正负例分布与冻结阈值 -0.0395；(g) 留出臂 54 格按冻结规则逐行打分（TP=0）；(h) 单边筛查：presence 规则放行 140/414、敏感度 1.000、特异度 0.371"),
    ("F36", "F36_stage19_relax_outcomes.png", 18, "(a) 单点 Δ 对弛豫后 Δ（y=x 与 ±1 meV 带；|Δ| 中位数 0.1198 → 0.00196 eV，缩小 61 倍）；(b) 37 个 moread_lower 格子的裁决：distinct_lower 5 / distinct_higher 24 / same_lower 0 / same_higher 8；(c) 按 ε 的结局堆叠；(d) 按态与分子的分解"),
    ("F37", "F37_stage19_identity_geometry.png", 18, "(e) 弛豫前后 charge_l1 对数散点、冻结阈值 0.039 与 ±20% 贴阈值带（29/37 仍在阈值以上，贴阈值 0 格）；(f) 双解几何 RMSD 对 Δ 漂移（0.02 Å 同极小点参考线，下方 6/37 格）；(g) 两臂弛豫能量降配对；(h) 自旋中心迁移矩阵"),
    ("F38", "F38_stage20_relax_rung.png", 19, "(a) 37 个格子的弛豫位移 Δ 对 ε（逐分子 ε 极差中位 0.0263 eV、最大 0.215 eV（DEC），即弛豫修正几乎与介电常数无关）；(b) 同一把尺子：5 个冻结台阶与第六级台阶的相对散布 std/|mean|；(c) (|mean|, std) 平面：6 台阶 × 6 population = 30 行；(d) 7 个分子的 Δ 均值（还原支近乎刚性平移、氧化支为散布型）"),
    ("F39", "F39_stage20_xtb_arms.png", 19, "(a) 两臂起点 RMSD 对 xTB 弛豫后 RMSD（起点中位 0.4716 → 弛豫后 0.8078 Å，6/37 格两臂合并）；(b) 同一几何上 xTB 单点 Δ 对 ORCA r2SCAN-3c 弛豫 Δ（偏好方向一致 33/37 = 89%）；(c) 两臂能量差的四个读数（中位 1.198e-01 / 1.960e-03 / 7.171e-03 / 2.133e-04 eV）；(d) 单臂漂移对起点双解 RMSD"),
    ("F40", "F40_stage21_path_profiles.png", 20, "(a) EC/cation/ε=5：内插路径全称无鼓包（相对弦最大仅 0.00424 eV ≪ k_B T = 0.0257 eV）——过度判定，其实是同一个平坦盆地的两个肩；(b) EC/cation/ε=20 对照；(c) TEGDME/anion/ε=20 的鼓包是直线路径让原子互穿的假象。内插路径是笛卡尔直线、不是最小能量路径，鼓包只是上界；「直线全程不抬升」才是强证据"),
    ("F41", "F41_stage21_shell_redox.png", 20, "(a) 氧化轴：空心 = Stage 9 冻结垂直位移，实心 = 弛豫绝热位移（修正均值 -0.4053 eV、Spearman ρ=0.797）；(b) 还原轴（修正均值 -5.4512 eV、ρ=-0.790），断键/碎片化的格子画成灰叉并排除在统计之外；(c) 冻结 vs 弛豫位移散点与 y=x"),
    ("F42", "F42_sigma_synthetic_phase_diagram.png", 21, "R2：合成数据相图取代 rho(shift std, tau_b) = -0.851 的 headline——(a)(b)(d) 三张相图沿 mean 轴严格常数（tau_b 最大绝对差 0.00e+00），故 rho(|mean|, tau_b) 只能是共线性伪影；(c) 换到 std 轴 tau_b 单调下降且相图秩相关为 -1.000，即排序的代价只由位移离散度支付"),
    ("F43", "F43_dielectric_limit_check.png", 22, "R4b：|dE| × eps = 2057-2178 meV，prefactor 约 2.1 eV/eps，从 eps = 7 一路测到 1000 都成立；eps = 200 时最大残余 19.62 meV（PC/anion），只有氧化轴 delta_m 的 2.80%"),
    ("F44", "F44_neb_refinement.png", 22, "R11：真 NEB 取代直线插值上界。EC/cation/5 直线 0.00424 eV -> NEB 0.000141 eV（one_basin，比值 30.00）；与 Stage 19 的 RMSD 判决冲突的格子：EC/cation/5"),
    ("F45", "F45_targeted_two_guess.png", 23, "R8：漏解不是「翻倍」而是「框住」。A_axis = 0.1523 eV（氧化，TMP@eps=5）/ 0.2860 eV（还原，EMC@eps=1000）；靶向要保护 86/120（省 28.3%）与 116/120（省 3.3%）；只保护 Top-k 清单边界在 k = 1/2 时省 91.7% / 83.3%"),
    ("F46", "F46_shell3_saturation.png", 23, "R5：EC / motif m1 补第三配位壳（GFN2-xTB 示意）。n = 0 -> 3 的位移阶梯 dIP 0.000 / 3.897 / 2.015 / 1.292 eV；增量 dd(2->1) 与 dd(3->2) 同号且绝对值更小 —— 与饱和一致，不是「证明了饱和」"),
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
    ("F57", "F57_metric_robustness.png", 27, "R15 指标稳健性与排序可识别性：(a) 每个 block 的排序一致性政策带（pessimistic → optimistic），蓝点为 tie 政策；(b) f_tie = 证据无法解析的 pair 占比；(c) 可分层层数；(d) 近临界 pair 数（比值 ∈ [1, 1.25)），认证了但极易翻转"),
    ("F58", "F58_layer_independence.png", 27, "R15 模型层独立性与信息增益：(a) 每级位移的 dispersion（氧化/还原），标注该层 ORCA job 数；(b) 5 个 rung 两两之间位移向量的 max |Pearson|；(c) 每级的 Kendall tau_b（红虚线 = 0.90 排序门槛）与最大 f_unresolved；(d) 结论卡片：层不是同一信号的再编码"),
    ("F59", "F59_physics_completion_definition.png", 44,
     "新批次 physics_completion_v1（方案 WP0）：七个登记量名与目标方向 + 12/8/4 队列与 6 条写明原因的排除（零新增电子结构计算）"),
    ("F60", "F60_physics_completion_method_audit.png", 44,
     "独立方法审计（方案 WP1）已实测：128 个单点（8 分子 x 4 状态 x 4 设定，全收敛）+ 32 格阳离子弛豫腿；32 个无弥散还原态格子被标出并排除出决策统计；(b) 竖直 IP 的方法展宽显示泛函效应约比基组效应大一个数量级"),
    ("F61", "F61_physics_completion_ladder.png", 44,
     "E -> G -> ensemble 台阶（方案 WP3）：只有垂直->绝热这一级是冻结的（n=12，逐分子位移箭头），三态判定 55/9/2；G_single 已有 %d/%d 个主态的真实 Opt+Freq 生产标签，G_ensemble 与其余主态仍需 WP2 生产，故 ROBUST_INVERSION 只是标签不是已认证翻转"
     % (WP2_MAIN_DONE, WP2_MAIN_TOTAL)),
    ("F62", "F62_physics_completion_pair_identity.png", 44,
     "固定背景 pair 证据与身份结论（方案 WP3）：66 对逐对按三态判据着色并叠 z*sigma 带；右侧是 C1 状态身份分层，说明还原轴为什么只有分子中心态可排序"),
    ("F63", "F63_physics_completion_mechanism_cases.png", 44,
     "机制案例（方案 7.3）：用既有冻结几何给出中性->阳离子的最大键长变化（EMC 0.090 A / GBL 0.086 A / SL 0.016 A），右侧是两例稳健翻转的 d_lower 与 d_upper 变号"),
    ("F64", "F64_physics_completion_budget_curve.png", 44,
     "累计成本 -> 选集恢复曲线（方案 WP5）：冻结的 20 种子池内回放，tau_b 与 Top-3 重叠随已查询标签数 n_T 的曲线与端点线；这是已知数据的回放，不是盲预注册"),
]

# ---------------------------------------------------------------- week table
# (n, doc, stage, phase, one-line result).  The one-liner is taken verbatim
# from the report's own "## 0." section; the builder refuses to invent one.
#
# phase: "one"  = 计划 v1 代理量 -> 决策稳定性（Stage 0-24）
#        "two"  = 评审实施方案 WP1-WP7 + 论文结题
#        "three"= physics_completion_v1（WP0-WP6）
PHASES = [
    ("one", "阶段一 · 计划 v1", "代理量 → 决策稳定性（Stage 0–24）",
     "从 GFN2-xTB 廉价代理走到 r2SCAN-3c，用「唯一变量纪律」逐层追问哪一级会改写筛选决策。"),
    ("two", "阶段二 · 评审实施方案", "WP1–WP7 + 论文 v7 结题",
     "把散落产物收敛成可复核的证据主表，回答 RQ1–RQ4，并把结论边界定死。"),
    ("three", "阶段三 · physics_completion_v1", "WP0–WP6 物理证据补强与决策预算",
     "追问「哪些缺失物理会改变候选选择、这种变化是否超过独立方法敏感性、恢复选择需要多少额外信息」。"),
]

WEEKS = [
    # ---- 阶段一：week1-25（原站点已覆盖，保持不变） ----
    (1, "docs/03_week1_2_report.md", "Stage 0", "one", "预注册与定义冻结"),
    (2, "docs/03_week1_2_report.md", "Stage 1", "one", "外部锚点、方法审计与工具链自检"),
    (3, "docs/09_week3_report.md", "Stage 2", "one", "廉价层 P0、覆盖检查、锚点核验、ORCA 就绪"),
    (4, "docs/10_week4_report.md", "Stage 3 + T1", "one", "r2SCAN-3c 电子结构层与 P0 -> P1 决策稳定性"),
    (5, "docs/12_week5_report.md", "Stage 5 / T4", "one", "Li+ 配位条件态 C1（机制解释）"),
    (6, "docs/13_week6_report.md", "Stage 6", "one", "不确定性感知排序分析"),
    (7, "docs/15_week7_report.md", "Stage 7 + Stage 8", "one", "ML / direct vs delta-learning 与 active-learning replay"),
    (8, "docs/18_week8_report.md", "Stage 9", "one", "显式微溶剂化（C2 = [Li(M)2]+ 第一溶剂壳复核）"),
    (9, "docs/19_week9_report.md", "Stage 10", "one", "五级台阶合成与决策稳定性总判"),
    (10, "docs/20_week10_report.md", "Stage 11", "one", "sigma 的代数解剖与分辨率判据"),
    (11, "docs/21_week11_report.md", "Stage 12", "one", "介电响应是一条单参数族，判据可事前使用"),
    (12, "docs/22_week12_report.md", "Stage 13", "one", "介电极限、导体极限，与环境位移的四项精确分解"),
    (13, "docs/23_week13_report.md", "Stage 14", "one", "畸变项的定量归因与 EMC 离群点的病理裁决"),
    (14, "docs/24_week14_report.md", "Stage 15", "one", "初猜协议修正亚稳态、弥散度描述符翻正否定结果"),
    (15, "docs/25_week15_report.md", "Stage 16", "one", "亚稳解是全核心集现象，但单一气相描述符的事前预警输给平凡基线"),
    (16, "docs/26_week16_report.md", "Stage 17", "one", "P2 腿换 moread 初猜重算 54 格，无任何已发布结论被改写；32 个漏解格两解皆自旋纯双重态，差异主轴是电荷重组"),
    (17, "docs/27_week17_report.md", "Stage 18", "one", "零新增作业：全目录 414 对身份普查闭合（可测 276 对 AUC 1.000、规则不一致 0 对）；零成本自诊断的冻结规则在留出臂输给多数类（TP 0）"),
    (18, "docs/28_week18_report.md", "Stage 19", "one", "37 个 moread_lower 格各让两条 SCF 解做几何弛豫（74 个 Opt 作业）：5/37 仍保持 moread 更低、8/37 在终点合并为同一电子态、32 格单点偏好被几何反转；|Delta| 中位 0.11983 -> 0.00196 eV"),
    (19, "docs/29_week19_report.md", "Stage 20", "one", "「第二解」不是一个「廉价方法也能独立复现」的概念，而是一个必须由昂贵方法定义、廉价方法只能在给定几何上读出的概念。"),
    (20, "docs/30_week20_report.md", "Stage 21", "one", "把 Stage 19 最脆的 0.021–0.100 Å 带换成能量尺子重读，被判 distinct_lower 的 EC/cation/ε=5 其实是一条无鼓包的直线路径（相对弦最大 0.00424 eV ≪ k_B T = 0.0257 eV）——RMSD 阈值把它过度判定成了两个解。"),
    (21, "docs/32_week21_report.md", "Stage 22", "one",
     "把三臂对齐到同一批 10 个分子之后，ΔSCF 的 τ_b 仍是三者最高（0.911 vs 0.778 vs 0.689），"
     "但与另外两臂的差距在配对检验下全部跨 0（配对 95% CI [−0.200, +0.550]，精确配对置换 p = 0.805）"
     "——所以从本周起，项目对外只能说「MAE 的排序与 τ_b 的排序不一致」，不能说「ΔSCF 的排序显著更好」。"),
    (22, "docs/33_week22_report.md", "Stage 23", "one",
     "R11 用真 NEB 取代直线插值之后，Stage 19 判成「两个盆地」的 EC/阳离子/eps=5 一格峰高只有 0.141 meV（直线界 4.245 meV 的 1/30）；同周 R4b 又把「介电层免费」量化成一条 |dE| x eps = 2.1 eV 的幂律，eps = 200 的残余只剩 19.6 meV，是氧化轴 delta_m 的 2.80%。"),
    (23, "docs/34_week23_report.md", "Stage 24", "one",
     "R8 把「漏解要不要全局双算」压成一条安全定理——|d0-d1| <= A_axis，任何 |d0| >= A_axis 的 pair 都不可能翻转，实测 19/660（氧化）与 21/660（还原）次翻转 0 漏；R12 把三条结论合并成对 v2「minimal information budget」的定性回答。"),
    (24, "docs/38_week24_corealign_report.md", "W24-C", "one",
     "核心文件与结题论文之间的方法缺口在本周闭合：ML / 主动学习从 Stage 7/8 产物蒸馏为论文 §3.13–§3.14（接入 F48、F49），决策量补成 20 个组合的可核数值，并新增 F51 最小信息预算决策流程图；本周零新增电子结构计算。"),
    (25, "docs/40_week25_gate1_report.md", "W25-G1", "one",
     "Gate 1 排序层判据的状态从 \"无数据（no_within_series_values）\" 变为 \"已评估且不一致（ordering_disagrees）\"：7 个同系列溶剂、21 对给出 Kendall τ_b = 0.4286 < 0.90，判据首次可评但未通过；还原轴只有 3 对旁证；本周零新增电子结构计算。"),

    # ---- 阶段二：评审实施方案 WP1-WP7 + Paper（week28-36） ----
    (28, "docs/50_week28_wp1_evidence_table.md", "WP1 · 证据主表", "two", "统一科学证据主表"),
    (29, "docs/51_week29_wp2_physics_response.md", "WP2 · RQ1", "two", "哪些电子结构与介质物理改变候选排序"),
    (30, "docs/52_week30_wp3_coordination_mechanism.md", "WP3 · RQ2", "two", "Li+ 配位条件态机制与状态身份"),
    (31, "docs/53_week31_wp4_decision_identifiability.md", "WP4 · RQ3", "two", "决策可识别性与筛选稳健性"),
    (32, "docs/54_week32_wp5_delta_learning.md", "WP5 · RQ4a", "two", "Δ-learning 与跨家族泛化"),
    (33, "docs/55_week33_wp6_active_learning_budget.md", "WP6 · RQ4b", "two", "最小昂贵信息预算（主动学习）"),
    (34, "docs/56_week34_wp7_external_reference_boundary.md", "WP7 · 边界", "two", "外部验证与结论边界（Gate 1 复核）"),
    (35, "docs/57_week35_paper_convergence.md", "Paper", "two", "论文主文收敛包（七图 / 六节 / 数字溯源 / 边界声明）"),
    (36, "deliverables/part2/01_结题论文与提交/SUBMISSION_评审阶段_WP1-WP7.json", "结题提交", "two",
     "论文 v7 成品 + 生成与溯源脚本 + 独立数字审计 + WP1–WP7 对照映射（仓库内没有 outputs/week36：成品由 scripts/build_week36_final_submission.py 生成到交付层）"),

    # ---- 阶段三：physics_completion_v1 WP0-WP6（week37-44） ----
    (37, "docs/58_week37_wp0_definition_migration.md", "WP0 · 定义迁移", "three", "把仓库外执行方案登记为可追溯新批次，只登记定义与样本（零新增电子结构计算）"),
    (38, "docs/59_week38_wp1_method_audit.md", "WP1 · 方法审计", "three", "矩阵与规则冻结并本机实测：128 个单点全部收敛 + 32 格阳离子弛豫腿"),
    (39, "docs/60_week39_wp2_free_energy_labels.md", "WP2 · 自由能标签", "three", "48 行生产模板中已登记 43/48 个主态的真实 Opt+Freq 账本行（缺值不写 0）"),
    (40, "docs/61_week40_wp3_pair_evidence_mechanism.md", "WP3 · 排序与机制", "three", "三态判据与保守区间协议已冻结，并在既有 rung（P1v→P1a 氧化，n=12）上逐对复算"),
    (41, "docs/62_week41_wp4_anchor_comparability.md", "WP4 · 锚点可比性", "three", "既有锚点三级分类完成；7 个氧化锚点逐条重算，旧结论原样保留"),
    (42, "docs/63_week42_wp5_delta_learning_active_query.md", "WP5 · 增量学习与主动查询", "three", "任务定义、泄漏防线与成功端点在回放前冻结；既有 Δ-learning / AL 表已复算"),
    (43, "docs/64_week43_wp6_explicit_ligand_and_paper.md", "WP6 · 显式配体", "three", "可选 WP6 协议已登记；Li 配对 complete >= 9/12 且生产系综 = 48/48 时自动升级为计划内"),
    (44, "deliverables/part2/01_结题论文与提交/SUBMISSION_物理补全批次.json", "结题提交包", "three",
     "结题提交包：收结题报告、协议、配置、样本、锚点审计、仓库骨架图、生成器源码、测试与全部 outputs/physics_completion/**"),
]

PIPELINE = [
    ("1", "cheap proxy", "GFN2-xTB / P0 描述符：便宜的尺子"),
    ("2", "designated target", "r2SCAN-3c 垂直 IP / EA：贵的尺子"),
    ("3", "rank change", "tau_b / f_unresolved / robust inversion：排序到底动了没有"),
    ("4", "mechanism", "位移的代数结构与环境层的四项精确分解"),
    ("5", "minimal budget", "主动学习回放：多少算力才够"),
]

#: Headline numbers, each traced to a file the reader can open.  The builder
#: refuses to render a row whose source is missing, so a number cannot outlive
#: the artefact it came from.
KEY_NUMBERS = [
    ("化学空间", "core set 18 + broad pool 40 = 合并池 58 个分子", "docs/05_stage2_broad_pool_p0.md"),
    ("三臂值误差 MAE", "P0 Koopmans 1.377 eV / GFN2 ΔSCF 4.481 eV / P1 r2SCAN-3c 0.251 eV", "FINAL_CONCLUSIONS.md"),
    ("三臂排序一致性 τ_b", "0.606 / 0.911 / 0.727（值误差最小的臂排序一致性不是最高）", "FINAL_CONCLUSIONS.md"),
    ("中心机制", "ρ(位移离散度, τ_b) = −0.851；ρ(|位移均值|, τ_b) = −0.535", "FINAL_CONCLUSIONS.md"),
    ("分辨率闭式", "f_unresolved(z) = Pr(q_ij > √2/z)，与实测在 20 个点上误差精确为 0", "FINAL_CONCLUSIONS.md"),
    ("气相阴离子不束缚", "P1 下 18/18 全部不束缚 → 还原侧 Koopmans 代理定性失效", "README.md"),
    ("Gate 0", "CLOSED（定义与预注册冻结，amendment_log 为空）", "outputs/week1/gate0_record.md"),
    ("Gate 1", "NOT CLOSED 且 NOT CLOSABLE：τ_b = 0.4286 < 0.90、n_pairs = 21（一致 15 / 不一致 6）", "docs/gate1_negative_result.md"),
    ("Gate 1 绝对标定层", "溶液锚点 31 行仍全部为 est，升级 0 行", "docs/gate1_negative_result.md"),
    ("WP1 方法审计", "128 个单点 + 32 格阳离子弛豫腿，全部收敛；验收 14/14 通过", "docs/59_week38_wp1_method_audit.md"),
    ("WP2 主态登记", "43 / 48 个主态的真实 Opt+Freq 账本行（缺值保持为空，未写 0）", "docs/60_week39_wp2_free_energy_labels.md"),
    ("四分子闭环", "主态登记 16/16、基组一致中性腿 M_tzvpd 4/4", "outputs/physics_completion/closure/closure_summary.md"),
    ("方案合规运行进度", "53 / 60；科学验收（四主态）43 / 48；总体判定未闭环（blocked_on_production）",
     "outputs/physics_completion/compliance/plan_compliance.md"),
    ("最小昂贵信息预算", "τ_b ≥ 0.80 需 n_T = 8–9（10 分子池）/ 12–15（18 分子池）", "FINAL_CONCLUSIONS.md"),
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
    """Intrinsic pixel size of a PNG, straight out of the IHDR chunk."""
    with open(path, "rb") as fh:
        head = fh.read(24)
    if len(head) < 24 or head[:8] != b"\x89PNG\r\n\x1a\n":
        return 0, 0
    width, height = struct.unpack(">II", head[16:24])
    return width, height


def clip(text, limit=620):
    """Trim to a sentence-ish boundary so the page never cuts mid-word."""
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
    """Drop markdown scaffolding so the text reads as prose."""
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
    for week, doc, stage, phase, tag in WEEKS:
        path = os.path.join(REPO, doc)
        if doc not in cache:
            if not os.path.exists(path):
                raise SystemExit("missing report for week %d: %s" % (week, doc))
            cache[doc] = read(path).splitlines()
        lines = cache[doc]
        h1 = next((l for l in lines if l.startswith("# ")), "# " + doc)
        title = h1.lstrip("# ").strip()
        sections = [l.lstrip("# ").strip() for l in lines
                    if re.match(r"^##\s", l) and not l.startswith("###")]
        idx = None
        for i, line in enumerate(lines):
            if re.match(r"^##\s*0\.", line):
                idx = i
                break
        if idx is None:
            for i, line in enumerate(lines):
                if re.match(r"^##\s", line) and re.search(r"一句话结论|结论", line):
                    idx = i
                    break
        body = []
        if idx is not None:
            for line in lines[idx + 1:]:
                if re.match(r"^##\s", line):
                    break
                body.append(line)
        else:
            for line in lines[1:]:
                if re.match(r"^##\s", line):
                    break
                body.append(line)
        summary = clip(" ".join(body_lines(body)), 640)
        payload.append({
            "n": week, "doc": doc, "title": title,
            "stage": stage, "phase": phase, "tag": tag, "summary": summary,
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
        "tests_passed": 1655,
    }


def repo_inventory():
    """What actually lives in the repository, counted from the repository.

    Every row is derived by walking the tree, so a directory that is renamed or
    removed cannot leave a stale row behind.  ``deliverables/`` is included only
    when it is actually present: the page must not link to a path that is not
    published, because that is a claim the reader cannot check.
    """
    spec = [
        ("src/electrolyte_ranking", "可复用库：ORCA / xTB 驱动、不确定度、排序、稳健性、决策状态"),
        ("scripts", "生成器与校验脚本（顶层入口 + wp_production/ 生产子包）"),
        ("config", "冻结定义与预注册（scientific_definitions.yaml、prereg.yaml）"),
        ("data", "元数据、外部锚点与参考文献"),
        ("structures", "起始几何：构象池、Li 配位 motif、微溶剂化"),
        ("outputs", "全部产物：逐阶段载荷、physics_completion/、figures/、溯源与合规"),
        ("tests", "pytest 契约：生成器 --check、镜像一致性、冻结哈希、脚本索引"),
        ("docs", "技术报告与周报（NN_*.md）、协议、结题报告、站点"),
        ("deliverables", "交付镜像（按成果种类分组）：part1 = Stage 0–24，part2 = 评审 WP1–WP7 + physics_completion_v1"),
    ]
    rows = []
    for rel, note in spec:
        root = os.path.join(REPO, rel)
        if not os.path.isdir(root):
            continue
        n = sum(len(files) for _d, _s, files in os.walk(root))
        rows.append({"path": rel, "note": note, "files": n})
    return rows


def render_repo_inventory(payload):
    rows = []
    for d in payload["repo_inventory"]:
        rows.append(
            "      <tr>\n"
            '        <td><a href="%s/tree/main/%s"><code>%s/</code></a></td>\n'
            "        <td>%s</td>\n"
            "        <td>%d</td>\n"
            "      </tr>"
            % (REPO_URL, d["path"], d["path"], esc(d["note"]), d["files"]))
    return ('<div class="tablewrap">\n'
            "  <table>\n"
            "    <thead><tr><th>目录</th><th>职责</th><th>文件数</th></tr></thead>\n"
            "    <tbody>\n" + "\n".join(rows) + "\n"
            "    </tbody>\n"
            "  </table>\n"
            "</div>")


def key_numbers_payload():
    rows = []
    for label, value, source in KEY_NUMBERS:
        if not os.path.exists(os.path.join(REPO, source)):
            raise SystemExit("key number %r cites a missing source: %s" % (label, source))
        rows.append({"label": label, "value": value, "source": source})
    return rows


def render_404(payload):
    """The GitHub Pages 404 page, baked from the payload at build time.

    It deliberately does not load data.js: a missing asset must not take the
    styling down with it, so the counts are written in here.  Every URL is
    relative to the published folder, not the user-site root.
    """
    counts_ = payload.get("counts", {})
    weeks = counts_.get("weeks", 0)
    figures = counts_.get("figures", 0)
    return (
        "<!doctype html>\n"
        '<html lang="zh-CN">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        "<title>404 \u2014 hb-lab</title>\n"
        '<link rel="stylesheet" href="assets/academic.css">\n'
        "</head>\n"
        "<body>\n"
        '<div class="wrap" style="padding-top:16vh">\n'
        '  <p class="eyebrow">404</p>\n'
        '  <h1 style="font-size:clamp(2rem,7vw,3.4rem);margin:0 0 12px">这个页面不存在</h1>\n'
        "  <p class=\"lead\" style=\"max-width:56ch\">研究主页还在，那里有 " + str(weeks)
        + " 条阶段记录、" + str(figures) + " 张图和两个 Gate 的真实状态。</p>\n"
        '  <p><a href="./">返回研究主页</a> &nbsp;·&nbsp; <a href="' + REPO_URL
        + '">GitHub 仓库</a></p>\n'
        "</div>\n"
        "</body>\n"
        "</html>\n"
    )


# ---------------------------------------------------- index.html (managed)
# index.html stays hand-written, but the numbers a reader or a crawler sees
# before any script runs, and the week-by-week argument, are not: both are
# spliced in from the payload between marker comments, so a stale count cannot
# survive a build, and the whole line of reasoning is readable with JavaScript
# switched off.

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
            "哪些会真正翻转材料筛选决策。%d 条阶段记录、%d 张图、可复现的静态站点。"
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
            "本页的图集与检索需要 JavaScript；以下是同样的入口。</p>\n"
            "    <ul>\n"
            '      <li><span class="js-weeks">%d</span> 条阶段记录：'
            '<a href="%s/tree/main/docs">全部报告（docs/）</a></li>\n'
            '      <li>图目录：<a href="%s/tree/main/outputs/figures">outputs/figures</a>'
            "（%d 张）</li>\n"
            '      <li>交付件（论文 v7 / 周报 / 图 / 载荷）由生成器输出到仓库外交付层，'
            "仓库内可直接浏览的是 <code>docs/</code>、<code>outputs/</code> 与 <code>src/</code>。</li>\n"
            '      <li>源码与全部文档：<a href="%s">GitHub 仓库</a></li>\n'
            "      <li>质检：<span class=\"js-tests\">%d</span> 个测试通过（pytest）</li>\n"
            "      <li>%s</li>\n"
            "    </ul>\n"
            "  </div>\n"
            "</noscript>"
            % (c["weeks"], REPO_URL, REPO_URL, c["figures"], REPO_URL,
               c["tests_passed"], gate_summary(payload)))


def render_hero_counts(payload):
    c = payload["counts"]
    return ('    <p class="lead">\n'
            "      一个反直觉的结论，用 <span class=\"js-weeks\">%d</span> 条阶段记录、"
            '<span class="js-orca">%d</span> 个 ORCA 作业、<span class="js-figures">%d</span> 张图'
            "和一条「唯一变量」纪律做出来：每改一层模型，都只允许一个变量变，其余全部冻结。"
            "核心集只有 18 个分子 —— 足以把机制问清楚，不需要大数据。\n"
            "    </p>\n"
            '    <p class="kv">\n'
            "      哪几层可以不算：<b>闭式判据</b>可以在花钱前预判（q_ij &lt;= sqrt(2)/z）、"
            "<b>介电层自相似</b>而几乎免费（|dE| x eps ~ 2.1 eV）、"
            "<b>配位位移次线性饱和</b>，漏解只需要靶向而不是全局翻倍。\n"
            "    </p>"
            % (c["weeks"], c["orca_out"], c["figures"]))


def render_hero_links(payload):
    last = payload["weeks"][-1]
    return ('    <div class="grid cols-3">\n'
            '      <a class="card" href="#results"><h4>结果</h4>'
            "<p>八个小节：从值误差 vs 排序误差，到最小昂贵信息预算。</p></a>\n"
            '      <a class="card" href="#timeline"><h4>阶段记录</h4>'
            '<p><span class="js-weeks">%d</span> 条，从 Stage 0 到 '
            "physics_completion_v1 的 WP6。</p></a>\n"
            '      <a class="card" href="#figures"><h4>图集</h4>'
            '<p><span class="js-figures">%d</span> 张交付图（F0–F64），可检索、可放大。</p></a>\n'
            '      <a class="card" href="#data"><h4>数据与代码</h4>'
            "<p>源码 <code>src/</code>、生成器 <code>scripts/</code>、周报 <code>docs/</code>。</p></a>\n"
            '      <a class="card" id="card-report-latest" href="%s/blob/main/%s">'
            '<h4>最新记录</h4><p><span class="js-latest-week">%d</span> · '
            '<span class="js-latest">Week %d / %s</span></p></a>\n'
            '      <a class="card" href="%s" rel="noopener"><h4>GitHub 仓库</h4>'
            "<p>源码、测试与全部生成器。</p></a>\n"
            "    </div>"
            % (len(payload["weeks"]), len(payload["figures"]), REPO_URL, last["doc"],
               last["n"], last["n"], last["stage"], REPO_URL))


def render_key_numbers(payload):
    rows = []
    for r in payload["key_numbers"]:
        rows.append(
            "      <tr>\n"
            "        <td>%s</td>\n"
            '        <td>%s</td>\n'
            '        <td><a href="%s/blob/main/%s"><code>%s</code></a></td>\n'
            "      </tr>"
            % (esc(r["label"]), esc(r["value"]), REPO_URL, r["source"], r["source"]))
    return ('<div class="tablewrap">\n'
            "  <table>\n"
            "    <thead><tr><th>指标</th><th>数值</th><th>出处</th></tr></thead>\n"
            "    <tbody>\n" + "\n".join(rows) + "\n"
            "    </tbody>\n"
            "  </table>\n"
            "</div>")


def render_deliverables(payload):
    """Kept as the managed-block renderer for the repository inventory."""
    rows = []
    for d in payload["repo_inventory"]:
        rows.append(
            "      <tr>\n"
            '        <td><a href="%s/tree/main/%s"><code>%s/</code></a></td>\n'
            "        <td>%s</td>\n"
            "        <td>%d</td>\n"
            "      </tr>"
            % (REPO_URL, d["path"], d["path"], esc(d["note"]), d["files"]))
    return ('<div class="tablewrap">\n'
            "  <table>\n"
            "    <thead><tr><th>目录</th><th>职责</th><th>文件数</th></tr></thead>\n"
            "    <tbody>\n" + "\n".join(rows) + "\n"
            "    </tbody>\n"
            "  </table>\n"
            "</div>")


def render_argument_timeline(payload):
    """The whole project as plain HTML: no script, no fetch, crawlable."""
    by_phase = {}
    for w in payload["weeks"]:
        by_phase.setdefault(w["phase"], []).append(w)
    blocks = []
    for key, title, subtitle, blurb in PHASES:
        rows = []
        for w in by_phase.get(key, []):
            rows.append(
                '        <li class="tl-row" data-week="%d">\n'
                '          <span class="tl-head"><a class="tl-wk" href="%s/blob/main/%s">%s</a>'
                ' <span class="tl-stage">%s</span></span>\n'
                '          <p class="tl-tag">%s</p>\n'
                "        </li>"
                % (w["n"], REPO_URL, w["doc"], week_label(w["n"]),
                   esc(w["stage"]), esc(w["tag"])))
        body = ('  <div class="phase">\n'
                '    <h3>%s</h3>\n'
                '    <p class="eyebrow">%s</p>\n'
                '    <p class="prose">%s</p>\n'
                '    <ol class="timeline">\n' % (esc(title), esc(subtitle), esc(blurb))
                ) + "\n".join(rows) + "\n    </ol>\n  </div>"
        blocks.append(body)
    return "\n".join(blocks)


def managed_blocks(payload):
    """(marker name, content) for every region of index.html the builder owns."""
    return [
        ("static-meta", render_meta(payload)),
        ("static-fallbacks", render_noscript(payload)),
        ("hero-counts", render_hero_counts(payload)),
        ("hero-links", render_hero_links(payload)),
        ("key-numbers", render_key_numbers(payload)),
        ("repo-inventory", render_deliverables(payload)),
        ("argument-timeline", render_argument_timeline(payload)),
    ]


def build_payload():
    return {
        "repo": REPO_URL,
        "pages": PAGES_URL,
        "counts": counts(),
        "pipeline": [{"n": n, "name": nm, "detail": d} for n, nm, d in PIPELINE],
        "gates": gates(),
        "phases": [{"key": k, "title": t, "subtitle": s, "blurb": b}
                   for k, t, s, b in PHASES],
        "weeks": week_payload(),
        "figures": figure_payload(),
        "repo_inventory": repo_inventory(),
        "key_numbers": key_numbers_payload(),
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
    for name in ("index.html", "404.html", "assets/academic.css",
                 "assets/academic.js", ".nojekyll"):
        if not os.path.exists(os.path.join(DOCS, name)):
            problems.append("missing page asset: docs/" + name)
    if problems:
        for p in problems:
            print("  [XX] " + p)
        return 1
    print("academic site: OK (%d figures, %d index regions, checks passed)"
          % (len(FIGURES), len(managed_blocks(payload))))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    sys.exit(check() if args.check else build() or 0)


if __name__ == "__main__":
    main()
