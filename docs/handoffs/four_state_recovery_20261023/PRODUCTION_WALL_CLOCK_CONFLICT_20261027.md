# 生产段「墙钟口径」契约-代码不一致（2026-10-27，待裁定）

> 本轮在为 DOL/EC 生产批备料时，核对**预算账**发现一处**契约与实现不一致**。
> **本文只诊断与呈报，不改 profile、不改契约**——因为两者都牵动既有账本与验收口径。**纯只读。**

## 1. 不一致的事实（实测）

| 来源 | 生产段墙钟 | 说明 |
|---|---|---|
| **契约** `recovery_contract.json` → `budget.production` | **`max_wall_hours: 4`** | 另有 `max_cores: 16`、`core_hours_cap: 512`、`max_attempts: 8`、`max_per_state: 2` |
| **实现** `submit_hpc_batch.RESOURCE_PROFILES["orca_production_v1"]` | **`wall_hours: 24`** | ⇒ 提交时注入 **`--time=24:00:00`** |

**⇒ 同一件事，两个数字：4 h vs 24 h。**

## 2. 对预留的影响（这是为什么值得管）

提交器的预留口径是 **`核 × 墙钟 × 元素数`**：

| 口径 | 2 腿的在飞预留 |
|---|---|
| **契约（4 h）** | `4 × 4 × 2` = **32 CH** |
| **实现（24 h）** | `4 × 24 × 2` = **192 CH** |
| 差异 | **6 倍** |

对 512 生产额度的影响：**不会撞 cap**（192 < 512），
但**可同时在飞的腿数**从「理论 512/32 = 16 腿」降到「**512/192 ≈ 2.7 腿**」——**并行能力差 6 倍**。

## 3. 实测墙钟站在哪一边（数据说话）

生产腿实测墙钟（`production_cost_ledger.csv` 60 腿，`core_hours ÷ 4 核`）：

| 统计量 | 值 |
|---|---|
| min | 0.10 h |
| **中位** | **2.03 h** |
| **p90** | **4.60 h** |
| **max** | **7.98 h** |

**⇒ 实测 p90 = 4.60 h，略超契约的 4 h；max = 7.98 h，明显超 4 h。**
即：**契约的 4 h 对 p90 偏紧、对长尾不足；profile 的 24 h 对 max 仍有 3 倍余量**。
**两边都不是"错"**：4 h 是**成本纪律**口径，24 h 是**Slurm 不被杀**口径。

## 4. 我的判断（**不自行执行**）

| 选项 | 内容 | 代价 |
|---|---|---|
| **A. 保持现状**（profile 24 h，按 96 CH/腿预留） | 不改任何东西 | 并行腿数被压到 ≈2.7 腿；但**安全**（不会被 Slurm 杀） |
| **B. profile 改 4 h**（对齐契约） | 预留降到 32 CH/腿 | **风险**：max 实测 7.98 h ⇒ **长尾腿会被杀**（浪费算力、且失败计入成本） |
| **C. 新增专用 profile**（如 `orca_production_8h`） | 覆盖 p90+余量、预留 32 CH/腿 | 需**无翻转证明**（证明不影响既有已提交腿的账本与验收） |
| **D. 改契约**（`max_wall_hours` 4 → 8） | 让契约与实测一致 | 改的是**授权文档**，须你批准 |

**我倾向**：**本轮 2 腿用 A（保持现状，安全优先）**——因为 2 腿的预留 192 CH 完全在 512 内，
**没有必要为省预留去冒「长尾被杀」的风险**；**C/D 留到将来需要多腿并行时再议**。

> **⚠ 与 H2 的关系**：「单点误用生产腿基准」是**基准错配**；这次的「4 h vs 24 h」是**同一参数在两个权威来源里取值不同**
> ——同族但更根本：**当契约与实现给出不同数字时，应当显式裁定哪一个算数**，而不是各自沿用。

## 5. 明确不做（守线）

- ⛔ **不**擅自改 `orca_production_v1.wall_hours`（全仓 60 条历史腿与 800 总 cap 依赖它）；
- ⛔ **不**擅自改 `recovery_contract.json`（那是**授权文档**，只有你能改）；
- ⛔ **不**为省预留而把墙钟压到实测 p90 以下（会让长尾腿被 Slurm 杀）。

## 6. 证据出处

- 契约：`docs/handoffs/four_state_recovery_20261023/recovery_contract.json` → `budget.production`
- 实现：`scripts/wp_production/submit_hpc_batch.py` → `RESOURCE_PROFILES["orca_production_v1"]`
  （并见 `:424-426` 用 profile 值改写脚本墙钟）
- 实测：`outputs/physics_completion/cost/production_cost_ledger.csv`（60 腿）
- 相关：`DOL_EC_PRODUCTION_COVERAGE_PLAN_20261027.md §3.1`

## 7. 处置（2026-10-27 批次落地后追加，不改动上文历史）

本文记录的「4 h 契约 vs 24 h profile」冲突最终按**上文的选项 C（新增专用 profile）**
关闭，但采用用户 2026-10-27 裁定的 **`orca_production_12h_v1`**（4 核 × 12 h，本批
2 腿 = **96 CH**，`paid_from=production`；12 h 是覆盖最长实测腿 ~8 h 的工程余量，
**不是**收敛保证，费用按终态 sacct 结算、绝不用 36.8 CH 的 p90 估算结）：

- 可执行包现为 `work/hpc_dol_ec_recovery_v1_20261027/`（`resource_profile=orca_production_12h_v1`），
  由 `scripts/wp_production/build_dol_ec_recovery_package.py` 生成，并经提交器自身加载器
  （`submit_hpc_batch._load_package` + `submission_resources`）验证（见
  `tests/test_dol_ec_recovery_package.py`）。
- 旧草案 `work/dol_ec_recovery_v1/`（`orca_production_v1` / 24 h / 192 CH）**保留作历史，不再提交**；
  它仍指向「无登记通道」的 `blocked_reason` 也随之作废（通道已落地，见下）。
- 其他批次的**通用生产墙钟仍为 4 h**（`CAPS["production"][3]`），只有本批两态享 12 h 例外；
  `preflight.py` 已适配 schema v2（`validate_version` 接受 v1/v2 + 新增
  `validate_production_batches`：第三态 / 非目标态 / 换 profile / 超 96 CH 均被拒，
  见 `tests/test_preflight_v2_production_batch.py`）。