# 电解液溶剂 ranking 稳定性项目 —— 结题论文数字档案

> 只读汇编。所有数字均从仓库产物（`outputs/`、`docs/`、`config/`、`data/`、`docs/assets/data.js`）
> 原样抄录，**未做任何重算或推测**；每行末注明出处（仓库相对路径）。
> 单位已标注：eV / meV / Å / % / kJ·mol⁻¹。
> 生成日期：2026-10-02。仓库根：`E:\Claude Code\电解液溶剂-HB\电解液溶剂HB-Code`。

## 1. 体系与规模

| 项 | 值 | 出处 |
| --- | --- | --- |
| core set 分子数 | 18（C01–C18） | `data/metadata/core_set.csv`（18 行）；`成果输出/数据结果汇总.md` §1 |
| broad pool 分子数 | 40（B01–B40） | `data/metadata/broad_pool.csv`（40 行） |
| 合并池 | 58 | `成果输出/数据结果汇总.md` §1 |
| 结构家族（core） | 8：linear_carbonate 3 / cyclic_carbonate 4 / ether 3 / ester 3 / sulfone 1 / sulfoxide 1 / nitrile 2 / phosphate 1 | `data/metadata/core_set.csv` 计数 |
| 结构家族（broad） | 11：core 8 家族 + sulfite 1 / sultone 1 / siloxane 2 | `data/metadata/broad_pool.csv` 计数；`data/metadata/chemical_space_metadata.md` §3 |
| 受控词表 family 取值 | 11 个（闭集） | `config/scientific_definitions.yaml:controlled_vocabularies.family.values` |
| P0 层 | GFN2-xTB 6.7.1pre，气相；Koopmans `p0_ox = -eps_HOMO`、`p0_red = +eps_LUMO` | `成果输出/数据结果汇总.md` §1 |
| P1 层 | ORCA 6.1.1，r2SCAN-3c，气相，ΔSCF 三态垂直量 | 同上 |
| P2 层 | ORCA 6.1.1，r2SCAN-3c + CPCM(SMD, 乙腈) | 同上 |
| 几何 G1 | GFN2-xTB 单构象优化几何（`outputs/_week3_scratch/<mol>/xtbopt.xyz`），全层共享 | `成果输出/数据结果汇总.md` §0 第 4 条 |
| 几何 G2 | r2SCAN-3c `Opt+Freq` 驻点（12 分子审计子集，唯一变量 = 几何） | `成果输出/数据结果汇总.md` §0 / §2 Week 4 |
| ORCA 作业产物计数 `.out` | 1535 | `docs/assets/data.js:counts.orca_out` |
| 站点其它计数 | weeks 23 / figures 47 / scripts 108 / test_files 57 / tests_passed 1194 | `docs/assets/data.js:counts` |
| z 因子（主判据） | 1.0；z = 1.96 作为并列敏感性 | `config/prereg.yaml:pair_comparison.z_factor.value`；`成果输出/数据结果汇总.md` §0 第 3 条 |
| Top-k 比例 | fractions 0.10 / 0.20 / 0.30；`k_abs = max(1, floor(frac*N + 0.5))` | `config/prereg.yaml:top_k` |
| Top-k 绝对 k（core N=18） | k = 2 / 4 / 5 | `config/prereg.yaml:top_k.core_set_k_abs` |
| Top-k 绝对 k（broad N=40） | k = 4 / 8 / 12 | `config/prereg.yaml:top_k.broad_pool_k_abs` |
| 材料阈值 | 1 meV = 0.001 eV | `outputs/week23/targeted_two_guess.json:material_ev`；图注见 `成果输出/数据结果汇总.md` §5（F32/F34 行） |
| delta_default / floor | 2.0 kJ·mol⁻¹（预注册默认）；floor 0.05 eV = 4.8242666 kJ·mol⁻¹ | `config/prereg.yaml:pair_comparison.delta_m.delta_default`；`outputs/week6/delta_m_frozen.json:rule_text` |
| 审计子集（12 分子） | EC、PC、DMC、EMC、DME、DOL、GBL、AN、SN、DMSO、SL、TMP | `outputs/week6/delta_m_frozen.json:audit_subset` |
| 条件态 | C0 = 自由分子 M；C1 = `[LiM]+`（week5）；C2 = 显式微溶剂化 cluster（week8） | `成果输出/数据结果汇总.md` §1 |
| main 化学空间依据 | v2 §3/§4/§5/§6/§8 + §19 Stage 0 | `config/scientific_definitions.yaml:provenance` |

## 2. 锚点与方法误差

