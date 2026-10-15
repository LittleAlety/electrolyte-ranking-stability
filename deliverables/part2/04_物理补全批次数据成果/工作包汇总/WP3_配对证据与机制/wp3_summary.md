# Week 40 / WP3 — 排序、独立不确定度与机制

**状态**：三态判据与保守区间协议已冻结，并在既有 rung（P1v→P1a 氧化，n=12）上逐对复算。

## 逐对复算（66 pair）

| 判定 | 复算 | 冻结 |
| --- | --- | --- |
| STABLE | 55 | 55 |
| UNRESOLVED | 9 | 9 |
| ROBUST_INVERSION | 2 | 2 |

- 三态分辨率曲线（z = 1.0/1.645/1.96/2.576，双边判据）：f_unresolved = 0.136363636、0.196969697、0.227272727、0.333333333
- 机制案例：2 个（规则：稳健翻转优先）

## 冻结台阶逐级报告（方案 7.2，零新增计算）

| 台阶 | 轴 | n | tau_b | f_unresolved (前 -> 后) | f_robust_inversion | dispersion (eV) | 既有作业 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| P0_to_P1 | oxidation | 18 | 0.673202614 | 0.359477124 -> 0.156862745 | 0.000000000 | 0.735188017 | 54 |
| P0_to_P1 | reduction | 18 | 0.594771242 | 0.169934641 -> 0.620915033 | 0.000000000 | 2.208762743 | 54 |
| P1_to_P2 | oxidation | 18 | 0.895424837 | 0.091503268 -> 0.111111111 | 0.000000000 | 0.301842333 | 54 |
| P1_to_P2 | reduction | 18 | 0.673202614 | 0.235294118 -> 0.222222222 | 0.000000000 | 0.320472917 | 54 |
| G1_to_G2 | oxidation | 12 | 0.939393939 | 0.015151515 -> 0.030303030 | 0.000000000 | 0.051609582 | 48 |
| G1_to_G2 | reduction | 12 | 0.848484848 | 0.045454545 -> 0.060606061 | 0.000000000 | 0.079749315 | 48 |
| C0_to_C1 | oxidation | 10 | 0.688888889 | 0.177777778 -> 0.200000000 | 0.000000000 | 0.594551882 | 92 |
| C0_to_C1 | reduction | 10 | -0.466666667 | 0.444444444 -> 0.800000000 | 0.000000000 | 0.832291087 | 92 |
| C1_to_C2 | oxidation | 10 | 0.866666667 | 0.133333333 -> 0.088888889 | 0.000000000 | 0.259427412 | 36 |
| C1_to_C2 | reduction | 10 | 0.288888889 | 0.355555556 -> 0.355555556 | 0.000000000 | 0.335007649 | 36 |

- 台阶间独立性（冻结 R15）：20 对、max |Pearson| = 0.7909267873261443、median |Pearson| = 0.383067803565867、>0.7 的 2 对。
- 逐级报告 = 冻结聚合值（n / tau_b / unresolved / robust 比例）+ 用同一批逐分子分值现算的
  固定 k=3（辅助 2/4）Top-k overlap 与 selection regret（目标=高层 after、代理=低层 before，越高越稳）；
  系综 / 自由能两级台阶仍要等 WP2 生产把同一 cohort 的自由能标签补齐。

## 验收（11/11 通过）

| check | ok | detail |
| --- | --- | --- |
| pairwise_recompute_matches_frozen_counts | PASS | recomputed={"ROBUST_INVERSION": 2, "STABLE": 55, "UNRESOLVED": 9} frozen={"ROBUST_INVERSION": 2, "STABLE": 55, "UNRESOLVED": 9} |
| no_robust_inversion_hidden_by_rounding | PASS | n_robust_inversion=2 |
| resolution_curve_monotone | PASS | f_unresolved=0.136363636,0.196969697,0.227272727,0.333333333 |
| sigma_not_from_free_Li_difference | PASS | sigma 取该 rung 的 relaxation displacement 总体标准差（0.206521 eV） |
| mechanism_cases_at_most_three | PASS | n_cases=2 |
| robust_inversion_certification_follows_the_method_audit | PASS | WP1 audit certified=True (2/2 frozen pairs)；label=ROBUST_INVERSION x2 |
| rung_cohort_difference_is_documented | PASS | rung members 含 SN 不含 DEC；主集含 DEC 不含 SN —— 已在 payload 的 rung_members_note 说明 |
| mechanism_case_geometries_are_frozen_inputs | PASS | 3 个案例分子；EMC max|Δr|=0.090 Å (C4-O5)、GBL max|Δr|=0.086 Å (C2-O6)、SL max|Δr|=0.016 Å (C5-C6) |
| frozen_ladder_covers_every_registered_rung | PASS | 5 级台阶 x 2 轴 = 10 行；每行给固定 k=3（辅助 2/4）的 Top-k overlap 与 selection regret |
| wp3_ladder_topk_regret_is_computed_not_copied | PASS | n_rows=10 ; k_main=3 ; 逐分子分值取自 week4/week5/week8 的台阶表，不改动冻结数 |
| mechanism_bond_table_covers_every_case_molecule | PASS | n_bond_rows=17 ; n_molecules=3 ; 变化 >0.01 A 的键 15 条 |

## 限制

- 逐级报告（方案 7.2）= 冻结的 5 级台阶聚合值（n / tau_b / unresolved / robust 比例）加上用同一批逐分子分值现算的固定 k=3（辅助 2/4）Top-k overlap 与 selection regret；WP1 独立方法审计已给出 4 设定的方法范围（只覆盖电子能层与氧化轴）。
- 该 rung 的 12 个成员与主 cohort 差一个分子（SN 进、DEC 出）：它只作判据演示，不代表已登记的主集。
- 稳健翻转认证：WP1 独立方法审计（4 设定 × 竖直/弛豫两腿）给出 certified=True；但**采样界限仍未纳入**，故只认证方法轴（方案 2）。
- 机制案例已补原始结构证据（既有冻结几何的重原子键长变化表，逐键列出中性/阳离子键长）与 WP1 方法敏感性范围，但电子密度/自旋、配位变化与 G 层分解仍需 WP2 生产计算。
- n=12 时主选集固定 k=3（辅助 k=2/4）；pairwise unresolved 不任意变成标准 tau_b 的相等值。
- 未解析关系不一定传递；优先用偏序 / 集合与显式政策带，而不是强行排名。
