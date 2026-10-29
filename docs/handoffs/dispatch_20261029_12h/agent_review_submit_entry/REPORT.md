# t11 ｜ `submit_batch` 入口审查（只读）：调用链、合同校验插入点、坏请求拒绝点、回归面与风险

> **角色/约束**：只读审查。**未改任何生产文件/未调 bridge/未提交/未写 outputs**；唯一写入＝本报告目录。
> **⚠ 复审对象不在 HEAD 的已提交版本上**：`git status` 显示两份 `.py` 均为 **未提交改动（M）**。且审查期间该文件被并发写入——我第一次读到 **531 行 / sha `2f900fd9…`**，随后变为 **727 行 / sha `7d0e0278…`**（同一批内不同 range 甚至返回了不同快照，见 §6）。**本报告全部行号绑定下表中的 sha**，凡与我更早快照不符者以本表为准。

## 0. 对象与 sha256（本次审查的字节快照）

| 对象 | sha256 | 规模 | git |
|---|---|---|---|
| `scripts/wp_production/submit_hpc_batch.py` | `7d0e0278b9e5571475eb2529c70fbd62db6fff47e0f4796426e3cff4255e394d` | 727 行（`Get-Content`；读取器计 728 行含末行）/ 28078 B 起 | **M（未提交）** |
| `scripts/wp_production/ec_recovery_contract.py` | `274732a6d858d8bc5774626e4b7205dd0a23e2a5827da52d47b375184d918df9` | 177 行 | **M（未提交）** |
| `work/hpc_ec_recovery_v2_p4_20261029/manifest.json` | 见 §2 字段摘录（44 行） | 1 元素 HOLD 包 | `work/`（gitignored） |

仓库 HEAD：`6a5f9ef`（"site: repo-inventory refresh after L14 handoff"）——**与两个 .py 的工作树内容不一致**。
旁证（实测）：`work/ec_recovery_v2_campaign/` **不存在** ⇒ **p4 尚未提交过任何元素**（与 manifest `submitted:false` / `submission_gate:HOLD` 一致）。

---

## 1.（问题①）`submit_batch` 完整调用链与副作用顺序

| # | 步骤 | file:line | 副作用 |
|---|---|---|---|
| 0 | `main()` 解析参数（package/--batch/--remote-workdir/--attempts-ledger/--budget-cap-core-hours/--bridge/--user） | `submit_hpc_batch.py:687-699` | 无 |
| 1 | 读 `--attempts-ledger` 文件并取 `attempts` | `:709-714` | 无（**但缺文件会抛未捕获异常，见 R7**） |
| 2 | `submit_batch` 入参校验：`USER_RE`／`remote_workdir` 非空且无换行 | `:525-528` | 无 |
| 3 | `_load_package`：读 `manifest.json`→`batches` 唯一条目、`count∈[1,20]`、`batch_N.sbatch`、`batch_N.txt`、清单行数==count | `:144-163`，调用 `:529` | 无 |
| 4 | `submission_resources`：从 **manifest** 的 `resource_profile` 解析 profile（未知即拒；缺字段回落 `orca_production_v1`） | `:166-180`，调用 `:530` | 无 |
| 5 | CLI cap 断言（`--budget-cap-core-hours` 必须**等于** profile cap，不得放宽） | `:531-534` | 无 |
| 6 | `attempts_ledger_required` 生效点（profile 要求账本而调用方未给 ⇒ 拒） | `:536-538` | 无 |
| 7 | 读 journal（不存在⇒空结构）＋**重复提交**检查（同 batch 已有记录即拒）＋本地预留文件存在即拒 | `:539-552` | 无 |
| 8 | **EC 战役合同校验**（`_enforce_ec_contract`） | `:554-561`（函数 `:431-477`） | **无** |
| 9 | **bridge `doctor`** | `:563` | **首个远端动作**（网络/进程） |
| 10 | **取账户级远端锁**（`mkdir ~/project/electrolyte_wp2/.wp2_submit.lock`） | `:564-569` | **远端写** |
| 11 | 实时 `squeue -h -u <user> -o %i` | `:572-574` | 远端读 |
| 12 | headroom 判定（`count > 20-active_pending` 即拒） | `:576-578` | 无 |
| 13 | `declared_task_cores`：任务 `job.inp` 的 `%pal nprocs`（或非 ORCA 的 `cores.txt`）必须 == profile cores | `:581-586`（函数 `:249-297`） | 无（只读） |
| 14 | 预算不变式：`committed+reserved ≤ cap`（无账本时仅打印 NOTE） | `:588-621`（`budget_headroom` `:325-346`；`committed_core_hours` `:300-322`） | 无（`print` 于 `:620`） |
| 15 | 组装 `record`（含三个 sha：脚本/清单/manifest） | `:623-634` | 无 |
| 16 | **创建本地预留锁 `.batch_N.submission.lock`（`x` 模式，独占）** | `:636-640` | **本地写** |
| 17 | **journal 追加 `status="submitting"`** | `:641-642` | **本地写** |
| 18 | **bridge `submit`（真正提交）** | `:650-652` | **远端提交** |
| 19 | 结果解析：`submit_failed` / `submit_result_unparseable` / `submitted(job_id=…)` 各写 journal | `:653-670` | 本地写 |
| 20 | `finally`：**追加 EC 战役账本记录**（无论成败，保守占位） | `:671-675`（`_append_ec_campaign_entry` `:480-517`） | **本地写** |
| 21 | `finally`：释放远端锁 `rmdir`（失败则记 journal 并 raise） | `:676-684` | 远端写 |
| 22 | main 收口：成功打印 JSON；`ValueError/RuntimeError` → `REFUSED: …` + **exit 2** | `:719-723` | 无 |

