# 43 Week 25 — 核心文件 §24「建议核心图」× 论文实际图号 双向对齐表

- 生成日期：2026-10-02（Asia/Shanghai）
- 性质：**只读分析**产物；除本文件外未改动仓库任何其它文件；未 `git commit`；零新增电子结构计算。
- 输入（只读）：
  - `核心文件/ranking-electrolyte-materials-v2.md`：§23（L1429–1445）与 §24「建议核心图」（L1447–1509）。
  - `论文/build_paper_docx.py`：论文唯一真源；本文的图号、节号均由该文件的 `figure()` 调用与 `h1/h2` 标题解析得到。
  - `电解液溶剂HB-Code/outputs/figures/figure_manifest*.md`、`outputs/week25/F52_manifest.md`、`outputs/week25/F53_manifest.md`、`outputs/week25/F54_manifest.md`。
  - 已有对齐/审计记录：`docs/41_week25_corefile_gap_audit.md`（§2.15 O1–O7）、`outputs/week24_corealign/core_alignment.json`。
- 覆盖说明：`outputs/week24_corealign/core_alignment.json` 覆盖 §22 分支认领、§23 最小成果判据与阅读清单，**不含 §24 核心图逐条映射**；本文件补齐该双向映射，作为 §24 的单一入口。

---

## 0. 口径与判定标准

- 图号「图 N」= 论文最终图号；「F 号」= `outputs/figures/` 下的文件名标识（图号与 F 号**不同号**，例如 图 19 = F51）。
- 节号「§x.y」= **论文正文**小节号，非核心文件章号。
- 判定：
  - **PASS**：§24 该条要求的全部关键维度都有可追溯到具体文件/数字的论文图表对应物。
  - **PARTIAL**：有对应物，但缺关键维度，或为语义近似/替代，或仅示意。
  - **MISSING**：无对应物。
- 无法确证者写 `UNVERIFIED` 并说明缺失原因；**不猜数**。
- 行号口径：`[System.IO.File]::ReadAllLines` / `Get-Content -Encoding UTF8`。本文件实测 v2 = 1778 行，§23 起于 L1429、§24 起于 L1447、§25 起于 L1510（`docs/41` §1.3 提示的「1279 行」是默认编码的错行 artifact，不代表文件被改动）。

### 判定标准在本文的具体含义

- 正向表只按 §24 的**字面要求**判定，不按「论文已声明图数非目标」放宽；论文 §5.8 的替换/拆分理由写在「备注」，不改变状态判定。
- 反向表对每条论文图给出回溯归属；不属于 §24 七图任何一条者标「超出 §24 要求（增量）」。

---

## 1. 自检锚点（用任务给定锚点核对）

| 锚点 | 实测结果 | 结论 |
| --- | --- | --- |
| 图 2 = `F54_two_axis_hierarchy.png` | 图 2 确为 F54（`build_paper_docx.py:434`），紧随图 1；对应 §24 Figure 1 的二维层级图 | 新增，一致 |
| 图 19 = `F51_minimal_budget_flowchart.png` | 图 19 确为 F51（`build_paper_docx.py:837`） | 文件一致 |
| 图 19 所在论文节 | 实测 **§3.14**（h2 `build_paper_docx.py:810`「3.14 最小昂贵标签预算：主动学习重放」） | 与任务锚点所写 §3.11 **不符**（见 §6；锚点用的是插入新图前的旧编号「图 18」） |
| 图 20 = `F52_gate1_ordering.png`（§3.15） | 实测一致（`build_paper_docx.py:885`，§3.15） | 一致 |
| 图 21 = `F53_family_resolved.png`（§3.16） | 实测一致（`build_paper_docx.py:913`，§3.16） | 一致 |
| 论文图号范围 1–21 | `figure()` 调用共 21 次，caption「图 1」–「图 21」连续 | 一致 |
| 表号范围 1–15 | caption「表 1」–「表 15」连续 | 一致 |

---

## 2. §24 Figure 1–7 逐条对齐（正向）

### 2.0 总览

