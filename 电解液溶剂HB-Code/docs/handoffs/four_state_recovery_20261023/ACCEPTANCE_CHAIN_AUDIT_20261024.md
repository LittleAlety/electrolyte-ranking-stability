# 验收链离线审计（2026-10-24；**花 800 core-hours 之前先证明闸门真会响**）

目的：确认「提交生产计算后，验收标准真的会被执行」，而不是只在文档里写着。
全部结论来自只读代码审阅 + 既有测试 + 本轮新增测试；**未运行任何 ORCA/xTB，未触网**。

## 1. 端到端证据链（file:line 级）

| # | 环节 | 位置 | 行为 |
|---|---|---|---|
| 1 | **容差同一性**（第一道反漂移） | `import_hpc_opt_numfreq.py:163-165` | ORCA 打印的容差必须等于 `VERY_TIGHT_THRESHOLDS[key]`（`abs_tol=5e-12`），否则抛 `VeryTightOpt tolerance mismatch for <key>`。**请求更宽容差的腿会被拒收，不会被按更宽的数字接受。** |
| 2 | **五项数值强制** | `import_hpc_opt_numfreq.py:166-168` | 任一 `value > frozen` 即抛 `VeryTightOpt final criterion not met: <key>=<v> > <frozen>`（覆盖 TolE / TolRMSG / TolMaxG / TolRMSD / TolMaxD）。 |
| 3 | **缺值不造数** | `import_hpc_opt_numfreq.py:158-162` | `Energy change` 行缺失时登记 `energy_change_absent = first_point_convergence_geometry_never_moved`（首点即收敛、原子未动）；**其它行缺失直接抛错**。 |
| 4 | **TolE 的专项裁决** | `import_ensemble_structures.py:935-947` | 终点判据失败且几何四项达标 ⇒ 旗标 `strict_reopt_required`；代码内记录 2026-10-17 裁决：**reject**，补救是从该末几何严格重优化。 |
| 5 | **旗标→状态** | `import_ensemble_structures.py:1047-1056` | **任一** flag ⇒ `status=technical_complete_qc_failed`、`failure_class=flags[0]`；无 flag 才是 `computed`。 |
| 6 | **不入池** | `build_production_ensemble_aggregator.py:817-818` vs `824-854` | 只有 `status=="computed"` 进 `extras_pool`；`technical_complete_qc_failed` 只计入 rescue/failed/limited，**永不入池**。 |
| 7 | **并使该态无法 accepted** | `tests/test_build_production_ensemble_aggregator.py:261-273` | 有 `strict_reopt_required` 额外成员时，态为 `provisional`、`n_unresolved=1`（不是 `accepted`）。 |
| 8 | 其余硬闸门 | `import_ensemble_structures.py:959-969` | `n_freq == 3N`、`imaginary_modes == 0`、热化学齐备、`|G − (E + thermal)| ≤ 2e-7` 恒等式；连接关系 start→final 不变；Hessian↔几何用**框架无关**的原子对距离不变量校验（`:73-121`）。 |

**结论：五项阈值与六项验收在**写入路径与聚合路径**上都真正 fail-closed**；`geometry_criteria_ok` 对缺值返回 `False`（`import_ensemble_structures.py:124-129`），不存在「缺值默认为零」。

## 2. 已发现并关闭的五个缺口（G1–G5）

### G1（前一轮已修，`06d08aa`）五项阈值无一致性守卫
三份表示（代码常量 / 冻结契约 / 两处生成器散文）之间**没有任何测试**。已补三道测试覆盖；RED 实证见 `work/_threshold_guard_red.py`。

### G2（本轮修复）容差同一性护栏**无测试**
第 1 环 `tolerance mismatch` 是反漂移的关键护栏，但既有测试**只改数值列**（4e-5 > 3e-5），**从未改容差列** → 该分支零覆盖；把它放宽或放松 `abs_tol` 都不会被发现。
**修复**：新增 `tests/test_hpc_opt_numfreq_import.py::test_a_printed_tolerance_that_differs_from_the_frozen_one_is_rejected`，对 **5 个键逐一**断言「容差列被改 ⇒ 抛 `tolerance mismatch for <key>`」，并先断言冻结表本身被接受。
**RED 实证**（`work/_tolerance_guard_red.py`）：护栏在位 GREEN；把 `math.isclose` 中和为恒真后，该测试**按预期失败**（`Failed: DID NOT RAISE ValueError`），退出码 0，生产模块未被改动。

