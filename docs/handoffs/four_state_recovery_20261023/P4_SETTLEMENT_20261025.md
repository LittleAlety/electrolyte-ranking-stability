# P4 筛选轮结算记录（2026-10-25 裁决落地）

> 依据：用户 2026-10-25 裁决——「**先结算 P4**，再在原 800 CH 总上限内建立新版筛选批次；
> 不申请增量预算，也不直接复用旧包的 32 CH 预留」。本文件是**结算侧**的唯一账目。

## 1. 两个 JobID（都已终结）

| JobID | 元素 | 终态 | ExitCode | Elapsed | AllocCPUS | 说明 |
|---|---|---|---|---|---|---|
| `3774076` | 8 | **FAILED 8/8** | `2:0` | 每元素 `00:00:00` | 4 | 首次提交：sbatch 缺 `#SBATCH --partition`，被桥的脚本校验拒；**在任何 sbatch 运行前**即失败 |
| `3774215` | 8 | **COMPLETED 8/8** | `0:0` | 0–1 s | 4 | 修正后重提；本次结算的依据 |

- 两次提交的原始记录**都保留、未覆盖**：当前包内 `submission_journal.json` 存 3774215；
  3774076 的记录在 `work/hpc_four_state_p4_xtb_screening_v1.pre_partition_fix/submission_journal.json`。
- 逐元素证据：`work/_p4_settlement_evidence/{sacct_3774215.txt, sacct_3774076.txt}`
  （含 `Start`/`End` 列，补齐 t4 复核指出的证据缺口），`squeue_account_level_utc.txt`
  （**账户级** `squeue -u pengqihang` + 时间戳 `2026-10-26T03:05:54Z`，**空队列**）。

## 2. 核数口径（根因，决定了结算数字）

**包内声明 2 核，Slurm 实际分配 4 核。** 代码级根因：`hpc.ps1:589-595` 拿到 `--cores N` 只改写
`#SBATCH --ntasks`，不动 `--cpus-per-task` ⇒ **分配 = `--cores` × `--cpus-per-task` = 2 × 2 = 4**。
（提交器自身的守卫只比对「声明核数 == profile 核数」，两者都是 2，故未察觉。）

## 3. 结算金额（保守口径，按裁决原文）

| 口径 | 数值 | 来源 |
|---|---|---|
| 实测（sacct `Elapsed × AllocCPUS`） | **0.002222 CH** | 8 元素合计 2 秒 × 4 核 |
| 保守地板（每元素 ≥ 4 核 × 1 分钟） | **0.533333 CH** | 时间戳仅整秒精度 |
| **采用（裁决）** | **0.54 CH** | 「保守计 P4 为 0.54 CH」 |
| **释放回筛选账** | **31.46 CH** | 32 − 0.54 |

> 这是**内部预算结算**，不声称是超算中心的实际收费数。
> 另注：失败批 3774076 的 8 元素若按同一地板规则计，会再加 0.54 CH；裁决采用的数字是 **0.54**（即把失败批视为零工作量），此处如实标注该选择。

## 4. 账本已更新（裁决第 1 条）

- `attempts_ledger.json`：8 行 `status` 由 `planned` 更正为 **`settled_terminal`**，每行新增
  `task` / `run_job_id` / `element_index` / `cores_allocated=4` / `slurm{state,exit_code,elapsed,alloc_cpus,start_utc,end_utc}`
  / `slurm_allocation_id="3774215_<i>"` / `measured_core_hours` / `conservative_floor_core_hours`；
  **保留 `cores: 2`（提交时声明值）**以便对照，不掩盖口径差。
- 新增 `settlement` 块：裁决原文、两个 JobID、核数口径与根因、四项合计、证据 sha256、冻结账本 sha256。
- **提交时的原始账本字节已冻结保存**：`attempts/frozen_attempts_ledger_at_submit.json`，
  sha256 = `c2a8fc1bbcb76dba2b77ff15047be360e20aa19abf27d2c7cf3fd7c91f7f94d4`
  —— **与提交时 `PACKAGE_SHA256SUMS` 首行逐字节相同**，故「提交态」可证。
- `PACKAGE_SHA256SUMS` 已按磁盘字节重同步（46 条），本地 `sha256sum -c` **0 FAILED**（46/46 OK）。

## 5. 完整性判据的切换（如实说明）

`build_torsion_probe_package.py --check-p4-screening` 是**建包期**判据（从当前 builder 重算并逐字节比对）。
包执行后它**必然**报：`changed:manifest.json`（生成器此后演进 → `generator_sha256` 改变）
与大量 `unexpected:`（任务目录里的 xtb 产物、根目录的 `slurm-*.out/err`）。
**未为此放宽该检查**（那就是「改门让红变绿」）；已执行的包改用
`work/_p4_settled_integrity.py`：`PACKAGE_SHA256SUMS` 自洽（46/46）＋ 冻结账本锚定（`c2a8fc1b…`）
＋ 结算块核对（0.54 / 31.46 / 8 元素）。实测 **P4 SETTLED INTEGRITY OK**。

## 6. 未处置项（不自行决定）

- **远端**：`~/project/electrolyte_wp2/p4_xtb_screening_v1`（3774215 的运行目录）与
  `~/project/electrolyte_wp2/hpc_four_state_p4_xtb_screening_v1`（我镜像的一份）**均保留不删**；
  远端 `attempts_ledger.json` 仍是提交时的 `planned` 版本（本地已结算）⇒ 是否要回传结算账**请示后再做**。
- **失败落点**：3774076 的远端痕迹保留，不删。

## 7. 与 v2 的衔接

预算与协议见 `XTB_SCREENING_V2_PROTOCOL_20261025.md`：
v2 = `xtb_screening_v2`（4 核 / ≤1 h / cap 16），首批只投 **DOL/EC**（预留 8 CH）；
**DMC 两态不投**（item 6 判读认定同设置重试已被 18 条失败腿证伪）。
最坏情况 `0.54 + 16 + 512 + 256 = 784.54 ≤ 800`。