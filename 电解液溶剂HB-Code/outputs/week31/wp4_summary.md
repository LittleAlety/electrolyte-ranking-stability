# Week 31 / WP4：把排序变化转成可辩护的筛选决策（RQ3）

> 阶段：下一阶段实施方案 WP4（RQ3）。产物目录 `outputs/week31/`，交付镜像
> `..\成果输出（part2）\week31/`。本文件由 `scripts/build_week31_wp4_decision_identifiability.py`
> 确定性生成，`--check` 逐字节复核。**零新增电子结构计算**：唯一输入是 Week 28 冻结主表。

## 0. 一句话结论

对每一个 Top-k 筛选决策，都可以给出「确定选择 / 边界候选 / 证据不足」的区分，而且这个区分
**依赖不确定性假设与分层算法**：同一份数据下，「端点区间抽样」的确定选择与「rung-wise 已解析」
的保守选择在 9 个 (组,k) 上给出不同答案。因此 WP4 不能只报 f_robust_inv —— 它在 z=1.0 下恒为 0，是 sigma=|d_upper-d_lower|/sqrt(2) 与 z>1/sqrt(2) 的**代数必然**，不是稳定性证据。

## 1. 三层评价总表（k_fraction=0.2）

| 对比 | scope | 轴 | n | τ_b | ρ | f_unres(lo) | f_unres(up) | 决策重叠 | regret(eV) | 选择不确定度 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P0_to_P1v | all | oxidation | 18 | 0.673 | 0.804 | 0.359 | 0.157 | 0.500 | 0.6563 | 0.734 |
| P0_to_P1v | all | reduction | 18 | 0.595 | 0.800 | 0.170 | 0.621 | 0.500 | 0.2630 | 0.449 |
| P1v_to_P1a | all | oxidation | 12 | 0.788 | 0.923 | 0.121 | 0.121 | 1.000 | 0.0000 | 1.000 |
| P1v_to_P2a | all | oxidation | 18 | 0.895 | 0.963 | 0.092 | 0.111 | 0.750 | 0.0272 | 0.637 |
| P1v_to_P2a | all | reduction | 18 | 0.673 | 0.827 | 0.235 | 0.222 | 0.500 | 0.1752 | 0.433 |
| P1v_to_P2eps10 | all | oxidation | 12 | 0.909 | 0.972 | 0.076 | 0.136 | 1.000 | 0.0000 | 0.758 |
| P1v_to_P2eps10 | all | reduction | 12 | 0.848 | 0.923 | 0.091 | 0.258 | 1.000 | 0.0000 | 0.508 |
| P0_to_P2a | all | oxidation | 18 | 0.673 | 0.814 | 0.301 | 0.229 | 0.500 | 0.5448 | 0.393 |
| P0_to_P2a | all | reduction | 18 | 0.791 | 0.920 | 0.105 | 0.680 | 0.750 | 0.0445 | 0.729 |
| C0_to_C1 | all | oxidation | 10 | 0.689 | 0.770 | 0.178 | 0.200 | 1.000 | 0.0000 | 0.548 |
| C0_to_C1 | primary | oxidation | 6 | 0.733 | 0.829 | 0.133 | 0.267 | 1.000 | 0.0000 | 0.281 |
| C0_to_C1 | all | reduction | 10 | -0.467 | -0.552 | 0.444 | 0.800 | 0.000 | 0.4573 | 0.137 |
| C1_to_C2 | all | oxidation | 10 | 0.867 | 0.952 | 0.133 | 0.089 | 1.000 | 0.0000 | 0.857 |
| C1_to_C2 | primary | oxidation | 6 | 0.600 | 0.771 | 0.267 | 0.267 | 0.000 | 0.1020 | 0.329 |
| C1_to_C2 | all | reduction | 10 | 0.289 | 0.273 | 0.356 | 0.356 | 0.000 | 0.5143 | 0.443 |

τ_b/ρ 是全局排序层；f_unres(lo/up) 与 decisive 比例是统计分辨率层；决策重叠/regret/选择不确定度
是筛选决策层。三层一起读：全局排序看起来还行，但不代表 Top-k 决策可识别。