**插入合同校验的唯一最优点：`:554-561`（即 `resources` 解析之后、【`:563` `doctor`】之前）。判定：成立——当前实现已在最优点。** 理由：
1. **`:563` 是第一个副作用点**（docstring `:434-437` 自述 "Runs BEFORE the bridge doctor call, the remote lock and any submission, so an invalid request has no side effect at all"，与实测行序一致）；`:564` 是第一个**远端写**。
2. 合同需要 `resources`（profile/cores/wall）⇒ 必须在 `:530` 之后；`_enforce_ec_contract` 也不读 `count` 之外的批次状态，故无需更晚。
3. 与它相邻的 `:539-552`（journal/预留/重复）同为**只读+纯判定**，先后无关紧要，但两者都必须在 `:563` 之前──这是唯一需要守的不变量。
4. 该处**不做任何写入**（`read_ec_campaign_history` 只读 `:377-400`、`_package_candidate_identity` 只读 `:403-428`）⇒ 坏请求连本地 journal 都不动。

---

## 2.（问题②）manifest / ledger / profile / journal 的读取点与字段名

| 读取物 | 函数:line | 字段 |
|---|---|---|
| manifest 批次 | `_load_package` `:144-163` | `batches[].batch`／`batches[].count`；同目录 `batch_N.sbatch`、`batch_N.txt` |
| manifest 资源 | `submission_resources` `:166-180` | `resource_profile`（缺失⇒`DEFAULT_RESOURCE_PROFILE`；未知⇒`unknown manifest resource_profile`） |
| manifest 预留/活动候选/战役 | `:598-600`、`:426-427`、`:447-449`、`:454-456`、`:477` | `first_batch_reserved_core_hours`（`get`，可为空）、`active_candidate`、`campaign`、`reserved_core_hours` |
| 通用 attempts ledger | `--attempts-ledger`→`main:709-714`；`committed_core_hours:300-322` | `status`（跳过 `planned/rejected/superseded_unsubmitted`；`pending/running/submitting` 按 `cores×wall_hours_reserved` 计；否则需 `slurm_allocation_id`+`measured_core_hours`，缺即 raise）、`cores`、`wall_hours_reserved`、`slurm_allocation_id`（**同一 allocation 只计一次** `:318-320`） |
| **EC 战役账本** | `ec_campaign_ledger_path:361-368`→`<package 父目录>/ec_recovery_v2_campaign/attempts_ledger.json`；读于 `read_ec_campaign_history:371-400` | `campaign_id`、`attempts[].candidate/submitted/terminal/accepted/evidence_complete/geometry_sha256/settled_core_hours`（`accepted`/`evidence_complete` **缺键⇒None**，与显式 null 等价） |
| journal | `:539-544` | `schema_version`、`submissions[].batch/status`（重复判定只看**最近一条**同批记录 `:545-549`） |
| 本地预留 | `:540`、`:636-640` | 文件即状态（`x` 独占创建） |

