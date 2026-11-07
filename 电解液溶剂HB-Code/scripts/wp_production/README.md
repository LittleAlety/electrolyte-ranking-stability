# `scripts/wp_production/` —— 历史入口兼容层（HISTORICAL_ENTRY）

> 本文件由 `scripts/production/build_script_index.py` 生成，**不要手改**。

**这里没有实现。** 真实实现已按职责迁到 `scripts/production/<category>/`。
本目录下每个 `*.py` 都是同形状的转发文件：被导入时加载真实模块并把符号转出，
被直接执行时以 `__main__` 运行真实文件。

## 为什么必须保留

删除任一兼容入口 = 让一个**已登记路径**悬空：

1. 22 个生成器把 `scripts/wp_production/<自己>.py` 写进已生成的 `*_index.json` / 记录件；
2. `outputs/week26/provenance_refreeze_record.json` 是**冻结历史**，同样记录旧路径；
3. `screen_li_motifs.py` 的路径写在 32 个**已计算** CSV 正文里（重跑需要 xTB）；
4. 243 个测试文件用旧路径作为定位键。

## 实现里为什么还留着旧路径字符串

真实实现里仍能见到 `"generator": "scripts/wp_production/<x>.py"` 这类字面量与
命令示例——这些**故意不改**：

* `generator` 字段是被写进已生成产物里的**稳定标识**；改它等于改产物字节（并作废已核验哈希）；
* 命令示例指的就是本兼容入口，照抄仍然可执行。

分类与真实实现位置以 `scripts/production/SCRIPT_INDEX.md` 为准。

## 提交纪律

`submit_hpc_batch.py` 是唯一正式提交入口；不得直接调用 `hpc submit`。
每条任务使用不可变 `attempts/<attempt-id>`，并在账户级 `.wp2_submit.lock`
保护下执行“运行中 + 排队中 ≤20”门禁。用 `--collect-sacct` 取得终态证据后，
才能判断是否属于自动技术重试。

## 退休条件（三条全满足才可删）

1. 生成器重建后，产物里的 `generator` 全部指向新路径且各自 `--check` 通过；
2. `tests/` 里不再有**以旧路径为入口**的调用——2026-11-07 实测：仍有 88 个测试文件提到
   `scripts/wp_production`，但**读实现源码的命中为 0**（源码读取一律走 `tests/_prod_paths.py`
   的 `prod_script()`）；剩下的都是子进程调用或 `spec_from_file_location`，**当前是有意保留**，
   用来持续验证本兼容层；
3. 交付镜像重建且 `build_physics_completion_deliverables.py --check` 通过。

满足后：删本目录 `*.py`，把 `registry.json` 里对应 `shim` 置 `no`，再跑
`python scripts/production/build_script_index.py --check`。

## 索引（兼容入口 → 真实实现）

