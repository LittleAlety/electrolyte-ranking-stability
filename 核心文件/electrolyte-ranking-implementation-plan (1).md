# 电解液排序稳定性：物理证据补强与决策预算研究执行方案


## v1.3 几何收敛紧急修订（2026-10-15）

1. **新任务统一升级为 `VeryTightOpt`**：所有尚未生成的新生产腿、救援腿和构象扩样均使用解析梯度的 `Opt VeryTightOpt`。冻结阈值为 `TolE=2e-7 Eh`、`TolMaxG=3e-5 Eh/Bohr`、`TolRMSG=8e-6 Eh/Bohr`、`TolMaxD=2e-4 Bohr`、`TolRMSD=1e-4 Bohr`；任务输入和 manifest 必须机器登记该档位。
2. **虚频先做严优化，不直接判定势能面失败**：从该腿已有的最终收敛几何继续 `VeryTightOpt`，不得从较早起点重新浪费优化；严优化正常收敛后，在其最终几何重新计算频率。只有这一步仍有显著虚频，才能进入模式扰动、独立构象或 `sampling_limited` 判定。
3. **与 AnFreq 审计组合而不混淆原因**：同一 `VeryTightOpt` 最终几何先运行冻结的 `NumFreq`，再运行配对 `AnFreq` 诊断。若两者均有同一虚频，优先解释为真实曲率/鞍点；若仅 `NumFreq` 有小虚频，则登记 Hessian 数值敏感性；不得用不同几何比较两种频率算法。
4. **旧结果的过渡政策**：此前 `TightOpt` 且零虚频、电子身份和其他 QC 全通过的腿保留，不无差别重算；此前 `TightOpt` 且存在虚频、最低正频异常、优化边界可疑或准备重新提交的腿，必须经过 `VeryTightOpt` 后才可科学验收。正在运行的旧任务允许完成以保留诊断证据，但其虚频结果不能绕过新闸门。
5. **验收证据**：除 `THE OPTIMIZATION HAS CONVERGED` 外，导入时必须记录实际收敛档位及最终五项阈值/数值。只有五项均满足 `VeryTightOpt` 阈值且频率完整时，救援腿才可进入后续科学 QC。


## v1.2 导数计算紧急修订（2026-10-15）

1. **解析一阶梯度是硬约束**：所有后续生产、救援与构象扩样的 ORCA 几何优化均使用 wB97X-D4 的解析梯度；输入中禁止 `NumGrad` 与 `%numgrad`。任务包生成器、导入器和测试必须 fail-closed，不能只靠人工检查。
2. **术语分离**：`NumGrad` 才是数值一阶梯度；当前 `Opt NumFreq` 的 Opt 使用解析梯度，`NumFreq` 则对解析梯度做有限差分得到数值 Hessian。不得因为名称相似而把已经运行的 `NumFreq` 作业误判为违反解析梯度要求。
3. **AnFreq 配对审计**：对同一收敛几何、同一电荷/多重度、同一 wB97X-D4/目标基组/SMD 设置另跑 `AnFreq`。第一阶段包含至少一个已通过的干净小体系和 TMP 的虚频失败态；兼容性通过后扩展到全部可用收敛几何。记录输入/几何哈希、ORCA 版本、模型项、3N 模式、虚频数、最低频、ZPE、热校正与 G，并与 `NumFreq` 逐态比较。鉴于 `AnFreq` 更耗内存且不可断点续算，先做小数组并按实测峰值内存扩容，不直接铺满队列。
4. **不得择优混算**：`AnFreq` 结果先作为 Hessian-method sensitivity 单独登记，不能因某一腿虚频更少就选择性替换 `NumFreq`。只有 ORCA 6.1.1 对完整目标模型（尤其 SMD 项）支持无缺项，且完整模式与热化学 QC 均通过，才允许修订冻结协议；一旦采用，应对需要比较的整套 cohort 统一重算并重建账本。
5. **当前作业处置**：现有 `Opt NumFreq` 作业没有请求数值梯度，不因本修订取消；任何含 `NumGrad` 的新旧输入一律不得进入科学验收。



## v1.1 执行决断（2026-10-15）

以下三项是对执行口径的冻结补充，不回写既有科学数值，也不把缺失证据改写成通过：

