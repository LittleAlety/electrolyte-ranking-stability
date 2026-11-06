# L00 接棒与归属（2026-10-29 自动快照）

- HEAD: `216a603744b5a7e2fe3d22a116919b4db81907fe`
- 工作树是否干净: **False**（已跟踪修改 11，未跟踪 24）
- 机器本地层 `work/` 存在: True（gitignored；干净克隆无此层）

## 已跟踪的未提交修改（不覆盖、不代提交）

- `ocs/assets/data.js`
- `docs/handoffs/four_state_recovery_20261023/DOL_EC_STAGE_REPORT_20261027.md`
- `docs/handoffs/wp5_formal_replay_guard_20261023/README.md`
- `docs/index.html`
- `outputs/physics_completion/compliance/plan_compliance.csv`
- `outputs/physics_completion/compliance/plan_compliance.md`
- `outputs/physics_completion/compliance/plan_compliance_meta.json`
- `scripts/wp_production/batch_cost_settlement.py`
- `scripts/wp_production/submit_hpc_batch.py`
- `tests/test_evidence_gate_and_cost.py`
- `计划.md`

## 未跟踪文件（并行会话或本轮产物）

- `docs/PLAN_INDEX.md`
- `docs/handoffs/four_state_recovery_20261023/DMC_PREREG_DRAFT_20261028.md`
- `docs/handoffs/four_state_recovery_20261023/DMC_PREREG_DRAFT_20261028_REVISED.md`
- `docs/handoffs/four_state_recovery_20261023/DMC_PREREG_DRAFT_20261028_REVISED_v2.md`
- `docs/handoffs/four_state_recovery_20261023/DMC_PREREG_DRAFT_20261028_REVISED_v3.md`
- `docs/handoffs/four_state_recovery_20261023/EC_PREREG_DRAFT_20261028.md`
- `docs/handoffs/four_state_recovery_20261023/EC_PREREG_DRAFT_20261028_REVISED.md`
- `docs/handoffs/four_state_recovery_20261023/EC_PREREG_DRAFT_20261028_REVISED_v2.md`
- `docs/handoffs/four_state_recovery_20261023/EC_PREREG_DRAFT_20261028_REVISED_v3.md`
- `docs/handoffs/four_state_recovery_20261023/audit_partial_crosscheck_20261026/STEP1_itemlist_p8copy.md`
- `docs/handoffs/four_state_recovery_20261023/audit_partial_crosscheck_20261026/STEP2_matrix_p8copy.md`
- `docs/handoffs/four_state_recovery_20261023/audit_partial_items_20261026/`
- `docs/handoffs/four_state_recovery_20261023/dmc_prereg_fast_audit/`
- `docs/handoffs/four_state_recovery_20261023/dmc_prereg_fast_audit_recheck/`
- `docs/handoffs/four_state_recovery_20261023/ec_prereg_fast_audit/`
- `docs/handoffs/four_state_recovery_20261023/prereg_audit_20261028/`
- `docs/handoffs/four_state_recovery_20261027_dol_log_audit/`
- `docs/handoffs/long_run_20261029/`
- `docs/handoffs/wp5_formal_replay_guard_20261023/REVIEW_20261026.md`
- `docs/handoffs/wp5_formal_replay_guard_20261023/probe_adversarial_20261026.py`
- `docs/handoffs/wp5_formal_replay_guard_20261023/probe_results_20261026.json`
- `docs/handoffs/wp5_formal_replay_guard_20261023/probe_stdout_20261026.txt`
- `docs/plans/`
- `tests/red_per_element_cost_swap.py`

## 授权范围（逐字转述，不扩张）

- EC 32 CH 属**提议**：预注册 v3 已就绪，未提交、未预算、未启动。
- DMC 本轮停止；新实验须先完成机制论证（§2.1 四问），不追加计算。
- 旧 800 CH / 600 CH / 剩余救援额度**不自动**成为新实验授权。
- 已有明确授权的事项（45/48 收口、身份单点、费用修复）不重复索要。

## 归属判定

- 本线（Lead）：程序、生成器、账本、派生产物、本轮新文档。
- 并行会话：`docs/`、`计划.md` 等在飞改动 —— 只读，不代提交。
- 判定方法：`git diff` 逐文件看内容，不按文件名猜。
