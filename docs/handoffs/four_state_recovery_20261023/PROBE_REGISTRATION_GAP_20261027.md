# 覆盖复核未登记 P4/v2 探针——一处**待裁定的登记缺口**（2026-10-27）

> 本轮在核对「DOL/EC 为何是 `search_exhausted`」时发现一处**真实缺口**。
> **本文只诊断与呈报，不修改任何 verdict、不放宽任何规则**——因为修它等于改变机器判定的输入。
> **纯只读、零计算。**

## 1. 事实链（每步实测）

1. `accepted` **只能**由 `acceptance_decision` 产生，判据是 **`cov.verdict == "resolved"`**（`3abe7b3` 已查明）。
2. `verdict == "resolved"` 只由两条 route 产生：**`multi_basin_coverage`** 与 **`single_basin_verified`**
   （`build_coverage_reviews.py:358-359`）；`known_basin_reproduction` ⇒ **`unresolved`**（`:361-362`）。
3. 那么 DOL/EC 为何走了 **`search_exhausted`**？——因为 `coverage_route` 的该分支要求
   **`latest_members` 为空**（`build_coverage_reviews.py:176-188`）：即「**登记了起点但没跑**」才能判 `search_exhausted`。
4. **而 P4/v2 实际跑了 28 条探针**（P4 job `3774215` 8 条 + v2 job `3777206` 20 条）。⇒ **矛盾**。
5. 根因：**探针从未登记进覆盖复核的输入**。
   - `registered_starts` 由 `starts` 组装（`build_coverage_reviews.py:250-256`）：
     冻结 recovery 行（`manifest` 的 `start_1_basin`/`start_2_basin`）**并集** `_probe_starts(name, state)`。
   - `_probe_starts`（`:84-103`）读 `outputs/physics_completion/ensembles/production_ensemble_candidates.csv`，
     且**只收 `seed.startswith("tors_")`**（`:101`）。
   - **实测该 CSV（119 行）里 DOL/EC 的 `LiM_2plus` 只有 `c01`/`c03`/`c05` 这类旧种子**，
     **没有任何 P4/v2 探针种子**（其命名是 `ring_pucker_00` / `li_coordination_away_00` / `p4_01_torsion_*`，
     **不以 `tors_` 开头**）。
   ⇒ 两道过滤**同时**拦下：文件里没有 + 前缀不匹配。故 `starts` 为空 ⇒ `search_exhausted`。

## 2. 这个缺口意味着什么（**关键**）

若探针结果**按规则登记**为 `computed` 成员，且其 **dedup verdict 为 `known`**（复现已知极小）、
且 `search_outcome` 有文档，则本机只读调用 `coverage_route` 实测得到：

| 输入 | route | verdict | ⇒ acceptance |
|---|---|---|---|
| 无起点 + 搜索无新盆地（**现状**） | `search_exhausted` | `search_exhausted` | **`limited`** |
| **有起点（`computed`,`known`）+ 搜索范围有文档** | **`single_basin_verified`** | **`resolved`** | **`accepted`** |
| 有起点（`computed`,`known`）+ 生产证据缺失 | `known_basin_reproduction` | `unresolved` | `limited` |

⇒ **DOL/EC 存在一条「已被现行规则支持、但因登记缺失而未走」的路径**：
`探针登记 → known → 搜索范围有文档 → single_basin_verified → resolved → accepted`。

## 3. 但**不能**据此宣布「可以恢复」——三个必须核实的门槛

| # | 门槛 | 现状 |
|---|---|---|
| 1 | **探针是否算「登记起点」** | **未定**：P4/v2 是**授权下的筛选探针**，从未作为 `production_ensemble_candidates.csv` 的 registered start 登记。这是**口径问题**，须由你裁定 |
| 2 | **`search_outcome` 是否有文档** | 需 `_search_scope_documented` 为真（`:150-160`），即 `search_outcome ∈ {new_minima_found, no_new_minimum_found, unused_pool_basin_no_search_needed}` **且 starts 非空** |
| 3 | **生产侧证据是否完整** | `production_evidence` 要求每个 computed 成员都有 `imaginary_modes`/`final_geometry_sha256`/`log_sha256`（`:333-338`）；**探针是 GFN2 单点+优化，不是 wB97X-D4 生产腿** ⇒ 这一条**很可能不满足** |

**门槛 3 尤其要紧**：「探针复现了已知极小」在 **GFN2 层**成立，但 `single_basin_verified` 的语义是
「**生产侧**已确认单盆地」。把 GFN2 探针当生产证据，可能违反「不把 GFN2 当生产自由能」的红线。

## 4. 我的建议（**不自行执行**）

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