| §24 条目 | 核心文件行 | 论文图号 | 论文节 | 状态 |
| --- | --- | --- | --- | --- |
| Figure 1 Two-axis model hierarchy + reference layer | L1449–1461 | 图 1、图 2、图 3 | §2.1 | **PASS** |
| Figure 2 External validation and uncertainty audit | L1463–1465 | 图 4、图 7、图 10、图 20 | §3.1、§3.3、§3.6、§3.15 | **PASS** |
| Figure 3 Uncertainty-aware rank stability matrix | L1467–1474 | 图 10、图 11 | §3.6 | **PASS** |
| Figure 4 Robust rank-flow map | L1476–1478 | 图 5、图 6 | §3.2 | **PARTIAL** |
| Figure 5 Mechanisms of coordination-induced inversion | L1480–1488 | 图 9、图 14 | §3.5、§3.9 | **PARTIAL** |
| Figure 6 Direct vs Δ-learning under extrapolation | L1490–1492 | 图 17 | §3.13 | **PASS** |
| Figure 7 Minimal expensive-information budget | L1494–1508 | 图 13、图 16、图 18、图 19 | §3.8、§3.12、§3.14 | **PASS** |

---

### 2.1 Figure 1：Two-axis model hierarchy + reference layer

- **§24 原文要求摘录（≤60 字）**：横轴 = proxy/电子结构层级，纵轴 = 条件态层级，外侧单标 external references；表达 complexity ≠ truth。
- **对应论文图号**：图 1（F0，单向流水线）、图 2（F54，二维层级 + 外部参考层）、图 3（F1，化学空间覆盖）。
- **对应论文节**：§2.1 分子集与化学空间（三图均在 §2.1，`build_paper_docx.py:428/434/436`）。
- **证据文件**：
  - `outputs/figures/F54_two_axis_hierarchy.png`（纵轴 proxy 层级 P0→P1→P2 × 横轴条件态层级 C0→C1→C2，右侧单列外部参考层 R_gas/R_sol/R_env）
  - `outputs/week25/F54_manifest.md`（图件尺寸、输入与 sha256、逐数字来源，以及实心/斜纹/留白三态定义）
  - `scripts/make_w25_figure_f54_two_axis_hierarchy.py`（生成脚本，`--check` 可复现）
  - `outputs/figures/F0_project_pipeline.png`（5 段式流水线示意）
  - `outputs/figures/F1_chemical_space_coverage.png`（家族分子数 + 供体原子数）
  - `outputs/figures/figure_manifest.md`（F0/F1 的输入与 sha256）
  - `data/metadata/core_set.csv`、`data/metadata/broad_pool.csv`
  - `scripts/make_summary_figures.py`
  - `论文/build_paper_docx.py:428/434/436`（图 1/图 2/图 3 调用）
- **状态**：PASS
- **备注**：新图 2（F54）以**二维层级图 + 外部参考层**覆盖了 §24 Figure 1 的核心要求：纵轴为 proxy/电子结构层级（P0→P1→P2），横轴为条件态层级（C0→C1→C2），最右列单列 R_gas/R_sol/R_env 并明确其不属计算层级；格点以**实心/斜纹/留白三态**区分「已算 / 仅 targeted / 未算」，直接表达 complexity ≠ truth（可定义 ≠ 已计算）。图 1（F0 一维流水线）与图 3（F1 化学空间覆盖）作补充；`docs/41` §2.15 O1 与 §3 优化项 3 所指缺口已闭合。

---

### 2.2 Figure 2：External validation and uncertainty audit

- **§24 原文要求摘录（≤60 字）**：展示 gas/solution anchors、不同方法的误差与 rank consistency，并据此定义 robust-pair tolerance。
- **对应论文图号**：图 4（F3，值误差—排序误差分离）、图 7（F8，环境层位移 + 不确定带）、图 10（F19，十级台阶总判）、图 20（F52，溶液相锚点排序检验）。
- **对应论文节**：§3.1（图 4）、§3.3（图 7）、§3.6（图 10）、§3.15（图 20）。
- **证据文件**：
  - `outputs/figures/F3_value_error_vs_rank_error.png`
  - `outputs/figures/F8_environment_layer_p1_to_p2.png`
  - `outputs/figures/F19_stage10_ladder.png`
  - `outputs/figures/F52_gate1_ordering.png`
  - `outputs/week2/method_audit_xtb_summary.json`（三层臂误差）
  - `outputs/week4/p1_anchor_comparison.json`（气相锚点误差与 τ_b）
  - `outputs/week4/p2_decision_stability.json`（环境层位移 + unresolved）
  - `outputs/week9/stage10_ladder.json`（台阶级 τ_b/f_unresolved）
  - `outputs/week25/gate1_oxidation.json` + `outputs/week25/F52_manifest.md` + `scripts/analyze_w25_figure_f52.py`（溶液相锚点）
  - `config/prereg.yaml`（robust-pair tolerance：δ_m / zσ 的冻结定义）
