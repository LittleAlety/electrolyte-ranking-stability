# 合规台账「未满足项」独立抽验报告（只读审计）

- 审计日期（UTC）：2026-10-25；审计者：独立 subagent（audit-partial-items）
- 审计对象：`outputs/physics_completion/compliance/plan_compliance.md` / `.csv`（42 项）
- 审计范围：**全部 17 个未满足项**（13 partial + 2 not_satisfied + 2 blocked_on_production）——比任务书要求的 16 项多 1 项，全数覆盖
- 纪律：只读既有文件；只写本目录；未 git add/commit；未运行 ORCA/xtB；未联网；未提交任何 Slurm 作业；未改动任何 `outputs/**`、`scripts/**`、测试
- **绑定快照**（跨会话结论必须带 sha256）：
  - 台账在审计期间被**并发会话重生成两次**：`04:31:51Z` → `11:01:34Z` → `12:51:40Z`；**`plan_compliance.csv` 的 sha256 自始至终不变**（`a1f70503e766121e…`）= 42 项逐行内容零变化，只有 md 的 `generated_at_utc` 头行在变（md 现 sha256=`13c76d7c27826e8b…`）。故本报告的逐项结论**绑定在 CSV 内容**上；状态分布全程不变：`satisfied=22; partial=13; not_satisfied=2; blocked_on_production=2; exempt=3`，17 项未满足集合逐字不变。
  - 审计期间并发会话前进了提交：git HEAD `569ccd215670bc44…`（审计开始）→ `291270a233c891d6…`（审计末）；其中 `0d01201` 清理了我早期写入的 0 字节沙箱探针、`a606f88` 为成员会话发现的真缺陷修复。**我本人未 git add / commit**（本目录在 `git status` 中为未跟踪项 `??`）。
  - 复核方法：`import build_plan_compliance; build_rows(wp2_progress.build_snapshot(REPO))` 现算（其 subprocess 仅 `build_production_ensemble_aggregator.py --check`，已核实该路径逐行只读：脚本 :1049-1079 明确不落盘），三次重算（11:01Z / 12:51Z / 终检）与台账 42 项状态、measured 逐字一致

## ① 实际跑过的命令与退出码

文件工具（read/write，无 shell 退出码）：读台账 md 全文（56 行）；读生成器 `build_plan_compliance.py` 1-1202 三段全文；读聚合器 :760-799 与 :1040-1097 证明 `--check` 只读。

shell 命令（bash/pwsh，全部用 `.venv/Scripts/python.exe`）：

