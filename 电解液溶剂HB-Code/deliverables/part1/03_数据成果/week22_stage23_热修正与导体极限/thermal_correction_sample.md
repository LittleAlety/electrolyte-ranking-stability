# R9：热修正抽样（GFN2-xTB ``--ohess``）

- 抽样：8 个分子（EC FEC DMC DME GBL AN SL DMSO），覆盖 7 个家族，含氟代溶剂 FEC。
- 作业：24 个 ``--ohess``（8 分子 x 3 态），几何**复用** P0/P1/P2 的 G1，不重新优化。
- 定义：``thermal_G = Delta(G) - Delta(E)``、``thermal_H = Delta(H) - Delta(E)``（同一对电荷态，eV）。

| 轴 | mean thermal_G (eV) | std | min | max | max abs | mean thermal_H |
| --- | --- | --- | --- | --- | --- | --- |
| 氧化 | -0.1350 | 0.0581 | -0.2635 | -0.0633 | 0.2635 | -0.1421 |
| 还原 | 0.1950 | 0.0775 | 0.1158 | 0.3180 | 0.3180 | 0.1878 |

对照 **delta_m**（项目决策容差，``outputs/week6/delta_m_frozen.json``）：氧化 0.700 eV、还原 2.074 eV。

**限制（必须与数字同时引用）**：带电态的 Hessian 取在**中性 G1 几何**上，不是它自己的极小点；16 个带电作业里有 2 个报出虚频。因此上表是「被略去的热修正有多大」的**量级上界**，不是热化学可观测量。

原始 xTB 文本：``raw/<mol_id>/<state>_ohess.out``。
