# 锚点检索协议执行记录（方案 §8(c)，协议 v1）

本文件是 `data/references/anchor_retrieval_protocol.md`（结果前登记）的**执行记录**：按登记好的检索源与
检索式实跑一遍，逐条登记谁取回、谁限流、谁被排除，并把全文获取尝试与被引登记的新发现一并留证。
本记录只登记事实，不改动任何既有锚点数值，也不把「没找到」写成「已完成」。

## 0. 执行摘要

- 协议版本：`anchor_retrieval_protocol_v1`（登记日期 2026-10-10，命中前写定）。
- 执行日期：2026-10-10。
- 执行源：Crossref REST API、OpenAlex、Unpaywall、Semantic Scholar（被引交叉核对）、
  IOPscience 与东京科学大学机构库（全文获取尝试）。
- DOI 反查：3/3 取回，题录与仓库登记一致（§2）。
- 登记检索式：4 条（协议 §3 的 A–D 组），实跑 4/4；其中 Crossref 对 B / D 两条持续限流（HTTP 429），
  该两条改由 OpenAlex 登记（§3），并把限流本身如实记录。
- 新命中条件可比条目：**0**。四组检索式返回 19 个去重候选，无一条同时满足协议 §4 的五条纳入标准。
- 全文获取：仍**未取得**（IOPscience PDF 返回验证码页而非 PDF；机构库只有题录页、无正文附件）（§4）。
- 结论：按协议 §6 停止规则，保留 computational target + external-validity limitation（方案 §8(d)）；
  `tier_1_condition_matched` 保持 **0**。

## 1. 执行方式（可复核）

全部查询用同一 UA（`electrolyte-ranking-anchor-protocol/1.0 (mailto:research@example.org)`）经 HTTPS 直连，
脚本不落库、不改任何锚点文件，只把原始响应写成 JSON 供本记录引用：

- DOI 反查：`GET https://api.crossref.org/works/{doi}`
- Crossref 检索：`GET https://api.crossref.org/works?rows=6&query.bibliographic={式}`
- OpenAlex 检索：`GET https://api.openalex.org/works?per-page=6&search={式}`
- OpenAlex 被引：`GET https://api.openalex.org/works/doi:10.1149/2.0051509eel`（取 `referenced_works`）
- Unpaywall 定位：`GET https://api.unpaywall.org/v2/{doi}`
- Semantic Scholar 被引：`GET https://api.semanticscholar.org/graph/v1/paper/DOI:10.1149/2.0051509eel?fields=references.*`

## 2. DOI 反查（3/3 取回）

| DOI | 题名（Crossref） | 作者 | 卷(期) 页 | 年 |
| --- | --- | --- | --- | --- |
| 10.1149/1.2059270 | Electrochemical Properties of Organic Liquid Electrolytes Based on Quaternary Onium Salts for Electrical Double‐Layer Capacitors | Ue M.; Ida K.; Mori S. | 141(11) 2989-2996 | 1994 |
| 10.1149/1.1837882 | Electrochemical Properties of Quaternary Ammonium Salts for Electrochemical Capacitors | Ue M.; Takeda M.; Takehara M.; Mori S. | 144(8) 2684-2688 | 1997 |
| 10.1149/2.0051509eel | Theoretical Analysis of the Oxidation Potentials of Organic Electrolyte Solvents | Okoshi M.; Ishikawa A.; Kawamura Y.; Nakai H. | 4(9) A103-A105 | 2015 |

题录层与仓库登记一致（`data/anchors/primary_source_verification.md` 第 2 节）。**注意**：题录已核 ≠ 正文已核；
两篇 Ue 正文仍未取得，`primary_source_status = full_text_not_obtained` 不变。

## 3. 检索式实跑与逐条排除

四组检索式按协议 §3 登记，返回的候选按协议 §4（五条纳入标准）逐条判定；**没有一条能同时满足**：
无法给出「同一溶剂 / 同一盐与浓度 / 25±5 °C / 同一 LSV 扫描速率与 onset 判据 / 原文表值可定位」的绝对标定。

| 组 | 登记检索式（协议 §3） | Crossref | OpenAlex | 判定 |
| --- | --- | --- | --- | --- |
| A（物种+条件） | oxidation potential organic electrolyte solvent vs Li/Li+ LSV onset | 取回（total 5003606） | 取回（total 411） | 前 6 位全是 LSV 一般方法学 / 别的体系 / 只有摘要级描述 → 全排除（§5 第 2、4 条） |
| B（条件锁定） | 0.65 M Et4NBF4 oxidation potential solvent glassy carbon LSV | **限流 429（未取回）** | 取回（total 0） | OpenAlex 零命中；Crossref 未取回 → 无候选 |
| C（盐/阳极稳定） | 1 M LiPF6 anodic stability oxidation onset solvent LSV | 取回（total 1848904） | 取回（total 64） | 命中集中在集流体腐蚀 / 界面 / 聚合物电解质，非溶剂氧化 onset → 全排除（§5 第 3、4 条） |
| D（专项物种） | sulfolane gamma-butyrolactone oxidation potential LSV onset lithium | **限流 429（未取回）** | 取回（total 1） | 唯一命中是低温电解液综述，无逐物种表值 → 排除（§5 第 2 条） |

