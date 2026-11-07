# 方案 6.1 第 1 轮构象采样（气相 GFN2 筛选）

> 由 `scripts/wp_production/build_wp2_sampling.py` 生成。采样层是**气相 GFN2-xTB 筛选**，
> 不是生产级 `wB97X-D4 + SMD(acetonitrile)`；它只回答「单一代表结构是否落在同一极小附近」。
>
> **集合偏差**：本层**声明覆盖**方案 3.1 主集 12 分子（DMC / EMC / DEC / EC / PC / DME / DOL / GBL / SL / DMSO / AN / TMP）的自由态 / 阳离子态，
> 但方案 3.3 指定的**采样审计集仍是 EMC/DEC/DME/TMP 四个**，两者不是一回事。
> 偏差登记在 `sampling_index.json` 的 `cohort_deviation`，**不宣称完成方案 3.3**；
> 本轮真正跑出结果的分子是 DMC / EMC / DEC / EC / PC / DME / DOL / GBL / SL / DMSO / AN / TMP。
>
> **DEC 缺冻结起点**：`outputs/week4/t2_opt_freq/DEC/DEC_G2.xyz` 不在仓库里（`data/metadata/core_set_metadata_ext.csv` 已把该分子登记为 `not_available_in_repo`），
> 所以 DEC 的「生产几何相对最低 / 冻结起点相对最低」两列留空，不写 0、不拿别的级别的几何顶替。

| 分子 | 态 | 撒点数 | 独立极小 | 次低极小 | 生产几何相对最低 | 冻结起点相对最低 | 判定 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| DMC | M | 16 | 1 | - | 0.330 | 0.615 | single_conformer_representative |
| DMC | M_plus | 16 | 1 | - | 5.333 | 4.098 | sampling_sensitive |
| EMC | M | 16 | 2 | 0.675 | 0.453 | 0.729 | single_conformer_representative |
| EMC | M_plus | 16 | 2 | 3.418 | 16.938 | 9.568 | sampling_sensitive |
| DEC | M | 16 | 3 | 0.671 | 1.200 | - | sampling_sensitive |
| DEC | M_plus | 16 | 4 | 0.965 | 17.491 | - | sampling_sensitive |
| EC | M | 16 | 1 | - | 1.310 | 0.692 | sampling_sensitive |
| EC | M_plus | 16 | 1 | - | 4.718 | 3.623 | sampling_sensitive |
| PC | M | 16 | 1 | - | 1.239 | 1.319 | sampling_sensitive |
| PC | M_plus | 16 | 1 | - | 10.294 | 6.601 | sampling_sensitive |
| DME | M | 16 | 6 | 0.246 | 2.422 | 2.500 | sampling_sensitive |
| DME | M_plus | 16 | 5 | 0.441 | 5.480 | 12.239 | sampling_sensitive |
| DOL | M | 16 | 1 | - | -0.134 | 0.626 | single_conformer_representative |
| DOL | M_plus | 16 | 1 | - | 2.562 | 7.626 | sampling_sensitive |
| GBL | M | 16 | 1 | - | 0.562 | 0.697 | single_conformer_representative |
| GBL | M_plus | 16 | 1 | - | 6.881 | 4.743 | sampling_sensitive |
| SL | M | 16 | 1 | - | 1.261 | 2.957 | sampling_sensitive |
| SL | M_plus | 16 | 1 | - | 3.487 | 5.496 | sampling_sensitive |
| DMSO | M | 16 | 1 | - | 2.472 | 1.957 | sampling_sensitive |
| DMSO | M_plus | 16 | 1 | - | 4.278 | 6.252 | sampling_sensitive |
| AN | M | 16 | 1 | - | 0.257 | 0.367 | single_conformer_representative |
| AN | M_plus | 16 | 1 | - | 4.966 | 1.204 | sampling_sensitive |
| TMP | M | 16 | 1 | - | 2.183 | 1.784 | sampling_sensitive |
| TMP | M_plus | 16 | 2 | 3.052 | 16.378 | 5.937 | sampling_sensitive |

## 升级与停止规则

* 每态先保留最多 **3** 个独立低能极小；只有 3 -> 6 的变化跨过独立容差或改写 Top-k 才升到 6。
* 两轮后仍无法解析就报告 `sampling_limited` / `unresolved`，不为「得到翻转」调窗口。
* Li 配位 motif 采样单列登记，本轮未做。


## 第 2 轮：统一扩大的池

