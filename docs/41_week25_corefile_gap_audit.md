# 41 Week 25 —— 核心文件要求 vs 项目交付物：剩余缺口审计

- 审计对象（核心文件）：`核心文件/ranking-electrolyte-materials-v2.md`（v2，1779 行）与 `核心文件/ranking-electrolyte-materials-reading-list.md`（729 行）。
- 审计对象（交付物）：`论文/build_paper_docx.py`（论文源码，当前 v5）、`成果输出/统一数据文档.md`（602 行）、`成果输出/数据结果汇总.md`（389 行）、`电解液溶剂HB-Code/docs/` 下各周报告（含本周 W25 的 `39`、`40`）。
- 落地周次：W25（`docs/40_week25_gate1_report.md` 所述命名空间 `week25`）。
- 本文件是**只读分析**的产物；除本文件外未改动仓库任何其它文件。

---

## 1. 审计方法

### 1.1 读了什么（覆盖到什么程度）

- 核心文件 **v2 全文逐行读完**：30 章（§1–§30）与参考文献 [1]–[11] 全部覆盖；本报告对每一条要求都标注了 v2 的行号。
- 阅读清单 **全文读完**：Part I（M1–M7、8 问最低标准、两周安排）、Part II（A/B/C/D/E）、"不建议本科阶段先读的 5 项"。
- 交付物侧：`论文/build_paper_docx.py` 的结构与全部章节标题、图题（图 1–19）、表题（表 1–14）、§5.1–§5.8 的对照表内容；`成果输出/统一数据文档.md` 的第一、三、四、五、六、七、八节与附录 A1–A14；`成果输出/数据结果汇总.md` 的口径纪律、三层臂定义、核心结论、Gate 状态与 22 条已知限制。
- 证据层：`config/prereg.yaml`、`config/scientific_definitions.yaml`、`data/metadata/{core_set,broad_pool}.csv`、`data/anchors/*`、`outputs/week{1,2,4,5,7,8,9,22,23,24_corealign,25}` 的关键 JSON/CSV，以及 `src/electrolyte_ranking/qc.py`。
- 周报告：重点读 `docs/00–08`（Stage 0–2）、`14`（阅读清单 QA）、`15`（Stage 7/8）、`18`（Week 8）、`31`（计划修订与合规核查）、`37/38`（W24）、`39/40`（W25），其余周报按标题与结论段抽查。

### 1.2 未覆盖什么

- **未做外部文献核验**：本报告只核对"核心文件的要求 ↔ 仓库内的产物/文本"，不核对任何第三方数值或结论的真实性。
- **沙箱无网络**：审计期间无法访问网络；这既限制了本审计，也正是项目内 W25 把锚点标为 `transcription_only` 的原因之一（`docs/40` §2.3）。
- **未重跑任何计算**：所有判定基于仓库既有产物与脚本源码，未重新执行 ORCA/xTB/测试。
- **未解析二进制交付物**：`.docx` / `.pdf` 的实际版面（页数、分页、图注同页）依据 `build_paper_docx.py` 源码与 W24/W25 报告的自检断言，未逐页打开 PDF 复核。
- **未逐行核对全部数值产物**：审计聚焦"要求是否有对应物"，不逐一对每个 JSON 的每个字段做独立复算；凡未能确证的判定在"差距说明"中标注 `uncertain`。

### 1.3 口径说明（重要）

- 本报告所有行号由 `[System.IO.File]::ReadAllLines` 口径给出。在本环境（Windows PowerShell 5.1）中，`Get-Content` 会把 LF 换行的文件错并行：例如 v2 被 `Get-Content` 计为 **1279 行**，而 .NET 读法为 **1779 行**；`data/metadata/core_set.csv`（19 行）被 `Get-Content` 计为 2 行。历史文档（如 `docs/38`）引用的"1279 行 / 30 章"应视为该工具 artifact，**不代表核心文件被改动**。后续文档引用行号建议统一采用 .NET 口径。

---

## 2. 逐条对照表

判定口径：**已满足** = 有明确对应物且与核心文件要求一致；**部分满足** = 有对应物但不完整/仅近似/覆盖不足；**未满足** = 无对应物或与要求实质冲突。行末 `uncertain` 表示本审计未能完全确证。

