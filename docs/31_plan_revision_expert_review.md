# 基于外部评审意见的计划修订（R1–R12）

> **文件名变更（2026-10-01）**：本文件原为 `docs/30_plan_revision_expert_review.md`。
> 因 `docs/30` 已被 Week 20 周报预定（`scripts/gen_week20_report.py:28` 的默认输出即
> `docs/30_week20_report.md`，且 `scripts/build_deliverables.py` 的 `WEEKS[20]` 以 required=True
> 引用它、`scripts/freeze_gates.py` 的 `STAGE2_PATTERNS` 收 `docs/30_*.md`），
> 故让出该编号，改名为 `docs/31_plan_revision_expert_review.md`。
> **注意：序号 31 自此被占用，Week 21 周报请用 32。**

> 来源：2026-10-01 外部评审对「第 20 周进展小结」的逐条意见。
> 上游：`docs/17_plan_optimization_branchABC.md`（P1–P8，文献驱动的措辞修订）。
> 定位：把评审意见转成**可执行、可验收**的条目。`docs/17` 管文献依据与措辞，本文件管统计、判据与 Gate，**两者并列**（不互相取代）。

## 0. 这份文件是什么，不是什么

**是**：评审意见 → 可执行条目的翻译表，每条带「现状 / 动作 / 验收判据 / 落点文件 / 工作量 / 是否需 PI 裁决」。

**不是**：不是对冻结件的改动。

- `config/prereg.yaml`：**0 改动**
- `config/scientific_definitions.yaml`：**0 改动**
- 目标量、family 定义、筛选方向、δ_m、k/N、种子集、splits：**全部沿用** → **Gate 0 保持 CLOSED**（**条件式**：仅当 R7 与 R11 都走「不登记进 `prereg.yaml`」那一支；若任一登记，见 §5）

**唯一例外是 R7**：它要动 Stage 1 的冻结件 `data/anchors/solution_redox_anchors.csv` 并改 Gate 1 的关闭判据。
但请注意——**补入可核验锚点本来就是 Gate 1 被设计出来的关闭路径**（`scripts/freeze_gates.py` 的模块
docstring 原话：Gate 1 在「溶液相锚点仍是未核验估值」期间报 not closed）。所以 R7 不是「绕过 Gate」，
而是「执行 Gate」，只是它改动了**关闭判据本身**，因此**必须 PI 裁决**。

除 R7 外，**R4b** 与 **R11** 也会碰到冻结面：R4b 想加的 ε 值不在 `config/scientific_definitions.yaml` 已登记的 `epsilon_values` 里；R11 的能量阈值属新判据。这两项的正确落法见 §5。

---

## 1. 评审之外发现的硬伤：三臂 τ_b 算在**不同的分子集**上

这是本轮最重要的发现，比「显著性不足」严重一个量级，必须在任何对外表述之前修掉。

`outputs/week4/p1_anchor_comparison.json` 的实际内容：

| 臂 | n | MAE (eV) | τ_b | τ_b 的 95% CI | 分子 |
| --- | --- | --- | --- | --- | --- |
| `P0_koopmans_xTB` | **12** | 1.3774 | **0.6061** | [0.164, 0.902] | DMC EC **VC** DME DOL EA **MA** GBL SL DMSO AN TMP |
| `GFN2_dSCF_xTB` | **10** | 4.4811 | **0.9111** | [0.692, 1.000] | DMC EC DME DOL EA GBL SL DMSO AN TMP |
| `P1_r2SCAN3c` | **12** | 0.2508 | **0.7273** | [0.378, 0.966] | DMC EC **VC** DME DOL EA **MA** GBL SL DMSO AN TMP |

**问题**：项目反复引用的核心反直觉结论——「ΔSCF 的**值**误差最大（4.48 eV）但**排序**最好（τ_b 0.911）」——
其中那个 0.911 是在**少两个分子的子集**上算的，而另外两臂是 12 个分子。**被排除的正是 VC 与 MA
（`GFN2_dSCF_xTB` 缺这两个）**，而 `analyze_p1_core_set.py` 目前**没有在报告里写明排除原因**。

这意味着：**0.911 与 0.606 / 0.727 不可比**；如果 VC/MA 恰好是 τ_b 的大杀手（完全可能——它们是
`unbound_anion` 高风险分子），那么「ΔSCF 排序最好」这条 headline **可能整体是子集效应**。

