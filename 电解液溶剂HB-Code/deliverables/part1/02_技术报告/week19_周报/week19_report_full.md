# Week 19 报告 —— Stage 20：把「弛豫」放回台阶上，再问「第二解」是不是跨方法的概念

## 0. 一句话结论

本周把 Week 18 留下的两个问题拆成互不依赖的两个 Part：Part 1 是**零新增计算**的台阶回填（Week 18 §10 的第 1 条候选），Part 2 是 **74 个冻结 GFN2-xTB 作业**的跨方法检验（这一条不在 Week 18 的候选清单里，是本周新增的检验）。

**Part 1 —— 弛豫是第六级台阶。** 把 Week 18 落盘的 37 格弛豫能量放回 Stage 10 五级台阶的同一把尺子上（`Delta_ox = -drop(cation)`、`Delta_red = -drop(anion)`，两轴都是越大越稳，故 Delta 为负 = 弛豫把该轴的值推低）：

- **弛豫不是「另一个环境」**：同一个 (分子, 态) 在它已有的各个介电常数上，Delta 的极差中位只有 **0.0263 eV**、最大 **0.215 eV（DEC）**；作为对照，同一批分子的 P1→P2 环境位移是 **−2.17 ~ −2.46 eV**（单格极值 −2.91 eV）。弛豫修正几乎与连续介质的介电常数无关，是一个**态内量**。
- **但它也不是「纯平移」**：按态分成两支 —— 还原轴（anion，21 格）mean **-1.953** / std **0.160** / 相对散布 **0.08**，接近刚性平移；氧化轴（cation，16 格）mean **-0.610** / std **0.315** / 相对散布 **0.52**，是散布型。
- 与五级台阶在**同一批分子**上并置：氧化 {DMC,EC,TMP}@eps=5 这条新台阶相对散布 **0.74**（P1→P2 只有 0.17）、碳酸酯 {DMC,EC}@eps=5 为 **0.35**（P1→P2 0.08）；还原 {DEC,EMC,PC,TEGDME}@eps=20 为 **0.13**（P1→P2 0.26）。
- **明确不报** τ_b / Top-k / `f_unresolved`：本目录里每个分子只出现**一种态**（氧化轴 n=3、还原轴 n=4），这么少的点上的秩相关不构成统计推断，报告它只会诱导误读。这是**数据事实**（`n_molecules_by_state = {"anion": 4, "cation": 3}`），不是计算没做——`rank_metrics` 列逐行写明省略原因。

**Part 2 —— 第二解在廉价势能面上还分得开吗。** 以 Stage 19 两条 r2SCAN-3c 弛豫终点为起点，各跑一次 GFN2-xTB 弛豫（74 个作业，74 ok / 0 failed，中位 0.71 s）：

- 几何：**6/37 格两臂合并**到同一极小点（RMSD ≤ 0.02 Å），**31/37 格仍是两个极小点**。
- 能量：弛豫后 `moread` 仍更低 **15 格**；单点上 `moread` 更低、弛豫后不再更低（偏好反转）**6 格**。
- 与 Stage 19 逐格裁决一致 **17/37（46%）** —— 但这是**两套不同判据**之间的一致性（Stage 19 用冻结电子身份 `charge_l1 > 0.039`，本 Part 只有几何 RMSD），**不可与下面的 89% 混用**。
- **同一几何**上 xTB 单点与 ORCA r2SCAN-3c 的偏好方向一致 **33/37（89%）** —— 这才是纯粹的「廉价 vs 昂贵」方法对照。
- 量级：|xTB 单点 Δ| 中位 **7.17e-3 eV**，|xTB 弛豫 Δ| 中位 **2.13e-4 eV**（**压掉约 34 倍**）；单臂漂移中位 **0.651 / 0.657 Å**，与起点双解 RMSD 中位 **0.4716 Å** 同量级。

**合起来的物理读法**：「第二解谁更低」这个**偏好是跨方法可迁移的**（同一几何 89%），但**廉价优化器自己的弛豫会把它抹掉**（能量差压掉约 34 倍，几何漂移与起点差异同量级）。所以「第二解」不是一个「廉价方法也能独立复现」的概念，而是一个**必须由昂贵方法定义、廉价方法只能在给定几何上读出**的概念。

---

## 1. 为什么要有这一步（Stage 20 的动机）

Week 18（`docs/28_week18_report.md`）把 37 个 `moread_lower` 格子各自的**两条 SCF 解**都做了几何弛豫，得到两个坚硬的数字：终点仍判不同态的 29 格、偏好被几何反转的 32 格。但它把两个问题留在了半空中：一条是 §10 的第 1 条候选（这条弛豫修正要不要回填台阶），另一条是它自己没写下来的 —— 这 37 格全部只用了一个方法（r2SCAN-3c），那「第二解」会不会只是这个昂贵方法的数值假象。本周把这两条同时推进。

**Part 1 回答第一条：这条弛豫修正要不要回填进五级台阶？** 那 37 格不在 Stage 10 的主链上，所以读者无法判断「把 P2 单点换成 P2 弛豫」会不会改写台阶结论。Stage 10 已经证明**决定排序是否被改写的不是位移的大小 |mean|，而是位移的离散度 std**（ρ(std, τ_b) = −0.851）。所以不必重跑台阶：只要量出这条新台阶的 mean 与 std，就能判断它有没有资格改写排序。这正是 Part 1 要做的，而且**不需要任何新的量化计算**。

**Part 2 回答第二条：第二解是不是只在昂贵方法里存在？** Week 18 只在一个方法（r2SCAN-3c）里说「第二解是真的另一个电子态」。这里要分两个**不同**的问题：

1. 在**同一个几何**上，「哪条腿更低」这个判断能不能被廉价方法复现？—— 如果能，第二解就是可读出的电子结构量，而不是昂贵方法的数值假象。
2. 廉价优化器能不能**独立地把第二解找回来**？—— 即从昂贵方法的终点出发再做一次廉价弛豫，两条腿会不会自己合到一起去。

这两个问题在本周被分开测量，得到的方向也**不一样**（89% vs 46%），这正是 Part 2 的核心产出。

---

## 2. 口径与记号

### 2.1 Part 1：第六级台阶

- **台阶定义**（按轴分开，因为一个几何弛豫只会压低带电态）：

  ```
  Delta_ox(name)  = p_ox(弛豫) - p_ox(单点) = - drop(cation)
  Delta_red(name) = p_red(弛豫) - p_red(单点) = - drop(anion)
  ```

  两个轴都是「越大越稳」，所以 **Delta 为负 = 弛豫把该轴的值推低**。
