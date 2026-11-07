# Agent 1 报告：框架槽位 ↔ 结题论文 逐节对表

- 核查对象：`E:\Claude Code\电解液溶剂-HB\核心文件\ranking-electrolyte-materials-v2.md`（框架 v2，30 章，1779 行）
- 被核查正文：`E:\Claude Code\电解液溶剂-HB\论文\_dossier\_fulltext_w22.txt`（14 页 PDF 全量抽取，401 行）
- 旁证：`figure_index.txt`（47 图清单）、`paper_numbers.md`、项目产出 `成果输出\week7`（Stage 7／8）、`week8`（Stage 9）、`week11`（Stage 12）
- 生成时间：2026-10-02
- 判定纪律：凡判"缺失"必列出所用检索关键词与命中数；命中 0 者标 `=0`。所有引文均为 `_fulltext_w22.txt` 原文片段，行号以 L 开头。

## 0. 结论摘要（先说最重要的）

1. **论文是"已完成工作的子集"，不是"未做"。** 项目在 `成果输出\week7` 已完整产出 Stage 7（direct vs Δ-learning、ridge→KRR→GPR→RF→GBDT 阶梯、random／group／LOFO 三拆分、selection regret）与 Stage 8（random／diversity／uncertainty／ranking-aware 四采集函数、20 次重复、`n_T → τb` 曲线），图件 `F16_stage7_direct_vs_shift.png`、`F17_stage8_active_learning.png` 俱在，但**这两章一行都没进结题论文**。
2. **框架自定的"最小成果判据"（§23）所列 11 条里，最后四条在论文中全部缺失**——依次是 random／group／LOFO 三拆分、direct vs Δ-learning、feature-cost-aware active-learning replay、high-cost-label budget vs decision accuracy 曲线。这四条恰好全部由项目已完成的 Stage 7／8 覆盖，即论文未达到框架自己写明的最低科学闭环。（注：§23 第 8 条"robust inversion mechanism analysis"论文已通过 §3.5 态身份分析落地，不计入缺失。）
3. **唯一"必须且确实没有数据"的槽位是 §3.3 Axis C 的外部参考层（尤其 R_sol 液相锚点）**；其余缺失项大多"数据现成、只差写进论文"。
4. 论文标题里的"**最小信息预算**"目前只有定性表述（L346–L355），**没有 §14 要求的 `n_T → {τb, O_k, R_k}` 定量曲线**；而框架 §24 明说这张图"很可能是整个项目最具有一般方法学辨识度的一张图"。
5. 十级台阶体系与框架 §19 的 Stage 0–9 **编号已脱钩**：论文 `Stage`／`Gate`／`闸门` 命中均为 0，而项目内部脚本仍在用 `stage7`／`stage8`／`Stage 12/16/19` 编号，外部读者无法把论文台阶映射回框架阶段。

## 1. 总表：框架槽位逐条对表

状态分四档：**落地** ／ **部分落地** ／ **口头提及但无结果** ／ **完全缺失**。"必须"列依据：框架原文出现"必须／不得／至少"等硬性措辞，或列于 §23 最小成果判据 / §24 建议核心图。

