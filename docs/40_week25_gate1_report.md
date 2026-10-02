# Week 25（W25-G1）报告 —— 溶液相锚点排序一致性判据的首次评估（负结果）

- 命名说明：本周命名空间 `week25`（W25-G1）；仓库既有 `week22`（Stage 23）、`week22_hardening`（W22-H）、`week23`（Stage 24）、`week24_corealign`（W24-C / W24-D）一律不改动。
- 对照对象：核心文件 `核心文件/ranking-electrolyte-materials-v2.md` §15.2（Solution redox anchors）与 §19 Stage 1 的 Gate 1。
- 上游依据：本周计划 `docs/39_week25_gate1_plan.md`；W24-D 的可行性审计 `outputs/week24_corealign/gate1_anchor_feasibility.md`（判决 NOT_CLOSABLE）。
- 唯一变量纪律：本周**零新增电子结构计算**。全部工作是把一批新到的外部实验锚点入库、用 Stage 1 **冻结的判据脚本**首次评估、并如实报告结果。
- Gate 1 现状口径：**排序层判据已评估但未闭合（τ_b = 0.4286 < 0.9）；绝对标定层仍记为 limitation**。本周的状态变化是"从无数据到已评估"，不是"已闭合"。

## 1. 本周解决的问题

Gate 1 的排序层判据自 Stage 1 起就被冻结（见 `config/prereg.yaml` 与 `data/anchors/solution_anchor_verification.md`），关键参数如下：

| 项目 | 冻结值 | 来源 |
| --- | --- | --- |
| 锚点表 | `data/anchors/within_series_ordering.csv` | `scripts/check_series_rel_ordering.py` |
| 模型列 | `outputs/week4/p1_core_set_derived.csv` 的 `p1_ox_ev` / `p1_red_ev` | 同上 |
| 最小对数 | `min_pairs = 18` | `config/prereg.yaml` |
| 秩相关阈值 | Kendall τ_b ≥ 0.9 | 同上（`strong_i_gt_j = 0.9`） |
| 成对规则 | 只在同一 `(series_id, property)` 组内成对；跨论文绝对值 pooling 禁止 | `scripts/check_series_rel_ordering.py` |

本周末之前，`data/anchors/within_series_ordering.csv` 只有表头，判据的返回是 `reason = no_within_series_values`：
**"无数据"**，既不能判通过也不能判不通过。本周收到一批满足"同装置 / 同判据 / 覆盖 ≥ 7 个核心集溶剂"要求的氧化锚点转录值，判据第一次真正可评。

于是本周解决的问题可以写成一句话：

> Gate 1 排序层判据的状态从 **"无数据（no_within_series_values）"** 变为 **"已评估且不一致（ordering_disagrees）"**。

这是一个**预注册的负结果**：数值本身（τ_b = 0.4286）事后不得通过剔除分子、替换模型列或放宽容差来"救回"。
本周严格按此纪律执行——所有剔除都只作为敏感性分析报告，并同时给出未剔除的结果。

## 2. 输入与入库（G1）

### 2.1 收到文件与哈希钉死

| 项目 | 值 |
| --- | --- |
| 收到文件 | `data/anchors/_received/Gate1_solution_anchor_potentials_2026-10-02.csv` |
| 文件 SHA256 | `3a8f63e8e4d02437bdcfd13022429cb4fb184cdeae4b22c10743dbddf6c33879` |
| 入库脚本 | `scripts/ingest_gate1_anchor_series.py` |
| 台账 | `outputs/week25/anchor_ingest_provenance.json` |
| 复核标记 | `repo_verification = transcription_only_not_reverified_against_primary` |

### 2.2 入库内容（14 行氧化 + 3 行还原）

| 文件 | 行数 | 说明 |
| --- | --- | --- |
| `data/anchors/ue1994_okoshi2015_oxidation.csv` | 14 | 氧化系列：7 核心集 + 7 非核心集 |
| `data/anchors/doe_apr2016_reduction_secondary.csv` | 3 | 还原旁证：EC / FEC / VC |
| `data/anchors/within_series_ordering.csv` | 17 | 判据脚本的输入表（14 + 3） |