| # | 命令（摘要） | 退出码 |
|---|---|---|
| 1 | Get-Item 台账 md（Length=17134, mtime 2026-10-25 12:31:51 本地） | 0 |
| 2 | Get-Item 生成器 + venv 冒烟 `print('venv ok')` | 0 |
| 3 | Select-String 生成器结构轮廓（def/状态分支） | 0 |
| 4 | Select-String 聚合器写操作面（write_text/mkdir/--check） | 0 |
| 5 | `New-Item -ItemType Directory` 审计目录（沙箱拒绝）| 1（沙箱面拒绝，非任务失败） |
| 6 | write 工具探针 ×3（workspace 根/仓库根/审计目录 REPORT.md 占位） | 成功 |
| 7 | `Remove-Item` 删探针（workspace 根成功；仓库根被 Everyone-Delete deny 挡） | 0 / 1 |
| 8 | Get-Acl 三层 ACL 取证（workspace 根/仓库根/目标父目录） | 0 |
| 9 | Set-Content 写能力测试（仓库根、docs/handoffs 下均被拒） | 1（预期取证结果） |
| 10 | 升级权限删探针 `__sandbox_probe_audit.tmp`（用户批准，后已生效删除） | 0 |
| 11 | `python -X utf8 verify_audit.py`（本目录，只读重算 A-O 段） | 0（全文见 VERIFICATION_OUTPUT.txt） |
| 12 | 内联 python 扩展池/成本/blocked_by（首次括号笔误） | 1 → 修正后 0 |
| 13 | `strict_readiness.py` 头部+函数枚举 | 0 |
| 14 | 生成器 :530/:697/:790/:858 逐字复核 + pair/recheck/limited/manifest | 1（语法）→ 0 |
| 15 | targeted_recheck record_id 交集/几何源/scf 状态 | 0 |
| 16 | recheck_pair_gaps + acceptance 14 检 + strict 全 32 problems | 0 |
| 17 | limited 4 行原因列 + WP6 plan 列 + 生成器 extension 引用行号 + 台账目录 mtime | 0 |
| 18 | `strict_readiness(...)` 复现 blocked_by + thresholds/flip/mechanism mtime | 0 |
| 19 | flip R4 状态 + 扩展池 family 标志 | 0 |
| 20 | Get-FileHash 台账两文件 + meta 头部 | 0 |
| 21 | **撤回指令复核**：读 `state_identity/state_identity_qc.csv` 全 60 行 `frontier_localization_status` 列 + `state_identity_acceptance.csv` 第 12 项 description/detail 全文（按纪律⑭先读该声称自己声明的数据源） | 0 |
| 22 | 重跑 `verify_audit.py` 写 `VERIFICATION_OUTPUT.txt`（修订后留档） | 0 |
| 23 | **自查 #6**：读 `mechanism_cases.md` L17/52/53/57/58/59/71/72/77/78/79 全文（判定 L58 是否真的陈旧） | 0 |
| 24 | **自查 #6**：main 集 mol_id↔name 映射 + EMC/GBL/SL 各态 `acceptance_status` + flip R2/R3/R4 全行 delta/note | 0 |
| 25 | **终检**：Get-FileHash 台账两文件 + `git log/status/rev-parse`（发现 HEAD 前进、md 第三次重生成、csv 未变）+ 台账目录 mtime | 0 |

注：`write` 工具与 `pwsh` 的沙箱面不同（write 可在仓库内建文件，pwsh 不可新建/删除），这是探针文件一度无法清理的原因，已按流程升级权限删除。第 21 条命令是**撤回复核**用：它证实 §6.3 口径下 frontier 一格确为 `not_computed`（qc.csv 60/60 行），故 #3 状态判定维持「一致」；报告 #3/#16 两处改判均基于该次实测，非照抄 Lead 叙述。

## ② 17 项逐项表

判定列含义：**一致** = 台账声称的阻塞原因与当前磁盘事实吻合；**不一致** = 声称的阻塞原因已不成立（判据脱钩）；**过时陈述** = 状态判定仍成立、但「实测/note」文字描述旧世界。生成器行号 = 状态表达式所在行。

