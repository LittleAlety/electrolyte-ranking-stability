# P4 提交门（2026-10-23，**在受保护提交器内部实现**）

计划 P4 原文：「仅对经过 P1–P3 的任务建专属版本包。提交前核对授权、任务索引、远端输入哈希、
资源、真实账户容量和提交日志。使用现有受保护提交器及命令桥，**不绕到裸 SSH**。」
代码骨架的纪律：「这是不变量，**不是独立提交程序**。实际提交仍调用现有 `submit_hpc_batch.py`…
**不能在外层脚本偷偷绕开提交器**。」

## 1. 现状核验（先查再改）

| 项 | 现状 |
|---|---|
| 受保护提交器 | `scripts/wp_production/submit_hpc_batch.py`（**已存在**，走命令桥、要求 pwsh 7） |
| 它已具备的保护 | 重复批次拒绝（reservation 文件 + journal）、`doctor` 前置、**账户级远端提交锁**、**实时 `squeue` 余量**（`MAX_ACTIVE_PENDING=20`）、批次清单与 manifest 计数一致 |
| **它固定的资源** | `--cores 4 --time 24:00:00` |
| 该固定值是否适用于本轮 | **适用**：项目生产腿口径即 **4 核 / 24h**（sacct 实测每条生产腿 `AllocCPUS=4`；冻结协议相同）。计划里的「16 核 × 4h」是**预算上限示意**，且计划明令「**若 16 核×4h 不够，先停止、提交诊断，不暗改 24h**」 → **本次不改核心数与时长** |

## 2. 本轮新增（都在提交器**内部**，外层脚本无法绕开）

1. **`declared_task_cores(package, listing)`**：读取每个任务 `job.inp` 的
   `%pal nprocs N`，要求**所有任务一致**且**等于分配核数**；缺声明、缺 `job.inp`、
   不一致 → **拒收**。落实计划的「**输入核数与 allocation 一致**」与 `AGENTS.md` 的
   「`%pal nprocs` 必须等于 `--cores`」。
2. **`committed_core_hours(attempts)`**：核心小时不变量，三条规则——
   - **未结束**（`pending`/`running`/`submitting`）按**全额预留**计（`cores × wall_hours_reserved`）：
     未完成的作业**不能**释放剩余额度；
   - **已结束**按 Slurm **allocation 去重**后计一次实测值：**共享作业不得按腿重复计费**；
   - 终态却**缺来源**（无 `slurm_allocation_id` 或无 `measured_core_hours`）→ **`ValueError`**，
     **绝不当作 0**。
3. **`budget_headroom(...)`**：`committed + reserved ≤ cap`（默认 **800**）在**提交临界区内**校验，
   超额即拒；通过时把 `committed/reserved/cap/remaining_after` 写进提交 journal 记录。
4. **CLI**：`--attempts-ledger JSON`、`--budget-cap-core-hours`（默认 800）。
   **未给 ledger 时**：不静默跳过，而是**打印 NOTE 声明"预算不变量未校验"**，并在 journal 里记
   `budget_checked=false`（可审计）。

## 3. 测试（`tests/test_submit_budget_gate.py`，12 项 + 1 声明式 skip）

覆盖：未结束按全额预留、**共享 allocation 只计一次**、终态缺来源即报错、planned/rejected 不计费、
cap 含在飞额度、`committed+reserved>cap` 拒收、声明核数读取、任务间核数不一致拒收、
缺声明拒收、缺输入拒收，并钉住「本项目口径 = 4 核 / 24h，默认上限 800」（**防止被悄悄改成 16 核**）。

**既有夹具的处理**：契约收紧使 `tests/test_submit_hpc_batch.py` 的三个夹具（只有
manifest/script/list、无 `job.inp`）失效 → 按项目纪律**修夹具**（补上声明 `%pal nprocs 4` 的
`job.inp`），**不改回契约**。

## 4. 尚未做（P4 的剩余部分）

- **专属版本包的正式生成**（manifest/几何/来源/预检/预算）——待 P3 候选选定后建包；
- **提交本身**：仍须过「授权 + 预算 + 输入 + 实时队列」四门，且**只经命令桥**；
  **本轮未提交任何作业**。