## 2. 分辨率曲线（f_unresolved vs z）

| 对比 | scope | 轴 | f(lo)@1 | f(lo)@1.645 | f(lo)@1.96 | f(up)@1.0 |
| --- | --- | --- | --- | --- | --- | --- |
| P0_to_P1v | all | oxidation | 0.359 | 0.529 | 0.549 | 0.157 |
| P0_to_P1v | all | reduction | 0.170 | 0.523 | 0.706 | 0.621 |
| P1v_to_P1a | all | oxidation | 0.121 | 0.167 | 0.167 | 0.121 |
| P1v_to_P2a | all | oxidation | 0.092 | 0.176 | 0.203 | 0.111 |
| P1v_to_P2a | all | reduction | 0.235 | 0.366 | 0.438 | 0.222 |
| P1v_to_P2eps10 | all | oxidation | 0.076 | 0.152 | 0.167 | 0.136 |
| P1v_to_P2eps10 | all | reduction | 0.091 | 0.273 | 0.333 | 0.258 |
| P0_to_P2a | all | oxidation | 0.301 | 0.444 | 0.503 | 0.229 |
| P0_to_P2a | all | reduction | 0.105 | 0.431 | 0.667 | 0.680 |
| C0_to_C1 | all | oxidation | 0.178 | 0.267 | 0.289 | 0.200 |
| C0_to_C1 | primary | oxidation | 0.133 | 0.267 | 0.333 | 0.267 |
| C0_to_C1 | all | reduction | 0.444 | 0.822 | 0.867 | 0.800 |
| C1_to_C2 | all | oxidation | 0.133 | 0.178 | 0.178 | 0.089 |
| C1_to_C2 | primary | oxidation | 0.267 | 0.400 | 0.400 | 0.267 |
| C1_to_C2 | all | reduction | 0.356 | 0.511 | 0.578 | 0.356 |

还原轴的 f_unresolved 明显高于氧化轴，且随 z 上升快得多：还原排序本身就更不可识别。

## 3. 结构性不可检验（algebra）

```
sigma_ij = |d_lower - d_upper| / sqrt(2)
z > 1/sqrt(2)  =>  反向 pair 两侧不可能同时 resolved
```

按 z 统计反向 pair 两侧同时 resolved 的个数：0.0->209, 0.5->63, 0.7071067811865476->0, 1.0->0, 1.2815515655446004->0, 1.6448536269514722->0, 1.959963984540054->0。

因此 Week 28 的 `f_robust_inversion == 0` **不能**读成「排序稳定」；它只是 z=1.0 > 1/sqrt(2) 的必然结果。
全部 1326 个 pair 都标注为 `structurally_non_testable`。

## 4. Case A：原始排序变化（不设阈值）

| 对比 | scope | 轴 | n | 反向 pair | τ_b(原始) | ρ(原始) | Top-20% 重叠 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| P0_to_P1v | all | oxidation | 18 | 25 | 0.673 | 0.804 | 0.500 |
| P0_to_P1v | all | reduction | 18 | 31 | 0.595 | 0.800 | 0.500 |
| P1v_to_P1a | all | oxidation | 12 | 7 | 0.788 | 0.923 | 1.000 |
| P1v_to_P2a | all | oxidation | 18 | 8 | 0.895 | 0.963 | 0.750 |
| P1v_to_P2a | all | reduction | 18 | 25 | 0.673 | 0.827 | 0.500 |
| P1v_to_P2eps10 | all | oxidation | 12 | 3 | 0.909 | 0.972 | 1.000 |
| P1v_to_P2eps10 | all | reduction | 12 | 5 | 0.848 | 0.923 | 1.000 |
| P0_to_P2a | all | oxidation | 18 | 25 | 0.673 | 0.814 | 0.500 |
| P0_to_P2a | all | reduction | 18 | 16 | 0.791 | 0.920 | 0.750 |
| C0_to_C1 | all | oxidation | 10 | 7 | 0.689 | 0.770 | 1.000 |
| C0_to_C1 | primary | oxidation | 6 | 2 | 0.733 | 0.829 | 1.000 |
| C0_to_C1 | all | reduction | 10 | 33 | -0.467 | -0.552 | 0.000 |
| C1_to_C2 | all | oxidation | 10 | 3 | 0.867 | 0.952 | 1.000 |
| C1_to_C2 | primary | oxidation | 6 | 3 | 0.600 | 0.771 | 0.000 |
| C1_to_C2 | all | reduction | 10 | 16 | 0.289 | 0.273 | 0.000 |

