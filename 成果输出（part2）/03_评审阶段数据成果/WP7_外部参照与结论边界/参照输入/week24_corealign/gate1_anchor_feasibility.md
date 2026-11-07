# Gate 1（溶液相锚点）降级关闭可行性审计

- 文档：`outputs/week24_corealign/gate1_anchor_feasibility.md`
- 日期：2026-10-02（Asia/Shanghai）
- 审计对象：核心文件 `ranking-electrolyte-materials-v2.md` §15.1–§15.3 与 §19 Stage 1 / Gate 1；
  冻结件 `data/anchors/`；`scripts/freeze_gates.py` 的 Gate 1 两级化实现
- 关联文档：`docs/06_stage1_solution_anchor_audit.md`、`docs/31_plan_revision_expert_review.md`（R7）、
  `data/anchors/solution_anchor_verification.md`
- 本轮纪律（**硬约束**）：**只读**。未新增任何电子结构计算；未改动论文任何文件；
  未改动 `data/anchors/solution_redox_anchors.csv`（31 行仍 `method=est`）；
  `data/anchors/within_series_ordering.csv` 仍为**仅表头**。
- 证据分级（全文统一使用）：

| 标记 | 含义 |
| --- | --- |
| **[L]** | 本地 PDF，本轮由 `scripts/audit_w24_gate1_literature.py` 用 pypdf 亲自抽取；给出文件名 + PDF 页 + 印刷页 |
| **[R]** | 本仓库**先前记录**（`outputs/_anchor_retrieval_raw.md` 2026-09-29；`outputs/_week6_scratch/anchor_verification.md` 2026-09-28；`data/anchors/solution_anchor_verification.md` 2026-10-02 批次 C）。**非本轮重取**，按记录转述 |
| **[未定位]** | 本地 PDF 与本仓库记录中**都找不到**；不写任何推测值 |

> 本轮新增一个可审计事实：本机**网络不可达**（`api.crossref.org` / `api.openalex.org` 均
> WinError 10061，本地代理端口无监听），见 `outputs/week24_corealign/gate1_ref_online_check.json`。
> 因此**本轮没有任何新的在线元数据或数值**；所有在线事实均来自上表 [R] 记录。

---

## 0. 判决（结论先行）

**判决：NOT_CLOSABLE（以当前可得证据）。**

排序一致性级的三条关闭条件中，**第 1 条直接不满足**：

| 判据（`data/anchors/solution_anchor_verification.md` §2 预注册） | 现状 | 判定 |
| --- | --- | --- |
| 1. 可用 within-series 锚点对数 `n_pairs >= 18` | **0** | **不满足** |
| 2. target model 的 within-series 排序一致性 `Kendall tau_b >= 0.9` | 无数据，不可计算 | **不可判定** |
| 3. 每一对必须同源（同一文献 / 同一装置 / 同一判据） | 无对可查 | **不适用** |

- 与 `docs/06` §8、`data/anchors/solution_anchor_verification.md` §4.3 的既有结论**一致**；
  本轮是**独立复核**（换了方法：先清点本地 13 篇 PDF 全文，再回到 [R] 记录交叉验证），结论未变。
- 本轮**增量**（相对既有记录）：
  1. 把 13 篇本地 PDF **逐篇**清点并给出题录、是否含可用数值、页码（下表 §2）；
  2. 把"提到溶剂名"与"有可引数值"**分开统计**（§3）；
  3. 给出**量化门槛**：`n_pairs >= 18` 等价于**同一序列至少覆盖 7 个核心集分子**（§4.0）；
  4. 把外部评审提出的两条线索（Okoshi 2015 / Ue 系列）**定性区分**，并指出其中一条表述需更正（§7）。

---

## 1. 判定口径（沿用冻结值，本轮不新造任何数字）

### 1.1 核心文件要求