| 项 | 值 | 出处 |
| --- | --- | --- |
| 外部气相锚点样本 | n = 12（IP，优先实验测定） | `outputs/week4/p1_anchor_comparison.json:n_with_anchor` |
| P0 Koopmans vs 锚点 | MAE **1.3774 eV**；bias +1.2790 eV；max\|err\| 2.0023 eV；τ_b **0.6061**（CI95 0.1639–0.9016） | `outputs/week4/p1_anchor_comparison.json:P0_koopmans_xTB` |
| GFN2-xTB ΔSCF vs 锚点 | n = 10；MAE **4.4811 eV**；τ_b **0.9111** | `outputs/week4/p1_anchor_comparison.json:GFN2_dSCF_xTB` |
| P1 r2SCAN-3c vs 锚点 | MAE **0.251 eV**；τ_b **0.727**（n = 12 口径） | `成果输出/数据结果汇总.md` §3.1 |
| 三臂对齐后（Week 21，n = 10） | P0 Koopmans MAE **1.349 eV** / τ_b 0.6889；GFN2 ΔSCF MAE **4.481 eV** / τ_b 0.9111；P1 MAE **0.255 eV** / τ_b 0.7778 | `成果输出/数据结果汇总.md` §2 Week 21 |
| 配对 Δτ_b（GFN2 − P1） | **+0.1333**；95% CI [−0.200, +0.550]；精确配对置换 p = **0.8049**；CI 跨 0 | 同上 |
| P1 下气相阴离子不束缚个数 | **18**（P1 54/54 成功，`unbound_anion = 18`） | `成果输出/数据结果汇总.md` §2 Week 4、§3.3 |
| 方法审计（12 分子，GFN2-xTB）气相阴离子不束缚 | **2** | `成果输出/数据结果汇总.md` §2 Week 2 |
| T5 加弥散（def2-TZVPD vs r2SCAN-3c 基组） | 气相 EA 系统性下拉 **0.34–1.60 eV**，4 分子 × 3 臂均不翻转符号；作业 24 个 | `outputs/week4/t5_diffuse_control_summary.json`；`成果输出/数据结果汇总.md` §3.4 |
| AN / DMSO 锚点量级 | AN **0.011 eV**、DMSO **0.014 eV**（比 DFT 误差棒 ~0.1–0.2 eV 低两个数量级） | `outputs/week4/t5_diffuse_control_summary.json:question`；`成果输出/数据结果汇总.md` §3.4 |

## 3. 台阶（位移与排序稳定性）

**约定**：Stage 10 冻结约定 `p_red = -EA`、两轴 `higher_is_better = True`，故下表还原轴数值 = **−ΔEA**。
共同子集 = 10 分子（AN、DMC、DME、DMSO、DOL、EC、GBL、SL、SN、TMP）。
数据源（整表）：`outputs/week9/stage10_ladder.json:ladder`（population = native）。

| 台阶 | 唯一变量 | 轴 | n | 位移均值 (eV) | 位移 std (eV) | τ_b | Top-10% | Top-20% | f_unresolved(后) | f_robust_inv |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P0→P1 | 电子结构方法 | 氧化 | 18 | −1.5496 | 0.7352 | 0.6732 | 0.000 | 0.500 | 0.1569 | 0.000 |
| P0→P1 | 电子结构方法 | 还原 | 18 | +7.5919 | 2.2088 | 0.5948 | 1.000 | 0.500 | 0.6209 | 0.000 |
| P1→P2 | 环境（气相→SMD 乙腈） | 氧化 | 18 | −2.3934 | 0.3018 | 0.8954 | 1.000 | 0.750 | 0.1111 | 0.000 |
| P1→P2 | 环境 | 还原 | 18 | −2.1731 | 0.3205 | 0.6732 | 0.500 | 0.500 | 0.2222 | 0.000 |
| G1→G2 | 几何 | 氧化 | 12 | −0.002274 | 0.05161 | 0.9394 | 1.000 | 1.000 | 0.0303 | 0.000 |
| G1→G2 | 几何 | 还原 | 12 | −0.11776 | 0.07975 | 0.8485 | 1.000 | 1.000 | 0.0606 | 0.000 |
| C0→C1 | 条件态（自由分子→`[LiM]+`） | 氧化 | 10 | +4.8872 | 0.5946 | 0.6889 | 1.000 | 1.000 | 0.2000 | 0.000 |
| C0→C1 | 条件态 | 还原 | 10 | −6.5782 | 0.8323 | **−0.4667** | 0.000 | 0.000 | 0.8000 | 0.000 |
| C1→C2 | 第二溶剂壳 | 氧化 | 10 | −1.6999 | 0.2594 | 0.8667 | 1.000 | 1.000 | 0.0889 | 0.000 |
| C1→C2 | 第二溶剂壳 | 还原 | 10 | +1.1986 | 0.3350 | 0.2889 | 0.000 | 0.000 | 0.3556 | 0.000 |

同一 JSON 的原始口径补充（供论文换算）：P1→P2 ΔIP 均值 −2.393 eV / std 0.293 eV、ΔEA 均值 +2.173 eV / std 0.311 eV（`成果输出/数据结果汇总.md` §2 Week 4）；
C1→C2 ΔIP −1.700 ± 0.259 eV、ΔEA −1.199 ± 0.335 eV（`成果输出/数据结果汇总.md` §2 Week 8）；G1→G2 位移总体标准差 0.049 eV（§2 Week 4）。

| 机制读数 | 值 | 出处 |
| --- | --- | --- |
| ρ(位移 std, τ_b) | **−0.8511** | `outputs/week9/stage10_ladder.json:hypothesis_test` |
| ρ(\|位移均值\|, τ_b) | **−0.5350** | 同上 |
| ρ(位移 std, f_unresolved) | **+0.8936** | 同上 |
| 最尖锐对照（还原轴） | P0→P1 位移 +7.064 eV、std 2.253 eV、τ_b 0.600 vs C0→C1 位移 −6.578 eV、std 0.832 eV、τ_b −0.467 | `成果输出/数据结果汇总.md` §3.2；`outputs/week9/stage10_ladder.json`（common10 行） |
| C0→C1 还原轴 state-identity | 还原态 11/12 为 Li 中心/混合还原 | `成果输出/数据结果汇总.md` §3.2 |
| Stage 6 并入 delta_m 后（P0→P1 氧化） | τ_b 0.667；f_unresolved 0.636；双方均解析 pair **22/66**；同家族 pair f_unresolved = 1.000 | `成果输出/数据结果汇总.md` §3.2、§2 Week 6 |
| Stage 6 还原轴 | 双方均解析 pair = 0，f_robust_inv 分母为 0 ⇒ **不可判定** | `成果输出/数据结果汇总.md` §2 Week 6 |

