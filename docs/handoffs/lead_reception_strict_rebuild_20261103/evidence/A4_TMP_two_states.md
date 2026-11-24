# A4 · TMP 两态（`TMP|M_plus`、`TMP|LiM_2plus`）承重成员与缺口清单

## 0. 元信息与方法红线

| 项 | 内容 |
|---|---|
| 任务 | A4：对 `TMP|M_plus` 与 `TMP|LiM_2plus` 逐态指名**承重成员**与**缺失项**；先列既有证据，再给最小补证（证据类型 + 最小范围，**不构成计算申请**） |
| 仓库根 | `E:\Claude Code\电解液溶剂-HB\电解液溶剂HB-Code` |
| 本轮动作 | 只读核验；未修改任何既有文件、未提交作业、未新增计算；本报告是新增文件之一 |
| 输入快照 | `coverage_recheck.json` / `member_statuses.csv` = 2026-11-03 09:19；`coverage_8.json` / `decisions.csv` = 2026-11-03 09:57；`candidate_sources.json` = 2026-11-03 10:30；`eight_admission_v2/*` = 2026-11-03 11:25；`coverage_reviews.csv` = 2026-11-02 15:45；`production_ensemble_labels.csv` = 2026-11-02 18:36 |
| 红线 1 | **不把任何缺项归因于数值误差**（下文所有“缺”均为登记、身份、范围、审查状态） |
| 红线 2 | 限定来源的“未找到” ≠ 身份失败；远端状态 `INACCESSIBLE_NOT_VERIFIED`，不推断远端证据存在或不存在 |
| 红线 3 | 不用数值 QC 替代身份 / coverage 结论 |
| 红线 4 | 最小补证只写“证据类型 + 最小范围”，逐条标注 **不构成计算申请** |

---

## 1. 一句话结论（逐态）

| 态 | 承重成员（严格侧） | 缺失项（门） | 最小补证一句话（**不构成计算申请**） |
|---|---|---|---|
| **`TMP|M_plus`** | `TMP|M_plus\|27`（严格合格池唯一成员；前沿身份链 `FROZEN_FRONTIER_CHAIN_VERIFIED`） | 已登记起点 `c10`、`r3_c42` 均不合格（`qualified_registered_starts=[]`）→ `route=unresolved_qc`；`r3_c42` 五项缺 `energy_change_Eh`；严格口径去重簇/搜索范围未重建；生产 review 用 `r3_c42` 承重且 `n_unique=3` 与严格池不一致 | 回收既有 `r3_c42` 单份 `job.log` 收敛表中的 `energy_change_Eh` 字段 + 以本态 5 个成员的既有几何重建去重簇/合格起点登记 + 出具生产与严格并列的裁定记录（范围：3 组既有材料，**不构成计算申请**） |
| **`TMP|LiM_2plus`** | `TMP|LiM_2plus\|c13`（严格合格池唯一成员；前沿身份链 `FROZEN_FRONTIER_CHAIN_VERIFIED`） | 已登记起点 `r3m_c00` 物种身份未核（`SPECIES_IDENTITY_UNVERIFIED`）→ `qualified_registered_starts=[]` → `route=unresolved_qc`；`c08` 登记/执行未闭合（`rescue_budget_exhausted`）；本态未进入版本化搜索范围；生产 review 用 `r3m_c00` 承重且 `n_unique=3` 与严格池不一致 | 核验 `r3m_c00` 物种身份的既有来源（前沿登记行 73 + 前沿腿行 73 + 任务目录四文件重哈希）+ 以本态 3 个 unique 成员的既有几何重建去重簇 + 出具 `c13` 态级身份裁决记录（范围：3 组既有材料，**不构成计算申请**） |

---

## 2. 承重成员明细

### 2.1 `TMP|M_plus`

