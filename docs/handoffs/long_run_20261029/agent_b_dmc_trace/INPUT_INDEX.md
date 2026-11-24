# INPUT_INDEX —— t10 输入清单与 sha256（含 attribution 声明）

## 0. 交付面归属声明（请 Lead 先读）

- 本目录 `docs/handoffs/long_run_20261029/agent_b_dmc_trace/` 由会话 **`dol-log-auditor`** 写出。
- **共享任务板 t10 的 owner 是 `triage-auditor`**（claim 时间 2026-10-28T23:46:25.941Z，`claimKind=auto`，ownerSessionId `session-7a469da9-…`），而该成员 **已 inactive 且上一轮致命失败**：`EAC_UPSTREAM_FAILED` —— 「The model 'z-ai/glm-5.3' has reached its end of life on 2026-10-28T08:00:00Z and is no longer available.」
- 我依 Lead 简报执行本任务（简报指定输出到本目录、目录名 `agent_b_*` 即本方角色），但**无法经任务板取得所有权**——实测两次被拒：
  - `team_task_update(action="claim", task_id="t10", expected_revision=2)` → `Error: task "t10" is owned by "triage-auditor"; release or reassign it first`
  - `team_task_update(action="release", task_id="t10", expected_revision=2)` → `Error: task "t10" is owned by "triage-auditor"`
  - 另：简报给的 `expected_revision=1` **已过期**（实测 revision=2）。
- ⇒ **本次产物是在「板上归属未变更」的情况下写出的**。请 Lead 二选一收口：① `assign`（Lead-only）把 t10 归到 `dol-log-auditor`；② 或改派他人——若改派，**请先删除本目录**以免与新作者冲突（同一写入面不得两写者）。
- 本目录**仅这 4 个文件**（TRACE / MATRIX / DECISION / INPUT_INDEX），无脚本、无测试产物。

## 1. 点名的输入（任务简报逐条要求）

| 输入 | sha256 | 用途 |
|---|---|---|
| `config/production_method_freeze_v1.json` | `b19488e4c4f4a4616ab12996e8a70b901c79a13f6e6b0c73ae0fa42e8000050d` | 冻结五阈值 + 方法（`geometry_convergence_policy.thresholds`） |
| `outputs/physics_completion/recovery/strict_recovery_v1_report.md` | `889c21d8c99f1f0429c64d37344f3cccd153688ba3ea1acf94245b7183ac11e2` | §逐态明细（`:63-64`）= DMC 两态 6 条恢复腿与失败类别 |
| `outputs/physics_completion/ensembles/production_ensemble_structures.csv` | `3f2c692d2207d935347c3508e095e183e7f25a192952dc84b430b2d023d55df6` | 逐 attempt 的 `log_path`/`log_sha256`/`failure_class`/`energy_change_Eh`（生产族） |
| `outputs/physics_completion/recovery/coverage_reviews.csv` | `db61c188c6ef1652f9551cf1cd554b2c0f9b00b5f2321550b6f3bde0de696876` | 覆盖复核口径（DMC 两行） |
| `docs/handoffs/four_state_recovery_20261023/DMC_THRESHOLD_DIAGNOSIS_20261025.md` | `4943a9f27a10218116a3f4326ccd63da67dc6d26ae920c17cc2e723b5fdd263d` | 既有判读（本单对其关键数字做了逐位复现） |
| `docs/handoffs/four_state_recovery_20261023/DMC_DECISION_BRIEF_20261027.md` | `4e7510270c6b0aab7ab0f43bf06b58b1baae5c73b81c357b831e5980b2ad6176` | 决断呈报（B1 成本量级） |
| `docs/handoffs/four_state_recovery_20261023/recovery_contract.json` | `c9d45851a9f6502ab71fcec7360bca935879c53183eefef4bd865542c5b38d6d` | 预算/授权边界 |

## 2. 被解析的 12 个 ORCA 日志（逐个 sha256，均实测）

生产族（`work/hpc_production_ensemble_*`）：

| # | 态 / 成员 / attempt | job | sha256 |
|---|---|---|---|
| 1 | `M_plus` / `M_plus\|28` / att0 | 3718293_16 | `dd54a5ff33884c2f827e2929da32ef664400ae7f174936215fd5d1cf1fb5f460` |
| 2 | `M_plus` / `M_plus\|28` / att1（reopt4） | 3725968_1 | `11f910020393fcab1ba54ae95ba991c76362b9452e523f2159bb137e88c5bb65` |
| 3 | `LiM_2plus` / `LiM_2plus\|c06` / att0 | 3723647_8 | `de4972de763a05638b6faeacaf8b8db057456be92b9e494f1e3ad45d0b0b852e` |
| 4 | `LiM_2plus` / `LiM_2plus\|c06` / att1（continuation4） | 3727606_2 | `07fd25fdd4be7c36cd29812e13fbda6406834ba27ef86ef7cc2567df2ed692c4` |

