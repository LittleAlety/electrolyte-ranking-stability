# Week 31 / WP4：把排序变化转成可辩护的筛选决策（RQ3）

> 阶段：下一阶段（评审实施方案）WP4（RQ3）。产物目录 `outputs/week31/`，交付镜像
> `..\成果输出（part2）\week31/`。数字由 `scripts/build_week31_wp4_decision_identifiability.py`
> 确定性生成并 `--check` 逐字节复核。**零新增电子结构计算**：唯一输入是 Week 28 冻结主表。

## 0. 本轮解决的问题

WP2 说清了「哪些物理改变排序」，WP3 说清了「Li+ 配位怎样改变机理」。WP4 处理决定这套分析
有没有用的那一步：**面对一次 Top-k 筛选决策，我们到底知道多少**。评审明确要求三套并列分析，
而不是只依赖 `f_robust_inv`：

| 评价层次 | 主指标 | 本阶段的落地表 |
| --- | --- | --- |
| 全局排序 | Kendall τ_b、Spearman ρ | `identifiability_summary` |
| 统计分辨率 | unresolved fraction、pairwise probability、resolution curve | `resolution_curve`、`structural_nontestability` |
| 筛选决策 | Top-k overlap、Jaccard、regret、selection uncertainty | `selection_uncertainty`、`decision_classes` |

评审还点出一个代数陷阱：在 `σ_ij = |d_lower − d_upper| / √2` 的约定下，若 `z > 1/√2`，
反向 pair 无法两侧同时通过稳健判据。本阶段把它写成断言而不是结论（见第 3 节）。

## 1. 三层评价总表（k_fraction = 0.2）

| 对比 | scope | 轴 | n | τ_b | ρ | f_unres(lo) | f_unres(up) | 决策重叠 | regret (eV) | 选择不确定度 |
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
| C0_to_C1 | all | reduction | 10 | −0.467 | −0.552 | 0.444 | 0.800 | 0.000 | 0.4573 | 0.137 |
| C1_to_C2 | all | oxidation | 10 | 0.867 | 0.952 | 0.133 | 0.089 | 1.000 | 0.0000 | 0.857 |
| C1_to_C2 | primary | oxidation | 6 | 0.600 | 0.771 | 0.267 | 0.267 | 0.000 | 0.1020 | 0.329 |
| C1_to_C2 | all | reduction | 10 | 0.289 | 0.273 | 0.356 | 0.356 | 0.000 | 0.5143 | 0.443 |

三层一起读才完整：`P1v_to_P2a / oxidation` 的 τ_b = 0.895 看起来很好，但它的 Top-k 重叠
只有 0.750、选择不确定度 0.637 —— 全局排序稳，不代表这一次筛选稳。

## 2. 分辨率曲线 `f_unresolved(z)`

15 组全部满足 `f_unresolved` 随 z 单调不减（违例 0）；z = 1.0 时与 Week 28 `decision_table`
逐位一致（最大绝对差 5.6e-17）。还原轴的不可识别性明显更高，且随 z 上升更快：

| 对比 | 轴 | f(lo)@1.0 | f(lo)@1.645 | f(lo)@1.96 | f(up)@1.0 |
| --- | --- | --- | --- | --- | --- |
| P0_to_P1v | oxidation | 0.359 | 0.529 | 0.549 | 0.157 |
| P0_to_P1v | reduction | 0.170 | 0.523 | 0.706 | 0.621 |
| P0_to_P2a | oxidation | 0.301 | 0.444 | 0.503 | 0.229 |
| P0_to_P2a | reduction | 0.105 | 0.431 | 0.667 | 0.680 |
| C0_to_C1 | reduction | 0.444 | 0.822 | 0.867 | 0.800 |
| C1_to_C2 | reduction | 0.356 | 0.511 | 0.578 | 0.356 |

## 3. 结构性不可检验（algebra，必须与结论一起读）

```
σ_ij = |d_lower − d_upper| / √2
z > 1/√2  =>  反向 pair 两侧不可能同时 resolved
```