### G3（本轮修复）**SCF 收敛此前在生产验收路径上没有任何断言**
计划 §6.3 把 SCF 收敛列为**不可被其它项替代**的检查之一，但 `import_ensemble_structures.py` 只断言
`ORCA TERMINATED NORMALLY`（:867）——那只是**技术标记**；`import_hpc_opt_numfreq.py:576-591` 的
「absolute guard」守的是「热化学 ↔ 末次单点能」一致性（≤1e-5 Eh），**也不是** SCF 断言；
`build_state_identity_qc.py` 只在**文档字符串**里提 SCF、实现里没有。⇒ 一个 SCF 未收敛的腿曾可能走到 `computed`。

**先测量后动手（无翻转证明）**：对 `production_ensemble_structures.csv` 中所有**入池腿**
（status `computed`/`ready`，共 **115** 条）逐条读其**记录的 `log_path`** 核对：
**115/115 全部带 `SCF CONVERGED AFTER N CYCLES`、`log_sha256` 全部相等、日志文件无一缺失**
（另：`work/wp2prod/**/*.log` 126 个中 125 个带签名，唯一例外是非腿日志 `_reopt/watch_reopt.log`；
8 个含「NOT CONVERGED」字样的**全部位于 `superseded_numfreq/`、`superseded/` 历史目录**）。
⇒ 加该断言**不翻转任何现行接受状态**（脚本 `work/_scf_nodiff_proof.py`）。

**修复**：新增 `RE_SCF_CONVERGED` 与 `qc_task` 中的门（缺签名 ⇒ flags 加 `scf_not_converged`
⇒ 经既有逻辑变 `technical_complete_qc_failed`）。测试夹具 `_log()` 与 `_converged_final_log()`
**补上真实 ORCA 必打的签名行**（原夹具造出了一份真实运行不会产生的日志，加门后 9 个测试立刻变红，
这本身就是门生效的证据）；新增
`tests/test_import_ensemble_structures.py::test_a_log_without_an_scf_convergence_signature_is_qc_failed`。
**RED 实证**（`work/_scf_gate_red.py`）：护栏在位 GREEN；把 `RE_SCF_CONVERGED` 中和为「匹配一切」后
该测试**按预期失败于 `AssertionError`**，退出码 0。
（注：第一次演示用同一临时目录重跑，失败原因是 `FileExistsError` 而非断言——那是**无效演示**，已改用全新目录重做。）

### G4（本轮修复）冻结的 **6 kcal/mol 筛选窗**在 4 处表示上**零守卫**
筛选窗决定「哪些筛选盆地可成为生产候选」，属 load-bearing；但实测它有 4 处独立表示，而
`tests/` 对 `WINDOW_KCAL` / `ENERGY_WINDOW_KJ` / `window_kcal` / `"6 kcal"` 的**引用数 = 0**：

| 位置 | 表示 |
|---|---|
| `build_production_ensemble_manifest.py:82` | `WINDOW_KCAL = 6.0`（并派生 `WINDOW_KJ = ×4.184`） |
| `build_gap_decision_support.py:70` | `WINDOW_KCAL = 6.0` |
| `build_sampling_audit_3to6.py:59` | `WINDOW_KCAL = 6.0` |
| `screen_li_motifs.py:71` | `ENERGY_WINDOW_KJ = 25.0`（= **5.975 kcal/mol**，比 6.0 kcal **略紧 0.1%**） |

对比：同层的 `DUP_TOL_KCAL` / `ESCALATE_TOL_KCAL` **已被既有测试钉住**（`tests/test_wp2_ensemble.py`
的 `test_free_state_pool_keeps_the_registered_screen_discipline`），**窗口这几份却谁都没钉** ⇒ 只改一份
就能静默改变入池判定而没有测试变红（与 G1 同类）。