### 2.1 三层框架与边界（v2 §3–§4）
| ID | 核心文件条目（§ + 行号） | 项目现有对应物（文件:行） | 判定 | 差距说明 |
| --- | --- | --- | --- | --- |
| A1 | §3.1 $P_0$ 必须是可排序**标量**代理量（L162–184） | `config/scientific_definitions.yaml:44–64`；`成果输出/统一数据文档.md:22` | 已满足 | 明确定义 $P_0^{ox}=-\varepsilon_{HOMO}$、$P_0^{red}=+\varepsilon_{LUMO}$，并显式排除 μ/α/ESP/fingerprint（sci_def:57–63）。 | 
| A2 | §3.1 $P_1$ 气相 redox + `unbound_anion` 标记（L186–202） | `scientific_definitions.yaml:65–74`；`outputs/week4/p1_core_set_audit.json`；`论文/build_paper_docx.py:439–441` | 已满足 | 18/18 气相阴离子不束缚已标记，且未强行给 adiabatic EA。 | 
| A3 | §3.1 $P_2$ 统一固定背景连续介质（L204–220） | `scientific_definitions.yaml:75–83`；`统一数据文档.md:24` | 已满足 | 全部候选统一 SMD(乙腈, ε=35.688)，不模拟各自 bulk。 | 
| A4 | §3.2 Axis B：$C_0/C_1/C_2$ 条件态层级（L226–288） | `scientific_definitions.yaml:89–111`；`成果输出/数据结果汇总.md:26–27` | 部分满足 | $C_0/C_1$ 已运行；$C_2$ 仅 `[Li(M)₂]⁺` 单一化学计量（`outputs/week8/stage9_*`），未覆盖 §3.2 所述"少量代表体系"的多态。 | 
| A5 | §3.2 不得把不同配位数/化学计量的 cluster 裸 Gibbs 平均（L288） | `scientific_definitions.yaml:239`（`ensemble_rule`）；`docs/08_stage2_production_protocol.md` | 已满足 | 冻结了"同电荷态/同化学计量/同模型内建 ensemble"的规则。 | 
| A6 | §3.3 Axis C：$R_{gas}/R_{sol}/R_{env}$（L290–306） | `docs/01_stage1_external_anchors.md:40–84,205–218`；`data/anchors/{gas_phase_anchors,solution_redox_anchors}.csv` | 部分满足 | $R_{gas}$ 闭合；$R_{sol}$ 仅 W25 的 7 个核心分子同源序列（`docs/40:54`）；$R_{env}$ 无数据，论文表 13 明列为 Phase IV 不做。 | 
| A7 | §4.1 ox/red 方向分离、必须分别记录 `objective_direction`（L310–334） | `config/prereg.yaml:44–45,51` | 已满足 | 预注册冻结了 ox/red 两方向，禁止代码默认"越大越好"。 | 
| A8 | §4.2 不得把 $S_{ox/red}$ 简写为"真实稳定窗口"（L336–342） | `scientific_definitions.yaml:29`；`build_paper_docx.py:457,953` | 已满足 | 定义与正文均限定为"完整物种一电子热力学代理量"。 | 

### 2.2 数据集（v2 §5）

| ID | 核心文件条目（§ + 行号） | 项目现有对应物（文件:行） | 判定 | 差距说明 |
| --- | --- | --- | --- | --- |
| B1 | §5.1 Core paired set $N_{core}\approx60$–100（L350–354） | `data/metadata/core_set.csv`（19 行 = 表头 + 18 分子）；`config/prereg.yaml:269` | 未满足 | 实得 **18**，约为建议下限的 30%。`prereg.yaml:269` 记录了"主动缩小到 18 个 family 覆盖分子"，但**论文正文未见与 §5.1 数值的显式偏差表**。 | 
| B2 | §5.1 Broad cheap pool $N_{pool}\approx300$–1000（L356–366） | `data/metadata/broad_pool.csv`（41 行 = 表头 + 40 分子）；`prereg.yaml:280–283` | 未满足 | 实得 **40**，约为建议下限的 13%。 | 
| B3 | §5.2 chemical-space metadata 13 项字段（L368–388） | `data/metadata/core_set.csv` 表头（14 列） | 部分满足 | 已有 mol_id/SMILES/family/role/donor_atoms/donor_count/heteroatom_count/n_heavy/mw/rotatable_bonds/tpsa/functionalization_tags；**缺** `formal_charge`、`conformer_count`、`Li_motif_count`、`state_identity_status`、`reactivity_status`、`qc_status` 共 6 项（部分散落于 outputs/week4、week5，未进主 metadata）。 | 
| B4 | §5.3 样本选择原则（donor 类型/单双齿/极性/刚性/家族内取代/跨家族/anchor）（L390–402） | `docs/00_stage0_definitions.md:134–151`；`docs/05_stage2_broad_pool_p0.md:89–109`；`build_paper_docx.py:413–417` | 部分满足 | 8 家族与 donor 覆盖已记录；"刚性/柔性轴""单齿 vs 双齿"未见成表逐条核对（`uncertain`）。 | 
| B5 | §5.3 禁止单骨架枚举 + 随机切分（L402） | `prereg.yaml:132–134,139` | 已满足 | group split 以 "family + 环系 + fluorinated 标签" 分组，明令禁止。 | 
### 2.3 构象与状态采样（v2 §6）

| ID | 核心文件条目（§ + 行号） | 项目现有对应物（文件:行） | 判定 | 差距说明 |
| --- | --- | --- | --- | --- |
| C1 | §6.1 母分子构象流程，选约 3–10 个低能构象进 DFT（L406–427） | `build_paper_docx.py:438`；`docs/14_reading_list_qa.md` §5 | 部分满足 | 实际用 RDKit ETKDGv3（24 初始构象）+ MMFF + GFN2-xTB 弛豫，**未用 CREST**（论文表 10 记"仅背景"）；进入 DFT 的构象数未见逐分子记录（`uncertain`）。 | 
| C2 | §6.2 构象 ensemble 自由能（L429–440） | `outputs/week6`（T6，`scripts/run_t6_conformer_spread.py`）；`docs/06_stage1_solution_anchor_audit.md` | 部分满足 | 只做了构象离散度的敏感性检验；**未按 §6.2 建 ensemble 自由能差**（redox 量仍取单构象）。 | 
| C3 | §6.3 Li⁺ 配位 motif 生成流程（L442–453） | `scripts/run_c1_li_coordination.py`；`outputs/week5/c1_coord_shifts.csv`；`docs/12_week5_report.md` | 已满足 | donor 枚举 → xTB 预优化 → 低能 motif 进 DFT 的链条已实现。 | 
| C4 | §6.4 state identity QC 六标签（L455–475） | `src/electrolyte_ranking/qc.py:40–48`；`build_paper_docx.py:912–913` | 已满足 | 六个标签与"断键本身不等于验证反应路径"的纪律均已落代码与论文。 | 

### 2.4 量子化学方法（v2 §7）

