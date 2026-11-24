# A1 五态覆盖逐态取证（strict_rebuild_20261103 → lead_reception）

- 任务：五态覆盖——逐态列出搜索范围、真实起点、作业与终态、身份及去重结果；判定每态属于「证据已有但未绑定」还是「覆盖证据不足」。
- 五态清单来源：`docs/handoffs/strict_rebuild_20261103/verification_20261103/README.md:15`（"五态条件池：DEC|LiM_2plus、DEC|M_plus、GBL|LiM_plus、PC|M_plus、TMP|M 仍需独立身份与 coverage 核验"），与 `verification_20261103/coverage_recheck.json`（`states[].state_key`）逐态一致。
- 性质：只读取证。本轮**未修改、未删除任何既有文件，未新增任何计算，未提交任何作业**；本文件是本任务唯一新增文件。
- 表述纪律：凡"本轮限定检索范围内未找到"一律写为**未找到**，不写成"不存在"；不补写任何搜索结论、不推断未记录的检索历史。

---

## 1. 五态判定总表

| 态 | 搜索范围（本轮只读检索与命中） | 真实起点 | 作业与终态 | 身份结论 | 去重结果 | 判定 |
|---|---|---|---|---|---|---|
| DEC\|LiM_2plus (C03) | li_motif round1 筛选 10 起点（`li_motif_screen.csv:42-51`，c02 kept 于 `:44`）；`motif_plan.csv:7` starts_round1=16/kept=1/verdict=production_motif_within_1kj；round2 计划 `li_motif_plan_round2.csv:5`（3 个已验证替代父、ceiling=4）+ 执行 `li_motif_round2_exec.csv:2-28`（3 父 × 9 布局，仅 `:5` kept → `work/limotif_r2/…`）；`sampling_audit_3to6.csv:9`（li_motif_round2_measured，2 independent，executable_partial）；`coverage_reviews.csv`、`strict_recovery_v1_manifest.csv` 本轮未命中该态 | c02 ← `work/limotif/C03_LiM_2plus/C03_LiM_2plus_c02/xtbopt.xyz`（sha `c17e97053121faf8…`，`production_ensemble_candidates.csv:86`；`structures.csv:95` start 同值）；父几何 `work/wp2prod/DEC/LiM_2plus/DEC_LiM_2plus_opt.xyz`（`493596b35f49…`，`li_motif_screen.csv:44`） | c02：数组作业 `3723647_9`（`work/hpc_production_ensemble_r1_036-053/tasks/DEC/LiM_2plus__c02/snapshots/3723647_9/job.log`，磁盘存在已核，sha `c400ff83…`），`structures.csv:95` status=computed、analytical_hessian、n_freq=57、imag=0、lowest 69.86 cm⁻¹、final `771a804688688c5f…`；`member_statuses.csv:12` ISOLATED_CONDITIONAL_POOL。primary `structures.csv:40` status=ready 但 `member_statuses.csv:13` MEASURED_NOT_MET;IDENTITY_PENDING;PROTOCOL_REVIEW + PRIMARY_IDENTITY_SEPARATE_SOURCE_NOT_REVERIFIED。c03_c03：attempt0 `3728918_5` superseded、attempt1 `3731705_0` technical_complete_qc_failed（source_index reasons 含 NOT_IN_FORMAL_CANDIDATE_REGISTER），未入 candidates/labels（labels `n_registered=1`） | c02 **verified**（`frontier_identity_evidence.csv:7`，missing/failed 空，geom `771a8046…` = structures final）；`coverage_8.json:46-84` identity_evidence status=FROZEN_FRONTIER_CHAIN_VERIFIED、geometry_hash_bound=true、raw_four_files_rehashed=true；primary 身份未复核（未找到 primary 的 frontier 行） | `dedup.csv:82` c02 kept=true unique；`:83` primary kept=false duplicate_of=c02（same minimum, rmsd 0.003 Å, torsion 0.6°）；labels `:39` n_deduplicated=1、n_members=1、pool_limited=true、all_extras_deduplicated_to_primary | **证据已有但未绑定**（成员/身份/去重/两轮搜索范围记录齐备，coverage 登记缺失） |
| DEC\|M_plus (C03) | `sampling_conformer_set.csv:11-14` 4 个结构（c15 / r2_c22 / r2_c46 / r2_c23，selected=true 3 条、`:14` r2_c23 selected=false）；`sampling_audit_3to6.csv:7`（free_conformer，round1=3→pool4、ceiling4、has_primary、executable_partial）；`sampling_index.json` conformer_pool（round1 16 起点 ∪ round2 64 起点，`keep_round1=3/max_pool=6`）；`coverage_reviews.csv`、`strict_recovery_v1_manifest.csv` 本轮未命中该态 | 15 ← `work/sampling/DEC/M_plus/c15/xtbopt.xyz`（`f2897bb8fbdbbf256…`，candidates `:36`、conformer_set `:11`）；structures attempt3 的 start=`34352b0dadb7…` 与登记值不同（见未确定事项） | attempt0 `3720638_1` status=superseded（orca_close_enough_but_frozen_tolE_missed_reopt_required）；attempt3 `3721460_1` status=computed、analytical_hessian、n_freq=54、imag=0、lowest 52.12、final `8e9479db43bcd35e…`（`structures.csv:132`）；22 attempt3 `3721460_2` computed 但 conv=first_point_convergence_geometry_never_moved 且缺 energy_change（`member_statuses.csv:17` EVIDENCE_MISSING）；23 attempt0 `3727721_3` superseded、attempt1 `3731145_0` computed 但 reasons 含 FIVE_ITEM_MISSING + SPECIES_IDENTITY_UNVERIFIED + NOT_IN_FORMAL_CANDIDATE_REGISTER；primary `structures.csv:16` ready 但 `member_statuses.csv:18` 同 primary 类未过 | 15 **verified**（`frontier_identity_evidence.csv:10`，geom `8e9479db…` = structures final）；`coverage_8.json:85-123` FROZEN_FRONTIER_CHAIN_VERIFIED；`:11` 22、`:12` primary 亦有 verified 行，但 22 五项缺 energy_change、primary 身份为"独立来源未复核" | `dedup.csv:32-34` primary/22/15 全部 kept=true、unique（无 duplicate_of）；labels `:15` n_registered=2、n_qc_passed=3、n_deduplicated=0、n_unique=3、n_members=3、pool_limited=false | **证据已有但未绑定** |
| GBL\|LiM_plus (C13) | `li_motif_screen.csv:137-140` round1 筛选 4 起点（c00-c03，c03 kept 于 `:140`，其余 duplicate_geometry_of_c03）；`motif_plan.csv:16` starts_round1=16/kept=1/within_1kj；`sampling_index.json:193-199` "4 starts screened"、status=computed；**本轮限定检索未找到**该态的 round-2 记录（`li_motif_plan_round2.csv` 仅 EMC/DEC/DME/TMP 8 行；`li_motif_round2_exec.csv` 54 行命中全部为 DEC）与 audit 行（`sampling_audit_3to6.csv` 仅 EMC/DEC/DME/TMP 四分子，`sampling_index.json:364/420` 明示 GBL 不属 designated 集合）；`coverage_reviews.csv`、`strict_recovery_v1_manifest.csv` 本轮未命中该态 | c03 ← `work/limotif/C13_LiM_plus/C13_LiM_plus_c03/xtbopt.xyz`（`adb7e3a49d1de739…`，candidates `:73`、`structures.csv:89` start 同值）；父几何 `work/wp2prod/GBL/LiM_plus/GBL_LiM_plus.xyz`（`c916bc4daaf8…`，`li_motif_screen.csv:140`） | c03：数组作业 `3723647_3`（`work/hpc_production_ensemble_r1_036-053/tasks/GBL/LiM_plus__c03/snapshots/3723647_3/job.log`，磁盘存在已核，sha `26ef1520…`），`structures.csv:89` status=computed、analytical_hessian、n_freq=39、imag=0、lowest 43.97、final `fc19de61a6de1163…`；`member_statuses.csv:93` ISOLATED_CONDITIONAL_POOL。primary `structures.csv:33` ready 但 `member_statuses.csv:94` MEASURED_NOT_MET;…;PRIMARY_IDENTITY_SEPARATE_SOURCE_NOT_REVERIFIED | c03 **verified**（`frontier_identity_evidence.csv:55`，geom `fc19de61…` = structures final，wavefunction R）；`coverage_8.json:124-162` FROZEN_FRONTIER_CHAIN_VERIFIED、geometry_hash_bound=true、raw_four_files_rehashed=true；未找到 primary 的 frontier 行 | `dedup.csv:72` c03 kept=true unique；`:73` primary kept=false duplicate_of=c03（rmsd 0.012 Å, torsion 2.7°）；labels `:34` n_deduplicated=1、n_members=1、pool_limited=true | **证据已有但未绑定**；范围证据为五态中最弱（无 round-2 记录、无 audit 行——均为本轮限定检索未找到，非"不存在"） |
| PC\|M_plus (C05) | `sampling_conformer_set.csv:18` 唯一结构 r2_c46（rank1、selected=true）；`sampling_index.json:420` PC 属 executed=12 分子、`:58` pool_limited_states 含 PC\|M_plus；**本轮限定检索未找到**该态 audit 行（PC 非 designated 分子）；`coverage_reviews.csv`、`strict_recovery_v1_manifest.csv` 本轮未命中该态 | 46 ← `work/sampling/PC/M_plus/r2_c46/xtbopt.xyz`（`ff038bb4e457d6fc…`，candidates `:41`、conformer_set `:18`；`structures.csv:72` start 同值） | 46：数组作业 `3720638_4`（`work/hpc_production_ensemble_r1_018-035/tasks/PC/M_plus__46/snapshots/3720638_4/job.log`，磁盘存在已核，sha `8040d2f4…`），`structures.csv:72` status=computed、analytical_hessian、n_freq=39、imag=0、lowest 102.57、final `5478c71eed13fe46…`；`member_statuses.csv:103` ISOLATED_CONDITIONAL_POOL。primary `structures.csv:18` ready 但 `member_statuses.csv:104` MEASURED_NOT_MET;…;PRIMARY_IDENTITY_SEPARATE_SOURCE_NOT_REVERIFIED | 46 **verified**（`frontier_identity_evidence.csv:62`，geom `5478c71e…` = structures final）；`:63` primary 亦 verified 行；`coverage_8.json:163-201` FROZEN_FRONTIER_CHAIN_VERIFIED | `dedup.csv:49-50` primary 与 46 均 kept=true、unique；labels `:23` n_registered=1、n_qc_passed=2、n_deduplicated=0、n_unique=2、n_members=2、pool_limited=false | **证据已有但未绑定**（范围记录只有单结构 conformer 池，且无 audit 行） |
| TMP\|M (C17) | `sampling_conformer_set.csv:41-42` 2 个结构（r2_c48 rank1、r2_c27 rank2，均 selected=true）；`sampling_audit_3to6.csv:14`（free_conformer、round1=2、independent=2、ceiling=2、has_primary=false、extension_available=false、**sampling_limited**）；`sampling_index.json:62` pool_limited_states 含 TMP\|M；`coverage_reviews.csv`、`strict_recovery_v1_manifest.csv` 本轮未命中该态 | 27 ← `work/sampling/TMP/M/r2_c27/xtbopt.xyz`（`d97d3c2769b015fd…`，candidates `:29`、conformer_set `:42`；`structures.csv:65` start 同值） | 27：数组作业 `3718293_15`（`work/hpc_production_ensemble_r1_000-017/tasks/TMP/M__27/snapshots/3718293_15/job.log`，磁盘存在已核，sha `7dec22f1…`），`structures.csv:65` status=computed、analytical_hessian、n_freq=51、imag=0、lowest 46.40、final `213005d20ea23e8c…`；`member_statuses.csv:131` ISOLATED_CONDITIONAL_POOL。48：attempt0 `3718293_14` superseded（energy_change 8.598e-07 > 2e-07）、attempt1 `3725968_0` computed 但 conv=first_point_convergence_geometry_never_moved 且 `member_statuses.csv:132` EVIDENCE_MISSING（缺 energy_change_Eh）。primary `structures.csv:13` ready 但 `member_statuses.csv:133` 同 primary 类未过 | 27 **verified**（`frontier_identity_evidence.csv:80`，geom `213005d2…` = structures final，wavefunction R）；`coverage_8.json:243-281` FROZEN_FRONTIER_CHAIN_VERIFIED；本轮未找到 TMP\|M\|48 的 frontier 行 | `dedup.csv:27` 27 kept=true unique；`:28` 48 kept=false duplicate_of=27（rmsd 0.007 Å, torsion 1.1°）；`:29` primary kept=true unique；labels `:13` n_registered=2、n_qc_passed=2、n_deduplicated=1、n_unique=2、n_members=2、pool_limited=false | **证据已有但未绑定**；audit 的 sampling_limited 结论基于过期账本哈希，按 `remote_closure_20261103/README.md:43` 不可沿用 |

