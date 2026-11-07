# Project Reading List
## 电解液 ranking 项目：Minimal + In-depth 两级阅读清单

**对应项目：** `ranking-electrolyte-materials-v2.md`

这份阅读清单按两层组织：

- **Part I — Minimal：必须读。** 目标不是系统掌握电化学、电解液和机器学习，而是在约 1–2 周内建立足以开始项目的概念框架。
- **Part II — In-depth：按需深入。** 只有当项目实际进入相应问题时再读，不要求在开工前完成。

本项目最重要的不是记住大量文献，而是始终能回答四个问题：

$$
\boxed{\text{我们计算的对象是什么？}}
$$

$$
\boxed{\text{这个量如何定义？}}
$$

$$
\boxed{\text{增加的新物理是否真的改变候选排序？}}
$$

$$
\boxed{\text{这种排序变化是否大于计算不确定性？}}
$$

# Part I. Minimal reading：开工前必须读的 7 项

## M1. 电化学与 redox potential：只建立最基本概念

### Bard, Faulkner & White, *Electrochemical Methods*, 3rd ed.

**不用通读。**

只需要理解：

- chemical potential；
- electrochemical potential；
- Nernst equation；
- electrode potential；
- reference electrode；
- equilibrium potential 与 kinetic onset 的区别。

读完后应理解：

$$
\Delta G=-nFE
$$

背后的物理意义，而不是只会套公式。

### 本项目要解决的问题

为什么“分子氧化/还原自由能”与“电池中真实分解电位”有关，但二者并不完全相同？

---

## M2. HOMO/LUMO 不是 electrochemical window

### Peljo & Girault, 2018

*Electrochemical potential window of battery electrolytes: the HOMO–LUMO misconception*

**Energy & Environmental Science**  
DOI: `10.1039/C8EE01286E`

这篇很短，建议全文读完。

核心只需真正理解一句话：

$$
\boxed{
\text{HOMO/LUMO energy}
\neq
\text{redox free energy}
}
$$

因为真正的 redox quantity 涉及：

- 不同电荷态总能；
- 结构弛豫；
- 溶剂化；
- 温度与自由能；
- reference electrode。

### 本项目要解决的问题

为什么 HOMO/LUMO 可以作为 cheap proxy，却不能直接被称为真实氧化/还原电位？

---

## M3. 计算 redox potential 的标准框架

### Marenich et al., 2014

*Computational electrochemistry: prediction of liquid-phase reduction potentials*

**PCCP**  
DOI: `10.1039/C4CP01572J`

不用逐页精读。重点看：

1. thermodynamic cycle；
2. gas-phase 与 solution-phase redox；
3. vertical vs adiabatic；
4. implicit solvent；
5. reference electrode。

需要理解以下结构：

$$
G_{\mathrm{solution}}
\approx
E_{\mathrm{electronic}}
+
G_{\mathrm{thermal}}
+
\Delta G_{\mathrm{solv}}.
$$

### 本项目要解决的问题

我们为什么不能只比较两个分子的 DFT orbital energies，而必须考虑不同电荷态的自由能？

---

## M4. Li$^+$ coordination 为什么是“另一种状态”，而不是简单的高精度版本

### Itkis et al., 2021

*Ambiguities in solvation free energies from cluster-continuum quasichemical theory: lithium cation in protic and aprotic solvents*

**PCCP**  
DOI: `10.1039/D1CP01454D`

这篇不要求掌握全部 quasichemical theory。

重点理解：

- Li$^+$ 有明确的第一配位壳；
- coordination number 会变化；
- cluster 大小会影响结果；
- continuum boundary 会影响结果；
- 单离子绝对 solvation free energy 不像普通中性分子那么简单。

关键概念：

$$
M
\qquad\text{和}\qquad
[\mathrm{Li}M]^+
$$

是两个不同的 conditional chemical states。

因此：

$$
P(M)
\rightarrow
P([\mathrm{Li}M]^+)
$$

不应该被机械描述成“low fidelity → high fidelity”。

### 本项目要解决的问题

为什么我们研究的是 **Li$^+$ coordination-induced rank shift**，而不是简单地说“加 Li$^+$ 后结果更真实”？

---

