# 核心文件承诺 vs 项目已交付：Week 24 对齐

本文件把核心文件（`ranking-electrolyte-materials-v2.md` §11 / §22 / §23 / §25 与 `ranking-electrolyte-materials-reading-list.md` Part II）的承诺，逐条对齐到项目已冻结的产物。只读输入、零新增电子结构计算；数值一律如实转述，未新增或改写。

## 表 1  §22 分支认领表（情形 A–G）

| 分支（A–G） | 判据定义 | 本项目判决 | 关键证据（带数值） | 证据文件路径 |
| --- | --- | --- | --- | --- |
| A（廉价 proxy 已足够） | tau_b(P0, P2) 高、unresolved 低、Top-k 重叠高 => 廉价 proxy 在该适用域已足够 | NOT SUPPORTED | P0→P2 氧化轴 τ_b=0.673、Top-10% 重叠 0.000、f_unresolved=0.229 | outputs/week4/p2_decision_stability.json, outputs/week9/stage10_ladder.json |
| B（位移大但排序稳） | P2 与 P1 之差整体大，但 robust inversion fraction 低 => 环境主要引入 common/family offset | SUPPORTED | P1→P2 氧化轴位移均值 −2.393 eV、位移 std 0.302 eV、τ_b=0.895、O_20%=0.750、f_robust_inv=0.000 | outputs/week4/p2_decision_stability.json, outputs/week9/stage10_ladder.json |
| C（结构集中的 robust inversion） | robust inversion 少量且结构集中 => 可提出 missing-physics mechanism | NOT OBSERVED | 五台阶 × 两轴 × 两口径共 20 个 (台阶, 轴) 组合中 f_robust_inv 全为 0.000；z=1.96 敏感性列同样全为 0.000 | outputs/week9/stage10_ladder.json |
| D（配位引发 state-identity 改变） | [Li M]0 出现 Li 中心/混合还原、断键或 motif switching => 配位台阶不是统一平滑函数 | OBSERVED | 还原态 12 个中 11 个 Li_centered_or_mixed_redox、1 个 molecule_centered；氧化态 12 个中 molecule_centered=8、no_intact_minimum=4（阈值 \|Li 自旋\|≥0.5 或 \|Δq(Li)\|≥0.5 e） | outputs/week5/c1_state_identity.json, outputs/week9/stage10_ladder.json |
| E（Δ-learning 优于 direct） | LOFO 下 Δ-learning 优于 direct => 自由分子物理已捕获大部分变化 | SUPPORTED（6/8）；例外：C/reduction/X0、C/reduction/X0+X1 | LOFO 下 Δ-learning 在 6/8 分组不劣于 direct：C/oxidation/X0 τ_b 0.111→0.644 (+0.533)、C/oxidation/X0+X1 0.244→0.644 (+0.400)；例外 C/reduction/X0 0.422→0.022 (−0.400)、C/reduction/X0+X1 0.289→0.200 (−0.089) | outputs/week7/stage7_ml_results.json, outputs/week9/stage10_ladder.json |
| F（Δ 无法从廉价特征学出） | Δ 无法由 cheap features 学出 => representation 缺关键物理信息 | NOT SUPPORTED（Δ 在 6/8 个分组上可从廉价特征学出）；例外：C/reduction/X0、C/reduction/X0+X1（与情形 D 同一根还原轴） | Δ 在 6/8 分组上可从廉价特征学出（与 E 同源）；真正学不动的仅 C0→C1 还原轴 | outputs/week7/stage7_ml_results.json, outputs/week9/stage10_ladder.json |
| G（大部分 pair 不可判定） | 大部分 pair 都 unresolved => 输出应是 equivalence classes / tiered sets，而不是强行排名 | PARTIALLY SUPPORTED (还原轴 C0 -> C1) | C0→C1 还原轴 τ_b=−0.467、f_unresolved(after)=0.800、O_10%=0.000；同级氧化轴对照 τ_b=0.689、f_unresolved(after)=0.200；P0→P1 还原轴 f_unresolved(after)=0.733 | outputs/week9/stage10_ladder.json |

> 判决与证据均取自 outputs/week9/stage10_ladder.json 的 verdicts 字段，只做如实转述，未新增任何数值。

**声明一（分支认领总述）**：本项目最终落在 B、D、E 三个分支（并以 G 的还原轴部分触发）：B——P1→P2 位移大而排序稳（τ_b=0.895、f_robust_inv=0.000），环境主要贡献 common/family-level offset；D——Li+ 配位改写态身份（还原态 11/12 为 Li 中心或混合还原）；E——Δ-learning 在 6/8 分组上不劣于 direct。A、C、F 均被如实否定：A 廉价 proxy 不能替代目标层（P0→P2 τ_b=0.673、Top-10% 重叠 0.000）；C 的 robust inversion 从未出现（20 个台阶-轴组合 f_robust_inv 全为 0.000，且必须与 G 的 f_unresolved 同读，不等于排序处处可靠）；F 的「Δ 不可学」不成立。真正 unresolved 的只有还原轴的 C0→C1（τ_b=−0.467、f_unresolved=0.800），即 G。

