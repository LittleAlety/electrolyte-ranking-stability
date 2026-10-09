# `scripts/` —— 入口脚本布局与索引

本目录放**可执行的入口脚本**（CLI 与批次生成器）；可复用的库代码在 `src/electrolyte_ranking/`。
分工不要混：`src/` 放被 `import` 的纯逻辑，`scripts/` 放「读仓库产物 → 校验 → 写产物」的入口。

## 目录约定

| 位置 | 放什么 |
| --- | --- |
| `scripts/*.py` | 历史各周（week1–week36）的分析 / 生成入口，以及仍被测试或门禁直接调用的全局入口。**不要为“好看”把历史脚本搬走**：`outputs/**` 的冻结产物里记录了它们的路径，移动会断掉可追溯性。 |
| `scripts/wp_production/` | 当前批次 **physics_completion_v1（WP0–WP6）的完整流水线**：生产驱动 + 生成器 emit + 各派生层 + 一键收口。见 `scripts/wp_production/README.md`，一键收口入口是 `scripts/wp_production/finalize_wp2.ps1` |
| `scripts/wp_production/wp1_audit_src.txt` / `wp1_newsrc.py` | WP1 方法审计的补丁源（由 `emit_wp1.py` 折进生成器） |
| `work/`（不跟踪） | 原始 ORCA / xTB 输出、生成器基线缓存、临时脚本 |
| `docs/65_repo_layout.md` | **仓库骨架图**（顶层目录职责、阶段编号 ↔ WP 对应、收口链、冻结与不可改清单）；由 `tests/test_repo_layout.py` 强制覆盖，骨架漂了就会测试失败 |

## 新增脚本的落点规则

1. 属于当前批次流水线 → 放 `scripts/wp_production/`，并在该目录 README 的脚本表里登记；
2. 全局门禁 / 交付入口（被 `tests/` 或 `freeze_gates.py` 直接调用）→ 留在 `scripts/` 顶层，并在下面的索引里归到「门禁 / 交付入口」；
3. 一次性历史分析 → 也放 `scripts/` 顶层，命名沿用 `analyze_*`（分析）、`build_week*`（出交付）、`run_*`（跑计算/驱动）；
4. 脚本只能用 `Path(__file__).resolve().parents[N]` 定位仓库根：顶层脚本 `N = 1`，`scripts/wp_production/` 内脚本 `N = 2`；
5. **新增顶层入口后必须在下面的索引里登记**：`tests/test_scripts_index.py` 会断言每个顶层
   `scripts/*.py`、`*.ps1` 都出现在本文件里。不登记就会测试失败，防止顶层再漂新脚本。

## 入口脚本索引（由 `tests/test_scripts_index.py` 强制覆盖）

共 **169** 个顶层入口（不含 `wp_production/`），按批次分组：

**门禁 / 交付入口（被 tests 或 freeze_gates 直接调用，必须保留在顶层）**（13）

- `analyze_r13_summary_figure.py`
- `audit_claim_scope.py`
- `audit_clean_room.py`
- `build_deliverables.py`
- `build_final_conclusions.py`
- `build_github_readme.py`
- `build_metadata.py`
- `build_physics_completion_batch.py`
- `build_terminal_site.py`
- `check_environment.py`
- `check_series_rel_ordering.py`
- `freeze_gates.py`
- `validate_anchors.py`

**周交付构建器（week24–week36）**（19）

- `build_week24_deliverables.py`
- `build_week25_deliverables.py`
- `build_week28_deliverables.py`
- `build_week28_evidence_table.py`
- `build_week29_deliverables.py`
- `build_week29_wp2_physics_response.py`
- `build_week30_deliverables.py`
- `build_week30_wp3_coordination_mechanism.py`
- `build_week31_deliverables.py`
- `build_week31_wp4_decision_identifiability.py`
- `build_week32_deliverables.py`
- `build_week32_wp5_delta_learning.py`
- `build_week33_deliverables.py`
- `build_week33_wp6_active_learning_budget.py`
- `build_week34_deliverables.py`
- `build_week34_wp7_external_reference_boundary.py`
- `build_week35_deliverables.py`
- `build_week35_paper_convergence.py`
- `build_week36_final_submission.py`

**周报文本生成（week15–week23）**（9）

- `gen_week15_report.py`
- `gen_week16_report.py`
- `gen_week17_report.py`
- `gen_week18_report.py`
- `gen_week19_report.py`
- `gen_week20_report.py`
- `gen_week21_report.py`
- `gen_week22_report.py`
- `gen_week23_report.py`

**阶段分析（stage6–stage21）**（19）

- `analyze_stage10_synthesis.py`
- `analyze_stage11_sigma_anatomy.py`
- `analyze_stage12_prescreen.py`
- `analyze_stage13_dielectric_limit.py`
- `analyze_stage14_outlier.py`
- `analyze_stage15_two_guess.py`
- `analyze_stage16_catalogue.py`
- `analyze_stage17_contamination.py`
- `analyze_stage17_solution_identity.py`
- `analyze_stage18_identity_census.py`
- `analyze_stage19_relax.py`
- `analyze_stage20_relax_rung.py`
- `analyze_stage20_xtb_arms.py`
- `analyze_stage21_path.py`
- `analyze_stage21_protocol.py`
- `analyze_stage21_refill.py`
- `analyze_stage21_shell_redox.py`
- `analyze_stage6.py`
- `analyze_stage9_microsolvation.py`

