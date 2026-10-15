# Week 16 成果小结 —— Stage 17（亚稳态污染上限与两个 SCF 解的电子结构身份）

## 0. 一页结论
- 做了什么：把 Week 9「五级台阶」第 2 级 `P1 -> P2` 的 P2 腿（SMD(乙腈) 层）从 ORCA 自带初猜换成 moread 初猜重算（18 分子 x 3 态 = 54 格，全部 ok、零复用），并只读既有 `.out` 对 32 个「漏解」配对格的两个 SCF 解做电子结构身份对照（<S^2> / 自旋中心 / 轨道标签 / 参与率 PR / Mulliken L1 差）。
- 关键数字：54 格上两臂的 tau_b / O_20% / f_unresolved / f_robust_inv 无一条被改写：oxidation tau_b 0.895 -> 0.922（Delta +0.0261）、reduction tau_b 0.673 -> 0.673（Delta +0.0000），两臂 tau_b 的 95% CI 在两条轴上都重叠；f_robust_inv 从 0 变非 0 在本项目这条具体流水线、这批格子、这套估计量下结构性不可能（**不是普适定理**）。Part B：32 格的两个 SCF 解都是自旋纯双重态（<S^2> 全落 0.75±0.01，32/32）；阴离子自旋中心两臂一致 16/16、阳离子仅 5/16。
- 质检：核心 QC：54/54 作业成功、零缺失参照、几何审计 18/18 逐位一致；四组 (轴, 臂) 的 n = 18、f_robust_inv 全为 0；32 格 <S^2> 全落 0.75±0.01、几何 QC 32/32 一致、census.unresolved 为空。逐项实测值见本目录 verification.json 的 checks。
- 限制：Part A 只在 native 18 分子的 SMD(乙腈) P2 层上做**单腿替换**，不是整条台阶重算；f_robust_inv ≡ 0 是估计量（z_primary = 1.0 + 两条 realization）的结构后果，不是物理结论——换 ddof、补第三条 realization 或抬高 z 都会改变它。Part B 只有 32 格 / 5 分子 / 2 个电荷态，判据 delta_ev < -1 meV 继承 Stage 16、本周未重标定；「主贡献轨道」是 reduced-orbital SPIN 子块里 |值| 最大的原子-轨道，在弥散基组下常落在弥散 s 通道，故「轨道标签相同 11/32」不能读成 pi* 身份相同。**TMP 的自旋近简并**：三个磷酸氧上的自旋几乎均摊，其「自旋中心翻转」（0/10）是近简并表观、不能当稳健判据。

本文可独立阅读；逐项细节、物理机制与需裁决项见同目录 `week16_report_full.md`。

## 1. 协议与规模
### 协议与规模

- **Part A（防守）**：把 Week 9「五级台阶」第 2 级 `P1 -> P2` 的 **P2 腿**（SMD(乙腈) 层）从 ORCA 自带初猜换成 `! MORead` + 气相 `%moinp` 重算；18 个分子 x 3 态 = **54 格**，`n_ok = 54`、`n_failed = 0`、`n_computed = 54`、`n_reused = 0`。
- 参照表：`outputs/week4/p2_core_set_smd_acetonitrile.csv`（default 臂，Week 4 冻结）；零格缺参照（`n_cells_without_reference = 0`）。
- 几何审计：18 个分子逐一比对参照的 xyz，全部 `all_identical = True`——这就是「单腿替换许可证」：被替换的只有初猜这一个变量。
- 调度：`--jobs 2 --nprocs 8`（本机 16 逻辑核），与既有各层协议相同。
- **Part B（机制）**：不新开任何量化作业，只读既有 `.out`，对 Stage 16 目录里 `delta_ev < -1 meV` 的 **32 个配对格**比较两条解的 `<S^2>`、自旋中心、轨道标签、参与率 PR 与 Mulliken 电荷 / 自旋的 L1 差。

## 2. Part A：污染上限（P1 -> P2 第 2 级的 P2 腿单腿替换）
### Part A 逐轴对照（published / default / moread）

