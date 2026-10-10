# 方案 6.1 第 3 步：四分子 Li 配位 motif 筛选（已执行）

> 由 scripts/wp_production/screen_li_motifs.py 生成。筛选层是**气相 GFN2-xTB**，它只回答
> 「每条腿保留哪几个独立 motif」，不是生产级自由能，也不是 wB97X-D4 + SMD。
> 规则在任何结果存在之前就已登记（selection_rule.md / motif_plan.csv）；本层不修改规则。

| 记录 | 分子 | 态 | 起点数 | 成功 | 保留 motif | 判定 | 最低 motif |
| --- | --- | --- | --- | --- | --- | --- | --- |
| C01|LiM_plus | DMC | LiM_plus | 10 | 10 | 2 | production_motif_is_lowest | monodentate_donor3 |
| C01|LiM_2plus | DMC | LiM_2plus | 10 | 10 | 1 | production_motif_within_1kj | monodentate_donor3 |
| C02|LiM_plus | EMC | LiM_plus | 10 | 10 | 2 | production_motif_is_lowest | monodentate_donor4 |
| C02|LiM_2plus | EMC | LiM_2plus | 10 | 10 | 2 | production_motif_within_1kj | monodentate_donor4 |
| C13|LiM_plus | GBL | LiM_plus | 4 | 4 | 1 | production_motif_within_1kj | monodentate_donor0 |
| C13|LiM_2plus | GBL | LiM_2plus | 7 | 7 | 1 | production_motif_within_1kj | monodentate_donor0 |
| C14|LiM_plus | SL | LiM_plus | 7 | 7 | 1 | production_motif_within_1kj | bidentate_donors0_2 |
| C14|LiM_2plus | SL | LiM_2plus | 7 | 7 | 3 | production_motif_within_1kj | monodentate_donor0 |

## 保留的独立 motif（可执行结构集合）

| 记录 | 序 | 相对最低 (kJ/mol) | motif 类别 | 给体接触 | Li-给体最近 (A) | 几何（仓库相对路径） |
| --- | --- | --- | --- | --- | --- | --- |
| C01|LiM_plus | 1 | 0.000 | monodentate_donor3 | 3 | 1.6559 | `work/limotif/C01_LiM_plus/C01_LiM_plus_c00/xtbopt.xyz` |
| C01|LiM_plus | 2 | 24.622 | bidentate_donors1_4 | 1,4 | 1.8702 | `work/limotif/C01_LiM_plus/C01_LiM_plus_c05/xtbopt.xyz` |
| C01|LiM_2plus | 1 | 0.000 | monodentate_donor3 | 3 | 1.8029 | `work/limotif/C01_LiM_2plus/C01_LiM_2plus_c06/xtbopt.xyz` |
| C02|LiM_plus | 1 | 0.000 | monodentate_donor4 | 4 | 1.6581 | `work/limotif/C02_LiM_plus/C02_LiM_plus_c00/xtbopt.xyz` |
| C02|LiM_plus | 2 | 19.927 | bidentate_donors2_5 | 2,5 | 1.8498 | `work/limotif/C02_LiM_plus/C02_LiM_plus_c05/xtbopt.xyz` |
| C02|LiM_2plus | 1 | 0.000 | monodentate_donor4 | 4 | 1.7630 | `work/limotif/C02_LiM_2plus/C02_LiM_2plus_c02/xtbopt.xyz` |
| C02|LiM_2plus | 2 | 18.307 | monodentate_donor4 | 4 | 1.7798 | `work/limotif/C02_LiM_2plus/C02_LiM_2plus_c06/xtbopt.xyz` |
| C13|LiM_plus | 1 | 0.000 | monodentate_donor0 | 0 | 1.6667 | `work/limotif/C13_LiM_plus/C13_LiM_plus_c03/xtbopt.xyz` |
| C13|LiM_2plus | 1 | 0.000 | monodentate_donor0 | 0 | 1.8143 | `work/limotif/C13_LiM_2plus/C13_LiM_2plus_c04/xtbopt.xyz` |
| C14|LiM_plus | 1 | 0.000 | bidentate_donors0_2 | 0,2 | 1.8872 | `work/limotif/C14_LiM_plus/C14_LiM_plus_c02/xtbopt.xyz` |
| C14|LiM_2plus | 1 | 0.000 | monodentate_donor0 | 0 | 1.7209 | `work/limotif/C14_LiM_2plus/C14_LiM_2plus_c06/xtbopt.xyz` |
| C14|LiM_2plus | 2 | 0.003 | monodentate_donor2 | 2 | 1.7208 | `work/limotif/C14_LiM_2plus/C14_LiM_2plus_c05/xtbopt.xyz` |
| C14|LiM_2plus | 3 | 9.095 | bidentate_donors0_2 | 0,2 | 2.0494 | `work/limotif/C14_LiM_2plus/C14_LiM_2plus_c03/xtbopt.xyz` |

## 与登记规则的偏差（逐条显式记录）

* 父几何用**该腿自己的生产几何去掉 Li**，不是共享的 week-3 中性几何：方案 6.1 要求每态从自己的连通性出发。
* 电荷/多重度取自该腿（LiM_plus = 1/1，LiM_2plus = 2/2），2+ 腿绝不按 1+ 复合物弛豫。
* 筛选仍是气相 GFN2-xTB，**不能**当作生产自由能，也不能替代 wB97X-D4 + SMD(acetonitrile)。

## 验收

| check | ok | detail |
| --- | --- | --- |
| every_registered_leg_was_screened | True | 8 legs carry candidates |
| each_leg_keeps_at_most_three_independent_motifs | True | max_keep=3 |
| charge_and_multiplicity_come_from_the_leg | True | no leg is relaxed with another leg's charge |
| every_candidate_carries_its_parent_hash | True | 65 candidates |
| no_candidate_is_dropped_silently | True | failed candidates keep a reason |

合计 5 项，失败 0 项。