1. **WP1 还原态合规豁免**：当 `unbound_anion` 规则排除全部还原腿且合格对象清单为零时，`wp1_reduction_state_checks` 记为 `exempt`。该状态不计入未闭合项，但必须保留规则引用、零对象清单和协议；它不等于三项检查通过。未来一旦纳入合格还原腿，豁免自动失效。
2. **WP4 永久外部验证限制**：在登记的检索协议已执行、付费墙/验证码等原文障碍与 `tier_1=0` 均有证据时，未取得条件可比锚点永久归入 `validation_limitation`。结题报告在 limitation 章节保留该事实；不再把它列为可修复失败，也不宣称外部验证成功。
3. **WP6 自动升级闸门**：WP6 在闸门前保持可选；当且仅当 12 分子中至少 9 个 Li 配对为 complete，且生产级同态系综达到 48/48 时，自动升级为计划内工作。升级后未执行记为未完成；升级前保持 `blocked_on_production`。

## 1. 研究问题与最终交付

研究对象继续限定为同一固定背景中的候选分子/共溶剂/添加剂。核心问题保持为：哪些缺失物理会改变候选选择；这种变化是否超过独立评估的方法与采样敏感性；恢复指定计算目标的选择，需要多少额外信息？

将问题拆成四个可以分别完成的任务：

1. 弛豫、热校正和构象系综分别是否改变氧化候选清单？
2. 在同一连续介质中，Li 配位是否改变可比物种的氧化排序？
3. 在独立方法审计下，哪些 pair 可解析，哪些翻转仍成立，哪些只能归入候选等价集合？
4. 以完成 QC 的目标标签为终点，廉价模型/Δ-learning/主动查询相对随机策略节省了多少成本？

氧化为首轮确认性主轴；还原为有条件的探索性副轴。若还原态不是分子中心态，输出状态身份结果，不强行拼出主排名。实验可比性单独报告，不把指定计算目标称为真实电解液排序。

最终交付六件：定义迁移表、独立方法审计表、固定背景配对标签表、pair 证据表、机制案例页、成本与决策预算曲线。无法认证稳健翻转也可完成项目，但必须说明限制来自方法、采样、状态身份还是候选间距。

## 2. 基线诊断及修正原则

当前双源 sigma 由被比较两层构成，在冻结 z 下排除 robust inversion。应保留为估计器局限案例；其 unresolved 主要反映比较口径，不能直接解释成目标模型的校准误差。

当前 P1a 为各态优化后的电子能差，不是完整 Gibbs 自由能；C1 的交换量也主要为电子能。新批次必须显式区分 E、E+ZPE、G_single、G_ensemble。

P1v→P1a 目前以跨候选位移 std 作 sigma，其两个翻转应称“在该敏感性尺度下的翻转”，待独立审计后再认证。跨分子响应离散度与同一分子的方法不确定性分开保存。

R15 的代数恒等式属于判据分析，不是独立物理机制验证；Born 自相似结果是受限连续介质模型的响应规律。主论文应清楚标出两者证据类型。

旧 Gate 1 的失败原样保留。新外部验证采用新协议，不删除不一致点或改变旧阈值以救回旧 Gate。

## 3. 具体样本：12 个主集、8 个方法集、4 个采样集

### 3.1 主配对集（12 个）

| ID | 分子 | 设置目的 |
|---|---|---|
| C01 | DMC | 线性碳酸酯基线 |
| C02 | EMC | 已知弛豫/SCF 异常的复核对象 |
| C03 | DEC | DMC–EMC–DEC 系统取代序列 |
| C04 | EC | 环状碳酸酯基线 |
| C05 | PC | EC–PC 取代对照 |
| C08 | DME | 双齿醚；固定背景配体 R |
| C09 | DOL | 环约束与配位对照 |
| C13 | GBL | 内酯对照 |
| C14 | SL | 砜给体对照 |
| C15 | DMSO | 亚砜给体对照 |
| C16 | AN | 单齿腈；背景溶剂也为乙腈 |
| C17 | TMP | 磷酸酯与多配位 motif 对照 |