- **氧化主系列（14 行）**：Ue, Ida & Mori, *J. Electrochem. Soc.* **1994**, 141(11), 2989（玻碳 / SCE / 0.65 mol/dm³ Et₄NBF₄ / 5 mV·s⁻¹ / 25 °C / 起始判据 j = 1 mA·cm⁻²），经 Okoshi et al. 2015（doi:10.1149/2.0051509eel）Fig. 1 统一换算到 Li⁺/Li 标度。
  - 换算：E(vs Li/Li⁺) = E(vs SCE) + 3.28。
  - 交叉验证：Ue 原文 Table II 的 PC 电解液 Eox = +3.65 V(vs SCE) → 6.93 V，与表中 6.9 V 一致。
  - **7 个核心集分子**：EMC 7.0、PC 6.9、MA 6.7、SL 6.6、EC 6.5、DOL 5.5、DMSO 4.8（V vs Li⁺/Li）。
  - **7 个非核心集分子**：GN 8.3、BC 7.5、NE 6.5、MPN 6.4、MAN 6.3、NMO 5.0、DMI 4.5。
- **还原旁证（3 行）**：US DOE FY2016 年报的 dQ/dV 首圈还原峰，FEC 1.2 / VC 0.74 / EC 0.70 V(vs Li)，文件中显式标注 adjudication = secondary，不进主检验。

### 2.3 provenance 纪律（必须与数字同时引用）

- 这批值是**用户提供的转录值**；Okoshi 2015 与 Ue 1994 的原 PDF 都不在 `核心文件/文献`，且沙箱无网络（WinError 10061）。
- 因此**仓库没有独立复核过任何一行**；所有入库行带 `repo_verification = transcription_only`，收到文件的 SHA256 被钉死。
- `0.1 V` 是 PI 声明的**系列重复性**，**不是**来源报告的不确定度。

## 3. 冻结判据的首次评估结果（G2）

用**冻结脚本**（未修改一行）对冻结输入表首次评估，产物 `outputs/week25/series_rel_ordering_check.json`：

| 项 | 值 |
| --- | --- |
| 台阶 / 层级 | Stage 1 / `ordering_consistency` |
| 判据 | n_pairs ≥ 18 且 τ_b ≥ 0.9 |
| 可用物种数 | 7 |
| 可用对数 n_pairs | **21** |
| 一致 / 不一致 | 15 / 6 |
| 复算 τ_b | **0.428571** |
| 冻结 τ_b | 0.428571 |
| 与冻结判决一致 | 是 |
| 判决 | `ok = false`，`reason = ordering_disagrees` |
| detail | `tau_b=0.4286 < 0.90 over n_pairs=21` |
| 因缺模型值跳过 | 7 行（n_skipped_missing_model_value = 7） |
| 实验端成对并列 | 0 |

结论：**排序层判据已评估，且不通过**。τ_b = 0.428571（≈ 0.4286）远低于冻结阈值 0.9；`n_pairs = 21` 满足下限 18，但因 τ_b 不达标，整体 `ok = false`、`reason = ordering_disagrees`。
这是一次**可评的负结果**，不是"无数据"——两者的诚实口径必须区分。

## 4. 氧化轴诊断（G3）

诊断脚本 `scripts/analyze_w25_gate1_oxidation.py`，产物 `outputs/week25/gate1_oxidation.{json,md}` 与图 `outputs/figures/F52_gate1_ordering.png`。
所有诊断都在**同一 21 对**上进行，未改动冻结判据。

### 4.1 三臂对照

| 臂 | 含义 | 模型来源 | τ_b | Spearman ρ | 一致/不一致 |
| --- | --- | --- | --- | --- | --- |
| P0 | P0 Koopmans/GFN2-xTB 气相 IP | `p1_core_set_derived.csv` 的 `p0_ox_ev` | **0.5238** | 0.6071 | 16/5 |
| P1 | P1 r2SCAN-3c 气相 IP（注册口径） | `p1_core_set_derived.csv` 的 `p1_ox_ev` | **0.4286** | 0.5357 | 15/6 |
| P2 | P2 ORCA SMD(乙腈) 垂直 IP | `p2_core_set_smd_acetonitrile.csv` | **0.5238** | 0.6071 | 16/5 |

三臂都远低于 0.9，且**注册臂 P1 是三者中最差的一臂**；P0 与 P2 逐对同判（τ_b 完全相同），说明这不是某一条廉价代理特有的偏差，而是这一实验系列与本项目氧化描述符之间的系统性次序差异。

### 4.2 主导分子：EC

逐分子敲除（P1，留一，剔除后 n_pairs = 15）：

