# P5 · 批准规则准入门盘点（Plan action item 5 · 第一轮：现状盘点与验证，只读）

> 会话：公共处理会话（唯一共享生产写入者）｜本轮**只读**：未改任何门控代码、未改阈值、未生成 `comparability_criterion_v1.json`、未填 `resolved`。
> 仓库 HEAD `80933e54f8a605d9dd6d033c0f2861e33b591c13`｜2026-11-03。

## 1. 五个维度的机读状态与门（现状盘点）

| 维度 | 机读状态持有者 | 门函数/判据 | fail-closed 证据 |
|---|---|---|---|
| 成员资格 | strict 资格审计（`rebuild_strict_isolated.py`：**资格先于去重**；`audit_strict_recovery.py`；`run_eight_terminal_admission.py` 逐员 `strict_eligible`+`strict_reasons`） | 合格成员才进 `dedup_members`；`kept_pool_evidence ⊆ strict_kept` 断言 | 终态义务视图实测 26 行（8 合格 / 18 不合格，含 `TMP\M\primary` 等 primary 行，不合格逐条带 reason） |
| 身份 | 接收登记 `gate_identity`（`build_production_ensemble_manifest.py:696` RECEPTION_FIELDS） | 派生自盘上证据，缺证据→PENDING | `tests/test_dmc_reception_registration.py:86/258` 断言 PASS 与 PENDING 两径；八态身份裁定仍 PENDING → 门保持非 PASS |
| 协议可比性 | `gate_comparability` | `_comparability_gate()`：**仅当存在版本化且 `approved=true` 的判据文件才 PASS** | 当前无该文件 → 恒 PENDING（红线一致：本会话不生成该文件、不选 δ）；测试 `:145/:171/:174` |
| 阶段绑定 | `gate_stage_linkage` + receiver 记录（D7 `identity_lines`/D8 schema 轴） | 依 receiver 记录与账本版本轴 | D8 缺陷未修、账本三轴偏斜未迁移、切换未授权 → 非 PASS（P1 §3）；receiver 测试 35 passed |
| coverage | `gate_coverage` | `_coverage_gate()`：读登记审表，`verdict=resolved` 才 PASS，否则 `NOT_RESOLVED`，表缺/不可读→PENDING | 五态 `PENDING_INDEPENDENT_COVERAGE_AND_IDENTITY_REVIEW`（A1/P4）；`test_strict_coverage_single_cluster` 5/5 |
| （正式验收） | `gate_formal_acceptance` | 读历史验收标签 CSV，全 accepted 才 PASS | 45/2/1 不变，非全量 accepted → NO（正确反映历史） |

七门汇总于 `RECEPTION_FIELDS`（`build_production_ensemble_manifest.py:691-697`）+ `unmet_conditions`；登记函数**只在七门全过时发 CANDIDATE 行，且 outright 拒绝 `status=computed`**（`:754-768` 文档串 + 测试 `:10`）。

## 2. staged ≠ computed ≠ accepted（实测）

- **staged**：`rebuild_strict_isolated.py:241` 单独读 DMC staged 表，五条 staged 腿逐条评估（`assess five staged legs individually`），staged 记录与正式登记分离；
- **computed**：登记函数拒发该值（"computed 是管道从真实结果推导的属性，登记表不可断言"）；
- **accepted**：仅由历史验收标签文件承载（45/2/1），`gate_formal_acceptance` 只读它，不与前两者混流。
- 三值分属三个独立文件/字段，无默认值互相填充路径。

## 3. 旁路与循环检查（验证口径）

| 检查 | 结果 |
|---|---|
| pending/failed 经默认值/旧缓存绕过 | token 集合显式声明（`strict_readiness_wiring.py:66-88`），**未知 token 永不被接受为处置**；表缺/不可读一律 PENDING/NO（fail closed，三处门函数 `except→PENDING`） |
| 绕过走"其他入口" | 严格沙箱断言 `kept_pool_evidence ⊆ strict_kept`（`run_eight_terminal_admission.py:54-57`）；资格**先于**去重（`rebuild_strict_isolated.py:5` + `test_strict_eligibility_before_dedup`） |
| primary 与旧追随者都进资格核验 | 终态义务视图 26 行覆盖全部 `is_current_attempt` 成员（含 primary），逐行 `strict_eligible`/`strict_reasons`，实测 8/18 |
| "尚未完成 coverage" 被误写成"不能开展 coverage 评估"的循环 | 全仓 scripts 检索 `cannot evaluate / 不能开展 / coverage blocked` 类措辞 **0 命中**；五态记录为 `route=pending`、`coverage_gate=HELD`（=尚未，非不能），A1/P4 一致 |

## 4. 本轮实测命令与结果

