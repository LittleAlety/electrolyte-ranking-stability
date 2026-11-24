# 第一仓库 A｜v1.3 计划细化：可执行规格与本地核验结论

**性质**：对《双仓库统一科研计划 v1.3》的**第一仓库部分**做落地细化。不是新计划、不是审计报告，
是把 v1.3 里标 `[L]`（待核验）的断言逐条升级为已核验的 `[V]`，把无法核验的降级为 `HOLD`，
并把每个工作包装配成可以直接开工的规格。

**编制依据**：v1.3 全文 585 行 + 本地只读核验（2026-11-22，A00-v1.3 已交付的 12 项审核 + 本轮新增 7 项核验）。

**核验产物**（机器可校验，非叙述）：

| 文件 | 内容 |
|---|---|
| `outputs/physics_completion_v2/a00_v1_3/A13_evidence_roots.csv` | 72 行逐位置：声明路径 → 实际证据根 → 实盘 sha256 → 匹配判定 |
| `outputs/physics_completion_v2/a00_v1_3/A13_refinement_verification.json` | 两证据根计数、72/72 sha、算子可比性判定、成本审计、三布尔 |
| `scripts/v2/a13_verify.py` | 生成器（只读，不启动任何量化计算） |
| `tests/test_a13_plan_refinement.py` | **15 项**回归，全部通过 |
| `tests/test_a00_v1_3_contract.py` | A00 契约 **19 项**回归，全部通过 |

合并测试结果：`A13_pytest.xml`，`tests="34" failures="0"`。
`determinism`：文档级 `DETERMINISTIC`（零差异）。

**执行边界**：与 A00-v1.3 授权一致——只读审计、生成新文件、不启动量化计算、不提交 HPC、
不覆盖冻结产物、不删历史、不 reset、不 push。本文件**不产生任何科学结论**。

---

## 0. 本轮核验新增的七个硬事实

v1.3 的 `[L]` 标记是对的：它没有谎称自己核过本地 work/。以下七条是本轮逐字节核出来的，
其中三条会直接改变 v1.3 的排期或预算。

### F1｜13 个位置的原始证据在仓库外，不在 `电解液溶剂HB-Code/` 下

`EVIDENCE_MATRIX_18x4.csv` 的 `source_path` 有 72 条，其中 **59 条在仓库内、13 条在仓库外**：

| 位置 | 实际路径（相对 `电解液溶剂-HB/`） |
|---|---|
| EA\|M, EA\|M_plus, EA\|LiM_plus | `docs/handoffs/evidence18_20261107/batch1_recovery_20261109/` |
| MA\|M, MA\|M_plus, MA\|LiM_plus, MA\|LiM_2plus | `docs/handoffs/evidence18_20261107/batch3_ext_20261110/` |
| EA\|LiM_2plus, SN\|LiM_2plus | `work/acceptance_4new_20261117/` |
| TEGDME\|M / M_plus / LiM_plus / LiM_2plus | `work/tegdme_{m,m_plus,lim_plus,lim_2plus}_anfreq_result_202611{18,20,21,22}/` |

**13/13 全部 sha256 与矩阵记录一致**（不是缺失，是路径基准不同）。

**影响**：v1.3 A00 要求 `unpushed_work_inventory` 覆盖"全部 18×4 closure 证据"，但基准写成
`电解液溶剂HB-Code/`。**证据根不是一个，是两个。** 我的 A00 `A00_evidence_manifest.csv`
（9,749 文件）当时只扫了 `电解液溶剂HB-Code/work/`，这 13 个主证据当时在清单外——必须补扫。
这是 A00 的一个真实缺陷，不是 v1.3 的。

### F2｜72/72 的 `source_sha256` 全部校验通过

`EVIDENCE_MATRIX_18x4.csv` 的 72 条 `source_sha256` 与磁盘字节**逐条一致**（59 条仓库内 + 13 条仓库外）。
24 个扩展态的 ORCA 日志**全部含 `NORMAL TERMINATION`**。

