# 新版本成员消费者入口 + 严格闸门是否真读 WP6/扩池证据（t5 · 只读核验）

核验者：ledger-verifier（只读沙箱会话，durable `triage-auditor`）。日期：2026-10-25。
**只读核验**：未改任何仓库文件（除本目录）、未 git 操作、未调用超算、未跑 pytest、未运行任何会写 `outputs/**` 的生成器。
按 STAGE 逐段落盘：每完成一段即写入本文件（崩溃只损失最后一段）。

## 0. 所读输入的 sha256（绑定快照）

| 输入 | 行数 | bytes | sha256 |
|---|---|---|---|
| `scripts/wp_production/import_ensemble_structures.py` | 2425 | 123747 | `EC41475A2FF7769AAE82C5921086624A430AEA3C3B2A01CEF5FA4EFF36213AEA` |
| `scripts/wp_production/build_coverage_reviews.py` | 473 | 21525 | `387D26B792EA62F0CD86839A9006879FD55CF2681B6D3DEB20D41E485D69050D` |
| `scripts/wp_production/build_production_ensemble_aggregator.py` | 1097 | 52398 | `7F6DD47F5583DFAF7B1D3B34D034E0F1671E88A4BF37F667F7380693CB964B49` |
| `scripts/wp_production/strict_readiness_wiring.py` | 563 | 25292 | `52A6D4B3A745B43425ABB8F9EC9D82D3C099DC3FA3C14831E6F3E209CA6182E7` |
| `scripts/wp_production/strict_readiness.py` | 64 | 2876 | `CF9CF464CC4500943E6E2F26FDD9987A0DA1428BCEE8FFAE66564C4BC28E11A8` |

---

## STAGE1｜导入器入口（新版本成员如何进系综结构表）

**主张（计划）**：新版本成员（同 `member_key`、版本号更高）应能经 `import_ensemble_structures.py` 进入 `production_ensemble_structures.csv`，且三类负向（缺输入哈希 / 错误电子身份 / 重复极小）应被拒。

### 1.1 入口与写表点

| 结论 | 证据（file:line） |
|---|---|
| 系综结构表本体，本脚本是唯一写者 | `import_ensemble_structures.py:148` `OUT = outputs/physics_completion/ensembles/production_ensemble_structures.csv` |
| 成员→结构表的**收集循环** | `:2256-2304`（`extra_rows`；`:2257` 遍历 `iter_packages()`；`:2277` `resolve_member_identity(...)`；`:2302` `qc_task(...)`；`:2303` `resolve_member_attempt(...)` 写 `attempt`） |
| **写表** | `:2339-2344`（`rows = primary_rows() + extra_rows`；`:2341-2343` 写 `OUT`） |
| 派生侧账（预算/处置） | `:2346-2414` → `production_ensemble_dispositions.csv` |

### 1.2 新版本成员如何被识别为「更高版本」

| 机制 | 证据（file:line） | 实测语义 |
|---|---|---|
| 包名→尝试号映射 | `:1379-1412` `pkg_attempt(name)` | `_reopt_v<N>` → **10+N-1**（新世系基线抬到 10，保证「最大 attempt 胜出」=最新世系胜出，`:1381-1387` 注释）；`_fragmentfix_<date>` → **5**（`:1392-1394`，修复件须排在它所修复的世系之后）；`torsion_probe_v<N>_realfragment` → **2**（`:1388-1389`）；`_reopt<N>`/`_continuation<N>`/`_cont<N>` → N；其余救援 → 1；基础批 → 0 |
| 成员级世系优先于包级序号 | `:1415-1427` `resolve_member_attempt` | 有 `member_attempt` 时要求 `attempt == source_attempt + 1`，否则 **raise ValueError('inconsistent per-member attempt lineage')** |
| 老版本行不被静默丢弃 | `:2315-2337` | 同 `member_key` 多行按 `attempt` 排序；**只有真正跑过（有 `log_sha256`）且获批的更新尝试**才把旧行标 `superseded` 并写 `superseded_by_attempt=<N>` |

**关键负向（正是计划担心的「算完才发现没有入口」的反面）**：`:2325-2331` 明写——**planned/pending 的更新行绝不能降级已完成证据**：`with_evidence = [r for r in member_rows if r.get("log_sha256")]`，`if len(with_evidence) < 2: continue`。即最新一版若没真跑过，旧行的 `technical_complete_qc_failed` 保持原状。
→ 对应测试：`tests/test_supersede_requires_evidence.py::test_source_requires_evidence_for_supersede`(:30)、`::test_completed_failures_keep_their_status_in_the_live_table`(:37)。

### 1.3 三类负向（缺输入哈希 / 错误电子身份 / 重复极小）

**(a) 缺输入哈希 —— 有实现，负向能力在代码层齐全**