## M5. 真实电解液稳定性为什么比单分子模型复杂

### Borodin, 2019

*Challenges with prediction of battery electrolyte electrochemical stability window and guiding the electrode–electrolyte stabilization*

**Current Opinion in Electrochemistry**  
DOI: `10.1016/j.coelec.2018.10.015`

重点只读概念：

- salt concentration；
- ion aggregation；
- electrode interface；
- bond breaking；
- proton/H transfer；
- SEI/CEI；
- kinetic stabilization。

需要形成下面的层级概念：

$$
\text{molecular proxy}
<
\text{solution redox thermodynamics}
<
\text{coordination/speciation}
<
\text{real interfacial reactivity}.
$$

这里的“$<$”表示加入更多物理信息，**不表示准确度一定单调提高**。

### 本项目要解决的问题

为什么本项目应该说：

> molecular redox thermodynamic proxy

而不是：

> true electrochemical stability window？

---

## M6. 看清楚已有工作已经做到哪一步

### Yang et al., 2025

*Unveiling redox potential behavior in electrolytes: A machine learning approach to Li-ion coordination effects*

**Materials Today Energy**  
DOI: `10.1016/j.mtener.2025.102121`

这是本项目最重要的 prior-art 文献之一。

重点看：

- 数据集多大；
- 如何定义 with/without Li$^+$ coordination；
- oxidation/reduction potential 怎么算；
- 用了什么 descriptors；
- ML 如何训练；
- train/test 怎么分；
- 是否研究跨 family 外推；
- 是否研究 ranking inversion；
- 是否考虑 uncertainty。

### 本项目要解决的问题

本项目不能只重复：

> Li$^+$ coordination 会改变 redox potential。

真正要进一步回答：

$$
\boxed{
\text{这种变化什么时候真的改变筛选决策？}
}
$$

以及：

$$
\boxed{
\text{需要多少昂贵计算才能恢复 target ranking？}
}
$$

---

## M7. Ranking：为什么不能只看 MAE

### Husch et al., 2015

*Large-scale virtual high-throughput screening for the identification of new battery electrolyte solvents*

**PCCP**  
DOI: `10.1039/C4CP04338C`

不用研究所有化学细节。

重点注意：

- high-throughput screening；
- Pareto filtering；
- Kendall rank correlation；
- 为什么 screening 关注候选次序，而不只是绝对数值误差。

理解：

$$
\mathrm{MAE}
$$

和

$$
\mathrm{ranking\ quality}
$$

不是一回事。

例如模型 A 的 MAE 更小，但如果候选都非常接近，它仍可能把 Top-10 排错很多。

### 本项目要解决的问题

为什么我们要重点研究：

- Spearman correlation；
- Kendall $\tau$；
- pairwise inversion；
- Top-$k$ overlap；
- selection regret；

而不是只报告 $R^2$ 和 MAE？

# Part I 的最低完成标准

读完以上 7 项后，只要能够清楚回答下面 8 个问题，就可以开始正式计算。

1. 为什么 HOMO/LUMO 不能直接等同于 redox potential？
2. vertical 与 adiabatic IP/EA 有什么区别？
3. 为什么 solution redox 需要 solvation free energy？
4. 为什么 $M$ 与 $[\mathrm{Li}M]^+$ 是不同 chemical states？
5. 为什么 Li$^+$ coordination effect 不是简单的 numerical fidelity correction？
6. 为什么真实 electrochemical window 比 molecular redox quantity 更复杂？
7. 为什么 MAE 小不意味着 screening decision 一定正确？
8. 为什么 random train/test split 可能高估模型的 transferable performance？

如果这 8 个问题能够讲清楚，已经足够进入项目的 Stage 0–3。

# 两周 Minimal 阅读安排

## Week 1：先把物理定义做对

### Day 1–2
Peljo 2018 + Bard 相关基础。

目标：

$$
\text{orbital energy}
\neq
\text{redox free energy}.
$$

### Day 3–4
Marenich 2014。

目标：自己画出 gas → solution 的 thermodynamic cycle。

### Day 5–7
Itkis 2021 + Borodin 2019。

目标：能够解释：

$$
\text{free molecule}
\neq
\text{Li-coordinated state}
\neq
\text{real electrolyte}.
$$

