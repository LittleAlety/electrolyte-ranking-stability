# Week 24 核心文件对照审计表（W24-C）

本文件给出三张可直接粘进论文附录/方法节的中文三线表：① 核心文件 §19 的 Stage 0–9 ↔ 论文十级台阶映射；② QC 状态机台账（§20 + 全部现存 warning/flag 字段）；③ 第一阶段显式“不做”声明表。全部输入只读，零新增电子结构计算；每个数字都从既有产物的真实字段读取，未确证的映射标“待确认”。

## 表 1  核心文件 §19 Stage 0–9 ↔ 论文十级台阶映射

| 核心文件 Stage | 实际计算内容 | 对应论文台阶 | 产物路径 | 证据强度(确证/待确认) |
| --- | --- | --- | --- | --- |
| Stage 0 冻结科学定义与 metadata | 冻结目标量方向、Top-k 比例（10/20/30%）、δ 确定规则、reference ligand R=DME、anchor 搜集规则；建立 core set（18）与 broad pool（40）的 chemical-space metadata；Gate 0 CLOSED。 | 不产生台阶（定义冻结层） | config/scientific_definitions.yaml；config/prereg.yaml；outputs/week1/gate0_record.md；data/metadata/core_set.csv | 确证 |
| Stage 1 方法审计与 external anchors | 12 个 method-audit 分子的 GFN2-xTB 三态审计（Koopmans vs ΔSCF）；气相 anchor 对照；31 行溶液锚点逐条审计（全部 method=est，0 exp / 0 calc）；production protocol DRAFT-FROZEN；Gate 1 NOT CLOSED。 | 方法审计（不产生台阶；其 τ_b / MAE 用于解释 P0→P1） | outputs/week2/method_audit_xtb.csv；outputs/week2/method_audit_xtb_summary.json；outputs/week2/solution_anchor_audit.json；outputs/week2/gate1_record.md | 确证 |
| Stage 2 Broad cheap pool | canonical 结构 + RDKit descriptors + CREST/GFN2-xTB 单构象优化，得到 X(0) 与 P0 标量代理；broad pool 40/40 + core 18/18 = 58/58 收敛、0 失败。 | P0 起点臂（十级台阶的起始层，本身不单独成台阶） | outputs/week3/p0_broad_pool.csv；outputs/week3/p0_core_set.csv；outputs/week3/p0_summary.json | 确证 |
| Stage 3 Core free-molecule electronic structure | core 18 分子三态 r2SCAN-3c 垂直 P1@G1（54/54，独立复核 0 分歧）；同一 12 分子子集做 G2 = r2SCAN-3c Opt+Freq（12 + 36 作业，0 失败）；unbound-anion QC。 | P0→P1（氧化/还原）与 G1→G2（氧化/还原）两个物理台阶 | outputs/week4/p1_core_set.csv；outputs/week4/p1_core_set_audit.json；outputs/week4/p1_decision_stability.json；outputs/week4/t2_opt_freq_summary.json | 确证 |
| Stage 4 Fixed-background continuum | 全部 core N=18 使用同一 production 连续介质设置（CPCM / SMD，乙腈 ε=35.688）得到 P2；12 分子审计子集做 dielectric-only 扫描（bare CPCM ε=5/10/20/40，144/144）。 | P1→P2（氧化/还原） | outputs/week4/p2_core_set_smd_acetonitrile.csv；outputs/week4/p2_decision_stability.json；outputs/week4/t3_cpcm_eps_scan_summary.json | 确证 |
| Stage 5 Conditional Li+ coordination | donor/motif 枚举（46 候选 -> 12 motif）；xTB 预筛；10 分子 C1 = [LiM]+ 三态 r2SCAN-3c（92 作业）；state-identity QC；ΔΔG_coord 与相对 ligand-exchange ΔΔG_bind。 | C0→C1（氧化/还原） | outputs/week5/li_motif_generation.json；outputs/week5/c1_li_coordination.csv；outputs/week5/c1_decision_stability.json；outputs/week5/c1_state_identity.json | 确证 |
| Stage 6 Uncertainty-aware ranking analysis | Kendall τ_b / f_unresolved / robust-inversion / Top-k / selection regret + bootstrap；δ_m 组装（T6 构象系综、T7 C1 虚频、T8 δ_m、T9 三口径决策稳定性）。 | 不产生新台阶（对全部十级台阶产出统计量，即论文表 2） | outputs/week6/delta_m_frozen.json；outputs/week6/stage6_decision_stability.json；outputs/week6/t7_c1_freq_check.json；outputs/week9/stage10_ladder.json（论文表 2 取数源） | 确证 |
| Stage 7 Mechanism analysis + Δ-learning | X(0)/X(1)/X(2) 特征成本分级；6 模型复杂度阶梯；random/group/LOFO 三拆分；direct vs Δ-learning；robust inversion 结构机制；X(2) 仅作 post hoc 解释。 | 不产生台阶（机制/学习层；论文 v2 命中 0，W24 计划补入 §3.13） | outputs/week7/feature_manifest.json；outputs/week7/stage7_ml_results.json（288 行）；outputs/week7/stage7_ml_predictions.csv | 确证 |
| Stage 8 Active-learning replay | random / diversity / uncertainty / ranking-aware 四采集函数；20 组种子重复；n_T -> τ_b / O_k / R_k 曲线与最小昂贵信息预算。 | 不产生台阶（主动学习层；论文 v2 命中 0，W24 计划补入 §3.14） | outputs/week7/stage8_al_curves.csv（296 行，含 2.5/97.5 分位）；outputs/week7/stage8_al_results.json；outputs/week7/stage8_al_runs.csv | 确证 |
| Stage 9 Optional explicit-microsolvation validation | 只对 12 个关键 motif 做 targeted check：homoleptic [Li(M)2]+ 第一溶剂壳（xTB 刚体放置 -> xTB 单点打分 -> DFT Opt + 三态单点 36 作业），给出 C1 vs C2 排序稳定性。 | C1→C2（氧化/还原） | outputs/week8/ms_shell_generation.json；outputs/week8/stage9_results.json；outputs/week8/stage9_shell_shifts.csv；outputs/week8/stage9_decision_stability.csv | 确证 |

