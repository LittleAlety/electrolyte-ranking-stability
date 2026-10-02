# Week 22 报告（Stage 23：批次 B）

> 上游：`docs/31_plan_revision_expert_review.md` 的「批次 B」——`R9`（xTB 热修正抽样）、`R4b`（一格导体极限，附加诊断）、`R11`（NEB 精修 2-3 格）。
> 本文件由 `scripts/gen_week22_report.py` 从 `outputs/week22/` 的产物渲染；`--check` 逐字节复核。

---

## 0. 一句话结论

R11 用真 NEB 取代直线插值之后，Stage 19 判成「两个盆地」的 EC/阳离子/eps=5 一格峰高只有 0.141 meV（直线界 4.245 meV 的 1/30），两端点就是同一个盆地——0.02 A 的 RMSD 一刀切在这一格误判；同周 R4b 又把「介电层免费」量化成一条 |dE| x eps = 2.1 eV 的幂律，eps = 200 的残余只剩 19.6 meV，是氧化轴 delta_m 的 2.80%。

---

## 1. R9：热修正抽样（8 个分子 x 3 态，xTB `--ohess`）

- 抽样 8 个分子（覆盖 7 个家族，含氟代溶剂 FEC），几何**复用** P0/P1/P2 共享的冻结 G1，不重新优化
- 作业 24 个 `--ohess`；定义 `thermal_G = dG - dE`、`thermal_H = dH - dE`（同一对电荷态，eV）

| 轴 | mean thermal_G (eV) | std | min | max | max abs | mean thermal_H (eV) |
| --- | --- | --- | --- | --- | --- | --- |
| 氧化 | -0.1350 | **0.0581** | -0.2635 | -0.0633 | 0.2635 | -0.1421 |
| 还原 | 0.1950 | **0.0775** | 0.1158 | 0.3180 | 0.3180 | 0.1878 |

对照冻结的 **delta_m**（`outputs/week6/delta_m_frozen.json`）：氧化 0.700 eV、还原 2.074 eV。
热修正本身的**分子间离散度**只有 0.0581 / 0.0775 eV，是 delta_m 的 **8.3% / 3.7%**——低一个数量级。
即：把热修正整项略去，不会改变任何排序结论。R9 要的不是「热修正很小」，而是把「没算过」变成「算过、且有界」。

**限制（必须与数字同时引用）**：带电态的 Hessian 取在**中性 G1 几何**上，不是它自己的极小点；16 个带电作业里有 2 个报出虚频。因此上表是「被略去的热修正有多大」的**量级上界**，不是热化学可观测量。原始 xTB 文本在 `outputs/week22/raw/<mol_id>/<state>_ohess.out`。

---

## 2. R4b：裸 CPCM 的导体极限（附加诊断）

> **不属预注册扫描集。** 预注册的介电网格是 `[5, 10, 20, 40]`（`config/scientific_definitions.yaml` 的 `STAGE0_ARTEFACTS`），`prereg.yaml` 是 append-only。本节的 eps = 80 / 200 / 1000 / 1e6 全部是**附加诊断**，不参与任何冻结量。

- 全部是单点，几何一律复用冻结 G1；作业数 54（18 分子 x 3 态）
- 问的问题：屏蔽项是**一路变到导体极限**，还是**早就饱和**？

### 2.1 结论一：不是饱和，是 1/eps 幂律

| eps | 平均 abs(dE) vs eps=1e6 (meV) | abs(dE) x eps (meV) |
| --- | --- | --- |
| 5 | 420.53 | 2103 |
| 7 | 297.96 | 2086 |
| 10 | 207.61 | 2076 |
| 14 | 146.93 | 2057 |
| 20 | 107.41 | 2148 |
| 28 | 77.80 | 2178 |
| 40 | 53.90 | 2156 |
| 80 | 27.00 | 2160 |
| 200 | 10.81 | 2162 |
| 1000 | 2.16 | 2162 |

`abs(dE) x eps` 从 eps = 7 一路到 eps = 1000 都是常数（2057 - 2178 meV），即残余几乎严格按 **1/eps** 衰减，prefactor 约 **2.13 eV/eps**。
- **逐分子一致性**：53/54 个 (分子, 电荷态) 的 `dE` 随 eps 单调下降；例外是 **EMC / anion**（覆盖 eps = 5,7,10,14,20,28,40,80,200,1000,1e6），最大回跳 **221.0 meV**。这是阴离子 SCF 在不同 eps 上落到不同解分支造成的**求解器伪迹，不是介电残差**；该行不进入上面的幂律判决量、也不进入任何冻结量，但必须与幂律同时引用。