核心文件 §15.2 原文要求：优先寻找**同一实验系列**中条件尽可能一致的 **10–20 个分子**；
条件（solvent / supporting salt / concentration / temperature / reference electrode / scan conditions）
不可统一时，**不**强行做绝对值 pooled regression，而**优先使用 within-series relative ranking**。
§19 Stage 1 的 Gate 1 判据是："production protocol 对典型体系的 state identity、SCF stability、
gas-phase anchor 和 **solution trend** 均没有明显系统性失败"。

### 1.2 本仓库把 Gate 1 两级化之后（`docs/31` R7，2026-10-02）

| 级别 | 内容 | 现状 |
| --- | --- | --- |
| **绝对标定级** `anchors:solution_absolute_calibration` | 31 行绝对电位可追溯到"条件匹配"的一次测量 | 承认为未达成 → 记为 **limitation**，不计 blocker |
| **排序一致性级** `anchors:series_rel_ordering` | within-series 相对排序与 target model 一致 | **当前唯一的 Gate 1 blocker** |

排序一致性级三条判据见本文件 §0 的表；阈值 `T = 0.9` 直接复用 `config/prereg.yaml` 已冻结的
"strong" 档，**本轮不新造、不放宽**。

### 1.3 本轮的两个操作性定义（不改冻结件，仅用于本报告表述）

- **"同源序列"（within-series）**：同一篇文献 **且** 同一装置/判据。
  *推论*：一本**综述**内部转述的多个数值来自不同上游文献，**不构成**一个同源序列。
- **"可引数值"**：能追到"具体文献 + 页码/表号 + 单位与参考电极 + 计算或实验"的数值。
  **只提到溶剂名不算**；"某配方电压窗上限"不算该溶剂自身的氧化/还原电位。

---

## 2. 本地文献清单（13 篇 PDF，逐篇）

清点范围：`核心文件/文献/分支a-d/`（7 篇）+ `核心文件/文献/新建文件夹/`（6 篇）＝ **13 篇**。
这是本项目全部本地文献 PDF（其余 PDF 为论文自身与 matplotlib 示例，已排除）。

