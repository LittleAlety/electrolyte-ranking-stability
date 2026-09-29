# Stage 0 · Reading List 文献问答（Minimal 清单 M1–M7 + Part I 八问）

> 本文回答 `核心文件/ranking-electrolyte-materials-reading-list.md` 中 Part I（Minimal reading）**
> 的 7 项「本项目要解决的问题」（M1–M7）以及「Part I 的最低完成标准」的 8 个问题，
> 依据用户提供的 6 篇 PDF。所有引文均带页码；凡抽取过程损坏的符号一律显式标注。

## 0. 依据文献与本轮范围

| 编号 | 文献 | 出处 | DOI | 对应 reading list 项 |
|---|---|---|---|---|
| P1 | Peljo & Girault, *Electrochemical potential window of battery electrolytes: the HOMO-LUMO misconception* | Energy Environ. Sci., 2018, 11, 2306-2309 | `10.1039/C8EE01286E` | M2 |
| P2 | Marenich, Ho, Coote, Cramer & Truhlar, *Computational electrochemistry: prediction of liquid-phase reduction potentials* | Phys. Chem. Chem. Phys., 2014, 16, 15068-15106 | `10.1039/C4CP01572J` | M3 |
| P3 | Itkis, Cavallo, Yashina & Minenkov, *Ambiguities in solvation free energies from cluster-continuum quasichemical theory: lithium cation in protic and aprotic solvents* | Phys. Chem. Chem. Phys., 2021, 23, 16077-16088 | `10.1039/D1CP01454D` | M4 |
| P4 | Borodin, *Challenges with prediction of battery electrolyte electrochemical stability window and guiding the electrode-electrolyte stabilization* | Curr. Opin. Electrochem., 2019, 13, 86-93 | `10.1016/j.coelec.2018.10.015` | M5 |
| P5 | Yang et al., *Unveiling redox potential behavior in electrolytes: A machine learning approach to Li-ion coordination effects* | Mater. Today Energy, 2025, 54, 102121 | `10.1016/j.mtener.2025.102121` | M6 |
| P6 | Husch, Yilmazer, Balducci & Korth, *Large-scale virtual high-throughput screening for the identification of new battery electrolyte solvents: computing infrastructure and collective properties* | Phys. Chem. Chem. Phys., 2015, 17, 3394-3401 | `10.1039/C4CP04338C` | M7 |

- 完整作者名单（据 PDF p.1）：P1 `Pekka Peljo and Hubert H. Girault`；P2 `Aleksandr V. Marenich, Junming Ho, Michelle L. Coote, Christopher J. Cramer and Donald G. Truhlar`；P3 `Daniil Itkis, Luigi Cavallo, Lada V. Yashina and Yury Minenkov`；P5 `Deshuai Yang ... Guannan Zhu, Jun Fan`；P6 `Tamara Husch, Nusret Duygu Yilmazer, Andrea Balducci, Martin Korth`（P4 为 Borodin 单作者综述）。
- M1（Bard/Faulkner/White 教材）**未提供 PDF**，其问题按电化学基本原理回答，并只引用上述 6 篇可核查的证据。
- 本文件为 draft 暂存于 `outputs/_week7_scratch/`，由主线复核后再落盘到 `docs/14_reading_list_qa.md`。

## 0.1 抽取瑕疵声明（必读）

6 篇 PDF 由 `pymupdf` 抽取为纯文本（每页以 `===== PAGE n =====` 分隔）。抽取过程**系统性地丢失了
数学符号与连字符**，具体包括：

| 真实符号 | 抽取后出现的形态 | 例 |
|---|---|---|
| `U+2212` 负号 `-` | 直接消失 | `-4.44 eV` → `4.44 eV`；`-10.51 eV` → `10.51 eV` |
| `±` | 变成空格 | `4.44 ± 0.02 V` → `4.44 0.02 V` |
| `Δ` | 消失或在行内错位 | `ΔrG°` → `DrGo`；`ΔG_solv` → `DGsolv` |
| `<` | 变成 `o` | \|ρ\| < 0.9（原文形态，此处转义为 `\|ρ\|`）未见但 `<` 类比较符普遍损坏 |
| `≈` | 变成 `B` | `≈8 kJ/mol` → `B8 kJ mol-1` |
| `≥` | 变成 `4` | `≥20 kJ/mol` → `420 kJ mol-1` |
| `τ`（Kendall） | 变成 `t` | Husch 的 `Kendall's t values`（实为 τ） |
| `ε` 下标/上标 | 上下标丢失 | `ΔG°_S` → `DGo S` |

**因此：凡本文引用涉及符号的数值，均在方括号内标注「据上下文还原」。** 例如 Marenich 的
`4.44 0.02 V` 按原文语义还原为 `4.44 ± 0.02 V`；Peljo 的 `10.51 eV` 按上下文（HOMO 能量、
与氧化电位 7.87 V 对举）还原为 `-10.51 eV`。**所有引用均经回到 PDF 抽取文本逐条原文比对**，
未从任何二手来源补入数字。

---

# 1. 逐项回答（M1–M7）

## M1. 为什么「分子氧化/还原自由能」与「电池中真实分解电位」有关，但二者并不完全相同？

**结论.** 二者"有关"是因为 redox potential 在热力学上与反应物/产物的 Gibbs 自由能差直接挂钩，
这是定义层面的关系（$\Delta G=-nFE$）；二者"不完全相同"是因为真实分解电位还叠加了三层分子模型
不包含的物理：(i) 反应路径耦合（去质子化/H-transfer、开环、与阴离子成键），使单一势垒被替换成
多个"速率依赖的"电位；(ii) 界面与相态（EDL 内层组分、离子聚集、电极表面），使本体均相自由能
不再是唯一控制量；(iii) 动力学（重排能与活化势垒），使"热力学 onset"≠"可观测 onset"。

**文献原句.**

- Peljo, 期刊 p.2306（PDF p.1）：`redox potentials are directly related to the Gibbs free energy difference of the reactants and products.`
- Marenich, 期刊 p.15068（PDF p.1）：`the standard reduction potential for the redox pair of interest in solution can be calculated from the standard-state Gibbs free energy of the corresponding half-reaction estimated, for example, based on a thermodynamic cycle that includes the free energies of products and reactants in the gas phase and their free energies of solvation.`
- Borodin, 期刊 p.92（PDF p.7）：`instead of focusing on a single oxidation or reduction potential for a given electrolyte, it should be recognized that multiple oxidation and reduction potentials exist corresponding to reactions occurring at different rates. Thus, the rate dependent oxidation and reduction potentials should be used to characterize battery electrolytes.`
- Borodin, 期刊 p.87（PDF p.2）：`If ether HOMO or oxidation stability of an isolated EC is used as a marker of the EC-based electrolyte stability, all these coupled reactions would be missed and electrochemically stability of the EC-based electrolytes would be significantly overestimated.`（抽取原文如此；`ether` 疑为 `either` 的抽取讫误。据上下文还原）

**边界.** M1 本身无 PDF；本节只能给出"热力学 vs 动力学/界面"的定性分界，**不能**从这 6 篇得到
"分子自由能 → 真实分解电位"的定量映射公式（Borodin 只给 shift factor 1.4 的经验修正，
见第 3 节）。此外 Peljo 是 Opinion 文章（`In this opinion we provide a correct thermodynamic
representation ...`），**未做任何新计算**。

## M2. 为什么 HOMO/LUMO 可以作为 cheap proxy，却不能直接被称为真实氧化/还原电位？

