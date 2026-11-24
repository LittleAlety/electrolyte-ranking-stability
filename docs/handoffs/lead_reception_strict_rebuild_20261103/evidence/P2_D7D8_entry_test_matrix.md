# P2 · Item 2 七类入口测试逐项对账（D7/D8 接收链工程收口 · 只读取证）

> 2026-11-03 晚。plan item 2「验证」要求的七类真实入口测试逐类盘点；**不改共享测试文件**，缺口以 evidence 内新测试文件补证。切换与账本迁移授权仍 HOLD（Open question 1）。

## 1. 测试载体与运行记录

| 套件 | 命令 | exit | 实测 | 说明 |
|---|---|---|---|---|
| v5 接收套（P1 已跑，输入未变不重复） | `python -m pytest work/test_dmc_staged_receiver_v5.py -q` | 1 | **35 过 + 5 败** | 5 败全 `rdkit` 缺环境（sealed-entry/registration/composite/cross-job 族，导入期） |
| v4 接收套（本轮新跑） | `python -m pytest work/test_dmc_staged_receiver.py -q` | 1 | **30 过 + 19 败**（进度行 49 用例 `[100%]`） | **19 败全部且仅** `ModuleNotFoundError: rdkit @ work\dmc_staged_receiver.py:108`（计数 19=19），非逻辑失败 |
| 提交/结算守卫（P7） | 3 个守卫文件 | 0 | 60 过 + 1 声明跳 | 含 `test_ledger_unchanged_when_gate_rejects` |
| **缺口补测（本轮新增）** | `pytest evidence/p2_item2_gap_tests/test_item2_receiver_entry_gaps.py -q` | **0** | **6/6 全过**（`......`） | 见 §2 前三行 |
| **崩溃恢复补测（2026-11-04 新增）** | `pytest evidence/p2_item2_gap_tests/ -q` | **0** | **9 过 + 1 跳**（`...s......`，两连跑 exit 0） | 3 过=中断拒收字节不变/备份恢复闭环/半条记录拒收；1 跳=迁移工具不存在（见 §3.2） |

## 2. 七类矩阵（plan item 2「验证」逐项）