**第 18 周那级（几何弛豫，Stage 20 Part 1，第六级台阶）**：37 格；Δ = −能量降。
还原支 mean/std/相对散布 = **−1.953 / 0.160 / 0.08**；氧化支 = **−0.610 / 0.315 / 0.52**；
弛豫修正与 ε 几乎无关（逐分子跨 ε 极差中位 **0.0263 eV**、最大 **0.215 eV**（DEC））。
出处：`outputs/week19/stage20_relax_rung.json`；`成果输出/数据结果汇总.md` §2 Week 19、§5（F38 行）。

**第 19/20 周补充（Stage 20 Part 2 / Stage 21）**

| 项 | 值 | 出处 |
| --- | --- | --- |
| xTB 跨方法偏好方向一致 | **33/37 = 89.2%**；\|Δ\| 中位 0.0072 → 0.00021 eV（压掉约 34 倍）；6/37 合并到同一极小点；逐格裁决与 Stage 19 一致 17/37 = 45.9% | `outputs/week19/stage20_xtb_arms.json`；`成果输出/数据结果汇总.md` §2 Week 19、§5（F39 行） |
| Stage 21 Part A（3 格 × 21 帧 = 63 个单点） | EC/cation/eps=5 判 distinct_lower，但路径相对弦最大抬升 **0.00424 eV** = k_B T(0.0257 eV) 的 **16.5%**（过度判定）；2/3 格与 Stage 19 一致 | `outputs/week20/stage21_path_analysis.json`；§2 Week 20、§5（F40 行） |
| Stage 21 Part B 身份阈值重导 | **0.038946**（空档宽 0.000874，无数据点）；borderline 3 格；可测 276 格；闭壳层反例探针 0 格越阈 | `outputs/week20/stage21_protocol.json:threshold`、`closed_shell_probe` |
| Stage 21 Part C 壳层氧化还原弛豫（24 作业） | 氧化轴修正 **−0.4053 ± 0.4102 eV**、ρ = **0.797**；还原轴 **−5.4512 ± 0.6121 eV**、ρ = **−0.790**；排除 0 格 | `outputs/week20/stage21_shell_redox_analysis.json`；§2 Week 20、§5（F41 行） |
| Stage 21 Part D 严格 P2 腿 | 7/54 可回填；氧化轴排序被改写（Top-10% 重叠 **0.000**）、还原轴未被改写 | `outputs/week20/stage21_refill.json`；§2 Week 20 |

## 4. 不确定度（delta_m / sigma_conf / 热修正）

| 项 | 值 | 出处 |
| --- | --- | --- |
| delta_m 氧化 | **0.700245 eV** = 67.5634 kJ·mol⁻¹；主导项 = method | `outputs/week6/delta_m_frozen.json:per_layer.p1.oxidation` |
| delta_m 还原 | **2.074299 eV** = 200.1395 kJ·mol⁻¹；主导项 = method | `outputs/week6/delta_m_frozen.json:per_layer.p1.reduction` |
| 合成规则（docx） | `delta_m = max(构象 90 分位展宽, 跨方法离散度, 0.05 eV floor)` | `outputs/week6/delta_m_frozen.json:rule_text.docx_synthesis` |
| 方法项 sigma_method（P0 口径） | 氧化 0.700245 eV、还原 2.074299 eV | `outputs/week6/delta_m_frozen.json:method_evidence` |
| 方法项 p90\|shift\| | 氧化 1.8387 eV、还原 9.0337 eV | 同上 |
| 构象项 p90（T6） | P0：氧化 0.034970 eV / 还原 0.221170 eV；P1：氧化 0.090746 eV / 还原 0.230267 eV | `outputs/week6/delta_m_frozen.json:conformer_evidence` |
| sigma_conf（T6） | P0：氧化 0.020656 eV / 还原 0.095140 eV；P1：氧化 0.020023 eV / 还原 0.058113 eV | 同上；源 `outputs/week6/t6_conformer_spread.json` |
| floor | 0.05 eV = 4.8242666 kJ·mol⁻¹ | `outputs/week6/delta_m_frozen.json:rule_text` |
| 锚点项 | 不可用：31 行锚点无重复测量（`n_replicated_series = 0`） | `outputs/week6/delta_m_frozen.json:anchors` |
| R9 热修正（xTB，8 分子 × 3 态 = 24 作业） | 氧化 std **0.0581 eV** = delta_m 的 **8.3%**；还原 std **0.0775 eV** = delta_m 的 **3.7%**；2 个带电作业报虚频；Hessian 取在中性 G1 几何 | `outputs/week22/thermal_correction_sample.json:spread`；`成果输出/数据结果汇总.md` §2 Week 22、§7 第 22 条 |
| 亚稳态（moRead）惩罚的规模 | 全核心集最大赤字 **−0.285961 eV**（EMC/anion/eps=1000） | `成果输出/数据结果汇总.md` §2 Week 15 |

## 5. σ 代数（Week 10 / Stage 11）

约定：`delta = P0 - P1`；`p_red = -EA`；`higher_is_better = True`。出处（整节）：`outputs/week10/stage11_sigma_anatomy.json`。