```
$ python -m pytest tests/test_dmc_reception_registration.py -q -p no:cacheprovider
exit 0 | 11 passed                                                      # 七门登记测试
$ python -m pytest tests/test_strict_eligibility_before_dedup.py tests/test_strict_readiness.py \
    tests/test_strict_readiness_strict.py tests/test_candidate_start_gate_order.py \
    tests/test_strict_isolated_entry.py -q -p no:cacheprovider
exit 1 | 53 = 47 passed + 5 FAILED + 1 skipped
```

5 个 FAILED 全部为同一环境缺口，**非门旁路**：

```
scripts\wp_production\build_torsion_probe_package.py:138: ModuleNotFoundError  (from rdkit import Chem)
FAILED test_one_hydrogen_moved_100a_is_refused_as_ring_broken
FAILED test_the_real_60_deg_probe_still_passes_the_reordered_gate
FAILED test_the_repair_path_calls_the_gate
FAILED test_a_bad_rotation_cannot_reach_the_manifest
FAILED test_the_second_packaging_path_also_calls_the_gate
```
与 P1 批的 rdkit 缺口同因（三解释器均无 rdkit，lesson `0mw0lz12`）；失败发生在导入期，未触及门逻辑判定。**这 5 例在本环境未获证明** → 列入未确定。

## 5. 没有关闭什么（本盘点的边界）

1. **rdkit 环境**：gate_order 5 例未证 → 交环境负责人/Lead，不自行改造环境。
2. **协议可比性判据**：缺 `approved` 版本化文件 → 恒 PENDING；生成与 δ 选择不在本会话权限（红线）。
3. **身份/coverage 裁定**：八态仍 PENDING → 交数据分析（P4 handover）。
4. **D7/D8 阶段绑定轴**：切换授权未批 → HOLD（Open question 1）。
5. **机读状态分散**：五维状态分持于 receiver 记录、coverage 审表、资格审计、验收标签四处，**尚无单一汇聚视图**——是否建"准入状态一览"聚合器属后续批次，需先定写入位置（默认只进 evidence/），本轮未做。
6. action items 6-9 未动。

## 6. 复现命令（cwd=仓库根）

```bash
python -m pytest tests/test_dmc_reception_registration.py -q -p no:cacheprovider            # exit 0
python -m pytest tests/test_strict_eligibility_before_dedup.py tests/test_strict_readiness.py tests/test_strict_readiness_strict.py tests/test_candidate_start_gate_order.py tests/test_strict_isolated_entry.py -q -p no:cacheprovider   # exit 1（5 rdkit）
```

## 7. 收尾：五维机读状态汇聚视图（补 §5 缺口 5，2026-11-03）

构建器 `p5_gate_inventory/admission_state_view.py`（`20bda968…`）→ `admission_state_view.json`（`0ced646d…`），exit 0。五态 × 五维单点保存，全部来自活文件实测/已审定证据，零裁定零手填：

| 维度 | 五态实测状态（全部一致） | 依据 |
|---|---|---|
| 成员资格 | `QUALIFIED_REPRESENTATIVE_PRESENT`（代表如 `DEC\|LiM_2plus\|c02`） | binding_package（P4 审定谱系） |
| 身份 | `PENDING_INDEPENDENT_IDENTITY_ADJUDICATION`（missing 逐条原样） | binding + coverage_recheck，权威=数据分析 |
| 协议可比性 | `NOT_APPROVED_CRITERION_ABSENT` | `config/comparability_criterion_v1.json` 不存在（fail-closed；生成/选 δ 超权限） |
| 阶段绑定 | `HISTORICAL_V4_ACTIVE_SWITCH_UNAUTHORIZED` | 三轴活哈希与 P1 记录**全等**（`drift=false`：`205f1ba9…`/`138df33b…`/`c336acb5…`）；账本 v2 vs 模块期望 v3 偏斜在案 |
| coverage | `NOT_TOUCHED` / 复审 `PENDING_INDEPENDENT_COVERAGE_AND_IDENTITY_REVIEW` | binding 原文；旧 claim 原样保留 |

自检（fail-loud）：`no_resolved_anywhere=true`、`coverage_not_touched_all=true`、`review_pending_all=true`、`production_written_false=true`、`states=5`；任一不满足即拒写。
依赖顺序声明（视图内 `dependency_order_per_approved_rules`）：身份+coverage 裁定（数据分析）→ 可比性判据批准（Lead/用户）→ D7/D8 切换+账本迁移授权（Open question 1）→ 正式验收/授权发布（Open question 2）；当前五态全部停在步骤 1-3 PENDING，**任何维度不得经默认值/旧缓存/其他入口前进**。

复现：
```bash
python docs/handoffs/lead_reception_strict_rebuild_20261103/evidence/p5_gate_inventory/admission_state_view.py   # exit 0
```
