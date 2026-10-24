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

## 3. 未覆盖范围
- 未验证真实 ORCA 输出格式是否总能解析成功（那需要真实作业；本轮只用合成 ORCA 文本与既有 fixture）。
- 未复核 `import_hpc_opt_numfreq.py` 之外的其它导入器（如 `import_hpc_numfreq.py` 的 NumFreq 遗留路径）是否同样严格；本轮只审 AnFreq 生产路径。
- 未复核聚合器的权重/去重数学（那属 WP3/WP5 面）。