| # | 文件 | 来源（本轮抽取的题录） | 含可用溶剂电位数值？ | 命中页码 / 表号 |
| --- | --- | --- | --- | --- |
| 1 | `分支a-d/B2-CREST-Pracht-2024.pdf` | Pracht et al., *J. Chem. Phys.* **160**, 114110 (2024)；DOI `10.1063/5.0197592`（CREST） | **否** | 无（全文 0 次 `V vs`、0 次 `oxidation potential`） |
| 2 | `分支a-d/A3-qRRHO-Grimme-2012.pdf` | Grimme, *Chem. Eur. J.* (2012)；DOI `10.1002/chem.201200497`（gCP / 色散校正） | **否** | 无 |
| 3 | `分支a-d/A2-association-entropy-RebollarZepeda-2026.pdf` | Rebollar-Zepeda et al., *JCTC* **22**, 6367–6376 (2026)；DOI `10.1021/acs.jctc.6c00575` | **否**（连续介质熵误差） | 无 |
| 4 | `分支a-d/B1-GFN2-xTB-Bannwarth-2019.pdf` | Bannwarth, Ehlert & Grimme, *JCTC* (2019)；DOI `10.1021/acs.jctc.8b01176`（GFN2-xTB） | **否** | 无（`HOMO`/`LUMO` 各 1 次，非电位表） |
| 5 | `分支a-d/C1-electrolyte-MD-review-2022.pdf` | Yao, Chen & Zhang, *Chem. Rev.* **122**, 10970–11021 (2022)；DOI `10.1021/acs.chemrev.1c00904` | **否**（综述；本地最广，14 个核心集分子名出现，但**无逐物种 redox 数值表**） | 无表；`V vs`/`Li/Li` 命中 0–1 次 |
| 6 | `分支a-d/A1-SMD-Marenich-2009.pdf` | Marenich, Cramer & Truhlar, *J. Phys. Chem. B* (2009)；DOI `10.1021/jp810292n`（SMD） | **否** | 无（DMSO/ACN 出现但为溶剂化参数语境） |
| 7 | `分支a-d/C2-solvation-structure-interface-2022.pdf` | Cheng et al., *ACS Energy Lett.* (2022)；DOI `10.1021/acsenergylett.1c02425`（溶剂化结构综述） | **否** | `vs Li` 3 次均为"vs Li+-EC"这类**比较级措辞**，不是电位值；出现的数字是配位数/摩尔比 |
| 8 | `新建文件夹/M5-Borodin-2019-electrolyte-stability-window.pdf` | Borodin, *Curr. Opin. Electrochem.* **13**, 86–93 (2019)；DOI `10.1016/j.coelec.2018.10.015` | **部分**（见 §3.2；4 个物种有值，但**分属 4 个上游来源、calc 与 exp 混排**） | 印刷 **p.87 / p.88 / p.89 / p.91**（PDF 2/3/4/6）；**全文 0 次 "Table"** |
| 9 | `新建文件夹/M6-Yang-2025-Li-coordination-ML.pdf` | Yang et al., *Mater. Today Energy* (2025)；DOI `10.1016/j.mtener.2025.102121` | **否**（计算/ML；Li+ 配位态的 ΔGox/ΔGred；只出现 EC / VC） | 数值表为 **Table S3（补充材料）**，未随 PDF 提供 → 不可引 |
| 10 | `新建文件夹/M3-Marenich-2014-liquid-phase-reduction-potentials.pdf` | Marenich et al., *PCCP* **16**, 15068–15106 (2014)（计算电化学综述）；DOI `10.1039/c4cp01572j` | **否**（方法学综述；`reduction potential` 96 次均为概念/协议） | 无逐溶剂实验表 |
| 11 | `新建文件夹/M7-Husch-2015-high-throughput-screening.pdf` | Husch et al., *PCCP* **17**, 3394–3401 (2015)（虚拟高通量筛选）；DOI `10.1039/c4cp04338c` | **否**（ESW **estimator** 定义与工作流） | 无 |
| 12 | `新建文件夹/M2-Peljo-Girault-2018-HOMO-LUMO.pdf` | Peljo & Girault, *Energy Environ. Sci.* **11**, 2306–2309 (2018)；DOI `10.1039/c8ee01286e` | **部分**（**仅 EC 一个物种**，且为计算，AVS 标度） | 印刷 p.3（PDF 3）：7.87 V（AVS）、6.4–6.6 V（AVS）= **5–5.2 V vs Li+/Li** |
| 13 | `新建文件夹/M4-Itkis-2021-Li-solvation-ambiguities.pdf` | Itkis et al., *PCCP* **23**, 16077–16088 (2021)；DOI `10.1039/d1cp01454d` | **否**（Li+ **溶剂化自由能**，属性不同；覆盖 PC/GBL/SL/DMSO/AN） | 无 redox 电位 |

**一句话**：13 篇中只有 1 篇（#8 Borodin 2019）含有**多个**核心集溶剂的电位数值，
且其数值**不是**一个同源测量序列；#12 只覆盖 EC 一个物种。

---

## 3. 溶剂交集表（文献 vs 本文 18 个核心集分子）

### 3.1 表 A：名称命中 ≠ 有数值

"名称命中"= 该缩写/全名在某篇本地 PDF 全文以词边界出现（`\bDMC\b`、`sulfolane` 等）；
**命中只说明该文讨论过这个溶剂，不说明该文给了它的氧化/还原电位**。缩写命中仍有噪声
（如 `MA`、`EA` 可能落在其他语境），凡不能逐句确认语境的，本表一律按"仅提及"处理。

