# 溶液锚点核验记录与 within-series 判据（R7）

本文件承担两件事，且**顺序不可颠倒**：

1. **§1–§3 是预注册**（2026-10-02 写定并先行提交）：判据、阈值、比较单元、样本量下限。
   它们在任何 within-series 比对**之前**落盘，用 git 历史可审计（协议提交早于结果提交）。
   纪律依据：`config/prereg.yaml` §4「T 必须…在看结果之前写定」、
   「严禁看完数据后人为挑选一个最有利的阈值」。
2. **§4 起是核验结果**（后补）：三条线索的逐个核验判定、可入表的数值、以及核验失败的如实记录。

---

## 1. 为什么需要这一层（R7 的物理不对称）

实验 LSV/CV 测的是**纯溶剂电解液分解电流的 onset**，是一个**动力学量**；
本项目算的是**固定背景中完整物种的一电子热力学 proxy**。两者的桥接**只能停在排序层面**——
把实验 onset 当作绝对标定去校准计算绝对值，是没有物理依据的。因此 R7 把 Gate 1 拆成两级：

| 级别 | 内容 | 现状 |
| --- | --- | --- |
| **绝对标定级** | 本表 31 行的绝对电位可追溯到「条件匹配」的一次测量 | **承认为未达成**，写成 limitation |
| **排序一致性级** | within-series（同一来源、同一装置/判据）的相对排序与 target model 一致 | 由本文件 §2 的判据决定 |

「该条件组合（neat solvent + 1 M LiPF6 + 其自身分解 onset）下公开可比数据稀缺」本身是 findings，
不是本项目的疏漏。

## 2. 预注册判据（排序一致性级）

排序一致性级**关闭**当且仅当以下三条**同时**成立：

1. **样本量**：可用的 within-series 锚点对数 `n_pairs >= 18`。
   —— 直接沿用 `docs/31` R7 §3 已写定的下限，本次不重新选择。
2. **排序一致性**：target model 的 within-series 相对排序与实验序列的
   **Kendall τ_b >= 0.9**。
3. **同源**：参与比较的每一对必须来自**同一个来源序列**（同一篇文献 / 同一装置 / 同一判据）。
   跨文献合并绝对值一律不得进入这一级（依据线索 3）。

### 2.1 阈值登记（`config/prereg.yaml` §4 要求的 recorded_fields）

| 字段 | 值 |
| --- | --- |
| `T` | **0.9** |
| `objective_direction` | higher_is_better（τ_b 越大越一致；单侧） |
| `source_type` | pre_defined_engineering_standard |
| `source_reference` | `config/prereg.yaml` §2 `probabilistic_pair_ordering.thresholds.strong_i_gt_j = 0.9` —— 本文件不新造数字，直接复用已冻结的 strong 档 |
| `frozen_date` | 2026-10-02 |

**为什么是 0.9 而不是别的数**：0.9 是 prereg 里**已经冻结**的「strong」档；取它有两个好处——
(a) 不引入计划外的新阈值，(b) 它比 Week 21 σ 相图里用的参考线 0.8 **更严**，
因此不能用「把阈值放松到刚好通过」来解释任何结论。

## 3. 与 Gate 0 的关系

本文件**不修改** `config/prereg.yaml` 与 `config/scientific_definitions.yaml`，
因此 Gate 0 保持 CLOSED。若将来要把上述阈值写进 prereg，则必须走 `amendment_log`
并接受 Gate 0 变 NOT CLOSED（`docs/31` §5）。

## 4. 核验结果（2026-10-02，批次 C）

核验方式：直连 Crossref / OpenAlex / Semantic Scholar / OpenAIRE + J-Stage + Kobe 机构库。
环境事实：本机代理端口无监听；`archive.org` / `web.archive.org` 与 `google.com` 不可达（http 000）；
`iopscience.iop.org` 被 Radware bot manager 拦截（302 → `validate.perfdrive.com`）；
`syndication.highwire.org` 返回 403；Unpaywall 官方 API 因要求真实邮箱而返回 422，
改用 OpenAlex（与 Unpaywall 同源）判定 OA。
**本轮未修改 `data/anchors/solution_redox_anchors.csv` 的任何一行。**

### 4.1 逐条判定

| # | 线索 | 判定 | 解析出的 DOI |
| --- | --- | --- | --- |
| 1 | Okoshi et al. 2015, ECS Electrochem. Lett. | **FOUND（元数据全对）** / **数值 NOT RETRIEVABLE** | `10.1149/2.0051509eel` |
| 2 | Ue 等的实验系列 | **FOUND**（两篇，均为 J. Electrochem. Soc.） | `10.1149/1.2059270`（1994）/ `10.1149/1.1837882`（1997） |
| 3 | Egashira 课题组微电极系列 | **FOUND**（代表作 + 一篇 OA 全文已取到） | `10.1016/S0378-7753(00)00553-X` / `10.5796/electrochemistry.69.455` |
| 4 | Xu, Ding & Jow 1999, JES 146, 4172 | **FOUND** | `10.1149/1.1392609` |

