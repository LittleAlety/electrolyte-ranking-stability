# WP2 生产系综收口执行补充计划 v1.4.1

本计划承接 v1.4，针对首批救援已提交、生产系综聚合器已有初版后的验收缺口安排下一步。目标是让计算、结构 QC、采样完成度、系综标签和合规闸门具有一致且可复算的含义。

更新日期：2026-10-17。本次更新采纳 accepted=8/48、provisional=40/48 的本地快照，并将 P0 剩余重点收敛到原子映射、真实去重及检查证据完整性。

本文件是执行计划，不是完成报告。本文没有提交新作业、取消既有作业、修改计算协议或修复生产代码。作业 3719664、3719665 已回收及第二轮 3720238 已提交的状态来自用户交接；本次未查询远端，执行前仍需通过命令桥核实最新状态与真实输出。

## 1. 当前基线与证据范围

### 1.1 本轮本地核验

| 项目 | 本轮读取结果 | 正确解释 |
| --- | --- | --- |
| 主生产运行 | 60/60 | 原生产腿运行计数 |
| 主态科学验收 | 48/48 | 已有主态代表结构的验收计数 |
| 主态 meta 时间 | 2026-10-17T10:01:58Z | 该时间对应生成快照，不是当前超算时间 |
| 系综结构表 | 48 ready、7 computed、43 pending、7 technical_complete_qc_failed、9 superseded | 含不同 attempt 的行数，不可直接相加为独立结构数 |
| 现存失败分类 | 7 verytight_convergence | 新结果需回收后按逐项准则重判 |
| 生产系综标签 | 48 行；accepted=8、provisional=40 | 正式计数已与数值可用性分开；去重完整性仍需下述复核 |
| 系综合规项 | partial，accepted=8/48 | 不再因占位标签提前通过 |
| WP6 | gate_ready=false、scope=optional、executed_jobs=0 | 当前关闭，继续等待正式验收 48/48 |
| 总结题闸门 | blocked_on_production | 项目仍未完成 |

权威输入包括：

- `outputs/physics_completion/compliance/plan_compliance_meta.json`：主生产实时与固化进度；目前哈希范围不覆盖完整系综依赖，不能据其 stale=false 推断系综最新。
- `outputs/physics_completion/ensembles/production_ensemble_candidates.csv`：登记的逻辑成员。
- `outputs/physics_completion/ensembles/production_ensemble_structures.csv`：成员及 attempt 的 QC 结果。
- `outputs/physics_completion/ensembles/production_ensemble_labels.csv`：当前聚合结果。
- `outputs/physics_completion/ensembles/production_ensemble_index.json`：当前聚合输入与输出索引。
- `scripts/wp_production/build_production_ensemble_aggregator.py`、`build_plan_compliance.py`、`finalize_wp2.ps1`：生成与验收实现。

最新交接报告 importer 16 测、aggregator 21 测、compliance 27 测及 finalize ALL GREEN；本次文档更新未重新执行这些测试。现有测试通过只能证明其覆盖的行为，不能替代等价原子映射、真实拓扑及证据完整性测试。

### 1.2 已实现成果应保留

- 原始字节哈希与跨平台换行问题已有明确处置。
- AnFreq 的零 `$act_energy` 和坐标系变化已有专用处理思路。
- DOL 最大循环耗尽已有独立分类及 continuation 包。
- 8 条能量阈值超标结构已有独立 reopt 包。
- 聚合器已有数值稳定的自由能求和初版与成员权重输出。
- 原始主态账本及 canonical AnFreq 证据链已建立，后续系综工作应与其来源绑定。
- 三维状态字段、候选完成度计数、accepted 合规消费和 WP6 关闭已在产物中体现。
- primary 与 extra 已共同参与去重，四原子扭转及周期角差已有实现；AN/M seed34 与 primary 被合并为同一个极小。
- `partition_sum_relative` 与归一化 `weight_sum` 已分列。
- 聚合器 `--check` 分支已移至写盘之前；finalize 已加入 `prod-ensemble` 和 `check-prod-ensemble`。

### 1.3 数值汇报纠正与科学解释边界

从实际标签读取的 `G_min − G_ensemble` 为：

| 状态 | 当前成员数 | 降低量（kcal/mol） |
| --- | --- | --- |
| DMSO/M | 2 | 0.408850 |
| SL/M | 2 | 0.406210 |

