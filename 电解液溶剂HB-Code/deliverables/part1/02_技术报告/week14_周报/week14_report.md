# Week 14 成果小结 —— Stage 15（双初猜协议、电子弥散度描述符与溶液锚点扫描）

## 0. 一页结论
- 做了什么：把 Stage 14 留下的开口一次收掉：(1) **双初猜协议**——对 EMC / DMC / EC 在十点介电阶梯（5/7/10/14/20/28/40/80/200/1000）上各跑两遍（ORCA 默认初猜 vs `! MORead` 气相 MO 重启），99 个新作业；(2) **导体极限**——补 `eps = 1000`（`x = 0.999`）实测点；(3) **弥散度描述符**——从六层 bare-CPCM 的 Mulliken 自旋布居构造 7 个新量并重跑 Stage 14 的归因（**0 个新作业**）；(4) **文献扫描**——对 13 篇在手 PDF 做机器可核查的锚点否证（**0 个新作业**）。
- 关键数字：90 个点里 78 个在收敛精度内一致、**12 个超过 1 meV 且全部为负**、反向 0 次，最大惩罚 **0.2860 eV**；EMC 还原轴九点 Born R2 **0.6788 -> 0.9556**、符号变化 4 -> 0、偶极粗糙度 1.991 -> 0.084，修复后偶极严格单调（rho = 1.000）；eps = 200 -> 1000 只走 **0.0113 eV**，而六点缺口 +0.0332 -> -0.0308 eV（**没有变小**）；阴离子畸变惩罚的最佳留一 R2 **0.162 -> 0.556**（spin_maxfrac，rho = +0.811），中性与阳离子的 `delta_loo_r2` 都为 0；31 行锚点里 4 行可裁定、3 改 1 确认，Gate 1 仍 NOT CLOSED。
- 质检：99 个作业 0 失败、0 QC flag、11 层各 9/9 ok；Stage 14 的九点 R2 0.6788 与符号变化 4 被逐位复现；Week 12 的 33.2 meV worst case 逐位复现（`reproduces_the_worst_case`）；描述符域检验 72 行全部通过（最坏 `|sum s - 1| = 0.0000030`）；层内越界点仅 1 个（EMC/cpcm_10 (2.799)）且与能量筛查独立命中同一层；13 篇 PDF 全部可读。
- 限制：双初猜只覆盖 EMC / DMC / EC 三个分子，所以「12 个真解差异」是这 3 个分子的**下界**；导体极限只补了 EMC 一条曲线，其余 11 个分子的 `eps = 1000` 未算；弥散度描述符与靶量之间只有留一交叉验证、没有第二个数据集（**0.556 不是样本外 R2**）；描述符的域比靶集小一格（AN 的气相点落在域外被排除）；文献扫描只覆盖 4 行，其余 27 行仍为 `est` 且其中 7 行的部分引用不在手；三条修正以 overlay 存在、未写回冻结表。

本文可独立阅读；逐项细节、物理机制与需裁决项见同目录 `week14_report_full.md`。

## 1. 双初猜协议：从「解不唯一」到「初猜选错」
### 1.1 协议与规模
- 分子 EMC / DMC / EC；介电阶梯 5/7/10/14/20/28/40/80/200/1000（10 点）；态 neutral / cation / anion。
- 每个点跑两遍：`default` = ORCA 自己的初猜；`moread` = `! MORead` + `%moinp <同电荷态气相 .gbw>`。共 **99** 个作业，**0 失败、0 QC flag**。
- 差异定义 `dE = E_moread - E_default`；`dE < 0` 表示重启到达了默认初猜没到达的更低价态。几何全部复用 G1 并逐原子核对。

### 1.2 能量差的分档（数据给出的阈值）
| 幅度阈值 (eV) | 超过该阈值的点数 |
| --- | --- |
| `1e-08` | 90 |
| `1e-07` | 86 |
| `1e-06` | 72 |
| `1e-05` | 27 |
| `1e-04` | 16 |
| `1e-03` | 12 |
| `1e-02` | 7 |
| `1e-01` | 6 |

- 90 个点里 **78** 个在收敛精度内一致；**12** 个超过 1 meV 且**全部为负**；反向（重启更差）**0** 次。
- 噪声带内最大值 **0.000827 eV**，真解差异最小 1.5e-03 eV、最大 **0.2860 eV**。