| ID | 核心文件条目（§ + 行号） | 项目现有对应物（文件:行） | 判定 | 差距说明 |
| --- | --- | --- | --- | --- |
| D1 | §7.1 method audit：8–10 分子、**两种合理 DFT functional**、≥2 基组/diffuse、continuum、anchor（L479–503） | `docs/02_stage1_method_audit.md:20–61`；`docs/04_stage1_xtb_audit_result.md`；`build_paper_docx.py:423` | 部分满足 | 审计分子数达标；但**生产方法只用 r2SCAN-3c 一条泛函族**，"两种 DFT functional"仅以 xTB-vs-DFT 对照替代；基组维度以 T5 diffuse control（`outputs/week4/t5_diffuse_control`）部分覆盖。 | 
| D2 | §7.2 r2SCAN-3c 作几何/频率起点 + 六项检查（L505–523） | `scripts/run_t2_opt_freq.py`；`outputs/week4/t2_opt_freq`；`build_paper_docx.py:436–438` | 已满足 | SCF/几何/虚频/自旋污染/连接性/波函数稳定性均有 QC 落盘。 | 
| D3 | §7.3 单点用 range-separated hybrid（如 ωB97X-D4）+ 阴离子专用 diffuse protocol（L525–536） | —— | 未满足 | 全程只用 r2SCAN-3c 单点，**未做 RS-hybrid 单点**；阴离子以 `unbound_anion` 判据替代 diffuse protocol。属预算外，但**未见论文显式登记为偏差**。 | 
| D4 | §7.4 生产参数机器可读记录 13 项（L538–555） | `scientific_definitions.yaml:340–367`；`src/electrolyte_ranking/provenance.py`；`数据结果汇总.md:8–17` | 部分满足 | 软件/泛函/基组/色散/溶剂模型/电荷/温度等已冻结；`integration grid`、`SCF threshold`、`geometry threshold` 等是否逐作业真实落盘未确证（`uncertain`）。 | 
| D5 | "先 method audit，再冻结 production protocol"（L479、L1158） | `docs/08_stage2_production_protocol.md`；`docs/31_plan_revision_expert_review.md` §8 | 已满足 | 冻结顺序与文档记录一致。 | 

### 2.5 Solution thermochemistry（v2 §8）

| ID | 核心文件条目（§ + 行号） | 项目现有对应物（文件:行） | 判定 | 差距说明 |
| --- | --- | --- | --- | --- |
| E1 | §8.1 redox difference 与 association free energy 分开、记录 thermodynamic cycle（L557–579） | `scientific_definitions.yaml:155–181`；`build_paper_docx.py:433–434,463` | 已满足 | 明确不以 $G=E_{elec}+G_{thermal}+\Delta G_{solv}$ 为通用公式。 | 
| E2 | §8.2 相对 ligand-exchange $\Delta\Delta G_{bind}$ + Stage 0 冻结 $R$（L581–612） | `scientific_definitions.yaml:185–212`（主 R=DME/C08，次 R=AN/C16）；`outputs/week5` | 已满足 | 相对量已实现，绝对 $\Delta G_{bind}$ 降为辅助量。 | 
| E3 | §8.3 两类 sensitivity 必须分开：A 固定溶剂 benchmark、B 仅介电 ε=5/10/20/40（L614–630） | `scientific_definitions.yaml:217–225`；`scripts/analyze_cpcm_eps_scan.py`；`outputs/week4/t3`、`outputs/week22/dielectric_limit.json` | 已满足 | 两类测试分开执行，介电扫描覆盖且超过要求值。 | 
### 2.6 不确定性排序与决策指标（v2 §9–§10）

| ID | 核心文件条目（§ + 行号） | 项目现有对应物（文件:行） | 判定 | 差距说明 |
| --- | --- | --- | --- | --- |
| F1 | §9.1 用 δ_m 或 $z\sigma$ 定义 unresolved/tied（L636–670） | `prereg.yaml:50–52`；`outputs/week4`（δ_m 推导） | 已满足 | 判定规则与 δ_m 来源规则均已冻结。 | 
| F2 | §9.2 robust inversion + $f_{robust\_inv}$ + $f_{unresolved}$ 必须报告（L672–704） | `prereg.yaml:72–81`；`outputs/week24_corealign/decision_metrics.json`；`build_paper_docx.py` 表 4 | 已满足 | 两比例并列报告，且 20 组合的 $f_{robust\_inv}$ 全为 0（分支 C 未观测）。 | 
| F3 | §9.3 优先 Kendall τ_b，Spearman ρ 辅助（L706–710） | `prereg.yaml:88–90` | 已满足 | 主/辅相关量已冻结。 | 
| F4 | §9.4 概率化 $p_{ij}$（>0.9 / <0.1）（L712–728） | `prereg.yaml:82–87`；`build_paper_docx.py:608` | 已满足 | 阈值与"中间区域 = unresolved"已实现。 | 
| F5 | §10.1 Top-k overlap + Jaccard，$k/N=10/20/30\%$ **看结果前预注册**（L732–757） | `prereg.yaml:25–45` | 已满足 | k 比例与绝对 k 规则（含 N=18/40）在冻结文件中。 | 
| F6 | §10.2 selection regret（L759–773） | `prereg.yaml:43`；`outputs/week7/stage7_ml_results.json`、`stage8_al_curves.csv` | 已满足 | 已并报 regret。 | 
| F7 | §10.3 threshold decision error 仅在阈值来源合规时使用（L775–794） | `prereg.yaml:115–123`；`build_paper_docx.py` 表 13 | 已满足 | 无合规阈值来源，按规则判 `not_applicable` 并明示，未用分位数临时替代。 | 

### 2.7 Feature cost 与 Δ-learning（v2 §11–§12）

