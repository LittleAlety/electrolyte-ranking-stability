# Week 39 / WP2 — 固定背景配对自由能标签

**状态**：账本与系综规则已冻结；既有数值只盘点电子能层，热校正仍为空（未计算）。

## 交付

- `state_ledger_template.csv`：12 主集 × 4 主状态 = **48** 行记账模板（Opt/Freq/SP 分列）。
- `sampling_plan.csv`：4 个采样审计分子 × 4 状态，3→6 结构升级规则。
- `ensemble_rules.csv`：7 条系综/窗口/去重规则。
- `existing_electronic_layer.csv`：32 条既有电子能层数值（12 个分子），全部标注 `thermal_correction=absent`。

## 验收（5/5 通过）

| check | ok | detail |
| --- | --- | --- |
| ledger_covers_main_x_four_states | PASS | n_rows=48 |
| thermal_fields_left_empty_not_zero | PASS | 48 行的 g_single_ev / thermal_corr_ev 均为空串 |
| sampling_plan_has_escalation_rule | PASS | n_rows=16 |
| existing_electronic_layer_is_labelled | PASS | 32 条既有数值 / 12 个分子 |
| ensemble_rules_frozen | PASS | n_rules=7 |

## 限制

- 热校正字段全部为空：本批次尚未运行任何频率计算，**不**把气相热项静默当作溶液热项。
- 既有 P1v/P1a/C1 数值是 r2SCAN-3c 气相电子能差，不能直接当作固定背景 SMD 自由能标签。
- 采样窗口 6 kcal/mol 与上限 3 结构是**资源规则**，不是已经证明收敛的采样尺度。