**修复**：新增两道测试（落在 `tests/test_wp2_ensemble.py`，与 KEEP/DUP/ESCALATE 钉子同处，**不新增测试文件**）：
1. 三份 `WINDOW_KCAL` 必须恒等于 `6.0`，且 `WINDOW_KJ == WINDOW_KCAL × 4.184`；
2. `ENERGY_WINDOW_KJ` 钉住 `25.0`，**且必须 ≤ 6.0 kcal/mol** —— 钉「关系」而非只钉数字，以记录那 0.1% 的差异，
   并挡住将来「把钉子改成跟代码一致」的改动。

**RED 实证**（`work/_window_guard_red.py`）：真源 GREEN；把其中一份副本改成 `7.0`、把 kJ 改成 `30.0`
（> 6 kcal）后，两道守卫均按预期 `AssertionError`；被审的 5 个生产模块**未被改动**。

### G5（本轮修复）**`coverage_route()` 的 7 个 route 里有 3 个「零数据 + 零行为测试」**；错拼在本地会降级（下游 fail-closed 兜住）
实测（AST 取产出侧 + 真实数据统计）：

| route | 14 条真实 `coverage_reviews.csv` 行数 | `tests/` 引用文件数（**加守卫之前**测量） |
|---|---|---|
| `multi_basin_coverage` | 8 | 3 |
| `single_basin_verified` | 2 | 1 |
| `unresolved_qc` | 2 | 0（仅间接：合成行喂给下游校验器） |
| `search_exhausted` | 2 | 2 |
| **`known_basin_reproduction`**（计划分支 2「回到已知盆地」） | **0** | **0** |
| **`pending`** | **0** | **0** |
| **`dedup_evidence_required`** | **0** | **0** |

> **口径更正（2026-10-25，由独立复核 `audit_g5_route_coverage_20261026/` 逼出）**：上表第三列是**加守卫之前**的测量。
> 守卫本身就点名了全部 7 个 route，所以**「零测试」现在只能按「零行为测试」理解**：
> 三个 route 的**数据行数仍精确为 0**，但它们的唯一测试引用是
> `test_resolved_route_evidence.py` 的冻结词表元组与 AST 守卫本身——**没有任何行为测试跑过这三条分支**。
> 独立复核同时**逐行复现了本表全部计数**（`STAGE2_counts.md` §2.3：8/2/2/2 与三个 0，逐项 ✅）。

**为何是风险（含**下修**：下游其实会报，但不是静默通过）**：`build_coverage_reviews.py:357–375` 的 route→verdict
映射带 **`else: verdict = "pending"`** 兜底；`:380` 又用**同一字符串**决定 `kept_evidence` 是否从 `duplicate_of` 取
（分支 2 的「只增覆盖证据」规则）。产出侧错拼**一次造成两件事**（独立复核逐行确认，`STAGE3`）：
① `unresolved`（确定的「否」）被降级成 **`pending`**（什么也没决定）；② **`kept_evidence` 被清空**（:388）。
另有一处退化：**`pending` 自身的错拼在行为上不可见**（正确与错拼都落到 `verdict="pending"`）。
**方向要分层看**：在 `build_coverage_reviews.py` **内部**它**看似 fail-open**（朝「不再阻塞」的方向走）；
但**下游 fail-closed**——`strict_readiness_wiring.py:167` 用 `COVERAGE_ROUTES` frozenset 校验 route（未知即报错），
`:179-180` 对 `verdict == "pending"` 报「review still pending (evidence not settled)」⇒ **链路重跑时严格门会变红**。
所以真实缺陷不是「静默通过闸门」，而是**三份 route 词表副本之间可以协调错拼**：
① `coverage_route()` 的产出字符串；② 映射处的比较字符串；③ `strict_readiness_wiring.COVERAGE_ROUTES` 的 frozenset。
只改 ①（或只改 ②）会被守卫抓到；③ 单独改会被下游抓到（`COVERAGE_ROUTES` 校验）；**唯一残余漏洞是全 ①+②+③ 协同改名**——
而那三个零数据 route 正是改名最易漏的地方。

**修复**：新增 `tests/test_resolved_route_evidence.py::test_the_coverage_route_vocabulary_is_frozen_and_mapping_complete`，
**用 AST**（不能靠文本匹配：`pending` 是裸逗号元组 `return "pending", "..."`）钉两件事：
① 产出侧 route 集合恒等于 7 元冻结集；② **每个能吐出的 route 都必须在 `coverage_route()` 函数体之外被点名**
（即映射/证据分支），任一侧错拼都会失败。该测试**不依赖任何数据**，干净克隆同样生效，
把「下游才发现」提前成「源头即失败」。

