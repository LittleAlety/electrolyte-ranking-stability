# Figure manifest - Week 7 / Stage 7+8 (F16, F17)

| figure | file | figure SHA256 | inputs (SHA256) |
| --- | --- | --- | --- |
| F16 | `F16_stage7_direct_vs_shift.png` | 3c3d8322179dc35a4088aa1134621be688aa224acbde6cc1c6c7d41af522ec08 | `stage7_ml_results.csv` 944aa9ad74137375bc45d2f92e891da2f29c4fab11597c6c2973fa163f917475 |
| F17 | `F17_stage8_active_learning.png` | b3802b8b870c6beecc9cbafc82cdd9d8c35531f67ded255335e9a36897f6fa11 | `stage8_al_curves.csv` cddf05f9d899fcda8524a2dabaceec9218cf8970267208ab48860960df93632c |

F16 panel (a): the best model of each shape under leave-one-family-out; whiskers are the bootstrap/median interval stored in the results CSV. Panel (b): the same selected combination read under random, group and LOFO splits - the gap between the grey and purple bar is the optimism of a random split. Panel (c): tau_b(shift) - tau_b(direct) for every model in the prereg complexity ladder.

F17: n_T -> Kendall tau_b for random / diversity / uncertainty / ranking-aware acquisition, median over 20 frozen-seed repeats with a 2.5-97.5 percentile band; the dashed line is tau_b = 0.8. The bottom panel is the last non-trivial point (n_T = n - 1), where every curve still has one unlabelled candidate. The trivial endpoint n_T = n (tau_b = 1 by construction) is deliberately not plotted.