| 槽位 | 框架要求（一句话） | 论文状态 | 证据（引文／检索） | 建议动作 |
|---|---|---|---|---|
| §1.2–1.3 数值准确≠决策准确；复杂度≠真实性 | 必须 | 落地 | L145–L158：P0 MAE 1.377 eV／τb 0.606，P1 MAE 0.251 eV／τb 0.727，P0′ MAE 4.481 eV／τb 0.911 | 保持，作为全文主轴 |
| §2.3 不声称完整稳定窗口 | 必须 | 部分落地 | 开篇 L58「电化学稳定性窗口由溶剂的氧化／还原电位排序决定」措辞偏强；全文检索「完整稳定窗口」「stability window」无免责句 | 在 §2.4 或 §4 补一句即得：本文只处理 intact-species 一电子热力学 proxy |
| §3.1 Axis A：P0／P1／P2 | 必须 | 落地 | L102–L107「P0 为 GFN2-xTB…P1 为 ORCA…P2 在 P1 基础上加入 CPCM 隐式溶剂」 | 保持 |
| §3.2 Axis B：C0／C1／C2 | 必须 | 落地 | L107「C0→C1（自由分子 → 1:1 Li+ 配位条件态）…C1→C2（[LiM]+ → 1:2 微溶剂化簇）」 | 保持 |
| **§3.3 Axis C：外部参考层 R_gas／R_sol／R_env** | 必须 | **部分落地** | R_gas 落地 L146「12 个气相锚点（锚点优先取实验测定值）」；R_sol 缺失 L371「液相锚点缺少重复测量…绝对标定的不确定性尚未封闭」；R_env 无：检索「外部参考」=0、「参考层」=0、「Axis C」=0 | 补 within-series 液相排序锚点小节（只做排序、不做绝对标定）；R_env 显式标注为 Phase II |
| §4.1 氧化／还原方向分别定义 | 必须 | 落地 | L126–L131 pox = Ecat−Eneu、pred = −(Ean−Eneu)，两者同向「越大越稳定」 | 保持 |
| §4.2 不把 proxy 简写为真实稳定窗口 | 必须 | 部分落地 | 同 §2.3，检索「稳定窗口」仅命中 L19／L58／L371 | 同上，补免责句 |
| §5.1 Core(60–100) + Broad pool(300–1000) | 必须 | **口头提及但无结果** | L83–L87「核心集包含 18 个溶剂分子…扩展池另含 40 个分子…用于检查结论是否依赖于核心集的选取」；检索「扩展池」仅 1 处（L87），全文无任何 broad-pool 结果 | 补 §3.11 broad-pool 敏感性（哪怕只做 P0 层）；否则删掉该承诺并说明核心集规模限制 |
| §5.2 metadata 多轴（14 字段） | 必须 | 部分落地 | L87「全部分子的标签、家族与供体数取自受控词表」仅点名 3 类字段；检索 `functionalization_tags`／`conformer_count`／`Li_motif_count`／`state_identity_status` = 0 | 附一张 metadata 字段表（14 行），成本极低 |
| §5.3 样本选择原则（单齿／双齿、刚性／柔性、同族取代） | 必须 | 部分落地 | L86 仅说明覆盖 8 个结构家族；检索「双齿」=0、「柔性」仅命中 L74（变量混杂语境） | 在 §2.1 补化学空间覆盖矩阵 |
| §6.1 母分子构象（single→ensemble→expanded） | 必须 | 部分落地 | L114「低能构象空间搜索使用 CREST」；检索「扩展系综」「expanded」=0，无三级采样对比 | 补构象层级敏感性（δm 已含构象项，可复用） |
| §6.2 构象 ensemble（Boltzmann 加权） | 必须 | 部分落地 | L136「δm = max(构象系综的 90 分位展宽, …)」；检索「Boltzmann」「玻尔兹曼」=0 | 说明 ensemble 是否 Boltzmann 加权，还是仅 90 分位包络 |
| §6.3 Li+ motif 生成（9 步枚举） | 必须 | 部分落地 | L335「12 个配位基元」；检索「donor」「ESP minima」「xTB 预筛」=0，无枚举／去重流程 | 补 motif 枚举与去重流程一句话＋附表 |
| §6.4 State identity QC（fragment charge／spin density／SOMO） | 必须 | 落地 | L214「在 11/12 个体系里，还原时电子落在 Li+ 上而不是溶剂分子上」；项目内 `F13_c1_state_identity.png`（Mulliken 投影） | 保持；建议把 F13 补进正文 |
| §6.4 reaction_path_verified 需 TS／动力学证据 | 必须 | **完全缺失** | 检索「reaction_path」「势垒」「NEB」「TS」=0；项目内 `F44_neb_refinement.png` 已有真 NEB 结果未进论文 | 把 F44 收进正文并写明「几何断键≠无势垒」，呼应 §3.8 漏解章 |
| §7.1 method audit（≥2 泛函 + ≥2 基组 + continuum） | 必须 | 部分落地 | 基组项落地 L123「同泛函三基组对照（含弥散函数）…24 个作业」；泛函项缺失：检索「泛函」全文只有 r2SCAN 一种，「ωB97」「B3LYP」「PBE」「M06」「hybrid」「杂化」=0 | 补第二个泛函对照（此条亦为评审 C2 所指） |
| §7.2 几何与频率（r2SCAN-3c Opt+Freq、虚频／自旋污染检查） | 必须 | 落地 | L205–L209 G1→G2 台阶「r2SCAN-3c 的 Opt+Freq 驻点（12 分子审计子集）」 | 保持 |
| §7.3 单点电子能（RSH + triple-ζ，如 ωB97X-D4） | 必须 | 部分落地 | L112 单点即 r2SCAN-3c（meta-GGA）／def2-mTZVPP；检索「ωB97」=0 | 说明为何不采用 RSH，或补一组 RSH 单点作审计 |
| §7.4 生产参数机器可读（15 项） | 必须 | 部分落地 | L138–L140「判据、容差与阈值…写入配置并冻结」；项目内 `feature_manifest.json` 含 `plan_reference` | 附参数清单表（15 行） |
| §8.1 redox 与 association 分开＋显式热力学循环 | 必须 | 部分落地 | L64–L65 提到液相电位热力学循环[3]；但 L115「所有 ΔSCF 结果均取自三态单点计算」，检索「热修正」「thermal」「RRHO」「标准态」=0 | 补热修正抽样（评审 D3），把"0 K 电子能"变成有界声明 |
| §8.2 相对 ligand-exchange 量＋冻结参考配体 R | 必须 | 部分落地 | 图 8 图注 L228 出现「配体交换」；检索「reference ligand」「参考配体」=0，正文未定义 R | 在 §2.6 给出冻结 R 与 ΔΔG_bind(M;R) 定义 |
| §8.3 两类 continuum sensitivity 必须分开 | 必须 | 落地 | SMD 环境层 L186–L197 与 bare CPCM ε 扫描 L273–L289 分列 §3.3／§3.7，未混用 | 保持（这是论文的强项） |
| §9.1 unresolved 定义（δm / zσ） | 必须 | 落地 | L134–L137 δm 合成规则；L131 funresolved 定义 | 保持 |
| §9.2 robust inversion fraction 必须报告 | 必须 | **部分落地（只定义未报数）** | L131 定义 `frobustinv`；检索 `frobust` 全文仅 1 处（即该定义），无任何实测值 | 补 f_robustinv 实测值（数据可从现有产物直接算） |
| §9.3 Kendall τb 优先、Spearman 辅助 | 必须 | 落地 | L130；L232–L235 ρ(std, τb) = −0.8511 等 | 保持 |
| **§9.4 概率化逐对排序 p_ij = P(P_i > P_j)** | 必须 | **完全缺失** | 检索「probabilis」「posterior」「bootstrap」「p_ij」「概率」「后验」「自助」全部 = 0 | 用 bootstrap 给出 p_ij 与 0.9／0.1 判决带；或显式声明列为 Phase II |
| §10.1 Top-k overlap + Jaccard | 必须 | 部分落地 | overlap 落地 L130（k = 10%／20%／30%）；检索「Jaccard」=0 | 补 Jaccard 列（一行公式＋一列数） |
| **§10.2 Selection regret R_k** | 必须 | **完全缺失** | 检索「regret」「selection」=0；项目内 `stage7_ml_results.csv` 已有 `R20%` 列 | 直接回填 R_k（数据现成） |
| **§10.3 Threshold-based decision error E_decision** | 必须 | **完全缺失** | 检索「threshold」「decision error」「决策错误」=0；「阈值」6 处均为 δm／A_axis 判据阈值，非外部设计要求阈值 | 若确无外部阈值来源，需明确声明该指标不适用（框架要求"不允许事后挑阈值"） |
| **§11 Descriptor 与 feature-cost accounting（X0／X1／X2）** | 必须 | **完全缺失** | 检索「feature」「成本」「X(0)」=0；项目内 `feature_manifest.json` 已有 `feature_cost_levels` X0／X1／X2 与 `x2_policy` 断言 | 回填成本分级表（数据现成，直接回应"虚假低成本预测"风险） |
| **§12 Δ-learning（direct vs conditional-shift）** | 必须 | **完全缺失** | 检索「Δ-learning」「delta-learning」「direct model」=0；项目内 `stage7_ml_summary.md` 有 direct τb 与 shift τb 全表 | 回填 Stage 7（数据现成、图 F16 现成） |
| **§13.1 模型复杂度阶梯（ridge→KRR→GPR→RF／GBDT）** | 必须 | **完全缺失** | 检索「ridge」「KRR」「GPR」「random forest」「梯度提升」=0；项目内 stage7 已跑 6 级阶梯 | 回填 |
| **§13.2 random／group／LOFO 三拆分必须同时报告** | 必须 | **完全缺失** | 检索「LOFO」「group split」「scaffold」「random split」=0；项目内 stage7 与 `F16(b)` 已有 | 回填（即框架 §23 第 8 条） |
| §13.3 统计边界（bootstrap／permutation CI） | 必须 | 部分落地 | L261–L262「N = 10 的子集上重抽 2000 次，τb 的抽样标准差为 0.1264」；检索「bootstrap」=0，无置信区间 | 补 bootstrap CI（评审 B1／B2 亦指向此） |
| **§14 Active learning（n_T→τb／O_k／R_k，4 baseline，多次重复，校准检查）** | 必须 | **完全缺失** | 检索「active learning」「主动学习」「acquisition」「采集」=0；项目内 `stage8_al_summary.md` 有 4 baseline × 6 任务 × 20 次重复、2.5–97.5 分位带，图 F17 现成 | 回填 Stage 8（即框架 §23 第 10 条） |
| §15.1 Gas-phase anchors（8–10 个） | 必须 | 落地 | L146 表 1「12 个气相锚点…锚点优先取实验测定值」 | 保持 |
| **§15.2 Solution redox anchors（10–20 个，同系列）** | 必须 | **完全缺失** | L371 局限承认；检索「液相锚点」仅 1 处（即该局限句） | 补 within-series 液相排序锚点（评审 D2 建议 Okoshi 2015 16 溶剂表） |
| §15.3 model-to-model 与 experimentally anchored 声称分离 | 必须 | 部分落地 | 全文未出现"experimentally anchored"类过强声称（诚实）；但也未显式声明边界 | 补一句显式声明即可 |
| §16.1 C1 = conditional coordination experiment | 必须 | 落地 | L107「是条件态的比较…不能解释为精度改善」 | 保持 |
| §16.2 真实体系需要 population | 非 MVP（Phase II／III） | 完全缺失（设计如此） | 检索「population」「speciation」=0 | 在局限中显式点名，避免读者误读为真实体系平均 |
| §17.1 显式微溶剂化 targeted（8–12 个） | 必须 | 落地 | L107 C1→C2 条件态台阶；L228 图 8；项目内 F18 | 保持 |
| §17.2 不做不严格的 cluster Boltzmann 平均 | 必须 | 落地 | L341「跨层级的绝对数值一律不得并列（两层的 IP／EA 相差 eV 量级）」 | 保持 |
| §18 多目标：不构造武断综合分数 | 必须 | **完全缺失** | 检索「多目标」「Pareto」=0 | 补一小节或声明本文为单目标范围 |
| **§19 Stage 0–9 与 Gate 0／1** | 必须 | **完全缺失** | 检索「Stage」「Gate」「闸门」=0；论文用十级台阶，项目脚本用 `stage7`／`stage8`／`Stage 12/16/19`，两套编号未做映射 | 加一张 Stage↔台阶对照表；并补 Gate 1（液相锚点）开放状态说明 |
| §20 QC 状态机（9 类异常分支＋发生率） | 必须 | **完全缺失** | 检索「QC」「状态机」「scf_failed」「accepted」=0；项目内 `verification.json` 已有部分机器可读状态 | 补异常台账表（发生率＋family 依赖） |
| §21 计算预算量化（core-hour／p90／失败率／存活率） | 必须 | **完全缺失** | 检索「CPU」「core-hour」「机时」=0；全文仅报作业计数（24 作业、360 格、120 格、660 对） | 补机器可读预算台账 |
| §21 只在近简并点升级热化学（思想） | 部分 | 落地（类比） | L291–L317 靶向双腿策略以 A_axis 阈值框住 | 保持并与 §21 思想交叉引用 |
| §22 预期结果分支 A–G | 必须 | 部分落地 | §22.2（幅值大排序稳）对应 L186–L197；§22.4（态身份改变）对应 L211–L217；§22.7（大量 unresolved）对应 L214 funresolved 0.800；但无显式分支枚举 | 加分支对照小表（一行一支） |
| **§22.7 大部分 pairs unresolved → 输出等价类／tiered sets** | 必须 | **完全缺失** | L214「未解析对比例高达 0.800」= 情形 G 触发；但检索「等价类」「Tier」「分层」=0，未给 tier 输出 | 补 tier／等价类输出表（这是情形 G 的正确收尾） |
| §23 最小成果判据（11 条） | 必须 | 部分落地 | 第 1／4／5／7／8 条落地（第 8 条 robust inversion 机理见 L211–L217 态身份分析）；第 2 条口头（L87）；第 6 条仅气相半条；**最后四条（9 random／group／LOFO、10 direct vs Δ-learning、11 active-learning replay、11 预算-精度曲线）完全缺失** | 见第 2 节「最值得补的 5 个槽位」 |
| §24 Figure 1：两轴模型层级＋参考层 | 必须 | 部分落地 | L94 图 1 实为 §30 的五段式流水线，**不是**两轴层级图；外部参考层未出现在任何图中 | 补 Axis C 参考层到图 1，或新增一张两轴图 |
| **§24 Figure 7：最小昂贵信息预算 n_T→{τb, O_k, R_k}** | 必须 | **完全缺失** | 检索「n_T」=0；项目内 F17／F23 已有 | 回填（框架称其为"最具有一般方法学辨识度"的一张图） |
| §25.3 三个一般性命题 | 必须 | 部分落地 | L356–L369 结语三点；第 3 命题（最小信息成本）仅定性 | 与 Figure 7 一并回填 |
| §28 可追溯数据结构 | 必须 | 部分落地 | L138–L140「可用 --check 逐字节复核…文档与图表均可追溯到具体的产物路径」 | 附追溯字段表（11 项） |
| §30 五段式工作流定位 | 必须 | 落地 | L94 图 1 图注与框架 §30 完全一致 | 保持 |
## 2. 最值得补的 5 个槽位（按投入产出排序）