这是针对现有问题设计的配对子集，不用于宣称化学空间普适性。选择 EMC 属既有问题复核，不作为新发现的独立验证。FEC、VC、SN、TEGDME 保留为后续扩展，不在第一轮承担完整计算；尤其避免长链柔性分子消耗首轮预算。

### 3.2 方法审计集（8 个）

DMC、EMC、EC、DME、GBL、SL、AN、TMP。覆盖主要给体与异常类型。DOL、PC、DMSO、DEC 留作冻结方法后的检验对象；这四个仅为有限留出，不构成真正的外部验证。

### 3.3 构象/配位采样审计集（4 个）

EMC、DEC、DME、TMP。分别代表不对称碳酸酯、较柔性同族成员、螯合醚、多 motif 磷酸酯。它们用于确定采样资源规则，不用于事后挑出有翻转的漂亮子集。

## 4. WP0：定义迁移与历史结论同步（第 1 周）

新增 config/physics_completion_v1.yaml 和 docs/physics_completion_protocol.md。旧定义保留，新增 quantity_kind、geometry_policy、thermal_policy、ensemble_policy、solvent、objective_direction、state_identity_eligibility、analysis_cohort 等字段。

新批次量名：

| 量名 | 定义 | 用途 |
|---|---|---|
| Eox_vertical | 同一初始几何上的 E(M+)−E(M) | 廉价/垂直参照 |
| Eox_adiabatic | 两态各自优化的电子能差 | 弛豫效应 |
| Gox_single | 每态代表极小的自由能差 | 热化学校正 |
| Gox_ensemble | 每态构象系综自由能差 | 主目标 |
| Gox_Li_ensemble | G([LiM]2+)−G([LiM]+) | 条件配位目标 |
| coordination_shift | Gox_Li_ensemble−Gox_free_ensemble | 环境响应 |
| Sred | G(reduced)−G(parent)，也即 −EA 的统一方向 | 有条件副轴 |

主目标均报告 eV，必要时同时给 kJ/mol。原始 EA 单独保存，方向为 minimize；统一抗还原 score 为 −EA，方向为 maximize。电子化学电位/电子参考只在明确转换约定后另列，不混入分子间主排序。

结论迁移必须覆盖：

- FINAL_CONCLUSIONS Q3：C1 全态负 tau 不再用于分子还原排序脆弱性的确认性判断。
- Q7：构象敏感性与 method 主导的 tolerance 分开解释。
- Q10：统一为既定检索标准下未定位到合格数据，不能断言世界范围不存在。
- R15：区分定义性零翻转与经验未观测；计算成本最多与改排序相关，不声称因果定律。
- P1a：写明电子能层，不以 thermodynamics 标签掩盖缺失热校正。

完成标准：所有新标签可追溯；不同量不得用旧别名静默替换；人为例子中最大化 Sred 与最小化 EA 选出同一集合；不合格态/缺值不得变成 0。只为这些有实际风险的行为增加针对性测试。

## 5. WP1：独立方法审计（第 1–2 周）

### 5.1 固定模型条件

固定 SMD 乙腈背景，298.15 K，溶液标准态 1 mol/L。这个设定是受控 embedding，不代表实际 EC/DMC 配方。bare CPCM ε 扫描保留为既有旁证，不用作固定介质误差来源。

几何起点采用 r2SCAN-3c。单点生产候选采用仓库所装 ORCA 实际支持的 range-separated hybrid（例如 omegaB97X-D4）与 triple-zeta 基组；审计对照采用一种合理的另一泛函（例如 PBE0-D4）。这些是建议候选，先用本机帮助、方法回显和中性/带电 smoke run 确认支持性，不把某个软件关键字当成已经验证的设置。

同一介质、同一几何、同一状态下比较 2 个泛函 × 2 个基组设定。氧化可用 def2-TZVP 与 def2-TZVPD 一类配对；若软件具体实现有差异，记录准确名称。还原必须使用含弥散函数的设定，并检查电子空间扩展、脱附稳定性和波函数身份。有限基组能收敛不能证明束缚，旧 unbound 标记是历史 QC 决定，不是所有方法下的普适物理结论。

### 5.2 最小作业矩阵

方法集每个分子：自由态 M/M+、一个 C1 代表 motif 的 [LiM]+/[LiM]2+。8 × 4 × 4 = 128 个单点上限，不含几何/频率。若带电复合物无法形成完整态，记录为 QC outcome，不用新 motif 反复替换直到得出想要的数。