- **输入**：`outputs/week18/stage19_relax_cells_analysis.csv`（37 格，Week 18 已发布、本周未改动）。
- **相对散布** = `shift_std_ev / |shift_mean_ev|`：Stage 10 用来判断「这条台阶有没有资格改写排序」的量。它在 |mean| 接近 0 时会发散，本报告在使用处逐条说明。
- **五级台阶参照物**：`outputs/week9/stage10_ladder.csv`（冻结），以及本目录自带的 `ladder_rows`（把新台阶与五级台阶在**同一批分子**上并置，因此可比）。
- **秩统计的门槛**：`min_n_for_rank_metrics = 5`。本目录每个分子只有一种态，氧化轴 n=3、还原轴 n=4，全部低于门槛，因此**一律不报** τ_b / Top-k / `f_unresolved`。

### 2.2 Part 2：跨方法裁决

- **起点**：Stage 19 两条腿各自的 r2SCAN-3c `Opt` 终点 `outputs/week18/orca_relax_<arm>/<name>/<name>_<state>_cpcm_<eps>_<arm>.xyz`，逐原子原样复制。
- **每个作业两步，全部冻结**：**GFN2-xTB 单点**（起点几何上的廉价读数，`sp`）→ **GFN2-xTB `--opt`**（廉价弛豫）。电荷/多重度逐行取 Stage 19 台账，不写死。
- **确定性**：`OMP_NUM_THREADS=1`；每次调用前清 xTB scratch，且每个作业独立目录。
- **xTB 侧没有隐式溶剂**：`epsilon` 只是「起点几何来自哪个 CPCM 格子」的**标签**，不进入 xTB 作业。因此按 `epsilon` 分层**不构成介电效应**，只是起点几何的分组。
- **判据（运行前固定）**：`same_*` = xTB 弛豫后两臂 Kabsch RMSD ≤ 0.02 Å；`lower` = `xtb_relax_delta_ev < -0.001 eV`（与 Stage 19 同一 material 阈值）。
- **同一几何的方法对照**：`xtb_sp_delta_ev` 与 Stage 19 的 `relax_delta_ev` 读的是**同一组几何**（Stage 19 弛豫终点），差别只在方法，因此可以逐格比较「哪条腿更低」——这是本阶段最锐利的廉价 vs 昂贵检验。
- **引擎**：xTB 6.7.1pre，GFN2。

---

## 3. 本周新增的计算

**Part 1：0 个新作业。** 它只把 Week 18 已经落盘的 37 格弛豫能量放到台阶的同一把尺子上。

**Part 2：74 个 GFN2-xTB 作业 = 37 格 × 2 条腿**（每腿 `sp` + `opt` 两步）。

| 项 | 值 | 来源 |
|---|---|---|
| 目标格子数 | 37 | `stage20_xtb_arms_plan.json` → `n_target_cells` |
| 作业数 | 74 | `stage20_xtb_arms_plan.json` → `n_jobs` |
| 作业类型 | `sp` + `opt` | `stage20_xtb_arms_plan.json` → `job_types` |
| 引擎 | 6.7.1pre（GFN2） | `stage20_xtb_arms_plan.json` → `engine_version` / `gfn` |
| 起点几何 | Stage 19 两腿的 r2SCAN-3c `Opt` 终点 | `stage20_xtb_arms_plan.json` → `start_geometry` |
| 电荷/多重度 | 逐行取 Stage 19 台账，不写死 | `stage20_xtb_arms_cells.csv` → `charge` / `multiplicity` |

### 3.1 起点几何审计（必须复用 Stage 19 终点，不重优化）

| 分子/态 | 格数 | 腿数 | 与 Stage 19 终点逐字节一致 |
|---|---|---|---|
| DEC/anion | 3 | 6 | 是 |
| DMC/cation | 1 | 2 | 是 |
| EC/cation | 5 | 10 | 是 |
| EMC/anion | 6 | 12 | 是 |
| PC/anion | 10 | 20 | 是 |
| TEGDME/anion | 2 | 4 | 是 |
| TMP/cation | 10 | 20 | 是 |
| **合计** | **37** | **74** | **74/74** |

审计逐条比对 `stage20_xtb_arms_cells.csv` 的 `start_geometry`（Stage 19 终点）与 `input_geometry`（本阶段实际喂给 xTB 的起始文件）的 SHA256：**74/74 逐字节相同**；74 条腿的起始几何彼此**互不相同**（74 个不同 SHA256），所以下面看到的任何差异都不可能来自起点被改动。

### 3.2 作业台账

- 台账行数：**74**（`stage20_xtb_arms_cells.csv`）——到本报告定稿时已登记 **74 个 ok**、0 个 failed。
- 单作业壁钟中位：**0.71 s**。
- 收敛与 QC：**74/74** 条腿 `opt_converged = True`、`scf_converged = True`、`normal_termination = True`；`qc_flags` 全部为空。弛豫后梯度范数区间 3.29e-4 – 9.74e-4 Eh/Bohr。
- 磁盘上的 `stage20_xtb_arms.json` 是定稿前一次**全缓存复跑**的快照（`n_reused = 74` / `n_computed = 0`），它记录的 74 个作业仍然 74 ok / 0 failed、中位壁钟 0.71 s；本报告只引用这个快照上的数字。

---

## 4. Part 1：弛豫作为第六级台阶

### 4.1 总量

| 切片 | n_cells | 分子数 | shift_mean (eV) | shift_std (eV) | 相对散布 std/|mean| | min (eV) | max (eV) |
|---|---|---|---|---|---|---|---|
| 全 37 格 | 37 | 7 | -1.372 | 0.714 | 0.52 | -2.440 | -0.191 |
| cation（氧化轴） | 16 | 3 | -0.610 | 0.315 | 0.52 | -0.850 | -0.191 |
| anion（还原轴） | 21 | 4 | -1.953 | 0.160 | 0.08 | -2.440 | -1.757 |

来源：`stage20_relax_rung.json` → `aggregates.overall` / `aggregates.by_state`。两轴方向一致（都被推低），但**位移的类型完全不同**：还原轴是「平移型」，氧化轴是「散布型」。

### 4.2 eps 不敏感性：弛豫是一个「态内量」

同一个 (分子, 态) 在它已有的各个介电常数上，Delta 几乎不动：

| 分子 | 态 | n_eps | eps 范围 | Delta 极差 (eV) | Delta 均值 (eV) |
|---|---|---|---|---|---|
| DEC | anion | 3 | 5–200 | 0.2150 | -1.842 |
| DMC | cation | 1 | 5–5 | 0.0000 | -0.335 |
| EC | cation | 5 | 5–20 | 0.0110 | -0.195 |
| EMC | anion | 6 | 5–1000 | 0.0263 | -1.944 |
| PC | anion | 10 | 5–1000 | 0.0534 | -1.900 |
| TEGDME | anion | 2 | 20–200 | 0.0640 | -2.408 |
| TMP | cation | 10 | 5–1000 | 0.0072 | -0.845 |

