# Week 32 / WP5：Δ-learning 与跨家族泛化（RQ4 前半）

> 阶段：下一阶段实施方案 WP5（RQ4 前半）。产物目录 `outputs/week32/`，交付镜像
> `..\成果输出（part2）\week32/`。本文件由 `scripts/build_week32_wp5_delta_learning.py`
> 确定性生成，`--check` 逐字节复核。**零新增电子结构计算**：输入是 Week 7 的冻结产物。

## 0. 一句话结论

在**相同标签数**下，Δ-learning（预测位移 Δ = P_T − P_cheap）相对 direct 的表现：部分成立：6/8 个 (任务,特征集,轴) 在 LOFO 下 Delta-learning 的 tau_b 更高。
但在 C 任务的**还原轴**上 Δ-learning 并不占优，而且「数值变好」与「选择变好」并不等价（见第 4 节）。

## 1. 特征成本硬约束（X2 审计）

| 任务 | 特征集 | 成本级别 | 列数 | 用到 X2？ | 允许 |
| --- | --- | --- | --- | --- | --- |
| M | X0 | X0 | 12 | 否 | 是 |
| E | X0+P1 | X1 | 14 | 否 | 是 |
| C | X0 | X0 | 12 | 否 | 是 |
| C | X0+X1 | X1 | 18 | 否 | 是 |

X2（`x2_li_min_distance_a` / `x2_dgdg_bind_ev` / `x2_li_contacts_n` / `x2_motif_switch`）
必须完成 Li-complex DFT 之后才能获得，只允许做机制解释。预测 C1 时使用 X2 是循环论证；
本阶段把「C 任务只用 X0 / X0+X1」写成断言 `feature_cost_hard_constraint_holds`。

## 2. 跨家族泛化：random / group / LOFO

`optimism = tau_LOFO − tau_random`：正值表示按随机划分汇报把成绩说高了。

| 任务 | 特征集 | 轴 | 模型 | 形状 | tau_random | tau_group | tau_LOFO | LOFO−random |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| C | X0 | oxidation | gpr | shift | 0.644 | 0.600 | 0.600 | -0.044 |
| C | X0 | oxidation | krr | shift | 0.733 | 0.600 | 0.644 | -0.089 |
| C | X0 | reduction | gpr | shift | -0.467 | -0.289 | -0.289 | +0.178 |
| C | X0 | reduction | krr | shift | -0.200 | -0.289 | 0.022 | +0.222 |
| C | X0+X1 | oxidation | gpr | shift | 0.600 | 0.600 | 0.600 | +0.000 |
| C | X0+X1 | oxidation | krr | shift | 0.644 | 0.733 | 0.556 | -0.089 |
| C | X0+X1 | reduction | gpr | shift | -0.289 | 0.022 | 0.022 | +0.311 |
| C | X0+X1 | reduction | krr | shift | -0.289 | -0.511 | -0.111 | +0.178 |
| E | X0+P1 | oxidation | gpr | shift | 0.948 | 0.922 | 0.908 | -0.039 |
| E | X0+P1 | oxidation | krr | shift | 0.922 | 0.895 | 0.882 | -0.039 |
| E | X0+P1 | reduction | gpr | shift | 0.569 | 0.621 | 0.634 | +0.065 |
| E | X0+P1 | reduction | krr | shift | 0.725 | 0.673 | 0.739 | +0.013 |
| M | X0 | oxidation | gpr | shift | 0.647 | 0.516 | 0.542 | -0.105 |
| M | X0 | oxidation | krr | shift | 0.621 | 0.608 | 0.569 | -0.052 |
| M | X0 | reduction | gpr | shift | 0.359 | 0.346 | 0.242 | -0.118 |
| M | X0 | reduction | krr | shift | 0.399 | 0.255 | 0.307 | -0.092 |

全部 96 个 (任务,特征集,轴,模型,形状) 组合的 `LOFO−random` 中位数 = -0.039；正值与负值同时存在，说明随机划分不是单向乐观。

## 3. Δ-learning vs direct（LOFO）

| 任务 | 特征集 | 轴 | best direct | best shift | Δtau_b | ΔMAE (eV) | ΔO20% | Δregret (eV) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| C | X0 | oxidation | krr | krr | +0.533 | -0.451 | +0.50 | -1.1324 |
| C | X0 | reduction | gbdt | krr | -0.400 | +0.185 | +0.00 | -0.1452 |
| C | X0+X1 | oxidation | ridge | rf | +0.400 | -0.454 | +1.00 | -1.7407 |
| C | X0+X1 | reduction | gbdt | ridge | -0.089 | +0.131 | +0.50 | -0.1754 |
| E | X0+P1 | oxidation | ridge | rf | +0.078 | -0.123 | +0.00 | +0.0000 |
| E | X0+P1 | reduction | rf | krr | +0.052 | -0.027 | +0.00 | -0.0321 |
| M | X0 | oxidation | krr | constant | +0.301 | -0.321 | +0.00 | -0.4310 |
| M | X0 | reduction | rf | constant | +0.196 | +1.732 | +0.50 | -0.6074 |

## 4. 数值变好 ≠ 选择变好

组内 6 个模型上，MAE 排名与 tau_b 排名的 Spearman 秩相关范围 `[-0.986, 0.714]`；MAE 最优的模型同时是 tau_b 最优的只有 19/48 个组。

**这就是实施方案要求同时报 MAE 与筛选指标的原因**：只看 MAE 会选出对材料筛选没有帮助的模型。

## 5. 状态身份分层（R13 闸门）