频率块有 23/24 命中 `VIBRATIONAL FREQUENCIES` 字面头，**1 个没有**——但该位置
（`MA|LiM_2plus`）本来就是 `A3 = FAILED` 的解离端点，矩阵里 `G_qRRHO` 为空，是设计保留的缺口。
所以正确表述是：**23/24 有热化学点，第 24 个是已登记的解离端点**，不是"有一个日志缺频率"。

**影响**：v1.3 A05 的前提"24/24 A1=COMPLETED 需用同源日志核验"**已经完成**。
A05 从"验真"降级为"编目 + 逐态 QC 签章"，时间可压缩。

### F3｜DMC 的逐 attempt 链条支持 v1.3 §4.1 的"不能混 attempt"

`production_ensemble_structures.csv`（246 行）对每个候选带 `attempt / failure_class /
energy_change_Eh / opt_tier`。**注意这张表的两列名是反直觉的**：`slot` 列存的是**态**
（`M`/`M_plus`/`LiM_plus`/`LiM_2plus`），`member_key` 才是**候选键**（`DMC|LiM_2plus|c06`）。
我第一版解析时搞反了，测试立刻报错——这个坑必须写进计划，否则 A02 会读错表。

DMC 的实际链条：

| 候选键 | attempt | failure_class | energy_change_Eh | status |
|---|---|---|---|---|
| `DMC\|LiM_2plus\|c06` | 0 | `max_cycles_exhausted` | — | superseded |
| `DMC\|LiM_2plus\|c06` | 1 | `strict_reopt_required` | **2.196e-07** | technical_complete_qc_failed |
| `DMC\|M_plus\|28` | 0 | `strict_reopt_required` | 2.0981e-06 | superseded |
| `DMC\|M_plus\|28` | 1 | `strict_reopt_required` | 6.239e-07 | technical_complete_qc_failed |

而且 `DMC|LiM_2plus|tors_7_0_1_2` 有 **attempt 0 / 5 / 12 三代**，各自 failure_class 不同
（空 / `strict_reopt_required` / `verytight_convergence`）。全表共有 6 个 DMC 候选键出现过
多个不同 `failure_class`。

**结论**：`max_cycles_exhausted`（attempt 0）与 `energy_change > 2e-07`（attempt 1）是两次不同尝试，
部分候选还有 3 代以上。v1.3 §4.1 要求"逐 attempt 核对，不把所有 attempt 混成同一失败"——
**现在有原始表支撑，可以执行**，而且 `production_ensemble_structures.csv` 就是 A04 的权威输入，
不需要再找日志。

### F4｜`2.906` 与 `3.851` 分母不同，且 3.851 的配对里不含 EC–PC

这是 v1.3 §4.2 最担心的一条，本轮确证：

| 数 | 值 | 定义 | 队列 | 出处 |
|---|---|---|---|---|
| k=3 边界间隔 | **2.906** kcal/mol | L2 系综层 EC(190.957) − PC(188.051) | **12 分子主集** | `CLOSURE_REPORT_20261117.md:682` |
| 官能团轴最大配对位移（绝热） | **3.851** kcal/mol | wB97X-D4 → PBE0-D4，**C04–C08** 的配对 | **8 分子方法审计队列** | `METHOD_AXIS.json#functional_axis_adiabatic`，`n_molecules=8` |
| 官能团轴最大配对位移（垂直） | 5.971 kcal/mol | 同上，C01–C16，**含 1 个符号翻转** | 8 分子方法审计队列 | 同上 |

**`METHOD_AXIS.json` 的 `cohort_note` 明写：`method_audit cohort only (8 main-set molecules); extension six = NOT_AVAILABLE`。**

所以"2.906 < 3.851"这个比较是**12 分子队列的一个数**和**8 分子队列的一个数**相比，
而且 **3.851 来自 C04–C08（EC–DME），不是 EC–PC**。两者不是同一算子、不是同一队列、不是同一对分子。

**影响**：v1.3 §4.2 说"不能自动成为推断显著性或因果比较"——**这是对的，而且比它以为的更严重**。
A09 不能只是"重新核实定义"，必须**重新构造一个同队列的可比算子**：只能在 8 分子方法审计队列里
算 k 边界间隔，或者只在有方法轴数据的分子上做 Top-3 稳定性。当前 F4 图的写法需要改。