→ 这条被提升为 **R1**，列为结题前第一优先。

---

## 2. 采纳判定总表

| # | 评审点 | 判定 | 理由 | 优先级 |
| --- | --- | --- | --- | --- |
| **R1** | τ_b 差值缺显著性与可比性 | **采纳并升级** | 评审只要求补检验；实测发现**子集不一致**，先对齐再检验 | **P0** |
| **R2** | −0.851（5 点相关）太脆弱 | **采纳** | 降级为现象示意，主角换成闭式判据 + 合成数据仿真 | **P0** |
| **R3** | 「误差精确为 0」像循环论证 | **采纳** | 改成「代数恒等式」，并补一次真正的前瞻检验 | **P0** |
| **R4** | 介电层：补两个小检查 | **采纳** | (a) 非静电项为 0 写进正文；(b) 实测一格导体极限 | **P0/P1** |
| **R5** | 「饱和」措辞 + 补 n=3 | **采纳（P2）** | 只有 n=1,2 两点，改措辞；n=3 作为可选增强 | **P2** |
| **R6** | 「结构性不可能」适用范围要写死 | **采纳** | 纯措辞修订 | **P0** |
| **R7** | Gate 1 两级化 + within-series 锚点 | **采纳（需 PI 裁决）** | 动 Stage 1 冻结件、改 Gate 关闭判据 | **P2** |
| **R8** | 漏解靶向双腿策略 | **采纳** | 用近简并 pair 做靶向，替代全局翻倍 | **P3** |
| **R9** | 热修正抽样（5–10 分子） | **采纳** | 把「没算」变成「算过、有界」 | **P1** |
| **R10** | 小样本纪律：统一配对 bootstrap | **采纳** | 与 R1 同源，合并实施 | **P0** |
| **R11** | 判据从几何换成能量 + NEB 精修 | **采纳（但要登记判据）** | 新阈值属新判据，不得回溯适用 | **P1** |
| **R12** | 「哪些层不用算」变成卖点 | **采纳（叙事）** | 无新计算，重写 framing | **P3** |

---

## 3. 逐条修订

### R1 —— 对齐三臂子集，再补配对显著性　【P0，最高优先】

- **现状**：三臂 n = 12 / 10 / 12；`kendall_tau_b_ci95` 是**各自独立**的 bootstrap CI，项目内部用「CI 是否重叠」目测代替配对检验；`analyze_p1_core_set.py` 未写明 VC/MA 被排除的原因。
- **动作**：
  1. **查清 VC/MA 被排除的原因**并写入报告（是 ΔSCF 未跑？SCF 不收敛？还是 `unbound_anion` 触发？）——不得留白。
  2. **把三臂统一到共同分子子集（n = 10）重算 MAE / τ_b**，并**同时**报告 n = 12 口径，明确标注哪个是 headline。
     - **连带项（易漏）**：`config/prereg.yaml:29` 的 `core_set_k_abs` 是按 N = 18 算的（k = 2/4/5）。对齐到 10 个分子后，必须按冻结公式 `max(1, floor(frac·N+0.5))` 重算（k = 1/2/3），并说明这是**公式内推**、不是新判据。
  3. 新增**配对**检验：对同一批分子**联合重抽样**，重算 `Δτ_b = τ_b(ΔSCF) − τ_b(P1)` 的 bootstrap 分布，给 95% 配对 CI；另做**配对置换检验**给 p 值。
  4. 报告里为**每一个** τ_b 标注参照物（下面第 5 点是目前最容易混淆的地方）。
- **关键澄清（评审已点名）**：本项目存在**两族 τ_b**，必须分列：
  - **anchor-referenced**：与 `data/anchors/gas_phase_anchors.csv`（实验气相 IP）比较（`p1_anchor_comparison.json` 里的 0.606 / 0.911 / 0.727 属于这一族）；
  - **target-model-referenced**：廉价臂 vs 目标模型 P1 的比较（`p1_decision_stability.json` 的 0.673 属于这一族）。
  两族语义不同，**禁止混引**。
- **验收判据**：报告里出现「对齐后 Δτ_b = x (95% CI [a,b], 置换 p = …)」，且若 CI 跨 0 则 headline 必须改写为「排序差异未达显著」。
- **落点**：`scripts/analyze_p1_core_set.py`（扩展）+ 复用 `src/electrolyte_ranking/uncertainty.py` 的
  `bootstrap_statistic(stat_fn, data)`（已存在配对 bootstrap 能力）+ `scripts/build_stage16_predictor.py`
  的 `permutation_p()`（已存在精确置换能力）+ `docs/10_week4_report.md` §3.1。
