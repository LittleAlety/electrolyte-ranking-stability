# Week 18 报告 —— Stage 19：第二个 SCF 解能不能扛住几何弛豫？

## 0. 一句话结论

条件在这 37 个 `moread_lower` 格子上（它们是“单点上两解不同、且 `moread` 更低”这一定义下的**全集**），把两条 SCF 解各自做几何弛豫后：

- 仍有 **5/37** 格保持 `moread` 更低（`still_lower`）：其中 5 格两解仍是不同电子态（`distinct_lower`）、0 格已在终点合并（`same_lower`）。
- **8/37** 格两解在终点**合并为同一电子态**（`same_lower` + `same_higher`）：单点上的身份差异被几何洗掉。
- **24/37** 格仍是两个不同电子态、但 `moread` 的偏好被几何反转（`distinct_higher`）；全阶段发生偏好反转的格子共 **32** 个。

判据沿用 Stage 18 冻结阈值 `charge_l1 > 0.039`，本阶段未重新拟合。

- 数值幅度：|Δ|单点 中位 0.11983 eV、|Δ|弛豫后 中位 0.00196 eV、|Δ改变| 中位 0.10411 eV（滚动求和算在 37 个完整格子上）。
- 几何：两条腿弛豫后的 RMSD 中位 0.4716 Å；6/37 格落在 `rmsd_same_minimum`（≤ 0.02 Å，仅作描述）；0 格的两条腿几何**逐位相同**。
- 判据与阈值全部冻结自上周：`charge_l1 > 0.039`（Stage 18，本阶段未重新拟合）；材料阈值 1e-03 eV；方法 r2SCAN-3c、裸 CPCM、起始几何 G1 全部冻结。

---

## 1. 为什么要有这一步（Stage 19 的动机）

Week 17（`docs/27_week17_report.md`）把全目录 1066 个 ORCA 输出扫了一遍，用冻结的电子身份量 `charge_l1` 在**同一个几何上**区分出两种自洽的 SCF 解：默认初猜与 `MORead` 会在 **37 格**（全部 414 对里）落到不同的电子态，且 `moread` 这一支能量更低。但 Week 17 的结论有一个坚硬的限制：它比较的是两条腿在**同一个装配几何上**的单点能量——那个几何本身并不是任何一支解的弛豫极小点。

因此下一步是唯一自然的：**把两条腿各自放到它们自己的几何极小点上，再问一次“这还是两个不同的电子态吗？还是 moread 还更低？”**。这是 Week 17 §10 列出的第一条候选（“本目录里 37 个 `moread_lower` 格子做几何优化”），也是“第二解是真实的另一个态”这一断言的**最后一块证据**。

## 2. 口径与记号

- **本周唯一的自由变量**：作业类型 `sp` → `Opt`，以及初猜（`default` vs `MORead`）。其余全部冻结：
  - 方法 `r2SCAN-3c`；
  - 溶剂 `bare CPCM at each cell's own epsilon (as in the P2 single points)`；
  - 起始几何 `outputs/week4/orca/<name>/<name>_<state>.xyz (G1, frozen since T1)`（本脚本先做几何审计，逐原子 1e-6 Å 一致）。
- **两条腿**：`default` = ORCA 自己的初猜；`moread` = `! MORead` + `%moinp` 指向同电荷态的气相 gbw。
  —— `! MORead + %moinp <gas-phase gbw of the same charge state>`。
- **配对能量** `delta_ev`：各自取自己 `.out` 的**最后一块**最终单点能（单位 eV，`HARTREE_TO_EV`）；本周有两套数：`single_point_delta_ev`（Stage 18 的单点，冻结）与 `relax_delta_ev`（本次弛豫后）。
- **位移** `delta_shift_ev = relax_delta_ev - single_point_delta_ev`：弛豫把偏好改了多少。
- **四类结论** `outcome`：
  - `distinct_lower`：终点仍判为不同电子态，且 `moread` 仍然更低；
  - `distinct_higher`：仍是不同态，但弛豫后 `moread` 反而**更高**（偏好反转）；
  - `same_lower` / `same_higher`：终点电子身份重合（单点差异被几何洗掉），再分依据能量高低；
  - `incomplete`：两条腿尚未齐备，不判。