## 表 2  §23 最小成果判据自查表（11 条）

| id | 条目 | status | evidence（原文） | 证据文件校验 | 论文中的落点 |
| --- | --- | --- | --- | --- | --- |
| 1 | metadata 严格、chemical-space 平衡的 core set（18 分子） | PASS | Week 1-3：core 18 / broad 40，family 平衡，`data/metadata/core_set.csv` | OK（data/metadata/core_set.csv） | 2.1 分子集与化学空间 |
| 2 | broad cheap pool（40 分子廉价层） | PASS | Week 3：`outputs/week3/p0_pool.csv`，58 分子合并池 | CHECK（outputs/week3/p0_broad_pool.csv；evidence 引用路径不存在：outputs/week3/p0_pool.csv，已改列实际产物） | 2.1 分子集与化学空间（另见 3.12） |
| 3 | P0 / P1 / P2 的一致定义 | PASS | Week 1 冻结（`config/scientific_definitions.yaml`），Week 3-4 全部执行 | OK（config/scientific_definitions.yaml） | 2.2 三层电子结构臂与唯一变量台阶设计 / 2.4 决策量定义 |
| 4 | C1 Li-coordination conditional analysis | PASS | Week 5（T4）：12 motif / 8 家族；另见 Week 8 的 C2 复核 | OK（outputs/week5/c1_state_identity.json、outputs/week5/c1_coord_shifts.csv；evidence 未给出文件路径，已补列实际产物） | 3.5 条件态台阶：Li+ 配位如何改写排序 |
| 5 | external gas / solution anchors | PARTIAL | 气相锚点已用（Week 2/4）；溶液锚点 31 行仍为 `method=est`（Gate 1 未关闭） | OK（data/anchors/gas_phase_anchors.csv、data/anchors/solution_redox_anchors.csv、outputs/week2/solution_anchor_audit.json；evidence 未给出文件路径，已补列实际产物） | 2.3 电子结构计算细节（气相锚点）；溶液锚点 Gate 1 未关，待补外部锚点/局限声明 |
| 6 | uncertainty-aware rank comparison | PASS | Week 4-8：tau_b / O_k / Jaccard / regret / f_unresolved / f_robust_inv | OK（outputs/week4/p2_decision_stability.json、outputs/week9/stage10_ladder.json；evidence 未给出文件路径，已补列实际产物） | 2.4 决策量定义 / 3.1 值误差与排序误差的解耦 / 3.6 位移离散度判据 |
| 7 | robust inversion mechanism analysis | PASS (negative) | Week 9 本文件：五个台阶上 f_robust_inv 恒为 0，机制归属见 §情形 C | OK（outputs/week9/stage10_ladder.json；evidence 未给出文件路径，已补列实际产物） | 3.5 条件态台阶 / 3.6 位移离散度判据（negative 结果） |
| 8 | random / group / LOFO 三种拆分 | PASS | Week 7 / Stage 7：`outputs/week7/stage7_ml_results.json` | OK（outputs/week7/stage7_ml_results.json） | 待补（论文缺 ML 章：random/group/LOFO 拆分） |
| 9 | direct vs Δ-learning | PASS | Week 7：F16 | OK（outputs/week7/stage7_ml_results.json；evidence 未给出文件路径，已补列实际产物） | 待补（论文缺 ML 章：direct vs Δ-learning） |
| 10 | feature-cost-aware active-learning replay | PASS | Week 7 / Stage 8：`outputs/week7/stage8_al_results.json`、F17 | OK（outputs/week7/stage8_al_results.json） | 待补（论文缺 ML / 主动学习章：feature-cost-aware active-learning replay） |
| 11 | high-cost-label budget vs decision accuracy 曲线 | PASS | Week 7：`n_T -> tau_b` 四条 acquisition 曲线（F17） | OK（outputs/week7/stage8_al_curves.csv；evidence 未给出文件路径，已补列实际产物） | 3.11 最小信息预算 / 3.12 broad pool 的实际演示 |

> status / item / evidence 取自 outputs/week9/stage10_ladder.json 的 minimum_outcome_checklist，未改动；PARTIAL 条目按原文如实保留。

## 表 3  §11 feature-cost accounting（X0 / X1 / X2）