**week22–week25 专项分析**（14）

- `analyze_w22_allowance.py`
- `analyze_w22_broadpool.py`
- `analyze_w22_stats.py`
- `analyze_w24_al.py`
- `analyze_w24_alignment.py`
- `analyze_w24_audit.py`
- `analyze_w24_decision.py`
- `analyze_w24_loro.py`
- `analyze_w24_ml.py`
- `analyze_w25_figure_f52.py`
- `analyze_w25_figure_f53.py`
- `analyze_w25_figure_f55.py`
- `analyze_w25_gate1_oxidation.py`
- `analyze_w25_gate1_reduction.py`

**C1 / CPCM / sigma / p1-p2 专项分析**（11）

- `analyze_c1_coordination.py`
- `analyze_c1_state_identity.py`
- `analyze_cpcm_eps_scan.py`
- `analyze_delta_m.py`
- `analyze_dielectric_limit.py`
- `analyze_family_resolved.py`
- `analyze_neb_refinement.py`
- `analyze_p1_core_set.py`
- `analyze_p2_environment.py`
- `analyze_sigma_prospective.py`
- `analyze_sigma_synthetic.py`

**阶段生成（stage13–stage18）**（5）

- `build_stage13_ladder.py`
- `build_stage14_attribution.py`
- `build_stage15_diffuseness.py`
- `build_stage16_predictor.py`
- `build_stage18_selfdiagnosis.py`

**图表（make_*）**（25）

- `make_c1_figure.py`
- `make_c1_state_identity_figure.py`
- `make_eps_scan_figure.py`
- `make_stage10_figure.py`
- `make_stage11_figure.py`
- `make_stage12_figure.py`
- `make_stage13_figure.py`
- `make_stage14_figure.py`
- `make_stage15_figure.py`
- `make_stage16_figure.py`
- `make_stage17_figure.py`
- `make_stage18_figure.py`
- `make_stage19_figure.py`
- `make_stage20_figure.py`
- `make_stage21_figure.py`
- `make_stage23_figure.py`
- `make_stage24_figure.py`
- `make_stage6_figure.py`
- `make_stage7_figure.py`
- `make_stage9_figure.py`
- `make_summary_figures.py`
- `make_t2_figure.py`
- `make_t5_figure.py`
- `make_w24_flowchart.py`
- `make_w25_figure_f54_two_axis_hierarchy.py`

**计算 / 实验驱动（run_*）**（25）

- `run_broad_pool_p0.py`
- `run_c1_freq_check.py`
- `run_c1_li_coordination.py`
- `run_core_set_p1.py`
- `run_core_set_p2.py`
- `run_diffuse_control.py`
- `run_method_audit_xtb.py`
- `run_orca_job.py`
- `run_p1a_adiabatic.py`
- `run_shell3_xtb_sign_test.py`
- `run_stage14_dense_grid.py`
- `run_stage15_two_guess.py`
- `run_stage16_catalogue.py`
- `run_stage17_smd_moread.py`
- `run_stage19_relax.py`
- `run_stage20_xtb_arms.py`
- `run_stage21_path.py`
- `run_stage21_shell_redox.py`
- `run_stage7_ml.py`
- `run_stage8_al.py`
- `run_stage9_microsolvation.py`
- `run_t2_opt_freq.py`
- `run_t6_conformer_spread.py`
- `run_thermal_correction_sample.py`
- `run_xtb_job.py`

**审计（audit_*）**（7）

- `audit_estimator_circularity.py`
- `audit_layer_independence.py`
- `audit_metric_robustness.py`
- `audit_p1_core_set.py`
- `audit_selection_multiplicity.py`
- `audit_solution_anchors.py`
- `audit_w24_gate1_literature.py`

**锚点 / 文献核对**（3）

- `ingest_gate1_anchor_series.py`
- `scan_stage15_anchor_literature.py`
- `verify_w24_gate1_refs.py`

**其他构建器（build_*）**（6）

- `build_compute_budget_ledger.py`
- `build_conformers.py`
- `build_core_set_metadata_ext.py`
- `build_li_motifs.py`
- `build_microsolvation_shells.py`
- `build_ml_features.py`

**环境 / 工具 / 其他入口**（13）

- `activate_toolchain.ps1`
- `check_sigma_boundary_resolution.py`
- `classify_state_identity.py`
- `compare_vertical_adiabatic.py`
- `decision_state_report.py`
- `docx2pdf.ps1`
- `gate1_dual_track_report.py`
- `orca_energy_ledger.py`
- `paper_v7_patch_content.py`
- `paper_v7_restructure_results.py`
- `plan_targeted_two_guess.py`
- `report_orca_pilot.py`
- `setup_orca.ps1`

## 一个重要约束

`outputs/**` 是**生成物**。改动量名、阈值、措辞或路径时，要改生成脚本，然后跑

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\wp_production\finalize_wp2.ps1
```

让产物、交付镜像、站点、冻结门与测试一起收敛；直接手改 `outputs/**` 会在下一次 `--check` 失败。
`scripts/build_physics_completion_batch.py` 本身也是**派生物**（由 `emit_wp2.py` 从 git 历史基线 + 补丁块确定性重打），手工改会被覆盖。