- **电子身份量**（沿用 Stage 17/18 的同一个读取器）：
  - `charge_l1` = 两腿 Mulliken 原子电荷分布的 L1 距离（e）——**判据**；
  - `spin_l1` = 两腿 Mulliken 原子自旋分布的 L1 距离；
  - `delta_s2 = <S**2>_moread - <S**2>_default`，参考纯二重态 0.75；
  - `loss_in_pr = PR_moread - PR_default`，参与数（participation ratio）变化，正表示第二解更弥散。
- **取最后一块的口径**：`Opt` 输出里 `MULLIKEN ATOMIC CHARGES AND SPIN POPULATIONS` 与 `CARTESIAN COORDINATES (ANGSTROEM)` 都出现多次，**首块是起始几何**；本阶段一律取**最后一块**，CSV/JSON 里的 `n_mulliken_blocks_*` / `n_cartesian_blocks_*` 是这条口径的审计列（本次实测：Mulliken [1,2] 块、CARTESIAN [9,12,13,14,15,17,18,20,21,22,25,28,29,30,31,32,48,76,80,111] 块）。
- **几何同最小点宽容** `0.02 Å` 只是**描述列**，判据仍是冻结的电子身份阈值 `charge_l1 > 0.039`。
- **材料阈值** `1e-03 eV`：`still_lower` ⇔ `relax_delta_ev < -1e-03`。

---

## 3. 本周新增的计算

**74 个 `Opt` 作业 = 37 格 × 2 条腿。** 每个 `moread_lower` 格子把两条 SCF 解各自从同一个冻结的 G1 几何出发，在各自的 epsilon 下做几何优化；方法、溶剂、起始几何全部冻结，唯一变化的是**作业类型（`sp` → `Opt`）与初猜**。

| 项 | 值 | 来源 |
|---|---|---|
| 目标格子数 | 37 | `stage19_relax_plan.json` → `n_target_cells` |
| 作业数 | 74 | `stage19_relax_plan.json` → `n_jobs` |
| 作业类型 | `opt` | `stage19_relax_plan.json` → `job_type` |
| 方法 | `r2SCAN-3c` | `stage19_relax_plan.json` → `method` |
| 环境 | bare CPCM at each cell's own epsilon (as in the P2 single points) | `stage19_relax_plan.json` → `environment` |
| 起始几何 | `outputs/week4/orca/<name>/<name>_<state>.xyz (G1, frozen since T1)` | `stage19_relax_plan.json` → `start_geometry` |
| 两条腿 | `default` / `moread` | `stage19_relax_plan.json` → `arms` |

### 3.1 几何审计（起点必须是 G1，不重优化）

| 分子/态 | 对比格数 | 逐原子一致 |
|---|---|---|
| DEC/anion | 3 | 是 |
| DMC/cation | 1 | 是 |
| EC/cation | 5 | 是 |
| EMC/anion | 6 | 是 |
| PC/anion | 10 | 是 |
| TEGDME/anion | 2 | 是 |
| TMP/cation | 10 | 是 |

合计对比 **37** 格，全部逐原子一致（`stage19_relax_plan.json` → `geometry_audit`）。这意味着下面看到的任何变化都不可能来自起点不同。

### 3.2 作业台账

- 台账行数：**74**（`stage19_relax_cells.csv`）——到本报告定稿时已登记 **74 个 ok**、0 个 failed（重用 0）。
- 单作业壁钟中位：**603.9 s**（4 nprocs）。
- 目标总量 74，完成 74。

---

## 4. 逐格裁决

### 4.1 四类结论的总数

| 结论 | 格数 | 含义 |
|---|---|---|
| `distinct_lower` | 5 | 终点仍不同态，moread 仍更低 |
| `distinct_higher` | 24 | 终点仍不同态，但 moread 反而更高（偏好反转） |
| `same_lower` | 0 | 终点身份重合，moread 仅作为数值更低 |
| `same_higher` | 8 | 终点身份重合且更高 |
| `incomplete` | 0 | 两腿未齐备，不判 |

来源：`stage19_relax_analysis.json` → `aggregates.all.all.outcomes`。已完成 37 格；其中仍判不同态 **29**、已重合 **8**、偏好反转 **24**。

### 4.2 逐格表

