# DMC 下一轮预注册草案（设计-only，不提交、不预算、不启动）

> **性质**：设计草稿，供用户审议。不触发提交、不占用预算、不改动任何现有标签或判定。
> **版本**：v0-draft（2026-10-28）
> **对应缺口**：`ensemble_not_48_accepted` → `DMC|M_plus`、`DMC|LiM_2plus` limited

## 1. 目标态与现状

- 目标态：`DMC|M_plus`、`DMC|LiM_2plus`（两轮尝试均 failed QC，用户裁决本轮停止）
- 历史失败原因：
  - 第一轮：TolE 超差 1.6×–2.2×，几何震荡于平台，无物种漂移
  - 第二轮（p4 筛选后）：未提交，因 p4 筛选无新起点；用户裁决停止
- 本轮诊断结论：需**新机制**（改变起点策略、预优化路径或配位几何），不可沿用旧池

## 2. 新机制选项（设计阶段，用户裁决前未定）

### 选项 A：显式 Li 配位几何
- 起点：Li 配位探针（登记 torsion 合法位移，如 tors_8_0_1_2）
- 预优化：xTB 预优化到 3 步，再转 DFT
- 判定：`single_basin_verified`（不要求第二个盆地）

### 选项 B：不同廉价预优化
- 起点：原始候选几何，但改用 GFN2-xTB VeryTight 预优化
- 预优化：xTB 收敛后转 DFT
- 判定：同上

### 选项 C：直接 DFT 多起点（无预优化）
- 起点：几何扰动后直接用冻结 DFT 方法
- 风险：成本高，须严格预算上限
- 判定：同上

**用户裁决前**：以上选项仅为设计可能性，不预决。

## 3. 预算与资源

| 项 | 值 |
|---|---|
| 本轮可用预算 | ≤256 CH（rescue 上限；须用户明确授权） |
| 并发上限 | 4 核/腿，最多 2 腿并行（避免与 EC 冲突） |
| 核算口径 | `per_element_core_hours()`（按元素结算，防交叉互换） |
| 停止预算 | 单腿 p90（18.41 CH）× 2 × 1.5 缓冲 ≈ 55 CH；或用户设定的更低硬上限 |

## 4. 停止条件

- 任一新起点通过 QC（五阈值、身份、0 虚频）→ `resolved` → `accepted`
- 全起点均失败 → `unresolved` → 状态保持 `limited`
- 成本超限或方法故障 → `limited`
- 物种漂移或不可恢复身份 → `limited`

## 5. 标识链与输入哈希

- 新起点来源：须登记于 `work/<new_package>/tasks/<name>/<slot>__<seed>/`
- 起点几何：来源哈希登记于 `candidate.json` + `inputs.sha256`
- 方法模板：冻结方法不变，预优化选项须在 prereg 中声明
- 不允许：使用其他分子的几何、复用旧 Hessian、覆盖已有标签

## 6. 双重口径预防

- 成本只记 `AllocCPUS × ElapsedRaw`，拒绝 `.batch`/`.extern`
- 失败尝试保留实测成本，不删除、不补零
- 系综标签只认 `accepted`，`limited` 不计入 `production_ensembles`
- 不将 `rescue_budget_exhausted` 视为科学通过

## 7. 版本化与可逆性

- 本草案 v0-draft，用户批准后升级为 v1-prereg
- 若用户拒绝，v0-draft 归档，不产生任何计算
- 若 v1 失败，v2 必须改变机制（选项 A/B/C 切换或新机制），不允许沿用 v1 配置

## 8. 提交与授权条件

- **必须**：用户对 v1-prereg 文本的显式批准
- **必须**：gate code audit 通过（不新增 audit 缺陷）
- **必须**：独立预算确认（≤256 CH，不与其他恢复包混用）
- **必须**：新起点来源通过 `candidate_gate_contract=validate_candidate_start_v2`（几何/身份/二面角验证）
- **禁止**：自动启动、自动追加、绕过 `acceptance_decision`

## 9. 下游影响

- 通过 2 态：`plan_overall_complete` 从 `blocked_on_production` → `satisfied`（若 EC 也过）
- `strict_readiness_evidence` 从 5/6 → 6/6（若 EC 也过）
- 系综从 45/48 → 47/48（若 EC 过则为 48/48）
- WP5 目标池须同步更新（新增 1-2 个 accepted 态）

## 10. 不变的红线

- 阈值不放宽
- 方法不替换（wB97X-D4/def2-TZVPD + SMD 不变）
- 40 分子 core set 不扩展
- 不将 `limited` 视为科学通过
- 不因预算压力而修改 `single_basin_verified` 判定标准
- 不无限重复审计或自动追加计算