极差中位 **0.0263 eV**、最大 **0.215 eV**（DEC）；作为对照，同一批分子的单点环境位移（P1→P2）在 `stage10_ladder.csv` 里的 `shift_mean_ev` 是 **−2.17 ~ −2.46 eV**，单格极值到 **−2.91 eV**。也就是说 **弛豫修正几乎与连续介质的介电常数无关**，是一个态内量；它与「环境位移随 eps 强烈变化」形成直接对照。

来源：`stage20_relax_rung_epsilon.csv`（7 行，n_eps 之和 = 37 格）。

### 4.3 放在五级台阶的同一把尺子上

Stage 10 的中心结论是「决定排序是否被改写的是位移的**离散度**，不是位移的大小」。下表把新台阶与五级台阶在**同一批分子**上并置（因此可比）：

| population | 轴 | eps | 分子 | P1→P2 相对散布 | 弛豫 相对散布 | 弛豫 mean (eV) | 弛豫 std (eV) |
|---|---|---|---|---|---|---|---|
| `ox_dmc_ec_tmp_eps5` | oxidation | 5 | DMC;EC;TMP | 0.17 | 0.74 | -0.462 | 0.342 |
| `ox_carbonates_eps5` | oxidation | 5 | DMC;EC | 0.08 | 0.35 | -0.269 | 0.094 |
| `ox_all_eps_mean` | oxidation | per-molecule mean | DMC;EC;TMP | 0.17 | 0.75 | -0.459 | 0.342 |
| `red_dec_emc_pc_tegdme_eps20` | reduction | 20 | DEC;EMC;PC;TEGDME | 0.26 | 0.13 | -2.010 | 0.254 |
| `red_dec_emc_pc_eps5` | reduction | 5 | DEC;EMC;PC | 0.09 | 0.01 | -1.947 | 0.023 |
| `red_all_eps_mean` | reduction | per-molecule mean | DEC;EMC;PC;TEGDME | 0.26 | 0.13 | -2.024 | 0.260 |

两条代表性 population 的完整六级台阶（只列与该台阶同轴的那一半）：

**ox_dmc_ec_tmp_eps5**（axis = oxidation，DMC;EC;TMP，eps = 5）

| 台阶 | shift_mean (eV) | shift_std (eV) | 相对散布 |
|---|---|---|---|
| P0_to_P1 | -1.661 | 0.173 | 0.10 |
| P1_to_P2 | -2.346 | 0.398 | 0.17 |
| G1_to_G2 | -0.016 | 0.053 | 3.31 |
| P2sp_to_P2relax | -0.462 | 0.342 | 0.74 |

**red_dec_emc_pc_tegdme_eps20**（axis = reduction，DEC;EMC;PC;TEGDME，eps = 20）

| 台阶 | shift_mean (eV) | shift_std (eV) | 相对散布 |
|---|---|---|---|
| P0_to_P1 | 7.494 | 2.960 | 0.39 |
| P1_to_P2 | -2.165 | 0.557 | 0.26 |
| G1_to_G2 | -0.081 | 0.008 | 0.09 |
| P2sp_to_P2relax | -2.010 | 0.254 | 0.13 |

来源：`stage20_relax_rung.json` → `ladder_rows`（与 `stage20_relax_rung_ladder.csv` 一一对应）。读法提醒：`G1_to_G2` 的氧化位移 |mean| ≈ 0.01 eV，它的相对散布在数学上发散，照抄只为并置，**不作比较**。

### 4.4 逐格

| 分子 | 态 | eps | 子集 | Stage 19 裁决 | Δ_default (eV) | Δ_moread (eV) | Δ_arm (eV) | 双解 RMSD (Å) |
|---|---|---|---|---|---|---|---|---|
| DEC | anion | 5 | holdout | `distinct_higher` | -1.97249 | -1.83265 | 0.02001 | 0.3010 |
| DEC | anion | 20 | holdout | `distinct_higher` | -1.79601 | -1.71373 | 0.02371 | 0.3157 |
| DEC | anion | 200 | holdout | `distinct_higher` | -1.75750 | -1.66855 | 0.02484 | 0.3217 |
| DMC | cation | 5 | discovery | `same_higher` | -0.33531 | -0.33370 | -0.00004 | 0.0031 |
| EC | cation | 5 | discovery | `distinct_lower` | -0.20198 | -0.19429 | -0.00972 | 0.1003 |
| EC | cation | 7 | discovery | `distinct_lower` | -0.19746 | -0.19179 | -0.00398 | 0.0790 |
| EC | cation | 10 | discovery | `distinct_lower` | -0.19436 | -0.19035 | -0.00110 | 0.0666 |
| EC | cation | 14 | discovery | `same_higher` | -0.19239 | -0.18980 | -0.00021 | 0.0402 |
| EC | cation | 20 | discovery | `same_higher` | -0.19097 | -0.18944 | 0.00004 | 0.0205 |
| EMC | anion | 5 | discovery | `same_higher` | -1.93901 | -1.80203 | 0.00000 | 0.0000 |
| EMC | anion | 20 | discovery | `distinct_higher` | -1.96535 | -1.69933 | 0.02402 | 0.3069 |
| EMC | anion | 40 | discovery | `same_higher` | -1.94079 | -1.67716 | 0.00000 | 0.0000 |
| EMC | anion | 80 | discovery | `same_higher` | -1.94063 | -1.66555 | 0.00000 | 0.0000 |
| EMC | anion | 200 | discovery | `same_higher` | -1.94054 | -1.65840 | -0.00000 | 0.0000 |
| EMC | anion | 1000 | discovery | `same_higher` | -1.94050 | -1.65454 | -0.00000 | 0.0000 |
| PC | anion | 5 | discovery | `distinct_higher` | -1.92958 | -1.84362 | 0.00653 | 0.4766 |
| PC | anion | 7 | discovery | `distinct_higher` | -1.92555 | -1.83209 | 0.00718 | 0.4741 |
| PC | anion | 10 | discovery | `distinct_higher` | -1.91726 | -1.81917 | 0.00765 | 0.4724 |
| PC | anion | 14 | discovery | `distinct_higher` | -1.90872 | -1.80819 | 0.00796 | 0.4721 |
| PC | anion | 20 | discovery | `distinct_higher` | -1.90059 | -1.79860 | 0.00819 | 0.4723 |
| PC | anion | 28 | discovery | `distinct_higher` | -1.89432 | -1.79153 | 0.00833 | 0.4716 |
| PC | anion | 40 | discovery | `distinct_higher` | -1.88916 | -1.78586 | 0.00845 | 0.4720 |
| PC | anion | 80 | discovery | `distinct_higher` | -1.88267 | -1.77883 | 0.00859 | 0.4708 |
| PC | anion | 200 | discovery | `distinct_higher` | -1.87852 | -1.77440 | 0.00867 | 0.4706 |
| PC | anion | 1000 | discovery | `distinct_higher` | -1.87622 | -1.77198 | 0.00871 | 0.4705 |
| TEGDME | anion | 20 | holdout | `distinct_lower` | -2.37643 | -2.32153 | -0.06561 | 2.2142 |
| TEGDME | anion | 200 | holdout | `distinct_lower` | -2.44047 | -2.42782 | -0.12994 | 3.8527 |
| TMP | cation | 5 | discovery | `distinct_higher` | -0.85006 | -0.69585 | 0.00196 | 0.7125 |
| TMP | cation | 7 | discovery | `distinct_higher` | -0.84719 | -0.69864 | 0.00145 | 0.7300 |
| TMP | cation | 10 | discovery | `distinct_higher` | -0.84616 | -0.70137 | 0.00171 | 0.7436 |
| TMP | cation | 14 | discovery | `distinct_higher` | -0.84534 | -0.70347 | 0.00151 | 0.7511 |
| TMP | cation | 20 | discovery | `distinct_higher` | -0.84484 | -0.70518 | 0.00137 | 0.7556 |
| TMP | cation | 28 | discovery | `distinct_higher` | -0.84456 | -0.70638 | 0.00127 | 0.7586 |
| TMP | cation | 40 | discovery | `distinct_higher` | -0.84439 | -0.70732 | 0.00119 | 0.7606 |
| TMP | cation | 80 | discovery | `distinct_higher` | -0.84284 | -0.70846 | -0.00026 | 0.7624 |
| TMP | cation | 200 | discovery | `distinct_higher` | -0.84413 | -0.70916 | 0.00107 | 0.7647 |
| TMP | cation | 1000 | discovery | `distinct_higher` | -0.84409 | -0.70955 | 0.00104 | 0.7653 |