**总判定**：五态全部为「证据已有但未绑定」——成员证据（严格五项、当前成员登记、共同去重、条件性权重）、合格代表的前沿身份链、以及逐态的搜索范围原始记录都已存在并被冻结，缺的是把范围与合格代表绑定进 coverage 登记（`coverage_status=not_reviewed`、`coverage_review_id` 空、`coverage_8.registered_starts=[]`、`route=pending`、`coverage_gate=HELD`、`search_outcome=not_searched`）。**没有任何一态被判为「覆盖证据不足」**；同时须注意全局限制（§3）：现有文件不能证明任何一态已穷尽搜索，故"绑定完成"也不等于覆盖已裁定。

---

## 2. 逐态证据细目

### 2.1 DEC|LiM_2plus（C03）

原始来源（path:line 或 JSON key path）：
- `docs/handoffs/strict_rebuild_20261103/verification_20261103/coverage_recheck.json:15-20` → `state_key="DEC|LiM_2plus"`、`qualified_representatives=["DEC|LiM_2plus|c02"]`、`status="PENDING_INDEPENDENT_COVERAGE_AND_IDENTITY_REVIEW"`、`zero_compute_action="verify terminal identity and coverage evidence before formal admission"`。
- `outputs/physics_completion/ensembles/production_ensemble_labels.csv:39`（C03,DEC,LiM_2plus：n_registered=1, n_qc_passed=1, n_deduplicated=1, n_unique=1, n_members=1, pool_limited=true, coverage_status=not_reviewed, coverage_review_id 空）。
- `outputs/physics_completion/ensembles/production_ensemble_candidates.csv:85-86`（primary + c02）；`production_ensemble_dedup.csv:82-83`；`production_ensemble_structures.csv:40`（primary）、`:95`（c02 attempt0）。
- `docs/handoffs/strict_rebuild_20261103/verification_20261103/member_statuses.csv:12-13`。
- `docs/handoffs/strict_rebuild_20261103/run_06c49d9e7ebe0688/gap_actions.json:379`（`state_key="DEC|LiM_2plus"` 起）；同块 `:457-459` `existing_archive_action="recheck raw Opt, frequency, identity and registration sources for the listed blockers"`、`coverage_action="rebuild claim from qualified representatives and independent search evidence; old resolved label is not inherited"`、`new_physical_evidence="NOT_AUTHORIZED; scope only after archive search and approved rule stop points"`。
- `…/run_06c49d9e7ebe0688/source_index.json` → `member_sources[]` 中 `DEC|LiM_2plus|c02`（attempt0, computed, kept=true, **eligible=true**, reasons=[]；opt_log `…/3723647_9/job.log` sha `c400ff83…`；final_geom sha `771a8046…`）、`DEC|LiM_2plus|primary`（eligible=false）、`DEC|LiM_2plus|c03_c03`（attempt0 superseded / attempt1 technical_complete_qc_failed，reasons 含 NOT_IN_FORMAL_CANDIDATE_REGISTER）。
- `…/run_06c49d9e7ebe0688/states.json[]` → 该态 `historical_label="accepted"`、`eligible_members/strict_kept=["DEC|LiM_2plus|c02"]`、`weights=[{rep:"DEC|LiM_2plus|c02",weight:1}]`、`category="CONDITIONAL_EVIDENCE_SUFFICIENT"`、`formal_acceptance="NOT_PUBLISHED"`、`old_coverage_claim_survives=false`、`old_coverage_review_reusable_without_recheck=false`。
- `…/recovery_decisions_20261103_v9/decisions.csv:6`（best chain=c02、remaining_stop="coverage 路由 pending，正式承重审计未闭合"、next action="核身份缺项与搜索起点/范围；按隔离合格池重审 coverage…"、budget=NONE_JUSTIFIED_YET）。
- `…/recovery_decisions_20261103_v9/coverage_8.json:46-84`（representatives=[c02]、identity_evidence FROZEN_FRONTIER_CHAIN_VERIFIED、registered_starts=[]、qualified_registered_starts=[]、search_outcome="not_searched"、route="pending"、coverage_gate="HELD"、route_reason="no recovery member registered yet; a versioned new search must register a start before any verdict"）。
- `outputs/physics_completion/frontier/frontier_identity_evidence.csv:7`；`outputs/physics_completion/recovery/coverage_reviews.csv`（14 条 review，行 2-15，本轮未命中该态）；`outputs/physics_completion/recovery/strict_recovery_v1_manifest.csv`（13 数据行，本轮未命中该态）。