### F5｜`ROBUST_INVERSION` 0 vs 2 仍是两个未命名估计量

仓库里唯一的冻结 pair 表 `pair_evidence.csv` 有 66 对：`STABLE 55 / UNRESOLVED 9 / ROBUST_INVERSION 2`，
**单 σ 列**（`sigma_ev`）。v1.3 沿用 v1.2 的"双来源 σ → 0"，但工作树里仍无双来源 σ 产物。

**沿用 A00 的 C09 裁决：`HOLD`，直到估计量被命名。** v1.3 §4.2 的表述（"可能来自定义性自指σ"）与此一致。

### F6｜TEGDME 实测成本是 p90 的 4–7 倍，A03 预算必须重算

| 来源 | 成本 | 口径 |
|---|---|---|
| `remaining_cost_scenarios.md` p90 | 中性 15.213 / 阳离子 18.406 / Li 20.006 CH | 旧主集 60 腿（12 分子） |
| **TEGDME 四态实测** | M **88.99** / M_plus **87.49** / LiM_plus **102.41** / LiM_2plus **152.20** CH | 单构象主腿，合计 **431.1 CH** |

v1.3 §4.2 写"p90：中性TZVPD约15.2、阳离子18.4、Li配合物20 core-hour/腿"。
这对旧主集成立，**对扩展六分子完全不成立**——TEGDME 一条腿就是 p90 的 5–7.6 倍。

**影响**：A06 的系综补齐预算不能用旧 p90 外推。扩展 24 位置若按 TEGDME 量级，
单构象就 431 CH，加系综（每个位置 2–3 个候选）将是**千核时量级**。
v1.3 §4.2 说"主要瓶颈是人工逐态审签、构象TEGDME风险，而不是24态primary尚未运行"——**前半句对，后半句低估了**。

### F7｜三布尔现在就能算，且值已确定

从 72 行注册表直接算：

| 布尔 | 当前值 | 依据 |
|---|---|---|
| `COVERAGE_CLOSED` | **false** | 27 个位置是 `AUDIT_OPEN_*`（26 系综缺失 + 1 目标物种失败），虽有理由但未闭合 |
| `STRICT_ENSEMBLE_COMPLETE` | **false** | 45/72 actual accepted |
| `SCIENTIFIC_REPORT_COMPLETE` | **false** | 7 条主张 `HOLD_NEEDS_DECISION` |

且 `strict_readiness_wiring.py` 现在可跑，输出 `wp5_full_target_pool_evaluated=false`、
`wp6_trigger_state=not_triggered`。**A12 不需要从零建底座，它是把这两个来源合并 + 加三布尔。**

---

## 1. 对 v1.3 的修正清单（必须先改，再开工）

| 编号 | v1.3 位置 | 现文 | 应改为 | 依据 |
|---|---|---|---|---|
| M1 | A00 输入/输出 | 证据基准统一为 `电解液溶剂HB-Code/` | 声明**两个证据根**：`电解液溶剂HB-Code/`（59 位置）与 `电解液溶剂-HB/`（13 位置） | F1 |
| M2 | A00 输出 | `unpushed_work_inventory.csv` | 拆成 `evidence_manifest_repo_root.csv` + `evidence_manifest_parent_root.csv` + 合并索引 | F1 |
| M3 | A05 定位 | "24/24执行已完成需用同源日志核验"（当作待办） | 标注**已完成**（72/72 sha 校验通过，24/24 NORMAL TERMINATION），A05 改为编目+签章 | F2 |
| M4 | A04 输入 | `[L] 2026-11 closure证据` | 明确权威输入是 `outputs/physics_completion/ensembles/production_ensemble_structures.csv`（246 行，带 attempt） | F3 |
| M5 | A09 / §4.2 | 沿用 "2.906 < 3.851" 作为 Top-3 威胁 | 标为 **INCOMPARABLE_OPERANDS**：不同队列（12 vs 8）、不同分子对（EC–PC vs EC–DME）。A09 必须重建同队列算子 | F4 |
| M6 | §4.2 预算 | p90 = 15.2/18.4/20 CH/腿 | 分两层：**旧主集 p90**（可用）与**扩展六分子实测**（TEGDME 88.99–152.20 CH/腿，431.1 CH/四态） | F6 |
| M7 | A12 | "新增代码 build_closure_release.py" | 复用 `strict_readiness_wiring.py`（已可跑）+ A00 注册表，只新增三布尔封装 | F7 |
| M8 | A03 | 预算基于 p90 外推 | 扩展 24 位置必须**按分子单独定价**，TEGDME 单列上限 | F6 |