> 同样是**气相 GFN2 筛选**。第 2 轮对**已跑**的分子-态用同一个更大的池
> （64 起点、seed 20261011），不逐态调参，也不覆盖第 1 轮的行，两轮分开审计。尚未跑第 2 轮的态单列登记，不计入「统一池」的分母。

| 分子 | 态 | 撒点数 | 独立极小 | 生产几何相对最低 | 冻结起点相对最低 | 判定 |
| --- | --- | --- | --- | --- | --- | --- |
| DMC | M | 64 | 1 | 0.330 | 0.615 | single_conformer_representative |
| DMC | M_plus | 64 | 1 | 5.333 | 4.098 | sampling_sensitive |
| EMC | M | 64 | 2 | 0.453 | 0.729 | single_conformer_representative |
| EMC | M_plus | 64 | 2 | 16.938 | 9.568 | sampling_sensitive |
| DEC | M | 64 | 3 | 1.200 | - | sampling_sensitive |
| DEC | M_plus | 64 | 4 | 17.491 | - | sampling_sensitive |
| EC | M | 64 | 1 | 1.310 | 0.692 | sampling_sensitive |
| EC | M_plus | 64 | 1 | 4.718 | 3.624 | sampling_sensitive |
| PC | M | 64 | 1 | 1.239 | 1.319 | sampling_sensitive |
| PC | M_plus | 64 | 1 | 10.294 | 6.601 | sampling_sensitive |
| DME | M | 64 | 7 | 2.736 | 2.814 | sampling_sensitive |
| DME | M_plus | 64 | 6 | 6.092 | 12.851 | sampling_sensitive |
| DOL | M | 64 | 1 | -0.134 | 0.626 | single_conformer_representative |
| DOL | M_plus | 64 | 1 | 2.562 | 7.626 | sampling_sensitive |
| GBL | M | 64 | 1 | 0.562 | 0.697 | single_conformer_representative |
| GBL | M_plus | 64 | 1 | 6.881 | 4.743 | sampling_sensitive |
| SL | M | 64 | 1 | 1.261 | 2.957 | sampling_sensitive |
| SL | M_plus | 64 | 1 | 3.487 | 5.496 | sampling_sensitive |
| DMSO | M | 64 | 1 | 2.472 | 1.957 | sampling_sensitive |
| DMSO | M_plus | 64 | 1 | 4.278 | 6.252 | sampling_sensitive |
| AN | M | 64 | 1 | 0.257 | 0.367 | single_conformer_representative |
| AN | M_plus | 64 | 1 | 4.966 | 1.204 | sampling_sensitive |
| TMP | M | 64 | 2 | 2.183 | 1.784 | sampling_sensitive |
| TMP | M_plus | 64 | 3 | 17.562 | 7.121 | sampling_sensitive |

## 独立低能结构（可执行结构集合）