- **状态**：PASS
- **备注**：gas 与 solution 两相锚点、方法误差与 rank consistency 均有可追溯图表（图 4 三层臂、图 20 溶液相 Gate 1，τ_b = 0.4286 的负结果如实呈现）。**robust-pair tolerance 的定义没有专属图**，落在 §2.5 正文与 `config/prereg.yaml`（z=1.0/1.96、δ_m）；图 20(d) 的逐分子敲除敏感性间接体现容差，但非容差定义的专门可视化。

---

### 2.3 Figure 3：Uncertainty-aware rank stability matrix

- **§24 原文要求摘录（≤60 字）**：同时展示 Spearman ρ、Kendall τ_b、unresolved fraction、robust inversion fraction。
- **对应论文图号**：图 10（F19）、图 11（F20）。
- **对应论文节**：§3.6 位移离散度判据与 σ 的闭式。
- **证据文件**：
  - `outputs/figures/F19_stage10_ladder.png`（(a) τ_b、(b)(c) Spearman ρ、(d) f_unresolved）
  - `outputs/figures/F20_sigma_anatomy.png`（σ 闭式与临界斜率几何）
  - `outputs/week9/stage10_ladder.json` / `stage10_ladder.csv`（含 `f_robust_inv` 字段）
  - `outputs/week10/stage11_sigma_anatomy.json`
  - `scripts/make_stage10_figure.py`（panel 定义见其 docstring）
  - 论文表 4（`build_paper_docx.py:618`，逐台阶列 `f_robust_inv(z=1)` 与 `f_robust_inv(z=1.96)`）
- **状态**：PASS
- **备注**：四个量里 **τ_b（图 10a）、Spearman ρ（图 10b/c）、f_unresolved（图 10d）在图内并置**；**robust inversion fraction 未单独作面板**，而是以「20 个 (台阶, 轴) 组合全部为 0.000」写入表 4 与 `stage10_ladder.json`，图 10 的 manifest 明确提醒「f_robust_inv = 0 不能单独当排序稳定的证据」。属可追溯的次要呈现差异，不影响该条判 PASS。

---

### 2.4 Figure 4：Robust rank-flow map

- **§24 原文要求摘录（≤60 字）**：只显示超出 uncertainty threshold 的 rank shifts；普通近简并交换不作为机制发现。
- **对应论文图号**：图 5（F4，氧化轴 P0→P1 位次迁移）、图 6（F5，还原轴 Koopmans 失效）。
- **对应论文节**：§3.2 方法台阶：P0→P1。
- **证据文件**：
  - `outputs/figures/F4_rank_migration_p0_to_p1.png`
  - `outputs/figures/F5_reduction_axis_koopmans_vs_dscf.png`
  - `outputs/figures/figure_manifest_week4.md`
  - `outputs/week4/p1_core_set.csv`、`outputs/week3/p0_core_set.csv`
  - `scripts/analyze_p1_core_set.py`
  - `outputs/week9/stage10_ladder.json`（阈值/robust 判据产物）
- **状态**：PARTIAL
- **备注**：图 5/6 呈现的是**未按 uncertainty threshold 过滤的全部位次迁移**（含整体平移与 Koopmans 定性失效），§24 要求的「robust rank-flow map（只画超阈值 shift）」未作为独立图交付。更实质的是：本项目**全台阶 f_robust_inv = 0**（`stage10_ladder.json`，20 个组合），即没有可画的「超阈值 robust shift」；论文因此以「位次迁移 + σ/f_unresolved 阈值几何（图 10/11）」替代，并在正文声明 near-degenerate swaps 不作机制发现。语义替代 + 现象未观测，判 PARTIAL。

---

### 2.5 Figure 5：Mechanisms of coordination-induced inversion

