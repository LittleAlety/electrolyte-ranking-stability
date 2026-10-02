# External reference anchors （对应 v2 §3.3 Axis C / §15 / §19 Stage 1）

本目录保存 **外部参考锚点（external reference anchors）**，用于把「model-to-model 的排序保持」
与「是否更接近真实可观测量」分开。

- `R_gas` → `gas_phase_anchors.csv`：气相电离能 IP / 电子亲和能 EA。
- `R_sol` → `solution_redox_anchors.csv`：溶液相氧化/还原电位。
- `R_env`（Li 配位 / explicit microsolvation 的定性锚点）本阶段 **未** 在本目录提供数值数据；
  使用方法见 `docs/01_stage1_external_anchors.md` §5。

校验脚本：`scripts/validate_anchors.py`（仅用 Python 标准库；仓库 README 的「快速开始」第 3 步）。

```text
.venv\Scripts\python.exe scripts\validate_anchors.py
```

与冻结配置的关系：

- 结构定义见 `config/scientific_definitions.yaml` 的 `axis_C_external_reference`
  （`R_gas` / `R_sol` / `R_env` 的审计对象与条件字段）；
- `delta_m` 的来源规则见 `config/prereg.yaml` 的 `pair_comparison.delta_m.source_rule`，
  其中第 (1) 条正是「外部 anchor 数据自身的实验离散度」。

---

## 1. 可信度分级（最重要，请先读）

本项目对每一行的 **可信度** 做显式标记，绝不把估算值伪装成文献测量值。

### 1.1 `gas_phase_anchors.csv`（共 39 行 / 26 个物种）

| 类别 | `source_type` | 行数 | 含义 |
| --- | --- | ---: | --- |
| curated-literature | `nist_webbook` | 27 | 来自 NIST Chemistry WebBook (SRD 69) 的 **实验** 气相离子能量学数据，逐条抓取核对 |
| curated-literature | `high_level_calc` | 2 | 来自 Fadel et al. 2019 (Nat. Commun.) 的 DLPNO-CCSD(T) 计算值 |
| curated-literature | `unbound_anion`（有值） | 1 | CO2 EA = −0.60 eV，NIST 明确标注为 unbound 的负值 |
| **待核 / 缺口** | `unbound_anion`（空值） | 6 | 判定「气相自由基阴离子不束缚」，**故意不填数值** |
| **待核 / 缺口** | `not_curated`（空值） | 3 | NIST 无该物种条目，**故意不填数值** |

> 结论：气相表中 **有数值的 30 行全部是 curated-literature**；其余 9 行是 **显式的空缺**，
> 不存在 estimated 数值。空缺处一律留空，而不是编造。

### 1.2 `solution_redox_anchors.csv`（共 31 行 / 16 个物种）

| 类别 | `method` | 行数 | 含义 |
| --- | --- | ---: | --- |
| **estimated（已核验）** | `est` | 31 | 文献趋势 **估算**，**不是** 任何单一文献的直接引用值；`doi` 一列 **全部留空**。2026-09-29 已逐行核验，**仍未升级** |
| curated-literature | `exp` / `calc` | 0 | 核验后 **仍没有** 找到可确证、条件统一、可直接引用的实验溶液相 redox 表 |

> 诚实声明：**溶液相表当前 100% 是 estimated（31 / 31 行）**。2026-09-29 的逐行核验（证据表见
> `data/anchors/solution_anchor_verification.md`，报告见 `docs/06_stage1_solution_anchor_audit.md`，
> 机器可读审计见 `outputs/week2/solution_anchor_audit.csv` / `.json`）把每一行从「未核验的估算」
> 变为「已核验、失败原因已记录、不确定度已放大（还原 +0.2 V、氧化 +0.3 V，上限 0.8 V）的估算」，
> 但 **没有任何一行升级为 `exp` / `calc`**：所引来源要么是二手综述 / 零散趋势，要么是计算型筛选，
> 要么其原始测量条件（如稀碳酸酯 / THF / CV）与行内条件（纯溶剂 / 1 M LiPF6 / LSV）不符，
> 且部分正文因站点反爬 / TLS 失败不可取。因此 `doi` 列 **继续全部留空**，本表只能用于
> 「量级 / 相对排序」级别的方法审计，**不能** 当作绝对 benchmark，也 **不能** 用于 pooled absolute regression。
> 每一行的 `source_note` 现同时写明「已尝试核验」与「失败原因」。该核验 **没有** 关闭 Gate 1
> （`method=est` 行数仍为 31）。

### 1.3 总计

- curated-literature：**30 行**（全部在 `gas_phase_anchors.csv`）
- estimated：**31 行**（全部在 `solution_redox_anchors.csv`）
- 待核 / 显式空缺：**9 行**（`gas_phase_anchors.csv`，值为空）

