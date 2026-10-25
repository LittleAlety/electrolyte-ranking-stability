# 验收链离线审计（2026-10-24；**花 800 core-hours 之前先证明闸门真会响**）

目的：确认「提交生产计算后，验收标准真的会被执行」，而不是只在文档里写着。
全部结论来自只读代码审阅 + 既有测试 + 本轮新增测试；**未运行任何 ORCA/xTB，未触网**。

## 1. 端到端证据链（file:line 级）

| # | 环节 | 位置 | 行为 |
|---|---|---|---|
| 1 | **容差同一性**（第一道反漂移） | `import_hpc_opt_numfreq.py:163-165` | ORCA 打印的容差必须等于 `VERY_TIGHT_THRESHOLDS[key]`（`abs_tol=5e-12`），否则抛 `VeryTightOpt tolerance mismatch for <key>`。**请求更宽容差的腿会被拒收，不会被按更宽的数字接受。** |
| 2 | **五项数值强制** | `import_hpc_opt_numfreq.py:166-168` | 任一 `value > frozen` 即抛 `VeryTightOpt final criterion not met: <key>=<v> > <frozen>`（覆盖 TolE / TolRMSG / TolMaxG / TolRMSD / TolMaxD）。 |
| 3 | **缺值不造数** | `import_hpc_opt_numfreq.py:158-162` | `Energy change` 行缺失时登记 `energy_change_absent = first_point_convergence_geometry_never_moved`（首点即收敛、原子未动）；**其它行缺失直接抛错**。 |
| 4 | **TolE 的专项裁决** | `import_ensemble_structures.py:935-947` | 终点判据失败且几何四项达标 ⇒ 旗标 `strict_reopt_required`；代码内记录 2026-10-17 裁决：**reject**，补救是从该末几何严格重优化。 |
| 5 | **旗标→状态** | `import_ensemble_structures.py:1047-1056` | **任一** flag ⇒ `status=technical_complete_qc_failed`、`failure_class=flags[0]`；无 flag 才是 `computed`。 |
| 6 | **不入池** | `build_production_ensemble_aggregator.py:817-818` vs `824-854` | 只有 `status=="computed"` 进 `extras_pool`；`technical_complete_qc_failed` 只计入 rescue/failed/limited，**永不入池**。 |
| 7 | **并使该态无法 accepted** | `tests/test_build_production_ensemble_aggregator.py:261-273` | 有 `strict_reopt_required` 额外成员时，态为 `provisional`、`n_unresolved=1`（不是 `accepted`）。 |
| 8 | 其余硬闸门 | `import_ensemble_structures.py:959-969` | `n_freq == 3N`、`imaginary_modes == 0`、热化学齐备、`|G − (E + thermal)| ≤ 2e-7` 恒等式；连接关系 start→final 不变；Hessian↔几何用**框架无关**的原子对距离不变量校验（`:73-121`）。 |

**结论：五项阈值与六项验收在**写入路径与聚合路径**上都真正 fail-closed**；`geometry_criteria_ok` 对缺值返回 `False`（`import_ensemble_structures.py:124-129`），不存在「缺值默认为零」。

## 2. 本轮发现并关闭的两个缺口

### G1（前一轮已修，`06d08aa`）五项阈值无一致性守卫
三份表示（代码常量 / 冻结契约 / 两处生成器散文）之间**没有任何测试**。已补三道测试覆盖；RED 实证见 `work/_threshold_guard_red.py`。

### G2（本轮修复）容差同一性护栏**无测试**
第 1 环 `tolerance mismatch` 是反漂移的关键护栏，但既有测试**只改数值列**（4e-5 > 3e-5），**从未改容差列** → 该分支零覆盖；把它放宽或放松 `abs_tol` 都不会被发现。
**修复**：新增 `tests/test_hpc_opt_numfreq_import.py::test_a_printed_tolerance_that_differs_from_the_frozen_one_is_rejected`，对 **5 个键逐一**断言「容差列被改 ⇒ 抛 `tolerance mismatch for <key>`」，并先断言冻结表本身被接受。
**RED 实证**（`work/_tolerance_guard_red.py`）：护栏在位 GREEN；把 `math.isclose` 中和为恒真后，该测试**按预期失败**（`Failed: DID NOT RAISE ValueError`），退出码 0，生产模块未被改动。

