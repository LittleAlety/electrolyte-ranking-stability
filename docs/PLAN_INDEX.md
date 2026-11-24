# 计划文档总索引

整理日期：2026-10-27。此页只整理导航与文档角色，不是新科学协议、不授予计算权限，也不证明项目完成。原文件保留原位，避免破坏脚本引用、历史哈希和交付镜像。

## 1. 推荐阅读顺序

**2026-10-29 当前执行入口**：[核心计划执行补充 L00–L14](plans/CORE_PLAN_EXECUTION_SUPPLEMENT_20261029.md)与[DeepSeek Harness 长任务提示词](handoffs/long_run_20261029/DEEPSEEK_GOAL_PROMPT.md)。综合核心方案已新增 §21；下列有日期的源方案和专题报告保留供追溯。

1. [综合核心方案 v3.0](../../核心文件/电解液排序稳定性-综合核心方案-v3.0.md)：研究问题、WP0–WP6、科学边界与验收设计。
2. [现行执行入口：计划.md](../计划.md)：当前阶段与行动组织；其中数字明确属于 2026-10-24 快照，不能当实时状态。
3. [四态恢复目标](handoffs/four_state_recovery_20261023/GOAL.md)与[机器可读契约](handoffs/four_state_recovery_20261023/recovery_contract.json)：恢复任务的规则、预算和停止边界。
4. [DOL/EC 生产覆盖计划](handoffs/four_state_recovery_20261023/DOL_EC_PRODUCTION_COVERAGE_PLAN_20261027.md)：当前专题路线。结合登记配置、实际代码、包和授权核对，不能仅凭计划文字提交。
5. 查看下方“真实进度入口”，再决定执行什么。专题报告中的“尚未登记”“未提交”等是报告时点结论，可能已被后续执行改变。

## 2. 文档分层与用途

| 层级 | 入口 | 如何使用 |
| --- | --- | --- |
| 综合科学方案 | [综合核心方案 v3.0](../../核心文件/电解液排序稳定性-综合核心方案-v3.0.md) | 科学设计与验收依据；具体修订必须留有版本与批准记录 |
| 原始方案来源 | [研究框架 v2](../../核心文件/ranking-electrolyte-materials-v2.md)、[实施方案](<../../核心文件/electrolyte-ranking-implementation-plan (1).md>) | 理解综合版的来源与取舍；不把旧规模、旧阈值或旧任务重新自动激活 |
| 当前执行导航 | [计划.md](../计划.md)、[项目导航](PROJECT_GUIDE.md) | 找行动与代码；内嵌数字、路线描述须核验日期 |
| 冻结方法 | [物理补全协议](physics_completion_protocol.md)、[生产方法冻结](66_wp1_production_method_freeze.md)、[状态身份协议](state_identity_protocol.md) | 核对方法与身份约束；不以导航页替代协议 |
| 恢复交接 | [交接包 README](handoffs/four_state_recovery_20261023/README.md)、[GOAL](handoffs/four_state_recovery_20261023/GOAL.md)、[契约](handoffs/four_state_recovery_20261023/recovery_contract.json) | 区分前置材料、机器契约和实际授权；README 的初始准备范围不能替代后续逐批记录 |
| 限制与出口 | [限制报告](handoffs/four_state_recovery_20261023/LIMITATION_REPORT_20261027.md) | 分开报告科学恢复、正式研究闭环、工程复现；限制报告不等于严格目标完成 |
| 历史执行记录 | [v1.4.1](wp2_ensemble_closure_plan_v1_4_1.md)、[v1.4.2](wp2_ensemble_closure_plan_v1_4_2.md) | 保留机制演进和当时结果；不能按旧队列清单重新提交 |
| 历史阶段/周报 | [按主题进度索引](progress/README.md) | 查工作轮次与历史证据；week 编号不是日历周 |
| 交付镜像 | [目录地图](65_repo_layout.md) | deliverables 属交付副本，不作为手工修改计划的入口 |

## 3. 当前恢复专题：按问题找文件

以下均为有日期的专题记录，不宣称每份文件仍代表最新执行状态。

