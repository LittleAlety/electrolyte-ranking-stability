# Week 15 成果小结 —— Stage 16（全核心集双初猜目录与事前预警规则）

## 0. 一页结论
- 做了什么：把 Week 14 的三分子双初猜协议扩成全核心集目录：12 个分子 x 3 个状态 x 10 个电介质 x 2 种初猜，并对此前从未算过连续介质的 6 个分子做留出验证；再用只依赖气相输出的描述符拟合一条事前预警规则。
- 关键数字：360 个配对单元格里 328 个一致、32 个 MORead 更低、0 个更高；最大赤字 -0.285961 eV（EMC / anion / eps=1000）；10 点阶梯下 5/12 个分子被判定存在漏解。
- 质检：360 个单元格全部落盘、0 个失败；几何审计逐分子通过；复用行全部带 `source` 出处；阈值 0.001 eV 原样继承自 Week 14；预警规则与多数类基线的比较按实测记录（`chosen_rule_beats_majority_baseline = False`），负结果原样写入报告与小结。
- 限制：目录只在 12 个分子的 10 点电介质阶梯上回答「默认初猜是否漏掉更低解」；「更低解」是按三条语句口径的能量比较，不是自由能；未做溶剂构型采样，也未回答泄漏解在真实溶液里的寿命。事前预警规则在发现集上**未能超过多数类基线**（正例只有 5/24），两臂诊断是事后解释、不构成可用的筛查工具。

本文可独立阅读；逐项细节、物理机制与需裁决项见同目录 `week15_report_full.md`。

## 1. 协议与规模
### 协议与规模

- 发现集：T3 审计子集的 12 个分子；验证集：从未做过连续介质计算的 6 个分子（DEC, EA, FEC, MA, TEGDME, VC）。
- 电介质阶梯：5, 7, 10, 14, 20, 28, 40, 80, 200, 1000，与 Stage 13/14/15 逐点一致。
- 两臂：`default`（ORCA 自带初猜）与 `moread`（`! MORead` + 气相 `%moinp`，同一电荷态）。
- 单元格：360 个（12 个分子的 3 个状态 x 10 个电介质），配对成功的 360 个，未配对的 0 个。
- 几何：G1 冻结；几何审计对每个有连续介质参照的分子逐一比对气相与 CPCM(20) 的xyz，全部逐原子相同。
- 算力：`--jobs 2 --nprocs 8`（本机 16 逻辑核），与既有 P2 各层协议相同。

## 2. 目录结论
### 目录结论

- 配对单元格 360：两臂一致到 SCF 收敛 328 个，MORead 更低 32 个，MORead 更高 0 个。
- 最大赤字：**-0.285961 eV**，出现在 EMC / anion / eps=1000。
- 阈值原文（继承自 Week 14，本周未重新调参）：inherited unchanged from Stage 15: the largest residual of the two arms on cells that share a solution was 8.27e-4 eV, so 1e-3 eV is the next round decade above the SCF noise band

| 状态 | 单元格 | MORead 更低 | MORead 更高 |
| --- | --- | --- | --- |
| 中性 | 120 | 0 | 0 |
| 阳离子 | 120 | 16 | 0 |
| 阴离子 | 120 | 16 | 0 |

| 阶梯 | 电介质 | 判为有漏解的分子 | 比例 |
| --- | --- | --- | --- |
| 3 点 | 5/20/200 | 5/12 | DMC, EC, EMC, PC, TMP |
| 6 点 | 5/10/20/40/80/200 | 5/12 | DMC, EC, EMC, PC, TMP |
| 10 点 | 5/7/10/14/20/28/40/80/200/1000 | 5/12 | DMC, EC, EMC, PC, TMP |

## 3. 标签对阶梯的稳健性
### 标签对阶梯的稳健性

标签定义在「某 (分子, 状态) 在被探测的电介质上是否存在被默认初猜漏掉的更低解」。阶梯越密，漏检越少，因此 `core3` 的标签必然被 `focus6` 蕴含、`focus6` 必然被 `ladder10` 蕴含；下表给出实测差异。

