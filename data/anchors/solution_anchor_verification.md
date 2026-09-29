# 溶液相 redox 锚点逐行核验记录（`data/anchors/solution_redox_anchors.csv`）

- 核验日期：2026-09-29
- 核验人：anchor-curator (Codex)
- 离线复算脚本：`scripts/audit_solution_anchors.py`（可在无网络下重跑）
- 机器可读审计：`outputs/week2/solution_anchor_audit.csv` + `outputs/week2/solution_anchor_audit.json`
- 结论摘要：**31 / 31 行经核验后仍为 `est`；0 行升级为 `exp` / `calc`。**

> 本文件只记录“核验后发生了什么”。核验的价值在于：把这 31 行从“未核验的估算”变为
> “已核验并记录失败原因的估算”，并为每一行给出放大后的不确定度。绝不为了让 Gate 1 变绿
> 而把行改成 `exp`。

## 1. 核验方法与可达性

核验分两步：

1. **来源级核验**：用 Crossref / OpenAlex / Unpaywall 逐条核对 `source_note` 里出现的 DOI，
   确认题录（标题 / 期刊 / 年份）匹配、是否能检索到该物种的数值、以及原文的实验条件。
2. **行级判定**：对每一行判断“是否能找到**明确给出该物种**在**明确实验条件**下的氧化或还原
   电位，并有可追溯标识”。判定只允许 `exp` / `calc` / `est` 三种。

网络可达性（本次实测）：

| 站点 | 结果 |
| --- | --- |
| `api.crossref.org` | 可达（题录/年份/期刊核对成功） |
| `api.openalex.org` | 可达（多数条目可取到摘要） |
| `api.unpaywall.org` | 可达（可定位 OA 副本位置） |
| `iopscience.iop.org`（JES / Nanotechnology 正文） | **被 Radware Bot Manager 拦截**（CAPTCHA），正文不可取 |
| `www.osti.gov`、`www.ncbi.nlm.nih.gov` | **TLS/SSL 连接失败**，不可取 |
| `www.nature.com`、`iris.unimore.it` | **Cloudflare 挑战**，正文不可取 |
| `www.repository.cam.ac.uk` | 可达（成功下载 Michan 2016 全文 PDF 并检索） |

## 2. 逐行证据表

表中“核验来源”列给出该行 `source_note` 指向的 DOI；“可回溯”指该 DOI 是否提供了**与行内条件
一致、可直接引用的数值**（不是指 DOI 是否存在）。

