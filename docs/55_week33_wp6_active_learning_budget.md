# Week 33 / WP6：最小昂贵信息预算（RQ4 后半）

> 阶段：下一阶段实施方案 WP6（RQ4 后半）。产物目录 `outputs/week33/`，交付镜像
> `..\成果输出（part2）\week33/`。数字由 `scripts/build_week33_wp6_active_learning_budget.py`
> 确定性生成，`--check` 逐字节复核。**零新增电子结构计算，且不重跑 acquisition loop**：
> 唯一输入是 Week 7 Stage 8 的冻结 replay（`stage8_al_curves.csv` / `stage8_al_runs.csv` /
> `stage8_al_trajectories.csv` / `stage8_al_results.json`）与 Stage 7 的冻结 ML 结果。

## 0. 本轮解决的问题

WP5 说明「便宜参考层 + 学到的位移」能否替代直接预测。WP6 换一个更贴近预算的问法：
**要用多少张昂贵标签，才能把筛选决策恢复到可接受水平**，即

```
n_T  ->  { tau_b, O_k, R_k }        n_T = 已获得的昂贵目标标签数量
```

实施方案给出的硬要求，本阶段逐条落地：

- 四条冻结 acquisition baseline：`random` / `diversity` / `uncertainty` / `ranking_aware`；
- 固定候选池、target、初始预算（4）、批次（1）与随机种子，每轮只暴露已查询标签；
- 标准化与模型拟合只在当轮可见数据内完成（Stage 8 已保证，本阶段只审计不重跑）；
- 多种子重复（20 次）报 median 与 2.5/97.5 百分位；
- 成功标准必须**预先定义**、对全部单元格一律适用，且要求**在多数重复中成立**，而不是只在
  中位数曲线上成立；
- 分别考虑池内插值（in-pool）与 family-held-out 两种情景。

三层表述纪律贯穿本文件：**模型事实**（`al_protocol_audit`、`budget_curves`、
`curve_reconciliation`）/ **统计判定**（`success_criteria`、`success_budget`、
`strategy_comparison`）/ **材料意义**（`family_coverage`、`holdout_vs_inpool`）。

## 1. 协议审计（冻结 replay 的事实）

| 任务 | 轴 | 池 | 初始种子 | 批次 | 重复 | n_T | 曲线点 | 采集特征 | regret 容忍 (eV) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| M | oxidation | 18 | 4 | 1 | 20 | 4-18 | 15 | X0 only | 0.2273 |
| M | reduction | 18 | 4 | 1 | 20 | 4-18 | 15 | X0 only | 0.1116 |
| E | oxidation | 18 | 4 | 1 | 20 | 4-18 | 15 | X0 only | 0.1641 |
| E | reduction | 18 | 4 | 1 | 20 | 4-18 | 15 | X0 only | 0.0810 |
| C | oxidation | 10 | 4 | 1 | 20 | 4-10 | 7 | X0 only | 0.1619 |
| C | reduction | 10 | 4 | 1 | 20 | 4-10 | 7 | X0 only | 0.0413 |

`ranking_aware` 的查询依据是二元熵 `H_i = -p_i ln p_i - (1-p_i) ln(1-p_i)`，`p_i = P(i ∈ Top-k)`；
采集只用 X0 描述符（绝不使用 X2 —— Li-complex 之后才有的信息）。**regret 容忍值由公式给出**：
池内目标真值极差的 5%（`REGRET_TARGET_SCALE = 0.05`），由轨迹中的真值直接算出，不是挑出来的。

## 2. 决策性能曲线：median τ_b 随 n_T

`M · oxidation`（池大小 18）：

