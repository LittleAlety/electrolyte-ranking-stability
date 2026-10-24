# 项目导航、后续安排与核心代码

> 导航核对：2026-10-22。数字只是该次已提交产物的快照；最新状态以以下机器可读账本为准。本文不改变科学协议、阈值、预算或计算授权。

历史 Round 1–44 已从根 README 的单一长日志拆为[按研究主题组织的进度索引](progress/README.md)。旧周报与 `outputs/week*` 均保留原位；新索引只负责导航，不改变证据或哈希。

## 1. 从哪里看真实进度

| 问题 | 权威入口 | 读法 |
| --- | --- | --- |
| 现有合规总体项 | [合规台账](../outputs/physics_completion/compliance/plan_compliance.md) | `plan_overall_complete` 不是完整 v3 严格目标证书；身份、正式 WP5 与触发后 WP6 仍须另验 |
| 48 个主态是否完成 | [主态元信息](../outputs/physics_completion/compliance/plan_compliance_meta.json) | primary 科学验收与运行完成分开 |
| 48 个系综是否可验收 | [系综标签](../outputs/physics_completion/ensembles/production_ensemble_labels.csv) | 只数 `acceptance_status=accepted`，不能只数数值行 |
| 已救回哪些、还卡哪些 | [严格恢复报告](../outputs/physics_completion/recovery/strict_recovery_v1_report.md) | 连同失败尝试、去重和覆盖复核一起读 |
| 前沿轨道与身份 | [全成员前沿报告](../outputs/physics_completion/frontier/frontier_localization.md) | 区分 AO 系数诊断与 FMO population 分类；不要混用两列权重 |
| 扩样是否收敛 | [3→6 差异](../outputs/physics_completion/sampling/sampling_3to6_diff.md) | 当前只报告差异，不判采样收敛；空缺不是零 |
| A/B 回放是否达到停止预算 | [A/B 端点](../outputs/physics_completion/active_learning/blind_replay/AB_axis_endpoint.csv) | 看池大小与 `stop_budget_status`，不拿历史 12 分子回放替代当前 accepted 子池 |

当前快照：primary **48/48**；系综 **44 accepted / 0 provisional / 4 limited**，严格目标尚未完成。
余下 DMC/M_plus、DMC/LiM_2plus（`unresolved_qc`：已收敛、0 虚频，但未过冻结五阈值 76.88 / 74.30 cm⁻¹，
真实计算次数已尽，含另立版本的严格重优化）、DOL/LiM_2plus、EC/LiM_2plus（`search_exhausted`：
五元环全刚性、两个登记二面角都穿过 C=O 中心——**两态没有任何可执行探针**，是数据结论不是预算不足）。
前沿产物当前为 **解析 80/80、证据表标记 verified 80/80**。分母来自当前加权成员集合，
不代表独立完整科学身份 QC；自旋/轨道选择、布居口径与来源链接仍须审查。最新数字由 README/Pages
生成器从权重、前沿和身份证据三表交叉核对；本文日期快照不等同于实时队列。
**契约探针**：`pwsh -NoProfile -File work/deepseek_support_20261022/run_preflight.ps1`
（0=全过 / 1=复现缺口 / 2=源码在运行期间变化须重跑）。当前 **15 PASS / 0 FAIL**，
入口与六项缺口见交接包说明（`work/deepseek_support_20261022/README.md`）——该目录是
**机器本地层且已 gitignore**，干净克隆中不存在，因此这里不给可点击链接（避免发布页死链）。

## 2. 接下来怎么做（按依赖，不按口头完成度）