---

## 2. 十二个工作包的细化规格

每个包给出：**权威输入（已核验路径）→ 输出 → 必须自动审的断言 → 人裁决点 → 停止条件**。
v1.3 已写的不重复，只写"落地时必须知道、但 v1.3 没写"的部分。

### A00-v2｜补齐父证据根与两份清单

- **前置**：A00-v1.3 已交付（12 项审核 11 PASS / 1 HOLD 设计如此）。
- **必须新增**：
  - `outputs/closure_v13/G0/evidence_manifest_parent_root.csv`：`电解液溶剂-HB/` 根下 13 个位置的
    证据逐文件 sha256。最低必含：`docs/handoffs/evidence18_20261107/**`（7 位置）、
    `work/acceptance_4new_20261117/**`（2 位置）、4 个 `work/tegdme_*_anfreq_result_*/**`。
  - `evidence_manifest_merged_index.csv`：`position_id → repo_root|parent_root → rel_path → sha256`，
    72 行全覆盖。
- **自动审**：
  - 72 个位置每个至少 1 条 `sha256` 匹配的证据路径（当前 72/72 已满足，须成为常驻回归）；
  - 路径基准字段必须显式（`repo_root` / `parent_root`），不允许裸相对路径。
- **人裁决**：无。
- **停止**：任一位置无匹配证据 → `AG0 = HOLD`。

**回归测试**：`tests/test_a00_evidence_roots.py`——构造一个"证据在父根"的位置，断言合并索引能找到它；
再构造"两个根都找不到"的位置，断言 `HOLD` 而非静默通过。

### A01｜72 位置注册表（A00-v1.3 已产出，改为冻结+补字段）

- **已交付**：`outputs/physics_completion_v2/a00_v1_3/core18_v2_state_registry.csv`（72 行 55 列，A00-01/02/03 PASS）。
- **本包只做三件事**：
  1. 迁移到 v1.3 要求的路径 `outputs/closure_v13/registry/`，并保留原文件不动；
  2. 补 `leg_to_state_mapping.csv`：60 腿 → 48 位置逐条映射（注册表已有 `legacy_ledger_state_labels`
     与 `legacy_ledger_record_ids`，直接展开即可）；
  3. 补 `pool_role_exclusions.csv`：6 `core_remaining` 保留 + 5 `broad_pool` 排除，逐行给理由。
- **自动审**（沿用 A00-01/02/03，全部已 PASS）：72 唯一键；60 腿全部消费；`M_tzvpd` 折叠到 `M`
  且不产生第 5 态；`core_remaining` 恰 6、`broad_pool` 恰 5 且零泄漏。
- **人裁决**：20 个位置的电荷/多重度仍为空（FEC/VC/EA/MA/SN × 4）——见 A00 的 C22。
- **停止**：键冲突或无证据替代 → `FAIL`。

### A02｜taxonomy 与旧结论更正

- **权威输入**：`production_ensemble_structures.csv`（246 行，带 `attempt/failure_class/energy_change_Eh`）
  + `production_ensemble_labels.csv`（48 行 acceptance）+ `EVIDENCE_MATRIX_18x4.csv`（五轴）。
- **必须输出**：`taxonomy_crosswalk.csv`，字段至少：
  `position_id, attempt, raw_opt_failure_class, raw_sampling_failure_class, a1..a5, legacy_acceptance_status, v13_disposition, evidence_sha256`。