### 1.4 `within_series_ordering.csv`（R7，2026-10-02 新增）

- **当前为 0 行**（只有表头）。这不是遗漏，是核验结果。
- 用途：Gate 1 的**排序一致性级**（`scripts/check_series_rel_ordering.py`）只从这张表取
  within-series 锚点对。`solution_redox_anchors.csv` 的 31 行 `est` 不再直接当 blocker，
  而是按 `docs/31` R7 记为 limitation。
- 为什么是空的：2026-10-02 的 batch C 核验把 `docs/31` R7 的四条线索全部解析到了唯一 DOI
  （见 `data/anchors/solution_anchor_verification.md` §4.1 与
  `scripts/audit_solution_anchors.py` 的 `SOURCES`），但**没有一条能给出可逐条引用的
  within-series 数值**：Okoshi 2015 与 Ue 1994/1997 的表都在 IOP 付费墙之后（本机被
  Radware bot manager 拦截），唯一公开可取的同领域全文只覆盖 PC 单溶剂。
  预注册判据要求 `n_pairs >= 18`，实际 `n_pairs = 0`。
- 填表规则：一行 = 一个（来源序列, 物种, 性质）的已核验数值；`series_id` 相同的行才会互相配对，
  `source_doi` 必须指向该序列本身（**禁止跨文献拼接绝对值**）。列定义见 §2.6。

---

## 2. 编码约定

### 2.1 通用

- 文件为 UTF-8、RFC4180 CSV，含表头行。
- **单位写进列名后缀**：`*_eV`（电子伏）、`*_V`（伏）、`*_K`（开尔文）。
  脚本据此校验，不允许把单位写进单元格。
- 缺值一律 **留空字符串**，不要写 `NA` / `-` / `n/a`。允许为空的列见 §2.5。
- **`doi` 的语义是「本行数值的来源 DOI」**。若数值不是该文献的直接引用值，则 **必须留空**，
  只在 `source_note` 里以文字形式给出「建议核对来源 doi:...」。
  这条约定保证 `doi` 非空 ⇒ 数值可回溯。
- `species` 的命名规则见 §3（对齐 `data/metadata/core_set.csv` 的 `name`）。

### 2.2 `gas_phase_anchors.csv`

列：`species, smiles, property, value_eV, uncertainty_eV, method, source_type, doi, source_note, curated_by`

- `property` ∈ `IP` | `EA`
- `method` ∈ `exp` | `calc` | `est` | `na`（`na` 仅用于空值行）
- `source_type` ∈ `nist_webbook` | `high_level_calc` | `experimental_literature` |
  `literature_estimate` | `unbound_anion` | `not_curated` | `reference_list`
- NIST 行的 `doi` 统一为 NIST WebBook 的 DOI：`10.18434/T4D303`
  （NIST Chemistry WebBook, NIST Standard Reference Database 69；DataCite 已核验）。
- NIST 网页 **未给出不确定度** 时，采用保守默认 `±0.10 eV`，并在 `source_note` 注明。
- `not_curated` / `unbound_anion` 的空值行：`value_eV`、`uncertainty_eV` 留空。

### 2.3 `solution_redox_anchors.csv`

列：`species, smiles, property, value_V, reference_electrode, solvent, electrolyte_note, temperature_K, method, uncertainty_V, doi, source_note`

- `property` ∈ `oxidation_potential` | `reduction_potential`
- `reference_electrode` ∈ `Li/Li+` | `Fc/Fc+` | `SCE` | `Ag/Ag+`（当前全部为 `Li/Li+`）
- `method` ∈ `exp` | `calc` | `est`

**条件字段的落位**（`config/scientific_definitions.yaml` 的 `R_sol.condition_fields`
要求 `solvent, supporting_salt, concentration, temperature, reference_electrode, scan_conditions`
六项都必须保存）：

| condition field | 落在哪一列 |
| --- | --- |
| `solvent` | `solvent`（`<缩写> (neat)` 表示该电位指纯溶剂的 **本征** 行为） |
| `supporting_salt` | `electrolyte_note`（`supporting_salt=...`） |
| `concentration` | `electrolyte_note`（`concentration=...`） |
| `scan_conditions` | `electrolyte_note`（`scan_conditions=...`） |
| `temperature` | `temperature_K` |
| `reference_electrode` | `reference_electrode` |

**单位换算约定**（`config/scientific_definitions.yaml` 的 `thermochemistry.units_policy` 要求：
若换算为 V，必须记录换算常数与 reference electrode）。本表每一行的 `source_note` 末尾都带：

```text
| unit convention: reference electrode Li/Li+ (1 M Li+, 298.15 K); 1 V = 96.485 kJ/mol (F = 96485.33212 C/mol)
```