| n_T | random | diversity | uncertainty | ranking_aware |
| --- | --- | --- | --- | --- |
| 4 | 0.255 | 0.255 | 0.255 | 0.255 |
| 5 | 0.336 | 0.425 | 0.384 | 0.262 |
| 6 | 0.332 | 0.438 | 0.425 | 0.320 |
| 7 | 0.419 | 0.510 | 0.562 | 0.438 |
| 8 | 0.460 | 0.634 | 0.608 | 0.391 |
| 9 | 0.562 | 0.680 | 0.660 | 0.500 |
| 10 | 0.595 | 0.719 | 0.686 | 0.556 |
| 11 | 0.654 | 0.739 | 0.771 | 0.601 |
| 12 | 0.712 | 0.778 | 0.804 | 0.754 |
| 13 | 0.804 | 0.843 | 0.856 | 0.830 |
| 14 | 0.850 | 0.863 | 0.869 | 0.889 |
| 15 | 0.895 | 0.948 | 0.961 | 0.948 |
| 16 | 0.961 | 0.987 | 0.987 | 0.954 |
| 17 | 0.987 | 1.000 | 0.987 | 0.987 |
| 18 | 1.000 | 1.000 | 1.000 | 1.000 |

`C · oxidation`（池大小 10）：

| n_T | random | diversity | uncertainty | ranking_aware |
| --- | --- | --- | --- | --- |
| 4 | 0.346 | 0.346 | 0.346 | 0.346 |
| 5 | 0.489 | 0.489 | 0.418 | 0.418 |
| 6 | 0.511 | 0.556 | 0.511 | 0.511 |
| 7 | 0.667 | 0.733 | 0.578 | 0.600 |
| 8 | 0.733 | 0.867 | 0.822 | 0.733 |
| 9 | 0.844 | 0.956 | 0.956 | 0.867 |
| 10 | 1.000 | 1.000 | 1.000 | 1.000 |

四个 target 的完整曲线（含 overlap 10/20/30% 与 regret 的 median、2.5/97.5 百分位）见
`budget_curves.csv`（296 行）。**n_T = 池大小处的 τ_b 恒为 1.0**：这是「已标注用真值、未标注用
预测」的**自检端点**，不是成绩，任何解读都必须排除这一点。

中位数曲线并非处处单调：24 条曲线里 **20 条单调不减**，4 处回落全部出现在 `n_T = 5→6` 或
`7→8` 的早期（`E|oxidation|ranking_aware`、`E|reduction|random`、`M|oxidation|random`、
`M|oxidation|ranking_aware`）。20 次重复的 median 本身就有跳变，不能把单点当成趋势。

## 3. 达标预算：中位数曲线 vs 多数重复

预注册判据（对所有单元格一律适用，无逐格调参）：

- `tau_b >= 0.80`（排序恢复）、`Top-20% overlap 全中`、`regret <= 池内极差 5%`；
- 三者**同时**成立才算「组合达标」，且要求**至少 80% 的重复**满足 —— 只在中位数曲线上达标
  不算。

| 任务 | 轴 | 策略 | median τ_b≥0.80 | 多数重复 τ_b≥0.80 | 多数重复 组合达标 | 中位数曲线高估？ |
| --- | --- | --- | --- | --- | --- | --- |
| C | oxidation | random | 9 | 10 | 10 | 是 |
| C | oxidation | diversity | 8 | 8 | 9 | 否 |
| C | oxidation | uncertainty | 8 | 8 | 9 | 否 |
| C | oxidation | ranking_aware | 9 | 10 | 10 | 是 |
| C | reduction | random | 9 | 9 | 10 | 否 |
| C | reduction | diversity | 9 | 9 | 9 | 否 |
| C | reduction | uncertainty | 9 | 9 | 9 | 否 |
| C | reduction | ranking_aware | 9 | 10 | 10 | 是 |
| E | oxidation | random | 15 | 15 | 17 | 否 |
| E | oxidation | diversity | 14 | 14 | 18 | 否 |
| E | oxidation | uncertainty | 12 | 14 | 18 | 是 |
| E | oxidation | ranking_aware | 13 | 14 | 15 | 是 |
| E | reduction | random | 14 | 15 | 18 | 是 |
| E | reduction | diversity | 13 | 13 | 13 | 否 |
| E | reduction | uncertainty | 13 | 14 | 14 | 是 |
| E | reduction | ranking_aware | 13 | 14 | 14 | 是 |
| M | oxidation | random | 13 | 15 | 16 | 是 |
| M | oxidation | diversity | 13 | 13 | 16 | 否 |
| M | oxidation | uncertainty | 12 | 13 | 15 | 是 |
| M | oxidation | ranking_aware | 13 | 15 | 15 | 是 |
| M | reduction | random | 13 | 14 | 18 | 是 |
| M | reduction | diversity | 13 | 13 | 17 | 否 |
| M | reduction | uncertainty | 13 | 14 | 18 | 是 |
| M | reduction | ranking_aware | 13 | 14 | 15 | 是 |