反向 pair 合计 209 个：原始排序确实发生了互换，只是这些互换在后面被判为不可检验。

## 5. Case C：决策稳健性（歧义区间抽样）

| 对比 | 轴 | k/N | S_upper | S_lower | 端点重叠 | P(S_upper 全中) | 平均∩S_upper |
| --- | --- | --- | --- | --- | --- | --- | --- |
| P0_to_P1v | oxidation | 4/18 | AN;SN;FEC;EC | FEC;EC;PC;DMC | 0.500 | 0.178 | 0.734 |
| P0_to_P1v | reduction | 4/18 | DOL;DME;DMC;DEC | DME;DOL;TEGDME;TMP | 0.500 | 0.004 | 0.449 |
| P1v_to_P1a | oxidation | 2/12 | AN;SN | AN;SN | 1.000 | 1.000 | 1.000 |
| P1v_to_P2a | oxidation | 4/18 | AN;SN;FEC;DMC | AN;SN;FEC;EC | 0.750 | 0.070 | 0.637 |
| P1v_to_P2a | reduction | 4/18 | DME;TEGDME;DOL;SL | DOL;DME;DMC;DEC | 0.500 | 0.008 | 0.433 |
| P1v_to_P2eps10 | oxidation | 2/12 | AN;SN | AN;SN | 1.000 | 0.546 | 0.758 |
| P1v_to_P2eps10 | reduction | 2/12 | DOL;DME | DOL;DME | 1.000 | 0.213 | 0.508 |
| P0_to_P2a | oxidation | 4/18 | AN;SN;FEC;DMC | FEC;EC;PC;DMC | 0.500 | 0.005 | 0.393 |
| P0_to_P2a | reduction | 4/18 | DME;TEGDME;DOL;SL | DME;DOL;TEGDME;TMP | 0.750 | 0.102 | 0.729 |
| C0_to_C1 | oxidation | 2/10 | AN;SN | AN;SN | 1.000 | 0.251 | 0.548 |
| C0_to_C1 | oxidation | 1/6 | EC | EC | 1.000 | 0.281 | 0.281 |
| C0_to_C1 | reduction | 2/10 | SN;SL | DOL;DME | 0.000 | 0.009 | 0.137 |
| C1_to_C2 | oxidation | 2/10 | AN;SN | AN;SN | 1.000 | 0.714 | 0.857 |
| C1_to_C2 | oxidation | 1/6 | DMC | EC | 0.000 | 0.329 | 0.329 |
| C1_to_C2 | reduction | 2/10 | DME;EC | SN;SL | 0.000 | 0.144 | 0.443 |

## 6. 分层算法敏感性（S1 vs S2）

