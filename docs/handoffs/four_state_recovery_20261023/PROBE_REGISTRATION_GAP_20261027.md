# 覆盖复核未登记 P4/v2 探针——一处**接线不完整**（2026-10-27，**经用户纠正后更正**）

> **⚠ 本文核心推断已被用户纠正并经我方实测确认为错——保留原文并加更正，不抹除。**
>
> **错在哪**：我把 `search_exhausted` 分支的条件 `not latest_members`（`:177`）解释为
> 「**登记了起点但没跑**」。**这是误读。** 用户指出：`latest_members` 是**已选入复核的生产恢复成员**，
> **不是** `registered_starts`。我方**实测复现该反例**：
>
> | 输入 | route |
> |---|---|
> | 无 starts | `search_exhausted` |
> | **只加 `registered_starts`（仍是空生产成员）** | **仍然是 `search_exhausted`** ✅ **用户正确** |
> | 有 `computed` 生产成员 + 生产证据齐全 | `single_basin_verified` |
> | 有 `computed` 生产成员 + 生产证据缺失 | `known_basin_reproduction` |
>
> ⇒ **只补登记并不能改变 route**；要离开 `search_exhausted` **必须有生产侧的 `computed` 成员**。
> 故我原文「补登记即可走 single_basin_verified」的暗示**不成立**，**必须撤回**。
>
> **仍然成立的部分**：P4/v2 的 28 条探针**确实没有登记进 `coverage_reviews` 的起点集合**
> （`_probe_starts` 只收 `tors_` 前缀、且候选 CSV 里根本没有这些种子）——**这是真的接线缺口**，
> 但它**不是**「accepted 被登记遗漏挡住」的原因。

## 0. 结论（更正后）

**接线不完整是真的；据此外推「补登记就能 recovered」是错的。**
正确关系：`search_exhausted` ↔ **无生产恢复成员**；恢复**必须**有**生产级 `computed` 成员**
（`single_basin_verified` 还要求生产证据齐全 + 搜索范围有文档）。
**补齐登记只是把筛选证据接上线，不能代替生产计算。**

## 1. 事实链（每步实测）

1. `accepted` **只能**由 `acceptance_decision` 产生，判据是 **`cov.verdict == "resolved"`**（`3abe7b3`）。
2. `verdict == "resolved"` 只由 **`multi_basin_coverage`** 与 **`single_basin_verified`** 产生（`:358-359`）；
   `known_basin_reproduction` ⇒ **`unresolved`**（`:361-362`）。
3. `search_exhausted` 的条件是 **`not latest_members` 且 `search_outcome == "no_new_minimum_found"`**（`:176-185`），
   其中 **`latest_members` ＝ 已选入复核的「生产恢复成员」**，与 `registered_starts` **不是同一概念**（`:172-190`）。
4. **实测**：`registered_starts` 非空而 `latest_members` 为空 ⇒ **仍是 `search_exhausted`**（用户反例，我方已复现）。
5. 真正的接线缺口：`registered_starts` 由 `:250-256` 组装 = 冻结 recovery 行 ∪ `_probe_starts()`；
   而 `_probe_starts()`（`:84-103`）**只收 `seed.startswith("tors_")`**（`:101`），
   且实测 `production_ensemble_candidates.csv`（119 行）里 **DOL/EC 的 `LiM_2plus` 只有 `c01`/`c03`/`c05` 等旧种子，
   没有任何 P4/v2 探针**（命名 `ring_pucker_00`/`li_coordination_away_00`/`p4_01_torsion_*`，**不以 `tors_` 开头**）。
   ⇒ **筛选证据没有接上线**，但这**只影响「搜索范围文档」一侧**，**不改变 `search_exhausted` 的成立条件**。



## 2. 这个缺口意味着什么（**关键**）

若探针结果**按规则登记**为 `computed` 成员，且其 **dedup verdict 为 `known`**（复现已知极小）、
且 `search_outcome` 有文档，则本机只读调用 `coverage_route` 实测得到：

| 输入 | route | verdict | ⇒ acceptance |
|---|---|---|---|
| 无起点 + 搜索无新盆地（**现状**） | `search_exhausted` | `search_exhausted` | **`limited`** |
| **有起点（`computed`,`known`）+ 搜索范围有文档** | **`single_basin_verified`** | **`resolved`** | **`accepted`** |
| 有起点（`computed`,`known`）+ 生产证据缺失 | `known_basin_reproduction` | `unresolved` | `limited` |

⇒ **⚠ 更正（用户纠正 + 我方实测）**：上表第一行「有起点(`computed`,`known`)+搜索范围有文档」中的
**「起点」必须是「生产恢复成员（`latest_members`）」**，**不是 `registered_starts`**。
故**不能**说「DOL/EC 因登记缺失而未走这条路」——补登记**不改变** route（实测仍 `search_exhausted`）。
**正确表述**：DOL/EC 要走 `single_basin_verified`，**必须有一个或多个人生产级 `computed` 成员**
（严格优化 + AnFreq + 身份 QC + 去重，且生产证据齐全）；**登记只是接线，不能代替计算**。

## 3. 但**不能**据此宣布「可以恢复」——三个必须核实的门槛

| # | 门槛 | 现状 |
|---|---|---|
| 1 | **探针是否算「登记起点」** | **未定**：P4/v2 是**授权下的筛选探针**，从未作为 `production_ensemble_candidates.csv` 的 registered start 登记。这是**口径问题**，须由你裁定 |
| 2 | **`search_outcome` 是否有文档** | 需 `_search_scope_documented` 为真（`:150-160`），即 `search_outcome ∈ {new_minima_found, no_new_minimum_found, unused_pool_basin_no_search_needed}` **且 starts 非空** |
| 3 | **生产侧证据是否完整** | `production_evidence` 要求每个 computed 成员都有 `imaginary_modes`/`final_geometry_sha256`/`log_sha256`（`:333-338`）；**探针是 GFN2 单点+优化，不是 wB97X-D4 生产腿** ⇒ 这一条**很可能不满足** |

