# physics_completion_v1 科学协议（WP0 登记）

> 本协议把仓库外的《电解液排序稳定性：物理证据补强与决策预算研究执行方案》登记为可追溯的新批次。
> 它**不**改写旧定义（`config/scientific_definitions.yaml` 原样保留，append-only），**不**运行新的电子结构计算，
> **不**改动任何既有冻结数据、阈值或结论。

## 1. 研究问题

在本集合内，继续追问：哪些缺失物理会改变候选选择；这种变化是否超过独立评估的方法与采样敏感性；
恢复指定计算目标的选择需要多少额外信息。四个可分别完成的任务：

1. 弛豫、热校正和构象系综是否分别改变氧化候选清单？
2. 同一连续介质中，Li 配位是否改变可比物种的氧化排序？
3. 独立方法审计下，哪些 pair 可解析、哪些翻转仍成立、哪些只能归入候选等价集合？
4. 以完成 QC 的目标标签为终点，廉价模型/Δ-learning/主动查询相对随机策略节省了多少成本？

氧化为首轮确认性主轴；还原为有条件的探索性副轴。实验可比性单独报告，不把指定计算目标称为真实电解液排序。

## 2. 量名、方向与状态身份

| 量名 | 定义 | 单位 | 方向 | 量类 | 分析 cohort |
| --- | --- | --- | --- | --- | --- |
| `Eox_vertical` | E(M+) - E(M) on the same initial geometry | eV | maximize | electronic_energy_difference | cheap_reference |
| `Eox_adiabatic` | electronic-energy difference between the two relaxed states | eV | maximize | electronic_energy_difference | relaxation_effect |
| `Gox_single` | free-energy difference from one representative minimum per state | eV | maximize | gibbs_free_energy_difference | thermochemical_correction |
| `Gox_ensemble` | conformer-ensemble free-energy difference, -RT ln sum g_i exp(-G_i/RT) | eV | maximize | gibbs_free_energy_difference | main_target |
| `Gox_Li_ensemble` | G([LiM]2+) - G([LiM]+) using per-state ensembles | eV | maximize | gibbs_free_energy_difference | conditional_coordination_target |
| `coordination_shift` | Gox_Li_ensemble - Gox_free_ensemble | eV | maximize | conditional_shift | conditional_coordination_target |
| `Sred` | G(reduced) - G(parent) = -EA (unified reduction-resistance score) | eV | maximize | gibbs_free_energy_difference | conditional_reduction_secondary |

方向语义只在 `config/physics_completion_v1.yaml` 的 `objective_direction` 定义一次：
原始 EA 方向为 **minimize**，统一抗还原 score `Sred = -EA` 方向为 **maximize**；二者必须选出同一候选集合。
缺值、不合格态、未完成 QC 的状态一律记为 `None`，**绝不**被替换成 0。

状态身份资格：还原轴只允许 `molecule_centered_redox` 进入主 ranking；其余标签作为 mechanistic outcome 单独统计。

## 3. 样本（12 主集 / 8 方法集 / 4 采样集）

| cohort | 分子 | 目的 |
| --- | --- | --- |
| main | C01、C02、C03、C04、C05、C08、C09、C13、C14、C15、C16、C17 | 固定主配对集（12） |
| method_audit | C01、C02、C04、C08、C13、C14、C16、C17 | 方法审计集（8） |
| sampling_audit | C02、C03、C08、C17 | 构象/配位采样审计集（4） |

这是针对现有问题设计的配对子集，不用于宣称化学空间普适性。FEC、VC、SN、TEGDME 保留为后续扩展。

## 4. 固定条件、方法与停止规则

固定 SMD 乙腈背景、298.15 K、溶液标准态 1 mol/L；几何起点 r2SCAN-3c；
单点生产候选为 range-separated hybrid（如 ωB97X-D4）配 triple-zeta 基组，审计对照为另一合理泛函（如 PBE0-D4）。
同一介质、同一几何、同一状态下比较 2 个泛函 × 2 个基组设定；还原必须使用含弥散函数的设定。

导数政策：生产与救援几何优化必须使用解析一阶梯度，`NumGrad` 与 `%numgrad` 明确禁止。
【协议 v1.3，2026-10-17 全局修订】频率 Hessian 由 `NumFreq`（有限差分）改为 `AnFreq`（解析 Hessian），全 cohort 统一。依据：60/60 腿配对审计（54 一致/6 不一致且分歧全在问题腿）＋ DX 步长探测（AN/LiM_2plus：DX=0.005→-127.20、DX=0.010→-57.21、AnFreq→0，真实鞍点不会随步长近乎减半）→ 虚频是离散化噪声。AnFreq 含 CPCM/SMD Hessian 项且警告块为空。审计：`outputs/physics_completion/method_audit/anfreq_paired_audit.md`。
另做同一收敛几何上的配对 `AnFreq` 审计：先用干净小体系和 TMP 失败态验证 ORCA 6.1.1 对完整
wB97X-D4/目标基组/SMD 模型项的兼容性，再扩至全部可用收敛几何。审计结果单独登记，不按单腿
挑选更好看的频率；只有完整模型项、3N 模式、热化学与几何哈希全部通过，才能以全局协议修订
统一采用 `AnFreq` 并重建可比账本。
`AnFreq` 不可断点续算且内存需求更高，因此先以小数组试算并用实测峰值内存决定后续并发。

几何收敛修订：所有新生成或救援的生产腿使用解析梯度的 `Opt VeryTightOpt`。冻结阈值为
`TolE=2e-7 Eh`、`TolMaxG=3e-5 Eh/Bohr`、`TolRMSG=8e-6 Eh/Bohr`、
`TolMaxD=2e-4 Bohr`、`TolRMSD=1e-4 Bohr`。虚频腿必须先从最新收敛几何继续严优化，
再在同一最终几何做 `AnFreq`；仍有显著虚频才进入模式扰动或独立构象。
旧 `TightOpt` 零虚频且其余 QC 通过者保留；虚频、可疑低频或重提交腿不得绕过新闸门。

停止规则（在结果产生前冻结，不按结果反推）：

- 方法分歧与目标间距相当 → 冻结为 `unresolved`；
- 所有候选设定均出现明显身份/QC 问题 → 先缩小可比问题，不进入大批量生产；
- 两轮采样后仍不收敛 → `sampling_limited`；
- 没有完整分子中心还原态 → `identity_outcome`；
- 外部量不可比 → `validation_limitation`；
- AL 不胜随机 → 报告无证据支持节省，不增加复杂模型。

## 5. 三层表述纪律

每份报告都区分**模型事实** / **统计判定** / **材料意义**，不混写。主结论带 Track A（指定计算目标内的决策稳定性）
或 Track B（外部参考有效性）标签；待验证推断单独标出。Gate 1 闭合前措辞只用 `designated computational target` /
`designated reference model`，禁用 `validated target`。`NOT CLOSABLE` != `NO SUCH DATA EXIST ANYWHERE`。
