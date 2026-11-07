# 分支 A–D 文献问答（Part II In-depth）

**对象**：`核心文件/文献/分支a-d/` 中的 7 篇 PDF。
**与 `docs/14_reading_list_qa.md` 的分工**：`docs/14` 回答 Part I 的 M1–M7 与「最低完成标准」8 问；本文回答 Part II 的 **A / B / C 三支**（问题驱动型扩展阅读），并给出对项目方法的直接含义。
**未提供的分支**：`分支a-d/` 目录里实际只有 A、B、C 三支的 7 篇。reading list 的 **C3**（JACS 2023, `10.1021/jacs.2c11807`）、**D1**（Rasmussen & Williams 教材）、**D2**（Settles 综述）、**D3**（`10.1137/16M1082469`）、**E**（Efron & Tibshirani 教材）**均无 PDF**，因此本文不对它们作答（见 §5）。

---

## 0. 抽取方法与必须声明的一致性瑕疵

7 篇均由 PyMuPDF（`pymupdf 1.28.2`）以 `page.get_text()` 抽取为纯文本，逐页以 `===== PAGE n =====` 分隔，落在 `outputs/_week8_scratch/lit/`。

**系统性字符损坏**（`docs/14` 已记录的同一类问题，本轮复核仍然成立）：

| 现象 | 例子 | 影响 |
|---|---|---|
| U+2212 负号整字丢失 | `E = 4.86 kcal mol`（原文为 −4.86） | 所有负号需**按上下文还原** |
| `±` 被删 | `0.78%` 前的误差范围丢失 | 不确定度不可直接引用 |
| 数学字体塌陷 | `Δ`→`DrGo`、`R²`→`R2`、`Fe²⁺`→`Fe2+`、`σ`→空格 | 公式必须回 PDF 核对 |
| 关系符被替换 | `<`→`o`、`≈`→`B`、`≥`→`4`、`τ`→`t` | 阈值类表述必须核对 |

**因此**：本文的英文原句逐字取自抽取文本（不改写、不代填符号）；凡涉及正负号/不等号的数值，均在引文之外用中文注明真实读法并标注「据上下文还原」。凡本代理**无法从抽取文本确认**的，一律写明「未能从抽取文本确认」，不推测。

**页码换算**（PDF 第 N 页 = 期刊页，按各刊首页核实）：

| 篇 | 期刊页起点 | 换算 |
|---|---|---|
| A1 | 6378 | 6377 + N |
| A2 | 6367 | 6366 + N |
| A3 | 9955 | 9954 + N |
| B1 | 1652 | 1651 + N |
| B2 | 114110 | 114109 + N |
| C1 | 10970 | 10969 + N |
| C2 | 490 | 489 + N |

---

## 1. A 支：solution thermochemistry

### A1. SMD — Marenich, Cramer & Truhlar, *J. Phys. Chem. B* **2009**, 113, 6378–6396, `10.1021/jp810292n`

**A1-Q1：SMD 到底把溶剂近似成了什么？总自由能怎么分解？**

**结论**：SMD 把溶剂近似成「一个**由体相介电常数与原子表面张力共同定义**的连续介质」——前半段是标准自洽反应场（NPE/IEF-PCM），后半段是**与溶剂可及表面积（SASA）成正比的经验表面张力**。它不是一个纯粹的介电连续体。

原文（摘要，p.6378）：
> "Continuum denotes that the solvent is not represented explicitly but rather as a dielectric medium with surface tension at the solute-solvent boundary."

原文（p.6378）：
> "The model separates the observable solvation free energy into two main components. The first component is the bulk electrostatic contribution arising from a self-consistent reaction field treatment that involves the solution of the nonhomogeneous Poisson equation for electrostatics in which the solute is represented by its full electron density. ... The second contribution is a cavity-dispersion-solvent-structure term ..."

即

```
ΔG*_Solv  =  ΔG_EP   +   G_CDS
             (体相静电)    (空腔–色散–溶剂结构)
```

**A1-Q2：cavity / non-electrostatic 项具体包含什么？为什么它不是介电响应？**

**结论**：`CDS = cavitation + dispersion + solvent-structure`，实现方式是**每个原子的经验表面张力 × 该原子的 SASA**。关键在于：CDS **被参数化去吞掉体相静电模型的一切偏差**——包括溶质电荷模型的不精确、介电/固有库仑半径假设的不精确、以及电荷溢出空腔（outlying charge）处理的误差。因此「非静电项」这个名字在物理上是有误导性的。

原文（p.6379）：
> "The contribution of the C, D, and S effects is labeled CDS, and the CDS contribution to the free energy of solvation is a sum of terms that are proportional (with geometry-dependent proportionality constants called atomic surface tensions) to the solvent-accessible surface areas (SASA) of the individual atoms of the solute."

原文（p.6379，关键）：
> "The CDS terms are parametrized to include all of the deviations of the electrostatics from the assumed bulk model, such as the inexactness of the solute charge model and the inexactness of the solvent permittivity model including assumed values for intrinsic Coulomb radii and uncertainties in the treatment of solute charge outside the cavity."

原文（p.6379）：
> "there is no thermodynamically unique way to separate the bulk electrostatic contribution to the free energy of solvation from the non-bulk-electrostatic one; only their sum is a state function."

**A1-Q3：为什么 SMD ≠「给 PCM 设一个 ε」？**

**结论**：因为 SMD 的 G_CDS 不是介电响应，而是**把 ε 之外的短程物理（空腔形成功、色散、第一溶剂壳的结构效应，含氢键与交换排斥）全部经验化**。体相静电项与真实溶剂之间的差额并不随 ε 一起变化，它是被 SASA 项单独拟合掉的。原文（p.6379）：

