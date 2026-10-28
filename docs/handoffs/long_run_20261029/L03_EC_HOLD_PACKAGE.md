# L03 EC 可执行 HOLD 材料（2026-10-29）

状态：**READY_HOLD**——本地准备完成，**未申请授权、未提交、零计算**。
依据：`docs/plans/CORE_PLAN_EXECUTION_SUPPLEMENT_20261029.md` §5.1/§5.3。

## 1. 包

- 路径：`work/hpc_ec_recovery_v2_p4_20261029/`（15 个被哈希文件 + `PACKAGE_SHA256SUMS`）
- 生成器：`scripts/wp_production/build_ec_recovery_package.py`（新脚本，已四处登记：README 索引 / `docs/65_repo_layout.md` §3.1 / 计数句 90 文件·84 py / `tests/test_wp2_cost_semantics.py` 计数字典）
- `submission_gate=HOLD`、`submitted=false`；`reserved_core_hours=16`；`task_count=1`；`batches=[{batch:1,count:1}]`

### 1.1 active 与 reserve 的隔离

| 项 | 位置 | 是否可被发现 |
|---|---|---|
| `ec_v2_p4`（active） | `tasks/EC__LiM_2plus/ec_v2_p4/` | 是（`tasks.txt` / `batch_1.txt` 各 1 行） |
| `ec_v2_p7`（reserve） | `reserve/EC__LiM_2plus/ec_v2_p7/` | **否**——不在 `tasks.txt`、不在批次清单、无 `import_level.txt`，importer 与提交器都扫不到 |

`reserve/.../RESERVED.md` 明写「不可提交；只有 p4 终态失败且完整取证后才另建包激活」。这样既保留了 p7 的候选几何与输入，又不会让它变成永久 pending 的已注册工作。

### 1.2 输入链

- 父几何：`work/hpc_dol_ec_recovery_v1_reopt_20261027/tasks/EC/LiM_2plus__p4_02_ring_pucker_twist/snapshots/3791416_1/job.xyz`
- 父几何 SHA256：`a0a8d53b1e6083c4212d98d844350ce3248c38d201b82f9f3f40936341cd969b`（构建器逐文件现算复核）
- p4 候选几何 SHA256：`candidate.json` 记录、`inputs.sha256` 锚定（ORCA 启动前 `sha256sum -c`）
- 身份：EC|LiM_2plus charge=2、multiplicity=2、`$spin=1`；`job.inp` 的 `* xyzfile 2 2 geom.xyz` 与 `candidate.json` 逐字段一致

## 2. 真实加载器 + 提交器门函数离线验证（27/27）

`work/_validate_ec_package_loader.py`（不导入 bridge、不触网、不提交）直接调用提交器自己的门函数：

- `_load_package` → `count=1`；`submission_resources` → `orca_production_4h_v1`、`attempts_ledger_required=True`
- `declared_task_cores` → 4 == profile cores；`budget_headroom` → `reserved=16`、`remaining=16`、cap 32
- gate 仍是 `HOLD`/`submitted=False`；reserve 不可发现
- sbatch：`--partition=hpxg`、`--array=0-0`、`--time=04:00:00`、`cd "${SLURM_SUBMIT_DIR}"`、`test "${SLURM_NTASKS}" = 4`、`module load` 独立一行
- `job.inp`：冻结方法（wB97X-D4 def2-TZVPD Opt AnFreq …）、无 NumGrad、身份一致
- `PACKAGE_SHA256SUMS` 逐文件重算全部一致
- 合同：p4 被接受；p7 抢跑被 `ContractViolation` 拒绝

```text
27 checks, 27 pass, 0 fail
build_ec_recovery_package.py --check -> EC PACKAGE OK (15 files, profile=orca_production_4h_v1, 1 active element, reserve isolated)
```

## 3. 唯一剩下的提交前步骤（授权后才做）

**为 `EC|LiM_2plus` 登记一条 planned 候选行**（p4 几何 sha 锚定，`source_kind=p4v2_screening_v1_start`、`member_role=recovery_v1_start`），走生产登记器并在登记后重算标签。

- 为什么不在本轮做：登记会让该态出现未决工作，可能把 `limited` 变 `provisional`；这是**状态变化**，必须有独立的无翻转证明（EC 当前非 accepted，故不会翻转任何已接受态，但仍需如实重算并记录）。
- 为什么必须做：不登记就提交，结果**无处挂靠**（聚合器看不到，永远 limited 且不报错）——即已知的静默阻塞链。

## 4. 边界

- 本步**没有**提交、没有 doctor/squeue、没有上传、没有占用任何 core-hour。
- `32 CH` 仍是**提议**：`paid_from=proposed_ec_campaign_32ch_not_yet_authorised`。
- 历史包与历史 profile 语义未改动；本包是**新目录**，不覆盖任何既有包。