- `core3_vs_focus6`：36 行中 0 行不一致（两者完全一致）
- `core3_vs_ladder10`：36 行中 0 行不一致（两者完全一致）
- `focus6_vs_ladder10`：36 行中 0 行不一致（两者完全一致）

## 4. 家族覆盖与命中模式
### 家族覆盖

| 家族 | 分子数 | 其中有漏解 | 分子 |
| --- | --- | --- | --- |
| cyclic_carbonate | 2 | 2 | EC, PC |
| ester | 1 | 0 | GBL |
| ether | 2 | 0 | DOL, DME |
| linear_carbonate | 2 | 2 | DMC, EMC |
| nitrile | 2 | 0 | SN, AN |
| phosphate | 1 | 1 | TMP |
| sulfone | 1 | 0 | SL |
| sulfoxide | 1 | 0 | DMSO |

| 分子 | 状态 | 模式（低 eps 到高 eps） | 命中 | 连续 | 首个 | 末个 |
| --- | --- | --- | --- | --- | --- | --- |
| EC | cation | `1111100000` | 5 | 是 | 5 | 20 |
| PC | anion | `1111111111` | 10 | 是 | 5 | 1000 |
| DMC | cation | `1000000000` | 1 | 是 | 5 | 5 |
| EMC | anion | `1000101111` | 6 | 否 | 5 | 1000 |
| TMP | cation | `1111111111` | 10 | 是 | 5 | 1000 |

## 5. 事前预警规则
### 事前预警规则

- 样本：24 行开壳层 (分子, 状态)（5 个正例）；open-shell states only: the label compares two SCF solutions and a closed-shell neutral has one
- 冻结规则：`gas_small_gap_value <= -0.071`，定义「ORCA's pre-SCF HOMO/LUMO gap estimate, i.e. the number behind its own small-gap warning」。
- 发现集：AUC 0.137，样本内准确率 0.833，留一准确率 0.708，多数类基线 0.792。
- 阈值只由发现集选出（留一），验证集不参与任何拟合。

| 描述符 | 方向 | AUC | 留一准确率 |
| --- | --- | --- | --- |
| gas_small_gap_value | 越小越危险 | 0.137 | 0.708 |
| gas_min_spin | 越小越危险 | 0.305 | 0.750 |
| gas_gyration_ang2 | 越大越危险 | 0.679 | 0.792 |
| gas_sum_spin_abs | 越大越危险 | 0.663 | 0.750 |
| gas_spin_rms_ang | 越大越危险 | 0.611 | 0.750 |
| gas_spin_extent_norm | 越小越危险 | 0.389 | 0.667 |

**与多数类基线的比较（不假设结论）**：留一准确率 **0.708** **未超过** 多数类基线 **0.792**，故 `chosen_rule_beats_majority_baseline = False`。
- 但规则**不是噪声**：平衡准确率（sensitivity 与 specificity 的均值，阈值并不按它选）样本内 0.674，而任何「一律判同一类」的平凡规则恒为 0.500；样本内准确率 0.833 与留一准确率 0.708 之间的落差就是过拟合的量。
- 基线定义：the trivial classifier that answers 'no deficit' for every row; at 5 positives out of 24 rows it is right 0.792 of the time, so plain accuracy is a weak yardstick and the balanced-accuracy threshold search is the reason the frozen rule predicts anything at all

**两臂事后诊断（`post_hoc = True`；这是对失败的机制解释，不是预报）**

| 臂 | 行数 | 正例 | 多数类基线 | 排序最强描述符 | AUC | 正例排名 | 该描述符留一 | 超过基线 | 精确置换 p |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| cation | 12 | 3 | 0.750 | `gas_small_gap_value` | 0.074 | 1/3/4 | 0.667 | 否 | 0.0407 |
| anion | 12 | 2 | 0.833 | `gas_spin_maxfrac` | 0.900 | 2/3 | 0.917 | 是 | 0.1343 |