- **工作量**：约半天（纯分析，无新电子结构）。
- **需 PI 裁决？** 否。

### R2 —— 把 −0.851 从 headline 降级，用「闭式判据 + 合成数据仿真」顶上　【P0】

- **现状**：ρ(std, τ_b) = −0.851 vs ρ(|mean|, τ_b) = −0.535 是**5 个点上的相关系数**（`docs/19_week9_report.md`），被当成核心证据引用。
- **动作**：
  1. **降级**：在 `docs/19` 与汇总里把它改称「现象示意（n = 5）」，不再作为 headline 数字。
  2. **新增合成数据蒙特卡洛**：构造已知 (mean, std) 的 offset 模型
     `δ_i = mean + std · z_i`，在固定 target-model 排序的前提下，让 mean 从 −8 扫到 +8 eV、std 从 0 扫到 2 eV，
     每个网格点生成数千组，计算 τ_b / f_unresolved / Top-k 重叠，画一张二维相图。
     预期结论：**τ_b 沿 std 轴单调下降，沿 mean 轴几乎不动**——这就把 N = 5 的经验观察升级为「定理 + 仿真」。
  3. **让公式做主角**：以 T1–T5（σ 的闭式解）+ `q_ij ≤ √2/z` 判据为主线叙事，−0.851 只作为一句「与仿真一致」的旁证。
- **验收判据**：仿真相图给出「固定 |mean| 时 τ_b 随 std 单调下降」的定量边界，并在报告里与实测 5 点叠图画在同一张图上。
- **落点**：新 `scripts/analyze_sigma_synthetic.py` + 新图（建议 F38，四面板）；
  `docs/20_week10_report.md`（把恒等式提升为主线）、`docs/19_week9_report.md` §0 改写。
- **工作量**：约半天（纯计算，无电子结构）。
- **需 PI 裁决？** 否（新增证据，不改定义）。

### R3 —— 「误差精确为 0」改写 + 一次真正的前瞻检验　【P0】

- **现状**：T1–T5 写成「与实测误差精确为 0」。若它由定义化简而来，这是**恒等式**不是预测，写成「预测精度」会被读成循环论证。
- **动作**：
  1. **改写**：所有 T1–T5 的表述改为「**代数恒等式**（identity），因此其价值在于**可外推**，而不在于拟合精度」。
  2. **补一次可证伪的前瞻检验**：选一个**从未算过**的分子子集（现成的：Stage 16 的 holdout 六分子
     DEC / EA / FEC / MA / TEGDME / VC）或一个未算过的台阶，**先用判据预测**「这一层会不会翻名单 / 会不会出现 resolved 反转」，
     **冻结预测**，再与实算对照，报告命中率**并包含失败案例**。
- **验收判据**：前瞻预测先落盘（带时间戳与哈希）再算；报告里给出命中/落空清单。
- **落点**：新 `scripts/analyze_sigma_prospective.py`；`outputs/weekN/sigma_prospective.json`。
- **工作量**：约半天（用已冻结数据即可，无新 QM）。
- **需 PI 裁决？** 否。

### R4 —— 介电层：两个小检查　【P0(b) 叙事 / P1(a) 一格实测】

- **动作 (a) 叙事**：把已经实测的「`SMD CDS` 在三电荷态上完全相同（spread = 0.0 eV）→ 对任何垂直 IP/EA 贡献精确为 0」
  写进 `docs/22_week12_report.md` 的**正文**（目前只在 §0）。这正好堵住「换溶剂时非静电项怎么办」的质疑。
- **动作 (b) 实测导体极限**：补跑**一格** conductor-like 极端（ε = 10⁶ 或 ORCA 支持的等价设定），
  与 ε = 200 对照，把「再加介电点没意义」从**外推**变成**实测**。