反向 pair 两侧同时 resolved 的个数，按 z：`0.0 → 209`、`0.5 → 63`、`1/√2 → 0`，
此后所有 z 恒为 0。全部 1326 个 pair 都带 `structurally_non_testable = True`；
Week 28 `decision_table` 的 `n_robust_inversion` 合计 0。

**因此 `f_robust_inversion == 0` 不能读成「排序稳定」**，它只是 `z = 1.0 > 1/√2` 的代数必然。
本阶段用 `robust_inversion_is_structurally_impossible` 把这一点钉成断言。

## 4. Case A：原始排序变化（不附加阈值）

不加任何不确定性阈值时，反向 pair 合计 **209** 个（`P0_to_P1v / oxidation` 25、
`P0_to_P1v / reduction` 31、`C0_to_C1 / all / reduction` 33 …）。也就是说模型输出确实发生了
互换；WP4 的价值在于说清**其中哪些互换是我们没有证据去判定的**，而不是把它们当成噪声抹掉。

## 5. Case C：决策稳健性（模型歧义区间抽样）

对每个候选，令其得分在两端模型输出构成的区间 `[min(P_lower,P_upper), max(…)]` 上均匀抽样
（B = 2000，seed = 0，逐候选独立），观察 Top-k 集合如何变化。关键量：端点重叠（S_upper vs
S_lower）、`P(S_upper 全中)`、平均 `|选中 ∩ S_upper| / k`。

| 对比 | 轴 | k/N | S_upper | S_lower | 端点重叠 | P(S_upper 全中) | 平均∩S_upper |
| --- | --- | --- | --- | --- | --- | --- | --- |
| P0_to_P1v | oxidation | 4/18 | AN;SN;FEC;EC | FEC;EC;PC;DMC | 0.500 | 0.179 | 0.734 |
| P0_to_P1v | reduction | 4/18 | DOL;DME;DMC;DEC | DME;DOL;TEGDME;TMP | 0.500 | 0.004 | 0.449 |
| P0_to_P2a | reduction | 4/18 | DME;TEGDME;DOL;SL | DME;DOL;TEGDME;TMP | 0.750 | 0.102 | 0.729 |
| P1v_to_P2a | oxidation | 4/18 | AN;SN;FEC;DMC | AN;SN;FEC;EC | 0.750 | 0.071 | 0.637 |
| C0_to_C1 | primary | oxidation | 1/6 | SN | FEC | 0.000 | 0.208 | 0.208 |

端点重叠与 Week 28 冻结 `overlap` 逐位一致（最大差 0）。`P(S_upper 全中)` 普遍很低：
**当前 Top-k 集合整体成立的概率远低于「其中有几个候选成立」的概率**，这正是 selection
uncertainty 要暴露的东西。

## 6. 分层算法敏感性（S1 vs S2）—— 本阶段最重要的一条

对 unresolved pair，评审明确禁止靠传递性把候选并成等价类，要求用**明确的分层算法**并检验
结果是否依赖算法选择。本阶段并列两种可辩护的定义：

- **S1（score-lexicographic）**：直接按上台阶得分降序取 Top-k；
- **S2（conservative / resolved-only）**：候选 `i` 入选，当且仅当它在**两侧都 resolved** 的
  比较中胜过至少 `n − k` 个对手 —— 即「无论未解析的 pair 如何翻转，它都稳进 Top-k」。

结果：`S2 ⊆ S1` **恒成立**（结构性质，已断言，反例 0），但两者并不一致 ——
`S1 ≠ S2` 的 (组,k) 数为 `k=0.1 → 10`、`k=0.2 → 12`、`k=0.3 → 14`。还原轴尤其严重，
很多组 `|S2| = 0`：保守算法在还原轴上给不出任何「确定选择」。

进一步，把 Case C 的确定性保证（`p_i = 1`）与 S2 对比，`k=0.2` 时 15 组里有 **9 组**给出
不同答案。两种不确定性口径都站得住，但它们的「确定选择」不同 —— 这就是评审要求
「不能简单依靠传递性」的实证依据。