### 第 1 位：§14 Active learning ／ §24 Figure 7「最小昂贵信息预算」

- 现状：论文标题与 §3.10 都以"最小信息预算"收尾（L346–L355），但全篇没有任何 `n_T → 判决指标` 的定量曲线；检索「active learning」「主动学习」「acquisition」「采集」「n_T」全部 = 0。
- 为什么最值得：① 框架 §24 明说 Figure 7「很可能是整个项目最具有一般方法学辨识度的一张图」；② 它是 §23 第 10／11 条最小闭环；③ 现在标题关键词处于"只有主张、没有曲线"的状态，审稿人必然追打。
- 现成材料：`成果输出\week7\stage8_al_summary.md`（4 baseline × 6 任务 × 20 次重复、2.5–97.5 分位带、判据"median τb 首次 ≥ 0.80 的 n_T"）；`stage8_al_curves.csv`；图 `F17_stage8_active_learning.png`；`F23_prescreening.png`（预算曲线）。
- 具体补法：新增 §3.11「最小昂贵信息预算：n_T → τb」，放入 F17；正文报两条实测结论即可——C／氧化任务 8–9 次昂贵计算即达 τb ≥ 0.80（random 9／uncertainty 8），E／氧化需 12–15 次；并必须原样保留 stage8 摘要里的诚实边界（"core set 只有 18（C 任务 10）个分子…不得给出真实项目需要买多少张 DFT 的定量外推"）。

