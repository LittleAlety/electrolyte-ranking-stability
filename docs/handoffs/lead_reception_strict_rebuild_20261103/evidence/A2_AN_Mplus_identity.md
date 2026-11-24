# A2 · AN M⁺ 前沿身份材料与单盆地证据（分离核验）

## 0. 元信息与方法红线

| 项 | 内容 |
|---|---|
| 任务 | A2：核验 AN M⁺（`AN|M_plus`）的前沿身份材料、以及单盆地（single-basin）证据，二者**分别给出独立结论** |
| 仓库根 | `E:\Claude Code\电解液溶剂-HB\电解液溶剂HB-Code` |
| 本轮动作 | 只读核验；未修改任何现有文件、未提交作业、未新增计算；本报告是新增文件之一 |
| 输入快照 | 关键文件 mtime：`coverage_recheck.json` / `member_statuses.csv` = 2026-11-03 09:19；`coverage_8.json` / `decisions.csv` = 2026-11-03 09:57；`candidate_sources.json` = 2026-11-03 10:30；`eight_admission_v2/*` = 2026-11-03 11:25；`coverage_reviews.csv` = 2026-11-02 15:45；`production_ensemble_labels.csv` = 2026-11-02 18:36 |
| 红线 1 | **不把任何缺项归因于数值误差**（本报告所有“缺/未找到”均为来源、登记、审查状态，不是数值结论） |
| 红线 2 | **限定来源的“未找到” ≠ 身份失败**；远端状态为 `INACCESSIBLE_NOT_VERIFIED`，不推断远端证据存在或不存在 |
| 红线 3 | 不用数值 QC（五项收敛判据）替代身份 / 覆盖（coverage）结论 |
| 红线 4 | 不提出计算申请；一切补证只以“证据类型 + 最小范围”表述，并显式标注 **不构成计算申请** |

---

## 1. 结论 A2-(a)：前沿身份材料 —— **未闭合**

> **一句话结论（a）：AN M⁺ 唯一严格合格代表 `AN|M_plus|tors_3_0_1_2` 的“独立前沿身份链”在本地限定来源内未找到，身份门保持 `HELD`（未闭合）；该状态是“本地指定来源未找到 + 远端未核”，不判为身份失败，也不归因于数值误差。**

### 1.1 身份门判据（先列判据，再列事实）

| # | 判据 / 原话 | 来源（路径 + 行/键路径） | 文件 SHA256 |
|---|---|---|---|
| J1 | 满足 `frontier 登记 verified` + `frontier_legs.geometry_sha256 == 登记几何哈希` + `sha256_geom_xyz == 登记几何哈希` + `work/hpc_frontier_localization_v1/tasks/<member>/attempt/` 下 `job.inp/geom.xyz/job.log/job.molden.input` 四文件重哈希一致 → `FROZEN_FRONTIER_CHAIN_VERIFIED`；否则 → `IDENTITY_EVIDENCE_NOT_IN_FRONTIER_REGISTER` | `scripts/wp_production/build_48_recovery_decisions.py:199-213` | 源码文件（本轮只读引用） |
| J2 | 仅当 `route == single_basin_verified` **且**该态全部代表均为 `FROZEN_FRONTIER_CHAIN_VERIFIED`，`coverage_gate` 才升级为 `ROUTE_SUPPORTS_CLOSURE_SUBJECT_TO_INDEPENDENT_COVERAGE_AUDIT`，否则保持 `HELD` | `scripts/wp_production/build_48_recovery_decisions.py:214-217` | 同上 |
| J3 | “AN M⁺ tors_3_0_1_2：独立前沿身份链仍缺……本地指定来源检查不能关闭身份门，远端来源尚未核实；本轮不将这一待核项转成必须新算。” | `docs/handoffs/strict_rebuild_20261103/blocker_resolution_20261103/CANDIDATE_SOURCES.md:5` | `64fa07bf8b518b0235abaffe6acd6830a8a32d12a8471276d2f19af391d666f4` |
| J4 | “已读 whu-hpc 技能及命令桥 AGENTS…没有远端文件读取，也没有提交新计算。该状态记为无法访问，不推断远端证据存在或不存在。” | `.../CANDIDATE_SOURCES.md:11` | 同上 |