| 成本档 | 特征清单 | 何时可得 | 允许用途（可否用于证明「低成本预测」） |
| --- | --- | --- | --- |
| X0（cheap，query 前可得） | mw、donor_count、n_heavy、rotatable_bonds、tpsa、is_cyclic、has_fluorine、p0_ox_ev、p0_red_ev、hl_gap_ev、dipole_debye、aux_alpha_bohr3（共 12 个） | query 前：分子式/结构描述符 + GFN2-xTB 单点即可，无需任何 DFT | 可作为任何预测器与 acquisition 的输入；active-learning acquisition 只允许用 X0；可支撑「低成本预测」的主张 |
| X1（free-molecule DFT 已知后可得） | p1_ox_ev、p1_red_ev、p2_ox_ev、p2_red_ev、env_d_ox_ev、env_d_red_ev（共 6 个） | free-molecule DFT（P1）或 P2 环境势已知之后 | 可用来预测昂贵的 C1 Li-配位响应，因为这些量在做新的 C1 计算前已经可得；但不得据此宣称「无需 C1 就能得到 C1 结果」 |
| X2（需 Li-complex DFT 后才能获得） | x2_dgdg_bind_ev、x2_li_min_distance_a、x2_li_contacts_n、x2_motif_switch（共 4 个） | 必须做完 Li-complex（C1）DFT 之后 | 仅机制解释（mechanism-only）；绝不进特征集，不能用于证明「低成本预测 C1」 |

> x2_policy 原文：X2 columns are mechanism-only.  The model runner asserts they never enter a feature set, so no table can claim to predict a C1 quantity cheaply by using a C1-derived descriptor. ｜ 所有 ML 表格均带 feature_cost_level 列：outputs/week7/stage7_ml_results.csv 的表头含该列，实际取值为 X0 / X0+P1 / X0+X1（不含 X2）。

## 表 4  §25.1/§25.2 RL Part II 方法依据映射

**声明二（创新边界，≤200 字）**：本项目不以「ranking/selection 本身」为创新（Husch et al. 2015），也不以「Li+ 配位改变 redox」为创新（Yang et al. 2025 已用 ML）。增量有三：①决策可靠性——τ_b 与 f_unresolved/f_robust_inv 并列，区分两类误差；②稳健翻转须超出方法不确定度——全部台阶 f_robust_inv=0；③最小信息预算——复现目标排序所需的昂贵信息量。