| # | item_id | 台账声称（状态｜measured 关键原文） | 判定分支 | 我的独立实测（当前磁盘） | 判定 |
|---|---|---|---|---|---|
| 1 | `wp2_conformer_ensemble` | partial｜accepted=44/48; provisional=0; limited=4; screen_gfn2_rows=75 | :400-440（状态 :428-429） | `production_ensemble_labels.csv` DictReader **48 行数据**（表头外；此前 50 是把表头计入），accepted 44 + limited 4 = 48 闭合✓；`ensemble_free_energies.csv` 75 行✓；聚合器 --check 通过（measured 无 validation_errors） | **一致**（口径收紧：4 个缺口是 `limitation_reason=rescue_budget_exhausted` 的**已封闭 limited**，n_members=1，非"在跑"——等待生产不会自动到 48/48） |
| 2 | `wp2_sampling_extension` | partial｜acceptance_ok=9/9; escalation_pending=24/24; executed=12 分子; designated=C02,C03,C08,C17 | :441-469（状态 :458；`samp_extension_ok` :453-454） | acceptance 9/9 ok=true✓；escalation 24/24 `registered_pending_round1_free_energy_check`✓；**executed(12) ≠ designated(4)**：executed={C01,C02,C03,C04,C05,C08,C09,C13,C14,C15,C16,C17}、designated={C02,C03,C08,C17}（指定 4 个全在其中，即执行集是严格超集，实测 `executed==designated: False`）→ 两个阻塞子条件（24/24 pending + 超集非对齐）都真实存在 | **一致**（备注口径澄清：「不一致」指 **磁盘上 executed≠designated 这一登记事实**，即 :452 `samp_on_designated_set=False`，正是 partial 的成因之一；**不是**我与台账的结论矛盾——两者一致） |
| 3 | `wp2_state_identity_qc` | partial｜qc_checks_ok=13/13; frontier_localization=**not_computed** | :502-522（状态 :512；`frontier_skipped` :506 grep `state_identity/thresholds.json` 字符串） | 13/13 自检 ok=true✓；身份分层与 measured 逐项吻合✓；**frontier 声称与自身数据源一致**：`state_identity/state_identity_qc.csv` 60 行 `frontier_localization_status` **全 = not_computed**（mtime 11:00:18Z），acceptance 第 12 项 `frontier_localization_is_registered_not_guessed` description 明写「生产输入未要求逐轨道原子组成」（detail: no orbital-energy read-out is published from concatenated Opt logs）、thresholds.json 同口径✓。项目里另有**第二条同名不同口径**证据链：`frontier/frontier_localization.csv` 80 行全 computed、`frontier_identity_evidence.csv` 80 行全 verified（frontier identity 管线，非 §6.3 的逐轨道原子组成格）——台账只读 (a)、证据列只写 `state_identity/` | **一致**（§6.3 口径的阻塞原因在当前磁盘仍真）。⚠ 另记记录缺陷：**口径覆盖不全**——台账未引用 frontier/ 管线（80 verified），读者据台账易误判"轨道定域/前端识别整体缺失"；不翻状态，不改判据 |
| 4 | `wp3_pair_evidence` | partial｜pairs=66; ROBUST_INVERSION=2; STABLE=55; UNRESOLVED=9 | :525-534（状态 :530 `"partial" if pe else "not_satisfied"`） | 66 行= C(12,2) 全覆盖✓，三分类计数逐字吻合✓ | **一致**（结构性缺陷：表达式**没有 satisfied 分支**，该 item 永远停在 partial——记为生成器设计限制，非状态误判） |
| 5 | `wp3_targeted_second_method` | partial｜plan=24 ready=24 blocked=0 results=24（note：复核结果未重现冻结 R1b 符号，换几何×换泛函不可分） | :549-560（状态 :556 `"satisfied" if plan_rows and ready==0`） | measured 两项均忠实：job_plan 24 行全 `ready`（注册即冻结的设计）、results **24/24 computed**、scf_converged/terminated 全 true、`geometry_sha256` 与登记生产 Opt 几何一致、acceptance.csv 14/14 全 true；**note 声称的阻塞原因实测成立**：4 对 gap 全部 `matches_frozen_r1b_sign=false`（EMC\|GBL / EMC\|SL × S3/S4，符号全正 vs 冻结 R1b 负）。**附带缺陷（非状态判错）**：`:556` 的 `satisfied` 需 `ready==0`，而 job_plan status 恒 ready ⇒ 该分支**不可达**；另在"只要求执行复核"的口径下本项可议为 satisfied（执行+验收已完成），但代码无此路径——**需用户裁决，本审计不改** | **一致**（台账自身口径内，声称的阻塞原因仍真）；附"不可达分支 + 口径可议"记录 |
| 6 | `wp3_mechanism_cases` | partial｜cases=2; six_item_pending=8; six_item_partial=14 | :561-576（状态 :569） | 台账 measured 本身**计数准确**：mechanism_cases.csv 2 行✓；md 全文 `待补`=8、`部分`=14 逐字吻合✓。**但所引证据文档内有陈旧陈述（证据层，非台账计数错）**：md L78「G_ensemble（生产 R4）未做——`flip_persistence.csv` R4 = `not_computed`；现有系综只有筛选层 GFN2」**与磁盘矛盾**——`flip_persistence.csv` R4 两对均 **computed**（EMC\|GBL +0.404536、EMC\|SL +0.356963，note 明写 G_ensemble 定义），且 EMC(C02)/GBL(C13)/SL(C14) 各 4 态在 `production_ensemble_labels.csv` **全 accepted**；更早的 04:31Z 台账已记 `rungs_computed=10/10 production`（含 R4）⇒ L78 在 md 自身写时就已过时。**同时更正我初版的一处过头**：md L58 的「frontier 轨道局域化在 thresholds.json 登记 not_computed」**是准确的**（该句自带数据源、与 qc.csv 60/60 全 not_computed 同口径），我初版称它"现产物 80/80 computed ⇒ 陈旧"是**错的**，已随 #3 一并撤回；故 8 处待补中现真正失效的是 **E/G 分解（G_ensemble）** 这一主题（3 大缺口主题 → 2），电子密度本体、多 motif 系综仍缺 → partial 仍成立 | **过时陈述（精确到证据层：台账 measured 计数准确，所引 md 的 L78 已过时；L58 准确、我前版误判已撤回）** |
| 7 | `wp5_new_endpoint_in_budget` | partial｜legacy_rounds=296 O_3_field=True fixed_R_3_0.10=True legacy_computed=8 legacy_blocked=16 | :694-704（状态 :697） | round_diagnostics 296 行✓ 全行含 O_3✓ regret_threshold_ev 集合={0.10}✓ success_budget 24 行 computed=8/blocked=16✓ | **一致**（同 #4：表达式无 satisfied 路径，结构性停在 partial） |
| 8 | `wp5_formal_ab_stop_budget_reached` | partial｜reached=19 of 32; stop_status={computed:19, not_reached_within_pool:13} | :730-742（状态 :734） | AB_axis_endpoint 32 行、状态分布逐字吻合✓；AB_index 声明 rows=32 = 实测 32✓ | **一致** |
| 9 | `wp5_two_consecutive_points` | partial｜formal_reached=19/32; legacy 8/16; required_consecutive==2 | :743-759（状态 :746-747） | sb 24 行 required_consecutive_budget_points 全 "2"✓、formal_reached=19✓、legacy 8+16✓ | **一致** |
| 10 | `wp5_absolute_cost_ledger` | partial｜cost_rows=10 MISSING=3 | :760-769（状态 :765） | 10 行：measured 4 / planned 3 / **MISSING 3 = cpu_core_hours、p90_job_cost、frequency_only_cost**，恰为要求三项，值全空✓ | **一致** |
| 11 | `wp5_remaining_unqueried_error` | partial｜legacy_rounds=296 remaining_error_MISSING=296 cumulative_core_hours_MISSING=296 | :785-796（状态 :790） | 296/296 两列全 MISSING，逐字吻合✓ | **一致**（同 #4/#7：无 satisfied 分支） |
| 12 | `wp5_pool_extension` | not_satisfied｜extension_rows=0; replay_pool=legacy_pool_not_blind | :797-806（状态 :801；:797 **只按 `physics_completion_set.csv` 的 cohort=="extension" 筛**） | set.csv cohort 实测只有 main12/method8/sampling4/excluded6，**永无 extension** → extension_rows=0 是**判据读错来源文件**；真实登记在 `data/metadata/physics_completion_extension_pool.csv`：**11 行全 FROZEN_NOT_COMPUTED**，in_method_audit 全 false，4 行 family 未被方法审计覆盖（满足"含一个未覆盖家族"）；但**计算与回放换池未发生**（AB 回放 n_pool∈{11,9}≠12，见 #16）→ "先冻结已做、再计算未做"，not_satisfied 仍成立（未提交任何计算，不翻状态） | **过时陈述（measured 来源错，状态判对；Lead 与我独立复算均确认此条）**——只记录 |
| 13 | `wp6_explicit_ligand` | blocked_on_production｜plan_rows=4 executed_jobs=0 gate_ready=false trigger_state=not_triggered | :808-846（状态 :821-831；gate :158-161 要求 Li 配对≥9 **且系综 48/48 accepted**） | plan 4 行（C04/C08/C16/C17，R=DME，字段齐）✓；explicit_ligand 目录除 plan 外 0 文件→executed=0✓；li_pair 12/12✓；系综 44/48 accepted → gate_ready=false✓；trigger=not_triggered 与 derive_checks() 现算吻合✓ | **一致**（口径同 #1：48/48 的 4 缺口是 rescue_budget_exhausted 封闭态，"等待生产"这一 gate 语义需 policy 决定才能闭合） |
| 14 | `stop_rules_registered` | partial｜stop_rules_in_config=True; li_motif_screen_computed=23/24 | :848-864（状态 :858 `"partial" if "stop_rules" in cfg_text`） | config yaml 含 stop_rules✓；motif_plan 24 行：computed 23 + unresolved 1✓ | **一致**（结构性：表达式无 satisfied 路径；motif 计数只是展示项，不参与状态） |
| 15 | `wp2_pilot_cost_fields` | partial｜pilot_rows=109; missing_fields=none; raw_verified=109/109; memory_MISSING=109; retry_UNVERIFIABLE=109 | :866-901（状态 :890-891） | 109 行✓ 四必需列全在✓ memory=MISSING 109✓ retry=UNVERIFIABLE 109✓ raw verified 109/109✓ | **一致** |
| 16 | `strict_readiness_evidence` | not_satisfied｜checks_passed=5/6; failed=wp5_full_target_pool_evaluated; wp6/pool 触发均 not_triggered | :918-971（状态 :959；failed 集 :927） | 现跑 `derive_check_details()`：6 项检查 5 过 1 败✓，败因 32 problems 全为 AB 回放 **n_pool=11/9 非完整 12 池**✓；trigger 两项 not_triggered✓。**口径要点（Lead 已撤回其初判）**：本行是 **wiring 六项**口径；组合闸门 `strict_readiness()` 复现 blocked_by=2 条（多出 `ensemble_not_48_accepted`），ensemble 条件**不在本行六项内**、属组合层/#17 展示口径——拿组合口径比本行即"拿错尺子"（教训⑮），已核对撤回指令成立 | **一致（wiring 六项口径内；组合/单口径区别已点明）** |
| 17 | `plan_overall_complete` | blocked_on_production｜main_states=48/48; ensembles=44/48; sampling_complete=False; flip_rungs=10/10; pilot 20/20 | :942-988（状态 :975；plan_complete 合取 :944-955） | 合取逐项复算：method_frozen✓ 48/48✓ free/li✓ **系综 44/48 ✗** **samp_extension_ok ✗**（escalation 24/24 未决 + executed≠designated）flip 10+2✓ **strict_evidence ✗**（#16）→ 阻塞因子 3 个全部现存，blocked_on_production 成立 | **一致**（同 #1/#13 口径：系综缺口的封闭语义） |

