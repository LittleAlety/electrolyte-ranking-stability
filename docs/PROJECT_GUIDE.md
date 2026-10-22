# 项目导航、后续安排与核心代码

> 导航核对：2026-10-22。数字只是该次已提交产物的快照；最新状态以以下机器可读账本为准。本文不改变科学协议、阈值、预算或计算授权。

## 1. 从哪里看真实进度

| 问题 | 权威入口 | 读法 |
| --- | --- | --- |
| 核心方案是否完成 | [合规台账](../outputs/physics_completion/compliance/plan_compliance.md) | `plan_overall_complete`，不能用工程全绿替代 |
| 48 个主态是否完成 | [主态元信息](../outputs/physics_completion/compliance/plan_compliance_meta.json) | primary 科学验收与运行完成分开 |
| 48 个系综是否可验收 | [系综标签](../outputs/physics_completion/ensembles/production_ensemble_labels.csv) | 只数 `acceptance_status=accepted`，不能只数数值行 |
| 已救回哪些、还卡哪些 | [严格恢复报告](../outputs/physics_completion/recovery/strict_recovery_v1_report.md) | 连同失败尝试、去重和覆盖复核一起读 |
| 前沿轨道与身份 | [全成员前沿报告](../outputs/physics_completion/frontier/frontier_localization.md) | 区分 AO 系数诊断与 FMO population 分类；不要混用两列权重 |
| 扩样是否收敛 | [3→6 差异](../outputs/physics_completion/sampling/sampling_3to6_diff.md) | 当前只报告差异，不判采样收敛；空缺不是零 |
| A/B 回放是否达到停止预算 | [A/B 端点](../outputs/physics_completion/active_learning/blind_replay/AB_axis_endpoint.csv) | 看池大小与 `stop_budget_status`，不拿历史 12 分子回放替代当前 accepted 子池 |

当前快照：primary **48/48**；系综 **43 accepted / 0 provisional / 5 limited**，严格目标尚未完成。
余下 AN/M_plus、DMC/M_plus、DMC/LiM_2plus、DOL/LiM_2plus、EC/LiM_2plus。
前沿解析与作业队列仍在更新，最新覆盖以其独立报告为准；本地回收快照不等同于实时队列。

## 2. 接下来怎么做（按依赖，不按口头完成度）

| 优先级 / 建议窗口 | 动作 | 完成证据 | 失败预案 |
| --- | --- | --- | --- |
| P0 / 第一天 | 先核对已有 frontier 作业与输出，回收缺失成员；不要因本地报告没变重复提交 | 全成员逐条有输出、输入/几何哈希与 population 来源；身份分类/报告同步 | SCF、解析、身份异常单列，不能以正常终止放行；AO 与 FMO 指标必须标明各自口径 |
| P0 / 第一天 | 五个 limited 态逐态决定生产级覆盖诊断 | 已批准的候选 manifest、独立性证据、预算、停止条件 | 冻结池耗尽不能原样再跑；新搜索须另行登记，不自动扩大计算 |
| P1 / 第二至四天，批准后 | 优先评估 AN/DMC 的 M_plus，再决定其余三条 Li 态是否值得扩展 | 新极小经过全套 QC，或生产级单盆地复现的覆盖复核 | AN 没有通常意义上的柔性重原子扭转，不能机械套用“扭转扫描”；需先验证搜索自由度是否存在。无可执行动作则保留 limited |
| P1 / 每批导入后 | importer → coverage reviews → aggregator → 下游同轮重建 | accepted/provisional/limited 与去重成员、覆盖证据一致；所有只读检查通过 | 漂移腿拒收，不能据单个漂移作“该态化学上不存在”的终局结论；同盆地复现不虚增简并度 |
| P1 / 第四至五天 | 补齐可执行的 3→6 ceiling 差异与 WP3 排序威胁分析 | 差异表、Top-k、regret、pair/rung 与同轮标签可追溯 | 无独立生产级容差时继续只报告差异；不能看完结果倒推验收阈值 |
| P2 / 第五至七天 | 用最新准入池重跑 WP5、重建合规与阶段报告 | 配对初始集；同一批 ≥16/20 repeats 在相邻两个非耗尽预算点联合通过；实测查询成本 | not_reached 原样保留；子池成功不能冒充 12 分子全目标完成；WP6 前置不满足就不启动 |

