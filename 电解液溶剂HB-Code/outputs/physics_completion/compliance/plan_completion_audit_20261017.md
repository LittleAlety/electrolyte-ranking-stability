# 计划任务完成度对照（electrolyte-ranking-implementation-plan v1.3）

> 生成时间：2026-10-17 · **03:00 刷新**（AnFreq 折入 + TMP/LiM_plus 救援 + 收口链全绿之后的口径）
> 依据 `C:\Users\Little Alety\Downloads\electrolyte-ranking-implementation-plan (1).md`（303 行）
> 口径来源：`outputs/physics_completion/compliance/plan_compliance.csv`（39 项）+ 实测账本
> **结论：计划尚未全部完成。** 已完成 23 项（satisfied 20 + exempt 3），12 项 partial，**2 项** blocked_on_production，2 项 not_satisfied。
> ⚠️ 本报告 2026-10-17 首版（43/48 口径）已作废；**权威实时口径＝`plan_compliance_meta.json`**，本文件须随收口链每次刷新。

## 一、总览

| 状态 | 项数 | 含义 |
| --- | --- | --- |
| satisfied | 20 | 已达成 |
| exempt | 3 | 按 v1.1 决断豁免（不计未闭合，也不等于通过） |
| partial | 12 | 部分达成 |
| blocked_on_production | **2** | 被生产未完成阻塞（较首版 5 项已解除 3 项） |
| **not_satisfied** | **2** | **未达成** |

核心闭环闸门 `plan_overall_complete` = **blocked_on_production**（只差系综 + 采样审计 + R4 + 升级后 WP6）。

## 二、三份修订的执行状态

### v1.3 几何收敛紧急修订（5 条）
| 条 | 要求 | 状态 |
| --- | --- | --- |
| 1 | 新任务统一 `VeryTightOpt` + 冻结阈值 + manifest 机器登记 | ✅ 已落地（`prepare_hpc_main_remaining`、`geometry_convergence_policy`、导入器逐项核对） |
| 2 | 虚频先严优化（从最新收敛几何，不退回旧起点） | ✅ 已执行（3700781/3700786/3704628 各救援包均按此生成） |
| 3 | 与 AnFreq 审计组合、不混淆原因 | ✅ **超额完成**：60/60 全 cohort 配对审计（`anfreq_paired_audit.md`），并用 DX 步长探测分离出数值噪声 |
| 4 | 旧结果过渡政策（零虚频保留、有虚频须过 VeryTightOpt） | ✅ 已落地 |
| 5 | 验收证据（记录档位 + 五项阈值/数值） | ✅ `enforce_geometry_convergence` 逐项核对 |

### v1.2 导数计算紧急修订（5 条）
| 条 | 要求 | 状态 |
| --- | --- | --- |
| 1 | 解析一阶梯度硬约束，禁 NumGrad，生成器/导入器/测试 fail-closed | ✅ `orca_derivative_policy.py` + 测试 |
| 2 | 术语分离（NumFreq ≠ NumGrad） | ✅ |
| 3 | AnFreq 配对审计（含干净小体系 + TMP 失败态，记录全部量） | ✅ **已完成 60/60**，报告含虚频数/最低频/ΔG/几何哈希 |
| 4 | 不得择优混算；门槛满足后全 cohort 统一重算 | ✅ **已按此执行**：审计→证据→**协议 v1.3 全局修订**（AnFreq）→**折入账本**（含 canonical 证据换源，归档复算 5078+300 处零失配） |
| 5 | 现有 Opt NumFreq 作业不取消 | ✅ |

### v1.1 执行决断（3 条）
| 条 | 要求 | 状态 |
| --- | --- | --- |
| 1 | WP1 还原态 → `exempt`（零对象清单 + 规则引用） | ✅ `wp1_reduction_state_checks` = exempt |
| 2 | WP4 锚点 → 永久 `validation_limitation` | ✅ `wp4_primary_text_check` / `wp4_new_comparable_entries` = exempt（付费墙证据在案） |
| 3 | WP6 自动升级闸门（Li 配对 ≥9/12 **且** 系综 48/48） | ⏸ 闸门差一项：Li 配对 **12/12 ✅**、系综 **0/48 ❌** → `wp6_explicit_ligand` 保持 `blocked_on_production` |

