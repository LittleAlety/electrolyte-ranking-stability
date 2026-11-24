# DMC 下一轮预注册草案（设计-only，不提交、不预算、不启动）——修订版 v1

> **性质**：设计草稿，供用户审议。不触发提交、不占用预算、不改动任何现有标签或判定。  
> **版本**：v0-draft-rev1（2026-10-28）  
> **对应缺口**：`ensemble_not_48_accepted` → `DMC|M_plus`、`DMC|LiM_2plus` limited  
> **修订依据**：独立审计 `REPORT_independent_t7.md` 16 条缺陷（F1-F16）

## 1. 目标态与现状（修正 F6/F7）

### 1.1 三层失败证据（拆开陈述，不再混为一谈）

| 层 | 证据 | 结论 |
|---|---|---|
| **生产层** | **8 条失败腿**：`verytight_convergence`×3、`max_cycles_exhausted`×2、`strict_reopt_required`×3。4/5 阈值过；**MAXstep（TolMaxD）差 1.6×** 或 **TolE 差 2.2×**；循环 16–23 显示是**平台不是尾巴** | 浅赝平坦谷：梯度过达标、位移/能量在阈值边缘震荡 |
| **重优化通道** | reopt1–4 + reopt_v2，att=1/2/5/12 **全部同型失败** | 从平台重启仍得平台（已被 4 次证伪） |
| **GFN2 交叉验证** | P4 筛选（job 3774215）所有 DMC 探针弛豫回 `C01#m1` 同一极小（RMSD 0.0013 Å） | **筛选轮，非生产尝试**；GFN2 下清晰单盆地 |

### 1.2 关键诊断

> **DMC 不缺新起点，缺的是能过五阈值的优化设定**——而设定属**冻结项**。

- `DMC|M_plus`：**无 Li**（电荷 +1，`record_id=C01|M_plus`），Li 配位类机制**不适用**
- `DMC|LiM_2plus`：**有 Li**（电荷 +2，`record_id=C01|LiM_2plus`），Li 配位类机制适用

## 2. 新机制选项与逐态适用性（修正 F5/F7 的「新实验定义」缺口）

### 2.1 机制比较表

| 选项 | 机制 | 适用态 | 相较历史尝试改变了什么 | 预期观测检验 | 预估成本 |
|---|---|---|---|---|---|
| **A** | 显式 Li 配位几何 + xTB 短程预优化 | **仅 `DMC\|LiM_2plus`** | 历史 8 腿起点均来自生产腿几何（Li 配位未显式变形）；A 用登记 Li 配位探针（`toward_3`, offset 0.45 Å）作新起点 | 新起点在 GFN2 下是否仍弛豫回 `C01#m1`（若是⇒仍单盆地）；DFT 下 MAXstep/TolE 是否进入阈值 | 2 腿 ≈ 37 CH（含 xTB 预优化，**按超算计**） |
| **B** | 不同廉价预优化（GFN2-xTB VeryTight） | 两态均可 | 历史预优化为默认档；B 升到 VeryTight，改变进入 DFT 的几何精度 | DFT 首轮 MAXstep 是否从 1.6× 收敛进阈值 | 2 腿 ≈ 37 CH |
| **C** | 直接 DFT 多起点（无预优化） | 两态均可 | 历史均经预优化；C 完全绕过预优化，用裸几何作起点 | 无预优化是否会落入更陡的下降方向 | 2–4 腿 ≈ 37–74 CH（风险最高） |

### 2.2 逐态机制选择建议

| 态 | 可用机制 | 说明 |
|---|---|---|
| `DMC\|M_plus` | **B 或 C** | 无 Li ⇒ A 不可用。历史 8 腿已证「同设定重试必败」，故须改预优化路径（B）或去预优化（C） |
| `DMC\|LiM_2plus` | **A / B / C** | 三选一，A 最有针对性（Li 配位是本态特征自由度） |

### 2.3 未决事项（须用户裁决）

