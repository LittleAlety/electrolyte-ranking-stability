# DMC 下一轮预注册草案（设计-only，不提交、不预算、不启动）——修订版 v3

> **性质**：设计草稿，供用户审议。不触发提交、不占用预算、不改动任何现有标签或判定。  
> **版本**：v0-draft-rev3（2026-10-28）  
> **对应缺口**：`ensemble_not_48_accepted` → `DMC|M_plus`、`DMC|LiM_2plus` limited  
> **修订依据**：独立审计 `REPORT_independent_t7.md` 16 条缺陷 + 用户具体修正指示

## 0. 本轮定位（重要）

**本轮不追加 DMC 计算。** 本草案只做**机制论证**：
- 用已有日志证明 A/B/C 中哪项值得试
- 证明该机制相较历史尝试**实际改变了什么**
- 形成**具体实验定义**（候选、资源、停止条件）

**未完成上述论证前，不进入预算裁决、不建包、不提交。**

## 1. 目标态与现状（修正失败史口径）

### 1.1 三层失败证据

| 层 | 证据 | 结论 |
|---|---|---|
| **生产层** | 8 条失败腿：`verytight_convergence`×3、`max_cycles_exhausted`×2、`strict_reopt_required`×3。4/5 阈值过；**MAXstep（TolMaxD）差 1.6×** 或 **TolE 差 2.2×** | 浅赝平坦谷 |
| **重优化** | reopt1–4 + reopt_v2，att=1/2/5/12 全部同型失败 | 从平台重启仍得平台 |
| **GFN2 筛选** | P4 筛选（job 3774215）所有探针弛豫回 `C01#m1`（RMSD 0.0013 Å） | **筛选轮，非 production 尝试** |

### 1.2 逐态机制适用性

| 态 | 特征 | 可用机制 |
|---|---|---|
| `DMC\|M_plus` | 无 Li（charge=1） | B（GFN2 VeryTight 预优化）或 C（直接 DFT 多起点） |
| `DMC\|LiM_2plus` | 有 Li（charge=2） | A（显式 Li 配位）/ B / C 均可 |

## 2. 机制论证要求（本轮核心工作）

### 2.1 必须回答的问题（每项机制）

| # | 问题 | 要求 |
|---|---|---|
| 1 | 相较历史尝试**实际改变了什么**？ | 点名改动的参数/起点/路径，不得只说"换设置" |
| 2 | 为什么**预期能解决**已知失败模式（平台震荡/TolE超差）？ | 给出机制性理由，不接受"试试看" |
| 3 | 用什么**观测检验**证明改变生效？ | 可判定的中间量（如 GFN2 下是否仍回同一极小） |
| 4 | **不改变**冻结项（五阈值/方法/cohort）？ | 逐条声明 |

### 2.2 逐选项待论证内容

| 选项 | 待论证 |
|---|---|
| **A（Li 配位 + xTB 短程预优化）** | ① 为何 Li 配位变形能打破平台？② xTB 预优化几步？③ 仅适用于 LiM_2plus，M_plus 如何另议？ |
| **B（GFN2 VeryTight 预优化）** | ① 历史默认预优化档是什么？VeryTight 改变了什么？② 为何能改善进入 DFT 的几何？ |
| **C（直接 DFT 多起点）** | ① 无预优化为何不会落入更陡方向？② 与历史 8 腿起点有何不同？③ 成本如何控制？ |

### 2.3 论证材料来源（已有，无需新计算）

- `DMC_THRESHOLD_DIAGNOSIS_20261025.md`（§2 统一判读表、§3 下一步含义、§4 GFN2 交叉验证）
- `production_ensemble_structures.csv`（DMC 两态 8 条 `technical_complete_qc_failed` 的 qc_flags）
- `strict_recovery_v1_report.md:63-64`（逐条失败腿）

## 3. 候选（现状，非新机制）

### 3.1 现有 4 个 P4 起点（**保留为历史起点，不构成新机制**）