| 优先级 / 建议窗口 | 动作 | 完成证据 | 失败预案 |
| --- | --- | --- | --- |
| P0 / 立即 | **已完成**：3748336 已回收并诊断（`orca_close_enough_but_frozen_tolE_missed_reopt_required`，`energy_change 8.857e-07` vs `TolE 2e-7`，0 虚频、92.43 cm⁻¹，重原子 Kabsch RMSD 0.0292 Å → 已知盆地）；不为它自动续算 | 同次执行证据、诊断字段与去重结论齐备；EC 两条双键拒绝；分批清单与远端哈希一致 | 旧 11 起点是刚体变化，不能冒充独立新构象；新作业失败或同盆地回落按原规则登记，不自动扩大候选 |
| P0 / 第一天 | 校核已解析 frontier 的同源证据、自旋/轨道选择与报告口径 | 每条正式权重绑定同次执行的输入/几何/日志/轨道；解析和身份 QC 分列 | 80/80 登记不能替代算法与科学复核；缺失/重复/多出成员 fail-closed，不自动补算 |
| P1 / 第一天至第三天 | **已完成主体**：探针按原协议验收并接入候选 manifest；**AN/M_plus 经 `single_basin_verified` 放行**（生产级 0 虚频 / 336.49 cm⁻¹ / 完整 Hessian + 独立甲基转子起点 + 重原子 Kabsch RMSD 0.0015 Å + 登记搜索范围） | 新极小全套 QC，或可核验的生产级单盆地复现与覆盖复核；探针强度按**重原子位移**分级（`probe_class`） | DMC 两态的探针已收敛但未过阈值 → 保持 `unresolved_qc`；DOL/EC 没有可执行注册 probe → 保留 `search_exhausted` |
| P1 / 每批导入后 | importer → coverage reviews → aggregator → 下游同轮重建 | accepted/provisional/limited 与去重成员、覆盖证据一致；所有只读检查通过 | 漂移腿拒收，不能据单个漂移作“该态化学上不存在”的终局结论；同盆地复现不虚增简并度 |
| P1 / 第四至五天 | 补齐可执行的 3→6 ceiling 差异与 WP3 排序威胁分析 | 差异表、Top-k、regret、pair/rung 与同轮标签可追溯 | 无独立生产级容差时继续只报告差异；不能看完结果倒推验收阈值 |
| P1 / 第三至五天 | **正式模型已真实运行**（`knn_baseline` 基线 + `ridge_std`/`krr_rbf`/`gpr_rbf`，逐行记 `executed_model`）；余下 = 消费者接线与 acquisition 身份（task-6/7） | 实际运行冻结模型；legacy 与正式 A/B 隔离；逐查询成本含成员、失败、救援且共享作业不重计 | **实测 `uncertainty` 的查询序列在四模型下完全相同** → acquisition 用自带 kNN、**没接模型**；不能据常量宣称契约已通过，也不得静默让 legacy 回退 |
| P2 / 第五至七天 | 重建完整严格目标闸门与阶段报告 | 身份、采样、WP3、正式 WP5、扩样处置及触发后的 WP6 有同轮可核验证据 | not_reached 和限制原样保留；即使系综 48/48 也不自动宣称项目完成 |

### 2026-10-22 批次/片段故障已修复，等待新任务验收

有 11 个数组元素提交记录：**3747714 / 3747724**，并非所有 11 条独立预期探针均已正确派发。
第二批提交脚本 `batch_2_20261022-150827.sbatch` 的数组为 `0-2`，却读取总 `tasks.txt` 的前 3 行，
重复指向首批 AN/M_plus 的 tors_3/4/5；原预期的 DMC/LiM_2plus tors_7 与 EC 两条没有正确派发。
用户现已授权取消错误第二批并只修复原指定三条中的合格者：**3747724 的三个元素已 CANCELLED，Elapsed=0**。
又发现旧生成器转动所有原子，11 个原起点的成对距离变化均 ≤1.066×10⁻⁹ Å，不能计作独立新构象。
真正片段旋转与全原子拓扑/对称去重预检后，只有 DMC/LiM_2plus tors_7_0_1_2 合格，
已提交 **3748336（1 任务、4 核、VeryTightOpt + AnFreq）**；EC 两条中心 C3=O4 双键被拒绝。
原第一批 3747714 未取消，历史成本保留。完整处置、哈希与验收边界见
[修复记录](hpc_batch2_repair_20261022.md)。旧 [B 组试点稿](../outputs/physics_completion/recovery/bgroup_pilot_preregistration.md)
的“未启动”属于早期注册稿，不能覆盖后续真实提交记录。预检成功不代表发现新盆地。

