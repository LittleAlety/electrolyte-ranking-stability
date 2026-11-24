# 核心计划长期执行补充：45/48 阶段交付与剩余三态

版本：execution-supplement-20261029-v1。日期：2026-10-29，Asia/Shanghai。

本补充落实用户“准备更长任务，并把之前步骤写入核心计划”的要求。它整理已有决定、可连续执行的本地工作和需要实际计算授权的分支，不修改冻结科学验收，也不签发 EC、DMC、WP6 或扩池的新计算额度。

科学主文：[综合核心方案 v3.0](../../../核心文件/电解液排序稳定性-综合核心方案-v3.0.md) §1–20；主文新增 §21 对应本执行补充。仓库内本文件可以随 Git 追踪；上级核心文件在代码仓库外。完整团队执行入口：[DeepSeek Harness 长任务提示词](../handoffs/long_run_20261029/DEEPSEEK_GOAL_PROMPT.md)。

## 1. 三个终点与本轮范围

| 终点 | 完成条件 | 当前定位 |
| --- | --- | --- |
| 阶段交付完成 | 已执行实验来源、QC、费用和限制清楚；WP3/WP5/合规/报告/页面/镜像同轮一致；所需检查完成；无未知提交或未解释在途 | 本长任务可自主推进的主要终点 |
| EC 下一批提交准备完成 | 固定 p4→p7、真实输入与机器合同、费用和尝试守卫、导入链、HOLD 包及审批材料可复核 | 可先完成，不以未获计算授权阻止本地准备 |
| 严格研究目标完成 | 真实 48/48，加完整目标池评估、其他冻结验收和实际触发后的后继任务全部满足 | 当前未完成；不能由阶段报告代替 |

本轮可做：文档、生成器/守卫修复、测试、纯几何生成、已有日志诊断、费用核对、HOLD 执行包、下游分析和交付。

计算分支：只有可追溯的用户授权确实覆盖该态、方法、次数、候选、profile 和新增预算时才执行。EC 32 CH 当前属于提议；DMC 本轮停止。旧 800 CH、600 CH 或剩余救援额度不自动成为后继实验授权。已有明确授权不重复索要。

## 2. 已核验快照与已完成事项

截至 2026-10-29 本地核对，HEAD 为 `216a603`，工作树有并行会话未提交修改；启动执行时重新确认。此表不证明实时 Slurm 队列。

| 项 | 快照/结果 | 执行含义 |
| --- | --- | --- |
| primary | runtime 60/60，主态科学验收 48/48 | 不重复生产主态，也不混作系综分母 |
| 系综 | 45 accepted、3 limited、0 provisional | 从标签推导，不硬编码数量 |
| AN/M_plus | v2 single_basin_verified/resolved | 既有搜索证据恢复完成，不重新增加计算 |
| DOL/LiM_2plus | v2 single_basin_verified/resolved | 新成员是同簇较低能代表；不称“新盆地” |
| DOL 身份 | 新加权成员前沿单点 3808874 已完成 | 已有身份数据不重复计算 |
| limited | DMC/M_plus、DMC/LiM_2plus、EC/LiM_2plus | 本轮停止及失败证据保留 |
| 严格证据 | 5/6，通过项含身份；全目标池 WP5 未通过 | 工程全绿与科学总闸门分别报告 |
| 正式 WP5 | A=11/12、B=10/12；32组中19 computed、13 not_reached_within_pool | 子池结果可报告，不作为完整12分子验收 |
| 费用 | 首轮与 reopt、身份单点均已有实际消耗；逐腿连接修复在工作树中 | 核验原始调度与修复，不把已修复项反复列待办 |
| EC 新资料 | 六个纯几何候选 p3–p8；固定拟选 p4、p7 | 只是候选资料，尚不能等同于可提交生产包 |

