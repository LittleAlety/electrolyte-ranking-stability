# EC 下一轮预注册草案（设计-only，不提交、不预算、不启动）——修订版 v1

> **性质**：设计草稿，供用户审议。不触发提交、不占用预算、不改动任何现有标签或判定。  
> **版本**：v0-draft-rev1（2026-10-28）  
> **对应缺口**：`ensemble_not_48_accepted` → `EC|LiM_2plus` limited  
> **修订依据**：独立审计 `REPORT_independent_t7.md` 16 条缺陷（F1-F16）

## 1. 目标态与方法

- 目标态：`EC|LiM_2plus`（当前 limited，reopt TolE 3.18× 二次超差）
- 方法：wB97X-D4/def2-TZVPD + SMD(acetonitrile)，Opt VeryTightOpt AnFreq（冻结方法不变）
- 判定路径：`single_basin_verified`（独立起点验证，**不要求找到第二个极小**，但必须通过六项验收）
- 严格总闸门关联：本态通过 → `production_ensembles=46/48`；**严格 readiness 仍为 5/6**（需 DMC 两态也 accepted 才可能 6/6）

## 2. 预算与资源

| 项 | 值 |
|---|---|
| 本轮可用预算 | ≤32 CH（**新授权额度**；独立于 600 CH 恢复包与 800 CH 框架；须另立版本） |
| 资源 profile | `orca_production_v1`（4 核/腿） |
| 每腿墙钟 | 4 h（默认）或按 `recovery_contract.json` 例外条款 |
| 并发上限 | 1 腿（**与 DMC 串行**，避免账户冲突） |
| 核算口径 | `per_element_core_hours()`（`tasks.txt line i` → `array element i` → `sacct JobID "<array>_<i>"` → 该行的 `JobIDRaw` → `AllocCPUS × ElapsedRaw / 3600`，按元素结算，防交叉互换） |
| 累计成本上限 | 32 CH（硬上限，超限立即阻断） |
| 每态起点额度 | ≤2 独立起点（授权明文），本批次 1 起点 + 5 探针扫描 |

## 3. 探针与路径定义（修正 F1/F13）

### 3.1 起点与探针

- **命名族**：`hpc_ec_recovery_v2_20261028`（序号高于该成员全部历史 attempt）
- **输入几何**：`work/hpc_dol_ec_recovery_v1_reopt_20261027/snapshots/3791416_1/job.xyz`（**真末几何**，SHA256 `6c711c4e…`；非 `snapshots/geom.xyz`）
- **已注册合法探针**：pucker/twist 5 个连续二面角（不改变骨架、不打断环）
- **探针方向**：从 reopt 收敛末几何沿登记二面角路径展开

### 3.2 判定条件（`single_basin_verified` 三条件，缺一不可）

| # | 条件 | 判定标准 | 失效后果 |
|---|------|----------|----------|
| ① | `production_evidence` 完整 | `imaginary_modes`/`final_geometry_sha256`/`log_sha256` 非空 + 过冻结五阈值 + 身份 QC + 0 虚频 + 热化学完整 + 共价连接不变 | 退化为 `known_basin_reproduction` ⇒ `unresolved` |
| ② | `search_scope_documented` | `registered_starts` 非空且 `search_outcome` ∈ {`no_new_minimum_found`, `new_minimum_resolved`, `same_basin_reproduction`} | 同上 |
| ③ | 进 `latest_members` | 角色在 `("round1_extra","recovery_v1_start","recovery_v2_start")` 白名单 | 同上 |

### 3.3 停止条件

- **任一探针**生产腿过六项验收（五阈值+身份+0 虚频…）且复现已登记极小 + 三条件齐 → `single_basin_verified` → `resolved` → `accepted`
- **任一探针**得新极小且过 QC → `multi_basin_coverage` → 同样 `accepted`
- 5 探针均失败或证据不完整 → `known_basin_reproduction` → `unresolved` → 状态维持 `limited`（不追加）
- 成本超限（>32 CH）或方法故障 → `limited`

## 4. 标识链与输入哈希（修正 F11/F12）

### 4.1 候选登记

| 探针 | 唯一名称 | 父几何 | 父几何 SHA256 | 变形参数 | 身份预检 |
|------|----------|--------|---------------|----------|----------|
| `ec_v2_p1` | `EC|LiM_2plus__ring_pucker_1` | `job.xyz` (3791416_1) | `6c711c4e…` | pucker θ=-20° | $chrg=2, $spin=1 |
| `ec_v2_p2` | `EC|LiM_2plus__ring_pucker_2` | 同上 | 同上 | pucker θ=-10° | 同上 |
| `ec_v2_p3` | `EC|LiM_2plus__ring_pucker_3` | 同上 | 同上 | pucker θ=+10° | 同上 |
| `ec_v2_p4` | `EC|LiM_2plus__ring_pucker_4` | 同上 | 同上 | pucker θ=+20° | 同上 |
| `ec_v2_p5` | `EC|LiM_2plus__twist_1` | 同上 | 同上 | twist φ=30° | 同上 |