`attempts_ledger_required` 生效点：**`:536-538`**（依 profile 表 `:24-75`；`orca_production_v1=False`，`orca_production_4h_v1`/`xtb_*`/`h2_single_point_v1`/`orca_production_12h_v1` 均为 `True`），另在 `:440-441` 对 EC 再兜一层。
`budget_headroom` 口径：**默认按元素**（`cores×wall_hours×task_count` `:337-338`）；**当 manifest 带 `first_batch_reserved_core_hours`（正值）时逐字改用该值**（`:597-609`），再与 `cap` 比（`:611-613`）。
实测（本包，SHA 见 §0）：`resource_profile="orca_production_4h_v1"`、`cores_per_task=4`、`wall_hours_per_task=4`、`reserved_core_hours=16`、`budget_cap_core_hours=32`、`active_candidate="ec_v2_p4"`、`campaign="four_state_recovery_20261023"`、`submission_gate="HOLD"`、`submitted=false`、`contract.{candidates,max_submitted_elements,element_core_hours}` 与 `ec_recovery_contract.py:14-20` 常量一致；`batches=[{batch:1,count:1}]`；`tasks=["tasks/EC__LiM_2plus/ec_v2_p4"]`（**注意实际目录名是 `tasks/EC__LiM_2plus/ec_v2_p4`，而 `_package_candidate_identity` 只要求 `len(listed)==1` 且 `candidate.json`/`geom.xyz` 存在** `:405-412`）。

---

## 3.（问题③）坏请求应在哪一行被拒（逐类）

简报列了 9 个短语、标称「8 类」；本表按 **9 类**逐条给出拒绝点（全部为 `fail-closed`，经 `main:719-721` → `REFUSED` + exit 2）。

| # | 坏请求 | 拒绝点（file:line） | 判据原文/机制 | 判定 |
|---|---|---|---|---|
| 1 | **p7 抢跑**（p4 未终态/证据未齐就投 p7） | `ec_recovery_contract.py:27-60`（`next_candidate`）→ `:88-93`（`candidate != expected` 抛 `ContractViolation`），经 `submit_hpc_batch.py:457-469` 调用 | `p4 terminal but accepted 缺失/None ⇒ None`（`:51-52`）、`evidence_complete is not True ⇒ None`（`:55-56`）；返回 None 时任何候选都 != None ⇒ 拒 | **成立** |
| 2 | **第三腿** | `ec_recovery_contract.py:95-99`；兜底 `:57-60`→`:88-93` | `ec_submitted_elements + element_count > EC_MAX_SUBMITTED_ELEMENTS(2)` ⇒ 拒 | **成立** |
| 3 | **p4 已 accepted 还想再算** | `ec_recovery_contract.py:53-54`→`:88-93` | `accepted ⇒ return None` ⇒ 无候选可投 | **成立** |
| 4 | **p4 结果未知／`accepted` 字段缺失** | `ec_recovery_contract.py:51-52`→`:88-93`；写入侧 `submit_hpc_batch.py:505` | `accepted is None ⇒ None`（**仅 `True` 才算通过**）；`_append_ec_campaign_entry` 恒写 `accepted=None`、`terminal=False`（`:501-513`） | **成立** |
| 5 | **超预算** | `ec_recovery_contract.py:148-158`（战役 32 CH 上限）＋`submit_hpc_batch.py:611-613`／`budget_headroom:341-343`（profile cap） | `settled+unsettled+new > 32`；`committed+reserved > cap` | **成立** |
| 6 | **低报预留** | `ec_recovery_contract.py:141-146` | `declared_reservation_core_hours` 必须 == `16×element_count`（`EC_ELEMENT_CORE_HOURS=16` `:18`） | **成立** |
| 7 | **缺账本** | `submit_hpc_batch.py:536-538`（profile 要求）＋`:440-441`（EC 再兜） | `attempts_ledger_required and attempts_ledger is None ⇒ 拒`；`_enforce_ec_contract` 第一句即拒 None | **成立** |
| 8 | **并发第二腿**（p4 在飞时再投） | `ec_recovery_contract.py:160-164`（`ec_active_pending != 0`）＋`:104-116`（计数须与历史吻合）＋`submit_hpc_batch.py:450-453/466-467`（重算 pending 后传入） | 调用方**不得自报** active/submitted 数；与 `history` 派生值不一致即拒 | **成立** |
| 9 | **候选/输入偷换** | `submit_hpc_batch.py:420-425`（`candidate.geometry_sha256` vs 磁盘 `geom.xyz` 实算）、`:426-427`（manifest `active_candidate` vs 任务候选）、`:470-475`（与历史记录 `geometry_sha256` 不一致） | 三处独立比对，任一不符即拒 | **成立** |

