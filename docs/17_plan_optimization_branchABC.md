# 基于分支 A/B/C 文献的计划优化建议

## 0. 这份文件是什么，不是什么

**是**：把 `docs/16_branch_abcd_qa.md` 的 11 条方法学含义（I1–I11）翻译成**对 `ranking-electrolyte-materials-v2.md` 的可执行修改提案**，并逐条标注「现状 / 建议 / 依据 / 影响面 / 是否需要 PI 裁决」。

**不是**：不是对冻结件的改动。本轮**没有**修改
- `config/prereg.yaml`（冻结）
- `config/scientific_definitions.yaml`（冻结）
- `核心文件/ranking-electrolyte-materials-v2.md`（PI 的计划原文）

因此 **Gate 0 保持 CLOSED**：本轮没有在看结果之后修改任何目标量、family 定义、筛选方向或阈值。

**为什么不做成 amendment**：v2 §8.1/§8.2 与 §17 的表述**已经**与我们现在的做法一致（见 §1 的「现状」列）。本轮的工作是**把原先没有文献依据的口径补上依据**、把**未写明的采样级别写明**，属于「让计划更可复现」，不是「改变科学定义」。凡真正会改变科学定义的部分，一律列进 §4 交 PI 裁决，并说明走 `amendment_log` 的路径。

---

## 1. 建议改动清单（P1–P8）

| # | 位置 | 现状 | 建议改动 | 依据 | 影响面 | 需 PI 裁决？ |
|---|---|---|---|---|---|---|
| **P1** | v2 §8.1 / §8.2 | 「把 redox free-energy difference 与 association free energy 分开处理」「Li⁺ 配位优先使用相对 ligand-exchange quantity」——**规则已对，但没写为什么** | 在 §8.2 增加一句文献依据：**分子数改变会引入约 +8 ~ +10 kcal/mol 的气相 RRHO 伪惩罚；相对 ligand-exchange 量两侧物种数相同（Δn = 0），该伪惩罚严格抵消** | A2 Table 1（+9.75 kcal/mol @1 atm；ΔG°_assoc 1 M = +4.85 kcal/mol） | 仅增补文字，不改变任何计算 | 否 |
| **P2** | v2 §6.1 / §6.2 | 「母分子构象」「构象 ensemble」两节没有写明**用什么采样器、到什么级别** | 明确写明：本项目构象采样 = **RDKit ETKDG 嵌入 + GFN2-xTB 优化**；环境**没有 CREST**，因此**不是** iMTD-GC / CREGEN 级采样；相关数字一律表述为「有限构象采样散布」 | B2（CREST iMTD-GC，O(10⁵) 评估/分子；CREGEN E_win 6.0 kcal/mol、R_thr 0.125 Å） | 措辞纪律；`docs/13`、`docs/15` 与后续报告统一口径 | 否 |
| **P3** | v2 §17.1 | 「选择约 8–12 个候选……构造少数**相同化学计量**的局域 cluster，检查 1:1 Li coordination 的关键结论是否改变」——**没有写成可复现规则** | 把 Stage 9 的 cluster 构建规则写成四步（锚定 [Li M]⁺/取 G1 第二配体/球面刚体放置与冲突过滤/单点打分后取最低再预优化），并把 CREGEN 阈值作为「我们没做全域搜索」的参照写进限制 | B2 | 新增 Stage 9 实现（`docs/18`） | 否 |
| **P4** | v2 §7.2 | 「几何与频率建议」未声明本项目**是否**做 ZPE/热修正 | 显式声明：本项目冻结口径为 **0 K 电子能 + 垂直 gap**，**不做** RRHO/qRRHO 热修正；因此 qRRHO 的 1–4 kcal/mol 系统性差异**结构性地不进入**本项目结论，但**必须写出来**，避免被读成「我们做对了」 | A3（Eq. 7/8；ω₀=100 cm⁻¹；~100 原子 1–2 kcal/mol，300–400 原子 3–4 kcal/mol） | 报告口径；不改计算 | 否 |
| **P5** | v2 §3.1（P2 层定义） | P2 = 「fixed-background continuum molecular redox thermodynamics」，未说明 SMD 的物理内含 | 增加三句限制：① SMD 的 G_CDS 是**经验表面张力项，并已被参数化去吞并体相静电模型的一切偏差**（含 outlying charge、固有库仑半径）；② SMD **没有显式氢键项**，氢键通过 Abraham α/β 隐式吸收；③ 原作者明确指出该连续介质假设**对单原子离子（Li⁺）的第一溶剂壳尤其糟糕** | A1（p.6379） | 报告与 framing；不改计算 | 否 |
| **P6** | v2 §2.3「第一阶段明确不声称什么」 | 已有「不声称真实 stability window」类条目 | 补两条**硬**依据：① `p(C)` 需要 MD（fs–ns / pm–nm），本项目的 C1 是 conditional state；② 「界面溶剂化模型」与「bulk 溶剂化结构」是两个对象（`p(C\|bulk) ≠ p(C\|interface)`） | C1、C2 | framing | 否 |
| **P7** | v2 §19 Stage 9 | 只有两句话：「只对关键 stable/inversion/uncertain cases 做 targeted check」「本科项目时间有限可不做」 | **本轮已实现**并把实施细节落成 `docs/18_week8_report.md` 的判据；建议把「关键 cases 的选取规则」固化为：(a) 全部 12 个 C1 motif（含 2 个双齿）覆盖全部 6 个实际家族；(b) 同化学计量 Li(M)₂；(c) 判据 = 1:1 → 1:2 的 ΔIP/ΔEA 排序 τ_b、O_k、f_unresolved、f_robust_inv 是否保持 | 本轮 Stage 9 实施 | 新增 Stage 9 结论 | **是**（见 §4-1） |
| **P8** | v2 §3.2 Axis B（C₂「selected explicit microsolvation states」） | C₂ 在 v2 里**已定义**，但 MVP 阶段被 §17.1 限制为 targeted check | 本轮把 C₂ 从「未实现的状态」推进为「**已实现但只对 12 个 motif 的 1:2 同配体壳层**」——建议在 v2 里把 C₂ 的状态标注从 "planned" 改为 "implemented (targeted, homoleptic Li(M)₂)" | 本轮 Stage 9 | 状态标注 | 否 |