修复后的 `render_batch_script` 已读取**该批专属清单**，而不是重用总清单的零基索引。核心关系：

```bash
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"
batch_file="batch_2.txt"  # 由已冻结 manifest 生成并核验哈希
mapfile -t batch_tasks < "$batch_file"
task="${batch_tasks[${SLURM_ARRAY_TASK_ID:?}]:?missing batch task}"
# 随后核对 task 在该批 manifest 中的身份及输入哈希，验证后才执行。
```

### 2026-10-22 第二批：探针世代与接线（系综 43 → 44）

交接包六项契约缺口已全部闭合（探针 **9 PASS/6 FAIL → 15 PASS/0 FAIL**）：停止预算的
**坏输入门**（五种结构非法批次此前都返回预算 7 → 现在一律 `raise`，把「没达到 / 达不了 /
无法评估」三分）、学习器接口**只传可见标签**（此前把完整真值交给预测器）、`model_contract`
维度不符即拒绝。合成反例已进正式测试 `tests/test_contract_counterexamples.py`（16 项）。

**决定性接线缺口**：探针成员**从未登记为系综候选**（`production_ensemble_candidates.csv`），
于是聚合器看不到它们——无去重行、不在 kept 池、覆盖复核拿不到任何证据。这正是
「探针 `computed` 且 Hessian 干净、态却一直 `unresolved`」的真因。修法：按
**最新真实世代**登记唯一候选行；**v1 刚性族排除**（起点与 primary 逐原子一致，RMSD 0.0000 Å，
冒充独立起点即伪造覆盖证据），排除项带原因可审计。登记起点同时改为
「冻结恢复行 ∪ 探针候选」的并集。

**探针批次（全部 `conv=1` + 完整 Hessian）**：

| Job | 内容 | 结论 |
| --- | --- | --- |
| 3749450 | AN + DMC/M_plus 甲基转子（`hpc_torsion_probe_v2_realfragment`） | AN **computed** → 放行；DMC/M_plus `strict_reopt_required`（76.88 cm⁻¹） |
| 3749453 | DMC/LiM_2plus 真片段严格重优化（`hpc_torsion_probe_v1_reopt_v3`，attempt 12） | `verytight_convergence`（74.30 cm⁻¹） |

**探针强度按重原子位移分级**（写入包 manifest 与候选行 `probe_class`）：DMC/LiM_2plus
tors_7 = **0.563 Å**（`heavy_fragment_torsion`）；AN 与 DMC/M_plus = **0.000 Å**
（`methyl_rotor`：只是转子坐标上的独立起点，**不能**搜索别的重原子盆地）。

**如实结论**：DMC 两态已收敛、0 虚频，但未过冻结五阈值，真实计算次数已尽
（含另立版本）→ 保持 `unresolved_qc`，**不自动续算**；DOL 与 EC 没有任何可执行探针
→ `search_exhausted`。被取消的 3747724 元素（`Elapsed=0`）与两条被拒 EC 探针
**不得读作"在途"**：复核读修复 manifest 的 `rejected` 与 `replaces_cancelled_job` 排除它们。

### 提交器回归现覆盖每批索引→任务映射

```python
from collections import Counter

def validate_batches(all_task_ids, batches):
    if not all_task_ids or any(not batch for batch in batches):
        raise ValueError("empty task registry or batch")
    if any(not task for task in all_task_ids):
        raise ValueError("empty task ID")
    if len(set(all_task_ids)) != len(all_task_ids):
        raise ValueError("duplicate registered task ID")
    assigned = [task for batch in batches for task in batch]
    if Counter(assigned) != Counter(all_task_ids):
        raise ValueError("missing, duplicate, or unregistered batch task")
    # 还需逐条读取生成的 sbatch，验证每个 array index 真正读取本批清单。
```

所有 ORCA/xtB 仅在超算运行；本机只做轻量解析、页面生成和离线检查。不要同时开多个昂贵测试进程。

## 3. 核心代码：复用入口，不另造一套验收

