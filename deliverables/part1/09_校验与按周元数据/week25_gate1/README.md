# W25-G1 交付镜像（week25_gate1）

本目录是 **W25 Gate 1（Gate 1 排序判据首次评估）的交付镜像**，由
`scripts/build_week25_deliverables.py` 从仓库只读复制生成。除本 `README.md`、
`SHA256SUMS` 与 `verification.json` 外，其余文件均**按仓库相对路径原样复制**，
不改动任何源文件。

## 包含的文件

镜像内文件清单（相对本目录的相对路径，与其在仓库中的位置一致）：

- `data/anchors/README.md`
- `data/anchors/_received/Gate1_solution_anchor_potentials_2026-10-02.csv`
- `data/anchors/_received/Gate1_solution_anchor_potentials_2026-10-02_rev2.csv`
- `data/anchors/doe_apr2016_reduction_secondary.csv`
- `data/anchors/ue1994_okoshi2015_oxidation.csv`
- `data/anchors/within_series_ordering.csv`
- `data/metadata/core_set_metadata_ext.csv`
- `docs/39_week25_gate1_plan.md`
- `docs/40_week25_gate1_report.md`
- `docs/42_w25_core_set_metadata_mapping.md`
- `docs/43_week25_corefile_figure_alignment.md`
- `docs/44_week25_compute_budget_ledger.md`
- `outputs/figures/F52_gate1_ordering.png`
- `outputs/figures/F53_family_resolved.png`
- `outputs/figures/F54_two_axis_hierarchy.png`
- `outputs/figures/F55_coord_descriptor_tags.png`
- `outputs/week25/F52_manifest.md`
- `outputs/week25/F53_manifest.md`
- `outputs/week25/F54_manifest.md`
- `outputs/week25/F55_manifest.md`
- `outputs/week25/anchor_attribution_conflict.json`
- `outputs/week25/anchor_attribution_conflict.md`
- `outputs/week25/anchor_ingest_provenance.json`
- `outputs/week25/compute_budget_ledger.csv`
- `outputs/week25/compute_budget_ledger.json`
- `outputs/week25/ec_anchor_ref_attribution.json`
- `outputs/week25/ec_anchor_ref_attribution.md`
- `outputs/week25/family_resolved_stats.json`
- `outputs/week25/family_resolved_stats.md`
- `outputs/week25/figure_f55_stats.json`
- `outputs/week25/figure_f55_stats.md`
- `outputs/week25/gate1_oxidation.json`
- `outputs/week25/gate1_oxidation.md`
- `outputs/week25/gate1_reduction_secondary.json`
- `outputs/week25/gate1_reduction_secondary.md`
- `outputs/week25/series_rel_ordering_check.json`
- `scripts/analyze_family_resolved.py`
- `scripts/analyze_w25_figure_f52.py`
- `scripts/analyze_w25_figure_f53.py`
- `scripts/analyze_w25_figure_f55.py`
- `scripts/analyze_w25_gate1_oxidation.py`
- `scripts/analyze_w25_gate1_reduction.py`
- `scripts/build_compute_budget_ledger.py`
- `scripts/build_core_set_metadata_ext.py`
- `scripts/check_series_rel_ordering.py`
- `scripts/ingest_gate1_anchor_series.py`
- `scripts/make_w25_figure_f54_two_axis_hierarchy.py`

其中 `verification.json` 记录本次构建的断言与实测值，`SHA256SUMS` 记录每个复制文件的
SHA256（`<sha256>  <相对路径>`，LF 换行，按相对路径排序）。

## 如何复现 / 校验

复现（幂等：重复运行除 `verification.json` 中的时间戳外输出一致）：

    .venv\Scripts\python.exe scripts\build_week25_deliverables.py

校验已生成的镜像（重算 SHA256 并重跑全部断言）：

    .venv\Scripts\python.exe scripts\build_week25_deliverables.py --check

图 F55（§3.17 配位位移 × 描述符标签）的复现 / 自检：

    .venv\Scripts\python.exe scripts\analyze_w25_figure_f55.py --check

## provenance（来源）纪律

- 用户转录值一律标注 `transcription_only`：
  `data/anchors/ue1994_okoshi2015_oxidation.csv` 的每一行 `repo_verification`
  均为 `transcription_only`；`data/anchors/doe_apr2016_reduction_secondary.csv`
  为同一批转录的**还原轴旁证**（`adjudication=secondary`）。
- 这些数值来自用户提供的转录文件：初版
  `data/anchors/_received/Gate1_solution_anchor_potentials_2026-10-02.csv`
  （SHA256 = `3a8f63e8e4d02437bdcfd13022429cb4fb184cdeae4b22c10743dbddf6c33879`），裁决后版本
  `data/anchors/_received/Gate1_solution_anchor_potentials_2026-10-02_rev2.csv`
  （SHA256 = `6aa15654ab5ef5eac74ea0b4bd19893a7c26128f89b4f6654eeab31a6bd2ee46`）。rev2 含 `primary_source` / `tabulation_source` /
  `ue_ref_attribution` 三列：13 行为 `ref1_likely_Ue1994_JES141_2989`，EC 一行为
  `ref2_likely_Ue1997_JES144_2684_UNVERIFIED`（`adjudicated_flagged` +
  `CONDITION_MATCH_UNVERIFIED`），还原轴 3 行为 `NA`。
- **来源归属冲突已裁决结案**（2026-10-02）：数据主源为 Ue 等在 Okoshi 2015 refs 1–2 的
  LSV 实测，Okoshi et al. 2015 仅为转录与式(2) 标度换算载体。详见
  `outputs/week25/anchor_attribution_conflict.md`。
- **EC 锚点归属仍待核**（熔点判据 mp < 30 °C 排除 EC）：即便合理降级，剔除后
  `tau_b = 0.7333` 仍 < 0.9，且只剩 15 对 < `min_pairs = 18`，冻结判据判
  `insufficient_pairs`（不可判定）——**Gate 1 依旧不闭合**。详见
  `outputs/week25/ec_anchor_ref_attribution.md`。
- **仓库未对这些转录值独立复核**：转录值不等于已核验的文献值，未与原始文献逐条
  对照。绝对标定层的 `method=est` 来源也未升级，仍记为 limitation。

## Gate 1 现状口径

- **排序层判据：已评估但未闭合。** W25 判据脚本给出 `n_pairs = 21`（>= 预注册最小
  18），但 `tau_b = 0.4286 < 预注册阈值 0.9`，判决 `ok = false`（`reason =
  ordering_disagrees`）。预注册阈值见 `config/prereg.yaml`。
- **绝对标定层：仍记为 limitation。** 溶液相锚点（`method=est`）未找到可确证、条件
  统一、可直接引用的实验表格，没有一行升级为 `exp` / `calc`。

## 两个未闭合原因不是一回事

- **还原轴 = 「证据不足」。** 目前缺少「同装置、同判据」的同系列还原锚点，`n_pairs`
  不足，属**数据缺口**，尚不能判定模型排序对错。
- **氧化轴 = 「排序不一致」。** 已有同系列锚点对（`n_pairs = 21`），但模型排序与实验
  排序显著不一致（`tau_b = 0.4286`），属**已评估且未通过**。

因此，还原轴的「证据不足」与氧化轴的「排序不一致」必须分开陈述，不能合并成
一个笼统的「Gate 1 未闭合」而掩盖两种不同性质的问题。