| 项 | 值 |
| --- | --- |
| z_primary / z_sensitivity | 1.0 / 1.96 |
| 临界斜率 √2/z | z = 1 → **1.4142135623730951**；z = 1.96 → **0.7215375318230077** |
| 闭式 T1 | `sigma_ij = abs(delta_i - delta_j)/sqrt(2)`；实测 max\|误差\| **1.1102e-15 eV** |
| 闭式 T2 | 逐对 RMS = 逐分子样本标准差；max 相对误差 **2.6679e-16** |
| T3 刚性偏移不变性 | max\|Δσ\| **8.8818e-16 eV**；max\|Δτ_b\| **0.0**；max\|Δf_unresolved\| **0.0** |
| T4 未解析闭式 | `f_unresolved(z) = Pr(q_ij > sqrt(2)/z)`；与实测 20 点误差 **0.0**（z = 1 与 z = 1.96 都是 0.0） |
| T5 σ² 预算分解 | max 份额误差 **1.7764e-15** |
| ρ(位移 std, τ_b) | **−0.8510678**（n_points = 10） |
| ρ(\|位移均值\|, τ_b) | **−0.5349569** |
| ρ(位移 std, f_unresolved) | **+0.8936211** |
| 带符号斜率预测子 `ols_slope_b` | AUC **1.000**；精确置换 p = **0.0083333**（120 次枚举）；LOO 准确率 1.0；正例 3/10 |
| `abs_ols_slope_b` | AUC **0.9047619**；p = **0.0333333** |
| `sigma2_share_parallel` | AUC **1.000**；p = **0.0083333**；LOO 准确率 0.8 |
| `q_median` | AUC **0.8571429**；p = **0.0583333** |
| N = 10 子抽样 τ_b 抽样标准差 | **0.126390**（2000 次重抽；P0→P1/oxidation；mean 0.671111、p05 0.466667、p95 0.866667） |
| R2 合成相图（Week 21） | max\|Δτ_b\|（纯均值平移）= **0.000**；合成 ρ(std, τ_b) = **−1.000**；合成 ρ(\|mean\|, τ_b) = **0.000** |

## 6. 介电层

| 项 | 值 | 出处 |
| --- | --- | --- |
| Born 形式 mean R²（6 个介电点 + 气相，24 条曲线） | **0.9860794**（min 0.8467822、max 0.9999951）；Onsager mean **0.8779255**（max 0.9900328） | `outputs/week12/stage13_analysis.json:model_comparison` |
| 两参数族 `delta = S(eps-1)/(eps+k)` | R² mean 0.9935486；**k = 0.0779063 ± 0.1004115** | 同上 |
| Born 斜率 | mean **2.3898 eV**（sd 0.2475、min 1.8205、max 2.8359） | 同上 |
| 更早的 5 点版本（20 条曲线，ε = 5…40） | Born mean R² **0.9936240**；Onsager mean **0.8835277**；逐级增量比 r2 1.97547、r3 1.98672 | `outputs/week11/stage12_prescreen.json:dielectric_law`、`checks` |
| T3 bare CPCM ε 扫描 σ_env（氧化轴） | ε=5 → **0.190952 eV**；10 → **0.212531**；20 → **0.223676**；40 → **0.229342** | `outputs/week4/t3_cpcm_eps_scan_summary.json:per_eps` |
| T3 σ_env（还原轴） | ε=5 → **0.197326 eV**；10 → **0.232877**；20 → **0.228720**；40 → **0.233589** | 同上 |
| σ_env 范围（汇总表述） | **0.19–0.24 eV**（位移近乎共同平移） | `成果输出/数据结果汇总.md` §2 Week 4、§7 第 7 条 |
| T3 稳健反转 | two_arm 口径 max f_robust_inv = **0.0000**；multi_source 口径最多 **1/66** 对（分母为两臂都可分辨的 51–60 对，不是 66） | `outputs/week4/t3_cpcm_eps_scan_summary.json:robust_inversion` |
| 幂律 `\|dE\| × eps` | mean_x_epsilon 范围 **2057.05–2178.34 meV**（ε = 5…1000）；prefactor ≈ **2.1 eV/eps** | `outputs/week22/dielectric_limit.json:power_law`；`成果输出/数据结果汇总.md` §2 Week 22、§5（F43 行） |
| ε = 200 残余 | max **19.6171 meV**（PC/anion）、mean **10.8117 meV**；占氧化轴 delta_m 的 **2.80%** | `outputs/week22/dielectric_limit.json:pairs.200`；百分比见 §2 Week 22 与 F43 图注 |
| ε = 1000 残余 | max **3.9286 meV**、mean **2.1618 meV** | 同上 `pairs.1000` |
| ε = 40 残余 | max **96.9918 meV**、mean **53.9036 meV** | 同上 `pairs.40` |
| ε = 200 → 1000 的位移 | **11.3 meV**（EMC 还原轴，默认初猜） | `docs/24_week14_report.md`（§5 表「eps 200 -> 1000 的位移」）；`成果输出/数据结果汇总.md` §2 Week 14（写作 0.0113 eV） |
| 22 点台阶（12 介电 + 10 电子结构） | 只剩 3 个台阶改写清单：P0_to_P1/oxidation、C0_to_C1/reduction、C1_to_C2/reduction；min τ_b = **−0.4667** | `outputs/week12/stage13_analysis.json:rung_ladder`；`成果输出/数据结果汇总.md` §2 Week 12 |
| SMD（乙腈）环境账本 | 氧化位移 **−2.4489 eV** = 介电 −2.5328 + 畸变 +0.0839；还原 **+2.2065 eV** = +2.5632 − 0.3567；畸变抵消介电比 **0.031**（氧化）/ **0.124**（还原） | `成果输出/数据结果汇总.md` §2 Week 12；`outputs/week12/stage13_analysis.json:smd_ledger` |
| 态的刚性偏移项 | SMD CDS 项三态逐点相同：max spread **0.0 eV**；Δ(D4) = Δ(gCP) = **0.0 eV** | `outputs/week12/stage13_analysis.json:smd_ledger`、`ladder_checks` |

## 7. 双初猜与第二解