### 第 2 位：§12 Δ-learning ＋ §13.2 random／group／LOFO ＋ §13.1 模型阶梯 ＋ §10.2 selection regret

- 现状：这四项在论文里检索命中全为 0，但属同一批 Stage 7 产物，一次补写即可同时关掉框架 §23 的第 8、9 条。
- 现成材料：`成果输出\week7\stage7_ml_summary.md`（direct τb 与 shift τb 逐任务全表、LOFO 主证据、`O20%`／`R20%` 两列 regret）；`stage7_ml_results.csv`；图 `F16_stage7_direct_vs_shift.png`（(a) LOFO 最优模型、(b) random／group／LOFO 乐观偏差、(c) τb(shift) − τb(direct)）。
- 具体补法：新增 §3.12「直接学习 vs 条件位移学习」。可直接引用三条硬结论：环境任务上 shift 模型 τb 0.882–0.922 显著优于 direct 0.529–0.843；配位任务 shift 全线优于 direct（氧化 direct 甚至为负）；LOFO 是主证据、random 划分高估可迁移性。同时把 `feature_manifest.json` 的 `x2_policy`（X2 列永不进入特征集）写成一句方法学声明，直接对上框架 §11.3。

### 第 3 位：§3.3 Axis C 外部参考层，优先 R_sol 液相锚点