### 1.3 十二个真解差异，方向全部相同
| 分子 | 态 | eps | `dE` (eV) | 默认初猜偶极 (D) |
| --- | --- | --- | --- | --- |
| EMC | 阴离子 | 1000 | **-0.2860** | 2.569 |
| EMC | 阴离子 | 200 | **-0.2821** | 2.564 |
| EMC | 阴离子 | 80 | **-0.2751** | 2.556 |
| EMC | 阴离子 | 40 | **-0.2636** | 2.542 |
| EMC | 阴离子 | 20 | **-0.2420** | 2.499 |
| EMC | 阴离子 | 5 | **-0.1370** | 2.538 |
| EC | 阳离子 | 5 | **-0.0174** | 9.730 |
| EC | 阳离子 | 7 | **-0.0097** | 9.885 |
| EC | 阳离子 | 10 | **-0.0051** | 10.005 |
| EC | 阳离子 | 14 | **-0.0028** | 10.088 |
| DMC | 阳离子 | 5 | **-0.0017** | 0.740 |
| EC | 阳离子 | 20 | **-0.0015** | 10.150 |

- 受影响：`DMC, EC, EMC`，态 `anion, cation`。最大惩罚 **0.2860 eV**（EMC 阴离子，eps = 1000）。

### 1.4 EMC 阴离子：失败集与成功集交错
- 失败集（默认初猜停在亚稳态）：`{5, 20, 40, 80, 200, 1000}`
- 成功集（默认初猜已落在真解）：`{7, 10, 14, 28}`
- 两个集合**交错**，所以这不是「大介电才出错」的单调故事，而是两个 SCF 解的吸引域随介电常数非单调变化——这解释了为什么 Week 13 把网格从 4 点加密到 9 点会让它**变糟**。

### 1.5 EMC 阴离子的修复是单调的
| eps | 默认初猜 (D) | MORead (D) | 能量降低 (eV) |
| --- | --- | --- | --- |
| 5 | 2.538 | **5.827** | 0.1370 |
| 20 | 2.499 | **7.036** | 0.2420 |
| 40 | 2.542 | **7.224** | 0.2636 |
| 80 | 2.556 | **7.316** | 0.2751 |
| 200 | 2.564 | **7.371** | 0.2821 |
| 1000 | 2.569 | **7.400** | 0.2860 |

- 十个偶极逐点上升（5.827 -> 7.400 D），**无一处回折**；修复后 Spearman(偶极, eps) = **1.000**，默认初猜是 -0.042。

### 1.6 曲线被修好，但没修到 1
| 口径（九点 5…200） | 默认初猜 | MORead |
| --- | --- | --- |
| Born R2（过原点） | 0.6788 | **0.9556** |
| 一阶差分符号变化 | 4 | **0** |
| 阴离子偶极粗糙度 | 1.991 | **0.084** |

- 六点 Born R2 = **0.8468**（Stage 14 公布 0.8468，`reproduces_stage14 = True`）；九点 Born R2 = **0.6788**（Stage 14 公布 0.6788）。
- 六点斜率：默认 2.5668 -> 修复 2.7848 eV；九点：2.6304 -> 2.7778 eV。
- **0.9556 不等于 1**：修复掉的是解选择伪影，不是 Born 形式的偏差（见 §2）。


## 2. 导体极限：eps = 1000 是第一次真正测到极限
Born 横坐标是 `x = 1 - 1/eps`，所以**拟合出的斜率就是 `eps -> infinity` 的外推极限本身**。Stage 14 停在 `eps = 200`（`x = 0.995`）；本周补的 `eps = 1000` 对应 `x = 0.999`，是第一个把横坐标推进到极限千分之一的实测点。

| 口径 | 默认初猜 | MORead |
| --- | --- | --- |
| 六点斜率（5/10/20/40/80/200） | 2.5668 | 2.7848 |
| 六点斜率下 eps = 200 的缺口 | **+0.0332** | **-0.0308** |
| 九点斜率（5…200） | 2.6304 | 2.7778 |
| `delta(eps = 200)` | 2.5335 | 2.8157 |
| `delta(eps = 1000)` | 2.5449 | 2.8308 |
| 外推误差 @200 | -0.0969 | +0.0378 |
| 外推误差 @1000 | -0.0856 | +0.0530 |
| eps 200 -> 1000 的位移 | **0.0113** | 0.0151 |

- 默认初猜的 `+33.2 meV` 是 Week 12 §5 那个 worst case 的**逐位复现**（`reproduces_the_worst_case = True`），所以对比的是同一根曲线。
- **缺口没有变小**：默认 +0.0332 -> 修复 -0.0308 eV。符号翻了，幅度基本没动。若 0.2860 eV 的亚稳位移是缺口来源，修掉它后缺口应塌掉一个量级；它没有。
- `eps = 200 -> 1000` 只走 **0.0113 eV**（相对 2.6 eV 的斜率是 0.4%），所以曲线的形状已经在极限附近平了，Stage 14 停在 200 不是坏截断；真实偏离在**形状**上，不在截断点上。


