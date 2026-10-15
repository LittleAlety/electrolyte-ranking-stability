# Stage 6：不确定性感知排序分析（T9）

## 1. 本轮解决的问题

Week 5 及之前所有对比用的是**临时口径** `|dP_ij| >= z*sigma_ij`（z=1.0），预注册里一直有一个固定兜底容差 `delta_m` 却从未启用。本轮把 `delta_m` 装上，并给出它在 3 个口径下的效果差：

| 口径 | delta_m | 含义 |
|---|---|---|
| `z_only` | delta_m = 0（等于不启用固定容差） | Week 5 及之前的临时口径，作为对照基线 |
| `floor_only` | delta_m = 0.05 eV（4.8242 kJ/mol） | 只看规划文档的数值下限，隔离 delta_m 中"证据驱动"部分的效果 |
| `docx_max` | delta_m = max(构象 90 分位展宽, 方法 pstdev, 0.05 eV)，见 T8 | 主口径：完整 docx §6.2 合成规则 |

判据（全部来自 `config/prereg.yaml`）：`unresolved <=> |dP_ij| < delta_m 或 |dP_ij| < z*sigma_ij`；`f_robust_inv = N_robust / N_pairs_resolved_in_both`；`f_unresolved = N_unresolved / C(N,2)`。

## 2. 主表（docx_max 口径）

| 层对 | 目标 | n | tau_b [CI95] | rho | f_unresolved(下/上) | 双方均解析 pair 数 | delta_m 起决定作用的 pair 数 | f_robust_inv | O_20% | R_20% |
|---|---|---|---|---|---|---|---|---|---|---|
| P0_to_P1 | oxidation | 12 | 0.667 [0.13, 1.00] | 0.776 | 0.636 / 0.364 | 22 / 66 | 24 | 0.000 | 0.000 | 1.2181 |
| P0_to_P1 | reduction | 12 | 0.545 [-0.02, 0.90] | 0.741 | 0.530 / 1.000 | 0 / 66 | 30 | 0.000 | 1.000 | 0.0000 |
| P1_to_P2 | oxidation | 12 | 0.909 [0.70, 1.00] | 0.972 | 0.333 / 0.379 | 39 / 66 | 25 | 0.000 | 1.000 | 0.0000 |
| P1_to_P2 | reduction | 12 | 0.848 [0.53, 1.00] | 0.923 | 0.985 / 1.000 | 0 / 66 | 63 | 0.000 | 1.000 | 0.0000 |
| C0_to_C1 | oxidation | 10 | 0.689 [0.15, 1.00] | 0.770 | 0.311 / 0.333 | 23 / 45 | 9 | 0.000 | 1.000 | 0.0000 |
| C0_to_C1 | reduction | 10 | -0.467 [-0.95, 0.11] | -0.552 | 0.978 / 1.000 | 0 / 45 | 29 | 0.000 | 0.000 | 0.4573 |

## 3. delta_m 的效果（3 个口径对比）

| 层对 | 目标 | f_unresolved(下) z_only / floor / docx_max | f_unresolved(上) z_only / floor / docx_max | f_robust_inv z_only / floor / docx_max |
|---|---|---|---|---|
| P0_to_P1 | oxidation | 0.348 / 0.348 / 0.636 | 0.106 / 0.106 / 0.364 | 0.000 / 0.000 / 0.000 |
| P0_to_P1 | reduction | 0.227 / 0.227 / 0.530 | 0.682 / 0.682 / 1.000 | 0.000 / 0.000 / 0.000 |
| P1_to_P2 | oxidation | 0.076 / 0.076 / 0.333 | 0.136 / 0.136 / 0.379 | 0.000 / 0.000 / 0.000 |
| P1_to_P2 | reduction | 0.091 / 0.091 / 0.985 | 0.258 / 0.258 / 1.000 | 0.000 / 0.000 / 0.000 |
| C0_to_C1 | oxidation | 0.178 / 0.178 / 0.311 | 0.200 / 0.200 / 0.333 | 0.000 / 0.000 / 0.000 |
| C0_to_C1 | reduction | 0.444 / 0.444 / 0.978 | 0.800 / 0.822 / 1.000 | 0.000 / 0.000 / 0.000 |

## 4. 家族内 / 跨家族

| 层对 | 目标 | 家族内对 | 跨家族对 | 家族内 f_unresolved(下) | 跨家族 f_unresolved(下) |
|---|---|---|---|---|---|
| P0_to_P1 | oxidation | 4 | 62 | 1.000 | 0.613 |
| P0_to_P1 | reduction | 4 | 62 | 1.000 | 0.500 |
| P1_to_P2 | oxidation | 4 | 62 | 1.000 | 0.290 |
| P1_to_P2 | reduction | 4 | 62 | 1.000 | 0.984 |
| C0_to_C1 | oxidation | 2 | 43 | 1.000 | 0.279 |
| C0_to_C1 | reduction | 2 | 43 | 1.000 | 0.977 |

## 5. 未报告项

- `threshold_decision_error`：记为 `not_applicable`。`config/prereg.yaml` 的 `threshold_decisions.if_unavailable` 禁止用数据分位数临时替代外部设计阈值，而本 objective 集合没有登记合规的外部阈值来源。

## 6. 一致性自检

- C0→C1 oxidation 的 tau_b：本轮复算 0.688889，Week 5 记录 0.688889 → 一致
- C0→C1 reduction 的 tau_b：本轮复算 -0.466667，Week 5 记录 -0.466667 → 一致
- P1→P2 与 C0→C1 的 delta_m 复用了 P0/P1 证据（见每行的 delta_m_source 字段），因为本仓库内 P2 层与 C1 层没有第二个同层级方法可对照。