- **验收判据**：报告给出 `|E(ε=10⁶) − E(ε=200)|` 的逐分子值。
- **落点**：`scripts/run_core_set_p2.py` 的 ε 阶梯追加一格（或独立小脚本）+ `docs/22` 正文。
- **冻结面约束（重要）**：`config/scientific_definitions.yaml:223` 已登记 `epsilon_values: [5, 10, 20, 40]`，而该文件在 `scripts/freeze_gates.py:36` 的 `STAGE0_ARTEFACTS` 里；`config/prereg.yaml:18` 是 append-only。因此 ε = 10⁶ 只能作为**附加诊断**运行，**不得**修改那份冻结列表，报告里必须标注「不属预注册扫描集」。若 PI 坚持登记，则走 `amendment_log`，并接受 Gate 0 变 NOT CLOSED（`scripts/freeze_gates.py:387` 的 `evaluate_stage0` 一见 `amendment_log` 非空即判未关闭）。
- 依据：v2 §8.3 原文是「例如 ε = 5,10,20,40」，属举例而非封闭清单，所以附加点是**扩展**，不是**违规**。
- **工作量**：一格 ≈ 18 分子 × 3 态单点，约 30 分钟。
- **需 PI 裁决？** 否。

### R5 —— 配位饱和：改措辞 + 可选补 n = 3　【P2】

- **动作 1（措辞，必做）**：n = 1 与 n = 2 只有两个点 → 全文改为
  「**与饱和一致的证据**（consistent with saturation）」，**不得**写「证明了饱和」。
- **动作 2（措辞，必做）**：`docs/12`/`docs/18` 里「翻号」必须用**条件态语言**写
  （「不同条件态不是同一 observable 的高低精度」），**禁止**写成「加 Li⁺ 后电位变得更准」。
- **动作 3（可选增强）**：对一个代表分子（EC）补 n = 3 壳层，xTB 级示意即可，
  检验 `ΔΔ(3→2)` 与 `ΔΔ(2→1)` 同号且 `|ΔΔ(3→2)| < |ΔΔ(2→1)|`。
- **落点**：`scripts/build_microsolvation_shells.py`（支持 shell = 3）、`scripts/run_stage9_microsolvation.py`、`docs/18`。
- **需 PI 裁决？** 否（但新增电子结构须登记）。

### R6 —— 「结构性不可能」写死适用范围　【P0，纯措辞】

- **动作**：`docs/26_week16_report.md` §4.7 与汇总、站点文案里，把
  「`f_robust_inv` 从 0 变非 0 是结构性不可能」加限定为
  **「在本项目的这条具体流水线、这批格子、这套估计量下」**，并明确它不是普适定理。
- **落点**：`docs/26`、`成果输出/数据结果汇总.md` 的生成模板、`docs/assets/data.js` 的静态文案。
- **需 PI 裁决？** 否。

### R7 —— Gate 1 两级化 + within-series 锚点　【P2，需 PI 裁决】

- **现状**：`data/anchors/solution_redox_anchors.csv` 31 行**全部** `method = est`，`uncertainty_V = 0.5`。
  `docs/06` 记录了 2026-09-29 的主文献核验：引用源测的是**稀碳酸酯/THF/CV**，与本表列的
  「neat solvent + 1 M LiPF6 + LSV」条件不符，因此**保留 est 是正确的判定**，不是偷懒。
- **评审给出的三条线索**（**必须先核验再入库**）：
  1. **Ue 等的成系列测量** + **Okoshi 等 2015, ECS Electrochemistry Letters** 对 16 个溶剂
     （APN GN BC EMC PC MA SFL EC NE MPN MAN DOL NMO DMF DMSO DMI）的氧化电位计算表，**逐一与 Ue 实验值对照**
     —— 这是一张现成的 **within-series 相对排序**锚点表，且与 core set 重叠度高。
  2. **Egashira 课题组的微电极系列**（同一装置、同一判据）——适合族内相对排序。
  3. **Xu, Ding & Jow, J. Electrochem. Soc. 1999, 146, 4172**《Toward Reliable Values of
     Electrochemical Stability Limits for Electrolytes》——**不是数据源**，是「为什么不能跨文献合并绝对值」的权威依据。
