# 机制案例页（最多 3 例）

选择规则（事先冻结）：优先选证据最强的稳健翻转，再选影响 Top-k 的 unresolved 边界，再选有身份改变的代表；**无稳健翻转时不强行补案例**。

## CASE1：EMC | GBL

- 轴：oxidation (P1v -> P1a vertical-to-adiabatic)
- d_lower = 0.250050009 eV；d_upper = -0.455791550 eV；sigma = 0.206521142 eV
- 判定：ROBUST_INVERSION
- 选集影响：flips the relative oxidation order of the pair under relaxation

## CASE2：EMC | SL

- 轴：oxidation (P1v -> P1a vertical-to-adiabatic)
- d_lower = 0.408539433 eV；d_upper = -0.277578589 eV；sigma = 0.206521142 eV
- 判定：ROBUST_INVERSION
- 选集影响：flips the relative oxidation order of the pair under relaxation

## 原始结构证据（既有冻结几何，零新增计算）

| 分子 | 家族 | 原子数 | 元素序列一致 | 重原子成键对 | 平均 abs(dr) (Å) | 最大 abs(dr) (Å) | 最大变化键 | 该键 dr (Å) | dIP (eV) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| EMC | linear_carbonate | 15 | true | 6 | 0.053936 | 0.089787 | C4-O5 | 0.089787 | -0.9503160071914678 |
| GBL | ester | 12 | true | 6 | 0.037918 | 0.085612 | C2-O6 | -0.085612 | -0.244474448699469 |
| SL | sulfone | 15 | true | 5 | 0.009897 | 0.015528 | C5-C6 | -0.015528 | -0.26419798480917933 |

结构来源（既有冻结路径；按交付层纪律不复制原始几何文件，只交付派生的键长变化）：中性松弛几何 `outputs/week4/t2_opt_freq/{name}/{name}_G2.xyz`；阳离子松弛几何 `outputs/phase2_p1a/geometry_relaxation/{name}/{name}_cation_opt.xyz`。
成键对只用 1.8 Å 几何截断枚举，不是力常数判据；键长是平移/旋转不变量，因此不需要结构叠合。

## 逐例六项证据覆盖（方案 7.3）

| 项目 | 状态 | 说明 |
| --- | --- | --- |
| 原始结构 | 已提供（派生） | 上表 + `mechanism_bond_changes.csv` 逐键列出中性/阳离子键长（原始几何仍留在冻结路径，未复制进交付层） |
| 电子密度/自旋 | 待补 | 需 WP1 生产单点的密度/自旋分析（本批次零新增计算） |
| 配位变化 | 待补 | 本 rung 为自由态；配位态属 WP2 |
| E/G 分解 | 部分 | 有电子能层分解（dIP 列）；G 层待 WP2 |
| 方法敏感性 | 待补 | 现为单 rung 位移 std；多方法范围待 WP1 |
| 选集影响 | 已提供 | 每例的 pair 级翻转说明 |

> 说明：本页登记判定、原始结构与选集影响；电子密度/自旋、配位变化、G 层分解与方法敏感性范围需在 WP1/WP2 的新计算完成后补入（本批次无可提供的对应计算）。