| 分子 | 态 | eps | 子集 | 单点 Δ(eV) | 弛豫后 Δ(eV) | Δ改变(eV) | charge_l1(弛豫) | 双解 RMSD(Å) | 几何逐位相同 | 结论 |
|---|---|---|---|---|---|---|---|---|---|---|
| DEC | anion | 5 | holdout | -0.11983 | 0.02001 | 0.13985 | 0.209176 | 0.3010 | 否 | `distinct_higher` |
| DEC | anion | 20 | holdout | -0.05858 | 0.02371 | 0.08229 | 0.195424 | 0.3157 | 否 | `distinct_higher` |
| DEC | anion | 200 | holdout | -0.06411 | 0.02484 | 0.08894 | 0.191340 | 0.3217 | 否 | `distinct_higher` |
| DMC | cation | 5 | discovery | -0.00165 | -0.00004 | 0.00162 | 0.000726 | 0.0031 | 否 | `same_higher` |
| EC | cation | 5 | discovery | -0.01741 | -0.00972 | 0.00769 | 0.113793 | 0.1003 | 否 | `distinct_lower` |
| EC | cation | 7 | discovery | -0.00965 | -0.00398 | 0.00567 | 0.077626 | 0.0790 | 否 | `distinct_lower` |
| EC | cation | 10 | discovery | -0.00511 | -0.00110 | 0.00401 | 0.050570 | 0.0666 | 否 | `distinct_lower` |
| EC | cation | 14 | discovery | -0.00280 | -0.00021 | 0.00259 | 0.018901 | 0.0402 | 否 | `same_higher` |
| EC | cation | 20 | discovery | -0.00149 | 0.00004 | 0.00153 | 0.006971 | 0.0205 | 否 | `same_higher` |
| EMC | anion | 5 | discovery | -0.13698 | 0.00000 | 0.13698 | 0.000001 | 0.0000 | 否 | `same_higher` |
| EMC | anion | 20 | discovery | -0.24199 | 0.02402 | 0.26601 | 0.187827 | 0.3069 | 否 | `distinct_higher` |
| EMC | anion | 40 | discovery | -0.26363 | 0.00000 | 0.26363 | 0.000002 | 0.0000 | 否 | `same_higher` |
| EMC | anion | 80 | discovery | -0.27509 | 0.00000 | 0.27509 | 0.000003 | 0.0000 | 否 | `same_higher` |
| EMC | anion | 200 | discovery | -0.28214 | -0.00000 | 0.28214 | 0.000000 | 0.0000 | 否 | `same_higher` |
| EMC | anion | 1000 | discovery | -0.28596 | -0.00000 | 0.28596 | 0.000001 | 0.0000 | 否 | `same_higher` |
| PC | anion | 5 | discovery | -0.07943 | 0.00653 | 0.08596 | 0.081568 | 0.4766 | 否 | `distinct_higher` |
| PC | anion | 7 | discovery | -0.08627 | 0.00718 | 0.09345 | 0.083916 | 0.4741 | 否 | `distinct_higher` |
| PC | anion | 10 | discovery | -0.09044 | 0.00765 | 0.09809 | 0.084656 | 0.4724 | 否 | `distinct_higher` |
| PC | anion | 14 | discovery | -0.09257 | 0.00796 | 0.10053 | 0.086549 | 0.4721 | 否 | `distinct_higher` |
| PC | anion | 20 | discovery | -0.09380 | 0.00819 | 0.10199 | 0.087423 | 0.4723 | 否 | `distinct_higher` |
| PC | anion | 28 | discovery | -0.09445 | 0.00833 | 0.10279 | 0.088152 | 0.4716 | 否 | `distinct_higher` |
| PC | anion | 40 | discovery | -0.09486 | 0.00845 | 0.10331 | 0.089019 | 0.4720 | 否 | `distinct_higher` |
| PC | anion | 80 | discovery | -0.09525 | 0.00859 | 0.10384 | 0.089959 | 0.4708 | 否 | `distinct_higher` |
| PC | anion | 200 | discovery | -0.09545 | 0.00867 | 0.10411 | 0.090530 | 0.4706 | 否 | `distinct_higher` |
| PC | anion | 1000 | discovery | -0.09554 | 0.00871 | 0.10424 | 0.090841 | 0.4705 | 否 | `distinct_higher` |
| TEGDME | anion | 20 | holdout | -0.12052 | -0.06561 | 0.05490 | 2.184831 | 2.2142 | 否 | `distinct_lower` |
| TEGDME | anion | 200 | holdout | -0.14259 | -0.12994 | 0.01266 | 3.281649 | 3.8527 | 否 | `distinct_lower` |
| TMP | cation | 5 | discovery | -0.15225 | 0.00196 | 0.15421 | 0.363306 | 0.7125 | 否 | `distinct_higher` |
| TMP | cation | 7 | discovery | -0.14710 | 0.00145 | 0.14855 | 0.373899 | 0.7300 | 否 | `distinct_higher` |
| TMP | cation | 10 | discovery | -0.14308 | 0.00171 | 0.14479 | 0.389155 | 0.7436 | 否 | `distinct_higher` |
| TMP | cation | 14 | discovery | -0.14036 | 0.00151 | 0.14187 | 0.395850 | 0.7511 | 否 | `distinct_higher` |
| TMP | cation | 20 | discovery | -0.13830 | 0.00137 | 0.13966 | 0.401384 | 0.7556 | 否 | `distinct_higher` |
| TMP | cation | 28 | discovery | -0.13691 | 0.00127 | 0.13818 | 0.406808 | 0.7586 | 否 | `distinct_higher` |
| TMP | cation | 40 | discovery | -0.13587 | 0.00119 | 0.13706 | 0.410683 | 0.7606 | 否 | `distinct_higher` |
| TMP | cation | 80 | discovery | -0.13464 | -0.00026 | 0.13438 | 0.405218 | 0.7624 | 否 | `distinct_higher` |
| TMP | cation | 200 | discovery | -0.13390 | 0.00107 | 0.13497 | 0.418904 | 0.7647 | 否 | `distinct_higher` |
| TMP | cation | 1000 | discovery | -0.13351 | 0.00104 | 0.13455 | 0.420528 | 0.7653 | 否 | `distinct_higher` |