来源：`stage20_relax_rung_cells.csv`（37 行）。`Δ_default` = −(default 腿的弛豫能量降)，`Δ_moread` = −(moread 腿的弛豫能量降)，`Δ_arm` = 两腿之差；**Delta 为负 = 弛豫把该轴的值推低**。「Stage 19 裁决」一列是从 Week 18 逐格台账原样带入的，**本周未重算**。

### 4.5 分层

**按态**

| 组 | n | mean (eV) | std (eV) | 相对散布 | min (eV) | max (eV) |
|---|---|---|---|---|---|---|
| anion | 21 | -1.953 | 0.160 | 0.08 | -2.440 | -1.757 |
| cation | 16 | -0.610 | 0.315 | 0.52 | -0.850 | -0.191 |

**按分子**

| 组 | n | mean (eV) | std (eV) | 相对散布 | min (eV) | max (eV) |
|---|---|---|---|---|---|---|
| DEC | 3 | -1.842 | 0.115 | 0.06 | -1.972 | -1.757 |
| DMC | 1 | -0.335 | — | — | -0.335 | -0.335 |
| EC | 5 | -0.195 | 0.004 | 0.02 | -0.202 | -0.191 |
| EMC | 6 | -1.944 | 0.010 | 0.01 | -1.965 | -1.939 |
| PC | 10 | -1.900 | 0.019 | 0.01 | -1.930 | -1.876 |
| TEGDME | 2 | -2.408 | 0.045 | 0.02 | -2.440 | -2.376 |
| TMP | 10 | -0.845 | 0.002 | 0.00 | -0.850 | -0.843 |

（`DMC` 只有 1 格，`shift_std_ev` 与相对散布在 JSON 里是 `null`，本表显示为 —。）

**按发现/留出臂**

| 组 | n | mean (eV) | std (eV) | 相对散布 | min (eV) | max (eV) |
|---|---|---|---|---|---|---|
| discovery | 32 | -1.264 | 0.699 | 0.553 | -1.965 | -0.191 |
| holdout | 5 | -2.069 | 0.321 | 0.155 | -2.440 | -1.757 |

来源：`stage20_relax_rung.json` → `aggregates.by_state` / `by_molecule` / `by_arm_set`。**按 eps 分层没有单调趋势**（`aggregates.by_epsilon`），本报告不主张任何 eps 趋势。

### 4.6 为什么这里不报 τ_b / Top-k（结构性理由）

本目录的 37 格只覆盖 7 个分子，而且**每个分子只出现一种态**：阴离子 4 个（DEC/EMC/PC/TEGDME）、阳离子 3 个（DMC/EC/TMP）。于是一条台阶上只有氧化轴 n=3 或还原轴 n=4 个点 —— 秩相关不是统计量，是三个/四个数之间的排序。报告 τ_b 只会让读者把它读成「台阶被改写/没被改写」的推断，而它承担不起这个推断。

这是**数据事实**（分子的态覆盖），不是计算没做：`stage20_relax_rung_ladder.csv` 的 `rank_metrics` 列在每一行都写明了省略原因（`omitted: n_molecules=<n> < 5`），本报告的 `_guard()` 也会逐行断言它。本报告改用 Stage 10 的**相对散布**做定性判读 —— 它不需要秩统计，只需要 mean 与 std。

---

## 5. Part 2：两个 SCF 解在 GFN2-xTB 势能面上的跨方法裁决

### 5.1 四类结局的总数

| 结论 | 格数 | 含义 |
|---|---|---|
| `distinct_lower` | 15 | 廉价弛豫后两臂仍是两个极小点，且 `moread` 腿更低 |
| `distinct_higher` | 16 | 仍是两个极小点，但 `moread` 腿反而更高（偏好反转） |
| `same_lower` | 0 | 两臂合并到同一极小点，且 `moread` 仅作为数值更低 |
| `same_higher` | 6 | 两臂合并到同一极小点，且 `moread` 更高 |
| `incomplete` | 0 | 两腿未齐备，不判 |

来源：`stage20_xtb_arms_analysis.json` → `aggregates.all.all.outcomes`。已完成 37 格；其中两臂仍是两个极小点 **31**、已合并 **6**、偏好反转 **6**。

