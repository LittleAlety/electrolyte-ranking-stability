# F55 统计 · Week 25 · 配位位移 ΔΔG_coord 与描述符标签的关系

- 图件：`outputs/figures/F55_coord_descriptor_tags.png`（6.3 × 6.6 in @ 200 dpi）
- 生成脚本：`scripts/analyze_w25_figure_f55.py`（确定性 / 幂等 / --check）
- 对应：核心文件 v2 §24 Figure 5 Mechanisms of coordination-induced inversion（L1480–1488）；docs/43 §5 缺口 #2
- 零新增电子结构计算：全部数字读自 outputs/ 与 data/ 既有产物

## 0. 速览

子集 n = 10（C1 有条件态的分子；core-18 的其余 8 个没有 C1，不在本表内）。

| 轴 | 描述符 | n | Spearman ρ | 精确置换 p | 置换数 | 状态 |
|---|---|---|---|---|---|---|
| oxidation | donor_count | 10 | -0.7942 | 0.0077 | 3628800 | ok |
| reduction | donor_count | 10 | -0.0586 | 0.8788 | 3628800 | ok |
| oxidation | li_contacts_n | 10 | 0.4264 | 0.2571 | 3628800 | ok |
| reduction | li_contacts_n | 10 | 0.0000 | 1.0000 | 3628800 | ok |
| oxidation | heteroatom_count | 10 | -0.7015 | 0.0282 | 3628800 | ok |
| reduction | heteroatom_count | 10 | -0.1377 | 0.7151 | 3628800 | ok |
| oxidation | rotatable_bonds | 10 | -0.2547 | 0.4833 | 3628800 | ok |
| reduction | rotatable_bonds | 10 | -0.1049 | 0.7833 | 3628800 | ok |
| oxidation | tpsa | 10 | -0.8903 | 0.0011 | 3628800 | ok |
| reduction | tpsa | 10 | -0.4573 | 0.1853 | 3628800 | ok |
| oxidation | n_heavy | 10 | -0.6659 | 0.0394 | 3628800 | ok |
| reduction | n_heavy | 10 | -0.3426 | 0.3387 | 3628800 | ok |
| oxidation | mw | 10 | -0.5636 | 0.0963 | 3628800 | ok |
| reduction | mw | 10 | -0.1636 | 0.6567 | 3628800 | ok |

可估计秩相关 14 / 14；可估计组间对比 3 / 47；not_estimable 条目 17 条。

## 1. 口径与符号

- oxidation：dIP = IP([LiM]+) - IP(M, C0@G2)；正值 = 配位后更难氧化（氧化稳定性提高）（来源 outputs/week5/c1_coord_shifts.csv · d_ip_ev）
- reduction：dEA = EA([LiM]+) - EA(M, C0@G2)；正值 = 配位后更易还原（来源 outputs/week5/c1_coord_shifts.csv · d_ea_ev）
  - 注意：week9 stage10 报 -dEA（p_red = -EA, higher_is_better），两者符号相反

与 week9 的交叉核对：ladder[C0_to_C1,oxidation,native].shift_mean_ev = 4.8872 eV，本脚本逐分子重算均值 = 4.8872 eV，差 = 0.00000000 eV；ladder 还原轴 -6.5782 eV 对应本表的 -mean(dEA)（两者符号约定相反）。
ladder 的排序侧读数（同一 C0_to_C1）：氧化轴 tau_b = 0.6889、f_unresolved_after = 0.2000；还原轴 tau_b = -0.4667、f_unresolved_after = 0.8000；两个轴的 f_robust_inv 都是 0.0。还原轴是五个台阶里唯一 tau_b 为负的一格，即配位把还原轴排序整体打乱——这与下面「还原轴位移对任何数值描述符都没有提示性关系」互相印证。

## 2. 子集与 n

