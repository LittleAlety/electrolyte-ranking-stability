# Week 24（W24-C）报告 —— 核心文件对齐、决策流程图与统一数据

- 命名说明：本周命名空间 `week24_corealign`（W24-C）；仓库既有 `week23`（Stage 24）、`week22`（Stage 23）与 `week22_hardening`（W22-H）均不改动。
- 对照对象：核心文件 `核心文件/ranking-electrolyte-materials-v2.md`（1279 行 / 30 章）与 `核心文件/ranking-electrolyte-materials-reading-list.md`（729 行）。
- 输入依据：对核心文件逐章对照得到的缺口审计，叠加外部专家对结题论文 PDF 的逐页审查（A1–A6 硬伤、B1–B5 统计与证据链、C1–C8 文字规范、D1–D7 科学深化，其中 D6 即本周的流程图）。
- 唯一变量纪律：本周**零新增电子结构计算**；论文与流程图里的每个数字都由既有 JSON 产物按点路径解析或按字段原文提取。

## 1. 缺口审计（对照核心文件）

| 缺口 | 核心文件出处 | 处置 | 论文落点 |
| --- | --- | --- | --- |
| 论文缺 ML / 主动学习章，而数据与现成图都在仓库里 | §23 第 8–11 条、§24 图 6/7 | 从 Stage 7/8 产物蒸馏出 §3.13、§3.14 两节，接入 F48、F49 与表 6、表 7 | §3.13、§3.14 |
| §22 分支（情形 A–G）在论文里没有被认领 | §22.1–§22.7 | G3：逐分支给出判据定义 / 本项目判决 / 带数值证据 / 证据文件路径 | §5.1 |
| §23 的判据清单没有逐条自查 | §23 第 1–11 条 | G4：11 条逐项 PASS / PARTIAL，缺件单独登记 | §5.2 |
| §11 的特征成本没有落成表 | §11 | §2.7 特征成本分级（X0 12 项 / X1 6 项 / X2 4 项机制专用） | §2.7 |
| §25 的创新边界没有写 | §25 | G6：把「不做 ranking 本身、不做 Li⁺ 配位改写 redox」写死，给出三条增量 | §5.3 |
| §9.2 / §9.4 / §10.1 的决策量只有定义没有数值 | §9.2、§9.4、§10.1 | G8：五台阶 × 两轴 × 两池共 20 个组合的 `f_robust_inv`、`f_unresolved`、`p_ij` 全部补成数值 | §3.14、§5.2 |
| §19 / §20 要求的审计表缺失 | §19、§20 | G9 / G10 / G13：阶段映射、QC 台账、不做声明 | §5.5–§5.7 |
| §3.10（今 §3.11）是文字罗列 | 外部评审 D6 | **F51 最小信息预算决策流程图**，并在 §3.11 加交叉引用、在图 18 落图 | §3.11、图 18 |
| 方法依据未成节 | §15.2 | §5.4 方法依据（预注册、冻结、只读输入） | §5.4 |

## 2. 新增产物（G1–G14）

