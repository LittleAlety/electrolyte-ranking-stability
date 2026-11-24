# DMC 下一轮预注册草案（设计-only，不提交、不预算、不启动）——修订版 v2

> **性质**：设计草稿，供用户审议。不触发提交、不占用预算、不改动任何现有标签或判定。  
> **版本**：v0-draft-rev2（2026-10-28）  
> **对应缺口**：`ensemble_not_48_accepted` → `DMC|M_plus`、`DMC|LiM_2plus` limited  
> **修订依据**：独立审计 `REPORT_independent_t7.md` 16 条缺陷 + 用户具体修正指示

## 1. 目标态与现状（修正失败史口径）

### 1.1 三层失败证据

| 层 | 证据 | 结论 |
|---|---|---|
| **生产层** | 8 条失败腿：`verytight_convergence`×3、`max_cycles_exhausted`×2、`strict_reopt_required`×3 | 浅赝平坦谷 |
| **重优化** | reopt1–4 + reopt_v2，att=1/2/5/12 全部同型失败 | 从平台重启仍得平台 |
| **GFN2 筛选** | P4 筛选（job 3774215）所有探针弛豫回 `C01#m1`（RMSD 0.0013 Å） | **筛选轮，非 production 尝试** |

### 1.2 逐态机制适用性

| 态 | 特征 | 可用机制 |
|---|---|---|
| `DMC\|M_plus` | 无 Li（charge=1） | B（GFN2 VeryTight 预优化）或 C（直接 DFT 多起点） |
| `DMC\|LiM_2plus` | 有 Li（charge=2） | A（显式 Li 配位）/ B / C 均可 |

**注意**：A 仅适用于 `LiM_2plus`；B/C 两态均可。旧 P4 起点换名不算新机制。

## 2. 预算与资源（修正 profile/墙钟/预算算式）

| 项 | 值 |
|---|---|
| 本轮可用预算（授权硬上限） | **新授权额度**（另立版本）；**不是** rescue 上限 |
| 与既有框架关系 | 独立于 600 恢复包与 800 四态框架；须用户单独批准 |
| 资源 profile | `orca_production_v1`（4 核/腿，**wall_hours=24**，实测 96 CH/腿） |
| 每腿墙钟 | 24 h（profile 默认） |
| 并发上限 | **与 EC 串行**（running+pending ≤2 才投下一批） |
| 逐腿费用 | 4 核 × 24 h = **96 CH/腿** |
| 2 腿最坏预留 | 2 × 96 = **192 CH**（非 37 CH） |
| 4 腿最坏预留 | 4 × 96 = **384 CH**（非 74 CH） |
| 停止预算 | 按实际腿数：2 腿 ≈192 CH、4 腿 ≈384 CH；**停止预算 < 授权上限** |

**预算约束说明**：
- 原草案 `18.41×2×1.5≈55.23` 错误（p90 18.41 不是实测口径，且未乘 24h profile）
- 实测口径：4 核 × 24 h = 96 CH/腿
- 2 腿 ≈192 CH、4 腿 ≈384 CH

## 3. 停止条件

- 任一新起点生产腿过六项验收 → `resolved` → `accepted`
- 全起点均失败 → `unresolved` → 状态保持 `limited`
- 成本达停止预算或方法故障 → `limited`
- 物种漂移或不可恢复身份 → `limited`

## 4. 标识链与输入哈希

### 4.1 现有可用起点（P4 筛选候选，**尚未生成新几何**）

| 态 | 候选唯一名 | 父几何 | 父几何 SHA256 | 变形参数 | 身份 |
|---|---|---|---|---|---|
| `DMC\|M_plus` | `dmc_v2_M_plus_tors_0_1_2_3` | `work/hpc_frontier_localization_v1/tasks/DMC__M_plus__primary/geom.xyz` | `5b9e93e0…` | torsion 0.2743 Å | $chrg=1,$spin=1 |
| `DMC\|M_plus` | `dmc_v2_M_plus_tors_1_2_4_5` | 同上 | 同上 | torsion 0.2432 Å | 同上 |
| `DMC\|LiM_2plus` | `dmc_v2_LiM_2plus_tors_0_1_2_3` | `work/hpc_frontier_localization_v1/tasks/DMC__LiM_2plus__primary/geom.xyz` | `f619c132…` | torsion 0.4874 Å | $chrg=2,$spin=1 |
| `DMC\|LiM_2plus` | `dmc_v2_LiM_2plus_toward_3` | 同上 | 同上 | Li 配位 offset 0.45 Å | 同上 |

- **候选几何已就绪**：以上 4 个 `geom.xyz` + `candidate.json` 存在于 `work/hpc_four_state_p4_xtb_screening_v1/tasks/`
- **但非新机制产物**：B/C 需新几何；A 需新几何 + xTB 预优化
- **候选门前置**：`candidate_gate_contract=validate_candidate_start_v2`

### 4.2 产出登记

- **命名族**：`hpc_dmc_recovery_v2_20261028`（序号高于历史）
- 新包路径：`work/hpc_dmc_recovery_v2_20261028/tasks/<name>/<slot>__<seed>/`
- 识别链：`tasks.txt line i` → `array element i` → `sacct JobID "<array>_<i>"` → 该行 `JobIDRaw`

## 5. 双重口径预防

- 成本只记 `AllocCPUS × ElapsedRaw`
- 失败尝试保留实测成本，不删除、不补零
- 系综标签只认 `accepted`，`limited` 不计入

## 6. 版本化与可逆性

- 本草案 v0-draft-rev2，用户批准后升级为 v1-prereg
- 若 v1 失败，v2 必须改变机制（A/B/C 切换或新机制），不允许沿用 v1 配置

## 7. 提交与授权条件

- **必须**：用户对 v1-prereg 文本的显式批准（含 §2 的机制选择与腿数）
- **必须**：`candidate_gate_contract` 通过
- **必须**：新授权额度确认（独立于 600/800 框架）
- **禁止**：自动启动、自动追加、绕过 `acceptance_decision`

## 8. 下游影响（修正重跑回放要求）

- 两态通过 + EC 通过 ⇒ 系综 48/48，`plan_overall_complete` 可为 `satisfied`
- `strict_readiness_evidence`：池前置满足（A=12, B=12），但**还要求按正式协议重跑 A/B 盲回放并通过停止预算判据**
- WP5 目标池须同步更新

## 9. 不变的红线

- 阈值不放宽
- 方法不替换（wB97X-D4/def2-TZVPD + SMD 不变；A/B 的 xTB 预优化属计划预案，最终 DFT 腿仍走冻结协议）
- 分子集不扩展（core set 18 / broad pool 40）
- 不将 `limited` 视为科学通过
- 不因预算压力而修改 `single_basin_verified` 判定标准
- 不无限重复审计或自动追加计算
- 不得只对 DMC 两态换冻结设定取有利结果（须全 cohort 重算可比性）

---

## 待完成（实体化清单）

| # | 事项 | 状态 |
|---|---|---|
| 1 | 选定具体机制（A/B/C）及每态腿数 | **待用户裁决** |
| 2 | 生成新候选几何（非旧 P4 换名） | **未开始** |
| 3 | 用受保护提交器加载器验证实际资源 | **未开始** |
| 4 | 做包含真实 manifest 的导入/覆盖测试 | **未开始** |
| 5 | 包保持 HOLD，交付逐项通过结果 | **未开始** |

**建议**：DMC 暂时无需强选 A/B/C；先完成候选生成与预检，再依据证据选机制。