| 成员 | 角色 | 严格状态（`member_statuses` 行） | 具体原因（原文） | 关键日志 / 几何来源 | 实测 SHA256（= dispositions 记录值） | 来源（路径 + 行/键） |
|---|---|---|---|---|---|---|
| **`TMP|M_plus\|27`** | **严格侧唯一合格代表（承重）**；生产去重中亦为 unique 成员 | 行 126：`old_kept=True, isolated_eligible=True` → `ISOLATED_CONDITIONAL_POOL`（无缺项原因） | — | `work/hpc_production_ensemble_r1_continuation2/tasks/TMP/M_plus__27/snapshots/3725969_1/job.log` | `22089565df59b0ef2f2ae8436e848ed6276bdee15e324a478090be1b6b09b0b9`（记录 `22089565…b0b9` 一致） | `member_statuses.csv:126`；`member_terminal_dispositions.json` 键 `TMP|M_plus\|27`；`coverage_8.json` 键 `[7].representatives` |
| `TMP|M_plus\|27` 身份门 | 前沿身份链 | — | `FROZEN_FRONTIER_CHAIN_VERIFIED`（`geometry_hash_bound=true`、`raw_four_files_rehashed=true`） | 前沿目录 `work/hpc_frontier_localization_v1/tasks/TMP__M_plus__27/`（存在） | 登记表行 77 四哈希：`job.inp=d692e3d1…`、`geom=50553079…`、`job_log=996ed4b1…`、`molden=604f3227…`；腿表行 77 `geometry_sha256=582e33c6…`（`geometry_verified=true`） | `frontier_identity_evidence.csv:77`；`frontier_legs.csv:77`；`coverage_8.json` 键 `[7].identity_evidence[0]` |
| `TMP|M_plus\|r3_c42` | **生产 review 的 `kept_pool_evidence`（生产侧承重）**；已登记 start_2；严格不合格 | 行 130：`old_kept=True, isolated_eligible=False` → `EVIDENCE_MISSING` | `FIVE_ITEM_MISSING:energy_change_Eh` | `work/hpc_production_ensemble_strict_recovery_v1_reopt_v2/tasks/TMP/M_plus__r3_c42/snapshots/3744604_0/job.log`（attempt 11，`historical_status=computed`，`failure_class=computed_no_failure`） | `b76ab94e3ad0eadbc79b9817ef7dfa0252043be4b6d64945ee11c96d61fc416e`（一致） | `member_statuses.csv:130`；dispositions 键 `TMP|M_plus\|r3_c42`；`coverage_reviews.csv:15` |
| `TMP|M_plus\|c10` | 已登记 start_1（历史 `unused_pool_basin`）；严格不合格 | 行 128：`old_kept=False, isolated_eligible=False` → `REGISTRATION_OR_EXECUTION_OPEN` | `NOT_CURRENT_NUMERIC_MEMBER`；dispositions：attempt 11 `technical_complete_qc_failed`、`failure_class=verytight_convergence`、`rescue_budget_exhausted` | `work/hpc_production_ensemble_strict_recovery_v1_reopt_v2/tasks/TMP/M_plus__c10/snapshots/3744604_1/job.log` | `79d29c37a2a1c4ee93587ffa30a0316fa52585df83cf31ae9bc1ff50d74ec8ac`（一致） | `member_statuses.csv:128`；dispositions 键 `TMP|M_plus\|c10` |
| `TMP|M_plus\|33` | 生产池成员（round1_extra）；严格不合格 | 行 127：`old_kept=False, isolated_eligible=False` → `REGISTRATION_OR_EXECUTION_OPEN` | `NOT_CURRENT_NUMERIC_MEMBER`；dispositions：`technical_complete_qc_failed`、`failure_class=strict_reopt_required`、`rescue_budget_exhausted` | `work/hpc_production_ensemble_r1_continuation2/tasks/TMP/M_plus__33/snapshots/3725969_0/job.log` | `864a901b159b4baa507407af984256c71162d2e8940a729f88f9c401ec7ecdf6`（一致） | `member_statuses.csv:127`；dispositions 键 `TMP|M_plus\|33` |
| `TMP|M_plus\|primary` | 历史簇头 / 生产 unique 成员；严格不合格 | 行 129：`old_kept=True, isolated_eligible=False` → `MEASURED_NOT_MET;IDENTITY_PENDING;PROTOCOL_REVIEW` | `FIVE_ITEM_EXCEEDS_STRICT_LIMIT:*`、`PRINTED_OPT_TOLERANCE_DIFFERS:*`、`PRIMARY_IDENTITY_SEPARATE_SOURCE_NOT_REVERIFIED` | `work/hpc_anfreq_cohort_20261016/hpc_runs/TMP_M_plus/job.log` | `f8f67c8cbf7b56880df81f4d1595c29275b64560ff9689faf7cff3a8e6b251db`（一致） | `member_statuses.csv:129`；dispositions 键 `TMP|M_plus\|primary` |

**严格侧合格成员计数**：`member_statuses.csv` 中 `isolated_eligible=True` 的 `TMP|M_plus` 成员**只有 `27` 一个**（行 126；行 127-130 均为 `False`）。

### 2.2 `TMP|LiM_2plus`

