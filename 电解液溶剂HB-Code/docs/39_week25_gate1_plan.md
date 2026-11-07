# Week 25（W25-G1）计划 —— 溶液相锚点的排序一致性判据：首次评估

- 命名空间：`week25`（W25-G1）；仓库既有 `week22`/`week22_hardening`/`week23`/`week24_corealign` 一律不改动。
- 对照对象：核心文件 `核心文件/ranking-electrolyte-materials-v2.md` §15.2（Solution redox anchors）与 §19 Stage 1 的 **Gate 1**。
- 唯一变量纪律：本周**零新增电子结构计算**。全部工作是把一批新到的外部实验锚点入库、用 **Stage 1 冻结的判据脚本**首次评估，并如实报告结果。
- 前置状态：W24-D 的可行性审计（`outputs/week24_corealign/gate1_anchor_feasibility.md`）判决 **NOT_CLOSABLE**，理由是"本地文献中不存在覆盖 ≥ 7 个核心集分子的同源序列"（本地最长序列 k = 1）。

## 1. 本周解决的问题

Gate 1 的排序层判据自 Stage 1 起冻结为：

| 项目 | 冻结值 | 来源 |
| --- | --- | --- |
| 表 | `data/anchors/within_series_ordering.csv` | `scripts/check_series_rel_ordering.py` |
| 模型列 | `outputs/week4/p1_core_set_derived.csv` 的 `p1_ox_ev` / `p1_red_ev` | 同上 |
| 最小对数 | `min_pairs = 18` | `config/prereg.yaml` |
| 秩相关阈值 | `Kendall τ_b ≥ 0.9` | 同上（`strong_i_gt_j = 0.9`） |
| 分组 | 只在同一 `(series_id, property)` 内成对 | 同上 |

此前该表只有表头，故判据"无法评估"（`reason = no_within_series_values`）。W25 收到一批满足"同装置 / 同判据 / ≥ 7 个核心集溶剂"要求的氧化锚点转录值，判据第一次可评。

## 2. 输入与入库（G1）

- 收到文件：`Gate1_溶液锚点电位表.csv`（SHA256 `3a8f63e8…c33879`），已原样归档到 `data/anchors/_received/`。
- 主系列：Ue, Ida & Mori, *J. Electrochem. Soc.* **1994**, 141(11), 2989（玻碳 / SCE / 0.65 M Et₄NBF₄ / 5 mV·s⁻¹ / 25 °C / 起始判据 j = 1 mA·cm⁻²），经 Okoshi et al. 2015（doi:10.1149/2.0051509eel）Fig. 1 统一换算到 Li⁺/Li 标度。
  - 换算：E(vs Li/Li⁺) = E(vs SCE) + 3.28。
  - 交叉验证：Ue 原文 Table II 的 PC 电解液 Eox = +3.65 V(vs SCE) → 6.93 V，与表中 6.9 V 一致。
  - 核心集 7 个：EMC 7.0、PC 6.9、MA 6.7、SL 6.6、EC 6.5、DOL 5.5、DMSO 4.8。
  - 非核心 7 个：GN 8.3、BC 7.5、NE 6.5、MPN 6.4、MAN 6.3、NMO 5.0、DMI 4.5。
- 旁证系列：US DOE FY2016 年报的 dQ/dV 首圈还原峰，FEC 1.2 / VC 0.74 / EC 0.70 V(vs Li)，**显式标为 secondary**，不进主检验。
- **provenance 纪律（必须与数字同时引用）**：这批值是**用户提供的转录值**；Okoshi 2015 与 Ue 1994 的原 PDF 都不在 `核心文件/文献`，且沙箱无网络（WinError 10061），因此**仓库没有独立复核过任何一行**。所有入库行带 `repo_verification = transcription_only`，收到文件的 SHA256 被钉死。0.1 V 是 PI 声明的**系列重复性**，不是来源报告的不确定度。

## 3. 执行步骤

| 步骤 | 内容 | 产出 |
| --- | --- | --- |
| G1 | 锚点入库 + provenance 钉死 | `scripts/ingest_gate1_anchor_series.py`、`data/anchors/ue1994_okoshi2015_oxidation.csv`、`data/anchors/doe_apr2016_reduction_secondary.csv`、`data/anchors/within_series_ordering.csv`、`outputs/week25/anchor_ingest_provenance.json` |
| G2 | **用冻结脚本首次评估**（不覆盖 week2 冻结产物） | `outputs/week25/series_rel_ordering_check.json` |
| G3 | 氧化轴诊断与稳健性（三臂 / 逐分子敲除 / 锚点噪声 bootstrap / 置换检验） | `scripts/analyze_w25_gate1_oxidation.py`、`outputs/week25/gate1_oxidation.{json,md}`、`outputs/figures/F52_gate1_ordering.png` |
| G4 | 还原轴旁证级评估与降级声明 | `scripts/analyze_w25_gate1_reduction.py`、`outputs/week25/gate1_reduction_secondary.{json,md}` |
| G5 | 论文回填（§2.6、新增 §3.15、§4 局限、§5.2 第 5 条） | `论文/…_v5.docx` / `_v5.pdf` |
| G6 | 统一数据文档 + 交付镜像 + 周报 | `成果输出/统一数据文档.md`、`成果输出/week25_gate1/`、`docs/40_week25_gate1_report.md` |

## 4. 预期的诚实边界（先写死，避免事后调整口径）

1. 该实验系列是**纯溶剂 + 鎓盐**体系（无 Li⁺），对应 **C0 梯级**；C1/C2 的排序结论不能用它裁决。
2. LSV/CV 的 `j = 1 mA·cm⁻²` 起始电位是**动力学**量，本项目的 ΔSCF 是**热力学**量，二者**只在排序层**可桥接。
3. 14 行里 7 行没有模型值（非核心集），会被判据脚本跳过——"跳过"不等于"通过"。
4. 还原轴在可比性上不可能达到 `min_pairs = 18`（只有 3 个物种 = 3 对），因此该轴只能给**旁证级**结论，并显式降级。
5. Ue 系列中 DMSO、DMI 的提前氧化被 PI 预设为 N/S 孤对驱动动力学分解的**已知例外模式**；不得据此在看完数据后再剔除分子——任何剔除都必须报告为敏感性分析，且同时给出未剔除的结果。

## 5. 判定口径

- Gate 1 排序层：`n_pairs ≥ 18` **且** `τ_b ≥ 0.9` 才算 `CLOSED`。
- 若 `τ_b < 0.9`：判据**不闭合**，但状态从"无数据"变为"**已评估且不一致**"（`reason = ordering_disagrees`）。这是一次**预注册的负结果**，必须原样报告，不得通过事后剔除分子或更换模型列来"救回"。