# 方案 6.1 第 3 步：主集 Li 配位 motif 筛选（已执行）

> 由 scripts/wp_production/screen_li_motifs.py 生成。筛选层是**气相 GFN2-xTB**，它只回答
> 「每条腿保留哪几个独立 motif」，不是生产级自由能，也不是 wB97X-D4 + SMD。
> 规则在任何结果存在之前就已登记（selection_rule.md / motif_plan.csv）；本层不修改规则。

| 记录 | 分子 | 态 | 起点数 | 成功 | 保留 motif | 判定 | 最低 motif |
| --- | --- | --- | --- | --- | --- | --- | --- |
| C01|LiM_plus | DMC | LiM_plus | 10 | 10 | 2 | production_motif_is_lowest | monodentate_donor3 |
| C01|LiM_2plus | DMC | LiM_2plus | 10 | 10 | 1 | production_motif_within_1kj | monodentate_donor3 |
| C02|LiM_plus | EMC | LiM_plus | 10 | 10 | 2 | production_motif_within_1kj | monodentate_donor4 |
| C02|LiM_2plus | EMC | LiM_2plus | 10 | 10 | 1 | production_motif_is_lowest | monodentate_donor4 |
| C03|LiM_plus | DEC | LiM_plus | 10 | 10 | 2 | production_motif_is_lowest | monodentate_donor4 |
| C03|LiM_2plus | DEC | LiM_2plus | 10 | 10 | 1 | production_motif_within_1kj | monodentate_donor4 |
| C04|LiM_plus | EC | LiM_plus | 10 | 10 | 1 | production_motif_within_1kj | monodentate_donor4 |
| C04|LiM_2plus | EC | LiM_2plus | 10 | 9 | 1 | production_motif_within_1kj | monodentate_donor4 |
| C05|LiM_plus | PC | LiM_plus | 10 | 10 | 1 | production_motif_within_1kj | monodentate_donor5 |
| C05|LiM_2plus | PC | LiM_2plus | 10 | 10 | 1 | production_motif_within_1kj | monodentate_donor5 |
| C08|LiM_plus | DME | LiM_plus | 7 | 7 | 1 | production_motif_is_lowest | bidentate_donors1_4 |
| C08|LiM_2plus | DME | LiM_2plus | 7 | 7 | 1 | production_motif_within_1kj | bidentate_donors1_4 |
| C09|LiM_plus | DOL | LiM_plus | 7 | 7 | 1 | production_motif_within_1kj | bidentate_donors2_4 |
| C09|LiM_2plus | DOL | LiM_2plus | 7 | 6 | 2 | production_motif_within_1kj | monodentate_donor4 |
| C13|LiM_plus | GBL | LiM_plus | 4 | 4 | 1 | production_motif_within_1kj | monodentate_donor0 |
| C13|LiM_2plus | GBL | LiM_2plus | 7 | 7 | 1 | production_motif_within_1kj | monodentate_donor0 |
| C14|LiM_plus | SL | LiM_plus | 7 | 7 | 1 | production_motif_within_1kj | bidentate_donors0_2 |
| C14|LiM_2plus | SL | LiM_2plus | 7 | 7 | 3 | production_motif_is_lowest | monodentate_donor0 |
| C15|LiM_plus | DMSO | LiM_plus | 5 | 5 | 1 | production_motif_within_1kj | monodentate_donor3 |
| C15|LiM_2plus | DMSO | LiM_2plus | 5 | 5 | 1 | production_motif_within_1kj | monodentate_donor3 |
| C16|LiM_plus | AN | LiM_plus | 5 | 5 | 1 | production_motif_within_1kj | monodentate_donor2 |
| C16|LiM_2plus | AN | LiM_2plus | 2 | 2 | 0 | unresolved | - |
| C17|LiM_plus | TMP | LiM_plus | 14 | 14 | 2 | production_motif_is_lowest | monodentate_donor3 |
| C17|LiM_2plus | TMP | LiM_2plus | 14 | 14 | 2 | production_motif_within_1kj | monodentate_donor3 |

## 保留的独立 motif（可执行结构集合）

