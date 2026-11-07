# `scripts/production/SCRIPT_INDEX.md` —— 逐脚本索引（生成物）

> 本文件由 `scripts/production/build_script_index.py` 生成，**不要手改**；
> `python scripts/production/build_script_index.py --check` 复核它与磁盘一致。
> 手写说明（导数政策 / 一键收口 / 队列纪律）在 `scripts/production/README.md`；
> 逐脚本的详细职责与输入→输出见 `docs/65_repo_layout.md` §3.1。

六类职责（一个文件只属于一类）：

| 目录 | 职责 |
| --- | --- |
| `jobs/` | 任务准备、提交、监守、队列（会起算或驱动作业） |
| `ingest/` | HPC 结果回收与导入（只读校验 + 非覆盖写入账本） |
| `validation/` | QC、身份、来源与证据门（判定，不产出科学数值） |
| `ensembles/` | 候选、覆盖、去重、恢复、采样（系综与恢复链） |
| `analysis/` | 排序、学习、成本、合规（派生分析层） |
| `release/` | 产物生成、镜像、归档、收口（交付面） |

公共入口：

| 入口 | 用途 |
| --- | --- |
| `jobs/run_wp2_queue.py` | 生产队列：查状态、断点续跑、并发上限 |
| `ingest/import_hpc_opt_numfreq.py` | 超算 Opt+NumFreq 结果回收与导入 |
| `validation/strict_readiness_wiring.py` | 逐项严格总闸门的证据推导 |
| `ensembles/build_production_ensemble_aggregator.py` | 生产系综聚合（权重 / 去重 / 三态标签） |
| `analysis/build_plan_compliance.py` | 方案逐条合规台账 |
| `release/finalize_wp2.ps1` | 一键收口链 |

历史路径 `scripts/wp_production/<name>.py` 仍然存在，但只是转发到这里的兼容入口，
见 `scripts/wp_production/README.md`。


## `jobs/`（16 个文件）

| 文件 | 一句话职责 |
| --- | --- |
| `ensemble_hpc_io.py` | Verified immutable ensemble snapshots through the WHU command bridge only. |
| `make_commit_msg.py` | 按当前已落地的 WP2 生产子集生成提交信息（供 finalize_wp2.ps1 使用）。 |
| `prepare_hpc_main_remaining.py` | Prepare missing WP2 legs without running or submitting any computation. |
| `reopt_saddle.py` | Re-optimise a converged-but-saddle WP2 leg off its imaginary mode. |
| `run_batch.py` | Pilot expansion (plan 15.5/15.6) - 12 main-set molecules x 4 master states. |
| `run_method_audit.py` | WP1 method audit - 8 method-set molecules x 4 states x 4 settings (128 single points) |
| `run_pair_recheck.py` | 方案 5.3 / 11 的关键 pair 第二泛函靶向复核 —— 执行器。 |
| `run_to_closure.py` | — |
| `run_wp2_extra.py` | WP2 生产扩展驱动：中性腿的 def2-TZVPD 版本（与阳离子/Li 腿基组一致）。 |
| `run_wp2_production.py` | WP2 生产驱动：主集分子 × 4 主状态的 SMD Opt+NumFreq+SP 与 G 账本行。 |
| `run_wp2_queue.py` | WP2 主集生产队列：可断点续跑、并发上限 3 个 ORCA 作业。 |
| `submit_hpc_batch.py` | Capacity-gated, idempotent submission through the protected WHU HPC bridge. |
| `supervise_pending.ps1` | — |
| `supervisor_policy.py` | — |
| `watch_smpd.ps1` | — |
| `watch_supervisor.ps1` | — |

## `ingest/`（8 个文件）

| 文件 | 一句话职责 |
| --- | --- |
| `emit_pair_recheck.py` | 把靶向复核的**原始单点结果**折成可提交的登记表（手工折步，仓库外 work/ -> 交付层）。 |
| `emit_wp1.py` | 收口七：把本机独立方法审计折进主生成器（一次性补丁）。 |
| `emit_wp2.py` | 把 WP2 生产首段（work/wp2prod 下已完成的分子 x 主态账本 JSON）折进生成器。 |
| `fold_anfreq_into_ledger.py` | — |
| `import_ensemble_structures.py` | — |
| `import_hpc_numfreq.py` | Validate HPC frequency results before opt-in, non-overwriting ledger import. |
| `import_hpc_opt_numfreq.py` | Validate and import a SELF-CONTAINED HPC Opt+NumFreq leg. |
| `wp1_audit_src.txt` | — |

## `validation/`（17 个文件）