| 核心集分子 | 命中文献数 | 命中的文献 | 是否有**可引的氧化/还原电位值** | 数值出处 |
| --- | ---: | --- | --- | --- |
| C01 DMC | 4 | cr1c00904, nz1c02425, Borodin2019, c4cp04338c | **部分**（Li+(DMC)Li+ 还原，计算） | Borodin2019 印刷 p.91 **[L]** |
| C02 EMC | 3 | cr1c00904, nz1c02425, c4cp04338c | 否 | — |
| C03 DEC | 3 | cr1c00904, nz1c02425, c4cp04338c | 否（仅"五种碳酸酯均 >1 V"的**组级**表述，无逐物种值） | [R] `_anchor_retrieval_raw.md` §1 |
| C04 EC | 6 | cr1c00904, nz1c02425, Borodin2019, c4cp01572j, c4cp04338c, c8ee01286e | **是**（计算 3 条 + 实验 1 条，见 §3.2） | Borodin2019 p.87–88 **[L]**；Peljo2018 p.3 **[L]** |
| C05 PC | 6 | Grimme2012, cr1c00904, jp810292n, nz1c02425, Borodin2019, c4cp04338c | 否（均为溶剂化/配位语境） | — |
| C06 FEC | 3 | cr1c00904, nz1c02425, Borodin2019 | 否（仅"比 EC 早约 0.3 V"的相对表述） | [R] `anchor_verification.md` §3.2 |
| C07 VC | 5 | cr1c00904, nz1c02425, Borodin2019, MTE2025, c4cp04338c | **是**（计算 ~5 V vs Li/Li+） | Borodin2019 印刷 p.88 **[L]** |
| C08 DME | 4 | cr1c00904, nz1c02425, c4cp04338c, d1cp01454d | 否 | — |
| C09 DOL | 2 | cr1c00904, nz1c02425 | 否 | — |
| C10 TEGDME | 1 | nz1c02425 | 否 | — |
| C11 EA | 5 | acs.jctc.8b01176, jp810292n, nz1c02425, MTE2025, c4cp04338c | 否 | — |
| C12 MA | 3 | nz1c02425, Borodin2019, MTE2025 | 否（命中语境未确认） | — |
| C13 GBL | 1 | d1cp01454d | 否（该文只给 Li+ 溶剂化自由能） | — |
| C14 SL | 3 | nz1c02425, Borodin2019, d1cp01454d | **是**（计算 4.65 V；另有实验单值 5.0 V 属 [R]） | Borodin2019 印刷 p.89 **[L]**；[R] Xing2014 摘要 |
| C15 DMSO | 5 | cr1c00904, jp810292n, nz1c02425, c4cp01572j, d1cp01454d | 否 | — |
| C16 AN | 5 | jp810292n, nz1c02425, Borodin2019, c4cp01572j, d1cp01454d | 否（只有"AN 对 Al 的氧化 ~4.1 V"，**不是 AN 自身氧化电位**） | [R] `anchor_verification.md` §3.7 |
| C17 TMP | 1 | nz1c02425 | 否 | — |
| C18 SN | 0 | — | 否 | — |

**交集规模**：18 个核心集分子中，**17/18 在本地文献里至少被提到过一次**（唯一完全未出现的是 SN / 丁二腈）；
但其中**只有 4 个（EC、VC、SL、DMC）取到可引数值**，且这 4 个值**来自 3 个不同的上游来源**（Ref [3] / Ref [15] / Ref [19]）。

### 3.2 表 B：本地文献中**唯一可取**的具体数值（逐条带页）

来源文件：`核心文件/文献/新建文件夹/M5-Borodin-2019-electrolyte-stability-window.pdf`
（Borodin, *Curr. Opin. Electrochem.* **13**, 86–93 (2019)）。印刷页与 PDF 页对应：
PDF 1 = p.86，PDF 2 = p.87，PDF 3 = p.88，PDF 4 = p.89，PDF 6 = p.91。