**RED 实证**（`work/_route_guard_red.py`）：真模块 GREEN；**产出侧**注入错拼 → 失败于 `vocabulary drifted`；
**仅映射侧**注入错拼 → 失败于 `never named elsewhere`；两次均不改动真实模块。

### 附：Phase-2 四条固定分支的映射（Lead 自查，取代失败的委派）
| 计划分支 | 落地位置 | 状态 |
|---|---|---|
| ① 发现合法新盆地 | coverage route `multi_basin_coverage`（+ `new_minima_found`）→ verdict `resolved` | 有数据(8)、有测试(3 文件) |
| ② 回到已知盆地 | route **`known_basin_reproduction`** → verdict `unresolved`；规则「只增覆盖证据、不增简并度」由 `:380` 取 `duplicate_of` | **route 名零数据零测试** → G5 已补词表/映射守卫 |
| ③ 身份漂移或断环 | **不在 coverage 层**，而在成员层：`species_drift_unrecoverable` 处置 / `member_next_action.stop_species_drift`（有测试）/ 导入器 `restart_species_drift` 拒收（有测试） | 有测试(4+1+1 文件) |
| ④ 八条均无可用新盆地 | route `search_exhausted` → verdict `search_exhausted`；`COVERAGE_SETTLED` 视其为「已定」 | 有数据(2)、有测试(2 文件) |

⇒ **四条分支都有落地位置，没有「无处可去」的分支**；唯一零覆盖的是分支 ②（已由 G5 补上词表/映射守卫）。

### 附：系统性常量守卫扫描（**负结果，用于界定审计边界**）
为确认「G1/G4/G5 这一类缺口还有没有别的」，做了一次全量扫描（`work/_constant_guard_sweep.py`，只读）：
按 AST 取出 `scripts/wp_production/*.py` 的**全部模块级字符串集合常量**并统计其名字/成员是否被 `tests/` 引用。
- 结果：**133 个常量，84 个名字零测试引用**。
- **但其中没有新的一类缺口**，因为逐条看下来它们分两类：
  1. **列名表**（`FIELDS`/`ACC_FIELDS`/`MAP_FIELDS` 等）：结构上由 CSV 读写间接引用，钉名字无意义；
  2. **闸门自己会用数据自校验的词表**：`strict_readiness_wiring.py` 会拿 `COVERAGE_ROUTES`(:167)、
     `COVERAGE_VERDICTS`(:169)、`WP5_STOP_STATUSES`(:381) **逐个校验传入产物**，未知 token 即报错
     ⇒ 生产者/消费者不一致会在链路重跑时**响亮失败**。
- **判据（可复用的分界）**：只有当某个冻结常量**存在独立的权威副本**（另一份契约、另一模块、生成器散文）
  且**没有任何下游对账**时，才构成 G1/G4/G5 那一类真缺口；只有一份副本的词表由「下游数据自校验」兜住。
⇒ 本轮审计的 G 系列到此**收敛**：已无同类未处置缺口。

## 3. WP5 目标池前置审计（只读，2026-10-25）：**缺额恰好等于四个 limited 态**
用 `build_wp5_target_pool.build_rows()`（**纯投影 labels CSV**）实测，并与端点表 `AB_axis_endpoint.csv` 的 `n_pool` 对账：

| 任务 | 态对 | 两腿都 accepted 的分子数 | 缺谁 | 缺的原因（该腿） |
|---|---|---|---|---|
| **A** | (`M_plus`, `M`) | **11 / 12** | **DMC** | `M_plus` = `limited`（`M` 腿 accepted） |
| **B** | (`LiM_2plus`, `LiM_plus`) | **9 / 12** | **DMC、DOL、EC** | 三者的 `LiM_2plus` = `limited`（`LiM_plus` 腿全部 accepted） |