来源：`stage19_relax_cells_analysis.csv`（37 行）逐格逐列。单点 Δ 列与上周发布的 `stage18_identity_census.csv` 逐格一致（本报告的 `_guard()` 会逐格断言）。

### 4.3 分层

**按电子态**

| 组 | n | 完整 | 仍不同 | 仍更低 | 偏好反转 | RMSD同极小点 | 单点Δ绝对值 p50 | 弛豫Δ绝对值 p50 | Δ改变绝对值 p50 |
|---|---|---|---|---|---|---|---|---|---|
| anion | 21 | 21 | 16 | 2 | 19 | 5 | 0.09545 | 0.00833 | 0.10331 |
| cation | 16 | 16 | 13 | 3 | 13 | 1 | 0.13427 | 0.00123 | 0.13476 |

**按分子**

| 组 | n | 完整 | 仍不同 | 仍更低 | 偏好反转 | RMSD同极小点 | 单点Δ绝对值 p50 | 弛豫Δ绝对值 p50 | Δ改变绝对值 p50 |
|---|---|---|---|---|---|---|---|---|---|
| DEC | 3 | 3 | 3 | 0 | 3 | 0 | 0.06411 | 0.02371 | 0.08894 |
| DMC | 1 | 1 | 0 | 0 | 1 | 1 | 0.00165 | 0.00004 | 0.00162 |
| EC | 5 | 5 | 3 | 3 | 2 | 0 | 0.00511 | 0.00110 | 0.00401 |
| EMC | 6 | 6 | 1 | 0 | 6 | 5 | 0.26936 | 0.00000 | 0.27055 |
| PC | 10 | 10 | 10 | 0 | 10 | 0 | 0.09413 | 0.00826 | 0.10239 |
| TEGDME | 2 | 2 | 2 | 2 | 0 | 0 | 0.13156 | 0.09778 | 0.03378 |
| TMP | 10 | 10 | 10 | 0 | 10 | 0 | 0.13760 | 0.00132 | 0.13892 |

**按介电常数**

| 组 | n | 完整 | 仍不同 | 仍更低 | 偏好反转 | RMSD同极小点 | 单点Δ绝对值 p50 | 弛豫Δ绝对值 p50 | Δ改变绝对值 p50 |
|---|---|---|---|---|---|---|---|---|---|
| 10.0 | 3 | 3 | 3 | 1 | 2 | 0 | 0.09044 | 0.00171 | 0.09809 |
| 1000.0 | 3 | 3 | 2 | 0 | 3 | 1 | 0.13351 | 0.00104 | 0.13455 |
| 14.0 | 3 | 3 | 2 | 0 | 3 | 0 | 0.09257 | 0.00151 | 0.10053 |
| 20.0 | 6 | 6 | 5 | 1 | 5 | 0 | 0.10716 | 0.01595 | 0.09214 |
| 200.0 | 5 | 5 | 4 | 1 | 4 | 1 | 0.13390 | 0.00867 | 0.10411 |
| 28.0 | 2 | 2 | 2 | 0 | 2 | 0 | 0.11568 | 0.00480 | 0.12048 |
| 40.0 | 3 | 3 | 2 | 0 | 3 | 1 | 0.13587 | 0.00119 | 0.13706 |
| 5.0 | 6 | 6 | 4 | 1 | 5 | 2 | 0.09963 | 0.00425 | 0.11147 |
| 7.0 | 3 | 3 | 3 | 1 | 2 | 0 | 0.08627 | 0.00398 | 0.09345 |
| 80.0 | 3 | 3 | 2 | 0 | 3 | 1 | 0.13464 | 0.00026 | 0.13438 |