| 轴 | 臂 | n | tau_b | tau_b 95% CI | O_20% | f_unresolved(after) | f_robust_inv | sigma 中位(eV) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 氧化轴 | **published** | 18 | 0.895 | [0.714, 1.000] | 0.750 | 0.111 | 0.000 | 0.198 |
| 氧化轴 | default | 18 | 0.895 | [0.714, 1.000] | 0.750 | 0.111 | 0.000 | 0.198 |
| 氧化轴 | moread | 18 | 0.922 | [0.774, 1.000] | 0.750 | 0.111 | 0.000 | 0.188 |
| 还原轴 | **published** | 18 | 0.673 | [0.403, 0.873] | 0.500 | 0.222 | 0.000 | 0.217 |
| 还原轴 | default | 18 | 0.673 | [0.403, 0.873] | 0.500 | 0.222 | 0.000 | 0.217 |
| 还原轴 | moread | 18 | 0.673 | [0.413, 0.871] | 0.500 | 0.255 | 0.000 | 0.226 |

> 来源：`stage17_contamination.json` 的 `published_comparison.<轴>.published`（published 行）与 `per_axis.<轴>.<臂>`（default / moread 行）；default 臂在逐项上**精确复原** published 值（`default_matches_published_max_abs_ev` = 0），所以 delta 只反映 moread 这一条腿。

**两臂 tau_b 的 95% CI 全部重叠**（污染被区间估计吸收）：

| 轴 | default 95% CI | moread 95% CI | 是否重叠 |
| --- | --- | --- | --- |
| 氧化轴 | [0.714, 1.000] | [0.774, 1.000] | 是 |
| 还原轴 | [0.403, 0.873] | [0.413, 0.871] | 是 |

- 产物判定：`any_published_conclusion_rewritten = False`、`tau_b_ci_overlap_both_axes = True`——**没有任何一条 published 结论被改写**。
- **结构性引理（一句话）**：在本周的估计量下（`sigma = abs(d0 - d1)/sqrt(2)`，`z_primary = 1.0`），两条 resolved 条件分别等价于 `(sqrt(2)-1)|d0| >= |d1|` 与 `(sqrt(2)-1)|d1| >= |d0|`；相乘要求 `1 <= (sqrt(2)-1)^2 = 0.1716`，矛盾——所以「反号且两臂都 resolved」的 pair 集合**恒为空集**，`f_robust_inv` 从 0 变非 0 在本项目这条具体流水线、这批格子、这套估计量下是结构性不可能（**不是普适定理**：换 `z`、换 `sigma` 的定义、或补进第三条 realization 都会解除），不是「本周恰好看不到」。

## 3. Part A：哪些格子被改变
### 被改变的格子（|delta| > 1 meV）

共 **6** 个格子：

| 分子 | 态 | delta (eV) | 所属轴 |
| --- | --- | --- | --- |
| TEGDME | anion | -0.156165 | reduction |
| TMP | cation | -0.134038 | oxidation |
| PC | anion | -0.118323 | reduction |
| EC | anion | +0.092274 | reduction |
| DEC | anion | -0.075211 | reduction |
| DEC | cation | +0.001381 | oxidation |

- 六个格里五个是 moread **更低**（`delta < 0`），只有 **EC / anion 是 +0.0923 eV**——moread 反而更高；这条正向残差原样保留。
- 54 格符号检验：正 **22** / 负 **32** / 零 **0**，双侧 p = **0.220328**——在符号层面不显著。
- 最坏 `|delta|` = 0.156165 eV（TEGDME/anion），最大正残差 = 0.092274 eV（EC/anion）。

## 4. Part B：两个 SCF 解的电子结构身份
### Part B：两个 SCF 解都是自旋纯双重态

- 受影响 **32** 格的两个解都是**自旋纯双重态**：两臂 `<S^2>` 全部落在 0.75±0.01，**32/32**；多重度逐格都是 2、电荷 -1 / +1。所以这**不是**破缺对称性 / 自旋污染伪影，而是同一自旋量子数下的两个不同 SCF 驻点。
- 差异的主轴是**电荷重组**而不只是自旋重排（`charge_l1` 与 `spin_l1` 量级相当）。

| 态 | 格子 | 自旋中心相同 | 轨道标签相同 |
| --- | --- | --- | --- |
| anion | 16 | 16/16 | 10/16 |
| cation | 16 | 5/16 | 1/16 |

