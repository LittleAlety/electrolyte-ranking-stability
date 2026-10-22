# 3→6 采样差异报告（EMC / DEC / DME / TMP × 四主态）

> 生成器：`scripts/wp_production/build_sampling_3to6_diff.py`（`--check` 完全只读）
> 按用户 2026-10-19 决定：**本轮只报告差异，不判“采样收敛”**。
> `sampling_limited` 只表示当前搜索池/扩样覆盖受限，不是数值收敛结论。
> GFN2 的 1.00 kcal/mol 是**筛选**阈值，不用于生产级验收。

## 本轮能给出什么、不能给出什么

| 项 | 状态 | 说明 |
| --- | --- | --- |
| round-1 `G_ensemble` | 16/16 态已填 | 直接取自生产系综标签，可复算 |
| 氧化轴 / Li 条件轴（round-1 侧） | 已填 | `G(M_plus)-G(M)`、`G(LiM_2plus)-G(LiM_plus)`，单位 eV |
| ceiling 侧（扩到池内上限） | 8/16 态 not_computed | 定义为**round-1 极小 + 已登记且 QC 通过的第二轮成员**（同一 DFT 级去重规则），缺口就留空：**空格是诚实状态，不是 0** |
| Top-k 重叠 / selection regret | not_computed | 依赖 ceiling 侧排序，只登记 round-1 基线集合 |
| 采样收敛判定 | **不做** | 独立生产级容差尚未冻结，不得据本轮结果倒推 |

## 池覆盖（来自 3→6 审计，非本轮数值）

| 判定 | 状态数 |
| --- | --- |
| executable / executable_partial | 10 |
| sampling_limited | 6 |
| Li 态池取第二轮**实测**值 | 8 |
| Li 态维持 round-1 池（父体哈希核验失败，不补数） | 0 |

## 逐态：round-1 自由能与 ceiling 侧

| 分子 | 态 | 池类型 | round1 | 池内上限 | 审计判定 | accepted | n_unique | G_ens(round-1) kcal/mol | G_ens(ceiling) | Δ |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| EMC | M | free_conformer | 2 | 2 | sampling_limited | accepted | 2 | -240413.138161 | — | — |
| EMC | M_plus | free_conformer | 2 | 2 | sampling_limited | accepted | 2 | -240226.173237 | — | — |
| EMC | LiM_plus | li_motif_round2_measured | 2 | 4 | executable_partial | accepted | 3 | -245090.677606 | — | — |
| EMC | LiM_2plus | li_motif_round2_measured | 1 | 2 | executable_partial | accepted | 1 | -244894.595300 | — | — |
| DEC | M | free_conformer | 3 | 3 | sampling_limited | accepted | 3 | -265093.802909 | — | — |
| DEC | M_plus | free_conformer | 3 | 4 | executable_partial | accepted | 3 | -264925.087287 | — | — |
| DEC | LiM_plus | li_motif_round2_measured | 2 | 4 | executable_partial | accepted | 2 | -269770.880754 | — | — |
| DEC | LiM_2plus | li_motif_round2_measured | 1 | 2 | executable_partial | accepted | 1 | -269576.059314 | — | — |
| DME | M | free_conformer | 3 | 6 | executable | accepted | 3 | -193896.607798 | — | — |
| DME | M_plus | free_conformer | 3 | 4 | executable_partial | accepted | 3 | -193744.466828 | — | — |
| DME | LiM_plus | li_motif_round2_measured | 1 | 1 | sampling_limited | accepted | 1 | -198585.253686 | — | — |
| DME | LiM_2plus | li_motif_round2_measured | 1 | 3 | executable_partial | accepted | 2 | -198409.511357 | — | — |
| TMP | M | free_conformer | 2 | 2 | sampling_limited | accepted | 2 | -478370.212791 | — | — |
| TMP | M_plus | free_conformer | 3 | 3 | sampling_limited | accepted | 2 | -478186.998219 | — | — |
| TMP | LiM_plus | li_motif_round2_measured | 2 | 5 | executable_partial | limited | 1 | -483045.245173 | — | — |
| TMP | LiM_2plus | li_motif_round2_measured | 2 | 3 | executable_partial | accepted | 3 | -482856.455592 | — | — |

## 氧化轴与 Li 条件轴（round-1 侧，eV）

| 分子 | 轴 | round-1 | ceiling | Δ | 状态 |
| --- | --- | --- | --- | --- | --- |
| EMC | oxidation (M_plus - M) | 8.107566437 | — | — | round1_only |
| EMC | Li-conditioned (LiM_2plus - LiM_plus) | 8.502933565 | — | — | round1_only |
| DEC | oxidation (M_plus - M) | 7.316201841 | — | — | complete |
| DEC | Li-conditioned (LiM_2plus - LiM_plus) | 8.448257218 | — | — | round1_only |
| DME | oxidation (M_plus - M) | 6.597456875 | — | — | complete |
| DME | Li-conditioned (LiM_2plus - LiM_plus) | 7.620908682 | — | — | round1_only |
| TMP | oxidation (M_plus - M) | 7.944935827 | — | — | round1_only |
| TMP | Li-conditioned (LiM_2plus - LiM_plus) | 8.186691056 | — | — | round1_only |

## Top-k 与 selection regret（预注册口径，本轮只登记基线）

审计集只有 4 个分子，故主 k=2，辅助 k=1 与 k=3（原方案 k=3/2/4 按集合规模缩放）。

| 量 | k | round-1 Top-k 集合 | ceiling 集合 | 值 | 状态 |
| --- | --- | --- | --- | --- | --- |
| top_k_overlap | 2 | EMC+TMP | — | — | round1_only |
| selection_regret_ev | 2 | EMC+TMP | — | — | round1_only |
| top_k_overlap | 1 | EMC | — | — | round1_only |
| selection_regret_ev | 1 | EMC | — | — | round1_only |
| top_k_overlap | 3 | EMC+TMP+DEC | — | — | round1_only |
| selection_regret_ev | 3 | EMC+TMP+DEC | — | — | round1_only |

## 判读规则（先冻结，后看结果）

1. **不得据本轮结果倒推阈值**：生产级独立容差须在扩样结果出现**之前**冻结，且不能由“希望哪个分子翻转”反推。
2. **空值不补零**：ceiling 侧未计算就留空并写原因；把缺证据写成 0 或写成“无变化”都是造假。
3. **池不足不凑数**：`sampling_limited` 的状态只登记真实上限，绝不复制构象凑到 6。
4. **Li 态第二轮 motif 搜索已执行**（`run_li_motif_round2.py`，独立中性盆地做父几何）：8 个态的池数取实测值（round-1 保留 + 真新盆地，同类重原子 RMSD 去重），0 个态因登记父体磁盘哈希与登记值不符而维持 round-1 池（不换父、不补数），仍有 0 个态标记待搜索。**池可用（筛选层）不等于已登记生产成员**：新盆地要进 ceiling 侧必须另跑生产级 ORCA 腿，故本轮 ceiling 仍一律 `not_computed`。
5. 扩样结果落地后，本表由生成器自动填 ceiling 侧与 Δ；届时仍需人工确认容差已冻结再下结论。