- **必须显式分离的六层**（v1.3 §4.1 已列，此处落字段）：
  `run/SCF` → `Opt五阈值` → `Hessian/虚频` → `identity` → `sampling/ensemble` → `final disposition`。
- **自动审**：
  - 每一行的 `raw_opt_failure_class` 必须来自 `production_ensemble_structures.csv` 的实际值，
    不得由 `acceptance_status` 反推；
  - `max_cycles_exhausted` 与 `strict_reopt_required` 必须落在**不同 attempt 行**（F3）；
  - 旧 48 行的 `legacy_acceptance_status` 必须与冻结表逐字一致（A00-08 已强制）。
- **人裁决（这是 A02 的真正工作）**：
  - `DMC|M_plus`：`sampling_limited`（冻结表）还是 `E_single_screened_QC_failed`（verdict）→ A00 的 C04；
  - `DMC|LiM_2plus`：同上 + attempt 0/1 归因；
  - `EC|LiM_2plus`：`provisional` → 最终态；
  - `DOL|LiM_2plus`：确认放行，保留历史 `n_limited=1`（A00 已保留 11 条放行记录）。
- **停止**：五阈值与 Opt 收敛混用 → `FAIL`；改写旧标签 → `FAIL`。

### A03｜预算与授权（本次核验改变最大的一包）

- **必须输出**：`cost_forecast.csv`，**按分子分行**，不得按旧 p90 外推：

| 分子 | 单构象实测 | 依据 |
|---|---|---|
| TEGDME | 88.99 / 87.49 / 102.41 / 152.20 CH（四态） | 矩阵 `cost_core_hours`，实测 |
| 其余扩展五分子 | 需从执行账本恢复（矩阵该列为空） | **缺口，见下** |
| 旧主集 12 分子 | p90 15.213 / 18.406 / 20.006 CH/腿 | `remaining_cost_scenarios.md` |

- **核验发现的新缺口**：扩展 24 位置里**只有 TEGDME 四态有 `cost_core_hours`，其余 20 个为空**。
  主集 48 位置有 46 个有成本。所以"扩展六分子系综预算"目前**只有 1/6 分子可定价**。
- **自动审**：
  - 无授权额度时 `submission_allowed = false`（A00-10 已强制）；
  - 每个位置的估算必须标 `measured | p90_extrapolated | unknown`，**`unknown` 不得写 0**；
  - 达到授权 80% 触发 `budget_stop_report.json`。
- **人裁决**：扩展 20 个未知成本位置，是补执行账本还是按 TEGDME 量级保守上界。
- **停止**：未签授权 → 禁止 submit；账本漏失败成本 → `FAIL`。

### A04｜四态结案（不是四态救援）

- **权威输入（已核验）**：`production_ensemble_structures.csv` 的 attempt 链 + `strict_recovery_v1_report.md`。
- **必须输出**：`DMC_M_plus.json`、`DMC_LiM_2plus.json`、`EC_LiM_2plus.json`、`DOL_release_trace.json`。
- **每份失败证书必须含**：`position_id, attempt_id, failure_class, energy_change_Eh, threshold,
  candidate_count, kept_count, dedup_rmsd_a, adds_member(bool), verdict`。
- **自动审**：
  - attempt 之间不得合并；
  - `DOL` 的 accepted 与历史 `n_limited=1` 必须同时存在（A00-08 已强制）；
  - 只有 `adds_member == false` 且 `recovery_state == COMPLETED` 才允许写"不可闭合"。
- **人裁决**：三态各签"已救回 / 预算耗尽 / 不可比 / 待复核"。
- **停止**：缺原始日志 → `HOLD`；零预算续算 → `FAIL`。

**这一包的实质**：v1.3 把它改名为 `four_state_closeout`（不再叫 rescue），方向是对的——
F3 证明问题已经有答案（候选 QC 失败 + 几何重复），不需要新算力。

### A05｜扩展 24 态验真（已完成 60%，降级为编目 + 签章）

