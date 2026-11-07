# Week 19 成果小结 —— Stage 20（第六级台阶与第二解的跨方法存亡）

## 0. 一页结论
- 做了什么：把 Week 18 留下的两个问题拆成互不依赖的两个 Part：Part 1 是**零新增计算**的台阶回填（把 37 格弛豫能量放回 Stage 10 五级台阶的同一把尺子上），Part 2 是 **74 个冻结 GFN2-xTB 作业**（37 格 x 2 臂）的跨方法检验。
- 关键数字：Part 1：弛豫修正几乎与 eps 无关（逐分子跨 eps 极差中位 **0.0263 eV**、最大 **0.215 eV**），但它不是纯平移 —— 还原支 mean/std/相对散布 **-1.953 / 0.160 / 0.08**，氧化支 **-0.610 / 0.315 / 0.52**。Part 2：同一几何上 xTB 单点与 ORCA r2SCAN-3c 的偏好方向一致 **33/37（89.2%）**，但 xTB 自己的弛豫把两臂能量差压掉约 **34 倍**（|Delta| 中位 0.0072 -> 0.00021 eV），**6/37** 格两臂干脆合并到同一极小点；逐格裁决与 Stage 19 只有 **17/37（45.9%）**一致，但那是**跨判据**的比较。
- 质检：核心 QC：Part 2 的 74 个 xTB 作业 74 ok / 0 failed；74 条腿的起始几何与 Stage 19 的弛豫终点逐字节相同；`charge_l1` 冻结阈值与 Stage 18 一致；四类裁决计数、两个一致率、交叉表、按态 / 按臂分解、以及四条量级中位数全部现算并写入 verification.json 的 checks；Part 1 的 30 行台阶表的 `rank_metrics` 必须逐行是 `omitted:`。
- 限制：所有比例都**条件在 37 个 `moread_lower` 格子**上（Week 17 单点上两解不同且 moread 更低的全集），不是 414 格总体。两个一致率**不可互换**：Stage 19 用冻结电子身份 `charge_l1 > 0.039`，Part 2 只有几何 `RMSD <= 0.02 A`。Part 2 的 xTB 作业是气相（无 CPCM），`epsilon` 只是起点几何的标签，`by_epsilon` **不是介电效应**。Part 1 的单点数目太少（氧化轴 3、还原轴 4），故不报任何秩相关；`rank_metrics` 的 `omitted:` 是结构性省略。`0.02 A` 与 `1e-03 eV` 是事前固定的描述性阈值，本阶段未做任何调参。

本文可独立阅读；逐项细节、物理机制与需裁决项见同目录 `week19_report_full.md`。

## 1. 协议与规模
### 两个 Part，两种作业量

- **Part 1：零新增计算。** 把 Week 18 落盘的 37 格弛豫能量按轴放回 Stage 10 五级台阶的同一把尺子上（`Delta_ox = -drop(cation)`、`Delta_red = -drop(anion)`），量出这条「第六级台阶」的 mean 与 std —— 因为 Stage 10 已经证明决定排序是否被改写的是位移的**离散度**而不是**大小**。
- **Part 2：74 个 GFN2-xTB 作业 = 37 格 x 2 臂**（reused 74 / computed 0），引擎 `xtb` 6.7.1pre（GFN2）。起点是 Stage 19 两条 r2SCAN-3c 弛豫终点，与 `outputs/week18` 的源几何逐字节相同。
- 两个 Part 的目标集合都是 Week 17 单点上「两解不同、且 `moread` 更低」的 **37 格全集**（发现集 32 + 留出臂 5），不是 414 对总体。
- **两把尺子必须分开读**：Stage 19 的 `distinct` 是冻结电子身份 `charge_l1 > 0.039`；Part 2 只有几何判据 `RMSD <= 0.02 A`（阈值事前固定）。所以「与 Stage 19 裁决的一致率」是**跨判据**的一致性，而「同一几何上的方法一致率」才是纯方法与方法的对照。
- Part 2 的 xTB 作业是**气相**（无 CPCM）；`epsilon` 只是「起点几何来自哪个 CPCM 格子」的标签，`by_epsilon` 分层**不构成介电效应**。
- Part 1 **不报** tau_b / Top-k / `f_unresolved`：本目录里每个分子只出现**一种态**（氧化轴 n=3、还原轴 n=4），这么少的点上的秩相关不构成统计推断，`rank_metrics` 列逐行写明 `omitted:` 原因。

## 2. Part 1：弛豫作为第六级台阶
### 弛豫不是「另一个环境」：它几乎与 eps 无关