**合并的 6 格**：DMC/cation/eps=5、EMC/anion/eps=5、EMC/anion/eps=40、EMC/anion/eps=80、EMC/anion/eps=200、EMC/anion/eps=1000。这些格子**几何上确实收敛到一起**（Kabsch RMSD ≤ 0.02 Å），对应 Stage 19 里被归为 `same_*` 的那些格子 —— 但两边的判据不同，见 §5.3。

**偏好反转的 6 格**：EC/cation/eps=10、EC/cation/eps=14、EC/cation/eps=20、TEGDME/anion/eps=20、TEGDME/anion/eps=200、TMP/cation/eps=80（单点上 `moread` 更低、xTB 弛豫后不再更低）。

### 5.2 分层

| 切片 | 组 | n | 仍两个极小点 | 合并为一 | moread仍更低 | 偏好反转 | 单点Δ绝对值中位 (eV) | 弛豫Δ绝对值中位 (eV) | 弛豫后RMSD中位 (Å) | 与S19一致 | 同几何一致 |
|---|---|---|---|---|---|---|---|---|---|---|
| 按态 | anion | 21 | 16 | 5 | 14 | 2 | 0.010 | 0.03301 | 0.8050 | 5/21 | 21/21 |
| 按态 | cation | 16 | 15 | 1 | 1 | 4 | 0.004 | 0.00004 | 0.9495 | 12/16 | 12/16 |
| 按分子 | DEC | 3 | 3 | 0 | 3 | 0 | 0.028 | 0.02684 | 1.4117 | 0/3 | 3/3 |
| 按分子 | DMC | 1 | 0 | 1 | 0 | 0 | 0.000 | 0.00002 | 0.0032 | 1/1 | 1/1 |
| 按分子 | EC | 5 | 5 | 0 | 1 | 3 | 0.007 | 0.00001 | 0.1066 | 1/5 | 2/5 |
| 按分子 | EMC | 6 | 1 | 5 | 1 | 0 | 0.000 | 0.00003 | 0.0029 | 5/6 | 6/6 |
| 按分子 | PC | 10 | 10 | 0 | 10 | 0 | 0.010 | 0.03308 | 0.8048 | 0/10 | 10/10 |
| 按分子 | TEGDME | 2 | 2 | 0 | 0 | 2 | 0.188 | 0.20077 | 3.6542 | 0/2 | 2/2 |
| 按分子 | TMP | 10 | 10 | 0 | 0 | 1 | 0.004 | 0.00008 | 0.9568 | 10/10 | 9/10 |
| 按臂 | discovery | 32 | 26 | 6 | 12 | 4 | 0.005 | 0.00016 | 0.8048 | 17/32 | 28/32 |
| 按臂 | holdout | 5 | 5 | 0 | 3 | 2 | 0.029 | 0.02716 | 1.4141 | 0/5 | 5/5 |

来源：`stage20_xtb_arms_analysis.json` → `aggregates.by_state` / `by_molecule` / `by_arm_set`（与同名 CSV 一一对应）。**按 `epsilon` 分层不构成介电效应**（见 §2.2），本报告只把它当作起点几何的分组列出，不主张任何趋势。

### 5.3 与 Stage 19 的裁决对照

行 = Stage 19 的**电子**裁决（`charge_l1`，冻结阈值 0.039）；列 = 本阶段 xTB 的**几何**裁决（RMSD ≤ 0.02 Å 记 `same_*`）。对角线之和 17 即 §0 的 46% 一致率。

| Stage 19 \ Part 2 | distinct_lower | distinct_higher | same_lower | same_higher |
|---|---|---|---|---|
| distinct_lower | 1 | 4 | 0 | 0 |
| distinct_higher | 14 | 10 | 0 | 0 |
| same_lower | 0 | 0 | 0 | 0 |
| same_higher | 0 | 2 | 0 | 6 |

这张表说明了一件必须说清楚的事：**两套判据本身就不一样**。Stage 19 问「两个解的 Mulliken 布居差得够不够远」，本阶段只能问「两个优化终点隔得够不够远」。所以 46% 是**判据之间**的一致性，不是同一个判据被重复测量了两次 —— 把它与下面的 89% 混为一谈是错的。

### 5.4 同一几何上的方法对照（xTB 单点 vs ORCA r2SCAN-3c）

`xtb_sp_delta_ev` 与 Stage 19 的 `relax_delta_ev` 读的是**同一组几何**（Stage 19 的弛豫终点），差别只在方法。以同一 material 阈值（−0.001 eV）判定「哪条腿更低」，两者一致 **33/37（89%）**。

不一致的 4 格（ORCA 侧「弛豫 Δ」绝对值最大 0.00972 eV，其中 3 格本身就在 material 阈值带（≤ 0.001 eV）里）——分歧集中在**昂贵方法自己都判不动的近简并格子**上：

| 分子 | 态 | eps | xTB 单点 Δ (eV) | ORCA 弛豫 Δ (eV) |
|---|---|---|---|---|
| EC | cation | 5 | 0.00717 | -0.00972 |
| EC | cation | 14 | -0.00731 | -0.00021 |
| EC | cation | 20 | -0.00267 | 0.00004 |
| TMP | cation | 80 | -0.00391 | -0.00026 |

### 5.5 逐格

