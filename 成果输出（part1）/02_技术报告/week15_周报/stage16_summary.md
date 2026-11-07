# stage16_summary

F30 / F31 的逐面板文字 companion。所有数字都从 `stage16_catalogue_analysis.json` 与 `stage16_predictor.json` 读出，不手抄。

## F30 (a) 完整网格

12 个分子 x 3 个电荷态 x 10 个电介质 = 360 个单元格，全部两臂配对成功。灰色表示两臂一致到 SCF 收敛（|dE| <= 1 meV），红色表示默认初猜落在更高解上（dE < 0），蓝色表示重启反而更高（dE > 0）。

- 一致 328，MORead 更低 32，MORead 更高 0。
- 最大赤字 -0.285961 eV，出现在 EMC / anion / eps=1000。
- 逐态计数：中性 0 个赤字、阳离子 16 个、阴离子 16 个。

## F30 (b) 逐 (分子, 状态) 的最大赤字

- EMC / anion：0.285961 eV（首次出现在 eps=5，共 6 个电介质命中）
- TMP / cation：0.152250 eV（首次出现在 eps=5，共 10 个电介质命中）
- PC / anion：0.095535 eV（首次出现在 eps=5，共 10 个电介质命中）
- EC / cation：0.017411 eV（首次出现在 eps=5，共 5 个电介质命中）
- DMC / cation：0.001655 eV（首次出现在 eps=5，共 1 个电介质命中）

## F30 (c) 阈值计数

- 超过 1e-08 eV：359 个单元格
- 超过 1e-07 eV：348 个单元格
- 超过 1e-06 eV：271 个单元格
- 超过 1e-05 eV：76 个单元格
- 超过 0.0001 eV：37 个单元格
- 超过 0.001 eV：32 个单元格
- 超过 0.01 eV：27 个单元格
- 超过 0.1 eV：16 个单元格

## 阶梯依赖

- core3（5/20/200）：判为存在漏解的分子 5/12 -> DMC, EC, EMC, PC, TMP
- focus6（5/10/20/40/80/200）：判为存在漏解的分子 5/12 -> DMC, EC, EMC, PC, TMP
- ladder10（5/7/10/14/20/28/40/80/200/1000）：判为存在漏解的分子 5/12 -> DMC, EC, EMC, PC, TMP
- core3_vs_focus6：36/36 行标签一致
- core3_vs_ladder10：36/36 行标签一致
- focus6_vs_ladder10：36/36 行标签一致

## F31 (d) 选定描述符与冻结阈值

- 规则：`gas_small_gap_value <= -0.071`
- 定义：ORCA's pre-SCF HOMO/LUMO gap estimate, i.e. the number behind its own small-gap warning
- 符号是否与物理先验一致：是
- 与多数类基线的比较：留一 0.708 vs 基线 0.792 -> **未超过**（平凡规则更准）
- 平衡准确率（sensitivity 与 specificity 的均值；阈值并不按它选）：样本内 0.674，平凡单类规则恒为 0.500
- 精确置换检验：gas_small_gap_value，在 42504 种标签指派下 p = 0.0116

## F31 (h) 两臂事后诊断（post_hoc，不是预报）

池化规则失败的机制原因：the pooled rule is frozen before the calculation; this split is not. The direction, the threshold and the arm assignment are all chosen after seeing the labels, so the numbers below are an explanation of the failure, never a forecast.

| 臂 | 行数 | 正例 | 多数类基线 | 排序最强描述符 | AUC | 正例排名 | 该描述符留一 | 超过基线 | 精确置换 p |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| cation | 12 | 3 | 0.750 | `gas_small_gap_value` | 0.074 | 1/3/4 | 0.667 | 否 | 0.0407 |
| anion | 12 | 2 | 0.833 | `gas_spin_maxfrac` | 0.900 | 2/3 | 0.917 | 是 | 0.1343 |

**这两条事后规则也在留出臂上打了分**（同一描述符、同一方向、同一阈值，只是换到 6 个没见过的分子上）：

| 臂 | 描述符 | 留出准确率 | 留出基线 | TP/FP/TN/FN | 超过基线 |
| --- | --- | --- | --- | --- | --- |
| cation | `gas_small_gap_value` | 0.667 | 1.000 | 0/2/4/0 | 否 |
| anion | `gas_spin_maxfrac` | 0.667 | 0.667 | 0/0/4/2 | 否 |

换句话说：两臂分工这件事在**发现集内**看起来成立，在**留出臂上同样不成立**。所以本文给出的机制解释只是解释，不是可以拿去用的筛查规则。

选臂用的量（电荷态）在作业开始前已知，但每臂用哪个描述符、阈值落在哪里都是看到标签之后选的：the branch key is the charge state, which is known before the job starts, so the split itself is free; what is not free is which descriptor each branch would use and where its threshold would sit.

## F31 (e) 单变量筛查

| 描述符 | 方向 | AUC | 留一准确率 | 阈值 |
| --- | --- | --- | --- | --- |
| `gas_small_gap_value` | 越小越危险 | 0.137 | 0.708 | -0.071 |
| `gas_min_spin` | 越小越危险 | 0.305 | 0.750 | -0.219332 |
| `gas_gyration_ang2` | 越大越危险 | 0.679 | 0.792 | 3.70841 |
| `gas_sum_spin_abs` | 越大越危险 | 0.663 | 0.750 | 1.95231 |
| `gas_spin_rms_ang` | 越大越危险 | 0.611 | 0.750 | 2.29673 |
| `gas_spin_extent_norm` | 越小越危险 | 0.389 | 0.667 | 0.418475 |
| `gas_spin_maxfrac` | 越大越危险 | 0.579 | 0.833 | 0.836975 |
| `gas_mulliken_shift` | 越小越危险 | 0.447 | 0.792 | 0.999999 |
| `gas_dipole_debye` | 越小越危险 | 0.453 | 0.667 | 0.0489827 |
| `gas_spin_participation` | 越小越危险 | 0.484 | 0.792 | 0.996754 |
| `gas_gap_ev` | 越小越危险 | 0.484 | 0.750 | 0.37465 |

## F31 (f) 留出臂

- 分子：DEC, EA, FEC, MA, TEGDME, VC
- 准确率 0.750（12 行）；TP 0 / FP 1 / TN 9 / FN 2
- DEC / cation：描述符 -0.024，预测 无漏解，真值 无漏解
- DEC / anion：描述符 -0.058，预测 无漏解，真值 有漏解
- EA / cation：描述符 -0.065，预测 无漏解，真值 无漏解
- EA / anion：描述符 -0.041，预测 无漏解，真值 无漏解
- FEC / cation：描述符 -0.012，预测 无漏解，真值 无漏解
- FEC / anion：描述符 -0.037，预测 无漏解，真值 无漏解
- MA / cation：描述符 0.001，预测 无漏解，真值 无漏解
- MA / anion：描述符 -0.024，预测 无漏解，真值 无漏解
- TEGDME / cation：描述符 -0.115，预测 有漏解，真值 无漏解
- TEGDME / anion：描述符 -0.066，预测 无漏解，真值 有漏解
- VC / cation：描述符 0.012，预测 无漏解，真值 无漏解
- VC / anion：描述符 -0.013，预测 无漏解，真值 无漏解

## F31 (g) 多变量上限

- 特征：gas_small_gap_value, gas_min_spin
- 留一 AUC 0.821
- 留出准确率 0.750