| 判定点 | 证据（file:line） | 触发的记录 |
|---|---|---|
| 输入/几何文件缺失 | `:810-812` | `status=failed`、`qc_flags="missing_input_or_geometry"` |
| `inputs.sha256` **缺失** | `:818-826`（`else: flags.append("inputs_sha256_missing")`，:826） | 落 `qc_flags` |
| `inputs.sha256` **不匹配** | `:819-824`（`input_sha_mismatch`，:824） | 落 `qc_flags` |
| 快照与登记输入不一致 | `:845-857`（`verify_receipt` 比对 `receipt['hashes']`，:852-853） | `status=technical_complete_qc_failed`、`failure_class="snapshot_integrity"` |

**测试覆盖（如实标注）**：`snapshot_integrity` 分支有测试——`tests/test_import_ensemble_structures.py:905` 断言 `pre_submission_rejections[0]["reason"] == "snapshot_integrity"`（相邻用例 `::test_round2_technical_retry_refuses_a_tampered_start_geometry`(:896)）。但**我未找到按名断言 `inputs_sha256_missing` 或 `input_sha_mismatch` 这两个 flags 的测试**（全仓 `tests/*.py` grep 无命中）⇒ 该两分支属**有实现、无专项测试**。

**(b) 错误电子身份 —— 有实现、有专项测试**

| 判定点 | 证据（file:line） | 触发的记录 |
|---|---|---|
| 与候选登记的 charge/multiplicity 比对 | `:837-840`（`RE_XYZFILE` 未命中或不等于 `cand["charge"]/cand["multiplicity"]` → `charge_mult_mismatch`） | 落 `qc_flags` |
| **身份完全无法声明**（无 manifest/registry/ledger 三源） | `:1318-1360` `resolve_member_identity` → `"member_identity_unknown"`（:1357）；角色缺失 → `"member_role_undeclared"`（:1359） | 调用端 `:2279-2294` **记一行** `status="failed"、qc_flags=reason、source_kind="rejected_identity"`，并打印 `REJECTED <reason>`；不静默跳过（`:1328-1330` 注释：「a silently skipped leg is a ledger lie」） |
| 身份漂移（键图改变） | `:748` `_cand_identity`；在 `:778-784` 用 `manifest.connectivity_signature(...)` 与 `bond_graph(...)` **双向比对候选 vs 最终几何**（`bond_graph` 定义 `:186`）；调用点 `:924`、`:1004` | 落 `qc_flags`（该函数同时负责 A 项） |
| 重启帧身份漂移（构建端拒收，非导入端） | `:1915-1916`、`:1936`、`:1949-1950` | `rejected.append({"reason": "restart_species_drift"})` |

**测试**：`tests/test_recovery_identity_wiring.py::test_missing_identity_everywhere_is_refused`(:126)、`::test_no_declared_role_is_refused_not_defaulted`(:94)；`tests/test_import_ensemble_structures.py::test_charge_mult_mismatch_is_rejected`(:239)、`::test_candidate_bond_graph_change_rejects_the_leg`(:161)。

**(c) 重复极小 —— 导入器只挡「重复提交」，不挡「重复极小」**

| 判定点 | 证据（file:line） | 语义 |
|---|---|---|
| 已提交未回收的救援包**继续拥有**成员，禁止再建同成员包 | `:1430-1481` `members_in_flight` | 「提交两次等同一次算力双计」——注释 `:1433-1435` |
| 未提交的救援计划不得顶掉最后一次真实 QC 结果 | `:1484-…` `rescue_package_is_active`（判据是 `submission_journal.json`，**不是** `submission.json`；`:1487-1490`） | 先前只看 `submission.json` 导致已提交包被误判 inactive |
| 预算按**去重后的 (attempt, log_sha256) 对**计数 | `:2364`、`:2370` 注释「budget counts DISTINCT (attempt, log) pairs so a duplicate submission can never double-charge a lineage」 | 成本/预算侧防重复计费 |

**测试**：`tests/test_import_ensemble_structures.py::test_submitted_rescue_package_blocks_a_duplicate_rebuild`(:465)、`tests/test_package_active_journal.py`（journal vs submission.json）、`tests/test_cost_dedup_invariants.py`。
**但**：**「几何上是同一极小」的去重不在本脚本**——`import_ensemble_structures.py` 只写结构表，不做原子映射/极小等价判定；该职责在聚合器 `dedup_members`（见 STAGE3）。⇒ 若「重复极小」指几何等价，**导入器无此入口**，须由 STAGE3 承担。

### 1.4 STAGE1 判定

**成立（有入口、且负向能力在代码层齐全）**，附三条**覆盖缺口**（有实现无专项测试）：
1. `inputs_sha256_missing` / `input_sha_mismatch` 两个 flags 无按名测试（仅 `snapshot_integrity` 有）。
2. 几何等价的「重复极小」不在导入器职责内，须看 STAGE3。
3. `resolve_member_attempt` 的 `ValueError` 有测试（`tests/test_ensemble_hpc_safety.py:14-19`），但**新版本 `_reopt_v<N>` 抬到基线 10** 的语义测试我仅在 `tests/test_recovery_attempt_numbering.py:26-45`（v1/cont/reopt 族）与 `tests/test_fragmentfix_lineage.py`（fragmentfix/realfragment）见到；**`_reopt_v2` 的 base-10 分支未见到按名用例**（`pkg_attempt` 中 `:1395-1397`）。