| 剔除物种 | 剩余 n_pairs | τ_b | 一致/不一致 |
| --- | --- | --- | --- |
| DOL | 15 | 0.2000 | 9/6 |
| DMSO | 15 | 0.2000 | 9/6 |
| SL | 15 | 0.3333 | 10/5 |
| PC | 15 | 0.4667 | 11/4 |
| MA | 15 | 0.4667 | 11/4 |
| EMC | 15 | 0.6000 | 12/3 |
| **EC** | 15 | **0.7333** | 13/2 |

- 剔除 **EC** 后 τ_b 由 0.4286 升至 **0.7333**（升幅最大），因此不一致的主导分子是 EC。
- 在 P1 的 **6 对不一致中，有 4 对涉及 EC**（EMC/EC、PC/EC、MA/EC、SL/EC）。
- 其余不一致对中，EMC/MA 的模型间距 < 1e-03 eV，属数值近简并（算术而非化学）。
- 按预注册纪律，此处**只报告敏感性**：未剔除的 τ_b = 0.4286 仍是判据口径的唯一结论，0.7333 不可替代它。

### 4.3 锚点噪声 bootstrap 与精确置换检验

| 项 | 值 |
| --- | --- |
| 噪声模型 | 实验值 ~ N(v, 0.1² V)，**2×10⁴ 次**，种子 **20261002** |
| τ_b 2.5% / 中位 / 97.5% | 0.3333 / 0.4286 / 0.6190 |
| τ_b 95% 区间 | **[0.3333, 0.6190]** |
| τ_b 均值 ± SD | **0.4518 ± 0.0900** |
| τ_b 范围 | [0.0476, 0.9048] |
| P(τ_b ≥ 0.9) | **5.0e-05**（2×10⁴ 次中 1 次） |
| P(τ_b ≥ 观测 0.4286) | 0.7973 |
| 精确置换（7! = **5040**）单尾 p | **0.1194**（602 / 5040） |

- 95% 区间 [0.3333, 0.6190] **整体低于 0.9**，观测值 0.4286 恰位于噪声分布中心附近（P(τ_b ≥ 观测) = 0.7973），说明不一致**不是实验重复性造成的偶然低值**。
- 噪声尺度 0.1 V 是 PI 声明的**系列重复性**，不是来源报告的不确定度。
- 本 bootstrap **只扰动实验端、未注入模型误差**，故 P(τ_b ≥ 0.9) 是"通过"概率的**上界**。
- 置换检验在 7! = 5040 个全排列上精确枚举，单尾 p = 0.1194，说明实验序与模型序的秩相关弱且在随机波动范围内可能更差。

### 4.4 物种位次对照

| 物种 | 实验 V vs Li⁺/Li | 实验位次 | P0 位次 | P1 位次 | P2 位次 |
| --- | --- | --- | --- | --- | --- |
| EMC | 7.0 | 1 | 3 | 4 | 3 |
| PC | 6.9 | 2 | 2 | 2 | 2 |
| MA | 6.7 | 3 | 4 | 3 | 4 |
| SL | 6.6 | 4 | 5 | 5 | 5 |
| EC | 6.5 | 5 | 1 | 1 | 1 |
| DOL | 5.5 | 6 | 6 | 6 | 6 |
| DMSO | 4.8 | 7 | 7 | 7 | 7 |

（位次 1 = 最难氧化 / 最稳定。）EC 由实验的第 5 位被模型排到第 1 位，是唯一显著偏离的物种。

## 5. 还原轴判定（G4）

判定脚本 `scripts/analyze_w25_gate1_reduction.py`，产物 `outputs/week25/gate1_reduction_secondary.{json,md}`。

| 项 | 值 |
| --- | --- |
| 系列 | `DOE_APR_FY2016`（adjudication = secondary） |
| 物种 | EC, FEC, VC（**3 个**） |
| 可用对数 | **3**（C(3,2)） |
| 预注册门槛 | n_pairs ≥ 18 |
| 缺口 | 15 对 |
| 判定 | **`not_evaluable_secondary_only` / `insufficient_pairs`** |

三点必须写清：

1. **3 物种 → 3 对 < min_pairs = 18**，因此这条轴在样本量上**不可能**通过排序层判据；要满足 18 对，一条同判据系列至少需覆盖 **7 个核心集分子**（C(7,2) = 21）。
2. **"证据不足" ≠ "排序不一致"**：还原轴是**样本量问题**（`insufficient_pairs`），氧化轴才是**结论冲突**（`ordering_disagrees`）。若把这 3 对拿去报 τ_b，等于把"没数据"包装成"有结论"，本周明确不做。
3. 这 3 行本身**也不是一条同装置系列**：FEC / VC 来自 Si-Gr 半电池，EC 来自石墨半电池；判据是**首圈 dQ/dV 峰位**，而非氧化轴所用的 **LSV j = 1 mA·cm⁻² 起始电位**。三者不构成一条 (paper, apparatus, criterion) 同源系列。