| 职责 | 正式实现 |
| --- | --- |
| 输入/收敛/频率/哈希 QC 与 attempt 导入 | [import_ensemble_structures.py](../scripts/wp_production/import_ensemble_structures.py) |
| 覆盖证据登记 | [build_coverage_reviews.py](../scripts/wp_production/build_coverage_reviews.py) |
| 同态去重、log-sum-exp、验收三态 | [build_production_ensemble_aggregator.py](../scripts/wp_production/build_production_ensemble_aggregator.py)，尤其 `acceptance_decision` |
| FMO 轨道人口及身份报告 | [frontier_fmopop.py](../scripts/wp_production/frontier_fmopop.py)、[build_frontier_localization.py](../scripts/wp_production/build_frontier_localization.py) |
| 同自旋同轨道与同源身份证据 | [frontier_spin_qc.py](../scripts/wp_production/frontier_spin_qc.py)、[build_frontier_identity_evidence.py](../scripts/wp_production/build_frontier_identity_evidence.py)；存在模块不等于所有消费者已正确接线 |
| 探针任务、片段预检与分批模板 | [build_torsion_probe_package.py](../scripts/wp_production/build_torsion_probe_package.py)：`render_batch_script`、`validate_batch_partition`、`rotate_fragment`、`equivalent_start`、`build_repair_package`；[包回归测试](../tests/test_build_torsion_probe_package.py) |
| Top-3 集合平均损失 | [run_wp5_AB_replay.py](../scripts/wp_production/run_wp5_AB_replay.py)，`Evaluator.r3_mean` |
| 相邻预算联合停止 | [wp5_replay_contract.py](../scripts/wp_production/wp5_replay_contract.py)，`empirical_stop_budget` + `_validate_stop_rows`（坏输入必 raise） |
| 正式预测器与模型契约 | [wp5_formal_models.py](../scripts/wp_production/wp5_formal_models.py)：`ridge_std`/`krr_rbf`/`gpr_rbf`（`knn_baseline` 是**基线的独立名字**）；带宽 `1/FEATURE_DIM`，维度不符即拒绝 |
| 来源哈希契约与清单重冻 | [provenance_hash.py](../scripts/wp_production/provenance_hash.py)（文本 LF 归一化、二进制原始、按后缀分派）、[refreeze_manifest.py](../scripts/wp_production/refreeze_manifest.py)（EOL 重标定 vs 真实内容变化分开、`--drop` 带理由） |
| 按族成本账（唯一作业身份） | [build_ensemble_cost_by_family.py](../scripts/wp_production/build_ensemble_cost_by_family.py)：基础主态 vs 完整系综标签两个分母；missing 如实登记不估 |
| 方案验收与新鲜度 | [build_plan_compliance.py](../scripts/wp_production/build_plan_compliance.py) |
| 探针强度分级 | 包 `manifest.json` 与候选行 `probe_class`（`heavy_fragment_torsion` vs `methyl_rotor`） |
| 一致性收口入口 | [finalize_wp2.ps1](../scripts/wp_production/finalize_wp2.ps1)（**79 步**）；不需要发布时不带 `-Commit` |

停止规则核心关系（正式实现已在上表，不复制修改阈值）：

```python
# passing[n] 是在预算 n 上 O_3 >= 2/3 且 R_3_mean <= 0.10 eV 的 repeat 集合；
# 已排除 n >= n_pool。要求同一批 repeats 同时通过，而非两个独立的 16/20。
joint_pass = passing.get(n, set()) & passing.get(n + 1, set())
stop_budget = n + 1 if len(joint_pass) >= 16 else None
```

R_3_mean 是“真实 Top-3 的均值 − 预测所选 Top-3 真值的均值”，不是 best-in-selected regret。
`n_unique=1` 也不必永久失败，但必须有可核验的生产级覆盖复核，不能因为没有第二极小就默认通过或默认不可能。
**这是一条被实测推翻过一次的判断**：2026-10-21 曾把「系综上限 42/48」写成硬结论，
24 小时内就因用户四项裁决与探针接线打通升至 **44/48**。上限类结论必须写成
「**在当前方法集与预算下**的上限」，并标明证据层级（筛选层 / 生产层）。

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
