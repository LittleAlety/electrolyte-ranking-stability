# 双闸门就绪度小结（2026-10-25）——**供你裁决授权与 P4 三选一**

> 全部数字均为**实测**，可在文末「证据出处」逐条复核；本文件**不新增任何推断**。

## 0. 一页结论

- 两道严格闸门**同被同四个 limited 态阻塞**：把那四个态按现有规则做成 `accepted` 后，闸门 2 的**池前置**（A/B 各 12）也随之满足。
  但**闸门 2 不会仅因此打开**——它还要求按正式协议**重跑** A/B 回放并满足其停止预算判据（见 §2）。
- **本地侧已全绿**（7/7 只读门）；真正缺的是 ①**你的计算授权** ②三道**口径裁决**。
- 授权后的算力在既定 800 内：筛选 **32** core-hours → 首产 **≤512** → 有因补救 **≤256**；**当前实耗 0**。

## 1. 闸门 1：`ensemble_not_48_accepted`（现 **44 accepted / 4 limited**）

| 态 | coverage route | verdict | registered_starts | label `limitation_reason` | 该态在生产系综里的角色 |
|---|---|---|---|---|---|
| `DMC\|M_plus`（C01） | `unresolved_qc` | `unresolved` | `tors_8_0_1_2` | `rescue_budget_exhausted` | 闸门 2 的 A 池缺它 |
| `DMC\|LiM_2plus`（C01） | `unresolved_qc` | `unresolved` | `tors_7_0_1_2` | `rescue_budget_exhausted` | 闸门 2 的 B 池缺它 |
| `DOL\|LiM_2plus`（C09） | `search_exhausted` | `search_exhausted` | **（空）** | `rescue_budget_exhausted` | 闸门 2 的 B 池缺它 |
| `EC\|LiM_2plus`（C04） | `search_exhausted` | `search_exhausted` | **（空）** | `rescue_budget_exhausted` | 闸门 2 的 B 池缺它 |

**怎么补**：按冻结规则走 P4 筛选轮（8 任务 / 2 核 × 2 h / **32 core-hours**）→ 逐元素按 **6 kcal/mol 窗**分流 →
每态 **≤2 个首轮独立生产起点 + ≤1 次有因补救**（首产 ≤512、补救 ≤256）。
**红线不变**：不改 48 分母、不降 `VeryTightOpt` 五阈值、不把 GFN2 当生产自由能、不手写 `accepted`、不清零历史成本。

## 2. 闸门 2：`wp5_full_target_pool_evaluated`（现 **A 11/12、B 9/12**）

| 任务 | 态对 | 两腿都 `accepted` | 缺谁 | 缺的原因 |
|---|---|---|---|---|
| **A** | (`M_plus`, `M`) | **11 / 12** | **DMC** | 其 `M_plus` = `limited`（`M` 腿 accepted） |
| **B** | (`LiM_2plus`, `LiM_plus`) | **9 / 12** | **DMC、DOL、EC** | 三者 `LiM_2plus` = `limited`（`LiM_plus` 腿全 accepted） |

**对账**：由 labels 纯投影算出的 `{A:11, B:9}` 与端点表 `AB_axis_endpoint.csv` 记录的 `n_pool`（A=11／B=9，各 16 组）**完全一致**。
⇒ **这道闸门不需要额外算力**；但**四态转 `accepted` 后池就变了，旧回放不作数，必须按正式协议重跑**
（四策略 × 四模型 × 20 repeats；Acquirer 只持可见标签、Evaluator 独占真值；停止预算仍按「同批 ≥16/20 repeats 在两个相邻非耗尽预算点同时达标」）。

## 3. 两闸门的耦合
同一根因（那四个态）⇒ **一次授权可同时推进两道闸门**；不存在「闸门 2 需要另买算力」的情况。
但两者**不是同一步骤生效**：闸门 1 由四态的接受状态直接决定；闸门 2 在池补齐后**还须重跑并过停止预算判据**。

## 4. 本地就绪度（实测）

| 项 | 实测 |
|---|---|
| 本地提交前门 | `work/_p4_preflight_local.py` → **7 / 7 通过**（含 293 项包审计、模拟提交 17-17 且 **0 次 bridge 调用**） |
| P4 包状态 | `submission_gate=HOLD`、`submitted=False`、`cap=32`、8 任务 × 5 文件 |
| 超算连通 | `hpc.ps1 doctor` **0 项提醒**；实时队列 **空**；远端**无本包**（无重复提交风险）；`~/project/soft/xtb/{env.sh,bin/xtb}` 均存在 |
| 花费 | 实耗 **0 core-hours**、在途预留 **0**、800 **未动** |

## 5. 四道待裁决门（以及开门后我做什么）

| # | 门 | 开门后我的动作 |
|---|---|---|
| 1 | **计算授权**（唯一硬门） | 按 `P4_SUBMIT_RUNBOOK_20261024.md` §1 固定顺序：`doctor` → 真实 `squeue` → 经桥上传并远端核对根哈希 → **只调用受保护提交器**（带 `attempts_ledger.json`）；提交后立刻登记数组 JobID 与 8 元素→任务映射 |
| 2 | **P4 三选一** | A 原包提交（塌缩则如实记「零」）／B 冻结集合内把短给体态改选 0.15 Å／C 预注册 v2 加最小接触护栏并另立版本族——按你选定的一项准备执行 |
| 3 | **baseline 刷新口径** | 按 `baseline_refresh_review.DRAFT.md` 写入刷新记录并令 `preflight` 由 `STALE` 回 `CONSISTENT` |
| 4 | **`limitation_reason` 口径**（本轮新增） | 若改：让 `aggregator:938-940` 在 `cov.verdict=="search_exhausted"` 时不抢占 `single_basin_pool`，再同步重建下游链；若不改：保留已知的「呈现可能误导」瑕疵 |

## 6. 证据出处（逐条可复核）
- 闸门清单与组合口径：`strict_readiness_wiring.py` + `build_github_readme.py` 的 `_strict_gate_snapshot()`；
- 逐态 route/verdict/registered_starts：`outputs/physics_completion/recovery/coverage_reviews.csv`（14 行）；
- 逐态 `limitation_reason` 与成员计数：`outputs/physics_completion/ensembles/production_ensemble_labels.csv`；
- A/B 池缺额与对账：`work/_wp5_pool_audit.py`（只读）+ `outputs/physics_completion/active_learning/blind_replay/AB_axis_endpoint.csv`；
- 审计与缺口 G1–G5：`ACCEPTANCE_CHAIN_AUDIT_20261024.md`；
- 提交序与离线门：`P4_SUBMIT_RUNBOOK_20261024.md`（§0.0 / §0.1 / §1 / §5.1）。