**结论.** HOMO/LUMO 是"孤立分子的近似电子结构量"；真实 redox 电位是"含溶剂与反离子、
不同电荷态、含弛豫的自由能差"。二者在**部分同族分子**上经验相关（Peljo 给出 74 个有机物
斜率 1.12、R²=0.9917 的例子），所以可当 cheap proxy；但相关性**不具普适性**（同一文中过渡金属
配合物 R²=0.32/0.71），且偏移量可以很大（Peljo：可达 **4 eV**）。用 HOMO 判断稳定性会
**系统性高估**电解液稳定性。

**文献原句.**

- Peljo, 期刊 p.2306（PDF p.1）：`HOMO and LUMO are concepts derived from approximated electronic structure theory while investigating electronic properties of isolated molecules, and their energy levels do not indicate species participating in redox reactions.`
- Peljo, p.2306：`While redox potentials in some cases show strong correlation with HOMO energies, the offset can be of several eVs. Presence of electrolytes and other molecules can also significantly affect the redox potentials of the solvent leading to offset as high as 4 eV from the HOMO energies.`
- Peljo, p.2308（PDF p.3）：`Finally, the HOMO energies of common battery solvents have been calculated as [据上下文还原：-]10.51 eV and [据上下文还原：-]9.64 eV for ethylene carbonate and dimethylcarbonate, while the calculated oxidation potentials are 7.87 V and 7.07 V vs. absolute vacuum scale` 以及 `So in fact, utilization of the HOMO energy to indicate if the electrolyte would be stable would lead to overestimated electrolyte stability.`
- Peljo, p.2308：`74 organic redox active compounds ... showed a linear relationship with experimental reduction potentials with a slope of [据上下文还原：-]1.12, intercept of [据上下文还原：-]4.34 and R2 of 0.9917. However, this correlation is by no means universal, as different studies with a set of different molecules show slopes of [据上下文还原：-]1.4 etc.`

**边界.** Peljo 明确**不主张**"HOMO/LUMO 无用"，只反对把二者**等同于**电化学窗口；文中不给
偏移量的普适上下界，也不含 Li⁺ 配位情形。因此本项目只能引它作为"术语与量纲不可混用"的依据，
不能从中得到任何排序结论。

## M3. 我们为什么不能只比较两个分子的 DFT orbital energies，而必须考虑不同电荷态的自由能？

**结论.** 因为氧化/还原涉及**电子数的改变**，反应物与产物属于**不同电荷态**，各自有不同的
平衡几何、热校正与溶剂化自由能。orbital energy 只是"冻结几何下的单电子本征值"，既不含
结构弛豫（垂直/绝热差），也不含热与溶剂化项。标准做法是把半反应写成 Born-Haber 热力学循环：
先在气相算出不同电荷态的自由能差，再对**每一种物种**分别加溶剂化自由能。

**文献原句.**

- Marenich, 期刊 p.15075（PDF p.8），式 (23)：`[据上下文还原：Δr]G[据上下文还原：°]_S(A|B) = [据上下文还原：Δr]G[据上下文还原：°]_g(A|B) + Σ_i [据上下文还原：Δ]G[据上下文还原：°]_S(B_i) - Σ_i [据上下文还原：Δ]G[据上下文还原：°]_S(A_i)`，抽取原文作 `DrGo SðAjBÞ ¼ DrGo gðAjBÞ þ X i DGo SðBiÞ  X i DGo SðAiÞ (23)`
- Marenich, p.15074（PDF p.7）：`the second term is the solvation free energy of k defined as the free energy of transfer of the solute from the ideal-gas state at a solute partial pressure of 1 bar to a 1 M ideal solution.`
- Marenich, p.15071（PDF p.4）：`The key reason that this is not an insuperable problem is that experimental reduction potentials are relative values (measured with respect to a reference electrode), and thus the contribution from the electron cancels out when the full reaction is considered.`
- Marenich, p.15081-15082（PDF p.14-15），式 (42)-(43)：`U(Z,x) = UO(x) + Z[UR(x) - UO(x)]`；`@U/@Z = UR(x) - UO(x) = DU(x) (43) where DU(x) is the vertical energy gap (VEG) as an analogue of the vertical excitation energy controlled by the Franck-Condon principle.`

**边界.** Marenich 是一篇 Perspective（综述 + 方法汇总），**明确声明**
`Detailed analysis of kinetics or heterogeneous reactions is beyond the scope of the present article.`（PDF p.2）。
它**没有**碳酸酯溶剂的排序结论，也**没有**给出"垂直 vs 绝热 IP/EA"的严格定义句（见第 5 节勘误）。

---
## M4. 为什么我们研究的是 Li⁺ coordination-induced rank shift，而不是简单地说「加 Li⁺ 后结果更真实」？

**结论.** 因为加入 Li⁺ 不是"提高同一个可观测量的数值精度"，而是**更换了被计算的化学对象**：
`M` 与 `[LiM]⁺` 是两种不同的 conditional chemical state。Itkis 用同一个离子、同一个配体、
同一种 continuum 模型，仅改变"初始态溶剂分子是分离单体还是 (S)ₙ 团簇"，得到的 Li⁺ 溶剂化
自由能就平均相差 **14 kcal/mol**（≈0.607 eV）——这正是"参考态/状态定义"而非"数值精度"带来的差异。
既然状态的改变可以带来量级远大于方法误差的位移，那么"加 Li⁺"就应当被当作**一个新的排序问题**
（谁的排序被翻转），而不是"低精度→高精度"的同量替换。

**文献原句.**

- Itkis, 期刊 p.16077（PDF p.1，摘要）：`With n independent solvent molecules S initial state forming the "monomer" thermodynamic cycle, Li+ solvation free energies are found to be on average 14 kcal mol[据上下文还原：-1] more positive compared to those from the "cluster" thermodynamic cycle where the initial state is the cluster Sn.`
- Itkis, p.16077：`We ascribe the inconsistency between the "monomer" and "cluster" cycles mainly to the incorrectly predicted solvation free energies of solvent clusters Sn from the SMD and CPCM continuum solvation models.`
- Itkis, p.16083（PDF p.7）：`If the computational chemistry methods were perfect, the difference between the solvation Gibbs free energies of ions obtained via the "monomer" and "cluster" cycles would not exist.`
- Itkis, p.16079（PDF p.3）：`it is worth considering the following numbers n of solvent molecules in the first coordination sphere of the Li+ ion: 4, 5 for MeCN, DMA, water; 3, 4 for DME, pyridine, methanol; 3, 4, 5 for DMSO; 4, 5, 6 for DMF, GBL; and 4 for TMS.`
- Itkis, p.16078（PDF p.2）：`The 1 mol L[据上下文还原：-1] DG[据上下文还原：°]_clust can be obtained from DG[据上下文还原：°]_clust(1 atm standard state) minus DG1-* correction of 1.89 kcal mol[据上下文还原：-1] (T = 298.15 K) multiplied n times.`

**边界.** Itkis **不含**任何氧化/还原电位或电化学窗口；它只讨论 Li⁺ 的溶剂化自由能。
它给出的配位数是"值得考虑的 n"列表（说明配位数本身不确定），而**不是**群体分布 `p(C)`；
文中明确说 `identification of either global or the most stable local minima ... is an unworkable task`（p.16078）。
因此本项目不能从它取任何排序结论，只能取"状态定义会主导误差"这一条。

