# 方案 6.1 第 1 轮构象采样（气相 GFN2 筛选）

> 由 `scripts/wp_production/build_wp2_sampling.py` 生成。采样层是**气相 GFN2-xTB 筛选**，
> 不是生产级 `wB97X-D4 + SMD(acetonitrile)`；它只回答「单一代表结构是否落在同一极小附近」。
>
> **集合偏差**：方案 3.3 指定的采样集是 EMC/DEC/DME/TMP，本层实际执行的是 DMC/EMC/GBL/SL
> （两对翻转的决定性自由态 / 阳离子态）。偏差登记在 `sampling_index.json` 的
> `cohort_deviation`，**不宣称完成方案 3.3**；DEC / DME / TMP 没有任何采样产物。

| 分子 | 态 | 撒点数 | 独立极小 | 次低极小 | 生产几何相对最低 | 冻结起点相对最低 | 判定 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| DMC | M | 16 | 1 | - | 0.330 | 0.615 | single_conformer_representative |
| DMC | M_plus | 16 | 1 | - | 4.098 | 4.098 | sampling_sensitive |
| EMC | M | 16 | 2 | 0.675 | 0.453 | 0.729 | single_conformer_representative |
| EMC | M_plus | 16 | 2 | 3.418 | 16.938 | 9.568 | sampling_sensitive |
| GBL | M | 16 | 1 | - | 0.562 | 0.697 | single_conformer_representative |
| GBL | M_plus | 16 | 1 | - | 6.881 | 4.743 | sampling_sensitive |
| SL | M | 16 | 1 | - | 1.261 | 2.957 | sampling_sensitive |
| SL | M_plus | 16 | 1 | - | 3.487 | 5.496 | sampling_sensitive |

## 升级与停止规则

* 每态先保留最多 **3** 个独立低能极小；只有 3 -> 6 的变化跨过独立容差或改写 Top-k 才升到 6。
* 两轮后仍无法解析就报告 `sampling_limited` / `unresolved`，不为「得到翻转」调窗口。
* Li 配位 motif 采样单列登记，本轮未做。


## 第 2 轮：统一扩大的池

> 同样是**气相 GFN2 筛选**。第 2 轮对所有 8 个分子-态用同一个更大的池
> （64 起点、seed 20261011），不逐态调参，也不覆盖第 1 轮的行，两轮分开审计。

| 分子 | 态 | 撒点数 | 独立极小 | 生产几何相对最低 | 冻结起点相对最低 | 判定 |
| --- | --- | --- | --- | --- | --- | --- |
| DMC | M | 64 | 1 | 0.330 | 0.615 | single_conformer_representative |
| DMC | M_plus | 64 | 1 | 4.098 | 4.098 | sampling_sensitive |
| EMC | M | 64 | 2 | 0.453 | 0.729 | single_conformer_representative |
| EMC | M_plus | 64 | 2 | 16.938 | 9.568 | sampling_sensitive |
| GBL | M | 64 | 1 | 0.562 | 0.697 | single_conformer_representative |
| GBL | M_plus | 64 | 1 | 6.881 | 4.743 | sampling_sensitive |
| SL | M | 64 | 1 | 1.261 | 2.957 | sampling_sensitive |
| SL | M_plus | 64 | 1 | 3.487 | 5.496 | sampling_sensitive |

## 独立低能结构（可执行结构集合）

| 分子 | 态 | 序 | 相对最低 (kcal/mol) | 来源 | 几何（仓库相对路径） | sha256 前 12 位 |
| --- | --- | --- | --- | --- | --- | --- |
| DMC | M | 1 | 0.000 | conformer_r2#8 | `work/sampling/DMC/M/r2_c08/xtbopt.xyz` | `7c1d88690fc0` |
| DMC | M_plus | 1 | 0.000 | conformer_r2#28 | `work/sampling/DMC/M_plus/r2_c28/xtbopt.xyz` | `f7956d842a70` |
| EMC | M | 1 | 0.000 | conformer_r2#57 | `work/sampling/EMC/M/r2_c57/xtbopt.xyz` | `abcc51b6f1a5` |
| EMC | M | 2 | 0.675 | conformer#14 | `work/sampling/EMC/M/c14/xtbopt.xyz` | `7c3de08711ac` |
| EMC | M_plus | 1 | 0.000 | conformer_r2#4 | `work/sampling/EMC/M_plus/r2_c04/xtbopt.xyz` | `6a9834c39cc9` |
| EMC | M_plus | 2 | 3.418 | conformer_r2#21 | `work/sampling/EMC/M_plus/r2_c21/xtbopt.xyz` | `32e385f45cb3` |
| GBL | M | 1 | 0.000 | conformer_r2#2 | `work/sampling/GBL/M/r2_c02/xtbopt.xyz` | `ae28786ba82b` |
| GBL | M_plus | 1 | 0.000 | conformer#9 | `work/sampling/GBL/M_plus/c09/xtbopt.xyz` | `743994b2edc1` |
| SL | M | 1 | 0.000 | conformer_r2#16 | `work/sampling/SL/M/r2_c16/xtbopt.xyz` | `46ba26d6a5ee` |
| SL | M_plus | 1 | 0.000 | conformer_r2#24 | `work/sampling/SL/M_plus/r2_c24/xtbopt.xyz` | `51872442626a` |

| 分子 | 态 | 池内独立极小 | 保留结构 | 第 1 轮用 | 池受限 | 升级状态 |
| --- | --- | --- | --- | --- | --- | --- |
| DMC | M | 1 | 1 | 1 | true | registered_pending_round1_free_energy_check |
| DMC | M_plus | 1 | 1 | 1 | true | registered_pending_round1_free_energy_check |
| EMC | M | 2 | 2 | 2 | true | registered_pending_round1_free_energy_check |
| EMC | M_plus | 2 | 2 | 2 | true | registered_pending_round1_free_energy_check |
| GBL | M | 1 | 1 | 1 | true | registered_pending_round1_free_energy_check |
| GBL | M_plus | 1 | 1 | 1 | true | registered_pending_round1_free_energy_check |
| SL | M | 1 | 1 | 1 | true | registered_pending_round1_free_energy_check |
| SL | M_plus | 1 | 1 | 1 | true | registered_pending_round1_free_energy_check |

* 每个独立 GFN2 极小保留一个最低能结构（最多 6 个）；`池受限 = true` 表示这个池
  在这一水平上只给出少于 3 个独立极小，结构集合无法凑满 3 个——这是登记的事实，不是结论。
  是否把第 3 个结构升到生产级，由登记规则在算出第 1 轮自由能之后决定。
