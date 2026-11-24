# 救援池 / Slurm 实时核对（exp_line_20261031，2026-10-31 02:2x–02:45 +0800）

> 全部数字来自**实测**：真实 `squeue` / `sacct`（经受保护命令桥）+ 仓库内的 attempts ledger + 提交 journal。
> 机器可读版本：`work/exp_line_20261031/LEDGER_AND_JOURNAL_20261031.json`。
> 基线 HEAD：`80933e54f8a605d9dd6d033c0f2861e33b591c13`。

## 1. 现场

| 项 | 实测值 | 方式 |
|---|---|---|
| 受保护桥 doctor | **通过，0 项提醒** | `hpc.ps1 doctor`（免密登录、登录/备用/传输节点、配额、module 均通过；`~/scratch` 不存在属免费账号正常） |
| 真实 Slurm 队列 | **空**（无任何作业行） | `hpc.ps1 jobs`，两次测定一致 |
| 在飞预留 | **0 core-hours** | 队列为空 + 全部 attempts ledger 无可计费的非终态行（`planned` 被 `committed_core_hours` 显式跳过，见 `submit_hpc_batch.py:346`） |
| 提交入口缺口 | **该批真跑过的 `squeue` 全为 0 行** → 不存在重复作业 | 同上 |

## 2. 报告基准 + 报告之后的实测消耗（sacct：`AllocCPUS × ElapsedRaw / 3600`）

生成的账目报告（`outputs/physics_completion/recovery/recovery_budget_accounting_index.json`，生成于 2026-10-29）只统计 `work/hpc_production_ensemble_strict_recovery_v1*` 这些包：

- **恢复包已用 187.0 / 600 CH；风险储备 300 未动用；系综 45 accepted / 3 limited。**

该报告之后发生的作业（下表全部为 sacct 实测，四舍五入到 5 位）：

| JobID | 作业名 | 状态 | ΣElapsedRaw(s) | AllocCPUS | 实测 CH | 归属 |
|---|---|---|---:|---:|---:|---|
| 3869232_0..5 | dmc_numprobe | 5 COMPLETED + 1 TIMEOUT | 1267 | 4 | **1.40778** | 救援线 |
| 3886095_0..3 | dmc_adjstep1 | FAILED ×4 | 0 | 4 | 0.00000 | 救援线 |
| 3886404_0..3 | dmc_adjstep1 | COMPLETED ×4 | 645 | 4 | **0.71667** | 救援线 |
| 3886289_0..3 | dmc_adjstep2 | FAILED ×4 | 0 | 4 | 0.00000 | 救援线 |
| 3886408_0..3 | dmc_adjstep2 | COMPLETED ×4 | 763 | 4 | **0.84778** | 救援线 |
| 3894976_0 | dmc_mplus_strict | COMPLETED | 1368 | 4 | **1.52000** | 救援线 |
| 3853042_0 | ec_recovery_v2 p4 | COMPLETED | 3354 | 4 | **3.72667** | EC 战线 |
| 3885000_0 | ec_v2_p7 | COMPLETED | 4191 | 4 | **4.65667** | EC 战线 |
| 3895005_0 | ec_strict_conv | FAILED | 0 | 4 | 0.00000 | EC 严格收敛 16 CH |
| 3895024_0 | ec_strict_conv | FAILED | 0 | 4 | 0.00000 | EC 严格收敛 16 CH |
| 3895037_0 | ec_strict_conv | COMPLETED | 202 | 4 | **0.22444** | EC 严格收敛 16 CH |
| 3910076_0 | ec_strict_conv | COMPLETED | 182 | 4 | **0.20222** | EC 严格收敛 16 CH |

小计（**v2 更正后**）：**救援线 4.4922222 CH**、**EC 战线 8.8100000 CH**、**全窗口合计 23.0583333 CH**。

> **v2 更正（2026-10-31：Agent B 的 t2 审计发现，Lead 独立重算确认）**：v1 的表格只列了 12 个工作，**漏记 9.7561111 CH** —— DOL 线 `3782517_0/3789580_1/3791416_0/_1` = 9.6211111、xtb 筛选 `3774215_1/_3` 与 `3777206_4..7/16/17` = 0.0088889、冒烟与授权 `3780713/3791324/3791344/3792233/3792235/3792287/3792307` = 0.0072222、`frontier 3808874_0` = 0.1188889。
> 重算方式：对**整个 2026-10-25 起窗口**（主作业 **78 行**）求 `Σ AllocCPUS×ElapsedRaw/3600 = 23.0583333`；原始输出存 `work/exp_line20261031/_sacct_window_1025.txt`。
> （附注：B 的四个分桶之和比其自身总数多 0.0005556 —— 它把 2 核的 `3791324` 按 4 核计；**总数正确**，仅该子标签有偏差。）