- C1 子集 n = 10：AN、DMC、DME、DMSO、DOL、EC、GBL、SL、SN、TMP
- 主 motif 数 = 10（is_primary=True 的唯一逐分子记录；TMP/DMC 另有 m2 非主 motif，未计入）
- week5 汇总 n_motifs = 12（含非主 motif）；core-18 = 18

## 3. 单齿/双齿判据

单齿/双齿判据（三口径，需分清）：(1) 图上与分层用的齿数取自 outputs/week5/c1_coord_shifts.csv 的 li_contacts（主 motif, is_primary=True）列表长度：n_Li=1 记单齿、n_Li>=2 记双齿/多齿，这是实际 C1 几何里 Li 接触到的 donor 数目。(2) data/metadata/core_set.csv 的 donor_atoms（如 O=;O-、O-、N）给出的是 donor 类型而非齿数，按分号拆分得到 donor_type_count。(3) donor_count 是该分子里 donor 杂原子的总数。只有 donor_count>=2 且几何上确有 >=2 个接触时才算可螯合；metadata 的 chelating tag 与 (1) 在 DME、SN 上一致，而 DOL、SL 虽 n_Li=2 却未打 chelating tag。

## 4. 逐分子位移与描述符标签

li_contacts 列是 Li 实际接触到的 donor 原子索引（取自 c1_coord_shifts.csv · li_contacts），n_Li 为其长度；dIP/dEA 为该分子主 motif 的两轴位移。

| mol_id | name | family | role | donor_atoms | donor_count | li_contacts | n_Li | denticity | rot_bonds | tpsa | n_heavy | mw | hetero | tags | state_identity | dIP (eV) | dEA (eV) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| C16 | AN | nitrile | co-solvent | N | 1 | 2 | 1 | 单齿 | 0 | 23.79 | 3 | 41.05 | 1 | linear | no_intact_minimum_found | 5.1054 | 7.0731 |
| C01 | DMC | linear_carbonate | solvent | O=;O- | 3 | 3 | 1 | 单齿 | 0 | 35.53 | 6 | 90.08 | 3 | linear | molecule_centered_redox | 4.3351 | 7.1574 |
| C08 | DME | ether | solvent | O- | 2 | 1;4 | 2 | 双齿/多齿 | 3 | 18.46 | 6 | 90.12 | 2 | linear|chelating | molecule_centered_redox | 5.1343 | 7.0674 |
| C15 | DMSO | sulfoxide | co-solvent | O= | 1 | 3 | 1 | 单齿 | 0 | 17.07 | 4 | 78.14 | 2 | linear|sulfur_containing | no_intact_minimum_found | 5.1843 | 6.4665 |
| C09 | DOL | ether | co-solvent | O- | 2 | 2;4 | 2 | 双齿/多齿 | 0 | 18.46 | 5 | 74.08 | 2 | cyclic | no_intact_minimum_found | 6.1556 | 8.0610 |
| C04 | EC | cyclic_carbonate | solvent | O=;O- | 3 | 4 | 1 | 单齿 | 0 | 35.53 | 6 | 88.06 | 3 | cyclic | molecule_centered_redox | 4.3208 | 6.1550 |
| C13 | GBL | ester | co-solvent | O=;O- | 2 | 0 | 1 | 单齿 | 0 | 26.30 | 6 | 86.09 | 2 | cyclic | molecule_centered_redox | 4.9011 | 6.1777 |
| C14 | SL | sulfone | co-solvent | O= | 2 | 0;2 | 2 | 双齿/多齿 | 0 | 34.14 | 7 | 120.17 | 3 | cyclic|sulfur_containing | molecule_centered_redox | 4.9288 | 6.2203 |
| C18 | SN | nitrile | additive | N | 2 | 0;5 | 2 | 双齿/多齿 | 1 | 47.58 | 6 | 80.09 | 2 | linear|chelating | no_intact_minimum_found | 4.7775 | 4.9273 |
| C17 | TMP | phosphate | additive | O=;O- | 4 | 3 | 1 | 单齿 | 3 | 44.76 | 8 | 140.07 | 5 | linear|phosphorus_containing | molecule_centered_redox | 4.0293 | 6.4765 |