| 对比 | 轴 | k | S1（score） | S2（conservative） | |S2| | 缺口 | 对称差 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| P0_to_P1v | oxidation | 4 | AN;SN;FEC;EC | EC;FEC | 2 | 2 | AN;SN |
| P0_to_P1v | reduction | 4 | DOL;DME;DMC;DEC | (空) | 0 | 4 | DEC;DMC;DME;DOL |
| P1v_to_P1a | oxidation | 2 | AN;SN | AN;SN | 2 | 0 | - |
| P1v_to_P2a | oxidation | 4 | AN;SN;FEC;DMC | AN;FEC;SN | 3 | 1 | DMC |
| P1v_to_P2a | reduction | 4 | DME;TEGDME;DOL;SL | DME | 1 | 3 | DOL;SL;TEGDME |
| P1v_to_P2eps10 | oxidation | 2 | AN;SN | AN;SN | 2 | 0 | - |
| P1v_to_P2eps10 | reduction | 2 | DOL;DME | DME | 1 | 1 | DOL |
| P0_to_P2a | oxidation | 4 | AN;SN;FEC;DMC | FEC | 1 | 3 | AN;DMC;SN |
| P0_to_P2a | reduction | 4 | DME;TEGDME;DOL;SL | (空) | 0 | 4 | DME;DOL;SL;TEGDME |
| C0_to_C1 | oxidation | 2 | AN;SN | AN | 1 | 1 | SN |
| C0_to_C1 | oxidation | 1 | EC | (空) | 0 | 1 | EC |
| C0_to_C1 | reduction | 2 | SN;SL | (空) | 0 | 2 | SL;SN |
| C1_to_C2 | oxidation | 2 | AN;SN | AN;SN | 2 | 0 | - |
| C1_to_C2 | oxidation | 1 | DMC | (空) | 0 | 1 | DMC |
| C1_to_C2 | reduction | 2 | DME;EC | (空) | 0 | 2 | DME;EC |

`S2 ⊆ S1` 恒成立（已断言）；但两者在 k=0.2 的 12 组上不一致。还原轴尤其严重：
大量 |S2|=0，意味着保守算法在还原轴上给不出任何「确定选择」。

## 7. 验收交付表：确定选择 / 边界候选 / 证据不足

- **P0_to_P1v / all / oxidation**（k=4）：确定选择 （无）；边界候选 AN, DEC, DMC, EA, EC, EMC, FEC, GBL, MA, PC, SN, TMP, VC；证据不足 5 个。
- **P0_to_P1v / all / reduction**（k=4）：确定选择 （无）；边界候选 AN, DEC, DMC, DME, DMSO, DOL, EA, EC, EMC, FEC, GBL, MA, PC, SL, SN, TEGDME, TMP, VC；证据不足 0 个。
- **P1v_to_P1a / all / oxidation**（k=2）：确定选择 AN, SN；边界候选 （无）；证据不足 10 个。
- **P1v_to_P2a / all / oxidation**（k=4）：确定选择 （无）；边界候选 AN, DEC, DMC, DOL, EA, EC, EMC, FEC, GBL, MA, PC, SL, SN, TMP, VC；证据不足 3 个。
- **P1v_to_P2a / all / reduction**（k=4）：确定选择 （无）；边界候选 AN, DEC, DMC, DME, DMSO, DOL, EA, EC, EMC, FEC, GBL, MA, PC, SL, TEGDME, TMP, VC；证据不足 1 个。
- **P1v_to_P2eps10 / all / oxidation**（k=2）：确定选择 （无）；边界候选 AN, DMC, EC, EMC, GBL, PC, SL, SN, TMP；证据不足 3 个。
- **P1v_to_P2eps10 / all / reduction**（k=2）：确定选择 （无）；边界候选 AN, DMC, DME, DMSO, DOL, EC, EMC, GBL, PC, SL, SN, TMP；证据不足 0 个。
- **P0_to_P2a / all / oxidation**（k=4）：确定选择 （无）；边界候选 AN, DEC, DMC, DME, DMSO, DOL, EA, EC, EMC, FEC, GBL, MA, PC, SL, SN, TEGDME, TMP, VC；证据不足 0 个。
- **P0_to_P2a / all / reduction**（k=4）：确定选择 DME；边界候选 AN, DEC, DMC, DMSO, DOL, EA, EC, EMC, FEC, GBL, MA, PC, SL, SN, TEGDME, TMP, VC；证据不足 0 个。
- **C0_to_C1 / all / oxidation**（k=2）：确定选择 （无）；边界候选 AN, DMC, DME, DMSO, DOL, EC, GBL, SL, SN, TMP；证据不足 0 个。
- **C0_to_C1 / primary / oxidation**（k=1）：确定选择 （无）；边界候选 DMC, DME, EC, GBL, SL, TMP；证据不足 0 个。
- **C0_to_C1 / all / reduction**（k=2）：确定选择 （无）；边界候选 AN, DMC, DME, DMSO, DOL, EC, GBL, SL, SN, TMP；证据不足 0 个。
- **C1_to_C2 / all / oxidation**（k=2）：确定选择 （无）；边界候选 AN, DMC, DOL, EC, GBL, SL, SN；证据不足 3 个。
- **C1_to_C2 / primary / oxidation**（k=1）：确定选择 （无）；边界候选 DMC, DME, EC, GBL, SL, TMP；证据不足 0 个。
- **C1_to_C2 / all / reduction**（k=2）：确定选择 （无）；边界候选 AN, DMC, DME, DMSO, DOL, EC, GBL, SL, SN, TMP；证据不足 0 个。

