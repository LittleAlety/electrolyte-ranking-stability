# Week 33 / WP6：最小昂贵信息预算（RQ4 后半）

> 阶段：下一阶段实施方案 WP6（RQ4 后半）。产物目录 `outputs/week33/`，交付镜像
> `..\成果输出（part2）\week33/`。本文件由 `scripts/build_week33_wp6_active_learning_budget.py`
> 确定性生成，`--check` 逐字节复核。**零新增电子结构计算，零重跑 acquisition**：
> 输入是 Week 7 Stage 8 的冻结 replay 产物。

## 0. 一句话结论

预注册的成功标准是「median τ_b ≥ 0.80、Top-20% overlap 全中、regret ≤ 池内目标极差的 5%，且在 ≥ 80% 的重复中成立」。
四条策略里 **12/18 个 (target, 非random 策略) 组合比 random 更早达标**，但有 **14** 个组合的中位数曲线比「≥ 80% 的重复满足 τ_b ≥ 0.80」更早达标（口径只按 τ_b；若按 τ_b ∧ Top-20% overlap ∧ regret 的**组合**口径，则为 21/24 个）—— 只看中位数曲线会低估预算。

## 1. 协议审计

| 任务 | 轴 | 池 | 初始种子 | 批次 | 重复 | n_T | 曲线点 | 采集特征 | regret 容忍 (eV) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| M | oxidation | 18 | 4 | 1 | 20 | 4-18 | 15 | X0 only | 0.2273 |
| M | reduction | 18 | 4 | 1 | 20 | 4-18 | 15 | X0 only | 0.1116 |
| E | oxidation | 18 | 4 | 1 | 20 | 4-18 | 15 | X0 only | 0.1641 |
| E | reduction | 18 | 4 | 1 | 20 | 4-18 | 15 | X0 only | 0.0810 |
| C | oxidation | 10 | 4 | 1 | 20 | 4-10 | 7 | X0 only | 0.1619 |
| C | reduction | 10 | 4 | 1 | 20 | 4-10 | 7 | X0 only | 0.0413 |

regret 容忍值 = 池内目标真值极差的 5%（由轨迹中的真值直接算出，不是挑出来的）。

## 2. 决策性能曲线：median τ_b 随 n_T

### M · oxidation（池大小 18）

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

### M · reduction（池大小 18）

| n_T | random | diversity | uncertainty | ranking_aware |
| --- | --- | --- | --- | --- |
| 4 | 0.314 | 0.314 | 0.314 | 0.314 |
| 5 | 0.418 | 0.412 | 0.438 | 0.431 |
| 6 | 0.439 | 0.471 | 0.469 | 0.437 |
| 7 | 0.503 | 0.503 | 0.523 | 0.455 |
| 8 | 0.562 | 0.569 | 0.595 | 0.542 |
| 9 | 0.634 | 0.647 | 0.627 | 0.614 |
| 10 | 0.725 | 0.680 | 0.686 | 0.634 |
| 11 | 0.771 | 0.758 | 0.732 | 0.654 |
| 12 | 0.784 | 0.791 | 0.771 | 0.745 |
| 13 | 0.837 | 0.843 | 0.824 | 0.810 |
| 14 | 0.869 | 0.882 | 0.850 | 0.856 |
| 15 | 0.889 | 0.935 | 0.895 | 0.922 |
| 16 | 0.928 | 0.954 | 0.935 | 0.974 |
| 17 | 0.967 | 0.974 | 0.974 | 0.987 |
| 18 | 1.000 | 1.000 | 1.000 | 1.000 |

### E · oxidation（池大小 18）

| n_T | random | diversity | uncertainty | ranking_aware |
| --- | --- | --- | --- | --- |
| 4 | 0.265 | 0.265 | 0.265 | 0.265 |
| 5 | 0.288 | 0.353 | 0.333 | 0.370 |
| 6 | 0.359 | 0.373 | 0.373 | 0.317 |
| 7 | 0.425 | 0.471 | 0.471 | 0.403 |
| 8 | 0.462 | 0.560 | 0.542 | 0.448 |
| 9 | 0.516 | 0.601 | 0.582 | 0.528 |
| 10 | 0.556 | 0.706 | 0.673 | 0.556 |
| 11 | 0.634 | 0.752 | 0.739 | 0.647 |
| 12 | 0.686 | 0.752 | 0.804 | 0.712 |
| 13 | 0.725 | 0.778 | 0.824 | 0.804 |
| 14 | 0.791 | 0.837 | 0.843 | 0.850 |
| 15 | 0.869 | 0.908 | 0.908 | 0.882 |
| 16 | 0.948 | 0.974 | 0.974 | 0.974 |
| 17 | 0.974 | 0.974 | 1.000 | 0.987 |
| 18 | 1.000 | 1.000 | 1.000 | 1.000 |