**对账结果**：builder 给的 `{A:11, B:9}` 与端点表记录的 `n_pool`（A=11、B=9，各 16 组）**完全一致**。
⇒ **`wp5_full_target_pool_evaluated` 的缺额就是那四个 limited 态本身，没有任何别的因素**；
四态一旦按现有规则转 `accepted`，A 与 B 应同时到 12/12，随后需按正式协议**重跑** A/B 回放（池变了，旧回放不作数）。

### 4.1 一处**层间措辞冲突**（如实记录，未改账本）
四个 limited 态的 label `limitation_reason` **全是 `rescue_budget_exhausted`**，但成员层计数与它**自洽**
（DMC\|M_plus 与 DMC\|LiM_2plus 各 `n_registered=2`/`n_qc_failed=2`；DOL\|LiM_2plus `n_registered=2`（1 失败 + 1 去重）；
EC\|LiM_2plus `n_registered=1`——代码判据是**每成员 attempted≥2**，单个成员可被尝试两次，故与「登记数≥2」不是一回事）。
**冲突在于层与层的说法**：`coverage_reviews.csv` 对 DOL/EC 明写
「single-basin is a physical finding at the screening level, **not** a budget failure」
（route=`search_exhausted`，`registered_starts=''`），而 label 写 `rescue_budget_exhausted`。
原因在 `build_production_ensemble_aggregator.py:938-940`：`if n_limited and not cov_resolved:` 先定粗原因，
**早于** `:941-949` 那串更细的分支（`no_registered_extras` / `single_basin_pool` / …）。
**风险**：读者可能据此推出「再加预算就能找到极小」，而覆盖复核恰好否认这一点（其对 DOL/EC 的结论是
「筛选层就是单盆地，属物理发现」）。
**处置**：**不改**冻结账本（labels 被多处产物哈希引用，且这是标签口径决策，须由 Lead/用户定）；
若将来要改，最小修法是让 `:938-940` 在 `cov.verdict == "search_exhausted"` 时不要抢占
`single_basin_pool` 这一更准确的原因，并同步重建下游链。

## 4. 是否把该门继续下沉到主态路径？——**已测量，结论：不下沉**（2026-10-24）
**门的位置决定了保护面**：`RE_SCF_CONVERGED` 在 `qc_task` 里，因此覆盖**经它的注册新增成员**——而
`production_ensemble_candidates.csv` 的实测构成是 **48 primary + 57 round1_extra + 14 recovery_v1_start**，
即**新增计算全部以 extra 身份走 `qc_task`**，已被覆盖。
**48 个冻结主态**走 `primary_rows()`（`import_ensemble_structures.py:1075-1114`），从 `candidates.csv`
取 `status`、复制逐腿 JSON 字段，**无 SCF 断言**。

**若下沉，代价与收益的实测**（脚本 `work/_scf_status_matrix.py`、`work/_scf_package_cost.py`）：
| 实测项 | 数值 |
|---|---|
| `production_ensemble_structures.csv` 全部**有日志**的行（含 89 `superseded` + 31 `technical_complete_qc_failed`） | **235/235 全部带 SCF 签名** |
| 无日志的行 | 仅 **3** 条 `pending`（中途抓取的日志，`qc_task` 的终止标记已先返回 `pending`，不会走到 SCF 检查） |
| `work/hpc_*/**` 全部包日志 | **434 个，431 带签名（99.3%）**；17 个无 `ORCA TERMINATED NORMALLY` |
| 3 个无签名者 | 2 个是批处理驱动日志（`local_batch*.log`，非腿日志）+ 1 个 `local_runs/GBL_LiM_2plus/job.log` |
| 该 GBL 日志是否为现行行所用 | **不是**——`ready` 行引用的是 `hpc_runs/GBL_LiM_2plus/job.log`（**有**签名）；无签名的那份 `local_runs/` 副本**无任何现行行引用** |

**结论**：下沉到 `import_hpc_opt_numfreq.py` 对**当前campaign 零新增保护**（新计算已在 `qc_task` 被覆盖），
却需改写该文件测试夹具里的合成日志并重验其约 60 个测试，且会新硬拒 1 个**无人引用**的历史本地日志。
⇒ **按「只为会改变结论的事花钱」的口径，本轮不做**。仅当将来**主态腿需要从 HPC 包重新导入**时，
才值得在 `import_hpc_opt_numfreq.py`（紧邻其 `ORCA TERMINATED NORMALLY` / `THE OPTIMIZATION HAS CONVERGED`
断言处）补同等断言——届时仍须先做上表这样的**无翻转证明**。
## 5. 仍未覆盖的范围
- 未验证真实 ORCA 输出格式是否总能解析成功（那需要真实作业；本轮只用合成 ORCA 文本与既有 fixture）。
- 未复核 `import_hpc_numfreq.py` 的 NumFreq 遗留路径是否同样严格；本轮只审 AnFreq 生产路径。
- 未复核聚合器的权重/去重数学（那属 WP3/WP5 面）。