- **非刚体预检**：5 探针重骨架 RMSD 互核（阈值 0.35 Å），确保非同一极小副本
- **历史重复性**：与 `p4_02_ring_pucker_twist`（已 accepted 成员）去重比对，RMSD<0.35 Å 视为同盆地
- **候选门前置**：`candidate_gate_contract=validate_candidate_start_v2`（几何/身份/二面角验证）

### 4.2 产出登记

- 新包路径：`work/hpc_ec_recovery_v2_20261028/tasks/EC/LiM_2plus__<probe_name>/`
- 产出文件：`geom.xyz`（输入）、`job.xyz`（ORCA 末几何）、`job.log`、`job.hess`、`candidate.json`、`inputs.sha256`
- 识别链：`tasks.txt line i` → `array element i` → `sacct JobID "<array>_<i>"` → 该行的 `JobIDRaw`
- 不允许：使用其他态的几何、复用旧 Hessian、覆盖已有标签

## 5. 双重口径预防

- 成本只记 `AllocCPUS × ElapsedRaw`，不记 wall clock、不记 TotalCPU
- 父行、`.batch`/`.extern` 子行不进入结算
- 失败探针保留实测成本，不删除、不补零
- 系综标签只认 `accepted`，`limited` 不计入 `production_ensembles`

## 6. 版本化与可逆性

- 本草案 v0-draft-rev1，用户批准后升级为 v1-prereg
- 若用户拒绝，v0-draft-rev1 归档，不产生任何计算
- 若探针失败，下一轮须新版本（v2+），不允许沿用本版本 ID，且必须改变机制或起点

## 7. 提交与授权条件

- **必须**：用户对 v1-prereg 文本的**显式批准**（逐条审阅 §1-§4）
- **必须**：`candidate_gate_contract=validate_candidate_start_v2` 通过（几何/身份/二面角验证）
- **必须**：独立预算确认（≤32 CH，不与其他恢复包混用）
- **禁止**：自动启动、自动追加、绕过 `acceptance_decision`

## 8. 下游影响（修正 F2/F3）

- 本态通过：`plan_overall_complete` 仍为 `blocked_on_production`（需 DMC 两态也过才可能 satisfied）
- `strict_readiness_evidence` **仍为 5/6**（`wp5_full_target_pool_evaluated` 需 DMC 两态 + WP5 重跑回放）
- 系综从 45/48 → 46/48
- WP5 目标池须同步更新（B 池从 10/12 → 11/12，A 池仍为 11/12 缺 DMC）

## 9. 不变的红线（修正 F5）

- 阈值不放宽
- 方法不替换
- **分子集不扩展**：core set 18 分子与 broad pool 40 分子均不动
- 不将 `limited` 视为科学通过
- 不因预算压力而修改 `single_basin_verified` 判定标准
- 新版本成员须另立命名族且序号高于该成员全部历史序号

---

## 修订记录（对照独立审计 16 条缺陷）

| 缺陷 | 修订位置 | 修订内容 |
|------|----------|----------|
| F1（高） | §3.2-3.3 | 停止条件改为「单盆地+过 QC → accepted」，补三条件 |
| F2（高） | §1, §8 | 删除「strict 5/6→6/6」错误主张，改为「仍为 5/6」 |
| F3（中） | §8 | 删除「→ partial」不存在取值，改为「仍为 blocked_on_production」 |
| F4（中） | §3.1, §9 | 补命名族规则 |
| F5（中） | §9 | 「40 分子 core set」→「分子集不扩展：core 18 / broad pool 40」 |
| F10（中） | §2 | 补 resource profile、每腿墙钟、识别链、起点额度 |
| F11（中） | §4.1-4.2 | 逐探针给唯一名/父几何哈希/变形参数/身份预检/历史重复性/识别链 |
| F12（中） | §7 | 补候选门前置 |
| F13（中） | §3.2 | 补 `single_basin_verified` 三条件 |
| F15（低） | §2 | 「停止预算」改为数值化表述（累计 CH + 每腿墙钟） |

**未修正缺陷**：F6-F9, F14, F16 属 DMC 草案或跨草案一致性问题，见 DMC 修订版。
