# 四态恢复起点账 · 只读出口复核（t4）

复核者：ledger-verifier（只读沙箱会话）。复核时间：2026-10-25。
复核对象：Lead 汇编的「四态恢复起点账」三条出口结论。
**本文件不含任何脚本产物；未改仓库任何文件；未调用超算；未跑 pytest。**

所有数字均为本次独立复算所得（原始输入直读），未照抄 Lead 结论。
每条给出：主张 / 原始命令或 file:line / 实测值 / 判定。

## 0. 所读输入的 sha256（绑定快照）

| 输入 | bytes | sha256 |
|---|---|---|
| `work/_recovery_sacct.txt` | 1565 | `0704D225310CF43C4A0B666899D8CE8338B821DEC9858DA4361B466890D689CD` |
| `outputs/physics_completion/recovery/recovery_budget_accounting.md` | 2460 | `78AC29DF64709859013170B6AF4B633F754A50998B7DE341FBCE48B4F92F8557` |
| `outputs/physics_completion/recovery/recovery_budget_accounting_index.json` | 351 | `D9D5685776E780FB229D648547B2F594E5CB831544476B6682626F95C30FFEF9` |
| `outputs/physics_completion/ensembles/production_ensemble_labels.csv` | 11574 | `822BE3B13978227EEB7C5970E32C538CC38C5F4EBF50709ACC4EACF7A2CB91BB` |
| `outputs/physics_completion/recovery/coverage_reviews.csv` | 4828 | `6CD5E92EDE14B910ED4555DCC5B1A187618245276B1231B55255B5192F3A0F80` |
| `outputs/physics_completion/recovery/strict_recovery_v1_manifest.csv` | 8214 | `8F710ACD7DF5099BC25FD36254D7C29A1CA9E3074D90949A4EE329C9BCD48612` |
| `outputs/physics_completion/recovery/strict_recovery_v1_report.md` | 4655 | `889C21D8C99F1F0429C64D37344F3CCCD153688BA3EA1ACF94245B7183AC11E2` |
| `outputs/physics_completion/recovery/strict_recovery_v1_report_index.json` | 952 | `89BA7F71441F8B4E09CCA55A22BA7E0EBF8B978D2C2C2210F30A8FA7D49A1288` |
| `work/hpc_torsion_probe_v1_batch2_fragmentfix_20261022/manifest.json` | — | `2A082CB8E6E60F8E4C065AC4DB0E0604804CBBD969AFB2572E6A222A5DEDB401` |
| `work/hpc_four_state_p4_xtb_screening_v1.pre_partition_fix/submission_journal.json` | — | `5A8A4255C546EE0146496A743E241C4D5EC3AADE4FA04F1F7DC5CDE51779834B` |
| `work/hpc_production_ensemble_r2_reopt/submission_journal.attempt0_refused_no_sbatch.json` | — | `7B3F31A3046919462B1144C597D40667337CEC30A10BA10687FA61603D971C72` |
| `work/hpc_torsion_probe_v1/submission_journal.json` | — | `0747160B2C39870B80300FF6007836C5D7A529FAE860B79C9E1F00288ABB24C6` |
| `work/deepseek_support_20261022/NEXT_ACTIONS.md` | — | `F121AB35D787A310C6305DB4860ED3D978EFCD40DD0C64B313C548D6EC8479EC` |

---

## 1. 检查 1｜终态证据（sacct 逐元素 core-hours）

**主张**：`work/_recovery_sacct.txt` 为 17 个 JobID 的原样落盘；总计 = **227.43**，其中 strict_recovery 家族 **187.00**、torsion probe 家族 **40.43**。

**原始命令**（`.venv/Scripts/python.exe -c`，直读文件，无中间产物）：
```
逐行 split('|') → Elapsed "HH:MM:SS" → 秒 × AllocCPUS / 3600，按 JobID 前缀聚合
```

**实测值**：
- 元素（行）数 = **42**（不含表头）；不同 JobID = **17**。
- `State` 分布：**COMPLETED 41 / CANCELLED by 59540 1**。
- 逐 JobID core-hours：

