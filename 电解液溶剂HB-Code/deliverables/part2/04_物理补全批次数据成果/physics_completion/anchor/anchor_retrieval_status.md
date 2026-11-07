# 锚点条件元数据审计与检索协议状态（方案 8(a) / 8(c)）

本文件由 scripts/wp_production/build_anchor_condition_audit.py 生成，数字全部从盘上读现算，源码里不写死。

## 1. 条件元数据并表结果

把四组既有锚点源里本来就有的条件列并到一张表，缺的字段留空并写明原因（详见 CSV 的 note 列）：

| family | 行数 | 条件状态 |
| --- | --- | --- |
| within_series_manual | 14 | condition_fields_present_but_primary_text_not_obtained |
| doe_secondary | 3 | series_trend_only_secondary_source |
| solution_estimate | 31 | estimate_nominal_condition_template |
| gas_phase | 39 | not_applicable_gas_phase |

覆盖字段：溶剂、盐与浓度、温度（K）、扫描速率（mV/s）、误差来源、原始标度与原始数值、原文页码/表号、
primary 源状态。参考电极 / 判据 / 系列 / 是否跨系列混合在 anchor_primary_audit.csv 里已有，本表沿用同一口径，
不改动那 87 行。

## 2. 检索协议状态（方案 8(c)）

- 协议文件：data/references/anchor_retrieval_protocol.md（结果前登记，含检索源、检索式、纳入、排除、停止规则）。
- 执行状态：已执行（executed = true，2026-10-10）；执行记录 data/references/anchor_retrieval_execution.md。
- 新命中条件可比条目：0（四组检索式返回 19 个去重候选，无一条满足纳入标准）。
- tier_1_condition_matched：0（保持）。
- 结论：按协议 §6 停止规则维持 computational target + external-validity limitation（方案 8(d)）；
  两篇 Ue 正文仍未取得，且执行中发现 Okoshi 2015 的被引登记（Ue 参编专著 + CRC 手册）与此前猜测的两篇 Ue JES 论文冲突，
  ue_ref_attribution 保持 UNVERIFIED 并登记为 attribution_conflict_open。

## 3. 验收（7/7 通过）

| check | ok | detail |
| --- | --- | --- |
| every_anchor_family_matches_the_primary_audit_table | PASS | primary_audit_by_family={"doe_secondary": 3, "gas_phase": 39, "solution_estimate": 31, "within_series_manual": 14} condition_audit_by_family={"doe_secondary": 3, "gas_phase": 39, "solution_estimate": 31, "within_series_manual": 14} |
| required_condition_fields_are_filled_per_family | PASS | missing=0  |
| gas_phase_conditions_are_explicitly_not_applicable | PASS | gas_rows=39 |
| retrieval_protocol_is_registered_with_all_required_sections | PASS | protocol=data/references/anchor_retrieval_protocol.md markers=5/5 |
| retrieval_is_executed_and_reports_zero_admissible | PASS | executed=true；执行记录 data/references/anchor_retrieval_execution.md 在盘上；新命中可纳入 0 条，走协议 §6 停止规则 |
| no_condition_value_is_guessed | PASS | empty stays empty; 0 is never used as a stand-in |
| tier1_limit_is_carried_forward_not_hidden | PASS | tier_1_row_present=False |