> "reliable calculations of solutes in solution must take into account not only bulk electrostatics (that is long-range electrostatic polarization effects) but also shorter-range polarization effects and shorter-range nonelectrostatic effects such as cavitation, dispersion, and solvent structural effects (CDS), the latter including both hydrogen bonding and exchange repulsion effects."

并且（p.6379）明确：SMD 用「尽量简单的空腔定义」，靠半经验表面张力去补偿空腔定义本身的不确定性：

> "we keep the cavity definition as simple as possible, thereby achieving a clear and systematic definition of the bulk electrostatic contribution ..., and we attempt to make up for the intrinsic uncertainty in cavity definition and its variation with chemical environment and functionality by the use of semiempirical surface tensions"

**A1-Q4：用了多少溶剂描述符？对带电溶质/H-bonding 溶剂怎么处理？**

**结论**：SMD 的原子表面张力被写成 **5 个溶剂描述符**的函数：介电常数 ε、折射率 n、Abraham 氢键酸度 α、Abraham 氢键碱度 β、宏观（体相）表面张力 ψ²（摘要 p.6378 表述为 "dielectric constant, refractive index, bulk surface tension, and acidity and basicity parameters"）。**不含任何显式氢键项**——氢键是通过 Abraham α/β 参数与 CDS 表面张力**隐式**吸收的。

原文（p.6381）：
> "σ̃_i ... are functions of a set of solvent descriptors. This dependence is given by ... n is the refractive index of the solvent at room temperature (which is conventionally taken as 293 K for this quantity), α is Abraham's hydrogen bond acidity parameter of the solvent ..., β is Abraham's hydrogen bond basicity parameter of the solvent ..."

对带电溶质：SMD 用**完整电子密度**（不是原子部分电荷），并训练了选择性聚簇的离子数据（p.6380）：
> "2346 reference solvation free energies for neutrals in 90 organic solvents and water and for single cations and anions in water, acetonitrile, dimethyl sulfoxide, and methanol"（支持信息摘要，p.6392–6393）

**A1-Q5：精度量级与训练集规模？**

- 参数**只需一套**，同时优化于 **6 种电子结构方法**（M05-2X/MIDI!6D、M05-2X/6-31G*、M05-2X/6-31+G**、M05-2X/cc-pVTZ、B3LYP/6-31G*、HF/6-31G*）（p.6380、p.6392）。
- 中性分子 MUE **0.5–0.8 kcal/mol**；离子 MUE **2–7 kcal/mol**（p.6379，该句在描述 SM8 的成绩并被 SMD 沿用为参照水平）。
- 训练/测试集规模：2346 条中性+离子溶剂化自由能、143 条中性溶质在 15 种有机溶剂间的转移自由能、112 条选择性聚簇离子（水）、220 条未聚簇离子（乙腈/DMSO/甲醇）（p.6392–6393）。

**A1 最重要的边界（对本项目是决定性的）**，原文 p.6379：

> "the assumption that the electrostatic interactions of the solute and the surrounding solvent do not depend on the molecular structure of the solvent and that the dielectric response of the medium is uniform and linear at all positions outside the space that defines the solute may not provide a completely valid description of the solvent in the first solvation shell. This assumption is particularly poor when strong, specific interactions between a solute and one or more first-shell solvent molecules are present, for example strong hydrogen bonding, π-π stacking interactions, or **monatomic ions**."

→ SMD 的作者自己指出：对**单原子离子（Li⁺ 正是）**，第一溶剂壳的连续介质假设「尤其糟糕」。这句话是本项目 Stage 9（显式微溶剂化验证）最直接的文献依据，也说明 P2/C1 的隐式壳层**不是**「更真实」，只是「同一个固定背景」。
---

### A2. Association entropy — Rebollar-Zepeda, Carreon-Gonzalez, Muñoz-Rugeles & Alvarez-Idaboy, *J. Chem. Theory Comput.* **2026**, 22, 6367–6376, `10.1021/acs.jctc.6c00575`

> 作者名以 PDF 首页为准（reading list 原文只写 "Rebollar-Zepeda et al."，本轮补齐）。

**A2-Q1：为什么 RRHO 的平动/转动熵在 molecularity-changing 过程里不抵消？方向是什么？**

**结论**：因为过程两边的**独立运动物种数变了**（`Δn ≠ 0`）。理想气体的平动熵按物种数线性叠加，缩合把两个独立平动体变成一个 → 熵大幅损失 → 出现**针对缔合物种的人为惩罚**（`ΔG` 被推向正）。这个误差**不来自连续介质项**，而来自把气相 RRHO 热化学修正搬进溶液反应自由能这一步。

原文（摘要，p.6367）：
> "For molecularity-changing processes such as association, clustering, and transition-state formation, the ideal-gas translational and rotational entropy terms do not cancel and can impose an artificial penalty against associated species."

原文（p.6368）：
> "In solution, molecules do not possess the translational freedom assumed in the gas phase. As a result, the RRHO treatment systematically overestimates translational entropy, leading to exaggerated −TΔS° penalties whenever the number of independently translating species decreases (Δn ≠ 0 ...)"

**A2-Q2：量级多大？用什么分解、什么诊断体系？**

**结论**：诊断体系是**液态 CCl₄ 中的 CCl₄ 自缔合**（2 CCl₄ → (CCl₄)₂）——选它的理由是两侧共价连接不变、分子高度对称无氢键、无多种化学上不同的构型，因此只剩「相互作用能 + 热化学修正」两个不确定源。作者把 1 M 溶液相缔合自由能分解为三块：

```
ΔG°_sol = ΔE_elec + ΔΔG°_solv + ΔG°_RRHO,corr
```

Table 1（p.6371，单位 kcal/mol）逐字复现：