SHA256（本态引用的生产文件）：见 §4 清单。

未确定事项：
1. round2 执行产物 `work/limotif_r2/DEC_LiM_2plus@c03/DEC_LiM_2plus@c03_c03/xtbopt.xyz`（`li_motif_round2_exec.csv:5` kept=true）是否进入过正式候选登记——本轮在 candidates/labels 中未找到该成员行。
2. `DEC|LiM_2plus|primary` 的前沿身份行本轮未找到（frontier 文件中该态只有 c02）；primary 的 `PRIMARY_IDENTITY_SEPARATE_SOURCE_NOT_REVERIFIED` 仍未闭合。
3. `sampling_audit_3to6.csv:9` 的 executable_partial 结论所依赖的 structure-ledger 哈希已过期（§3.2），其状态结论按 `remote_closure_20261103/README.md:43` 不得直接沿用。
4. c03_c03 的 rescue_budget_exhausted 历史结论（`remote_closure_20261103/README.md:21`）本轮未重算、未复核。

是否需要新物理证据：**仅标记——NOT_AUTHORIZED**（`gap_actions.json:459`；`decisions.csv:6` budget=NONE_JUSTIFIED_YET）。本轮不申请新计算。

### 2.2 DEC|M_plus（C03）

原始来源：
- `coverage_recheck.json:23-28` → state_key、qualified_representatives=["DEC|M_plus|15"]、status=PENDING_INDEPENDENT_COVERAGE_AND_IDENTITY_REVIEW、zero_compute_action 同上。
- `production_ensemble_labels.csv:15`（n_registered=2, n_qc_passed=3, n_deduplicated=0, n_unique=3, n_members=3, pool_limited=false, coverage_status=not_reviewed）。
- `production_ensemble_candidates.csv:35-37`（primary、15、22；23 本轮未找到登记行）；`dedup.csv:32-34`；`structures.csv:16`（primary）、`:69`（15 attempt0 superseded）、`:70`（22 attempt0 superseded）、`:132`（15 attempt3 computed）、`:133`（22 attempt3 computed）。
- `member_statuses.csv:16-18`（15 ISOLATED_CONDITIONAL_POOL；22 EVIDENCE_MISSING/FIVE_ITEM_MISSING:energy_change_Eh；primary MEASURED_NOT_MET;IDENTITY_PENDING;PROTOCOL_REVIEW）。
- `gap_actions.json:674` 起；`:785-787` 三条 action（同 §2.1 文案）。
- `source_index.json` → `DEC|M_plus|15` 两条：attempt0 superseded（job `3720638_1`）、attempt3 computed **eligible=true**（job `3721460_1`，opt_log sha `2b732888…`、final `8e9479db…`）；`22` attempt3 eligible=false（FIVE_ITEM_MISSING）；`23` attempt0 superseded / attempt1 computed（reasons：FIVE_ITEM_MISSING:energy_change_Eh、SPECIES_IDENTITY_UNVERIFIED、NOT_IN_FORMAL_CANDIDATE_REGISTER、SUPERSEDED_BY_LATER_ATTEMPT）。
- `states.json[]` → eligible/strict_kept=["DEC|M_plus|15"]、weights=[{15,1}]、category=CONDITIONAL_EVIDENCE_SUFFICIENT、formal_acceptance=NOT_PUBLISHED、lost_old_representatives=[22, primary]。
- `decisions.csv:9`；`coverage_8.json:85-123`；`frontier_identity_evidence.csv:10-12`（15/22/primary 均 verified）。
- 搜索范围：`sampling_conformer_set.csv:11-14`；`sampling_audit_3to6.csv:7`；`sampling_index.json:36-63`（conformer_pool：union round1 16 + round2 64，keep_round1=3，max_pool=6）；`coverage_reviews.csv`、`strict_recovery_v1_manifest.csv` 本轮未命中该态。