- 37 格、7 个分子、10 个不同 eps。同一个 (分子, 态) 在它自己的各个 eps 上，Delta 的极差**中位 0.0263 eV、最大 0.215 eV（DEC）** —— 而同一批分子的 P1->P2 环境位移是 -2.17 ~ -2.46 eV（单格极值 -2.91 eV）。**弛豫修正与连续介质的介电常数几乎无关，是态内量。**

| 分子 | 态 | n_eps | Delta 最小 | Delta 最大 | 相对散布 |
| --- | --- | --- | --- | --- | --- |
| DEC | anion | 3 | -1.9725 | -1.7575 | 0.062 |
| DMC | cation | 1 | -0.3353 | -0.3353 | — |
| EC | cation | 5 | -0.2020 | -0.1910 | 0.022 |
| EMC | anion | 6 | -1.9653 | -1.9390 | 0.005 |
| PC | anion | 10 | -1.9296 | -1.8762 | 0.010 |
| TEGDME | anion | 2 | -2.4405 | -2.3764 | 0.019 |
| TMP | cation | 10 | -0.8501 | -0.8428 | 0.002 |

### 但它也不是「纯平移」：按态分成两支

| 态 | 格数 | mean | std | 相对散布 |
| --- | --- | --- | --- | --- |
| anion | 21 | -1.953 eV | 0.160 eV | 0.08 |
| cation | 16 | -0.610 eV | 0.315 eV | 0.52 |

还原支（anion）接近**刚性平移**（相对散布 0.08），氧化支（cation）是**散布型**（相对散布 0.52）。这也是这条新台阶在两条轴上意义不同的原因。

### 与五级台阶同口径并置（同一批分子）

| population | 台阶 | mean | std | 相对散布 |
| --- | --- | --- | --- | --- |
| ox_dmc_ec_tmp_eps5 | P1_to_P2 | -2.3461 | 0.3984 | 0.1698 |
| ox_carbonates_eps5 | P1_to_P2 | -2.5594 | 0.2108 | 0.0824 |
| red_dec_emc_pc_tegdme_eps20 | P1_to_P2 | -2.1649 | 0.5569 | 0.2572 |
| red_dec_emc_pc_eps5 | P1_to_P2 | -2.4279 | 0.2242 | 0.0923 |
| ox_dmc_ec_tmp_eps5 | P2sp_to_P2relax | -0.4625 | 0.3422 | 0.7400 |
| ox_carbonates_eps5 | P2sp_to_P2relax | -0.2686 | 0.0943 | 0.3509 |
| red_dec_emc_pc_tegdme_eps20 | P2sp_to_P2relax | -2.0096 | 0.2543 | 0.1265 |
| red_dec_emc_pc_eps5 | P2sp_to_P2relax | -1.9470 | 0.0226 | 0.0116 |

- 氧化 {DMC,EC,TMP}@eps=5：新台阶相对散布 **0.74**，而同一 population 的 P1->P2 只有 **0.17**；碳酸酯 {DMC,EC}@eps=5 为 **0.35** 对 **0.08**。
- 还原 {DEC,EMC,PC,TEGDME}@eps=20：新台阶 **0.13**，P1->P2 **0.26**；{DEC,EMC,PC}@eps=5 为 **0.01** 对 **0.09**。
- 唯一被标为**退化**的台阶是氧化轴的 G1->G2（|mean| 近似 0，相对散布无意义）——它在 (b) 面板里用斜纹柱画出，不参与任何比较。
- `rank_metrics` 在全部 30 行上都是 `omitted:`：这是**结构性省略**，不是计算没做。

## 3. Part 2：第二解在廉价势能面上的存亡
### 两个不同的问题，两个不同的答案

| 问题 | 判据 | 结果 |
| --- | --- | --- |
| 同一几何上「哪条腿更低」能否被廉价方法复现？ | 符号一致（材料阈值 1e-03 eV） | **33/37（89.2%）** |
| 廉价优化器能否独立把第二解找回来？ | 几何 RMSD <= 0.02 A | 两臂合并 **6/37** |
| 逐格裁决与 Stage 19 是否一致？ | 跨判据（电子身份 vs 几何） | **17/37（45.9%）** |

### 四类裁决（xTB 面上）

| 结局 | 计数 | 含义 |
| --- | --- | --- |
| `distinct_lower` | 15 | 几何上仍是两个极小点，且 moread 仍更低 |
| `distinct_higher` | 16 | 仍是两个极小点，但弛豫后 moread 反而更高 |
| `same_lower` | 0 | 两臂合并，且 moread 更低 |
| `same_higher` | 6 | 两臂合并，且 moread 更高 |
| `incomplete` | 0 | 两条腿未齐备，不判 |

