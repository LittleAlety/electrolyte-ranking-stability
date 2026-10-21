# Li 配位 motif 第二轮搜索（已执行）

> 由 `scripts/wp_production/run_li_motif_round2.py` 生成。筛选层是**气相 GFN2-xTB**：
> 它只回答「换一个中性盆地当父体，这条腿还能长出几个**独立的**极小」，
> 不是生产级自由能，也不使用 GFN2 的 1.00 kcal/mol 作收敛判据。

## 每腿上限：登记值 vs 实测值

| 腿 | 父体（用/登记） | round-1 保留 | 登记上限 | 执行上限 | 实测新盆地 | 实测上限 | 塌缩到 round-1 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| EMC\|LiM_plus | 2/2 | 2 | 4 | 4 | 2 | 4 | 1 |
| EMC\|LiM_2plus | 2/2 | 1 | 3 | 3 | 1 | 2 | 1 |
| DEC\|LiM_plus | 3/3 | 2 | 5 | 5 | 2 | 4 | 1 |
| DEC\|LiM_2plus | 3/3 | 1 | 4 | 4 | 1 | 2 | 1 |
| DME\|LiM_plus | 6/6 | 1 | 7 | 7 | 0 | 1 | 1 |
| DME\|LiM_2plus | 6/6 | 1 | 7 | 7 | 2 | 3 | 1 |
| TMP\|LiM_plus | 2/2 | 2 | 4 | 4 | 3 | 5 | 0 |
| TMP\|LiM_2plus | 2/2 | 2 | 4 | 4 | 1 | 3 | 1 |

实测上限高于**登记**上限的腿：`TMP|LiM_plus`。登记上限是 `round1_kept + 已验证父体` 的**启发式**上限（假设每个补充盆地最多只贡献一个新极小），实测证明一个盆地可以承载多个独立极小（TMP 两个父体给出 3 个新盆地）。因此报告一律用**实测**列，登记值保持原样不改。

## 保留的 motif（含与 round-1 的对照）