未确定事项：
1. `structures.csv:132` 中 15 的 attempt3 `start_geometry_sha256=34352b0dadb7…`，与 candidates/conformer_set 登记的 `f2897bb8fbdb…` 不同，本轮未找到说明二者关系的记录。
2. `DEC|M_plus|23` 存在于 source_index（job `3727721_3` / `3731145_0`）但不在 candidates/labels 正式登记；其最终处置本轮未找到闭合记录。
3. 22 的 `first_point_convergence_geometry_never_moved` 与缺 energy_change 并存，能否补位/必须重算，本轮未找到裁定记录。

是否需要新物理证据：**仅标记——NOT_AUTHORIZED**（`gap_actions.json:787`；`decisions.csv:9` NONE_JUSTIFIED_YET）。

### 2.3 GBL|LiM_plus（C13）

原始来源：
- `coverage_recheck.json:31-36` → qualified_representatives=["GBL|LiM_plus|c03"]、status=PENDING_INDEPENDENT_COVERAGE_AND_IDENTITY_REVIEW。
- `production_ensemble_labels.csv:34`（n_registered=1, n_qc_passed=1, n_deduplicated=1, n_unique=1, n_members=1, pool_limited=true, all_extras_deduplicated_to_primary, coverage_status=not_reviewed）。
- `production_ensemble_candidates.csv:72-73`；`dedup.csv:72-73`；`structures.csv:33`（primary）、`:89`（c03）。
- `member_statuses.csv:93-94`；`gap_actions.json:3055` 起、`:3132-3134` 三条 action。
- `source_index.json` → `GBL|LiM_plus|c03` attempt0 computed kept=true **eligible=true**（job `3723647_3`，opt_log sha `26ef1520…`、final `fc19de61…`）；`primary` eligible=false。
- `states.json[]` → eligible/strict_kept=["GBL|LiM_plus|c03"]、weights=[{c03,1}]、category=CONDITIONAL_EVIDENCE_SUFFICIENT、formal_acceptance=NOT_PUBLISHED、lost_old_representatives=[]。
- `decisions.csv:35`；`coverage_8.json:124-162`；`frontier_identity_evidence.csv:55`。
- 搜索范围：`li_motif_screen.csv:137-140`；`motif_plan.csv:16`；`sampling_index.json:193-199`；`sampling_audit_3to6.csv`（本轮未找到 GBL 行——GBL 不在 designated 集合，见 `sampling_index.json:364/420`）；`li_motif_plan_round2.csv`（本轮未找到 GBL 行）；`li_motif_round2_exec.csv`（54 条命中全为 DEC，未找到 GBL 行）；`coverage_reviews.csv`、`strict_recovery_v1_manifest.csv` 本轮未命中该态。

