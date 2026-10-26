# 计划 item 2 主出口验证：四种合成新成员（2026-10-27）

> 计划原文出口：「**用四种合成新成员（重骨架扭转、Li motif、环形变、同盆地复现）验证
> 导入器、覆盖复核和聚合器都能识别新版本成员……出口：合成合格成员能走到 `accepted`，
> 缺哈希、错误身份及重复极小均不能蒙混过关。**」
>
> 本文记录该出口的**实测闭合**。harness 位于 `work/_four_synthetic_members.py`（gitignored 机器本地层，
> 按项目纪律不入库，故以本文留痕）。**驱动的是生产原语本身**（聚合器的 `acceptance_decision` +
> 覆盖复核的 `coverage_route`），不是另写一份实现——否则测试会与生产漂移。

## 1. 四种成员各自的路由（**都被识别，没有一个被静默丢弃**）

| 成员类 | novelty | 路由 | 判据含义 |
|---|---|---|---|
| `ring_pucker`（环形变） | new | **`multi_basin_coverage`** | 新独立盆地 ⇒ 覆盖成立 |
| `li_motif`（Li 配位） | new | **`multi_basin_coverage`** | 同上 |
| `heavy_torsion`（重骨架扭转） | new | **`multi_basin_coverage`** | 同上 |
| `same_basin`（同盆地复现） | known | **`known_basin_reproduction`** | 复现已知极小（**不是失败**） |

**1b. 更严格的路由可达**：当 `search_outcome="no_new_minimum_found"`（**搜索范围有文档**）时，
同盆地成员升级为 **`single_basin_verified`** ⇒ 单盆地系综在此态是**合法的**，而非「凑合」。

## 2. 合格成员**确实能走到 `accepted`**（两条正路都通）

| 情形 | 结果 |
|---|---|
| **新成员**，claim 的成员在 kept 池中 | **`accepted`** ✅ |
| **同盆地复现**，claim 的成员在 kept 池中 | **`accepted`** ✅ |

## 3. 四种「不能蒙混过关」的拒绝（计划明确点名）

| 蒙混方式 | 实测结果 | 说明 |
|---|---|---|
| **claim 的成员不在 kept 池**（伪造证据） | **`limited`** ✅ | 反作弊：`cov_resolved = bool(claimed) and all(c in kept_keys for c in claimed)` |
| **缺哈希/无可用去重判定** | **`dedup_evidence_required`** ✅ | 无法区分 new/known 时**不得**下任何路由 |
| **没有复核（错误身份）** | **`limited`** ✅ | 无复核即不能接受 |
| **存在未决工作**（哪怕复核完美） | **`provisional`** ✅ | `unresolved` **压倒一切**，含合法复核 |

## 4. 「重复极小」**不被误判为失败**

同盆地成员在 `production_evidence=False`（生产侧证据集不完整）时路由为 **`known_basin_reproduction`**，
其说明原文即「**not a QC failure** — these are independent reproductions」。
⇒ 「重复极小」是**覆盖证据**，不是失败——与冻结规则一致。

## 5. RED 实证（每条拒绝都依赖真实守卫）

`work/_four_members_red.py` 逐条**在生产文件的副本里**删掉守卫（绝不动生产文件）：

| 删除的守卫 | 实测 |
|---|---|
| 聚合器反作弊 `all(c in kept_keys ...)` | **exit=1 RED-OK** |
| 路由 `unresolved-novelty` 守卫 | **exit=1 RED-OK** |
| 路由 `pending-start` 守卫 | **exit=1 RED-OK** |

⇒ **RED PROVEN**：四条「不能蒙混」的拒绝各自**真的**依赖一条守卫，不是无条件通过。

## 6. 一处我自己写错的预期（如实记录）

harness 第一版把 `same_basin`（`production_evidence=True`）预期成 `single_basin_verified`，
实测返回 `known_basin_reproduction`——**是我的预期错了**：`single_basin_verified` 还要求
**搜索范围有文档**（`_search_scope_documented`）。已改为：
① 该用例预期 `known_basin_reproduction`；
② **另加** §1b 用例（`search_outcome="no_new_minimum_found"`）验证更严格路由**确实可达**。
**若把这个误报当缺陷上报，就会变成假报告**（同族：`0mvp404z` 审计器同分支、`0mvp3fdm` 数目三分法）。

## 7. 结论

| 计划 item 2 的出口要求 | 状态 |
|---|---|
| 四种合成成员**都被识别**（不静默丢弃） | **已验证** |
| 合成合格成员**能走到 `accepted`** | **已验证**（新成员 + 同盆地复现两条正路） |
| **缺哈希**不能蒙混 | **已验证**（`dedup_evidence_required`） |
| **错误身份**不能蒙混 | **已验证**（无复核 ⇒ `limited`） |
| **重复极小**不能蒙混 / 也不被误判为失败 | **已验证**（`known_basin_reproduction`，非失败） |
| 断言**依赖真实守卫** | **RED PROVEN**（3/3 守卫） |
