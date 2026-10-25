# STEP2：plan_compliance 未满足项逐条核查（增量落盘）

来源：`scripts/wp_production/build_plan_compliance.py`（grep 定位分支行号）、各产物现算、`outputs/physics_completion/compliance/plan_compliance.csv`

判定：`一致` / `阻塞原因已不成立` / `陈述过时（数字或对象已变）`

## 第1批（1-5）
| # | item_id | status | 生成器分支行号 | 生成器读的输入（从代码推断） | 当前实测（命令+退出码） | 判定 | 备注 |
|---|---------|--------|----------------|--------------------------|----------------------|------|------|
| 1 | wp2_conformer_ensemble | partial | L426 | `ensembles/production_ensemble_labels.csv`, `ensembles/ensemble_free_energies.csv` | `ensembles/production_ensemble_labels.csv`: 50 行，accepted=44, limited=4, provisional=0（`python -X utf8 -c ...` exit 0） | 一致 | 只计 accepted；44/48 |
| 2 | wp2_sampling_extension | partial | L456 | `sampling/sampling_acceptance.csv`, `sampling/sampling_escalation.csv`, `data/metadata/physics_completion_set.csv` | `sampling/sampling_escalation.csv`: 24 行全 `registered_pending_round1_free_energy_check`；实际执行集与方案 3.3 指定不一致（exit 0） | 一致 | 升级待第1轮生产自由能判定 |
| 3 | wp2_state_identity_qc | partial | L509 | `state_identity/*`, `state_identity/thresholds.json` | `state_identity/thresholds.json`: frontier_localization.status=not_computed（exit 0） | 一致 | frontier_localization 显式 not_computed |
| 4 | wp3_pair_evidence | partial | L528 | `pair_evidence/pair_evidence.csv` | `pair_evidence/pair_evidence.csv`: 66 行 STABLE=55, UNRESOLVED=9, ROBUST_INVERSION=2（exit 0） | 一致 | 容差来自重算误差 |
| 5 | wp3_targeted_second_method | partial | L554 | `pair_evidence/targeted_recheck/*` | `pair_evidence/targeted_recheck/job_plan.csv` 24 行，`recheck_results.csv` 24 行（exit 0） | 一致 | 规则先于结果登记 |

## 第2批（6-10）
| # | item_id | status | 生成器分支行号 | 生成器读的输入（从代码推断） | 当前实测（命令+退出码） | 判定 | 备注 |
|---|---------|--------|----------------|--------------------------|----------------------|------|------|
| 6 | wp3_mechanism_cases | partial | L567 | `pair_evidence/mechanism_cases.csv` | CASE1/CASE2：original_structure/method_sensitivity/selection_set_impact=已具；density_spin/coordination/eg_decomposition=部分（UTF-8 读取 exit 0） | 一致 | 六项部分达成 |
| 7 | wp5_new_endpoint_in_budget | partial | L695 | `active_learning/round_diagnostics.csv`, `active_learning/success_budget.csv` | `round_diagnostics.csv` 296 行，旧池口径（非盲）与正式 A/B 分离（exit 0） | 一致 | 不可混用池口径 |
| 8 | wp5_formal_ab_stop_budget_reached | partial | L732 | `active_learning/blind_replay/AB_axis_endpoint.csv`, `AB_index.json` | `AB_axis_endpoint.csv` 32 行：computed=19，not_reached_within_pool=13；model_is formal_frozen_predictor=24/baseline_not_formal=8（exit 0） | 一致 | 子池达标不等于全 12 分子 |
| 9 | wp5_two_consecutive_points | partial | L744 | 同上 | 同上，stop_budget_status 三语义并存（exit 0） | 一致 | 正式 A/B 按联合口径计数 |
| 10 | wp5_absolute_cost_ledger | partial | L763 | `cost/cost_ledger.csv`（`status=='MISSING'` 计数） | 10 行，MISSING=3（status Counter: measured 4 / planned 3 / MISSING 3），与 measured 串 `cost_rows=10 MISSING=3` 一致（exit 0） | 一致 | 项目级标量等闭环后再填 |