| 分子 | 态 | eps | 子集 | xTB单点Δ (eV) | xTB弛豫Δ (eV) | Δ改变 (eV) | 起始RMSD (Å) | 弛豫后RMSD (Å) | 漂移 d/m (Å) | 结论 | S19裁决 | 一致 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| DEC | anion | 5 | holdout | 0.02732 | -0.02651 | -0.05384 | 0.3010 | 1.4001 | 1.100 / 0.937 | `distinct_lower` | `distinct_higher` | 否 |
| DEC | anion | 20 | holdout | 0.02832 | -0.02716 | -0.05548 | 0.3157 | 1.4117 | 1.114 / 0.960 | `distinct_lower` | `distinct_higher` | 否 |
| DEC | anion | 200 | holdout | 0.02939 | -0.02684 | -0.05623 | 0.3217 | 1.4141 | 1.121 / 0.974 | `distinct_lower` | `distinct_higher` | 否 |
| DMC | cation | 5 | discovery | 0.00041 | -0.00002 | -0.00043 | 0.0031 | 0.0032 | 0.312 / 0.315 | `same_higher` | `same_higher` | 是 |
| EC | cation | 5 | discovery | 0.00717 | -0.00001 | -0.00718 | 0.1003 | 0.1062 | 0.050 / 0.042 | `distinct_higher` | `distinct_lower` | 否 |
| EC | cation | 7 | discovery | -0.00314 | -0.01055 | -0.00742 | 0.0790 | 0.0526 | 0.016 / 0.030 | `distinct_lower` | `distinct_lower` | 是 |
| EC | cation | 10 | discovery | -0.00760 | -0.00001 | 0.00759 | 0.0666 | 0.1066 | 0.056 / 0.021 | `distinct_higher` | `distinct_lower` | 否 |
| EC | cation | 14 | discovery | -0.00731 | 0.00001 | 0.00732 | 0.0402 | 0.1067 | 0.057 / 0.023 | `distinct_higher` | `same_higher` | 否 |
| EC | cation | 20 | discovery | -0.00267 | -0.00000 | 0.00266 | 0.0205 | 0.1072 | 0.057 / 0.040 | `distinct_higher` | `same_higher` | 否 |
| EMC | anion | 5 | discovery | -0.00000 | 0.00000 | 0.00000 | 0.0000 | 0.0001 | 1.191 / 1.191 | `same_higher` | `same_higher` | 是 |
| EMC | anion | 20 | discovery | 0.02312 | -0.01325 | -0.03637 | 0.3069 | 1.6175 | 0.959 / 1.205 | `distinct_lower` | `distinct_higher` | 否 |
| EMC | anion | 40 | discovery | -0.00000 | -0.00005 | -0.00005 | 0.0000 | 0.0027 | 1.217 / 1.218 | `same_higher` | `same_higher` | 是 |
| EMC | anion | 80 | discovery | -0.00000 | -0.00001 | -0.00001 | 0.0000 | 0.0032 | 1.212 / 1.213 | `same_higher` | `same_higher` | 是 |
| EMC | anion | 200 | discovery | 0.00000 | -0.00001 | -0.00001 | 0.0000 | 0.0009 | 1.207 / 1.208 | `same_higher` | `same_higher` | 是 |
| EMC | anion | 1000 | discovery | 0.00000 | -0.00028 | -0.00028 | 0.0000 | 0.0138 | 1.206 / 1.211 | `same_higher` | `same_higher` | 是 |
| PC | anion | 5 | discovery | 0.00937 | -0.03313 | -0.04250 | 0.4766 | 0.8078 | 0.415 / 0.452 | `distinct_lower` | `distinct_higher` | 否 |
| PC | anion | 7 | discovery | 0.00993 | -0.03301 | -0.04294 | 0.4741 | 0.8094 | 0.414 / 0.453 | `distinct_lower` | `distinct_higher` | 否 |
| PC | anion | 10 | discovery | 0.00978 | -0.03306 | -0.04284 | 0.4724 | 0.8087 | 0.413 / 0.452 | `distinct_lower` | `distinct_higher` | 否 |
| PC | anion | 14 | discovery | 0.01011 | -0.03309 | -0.04320 | 0.4721 | 0.8050 | 0.413 / 0.451 | `distinct_lower` | `distinct_higher` | 否 |
| PC | anion | 20 | discovery | 0.00989 | -0.03308 | -0.04297 | 0.4723 | 0.8047 | 0.413 / 0.450 | `distinct_lower` | `distinct_higher` | 否 |
| PC | anion | 28 | discovery | 0.00989 | -0.03321 | -0.04309 | 0.4716 | 0.8076 | 0.408 / 0.450 | `distinct_lower` | `distinct_higher` | 否 |
| PC | anion | 40 | discovery | 0.00975 | -0.03311 | -0.04286 | 0.4720 | 0.8046 | 0.411 / 0.450 | `distinct_lower` | `distinct_higher` | 否 |
| PC | anion | 80 | discovery | 0.00991 | -0.03301 | -0.04292 | 0.4708 | 0.8003 | 0.416 / 0.450 | `distinct_lower` | `distinct_higher` | 否 |
| PC | anion | 200 | discovery | 0.00992 | -0.03304 | -0.04296 | 0.4706 | 0.8010 | 0.414 / 0.450 | `distinct_lower` | `distinct_higher` | 否 |
| PC | anion | 1000 | discovery | 0.00993 | -0.03308 | -0.04302 | 0.4705 | 0.8036 | 0.411 / 0.450 | `distinct_lower` | `distinct_higher` | 否 |
| TEGDME | anion | 20 | holdout | -0.03267 | 0.10784 | 0.14052 | 2.2142 | 4.0312 | 1.521 / 2.945 | `distinct_higher` | `distinct_lower` | 否 |
| TEGDME | anion | 200 | holdout | -0.34415 | 0.29370 | 0.63785 | 3.8527 | 3.2773 | 2.497 / 1.106 | `distinct_higher` | `distinct_lower` | 否 |
| TMP | cation | 5 | discovery | 0.00018 | -0.00006 | -0.00024 | 0.7125 | 0.9418 | 0.646 / 0.646 | `distinct_higher` | `distinct_higher` | 是 |
| TMP | cation | 7 | discovery | 0.00159 | -0.00015 | -0.00174 | 0.7300 | 0.9521 | 0.651 / 0.655 | `distinct_higher` | `distinct_higher` | 是 |
| TMP | cation | 10 | discovery | 0.00439 | 0.00021 | -0.00417 | 0.7436 | 0.9469 | 0.673 / 0.657 | `distinct_higher` | `distinct_higher` | 是 |
| TMP | cation | 14 | discovery | 0.00479 | 0.00005 | -0.00474 | 0.7511 | 0.9573 | 0.673 / 0.658 | `distinct_higher` | `distinct_higher` | 是 |
| TMP | cation | 20 | discovery | 0.00474 | -0.00002 | -0.00476 | 0.7556 | 0.9596 | 0.674 / 0.659 | `distinct_higher` | `distinct_higher` | 是 |
| TMP | cation | 28 | discovery | 0.00456 | -0.00018 | -0.00474 | 0.7586 | 0.9563 | 0.675 / 0.659 | `distinct_higher` | `distinct_higher` | 是 |
| TMP | cation | 40 | discovery | 0.00466 | -0.00021 | -0.00487 | 0.7606 | 0.9557 | 0.677 / 0.659 | `distinct_higher` | `distinct_higher` | 是 |
| TMP | cation | 80 | discovery | -0.00391 | -0.00010 | 0.00381 | 0.7624 | 0.9595 | 0.651 / 0.662 | `distinct_higher` | `distinct_higher` | 是 |
| TMP | cation | 200 | discovery | 0.00437 | -0.00001 | -0.00438 | 0.7647 | 0.9608 | 0.679 / 0.662 | `distinct_higher` | `distinct_higher` | 是 |
| TMP | cation | 1000 | discovery | 0.00431 | -0.00004 | -0.00435 | 0.7653 | 0.9606 | 0.679 / 0.662 | `distinct_higher` | `distinct_higher` | 是 |