| 记录 | 序 | 相对最低 (kJ/mol) | motif 类别 | 给体接触 | Li-给体最近 (A) | 几何（仓库相对路径） |
| --- | --- | --- | --- | --- | --- | --- |
| C01|LiM_plus | 1 | 0.000 | monodentate_donor3 | 3 | 1.6559 | `work/limotif/C01_LiM_plus/C01_LiM_plus_c00/xtbopt.xyz` |
| C01|LiM_plus | 2 | 24.622 | bidentate_donors1_4 | 1,4 | 1.8702 | `work/limotif/C01_LiM_plus/C01_LiM_plus_c05/xtbopt.xyz` |
| C01|LiM_2plus | 1 | 0.000 | monodentate_donor3 | 3 | 1.8029 | `work/limotif/C01_LiM_2plus/C01_LiM_2plus_c06/xtbopt.xyz` |
| C02|LiM_plus | 1 | 0.000 | monodentate_donor4 | 4 | 1.6577 | `work/limotif/C02_LiM_plus/C02_LiM_plus_c02/xtbopt.xyz` |
| C02|LiM_plus | 2 | 19.885 | bidentate_donors2_5 | 2,5 | 1.8509 | `work/limotif/C02_LiM_plus/C02_LiM_plus_c08/xtbopt.xyz` |
| C02|LiM_2plus | 1 | 0.000 | monodentate_donor4 | 4 | 1.7636 | `work/limotif/C02_LiM_2plus/C02_LiM_2plus_c00/xtbopt.xyz` |
| C03|LiM_plus | 1 | 0.000 | monodentate_donor4 | 4 | 1.6534 | `work/limotif/C03_LiM_plus/C03_LiM_plus_c00/xtbopt.xyz` |
| C03|LiM_plus | 2 | 10.923 | bidentate_donors2_5 | 2,5 | 1.8475 | `work/limotif/C03_LiM_plus/C03_LiM_plus_c09/xtbopt.xyz` |
| C03|LiM_2plus | 1 | 0.000 | monodentate_donor4 | 4 | 1.7369 | `work/limotif/C03_LiM_2plus/C03_LiM_2plus_c02/xtbopt.xyz` |
| C04|LiM_plus | 1 | 0.000 | monodentate_donor4 | 4 | 1.6593 | `work/limotif/C04_LiM_plus/C04_LiM_plus_c06/xtbopt.xyz` |
| C04|LiM_2plus | 1 | 0.000 | monodentate_donor4 | 4 | 1.8486 | `work/limotif/C04_LiM_2plus/C04_LiM_2plus_c03/xtbopt.xyz` |
| C05|LiM_plus | 1 | 0.000 | monodentate_donor5 | 5 | 1.6541 | `work/limotif/C05_LiM_plus/C05_LiM_plus_c01/xtbopt.xyz` |
| C05|LiM_2plus | 1 | 0.000 | monodentate_donor5 | 5 | 1.7993 | `work/limotif/C05_LiM_2plus/C05_LiM_2plus_c05/xtbopt.xyz` |
| C08|LiM_plus | 1 | 0.000 | bidentate_donors1_4 | 1,4 | 1.7978 | `work/limotif/C08_LiM_plus/C08_LiM_plus_c00/xtbopt.xyz` |
| C08|LiM_2plus | 1 | 0.000 | bidentate_donors1_4 | 1,4 | 1.9288 | `work/limotif/C08_LiM_2plus/C08_LiM_2plus_c01/xtbopt.xyz` |
| C09|LiM_plus | 1 | 0.000 | bidentate_donors2_4 | 2,4 | 1.9738 | `work/limotif/C09_LiM_plus/C09_LiM_plus_c02/xtbopt.xyz` |
| C09|LiM_2plus | 1 | 0.000 | monodentate_donor4 | 4 | 2.0830 | `work/limotif/C09_LiM_2plus/C09_LiM_2plus_c05/xtbopt.xyz` |
| C09|LiM_2plus | 2 | 0.011 | monodentate_donor2 | 2 | 2.0825 | `work/limotif/C09_LiM_2plus/C09_LiM_2plus_c01/xtbopt.xyz` |
| C13|LiM_plus | 1 | 0.000 | monodentate_donor0 | 0 | 1.6667 | `work/limotif/C13_LiM_plus/C13_LiM_plus_c03/xtbopt.xyz` |
| C13|LiM_2plus | 1 | 0.000 | monodentate_donor0 | 0 | 1.8142 | `work/limotif/C13_LiM_2plus/C13_LiM_2plus_c04/xtbopt.xyz` |
| C14|LiM_plus | 1 | 0.000 | bidentate_donors0_2 | 0,2 | 1.8872 | `work/limotif/C14_LiM_plus/C14_LiM_plus_c02/xtbopt.xyz` |
| C14|LiM_2plus | 1 | 0.000 | monodentate_donor0 | 0 | 1.7213 | `work/limotif/C14_LiM_2plus/C14_LiM_2plus_c00/xtbopt.xyz` |
| C14|LiM_2plus | 2 | 0.004 | monodentate_donor2 | 2 | 1.7210 | `work/limotif/C14_LiM_2plus/C14_LiM_2plus_c02/xtbopt.xyz` |
| C14|LiM_2plus | 3 | 9.091 | bidentate_donors0_2 | 0,2 | 2.0478 | `work/limotif/C14_LiM_2plus/C14_LiM_2plus_c03/xtbopt.xyz` |
| C15|LiM_plus | 1 | 0.000 | monodentate_donor3 | 3 | 1.6294 | `work/limotif/C15_LiM_plus/C15_LiM_plus_c01/xtbopt.xyz` |
| C15|LiM_2plus | 1 | 0.000 | monodentate_donor3 | 3 | 1.8015 | `work/limotif/C15_LiM_2plus/C15_LiM_2plus_c01/xtbopt.xyz` |
| C16|LiM_plus | 1 | 0.000 | monodentate_donor2 | 2 | 1.8605 | `work/limotif/C16_LiM_plus/C16_LiM_plus_c01/xtbopt.xyz` |
| C17|LiM_plus | 1 | 0.000 | monodentate_donor3 | 3 | 1.6043 | `work/limotif/C17_LiM_plus/C17_LiM_plus_c00/xtbopt.xyz` |
| C17|LiM_plus | 2 | 14.736 | bidentate_donors1_4_6 | 1,4,6 | 2.0141 | `work/limotif/C17_LiM_plus/C17_LiM_plus_c04/xtbopt.xyz` |
| C17|LiM_2plus | 1 | 0.000 | monodentate_donor3 | 3 | 1.6842 | `work/limotif/C17_LiM_2plus/C17_LiM_2plus_c13/xtbopt.xyz` |
| C17|LiM_2plus | 2 | 0.018 | monodentate_donor3 | 3 | 1.6833 | `work/limotif/C17_LiM_2plus/C17_LiM_2plus_c08/xtbopt.xyz` |