---

## STAGE2｜覆盖复核入口（`build_coverage_reviews.py`，473 行）

**主张（计划）**：`coverage_route()` 的四条分支（新盆地 / 回已知盆地 / 身份漂移 / 八条均无）各有明确输入；「源证据变更会使旧 `resolved` 失效」应有承担者。

### 2.1 实测：`coverage_route()` 的**实际**分支是 **7 条**（不是 4 条）

`coverage_route(latest_members, novelty, *, min_unique_after, registered_starts, search_outcome, production_evidence)`——定义 `:163-165`。逐分支（含所需输入与判定）：

| # | 返回 route | 触发条件（file:line） | 需要什么输入 | 下游 verdict |
|---|---|---|---|---|
| 1 | `pending` | 任一 `latest_member.status ∈ {pending, ready}`（:172-173）；或 `latest_members` 为空且 `search_outcome != "no_new_minimum_found"`（:190-191） | 成员状态；`search_outcome` | `pending`（:364-366） |
| 2 | `search_exhausted` | **无成员通过 QC** 且 `latest_members` **为空** 且 `search_outcome == "no_new_minimum_found"`（:177-185） | `latest_members` 是否空 + `search_outcome` | `search_exhausted`（:367-369） |
| 3 | `unresolved_qc` | `latest_members` 非空但**无一条 `status=="computed"`**（:175-176、:186-189） | 成员状态 | `unresolved`（:370-372） |
| 4 | `dedup_evidence_required` | ≥1 `computed` 且任一 `novelty == "unresolved"`（:193-197） | `novelty` 映射（见下） | `unresolved`（:370-372） |
| 5 | `multi_basin_coverage` | 全部 computed 的 novelty 已定，且（`min_unique_after >= 2` 且有 `"new"`）（:199-202）**或**存在 `"new"`（:204-206） | `novelty`、`min_unique_after` | **`resolved`**（:358-360） |
| 6 | `known_basin_reproduction` | 全部 computed 都归并到已知极小，且（`production_evidence` 为假 :209-214 **或** `_search_scope_documented(...)` 为假 :215-218） | `production_evidence`、`search_outcome`、`registered_starts` | `unresolved`（:361-363） |
| 7 | `single_basin_verified` | 复现单一已知极小 **且** `production_evidence` 为真 **且** `_search_scope_documented(...)` 为真（:220-223） | 同上 | **`resolved`**（:358-360） |

- `novelty` 来源（:316-331）：`member_key` 是否出现在 Boltzmann 权重表（`production_ensemble_weights.csv`）→ `"new"`，否则 `"known"`；再由 `production_ensemble_dedup.csv` 的 `duplicate_of` 覆盖为 `"known"`。
- `production_evidence` 定义（:333-338）：**每个** computed 成员的 `imaginary_modes`、`final_geometry_sha256`、`log_sha256` 三项**均非空**。
- `_search_scope_documented`（:150-160）：`registered_starts` 非空 **且** `search_outcome ∈ {new_minima_found, no_new_minimum_found, unused_pool_basin_no_search_needed}`。
- **另有一处 `coverage_route` 之外的覆盖入口**（C-group 裁决）：`:344-349`——若加权合格成员 `len(qualified_all) >= 2` 且无 pending，直接判 `multi_basin_coverage`，**绕过 `coverage_route`**（注释明写「coverage over ALL qualified members, not only the recovery batch」）。

**与简报 4 标签的差异（如实指出）**：我**无法**把简报的「新盆地 / 回已知盆地 / 身份漂移 / 八条均无」逐一对上代码——代码里**没有**名为「身份漂移」的 route。身份漂移在本模块是**上游排除**而非 route：`_rejected_probe_members()`（:106-148）把「被拒候选」与「被取消数组的成员」从成员集合中剔除（`:260-268` 参与 `members` 过滤），使它们不再读作 in-flight。简报「八条均无」我也未在代码中见到对应命名。⇒ **简报的分支清单与实现不一致，应以代码的 7 条 route 为准。**

### 2.2 「源证据变更使旧 `resolved` 失效」由谁承担

