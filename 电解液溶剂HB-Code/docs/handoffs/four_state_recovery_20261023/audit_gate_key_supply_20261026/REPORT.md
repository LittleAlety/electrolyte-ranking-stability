# t7 报告：普查「闸门读而不写的键」（有入口无供给类缺陷）——Lead 收回自做

- 承担：原派 `submitter-bypass-audit`（15:08 认领），四轮未落盘 → 按「零产物不收口、Lead 收回自做」纪律，Lead 于 Round 66 代为完成。
- 性质：只读普查（零写产线、零网络、零桥触达）。判据＝精确键名 grep（排除 `*.pyc`）+ **实跑 `derive_checks()` 取真实键集** + 源码行号，未用子串启发式。

## 1. 闸门侧读取的键全集（`scripts/wp_production/strict_readiness.py`）

| 读取点 | 键 | 写入者（grep 全仓 + 实跑） | 三态结论 |
|---|---|---|---|
| `:49` `for k in REQUIRED_CHECKS: checks.get(k) is not True` | 6 个必需检查键（`coverage_reviews_valid` 等，见 §2 实跑清单前 6 个） | `strict_readiness_wiring.CHECKS` 字典（`:447-454`）经 `derive_checks()` 产出 | **有生产者** |
| `:55` `checks.get(gate + "_trigger_state")`（gate∈{wp6, pool_extension}） | `wp6_trigger_state` / `pool_extension_trigger_state` | `derive_checks():541-547` | **有生产者** |
| `:57` `checks.get(gate + "_triggered")`（向后兼容分支） | `wp6_triggered` / `pool_extension_triggered` | `derive_checks():548-549` | **有生产者** |
| **`:61` `checks.get(gate + "_complete") is not True`** | **`wp6_complete` / `pool_extension_complete`** | **全仓（scripts/tests，排除 pyc）唯一命中＝`tests/test_strict_readiness.py:97` 的合成字典 `dict(ALL_TRUE, wp6_triggered=True, wp6_complete=True)`**；`derive_checks()` 实跑 10 键中**不含**它们 | **无生产者**（已知项，本报告确认为全仓唯一） |

## 2. 生产侧实跑键集（`derive_checks()`，exit 0）

`['coverage_reviews_valid', 'execution_cost_provenance_complete', 'identity_all_members_complete', 'pool_extension_trigger_state', 'pool_extension_triggered', 'sampling_audit_complete', 'wp3_evidence_complete', 'wp5_full_target_pool_evaluated', 'wp6_trigger_state', 'wp6_triggered']` —— 共 **10 键**，其中 8 键被 `strict_readiness.py` 直接消费、2 个 `_triggered` 是兼容布尔。**无任何 `*_complete`。**

## 3. 其他消费者普查（`checks.get(`/`checks[` 全 scripts 扫描）

- `scripts/build_github_readme.py:718-728` `_strict_gate_snapshot()`：动态 import wiring+strict 二者后调同一 `strict_readiness()` —— 读取面与 §1 完全相同，**不引入新键**。
- `scripts/wp_production/build_plan_compliance.py:27-45`：只用 `REQUIRED_CHECKS`/`derive_checks`/`derive_check_details`（wiring 自产），**不读 `*_complete`**。
- 其余 `scripts/wp_production/*.py` 对 `checks.get(`/`checks[` 的命中：除上述两文件与 strict_readiness_wiring 自身外为空。

## 4. 后果方向（无生产者键）

`strict_readiness.py:61`：`state=="triggered" and checks.get(gate+"_complete") is not True` → `reasons.append(gate+"_incomplete")`。由于生产字典永不含该键（`.get` 恒 None → `is not True` 恒真），**一旦 WP6/扩池触发，闸门永久报 `wp6_incomplete`/`pool_extension_complete_incomplete`，无论实际是否完成**。当前不显形仅因两触发器均为 `not_triggered`（labels 44/48）。修复判据方向（P9 §四之八 已载，此处不重复）：WP6＝`explicit_ligand_plan.csv` 的 `executed_jobs` 覆盖已触发范围且逐条 QC 证据；扩池＝新 cohort 成员进入目标池并被评估；须配负向测试 + no-flip 证明，**禁止常量 True**。

## 5. 结论

- **全仓唯一「读而不写」键对**：`wp6_complete` / `pool_extension_complete`（P9 §四之八 已立案，属用户裁决项 ④）。
- 其余被读键全部有生产者；README/compliance 两个下游消费者不引入新键。
- **未覆盖**：`derive_check_details()` 的 per-check detail 结构未被逐键展开（本轮只验证键存在性）；`tests/` 内其他合成字典未逐一溯源（仅确认它们不是生产供给）。
- 命令与退出码：grep 均 exit 0/1（无匹配）；实跑 `derive_checks()` exit 0；本报告全程序零写 `outputs/**`。
