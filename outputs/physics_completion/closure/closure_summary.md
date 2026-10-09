# 四分子四态闭环与翻转持续性（derived）

> 由 `scripts/wp_production/build_wp2_closure.py` 从 `outputs/physics_completion/**` 只读派生；
> 零新增电子结构计算。缺值一律留空并标 `not_computed`。

## 闭环进度

| 项 | 值 |
| --- | --- |
|主态登记 | 8 / 16 |
| 基组一致中性腿（M_tzvpd） | 1 / 4 |
| 四态齐备的分子 | none |
| 基组一致自由腿齐备的分子 | GBL |

## 翻转阶梯（Δ = IP(i) − IP(j)，氧化轴）

| pair | R1a 垂直 | R1b 绝热 | R2 溶液优化电子能 | R3 单构象自由能 | R4 系综 |
| --- | --- | --- | --- | --- | --- |
| EMC | GBL | positive | negative | not_computed | not_computed | not_computed |
| EMC | SL | positive | negative | not_computed | not_computed | not_computed |

## 口径

方法轴认证只覆盖**固定几何上的电子能层**：EMC–GBL 与 EMC–SL 在四种预设设定下
垂直腿与绝热腿符号相反且各自稳定。该结论**不**自动外推到溶液优化几何或自由能层；
R2/R3 需要基组一致的 `M_tzvpd` 腿，R4 需要构象采样，未完成即标 `not_computed`。
