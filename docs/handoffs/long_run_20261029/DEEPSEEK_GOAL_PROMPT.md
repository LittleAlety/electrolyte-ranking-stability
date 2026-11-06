# DeepSeek Harness 长期任务提示词：阶段交付、EC就绪与DMC机制诊断

日期：2026-10-29。配套计划：[核心计划执行补充](../../plans/CORE_PLAN_EXECUTION_SUPPLEMENT_20261029.md)。

复制下方代码块作为一次完整任务。提示词里的计算分支是条件分支；复制提示词不构成新核时或新实验批准。

```text
/goal

你是电解液溶剂-HB项目的执行Lead。请使用多agent团队，持续完成下面的连续任务。

工作目录：E:\Claude Code\电解液溶剂-HB\电解液溶剂HB-Code
科学主文：上级“核心文件/电解液排序稳定性-综合核心方案-v3.0.md”
当前执行依据：docs/plans/CORE_PLAN_EXECUTION_SUPPLEMENT_20261029.md

本goal的可完成终点：当前45/48研究结果形成科学、费用、软件和交付一致的阶段版本；EC下一实验有具体可审查HOLD包；DMC两态有基于已有日志的机制决策和下一轮实验定义。严格48/48科学目标继续如实报告。

不要把任务时长理解成无限增加审计。每一步完成即进入下一步，只有具体新失败才追加检查。

一、授权和边界

1. 自动推进本地修复、纯几何生成、解析、测试、费用核验、HOLD包、下游、图表、文档、镜像和发布候选。
2. 用户已有明确授权继续有效；先查其对象、候选、次数、预算和资源，不重复询问已经明确的事项。
3. 本提示词没有新批准EC32CH、DMC、WP6或扩池计算。具体计算授权缺失时只暂停该分支，其余工作继续到本goal终点。
4. ORCA/xtB/GFN2优化只在超算Slurm运行。本地纯几何变形不调用这些程序。DMC当前仅诊断已有数据。
5. 保护共享工作树，禁止重置、删除用户证据、强推、广泛清理旧包。原计划旧授权模板不能当新授权。

二、先核对基线，禁止重做已完成工作

启动时读取AGENTS.md、git HEAD/status、会话归属和本计划。当前核对基线为216a603及未提交工作树，若有新提交，查明差异。

预期基线：
- primary科学验收48/48，runtime60/60。
- 系综45accepted、3limited、0provisional。
- AN/M_plus和DOL/LiM_2plus均为v2 single_basin_verified/resolved。
- DOL新加权成员身份已补算3808874，不重复身份单点。
- limited：DMC/M_plus、DMC/LiM_2plus、EC/LiM_2plus。
- DMC本轮停止已裁定；EC上一批一次reopt失败后停止已生效。
- 严格证据5/6；WP5完整目标池未满足；A11/B10。
- 正式WP5有32组：19computed、13not_reached_within_pool。读当前产物确认，不能硬编码数量。
- 费用元素连接修复、合规/页面同步等可能已在工作树，不把“未提交”误写为“未实现”。

建立BASELINE与TASK_STATUS，记录每任务已完成/待做/在途/READY_HOLD及证据。机器可读状态由观测填入，不预填通过。

三、团队：Lead加三名agent，单写入者

Lead独占生产代码、配置、tests、源账本及生成物集成。

Agent A：费用和EC合同。
输入：submit_hpc_batch.py、batch_cost_settlement.py、EC候选manifest、既有attempt账本和调度原证据。
输出：元素映射矩阵、资源/profile与预算接口缺口、最小修复建议、负向测试建议。

Agent B：DMC过程数据和科学证据。
输入：DMC两态结构账本、全部已登记日志及轨迹、诊断报告、生产冻结协议。
输出：独立日志清单、五准则逐步轨迹、失败矩阵、A/B/C机制证据、诊断图草稿。

Agent C：WP3/WP5和交付。
输入：最终标签、正式A/B目标池及回放、合规、采样差异、阶段报告、页面、镜像。
输出：消费关系与缺口、结论差异、六图/六件交付矩阵、报告章节草稿。

每个agent只读生产源，必要新代码/报告放各自独占新目录，例如work/long_run_20261029/agent_a/。不得同时改同一生产文件，不commit/push、不提交计算。
给每人逐条点名输入、输出和验证命令。Lead复核后集成。
agent无交付时先核查是否运行/是否真的写出产物；明确失败或连续反馈仍无产物则Lead接手，不重复空委派。
完成后回收任务名额。可复用已有成员，不把平台旧running标记当真实进度。

四、L00/L01：先完成证据与费用连接

保存输入哈希和git归属，读取原始作业证据。
调度链：task→member→array element JobID→JobIDRaw→State/ExitCode/AllocCPUS/ElapsedRaw。

已有现场观测供核对：
3791416_0 / DOL → JobIDRaw3791417，4核810秒；
3791416_1 / EC → JobIDRaw3791416，4核1004秒；
3808874_0 → 4核107秒。
必须以原始证据和实际任务列表验证，不照抄本提示词数值。

核时=AllocCPUS*ElapsedRaw/3600。不能按返回顺序连接，不重复计父/.batch/.extern。原始调度记录和解析字段归档。
首轮7.605556CH和所有历史费用保留。未舍入值求和、最后格式化；缺失不补零，不用p90或最坏预留结算。
旧DEC显式不完整费用继续明确范围，不把本批修复表述为全项目费用零缺失。

若需现场查询，按whu-hpc技能：在E:\软件\超算连接读AGENTS.md、doctor通过后只走hpc.ps1桥。仅查询，不据此新增任务。

五、L02：EC机器合同必须可执行

固定对象：EC/LiM_2plus；最多两次实际提交，p4→p7。
新profile：orca_production_4h_v1，4核、4小时、16CH/元素、campaign总帽32CH。

当前已知缺口：
- attempts_ledger_required=False，必须对本新profile改为True并验证漏账本被拒。
- 提交器只管全账户上限，必须验证本EC campaign串行一次在飞。
- first_batch_reserved_core_hours不得低报本新ORCA元素真实预留。
- 草案仍有p8/p3/p5/p6递补条款，删除自动递补语义，仅保留候选reserve。

提交前同一机器合同验证：
candidate在[p4,p7]；profile正确；cores=4；wall=4；
candidate必须等于从完整campaign历史推导的下一候选，不能先投p7或在p4已accepted后投p7；
本EC无其他pending/running/submitting；
本EC已实际提交元素数<2；
已结算费用+所有未结算预留+新16CH<=32CH；
新预留等于4*4*实际元素数；
用户有效授权覆盖本次元素。

实际提交次数与科学尝试次数分开记录。两次提交硬帽下不自动追加第三次技术补投。技术失败照计实耗；拒绝前未提交不冒充已计算。
提交响应未知保守占用次数和预留；只有journal与Slurm共同证明未被接收才解除占位，不能因网络超时、客户端错误或缺JobID就释放。
所有包共用本campaign费用与次数账本，不通过换目录重置。
保留历史profile和旧批次行为，仅对本新合同加明确守卫。

六、L03：EC候选资料变成真实HOLD执行包

候选资料：work/hpc_ec_recovery_v2_20261028/manifest.json。
现有子目录：
work/hpc_ec_recovery_v2_20261028/EC/LiM_2plus__ec_v2_p4/
work/hpc_ec_recovery_v2_20261028/EC/LiM_2plus__ec_v2_p7/

真实父几何：
work/hpc_dol_ec_recovery_v1_reopt_20261027/tasks/EC/LiM_2plus__p4_02_ring_pucker_twist/snapshots/3791416_1/job.xyz
SHA256=a0a8d53b1e6083c4212d98d844350ce3248c38d201b82f9f3f40936341cd969b

修正草案不存在的简写父路径。6c711c4e开头的几何不是本次reopt输出。
当前候选manifest的profile字段不等于提交器resource_profile；当前资料不能直接按24h默认提交。

建立只含active p4的独立执行包：
- 冻结方法Opt/AnFreq输入，charge/mult来自权威账本；
- members、batches、tasks.txt、batch_1.txt、batch_1.sbatch；
- resource_profile、授权引用槽位、公共费用账本、完整输入哈希；
- source_kind及member_role通过全部消费者，沿用支持的recovery_v1_start；
- 候选几何门、拓扑/身份、非刚体和历史起点重复性留证。

p7和其余候选保留reserve。不要先把p7放进正式planned集合或可发现生产任务，再不提交它，造成pending永远不清。
可准备p7模板；只有p4明确最终失败、授权覆盖且预算与串行条件满足，才激活并创建其执行包。

真实验证必须调用_load_package、submission_resources、declared_task_cores及importer发现/身份解析，不用自造字典绕过缺sbatch测试。
样例终态用隔离fixture验证，不伪造生产输出。

负向测试至少覆盖：漏账本、错profile、第三腿、偷换候选、先投p7、p4已accepted仍投p7、低报预留、并发第二腿、错父哈希、重复任务、未知提交释放占位、备用误入pending。
本地准备完成即READY_HOLD。没有计算授权仍继续后面任务，不重复每轮询问。

七、L04：DMC日志过程解析与图

逐态收集已登记全部attempt和日志，按日志哈希去重，区分superseded与独立计算。
优先复用现有解析器；若只有末值接口，可扩展纯本地过程解析。新增脚本按仓库规则登记。

输出：
DMC_OPTIMIZATION_TRACE.csv
DMC_FAILURE_MATRIX.csv
DMC_MECHANISM_DECISION.md
输入哈希索引及两态过程图。

轨迹字段至少：state/member/attempt/job/log_sha、优化任务段、cycle、源行号、E、abs(deltaE)、RMSG/MaxG/RMSD/MaxD、单位、阈值与比值、SCF状态、缺失原因。
按真实表头解析，TolE绝对值；区分一个优化中的多张表和多个优化任务。首点收敛、缺字段、多优化段、异常日志、重复别名必须能解释，不能补零。
画末若干步五准则相对阈值及能量变化。用已有数据检验“持续平台/周期变化/偶发末步超差”，不能仅因一次失败就断言浅平坦谷或无解。
解析测试要用真实报文结构和反例，不能只测与实现同形的数字表。

八、L05：DMC形成有证据的下一实验

对M_plus和LiM_2plus分别比较：
A Li配位+短程预优化（只适用于有Li的态）；
B 更紧GFN2预优化；
C 不经廉价预优化的直接DFT起点。

每项必须回答：
1. 历史实际做了什么，引用文件和参数；
2. 这次具体改变什么，不能旧P4换名；
3. 为何针对已观察到的失败过程；
4. 哪项观测支持/否定假设；
5. 最终如何回到冻结科学目标验证；
6. 需要何种对照；
7. 候选数、预期费用、最坏预留、预算、停止条件；
8. 失败的交付与终止条件。

若证据不足以推荐任何选项，明确作出“不建议当前增加计算”的结论并列出真正缺的证据。不能为了给用户A/B/C选择而假装已有机制。
修改优化算法不自动要求全cohort重算；改变最终电子结构/介质/数值目标必须评估可比性。
本轮不跑xTB预优化，不创建可发现的DMC新生产包，不占用所谓救援余额。

九、L06/L07：研究分析继续推进

WP3重建pair、翻转阶梯、Top-k及受限区间，解释AN/DOL修正对结论的实际影响。若缺失态仍可改变全池Top-3，报告该限制。

WP5从最终labels重建目标池和费用：
- A=free氧化；B=Li条件相对free位移，核对四腿与恒等式；
- accepted准入、模型与acquisition显式记录、训练内预处理、可见标签隔离；
- 同repeat共享初始集合；稳定种子；
- 成本含初始标签、free前置、失败救援及共享作业去重；MISSING保持缺失。

当前停止算法已有joint实现，不重新发明算法：
同20 repeats至少16个在n和n+1均满足O3>=2/3且Top-3集合均值regret<=0.10eV，两点均未耗尽，报告n+1。
每点各16但交集不足16不得通过；平均端点不替代经验预算。

完整目标池已评估、模型是否成功、是否比随机节省费用是不同结果。not_reached合法，不能把全池门改成“所有策略都成功”。
A11/B10保留子池声明，不能过A12/B12验收。当前19computed/13not_reached只是待复核快照。
分析策略/模型差异、成本与未查询误差，负结果如实报告，不加策略直到出现希望的优势。

十、L08/L09：采样、锚点、报告和主图

3→6完成登记、QC、去重、差异及限制处置；生产采样收敛仍未证明。不得用GFN2的1kcal/mol容差判生产采样过门。
WP4锚点不足保持validation limitation，并明确可比性范围。
WP6和扩池重新读取动态门，当前未触发不得提前算。

对照主文§16列六件交付/六图：图号、问题、输入、脚本、源哈希、结论、限制、当前状态。已有合适图复用；不为凑数画无研究内容的图。
报告至少覆盖：研究问题、方法证据、45/48、AN/DOL路线、三态限制、WP3、WP5、费用、采样与外部验证边界、复现和后继实验。
新阶段结果用新日期报告或明确附录，不静默覆盖旧历史报告。

十一、L10：重建、检查与一致性交付

使用现有依赖链：原证据/费用→QC/处置→去重/覆盖/系综→采样/目标池→WP3/WP5→合规→图/报告/站点/镜像→归档。
已有覆盖/聚合固定点机制继续用，不另造第二套标签权威。
先运行受影响定向测试，再整链。示例入口：

.\.venv\Scripts\python.exe -B -m pytest tests/test_submit_hpc_batch.py tests/test_evidence_gate_and_cost.py tests/test_resolved_route_evidence.py tests/test_strict_readiness_strict.py tests/test_cost_scope_plumbing.py -q
.\.venv\Scripts\python.exe -B scripts/wp_production/build_coverage_reviews.py --check
.\.venv\Scripts\python.exe -B scripts/wp_production/build_production_ensemble_aggregator.py --check
.\.venv\Scripts\python.exe -B scripts/wp_production/strict_readiness_wiring.py
pwsh -NoProfile -File scripts/wp_production/finalize_wp2.ps1
git diff --check

只读check失败后修根因，不能手改产物或测试预期掩盖。
离线链与真实ORCA/xtB集成分开报告。当前整链引用work/_converge_acceptance.py；确认克隆环境如何获得本地依赖，缺失要响亮说明。
归档按其声明的原始字节或LF归一化规则验证，不因混用口径误报漂移。

共享树不运行finalize -Commit（它会广泛git add -A）。Lead按归属白名单暂存，检查cached diff，沿用有效发布授权提交/推送；否则交付发布候选。不混入他人文件、不强推。
外部“核心文件”不在此Git仓库，本执行补充在docs/plans内用于版本追踪；报告说明两处关系。

十二、L11/L12：仅在EC具体计算授权有效时

进入计算前验证：授权覆盖p4/p7、32CH、次数和profile；账本、真实输入、远端哈希、桥doctor、实时容量、journal通过。
提交p4一次，留唯一JobID。若返回不确定，查journal/squeue/sacct及日志，不重投、不自动删除锁。
健康无变化保持安静，发生完成、失败、超时或需动作再报告。使用产品等待机制而不是高速循环。

终态完整回收输入/日志/末几何/Hessian/轨迹/stderr/时间/调度证据，按哈希关联。
完整QC、身份、去重、搜索范围和覆盖验收通过则EC结束，p7维持reserve。
p4有明确最终失败且授权包含p7、预算+预留合规、无本campaign在飞，才激活p7。
缺日志、映射不明或提交未知不是最终失败，先补证据。
p7结束后无论成败终止本campaign，不从其他四个备用递补。
每条腿结算实际费用、释放相应预留；新几何不拼接旧Hessian/热化学。

十三、L13/L14：真实终态与结束

有新结果则同轮重建下游。EC通过最高46/48，失败保持实际数；DMC不因此复活。
若未来真的48/48：重新评估完整A/B池及正式回放、采样/身份/成本与WP6/扩池触发。48/48本身不自动关闭所有核心计划闸门。
WP6在Li配对>=9/12且accepted48/48触发；扩池按自身门。已触发任务需要实际完成证据和明确预算；未授权计算不能自行提交。

本轮最终交付放在明确新目录并登记：
1. BASELINE与输入哈希索引；
2. TASK_STATUS（L00-L14及证据，不填假通过）；
3. 费用元素映射与结算核验；
4. EC固定候选合同、HOLD包验证及一次具体审议材料；
5. DMC逐步轨迹、失败矩阵、诊断图和机制决策；
6. WP3/WP5变化与限制、六件交付/六图映射；
7. 阶段最终报告、测试/检查结果、镜像/页面、Git归属与版本；
8. 下一轮需要的具体授权或证据；已有明确授权不重问。

完成本地任务后，无EC新授权可以按READY_HOLD结束该准备分支，并完成本goal的阶段交付。不得仅因严格48/48仍未达成就无限续跑。
最后汇报：完成事项、关键科学结果、验证范围、文件链接、提交状态、真正剩余门。不要再输出没有新证据的第N轮重复审计。
```