## 第3批（11-15）
| # | item_id | status | 生成器分支行号 | 生成器读的输入（代码确认） | 当前实测（命令+退出码） | 判定 | 备注 |
|---|---------|--------|----------------|--------------------------|----------------------|------|------|
| 11 | wp5_remaining_unqueried_error | partial | L787-796 | `active_learning/round_diagnostics.csv`（`remaining_unqueried_error_status`/`cumulative_core_hours_status`=='MISSING' 计数） | 296 行，两列 MISSING 均=296，与 measured 串逐字一致（exit 0） | 一致 | 旧回放无候选级预测/逐查询成本映射 |
| 12 | wp5_pool_extension | not_satisfied | L797-806 | `data/metadata/physics_completion_set.csv`（cohort=='extension' 行数，阈值 ≥8 才 partial） | cohort 取值={excluded, main, method_audit, sampling_audit}，**extension 行=0** → not_satisfied 正确（exit 0） | 一致 | extension_pool.csv 存在但未登记进 set.csv 的 extension cohort |
| 13 | wp6_explicit_ligand | blocked_on_production | L808-846 | `explicit_ligand/` 目录文件数、`explicit_ligand_plan.csv`、labels（L158-174 `strict_main_counts`/`wp6_gate_ready`）、`wp2_progress` scientific accepted_legs | plan_rows=4, executed_jobs=0, accepted ensembles=44, measured 串 `li_pair_complete=12/12` 系 **scientific ledger 口径**（C11-C12 只读重放生成器逐字复现）；labels 系综口径为 9/12（C13）；两种口径下 gate 均由 44/48 半边失败 → **blocked_on_production 正确**（exit 0） | 一致（疑点已定案，见下节） | 同名字段跨行口径不同，属命名可读性问题非数据错 |
| 14 | stop_rules_registered | partial | L848-864 | `config/physics_completion_v1.yaml`（'stop_rules' 子串）、`li_motif_sampling/motif_plan.csv`（`motif_screen_status=='computed'` 计数） | yaml 含 stop_rules=True；motif_plan 24 行、computed=23 → `23/24` 与 CSV measured 一致（exit 0） | 一致 | sampling_limited 待第1轮生产自由能 |
| 15 | wp2_pilot_cost_fields | partial | L866-901 | `cost/pilot_cost_ledger.csv`（memory=='MISSING'、retry=='UNVERIFIABLE'、raw_output_status=='verified_on_disk' 计数） | 109 行：memory_MISSING=109, retry_UNVERIFIABLE=109, raw_verified=109/109，与 measured 串一致；partial 判定正确（pilot_evidence_complete 要求 MISSING==0）（exit 0） | 一致 | 字段存在≠证据完备 |

## 第4批（16-17）
| # | item_id | status | 生成器分支行号 | 生成器读的输入（代码确认） | 当前实测（命令+退出码） | 判定 | 备注 |
|---|---------|--------|----------------|--------------------------|----------------------|------|------|
| 16 | strict_readiness_evidence | not_satisfied | L918-971 | `strict_readiness_wiring.REQUIRED_CHECKS` 六项 | CSV measured：checks_passed=5/6, failed=wp5_full_target_pool_evaluated；我现算 `AB_axis_endpoint.csv` 的 (task,baseline,acq,n_pool) 8 组组合中 **n_pool 全部 ≠12**（4 组=11、4 组=9）→「子池非全 12」的失败原因**仍成立**（exit 0） | 一致 | fail-closed 语义正确 |
| 17 | plan_overall_complete | blocked_on_production | L972-988 | `work/wp2prod/**`, labels, closure 表等（plan_complete 十条件合取 L944-955） | 条件链里 `production_ensembles==48` 不满足（实测 44）、`strict_evidence_ok=False`（第16项）→ blocked_on_production 正确；measured 串 main_states=48/48（runtime 口径）与 production_ensembles=44/48（accepted 口径）并存（exit 0） | 一致 | 硬闸门分母固定 12×4 |

## exempt 3 行（单列，不计入 17）——豁免理由是否仍成立
| item_id | 豁免理由（CSV note） | 我的核验 | 判定 |
|---|---|---|---|
| wp1_reduction_state_checks | 本批次只有 M/M+/LiM+/LiM2+，无还原态腿（unbound_anion 排除） | `method_audit/job_matrix.csv` 128 行，state 取值恰为 {LiM_2plus, LiM_plus, M, M_plus}，无任何还原态 | **豁免理由仍成立** |
| wp4_primary_text_check | 两篇 Ue 正文未取得（付费墙+验证码），14 行保持 transcription-only | `data/anchors/primary_source_verification.csv` 14 行全部 `primary_source_status=full_text_not_obtained`、`primary_verification_level=not_obtained`、blocker=`Ue1994_closed_access_Ue1997_bronze_IOP_Radware_botwall`；`transcription_reverified_status` 14/14 reverified match | **豁免理由仍成立** |
| wp4_new_comparable_entries | 检索协议已执行，新命中 0 条，按 §6 停止规则保留 limitation | `data/references/anchor_retrieval_execution.md` 存在，tier_1 condition-matched=0 未被推翻 | **豁免理由仍成立** |