| 环节 | 证据（file:line） | 实测语义 |
|---|---|---|
| 本模块**复用**旧行 | `:311-314`：`label_cov = labels[key].get("coverage_status","")`；`if label_cov == "resolved_by_review" and key in prior: rows.append(dict(prior[key])); continue` | 只要 **labels 的 `coverage_status` 仍写 `resolved_by_review`**，本模块**原样复用** prior 行，**不看任何源证据哈希** |
| 失效信号来自**标签生产者** | `:303-310` 注释：「The label itself is recomputed from the ledger every pass, so a genuine retraction (the coverage_status no longer says resolved_by_review) still flips this row back to the derived route」 | ⇒ **承担者是 `production_ensemble_labels.csv` 的生产者**，即 `build_production_ensemble_aggregator.py`（STAGE3）；本模块只**消费**该信号 |
| 本模块**有**输入哈希记录 | `:428-435`：`coverage_reviews_index.json` 的 `inputs` = `{LABELS, STRUCT, DISPOS, WEIGHTS, MANIFEST}` 各自 sha256 | 但只记录**本次**输入哈希，**不与上一次 review 的哈希比对** |
| `--check` 只做**同输入**重算比对 | `:446-457`：`build_rows()` 重算后与磁盘**逐字节**比较 | 不触发任何 invalidation；输入变了就 CHECK FAILED，但不会自动撤销旧 `resolved` |

**判定**：本模块**无**「源证据变更 → 撤销旧 resolved」的实现（是否随 labels 撤回，取决于聚合器是否把 `coverage_status` 从 `resolved_by_review` 改掉）。**归属明确**：由 `build_production_ensemble_aggregator.py` 承担（见 STAGE3）。**无专项测试**——`tests/test_strict_recovery_coverage.py` 有 `test_historical_failures_are_not_rewritten`(:219)、`test_no_state_leaves_limited_without_a_resolved_review`(:173)、`test_search_exhausted_is_never_treated_as_resolved`(:149)、`test_a_state_is_resolved_only_with_a_computed_kept_member`(:93)、`test_clearing_n_limited_alone_cannot_upgrade`(:198)、`test_review_must_name_members_present_in_the_kept_pool`(:211)，**但没有**按名断言「源证据哈希变化后旧 resolved 必须失效」的用例。

### 2.3 一处**有实测价值的负向守卫**（附带发现）

`_rejected_probe_members()` `:120-129`：若 `work/hpc_torsion_probe_v*/manifest.json` 一个都找不到，**直接 `raise SystemExit`** 并打印「REFUSING to derive probe exclusions … an empty exclusion set here would silently re-admit refused or cancelled members」。即「无法读取拒收记录」**不会**静默退化成「没有拒收」——这是 fail-closed 的。
**交叉印证（与我 t4 复核一致）**：该函数**依赖** `manifest.json` 的 `rejected` 数组（EC 两条腿）与 `replaces_cancelled_job`+`requested_tasks`（3747724），说明这些**是功能性排除输入**，进一步说明 `submission_journal.attempt0_refused_no_sbatch.json` **不是**系统里唯一的拒收记录。

### 2.4 STAGE2 判定

**成立（入口存在、输入明确、且有一条 fail-closed 守卫）**，附三条**不符/缺口**：
1. **分支清单不符**：简报的 4 标签 ≠ 实现的 7 条 route；「身份漂移」「八条均无」在 `coverage_route` 中不存在（身份漂移是上游排除）。
2. **invalidation 无本模块实现、无专项测试**：本模块对仍标 `resolved_by_review` 的状态**原样复用旧行**、不校验源证据哈希；撤销责任在聚合器。
3. 本模块的 `--check` 只保证「同输入可复算」，**不保证**「旧 resolved 在新证据下仍成立」。

**第三方佐证（我未参与该测试的编写）**：`tests/test_resolved_route_evidence.py::test_the_coverage_route_vocabulary_is_frozen_and_mapping_complete`(:96) 的 docstring 独立记有「**of the seven routes `coverage_route()` can return, three — `known_basin_reproduction`（the plan's "returned to a known basin" branch）, `pending` and `dedup_evidence_required` — appear in NO test file AND in NO row of `coverage_reviews.csv`**」。这与我的 7 条 route 计数、以及「简报的 4 标签对不上代码」一致，并把「回已知盆地」正式映射到 `known_basin_reproduction`。

---

## STAGE3｜聚合器入口（`build_production_ensemble_aggregator.py`，1097 行）

**主张（计划）**：新版本成员须能进 `kept` 并影响 `acceptance_status`；「同盆地复现只增覆盖证据、不增简并度」与「重复极小不得蒙混」各有代码保证。

### 3.1 新版本成员如何进 `kept`