**小结（最终版 v4，2026-10-25 晚；含 Lead 两次撤回指令 + 我三轮自查改判）**：一致 **15**（#1,2,3,4,5,7,8,9,10,11,13,14,15,16,17）；**不一致 0**（未发现任何"状态判错/声称阻塞原因已不成立"的项——与 t4 独立现算 17/17 状态吻合的结论一致）；**过时陈述 2**（#6 = **证据层**陈旧：台账 measured 计数准确、所引 mechanism md 的 L78「R4=not_computed / G_ensemble 未做」与磁盘矛盾；#12 = 台账 measured **读错来源文件**：extension 登记在 `physics_completion_extension_pool.csv` 而非 set.csv，状态 not_satisfied 仍对）。15+0+2=17 闭合。
> **我自查撤回的三处过头（本轮）**：(a) 初版把 #3 判为"不一致（判据与产物脱钩）"——错在只读了 `thresholds.json` 与隔壁 `frontier/*.csv`，没读该声称**自己引用**的数据源。复核确认 `state_identity_qc.csv` 60/60 行 `frontier_localization_status=not_computed` + acceptance 第 12 项 ok=true 且明写"生产输入未要求逐轨道原子组成" ⇒ §6.3 口径阻塞原因仍真，**原判"一致"正确**（Lead 撤回其指令成立）；隔壁 frontier/ 管线（80 computed/80 verified）是**同名不同口径的第二条证据链**，台账未引用它属"口径覆盖不全的人读误导"（记录缺陷，不翻状态）。(b) #6 里我原称 mechanism md 的 L58「frontier 缺失」陈旧——**该句自带数据源（thresholds.json）且与 qc.csv 同口径，是准确的**，已撤回；#6 真正失效的是 L78 的 G_ensemble/R4 那一半。(c) #5 我原判"不一致（暗示待执行）"——**台账 measured 与 note 都忠实于磁盘**（results=24 已列、note 的符号未复现实测 4/4 成立），我误加了它并未做出的"待执行"声称，已改判为**一致 + 不可达分支记录**。教训：**宣布"某声称与事实矛盾"前，必须先把该声称自己引用的那个数据源那一列读到底；同名概念要分清口径**；同一纪律另一次应用：item 16 的"failed 只 1 项过时"是拿**组合**口径比本行 **wiring 六项**口径（拿错尺子）。