**门槛 3 尤其要紧**：「探针复现了已知极小」在 **GFN2 层**成立，但 `single_basin_verified` 的语义是
「**生产侧**已确认单盆地」。把 GFN2 探针当生产证据，可能违反「不把 GFN2 当生产自由能」的红线。

## 3.5 用户裁定（2026-10-27，**已采纳，取代 §4 我的建议**）

| 待裁定事项 | 用户裁定 |
|---|---|
| **P4/v2 是否登记** | **作为「筛选证据」登记：是**；**直接作为生产级 `computed` 成员：否**。另建**版本化映射**，保留原始执行时间、方法、几何与日志哈希 |
| **H2 是否执行** | **暂不作为恢复前置条件**。修正验收缺口后**可做小额能量诊断**；但**单点结果不能证明同盆地，也不能替代生产覆盖证据** |
| **H3 是否结题** | **可定稿本轮限制报告**，保留 **44/48** 与严格目标未完成。**明确不同意**「探针不属生产证据 ⇒ 永久终局」这一推论 |
| **S2 与阈值** | **沿用 `away_01`**；0.35／1.0／3.0 **只能作明确标注的描述性分档，不用于判定盆地相同或不同** |

**用户给执行侧的下一步顺序（4 步）**：
1. **补齐 28 条筛选证据的登记与引用**——按态拆分：DOL/EC 合计 **24** 条、DMC 两态合计 **4** 条；
   注明这是**历史执行证据的补接线**，**不能伪装成事前生产预注册**；**补登记后的验收预期仍为 44/4**。
2. **为 DOL/EC 各准备一个生产级覆盖验证方案**——从可追溯、经**非刚体与身份预检**的**独立起点**出发，
   冻结候选、次数、成本与停止条件；**单纯重复提交已知极小的相同几何，不能冒充独立搜索**。
3. **通过真实生产计算补足证据**——冻结方法下完成严格优化、`AnFreq`、身份 QC 与去重，
   由 importer 验证方法与原始文件；**`imaginary_modes`、两个哈希字段「非空」本身不足以证明生产证据合格**。
4. **按结果自动走覆盖路线**：QC 通过且复现已接受极小 + 搜索范围与其他证据齐全 ⇒ **`single_basin_verified`**；
   通过 QC 且得新极小 ⇒ **`multi_basin_coverage`**；QC 失败或证据不完整 ⇒ **继续 `limited`**，保留原因与成本。

**用户的核心结论（原话要旨）**：
> 「**DOL/EC 不必强行找到第二个极小才能恢复，但必须证明独立起点在生产方法下通过了验证。**
> **『版本化登记』能够建立这条证据链，不能替代其中的计算。**」

## 4. 我的建议（**不自行执行**）——⚠ **已被用户裁定取代（见 §3.5）**，仅作过程记录

> 本文 §4 原建议的第 3 条（「若裁定为是，须另立版本化登记批次」）与用户裁定方向一致；
> 但**第 4 条「若裁定为否，则 `search_exhausted` 就是终局」已被用户明确否定**
> （原话要旨：「**不同意『探针不属生产证据，所以永久终局』这个推论**」）。
> **以 §3.5 为准。**


1. **不修改** `coverage_reviews.csv`、**不放宽** `_probe_starts` 的前缀过滤、**不改** `coverage_route`；
2. **把本缺口作为一项独立裁定**呈报：**「P4/v2 探针是否构成 `single_basin_verified` 所需的已登记起点」**；
3. 若你的裁定是「**是**」，则需**另立一个版本化的登记批次**（把探针正式登记为 candidates，
   并明确其 `search_outcome` 文档），**而不是事后把 verdict 改写成 `resolved`**；
4. 若裁定是「**否**」（探针不属于该 route 的证据类型），则 **DOL/EC 的 `search_exhausted` 就是终局**，
   **H3 按其「停止条件」语义结题**。
5. **H2 的价值因此上升**：它检验的正是「GFN2 单盆地是否可信」——**无论上面哪条裁定成立，H2 都是它们的科学前提**。

## 5. 明确不做的事（守线）

- ⛔ **不**把 `search_exhausted` 改写成 `resolved`；
- ⛔ **不**手工往 `coverage_reviews.csv` 里补 `registered_starts`；
- ⛔ **不**为了让 DOL/EC 变 `accepted` 而放松 `single_basin_verified` 的生产证据要求；
- ⛔ **不**把 GFN2 探针当生产腿证据（红线：不把 GFN2 当生产自由能）。

## 6. 证据出处

- 路由与 verdict：`build_coverage_reviews.py` `coverage_route`(`:163-223`)、`_search_scope_documented`(`:150-160`)、
  verdict 映射(`:358-362`)、`starts` 组装(`:250-256`)、`_probe_starts`(`:84-103`)
- 接受通道：`build_production_ensemble_aggregator.py` `acceptance_decision`(`:619-657`)
- 实测数据：`outputs/physics_completion/recovery/coverage_reviews.csv`（14 行）、
  `outputs/physics_completion/ensembles/production_ensemble_candidates.csv`（119 行）
- 探针执行证据：P4 `3774215`、v2 `3777206`（`P4/V2_RESULTS_ADJUDICATION`、`P4_SETTLEMENT_20261025.md`）