| 环节 | 证据（file:line） | 实测语义 |
|---|---|---|
| 去重函数（唯一入池通道） | `:432-550` `dedup_members(members, repo, pair_sink)`；调用点 `:863` `kept, decisions = dedup_members(pool, REPO, pair_rows)` | 全成员集（含 primary）真几何去重 |
| 代表元规则 | `:437`、`:454-457` `order = sorted(..., key=(g_single_eh, member_key))` | **代表 = 最低 G**，同 G 以 `member_key` 稳定破平（可复现） |
| 入池的**闸门次序** | `:435-436` 注释 + 实现：① 碎片组成/键签名 → ② Li 供体身份/齿合 → ③ 重原子 Kabsch RMSD → ④ 扭转 | `:475-485` 拓扑映射（穷尽搜索）；`:495` `rmsd >= DUP_RMSD_A` 丢弃；`:497-499` 扭转 `tdelta > TORSION_TOL_DEG` 丢弃；`:500-503` Li 供体集合身份；`:504-509` 只允许 proper rotation（拒镜像）+ 手性匹配 |
| 落 `kept` / 落 duplicate | `:548-549` `if not duplicate_of and not why.startswith("mapping_unresolved"): kept.append(i)`；`:544` `"kept": "false" if duplicate_of or why.startswith("mapping_unresolved") else "true"` | 只有「非重复**且**映射已穷尽判定」才入池 |
| 拒收语义（关键负向） | `:528-531`：映射搜索预算耗尽 → `why="mapping_unresolved: mapping search exhausted budget"`、`verdict='mapping_unresolved'` | **不得静默当作 unique**（`:544` 同时把该行 `kept=false`） |
| 缺几何 | `:438-439`、`:460-467`：`reason="dedup_blocked: no final geometry"` | 同样不入池（非「唯一」） |

### 3.2 进 `kept` 如何影响 `acceptance_status`

| 影响面 | 证据（file:line） |
|---|---|
| 成员/简并度计数全部取自 `kept` | `:887`、`:957` `n_unique = len(kept)`；`:959` `n_members = len(kept)`；`:960` `pool_limited = "true" if len(kept) < 2 else "false"` |
| Boltzmann 权重与下界只由 `kept` 生成 | `:900` `g_ens, weights, q_total = boltzmann(g_vals, temps[0])`；`:902` `for m, w, g in zip(kept, weights, g_vals)`；`:968` `lowering_bound_rt_ln_n_kcal = R_KCAL * T * log(len(kept))` |
| **`coverage_status` 信号**（STAGE2 依赖它） | `:969` `"coverage_status": ("resolved_by_review" if cov_resolved …)` |
| 验收判定 + **反作弊入参** | `:923-925` `acceptance_decision(..., kept_keys={m["member_key"] for m in kept})`；判定体 `:619-657`：`:644` 需 `cov.verdict=="resolved"` 且无 unresolved；`:649-651` `claimed` = `computed_new_members` 或 `kept_pool_evidence` 拆 `;`，**`cov_resolved = bool(claimed) and all(c in kept_keys for c in claimed)`**；`:653-657` unresolved→`provisional`；`n_limited and not cov_resolved`→`limited`；否则 `accepted` |

### 3.3 「同盆地复现只增覆盖证据、不增简并度」由谁保证

| 保证点 | 证据（file:line） |
|---|---|
| 复现行被打 `duplicate_of` 且 `kept=false`，**不进 `kept`** | `:514-516`、`:544`、`:548` |
| ⇒ 不计入 `n_unique` / `n_members` / Boltzmann / `Rt·ln N` | 上表 3.2 三行（全部以 `len(kept)` 为源） |
| 复现的「证据价值」走**另一列**：评审的 `kept_pool_evidence` = 被复现的 dedup 目标 | `build_coverage_reviews.py:380-386`（`kept_evidence = duplicate_of 集合`）；聚合器 `:633-637` docstring 明确「single_basin_verified 的 claimed members 正是被 dedup 排除的那些行；核查落在 `kept_pool_evidence`，即它们所复现的 dedup 目标」 |
| 被取代的旧尝试**不得二次计权** | `:686-702` `latest_attempt_per_member`（「superseded evidence never contributes a second weight」，仅取每 member 最高 `attempt`） |
| 非单位简并被拒 | `:411-…` `boltzmann(...)` 的 `degeneracies` 路径 + 测试 `tests/test_build_production_ensemble_aggregator.py::test_nonunit_degeneracy_is_rejected_under_the_frozen_rule`(:70)、`::test_identical_members_get_rt_ln2_gain_not_more`(:59) |

### 3.4 「重复极小不得蒙混」由谁保证

| 保证点 | 证据（file:line） |
|---|---|
| 拓扑映射必须存在且**已穷尽**；预算耗尽 → `mapping_unresolved`（不当 unique） | `:475-485`、`:528-531`、`:544` |
| RMSD **且** 扭转**且** Li 供体身份**同时**满足才算重复 | `:495-503` |
| 镜像拟合不得算作旋转重复 | `:504-507`（`reflection_preferred`）、测试 `::test_mirror_image_is_not_a_rotation_duplicate`(:479) |
| 验收反作弊：评审声称的成员**必须真在 kept 池**，否则不能升级 `accepted` | `:649-651`；测试 `tests/test_acceptance_decision.py::test_review_naming_a_member_absent_from_the_pool_cannot_upgrade`(:66)、`::test_review_with_no_claimed_members_cannot_upgrade`(:75) |
| 处置表**重复 member_key 直接 raise** | `:677-683` `load_dispositions`：`if len({member_key}) != len(rows): raise ValueError('duplicate member disposition')` |

