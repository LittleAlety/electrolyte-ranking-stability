# 外部锚点：转录源与原始文献核实（WP4 / 方案五）

> 本文件由人工核实后手写，**不是生成物**，不入任何冻结清单；它记录一次**只读**的
> 原文检索与比对，零新增电子结构计算。
> 一句话结论：**转录源（Okoshi 2015）全文已取得并逐值核对一致；原始文献身份已核实，
> 但全文仍未取得，故锚点等级保持 tier_2（transcription），本文件不构成任何「原始文献验证」。**

## 1. 这条锚点的两层来源

| 层 | 文献 | 可得性 | 本轮状态 |
| --- | --- | --- | --- |
| 原始测量（primary） | Ue, Ida, Mori, *J. Electrochem. Soc.* **141**(11) 2989-2996 (1994), DOI `10.1149/1.2059270` | 付费墙（Unpaywall `is_oa=false`, `oa_status=closed`） | `full_text_not_obtained`（等级不变） |
| 转录 + 换算（tabulation） | Okoshi, Ishikawa, Kawamura, Nakai, *ECS Electrochem. Lett.* **4**(9) A103-A105 (2015), DOI `10.1149/2.0051509eel` | **开放获取 CC BY 4.0** | 全文已取得，Fig.1 的 14 个值逐条核对一致 |

`data/anchors/within_series_ordering.csv` 的 14 行即转录自 Okoshi 2015 Fig.1。
需要特别说明：**Okoshi 是转录源，不是原始测量文献**；把本文件的比对结果称作「原始文献验证」
是错的，本条锚点因此仍停在 transcription 等级。

## 2. 原始文献身份核实（本轮新增）

Okoshi 2015 的参考文献表逐字写明：

```
1. M. Ue et al., J. Electrochem. Soc., 141, 2989 (1994).
2. M. Ue et al., J. Electrochem. Soc., 144, 2684 (1997).
```

用 Crossref 逐条核对这两条的身份（归属由此从「猜测」升级为「已核实」）：

| 代号 | DOI | 题名 | 卷/期/页 | 作者 |
| --- | --- | --- | --- | --- |
| ref1 | `10.1149/1.2059270` | Electrochemical Properties of Organic Liquid Electrolytes Based on Quaternary Onium Salts for Electrical Double-Layer Capacitors | JES 141(11) 2989-2996 (1994) | Ue, Ida, Mori |
| ref2 | `10.1149/1.1837882` | Electrochemical Properties of Quaternary Ammonium Salts for Electrochemical Capacitors | JES 144(8) 2684-2688 (1997) | Ue 等 |

这说明仓库此前的归属猜测（`ref1_likely_Ue1994_JES141_2989`、
`ref2_likely_Ue1997_JES144_2684_UNVERIFIED`）在**书目层是正确的**：页码、年份、作者全部对得上。
**但这只能证明「引用了哪一篇」，不能证明「那一篇里的实验条件与判据」**。

## 3. 逐值复核（14 / 14 一致）

论文 Fig.1 的图内文字（PDF 矢量文本，可被直接抽取）逐条给出 14 个溶剂的实验氧化电位：

```
#7: Ethylene carbonate      EC,  6.5 V
#9: Methoxy propionitrile   MPN, 6.4 V
#12: N-Methyl oxazolidinone NMO, 5.0 V
#14: Dimethyl imidazolidinone DMI, 4.5 V
#13: Dimethyl sulfoxide     DMSO,4.8 V
#8: Nitro ethane            NE,  6.5 V
#4: Propylene carbonate     PC,  6.9 V
#11: 1,3-Dioxolane          DOL, 5.5 V
#10: Methoxy acetonitrile   MAN, 6.3 V
#6: Sulfolane               SFL, 6.6 V
#5: Methyl acetate          MA,  6.7 V
#1: Glutaronitrile          GN,  8.3 V
#2: Butylene carbonate      BC,  7.5 V
#3: Ethyl methyl carbonate  EMC, 7.0 V
```

