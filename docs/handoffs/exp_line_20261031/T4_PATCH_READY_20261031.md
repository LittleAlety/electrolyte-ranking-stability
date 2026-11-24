# t4 补丁：16 核 profile（**未执行**，等 A 复检 + 用户裁决）

> 状态：**仅规格**。`RESOURCE_PROFILES` 里**尚无** `orca_dmc_vtscf_16c_4h_v1`（实测 `False`）。
> 一旦 A 复检放行且你批准，执行本文件的 4 步即可，全程有验证。

## 0. 前置已全部实测通过（本轮验证）

| 检查 | 实测 | 结论 |
|---|---|---|
| 任务声明的核数 | `declared_task_cores(pkg) = **16**`（读 `job.inp` 的 `%pal nprocs`） | ✔ 与目标一致 |
| 预算算术 | `budget_headroom(cap="64", cores=16, wall=4, count=1)` → `reserved=**64**`、`remaining=**0**` | ✔ 精确等于授权上限，不多不少 |
| 当前 gate | `HOLD` / `submitted=False` | ✔ 未授权状态正确 |
| 未登记 profile 的行为 | `ValueError: unknown manifest resource_profile: 'orca_dmc_vtscf_16c_4h_v1'` | ✔ **fail closed**，不会静默降级 |
| 重复提交保护 | `submission_journal.json` **不存在**、`.batch_1.submission.lock` **不存在** | ✔ 仍是一次可提交状态 |
| 包冻结完整性 | `sha256sum -c PACKAGE_SHA256SUMS` = **14/14 OK** | ✔ |

⇒ **除 profile 外，16 核提交的所有技术前置都已就绪。**

## 1. 补丁内容（唯一一处代码改动）

`scripts/wp_production/submit_hpc_batch.py` 的 `RESOURCE_PROFILES`，插在 `orca_dmc_vtscf_4h_v1`（`:43-45`）之后，**既有条目一字不改**：

```python
    # 2026-10-31 一次性 DMC|LiM_2plus 试验专用：16 核 × 4 h = 64 CH，单元素，
    # 从救援池预留。与既有 4 核 profile 语义隔离：本条目不改动任何一个既有条目。
    "orca_dmc_vtscf_16c_4h_v1": {"engine": "orca", "cores": 16, "wall_hours": 4,
                                 "budget_cap_core_hours": "64",
                                 "attempts_ledger_required": True},
```

**登记面实测只有两项**（那条"四处登记"纪律只针对**新增 `.py` 文件**）：
- 既有 profile 名（如 `orca_dmc_vtscf_4h_v1`）**只在 `submit_hpc_batch.py` 出现**；`README.md`/`docs/65_repo_layout.md`/`tests/test_wp2_cost_semantics.py` **零命中**；
- **没有任何测试枚举 `RESOURCE_PROFILES` 全集**（只按名字取用：`test_ec_recovery_contract.py:16,25`、`test_h2_diagnostic_budget_cumulative.py:80-91`、`test_p4_screening_plan.py:157`）。

⇒ 只需 ① 本体条目 ② 本次自己的入口级负测。**不会让既有测试变红。**

## 2. 入口级负测（4 条，必须真拒）

| # | 用例 | 期望 |
|---|---|---|
| N1 | 本包 `declared_task_cores == 16` 且 `== profile["cores"]` | 通过 |
| N2 | 把 manifest 的 profile 换成 4 核的 `orca_dmc_vtscf_4h_v1` | 拒：`refusing to silently change the resource`（`:725-731`） |
| N3 | manifest 写未登记 profile 名 | 拒：`unknown manifest resource_profile`（`:217`） |
| N4 | `budget_headroom(cap="64", 16c, 4h, 1)` | `reserved=64`、`committed+reserved ≤ 64` |

## 3. 执行顺序（批准后）

1. 打上面那一处补丁；
2. 跑 N1–N4（可写成 `work/exp_line20261031/red_rev5_16c_profile_entry.py` 的 GREEN 版，该 RED 版已存在）；
3. **重跑 `work/_profile_audit.py`**（仓库既有的跨 profile 审计器，60 包 / 0 findings）复核新包，**不要手算**；
4. 重生成 `PACKAGE_SHA256SUMS` 并复验（我上一轮就漏过这一步，导致 13/14）。

## 4. 红线

本文件**未改动** `scripts/` 任何内容；`RESOURCE_PROFILES` 仍是原状；包 `HOLD`；**0 提交**；正式记录 **45 accepted / 3 limited**。