| ID | 核心文件条目（§ + 行号） | 项目现有对应物（文件:行） | 判定 | 差距说明 |
| --- | --- | --- | --- | --- |
| G1 | §11.1/§11.2/§11.3 $X^{(0)}/X^{(1)}/X^{(2)}$ 定义（L798–836） | `outputs/week7/feature_manifest.json`（X0=12、X1=6、X2=4）；`build_paper_docx.py:476–488` | 已满足 | 三档特征与 v2 列举基本一一对应。 | 
| G2 | §11 所有 ML 表格须含 `feature_cost_level`；$X^{(2)}$ 只能机制解释（L838） | `feature_manifest.json`（`x2_policy`）；`build_paper_docx.py:474` | 已满足 | X2 严禁进特征集已作为硬性纪律。 | 
| G3 | §12 direct vs conditional-shift + 5 项检验（L840–884） | `outputs/week7/stage7_ml_results.json`；`build_paper_docx.py` §3.13、图 16 | 已满足 | Δ 的方差、descriptor 依赖、LOFO 优势、决策量同步优势均已检验。 | 

### 2.8 机器学习与外推（v2 §13）

| ID | 核心文件条目（§ + 行号） | 项目现有对应物（文件:行） | 判定 | 差距说明 |
| --- | --- | --- | --- | --- |
| H1 | §13.1 模型复杂度顺序（linear/KRR/GPR/RF，不默认 DNN）（L888–897） | `prereg.yaml:169–176`；`build_paper_docx.py:490` | 已满足 | constant→ridge→KRR→GPR→RF→GBDT，GNN 置末。 | 
| H2 | §13.2 random/group/LOFO 三种拆分必须同时报告（L899–913） | `prereg.yaml:128–139`；`build_paper_docx.py` §3.13 | 已满足 | LOFO 作为主要迁移性证据。 | 
| H3 | §13.3 60–100 core points 的统计边界 + bootstrap/permutation（L915–919） | `build_paper_docx.py:891`；`outputs/week24_corealign/loro.json` | 部分满足 | 结论已按 18 分子下调口径（τ_b 子集 SD≈0.126）；但 §13.3 期望的"每 LOFO 家族约 10 样本 + 置信区间"因 N=18 **无法满足**，论文以定性限制替代。 | 

### 2.9 Active learning（v2 §14）

| ID | 核心文件条目（§ + 行号） | 项目现有对应物（文件:行） | 判定 | 差距说明 |
| --- | --- | --- | --- | --- |
| I1 | §14.1 $n_T\to\{\tau_b,O_k,R_k\}$（L921–945） | `outputs/week7/stage8_al_curves.csv`；`build_paper_docx.py` 图 17 | 已满足 | 曲线覆盖三个决策量。 | 
| I2 | §14.2 retrospective replay + 轮内 hygiene（L947–958） | `prereg.yaml:155–160` | 已满足 | 隐藏标签 + 每折内部完成标准化/调参。 | 
| I3 | §14.3 四种采集函数 baseline（L960–992） | `prereg.yaml:161` | 已满足 | random/diversity/uncertainty/ranking_aware 全做。 | 
| I4 | §14.4 多种子重复 + CI（L994–996） | `prereg.yaml:163–164`（20 repeats） | 已满足 | 报告 median 与置信区间，未只取最漂亮轨迹。 | 
### 2.10 外部 reference anchors（v2 §15）

| ID | 核心文件条目（§ + 行号） | 项目现有对应物（文件:行） | 判定 | 差距说明 |
| --- | --- | --- | --- | --- |
| J1 | §15.1 气相 anchors：约 8–10 个分子，验证绝对尺度/家族趋势/排序（L1000–1008） | `data/anchors/gas_phase_anchors.csv`（40 行）；`build_paper_docx.py:500`（12 锚点） | 已满足 | 覆盖数超过下限，用于 §3.1 的值误差—排序误差分离。 | 
| J2 | §15.2 液相 anchors：同一实验系列、条件一致的 10–20 分子（L1010–1021） | `data/anchors/ue1994_okoshi2015_oxidation.csv`；`docs/40_week25_gate1_report.md:54` | 部分满足 | 实得**同源序列 7 个核心分子**（21 对），未达 10–20 下限；且为**转录值**（`repo_verification=transcription_only`），仓库未独立复核任何一行。 | 
| J3 | §15.2 数据不可统一时不做跨文献 pooled regression，优先 within-series 相对排序（L1021） | `docs/40:207`；`outputs/week25/series_rel_ordering_check.json` | 已满足 | 只做同源 within-series 排序，未做跨论文绝对 pooling。 | 
| J4 | §15.3 区分"model-to-model 保序"与"experimentally anchored accuracy"（L1023–1031） | `build_paper_docx.py` §5.2/§5.3、:945–954 | 已满足 | 论文明确把 accuracy 声明限定在已验证域内。 | 

### 2.11 条件态、population 与多目标（v2 §16–§18）

