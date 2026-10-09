# Week 32 / WP5：Δ-learning 与跨家族泛化（RQ4 前半）

> 阶段：下一阶段实施方案 WP5（RQ4 前半）。产物目录 `outputs/week32/`，交付镜像
> `..\成果输出（part2）\week32/`。数字由 `scripts/build_week32_wp5_delta_learning.py`
> 确定性生成，`--check` 逐字节复核。**零新增电子结构计算**：唯一输入是 Week 7 的冻结产物
> （`stage7_ml_predictions.csv` / `stage7_ml_results.csv`）与 Week 5 的 C1 状态身份表
> （`c1_state_identity.csv`）。

## 0. 本轮解决的问题

WP4 把「一次 Top-k 筛选到底知道多少」讲清楚了。WP5（RQ4 前半）换一个问法：**能不能用更少的
昂贵标签，得到同样的筛选决策**。具体是三个问题：

```
Q1  Δ-learning（预测位移 Δ = P_T − P_cheap）是否比 direct model 更省标签？
Q2  这个优势是否在「留一家族」（LOFO）下保留？
Q3  优势是否真正转化为筛选收益（Top-k overlap 不降且 selection regret 不升）？
```

本阶段不重跑 Stage 7 管线，而是用它的**逐分子 out-of-fold 预测**独立重算 MAE / Kendall τ_b /
Top-20% overlap / Jaccard / selection regret，先与冻结结果逐位对账（见第 6 节），再做比较。
三种拆分口径：`random`（KFold，多种子取均值）、`group`（leave-one-group-out，按 `group_key`
脚手架分组）、`lofo`（leave-one-family-out，按 `family` 留一家族）。两种模型形状：`direct`
（直接回归目标）与 `shift`（回归位移 Δ，再加回便宜参考）。模型 6 个：`constant`（家族均值
基线）、`ridge`、`krr`、`gpr`、`rf`、`gbdt`。

三层表述纪律贯穿本文件，三者不得混写：

| 表述层 | 本阶段落地表 |
| --- | --- |
| 模型事实 | `feature_cost_audit`、`cross_family_generalization` |
| 统计判定 | `delta_vs_direct`、`screening_conversion`、`oof_metrics_reconciliation` |
| 材料意义 | `state_identity_stratification`、`wp5_acceptance` |

## 1. 特征成本硬约束（X2 审计）

| 任务 | 特征集 | 成本级别 | 列数 | 用到 X2？ | 允许 |
| --- | --- | --- | --- | --- | --- |
| M | X0 | X0 | 12 | 否 | 是 |
| E | X0+P1 | X1 | 14 | 否 | 是 |
| C | X0 | X0 | 12 | 否 | 是 |
| C | X0+X1 | X1 | 18 | 否 | 是 |

X2（`x2_li_min_distance_a` / `x2_dgdg_bind_ev` / `x2_li_contacts_n` / `x2_motif_switch`）
必须完成 Li-complex DFT 之后才能获得，只允许做机制解释。预测 C1 时使用 X2 是循环论证；
本阶段把「C 任务只用 X0 / X0+X1」写成断言 `feature_cost_hard_constraint_holds`，而不是靠约定。

## 2. 跨家族泛化：random / group / LOFO

`optimism = tau_LOFO − tau_random`：正值表示按随机划分汇报把成绩说高了。下表列 `shift` 形状的
`gpr` / `krr` 两个模型（完整 96 行见 `cross_family_generalization.csv`）。

| 任务 | 特征集 | 轴 | 模型 | tau_random | tau_group | tau_lofo | LOFO−random |
| --- | --- | --- | --- | --- | --- | --- | --- |
| C | X0 | oxidation | gpr | 0.644 | 0.600 | 0.600 | -0.044 |
| C | X0 | oxidation | krr | 0.733 | 0.600 | 0.644 | -0.089 |
| C | X0 | reduction | gpr | -0.467 | -0.289 | -0.289 | +0.178 |
| C | X0 | reduction | krr | -0.200 | -0.289 | 0.022 | +0.222 |
| C | X0+X1 | oxidation | gpr | 0.600 | 0.600 | 0.600 | +0.000 |
| C | X0+X1 | oxidation | krr | 0.644 | 0.733 | 0.556 | -0.089 |
| C | X0+X1 | reduction | gpr | -0.289 | 0.022 | 0.022 | +0.311 |
| C | X0+X1 | reduction | krr | -0.289 | -0.511 | -0.111 | +0.178 |
| E | X0+P1 | oxidation | gpr | 0.948 | 0.922 | 0.908 | -0.039 |
| E | X0+P1 | oxidation | krr | 0.922 | 0.895 | 0.882 | -0.039 |
| E | X0+P1 | reduction | gpr | 0.569 | 0.621 | 0.634 | +0.065 |
| E | X0+P1 | reduction | krr | 0.725 | 0.673 | 0.739 | +0.013 |
| M | X0 | oxidation | gpr | 0.647 | 0.516 | 0.542 | -0.105 |
| M | X0 | oxidation | krr | 0.621 | 0.608 | 0.569 | -0.052 |
| M | X0 | reduction | gpr | 0.359 | 0.346 | 0.242 | -0.118 |
| M | X0 | reduction | krr | 0.399 | 0.255 | 0.307 | -0.092 |