- 两态各选哪个机制？合计几腿（2 腿 ≈37 CH / 4 腿 ≈74 CH）？
- 若两态都选，是否串行（避免与 EC 冲突）？

**用户裁决前**：以上仅为设计可能性，不预决、不建包、不提交。

## 3. 预算与资源（修正 F8/F10）

| 项 | 值 |
|---|---|
| 本轮可用预算 | **新授权额度**（另立版本）；**不是**「rescue 上限」——两态 `limitation_reason=rescue_budget_exhausted`，账本明写「再算需要另立版本，不是继续花这一包」 |
| 与既有框架关系 | **独立于** 600 CH 恢复包与 800 CH 四态框架；须用户单独批准额度 |
| 资源 profile | `orca_production_v1`（4 核/腿） |
| 每腿墙钟 | 4 h（默认）；xTB 预优化腿另计，按实际 profile |
| 并发上限 | **与 EC 串行**（EC 1 腿 → DMC 至多 2 腿，但须账户 running+pending ≤2 才投下一批） |
| 核算口径 | `per_element_core_hours()`（`<array>_<index>` 识别，防交叉互换） |
| 停止预算 | 按实际腿数：2 腿 ≈37 CH、4 腿 ≈74 CH（p90 18.41 × 腿数 × 1.5 缓冲）；**停止预算 < 授权上限**，二者约束关系：累计成本达停止预算即停 |
| 每态起点额度 | ≤2 独立起点 + ≤1 有因补救（授权明文；本轮尝试额度已耗尽，须用户重开） |

## 4. 停止条件

- 任一新起点生产腿过六项验收（五阈值+身份+0 虚频+热化学+连接关系）→ `resolved` → `accepted`
- 全起点均失败 → `unresolved` → 状态保持 `limited`
- 成本达停止预算或方法故障 → `limited`
- 物种漂移或不可恢复身份 → `limited`

## 5. 标识链与输入哈希（修正 F11 同款精度）

### 5.1 候选清单（现有可用起点）

| 态 | 候选唯一名 | 父几何 | 父几何 SHA256 | 变形参数 | 身份 |
|---|---|---|---|---|---|
| `DMC\|M_plus` | `dmc_v2_M_plus_tors_0_1_2_3` | `work/hpc_frontier_localization_v1/tasks/DMC__M_plus__primary/geom.xyz` | `5b9e93e0…` | torsion `tors_0_1_2_3`（重原子对变化 0.2743 Å） | $chrg=1, $spin=1 |
| `DMC\|M_plus` | `dmc_v2_M_plus_tors_1_2_4_5` | 同上 | 同上 | torsion `tors_1_2_4_5`（0.2432 Å） | 同上 |
| `DMC\|LiM_2plus` | `dmc_v2_LiM_2plus_tors_0_1_2_3` | `work/hpc_frontier_localization_v1/tasks/DMC__LiM_2plus__primary/geom.xyz` | `f619c132…` | torsion `tors_0_1_2_3`（0.4874 Å） | $chrg=2, $spin=1 |
| `DMC\|LiM_2plus` | `dmc_v2_LiM_2plus_toward_3` | 同上 | 同上 | Li 配位 `toward_3`（offset 0.45 Å） | 同上 |

- **候选几何已就绪**：以上 4 个 `geom.xyz` + `candidate.json` 均存在于 `work/hpc_four_state_p4_xtb_screening_v1/tasks/`
- **非刚体预检**：候选间重骨架 RMSD 互核（阈值 0.35 Å）
- **历史重复性**：与 8 条失败腿起点比对，RMSD<0.35 Å 者视为同起点，不得重复计入
- **候选门前置**：`candidate_gate_contract=validate_candidate_start_v2`

### 5.2 产出登记