| 量 | gas phase | SMD/CCl₄ |
|---|---|---|
| ΔE_elec | −4.86 | −3.93 |
| ΔΔG°_solv | NA | +0.93 |
| ΔG°_assoc, 1 atm | +5.54 | +6.75 |
| ΔG°_RRHO,corr, 1 atm | +10.40 | +9.75 |
| standard-state 1 atm→1 M | −1.90 | −1.90 |
| **ΔG°_assoc, 1 M** | **+3.64** | **+4.85** |
| ΔG°_RRHO,corr, 1 M | +8.53 | +7.82 |

（负号按 Table 1 的排版与上下文还原；抽取文本中 U+2212 已丢失。）作者原话（p.6371）：

> "This provides a direct diagnostic of the inconsistency: the differential continuum solvation term changes the association energy by less than 1 kcal mol−1, whereas the molecularity-dependent RRHO term contributes +9.75 kcal mol−1 at 1 atm Gaussian convention."

即：**电子项是有利的（−3.9 ~ −4.9），连续介质差分项不到 1 kcal/mol，但最终 1 M 缔合自由能仍是正的（+3.6 ~ +4.9）——大头完全来自 +9.75 kcal/mol 的 RRHO 分子数惩罚。**

**A2-Q3：修正方案是什么？**

**结论**：两类「受限（confinement）」修正，都**只改平动熵项**，不改电子能、几何、频率、也不改连续介质溶剂化项：

- **Martin–Pratt 密度标定**：把 1 M 标准浓度换成液体的**真实分子数密度** `ΔG_1M^MP = ΔG_gas + RT ln(C_liq / 1M)`；对 n 个单体的缔合 `ΔG_1M^MP = ΔG_gas + (n−1) RT ln(C_liq/1M)`。
- **Benson 自由体积**：用有效自由体积估计平动熵，`ΔG_sol^Benson = ΔG_gas + RT ln( (2e)/(n) )`（双分子 n=2）；原文：**在 298.15 K，Benson 修正把双分子缔合的自由能降低 2.55 kcal/mol**。

原文（p.6372）：
> "Both corrections reduce the ideal-gas molecularity penalty, but Benson generally gives a larger correction because the free volume accessible to molecular translation is smaller than the total molar volume of the liquid."

**A2-Q4：对 `Li⁺ + M → [LiM]⁺` 意味着什么？**

**结论（本轮最重要的方法学收获）**：本项目**主结论用的不是绝对缔合自由能，而是相对 ligand-exchange 量**

```
ΔΔG_bind(M; R) = [G([LiM]⁺) + G(R)] − [G([LiR]⁺) + G(M)]
```

它的**两侧各有两个独立物种**（`Δn_molecularity = 0`），因此 A2 指认的那个「每个缔合事件 RT·ln(…) 量级」的**分子数惩罚在差分中严格抵消**，Benson/Martin–Pratt 修正对它的净影响是高阶小量。这从热力学上**独立佐证了 `config/scientific_definitions.yaml` 里「优先使用相对 ligand-exchange quantity、禁止把绝对 dG_bind 当核心量」这条冻结规则的正确性**——而不是仅仅为了「省事」。

反过来，这也给出一条**必须写进报告的限制**：本项目**不得**把 `G([LiM]⁺) − G(M)` 这类绝对缔合自由能当作可引用数字，因为它包含一个约 **+8 ~ +10 kcal/mol（1 M）** 的、纯粹来自气相机理的伪惩罚。`outputs/week5/c1_ligand_exchange.csv` 里的 `g_liM_cation_eh` / `g_lir_cation_eh` 只是原始电子能，不是结合自由能（`docs/12` §3 已如此声明，此处给出文献依据）。

**A2 的边界**：
- 作者针对的是**溶液相反应自由能的工作流**，不是单物种 `ΔG*_solv`；本文明确说连续介质模型「常常能准确复现标准溶剂化自由能」，问题出在**组合方式**（p.6367）。
- 本文**没有**给出 Li⁺ 具体体系的数字；CCl₄、水、氯仿只是诊断案例。
- 本文**没有**处理多个化学上不同微态（conformer）的构型熵——它特意选了「无构型歧义」的 CCl₄（p.6370）。因此它**不能**替代 B2/CREST 那一层的构象系综问题。

---

### A3. qRRHO — Grimme, *Chem. Eur. J.* **2012**, 18, 9955–9964, `10.1002/chem.201200497`

**A3-Q1：qRRHO 用什么替换低频振动模式？关键公式与参数？**

**结论**：把**低于 ω₀ 的简正模式**的谐振子振动熵，用**同一个频率对应的自由转子熵**连续地替代。四个式子（p.9957–9958，Eq. 3–8）：

- 谐振子熵（Eq. 3）：`S_V = R[ (ħω/kT)/(e^{ħω/kT} − 1) − ln(1 − e^{−ħω/kT}) ]`；作者指出 **ω→0 时第一项发散**，所以必须替换。
- 由频率构造等效转动惯量（Eq. 4）：`μ = h / (8π²ω)`
- 用平均分子转动惯量 `B_av` 截断（Eq. 5）：`μ' = μ·B_av/(μ + B_av)`
- 自由转子熵（Eq. 6）：`S_R = R[ 1/2 + ln( (8π³μ'kT/h²)^{1/2} ) ]`
- 连续插值（Eq. 7）：`S = w(ω)·S_V + (1 − w(ω))·S_R`
- Head-Gordon 阻尼（Eq. 8）：`w(ω) = 1 / (1 + (ω₀/ω)^α)`，**α = 4**

**默认参数**：`ω₀ = 100 cm⁻¹`（「about 1/2 kT at room temperature」）、`B_av = 10⁻⁴⁴ kg·m²`。原文（p.9958）：

> "Equation (7) then effectively replaces the vibrational entropy for all modes with frequencies <100 cm⁻¹ by a corresponding free-rotor entropy."

