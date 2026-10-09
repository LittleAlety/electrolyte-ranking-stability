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

## 验收（9/9 通过）

| check | ok | detail |
| --- | --- | --- |
| pairwise_recompute_matches_frozen_counts | PASS | recomputed={"ROBUST_INVERSION": 2, "STABLE": 55, "UNRESOLVED": 9} frozen={"ROBUST_INVERSION": 2, "STABLE": 55, "UNRESOLVED": 9} |
| no_robust_inversion_hidden_by_rounding | PASS | n_robust_inversion=2 |
| resolution_curve_monotone | PASS | f_unresolved=0.136363636,0.196969697,0.227272727,0.333333333 |
| sigma_not_from_free_Li_difference | PASS | sigma 取该 rung 的 relaxation displacement 总体标准差（0.206521 eV） |
| mechanism_cases_at_most_three | PASS | n_cases=2 |
| robust_inversion_not_yet_certified | PASS | label=ROBUST_INVERSION x2 只表示「在该敏感性尺度下的翻转」；认证待 WP1 独立方法审计 |
| rung_cohort_difference_is_documented | PASS | rung members 含 SN 不含 DEC；主集含 DEC 不含 SN —— 已在 payload 的 rung_members_note 说明 |
| mechanism_case_geometries_are_frozen_inputs | PASS | 3 个案例分子；EMC max|Δr|=0.090 Å (C4-O5)、GBL max|Δr|=0.086 Å (C2-O6)、SL max|Δr|=0.016 Å (C5-C6) |
| mechanism_bond_table_covers_every_case_molecule | PASS | n_bond_rows=17 ; n_molecules=3 ; 变化 >0.01 A 的键 15 条 |

## 限制

- 首轮只用**单一既有 rung**演示；多方法保守区间待 WP1 生产单点完成后才有真正的方法范围。
- 该 rung 的 12 个成员与主 cohort 差一个分子（SN 进、DEC 出）：它只作判据演示，不代表已登记的主集。
- 稳健翻转**尚未认证**：本标签只表示「在该 rung 的位移 std 敏感性尺度下的翻转」，认证需 WP1 独立方法审计与采样界限（方案 2）。
- 机制案例已补原始结构证据（既有冻结几何的重原子键长变化表，逐键列出中性/阳离子键长），但电子密度/自旋、配位变化与 G 层分解仍需 WP1/WP2 新计算。
- n=12 时主选集固定 k=3（辅助 k=2/4）；pairwise unresolved 不任意变成标准 tau_b 的相等值。
- 未解析关系不一定传递；优先用偏序 / 集合与显式政策带，而不是强行排名。
