# 参考文献

> 条目顺序与 `references.json` 一致（先 6 篇「新建文件夹」，后 7 篇「分支a-d」）。题名/作者/卷/页取自各 PDF 首页与页脚；未出现在 PDF 中的期号由 Crossref 条目（按 DOI 查询）补齐并在 JSON 中如实记录。

[1] Borodin, O. Curr. Opin. Electrochem. 2019, 13, 86–93.
—— 支撑「电池电解液电化学稳定性窗口的预测方法与局限」，以及「键合到 Li+ 上的阴离子/溶剂数目会改变电解液的还原与氧化稳定性」这一核心命题（该文用代表性电解液团簇与电极表面反应的量子化学计算给出分子尺度证据）。

[2] Yang, D.; Zhang, P.; Xiong, Y.; Wang, T.; Wang, Q.; Zhang, C.; Wang, L.; Lu, S.; Liu, T. C.; Qi, S.; et al. Mater. Today Energy 2025, 54, 102121.
—— 支撑「Li+ 配位会抬高电解液的氧化还原电位」这一实验/机器学习证据，其归因为静电与离子–偶极的联合作用，且两类作用对氧化与还原电位的影响方向相反；对应本论文把「配位位移」拆成氧化轴与还原轴分别统计的做法。

[3] Marenich, A. V.; Ho, J.; Coote, M. L.; Cramer, C. J.; Truhlar, D. G. Phys. Chem. Chem. Phys. 2014, 16 (29), 15068–15106.
—— 支撑「液相还原电位的计算协议」：热力学循环（自由能差到电位换算）与隐式溶剂协议的系统评述，是本论文 ΔSCF/IP–EA 位移量口径的方法学依据。

[4] Husch, T.; Yilmazer, N. D.; Balducci, A.; Korth, M. Phys. Chem. Chem. Phys. 2015, 17 (5), 3394–3401.
—— 支撑「电解液溶剂的大规模虚拟高通量筛选」与「电化学稳定性窗口估计量」的既有先例，用于说明本论文的分子榜单并非孤立工作。

[5] Peljo, P.; Girault, H. H. Energy Environ. Sci. 2018, 11 (9), 2306–2309.
—— 支撑「应当用氧化还原电位而不是 HOMO/LUMO 能级来定义电解液稳定窗口」（该文指出二者偏差可达数 eV）；这是本论文全程使用 IP/EA 位移而非轨道能级差的判据基础。

[6] Itkis, D.; Cavallo, L.; Yashina, L. V.; Minenkov, Y. Phys. Chem. Chem. Phys. 2021, 23 (30), 16077–16088.
—— 支撑「团簇–连续介质（cluster–continuum）模型的 Li+ 溶剂化自由能存在模型歧义」，以及 SMD/CPCM 对溶剂团簇溶剂化自由能的系统偏差；对应本论文连续介质层（CPCM/SMD）设置与不确定性讨论。

[7] Pracht, P.; Grimme, S.; Bannwarth, C.; Bohle, F.; Ehlert, S.; Feldmann, G.; Gorges, J.; Müller, M.; Neudecker, T.; Plett, C.; et al. J. Chem. Phys. 2024, 160 (11), 114110.
—— 支撑「构象/低能化学空间搜索」这一步的方法引用（CREST 程序）。

[8] Rebollar-Zepeda, A.; Carreon-Gonzalez, M.; Muñoz-Rugeles, L.; Alvarez-Idaboy, J. R. J. Chem. Theory Comput. 2026, 22 (13), 6367–6376.
—— 支撑「连续介质溶剂化项与气相 RRHO 热化学修正直接相加会在分子数变化的过程中引入人为熵罚」这一已知误差来源，用于界定本论文热力学换算的不确定度。

[9] Bannwarth, C.; Ehlert, S.; Grimme, S. J. Chem. Theory Comput. 2019, 15 (3), 1652–1671.
—— 支撑「GFN2-xTB 半经验紧束缚方法的定义与参数化范围」，是本论文 xtb 几何优化/单点计算的方法引用。

