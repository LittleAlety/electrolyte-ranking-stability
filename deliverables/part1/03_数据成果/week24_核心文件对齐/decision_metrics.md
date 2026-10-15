# Week 24 决策指标实测（核心文件 v2 §9.2 / §9.4 / §10.1）

## 论文可直接使用的小结（≤200 字）

**按 §9.2 重算五台阶×两轴×两池共 20 个 (台阶,轴) 组合，f_robust_inv 在 z=1 与 1.96 两档共 40 个数全为 0：无 §22.3 情形 C。§9.4 逐对概率显示 C0→C1 还原轴 45 对中 82% 为 unresolved，τ_b=−0.467 的换序全落在 unresolved 对上（§22.7 情形 G），且该轴 11/12 还原态为 Li 中心还原（§22.4 情形 D）。带 CI 的 Jaccard 仅见 Stage 7。**

> 去空白字符数：196

## 表 1  十级台阶 f_robust_inv 与 Top-k Jaccard（common10，N=10，45 对）

| 台阶 | 轴 | N | τ_b | f_unresolved(后层, z=1) | f_robust_inv(z=1) | f_robust_inv(z=1.96) | J_10% | J_20% | J_30% |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P0_to_P1 | oxidation | 10 | 0.7333 | 0.1333 | 0 | 0 | 0 | 0 | 0.5 |
| P0_to_P1 | reduction | 10 | 0.6 | 0.7333 | 0 | 0 | 0 | 1 | 0.5 |
| P1_to_P2 | oxidation | 10 | 0.9111 | 0.1111 | 0 | 0 | 1 | 1 | 0.5 |
| P1_to_P2 | reduction | 10 | 0.7778 | 0.2 | 0 | 0 | 0 | 1 | 0.5 |
| G1_to_G2 | oxidation | 10 | 0.9556 | 0.02222 | 0 | 0 | 1 | 1 | 1 |
| G1_to_G2 | reduction | 10 | 0.8667 | 0.06667 | 0 | 0 | 1 | 1 | 0.5 |
| C0_to_C1 | oxidation | 10 | 0.6889 | 0.2 | 0 | 0 | 1 | 1 | 0.5 |
| C0_to_C1 | reduction | 10 | -0.4667 | 0.8 | 0 | 0 | 0 | 0 | 0.2 |
| C1_to_C2 | oxidation | 10 | 0.8667 | 0.08889 | 0 | 0 | 1 | 1 | 1 |
| C1_to_C2 | reduction | 10 | 0.2889 | 0.3556 | 0 | 0 | 0 | 0 | 0.5 |

> 全台阶全轴 20/20 个 (population, 台阶, 轴) 组合在 z=1 与 z=1.96 两种口径下 f_robust_inv 均为 0：表中 common10（10 个组合）与各台阶 native 分子池（N=18/18/12/10/12，10 个组合）一致，合计 40 个数无一非零。这是核心文件 §22.3 情形 C「NOT OBSERVED」的直接证据（未放宽任何阈值）。

> Jaccard 口径：stage10_ladder 原生仅给出 J_20%；J_10 / J_30 由同一冻结逐分子值按 §10.1 重算（k = round(0.1/0.2/0.3·N) = 1/2/3），未用其它量冒充。带 bootstrap CI 的 Jaccard 仅见 Stage 7（任务 M/E/C）。

## 表 2  关键分子对 p_ij（§9.4；common10 与 native 两池；p_ij = Φ(ΔP_ij/σ_ij)，σ_ij = |δ_i−δ_j|/√2）