构象审计先只做自由态与配位母态的廉价搜索，再选低能独立结构进入 DFT。先冻结去重、窗口与上限，再观察目标排名。

### 5.3 方法选择与冻结

以 QC 可用率、数值稳定性、气相可比 anchor、固定介质内的 rank sensitivity、实测成本综合选择。不根据“哪个方法产生更多翻转”选方法。外部气相 IP 的 vertical/adiabatic 口径必须匹配；气相验证不能直接证明溶液模型准确。

独立方法审计是 sensitivity assessment，不等于校准的概率误差。审计表应报告所有合理方法的排序、范围和成对差值，不只给一个 sigma。

停止条件：若方法分歧与目标间距相当，冻结为 unresolved；若所有候选设定均出现明显身份/QC 问题，先缩小可比问题，不进入大批量生产。

## 6. WP2：固定背景配对自由能标签（第 2–4 周）

### 6.1 每个分子的四个主状态

M、M+、[LiM]+、[LiM]2+ 均在相同 SMD 乙腈下各自优化。先做每态一个代表结构的完整 Opt/Freq 和生产单点，再按已冻结采样规则加入额外构象/motif。

12 × 4 = 48 个状态结构起步。初始每个状态最多 3 个 DFT 独立构象/motif，总上限 144 个状态结构。单个 Opt、Freq、SP 分开记账；只有方法一致、几何一致、原始输出完整的旧作业可复用。

生成与过滤建议起始规则：廉价搜索保留母态最低结构上方 6 kcal/mol 内的独立结构；按连接关系、配位模式、重原子 RMSD/扭转角去重，先取最低的 3 个独立结构。这一窗口和上限是资源规则，不是已经证明收敛的采样尺度。

对 4 个采样审计分子扩大到最多 6 个结构，比较 3→6 的自由能变化、pair gap 与 Top-k 变化。若变化不足以跨越独立 tolerance 且选集不变，则报告“在本采样测试中稳定”；否则只对相关分子扩大搜索，最多再一轮。若仍不稳定，标记 sampling_limited，不无限加算。

不同电荷态各自采样。除母态构象传播外，应对带电态补独立种子/扭转结构，不能假定母态最低构象就覆盖其搜索空间。motif 能切换，电子身份与连接关系必须重新检查。

### 6.2 自由能账本

推荐采用明确的复合账本：G = E_SP,solution + (G_thermal,solution − E_geometry_level,solution) + 标准态项。括号项必须来自已说明方法的频率计算，避免重复加入隐式溶剂项。低频采用统一且可重现的处理（例如 qRRHO），并在分析前固定具体工具、版本和设置。

若频率实现不能在该介质下可靠运行，可用另一个明确写出的 thermodynamic cycle，但必须增加其 sensitivity；不能把气相热项静默当作溶液精确热项。

同态系综：G_ens = −RT ln Σ g_i exp(−G_i/RT)。重复搜索到同一极小不重复计数；统计简并度只有在可证明时加入。不同化学计量不混做 ensemble。

输出 raw E、ZPE、thermal correction、standard-state correction、G_single、G_ensemble；如果使用一致一分子 redox 标准态项抵消，也保留抵消说明。

### 6.3 QC 与状态身份

每态检查 SCF/几何收敛、虚频、spin、连接关系、Li–donor motif、fragment charge/spin、frontier localization。轻微虚频先复核模式和优化收敛，不自动删除；无法修复的状态不进入主极小集合。

fragment charge/spin 阈值在审计集上冻结；对临界态增加另一分区或密度差复核。阈值依赖分区方式，不作普适常数。氧化态同样检查是否保持可比身份。

主集必须是完整配对且符合预先定义的身份条件。断裂产物、Li-centered、mixed、ambiguous 与 intact 分开表；不能把优化断裂直接写成已证实的实际分解路径。

## 7. WP3：排序、独立 uncertainty 与机制（第 4–5 周）

### 7.1 主判据采用多方法一致性/保守区间

对固定目标模型 m 和 pair i,j，每个合理方法 r 得到 D_ij^(m,r)。分别为自由态和 Li 态构造方法范围，并叠加已报告的采样敏感性界限，不用 free/Li 的物理差值定义其自身误差。