### E · reduction（池大小 18）

| n_T | random | diversity | uncertainty | ranking_aware |
| --- | --- | --- | --- | --- |
| 4 | 0.312 | 0.312 | 0.312 | 0.312 |
| 5 | 0.436 | 0.405 | 0.444 | 0.383 |
| 6 | 0.449 | 0.529 | 0.556 | 0.449 |
| 7 | 0.534 | 0.582 | 0.562 | 0.554 |
| 8 | 0.529 | 0.621 | 0.641 | 0.569 |
| 9 | 0.601 | 0.673 | 0.660 | 0.614 |
| 10 | 0.654 | 0.693 | 0.673 | 0.660 |
| 11 | 0.719 | 0.739 | 0.725 | 0.693 |
| 12 | 0.725 | 0.797 | 0.778 | 0.765 |
| 13 | 0.797 | 0.856 | 0.843 | 0.850 |
| 14 | 0.830 | 0.882 | 0.850 | 0.889 |
| 15 | 0.882 | 0.922 | 0.895 | 0.922 |
| 16 | 0.922 | 0.954 | 0.961 | 0.941 |
| 17 | 0.961 | 0.961 | 0.961 | 0.974 |
| 18 | 1.000 | 1.000 | 1.000 | 1.000 |

### C · oxidation（池大小 10）

| n_T | random | diversity | uncertainty | ranking_aware |
| --- | --- | --- | --- | --- |
| 4 | 0.346 | 0.346 | 0.346 | 0.346 |
| 5 | 0.489 | 0.489 | 0.418 | 0.418 |
| 6 | 0.511 | 0.556 | 0.511 | 0.511 |
| 7 | 0.667 | 0.733 | 0.578 | 0.600 |
| 8 | 0.733 | 0.867 | 0.822 | 0.733 |
| 9 | 0.844 | 0.956 | 0.956 | 0.867 |
| 10 | 1.000 | 1.000 | 1.000 | 1.000 |

### C · reduction（池大小 10）

| n_T | random | diversity | uncertainty | ranking_aware |
| --- | --- | --- | --- | --- |
| 4 | 0.289 | 0.289 | 0.289 | 0.289 |
| 5 | 0.333 | 0.289 | 0.378 | 0.444 |
| 6 | 0.422 | 0.489 | 0.481 | 0.467 |
| 7 | 0.600 | 0.556 | 0.600 | 0.556 |
| 8 | 0.733 | 0.689 | 0.644 | 0.733 |
| 9 | 0.867 | 0.956 | 0.956 | 0.844 |
| 10 | 1.000 | 1.000 | 1.000 | 1.000 |

## 3. 达标预算：中位数曲线 vs 多数重复

「多数重复」= 该 (target, 策略) 上有 ≥ 80% 的重复满足判据。

| 任务 | 轴 | 策略 | median τ_b≥0.80 | 多数重复 τ_b≥0.80 | 多数重复 组合达标 | 中位数曲线高估？ |
| --- | --- | --- | --- | --- | --- | --- |
| C | oxidation | diversity | 8 | 8 | 9 | 否 |
| C | oxidation | random | 9 | 10 | 10 | 是 |
| C | oxidation | ranking_aware | 9 | 10 | 10 | 是 |
| C | oxidation | uncertainty | 8 | 8 | 9 | 否 |
| C | reduction | diversity | 9 | 9 | 9 | 否 |
| C | reduction | random | 9 | 9 | 10 | 否 |
| C | reduction | ranking_aware | 9 | 10 | 10 | 是 |
| C | reduction | uncertainty | 9 | 9 | 9 | 否 |
| E | oxidation | diversity | 14 | 14 | 18 | 否 |
| E | oxidation | random | 15 | 15 | 17 | 否 |
| E | oxidation | ranking_aware | 13 | 14 | 15 | 是 |
| E | oxidation | uncertainty | 12 | 14 | 18 | 是 |
| E | reduction | diversity | 13 | 13 | 13 | 否 |
| E | reduction | random | 14 | 15 | 18 | 是 |
| E | reduction | ranking_aware | 13 | 14 | 14 | 是 |
| E | reduction | uncertainty | 13 | 14 | 14 | 是 |
| M | oxidation | diversity | 13 | 13 | 16 | 否 |
| M | oxidation | random | 13 | 15 | 16 | 是 |
| M | oxidation | ranking_aware | 13 | 15 | 15 | 是 |
| M | oxidation | uncertainty | 12 | 13 | 15 | 是 |
| M | reduction | diversity | 13 | 13 | 17 | 否 |
| M | reduction | random | 13 | 14 | 18 | 是 |
| M | reduction | ranking_aware | 13 | 14 | 15 | 是 |
| M | reduction | uncertainty | 13 | 14 | 18 | 是 |

