# 实验线状态快照（2026-10-31 06:32Z / 北京时间 14:32）— 轮次 26

> 本文件是**当前真实状态的单一入口**，取代此前分散在多份报告里的状态描述。
> 全部数字为实测，可逐条复算。

## 1. 一句话状态

**未提交任何作业。** A-1 已落地（包移位 + manifest `members` + 清单重生成）；A-2 停在报备点等用户裁决；
Agent A 的复检任务（t10）因其中断尚未执行，已重投；正式记录仍为**历史协议 45 accepted / 3 limited（分母 48）**。

## 2. 逐项实测（截至 06:32Z）

| 项 | 值 | 证据 |
|---|---|---|
| 提交痕迹 | **无** | `submission_journal.json` 不存在、`.batch_1.submission.lock` 不存在 |
| 包 gate | `submission_gate=HOLD`、`submitted=false` | `work/hpc_dmc_lim2plus_vtscf16_v1/manifest.json` |
| 包冻结完整性 | **14/14 OK** | `sha256sum -c PACKAGE_SHA256SUMS`（清单 sha `562326384aca4990ef76a212ca86acec`） |
| 正式标签 | **45 accepted / 3 limited**，分母 48 | `production_ensemble_labels.csv` |
| 候选表 | **未改**（123 行，无 `p5li_vtscf16`） | `production_ensemble_candidates.csv` |
| `scripts/` 改动 | **0**（本轮及 A 发 HOLD 之后） | — |
| 队列 / 在飞 | 空 / 0 | Agent B 三次实测 + Lead 复核 |
| 费用 | 池余最保守 **389.9416667**；预留 64 后 **325.9416667** | t2 审计 + t7 结清 |

## 3. 三道门

| 门 | 状态 | 产物 |
|---|---|---|
| **A 科学门（t1）** | **`SCIENTIFIC_HOLD`**，已审议批准 | `work/exp_line_20261031/SCIENCE_ACCEPTABILITY_AUDIT_20261031.md` |
| **A 复检（t10）** | **pending，A 的 turn 3 被 interrupted，已重投** | 目标文件 `SCIENCE_RECHECK_AFTER_A1_20261031.md`（未生成） |
| **B 费用门（t2）** | **通过**，已审议批准 | `COST_AND_DUPLICATE_AUDIT_20261031.md` |
| **C 提交门（t8）** | **未启动**（依赖 Lead 五项改动，被 A 的 HOLD 阻断） | — |

## 4. 已确证的两条硬结论（决定后续走向）

**① 不借被取消探针 ⇒ 无法 `resolved`**（真实 `coverage_route()` 实测 4/4）

| 输入 | route | verdict |
|---|---|---|
| `computed` + `starts=[]` | `known_basin_reproduction` | **unresolved** |
| `computed` + `starts=["tors_7_0_1_2"]` | `single_basin_verified` | resolved |
| `computed` + `novelty=unresolved` | `dedup_evidence_required` | unresolved |
| `computed` + `production_evidence=False` | `known_basin_reproduction` | unresolved |

**② `start_1_basin` 是搜索的结论，不是可填配置**：`build_strict_recovery_manifest.py:355-364` 只从 `_li_recovery_starts()`（需 `kept=true && new_vs_round1=true`）与 `_search_minima()`（需 `status=candidate_start`）取；三处注释写 "**starts are never invented**"。

⇒ **补搜索范围证据必须真跑搜索（新计算）**，或接受 `tors_7` 背书（用户已否决）。

## 5. 本轮 64 CH 的真实价值（实测基线）

sacct 10 月全量 **622** 个有实耗主作业：1 核 5、2 核 4、**4 核 613（总 2102.0189 CH）**、**16 核 0**。

| 目标 | 64 CH 够不够 |
|---|---|
| 推进 45→46 | **不够**（缺搜索范围证据） |
| 严格测核数收益 | **不够**（需 4 核 + 16 核各一次同输入 A/B；`3894976_0` 是不同体系） |
| 严格协议下"对已登记单一极小的独立复现"证据 | **够**（但不会让覆盖审 resolved） |
| **16 核可行性首个技术验证**（历史 0 条 16 核） | **够** |

## 6. 待用户裁决（两项，互不依赖）

**(a) A-2 的登记方式**：P1（`recovery_v1_start`，接受 `limited→provisional`）/ **P2**（新 `recovery_v1` 前缀角色，**标签不动**，机制已 8/8 证实）/ P3（不登记）。
—— 但注意 §4①：**若 A 复检确认"不借探针无法 resolved"，P1/P2 都失去意义，P3 成为唯一合理选项。**

**(b) 本轮 64 CH 的目标**：跑通 16 核 / 两阶段测收益 / 直接收口。

## 7. 已就绪、批准即可执行

- **t4 补丁**：`docs/handoffs/exp_line_20261031/T4_PATCH_READY_20261031.md`（16 核前置已全部实测通过，只差 `RESOURCE_PROFILES` 一条；含 4 条入口级负测与"必须重跑 `_profile_audit.py` + 重生成清单"两条防坑提示）
- **t3 预验证**：rev5 生产入口在真实证据上 **PASS**（`sealed_registry`，B1/B2 提前闭合 6/6）＋ 测试件 **9/9 绿**
- **账本**：t7 已结清（`1.5644444` / `1.4077778`），回归复验通过