| 成员 | 角色 | 严格状态（行） | 具体原因（原文） | 关键日志 / 几何来源 | 实测 SHA256（= dispositions 记录值） | 来源（路径 + 行/键） |
|---|---|---|---|---|---|---|
| **`TMP|LiM_2plus\|c13`** | **严格侧唯一合格代表（承重）**；生产去重中亦为 unique 成员 | 行 119：`old_kept=True, isolated_eligible=True` → `ISOLATED_CONDITIONAL_POOL`（无缺项原因） | — | `work/hpc_production_ensemble_r1_continuation4/tasks/TMP/LiM_2plus__c13/snapshots/3727606_4/job.log` | `5a0da9c4e3e21754739450b8073fff86f0f902e8aa7095cf5b62bac9b12ca861`（记录 `5a0da9c4…a861` 一致） | `member_statuses.csv:119`；dispositions 键 `TMP|LiM_2plus\|c13`；`coverage_8.json` 键 `[5].representatives` |
| `TMP|LiM_2plus\|c13` 身份门 | 前沿身份链 | — | `FROZEN_FRONTIER_CHAIN_VERIFIED`（`geometry_hash_bound=true`、`raw_four_files_rehashed=true`）；dispositions 备注 `accepted_by_recheck = "accepted by isolation; identity gate remains a separate state decision"` | 前沿目录 `work/hpc_frontier_localization_v1/tasks/TMP__LiM_2plus__c13/`（存在） | 登记表行 71 四哈希：`job.inp=e288a018…`、`geom=b78f3e64…`、`job_log=79a91289…`、`molden=eed383af…`；腿表行 71 `geometry_sha256=b78f3e64…`（与登记 `sha256_geom_xyz` 一致，`geometry_verified=true`） | `frontier_identity_evidence.csv:71`；`frontier_legs.csv:71`；`coverage_8.json` 键 `[5].identity_evidence[0]`；dispositions 键 `TMP|LiM_2plus\|c13` |
| `TMP|LiM_2plus\|r3m_c00` | **生产 review 的 `kept_pool_evidence`（生产侧承重）**；已登记 start_1；严格不合格 | 行 121：`old_kept=True, isolated_eligible=False` → `IDENTITY_PENDING` | `SPECIES_IDENTITY_UNVERIFIED`（**物种身份门**，不是数值五项缺失） | `work/hpc_production_ensemble_strict_recovery_v1_cont5/tasks/TMP/LiM_2plus__r3m_c00/snapshots/3742333_0/job.log`（attempt 5，`historical_status=computed`） | `faf60e029ee515ec900b4dfe9f1dde26f2490c4291b399af67d0b5debd7b9c1b`（一致） | `member_statuses.csv:121`；dispositions 键 `TMP\|LiM_2plus\|r3m_c00` |
| `TMP|LiM_2plus\|r3m_c00` 前沿登记 | 电子前沿身份（**另一门**） | — | 前沿登记表行 73 `verified`；腿表行 73 `geometry_verified=true`；前沿任务目录 `TMP__LiM_2plus__r3m_c00` 存在 → 与上一行的 `SPECIES_IDENTITY_UNVERIFIED` 属**两个不同门**，本轮未见裁决文档 | 同上 | 登记表行 73 四哈希：`job.inp=990dbd47…`、`geom=1f39114c…`、`job_log=75f8e20d…`、`molden=179ef31f…`；腿表行 73 `geometry_sha256=1f39114c…` | `frontier_identity_evidence.csv:73`；`frontier_legs.csv:73` |
| `TMP|LiM_2plus\|c08` | 生产池成员（round1_extra）；严格不合格 | 行 118：`old_kept=False, isolated_eligible=False` → `REGISTRATION_OR_EXECUTION_OPEN` | `NOT_CURRENT_NUMERIC_MEMBER`；dispositions：attempt 11 `technical_complete_qc_failed`、`failure_class=strict_reopt_required`、`rescue_budget_exhausted` | `work/hpc_production_ensemble_strict_recovery_v1_reopt_v2/tasks/TMP/LiM_2plus__c08/snapshots/3744604_2/job.log` | `04ba6d5ab2e933250e1d2b4f979e4091e87a38aaf638cc2fc53eb81aa3e5f173`（一致） | `member_statuses.csv:118`；dispositions 键 `TMP\|LiM_2plus\|c08` |
| `TMP|LiM_2plus\|primary` | 历史簇头 / 生产 unique 成员；严格不合格 | 行 120：`old_kept=True, isolated_eligible=False` → `MEASURED_NOT_MET;IDENTITY_PENDING;PROTOCOL_REVIEW` | `FIVE_ITEM_EXCEEDS_STRICT_LIMIT:*`、`PRINTED_OPT_TOLERANCE_DIFFERS:*`、`PRIMARY_IDENTITY_SEPARATE_SOURCE_NOT_REVERIFIED` | `work/hpc_anfreq_cohort_20261016/hpc_runs/TMP_LiM_2plus/job.log` | `122334b2dca238c49b1ac47ad5b65d47c027eb149d979c15bc702fb6d727fd0d`（一致） | `member_statuses.csv:120`；dispositions 键 `TMP\|LiM_2plus\|primary` |

**严格侧合格成员计数**：`isolated_eligible=True` 的 `TMP|LiM_2plus` 成员**只有 `c13` 一个**（行 119；行 118、120、121 均为 `False`）。

---

## 3. 缺失项清单（缺什么 / 卡哪个门 / 来源）

### 3.1 `TMP|M_plus`

