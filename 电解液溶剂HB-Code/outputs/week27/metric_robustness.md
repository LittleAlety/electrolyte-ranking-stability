# 27 · R15 指标稳健性与排序可识别性审计（对抗审计 round 3 · 项目 A/B）

- 触发：第二轮收口后，评审要求攻击「排序稳定性指标本身的定义」与「非反转型的排序损伤」。
- 生成器：`scripts/audit_metric_robustness.py`（离线只读，零新增电子结构）
- 产物：`outputs/week27/metric_robustness.json`、`outputs/week27/metric_robustness.md`、
  图 `outputs/figures/F57_metric_robustness.png`、`outputs/week27/F57_manifest.md`

## 0. 一句话结论

**两件事同时成立，而且必须一起说：**

1. 两个模型的**点排序**确实高度一致（`rho` ≈ 0.80，`tau_b` 0.59–0.90）——「cheap proxy 保留
   了排序」这句话在点排序意义上是**真**的；
2. 但**证据无法识别这个排序**：把不可解析 pair 换一种同样合理的处理方式，`tau_b` 在
   `[pessimistic, optimistic]` 之间整段滑动，**8 个 block 全部**在冻结的 0.90 排序门槛两侧翻转。

所以本项目的正确表述不是「排序被反转」，而是**排序不可识别（loss of rank identifiability）**。
这与评审的假设一致，也是比 inversion 更准确的失败模式描述。

## 1. 口径

| 项 | 值 |
| --- | --- |
| 主判据 | z = 1（预注册） |
| 排序门槛 | tau_b >= 0.9（预注册 Gate-1 排序层门槛） |
| 四政策 | `exclusion` / `tie` / `pessimistic` / `optimistic`（见脚本头部闭式） |
| 可分层层数 | 按模型自身值排序，相邻 pair 未解析即断块 |

## 2. 策略带（同一份数据，四种同样合理的处理）

| rung | 轴 | n | f_tie | exclusion | tie | pessimistic | optimistic | 带宽度 | 结论翻转 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P0->P1v | oxidation | 18 | 0.458 | 1.000 | 0.542 | 0.085 | 1.000 | 0.915 | 是 |
| P0->P1v | reduction | 18 | 0.712 | 1.000 | 0.288 | -0.425 | 1.000 | 1.425 | 是 |
| P1v->P2a | oxidation | 18 | 0.183 | 1.000 | 0.817 | 0.634 | 1.000 | 0.366 | 是 |
| P1v->P2a | reduction | 18 | 0.386 | 1.000 | 0.614 | 0.229 | 1.000 | 0.771 | 是 |
| P0->P2a | oxidation | 18 | 0.451 | 1.000 | 0.549 | 0.098 | 1.000 | 0.902 | 是 |
| P0->P2a | reduction | 18 | 0.739 | 1.000 | 0.261 | -0.477 | 1.000 | 1.477 | 是 |
| C0->C1 | oxidation | 10 | 0.333 | 1.000 | 0.667 | 0.333 | 1.000 | 0.667 | 是 |
| C0->C1 | reduction | 10 | 0.911 | 1.000 | 0.089 | -0.822 | 1.000 | 1.822 | 是 |

> 带宽度恒等于 `2 * f_tie`：**不可解析比例就是排序一致性统计量的政策歧义**。
> `exclusion` 一列恒为 1.000 —— 这正是 R15 循环性审计的 T6b（双方解析子集内没有反向 pair）。

## 3. 排序可识别性（可分层层数）

| rung | 轴 | n | cheap 层数 | target 层数 | 双方认证层数 | 最大同层块 | 近临界 pair（cheap/target） |
| --- | --- | --- | --- | --- | --- | --- | --- |
| P0->P1v | oxidation | 18 | 13 (块 4) | 12 (块 3) | 14 (块 3) | 3 | 14 / 8 |
| P0->P1v | reduction | 18 | 13 (块 4) | 16 (块 2) | 17 (块 2) | 2 | 8 / 3 |
| P1v->P2a | oxidation | 18 | 9 (块 5) | 10 (块 5) | 11 (块 3) | 3 | 7 / 7 |
| P1v->P2a | reduction | 18 | 12 (块 3) | 14 (块 4) | 15 (块 3) | 3 | 7 / 6 |
| P0->P2a | oxidation | 18 | 13 (块 3) | 12 (块 2) | 13 (块 2) | 2 | 17 / 9 |
| P0->P2a | reduction | 18 | 8 (块 5) | 16 (块 3) | 16 (块 3) | 3 | 5 / 3 |
| C0->C1 | oxidation | 10 | 5 (块 5) | 6 (块 3) | 6 (块 3) | 3 | 1 / 4 |
| C0->C1 | reduction | 10 | 8 (块 2) | 8 (块 2) | 10 (块 1) | 1 | 9 / 1 |

## 4. 赢家边际（top-1 vs top-2，单位：该 pair 自身 sigma）

| rung | 轴 | cheap 边际 | target 边际 |
| --- | --- | --- | --- |
| P0->P1v | oxidation | 21.12 | 0.90 |
| P0->P1v | reduction | 0.98 | 0.44 |
| P1v->P2a | oxidation | 2.39 | 0.98 |
| P1v->P2a | reduction | 1.15 | 0.01 |
| P0->P2a | oxidation | 4.74 | 0.59 |
| P0->P2a | reduction | 1.58 | 0.01 |
| C0->C1 | oxidation | 2.37 | 3.79 |
| C0->C1 | reduction | 0.58 | 0.16 |

## 5. 汇总

| 量 | 值 |
| --- | --- |
| block 数 | 8 |
| 政策下结论翻转的 block 数 | **8 / 8** |
| 最大带宽度 | 1.822 |
| 带宽度中位数 | 0.908 |
| 最低认证层数比（层数 / n） | 0.600 |
| 最大同层块 | 3 |
| target 赢家边际范围（sigma） | 0.01 - 3.79 |

## 6. 结论与读法纪律

> Every rung/axis block flips its verdict across the four unresolved policies (8/8): the same data clears the 0.90 ordering bar under the optimistic policy and fails it under the pessimistic one, with a policy band of width 0.37-1.82. The point orderings agree (rho ~ 0.8) but the evidence does not identify them: the certified ordering keeps only 11-17 of the 18 tiers (and 6 of 10 in the C0->C1 reduction block), up to 3 molecules share a single tier, and 1-17 pairs per block sit within 25% of the resolution threshold. The dominant failure mode is loss of rank identifiability, not rank inversion.

读法纪律（新增，与 R15 循环性审计配套）：

1. 引用 `tau_b` 时必须说明它是对**全排序**的点统计量，不含证据门槛；
2. 引用「排序稳定/不稳定」时必须给出**政策带**或 `f_unresolved`，不能只给一个数；
3. 不得把「18 个分子 → 11–17 个可分层层」说成「排序已确定」。

## 7. 复现

```powershell
.venv\Scripts\python.exe scripts\audit_metric_robustness.py --check
.venv\Scripts\python.exe scripts\audit_metric_robustness.py
```