全部 96 个 (任务,特征集,轴,模型,形状) 组合的 `LOFO−random` 中位数 = **−0.039**，正值与负值
同时存在 —— 「随机划分一定把成绩说高」这个直觉**在本数据上不成立**，必须逐配置核实。

## 3. Δ-learning vs direct（LOFO）

`best_direct` / `best_shift` 是在该组 6 个模型里**按 τ_b 取最大**选出的最优模型（不是按 MAE
选，也不是取最差）；`Δtau_b > 0` 即 Δ-learning 更好。

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

LOFO 下 6/8 个组合 Δ-learning 的 τ_b 更高；两个反例（`C|X0|reduction`、`C|X0+X1|reduction`）
都落在 **C 任务的还原轴** —— 而第 5 节说明该轴经状态身份闸门后实际上只剩 SN（n=1），
这些格子的「反例」本身不可作为材料结论，只能是方法学观察。注意 `M|X0|reduction`：
Δtau_b = +0.196 为正，但 ΔMAE = +1.732 eV 显著变差 —— 这正是第 4 节要说的「两个指标不能互替」。

## 4. 数值变好 ≠ 选择变好

统计 `screening_conversion.csv` 的 48 个 (任务,特征集,轴,拆分,形状) 组，每组 6 个模型：

- 组内 MAE 排名与 τ_b 排名的 Spearman 秩相关范围 `[-0.986, 0.714]`，中位数 `-0.657`；
  多数组为负（MAE 越小 τ_b 越大，符合直觉）。
- 「MAE 最优的模型同时是 τ_b 最优」只有 **19/48** 个组；
- 「MAE 最优同时是 Top-20% overlap 最优」只有 **12/48** 个组；
- **2 个组为正**（`C|X0|oxidation` 的 `direct`，`group` 与 `lofo` 两个拆分，ρ = 0.714 / 0.638）——
  即**数值越好、排序/选择反而越差**。

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

从 `stage7_ml_predictions.csv` 的逐分子 OOF 预测独立重算 288 个 (任务,特征集,轴,模型,拆分,
形状) 组合，与冻结的 `stage7_ml_results.csv` 比较：

| 指标 | 最大绝对差 | 逐位相同的组合数 |
| --- | --- | --- |
| Top-20% overlap | 0.000e+00 | 288 / 288 |
| Jaccard@20% | 3.333e-07 | 169 / 288 |
| MAE (eV) | 3.800e-05 | 8 / 288 |
| tau_b | 3.026e-02 | 24 / 288 |
| selection regret (eV) | 2.931e-01 | 36 / 288 |

冻结的预测表按 ~6 位小数存储，因此两条预测之差小于存储分辨率（`STORAGE_RESOLUTION = 2e-05`）
时，排序关系会改变。本阶段的 **7 个 τ_b 分歧**与 **1 个 regret 离群**全部落在 35 个这样的
「近并列」组合上（`tau_mismatches_explained = True`、`regret_outliers_explained = True`）；
Top-20% overlap 逐位相同。这里**不采取放宽容差抹掉分歧**的做法，只做逐条归因。

需要分开说清楚的是：**MAE 与 Jaccard 的残差不是近并列造成的**，而是发布精度（预测值 6 位
有效数字、指标 6 位小数）带来的量化残差，全部远低于参考容差（MAE ≤ 3.8e-05 ≪ 1e-4、
Jaccard ≤ 3.34e-07 ≪ 1e-6）。近并列归因只对 τ_b 与 regret 成立。

7 个 τ_b 分歧键：`M|X0|oxidation|gpr|random|direct`、`C|X0|oxidation|gpr|random|direct`、
`C|X0|reduction|gpr|random|direct`、`C|X0+X1|oxidation|gpr|random|direct`、
`C|X0+X1|reduction|gpr|random|direct`、`C|X0+X1|reduction|gpr|group|direct`、
`C|X0+X1|reduction|gpr|lofo|direct`。

## 7. 验收问题