## 三、WP0–WP6 逐项

| WP | 计划要求 | 状态 | 实测 |
| --- | --- | --- | --- |
| **WP0** | 定义迁移：7 个新量名 + 5 条结论迁移 + 生成器 | ✅ **完成** | 7 量名全在 `physics_completion_v1.yaml`；Q3/Q7/Q10/R15/P1a 全在 `claim_migration.md`；`direction_selection` 测试通过 |
| **WP1** | 独立方法审计：2 泛函 × 2 基组 × 8 分子 | ✅ **完成** | `method_audit/` 14 文件（含 `axis_sensitivity.csv`、`method_settings.csv`）；还原轴按 unbound_anion 豁免 |
| **WP2** | 48 态固定背景配对自由能标签 | ⚠️ **标签层完成、系综层未启** | 主态运行 **48/48**、科学验收 **48/48**、四态完整 **12/12**、Li 腿 **24/24**（配对 12/12）；**系综 0/48**（round1 已在跑，见 §五） |
| **WP3** | 排序 + 独立 uncertainty + 机制（≤3 案例） | ⚠️ **部分** | `pair_evidence/` 10 文件（含 resolved/robust/unresolved 与 tau_b/Top-k/regret）；机制案例页存在 |
| **WP4** | 外部锚点复核 + 可比性审计 | ✅ **完成（含 limitation）** | `anchor_primary_audit.csv` 23KB；新条目按协议检索得 0 条 → 永久 limitation |
| **WP5** | Δ-learning + 主动查询 + 成本曲线 | ⚠️ **部分** | `ml/` 2 文件、`active_learning/` 3 文件、`cost/` 8 文件；**扩样 0 行**（`wp5_pool_extension` not_satisfied，与系综独立） |
| **WP6** | 可选共同背景显式配体 | ⏸ **只差系综** | Li 配对 ✅ 12/12；系综 48/48 ❌ 0/48 → 开闸后仍需执行 EC/DME/AN/TMP 四个显式配体案例 |

## 四、12 项 partial 明细（实测）

| item_id | 要求 | 实测 |
| --- | --- | --- |
| `wp2_sampling_extension` | 采样审计集 3→6 结构比较与 sampling_limited 判定 | 验收 9/9；**escalation_pending 24/24**；已执行 C01,C02,C03…（集合与计划指定 EMC/DEC/DME/TMP **尚不一致，v1.4 步骤 5 修正**） |
| `wp2_flip_persistence` | EMC-GBL / EMC-SL 两对翻转能否保留到自由能层 | rungs 8/12（依赖系综） |
| `wp2_state_identity_qc` | §6.3 每态 QC（SCF/几何/虚频/spin/连接/Li-motif/fragment/frontier） | **13/13 通过**；分类 intact:12、Li_centered:12、mixed:0、ambiguous:0、fragmented:0 |
| `wp3_pair_evidence` | 保守符号一致性 STABLE / UNRESOLVED / ROBUST_INVERSION | pairs 66：**ROBUST_INVERSION 2、STABLE 55、UNRESOLVED 9** |
| `wp3_targeted_second_method` | 关键 pair 第二泛函靶向复核 | plan 24 / ready 24 / blocked 0 / **results 24** |
| `wp3_mechanism_cases` | §7.3 机制案例 ≤3 个 + 六项证据 | cases 2；six_item_pending 8、partial 14 |
| `wp5_new_endpoint_in_budget` | 新端点 O_3≥2/3 且 R_3≤0.10 eV 真的用于算预算 | rounds 296；**computed 8 / blocked 16** |
| `wp5_two_consecutive_points` | ≥16/20 回放在两个连续预算点达标 | **computed 8 / blocked 16**；池为 legacy_18_not_blind |
| `wp5_absolute_cost_ledger` | 绝对成本三项（cpu_core_hours / p90_job_cost / frequency_only_cost） | cost_rows 10，**MISSING 3** |
| `wp5_remaining_unqueried_error` | 每轮报告 n_T→tau_b、O_3、R_3、remaining_unqueried_error、累计 core-hours | **remaining_error MISSING 296/296、cumulative_core_hours MISSING 296/296** |
| `stop_rules_registered` | 停止规则登记（unresolved / sampling_limited / identity / validation） | stop_rules_in_config ✅；li_motif_screen 23/24 |
| `wp2_pilot_cost_fields` | §11 前 2 分子 pilot 逐作业记录 | pilot_rows 109，列齐 |

