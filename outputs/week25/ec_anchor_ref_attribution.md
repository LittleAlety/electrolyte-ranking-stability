# W25 EC 氧化锚点归属疑点

## 发现

Ue 1994 的溶剂选择判据是**熔点低于 30 °C**；EC 熔点 36.4 °C，按此判据**进不了**主源的 20 溶剂表（该文试剂段也只列了电池级 PC、BC、GBL）。因此 Okoshi 2015 Fig. 1 中 **EC = 6.5 V** 这个值大概率来自 **ref 2**——候选为 Ue, Takeda, Takehara, Mori, *J. Electrochem. Soc.* **1997**, 144, 2684–2688，其装置 / 判据 / 支持电解质 / 温度是否与 ref 1 完全一致**必须核实原文**。

## 意义：EC 处置从"事后剔除"升级为"先验锚点质量分层"

判据的 6 个不一致对中有 4 个涉及 EC，而 EC 恰是系列内**唯一有据可查的条件可疑锚点**。这一步的动机来自**独立的文献判据（熔点选择规则）**，不是结果驱动：在仓库里，EC 已按该规则标为 `adjudicated_flagged` + `CONDITION_MATCH_UNVERIFIED`（`ue_ref_attribution = ref2_likely_Ue1997_JES144_2684_UNVERIFIED`）。

## 行动项

1. 从图书馆取 Ue 1997 原文，核 EC 的测量条件；
2. 条件一致 → EC 归位主系列；
3. 条件不一致 → EC 保持 flagged，6 溶剂子集只作诊断；
4. 核实完成前，主检验仍以注册的 7 溶剂（21 对）为准，EC 单列报告。

## 诚实边界（必须与数字同时引用）

- **即便 EC 被合理降级，Gate 1 依旧不闭合**：其余 6 个分子的 τ_b = 0.7333，仍低于预注册阈值 0.9。
- **剔除后只有 15 对，低于 `min_pairs = 18`**：该变体在冻结判据下的判决是 `insufficient_pairs`（**不可判定**），不是"通过"。
- 该结论已于 2026-10-02 在仓库内实测确认：用 `scripts/check_series_rel_ordering.py --table <6 溶剂副本>` 得到 `usable pairs = 15`、`tau_b = 0.7333`、`verdict = OPEN (insufficient_pairs)`。
- **措辞规则**：可以说"判据未通过（`ordering_disagrees`），且主要来源是一个条件可疑的锚点"；可以说"按文献判据排除该锚点后仍未达阈值"；**不可以说"排除后通过"**。
- 本批数值仍全部是用户提供的转录值（`repo_verification = transcription_only`），仓库未独立复核任何一行。

## 相关文件

- `data/anchors/ue1994_okoshi2015_oxidation.csv`（含 `ue_ref_attribution` 列）
- `data/anchors/_received/Gate1_solution_anchor_potentials_2026-10-02_rev2.csv`（SHA256 `6aa15654…ee46`，字节级归档）
- `outputs/week25/anchor_ingest_provenance.json`（ref1 = 13、ref2 = 1、NA = 3；`adjudicated_flagged` = 1）
- `outputs/week25/anchor_attribution_conflict.json`（归属裁决，status = resolved）