### 3.5 STAGE3 判定

**成立**（新版本成员有明确入池通道与影响面，两条不变式各有代码 + 命名测试）。测试点名：`tests/test_acceptance_decision.py`（8 例，含三条「不能升级」负向）、`tests/test_resolved_route_evidence.py`(:33,:96)、`tests/test_build_production_ensemble_aggregator.py`(:450,:465,:479,:490,:524,:59,:70,:276)。
仅两点提示：① `dedup_members` 的**代表元是「最低 G」**，而筛选层（t1 交付的判定器）刻意不做「按 G 排代表」——两层的代表元规则不同，跨层比对时须注明；② 入池判定依赖 `find_topology_mappings` 的**搜索预算**，`mapping_unresolved` 是 fail-closed（不入池），但会让状态停在 `limited`——这与「重复极小不得蒙混」取向一致，代价是可能少收一个真极小。

---

## STAGE4｜严格闸门是否**真读** WP6 / 扩池完成证据

**主张（计划）**：闸门应实际读取 WP6（`wp6_*`）与扩池（`wp5_pool_extension` / `extension_pool`）的**完成证据**；若只是常量/占位，须点名 file:line 并给出该键当前值。

### 4.1 结论先行：**真读，且是派生三态，不是常量**

| 问题 | 实测答案 | 证据（file:line） |
|---|---|---|
| 闸门是否真读 WP6 完成证据？ | **是**——`derive_wp6_trigger(labels, frozen_molecules, complete_li_pairs)` 从**标签 CSV + 冻结分子集 + 完成的 Li 对**推导 `triggered / not_triggered / unknown`；门槛 = **全部 48 态 accepted 且 Li 对 ≥9/12** | `strict_readiness_wiring.py:461-489`；常量 `WP6_REQUIRED_LI_PAIRS = 9` 于 `:83`；触发条件 `:487` |
| 闸门是否真读扩池完成证据？ | **是**——`derive_pool_extension_trigger(wp5_full_pool_ok)` 由 `wp5_full_target_pool_evaluated` 这一项**派生**；该 bool 本身由 `_check_wp5()` 读真实 WP5 组合产物推导 | `:492-502`；`:543` `pool_state = derive_pool_extension_trigger(checks.get("wp5_full_target_pool_evaluated"))` |
| 是否只是常量/占位？ | **否**（旧版硬编码已移除，且有回归守卫） | `tests/test_plan_compliance_strict_gate.py:70-71` 断言源码**不含** `checks["wp6_triggered"] = False` / `checks["pool_extension_triggered"] = False`；`:72-73` 断言两个 `derive_*` 函数存在 |
| 六个必需检查各自读自己的产物 | `CHECKS` 映射 6 项 → 6 个检查函数（含 `wp5_full_target_pool_evaluated → _check_wp5`） | `strict_readiness_wiring.py:447-454` |
| 缺产物/读不动 → **fail closed** | `derive_check_details()`：文件不存在 → `_result(False, ["artifact missing"])`；任何 `OSError/UnicodeDecodeError/csv.Error/KeyError/TypeError/ValueError` → `passed=False` | `:515-528`（注释 `# fail closed` :524） |
| 三态触发器：`unknown` **阻断**闸门 | `strict_readiness.py:52-62`：`state == "unknown"` → `reasons.append(gate + "_trigger_unknown")`；`triggered` 且 `_complete is not True` → `gate + "_incomplete"` | `strict_readiness.py:54-62` |
| 缺档的必需检查阻断 | `:48-50` `for k in REQUIRED_CHECKS: if checks.get(k) is not True: reasons.append(k)` | `strict_readiness.py:21-28`（`wp5_full_target_pool_evaluated` **在必需清单内**） |
| 组合口径（README） | `_strict_gate_snapshot()`：动态 `exec_module` 两个模块 → `derive_checks()` → 读 `production_ensemble_labels.csv` → `strict_readiness(...)`；异常 → `"**无法判定**"`（**绝不默认通过**） | `scripts/build_github_readme.py:718-740`（`# fail-closed: never read as pass` :739） |

### 4.2 键名映射与**当前实测值**

| 计划里的键 | 代码里的键（file:line） | **当前值** |
|---|---|---|
| `wp6_*` | `wp6_trigger_state` / `wp6_triggered`（`wiring:545,548`）；合规表 `wp6_explicit_ligand`（`build_plan_compliance.py:832-838`） | `plan_compliance.csv`：`status=blocked_on_production`；`measured=plan_rows=4 executed_jobs=0 **li_pair_complete=12/12** required_li_pairs=9 production_ensembles=44/48 gate_ready=false **trigger_state=not_triggered** scope=optional` |
| `wp5_pool_extension` | `pool_extension_trigger_state` / `pool_extension_triggered`（`wiring:546,549`）；合规表行 `wp5_pool_extension`（`build_plan_compliance.py:797-806`） | `status=not_satisfied`；`measured=**extension_rows=0**; replay_pool=legacy_pool_not_blind` |
| `extension_pool` | 代码里**无**该字面量；等价物 = `derive_pool_extension_trigger` 的输入 `wp5_full_target_pool_evaluated` + 合规表按 `cohort == "extension"` 计数 | 截至本快照 **0 行**（`extension_rows=0`） |

