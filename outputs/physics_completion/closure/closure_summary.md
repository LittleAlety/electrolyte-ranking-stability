# 四分子四态闭环与翻转持续性（derived）

> 由 `scripts/wp_production/build_wp2_closure.py` 从 `outputs/physics_completion/**` 只读派生；
> 零新增电子结构计算。缺值一律留空并标 `not_computed`。

## 闭环进度

| 项 | 值 |
| --- | --- |
|主态登记 | 12 / 16 |
| 基组一致中性腿（M_tzvpd） | 1 / 4 |
| 四态齐备的分子 | DMC |
| 基组一致自由腿齐备的分子 | GBL |

## 翻转阶梯（Δ = IP(i) − IP(j)，氧化轴）

| pair | R1a 垂直 | R1b 绝热 | R2 溶液优化电子能 | R3 单构象自由能 | R4 系综 | R4_screen 筛选层系综 |
| --- | --- | --- | --- | --- | --- | --- |
| EMC | GBL | positive | negative | not_computed | not_computed | not_computed | negative (screen) |
| EMC | SL | positive | negative | not_computed | not_computed | not_computed | positive (screen) |

## 方案第 2 步的三个问题（逐对）

| pair | 固定几何 → 溶液各态优化 | 电子能 → 单构象自由能（热校正） | 单构象 → 系综 |
| --- | --- | --- | --- |
| EMC | GBL | not_computed（R2 缺基组一致腿） | not_computed（R2 或 R3 缺） | not_computed（R3 与系综都缺） |
| EMC | SL | not_computed（R2 缺基组一致腿） | not_computed（R2 或 R3 缺） | not_computed（R3 与系综都缺） |

口径：Δ = IP(i) − IP(j)（氧化轴）。「符号改变」= 这一步之后两分子的先后被翻转；未计算的一律写 not_computed，不做任何外推。R4_screen 是筛选层，单独标注，不冒充生产 R4。

## 口径

方法轴认证只覆盖**固定几何上的电子能层**：EMC–GBL 与 EMC–SL 在四种预设设定下
垂直腿与绝热腿符号相反且各自稳定。该结论**不**自动外推到溶液优化几何或自由能层；
R2/R3 需要基组一致的 `M_tzvpd` 腿，R4（生产系综）需要额外产出的结构腿，未完成即标 `not_computed`。

`R4_screen` 是**另一档、单独标注**的：它是已登记筛选池上的气相 GFN2 Boltzmann 系综
（`outputs/physics_completion/ensembles/`），口径是 `L(M_plus) - L(M)`、`L = G_state`；
它的状态一律是 `computed_screen_only`，**不是**生产 R4，也不与 R1/R2/R3 的平均口径混用。
同一份筛选层还给出 Li 条件态 `L(LiM_2plus) - L(LiM_plus)` 的四层阶梯，用来回答
「Li 配位是否改变这一对的符号」；两者是否同号写在 `closure_index.json` 的 `screen_verdict` 里。