- **动作**：
  1. **文献核验**：沿用 `scripts/audit_solution_anchors.py` 的离线 + 在线（Crossref / OpenAlex / Unpaywall）流程，
     逐条核验上述线索的**卷期页码与测量条件**。**未核验通过的条目不得写入 CSV**；核验失败的如实记录。
     - **先例警告**：本项目已在 `docs/13_week6_report.md:233` 记录过一次误配 —— CSV 里的 `10.1149/1.1838419` 原写作「Ue et al.」，核验后实为 **Xu & Angell, JES 145, L70–L72 (1998)**。评审这条线索的措辞与当年那处几乎一致，因此**必须先验卷期页码与测量条件再入库**，否则会重犯同一个错。
  2. **新增 method 枚举**：在 `scripts/validate_anchors.py` 里增加 `series_rel`（within-series 相对锚点）
     与 `verified_abs`（绝对标定）两类，并在 CSV 里打标。
  3. **Gate 1 两级化**（`scripts/freeze_gates.py`）：
     - **绝对标定级**：**承认为未达成**，写成 limitation，并把「该条件组合下公开可比数据稀缺」本身作为 findings；
     - **排序一致性级**：只要 within-series 锚点数 ≥ 18 且 target model 的相对排序与实验系列一致
       （**τ_b ≥ 预注册阈值**，阈值须在跑之前写定），即关闭 Gate。
  4. **物理不对称必须写明**：实验 LSV/CV 测的是**纯溶剂电解液分解电流的 onset（动力学量）**，
     我们算的是**固定背景中完整物种的一电子热力学 proxy**；两者的桥接**只能停在排序层面**。
     引用 Borodin 2019、Peljo 2018、Xu-Ding-Jow 1999 反而显边界清楚。
- **验收判据**：within-series 锚点表 + 排序一致性 τ_b + 绝对标定级 limitation 段落，三者齐备才允许改 Gate 状态。
- **落点**：`data/anchors/solution_redox_anchors.csv`（**Stage 1 冻结件 → 改后必须重录 digest 并说明**）、
  `data/anchors/solution_anchor_verification.md`、`scripts/validate_anchors.py`、`scripts/freeze_gates.py`、
  `scripts/audit_solution_anchors.py`。
- **工作量**：核验 ~1 天，实现 ~半天。
- **需 PI 裁决？** **是** —— 而且是要在**跑之前**裁决，否则构成「看结果改判据」。

### R8 —— 漏解：靶向双腿，而不是全局翻倍　【P3】

- **动作**：利用本项目自己的结论（漏解只在 **pair 接近简并**时才可能改变决策）：
  1. 只对 `|ΔP_ij| < δ` 的 **near-degenerate pairs** 涉及的格子做双腿重跑；
  2. 其余格子保留单腿，但在不确定性预算里加一项 **`missed-solution allowance`**，
     其分布由 Stage 16 的 32 格实测效应量估计；
     - **登记面**：`config/prereg.yaml` §3 的 `uncertainty.variability_sources_to_separate` 只登记了 5 项（method / conformer / Li⁺ motif / continuum dielectric / bootstrap）。这一项要么登记，要么在报告里明确标注为**非注册项**，不得静默当成已注册的不确定度来源。
  3. **把「两次预测失败」写进正文作为结论**——「不可预报性」本身正当化了上面的靶向策略。
- **验收判据**：给出「靶向集合占全部格子的比例」与「allowance 的效应分布」。
- **落点**：新 `scripts/plan_targeted_two_guess.py` + `scripts/analyze_stage16_catalogue.py` 的决策侧接口。
- **需 PI 裁决？** 否。

### R9 —— 热修正抽样：把「没算」变成「算过、有界」　【P1】

- **现状**：全文声明「0 K 电子能 + 垂直 gap，不做 RRHO/qRRHO」。这是**结构性缺失**，目前只是口头免责。
- **动作**：挑 **5–10 个代表分子**（覆盖 4–5 个 family、含一个氟代），用 **GFN2-xTB `--ohess`**
  （`src/electrolyte_ranking/xtb.py` 已支持 `--ohess`）补算热修正，回答**一个**问题：
  **热修正的分子间离散度有多大？** 若远小于 δ_m，则得到一句可引用的硬话：
  「未包含的热修正按抽样估计为 X eV 量级，**低于本文决策容差 δ_m**，不改变任何 robust inversion 判定。」
- **验收判据**：给出一张 `δ_thermal` 逐分子表 + 离散度与 δ_m 的对比。
- **落点**：新 `scripts/run_thermal_correction_sample.py` + `outputs/weekN/thermal_correction_sample.csv`。
- **工作量**：5–10 个 xTB `--ohess`，**1 天内完成**。
- **需 PI 裁决？** 否（但会改写 §限制 的口径，须登记）。

### R10 —— 小样本纪律：统一配对 bootstrap + 子集敏感性　【P0，与 R1 合并】