| JobID | n | core-hours | JobID | n | core-hours |
|---|---|---|---|---|---|
| 3738029 | 4 | 33.3056 | 3742330 | 1 | 2.1011 |
| 3738645 | 8 | 81.1989 | 3742333 | 3 | 29.0644 |
| 3738937 | 2 | 2.8856 | 3744604 | 5 | 17.1367 |
| 3739147 | 1 | 7.9422 | 3747714 | 8 | 24.1100 |
| 3739236 | 1 | 4.4567 | 3747724 | 1 | **0.0000** |
| 3739621 | 1 | 1.7889 | 3748336 | 1 | 6.5200 |
| 3739650 | 1 | 1.6589 | 3749450 | 2 | 5.2467 |
| 3739671 | 1 | 3.3533 | 3749453 | 1 | 4.5567 |
| 3740627 | 1 | 2.1056 | | | |

- **总计 = 227.4311 core-hours**。

**判定**：**成立**。227.4311 与主张 227.43 一致（1 位小数四舍五入）。
附注：`3747724_[0-2]` 在 `-X` 汇总下为 1 行、代表 3 个数组元素，`Elapsed=00:00:00`、`AllocCPUS=0` ⇒ 计 0 core-hours；无论按 1 行还是按 3 元素计，成本都相同（0）。

---

## 2. 检查 2｜与权威账本对账（按包 ↔ 按 JobID）

**主张**：`recovery_budget_accounting.md` 的 strict_recovery 家族合计 **187.0**；逐包数值可与按 JobID 的结果建立对应。

**我的对应依据（可复核）**：JobID → 记录该 `job_id` 的 `submission_journal.json` → 其所在包目录名；家族按目录名前缀划分（`hpc_production_ensemble_strict_recovery_v1*` / `hpc_torsion_probe_v*`）。依据是 journal 内 `job_id` 字段与 sacct 的 JobID 完全一致（下节检查 3 给出全量比对）。

**实测值（strict_recovery 家族，12 包 / 12 提交）**：

| 包 | JobID | 我算 core-hours | 账本表值 |
|---|---|---|---|
| strict_recovery_v1 | 3738029 | 33.3056 | 33.3 |
| _b2 | 3738645 | 81.1989 | 81.2 |
| _cont1 | 3739147 | 7.9422 | 7.9 |
| _cont2 | 3739236 | 4.4567 | 4.5 |
| _cont3 | 3739621 | 1.7889 | 1.8 |
| _cont4 | 3739671 | 3.3533 | 3.4 |
| _cont5 | 3742333 | 29.0644 | 29.1 |
| _reopt1 | 3738937 | 2.8856 | 2.9 |
| _reopt2 | 3739650 | 1.6589 | 1.7 |
| _reopt3 | 3740627 | 2.1056 | 2.1 |
| _reopt4 | 3742330 | 2.1011 | 2.1 |
| _reopt_v2 | 3744604 | 17.1367 | 17.1 |

- 家族合计 = **186.9979 ≈ 187.0** ✔（与账本 `**恢复包合计：187.0 / 600 core-hours` 一致）
- `recovery_budget_accounting_index.json`：`recovery_used_core_hours=187.0`、`recovery_cap=600.0`、`reserve_cap=300.0`、`accepted=44`、`limited=4` ✔
- torsion probe 家族（不在该账本表内，属独立家族）：3747714 24.1100 + 3747724 0.0000 + 3748336 6.5200 + 3749450 5.2467 + 3749453 4.5567 = **40.4334 ≈ 40.43** ✔
- 两家族合计 186.9979 + 40.4334 = **227.4313 ≈ 227.43** ✔

**判定**：**成立**（12/12 逐包对应一致）。
**呈现瑕疵（不影响结论）**：账本表把每包四舍五入到 1 位小数后，**表面相加 = 187.1**，而文字合计写 187.0。差 0.1 来自分别取整；精确值为 186.9979，故合计 187.0 正确。建议账本标注「逐包为 1 位小数取整、合计按未取整值」。

---

## 3. 检查 3｜提交史完整性与「共 17 次提交」

**主张**：recovery + torsion 家族共 **17 次提交**；`attempt0_refused_no_sbatch.json` 是唯一拒收记录（后者见检查 6）。