| 分子 | 态 | 序 | 相对最低 (kcal/mol) | 来源 | 几何（仓库相对路径） | sha256 前 12 位 |
| --- | --- | --- | --- | --- | --- | --- |
| DMC | M | 1 | 0.000 | conformer_r2#8 | `work/sampling/DMC/M/r2_c08/xtbopt.xyz` | `6361bd413f5e` |
| DMC | M_plus | 1 | 0.000 | conformer_r2#28 | `work/sampling/DMC/M_plus/r2_c28/xtbopt.xyz` | `b43a944f22f8` |
| EMC | M | 1 | 0.000 | conformer_r2#57 | `work/sampling/EMC/M/r2_c57/xtbopt.xyz` | `bdb404894745` |
| EMC | M | 2 | 0.675 | conformer#14 | `work/sampling/EMC/M/c14/xtbopt.xyz` | `2edfb9e07f0b` |
| EMC | M_plus | 1 | 0.000 | conformer_r2#4 | `work/sampling/EMC/M_plus/r2_c04/xtbopt.xyz` | `be25b4b3a638` |
| EMC | M_plus | 2 | 3.418 | conformer_r2#21 | `work/sampling/EMC/M_plus/r2_c21/xtbopt.xyz` | `208bbf1b506d` |
| DEC | M | 1 | 0.000 | conformer_r2#13 | `work/sampling/DEC/M/r2_c13/xtbopt.xyz` | `c2d13147b264` |
| DEC | M | 2 | 0.671 | conformer#3 | `work/sampling/DEC/M/c03/xtbopt.xyz` | `37908cfc52dd` |
| DEC | M | 3 | 1.350 | conformer_r2#23 | `work/sampling/DEC/M/r2_c23/xtbopt.xyz` | `29dd560290c2` |
| DEC | M_plus | 1 | 0.000 | conformer#15 | `work/sampling/DEC/M_plus/c15/xtbopt.xyz` | `f2897bb8fbdb` |
| DEC | M_plus | 2 | 0.965 | conformer_r2#22 | `work/sampling/DEC/M_plus/r2_c22/xtbopt.xyz` | `fac5143af30c` |
| DEC | M_plus | 3 | 2.299 | conformer_r2#46 | `work/sampling/DEC/M_plus/r2_c46/xtbopt.xyz` | `92a842452c99` |
| DEC | M_plus | 4 | 4.101 | conformer_r2#23 | `work/sampling/DEC/M_plus/r2_c23/xtbopt.xyz` | `f918e00bbc1c` |
| EC | M | 1 | 0.000 | conformer_r2#63 | `work/sampling/EC/M/r2_c63/xtbopt.xyz` | `7299f706409c` |
| EC | M_plus | 1 | 0.000 | conformer_r2#0 | `work/sampling/EC/M_plus/r2_c00/xtbopt.xyz` | `6da2555fbe94` |
| PC | M | 1 | 0.000 | conformer_r2#25 | `work/sampling/PC/M/r2_c25/xtbopt.xyz` | `f7b0e5500d32` |
| PC | M_plus | 1 | 0.000 | conformer_r2#46 | `work/sampling/PC/M_plus/r2_c46/xtbopt.xyz` | `ff038bb4e457` |
| DME | M | 1 | 0.000 | conformer_r2#14 | `work/sampling/DME/M/r2_c14/xtbopt.xyz` | `8caa1a2d108b` |
| DME | M | 2 | 0.314 | conformer_r2#22 | `work/sampling/DME/M/r2_c22/xtbopt.xyz` | `f258fc7101b1` |
| DME | M | 3 | 0.560 | conformer#3 | `work/sampling/DME/M/c03/xtbopt.xyz` | `6c3862dbecf9` |
| DME | M | 4 | 0.697 | conformer_r2#39 | `work/sampling/DME/M/r2_c39/xtbopt.xyz` | `e718829ca785` |
| DME | M | 5 | 1.054 | conformer#5 | `work/sampling/DME/M/c05/xtbopt.xyz` | `fe66cdf0a246` |
| DME | M | 6 | 1.807 | conformer_r2#25 | `work/sampling/DME/M/r2_c25/xtbopt.xyz` | `d747f3609773` |
| DME | M_plus | 1 | 0.000 | conformer_r2#14 | `work/sampling/DME/M_plus/r2_c14/xtbopt.xyz` | `8bca190ec7ec` |
| DME | M_plus | 2 | 0.612 | conformer_r2#23 | `work/sampling/DME/M_plus/r2_c23/xtbopt.xyz` | `e95d5760b6fc` |
| DME | M_plus | 3 | 1.053 | conformer#7 | `work/sampling/DME/M_plus/c07/xtbopt.xyz` | `07c09b994f43` |
| DME | M_plus | 4 | 2.133 | conformer_r2#55 | `work/sampling/DME/M_plus/r2_c55/xtbopt.xyz` | `b3f7d4861582` |
| DME | M_plus | 5 | 6.399 | conformer_r2#46 | `work/sampling/DME/M_plus/r2_c46/xtbopt.xyz` | `c15c83dd0401` |
| DME | M_plus | 6 | 6.607 | conformer_r2#13 | `work/sampling/DME/M_plus/r2_c13/xtbopt.xyz` | `d67fc79a67b2` |
| DOL | M | 1 | 0.000 | conformer#15 | `work/sampling/DOL/M/c15/xtbopt.xyz` | `68e15690f750` |
| DOL | M_plus | 1 | 0.000 | conformer_r2#40 | `work/sampling/DOL/M_plus/r2_c40/xtbopt.xyz` | `f4b34b0215d9` |
| GBL | M | 1 | 0.000 | conformer_r2#2 | `work/sampling/GBL/M/r2_c02/xtbopt.xyz` | `2ecb5f2e26c7` |
| GBL | M_plus | 1 | 0.000 | conformer#9 | `work/sampling/GBL/M_plus/c09/xtbopt.xyz` | `0eb3ffb9459e` |
| SL | M | 1 | 0.000 | conformer_r2#16 | `work/sampling/SL/M/r2_c16/xtbopt.xyz` | `17a359116759` |
| SL | M_plus | 1 | 0.000 | conformer_r2#53 | `work/sampling/SL/M_plus/r2_c53/xtbopt.xyz` | `e1ede874ee75` |
| DMSO | M | 1 | 0.000 | conformer_r2#50 | `work/sampling/DMSO/M/r2_c50/xtbopt.xyz` | `eba8df56a689` |
| DMSO | M_plus | 1 | 0.000 | conformer_r2#20 | `work/sampling/DMSO/M_plus/r2_c20/xtbopt.xyz` | `c722fdb033f3` |
| AN | M | 1 | 0.000 | conformer_r2#34 | `work/sampling/AN/M/r2_c34/xtbopt.xyz` | `f9690586e5fc` |
| AN | M_plus | 1 | 0.000 | conformer#10 | `work/sampling/AN/M_plus/c10/xtbopt.xyz` | `42d5f2054a42` |
| TMP | M | 1 | 0.000 | conformer_r2#48 | `work/sampling/TMP/M/r2_c48/xtbopt.xyz` | `e0e627c94e3b` |
| TMP | M | 2 | 0.480 | conformer_r2#27 | `work/sampling/TMP/M/r2_c27/xtbopt.xyz` | `d97d3c2769b0` |
| TMP | M_plus | 1 | 0.000 | conformer_r2#33 | `work/sampling/TMP/M_plus/r2_c33/xtbopt.xyz` | `e02af1fc2fb4` |
| TMP | M_plus | 2 | 1.184 | conformer_r2#27 | `work/sampling/TMP/M_plus/r2_c27/xtbopt.xyz` | `7abdf8d0a934` |
| TMP | M_plus | 3 | 4.235 | conformer#10 | `work/sampling/TMP/M_plus/c10/xtbopt.xyz` | `c0c9e8082edd` |

