# 3→6 采样审计计划（EMC / DEC / DME / TMP × 四主态）

> 生成器：`scripts/wp_production/build_sampling_audit_3to6.py`
> 冻结窗口 6 kcal/mol；round-1 上限 3；round-2 上限 6。**绝不用重复构象凑数。**

## 结论

| 状态 | 状态数 | 含义 |
| --- | --- | --- |
| executable | 1 | 池内 ≥6 个独立极小，可完整执行 3→6 |
| executable_partial | 9 | 池内不足 6，按真实上限执行 |
| sampling_limited | 6 | 池内仅 1–3 个独立极小，无法诚实扩样 |

## 逐态明细

| 分子 | 态 | 池类型 | round1 | 池内独立极小 | round2 上限 | 可扩样 | 需第二轮 motif 搜索 | 判定 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| EMC | M | free_conformer | 2 | 2 | 2 | false | false | sampling_limited |
| EMC | M_plus | free_conformer | 2 | 2 | 2 | false | false | sampling_limited |
| EMC | LiM_plus | li_motif_round2_measured | 2 | 4 | 4 | true | false | executable_partial |
| EMC | LiM_2plus | li_motif_round2_measured | 1 | 2 | 2 | true | false | executable_partial |
| DEC | M | free_conformer | 3 | 3 | 3 | false | false | sampling_limited |
| DEC | M_plus | free_conformer | 3 | 4 | 4 | true | false | executable_partial |
| DEC | LiM_plus | li_motif_round2_measured | 2 | 4 | 4 | true | false | executable_partial |
| DEC | LiM_2plus | li_motif_round2_measured | 1 | 2 | 2 | true | false | executable_partial |
| DME | M | free_conformer | 3 | 6 | 6 | true | false | executable |
| DME | M_plus | free_conformer | 3 | 4 | 4 | true | false | executable_partial |
| DME | LiM_plus | li_motif_round2_measured | 1 | 1 | 1 | false | false | sampling_limited |
| DME | LiM_2plus | li_motif_round2_measured | 1 | 3 | 3 | true | false | executable_partial |
| TMP | M | free_conformer | 2 | 2 | 2 | false | false | sampling_limited |
| TMP | M_plus | free_conformer | 3 | 3 | 3 | false | false | sampling_limited |
| TMP | LiM_plus | li_motif_round2_measured | 2 | 5 | 5 | true | false | executable_partial |
| TMP | LiM_2plus | li_motif_round2_measured | 2 | 3 | 3 | true | false | executable_partial |

## 判读规则（预注册，不事后调整）

1. **不复制构象凑足 6**：池内独立极小不足时，记录真实数量与搜索证据，状态记 `sampling_limited`。
2. **Li 态**：第二轮 motif 搜索（`run_li_motif_round2.py`，独立的中性盆地做父几何）**已执行**，本表的 Li 池数取**实测**值（round-1 保留 + 真新盆地，同类重原子 RMSD 去重）；父体哈希核验不过的腿保持 round-1 池数并注明原因，绝不补数。
3. **比较口径**：3 结构 vs 上限结构的 `G_ensemble`、氧化轴、Li 条件轴与 Top-k 集合变化；本轮按 2026-10-19 用户决定只报告这些差异，不判采样收敛；生产级独立容差尚未冻结。 `sampling_limited` 只表示当前搜索池/扩样覆盖受限，不是数值收敛结论。
4. 本表只登记**计划与可行性**；实际扩样结果另表登记，不得把本表当结果。