- 现状：这是**唯一"框架要求必须、且项目确实没有数据"**的槽位。R_gas 已落地（12 个气相锚点），R_sol 只在局限里被承认（L371），R_env 全无。
- 为什么必须补：框架 §15.3 明确——没有 external anchor 时只能声称"模型 A 能否恢复模型 B 的排序"，**不能**声称"experimentally anchored ranking decisions"。当前论文的所有结论都停在 model-to-model 层，却缺少这句限定。
- 具体补法（降级关门，不需新算量化）：只做 **within-series 排序一致性**——取同一实验系列（同溶剂／盐／温度／参比电极）的 10–20 个分子，比较实验相对次序与 P2 相对次序，报 Spearman／τb，**不做绝对标定回归**。评审 D2 已给出候选来源（Ue 等系列、Okoshi 2015 的 16 溶剂对照表，EC／PC／EMC／BC／DOL／sulfolane／GN／MPN 与核心集高度重叠）。同时在 §2.6 补一句显式边界表述。

### 第 4 位：§9.4 概率化逐对排序 ＋ §9.2 f_robustinv 实测值 ＋ §10.1 Jaccard

- 现状：三者都是"框架必须、论文只做了一半"——`frobustinv` 在 L131 被定义后全文再无引用与数值；Jaccard 检索 = 0；p_ij 全无。
- 为什么值得：成本极低（都能从现有位移／分数矩阵直接算），但直接回应外部评审 B1（n=10 的 ρ 需加固）与 B2（Δτb 处于显著性边缘）——把点估计升级为带不确定性的概率判决。
- 具体补法：① 用现有 bootstrap（framework §9.4 阈值 p_ij > 0.9／< 0.1）给出关键 pair 的 p_ij，取代"伪确定顺序"；② 把 §2.4 定义的 f_robustinv 补上实测值（每台阶一行）；③ 表 2 增加 Jaccard 列。三处合计约半页。

