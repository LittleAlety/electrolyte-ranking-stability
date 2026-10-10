# 锚点检索协议（方案 §8(c) 登记）

本文件是**结果前登记**的检索协议：在查看任何新命中之前写定检索源、检索式、纳入/排除标准与目标条目数。
它把方案 §8(c)「按明确检索协议寻找 6–10 个条件可比条目」的要求变成一条可核对、可复算的登记，
而不是每次口头重述。**当前状态：协议已登记且已执行（见文末「执行状态」与 `data/references/anchor_retrieval_execution.md`），新命中可纳入 0 条**，因此 tier_1 仍为 0，
external-validity limitation 继续生效（方案 §8(d)）。

## 1. 目的
为既有的氧化锚点找到**条件可比**的绝对标定条目：条件可比 = 同一溶剂（或同一溶剂体系）、同一盐与浓度、
同一温度、同一扫描速率区间、同一参考电极口径、同一 onset/峰值判据。只有条件可比才允许做热力学定量比较；
否则只能作系列内趋势，或不可用（方案 §8(b) 的三级分类）。

## 2. 检索源（按优先级）
1. Crossref REST API（`api.crossref.org`）：按 DOI 反查元数据与页码/表号。
2. OpenAlex（`api.openalex.org`）：补全收录、被引与开放获取状态。
3. Unpaywall / Europe PMC：确认是否有合法开放版本可取全文页码/表号。
4. NIST Chemistry WebBook（`webbook.nist.gov`）：气相电离能（只用于气相锚点，不作条件可比候选）。

## 3. 检索式（按源拼接，逐条登记，不事后改）
- 关键词组 A（物种）：`("ethylene carbonate" OR "propylene carbonate" OR "ethyl methyl carbonate" OR "gamma-butyrolactone" OR "sulfolane" OR "dimethyl sulfoxide" OR "acetonitrile")`
- 关键词组 B（条件）：`("oxidation potential" OR "oxidation stability" OR "anodic stability" OR "HOMO" ) AND ("vs Li/Li+" OR "vs Li" OR "vs SCE" OR "vs Ag/AgCl")`
- 关键词组 C（方法）：`AND ("linear sweep voltammetry" OR "LSV" OR "cyclic voltammetry" OR "CV") AND ("onset" OR "1 mA cm-2" OR "peak")`
- 关键词组 D（条件锁定）：`AND ("1 M LiPF6" OR "1 mol L-1 LiPF6" OR "0.65 M Et4NBF4") AND ("25 C" OR "room temperature")`
- DOI 反查式：对 `data/anchors/*.csv` 里已登记的每个 DOI，调 Crossref 取 `page` / `article-number` / `container-title` / `published`。

## 4. 纳入标准（全部满足才可作条件可比候选）
1. 溶剂与盐浓度与目标条目一致（允许明确声明的同一体系）。
2. 温度一致（25 ± 5 °C）。
3. 扫描速率与判据在同一区间（LSV，且 onset 判据一致：`j_onset_1mA_cm2` 或明确写出的等效判据）。
4. 参考电极口径可换算（给出 vs SCE / vs Ag/AgCl / vs Li 的换算与偏移）。
5. 原文可取得页码或表号，且数值为该表所载（非二次转录）。

## 5. 排除标准
- 跨原始系列混合后拼出的值（`cross_series_mixed = true`）。
- 只有摘要级描述（如 “above 1 V”）而无精确值的条目。
- 计算值冒充实验值（除非明确标为 computational target）。
- 条件模板而非某次实测条件（`nominal condition template`）。

## 6. 目标与停止规则
- 目标：找到 **6–10 条**条件可比条目，使 `tier_1_condition_matched` 严格大于 0。
- 停止：若在登记的检索源与检索式下仍取不到 6 条，则**保留 computational target + external-validity limitation**（方案 §8(d)），
  并在 `outputs/physics_completion/anchor/anchor_retrieval_status.md` 里如实登记已执行与未命中的检索式，不把「没找到」写成「已完成」。
- 旧结论不被覆盖：新证据只进入新的版本化评估（方案 §8(e)）。

## 7. 执行状态
- 协议版本：`anchor_retrieval_protocol_v1`
- 协议登记日期：2026-10-10
- 检索是否执行：**是（`executed = true`）**；执行日期 2026-10-10，执行记录见 `data/references/anchor_retrieval_execution.md`
- 实际执行源：Crossref REST API（DOI 反查 + 检索式 A/C 取回）、OpenAlex（检索式 A–D + 被引登记）、Unpaywall（OA 定位）、Semantic Scholar（被引交叉核对）
- 执行偏差：Crossref 对检索式 B / D 持续返回 HTTP 429 限流，未取回；该两条改由 OpenAlex 登记，偏差已写进执行记录
- 新命中条目数：**0**（四组检索式返回 19 个去重候选，无一条同时满足 §4 的五条纳入标准）
- 新命中可纳入条目数：**0**
- `tier_1_condition_matched`：**0**（保持）
- 结论：协议已按登记的源与检索式执行，结果按 §6 停止规则走「找不到足够可比数据」这一条——保留 computational target + external-validity limitation（方案 §8(d)），
  并把「没找到」原样写进执行记录，不写成「已完成」。两篇 Ue 正文仍未取得（IOPscience PDF 返回验证码页而非 PDF），
  `primary_source_status = full_text_not_obtained` 不变；执行中还发现 Okoshi 2015 的被引登记指向 Ue 参编专著与 CRC 手册，
  与此前猜测的两篇 Ue JES 论文不一致，故 `ue_ref_attribution` 的猜测保持 UNVERIFIED 并新登记为 `attribution_conflict_open`（详见执行记录 §5）。
