# Week 29 / WP2：哪些电子结构与介质物理改变候选排序

> 阶段：下一阶段实施方案 WP2（RQ1）。产物目录 `outputs/week29/`，交付镜像
> `..\成果输出（part2）\week29/`。本文件由 `scripts/build_week29_wp2_physics_response.py`
> 确定性生成，`--check` 逐字节复核。**零新增电子结构计算**：唯一输入是 Week 28 冻结主表。

## 0. 一句话结论

排序变化只由候选间的**差异性响应** `delta_i - delta_j` 驱动。在 core18 上，把极廉价
代理量 `P0` 换成电子结构 `P1v` 会明显改变候选选择（Top-20% overlap 0.5，氧化轴
`AN/SN` 进、`DMC/PC` 退）；而把固定连续介质 `P2a` 换成 `P1v` 只带来中等改变
（氧化轴 Top-20% overlap 0.75，仅 `DMC`/`EC` 互换）。同方法内的两个 rung —— 垂直/绝热
`P1v->P1a` 与裸介电 `P1v->P2eps10` —— 在 12 分子审计集上**不改变 Top-k 选择**：它们的
位移以家族级共同偏移为主，被家族偏移模型吸收后残差从 ~0.31 降到 ~0.15-0.19 eV。

## 1. 口径与输入

- 唯一输入：`outputs/week28/property_table.csv`、`pairwise_table.csv`、
  `decision_table.csv`、`molecule_registry.csv`。
- 恒等式：`dP_ij^B = dP_ij^A + (delta_i - delta_j)`，本阶段逐 pair 复核（见 §6）。
- 对比集合：`P0_to_P1v`、`P1v_to_P1a`、`P1v_to_P2a`、`P1v_to_P2eps10`、`P0_to_P2a`
  （C0/C1/C2 环境条件态归 WP3）。
- 统计口径：`electrolyte_ranking.ranking`（tau_b / rho / top_k_overlap / jaccard_at_k /
  selection_regret），`k = round(k_fraction * n)`。

## 2. 逐级位移与家族分层

`delta_i` 的分子级汇总（eV）：

| 对比 | 轴 | n | RMSE 共模(eV) | RMSE 家族(eV) | 族效应占比 |
| --- | --- | --- | --- | --- | --- |
| P0_to_P1v | oxidation | 18 | 1.0397 | 0.4424 | 0.8190 |
| P0_to_P1v | reduction | 18 | 3.1237 | 0.3848 | 0.9848 |
| P1v_to_P1a | oxidation | 12 | 0.3051 | 0.1853 | 0.6309 |
| P1v_to_P2a | oxidation | 18 | 0.4269 | 0.2860 | 0.5511 |
| P1v_to_P2a | reduction | 18 | 0.4532 | 0.3585 | 0.3745 |
| P1v_to_P2eps10 | oxidation | 12 | 0.3139 | 0.1507 | 0.7697 |
| P1v_to_P2eps10 | reduction | 12 | 0.3440 | 0.1862 | 0.7070 |
| P0_to_P2a | oxidation | 18 | 0.8486 | 0.2830 | 0.8888 |
| P0_to_P2a | reduction | 18 | 2.9951 | 0.3184 | 0.9887 |

家族内 / 跨家族 `mean |delta_shift|`（eV）与族效应对齐见 `family_displacement.csv`；
关键读数：还原轴 `P0->P1v` 的跨家族位移均值 (2.43) 远高于家族内 (0.34)，
族效应占比 0.985 —— 廉价代理量的误差在这个轴上基本是**家族级**的。

## 3. 三种解释模型

对 `dP_ij^B` 的三层残差（eV）：

| 对比 | 轴 | RMSE 共模 | RMSE 家族偏移 | RMSE 分子校正 | R2_family |
| --- | --- | --- | --- | --- | --- |
| P0_to_P1v | oxidation | 1.0397 | 0.4424 | 0.000e+00 | 0.8190 |
| P0_to_P1v | reduction | 3.1237 | 0.3848 | 5.946e-16 | 0.9848 |
| P1v_to_P1a | oxidation | 0.3051 | 0.1853 | 0.000e+00 | 0.6309 |
| P1v_to_P2a | oxidation | 0.4269 | 0.2860 | 0.000e+00 | 0.5511 |
| P1v_to_P2a | reduction | 0.4532 | 0.3585 | 1.675e-16 | 0.3745 |
| P1v_to_P2eps10 | oxidation | 0.3139 | 0.1507 | 0.000e+00 | 0.7697 |
| P1v_to_P2eps10 | reduction | 0.3440 | 0.1862 | 1.440e-16 | 0.7070 |
| P0_to_P2a | oxidation | 0.8486 | 0.2830 | 0.000e+00 | 0.8888 |
| P0_to_P2a | reduction | 2.9951 | 0.3184 | 4.555e-16 | 0.9887 |