此前“SL 约 0.8 kcal/mol”的表述错误，应统一更正。对于 N 个独立成员、g_i=1，必有 `0 ≤ G_min − G_ensemble ≤ RT ln N`；在 298.15 K、N=2 时上限约 0.411 kcal/mol。当前数值符合该界限。

上述两行仅证明当前聚合器保留了两个成员，尚不能确认是两个独立极小。当前 RMSD 和扭转比较仍依赖原子顺序；应按 §3.1 的等价原子映射复核后再做物理解释。接近 RT ln 2 既不能证明重复，也不能证明独立，不按自由能增益大小选择去重结论。

## 2. 必须先修正的口径

### 2.1 区分“有数值”与“采样任务完成”

单成员系综在数学上成立，满足 `G_ensemble = G_single`。合法的 N=1 结果不应被一概拒绝；但登记的其他成员尚在排队、运行、未回收或待救援时，仅用 primary 得到的数值必须标为 provisional。

不能将 `n_members >= 2` 当成新的验收阈值。真正的条件是：登记采样已完整核对、所有候选有可追溯处理结果、去重与 QC 已执行、未解决问题已按既定停止规则处理。

已落地的三个维度继续独立登记：

| 字段 | 状态约定 | 用途 |
| --- | --- | --- |
| numerical_status | available / unavailable | 当前是否可计算基线或系综数值 |
| sampling_status | pending / in_progress / complete / sampling_limited | 登记的采样工作是否完成 |
| acceptance_status | provisional / accepted / limited / blocked | 是否可计入下游正式验收 |

`pool_limited` 不能仅由 N=1 自动推出。候选不足、去重后只剩一个极小、尚未计算、QC 全失败是不同原因，应另设 `limitation_reason` 和候选处置计数。

每态至少输出 `n_registered`、`n_pending`、`n_qc_passed`、`n_qc_failed`、`n_deduplicated`、`n_unique` 和 `n_unresolved`。计数按逻辑成员计算，attempt 数另列，避免重试增加样本数。

### 2.2 修正合规与 WP6 闸门

`wp2_conformer_ensemble` 必须根据有效的 accepted 状态集合和证据完整性计数，而非只读取 48 个 computed 键。必须验证主集恰为冻结的 12 分子 × 4 主态；缺键、重复键、错误身份、旧协议和失效哈希均不能计入。

WP6 继续使用既定条件：Li 配对 complete ≥9/12 且生产系综正式验收 48/48。当前已按 accepted=8/48 关闭闸门。后续去重或 QC 修订可能改变计数，必须通过生成器重新生成 WP6 状态，不手写合规 CSV，也不在未核实闸门前开始 WP6 新计算。

`sampling_limited` 是有效科学结果，但不自动等于完整采样验收。其数值可作为带限制的结果展示，是否满足具体交付条款由预先声明的规则决定，不得为了凑齐 48 而升级。

### 2.3 修正此前对 strict reopt 的过窄表述

此前“仅能量阈值未达标才可 strict reopt”的表述是执行计划的过窄限定。冻结协议要求检查五项几何收敛准则，因此通过其余科学 QC、但任一冻结几何准则超标的结构，都应进入有界严格重优化候选。

分类与补救动作分开记录：

| 科学/技术事实 | failure_criteria | 补救动作 |
| --- | --- | --- |
| ORCA 宣布收敛，TolE 超标，其余 QC 通过 | energy_change | 从自身最终几何严格重优化 |
| ORCA 宣布收敛，步长等冻结准则超标，其余 QC 通过 | rms_step / max_step / 其他实际超标项 | 同样从自身最终几何严格重优化 |
| 同时多项超标 | 列出全部超标项 | 保留全部证据后严格重优化 |
| 循环耗尽，频率未执行 | max_cycles_exhausted | 独立 continuation；完成优化后重新 AnFreq |
| 虚频、身份改变或连接异常 | 对应独立 QC 原因 | 不并入仅收敛阈值问题的自动补救 |

其余 5 条 verytight_convergence 需要逐项核实实际收敛表；不能因没有 close-enough 文案而遗漏，也不能假设重启首点必然满足全部准则。任何新的重试仍须用完整输出重新验收。

## 3. P0：先修复生产系综聚合与验收

### 3.1 去重实现