**A3-Q2：它为什么能修正柔性分子/弱相互作用的结合自由能？**

**结论**：因为柔性配体（glyme、磷酸酯）和弱相互作用复合物的**最低几个简正模式本质上是受阻平动/转动**，其真实熵介于「谐振子（会发散/被严重低估）」与「自由转子（上界）」之间；qRRHO 用一个物理上有界的插值把这个区间补齐，并且**对频率数值噪声免疫**。作者强调 ω₀ 在 **50–150 cm⁻¹** 内结果不敏感（p.9958）：

> "In the Supporting Information it is shown that the computed entropies are only weakly dependent on the value of w0 if chosen within reasonable limits (50–150 cm−1)."（ω₀ 原文字符丢失，据上下文还原）

**A3-Q3：修正的量级与体系？**

p.9958：
> "the differences between the results from Equations (3) and (7) for bimolecular reaction (association) entropies for molecules with only about 100 atoms already is often 1–2 kcalmol−1. Test calculations on model systems with 300–400 atoms have shown that the errors from Equation (3) can easily reach 3–4 kcalmol−1, because very small ω values on the order of 5–10 cm−1 are quite common in such systems."

即：**~100 原子的双分子缔合熵差 1–2 kcal/mol；300–400 原子可到 3–4 kcal/mol**。文中用它计算了一系列超分子结合热力学（如 host–guest、分子间复合物），并配合色散校正泛函（TPSS-D3 等）与 def2-QZVP' 基组。

**A3 的边界**：
- qRRHO 修的是**分子内/分子间熵**，**不修** A2 的分子数惩罚平动熵（两者是不同层级的问题；A2 用受限平动熵修正，A3 用自由转子替换低频振动熵）。
- 论文的主体是**气相**超分子结合热力学；它不讨论 SMD 连续介质如何与之组合（连续介质组合是 A2 的议题）。
- 它**不给**「本项目该不该对 Li⁺ 配位复合物做 qRRHO」的结论——需要我们自己判断（见 §4 影响清单）。
---

## 2. B 支：构象与配位构型

### B1. GFN2-xTB — Bannwarth, Ehlert & Grimme, *J. Chem. Theory Comput.* **2019**, 15, 1652–1671, `10.1021/acs.jctc.8b01176`

**B1-Q1：GFN2-xTB 相对 GFN1-xTB（GFN-xTB）的关键物理改进？**

**结论**：两条核心新物理，都不增加明显计算量：

1. **各向异性二阶密度涨落 / 累积原子多极矩的短程阻尼相互作用** —— 用密度涨落的一阶/二阶项给出多极静电，因此**不再需要任何经典的卤键/氢键修正项**，且收敛到「只依赖全局 + 元素特异性参数」。
2. **原子部分电荷依赖的 D4 London 色散模型自洽地并入**（在紧束缚图像里由二阶密度涨落自然得到）。

原文（摘要，p.1652）：
> "The essential novelty in this so-called GFN2-xTB method is the inclusion of anisotropic second order density fluctuation effects via short-range damped interactions of cumulative atomic multipole moments. Without noticeable increase in the computational demands, this results in a less empirical and overall more physically sound method, which does not require any classical halogen or hydrogen bonding corrections and which relies solely on global and element-specific parameters (available up to radon, Z = 86). Moreover, the atomic partial charge dependent D4 London dispersion model is incorporated self-consistently ..."

**B1-Q2：精度量级？**

- **几何（ROT34，平衡转动常数 B_e 的相对误差）**：GFN2-xTB **MRD = 0.78%，SRD = 1.24%**；对比 GFN-xTB（0.52%/1.10%）、DFTB-D3(BJ)（−1.26%/1.28%）、PM6-D3H4X（−1.60%/2.50%）（Fig. 2 图注，p.1661）。**几何上 GFN2-xTB 略逊于其前身**，作者归因于拟合时几何权重较小。
- **键长（LB12 / HMGB11）**：GFN2-xTB 明显优于 PM6-D3H4X，且在 LB12 上「particularly well」（p.1661）。
- **非共价相互作用能（GMTKN55 子集）：`|MD| < 1 kcal/mol`**（p.1661 附近）；PM6-D3H4X 在 HAL59 上有 7 个体系误差 >10 kcal/mol。
- **适用规模**：设计目标是**约 1000 原子**（摘要 p.1652）。

**B1-Q3：文中明说哪些场景不该用 / 不保证可靠？**

**结论**：文中最醒目的一条限制**恰好命中我们 C1 的阳离子态**——强净电荷 + 截断的高阶多极展开会失效。原文（p.1661）：

> "there exists one outlier in the LB12 set for GFN2-xTB (385 pm instead of 286 pm for the S8 2+ system), which is excluded in the statistical analysis. Presumably, this overestimated bond length is caused by the strong net charge of the system in combination with the higher order but truncated multipole expansion"

（`S8 2+` 即 S₈²⁺，净电荷 +2；符号按上下文还原。）

→ 对本项目的直接含义：**GFN2-xTB 被用来做 [Li M]⁺（净电荷 +1）与 [Li(M)₂]⁺ 的预优化是合适的**（摘要明确把 "conformational space exploration" 与 "geometry preoptimization" 列为主用途，且我们从不把它当能量参考）；但**绝不能**把 GFN2-xTB 用在净电荷 +2 的 dication 态上做定量结论——这正是本项目把 dication/reduced 的**能量**全部交给 r2SCAN-3c 的原因。

**B1-Q4：对氧化还原能 / 电子亲和有讨论吗？**