| ID | 核心文件条目（§ + 行号） | 项目现有对应物（文件:行） | 判定 | 差距说明 |
| --- | --- | --- | --- | --- |
| K1 | §16.1 $C_1$ 是 conditional coordination experiment，不等于真实平均态（L1035–1047） | `scientific_definitions.yaml:94–105`；`build_paper_docx.py:433–434` | 已满足 | $C_0\to C_1$ 明确标为条件态比较。 | 
| K2 | §16.2 真实 population $\{p_s\}$ 属 Phase II/III（L1049–1072） | `build_paper_docx.py` 表 13 | 已满足 | 明列不做，未用强制 1:1 配合物冒充。 | 
| K3 | §17.1 微溶剂化只做 targeted check：约 8–12 个候选（stable/inversion/high-uncertainty/各家族代表）（L1076–1085） | `outputs/week8/stage9_*.{json,csv}`；`docs/18_week8_report.md` | 部分满足 | 已做 $C_2=[Li(M)_2]^+$，但覆盖分子数与"四类各抽若干"的抽样设计**未确证**（`uncertain`）；化学计量仅 1:2 一种。 | 
| K4 | §17.2 不做不严格的"随意 cluster 指数平均"（L1087–1110） | `scientific_definitions.yaml:239`；`build_paper_docx.py` 表 13 | 已满足 | 明确限定同电荷态/同化学计量才允许 ensemble。 | 
| K5 | §18 不构造 $S=\sum w_iP_i$ 综合分数；$\Delta\Delta G_{bind}$ 不做 maximize；用 Pareto/target window（L1112–1128） | `build_paper_docx.py` 表 13、§5.3 | 已满足 | 氧化/还原两轴并列报告，结合能差只作机制描述符。 | 

### 2.12 分阶段实施方案与 Gate（v2 §19，Stage 0–9 逐条）

| ID | 核心文件条目（§ + 行号） | 项目现有对应物（文件:行） | 判定 | 差距说明 |
| --- | --- | --- | --- | --- |
| L1 | Stage 0 九项冻结操作（L1132–1143） | `docs/00_stage0_definitions.md:14–37`；`config/{prereg,scientific_definitions}.yaml` | 已满足 | core/pool、family/tags/role、方向、embedding、k、tolerance 规则、R、anchor 规则全部冻结。 | 
| L2 | Gate 0：不得看结果后无记录修改（L1145–1147） | `outputs/week1/gate0_record.md`；`统一数据文档.md:25` | 已满足 | `amendment_log` 为空，`--check` 通过。 | 
| L3 | Stage 1 七项操作（L1149–1158） | `docs/02`、`docs/04`、`docs/06` | 部分满足 | 泛函/基组维度未按 §7.1 完整覆盖（见 D1/D3），其余（audit 分子、气相 anchor、solution anchor subset、绝对误差 vs 排序、冻结协议）均已做。 | 
| L4 | **Gate 1**：production protocol 在 state identity / SCF / gas anchor / **solution trend** 上均无系统性失败（L1160–1162） | `outputs/week2/gate1_record.md`（NOT CLOSED）；`outputs/week25/series_rel_ordering_check.json`（τ_b=0.4286） | 未满足 | 气相锚点闭合；**液相排序层首次可评但不一致**（τ_b=0.4286 < 0.9）。论文 §3.15/§5.2 如实登记，未粉饰。 | 
| L5 | Stage 2 broad cheap pool + 输出 cheap chemical-space map（L1164–1177） | `outputs/week3`；`docs/05`；`build_paper_docx.py` 图 2 | 已满足 | 空间覆盖图已出。 | 
| L6 | Stage 3 core free-molecule 电子结构 + $P_0\to P_1$ 是否保序（L1179–1197） | `build_paper_docx.py` §3.2；`outputs/week4` | 已满足 | 已报告 P0→P1 位移与 τ_b。 | 
| L7 | Stage 4 fixed-background continuum + $P_1\to P_2$ robust shift（L1199–1210） | `build_paper_docx.py` §3.3；图 6 | 已满足 | 已报告 common offset / family shift / reorder 判定。 | 
| L8 | Stage 5 conditional Li⁺ coordination 九项 + 相对 ligand-exchange（L1212–1223） | `build_paper_docx.py` §3.5；`outputs/week5` | 已满足 | 含 robust inversion 人工结构审查。 | 
| L9 | Stage 6 输出：τ_b 矩阵 / unresolved / robust / Top-k / regret / **family-resolved / cross-family** 统计（L1229–1251） | `build_paper_docx.py` §3.6–§3.7；`outputs/week9/stage10_ladder.json` | 部分满足 | τ_b/unresolved/robust/Top-k/regret 已报告；**family-resolved 与 cross-family 逐家族统计是否成表未确证**（`uncertain`）。 | 
| L10 | Stage 7 mechanism + Δ-learning（L1253–1261） | `build_paper_docx.py` §3.13；`outputs/week7` | 已满足 | $X^{(2)}$ 仅用于 post hoc 机制解释。 | 
| L11 | Stage 8 active-learning replay（L1263–1279） | `build_paper_docx.py` §3.14；图 17 | 已满足 | 多 seed + CI。 | 
| L12 | Stage 9 optional explicit-microsolvation validation（L1281–1283） | `outputs/week8`（$C_2$） | 已满足 | 明为 optional；项目已做一次（覆盖广度见 K3）。 | 
### 2.13 QC 状态机与计算预算（v2 §20–§21）

| ID | 核心文件条目（§ + 行号） | 项目现有对应物（文件:行） | 判定 | 差距说明 |
| --- | --- | --- | --- | --- |
| M1 | §20 QC 状态机 8 态 + 9 异常分支（L1285–1301） | `src/electrolyte_ranking/qc.py:29–76` | 已满足 | `generated→…→accepted` 与 9 个异常分支均在代码中枚举。 | 
| M2 | §20 异常样本不得当普通缺失值删除，须统计发生率与 family 依赖（L1303） | `build_paper_docx.py` 表 12 | 已满足 | 异常台账逐项列出发生率。 | 
| M3 | §21 Stage 1 后统计 6 项预算指标：median CPU-core-hours、90th pct job cost、failure rate、conformer survival rate、Li-motif survival rate、frequency cost fraction（L1305–1330） | `outputs/**/jobs.csv` 等（分散）；`build_paper_docx.py` 表 12（failure rate 类） | 部分满足 | failure rate 类已报；**median CPU-core-hours、90th pct job cost、conformer/motif survival rate、frequency cost fraction 未见汇总表**（部分指标可从作业目录算出，`uncertain`）。 | 