### 1.2 身份材料核对表（事实层）

| # | 期望的来源 / 材料 | 实测结果 | 来源（路径 + 行/键路径） | SHA256 |
|---|---|---|---|---|
| 1 | 独立前沿任务目录 `work/hpc_frontier_localization_v1/tasks/AN__M_plus__tors_3_0_1_2/` | **不存在**；`frontier_task_exists=false`；该 tasks 目录共 81 项，AN 相关 5 项（`AN__LiM_2plus__primary`、`AN__LiM_plus__c01`、`AN__LiM_plus__primary`、`AN__M__34`、`AN__M_plus__primary`），`grep -i tors` 0 命中 | `docs/handoffs/strict_rebuild_20261103/blocker_resolution_20261103/candidate_sources.json` 键 `an_frontier.frontier_task_exists` / `.an_frontier_task_dirs_present`（文件行 2-14）；`CANDIDATE_SOURCES.md:5`；目录列举本轮实测 | `3bccdb416e2ebaa10c06efe1b787c8adc3fcf89170d3ab4801eabd56d0d6a244`（json） |
| 2 | 前沿身份登记表中该成员行 | `outputs/physics_completion/frontier/frontier_identity_evidence.csv` 全表 81 行（含表头，数据行 80），检索 `tors_3_0_1_2` **0 命中** | `outputs/physics_completion/frontier/frontier_identity_evidence.csv`（表头行 1；`AN|M_plus|primary` 在行 5） | `0f8a8653b5285e0e786e62f1f3c03d021b8edc48502a56e768dba46d7ebcc5c6` |
| 3 | 前沿定位表 / 前沿腿表中该成员行 | `frontier_localization.csv`（81 行，含表头，数据行 80）与 `frontier_legs.csv`（81 行，含表头，数据行 80）检索 `tors_3_0_1_2` **0 命中**；AN M⁺ 两表均只有 `AN|M_plus|primary`（行 5） | `outputs/physics_completion/frontier/frontier_localization.csv:5`；`outputs/physics_completion/frontier/frontier_legs.csv:5` | `7310354c98ff2962226bb320438360166ddd1c2d1b368472afdaed639f1effa3`（localization） |
| 4 | 隔离身份判据的实测输出 | `coverage_8.json` 键 `[0]`（`state_key=AN|M_plus`）：`identity_evidence[0].status = IDENTITY_EVIDENCE_NOT_IN_FRONTIER_REGISTER`、`geometry_hash_bound=false`、`raw_four_files_rehashed=false`、`coverage_gate=HELD` | `docs/handoffs/strict_rebuild_20261103/recovery_decisions_20261103_v9/coverage_8.json` 键 `[0].identity_evidence` / `[0].coverage_gate` | `26ccc6e50a510a8a4f37c35b1bd06bd2e417f63ec7d0827366a20d03f36f2ba7` |
| 5 | 现存的唯一 `AN__M_plus__primary` 前沿任务目录（对照组，**不是** tors 成员的来源） | 四文件齐全且与登记表行 5 的四哈希一致：`job.inp=38e3c4e5…`、`geom.xyz=c1a83a12…`、`attempt/job.log=19d61aea…`、`attempt/job.molden.input=59de2fb2…`；`fetch_receipt.json=66cf28e6…` | `work/hpc_frontier_localization_v1/tasks/AN__M_plus__primary/{job.inp,geom.xyz,attempt/job.log,attempt/job.molden.input,fetch_receipt.json}`；对 `outputs/physics_completion/frontier/frontier_identity_evidence.csv:5` | 实测：`job.inp`=`38e3c4e5b8e7d57681e00574a188d56415b56fd13b35ae6cf7e434255e4f6565`；`geom.xyz`=`c1a83a12328ed0f670f2251e4ac698da60d60ee79e0fd758c13b0febd024d8ca`；`attempt/job.log`=`19d61aeaa47bf3a9b27f020e2fe955de9adb01abb3722cb9548ed93b2b54b4be`；`attempt/job.molden.input`=`59de2fb239e45bc6a169cb1b9c93e234e9d97cce9048777b2acdf2e62ebe8393`；`fetch_receipt.json`=`66cf28e6911ee13d31f4fe387687bc017cbf60c88f56f27f8362c71a8eae5d3b` |
| 6 | 候选自己的优化／频率日志 | 存在且哈希与机器证据一致；`job.inp` 首行 `! wB97X-D4 def2-TZVPD Opt AnFreq SMD(acetonitrile) VeryTightOpt TightSCF SlowConv`、`import_level.txt = torsion_probe_from_primary_minimum_offset_60`；日志 `****ORCA TERMINATED NORMALLY****`。**按 J3 原话：不构成另一个已绑定的独立前沿身份来源** | `work/hpc_torsion_probe_v2_realfragment/tasks/AN/M_plus__tors_3_0_1_2/snapshots/3749450_0/{job.log,job.inp,geom.xyz}`；`candidate_sources.json` 键 `an_frontier.existing_log_sha256` | 实测 `job.log`=`3fb8066e0f26d6da0a6cfd9b081a48cddf5e370b9847e3403c4bddfe27de5926`（与 json 记录一致）；`job.inp`=`6d0aefeeb9faf555d1f05a692c1efeb7175444cfd5a0177f2edb87c502c48ab2`；`geom.xyz`=`02e5e877b81e3697c57d747718c37deb56469ee1d8da064203295e34f1e06a05` |
| 7 | 历史簇头成员 `AN|M_plus|primary` 的身份状态 | `member_statuses.csv` 列 `isolated_eligible=false`（dispositions 同义键 `strict_eligible=false`），原因同时含数值门与身份门两类：`MEASURED_NOT_MET;IDENTITY_PENDING;PROTOCOL_REVIEW`，其中 `PRIMARY_IDENTITY_SEPARATE_SOURCE_NOT_REVERIFIED` | `.../verification_20261103/member_statuses.csv:6`；`.../eight_admission_v2/member_terminal_dispositions.json` 键 `member_key=AN|M_plus|primary` | `2875d108c3236e452dedc06c9eca3c3b6f9445bbf33de432cf289899a4708b19`（statuses）；`b12c5c711213e39282be3cae4792ef81a8f263a34aec8dc57ddad32c4e8cc03a`（dispositions） |
| 8 | 远端来源 | `remote.status = INACCESSIBLE_NOT_VERIFIED`，无远端文件读取 | `candidate_sources.json` 键 `remote`（文件行 166-171）；`CANDIDATE_SOURCES.md:11` | `3bccdb416e2ebaa10c06efe1b787c8adc3fcf89170d3ab4801eabd56d0d6a244` |
| 9 | 决策层对身份门的记法 | `closed_gates` 只写“物种/**数值身份旁证**”（未含“前沿身份链”），`remaining_stop` 首项即“身份链缺项” | `.../recovery_decisions_20261103_v9/decisions.csv:5` | `ac430d378c05444c9f2afc08b0ac477b6221ff4d64a78dedd7d3f8136cc1ae5d` |

### 1.3 明确不做的三类替代（防混淆）

| 不做 | 理由 | 来源 |
|---|---|---|
| 不用数值 QC（五项收敛、印刷容差）替代身份结论 | `AN|M_plus|primary` 的 `MEASURED_NOT_MET` 属数值门，`IDENTITY_PENDING` 属身份门，二者在同一行但相互独立 | `member_statuses.csv:6`；`member_statuses.csv` 表头（行 1 列 `evidence_statuses` 与 `specific_reasons`） |
| 不因“限定来源未找到”判身份失败 | 缺的是“已绑定的独立前沿身份来源”，不是对已存在来源的判定 | `CANDIDATE_SOURCES.md:5` |
| 不把候选自己的 Opt/Freq 日志当身份来源 | 该日志无 frontier 登记绑定，非“独立前沿身份来源” | `CANDIDATE_SOURCES.md:5` |

---

## 2. 结论 A2-(b)：单盆地证据 —— **未闭合**

> **一句话结论（b）：AN M⁺ 的单盆地证据未闭合——同一组证据在两套输入语义下给出相反路由（保留历史去重关系 → `single_basin_verified`；严格池去重 → `single_basin_scope_review / unresolved`），独立严格复核状态为 `UNRESOLVED_RECHECK_REQUIRED` 且要求重建搜索范围、合格起点与去重簇，因此“单盆地已成立”目前不成立；该停点是范围与证据审查状态，既非科学失败，也不归因于数值误差。**

### 2.1 `single_basin_verified` 的路由前提（代码判据逐条对照）

| # | 前提条件 | 代码位置 | AN M⁺ 实测 | 证据来源 |
|---|---|---|---|---|
| P1 | 无 `pending`/`ready` 的已登记起点 | `scripts/wp_production/build_coverage_reviews.py:174-176` | 通过（隔离输入中无 pending 成员） | `coverage_8.json` 键 `[0]` |
| P2 | 至少一个 `computed` 成员 | `build_coverage_reviews.py:177-178` | 通过（`tors_3_0_1_2` `historical_status=computed`、`strict_eligible=true`（该键名为 dispositions JSON 字段；`member_statuses.csv` 对应列名为 `isolated_eligible`）） | `eight_admission_v2/member_terminal_dispositions.json` 键 `AN|M_plus|tors_3_0_1_2` |
| P3 | 全部 computed 成员的 novelty 为 `known`（`new`/`unresolved` 不通过） | `build_coverage_reviews.py:194-221`（`new` → `single_basin_scope_review`，行 215-221） | **两套语义分歧**：旧决策脚本带历史 `duplicate_of` → `known`；完整入口用严格池去重 → `new` | `AN_ROOT_CAUSE.md:7`、`AN_ROOT_CAUSE.md:9` |
| P4 | `production_evidence`（各合格代表的 opt_log / opt_input / 频率日志 / 末几何四类文件齐全且已哈希） | `build_48_recovery_decisions.py:187-192` | 通过（`production_evidence_files_present_and_hashed=true`） | `coverage_8.json` 键 `[0].production_evidence_files_present_and_hashed` |
| P5 | `_search_scope_documented`：登记起点非空 **且** `search_outcome ∈ {new_minima_found, no_new_minimum_found, unused_pool_basin_no_search_needed}` | `build_coverage_reviews.py:154-164` | 通过：`registered_starts=[tors_3_0_1_2]`、`qualified_registered_starts=[AN|M_plus|tors_3_0_1_2]`、`search_outcome=no_new_minimum_found` | `coverage_8.json` 键 `[0]` |
| P6 | （独立门）身份链全部 `FROZEN_FRONTIER_CHAIN_VERIFIED` 才可能关闭 coverage gate | `build_48_recovery_decisions.py:214-217` | **不通过**：`coverage_gate=HELD`（见结论 a） | `coverage_8.json` 键 `[0].coverage_gate` |

### 2.2 同一状态的五个路由视图（并列，不裁定）

| 视图 | 输入语义 / 时间 | 路由与 verdict | 承重/合格代表 | 来源（路径 + 行/键） | 文件 SHA256 |
|---|---|---|---|---|---|
| A 生产正式 review | `coverage_review_v2_dedup_aware_20261027`；mtime 2026-11-02 15:45 | `single_basin_verified` / `resolved`；`computed_new_members` 为空；`n_unique_after=1`；`resolution_path=new_search_required` | `kept_pool_evidence=AN|M_plus|primary`（严格过滤下不合格） | `outputs/physics_completion/recovery/coverage_reviews.csv:2` | `e89188f6eac28bbf2dd309a95ec19ea9b1cc78969a262883820f939eec28ba40` |
| B 生产标签 | 同上 | `coverage_status=resolved_by_review`、`pool_limited=true`、`limitation_reason=single_basin_pool`、`n_registered=2, n_qc_passed=1, n_qc_failed=1, n_deduplicated=1, n_unique=1` | review_id 绑定视图 A | `outputs/physics_completion/ensembles/production_ensemble_labels.csv:14` | `c21003f5e18a2faaf4e3c8e91c379ea3ab16659706d13786ed25df0038ae0c80` |
| C 隔离 `coverage_route`（v9） | 严格池 + 历史 dedup 关系；mtime 2026-11-03 09:57 | `route=single_basin_verified`、`route_reason`“computed start(s) reproduced the single known minimum, and the production evidence + registered search scope are complete”、`coverage_gate=HELD` | `representatives=[AN|M_plus|tors_3_0_1_2]` | `recovery_decisions_20261103_v9/coverage_8.json` 键 `[0]` | `26ccc6e50a510a8a4f37c35b1bd06bd2e417f63ec7d0827366a20d03f36f2ba7` |
| D 完整生成器严格隔离（最新） | 严格池去重（`new`），review_version `coverage_review_v3_strict_basin_guard_20261103`；mtime 2026-11-03 11:25 | `route=single_basin_scope_review` / `verdict=unresolved`；`evidence_note`“one qualified basin remains; a computed recovery start has no qualified independent second basin, so search scope and production evidence require separate review”；`kept_pool_evidence` 为空；`n_unique_after=1` | `computed_new_members=AN|M_plus|tors_3_0_1_2`、`registered_starts=tors_3_0_1_2` | `remote_closure_20261103/eight_admission_v2/full_generator_8.json` 键 `[0]` | `acd48d381e71d8939b0ecbc24b077919a96f8762053e0581c06309e18d9ba15c` |
| E 独立严格复核 | 旧 claim vs 严格合格池；mtime 2026-11-03 09:19 | `status=UNRESOLVED_RECHECK_REQUIRED`；`reason=old claim depends on a member absent from strict qualified representatives`；`zero_compute_action=reconstruct search scope, qualified starts and dedup clusters; do not inherit old resolved` | 合格代表仅 `AN|M_plus|tors_3_0_1_2` | `verification_20261103/coverage_recheck.json:3-13` | `182d32aba5e99e7ff13f7f922f42d4e3fe473f26e8a276710419ddcc1cbc8a6d` |

### 2.3 单盆地三要素齐备性判定

| 要素 | 现有证据 | 状态 | 来源（路径 + 行/键） | SHA256 |
|---|---|---|---|---|
| ① 合格起点登记 | `start_1_basin=tors_3_0_1_2`、`max_new_starts=0`、`needs_versioned_search=false`、`released=true`、`search_outcome=no_new_minimum_found` | **登记齐** | `outputs/physics_completion/recovery/strict_recovery_v1_manifest.csv:5` | `aab933144ad63d6af1b94b6de4d1f3bdec840b1986c85455357363bceb5ef1a0` |
| ② 搜索执行记录 | `states_searched` 含 `AN|M_plus`；协议 `num_confs_per_state=64`、`rmsd_threshold_a=0.35`；`per_state_new_minima` 无 AN 条目；`strict_recovery_v1_search_pool.csv` 共 3 行（表头 + 2 条 `TMP|M_plus`），**无 AN 行** | **执行有记录，池内无新最小值** | `outputs/physics_completion/recovery/strict_recovery_v1_search_index.json` 键 `states_searched` / `protocol` / `per_state_new_minima`；`strict_recovery_v1_search_pool.csv`（全表 3 行） | 同 manifest 一并读取：`search_index.json`=`932a454a4aede0dc1ec254d8f3f1c4814edd38bc8431c27d741960ddf39f7dc3`；`search_pool.csv`=`8ae4bd1372d8376eafb56199f49058678f7a13291a3b4464d173f04de645590f` |
| ③ 起点是否“合格” | 严格合格池内 AN M⁺ 仅 `tors_3_0_1_2` 一个成员（`isolated_eligible=True`）；历史簇头 `primary` 被严格过滤判不合格 | **合格起点 = 1（单簇）** | `member_statuses.csv:6`（primary）、`:7`（`tors_3_0_1_2`，`old_kept=False, isolated_eligible=True, ISOLATED_CONDITIONAL_POOL`） | `2875d108c3236e452dedc06c9eca3c3b6f9445bbf33de432cf289899a4708b19` |
| ④ 去重簇 | 生产去重：`AN|M_plus|primary` `kept=true, unique`；`AN|M_plus|tors_3_0_1_2` `kept=false, duplicate_of=primary`（`same minimum: topology mapping + rmsd 0.0015 A + torsion 0.0 deg`）。即唯一簇的簇头是被严格过滤剔除的成员；**严格口径下的簇与搜索范围重建尚未产出** | **未重建** | `outputs/physics_completion/ensembles/production_ensemble_dedup.csv:30-31`；`coverage_recheck.json:12`（`zero_compute_action`） | `1f3ea92971d9725f407109d6a3c121b18aa4af13f80331e891ee612247377c04` |
| ⑤ 生产证据文件 | `production_evidence_files_present_and_hashed=true` | 有 | `coverage_8.json` 键 `[0]` | `26ccc6e5…` |
| ⑥ 身份门（独立） | `HELD`，见结论 (a) | 未闭合 | `coverage_8.json` 键 `[0].coverage_gate` | 同上 |
| ⑦ 搜索范围科学审查 | “64 构象 GFN2 搜索与 methyl-rotor 起点能否支撑目标协议搜索范围仍需审查；前沿身份来源另见候选核实结果” | **未审** | `blocker_resolution_20261103/AN_ROOT_CAUSE.md:25` | `394a7ad2467123351292555ee1d9a1d018a500bca7bcf475a24246ec4c81e92c` |

**判定**：①②⑤齐备，但 ④（严格口径的去重簇/搜索范围重建）未产出、正式 review 的承重成员（`primary`）不在严格合格代表内、最新完整生成器给 `unresolved`、独立复核要求“不得继承旧 resolved”——故**单盆地证据未闭合**。另需注意 `AN_ROOT_CAUSE.md:13`：单簇且 novelty 为 `new` 时停点是“单盆地搜索范围与生产证据需要单独审查”，该处理**不将单代表一概判为 coverage 不足**；`AN_ROOT_CAUSE.md:34`：这些是生成器实际路由，并非科学失败。

---

## 3. 未确定事项

| # | 未确定事项 | 为何未定 | 来源（路径 + 行/键） |
|---|---|---|---|
| U1 | 远端是否含 `tors_3_0_1_2` 的独立前沿身份来源 | `remote.status=INACCESSIBLE_NOT_VERIFIED`，本轮无远端文件读取；按红线 2 不推断其存在或不存在 | `candidate_sources.json` 键 `remote`（行 166-171）；`CANDIDATE_SOURCES.md:11` |
| U2 | 前沿登记三表为何不含 tors 成员（登记时序/登记范围） | 本轮只确认“三表 0 命中”这一事实，未追查登记生成过程 | `frontier_identity_evidence.csv` / `frontier_localization.csv` / `frontier_legs.csv`（各 81 行 = 表头 1 + 数据 80） |
| U3 | 生产 v2 review 与严格 v3 隔离路由之间以哪一版为正式 | 未见裁定文档；`AN_ROOT_CAUSE.md:15` 明确“本轮仅运行隔离入口，未生成正式 review”，且 review version 已升为 `coverage_review_v3_strict_basin_guard_20261103` | `AN_ROOT_CAUSE.md:15`；`coverage_reviews.csv:2` |
| U4 | 视图 C（09:57 `single_basin_verified`）、视图 E（09:19 `UNRESOLVED_RECHECK_REQUIRED`）、视图 D（11:25 `unresolved`）三者优先级与合成规则 | 三份产物时间与输入语义不同，本轮未见合并/裁定规则文档 | 三文件 mtime（见第 0 节）+ `coverage_8.json` / `coverage_recheck.json` / `full_generator_8.json` |
| U5 | 64 构象 GFN2 搜索范围是否足以支撑目标协议的搜索范围 | 明确记为“仍需审查”，未见审查结论 | `AN_ROOT_CAUSE.md:25` |
| U6 | `AN|M_plus|primary` 的 `PROTOCOL_REVIEW`、`IDENTITY_PENDING` 是否可解除 | 需独立身份来源复核与协议状态裁决，本轮无结论（且与结论 (a) 的 tors 成员身份门是两件事） | `member_statuses.csv:6`；`member_terminal_dispositions.json` 键 `AN|M_plus|primary` |
| U7 | 候选路径是否覆盖 AN M⁺ | `candidate_evaluation.json` 检索 `"AN"`/`"TMP"` **0 命中**（仅 DMC 5 条 + EC 6 条），故候选通道对本态无现成材料 | `verification_20261103/candidate_evaluation.json`（250 行，0 命中） |

> 以上均为**来源、登记与审查状态**的未确定，**无一项归因于数值误差**。

---

## 4. 是否需要新物理证据

| 项 | 结论 |
|---|---|
| 是否主张新增计算 | **否**。现有材料不能证明需要新增计算 |
| 现有记录 | `decisions.csv:5` 的 `new_computation_budget = NONE_JUSTIFIED_YET`；`AN_ROOT_CAUSE.md:34`“七个 pending…不能自动解释为必须新增计算”；`CANDIDATE_SOURCES.md:5`“本轮不将这一待核项转成必须新算”；`verification_20261103/README.md:21`“当前不能证明任何一态已穷尽…未确认最小新增实验清单或预算” |
| 最小补证 | 见下表；**全部为既有证据的读取/核对/重建留档，不构成计算申请** |

### 4.1 最小补证清单（证据类型 + 最小范围；**不构成计算申请**）

| # | 证据类型 | 最小范围 | 关闭哪个门 | 是否计算 |
|---|---|---|---|---|
| S1 | 读取型来源核验：恢复远端访问后，读取 `AN__M_plus__tors_3_0_1_2` 对应的前沿任务目录/登记记录，并对其 `job.inp、geom.xyz、job.log、job.molden.input` 四文件重哈希比对 | 1 个任务目录、4 个文件 | 结论 (a) 身份门 | **不构成计算申请** |
| S2 | 本地登记一致性核对：定位前沿三份登记表为何无 `tors_3_0_1_2` 行（登记输入清单 + 生成脚本输出） | 3 个 CSV + 1 个生成脚本的既有输出 | 结论 (a) 身份门“来源登记缺项”定位 | **不构成计算申请** |
| S3 | 去重簇重建留档：以 AN M⁺ 现有 5 个成员的既有几何，按既有 Kabsch/RMSD 判据（阈值 0.35 Å，见搜索协议）重跑并留档 | 本态 5 个成员的既有几何 | 结论 (b) 要素 ④ | **不构成计算申请** |
| S4 | 搜索范围审查记录：核对 `strict_recovery_v1_manifest.csv` + `strict_recovery_v1_search_index.json` + `strict_recovery_v1_search_pool.csv` 三份既有文件对 64 构象搜索范围的覆盖说明 | 3 份既有文件 | 结论 (b) 要素 ⑦ | **不构成计算申请** |

> 若 S1/S2 完成后仍无远端身份来源，届时再由 Lead 判断是否需要新物理证据；本报告**不提出任何计算申请**。

---

## 5. 关键文件 SHA256 汇总

| 文件 | SHA256 |
|---|---|
| `docs/handoffs/strict_rebuild_20261103/blocker_resolution_20261103/AN_ROOT_CAUSE.md` | `394a7ad2467123351292555ee1d9a1d018a500bca7bcf475a24246ec4c81e92c` |
| `docs/handoffs/strict_rebuild_20261103/blocker_resolution_20261103/CANDIDATE_SOURCES.md` | `64fa07bf8b518b0235abaffe6acd6830a8a32d12a8471276d2f19af391d666f4` |
| `docs/handoffs/strict_rebuild_20261103/blocker_resolution_20261103/candidate_sources.json` | `3bccdb416e2ebaa10c06efe1b787c8adc3fcf89170d3ab4801eabd56d0d6a244` |
| `docs/handoffs/strict_rebuild_20261103/verification_20261103/coverage_recheck.json` | `182d32aba5e99e7ff13f7f922f42d4e3fe473f26e8a276710419ddcc1cbc8a6d` |
| `docs/handoffs/strict_rebuild_20261103/verification_20261103/member_statuses.csv` | `2875d108c3236e452dedc06c9eca3c3b6f9445bbf33de432cf289899a4708b19` |
| `docs/handoffs/strict_rebuild_20261103/verification_20261103/README.md` | `61e930b842abc97c082e11e9fa0662f356e25be3411aabce0774e4b3206ddf3e` |
| `docs/handoffs/strict_rebuild_20261103/verification_20261103/candidate_evaluation.json` | `14d4d1318c899d4e3237b26c07c2d9ccfe6ce6e453609f08b4621b767bc89447` |
| `docs/handoffs/strict_rebuild_20261103/recovery_decisions_20261103_v9/decisions.csv` | `ac430d378c05444c9f2afc08b0ac477b6221ff4d64a78dedd7d3f8136cc1ae5d` |
| `docs/handoffs/strict_rebuild_20261103/recovery_decisions_20261103_v9/coverage_8.json` | `26ccc6e50a510a8a4f37c35b1bd06bd2e417f63ec7d0827366a20d03f36f2ba7` |
| `docs/handoffs/strict_rebuild_20261103/recovery_decisions_20261103_v9/README.md` | `0dd8c7cf2204de4590bcc1c549d193717b9447957e04ba94b664308ccf9d3f44` |
| `docs/handoffs/strict_rebuild_20261103/remote_closure_20261103/eight_admission_v2/member_terminal_dispositions.json` | `b12c5c711213e39282be3cae4792ef81a8f263a34aec8dc57ddad32c4e8cc03a` |
| `docs/handoffs/strict_rebuild_20261103/remote_closure_20261103/eight_admission_v2/full_generator_8.json` | `acd48d381e71d8939b0ecbc24b077919a96f8762053e0581c06309e18d9ba15c` |
| `outputs/physics_completion/recovery/coverage_reviews.csv` | `e89188f6eac28bbf2dd309a95ec19ea9b1cc78969a262883820f939eec28ba40` |
| `outputs/physics_completion/ensembles/production_ensemble_labels.csv` | `c21003f5e18a2faaf4e3c8e91c379ea3ab16659706d13786ed25df0038ae0c80` |
| `outputs/physics_completion/ensembles/production_ensemble_dedup.csv` | `1f3ea92971d9725f407109d6a3c121b18aa4af13f80331e891ee612247377c04` |
| `outputs/physics_completion/recovery/strict_recovery_v1_manifest.csv` | `aab933144ad63d6af1b94b6de4d1f3bdec840b1986c85455357363bceb5ef1a0` |
| `outputs/physics_completion/recovery/strict_recovery_v1_search_index.json` | `932a454a4aede0dc1ec254d8f3f1c4814edd38bc8431c27d741960ddf39f7dc3` |
| `outputs/physics_completion/recovery/strict_recovery_v1_search_pool.csv` | `8ae4bd1372d8376eafb56199f49058678f7a13291a3b4464d173f04de645590f` |
| `outputs/physics_completion/frontier/frontier_identity_evidence.csv` | `0f8a8653b5285e0e786e62f1f3c03d021b8edc48502a56e768dba46d7ebcc5c6` |
| `outputs/physics_completion/frontier/frontier_localization.csv` | `7310354c98ff2962226bb320438360166ddd1c2d1b368472afdaed639f1effa3` |
| `work/hpc_torsion_probe_v2_realfragment/tasks/AN/M_plus__tors_3_0_1_2/snapshots/3749450_0/job.log` | `3fb8066e0f26d6da0a6cfd9b081a48cddf5e370b9847e3403c4bddfe27de5926` |
| `work/hpc_frontier_localization_v1/tasks/AN__M_plus__primary/attempt/job.log` | `19d61aeaa47bf3a9b27f020e2fe955de9adb01abb3722cb9548ed93b2b54b4be` |
| `work/hpc_anfreq_cohort_20261016/hpc_runs/AN_M_plus/job.log` | `5136b07ab7fcfdc3bf6752b5c34337841cd3334634ac4df8ee3008e922be315f` |

---

## 6. 交付说明

本文件为 A2 任务允许新增的两个文件之一：`docs/handoffs/lead_reception_strict_rebuild_20261103/evidence/A2_AN_Mplus_identity.md`。本文件自身的 SHA256 随交付消息一并给出。本轮未修改任何既有文件、未提交作业、未新增计算。