> **结论**：核心文件 §19 的 Stage 3/4/5/9 分别产出论文十级台阶里的 P0→P1、P1→P2、C0→C1、C1→C2 四个物理台阶，并（在 Stage 3 的 T2 子任务里）产出 G1→G2，合起来正好是“5 个物理台阶 × 2 条轴 = 10 级”；Stage 0/1/2/6/7/8 只做定义冻结、方法审计、P0 起点层、统计层与机制/学习层，**不产生台阶**。待确认 0 条。

> 论文的“十级台阶”= 5 个物理台阶（P0→P1、P1→P2、G1→G2、C0→C1、C1→C2）× 2 条轴（氧化/还原）。项目内部 Stage 编号在 0–9 与核心文件 §19 一致（`成果输出/数据结果汇总.md` §2），10–24 为超出核心文件的扩展（Stage 10 五级台阶合成 … Stage 24 R8 靶向双腿）。论文表 2 的取数源为 `outputs/week9/stage10_ladder.json`（Stage 10 合成，投影自 Stage 3/4/5/9 产物）。核心文件 §19 没有独立的“几何”Stage，G1→G2 归属 Stage 3 是项目文档（`docs/11` §2 把 T2 记在 Stage 3 下）的归档口径。

## 表 2  QC 状态机台账（核心文件 §20 九类异常 + 全部现存 warning/flag 字段）