| 池 | 台阶 | 轴 | 选取规则 | i | j | ΔP_ij / eV | σ_ij / eV | ΔP/σ | p_ij | 判决 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| common10 | P0_to_P1 | oxidation | Top-20% 边界对 (rank 2 vs 3) | SN | EC | 0.8345 | 0.9304 | 0.897 | 0.8151 | unresolved |
| common10 | P0_to_P1 | reduction | Top-20% 边界对 (rank 2 vs 3) | DME | DMC | 0.2646 | 4.431 | 0.05973 | 0.5238 | unresolved |
| common10 | P1_to_P2 | oxidation | Top-20% 边界对 (rank 2 vs 3) | SN | DMC | 0.8441 | 0.1271 | 6.643 | 1 | i>j |
| common10 | P1_to_P2 | reduction | Top-20% 边界对 (rank 2 vs 3) | DOL | SL | 0.2287 | 0.6227 | 0.3673 | 0.6433 | unresolved |
| common10 | G1_to_G2 | oxidation | Top-20% 边界对 (rank 2 vs 3) | SN | EC | 0.76 | 0.05272 | 14.42 | 1 | i>j |
| common10 | G1_to_G2 | reduction | Top-20% 边界对 (rank 2 vs 3) | DME | AN | 0.4518 | 0.05733 | 7.881 | 1 | i>j |
| common10 | C0_to_C1 | oxidation | Top-20% 边界对 (rank 2 vs 3) | SN/m1 | DOL/m1 | 0.7824 | 0.9745 | 0.8029 | 0.789 | unresolved |
| common10 | C0_to_C1 | reduction | Top-20% 边界对 (rank 2 vs 3) | SL/m1 | DME/m1 | 0.08915 | 0.599 | 0.1488 | 0.5592 | unresolved |
| common10 | C0_to_C1 | reduction | DeltaP/sigma 最大 3 对 | AN/m1 | DME/m1 | -0.4574 | 0.003981 | -114.9 | 0 | i<j |
| common10 | C0_to_C1 | reduction | DeltaP/sigma 最大 3 对 | GBL/m1 | SL/m1 | -0.36 | 0.03013 | -11.95 | 0 | i<j |
| common10 | C0_to_C1 | reduction | DeltaP/sigma 最大 3 对 | DMC/m1 | DME/m1 | -0.5755 | 0.06364 | -9.042 | 0 | i<j |
| common10 | C0_to_C1 | reduction | 前后层符号翻转对 | DMC/m1 | SL/m1 | -0.6646 | 0.6626 | -1.003 | 0.1579 | unresolved |
| common10 | C0_to_C1 | reduction | 前后层符号翻转对 | AN/m1 | SL/m1 | -0.5466 | 0.603 | -0.9065 | 0.1823 | unresolved |
| common10 | C0_to_C1 | reduction | 前后层符号翻转对 | DME/m1 | DOL/m1 | 0.5863 | 0.7026 | 0.8345 | 0.798 | unresolved |
| common10 | C0_to_C1 | reduction | 前后层符号翻转对 | DMC/m1 | DMSO/m1 | -0.2987 | 0.4886 | -0.6113 | 0.2705 | unresolved |
| common10 | C0_to_C1 | reduction | 前后层符号翻转对 | DMC/m1 | TMP/m1 | -0.285 | 0.4815 | -0.5919 | 0.2769 | unresolved |
| common10 | C1_to_C2 | oxidation | Top-20% 边界对 (rank 2 vs 3) | SN/m1 | DOL/m1 | 0.4652 | 0.2243 | 2.074 | 0.981 | i>j |
| common10 | C1_to_C2 | reduction | Top-20% 边界对 (rank 2 vs 3) | EC/m1 | SL/m1 | 0.1555 | 0.3581 | 0.4343 | 0.668 | unresolved |
| common10 | C1_to_C2 | reduction | DeltaP/sigma 最大 2 对 | DMC/m1 | TMP/m1 | -0.2936 | 0.006093 | -48.19 | 0 | i<j |
| common10 | C1_to_C2 | reduction | DeltaP/sigma 最大 2 对 | DOL/m1 | EC/m1 | -0.3454 | 0.01475 | -23.41 | 0 | i<j |
| native | P0_to_P1 | oxidation | Top-20% 边界对 (rank 4 vs 5) | EC | DMC | 0.1892 | 0.09189 | 2.059 | 0.9803 | i>j |
| native | P0_to_P1 | reduction | Top-20% 边界对 (rank 4 vs 5) | DEC | EMC | 0.05209 | 0.02228 | 2.338 | 0.9903 | i>j |
| native | P1_to_P2 | oxidation | Top-20% 边界对 (rank 4 vs 5) | DMC | TMP | 0.03222 | 0.3471 | 0.09284 | 0.537 | unresolved |
| native | P1_to_P2 | reduction | Top-20% 边界对 (rank 4 vs 5) | SL | DMC | 0.04957 | 0.3794 | 0.1307 | 0.552 | unresolved |
| native | G1_to_G2 | oxidation | Top-20% 边界对 (rank 2 vs 3) | SN | EC | 0.76 | 0.05272 | 14.42 | 1 | i>j |
| native | G1_to_G2 | reduction | Top-20% 边界对 (rank 2 vs 3) | DME | EMC | 0.3902 | 0.0156 | 25.02 | 1 | i>j |
| native | C0_to_C1 | oxidation | Top-20% 边界对 (rank 2 vs 3) | SN/m1 | DOL/m1 | 0.7824 | 0.9745 | 0.8029 | 0.789 | unresolved |
| native | C0_to_C1 | reduction | Top-20% 边界对 (rank 2 vs 3) | SL/m1 | DME/m1 | 0.08915 | 0.599 | 0.1488 | 0.5592 | unresolved |
| native | C1_to_C2 | oxidation | Top-20% 边界对 (rank 2 vs 3) | SN/m1 | DOL/m1 | 0.4652 | 0.2243 | 2.074 | 0.981 | i>j |
| native | C1_to_C2 | reduction | Top-20% 边界对 (rank 2 vs 3) | EC/m1 | SL/m1 | 0.1555 | 0.3581 | 0.4343 | 0.668 | unresolved |