旧版唯一成员键阻断 RMSD、primary 未参与和扭转占位的问题已修复。P0 尚缺等价原子映射及相应的真实数据复核，不能把“能调用 RMSD”视为去重验收完成。

修复要求：

1. primary 与已通过 QC 的 extras 合并成同一去重输入集合。
2. 使用真实几何生成连接与配位特征；不能把成员 ID 当作结构特征。
3. 当前 `canonical_bond_signature` 是片段组成加元素对键的多重集合，仍不等于完整键拓扑。两图具有相同元素和键类型计数，不保证同构；需要元素标记的邻接图与原子映射验证。
4. 枚举或搜索保持元素、键连接及所需立体身份的合法原子映射，在同一映射下比较几何、配位和扭转；不得仅按元素任意换序，也不得让镜像反射通过旋转拟合。映射搜索若超过预注册资源上限，明确标记 mapping_unresolved，不能默认 unique。
5. 保持冻结的重原子 Kabsch RMSD 0.35 Å 和扭转角差 10°。四原子二面角使用映射后的原子索引；同一判定需在同一合法映射下同时满足 RMSD 与扭转条件。新增重原子映射不能遗漏氢相关扭转的对应关系。
6. 在同一重复簇内按预先固定、可复算的规则选代表，例如最低 G 加稳定 ID 排序；保留 primary 的历史身份及重复映射，不因其是 primary 而重复计数。
7. 缺几何或几何哈希不符时，标记 dedup_blocked，禁止默认为 unique。

验收应包含 primary-extra 重复、extra-extra 重复、旋转平移、等价原子换序、同组成不同连接、相同齿数不同给体、二面角跨 ±180° 和缺失几何等案例。

当前 `li_donor_set` 只返回接触给体的元素集合，不能单独证明给体原子身份相同。应在合法映射下比较实际给体位点；对称等价给体允许对应，不等价位点不能因元素同为 O 而合并。

针对 DMSO/M 与 SL/M，交付一份逐对复核表，列出源几何 SHA256、合法映射、拟合旋转的行列式、最佳重原子 RMSD、对应扭转差、配位比较、代表选择及最后决策。AN/M 作为已有重复正例一并回归。若确认重复，保留最低 G 代表并重算；若确认不同，保留两个成员及可复核证据；证据不足则标记 provisional/dedup_blocked。禁止手工把两个状态判为重复或独立。

等价原子换序测试应使用同一合理几何的重新编号；不同构象测试应使用同一拓扑下的真实构象差异。不能仅把 C–C 距离从 1.2 Å 拉至 2.0 Å 来证明构象去重正确，因为该变化可能改变键拓扑。

### 3.2 成员选择与 attempt

一个逻辑成员只贡献一次统计权重。旧失败 attempt 保留在结构表中，明确 selected_attempt 与 superseded_by；多个成功 attempt 也不能当作多个独立构象求和。

primary 和 extra 均须核对方法、基组、溶剂、charge/multiplicity、温度、频率方法、热校正规则、标准态约定及几何来源。中性 M 槽继续使用 M_tzvpd 同基组结果。只有相同状态定义与化学计量的成员可组成同一系综。

结构表的 ready/computed 标记不能替代关键字段验证；不得因旧行缺失温度而静默补成 298.15 K。旧证据允许通过明确迁移记录补齐，不能凭空生成。

### 3.3 公式与字段语义

维持方案 §6.2：

\[
G_{\mathrm{ens}}=G_{\min}-RT\ln\sum_i g_i\exp[-(G_i-G_{\min})/(RT)]
\]

\[
w_i=\frac{g_i\exp[-(G_i-G_{\min})/(RT)]}{\sum_j g_j\exp[-(G_j-G_{\min})/(RT)]}
\]

- 温度为冻结的 298.15 K，能量单位转换集中管理。
- 默认 g_i=1；如支持其他值，必须读取登记证据、实际用于计算，并在输出中保持一致。
- 已分列 `partition_sum_relative`（Q）和 `weight_sum`（Σw_i），保留两者各自的回归断言。
- 增加 `0 ≤ G_min − G_ensemble ≤ RT ln N` 的 g_i=1 测试；有已登记简并度时上界为 `RT ln Σg_i`。DMSO/SL 报告直接从标签计算，避免人工抄写误差。
- 所有数值必须有限；拒绝 NaN、Inf、非正温度及非正或非法简并度。
- 同一极小重复出现不能获得额外的 −RT ln 2 稳定化。
- 保留 raw E、热校正、qRRHO 设置和标准态项的来源。若项抵消，记录抵消条件；不能只因数值可相减便假定模型一致。
- G_ensemble 与 Σw_iG_i 含义不同，如两者都输出必须分别命名。