## M5. 为什么本项目应该说 molecular redox thermodynamic proxy，而不是 true electrochemical stability window？

**结论.** 因为真实电化学窗口由**多速率、多路径、含界面与钝化层**的过程决定，而我们的计算量是
"单分子（或单络合物）在隐式溶剂中的热力学 redox 自由能"。Borodin 明确指出：对绝大多数电解液，
用单一电位关联分子描述符会**误导**电解液开发，因为 redox 反应与界面化学反应耦合；且必须使用
"速率依赖的"多个电位。Peljo 的 EC 例子更直观：孤立 EC 氧化 ≈7 V vs Li/Li⁺，但与 PF6⁻ 络合并
发生 H-transfer 后降到 6.4-6.6 V（AVS）/5-5.2 V vs Li⁺/Li。因此我们只能说自己的量是
**molecular redox thermodynamic proxy**。

**文献原句.**

- Borodin, 期刊 p.87（PDF p.2）：`Unfortunately, recent studies indicated that for the overwhelming majority of battery electrolytes usage of such correlations could be misleading for electrolyte development due to the coupling of redox reactions with chemical reactions at electrochemical interfaces [7-12].`
- Borodin, p.87：`A shift factor of 1.4 accounts for the difference between the absolute potential scale and Li/Li[据上下文还原：+]. The shift factor depends on the nature of solvent, salt and concentration and might vary by 0.1-0.3 V.`
- Borodin, p.88（PDF p.3）：`A strong kinetic dependence of the multiple oxidation reactions suggests that a single oxidation potential cannot be used to characterize oxidation stability of the (EC)nPF6[据上下文还原：-] representative electrolyte clusters.`
- Borodin, p.92（PDF p.7）：`As clearly articulated by Peljo et al. usage of terms such as HOMO - LUMO should be avoided [8].`
- Borodin, p.86（PDF p.1）：`It usually has thickness from 3 nm to 10 nm [1,2].`（指 SEI 厚度；用于说明界面层是分子模型之外的新相）

**边界.** Borodin 是 review/opinion，**没有**可自动计算的排序或打分流程，**没有**统一的"真实窗口"
定量预测，也**没有** SEI 完整动力学参数。它给的经验 shift factor（1.4 V）并非可直接引用的本项目
标准（本项目采用显式热力学循环 + 溶液锚点），仅用于说明"绝对标度 → Li/Li⁺ 标度"的换算存在
0.1-0.3 V 的浓度/溶剂依赖漂移。

## M6. 本项目不能只重复「Li⁺ coordination 会改变 redox potential」；要回答：这种变化什么时候真的改变筛选决策？需要多少昂贵计算才能恢复 target ranking？

**结论.** Yang et al. 2025 是本项目**最直接的 prior art**：140 个电解质分子 × 2 种热力学循环
（有/无 Li⁺），M06-2X/6-311++G(d,p)+D3+SMD 自算靶值，32 个描述符，6 种 sklearn 模型，5 折 CV +
500 次重复，**随机 8:2** 划分；结论是 Li⁺ 使氧化/还原平均提升 0.60 / 0.71 V，XGB 测试集
R²=0.95（氧化）/0.90（还原）。**但**它只回答"会不会变、变多少"，**完全没有**回答本项目的两个问题：
(i) 这种位移**在哪些分子对上翻转了次序**；(ii) 需要**多少笔昂贵计算**才能把 target ranking 恢复。
反查全文证实：`inversion`/`invert`=0 次、`Spearman`=0、`Kendall`=0、`Top-k`/`Top-10`=0、
`regret`=0、`family`/`families`=0、`extrapolat`=0、`leave-one`=0、`holdout`=0、**`uncertaint`=0**。
Husch 则正面说明"排序质量可以好于数值精度"，给出 τ 型指标（抽取作 `t`，实为 Kendall τ）。

**文献原句.**

- Yang, PDF p.1（摘要）：`We conducted a systematic investigation of a 140 Li+-coordinated electrolytes library and discovered that the elevation in redox potential caused by Li+ is attributable to a combined effect of electrostatic and ion-dipole interactions.`
- Yang, PDF p.2：`there are no relevant ML algorithms specifically focusing on redox properties considering the coordination of Li+.`
- Yang, PDF p.3：`Before machine learning, the original data obtained from DFT calculations were randomly divided into train set and test set with a ratio of 8:2.`
- Yang, PDF p.4：`the incorporation of the Li+ ion elevates the average oxidative and reduction potentials of the electrolyte complexes by 0.60 and 0.71 V, respectively.`
- Yang, PDF p.5：`only the XGB model perform well for the prediction of oxidation and reduction potential with test R2 values of 0.95 and 0.90.`
- Yang, PDF p.3：`Finally, we selected 32 features with |ρ| ≤0.9 as input characteristics, ensuring their independence and low redundancy`（`≤` 未损坏，原文即可读）
- Husch, 期刊 p.3397（PDF p.4）：`Both correlation measures are very high, especially for the COSMOtherm-based estimates (with R values of 0.95 to 0.98 and t values of 0.73-0.78), which implies that the ranking of compounds with respect to these properties is even better than the prediction of the actual values.`

**边界.** Yang 用**随机** 8:2，无分族留出、无外推拆解、无不确定度——其"可迁移性"仅靠引用
Wang et al. 的**外部数据库**（RMSE 0.25 / 0.36 V）间接体现，不能证明本项目的 target ranking 在
新家族上可恢复。另需注意：Yang 的 32 个描述符**包含 HOMO/LUMO/EA/IP**，而被预测量正是由它们
推出的电位，存在**信息泄漏风险，文献未讨论**。Husch 不是 ML 训练（COSMOtherm + QSPR），
且**不含 Li⁺ 配位**，也明确 `Here we do not take electrolyte reactivity into account when screening for new materials`。

## M7. 为什么我们要重点研究 Spearman / Kendall τ / pairwise inversion / Top-k overlap / selection regret，而不是只报告 R² 和 MAE？

**结论.** 因为筛选的目标是**选出正确的 Top-k 集合**，而 R²/MAE 是"逐点数值误差"的度量，
两者在高相关候选密集时并不同步：模型可以把 MAE 压到很小，却把 Top-10 排错。Husch 用数据直接
说明"排序质量可以优于数值预测"（R=0.95-0.98 而 τ=0.73-0.78，且**全文 0 处出现 `MAE`/
`mean absolute error`，只用 MD/MAD/RMSD**），并进一步用 **5% 分箱**吸收模型误差后再判定 Pareto 最优。
所以本项目采用：Spearman ρ、Kendall τ_b、pairwise inversion（含 unresolved pair）、
Top-k overlap / Jaccard、selection regret，并把"排序变化是否大于不确定度"作为判定侵入性的核心。

**文献原句.**

- Husch, p.3397（PDF p.4）：`The correct ranking of compounds can be investigated by looking at correlation coefficients, such as Pearson's R values for linear correlation and Kendall's t values for non-linear (rank) correlation.`（`Kendall's t` 实为 `Kendall's τ`，抽取讹误）
- Husch, p.3397：`Mean absolute deviations (MADs) are higher for the consensus model especially in the case of viscosities.`
- Husch, p.3398（PDF p.5）：`To account for the inaccuracy of our approximate models we binned the computed values in 5 percent intervals before checking for Pareto-optimal cases.`
- Husch, p.3394（PDF p.1，摘要）：`all reasonable nitrile solvents up to 12 heavy atoms are generated and used to illustrate a suitable filter protocol for picking Pareto-optimal candidates.`

