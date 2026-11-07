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
| 版本化资源 | 历史/ORCA 包缺 profile 时保持 `orca_production_v1`＝4核/24h/800 core-hours；本轮筛选必须显式 `xtb_screening_v1`＝2核/2h/32 core-hours |
| 资源能否由 CLI 放宽 | **不能**。profile 随被哈希的 manifest 进入提交；未知 profile、CLI cap 与 profile 不一致、引擎与输入格式不一致均在 bridge 前拒绝 |

## 2. 本轮新增（都在提交器**内部**，外层脚本无法绕开）

1. **`submission_resources(...)` + `declared_task_cores(...)`**：ORCA profile 只接受
   `%pal nprocs N`；xtB profile 拒绝 `%pal`，要求 `$chrg/$spin` 与 `cores.txt`。
   所有任务核数必须一致且等于 profile 分配核数；缺声明、缺输入、引擎错配均拒收。
2. **`committed_core_hours(attempts)`**：核心小时不变量，三条规则——
   - **未结束**（`pending`/`running`/`submitting`）按**全额预留**计（`cores × wall_hours_reserved`）：
     未完成的作业**不能**释放剩余额度；
   - **已结束**按 Slurm **allocation 去重**后计一次实测值：**共享作业不得按腿重复计费**；
   - 终态却**缺来源**（无 `slurm_allocation_id` 或无 `measured_core_hours`）→ **`ValueError`**，
     **绝不当作 0**。
3. **`budget_headroom(...)`**：`committed + reserved ≤ profile cap` 在**提交临界区内**校验，
   超额即拒；通过时把 `committed/reserved/cap/remaining_after` 写进提交 journal 记录。
4. **CLI**：`--budget-cap-core-hours` 仅作一致性断言，不能覆盖 profile。显式
   `xtb_screening_v1` **强制要求** `--attempts-ledger`，缺失即在 doctor/bridge 前拒绝；
   历史 ORCA 包仍保留无 ledger 时打印 NOTE、journal 记 `budget_checked=false` 的兼容行为。

## 3. 测试

覆盖：未结束按全额预留、**共享 allocation 只计一次**、终态缺来源即报错、planned/rejected 不计费、
cap 含在飞额度、`committed+reserved>cap` 拒收、声明核数读取、任务间核数不一致拒收、
缺声明拒收、缺输入拒收，并钉住 ORCA＝4核/24h/800 与 xtB＝2核/2h/32 两套协议。
八任务 xtB 贯通测试同时断言 bridge 参数、`reserved=32`、`cap=32` 与
`budget_checked=true`；缺账本、cap 覆盖、引擎错配和未知 profile 均有负测。

**既有夹具的处理**：契约收紧使 `tests/test_submit_hpc_batch.py` 的三个夹具（只有
manifest/script/list、无 `job.inp`）失效 → 按项目纪律**修夹具**（补上声明 `%pal nprocs 4` 的
`job.inp`），**不改回契约**。

## 4. 专属版本包（已生成，仍为 HOLD）

- 本地包：`work/hpc_four_state_p4_xtb_screening_v1/`，共 8 个任务；单数组
  `0-7%2`，一次锁定 `8 × 2核 × 2小时 = 32 core-hours`。
- 身份来源：`production_ledger.csv`；P3/P4 的 `record_id/charge/multiplicity` 任一漂移即拒绝。
  三个 `LiM_2plus` 均按权威态 `charge=2, multiplicity=2, spin=1`，不再沿用旧 scratch
  生成器错误的 `1/1`。
- 每条任务均从锁定源几何重建，重新经过候选 gate，并同时锁定 raw geometry SHA256 与
  distance fingerprint；根 `PACKAGE_SHA256SUMS` 对不可变输入做完整清单闭包。
- 生成与只读复核：

  ```powershell
  .\.venv\Scripts\python.exe scripts\wp_production\build_torsion_probe_package.py --build-p4-screening
  .\.venv\Scripts\python.exe scripts\wp_production\build_torsion_probe_package.py --check-p4-screening
  ```

- **提交仍未做**：`manifest.json` 与 selection lock 均为 `submission_gate=HOLD`、
  `submitted=false`。上传前还须远端逐文件核对 `PACKAGE_SHA256SUMS`，提交只允许走命令桥与
  `submit_hpc_batch.py --attempts-ledger ...`，不得裸 SSH 或绕过预算门。
