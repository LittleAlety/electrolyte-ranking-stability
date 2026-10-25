# Submit-bypass Offline Audit Report（独立复现）

**项目状态**：`submission_gate=HOLD`, `submitted=false`。**未获任何计算授权**。  
**范围**：仅离线复现 `scripts/wp_production/submit_hpc_batch.py` H1–H5。全程不触达 bridge/集群/网络/ORCA。  
**探针**：`probe_offline.py`（纯内存 + `tempfile` 构造合成包，monkeypatch `subprocess.run`/`shutil.which` 为 tripwire，强制 `bridge=E:/nonexistent/hpc.ps1`）。  
**输出**：`probe_output.txt`（完整 stdout）。

## H1–H5 逐条行号级结论（独立再推导）

| Hole | 源码行号（现采） | 结论 | 独立复现证据 |
|------|-------------------|------|----------------|
| **H1**（attempts ledger 不可信、无 sacct→measured 自动回填） | `committed_core_hours()` ~250-272（终态需 `slurm_allocation_id` + 非空 `measured_core_hours`，否则 `ValueError`；`planned/rejected/superseded_unsubmitted` 跳过）；`budget_headroom()` ~275-288；`submit_batch()` ~419,434-443（从调用方 JSON 读取 ledger，无哈希绑定） | **确认（成立）** | C5：终态缺 provenance → `refused: terminal cost provenance missing`。C6：`measured_core_hours="0"` → `committed_core_hours=0`（账面抹零）。C7：`status="completed"` 改标 `planned` → 被排除出计费 → `committed_core_hours=0`。**ledger 完全由调用方自备，无自动校验/回填。** |
| **H2**（缺 `resource_profile` 静默降级） | `submission_resources()` ~116-131：`name = manifest.get("resource_profile", DEFAULT_RESOURCE_PROFILE)`，`DEFAULT_RESOURCE_PROFILE="orca_production_v1"`（~35），`RESOURCE_PROFILES` ~24-34（注释明确沿用历史 ORCA 契约）；`submit_batch()` ~300-308 用 profile cap。 | **确认（关键）** | C1：manifest **无** `resource_profile` → `resource_profile=orca_production_v1`，`budget_checked=False`，提交成功（`--cores 4 --time 24:00:00`）。C1 h5：manifest 仍 `submission_gate=HOLD`，journal 却 `status=submitted`。 |
| **H2′**（拒绝时机过晚） | `declared_task_cores()` ~199-247；`submit_batch()` ~324-347 在走到该处前已执行 doctor→锁→squeue | **确认（关键）** | C2：xtb 输入但 manifest 丢失 profile → 回退 to orca，**拒绝发生在** `doctor` → `mkdir` 锁 → `squeue` → `rmdir` 锁 **4 次 bridge 调用之后**。实测调用序列已记录。 |
| **H3**（不解析 sbatch、不校验脚本哈希） | `submit_batch()` ~366-368 仅**记录** `batch_script_sha256/batch_list_sha256/manifest_sha256`，全文件无 `#SBATCH` 解析；`_load_package()` ~95-114 只校验存在性/计数。 | **确认（关键）** | C3：将 sbatch 篡改为 `#SBATCH --array=0-99%2 --cpus-per-task=16 --time=24:00:00`（潜在 38400 core-hours），manifest 声明的 `script_sha256` 与实际不符。提交器仍 `budget_checked=True reserved_core_hours=32`，按 profile 分配 `--cores 2 --time 02:00:00`，**哈希不匹配全程未被发现**，脚本原样传给 bridge。 |
| **H4**（manifest 数字被忽略） | `submission_resources()` 只读 `resource_profile`；`submit_batch()` ~302-305 仅拿 profile cap 做 CLI 对比；预算用 profile 的 `cores/wall_hours/budget_cap_core_hours`。 | **确认（中等）** | C4a：CLI `--budget-cap-core-hours=999999` 与 profile cap 32 不符 → **在任何 bridge 调用前**拒绝（`bridge calls during refusal: 0`）。C4b：manifest 写 `task_count=100 cores_per_task=16 wall_hours_per_task=24 budget_cap_core_hours=999999`，提交器仍用 profile 值（2 核×2 h、cap 32、reserved 32）。**profile 静默覆盖 manifest。** |
| **H5**（`submission_gate`/`submitted` 零检查） | 全文件 grep：`submission_gate` **0 次**，`submitted` **0 次**。仅 `manifest.get("batches",...)`、`manifest.get("resource_profile",...)` 两处读取。 | **确认（高）** | C8：源码核对确认。C1 h5：manifest `submission_gate=HOLD` 仍能走到 `submitted`。**门字段纯装饰，未参与任何判定。** |

