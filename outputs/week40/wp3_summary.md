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

## 验收（5/5 通过）

| check | ok | detail |
| --- | --- | --- |
| pairwise_recompute_matches_frozen_counts | PASS | recomputed={"ROBUST_INVERSION": 2, "STABLE": 55, "UNRESOLVED": 9} frozen={"ROBUST_INVERSION": 2, "STABLE": 55, "UNRESOLVED": 9} |
| no_robust_inversion_hidden_by_rounding | PASS | n_robust_inversion=2 |
| resolution_curve_monotone | PASS | f_unresolved=0.136363636,0.196969697,0.227272727,0.333333333 |
| sigma_not_from_free_Li_difference | PASS | sigma 取该 rung 的 relaxation displacement 总体标准差（0.206521 eV） |
| mechanism_cases_at_most_three | PASS | n_cases=2 |

## 限制

- 首轮只用**单一既有 rung**演示；多方法保守区间待 WP1 生产单点完成后才有真正的方法范围。
- n=12 时主选集固定 k=3（辅助 k=2/4）；pairwise unresolved 不任意变成标准 tau_b 的相等值。
- 未解析关系不一定传递；优先用偏序 / 集合与显式政策带，而不是强行排名。
