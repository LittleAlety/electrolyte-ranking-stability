# F56 · R14 收口汇总图（R13 阶段）

> 由 `scripts/analyze_r13_summary_figure.py` 从已冻结产物现算，不跑新电子结构。

**判据**：pair 级判据 resolved(i,j) <=> |dP_ij| >= max(z*sigma_ij, delta_m)；STABLE / UNRESOLVED / ROBUST_INVERSION 三态主口径 z = 1.0。

## (a) 三态计数（z = 1.0）

| rung | axis | n | n_pairs | τ_b | STABLE | UNRESOLVED | ROBUST_INVERSION | f_UNRESOLVED |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P0->P1v | oxidation | 18 | 153 | 0.673 | 83 | 70 | 0 | 0.458 |
| P0->P1v | reduction | 18 | 153 | 0.595 | 44 | 109 | 0 | 0.712 |
| P1v->P2a | oxidation | 18 | 153 | 0.895 | 125 | 28 | 0 | 0.183 |
| P1v->P2a | reduction | 18 | 153 | 0.673 | 94 | 59 | 0 | 0.386 |
| P0->P2a | oxidation | 18 | 153 | 0.673 | 84 | 69 | 0 | 0.451 |
| P0->P2a | reduction | 18 | 153 | 0.791 | 40 | 113 | 0 | 0.739 |

## (b) 分辨率曲线 f_unresolved(z)（目标模型）

| rung | axis | z = 1 | z = 1.645 | z = 1.96 | z = 2.576 |
| --- | --- | --- | --- | --- | --- |
| P0->P1v | oxidation | 0.157 | 0.281 | 0.359 | 0.542 |
| P0->P1v | reduction | 0.621 | 0.680 | 0.699 | 0.771 |
| P1v->P2a | oxidation | 0.111 | 0.209 | 0.255 | 0.333 |
| P1v->P2a | reduction | 0.222 | 0.373 | 0.425 | 0.556 |
| P0->P2a | oxidation | 0.229 | 0.366 | 0.418 | 0.582 |
| P0->P2a | reduction | 0.680 | 0.725 | 0.745 | 0.784 |

## (c) Gate 1 双轨定性

| 轨道 | 状态 |
| --- | --- |
| Track A（decision stability） | **computationally established** |
| Track B（external / experimental validity） | **NOT CLOSED / NOT CLOSABLE** |

- 排序一致性层：τ_b = 0.4286 < 0.90，n_pairs = 21。
- 可闭合性：最长同装置 / 同判据同源序列 k = 1，要求 ≥ 7 个核心集分子。
- 绝对标定层：31 行仍 `est`，升级 0 行。

## (d) 防误读卡片

```text
0 robust inversions
  ≠
0 ranking instability
```

- robust inversion: **0 observed**（20 个（阶梯, 轴）组合）。
- unresolved: **up to 80.0%**（C0→to→C1 · 还原轴）。
- 唯一真正出现 robust inversion 的地方：P1v→P1a 绝热阶梯（n = 12，2 个）。

> 本图不跑任何新电子结构；所有数字均为已冻结产物的现算读出。robust inversion = 0 的含义是 evidence insufficient to resolve，不是 ranking stable；不得把本图读成「18 个溶剂的最终性能排名」。