### 第 5 位：可审计性三表打包（§11 特征成本分级 ＋ §19 Stage↔台阶映射 ＋ §20 QC 状态机台账）

- 现状：§11／§19／§20／§21 四章在论文中命中全为 0，而这三张表几乎零计算成本——纯写作即可补齐，且是审稿人"对不上数"时最先要的东西。
- 现成材料：`feature_manifest.json`（X0／X1／X2 分级 + `x2_policy`）；项目 `stage7`／`stage8`／`Stage 12/16/19` 编号（做 Stage↔十级台阶映射表的依据）；`verification.json`（QC 状态与异常分支）。
- 具体补法：① §2.6 后加"特征成本分级表"（X0 12 项／X1 6 项／X2 4 项）；② §2.2 加"框架 Stage ↔ 论文台阶"映射表（Stage 3→P0→P1，Stage 4→P1→P2，Stage 5→C0→C1，Stage 9→C1→C2，Stage 6→§3.6，Stage 7/8→待补 §3.12／§3.11）；③ 附录加"异常状态台账"（scf_failed／unbound_anion／motif_switch 等分支及发生率）。
- 附：把项目已有的 `F44_neb_refinement.png`（真 NEB 取代直线插值，最松一格峰高被高估 30 倍）补进 §3.8 或 §3.10，可同时补上框架 §6.4"reaction_path_verified 需 TS／动力学证据"这一完全缺失项。