当前 [B 组试点稿](../outputs/physics_completion/recovery/bgroup_pilot_preregistration.md) 仍明确“未启动”。
其中“AN/DMC 都应做相关扭转扫描”不能直接作为可执行协议：应先做分子自由度/物理可行性复核，再逐态注册动作。
所有 ORCA/xtB 仅在超算运行；本机只做轻量解析、页面生成和离线检查。不要同时开多个昂贵测试进程。

## 3. 核心代码：复用入口，不另造一套验收

| 职责 | 正式实现 |
| --- | --- |
| 输入/收敛/频率/哈希 QC 与 attempt 导入 | [import_ensemble_structures.py](../scripts/wp_production/import_ensemble_structures.py) |
| 覆盖证据登记 | [build_coverage_reviews.py](../scripts/wp_production/build_coverage_reviews.py) |
| 同态去重、log-sum-exp、验收三态 | [build_production_ensemble_aggregator.py](../scripts/wp_production/build_production_ensemble_aggregator.py)，尤其 `acceptance_decision` |
| FMO 轨道人口及身份报告 | [frontier_fmopop.py](../scripts/wp_production/frontier_fmopop.py)、[build_frontier_localization.py](../scripts/wp_production/build_frontier_localization.py) |
| Top-3 集合平均损失 | [run_wp5_AB_replay.py](../scripts/wp_production/run_wp5_AB_replay.py)，`Evaluator.r3_mean` |
| 相邻预算联合停止 | [wp5_replay_contract.py](../scripts/wp_production/wp5_replay_contract.py)，`empirical_stop_budget` |
| 方案验收与新鲜度 | [build_plan_compliance.py](../scripts/wp_production/build_plan_compliance.py) |
| 一致性收口入口 | [finalize_wp2.ps1](../scripts/wp_production/finalize_wp2.ps1)；不需要发布时不带 `-Commit` |

停止规则核心关系（正式实现已在上表，不复制修改阈值）：

```python
# passing[n] 是在预算 n 上 O_3 >= 2/3 且 R_3_mean <= 0.10 eV 的 repeat 集合；
# 已排除 n >= n_pool。要求同一批 repeats 同时通过，而非两个独立的 16/20。
joint_pass = passing.get(n, set()) & passing.get(n + 1, set())
stop_budget = n + 1 if len(joint_pass) >= 16 else None
```

R_3_mean 是“真实 Top-3 的均值 − 预测所选 Top-3 真值的均值”，不是 best-in-selected regret。
`n_unique=1` 也不必永久失败，但必须有可核验的生产级覆盖复核，不能因为没有第二极小就默认通过或默认不可能。

## 4. 页面与仓库维护

只编辑生成器，不手写派生数字：

```powershell
.venv\Scripts\python.exe scripts/build_github_readme.py
.venv\Scripts\python.exe scripts/build_terminal_site.py
.venv\Scripts\python.exe scripts/build_github_readme.py --check
.venv\Scripts\python.exe scripts/build_terminal_site.py --check
.venv\Scripts\python.exe -m pytest tests/test_terminal_site.py tests/test_repo_layout.py -q
git diff --check
```

页面以居中阅读轴、当前验收层次与证据链接为主。图集检索、放大、移动菜单和演示口令均保留。
GitHub 私有仓库的文件推送不等于 Pages 已上线；启用托管前应明确可见性与研究数据披露范围。
`asdfghjkl` 是客户端可见的假密码，不能用于保护隐私、API key 或未公开研究数据。

历史研究：[科学协议](physics_completion_protocol.md) · [历史结论](../FINAL_CONCLUSIONS.md) · [目录地图](65_repo_layout.md)。
不删除、不搬移归档证据；通过导航区分历史载荷与当前生产，避免破坏已有哈希和相对链接。