来源：`stage20_xtb_arms_cells_analysis.csv`（37 行）。`d/m` = default 腿 / moread 腿的弛豫漂移（各自终点对各自起点的 Kabsch RMSD）。

### 5.6 量级对比

| 量 | 中位 p50 |
|---|---|
| `abs(xtb_sp_delta_ev)` | 7.17e-3 eV |
| `abs(xtb_relax_delta_ev)` | 2.13e-4 eV |
| 单臂漂移（default） | 0.651 Å |
| 单臂漂移（moread） | 0.657 Å |
| 起点双解 RMSD | 0.4716 Å |
| xTB 弛豫后双解 RMSD | 0.8078 Å |
| xTB 弛豫能量降（default） | 0.301 eV |
| xTB 弛豫能量降（moread） | 0.320 eV |

来源：`stage20_xtb_arms_analysis.json` → `aggregates.all.all`。xTB 弛豫把两臂的能量差压掉约 **34 倍**（7.17e-3 → 2.13e-4 eV），而它自己的几何漂移（0.651 / 0.657 Å）与起点两条腿的差异（0.4716 Å）是**同一个量级** —— 也就是说，廉价优化器的每一步移动，和它想分辨的那件事一样大。

---

## 6. 物理读法

1. **「第二解谁更低」这个偏好是跨方法可迁移的。** 在**同一几何**上，一个 GFN2-xTB 单点就能复现 ORCA r2SCAN-3c 的偏好方向 33/37（89%）。这说明两臂的能量差不是昂贵泛函的数值假象，而是**几何/电子结构**里本来就有的东西。
2. **但廉价优化器自己的弛豫会把这件事抹掉。** 一旦让 xTB 从 Stage 19 终点继续优化，两臂的能量差被压掉约 34 倍（7.17e-3 → 2.13e-4 eV），而它同时把几何挪了 0.651 / 0.657 Å —— **挪动量与待分辨量同量级**，于是 xTB 自己的裁决（46% 一致）就不再说明第二解的存在与否，只说明廉价势能面把这两条腿当成了一条。
3. **因此「第二解」的定义方式是唯一确定的：必须由昂贵方法定义，廉价方法只能在给定几何上读出。**想用廉价方法**独立复现**同一套裁决是行不通的：它自己的弛豫把两臂的能量差压掉约 34 倍，逐格裁决与 Stage 19 只有 46% 一致（6/37 格两臂干脆合并）；但把它当作**预检/复核工具**是可行的（同一几何上 89% 一致）。
4. **Part 1：弛豫不是「另一个环境」。** 它的位移几乎与 eps 无关（逐 (分子, 态) 极差中位 0.0263 eV），而 P1→P2 的环境位移是 −2.17 ~ −2.46 eV（单格极值 −2.91 eV）。把弛豫当成台阶时，它属于**态内量**，不属于环境位移那一类。
5. **但它也不是纯平移，而且两条轴类型不同。** 还原轴（anion）相对散布 0.08，接近刚性平移；氧化轴（cation）相对散布 0.52，是散布型。按 Stage 10 的判据（决定台阶是否改写排序的是 std 而非 |mean|），这条新台阶在**还原轴上几乎不可能改写排序**，在**氧化轴上具备改写排序所需的散布**。
6. **46% 与 89% 的差距是判据差距，不是方法差距。** 前者把「电子身份」与「几何」两种判据放在一起比，后者把两种方法放在同一个几何上比。两者都在 §5 里，但只能读各自的结论。
7. **合并的格子集中在特定的化学环境**：6 格合并里 5 格是 EMC 阴离子、1 格是 DMC 阳离子；而 PC/DEC/TMP 与 EC 的那些格子两臂始终分得开（共 31 格 `distinct_*`）。这与 Week 18 的观察一致：**身份差异的大小与分子/态强相关**。
8. **阴离子在 xTB 上也没有出现「未束缚」信号**：42 条阴离子作业的 HOMO 全为负（起始最大 -0.4289 eV、弛豫后最大 -0.9298 eV），因此没有任何 `unbound_anion` 标记 —— 这是真实读数。

**一个样例（数字直接读自 JSON，不作外推）**：

- **DEC/anion/eps=5**：起点两臂 RMSD 0.3010 Å。在**同一几何**上 xTB 单点 Δ = 0.02732 eV、ORCA 弛豫 Δ = 0.02001 eV —— **两种方法一致地说 `moread` 更高**（这正是 89% 那一类）。但让 xTB 自己继续弛豫后就变成 Δ = -0.02651 eV（`moread` 更低），两臂 RMSD 被推到 1.4001 Å —— **廉价弛豫把偏好又翻了回去**，于是 Part 2 的裁决（`distinct_lower`）与 Stage 19（`distinct_higher`）不一致；两腿漂移 1.100 / 0.937 Å。
- **EMC/anion/eps=40**（`same_higher`）：起点两臂 RMSD 0.0000 Å，xTB 弛豫后 0.0027 Å —— 两臂落到**同一个极小点**；单点 Δ = -6.89e-8 eV，弛豫后 Δ = -4.99e-5 eV —— 两者都落在 0.001 eV 的 material 阈值带内，按冻结约定记 `same_higher`。对应 Stage 19 的 `same_higher`（电子身份也重合），两边结论一致。

---

## 7. 读法纪律

1. **两个「一致率」不可混用。** 46% 是**两套不同判据**（电子身份 vs 几何）之间的一致性；89% 是**同一几何上两种方法**的一致性。前者不能当成方法验证，后者不能当成身份判定。
2. **Part 2 的所有比例都条件在「Stage 19 单点上两解不同且 `moread` 更低」这 37 格上**；它们不是 414 格总体的发生率。
3. **xTB 作业是气相的（无 CPCM）**，而 Stage 19 是 CPCM(epsilon)。`epsilon` 在本节只标记「起点几何来自哪个格子」，因此 `by_epsilon` 分层**不构成介电效应**。
4. **`xtb_preference_flipped` 沿用 Stage 19 的单向约定**（`moread` 更低 → 不再更低），但反方向同样存在：有 **14 格**是 xTB 弛豫后才**变成** `moread` 更低（单点时不是）。只读单向列会误以为变化只朝一个方向。
5. **`0.02 Å` 与 `0.001 eV` 都是运行前固定的描述性阈值**，本阶段未做任何事后调参；`_guard()` 每次生成都断言它们没有被改。
6. **Part 1 不重算 τ_b / Top-k / `f_unresolved`**（§4.6），**也不把本目录读成 414 格的发生率**（这 37 格是按「两解不同」选出来的）。
7. **不可读成「P2 腿错了 1.9 eV」。** 本目录的格子是**裸 CPCM、逐格自己的 eps**，而五级台阶的 P2 腿是 **SMD(乙腈)**；两者不是同一个环境模型，§4 只给「垂直近似」的量级尺度。
8. **不可把氧化轴的散布读成「碳酸酯之间的差异」**：氧化轴的 3 个分子跨了 2 个家族（碳酸酯 EC/DMC + 亚磷酸酯 TMP），相对散布里含有家族对比；同一家族的碳酸酯子集（DMC/EC）在 §4.3 里单列。
9. **相对散布在 |mean| 接近 0 时会发散**（如 `G1_to_G2` 的氧化位移），本报告在使用处逐条标注。