**原始命令**：`json` 遍历 `work/hpc_production_ensemble_strict_recovery_v1*/submission_journal*.json` 与 `work/hpc_torsion_probe_v*/submission_journal*.json`，取 `len(submissions)` 与每个 `job_id`。

**实测值（每个 journal 的 submission 数与 job_ids）**：
- 12 个 recovery journal：各 **1** 次，job_ids = 3738029 / 3738645 / 3739147 / 3739236 / 3739621 / 3739671 / 3742333 / 3738937 / 3739650 / 3740627 / 3742330 / 3744604。
- 4 个 torsion journal：`hpc_torsion_probe_v1` = **2** 次（3747714、3747724）；`_batch2_fragmentfix_20261022` = 1（3748336）；`_reopt_v3` = 1（3749453）；`_v2_realfragment` = 1（3749450）。
- **合计 17 次提交，job_ids 恰为 sacct 的 17 个 JobID（集合相等，无缺无多）** ✔

**独立搜漏结果**：
1. `work/**/submission_journal*.json` 全仓共 **34** 个文件：其中 16 个的 job_ids 全部落在这 17 个内（即上表）；其余 18 个的 job_ids 全在 17 之外，且按其包名属**其它家族**（`hpc_production_ensemble_r2_*`、`hpc_frontier_localization_v1`、`hpc_saddle_repair_round2_20261014`、`hpc_pc_continue_20261014`）或为**测试夹具**（`work/_release_core_tests_*`、`work/_torsion_submit_fix_tests_*`，job_id 均为 `987654`）。
2. `outputs/physics_completion/provenance/job_archive_manifest.csv`（**2167 行**）：17 个 JobID **一个都不含** ⇒ 该归档与恢复/扭转家族无交集，不构成漏记来源。
3. `.dsh-coordination/`：**仓库内不存在**；工作区根 `E:\Claude Code\电解液溶剂-HB\.dsh-coordination\af276253\` 下只有 `pytest_tmp*` / `pytest_full` 夹具（harness 的 pytest 临时目录），**无任何真实作业记录**。
4. `work/_sacct_ensemble_wall.txt`（36 行，JobID 3725968_* 等）是**另一次**查询，17 个 JobID 在其中 **0 次出现**，不构成漏记来源。

**判定**：**成立**。「共 17 次提交」在**恢复+扭转两家族**范围内准确，且我未能找到被漏掉的提交记录。
**口径提醒**：17 是**家族范围**的计数；全仓 34 个 journal 合计 `submitted` 状态 **54** 次、`submit_failed` **4** 次（见检查 6），不是全部。

---

## 4. 检查 4｜四态冻结事实

**主张**（Lead 列表）：四态 `DMC|M_plus`、`DMC|LiM_2plus`、`DOL|LiM_2plus`、`EC|LiM_2plus` 的 `acceptance_status` / `limitation_reason` / `route` / `verdict` / `registered_starts`。

**原始命令**：直读两个 CSV，按 `name + '|' + state` 组合键取行。

**实测值**：

`production_ensemble_labels.csv`（48 行）：

| 态 | acceptance_status | limitation_reason | n_members | pool_limited | coverage_status |
|---|---|---|---|---|---|
| DMC\|M_plus | `limited` | `rescue_budget_exhausted` | 1 | true | review_unresolved |
| DMC\|LiM_2plus | `limited` | `rescue_budget_exhausted` | 1 | true | review_unresolved |
| DOL\|LiM_2plus | `limited` | `rescue_budget_exhausted` | 1 | true | review_search_exhausted |
| EC\|LiM_2plus | `limited` | `rescue_budget_exhausted` | 1 | true | review_search_exhausted |

`coverage_reviews.csv`（14 行；全表 route/verdict 分布 = single_basin_verified/resolved ×2、multi_basin_coverage/resolved ×8、unresolved_qc/unresolved ×2、search_exhausted/search_exhausted ×2）：

| 态 | route | verdict | registered_starts | n_unique_after | kept_pool_evidence |
|---|---|---|---|---|---|
| DMC\|M_plus | `unresolved_qc` | `unresolved` | `tors_8_0_1_2` | 1 | （空） |
| DMC\|LiM_2plus | `unresolved_qc` | `unresolved` | `tors_7_0_1_2` | 1 | （空） |
| DOL\|LiM_2plus | `search_exhausted` | `search_exhausted` | （空） | 1 | （空） |
| EC\|LiM_2plus | `search_exhausted` | `search_exhausted` | （空） | 1 | （空） |

**判定**：**成立**。四态的 `acceptance_status`/`limitation_reason`/`route`/`verdict`/`registered_starts` 与 Lead 列表**逐字段一致**；`n_unique_after` 四态均为 **1**。
附注：四态 `kept_pool_evidence` 均为空串（与既有审计「kept_evidence 被清空」的观察同向）；`registered_starts` 在 `coverage_reviews.csv` 是**盆地名字符串**，而在 `strict_recovery_v1_report.md:63-66` 同一列语义是**计数**（四态均显示「注册起点 0」）——两处不是同一口径，跨文件引用时须注明来源。

---

## 5. 检查 5｜在飞核查：该断言可能漏掉什么

**主张**：以「sacct 全部终态 + 实时 squeue 空」断言「不存在重复在飞任务」。

**实测/该证据链的结构性缺口**：
1. **查询范围仅限已知 17 个 JobID**（`sacct -j <17 IDs>`）。sacct 落盘不含 Start/End 时间（列为 `JobID,State,ExitCode,Elapsed,AllocCPUS`），因此**无法重建各元素的实际运行区间**，也就无法用本文件排除「两次重投短暂并发」。
2. **未查该账户其它在飞作业**：本次落盘不含 `sacct -u <user>` 或 `squeue -u <user>` 的账户级快照，无法证明账户内没有其它正在跑/排队的作业。
3. **`squeue` 空是单点快照**：只在某一瞬间为空；若查询与 sacct 落盘之间有时间差，期间的 pending/running 不会被捕获（本文件无法给出 squeue 的时间戳与命令原文）。
4. **`3747724_[0-2] CANCELLED`**：`-X` 把它折叠成 1 行、3 个数组元素不可分。**是否留部分产出/待重投意图，本文件无法判定**——须由包内文档回答（见检查 6，结论：取消前未运行、且明确不建议重投）。
5. **重投顺序（我另查的补充证据）**：同一条腿确有**两次提交**——`DMC|LiM_2plus__tors_7_0_1_2` 先在 `fragmentfix`（3748336，2026-10-22T08:21:36Z 提交）、后又在 `_reopt_v3`（3749453，11:30:25Z）；`DMC|M_plus__tors_8_0_1_2` 先在 `hpc_torsion_probe_v1` batch 1（3747714，07:07:55Z）、后在 `_v2_realfragment`（3749450，11:30:13Z）。**提交事件间隔 ≥3 小时**，且所有 17 个 JobID 在 sacct 均为终态 ⇒ 与「无重复在飞」**不冲突**；但 journal 记的是**提交事件时间（每次约 4 秒）**，不是作业运行区间，故严格意义上「无并发运行」仍未由本地证据**证明**，只是**未被反驳**。

**我的判断**：断言在**当前可观测范围**内成立（17 个 JobID 全终态；重投事件分离；无待重投迹象），但**证据强度不足**——不足以支持「该账户/整个项目不存在任何重复在飞」的全称结论。建议补齐：① `squeue -u <user>` 的**带时间戳原始输出**；② `sacct` 增加 `Start,End` 列以重建运行区间；③ 账户级而非仅已知 ID 的查询。

---

## 6. 检查 6｜规划 vs 拒收

### 6.1 manifest 四态行是否等于「已运行的尝试」

**原始命令**：直读 `strict_recovery_v1_manifest.csv`（13 行）。

**实测值**：四态行 `status=planned`、`start_1_basin=""`、`start_2_basin=""`、`start_1_source_sha256=""`、`start_2_source_sha256=""`、`released=""`，同时 `path=new_search_required`、`needs_versioned_search=true`、`max_new_starts=2`、`search_outcome=no_new_minimum_found`。全表 status 分布 = `planned` 7 / 空 6。
- 对照：同为 `planned` 的 `DMSO|LiM_plus`、`TMP|LiM_plus`、`TMP|M_plus` 三行**已 `released=true` 且 `search_outcome=new_minima_found`**（另有 6 行 status 为空、`released_by_review`）。

**判定**：**成立**——四态这些行**不等于已运行的尝试**：它们是无起点盆地、无源几何 sha256 的**计划行**，`path` 自述 `new_search_required`。真实已运行的尝试见 `strict_recovery_v1_report.md:61-66`（逐态「腿」列）：
- `DMC|M_plus`：3 条腿（tors_6/7/8），全部**真实运行**、最后结果均 `technical_complete_qc_failed`；
- `DMC|LiM_2plus`：3 条腿（tors_6/7/8），同样全部真实运行、`technical_complete_qc_failed`；
- `DOL|LiM_2plus`：**「—（无恢复腿）」**，即**零尝试**；
- `EC|LiM_2plus`：2 条腿（tors_2_3_4_10、tors_5_3_4_10），记「0/2；结果 未跑；当前 pending」。
- 该报告 `:26` 自己写明：「**pending 行：2 条腿——本报告不校验它是否真的提交过**（判据只有那一行的 `status`）⇒『在飞』必须另与实时 `squeue`/提交日志交叉核对」。

**呈现瑕疵**：四态 `planned` 行已预填 `search_outcome=no_new_minimum_found`，与「尚未立项/尚未搜索」的状态语义相冲突（该字段在未运行行上看起来像结论）。建议计划行该字段留空或以 `not_run` 区分。

### 6.2 EC 两条 pending 腿的真实来龙（我独立补链）

- `work/hpc_torsion_probe_v1/batch_2.txt` 的 3 个任务 = `DMC/LiM_2plus__tors_7_0_1_2`、`EC/LiM_2plus__tors_2_3_4_10`、`EC/LiM_2plus__tors_5_3_4_10`；该批次即 **3747724**（`hpc_torsion_probe_v1/submission_journal.json` 第 2 条提交，07:08:26Z），sacct 记为 `CANCELLED by 59540`、0 时长 ⇒ **提交过、取消前未运行**。
- `work/hpc_torsion_probe_v1_batch2_fragmentfix_20261022/manifest.json`：`replaces_cancelled_job="3747724"`、`requested_tasks` 列 3 项，但 `tasks=1`、`batches=[{batch:1,count:1}]`，且 `batch_1.txt` **只有 DMC 一条** ⇒ 实际只补投了 DMC 腿（3748336）；**EC 两条**被列入 `rejected` 数组（`:50-59`，理由均为 `central bond is not a verified single bond`）。
- `work/deepseek_support_20261022/NEXT_ACTIONS.md:35,39`：明载「原第二批 3747724 的实际映射指向 AN，且**取消前未运行**。不要把它记成已经执行过的 DMC 几何计算」；「本包**不建议再次提交**」。
- 另行核对：`_reopt_v3`（3749453）的 batch 也只含 `DMC/LiM_2plus__tors_7_0_1_2`，未再含 EC 两腿。

⇒ EC 两条腿的 `pending` 是**「已提交但被取消（未运行）+ 修复阶段被拒收（化学理由）」**共同结果，**没有部分产出、没有待重投意图**。

### 6.3 「`attempt0_refused_no_sbatch.json` 是唯一拒收记录」

**原始命令**：全仓 `work/**/submission_journal*.json` 的 `status` 计数 + `*refus*`/`*attempt*` 文件名搜索 + manifest 内 `rejected` 搜索。

**实测值**：
- 全仓 journal 提交条目状态：`submitted` **54**、`submit_failed` **4**。其中**真实**（非测试夹具）的 `submit_failed` 有 **2** 个：
  1. `work/hpc_production_ensemble_r2_reopt/submission_journal.attempt0_refused_no_sbatch.json` — `status=submit_failed`、`bridge_exit_code=1`，`bridge_message` 为「远程路径含引号/空格，被拒绝」；
  2. `work/hpc_four_state_p4_xtb_screening_v1.pre_partition_fix/submission_journal.json` — `status=submit_failed`、`bridge_exit_code=1`，`bridge_message` 为「缺少 `#SBATCH --partition`，脚本校验未通过」，且 `job_id` 为空（**同样在任何 sbatch 运行前被拒**）。
  另 2 个 `submit_failed` 属测试夹具（`_release_core_tests_*`、`_torsion_submit_fix_tests_*`，exit=7）。
