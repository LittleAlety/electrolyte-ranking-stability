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

---

## 7. 2026-10-28 本轮收口（追加节，不覆盖）

> **本轮结束条件**：阶段交付完成（45/48 科学结果）。严格 48/48 研究目标仍未完成。

### 7.1 系综现状

| 态 | 验收判定 | 依据 |
|---|---|---|
| DOL\|LiM_2plus | **accepted** | 生产腿通过 + 两轮严格重优化 QC 通过（五阈值全过、身份全过、0 虚频、热化学完整） |
| EC\|LiM_2plus | **limited** | reopt 在冻结边界内再次失败（TolE abs 6.366e-7 = 3.18× 阈值）；按用户 2026-10-27 裁定「本次仍失败即保留 limited，不自动追加」 |
| DMC\|M_plus | **limited** | 用户 2026-10-27 裁决本轮停止，不重新提交 |
| DMC\|LiM_2plus | **limited** | 同上 |
| 其余 44 态 | **accepted** | 生产腿直接通过 |

**系综计数：45 accepted / 3 limited / 0 provisional；分母 48 不变。**

### 7.2 成本修正（per-leg 结算）

2026-10-28 发现 reopt 批次（job 3791416）的手工结算将 DOL/EC 两腿成本**交叉互换**。原因：`sacct JobIDRaw` 不是元素 id——该批次 raw id 交叉（element 0→3791417, element 1→3791416），而 810+1004 对称，total-only 检查无法发现。

| 腿 | slurm_element | job_id_raw | ElapsedRaw | **实测 core-hours** |
|---|---|---|---|---|
| DOL | 3791416_0 | 3791417 | 810 s | **0.900000 CH** |
| EC | 3791416_1 | 3791416 | 1004 s | **1.115556 CH** |
| **reopt 合计** | | | | **2.015556 CH** |

- 权威结算链：`tasks.txt line i` → `array element i` → `sacct JobID "<array>_<i>"` → 该行的 `JobIDRaw` → `AllocCPUS × ElapsedRaw / 3600`
- `.batch`/`.extern` 子行携带 `_b`/`_e` 后缀，已被 `per_element_core_hours()` 显式拒绝（避免 3× 超计）
- 新增 `per_element_core_hours()` 函数 + 6 个 pytest（35/35 绿）+ RED 证明（缺陷注入后 5/6 失败）确保此 bug 不复发

### 7.3 下游重建

1. `ensemble_cost_by_family.csv`：reopt 精确值 0.9000 + 1.1156 = 2.0156 CH 已登记
2. `recovery_budget_accounting.md`：严格恢复包 187.0 / 600 CH；DOL/EC 恢复（9.6 CH）与 reopt（2.0 CH）分别归档
3. `plan_compliance`：`strict_readiness_evidence` 从 4/6 → 5/6（`identity_all_members_complete` 现在通过）；唯一未过项 `wp5_full_target_pool_evaluated`
4. 网站 `data.js` + `index.html`：系综 45/48、strict evidence 5/6、进度 83%、3 limited 态及原因已同步
5. `build_ensemble_cost_by_family.py --check` / `build_recovery_budget_accounting.py --check` / `plan_compliance --check` / `site --check` / `readme --check` 全部通过

### 7.4 当前 blocker

| 缺口 | 原因 |
|---|---|
| `ensemble_not_48_accepted` | DMC 两态 + EC 仍 limited |
| `wp5_full_target_pool_evaluated` | 全池评估未完成 |

### 7.5 下一轮诊断方案（EC/DMC，设计-only，不提交、不预算）

**EC**：
- 前提：本轮 reopt 在 TolE 上再次失败（abs 6.366e-7），但优化几何已完全弛豫回已登记极小邻域，无物种漂移
- 诊断：若用户批准，在**有界预算内**（≤32 CH 新授权；≤256 rescue）运行 `single_basin_verified` 全池评估，聚焦已注册二面角探针路径（pucker/twist 5 个合法连续）
- 停止条件：任一探针到达另一盆地 → 状态更新为 `resolved`；全探针仍单盆地 → `unresolved`；成本或预算超限 → `limited`
- 预注册：9 点（方法、探针定义、停止条件、成本上限、标识链、双重口径预防）

**DMC**：
- 前提：用户 2026-10-27 裁决本轮停止，不重新提交
- 诊断：下一轮须**新机制**（如显式 Li 配位几何、不同预优化路径）+ 版本化方案 + 独立预算
- 停止条件：同 EC 框架，但方法变更需通过 gate code audit + 用户明确批准
- 预注册：9 点（新机制、版本化、独立预算、标识链、停止条件）

### 7.6 复现命令

```bash
# 依赖已安装的 .venv
python scripts/wp_production/batch_cost_settlement.py  # --check
python tests/red_per_element_cost_swap.py               # RED 证明
python -m pytest tests/test_evidence_gate_and_cost.py -k per_element -v
python scripts/wp_production/build_ensemble_cost_by_family.py --check
python scripts/wp_production/build_recovery_budget_accounting.py --check
python scripts/wp_production/build_plan_compliance.py --check
python scripts/build_terminal_site.py --check
python scripts/build_github_readme.py --check
python scripts/wp_production/refreeze_manifest.py --check
git diff --check
```