**按发现/留出臂**

| 组 | n | 完整 | 仍不同 | 仍更低 | 偏好反转 | RMSD同极小点 | 单点Δ绝对值 p50 | 弛豫Δ绝对值 p50 | Δ改变绝对值 p50 |
|---|---|---|---|---|---|---|---|---|---|
| discovery | 32 | 32 | 24 | 3 | 29 | 6 | 0.11452 | 0.00148 | 0.11931 |
| holdout | 5 | 5 | 5 | 2 | 3 | 0 | 0.11983 | 0.02484 | 0.08229 |

来源：`stage19_relax_analysis.json` → `aggregates.by_state` / `by_molecule` / `by_epsilon` / `by_arm_set`（与同名 CSV 一一对应）。

### 4.4 量级对比与机制

| 量 | 中位 p50 (eV) |
|---|---|
| |Δ|单点 | 0.11983 |
| |Δ|弛豫后 | 0.00196 |
| |Δ改变| | 0.10411 |
| default 腿弛豫能量降 | 1.8762 |
| moread 腿弛豫能量降 | 1.6655 |

来源：`aggregates.all.all` 的 `abs_single_point_delta_ev` / `abs_relax_delta_ev` / `abs_delta_shift_ev` / `energy_drop_default_ev` / `energy_drop_moread_ev`。弛豫把两解的能量差缩小了 **61 倍**（0.11983 → 0.00196 eV），而改变量本身（p50 0.10411 eV）与台阶位移同量级。

### 4.5 两解合并的 8 格构成

| 分子/态 | 格数 | eps |
|---|---|---|
| DMC/cation | 1 | 5 |
| EC/cation | 2 | 14、20 |
| EMC/anion | 5 | 5、40、80、200、1000 |

来源：`stage19_relax_cells_analysis.csv` 的 `name` / `state` / `epsilon` 列（只取 `same_*`）。其中 **5 格**的 `relax_charge_l1 < 1e-3` 且双解几何 RMSD < 1e-4 Å：两条腿收敛到**逐位相同**的极小点，单点上的差异纯属 SCF 分支假象。

### 4.6 `distinct_lower` 的 5 个幸存者

| 分子 | 态 | eps | 单点 Δ(eV) | 弛豫后 Δ(eV) | charge_l1(弛豫) | 两腿 Opt 均收敛 |
|---|---|---|---|---|---|---|
| EC | cation | 5 | -0.01741 | -0.00972 | 0.113793 | 是 |
| EC | cation | 7 | -0.00965 | -0.00398 | 0.077626 | 是 |
| EC | cation | 10 | -0.00511 | -0.00110 | 0.050570 | 是 |
| TEGDME | anion | 20 | -0.12052 | -0.06561 | 2.184831 | 是 |
| TEGDME | anion | 200 | -0.14259 | -0.12994 | 3.281649 | 否 |

来源：`stage19_relax_cells_analysis.csv`（`outcome = distinct_lower`）。

### 4.7 收敛性审计

| 分子/态 | eps | 腿 | 优化循环数 | Opt 收敛 | 正常结束 |
|---|---|---|---|---|---|
| TEGDME/anion | 200 | `default` | 111 | 否 | 是 |

来源：`stage19_relax_cells_analysis.csv` 的 `n_cycles_*` / `opt_converged_*` / `normal_termination_*` 列。**共 1/74 条腿触及迭代上限而未收敛**（作业 `status = ok`、正常结束，只是几何尚未满足收敛判据）；依赖这些腿的结论需按 §9 的说明谨慎读。

---

## 5. 身份与几何的联合读数

