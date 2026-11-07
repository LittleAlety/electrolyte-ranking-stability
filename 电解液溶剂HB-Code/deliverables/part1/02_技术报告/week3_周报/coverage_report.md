# Week 3 / Stage 2 -- 化学空间覆盖检查 (core set vs broad pool)

本报告由 scripts/run_broad_pool_p0.py --pool both 生成; 覆盖轴定义依据
data/metadata/chemical_space_metadata.md 与 docs/00_stage0_definitions.md。

## 1. family 覆盖

| family | core set (N=18) | broad pool (N=40) |
|---|---|---|
| cyclic_carbonate | 4 | 5 |
| ester | 3 | 4 |
| ether | 3 | 11 |
| linear_carbonate | 3 | 3 |
| nitrile | 2 | 5 |
| phosphate | 1 | 3 |
| siloxane | 0 | 2 |
| sulfite | 0 | 1 |
| sulfone | 1 | 3 |
| sulfoxide | 1 | 2 |
| sultone | 0 | 1 |

broad pool 新增 (core set 完全没有) 的 family: siloxane, sulfite, sultone。

## 2. 二值标签覆盖

| 轴 | core set yes/no | broad pool yes/no |
|---|---|---|
| fluorinated | 1 / 17 | 6 / 34 |
| cyclic | 7 / 11 | 14 / 26 |
| flexible | 1 / 17 | 7 / 33 |

## 3. 分子量分箱

| MW 区间 | core set | broad pool |
|---|---|---|
| <90 | 9 | 11 |
| 90-120 | 6 | 14 |
| 120-160 | 2 | 5 |
| 160-220 | 0 | 6 |
| >=220 | 1 | 4 |

## 4. 可旋转键分箱 (柔性)

| rotatable_bonds | core set | broad pool |
|---|---|---|
| 0 | 11 | 16 |
| 1-2 | 4 | 14 |
| 3-4 | 2 | 4 |
| 5+ | 1 | 6 |

## 5. 给体数目分布 (donor_count)

| donor_count | core set | broad pool |
|---|---|---|
| 1 | 2 | 11 |
| 2 | 7 | 14 |
| 3 | 7 | 11 |
| 4 | 1 | 4 |
| 5 | 1 | 0 |

## 6. 连续描述符分布 (min / median / max)

| 描述符 | core set | broad pool |
|---|---|---|
| mw | 41.050 / 89.095 / 222.280 | 55.080 / 111.130 / 344.070 |
| tpsa | 17.070 / 35.530 / 47.580 | 9.230 / 30.355 / 47.580 |
| heteroatom_count | 1.000 / 3.000 / 5.000 | 1.000 / 3.000 / 14.000 |
| donor_count | 1.000 / 2.500 / 5.000 | 1.000 / 2.000 / 4.000 |

## 7. 结论: 哪些轴被扩展 / 仍稀疏 / 谁没被覆盖

**被扩展的轴**

- family: broad pool 新增 siloxane, sulfite, sultone, 覆盖了 core set 完全没有的骨架化学。
- 分子量: core 上限 222.3 g/mol, broad 上限 344.1 g/mol; broad 进入更高分子量的氟化/磷酸酯/硅氧烷区域。
- 氟化: core 仅 1/18 氟化, broad 6/40; broad 把氟化从单一 FEC 扩展到氟代碳酸酯/醚/磷酸酯。
- 给体数目: 齿数上限 core = 5, broad = 4; 该轴上 core 本身已覆盖更高齿数, broad 未扩展。
- 柔性: 两者可旋转键上限均为 12; broad 在高柔档 (rotatable_bonds 5+) 更密 (core 1 vs broad 6), 属密度扩展而非上限扩展。

**仍然稀疏 / 未被覆盖的轴**

- 芳香族: 仅 broad 的 B02 (DPC) 一个, 无法支持任何芳香族统计。
- 卤素 (非 F): 仅 broad 的 B08 (ClEC) 一个, core 完全没有卤素对照。
- 硅氧烷 / 亚硫酸酯 / 磺酸内酯: 只有 broad 各 1-2 个, core 完全没有, 属 '探点' 而非系统序列。
- 高介电 / 高给体强度端点: 仍以少数常见溶剂为主, 未做系统同族取代扫描。
- 阴离子 / 盐 / Li 配合物形态: 完全未覆盖 (P0 只针对中性 free molecule, 符合设计)。

## 8. P0 数值覆盖 (真实 xTB 结果)

| 量 | core set min/median/max | broad pool min/median/max |
|---|---|---|
| p0_ox_ev | 10.424 / 11.745 / 12.995 | 10.176 / 11.439 / 13.857 |
| p0_red_ev | -6.877 / -5.774 / 0.718 | -6.825 / -5.394 / 0.898 |

## 9. 图

- fig1_family_counts.png: family 计数对比 (英文标签)。
- fig2_mw_donor.png: MW-donor_count 散点, 按 family 着色, 形状区分 core/broad。
- fig3_p0_ox_fluorinated.png: 氟化 / 非氟化 的 p0_ox 分布。

> 注: matplotlib 环境可能缺少中文字体, 因此图内标签全部使用英文, 以免出现方框。