| # | 类别 | 入口测试（真实入口） | 状态 |
|---|---|---|---|
| 1 | NaN/Inf 混入 | v5 `test_R6_non_finite_populations_are_refused`（param：NaN/nan/Inf/Infinity/-Infinity 5 值） | ✅ **已证**（35 过集内） |
| 2 | 缺字段 | v4 `test_missing_stage_refuses`/`test_partial_hash_set_refuses`/`test_identity_not_declared_refuses`/**`test_K4_register_validates_the_record_shape`→`LEDGER_RECORD_INVALID`**（均 30 过集内）；v5 `test_R5_a_missing_population_line…`、`test_absent_declared_count_is_still_accepted` | ✅ **已证** |
| 3 | 未知 schema | 代码守卫 `dmc_staged_receiver_v5.py:1787`（`schema != SCHEMA → LEDGER_RECORD_INVALID`）；**原缺独立用例** → 补测 `test_unknown_schema_is_refused_and_creates_no_ledger`（`v99` 拒收 + 不落账本文件） | ✅ **本轮补证**（6/6 内） |
| 4 | 跨作业错配 | v5 `test_composite_naming_an_unrelated_completed_job…`（:534）/`…mismatched_freq_job…`（:541）/`…different_deck…`（:560）/`test_cross_job_protocol_guards_are_reachable_directly`（:598） | ⚠️ **用例在、本环境未证**（rdkit 导入期 5 败族） |
| 5 | 重复接收 | v4 `test_repeated_import_does_not_double_count`（→`appended=False, reason=duplicate_member`，:296；本环境 rdkit 败）；**补测** `test_duplicate_same_content_is_idempotent…` + `test_duplicate_member_with_different_evidence_is_refused`（→`MEMBER_NOT_UNIQUE`，代码 `:1839-1846`） | ✅ **本轮补证**（同内容幂等+异内容拒收+字节不变） |
| 6 | 目标文件已存在 | 接收链账本=追加模型，无「覆盖已有目标」路径；等价入口：补测 `test_directory_target_is_refused`（`LEDGER_PATH_INVALID`）；提交/发布链：`test_submit_hpc_batch:326 already exists`（P7 套 20/20）、P6 独占输出 `:202`、sacct `:290` 不可覆写 | ✅ **已证**（映射后覆盖） |
| 7 | 写入中断 | 内容截断：v4 `test_hessian_parser_rejects_a_truncated_matrix`（30 过内）、`test_truncated_mode_list_refuses`（rdkit 败）；**写时中断 fail-closed**：`LEDGER_UNREADABLE`/`LEDGER_MALFORMED_ENTRY`/`LEDGER_TAMPERED` 均「file left untouched」（`:1816/:1819/:1836`）→ 补测两例字节逐位不变断言 | ✅ **已证**（malformed+unreadable 字节不变）；**崩溃恢复语义** ✅ **2026-11-04 补证**：`test_item2_crash_recovery.py` 3 过（半截账本重跑拒收字节不变、备份覆盖恢复后重跑成功 A+B 都在、半条记录 `LEDGER_MALFORMED_ENTRY` 字节不变）+1 显式跳（迁移工具不存在） |

**拒收不污染账本（横切）**：接收链补测 4 例字节断言全过（未知 schema/异内容重复/malformed/unreadable）；提交链 `test_ledger_unchanged_when_gate_rejects`（`tests/test_submission_gate_entry.py:205`，P7 60 过集内）；结算链 `test_settle_ec_campaign.py:47-49`（before/after 字节相等）、`test_ec_submit_entry.py:268`。

## 3. 没有关闭什么（诚实缺口）

1. ~~**跨作业错配与 v4 重复接收用例在本环境因 rdkit 未证**~~ → **2026-11-04 已复验闭环**：独立环境 `.venv-review-20261103`（rdkit 2026.09.1 + pyyaml 6.0.3，重建步骤与版本钉见 `ENV_RECOVERY.md`）下 E1–E5 全部复跑 **exit 0**：v5 套 **40 过**（含跨作业错配族，P1-R5 的 5 个 rdkit 败例全绿）、v4 套 **49 过**（含重复接收族）、P5 注册 **11 过**、P5 门套 **52 过+1 跳**（首跑 5 败为 `No module named 'yaml'` 缺口，补 pyyaml 后全绿）、gap+crash **9 过+1 跳**。日志 `$VENV/_rerun20261104.log`、`$VENV/_s4_retry.log`。
2. ~~崩溃/写中断后的恢复语义无独立入口测试~~ → **2026-11-04 已补** `test_item2_crash_recovery.py`（3 过）。**残留缺口**：账本迁移中断与恢复**无法测**——迁移工具尚不存在（`test_migration_interrupt_recovery_awaiting_tool` 显式 skip，属切换预案前置条件 C6，见 `p10_switch_plan/SWITCH_PLAN.md`），不伪造通过。
3. D7/D8 切换、账本迁移仍 **HOLD**（Open question 1；本批零切换零迁移）。
4. v4 套 19 败与 v5 套 5 败均**非逻辑失败**（全 rdkit 导入期），不作「测试不通过」结论，也不因此放宽任何门。

## 4. 复现命令

```bash
cd 电解液溶剂HB-Code
PYTHONIOENCODING=utf-8 python -m pytest work/test_dmc_staged_receiver.py -q        # 30 过+19 败(rdkit)，exit 1
PYTHONIOENCODING=utf-8 python -m pytest docs/handoffs/lead_reception_strict_rebuild_20261103/evidence/p2_item2_gap_tests/test_item2_receiver_entry_gaps.py -q   # 6/6，exit 0
```

**发布了什么 = 零**（全部只读 + evidence 内新增文件）；恢复=删除 `p2_item2_gap_tests/`、`p10_switch_plan/` 与本文件。