**结论**：**没有**。全文 `redox` 出现 0 次、`electron affinity` 出现 0 次；`ionization` 的 2 次命中全部落在参考文献题名里（如 "Molecular Orbital Theory of Chemical Valency. VIII. A Method of Calculating Ionization Potentials"），不是方法学讨论。因此 B1 **不能**被引用来支持「xTB 可以算 redox」；它只支持「xTB 适合构象搜索、几何预优化、廉价描述符」。

**B1 的边界**：它是方法论文，不含电池电解液体系；不含溶液相/电位标度；作者自陈其目标是非共价相互作用能与结构，**不是**电化学性质。

---

### B2. CREST — Pracht, Grimme, Bannwarth et al., *J. Chem. Phys.* **2024**, 160, 114110, `10.1063/5.0197592`

**B2-Q1：CREST 的算法骨架与主要采样方法？**

**结论**：CREST 是「分子化学空间探索」的驱动器，核心流程是 **iMTD-GC**（iterative Metadynamics + Genetic Crossing）。原文（摘要，p.114110）：

> "It offers a variety of molecular- and metadynamics simulations, geometry optimization, and molecular structure analysis capabilities. Implemented algorithms include automated procedures for conformational sampling, explicit solvation studies, the calculation of absolute molecular entropy, and the identification of molecular protonation and deprotonation sites. ... CREST is designed to require minimal user input and comes with an implementation of the GFNn-xTB Hamiltonians and the GFN-FF force-field."

iMTD-GC 的定义（正文）：
> "The combined workflow is hence abbreviated as the iterative metadynamics-genetic crossing (iMTD-GC) method, which was designed to both reliably reproduce the global minimum of drug-like molecules and to provide good ensemble coverage as measured by an ensemble entropy"

代价：单分子 iMTD-GC 的能量+梯度评估量级为 **O(10⁵)**。

**B2-Q2：`single minimum` vs `ensemble`：CREST 如何给构象系综与权重？**

**结论**：CREST 输出的是一个**去冗余后的 CRE（Conformer–Rotamer Ensemble）**，排序由 **CREGEN**（Conformer–Rotamer Ensemble GENeration）完成。判定三准则**顺序执行**：① 能量差 ΔE 对阈值 E_thr；② 转动常数差 |ΔB_e| 对 B_thr；③ 笛卡尔 RMSD 对 R_thr（四元数算法）。只有**超过 RMSD 阈值**的结构才保留为真正的构象；否则归为 rotamer 或重复。

**CREGEN 默认阈值（Table II，p.114114）**：

| 参数 | 默认值 |
|---|---|
| E_win（能量窗口） | **6.0 kcal mol⁻¹** |
| E_thr（去重能量差） | 0.05 kcal mol⁻¹ |
| B_thr（转动常数差） | 1.0%–2.5%（随体系各向异性自适应） |
| R_thr（笛卡尔 RMSD） | **0.125 Å** |

**B2-Q3：局限——什么时候会漏构象？**

原文（p.114114）：
> "Notably, the threshold-based numerical construction of the algorithm may lead to false-positive identification of true conformers as rotamers or vice versa. This problem occurs more frequently with increasing system size (Nat), which can only partially be compensated by an adjustment of {Ethr, Rthr, Bthr}."

即：**体系越大，阈值型判据越容易把真构象误判成 rotamer（或反之）**；作者指出严格做法需要置换不变比较（Hungarian / SOAP kernel），但 CREST **当前没有实现**，只能靠调阈值缓解。

**B2 的边界（对本项目是硬信息）**：
- 本项目**没有安装 CREST**（`scripts/check_environment.py`：`crest MISSING`）。T6（`scripts/build_conformers.py` / `run_t6_conformer_spread.py`）走的是 **RDKit 嵌入 + GFN2-xTB 优化**的构象系综，**不是 CREST 的 iMTD-GC**。
- 因此 `outputs/week6/t6_conformer_spread.*` 的「构象散布 σ_conf」**不能**被表述为「CREST 系综」，只能表述为「ETKDG 嵌入 + xTB 优化的有限构象采样」。这是一条**必须保留的措辞纪律**。
- 本轮的 T10 显式壳层**同样不是 CREST 采样**：它是一个**规则化的刚体放置 + xTB 预优化**（见 `docs/18_week8_report.md`），因为我们只需要「同一化学计量的少数局域 cluster」做 targeted check（v2 §17.1），不做全域构象搜索。
---

## 3. C 支：真实 electrolyte speciation / 界面

### C1. Electrolyte MD 综述 — Yao, Chen, Fu & Zhang, *Chem. Rev.* **2022**, 122, 10970–11021, `10.1021/acs.chemrev.1c00904`

**C1-Q1：CMD / AIMD / MLMD 三类的分工、尺度与精度边界？**

**结论**：按「力从哪来」分类——CMD 用经典势函数，AIMD 从头算求力，MLMD 用机器学习势（MLP）。原文（p.10975 附近）：

> "MD simulations mainly can be classified into CMD, AIMD, and MLMD according to the way of dealing with atomic interaction forces. CMD adopts classical potential energy functions with specific mathematical forms to describe atomic interactions, whereas AIMD calculates the interaction forces by ab initio methods."

- **时间/空间尺度**：综述把 MD 的**界面反应**探查能力总结为「**from femtosecond to nanosecond and from picometer to nanometer**」（p.11013 附近）。**AIMD 的盒子尺寸与模拟时间非常受限**，这是它观察完整界面反应的瓶颈：
  > "The box size and simulation time are very limited for AIMD simulations to observe complete interfacial reactions due to their high computation expense."
- **能/不能**：AIMD 天然包含**电荷转移**与极化，因此能描述**断键/成键**：
  > "The charge transfer, which allows for the bond breaking and bond forming, and the polarization effects are directly incorporated in AIMD. Such first-principles calculations eliminate negative effects brought by empirical force fields. However, inheriting shortcomings of first-principles calculations, AIMD produces high-accuracy results [at high cost]"
