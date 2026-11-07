# Stage 20 / Part 2 —— 两个 SCF 解在廉价 GFN2-xTB 势能面上还分得开吗？

## 0. 一句话结论

把 37 个 `moread_lower` 格子各自的**两条 r2SCAN-3c 弛豫终点**（Stage 19）当作起点，各跑一次冻结 GFN2-xTB 弛豫后：**6 格两臂收敛到同一个极小点**（几何 RMSD ≤ 0.02 Å，即 `same_*`），**31 格仍是两个不同极小点**（`distinct_*`）；弛豫后 moread 腿仍更低的只有 **15 格**，而单点上 moread 更低、弛豫后不再更低（偏好反转）的有 **6 格**。与 Stage 19 的逐格裁决一致 **17/37（46%）**；但在**同一几何**上，xTB 与 ORCA 对「哪条腿更低」的判断一致 **33/37（89%）** —— 后者才是纯粹的「廉价 vs 昂贵」方法对照。

⚠️ 两个「一致率」含义不同：一个是**两套判据**之间的一致性（Stage 19 用电子身份，本节用几何），另一个是**同一几何上两种方法**的一致性——见 §4/§4b 与 §5，两者不可互相替代。

## 1. 口径

- 起点：Stage 19 两条腿各自的 r2SCAN-3c `Opt` 终点 `outputs/week18/orca_relax_<arm>/<name>/<name>_<state>_cpcm_<eps>_<arm>.xyz`，逐原子原样复制。
- 每个作业两步，全部冻结：**GFN2-xTB 单点**（起点几何上的廉价读数，`sp`）→ **GFN2-xTB `--opt`**（廉价弛豫）。电荷/多重度逐行取 Stage 19 台账，不写死。
- 确定性：`OMP_NUM_THREADS=1`；每次调用前清 xTB scratch，且每个作业独立目录（`electrolyte_ranking.xtb` 的既有实现）。
- **xTB 侧没有隐式溶剂**：`epsilon` 只是「起点几何来自哪个 CPCM 格子」的标签，不进入 xTB 作业。因此 §3 的按 `epsilon` 分层**不构成介电效应**，只是起点几何的分组。
- 判据（运行前固定）：`same_*` = xTB 弛豫后两臂 Kabsch RMSD ≤ 0.02 Å；`lower` = `xtb_relax_delta_ev < -0.001 eV`（与 Stage 19 同一 material 阈值）。
- **同一几何的方法对照**：`xtb_sp_delta_ev` 与 Stage 19 的 `relax_delta_ev` 读的是同一组几何（Stage 19 弛豫终点），差别只在方法，因此可以逐格比较「哪条腿更低」——这是本阶段最锐利的廉价 vs 昂贵检验（§4b）。
- 引擎：xTB 6.7.1pre，GFN2。

## 2. 逐格结果