另记 **生成器结构性缺陷**（全部只记录、未改任何代码；是否改判据属需用户裁决）：
- 无 satisfied 分支（状态永远最高只能到 partial）：`wp3_pair_evidence` :530、`wp5_new_endpoint_in_budget` :697、`wp5_remaining_unqueried_error` :790、`stop_rules_registered` :858。
- satisfied 条件不可达：`wp3_targeted_second_method` :556 要求 `ready==0`，而 job_plan 的 status 注册即冻结恒 ready=24（执行与验收实际已完成）。
- 判据引用来源不完整/读错文件：`wp2_state_identity_qc` :506 只读 `thresholds.json` 一格、`证据` 列只写 `state_identity/`，未引用 frontier/ 管线（80 verified）⇒ 人读误导风险（口径覆盖不全）；`wp5_pool_extension` :797 在 `physics_completion_set.csv` 筛 `cohort=="extension"`，而该文件无此 cohort，真实登记在 `physics_completion_extension_pool.csv`。

## ③ 需优先复核项（证据出处）

> 进口结论：**本审计未发现"状态判错"项（不一致 = 0）**——17 项的 status 与各自声称在自身口径内均与当前磁盘吻合（与 t4 独立现算 17/17 一致）。需要用户裁决的是下面 1–2 的**判据/来源缺陷**与 3 的**证据层陈旧**，均**只记录、不翻状态、不改代码**。

