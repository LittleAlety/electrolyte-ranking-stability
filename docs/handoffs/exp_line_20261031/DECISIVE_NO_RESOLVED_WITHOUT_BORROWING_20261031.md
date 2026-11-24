# 决定性发现：不借被取消探针 ⇒ 这条腿**无法**达到 `resolved`（2026-10-31，实测）

> 方法：**直接调用**真实函数 `coverage_route()`（`build_coverage_reviews.py`），
> 输入形状照生成器 `build_rows` 的真实用法（`computed` 成员 + `novelty` + `starts` + `search_outcome` + `production_evidence`）。
> 探针：`work/exp_line20261031/probe_coverage_route_under_p2.py`，**4/4 测量通过**，无生产写入。

## 1. 四个场景的实测输出

| 场景 | 输入 | `route` | `verdict`（按生成器 `:414-425` 映射） |
|---|---|---|---|
| **S1** | `computed` 成员 + `starts=[]`（**不借被取消探针**） | **`known_basin_reproduction`** | **`unresolved`** |
| **S2** | `computed` 成员 + `starts=["tors_7_0_1_2"]`（借被取消探针） | **`single_basin_verified`** | **`resolved`** |
| S3 | `computed` + 借探针，但 dedup `novelty=unresolved` | `dedup_evidence_required` | `unresolved` |
| S4 | `computed` + 借探针，但 `production_evidence=False` | `known_basin_reproduction` | `unresolved` |

原文摘录（探针输出）：
- S1：`computed start(s) reproduced known minima; no registered search scope documents whether an undiscovered production basin exists`
- S2：`computed start(s) reproduced the single known minimum, and the production evidence + registered search scope are complete: a single-basin ensemble is legitimate here`

## 2. 结论（直接回答你要求 A 复审的问 2）

**在"不借被取消的 `tors_7_0_1_2` 探针背书"的前提下，这条腿即使跑到 `computed`，覆盖审也只能返回 `known_basin_reproduction → unresolved`。**

⇒ **`single_basin_verified` 的必要条件里，"已登记搜索范围"（R7）无法用本腿自身满足**：
本腿的 `seed=p5li_vtscf16` 不以 `tors_` 开头、`source_kind` 也不是 `p4v2_screening_v1_start`（这是**为了不蹭通道而有意如此**），
而 `starts` 的两个来源（冻结清单 `start_1/2_basin` 为空；`_probe_starts` 不认本 seed）**都给不出**它。

**换句话说**：你拒绝的"用已取消探针背书"，恰恰是这条路径**唯一**能让 `single_basin_verified` 成立的输入。
这不是实现缺陷，而是**证据结构的事实**：本腿**不产生**搜索范围信息（它从一个已知极小出发、复现同一极小），
所以它**不能**证明"这个态在冻结搜索范围内只有一个盆地"。

## 3. 对 P1/P2/P3 的影响（我上一轮的建议需要修正）

| 路径 | 原评估 | 修正后 |
|---|---|---|
| **P1**（`recovery_v1_start` 登记） | 可推进 | **无意义**：登记后即便腿成功，也只到 `known_basin_reproduction → unresolved`，却先付出 `limited → provisional` 的标签迁移 |
| **P2**（新前缀角色、标签不动） | 建议 | **无意义**：同理，覆盖审仍 `unresolved`；P2 只保证"看得见"，不保证"能 resolved" |
| **P3**（不登记） | 备选 | **现在成为唯一合理选项**（在找到诚实的搜索范围证据之前） |

**我上一轮把 P2 说成"建议"是过早的**——我当时只验证了"看得见"，没有验证"看得见之后能否 resolved"。本轮补上了这一步，结论反转。这是我应该更早做的事：**先问"登记之后会得到什么结论"，再谈登记方式。**

## 4. 真正缺的是什么（诚实表述）

要让 `DMC|LiM_2plus` 从 `limited` 推进，需要的**不是**"本腿的登记"，而是**该态自身的已登记搜索范围证据**之一：

1. **冻结清单里补 `start_1_basin`/`start_2_basin`**（`strict_recovery_v1_manifest.csv:2` 现为空）——但它是**生成物**，手改会被重建覆盖，须改生成它的源；
2. **或**由一次**真正的搜索**（多个独立起点、覆盖构象空间）产出 `search_outcome` 与 `starts`——这是**新计算**，不在本轮授权内；
3. **或**你在裁决中明确接受"用 `tors_7_0_1_2` 作为该态的历史搜索范围证据"——**你已明确不批**（"不借已取消探针背书"）。

⇒ 三条路里，只有第 3 条是 0 CH，但**你已否决**；第 1 条需定位并修改生成物源（工作量中等、0 CH）；第 2 条需新授权。

## 5. 当前状态（实测，本轮零生产写入）

| 项 | 值 |
|---|---|
| 提交 | **0**（无 `submission_journal.json`、无提交锁） |
| 包 | `submission_gate=HOLD`、`submitted=false`、`sha256sum -c` **14/14 OK** |
| 候选表 | **未改**（123 行，无 `p5li_vtscf16`） |
| 正式记录 | **45 accepted / 3 limited，分母 48** |
| A 复检（t10） | 已派发、**尚未认领**；本文件是 Lead 的独立前置测定，**不替代** A 的复审 |