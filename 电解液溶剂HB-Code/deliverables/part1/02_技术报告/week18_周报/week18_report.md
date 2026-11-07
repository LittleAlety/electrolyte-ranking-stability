# Week 18 成果小结 —— Stage 19（几何弛豫检验：第二个 SCF 解能不能扛住弛豫）

## 0. 一页结论
- 做了什么：把 Week 17 找出的 **37 个 `moread_lower` 格子**（单点上两解不同、且 `moread` 更低的**全集**）里的两条 SCF 解各自做几何弛豫（**74 个 ORCA `Opt` 作业 = 37 格 x 2 臂**），再问一次：这还是两个不同的电子态吗？`moread` 还更低吗？唯一的自由变量是作业类型（`sp` -> `Opt`）与初猜；方法、溶剂、起始几何 G1 全部冻结。
- 关键数字：把两条腿各自放到自己的几何极小点之后：只有 **5/37** 格仍保持 `moread` 更低（`still_lower`）；**8/37** 格的两解在终点**合并为同一电子态**（单点身份差异被几何洗掉）；**24/37** 格仍是两个不同态、但偏好被几何反转，全阶段偏好反转 **32** 格。`|delta|` 中位从单点 **0.11983 eV** 塌到 **0.00196 eV**（缩小 61 倍），而带符号位移在 **37/37** 格为正 —— 这就是「身份差异多数是真的，但单点上的能量偏好多数是假象」的定量版本。
- 质检：核心 QC：74 个 `Opt` 作业 74 ok / 0 failed（37 格 x 2 臂）；两条腿起始几何先做审计、与冻结 G1 逐原子一致；阈值 0.039 与 Week 17 `stage18_identity_census.json` 的 `thresholds.charge_l1_primary` 逐位相同；四类裁决计数、按态 / 按分子 / 按 eps / 按臂分组表、以及五条量级中位数全部现算并写入 verification.json 的 checks。
- 限制：所有比例都**条件在 37 个 `moread_lower` 格子**上（Week 17 单点上两解不同且 moread 更低的全集），不是 414 格总体，也不能读成「默认解在 N% 的格子上安全」。判据 `charge_l1 > 0.039` 与材料阈值 1e-03 eV 冻结自 Stage 18、本阶段未重新拟合；几何同最小点宽容 0.02 A 只是描述列。两条腿的弛豫几何**没有一对逐位相同**，`rmsd_same_minimum` 的 6 格只是同一极小点附近的近似，不构成「同一个驻点」的证明；`Opt` 收敛判据是 ORCA 默认、未做频率复核，机械稳定性不在本阶段结论之内。裸 CPCM、G1 起始几何，以及「阴离子在 r2SCAN-3c 下不束缚」的方法适用域限制全部继承前几周。

本文可独立阅读；逐项细节、物理机制与需裁决项见同目录 `week18_report_full.md`。

## 1. 协议与规模
### 唯一的自由变量：作业类型与初猜

- **本周新增 74 个 ORCA `Opt` 作业 = 37 格 x 2 条腿**（reused 5 / computed 69）。
- 目标集合是 Week 17 单点上「两解不同、且 `moread` 更低」的 **37 格全集**（发现集 32 + 留出臂 5），不是 414 对总体。
- 每个格子把两条 SCF 解（`default` = ORCA 自己的初猜；`moread` = `! MORead` + `%moinp` 指向同电荷态的气相 gbw）各自从同一个冻结的 G1 几何出发，在各自 eps 下做几何优化；方法 `r2SCAN-3c`、溶剂 `bare CPCM at each cell's own epsilon`、起始几何全部冻结。
- **判据沿用 Stage 18 冻结阈值** `charge_l1 > 0.039`（本阶段未重新拟合）；材料阈值 1e-03 eV 定 `still_lower`；几何同最小点宽容 0.02 A **只是描述列**。
- 取块口径：`Opt` 输出里 Mulliken 块与 CARTESIAN 块都出现多次（首块是起始几何），本阶段一律取**最后一块**；实测块计数 Mulliken [1, 2]、CARTESIAN [9, 12, 13, 14, 15, 17, 18, 20, 21, 22, 25, 28, 29, 30, 31, 32, 48, 76, 80, 111]。

## 2. 裁决：37 个 moread_lower 格子
### 四类裁决

| 结局 | 计数 | 含义 |
| --- | --- | --- |
| `distinct_lower` | 5 | 终点仍是两个不同电子态，且 moread 仍更低 |
| `distinct_higher` | 24 | 仍是两个不同态，但弛豫后 moread 反而**更高**（偏好反转） |
| `same_lower` | 0 | 终点身份重合，moread 更低 |
| `same_higher` | 8 | 终点身份重合，moread 更高（身份差异被几何洗掉） |
| `incomplete` | 0 | 两条腿未齐备，不判 |

- 三条关键计数：`n_still_distinct` **29/37**、`n_still_lower` **5/37**、`n_preference_flipped` **32/37**。
- 唯一没有反转的 `distinct_lower` 格子（5 个）：EC cation eps=5、EC cation eps=7、EC cation eps=10、TEGDME anion eps=20、TEGDME anion eps=200 —— 5 个里 3 个是 EC 阳离子、2 个是 TEGDME 阴离子。