| 编号 | 内容 | 关键数字 | 来源文件 |
| --- | --- | --- | --- |
| G1 | Stage 7 蒸馏（direct vs Δ-learning） | LOFO 下 8 分组中 7 个 Δτ_b > 0、3 个区间不含 0；中位 +0.463；24 组合中 19 不可区分 | `outputs/week24_corealign/ml_direct_vs_shift.json` |
| G2 | Stage 8 蒸馏（最小昂贵标签预算） | τ_b ≥ 0.80 需 n_T = 8–9（10 分子池）/ 12–15（18 分子池）；区间两两重叠 | `outputs/week24_corealign/al_budget.json` |
| G3–G6 | 分支认领 / 判据自查 / 特征成本 / 创新边界 | 分支落 B、D、E（G 部分触发）；判据 10 PASS + 1 PARTIAL；X0 12 项、X1 6 项、X2 4 项 | `outputs/week24_corealign/core_alignment.json` |
| G8 | 决策量补全（§9.2 / §9.4 / §10.1） | `f_robust_inv` 40 个数全为 0；`p_ij` 与闭式 `f_unresolved` 在 z = 1.2816 逐点相等；C0→C1 还原轴 33/45 翻转全在 unresolved 区 | `outputs/week24_corealign/decision_metrics.json` |
| G9–G13 | 阶段映射 / QC 台账 / 不做声明 | Stage↔台阶 10/10 确证；QC 19 行（其中 13 行原论文未报）；4 项不做 | `outputs/week24_corealign/audit_tables.json` |
| **G14** | **F51 最小信息预算决策流程图（本周新增）** | 7 判定框、24 个数字全部按点路径解析；含 3 处声明的上游来源 | `outputs/figures/F51_minimal_budget_flowchart.png` + `scripts/make_w24_flowchart.py` |

## 3. 论文修订（v3 → v4）

| 项 | 处置 |
| --- | --- |
| §3.11 结尾 | 新增一句交叉引用：本节回答“该算哪些层”、3.14 节回答“该买多少标签”，两者互不相加，合起来即图 18 |
| §3.14 结尾 | 插入 F51，作为**图 18**（宽 6.3 in）；图 1–18 编号保持单调首次出现 |
| 页数与版面 | v3 24 页 → v4 **25 页**；F51 整幅落在第 20 页并与图注同页 |
| 英文摘要 | 仍完整落在第 1 页（含 `Key Words` 行） |
| 页眉 | 模板串「WHU 2023 级 基础化学实验 研究性实验」，无乱码 |

构建命令（两步，均从仓库根执行）：

```powershell
$env:PAPER_OUT = "E:\Claude Code\电解液溶剂-HB\论文\电解液溶剂氧化还原描述符决策稳定性_结题论文_v4.docx"
& $py 'E:\Claude Code\电解液溶剂-HB\论文\build_paper_docx.py'
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\docx2pdf.ps1 `
  -Docx 'E:\Claude Code\电解液溶剂-HB\论文\..._v4.docx' -Pdf 'E:\Claude Code\电解液溶剂-HB\论文\..._v4.pdf'