| # | 缺失项 | 卡住的门 | 现有记录（原文/实测） | 来源（路径 + 行/键） | 文件 SHA256 |
|---|---|---|---|---|---|
| M-1 | **合格的已登记起点**：`registered_starts=[c10, r3_c42]`，但 `qualified_registered_starts=[]` | coverage 路由门 | `route=unresolved_qc`、`search_outcome=new_minima_found`、`coverage_gate=HELD` | `recovery_decisions_20261103_v9/coverage_8.json` 键 `[7].registered_starts / .qualified_registered_starts / .route / .coverage_gate` | `26ccc6e50a510a8a4f37c35b1bd06bd2e417f63ec7d0827366a20d03f36f2ba7` |
| M-2 | `r3_c42` 的五项证据缺 `energy_change_Eh` | 成员严格证据门（`EVIDENCE_MISSING`） | `FIVE_ITEM_MISSING:energy_change_Eh`；`isolated_eligible=False` | `member_statuses.csv:130`；dispositions 键 `TMP\|M_plus\|r3_c42` | `2875d108c3236e452dedc06c9eca3c3b6f9445bbf33de432cf289899a4708b19` |
| M-3 | 严格口径的**去重簇与搜索范围重建**未产出 | coverage 复核门 | `status=UNRESOLVED_RECHECK_REQUIRED`；`reason=old claim depends on a member absent from strict qualified representatives`；`zero_compute_action=reconstruct search scope, qualified starts and dedup clusters; do not inherit old resolved` | `verification_20261103/coverage_recheck.json:66-77` | `182d32aba5e99e7ff13f7f922f42d4e3fe473f26e8a276710419ddcc1cbc8a6d` |
| M-4 | 正式生成器侧的覆盖判定未闭合 | coverage 生成器门 | `route=pending`、`verdict=pending`、`n_unique_after=0`、`kept_pool_evidence` 为空、`historical_limitation=frozen_basin`、`evidence_note`“no recovery member registered yet; a versioned new search must register a start before any verdict” | `remote_closure_20261103/eight_admission_v2/full_generator_8.json` 键 `[3]` | `acd48d381e71d8939b0ecbc24b077919a96f8762053e0581c06309e18d9ba15c` |
| M-5 | **生产与严格的承重成员不一致** | 承重审计一致性 | 生产：`kept_pool_evidence=TMP\|M_plus\|r3_c42`、`route=multi_basin_coverage`、`n_unique_after=3`、`verdict=resolved`、`review_version=coverage_review_v2_dedup_aware_20261027`；严格：唯一合格代表 `TMP\|M_plus\|27` | `outputs/physics_completion/recovery/coverage_reviews.csv:15`；`member_statuses.csv:126-130` | `e89188f6eac28bbf2dd309a95ec19ea9b1cc78969a262883820f939eec28ba40` |
| M-6 | 生产 `n_unique=3` 的成员构成中含严格不合格成员 | 同上 | dedup 行 53-55：`primary`、`27`、`r3_c42` 三者 `kept=true, unique`；labels 行 25：`n_registered=4, n_qc_passed=3, n_qc_failed=2, n_deduplicated=0, n_unique=3, n_members=3, coverage_status=resolved_by_review` | `production_ensemble_dedup.csv:53-55`；`production_ensemble_labels.csv:25` | `1f3ea92971d9725f407109d6a3c121b18aa4af13f80331e891ee612247377c04`；`c21003f5e18a2faaf4e3c8e91c379ea3ab16659706d13786ed25df0038ae0c80` |
| M-7 | 搜索命中的新最小值未全部进入成员登记 | 登记门 | `per_state_new_minima={"TMP\|M_plus": 2}`，`search_pool` 两条为 `r3_c42`、`r3_c20`；`r3_c20` 在 `member_statuses.csv` 与 `production_ensemble_dedup.csv` 中 **grep 0 命中** | `strict_recovery_v1_search_index.json` 键 `per_state_new_minima` / `states_searched`；`strict_recovery_v1_search_pool.csv:2-3` | `932a454a4aede0dc1ec254d8f3f1c4814edd38bc8431c27d741960ddf39f7dc3`；`8ae4bd1372d8376eafb56199f49058678f7a13291a3b4464d173f04de645590f` |
| M-8 | 若想让 `primary` 承重 | 身份门 + 数值/协议门 | `MEASURED_NOT_MET;IDENTITY_PENDING;PROTOCOL_REVIEW`，含 `PRIMARY_IDENTITY_SEPARATE_SOURCE_NOT_REVERIFIED` | `member_statuses.csv:129` | `2875d108…` |

### 3.2 `TMP|LiM_2plus`

| # | 缺失项 | 卡住的门 | 现有记录（原文/实测） | 来源（路径 + 行/键） | 文件 SHA256 |
|---|---|---|---|---|---|
| L-1 | **合格的已登记起点**：`registered_starts=[r3m_c00]`，但 `qualified_registered_starts=[]` | coverage 路由门 | `route=unresolved_qc`、`search_outcome=released_by_review`、`coverage_gate=HELD` | `recovery_decisions_20261103_v9/coverage_8.json` 键 `[5]` | `26ccc6e50a510a8a4f37c35b1bd06bd2e417f63ec7d0827366a20d03f36f2ba7` |
| L-2 | `r3m_c00` 的**物种身份**未核（前沿电子身份登记却为 verified，两门并列） | 物种身份门 | `IDENTITY_PENDING` / `SPECIES_IDENTITY_UNVERIFIED`，`isolated_eligible=False` | `member_statuses.csv:121`；`frontier_identity_evidence.csv:73`（`verified`） | `2875d108…`；`0f8a8653b5285e0e786e62f1f3c03d021b8edc48502a56e768dba46d7ebcc5c6` |
| L-3 | 严格口径的**去重簇与搜索范围重建**未产出 | coverage 复核门 | `status=UNRESOLVED_RECHECK_REQUIRED`；`zero_compute_action=reconstruct search scope, qualified starts and dedup clusters; do not inherit old resolved` | `coverage_recheck.json:46-57` | `182d32aba5e99e7ff13f7f922f42d4e3fe473f26e8a276710419ddcc1cbc8a6d` |
| L-4 | 正式生成器侧的覆盖判定未闭合 | coverage 生成器门 | `route=pending`、`verdict=pending`、`registered_starts=[r3m_c00]`、`n_unique_after=0`、`evidence_note`“no recovery member registered yet; a versioned new search must register a start before any verdict” | `full_generator_8.json` 键 `[1]` | `acd48d38…` |
| L-5 | **本态未进入版本化搜索范围** | 搜索范围门 | `states_searched=["AN\|M_plus","DMC\|M_plus","EMC\|M_plus","TMP\|M_plus"]`（**不含 `TMP\|LiM_2plus`**）；manifest：`start_1_basin=r3m_c00`、`max_new_starts=0`、`search_outcome=released_by_review`、`released=true`、`preferred_path` 空 | `strict_recovery_v1_search_index.json` 键 `states_searched`；`strict_recovery_v1_manifest.csv`（`name=TMP,state=LiM_2plus` 行） | `932a454a…`；`aab933144ad63d6af1b94b6de4d1f3bdec840b1986c85455357363bceb5ef1a0` |
| L-6 | `c08` 登记/执行未闭合（第二现成成员不可用） | 登记与执行门 | `REGISTRATION_OR_EXECUTION_OPEN` / `NOT_CURRENT_NUMERIC_MEMBER`；`technical_complete_qc_failed`、`failure_class=strict_reopt_required`、`rescue_budget_exhausted` | `member_statuses.csv:118`；dispositions 键 `TMP\|LiM_2plus\|c08` | `2875d108…` |
| L-7 | **生产与严格的承重成员不一致** | 承重审计一致性 | 生产：`kept_pool_evidence=TMP\|LiM_2plus\|r3m_c00`、`route=multi_basin_coverage`、`resolution_path=released`、`n_unique_after=3`、`verdict=resolved`；严格：唯一合格代表 `TMP\|LiM_2plus\|c13` | `coverage_reviews.csv:13`；`member_statuses.csv:119-121` | `e89188f6…` |
| L-8 | 生产 `n_unique=3` 含严格不合格成员 | 同上 | dedup 行 102-104：`r3m_c00`、`c13`、`primary` 三者 `kept=true, unique`；labels 行 49：`n_registered=3, n_qc_passed=3, n_qc_failed=1, n_deduplicated=0, n_unique=3, n_members=3, coverage_status=resolved_by_review` | `production_ensemble_dedup.csv:102-104`；`production_ensemble_labels.csv:49` | `1f3ea929…`；`c21003f5…` |
| L-9 | 若想让 `primary` 承重 | 身份门 + 数值/协议门 | `MEASURED_NOT_MET;IDENTITY_PENDING;PROTOCOL_REVIEW`，含 `PRIMARY_IDENTITY_SEPARATE_SOURCE_NOT_REVERIFIED` | `member_statuses.csv:120` | `2875d108…` |