| # | 物种 | 文献值 | 单位 / 标度 | 参考电极 | 测量方式 | 页（印刷/PDF） | 上游出处 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 孤立 EC（隐式溶剂包围） | ~7 V | V vs Li/Li+ | Li/Li+ | **计算**（DFT/QC） | p.87 / PDF 2 | 本文档自身计算 |
| 2 | EC(PF6-) 与 EC2 二聚体 | 5–6 V（随反应物/终态构型） | V vs Li/Li+ | Li/Li+ | **计算** | p.88 / PDF 3 | 同上 |
| 3 | EC2 二聚体（假设 (EC-H) 自由基开环） | ~4.3 V | V vs Li/Li+ | Li/Li+ | **计算** | p.88 / PDF 3 | 同上 |
| 4 | EC 基电解液氧化起始 | onset ~4.3 V（低速率）；>4.9 V 无需开环；~6.8 V 无需 H 转移 | V vs Li/Li+ | Li/Li+ | **计算** | p.88 / PDF 3 | 同上 |
| 5 | **混合碳酸酯 + 1 M LiClO4 或 LiPF6**（glassy carbon） | onset ~4 V；"characteristic oxidation stability **3.9–4.4 V**" | V vs Li/Li+ | Li/Li+ | **实验**（CV） | p.88 / PDF 3 | Egashira et al., *J. Power Sources* **2001**, 92, 267–271（= 该文 Ref [15]，**本地 PDF 参考文献逐字可查**；原始文本身未取到 [R]） |
| 6 | VC（以 VC(PF6-)2 为模型） | ~5 V | V vs Li/Li+ | Li/Li+ | **计算** | p.88 / PDF 3 | 该文 Ref [3] = Borodin, Behl & Jow, *J. Phys. Chem. C* **2013**, 117, 8661–8682 |
| 7 | SL（SL–FSI） | 4.65 V | V vs Li/Li+ | Li/Li+ | **计算** | p.89 / PDF 4 | 该文 Ref [19] = Alvarado et al., *Mater. Today* **2018**, 21, 341–353 |
| 8 | SL–LiFSI 复合物 | 比 SL–FSI 高 ~0.9 V | V vs Li/Li+ | Li/Li+ | **计算** | p.89 / PDF 4 | 同上 |
| 9 | Li+(DMC)Li+ 还原 / Li+EC 复合物还原 | 1.4 V / ~0.6 V | V vs Li/Li+ | Li/Li+ | **计算** | p.91 / PDF 6 | 该文计算 |
| 10 | 线性碳酸酯还原（实验，**组级**表述） | ~1.4–1.5 V | V vs Li/Li+ | Li/Li+ | **实验**（转述，未给单篇条件） | p.91 / PDF 6 | 该文 Ref [24, 25] |
| 11 | EC 直接氧化 / EC+PF6-（生成 HF 后） | 7.87 V（AVS）；6.4–6.6 V（AVS）= **5–5.2 V vs Li+/Li** | 绝对真空标度 AVS，并换算 | Li+/Li / AVS | **计算** | `M2-Peljo-Girault-2018-HOMO-LUMO.pdf` PDF 3 = 印刷 p.2308 **[L]** | Peljo & Girault, *EES* **11**, 2306 (2018) |
| 12 | SL 氧化（1 M LiPF6/SL，Pt 与 LNMO 电极） | ~5.0 V | V vs Li/Li+ | Li/Li+ | **实验**（摘要逐字） | 无本地 PDF | **[R]** Xing et al., *Electrochim. Acta* **133**, 117–122 (2014)，DOI `10.1016/j.electacta.2014.03.190` |

### 3.3 两条必须写死的读法

1. **#1–#4、#6–#9 全部是计算值**。按 §1.3 的"可引数值"口径它们可引用，但**不能**用于支撑
   "experimentally anchored ranking decisions"（§15.3）这句话。
2. **#5 是唯一的实验序列**，但它是"**混合碳酸酯**"的**组级**区间（3.9–4.4 V），
   **不是**逐溶剂值；它对核心集只能提供一个"碳酸酯整体"的落点，构造不出任何一对。
   #12 是单溶剂单值。二者**都不是** within-series 表。

---

## 4. 能构造多少个 within-series 内可比的分子对？

### 4.0 量化门槛（本轮补算，关键）

判据 1 要求 `n_pairs >= 18`。若某个同源序列覆盖 `k` 个核心集分子，则 `n_pairs = k(k-1)/2`：

| k | 6 | **7** | 8 | 10 | 12 | 18 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| n_pairs | 15（不足） | **21（刚过线）** | 28 | 45 | 66 | 153 |