---

## 8. 产物与图表

| 产物 | 说明 |
|---|---|
| `outputs/week19/stage20_relax_rung.json` | Part 1 主数据源：37 格、分层、六级台阶并置（本报告引用） |
| `outputs/week19/stage20_relax_rung_cells.csv` | Part 1 逐格（37 行） |
| `outputs/week19/stage20_relax_rung_epsilon.csv` | Part 1 逐 (分子, 态) 的 eps 极差（7 行） |
| `outputs/week19/stage20_relax_rung_ladder.csv` | Part 1 六级台阶并置（30 行，含 `rank_metrics` 省略说明） |
| `outputs/week19/stage20_relax_rung_summary.md` | Part 1 的 Markdown 摘要 |
| `outputs/week19/stage20_xtb_arms_analysis.json` | Part 2 主数据源：逐格裁决、分层、交叉表（本报告引用） |
| `outputs/week19/stage20_xtb_arms_cells_analysis.csv` | Part 2 逐格 × 37 列的计算明细（37 行） |
| `outputs/week19/stage20_xtb_arms_cells.csv` | Part 2 作业级台账（每行 = 1 个 xTB 作业，74 行） |
| `outputs/week19/stage20_xtb_arms_plan.json` | Part 2 的提交计划（37 格 / 74 作业） |
| `outputs/week19/stage20_xtb_arms.json` | Part 2 运行器逐层摘要 |
| `outputs/week19/stage20_xtb_arms_by_state.csv` | Part 2 按电子态分层 |
| `outputs/week19/stage20_xtb_arms_by_molecule.csv` | Part 2 按分子分层 |
| `outputs/week19/stage20_xtb_arms_by_epsilon.csv` | Part 2 按起点来源 eps 分层（不是溶剂效应） |
| `outputs/week19/stage20_xtb_arms_by_arm_set.csv` | Part 2 按发现/留出臂分层 |
| `outputs/week19/stage20_xtb_arms_summary.md` | Part 2 的 Markdown 摘要 |

| 脚本 | 说明 |
|---|---|
| `scripts/analyze_stage20_relax_rung.py` | Part 1 的合成器（零新增计算） |
| `scripts/run_stage20_xtb_arms.py` | Part 2 的 74 个 GFN2-xTB 作业提交器 |
| `scripts/analyze_stage20_xtb_arms.py` | Part 2 的逐格裁决与聚合 |
| `scripts/gen_week19_report.py` | 本报告生成器 |

两张图（`outputs/figures/`，dpi 170，标签全 ASCII）：

- `outputs/figures/F38_stage20_relax_rung.png`（F38）—— Part 1 —— 第六级台阶（P2 单点 -> P2 弛豫）的刻度
- `outputs/figures/F39_stage20_xtb_arms.png`（F39）—— Part 2 —— 两个 SCF 解在 GFN2-xTB 势能面上的跨方法裁决

图的长 caption（供终端站点逐字引用）与输入产物的 sha256 清单见 `outputs/figures/figure_manifest_week19_stage20.md`。

---

## 9. 已知限制

- **选择偏差**：这 37 格是按「两解不同」挑出来的，本报告的任何比例都**不是**全目录的发生率。
- **两个 Part 的判据不同**：Part 1 沿用 Stage 19 的电子裁决，Part 2 只有几何 RMSD；两边的「distinct」不是同一个量（§5.3）。
- **Part 2 没有隐式溶剂**：xTB 是气相的，Stage 19 是 CPCM；这是廉价方法本身的差异，属于本阶段要测量的对象之一，不是可控变量。
- **几何级判据的代理性**：RMSD ≤ 0.02 Å 不能证明两条腿在电子结构上相同，只说明落点靠近。
- **无频率校验**：`Opt` 只证明终点是驻点，不证明它是**真极小点**（没有虚频排查），两个 Part 都继承了这一点。
- **Part 1 的相对散布在 |mean| 接近 0 时发散**，本报告在使用处逐条标注，不作比较。
- **Part 1 不回填台阶**：它只给出「这条新台阶的 mean/std 是多少」，并不声称 Stage 10 的发布结论需要变动 —— 那需要真正重跑 P2 腿。
- **台账与数据的时间差**：本报告的数字是一个快照（`stage20_xtb_arms.json` → `generated_utc = 2026-09-30T22:14:40.228182+00:00`）。

---

## 10. 下一步（Week 20 候选）

1. **对 Week 18 的 5 个 `distinct_lower` 幸存者做极小点确认**（新计算，数量小）：EC/cation/eps=5,7,10 与 TEGDME/anion/eps=20,200 做频率分析，确认它们是**真极小点**而不是鞍点，并看两条腿落在哪个自由度上。注意本周 Part 2 已经说明：这 5 格里只有 EC/cation/eps=7 在廉价势能面上**仍是** `distinct_lower`，另外 4 格都被 xTB 弛豫改判 —— 所以频率分析要同时回答「它们是不是驻点」与「为什么廉价面会把其中 4 格抹掉」。
2. **把 `charge_l1` 判据做成运行手册里的预检**（**零新增计算**）：在提交单点作业后先算一遍身份距离，只对超阈值的格子排第二次计算；顺带把 Part 2 的 89% 同几何一致性写成「廉价单点读数」的适用条件与反例。
3. **把第一溶剂壳（Stage 9）与弛豫联合**（新计算）：问「配位一个溶剂分子后，第二解还存在吗」——这是把两周的结论从裸离子推向真实溶液的第一步。
4. **给第六级台阶补一次「真回填」的敏感性检查**（新计算或半新）：本报告只把弛豫放到台阶的尺子上（Part 1），若要回答「台阶结论会不会动」，需要把 P2 腿里对应的格子真正换成弛豫后能量再合成一次 —— 氧化轴尤其值得做，因为它的相对散布（0.74）已经落在能改写排序的区间里。

（Gate 状态：Gate 0 CLOSED、Gate 1 NOT CLOSED —— 唯一 blocker 仍是溶液锚点 31 行 `est`。）

