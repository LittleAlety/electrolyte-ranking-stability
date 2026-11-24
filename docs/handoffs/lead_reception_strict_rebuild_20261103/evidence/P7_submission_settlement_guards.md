# P7 · 受保护提交与幂等结算守卫盘点（Plan action item 7 · 第一轮）

> 会话：公共处理会话（唯一共享生产写入者）｜2026-11-03。**本轮零提交**：无 Lead 转交且用户已批准的实验，执行面不触发——本批交付=守卫现状盘点+实测入口。
> 红线自检：未提交作业、未新增计算、未改阈值、未动正式账本/费用。

## 1. 本轮实测（命令+结果）

```
$ python -m pytest tests/test_submit_budget_gate.py tests/test_submission_gate_entry.py \
                   tests/test_evidence_gate_and_cost.py -q -rs -p no:cacheprovider
exit 0 | 61 = 60 passed + 1 skipped
SKIPPED [1] tests/test_submit_budget_gate.py:88: attempt_ledger.json not built yet (declared unavailable)
```
跳过为**声明式不可用**（账本未建即如实跳过，非静默吞测）。桥接全 FakeRunner mock，**无真实 sbatch**（`test_submission_gate_entry.py:9`）。

## 2. 守卫现状 ↔ Plan item 7 验证清单

| 验证项 | 机读守卫（文件:行） | 实测 |
|---|---|---|
| HOLD 拒绝 | `evidence_gate.py:64-109`：`NextAction.HOLD` 状态机，仅 `ready` 才 `SUBMIT_ONCE`；`submit_hpc_batch.py:549` EC 包 `submission_gate=HOLD` 即 `ValueError` 拒提交 | 入口测试 61 例中覆盖（60 过） |
| 缺授权拒绝 | `build_ec_recovery_package.py:194-196`：`submission_gate="HOLD"` + `blocked_reason="design-only: user has not approved the EC 32 CH proposal"`——授权缺失=机读字段，非口头 | 包文件实读确认 |
| 超预算拒绝 | `submit_hpc_batch.py:401 budget_headroom()` + 逐包 `budget_cap_core_hours`（`:29-123` 共 13 包全 `attempts_ledger_required=True`）；`:86` 注释：第二次提交被 `budget_headroom` 直接拒绝 | `test_submit_budget_gate.py` 过 |
| 重复提交拒绝 | `:86`（headroom 拒二次）、`:273` `malformed or duplicate scheduler_state.request key` 拒重、模块 docstring `idempotent submission` | 同上 |
| 预留与实耗分开 | `:55` 结算时释放未用小时；`wall_hours_reserved` 为预留、实耗由终态 sacct 结算（`:146`：ledger 必需，actual spend settles from terminal sacct） | 结算读数分列 |
| 技术失败仍计真实成本 | 结算源=终态 sacct 实据（`JobIDRaw,State,ExitCode,ElapsedRaw…`，`prepare_remote_final_checks.py:25`）——FAILED/CANCELLED 同样落 terminal 记录按实耗计入；未知 sacct 状态**非终态 fail-closed**（`evidence_gate.py:15,263`） | 白名单机制在案 |
| 跨作业接续费用不重扣 | `submit_hpc_batch.py:377` committed+in-flight **按 Slurm allocation 去重**后计 core-hours | 单测过 |
| 元数据修正不抹原始记录 | 修正为 append-only jsonl；消费侧同时留 `settlement_protocol_label_original` + `settlement_protocol_label`（effective）+ `protocol_metadata_correction_ids`（`rebuild_strict_isolated.py:258-260`） | P6 跑次实读 |
| 门先于副作用 | `test_submission_gate_entry.py`：通用 gate 在 doctor/lock/submit **之前**执行；缺 gate 字段/非 OPEN/`submitted!=False` 一律拒 | 60 过实测 |
| 结算证据不可篡改 | `:290` `sacct.terminal already exists; refusing to overwrite immutable evidence`；`:308` sacct 必须恰一行 | 单测过 |

## 3. 发布了什么

**零正式发布**：无提交、无结算写入、无正式账本/费用变更（本轮只跑测试+读代码）。

## 4. 没关闭什么

1. **执行面未触发**：无 Lead 转交的用户已批准实验 → 「准备或执行相应操作」本轮为空转；守卫验证≠执行演练。
2. **端到端真实结算未重放**：sacct 实据结算路径需真实 Slurm 环境与作业，本机不可重放——不自动申请计算，留待有真实作业时随批次验证。
3. **`attempt_ledger.json` 未建**：`test_submit_budget_gate.py:88` 条件跳过——该账本层测试在本 checkout 条件未满足（declared unavailable）。
4. EC 32 CH 提案仍缺用户批准 → HOLD 照旧；D7/D8 切换、身份/coverage、rdkit 照旧（见 P1/P4/P5/P6）。
5. items 5（汇聚视图候选）、8、9 未动。

## 5. 如何恢复 / 复现

本批**无受控文件修改**，无需恢复。复现（cwd=仓库根）：
```bash
python -m pytest tests/test_submit_budget_gate.py tests/test_submission_gate_entry.py \
  tests/test_evidence_gate_and_cost.py -q -rs -p no:cacheprovider      # 期望 exit 0，60 passed + 1 skipped
```