→ **门槛等价于：必须找到"同一文献 + 同一装置/判据"、且至少覆盖 7 个本文核心集分子的序列。**
核心文件 §15.2 说的"10–20 个分子"对应 `n_pairs = 45–190`，远高于下限；本轮以 18 对为最低线。

### 4.1 实际可构造数

| 来源 | 该来源内可用于同一序列的物种数 `k` | `n_pairs = C(k,2)` | 是否合格 |
| --- | ---: | ---: | --- |
| Egashira 2001（碳酸酯 CV，glassy carbon） | 1（**组级**"混合碳酸酯"） | 0 | 否 |
| Alvarado 2018（1 m LiFSI-SL） | 1（SL） | 0 | 否 |
| Xing 2014（1 M LiPF6/SL） | 1（SL） | 0 | 否 |
| A 组（碳酸酯 CV in THF/LiClO4） | 1（**组级**"均 >1 V"） | 0 | 否 |
| Nilsson 2018（AN） | 1（AN，且值是 Al 集流体而非溶剂） | 0 | 否 |
| **合计（严格按"同源"定义）** | — | **0** | **否** |

### 4.2 一个"最宽松"反例（说明为什么不能靠综述凑数）

若**故意违反**判据 3、把 `Borodin 2019` **整篇综述**当成一个"序列"，其可用的**氧化**值也只有
`EC / VC / SL` 三个物种（`k = 3`，`n_pairs = 3`），其中 **2 个是 QC 计算值、1 个是 Egashira 的实验值**，
且分别来自 Ref [3] / Ref [19] / Ref [15] 三个不同装置。结论不变：

- `n_pairs = 3 < 18` → 判据 1 仍不满足；
- 并且这种凑法**直接违反**判据 3 与核心文件 §15.2（"跨文献合并绝对值一律不得进入这一级"）。

### 4.3 因此

- 判据 1 **不满足** → 判据 2（`tau_b >= 0.9`）**不可判定**（无数据），而非"通过"或"不通过"。
- 所以：**排序一致性级本轮不能关闭，Gate 1 维持 NOT CLOSED（PARTIAL）**。

---

## 5. 为关闭 Gate 1 还缺什么（需要补充的文献条目）

按"拿到后能立刻构成同源序列"的可行性排序。**下表所有 DOI/题录均来自本仓库既有核验记录 [R]，
本轮未能联网复核**（见 `gate1_ref_online_check.json`）。

| 优先级 | 条目 | DOI | 类型 | 为什么需要 | 现状 |
| ---: | --- | --- | --- | --- | --- |
| 1 | Okoshi, Ishikawa, Kawamura & Nakai, *Theoretical Analysis of the Oxidation Potentials of Organic Electrolyte Solvents*, *ECS Electrochem. Lett.* **4**(9), A103–A105 (2015) | `10.1149/2.0051509eel` | **理论计算**（标题即 "Theoretical Analysis"） | 最可能一次性覆盖多个溶剂的**单一计算系列**；若覆盖 >=7 个核心集分子即可满足判据 1，但**只能算 calc 级**（见 §7 更正 1） | 元数据已核 [R]；正文付费墙，**数值未取到** |
| 2 | Ue et al., *J. Electrochem. Soc.* (1994) | `10.1149/1.2059270` | **实验**（四烷基铵盐体系） | 真正的**实验** within-series 候选 | 元数据已核 [R]；正文未取 |
| 3 | Ue et al., *J. Electrochem. Soc.* (1997) | `10.1149/1.1837882` | **实验** | 同上（同组另一篇，可能覆盖不同溶剂） | 元数据已核 [R]；正文未取 |
| 4 | Egashira et al., *J. Power Sources* **92**, 267–271 (2001) | `10.1016/S0378-7753(00)00553-X` | **实验**（Pt 微电极 100 µm，quasi-RE，1 M 铵盐，PC） | 装置/判据最明确；但**只覆盖 PC 单溶剂** | 代表作付费墙；同组 OA 短文已取得并校读 [R] → 确认多溶剂表在代表作里（付费墙） |
| 5 | Alvarado et al., *Mater. Today* **21**, 341–353 (2018) | 未核 | **实验**（carbonate-free sulfone 高浓体系） | SL 的上游；**只有 SL 一个核心集溶剂** | 仅从 Borodin2019 参考文献 [L] 定位 |
| 6 | Borodin, Behl & Jow, *J. Phys. Chem. C* **117**, 8661–8682 (2013) | 未核 | 计算 + LCV | EC/VC 的上游 | 仅从 Borodin2019 参考文献 [L] 定位 |
| 7 | Xing et al., *Electrochim. Acta* **133**, 117–122 (2014) | `10.1016/j.electacta.2014.03.190` | 实验 | SL 单值 ~5.0 V（**只有 1 个物种**） | 摘要逐字已录 [R] |
| 8 | Xu, Ding & Jow, *J. Electrochem. Soc.* **146**, 4172–4178 (1999) | `10.1149/1.1392609` | **方法学（不是数据源）** | 是"**不可跨文献合并绝对值**"的依据；应引用而非当数据 | 摘要逐字已录 [R] |