- 失败原因（产物原文）：the pooled rule is frozen before the calculation; this split is not. The direction, the threshold and the arm assignment are all chosen after seeing the labels, so the numbers below are an explanation of the failure, never a forecast.
- 选臂用的量是**电荷态**，作业开始前就已知：the branch key is the charge state, which is known before the job starts, so the split itself is free; what is not free is which descriptor each branch would use and where its threshold would sit.
- 注意：「某描述符的留一准确率超过基线」本身不等于证据——阳离子臂上留一最高的是 `gas_spin_participation`（0.833），但它的排序信息几乎为零（|AUC−0.5| = 0.019，置换 p = 1.000）。因此本表同时给出 AUC 与正例排名。

- 留出臂（DEC, EA, FEC, MA, TEGDME, VC 的 12 个 (分子, 状态) 行，标签取自 5 / 20 / 200 三个电介质）：准确率 **0.750**，混淆矩阵 TP 0 / FP 1 / TN 9 / FN 2。
- 精确置换检验（gas_small_gap_value）：统计量 |AUC - 0.5|，在 24 行 / 5 个正例的全部 **42504** 种标签指派下 p = **0.0116**。
- 多变量上限（gas_small_gap_value, gas_min_spin）：留一 AUC 0.821，留出准确率 0.750。

## 6. 产物与口径
### 本周产物

| 文件 | 说明 |
| --- | --- |
| `stage16_catalogue.json` | 运行账本：单元格数、复用/新算计数、几何审计、逐层摘要 |
| `stage16_catalogue_analysis.json` | 目录分析：阈值直方图、逐分子逐态标签、阶梯一致性、家族覆盖 |
| `stage16_cells.csv` | 逐单元格能量对照（默认初猜 vs MORead 重启） |
| `stage16_by_state.csv` | 逐 (分子, 状态) 在三种阶梯上的汇总 |
| `stage16_gas_descriptors.csv` | 气相先验描述符表（18 分子 x 3 状态） |
| `stage16_predictor.json` | 预警规则：单变量筛查、冻结阈值、留出臂混淆矩阵、多变量上限 |
| `stage16_summary.md` | F30 / F31 的逐面板文字 companion |

## 7. 产物清单
- `artifacts/F30_two_guess_catalogue.png`
- `artifacts/F31_apriori_warning_rule.png`
- `artifacts/figure_manifest_week15_stage16.md`
- `p2_core_set_cpcm_1000.csv`
- `p2_core_set_cpcm_14.csv`
- `p2_core_set_cpcm_28.csv`
- `p2_core_set_cpcm_7.csv`
- `p2_core_set_holdout_cpcm_20.csv`
- `p2_core_set_holdout_cpcm_200.csv`
- `p2_core_set_holdout_cpcm_5.csv`
- `p2_core_set_holdout_moread_cpcm_20.csv`
- `p2_core_set_holdout_moread_cpcm_200.csv`
- `p2_core_set_holdout_moread_cpcm_5.csv`
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
- `p2_summary_cpcm_14.json`
- `p2_summary_cpcm_28.json`
- `p2_summary_cpcm_7.json`
- `p2_summary_holdout_cpcm_20.json`
- `p2_summary_holdout_cpcm_200.json`
- `p2_summary_holdout_cpcm_5.json`
- `p2_summary_holdout_moread_cpcm_20.json`
- `p2_summary_holdout_moread_cpcm_200.json`
- `p2_summary_holdout_moread_cpcm_5.json`
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
- `stage16_by_state.csv`
- `stage16_catalogue.json`
- `stage16_catalogue_analysis.json`
- `stage16_cells.csv`
- `stage16_gas_descriptors.csv`
- `stage16_holdout.json`
- `stage16_predictor.json`
- `stage16_summary.md`
- `stage16_validation_cells.csv`
- `week15_report_full.md`

## 8. 源文件缺失
- 无（全部源路径均存在）