## 5. 标签分层对比（中位数 / IQR / n）


### denticity —— 配位齿数（C1 主 motif 的 Li 接触数）

| level | n | members | dIP median [q1, q3] (min–max) | dEA median [q1, q3] (min–max) |
|---|---|---|---|---|
| 单齿 (n_Li=1) | 6 | AN、DMC、DMSO、EC、GBL、TMP | 4.618 [4.324, 5.054] (4.029–5.184) | 6.472 [6.250, 6.924] (6.155–7.157) |
| 双齿/多齿 (n_Li>=2) | 4 | DME、DOL、SL、SN | 5.032 [4.891, 5.390] (4.778–6.156) | 6.644 [5.897, 7.316] (4.927–8.061) |

### donor_element —— donor 元素类型（来自 donor_atoms）

| level | n | members | dIP median [q1, q3] (min–max) | dEA median [q1, q3] (min–max) |
|---|---|---|---|---|
| N | 2 | AN、SN | 4.941 [4.859, 5.023] (4.778–5.105) | 6.000 [5.464, 6.537] (4.927–7.073) |
| O | 8 | DMC、DME、DMSO、DOL、EC、GBL、SL、TMP | 4.915 [4.332, 5.147] (4.029–6.156) | 6.472 [6.210, 7.090] (6.155–8.061) |

### donor_count —— donor 杂原子数 donor_count

| level | n | members | dIP median [q1, q3] (min–max) | dEA median [q1, q3] (min–max) |
|---|---|---|---|---|
| 1 | 2 | AN、DMSO | 5.145 [5.125, 5.165] (5.105–5.184) | 6.770 [6.618, 6.921] (6.466–7.073) |
| 2 | 5 | DME、DOL、GBL、SL、SN | 4.929 [4.901, 5.134] (4.778–6.156) | 6.220 [6.178, 7.067] (4.927–8.061) |
| >=3 | 3 | DMC、EC、TMP | 4.321 [4.175, 4.328] (4.029–4.335) | 6.477 [6.316, 6.817] (6.155–7.157) |

### state_identity —— dication 态身份标签（c1_state_identity.csv）

| level | n | members | dIP median [q1, q3] (min–max) | dEA median [q1, q3] (min–max) |
|---|---|---|---|---|
| molecule_centered_redox | 6 | DMC、DME、EC、GBL、SL、TMP | 4.618 [4.324, 4.922] (4.029–5.134) | 6.348 [6.188, 6.920] (6.155–7.157) |
| no_intact_minimum_found | 4 | AN、DMSO、DOL、SN | 5.145 [5.023, 5.427] (4.778–6.156) | 6.770 [6.082, 7.320] (4.927–8.061) |

### role —— 角色 role

| level | n | members | dIP median [q1, q3] (min–max) | dEA median [q1, q3] (min–max) |
|---|---|---|---|---|
| additive | 2 | SN、TMP | 4.403 [4.216, 4.590] (4.029–4.778) | 5.702 [5.315, 6.089] (4.927–6.477) |
| co-solvent | 5 | AN、DMSO、DOL、GBL、SL | 5.105 [4.929, 5.184] (4.901–6.156) | 6.466 [6.220, 7.073] (6.178–8.061) |
| solvent | 3 | DMC、DME、EC | 4.335 [4.328, 4.735] (4.321–5.134) | 7.067 [6.611, 7.112] (6.155–7.157) |

### family —— 结构家族 family