> 键值来源与快照：`outputs/physics_completion/compliance/plan_compliance.csv` sha256 `A1F70503E766121E748A1BF15C05AE458021413D998C5523E4B7BF96AB708423`（42 行）。我**未运行**任何生成器，故这些是**磁盘现状**，不是本次重算值。

### 4.3 「完成证据」的真实性抽查：扩池行读的是真数据

`build_plan_compliance.py:797-806`：`ext_rows = [r for r in cfg_set if r.get("cohort") == "extension" and r.get("mol_id")]`，status = `"partial" if len(ext_rows) >= 8 else "not_satisfied"`，证据列点名 `data/metadata/physics_completion_set.csv`。⇒ 是**按行计数**，非常量。当前 `extension_rows=0` ⇒ `not_satisfied`（与计划的「首轮没有扩样」一致）。

### 4.4 负向测试（点名）

| 测试 | file:line |
|---|---|
| `test_wp6_trigger_is_unknown_without_li_pair_evidence` | `tests/test_strict_readiness_strict.py:187` |
| `test_wp6_trigger_fires_only_with_both_preconditions` | `…:192` |
| `test_wp6_trigger_unknown_on_broken_input` | `…:206` |
| **`test_triggers_are_derived_not_constants`** | `…:219` |
| **`test_unknown_trigger_blocks_the_gate`** | `…:228` |
| `test_wp5_subset_pool_is_not_the_full_cohort`（子集池 ≠ 全队列，必须不过） | `…:126` |
| `test_bad_evidence_must_not_pass` / `test_cost_missing_must_not_become_zero` | `…:72` / `…:149` |
| `test_trigger_booleans_are_derived_in_the_wiring` / `test_wp6_item_reports_a_derived_trigger_state` | `tests/test_plan_compliance_strict_gate.py:68` / `:76` |

### 4.5 一处**口径警示**（非缺陷判定，需 Lead 确认）

合规表的 `li_pair_complete` **不是**从冻结标签算的——它在 `build_plan_compliance.py:164-174` `strict_main_counts(main_ids, accepted_legs)` 里由 `accepted_legs` 计数，而 `accepted_legs` 来自 `wp2_progress.build_snapshot(REPO)`（`:205`、`:318-320`），后者读的是**逐腿运行 JSON** `work/wp2prod/<name>/<state>/<name>_<state>.json` 并经 `_strict()`（`wp2_progress.py:36-39`：`computed` + `terminated=true` + `opt_converged=true` + `imaginary_modes=0`）。

⇒ 与 `production_ensemble_labels.csv` 的 `acceptance_status`（44 accepted / 4 limited）**不是同一证据源**：前者是**逐腿 QC**，后者是**系综验收**。因此 `li_pair_complete=12/12` 与闸门 2 的 A 11/12、B 9/12（池完整性）**不可直接互相印证**，也**不能**据此说某一方错。**我未读 `work/wp2prod/**` 的逐腿 JSON**，故不判定 `12/12` 是否合理——若 Lead 需要，这是下一步可复核点（读 4 个受限态的逐腿 JSON，看 `_strict` 为何通过）。

### 4.6 STAGE4 判定

**成立**：闸门**实际读取** WP6 与扩池的完成证据（源自真实产物、派生三态、fail-closed、有 7 个命名负向测试 + 2 个回归守卫），**不存在**把常量/占位当完成证据的情况。唯一附注是 4.5 的口径警示（跨模块两套「Li 对完整」定义）。

---

## 总结行

**17 项检查，14 成立，1 不符，2 部分成立（缺口已逐条列出）。**