| RL Part II 条目 | 出处 | 本项目在哪个环节用到 | 建议引用位置 |
| --- | --- | --- | --- |
| A1 SMD | Marenich, Cramer & Truhlar 2009，DOI 10.1021/jp810292n（阅读清单 Part II §A1） | ✅ 已使用：P2 环境臂 = ORCA 6.1.1 r2SCAN-3c 的 CPCM(SMD, 乙腈 ε=35.688)，54/54 作业成功（outputs/week4/p2_summary_smd_acetonitrile.json） | 论文 2.3 电子结构计算细节；3.3 环境台阶（P1→P2） |
| A2 association entropy | Rebollar-Zepeda et al., JCTC 2026，DOI 10.1021/acs.jctc.6c00575（阅读清单 Part II §A2） | ○ 未直接使用，仅方法学背景：项目识别了 Li+ + M → [LiM]+ 的平动熵 artifact（config/scientific_definitions.yaml 的 molecularity_warning），并以配体交换相对量 dGdG_bind 规避；未显式建模 condensed-phase association entropy | 论文 2.3 / 2.4 的方法学说明与局限 |
| A3 qRRHO | Grimme 2012，DOI 10.1002/chem.201200497（阅读清单 Part II §A3） | ○ 未直接使用，仅方法学背景：热修正抽样用的是 xtb --ohess 的谐近似 RRHO 项 G(RRHO)（scripts/run_thermal_correction_sample.py），未使用 quasi-RRHO 熵插值 | 论文 2.5 不确定度预算（热修正抽样） |
| B1 GFN2-xTB | Bannwarth, Ehlert & Grimme 2019，DOI 10.1021/acs.jctc.8b01176（阅读清单 Part II §B1） | ✅ 已使用：P0 Koopmans 层（xtb 6.7.1pre）、G1 几何、构象系综弛豫，以及 week23 第三配位壳符号检验（engine=GFN2-xTB，14 作业） | 论文 2.2 / 2.3 / 3.9 |
| B2 CREST | CREST, JCP 2024，DOI 10.1063/5.0197592（阅读清单 Part II §B2） | ○ 未直接使用，仅方法学背景：仓库内无 CREST 运行产物（无 crest.exe、无 crest_conformers.xyz）；构象系综实际由 RDKit ETKDGv3 + MMFF + GFN2-xTB 弛豫构建（scripts/build_conformers.py）。注：论文 2.3 现写有「低能构象空间搜索使用 CREST[7]」，与实际实现不一致 | 论文 2.3（需与 build_conformers.py 实际做法核对/修正） |
| C1 electrolyte speciation | Chem. Rev. 2022，DOI 10.1021/acs.chemrev.1c00904（阅读清单 Part II §C1，真实 speciation / MD） | ○ 未直接使用，仅方法学背景：项目停留在单一 [LiM]+ conditional state（week5 T4，12 motif / 8 家族），未做 p(C) 配位环境分布或 MD speciation | 论文 3.5 的局限声明 / 4 展望（Phase II 真实配位 population） |
| C2 solvation structure | ACS Energy Lett. 2022，DOI 10.1021/acsenergylett.1c02425（阅读清单 Part II §C2） | ◐ 间接使用：C1→C2 显式微溶剂化 [Li(M)2]+ 簇（week8 Stage 9，10 分子），week23 追加 EC 第三配位壳符号检验；对应第一溶剂化壳，但未涉及 Li–溶剂–阴离子竞争或界面结构 | 论文 3.5 / 3.9 配位饱和的证据 |
| D1 Gaussian Process | Rasmussen & Williams, Gaussian Processes for Machine Learning（阅读清单 Part II §D1） | ✅ 已使用：Stage 7 模型阶梯含 sklearn GaussianProcessRegressor（scripts/run_stage7_ml.py），与 Stage 8 acquisition 同源 | 论文待补 ML 章 |
| D2 Active learning | Settles 2009, Active Learning Literature Survey（阅读清单 Part II §D2） | ✅ 已使用：Stage 8 retrospective active-learning replay，4 种 acquisition（random / diversity / uncertainty / ranking-aware，ranking-aware 用二元熵），acquisition 只用 X0（outputs/week7/stage8_al_results.json） | 论文待补 ML / 主动学习章 |
| D3 Multi-fidelity | Peherstorfer, Willcox & Gunzburger 2018，DOI 10.1137/16M1082469（阅读清单 Part II §D3） | ○ 未直接使用，仅方法学背景：仓库无 multi-fidelity 实现；Δ-learning 的 P_H = P_L + Δ 形式相同，但按阅读清单定义 P(M) → P([LiM]+) 属 environment perturbation，不是数值 fidelity 校正 | 论文待补 ML 章的方法学说明（与 2.2 条件态定义呼应） |
| E Efron & Tibshirani (bootstrap) | Efron & Tibshirani, An Introduction to the Bootstrap（阅读清单 Part II §E） | ✅ 已使用：Week 22 hardening 对 ladder 的 10 个 (台阶, 轴) 点做 bootstrap（percentile 主口径 + BCa 并列，n_boot=20000，固定种子）（outputs/week22_hardening/stats_b1_b2.json） | 论文 2.5 / 3.6（τ_b 的 bootstrap 置信区间） |

> marker：✅ 已使用 / ◐ 间接使用 / ○ 未直接使用，仅方法学背景。找不到真实使用证据的条目已如实标注，未硬凑。

## 数据核查提示（data flags）

- §22 情形 B 的 verdict 文字记「位移 std 0.302 eV」，而 outputs/week4/p2_decision_stability.json 的 delta_ip.std_ev = 0.293338 eV；两者口径/舍入不一致，本表按 verdicts 原文转述 0.302，建议主代理复核。
- §23 第 2 条 evidence 引用 `outputs/week3/p0_pool.csv`，该路径不存在；实际产物为 `outputs/week3/p0_broad_pool.csv`（40 行，另有 p0_core_set.csv 18 行），两者合计 58。需要修正 evidence 路径。
- 论文 build_paper_docx.py 的 2.3 节写有「低能构象空间搜索使用 CREST[7]」，但仓库内没有任何 CREST 运行产物（无 crest.exe、无 crest_conformers.xyz、无 crest 输出目录）；scripts/build_conformers.py 明确用 RDKit ETKDGv3 + MMFF + GFN2-xTB 弛豫构建构象系综。RL Part II 的 B2（CREST）因此记「未直接使用」。

## 结构计数（供程序化取数）

- 分支判决：A=NOT SUPPORTED；B=SUPPORTED；C=NOT OBSERVED；D=OBSERVED；E=SUPPORTED（6/8）；例外：C/reduction/X0、C/reduction/X0+X1；F=NOT SUPPORTED（Δ 在 6/8 个分组上可从廉价特征学出）；例外：C/reduction/X0、C/reduction/X0+X1（与情形 D 同一根还原轴）；G=PARTIALLY SUPPORTED (还原轴 C0 -> C1)
- §23 PARTIAL 条目：5
- RL Part II 无真实使用证据（仅方法学背景）：5 条 —— A2 association entropy、A3 qRRHO、B2 CREST、C1 electrolyte speciation、D3 Multi-fidelity
- feature_cost_level 实际取值：X0 / X0+P1 / X0+X1