## Week 2：理解项目创新在哪里

### Day 8–10
Yang 2025。

目标：明确已有 Li$^+$-coordination ML 已经做过什么。

### Day 11–12
Husch 2015。

目标：理解 ranking 为什么比单纯 MAE 更接近 screening。

### Day 13–14
结合 `understanding-electrolyte-materials-v2.md` 做一张自己的项目逻辑图：

$$
\text{cheap proxy}
\rightarrow
\text{free molecule}
\rightarrow
\text{solvation}
\rightarrow
\text{Li coordination}
\rightarrow
\text{ranking change}
\rightarrow
\text{decision uncertainty}.
$$

如果能把这张图讲清楚，就可以开工。

# Part II. In-depth reading：遇到具体问题时再读

下面内容不是开工前作业。它们是“问题驱动”的扩展阅读。

# A. 如果 solution thermochemistry 出现问题

## A1. SMD

Marenich, Cramer & Truhlar, 2009  
DOI: `10.1021/jp810292n`

读它是为了理解：

- continuum solvent 到底近似了什么；
- dielectric response 与 cavity/non-electrostatic terms；
- 为什么 SMD 不等于“给 PCM 设置一个 $\epsilon$”。

## A2. Association entropy

Rebollar-Zepeda et al., JCTC 2026  
DOI: `10.1021/acs.jctc.6c00575`

当开始计算

$$
\mathrm{Li}^+ + M
\rightarrow
[\mathrm{Li}M]^+
$$

的 free energy 时再重点读。

需要理解为什么 condensed-phase association 中，传统 gas-phase RRHO translational entropy 可能产生系统误差。

## A3. qRRHO

Grimme, Chem. Eur. J. 2012  
DOI: `10.1002/chem.201200497`

当 glyme、phosphate 等柔性分子的低频振动开始影响 free-energy ranking 时再读。

# B. 如果构象和配位构型成为主要问题

## B1. GFN2-xTB

Bannwarth, Ehlert & Grimme, JCTC 2019  
DOI: `10.1021/acs.jctc.8b01176`

目的是理解为什么 xTB 很适合：

- conformer search；
- geometry preoptimization；
- cheap descriptors；

但不应未经 benchmark 直接作为最终 redox reference。

## B2. CREST

*CREST—A program for the exploration of low-energy molecular chemical space*  
JCP 2024  
DOI: `10.1063/5.0197592`

当项目进入 conformer ensemble 时再读。

核心问题：

$$
\text{single minimum}
\quad\text{vs}\quad
\text{ensemble}.
$$

# C. 如果要进入真实 electrolyte speciation / MD

## C1. Electrolyte MD review

*Applying Classical, Ab Initio, and Machine-Learning Molecular Dynamics Simulations to the Liquid Electrolyte for Rechargeable Batteries*

**Chemical Reviews** 2022  
DOI: `10.1021/acs.chemrev.1c00904`

当项目从

$$
[\mathrm{Li}M]^+
$$

这种单一 conditional state，升级到真实的

$$
p(C)
$$

配位环境分布时再读。

## C2. Solvation structure and interfaces

*Emerging Era of Electrolyte Solvation Structure and Interfacial Model in Batteries*

**ACS Energy Letters** 2022  
DOI: `10.1021/acsenergylett.1c02425`

重点看：

- Li–solvent–anion competition；
- contact ion pair；
- solvent-separated ion pair；
- interface solvation structure。

## C3. EDL/speciation

JACS 2023  
DOI: `10.1021/jacs.2c11807`

当项目开始讨论：

> 哪种 species 在电极附近真正占优势？

再读。

关键关系：

$$
p(C|\mathrm{bulk})
\neq
p(C|\mathrm{interface}).
$$

# D. 如果进入 ML / active learning

本科阶段不必先读完整机器学习教材。

先只掌握三个概念：

1. interpolation 与 extrapolation；
2. uncertainty；
3. acquisition。

## D1. Gaussian Process

Rasmussen & Williams, *Gaussian Processes for Machine Learning*

只读：

- Chapter 2；
- 必要时再读 Chapter 5。

需要理解：

$$
f(x)
\sim
\mathcal{GP}(m,k)
$$