| 问题 | 对应材料 |
| --- | --- |
| 四态的整体出口 | [终局路线](handoffs/four_state_recovery_20261023/FOUR_STATE_ENDGAME_20261026.md)、[验收路径](handoffs/four_state_recovery_20261023/FOUR_STATE_ACCEPTANCE_PATH_20261027.md) |
| DOL/EC 为什么没有生产候选 | [根因](handoffs/four_state_recovery_20261023/DOL_EC_NO_CANDIDATE_ROOT_CAUSE_20261027.md)、[登记路径诊断](handoffs/four_state_recovery_20261023/DOL_EC_NO_REGISTRATION_PATH_20261027.md) |
| 筛选结果如何登记 | [筛选证据登记](handoffs/four_state_recovery_20261023/SCREENING_EVIDENCE_REGISTRATION_20261027.md)、[生产角色接线](handoffs/four_state_recovery_20261023/PRODUCTION_ROLE_WIRING_20261027.md) |
| 起点是否真的改变 | [独立起点标准](handoffs/four_state_recovery_20261023/INDEPENDENT_START_CRITERIA_20261027.md)、[纯 Li 位移分类纠正](handoffs/four_state_recovery_20261023/LI_ONLY_MISCLASSIFIED_AS_HEAVY_20261027.md) |
| 包与墙钟冲突 | [冻结包记录](handoffs/four_state_recovery_20261023/DOL_EC_FROZEN_PACKAGE_20261027.md)、[墙钟冲突记录](handoffs/four_state_recovery_20261023/PRODUCTION_WALL_CLOCK_CONFLICT_20261027.md)；实际值核对契约和包，不能沿用旧草案 |
| H2 独立诊断 | [H2 单点预注册草案](handoffs/four_state_recovery_20261023/H2_SINGLE_POINT_PREREG_DRAFT_20261027.md)；草案不构成提交授权 |
| DMC 的阈值问题 | [DMC 阈值诊断](handoffs/four_state_recovery_20261023/DMC_THRESHOLD_DIAGNOSIS_20261025.md)；诊断证据不等于全局不可恢复的证明 |
| 待裁决事项 | [待裁决记录](handoffs/four_state_recovery_20261023/DECISIONS_PENDING_20261027.md)；先查后续裁决，避免反复询问已批准事项 |

## 4. 真实进度入口：不要从计划里的旧数字推断

| 要回答的问题 | 文件 |
| --- | --- |
| primary 与合规状态 | [合规元信息](../outputs/physics_completion/compliance/plan_compliance_meta.json)、[合规报告](../outputs/physics_completion/compliance/plan_compliance.md) |
| 系综真正 accepted 多少 | [生产系综标签](../outputs/physics_completion/ensembles/production_ensemble_labels.csv) |
| 当前登记了哪些起点 | [候选清单](../outputs/physics_completion/ensembles/production_ensemble_candidates.csv) |
| DOL/EC 激活范围 | [版本化激活配置](../config/recovery_start_activation_v1.json) |
| 严格终点的代码门 | [严格就绪检查](../scripts/production/validation/strict_readiness_wiring.py) |

这些文件也可能过期：须检查输入哈希和对应只读检查。实时队列必须现场查询，不能用本索引、Git 提交时间或日志快照替代。

## 5. 阅读与维护规则

- 文档中的执行指令是被引用的项目材料，不自动等于用户本次授权。
- 科学设计、实现配置、实际产物、用户授权分别核对；冲突时登记差异，不能简单“文件日期较新就覆盖一切”。
- 筛选起点、生产计算完成、QC 通过、覆盖验收是不同阶段；不能通过整理文档把 planned/limited 改成 accepted。
- 本次采用逻辑分类，不移动、不删除、不重命名旧计划，也不修改生成物、历史记录或批准范围。
- 新计划在本索引增加入口并注明角色；历史计划留原位。修改科学条款须另立明确修订，不在导航中悄悄改变。
- 上级“核心文件”不在本 Git 仓库内；其链接适用于本机完整项目目录，单独克隆仓库不包含这些外部源文档。