## 8. 一致性自检

- `pair_shift_identity_holds`: PASS -- d_upper = d_lower + delta_shift（max 0.000e+00）且 sigma = |delta_shift|/sqrt(2)（max 8.882e-16），1326 行
- `resolution_curve_monotone_and_matches_week28`: PASS -- f_unresolved 随 z 单调不减（违例 0）；z=1.0 时与 Week 28 decision_table 最大绝对差 5.551e-17（15 个比较）
- `topk_sets_match_week28_decision_table`: PASS -- 45 行 (key,k) 的 selected_upper/lower 与冻结值一致（按集合比较；冻结列组内顺序来自 CPython set 迭代，无语义）；不一致 0
- `ranking_metrics_match_week28`: PASS -- overlap/Jaccard/regret/tau_b/rho 对齐冻结值，最大绝对差 overlap=0.000e+00, jaccard=0.000e+00, selection_regret_ev=0.000e+00, kendall_tau_b=0.000e+00, spearman_rho=0.000e+00（75 个 metric 行）
- `robust_inversion_is_structurally_impossible`: PASS -- 1326 个 pair 全部 structurally_non_testable；decision_table 的 n_robust_inversion 合计 0；z>1/sqrt(2) 时反向 pair 两侧同时 resolved 恒为 0。按 z 的计数：0.0:209, 0.5:63, 0.7071067811865476:0, 1.0:0, 1.2815515655446004:0, 1.6448536269514722:0, 1.959963984540054:0
- `selection_uncertainty_internally_consistent`: PASS -- 端点 overlap 与冻结 overlap 最大差 0.000e+00；确定性保证的候选（p=1）必须落在 score Top-k 内 —— 违例 0
- `stratification_sensitivity_surfaced`: PASS -- S2 ⊆ S1 恒成立（反例 0）；S1 != S2 的 (组,k) 数按 k_fraction：0.1:10, 0.2:12, 0.3:14（k=0.2 时 12 组，与独立复核一致）
- `decision_classes_partition_every_selection`: PASS -- 45 个 (组,k) 决策全部被划分为 certain / boundary / insufficient；每个决策的候选数之和等于该组分子数
- `independent_review_reconciled`: PASS -- 三个独立复核（A 分辨率 / B 稳健性 / C 分层）的锚点与本规范实现逐位一致：锚点最大差 0.000e+00；sign_reverse 合计 209；k=0.2 的 S1!=S2 组数 12
- `zero_new_electronic_structure`: PASS -- 唯一输入是 outputs/week28/*.csv；未运行任何电子结构作业

## 9. 限制

- 零新增计算；Gate 1 仍 NOT CLOSED，本阶段不提供任何外部有效性支持。
- 不确定性只用「两端模型输出的歧义区间」这一个独立来源；来源不足的地方如实报为 sensitivity range。
- `f_robust_inversion == 0` 是代数必然，不得当作稳定性证据。
- 「确定选择」是相对某一套不确定性假设与分层算法而言的；换假设会改变结论（见第 6 节）。
- core18 上的结论不可外推到其他分子集：每组 n 随对比变化（18/12/10/6），跨行不可比。

## 10. 复现命令

```powershell
.venv\Scripts\python.exe scripts\build_week31_wp4_decision_identifiability.py
.venv\Scripts\python.exe scripts\build_week31_wp4_decision_identifiability.py --check
.venv\Scripts\python.exe -m pytest tests/test_week31_wp4_decision_identifiability.py -q
```
