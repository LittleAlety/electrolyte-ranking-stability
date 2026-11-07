# 3→6 采样审计：ceiling 缺口四分类（证据层，非收敛判定）

> 生成器 `build_sampling_ceiling_classification.py`（`--check` 完全只读）。
> **容差未冻结**：本表只描述差异与缺口类型，不给出任何采样收敛结论。

## 分布

| 类别 | 态数 |
|---|---|
| `complete` | 10 |
| `registered_candidates_qc_pending` | 2 |
| `pool_has_no_independent_structure` | 4 |

## 逐态

| 态 | ceiling | 类别 | 已登记 round-2 | QC 通过 | 池内极小 | 恢复批次起点 | 备注 |
|---|---|---|---|---|---|---|---|
| EMC\|M | not_computed | `pool_has_no_independent_structure` | 0 | 0 | — | — | — |
| EMC\|M_plus | not_computed | `pool_has_no_independent_structure` | 0 | 0 | — | — | — |
| EMC\|LiM_plus | complete | `complete` | 0 | 0 | — | — | — |
| EMC\|LiM_2plus | not_computed | `registered_candidates_qc_pending` | 0 | 0 | — | — | — |
| DEC\|M | complete | `complete` | 0 | 0 | — | r2_c23 | — |
| DEC\|M_plus | complete | `complete` | 0 | 0 | — | — | — |
| DEC\|LiM_plus | complete | `complete` | 0 | 0 | — | — | — |
| DEC\|LiM_2plus | not_computed | `registered_candidates_qc_pending` | 0 | 0 | — | — | — |
| DME\|M | complete | `complete` | 0 | 0 | — | — | — |
| DME\|M_plus | complete | `complete` | 0 | 0 | — | c07 | — |
| DME\|LiM_plus | not_computed | `pool_has_no_independent_structure` | 0 | 0 | — | — | — |
| DME\|LiM_2plus | complete | `complete` | 0 | 0 | — | r3m_c05 | — |
| TMP\|M | not_computed | `pool_has_no_independent_structure` | 0 | 0 | — | — | — |
| TMP\|M_plus | complete | `complete` | 0 | 0 | — | c10;r3_c42 | — |
| TMP\|LiM_plus | complete | `complete` | 0 | 0 | — | r3m_c05;r3m_c08 | — |
| TMP\|LiM_2plus | complete | `complete` | 0 | 0 | — | r3m_c00 | — |

## 四类的含义（不可互换）

1. `registered_candidates_qc_pending`——候选已登记、生产 QC 未全过：**等真实计算**。
2. `pool_has_no_independent_structure`——冻结池没有更多独立极小：**当前池的结构限制**。
3. `collapsed_onto_existing_minimum`——优化后塌缩到已有极小：**去重结果**，不是缺口。
4. `coverage_genuinely_missing`——既无登记候选又无池结构：**覆盖真的缺失**。

`strict_recovery_v1` 已登记的起点在「恢复批次起点」列可见——那是**登记事实**，
不代表 ceiling 已改变；ceiling 只在成员 QC 通过并聚合后才更新。