- **Q1_label_efficiency**：在相同标签数下，Δ-learning 是否比 direct model 更好？
  → **部分成立**：6/8 个 (任务,特征集,轴) 在 LOFO 下 Δ-learning 的 τ_b 更高
  （`C|X0|oxidation` +0.533、`C|X0+X1|oxidation` +0.400、`E|X0+P1|oxidation` +0.078、
  `E|X0+P1|reduction` +0.052、`M|X0|oxidation` +0.301、`M|X0|reduction` +0.196）。
  反例：`C|X0|reduction`（−0.400）;`C|X0+X1|reduction`（−0.089）。
- **Q2_holds_under_lofo**：这个优势是否在 LOFO 下保留（三种拆分符号是否一致）？
  → **6/8** 个组合在 random/group/LOFO 三种拆分下符号一致。反例：
  `E|X0+P1|reduction`（random/group 为负、LOFO 为正）与 `M|X0|reduction`
  （group 为负、random/LOFO 为正）——**拆分选择会改变「Δ-learning 是否更好」的结论**。
- **Q3_screening_conversion**：优势是否真正转化为筛选收益（Top-k overlap 不降且 regret 不升）？
  → LOFO 下 **6/6** 个 τ_b 更好的组合同时不劣于 direct 的筛选指标（`ΔO20 ≥ 0` 且 `Δregret ≤ 0`）。
- **Q4_metric_vs_selection**：MAE 排名与筛选排名是否一致（数值变好是否等于选择变好）？
  → **19/48** 个组里 MAE 最优的模型同时是 τ_b 最优；**2 个组**的 Spearman(MAE, τ_b) > 0.5 ——
  数值越好、选择反而越差。

## 8. 一致性自检（8 项，全部 PASS）

| 自检 | 断言 |
| --- | --- |
| `feature_cost_hard_constraint_holds` | 4 个 (任务,特征集) 组合全部不含 X2 列；C 任务只用 X0 / X0+X1 |
| `oof_metrics_reconciled_with_stage7` | 288 个组合重算：overlap 逐位相同；Jaccard 差 3.333e-07；MAE 差 3.800e-05；τ_b 分歧 7、regret 离群 1，全部落在 35 个近并列组合上 |
| `every_frozen_cell_recomputed` | 冻结 `stage7_ml_results` 的 288 行全部被重算覆盖，缺失 0 |
| `state_identity_gate_matches_week30` | 氧化轴 molecule_centered 6 / no_intact_minimum 4；还原轴 Li_centered 9 / molecule_centered 1（SN） |
| `delta_learning_direction_reported` | 4 个验收问题（Q1–Q4）都给出结论、支撑数与反例 |
| `screening_conversion_checked` | 48 个组内各 6 个模型都算了 MAE 排名与 τ_b/overlap 排名的秩相关 |
| `cross_family_optimism_quantified` | 96 个组合都给出 random/group/LOFO 三个 τ_b 与两个乐观偏差量 |
| `zero_new_electronic_structure` | 唯一输入是 `outputs/week7` 的 Stage 7 冻结产物与 `outputs/week5` 的 C1 状态身份表 |

`delta_vs_direct` 的 `best_*` 列一律由 `wp5._best(..., higher_is_better=True)` 取 **τ_b 最大**，
`tests/test_week32_wp5_delta_learning.py::test_delta_vs_direct_picks_the_best_model` 固化这一口径。

## 9. 限制与下一步

- 零新增计算；Gate 1 仍 NOT CLOSED，本阶段不提供任何外部有效性支持。
- core set 只有 18 个分子（C 任务 10 个），LOFO 每一折都是「预测一个从未见过的家族」，
  某些家族只有 1 个分子，该折等价于单点外推；本阶段用于暴露方法学差异，不是定量精度结论。
- C 任务还原轴经状态身份闸门后只剩 SN（n=1），只能作探索性分析。
- 「哪种模型算最优」会改变 Δ-learning 的胜负（本阶段固定为 τ_b 最大）；报告已把口径写死在
  代码与测试里，换口径必须重新走一遍验收。
- 结论依赖 Stage 7 的冻结预测；本阶段是复算与再解释，不是重训。
- 下一步 WP6（Week 33）：最小昂贵信息预算（主动学习四策略、多种子、决策性能曲线）。

## 10. 复现命令

```powershell
cd 电解液溶剂HB-Code
.venv\Scripts\python.exe scripts\build_week32_wp5_delta_learning.py
.venv\Scripts\python.exe scripts\build_week32_wp5_delta_learning.py --check
.venv\Scripts\python.exe -m pytest tests/test_week32_wp5_delta_learning.py -q
.venv\Scripts\python.exe scripts\build_week32_deliverables.py
```