---

## 4. 同一状态的路由视图对照（并列，不裁定）

| 视图 | 输入语义 / 时间 | `TMP|M_plus` | `TMP|LiM_2plus` | 来源 |
|---|---|---|---|---|
| A 生产正式 review | `coverage_review_v2_dedup_aware_20261027`；2026-11-02 15:45 | `multi_basin_coverage` / `resolved`，kept=`r3_c42`，starts=`c10;r3_c42`，`n_unique_after=3`，`resolution_path=frozen_basin`，`historical_n_limited=2` | `multi_basin_coverage` / `resolved`，kept=`r3m_c00`，starts=`r3m_c00`，`n_unique_after=3`，`resolution_path=released`，`historical_n_limited=1` | `coverage_reviews.csv:15`、`:13` |
| B 生产标签 | 2026-11-02 18:36 | `coverage_status=resolved_by_review`、`n_unique=3` | `coverage_status=resolved_by_review`、`n_unique=3` | `production_ensemble_labels.csv:25`、`:49` |
| C 隔离 `coverage_route`（v9） | 严格池 + 历史 dedup；2026-11-03 09:57 | `route=unresolved_qc`、`gate=HELD`、identity `FROZEN_FRONTIER_CHAIN_VERIFIED` | `route=unresolved_qc`、`gate=HELD`、identity `FROZEN_FRONTIER_CHAIN_VERIFIED` | `coverage_8.json` 键 `[7]`、`[5]` |
| D 完整生成器（最新严格入口） | `coverage_review_v3_strict_basin_guard_20261103`；2026-11-03 11:25 | `route=pending` / `verdict=pending`、`resolution_path=frozen_basin`、`n_unique_after=0` | `route=pending` / `verdict=pending`、`n_unique_after=0` | `full_generator_8.json` 键 `[3]`、`[1]` |
| E 独立严格复核 | 2026-11-03 09:19 | `UNRESOLVED_RECHECK_REQUIRED`，合格代表 `[TMP\|M_plus\|27]` | `UNRESOLVED_RECHECK_REQUIRED`，合格代表 `[TMP\|LiM_2plus\|c13]` | `coverage_recheck.json:66-77`、`:46-57` |
| F 决策账本 | `decisions.csv`；2026-11-03 09:57 | 行 49：`closed_gates` 含“前沿身份链”；`remaining_stop`“coverage 路由 unresolved_qc，正式承重审计未闭合”；`new_computation_budget=NONE_JUSTIFIED_YET` | 行 46：`closed_gates` 含“前沿身份链”；`remaining_stop`“coverage 路由 unresolved_qc，正式承重审计未闭合”；`new_computation_budget=NONE_JUSTIFIED_YET` | `recovery_decisions_20261103_v9/decisions.csv:49`、`:46` |

> 五/六个视图的差异来自输入语义与审查时点不同，**本报告不作裁定，也不归因于数值误差**。

---

## 5. 任务所给“已知线索”核验

