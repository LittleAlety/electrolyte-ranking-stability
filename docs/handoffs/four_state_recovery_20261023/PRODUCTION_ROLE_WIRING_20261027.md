# DOL/EC 生产腿的**登记接线要求**（2026-10-27）——写错角色 = 静默阻塞整条接受路径

> 本轮为 DOL/EC 生产批补一项**此前未核**的接线约束：新生产腿必须以**正确的 `member_role`** 登记，
> 否则**永远不会进 `latest_members`**，状态**永远停在 `limited`**——且**不报任何错**。
> 这正是计划 item 2 警告的「**计算成功之后才发现验收器无入口**」。**纯只读。**

## 1. 代码里的硬约束（实测）

`build_production_ensemble_aggregator.py` 的白名单（两处，语义一致）：

| 位置 | 内容 |
|---|---|
| **`:610`** | `if r["member_role"] in ("round1_extra", "recovery_v1_start"):` → 才进 `regs`（注册成员） |
| **`:696`** | `if r["member_role"] not in ("round1_extra", "recovery_v1_start"): continue` → 才进 `latest`（最新尝试） |

**`:691-696` 的注释就是一份事故报告**：
> 「**EVERY first-class member role must be listed here. A missing role is not a cosmetic omission:
> the member then never enters `latest`, the aggregator reads it as "registered but no result yet" (`n_pending`)
> and the state can never leave `limited` — `recovery_v1_start` was missing exactly so,
> which silently blocked the whole acceptance path.**」

## 2. 现有四类角色与它们的**资格**（`production_ensemble_structures.csv`，238 行）

| `member_role` | 行数 | **进 `latest`？** | 计入接受？ | 说明 |
|---|---|---|---|---|
| `primary` | 48 | — （走另一条路，`:367`/`:393`/`:780`） | 基线 | 48 主态腿 |
| **`round1_extra`** | 110 | **✅** | **✅** | 第一轮 extras 及其救援 |
| **`recovery_v1_start`** | 44 | **✅** | **✅** | `strict_recovery_v1` 的**新独立极小**（一类成员） |
| **`round2_audit_extra`** | 36 | **❌** | **仅 ceiling**（`:608` 注释：*ceiling-only*） | **登记成它会静默阻塞接受路径** |

**⇒ 新生产腿必须登记为 `round1_extra` 或 `recovery_v1_start` 之一。**
本批是「**新的独立起点验证**」⇒ 语义上对应 **`recovery_v1_start`**（`:606-608`：
"a NEW independent minimum … It is a first-class member"）。

## 3. 对 DOL/EC 生产批的具体要求

| # | 要求 |
|---|---|
| 1 | 新腿在 `production_ensemble_structures.csv` 里 `member_role = **recovery_v1_start**`（或经你裁定用 `round1_extra`） |
| 2 | **`member_key` 必须与 `coverage_reviews.csv` 里该态的证据列一致**（聚合器用 `kept_keys` 做反作弊：`:649-651` 要求 claim 的成员在 kept 池中） |
| 3 | **`status` 必须最终为 `computed`**（`build_coverage_reviews.py:175` 只把 `computed` 计入 `passed`；`technical_complete_qc_failed` 不计） |
| 4 | **`production_evidence` 三个字段须非空**：`imaginary_modes`、`final_geometry_sha256`、`log_sha256`（`build_coverage_reviews.py:334-338`）**且**过冻结五阈值与身份 QC |
| 5 | 复核的 `search_outcome` 须属 `{new_minima_found, no_new_minimum_found, unused_pool_basin_no_search_needed}` 且 `registered_starts` 非空（`build_coverage_reviews.py:150-160`） |
| 6 | 「**新版本成员须另立命名族且序号高于该成员全部历史序号**」（项目红线） |

## 4. 这是**第二个**「静默阻塞」类接线约束（须记住）

| # | 约束 | 后果 | 状态 |
|---|---|---|---|
| 1 | `search_exhausted` 分支要求 `latest_members` 为空（即**必须有生产恢复成员**） | 只补登记不恢复 | 已在 `0mvp79e3` 更正并记住 |
| 2 | **`member_role` 不在白名单 ⇒ 永不进 `latest`** | **状态永远 `limited`，且不报错** | **本文新增** |

**两者共同点**：**「有结果」不等于「被系统看见」**——中间隔着一层**登记/角色白名单**，而它**失败是静默的**。

## 5. 守线

- ⛔ 不改 `:610` / `:696` 的白名单（改它会**改变历史成员的资格语义**，须无翻转证明 + 版本化）；
- ⛔ 不把本批登记成 `round2_audit_extra`（那会**故意制造静默阻塞**）；
- ⛔ 未获授权前不提交。

## 6. 证据出处

- 白名单：`build_production_ensemble_aggregator.py:610`、`:696`（含 `:691-696` 事故注释）
- 角色分布：`outputs/physics_completion/ensembles/production_ensemble_structures.csv`（238 行，实测四类）
- `passed` 判据：`build_coverage_reviews.py:175`；`production_evidence`：`build_coverage_reviews.py:334-338`；反作弊：`build_production_ensemble_aggregator.py:649-651`
- 搜索范围：`build_coverage_reviews.py:150-160`
- 相关：`INDEPENDENT_START_CRITERIA_20261027.md`、`0mvp79e3`