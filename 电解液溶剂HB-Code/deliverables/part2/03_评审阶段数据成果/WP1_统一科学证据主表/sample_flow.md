# Week 28 / WP1 样本流转图（sample flow）

> 由 `scripts/build_week28_evidence_table.py` 确定性生成。

## 1. 计算对象 -> 物理层级 -> 决策的流转

```mermaid
flowchart TD
  M["data/metadata/core_set.csv (18) + broad_pool.csv (40)<br/>molecule_registry"] --> S
  S["state_registry<br/>G1 / G2 / G2a 自由分子态 + C1/C2 条件态<br/>charge x multiplicity x motif x QC x state identity"] --> P
  SRC["outputs/week3, week4, week5, week8, phase2_p1a<br/>冻结的逐 rung 表格"] --> P
  P["property_table<br/>每行一个 (object, rung, axis)<br/>value + value_status + source_file:field"] --> W
  P --> C["cost_table<br/>feature availability / jobs / wall seconds / failures"]
  W["pairwise_table<br/>d_lower, d_upper, sigma_ij, resolved masks, decision_state<br/>scope = all | primary"] --> D
  W --> R["冻结数字复核<br/>= outputs/week6 stored pairs"]
  D["decision_table<br/>Top-k overlap / Jaccard / regret / tau_b / f_unresolved"] --> OUT
  OUT["WP2 (物理层级) / WP3 (条件态) / WP4 (决策可靠性) / WP5-WP6 (信息预算)"]
```

## 2. 各 rung 的实际候选覆盖（common set 大小）

| 对比 | 轴 | scope | 候选数 n | pair 数 |
| --- | --- | --- | --- | --- |
| P0_to_P1v | oxidation | all | 18 | 153 |
| P0_to_P1v | reduction | all | 18 | 153 |
| P1v_to_P1a | oxidation | all | 12 | 66 |
| P1v_to_P1a | reduction | all | 0 | — |
| P1v_to_P2a | oxidation | all | 18 | 153 |
| P1v_to_P2a | reduction | all | 18 | 153 |
| P1v_to_P2eps10 | oxidation | all | 12 | 66 |
| P1v_to_P2eps10 | reduction | all | 12 | 66 |
| P0_to_P2a | oxidation | all | 18 | 153 |
| P0_to_P2a | reduction | all | 18 | 153 |
| C0_to_C1 | oxidation | all | 10 | 45 |
| C0_to_C1 | oxidation | primary | 6 | 15 |
| C0_to_C1 | reduction | all | 10 | 45 |
| C0_to_C1 | reduction | primary | 1 | — |
| C1_to_C2 | oxidation | all | 10 | 45 |
| C1_to_C2 | oxidation | primary | 6 | 15 |
| C1_to_C2 | reduction | all | 10 | 45 |
| C1_to_C2 | reduction | primary | 1 | — |

## 3. 被规则挡掉的样本（必须写明，不能静默丢弃）

| 规则 | 挡掉的样本 | 原因 |
| --- | --- | --- |
| `unbound_anion` | P1a 还原轴 12 个对象 | 气相阴离子不是束缚态，绝热 EA 无物理意义（冻结 failure_rule） |
| R13 state-identity 闸门 | 还原轴 9 个 C1 对象 | Li-centered/mixed 还原不是分子还原，不得进入主 ranking |
| 数据缺失 | 见 `cost_table` 的 `n_missing` / `n_not_converged` | 仓库内确实没有数值，不强行补齐 |

