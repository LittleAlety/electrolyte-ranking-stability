# Gate 1 双轨定位（R13）

> 由 `scripts/gate1_dual_track_report.py` 从已冻结的 Week-25 / Week-2 Gate-1 产物与 R13 各层产物现算，不跑新电子结构。

## 结论

| 轨道 | 名称 | 状态 |
| --- | --- | --- |
| Track A | decision-stability validity | **computationally established** |
| Track B | external / experimental validity | **NOT CLOSED**（negative result） |

Track B 未闭合**不**使 Track A 失效；它只限制「绝对尺度 / 真实排序」这类声明的强度。

## Track A：decision stability（独立成立）

阶梯：`P0 → P1v → P1a → P2a → P2eps → C1 → C2`。问题：哪些缺失物理会改变材料筛选决策？

| rung | axis | n | n_pairs | τ_b | STABLE | UNRESOLVED | ROBUST_INVERSION |
| --- | --- | --- | --- | --- | --- | --- | --- |
| P0->P1v | oxidation | 18 | 153 | 0.673 | 83 | 70 | 0 |
| P0->P1v | reduction | 18 | 153 | 0.595 | 44 | 109 | 0 |
| P1v->P2a | oxidation | 18 | 153 | 0.895 | 125 | 28 | 0 |
| P1v->P2a | reduction | 18 | 153 | 0.673 | 94 | 59 | 0 |
| P0->P2a | oxidation | 18 | 153 | 0.673 | 84 | 69 | 0 |
| P0->P2a | reduction | 18 | 153 | 0.791 | 40 | 113 | 0 |

**P1v vs P1a（绝热阶梯）**：n = 12，τ_b = 0.788，位移 population std = 0.207 eV，robust inversion = 2。
还原轴按 `unbound_anion` 规则排除（气相阴离子不束缚）。

**C1 还原态身份分层**：标签 {"Li_centered_or_mixed_redox": 11, "molecule_centered_redox": 1}；主 ranking 只用 `molecule_centered_redox`，分层后 n = 1 → 排序无定义。

## Track B：external / experimental validity（NOT CLOSED）

| 组件 | 结果 | 说明 |
| --- | --- | --- |
| 排序一致性层 | **ordering_disagrees** | τ_b = 0.429 < 0.9，n_pairs = 21（一致 15 / 不一致 6）（`outputs/week25/series_rel_ordering_check.json`） |
| 绝对标定层 | limitation | 31 行仍为 `est`，升级 0 行；按 R7 记为 limitation，不再单列 blocker（`outputs/week2/solution_anchor_audit.json`） |
| 还原轴旁证 | not_evaluable_secondary_only | 只有 3 个 pair（门槛 18）：**数据不足**，不是不一致（`outputs/week25/gate1_reduction_secondary.json`） |
| 上游可行性 | not_closable_on_current_literature | W24-D 发现本地文献里最长同装置 / 同判据同源序列只有 k = 1；审计细节见来源文档。（`outputs/week24_corealign/gate1_anchor_feasibility.md`） |

## 措辞规范

- 允许：`designated computational target`、`designated reference model`
- 禁止：`validated target`、`physically validated target`
- 解禁条件：只有 Gate 1（含排序一致性层）CLOSED 之后，才可恢复 validated 字样；见 config/scientific_definitions.yaml 的 target_naming