这条幂律把「离导体极限还有多远」变成**可以在花钱之前算出来**的量：`abs(dE(eps)) ~ 2.13 eV / eps`。这也解释了为什么 eps = 5 到 40 那一档（Stage 12/13 用的正是这一档）在数值上看起来「怎么换都差不多」——它们的残余本来就只有 0.42 到 0.054 eV，且**同号、单调**。

### 2.2 结论二：残余相对 delta_m 小 1-2 个数量级

- 相对 **eps = 200**：36 个 (分子, 电荷态) 组合，`|dE|` 最大 **19.62 meV**（PC / anion）、平均 10.81 meV
- 相对 **eps = 1000**：最大只剩 **3.929 meV**
- 相对 **eps = 200** 这一列，所有 `dE` **同号**且为正（最小 1.04 meV）：深屏蔽把能量单调往下拉，这一列上看不到振荡
- 判决：**尚未饱和**（eps = 200 还剩 19.62 meV，按 1/eps 幂律要跑到 eps ~ 1e4 才压到 1 meV 以下），但 eps = 200 的残余只有氧化轴 delta_m（700.2 meV）的 **2.80%**、还原轴 delta_m（2074.3 meV）的 **0.95%**。

也就是说：介电层**不是严格免费**，但它的残余比排序论证关心的尺度小 1-2 个数量级。Stage 12/13 从**位移结构**论证「介电层免费」，本节从**绝对能量**独立复核同一命题，结论一致但用的不是同一个可观测量，所以这不是重复计算。

![F43](figures/F43_dielectric_limit_check.png)

**R4b（附加诊断，不属预注册扫描集 [5,10,20,40]）—— 裸 CPCM 离导体极限还有多远。**(a) 36 个 (分子, 电荷态) 组合上，`|E(eps) - E(1e6)|` 的均值随 eps 下降；它不是「饱和」，而是**几乎严格的 1/eps 幂律**：`|dE| x eps = 2057-2178 meV`，prefactor 约 **2.1 eV/eps**，从 eps = 7 一路测到 eps = 1000 都成立。这条律把「离导体极限还差多少」变成**可以提前算出来**的量。(b) eps = 200 时的逐分子残余：最大 **19.62 meV**（PC / anion），平均 10.81 meV；相对 eps = 1000 时最大只剩 **3.929 meV**。作为参照，冻结的决策容差 delta_m 是氧化 700 meV / 还原 2074 meV，所以 eps = 200 的残余只有它的 **2.80% / 0.95%** —— 介电层**不是严格免费**，但残差比排序论证关心的尺度小 1-2 个数量级，Stage 12/13 的「介电层免费」在实用精度上量化成立。逐分子一致性：53/54 个组合的 `dE` 随 eps 单调下降，例外 EMC/anion —— 阴离子 SCF 在不同 eps 上落到不同解分支的求解器伪迹，不是介电残差，已在该行的分析里单独标出。

---

## 3. R11：NEB 精修（`docs/31` 批次 B 的最后一项）

- 反应物 = Stage 19 `default` 臂弛豫终点，产物 = Stage 19 `moread` 臂弛豫终点，**端点不重新优化**（所以比较的正是 Stage 19 判决所依据的那两个终点）
- 中间像数取自各格 ORCA 输入：EC/cation/5 = 8，EC/cation/20 = 8，TEGDME/anion/20 = 2（加 2 个端点即该格镜像总数）；**regular (climbing : no)**
- 峰高从 ORCA 自带的收敛路径文件 `<stem>.final.interp` 读（能量相对反应物、全精度），`.out` 的 `INFORMATION ABOUT HIGHEST ENERGY IMAGE` 块作独立交叉校验
- 判据沿用 Stage 21 的**双侧口径**（`<= 1 kT = 0.0257 eV` -> `one_basin`；`>= 1 kcal/mol = 0.043364 eV` -> `separated`；之间 `inconclusive`），**不回溯改写 Stage 19 的既有判决**

| 格 | Stage 19 (RMSD) | RMSD (A) | Stage 21 直线界 (eV) | NEB 峰高 (eV) | 直线高估 | NEB 判决 | 力判据 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| EC/cation/5 | distinct_lower | 0.100 | 0.00424 | **0.000141** | 30.0x | one_basin | 达标 |
| EC/cation/20 | same_higher | 0.021 | 0.00001 | **0.000053** | 0.2x | one_basin | 未知 |
| TEGDME/anion/20 | distinct_lower | 2.214 | 66.14456 | **0.679417** | 97.4x | separated | 未达标 |

