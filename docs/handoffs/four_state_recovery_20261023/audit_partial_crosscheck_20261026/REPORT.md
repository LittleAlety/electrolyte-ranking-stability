# t4：复核 plan_compliance 中 partial/not_satisfied/blocked_on_production 项目（独立双查）

**任务**：复核 `partial-audit` 对合规未满足项的抽验（独立双查，不重做审计）。对照对象改为 `outputs/physics_completion/compliance/plan_compliance.csv` 中状态 ∈ {`partial`,`not_satisfied`,`blocked_on_production`} 的项目。

**时间**：2026-10-25  
**仓库根**：`E:\Claude Code\电解液溶剂-HB\电解液溶剂HB-Code`  
**原则**：只读、只写本目录、不改他人文件、不改生产产物、禁 commit、禁联网、禁计算

---

## 1. partial-audit 报告状态
- 路径：`docs/handoffs/four_state_recovery_20261023/audit_partial_items_20261026/REPORT.md`
- 实测大小：**6 B**（占位）
- 结论：始终未出现实质内容（>2KB）。**双查降级为独立建立 ground truth**。

---

## 2. 目标清单（独立盘点）
从 `plan_compliance.csv` 读取，状态符合条件共 **17 项**（CSV 实测）：`partial=13, not_satisfied=2, blocked_on_production=2`

清单：wp2_conformer_ensemble、wp2_sampling_extension、wp2_state_identity_qc、wp3_pair_evidence、wp3_targeted_second_method、wp3_mechanism_cases、wp5_new_endpoint_in_budget、wp5_formal_ab_stop_budget_reached、wp5_two_consecutive_points、wp5_absolute_cost_ledger、wp5_remaining_unqueried_error、wp5_pool_extension、stop_rules_registered、wp2_pilot_cost_fields、wp6_explicit_ligand、strict_readiness_evidence、plan_overall_complete

---

## 3. 独立 ground truth（同源现算）
- `ensembles/production_ensemble_labels.csv`（50 行）：`accepted=44, limited=4, provisional=0`
- `pair_evidence/pair_evidence.csv`（66 行）：`STABLE=55, UNRESOLVED=9, ROBUST_INVERSION=2`
- `active_learning/blind_replay/AB_axis_endpoint.csv`（32 行）：`computed=19, not_reached_within_pool=13`；`model_is: formal_frozen_predictor=24, baseline_not_formal=8`
- `li_motif_sampling/li_motif_screen.csv`（24 腿）：零 kept 仅 `{('AN','LiM_2plus')}` → `23/24`
- `li_motif_sampling/acceptance.csv`：13/13 ok
- `cost/pilot_cost_ledger.csv`（109 行）：memory 全部 MISSING，retry 全部 UNVERIFIABLE
- `cost/cost_ledger.csv`（10 行）：`measured:4, planned:3, MISSING:3`
- `pair_evidence/targeted_recheck`：plan/results 均 24
- `pair_evidence/mechanism_cases.csv`：两例六项中 3 项已具、3 项部分
- `state_identity/thresholds.json`：`frontier_localization.status=not_computed`
- `sampling_escalation.csv`（24 行）：全部 `registered_pending_round1_free_energy_check`
- `active_learning/round_diagnostics.csv`（296 行）：旧回放字段缺失标 MISSING 合理

---

## 4. 对照矩阵（合规声称 vs 独立复算）
所有 17 项均 **同意**。阻塞项（wp6_explicit_ligand、plan_overall_complete）与 not_satisfied（wp5_pool_extension、strict_readiness_evidence）的语义与当前实测相符，不应改为 satisfied。

**统计**：17/17 同意，0 分歧。

---

## 5. 附录 A（偏离目标的副产品，保留备用）
之前按采样审计建立的 ground truth 已降级为附录。发现旧口径与现产物不符（Li 腿执行情况等），相关证据链已记录，不影响本次主体结论。

---

**最终结论**：partial-audit 报告未实质交付，双查已降级为独立建立 ground truth。对 plan_compliance 17 项逐一独立复算，结论**完全一致**。本报告仅写入本目录，未改动他人文件或生产产物。