去重后候选 19 条（含 `10.1021/jp210802q.s001` 这类补充材料 DOI、`10.1007/978-1-4613-4145-1_6` 这类教科书章节）。
逐条按协议 §5 判定的结果：

- 教科书 / 方法学章节（如 `10.1007/978-1-4613-4145-1_6`、`10.1201/b11100-10`、`10.1007/bf01034048`）：无目标溶剂的逐物种 onset 表值 → 排除。
- 补充材料 DOI（如 `10.1021/jp210802q.s001` 等以 `.s001` 结尾者）：不是独立实验条目 → 排除。
- 别的体系 / 别的电极过程（集流体腐蚀、ORR、PVdF 稳定性、正极界面，如 `10.1016/j.ces.2023.119346`、`10.3390/nano10091735`、`10.1038/srep45390`）：不是溶剂一电子氧化 onset → 排除。
- 综述（如 `10.1007/s41918-023-00199-1`）：无逐物种同条件表值 → 排除。
- 聚合物 / 离子液体体系（如 `10.1038/srep19892`、`10.1002/batt.202300085`）：盐与浓度条件不同 → 排除。

**结论：0 条通过协议 §4。** 不新增 `tier_1_condition_matched`。

## 4. 全文获取尝试（仍未取得）

| 目标 | 途径 | 结果 | 证据 |
| --- | --- | --- | --- |
| Okoshi 2015（10.1149/2.0051509eel） | Unpaywall 最佳 OA 位置 / IOPscience PDF | **未取得 PDF** | HTTP 200，`Content-Type: text/html`，14371 字节，首 6 字节为 `<head>`（验证码中转页，非 PDF） |
| Okoshi 2015 | 东京科学大学机构库（T2R2）题录页 | 只拿到题录 | 12220 字节 HTML，含作者/卷期页/DOI，**无正文附件链接** |
| Ue 1994（10.1149/1.2059270） | Unpaywall | 无合法开放版本 | `is_oa=false`，`oa_status=closed` |
| Ue 1997（10.1149/1.1837882） | Unpaywall | 有 bronze 版本但被拦 | `is_oa=true`，`oa_status=bronze`，PDF 地址同样返回验证码页 |

因此协议 §4 第 5 条（原文可取得页码或表号，且数值为该表所载）对全部候选均**无法满足**——
这本身也是 0 条通过的原因之一，必须如实登记，不能因为「大概能拿到」就算过。

## 5. 执行中的新发现：Okoshi 2015 被引登记与仓库猜测冲突

仓库把 14 行氧化锚点归给「Ue et al.（Okoshi 2015 refs 1-2）」，占位标识为
`ref1_likely_Ue1994_JES141_2989`（13 行）与 `ref2_likely_Ue1997_JES144_2684_UNVERIFIED`（EC 行）。
本次执行首次拿到 Okoshi 2015 的**被引登记**（此前因正文未取得而只能猜），两个独立索引给出的结果都**不支持**该猜测：

- **OpenAlex**（`W2136842731`）：`referenced_works` 恰好 **2 条**，为
  `W2132905138` = *CRC Handbook of Chemistry and Physics*（2014）与
  `W3143866903` = *Electrolytes for Lithium and Lithium-Ion Batteries*（Modern Aspects of Electrochemistry，2014，编者含 **Ue, Makoto**）。
- **Semantic Scholar**（`DOI:10.1149/2.0051509eel`）：`referenceCount=4`，其中同样出现
  *Electrolytes for Lithium and Lithium-Ion Batteries* 与 *CRC Handbook of Chemistry and Physics*；
  未见两篇 Ue JES 论文。

两个索引一致指向「Ue 参编专著 + CRC 手册」，而不是「Ue 1994 JES 141:2989 + Ue 1997 JES 144:2684」。
鉴于正文仍未取得（§4），本记录**不宣称** Okoshi 2015 的 refs 1-2 一定是哪几篇，只登记三点事实：

1. 仓库此前的 DOI 级归属是**猜测**（占位串里本就写着 `likely` / `UNVERIFIED`）；
2. 该猜测目前**未被任何可用证据支持**，且与两个独立被引登记**不一致**；
3. 因此 `ue_ref_attribution` 保持 UNVERIFIED，并新登记为 **attribution_conflict_open**，
   `tier_1_condition_matched` 不得因此升级。

正确收口方向（下一轮，需正文）：取到 Okoshi 2015 正文参考文献表后，按印刷版 ref 编号直接核对，
再决定是「确认为两篇 Ue JES 论文」还是「改登记为 Ue 参编专著 + CRC 手册」。在拿到正文前不改既有数值、不删既有登记。

## 6. 对合规台账的影响

- `tier_1_condition_matched`：**0**（保持）；external-validity limitation 继续生效（方案 §8(d)）。
- `wp4_new_comparable_entries`（方案 §8(c)）：由「尚未执行」转为**已按协议执行**；新命中可纳入 0 条，
  按协议 §6 走「找不到足够可比数据 → 保留 computational target + external-validity limitation」这一条，
  并把「没找到」原样写进本记录。
- `wp4_primary_text_check`：仍是 partial —— 两篇 Ue 正文未取得，14 行保持 transcription-only。
- 既有数值与既有登记**一律不动**：本记录只增不改（方案 §8(e)：新证据进新的版本化评估，不覆盖旧结论）。