| 状态/异常 | 含义 | 发生数/总数 | 发生率 | 证据文件 | 论文中的处置 |
| --- | --- | --- | --- | --- | --- |
| scf_failed | 自洽场求解失败（字面字段，与“多解 / 漏解”是两件事） | P1 core（54 记录）: 0/54；C1 配位态（92 作业）: 0/92；Stage 9 壳层（12 壳）: 0/12 | P1 core 0.0%；C1 配位态 0.0%；Stage 9 壳层 0.0% | outputs/week4/p1_core_set_audit.json:flag_counts.scf_failed；outputs/week5/c1_li_coordination_summary.json:qc_flag_counts.scf_failed；outputs/week8/ms_shell_generation.json:qc_flag_counts.scf_failed | 论文未报告字面 scf_failed 计数（关键词命中 0）；§3.8 讨论的是“自洽场多解 / 漏解”，与该字段计数为 0 不矛盾。 |
| 自洽场多解：默认初猜漏解 | 默认初猜落到能量偏高的亚稳态；与 moread 初猜配对普查（Stage 16 目录） | 12 分子 x 3 态 x 10 个 ε = 360 格: 32/360 | 12 分子 x 3 态 x 10 个 ε = 360 格 8.9% | outputs/week15/stage16_catalogue_analysis.json:n_material_differences / n_cells | §3.8 全量报告（328/360 一致、32 更低、0 更高、最大缺陷 −0.285961 eV）。 |
| 自洽场多解：第二解弛豫存亡 | 第二个 SCF 解在几何弛豫后是否仍是更低的那个（Stage 19） | 37 个差异格: 5/37 | 37 个差异格 13.5% | outputs/week18/stage19_relax_analysis.json:aggregates.all.all.outcomes.distinct_lower / n_cells | 论文未报告（关键词命中 0）——建议随本台账补入 §3.8 附录。 |
| 自洽场多解：跨引擎存亡 | 同一批第二解在 xTB 级弛豫后是否仍更低（Stage 20，跨方法） | 37 个差异格: 15/37 | 37 个差异格 40.5% | outputs/week19/stage20_xtb_arms_analysis.json:aggregates.all.all.outcomes.distinct_lower / n_cells | 论文未报告（关键词命中 0）——建议随本台账补入 §3.8 附录。 |
| 漏解引起的 pair 翻转（R8 靶向双腿） | 漏解真实改写的分子对；安全阈值 A_axis = 单格最大效应量 | 氧化轴（660 对）: 19/660；还原轴（660 对）: 21/660 | 氧化轴 2.9%；还原轴 3.2% | outputs/week23/targeted_two_guess.json:axes.*.n_flips / n_pairs；outputs/week22_hardening/allowance_factor2.json:axes.*.two_times_A_axis_ev | §3.8 表 3 报告（氧化 19 次 / 还原 21 次，靶向漏 0）；严格上界为 2·A_axis（0.3045 / 0.5719 eV，见 allowance_factor2.json）。 |
| unbound_anion | 气相阴离子不束缚（带负电荷态出现正 HOMO） | P1 core（18 分子）: 18/18；C1 配位态（92 作业）: 0/92 | P1 core 100.0%；C1 配位态 0.0% | outputs/week4/p1_core_set_audit.json:flag_counts.unbound_anion；outputs/week5/c1_li_coordination_summary.json:qc_flag_counts.unbound_anion | §2.3 / §3.3 报告 18/18 并说明气相 EA 只在趋势上有意义，定量比较需溶剂化或弥散基组（T5 弥散对照 24 作业）。 |
| motif_switch | 配位 motif 改变（放置 / 优化后与实际接触模式不一致） | Li motif 枚举（46 候选）: 32/46；保留 12 motif 的行: 9/12；Stage 9 壳层 shell1（12 motif）: 9/12 | Li motif 枚举 69.6%；保留 12 motif 的行 75.0%；Stage 9 壳层 shell1 75.0% | outputs/week5/li_motif_generation.json:qc_flag_counts.motif_switch；outputs/week8/stage9_results.json:shifts[].qc_flags = shell1:motif_switch | 论文未报告（motif 关键词命中 0）——建议随本台账补入附录。 |
| no_intact_minimum_found | 优化后 Li–M 最小接触消失（几何优先于电子标签） | Li motif 枚举（46 候选）: 1/46；C1 扫描（92 作业）: 4/92；C1 态身份：dication（12 行）: 4/12；C1 态身份（24 行）: 4/24 | Li motif 枚举 2.2%；C1 扫描 4.3%；C1 态身份：dication 33.3%；C1 态身份 16.7% | outputs/week5/li_motif_generation.json:qc_flag_counts.no_intact_minimum_found；outputs/week5/c1_li_coordination_summary.json:qc_flag_counts.no_intact_minimum_found；outputs/week5/c1_state_identity.json:per_redox_state.dication.labels | §3.5 用了态身份分析（还原态 11/12 电子落在 Li 上），但未单列本 QC 计数。 |
| geometry_failed | 几何优化失败（唯一一例为 SL/m1 dication，ORCA 超时被 kill） | C1 扫描（92 作业）: 1/92；Li motif 枚举（46 候选）: 0/46 | C1 扫描 1.1%；Li motif 枚举 0.0% | outputs/week5/c1_li_coordination_summary.json:qc_flag_counts.geometry_failed | 论文未报告（geometry_failed 关键词命中 0）。 |
| 虚频 imaginary_mode_unresolved | 驻点 Hessian 存在虚频（不是局部极小） | T2 几何台阶（12 分子 Opt+Freq）: 2/12；T7 C1 [LiM]+ Freq（10 分子）: 1/10 | T2 几何台阶 16.7%；T7 C1 [LiM]+ Freq 10.0% | outputs/week4/t2_opt_freq_summary.json:n_imaginary_unresolved / n_opt_jobs；outputs/week6/t7_c1_freq_check.json:n_imaginary / n_molecules | 论文未报告（虚频 关键词命中 0）——EC 的 [LiEC]+ 在 −80.4 cm⁻¹ 有虚频，其 C0→C1 位移系鞍点测量，应写入局限。 |
| dissociated_optimized_product | 优化后母体连接断裂（解离产物） | Li motif 枚举（46 候选）: 1/46；C1 扫描（92 作业）: 0/92；Stage 9 壳层（12 壳）: 0/12 | Li motif 枚举 2.2%；C1 扫描 0.0%；Stage 9 壳层 0.0% | outputs/week5/li_motif_generation.json:qc_flag_counts.dissociated_optimized_product；outputs/week5/c1_li_coordination_summary.json:qc_flag_counts.dissociated_optimized_product | 论文未报告（关键词命中 0）；Stage 9 的 12 壳层 second_ligand_intact 全 True。 |
| state_identity_ambiguous | 态身份指标冲突（无法判定电子落在 Li 还是分子） | C1 扫描（92 作业）: 0/92 | C1 扫描 0.0% | outputs/week5/c1_li_coordination_summary.json:qc_flag_counts.state_identity_ambiguous | §3.5 报告态身份分类（11/12 Li-centered），本字段计数为 0。 |
| spin_contamination_flag | 自旋污染（<S²> 偏离） | P1 core（54 记录）: 0/54；C1 扫描（92 作业）: 0/92 | P1 core 0.0%；C1 扫描 0.0% | outputs/week4/p1_core_set_audit.json:flag_counts.spin_contamination_flag；outputs/week5/c1_li_coordination_summary.json:qc_flag_counts.spin_contamination_flag | 论文未报告（关键词命中 0）；交付层断言 p1_audit.spin_contamination_flag==0 通过。 |
| electron_count_mismatch | 电子数不一致 | C1 扫描（92 作业）: 0/92 | C1 扫描 0.0% | outputs/week5/c1_li_coordination_summary.json:qc_flag_counts.electron_count_mismatch | 论文未报告（关键词命中 0）。 |
| execution_failed | 作业级执行失败（非物理失败） | C1 扫描（92 作业）: 1/92 | C1 扫描 1.1% | outputs/week5/c1_li_coordination_summary.json:status_counts.execution_failed | 论文未报告（关键词命中 0）；该例同时是 geometry_failed（SL/m1 dication 超时）。 |
| abnormal_termination / energy_mismatch / missing_output | ORCA 输出异常终止 / 能量解析不一致 / 输出缺失 | P1 core abnormal_termination（54 记录）: 0/54；P1 core energy_mismatch（54 记录）: 0/54；P1 core missing_output（54 记录）: 0/54 | P1 core abnormal_termination 0.0%；P1 core energy_mismatch 0.0%；P1 core missing_output 0.0% | outputs/week4/p1_core_set_audit.json:flag_counts.abnormal_termination / energy_mismatch / missing_output | 论文未报告（关键词命中 0）；交付层三条断言全部通过。 |
| placement_clash_start | 壳层放置回退（起点与 Li+ 球面冲突，按事前规则放宽并记录） | Stage 9 壳层（12 壳）: 2/12 | Stage 9 壳层 16.7% | outputs/week8/ms_shell_generation.json:shells[].qc_flags = placement_clash_start | 论文未报告（关键词命中 0）；涉及 DMC/m2 与 TMP/m2，几何完好（Li 接触数 4 与 6）。 |
| warning（Stage 21 refill） | 记录型警示字符串（非计数型异常） | Stage 21 refill 警示条数: 1/1 | Stage 21 refill 警示条数 100.0% | outputs/week20/stage21_refill.json:coverage.warning | 论文未报告（关键词命中 0）；内容为“严格 P2 腿（SMD）的弛豫覆盖为 0”，属过程警示。 |
| 交付包 verification.json 断言 | 交付层自动断言（含文件 SHA256 与现场取数核对），23 个交付包 | checks 通过 / 总数: 372/372 | checks 通过 / 总数 100.0% | 成果输出/week1/verification.json（13 checks）；成果输出/week10/verification.json（22 checks）；成果输出/week11/verification.json（26 checks）；成果输出/week12/verification.json（17 checks）；成果输出/week13/verification.json（17 checks）；... | 论文 §2.6 声明“可用 --check 逐字节复核”；交付层 0 条断言失败。 |

