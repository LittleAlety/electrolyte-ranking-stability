# P2 四态分流诊断：route_decision（2026-10-23）

依据：四态 labels/dispositions/coverage_reviews + 各自**代表成员几何**上的实测。
本文件只诊断，**不构成提交授权**；任何提交仍须过 P4 的门。

## 0. 共同事实（实测）

| 项 | 值 |
|---|---|
| 四态 labels | `acceptance_status=limited`，`n_unique=1`，`n_members=1`，`pool_limited=true`，`limitation_reason=rescue_budget_exhausted` |
| 覆盖复核分级 | **DMC 两态 = `unresolved_qc`**（"registered recovery start(s) exist but none passed QC"）；**DOL/EC = `search_exhausted`**（"independent GFN2 search found no new minimum … **a physical finding at the screening level, not a budget failure**"） |
| 严格总闸门 | 仍 3 缺口（`ensemble_not_48_accepted` / `wp5_full_target_pool_evaluated` / `execution_cost_provenance_complete`） |

## 1. `DMC|M_plus` → 路线：**数值收敛补救 + ≤2 独立起点**

| 项 | 值 |
|---|---|
| 代表几何（P0 解析器） | `work/hpc_frontier_localization_v1/tasks/DMC__M_plus__primary/geom.xyz`，sha256 `5b9e93e0146333f7c851e2f0176675a9`（**2026-10-24 逐文件实测：该 sha 属 frontier 树**，本态无同名系综副本；与 §3 的 DOL 行不同——那份属生产系综包） |
| 末次尝试 | `tors_8_0_1_2` att2 `technical_complete_qc_failed`，`final_geom` `60ef9ba4…`、`log` `fa78c69f…`、`hess` `42ea648b…` |
| 失败机制 | `verytight_convergence`（`tors_6`/`tors_7`，**各仅 1 次真实计算**）＋ `strict_reopt_required`（`28`/`tors_8`，**2 次已尽**） |
| **可用独立起点** | 登记二面角 **10** 个（键级校验后），已探过 **3** 个且全部来自**被声明无效的 v1 刚性族** → **7 个从未被合法探过**。对这 7 个跑**修好的 gate（不带 `prior_starts`，只看"这条候选本身合法吗"）**：**7 个全部接受**（**4 个 `ok_heavy_fragment`**、3 个 `ok_methyl_rotor`）。⚠ **这是"逐条合法性"测量，不是最终候选数**——加上 `prior_starts` 去重后**只余 3 个**（见下一行与 `P3_CANDIDATES_20261023.json` 的 `select_candidates` 口径，那边记「3 接受 + 4 判 `equivalent_start`」）。两者不矛盾，**以带去重的那一行为准**。 |
| 去重后**真正不同的操作** | **2 个重骨架操作**：`{0-1-2-3/4}`（pair 1.0131、**heavy 0.2743 Å**）与 `{1/3-2-4-5}`（pair 0.6152、**heavy 0.2432 Å**）；另有 1 个甲基转子（`2-4-5-H`，heavy 0.0000，**不得当作重骨架搜索证据**） |
| 为何独立 | gate verdict `ok_heavy_fragment`，重原子成对距离变化 **0.2743 / 0.2432 Å ≫ 1e-5**；共价拓扑完整、Li 首壳未变、**与源及任一已登记起点不等价**（gate 逐项判定） |
| **路线** | ① 对 `verytight_convergence` 且**仅 1 次**计算的腿，从其**自身收敛末几何**做严格重优化（两步走设计，**这是数值修复，不计作独立新起点**）；② 最多 **2 个独立生产起点**取自上面两个不同重骨架操作 |

## 2. `DMC|LiM_2plus` → 路线：**数值收敛补救 + 1 个独立起点（+可选登记 Li 配位探针）**

| 项 | 值 |
|---|---|
| 代表几何 | `work/hpc_frontier_localization_v1/tasks/DMC__LiM_2plus__primary/geom.xyz`，sha256 `f619c13234e5455fe0651b7444728e42`（**2026-10-24 实测属 frontier 树**） |
| 末次尝试 | `tors_7_0_1_2` att**12** `technical_complete_qc_failed`，`final_geom` `a7bc7283…`、`log` `3973a13d…`、`hess` `aa06de59…` |
| 失败机制 | `max_cycles_exhausted`（`tors_6`/`tors_8`，**各 1 次**）＋ `verytight_convergence`（`tors_7` att12，2 次已尽）＋ `strict_reopt_required`（`c06` att1，2 次已尽） |
| 可用独立起点 | 上述 7 个候选中，**仅 2 个接受**（`{0-1-2-3/4}`，pair 1.2478、**heavy 0.4874 Å**，四态中最大重骨架扰动）→ **1 个真正不同的重骨架操作** |
| **5 个被拒** | 全部 reason = **`li_coordination_changed`**——旋转它们会把 Li 配位壳内的给体移出首壳。**这是合法的搜索方向，但必须作为"登记的 Li 配位探针"显式声明，不能靠扭转的副作用顺带发生** |
| **已解除该障碍（本轮代码）** | gate 新增**声明式**开关 `declared_li_change=True`：默认仍拒收**意外**改变；声明后接受并**分类为 `ok_li_coordination_change`**（自己的类，绝不冒充扭转），并把 source/candidate 壳层写入 detail。实测这 5 个候选随之变为**可用**：`1/3-2-4-5`（heavy **0.4667**）、`2-4-5-9/10/11`（heavy **1.7274**） |
| 为何独立 | 同上（heavy 0.4874 Å、拓扑完整、Li 首壳未变、不等价） |
| **路线** | ① 对 `max_cycles_exhausted` 且仅 1 次计算的腿做数值补救；② **1 个独立生产起点**（heavy 0.4874）；③ 若仍需第二起点，则**登记 `li_coordination_change` 探针类**（方法/成本/停止条件先预注册），并在 gate 上显式 `check_li_shell=False` |