| 类别 | 格数 | 双解 RMSD ≤ 0.02 Å | 几何逐位相同 |
|---|---|---|---|
| `distinct_*`（仍不同态） | 29 | 0 | 0 |
| `same_*`（已重合） | 8 | 6 | 0 |
| 全部完整格子 | 37 | 6 | 0 |

来源：`stage19_relax_cells_analysis.csv` 的 `outcome` / `rmsd_same_minimum` / `geometry_identical_raw` 列。

**贴阈值的格子（`near_threshold`）**：以冻结切点 0.039 的 ±20% 为界（即 |`charge_l1_margin`| ≤ 0.0078），0/37 个完整格子落在带内。
—— 本次**没有格子贴阈值**：`charge_l1_margin` min -0.039000 / p50 0.051530 / max 3.242649，离切点最近的一格是 EC/cation/eps=10（|margin| = 0.0116）。

- `relax_charge_l1`（弛豫后）：min 0.000000 / p50 0.090530 / max 3.281649；阈值 0.039。
- 几何弛豫收获（单点→弛豫后能量下降）：default 中位 1.8762 eV、moread 中位 1.6655 eV。
- 位移方向：37 格的 `delta_shift_ev > 0`（弛豫把 moread 往上推），0 格往下。
- 被几何洗掉的 8 格：DMC/cation/eps=5、EC/cation/eps=14、EC/cation/eps=20、EMC/anion/eps=5、EMC/anion/eps=40、EMC/anion/eps=80、EMC/anion/eps=200、EMC/anion/eps=1000。
- 发生偏好反转的 32 格：DEC/anion/eps=5、DEC/anion/eps=20、DEC/anion/eps=200、DMC/cation/eps=5、EC/cation/eps=14、EC/cation/eps=20、EMC/anion/eps=5、EMC/anion/eps=20、EMC/anion/eps=40、EMC/anion/eps=80、EMC/anion/eps=200、EMC/anion/eps=1000、PC/anion/eps=5、PC/anion/eps=7、PC/anion/eps=10、PC/anion/eps=14、PC/anion/eps=20、PC/anion/eps=28、PC/anion/eps=40、PC/anion/eps=80、PC/anion/eps=200、PC/anion/eps=1000、TMP/cation/eps=5、TMP/cation/eps=7、TMP/cation/eps=10、TMP/cation/eps=14、TMP/cation/eps=20、TMP/cation/eps=28、TMP/cation/eps=40、TMP/cation/eps=80、TMP/cation/eps=200、TMP/cation/eps=1000（单点 moread 更低，弛豫后反而更高）。

**仍判不同态的 29 格在三个参考通道上的交叉一致性：**

| 通道 | 最小 | 中位 | 最大 |
|---|---|---|---|
| `relax_spin_l1` | 0.078142 | 0.123723 | 3.584638 |
| `relax_delta_s2` | -0.001204 | -0.000008 | 0.000057 |
| `relax_loss_in_pr` | -1.5301 | 0.0614 | 0.6063 |

来源：`stage19_relax_cells_analysis.csv` 的 `relax_spin_l1` / `relax_delta_s2` / `relax_loss_in_pr` 列（只对完整且仍不同态的格子）。

---

## 6. 物理读法

1. **弛豫并没有把第二解一律抹平或一律保留。** 在 37 个完整格子里，29 格终点仍判为两个不同的电子态，8 格终点身份重合。这两种结果都是物理信号：前者说明“同一个几何上两个自洽解”是**真的电子结构双稳**，后者说明那些“第二解”不过是**未弛豫几何上的分支幻象**。
2. **偏好反转（32 格）是对“用单点能量定排序”最直接的警告**：在这些格子上，单点上的 moread 优势（中位 0.11983 eV）小于几何弛豫带来的能量收获，所以它被几何反向超越。
3. **几何与电子身份是两件事。** 6 格的两条腿落在同一个极小点（RMSD ≤ 0.02 Å），但它们都在终点合并为同一电子态（单点差异纯属 SCF 分支）。
4. **身份差异不只在电荷上。** 在仍判不同态的 29 格里，29 格的自旋分布 L1 距离也超过同一个阈值——两个解不只是电荷重排，自旋（单电子轨道的定位）也不同。
5. **本周没有重算任何台阶。** 这 37 格不在五级台阶的主链上，它们只回答“第二解是不是真的”这一个断言，不改变 `docs/26` / `docs/27` 的台阶结论。
6. **机制：默认分支在弛豫中降得更多。** default 腿的弛豫能量降 p50 1.8762 eV 大于 moread 腿的 1.6655 eV；单点上 moread 的微小优势（p50 |Δ| 0.11983 eV）来自默认初猜在那个**冻结几何**上落进了一个略高的 SCF 解。一旦两条腿都允许几何弛豫，默认分支有更多下行空间，于是反超（32/37 格发生偏好反转）。
7. **留出臂方向一致。** `by_arm_set.holdout` 的 5 格里 **5 格仍判不同态**、2 格仍更低；发现集（32 格）为 24 格仍不同态、3 格仍更低。两臂方向一致，说明这不是发现集特有的过拟合。
8. **按介电常数没有单调趋势。** `by_epsilon` 各组的结局混杂（见 §4.3），本报告不主张任何 eps 趋势。