未确定事项：
1. 该态是否需要第二轮 motif 搜索、以及为何未列入 `li_motif_plan_round2.csv`——本轮未找到裁定记录（不得据此推断"不需要"）。
2. round1 之外的任何搜索记录（round-2/round-3）本轮限定检索未找到；`primary` 的 frontier 身份行本轮未找到。
3. 无 sampling audit 行 → 无该态的 pool/ceiling 独立复核记录。

是否需要新物理证据：**仅标记——NOT_AUTHORIZED**（`gap_actions.json:3134`；`decisions.csv:35` NONE_JUSTIFIED_YET）。是否缺第二轮搜索属 coverage 裁定范围，本轮不作推断、不提申请。

### 2.4 PC|M_plus（C05）

原始来源：
- `coverage_recheck.json:39-44` → qualified_representatives=["PC|M_plus|46"]、status=PENDING_INDEPENDENT_COVERAGE_AND_IDENTITY_REVIEW。
- `production_ensemble_labels.csv:23`（n_registered=1, n_qc_passed=2, n_deduplicated=0, n_unique=2, n_members=2, pool_limited=false, coverage_status=not_reviewed）。
- `production_ensemble_candidates.csv:40-41`；`dedup.csv:49-50`；`structures.csv:18`（primary）、`:72`（46）。
- `member_statuses.csv:103-104`；`gap_actions.json:3567` 起、`:3646-3648` 三条 action。
- `source_index.json` → `PC|M_plus|46` attempt0 computed kept=true **eligible=true**（job `3720638_4`，opt_log sha `8040d2f4…`、final `5478c71e…`）；`primary` eligible=false。
- `states.json[]` → eligible/strict_kept=["PC|M_plus|46"]、weights=[{46,1}]、category=CONDITIONAL_EVIDENCE_SUFFICIENT、formal_acceptance=NOT_PUBLISHED、lost_old_representatives=["PC|M_plus|primary"]。
- `decisions.csv:41`；`coverage_8.json:163-201`；`frontier_identity_evidence.csv:62-63`（46 与 primary 均 verified）。
- 搜索范围：`sampling_conformer_set.csv:18`（唯一结构 r2_c46，source_kind 行内 geometry_relpath=`work/sampling/PC/M_plus/r2_c46/xtbopt.xyz`）；`sampling_index.json:58`（pool_limited_states 含 PC|M_plus）、`:420`（PC 属 executed 集合）；`sampling_audit_3to6.csv` 本轮未找到 PC 行（PC 非 designated 分子）；`coverage_reviews.csv`、`strict_recovery_v1_manifest.csv` 本轮未命中该态。