| # | 任务线索 | 核验结论 | 证据 |
|---|---|---|---|
| 1 | TMP\|M_plus 历史失败 `c10` / `33` | **证实（表述需更精确）**：两者均 `technical_complete_qc_failed`（`c10` `failure_class=verytight_convergence`；`33` `failure_class=strict_reopt_required`），均 `rescue_budget_exhausted`；严格侧记为 `NOT_CURRENT_NUMERIC_MEMBER` + `REGISTRATION_OR_EXECUTION_OPEN` | dispositions 键 `TMP\|M_plus\|c10` / `TMP\|M_plus\|33`；`member_statuses.csv:127-128` |
| 2 | `r3_c42` 已算但严格证据不足 | **证实**：`historical_status=computed`（attempt 11）、`isolated_eligible=False`、`FIVE_ITEM_MISSING:energy_change_Eh`；日志实测哈希与记录一致 | `member_statuses.csv:130`；dispositions 键 `TMP\|M_plus\|r3_c42`；`b76ab94e…` |
| 3 | 成员 `27` 合格 | **证实**：`isolated_eligible=True`、`ISOLATED_CONDITIONAL_POOL`、前沿身份 `FROZEN_FRONTIER_CHAIN_VERIFIED`、日志哈希一致 | `member_statuses.csv:126`；`frontier_identity_evidence.csv:77`；`22089565…` |
| 4 | TMP\|LiM_2plus 历史失败 `c08` | **证实**：`technical_complete_qc_failed`、`failure_class=strict_reopt_required`、`rescue_budget_exhausted`、`NOT_CURRENT_NUMERIC_MEMBER` | dispositions 键 `TMP\|LiM_2plus\|c08`；`member_statuses.csv:118` |
| 5 | `r2_c48_c00` / `r3m_c00` 已算但严格证据不足 | **需修正**：`r2_c48_c00` 不是严格池成员，而是登记起点 `r3m_c00` 的 seed 几何路径（`work/limotif_r3_recovery/TMP_LiM_2plus@r2_c48/.../r2_c48_c00/xtbopt.xyz`，其 `xtbopt.log` 实测 `c5fe8349f65041a664622081f6f7b1e6a824b9941b3d334153bb4c4cdabbbcc8`）；`r3m_c00` 为 `historical_status=computed` 的已登记起点，严格不合格原因是**物种身份未核**，不是数值五项缺失 | `verification_20261103/candidates.csv:113`；`member_statuses.csv:121` |
| 6 | 成员 `c13` 合格 | **证实**：`isolated_eligible=True`、`ISOLATED_CONDITIONAL_POOL`、前沿身份 `FROZEN_FRONTIER_CHAIN_VERIFIED`、日志哈希一致 | `member_statuses.csv:119`；`frontier_identity_evidence.csv:71`；`5a0da9c4…` |

---

## 6. 任务前提更正（两处）

| # | 任务/既有说法 | 实测事实 | 来源 |
|---|---|---|---|
| C1 | “TMP\|M 已 resolved\_multi\_basin\_coverage” | **`coverage_reviews.csv` 无 `TMP|M` 行**（全表仅 4 条含 TMP：行 13 `TMP\|LiM_2plus`、行 14 `TMP\|LiM_plus`、行 15 `TMP\|M_plus`，另有行 2 `AN\|M_plus`）；`production_ensemble_labels.csv:13` 的 `TMP,M` 为 `coverage_status=not_reviewed`（`n_registered=2, n_qc_passed=2, n_unique=2, n_deduplicated=1`）；严格侧 `TMP\|M` 状态为 `PENDING_INDEPENDENT_COVERAGE_AND_IDENTITY_REVIEW`、路由 `pending` | `coverage_reviews.csv`（全表检索）；`production_ensemble_labels.csv:13`；`coverage_recheck.json:58-65`；`coverage_8.json` 键 `[6]` |
| C2 | “`r2_c48_c00` 是已算但严格证据不足的成员” | 见第 5 节线索 5：`r2_c48_c00` 是 seed 几何路径，非严格池成员；对应成员是 `r3m_c00` | `candidates.csv:113`；`member_statuses.csv:121` |

---

## 7. 未确定事项

| # | 未确定事项 | 为何未定 | 来源 |
|---|---|---|---|
| U1 | `r3m_c00` 的**物种身份门**与**前沿电子身份门**结论不一致（前沿登记 `verified` vs 严格 `SPECIES_IDENTITY_UNVERIFIED`），以哪个为准 | 未见两门的对账/裁决文档；本轮只并列陈述 | `frontier_identity_evidence.csv:73`；`member_statuses.csv:121` |
| U2 | 远端是否存在可关闭上述缺项的既有来源 | `remote.status=INACCESSIBLE_NOT_VERIFIED`，无远端读取；不推断其存在或不存在 | `candidate_sources.json` 键 `remote`；`CANDIDATE_SOURCES.md:11` |
| U3 | 生产 v2 review（`resolved`）与严格 v3 入口（`pending`/`unresolved_qc`）以哪一版为正式 | 未见裁定文档；`AN_ROOT_CAUSE.md:15`“本轮仅运行隔离入口，未生成正式 review” | `AN_ROOT_CAUSE.md:15`；`coverage_reviews.csv:13,15` |
| U4 | 隔离 `coverage_route`（`unresolved_qc`）与完整生成器（`pending`）在同一严格池上给出不同路由的合成规则 | 两者 `latest_members` 输入构造不同，未见合并规则文档 | `coverage_8.json` 键 `[5]/[7]`；`full_generator_8.json` 键 `[1]/[3]` |
| U5 | `r3_c20`（搜索命中的第 2 个新最小值）为何不在成员登记/去重表 | grep 0 命中；未见登记说明 | `search_pool.csv:3`；`member_statuses.csv`（无该行） |
| U6 | `TMP|M_plus` manifest 中 `status=planned` 与 `released=true` 并存 | 字段并存，未见解释 | `strict_recovery_v1_manifest.csv`（`name=TMP,state=M_plus` 行） |
| U7 | `c13` 身份门“态级裁决”（dispositions 备注 `identity gate remains a separate state decision`）是否已完成 | 未见态级身份裁决记录 | dispositions 键 `TMP\|LiM_2plus\|c13` |
| U8 | 搜索协议为 `gas-phase GFN2-xTB --opt tight (screening only, NOT production)`，其结果是否足以支撑目标协议搜索范围 | 明确标注 screening only；未见目标协议层面的范围审查结论 | `strict_recovery_v1_search_index.json` 键 `protocol` |

> 以上均为登记、身份、范围与审查状态的未确定，**无一项归因于数值误差**。

---

## 8. 是否需要新物理证据