补充口径（来自 `outputs/week25/gate1_reduction_secondary.md`）：

- P1 气相阴离子 **18/18 不束缚**（`outputs/week4/p1_core_set_audit.json`），故 P1 的还原排序**不可作为物理结论**；还原轴结论只以 P2 / C1 为载体。
- C1 条件态覆盖不足：`outputs/week5/c1_coord_shifts.csv` 与 DOE 三物种的交集只有 EC，可组成 **0 对**；FEC 与 VC 从未进入 Li 配位集。

## 6. 诚实边界（G5 与全周口径）

以下边界先写死，避免事后调整口径：

1. **转录值，未回原刊核验**：14 行 + 3 行锚点值是对 Okoshi 2015 图 1（其本身转绘自 Ue 1994）与 DOE 年报的人工转录，台账记 `repo_verification = transcription_only`；**仓库未独立复核任何一行**。
2. **0.1 V 是 PI 声明的系列重复性**，不是来源报告的不确定度；把它当作来源不确定度会夸大 bootstrap 的结论强度。
3. **7 行非核心锚点被"跳过"不等于"通过"**：14 行中 7 行（GN、BC、NE、MPN、MAN、NMO、DMI）在核心集中没有模型值，按"跳过"处理，绝不能计为"通过"；可用 21 对只来自其余 7 个物种。
4. **梯级范围**：该系列是纯溶剂 + 0.65 mol/dm³ Et₄NBF₄（**无 Li⁺**），只对应 **C0 梯级**，不能裁决 C1 / C2 梯级的排序结论。
5. **动力学 vs 热力学**：锚点是 j = 1 mA·cm⁻² 的 LSV 起始电位（**动力学**量），模型列是 ΔSCF 的 IP（**热力学**量）；二者**只在排序层**可桥接——而这正是本判据所检验的内容。
6. **bootstrap 只扰动实验端**，模型误差固定，故 P(τ_b ≥ 0.9) 是"通过"概率的**上界**。
7. **已知例外模式**：来源指出 DMSO、DMI 的提前氧化由 **N/S 孤对电子**驱动的动力学分解造成，而非热力学稳定性；DMSO 正落在核心集内。该模式**可能同样作用于 EC**（EC 的文化上同样是氧孤对 + 环张力），但仍须按预注册纪律只作敏感性报告，不得据事后观察剔除。
8. **不声称 Gate 1 闭合**：本周只是"排序层判据已评估但未闭合"；绝对标定层仍记为 limitation。

## 7. 发现的一处缺陷（只报告，未改动）

在还原轴判定过程中发现 `scripts/check_series_rel_ordering.py` 存在一处**潜伏的符号取向缺陷**：

- 该脚本对两个性质一律采用 `sign(exp) == sign(model)`（第 230–247 行）作为一致判据。
- 这对氧化轴成立：`p1_ox_ev`（= IP，越大越难氧化）与实验氧化电位（越大越难氧化）**同向**。
- 但对还原轴**取向相反**：冻结量 `p_red = E(anion) − E(neutral) = −EA`（越大越难还原），而实验还原电位（越大越易还原）**反向**，故一致判据应为 `sign(exp) == -sign(model)`。
- 脚本 docstring 中"两个键与实验电位同向"的说法**只对氧化轴成立**。

该缺陷目前是**潜伏的**：`data/anchors/within_series_ordering.csv` 本周只有氧化行，还原分支从未被执行。
本周的处理是**只报告、不修改**——`scripts/check_series_rel_ordering.py` 与 `outputs/week2/series_rel_ordering_check.json` 均为冻结件，**未作任何改动**。
建议在后续涉及还原轴的判据脚本中先行修正取向，并保留本条作为变更依据。

## 8. 与核心文件 §15.2 / §19 Gate 1 的对照