**这是本阶段最重要的一条**：24 个 (target, 策略) 组合里有 **14 个**的中位数曲线比「≥ 80% 的重复
满足 τ_b ≥ 0.80」更早达标（**口径只按 τ_b**；若按 τ_b ∧ Top-20% overlap ∧ regret 的**组合**口径，
则为 **21/24 个**）。若只看中位数曲线，就会低估所需的昂贵标签数。`diversity` 是唯一 6/6 都不高估的策略，
它的中位数曲线恰好是最可信的指示器。

还有一层更严格的对照：**「组合达标」（overlap 全中且 regret 达标）普遍比「τ_b ≥ 0.80」更晚
才达到多数重复标准**（`M|reduction|random` 从 n_T=14 推到 18，`E|oxidation|uncertainty` 从 14
推到 18）。排序看起来恢复了，不等于筛选结果恢复了。

## 4. 策略是否比 random 更省昂贵标签

在同一 (repeat, n_T) 上把每个非随机策略与配对的 `random` 比较（20 次重复 × 公共 n_T）：

| 任务 | 轴 | 策略 | 配对数 | τ_b 胜率 | 打平率 | Δτ_b 中位数 |
| --- | --- | --- | --- | --- | --- | --- |
| C | oxidation | diversity | 140 | 0.436 | 0.407 | +0.000 |
| C | oxidation | uncertainty | 140 | 0.379 | 0.400 | +0.000 |
| C | oxidation | ranking_aware | 140 | 0.307 | 0.379 | +0.000 |
| C | reduction | diversity | 140 | 0.329 | 0.436 | +0.000 |
| C | reduction | uncertainty | 140 | 0.336 | 0.400 | +0.000 |
| C | reduction | ranking_aware | 140 | 0.300 | 0.407 | +0.000 |
| E | oxidation | diversity | 300 | 0.637 | 0.193 | +0.039 |
| E | oxidation | uncertainty | 300 | 0.660 | 0.177 | +0.052 |
| E | oxidation | ranking_aware | 300 | 0.487 | 0.200 | +0.000 |
| E | reduction | diversity | 300 | 0.563 | 0.183 | +0.026 |
| E | reduction | uncertainty | 300 | 0.507 | 0.210 | +0.009 |
| E | reduction | ranking_aware | 300 | 0.480 | 0.173 | +0.000 |
| M | oxidation | diversity | 300 | 0.593 | 0.210 | +0.031 |
| M | oxidation | uncertainty | 300 | 0.587 | 0.173 | +0.039 |
| M | oxidation | ranking_aware | 300 | 0.383 | 0.170 | +0.000 |
| M | reduction | diversity | 300 | 0.420 | 0.190 | +0.000 |
| M | reduction | uncertainty | 300 | 0.400 | 0.187 | +0.000 |
| M | reduction | ranking_aware | 300 | 0.397 | 0.190 | +0.000 |

在「多数重复组合达标」的预算口径上，18 个 (target, 非随机策略) 组合里 **12 个比 random 更省
标签、2 个更贵、4 个打平**。更省的典型是 `E|reduction|diversity`（省 5 张）与
`E|reduction|uncertainty`、`E|reduction|ranking_aware`（各省 4 张）；更贵的只有
`E|oxidation|diversity`、`E|oxidation|uncertainty`（各多花 1 张）。