- 项目 **主报告量** 是自由能差 (kJ/mol)；本表用 V 只是为了与实验电化学文献对照。
- **不同实验系列的绝对电位不可直接合并**（v2 §15.2，`R_sol.pooling_rule`）。
  本表全部为同一参考电极、同一温度的 **估算** 值，仅用于 **同一表内相对排序** 的定性审计。

### 2.4 数值合理区间（校验脚本强制）

| 物理量 | 允许区间 | 说明 |
| --- | --- | --- |
| `IP`（`value_eV`） | 5.0 – 15.0 | 覆盖 H2O 12.62 / CO2 13.78 到 DME 9.30 |
| `EA`（`value_eV`） | −3.0 – 5.0 | 允许负值（unbound anion，如 CO2 −0.60） |
| `reduction_potential` vs `Li/Li+` | −0.50 – 3.00 | |
| `oxidation_potential` vs `Li/Li+` | 2.50 – 6.50 | |
| `Fc/Fc+` / `SCE` / `Ag/Ag+`（任意 property） | −3.00 – 3.50 | 相对参比，窗口更窄 |
| `temperature_K` | 200 – 400 | |
| `uncertainty_eV` / `uncertainty_V` | ≥ 0 | |

### 2.5 允许为空的列

- `gas_phase_anchors.csv`：仅当 `source_type` ∈ {`unbound_anion`, `not_curated`} 时，
  `value_eV` / `uncertainty_eV` 允许为空。
- `solution_redox_anchors.csv`：`doi` 允许为空（estimated 行必须为空）。

---

### 2.6 `within_series_ordering.csv`

| 列 | 含义 |
| --- | --- |
| `series_id` | 来源序列 ID；只有同 ID 的行会互相配对，「同源」要求由它保证 |
| `source_doi` | 该序列本身的 DOI，必须形如 `10.…`；无源的估值不许写进这张表 |
| `species` | 物种名，须与 `outputs/week4/p1_core_set_derived.csv` 的 `name` 一致 |
| `property` | `oxidation_potential` 或 `reduction_potential` |
| `value_V` | 该序列内的实测电位（同一序列内同一参比） |
| `uncertainty_V` | 可选；本表判据不用它，但便于将来加权 |
| `reference_electrode` | 可选；只作记录，不参与跨序列合并 |
| `provenance` | 自由文本：装置 / 判据 / 表号 |
| `verified_date` | 核验日期 |

模型侧的排序键沿用全项目自 Week 4 起的 P1 口径（`p1_ox_ev` / `p1_red_ev`，越大越稳定），
与实验电位的取向一致。

## 3. 物种命名与对照表

`species` 一列的规则：**凡是 `data/metadata/core_set.csv` 中已有的分子，一律使用其
`name` 字段（EC / DMC / …）**，以便直接用 `species` ↔ `core_set.name` 对齐做方法审计；
不在 core set 中的分子用通用简写或全名。SMILES 与 `core_set.csv` 化学等价
（字符串表示可能不同，例如 EC 写作 `O=C1OCCO1` vs `C1COC(=O)O1`）。

| species | 全名 | core_set `mol_id` |
| --- | --- | --- |
| `EC` | ethylene carbonate | C04 |
| `PC` | propylene carbonate | C05 |
| `DMC` | dimethyl carbonate | C01 |
| `EMC` | ethyl methyl carbonate | C02 |
| `DEC` | diethyl carbonate | C03 |
| `FEC` | fluoroethylene carbonate | C06 |
| `VC` | vinylene carbonate | C07 |
| `DME` | 1,2-dimethoxyethane | C08 |
| `DOL` | 1,3-dioxolane | C09 |
| `EA` | ethyl acetate | C11 |
| `MA` | methyl acetate | C12 |
| `GBL` | gamma-butyrolactone | C13 |
| `SL` | sulfolane | C14 |
| `DMSO` | dimethyl sulfoxide | C15 |
| `AN` | acetonitrile | C16 |
| `TMP` | trimethyl phosphate | C17 |
| `THF` | tetrahydrofuran | （不在 core set，仅作气相锚点） |
| `water` / `methanol` | H2O / CH3OH | （仅作 sanity anchor） |
| `carbon dioxide` / `sulfur dioxide` / `nitrogen dioxide` / `oxygen` | CO2 / SO2 / NO2 / O2 | （仅作 sanity / EA anchor） |
| `hexafluorobenzene` / `benzene` / `pyridine` | C6F6 / C6H6 / C5H5N | （仅作 sanity anchor） |
| `bis(trifluoromethanesulfonyl)imide anion` | TFSI⁻（LiTFSI 阴离子） | （盐阴离子参照） |

---

## 4. 需要人工核对的行（curator 建议，按优先级）

1. `gas_phase_anchors.csv` → **VC IP = 10.08 eV**
   NIST 同时收录 `11.91 eV`（Bain & Frost 1973），两者相差 1.8 eV，必属两者之一有问题。