| 项 | 值 | 出处 |
| --- | --- | --- |
| 90 点双初猜（EMC/DMC/EC × 10 介电 × 3 态 × 2 初猜） | 78 点一致；**12 点 > 1 meV 且全部为负**；反向 0 次；最大惩罚 **0.2860 eV**（EMC 阴离子，ε=1000） | `docs/24_week14_report.md` §1；`成果输出/数据结果汇总.md` §2 Week 14 |
| EMC 还原轴 Born R² | **0.6788 → 0.9556**；一阶差分符号变化 **4 → 0**；阴离子偶极粗糙度 **1.991 → 0.084**；修复后 ρ = **+1.000**（默认初猜 −0.042） | 同上 |
| 全核心集双初猜目录（Stage 16） | 12 分子 × 3 态 × 10 介电 = 360 配对格；328 一致 / 32 个 MORead 更低 / 0 更高；最大赤字 **−0.285961 eV**；10 点阶梯下 5/12 分子存在漏解 | `成果输出/数据结果汇总.md` §2 Week 15 |
| 留出臂（Stage 16 A2） | 6 分子（DEC/EA/FEC/MA/TEGDME/VC）、108 格，`n_ok = 108`、`n_failed = 0` | `outputs/week15/stage16_holdout.json` |
| 身份普查规模（Stage 18） | **414 对** = 发现集 360 + 留出臂 54；可测 **276** 对（66.7%），不可测 138 对（全为闭壳层中性） | `outputs/week17/stage18_identity_census.json`；`outputs/week20/stage21_protocol.json:reach` |
| 身份判据切点 | `charge_l1 > 0.039`；落在空档 (0.038509, 0.039383)，宽 **0.000874** | `outputs/week20/stage21_protocol.json:threshold`；`成果输出/数据结果汇总.md` §2 Week 17 |
| 身份普查 AUC | 可测子集 AUC = **1.000**；发现集混淆 TP 37 / FN 0 / FP 0 / TN 239；留出臂同一刀 AUC = **1.000**；分类与身份一致 414/414 | `成果输出/数据结果汇总.md` §2 Week 17、§5（F34 行） |
| 家族分裂（漏解分布） | ester / nitrile / sulfone / sulfoxide 四家族零漏解；漏解集中 cyclic_carbonate **15**、phosphate **10**、linear_carbonate **10**、ether **2** | 同上 |
| 零成本自诊断规则 `gap_warn_value <= -0.0395` | 发现集 LOO **0.9167**（多数类基线 0.9111，精确 p = **2.56e-19**）；留出臂 54 格 **0.7963**（输给基线 0.9074），5 个真漏解 TP = **0** | `outputs/week17/stage18_selfdiagnosis.json`；同上 |
| 多变量上限（前 3 特征） | LOO AUC **0.836**；留出 **0.833** | 同上 |
| 几何弛豫判决（Stage 19，37 格 × 2 臂 = 74 个 `Opt`） | `still_lower` **5/37**；两解合并 **8/37**；仍两态但偏好反转 **24/37**；全阶段偏好反转 **32** 格 | `outputs/week18/stage19_relax_analysis.json`；`成果输出/数据结果汇总.md` §2 Week 18、§5（F36 行） |
| 几何弛豫量 | \|Δ\| 中位 **0.11983 → 0.00196 eV**（缩小 **61** 倍）；带符号位移 **37/37** 为正；弛豫后仍在阈值以上 **29/37**、贴阈值 **0** 格；`rmsd_same_minimum` **6/37** | 同上；§5（F37 行） |
| xTB 作业数（Stage 20 Part 2） | 74 个（37 格 × 2 臂），气相（无 CPCM） | `outputs/week19/stage20_xtb_arms.json`；§7 第 19 条 |
| NEB 三格（R11，regular NEB，climbing = no） | EC/cation/ε=5：峰高 **0.0001415 eV**（直线界 0.0042449 eV 的 1/30，`bound_ratio` = **29.999**；k_BT 0.0257 eV 的 0.55%）；EC/cation/ε=20：峰高 **5.279e-05 eV**（ratio 0.1507）；TEGDME/anion/ε=20：峰高 **0.6794 eV**（ratio 97.35） | `outputs/week22/neb_refinement.json:cells`；`成果输出/数据结果汇总.md` §5（F44 行） |
| NEB 裁决 | `n_ok` 3/3；与 Stage 21 一致 3/3；与 Stage 19 冲突 **1**（EC/cation/ε=5，Stage 19 判 distinct_lower） | `outputs/week22/neb_refinement.json` |
| 0.02 Å 阈值的误判格 | EC/阳离子/eps=5（Stage 19 RMSD 0.1 Å 判 distinct_lower，NEB 判 one_basin） | `outputs/week22/neb_refinement.json:cells`；`成果输出/数据结果汇总.md` §2 Week 22 |

## 8. Week 23（R5 / R8 / R12）

### 8.1 R8 —— 漏解靶向双腿策略

出处（整节，除注明外）：`outputs/week23/targeted_two_guess.json`。