以下历史步骤已纳入计划：登记通道和来源角色接线；121行候选生成；首轮 DOL/EC 回收及五阈值判定；输入副本与末几何纠正；严格 reopt；去重簇感知及旧复核版本失效；AN 搜索结论保留；DOL 新身份；费用元素映射修正。它们作为验证对象保留，不作为重新实施的任务清单。

旧主文 §18.1 的34/11/3及根 `计划.md` 的2026-10-24数字继续作为有日期的历史快照。主文 §19.1 的旧实现差异须逐项查当前代码和测试，已有修复不重做。

## 3. 连续任务板 L00–L14

| ID | 工作 | 具体动作/交付 | 完成条件 |
| --- | --- | --- | --- |
| L00 | 接棒与归属 | HEAD、原始 git status、文件所有者、源哈希、授权范围、任务板 | 不覆盖并行文件，已做/待做可区分 |
| L01 | 科学与费用基线 | labels/coverage/identity 与任务—数组—allocation—费用证据矩阵 | 同一态、同一作业证据可复算 |
| L02 | EC 合同修正 | 固定 p4→p7；账本必需；16CH/腿；32CH总帽；一次在飞；最多两次实际提交 | 负向用例拒绝第三腿、低报预留、漏账本、错候选 |
| L03 | EC 可执行 HOLD 材料 | 新执行目录、冻结 inp、members/tasks/batches/sbatch、完整 SHA、导入测试 | 真实加载器走通；备用不误进 pending；授权不足保持HOLD |
| L04 | DMC 历史过程诊断 | 逐态完整attempt清单、末若干步五准则/能量/SCF、来源行号和图 | 判断依据来自过程而非单一末值；缺失显式登记 |
| L05 | DMC 新实验定义 | A/B/C逐态比较、可否证假设、与历史差异、对照、预算和停止条件 | 有证据推荐具体机制，或有依据不推荐任何机制 |
| L06 | WP3 与机制结论 | 当前标签下pair/Top-k/区间/阶梯和机制案例重建、差异说明 | 可解析与受限结论分开，不承诺全池排名 |
| L07 | WP5 与费用消费 | A/B目标池、任务恒等式、模型/采集模型、正式回放、费用、停止预算 | 输入来源一致；computed/not_reached/full-pool三种含义正确 |
| L08 | 采样、外部锚点及后继门 | 3→6差异与限制、WP4 limitation、WP6/扩池触发证据 | 不把审计处理完整说成采样收敛，不自动启后继计算 |
| L09 | 报告与图 | 新阶段报告、六件交付/六图映射、结论—证据—限制矩阵 | 每个主要结论有图表与来源；历史不被静默改写 |
| L10 | 工程收口与发布候选 | 定向测试、生成器/check、离线链、镜像、页面、暂存白名单 | 所需检查通过；科学阻塞如实保留；Git归属清楚 |
| L11 | EC 授权分支 | 具体授权存在才运行p4；真实bridge/队列/远端哈希/journal/预留 | 一次提交、有明确作业映射；不确定响应不重投 |
| L12 | EC 终态与第二腿分支 | 取证、QC、去重/覆盖/聚合、结算；符合合同才激活p7 | p4通过覆盖则停；否则最多p7；无第三腿 |
| L13 | 全结果下游重建 | 每次新科学结果按源→QC→系综→WP3/WP5→合规→交付重建 | EC成功最高46/48；失败维持实测结果，不操纵数量 |
| L14 | 结束与接力 | 阶段最终报告、剩余门、后继实验精确审议包、复现与版本 | 可结束本轮；新预算缺失仅暂停对应计算分支 |

推荐顺序：L00→L01→L02/L04并行→L03/L05；L06–L10与计算授权等待独立推进。L11–L13是条件分支，不是完成L10的前提。最终汇合到L14。

## 4. 角色、单写入者与有限团队