### 3.4 完整性与 provisional 标签

构建时连接候选 manifest 与结构账本，逐一核对登记成员。缺失、待运行、正在运行、待回收、待救援、已排除、已去重及已接受均需要显式处置。

可以继续输出 48 行 provisional 基线供预览，但其 `acceptance_status` 不得满足正式系综计数。对于已完成全部登记搜索且最终只剩一个独立合格极小的状态，可以验收 N=1，并注明为何只有一个成员。

### 3.5 真正只读的 --check

当前 `--check` 已在写文件之前返回，避免了旧版检查时重写产物的问题。剩余检查项包括：index 不存在时必须失败；完整证据依赖必须进入索引。源码当前仅在 index 存在时检查其内容，缺失 index 没有加入 failures；输入哈希也只显式覆盖 structures 与 candidates 两份 CSV。

要求将“纯计算预期字节”和“写文件”分离：

1. `--check` 在内存中计算预期输出，读取磁盘现有文件比较。
2. 成功、失败、缺索引等路径均不修改产物内容或修改时间。
3. 索引覆盖结构账本、候选清单、冻结主集、协议/去重配置、实际使用的几何及相关生成器版本或代码哈希。
4. 仅将生成时间排除在确定性内容比较之外，继续校验 index 的 inputs、outputs、rules、schema、计数等有效字段；缺 index 必须报错。构建失败时不发布半套新产物。
5. 无法验证输入证据时 fail-closed，不能仅信任 index 内的 stale=false。

必测：标签被改但输入未变；几何被改但结构 CSV 未变；候选 manifest 变化；删掉任一产物；索引损坏；连续两次失败检查均保持磁盘原样。

### 3.6 接入 finalize

本次确认 `finalize_wp2.ps1` 已加入生产聚合生成与 `check-prod-ensemble`，原接入缺口已闭合。保留 GFN2 筛选层和生产层的独立命名，继续核对其上下游生成顺序和新增证据依赖。

应按依赖关系接入：

```text
已回收且校验的原始证据
  → 系综 importer / attempt 选择
  → 生产聚合器（provisional 与 accepted 分开）
  → 生产自由能标签与 flip ladder / WP3
  → compliance / WP6 闸门
  → 报告、图、镜像、Pages
  → 所有只读 --check + 归档复算 + pytest
```

常规 finalize 可以成功生成诚实的 incomplete 状态；另设明确的“结题验收”检查读取科学闸门。工程检查通过与研究方案完成必须分别输出。

## 4. P1：继续超算生产与救援

### 4.1 先核实已提交救援

交接报告：3719664（8 条）及 3719665（DOL 1 条）共 9 条已回收；其中 7 条 QC 通过，GBL/DOL 仍需救援。3720238 为第二轮 7 条 reopt，成员为 EMC/M/57、DEC/M/3、PC/M/25、DME/M/14、DME/M/22、GBL/M/2、DOL/M/15。

下一次超算执行按 whu-hpc 技能先 doctor，再经桥优先检查 3720238，并对照前两作业的已存终态与哈希。本次文档更新没有查询远端实时状态，不能把交接中的运行/排队数当作当前值。

对已提交任务只回收、诊断并登记，避免同一个逻辑成员重复提交。远端正常终止标记与零退出码均不能覆盖循环耗尽、明确错误或不完整频率。

### 4.2 补齐首批终态和剩余 5 条处置

- 核对第一批 18 个原任务与所有救援 attempt 的最终文件，修正本地遗留 pending。
- 原 5 条 verytight_convergence 已据交接纳入 reopt2，加上 GBL/DOL 共 7 条；核对提交 journal 与 manifest 后回收，不重新提交同一成员。
- 已提交 8 条 reopt 和 DOL continuation 的 manifest 不再原地修改。
- reopt2 包必须登记五项数值/阈值、源最终几何、来源日志哈希和补救理由；不能只登记 failure_criteria 名称和 energy_change_Eh。
- 不删除旧包。需重建时使用新版本目录或明确归档，保留已提交输入的可追溯性。