- **动作**：
  1. 所有关键对比**统一报配对 bootstrap 的「差值」分布**，不再用「两个独立 CI 是否重叠」目测；
  2. 把 Week 9「被迫统一到共同 10 分子」这件事在**方法部分透明写出**；
  3. 做**子集敏感性检查**：结论在 10 分子 vs 18 分子子集上是否同向。
- **落点**：`scripts/analyze_stage10_synthesis.py` 扩展 + `docs/19` 方法节。
- **连带纪律（交付层）**：改写 `docs/19`/`docs/22`/`docs/26` 的正文会改变 `成果输出/` 交付副本的 SHA256。任何这类改写完成后必须重跑 `scripts/build_deliverables.py` 并重算 `SHA256SUMS` 与 `verification.json`，否则交付层与仓库会再次出现「过期副本」（Week 4 的 T3 就是这个毛病）。
- **需 PI 裁决？** 否。

### R11 —— RMSD 判据 → 能量判据 + NEB 精修　【P1】

- **现状**：Stage 19 用 **0.02 Å 的 RMSD 阈值**判「两个弛豫终点是不是同一个盆地」。**这是全项目最脆弱的一个判决**：
  5 个 EC/阳离子格子的 RMSD 落在 **0.021–0.100 Å 的连续带**上被一刀切。
- **动作**：
  1. **能量判据取代几何判据 —— 按已实现的双侧口径改写**（评审建议的「2 kT / δ_m」不要照抄）。
     实际实现见 `scripts/analyze_stage21_path.py:64-66,165-168`：
     - 中间峰高 ≤ **1 kT = 0.0257 eV** → `one_basin`；
     - 中间峰高 ≥ **1 kcal/mol = 0.043364 eV** → `separated`；
     - 两者之间 → **`inconclusive`**（这正是评审原稿缺的那一段，必须保留）。
     评审建议的「> δ_m 才判 distinct」**不可用**：实测冻结的 `delta_m` 是氧化 0.700 eV / 还原 2.074 eV
     （`outputs/week6/delta_m_frozen.json`），拿它当 distinct 门限会留下 0.05–0.70 eV 的**未定义带**。
     另注意 0.043364 eV（1 kcal/mol）≈ 执行计划 docx §6.2 里那个 **0.05 eV 下限**，
     与 `config/prereg.yaml:67` 的 `delta_default = 2.0 kJ/mol`（= 0.0207 eV）**不是同一个数**，引用时必须点明用的是哪一个。
     - **本轮实测（Stage 21 Part A，2026-10-01）**：`EC/cation/5`（RMSD 0.100 Å，Stage 19 判 `distinct_lower`）峰高仅 0.00424 eV → **`one_basin`，Stage 19 未被支持**；`EC/cation/20`、`TEGDME/anion/20` 判决一致。即 0.02 Å 的一刀切在抽样的 2 个临界格里已误判 1 格。5 个临界 EC/阳离子格只扫了两端（ε = 5、20），ε = 7/10/14 三格仍是旧判决，报告里必须写明这是**抽样**。来源：`outputs/week20/stage21_path_summary.md`（Week 20 未提交件）。
  2. **NEB / QST2 精修**：直线插值**不是最低能路径**，峰高会**高估**真实势垒；
     对扫描出峰的格子用 ORCA NEB（或至少 QST2）精修 2–3 格。
  3. **新判据不得回溯适用**：阈值属**新判据**，必须在 prereg 登记，或明确写成
     「本阶段内部判据、不回溯改写 Stage 19 的既有判决」。
- **验收判据**：3 个格子的峰高表 + 与 Stage 19 RMSD 判决的**一致/冲突清单**（冲突必须逐条讨论）。
- **落点**：`scripts/run_stage21_path.py`（加 NEB 模式）、新 `scripts/analyze_stage21_path.py`、`docs/28` 补充。
- **工作量**：NEB 精修 2–3 格 ≈ 数小时机时。
- **需 PI 裁决？** **是（仅限阈值是否写入 prereg）**。

### R12 —— 叙事：把算力瓶颈反转成「哪些层不用算」　【P3】

- **动作（无新计算）**：结题叙事把三条结论合并成对 v2「minimal information budget」主问题的定性回答：
  **闭式判据（可在花钱前预判）+ 介电层免费（自相似、平行于轴）+ 配位饱和（次线性）**
  → 「大规模筛选时，哪几层可以不算」。