## #13 口径疑点的定案（追加，C11-C13 复现）
只读重放 `build_plan_compliance.build_rows()`（不写盘，等价 `--check`）实测返回 **WP6 status=blocked_on_production, measured=`plan_rows=4 executed_jobs=0 li_pair_complete=12/12 required_li_pairs=9 production_ensembles=44/48 gate_ready=false`**，与 CSV 逐字一致（叠加 C8 的 `--check` 字节一致 ⇒ CSV 无誊写错）。定论：
- 生成器喂给 `wp6_gate_ready` 的 `li_pair_ok` 取 **runtime scientific ledger 口径**（L318-320 `strict_main_counts(set_main, progress["scientific"]["accepted_legs"])`，48 条 accepted legs ⇒ 12/12）；
- 我先前复算的 **9/12 是 labels 系综 accepted 口径**（DMC/DOL/EC 三分子的 LiM_2plus 态未 accepted）。
- 两种口径下 Li 配对条件**都 ≥9 已满足**，gate 失败只由 `production_ensembles=44/48` 这一半决定，**状态判定不受影响**（gate_ready=false、blocked_on_production 均正确）。
- 遗留的只是一个**命名清晰度问题**：同名短语 `li_pair_complete` 在 wp2 行（scientific 口径 12/12）与系综行（44/48）语义不同，读者易误读——与 t3 那次「报告口径要与文件逐字一致」是同一教训的另一面（文件里同名字段跨行口径不同）。建议 Lead 决定是否给 L838 的串改为显式 `li_pair_complete_scientific_ledger=` 之类消歧命名；**本项判定维持「一致」**（不是数据错，是表述可读性）。

## 汇总
- **17/17 判定「一致」**（无「阻塞原因已不成立」项；无状态该改写的项）。
- **1 处数字疑点上报**（#13 wp6_explicit_ligand 的 `li_pair_complete=12/12` measured 串与 gate 口径 9/12 并存——属生成器两个口径变量同名字段所致，不改变状态判定；建议 Lead 决定是否给 L838 的串改用显式区分命名）。
- 「陈述过时」检查：t4 时期发现的 `wp2_sampling_extension` note「3->6 升级对全部态仍是 registered_pending」经 `sampling_escalation.csv` 实测 24/24 仍为 registered_pending——**该陈述未过时，仍成立**（t4 附录里曾疑其与采样审计状态矛盾，实际 sampling_escalation 与 sampling_audit_3to6 是两个对象：升级登记 vs 池差异比较，不构成过时）。

## 命令清单（实际运行与退出码）
| # | 命令 | 输出摘要 | 退出码 |
|---|---|---|---|
| C1 | `.venv\Scripts\python.exe -X utf8 -c "csv 读 plan_compliance.csv 筛三态"` | count 17（partial 13 / not_satisfied 2 / blocked_on_production 2） | 0 |
| C2 | `python -c "txt.find(item_id) 定位 build_plan_compliance.py 分支"` | 17 个行号（L426/456/509/528/554/567/695/732/744/763/788/799/833/856/887/957/973） | 0 |
| C3 | labels 计数 | 50 行，accepted=44, limited=4, provisional=0 | 0 |
| C4 | pair_evidence 计数 | 66 行 STABLE 55/UNRESOLVED 9/ROBUST_INVERSION 2 | 0 |
| C5 | AB_axis_endpoint stop_budget_status + n_pool | computed 19/not_reached 13；n_pool 全≠12（11×4、9×4） | 0 |
| C6 | li_motif_screen 按腿 kept | 24 腿，AN\|LiM_2plus 零 kept → 23/24 | 0 |
| C7 | pilot_cost/cost_ledger/mechanism_cases/targeted_recheck/thresholds.json | 全 MISSING/UNVERIFIABLE；MISSING=3；六项 3已具3部分；24/24；frontier not_computed | 0 |
| C8 | `python scripts/wp_production/build_plan_compliance.py --check`（只读） | `CHECK OK -- plan-compliance table is byte-identical (42 items)` | 0 |
| C9 | gate 口径 li_pair 独立复算（按 L170 定义） | 9/12，与 wp6_gate_ready=false 判定链一致 | 0 |
| C10 | exempt 三源核验（job_matrix states / primary_source_verification / retrieval doc） | 无还原态；14/14 not_obtained；tier1=0 | 0 |
| C11 | 只读 `wp2_progress.build_snapshot(REPO)` 读 accepted_legs | 48 条（C01\|M…），scientific 口径 | 0 |
| C12 | 只读 `build_plan_compliance.build_rows()` 取 wp6 行 | status=blocked_on_production；measured 与 CSV 逐字一致（li_pair_complete=12/12） | 0 |
| C13 | labels 系综口径 li-pair 独立复算 | 9/12（DMC/DOL/EC 的 LiM_2plus 未 accepted） | 0 |

（C11-C13 均为纯只读内存计算，未写任何产物、未触网络/集群。）

## 未覆盖部分
- **partial-audit 的 REPORT.md 在本次核查全程仍为 6 B 占位**（`Get-ChildItem` 实测，mtime 2026-10-25 15:22:13）——无断言可对照，本任务按 Lead t5 指令改为独立建立 ground truth（t4 的降级路径沿用）。
- #13 疑点仅定位到口径并存，**未验证生成器内部变量赋值顺序**（需逐行追 `li_pair_ok` 在 L320/391/838 的读写序列，超出只读抽验范围，留给 Lead/负责生成器的成员）。
- 未重跑任何生成器写模式（只跑过 `--check` 只读）；未复核 satisfied 22 行与 exempt 之外的行。
- `sampling_3to6_diff` 的实际 G_ensemble 数值差异未复算（属采样审计对象，t4 附录已有三方互证）。