## 3. 电子弥散度描述符：把否定结果翻正
### 3.1 七个新描述符（0 个新作业）
取自六层 bare-CPCM 阴离子的 `MULLIKEN ATOMIC CHARGES AND SPIN POPULATIONS` 块，逐分子取层均值（另给中位数口径）：

| 描述符 | 定义 |
| --- | --- |
| `spin_extent_ang2` | sum |s_i| |r_i - CM|^2 / sum |s_i|, s = Mulliken spin population of the anion, CM = centre of mass |
| `spin_rms_ang` | sqrt(spin_extent_ang2) |
| `spin_maxfrac` | max |s_i| |
| `spin_participation` | 1 / sum s_i^2 (inverse participation ratio) |
| `spin_extent_norm` | spin_extent_ang2 / <r^2>_mass |
| `chg_extent_ang2` | same radius of second moment with the weights q_anion - q_neutral |
| `chg_extent_norm` | chg_extent_ang2 / <r^2>_mass |

### 3.2 先检验描述符自己是否良定义
- 归一化：**72** 行（12 分子 x 6 层）最坏的 `|sum s - 1| = 0.0000030`、`|sum q + 1| = 0.0`，全部通过。
- 符号：Mulliken 自旋是**有符号**的，所以 `max|s_i| > 1` 是**强自旋极化**的标志、不是「阴离子不束缚」；判据必须用**带符号和**。
- 气相排除：`AN` 落在六层张成的域之外，`n_inside_domain = 11/12`。
- **唯一**偏离自身分子中位数 20% 以上的层：**EMC/cpcm_10 (2.799)**（该层 `spin_maxfrac` 跳到 1.737、参与比掉到 0.308）。这与 §1 的能量筛查**独立命中同一个层**，所以不是循环论证。

### 3.3 阴离子畸变惩罚从不可预测变成可预测
| 目标 | Stage 14 冠军 | 留一 R2 | Stage 15 冠军 | 留一 R2 | `delta_loo_r2` |
| --- | --- | --- | --- | --- | --- |
| `D_neutral` | `mu_neutral_debye` | 0.634 | `mu_neutral_debye` | **0.634** | **0.000** |
| `D_cation` | `homo_ev` | 0.071 | `homo_ev` | **0.071** | **0.000** |
| `D_anion` | `mu_anion_smd_acn_debye` | 0.162 | `spin_maxfrac` | **0.556** | **0.394** |

- `spin_maxfrac` 的 Spearman `rho = +0.811`、`p = 0.0014`；换成层**中位数**口径，留一 R2 = **0.630**、`rho = +0.706`。
- **中性与阳离子最优描述符一变不变**（`delta_loo_r2 = 0`），所以这不是「多加 7 个描述符所以哪都能拟合」。

### 3.4 秩 vs 线性：两个统计量都要报
| 阴离子轴上的描述符 | Spearman rho | p | 留一直线 R2 |
| --- | --- | --- | --- |
| `spin_maxfrac` | **+0.811** | 0.0014 | **+0.556** |
| `spin_participation` | **-0.846** | 0.0005 | **-2.899** |

- 参与比的**秩**信号（rho = -0.846）比 `spin_maxfrac` 还强，但它的留一**直线** R2 是负的 —— 只报秩会严重误导。

### 3.5 配对搜索
| 目标 | 最好的一对 | 留一 R2 |
| --- | --- | --- |
| `D_neutral` | `mu_cation_debye + spin_participation` | **0.962** |
| `D_cation` | `dmu_reduction_debye + homo_ev` | **0.368** |
| `D_anion` | `spin_rms_ang + spin_maxfrac` | **0.647** |


## 4. 溶液锚点的文献扫描
- 语料：**13** 篇 PDF，**13** 篇可读；审计表引用 7 个 DOI，语料里只有 **1** 个在手。
- 31 行里 11 行引用了那篇在手综述，其中只有 **4** 行的引用集合完全在手，因此只有这 4 行可裁定。

| 行 | 物种 | 性质 | 最终证据标签 | 是否改动 | 理由 |
| --- | --- | --- | --- | --- | --- |
| 14 | DMSO | reduction_potential | `source_does_not_cover_species` | **是** | the in-hand review never writes DMSO or "dimethyl sulfoxide" anywhere, in the body or in the reference list |
| 15 | AN | reduction_potential | `source_does_not_provide_value` | **是** | acetonitrile occurs exactly once in the whole PDF and inside the title of a cited article, so the review carries no value |
| 24 | DME | oxidation_potential | `review_trend_only` | 否（确认） | the only number attached to a glyme is a 0.5-1.0 V oxidation-stability *enhancement* with salt concentration, which is a shift and not a potential on a stated scale |
| 25 | DOL | oxidation_potential | `source_does_not_cover_species` | **是** | the in-hand review never writes DOL or "dioxolane" anywhere |