| 项 | 结论 |
|---|---|
| 是否主张新增计算 | **否**。两态的 `new_computation_budget` 均为 `NONE_JUSTIFIED_YET`；`AN_ROOT_CAUSE.md:34`“七个 pending…不能自动解释为必须新增计算”；`verification_20261103/README.md:14-15` 只要求“旧 resolved 均不能直接继承”，未要求新算 |
| 边界声明 | 下列补证**全部为既有证据的读取、字段回收、几何重建与并列裁定记录，不构成计算申请**；若执行后仍缺项，再由 Lead 判断是否需要新物理证据 |

### 8.1 `TMP|M_plus` 最小补证（证据类型 + 最小范围；**不构成计算申请**）

| # | 证据类型 | 最小范围 | 关闭哪项缺口 | 是否计算 |
|---|---|---|---|---|
| S1 | 既有日志**字段级回收**：从 `r3_c42` 的单份 `job.log`（attempt 11）收敛表读取 `Energy change` 并绑定哈希 | 1 个日志文件、1 个字段 | M-2 | **不构成计算申请** |
| S2 | **去重簇与合格起点重建留档**：以本态 5 个成员（`primary/27/r3_c42/c10/33`）的既有几何按既有 Kabsch/RMSD 判据（0.35 Å）重跑并留档 | 5 个成员的既有几何 | M-3、M-4 | **不构成计算申请** |
| S3 | **登记核对记录**：核对 `r3_c20` 与 `c10` 的登记/当前数值成员状态来源 | 2 个成员的既有登记记录 | M-1、M-7 | **不构成计算申请** |
| S4 | **并列裁定记录**：生产 v2（kept=`r3_c42`，`n_unique=3`）与严格侧（合格代表=`27`）的输入语义并列与取舍记录 | 2 份既有产物 | M-5、M-6 | **不构成计算申请** |

### 8.2 `TMP|LiM_2plus` 最小补证（证据类型 + 最小范围；**不构成计算申请**）

| # | 证据类型 | 最小范围 | 关闭哪项缺口 | 是否计算 |
|---|---|---|---|---|
| S5 | **物种身份既有来源核验**：核对 `r3m_c00` 的前沿登记行、前沿腿行与任务目录四文件（`job.inp/geom.xyz/job.log/job.molden.input`）重哈希，并与 `SPECIES_IDENTITY_UNVERIFIED` 并列出裁决记录 | 1 个任务目录、4 个文件 + 2 行登记 | L-1、L-2 | **不构成计算申请** |
| S6 | **去重簇重建留档**：以本态 3 个 unique 成员（`r3m_c00/c13/primary`）的既有几何按既有判据重跑并留档 | 3 个成员的既有几何 | L-3、L-4 | **不构成计算申请** |
| S7 | **搜索范围登记核对**：把 `r3m_c00` 与 `c08` 的登记状态绑定到 `strict_recovery_v1_search_index` / manifest 的既有范围记录（本态未在 `states_searched` 内） | 2 份既有文件 | L-5、L-6 | **不构成计算申请** |
| S8 | **并列裁定记录**：生产 v2（kept=`r3m_c00`，`n_unique=3`）与严格侧（合格代表=`c13`）的并列与取舍记录 | 2 份既有产物 | L-7、L-8 | **不构成计算申请** |

---

## 9. 关键文件 SHA256 汇总

| 文件 | SHA256 |
|---|---|
| `docs/handoffs/strict_rebuild_20261103/verification_20261103/coverage_recheck.json` | `182d32aba5e99e7ff13f7f922f42d4e3fe473f26e8a276710419ddcc1cbc8a6d` |
| `docs/handoffs/strict_rebuild_20261103/verification_20261103/member_statuses.csv` | `2875d108c3236e452dedc06c9eca3c3b6f9445bbf33de432cf289899a4708b19` |
| `docs/handoffs/strict_rebuild_20261103/verification_20261103/README.md` | `61e930b842abc97c082e11e9fa0662f356e25be3411aabce0774e4b3206ddf3e` |
| `docs/handoffs/strict_rebuild_20261103/verification_20261103/candidates.csv`（seed 几何登记，行 113） | （与 `coverage_recheck` 同批产物；本轮以行号引用） |
| `docs/handoffs/strict_rebuild_20261103/recovery_decisions_20261103_v9/decisions.csv` | `ac430d378c05444c9f2afc08b0ac477b6221ff4d64a78dedd7d3f8136cc1ae5d` |
| `docs/handoffs/strict_rebuild_20261103/recovery_decisions_20261103_v9/coverage_8.json` | `26ccc6e50a510a8a4f37c35b1bd06bd2e417f63ec7d0827366a20d03f36f2ba7` |
| `docs/handoffs/strict_rebuild_20261103/recovery_decisions_20261103_v9/README.md` | `0dd8c7cf2204de4590bcc1c549d193717b9447957e04ba94b664308ccf9d3f44` |
| `docs/handoffs/strict_rebuild_20261103/blocker_resolution_20261103/AN_ROOT_CAUSE.md` | `394a7ad2467123351292555ee1d9a1d018a500bca7bcf475a24246ec4c81e92c` |
| `docs/handoffs/strict_rebuild_20261103/blocker_resolution_20261103/CANDIDATE_SOURCES.md` | `64fa07bf8b518b0235abaffe6acd6830a8a32d12a8471276d2f19af391d666f4` |
| `docs/handoffs/strict_rebuild_20261103/blocker_resolution_20261103/candidate_sources.json` | `3bccdb416e2ebaa10c06efe1b787c8adc3fcf89170d3ab4801eabd56d0d6a244` |
| `docs/handoffs/strict_rebuild_20261103/remote_closure_20261103/eight_admission_v2/member_terminal_dispositions.json` | `b12c5c711213e39282be3cae4792ef81a8f263a34aec8dc57ddad32c4e8cc03a` |
| `docs/handoffs/strict_rebuild_20261103/remote_closure_20261103/eight_admission_v2/full_generator_8.json` | `acd48d381e71d8939b0ecbc24b077919a96f8762053e0581c06309e18d9ba15c` |
| `outputs/physics_completion/recovery/coverage_reviews.csv` | `e89188f6eac28bbf2dd309a95ec19ea9b1cc78969a262883820f939eec28ba40` |
| `outputs/physics_completion/ensembles/production_ensemble_labels.csv` | `c21003f5e18a2faaf4e3c8e91c379ea3ab16659706d13786ed25df0038ae0c80` |
| `outputs/physics_completion/ensembles/production_ensemble_dedup.csv` | `1f3ea92971d9725f407109d6a3c121b18aa4af13f80331e891ee612247377c04` |
| `outputs/physics_completion/recovery/strict_recovery_v1_manifest.csv` | `aab933144ad63d6af1b94b6de4d1f3bdec840b1986c85455357363bceb5ef1a0` |
| `outputs/physics_completion/recovery/strict_recovery_v1_search_index.json` | `932a454a4aede0dc1ec254d8f3f1c4814edd38bc8431c27d741960ddf39f7dc3` |
| `outputs/physics_completion/recovery/strict_recovery_v1_search_pool.csv` | `8ae4bd1372d8376eafb56199f49058678f7a13291a3b4464d173f04de645590f` |
| `outputs/physics_completion/frontier/frontier_identity_evidence.csv` | `0f8a8653b5285e0e786e62f1f3c03d021b8edc48502a56e768dba46d7ebcc5c6` |
| `outputs/physics_completion/frontier/frontier_legs.csv` | （与登记表同批生成；本轮以行号引用，登记表哈希见上） |

