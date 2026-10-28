# L09 阶段报告与图/交付映射（2026-10-29，45/48 阶段交付）

本文件是**阶段交付**报告（不是结题、不是严格目标完成）。所有数字可在同目录 L00–L08 证据文件与
`outputs/physics_completion/**` 产物中逐条复核；生成器 `--check` 已全绿（见 L06）。

## 1. 状态

| 维度 | 状态 |
|---|---|
| 系综 | **45 accepted / 3 limited / 0 provisional**（分母 48 不变） |
| 严格就绪度 | **5/6**；唯一未过 `wp5_full_target_pool_evaluated` |
| 未 accepted 三态 | `EC|LiM_2plus`（reopt TolE 3.18×，冻结边界内保留 limited）、`DMC|M_plus`、`DMC|LiM_2plus`（用户裁决本轮停止） |
| 已恢复的两态 | `DOL|LiM_2plus`（生产腿 + 两轮严格重优化 QC 通过）、`AN|M_plus`（`single_basin_verified`，零新增算力） |
| 计算授权 | EC **32 CH 仍为提议**；DMC 本轮停止；本轮零提交、零 core-hour |
| 工程 | 生成器 `--check` 全绿；L03 EC HOLD 包离线门 27/27 |

## 2. 六件交付映射（`deliverables/part2/`，镜像由生成器重建）

| 交付 | 路径 | 本轮更新 |
|---|---|---|
| 结题论文与提交 | `01_结题论文与提交/` | 未改（历史材料保留） |
| 技术报告 | `02_技术报告/` | 本轮阶段报告以 `docs/handoffs/long_run_20261029/` 为主，不覆盖历史 |
| 评审阶段数据成果 | `03_评审阶段数据成果/` | 由 `build_physics_completion_deliverables.py` 镜像 |
| 物理补全批次数据成果 | `04_物理补全批次数据成果/` | 同上（含 45/48 后的派生产物） |
| 配置与口径 | `05_配置与口径/` | 同上 |
| 基础与参照数据 | `06_基础与参照数据/` | 同上 |
| 代码与测试 | `07_代码与测试/` | 含本轮新增 `ec_recovery_contract.py`、`build_ec_recovery_package.py`、`tests/test_ec_recovery_contract.py` |
| 图表 | `08_图表/` | 六图 F59–F64 |
| 校验与清单 | `09_校验与清单/` | 镜像总清单（SHA256SUMS） |

合规口径：`plan_landing_paths` = **16/16 present**；`plan_stage_reports_present` = **7/7**；`plan_main_figures_six` = **6/6**。

## 3. 六张主图（`outputs/figures/` 与 `docs/assets/figures/`）

| 图 | 文件 | 说明 |
|---|---|---|
| F59 | `F59_physics_completion_definition.png` | 定义/集合与分母（12 分子 × 4 态 = 48，永不缩小） |
| F60 | `F60_physics_completion_method_audit.png` | 方法审计矩阵（含 AnFreq vs NumFreq 敏感性） |
| F61 | `F61_physics_completion_ladder.png` | 翻转阶梯 12 格（2 对 × 6 级） |
| F62 | `F62_physics_completion_pair_identity.png` | pair 证据与身份（66 对，区间口径） |
| F63 | `F63_physics_completion_mechanism_cases.png` | 两个机制案例（几何/键变化） |
| F64 | `F64_physics_completion_budget_curve.png` | 预算/停止曲线（WP5 子池与 not_reached） |

## 4. 结论—证据—限制矩阵

| # | 结论 | 证据 | 限制（不得越界） |
|---|---|---|---|
| 1 | 45/48 accepted，3 limited | `production_ensemble_labels.csv`（45/3/0） | 不得写成 48/48；不得把 limited 计为通过 |
| 2 | DOL/AN 两态恢复有生产级依据 | DOL 生产腿+两轮 reopt；AN `single_basin_verified` | 不称「新盆地」；AN 依据是复现+搜索范围，不是新极小 |
| 3 | WP3 Top-3 = AN>EC>PC（n=11） | `closure/wp3_rung_rebuild_report.md` §3、pair 证据 66 对 | limited 真值可改写 Top-3 ⇒ **不认证全池排名** |
| 4 | WP3 pair 证据：2 ROBUST_INVERSION / 55 STABLE / 9 UNRESOLVED | `plan_compliance` `wp3_pair_evidence` | 仍为 partial（66 对中含未决） |
| 5 | WP5 子池停止 19/32，13 not_reached | `AB_axis_endpoint.csv`、`success_budget.csv` | 子池≠全池；not_reached 是诚实结果，不是失败 |
| 6 | WP5 逐轮费用不可复算 | `round_diagnostics.csv` 两列 296/296 MISSING | 只能按契约/账本口径报；成本账 10 行 3 MISSING |
| 7 | DMC 失败机制有过程证据，推荐 B | `L04_DMC_TRACE/`（9/15 close-enough、探针塌缩、两类失败） | 仅为呈报；**不构成授权**，DMC 仍停止 |
| 8 | 采样/锚点/后继门 | 采样验收 9/9 但 escalation 24/24 未执行；WP4 tier_1=0；WP6/扩池 not_triggered | 不称采样收敛；触发≠完成；0 CH |

## 5. 明确不主张

1. 不主张「48/48」或「严格目标完成」；
2. 不主张排序收敛 / 全池排名（limited 可改写 Top-3）；
3. 不主张「800 CH 框架内路径已穷尽」；
4. 不主张「DMC 永久单盆地」——只说「已登记动作未找到新盆地 + 过程证据支持机制 B」；
5. 不主张采样收敛、WP6/扩池已就绪；
6. 不把「WC 工程链绿」与「科学总闸门通过」混为一谈。

## 6. 复现入口

```text
pytest tests/test_ec_recovery_contract.py tests/test_submit_hpc_batch.py tests/test_evidence_gate_and_cost.py -q
python scripts/wp_production/build_ec_recovery_package.py --check
python work/_validate_ec_package_loader.py
python work/_l00_l01_baseline.py
python work/_dmc_trace.py
```