**无 DOI-MISMATCH**：评审文案未给出 DOI，四条均由 Crossref 唯一匹配解析得到，
且与可取的独立书目佐证逐字一致（见下）。

#### 线索 1 —— Okoshi et al. 2015

- 标题：*Theoretical Analysis of the Oxidation Potentials of Organic Electrolyte Solvents*；
  作者 M. Okoshi, A. Ishikawa, Y. Kawamura, H. Nakai；
  **ECS Electrochemistry Letters 4(9), A103–A105**（2015-07-09；ISSN 2162-8726 / 2162-8734）；
  DOI `10.1149/2.0051509eel`。
- 独立书目佐证：Kobe 大学一篇 OA 论文的参考文献 24 逐字写作
  "M. Okoshi, A. Ishikawa, Y. Kawamura, and H. Nakai, ECS Electrochem. Lett. **4**, A103 (2015)."
- **数值取不到。** OpenAlex 标 `is_oa = True`（hybrid），Semantic Scholar 标 `CCBY`，
  摘要末段自述 CC BY 4.0；但**唯一的 OA 定位就是被 Radware 拦截的 IOP PDF**。
  尝试并失败的路径（8 条）：IOP PDF（302 → `validate.perfdrive.com`，0 字节）、
  Googlebot UA 访问 landing（302，0 字节）、Crossref 的 VOR 全文端点 `syndication.highwire.org`（403）、
  OpenAIRE（只回 DOI 链接，无镜像）、Semantic Scholar `openAccessPdf`（`status = CLOSED`）、
  J-Stage / arXiv / Kobe 机构库（均无镜像）、Wayback（本机不可达，无法从 ECS 原站取档）。
- **「16 个溶剂」这个数字本身也未核实**：摘要只写 "a wide variety of solvents"，未给出溶剂数；
  评审列出的 16 个缩写（APN GN BC EMC PC MA SFL EC NE MPN MAN DOL NMO DMF DMSO DMI）
  在本轮**无法从任何可达来源确认**，故**不作为事实登记**。

#### 线索 2 —— Ue 等的实验系列

- 主篇：Ue, Ida & Mori，**J. Electrochem. Soc. 1994, 141(11), 2989–2996**，DOI `10.1149/1.2059270`；
  摘要逐字自述测了 "limiting reduction and oxidation potentials for various organic liquid
  electrolytes based on quaternary onium salts"。OpenAlex 判 **closed**，无 OA 镜像。
- 续篇：Ue, Takeda, Takehara & Mori，**J. Electrochem. Soc. 1997, 144(8), 2684–2688**，
  DOI `10.1149/1.1837882`；OpenAlex 标 bronze，指向同一个被拦的 IOP PDF，**实际取不到**。
- 旁证（唯一能打开的同领域 OA 全文：Egashira 2001 *Electrochemistry* 69(6) 455）正文原文：
  > "Ue *et al.* showed the anodic stability data of various organic solvent electrolytes with
  > tetraalkylammonium cations. 9,10)"
  其 ref 9 / ref 10 正是上面两篇 → 支持「Ue 系列 = 四烷基铵盐 + 多有机溶剂的阳极稳定性标准数据」
  这一判断；但**工作电极材质、参比电极、支持电解质浓度、扫描速率/判据仍未核实**。

#### 线索 3 —— Egashira 课题组的微电极系列

- 代表作：Egashira, Takahashi, Okada & Yamaki，**J. Power Sources 2001, 92(1–2), 267–271**，
  DOI `10.1016/S0378-7753(00)00553-X`；**closed**，无镜像 —— 即微电极装置的出处。
- 同组 OA 全文（J-Stage PDF 已取到，201811 B）：
  Egashira, Okada & Yamaki，**Electrochemistry 2001, 69(6), 455–457**，
  DOI `10.5796/electrochemistry.69.455`。装置与判据逐字（该刊为扫描版，已按原文校读）：
  - 工作电极 "a platinum microelectrode (**100 µm in diameter**)"；
  - 参比 "Silver wire was used as a **quasi-reference electrode**"，部分条件下
    "Ag/0.05 mol dm-3 of AgNO3 in PC solution"；
  - 溶剂 PC（battery grade）；支持电解质 Et4NBF4 / Bu4NBF4 / Et3MeNBF4 / LiBF4，1 mol dm-3；
  - 技术 "19F-NMR spectroscopy and **linear sweep voltammogramography using microelectrodes**"；
    水分 "less than 30 ppm"（Karl-Fischer）。