| 分子 | 态 | eps | 子集 | xTB单点Δ(eV) | xTB弛豫Δ(eV) | Δ改变(eV) | 起始RMSD(Å) | 弛豫后RMSD(Å) | 漂移d/m(Å) | 结论 | S19裁决 | 一致 | S19弛豫Δ(eV) | 同几何一致 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| DEC | anion | 5 | holdout | 0.02732 | -0.02651 | -0.05384 | 0.3010 | 1.4001 | 1.100 / 0.937 | distinct_lower | distinct_higher | False | 0.02001 | True |
| DEC | anion | 20 | holdout | 0.02832 | -0.02716 | -0.05548 | 0.3157 | 1.4117 | 1.114 / 0.960 | distinct_lower | distinct_higher | False | 0.02371 | True |
| DEC | anion | 200 | holdout | 0.02939 | -0.02684 | -0.05623 | 0.3217 | 1.4141 | 1.121 / 0.974 | distinct_lower | distinct_higher | False | 0.02484 | True |
| DMC | cation | 5 | discovery | 0.00041 | -0.00002 | -0.00043 | 0.0031 | 0.0032 | 0.312 / 0.315 | same_higher | same_higher | True | -0.00004 | True |
| EC | cation | 5 | discovery | 0.00717 | -0.00001 | -0.00718 | 0.1003 | 0.1062 | 0.050 / 0.042 | distinct_higher | distinct_lower | False | -0.00972 | False |
| EC | cation | 7 | discovery | -0.00314 | -0.01055 | -0.00742 | 0.0790 | 0.0526 | 0.016 / 0.030 | distinct_lower | distinct_lower | True | -0.00398 | True |
| EC | cation | 10 | discovery | -0.00760 | -0.00001 | 0.00759 | 0.0666 | 0.1066 | 0.056 / 0.021 | distinct_higher | distinct_lower | False | -0.00110 | True |
| EC | cation | 14 | discovery | -0.00731 | 0.00001 | 0.00732 | 0.0402 | 0.1067 | 0.057 / 0.023 | distinct_higher | same_higher | False | -0.00021 | False |
| EC | cation | 20 | discovery | -0.00267 | -0.00000 | 0.00266 | 0.0205 | 0.1072 | 0.057 / 0.040 | distinct_higher | same_higher | False | 0.00004 | False |
| EMC | anion | 5 | discovery | -0.00000 | 0.00000 | 0.00000 | 0.0000 | 0.0001 | 1.191 / 1.191 | same_higher | same_higher | True | 0.00000 | True |
| EMC | anion | 20 | discovery | 0.02312 | -0.01325 | -0.03637 | 0.3069 | 1.6175 | 0.959 / 1.205 | distinct_lower | distinct_higher | False | 0.02402 | True |
| EMC | anion | 40 | discovery | -0.00000 | -0.00005 | -0.00005 | 0.0000 | 0.0027 | 1.217 / 1.218 | same_higher | same_higher | True | 0.00000 | True |
| EMC | anion | 80 | discovery | -0.00000 | -0.00001 | -0.00001 | 0.0000 | 0.0032 | 1.212 / 1.213 | same_higher | same_higher | True | 0.00000 | True |
| EMC | anion | 200 | discovery | 0.00000 | -0.00001 | -0.00001 | 0.0000 | 0.0009 | 1.207 / 1.208 | same_higher | same_higher | True | -0.00000 | True |
| EMC | anion | 1000 | discovery | 0.00000 | -0.00028 | -0.00028 | 0.0000 | 0.0138 | 1.206 / 1.211 | same_higher | same_higher | True | -0.00000 | True |
| PC | anion | 5 | discovery | 0.00937 | -0.03313 | -0.04250 | 0.4766 | 0.8078 | 0.415 / 0.452 | distinct_lower | distinct_higher | False | 0.00653 | True |
| PC | anion | 7 | discovery | 0.00993 | -0.03301 | -0.04294 | 0.4741 | 0.8094 | 0.414 / 0.453 | distinct_lower | distinct_higher | False | 0.00718 | True |
| PC | anion | 10 | discovery | 0.00978 | -0.03306 | -0.04284 | 0.4724 | 0.8087 | 0.413 / 0.452 | distinct_lower | distinct_higher | False | 0.00765 | True |
| PC | anion | 14 | discovery | 0.01011 | -0.03309 | -0.04320 | 0.4721 | 0.8050 | 0.413 / 0.451 | distinct_lower | distinct_higher | False | 0.00796 | True |
| PC | anion | 20 | discovery | 0.00989 | -0.03308 | -0.04297 | 0.4723 | 0.8047 | 0.413 / 0.450 | distinct_lower | distinct_higher | False | 0.00819 | True |
| PC | anion | 28 | discovery | 0.00989 | -0.03321 | -0.04309 | 0.4716 | 0.8076 | 0.408 / 0.450 | distinct_lower | distinct_higher | False | 0.00833 | True |
| PC | anion | 40 | discovery | 0.00975 | -0.03311 | -0.04286 | 0.4720 | 0.8046 | 0.411 / 0.450 | distinct_lower | distinct_higher | False | 0.00845 | True |
| PC | anion | 80 | discovery | 0.00991 | -0.03301 | -0.04292 | 0.4708 | 0.8003 | 0.416 / 0.450 | distinct_lower | distinct_higher | False | 0.00859 | True |
| PC | anion | 200 | discovery | 0.00992 | -0.03304 | -0.04296 | 0.4706 | 0.8010 | 0.414 / 0.450 | distinct_lower | distinct_higher | False | 0.00867 | True |
| PC | anion | 1000 | discovery | 0.00993 | -0.03308 | -0.04302 | 0.4705 | 0.8036 | 0.411 / 0.450 | distinct_lower | distinct_higher | False | 0.00871 | True |
| TEGDME | anion | 20 | holdout | -0.03267 | 0.10784 | 0.14052 | 2.2142 | 4.0312 | 1.521 / 2.945 | distinct_higher | distinct_lower | False | -0.06561 | True |
| TEGDME | anion | 200 | holdout | -0.34415 | 0.29370 | 0.63785 | 3.8527 | 3.2773 | 2.497 / 1.106 | distinct_higher | distinct_lower | False | -0.12994 | True |
| TMP | cation | 5 | discovery | 0.00018 | -0.00006 | -0.00024 | 0.7125 | 0.9418 | 0.646 / 0.646 | distinct_higher | distinct_higher | True | 0.00196 | True |
| TMP | cation | 7 | discovery | 0.00159 | -0.00015 | -0.00174 | 0.7300 | 0.9521 | 0.651 / 0.655 | distinct_higher | distinct_higher | True | 0.00145 | True |
| TMP | cation | 10 | discovery | 0.00439 | 0.00021 | -0.00417 | 0.7436 | 0.9469 | 0.673 / 0.657 | distinct_higher | distinct_higher | True | 0.00171 | True |
| TMP | cation | 14 | discovery | 0.00479 | 0.00005 | -0.00474 | 0.7511 | 0.9573 | 0.673 / 0.658 | distinct_higher | distinct_higher | True | 0.00151 | True |
| TMP | cation | 20 | discovery | 0.00474 | -0.00002 | -0.00476 | 0.7556 | 0.9596 | 0.674 / 0.659 | distinct_higher | distinct_higher | True | 0.00137 | True |
| TMP | cation | 28 | discovery | 0.00456 | -0.00018 | -0.00474 | 0.7586 | 0.9563 | 0.675 / 0.659 | distinct_higher | distinct_higher | True | 0.00127 | True |
| TMP | cation | 40 | discovery | 0.00466 | -0.00021 | -0.00487 | 0.7606 | 0.9557 | 0.677 / 0.659 | distinct_higher | distinct_higher | True | 0.00119 | True |
| TMP | cation | 80 | discovery | -0.00391 | -0.00010 | 0.00381 | 0.7624 | 0.9595 | 0.651 / 0.662 | distinct_higher | distinct_higher | True | -0.00026 | False |
| TMP | cation | 200 | discovery | 0.00437 | -0.00001 | -0.00438 | 0.7647 | 0.9608 | 0.679 / 0.662 | distinct_higher | distinct_higher | True | 0.00107 | True |
| TMP | cation | 1000 | discovery | 0.00431 | -0.00004 | -0.00435 | 0.7653 | 0.9606 | 0.679 / 0.662 | distinct_higher | distinct_higher | True | 0.00104 | True |