- **落点**：`成果输出/数据结果汇总.md` 的结论节、站点首页文案、README。
- **需 PI 裁决？** 否。

---

## 4. 执行批次

**批次 A（结题前必做，全部为纯分析，不产生新电子结构，1–2 天）**
R1（含 R10）→ R2 → R3 → R6 → R4(a)

**批次 B（低成本新计算，1 天）**
R9（xTB 热修正抽样，5–10 分子）· R4(b)（一格导体极限，**附加诊断**）· R11（NEB 精修 2–3 格）

> **2026-10-01 更新**：R11 的**能量判据部分已在 Stage 21 Part A 落地**（见 R11 节的实测）；批次 B 里 R11 只剩 **NEB / QST2 精修 2–3 格**这一段。

**批次 C（需 PI 裁决 / 依赖文献核验）**
R7（先核验文献，再决定是否改 Gate 关闭判据）· R5（措辞必做；n = 3 可选）

**批次 D（策略性，不阻塞结题）**
R8（靶向双腿策略）· R12（叙事重写）

---

## 5. 与 Gate 的关系

| Gate | 当前 | 本文件的影响 |
| --- | --- | --- |
| Gate 0（定义冻结） | **CLOSED** | **条件式**：若 R7、R11 都走「不登记」支，则 0 处改动、保持 CLOSED；若任一项登记进 `prereg.yaml` 或改 `scientific_definitions.yaml`，则按 `scripts/freeze_gates.py:387` 的 `evaluate_stage0` 变 **NOT CLOSED**，须由周报把该 amendment 解释清楚后才恢复 |
| Gate 1（方法 / 锚点） | **NOT CLOSED** | R7 若获 PI 批准，走「排序一致性级」关闭；**绝对标定级如实写成 limitation** |
| Gate 2+ | 未定义 / 未触发 | —— |

**顺序纪律**：R7 的 τ_b 阈值必须**在跑之前**写定并登记，否则「看结果改判据」= 自毁 Gate 0 的纪律。
R11 的阈值同理 —— 且 2026-10-01 已实际采用 **1 kT / 1 kcal/mol**，若登记，登记的就是这两个数。

---

## 6. 待 PI 裁决清单（累计）

1. **【本轮新增，阻塞 R7】** Gate 1 是否允许**两级化**（绝对标定级写成 limitation + 排序一致性级关闭）？
   若同意，τ_b 阈值定多少？必须在核验与计算**之前**给出。
2. **【本轮新增，R11 的回溯适用】已定默认：不登记。**
   判据采用 `scripts/analyze_stage21_path.py:64-66,165-168` 的**双侧口径**（≤ 1 kT → 同一盆地；≥ 1 kcal/mol → 分离；之间 `inconclusive`），并**明确声明为「本阶段内部判据、不回溯改写 Stage 19 的既有判决」** —— 与 `docs/13` §3.6 对 `delta_m` 采用的「选项 B」同一路子。
   好处：Gate 0 保持 CLOSED。缓解措辞张力的办法也与 `delta_m` 相同：把阈值作为 `outputs/week20/stage21_path_analysis.json` 的显式字段并在报告中回链（已实现：`thermal_ev` / `kcal_ev`）。
   **PI 可推翻**：若坚持登记，改走 `amendment_log`，并接受 Gate 0 变 NOT CLOSED。
3. **【Week 6 遗留】** `delta_m` 是否 append 进 `config/prereg.yaml`？
4. **【Week 7 遗留】** `ranking._resolve_k` 口径偏差（prereg 写 `max(1, floor(frac·N+0.5))`，代码用 `round(frac·N)`）。
5. **【Week 4 遗留】** Gate 1 的绝对标定级 blocker：溶液锚点 31 行仍为 `est`（R7 的直接对象）。
   **本轮未执行 R7**：它要动 Stage 1 冻结件与 Gate 的关闭判据，且必须先完成文献核验（批次 C）。旁路线程不做此类改动，等 PI 裁决 + 核验通过后再动。
6. **【本轮新增】** 三臂子集不一致（n = 12/10/12）的**对外表述**是否需要发布勘误（若 R1 结果改变 headline）。

---

## 7. 本轮对冻结件的**不**改动声明

- `config/prereg.yaml`：**0 改动**
- `config/scientific_definitions.yaml`：**0 改动**
- 目标量、family 定义、筛选方向、δ_m、k/N 比例、bootstrap 种子集、splits 规则：**全部沿用**

