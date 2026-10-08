# Gate 1 = negative result（双轨定位，R13）

## 1. 事实

Gate 1 有两层：

| 层 | 判据 | 状态 |
| --- | --- | --- |
| 排序一致性层 | within-series 相对排序被 target model 复现（`scripts/check_series_rel_ordering.py`） | **未通过**：Kendall **τ_b = 0.4286 < 0.90**、n_pairs = 21 → `ordering_disagrees` |
| 绝对标定层 | 31 行 solution anchor 逐条可追溯到条件匹配的一次测量 | 仍全部 `est`（transcription-only）→ 按 R7 记为 **limitation**，不再单列 blocker |

来源：`outputs/week25/series_rel_ordering_check.json`、`data/anchors/solution_anchor_verification.md`。

## 2. 决定：不修数据，改叙事

外部评审给出的关键判断是：

> **不要让外部有效性把整个项目定义成「失败」。**

R13 因此把项目分成两条互不依赖的轨道：

```
Track A   Decision-stability study
          P0 → P1v → P1a → P2a/P2eps → C1 → C2
          问：哪些 missing physics 会改变材料筛选决策？
          状态：computationally established（独立成立）

Track B   Experimental validity
          computed ranking  →  external solution ranking
          状态：Gate 1 NOT CLOSED（negative result，如实记录）
```

Track A 的全部结论**不依赖** Track B 是否闭合。Track B 未闭合只限制「绝对尺度与真实排序」的声明强度。

## 3. 措辞规范（R13 起强制）

| 禁止 | 允许 |
| --- | --- |
| validated target | **designated computational target** |
| physically validated target | **designated reference model** |
| 「方法已被实验验证」 | 「在本 core set 上，计算排序与外部 within-series 排序**不一致**（negative result）」 |

解禁条件（`target_naming.lift_condition`）：只有当 Gate 1（含 ordering-consistency tier）**CLOSED** 之后，
才可恢复 `validated` 字样。

## 4. 为什么这是更强的科学叙事

把 Gate 1 的失败当成结果而不是缺陷，项目的问题从

> 「18 个电解液分子，用 xTB + DFT 看排序是否一致」

升级为

> **「定量研究缺失物理何时真正改变材料筛选决策，以及达到可靠排序所需的最小计算信息」**——
> 其中外部有效性边界被明确定义、单独报告。

这与 v2 反复强调的 `model complexity ≠ accuracy ≠ physical representativeness` 完全一致。