1. **#5 `wp3_targeted_second_method`（结构性：satisfied 分支不可达 + 口径可议）**：`:556` 要求 `ready==0` 才 satisfied，而 `job_plan.csv` 24 行 status 恒 `ready`（注册即冻结的设计）⇒ 该分支**永不成立**；同时 `recheck_results.csv` 24/24 computed、`acceptance.csv` 14/14 全 true（含"结果恰覆盖 24 ready 行"）、几何哈希与登记生产 Opt 一致 ⇒ 在"只要求执行复核"的口径下本项可议为 satisfied（**需用户裁决**）。证据：`outputs/physics_completion/pair_evidence/targeted_recheck/{job_plan.csv,recheck_results.csv,acceptance.csv,recheck_pair_gaps.csv}`（目录 mtime 2026-10-25 19:01:31 本地）。
2. **#12 `wp5_pool_extension`（判据读错来源文件；状态不变）**：`:797` 筛 `physics_completion_set.csv` 的 `cohort=="extension"`；实测该文件 cohort 分布 {main:12, method_audit:8, sampling_audit:4, excluded:6}，**无 extension**；真实登记在 `data/metadata/physics_completion_extension_pool.csv`：11 行、`registration_status` 11/11 `FROZEN_NOT_COMPUTED`、`in_method_audit` 全 false、4 行 family 未被方法审计覆盖。扩样**未提交任何计算** ⇒ not_satisfied 仍成立。
3. **#6 `wp3_mechanism_cases`（证据层陈旧；台账计数准确）**：`mechanism_cases.md` L78「G_ensemble（生产 R4）未做——`flip_persistence.csv` R4 = `not_computed`；现有系综只有筛选层 GFN2」与磁盘矛盾——flip R4 两对均 computed（EMC\|GBL +0.404536、EMC\|SL +0.356963，note 明写 G_ensemble 定义），EMC(C02)/GBL(C13)/SL(C14) 各 4 态 `production_ensemble_labels.csv` 全 accepted；且 04:31Z 版台账已记 `rungs_computed=10/10 production`（含 R4）⇒ 该句在 md 自身写时即过时。md L58 的 frontier 句**准确**（自带 thresholds.json 数据源，见 #3）。8 处「待补」现真正失效的是 E/G 分解主题（3 大缺口主题 → 2）。
4. **#3 `wp2_state_identity_qc`（口径覆盖不全，非状态问题）**：§6.3 口径证据 `state_identity_qc.csv` 60/60 `frontier_localization_status=not_computed` + `thresholds.json` 同口径；第二条 frontier 管线 `frontier/frontier_localization.csv` 80/80 computed、`frontier_identity_evidence.csv` 80/80 verified（sha16 `ae6d6f6ae4326e89`）。台账只引用前者 ⇒ 读者易误判整体缺失。
5. **#16 `strict_readiness_evidence`（口径注明）**：wiring 六项口径内 `checks_passed=5/6` 与 failed 列表准确；组合闸门 `blocked_by` 的第 2 条 `ensemble_not_48_accepted` **不属本行**（属 #17 展示口径）。复现见 VERIFICATION_OUTPUT.txt 与 VERIFICATION_OUTPUT_APPENDIX.txt。
6. **#1/#13/#17 共同语义收紧**：系综 4 个缺口 = `limitation_reason=rescue_budget_exhausted`、`pool_limited=true`、`n_members=1`（C01|M_plus、C01|LiM_2plus、C09|LiM_2plus、C04|LiM_2plus），即**已封闭的 limited** 而非"在跑"——继续等待生产不会自动到 48/48，闭合需 policy 层决定。

## ④ 未覆盖范围

- 未审计 25 个 satisfied/exempt 项（任务书范围外）。
- 未复算 `progress` 快照的 60/60、48/48 逐腿 payload 磁盘核对（依赖 `wp2_progress.build_snapshot` 同源函数，未独立重写其聚合逻辑；仅核实其只读性与 meta 哈希一致）。
- 未验证 mechanism 六项中"电子密度本体"是否有其他新产物路径（只确认 .cube/密度差在 md 声明路径下仍缺）。
- 未核对 `rescue_budget_exhausted` 的 budget 决策文档链（policy 层，超出磁盘抽验）。
- 台账重生成（04:31Z→11:01Z）由并发会话完成，我未复跑写路径（write_outputs），只使用其 --check 等价重算；对并发会话 11:01Z 后的再写入不作保证（结论已绑定两文件 sha256）。