- **但这一篇只覆盖 PC 单一溶剂**，不是多溶剂的氧化/还原电位系列表；
  多溶剂那张表在代表作里，仍是付费墙。

#### 线索 4 —— Xu, Ding & Jow 1999

- *Toward Reliable Values of Electrochemical Stability Limits for Electrolytes*；
  Kang Xu, Sheng P. Ding, T. Richard Jow（Army Research Laboratory, Electrochemistry Branch）；
  **J. Electrochem. Soc. 146(11), 4172–4178**（1999-11）；DOI **`10.1149/1.1392609`**。
- **DOI 陷阱（必须写全）**：若把末四位误写成 `2658`，`10.1149/1.1392658` 指向的是
  *Li-Chong Xu, Herbert H. P. Fang, Kwong-Yu Chan*, "Atomic Force Microscopy Study of
  Microbiologically Influenced Corrosion of Mild Steel", **JES 146(12) 4455–4460 (1999)** ——
  作者姓氏同为 Xu，内容完全无关。
- 定位：**不是数据源，是「为什么不能跨文献合并绝对值」的方法学依据**。摘要逐字：
  "We scrutinized the conventional practice of measuring an electrolyte stability window.
  It is shown that misleading values might be generated by this practice. Thus, we recommend
  that to obtain a real stability window, the working electrode material should simulate the
  electrodes used in a real device."

### 4.2 本地已持有 PDF 的复查（本轮补做）

除在线核验外，本轮还把本机可访问的 13 篇 PDF（`核心文件/文献/分支a-d/` 7 篇 +
`核心文件/文献/新建文件夹/` 6 篇）全文抽出，逐篇检索是否存在**同源多溶剂氧化/还原电位数值表**。
结论：**没有**。命中最接近的两篇是

- `M5-Borodin-2019-electrolyte-stability-window.pdf` = **Borodin 2019 综述**（*Challenges with prediction of
  battery electrolyte electrochemical stability window and guiding the electrode–electrolyte
  stabilization*）—— 只讨论 EC / SL / FEC / Li-SL 的分解路径与「HOMO–LUMO ≠ 窗口」，
  未给多溶剂数值表；
- `C2-solvation-structure-interface-2022.pdf` = Cheng et al., *ACS Energy Lett.* 2022, 7, 490−513（溶剂化结构综述）——
  该文出现的数字是配位数/摩尔比（如 Li⁺[PC]₁₂.₆、Li⁺[TEGDME]₄.₄₆），**不是**氧化电位。

因此**本轮的 within-series 数值表在本地与线上都取不到**。

### 4.3 本轮对 §2 判据的裁定

| 判据 | 实际值 | 判定 |
| --- | --- | --- |
| 1. `n_pairs >= 18` | **0**（无一条可核验的 within-series 数值） | **不满足** |
| 2. `tau_b >= 0.9` | 未计算（无数据） | **不可判定** |
| 3. 每一对同源 | —— | 无对可查 |

→ **排序一致性级本轮不能关闭，Gate 1 维持 NOT CLOSED。**
`data/anchors/solution_redox_anchors.csv` **一行未改**（31 行仍为 `method=est`、`uncertainty_V=0.5`）。

**解锁路径（按可行性排序）**：

1. 机构订阅 IOP/ECS，取 Okoshi 2015 正文表（该文是 **CC BY 4.0**，订阅后可合法复制入表）；
2. 取 Ue 1994 JES 141 2989 正文表（多溶剂极限氧化电位）；
3. 取 Xu 1999 JES 146 4172 全文（同样 bronze OA，被同一层反爬挡住）；
4. 向作者索取（Okoshi / H. Nakai 组；Ue 本人）。

**先例纪律**：`docs/13_week6_report.md:233` 记录过一次误配 —— CSV 里的 `10.1149/1.1838419`
原写作「Ue et al.」，核验后实为 **Xu & Angell, JES 145, L70–L72 (1998)**，讲的是非环脂肪砜。
本轮四条线索**全部先验卷期页码再判定**，未重犯该错；
但也正因为坚持「先验数值、再入库」，**一条都没有写入 CSV**。

### 4.4 与绝对标定级的关系

绝对标定级**承认为未达成**（31 行仍为 `est`），理由与 `docs/06` 一致；本轮新增一条硬证据：
线索 1/2/3 的**测量条件本身就跨文献不同**（Ue = 四烷基铵盐体系；Egashira = 1 M 铵盐 / PC /
Pt 微电极；经典 CV 系列 = 稀碳酸酯 / THF / 惰性电极），正是 Xu 1999 警告的那种
「不能合并成单一绝对 benchmark」的情形。该条目按 `docs/31` §5 登记为 **limitation**；
排序一致性级另立一条 blocker（见 §4.3）。
