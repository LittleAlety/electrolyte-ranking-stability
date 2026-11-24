# EC 下一轮预注册草案（设计-only，不提交、不预算、不启动）

> **性质**：设计草稿，供用户审议。不触发提交、不占用预算、不改动任何现有标签或判定。
> **版本**：v0-draft（2026-10-28）
> **对应缺口**：`ensemble_not_48_accepted` → `EC|LiM_2plus` limited

## 1. 目标态与方法

- 目标态：`EC|LiM_2plus`（当前 limited，reopt 失败）
- 方法：wB97X-D4/def2-TZVPD + SMD(acetonitrile)，Opt VeryTightOpt AnFreq（冻结方法不变）
- 判定路径：`single_basin_verified`（独立起点验证，不要求找到第二个极小）
- 严格总闸门关联：通过 → `production_ensembles=46/48`；仍失败 → 保持 `limited`

## 2. 预算与资源

| 项 | 值 |
|---|---|
| 本轮可用预算 | ≤32 CH（独立于 600 CH 恢复包；须另立版本） |
| 并发上限 | 1 腿（不可与 DMC 并行） |
| 核算口径 | `per_element_core_hours()`（AllocCPUS × ElapsedRaw / 3600，按元素结算） |
| 停止预算 | TolE 再次失败、成本超限、或达到探针边界 |

## 3. 探针与路径定义

- 已注册合法探针：pucker/twist 5 个连续二面角（不改变骨架、不打断环）
- 探针方向：从 reopt 收敛末几何沿登记二面角路径展开
- 停止条件：
  - 任一探针到达另一盆地 → `resolved` → `accepted`
  - 5 探针均仍单盆地 → `unresolved` → 状态维持 `limited`（不追加）
  - 成本超限或方法故障 → `limited`

## 4. 标识链与输入哈希

- 输入几何：reopt 收敛末几何（SHA256 登记于 `work/hpc_dol_ec_recovery_v1_reopt_20261027/`）
- 方法模板：`config/physics_completion_v1.yaml` + `orca_input_template.inp`
- 产出登记：`work/<new_package>/tasks/EC/LiM_2plus__p4_02_ring_pucker_twist/`
- 不允许：使用其他态的几何、复用旧 Hessian、覆盖已有标签

## 5. 双重口径预防

- 成本只记 `AllocCPUS × ElapsedRaw`，不记 wall clock、不记 TotalCPU
- 父行、`.batch`/`.extern` 子行不进入结算
- 失败探针保留实测成本，不删除、不补零
- 系综标签只认 `accepted`，`limited` 不计入 `production_ensembles`

## 6. 版本化与可逆性

- 本草案 v0-draft，用户批准后升级为 v1-prereg
- 若用户拒绝，v0-draft 归档，不产生任何计算
- 若探针失败，下一轮须新版本（v2+），不允许沿用本版本 ID

## 7. 提交与授权条件

- **必须**：用户对 v1-prereg 文本的显式批准
- **必须**：gate code audit 通过（不新增 audit 缺陷）
- **必须**：独立预算确认（≤32 CH，不与其他恢复包混用）
- **禁止**：自动启动、自动追加、绕过 `acceptance_decision`

## 8. 下游影响

- 通过：`plan_overall_complete` 从 `blocked_on_production` → `partial`（余 DMC）
- `strict_readiness_evidence` 从 5/6 → 6/6
- 系综从 45/48 → 46/48
- WP5 目标池须同步更新（新增 1 个 accepted 态）

## 9. 不变的红线

- 阈值不放宽
- 方法不替换
- 40 分子 core set 不扩展
- 不将 `limited` 视为科学通过
- 不因预算压力而修改 `single_basin_verified` 判定标准