最高的一格是 **TEGDME/anion/20 = 0.679417 eV**（`separated`），最低的一格是 **EC/cation/20 = 0.000053 eV**（`one_basin`）；判决计数：`one_basin` 2 格、`separated` 1 格、`inconclusive` 0 格。
落在 1 kT（0.0257 eV）以下的格子：EC/cation/5、EC/cation/20 —— 这些格子的两条臂终点在能量上就是同一个盆地。
越过 1 kcal/mol（0.043364 eV）的格子：TEGDME/anion/20 —— 该格**不是**同一个盆地，与 Stage 19 对该格的几何判决方向一致。
直线插值确实只是上界，但**松紧不是全局常数**：在高于 1 kT 的格子上，直线界把峰高放大了 97.4 倍（TEGDME/anion/20）。因此不能用某一个格子的直线计算外推别的格子。

### 3.1 与 Stage 19 的一致 / 冲突清单

- 一致（2 格）：EC/cation/20、TEGDME/anion/20
- 冲突（1 格）：EC/cation/5

**冲突：EC/cation/5。** Stage 19 判 `distinct_lower`（RMSD 0.100 A，越过 0.02 A 阈值），但真 NEB 路径的峰高只有 **0.000141 eV**，比 1 kT 还小 182 倍，两端点**就是同一个盆地**。
即 0.02 A 的一刀切在这一格**误判**：0.100 A 的端点位移沿路径被摊成 0.319 A，位移本身不小，但方向上**不构成势垒**。这说明 RMSD 作为「是否同一盆地」的代理，在 0.02-0.10 A 这一段带内失效。

![F44](figures/F44_neb_refinement.png)

**R11 —— 用真 NEB 取代直线插值上界。** 反应物/产物 = Stage 19 两条臂的弛豫终点（端点不重优化），regular (climbing : no)（中间像数：EC/cation/5 = 8，EC/cation/20 = 8，TEGDME/anion/20 = 2）。峰高从 ORCA 的 `<stem>.final.interp` 读，全精度。(a)-(c) 三条收敛路径，能量相对反应物，1 kT 与 1 kcal/mol 画成横线；(d) 直线界 vs 真 NEB 的对数柱状图。EC/cation/5：直线 0.00424 eV -> NEB **0.000141 eV**（one_basin，直线/NEB = 30.00） EC/cation/20：直线 0.00001 eV -> NEB **0.000053 eV**（one_basin，直线/NEB = 0.15） TEGDME/anion/20：直线 66.14456 eV -> NEB **0.679417 eV**（separated，直线/NEB = 97.35）2 格落在 1 kT 以下（`one_basin`）：EC/cation/5、EC/cation/20；1 格高于 1 kcal/mol（`separated`）：TEGDME/anion/20。直线界把峰高放大了最多 97.4 倍（TEGDME/anion/20）；EC/cation/20 的直线界与 NEB 峰高两侧都落在 ~1e-5 eV 的噪声底，比值没有判别意义。与 Stage 19 的 RMSD 判决**冲突**的格子：EC/cation/5。**力判据未达标**（撞 `MaxIter` 后正常终止，峰高只能按未收敛上界读）：TEGDME/anion/20。

### 3.2 限制（必须与数字同时引用）

1. **regular NEB 不是 climbing-image**：常规弹性带会把尖峭鞍点抹圆，峰高因此偏小。判 `one_basin` 的两格，峰高比 1 kT 小 2 个数量级以上；判 `separated` 的一格，峰高比 1 kcal/mol 高 1 个数量级以上。两个方向的误差都不改变判决。
2. **只精修 3 格（抽样）**：5 个 EC/阳离子临界格里只扫了 eps = 5 与 20 两端，eps = 7/10/14 三格**仍是 Stage 19 的旧判决**，报告不得暗示扫过。
3. **端点不重新优化**：这是刻意的——要让本轮判决直接对上 Stage 19 判决所依据的那两个终点。
4. **TEGDME/anion/20 未达 ORCA 自己的 NEB 力判据**：该格在 `MaxIter` 处**正常终止**，最后一次力表为 `RMS(Fp) = 1.0081e-03`（目标 5.0e-04，判 NO）、`MAX(|Fp|) = 5.3259e-03`（目标 1.0e-03，判 NO），且迭代过程中峰高一直在下降（迭代 0 的 3.204 eV 一路降到 0.30 eV 量级）。因此该格的峰高是**未收敛的上界**，**不是**收敛峰高。两种读法——插值上界 0.679 eV、`HEI` 像能量 0.302 eV——都仍比 1 kcal/mol（0.0434 eV）高 7 倍以上，所以 `separated` 这一**判决**稳健；但**数值**不得当作收敛峰高引用。

---

## 4. Week 21 对抗式复检：相图边界是不是网格假象？