| 核心文件条款 | 原文要求 | 本周实得 | 判定 |
| --- | --- | --- | --- |
| §15.2 Solution redox anchors | 优先寻找**同一实验系列**中、条件尽可能一致的 **10–20 个分子** | 同源序列 `Ue1994_Okoshi2015` 覆盖 **7 个核心集分子**（C(7,2) = 21 对） | 满足 `min_pairs ≥ 18` 的**下限**，但**未达 10–20 上限**；条件一致性满足（同装置 / 同判据 / 同参比换算） |
| §15.2 数据不可统一时的处置 | 不强行对全部文献做绝对值 pooled regression，优先使用 within-series relative ranking | 本周**只**做同源 within-series 排序，未做跨论文 pooling | 一致 |
| §19 Stage 1 Gate 1 | production protocol 对 state identity、SCF stability、gas-phase anchor、**solution trend** 均无系统性失败后才能启动批量计算 | 气相锚点已闭合；**solution trend 在排序层被评估为不一致**（τ_b = 0.4286 < 0.9） | **未通过**；Gate 1 不闭合 |

结论：本周把 §15.2 要求的"同系列溶液锚点"落实到了一批量级上**刚好过下限**的数据（7 分子 / 21 对），并按 §19 Gate 1 的口径给出首次评判——该项**不通过**。
这也意味着 §19 所指的"无系统性失败"前提在 solution trend 维度上**尚未满足**。

## 9. 下周候选（G6 之外的延伸）

要把还原轴与绝对标定层推进一步，需要满足"同装置 / 同判据 / 同态 + 真有离散度"的新系列。以下为 PI 提供的文献线索（**本仓库未取到原文、未核验数值**）：

| 来源 | DOI | 预期覆盖 | 已知限制 |
| --- | --- | --- | --- |
| Delp et al., *Electrochim. Acta* 2016, 209, 498–510 | 10.1016/j.electacta.2016.05.100 | EC, DMC, FEC, VC | 4 物种 → 6 对，仍 < 18；Li 盐体系，锚定 C1/C2 而非 C0 |
| Borodin, Behl, Jow, *J. Phys. Chem. C* 2013 | — | DMC, EMC, EC, PC, VC, TMS, TMP | 逐条判据不一致，合并会违反 same-criterion 要求 |
| Ue 1994 / Ue 1997 还原极限 | 10.1149/1.2059270 / 10.1149/1.1837882 | 多溶剂 | 还原极限被 Et₄N⁺ 分解钉在约 −3.0 V vs SCE，对溶剂还原**无区分度** |

最低要求（与 §19 / §15.2 对齐）：一条 `series_id` 覆盖 ≥ 7 个核心集分子、同参比换算与可重复性数值明确、描述符在 7 个以上溶剂间**真有离散度**。

## 附录 A. 产物清单（G1–G6）

| 步骤 | 内容 | 产物 |
| --- | --- | --- |
| G1 | 锚点入库 + provenance 钉死 | `scripts/ingest_gate1_anchor_series.py`、`data/anchors/ue1994_okoshi2015_oxidation.csv`、`data/anchors/doe_apr2016_reduction_secondary.csv`、`data/anchors/within_series_ordering.csv`、`outputs/week25/anchor_ingest_provenance.json` |
| G2 | 用冻结脚本首次评估 | `outputs/week25/series_rel_ordering_check.json` |
| G3 | 氧化轴诊断与稳健性 | `scripts/analyze_w25_gate1_oxidation.py`、`outputs/week25/gate1_oxidation.{json,md}`、`outputs/figures/F52_gate1_ordering.png`、`scripts/analyze_w25_figure_f52.py` |
| G4 | 还原轴旁证级评估与降级声明 | `scripts/analyze_w25_gate1_reduction.py`、`outputs/week25/gate1_reduction_secondary.{json,md}` |
| G5 | 论文回填（§2.6、§3.15、§4 局限、§5.2 第 5 条） | `论文/..._v5.docx` / `_v5.pdf` |
| G6 | 统一数据文档 + 交付镜像 + 周报 | `成果输出/统一数据文档.md`、`成果输出/week25_gate1/`、`docs/40_week25_gate1_report.md`（本文件） |

## 附录 B. 复现与自检

```powershell
.venv/Scripts/python.exe scripts/ingest_gate1_anchor_series.py --check
.venv/Scripts/python.exe scripts/analyze_w25_gate1_oxidation.py --check
.venv/Scripts/python.exe scripts/analyze_w25_figure_f52.py --check
.venv/Scripts/python.exe scripts/analyze_w25_gate1_reduction.py --check
```

上述 `--check` 均要求输出与磁盘逐字节 / 逐像素一致才返回 0。
本报告本身由脚本回读自检：文件存在、行数 > 200、无 Unicode 替换字符污染（不含连续两个以上 `?` 的中文上下文）、关键数字字符串全部命中。