| 兼容入口 | 真实实现 | 分类 |
| --- | --- | --- |
| `archive_raw_outputs.py` | `scripts/production/release/archive_raw_outputs.py` | release |
| `build_anchor_condition_audit.py` | `scripts/production/analysis/build_anchor_condition_audit.py` | analysis |
| `build_bgroup_pilot_preregistration.py` | `scripts/production/ensembles/build_bgroup_pilot_preregistration.py` | ensembles |
| `build_compute_provenance.py` | `scripts/production/analysis/build_compute_provenance.py` | analysis |
| `build_coverage_reviews.py` | `scripts/production/ensembles/build_coverage_reviews.py` | ensembles |
| `build_d6_preregistration_draft.py` | `scripts/production/analysis/build_d6_preregistration_draft.py` | analysis |
| `build_descriptor_analysis.py` | `scripts/production/analysis/build_descriptor_analysis.py` | analysis |
| `build_ensemble_cost_by_family.py` | `scripts/production/analysis/build_ensemble_cost_by_family.py` | analysis |
| `build_frontier_identity_evidence.py` | `scripts/production/validation/build_frontier_identity_evidence.py` | validation |
| `build_frontier_legs.py` | `scripts/production/validation/build_frontier_legs.py` | validation |
| `build_frontier_localization.py` | `scripts/production/validation/build_frontier_localization.py` | validation |
| `build_gap_decision_support.py` | `scripts/production/analysis/build_gap_decision_support.py` | analysis |
| `build_li_motif_plan_round2.py` | `scripts/production/ensembles/build_li_motif_plan_round2.py` | ensembles |
| `build_li_motif_sampling_plan.py` | `scripts/production/ensembles/build_li_motif_sampling_plan.py` | ensembles |
| `build_p4_screening_adjudication.py` | `scripts/production/ensembles/build_p4_screening_adjudication.py` | ensembles |
| `build_pair_recheck_plan.py` | `scripts/production/analysis/build_pair_recheck_plan.py` | analysis |
| `build_physics_completion_deliverables.py` | `scripts/production/release/build_physics_completion_deliverables.py` | release |
| `build_plan_compliance.py` | `scripts/production/analysis/build_plan_compliance.py` | analysis |
| `build_probe_routes.py` | `scripts/production/validation/build_probe_routes.py` | validation |
| `build_production_ensemble_aggregator.py` | `scripts/production/ensembles/build_production_ensemble_aggregator.py` | ensembles |
| `build_production_ensemble_manifest.py` | `scripts/production/ensembles/build_production_ensemble_manifest.py` | ensembles |
| `build_recovery_budget_accounting.py` | `scripts/production/analysis/build_recovery_budget_accounting.py` | analysis |
| `build_sampling_3to6_diff.py` | `scripts/production/ensembles/build_sampling_3to6_diff.py` | ensembles |
| `build_sampling_audit_3to6.py` | `scripts/production/ensembles/build_sampling_audit_3to6.py` | ensembles |
| `build_sampling_ceiling_classification.py` | `scripts/production/ensembles/build_sampling_ceiling_classification.py` | ensembles |
| `build_second_search_preregistration.py` | `scripts/production/ensembles/build_second_search_preregistration.py` | ensembles |
| `build_state_identity_qc.py` | `scripts/production/validation/build_state_identity_qc.py` | validation |
| `build_strict_recovery_manifest.py` | `scripts/production/ensembles/build_strict_recovery_manifest.py` | ensembles |
| `build_strict_recovery_report.py` | `scripts/production/ensembles/build_strict_recovery_report.py` | ensembles |
| `build_tolerance_preregistration.py` | `scripts/production/ensembles/build_tolerance_preregistration.py` | ensembles |
| `build_torsion_probe_package.py` | `scripts/production/ensembles/build_torsion_probe_package.py` | ensembles |
| `build_torsion_registry.py` | `scripts/production/validation/build_torsion_registry.py` | validation |
| `build_wp2_closure.py` | `scripts/production/analysis/build_wp2_closure.py` | analysis |
| `build_wp2_cost_scenarios.py` | `scripts/production/analysis/build_wp2_cost_scenarios.py` | analysis |
| `build_wp2_ensemble_free_energies.py` | `scripts/production/ensembles/build_wp2_ensemble_free_energies.py` | ensembles |
| `build_wp2_sampling.py` | `scripts/production/ensembles/build_wp2_sampling.py` | ensembles |
| `build_wp5_target_pool.py` | `scripts/production/analysis/build_wp5_target_pool.py` | analysis |
| `check_wp2_anchors.py` | `scripts/production/validation/check_wp2_anchors.py` | validation |
| `emit_pair_recheck.py` | `scripts/production/ingest/emit_pair_recheck.py` | ingest |
| `emit_wp1.py` | `scripts/production/ingest/emit_wp1.py` | ingest |
| `emit_wp2.py` | `scripts/production/ingest/emit_wp2.py` | ingest |
| `ensemble_hpc_io.py` | `scripts/production/jobs/ensemble_hpc_io.py` | jobs |
| `finalize_wp2.ps1` | `scripts/production/release/finalize_wp2.ps1` | release |
| `fold_anfreq_into_ledger.py` | `scripts/production/ingest/fold_anfreq_into_ledger.py` | ingest |
| `frontier_fmopop.py` | `scripts/production/validation/frontier_fmopop.py` | validation |
| `frontier_lowdin.py` | `scripts/production/validation/frontier_lowdin.py` | validation |
| `frontier_spin_qc.py` | `scripts/production/validation/frontier_spin_qc.py` | validation |
| `import_ensemble_structures.py` | `scripts/production/ingest/import_ensemble_structures.py` | ingest |
| `import_hpc_numfreq.py` | `scripts/production/ingest/import_hpc_numfreq.py` | ingest |
| `import_hpc_opt_numfreq.py` | `scripts/production/ingest/import_hpc_opt_numfreq.py` | ingest |
| `make_commit_msg.py` | `scripts/production/jobs/make_commit_msg.py` | jobs |
| `make_physics_completion_figures.py` | `scripts/production/release/make_physics_completion_figures.py` | release |
| `member_next_action.py` | `scripts/production/validation/member_next_action.py` | validation |
| `orca_derivative_policy.py` | `scripts/production/validation/orca_derivative_policy.py` | validation |
| `prepare_hpc_main_remaining.py` | `scripts/production/jobs/prepare_hpc_main_remaining.py` | jobs |
| `probe_route.py` | `scripts/production/validation/probe_route.py` | validation |
| `provenance_hash.py` | `scripts/production/validation/provenance_hash.py` | validation |
| `refreeze_manifest.py` | `scripts/production/release/refreeze_manifest.py` | release |
| `reopt_saddle.py` | `scripts/production/jobs/reopt_saddle.py` | jobs |
| `run_batch.py` | `scripts/production/jobs/run_batch.py` | jobs |
| `run_li_motif_round2.py` | `scripts/production/ensembles/run_li_motif_round2.py` | ensembles |
| `run_method_audit.py` | `scripts/production/jobs/run_method_audit.py` | jobs |
| `run_pair_recheck.py` | `scripts/production/jobs/run_pair_recheck.py` | jobs |
| `run_second_search_emc.py` | `scripts/production/ensembles/run_second_search_emc.py` | ensembles |
| `run_strict_recovery_search.py` | `scripts/production/ensembles/run_strict_recovery_search.py` | ensembles |
| `run_to_closure.py` | `scripts/production/jobs/run_to_closure.py` | jobs |
| `run_wp2_extra.py` | `scripts/production/jobs/run_wp2_extra.py` | jobs |
| `run_wp2_production.py` | `scripts/production/jobs/run_wp2_production.py` | jobs |
| `run_wp2_queue.py` | `scripts/production/jobs/run_wp2_queue.py` | jobs |
| `run_wp5_AB_replay.py` | `scripts/production/analysis/run_wp5_AB_replay.py` | analysis |
| `run_wp5_blind_replay.py` | `scripts/production/analysis/run_wp5_blind_replay.py` | analysis |
| `screen_li_motifs.py` | `scripts/production/ensembles/screen_li_motifs.py` | ensembles |
| `strict_readiness.py` | `scripts/production/validation/strict_readiness.py` | validation |
| `strict_readiness_wiring.py` | `scripts/production/validation/strict_readiness_wiring.py` | validation |
| `submit_hpc_batch.py` | `scripts/production/jobs/submit_hpc_batch.py` | jobs |
| `supervise_pending.ps1` | `scripts/production/jobs/supervise_pending.ps1` | jobs |
| `supervisor_policy.py` | `scripts/production/jobs/supervisor_policy.py` | jobs |
| `verify_archive.py` | `scripts/production/release/verify_archive.py` | release |
| `watch_smpd.ps1` | `scripts/production/jobs/watch_smpd.ps1` | jobs |
| `watch_supervisor.ps1` | `scripts/production/jobs/watch_supervisor.ps1` | jobs |
| `wp2_progress.py` | `scripts/production/validation/wp2_progress.py` | validation |
| `wp5_formal_models.py` | `scripts/production/analysis/wp5_formal_models.py` | analysis |
| `wp5_replay_contract.py` | `scripts/production/analysis/wp5_replay_contract.py` | analysis |