- **已完成（F2 核验）**：72/72 `source_sha256` 匹配；24/24 `NORMAL TERMINATION`；
  TEGDME 四态含频率、零虚频。
- **剩余工作**：
  1. 逐位抽取并结构化：`imaginary_modes, lowest_freq_cm1, n_freq, charge, multiplicity, atoms`；
  2. 补 20 个位置的电荷/多重度（矩阵该列为空）；
  3. 逐态 QC 签章（人工）。
- **自动审**：执行完成 ≠ QC 通过；`A5 = MISSING_EVIDENCE` 必须保留（24/24）；
  `MA|LiM_2plus` 的 `A3 = FAILED`（解离端点）必须保留。
- **人裁决**：FEC/VC 是否有碎裂/自旋漂移 → `identity_outcome`；TEGDME 配位 motif 单列。
- **停止**：只读证据无法验证 → `HOLD`；不得重开空白 24 态生产。

### A06｜扩展 24 位置系综补齐（真正的计算包）

- **前置**：A03 额度（当前 `null`）+ A05 签章。
- **真实缺口规模**：24 位置 × 每位置需 2–3 个候选 → 48–72 次构象/配位优化 + 频率。
- **成本情景（用 F6 实测重算，不用旧 p90）**：

| 情景 | 假设 | 估算 |
|---|---|---|
| 乐观 | 5 个分子按旧主集 p90（~18 CH/腿），TEGDME 按实测 | ~5×18×4 + 431 ≈ **791 CH** |
| 中性 | 扩展平均取 TEGDME 的 40% | ~24×4×0.4×107 ≈ **4,100 CH** |
| 保守 | 扩展全部按 TEGDME 量级 | ~**10,300 CH** |

**这三个数说明：v1.3 把 A06 排在 12-07—01-31 且只说"系综补齐"，预算上是不成立的。**
必须先在 A03 拿到扩展五分子的真实成本，才能定 A06 的额度与停止线。
- **自动审**：不重复生产已通过的 primary；Li motif 去重；每个新成员登记真实 attempt 成本；
  `N=1` 必须 coverage 复核。
- **停止**：无新合法盆地 + 预算穷尽 → `sampling_limited` + 证书；**不为了 72/72 放宽阈值**。

### A07｜逐态物理 QC

- **可复用**：`build_state_identity_qc.py`、`build_frontier_identity_evidence.py`、`frontier_spin_qc.py`（均已核验存在）。
- **必须承认的现状**：`frontier_localization_status = not_computed 60/60`（FINAL_VERDICT）；
  `M_plus` 的 `redox_localization_class` 空 12/12。
- **自动审**：SCF / 五阈值 / Hessian / 虚频 / 热化学 / 键图 / spin-fmo / Li 局域，**各层不得互相代替**；
  0 虚频 ≠ 通过。
- **停止**：任一物理 QC 失败不得 accepted。

### A08｜系综权重与自由能

- **可复用**：`build_production_ensemble_aggregator.py`、`build_sampling_3to6_diff.py`、`build_sampling_ceiling_classification.py`。
- **已知限制（必须写进 A08 输出）**：主集 48 位置 80 唯一成员/98 候选，24/48 位置只有 1 个成员。
- **自动审**：温度/标准态一致；`∑w = 1`；缺失不补 0；有限池不得称收敛；TEGDME 单列。
- **停止**：只有初筛无 DFT 极小 → 不可 accepted。

### A09｜Top-3 边界威胁重审（本轮核心修正对象）

- **必须推翻的旧写法**：`2.906 < 3.851` 作为 Top-3 威胁（M5，F4 已证不可比）。
- **必须重建**：同队列可比算子。可行路径只有两条：
  1. 在 **8 分子方法审计队列**内算 L2 的 k=3 边界间隔，与 3.851 直接比；
  2. 明确声明"方法轴数据只覆盖 8 分子，EC/PC 的方法轴敏感性不可估"，
     把 Top-3 结论降级为 `THIRD_SEAT_UNRESOLVED_METHOD_DATA_MISSING`。