## 3. 分层

### 按电子态

| 组 | n | 仍两个极小点 | 合并为一 | moread仍更低 | 偏好反转 | 单点Δ绝对值中位(eV) | 弛豫Δ绝对值中位(eV) | 弛豫后RMSD中位(Å) | 与S19一致 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| anion | 21 | 16 | 5 | 14 | 2 | 0.00991 | 0.03301 | 0.8050 | 5/21 |
| cation | 16 | 15 | 1 | 1 | 4 | 0.00438 | 0.00004 | 0.9495 | 12/16 |

### 按分子

| 组 | n | 仍两个极小点 | 合并为一 | moread仍更低 | 偏好反转 | 单点Δ绝对值中位(eV) | 弛豫Δ绝对值中位(eV) | 弛豫后RMSD中位(Å) | 与S19一致 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| DEC | 3 | 3 | 0 | 3 | 0 | 0.02832 | 0.02684 | 1.4117 | 0/3 |
| DMC | 1 | 0 | 1 | 0 | 0 | 0.00041 | 0.00002 | 0.0032 | 1/1 |
| EC | 5 | 5 | 0 | 1 | 3 | 0.00717 | 0.00001 | 0.1066 | 1/5 |
| EMC | 6 | 1 | 5 | 1 | 0 | 0.00000 | 0.00003 | 0.0029 | 5/6 |
| PC | 10 | 10 | 0 | 10 | 0 | 0.00990 | 0.03308 | 0.8048 | 0/10 |
| TEGDME | 2 | 2 | 0 | 0 | 2 | 0.18841 | 0.20077 | 3.6542 | 0/2 |
| TMP | 10 | 10 | 0 | 0 | 1 | 0.00438 | 0.00008 | 0.9568 | 10/10 |

### 按起点来源的介电常数（不是溶剂效应）