但**逐点胜率讲述的是另一个故事**：只有在池子较大（18）且轴上出现 `diversity` / `uncertainty`
时才稳定优于 random（胜率 0.56-0.66）；在池子只有 10 的 C 任务上，所有非随机策略的胜率都
**低于 0.44**（打平率约 0.4 —— 池太小，很多重复根本分不出差别）。`ranking_aware` 在 6 个
target 上有 4 个胜率不到 0.49：**「直接优化 Top-k 不确定性」在当前规模下并没有兑现它的承诺。**

## 5. 家族覆盖：覆盖 ≠ 决策质量

`family_coverage.csv` 统计每次重复「已查询集合」覆盖的家族数（中位数）。池内各有 8 个家族。
在 `median τ_b` 首次达到 0.80 的预算点上，覆盖数分布是：

- 大多数组合已覆盖 7-8 个家族（`M`/`E` 的大多数策略在 n_T = 12-15 时已到 8/8）；
- 但 `C|oxidation|diversity` 只用 6.0/8 个家族就达到了 τ_b ≥ 0.80。

也就是说**家族覆盖与决策质量并不同步**：覆盖（`diversity` 的卖点）既不是达标所必需，也不足以
保证达标。这里必须强调口径边界 —— 覆盖只是「池内化学空间覆盖」的代理，**不是** family-held-out
泛化。

## 6. 池内 vs 跨家族（口径诚实声明）

| 任务 | 轴 | 池 | 池内端点 τ_b | 静态 LOFO τ_b | LOFO 最优模型 | AL family-held-out |
| --- | --- | --- | --- | --- | --- | --- |
| C | oxidation | 10 | 1.000 | +0.111 | krr | 不可用 |
| C | reduction | 10 | 1.000 | +0.422 | gbdt | 不可用 |
| E | oxidation | 18 | 1.000 | +0.843 | ridge | 不可用 |
| E | reduction | 18 | 1.000 | +0.686 | rf | 不可用 |
| M | oxidation | 18 | 1.000 | +0.294 | krr | 不可用 |
| M | reduction | 18 | 1.000 | +0.359 | rf | 不可用 |

冻结的 Stage 8 replay 只有**池内插值**一种口径（池 = core set 自身，评价也在同一池上）。它没有
任何 fold 字段，**family-held-out 的主动学习曲线不存在**，要得到它必须重跑 acquisition —— 不在
本阶段范围，也不在「零新增计算」的许可范围内。

本阶段用 Stage 7 的静态 LOFO 结果（同一廉价特征集、留一家族、`direct`）作对照：池内端点恒为
1.000，而留一家族最好也只有 0.843（M 任务仅 0.294）。**池内曲线饱和绝不等于跨家族泛化**，
任何「买 X 张 DFT 就够了」的说法在本文的口径下都不成立。

## 7. 与冻结 Stage 8 曲线的对账

从 `stage8_al_runs.csv`（5920 行 = 296 单元格 × 20 重复）独立重算每个单元格的 median 与
2.5/97.5 百分位，与冻结的 `stage8_al_curves.csv` 逐格比较：

| 指标 | 最大绝对差 | 容差 |
| --- | --- | --- |
| Kendall tau_b | 8.500e-07 | 1e-06 |
| Top-20% overlap | 3.331e-16 | 1e-06 |
| Top-30% overlap | 1.750e-07 | 1e-06 |
| selection regret (eV) | 7.000e-06 | 1e-05 |

**超容差 0 个单元格**。冻结曲线用 `%.6g` 写出（发布精度），残差最大只相当于 3 个存储步长；
本阶段不靠放宽容差掩盖差异，只如实报出量级与来源（发布精度，而非模型差异）。

## 8. 验收问题

- **Q1_budget_curve_improves**：四个策略的 median τ_b 是否都随 n_T 单调改善？
  → **20/24** 条曲线单调不减；4 处回落全在 n_T ≤ 8 的早期，属 20 次重复 median 的跳变。