> **结论**：19 类状态/异常中，6 类在论文中有落点，13 类（scf_failed、自洽场多解：第二解弛豫存亡、自洽场多解：跨引擎存亡、motif_switch 等）论文正文命中为 0，需随本台账补入附录；核心集 P1 唯一的高发异常是气相阴离子不束缚（18/18，结构性），C1 层最值得写进论文的是虚频（EC 的 [LiEC]+，−80.4 cm⁻¹，1/10）与 no_intact_minimum_found（dication 4/12），两者都直接影响现有位移的物理解释。

> 口径：发生数/总数 逐层给出，分母取该 JSON 自己的分母字段（n_records / n_jobs / n_candidates / n_molecules / n_rows / n_cells / n_selected）。只登记真实存在的字段；缺字段的层不出现。“论文未报告 / 命中 0”按关键词字符串检索计，非逐字段核对。核心集 P1 唯一的高发异常是 unbound_anion（18/18，结构性）；C1 层最值得报告的是 T7 虚频（EC，−80.4 cm⁻¹）与 no_intact_minimum_found（dication 4/12）。

## 表 3  第一阶段显式“不做”声明表（四项条款）

| 条款 | 是否做 | 为什么不做（核心文件 §2.3 纪律 + 论文局限章） | 建议在论文哪一节声明为 Phase II | 证据强度 |
| --- | --- | --- | --- | --- |
| §16.2 真实配位 population（{p_s}: M / [LiM]+ / [LiM2]+ / [LiMmA]…） | 否（只做 1:1 条件态 C1 与同配体、同化学计量的 1:2 targeted check，不是 population） | 核心文件 §16.2 自己写明“这属于 Phase II/III，而不是 MVP 中通过强制 1:1 complex 偷偷替代”；§2.3 纪律不允许把 [LiM]+ 的 redox quantity 当作实际浓度电解液的有效 redox potential；§27 Phase II 要求明确浓度与组成，Phase III 才用 MD/AIMD 取真实 coordination distribution。论文 §4 局限承认 Li+ 条件态结论只在 10 分子上得到、普适性待更大配位基元库检验。 | §5.1 分支/边界认领表（W24 新增），或 §4 局限；并在 §2.2 台阶设计处加一句“C1/C2 是条件态、非 speciation”。 | 确证 |
| §18 多目标 Pareto / 武断“综合电解液分数” | 否（未构造 S=Σw_iP_i，也未做 Pareto front 数值；只并列报告氧化/还原两轴，并把 ΔΔG_bind 当 mechanistic descriptor） | 核心文件 §18 规定：ΔΔG_bind 不默认设为 maximize 目标；若做多目标展示，用 Pareto front 或明确 target window，而不是缺乏物理依据的综合分数。本项目全文检索 Pareto / target_window / 加权和 = 0（仅文献讨论中出现），属“遵守纪律而未做”，不是遗漏。 | §2.4 决策量定义（两条轴分别定义方向）+ §2.6 预注册；若 W24 新增 §5.1，可在其中声明 Pareto 留待 Phase II。 | 确证 |
| §10.3 threshold-based decision error（需外部设计要求阈值） | 否（记为 not_applicable） | 核心文件 §10.3 规定：只有当阈值 T 来自外部设计要求、实验基准或事先定义的工程标准时才使用，且不允许看完数据后人为挑一个最有利阈值。`config/prereg.yaml` 的 `threshold_decisions.if_unavailable` 禁止用数据分位数临时替代；本项目不存在合规外部阈值来源，故 Stage 6 如实记 not_applicable。论文 §4 局限（液相锚点未封闭、无实验基准阈值）与此一致。 | §2.4/§2.6 加一条脚注（记 not_applicable 及原因），并在 §5.1 声明为 Phase II；本项目落点：outputs/week6/stage6_decision_stability.md §5。 | 确证 |
| §3.3 R_env（环境 / 电极界面、EDL 参考层） | 否（data/anchors/ 无 R_env 数值文件；论文 §3.5 只对 Yang 2025 已发表趋势做定性对照，可视为 R_env 的弱形式，但未落盘为 anchor） | 核心文件 §3.3 明说第一阶段不要求这一层完整覆盖全部候选；docs/01 §5 记录“data/anchors/ 当前没有 R_env 数值文件”，并禁止把 R_gas/R_sol 结论外推到 C1。§2.3 纪律不允许把条件态 proxy 说成真实电化学窗口；§27 Phase IV 需 electrode potential / surface / EDL composition / charge transfer 才进入真实 electrochemical stability。论文 §4 局限（液相锚点绝对标定未封闭）。 | §2.3（外部参考层）或 §4 局限明确写为 Phase IV/II 边界；若保留 Yang 2025 那句定性对照，应注明“定性趋势、非 R_env anchor”。 | 确证 |