未确定事项：
1. labels `pool_limited=false` 与 `sampling_index.json` pool_limited_states 含 `PC|M_plus` 是两个口径，本轮未找到二者的对账说明。
2. 无 sampling audit 行 → 无该态独立的 pool/ceiling 复核记录；范围仅有单结构池（r2_c46），是否足以证明覆盖，本轮未找到裁定。
3. `DEC|M_plus` 式的 attempt 覆盖不适用于本态（46 仅 attempt0）；primary 的 `PRIMARY_IDENTITY_SEPARATE_SOURCE_NOT_REVERIFIED` 仍未闭合。

是否需要新物理证据：**仅标记——NOT_AUTHORIZED**（`gap_actions.json:3648`；`decisions.csv:41` NONE_JUSTIFIED_YET）。

### 2.5 TMP|M（C17）

原始来源：
- `coverage_recheck.json:59-64` → qualified_representatives=["TMP|M|27"]、status=PENDING_INDEPENDENT_COVERAGE_AND_IDENTITY_REVIEW。
- `production_ensemble_labels.csv:13`（n_registered=2, n_qc_passed=2, n_deduplicated=1, n_unique=2, n_members=2, pool_limited=false, coverage_status=not_reviewed）。
- `production_ensemble_candidates.csv:27-29`（primary、48、27）；`dedup.csv:27-29`；`structures.csv:13`（primary）、`:64`（48 attempt0 superseded）、`:65`（27）、`:140`（48 attempt1）。
- `member_statuses.csv:131-133`（27 ISOLATED_CONDITIONAL_POOL；48 EVIDENCE_MISSING；primary MEASURED_NOT_MET;…）。
- `gap_actions.json:4317` 起、`:4427-4429` 三条 action。
- `source_index.json` → `TMP|M|27` attempt0 computed kept=true **eligible=true**（job `3718293_15`，opt_log sha `7dec22f1…`、final `213005d2…`）；`48` attempt0 superseded / attempt1 computed eligible=false（FIVE_ITEM_MISSING:energy_change_Eh）；`primary` eligible=false。
- `states.json[]` → eligible/strict_kept=["TMP|M|27"]、weights=[{27,1}]、category=CONDITIONAL_EVIDENCE_SUFFICIENT、formal_acceptance=NOT_PUBLISHED、lost_old_representatives=["TMP|M|primary"]。
- `decisions.csv:48`；`coverage_8.json:243-281`；`frontier_identity_evidence.csv:80-81`（27 与 primary verified；本轮未找到 48 行）。
- 搜索范围：`sampling_conformer_set.csv:41-42`；`sampling_audit_3to6.csv:14`（sampling_limited：pool holds only 2 independent minima…）；`sampling_index.json:62`（pool_limited_states 含 TMP|M）；`coverage_reviews.csv`、`strict_recovery_v1_manifest.csv` 本轮未命中该态。

未确定事项：
1. `sampling_audit_3to6.csv:14` 的 sampling_limited 结论基于过期 structure-ledger 哈希（§3.2），按 `remote_closure_20261103/README.md:43` 不可沿用；独立重核该结论不在本任务范围（禁止新增计算）。
2. `TMP|M|48` 缺 energy_change_Eh 且被判为 27 的重复；若 27 被否定，48 能否补位——本轮未找到裁定记录。
3. 本轮未找到 `TMP|M|48` 的 frontier 身份行。

是否需要新物理证据：**仅标记——NOT_AUTHORIZED**（`gap_actions.json:4429`；`decisions.csv:48` NONE_JUSTIFIED_YET）。

---

## 3. 跨态共通限制

### 3.1 五态 coverage 记录状态（原始来源）
- `verification_20261103/README.md:15`：五态仍需独立身份与 coverage 核验；`:21`：**当前不能证明任何一态已穷尽现有文件与候选路径，因此未确认最小新增实验清单或预算**；`:23`：历史正式状态 45 accepted / 2 limited / 1 provisional 未改变，该文件不是正式晋升。
- `coverage_recheck.json:19/27/35/43/63`：五态均 `PENDING_INDEPENDENT_COVERAGE_AND_IDENTITY_REVIEW`，`zero_compute_action="verify terminal identity and coverage evidence before formal admission"`。
- `production_ensemble_labels.csv:13/15/23/34/39`：`coverage_status=not_reviewed`、`coverage_review_id` 空。
- `coverage_reviews.csv`（14 条 review，行 2-15）本轮**未找到**五态任何一行——据此只能说"本轮限定范围内未找到五态的 coverage review 记录"，不得写成"五态不存在 review"。
- `coverage_8.json` 五态：`registered_starts=[]`、`qualified_registered_starts=[]`、`search_outcome="not_searched"`、`route="pending"`、`coverage_gate="HELD"`、`full_generator_isolated_diagnostic.adjudicated_gate="HELD_PENDING_OR_INDEPENDENT_REVIEW"`。
- `strict_recovery_v1_manifest.csv`（13 数据行）本轮未找到五态任何一行（命中的只有 DEC|M、TMP|LiM_2plus、TMP|LiM_plus、TMP|M_plus）。
- `states.json` 五态：`category="CONDITIONAL_EVIDENCE_SUFFICIENT"`、`formal_acceptance="NOT_PUBLISHED"`、`old_coverage_claim_survives=false`、`old_coverage_review_reusable_without_recheck=false`。
- `candidate_evaluation.json`：11 条候选，键均为 DMC/EC 候选，`present:false` 对五态全部成立——五态不在该候选评估范围内。
- `verification_20261103/README.md:14` 与 `remote_closure_20261103/README.md:28`：旧 resolved 结论不得继承，8 态 coverage 结论均 unresolved、无新增 accepted。
- `remote_closure_20261103/README.md:43`（必须沿用的上游警示）：五态覆盖范围绑定尚未完成，应对照 sampling_conformer_set / sampling_index / sampling_audit_index / 原候选登记 / 原起点几何逐态绑定；**旧 sampling 审核索引引用的结构账本哈希已过期，不能直接沿用其状态结论**；没有理由先申请新计算。