- **§24 原文要求摘录（≤60 字）**：分析 ΔΔG_coord 与 donor type/ESP/chelation/flexibility/functionalization tags 的关系，并给典型分子/态密度图。
- **对应论文图号**：图 9（F12，C1 配位条件态）、图 14（F46，第三配位点饱和）。
- **对应论文节**：§3.5 条件态台阶：Li+ 配位如何改写排序、§3.9 配位饱和的证据。
- **证据文件**：
  - `outputs/figures/F12_li_coordination_c1.png`
  - `outputs/figures/F46_shell3_saturation.png`
  - `outputs/week5/c1_summary.json`、`outputs/week5/c1_coord_shifts.csv`、`outputs/week5/c1_state_identity.json`、`outputs/week5/c1_ligand_exchange.csv`
  - `outputs/figures/figure_manifest_week5_c1.md`、`outputs/figures/figure_manifest_week23_stage24.md`
  - `outputs/week23/shell3_xtb_sign_test.json`
  - `scripts/make_stage24_figure.py`
- **状态**：PARTIAL
- **备注**：机制**改以「态身份改变」解释**——还原时 11/12 个体系电子落在 Li⁺ 上（`c1_state_identity.json`），而非 §24 点名要求的「ΔΔG_coord 对 donor type / ESP / chelation / flexibility / functionalization tags 的关系分析」。这些 descriptor tag 在 `data/metadata/core_set.csv`（`scripts/build_metadata.py` 生成）中确有字段，但论文没有把它们与 ΔΔG_coord 建立关系图。此外 §24 标题中的 **inversion 现象本身在本项目未观测到**（f_robust_inv = 0），故无法展示 inversion 机制，只能展示配位改写与饱和；这属于「现象缺失 + 分析维度替代」，判 PARTIAL。

---

### 2.6 Figure 6：Direct vs Δ-learning under extrapolation

- **§24 原文要求摘录（≤60 字）**：重点比较 LOFO，而不是只展示 random split R²。
- **对应论文图号**：图 17（F48）。
- **对应论文节**：§3.13 直接学习与位移学习：留一家族出外推下的判决。
- **证据文件**：
  - `outputs/figures/F48_ml_direct_vs_shift.png`
  - `outputs/week24_corealign/ml_direct_vs_shift.json`
  - `outputs/week7/stage7_ml_results.json`
  - `scripts/analyze_w24_ml.py`
  - `outputs/figures/figure_manifest_week24_corealign.md`
- **状态**：PASS
- **备注**：图 17(a) 留一家族出（LOFO）下两形状最优模型及 95% 区间；(b) 随机/分组/LOFO 三种划分的配对 Δτ_b。满足「以 LOFO 为主、非只报 random R²」。限制（LOFO/group 各仅 1 次留出、区间来自分子层 bootstrap、n=18/10）已在正文同段声明。

---

### 2.7 Figure 7：Minimal expensive-information budget

- **§24 原文要求摘录（≤60 字）**：比较 random/diversity/uncertainty/ranking-aware 采集：n_T → {τ_b, O_k, R_k}；最具一般方法学辨识度。
- **对应论文图号**：图 13（F45）、图 16（F47）、图 18（F17）、图 19（F51）。
- **对应论文节**：§3.8（图 13）、§3.12（图 16）、§3.14（图 18、图 19）。
- **证据文件**：
  - `outputs/figures/F45_targeted_two_guess.png`（漏解靶向重算量）
  - `outputs/figures/F47_broadpool_budget.png`（broad 池升级子集）
  - `outputs/figures/F17_stage8_active_learning.png`（n_T → τ_b 四条采集曲线）
  - `outputs/figures/F51_minimal_budget_flowchart.png`（两类预算合成决策路径）
  - `outputs/week23/targeted_two_guess.json`
  - `outputs/week22_hardening/broad_pool_demo.json`
  - `outputs/week7/stage8_al_results.json`、`outputs/week7/stage8_al_curves.csv`
  - `outputs/week24_corealign/al_budget.json`、`outputs/week24_corealign/decision_metrics.json`
  - `scripts/run_stage8_al.py`、`scripts/analyze_w24_al.py`、`scripts/analyze_w22_broadpool.py`、`scripts/make_w24_flowchart.py`
  - `outputs/figures/figure_manifest_week7_s7s8.md`、`outputs/figures/figure_manifest_week24_corealign.md`