**关键原始日志 SHA256（本轮实测，全部与 `member_terminal_dispositions.json` 记录一致）**

| 成员 | 日志路径 | SHA256 |
|---|---|---|
| `TMP|M_plus\|27` | `work/hpc_production_ensemble_r1_continuation2/tasks/TMP/M_plus__27/snapshots/3725969_1/job.log` | `22089565df59b0ef2f2ae8436e848ed6276bdee15e324a478090be1b6b09b0b9` |
| `TMP|M_plus\|r3_c42` | `work/hpc_production_ensemble_strict_recovery_v1_reopt_v2/tasks/TMP/M_plus__r3_c42/snapshots/3744604_0/job.log` | `b76ab94e3ad0eadbc79b9817ef7dfa0252043be4b6d64945ee11c96d61fc416e` |
| `TMP|M_plus\|c10` | `work/hpc_production_ensemble_strict_recovery_v1_reopt_v2/tasks/TMP/M_plus__c10/snapshots/3744604_1/job.log` | `79d29c37a2a1c4ee93587ffa30a0316fa52585df83cf31ae9bc1ff50d74ec8ac` |
| `TMP|M_plus\|33` | `work/hpc_production_ensemble_r1_continuation2/tasks/TMP/M_plus__33/snapshots/3725969_0/job.log` | `864a901b159b4baa507407af984256c71162d2e8940a729f88f9c401ec7ecdf6` |
| `TMP|M_plus\|primary` | `work/hpc_anfreq_cohort_20261016/hpc_runs/TMP_M_plus/job.log` | `f8f67c8cbf7b56880df81f4d1595c29275b64560ff9689faf7cff3a8e6b251db` |
| `TMP|LiM_2plus\|c13` | `work/hpc_production_ensemble_r1_continuation4/tasks/TMP/LiM_2plus__c13/snapshots/3727606_4/job.log` | `5a0da9c4e3e21754739450b8073fff86f0f902e8aa7095cf5b62bac9b12ca861` |
| `TMP|LiM_2plus\|r3m_c00` | `work/hpc_production_ensemble_strict_recovery_v1_cont5/tasks/TMP/LiM_2plus__r3m_c00/snapshots/3742333_0/job.log` | `faf60e029ee515ec900b4dfe9f1dde26f2490c4291b399af67d0b5debd7b9c1b` |
| `TMP|LiM_2plus\|c08` | `work/hpc_production_ensemble_strict_recovery_v1_reopt_v2/tasks/TMP/LiM_2plus__c08/snapshots/3744604_2/job.log` | `04ba6d5ab2e933250e1d2b4f979e4091e87a38aaf638cc2fc53eb81aa3e5f173` |
| `TMP|LiM_2plus\|primary` | `work/hpc_anfreq_cohort_20261016/hpc_runs/TMP_LiM_2plus/job.log` | `122334b2dca238c49b1ac47ad5b65d47c027eb149d979c15bc702fb6d727fd0d` |
| `r3m_c00` seed 几何（非成员） | `work/limotif_r3_recovery/TMP_LiM_2plus@r2_c48/TMP_LiM_2plus@r2_c48_c00/xtbopt.log` | `c5fe8349f65041a664622081f6f7b1e6a824b9941b3d334153bb4c4cdabbbcc8` |

---

## 10. 交付说明

本文件为 A4 任务允许新增的两个文件之一：`docs/handoffs/lead_reception_strict_rebuild_20261103/evidence/A4_TMP_two_states.md`。本文件自身的 SHA256 随交付消息一并给出。本轮未修改任何既有文件、未提交作业、未新增计算。
