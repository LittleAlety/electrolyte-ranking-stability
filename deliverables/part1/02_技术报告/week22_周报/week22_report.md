# Week 22 成果小结 —— Stage 23（批次 B：热修正抽样 + 导体极限诊断 + NEB 精修）

Week 22 执行 `docs/31_plan_revision_expert_review.md` 的批次 B：**R9、R4b、R11**，
外加一项对 Week 21 σ 相图边界的网格分辨率复核。与批次 A 不同，本周**有新增电子结构**：
24 个 GFN2-xTB `--ohess`、54 个 eps = 1e6 的裸 CPCM 单点、以及三格真 NEB；
几何一律复用冻结 G1 或 Stage 19 的弛豫终点，**没有任何一步重新优化几何**。

> 周内最不可回避的一条更正是能量尺子对几何尺子的：R11 用真 NEB 取代直线插值之后，
> Stage 19 用 0.02 A 的 RMSD 阈值判成「两个独立解」的 EC/阳离子/eps=5 一格，
> 其最小能量路径上的峰高只有 **0.141 meV**——比 k_B T 小 182 倍，两端点就是**同一个盆地**。
> 直线插值给出的 4.245 meV 已经只是上界，几何阈值则连方向都判错了。

完整版本见 `week22_report_full.md`。

## 1. 本周做了什么

R9：8 个分子 x 3 个电荷态的 GFN2-xTB `--ohess` 热修正抽样（24 个作业，几何一律复用冻结 G1，不重新优化）。R4b：18 分子 x 3 态、eps = 1e6 的裸 CPCM 单点（54 行）补齐导体极限，与既有的 eps = 5/7/10/14/20/28/40/80/200/1000 网格合成一条扫描。R11：Stage 19 三格临界格的真 NEB 精修（端点不重优化，峰高取自 ORCA 的 `<stem>.final.interp`）。另加一项对 Week 21 σ 相图 6 条边界的一步长方格分辨率复核（零新增计算）。

## 2. 关键数字

R9 的热修正分子间离散度 std 是 0.0581 / 0.0775 eV，只有同轴 delta_m 的 **8.3% / 3.7%**；R4b 把「介电层免费」量化成 `abs(dE) x eps = 2057-2178 meV` 的幂律（prefactor 约 2.13 eV/eps），eps = 200 的残余最大 19.62 meV（PC / anion），是氧化轴 delta_m 的 **2.80%**；R11 用真 NEB 读到 EC/cation/5 的峰高只有 **0.000141 eV**，是直线界 0.00424 eV 的 1/30.0，比 k_B T = 0.0257 eV 小 182 倍——2 个取得判决的格子全部落在 1 kT 以下，与 Stage 19 的 RMSD 判决冲突 1 格。

## 3. R9：把「没算过热修正」变成「算过、且有界」

| 轴 | mean thermal_G (eV) | std | min | max | max abs | mean thermal_H (eV) | 相对 delta_m |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 氧化 | -0.1350 | **0.0581** | -0.2635 | -0.0633 | 0.2635 | -0.1421 | 8.3% |
| 还原 | 0.1950 | **0.0775** | 0.1158 | 0.3180 | 0.3180 | 0.1878 | 3.7% |

对照冻结的 **delta_m**（`outputs/week6/delta_m_frozen.json`）：氧化 0.700 eV、还原 2.074 eV。

> 结论不是「热修正很小」，而是「热修正的**分子间离散度**比同一轴的 delta_m 低一个数量级，
> 所以整项略去不会改变任何排序结论」。限制与数字同时引用：带电态 Hessian 取在中性 G1 几何上。

## 4. R4b：裸 CPCM 的导体极限（附加诊断）

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

相对 **eps = 200**：36 个 (分子, 电荷态) 组合，`|dE|` 最大 **19.62 meV**（PC / anion）、平均 10.81 meV，是氧化轴 delta_m 的 **2.80%**；相对 **eps = 1000** 最大只剩 **3.929 meV**。
逐分子一致性：53 个组合的 `dE` 随 eps 单调下降，例外是 EMC / anion（最大回跳 221.0 meV），属阴离子 SCF 在不同 eps 上落到不同解分支的求解器伪迹，不是介电残差。

> **不属预注册扫描集**（预注册网格是 `[5, 10, 20, 40]`）；它既不改 `rank`，也不改 `delta_m` / `sigma`。
> 它给出的是一条可以提前使用的量：`abs(dE(eps)) ~ 2.1 eV / eps`。

## 5. R11：真 NEB 取代直线插值上界