- **状态**：PASS
- **备注**：四条采集基线（random/diversity/uncertainty/ranking-aware）与预算—决策关系已交付。**呈现差异**：图 18 只画 **n_T → τ_b**；§24 点名的 **O_k（Top-k overlap）与 R_k（selection regret）** 在 `stage8_al_curves.csv` 与汇总（`run_stage8_al.py`）中**已计算**（top_k_overlap/selection_regret 10/20/30%、regret），但未在同一图内以 n_T → {O_k, R_k} 面板呈现，需并读产物/表；图 19 把「算哪些层」与「买多少标签」合成一条路径。核心维度可追溯，判 PASS，O_k/R_k 未成图为次要缺口。

---

## 3. 论文实际图 1–21 → 核心文件 Figure 回溯（反向）

> 反向表保证双向可查：给定任一论文图号，可定位其对应 §24 条目；不属于 §24 七图者标「超出 §24 要求（增量）」。

| 论文图号 | 文件 | 论文节 | 回溯 §24 | 性质 | 证据/清单 |
| --- | --- | --- | --- | --- | --- |
| 图 1 | `F0_project_pipeline.png` | §2.1 | Figure 1 | PASS | `figure_manifest.md` |
| 图 2 | `F54_two_axis_hierarchy.png` | §2.1 | Figure 1 | PASS | `outputs/week25/F54_manifest.md` |
| 图 3 | `F1_chemical_space_coverage.png` | §2.1 | Figure 1 | PASS | `figure_manifest.md` |
| 图 4 | `F3_value_error_vs_rank_error.png` | §3.1 | Figure 2 | PASS | `figure_manifest.md` |
| 图 5 | `F4_rank_migration_p0_to_p1.png` | §3.2 | Figure 4 | PARTIAL | `figure_manifest_week4.md` |
| 图 6 | `F5_reduction_axis_koopmans_vs_dscf.png` | §3.2 | Figure 4 | PARTIAL | `figure_manifest_week4.md` |
| 图 7 | `F8_environment_layer_p1_to_p2.png` | §3.3 | Figure 2 | PASS | `figure_manifest_week4_p2.md` |
| 图 8 | `F10_cpcm_eps_scan.png` | §3.3 | — | 超出 §24 要求（增量） | `figure_manifest_week4_t3.md`；支撑 Figure 2 的 robust-pair tolerance |
| 图 9 | `F12_li_coordination_c1.png` | §3.5 | Figure 5 | PARTIAL | `figure_manifest_week5_c1.md` |
| 图 10 | `F19_stage10_ladder.png` | §3.6 | Figure 2、Figure 3 | PASS | `figure_manifest_week9_stage10.md` |
| 图 11 | `F20_sigma_anatomy.png` | §3.6 | Figure 3 | PASS | `figure_manifest_week10_stage11.md` |
| 图 12 | `F24_dielectric_limit.png` | §3.7 | — | 超出 §24 要求（增量） | `figure_manifest_week12_stage13.md`（输入 `outputs/week12/stage13_analysis.json`） |
| 图 13 | `F45_targeted_two_guess.png` | §3.8 | Figure 7 | PASS | `figure_manifest_week23_stage24.md` |
| 图 14 | `F46_shell3_saturation.png` | §3.9 | Figure 5 | PARTIAL | `figure_manifest_week23_stage24.md` |
| 图 15 | `F44_neb_refinement.png` | §3.10 | — | 超出 §24 要求（增量） | `figure_manifest_week22_stage23.md` |
| 图 16 | `F47_broadpool_budget.png` | §3.12 | Figure 7 | PASS | `outputs/week22_hardening/broad_pool_demo.json` + `broad_pool_demo.md`；脚本 `scripts/analyze_w22_broadpool.py` |
| 图 17 | `F48_ml_direct_vs_shift.png` | §3.13 | Figure 6 | PASS | `figure_manifest_week24_corealign.md` |
| 图 18 | `F17_stage8_active_learning.png` | §3.14 | Figure 7 | PASS | `figure_manifest_week7_s7s8.md` |
| 图 19 | `F51_minimal_budget_flowchart.png` | §3.14 | Figure 7 | PASS | `figure_manifest_week24_corealign.md` |
| 图 20 | `F52_gate1_ordering.png` | §3.15 | Figure 2 | PASS | `outputs/week25/F52_manifest.md` |
| 图 21 | `F53_family_resolved.png` | §3.16 | — | 超出 §24 要求（增量） | `outputs/week25/F53_manifest.md` |