> **结论**：四项都属于“按项目自己的纪律在第一阶段**不做**”的显式边界，论文 v2 对 §16.2/§18/§10.3/§3.3 的关键词命中均为 0，应把本表写进方法节/附录，把“没做”变成“说明过不做”。其中 §3.3 R_env 是唯一有“弱形式已做”的条款——论文 §3.5 用 Yang et al. 2025 的已发表趋势做了一次定性对照（未落盘为 anchor 文件）。

> 口径：是否做 以项目产物与文档为准；“论文命中 0”按关键词字符串检索计，非逐字段核对。四项都可直接写进方法节/附录，把“没做”说明成“按纪律不做”。

## 输入清单与 SHA256

| 输入 | 存在 | SHA256 |
| --- | --- | --- |
| `核心文件/ranking-electrolyte-materials-v2.md` | Y | `e55c1b07a127ef7d0bb2f25302ac39f0640f24f45c0547bb482a63b1f4f17c0e` |
| `论文/_dossier/_fulltext_w22.txt` | Y | `19a84d45c20101056549536774275cdbb20f86d186a355f03887a5de5c29b6df` |
| `论文/build_paper_docx.py` | Y | `b87361044664e7e16e525fb470e87151dea5a94bb3480e69d18575025f04b77c` |
| `成果输出/数据结果汇总.md` | Y | `e3341e3cb2274446c77ea7573a569499485197e72c1c1c0ced75b0ddbe2f9158` |
| `电解液溶剂HB-Code/docs/00_stage0_definitions.md` | Y | `4372a4bb8ed3a552cb91bccdeb543d45d9699ffa3d84a555150481dd4b984d1a` |
| `电解液溶剂HB-Code/docs/01_stage1_external_anchors.md` | Y | `5656882885cc4b70ee24020762fecc90b1b6d7aa365573cd04ecbeed76b82250` |
| `电解液溶剂HB-Code/docs/02_stage1_method_audit.md` | Y | `1acf6b547eebfea94595f19bcadc78989bd944fa721b3d2cdabd75d4292d9edb` |
| `电解液溶剂HB-Code/docs/04_stage1_xtb_audit_result.md` | Y | `e9117051e156a51256b1808ebd0404bec7ab575e62e7d3ad317f89ef17ab347d` |
| `电解液溶剂HB-Code/docs/05_stage2_broad_pool_p0.md` | Y | `89f19a6778511869345fdb0ca39becf55b6971d518adb9ce5d8971a9cda855c2` |
| `电解液溶剂HB-Code/docs/06_stage1_solution_anchor_audit.md` | Y | `9e5dfc80e0d40f516140b7f75c6b3146165e088b2d29ae2b8a71b34d58c68e5c` |
| `电解液溶剂HB-Code/docs/08_stage2_production_protocol.md` | Y | `19cc0b390ef8944d645559972b469b3aea707eb60a6887cb6e3dc95cbec59715` |
| `电解液溶剂HB-Code/docs/09_week3_report.md` | Y | `22bdc620d1b24693e9319538d8b6631c2b45700eba7c0a7b51cbcaedeb4804b9` |
| `电解液溶剂HB-Code/docs/10_week4_report.md` | Y | `b296c9b0565d2105f4d8857a7162f6c5569b4e591b440dd42d422c199d5807f4` |
| `电解液溶剂HB-Code/docs/11_plan_alignment.md` | Y | `5b7a2bcc15d90c07c72d8e13b7a35b38af82034cd49ce32f793d273b88b9e215` |
| `电解液溶剂HB-Code/docs/12_week5_report.md` | Y | `40f2dc26386777afc93c627e1b9539a8ac4a95ff257afcead70ff52a5018e509` |
| `电解液溶剂HB-Code/docs/13_week6_report.md` | Y | `ca0f0e35a7ac46a7fd9cebed03a80912d06325ab39c83548aaeb4ff692a7c965` |
| `电解液溶剂HB-Code/docs/15_week7_report.md` | Y | `5b96e4273fc6be0812d927e28fdc5e16a8cd4dcbe6fea1f4ef081f87a5b1794c` |
| `电解液溶剂HB-Code/docs/16_branch_abcd_qa.md` | Y | `a8cbfd6d310136decf388e4c0a796edd941fef81ba2da26787b9eb98a21b7565` |
| `电解液溶剂HB-Code/docs/18_week8_report.md` | Y | `cae2ba95220f9dbd37594e8de8a1033d66057eab39148f10e348d7894ae349e7` |
| `电解液溶剂HB-Code/docs/19_week9_report.md` | Y | `1a44c281b1ef252b63755514f85cfc8706ab33ed9f743f1c540f94ba2dd0e592` |
| `电解液溶剂HB-Code/scripts/run_method_audit_xtb.py` | Y | `f1102602f476bbd3b9aa60dec0e3af491d09922a614ce92c776886d8d21b0827` |
| `电解液溶剂HB-Code/scripts/audit_solution_anchors.py` | Y | `d8258e07ca72925de898af5f0fb8c356d5da89f58df6b26c347e88c822f124c8` |
| `电解液溶剂HB-Code/scripts/build_metadata.py` | Y | `7b57913fd1f2003c87a04ff82079f00f0d002712a01f59dcf2a1b0e15e979b1a` |
| `电解液溶剂HB-Code/scripts/run_broad_pool_p0.py` | Y | `736c91001d995d544a82d12a0934fd276d91755d46dd198b4ed28616335dd015` |
| `电解液溶剂HB-Code/scripts/run_core_set_p1.py` | Y | `9c0f00283b8a3ddbb8d109fc4f1c68803c6cea4bb99742b41f8bb70723caad77` |
| `电解液溶剂HB-Code/scripts/audit_p1_core_set.py` | Y | `42673f3afef2e0c53951e9a18c53d78aad5593bbccd2639bff22ea90c72274e9` |
| `电解液溶剂HB-Code/scripts/run_t2_opt_freq.py` | Y | `ec893780a6e61c037acbdfc298296c430ac9bc062f6a4ba31272f1d807eeb596` |
| `电解液溶剂HB-Code/scripts/run_core_set_p2.py` | Y | `c8c542f5f7c440615d93f45401879b65df70e2ca79c3c70b227d73bd55afd3eb` |
| `电解液溶剂HB-Code/scripts/analyze_cpcm_eps_scan.py` | Y | `0b60834cdd1ad4efd4f1fbacc4875eede06cfc946b06be50279d8627c777cfbe` |
| `电解液溶剂HB-Code/scripts/build_li_motifs.py` | Y | `99856179e6b65e0f3feed03c6b7c098cd4251438c47a0b951f238d954abf5d78` |
| `电解液溶剂HB-Code/scripts/run_c1_li_coordination.py` | Y | `d852400dc0a63e0bae83b79f9954ea40d79570427ed0496b11abf9fd82a81757` |
| `电解液溶剂HB-Code/scripts/analyze_c1_state_identity.py` | Y | `b258658ece437c31c0db10fda3692ebb9729222686256c7748ec2b11a04321e5` |
| `电解液溶剂HB-Code/scripts/analyze_stage6.py` | Y | `c3b28e3fc3346505318ccdd828dc1cb8a3905249877f12984a8686fa8c087019` |
| `电解液溶剂HB-Code/scripts/analyze_delta_m.py` | Y | `f8f8b7604f4c0f38fc2f969fce56849738201635e1d98fa38599dd95fbf74db3` |
| `电解液溶剂HB-Code/scripts/analyze_stage10_synthesis.py` | Y | `d68791b9c6f519b40742926c6d0523d2ef2c2eee0b3dba845576ce81d9bea0c3` |
| `电解液溶剂HB-Code/scripts/run_stage7_ml.py` | Y | `f1bc3fb02559bdc87f5929d184a16642bffb793bda9c88824d1662afe2e43712` |
| `电解液溶剂HB-Code/scripts/build_ml_features.py` | Y | `49f39880ccc50ddb2327d50a890dffda24b32d14e72dd2b4a0ac4b11da2b21d5` |
| `电解液溶剂HB-Code/scripts/run_stage8_al.py` | Y | `e3206904aa58e501359775ee873627b82c76ead9cae4a58544558aee6b27e626` |
| `电解液溶剂HB-Code/scripts/build_microsolvation_shells.py` | Y | `a5b075a5eee058ec520ad2f94b55e02397225c478ba570519fb9d403a32a7b0a` |
| `电解液溶剂HB-Code/scripts/run_stage9_microsolvation.py` | Y | `eef81a8f6171d8b730e36c80139cd22c5892f02a25cd1d00f1829f851571c6f0` |
| `电解液溶剂HB-Code/outputs/week1/gate0_record.md` | Y | `36591ea9c1f615a7783509bb72a5c60fd926bf1ac2913fd62b8613652f6bcd80` |
| `电解液溶剂HB-Code/outputs/week2/gate1_record.md` | Y | `fe5738f27cb56934effa70a05b9121196f2de583fe88fffd5000f1a18c05a0b6` |
| `电解液溶剂HB-Code/outputs/week2/method_audit_xtb_summary.json` | Y | `e6bdf6217f71e2d01e26ee181ee9b71b12fd58558054c82a093fc27678d5ad76` |
| `电解液溶剂HB-Code/outputs/week2/solution_anchor_audit.json` | Y | `bec6f71270fac92066cfe1cc9239e012d2e595f48c84fa1ec233d3b111e34719` |
| `电解液溶剂HB-Code/outputs/week3/p0_broad_pool.csv` | Y | `363f67eca29afa0a986e5e48964447f9e821a2c0669c2517397f74f5cc25b2aa` |
| `电解液溶剂HB-Code/outputs/week3/p0_core_set.csv` | Y | `8001accb7066b18bdc8b622466163f796ba0b7c527f394d585ff3bdfab5b1cb3` |
| `电解液溶剂HB-Code/outputs/week4/p1_core_set.csv` | Y | `a872f359d93d64ccd97ded9561cf21b6a66917c4d10cfb9b893442c4f067caaa` |
| `电解液溶剂HB-Code/outputs/week4/p1_core_set_audit.json` | Y | `d796fcfd4477ec7be9cdcf6951f2980a2b9c3252e4a08a5346f32c7088809a48` |
| `电解液溶剂HB-Code/outputs/week4/p1_decision_stability.json` | Y | `9fa78cd9f5d81485235981ec750ade9c25cb7eec305f154df43294f73d08b085` |
| `电解液溶剂HB-Code/outputs/week4/t2_opt_freq_summary.json` | Y | `eb383c6c1760cd04ae5d84807de660e518c032d16e65778051df88bca7f23b17` |
| `电解液溶剂HB-Code/outputs/week4/p2_summary_smd_acetonitrile.json` | Y | `b39720c91180ce116eb3edb13d718f7a31f78ce3ca2a8ac8435db70746688cea` |
| `电解液溶剂HB-Code/outputs/week4/p2_decision_stability.json` | Y | `38eb6af12228a52016a6e20af6768336d1fa6693cff9422a56cebe83f9df2108` |
| `电解液溶剂HB-Code/outputs/week4/t3_cpcm_eps_scan_summary.json` | Y | `ce04777bf324683526183ef783177073cb70512f94d623b7bd559391706a28d4` |
| `电解液溶剂HB-Code/outputs/week5/li_motif_generation.json` | Y | `5a87805098a2cf4e884e9a79537e0a2a1ad227ea3ed45207258e92f29ea3de2f` |
| `电解液溶剂HB-Code/outputs/week5/c1_li_coordination_summary.json` | Y | `772d35d250312382829a74fc6b07dd8fa980a88eaffb392fe750d5038f1a5022` |
| `电解液溶剂HB-Code/outputs/week5/c1_state_identity.json` | Y | `b7672afcb48594c3e0950a70091a87ff340dae9e6131759ecfa96eeed96199d0` |
| `电解液溶剂HB-Code/outputs/week5/c1_decision_stability.json` | Y | `da9df806884640d4ac23a9b074b858d306bfeee216ff516c0d526571b56993cb` |
| `电解液溶剂HB-Code/outputs/week6/delta_m_frozen.json` | Y | `eda08587448aec62ed251e6f95b2463b5a25e7911a8e3aba08a2915d5f190402` |
| `电解液溶剂HB-Code/outputs/week6/stage6_decision_stability.json` | Y | `3e9864cd9427ed1b59a8526b0c8443f0f1b865008f6a9ab4b7839340f07d2df0` |
| `电解液溶剂HB-Code/outputs/week6/t7_c1_freq_check.json` | Y | `425d03c5987db9cb11512e1c6851247e40b14272d8112871af3eefb5dae8c95f` |
| `电解液溶剂HB-Code/outputs/week7/stage7_ml_results.json` | Y | `5b134864b66b7567fc57050d5eb56b4ea81ec4e7302bb8696c0e2d2516b7c10f` |
| `电解液溶剂HB-Code/outputs/week7/stage8_al_curves.csv` | Y | `cddf05f9d899fcda8524a2dabaceec9218cf8970267208ab48860960df93632c` |
| `电解液溶剂HB-Code/outputs/week7/feature_manifest.json` | Y | `c020bf93269fbe9011a043b94454b62b44fae74448d322c3d5cd799ac2d60cc3` |
| `电解液溶剂HB-Code/outputs/week8/ms_shell_generation.json` | Y | `4b95587eb1c4c8423693601851f2b27f9b2f26b4bd13617875af8b2f4f7061b2` |
| `电解液溶剂HB-Code/outputs/week8/stage9_results.json` | Y | `f783b564b1b8a42dfdb2e02a633ce80e7c660e9b6a23f98f22959377c536b012` |
| `电解液溶剂HB-Code/outputs/week9/stage10_ladder.json` | Y | `3eb6b36d5622ec0e3147dd827a6437aabac2ea38c53936fddc974e85376ac3cf` |
| `电解液溶剂HB-Code/outputs/week15/stage16_catalogue_analysis.json` | Y | `f0a4ef2db120f10f8ddf075b6602c43548d5c9cb772471ccb8ed699a84afbb9c` |
| `电解液溶剂HB-Code/outputs/week18/stage19_relax_analysis.json` | Y | `90757ca1169e0e1136f58f0395a19298a91379049a0ab7cfd0f5f7f2a099b198` |
| `电解液溶剂HB-Code/outputs/week19/stage20_xtb_arms_analysis.json` | Y | `30042094148ee0a0c37c3eafb3aa12405ce44d23142caf3a65f381fb4415c9fc` |
| `电解液溶剂HB-Code/outputs/week20/stage21_refill.json` | Y | `bb424fee1e0c01e9a71609fb1b3bf9a93ee27d7e38a014ec37c8f9199ce06cd4` |
| `电解液溶剂HB-Code/outputs/week22_hardening/allowance_factor2.json` | Y | `8ddee883b4f0362f357da740bfbdd4129678b2c872d23be96778ec60d19ff2ce` |
| `电解液溶剂HB-Code/outputs/week23/targeted_two_guess.json` | Y | `c6ca4fbbdd50c79e82a9251a69916c75cd29e288f9f571971da8ebf22b14756a` |
| `成果输出/week1/verification.json` | Y | `3e91826b365de3a888782dfc0970ba2c1dc4b49fc6af891de427dd16864ff456` |
| `成果输出/week10/verification.json` | Y | `4de5897c2a695f7046aa584dd0bc7df7e6841a11bdb06a1707f23e15a97755f4` |
| `成果输出/week11/verification.json` | Y | `a2733ba55546f93028e43558ab963e45eee21964c9b4a111cd6aa7f835b72cf9` |
| `成果输出/week12/verification.json` | Y | `6806f3aa3ab17f8c23225ef98059b38d09227e97209a2ee8c377baf2b71809df` |
| `成果输出/week13/verification.json` | Y | `680dcb90320c13039b6ad0b4cb9d6ee59c44f0c3775aa8af6b8b03a87579b4a0` |
| `成果输出/week14/verification.json` | Y | `ec9d53a83c0ab46fcff2d9546abef5660a8ed9ef7386b99dadc6012da790eabb` |
| `成果输出/week15/verification.json` | Y | `3369363b7fdc1db051c89219d71f5fed478fb7beaf3f54335c7ba4bf282899e4` |
| `成果输出/week16/verification.json` | Y | `06edb758cb32f355aa17f07536e36e8e1ab64eeea08f659e8db5e563d015013a` |
| `成果输出/week17/verification.json` | Y | `dfc9b9fa5c01d06e9a078e47d6d2d9c6f386179d649e94bcd4b13171d60ff83f` |
| `成果输出/week18/verification.json` | Y | `d93b670729dfb813e299baa133f45a35fdc64653efd19f7c6114ed6c34e3f978` |
| `成果输出/week19/verification.json` | Y | `7b4dcd2c322f4b9d754e493c49c3eccfdb60192f3ca4fd2ac9fc76521cee6b3f` |
| `成果输出/week2/verification.json` | Y | `c2fce4bd48d5d55da8d155c340e555cf42130e64f1c2d580276e13c9337ac1a9` |
| `成果输出/week20/verification.json` | Y | `4fea2eb4f70817cbcff1e6c038b66e526368c6a9fd9e8bd34ebd434e773e4fb9` |
| `成果输出/week21/verification.json` | Y | `a83e8f117612ef45a046322660bf0b735729597390bac6265df9d2cb2c73a1bc` |
| `成果输出/week22/verification.json` | Y | `66e899023cd2045c8dcc1bd945a0fd22a4ea5561c8279dc40bd562806420d40c` |
| `成果输出/week23/verification.json` | Y | `5db400d9a8a8d69e4c5eb4342fd376fb594da460ef845beaa09daad8037feaa8` |
| `成果输出/week3/verification.json` | Y | `4278e6404137141aa52dbca5f371df225203f9d6d8ff86ae41902c546804a90c` |
| `成果输出/week4/verification.json` | Y | `7b7c1b2a2125549638c22a65e7b9546134ff1a081089f1308a879c73766b3510` |
| `成果输出/week5/verification.json` | Y | `1f2b4002fc2d7b0e55afc0e5cd910edb524e0d66e7f4856d49a3b20bbd1efcb6` |
| `成果输出/week6/verification.json` | Y | `cd861687758bc9ef1cc3c55bc9b5fa1f83b82c4a12d3e5ff5636dd291f442a01` |
| `成果输出/week7/verification.json` | Y | `cd7475073d943861fbcfe316d14f17106871f2e49d02f9f12d0eb503b622088f` |
| `成果输出/week8/verification.json` | Y | `9376fbf1a3d5986a72d45d3d2b94093c3d9ca6923f592e8f88565bf28d30b48c` |
| `成果输出/week9/verification.json` | Y | `491f2f7e96b9d31051db2d99f8b405d5e8a9976d383f6c1d8187f0391456c325` |

## 复核

- 幂等复核：`.\\.venv\\Scripts\\python.exe scripts/analyze_w24_audit.py --check`
- Stage 映射行数：10；待确认：0
- QC 台账行数：19；论文未报告：13（scf_failed、自洽场多解：第二解弛豫存亡、自洽场多解：跨引擎存亡、motif_switch、geometry_failed、虚频 imaginary_mode_unresolved、dissociated_optimized_product、spin_contamination_flag、electron_count_mismatch、execution_failed、abnormal_termination / energy_mismatch / missing_output、placement_clash_start、warning（Stage 21 refill））
- 第一阶段不做行数：4；待确认：无
- 交付层 verification.json 断言：372 条