### 2.14 预期分支与最小成果判据（v2 §22–§23）

| ID | 核心文件条目（§ + 行号） | 项目现有对应物（文件:行） | 判定 | 差距说明 |
| --- | --- | --- | --- | --- |
| N1 | §22 情形 A–G 逐分支认领（L1342–1427） | `outputs/week9/stage10_ladder.json:verdicts`；`build_paper_docx.py` 表 8 | 已满足 | 落 B/D/E，部分触发 G；A/C/F 如实否定。 | 
| N2 | §23 最小成果判据 11 条（L1429–1445） | `outputs/week9/stage10_ladder.json:minimum_outcome_checklist`；`build_paper_docx.py` 表 9 | 已满足 | 10 PASS + 1 PARTIAL（第 5 条外部锚点），PARTIAL 如实保留。 | 

### 2.15 建议核心图（v2 §24，7 张逐条）

| ID | 核心文件条目（§ + 行号） | 项目现有对应物（文件:行） | 判定 | 差距说明 |
| --- | --- | --- | --- | --- |
| O1 | Figure 1：Two-axis model hierarchy + reference layer（L1449–1461） | `build_paper_docx.py` §5.8 表 14（图 1、图 2） | 部分满足 | 现为"图 1（流水线）+ 图 2（化学空间覆盖）"的近似，**缺一张真正的"复杂度 × 条件态 × 外部参考"二维示意图**。 | 
| O2 | Figure 2：External validation and uncertainty audit（L1463–1465） | 表 14 → 图 3、6、9、**19** | 已满足 | 液相维度以新增图 19（F52）承接（本周新增）。 | 
| O3 | Figure 3：Uncertainty-aware rank stability matrix（L1467–1474） | 表 14 → 图 9、10 | 已满足 | τ_b / unresolved / robust 内容齐备。 | 
| O4 | Figure 4：Robust rank-flow map（L1476–1478） | 表 14 → 图 4、5 | 已满足 | 氧化/还原两轴分开呈现。 | 
| O5 | Figure 5：Mechanisms of coordination-induced inversion（L1480–1488） | 表 14 → 图 8、13 | 已满足 | 语义需并读：本项目 $f_{robust\_inv}=0$，图 5 实为"配位改写机制"而非"inversion 机制"（论文已处理）。 | 
| O6 | Figure 6：Direct vs Δ-learning under extrapolation（L1490–1492） | 表 14 → 图 16 | 已满足 | 以 LOFO 为主，非只报 random R²。 | 
| O7 | Figure 7：Minimal expensive-information budget（L1494–1508） | 表 14 → 图 12、15、17、18 | 已满足 | 拆为三层预算 + 合成决策路径。 | 

### 2.16 创新、意义、路线与定位（v2 §25–§30）

| ID | 核心文件条目（§ + 行号） | 项目现有对应物（文件:行） | 判定 | 差距说明 |
| --- | --- | --- | --- | --- |
| P1 | §25.1 不把"ranking/selection"本身当创新（L1512–1516） | `build_paper_docx.py` §5.3、:947 | 已满足 | 明确引用先例 [4]。 | 
| P2 | §25.2 不把"Li⁺ 配位改 redox"当创新，并列出 8 条真正增量（L1518–1536） | `build_paper_docx.py` §5.3、§5.4 | 部分满足 | 8 条增量在 §5.3 归纳为 3 条；feature-cost / external anchor / active learning 三处已分别落在 §2.7/§5.2/§3.14，但**未逐条编号对应**（散落）。 | 
| P3 | §25.3 三个一般方法学命题（L1538–1564） | `build_paper_docx.py` 摘要、§4、§5.3 | 已满足 | 叙事层完整对应，未逐条引用。 | 
| P4 | §26 科学意义 4 点（decision reliability / 足够真实性 / 不确定性入筛选 / negative result 有价值）（L1566–1610） | `build_paper_docx.py` §4、摘要 | 部分满足 | 4 点均散见正文，**未成对照表**逐点认领。 | 
| P5 | §27 Phase II–IV 升级路线（L1612–1645） | `build_paper_docx.py` 表 13、§5.7 | 已满足 | 明列为后续范围。 | 
| P6 | §28 推荐目录结构 + 11 项可追溯字段（L1647–1688） | `scientific_definitions.yaml:340–367`；实际目录 `data/`、`structures/`、`outputs/weekN/` | 部分满足 | 可追溯字段要求已冻结；但物理目录骨架（P0_cheap_proxy/P1_gas_dft/P2_fixed_continuum/…）与仓库实际层级**不同构，未给映射表**。 | 
| P7 | §29 8–12 周执行时间框架（L1690–1718） | 项目实际运行至**第 25 周**（`docs/40`） | 未满足 | 超时约 2 倍；属范围扩张，**论文未显式登记**时间维度偏差（只提样本/锚点限制）。 | 
| P8 | §30 最终项目定位表述（L1720–1754） | `build_paper_docx.py:264`（论文标题）；`统一数据文档.md:8` | 已满足 | 定位与"复杂度/准确性/物种状态/材料决策严格分开"一致。 | 

### 2.17 阅读清单（reading-list）