| 项 | 值 |
| --- | --- |
| 目录规模 | 240 格 = 12 分子 × 10 介电 × 2 轴；材料阈值 0.001 eV；每轴 material cells = 16 |
| 容许量 A_axis（氧化） | **0.152251551 eV**；最坏格 TMP@eps=5；material median 0.134273 eV、p90 0.147105 eV |
| 容许量 A_axis（还原） | **0.285963046 eV**；最坏格 EMC@eps=1000；material median 0.095349 eV、p90 0.282145 eV |
| A_axis / delta_m | 氧化 **21.743%**；还原 **13.786%** |
| 安全定理（原文） | `flip requires abs(d0 - d1) = abs(d0) + abs(d1) > abs(d0), and abs(d0 - d1) <= A_axis, so any pair with abs(d0) >= A_axis cannot flip` |
| 实测翻转数 | 氧化 **19/660**（2.879%）；还原 **21/660**（3.182%）；漏 **0**（`soundness_missed_flips = 0`） |
| 靶向集 / 全部（A_axis 规则） | 氧化 **86/120**（省 **28.333%**）；还原 **116/120**（省 **3.333%**） |
| delta_m 规则靶向 | 两轴都 120/120（省 0%） |
| 事后 delta_star（严格 <） | 氧化 **0.1462918 eV**，靶向 72/120（省 40%），漏 1 对（EMC/TMP@eps=7）；还原 **0.2534220 eV**，靶向 112/120（省 6.667%），漏 1 对 |
| 事后 delta_star（inclusive, `nextafter`） | 氧化 0.1462918 eV（漏 0）；还原 0.2534220 eV（漏 0）；靶向仍 72/112 |
| 协议校验 τ_b（靶向双腿 vs 全双腿） | 10 个 ε 全部 **1.0000** |
| 对照：单腿 vs 全双腿 τ_b 最小值 | 氧化 **0.93939**；还原 **0.87879** |
| Top-k 清单重叠最小值（靶向协议） | top1 / top2 / top4 均 = **1.0** |
| Top-k 清单变体（半宽 = A_axis） | k=1/2：氧化 **10 格（省 91.667%）**、还原 **20 格（省 83.333%）**；k=4：氧化 **40 格（省 66.667%）**、还原 **56 格（省 53.333%）** |
| 决策量口径一致性 | 与 Stage 16 `delta_ev` 的最大偏差 **1.6057e-05 eV**（已断言） |
| 登记状态 | `registered = false`，field = `missed_solution_allowance`；从 `config/prereg.yaml` 读出的 5 个已注册来源：method / functional / basis；conformer ensemble；Li+ motif；continuum dielectric setting；bootstrap resampling |

**预报失败（第 5 节）**

| 项 | 值 |
| --- | --- |
| 发现集描述符 | `gas_small_gap_value`，阈值 **−0.071**；n = 24、正例 5 |
| 发现集成绩 | 样本内准确率 0.833333；平衡准确率 0.673684；LOO 准确率 **0.708333**；多数类基线 **0.791667**；`beats_majority_baseline = false`；精确置换 p = **0.011575** |
| 留出臂 | 6 分子（DEC/EA/FEC/MA/TEGDME/VC）、12 格；准确率 **0.75**；混淆 TP **0** / FP 1 / TN 9 / FN 2 |
| 分臂（事后） | cation：阈值 −0.0315，准确率 0.666667 vs 多数类 1.0（TP 0 / FP 2 / TN 4 / FN 0）；anion：阈值 0.829451，准确率 0.666667 vs 多数类 0.666667（TP 0 / FP 0 / TN 4 / FN 2） |
| 多变量上限 | 2 特征 logistic（`gas_small_gap_value`, `gas_min_spin`）LOO AUC **0.821053**；留出 accuracy 0.75 / AUC 0.85 |
| 上述全部数字的二级来源 | `outputs/week15/stage16_predictor.json` |

### 8.2 R5 —— EC 第三次配位（GFN2-xTB 示意级）

出处（整节）：`outputs/week23/shell3_xtb_sign_test.json`；引擎 GFN2-xTB **6.7.1pre**，14 个作业，
目标 = EC（motif m1，双齿 2×O）；新增结构 `structures/microsolvation/EC_m1_shell3.xyz`。
`level_caveat` 原文：绝对数值**不得**与 `docs/18` 的 r2SCAN-3c 阶梯并列，只有符号与单调性可比。

| n | 参考态 | IP (eV) | EA (eV) | dIP (eV) | dEA (eV) |
| --- | --- | --- | --- | --- | --- |
| 0 | free EC | 15.5898 | 1.7474 | 0.0000 | 0.0000 |
| 1 | `[Li(EC)]+` | 19.4869 | 8.0388 | 3.8970 | 6.2914 |
| 2 | `[Li(EC)2]+` | 17.6048 | 7.4196 | 2.0150 | 5.6722 |
| 3 | `[Li(EC)3]+` | 16.8823 | 7.0836 | 1.2925 | 5.3361 |

| 项 | 值 |
| --- | --- |
| 增量 dd(2→1) | 氧化 **−1.88205 eV**；还原 **−0.61925 eV** |
| 增量 dd(3→2) | 氧化 **−0.72252 eV**；还原 **−0.33603 eV** |
| 符号与幅度判据 | 两轴 `sign_persists = true`、`magnitude_shrinks = true` |
| 比值 dd(3→2)/dd(2→1) | 氧化 **0.383903**；还原 **0.542640** |
| 跨层级无量纲对照 dd(2→1)/dd(1→0) | xTB：氧化 **−0.482942**、还原 **−0.098428** |
| r2SCAN-3c 对照（Stage 9，EC 行，源 `outputs/week8/stage9_shell_shifts.csv`） | dIP shell1 4.320825 / shell2 2.558078（dd = −1.762747，比值 **−0.407965**）；dEA shell1 6.155021 / shell2 4.686471（dd = −1.468550，比值 **−0.238594**） |
| 判定 | `consistent_with_saturation`（与饱和一致，**不构成**饱和的证明；1 个分子、3 个点） |

### 8.3 R12 —— 叙事合成

「哪些层可以不算」的四条合成（闭式判据 `q_ij <= sqrt(2)/z` + 介电层免费 `|dE| x eps ≈ 2.1 eV` +
配位饱和次线性 + 漏解靶向而非翻倍），原文见 `成果输出/数据结果汇总.md` §3.5。

## 9. Gate 状态