- **自动审**：
  - 任何跨队列比较必须带 `cohort_i/cohort_j` 字段，且断言相同才允许相减；
  - `robust_inversion = 0` 不得作为稳定证据（C09 仍 `HOLD`）；
  - 2.906/3.851 的单位、分母、分子对逐值溯源。
- **人裁决**：选路径 1 还是 2；选 2 则 F4 图重画。
- **停止**：差值定义不明 → 只保留 `candidate observation`。

### A10｜WP5 固定池与 regret

- **可复用**：`run_wp5_AB_replay.py`、`run_wp5_blind_replay.py`、`wp5_replay_contract.py`、`build_wp5_target_pool.py`。
- **现状**：`strict_readiness_wiring.py` 报 `wp5_full_target_pool_evaluated = false`。
- **自动审**：同 repeat 同初始标签；16/20 在**两个相邻预算点同一 repeat** 同时达标；
  `O3 ≥ 2/3` 且 `R3 ≤ 0.10 eV`。
- **停止**：样本太少 → 描述性；缺一致目标池 → `NO_DECISION_CLAIM`。

### A11｜外部效度与主张矩阵

- **现状**：锚点 87 行，`tier_1 = 0`、`tier_2 = 14`、`tier_3 = 73`，Gate1 仍 `NOT_CLOSABLE`。
- **自动审**：Gate1 失败状态不得被任何 v2 脚本重写（A00-08 已强制到注册表级）。
- **停止**：无同源实验锚点不得标 `experimentally_validated`。

### A12｜三布尔与只读发布

- **底座（已核验可跑）**：`strict_readiness_wiring.py` 输出机器可读 readiness；
  A00 注册表输出 72 行处置。A12 = 两者合并 + 三布尔。
- **当前三布尔值**（F7）：`false / false / false`。
- **自动审**：
  - 三布尔各自独立计算，不得互相替代；
  - `COVERAGE_CLOSED=true` 的判定必须允许 `limited` 存在，但不允许"未尝试且原因空白"；
  - `STRICT_ENSEMBLE_COMPLETE` 只由 72 个 accepted 算出。
- **停止**：任一未解释位置 → `COVERAGE_CLOSED=false`；读不到受控原始证据 → 发布 `HOLD`。

---

## 3. 修订后的 A 关键路径（与 v1.3 的差异）

| 日期 | 门 | v1.3 原定 | 本细化建议 | 理由 |
|---|---|---|---|---|
| 11-29 | AG0 | A00 初版 | A00-v2：补父证据根（F1），72/72 sha 回归 | 13 位置证据在清单外 |
| 12-02 | — | A01 建档 | A01 冻结 A00 注册表 + 补 3 张映射表 | 72 行已建好，别重做 |
| 12-06 | AG0 关门 | A02 taxonomy | A02 必须含 DMC 四态人裁决（C04） | 不裁定则 A04 无法开 |
| 12-13 | AG1 | A04+A05 | A04 只出证书（F3 已给答案）；A05 编目+签章（F2 已验 60%） | 两包都比 v1.3 轻 |
| 12-20 | — | — | **新增：A03 扩展成本补账**（20 位置未知成本） | 不定价则 A06 无法授权 |
| 01-31 | AG2 | 24 态系综补齐 | **依赖 A03 额度；当前不可承诺**（F6 显示可能千核时级） | 预算未定 |
| 02-14 | AG3a | A09 Top-3 重审 | A09 必须先重建同队列算子（M5） | 2.906/3.851 不可比 |
| 02-28 | AG3b | A12 发布 | 不变，但底座复用 `strict_readiness_wiring.py` | 已可跑 |

**关键路径变化**：v1.3 把 A06 放在 12-07 开工。按 F6，扩展系综成本可能是 4,100–10,300 CH，
在 A03 没有额度前开工等于无授权消耗。**建议 A06 改为"额度到位才开工"，并把它从"必经"改为"条件必经"**——
用 `sampling_limited` 证书结题也是 v1.3 自己承认的合法出口。

---

## 4. 必须先解决的七个人裁决（阻塞项）