主分析先用保守符号一致性：所有预先接受的方法及采样敏感性下 D_ij 仍同号，并超过数值容差，才称 resolved；两侧分别 resolved 且异号才称 robust inversion。区间重叠或符号不一致为 unresolved。容差由试算重算误差/明确实用分辨率确定并冻结，不由目标清单是否好看确定。

另外提供方法 pair spread 的 z 曲线作为 sensitivity；小数目的相关泛函并非独立随机重复，所以 1.96×spread 不能自动标成校准 95% 置信度。模型 posterior ordering probability 与电子结构误差也分开命名。

### 7.2 逐级和端点都报告

比较 vertical→adiabatic E、adiabatic E→G_single、G_single→G_ensemble，以及 fixed-background free→Li conditional。前三级尽量只改一个因素；free→Li 是条件物种变化，明确伴随各自几何/系综响应，不声称所有内部变化都被单独隔离。

每项报告同一 cohort 的 n、普通 tau_b、Top-k overlap、selection regret、resolved/robust counts、unresolved fraction。主集 n=12 时主选集固定 k=3，辅助 k=2/4；若 QC 减员，仍报告固定 k，n<2k 时主选集结论标记样本不足，同时给完整排除表。不把 pairwise unresolved 任意变成标准 tau_b 的相等值：未解析关系不一定传递，优先用偏序/集合与显式政策带。

### 7.3 机制案例最多 3 个

事先规则：优先选证据最强的稳健翻转，再选影响 Top-k 的 unresolved 边界，再选有身份改变的代表。无稳健翻转时不强行补案例。每例展示对应原始结构、电子密度/自旋、配位变化、E/G 分解、方法敏感性与实际选集影响。

描述符分析只预列 donor type、chelation、flexibility、functionalization、廉价 ESP。TPSA 相关仅探索性；报告全部检验并进行族内多重比较处理。n=12 不拟合多参数机制模型。

## 8. WP4：外部锚点复核与可比性审计（第 1–5 周并行）

首先核对当前已有的 7 个氧化锚点：原文页码/表号、原始数值、参考电极、溶剂、盐与浓度、温度、扫描速率、onset 或峰值定义、误差来源、是否跨原始系列混合。

输出三个等级：可做热力学定量比较；仅可比较特定实验系列趋势；不可用于当前目标验证。不可逆分解 onset 不自动等于完整分子一电子平衡电位。跨系列不强行汇总，7 个分子产生的 21 个 pair 也不是 21 个独立实验样本。

目标是先复核已有条目，再按明确检索协议寻找 6–10 个条件可比条目；数量不是硬造数据的目标。找不到足够可比数据，则论文保留 computational target，完成 external-validity limitation。若旧审计曾判 NOT CLOSABLE，新证据只进入新的版本化评估，不覆盖旧结论。

## 9. WP5：Δ-learning 与成本感知主动查询（第 5–7 周）

### 9.1 两个任务分开

任务 A：用 X0 与廉价 P0 预测完成 QC 的自由分子 Gox_ensemble。任务 B：已获得 free Gox 后，以 X0+X1 预测配位 shift 并恢复 Gox_Li。B 的成本必须包含获得 free 标签的成本，不能把它隐含为免费。

主模型只用岭回归/核岭与 GPR 两类，direct/shift 用相同特征、相同外层 split、相同调参预算。保留 random 与 family-group/LOFO；小家族单成员的 LOFO 是困难案例而非稳定估计。报告各留出组和配对差值，不把多个随机种子当作独立分子证据。

### 9.2 主动学习回放

12 个完整标签池内回放。初始 4 个标签、每轮 1 个、20 个配对种子；比较 random、diversity、uncertainty、ranking-aware 四种策略。隐藏标签只可由离线 evaluator 使用，acquisition、标准化与调参不得读取。X2 仅机制使用。

分别评价全池的最终选集，以及尚未查询候选上的预测。已经查询的样本使用真标签，其贡献单列，避免曲线改善被误读为模型泛化。每轮记录失败、重试与实际消耗。

