# 四态恢复「正式执行账」（2026-10-25）——计划 action item 3

> 本文件把**授权、预算与批次**写进正式账；提交动作产生的 JobID 与实测成本随后回填在本文件末。
> 记账纪律：**缺失的终态费用绝不按 0**；历史成本**记录不清零**。

## 1. 授权记录（原话与来源）

- 计划原文：「我将你的『基本完全授权』按**有界执行授权**理解：可以准备并推进四态恢复，
  但四态新轮次累计不得超过现有提案的 **800 allocated core-hours**；P4 的 32 包含在内。」
- 计划自身的 Open question 要求：若授权排除实际提交，须在启动前指出。
- **2026-10-25 Lead 就此向用户提出单选确认，用户选择：**
  **「确认：授权覆盖实际提交（推荐）」**
  —— 选项原文：「我先完成计划第 2–3 项（接线反例测试、正式执行账），随后按 runbook §1 固定顺序：
  doctor → 实时 squeue → 逐文件上传 → 受保护提交器（32 CH，含在 800 内）；每步汇报。」
- ⇒ **本条即解除 HOLD 的授权依据**（见 §4：HOLD 由记录解除，**不由编辑冻结包解除**）。

## 2. 预算账（总 800 core-hours）

| 段 | 上限 | 形态 | 已用（新轮次） | 在途/排队 | 待提交预留 |
|---|---|---|---|---|---|
| 筛选（P4） | **32** | 8 任务 × 2 核 × 2 h，单数组 `0-7%2` | 0 | 0 | **32** |
| 首轮生产 | 512 | 8 起点 × 16 核 × 4 h | 0 | 0 | 0（未建包） |
| 有因救援 | 256 | ≤4 × 16 核 × 4 h | 0 | 0 | 0（未建包） |
| **合计** | **800** | | **0** | **0** | **32** |

**历史成本（记录不清零，不计入 800 新轮次）**：四态活动历史实测 **227.43 CH**
（strict_recovery 家族 187.00 + torsion-probe 家族 40.43，见 `FOUR_STATE_STARTING_LEDGER_20261025.md`）；
主生产账本（60 腿）另计 **591.8 CH**。

## 3. 提交前四道门（2026-10-25 实测，全部通过）

| 门 | 要求 | 实测 |
|---|---|---|
| ① **输入哈希／同源** | 候选与当前账本同源 | **3/3 命中**：`p3_candidates_sha256`↔`docs/handoffs/four_state_recovery_20261023/P3_CANDIDATES_20261023.json`；`p4_selection_sha256`↔`P4_SCREENING_PLAN_20261023.json`（亦等于包内 `selection.lock.json`）；`production_ledger_sha256`↔`outputs/physics_completion/free_states/production_ledger.csv`；另 `generator_sha256`↔`build_torsion_probe_package.py` 当前字节 |
| ② **命令桥体检** | `doctor` 通过 | **通过（0 项提醒）** |
| ③ **账户配额** | 空间/文件数充裕 | `/project` **44.73 G / 500 G**、文件 **22319 / 500000**；`/home` 278 k/1 G、12/10000 |
| ④ **实时队列** | running+pending ≤ 20 | **空（0 running / 0 pending）** |

## 4. HOLD 的正确解除方式（实测结论）

`submission_gate` 全仓用法：**builder 只写 HOLD**（`build_torsion_probe_package.py:1095`；`:990` 还要求必须是 HOLD）、
README/站点只显示、`tests/test_p4_screening_plan.py:81` **断言必须为 HOLD**、而**受保护提交器根本不读它**（H5）。
且 `manifest.json` 在 `PACKAGE_SHA256SUMS` 的哈希闭包内。
⇒ **不存在「改 manifest 解除 HOLD」的合法路径**；**解除＝写入本授权记录并用受保护提交器提交**，
包本身**保持字节冻结**（`HOLD` 字段即「授权前冻结」的诚实记录）。

## 5. 本批参数（提交时逐项核对）

| 项 | 值 |
|---|---|
| 包 | `work/hpc_four_state_p4_xtb_screening_v1`（47 文件，8 任务 × 5 文件 + 6 顶层） |
| 批次 | `--batch 1`（数组 `0-7%2`，8 元素，`cores.txt`=2，wall 2 h） |
| 远端落点 | `~/project/electrolyte_wp2/p4_xtb_screening_v1`（**逐文件上传**：9 × `mkdir -p` + 46 × `put` + 1 次远端 `sha256sum -c`；因 `hpc put` 无 `-r`） |
| 提交器 | `submit_hpc_batch.py <包> --batch 1 --remote-workdir <远端> --attempts-ledger <包>/attempts_ledger.json --budget-cap-core-hours 32 --bridge <hpc.ps1>` |
| 提交器不变量 | `--budget-cap-core-hours` 必须等于 profile cap（唯一在任何 bridge 调用**之前**生效的守卫）；终态缺 `slurm_allocation_id`/`measured_core_hours` 即抛错，**绝不按 0**；重复 journal 会被拒（幂等） |

## 6. 提交后必须回填（禁止遗漏）

- **数组 JobID** 与「本批索引 → 本批任务」映射（`batch_1.txt` 的行序）；
- 每元素**实测成本**：`sacct -X -j <JobID> -o JobID,State,ExitCode,Elapsed,AllocCPUS` → `Elapsed × AllocCPUS`，
  **可追到 sacct 手填**（H1–H5 的五条强制核对之一）；
- 回收快照（`ensemble_hpc_io.py`）与判定（`build_p4_screening_adjudication.py`）的结果指针。