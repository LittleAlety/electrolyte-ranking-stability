# Week 37 / WP0 — 定义迁移与历史结论同步

**状态**：已登记（零新增电子结构计算）。

## 交付

- 新批次协议 `config/physics_completion_v1.yaml`（量名/方向/状态身份/停止规则/落点）
- 样本 `data/metadata/physics_completion_set.csv`（12 主集 / 8 方法集 / 4 采样集）
- 结论迁移 `docs/claim_migration.md`（5 条：M1/Q3、M2/Q7、M3/Q10、M4/R15、M5/P1a）
- 原始锚点复核 `data/references/anchor_primary_audit.csv`（WP0 起登记，WP4 细化）

## 验收（7/7 通过）

| check | ok | detail |
| --- | --- | --- |
| quantity_names_unique | PASS | 7 个量名 / 7 个唯一 |
| quantity_fields_complete | PASS | required=name,definition,unit,quantity_kind,objective_direction,geometry_policy,thermal_policy,ensemble_policy,solvent,state_identity_eligibility,analysis_cohort,role |
| legacy_alias_never_a_new_quantity_name | PASS | clash=none |
| direction_selects_the_same_set | PASS | EA pick=a ; Sred pick=a |
| missing_state_never_coerced_to_zero | PASS | mixed pick=a ; all-missing pick=None |
| claim_migration_covers_required | PASS | covered=P1a,Q10,Q3,Q7,R15 |
| cohorts_nested_in_core_set | PASS | main=12 audit=8 sampling=4 |

## 限制

- 本批次只登记定义与样本；新方法、新阈值在结果产生前冻结，尚未产生任何新计算量。
- 方向一致性用人为例子验证（maximise Sred 与 minimise EA 同一集合），不代表真实数值已就绪。
- 旧别名（P1→P1v、P2→P2a）只作映射存在，任何代码路径都不允许把旧别名静默当成新量名。
