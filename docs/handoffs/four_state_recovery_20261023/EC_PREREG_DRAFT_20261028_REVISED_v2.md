# EC 下一轮预注册草案（设计-only，不提交、不预算、不启动）——修订版 v2

> **性质**：设计草稿，供用户审议。不触发提交、不占用预算、不改动任何现有标签或判定。  
> **版本**：v0-draft-rev2（2026-10-28）  
> **对应缺口**：`ensemble_not_48_accepted` → `EC|LiM_2plus` limited  
> **修订依据**：独立审计 `REPORT_independent_t7.md` 16 条缺陷 + 用户具体修正指示

## 1. 目标态与方法

- 目标态：`EC|LiM_2plus`（当前 limited，reopt TolE 3.18× 二次超差）
- 方法：wB97X-D4/def2-TZVPD + SMD(acetonitrile)，Opt VeryTightOpt AnFreq（冻结方法不变）
- 判定路径：`single_basin_verified`（独立起点验证，**不要求找到第二个极小**，但必须通过六项验收）
- 严格总闸门关联：本态通过 → `production_ensembles=46/48`；**严格 readiness 仍为 5/6**（需 DMC 两态也 accepted 才可能 6/6）

## 2. 预算与资源（修正 profile/墙钟/预算算式）

| 项 | 值 |
|---|---|
| 本轮可用预算（授权硬上限） | ≤32 CH（**新授权额度**；独立于 600 CH 恢复包与 800 CH 框架） |
| 资源 profile | `orca_production_v1`（4 核/腿，**wall_hours=24**，实测 96 CH/腿） |
| 每腿墙钟 | 24 h（profile 默认值） |
| 并发上限 | 1 腿（**与 DMC 串行**） |
| 逐腿费用 | 4 核 × 24 h = **96 CH/腿**（实测口径） |
| 最坏预留（5 探针） | 5 × 96 = **480 CH**（远超 32 CH 上限） |
| 实际可行方案 | **逐腿提交、累计 ≤32 CH 即停**；允许预算不足时少于 5 条 |
| 核算口径 | `per_element_core_hours()`（`<array>_<index>` 识别，防交叉互换） |

**预算约束说明**：
- 32 CH 上限仅够 **0.33 腿**（按 96 CH/腿）
- 若要求完成 5 条 4 核×4 小时计算，须申请专用 profile（如 `orca_production_4h_v1`），最坏预留 80 CH
- 当前草案**不匹配** 32 CH 预算与 24 h profile；须用户裁决：① 提高预算 ② 改 profile ③ 减少探针数

## 3. 探针与路径定义（修正父几何/枚举/角色）

### 3.1 起点与探针（候选尚未生成）

> **状态**：候选定义就绪，几何尚未生成。

- **命名族**：`hpc_ec_recovery_v2_20261028`（序号高于历史）
- **输入几何来源**：`work/hpc_dol_ec_recovery_v1_reopt_20261027/snapshots/3791416_1/job.xyz`
- **真末几何 SHA256**：`a0a8d53b1e6083c4212d98d844350ce3248c38d201b82f9f3f40936341cd969b`
- **注意**：`6c711c4e…` 是输入 `geom.xyz`，非末几何

### 3.2 候选定义（待生成）

| 探针名 | 父几何 | 变形参数 | 身份 | 状态 |
|---|---|---|---|---|
| `ec_v2_p1` | `job.xyz` (SHA256 `a0a8d53b…`) | pucker θ=-20° | $chrg=2,$spin=1 | **未生成** |
| `ec_v2_p2` | 同上 | pucker θ=-10° | 同上 | **未生成** |
| `ec_v2_p3` | 同上 | pucker θ=+10° | 同上 | **未生成** |
| `ec_v2_p4` | 同上 | pucker θ=+20° | 同上 | **未生成** |
| `ec_v2_p5` | 同上 | twist φ=30° | 同上 | **未生成** |

**预检项**（生成后须逐个验证）：
- 父文件完整 SHA256
- 新几何 SHA256
- 变形参数（二面角/扭转角）
- 身份（$chrg/$spin）
- 非刚体变化（重骨架 RMSD 互核）
- 历史重复性（与已 accepted 成员去重比对）

### 3.3 判定条件（`single_basin_verified`）

| # | 条件 | 判定标准 |
|---|---|----------|
| ① | `production_evidence` 完整 | 六项验收齐全（五阈值+身份+0 虚频+热化学+连接关系） |
| ② | `search_scope_documented` | `registered_starts` 非空且 `search_outcome` ∈ {`new_minima_found`, `no_new_minimum_found`, `unused_pool_basin_no_search_needed`} |
| ③ | 进 `latest_members` | 角色在聚合器白名单（`round1_extra`, `recovery_v1_start`） |

**注意**：聚合器目前**不接受** `recovery_v2_start`；新包须沿用已支持角色或先更新消费者。

### 3.4 搜索结论枚举（现行契约）

- `new_minima_found` — 发现新极小
- `no_new_minimum_found` — 无新极小（单盆地）
- `unused_pool_basin_no_search_needed` — 未搜索（池 basin）

**草案错误**：此前 invented `new_minimum_resolved`、`same_basin_reproduction` 不被代码接受。

## 4. 标识链与输入哈希

### 4.1 候选登记（生成后）

- 新包路径：`work/hpc_ec_recovery_v2_20261028/tasks/EC/LiM_2plus__<probe_name>/`
- 产出文件：`geom.xyz`（输入）、`job.xyz`（ORCA 末几何）、`job.log`、`job.hess`、`candidate.json`、`inputs.sha256`
- 识别链：`tasks.txt line i` → `array element i` → `sacct JobID "<array>_<i>"` → 该行 `JobIDRaw`

### 4.2 候选门前置

- `candidate_gate_contract=validate_candidate_start_v2`（几何/身份/二面角验证）

## 5. 双重口径预防

- 成本只记 `AllocCPUS × ElapsedRaw`
- 失败探针保留实测成本，不删除、不补零
- 系综标签只认 `accepted`，`limited` 不计入

## 6. 版本化与可逆性

- 本草案 v0-draft-rev2，用户批准后升级为 v1-prereg
- 若探针失败，下一轮须新版本（v2+），不允许沿用本版本 ID

## 7. 提交与授权条件

- **必须**：用户对 v1-prereg 文本的显式批准
- **必须**：`candidate_gate_contract` 通过
- **必须**：独立预算确认（≤32 CH）
- **禁止**：自动启动、自动追加、绕过 `acceptance_decision`

## 8. 下游影响

- 本态通过：`production_ensembles=46/48`
- `strict_readiness_evidence`**仍为 5/6**
- `plan_overall_complete`**仍为 blocked_on_production**（需 DMC 两态也过才可能 satisfied）

## 9. 不变的红线

- 阈值不放宽
- 方法不替换
- 分子集不扩展（core set 18 / broad pool 40）
- 不将 `limited` 视为科学通过
- 新版本成员须另立命名族且序号高于历史

---

## 待完成（实体化清单）

| # | 事项 | 状态 |
|---|---|---|
| 1 | 修正 profile 与预算冲突（或申请专用 profile） | **待裁决** |
| 2 | 生成 5 个候选几何，给出完整 SHA256/变形参数/身份/预检 | **未开始** |
| 3 | 用受保护提交器加载器验证实际资源 | **未开始** |
| 4 | 做包含真实 manifest 的导入/覆盖测试 | **未开始** |
| 5 | 包保持 HOLD，交付逐项通过结果 | **未开始** |

**建议**：先不批准立即提交；批准材料应是可执行包及其验证结果，而非目前这份文字修订稿。