- Lead：唯一修改生产生成器、配置、tests、账本和派生产物的人；负责集成、验证与交付。
- Agent A：费用/profile/任务映射，只读生产源；在独占新目录交付证据与候选修复。
- Agent B：DMC现有日志和科学判据，交付过程数据、假设和反证。
- Agent C：WP3/WP5、采样与报告/页面一致性，交付缺口和章节草稿。
- 每个agent任务明确输入、输出、验证命令和禁止修改范围；先用已有空闲成员，结束后回收名额。并发以实际平台容量为限。
- Agent无产物时检查交付路径与运行状态；任务明确失败或连续反馈无交付则Lead接手。不得仅因UI显示running就继续等待，也不以固定秒数判定复杂任务失败。
- Lead独立复跑关键结论。已修复且必要验证通过后继续下一任务，不发明新审计轮次；无变化不重复轮报。

## 5. L02/L03：EC 专用机器合同与输入链

### 5.1 固定对象与真实文件

候选资料：`work/hpc_ec_recovery_v2_20261028/manifest.json`。

现有候选目录（无 `tasks/` 层）：

- `work/hpc_ec_recovery_v2_20261028/EC/LiM_2plus__ec_v2_p4/`
- `work/hpc_ec_recovery_v2_20261028/EC/LiM_2plus__ec_v2_p7/`

父几何：`work/hpc_dol_ec_recovery_v1_reopt_20261027/tasks/EC/LiM_2plus__p4_02_ring_pucker_twist/snapshots/3791416_1/job.xyz`。

完整 SHA256：`a0a8d53b1e6083c4212d98d844350ce3248c38d201b82f9f3f40936341cd969b`。草案中省略中间任务路径的写法不存在，应在执行文档修正。`6c711c4e…` 属更早几何，不混称本次reopt末几何。

当前候选 manifest 的 `profile` 不是提交器读取的 `resource_profile`；候选资料还缺执行包的 members、batches、tasks.txt、batch_1.txt、sbatch与生产输入。不得把候选JSON验证称为完整提交器端到端通过。

### 5.2 预算与次数

建议新合同：`orca_production_4h_v1`，4核×4小时=16CH/提交元素，整个EC campaign累计≤32CH。该profile当前 `attempts_ledger_required=False`，必须在此新profile范围内强制真实账本；保留历史profile原有语义。

提交前同时验证：

```text
candidate ∈ [ec_v2_p4, ec_v2_p7]
candidate == derive_next_candidate(campaign_history)
profile == orca_production_4h_v1
cores == 4 and wall_hours == 4
new_reservation == 16 * number_of_elements
settled_cost + all_unsettled_reservations + new_reservation <= 32
EC_active_pending == 0 before submitting next element
EC_submitted_elements < 2
```

`first_batch_reserved_core_hours` 对本新ORCA批不得低报真实预留；不修改历史xtB批次的独立约定。EC/DMC生产按本新方案串行；账户总量仍需遵守实际≤20及QOS/CPU约束，不能把本campaign≤1误写成全账户≤1。

保守建议：本新EC批最多两个实际提交元素，技术故障也保留提交次数和实耗；科学尝试计数与实际提交计数分别记录，不自动增加第三次技术补投。旧批次技术故障计数规则保持其原合同。

顺序门明确拒绝“先投p7”和“p4已accepted仍投p7”；p7仅在p4明确终态、完整证据判定未通过覆盖时可激活。提交响应未知时，次数和预算预留均保守占用；只有journal与Slurm共同证明没有被调度接收，才能解除该占位。客户端错误、缺JobID或网络超时不能作为释放依据。

### 5.3 active/reserve 与状态转移

初始只激活p4。p7及p3/p5/p6/p8均保留候选资料，不进入正式candidates的planned成员或可被importer发现的待跑任务。可为备用准备不被生产导入器识别的模板。

推荐每条active腿独立执行包、共同campaign费用账本；p7执行包仅在激活条件满足后建立。不要先建立两条可发现任务再只提交一条，造成备用永远pending。

