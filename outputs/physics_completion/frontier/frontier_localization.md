# 电子身份：前沿轨道组成分析（全系综成员）

> 生成器 `build_frontier_localization.py`（`--check` 完全只读）。
> 单点固定几何、冻结生产级别；Molden 由 `orca_2mkl job -molden` 生成。
> 分类阈值在**读任何结果之前**就冻结：轨道定域 weight ≥ 0.5，Li 定域 ≥ 0.25。

## 覆盖进度

| 项 | 值 |
|---|---|
| 系综加权成员（非仅 48 primary） | 80 |
| 已解析 | **76** |
| 待算 | 4 |

## 两个前沿并不一致

| 指标 | HOMO 侧 | LUMO 侧 |
|---|---|---|
| Li 权重最大值 | **0.004331** | **0.219803** |
| 分类分布 | donor_localized 41 / ligand_localized 35 | donor_localized 5 / li_localized 31 / ligand_localized 40 |

**Li 在 HOMO 中实质上不参与**（最大权重 4.3e-03，远低于 0.25 的 Li 定域阈值），但它在 LUMO 中可以占到 0.22。因此「Li 是否承载前线轨道」这个问题，**只问 HOMO 会得出错误答案**。

## Li 定域的例外（LUMO 侧）

| 成员 | Li_LUMO | 给体_LUMO | 分类 |
|---|---|---|---|
| `TMP|LiM_plus|primary` | 0.2198 | 0.5624 | `li_localized` |
| `DMC|LiM_plus|c05` | 0.2093 | 0.4625 | `li_localized` |
| `DMC|LiM_plus|primary` | 0.1892 | 0.5673 | `li_localized` |
| `EC|LiM_plus|primary` | 0.1697 | 0.4436 | `li_localized` |
| `EMC|LiM_plus|primary` | 0.1646 | 0.5241 | `li_localized` |
| `EMC|LiM_plus|c02` | 0.1442 | 0.4972 | `li_localized` |
| `PC|LiM_plus|c01` | 0.1422 | 0.3980 | `li_localized` |
| `DEC|LiM_plus|primary` | 0.1398 | 0.4775 | `li_localized` |
| `EMC|LiM_plus|c08` | 0.1363 | 0.4275 | `li_localized` |
| `DEC|LiM_plus|c09` | 0.1100 | 0.4200 | `li_localized` |
| `GBL|LiM_plus|c03` | 0.1083 | 0.2130 | `li_localized` |
| `DME|LiM_plus|primary` | 0.1041 | 0.5447 | `li_localized` |
| `SL|LiM_plus|c02` | 0.0899 | 0.2902 | `li_localized` |
| `DOL|LiM_plus|c02` | 0.0598 | 0.2486 | `li_localized` |
| `AN|LiM_plus|c01` | 0.0299 | 0.5326 | `li_localized` |
| `AN|LiM_plus|primary` | 0.0299 | 0.5326 | `li_localized` |
| `DMSO|LiM_2plus|primary` | 0.0035 | 0.8278 | `li_localized` |
| `DMSO|LiM_2plus|c01` | 0.0032 | 0.8296 | `li_localized` |
| `DME|LiM_2plus|primary` | 0.0024 | 0.4841 | `li_localized` |
| `DME|LiM_2plus|r3m_c05` | 0.0009 | 0.3472 | `li_localized` |
| `EMC|LiM_2plus|primary` | 0.0008 | 0.2676 | `li_localized` |
| `DOL|LiM_2plus|c05` | 0.0002 | 0.4589 | `li_localized` |
| `TMP|LiM_2plus|primary` | 0.0002 | 0.5930 | `li_localized` |
| `SL|LiM_2plus|primary` | 0.0002 | 0.4797 | `li_localized` |
| `TMP|LiM_2plus|r3m_c00` | 0.0001 | 0.5743 | `li_localized` |
| `TMP|LiM_2plus|c13` | 0.0001 | 0.5771 | `li_localized` |
| `PC|LiM_2plus|primary` | 0.0001 | 0.1878 | `li_localized` |
| `PC|LiM_2plus|c04` | 0.0001 | 0.1905 | `li_localized` |
| `DEC|LiM_2plus|c02` | 0.0000 | 0.2914 | `li_localized` |
| `DMC|LiM_2plus|primary` | 0.0000 | 0.4562 | `li_localized` |
| `EC|LiM_2plus|primary` | 0.0000 | 0.3234 | `li_localized` |

这些态的还原过程涉及 Li 本身，与「Li⁺ 氧化还原沉默」的一般规律相反。**它们是结论的边界，不是噪声**：报告一般规律时必须同时报告例外。