- **MLMD 的定位**：作者把 MLMD 当作突破 CMD 精度与 AIMD 成本两边限制的路线：
  > "Therefore, MLMD simulations are strongly supposed to break through the limitations of both CMD and AIMD simulations and achieve wide applications in the study of rechargeable battery electrolytes."

**C1-Q2：经典力场对 Li⁺–溶剂/阴离子的已知问题？**

**结论**：分两类。(a) **通用力场**（UFF 一类）对材料性质预测不佳；(b) **凝聚相专用力场**（OPLS、CHARMM、AMBER、GAFF、COMPASS）精度更高但覆盖面有限；离子液体/电解液常用 **CL&P**（沿用 OPLS 函数形式、但电荷与柔性另行参数化）。**极化**需要专门的**可极化力场**（APPLE&P、AMOEBA）。综述把「力场与原子电荷模型的发展」列为**第一条挑战**（p.11017 附近）：

> "While CMD is superior to AIMD in terms of simulation efficiency, CMD simulation results are highly dependent on the force field adopted. Although various force fields have been proposed and widely applied in electrolyte studies, a universal and highly accurate force field applicable to all electrolyte systems is very lacking"

**C1-Q3：综述从 MD 提取哪些配位结构量？**

RDF（径向分布函数）与配位数是主分析量；综述第 3 节标题即为 "Unveiling the electrolyte structures including bulk and interfacial structures through radial distribution fun[ctions]"。（**注**：本文抽取文本中 `RDF` 词频很低，说明综述正文主要写全称 "radial distribution function"；本轮**未能**在抽取文本中定位到一个把 CIP/SSIP/AGG 写成显式操作定义（距离判据）的句子 → 该项由 **C2** 承担，见下。）

**C1 的边界**：它是**综述**，不含作者自己的新计算；不提供可直接引用的 Li⁺-specific 判据数值；不讨论 ranking / ML 筛选。

---

### C2. Solvation structure & interfaces — Cheng, Sun, Li et al., *ACS Energy Lett.* **2022**, 7, 490–513, `10.1021/acsenergylett.1c02425`

**C2-Q1：溶剂化结构的定量描述量有哪些？**

**结论**：综述开篇即把「**定量分析溶剂化结构与动态去溶剂化过程**」列为第一个待解决问题，并列出基本参数：**配位数（coordination number）、键长、键角**，以及**相邻溶剂化结构之间的长程溶剂–溶剂/溶剂–阴离子相互作用**。原文（p.490 附近）：

> "(i) Analyzing quantitatively the solvation structure and the dynamic desolvation process. The basic parameters of a single solvation structure (e.g., coordination number, bond length, angle, etc.) and the interactions between the neighboring solvation structures (e.g., long-range solvent−solvent and solvent−anion interactions) need to be characterized since they can shape the electrolyte's properties."

**关于 SSIP/CIP/AGG 的操作定义**：本轮**未能**从 C2 抽取文本中确认一组写成「Li–O 距离 < X Å 记为 CIP」式的显式距离判据——文中 `SSIP` 出现 0 次、`CIP` 1 次、`AGG` 3 次，且这几次命中都不是定义句。**因此本节明确声明：本代理不能用 C2 支撑任何具体的 CIP/SSIP/AGG 数值判据。** 这是一条**证据缺口**，不是「综述没说」——它很可能写在综述的图表或其引用文献里，需要回看 PDF 图注（下一轮可做）。

**C2-Q2：Li⁺–溶剂–阴离子竞争如何影响配位？**

综述把电解质设计范式从「SEI 工程」转向「**溶剂化结构 + Li⁺ 去溶剂化过程**」：原文（摘要，p.490）：

> "the metal-ion solvation structure (e.g., Li+) in electrolytes and the derived interfacial model (i.e., the desolvation process) can affect the electrode's performance significantly"

具体机制案例（p.501 附近）：添加剂（BTFE、VC）可以**进入聚集体（AGG）的溶剂化壳层**、把 TMP 挤出第一溶剂壳，从而调节 Na⁺ 与 TFSI⁻ 的溶剂化平衡。

**C2-Q3：界面 vs bulk 的差异？**

综述强调电极界面上存在一个**「界面模型」**，其核心过程是 **desolvation（去溶剂化）**；文中明确把「溶剂化结构」与「界面模型」当作**两个不同的对象**来构造（这是 reading list 里 `p(C|bulk) ≠ p(C|interface)` 的定性版本）。同时它承认旧的「SEI/电极是刚性固/固界面」观点在**液相体系里缺乏可迁移的科学关联**（p.490）：

> "the SEI/electrode is more like a stiff "solid/solid" interface that lacks scientific correlations in liquid systems"

**C2-Q4：把溶剂化结构量与电池性能定量联系的具体例子？**

- **去溶剂化能与电位的关系**：在 DEGDME 基体系里，加入 DOL 后 Na⁺ 去溶剂化能从 **2.45 eV（0.94 M NaPF₆/DEGDME）降到 2.29 eV（3.04 M NaPF₆/DEGDME+DOL 10:1）**，作者认为这有利于分步溶剂解离、抑制溶剂共嵌入（p.501 附近）。
- **Li⁺–溶剂结合能 ↔ 枝晶**：EMC 体系中 Li⁺–EMC 结合能高 → 去溶剂化困难 → 极化升高 → 石墨负极析锂；MA 体系中 Li⁺–MA 去溶剂化能低 → 可以镀锂，但靠近负极的 MA 容易与金属锂反应（p.501 附近）。
- **添加剂的协同**：BTFE + VC 依次调节 Na⁺ 溶剂化结构，给出 **99.6% 容量保持（100 圈）**（p.501 附近）。