| 文件 | 一句话职责 |
| --- | --- |
| `build_frontier_identity_evidence.py` | Identity evidence-chain assembly (plan v3.1 item 2): pending -> verified. |
| `build_frontier_legs.py` | Frontier-localization legs: fixed-geometry single points with Molden output. |
| `build_frontier_localization.py` | Frontier-orbital composition analysis (the step AFTER the single points). |
| `build_probe_routes.py` | Derive the five limited states' probe_route inputs and emit the real routes. |
| `build_state_identity_qc.py` | — |
| `build_torsion_registry.py` | Torsion-freedom registry for the five limited states (v3.1 item 4 preflight). |
| `check_wp2_anchors.py` | — |
| `frontier_fmopop.py` | Parse ORCA 6.1 ``! FMOPop`` output into per-atom frontier populations. |
| `frontier_lowdin.py` | Löwdin orthogonalised atomic weights for the frontier analysis. |
| `frontier_spin_qc.py` | Per-spin frontier populations + the three QC statuses (plan v3.1 items 1-2). |
| `member_next_action.py` | Next-action dispositions for ensemble members: the frozen decision contract. |
| `orca_derivative_policy.py` | Machine-enforced ORCA derivative policy for WP2 production inputs. |
| `probe_route.py` | Per-state probe routing for the five limited states (plan v3.1 item 4). |
| `provenance_hash.py` | Explicit provenance-hash contract: text artifacts are LF-normalised. |
| `strict_readiness.py` | Strict readiness: the final gate must inspect ALL evidence, not count labels. |
| `strict_readiness_wiring.py` | Derive the strict_readiness evidence flags from real artifacts on disk. |
| `wp2_progress.py` | — |

## `ensembles/`（21 个文件）

| 文件 | 一句话职责 |
| --- | --- |
| `build_bgroup_pilot_preregistration.py` | B-group pilot preregistration: production-level coverage diagnosis for AN/DMC M_plus. |
| `build_coverage_reviews.py` | Coverage reviews: the honest way a `limited` state may become `accepted`. |
| `build_li_motif_plan_round2.py` | — |
| `build_li_motif_sampling_plan.py` | — |
| `build_p4_screening_adjudication.py` | P4 xTB screening adjudicator: element-level facts -> frozen-window verdict. |
| `build_production_ensemble_aggregator.py` | — |
| `build_production_ensemble_manifest.py` | — |
| `build_sampling_3to6_diff.py` | — |
| `build_sampling_audit_3to6.py` | — |
| `build_sampling_ceiling_classification.py` | Sampling-audit ceiling classification (plan item ⑤, evidence side only). |
| `build_second_search_preregistration.py` | Second-round search preregistration for the states this batch cannot recover. |
| `build_strict_recovery_manifest.py` | strict_recovery_v1: the frozen recovery-batch manifest (registration only). |
| `build_strict_recovery_report.py` | Per-batch outcome report for strict_recovery_v1. |
| `build_tolerance_preregistration.py` | Sampling-stability tolerance: the PRE-REGISTRATION DRAFT (no number chosen). |
| `build_torsion_probe_package.py` | Torsion-probe preregistration + package build for the 4 authorised states. |
| `build_wp2_ensemble_free_energies.py` | — |
| `build_wp2_sampling.py` | — |
| `run_li_motif_round2.py` | — |
| `run_second_search_emc.py` | Second-round search for EMC\|M_plus under a REGISTERED method change. |
| `run_strict_recovery_search.py` | strict_recovery_v1 independent basin search (local GFN2 screen). |
| `screen_li_motifs.py` | — |

## `analysis/`（16 个文件）

| 文件 | 一句话职责 |
| --- | --- |
| `build_anchor_condition_audit.py` | — |
| `build_compute_provenance.py` | — |
| `build_d6_preregistration_draft.py` | D6 deliverable: the preregistration DRAFT for the four ranking-sensitive |
| `build_descriptor_analysis.py` | — |
| `build_ensemble_cost_by_family.py` | One cost ledger, unique job identity, basis vs full-label acquisition. |
| `build_gap_decision_support.py` | Decision support for the ensemble states not accepted yet (at most 14). |
| `build_pair_recheck_plan.py` | — |
| `build_plan_compliance.py` | — |
| `build_recovery_budget_accounting.py` | Recovery-budget accounting and terminal-state report (plan: 资源安排条款). |
| `build_wp2_closure.py` | — |
| `build_wp2_cost_scenarios.py` | — |
| `build_wp5_target_pool.py` | WP5 tasks A/B: the 12-molecule QC-labelled target pools (v2 input contract). |
| `run_wp5_AB_replay.py` | WP5 tasks A/B: the blind replay on the 12-molecule QC-labelled pools. |
| `run_wp5_blind_replay.py` | WP5 candidate-level blind replay: the honest O_3 / R_3 data chain. |
| `wp5_formal_models.py` | Frozen formal predictors for the WP5 A/B replay (plan v3.1 item 5). |
| `wp5_replay_contract.py` | Paired-seed and stop-budget helpers for the WP5 blind replay v2. |

## `release/`（6 个文件）

| 文件 | 一句话职责 |
| --- | --- |
| `archive_raw_outputs.py` | 把 provenance 里登记的原始作业文件打成**独立可复核的 zip 归档**。 |
| `build_physics_completion_deliverables.py` | — |
| `finalize_wp2.ps1` | — |
| `make_physics_completion_figures.py` | physics_completion_v1 main figures F59-F64 (plan section 14). |
| `refreeze_manifest.py` | Re-freeze a frozen provenance manifest under the explicit hash contract. |
| `verify_archive.py` | — |