> 判决：p_ij>0.9 记 i>j，p_ij<0.1 记 i<j，0.1≤p_ij≤0.9 记 unresolved；§9.4 的 0.9/0.1 阈值等价于 z=Φ⁻¹(0.9)=1.282。i>j 表示 i 在 p_red=-EA、higher_is_better 口径下更优。

## 表 3  一致性检查：p_ij 导出 unresolved vs 既有 f_unresolved / τ_b（common10）

| 台阶 | 轴 | τ_b | 符号翻转对数 | 其中 unresolved | p 导出 unresolved | 闭式 f_unres(z=1.2816) | 既有 f_unres(后层, z=1) | 偏差 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P0_to_P1 | oxidation | 0.7333 | 6 | 6 | 0.2 | 0.2 | 0.1333 | 0.06667 |
| P0_to_P1 | reduction | 0.6 | 9 | 9 | 0.7778 | 0.7778 | 0.7333 | 0.04444 |
| P1_to_P2 | oxidation | 0.9111 | 2 | 2 | 0.1111 | 0.1111 | 0.1111 | 0 |
| P1_to_P2 | reduction | 0.7778 | 5 | 5 | 0.2444 | 0.2444 | 0.2 | 0.04444 |
| G1_to_G2 | oxidation | 0.9556 | 1 | 1 | 0.02222 | 0.02222 | 0.02222 | 0 |
| G1_to_G2 | reduction | 0.8667 | 3 | 3 | 0.06667 | 0.06667 | 0.06667 | 0 |
| C0_to_C1 | oxidation | 0.6889 | 7 | 7 | 0.2889 | 0.2889 | 0.2 | 0.08889 |
| C0_to_C1 | reduction | -0.4667 | 33 | 33 | 0.8222 | 0.8222 | 0.8 | 0.02222 |
| C1_to_C2 | oxidation | 0.8667 | 3 | 3 | 0.1111 | 0.1111 | 0.08889 | 0.02222 |
| C1_to_C2 | reduction | 0.2889 | 16 | 16 | 0.4444 | 0.4444 | 0.3556 | 0.08889 |

> p 导出 unresolved（0.1<p<0.9）与「闭式 f_unresolved(z=1.2816)」逐点相等（偏差 <= 1e-15），因为 §9.4 的 0.9/0.1 阈值等价于 z=Φ⁻¹(0.9)=1.2816；这与既有的 z=1（prereg 主口径）和 z=1.96（敏感性）不是同一口径，故「既有偏差」非零是口径差而非矛盾。
> 偏差量化：p 导出 unresolved 与既有 z=1 主口径的最大差为 0.08889（4/45 对），与既有 z=1.96 的最大差为 0.1778；与等价口径 z=1.2816 的逐点偏差为 0。

## Stage 6 原生 p_ij 口径对照（同一 §9.4 的 0.9/0.1 阈值，不同 σ 定义）