## 7. 验收交付表：确定选择 / 边界候选 / 证据不足

`decision_classes.csv`（588 行）对每个 (组, k, 候选) 给出三分类，并附判定理由：

- **certain（确定选择）**：在歧义区间的所有实现下都进 Top-k（`p_i = 1`）；
- **boundary（边界候选）**：进与不进都可能（`0 < p_i < 1`），理由列出具名未解析对手；
- **insufficient（证据不足）**：从不入选（`p_i = 0`），并区分「被已解析地压过」与「与入选者之间仍不可判定」。

`k = 0.2` 的典型情形：`P1v_to_P1a / oxidation` 的确定选择是 AN、SN（无边界候选）；
`P0_to_P2a / reduction` 的确定选择是 DME；而 `P1v_to_P2a / oxidation`、`P1v_to_P2a / reduction`
的确定选择为空、全部候选都是边界候选 —— 这些组的 Top-k 决策目前**不可识别**，
必须如实标注为证据不足，而不是报一个看起来干净的名次。

## 8. 一致性自检（10 项，全部 PASS）

| 自检 | 断言 |
| --- | --- |
| `pair_shift_identity_holds` | `d_upper = d_lower + Δshift`、`σ = |Δshift|/√2`，1326 行，最大误差 ≤ 1e-15 |
| `resolution_curve_monotone_and_matches_week28` | 单调不减（违例 0）；z=1.0 对齐冻结值（≤ 5.6e-17） |
| `topk_sets_match_week28_decision_table` | 45 个 (组,k) 的 Top-k 集合与冻结值一致（按集合比较） |
| `ranking_metrics_match_week28` | overlap/Jaccard/regret/τ_b/ρ 对齐冻结值（最大差 0） |
| `robust_inversion_is_structurally_impossible` | 1326 pair 全 `structurally_non_testable`；`n_robust_inversion` 合计 0 |
| `selection_uncertainty_internally_consistent` | 端点重叠对齐冻结值；`p=1` 的候选必落在 score Top-k 内 |
| `stratification_sensitivity_surfaced` | `S2 ⊆ S1` 恒成立；S1≠S2 计数已上报 |
| `decision_classes_partition_every_selection` | 45 个决策的三分类构成完整分区 |
| `independent_review_reconciled` | 三个独立复核锚点与本实现逐位一致（最大差 0） |
| `zero_new_electronic_structure` | 唯一输入为 `outputs/week28/*.csv` |

第 9 项说明：本阶段另派三个只读子智能体独立重算了「分辨率曲线 / Monte-Carlo 稳健性 /
分层算法敏感性」，与本实现的规范代码逐位对账后才冻结数字。

## 9. 限制与下一步

- 不确定性只有**一个**独立来源（两端模型输出的歧义区间）；来源不足处如实报为 sensitivity range，
  不伪装成置信区间。
- `f_robust_inversion == 0` 是代数必然，不得当作稳定性证据（已经写成断言）。
- 「确定选择」是相对于一套不确定性假设与一种分层算法而言的；换假设会改变结论（第 6 节已量化）。
- 每组 n 随对比变化（18/12/10/6），跨行不可比；结论不外推到 core18 之外。
- 冻结的 `decision_table.selected_upper/lower` 列，其组内顺序来自 CPython `set` 迭代、无语义；
  Week 31 的对应列按数值降序，两者按集合对账。
- 下一步 WP5（Week 32）：Δ-learning 与 LOFO 跨家族泛化，源数据 `outputs/week7`。

## 10. 复现命令

```powershell
cd 电解液溶剂HB-Code
.venv\Scripts\python.exe scripts\build_week31_wp4_decision_identifiability.py
.venv\Scripts\python.exe scripts\build_week31_wp4_decision_identifiability.py --check
.venv\Scripts\python.exe -m pytest tests/test_week31_wp4_decision_identifiability.py -q
.venv\Scripts\python.exe scripts\build_week31_deliverables.py
```