**C2 的边界**：综述，无自算；给出的数字来自被引文献（抽自图注与正文转述）；**不涉及氧化还原电位/ranking**。

---

## 4. 对本项目的方法学含义（逐条给「需改 / 需加限定 / 无需改」）

| # | 来源 | 现有做法 | 判定 | 理由与动作 |
|---|---|---|---|---|
| I1 | A1 | P2 层用 SMD(乙腈) 作固定背景 | **需加限定**（已在 `docs/10` 有类似说明，本轮补文献依据） | SMD 的 G_CDS 吞并了体相静电模型的全部偏差、且**显式不含氢键项**；作者自陈对**单原子离子**第一壳假设「尤其糟糕」。因此 P2 的结论只能表述为「同一固定连续背景下的敏感度」，不能表述为「更接近真实溶剂」。 |
| I2 | A1 | 用 `ε` 扫描（T3, ε=5/10/20/40）区分 fixed-solvent vs dielectric-only | **无需改**，**加强** | A1 说明「bulk electrostatics 与 non-bulk 的划分不是热力学唯一（只有和是态函数）」。这正好支持 v2 §8.3 把两类 sensitivity test **分开**而不是混为一个「溶剂效应」。 |
| I3 | A2 | 主结论用相对 ligand-exchange `ΔΔG_bind` | **无需改，且获得独立热力学依据** | A2 的分子数惩罚 (+9.75 kcal/mol @1 atm) 在「两侧物种数相同」的交换量中严格抵消；而绝对 `G[LiM]⁺ − G(M)` 含该伪惩罚，**禁止**作为可引用数字。 |
| I4 | A2 | `docs/12` §3 已声明 `g_liM_cation_eh` 只是电子能、不是结合自由能 | **无需改**，补文献锚点 | 现在可引 A2 Table 1 作为该声明的定量依据。 |
| I5 | A3 | C1/Stage 9 全部走 **电子能 + 垂直**量，**不做** ZPE/热修正 | **无需改，但须显式声明** | qRRHO 与 RRHO 的差异（1–4 kcal/mol）**只有在做热修正时才出现**。本项目冻结为「0 K 电子能 + 垂直 gap」口径，因此**结构性免疫**于该误差，但必须在报告里说明「不是因为我们处理得更对，而是因为我们不做热修正」。 |
| I6 | B1 | GFN2-xTB 只做预优化，r2SCAN-3c 出能量 | **无需改，且被文献佐证** | B1 把「构象空间探索 / 几何预优化」列为设计用途；同时明说**强净电荷 + 截断多极展开**是已知失弱点（S₈²⁺ 键长 385 vs 286 pm）→ 我们**不得**用 xTB 给 dication(+2) 出定量数字，这一点现有流程已满足。 |
| I7 | B2 | T6 构象系综走 RDKit ETKDG + xTB，**非 CREST** | **需加限定**（措辞纪律） | 环境里 `crest MISSING`。所有涉及 T6 的表述必须写「ETKDG 嵌入 + xTB 优化的有限构象采样」，**禁止**写「CREST 系综 / iMTD-GC」。 |
| I8 | B2 | Stage 9 显式壳层的构型生成 | **需加限定** | 我们用「规则化刚体放置 + xTB 预优化」，**不是** iMTD-GC；CREGEN 的 E_win=6.0 kcal/mol、R_thr=0.125 Å 只能作为**参照**说明我们没做全域搜索。 |
| I9 | C1 | 本项目不做 MD | **无需改** | C1 明确：`p(C)` 需要 MD（fs–ns、pm–nm），本项目的 C1 是**条件态（conditional state）**，v2 §16.1 已严格区分。但报告需重申「C1 ≠ real speciation」。 |
| I10 | C2 | 项目不做界面/去溶剂化 | **无需改**，强化 framing | C2 把「界面溶剂化模型」与「bulk 溶剂化结构」当作不同对象；支持 v2 §16.2「真实体系需要 population」「p(C|bulk) ≠ p(C|interface)」。 |
| I11 | A1+C1+C2 | 项目结论的**声称边界** | **需加限定**（写作纪律） | 三篇合起来排除了「molecular redox proxy = 真实电化学窗口」的任何表述。允许的最强表述是 v2 §4.2 的 **conditional-species one-electron redox thermodynamic proxy**。 |
---

## 5. 未提供的分支（本代理**没有**作答）

按 `核心文件/文献/分支a-d/` 的实际内容，以下 reading list 条目**没有 PDF**，本文不作答，也不从二手来源杜撰：

| 条目 | 文献 | 状态 |
|---|---|---|
| C3 | JACS 2023, `10.1021/jacs.2c11807`（EDL/speciation） | **无 PDF** |
| D1 | Rasmussen & Williams, *Gaussian Processes for Machine Learning* | **无 PDF**（教材） |
| D2 | Settles, *Active Learning Literature Survey* (2009) | **无 PDF** |
| D3 | Peherstorfer, Willcox & Gunzburger, *SIAM Review* 2018, `10.1137/16M1082469` | **无 PDF** |
| E | Efron & Tibshirani, *An Introduction to the Bootstrap* | **无 PDF**（教材） |

其中 **D3（multi-fidelity）** 与本项目直接相关：reading list 自己已指出 `P(M) → P([LiM]⁺)` 严格说更适合称为 **environment perturbation** 而不是数值 fidelity correction——这一点在本项目的 Week 7 `Δ`-learning 结论里已经**用实验方式**验证（`outputs/week7/stage7_ml_summary.md`：LOFO 下 Δ-learning 在 8 个组合里赢 6 个，而唯一反转出现在还原轴），但我们**没有** D3 原文，因此**不**在报告里引用其形式命题 `P_H(x) = P_L(x) + Δ(x)` 作为文献依据。

---