| level | n | members | dIP median [q1, q3] (min–max) | dEA median [q1, q3] (min–max) |
|---|---|---|---|---|
| cyclic_carbonate | 1 | EC | 4.321 [4.321, 4.321] (4.321–4.321) | 6.155 [6.155, 6.155] (6.155–6.155) |
| ester | 1 | GBL | 4.901 [4.901, 4.901] (4.901–4.901) | 6.178 [6.178, 6.178] (6.178–6.178) |
| ether | 2 | DME、DOL | 5.645 [5.390, 5.900] (5.134–6.156) | 7.564 [7.316, 7.813] (7.067–8.061) |
| linear_carbonate | 1 | DMC | 4.335 [4.335, 4.335] (4.335–4.335) | 7.157 [7.157, 7.157] (7.157–7.157) |
| nitrile | 2 | AN、SN | 4.941 [4.859, 5.023] (4.778–5.105) | 6.000 [5.464, 6.537] (4.927–7.073) |
| phosphate | 1 | TMP | 4.029 [4.029, 4.029] (4.029–4.029) | 6.477 [6.477, 6.477] (6.477–6.477) |
| sulfone | 1 | SL | 4.929 [4.929, 4.929] (4.929–4.929) | 6.220 [6.220, 6.220] (6.220–6.220) |
| sulfoxide | 1 | DMSO | 5.184 [5.184, 5.184] (5.184–5.184) | 6.466 [6.466, 6.466] (6.466–6.466) |

### functionalization_tag —— functionalization tag（含该 tag 的子集）

| level | n | members | dIP median [q1, q3] (min–max) | dEA median [q1, q3] (min–max) |
|---|---|---|---|---|
| chelating | 2 | DME、SN | 4.956 [4.867, 5.045] (4.778–5.134) | 5.997 [5.462, 6.532] (4.927–7.067) |
| cyclic | 4 | DOL、EC、GBL、SL | 4.915 [4.756, 5.235] (4.321–6.156) | 6.199 [6.172, 6.680] (6.155–8.061) |
| linear | 6 | AN、DMC、DME、DMSO、SN、TMP | 4.941 [4.446, 5.127] (4.029–5.184) | 6.772 [6.469, 7.072] (4.927–7.157) |
| phosphorus_containing | 1 | TMP | 4.029 [4.029, 4.029] (4.029–4.029) | 6.477 [6.477, 6.477] (6.477–6.477) |
| sulfur_containing | 2 | DMSO、SL | 5.057 [4.993, 5.120] (4.929–5.184) | 6.343 [6.282, 6.405] (6.220–6.466) |

组内 n < 4 的层只报中位数与分布，不做推广（见 §8 not_estimable 清单）。

## 6. 秩相关（Spearman ρ + 精确置换 p）

做法：固定描述符、对位移做全排列（n=10 时共 3628800 种），统计 |ρ_perm| ≥ |ρ_obs| 的比例；这是精确置换 p，不是正态近似。descriptor 有并列时该做法条件于观测到的 x，仍然精确。

| 轴 | descriptor | 含义 | n | ρ | 精确 p |
|---|---|---|---|---|---|
| oxidation | donor_count | donor_count | 10 | -0.7942 | 0.0077 |
| reduction | donor_count | donor_count | 10 | -0.0586 | 0.8788 |
| oxidation | li_contacts_n | n_Li（主 motif Li 接触数） | 10 | 0.4264 | 0.2571 |
| reduction | li_contacts_n | n_Li（主 motif Li 接触数） | 10 | 0.0000 | 1.0000 |
| oxidation | heteroatom_count | heteroatom_count | 10 | -0.7015 | 0.0282 |
| reduction | heteroatom_count | heteroatom_count | 10 | -0.1377 | 0.7151 |
| oxidation | rotatable_bonds | rotatable_bonds（柔性） | 10 | -0.2547 | 0.4833 |
| reduction | rotatable_bonds | rotatable_bonds（柔性） | 10 | -0.1049 | 0.7833 |
| oxidation | tpsa | tpsa | 10 | -0.8903 | 0.0011 |
| reduction | tpsa | tpsa | 10 | -0.4573 | 0.1853 |
| oxidation | n_heavy | n_heavy | 10 | -0.6659 | 0.0394 |
| reduction | n_heavy | n_heavy | 10 | -0.3426 | 0.3387 |
| oxidation | mw | mw | 10 | -0.5636 | 0.0963 |
| reduction | mw | mw | 10 | -0.1636 | 0.6567 |

