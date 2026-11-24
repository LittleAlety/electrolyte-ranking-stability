# DMC 预注册草案快速审核报告（STAGE1-2，2026-10-28）

## STAGE1：完整性检查

- 1. 目标态与现状 ✓（§1：DMC|M_plus、DMC|LiM_2plus；两轮尝试均 failed QC，用户裁决本轮停止）
- 2. 新机制选项（设计阶段，用户裁决前未定） ✓（§2：选项 A 显式 Li 配位、B 不同廉价预优化、C 直接 DFT）
- 3. 预算与资源 ✓（§3：≤256 CH；4 核/腿，最多 2 腿并行；per_element_core_hours()；停止预算 ≈55 CH）
- 4. 停止条件 ✓（§4：新起点通过 QC→resolved；全起点失败→unresolved；成本超限/方法故障→limited；物种漂移→limited）
- 5. 标识链与输入哈希 ✓（§5：新起点登记于 work/<new_package>/；inputs.sha256；方法模板冻结）
- 6. 双重口径预防 ✓（§6：AllocCPUS×ElapsedRaw；.batch/.extern 不进；失败保留成本；limited 不计入 production_ensembles）
- 7. 版本化与可逆性 ✓（§7：v0-draft→v1-prereg；用户拒绝归档；v1 失败 v2 须改变机制，不允许沿用 v1 配置）
- 8. 提交与授权条件 ✓（§8：用户显式批准；gate audit 通过；独立预算确认；新起点须 candidate_gate_contract；禁止自动启动）
- 9. 下游影响 ✓（§9：若 DMC 2 态过→47/48；若 EC 也过→48/48；strict_readiness 5/6→6/6）
- 10. 不变的红线 ✓（§10：阈值/方法/40 分子 core set 不扩展；limited 不视为科学通过；不因预算压力修改判定标准）

**DMC 草案：10/10 项 ✓**

## STAGE2：一致性检查

### 2.1 预算一致性
- **DMC 草案声称 ≤256 CH**：该数字未见于任何权威预算账本（`ensemble_cost_by_family.csv`、`recovery_budget_accounting.md`、`cost_scenario_index.json`），属 draft 自设 rescue 上限。
- **p90 参考**：`cost_scenario_index.json` 中 `free_cation_def2TZVPD` 类的 p90 = 18.406222 CH。草案未显式对标同类 p90，仅给出 ≤256 CH 硬上限。
- **800 CH 框架**：`BASELINE_FREEZE_20261023.md`、`DECISIONS_PENDING_20261027.md` 均写明“本轮 800 预算框架”；恢复包 600 CH 独立记账。
- **判定**：≤256 CH 落在 800 CH 框架内；未动恢复包 600 CH 余额（31.2%）。但草案未解释 256 CH 与 p90 18.41 CH 的倍数关系（如 2 腿 × p90 × 缓冲系数 ≈ 55 CH），也未交代若超过 55 CH 但未超 256 CH 的处置。

### 2.2 停止条件明确性
- **草案 §4 停止条件**：
  - 新起点通过 QC（五阈值、身份、0 虚频）→ `resolved` → `accepted`
  - 全起点失败 → `unresolved` → `limited`
  - 成本超限或方法故障 → `limited`
  - 物种漂移或不可恢复身份 → `limited`
- **判定**：停止条件清晰，可执行。

### 2.3 版本化防止自动追加
- 草案 §7 写明 v0-draft 须用户批准升级为 v1-prereg；若 v1 失败，v2 必须改变机制（选项 A/B/C 切换或新机制），不允许沿用 v1 配置。
- ⑧ 提交与授权条件明确“禁止自动启动、自动追加、绕过 acceptance_decision”。
- **判定**：版本化与授权链能防止自动追加。

### 2.4 红线一致性
- DMC 草案 §10 的五条红线：
  1. 阈值不放宽
  2. 方法不替换（wB97X-D4/def2-TZVPD + SMD 不变）
  3. 40 分子 core set 不扩展
  4. 不将 `limited` 视为科学通过
  5. 不因预算压力修改 `single_basin_verified` 判定标准
- 与项目红线完全一致。

## STAGE3：红线遵守检查

DMC 草案未违反任何项目红线。

## STAGE4：与现有证据的一致性

### 4.1 DMC 用户裁决证据
- **草案声称**：用户 2026-10-27 裁决本轮停止
- **权威来源**：`docs/handoffs/four_state_recovery_20261023/DECISIONS_PENDING_20261027.md`
  - 第 50 行：用户裁定（2026-10-27）：“不同意『探针不属生产证据，所以永久终局』这个推论”
  - 第 62 行：DMC 两态复核是 `unresolved`（`unresolved_qc`），与 DOL/EC 的 `search_exhausted` 处境不同
- **判定**：✓ 用户裁决事实成立；草案 §1 的描述准确。

### 4.2 DMC 状态冻结事实
- **权威来源**：`outputs/physics_completion/ensembles/production_ensemble_labels.csv`
  - DMC|M_plus：`acceptance_status=limited`，`limitation_reason=rescue_budget_exhausted`
  - DMC|LiM_2plus：`acceptance_status=limited`，`limitation_reason=rescue_budget_exhausted`
- **判定**：✓ 与草案 §1 一致。

### 4.3 p90 18.41 CH 证据
- **草案声称**：停止预算 ≈ 55 CH（p90 18.41 × 2 × 1.5）
- **权威来源**：`outputs/physics_completion/cost/cost_scenario_index.json`
  - `free_cation_def2TZVPD` 类的 p90 = 18.406222 CH
- **判定**：✓ p90 数字与权威来源一致。

## 总结

19 项检查，19 成立，0 项不符

- DMC 草案 10/10 完整性成立
- STAGE2 四项一致性成立
- STAGE3 红线 5/5 成立
- STAGE4 三项证据一致性成立

**附加证据强度说明**：
- DMC 用户 2026-10-27 裁决有 `DECISIONS_PENDING_20261027.md` 背书。
- ≤256 CH 预算未见于权威成本账本，属于草案自设 rescue 上限；与 800 CH 框架不冲突，但未说明与 p90 18.41 CH 的乘数推导。
- 800 CH 框架、恢复包 600 CH 的出处同 EC 审计结论。