- **命名族**：`hpc_dmc_recovery_v2_20261028`（序号高于该成员全部历史序号）
- 新包路径：`work/hpc_dmc_recovery_v2_20261028/tasks/<name>/<slot>__<seed>/`
- 起点几何：来源哈希登记于 `candidate.json` + `inputs.sha256`
- 识别链：`tasks.txt line i` → `array element i` → `sacct JobID "<array>_<i>"` → 该行 `JobIDRaw`
- 不允许：使用其他分子几何、复用旧 Hessian、覆盖已有标签、回填旧池

## 6. 双重口径预防

- 成本只记 `AllocCPUS × ElapsedRaw`，拒绝 `.batch`/`.extern`
- 失败尝试保留实测成本，不删除、不补零
- 系综标签只认 `accepted`，`limited` 不计入 `production_ensembles`
- 不将 `rescue_budget_exhausted` 视为科学通过

## 7. 版本化与可逆性

- 本草案 v0-draft-rev1，用户批准后升级为 v1-prereg
- 若用户拒绝，v0-draft-rev1 归档，不产生任何计算
- 若 v1 失败，v2 必须改变机制（A/B/C 切换或新机制），不允许沿用 v1 配置

## 8. 提交与授权条件

- **必须**：用户对 v1-prereg 文本的**显式批准**（含 §2.3 的机制选择与腿数）
- **必须**：`candidate_gate_contract=validate_candidate_start_v2` 通过
- **必须**：新授权额度确认（独立于 600/800 框架）
- **禁止**：自动启动、自动追加、绕过 `acceptance_decision`

## 9. 下游影响（修正 F14）

- 两态通过 + EC 通过 ⇒ 系综 48/48，`plan_overall_complete` 可为 `satisfied`
- `strict_readiness_evidence`：池前置满足（A=12, B=12），但**闸门 2 仍要求按正式协议重跑 A/B 盲回放并通过停止预算判据**（四策略×四模型×20 repeats、两相邻非耗尽预算点）⇒ 不是自动 6/6
- WP5 目标池须同步更新

## 10. 不变的红线（修正 F5/F4）

- 阈值不放宽
- 方法不替换（wB97X-D4/def2-TZVPD + SMD 不变；A/B 的 xTB 预优化属计划预案，最终 DFT 腿仍走冻结协议 + 六项验收）
- **分子集不扩展**：core set 18 分子与 broad pool 40 分子均不动
- 不将 `limited` 视为科学通过
- 不因预算压力而修改 `single_basin_verified` 判定标准
- 不无限重复审计或自动追加计算
- **新版本成员须另立命名族且序号高于该成员全部历史序号**
- **不得只对 DMC 两态换冻结设定取有利结果**（若换设定须全 cohort 重算可比性，见 `DMC_DECISION_BRIEF_20261027.md` §3 B1）

---

## 修订记录（对照独立审计 16 条缺陷）

| 缺陷 | 修订位置 | 修订内容 |
|------|----------|----------|
| F4（中） | §5.2, §10 | 补命名族规则 |
| F5（中） | §10 | 「40 分子 core set」→「分子集不扩展：core 18 / broad pool 40」 |
| F6（中） | §1.1 | 「TolE 超差 1.6×」→「MAXstep 差 1.6× 或 TolE 差 2.2×」 |
| F7（中） | §1.1 | 拆成生产层/重优化/GFN2 三条独立事实，P4 标为筛选轮 |
| F8（中） | §3 | 「rescue 上限」→「新授权额度（另立版本）」 |
| F9（中） | §3 | 并发规则统一为「与 EC 串行 + running+pending ≤2」 |
| F10（中） | §3 | 补 resource profile、每腿墙钟、停止预算与授权上限的约束关系 |
| F14（低-中） | §9 | 补「须重跑 A/B 盲回放并通过停止预算判据」 |
| F16（低） | §8 | 删除范围未定义的「gate code audit」，改引候选门契约 |
| 新实验定义 | §2.1-2.2 | 逐态适用性 + 相较历史改变了什么 + 预期观测检验 + 成本 |

**跨草案一致性**：并发规则（F9）与 EC 修订版 §2 一致（串行）。