**补充（第 10 类，简报未列但同属入口级）：非 EC profile 时合同整体不生效** ⇒ 见 R2（这是"拒绝点缺失"而非"拒绝点存在"，故计入 §5 风险而非本节）。

---

## 4.（问题④）旧 profile 行为不得变化的回归面

**不得变化的语义**（profile 表 `:24-75`）：`orca_production_v1`＝4 核/24 h/cap 800/**`attempts_ledger_required=False`**（`:27-29`，即**不给账本仍可提交**、仅 `:620` 打印 NOTE）；`xtb_screening_v1`＝2 核/2 h/cap 32/需账本（`:40-42`）；`xtb_screening_v2`＝4 核/1 h/cap 16/需账本（`:51-53`）；`h2_single_point_v1`＝4 核/**1/12 h**/cap 2/需账本（`:61-63`，**分数墙钟必须继续走 `:643-647` 的 `%02d:%02d:00` 换算**，否则被截断为 `00:00:00`）；`orca_production_12h_v1`＝4 核/12 h/cap 96/需账本（`:72-74`）。缺 `resource_profile` ⇒ 回落历史默认（`:177`＋`:76`）。

**必须保持的字段/契约**：journal 键集合（`batch`/`batch_count`/`observed_active_pending`/`resource_profile`/`resource_engine`/`declared_task_cores`/`allocated_wall_hours`/`headroom_before_submit`/`remote_workdir`/`remote_submission_lock`/`batch_script_sha256`/`batch_list_sha256`/`manifest_sha256`/`started_at_utc`/`status`＋`budget_*`，`:623-634`）；CLI 契约 `REFUSED: …` + exit 2（`:719-721`）；`first_batch_reserved_core_hours` 的"按作业计费"覆盖语义（`:597-609`）；`.batch_N.submission.lock` 与 journal 双幂等（`:539-552`,`:636-642`）。

**现有回归测试面（点名，均须保持绿）**：`tests/test_submit_hpc_batch.py:45,113,135`（xtb_screening_v1 / orca_production_v1 结果字段）；`tests/test_submit_budget_gate.py:98-111`（`budget_headroom` 800/4/24 与 100/200 cap 两态）；`tests/test_dol_ec_recovery_package.py:74-76`（`submission_resources` → `orca_production_12h_v1`）；`tests/test_p4_screening_plan.py:157,180-181`（计划层核数/预算）；`tests/test_preflight_v2_production_batch.py:82`（契约把 `dol_ec_recovery_v1` 改成 `orca_production_v1` 的路径）；`tests/test_ec_recovery_contract.py:16,25-26,141`（新合同单测＋**显式断言 `orca_production_v1.attempts_ledger_required is False`**）；`tests/test_ec_submit_entry.py:56,249`（**`:249` 用 `profile="orca_production_v1"`＋`reserved=16` ⇒ 正是"非 EC profile 不得套用 EC 合同"的回归守卫**）。判定：**回归面清晰、成对存在** ⇒ 成立。

---

## 5.（问题⑤）风险（逐条：触发条件 → 后果 → 建议）