## HOMO/LUMO 分类不一致的成员

52 / 76 个已解析成员的 HOMO 与 LUMO 分类不同。

| 成员 | HOMO | LUMO |
|---|---|---|
| `AN|LiM_plus|c01` | `ligand_localized` | `li_localized` |
| `AN|LiM_plus|primary` | `ligand_localized` | `li_localized` |
| `DEC|LiM_2plus|c02` | `ligand_localized` | `li_localized` |
| `DEC|LiM_plus|c09` | `donor_localized` | `li_localized` |
| `DEC|LiM_plus|primary` | `ligand_localized` | `li_localized` |
| `DEC|M_plus|22` | `ligand_localized` | `donor_localized` |
| `DEC|M|13` | `donor_localized` | `ligand_localized` |
| `DEC|M|primary` | `donor_localized` | `ligand_localized` |
| `DEC|M|r2_c23` | `donor_localized` | `ligand_localized` |
| `DMC|LiM_2plus|primary` | `donor_localized` | `li_localized` |
| `DMC|LiM_plus|c05` | `donor_localized` | `li_localized` |
| `DMC|LiM_plus|primary` | `donor_localized` | `li_localized` |
| `DMC|M_plus|primary` | `donor_localized` | `ligand_localized` |
| `DMC|M|primary` | `donor_localized` | `ligand_localized` |
| `DME|LiM_2plus|primary` | `donor_localized` | `li_localized` |
| `DME|LiM_2plus|r3m_c05` | `ligand_localized` | `li_localized` |
| `DME|LiM_plus|primary` | `donor_localized` | `li_localized` |
| `DME|M|14` | `donor_localized` | `ligand_localized` |
| `DME|M|22` | `donor_localized` | `ligand_localized` |
| `DME|M|primary` | `donor_localized` | `ligand_localized` |
| … | 共 52 条 | |

## 已解析成员明细