| 行号 | mol_id | 物种 | 性质 | 原值 (V) | 原 unc (V) | 核验结论 | 证据类别 | 核验来源 (DOI) | 可回溯 | 失败原因 |
| ---: | --- | --- | --- | ---: | ---: | --- | --- | --- | --- | --- |
| 1 | C04 | EC | 还原 | 0.9 | 0.3 | `est` | `condition_mismatch` | 10.1149/1.1415547; 10.1088/0957-4484/26/35/354003 | 否 | 原始测量条件与行内条件不符（THF 稀溶液 CV ≠ 纯溶剂 / 1 M LiPF6 / LSV），且具体数值不可得 |
| 2 | C05 | PC | 还原 | 1 | 0.3 | `est` | `condition_mismatch` | 10.1149/1.1415547; 10.1088/0957-4484/26/35/354003 | 否 | 原始测量条件与行内条件不符（THF 稀溶液 CV ≠ 纯溶剂 / 1 M LiPF6 / LSV），且具体数值不可得 |
| 3 | C01 | DMC | 还原 | 1 | 0.3 | `est` | `condition_mismatch` | 10.1149/1.1415547; 10.1088/0957-4484/26/35/354003 | 否 | 原始测量条件与行内条件不符（THF 稀溶液 CV ≠ 纯溶剂 / 1 M LiPF6 / LSV），且具体数值不可得 |
| 4 | C02 | EMC | 还原 | 1 | 0.3 | `est` | `source_does_not_cover_species` | 10.1149/1.1415547; 10.1088/0957-4484/26/35/354003 | 否 | 所引原始文献未覆盖该物种（其五种碳酸酯不含 EMC） |
| 5 | C03 | DEC | 还原 | 1 | 0.3 | `est` | `condition_mismatch` | 10.1149/1.1415547; 10.1088/0957-4484/26/35/354003 | 否 | 原始测量条件与行内条件不符（THF 稀溶液 CV ≠ 纯溶剂 / 1 M LiPF6 / LSV），且具体数值不可得 |
| 6 | C06 | FEC | 还原 | 1.3 | 0.4 | `est` | `source_does_not_provide_value` | 10.1021/acs.chemmater.6b02282; 10.1016/j.jpowsour.2006.07.074 | 否 | 所引文献只表征还原产物，未给出该电位数值 |
| 7 | C07 | VC | 还原 | 1.4 | 0.4 | `est` | `condition_mismatch` | 10.1149/1.1415547; 10.1021/acs.chemmater.6b02282 | 否 | 原始测量条件与行内条件不符（THF 稀溶液 CV ≠ 纯溶剂 / 1 M LiPF6 / LSV），且具体数值不可得 |
| 8 | C08 | DME | 还原 | 1 | 0.3 | `est` | `computational_not_retrieved` | 10.1088/0957-4484/26/35/354003 | 否 | 仅有计算型来源，且其逐溶剂具体数值不可得 |
| 9 | C09 | DOL | 还原 | 1.1 | 0.3 | `est` | `computational_not_retrieved` | 10.1088/0957-4484/26/35/354003 | 否 | 仅有计算型来源，且其逐溶剂具体数值不可得 |
| 10 | C11 | EA | 还原 | 1 | 0.4 | `est` | `computational_not_retrieved` | 10.1088/0957-4484/26/35/354003 | 否 | 仅有计算型来源，且其逐溶剂具体数值不可得 |
| 11 | C12 | MA | 还原 | 1 | 0.4 | `est` | `computational_not_retrieved` | 10.1088/0957-4484/26/35/354003 | 否 | 仅有计算型来源，且其逐溶剂具体数值不可得 |
| 12 | C13 | GBL | 还原 | 0.9 | 0.3 | `est` | `computational_not_retrieved` | 10.1088/0957-4484/26/35/354003 | 否 | 仅有计算型来源，且其逐溶剂具体数值不可得 |
| 13 | C14 | SL | 还原 | 0.9 | 0.3 | `est` | `mis_citation` | 10.1149/1.1838419 | 否 | 引用文献研究对象错配：其为非环状不对称砜，而非目标物种 |
| 14 | C15 | DMSO | 还原 | 1.2 | 0.5 | `est` | `review_trend_only` | 10.1016/j.coelec.2018.10.015 | 否 | 仅二手综述/趋势，无法回溯到原始测量 |
| 15 | C16 | AN | 还原 | 1 | 0.5 | `est` | `review_trend_only` | 10.1016/j.coelec.2018.10.015 | 否 | 仅二手综述/趋势，无法回溯到原始测量 |
| 16 | C17 | TMP | 还原 | 1.2 | 0.4 | `est` | `no_reference` | — | 否 | source_note 未给出任何可核对来源 |
| 17 | C04 | EC | 氧化 | 4.5 | 0.5 | `est` | `solvent_anion_coupling` | 10.1038/s41467-019-11317-3; 10.1016/j.coelec.2018.10.015 | 否 | 真实氧化为溶剂–阴离子耦合过程，孤立溶剂值仅为上界式参考 |
| 18 | C05 | PC | 氧化 | 4.6 | 0.5 | `est` | `solvent_anion_coupling` | 10.1038/s41467-019-11317-3; 10.1016/j.coelec.2018.10.015 | 否 | 真实氧化为溶剂–阴离子耦合过程，孤立溶剂值仅为上界式参考 |
| 19 | C01 | DMC | 氧化 | 4.5 | 0.5 | `est` | `solvent_anion_coupling` | 10.1038/s41467-019-11317-3; 10.1016/j.coelec.2018.10.015 | 否 | 真实氧化为溶剂–阴离子耦合过程，孤立溶剂值仅为上界式参考 |
| 20 | C02 | EMC | 氧化 | 4.5 | 0.5 | `est` | `solvent_anion_coupling` | 10.1038/s41467-019-11317-3; 10.1016/j.coelec.2018.10.015 | 否 | 真实氧化为溶剂–阴离子耦合过程，孤立溶剂值仅为上界式参考 |
| 21 | C03 | DEC | 氧化 | 4.5 | 0.5 | `est` | `solvent_anion_coupling` | 10.1038/s41467-019-11317-3; 10.1016/j.coelec.2018.10.015 | 否 | 真实氧化为溶剂–阴离子耦合过程，孤立溶剂值仅为上界式参考 |
| 22 | C06 | FEC | 氧化 | 4.7 | 0.5 | `est` | `solvent_anion_coupling` | 10.1038/s41467-019-11317-3; 10.1016/j.coelec.2018.10.015 | 否 | 真实氧化为溶剂–阴离子耦合过程，孤立溶剂值仅为上界式参考 |
| 23 | C07 | VC | 氧化 | 4.5 | 0.5 | `est` | `solvent_anion_coupling` | 10.1038/s41467-019-11317-3; 10.1016/j.coelec.2018.10.015 | 否 | 真实氧化为溶剂–阴离子耦合过程，孤立溶剂值仅为上界式参考 |
| 24 | C08 | DME | 氧化 | 4 | 0.5 | `est` | `review_trend_only` | 10.1016/j.coelec.2018.10.015 | 否 | 仅二手综述/趋势，无法回溯到原始测量 |
| 25 | C09 | DOL | 氧化 | 4.1 | 0.5 | `est` | `review_trend_only` | 10.1016/j.coelec.2018.10.015 | 否 | 仅二手综述/趋势，无法回溯到原始测量 |
| 26 | C11 | EA | 氧化 | 4.4 | 0.5 | `est` | `no_reference` | — | 否 | source_note 未给出任何可核对来源 |
| 27 | C13 | GBL | 氧化 | 4.5 | 0.5 | `est` | `no_reference` | — | 否 | source_note 未给出任何可核对来源 |
| 28 | C14 | SL | 氧化 | 4.9 | 0.5 | `est` | `mis_citation` | 10.1149/1.1838419 | 否 | 引用文献研究对象错配：其为非环状不对称砜，而非目标物种 |
| 29 | C15 | DMSO | 氧化 | 4.3 | 0.4 | `est` | `no_reference` | — | 否 | source_note 未给出任何可核对来源 |
| 30 | C16 | AN | 氧化 | 4.7 | 0.5 | `est` | `review_trend_only` | 10.1016/j.jpowsour.2006.07.074 | 否 | 仅二手综述/趋势，无法回溯到原始测量 |
| 31 | C17 | TMP | 氧化 | 4.6 | 0.5 | `est` | `no_reference` | — | 否 | source_note 未给出任何可核对来源 |