**边界.** Husch **没有**给出 pair-wise inversion、Top-k overlap、selection regret 这类指标
（全文 `inversion`=0、`regret`=0、`Spearman`=0），也**不含** Li⁺ 配位、不含 SEI/反应性、
不含不确定度量化。因此它只能支持"排序指标优先于纯数值误差"这一**方法论立场**，
不能提供可直接照搬的筛选评估流水线。本项目要补的正是这三个指标的落地与检验。

---

# 2. Part I 最低完成标准：8 个问题逐条回答

> 这 8 问是 reading list 的**硬性交付**（第 315-326 行）。每题给：① 结论；② 文献证据（含页码）；
> ③ 若文献不足以完全回答，明确说明缺口。

## Q1. 为什么 HOMO/LUMO 不能直接等同于 redox potential？

**结论.** 因为 HOMO/LUMO 是**孤立分子、冻结几何下的单电子能量本征值**，而 redox potential 是
**含溶剂/反离子、两个不同电荷态、各自弛豫后的 Gibbs 自由能之差**，再经参考电极换算。前者不含
结构弛豫、热校正、溶剂化与界面效应；二者只有经验相关、无普适等式。

**证据.** Peljo（p.2306）：`HOMO and LUMO are concepts derived from approximated electronic structure theory while investigating electronic properties of isolated molecules, and their energy levels do not indicate species participating in redox reactions. On the other hand, redox potentials are directly related to the Gibbs free energy difference of the reactants and products.`
Marenich（p.15068）：reduction potential 由 half-reaction 的标准 Gibbs 自由能算出，且该自由能需
`a thermodynamic cycle that includes the free energies of products and reactants in the gas phase and their free energies of solvation.`
定量对照：Peljo 给出 EC 的 HOMO = [还原：-]10.51 eV 而氧化电位 = 7.87 V（AVS）——差约 2.6 eV；
并明确 `utilization of the HOMO energy to indicate if the electrolyte would be stable would lead to overestimated electrolyte stability.`

**缺口.** 无。

## Q2. vertical 与 adiabatic IP/EA 有什么区别？

**结论（教科书定义，非本 6 篇原文）.** vertical IP/EA = **冻结中性分子平衡几何**（Franck-Condon
垂直跃迁）下移除/附加一个电子的能量；adiabatic IP/EA = 同时允许**中性态与离子态各自充分弛豫**
后的能量差。因此 adiabatic 总是比 vertical 更"小"（对 IP 而言，弛豫会降低阳离子能量），
二者的差 ≈ 该电对的**重组能**。

**证据（本 6 篇能提供的部分证据）.**

- Marenich, p.15082（PDF p.15），式 (43)：`@U/@Z = UR(x) - UO(x) = DU(x) (43) where DU(x) is the vertical energy gap (VEG) as an analogue of the vertical excitation energy controlled by the Franck-Condon principle.` —— 给出了"垂直量受 Franck-Condon 判据控制"的判据。
- Marenich, p.15084（PDF p.17），式 (59)：`U(me,x) = min[UO(x) + neme, UR(x)]`，其中 `UO(x) and UR(x) are the adiabatic potential energy surfaces for each oxidation state.` —— 明确区分 adiabatic PES。
- Marenich, p.15080（PDF p.12）：`72 adiabatic ionization potentials and 21 electron affinities` —— 该综述评估的是**绝热** IP/EA。
- Borodin, p.87（PDF p.2）图 1 caption：`The difference between vertical (Evert) and adiabatic (Ead) oxidation potentials is from the M05-2X/6-31+G(d,p) calculations.` 以及正文 `We suggest to follow the spirit of Marcus electron transfer theory and use a difference between the adiabatic and vertical oxidation potentials (Evert - Ead) as a descriptor for the kinetics of various oxidation reactions` —— 这是本 6 篇中**唯一**把 vertical/adiabatic 之差当作**有物理意义的量**使用的句子。
- Peljo, p.2308（PDF p.3）：`the difference of these two energies is due to the reorganization of the complex with its solvation shell, i.e. sudden removal of electron from Fe(II) complex leaves the resulting Fe(III) complex in an unoptimized configuration, and relaxation to typical Fe(III) configuration results in a reorganization energy of 1.92 eV.` —— 给出"垂直-绝热差 ≈ 重组能"的**量级**（本例 1.92 eV）。

**缺口（重要）.** 本 6 篇**没有**任何一句给出 IP/EA 意义下 vertical/adiabatic 的**严格定义句**：
全文关键词计数为 `adiabatic` 仅出现在 Marenich（5 次）与 Borodin（1 次），
`Franck` 仅 Marenich（3 次）；Itkis / Yang / Husch **0 次**（Peljo `adiabatic`=0）。
因此 Q2 的"定义"部分只能来自教材，文献只能提供**判据（Franck-Condon）**与**量级（1.92 eV）**。
→ 已在第 5 节列为 reading list 勘误项。

## Q3. 为什么 solution redox 需要 solvation free energy？

**结论.** 因为电子转移发生在溶液相，反应物与产物（尤其带电物种）从气相进入溶液时得失的自由能
不同，必须逐物种计入。标准做法是 Born-Haber 循环：气相反应自由能 + 各产物溶剂化自由能
- 各反应物溶剂化自由能。

**证据.** Marenich, p.15075（PDF p.8），式 (23)：`DrGo S(A|B) = DrGo g(A|B) + Σ_i DGo S(B_i) - Σ_i DGo S(A_i)`（抽取原文如此，符号据上下文还原）。
Marenich, p.15074（PDF p.7）：溶剂化自由能定义为 `the free energy of transfer of the solute from the ideal-gas state at a solute partial pressure of 1 bar to a 1 M ideal solution.`
Itkis, p.16077 摘要：`With n independent solvent molecules S initial state forming the "monomer" thermodynamic cycle, Li+ solvation free energies are found to be on average 14 kcal mol[还原：-1] more positive compared to those from the "cluster" thermodynamic cycle` —— 说明**同一个离子**的溶剂化自由能会因参考态定义不同而相差 14 kcal/mol。

**缺口.** 无（这是标准框架，Marenich 给得非常完整）。

## Q4. 为什么 M 与 [LiM]⁺ 是不同 chemical states？

**结论.** 因为二者的**化学计量、电荷、对称性与第一配位环境**都不同：`M` 是中性溶剂分子，
`[LiM]⁺` 是带正电的 Li⁺-溶剂络合物，其几何、电子结构与溶剂化响应都改变。热力学上，它们需要
**两条独立的 Born-Haber 循环**（不同产物集合，不同溶剂化项），而不是同一条循环里的数值修正。

**证据.** Yang, PDF p.2：`Two thermodynamic cycle patterns (with and without Li+) were considered here to obtain the input database, separately, leveraging high-throughput density functional theory (DFT) calculations.`（`separately` = 两条独立循环）
Yang, PDF p.3：`we screened configurations for Li+ binding to oxygen, nitrogen, and sulfur atoms of electrolyte molecules and choose the configuration with the most energetic stability.` —— Li⁺ 结合位点是**新的自由度**，与中性分子的构象空间不同。
Itkis, p.16083（PDF p.7）：`If the computational chemistry methods were perfect, the difference between the solvation Gibbs free energies of ions obtained via the "monomer" and "cluster" cycles would not exist.` —— 说明"态的定义"本身就能产生差异，与数值精度无关。

**缺口.** 无。