| Gate | 状态 | 内容 | 出处 |
| --- | --- | --- | --- |
| Gate 0（定义冻结） | **CLOSED** | 冻结产物 6 个；4 项检查全过；`amendment_log` 为空；`config/prereg.yaml` sha256 = `e89f2e2ab714ac4268d7b695fbb8494b7aef61a68341753cc031b8af0ca5f340` | `outputs/week1/gate0_record.md`；`成果输出/数据结果汇总.md` §2 Week 1、§4 |
| Gate 1（方法 / 锚点） | **NOT CLOSED** | blocker 原文：`Gate 1 ordering-consistency tier (R7): no verified within-series values on file (n_pairs=0); the absolute-calibration level is recorded as a limitation and this tier stays open` | `docs/assets/data.js:gates[1]` |
| 排序一致性级 | `n_pairs = 0`，低于预注册下限 18 | 检查 `data/anchors/within_series_ordering.csv` | `scripts/check_series_rel_ordering.py`；`成果输出/数据结果汇总.md` §4 |
| 绝对标定级 | 溶液相锚点 **31 行**仍为 `est`（升级 exp/calc 的行数 = 0），按 Week 22 R7 记为 **limitation**，不再单列 blocker | `data/anchors/solution_anchor_verification.md` §4.4；`成果输出/数据结果汇总.md` §4、§7 第 6 条 |
| 气相锚点一致性检查 | PASS（`anchors:validate_anchors`） | `docs/assets/data.js:gates[1].checks` |
| 工具链 | xTB found；ORCA found | 同上 |
| Gate 2+ | 未定义 / 未触发 | `成果输出/数据结果汇总.md` §4 |

## 10. 可引用图清单 F0–F46

列表来自 `outputs/figures/` 文件清单（当前 47 个），一句话内容摘抄自
`成果输出/数据结果汇总.md` §5 图注（F0–F46 齐全），逐周 manifest 在 `outputs/figures/figure_manifest_*.md`。

- `F0_project_pipeline.png` **F0**：管线：廉价代理 → 验证目标 → 排序变化 → 机制 → 最小预算（week1）；`F1_chemical_space_coverage.png` **F1**：core set vs broad pool 的结构家族覆盖（week3）
- `F2_p0_distributions_by_family.png` **F2**：P0 代理按家族 / 氟化的分布（week3）；`F3_value_error_vs_rank_error.png` **F3**：值误差 vs 排序误差（中心反直觉结果）（week4）
- `F4_rank_migration_p0_to_p1.png` **F4**：P0 → P1 的排序迁移（week4）；`F5_reduction_axis_koopmans_vs_dscf.png` **F5**：还原轴：Koopmans 连定性都不对（week4）
- `F6_decision_stability_indicators.png` **F6**：Top-k 重叠 / Jaccard 与 pair 分离度（week4）；`F7_shift_structure.png` **F7**：廉价层是「平移的尺子」还是「另一把尺子」（week4）
- `F8_environment_layer_p1_to_p2.png` **F8**：环境层的逐分子气相 → 溶剂位移（week4）；`F9_diffuse_function_control.png` **F9**：同泛函三基组：加弥散下拉 EA 但不翻转符号（week4）
- `F10_cpcm_eps_scan.png` **F10**：介电常数扫描：ΔIP / ΔEA 随 ε 的位移（week4）；`F11_opt_freq_g2_sensitivity.png` **F11**：几何台阶：G1 换 G2 后垂直 IP / EA 的逐分子位移与 σ 对比（week4）
- `F12_li_coordination_c1.png` **F12**：条件态台阶：C0 → C1 的垂直 IP / EA 位移与配体交换量（week5）；`F13_c1_state_identity.png` **F13**：C1 state-identity QC（空穴落在给体原子、电子落在 Li 上）（week5）
- `F14_delta_m_derivation.png` **F14**：delta_m 推导：构象 90 分位 / 方法 pstdev / 0.05 eV 下限与 max 规则（week6）；`F15_stage6_decision_metrics.png` **F15**：Stage 6：三口径 unresolved 比例与 τ_b / Top-20% / f_robust_inv（week6）
- `F16_stage7_direct_vs_shift.png` **F16**：Stage 7：直接学习 vs 条件位移学习（random / group / LOFO）（week7）；`F17_stage8_active_learning.png` **F17**：Stage 8：`n_T → τ_b` 的四条 acquisition 曲线（week7）
- `F18_stage9_explicit_shell.png` **F18**：Stage 9：显式第一溶剂壳的位移、与 C1 的差值与决策指标（week8）；`F19_stage10_ladder.png` **F19**：Stage 10：五级台阶 τ_b / std / \|mean\| / f_unresolved 关系（week9）
- `F20_sigma_anatomy.png` **F20**：Stage 11 σ 解剖：(a) T1 恒等式 (b) q_ij 分布与临界斜率 (c) 闭式 vs 实测 (d) 预测子 AUC（week10）；`F21_sigma_controls.png` **F21**：Stage 11 反事实对照：线性位移 / Lipschitz / 拉伸 / 白噪声 / 刚性偏移 / 子集规模（week10）
- `F22_dielectric_scaling.png` **F22**：Stage 12：介电自相似（Born 线性轮廓、增量比、形状不变性、外推检验）（week11）；`F23_prescreening.png` **F23**：Stage 12：事前预警（预算曲线、b_hat 分布、试点散点、判据平面）（week11）
- `F24_dielectric_limit.png` **F24**：Stage 13：介电极限七级曲线与 Born / Onsager / 两参数族对照（week12）；`F25_environment_ledger.png` **F25**：Stage 13：环境账本（介电项 + 溶质畸变项分解；CDS 项的态刚性）（week12）
- `F26_distortion_attribution.png` **F26**：Stage 14：逐态畸变惩罚与 D_neutral 对自身偶极的关系（week13）；`F27_emc_outlier.png` **F27**：Stage 14：EMC 离群点的九点阶梯、SCF 解分支与 Born R² 收敛（week13）
- `F28_two_guess_protocol.png` **F28**：Stage 15：双初猜协议（能量差分档、EMC 偶极双支、导体极限、外推缺口）（week14）；`F29_diffuseness_descriptor.png` **F29**：Stage 15：电子弥散度描述符（spin_maxfrac、参与比、留一 R²、域检验）（week14）
- `F30_two_guess_catalogue.png` **F30**：Stage 16：12 × 3 × 10 双初猜目录网格与最大赤字（week15）；`F31_apriori_warning_rule.png` **F31**：Stage 16：事前预警规则（单变量 AUC、冻结阈值、留出臂逐行、多变量上限）（week15）
- `F32_stage17_contamination.png` **F32**：Stage 17 Part A：亚稳态污染上限（delta = p2_moread − p2_default，材料阈值 1 meV 参考带）（week16）；`F33_stage17_solution_identity.png` **F33**：Stage 17 Part B：两个 SCF 解的电子结构身份（week16）
- `F34_stage18_identity_census.png` **F34**：Stage 18 Part A：charge_l1 双峰、切点空隙、家族分裂（week17）；`F35_stage18_selfdiagnosis.png` **F35**：Stage 18 Part B：零成本自诊断（small-gap 警告的单边可用性）（week17）
- `F36_stage19_relax_outcomes.png` **F36**：Stage 19：弛豫裁决（distinct_lower 5 / distinct_higher 24 / same_higher 8）（week18）；`F37_stage19_identity_geometry.png` **F37**：Stage 19：身份与几何（charge_l1 前后、RMSD 漂移、能量降配对、自旋中心迁移）（week18）
- `F38_stage20_relax_rung.png` **F38**：Stage 20 Part 1：第六级台阶（弛豫位移对 ε、同尺子对比、\|mean\|–std 平面）（week19）；`F39_stage20_xtb_arms.png` **F39**：Stage 20 Part 2：xTB 跨方法检验（RMSD、偏好方向、能量差读数、单臂漂移）（week19）
- `F40_stage21_path_profiles.png` **F40**：Stage 21 Part A：临界带三格直线内插能量剖面（week20）；`F41_stage21_shell_redox.png` **F41**：Stage 21 Part C：`[Li(M)2]+` 氧化/还原态弛豫位移修正（week20）
- `F42_sigma_synthetic_phase_diagram.png` **F42**：Stage 22 R2：合成（均值, 离散度）相图，τ_b 只随 std 变（week21）；`F43_dielectric_limit_check.png` **F43**：Stage 23 R4b：`\|dE\| × eps` 幂律与 eps = 200 残余 19.62 meV（week22）
- `F44_neb_refinement.png` **F44**：Stage 23 R11：三格临界格真 NEB 精修（峰高 vs 直线界）（week22）；`F45_targeted_two_guess.png` **F45**：Stage 24 R8：容许量 A_axis、安全定理、靶向代价、Top-k 变体（week23）
- `F46_shell3_saturation.png` **F46**：Stage 24 R5：EC 第三配位壳 n = 0→3 阶梯与增量递减（week23）

