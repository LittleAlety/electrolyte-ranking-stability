# L02 EC 机器合同修正与负向用例（2026-10-29）

范围：只修 **机器合同**，不创建提交包、不申请预算、不提交任何作业。
依据：`docs/plans/CORE_PLAN_EXECUTION_SUPPLEMENT_20261029.md` §5.2。

## 1. 改了什么

| 项 | 改前 | 改后 | 理由 |
|---|---|---|---|
| `RESOURCE_PROFILES["orca_production_4h_v1"]["attempts_ledger_required"]` | `False` | **`True`** | 补充计划 §5.2 明写「必须在此新 profile 范围内强制真实账本」；历史 profile（`orca_production_v1` / `xtb_*` / `h2_*` / `12h_*`）语义**未动** |
| 新增 `scripts/wp_production/ec_recovery_contract.py` | — | 纯函数合同 | 把「p4→p7、一次在飞、≤2 次提交、16 CH/元素、32 CH 帽、错候选/低报/第三腿拒绝」变成**机器可验**，供 L03 建包器与提交器共用 |

`ec_recovery_contract.py` 的固定常量：`EC_CANDIDATES=("ec_v2_p4","ec_v2_p7")`、`EC_PROFILE="orca_production_4h_v1"`、`EC_CORES=4`、`EC_WALL_HOURS=4`、`EC_ELEMENT_CORE_HOURS=16`、`EC_CAP_CORE_HOURS=32`、`EC_MAX_SUBMITTED_ELEMENTS=2`。

- `next_candidate(history)`：未提交 ⇒ p4；p4 在飞 ⇒ `None`；p4 通过 ⇒ `None`（campaign 结束）；p4 终态失败 ⇒ p7；p7 已提交 ⇒ `None`（**永无第三腿**）。
- `check_campaign_contract(...)` 依次拒绝：未登记候选、非下一步（p7 抢跑）、错 profile、错核数、错墙钟、元素数 ≠ 1、**低报预留**（声明值 ≠ 16×元素数）、第三腿、超 32 CH 帽、已有 active/pending。全部 `raise ContractViolation`（fail-closed，调用方无法降级为告警）。

## 2. 负向用例（`tests/test_ec_recovery_contract.py`，18 项）

覆盖四类点名拒绝 + 资源形状：
1. **漏账本**：断言 `orca_production_4h_v1.attempts_ledger_required is True`（且历史 profile 保持原语义）；
2. **错候选**：`ec_v2_p3` 拒、`p7` 抢跑拒；
3. **低报预留**：声明 8 CH 拒；
4. **第三腿**：已提交 2 个仍投拒；
5. 另含：超帽、active/pending 在飞、错 profile/核数、多元素在飞、p4 通过即停、p4 失败才开 p7。

## 3. 验证（全部只读、零计算）

```text
pytest tests/test_ec_recovery_contract.py tests/test_wp2_cost_semantics.py tests/test_scripts_index.py -q  -> 26 passed
pytest tests/test_repo_layout.py tests/test_submit_hpc_batch.py tests/test_evidence_gate_and_cost.py -q     -> 59 passed
work/_validate_ec_v2_presubmission.py                                                                      -> 5 passed, 0 failed
```

`work/_validate_ec_v2_presubmission.py` 末行仍为 `Status: HOLD (awaiting user approval)`。

## 4. 边界（防误读）

- 本步**没有**创建 `tasks/`、`batch_*.txt`、`sbatch`、`PACKAGE_SHA256SUMS`，**不是**可提交包——那是 L03。
- 本步**没有**申请或占用任何 core-hour；`32 CH` 仍是**提议**，不是已批准额度。
- `attempts_ledger_required=True` 只改变**未来**对 `orca_production_4h_v1` 的提交要求，未回溯任何历史包。

## 5. 下一步

L03：按 schema-2 生成 `p4` 单腿可执行 HOLD 包（与 `build_dol_ec_recovery_package.py` 同形；p7 只留不进入生产候选表的模板），并用真实加载器/提交器门函数离线验证；L04 并行诊断 DMC 历史过程。