### G3（本轮修复）**SCF 收敛此前在生产验收路径上没有任何断言**
计划 §6.3 把 SCF 收敛列为**不可被其它项替代**的检查之一，但 `import_ensemble_structures.py` 只断言
`ORCA TERMINATED NORMALLY`（:867）——那只是**技术标记**；`import_hpc_opt_numfreq.py:576-591` 的
「absolute guard」守的是「热化学 ↔ 末次单点能」一致性（≤1e-5 Eh），**也不是** SCF 断言；
`build_state_identity_qc.py` 只在**文档字符串**里提 SCF、实现里没有。⇒ 一个 SCF 未收敛的腿曾可能走到 `computed`。

**先测量后动手（无翻转证明）**：对 `production_ensemble_structures.csv` 中所有**入池腿**
（status `computed`/`ready`，共 **115** 条）逐条读其**记录的 `log_path`** 核对：
**115/115 全部带 `SCF CONVERGED AFTER N CYCLES`、`log_sha256` 全部相等、日志文件无一缺失**
（另：`work/wp2prod/**/*.log` 126 个中 125 个带签名，唯一例外是非腿日志 `_reopt/watch_reopt.log`；
8 个含「NOT CONVERGED」字样的**全部位于 `superseded_numfreq/`、`superseded/` 历史目录**）。
⇒ 加该断言**不翻转任何现行接受状态**（脚本 `work/_scf_nodiff_proof.py`）。

**修复**：新增 `RE_SCF_CONVERGED` 与 `qc_task` 中的门（缺签名 ⇒ flags 加 `scf_not_converged`
⇒ 经既有逻辑变 `technical_complete_qc_failed`）。测试夹具 `_log()` 与 `_converged_final_log()`
**补上真实 ORCA 必打的签名行**（原夹具造出了一份真实运行不会产生的日志，加门后 9 个测试立刻变红，
这本身就是门生效的证据）；新增
`tests/test_import_ensemble_structures.py::test_a_log_without_an_scf_convergence_signature_is_qc_failed`。
**RED 实证**（`work/_scf_gate_red.py`）：护栏在位 GREEN；把 `RE_SCF_CONVERGED` 中和为「匹配一切」后
该测试**按预期失败于 `AssertionError`**，退出码 0。
（注：第一次演示用同一临时目录重跑，失败原因是 `FileExistsError` 而非断言——那是**无效演示**，已改用全新目录重做。）

## 3. 本轮的边界（如实记录）
- **该门覆盖的是「经 `qc_task` 的成员」**（即注册新增成员：救援/扭转/恢复/探针腿）——**新计算正是从这条道进**。
  **48 个冻结主态不走这条路**：`primary_rows()` 直接从 `candidates.csv` 取 `status` 并复制逐腿 JSON 字段
  （`import_ensemble_structures.py:1075-1114`），其中**没有** SCF 断言。因 115/115 现行腿都带签名，
  两条路当前结果一致；若要让主态也受同一门约束，需在逐腿 JSON 生产链（`import_hpc_opt_numfreq.py`）
  或 `primary_rows()` 增加同等断言——**本轮未做，登记为后续**。
- 未验证真实 ORCA 输出格式是否总能解析成功（那需要真实作业；本轮只用合成 ORCA 文本与既有 fixture）。
- 未复核 `import_hpc_numfreq.py` 的 NumFreq 遗留路径是否同样严格；本轮只审 AnFreq 生产路径。
- 未复核聚合器的权重/去重数学（那属 WP3/WP5 面）。