分子校正按恒等式精确为 0；家族偏移把残差显著压低，说明大部分差异性响应是**家族可解释**的。

## 4. 排序响应与候选交换

| 对比 | 轴 | k/N | k | O_k | J_k | regret(eV) | tau_b | 进入 | 退出 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P0_to_P1v | oxidation | 0.2 | 4 | 0.500 | 0.333 | 0.6563 | 0.673 | AN;SN | DMC;PC |
| P0_to_P1v | reduction | 0.2 | 4 | 0.500 | 0.333 | 0.2630 | 0.595 | DEC;DMC | TEGDME;TMP |
| P1v_to_P1a | oxidation | 0.2 | 2 | 1.000 | 1.000 | 0.0000 | 0.788 | - | - |
| P1v_to_P2a | oxidation | 0.2 | 4 | 0.750 | 0.600 | 0.0272 | 0.895 | DMC | EC |
| P1v_to_P2a | reduction | 0.2 | 4 | 0.500 | 0.333 | 0.1752 | 0.673 | SL;TEGDME | DEC;DMC |
| P1v_to_P2eps10 | oxidation | 0.2 | 2 | 1.000 | 1.000 | 0.0000 | 0.909 | - | - |
| P1v_to_P2eps10 | reduction | 0.2 | 2 | 1.000 | 1.000 | 0.0000 | 0.848 | - | - |
| P0_to_P2a | oxidation | 0.2 | 4 | 0.500 | 0.333 | 0.5448 | 0.673 | AN;SN | EC;PC |
| P0_to_P2a | reduction | 0.2 | 4 | 0.750 | 0.600 | 0.0445 | 0.791 | SL | TMP |

完整 3 个 k 见 `decision_response.csv`；`frozen_*` 列是 Week 28 冻结值，逐行与重算对齐。

## 5. 分辨率约束

小样本下必须与分辨率一起读：`f_unresolved_lower` / `f_unresolved_upper` 与
`swapped_pairs_resolved_both` 给出「交换是否超出原始数据分辨能力」。
`ROBUST_INVERSION` 在 WP2 的 5 个对比里恒为 0，且这是**结构性**的
（`z = 1.0 > 1/sqrt(2)` 时反向 pair 不可能两侧同时过门槛）—— 不得读成「排序稳定」。

## 6. 一致性自检

- `displacement_reproduces_pairwise_shift`: PASS -- delta_i - delta_j 与 pairwise_table.delta_shift_ev 的最大绝对误差 1.332e-15 eV（1116 个 pair 行）
- `decision_metrics_match_week28`: PASS -- 重算的 Top-k overlap / Jaccard / regret / tau_b / rho 对齐 Week 28 decision_table，最大绝对差 overlap=0.000e+00, jaccard=0.000e+00, selection_regret_ev=0.000e+00, kendall_tau_b=0.000e+00, spearman_rho=0.000e+00
- `molecule_model_is_exact`: PASS -- 分子级校正残差 RMSE 最大值 5.946e-16 eV（恒等式应精确成立）
- `family_variance_identity`: PASS -- SS_between + SS_within = SS_total 最大偏差 0.000e+00；R2_family 与族效应占比最大偏差 3.331e-16（无序完全对下二者恒等）
- `ladder_additivity_exact`: PASS -- delta(P0->P2a) - [delta(P0->P1v) + delta(P1v->P2a)] 最大绝对误差 8.882e-16 eV
- `p1a_reduction_is_rule_excluded`: PASS -- P1v_to_P1a 还原轴在 WP2 里 0 行：气相阴离子不是束缚态，该轴按 unbound_anion 规则被排除（不读成「稳定」）
- `zero_new_electronic_structure`: PASS -- 唯一输入是 outputs/week28/*.csv；本阶段未读取任何 ORCA / xTB 原始输出，未运行任何电子结构作业

## 7. 阶梯信息增量与 bootstrap

阶梯（相对终端 P2a，core18）见 `ladder_incremental.csv`；小样本 bootstrap 区间见
`bootstrap_ci.csv`（分子级有放回，B=2000，seed=0）。

## 8. 复现命令

```powershell
.venv\Scripts\python.exe scripts\build_week29_wp2_physics_response.py
.venv\Scripts\python.exe scripts\build_week29_wp2_physics_response.py --check
.venv\Scripts\python.exe -m pytest tests/test_week29_wp2_physics_response.py -q
```