| 态 | 候选名 | 父几何 SHA256 | 类型 |
|---|---|---|---|
| `DMC\|M_plus` | `dmc_v2_M_plus_01_torsion` | `432fe3b7a621…` | torsion 0.2743 Å |
| `DMC\|M_plus` | `dmc_v2_M_plus_02_torsion` | `952d0817a489…` | torsion 0.2432 Å |
| `DMC\|LiM_2plus` | `dmc_v2_LiM_2plus_01_torsion` | `52a4d879149a…` | torsion 0.4874 Å |
| `DMC\|LiM_2plus` | `dmc_v2_LiM_2plus_02_li_coord` | `9038baccfb37…` | Li 配位 0.45 Å |

**明确声明**：这 4 个是 P4 筛选包的原几何，**换名不算新机制**。它们只能作为新机制的**起点输入**。

### 3.2 新机制候选（待论证后生成）

- 选项 A：需在 LiM_2plus 上做 xTB 预优化（**按超算计**）
- 选项 B：需跑 GFN2-xTB VeryTight 预优化（**按超算计**）
- 选项 C：需新扰动几何（纯几何可本地生成）

## 4. 预算（本轮不适用，仅列口径供参考）

> **本轮无预算裁决**。以下仅为将来形成实验后的口径说明。

| 项 | 说明 |
|---|---|
| 预期费用 vs 最坏预留 | **必须分开列**。预期费用按实测 p90（18.41 CH/腿）；最坏预留按 profile（`orca_production_v1` 96 CH/腿、`orca_production_12h_v1` 48 CH/腿、`orca_production_4h_v1` 16 CH/腿） |
| 不得推导 | 不得按旧 24h profile 直接说"必须花 192/384 CH" |
| 授权额度 | 须用户**单独批准**（独立于 600 恢复包与 800 四态框架） |

## 5. 停止条件（将来实验适用）

- 任一新起点生产腿过六项验收 → `resolved` → `accepted`
- 全起点均失败 → `unresolved` → 状态保持 `limited`
- 成本达停止预算或方法故障 → `limited`
- 物种漂移或不可恢复身份 → `limited`

## 6. 标识链与输入哈希

- **命名族**：`hpc_dmc_recovery_v2_20261028`（序号高于历史）
- 新包路径：`work/hpc_dmc_recovery_v2_20261028/tasks/<name>/<slot>__<seed>/`
- 识别链：`tasks.txt line i` → `array element i` → `sacct JobID "<array>_<i>"` → 该行 `JobIDRaw`
- 候选门前置：`candidate_gate_contract=validate_candidate_start_v2`

## 7. 双重口径预防

- 成本只记 `AllocCPUS × ElapsedRaw`
- 失败尝试保留实测成本，不删除、不补零
- 系综标签只认 `accepted`，`limited` 不计入

## 8. 版本化与可逆性

- 本草案 v0-draft-rev3，用户批准后升级为 v1-prereg
- 若 v1 失败，v2 必须改变机制，不允许沿用 v1 配置

## 9. 提交与授权条件（将来适用）

- **必须**：机制论证完成并通过审议
- **必须**：用户对 v1-prereg 文本的显式批准（含机制选择与腿数）
- **必须**：新授权额度确认
- **禁止**：自动启动、自动追加、绕过 `acceptance_decision`

## 10. 下游影响

- 两态通过 + EC 通过 ⇒ 系综 48/48，`plan_overall_complete` 可为 `satisfied`
- `strict_readiness_evidence`：池前置满足，但**还要求按正式协议重跑 A/B 盲回放并通过停止预算判据**
- WP5 目标池须同步更新

## 11. 不变的红线

- 阈值不放宽
- 方法不替换（最终 DFT 腿仍走冻结协议）
- 分子集不扩展（core set 18 / broad pool 40）
- 不将 `limited` 视为科学通过
- 不因预算压力而修改 `single_basin_verified` 判定标准
- 不无限重复审计或自动追加计算
- 不得只对 DMC 两态换冻结设定取有利结果
- **旧文件换名不算新机制**

---

## 本轮交付清单

| # | 事项 | 状态 |
|---|---|---|
| 1 | 机制论证（A/B/C 逐项回答 §2.1 四问） | ⏳ **待完成（本轮核心工作）** |
| 2 | 新机制候选生成 | ⏳ 论证后决定 |
| 3 | 预算裁决 | ⏳ 论证后另议 |
| 4 | 提交 | ❌ **本轮不提交** |