报告 n_T→tau_b、O_3、R_3、remaining_unqueried_error 与累计 core-hours。建议新批次 success endpoint：O_3≥2/3 且 R_3≤0.10 eV；tau_b≥0.80 为辅助端点。0.10 eV 是计算目标容许损失的建议，不是实际电池工程阈值，在回放前冻结，并同时给完整连续曲线。至少 16/20 回放在两个连续预算点达到端点，才报告该池的经验停止预算；未达到则标“在本预算内未达标”。

这些 replay 门槛因为已经知道旧数据的大致行为，只能作为新批次协议/方法评估，不伪装成对旧数据完全盲的预注册。真实前瞻性需另留未计算分子。

### 9.3 扩样触发条件

只有目标标签与独立 uncertainty 流程可用、特征查询成本无泄漏、回放能正常运行后，才从现有 core 的剩余候选及 broad pool 预选新分子。扩展先加 8–12 个，使完整目标池约 20–24，包含至少一个未在方法审计中覆盖的家族，先冻结再计算。

规模不足时主动学习仍可作为工作流演示，不能证明普适最低标签数。首轮无需直接扩到 60–100/300–1000。

## 10. 可选 WP6：共同背景的显式配体检查

仅在量化闸门满足后做：12 分子中至少 9 个 Li 配对为 complete，且生产级同态系综达到 48/48；两项同时满足时，WP6 从可选自动升级为计划内。固定 R=DME，在 EC、DME、AN、TMP 上比较 [LiM]+ 与 [LiMR]+；所有样本同一背景配体、同一介质、相同化学计量。DME 情况自动成为 [Li(DME)2]+。

对每个 cluster 的氧化前后态各自 QC/弛豫，避免复制旧不同几何量。比较的是不同条件态的 redox 差值，不将 cluster 裸 G 跨化学计量 Boltzmann 平均。此项不模拟真实配位 population；不纳入首轮必需闭环。

## 11. 资源预算与停止规则

| 工作包 | 首轮规划上限 | 说明 |
|---|---|---|
| 方法审计 | 128 SP | 8 分子×4 状态×4 设定 |
| 主生产 | 48–144 状态结构 | 每个结构含 Opt、Freq、SP，逐任务记账 |
| 采样扩展 | 最多 48 额外状态结构 | 4 分子×4 状态×额外 3 结构；能复用则去重 |
| 关键 pair 第二方法复核 | 约 16–32 SP | 明确选择规则，属于靶向复核 |
| 可选共同配体 | 8–24 状态结构 | 4 cluster×2 氧化态×1–3 motif |

以上为规划计数，不是时间估算；不得把 job 数当计算成本。前 2 个分子的 pilot 记录 wall time、allocated cores、core-hours、memory、failed/retry、phase、method、state、conformer、raw_output。若无法获取 process CPU time，以 allocated core-hours 命名，不写成实际 CPU time。

用 pilot 的中位与 p90 按作业类别估算剩余成本；给出低/中/高资源情景及可用并发，不直接套用旧单点的 30 秒。先检查 Opt/Freq 成本；超出可用资源时先减可选还原和 WP6，再减少每态结构上限，最后缩到 8 个完整配对分子。保持物理定义完整优先于名义样本数。

停止规则：两轮采样后仍不收敛→sampling_limited；合理方法下符号不稳定→unresolved；没有完整分子中心还原态→identity outcome；外部量不可比→validation limitation；AL 不胜随机→报告无证据支持节省，不增加复杂模型救结果。

## 12. 时间安排与阶段验收

| 时间 | 必须完成 | 验收后下一步 |
|---|---|---|
| 第 1 周 | WP0、两分子 pilot、锚点复核启动 | 明确目标、方向、资源上限 |
| 第 2 周 | WP1、4 分子采样审计初版 | 冻结方法/采样规则，不按翻转结果选方法 |
| 第 3–4 周 | WP2 配对生产与 QC | 形成完整可比 cohort，缺失不补成数值 |
| 第 5 周 | WP3、外部可比性报告 | 定义可解析/不可解析的科学结果 |
| 第 6–7 周 | WP5、成本账本 | 给出有限池的预算结论 |
| 第 8 周 | 论文改写与必要 WP6/留出复核 | 新证据与旧结论分层收口 |

每周报告只写完成的科学问题、尚未解决的限制和下周依赖，不再以累计周数或图数作为完成度。