因此本文件列出的批次 A 结果**可以**与 Week 4–19 的结果直接比较，不需要任何口径护身符。

> **2026-10-01 补充**：该声明的前提是「按默认路子执行」—— R7 不登记、R11 不登记、R4b 只作附加诊断。若三者中任一项走进 `amendment_log`，本节的「0 改动」不再成立，须以重跑后的 `outputs/week0*/gate*` 记录为准。

---

## 8. 核心文件合规性核查（2026-10-01）

对撞 `核心文件/ranking-electrolyte-materials-v2.md`、`config/prereg.yaml`、`config/scientific_definitions.yaml`、`scripts/freeze_gates.py` 与执行计划 docx 后的结论：**R1–R12 的大方向不但不冲突，其中 6 条本身就是核心文件明文要求**。本文件原有 4 处需修正，已在 2026-10-01 的修订中改掉（§0 的条件式声明、R1 的 k_abs 连带项、R4b 的冻结面约束、R11 的双侧口径 + §5 的条件式 Gate 0）。

### 8.1 最反直觉的一处：R7 不是放松 Gate，是实现偏离了核心文件

- 核心文件 v2 §19 Gate 1 原文只要求「state identity、SCF stability、gas-phase anchor 和 **solution trend** 均没有明显系统性失败」—— 判的是 **trend（趋势）**。
- `scripts/freeze_gates.py:433-443` 的实现却是「`count_estimated_solution_rows` 必须为 0」，即「零条 `method = est`」，**比核心文件严得多**。
- 同时 v2 §3.3 与 §15.2 明文：「数据不可统一时，**不强行对全部文献做绝对值 pooled regression，而优先使用 within-series relative ranking**」；`config/scientific_definitions.yaml` 的 `reference_electrode.forbidden` 也列了「把不同实验系列的绝对值强行合并成单一绝对 benchmark」。
- **结论**：R7 的「排序一致性级」是**执行** v2 §3.3 / §15.2 / §19；当前实现才是偏离。这一条必须写进结题结论，否则会被读成「为了关 Gate 而改判据」。

### 8.2 逐条合规判定

| # | 判定 | 核心文件依据 / 冲突点 |
| --- | --- | --- |
| R1 R10 | **核心文件本来就要** | v2 §13.3「置信区间必须通过 bootstrap 或 permutation 报告」；`prereg.yaml` §3 / §9。当前「比两个独立 CI」才是违规 |
| R2 | 合规 | v2 §26.4（negative result 有价值）；需连带重跑交付件 |
| R3 | 合规且是范式 | `prereg.yaml:59` 的 source_rule「必须在看到结果之前确定」—— 前瞻检验同纪律。弱点：Stage 16 留出集已被用过一次，非真正未见 |
| R4a | **核心文件明文要求** | v2 §8.3「不能把 SMD 非静电参数与只改 dielectric 混成同一操作」 |
| R4b | **冲突（已改为附加诊断）** | `scientific_definitions.yaml:223` 的冻结列表 + Gate 0 |
| R5 | **核心文件明文要求** | v2 §16.1「C₁ 是 conditional coordination experiment」；v2 §8.1 |
| R6 | 合规 | v2 §2.3「第一阶段明确不声称什么」 |
| R7 | **核心文件明文要求** | v2 §3.3 / §15.2 / §19 Gate 1「solution **trend**」；需文献核验 + PI 裁决 |
| R8 | **核心文件已背书该策略** | v2 §21「只在排序可能改变的 near-degenerate candidates 上升级」 |
| R9 | 不冲突，且补上 v2 §7.2 | v2 §7.2 要求查虚频；`docs/17` P4 的「0 K、不做 RRHO」是项目自设并已声明为限制，v2 从未强制热修正 |
| R11 | 部分冲突（已修） | NEB 有 v2 §6.4 末端背书；阈值空档与 Gate 0 后果已在本轮修订中处理 |
| R12 | **就是 v2 §14 的框架** | 「真正的问题是最小昂贵信息预算」 |

### 8.3 与 `docs/17` 的关系（修正原有的「取代」措辞）

`docs/17_plan_optimization_branchABC.md` 的 P1–P8 是**文献依据与措辞层面**，本文件是**统计、判据与 Gate 层面**；两者并列，不互相取代。本文件 §6 已把 `docs/17` §4 的三条遗留（`delta_m`、Gate 1、`_resolve_k`）全部收进来。