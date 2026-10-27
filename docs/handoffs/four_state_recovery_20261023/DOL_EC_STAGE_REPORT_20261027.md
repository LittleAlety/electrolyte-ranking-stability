# DOL/EC 两腿阶段报告（2026-10-27）——已授权实验执行完毕、结果可信、成本结清

> 按 2026-10-27 执行方案的「本轮可完成终点」签发：**已授权实验执行完毕、结果可信、成本结清、
> 阶段结论一致**。**不是严格结题**——系综仍 44/48，严格目标保持未完成（不冒充）。

## 1. 两腿执行与判读总表（权威口径 `final_geometry_convergence`，取 abs）

| 腿 | job | 终态 | 墙钟 | **实测成本** | 五阈值 | 虚频 | 身份 | vs 已登记极小 |
|---|---|---|---|---|---|---|---|---|
| **DOL\|LiM_2plus** | `3782517_0` | COMPLETED | 01:04:08 | **4.2756 CH** | **4/5**：TolMaxD 2.478e-4 > 2e-4（超 1.24×） | **0** | ✅ 全过 | `C09#m2` RMSD 0.0962 |
| **EC\|LiM_2plus** | `3789580_1` | COMPLETED | 00:49:57 | **3.3300 CH** | **4/5**：TolE \|−5.205e-7\| > 2e-7（超 2.6×） | **0** | ✅ 全过 | `C04#m1` RMSD 0.1224 |

**两腿共同点（如实）**：
- **正常终止、SCF 全收敛、0 虚频、热化学完整、共价连接与 Li 首壳不变**——四层验收中除五阈值外**全部通过**；
- **末几何 vs 起点的纯骨架 RMSD = 0.0000**（两腿相同）：起点扰动被**完全弛豫回源**——
  优化收敛于**已登记极小的邻域**，未产生新极小；
- ORCA 均以 close-enough（「gradient convergence is overachieved」）宣布收敛，**但按冻结五阈值
  各有一项超差 ⇒ `technical_complete_qc_failed`（`verytight_convergence`）**——「ORCA 说 CONVERGED ≠ 过五阈值」再次实证。

**failure class：两腿均为 `verytight_convergence`**（与 DMC 历史同型但**程度远好**：
DOL MaxD 超 1.24×、EC TolE 超 2.6× vs DMC 的 1.6×–2.2× 且 DMC 是循环 16–23 的平台震荡）。

## 2. 成本结算（sacct 实据，AllocCPUS × ElapsedRaw）

| 项 | 值 |
|---|---|
| DOL（draft 包 `dol_ec_recovery_v1` batch 2） | `3782517_0`：4 核 × 3848 s = **4.275556 CH** |
| EC（正包 `hpc_dol_ec_recovery_v1_20261027` batch 2） | `3789580_1`：4 核 × 2997 s = **3.330000 CH** |
| **两腿合计** | **7.605556 CH**（预留 96 的 **7.9%**；父/`.batch`/`.extern` 未双计） |
| 预算总况 | 生产段（512）已用 **7.61 CH**；筛选已用 1.88 / 余 30.12；历史 227.43+591.8 不清零 |

两腿均远低于单腿 p90 基准（18.41 CH）——12 h 墙钟上限余量充足（实测最长 64 分钟）。

## 3. 对系综的含义（不预判、不冒充）

| 结果 | 系综 |
|---|---|
| **当前（两腿 QC 未过）** | **44/48**，四态仍 `limited` |
| 两腿经重优化过 QC ⇒ `single_basin_verified` | 最多 **46/48**（DMC 两态仍缺） |
| 严格目标 48/48 | **保持未完成**（**DMC 已按用户 2026-10-27 裁决本轮停止**，见 `0mvpw51rb` 与 `DMC_DECISION_BRIEF_20261027.md`；重启仅在新机制+版本化方案+独立预算获批后） |