- Stage 6（outputs/week6/stage6_decision_stability.json，scenario=z_only）只对 P0_to_P1、P1_to_P2、C0_to_C1 三个台阶原生给出 prob_undecided_fraction：P0_to_P1/oxi = 0.9848 (n=12)；P0_to_P1/red = 1 (n=12)；P1_to_P2/oxi = 0.9545 (n=12)；P1_to_P2/red = 1 (n=12)；C0_to_C1/oxi = 1 (n=10)；C0_to_C1/red = 1 (n=10)。
- 该实现用 σ_ij² = (δ_i² + δ_j²)/2（逐分子位移的方差和），而 §9.1 与本脚本用 σ_ij = |δ_i − δ_j|/√2；同一台阶下前者 unresolved 比例可达 1.00，后者为 0.111–0.822（见表 3）。
- G1_to_G2 与 C1_to_C2 两个台阶不存在任何原生 p_ij（Stage 6 未覆盖）。
- 结论：p_ij 的数值强依赖 σ 口径，论文引用时必须同时声明 σ 定义；本报告一律用 §9.1 闭式。

## 数据核查与输入 SHA256

- 全部 40 个 f_robust_inv 数值（2 z × 2 population × 10 点）在本数据集中为 0；本脚本未放宽任何阈值来制造非零值。
- stage10_ladder 原生只存储 Jaccard_20；J_10 / J_30 由本脚本用同一冻结逐分子值重算（非伪造、未替换其它量）。
- 带 bootstrap CI 的 Jaccard 仅存在于 Stage 7（stage7_ml_results.json，任务 M/E/C）；十级台阶本身没有 CI 版 Jaccard。
- 五个台阶在 stage10_ladder 中均有原生 J_20，故「仅 Stage 7 有」的占位标注未启用；本项目 Jaccard 均由逐分子值直接算出。
- p_ij 的 §9.4 阈值 0.9/0.1 等价于 z=1.2816；与既有的 z=1 主口径不是同一 z，因此「既有偏差」反映的是口径差。
- Stage 6 已有原生 p_ij（prob_undecided_fraction），但 sigma 口径为 (delta_i^2+delta_j^2)/2，与本脚本/§9.1 的 |delta_i-delta_j|/sqrt(2) 不同；G1→G2 与 C1→C2 两个台阶则完全无原生 p_ij。

| 输入（只读） | bytes | SHA256（前 16 位） |
| --- | --- | --- |
| 核心文件/ranking-electrolyte-materials-v2.md | 54147 | e55c1b07a127ef7d |
| outputs/week9/stage10_ladder.json | 36096 | 3eb6b36d5622ec0e |
| outputs/week9/stage10_ladder.csv | 8084 | c4cdec417373fcd6 |
| outputs/week10/stage11_sigma_anatomy.json | 140446 | 0057eab40133c3e1 |
| outputs/week4/p1_decision_stability.json | 54834 | 9fa78cd9f5d81485 |
| outputs/week4/p2_decision_stability.json | 120081 | 38eb6af12228a520 |
| outputs/week4/p1_core_set_derived.csv | 5642 | 2987f8771b722d5a |
| outputs/week4/p2_environment_effects.csv | 4862 | b74de81a66979f04 |
| outputs/week4/t2_opt_freq_summary.json | 9009 | eb383c6c1760cd04 |
| outputs/week5/c1_decision_stability.json | 17846 | da9df806884640d4 |
| outputs/week5/c1_coord_shifts.csv | 2523 | 1f9597ba376ffb19 |
| outputs/week6/delta_m_frozen.json | 11695 | eda08587448aec62 |
| outputs/week6/stage6_decision_stability.json | 366787 | 3e9864cd9427ed1b |
| outputs/week6/stage6_decision_stability.csv | 6299 | 689a86e421e945a5 |
| outputs/week7/stage7_ml_results.json | 608857 | 5b134864b66b7567 |
| outputs/week8/stage9_decision_stability.csv | 1285 | 2ce2d1aff0090d87 |
| outputs/week8/stage9_shell_shifts.csv | 2867 | ce206cbd8c7ce810 |

> 验证：重算值与 stage10_ladder 既有值的最大绝对偏差 —— f_robust_inv(z=1) 0、f_robust_inv(z=1.96) 0、f_unresolved_after(z=1) 0、J_20% 0；σ 闭式 vs 库函数 1.11e-15；关键对判决与符号不一致数 0。

> p_ij 方法核验（C0_to_C1 / 还原轴，200000 次 Monte-Carlo）：与闭式最大绝对偏差 1.93e-03，在 0.9 与 0.1 两个判决阈值上均 0 分歧。