**与既有账本交叉验证（逐条命中，独立于我的算术）**：`3894976_0` → ledger `measured_core_hours=1.52`；`3895037_0` → `0.2244444`；`3910076_0` → `0.2022222`；`3853042_0` → campaign ledger `settled_core_hours=3.7266666666666666`；`3885000_0` → `4.6567`。**五条全部一致**，说明 sacct 口径与账本口径可互证。

## 3. 池余额（两种口径，**待用户裁定**）

| 口径 | 600 CH 池已用 | 可用余额 |
|---|---:|---:|
| **A**：报告后全部计入 600 池（**最保守**） | 187.0 + 23.0583333 = **210.0583333** | **389.9416667 CH**（预留 64 后 325.9416667） |
| **B**：EC 战线（8.81 CH）走它自己的额度，不计入 600 池 | 187.0 + 14.2483333 = **201.2483333** | **398.7516667 CH**（预留 64 后 334.7516667） |

- **判定：最保守口径下 64 CH 可用** —— `600 − 210.0583333 − 0(在飞) = 389.9416667 ≥ 64`。与 Agent B 的 §4 结论一致（其口径 B 数字也同为 398.7516667）。
- **口径差异不是小事**：仓库里**没有任何机器记录**说明 EC 严格收敛实验的 16 CH 是从 600 池支取还是独立额度（`work/hpc_ec_strict_convergence_v1/AUTHORIZATION.json` 只写 `budget_source` 与"独立 16 CH 总帽"，没有池名）。按用户纪律（"剩余预算不等于新增尝试授权"、"不得挪用"），这属于必须由用户固定的资源口径，我不自行选一个。
- 另：`docs/handoffs/four_state_recovery_20261023/recovery_contract.json` 里是另一套上限（`total_core_hours 800 = screening 32 + production 512 + rescue 256`），其 `status` 明确写着 `proposed_new_round_ceiling_not_submission_permission` —— 它**不是**默认可花的额度，本次核对不把它当作可用余额。

## 4. 本次核对发现的账本缺陷（必须记账，不得假设为 0）

复现命令：用受保护提交器自己的 `committed_core_hours()` 逐包计算。

| 文件 | 缺陷（实测） | 后果 |
|---|---|---|
| `work/hpc_dmc_adjacent_step_v2/attempts_ledger.json` | 8 行 `status=terminal_diagnostic_complete`：值写在 **`settled_core_hours`**，而提交器读的是 **`measured_core_hours`**（**Agent B 的锐化发现——值不是"缺"，是"放错字段"**）；且 8 行均无 `slurm_allocation_id` | `committed_core_hours()` 直接抛 `ValueError: terminal cost provenance missing`；实测 **1.5644444 CH**（`3886404` 0.7166667 + `3886408` 0.8477778）对任何预算检查不可见 |
| `work/hpc_dmc_numerical_probe_v1/attempts_ledger.json` | 6 行仍是 `status=planned`，但 `3869232_0..5` 实际已跑完并终态 | `committed_core_hours()` 返回 **0**；实测 **1.4077778 CH 对任何预算检查都不可见** |

**合计"已花但未记账" = 2.9722222 CH。** 与合同口径一致：`missing_terminal_cost = block_do_not_assume_zero`。

## 5. 一个结构性缺口：600 池的余量在提交时**没有机器强制**

`scripts/wp_production/submit_hpc_batch.py` 的预算检查（`:665-670`、`:744-760`）只核算**包级 cap**（来自 manifest/resource_profile），**没有任何一处校验 600 CH 池的池级余量**。也就是说"600 − 已用 − 在飞 ≥ 本次预留"这句话目前是**人工对账**，不是门禁。历史上多笔从"救援池"支取的作业（`funding: recovery_rescue_pool_600ch` 只出现在 `work/hpc_dmc_mplus_opt_repaired_v1_20261030/attempts_ledger.json`）都无法从机器上追溯到池级扣减。

**建议（待裁定）**：在新实验之前 ① 把上面两笔未记账成本结清到对应 ledger（由账本所有者写，本线不写）；② 明确 EC 16 CH 的池归属；③ 若要长期跑这条实验线，再讨论是否给池级余量加一道机器门（属生产代码改动，非本线写入面）。

**本核对只记账、只读；未改动任何账本、未提交任何作业、未改任何标签。**