- 另有**非 journal 形式**的拒收记录：`fragmentfix manifest.json` 的 `rejected` 数组含 **2 条**（EC 两腿，化学理由），且 `NEXT_ACTIONS.md:39` 记「不建议再次提交」。
- `work/hpc_production_ensemble_r2_reopt/submission.json:21` 有同源文字记录（`"attempt0": "Refused by the bridge BEFORE any sbatch ran: ..."`）。

**判定**：**不符**。作为书面陈述，「唯一拒收记录」**不成立**：
- 若「拒收」= **提交器/jour­nal 里的 submit_failed**：至少 **2** 条（另有 1 条属 P4 筛选包，与四态恢复计划的 P4 下一步直接相关）；
- 若「拒收」= **任何被拒的登记/申请**：另有 `fragmentfix` manifest 的 **2** 条 `rejected`（EC 两腿）。
正确的表述应为：「在四态恢复/扭转两个家族的 `submission_journal*` 内**没有** submit_failed；第一个 `submit_failed` 记录是 `attempt0_refused_no_sbatch.json`。」

---

## 7. 总结行

**15 项检查，14 成立，1 不符。**

| # | 检查项 | 判定 |
|---|---|---|
| 1 | sacct 元素数 / State 分布 | 成立（42 行；41 COMPLETED + 1 CANCELLED） |
| 2 | sacct 总 core-hours = 227.43 | 成立（227.4311） |
| 3 | strict_recovery 家族 = 187.00 | 成立（186.9979） |
| 4 | torsion probe 家族 = 40.43 | 成立（40.4334） |
| 5 | 账本逐包 ↔ 按 JobID 对应（12 包） | 成立（12/12 一致；附取整呈现瑕疵） |
| 6 | `index.json` 值（187.0 / 600 / 300 / 44 / 4） | 成立 |
| 7 | 家族 journal 共 17 次提交、job_ids ↔ sacct 17 | 成立（集合相等） |
| 8 | 独立搜漏（全仓 journal / 归档 manifest / 协调目录 / 另一次 sacct） | 成立（未发现漏记） |
| 9 | 四态 labels 字段 | 成立（逐字段一致） |
| 10 | 四态 coverage 字段（含 n_unique_after=1） | 成立（逐字段一致） |
| 11 | manifest 四态行 status=planned、starts/sha 为空 | 成立（附 `search_outcome` 预填瑕疵） |
| 12 | 「`attempt0_refused_no_sbatch.json` 是唯一拒收记录」 | **不符**（另有 1 条 journal + 2 条 manifest rejected） |
| 13 | EC 两条 pending 腿可追至 3747724 取消 + fragmentfix 拒收 | 成立 |
| 14 | 「无重复在飞任务」断言 | 成立（范围内）但**证据强度不足**（无 Start/End、无账户级查询、squeue 单点快照） |
| 15 | 3747724 无部分产出、无待重投意图 | 成立（文档记载 + 无产物 + 明确不建议重投） |

### 未能覆盖 / 需 Lead 补做的范围
1. **无法本地验证超算侧实况**：`squeue` 空与 `sacct` 全终态的**原始桥输出**（含命令原文与时间戳）不在本仓库，我无法复核其时效；`3747724` 三个数组元素在远端的逐元素终态与是否留残物**无法本地判定**。
2. **无账户级在飞快照**：因此检查 14 的全称结论无法闭合（见检查 5 的三条补齐建议）。
3. **`strict_recovery_v1_report.md` 的 2 条 pending 腿**：本报告已用包内文档补出「取消+拒收」链，但该报告自身的判据只有 `status` 字段，与提交史的对账建议正式写入该报告而非仅留在本复核。
4. 未运行任何生成器、未跑 pytest、未调用超算；除本文件外未写入任何文件。