## 4. 策略是否比 random 更省昂贵标签

在同一 (repeat, n_T) 上把每个非随机策略与其配对的 random 比较（20 次重复 × 公共 n_T）。

| 任务 | 轴 | 策略 | 配对数 | τ_b 胜率 | 打平率 | Δτ_b 中位数 |
| --- | --- | --- | --- | --- | --- | --- |
| C | oxidation | diversity | 140 | 0.436 | 0.407 | +0.000 |
| C | oxidation | ranking_aware | 140 | 0.307 | 0.379 | +0.000 |
| C | oxidation | uncertainty | 140 | 0.379 | 0.400 | +0.000 |
| C | reduction | diversity | 140 | 0.329 | 0.436 | +0.000 |
| C | reduction | ranking_aware | 140 | 0.300 | 0.407 | +0.000 |
| C | reduction | uncertainty | 140 | 0.336 | 0.400 | +0.000 |
| E | oxidation | diversity | 300 | 0.637 | 0.193 | +0.039 |
| E | oxidation | ranking_aware | 300 | 0.487 | 0.200 | +0.000 |
| E | oxidation | uncertainty | 300 | 0.660 | 0.177 | +0.052 |
| E | reduction | diversity | 300 | 0.563 | 0.183 | +0.026 |
| E | reduction | ranking_aware | 300 | 0.480 | 0.173 | +0.000 |
| E | reduction | uncertainty | 300 | 0.507 | 0.210 | +0.009 |
| M | oxidation | diversity | 300 | 0.593 | 0.210 | +0.031 |
| M | oxidation | ranking_aware | 300 | 0.383 | 0.170 | +0.000 |
| M | oxidation | uncertainty | 300 | 0.587 | 0.173 | +0.039 |
| M | reduction | diversity | 300 | 0.420 | 0.190 | +0.000 |
| M | reduction | ranking_aware | 300 | 0.397 | 0.190 | +0.000 |
| M | reduction | uncertainty | 300 | 0.400 | 0.187 | +0.000 |

## 5. 池内 vs 跨家族（口径诚实声明）

| 任务 | 轴 | 池 | 池内端点 τ_b | 静态 LOFO τ_b | LOFO 最优模型 | AL family-held-out |
| --- | --- | --- | --- | --- | --- | --- |
| C | oxidation | 10 | 1.000 | +0.111 | krr | 不可用 |
| C | reduction | 10 | 1.000 | +0.422 | gbdt | 不可用 |
| E | oxidation | 18 | 1.000 | +0.843 | ridge | 不可用 |
| E | reduction | 18 | 1.000 | +0.686 | rf | 不可用 |
| M | oxidation | 18 | 1.000 | +0.294 | krr | 不可用 |
| M | reduction | 18 | 1.000 | +0.359 | rf | 不可用 |

池内端点的 τ_b 恒为 1.0，是「已标注用真值、未标注用预测」的**自检端点**，不是成绩；
静态 LOFO 参照（同一廉价特征集的留一家族结果）最高只有 0.843。冻结 replay 里没有
family-held-out 的 AL 曲线，本阶段如实标注为**缺口**，不做任何外推。

## 6. 验收问题

- **Q1_budget_curve_improves**：四个策略的 median tau_b 是否都随 n_T 单调改善？ → 20/24 条 median tau_b 曲线单调不减（违例 4 处）
  - 反例：E|oxidation|ranking_aware;E|reduction|random;M|oxidation|random;M|oxidation|ranking_aware
- **Q2_strategy_beats_random**：非随机策略是否比 random 更省昂贵标签（用「多数重复达标」预算衡量）？ → 更省 12 个组合 / 更贵 2 个 / 打平 4 个
  - 反例：E|oxidation|diversity(costs +1);E|oxidation|uncertainty(costs +1)