**反向汇总**：

- 回溯源 → §24 七图：图 1,2,3（Fig1）；图 4,7,10,20（Fig2）；图 10,11（Fig3）；图 5,6（Fig4）；图 9,14（Fig5）；图 17（Fig6）；图 13,16,18,19（Fig7）。
- 「超出 §24 要求（增量）」共 **4** 条：图 8（F10）、图 12（F24）、图 15（F44）、图 21（F53）。此 4 图不属 §24 七图的直接对应物，或因证据链扩张而新增（介电极限、NEB 几何盆地、逐家族统计），或作为 Figure 2 的容差支撑（裸 CPCM 扫描）。

---

## 4. 状态统计（§24 七条）

| 状态 | 条数 | 条目 |
| --- | --- | --- |
| PASS | 5 | Figure 1、Figure 2、Figure 3、Figure 6、Figure 7 |
| PARTIAL | 2 | Figure 4、Figure 5 |
| MISSING | 0 | — |

- 论文图 1–21 中，落入 §24 七图对应物者 17 条，标「超出 §24 要求（增量）」者 4 条（图 8、图 12、图 15、图 21）。

---

## 5. 关键缺口（Top 2）

> 原 Top 3 的第 1 条「§24 Figure 1 缺真正的二维层级示意图」已由新图 2（`F54_two_axis_hierarchy.png`，证据 `outputs/week25/F54_manifest.md`、`scripts/make_w25_figure_f54_two_axis_hierarchy.py`）闭合，该条状态升为 PASS，不再列为缺口。

1. **§24 Figure 4 / Figure 5 — robust inversion 现象在本项目未观测到，导致两图只能作语义替代**。全台阶 `f_robust_inv = 0`（20 个 (台阶, 轴) 组合，`outputs/week9/stage10_ladder.json`），因此「robust rank-flow map（只画超阈值 shift）」（Fig4）无内容可画，退化为未过滤的位次迁移（图 5/6）；「coordination-induced inversion 机制」（Fig5）退化为「配位改写 + 态身份改变」解释。这不是排版缺口，而是**核心科学现象缺失**，应在论文中显式登记为 negative result，而非仅标「语义需并读」。
2. **§24 Figure 5 — descriptor 关系分析未做**。§24 点名要求 ΔΔG_coord 与 donor type / ESP / chelation / flexibility / functionalization tags 的关系分析，论文只给了逐分子 dIP/dEA、态身份与壳层饱和（图 9/14）；相关 tag 字段存在于 `data/metadata/core_set.csv`，但未与 ΔΔG_coord 建立关系图。属可低成本补做的分析维度（纯既有产物再聚合）。

---

## 6. UNVERIFIED / 与给定锚点不符之处

- **图 19 所在节的锚点不符（非 UNVERIFIED，已确证）**：任务锚点按插入新图前的旧编号写「图 18 = `F51_minimal_budget_flowchart.png`（§3.11）」（新编号为图 19），实测文件一致但**所在节为 §3.14**（`build_paper_docx.py:810` 的 h2「3.14 最小昂贵标签预算：主动学习重放」，图 19 置于 `build_paper_docx.py:837`）。§3.11「最小计算层预算」（h2 `build_paper_docx.py:737`）**整节无图**。图 19 的图注正文引用了「3.11 节」，可能因此被误记为 §3.11；本文按文件实测记 §3.14。
- **无 UNVERIFIED 的 §24 条目**：七条均有可追溯的论文图/表与证据文件，未见需要标 UNVERIFIED 者。
- **次级呈现差异（已确证，非 UNVERIFIED）**：
  - Figure 3 的 `f_robust_inv` 未作面板，仅入表 4 与 `stage10_ladder.json`；
  - Figure 7 的 `O_k`（Top-k overlap）/`R_k`（selection regret）已在 `outputs/week7/stage8_al_curves.csv` 计算，但未作图 18 的面板。
  两者均为「有产物、未成图」，非缺失、非猜数。
- **未覆盖范围**：本文件未核验任何第三方文献数值，未重跑计算，未打开 `.docx`/`.pdf` 复核实际版面（图注是否与图同页等）；所有判定基于 `论文/build_paper_docx.py` 源码、`outputs/` 产物与 manifest，与 `docs/41` §1.2 的未覆盖范围一致。