## Q5. 为什么 Li⁺ coordination effect 不是简单的 numerical fidelity correction？

**结论.** multi-fidelity 修正要求高低保真度是**同一个 observable 的不同近似**（形如
`P_H(x) = P_L(x) + Δ(x)`）；而 `M → [LiM]⁺` 改变的是**被计算的化学对象**（不同物种、不同电荷、
不同势能面），属于 **environment perturbation / conditional state 切换**，不是同量纲的数值精度差。
一个可操作的判据：若只是精度差，则二者之差应随方法精度提升而收敛到 0；Itkis 的证据表明
差值主要来自**参考态与 continuum 模型对团簇的错误描述**（14 kcal/mol），而不是"计算不够准"。

**证据.** Itkis, p.16077：`We ascribe the inconsistency between the "monomer" and "cluster" cycles mainly to the incorrectly predicted solvation free energies of solvent clusters Sn from the SMD and CPCM continuum solvation models.`
Itkis, p.16077：`When experimental-based solvation free energies of individual solvent molecules and solvent clusters are employed, the "monomer" and "cluster" cycles result in identical numbers.` —— 说明差异的根源是**模型对"态"的描述**，而非数值噪声。
Yang, PDF p.3（两条 separate cycle）与 PDF p.4（`0.60 and 0.71 V` 的系统位移）——位移是**物理的**（静电 + 离子-偶极），不是数值误差。
Multi-fidelity 的形式要求见 reading list 的 D3（Peherstorfer et al.），本 6 篇未提供 PDF，不作直接引用。

**缺口.** 这 6 篇**没有**任何一篇显式讨论 multi-fidelity 定义；Q5 的"为什么"依据的是
`P(M) → P([LiM]⁺)` 的态切换事实（Itkis/Yang）+ 教科书级 multi-fidelity 形式要求。

## Q6. 为什么真实 electrochemical window 比 molecular redox quantity 更复杂？

**结论.** 因为真实窗口由**多路径、多速率、含界面与钝化层**的过程共同决定：同一电解液存在多个
氧化/还原电位（对应不同反应路径与速率）；界面处 EDL 组分与本体不同（PF6⁻ 富集、离子聚集、
溶剂-盐共配位）；钝化层（SEI/CEI）改变后续反应的可及性。分子水平的热力学 redox 量只是这一
图景的**一个下限/代理**。

**证据.** Borodin, p.92（PDF p.7）：`it should be recognized that multiple oxidation and reduction potentials exist corresponding to reactions occurring at different rates.`
Borodin, p.87（PDF p.2）：`coupling of redox reactions with chemical reactions at electrochemical interfaces`
Borodin, p.87（PDF p.2）：`DFT calculations yield oxidation potential for an isolated solvent surrounded by implicit solvent at around 7 V vs. Li/Li[还原：+]. Oxidation stability of the EC(PF6-) and EC2 dimers surrounded by implicit solvent is, however, significantly lower (5-6 V vs. Li/Li[还原：+]) due to coupling of the oxidation reaction with the H-transfer from EC to PF6[-] or another EC molecule.`
Borodin, p.91（PDF p.5）：`Around 30% of inner part of EDL on the positive electrode consisted of PF6[-] anions when cell potential was 5 V [16].`
Borodin, p.86（PDF p.1）：`It usually has thickness from 3 nm to 10 nm [1,2].`（SEI）
Peljo, p.2308（PDF p.3）：H-transfer 使 EC 络合物氧化电位降到 `6.4-6.6 V on the AVS scale (5-5.2 V vs. Li+/Li)`。

**缺口.** Borodin 是 review，**无**统一"真实窗口"的定量预测流程；EDL/SEI 部分的数字来自引用
文献，本项目不能直接复用为靶值。

## Q7. 为什么 MAE 小不意味着 screening decision 一定正确？

**结论.** 因为筛选决策只依赖**候选之间的次序**（尤其 Top-k 成员），而 MAE/R² 度量的是
**逐点数值误差**；当候选密集时，小的数值误差也能把大量相邻候选的次序打乱，从而改变 Top-k 集合。
Husch 用经验证据支撑"排序质量可以优于数值预测"：同一批模型 R=0.95-0.98 但 τ=0.73-0.78；
且该文**全文不使用 MAE**（`mae`/`mean absolute error` = 0 次），改用 MD/MAD/RMSD 与分箱，
并用 Pareto 过滤挑选候选。

**证据.** Husch, p.3397（PDF p.4）：`Both correlation measures are very high, especially for the COSMOtherm-based estimates (with R values of 0.95 to 0.98 and t values of 0.73-0.78), which implies that the ranking of compounds with respect to these properties is even better than the prediction of the actual values.`
Husch, p.3397：`Mean absolute deviations (MADs) are higher for the consensus model especially in the case of viscosities.`
Husch, p.3398（PDF p.5）：`To account for the inaccuracy of our approximate models we binned the computed values in 5 percent intervals before checking for Pareto-optimal cases.`
关键词计数（全文小写）：`pareto`=6、`kendall`=7、`ranking`=11、`mae`=0、`mean absolute error`=0、`spearman`=0。

**缺口.** Husch 未给 Top-k overlap / selection regret 的定量定义，也未做"MAE 小但 Top-k 错"的
对照实验；本项目需自行实现并量化（这正是 Stage 6-7 的交付）。

## Q8. 为什么 random train/test split 可能高估模型的 transferable performance？

**结论.** 因为随机划分允许**同一家族/同一母体结构的近邻分子**同时出现在训练集与测试集，
模型可以靠"记住家族"而非"学到可迁移的物理"来取得低误差；当测试集换成**未见过的家族**时，
性能会显著下降。因此随机 8:2 得到的是**插值性能**，不是**外推（transferable）性能**。

**证据（本 6 篇能提供的）.**
Yang, PDF p.3：`the original data obtained from DFT calculations were randomly divided into train set and test set with a ratio of 8:2.` —— prior art **只做随机划分**。
Yang 的"可迁移性"证据来自**外部数据库**（PDF p.5）：`The transferability analysis for the trained XGB model are carried out based on the published database from Wang et al. ... both of the oxidation and reduction potential exhibits well prediction accuracy with RMSE values of 0.25 and 0.36 V` —— 即随机划分本身无法证明可迁移，只能靠外部数据间接体现。
关键词计数：Yang 全文 `leave-one`=0、`holdout`=0、`extrapolat`=0、`family`/`families`=0、`uncertaint`=0；Husch/Itkis/Borodin/Peljo 亦无分族留出。

**缺口（重要）.** **这 6 篇中没有一篇做了 leave-family-out / leave-one-family-out 或等价的外推拆解**。
Q8 的"为什么"由**统计推断原理**（近邻泄漏）支撑，加上"prior art 只做随机划分"这一事实性证据。
本项目在 Stage 7 用 `random / group / leave-one-family-out` 三种拆分**并列报告**，正是为补此空白。

---

# 3. 定量事实表

换算口径（全表统一）：`1 eV = 96.4853321233 kJ/mol`；`1 kcal/mol = 4.184 kJ/mol`
（故 `1 kcal/mol = 0.043364 eV`）。所有数值均回到 PDF 抽取文本核对。

