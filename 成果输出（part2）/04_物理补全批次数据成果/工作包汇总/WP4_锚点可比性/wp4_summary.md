# Week 41 / WP4 — 外部锚点复核与可比性审计

**状态**：既有锚点三级分类完成；7 个氧化锚点逐条重算，旧结论原样保留。

## 逐条复核（单一同源序列 Ue1994_Okoshi2015）

- 序列共 14 行；被模型覆盖 **7** 个（EMC、PC、MA、SL、EC、DOL、DMSO）；未覆盖 7 个。
- 逐对重算：一致 **15** / 不一致 **6** / n_pairs = **21** → tau_b = **0.428571**（冻结 0.428571）。
- 旧 Gate 1：reason = `ordering_disagrees`，tau_b = 0.4286 < 0.90，**NOT CLOSED / NOT CLOSABLE 原样保留**。

## 三级分类

| tier | 条目数 | 其中被模型覆盖物种 | 可用性 | 依据 |
| --- | --- | --- | --- | --- |
| tier_1_thermodynamic_quantitative | 0 | 0 | false | no condition-matched absolute-calibration series exists in the repository |
| tier_2_series_trend | 14 | 7 | trend_only | one homologous series (one paper / apparatus / criterion); 7/14 series rows are model-covered |
| tier_3_not_usable | 73 | 54 | false | literature estimates (est), DOE secondary and gas-phase anchors: species coverage is recorded per row, but a covered species is still not condition-comparable -> stays unusable |

## 验收（7/7 通过）

| check | ok | detail |
| --- | --- | --- |
| tau_b_recomputed_from_frozen_inputs | PASS | recomputed=0.428571428571 frozen=0.428571428571 |
| pair_counts_match_frozen | PASS | recomputed 15/6 n=21 ; frozen 15/6 n=21 |
| est_rows_not_upgraded | PASS | n_est=31 (0 upgraded) |
| cross_series_mixing_flagged | PASS | series_id=Ue1994_Okoshi2015 单系列；DOE secondary 与气相锚点单列 tier_3 |
| tier_counts_match_the_audit_table | PASS | tier entries=87 ; audit rows=87 |
| gate1_unchanged | PASS | reason=ordering_disagrees tau_b=0.4286 n_pairs=21 |
| tier_coverage_counts_match_the_audit_table | PASS | tier_2=7 tier_3=54（由 audit 表 covered_by_model 逐行计数） |

## 限制

- 该序列仍是 **transcription-only**（未回原文页码/表号复核）；行本身未删除、未升级。
- 7 个分子产生的 21 个 pair **不是** 21 个独立实验样本；跨系列不强行汇总。
- 不可逆分解 onset 不等于完整分子一电子平衡电位；绝对标定层仍按 limitation 处理。
- 若新证据出现，只进入**新的版本化评估**，不覆盖旧结论。