## 7. 组间对比（均值差的精确置换 p）

规则：两组各 n ≥ 4 才给精确置换 p；否则记 not_estimable。检验统计量是均值差，枚举全部 C(n, k) 种标签切分。

| 组 | A vs B | n_A | n_B | 轴 | 均值差 (eV) | 精确 p | 切分数 |
|---|---|---|---|---|---|---|---|
| denticity | 单齿 (n_Li=1) vs 双齿/多齿 (n_Li>=2) | 6 | 4 | oxidation | -0.6030 | 0.1238 | 210 |
| denticity | 单齿 (n_Li=1) vs 双齿/多齿 (n_Li>=2) | 6 | 4 | reduction | 0.0154 | 0.9762 | 210 |
| state_identity | molecule_centered_redox vs no_intact_minimum_found | 6 | 4 | oxidation | -0.6975 | 0.0714 | 210 |
| state_identity | molecule_centered_redox vs no_intact_minimum_found | 6 | 4 | reduction | -0.0895 | 0.8952 | 210 |
| functionalization_tag | cyclic vs linear | 4 | 6 | oxidation | 0.3156 | 0.4762 | 210 |
| functionalization_tag | cyclic vs linear | 4 | 6 | reduction | 0.1255 | 0.8429 | 210 |

其余 44 对（family / role / donor_count / donor_element 及部分 tag 组合）因两组中至少一组 n<4 记 not_estimable，不在此表列出，逐条见 §11。

## 8. 态身份维度（机制，不是数值）

来源：outputs/week5/c1_state_identity.csv · state_identity_label（dication 行）

no_intact_minimum_found 表示二价阳离子在该 motif 上找不到完整极小（几何/电子重排）；这是机制维度，不是数值维度。

- oxidation：molecule_centered_redox（n=6）− no_intact_minimum_found（n=4）均值差 = -0.6975 eV，精确置换 p = 0.0714（210 种切分）
- reduction：molecule_centered_redox（n=6）− no_intact_minimum_found（n=4）均值差 = -0.0895 eV，精确置换 p = 0.8952（210 种切分）

## 9. tag 覆盖与不可得项

- C1 子集内存在的 tag：chelating、cyclic、linear、phosphorus_containing、sulfur_containing
- core-18 有但 C1 子集没有的 tag：flexible、fluorinated、unsaturated
- not_available_in_repo：ESP
  - flexible / fluorinated / unsaturated 只出现在 core-18 中不在 C1 子集的分子上（TEGDME / FEC / VC），故在本子集内不可检验。
  - 柔性维度改用 rotatable_bonds 作为数值代理（见秩相关）。
  - chelation 用两个口径交叉：metadata 的 chelating tag（DME/SN）与主 motif 的实际 Li 接触数。

## 10. 第三配位壳（EC）上下文

- 分子 EC；引擎 GFN2-xTB；作业 14（仅 1 个分子，n=1，不能推广）
- 层级提醒：GFN2-xTB, not r2SCAN-3c: absolute values must never be placed next to the docs/18 ladder; only sign and monotonicity are comparable
- dd(2→1) 与 dd(3→2)，dIP：-1.882，-0.723；dEA：-0.619，-0.336
- 判语 consistent_with_saturation：符号在两个轴上都保持 = True / True，幅度收缩 = True / True

## 11. not_estimable / not_available_in_repo 清单