## 13. 推荐仓库落点

config/physics_completion_v1.yaml：新增协议、样本、量名、预算与停止规则。  
data/metadata/physics_completion_set.csv：固定主集/审计集标签。  
data/references/anchor_primary_audit.csv：原始锚点复核。  
outputs/physics_completion/{method_audit,free_states,li_states,ensembles,pair_evidence,ml,active_learning,cost}/：新批次产物。  
docs/physics_completion_protocol.md：科学协议。  
docs/claim_migration.md：历史到当前主结论的映射。  
docs/physics_completion_final_report.md：研究问题→结果→证据→限制。

复用现有 runner/parser；只为缺失的热化学账本、同态 ensemble、独立 pair uncertainty、查询可见性与成本统计增加代码。以上为建议新增路径，当前仓库并不存在这些产物。README/FINAL_CONCLUSIONS 由生成脚本更新，历史产物不被覆写。

## 14. 最终图与论文主线

主图控制为 6 张：模型与条件态定义；独立方法审计；E→G→ensemble 决策变化；固定背景配位 pair 证据与身份 outcome；最多 3 个机制案例；累计成本→选集恢复曲线。

主论文首先回答“在本集合中决策可否被解析”，再讨论缺失物理如何改变可解析的选择，最后讨论恢复计算目标的成本。双源 sigma 恒等式作为方法审计结果，不占据主要物理发现位置。真实电解液稳定窗口、最佳配方和 SEI/CEI 性能不由这些量推断。

若没有稳健翻转：可以得出在所测模型与独立敏感性界限内没有认证翻转，但仍明确 unresolved 的比例。若出现翻转：必须跨合理方法/采样稳健且状态可比。若绝大多数 unresolved：输出候选可接受集合，停止伪精确排名。三种结果都能完成此方案。

## 15. 现在可以直接开始的前 10 项任务

1. 保存基线提交与已有产物哈希，不重写旧结果。
2. 建立量名/方向/状态身份迁移表，修订结论生成器。
3. 固定 12 主集、8 审计集、4 采样集及排除原因规则。
4. 核验本机两种候选泛函、弥散基组、SMD 与频率设置。
5. 用 DMC/EMC 的四主态做实际 pilot，生成成本与 QC 记录。
6. 写清 E_SP 与 thermal correction 的来源，完成一个自由能账本实例。
7. 冻结 method sensitivity 的主判据，不再用 free/Li 差值估其自身误差。
8. 启动 7 个既有氧化锚点的逐条原文复核。
9. 完成方法/采样审计后，分批做固定背景配对生产。
10. 只有完整标签和 QC 完成后，运行排序机制与预算实验。

## 16. 依据与证据范围

- 用户上传 ranking-electrolyte-materials-v2.md：§3、§6–13、§23–30。
- [仓库基线](https://github.com/LittleAlety/electrolyte-ranking-stability/tree/d5217a1f1f7e85c3e117b29d734efc2a8e535ecd)。
- [R15 审计](https://github.com/LittleAlety/electrolyte-ranking-stability/blob/d5217a1f1f7e85c3e117b29d734efc2a8e535ecd/docs/49_round3_adversarial_audit.md)。
- [科学定义](https://github.com/LittleAlety/electrolyte-ranking-stability/blob/d5217a1f1f7e85c3e117b29d734efc2a8e535ecd/config/scientific_definitions.yaml)。
- [C1 报告](https://github.com/LittleAlety/electrolyte-ranking-stability/blob/d5217a1f1f7e85c3e117b29d734efc2a8e535ecd/docs/12_week5_report.md)。
- [P1a runner](https://github.com/LittleAlety/electrolyte-ranking-stability/blob/d5217a1f1f7e85c3e117b29d734efc2a8e535ecd/scripts/run_p1a_adiabatic.py)。
- [主动学习 runner](https://github.com/LittleAlety/electrolyte-ranking-stability/blob/d5217a1f1f7e85c3e117b29d734efc2a8e535ecd/scripts/run_stage8_al.py)。

候选方法、采样窗口、样本与新停止门槛均为本方案的实施建议，尚未经新计算确认。执行前以本机方法支持性、pilot 成本和可获得原始文献为约束冻结版本。
