# 方案合规台账（derived）

> 由 `scripts/wp_production/build_plan_compliance.py` 从 `outputs/physics_completion/**`、`outputs/week7/`、`data/references/anchor_primary_audit.csv`
> 只读现算；本文件不写死任何状态或数字，生产腿每落地一批重跑即更新。

| item_id | 方案节 | 要求 | 状态 | 实测 | 证据 |
| --- | --- | --- | --- | --- | --- |
| `wp0_definition_migration` | §4 WP0 定义迁移与历史结论同步 | 量名/方向/状态身份迁移表与历史结论同步（Q3/Q7/Q10/R15/P1a）落盘 | satisfied | quantities=7 claims=5 config=True protocol=True | config/physics_completion_v1.yaml; docs/physics_completion_protocol.md; docs/claim_migration.md; outputs/physics_completion/definition/ |
| `wp1_method_audit_matrix` | §5 WP1 独立方法审计 | 最小作业矩阵：方法集 8 分子 x 4 状态 x 4 设定 = 128 单点实测 | satisfied | computed=128 total=128 | outputs/physics_completion/method_audit/job_matrix.csv |
| `wp1_reduction_state_checks` | §5 WP1 独立方法审计 | 还原态三项检查：电子空间扩展 / 脱附稳定性 / 波函数身份 | not_satisfied | audited_states=LiM_2plus,LiM_plus,M,M_plus has_reduced_leg=False | outputs/physics_completion/method_audit/job_matrix.csv; docs/59_week38_wp1_method_audit.md |
| `wp1_unique_production_method` | §5 WP1 独立方法审计 | 冻结唯一生产方法（不按哪个方法翻出更多翻转来选） | satisfied | production_candidates=omegaB97X-D4 | outputs/physics_completion/method_audit/method_settings.csv; docs/59_week38_wp1_method_audit.md |
| `wp2_production_state_ledger` | §6 WP2 固定背景配对自由能标签 | 四分子 x 四主态（另加基组一致中性腿）的真实 Opt+NumFreq 登记 | blocked_on_production | produced=12 total=20 molecules=4 | outputs/physics_completion/closure/four_molecule_state_closure.csv |
| `wp2_four_state_complete` | §6 WP2 固定背景配对自由能标签 | 四态齐备分子：M / M+ / [LiM]+ / [LiM]2+ 全部产出 | blocked_on_production | M/M+/LiM+/LiM2+=1/4; 再加基组一致中性腿=0/4; Li 成对齐备=1/4 | outputs/physics_completion/closure/four_molecule_state_closure.csv |
| `wp2_free_redox_labels` | §6 WP2 固定背景配对自由能标签 | 绝热电子能差 + 单构象自由能差（两腿同为 def2-TZVPD 才相减） | partial | free_status_computed=1/4; li_status_computed=0/4 | outputs/physics_completion/free_states/production_redox.csv |
| `wp2_li_legs` | §6 WP2 固定背景配对自由能标签 | Li 条件态（[LiM]+ / [LiM]2+）：E 与 G 两种配位位移 | blocked_on_production | li_legs_produced=3/8; li_status_computed=0/4 | outputs/physics_completion/closure/four_molecule_state_closure.csv; outputs/physics_completion/free_states/production_redox.csv |
| `wp2_conformer_ensemble` | §6 WP2 固定背景配对自由能标签 | 同态构象系综自由能 G_ens（最多 3 个再 6 个独立结构） | not_satisfied | distinct_n_conformers=1 | outputs/physics_completion/closure/four_molecule_state_closure.csv |
| `wp2_sampling_extension` | §6 WP2 固定背景配对自由能标签 | 采样审计集 3 -> 6 结构比较与 sampling_limited 判定 | satisfied | acceptance_ok=9/9 | outputs/physics_completion/sampling/sampling_acceptance.csv |
| `wp2_closure_acceptance` | §6 WP2 固定背景配对自由能标签 | 闭环表自检：不造数 / 未完成显式登记 / 几何与频率 QC | satisfied | closure_checks_ok=8/8 | outputs/physics_completion/closure/closure_acceptance.csv |
| `wp2_flip_persistence` | §6 WP2 固定背景配对自由能标签 | EMC-GBL / EMC-SL 两对翻转能否保留到自由能层 | partial | rungs_computed=4/10 | outputs/physics_completion/closure/flip_persistence.csv |
| `wp3_pair_evidence` | §7 WP3 排序、独立 uncertainty 与机制 | 固定模型下的保守符号一致性：STABLE / UNRESOLVED / ROBUST_INVERSION | partial | pairs=66; ROBUST_INVERSION=2; STABLE=55; UNRESOLVED=9 | outputs/physics_completion/pair_evidence/pair_evidence.csv |
| `wp3_rung_ladder_topk_regret` | §7 WP3 排序、独立 uncertainty 与机制 | 逐级报告固定 k=3（辅助 2/4）的 Top-k overlap 与 selection regret | satisfied | ladder_rows=10 has_selection_regret=True has_top_k=True | outputs/physics_completion/pair_evidence/frozen_rung_ladder.csv |
| `wp3_targeted_second_method` | §7 WP3 排序、独立 uncertainty 与机制 | 关键 pair 第二泛函靶向复核（只对新优化几何的单点） | partial | plan=24 ready=14 blocked=10 results=14 | outputs/physics_completion/pair_evidence/targeted_recheck/ |
| `wp3_mechanism_cases` | §7 WP3 排序、独立 uncertainty 与机制 | 机制案例最多 3 个，事先规则选定 | satisfied | cases=2 | outputs/physics_completion/pair_evidence/mechanism_cases.csv |
| `wp4_anchor_tiers` | §8 WP4 外部锚点复核与可比性审计 | 既有氧化锚点逐条复核并分三级（可定量 / 仅趋势 / 不可用） | partial | anchor_rows=87 tier_1=0 tier_2=14 tier_3=73 | data/references/anchor_primary_audit.csv |
| `wp4_primary_text_check` | §8 WP4 外部锚点复核与可比性审计 | 回原始文献页码/表号复核（而非二级转抄） | partial | transcription_only=14/87 | data/anchors/primary_source_verification.csv; docs/62_week41_wp4_anchor_comparability.md |
| `wp4_new_comparable_entries` | §8 WP4 外部锚点复核与可比性审计 | 按明确检索协议再找 6-10 条条件可比条目 | not_satisfied | tier_1_condition_matched=0 | outputs/physics_completion/anchor/anchor_tier_summary.csv |
| `wp5_task_separation` | §9 WP5 delta-learning 与成本感知主动查询 | 任务 A（预测 free Gox）与任务 B（预测配位位移）分开，C 特征集不出现 X2 | satisfied | ml_rows=48 budget_rows=24 | outputs/physics_completion/ml/; outputs/physics_completion/active_learning/ |
| `wp5_new_endpoint_in_budget` | §9 WP5 delta-learning 与成本感知主动查询 | 新端点 O_3>=2/3 且 R_3<=0.10 eV 真的用于算预算 | not_satisfied | budget_columns=axis,baseline,median_overstates_majority,n_t_majority_combined,n_t_majority_tau080,n_t_median_tau080,regret_tolerance_ev,task; regret_tolerance_ev=0.041270500000000016,0.08099575000000002,0.11163849999999997,0.1619,0.16414650000000003,0.22725399999999998 | outputs/physics_completion/active_learning/success_budget.csv |
| `wp5_two_consecutive_points` | §9 WP5 delta-learning 与成本感知主动查询 | 至少 16/20 回放在两个连续预算点达标才报经验停止预算；12 标签池回放 | not_satisfied | budget_table_has_consecutive_rule=False; replay_pool=legacy_18_not_blind | src/electrolyte_ranking/wp6.py; outputs/week7/stage8_al_summary.md |
| `wp5_absolute_cost_ledger` | §11 停止规则 | 绝对成本三项：cpu_core_hours / p90_job_cost / frequency_only_cost | partial | cost_rows=10 MISSING=3 | outputs/physics_completion/cost/cost_ledger.csv |
| `wp6_explicit_ligand` | §10 WP6 显式配体检查（可选） | 可选 WP6：固定 R=DME 的共同背景显式配体检查 | satisfied | plan_rows=4 executed_jobs=0 | outputs/physics_completion/explicit_ligand/explicit_ligand_plan.csv |
| `stop_rules_registered` | §11 停止规则 | 停止规则（unresolved / sampling_limited / identity outcome / validation limitation） | partial | stop_rules_in_config=True; li_motif_screen_computed=0/8 | config/physics_completion_v1.yaml; docs/physics_completion_protocol.md |
| `plan_overall_complete` | §1 研究问题与最终交付 | 方案第 1-5 步闭环：四分子四态齐备 + 两对翻转在自由能层判定 | blocked_on_production | four_state_complete=1/4 li_pair_complete=1/4 flip_rungs=4/10 | outputs/physics_completion/closure/four_molecule_state_closure.csv; outputs/physics_completion/closure/flip_persistence.csv |

**状态合计**：satisfied=9; partial=8; not_satisfied=5; blocked_on_production=4

**总体判定**：未闭环 -- 见 `plan_overall_complete` 行