恢复族（`work/hpc_torsion_probe_*`）：

| # | 态 / 成员 / attempt | job | sha256 |
|---|---|---|---|
| 5 | `M_plus` / `tors_6_0_1_2` / att0 | 3747714_4 | `01cbd8a210c2a8b7caea17617f8d279de000105192ad1edc470bd1c8b8abfd0b` |
| 6 | `M_plus` / `tors_7_0_1_2` / att0 | 3747714_5 | `d327be96f2e7ea66488ac053e459461e92a8ba9bf5b7b2488fc9b2ce9c441ae2` |
| 7 | `M_plus` / `tors_8_0_1_2` / att0 | 3747714_3 | `0308c3048903758dc32f8a6783d5ae04466575dc586d0c9f11735057c4aae0d6` |
| 8 | `M_plus` / `tors_8_0_1_2` / att1（v2_realfragment） | 3749450_1 | `fa78c69f7fabbbcffa3c6ecda639ad1b55e47a188633404d95dd6ce8874df3ac` |
| 9 | `LiM_2plus` / `tors_6_0_1_2` / att0 | 3747714_7 | `f78a38c84d5953cffebde0ad832d8ac83257b5122ee614c9ab4796dd450c759b` |
| 10 | `LiM_2plus` / `tors_8_0_1_2` / att0 | 3747714_6 | `339f09f8a8a12fa32cb1ac52da5694cc1a2f8687104430b988d31708bf20fc5e` |
| 11 | `LiM_2plus` / `tors_7_0_1_2` / att0（batch2_fragmentfix） | 3748336_0 | `947179a6a8a3454df84638ae31011abfd7946e31ae10e543f2f131afeb0bcb0a` |
| 12 | `LiM_2plus` / `tors_7_0_1_2` / att1（reopt_v3） | 3749453_0 | `3973a13dce5dc01705c7a565abb98104c9ae9b32785862b427677753b595da83` |

> 生产族 4 个日志的 `log_sha256` 与 `production_ensemble_structures.csv` 声明值**逐位一致**（该 CSV 对 #1–#4 分别记 `dd54a5ff…`、`11f91002…`、`de4972de…`、`07fd25fd…`）。

## 3. 本目录产物（非输入）

| 文件 | 说明 |
|---|---|
| `DMC_OPTIMIZATION_TRACE.csv` | 37 行（含表头）= 36 数据行 = 12 attempt × 各末 3 张收敛表；列含 state/member/attempt/job_id/log_sha256/optimization_segment/cycle/source_line_range/E/abs_delta_E/五项 Tol 与 ratio/unit/SCF_status/termination/missing_reason |
| `DMC_FAILURE_MATRIX.csv` | 61 行（含表头）= 12 attempt × 5 准则；含权威 `failure_class`、末值、abs 比值、ORCA 自标 flag、我的判定、末 3 表内是否出现过 PASS/FAIL、证据源行号 |
| `DMC_MECHANISM_DECISION.md` | 逐态回答「改变什么—为何针对失败—如何否定—所需对照—冻结目标如何验证」+ 结论 |
| `INPUT_INDEX.md` | 本文件 |

## 4. 解析契约与偏离声明

- **列集合是对简报的严格超集**：简报 TRACE 栏位写到 `ratio`（单列）为止；因五项阈值各不相同，本表按项给出 `TolX` 与 `ratio_X`，并另设 `unit`、`SCF_status`、`termination`、`missing_reason`。
- TolE 取绝对值（`abs_delta_E_Eh`）；ΔE 为负值时 ORCA 打印带负号，本表用 `-?[\d.]+` 正则解析（否则会静默漏行）。
- 同一日志内多张收敛表 = **同一次优化的不同 cycle**（如 #1 单条日志 23 张表），**不解读为多次独立优化**。
- 缺列一律 `MISSING` + 原因；不补零、不沿用上一段末值。实际发生 `MISSING` 的情形：#2 的**第一张**表缺 `Energy change` 行（首步无前序能量，属正常）。