### 4.3 DOL 专项

原 DOL 日志同时出现正常终止文本和最大优化循环耗尽错误；据此登记 max_cycles_exhausted 正确。其 continuation 从轨迹选帧的规则、帧号、能量、轨迹哈希和新起点哈希均须绑定。

对交接中的 frame 49、−268.55301391 Eh 先复算，再作为已验证事实使用。MaxIter 200 只是提高循环预算，不降低任一收敛阈值。完成后要求严格优化、完整 AnFreq、零虚频、身份/连接与热化学 QC；再次失败按停止规则报告，不无限续算。

### 4.4 后续 18+18+3 批次

始终通过仓库提交入口与受保护命令桥操作，提交前持锁核对账户范围的真实运行+排队数量和已有提交 journal。18 元素数组提交时须满足当前活跃数 ≤2；其他批次同样保证提交后总数 ≤20。

救援与下一批共享同一账户额度。以实际活跃数核算下一次提交，不能把已提交的 reopt2 当作未占名额。映射代码修复与既定超算任务回收可同步推进；结果的正式接受须等待相应去重验证。

每个包在上传前检查输入、manifest、核数、时限、OpenMPI 环境和哈希；每批回收即 QC。所有 ORCA/xtB 仍仅在超算执行，本机做轻量解析、生成与测试。

## 5. P2：采样审计与科学下游

### 5.1 完成 round-1 状态验收

对冻结的 48 个状态逐项核对已登记成员是否全部有处置，完成 QC 后去重并聚合。报告 accepted、provisional、limited、blocked 的状态数及原因，不预先写死 accepted=48。

不要因某态未出现多成员就再造任务，也不要因单成员基线可算就忽略原定 extras。重复搜索同一极小计一次；失败成本和排除原因全部保留。

### 5.2 对 EMC/DEC/DME/TMP 做 3→6

- 固定四个审计分子及四个主态，先核对候选与独立种子覆盖，补齐 Li motif 搜索缺口。
- 每态最多 6 个结构，遵守冻结的窗口、连接/配位/RMSD/扭转规则。超窗候选仅可留作候选记录，不能无说明进入任务包。
- 比较 3→6 的 ΔG_ensemble、pair gap、Top-k 和 regret；用独立 tolerance 判定，不从目标翻转结果反推阈值。
- 若没有足够独立候选，记录搜索证据和实际数量，不复制构象凑足 6。
- 严格遵守原方案的有界追加轮次；预算耗尽仍不稳时记录 sampling_limited。

### 5.3 重建 WP3、WP5 与 WP6

用正式可比较标签更新 free/Li 氧化差、coordination shift、flip ladder、pair evidence 和机制案例。frontier localization、密度/自旋及配位变化等独立缺项需另补证据，不因系综完成自动通过。

WP5 必须用新目标标签重跑有查询隔离的回放与成本统计。旧回放缺失预测或成本历史时继续显式标缺失；不能用新增标签回填未保存的历史证据。8–12 个分子的扩样只在目标标签、独立 uncertainty 与无泄漏回放就绪后按原方案先冻结再计算。

WP6 只有在修正后的闸门真实通过时启动；登记 4 个分子的比较案例，并明确每个案例氧化前后态及 motif 数量。“4 案例”不是“4 个 ORCA 任务”，实际包大小由复用证据和状态矩阵确定。

## 6. 验证矩阵

| 层 | 必须验证的行为 | 通过含义 |
| --- | --- | --- |
| 导入 | 正常终止+错误并存仍拒收；max-cycles 提前分类；半截日志 pending | 状态分类可信 |
| 几何 | 能量、梯度、步长逐项核对；超标项完整保留 | 不靠 ORCA 文案替代冻结准则 |
| Hessian | 空行、零能量占位、旋转平移可处理；错误单位/元素/内部几何拒收 | AnFreq 证据联动可信 |
| 退化测试 | 旧 mixed restart 仍检查实际几何混用原因 | 输入早期拒收没有掩盖原有回归风险 |
| 成员 | 重复 attempt 不重复计数；错误方法/温度/身份拒收 | 目标定义一致 |
| 去重 | primary-extra、extra-extra、合法等价原子映射、同拓扑异构象、非同构反例、镜像、对应扭转 | 独立极小不被重复计权 |
| 数值 | 单成员、两成员、RT ln N 界限、极大能差、非法值、已登记简并度 | 公式与单位可靠 |
| 完成度 | 有 pending extras 时 provisional；合法完成的 N=1 可验收 | 数值可用与采样完成分开 |
| 检查 | 篡改/缺文件/缺 index/几何单独变化时报错且不写盘 | --check 不自我修复现场 |
| 集成 | finalize 实际运行生产聚合与检查；WP6 不被占位值打开 | 下游读到正确状态 |
| 归档 | 从 canonical 原始文件复算字段与哈希 | 报告可复现 |