## 与登记规则的偏差（逐条显式记录）

* 父几何用**该腿自己的生产几何去掉 Li**，不是共享的 week-3 中性几何：方案 6.1 要求每态从自己的连通性出发。
* 该腿自己的收敛几何在磁盘上有两种命名（`<NAME>_<STATE>.xyz` 与 `<NAME>_<STATE>_opt.xyz`，后者来自 HPC 导入）；
  两者是**同一个对象**，逐候选登记 `parent_naming`（exact / opt）以便追溯。
* 电荷/多重度取自该腿（LiM_plus = 1/1，LiM_2plus = 2/2），2+ 腿绝不按 1+ 复合物弛豫。
* 筛选仍是气相 GFN2-xTB，**不能**当作生产自由能，也不能替代 wB97X-D4 + SMD(acetonitrile)。

## 验收

| check | ok | detail |
| --- | --- | --- |
| every_registered_leg_was_screened | True | 24 legs carry candidates |
| each_leg_keeps_at_most_three_independent_motifs | True | max_keep=3 |
| charge_and_multiplicity_come_from_the_leg | True | no leg is relaxed with another leg's charge |
| every_candidate_carries_its_parent_hash | True | 198 candidates |
| no_candidate_is_dropped_silently | True | failed candidates keep a reason |
| every_candidate_records_which_parent_naming_it_used | True | parent_naming is registered per candidate (exact vs opt): exact=75, opt=123 |

合计 6 项，失败 0 项。