| 状态 | 后续 |
| --- | --- |
| 本地准备完成、无具体计算授权 | READY_HOLD；呈交一次具体包并继续L04–L10 |
| p4提交响应不明 | SUBMISSION_UNKNOWN；查journal/squeue/sacct，不重投、不删除锁 |
| p4运行中 | 等真实终态；独立推进其他本地任务 |
| p4完整QC且覆盖验收通过 | 结束EC campaign；p7保持reserve；结算并重建 |
| p4有明确最终失败 | 若授权覆盖p7、总费用+预留合规、无在飞，则激活p7 |
| 日志/映射/证据缺失 | 先诊断和补取，不把未知当失败触发下一腿 |
| p7通过或失败 | 结束本campaign；不从其他备用候选递补 |

“通过”使用实际QC、去重、搜索范围、身份与覆盖判据；不能把 Slurm COMPLETED、零虚频或未定义的“六项齐”当作自动accepted。

## 6. L01/L04：费用和DMC难点代码契约

### 6.1 费用

通过受保护bridge获取并保存原始 `JobIDRaw,JobID,State,ExitCode,AllocCPUS,ElapsedRaw`。连接为 task→member→array element→JobIDRaw；不按输出顺序，不累加父/`.batch`/`.extern`。完整原始字节与所用解析规则留证。

既有现场观测（执行时核对，不硬编码结果）：3791416_0/DOL对应JobIDRaw3791417、4核810秒；3791416_1/EC对应JobIDRaw3791416、4核1004秒；3808874_0为4核107秒。保持各次历史费用、不用预留充实耗、不用p90结算。未舍入值求和，最后展示时舍入。

缺失、矛盾、重排队或多段allocation不明确时拒绝简单结算，先形成明确映射和生命周期记录。旧DEC两腿的显式不完整费用不得因本批修复变成“全部来源完整”。

### 6.2 DMC 过程诊断

先查现有解析器能否产出逐步轨迹；能复用则扩展，确无入口再新增一个纯本地解析生成器并按仓库规则登记。输入必须逐条点名，不扫全盘、不调用ORCA/xtB。

建议输出 `DMC_OPTIMIZATION_TRACE.csv`、`DMC_FAILURE_MATRIX.csv`、`DMC_MECHANISM_DECISION.md` 和输入索引。每行至少：state/member/attempt/job/log_sha256、优化任务段、cycle、源行号范围、E、abs_delta_E、RMSG/MaxG/RMSD/MaxD及单位、冻结阈值与比值、SCF状态、缺失原因。相同日志哈希别名不重复算独立实验。

解析契约：按实际表头和单位识别，区分循环内收敛表与独立优化任务；不将5张表说成5次独立优化。TolE用绝对值；首点收敛或缺某列写MISSING并解释，不补零、不拿上一任务段末值。纯粹最后一步超差不自动证明震荡、平台或不可恢复。

至少覆盖：多优化段、能量差正负、首点收敛、缺列、异常终止、重复日志别名。图显示末若干步五准则相对阈值和能量变化，图注写单位、来源和诊断边界。

机制表逐态回答“改变什么—为何针对失败—如何否定—所需对照—冻结目标如何验证”。M_plus无Li不能用Li配位机制；旧P4重命名不算新机制；GFN2更紧预优化不保证DFT阈值改善；A/B中的xtB优化仍属于新超算计算。

改变优化算法不自动要求全cohort重算；改变电子结构/介质或最终数值目标须评估可比性。不能先验写“所有设置变更都要重算60腿”，也不能只取有利新结果替换冻结标签。

## 7. L06–L09：研究内容与结题材料

