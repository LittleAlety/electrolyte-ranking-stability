# 四态恢复「起点账」（2026-10-25）——计划 action item 1 的出口

> 全部数字**从磁盘与实时查询实测**；两处独立来源（自算 `sacct` vs 权威账本）已逐包对账。
> 本文件**只记账、不改任何验收判定**，也不改变任何冻结产物。

## 0. 授权与预算框架（先钉清，避免混淆）

| 项 | 值 |
|---|---|
| 授权形态 | **有界执行授权**：四态**新轮次**累计 ≤ **800 core-hours**（筛选 32 + 首轮生产 512 + 救援 256），P4 的 32 含在内 |
| 每次提交仍需 | 四道门：① 实时队列 ② 预算 ③ 输入哈希 ④ 科学起点 |
| 历史成本 | **记录但不清零**：本活动历史实测 **227.43 CH**（见 §2）；主生产账本（60 腿）另计 **591.8 CH** |
| 新轮次已用 | **0 CH**（P4 包仍 `HOLD`、`submitted=false`，账本 8 条 `planned`） |
| 额外告示 | `recovery_contract.json` 自身仍写 `submission_authorized_by_this_bundle=false`、`budget.status="proposed_new_round_ceiling_not_submission_permission"` ⇒ **解除 HOLD 前需一次明确确认**（§6） |

## 1. 四态冻结事实（逐字段，2026-10-25 实测）

| 态 | `acceptance_status` | `limitation_reason` | coverage `route` | `verdict` | `registered_starts` | `n_unique_after` | label `n_registered`/`n_unique` |
|---|---|---|---|---|---|---|---|
| `DMC\|M_plus` | `limited` | `rescue_budget_exhausted` | `unresolved_qc` | `unresolved` | `tors_8_0_1_2` | 1 | 2 / 1 |
| `DMC\|LiM_2plus` | `limited` | `rescue_budget_exhausted` | `unresolved_qc` | `unresolved` | `tors_7_0_1_2` | 1 | 2 / 1 |
| `DOL\|LiM_2plus` | `limited` | `rescue_budget_exhausted` | `search_exhausted` | `search_exhausted` | **（空）** | 1 | 2 / 1 |
| `EC\|LiM_2plus` | `limited` | `rescue_budget_exhausted` | `search_exhausted` | `search_exhausted` | **（空）** | 1 | 1 / 1 |

## 2. 真实已运行 vs 规划／拒收

**真实提交共 17 次**（自 `work/**/submission_journal*.json` 枚举），全部经 `sacct` 核验为**终态**：

| 包（remote workdir 尾名） | JobID | 元素 | 实测 CH（`Elapsed × AllocCPUS`） | 权威账本值 | 一致 |
|---|---|---|---|---|---|
| `strict_recovery_v1` | 3738029 | 4 | 33.31 | 33.3 | ✅ |
| `…_b2` | 3738645 | 8 | 81.20 | 81.2 | ✅ |
| `…_cont1` | 3739147 | 1 | 7.94 | 7.9 | ✅ |
| `…_cont2` | 3739236 | 1 | 4.46 | 4.5 | ✅ |
| `…_cont3` | 3739621 | 1 | 1.79 | 1.8 | ✅ |
| `…_cont4` | 3739671 | 1 | 3.35 | 3.4 | ✅ |
| `…_cont5` | 3742333 | 3 | 29.06 | 29.1 | ✅ |
| `…_reopt1` | 3738937 | 2 | 2.89 | 2.9 | ✅ |
| `…_reopt2` | 3739650 | 1 | 1.66 | 1.7 | ✅ |
| `…_reopt3` | 3740627 | 1 | 2.11 | 2.1 | ✅ |
| `…_reopt4` | 3742330 | 1 | 2.10 | 2.1 | ✅ |
| `…_reopt_v2` | 3744604 | 5 | 17.14 | 17.1 | ✅ |
| `hpc_torsion_probe_v1` | 3747714 | 8 | 24.11 | —（另计） | — |
| `…_v1`（b2） | **3747724** | 3 | **0.00** | — | **CANCELLED** |
| `…_v1_batch2_fragmentfix` | 3748336 | 1 | 6.52 | — | — |
| `…_v1_reopt_v3` | 3749453 | 1 | 4.56 | — | — |
| `…_v2_realfragment` | 3749450 | 2 | 5.25 | — | — |