测试先运行 importer、aggregator、compliance、进度及收口链相关测试；对应缺陷修正后再运行全量 pytest。修改测试时不能只扩大错误消息正则让旧测试通过，需保留真正的行为断言。

## 7. 执行顺序与交付清单

### 第一阶段：P0 剩余修复与已完成基础

已勾选表示当前代码/产物可见该能力，不代表其所有边界测试均已独立复跑。

- [x] 连接候选 manifest，输出 provisional/accepted 和完成度计数。
- [x] primary 与 extra 共同去重，四原子扭转与周期角差已有实现。
- [x] 分离 partition_sum_relative 与 weight_sum。
- [x] --check 在写盘前返回，compliance/WP6 消费 accepted，finalize 接入生产聚合与检查。
- [ ] **优先：实现保持拓扑与身份的等价原子映射，以及映射后的 Li 给体和扭转比较。**
- [ ] **复核 DMSO/M、SL/M 和 AN/M，输出映射证据并重新判定独立成员。**
- [ ] 修复缺 index 的检查漏报，将几何、配置、主集及代码版本等实际依赖纳入证据索引。
- [ ] 完成模型/温度/简并度及 RT ln N 界限回归；补充合理几何的去重测试。
- [ ] 重建标签、权重、去重表、compliance、报告与 Pages，纠正 SL 的 0.8 kcal/mol 表述。
- [ ] 定向测试通过后重跑 finalize 与全量测试；accepted 计数允许据证据变化，不锁死为 8。

### 第二阶段：完成计算与回收

- [ ] 经桥核对 3720238 并回收终态；对照 3719664/3719665 的已回收证据。
- [ ] 修正首批遗留 pending，核验 reopt2 七条成员及五项收敛证据，不重复提交已有作业。
- [ ] 按账户并发门禁依次推进余批 18+18+3。
- [ ] 每批完成后重建结构表、聚合与来源索引。

### 第三阶段：科学闭环

- [ ] 完成 round-1 登记采样处置及 48 态正式验收核对。
- [ ] 完成指定四分子的 3→6 及停止规则登记。
- [ ] 更新 WP3、WP5 和符合闸门的 WP6，保留独立未闭合项。
- [ ] 重建归档、报告、镜像、网站，验证全部 --check 与 pytest。
- [ ] 仅在交付集合一致且既定验收满足后执行一次性一致性提交；本计划不执行 commit/push。

## 8. 后续进度汇报模板

```text
核验时间：<带时区时间>
超算：running=<n> pending=<n> terminal=<n>；证据=squeue/sacct/日志
原主生产：运行 <n>/60；主态科学验收 <n>/48
系综补充成员：登记 <n>；未处置 <n>；QC通过 <n>；失败 <n>；救援中 <n>
系综状态：numerically_available=<n>/48；accepted=<n>/48；provisional=<n>/48
去重：完成 <n> 态；重复极小 <n>；缺证据 <n>
3→6：完成 <n>/16 个审计状态；sampling_limited=<n>
WP6：gate_ready=<true/false>，依据=正式 accepted 计数
检查：只读 --check=<结果>；pytest=<结果>；归档复算=<结果>
本轮变化：<有证据的新增进展>
下一步：<明确的动作、依赖与停止条件>
```

当前可引用的表述是：“原主生产代表结构已验收 48/48；系综账本当前 accepted=8/48、provisional=40/48，WP6 关闭。DMSO/M 与 SL/M 在当前算法下各保留两个成员，自由能相对最低成员降低 0.408850 与 0.406210 kcal/mol；其独立极小身份仍待等价原子映射复核。第二轮救援、余批计算和 3→6 审计继续按计划推进，最终进度以重新生成的证据为准。”