### 按电性状态

| 态 | 格数 | 完成 | distinct_lower | distinct_higher | same_lower | same_higher |
| --- | --- | --- | --- | --- | --- | --- |
| anion | 21 | 21 | 2 | 14 | 0 | 5 |
| cation | 16 | 16 | 3 | 10 | 0 | 3 |

### 按臂（发现集 / 留出臂）

| 臂 | 格数 | distinct_lower | distinct_higher | same_lower | same_higher |
| --- | --- | --- | --- | --- | --- |
| discovery | 32 | 3 | 21 | 0 | 8 |
| holdout | 5 | 2 | 3 | 0 | 0 |

### 按分子

| 分子 | 格数 | distinct_lower | distinct_higher | same_lower | same_higher |
| --- | --- | --- | --- | --- | --- |
| PC | 10 | 0 | 10 | 0 | 0 |
| TMP | 10 | 0 | 10 | 0 | 0 |
| EMC | 6 | 0 | 1 | 0 | 5 |
| EC | 5 | 3 | 0 | 0 | 2 |
| DEC | 3 | 0 | 3 | 0 | 0 |
| TEGDME | 2 | 2 | 0 | 0 | 0 |
| DMC | 1 | 0 | 0 | 0 | 1 |

### 按介电常数

| eps | 格数 | distinct_lower | distinct_higher | same_lower | same_higher |
| --- | --- | --- | --- | --- | --- |
| 5.0 | 6 | 1 | 3 | 0 | 2 |
| 7.0 | 3 | 1 | 2 | 0 | 0 |
| 10.0 | 3 | 1 | 2 | 0 | 0 |
| 14.0 | 3 | 0 | 2 | 0 | 1 |
| 20.0 | 6 | 1 | 4 | 0 | 1 |
| 28.0 | 2 | 0 | 2 | 0 | 0 |
| 40.0 | 3 | 0 | 2 | 0 | 1 |
| 80.0 | 3 | 0 | 2 | 0 | 1 |
| 200.0 | 5 | 1 | 3 | 0 | 1 |
| 1000.0 | 3 | 0 | 2 | 0 | 1 |

## 3. 幅度与几何
### 幅度：单点差异被几何压缩了两个数量级

- `|delta|` 单点中位 **0.11983 eV** -> 弛豫后中位 **0.00196 eV**：**缩小 61 倍**。
- 带符号的 `delta_shift_ev = relax - single` 在 **37/37** 格为正、**0/37** 格为负：弛豫把偏好一致地朝「moread 不再更低」的方向推，这就是 |delta| 收缩而偏好反转的机制。
- `|delta 改变|` 中位 **0.10411 eV** —— 与单点差异同量级，说明弛豫不是小扰动。
- 两臂各自的弛豫能量降中位：**default 1.8762 eV vs moread 1.6655 eV**；moread 降得更多的格子 **0/37**（default 在每个格子上都降得更多），这正是单点偏好被反转的能量学来源。

### 几何与身份通道

- 两条腿弛豫后的几何 RMSD 中位 **0.4716 A**；**6/37** 格落在 `rmsd_same_minimum`（<= 0.02 A，仅作描述），**0 格**的两条腿几何逐位相同 —— 没有一对收敛到同一个驻点。
- 身份通道：弛豫后 `charge_l1 > 0.039` 仍有 **29/37** 格、贴阈值（±20%）**0 格**（冻结阈值 `near_threshold` 只是描述列，判据不变）。

## 4. 产物与口径
| 文件 | 内容 |
| --- | --- |
| `stage19_relax.json` / `stage19_relax_plan.json` | 作业台账（37 格 x 2 臂 = 74 个 Opt 作业；method / job_type / 起始几何与 QC 摘要） |
| `stage19_relax_cells.csv` | 逐格逐臂原始读数（74 行：最后一块能量、<S^2>、收敛、Mulliken / CARTESIAN 块计数） |
| `stage19_relax_analysis.json` | 主结论全部聚合（threshold_charge_l1 / block_counts / cells / aggregates: all + by_state + by_molecule + by_epsilon + by_arm_set） |
| `stage19_relax_cells_analysis.csv` | 37 个 moread_lower 格子的逐格裁决表 |
| `stage19_relax_by_state.csv` / `_by_molecule.csv` / `_by_epsilon.csv` / `_by_arm_set.csv` | 四张分组汇总表 |
| `stage19_relax_summary.md` | 本周中文小结 |

## 5. 产物清单
- `artifacts/F36_stage19_relax_outcomes.png`
- `artifacts/F37_stage19_identity_geometry.png`
- `artifacts/figure_manifest_week18_stage19.md`
- `stage19_relax.json`
- `stage19_relax_analysis.json`
- `stage19_relax_by_arm_set.csv`
- `stage19_relax_by_epsilon.csv`
- `stage19_relax_by_molecule.csv`
- `stage19_relax_by_state.csv`
- `stage19_relax_cells.csv`
- `stage19_relax_cells_analysis.csv`
- `stage19_relax_plan.json`
- `stage19_relax_summary.md`
- `week18_report_full.md`

## 6. 源文件缺失
- 无（全部源路径均存在）