- **空穴比电子更难安放**：阴离子的自旋中心在两臂**完全一致**（16/16），阳离子只有 **5/16**——默认初猜把多余电子放在哪里基本可复现，把空穴放在哪里高度依赖初猜。
- 几何 QC：两臂 `.out` 的 CARTESIAN COORDINATES 逐位相同的格子 **32/32**，所以上面的差异只能来自 SCF 解本身。

## 5. Part B：按分子家族
### Part B：按分子家族

| 家族 | 分子 | n_cells | loss_in_pr 均值 | charge_l1 均值 | 自旋中心相同 | 轨道标签相同 |
| --- | --- | --- | --- | --- | --- | --- |
| cyclic_carbonate | EC, PC | 15 | -0.5025 | 0.6689 | 15/15 | 10/15 |
| linear_carbonate | DMC, EMC | 7 | 0.4034 | 2.5862 | 6/7 | 1/7 |
| phosphate | TMP | 10 | -0.2215 | 0.3305 | 0/10 | 0/10 |

- 三族格数 15 + 7 + 10 = **32**。
- 家族分裂比电荷态更锋利：cyclic_carbonate 的 `loss_in_pr` 为负（moread 更定域）而 linear_carbonate 为正（moread 更离域），两条方向相反；linear 的 `charge_l1` 是 cyclic 的约 3.9 倍。
- phosphate（TMP）的自旋中心 0/10 全部翻转——这是**近简并表观、不能当判据**（见限制）。

## 6. 图表
- `artifacts/F32_stage17_contamination.png` —— Stage 17 Part A（污染上限）三面板。
- `artifacts/F33_stage17_solution_identity.png` —— Stage 17 Part B（两个 SCF 解的电子结构身份）四面板。
- 面板组成的权威说明：`artifacts/figure_manifest_week16_stage17.md`。

## 7. 产物与口径
### 本周产物

| 文件 | 说明 |
| --- | --- |
| `stage17_smd_moread.json` | Part A 运行台账：54 格计数、复用/新算、G1 几何审计、初猜协议原文 |
| `stage17_smd_moread_plan.json` | Part A 运行前的作业计划（18 分子 x 3 态） |
| `stage17_contamination.json` | Part A 全部分析（逐轴对照、delta_stats、符号检验、scenario verdict、CI 重叠） |
| `stage17_contamination_cells.csv` | Part A 逐分子表（P1 与两臂 P2 的原始能量、逐态 delta） |
| `stage17_contamination_ladder.csv` | Part A 四行 (臂, 轴) 指标表（含 published 列与 delta 列） |
| `stage17_contamination_summary.md` | Part A 的中文小结 |
| `stage17_solution_identity.json` | Part B 聚合产物（census / by_state / by_family / aggregates） |
| `stage17_solution_identity.csv` | Part B 逐格表（两臂 .out 路径、<S^2>、自旋中心、PR、L1、几何 QC） |
| `stage17_solution_identity_by_molecule.csv` | Part B 按 (分子, 态) 汇总表 |
| `stage17_solution_identity_summary.md` | Part B 的中文小结 |
| `p2_core_set_moread_smd_acetonitrile.csv` / `p2_summary_moread_smd_acetonitrile.json` | Part A 的原始能量表与逐层汇总（SMD(乙腈) moread 臂） |

## 8. 产物清单
- `artifacts/F32_stage17_contamination.png`
- `artifacts/F33_stage17_solution_identity.png`
- `artifacts/figure_manifest_week16_stage17.md`
- `p2_core_set_moread_smd_acetonitrile.csv`
- `p2_summary_moread_smd_acetonitrile.json`
- `stage17_contamination.json`
- `stage17_contamination_cells.csv`
- `stage17_contamination_ladder.csv`
- `stage17_contamination_summary.md`
- `stage17_smd_moread.json`
- `stage17_smd_moread_plan.json`
- `stage17_solution_identity.csv`
- `stage17_solution_identity.json`
- `stage17_solution_identity_by_molecule.csv`
- `stage17_solution_identity_summary.md`
- `week16_report_full.md`

## 9. 源文件缺失
- 无（全部源路径均存在）