| # | 风险 | file:line | 触发条件 | 后果 | 建议 |
|---|---|---|---|---|---|
| **R1** | **`submission_gate:"HOLD"` / `submitted:false` 完全不被提交器读取** | 全文 grep `submission_gate` = **0 命中**；manifest 字段见 `manifest.json:32-34` | 有人显式传 `--attempts-ledger`（EC 包自带 `attempts_ledger.json`）且战役目录为空 | **HOLD 包会被合同判为合法 p4 并真正提交**（空历史下 `next_candidate→p4`、预留 16==16、cap 32 全过）⇒ "设计-only/HOLD" 仅是散文，无机器强制 | 在 `:554-561` 区加显式门：manifest `submission_gate` 必须为允许值（如 `OPEN`），且与 `submitted` 一致，否则拒 |
| **R2** | **profile 由包内 manifest 自选 ⇒ EC 合同可被整体绕过** | `:558`（`resources["name"] == EC_CAMPAIGN_PROFILE` 才进合同）、`:177`（profile 来自 manifest）、`:27-29` | 把 manifest 的 `resource_profile` 改成 `orca_production_v1` | EC 合同（候选顺序/两腿上限/16 CH/32 CH/账本）**全部跳过**；cap 升为 **800**、且**不再要求账本** ⇒ 用改一个字段即可越过全部 EC 约束 | 对战役包做**与 profile 无关的身份绑定**（包名/战役目录/`campaign` 字段命中 EC 候选集即无条件走合同） |
| **R3** | **manifest 缺 `campaign` 时战役身份核对静默通过** | `:447-449` | manifest 无 `campaign`（`None`）而账本有 `campaign_id` | `None in (None, X)` ⇒ **不拒** ⇒ 可拿别的战役的账本"洗白"预算/轮次 | 缺 `campaign` 即拒（EC 包应强制声明） |
| **R4** | **战役账本可被任意改写，且"文件缺失＝从未提交"** | `:361-368`、`:377-378` | 改写/删除 `<package 父>/ec_recovery_v2_campaign/attempts_ledger.json`，或把 p4 条目改成 `terminal=true,accepted=false,evidence_complete=true` | 可**重复 p4**（另有 journal/预留锁兜底）或**抢跑 p7**（无第二道防线）；违反"未知不得当作已决" | 账本 append-only＋内容哈希链；或与 journal/sacct 交叉核验后才认 `terminal/accepted` |
| **R5** | **同名不同架构的两个 `attempts_ledger.json`** | 包内 `work/hpc_ec_recovery_v2_p4_20261029/attempts_ledger.json`（通用 schema，供 `:300-322`）vs `:368` 战役账本（candidate/submitted/…） | 把包内那份当战役账本传入 | 会被 `:388` `malformed EC campaign ledger entry` 拒（**fail-closed，尚好**），但人极易混淆、误判"账本已就绪" | 战役账本改名（如 `campaign_ledger.json`），并在 manifest 写明路径 |
| **R6** | **`first_batch_reserved_core_hours` 可把预留压到任意小** | `:597-609`（正值逐字采用）、`:611-613` | manifest 声明 `first_batch_reserved_core_hours: 1` | 不变式通过，而实际分配是 `cores×wall_hours×元素数` ⇒ **账面预留与真实占用脱钩**（EC 有 `:141-146` 兜底，**其他 profile 无**） | 增设**下限**校验（≥ `cores×wall_hours×jobs`），而非仅"为正" |
| **R7** | **`--attempts-ledger` 文件缺失抛未捕获异常** | `:709-710`（`read_text` 无 try） | 传了不存在的账本路径 | 输出 traceback 而非既有 `REFUSED: …`/exit 2 CLI 契约（`:719-721`）⇒ 调用方/测试按退出码判定会误读 | 并入 `try` 转 `ValueError` |
| **R8** | **journal 缺失＝"从未提交"（未知状态的 fail-open 默认值）** | `:541-544`、`:545-549` | journal 被删/改名，或同批只存在旧记录被清 | 重复提交只剩本地预留锁＋远端锁兜底（两者都可被本地删除）⇒ 幂等保护可被"删文件"绕过 | 对"journal 存在但无记录"与"journal 不存在"区分处置；保留远端/独立幂等证据 |
| **R9** | **合同模块惰性加载无 sha/版本校验** | `:349-358` | `ec_recovery_contract.py` 被替换 | 合同常量（`EC_CANDIDATES`/`EC_ELEMENT_CORE_HOURS`/`EC_CAP_CORE_HOURS`/`EC_MAX_SUBMITTED_ELEMENTS`）静默改变判定，且**无守卫**（与本项目"两份副本无一致性守卫"同族） | 记录/断言合同模块 sha256（或把常量写进 journal） |
| **R10** | **4 核检查无法区分 profile** | `:582-586`（仅比 `declared_cores == resources["cores"]`） | `orca_production_4h_v1` 与 `orca_production_v1` 同为 4 核 | 核数校验不能替代 profile 身份校验 ⇒ 与 R2 叠加 | 与 R2 一并修（身份绑定） |

**成立的关键保护（正面核实）**：① 合同校验确在**所有副作用之前**（`:554-561` < `:563`），与 docstring `:434-437` 一致；② 合同**不信任调用方布尔**，`ec_active_pending`/`ec_submitted_elements` 均从历史**重算**后传入（`:450-453`,`:466-467`），并在合同内**双向校验**计数与历史吻合（`ec_recovery_contract.py:104-116`）；③ **未知结果保守占位**——`finally` 无条件追加战役记录且写 `accepted=None`/`terminal=False`（`:501-513`,`:671-675`）⇒ 与用户"不得把未知读成已决"一致；④ 预留锁 `x` 模式＋先写 `submitting`（`:636-642`）⇒ 本地并发幂等；⑤ CLI 不能放宽 cap（`:531-534`）、profile 取自**被哈希的 manifest** 而非 CLI（`:166-180`，`manifest_sha256` 入 journal `:631`）；⑥ 几何/候选三处交叉比对（`:420-427`,`:470-475`）。