**两个样例（数字直接读自 JSON，不作外推）—— 两种结局都真实存在：**
- **EC/cation/eps=5**（`distinct_lower`，仍然不同态且 moread 仍更低）：单点 Δ = -0.0174 eV → 弛豫后 -0.0097 eV，位移 0.0077 eV；`charge_l1` 0.153 → 0.114（阈值 0.039）；两腿弛豫能量降：default 0.202 eV、moread 0.194 eV；双解几何 RMSD 0.100 Å。
- **DEC/anion/eps=5**（`distinct_higher`，仍然不同态但 moread 反而更高）：单点 Δ = -0.1198 eV → 弛豫后 0.0200 eV，位移 0.1398 eV；`charge_l1` 2.917 → 0.209（阈值 0.039）；两腿弛豫能量降：default 1.972 eV、moread 1.833 eV；双解几何 RMSD 0.301 Å。

---

## 7. 读法纪律（延续 Week 9 §10 / 10 §11 / 11 §11 / 12 §10 / 13 §11 / 14 §9 / 15 §8 / 16 §7 / 17 §7）

1. **比例只作条件陈述**：这 37 格是“单点上两解不同、且 `moread` 更低”这一定义下的**全集**，所以“条件在单点出现亚稳态时，弛豫后还保不保得住”是一个定义良好的条件概率，样本就是这 37 格——本报告一律以**分母为 37** 的条件比例报告它（具体分子见 §0）。但**不可以**把它当成 414 格总体的发生率，也不据此重算 τ_b / Top-k 之类的排序统计（选择偏差会把它们带偏）；也不要反过来宣称“默认解在 91% 的格子上是安全的”——那是 377/414 的覆盖率，不是本周测的量。
2. **`rmsd_same_minimum`（双解几何 RMSD ≤ 0.02 Å）只是描述列**：判据是冻结的电子身份阈值 `charge_l1 > 0.039`，不是几何 RMSD。
3. **`Opt` 输出里取最后一块**：`MULLIKEN ATOMIC ...` 与 `CARTESIAN ...` 各出现多次，**首块是起始几何**；`s17` 的取首块解析器只对单点输出成立。`n_mulliken_blocks_*` / `n_cartesian_blocks_*` 就是这条口径的审计列。
4. **未完成格子（`incomplete`）不计入任何比例与均值**。
5. **本阶段不重新拟合任何阈值**：`charge_l1 > 0.039`、1e-03 eV、0.02 Å 全部沿自上一步（Stage 18/15）。
6. **`near_threshold`（|`charge_l1_margin`| ≤ 20% × 0.039 = 0.0078）与 `rmsd_same_minimum` 一样只是描述列**：判据始终是冻结的 `charge_l1 > 0.039`，不因它变更。

---

## 8. 产物与图表

| 产物 | 说明 |
|---|---|
| `outputs/week18/stage19_relax_analysis.json` | 逐格裁决、聚合、阈值（本报告的主数据源） |
| `outputs/week18/stage19_relax_summary.md` | 同一份内容的 Markdown 摘要 |
| `outputs/week18/stage19_relax_cells_analysis.csv` | 逐格 × 55 列的计算明细 |
| `outputs/week18/stage19_relax_cells.csv` | 作业级台账（每行 = 1 个 Opt 作业） |
| `outputs/week18/stage19_relax_plan.json` | 本周的提交计划（37 格 / 74 作业 / 几何审计） |
| `outputs/week18/stage19_relax.json` | 运行器逐层摘要 |
| `outputs/week18/stage19_relax_by_state.csv` | 按电子态分层 |
| `outputs/week18/stage19_relax_by_molecule.csv` | 按分子分层 |
| `outputs/week18/stage19_relax_by_epsilon.csv` | 按介电常数分层 |
| `outputs/week18/stage19_relax_by_arm_set.csv` | 按发现/留出臂分层 |

