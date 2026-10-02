# Stage 1 / Week 2：溶液相 redox 锚点逐行核验报告

- 文档编号：06
- 日期：2026-09-29
- 关联：`data/anchors/solution_anchor_verification.md`（逐行证据表）、
  `outputs/week2/solution_anchor_audit.csv` / `.json`（机器可读审计）、
  `scripts/audit_solution_anchors.py`（离线复算）、`tests/test_solution_anchors.py`（测试）
- 写入范围说明：本报告与上述文件为 Week 2 / Stage 1 缺口的核验交付物。

## 1. 目的

`data/anchors/solution_redox_anchors.csv` 的 31 行（16 个物种）此前 **`method` 全部为 `est`**，
`doi` 全空。它直接卡住 Gate 1：`scripts/freeze_gates.py::evaluate_stage1` 会统计 `method == "est"`
的行数（`count_estimated_solution_rows`），只要非零就判 `NOT CLOSED` 并列为 blocker。

本次任务的目标是：**对这 31 行逐行核验**，能升级为可回溯的 `exp` / `calc` 就升级，否则**诚实保留 `est`**
并把失败原因、放大后的不确定度写清楚。**严禁为了让 Gate 1 变绿而把行改成 `exp`。**

## 2. 判定标准

每一行只允许三种结论：

- `exp`：能找到**明确给出该物种**（或可比同类）在**明确实验条件**（溶剂 / 支持电解质 / 浓度 /
  参比电极 / 换算标度 / 扫描方式）下的电位，且有可追溯标识（DOI 或权威条目 + 表号）。
- `calc`：能找到**可确证的高水平计算值**，且其条件与取值可复现。
- `est`：核验后仍不可确证，**保留 `est`**。

关键判据是**条件一致 + 数值可引**：DOI 存在、题录匹配只说明“参考文献为真”，并不等于“该行的数值
可回溯”。因此本轮核验通过后，31 行的 `doi` 列**依旧全部留空**。

## 3. 方法

### 3.1 网络核验（2026-09-29）

逐条核对 `source_note` 中出现的 DOI，用：

- Crossref（`api.crossref.org`）：题录 / 期刊 / 年份；
- OpenAlex（`api.openalex.org`）：摘要，用于判断该文献**到底报了没有、报了什么条件**；
- Unpaywall（`api.unpaywall.org`）：定位开放获取副本；
- 仓库镜像：成功从 `repository.cam.ac.uk` 下载 Michan 2016 全文 PDF 并用 pypdf 检索正文。

**可达性受限**（如实记录）：`iopscience.iop.org`（JES / Nanotechnology 正文）被 Radware Bot Manager
CAPTCHA 拦截；`www.osti.gov`、`www.ncbi.nlm.nih.gov` TLS 连接失败；`www.nature.com`、
`iris.unimore.it` 被 Cloudflare 挑战拦截。因此有几篇“原始实验”文献的**具体表格数值无法取得**。

### 3.2 离线复算

网络核验的结论被固化为**证据登记表**（写在 `scripts/audit_solution_anchors.py` 内），脚本在**无网络**下
即可对每一行确定性重算：`decision`、`evidence_kind`、`evidence_reference`、`conditions_complete`、
`missing_fields`、以及一组自洽性检查（单位 / 氧化-还原次序 / 量级窗口 / 气相-溶液相量级 / CSV 与登记表
是否漂移）。

## 4. 逐条结论摘要

核验行数：**31**；核验后：**`exp` = 0，`calc` = 0，`est` = 31**。

### 4.1 按证据类别

| 证据类别 | 行数 | 含义 |
| --- | ---: | --- |
| `solvent_anion_coupling` | 7 | 真实氧化为溶剂-阴离子耦合，孤立溶剂值仅为上界式参考 |
| `computational_not_retrieved` | 5 | 仅有计算型来源，逐溶剂数值不可得 |
| `condition_mismatch` | 5 | 原始测量条件与行内条件不符，且具体数值不可得 |
| `no_reference` | 5 | source_note 未给出任何可核对来源 |
| `review_trend_only` | 5 | 仅二手综述/趋势，无法回溯原始测量 |
| `mis_citation` | 2 | 引用文献研究对象错配 |
| `source_does_not_cover_species` | 1 | 所引原始文献未覆盖该物种 |
| `source_does_not_provide_value` | 1 | 所引文献未给出该电位数值 |

### 4.2 升级清单

**本阶段没有任何一行被升级为 `exp` 或 `calc`。** 逐行理由见 `data/anchors/solution_anchor_verification.md` §2。

### 4.3 核验暴露的两处引用问题（重要）

1. **sulfolane（SL）两行引用错配**：`source_note` 指向 Xu & Angell, JES 1998, `doi:10.1149/1.1838419`，但该文
   研究的是**非环状不对称脂肪族砜**（乙基甲基砜），并非环状砜 sulfolane；且其报的是 5.8 V 阳极极限，
   与 SL 行的 4.9 V 也对不上。引用**不支持**该行。