| # | 文献事实 | 原文数值（含抽取还原说明） | 页（期刊页 / PDF 页） | 换算（本项目统一口径） |
|---|---|---|---|---|
| 1 | SHE 在水中的绝对标准电位（IUPAC 推荐） | `4.44 [还原：±] 0.02 V` @298.15 K | Marenich p.15069 / p.3 | 428.39 kJ/mol |
| 2 | 上述值的替代参考范围 | `4.05 to 4.44 V`（另处作 `4.05 to 4.42 V`） | Marenich p.15071 / p.5 | 390.77 - 428.39 kJ/mol |
| 3 | 参考电极换算（Table 2 选值） | 4.44 V / 4.42 V / 4.28 V / 4.28 V | Marenich p.15071 / p.5 | 428.39 / 426.46 / 412.96 kJ/mol |
| 4 | 用自洽参考值时相对 SHE 电位的 MUE | `0.08 V`（与 ΔG°S(H⁺)=-1105 kJ/mol 自洽）；改用 4.42 V 则 `0.20 V` | Marenich p.15072 / p.6 | 7.72 / 19.30 kJ/mol |
| 5 | 硼氢化合物/DFT 计算 IP+EA 的 MUE 量级 | 复合方法 `about 60 mV (or 6 kJ mol-1)`；DFT 一般 `[还原：≥]20 kJ mol-1`（抽取作 `420`）；M05-2X/M06-2X `about 12 and 10 kJ mol-1` | Marenich p.15080 / p.13 | 60 mV = 5.79 kJ/mol |
| 6 | 22 个中性有机物水相单电子氧化电位 MUE | `270 to 500 mV` | Marenich p.15079 / p.13 | 26.05 - 48.24 kJ/mol |
| 7 | 过渡金属配合物 95 个的标准还原电位 MUE（B3LYP+PB） | `about 0.4 V`，加七参数修正后 `0.12 V` | Marenich p.15091 / p.24 | 38.59 / 11.58 kJ/mol |
| 8 | Borodin 热力学循环的绝对标度→Li/Li⁺ 位移因子 | `1.4`（`accounts for the difference between the absolute potential scale and Li/Li+`） | Borodin p.87 / p.2 | 135.08 kJ/mol |
| 9 | 上述位移因子的溶剂/盐/浓度漂移 | `might vary by 0.1-0.3 V` | Borodin p.87 / p.2 | 9.65 - 28.95 kJ/mol |
| 10 | 孤立 EC（隐式溶剂）氧化电位 | `around 7 V vs. Li/Li+` | Borodin p.87 / p.2 | 675.40 kJ/mol |
| 11 | EC(PF6⁻) 与 EC₂ 二聚体（含 H-transfer）氧化电位 | `significantly lower (5-6 V vs. Li/Li+)` | Borodin p.87 / p.2 | 482.43 - 578.91 kJ/mol |
| 12 | EC₂ 若 EC(-H) 开环后的氧化电位 | `[还原：≈]4.3 V vs. Li/Li+` | Borodin p.87 / p.2 | 414.89 kJ/mol |
| 13 | EC(-H) 开环势垒 | `0.65[-]0.91 eV` | Borodin p.87 / p.2 | 62.72 - 87.80 kJ/mol |
| 14 | FEC(-H) vs EC(-H) 开环势垒 | `1.28 eV for FEC(-H) vs. 0.91 eV for EC(-H)` | Borodin p.90 / p.5 | 123.50 / 87.80 kJ/mol |
| 15 | SL-FSI 氧化电位（本项目 SL 锚点同源） | `4.65 V vs. Li/Li+`；SL-LiFSI 络合物高 `[还原：≈]0.9 V` | Borodin p.89 / p.4 | 448.66 / 86.84 kJ/mol |
| 16 | 线性碳酸酯实验还原电位 | `around 1.4[-]1.5 V`；高盐 Li⁺(DMC)Li⁺ 还原 `1.4 V` vs Li⁺EC `[还原：≈]0.6 V` | Borodin p.90-91 / p.6 | 135.08 - 144.73 kJ/mol |
| 17 | 5 V 时正极 EDL 内层 PF6⁻ 占比 | `Around 30%` | Borodin p.91 / p.5 | - |
| 18 | SEI 厚度 | `from 3 nm to 10 nm` | Borodin p.86 / p.1 | - |
| 19 | Peljo：HOMO/电位偏差最大量级 | `offset as high as 4 eV from the HOMO energies` | Peljo p.2306 / p.1 | 385.94 kJ/mol |
| 20 | Peljo：74 个有机物的 LUMO-还原电位线性相关 | `slope of [还原：-]1.12, intercept of [还原：-]4.34 and R2 of 0.9917` | Peljo p.2308 / p.3 | - |
| 21 | Peljo：过渡金属配合物的相关性（反例） | 还原 `slope [还原：-]1.23, intercept [还原：-]8.9 eV, R2 0.32`；氧化 `[还原：-]1.09, [还原：-]7.3 eV, R2 0.71` | Peljo p.2308 / p.3 | - |
| 22 | Peljo：常见溶剂 HOMO vs 计算氧化电位 | EC `[还原：-]10.51 eV` vs `7.87 V`(AVS)；DMC `[还原：-]9.64 eV` vs `7.07 V`(AVS) | Peljo p.2308 / p.3 | - |
| 23 | Peljo：EC+PF6⁻ 络合且 H-transfer 后的氧化电位 | `6.4[-]6.6 V on the AVS scale (5[-]5.2 V vs. Li+/Li)` | Peljo p.2308 / p.3 | 617.51 - 636.80 kJ/mol (AVS) |
| 24 | Peljo：Fe 电对的重组能（垂直-绝热差量级） | `reorganization energy of 1.92 eV` | Peljo p.2308 / p.3 | 185.25 kJ/mol |
| 25 | Peljo：Nernst 浓度比引起的电位漂移 | 10:1 → `59 mV`；100:1 → `118 mV` | Peljo p.2308 / p.3 | 5.69 / 11.39 kJ/mol |
| 26 | Itkis：monomer vs cluster 循环的 Li⁺ 溶剂化自由能差 | `on average 14 kcal mol[还原：-1] more positive` | Itkis p.16077 / p.1 | 58.58 kJ/mol = 0.6071 eV |
| 27 | Itkis：1 atm → 1 mol/L 标准态换算修正 | `DG1-* correction of 1.89 kcal mol[还原：-1] (T = 298.15 K)` | Itkis p.16079 / p.3 | 7.908 kJ/mol = 0.0820 eV |
| 28 | Itkis：Li⁺ 第一配位壳"值得考虑的" n 值 | MeCN/DMA/water `4, 5`；DME/pyridine/methanol `3, 4`；DMSO `3, 4, 5`；DMF/GBL `4, 5, 6`；TMS `4` | Itkis p.16079 / p.3 | - |
| 29 | Yang：Li⁺ 配位导致的平均 redox 电位提升 | `elevates the average oxidative and reduction potentials ... by 0.60 and 0.71 V` | Yang p.4 | 57.89 / 68.50 kJ/mol |
| 30 | Yang：XGB 测试集 R²（有 Li⁺） | 氧化 `0.95`、还原 `0.90` | Yang p.5 | - |
| 31 | Yang：XGB 在外部数据库上的 RMSE | `0.25 and 0.36 V` | Yang p.5 | 24.12 / 34.73 kJ/mol |
| 32 | Yang：电位跨度 | 氧化 `spans approximately 4.00 eV`，约为还原的 2 倍 | Yang p.4 | 385.94 kJ/mol |
| 33 | Yang：数据集与计算条件 | `140 electrolyte molecules`；`M06-2X/6-311++G(d,p)`+D3+SMD，`323.15 K`，Gaussian 16；`32 features with` \|ρ\| `≤0.9`；随机 `8:2`；500 次重复 | Yang p.2-3 | - |
| 34 | Yang：电位换算常数（其采用值） | `Eox(vs Li+/Li) = ΔGoxsolv/(nF) - 4.48 + 3.04 = ΔGoxsolv/(nF) - 1.44` | Yang p.3 | 4.48 V = 432.25 kJ/mol |
| 35 | Husch：COSMOtherm 估计的数值相关性 | `R values of 0.95 to 0.98 and [还原：τ] values of 0.73-0.78` | Husch p.3397 / p.4 | - |
| 36 | Husch：MAD 相对属性窗口的占比 | `in the order of about 10 to 15 percent of the relevant property windows` | Husch p.3397 / p.4 | - |
| 37 | Husch：Pareto 判定前的分箱 | `binned the computed values in 5 percent intervals` | Husch p.3398 / p.5 | - |
| 38 | Husch：筛选规模链 | `100 000 structures` → 约 `10 000` 子集 → `8772 candidates` 成功 → `72` → `53 Pareto-optimal`（腈类算例另有一组数量级相同的流程） | Husch p.3398 / p.5 | - |