## 3. `DOL|LiM_2plus` → 路线：**合法环形变 + Li 供体/配位搜索**（筛选级已判单盆地）

| 项 | 值 |
|---|---|
| 代表几何 | **`work/hpc_production_ensemble_r1_036-053/tasks/DOL/LiM_2plus__c05/geom.xyz`**（**加权成员是 `c05`，不是 `primary`**），sha256 `f0b2558e0cf2cf9b3430d27239b4a76a` |
| ｜路径提醒 | ⚠ 上行的 sha 属**生产系综包**（该目录正是登记 resolver 实际读的那份）。**frontier 树里的同名文件是另一份**：`work/hpc_frontier_localization_v1/tasks/DOL__LiM_2plus__c05/geom.xyz` = `079dd8b35c5839c0…`（**不同 sha，勿混用**）。2026-10-24 逐文件实测 |
| **`c05` att1 = `computed`** | 即 **scientific QC passed**（`disposition=computed`、`failure_class=strict_reopt_not_needed`）；`final_geom` `079dd8b3…`、`log` `984fa741…`、`hess` `0ac027cf…` |
| 其余 | `c01` att1 `imaginary_modes`（2 次已尽） |
| 失败机制 | **筛选级单盆地**：独立 GFN2 搜索"所有起点塌缩到已知盆地"，复核原文明确「**是筛选层的物理发现，不是预算失败**」 |
| 可用登记扭转 | **0 个**（五元环刚性 + 环上无重原子取代基；已在**真实代表几何**上算出，非缺失文件推断） |
| **路线** | 登记两类**新的合法探针类**：① **环形变（pucker）**——沿环法向位移环原子，保持键图，gate 应判 `ok_heavy_fragment`；② **Li 供体方向/配位**——显式 `li_coordination_change`。两类先做**本机筛选级**生成+gate 校验，再交 Slurm 做 GFN2 筛选。**若全部塌缩回已知盆地**：按**事前登记**的生产级覆盖探针分支处理，**不伪称 GFN2 新极小**；**找不到合格候选就填"零"** |

## 4. `EC|LiM_2plus` → 路线：**环/配位自由度，明确禁止 C=O 伪扭转**

| 项 | 值 |
|---|---|
| 代表几何 | `work/hpc_frontier_localization_v1/tasks/EC__LiM_2plus__primary/geom.xyz`，sha256 `16774e2151551a5e69ff867c6deea686`（**2026-10-24 实测属 frontier 树**） |
| 末次尝试 | `c03` att1 `technical_complete_qc_failed`，`final_geom` `7de2ab24…`、`log` `4887d4ed…`、`hess` `9d4fc1cf…` |
| 失败机制 | `imaginary_modes`（2 次已尽）＋ 两个 v1 `tors_2_3_4_10`/`tors_5_3_4_10` 是 **C=O 伪扭转**（`rotate_fragment` 的单键门直接拒收） |
| 可用登记扭转 | **0 个**（键级门禁后；两条原登记都是绕 **1.186 Å 的 C=O** 旋转） |
| **路线** | 同 DOL：碳酸酯环 pucker + Li···O=C 配位/给体方向；**C=O 不得作为自由扭转**。同样走「本机生成+gate → Slurm GFN2 筛选 → 全塌缩则按预注册分支」 |

## 5. 由本诊断导出的**新需求**

1. **gate 支持显式登记的 Li 配位探针 → 本轮已实现并测试**：默认 `check_li_shell=True`（拒收**意外**
   改变），允许**声明式** `declared_li_change=True` → 接受并分类为 `ok_li_coordination_change`。
   **同时修了一个真实连带缺陷**：共价拓扑判据原先把 `bond_graph` 半径截断下的 **2.0 Å Li···O**
   当成共价键，导致 (a) 意外的配位变化**永远先报 `ring_broken`**、(b) 声明式配位探针**仍被拒**。
   现拓扑判据**排除 Li 关联边**（Li···O 是配位，不是共价），由 Li 首壳判据负责。
2. **需要两类新的候选生成器**：环形变（pucker）与 Li 配位/给体方向；两者都必须**先过 gate**、
   并记录 源几何 SHA256 / 原子映射 / 距离不变量 / 独立性类别。
3. **候选去重必须带 `prior_starts`**：实测 7 个登记二面角在几何上只对应 **2–3 个真正不同的操作**
   （如 `0-1-2-3` 与 `0-1-2-4` 给出**完全相同**的 pair/heavy 变化）——生产构建器已传
   `prior_starts=selected`（gate 测试已钉住），P3 必须沿用。
4. **新探针类必须先预注册**（方法唯一定义 / 成本上限 / 停止条件 / 不回填旧池），
   因为 `li_coordination_change` 与环 pucker 的重骨架位移可达 **0.47–1.73 Å**，属真实结构变化，
   **不是**"同终点重启"，也不得冒充扭转。

## 6. 预算映射（建议上限，**未自动批准**）

| 用途 | 上限 | 拟用 |
|---|---:|---|
| 筛选（GFN2，Slurm 计算节点） | 32 core-hours | DMC 两态候选 + DOL/EC 的环/Li 探针筛选 |
| 首轮生产 | 512 core-hours | 每态 ≤2 独立起点 |
| 有因补救 | 256 core-hours | 仅"1 次真实计算 + 有明确父尝试与失败机制"的腿 |
| **合计** | **800** | **不是要把槽位用满**；16 核×4h 不够时**先停止并提交诊断，不暗改 24h** |

**本轮未提交任何作业**；下一步 P3 先做**本机**候选生成 + gate 校验（不消耗超算额度）。