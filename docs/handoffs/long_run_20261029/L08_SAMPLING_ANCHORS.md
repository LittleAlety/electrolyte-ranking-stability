# L08 采样、外部锚点与后继门（2026-10-29，只读核对）

零新增计算、零触发。所有数字来自 `plan_compliance.csv` 的 `measured` 列与对应产物，生成器 `--check` 已全过（见 L06 同批）。

## 1. 3→6 采样升级：登记完成、执行未完成

| 证据 | 实测 |
|---|---|
| `wp2_sampling_extension` 状态 | **partial** |
| measured | `acceptance_ok=9/9; escalation_pending=24/24; executed=C01,C02,C03,C04,C05,C08,C09,C13,C14,C15,C16,C17; designated=C02,C03,C08,C17` |
| `sampling/sampling_acceptance.csv` | 9 行（9/9 验收） |
| `sampling/sampling_3to6_diff.md` 等 | 差异与轴选择均已产出（`sampling_3to6_diff*.csv/json`） |

**判读纪律**：`escalation_pending=24/24` 表示**升级已登记但未执行** ⇒ 只能说「审计处理与差异分析完整」，**不能说采样已收敛**；真正的采样收敛仍待独立容差/实用分辨率冻结，不能借 GFN2 的 1 kcal/mol 过门。

## 2. WP4 外部锚点：永久验证限制，不是"没有数据"

| 项 | 实测 |
|---|---|
| `wp4_anchor_tiers` | **satisfied**：`anchor_rows=87 tier_1=0 tier_2=14 tier_3=73` |
| `wp4_primary_text_check` | **exempt**：`transcription_only=14/87 permanent_validation_limitation=true` |
| `wp4_new_comparable_entries` | **exempt**：`tier_1_condition_matched=0 permanent_validation_limitation=true` |

**判读**：tier_1（同条件可比锚点）**为 0**，属可比性不足的**永久 validation limitation**；**不得**把付费墙/无 tier_1 说成「没有任何数据」。锚点产物在 `anchor/`（条件表、tier 汇总、系列覆盖、检索状态）。

## 3. 后继门：两项均未触发，且当前额为 0 CH

| 门 | 触发证据 | 结论 |
|---|---|---|
| WP6 显式配体 | `wp6_explicit_ligand status=blocked_on_production`；`li_pair_complete=12/12`、`required_li_pairs=9`、`production_ensembles=45/48`、`gate_ready=false`、`trigger_state=not_triggered` | **未触发**（差 48/48）；`plan_rows=4 executed_jobs=0` |
| 扩池 | `wp5_pool_extension status=not_satisfied`；`extension_candidates_frozen=11; extension_candidates_computed=0; extension_rows_in_main_set_file=0; replay_pool=legacy_pool_not_blind` | **未触发**（WP5 全池未通过） |

- 两项**当前执行额度 = 0 CH**；触发时须按实测 p90 与候选数**各自冻结**预算，**绝不从四态 800 抽取**。
- 严格闸门的 `derive_wp6_completion()` / `derive_pool_extension_completion()` 在证据产物缺失时返回 `None`（不是 False/True）⇒「没证据」永不被读成「已完成」。
- **触发 ≠ 已完成**：即使将来触发，也须实际执行并留下完成证据。

## 4. 边界

- 本文件不启动任何后继计算、不修改采样容差、不把 partial/exempt 升级为 satisfied。
- 采样收敛、WP6、扩池三项在报告中必须与「工程链全绿」**分开陈述**。