- WP3：从最终合格标签重建pair证据、阶梯、Top-k与受限区间；注明DOL/AN修正是否改变结论。缺失态可改变全池Top-3时，不认证全池排名。
- WP5：A为free氧化、B为Li−free位移；核对四腿、准入和费用。保留四模型、四策略及配对repeat初始集合、可见标签隔离和训练内预处理。当前联合停止算法已经实现，不重写算法求好结果。
- 停止预算：同20 repeats至少16个在n和n+1均成功、两点均未耗尽，报告n+1；O3≥2/3且Top-3集合均值regret≤0.10eV。not_reached是合法结果；全池评估完成与所有组都成功是两回事。按冻结合同分别报告。
- 当前A11/B10回放支持子池结论，不替代A12/B12。模型没优于随机时如实报告，不无限加模型或改阈值。
- 3→6：登记、QC、去重、差异和限制处理可以完成；生产级采样收敛仍待独立容差或实用分辨率冻结，不能借GFN2的1kcal/mol过门。
- WP4：外部锚点可比性不足按validation limitation保留，不把付费墙作为没有任何数据的证明。
- 交付：对照主文§16逐项登记六件交付及六张主图，写清图号、生成入口、源哈希、结论、限制；已有图适用则复用，不为数量编新图。新实验材料不要静默覆盖有日期的历史报告。

报告至少包括研究问题、协议与证据、45/48结果、AN/DOL正确依据、三态限制、WP3/WP5、费用范围、采样/外部验证边界、复现和后继实验。

## 8. 验证、Git与复现

按真实变更选择定向测试，新增负向测试针对可导致错误提交/结算/验收的缺口。不要反复跑无关全量测试。可用入口：

```powershell
.\.venv\Scripts\python.exe -B -m pytest tests/test_submit_hpc_batch.py tests/test_evidence_gate_and_cost.py tests/test_resolved_route_evidence.py tests/test_strict_readiness_strict.py tests/test_cost_scope_plumbing.py -q
.\.venv\Scripts\python.exe -B scripts/wp_production/build_coverage_reviews.py --check
.\.venv\Scripts\python.exe -B scripts/wp_production/build_production_ensemble_aggregator.py --check
.\.venv\Scripts\python.exe -B scripts/wp_production/strict_readiness_wiring.py
pwsh -NoProfile -File scripts/wp_production/finalize_wp2.ps1
git diff --check
```

整链会生成派生产物，故由Lead在文件归属清楚时运行；`--check`自身必须只读。收口链使用现有入口，不使用会启动本机ORCA的旧runner。当前链引用机器本地 `work/_converge_acceptance.py`；干净克隆复现必须明确该依赖如何获得或为何被判MISSING，不能假称纯仓库可完整复现。

`finalize_wp2.ps1 -Commit`会广泛暂存，故共享脏树只运行不带该开关的链。对本轮自有文件显式白名单暂存，检查cached diff；与他人改动混在一文件时先分离审阅，不能重置用户文件。commit/push沿用实际已有授权，无授权则交付发布候选；不强推。

哈希区分输入/归档规则：原始计算证据按原始字节；某历史登记表明确LF归一化时按其规则复算并标注。不得为消除差异擅自统一换行，或因原始字节与归一化digest不同误报全仓库损坏。

验证报告写检查名称、退出码、范围与未执行集成项。strict总目标false可与离线工程链通过并存；不能修改预期值强行抹掉真实科学缺口。

## 9. 后继分支与有限结束

EC获得有效授权后才进入L11/L12；本长任务的文档准备请求不构成32CH批准。DMC保持本轮停止，完成L04/L05后只呈报具体新实验。WP6在accepted=48/48且Li配对≥9/12时重新计算触发；扩池按自身门判断。两者即便触发，预算仍需明确；触发不等于已经完成，也不自动取得新计算额度。

若以后达到48/48，仍需完整A/B池重建和正式评估、采样/身份/成本/报告及已触发后继任务的实际完成证据；不自动把plan_overall_complete设为satisfied。

本轮结束须交付：阶段最终报告、输入证据索引、测试与检查结果、六图/交付映射、EC具体HOLD审议包、DMC机制判断、剩余门与Git版本。只有真实缺外部资料/权限时才暂停依赖项，其他本地任务继续。无授权计算分支可以以READY_HOLD结束准备，不用每轮重复申请；严格目标未完成不导致本轮长任务无限续跑。