| 脚本 | 说明 |
|---|---|
| `scripts/run_stage19_relax.py` | 本周 74 个 `Opt` 作业的提交器 |
| `scripts/analyze_stage19_relax.py` | 逐格裁决与聚合的生成器 |
| `scripts/gen_week18_report.py` | 本报告生成器 |

两张图（`outputs/figures/`，dpi 170，标签全 ASCII）：

- `outputs/figures/F36_stage19_relax_outcomes.png`（F36）—— (a) 单点 Δ 对弛豫后 Δ（按结局着色，y=x 与 ±1 meV 带；|Δ| 中位数 0.1198 → 0.00196 eV，缩小 61 倍）；(b) 37 个 moread_lower 格子的裁决：distinct_lower 5 / distinct_higher 24 / same_lower 0 / same_higher 8（已完成 37）；(c) 按 ε 的结局堆叠；(d) 按态与分子的分解
  sha256 = `0f46a89086d892ed04cc2133635b34557786e2ab9ac126cfb34efcd4d1ee4ca2`
- `outputs/figures/F37_stage19_identity_geometry.png`（F37）—— (e) 弛豫前后 charge_l1 对数散点、冻结阈值 0.039 与 ±20% 贴阈值带（弛豫前后都在阈值以上 29/37，贴阈值 0 格）；(f) 双解几何 RMSD 对 Δ 漂移（0.02 Å 同极小点参考线，下方 6/37 格）；(g) 两臂弛豫能量降配对（默认解中位降 1.876 eV vs moread 1.666 eV）；(h) 自旋中心迁移矩阵（argmax 仅作描述，不作判据）
  sha256 = `904c5f1e0f1826a2c2cec5756f5080f71d5caf1a97017419b7b86d30d637507a`

图与输入产物的 sha256 清单见 `outputs/figures/figure_manifest_week18_stage19.md`。

---

## 9. 已知限制

- **选择偏差**：这 37 格是按「两解不同」挑出来的，本报告的任何比例都**不是**全目录的发生率。
- **几何级判据的代理性**：`charge_l1` 是布居（population）距离，不是波函数重叠；两个布居相似但波函数不同的解会被当成“同一个”。
- **无频率校验**：`Opt` 只证明终点是驻点，不证明它是**真极小点**（没有虚频排查）。对发生偏好反转、以及被归入 `same_*` 的格子，这一点尤其重要。
- **有 1 条腿的 `Opt` 没有收敛**：TEGDME/anion/eps=200/default（触及迭代上限，作业仍正常结束）。相关格子的结论建立在一个未完全弛豫的几何上。
- **两条腿各自弛豫**：两个终点都只是**各自初猜落到的局部**极小点，不能说哪一个是全局最低。
- **无溶剂壳**：本周只有裸 CPCM 介电屏蔽，没有显式微溶剂化（第一溶剂壳在 Stage 9 单独考察）。
- **台账与数据的时间差**：本报告的数字是一个快照（`generated_utc = 2026-09-30T21:45:38.588152+00:00`）。

---

## 10. 下一步（Week 19 候选）

1. **把这 37 格的结论回填五级台阶的 P2 腿做敏感性检查**（**零新增计算**）：问“若 P2 单点里的这些格子改用弛豫后能量，台阶结论会不会动”；若不动，就把本周的 74 个作业归成“已排除的风险”。
2. **把 Stage 18 的 `charge_l1` 判据做成运行手册里的预检**（**零新增计算**）：在提交单点作业后先算一遍身份距离，只对超阈值的格子排第二次计算。
3. **对 `distinct_higher`（偏好反转）与 `same_*` 的格子做频率分析**（新计算，数量小）：确认它们是真极小点而不是鞍点，并看两条腿是否落在不同的自由度上（例如碳酸酯环的拉伸与弯折）。
4. **把第一溶剂壳（Stage 9）与弛豫联合**（新计算）：问“配位一个溶剂分子后，第二解还存在吗”——这是把本周的结论从裸离子推向真实溶液的第一步。

（Gate 状态：Gate 0 CLOSED、Gate 1 NOT CLOSED —— 唯一 blocker 仍是溶液锚点 31 行 `est`。）