## 3. 引用来源核验结果（来源级）

| DOI | 简写 | 可解析 | 覆盖物种/对象 | 是否提供条件一致的可引数值 | 备注 |
| --- | --- | --- | --- | --- | --- |
| `10.1149/1.1415547` | Zhang & Kostecki, J. Electrochem. Soc. 2001 | 是 | EC / PC / DMC / DEC / VC | 否 | CV reduction potentials of five carbonates (EC, PC, DEC, DMC, VC) on inert (Au / glassy carbon) electrodes in THF with a supporting electrolyte - NOT the neat solvent / 1 M LiPF6 / LSV conditions of the CSV rows. The abstract only states the five values are 'above 1 V'; exact tabulated potentials were not retrievable (publisher bot-block). |
| `10.1088/0957-4484/26/35/354003` | Borodin et al., Nanotechnology 2015 | 是 | carbonates / phosphates / ethers / esters | 否 | DFT screening of ISOLATED solvents surrounded by an implicit solvent; reports first/second reduction and oxidation stability. A calc-type source, not an experiment; exact per-solvent numbers were not retrievable (publisher bot-block). |
| `10.1021/acs.chemmater.6b02282` | Michan et al., Chem. Mater. 2016 | 是 | FEC / VC | 否 | Characterises FEC/VC reduction PRODUCTS obtained by chemical reduction with lithium naphthalenide (XPS/NMR) plus DFT; the retrieved full text reports no electrochemical reduction potential vs Li/Li+ (no 'V vs Li' value occurs). |
| `10.1016/j.jpowsour.2006.07.074` | Zhang, J. Power Sources 2006 | 是 | additives / AN | 否 | Secondary review of additives; no condition-controlled per-solvent potential table. |
| `10.1016/j.coelec.2018.10.015` | Borodin, Curr. Opin. Electrochem. 2019 | 是 | solvents | 否 | Discussion/review of the pitfalls of predicting stability windows; gives trends rather than a single quotable per-solvent value. |
| `10.1038/s41467-019-11317-3` | Fadel et al., Nat. Commun. 2019 | 是 | solvent-anion complexes | 否 | Shows electrolyte oxidation is a solvent-anion charge-transfer process; the oxidation potential of the ISOLATED solvent is only an upper-bound-like guideline, not a directly measured quantity. |
| `10.1149/1.1838419` | Ue et al., J. Electrochem. Soc. 1998 | 是 | ethyl methyl sulfone (unsymmetric noncyclic sulfone) | 否 | Concerns an UNSYMMETRIC NONCYCLIC aliphatic sulfone, not the cyclic sulfone sulfolane; reports a 5.8 V anodic limit for that other solvent, so it does not support a sulfolane reduction or oxidation value. |

