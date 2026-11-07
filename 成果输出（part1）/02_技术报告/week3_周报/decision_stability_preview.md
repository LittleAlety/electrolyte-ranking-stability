# Week 3 / Stage 2 -- 决策稳定性预演 (P0 内部, 无 r2SCAN-3c 对照)

> 诚实声明: 本文件是 P0 代理量内部的预演, 还没有 r2SCAN-3c 的 P1/P2 对照。
> P0 只用于回答 '极低成本的轨道能标量是否已经保留目标排序', 不得解释为真实 redox 电位。
> k 值取 config/prereg.yaml 的 fractions = [0.10, 0.20, 0.30]。

## 1. 设置

- core set 成功分子: 18
- broad pool 成功分子: 40
- 合并集合: 58
- Kendall tau(P0_ox, P0_red) on combined = -0.302

## 2. objective 敏感性: P0_ox 与 P0_red 的 top-k 是否一致

| pool | N | k(10%) | overlap@k | Jaccard | k(20%) | overlap@k | Jaccard | k(30%) | overlap@k | Jaccard |
|---|---|---|---|---|---|---|---|---|---|---|
| core | 18 | 2 | 0.000 | 0.000 | 4 | 0.000 | 0.000 | 5 | 0.000 | 0.000 |
| broad | 40 | 4 | 0.000 | 0.000 | 8 | 0.000 | 0.000 | 12 | 0.167 | 0.091 |
| combined | 58 | 6 | 0.000 | 0.000 | 12 | 0.000 | 0.000 | 17 | 0.176 | 0.097 |

- core: Kendall tau(P0_ox, P0_red) = -0.425
- broad: Kendall tau(P0_ox, P0_red) = -0.244
- combined: Kendall tau(P0_ox, P0_red) = -0.302

## 3. pool 扩展敏感性: core-only 领袖在新池 (core+broad) 中是否保留

| fraction | k_core | k_union | core 领袖存活比例 | union 氧化侧 top-k |
|---|---|---|---|---|
| 0.10 | 2 | 6 | 0.500 (1/2) | B05, B17, B18, B19, B32, C06 |
| 0.20 | 4 | 12 | 0.750 (3/4) | B03, B05, B07, B08, B17, B18, B19, B29, B32, C04, C05, C06 |
| 0.30 | 5 | 17 | 1.000 (5/5) | B03, B04, B05, B07, B08, B17, B18, B19, B29, B32, B38, C01, C02, C04, C05, C06, C18 |

## 4. reference ligand 敏感性 (primary_R = DME, secondary_R = AN)

| R | role | P0_ox(R) | 氧化侧 '优于 R' 的候选数 | P0_red(R) |
|---|---|---|---|---|
| DME | primary_R | 10.849 | 44 | 0.718 |
| AN | secondary_R | 11.611 | 25 | -5.500 |

- '优于 DME' 与 '优于 AN' 两个候选集合的 Jaccard = 0.568, overlap = 0.568。
- 对照: 把 P0_ox 整体平移 (即换成以某个 R 为参照的相对量) 后, Kendall tau = 1.000。

**结论 (诚实版)**: P0 = -eps_HOMO / +eps_LUMO 的排序本身对 reference ligand R 完全不敏感
(P0 的定义中根本不含 R; 平移参照不改变 order, tau = 1)。真正会随 R 变化的是以参照分子为基准的
入选阈值决策 (上表 '优于 R 的候选数')。因此任何 P0 给出的 R-dependent 结论都必须推迟到
P1/P2 (Li-complex exchange 反应) 才能判定; 本预演只能量化 P0 内部的可复现性。

## 5. proxy 敏感性: 平凡廉价描述符能否复现 P0_ox 的 top-k

| fraction | MW Jaccard | TPSA Jaccard | alpha Jaccard | dipole Jaccard |
|---|---|---|---|---|
| 0.10 | 0.000 | 0.000 | 0.091 | 0.000 |
| 0.20 | 0.000 | 0.000 | 0.091 | 0.143 |
| 0.30 | 0.000 | 0.000 | 0.062 | 0.259 |

低 Jaccard 说明 P0_ox 的 top-k 不能被简单的分子量/极性/极化率/偶极排序复现,
因此把 P0 换成这些辅助描述符会实质改变筛选决策 (但它们被 explicitly_excluded_from_P0)。

## 6. 极化率 (alpha) 说明

GFN2-xTB 6.7.1 支持 --alpha (xtb --help 列出 '--alpha  requests ... static molecular dipole polarizabilities')。已对 10 个分子额外跑了单点 --alpha 作业 (基于 GFN2 优化几何), 结果记为 auxiliary (aux_alpha_bohr3, 单位 a.u. = Bohr^3)。注意: 该版本默认的 --opt 输出本身也打印 Mol. alpha(0), 主 CSV 的 aux_alpha_bohr3 即来自主运行, 额外 --alpha 作业用于交叉确认。alpha 不参与任何 P0 排序。

## 7. 局限

- 只有 P0 (气体相 free-molecule 轨道能), 无溶剂、无显式 Li+, 无 r2SCAN-3c 对照。
- 单一构象 (RDKit ETKDG + MMFF 预优化 -> GFN2 优化), 未做构象系综采样, 未评估构象不确定度。
- top-k 只比较集合成员, 未使用 delta_m / sigma_ij (需要 P1/P2 的不确定度才可定义)。
- P0 与任何真实 redox 排序之间的关联仍需 Stage 3 的 validated target 才能量化。