- **合计 42 个元素**：`COMPLETED` **41**（ExitCode 全部 `0:0`）+ `CANCELLED by 59540` **1**（`3747724_[0-2]`，`00:00:00`、`AllocCPUS=0` ⇒ **零消耗**）。
- **strict_recovery 家族 12 包 = 187.00 CH**，与 `recovery_budget_accounting.md` 的 **187.0** 及**逐包 12/12 数值**全部一致；torsion-probe 家族另计 **40.43 CH**；**总 227.43 CH**。

**规划但从未发送**：
- `outputs/physics_completion/recovery/strict_recovery_v1_manifest.csv` 的四态行 `status=**planned**`，且 `start_1_basin`/`start_2_basin`/`start_1_source_sha256`/`start_2_source_sha256` **全为空** ⇒ **这些行不等于已运行的尝试**；真实已跑的腿是 coverage 里登记的 `tors_8_0_1_2`（DMC\|M_plus）与 `tors_7_0_1_2`（DMC\|LiM_2plus）；**DOL/EC 无登记腿**。

**唯一拒收记录**：`work/hpc_production_ensemble_r2_reopt/submission_journal.attempt0_refused_no_sbatch.json`（`r2_reopt` 不在四态活动内）。

## 3. 唯一链条 `state → candidate → attempt → Slurm element → output → cost`

| 环节 | 权威位置 |
|---|---|
| state | `production_ensemble_labels.csv` 的 `(name,state)` |
| candidate | coverage 的 `registered_starts`（DMC 两条；DOL/EC 空） |
| attempt | `strict_recovery_v1_manifest.csv`（**planned** 行）+ 各包 `submission_journal.json` 的 `batch` |
| Slurm element | journal 的 `job_id` + `sacct` 的 `JobID_<index>` |
| output | 远端 `~/project/electrolyte_wp2/<包>/tasks/**`（经 `ensemble_hpc_io.py` 落快照） |
| cost | `sacct` 的 `Elapsed × AllocCPUS` → 与 `recovery_budget_accounting.md` 对账 |

**现状**：DMC 两态链条**完整到 cost**（两条腿均以 QC 失败结束：`technical_complete_qc_failed`）；**DOL/EC 链条在「candidate」处断**（无登记起点，`search_exhausted` 是筛选层结论）。

## 4. 在飞／重复核查

- 实时 `squeue`：**空**（0 running / 0 pending，本轮实测）。
- 17 个 JobID **全部终态**（见 §2 的 41+1）。
- 每个包**恰 1 次提交**（仅 `hpc_torsion_probe_v1` 为 2 次：`3747714` + 被取消的 `3747724`）。
- 上游 P4 包仍 `HOLD`／未提交 ⇒ **不存在第二份在飞**。
⇒ **出口（2）成立：不存在重复在飞任务。**

## 5. 写入面归属（「他人持有」）

读 `E:\Claude Code\电解液溶剂-HB\.dsh-coordination\SESSION_CLAIMS.md` + 本轮 `git status` 实测：
- **他人持有/产出**：`计划.md`（另一会话专属）、`outputs/**` 的部分行、`docs/assets/data.js`、`docs/index.html`、`scripts/…/build_second_search_preregistration.py`、wp5 README、`docs/handoffs/.../audit_*_20261026/` 与 `agent_*` 目录（由并行会话与其成员产出）。
- **本轮 Lead 写入面**：本文件、`work/_four_state_ledger_probe.py`（机器本地）、`work/_recovery_sacct.txt`（证据快照）；t4 复核由 `ledger-verifier` 独占 `agent_ledger_verify_20261025/`。

## 6. 出口判定与唯一待确认问题

- ✅ 出口（1）：能明确回答四态各有哪些**真实已运行**尝试、哪些只是**规划/拒收**（§2）。
- ✅ 出口（2）：**不存在重复在飞任务**（§4）。
- ✅ 出口（3）：候选→尝试→Slurm 元素→产出→成本链条可追，并注明 DOL/EC 的断点在「candidate」（§3）。

**唯一待确认问题（解除 HOLD 前）**：新目标写「有界执行授权」，而 `recovery_contract.json` 仍写 `submission_authorized_by_this_bundle=false` / `requires_external_execution_authorization=true`。
**请确认：该 800 CH 有界授权是否覆盖「实际提交」**（含 P4 的 32 CH）？一经确认，我将按 `P4_SUBMIT_RUNBOOK_20261024.md` §1 固定顺序执行：`doctor` → 实时 `squeue` → **逐文件上传**（`work/_p4_upload_package.py`，56 次桥调用）→ 受保护提交器（`--attempts-ledger` + `--budget-cap-core-hours 32`）。