| 组 | n | 仍两个极小点 | 合并为一 | moread仍更低 | 偏好反转 | 单点Δ绝对值中位(eV) | 弛豫Δ绝对值中位(eV) | 弛豫后RMSD中位(Å) | 与S19一致 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 10.0 | 3 | 3 | 0 | 1 | 1 | 0.00760 | 0.00021 | 0.8087 | 1/3 |
| 1000.0 | 3 | 2 | 1 | 1 | 0 | 0.00431 | 0.00028 | 0.8036 | 2/3 |
| 14.0 | 3 | 3 | 0 | 1 | 1 | 0.00731 | 0.00005 | 0.8050 | 1/3 |
| 20.0 | 6 | 6 | 0 | 3 | 2 | 0.01651 | 0.02021 | 1.1856 | 1/6 |
| 200.0 | 5 | 4 | 1 | 2 | 1 | 0.00992 | 0.02684 | 0.9608 | 2/5 |
| 28.0 | 2 | 2 | 0 | 1 | 0 | 0.00722 | 0.01670 | 0.8820 | 1/2 |
| 40.0 | 3 | 2 | 1 | 1 | 0 | 0.00466 | 0.00021 | 0.8046 | 2/3 |
| 5.0 | 6 | 4 | 2 | 2 | 0 | 0.00379 | 0.00004 | 0.4570 | 3/6 |
| 7.0 | 3 | 3 | 0 | 2 | 0 | 0.00314 | 0.01055 | 0.8094 | 2/3 |
| 80.0 | 3 | 2 | 1 | 1 | 1 | 0.00391 | 0.00010 | 0.8003 | 2/3 |

### 按发现/留出臂

| 组 | n | 仍两个极小点 | 合并为一 | moread仍更低 | 偏好反转 | 单点Δ绝对值中位(eV) | 弛豫Δ绝对值中位(eV) | 弛豫后RMSD中位(Å) | 与S19一致 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| discovery | 32 | 26 | 6 | 12 | 4 | 0.00470 | 0.00016 | 0.8048 | 17/32 |
| holdout | 5 | 5 | 0 | 3 | 2 | 0.02939 | 0.02716 | 1.4141 | 0/5 |

## 4. 与 Stage 19 的裁决对照

行 = Stage 19 的电子裁决（`charge_l1`，冻结阈值 0.039）；列 = 本阶段 xTB 的几何裁决（RMSD ≤ 0.02 Å 记 `same_*`）。对角线 17/37 即 §0 的一致率。

| Stage 19 \ Part 2 | distinct_lower | distinct_higher | same_lower | same_higher |
| --- | --- | --- | --- | --- |
| distinct_lower | 1 | 4 | 0 | 0 |
| distinct_higher | 14 | 10 | 0 | 0 |
| same_lower | 0 | 0 | 0 | 0 |
| same_higher | 0 | 2 | 0 | 6 |

### 4b. 同一几何上的方法对照（xTB 单点 vs ORCA r2SCAN-3c）

`xtb_sp_delta_ev` 与 Stage 19 的 `relax_delta_ev` 读的是**同一组几何**（Stage 19 的弛豫终点），差别只在方法。以同一 material 阈值（-0.001 eV）判定「哪条腿更低」，两者一致 **33/37（89%）**。

不一致的 4 格：ORCA 侧「弛豫 Δ」绝对值最大 0.00972 eV，其中 3 格本身就在 material 阈值带（≤ 0.001 eV）里 —— 分歧集中在昂贵方法自己都判不动的近简并格子上。

| 分子 | 态 | eps | xTB单点Δ(eV) | ORCA弛豫Δ(eV) |
| --- | --- | --- | --- | --- |
| EC | cation | 5 | 0.00717 | -0.00972 |
| EC | cation | 14 | -0.00731 | -0.00021 |
| EC | cation | 20 | -0.00267 | 0.00004 |
| TMP | cation | 80 | -0.00391 | -0.00026 |

## 5. 读法纪律

- 两边的 `distinct` **不是同一个判据**：Stage 19 用冻结的电子身份阈值 `charge_l1 > 0.039`；本阶段只有廉价优化器能给的**几何**（RMSD ≤ 0.02 Å）。§4 的 outcome 一致率是两套判据之间的一致性，不是同一判据的重复测量；把它与 §4b 的同一几何方法一致率混为一谈是错的。
- 本节所有比例都**条件在「Stage 19 单点上两解不同且 moread 更低」这 37 格**上；它们不是 414 格总体的发生率。
- **不重算** τ_b / Top-k / `f_unresolved`：那是本阶段 Part 1 （`stage20_relax_rung_*`）的事，且本子集是选择出来的，任何总体排序统计都会有选择偏差。
- xTB 作业是**气相**的（无 CPCM），而 Stage 19 是 CPCM(epsilon)。这是廉价方法本身的差异，属于本阶段要测量的对象之一，不是可控变量；因此 `epsilon` 在本节只标记起点来源。
- `0.02 Å` 与 `0.001 eV` 均为**运行前固定**的描述性阈值，未做任何事后调参。