- `n_corrections_adopted = 3`、`confirmed_rows = 24`、`n_upgrades_meeting_conditions = 0`。
- 三条被逐字读过、仍被否的数值线索（全部是**络合物**而非孤立溶剂）：

| 行 | 线索 | 否掉的理由 |
| --- | --- | --- |
| 17 | —— | EC(PF6-) and EC2 dimers -- anion complexes, not the isolated solvent |
| 19 | —— | Li+(DMC)Li+ complex reduced at 1.4 V -- a complex, and on the reduction axis |
| 23 | —— | VC(PF6)2 -- a complex carrying two anion units |

- **Gate 1 仍是 `NOT CLOSED`**，`n_rows_still_est_after_scan = 31`；三条修正以 overlay `stage15_anchor_corrections.csv` 作为 correction of record，**不写回**有 digest 的冻结表。
- 净收益是**清账而非补值**：3 行的标签从「有综述趋势支持」降级为「在手来源根本没覆盖这个物种」。


## 5. 产物与口径
| 产物 | 内容 |
| --- | --- |
| `stage15_two_guess.json` | 99 个作业的运行记录（11 层 x 9 作业，0 失败） |
| `stage15_two_guess_analysis.json` | Part A 全部分析（能量、偶极、Born 曲线、导体极限、判决） |
| `stage15_two_guess_energy.csv` / `_dipole.csv` | 90 个点的双协议能量差 / 偶极 |
| `stage15_diffuseness.json` | Part B：7 个新描述符、21 个扩展描述符、域检验、判决、配对搜索 |
| `stage15_diffuseness.csv` / `_by_molecule.csv` | 72 行逐层 / 12 行逐分子（层均值与中位数两种口径） |
| `stage15_anchor_scan.json` / `.csv` | Part C：13 篇语料、DOI 交集、31 行裁定、gate1 汇总 |
| `stage15_anchor_corrections.csv` | 3 条修正的 overlay（correction of record） |
| `stage15_summary.md` | F28 / F29 的逐面板文字 companion |
| `p2_core_set_*.csv` / `p2_summary_*.json` | 11 层的能量表与逐层汇总（eps = 1000 + 10 个 MORead 层） |

## 6. 产物清单
- `artifacts/F28_two_guess_protocol.png`
- `artifacts/F29_diffuseness_descriptor.png`
- `artifacts/figure_manifest_week14_stage15.md`
- `p2_core_set_cpcm_1000.csv`
- `p2_core_set_moread_cpcm_10.csv`
- `p2_core_set_moread_cpcm_1000.csv`
- `p2_core_set_moread_cpcm_14.csv`
- `p2_core_set_moread_cpcm_20.csv`
- `p2_core_set_moread_cpcm_200.csv`
- `p2_core_set_moread_cpcm_28.csv`
- `p2_core_set_moread_cpcm_40.csv`
- `p2_core_set_moread_cpcm_5.csv`
- `p2_core_set_moread_cpcm_7.csv`
- `p2_core_set_moread_cpcm_80.csv`
- `p2_summary_cpcm_1000.json`
- `p2_summary_moread_cpcm_10.json`
- `p2_summary_moread_cpcm_1000.json`
- `p2_summary_moread_cpcm_14.json`
- `p2_summary_moread_cpcm_20.json`
- `p2_summary_moread_cpcm_200.json`
- `p2_summary_moread_cpcm_28.json`
- `p2_summary_moread_cpcm_40.json`
- `p2_summary_moread_cpcm_5.json`
- `p2_summary_moread_cpcm_7.json`
- `p2_summary_moread_cpcm_80.json`
- `stage15_anchor_corrections.csv`
- `stage15_anchor_scan.csv`
- `stage15_anchor_scan.json`
- `stage15_diffuseness.csv`
- `stage15_diffuseness.json`
- `stage15_diffuseness_by_molecule.csv`
- `stage15_summary.md`
- `stage15_two_guess.json`
- `stage15_two_guess_analysis.json`
- `stage15_two_guess_dipole.csv`
- `stage15_two_guess_energy.csv`
- `week14_report_full.md`

## 7. 源文件缺失
- 无（全部源路径均存在）