2. **EC 还原 0.9 V 与所引文献冲突**：所引 Zhang & Kostecki 2001, `doi:10.1149/1.1415547` 摘要明确称五种
   碳酸酯的还原电位均 “above 1 V”，与本行的 0.9 V 相矛盾。

此外，`doi:10.1021/acs.chemmater.6b02282`（Michan 2016）**只做化学还原（萘锂）的产物表征**，正文检索
不到 “V vs Li” 形式的还原电位；`doi:10.1038/s41467-019-11317-3`（Fadel 2019）证明氧化是溶剂-阴离子耦合
过程，孤立溶剂氧化值只能作上界式参考——两者都无法支撑把对应行升级。

## 5. 对 Gate 1 的影响

- 核验后，`data/anchors/solution_redox_anchors.csv` 中 **`method == "est"` 的行数仍为 31 行**。
- 因此 Gate 1 **仍然被卡住（NOT CLOSED）**：`evaluate_stage1()` 的 `anchors:solution_verified` 检查仍为 `False`，
  blocker 仍为“31 rows are estimates without a verified DOI”。
- 其余与锚点无关的 Gate 1 检查（`validate_anchors` 等）状态：`validate_anchors` = PASS。
- Gate 1 当前 `closed = False`；blocker 共 2 条。

> 换句话说：本次核验**没有**、也**不应该**让 Gate 1 变绿。它把“31 行未核验的估算”变成了
> “31 行已核验、原因清楚、不确定度已放大的估算”。Gate 1 要真正关闭，仍需要**未来找到条件统一、
> 数值可逐条引用的实验溶液相 redox 表**（见 §6 建议）。

## 6. 局限与诚实声明

- 31 行**依旧不是**任何单一文献的直接引用值；仍只能用于“量级 / 相对排序”级别的审计，
  **不能**作为绝对 benchmark，也**不能**用于 pooled absolute regression。
- 参比电极只有 `Li/Li+` 一种；若将来并入 `Fc/Fc+` 系列，必须同时给出换算依据与不确定度（禁止直接相加）。
- 部分原始文献正文因站点反爬 / TLS 失败**不可取**，所以“具体数值不可得”这一失败原因中包含**可达性**
  成分，而非仅“文献里没有”。这一点已逐条记录，未做任何推测填充。
- 不确定度放大规则（还原 +0.2、氧化 +0.3，上限 0.8 V）是**工程判断**，不是文献测量值；其作用是把
  “条件未核验 + 参比换算未核验”的风险显式计入 tolerance，规则写在脚本里、可复算。
- 若日后拿到可信实验表并升级某些行为 `exp`，必须同步更新 `data/anchors/README.md` §1.2 与
  `scripts/audit_solution_anchors.py` 的证据登记表（否则审计脚本会因“CSV 与登记表漂移”报错）。

## 7. 复现命令

```text
.venv\Scripts\python.exe scripts\audit_solution_anchors.py
.venv\Scripts\python.exe scripts\validate_anchors.py
.venv\Scripts\python.exe -m pytest tests -q
.venv\Scripts\python.exe scripts\build_metadata.py --check
```

## 8. 后续修订（2026-10-02）：Gate 1 两级化

> 本节是**后补记录**，不改写 §4–§6 在 2026-09-29 的结论。

- §5 里写的 `anchors:solution_verified` 这个检查名**已不存在**。按 `docs/31` R7，Gate 1 拆成两级：
  - **绝对标定级** `anchors:solution_absolute_calibration`：31 行仍为 `est`，检查仍为 `NO`，
    但按 R7 **只记为 limitation，不再计入 blocker**。依据 `docs/31` §8.1：核心文件 §19 对 Gate 1
    只要求「solution trend 没有明显系统性失败」，原实现「零条 `est`」严于核心文件。
  - **排序一致性级** `anchors:series_rel_ordering`：由 `scripts/check_series_rel_ordering.py`
    确定性判定，这是现在**唯一**的 Gate 1 blocker。
- 同日完成的 batch C 核验（四条线索 → 6 个 DOI）见 `data/anchors/solution_anchor_verification.md` §4。
  结论是**数值一条都没取到**，因此 `n_pairs = 0 < 18`，**Gate 1 依旧 NOT CLOSED** ——
  两级化没有、也不能让 Gate 1 变绿。
- 新增冻结件：`data/anchors/within_series_ordering.csv`（仅表头）、
  `scripts/check_series_rel_ordering.py`、`outputs/week2/series_rel_ordering_check.json`。
  因此 `outputs/week2/SHA256SUMS` 与 `gate1_record.md` 已重录（冻结件 27 → 30）。
