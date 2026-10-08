# Pairwise decision state + resolution curve（R13）

> 由 `scripts/decision_state_report.py` 从冻结的 Week-4 判据表现算；不跑新电子结构。
> 判据口径：`|dP| >= z·sigma` 才算 resolve；`f_robust_inv = 0` 只有在 UNRESOLVED 很小时才意味着稳定。

## 三态计数（z = 1.0）

| rung | axis | n | n_pairs | STABLE | UNRESOLVED | ROBUST_INVERSION | f_UNRESOLVED | f_ROBUST_INV |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P0->P1v | oxidation | 18 | 153 | 83 | 70 | 0 | 0.458 | 0.000 |
| P0->P1v | reduction | 18 | 153 | 44 | 109 | 0 | 0.712 | 0.000 |
| P1v->P2a | oxidation | 18 | 153 | 125 | 28 | 0 | 0.183 | 0.000 |
| P1v->P2a | reduction | 18 | 153 | 94 | 59 | 0 | 0.386 | 0.000 |
| P0->P2a | oxidation | 18 | 153 | 84 | 69 | 0 | 0.451 | 0.000 |
| P0->P2a | reduction | 18 | 153 | 40 | 113 | 0 | 0.739 | 0.000 |

## 分辨率曲线 f_unresolved(z)

| rung | axis | model | z = 1.0 | z = 1.645 | z = 1.96 | z = 2.576 |
| --- | --- | --- | --- | --- | --- | --- |
| P0->P1v | oxidation | P_cheap | 0.359 | 0.529 | 0.549 | 0.614 |
| P0->P1v | oxidation | P_target | 0.157 | 0.281 | 0.359 | 0.542 |
| P0->P1v | reduction | P_cheap | 0.170 | 0.523 | 0.706 | 0.778 |
| P0->P1v | reduction | P_target | 0.621 | 0.680 | 0.699 | 0.771 |
| P1v->P2a | oxidation | P_cheap | 0.092 | 0.176 | 0.203 | 0.275 |
| P1v->P2a | oxidation | P_target | 0.111 | 0.209 | 0.255 | 0.333 |
| P1v->P2a | reduction | P_cheap | 0.235 | 0.366 | 0.438 | 0.497 |
| P1v->P2a | reduction | P_target | 0.222 | 0.373 | 0.425 | 0.556 |
| P0->P2a | oxidation | P_cheap | 0.301 | 0.444 | 0.503 | 0.608 |
| P0->P2a | oxidation | P_target | 0.229 | 0.366 | 0.418 | 0.582 |
| P0->P2a | reduction | P_cheap | 0.105 | 0.431 | 0.667 | 0.778 |
| P0->P2a | reduction | P_target | 0.680 | 0.725 | 0.745 | 0.784 |

> 读法：曲线告诉你「在 1σ / 90% / 95% / 99% 证据门槛下，多少 pair 根本无法解析」。
> f_robust_inv = 0 且 f_unresolved 高，其含义是 `evidence insufficient to resolve the ranking`，而不是 ranking stable。