**正面守卫（记录）**：`submit_batch()` ~302-305 CLI cap 与 profile cap 对比在 bridge 调用前生效（C4a 实证）。

## H2/H3 mock 复现（命令 / 退出码 / bridge_never_reached）

**命令（仓库根）：**
```bash
cd "E:\Claude Code\电解液溶剂-HB\电解液溶剂HB-Code"
.\.venv\Scripts\python.exe -B docs\handoffs\four_state_recovery_20261023\audit_submitter_bypass_20261026\probe_offline.py
```

**执行要点：**
- 使用合成包（全写入 `tempfile` 临时目录，跑完即清理）
- `subprocess.run` / `shutil.which` 全部被 tripwire 替换
- `bridge = E:/nonexistent/hpc.ps1`（不存在）
- 所有 bridge 响应均由纯 Python mock `runner()` 返回

**结果：**
- **退出码：0**
- **bridge_never_reached：true**（C9：`real subprocess/which attempts: 0`）
- 详见 `probe_output.txt`：12 项检查 **12 PASS，0 FAIL**

关键实测摘录（H2/H3）：
- H2：`C1 h2_fallback_submits_budget_unchecked` PASS（`profile=orca_production_v1 budget_checked=False`）
- H2′：`C2 h2_rejected_only_after_3_bridge_calls` PASS（4 次 bridge 调用后才拒）
- H3：`C3 h3_tampered_sbatch_budget_checked_true_reserved_32` PASS（sha_rec≠sha_decl，预算仍按 profile 生效）
- H5：`C1 h5_hold_manifest_still_submitted` PASS、`C8 h5_source_never_reads_gate_fields` PASS

## 无法离线复现 / 未覆盖部分
- **sacct→measured_core_hours 回填链**：需真实集群/sacct 数据。本审计确认提交器 `collect_sacct()`（~159-196）仅取 `JobIDRaw,State,ExitCode`，未取 `Elapsed/AllocCPUS`，且仓库内提交器侧无自动写入 `measured_core_hours` 的生产点。`attempts_ledger` 由调用方自备且无哈希绑定（H1 成立且无自动纠错通道）。
- **锁释放后真实提交成功路径**：本次停在拒绝点验证边界（刻意不触达集群），符合硬红线。
- **批次 count 欺骗**：仅验证 cores/cap/profile 被忽略，未穷举 `count` 全量场景。
- **修复方案**：不在本次只读复核范围内，需用户裁决。

## 遗留说明
- `wp5_guard_review_independent/PROBE.txt` 是早期自动派单竞态残留的**空探针**（与本次 t2 无关），**已由 Lead 随本报告入库时删除**；合成 `fixtures/` 同样不入库（见「快速复跑」的前置清理）。
- 报告文件：`REPORT.md`、`probe_offline.py`、`probe_output.txt` 均位于本审计目录顶层。

## 快速复跑
```bash
cd "E:\Claude Code\电解液溶剂-HB\电解液溶剂HB-Code"
# 前置（必需）：清掉上次运行残留的合成包，否则 C1 抛 "already submitted" 假失败
rm -rf docs\handoffs\four_state_recovery_20261023\audit_submitter_bypass_20261026\fixtures
.\.venv\Scripts\python.exe -B docs\handoffs\four_state_recovery_20261023\audit_submitter_bypass_20261026\probe_offline.py
# 预期：SUMMARY 12 checks, 12 pass, 0 fail；exit 0（脚本自身会重建 fixtures/，勿入库）
```
