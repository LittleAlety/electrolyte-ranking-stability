# Gate 1 = negative result（双轨定位，R13）

## 1. 事实

Gate 1 有两层：

| 层 | 判据 | 状态 |
| --- | --- | --- |
| 排序一致性层 | within-series 相对排序被 target model 复现（`scripts/check_series_rel_ordering.py`） | **未通过**：Kendall **τ_b = 0.4286 < 0.90**、n_pairs = 21 → `ordering_disagrees` |
| 绝对标定层 | 31 行 solution anchor 逐条可追溯到条件匹配的一次测量 | 仍全部 `est`（transcription-only）→ 按 R7 记为 **limitation**，不再单列 blocker |

来源：`outputs/week25/series_rel_ordering_check.json`、`data/anchors/solution_anchor_verification.md`。

## 1b. 最终定性：NOT CLOSED **且** NOT CLOSABLE（研究结果，不是待办缺陷）

**结论（一句话）**：在预注册要求的同装置 / 同判据 / 至少 7 个核心集分子的同源序列条件下，公开可验证数据不足，因此无法完成排序层外部锚定。

这不是“还没做完”，而是“在当前可得证据下不可闭合”。判据如下：

| 预注册关闭条件（同装置 / 同判据 / 同态） | 要求 | 现状 |
| --- | --- | --- |
| 同源序列覆盖核心集 | ≥ 7 个分子（C(7,2)=21 ≥ n_pairs 18） | 最长同源序列 **k = 1** |
| 排序一致性 | Kendall τ_b ≥ 0.90 | 唯一可评序列 = **0.4286** |
| 绝对标定层 | 至少一行升级至 exp/calc | **0 / 31**（仍 `est`） |

因此 Gate 1 从此**作为研究结果**报告：**NOT CLOSED 且 NOT CLOSABLE**。禁止事后通过剔除分子 / 替换模型列 / 放宽容差把它「救」成 PASS；也不再为它无限追加周次计算。

机器可读形式：`outputs/gate1/gate1_dual_track.json` 的`gate1_closability = "NOT CLOSABLE"` 与 `track_B.components.closability`（含预注册条件、证据、结论）。

## 1c. 措辞边界：NOT CLOSABLE ≠ 世上不存在这类数据

**这个负结果是可被证伪的**，而不是一条不可动摇的断言。它只声称：

> 在预注册的发现 / 验证标准（同装置 · 同判据 · 同态 · ≥7 个核心集分子的同源序列）下，**未定位到**足以关闭排序层的外部数据。

它**不**声称这类数据在世界上不存在。absence of evidence 不等于 evidence of absence：

```text
NOT CLOSABLE
≠  NO SUCH DATA EXIST ANYWHERE
=
NO SUFFICIENTLY VERIFIED DATA WERE LOCATED
UNDER THE PRE-REGISTERED DISCOVERY / VALIDATION CRITERIA
```

若日后出现满足全部预注册条件的同源序列，本判定应被该数据直接推翻。机器可读形式为 `track_B.components.closability.scope_caveat` / `scope_caveat_en`（`outputs/gate1/gate1_dual_track.json`）。

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