**关键缺口一句话**：目前缺的**不是**"再多几个单值"，而是**一份同一装置/同一判据下覆盖 >=7 个本文核心集溶剂的电位表**。
再多单溶剂文献都只会增加 `k = 1` 的序列，`n_pairs` 仍是 0。

---

## 6. 一旦拿到这类文献，应跑的最小分析（SOP，零新增电子结构）

> 全部复用已有产物（`outputs/week4/p1_core_set.csv`、`outputs/week4/p2_*`、
> `outputs/week5/c1_coord_shifts.csv`、`outputs/week9/stage10_ladder.json`），
> **不需要任何新的 QM 计算**。

1. **条件六字段先落盘**：把文献的 solvent / supporting_salt / concentration / temperature /
   reference_electrode / scan_conditions 逐行写入 `data/anchors/within_series_ordering.csv`
   （列名已冻结，目前仅表头）。每行必须带 `source_doi`、`provenance`、`verified_date`。
2. **同源过滤**：按 `series_id`（= 同一文献 + 同一装置/判据）分组，**跨 `series_id` 不合并**。
3. **映射到核心集**：按名/SMILES 把文献物种映射到 `data/metadata/core_set.csv` 的 `mol_id`；
   若某个 `series_id` 覆盖 < 7 个核心集分子，判据 1 自动不满足，**立即停止并如实报告**。
4. **算排序一致性**：在"两侧都有值"的 common-`k` 子集上，对每个台阶 `m ∈ {P0, P1, P2, C1}`
   计算 `Kendall tau_b` 与 `Spearman rho`（**P2 为主**：§15.2 规定 `R_sol` 审计 `P2`；
   其余台阶只作完备性展示，正是本轮外部评审建议的"降级版"用法）。
5. **不确定度**：成对 bootstrap 2000 次（复用 `config/prereg.yaml` 已冻结的种子），报 `tau_b` 的 95% CI；
   若 CI 跨 0.9，headline 必须改写为"未达显著"。
6. **判据复核**：`n_pairs >= 18` **且** `tau_b >= 0.9` **且** 单源 → 用
   `scripts/check_series_rel_ordering.py` 重跑，`anchors:series_rel_ordering` 由 NO 变 PASS，
   Gate 1 从 PARTIAL → CLOSED（降级版）；同步更新论文 §5 自查表与摘要措辞。
7. **三个"禁止"**（沿用既有纪律）：禁止跨 `series_id` 合并绝对值；禁止把实验 onset 当绝对标定；
   禁止用该锚点数据反推调参（anchors 是审计集，不是训练集）。

---

## 7. 与外部评审意见的两处更正（措辞纪律）

外部评审建议用"**Ue 等的系列测量**和 **Okoshi 2015 的 16 溶剂对照表**"来降级关闭 Gate 1。
方向是对的（within-series 相对排序确实是核心文件 §15.2 允许的降级路径），但有两处必须先更正：