**两腿的 0 虚频 + 身份通过 + 完全弛豫回源**意味着：若重优化后五阈值全过，
它们将作为**复现已登记极小的独立起点验证**走 `single_basin_verified` ⇒ `resolved` ⇒ `accepted`
——正是用户裁定「不必强行找到第二个极小，但必须证明独立起点在生产方法下通过了验证」的路径。

## 4. 下一个唯一允许动作（**已获用户 2026-10-27 批准**，按冻结边界执行）

**两腿共同：从各自收敛末几何严格重优化**（红线明文：阈值失败 ≠ 物种漂移，前者可从收敛末几何
严格重优化恢复）。用户已裁定「DOL/EC 值得各做一次**有界严格重优化**」，冻结边界如下：

| 项 | 冻结边界（用户裁定） |
|---|---|
| 任务 | DOL/EC 原两腿，**各一次新 attempt** |
| 起点 | 各腿**自己的最终几何**，保留来源哈希；与日志的关联在建包前列出（§4.1） |
| 方法 | 冻结方法、身份与五阈值**不变**；不换方法、不放宽 |
| 验收 | 优化及 AnFreq 完整；五阈值（**TolE 用 abs(ΔE)**，杜绝符号判定问题）、身份、频率、热化学与证据关联**全部通过** |
| 预算 | 4 核 × 12 h × 2 ⇒ **新增预留 96 CH**；既有 7.6056 CH **保留历史成本不清零** |
| 停止 | **本次仍失败即保留 limited；不自动追加下一轮** |
| 新 Hessian | 重优化若改变几何，**不复用旧几何的 Hessian 或热化学结果** |

**定位（用户裁定措辞）**：这是**本轮建议的最后一次有界尝试**——不是「最后一段必成计算」。
成功后还需覆盖复核与下游重建（最高 46/48）；失败则以实测结果完成**限制性阶段交付**。

### 4.1 建包前确认清单（用户裁定要求，先列实测再建包）

见 `DOL_EC_REOPT_PREREG_20261027.md`（五准则实测值/冻结阈值/**比值**/末收敛表所在优化段/
原始日志哈希/起点几何与日志关联证据）——**"4/5"本身不能说明差距小**，逐项以比值呈现。

## 5. 执行账对账

| 检查 | 实测 |
|---|---|
| 四道门（两腿提交时） | 混入检测/包加载/核数/预算 全过（EC：committed 0+48≤96） |
| 远端输入哈希 | DOL 16 文件 0 mismatch；EC 17/17 全 OK |
| 幂等提交 | DOL journal batch1=technical_failed+batch2=submitted；EC batch2=submitted（不投 batch1 避免重复 DOL） |
| 无重复在飞 | 队列空；两腿均终态结算 |
| 导入链 | candidates 2 行（119 既有行逐字节 0 变化）；`_probe_starts` 按 source_kind 识别；导入器保留 p4v2 来源（测试 42/42） |

## 6. 证据出处

- DOL：`work/dol_ec_recovery_v1/`（attempt 账本结算块 + submission journal）、
  `snapshots/3782517_0/`（8 产物）、`work/_dol_leg_acceptance.json`
- EC：`work/hpc_dol_ec_recovery_v1_20261027/`（结算后 SUMS 29 文件）、
  `snapshots/3789580_1/`（8 产物）、`work/_ec_leg_acceptance.json`
- 权威阈值解析：`scripts/wp_production/import_hpc_opt_numfreq.py::final_geometry_convergence`（取 abs）
- 五阈值冻结值：`recovery_contract.json` thresholds / `orca_derivative_policy.py`
- 成本：sacct `-P -o JobIDRaw,State,AllocCPUS,ElapsedRaw`（`batch_cost_settlement.allocated_core_hours` 结算）
- 审计与修复：`docs/handoffs/four_state_recovery_20261027_gate_code_audit/REPORT.md`（14 缺陷全采信）、
  commits `bd754f8`/`9e0c377`/`d7bcbdf`/`c170997`