| 项 | n | 状态 | 原因 |
|---|---|---|---|
| donor_element = N | 2 | not_estimable | 组内 n<4，只报中位数/分布，不做推广 |
| donor_count = 1 | 2 | not_estimable | 组内 n<4，只报中位数/分布，不做推广 |
| donor_count = >=3 | 3 | not_estimable | 组内 n<4，只报中位数/分布，不做推广 |
| role = additive | 2 | not_estimable | 组内 n<4，只报中位数/分布，不做推广 |
| role = solvent | 3 | not_estimable | 组内 n<4，只报中位数/分布，不做推广 |
| family = cyclic_carbonate | 1 | not_estimable | 组内 n<4，只报中位数/分布，不做推广 |
| family = ester | 1 | not_estimable | 组内 n<4，只报中位数/分布，不做推广 |
| family = ether | 2 | not_estimable | 组内 n<4，只报中位数/分布，不做推广 |
| family = linear_carbonate | 1 | not_estimable | 组内 n<4，只报中位数/分布，不做推广 |
| family = nitrile | 2 | not_estimable | 组内 n<4，只报中位数/分布，不做推广 |
| family = phosphate | 1 | not_estimable | 组内 n<4，只报中位数/分布，不做推广 |
| family = sulfone | 1 | not_estimable | 组内 n<4，只报中位数/分布，不做推广 |
| family = sulfoxide | 1 | not_estimable | 组内 n<4，只报中位数/分布，不做推广 |
| functionalization_tag = chelating | 2 | not_estimable | 组内 n<4，只报中位数/分布，不做推广 |
| functionalization_tag = phosphorus_containing | 1 | not_estimable | 组内 n<4，只报中位数/分布，不做推广 |
| functionalization_tag = sulfur_containing | 2 | not_estimable | 组内 n<4，只报中位数/分布，不做推广 |
| ESP descriptor | n/a | not_available_in_repo | data/metadata/core_set.csv 与 outputs/ 内均无 ESP 字段 |

## 12. 诚实边界

C1 子集 n=10（小于 core-18）；任何相关或组间差异都只能是提示性证据，不得称显著；未作多重比较校正；ESP 字段仓库内不存在（not_available_in_repo）；本分析不改动任何既有判决。

- 这不是「配位诱导反转（robust inversion）」的发现：week9 ladder 上 f_robust_inv 在全部(台阶, 轴) 组合都为 0，§24 Figure 4/5 的 inversion 现象在本项目未被观测到。本图只刻画「配位位移有多大、和哪些标签同向」，不构成 inversion 机制证据。
- TMP 的 m2 与 DMC 的 m2 是非主 motif，未纳入；若改用它们会得到不同的逐分子值。
- tpsa / donor_count / heteroatom_count / n_heavy 在 C1 子集内彼此高度共线，单凭 ρ 无法区分是哪一个描述符在起作用；§24 点名的 ESP 是电子结构量，tpsa 只是几何/组成量，不能当作 ESP 的替代。
- 还原轴（dEA）上没有任何 |ρ| > 0.5 的描述符（最大 |ρ| = 0.457，p = 0.185），且 ladder 还原轴 f_unresolved_after = 0.8，说明配位后的还原轴排序本身大半不可分辨；「还原轴没有可读的标签关系」是数据边界，不是没做。

## 13. 图上每个数字的来源

| 元素 | 来源文件 · 字段 |
|---|---|
| d_ea_ev | outputs/week5/c1_coord_shifts.csv · d_ea_ev（is_primary=True） |
| d_ip_ev | outputs/week5/c1_coord_shifts.csv · d_ip_ev（is_primary=True） |
| descriptors | data/metadata/core_set.csv · donor_atoms/donor_count/heteroatom_count/rotatable_bonds/tpsa/n_heavy/mw/functionalization_tags/family/role |
| ladder | outputs/week9/stage10_ladder.json · ladder[C0_to_C1, native] |
| li_contacts | outputs/week5/c1_coord_shifts.csv · li_contacts |
| sd_anchor | outputs/week5/c1_summary.json · delta_ip_ev.mean/std |
| shell3 | outputs/week23/shell3_xtb_sign_test.json · increments / verdict |
| state_identity | outputs/week5/c1_state_identity.csv · state_identity_label |
| subset_n | outputs/week5/c1_li_coordination_summary.json · molecules / n_motifs |