```

## 4. 决策流程图 F51（本周重点）

设计目标：把论文里两段**正交**的文字（§3.11 该算哪些计算层、§3.14 该买多少昂贵标签）合成一条自上而下的判定路径，并让每个数字都能被回溯到 JSON 字段，供正文直接引用。两者**不可混引、不可相加**，这一点写进了图的页脚。

### 4.1 图上数字与其来源字段

| 判定框 | 图上数字 | 来源文件 | 字段 |
| --- | --- | --- | --- |
| 输入 | core 18、台阶 n = 18、公共子集 10、broad 40 | `week9/stage10_ladder.json`；`week22_hardening/broad_pool_demo.json` | `common_subset_size`、`ladder[0].n`；`meta.core_n`、`meta.broad_n` |
| ① 廉价层够不够 | 分支 A = NOT SUPPORTED；τ_b = 0.673、重叠 = 0.000、f_unresolved = 0.229 | `week24_corealign/core_alignment.json` | `tables.s22_branch_claims.rows[0]`（后三个数字由该字段原文正则提取） |
| ② 闭式判据 | √2 = 1.414214；z = 1.2816；max\|Δ\| = 0（≤ 1e-15）；45 对 | `week24_corealign/decision_metrics.json`；`week22_hardening/broad_pool_demo.json` | `z_from_p_threshold`、`consistency[].abs_dev_p_vs_closedform`、`rows[0].n_pairs`；`meta.sqrt2` |
| ③ 靶向双腿 | A_axis 0.1523 / 0.2860 eV；19 / 21 次翻转；漏 0 次；省 28.3% / 3.3%；Top-10% 边界省 91.7% / 83.3% | `week23/targeted_two_guess.json` | `axes.*.allowance_ev`、`ladder[0].{savings_fraction,n_flips}`、`soundness_missed_flips`、`list_variant[0].boundary_savings` |
| ④ 升级清单 | 21/40 省 47.5%；38/40 省 5.0% | `week22_hardening/broad_pool_demo.json` | `budget.union.{n_worth_union_axes_k10,saving_union_axes_k10_pct,n_worth_union_axes_allk,saving_union_axes_allk_pct}` |
| ⑤ 可跳过 / 不可省 | 几何台阶 std 0.052–0.080 eV、τ_b ≥ 0.848、f_unresolved ≤ 0.061（n = 12）；ε ≥ 200 残余 ≤ 19.6 meV = δ_m(氧化) 的 2.80%；气相阴离子 18/18 不束缚 | `week9/stage10_ladder.json`；`week22/dielectric_limit.json`；`week4/p1_core_set_audit.json` | `ladder[G1_to_G2]`；`pairs.200.max_abs_mev`、`delta_m_mev.oxidation`；`flag_counts.unbound_anion`、`n_molecules` |
| ⑥ 标签预算 | 10 分子池 8–9 个、18 分子池 12–15 个；τ_b ≥ 0.80；20 组种子；端点 24 行 | `week24_corealign/al_budget.json` | `tau80_budget[].budget_n_T`（按 `pool_n` 分组取极值）、`key_n_T_by_pool`、`pool_sizes`、`tau_threshold`、`endpoint_self_check.n_endpoint_rows`、`n_repeats` |

### 4.2 三处声明的上游来源

任务给定的锚点文件是五份；图上另有三个数字，其来源由锚点自身声明或由论文正文引用，脚本把它们显式登记在 `TRANSITIVE` 里并在 `--check` 输出中打印 SHA256：

| 键 | 文件 | 声明方 |
| --- | --- | --- |
| `allowance` | `outputs/week23/targeted_two_guess.json` | `outputs/week22_hardening/allowance_factor2.json:sources.allowance` |
| `dielectric` | `outputs/week22/dielectric_limit.json` | 论文 §3.11 正文引用的 ε ≥ 200 残余 |
| `p1audit` | `outputs/week4/p1_core_set_audit.json` | `outputs/week24_corealign/audit_tables.json:tables.qc_ledger` |

### 4.3 与正文的口径对齐

- 图 ⑤ 写「ε ≥ 200 的**介电加密点**可跳过，单一连续介质不可省」，与 A6 修正后的 §3.11 口径一致；没有把「介电层免费」写成无条件结论。
- 图 ⑥ 照抄 §3.14 的判据（中位 τ_b 首次 ≥ 0.80、排除 n_T = n 端点），并保留「ranking_aware 未稳定胜出」这一负面结果。
- 图的 Top-10% 边界节省率直接取自 JSON，为 91.7% / 83.3%；正文 §3.11 原写「Top-k 变体可省 80%–90%」；W24-D 已按 JSON 精确值改为「k = 1/2 时分别可省 91.7% 与 83.3%」，与图的精确值一致。

## 5. 统一数据文档

- `成果输出/统一数据文档.md` 第七节「W24-C 新增产物」补齐 G1–G14 与 F51；图表索引的 F 图计数由 50（F0–F50）更新为 **51（F0–F51）**，manifest 计数由 26 更新为 **27**。
- 第二节标题由「Week 1 – Week 23」更正为「**Week 1 – Week 24**」（该节此前已含 Week 24 小节）。
- 交付镜像 `成果输出/week24_corealign/` 与 `outputs/week24_corealign/`、`outputs/figures/`、`docs/` 三方一致，逐文件 SHA256 见镜像内 `SHA256SUMS` 与 `verification.json`。

## 6. QC 与限制

- **缺字即失败**：`make_w24_flowchart.py` 在 `savefig` 时捕获 `missing from font` 告警并抛错；本次运行零告警（早期版本的 `⇒ ⁻¹ ₀ ✔ ✘` 五个字形在 Microsoft YaHei 里缺失，已全部替换）。
- **幂等**：PNG 不含时间戳，连续两次运行 SHA256 相同（`857dc62d…`）。
- **版面**：成图 1260 × 1711 px @ 200 dpi = 6.3 × 8.555 in；A4 正文可用高度 9.16 in，故图与图注同页，不会溢出。
- **可加性**：图上所有数字只来自 JSON 解析或字段原文提取；脚本对被改动的口径写死断言（例如 `n_worth_union_axes_k10 == 21`），数据一改即报错，不会静默出图。
- 限制：F51 是**汇总图**，本身不产生新证据；它继承 §3.13/§3.14 的小样本限制（n = 10/18、池不是真实 DFT 预算），故图上对 ⑥ 保留「提示性结论」字样。

## 7. 产物清单

| 类别 | 文件 |
| --- | --- |
| 流程图脚本 | `scripts/make_w24_flowchart.py`（支持 `--check`） |
| 流程图 | `outputs/figures/F51_minimal_budget_flowchart.png` |
| 图清单 | `outputs/figures/figure_manifest_week24_corealign.md` |
| 数据产物 | `outputs/week24_corealign/{ml_direct_vs_shift,al_budget,decision_metrics,core_alignment,audit_tables}.{json,csv,md}` |
| 新图 | `outputs/figures/F48_ml_direct_vs_shift.png`、`F49_al_budget.png`、`F50_decision_metrics.png`、`F51_minimal_budget_flowchart.png` |
| 分析脚本 | `scripts/analyze_w24_{ml,al,decision,alignment,audit,loro}.py`、`scripts/make_w24_flowchart.py`、`scripts/audit_w24_gate1_literature.py`、`scripts/verify_w24_gate1_refs.py` |
| W24-D 产物 | `outputs/week24_corealign/loro.{json,md}`、`loro_folds.csv`、`gate1_anchor_feasibility.md`、`gate1_literature_inventory.json`、`gate1_solvent_name_hits.json`、`gate1_ref_online_check.json` |
| 论文 | `论文/电解液溶剂氧化还原描述符决策稳定性_结题论文_v4.docx` / `_v4.pdf`（26 页；含 §5.8 表 14 与图 18） |
| 交付镜像 | `成果输出/week24_corealign/`（含 `SHA256SUMS`、`verification.json`） |

## 8. 缺失源

- 无阻塞性缺失源。`outputs/_week5_scratch/` 下的 pytest 临时目录属其它用户的暂存目录（Windows ACL 拒绝读取），不计入覆盖率统计，也不参与本周任何计算。

## 9. W24-D（第二轮）：对照核心文件的残余缺口

W24-C 交付后，对论文 v4 与核心文件再逐条核对，发现 9 处仍可优化项；本轮全部落盘，仍**零新增电子结构计算**。

| 缺口 | 处置 | 落点 | 关键数字 |
| --- | --- | --- | --- |
| 英文摘要仍用 ASCII 占位（`tau_b` / `sigma_ij` / `rho` / `sqrt(2)` / `dE` / `eps`），W22-H 报告称"已修"实为只修了中文摘要 | 全部改为正式符号 τ_b / σ_ij / δ_i / ρ / √2 / ≤ / ≥ / Δ / ε / R² | 摘要块 | 改后英文摘要仍完整落第 1 页（含 Key Words） |
| 核心文件 §24「建议核心图」与论文图号无映射 | 新增 §5.8 与表 14：7 条建议 → 18 张图的逐条对照与拆分说明 | §5.8、表 14 | 图 1–18 首次出现仍单调；表 1–14 首次出现单调 |
| 评审 D1 的 leave-one-rung-out 前瞻检验缺失 | 新脚本 `analyze_w24_loro.py`：逐折留一台阶、配对朴素规则 | §3.6 | `|b|→f_unresolved` MAE **0.052**、R² **0.932**、方向 9/10；`std→τ_b` 数值外推**失败**（MAE 0.483、命中 1/10），序数方向 10/10 |
| 摘要"可在计算前预判"与 LORO 结果不一致（过强） | 改为「可预判未解析的**比例与量级**，不能在算出目标层数值前指认具体分子对」 | 摘要、§3.6 | 未解析对集合跨台阶两两 Jaccard 中位 **0**、45 组中 31 组零重叠 |
| Gate 1 只说"n_pairs = 0"，未给可执行门槛 | 新脚本 `audit_w24_gate1_literature.py` + `gate1_anchor_feasibility.md`：逐篇核查本地 13 篇文献 | §2.6、§5.2 | 判决 **NOT_CLOSABLE**；≥ 18 对 ⟺ 同源序列覆盖 **≥ 7** 个核心集分子；本地最长序列 k = 1 |
| 外部评审建议的 Okoshi 2015 被当作实验锚点 | 核查后更正：属**理论计算**，纳入只能作 R_sol(calc) 单列，不能支撑"实验锚定" | §5.2 | 18 个核心集分子 17 个被提及，但仅 4 个可取到可引值、分属 3 个上游来源 |
| ε 点口径三处不一致（图 11「七级阶梯」/ §3.7「取多个点」/ §3.8「10 个介电点」） | 三处各自写明网格：图 11 = 气相 + 6 个介电点；§3.8 = 10 点密网格（5/7/10/14/20/28/40/80/200/1000） | §3.7、§3.8、图 11 图注 | 图内标题 `six dielectrics` 与「七级阶梯」由此可对齐 |
| §3.11 写「Top-k 可省 80%–90%」，与图 18 精确值不符 | 改为 k = 1/2 分别省 91.7% 与 83.3% | §3.11 | 与 `F51` 框 ③ 的数字一致 |
| 参考文献 [8]、[11] 在正文中找不到引用点（W22-H 报告称已补引，实测正文无 [8]/[11]） | 按项目真实做法补入两处方法学引用：[8] 用于 §2.3 的「以配体交换相对量规避缔合步骤的平动熵/缔合熵假象」，[11] 用于 §4 局限的「真实电解液物种分布与配位壳层竞争不在本文范围」 | §2.3、§4 | 补引后正文括号引用覆盖 [1]–[18] 全部 18 条（[14,15] 为合并引用） |
| §3.14 未声明小池贴近构造性端点 | 补第三条限制：10 分子池 8–9 个标签距端点仅差 1–2 步，故以 18 分子池（12–15 个标签）为主口径 | §3.14 | n_T = n 端点 24 行继续排除 |

### 9.1 交付镜像与校验（W24-D 后）

- 镜像 `成果输出/week24_corealign/` 由 **26 → 36 个文件**；`verification.json` 内置检查 **36/36 通过**（新增 `loro.*`、`gate1.*`、`paper.table_numbers_monotonic`、`paper.pages ≥ 26` 等断言）。
- 论文 v4 重建后 26 页；`paper.figure_numbers_monotonic`（图 1–18）与 `paper.table_numbers_monotonic`（表 1–14）均通过；页眉 26 页无乱码；英文摘要完整在第 1 页。
- 逐文件 SHA256 见镜像内 `SHA256SUMS`。

### 9.2 仍然不闭合的两项（如实保留）

- **Gate 1 溶液锚点**：本地文献不足以构造 ≥ 7 个核心集分子的同源序列，需外部补充一份同装置/同判据的溶剂电位表（优先级：Okoshi 2015 理论表 → Ue 1994/1997 实验系列）。
- **§24 Figure 2 的"外部验证"维度**：气相锚点已闭合，液相维度仍以"排序层降级"形式保留；表 14 已把该维度标为"部分支撑"。