**注.** 表中 "-" 表示该项无量纲换算。第 5 行 `[还原：≥]20 kJ mol-1` 系抽取把 `≥` 讹为 `4`；
第 35 行 `t values` 系抽取把 `τ` 讹为 `t`；第 23 行 AVS 与 vs Li⁺/Li 两列均按原文并列给出。

---

# 4. 「共同空白 = 本项目 Stage 7–8 立足点」

以下 5 条空白，均以**逐字关键词全文检索**为依据（检索对象为 6 篇 PDF 的 pymupdf 抽取文本，
已统一转小写；`τ` 因抽取讹为 `t`，故另以 `kendall` 覆盖）。

## 4.0 检索结果矩阵（命中次数）

| 检索词 | Peljo | Marenich | Itkis | Borodin | Yang | Husch |
|---|---|---|---|---|---|---|
| `inversion` / `invert` | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| `spearman` | 0 | 0 | 0 | 0 | 0 | 0 |
| `kendall` | 0 | 0 | 0 | 0 | 0 | 7 |
| `top-k` / `top-10` | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| `regret` | 0 | 0 | 0 | 0 | 0 | 0 |
| `uncertaint*` | 0 | 4 | 1 | 0 | 0 | 0 |
| `extrapolat*` | 0 | 5 | 0 | 0 | 0 | 0 |
| `family` / `families` | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| `leave-one` | 0 | 0 | 0 | 0 | 0 | 0 |
| `holdout` | 0 | 0 | 0 | 0 | 0 | 0 |
| `ranking` | 0 | 0 | 0 | 0 | 2 | 11 |
| `adiabatic` | 0 | 5 | 0 | 1 | 0 | 0 |
| `active learn` | 0 | 0 | 0 | 0 | 1 | 0 |

**命中项的语义核实（避免误读）.**

- `uncertaint*` 命中：Marenich 4 次、Itkis 1 次，均指**实验/理论绝对电位的数值不确定度**
  （如 `the uncertainty associated with recent experimental and theoretical determinations of
  absolute reduction potential values for the SHE`），**不是**预测的不确定度量化（UQ）；
  Yang 0 次 → **预测不确定度在 prior art 中完全缺位**。
- `extrapolat*` 命中：仅 Marenich 5 次，指 (a) 电位测量外推到无限稀释/零离子强度，
  (b) 完备基组（CBS）外推；**不是** ML 的家族外推（out-of-family）评估。
- `ranking` 命中：Yang 2 次指 **feature importance 的排名**（`This ranking aligns with the fact
  that Li+ tends to locate around these two functional groups`），Husch 11 次指**候选排序质量**；
  二者都不是"筛选决策评估"的完整框架。
- `active learn` 命中：Yang 仅 1 次，且出现在**参考文献标题**中
  （`Quantum chemistry-informed active learning to accelerate the design and discovery of
  sustainable energy storage materials, Chem. Mater. 32 (2020)`），Yang **本人未做 active learning**。

## 4.1 空白①：Li⁺/方法/环境误差在**哪一类候选对上**翻转子次序 —— 未见

**查过**：6 篇全部。**查什么**：`inversion`、`invert`、`top-k`、`regret`。
**结果**：全部 0 次。Yang 只报告平均位移（0.60 / 0.71 V）与全局 R²/RMSE，**从未**考察
"哪一对 (i,j) 的次序被 Li⁺ 配位翻转"；Borodin 定性指出会 `overestimated`（高估稳定性），
但不细到候选对。→ **这正是本项目 Stage 6/7 的 `pairwise inversion` 与 `robust inversion fraction` 要填的空白。**

## 4.2 空白②：需要**多少昂贵计算**才能恢复 target ranking —— 未见

**查过**：6 篇全部。**查什么**：`top-k`、`top-10`、`regret`、`active learn`。
**结果**：前三者全 0；`active learn` 仅在 Yang 的参考文献标题中出现 1 次。
Husch 的筛选链（`100 000 → 8772 → 72 → 53`）是**固定流程的漏斗**，不是"随预算递增的
排序恢复曲线"。→ **本项目 Stage 8 的 retrospective replay（`n_T → {τ_b, O_k, R_k}`）要填此空白。**

## 4.3 空白③：用 pairwise inversion + Top-k overlap + selection regret 而非 R²/MAE 评估筛选决策 —— 未见

**查过**：6 篇全部。**查什么**：`inversion`、`regret`、`top-k`、`spearman`、`kendall`、
`mae`/`mean absolute error`。
**结果**：`inversion`=0、`regret`=0、`top-k`=0、`spearman`=0 于全部 6 篇；`kendall`=7 仅 Husch
（且是抽取讹为 `t` 的 τ）；Husch `mae`=0、`mean absolute error`=0（只用 MD/MAD/RMSD = 它们
自己定义了 `Mean absolute deviations (MADs)`）。最接近的是 Husch 的 Kendall τ + Pareto 分箱，
但它**不是** Top-k 恢复/regret 框架。Yang 只用 R² 与 RMSE。→ **本项目 Stage 7 的指标矩阵要填此空白。**

## 4.4 空白④：用**分族留出**证明随机划分高估可迁移性 —— 未见

**查过**：6 篇全部。**查什么**：`family`、`families`、`leave-one`、`holdout`、`extrapolat`。
**结果**：`family`/`families`/`leave-one`/`holdout` 全部 0 次；`extrapolat` 的 5 次命中全在
Marenich 且与 ML 无关（见 4.0）。Yang 用的是**随机 8:2**（PDF p.3 原句），其可迁移性论证靠
**外部数据库**（Wang et al.）的 RMSE 0.25/0.36 V 间接给出。→ **本项目 Stage 7 的
`random / group / leave-one-family-out` 三拆分并列报告要填此空白。**

## 4.5 空白⑤：vertical/adiabatic（IP/EA 意义下）的**严格定义句**在这 6 篇里找不到

**查过**：6 篇全部。**查什么**：`adiabatic`、`vertical`、`franck`。
**结果**：`adiabatic` 仅 Marenich(5) 与 Borodin(1)；`franck` 仅 Marenich(3)；Itkis/Yang/Husch 全 0。
能提供的只有：Franck-Condon 判据（Marenich p.15082）、adiabatic PES 的显式使用（Marenich p.15084
式 59）、以及 `Evert - Ead` 作为动力学描述符（Borodin p.87 图 1）与"垂直-绝热差 ≈ 重组能 =
1.92 eV"的量级（Peljo p.2308）。**没有**"vertical IP/EA = 冻结几何的 ΔE；adiabatic IP/EA =
各自弛豫后的 ΔE"这类严格定义句。→ 已列入第 5 节勘误。