### 3.2 哈希独立复核（本轮实测）
- `sampling_audit_index.json` 记录 `inputs.production_ensemble_structures.csv = 3f2c692d2207d935347c3508e095e183e7f25a192952dc84b430b2d023d55df6`，而当前文件实测为 `3a795ce8680e84ec0e60ef0411c78fb8236daf492e8647ebec25efbebc96732b` → **不一致，过期已被独立证实**；故 `sampling_audit_3to6.csv` 中五态相关状态结论（executable_partial / sampling_limited）不得沿用。
- `run_06c49d9e7ebe0688/source_index.json.input_sha256` 记录 structures=`3a795ce8…`、candidates=`6096cd12…`、dedup=`1f3ea929…`、labels=`c21003f5…`、coverage_reviews=`e89188f6…`，均与本轮实测一致 → 严格重建 run 使用的是当前账本。
- `sampling_audit_index.json` 记录 `inputs.sampling_conformer_set.csv = b4665e14…`，与当前实测一致 → 该文件未变。
- `frontier_identity_evidence.csv` 的 `sha256_geom_xyz` 与 `production_ensemble_structures.csv.final_geometry_sha256` 对五个合格代表逐一相等（771a8046 / 8e9479db / fc19de61 / 5478c71e / 213005d2）→ 几何链一致。
- **哈希差异待解释**：`frontier_identity_evidence.csv.sha256_job_log` 与 `structures.log_sha256` / `source_index.opt_log_sha` 对同一成员不等（例：TMP|M|27 = `bdd901b3…` vs `7dec22f1…`；DEC|LiM_2plus|c02 = `e2cc3c7d…` vs `c400ff83…`）。两个哈希各自都被记录为已核，但其指向文件的关系本轮未找到说明 → 列为未确定事项，不作调和、不作取舍。

### 3.3 作业与身份的口径
- 五个合格代表的 job.log 磁盘存在性本轮逐一核验：`3723647_9`、`3721460_1`、`3723647_3`、`3720638_4`、`3718293_15` 全部 EXISTS。
- `run_06c49d9e7ebe0688/README.md`（五态行）：DEC|LiM_2plus accepted 2/1、DEC|M_plus accepted 3/1、GBL|LiM_plus accepted 2/1、PC|M_plus accepted 2/1、TMP|M accepted 3/1（"当前成员/合格"），并注明 CONDITIONAL_EVIDENCE_SUFFICIENT 仍需独立身份/协议与 coverage 复核，不是正式释放。
- 全部 primary 均未通过严格身份/协议门（`MEASURED_NOT_MET;IDENTITY_PENDING;PROTOCOL_REVIEW` + `PRIMARY_IDENTITY_SEPARATE_SOURCE_NOT_REVERIFIED`），故各态条件池仅含1 个合格代表。

---

## 4. 引用文件 SHA256 清单（本轮实测）