## 11. 未找到 / 需注意的条目

1. **ORCA「作业总数」的官方登记值**：仓库没有逐周作业数汇总表，只有 `.out` 文件计数 **1535**（`docs/assets/data.js:counts.orca_out`）。论文若要写「总作业数」需注明这是文件计数口径，且未扣除失败/重试。
2. **「结构家族数」的单一数字不存在**：core 8、broad 11、受控词表 11，三个数都在，但没有一个「本项目家族数 = N」的冻结字段（`config/scientific_definitions.yaml` 只给取值列表）。
3. **P1 锚点 MAE / τ_b 有两个口径**：n = 12 时 0.251 eV / 0.727（`成果输出/数据结果汇总.md` §3.1），n = 10 对齐时 0.255 eV / 0.7778（§2 Week 21）。档案并列给出，无单一冻结值。
4. **P0 / GFN2 ΔSCF 的 τ_b 同样有两口径**：0.606 / 0.911（n = 12）与 0.6889 / 0.9111（n = 10，Week 21）。
5. **还原轴 ΔEA 的符号**：`outputs/week9/stage10_ladder.json` 用 `p_red = -EA` 约定，还原轴数值 = −ΔEA；Week 4 / Week 8 报告给的是原始 ΔEA。两者不可直接混引。
6. **σ_env 的「0.19–0.24 eV」是区间表述**：精确逐 ε 值见本档案 §6（`outputs/week4/t3_cpcm_eps_scan_summary.json`），无单一标量。
7. **R9 热修正的 8.3% / 3.7%**：来自 `成果输出/数据结果汇总.md` §2 Week 22 的比例表述；JSON 只给 std（0.0581 / 0.0775 eV）与 delta_m，比例未在产物中写成字段。
8. **R8 的「跨层级无量纲对照」在 r2SCAN-3c 侧只有 2 个壳层**（`n_shells_available = 2`），第 3 层无对照，故氧化轴可比、还原轴只能作提示（`outputs/week23/shell3_xtb_sign_test.json:stage9_reference`）。
9. **Week 23 的 R12 结论没有独立 JSON 产物**：只有叙事段落位于 `成果输出/数据结果汇总.md` §3.5，其三个支撑量分别来自 `outputs/week10/stage11_sigma_anatomy.json`、`outputs/week22/dielectric_limit.json`、`outputs/week23/shell3_xtb_sign_test.json`。
10. **`docs/33_week22_report.md` §5 与冻结状态不一致**：该报告写「R7 属批次 C，本轮未执行」，而 Gate 1 现已收敛为单一 `series_rel_ordering` blocker（`docs/assets/data.js:gates[1]`）。引用 Week 22 报告该句需订正。