## 6. 定量事实表（仅列本文逐字核到页码的数字）

| # | 来源 | 事实 | 数值 | 页码 |
|---|---|---|---|---|
| F1 | A1 | SMD 溶剂描述符数量与种类 | ε, n, Abraham α, Abraham β, 体相表面张力 ψ²（5 类） | 6378 |
| F2 | A1 | SMD 中性溶质 MUE | 0.5–0.8 kcal/mol | 6379 |
| F3 | A1 | SMD/离子 MUE | 2–7 kcal/mol | 6379 |
| F4 | A1 | SMD 训练数据 | 2346 条（90 溶剂+水）+143 转移能 +112 聚簇离子 +220 未聚簇离子 | 6392–6393 |
| F5 | A1 | 参数优化覆盖的电子结构方法数 | 6 | 6380 / 6392 |
| F6 | A2 | CCl₄ 二聚 ΔE_elec（气相 / SMD） | −4.86 / −3.93 kcal/mol | 6371 |
| F7 | A2 | CCl₄ 二聚 ΔΔG°_solv | +0.93 kcal/mol | 6371 |
| F8 | A2 | CCl₄ 二聚 ΔG°_RRHO,corr | +10.40（气相）/ +9.75（SMD），1 atm | 6371 |
| F9 | A2 | 1 atm→1 M 标准态换算 | −1.90 kcal/mol（双分子，298.15 K） | 6371 |
| F10 | A2 | CCl₄ 二聚 ΔG°_assoc（1 M） | +3.64（气相）/ +4.85（SMD）kcal/mol | 6371 |
| F11 | A2 | Benson 修正对双分子缔合的降低量 | 2.55 kcal/mol（298.15 K） | 6372 |
| F12 | A3 | qRRHO 默认 ω₀ | 100 cm⁻¹ | 9958 |
| F13 | A3 | qRRHO 阻尼指数 α | 4 | 9957 |
| F14 | A3 | qRRHO 平均转动惯量 B_av | 10⁻⁴⁴ kg·m² | 9958 |
| F15 | A3 | ω₀ 不敏感区间 | 50–150 cm⁻¹ | 9958 |
| F16 | A3 | Eq.(3) vs Eq.(7) 的双分子缔合熵差 | ~100 原子：1–2 kcal/mol；300–400 原子：3–4 kcal/mol | 9958 |
| F17 | B1 | GFN2-xTB ROT34 结构精度 | MRD 0.78%，SRD 1.24% | 1661 |
| F18 | B1 | GFN2-xTB 非共价相互作用能 | \|MD\| < 1 kcal/mol（GMTKN55 子集） | 1661 |
| F19 | B1 | GFN2-xTB 目标规模 | ~1000 原子 | 1652 |
| F20 | B1 | 已知失弱点 | 强净电荷 + 截断多极：S₈²⁺ 键长 385 vs 286 pm | 1661 |
| F21 | B2 | CREGEN 默认 E_win | 6.0 kcal mol⁻¹ | 114114 |
| F22 | B2 | CREGEN 默认 R_thr | 0.125 Å | 114114 |
| F23 | B2 | CREGEN 默认 E_thr / B_thr | 0.05 kcal mol⁻¹ / 1.0–2.5% | 114114 |
| F24 | B2 | iMTD-GC 单分子评估量级 | O(10⁵) 次能量+梯度 | 正文（iMTD-GC 章节） |
| F25 | C1 | MD 探查界面反应的时空尺度 | fs–ns，pm–nm | ~11013 |
| F26 | C1 | AIMD 瓶颈 | 盒子尺寸与模拟时长受限 | AIMD 章节 |
| F27 | C2 | Na⁺ 去溶剂化能（DEGDME / +DOL） | 2.45 eV → 2.29 eV | ~501 |
| F28 | C2 | BTFE+VC 调溶剂化后的容量保持 | 99.6%（100 圈） | ~501 |

（负号与不等号按 Table 1 / 图注排版还原；抽取文本中 U+2212 与 `<` 已损坏。）

---

## 7. 证据缺口（明确列出，不掩盖）

1. **CIP/SSIP/AGG 的显式距离判据**：C2 抽取文本中 `SSIP` 0 次、无定义句。需要下一轮回看 PDF 图注或其被引文献才能给出「Li–O < X Å」式的操作定义。**本轮不提供任何具体判据数值。**
2. **B2 的构象「找回率」基准**：本轮未能从抽取文本中定位到量化的找回率表格，因此未列具体百分比。
3. **C1 的具体 RDF 截断/配位数积分上限**：未能定位到统一数值。
4. **A2 的水/氯仿团簇累积表**：Table 1 只完整核到 CCl₄ 行；团簇行未逐条核。
5. **A3 的具体超分子体系与误差改善幅度**：正文有体系描述但抽取值不完整，未列数字。

以上 5 条如需补齐，应回到 PDF 原图（非文本层）核对，属于下一轮工作。

---

## 8. 对 reading list 的勘误（承接 `docs/14` §5）

1. **A2 的作者名**：reading list 只写 "Rebollar-Zepeda et al."；PDF 首页完整为 *Aida Rebollar-Zepeda, Mirzam Carreon-Gonzalez, Leonardo Muñoz-Rugeles, Juan Raúl Alvarez-Idaboy*。建议回改。
2. **A2 的年份**：reading list 写 "JCTC 2026"，卷页为 **22, 6367−6376**（Published June 30, 2026）。与 `docs/14` 中「真实 2026 新文」的判断一致，现已由 PDF 首页证实。
3. **「分支a-d」≠ 四个分支齐全**：目录实际只有 A/B/C 三支 7 篇，缺 C3 与整个 D 支、E 支。建议 reading list 或目录命名回改，避免「a-d 已全部读完」的误读。