| 格 | Stage 19 (RMSD) | RMSD (A) | 直线界 (eV) | **NEB 峰高 (eV)** | 直线/NEB | NEB 判决 | 与 Stage 19 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| EC/cation/5 | distinct_lower | 0.100 | 0.00424 | **0.000141** | 30.00 | one_basin | **冲突** |
| EC/cation/20 | same_higher | 0.021 | 0.00001 | **0.000053** | 0.15 | one_basin | 一致 |
| TEGDME/anion/20 | distinct_lower | 2.214 | 66.14456 | **0.679417** | 97.35 | separated | 一致 |

判据（Stage 21 内部双侧口径，**不回溯改写 Stage 19**）：`<= 1 kT = 0.0257 eV` -> `one_basin`，`>= 1 kcal/mol = 0.043364 eV` -> `separated`，之间 `inconclusive`。

> 阈值沿用 Stage 21 的内部双侧判据，**不回溯改写** Stage 19 的既有判决；
> 本轮 NEB 是 regular（`climbing : no`）而非 climbing-image，峰高只作「有没有峰」的判读。

## 6. Week 21 边界的网格分辨率复核

| 轴 | 指标 | 阈值 | 源陈述 (eV) | 插值 (eV) | 偏差 (eV) | 偏差 / 网格步长 |
| --- | --- | --- | --- | --- | --- | --- |
| oxidation | tau_b_mean | 0.8 | 0.4500 | 0.4416 | -0.0084 | -0.17 |
| oxidation | tau_b_mean | 0.5 | 1.2000 | 1.1532 | -0.0468 | -0.94 |
| oxidation | overlap_mean | 1.0 | 0.2500 | 0.2000 | -0.0500 | -1.00 |
| reduction | tau_b_mean | 0.8 | 0.2500 | 0.2456 | -0.0044 | -0.09 |
| reduction | tau_b_mean | 0.5 | 0.7000 | 0.6529 | -0.0471 | -0.94 |
| reduction | overlap_mean | 1.0 | 0.1000 | 0.0500 | -0.0500 | -1.00 |

网格步长 0.05 eV；6 条边界全部 `reproduces_source = True`，最大偏差 0.0500 eV = 1.00 个网格步长。结论：Week 21 的边界是「一步长」级的陈述，但没有变成网格假象；引用时应写成 +- 0.05 eV。

## 7. 文件清单

| 文件 | 内容 |
| --- | --- |
| `thermal_correction_sample.json` / `.csv` / `.md` | R9：8 分子 x 3 电荷态的 GFN2-xTB `--ohess` 热修正抽样（24 个作业，几何复用冻结 G1），含逐分子 dH / dG / dZPE 与两轴的 mean / std / max abs。 |
| `dielectric_limit.json` / `.csv` / `.md` | R4b：裸 CPCM 的导体极限诊断（eps = 5..1e6，54 个单点；含 1/eps 幂律、与 delta_m 的比值、逐分子单调性例外清单）。 |
| `neb_refinement.json` / `.csv` / `.md` | R11：三格 NEB 精修的收敛路径、峰高、直线/真路径比值、两侧判据下的一致/冲突清单。 |
| `sigma_boundary_resolution.json` / `.md` | Week 21 σ 相图 6 条边界的一步长方格分辨率复核（零新增计算）。 |

## 8. QC 与限制

- R9：24/24 个 `--ohess` 作业完成；R4b：54/54 个 eps = 1e6 单点 TERMINATED NORMALLY、无一个未收敛；R11：3/3 格拿到收敛路径，峰高由 `.final.interp` 读出并与 `.out` 的 HEI 块交叉校验；网格复核：6/6 条边界复现源陈述。
- **限制**：R9 的带电态 Hessian 取在**中性 G1 几何**上（16 个带电作业里 2 个报出虚频），所以它给出的是「被略去的热修正有多大」的量级上界，不是热化学可观测量；R4b 的 eps = 80/200/1000/1e6 全部**不属预注册扫描集**，不参与任何冻结量，且 eps = 1e6 是「近似导体」而非严格导体边界条件；R11 是 **regular NEB（climbing : no）**，峰高只作「有没有峰」的判读，且阈值**不回溯改写** Stage 19 的判决。

## 9. 本周产物

- `artifacts/F43_dielectric_limit_check.png`
- `artifacts/F44_neb_refinement.png`
- `artifacts/figure_manifest_week22_stage23.md`
- `dielectric_limit.csv`
- `dielectric_limit.json`
- `dielectric_limit.md`
- `neb_refinement.csv`
- `neb_refinement.json`
- `neb_refinement.md`
- `sigma_boundary_resolution.json`
- `sigma_boundary_resolution.md`
- `thermal_correction_sample.csv`
- `thermal_correction_sample.json`
- `thermal_correction_sample.md`
- `week22_report_full.md`

## 10. 缺失源

- 无（全部源路径均存在）