- 关键计数：`n_xtb_same_minimum` **6/37**、`n_xtb_still_lower` **15/37**、`n_xtb_preference_flipped` **6/37**（仅单向计数：反方向「单点上 default 更低、弛豫后 moread 更低」同样存在，只是不在这个计数里）。

### 量级：廉价弛豫把两臂的能量差压掉约 34 倍

- |xTB 单点 Delta| 中位 **0.0072 eV** -> |xTB 弛豫 Delta| 中位 **0.00021 eV**（压掉约 33.6 倍）。
- 单臂几何漂移中位 **default 0.651 A / moread 0.657 A**，与起点双解 RMSD 中位 **0.4716 A** 同量级；弛豫后双解 RMSD 中位 **0.8078 A**（起点 0.4716 A）。
- 同一几何上的 4 个分歧格里有 3 个落在 ORCA 侧的 1 meV 材料带内（最大 0.00972 eV），即分歧集中在近简并处，不是方向性错误。

### Stage 19 裁决 x Stage 20 裁决

| Stage19 \ Stage20 | distinct_lower | distinct_higher | same_lower | same_higher |
| --- | --- | --- | --- | --- |
| distinct_lower | 1 | 4 | 0 | 0 |
| distinct_higher | 14 | 10 | 0 | 0 |
| same_lower | 0 | 0 | 0 | 0 |
| same_higher | 0 | 2 | 0 | 6 |

### 按态与按臂的分解

| 态 | 格数 | 完成 | distinct_lower | distinct_higher | same_lower | same_higher |
| --- | --- | --- | --- | --- | --- | --- |
| anion | 21 | 21 | 14 | 2 | 0 | 5 |
| cation | 16 | 16 | 1 | 14 | 0 | 1 |

| 臂 | 格数 | 完成 | distinct_lower | distinct_higher | same_lower | same_higher |
| --- | --- | --- | --- | --- | --- | --- |
| discovery | 32 | 32 | 12 | 14 | 0 | 6 |
| holdout | 5 | 5 | 3 | 2 | 0 | 0 |

- 阴离子侧同几何方法一致率 **100.0%**（21/21），阳离子侧 75.0%；发现集 87.5%，留出臂 100.0%。

## 4. 产物与口径
| 文件 | 内容 |
| --- | --- |
| `stage20_relax_rung.json` / `_cells.csv` / `_epsilon.csv` / `_ladder.csv` | Part 1 全部内容（37 格的弛豫位移、逐分子跨 eps 极差、30 行台阶表、按态 / 按分子 / 按臂 / 按 eps 聚合）；ladder 每一行的 `rank_metrics` 都写明 `omitted:` 原因 |
| `stage20_relax_rung_summary.md` | Part 1 的中文小结 |
| `stage20_xtb_arms.json` / `stage20_xtb_arms_plan.json` | Part 2 作业台账（37 格 x 2 臂 = 74 个 GFN2-xTB 作业；起始几何来自 Stage 19 的弛豫终点） |
| `stage20_xtb_arms_cells.csv` | Part 2 逐格逐臂原始读数（74 行） |
| `stage20_xtb_arms_analysis.json` | Part 2 主结论（cross-tab、同几何方法对照、aggregates: all + by_state + by_molecule + by_epsilon + by_arm_set） |
| `stage20_xtb_arms_cells_analysis.csv` / `_by_*.csv` | Part 2 逐格裁决表与四张分组汇总表 |
| `stage20_xtb_arms_summary.md` | Part 2 的中文小结 |

## 5. 产物清单
- `artifacts/F38_stage20_relax_rung.png`
- `artifacts/F39_stage20_xtb_arms.png`
- `artifacts/figure_manifest_week19_stage20.md`
- `stage20_relax_rung.json`
- `stage20_relax_rung_cells.csv`
- `stage20_relax_rung_epsilon.csv`
- `stage20_relax_rung_ladder.csv`
- `stage20_relax_rung_summary.md`
- `stage20_xtb_arms.json`
- `stage20_xtb_arms_analysis.json`
- `stage20_xtb_arms_by_arm_set.csv`
- `stage20_xtb_arms_by_epsilon.csv`
- `stage20_xtb_arms_by_molecule.csv`
- `stage20_xtb_arms_by_state.csv`
- `stage20_xtb_arms_cells.csv`
- `stage20_xtb_arms_cells_analysis.csv`
- `stage20_xtb_arms_plan.json`
- `stage20_xtb_arms_summary.md`
- `week19_report_full.md`

## 6. 源文件缺失
- 无（全部源路径均存在）