---

# 5. reading list 勘误

## 5.1 M7 标题不完整

- reading list 写作：`Husch et al., 2015 — Large-scale virtual high-throughput screening for the identification of new battery electrolyte solvents`
- **完整标题**（PDF p.1 原样）：`Large-scale virtual high-throughput screening for the identification of new battery electrolyte solvents: computing infrastructure and collective properties`
  —— 副标题 **`: computing infrastructure and collective properties`** 缺失。
- 出处核对：`Phys. Chem. Chem. Phys., 2015, 17, 3394-3401`；作者
  `Tamara Husch, Nusret Duygu Yilmazer, Andrea Balducci, Martin Korth`（PDF p.1）。
- 影响：该文的两条主线正是"志愿计算基础设施"与"集体性质（熔点/沸点/闪点/黏度）"，
  缺失副标题会误导读者以为它只做电子结构筛选。

## 5.2 vertical vs adiabatic 的严格定义句在这 6 篇中不存在

- 见 4.5：6 篇中无一句给出 IP/EA 意义下 vertical/adiabatic 的严格定义。
- 能给出的替代证据：
  - **Franck-Condon 判据**：Marenich, p.15082（PDF p.15）——`DU(x) is the vertical energy gap
    (VEG) as an analogue of the vertical excitation energy controlled by the Franck-Condon principle.`
  - **垂直-绝热差额量级**：Peljo, p.2308（PDF p.3）——Fe 电对 `reorganization energy of 1.92 eV`。
  - **工业级用法**：Borodin, p.87（PDF p.2）——把 `(Evert - Ead)` 当作**动力学**描述符
    （`use a difference between the adiabatic and vertical oxidation potentials (Evert - Ead) as a
    descriptor for the kinetics of various oxidation reactions`），而不是精度问题。
- 建议：reading list 的 M3 条目应在"vertical vs adiabatic"旁注明"该定义需查教材/专门文献，
  本 Minimal 清单不含"。

## 5.3 其他观察（非勘误，但影响引用方式）

- reading list 引 Marenich 的 DOI `10.1039/C4CP01572J` 正确；但需注意原文用的是
  `4.44 ± 0.02 V`（IUPAC 推荐）而 Yang 2025 用的是 `4.48 V`（本文第 3 节 #1、#34）。
  **两篇文献的 SHE 锚点不同（差 0.04 V）**，本项目引用时必须显式声明所用锚点。
- Peljo 是 **Opinion**（`In this opinion we provide ...`），不含新计算；引其定量数字时
  均应标注"转引原始文献"而非"Peljo 计算"。

---

# 6. 覆盖度自检

| 问题编号 | 是否给出文献证据 | 证据充分度 | 说明 |
|---|---|---|---|
| M1 | 是（P1/P2/P4 间接） | 中 | M1 无 PDF；用 P1/P2/P4 支撑"热力学 vs 动力学/界面"分界 |
| M2 | 是（P1 直接） | 高 | Peljo 全文即围绕此问题 |
| M3 | 是（P2 直接，式 23/42/43） | 高 | 框架完整 |
| M4 | 是（P3 直接） | 高 | Itkis 14 kcal/mol + 参考态依赖 |
| M5 | 是（P4 直接） | 高 | Borodin 多速率电位 + 界面耦合 |
| M6 | 是（P5 直接 + P6 辅助） | 高 | Yang prior art + 关键词空白举证 |
| M7 | 是（P6 直接） | 中-高 | Husch 支持方法论立场；Top-k/regret 需本项目自建 |
| Part I Q1 | 是（P1/P2） | 高 | - |
| Part I Q2 | **部分** | **低-中** | 6 篇**无严格定义句**；仅 Franck-Condon 判据 + 1.92 eV 量级 + Borodin 的 `Evert-Ead` 用法 |
| Part I Q3 | 是（P2 式 23） | 高 | - |
| Part I Q4 | 是（P5/P3） | 高 | 两条独立循环 + 结合位点自由度 |
| Part I Q5 | **部分** | **中** | 依据态切换事实；multi-fidelity 形式要求来自 reading list D3，本 6 篇无 |
| Part I Q6 | 是（P4 直接） | 高 | - |
| Part I Q7 | 是（P6 直接） | 中-高 | Husch 无 Top-k/regret 定义 |
| Part I Q8 | **部分** | **中** | 依据统计原理 + "prior art 只做随机划分"的事实；6 篇**均无**分族留出实验 |

**明确未能给出文献证据的问题**：Part I **Q2**（vertical/adiabatic 的严格定义句）与
Part I **Q5** 的 multi-fidelity 形式化（本 6 篇无该术语），已在 4.5 / 5.2 标注。
**抽取文本中未见明确表述**的事项：Yang 是否做 Li⁺ 结合的系综/Boltzmann 平均（原文只写
"choose the configuration with the most energetic stability"，即**单一最稳构型**）；
Itkis 的 `p(C)` 群体分布（原文无群体分布，只有"值得考虑的 n 值"列表）。

---

*draft 完成。等待主线复核后落盘 `docs/14_reading_list_qa.md`。*


---

## 7. 本文档的来源与可复现性

- 依据文献（6 篇 PDF，位于 `核心文件/文献/`）：
  - `c8ee01286e.pdf` — Peljo & Girault, *Energy Environ. Sci.* 2018, 11, 2306–2309, DOI `10.1039/C8EE01286E`
  - `c4cp01572j.pdf` — Marenich, Ho, Coote, Cramer & Truhlar, *Phys. Chem. Chem. Phys.* 2014, 16, 15068–15106, DOI `10.1039/C4CP01572J`
  - `d1cp01454d.pdf` — Itkis, Cavallo, Yashina & Minenkov, *Phys. Chem. Chem. Phys.* 2021, 23, 16077–16088, DOI `10.1039/D1CP01454D`
  - `1-s2.0-S2451910318302035-main.pdf` — Borodin, *Curr. Opin. Electrochem.* 2019, 13, 86–93, DOI `10.1016/j.coelec.2018.10.015`
  - `1-s2.0-S2468606925003296-main.pdf` — Yang et al., *Mater. Today Energy* 2025, 54, 102121, DOI `10.1016/j.mtener.2025.102121`
  - `c4cp04338c.pdf` — Husch, Yilmazer, Balducci & Korth, *Phys. Chem. Chem. Phys.* 2015, 17, 3394–3401, DOI `10.1039/C4CP04338C`
- M1（Bard / Faulkner / White 教材）未提供 PDF，相关条目仅作概念性回答，并已逐条标注。
- 抽取文本副本：`outputs/_week7_scratch/lit/*.txt`（`pymupdf`，每页以 `===== PAGE n =====` 分隔）；
  抽取脚本 `outputs/_week7_scratch/extract.py`。抽取造成的符号损坏见 §0.1。
- 本文档为 Stage 0 / Week 7 交付物，回答对象是 `核心文件/ranking-electrolyte-materials-reading-list.md`。
  该 reading list 本身**未被修改**；两处需要更正之处以 §5「勘误」形式给出，供 PI 决定是否回改原文件。