| 腿 | 候选 | 父体 | 类别 | 相对最低 (kJ/mol) | 新增? | 重复于 | 几何 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| EMC\|LiM_plus | c01 | r2_c57 | monodentate_donor4 | 0.000 | false | round1:c02 | `work/limotif_r2/EMC_LiM_plus@r2_c57/EMC_LiM_plus@r2_c57_c01/xtbopt.xyz` |
| EMC\|LiM_plus | c05 | c14 | monodentate_donor4 | 3.462 | true | - | `work/limotif_r2/EMC_LiM_plus@c14/EMC_LiM_plus@c14_c05/xtbopt.xyz` |
| EMC\|LiM_plus | c00 | c14 | bidentate_donors2_5 | 17.942 | true | - | `work/limotif_r2/EMC_LiM_plus@c14/EMC_LiM_plus@c14_c00/xtbopt.xyz` |
| EMC\|LiM_2plus | c08 | c14 | monodentate_donor4 | 0.000 | false | round1:c00 | `work/limotif_r2/EMC_LiM_2plus@c14/EMC_LiM_2plus@c14_c08/xtbopt.xyz` |
| EMC\|LiM_2plus | c07 | r2_c57 | monodentate_donor4 | 18.335 | true | - | `work/limotif_r2/EMC_LiM_2plus@r2_c57/EMC_LiM_2plus@r2_c57_c07/xtbopt.xyz` |
| DEC\|LiM_plus | c03 | r2_c13 | monodentate_donor4 | 0.000 | true | - | `work/limotif_r2/DEC_LiM_plus@r2_c13/DEC_LiM_plus@r2_c13_c03/xtbopt.xyz` |
| DEC\|LiM_plus | c07 | c03 | monodentate_donor4 | 2.955 | false | round1:c00 | `work/limotif_r2/DEC_LiM_plus@c03/DEC_LiM_plus@c03_c07/xtbopt.xyz` |
| DEC\|LiM_plus | c03 | r2_c23 | monodentate_donor4 | 6.360 | true | - | `work/limotif_r2/DEC_LiM_plus@r2_c23/DEC_LiM_plus@r2_c23_c03/xtbopt.xyz` |
| DEC\|LiM_2plus | c06 | r2_c23 | monodentate_donor4 | 0.000 | false | round1:c02 | `work/limotif_r2/DEC_LiM_2plus@r2_c23/DEC_LiM_2plus@r2_c23_c06/xtbopt.xyz` |
| DEC\|LiM_2plus | c03 | c03 | monodentate_donor4 | 15.727 | true | - | `work/limotif_r2/DEC_LiM_2plus@c03/DEC_LiM_2plus@c03_c03/xtbopt.xyz` |
| DME\|LiM_plus | c05 | r2_c25 | bidentate_donors1_4 | 0.000 | false | round1:c00 | `work/limotif_r2/DME_LiM_plus@r2_c25/DME_LiM_plus@r2_c25_c05/xtbopt.xyz` |
| DME\|LiM_2plus | c02 | c05 | bidentate_donors1_4 | 0.000 | false | round1:c01 | `work/limotif_r2/DME_LiM_2plus@c05/DME_LiM_2plus@c05_c02/xtbopt.xyz` |
| DME\|LiM_2plus | c03 | c05 | monodentate_donor1 | 18.469 | true | - | `work/limotif_r2/DME_LiM_2plus@c05/DME_LiM_2plus@c05_c03/xtbopt.xyz` |
| DME\|LiM_2plus | c05 | c05 | monodentate_donor4 | 18.469 | true | - | `work/limotif_r2/DME_LiM_2plus@c05/DME_LiM_2plus@c05_c05/xtbopt.xyz` |
| TMP\|LiM_plus | c05 | r2_c48 | bidentate_donors3_4 | 0.000 | true | - | `work/limotif_r2/TMP_LiM_plus@r2_c48/TMP_LiM_plus@r2_c48_c05/xtbopt.xyz` |
| TMP\|LiM_plus | c08 | r2_c27 | bidentate_donors3_6 | 0.012 | true | - | `work/limotif_r2/TMP_LiM_plus@r2_c27/TMP_LiM_plus@r2_c27_c08/xtbopt.xyz` |
| TMP\|LiM_plus | c07 | r2_c27 | bidentate_donors3_6 | 0.025 | true | - | `work/limotif_r2/TMP_LiM_plus@r2_c27/TMP_LiM_plus@r2_c27_c07/xtbopt.xyz` |
| TMP\|LiM_2plus | c00 | r2_c48 | monodentate_donor3 | 0.000 | true | - | `work/limotif_r2/TMP_LiM_2plus@r2_c48/TMP_LiM_2plus@r2_c48_c00/xtbopt.xyz` |
| TMP\|LiM_2plus | c10 | r2_c27 | monodentate_donor3 | 0.005 | false | round1:c08 | `work/limotif_r2/TMP_LiM_2plus@r2_c27/TMP_LiM_2plus@r2_c27_c10/xtbopt.xyz` |

## 被拒的父体（fail closed）

无：所有登记父体的磁盘哈希都与登记值一致。

## 验收

| check | ok | detail |
| --- | --- | --- |
| every_selected_round2_leg_was_executed | True | 8/8 legs executed (mode=full; the plan registers 8 legs) |
| kept_motifs_of_each_leg_are_pairwise_independent | True | same-class pairs keep RMSD >= 0.35 A (frozen keep rule) |
| each_leg_keeps_at_most_three_independent_motifs | True | max_keep=3 (frozen round-1 keep rule) |
| no_candidate_is_dropped_silently | True | 214 candidates carry a status or a reason |
| every_kept_motif_is_tagged_new_or_duplicate | True | round-1 collisions stay visible instead of inflating the count |
| every_candidate_carries_parent_identity | True | 214 candidates |
| screen_is_not_a_free_energy | True | xTB GFN2 (gas phase) coordination-motif screen -- ranks starting structures only |
| registered_upper_bound_is_never_reported_as_a_pool_size | True | measured value is reported; 1 leg(s) exceed the registered upper bound (TMP/LiM_plus): a single basin can host several independent minima, so 'round1_kept + parents' was a heuristic bound, not a mathematical one |
| legs_without_a_verifiable_parent_are_registered_not_invented | True | every leg had at least one hash-verified parent |

合计 9 项，失败 0 项。
