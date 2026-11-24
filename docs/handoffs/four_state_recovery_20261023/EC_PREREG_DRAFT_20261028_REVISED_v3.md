# EC 下一轮预注册草案（设计-only，不提交、不预算、不启动）——修订版 v3

> **性质**：设计草稿，供用户审议。不触发提交、不占用预算、不改动任何现有标签或判定。  
> **版本**：v0-draft-rev3（2026-10-28）  
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
| 资源 profile | `orca_production_4h_v1`（**4 核/腿，4 小时，16 CH/腿**） |
| 每腿墙钟 | 4 h（profile 默认值） |
| 并发上限 | 1 腿（**串行执行**） |
| 逐腿预留 | 4 核 × 4 h = **16 CH/腿** |
| 最大腿数 | **2 腿**（最坏预留 32 CH） |
| 停止策略 | 第一腿通过完整科学验收（六项）即停止；两腿用尽/超时/未通过则保留 limited |
| 核算口径 | `per_element_core_hours()`（`<array>_<index>` 识别，防交叉互换） |

**预算约束说明**：
- 32 CH = 2 腿 × 16 CH（最坏预留）
- 4 h 是运行上限，不保证收敛
- 串行执行确保 running+pending ≤1 ≤2 账户规则

## 3. 探针与路径定义（修正父几何/枚举/角色）

### 3.1 起点与探针（候选已生成）

> **状态**：候选已生成（6个），预检通过。

- **命名族**：`hpc_ec_recovery_v2_20261028`（序号高于历史）
- **输入几何来源**：`work/hpc_dol_ec_recovery_v1_reopt_20261027/snapshots/3791416_1/job.xyz`
- **真末几何 SHA256**：`a0a8d53b1e6083c4212d98d844350ce3248c38d201b82f9f3f40936341cd969b`
- **注意**：`6c711c4e…` 是输入 `geom.xyz`，非末几何

### 3.2 候选清单（6个已生成）

| 候选名 | 模式 | 振幅 | 新几何 SHA256 | 骨架 RMSD vs 源 | 门判定 |
|---|---|---|---|---|---|
| `ec_v2_p3` | envelope | -0.10 Å | `7b047f34c5a7…` | 0.027169 | ok_heavy_fragment |
| `ec_v2_p4` | twist | -0.10 Å | `1c04e3b80f7d…` | 0.044653 | ok_heavy_fragment |
| `ec_v2_p5` | envelope | +0.10 Å | `a7e9caaf528e…` | 0.027149 | ok_heavy_fragment |
| `ec_v2_p6` | twist | +0.10 Å | `0f5c89cbcdc8…` | 0.044494 | ok_heavy_fragment |
| `ec_v2_p7` | envelope | +0.20 Å | `4cf903d4ff3a…` | 0.054279 | ok_heavy_fragment |
| `ec_v2_p8` | twist | +0.20 Å | `9ad9c25139e7…` | 0.088827 | ok_heavy_fragment |

- **拒绝 4 个**：振幅 ±0.30 Å 全部 `bond_broken`（环键断裂）
- **非刚体预检**：全部通过（骨架 RMSD 0.027–0.089 Å，均 > 0.01）
- **身份验证**：$chrg=2, $spin=1, mol_id=C04, record_id=C04|LiM_2plus

### 3.3 预选 2 个生产腿（按覆盖最大化）

| 顺序 | 候选名 | 模式 | 振幅 | 选择理由 |
|---|---|---|---|---|
| **腿 1** | `ec_v2_p4` | twist | -0.10 Å | twist 模式，中等变形，与 P4 起点不同 |
| **腿 2** | `ec_v2_p7` | envelope | +0.20 Å | envelope 模式，较大变形，覆盖正向幅度 |

**备选**：若腿1失败或超时，依次递补 `ec_v2_p8` → `ec_v2_p3` → `ec_v2_p5` → `ec_v2_p6`

### 3.4 判定条件（`single_basin_verified`）

| # | 条件 | 判定标准 |
|---|---|----------|
| ① | `production_evidence` 完整 | 六项验收齐全（五阈值+身份+0 虚频+热化学+连接关系） |
| ② | `search_scope_documented` | `registered_starts` 非空且 `search_outcome` ∈ {`new_minima_found`, `no_new_minimum_found`, `unused_pool_basin_no_search_needed`} |
| ③ | 进 `latest_members` | 角色在聚合器白名单（`round1_extra`, `recovery_v1_start`） |

### 3.5 搜索结论枚举（现行契约）

- `new_minima_found` — 发现新极小
- `no_new_minimum_found` — 无新极小（单盆地）
- `unused_pool_basin_no_search_needed` — 未搜索（池 basin）

## 4. 标识链与输入哈希

### 4.1 候选登记（已生成）

- 包路径：`work/hpc_ec_recovery_v2_20261028/tasks/EC/LiM_2plus__<probe_name>/`
- 产出文件：`geom.xyz`、`candidate.json`、`inputs.sha256`
- 识别链：`tasks.txt line i` → `array element i` → `sacct JobID "<array>_<i>"` → 该行 `JobIDRaw`

### 4.2 候选门前置

- `candidate_gate_contract=validate_candidate_start_v2`（几何/身份/二面角验证）

## 5. 双重口径预防

- 成本只记 `AllocCPUS × ElapsedRaw`
- 失败探针保留实测成本，不删除、不补零
- 系综标签只认 `accepted`，`limited` 不计入

## 6. 版本化与可逆性

- 本草案 v0-draft-rev3，用户批准后升级为 v1-prereg
- 若探针失败，下一轮须新版本（v2+），不允许沿用本版本 ID

## 7. 提交与授权条件

- **必须**：用户对 v1-prereg 文本的显式批准（含 §3.3 预选 2 腿清单）
- **必须**：`candidate_gate_contract` 通过
- **必须**：预算检查通过（已用 + 在飞 + 新腿预留 ≤ 32 CH）
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

## 实体化清单（已完成）

| # | 事项 | 状态 |
|---|---|---|
| 1 | 新增 `orca_production_4h_v1` profile | ✅ 已添加至 submit_hpc_batch.py |
| 2 | 生成 6 个候选几何 | ✅ 本地完成，预检通过 |
| 3 | 预选 2 个生产腿（覆盖最大化） | ✅ 草案 §3.3 |
| 4 | 用提交器加载器验证资源 | ⏳ 待运行 |
| 5 | 做包含真实 manifest 的导入测试 | ⏳ 待运行 |
| 6 | 包保持 HOLD | ✅ 当前状态 |

**建议暂不批准立即提交**；批准材料应是可执行包及其验证结果。