- **Q3_majority_of_repeats**：达标是否在多数重复中成立，而不是只在中位数曲线上成立？ → 14/24 个 (task, axis, baseline) 的中位数曲线比「多数重复」更早达标（高估）
  - 反例：C|oxidation|random;C|oxidation|ranking_aware;C|reduction|ranking_aware;E|oxidation|ranking_aware;E|oxidation|uncertainty;E|reduction|random;E|reduction|ranking_aware;E|reduction|uncertainty;M|oxidation|random;M|oxidation|ranking_aware;M|oxidation|uncertainty;M|reduction|random;M|reduction|ranking_aware;M|reduction|uncertainty
- **Q4_inpool_vs_family_heldout**：池内（in-pool）曲线饱和是否等于跨家族泛化？ → 不等价：冻结 replay 只有池内插值，family-held-out 的 AL 曲线不可用；池内端点 tau_b 恒为 1.0（自检端点），静态 LOFO 参照最高也只有 +0.843

## 7. 一致性自检（10 项）

- `curves_recomputed_from_runs_within_storage_precision`: PASS -- 从逐 repeat 记录重算 296 个曲线单元格的 median 与 2.5/97.5 百分位，全部落在发布精度容差内（max |diff| tau_b=8.500e-07, overlap=1.750e-07, regret=7.000e-06；最大残差仅相当于 3.00 个 6 存储步长）；超容差 0
- `every_frozen_curve_cell_recombined`: PASS -- 冻结曲线的 296 个 (task, axis, baseline, n_T) 单元格全部被重算覆盖，缺失 0
- `protocol_matches_frozen_ledger`: PASS -- 池大小 / n_T 范围 / repeats=20 / 四 baseline / k=10,20,30%% / acquisition 特征 = X0 only 与 stage8_al_results.json 一致；计数 296 curves / 5920 runs / 7360 trajectories，GPR 回落 0 次
- `sequential_acquisition_prefix_property`: PASS -- 480 条 (task, axis, baseline, repeat) 采集轨迹，step 连续且每一步是全新分子（无重复 query），因此 n_T 的已查询集合严格是 n_T+1 的前缀
- `success_criteria_preregistered_and_uniform`: PASS -- 四个成功判据（tau_b >= 0.80；Top-20% overlap 全中；regret <= 池内目标极差的 5%；且在 >= 80% 重复中成立）写死在代码里、对所有 296 个单元格一律适用；容忍值由公式推出（每 target 一个值），无逐格调参
- `bands_ordered_and_bracketing`: PASS -- 全部 296 个单元格满足 2.5% <= median <= 97.5%（反例 0）
- `strategy_effect_quantified`: PASS -- 18 个 (task, axis, 非random baseline) 组都在同一 (repeat, n_T) 上与 random 配对比较，给出胜负率与 tau_b 收益中位数
- `family_coverage_computed`: PASS -- 296 个单元格都算了已查询集合覆盖的家族数（中位数/最小/最大）；覆盖数随 n_T 单调不减且不超过池内家族数
- `family_heldout_gap_declared`: PASS -- 6 个 target 的池内端点 tau_b 恒为 1.0（自检端点，不是成绩）；静态 LOFO 参照最高 0.843；**AL family-held-out 曲线不可用**（需要重跑 acquisition），已逐行标注
- `zero_new_electronic_structure`: PASS -- 唯一输入是 outputs/week7 的 Stage 8 冻结 replay 与 Stage 7 冻结 ML 结果；未运行任何电子结构作业，也未重跑 acquisition loop

## 8. 限制

- 零新增计算；Gate 1 仍 NOT CLOSED。本阶段是**computational-target** 陈述。
- core set 只有 18（C 任务 10）个分子，每 target 只有 15（C 为 7）个预算点；
  20 次重复的 2.5/97.5 百分位本身很粗。只比较**方法的相对行为**。
- 成功标准是内部操作性标准，未经外部校准；不得读成「真实项目需要买多少张 DFT」。
- posterior sampling 来自 GPR 后验协方差（样本 256），未做 uncertainty calibration；
  在 18 个点上无法做可信校准，这一点必须重申。
- family-held-out 的 AL 曲线不可用；如需要，须重跑 acquisition（不在本阶段范围）。
- 下一步 WP7（Week 34）：外部参考分层与 Gate 1 结论边界。

## 9. 复现命令

```powershell
cd 电解液溶剂HB-Code
.venv\Scripts\python.exe scripts\build_week33_wp6_active_learning_budget.py
.venv\Scripts\python.exe scripts\build_week33_wp6_active_learning_budget.py --check
.venv\Scripts\python.exe -m pytest tests/test_week33_wp6_active_learning_budget.py -q
```