## 3. 按"是否需新算"分类（供排期用）

| 类别 | 槽位 | 说明 |
|---|---|---|
| 纯写作即可补齐（数据／图件现成） | §10.1 Jaccard、§10.2 regret、§11 特征成本表、§12 Δ-learning、§13.1 模型阶梯、§13.2 三拆分、§14 active learning、§19 Stage 映射、§20 QC 台账、§22.7 tier 输出、§24 Figure 7、§6.4 NEB（F44） | 占全部缺失槽位的多数；建议优先，成本以"天"计 |
| 低成本补算／可直接从产物重算 | §9.2 f_robustinv 实测值、§9.4 p_ij bootstrap、§13.3 bootstrap CI、§21 预算台账（从日志统计） | 无需新量化作业 |
| 需新计算或有外部依赖 | §3.3 R_sol 液相锚点（需文献数据整理，可降级为纯排序）、§7.1 第二泛函对照（需新 DFT 审计）、§8.1 热修正抽样（xTB 级即可）、§5.1 broad-pool 结果（40 分子已建、差结果） | 建议排入后续 week；R_sol 与第二泛函优先级最高 |
| 建议显式声明为 Phase II／不适用的槽位 | §10.3 threshold decision error（无外部阈值来源）、§16.2 population、§18 多目标 Pareto、§3.3 R_env | 明写"第一阶段不做及为何"，反而符合框架 §2.3 纪律 |

## 4. 核查方法与可复现性

- 框架槽位清单来源：对 `ranking-electrolyte-materials-v2.md` 逐章抽取 `^#{1,3}\s` 标题（30 章、含 3 个 Axis 与 9 个 Stage），再对每章正文提取"必须／不得／至少"硬性措辞与 §23 判据条目。
- 论文侧检索方式：对 `_fulltext_w22.txt` 逐行正则匹配。关键空结果关键词与命中数——`probabilis`=0、`posterior`=0、`bootstrap`=0、`regret`=0、`threshold`=0、`decision error`=0、`active learning`=0、`acquisition`=0、`feature_cost`=0、`LOFO`=0、`ridge`=0、`KRR`=0、`GPR`=0、`Jaccard`=0、`Stage`=0、`Gate`=0、`QC`=0、`CPU`=0、`population`=0、`Pareto`=0、`ωB97`=0、`外部参考`=0、`参考层`=0。
- 非空但需区分的：`阈值`=6（均为 δm／A_axis 判据阈值，非 §10.3 的外部设计要求阈值）、`预算`=12（均为"不确定度预算"，非 §21 的计算预算）、`frobust`=1（仅定义，无数值）、`descriptor`=2（仅英文标题与摘要措辞，非 §11 的 feature-cost accounting）。
- 图件归属判定：`figure_index.txt` 共 47 图（F0–F46），但 `build_paper_docx.py` 仅引用 F0／F1／F3／F4／F5／F8／F10／F12／F19／F20／F24／F45／F46 共 13 图，与 14 页 PDF 的 13 图一一对应；F16／F17／F18／F22／F23／F28／F31／F44 等均**存在于项目产物但未进论文**，故这些槽位判"论文缺失"而非"工作缺失"。