2. `gas_phase_anchors.csv` → **DME IP = 9.30 eV**
   与 Fadel et al. 2019 正文引用的「experimental 9.8 eV」冲突，需确认是 vertical vs adiabatic
   还是不同电子态。
3. `gas_phase_anchors.csv` → **PC / DEC / EMC（`source_type=not_curated`，值为空）**
   NIST 无气相离子能量学条目；需另找实验源，或改用高等级计算并改 `source_type`。
4. `gas_phase_anchors.csv` → **EC / PC / DMC / DME / DOL / THF 的 EA 空值行**
   「气相自由基阴离子不束缚」是化学常识 + v2 的 `unbound_anion` 情形，但本仓库 **未** 逐条附
   electron-transmission / DEA 文献；正式使用前应补引用。
5. `solution_redox_anchors.csv` → **全部 31 行：已于 2026-09-29 完成逐行核验，结论是全部保留 `est`**
   核验**未**找到可确证、条件统一、可直接引用的原始实验表格，故没有一行升级（逐行证据：
   `data/anchors/solution_anchor_verification.md`；报告：`docs/06_stage1_solution_anchor_audit.md`）。
   核验中发现两处**引用错配**，后续若再找来源必须先解决：
   - **SL（sulfolane）两行**：所引 `10.1149/1.1838419` 研究的是**非环状不对称砜**，不是环状 sulfolane；
   - **EC 还原 0.9 V**：所引 `10.1149/1.1415547` 实为 THF 稀溶液 CV，与行内「纯溶剂 / 1 M LiPF6 / LSV」不符。
   最可疑的两类仍是 **oxidation_potential**（真实体系是 solvent–anion 耦合氧化，孤立溶剂值只作上界式参考）
   与 **DMSO / AN 的 reduction_potential**。详见 `docs/06` §3。
6. `solution_redox_anchors.csv` → `reference_electrode` 当前只有 `Li/Li+`。
   若要并入 `Fc/Fc+` 系列，必须同时给出换算依据与不确定度，禁止直接相加。

---

## 5. 已核验的 DOI（Crossref / DataCite 返回 200 且题录匹配）

v2 参考文献：

- `10.1016/j.commatsci.2015.02.050` Electrolyte Genome (Qu 2015)
- `10.1039/C4CP00547C` Korth 2014
- `10.1039/C4CP04338C` Husch 2015
- `10.1039/C8EE01286E` Peljo & Girault 2018
- `10.1016/j.coelec.2018.10.015` Borodin 2019
- `10.1038/s41467-019-11317-3` Fadel 2019
- `10.1039/D1CP01454D` Itkis 2021
- `10.1021/jacs.2c11807` Wu 2023
- `10.1016/j.mtener.2025.102121` Yang 2025
- `10.1021/acs.jctc.6c00575` Rebollar-Zepeda 2026
- `10.1002/aenm.71542` Chen 2026

本目录额外引用的锚点文献（均已核验）：

- `10.18434/T4D303` NIST Chemistry WebBook, SRD 69
- `10.1021/cr030203g` Xu, Chem. Rev. 2004（非水电解液综述）
- `10.1016/j.jpowsour.2006.07.074` Zhang, J. Power Sources 2006（添加剂综述）
- `10.1149/1.1415547` Zhang & Kostecki et al., JES 2001（EC/PC/DMC/DEC/EMC 的还原）
- `10.1149/1.1838419` Xu & Angell, JES 1998（sulfolane 高阳极稳定性）
- `10.1021/acs.chemmater.6b02282` Michan et al., Chem. Mater. 2016（FEC/VC 还原）
- `10.1088/0957-4484/26/35/354003` Borodin et al., Nanotechnology 2015（电化学稳定性高通量筛选）
- `10.1039/d0ma00847h` Materials Advances 2021（EC–PC 氧化还原分解）

> 说明：以上 DOI 均已用 Crossref / DataCite API 逐条核验题录；`source_note` 中出现的
> `doi:` 文本同样是「建议核对来源」，不代表本行数值直接引自该文献。

---

## 6. 使用方式（对应 v2 §9.1 与 §7.1）

1. **绝对定标**：把生产方法算出的 IP/EA 与 `R_gas` 逐物种比较，得到 method accuracy。
2. **tolerance δ 来源**：用锚点上的方法误差 / 实验不确定度给出 §9.1 的预注册 tolerance `δ_m`
   （对应 `prereg.yaml: pair_comparison.delta_m.source_rule` 第 (1) 条），
   使 `|ΔP| < δ_m` 的 pair 记为 `unresolved/tied`，避免把量化噪声当排名翻转。
3. **排序审计**：只在 **同一来源、同一条件** 的行之间比较相对排序（within-series relative ranking），
   不要把跨系列绝对值直接合并（v2 §15.2）。