[10] Grimme, S. Chem. Eur. J. 2012, 18 (32), 9955–9964.
—— 支撑「色散校正密度泛函 + 刚性转子谐振子（RRHO）处理下的超分子结合热力学」，是本论文配位「位移」换算为热力学量时的参照框架。

[11] Yao, N.; Chen, X.; Fu, Z.-H.; Zhang, Q. Chem. Rev. 2022, 122 (12), 10970–11021.
—— 支撑「液态电解液的经典/从头/机器学习分子动力学模拟」综述背景，用于把本论文的静态量子化学排序与动力学/界面方法作对比。

[12] Marenich, A. V.; Cramer, C. J.; Truhlar, D. G. J. Phys. Chem. B 2009, 113 (18), 6378–6396.
—— 支撑「SMD 隐式溶剂模型」的定义与参数（体相介电常数、折射率、表面张力、酸碱性参数），是本论文介电层计算的模型出处。

[13] Cheng, H.; Sun, Q.; Li, L.; Zou, Y.; Wang, Y.; Cai, T.; Zhao, F.; Liu, G.; Ma, Z.; Wahyudi, W.; et al. ACS Energy Lett. 2022, 7 (1), 490–513.
—— 支撑「电解液溶剂化结构与电极/电解液界面模型」的综述背景，用于把 Li+ 配位位移放回电池语境。

## 方法学与软件引用（非 PDF，需作者核对）

- ORCA 6（程序包总引，对应 ORCA 4/5 世代）: Neese, F.; Wennmohs, F.; Becker, U.; Riplinger, C. The ORCA Quantum Chemistry Program Package. J. Chem. Phys. 2020, 152 (22), 224108.
- ORCA 5.0 版本更新（建议与上条并用）: Neese, F. Software Update: The ORCA Program System—Version 5.0. WIREs Comput. Mol. Sci. 2022, 12 (5), e1606.
- ORCA 6.0 版本更新（待核）：Neese, F. et al. Software Update: The ORCA Program System—Version 6.0. WIREs Comput. Mol. Sci. 2025, 15, e70019.（年份/卷期待核）
- GFN2-xTB: Bannwarth, C.; Ehlert, S.; Grimme, S. GFN2-xTB—An Accurate and Broadly Parametrized Self-Consistent Tight-Binding Quantum Chemical Method with Multipole Electrostatics and Density-Dependent Dispersion Contributions. J. Chem. Theory Comput. 2019, 15 (3), 1652–1671.
- r2SCAN-3c（复合方法定义）: Grimme, S.; Hansen, A.; Ehlert, S.; Mewes, J.-M. r2SCAN-3c: A 「Swiss army knife」 Composite Electronic-Structure Method. J. Chem. Phys. 2021, 154, 064103.
- r2SCAN 泛函: Furness, J. W.; Kaplan, A. D.; Ning, J.; Perdew, J. P.; Sun, J. Accurate and Numerically Efficient r2SCAN Meta-Generalized Gradient Approximation. J. Phys. Chem. Lett. 2020, 11, 8208–8215.
- SMD 溶剂化模型: Marenich, A. V.; Cramer, C. J.; Truhlar, D. G. Universal Solvation Model Based on Solute Electron Density and on a Continuum Model of the Solvent Defined by the Bulk Dielectric Constant and Atomic Surface Tensions. J. Phys. Chem. B 2009, 113 (18), 6378–6396.
- CPCM/导体极化连续介质模型: Barone, V.; Cossi, M. Quantum Calculation of Molecular Energies and Energy Gradients in Solution by a Conductor Solvent Model. J. Phys. Chem. A 1998, 102, 1995–2001.

> 说明：上列 8 条为论文正文/计算部分实际使用的程序与方法，均不属于本次 13 篇 PDF 的范畴，请作者按投稿期刊要求核对版本与卷期（已标注「待核」的条目需人工确认）。
