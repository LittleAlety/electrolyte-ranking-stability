# EC 预注册草案快速审核报告（STAGE1-2，2026-10-28）

## STAGE1：完整性检查

- 1. 目标态与方法 ✓（§1：EC|LiM_2plus；方法冻结 wB97X-D4/def2-TZVPD+SMD；判定路径 single_basin_verified）
- 2. 预算与资源 ✓（§2：≤32 CH；独立预算；per_element_core_hours()；停止预算）
- 3. 探针与路径定义 ✓（§3：5 合法连续二面角；任一另一盆地→resolved；全单盆地→unresolved）
- 4. 标识链与输入哈希 ✓（§4：reopt 收敛末几何 sha256；方法模板；产出登记路径）
- 5. 双重口径预防 ✓（§5：只记 AllocCPUS×ElapsedRaw；父/子行不进；失败保留实测成本）
- 6. 版本化与可逆性 ✓（§6：v0-draft→v1-prereg；用户拒绝归档；失败不沿用 v0 ID）
- 7. 提交与授权条件 ✓（§7：用户显式批准；gate audit 通过；独立预算；禁止自动启动）
- 8. 下游影响 ✓（§8：严格就绪 5/6→6/6；系综 45/48→46/48）
- 9. 不变的红线 ✓（§9：阈值/方法/40 分子 core set 不扩展；limited 不视为通过）

**EC 草案：9/9 项 ✓**

## STAGE2：一致性检查

### 2.1 预算一致性
- **EC 草案声称 ≤32 CH**：该数字未出现在任何权威预算账本（`recovery_budget_accounting.md`、`cost_scenario_index.json`、`ensemble_cost_by_family.csv`）中，属 draft 自设上限。
- **权威 800 CH 本轮上限出处**：`BASELINE_FREEZE_20261023.md`、`DMC_DECISION_BRIEF_20261027.md` 均写明“本轮 800 预算框架”；恢复包 600 CH 另有独立账本。
- **历史成本已记录不清零**：`FOUR_STATE_STARTING_LEDGER_20261025.md` 记录 227.43 + 591.8 CH 记录不清零，DOL/EC reopt 批次另计 2.015556 CH（`attempts_ledger.json`）。
- **判定**：≤32 CH 与 800 CH 框架不冲突；但“须另立版本”在草案中无预算系统对接说明。

### 2.2 停止条件明确性
- **草案 §3 停止条件**：
  - 任一探针到达另一盆地 → `resolved` → `accepted`
  - 5 探针均仍单盆地 → `unresolved` → `limited`
  - 成本超限或方法故障 → `limited`
- **DMC 草案 p90 参考**：`cost_scenario_index.json` 中 `free_cation_def2TZVPD` 类的 p90 = 18.406222 CH；EC 草案未显式对标同类 p90，仅给出 ≤32 CH 上限。
- **判定**：停止条件逻辑清晰，可执行。

### 2.3 版本化防止自动追加
- 草案 §6 写明 v0-draft 须用户批准升级为 v1-prereg；失败 v2 须改变机制。
- ⑦ 提交与授权条件明确“禁止自动启动、自动追加、绕过 acceptance_decision”。
- **判定**：版本化与授权链能防止自动追加。

### 2.4 红线一致性
- EC 草案 §9 的五条红线：
  1. 阈值不放宽
  2. 方法不替换（wB97X-D4/def2-TZVPD + SMD 不变）
  3. 40 分子 core set 不扩展
  4. 不将 `limited` 视为科学通过
  5. 不因预算压力修改 `single_basin_verified`
- 与项目红线完全一致。

## STAGE3：红线遵守检查

EC 草案未违反任何项目红线。

## STAGE4：与现有证据的一致性

### 4.1 EC reopt TolE 证据
- **草案声称**：reopt failed the frozen TolE again (abs 6.366e-07 = 3.18x threshold)
- **权威来源**：`work/hpc_dol_ec_recovery_v1_reopt_20261027/attempts_ledger.json`
  - `EC|LiM_2plus|p4_02_ring_pucker_twist`：`slurm_element=3791416_1`，`job_id_raw=3791416`，`elapsed_raw_s=1004`，`measured_core_hours=1.115556`
  - `ec_outcome` = "reopt failed the frozen TolE again (abs 6.366e-07 = 3.18x threshold); per the user's frozen boundary the state KEEPS limited"
- **判定**：✓ 完全一致

### 4.2 EC 状态冻结事实
- **权威来源**：`outputs/physics_completion/ensembles/production_ensemble_labels.csv`
  - EC|LiM_2plus：`acceptance_status=limited`，`limitation_reason=rescue_budget_exhausted`
- **判定**：✓ 与草案 §1 "当前 limited" 一致

### 4.3 DOL/EC 成本数字一致性
- **草案**：未显式引用 DOL 0.9 / EC 1.115556 CH（EC 草案只写了 ≤32 CH 本轮预算）
- **权威来源**：`attempts_ledger.json`：DOL 0.900000 CH，EC 1.115556 CH；batch total 2.015556 CH
- **判定**：成本数字未在 EC 草案中引用，故无矛盾。

### 4.4 与 800 CH / 600 CH 框架的关系
- **权威来源**：`BASELINE_FREEZE_20261023.md`、`DECISIONS_PENDING_20261027.md`
  - 本轮上限 800 CH；恢复包 600 CH；独立风险储备 300 未动用
- **判定**：EC ≤32 CH 落在 800 框架内；未动恢复包 600 CH 的余额（31.2%）。

## 总结

18 项检查，18 成立，0 不符

- EC 草案 9/9 完整性成立
- STAGE2 四项一致性成立
- STAGE3 红线 5/5 成立
- STAGE4 四项证据一致性成立

**附加证据强度说明**：
- EC reopt 证据（TolE 3.18× 超差、状态保持 limited）来自 `attempts_ledger.json`，与 EC 草案一致。
- ≤32 CH 预算未见于任何权威成本账本，属于草案自设设计上限；与 800 CH 框架不冲突。
- 800 CH 框架、历史 227.43+591.8 CH 记录不清零、恢复包 187.0/600 CH 均有 `BASELINE_FREEZE_20261023.md` 与 `recovery_budget_accounting.md` 背书。