| ID | 核心文件条目（§ + 行号） | 项目现有对应物（文件:行） | 判定 | 差距说明 |
| --- | --- | --- | --- | --- |
| Q1 | Part I：M1–M7 七项必读（reading-list L29–311） | `docs/14_reading_list_qa.md`；`build_paper_docx.py` 表 10 | 已满足 | 七项均有 QA 记录。 | 
| Q2 | Part I 最低完成标准 8 问（reading-list L313–326） | `docs/14_reading_list_qa.md` §2（Q1–Q8） | 已满足 | 8 问逐题作答。 | 
| Q3 | Part II：A/B/C/D/E 方法依据（reading-list L392–631） | `build_paper_docx.py` 表 10；`docs/16_branch_abcd_qa.md` | 部分满足 | A1/A2/A3、B1/B2、C1/C2、D1/D2/D3、E 已对照；**C3（EDL/speciation）未在表 10 单列**（论文表 13 以 Phase IV 处理）。 | 
| Q4 | "不建议本科阶段先读"5 项（reading-list L633–679） | `build_paper_docx.py` 表 13、§5.7 | 已满足 | SEI 网络/MD/GNN/Marcus/电池工程均声明不做。 | 

### 2.18 判定分布小结

- 逐条对照共 **87 条**：**已满足 63 条**、**部分满足 19 条**、**未满足 5 条**（B1、B2、D3、L4、P7）。
- 5 条"未满足"中，**4 条是预注册/预算的主动取舍**（core/pool 规模、RS-hybrid 单点、时间框架），1 条是**真实未闭合的科学判据**（Gate 1 液相排序层，τ_b=0.4286）。
- 标注 `uncertain` 的条目：B4、C1、D4、K3、L9、M3（共 6 处），均已注明未确证的原因。
---

## 3. Top-8 可继续优化项（按投入产出比排序）

> 全部为**零新增电子结构计算**或低成本文字/汇总工作；每项都对齐到具体论文章节/图。

**1. 论文新增"与核心文件规模的显式偏差表"（对应 B1/B2/H3/J2/P7）**
- 做什么：在 §5 增一小节（或并入表 9 之后），逐行列出：core §5.1 建议 60–100 vs 实得 18；broad §5.1 300–1000 vs 40；solution §15.2 10–20 vs 7；§13.3 60–100 vs 18；§29 8–12 周 vs 25 周，并写明每项处置与后果。
- 为什么值得：这是当前最显眼、且**数据已存在、只差表述**的一类硬性差距；不写等于把最容易被审稿人问的问题留给对方。
- 成本：0.5–1 天，零计算。
- 改进：§5.5/表 11 附近（或新增 §5.9）；同时强化 §23 判据自查。

**2. §5.2 metadata 六字段落表/补列（对应 B3）**
- 做什么：把 `formal_charge`、`conformer_count`、`Li_motif_count`、`state_identity_status`、`reactivity_status`、`qc_status` 从 `outputs/week4`、`week5` 的 JSON 汇总进 `data/metadata`（新列，不改冻结件）或至少在统一数据文档新增字段映射表。
- 为什么值得：§5.2 是硬性字段表，主 metadata 缺 6 项会被直接对照扣分。
- 成本：1–2 天（纯抽取；不动 `core_set.csv` 的既有列语义）。
- 改进：§2.1；`成果输出/统一数据文档.md` 第二节 Week 1。

**3. §24 Figure 1 专用二维层级示意图（对应 O1）**
- 做什么：用 matplotlib 画一张"横轴 = P0/P1/P2，纵轴 = C0/C1/C2，外侧 = R_gas/R_sol/R_env"的示意图（新 F 图 + 图清单），替换表 14 中 Figure 1 的"图 1+图 2"近似。
- 为什么值得：这是 §24 的第一张核心图、也是全文概念骨架；现映射语义不精确。
- 成本：0.5 天（纯绘图脚本 + manifest）。
- 改进：§5.8 表 14、§2.2；新增 1 张图。

**4. §7.1/§19 Stage 1 的 method-audit 偏差与替代显式化（对应 D1/D3/L3）**
- 做什么：在表 10/表 11 增行，明确"两种 DFT functional / ≥2 basis-set level 未做，实际以 xTB-vs-DFT + T5 diffuse control 替代"，并附证据路径。
- 为什么值得：把"未做"与"做错"分开，成本极低、直接回应 §7 的硬性 audit 项。
- 成本：0.5 天。
- 改进：§5.4 表 10、§5.5 表 11。

**5. §21 计算预算台账表（对应 M3）**
- 做什么：从 `outputs/weekN` 的 `jobs.csv` 与作业目录汇总 median CPU-core-hours、90th pct job cost、failure rate、conformer survival rate、Li-motif survival rate、frequency cost fraction；能算的算，算不出的标 `uncertain`。
- 为什么值得：§21 是 Stage 1 后的硬性统计要求，也是"为什么 core set 是 18"的量化依据。
- 成本：1–2 天（纯解析既有作业目录）。
- 改进：§2.6 或扩充 §5.6 表 12。

**6. §28 目录骨架 ↔ 仓库实际路径映射表（对应 P6）**
- 做什么：把 §28 的 `P0_cheap_proxy / P1_gas_dft / P2_fixed_continuum / C1_li_conditional / C2_microsolvation_optional / external_reference / analysis / results` 骨架映射到 `outputs/weekN`、`data/anchors`、`src/` 实际路径。
- 为什么值得：§28 是"可追溯数据结构"的硬性约定，不做映射外部读者无法按图索骥。
- 成本：0.5 天。
- 改进：`成果输出/统一数据文档.md` 新增一节；论文 §2.6 加引用。

**7. §13.3 / §19 Stage 6 的 family-resolved 统计补全（对应 H3/L9）**
- 做什么：对 8 个家族 × 五台阶 × 两轴，补每家族 τ_b / f_unresolved 与 bootstrap CI（数据已在 `outputs/week9/stage10_ladder.json`、`outputs/week24_corealign/loro_folds.csv`）。
- 为什么值得：§13.3 要求"每 LOFO 家族约 10 样本 + 置信区间"，§19 Stage 6 要求 family-resolved / cross-family statistics；目前仅以 18 分子整体口径替代。
- 成本：1–2 天（解析 + 画图）。
- 改进：§3.6、§3.13；图 9、图 16。