| 文件 | SHA256 |
|---|---|
| `outputs/physics_completion/ensembles/production_ensemble_structures.csv` | `3a795ce8680e84ec0e60ef0411c78fb8236daf492e8647ebec25efbebc96732b` |
| `outputs/physics_completion/ensembles/production_ensemble_candidates.csv` | `6096cd125210e0fe8428d526e3932cc56489ba92c2d11d4a2d84084434e58efa` |
| `outputs/physics_completion/ensembles/production_ensemble_dedup.csv` | `1f3ea92971d9725f407109d6a3c121b18aa4af13f80331e891ee612247377c04` |
| `outputs/physics_completion/ensembles/production_ensemble_labels.csv` | `c21003f5e18a2faaf4e3c8e91c379ea3ab16659706d13786ed25df0038ae0c80` |
| `outputs/physics_completion/recovery/coverage_reviews.csv` | `e89188f6eac28bbf2dd309a95ec19ea9b1cc78969a262883820f939eec28ba40` |
| `outputs/physics_completion/recovery/strict_recovery_v1_manifest.csv` | `aab933144ad63d6af1b94b6de4d1f3bdec840b1986c85455357363bceb5ef1a0` |
| `outputs/physics_completion/frontier/frontier_identity_evidence.csv` | `0f8a8653b5285e0e786e62f1f3c03d021b8edc48502a56e768dba46d7ebcc5c6` |
| `outputs/physics_completion/sampling/sampling_conformer_set.csv` | `b4665e14dc3f2cc337e2229190115f52f98725be09bec1f49d0b7099b91b4f4c` |
| `outputs/physics_completion/sampling/sampling_index.json` | `6aa3bf194a1bbf5ee3210c6cdcdd72af14912f8b632c1543732aba50d2de9195` |
| `outputs/physics_completion/sampling/sampling_audit_index.json` | `c0180ae81d69851625c0b9e980ac46da9de61d6e62dfae055f9beab58a134fa3` |
| `outputs/physics_completion/sampling/sampling_audit_3to6.csv` | `a1a66fe9f9ce9e22e3efbf16178410a91b1b3c9d6d41cddf3aba6c3b068549c0` |
| `outputs/physics_completion/li_motif_sampling/li_motif_screen.csv` | `41a285361df46eef68423eff8ce64e669f2d4f2a1623e09b1011b8ba912d162a` |
| `outputs/physics_completion/li_motif_sampling/motif_plan.csv` | `5cb13ec62f30246027bf5f4fff226337a31ec55d620ef40d5ec3cce1764d2801` |
| `outputs/physics_completion/li_motif_sampling/li_motif_round2_exec.csv` | `e587000bfb93580f75723a93528b5b8708f6e2f37f696b862cb65f37a5b47c4f` |
| `outputs/physics_completion/li_motif_sampling/li_motif_plan_round2.csv` | `18896217dc62363a4569e7a722c216662a05df4dfeac17bf1e710ecb9b2bc22a` |
| `docs/handoffs/strict_rebuild_20261103/verification_20261103/README.md` | `61e930b842abc97c082e11e9fa0662f356e25be3411aabce0774e4b3206ddf3e` |
| `docs/handoffs/strict_rebuild_20261103/verification_20261103/coverage_recheck.json` | `182d32aba5e99e7ff13f7f922f42d4e3fe473f26e8a276710419ddcc1cbc8a6d` |
| `docs/handoffs/strict_rebuild_20261103/verification_20261103/member_statuses.csv` | `2875d108c3236e452dedc06c9eca3c3b6f9445bbf33de432cf289899a4708b19` |
| `docs/handoffs/strict_rebuild_20261103/remote_closure_20261103/README.md` | `a1aa76672e6f01e8bad9d457a1a1b6936f20a2f70e43e5ac6db64358342e353c` |
| `docs/handoffs/strict_rebuild_20261103/README.md` | `c0668012adf51e7db081158265373ec2e04b10e91be81be75ce76ca9af99bda4` |
| `docs/handoffs/strict_rebuild_20261103/run_06c49d9e7ebe0688/states.json` | `779dda1c3fe81718806484b675d4903f144ec945e6fce3d16ea8848b6adfbfac` |
| `docs/handoffs/strict_rebuild_20261103/run_06c49d9e7ebe0688/gap_actions.json` | `e7ce5ba931dc42157ce2dd12cd7fbd27d6776ade59d274fa1f537620172a9113` |
| `docs/handoffs/strict_rebuild_20261103/run_06c49d9e7ebe0688/source_index.json` | `3346f78f0e280bf910c33298845215a8afc0056c69576d97d79b2d11a05b5caf` |
| `docs/handoffs/strict_rebuild_20261103/recovery_decisions_20261103_v9/decisions.csv` | `ac430d378c05444c9f2afc08b0ac477b6221ff4d64a78dedd7d3f8136cc1ae5d` |
| `docs/handoffs/strict_rebuild_20261103/recovery_decisions_20261103_v9/coverage_8.json` | `26ccc6e50a510a8a4f37c35b1bd06bd2e417f63ec7d0827366a20d03f36f2ba7` |
| `docs/handoffs/strict_rebuild_20261103/recovery_decisions_20261103_v9/README.md` | `0dd8c7cf2204de4590bcc1c549d193717b9447957e04ba94b664308ccf9d3f44` |

---

## 5. 结论边界

1. 五态判定均为「证据已有但未绑定」；**未发现任何一态被本任务判为「覆盖证据不足」**，但范围证据强度不等：DEC|LiM_2plus、DEC|M_plus 有 round-1 + round-2 与 audit 记录，TMP|M 有 conformer + audit 记录（audit 结论过期不可沿用），PC|M_plus 只有单结构 conformer 池记录，GBL|LiM_plus 只有 round-1 motif 筛选记录（round-2 与 audit 记录本轮限定检索未找到）。
2. 一切"未找到"均为**限定检索范围内的未找到**，不构成"不存在"的断言；本任务未补写任何搜索结论。
3. 是否需要新物理证据：五态一致标记 **NOT_AUTHORIZED**（`gap_actions.json` 各态 `new_physical_evidence`），`decisions.csv` 预算一律 `NONE_JUSTIFIED_YET`，且 `verification_20261103/README.md:21` 明示未确认最小新增实验清单或预算——本文件不申请、不建议任何新计算。
4. 本文件不是正式准入、正式晋升或用户签认；五态仍为 `PENDING_INDEPENDENT_COVERAGE_AND_IDENTITY_REVIEW`，须由独立角色完成身份与 coverage 绑定复核。