1. **Okoshi 2015 不是实验测量**。其题录（[R]，2026-10-02 批次 C 经 Crossref 核验）为
   *Theoretical Analysis of the Oxidation Potentials of Organic Electrolyte Solvents*，
   属**理论计算**工作。若直接拿它充当 `R_sol`，会把 §15.3 的
   "experimentally anchored ranking decisions" 这句话变成无依据表述。
   正确做法：把它标为 **`R_sol`(calc) 级**并在报告里**单独成句**说明，它与实验锚点**不可互换**。
   "**16 溶剂**"这个数字本轮**未定位**（本地无该文，网络不可达），**不写、不用**。
2. **"Ue 等的系列测量"才是实验候选，但必须确认"同装置/同判据"**。据本仓库先前记录 [R]，
   Ue 1994 是**四烷基铵盐体系**，与本文核心集名义条件（neat solvent + 1 M LiPF6 + LSV）不同；
   因此它只能支撑"**Ue 体系内部的相对排序**"，**不能**升级为绝对标定。这一限制与
   Xu 1999 的警告（不同电极/装置测出的窗口不可比）完全一致。

此外必须与论文的物理叙事保持一致（外部评审 A5/A6 已指出）：本文 **P1 气相阴离子不束缚**，
所以**还原轴**的决策结论以 **P2/C1** 为载体；因此溶液锚点检验**应优先锚在 P2 的还原方向**，
而 P0→P1 的还原轴对比只作完备性展示。

---

## 8. 复现与产物

```text
# 本地 13 篇 PDF 清点（题录 / DOI / 关键词命中 / 溶剂名命中）
.venv\Scripts\python.exe scripts\audit_w24_gate1_literature.py
#   -> outputs/week24_corealign/gate1_literature_inventory.json
#   -> outputs/week24_corealign/gate1_solvent_name_hits.json

# 候选文献的在线元数据核验（本机网络不可达，本脚本会如实记录失败原因）
.venv\Scripts\python.exe scripts\verify_w24_gate1_refs.py
#   -> outputs/week24_corealign/gate1_ref_online_check.json

# Gate 1 排序一致性级的既有判定器（本轮未改动，仅用于核对判据名与口径）
.venv\Scripts\python.exe scripts\check_series_rel_ordering.py
```

产物：

| 文件 | 内容 |
| --- | --- |
| `outputs/week24_corealign/gate1_anchor_feasibility.md` | 本报告 |
| `outputs/week24_corealign/gate1_literature_inventory.json` | 13 篇本地 PDF 的机器可读清点结果 |
| `outputs/week24_corealign/gate1_solvent_name_hits.json` | §3.1 表 A 的可复现来源（溶剂名词边界命中；只表示被提及，不表示有电位值） |
| `outputs/week24_corealign/gate1_ref_online_check.json` | 在线核验尝试与"网络不可达"的如实记录（`network_reachable=false`） |
| `scripts/audit_w24_gate1_literature.py` | 生成本报告 §2 的只读脚本 |
| `scripts/verify_w24_gate1_refs.py` | 生成在线核验记录的只读脚本 |

## 9. 局限与诚实声明

1. **网络不可达**：本轮无法复核任何 DOI/摘要/正文；§5 的题录全部来自本仓库先前记录 [R]，
   标注为"已核"指的是**先前那一次**核验，不是本轮。
2. **"名称命中"含噪声**：§3.1 表 A 的命中数只说明"该文出现过这个字符串/缩写"，**不等于**讨论；
   本报告已把所有不能逐句确认语境的命中一律按"仅提及"处理。
3. **未做任何数值升级**：`data/anchors/solution_redox_anchors.csv` 的 31 行**一行未改**；
   即便 Borodin 2019 全文现在本地可读（其 EC/VC/SL 值可支撑把个别行从 `est` 提到 `calc`，
   **绝对标定级**），这也**不会**让排序一致性级变绿，因此本轮**刻意不动**，避免混淆两级证据。
4. **`k >= 7` 是判据 1 的等价换算**，不是新阈值；它由 `n_pairs = C(k,2) >= 18` 直接得出。