## 6. 「同一个量、三个名字」的口径隐患——已实测澄清并新增守卫（2026-10-25）

起因：核对目标书条目「三个 `LiM_2plus` 的 **charge=2/spin=1**」时，看到包里 `candidate.json` 写 `multiplicity: 2`，
一度以为筛选包算错了自旋态。逐行查证后**结论是：没有错误——同一个物理量在本项目有三个名字，其中两种形式数值差 1**：

| 形式 | 出现处 | 含义 |
|---|---|---|
| `uhf` | `run_batch.XT_PLAN` / `ROUND1_STATES` / `--uhf` 命令行 | **未成对电子数 2S** |
| `multiplicity` | `run_batch.SP_PLAN` / `candidate.json` / 两个登记池的列 | **多重度 2S+1** |
| `$spin` | xtB 输入文件（`job.inp`）里那一行 | **同 `uhf`（2S）** |

**换算在全项目一致**（逐处实测）：`build_torsion_probe_package.py:1048` `spin = identity["multiplicity"] - 1`
（该行在 `build_p4_screening_files` 内，`:1049` 写出 `$chrg/$spin`）；`run_strict_recovery_search.py:189`
`--uhf str(mult - 1)`；`run_second_search_emc.py:85` 同；`run_batch.py:183` 由**名为 `uhf` 的列**喂 `--uhf`；
`build_wp2_sampling.py:236-267` 循环变量即 `uhf`、写表时 `"multiplicity": str(uhf + 1)`。

**实测（P4 包 8 个任务）**：`M_plus` 全部 `job.inp: $chrg 1 / $spin 1` ＋ `candidate.json: multiplicity 2`；
三个 `LiM_2plus` 全部 `$chrg 2 / $spin 1` ＋ `multiplicity 2` ⇒ **标签与输入自洽**；
目标书的「charge=2/spin=1」指的正是 **`$spin` 关键字值（UHF）**。池表亦然（`sampling_conformer_set` 的
`M_plus` 记 mult=2、`li_motif_screen` 的 `LiM_2plus` 记 mult=2，均 = uhf+1）。

**唯一真隐患是命名而非数值**：`build_wp2_sampling.run_xtb(directory, block, charge, multiplicity, do_opt)`
的**形参叫 `multiplicity` 却收 `uhf`**（调用点与写表都对，故不产生错误结果），读者极易混。

**新增两道守卫**（`tests/test_build_torsion_probe_package.py`）：
① 结构：用 AST 断言 `spin = identity["multiplicity"] - 1` 仍留在 `build_p4_screening_files` 内（防改名/搬移后静默丢失）；
② 真实数据：对包里**每个**任务断言 `$chrg == candidate.json.charge` 且 `candidate.json.multiplicity == $spin + 1`。
**RED 实证**：把该行改成 `spin = identity["multiplicity"]`（不 −1）⇒ pytest **exit 1**；随后按字节还原。

**事故与整改（如实记录）**：做 RED 时我**直接改了生产脚本**、又用 Python `Path.write_text` 还原——
Windows 默认换行翻译把 **CRLF 写进工作树**，使该文件 sha256 从冻结的 `5eb615da…` 变成 `8fec1fa…`
（`.gitattributes` 要求 LF）。已改为**用 git blob 的精确字节还原**（`write_bytes`）：CRLF=0、
sha256 回到 `5eb615da609b9c59d4edb35ec5ae3089df53e225264aef246ef8ce53be98668f`、`git status` 干净，
且 `--check-p4-screening` 与 293 项审计复跑全绿。
**整改后的做法**：RED 实证只改**副本或 monkeypatch**，绝不碰生产文件；还原文件一律 `write_bytes`/`git checkout`。