---

## 6. 审查过程的可复核性声明与未覆盖项

1. **对象在审查中途被改**（实测）：首读 `531 行 / sha 2f900fd9…` → 终读 `727 行 / sha 7d0e0278…`；同一 `ops_inspect` 批的多个 range 甚至返回了**不同版本**的行号（旧版本 `def main` 位于 `:491`，新版本位于 `:687`）。**故本报告只承认 §0 表中 sha 对应的行号**；若该文件再被修改，请以本报告的函数名/字符串锚点重新定位（本报告每条已同时给函数名与判据原文，避免只靠行号）。
2. **未运行**：未执行任何提交/`--collect-sacct`、未调用 bridge、未跑 pytest（含 `test_ec_submit_entry.py`）、未写 `outputs/**`。结论均为**源码静态核验 + 磁盘产物读取**。
3. **未能覆盖**：`tests/` 的实际通过状态（未跑）；`ec_recovery_v2_p4_20261029` 包内 `attempts_ledger.json` 的具体内容与 schema 合规性（未读取，仅据文件名与 §R5 推断存在同名冲突）；`build_ec_recovery_package.py`（生成器，`manifest.json:35` 自述）本身的约束（不在本任务范围）。
4. **与 t11 简报的偏差（如实）**：简报称"8 类坏请求"，实列 **9 个短语**，本报告按 9 类逐条落位（§3）。

---

## 7. 结论行

**27 项检查 17 成立 10 不符**（§1 三项＋§2 四项＋§3 九类＋§4 一项＝**成立 17**；§5 的 R1–R10＝**不符 10**）。
**成立 17**：① 调用链 22 步完整、行号绑定 §0 sha；② 副作用顺序正确（全部校验都在 `:563` 之前）；③ 唯一最优点已在位（`:554-561`）；④ manifest 字段读取与行号一致；⑤ 通用 attempts ledger 语义明确且按 allocation 去重（`:300-322`）；⑥ 战役账本语义明确、缺文件≠有记录、畸形即拒（`:361-400`）；⑦ journal＋预留锁双幂等（`:539-552`,`:636-642`）；⑧–⑯ 九类坏请求各有 fail-closed 拒绝点（§3 表）；⑰ 旧 profile 回归面清晰且成对测试存在（§4）。
**不符 10 ＝ R1–R10**。其中 **R1、R2 高危**：① `submission_gate:"HOLD"`／`submitted:false` 在提交器内**全文零命中**（从不被读取）⇒ 被标 HOLD 的 EC 包在空战役历史上**可通过合同并被真正提交**；② profile 由包内 manifest 自选（`:177`,`:558`）⇒ 只改一个字段为 `orca_production_v1` 即可**整体绕过 EC 合同**（cap 800、免账本、免候选顺序）。R4／R8 同族：把"未知/文件缺失"当作"未提交"的 **fail-open 默认值**。
**最需立即处理 2 条**：**R1**（把 manifest `submission_gate`/`submitted` 接进入口拒绝）与 **R2**（让 EC 合同绑定"包身份"而非"manifest 自选 profile"）——两者叠加时，一个被标为 `HOLD` 的 EC 包**可以通过真实提交路径被提交**。

---

### 附：本报告对 t11 看板归属的说明（非审查内容，但必须记录）
`team_task_update(claim, t11, expected_revision=2)` **被拒**：`Error: task "t11" is owned by "triage-auditor"; release or reassign it first`。即 **t11 当前由 `triage-auditor` 持有（claimKind=auto，claimedAt 2026-10-29T01:28:13Z）**。按本项目"写入面归属以任务板为准、不以消息措辞为准"的纪律（lesson `0mvnryesh`／`0mvsd299`），我**未**强行抢占、**未**改名或释放他人认领；本报告写在我方被指定的空目录（写入前实测 `agent_review_submit_entry/` **不存在**，无覆盖）。**请 Lead 决定**：release/reassign 给本会话并收口，或直接采信本报告。另：审查对象 `submit_hpc_batch.py`／`ec_recovery_contract.py` **均为未提交改动**，且审查期间被并发写入——**入库前应重新绑定 sha 复核 §0 行号**。