| 轴 | 身份标签 | 分子 |
| --- | --- | --- |
| oxidation | molecule_centered_redox | DMC;DME;EC;GBL;SL;TMP |
| oxidation | no_intact_minimum_found | AN;DMSO;DOL;SN |
| reduction | Li_centered_or_mixed_redox | AN;DMC;DME;DMSO;DOL;EC;GBL;SL;TMP |
| reduction | molecule_centered_redox | SN |

与 Week 30 完全一致：还原轴 10 个分子里 9 个外加电子落在 Li 上，只有 SN 保持分子中心还原。
因此 C 任务的还原轴条件回归**只能在 SN 上做（n=1）**，本阶段按实施方案把它标为探索性，
不并入正式结论。

## 6. 与冻结 Stage 7 表的对账（残差逐条归因）

从 `stage7_ml_predictions.csv` 的逐分子 OOF 预测独立重算 288 个组合：

| 指标 | 最大绝对差 | 逐位相同的组合数 |
| --- | --- | --- |
| Top-20% overlap | 0.000e+00 | 288 / 288 |
| Jaccard@20% | 3.333e-07 | 169 / 288 |
| MAE (eV) | 3.800e-05 | 8 / 288 |
| tau_b | 3.026e-02 | 24 / 288 |
| selection regret (eV) | 2.931e-01 | 36 / 288 |

冻结的预测表按 ~6 位小数存储，因此两条预测之差小于存储分辨率（2e-05）时，排序关系会改变。
本阶段的 7 个 tau_b 分歧与 1 个 regret 离群**全部**落在 35 个这样的组合上
（`tau_mismatches_explained=True`、`regret_outliers_explained=True`）；Top-k overlap 则逐位相同。

## 7. 验收问题

- **Q1_label_efficiency** 在相同标签数下，Delta-learning 是否比 direct model 更好？ → 部分成立：6/8 个 (任务,特征集,轴) 在 LOFO 下 Delta-learning 的 tau_b 更高
  - 反例：C|X0|reduction;C|X0+X1|reduction
- **Q2_holds_under_lofo** 这个优势是否在 LOFO 下保留（三种拆分符号是否一致）？ → 6/8 个 (任务,特征集,轴) 在 random/group/LOFO 三种拆分下符号一致
  - 反例：E|X0+P1|reduction;M|X0|reduction
- **Q3_screening_conversion** 优势是否真正转化为筛选收益（Top-k overlap 不降且 regret 不升）？ → LOFO 下 6/6 个 tau_b 更好的组合同时不劣于 direct 的筛选指标
- **Q4_metric_vs_selection** MAE 排名与筛选排名是否一致（数值变好是否等于选择变好）？ → 19/48 个组里 MAE 最优的模型同时是 tau_b 最优（29 个组不是）；2 个组的 Spearman(MAE, tau_b) 为正 —— 数值越好、选择反而越差

## 8. 一致性自检

- `feature_cost_hard_constraint_holds`: PASS -- 4 个 (任务,特征集) 组合全部不含 X2 列；C 任务只用 X0/X0+X1（Li-donor 距离 / 电荷重排永不进入输入）
- `oof_metrics_reconciled_with_stage7`: PASS -- 从 stage7 的逐分子 OOF 预测独立重算 288 个 (任务,特征集,轴,模型,拆分,形状)：Top-20% overlap 逐位相同；Jaccard 差 3.333e-07；MAE 差 3.800e-05；tau_b 分歧 7 个、regret 离群 1 个，全部落在「两条预测之差 <= 存储分辨率 2e-05」的 35 个组合上
- `every_frozen_cell_recomputed`: PASS -- 冻结 stage7_ml_results 的 288 行全部被重算覆盖，缺失 0
- `state_identity_gate_matches_week30`: PASS -- C0->C1 状态身份分层：氧化轴 molecule_centered 6 个 / no_intact_minimum 4 个；还原轴 Li_centered 9 个 / molecule_centered 1 个（SN）——与 Week 30 的 R13 闸门一致
- `delta_learning_direction_reported`: PASS -- 4 个验收问题都给出结论、支撑数与反例：Q1_label_efficiency; Q2_holds_under_lofo; Q3_screening_conversion; Q4_metric_vs_selection
- `screening_conversion_checked`: PASS -- 48 个 (任务,特征集,轴,拆分,形状) 组内各 6 个模型都算了 MAE 排名与 tau_b/overlap 排名的秩相关；MAE 最优同时是 tau_b 最优的有 19 个组
- `cross_family_optimism_quantified`: PASS -- 96 个 (任务,特征集,轴,模型,形状) 都给出 random/group/LOFO 三个 tau_b 与两个乐观偏差量
- `zero_new_electronic_structure`: PASS -- 唯一输入是 outputs/week7 的 Stage 7 冻结产物与 outputs/week5 的 C1 状态身份表；未运行任何电子结构作业

## 9. 限制

- 零新增计算；Gate 1 仍 NOT CLOSED，本阶段不提供任何外部有效性支持。
- core set 只有 18 个分子（C 任务 10 个），LOFO 每一折都是「预测一个从未见过的家族」，
  某些家族只有 1 个分子，该折等价于单点外推；本阶段用于暴露方法学差异，不是定量精度结论。
- C 任务还原轴的身份闸门后只剩 SN（n=1），只能作探索性分析。
- 结论依赖 Stage 7 的冻结预测；本阶段是复算与再解释，不是重训。
- 下一步 WP6（Week 33）：最小昂贵信息预算（主动学习四策略、多种子、决策性能曲线）。

## 10. 复现命令

```powershell
cd 电解液溶剂HB-Code
.venv\Scripts\python.exe scripts\build_week32_wp5_delta_learning.py
.venv\Scripts\python.exe scripts\build_week32_wp5_delta_learning.py --check
.venv\Scripts\python.exe -m pytest tests/test_week32_wp5_delta_learning.py -q
```