| ID | 阻塞对象 | 问题 | 不裁定的后果 |
|---|---|---|---|
| D1 | A02/A04 | DMC 两态用哪套 taxonomy | 72 行处置表出现两套并行分类 |
| D2 | A09/A11 | 2.906 vs 3.851 是否重算 | F4 图无法落笔 |
| D3 | A09 | 双来源 σ 是否存在 | `ROBUST_INVERSION` 无法引用 |
| D4 | A03/A06 | 扩展 20 位置的未知成本如何定价 | 系综预算无法授权 |
| D5 | A01/A07 | 20 位置电荷/多重度从哪恢复 | 身份轴 72/72 不完整 |
| D6 | H1 | 18 母体 InChIKey | H1 交接建不起来 |
| D7 | A12 | 54 个被删的已提交文件恢复还是退役 | 发布无法声明"干净检出" |

D1–D5 与 A00 的 C04/C09/C22/C26 是同一批；D2 与 C17 相关。**A00 的 7 条 HOLD 主张与本表基本一一对应**，
说明 A00 已经找到了正确的阻塞点。

---

## 5. 交接 H1 的前置缺口（现在就能看见的）

| 字段 | 状态 | 来源 |
|---|---|---|
| `parent_inchikey` | **缺失** | `data/` 下无任何 InChIKey 列 |
| `charge/multiplicity` | **20/72 空** | `EVIDENCE_MATRIX_18x4.csv` |
| 72 行处置闭合 | false（27 open） | 注册表 |
| 证据根 | **两个** | F1 |
| 被删的已提交文件 | 54 个 | `git status` |

**H1 不是"到时间自然能交"的包**：InChIKey 与电荷/多重度是硬缺口，必须在 A01/A07 期间补，
不能留到 H101（2027-03-01）才发现。

---

## 6. 本轮新增的回归测试清单

| 测试 | 人造坏输入 | 断言 |
|---|---|---|
| `test_a00_evidence_roots.py` | 位置证据只在父根 | 合并索引能找到；两处都没有 → `HOLD` |
| `test_source_sha_full.py` | 任一位置 sha 不符 | 72/72 必须全过，否则 `AG0 HOLD` |
| `test_dmc_attempt_separation.py` | 把 attempt 0/1 的 failure_class 合并 | `FAIL` |
| `test_operand_comparability.py` | 跨队列相减 2.906 与 3.851 | `FAIL`（缺 `cohort` 字段即拒） |
| `test_extension_cost_not_zero.py` | 未知成本写成 0 | `FAIL`（必须 `unknown`） |
| `test_three_boolean_independence.py` | 用 `coverage_closed` 冒充 `strict_ensemble_complete` | `FAIL` |
| `test_a05_execution_not_acceptance.py` | `A1=COMPLETED` 推出 `A5=accepted` | `FAIL` |

前两条是**存储层**回归（证据根 + 全量 sha），中间三条是**语义层**回归（不能混 attempt、
不能跨队列比、不能空当 0），后两条是**结论层**回归（三布尔独立、执行不等于验收）。
v1.3 §6 已有 19 条反例矩阵，本表是它的第一仓库补集。

---

## 7. 一句话总结

v1.3 的方向是对的，而且比 v1.2 更诚实（它明说自己没核过本地）。

本轮核验把它标 `[L]` 的断言升级为 4 条已确证、3 条需修正：

- **已确证**：45/2/1 ✅；24/24 执行完成 ✅；72/72 sha 匹配 ✅；扩展系综全缺 ✅
- **需修正**：证据根有两个（F1）；DMC 逐 attempt 链已有权威表（F3）；TEGDME 成本是 p90 的 4–7 倍（F6）
- **必须重做**：`2.906 < 3.851` 不是同一算子的比较（F4）——这是 A09 的核心工作，不是"重新核实定义"

**最需要改的不是工作包，是 A06 的预算前提。** 在扩展五分子的真实成本补上之前，
"12-07 开工、01-31 补齐 24 态系综"这条排期是不成立的；而 `sampling_limited` 证书结题
本来就是 v1.3 承认的合法出口。