---

## 2. 与 `docs/11_plan_alignment.md` 的关系

`docs/11` 是 Week 5 结束时写的「计划对齐表」。本轮**不直接改写**它（它属于 Stage 2 冻结集合，改动会改变其摘要值），而是在 `docs/18_week8_report.md` 里新增一节「Stage 9 对齐」，并在重建交付包时把 `docs/16`/`docs/17`/`docs/18` 一并冻结。若 PI 希望 `docs/11` 同步，需下一轮显式授权。

---

## 3. 本轮对冻结件的**不**改动声明

- `config/prereg.yaml`：**0 改动**。
- `config/scientific_definitions.yaml`：**0 改动**。
- 目标量、family 定义、筛选方向、阈值、k/N 比例、bootstrap 种子集、splits 规则：**全部沿用**。

因此本轮的 Stage 9 结果**可以**与 Week 4–7 的结果直接比较，不需要任何「口径变更」的护身符。

---

## 4. 需要 PI 裁决的遗留项（每轮都应重申）

1. **【本轮新增】Stage 9 的判据是否需要写进 prereg？**
   本轮把 Stage 9（显式微溶剂化）的判据实现为 `docs/18_week8_report.md` §2 的四个指标。由于 v2 §19 把 Stage 9 定义为 **optional**，我们没有把它写进 `config/prereg.yaml`。若 PI 希望把「C₂ 壳层鲁棒性」提升为一个**必报指标**，则需要走 `amendment_log`，并接受 **Gate 0 从 CLOSED 变为 NOT CLOSED** 的后果。
2. **【Week 6 遗留】`delta_m` 是否 append 进 `config/prereg.yaml`？** 当前取候选值，Gate 0 保持 CLOSED。
3. **【Week 4 遗留】Gate 1 NOT CLOSED**：唯一 blocker 是 `data/anchors/solution_redox_anchors.csv` 的 **31 行仍为 `method=est`**，缺主文献核验。主结论只依赖气相锚点。
4. **【Week 7 遗留】`ranking._resolve_k` 口径偏差**：prereg §1 写 `max(1, floor(frac·N+0.5))`，代码用 `round(frac·N)`；N=18/40 两者一致，N=5 时 10% 退化为 k=0。见 `docs/15` §8 第 5 条。
5. **【本轮新增】reading list 勘误回改**：A2 作者名（补全 4 位）与「分支a-d 实为 A/B/C 三支」两条建议回改 reading list 原文。