| 成员 | Li_HOMO | 给体_HOMO | HOMO 分类 | Li_LUMO | 给体_LUMO | LUMO 分类 |
|---|---|---|---|---|---|---|
| `AN|LiM_2plus|primary` | 0.0001 | 0.4627 | `ligand_localized` | 0.0002 | 0.4397 | `ligand_localized` |
| `AN|LiM_plus|c01` | 0.0002 | 0.4668 | `ligand_localized` | 0.0299 | 0.5326 | `li_localized` |
| `AN|LiM_plus|primary` | 0.0002 | 0.4667 | `ligand_localized` | 0.0299 | 0.5326 | `li_localized` |
| `AN|M_plus|primary` | 0.0000 | 0.4734 | `ligand_localized` | 0.0000 | 0.4615 | `ligand_localized` |
| `AN|M|34` | 0.0000 | 0.4891 | `ligand_localized` | 0.0000 | 0.1963 | `ligand_localized` |
| `DEC|LiM_2plus|c02` | 0.0000 | 0.3126 | `ligand_localized` | 0.0000 | 0.2914 | `li_localized` |
| `DEC|LiM_plus|c09` | 0.0002 | 0.7495 | `donor_localized` | 0.1100 | 0.4200 | `li_localized` |
| `DEC|LiM_plus|primary` | 0.0001 | 0.4661 | `ligand_localized` | 0.1398 | 0.4775 | `li_localized` |
| `DEC|M_plus|15` | 0.0000 | 0.3372 | `ligand_localized` | 0.0000 | 0.8285 | `ligand_localized` |
| `DEC|M_plus|22` | 0.0000 | 0.3260 | `ligand_localized` | 0.0000 | 0.7943 | `donor_localized` |
| `DEC|M_plus|primary` | 0.0000 | 0.0720 | `ligand_localized` | 0.0000 | 0.2076 | `ligand_localized` |
| `DEC|M|13` | 0.0000 | 0.8542 | `donor_localized` | 0.0000 | 0.5205 | `ligand_localized` |
| `DEC|M|primary` | 0.0000 | 0.8579 | `donor_localized` | 0.0000 | 0.5149 | `ligand_localized` |
| `DEC|M|r2_c23` | 0.0000 | 0.9196 | `donor_localized` | 0.0000 | 0.5061 | `ligand_localized` |
| `DMC|LiM_2plus|primary` | 0.0001 | 0.6269 | `donor_localized` | 0.0000 | 0.4562 | `li_localized` |
| `DMC|LiM_plus|c05` | 0.0004 | 0.9516 | `donor_localized` | 0.2093 | 0.4625 | `li_localized` |
| `DMC|LiM_plus|primary` | 0.0000 | 0.6043 | `donor_localized` | 0.1892 | 0.5673 | `li_localized` |
| `DMC|M_plus|primary` | 0.0000 | 0.6956 | `donor_localized` | 0.0000 | 0.5292 | `ligand_localized` |
| `DMC|M|primary` | 0.0000 | 0.9441 | `donor_localized` | 0.0000 | 0.4859 | `ligand_localized` |
| `DME|LiM_2plus|primary` | 0.0013 | 0.4437 | `donor_localized` | 0.0024 | 0.4841 | `li_localized` |
| `DME|LiM_2plus|r3m_c05` | 0.0002 | 0.4019 | `ligand_localized` | 0.0009 | 0.3472 | `li_localized` |
| `DME|LiM_plus|primary` | 0.0024 | 0.4924 | `donor_localized` | 0.1041 | 0.5447 | `li_localized` |
| `DME|M_plus|23` | 0.0000 | 0.3831 | `ligand_localized` | 0.0000 | 0.3184 | `ligand_localized` |
| `DME|M_plus|c07` | 0.0000 | 0.4643 | `ligand_localized` | 0.0000 | 0.4557 | `ligand_localized` |
| `DME|M_plus|primary` | 0.0000 | 0.3744 | `ligand_localized` | 0.0000 | 0.3127 | `ligand_localized` |
| `DME|M|14` | 0.0000 | 0.4166 | `donor_localized` | 0.0000 | 0.4893 | `ligand_localized` |
| `DME|M|22` | 0.0000 | 0.5440 | `donor_localized` | 0.0000 | 0.5041 | `ligand_localized` |
| `DME|M|primary` | 0.0000 | 0.5225 | `donor_localized` | 0.0000 | 0.4634 | `ligand_localized` |
| `DMSO|LiM_2plus|c01` | 0.0002 | 0.7967 | `donor_localized` | 0.0032 | 0.8296 | `li_localized` |
| `DMSO|LiM_2plus|primary` | 0.0002 | 0.7961 | `donor_localized` | 0.0035 | 0.8278 | `li_localized` |
| `DMSO|M_plus|primary` | 0.0000 | 0.8095 | `donor_localized` | 0.0000 | 0.8123 | `donor_localized` |
| `DMSO|M|primary` | 0.0000 | 0.8331 | `donor_localized` | 0.0000 | 0.2609 | `donor_localized` |
| `DOL|LiM_2plus|c05` | 0.0002 | 0.4720 | `donor_localized` | 0.0002 | 0.4589 | `li_localized` |
| `DOL|LiM_plus|c02` | 0.0006 | 0.5016 | `donor_localized` | 0.0598 | 0.2486 | `li_localized` |
| `DOL|M_plus|40` | 0.0000 | 0.5332 | `ligand_localized` | 0.0000 | 0.3966 | `ligand_localized` |
| `DOL|M_plus|primary` | 0.0000 | 0.5339 | `ligand_localized` | 0.0000 | 0.3939 | `ligand_localized` |
| `DOL|M|15` | 0.0000 | 0.5639 | `donor_localized` | 0.0000 | 0.2831 | `ligand_localized` |
| `EC|LiM_2plus|primary` | 0.0000 | 0.4161 | `ligand_localized` | 0.0000 | 0.3234 | `li_localized` |
| `EC|LiM_plus|primary` | 0.0000 | 0.4619 | `ligand_localized` | 0.1697 | 0.4436 | `li_localized` |
| `EC|M_plus|0` | 0.0000 | 0.7442 | `ligand_localized` | 0.0000 | 0.3659 | `ligand_localized` |
| `EC|M_plus|primary` | 0.0000 | 0.7435 | `ligand_localized` | 0.0000 | 0.3639 | `ligand_localized` |
| `EC|M|63` | 0.0000 | 0.9175 | `donor_localized` | 0.0000 | 0.3299 | `ligand_localized` |
| `EMC|LiM_2plus|primary` | 0.0003 | 0.3974 | `ligand_localized` | 0.0008 | 0.2676 | `li_localized` |
| `EMC|LiM_plus|c02` | 0.0002 | 0.5204 | `donor_localized` | 0.1442 | 0.4972 | `li_localized` |
| `EMC|LiM_plus|c08` | 0.0003 | 0.8316 | `donor_localized` | 0.1363 | 0.4275 | `li_localized` |
| `EMC|LiM_plus|primary` | 0.0002 | 0.5031 | `donor_localized` | 0.1646 | 0.5241 | `li_localized` |
| `EMC|M_plus|21` | 0.0000 | 0.5615 | `ligand_localized` | 0.0000 | 0.3364 | `ligand_localized` |
| `EMC|M_plus|primary` | 0.0000 | 0.3263 | `ligand_localized` | 0.0000 | 0.8641 | `donor_localized` |
| `EMC|M|14` | 0.0000 | 0.9327 | `donor_localized` | 0.0000 | 0.4936 | `ligand_localized` |
| `EMC|M|primary` | 0.0000 | 0.8776 | `donor_localized` | 0.0000 | 0.5001 | `ligand_localized` |
| `GBL|LiM_2plus|c04` | 0.0000 | 0.2041 | `ligand_localized` | 0.0000 | 0.2634 | `ligand_localized` |
| `GBL|LiM_2plus|primary` | 0.0000 | 0.2044 | `ligand_localized` | 0.0000 | 0.2656 | `ligand_localized` |
| `GBL|LiM_plus|c03` | 0.0043 | 0.6639 | `donor_localized` | 0.1083 | 0.2130 | `li_localized` |
| `GBL|M_plus|primary` | 0.0000 | 0.2042 | `ligand_localized` | 0.0000 | 0.7065 | `ligand_localized` |
| `GBL|M|2` | 0.0000 | 0.7111 | `donor_localized` | 0.0000 | 0.3219 | `ligand_localized` |
| `GBL|M|primary` | 0.0000 | 0.7112 | `donor_localized` | 0.0000 | 0.3217 | `ligand_localized` |
| `PC|LiM_2plus|c04` | 0.0000 | 0.2711 | `ligand_localized` | 0.0001 | 0.1905 | `li_localized` |
| `PC|LiM_2plus|primary` | 0.0000 | 0.2713 | `ligand_localized` | 0.0001 | 0.1878 | `li_localized` |
| `PC|LiM_plus|c01` | 0.0000 | 0.3347 | `ligand_localized` | 0.1422 | 0.3980 | `li_localized` |
| `PC|M_plus|46` | 0.0000 | 0.2906 | `ligand_localized` | 0.0000 | 0.2136 | `ligand_localized` |
| `PC|M_plus|primary` | 0.0000 | 0.2894 | `ligand_localized` | 0.0000 | 0.2129 | `ligand_localized` |
| `PC|M|25` | 0.0000 | 0.7842 | `donor_localized` | 0.0000 | 0.3029 | `ligand_localized` |
| `SL|LiM_2plus|c02` | 0.0001 | 0.4592 | `ligand_localized` | 0.0002 | 0.5064 | `ligand_localized` |
| `SL|LiM_2plus|primary` | 0.0001 | 0.4848 | `ligand_localized` | 0.0002 | 0.4797 | `li_localized` |
| `SL|LiM_plus|c02` | 0.0003 | 0.5183 | `donor_localized` | 0.0899 | 0.2902 | `li_localized` |
| `SL|M_plus|53` | 0.0000 | 0.4778 | `ligand_localized` | 0.0000 | 0.4612 | `ligand_localized` |
| `SL|M_plus|primary` | 0.0000 | 0.4780 | `ligand_localized` | 0.0000 | 0.4596 | `ligand_localized` |
| `SL|M|16` | 0.0000 | 0.5569 | `donor_localized` | 0.0000 | 0.5777 | `donor_localized` |
| `TMP|LiM_2plus|c13` | 0.0000 | 0.5852 | `donor_localized` | 0.0001 | 0.5771 | `li_localized` |
| `TMP|LiM_2plus|primary` | 0.0002 | 0.7121 | `donor_localized` | 0.0002 | 0.5930 | `li_localized` |
| `TMP|LiM_2plus|r3m_c00` | 0.0000 | 0.5907 | `donor_localized` | 0.0001 | 0.5743 | `li_localized` |
| `TMP|LiM_plus|primary` | 0.0002 | 0.7382 | `donor_localized` | 0.2198 | 0.5624 | `li_localized` |
| `TMP|M_plus|27` | 0.0000 | 0.8399 | `donor_localized` | 0.0000 | 0.6246 | `ligand_localized` |
| `TMP|M_plus|primary` | 0.0000 | 0.6794 | `donor_localized` | 0.0000 | 0.9324 | `ligand_localized` |
| `TMP|M|27` | 0.0000 | 0.8872 | `donor_localized` | 0.0000 | 0.6771 | `ligand_localized` |
| `TMP|M|primary` | 0.0000 | 0.8717 | `donor_localized` | 0.0000 | 0.6947 | `ligand_localized` |

**口径**：本报告只描述已解析成员的轨道组成，不改变任何验收判定。
待算成员补齐后本表会自动扩展——覆盖率本身就是「并行补电子身份」这项工作的进度。