**12 项 partial 的共同瓶颈**：多数是「方法/框架已就绪、只差生产量」——`wp5_*` 的 computed 8 / blocked 16 全部等系综标签齐备；`wp2_sampling_extension` 的 escalation_pending 等系综层 + 3→6 审计修正；`wp2_flip_persistence` 等系综自由能层。

## 五、两项 not_satisfied（真正的未达成）

1. **`wp2_conformer_ensemble`**：生产级同态系综自由能 **0/48**。
   - 现状：`ensemble_free_energies.csv` 是气相/廉价层结果，**不计入 48 态分母**；
   - **v1.4 已启动**：候选 manifest 已按 48/48 重建（`production_ensemble_candidates.csv`：48 primary + 57 round1 extras = 105 结构）；4 个分块包 18+18+18+3，首包 **job 3718293** 在跑；待写专用 importer + 48 态聚合器（禁止污染 primary 账本）。
   - 缺口收口路径＝v1.4 六步（round1 回收 → 严格 QC → DFT 后二次去重 → Boltzmann 聚合 → 3→6 审计 → 48/48 标签）。
2. **`wp5_pool_extension`**：扩样 **0 行**（计划 §9.3 要求先加 8–12 个分子使池到 20–24）。
   - 现状：ML/AL 回放跑在旧池上；**与系综独立**，须在目标标签 + 独立 uncertainty 可用后单独排产。

## 六、2 项 blocked_on_production

`wp6_explicit_ligand`（Li 配对已 12/12，只差系综 48/48 开闸；开闸后仍需执行 4 个显式配体案例）、`plan_overall_complete`（主态 ✅、系综 ❌、采样审计 ❌、R4 排序依赖前述、升级后 WP6）。

> 首版的另 3 项 blocked（`wp2_production_state_ledger` 60/60、`wp2_four_state_complete` 12/12、`wp2_li_legs` 24/24）已随 TMP/LiM_plus 救援（job 3717952，AnFreq 零虚频导入）转 **satisfied**。

## 七、当前真实进度

| 指标 | 数值 |
| --- | --- |
| 运行进度（60 腿全批次） | **60/60** |
| 主态运行（48 态） | **48/48** |
| 科学验收 | **48/48** |
| 固化交付 | **48/48** |
| 四态完整分子 | **12/12** |
| Li 配对 | **12/12** |
| 生产系综 | **0/48**（round1 57 结构：首包 18 已提交在跑） |
| 归档复算核验 | manifest 5078 处 + 账本 300 处 **零失配**（AnFreq canonical 同源） |

## 八、结论与下一步（v1.4 收口链）

**计划未全部完成。** 分层看：

- **已闭环**：WP0、WP1、WP4，v1.1/v1.2/v1.3 三份修订全部可执行条款，以及 **WP2 的主标签层**（48/48 科学验收 + 12/12 四态 + 12/12 Li 配对，含 AnFreq 折入与 TMP/LiM_plus 救援）。
- **未闭环**：WP2 的**系综层**（0/48，最硬的缺口）、WP5 的**扩样**（独立缺口）、WP6（只差系综开闸）。
- **直接阻塞**：`plan_overall_complete` 与 `wp6_explicit_ligand`，全部等系综。

**v1.4 执行顺序（2026-10-17 用户确认，链条一致前不提交混合工作区）**：
1. ~~闭环 B 全部 `already`~~ ✅（60/60 两轮确认）；
2. ~~重建 canonical 原始归档~~ ✅（`raw_jobs_2167_01413d4d237c_20261017.zip`）；
3. ~~从归档复算并核验账本~~ ✅（零失配、同版新鲜）；
4. ~~刷新本报告~~ ✅；
5. 重跑 finalize 至 ALL GREEN；
6. 补齐系综专用 importer + 48 态聚合器 + 测试；
7. 当前数组 `running+pending ≤ 2` 时提交下一批 18（批次 18→18→18→3）。

之后：3→6 审计修正（EMC/DEC/DME/TMP，补 Li 态 round2 候选）→ 系综 48/48 → WP6 自动升级（仍需 4 个显式配体案例）→ WP5 池扩独立排产。