| # | 检查 | 判定 |
|---|---|---|
| 1 | STAGE1 导入器入口存在、新版本成员有入池通道（写表点 :2339-2344） | 成立 |
| 2 | STAGE1 老版本行不被 planned/pending 更新行降级（:2325-2331） | 成立（+测试） |
| 3 | STAGE1 错误电子身份被拒（`charge_mult_mismatch`、三源身份缺失 → 记行拒收） | 成立（+测试） |
| 4 | STAGE1 重复提交被挡（`members_in_flight`、`rescue_package_is_active`、DISTINCT (attempt,log)） | 成立（+测试） |
| 5 | STAGE1 **缺输入哈希**被拒（`inputs_sha256_missing` / `input_sha_mismatch`） | **部分成立**：有实现，**无按名专项测试** |
| 6 | STAGE1 几何等价「重复极小」在导入器有入口 | **部分成立**：不在导入器职责，属 STAGE3 |
| 7 | STAGE2 `coverage_route()` 分支与各自输入明确 | 成立（7 条 route 已逐条列出） |
| 8 | STAGE2 简报「4 分支（新盆地/回已知盆地/身份漂移/八条均无）」与实现一致 | **不符**（代码 7 条 route；「身份漂移」是上游排除、非 route；「八条均无」无对应命名） |
| 9 | STAGE2 「源证据变更使旧 resolved 失效」有承担者 | **部分成立**：本模块**无**实现（:311-314 原样复用旧行），归属聚合器；**无专项测试** |
| 10 | STAGE2 有一条 fail-closed 守卫（`_rejected_probe_members` 缺 manifest 即 `SystemExit`） | 成立 |
| 11 | STAGE3 新版本成员进 `kept` 的闸门次序 + 代表元规则 | 成立 |
| 12 | STAGE3 `kept` → `acceptance_status` 影响面（含 `kept_keys` 反作弊） | 成立 |
| 13 | STAGE3 「同盆地复现只增覆盖证据、不增简并度」 | 成立（+测试） |
| 14 | STAGE3 「重复极小不得蒙混」 | 成立（+测试） |
| 15 | STAGE4 闸门**真读** WP6 完成证据（派生三态、非常量） | 成立（+5 负向测试） |
| 16 | STAGE4 闸门**真读**扩池完成证据（`wp5_full_target_pool_evaluated` 派生 + 合规表 extension 行读实数据） | 成立（+2 回归守卫） |
| 17 | STAGE4 缺产物/读不动/`unknown` 均 fail-closed | 成立（+`test_unknown_trigger_blocks_the_gate`） |

### 未能覆盖 / 需 Lead 决定
1. **未运行任何生成器、未跑 pytest**（含只读 `--check` 亦未跑）⇒ 所有结论均为**源码与磁盘产物**的静态核验，**未**验证运行时行为。
2. **`work/` 机器本地层未入库**（`_rejected_probe_members` 依赖它）⇒ 干净克隆下 `coverage_route` 的相关排除会 `SystemExit`；这是刻意设计，但意味着该路径**不可在 CI 里跑通**，除非 `work/` 层被提供。
3. **4.5 的口径警示**：`li_pair_complete=12/12`（逐腿 QC 源）vs 闸门 2 的池计数（验收源）——需 Lead 决定是否统一口径或加注。
4. STAGE1 的两处**无按名测试**缺口（缺哈希 flags、`_reopt_v2` base-10）建议补测；STAGE2 的「源证据失效」建议落一条负向测试。

---

## 附录：所引用的全部输入 sha256（全值）

```
EC41475A2FF7769AAE82C5921086624A430AEA3C3B2A01CEF5FA4EFF36213AEA  scripts/wp_production/import_ensemble_structures.py
387D26B792EA62F0CD86839A9006879FD55CF2681B6D3DEB20D41E485D69050D  scripts/wp_production/build_coverage_reviews.py
7F6DD47F5583DFAF7B1D3B34D034E0F1671E88A4BF37F667F7380693CB964B49  scripts/wp_production/build_production_ensemble_aggregator.py
52A6D4B3A745B43425ABB8F9EC9D82D3C099DC3FA3C14831E6F3E209CA6182E7  scripts/wp_production/strict_readiness_wiring.py
CF9CF464CC4500943E6E2F26FDD9987A0DA1428BCEE8FFAE66564C4BC28E11A8  scripts/wp_production/strict_readiness.py
47380151377018319A9974ED445196C9E229BCB6D80C484B1C47F7E6F4DB0285  scripts/wp_production/build_plan_compliance.py
16E173184A1174B97748E2564789305048412920AFAC5B2007A2D7E89FF2A4B9  scripts/wp_production/wp2_progress.py
88D0F6A6A9446C63359560A8C846117DFBCB3AA63C7F83464D0A82BFA6AB63CB  scripts/build_github_readme.py
A1F70503E766121E748A1BF15C05AE458021413D998C5523E4B7BF96AB708423  outputs/physics_completion/compliance/plan_compliance.csv
E0C331DA01DD67BE2741F67CAC048E9C7229A1CD9E79EB5FFAFA02BDA7B385BC  tests/test_resolved_route_evidence.py
6BE994479650A184D7406386CB55013611F9BD1DC6EBC74A51A39EAD70273A56  tests/test_acceptance_decision.py
F6AB770A86C1508C8CDA030839C7764E64D8717190630E354142DC344B129587  tests/test_strict_readiness_strict.py
76A0FB19C22096262BA7BFD14B3F6A1C3AC34B727C37670018BCE1A4C0DC41FF  tests/test_plan_compliance_strict_gate.py
```

**产物声明**：本目录**仅有** `REPORT.md` 一个文件；无脚本、无测试、无中间产物。未改任何仓库文件（本文件除外）。