| 分子 | 态 | 池内独立极小 | 保留结构 | 第 1 轮用 | 池受限 | 升级状态 |
| --- | --- | --- | --- | --- | --- | --- |
| DMC | M | 1 | 1 | 1 | true | registered_pending_round1_free_energy_check |
| DMC | M_plus | 1 | 1 | 1 | true | registered_pending_round1_free_energy_check |
| EMC | M | 2 | 2 | 2 | true | registered_pending_round1_free_energy_check |
| EMC | M_plus | 2 | 2 | 2 | true | registered_pending_round1_free_energy_check |
| DEC | M | 3 | 3 | 3 | false | registered_pending_round1_free_energy_check |
| DEC | M_plus | 4 | 4 | 3 | false | registered_pending_round1_free_energy_check |
| EC | M | 1 | 1 | 1 | true | registered_pending_round1_free_energy_check |
| EC | M_plus | 1 | 1 | 1 | true | registered_pending_round1_free_energy_check |
| PC | M | 1 | 1 | 1 | true | registered_pending_round1_free_energy_check |
| PC | M_plus | 1 | 1 | 1 | true | registered_pending_round1_free_energy_check |
| DME | M | 6 | 6 | 3 | false | registered_pending_round1_free_energy_check |
| DME | M_plus | 6 | 6 | 3 | false | registered_pending_round1_free_energy_check |
| DOL | M | 1 | 1 | 1 | true | registered_pending_round1_free_energy_check |
| DOL | M_plus | 1 | 1 | 1 | true | registered_pending_round1_free_energy_check |
| GBL | M | 1 | 1 | 1 | true | registered_pending_round1_free_energy_check |
| GBL | M_plus | 1 | 1 | 1 | true | registered_pending_round1_free_energy_check |
| SL | M | 1 | 1 | 1 | true | registered_pending_round1_free_energy_check |
| SL | M_plus | 1 | 1 | 1 | true | registered_pending_round1_free_energy_check |
| DMSO | M | 1 | 1 | 1 | true | registered_pending_round1_free_energy_check |
| DMSO | M_plus | 1 | 1 | 1 | true | registered_pending_round1_free_energy_check |
| AN | M | 1 | 1 | 1 | true | registered_pending_round1_free_energy_check |
| AN | M_plus | 1 | 1 | 1 | true | registered_pending_round1_free_energy_check |
| TMP | M | 2 | 2 | 2 | true | registered_pending_round1_free_energy_check |
| TMP | M_plus | 3 | 3 | 3 | false | registered_pending_round1_free_energy_check |

* 每个独立 GFN2 极小保留一个最低能结构（最多 6 个）；`池受限 = true` 表示这个池
  在这一水平上只给出少于 3 个独立极小，结构集合无法凑满 3 个——这是登记的事实，不是结论。
  是否把第 3 个结构升到生产级，由登记规则在算出第 1 轮自由能之后决定。