- **Q2_strategy_beats_random**：非随机策略是否比 random 更省昂贵标签？
  → 用「多数重复组合达标」的预算衡量：**12 个更省 / 2 个更贵 / 4 个打平**。但逐点胜率显示，
  这一优势集中在池较大的 M/E 任务的 `diversity` / `uncertainty`；`ranking_aware` 基本没兑现。
- **Q3_majority_of_repeats**：达标是否在多数重复中成立，而不是只在中位数曲线上成立？
  → **14/24** 个组合的中位数曲线比「≥ 80% 重复满足 τ_b ≥ 0.80」更早达标（按 τ_b ∧ overlap ∧
  regret 的**组合**口径则为 **21/24**）—— 只看中位数曲线会低估预算。
- **Q4_inpool_vs_family_heldout**：池内曲线饱和是否等于跨家族泛化？
  → **不等价**。池内端点恒为 1.0（自检端点）；静态 LOFO 参照最高仅 0.843；冻结 replay 里
  family-held-out 的 AL 曲线**不可用**，本阶段不做任何外推。

## 9. 一致性自检（10 项，全部 PASS）

| 自检 | 断言 |
| --- | --- |
| `curves_recomputed_from_runs_within_storage_precision` | 296 单元格重算，超容差 0 |
| `every_frozen_curve_cell_recombined` | 冻结曲线单元格全部被覆盖，缺失 0 |
| `protocol_matches_frozen_ledger` | 池/种子/批次/重复/策略/k/采集特征与台账一致；296/5920/7360，GPR 回落 0 |
| `sequential_acquisition_prefix_property` | 480 条轨迹 step 连续且无重复 query（n_T 集合严格是 n_T+1 的前缀） |
| `success_criteria_preregistered_and_uniform` | 判据写死在代码里、296 个单元格一律适用；容忍值由公式推出 |
| `bands_ordered_and_bracketing` | 全部单元格满足 2.5% ≤ median ≤ 97.5% |
| `strategy_effect_quantified` | 18 个 (target, 非随机策略) 组都在同一 (repeat, n_T) 上与 random 配对 |
| `family_coverage_computed` | 296 格覆盖数随 n_T 单调不减、且不超过池内家族数 |
| `family_heldout_gap_declared` | 6 个 target 全部标注 AL family-held-out 不可用；池内端点 1.0，静态 LOFO < 1.0 |
| `zero_new_electronic_structure` | 零新增电子结构计算，零重跑 acquisition |

## 10. 限制

- 零新增计算；Gate 1 仍 NOT CLOSED，本阶段是 **computational-target** 陈述。
- core set 只有 18（C 任务 10）个分子，每 target 只有 15（C 为 7）个预算点；20 次重复的
  2.5/97.5 百分位本身很粗。只比较**方法的相对行为**，不做绝对外推。
- 成功标准是**内部操作性标准**（τ_b ≥ 0.80、overlap 全中、regret ≤ 极差 5%、≥ 80% 重复），
  未经外部校准；不得读成「真实项目需要买多少张 DFT」。
- posterior sampling 来自 GPR 后验协方差（样本 256），未做 uncertainty calibration 检验；
  在 18 个点上无法做可信校准，这一点在 `uncertainty` 策略的任何结论里都必须重申。
- family-held-out 的 AL 曲线不可用；如需要须重跑 acquisition。
- 下一步 WP7（Week 34）：外部参考分层与 Gate 1 结论边界。

## 11. 复现命令

```powershell
cd 电解液溶剂HB-Code
.venv\Scripts\python.exe scripts\build_week33_wp6_active_learning_budget.py
.venv\Scripts\python.exe scripts\build_week33_wp6_active_learning_budget.py --check
.venv\Scripts\python.exe -m pytest tests/test_week33_wp6_active_learning_budget.py -q
.venv\Scripts\python.exe scripts\build_week33_deliverables.py
```