**8. §17.1 微溶剂化覆盖声明 + §27 路线映射（对应 K3/P5）**
- 做什么：在表 13 或新增小表写清 $C_2$ 实际覆盖的分子数/化学计量，并显式标注 §17.1 期望的 8–12 候选（stable / inversion / high-uncertainty / 各家族代表）覆盖情况；同时把 §27 的 Phase II–IV 与表 13 对齐编号。
- 为什么值得：K3 目前"做了但覆盖口径不明"，补声明可避免"声称覆盖"的风险；纯表述。
- 成本：0.5 天。
- 改进：§5.7 表 13。

---

## 4. 明确**不建议**做的项及理由

1. **为补齐 §5.1（core 60–100）/§7.3（RS-hybrid 单点）/§17.1（微溶剂化扩样）而新增电子结构计算**。理由：超出当前预算与时间；Gate 0 已冻结"主动缩小到 18 并侧重机制"；改规模须走 amendment 且与"唯一变量"纪律冲突。
2. **回原刊核验 Okoshi 2015 / Ue 1994，或收录 Delp 2016 / Borodin 2013 系列以凑 §15.2 的 10–20 分子**。理由：**沙箱无网络**（WinError 10061），原文不在库；W25 已冻结 `provenance=transcription_only`，引入新来源会变更 Gate 1 的冻结输入表。
3. **推进 Phase II–IV（真实配位 population / MD-AIMD-MLFF / EDL 参考层）**。理由：超出 MVP 与预注册范围，论文表 13 已声明不做（§16.2、§27）。
4. **构造综合电解液分数或 Pareto 前端**。理由：§18（L1112–1128）明确禁止 $\sum w_iP_i$ 式无物理依据的分数。
5. **用数据分位数临时替代外部阈值来报 $E_{decision}$**。理由：`prereg.yaml:118–122` 禁止；无合规来源时只能报 `not_applicable`。
6. **事后剔除 EC 把 Gate 1 的 τ_b 从 0.4286"救回"0.7333**。理由：违反预注册纪律；W25 已声明该剔除只作敏感性、不得替代判据口径（`docs/39:50,55`、`docs/40:118`）。
7. **修改任何冻结件或覆盖 week2 产物**。理由：破坏 Gate 0/Gate 1 可审计性（见 §5）。
8. **为凑 §24 的图数而新增与证据链无关的图**。理由：§24 的意图是"每个证据维度都有对应可视化"，不是图数一致（论文 §5.8 已声明）。

---

## 5. 风险与红线

### 5.1 冻结件与预注册纪律（改动即破坏可审计性）

- **不得改动**：`config/prereg.yaml`、`config/scientific_definitions.yaml`、`scripts/check_series_rel_ordering.py`、`outputs/week2/series_rel_ordering_check.json`、`data/anchors/within_series_ordering.csv`（W25 写入并冻结的判据输入表）；`prereg.yaml:20` 的 `amendment_log` 必须保持为空，任何修改只能 append-only 记录。
- **命名空间纪律**：新增工作必须用新命名空间（如 `week26`），**不得覆盖** `week22`、`week22_hardening`、`week23`、`week24_corealign`、`week25` 的既有产物。

### 5.2 文字与结论红线

- 不得把 $S_{ox/red}$ 简写为"真实电化学稳定窗口"（§4.2；`prereg.yaml:190`）。
- 不得把 $[\mathrm{Li}M]^+$ 描述为 $M$ 的"更高保真度估计"（§3.2；`scientific_definitions.yaml:31`）。
- 不得用接近目标层成本的特征（$X^{(2)}$）证明"低成本预测"（§11.3；`prereg.yaml:150,192`）。
- **Gate 1 未闭合**（液相排序层 τ_b=0.4286 < 0.9，绝对标定层仍缺）→ 论文与对外材料**不得声称液相锚定**；只能表述为"排序层已评估且不一致、绝对标定未封闭"（`docs/40:7,208,210`）。
- 未解析 pair 的任意换序不得称为物理 ranking inversion（§9.2；`prereg.yaml:75`）。
- 报告决策量时必须并列 `f_unresolved`，否则不得宣称"排序稳定"（`prereg.yaml:78,191`）。

### 5.3 与冻结产物冲突的具体风险点

- 任何"重跑 Gate 1 判据脚本以改变 τ_b"的尝试，都会直接覆盖/偏离 `outputs/week2/series_rel_ordering_check.json` 的冻结判决——正确做法是在新的 `weekNN` 命名空间输在新文件里。
- 任何对 `data/anchors/within_series_ordering.csv` 的追加/筛选都会改变冻结输入表，必须走 amendment 记录并同时给出未剔除结果（`docs/39:50`）。
- 论文重建红线：`build_paper_docx.py` 改动后必须仍满足 图 1–19 首次出现单调、表 1–14 单调、中/英文摘要（含 `Key Words`）完整落第 1 页、页眉无乱码（`docs/38` §9.1 的自检断言）。

### 5.4 环境与工具口径风险

- **行号口径**：本环境 `Get-Content` 会错并行 LF 文件（v2 被计为 1279 行、`core_set.csv` 被计为 2 行）。历史 docs 引用"1279 行"应视为该 artifact；后续文档统一采用 `[System.IO.File]::ReadAllLines` 口径，避免误判核心文件被改动。
- **无网络**：任何依赖联网的核验/检索在沙箱内不可执行，相关工作必须显式标注为"未核验/转录值"。