## 4. 不确定度放大规则

对**保留 `est`** 的行，按如下确定性规则放大不确定度（见 `scripts/audit_solution_anchors.py`）：

- 还原行：`新 unc = min(原 unc + 0.2, 0.8)`
- 氧化行：`新 unc = min(原 unc + 0.3, 0.8)`（额外 +0.1 反映溶剂–阴离子耦合的结构性误差）

规则作用于 `BASE_UNCERTAINTY`（核验前原值），而非 CSV 当前值，因此可重复运行且不变。

| 性质 | 原 unc (V) | 新 unc (V) | 行数 |
| --- | ---: | ---: | ---: |
| 氧化 | 0.4 | 0.7 | 1 |
| 氧化 | 0.5 | 0.8 | 14 |
| 还原 | 0.3 | 0.5 | 9 |
| 还原 | 0.4 | 0.6 | 5 |
| 还原 | 0.5 | 0.7 | 2 |

还原行共 16，氧化行共 15。

## 5. 诚实声明

- 这 31 行**仍然不是**任何单一文献的直接引用值；它们依旧只能用于“量级 / 相对排序”级别的方法
  审计，不能作为绝对 benchmark，也不能用于 pooled absolute regression。
- `doi` 列继续保持**全部为空**：按仓库约定，`doi` 非空意味着“数值可回溯到该文献”，当前不成立。
- 核验**没有**发现任何一行可以在行内声明的条件（纯溶剂 / 1 M LiPF6 / LSV / vs Li/Li+）下被
  逐字回溯；相反，核验暴露了两处引用问题（sulfolane 的引用对象错配；EC 还原 0.9 V 与所引
  文献“>1 V”的表述冲突），这些都记录在对应行的 `source_note` 中。