以及为什么 GP 同时输出 prediction 与 uncertainty。

不用推导整本书。

## D2. Active learning

Settles, *Active Learning Literature Survey*, 2009.

重点只看：

- uncertainty sampling；
- diversity sampling；
- pool-based active learning。

本项目需要回答的其实只有：

> 下一笔昂贵 DFT 预算应该花在哪个分子上？

## D3. Multi-fidelity

Peherstorfer, Willcox & Gunzburger, SIAM Review 2018  
DOI: `10.1137/16M1082469`

只在真正进入 multi-fidelity modeling 时读。

最重要的是理解：

$$
P_H(x)=P_L(x)+\Delta(x)
$$

通常要求 $P_H$ 与 $P_L$ 是**同一个 observable 的不同近似**。

因此：

$$
P(M)
\rightarrow
P([\mathrm{Li}M]^+)
$$

严格来说更适合称为 environment perturbation，而不是普通 numerical fidelity correction。

# E. 如果统计 ranking 时出现“很多候选差不多”

这时再补：

### Efron & Tibshirani
*An Introduction to the Bootstrap*

以及任一本非参数统计教材中：

- Spearman；
- Kendall $\tau_b$；
- bootstrap confidence interval。

真正需要建立的是：

$$
|\Delta P_{ij}|
<
\sigma_{ij}
$$

时，不应该强迫判断

$$
i>j
$$

或

$$
j>i.
$$

应该允许：

$$
i\sim j
$$

即 unresolved pair。

只有当两个模型给出的 pair ordering 都显著超出不确定性、且符号相反时，才应称为 **robust ranking inversion**。

# 不建议本科阶段先读的内容

以下内容都重要，但不是这个项目开工的前置条件。

## 1. 完整 SEI/CEI reaction network

知道它们为什么使 molecular redox proxy 不完备即可。

## 2. 大规模 classical MD / AIMD / MLFF

第一阶段不需要。

只有当研究问题从 conditional state 进入真实 speciation population 时再做。

## 3. 深度 GNN / foundation model

当前 60–100 个 paired labels 根本不是主要矛盾。

优先保证：

$$
\text{state definition}
+
\text{thermodynamics}
+
\text{ranking statistics}
$$

是正确的。

## 4. 完整 Marcus electron-transfer theory

当前项目研究 thermodynamic ranking，不是 electron-transfer rate。

知道

$$
\text{thermodynamics}
\neq
\text{kinetics}
$$

即可。

## 5. 完整电池工程文献

倍率、循环寿命、低温性能、安全性等都重要，但不应该在 MVP 阶段把一个清晰的小项目扩展成“研究整个电解液”。

# 推荐给本科生的实际执行方式

最不建议的方式是：

> 先把阅读清单全部读完，再开始计算。

更合理的是：

$$
\boxed{
\text{Minimal reading}
\rightarrow
\text{跑 5–10 个 benchmark molecules}
\rightarrow
\text{遇到具体问题}
\rightarrow
\text{进入对应 In-depth module}
}
$$

例如：

- 阴离子不稳定 → 查 redox / diffuse basis；
- Li binding free energy 很怪 → 查 solution thermochemistry；
- 同一分子有很多构象 → 查 CREST/qRRHO；
- ranking 很不稳定 → 查 uncertainty/rank statistics；
- 想减少高层 DFT 数量 → 再学 GP/active learning。

这样阅读会直接服务于研究问题，而不是变成额外负担。

# 最终 Minimal 清单

如果只打印一页给学生，我建议只留下下面 7 项：

1. **Peljo & Girault 2018** — HOMO/LUMO misconception。
2. **Marenich et al. 2014** — 如何计算 solution redox potential。
3. **Itkis et al. 2021** — Li$^+$ solvation/coordination 为什么复杂。
4. **Borodin 2019** — molecular redox 与真实 electrolyte stability 的边界。
5. **Yang et al. 2025** — Li$^+$ coordination + redox + ML 的直接 prior art。
6. **Husch et al. 2015** — ranking 与 screening。
7. **Bard/Faulkner/White** — 只作为电化学概念查询教材。

真正需要精读的其实只有前六篇论文。

其余文献全部归入：

> **遇到问题时再读。**

对于这个项目，这样已经足够。