对照仓库值逐条一致（单位 V vs Li+/Li）。复核明细见同目录
`primary_source_verification.csv`（每行一条：仓库值 / 论文引文值 / 一致性 /
原始文献身份核实结果 / 原始正文可得状态）。

## 4. 换算口径已由原文确证

Okoshi 2015 正文明确写出 SCE → Li+/Li 的换算式（式 (2)）：

```
Vox (vs. Li+/Li) = Vox (vs. SCE) + Eo(SCE/SHE) - Eo(Li+/Li)/SHE
```

并以 `Eo(SCE/SHE) = 0.24 V` 计算，得到固定偏移 **+3.28 V**。这与
`data/anchors/within_series_ordering.csv` 记录的 `original_scale=SCE` /
`offset_applied_V=3.28` / `potential_V_vs_Li` 完全对应；Fig.1 印出的数值即换算后的
vs Li+/Li 值，因此仓库值与论文显示值应当逐字相等（实测相等）。

论文同一段还写明：

> experimental values are dependent on the experimental conditions, such as species and
> concentration of salt, while **the reference experimental values were obtained under an
> identical experimental condition**.

这支撑「同一系列 / 同一装置 / 同一判据」的分组用法（tier_2 的 series-trend 口径），
而不支撑任何跨系列的绝对比较。

## 5. 取回尝试与结果（本轮新增，全部为只读）

| 途径 | 结果 |
| --- | --- |
| Unpaywall（`api.unpaywall.org/v2/10.1149/1.2059270`） | `is_oa=false`, `oa_status=closed`, `oa_locations=[]` |
| OpenAlex（`api.openalex.org/works/doi:10.1149/1.2059270`） | `oa_status=closed`，无可用仓储副本 |
| Semantic Scholar（Graph API） | `isOpenAccess=false`，无 PDF |
| 出版社页面（IOPscience，`/article`、`/pdf`、`/meta`） | 均返回 Radware Bot Manager 验证页（HTTP 200 但不是正文），自动化无法取得 |
| ref2（`10.1149/1.1837882`） | Unpaywall `is_oa=true`（bronze），但唯一地址就在 IOPscience，同样被验证页阻断 |

结论：本机可以取得元数据（Crossref / Unpaywall / OpenAlex），但**取不到两篇 Ue 文献的正文**。
按方案五的停止规则，未取得全文时保持当前等级；该项不阻塞计算模型内部的研究。

## 6. 覆盖与限制

- 覆盖：Okoshi 2015 Fig.1 的 14 个溶剂全部核对；其中被本模型主集覆盖的仍是原来那 7 个。
- EC 一行仍带 `CONDITION_MATCH_UNVERIFIED`：Ue1994 的溶剂选择判据（mp<30°C）排除 EC，
  该值大概率来自 ref2；ref2 全文本轮**仍未取得**，故该旗标保持。
- 7 个锚点仍全部是 `transcription_only`；`tau_b = 0.428571` 与 Gate 1 的
  NOT CLOSED / NOT CLOSABLE 均不受本文件影响。
- 本文件**不**改写任何冻结产物（`within_series_ordering.csv`、
  `ue1994_okoshi2015_oxidation.csv`、`anchor_primary_audit.csv`、`outputs/week2/SHA256SUMS` 等一律原样）。
  对 `ref1_likely_*` / `ref2_likely_*UNVERIFIED` 字串的正式更新需连带重生成 week34 产物，故留待后续统一收口。

## 7. 复现

1. 取得 Okoshi 2015 全文（DOI `10.1149/2.0051509eel`，开放获取 CC BY 4.0）。
2. 抽取 p.A104 的 Fig.1 图内文字，与 `primary_source_verification.csv` 的
   `transcription_quoted_value_V` 列逐条比对。
3. 对照 `data/anchors/within_series_ordering.csv` 的 `potential_V_vs_Li` 列，应 14/14 相等。
4. 身份与可得性可用 Crossref / Unpaywall / OpenAlex 的公开 API 重算（第 2–5 节已给出确切结果）。

原始 PDF 放在仓库外（`work/`，不入库）；上面的引文已足以让审阅者独立复核。