- 对象：`analyze_sigma_synthetic.py` 报出的 `std_where_mean_tau_b_below_0p8`（氧化 0.45 eV）、`below_0p5`（1.20 eV）以及 overlap 的 0.25 / 0.10
- 机制：`boundary()` 返回的是**第一个穿越阈值的网格点**，`STD_GRID` 步长 0.05 eV，所以这个数字天然被量化到一个步长
- 做法：从**同一份已保存的曲线**（`outputs/week21/sigma_synthetic.json`，每轴 41 个网格点）做线性插值求穿越点，**不重抽样**

| 轴 | 判据 | 源文件报出 | 网格点 | 括住的区间 (eV) | 插值穿越 (eV) | 偏差 (步长) |
| --- | --- | --- | --- | --- | --- | --- |
| oxidation | tau_b_mean_below_0p8 | 0.450000 | 0.450000 | 0.40 - 0.45 | 0.4416 | -0.17 |
| oxidation | tau_b_mean_below_0p5 | 1.200000 | 1.200000 | 1.15 - 1.20 | 1.1532 | -0.94 |
| oxidation | overlap_mean_below_1 | 0.250000 | 0.250000 | 0.20 - 0.25 | 0.2000 | -1.00 |
| reduction | tau_b_mean_below_0p8 | 0.250000 | 0.250000 | 0.20 - 0.25 | 0.2456 | -0.09 |
| reduction | tau_b_mean_below_0p5 | 0.700000 | 0.700000 | 0.65 - 0.70 | 0.6529 | -0.94 |
| reduction | overlap_mean_below_1 | 0.100000 | 0.100000 | 0.05 - 0.10 | 0.0500 | -1.00 |

插值穿越点与网格点的最大偏差 **0.0500 eV**，即 **1.00 个网格步长**。
判决：边界确实是一个「一步长」级别的陈述，但**没有变成网格假象**——插值后的穿越点仍落在原报出网格点的相邻一步之内，所以 `0.45 / 1.20 / 0.25 / 0.70` 那组数字可以继续用，只是引用时必须写成 `+/- 0.05 eV`。

**限制**：插值假设 `tau_b(std)` 在相邻网格点之间近似线性；曲线单调（秩相关 -1.000），但没有理由严格线性，所以插值值只能读作「量级正确」。本复检**不重抽样**，Monte-Carlo 误差原样继承；结论**不回写** `outputs/week21/`。

---

## 5. 与冻结件的关系

- `config/prereg.yaml`：**0 改动**
- `config/scientific_definitions.yaml`：**0 改动**
- `data/anchors/solution_redox_anchors.csv`：**0 改动**
- R4b 的 eps = 80/200/1000/1e6 与 R11 的 1 kT / 1 kcal/mol 阈值都按 `docs/31` 的默认裁决**不进 prereg**：它们分别被登记为「附加诊断」与「本阶段内部判据、不回溯改写 Stage 19」。
因此本报告的数字可以与 Week 4-21 的结果直接比较，不需要口径护身符。

## 6. Gate 状态

Gate 0 CLOSED、Gate 1 NOT CLOSED。

Gate 0 保持 CLOSED 的理由与 Week 21 相同：本周只新增诊断与精修，没有一条改动落进目标量、family 定义、筛选方向、delta_m、k/N、种子集或 splits。Gate 1 的唯一 blocker 也仍然是 `data/anchors/solution_redox_anchors.csv` 的 31 行 `method=est`——那是 R7 的对象，而 R7 属批次 C，需**先完成文献核验 + PI 裁决**，本轮未执行。

## 7. 产物清单

| 产物 | 内容 |
| --- | --- |
| `outputs/week22/thermal_correction_sample.{json,csv,md}` | R9 的 24 个作业与离散度统计 |
| `outputs/week22/raw/<mol_id>/<state>_ohess.out` | R9 的原始 xTB 文本 |
| `outputs/week22/dielectric_limit.{json,csv,md}` | R4b 的逐分子逐态残余与 1/eps 幂律 |
| `outputs/week22/neb_refinement.{json,csv,md}` | R11 的路径、峰高与一致/冲突清单 |
| `outputs/week22/sigma_boundary_resolution.{json,md}` | Week 21 边界网格分辨率复检 |
| `outputs/week22/neb_example_EC_cation_eps5/` | 交给 PI 自行运行的那一格（输入 + 端点 + 说明） |
| `outputs/week22/neb_EC_cation_eps20/`、`outputs/week22/neb_TEGDME_anion_eps20/` | 另外两格 |
| `outputs/figures/F43_dielectric_limit_check.png` | 导体极限图 |
| `outputs/figures/F44_neb_refinement.png` | NEB 精修图 |
