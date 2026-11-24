# EC/DMC 预注册草案 —— **独立复核**（t7，2026-10-28）

> **角色**：只读独立复核。本报告**不修改任何生产代码/脚本/测试**，**不调超算**，**不运行生成器**。
> **⚠ 产物占用声明（重要）**：本任务指定的输出路径 `prereg_audit_20261028/REPORT.md` **已被占用**（同日 16:33:53 由并行会话产出，sha256 `052604958fae…`，结论「28 项检查，28 成立，0 不符」）。按本项目单写入者纪律（`SESSION_CLAIMS` 占用登记、`0mvmdttum` 准则），**我未覆盖它**，只读引用；我的独立结论落在本文件。是否合并/替换由 Lead 审议决定。
> **本报告与既有两份审计（`ec_prereg_fast_audit`、`dmc_prereg_fast_audit`，均未入库）逐条对过的差异见 §6。**

## 0. 审计对象与快照（跨会话结论绑定 sha256）

| 对象 | sha256 | mtime (UTC) |
|---|---|---|
| `EC_PREREG_DRAFT_20261028.md` | `306ca7729be4cdb519a488ab706274cdd7bc35ac791099a5a3ec70afcea1bdaf` | 2026-10-28T16:14:35Z |
| `DMC_PREREG_DRAFT_20261028.md` | `6fb2f48e25f4f0efa2a078810cc161ca8ebb8738d729b275647555513f43fbae` | 2026-10-28T16:14:57Z |
| `prereg_audit_20261028/REPORT.md`（**既有，未覆盖**） | `052604958fae6887b31ff7b46746d7d29689883758b99777f464782ebc5c8776` | 2026-10-28T16:33:53Z |
| `ec_prereg_fast_audit/REPORT.md`（既有） | `38ed79620a846ac089cd67bdbe7ebb9cf5ed3c4eff3369e3bd0cc1b2f6e76f65` | 2026-10-28T16:28:41Z |
| `dmc_prereg_fast_audit/REPORT.md`（既有） | `a1fa211ecdf9e06631717ebc37c1b43fe038291ebd37fbc0a888b51c040c0fe7` | 2026-10-28T16:30:06Z |
| `INDEPENDENT_START_CRITERIA_20261027.md`（判据源） | `45495a6a9d92ba65d2b94e86c3ef0411a887e973b82da273fd996a8533553996` | 2026-10-27T10:12:58Z |
| `DOL_EC_STAGE_REPORT_20261027.md`（草案上游来源） | `771cfb768d9f0bf86e67b18214ea9470cc47987b14bcfe611810a2337b61bc76` | 2026-10-28T16:14:22Z |

仓库 HEAD（复核时点）：`216a603744b5a7e2fe3d22a116919b4db81907fe`（`216a603` 2026-10-28「限制报告 §8.4 更正」）。

## 0.1 结论行

**37 项检查 18 成立 17 不符**（另 2 项部分成立；不符项去重后 = **16 条缺陷/缺口**，见 §7）。
**最严重 3 条**：**F1（EC §3 停止条件把「单盆地」判成失败，与 `single_basin_verified` 及用户 H3 裁定相反——会让本轮在「用户认可的恢复情形」下被判 `limited`）**、**F2（EC §8「strict 5/6→6/6」在数学上不可能由 EC 单独达成）**、**F8（DMC 取「rescue 上限 256 CH」，但两态 `limitation_reason=rescue_budget_exhausted`，账本明写「再算需要另立版本，不是继续花这一包」）**。
**红线总判**：两份草案的**声明层**红线齐备，但**执行层**有 3 处不成立（F1 以盆地新颖性替代阈值验收、F5 术语错标、F4 缺命名族红线），故**不能给出「未违反任何项目红线」的结论**——与既有审计的结论相反（详见 §6）。

---

## 1. STAGE1 完整性检查

**结构计数成立**：EC 草案 §1–§9 = **9 点**，DMC 草案 §1–§10 = **10 点**，与 `DOL_EC_STAGE_REPORT_20261027.md:144,150`（「EC 预注册：9 点」「DMC 预注册：9 点」，DMC 实交 10 点）逐项对得上。**但结构齐 ≠ 实质齐**，逐点核出以下缺项：

| 编号 | 缺项 | 现状（file:line + 原文） | 判定 |
|---|---|---|---|
| S1 | **无墙钟 / profile 行（两份都缺）** | EC §2「本轮可用预算 ≤32 CH／并发上限 1 腿／核算口径／停止预算」；DMC §3 同构——**均无墙钟与 resource profile** | **不符**。`recovery_contract.json:7`：「a per-batch wall-clock exception (**4 cores x 12 h** x max 2 legs, reserved 96 CH…) **The v1 general production wall clock (4 h) stays unchanged for every other batch**」⇒ 新批次默认 **4 h/腿 = 16 CH/腿**，12 h 例外**只挂 `dol_ec_recovery_v1` 这一个批次**。EC 的「5 探针 ≤32 CH」在 4 h 口径下最多可达 **80 CH > 32 CH**（见 F10） |
| S2 | **EC 缺候选门前置** | DMC §8：「**必须**：新起点来源通过 `candidate_gate_contract=validate_candidate_start_v2`」；EC §7 只有「用户批准／gate code audit／独立预算」三项 | **不符**（F12）。P1 原话「把这个门接到**候选注册与提交前**」+ 既有缺口（提交器仍不读任何 gate verdict）⇒ EC 是唯一真正引入新起点的这一轮却缺该前置 |
| S3 | **无「每态 ≤2 起点 + ≤1 有因补救」额度声明** | 授权明文（`0mvpw51rb`／`DOL_EC_PRODUCTION_COVERAGE_PLAN_20261027.md`）：每态 ≤2 独立起点、≤1 有因补救 | **不符**。EC §3 只说「5 探针」，未说明这些探针**占几条起点额度**（5 条探针 > 每态 ≤2 起点 ⇒ 需要裁定或改写为「1 起点 + 扫描」） |
| S4 | **停止预算非数值** | EC §2「停止预算｜TolE 再次失败、成本超限、或达到探针边界」——三项都是定性触发器；§3 又重复一遍 | **不符**。设计框架要求「成本上限」可判定（对比 DMC §3 给了 `≈55 CH` 数值） |
| S5 | **DMC 缺腿数与两态分配** | DMC §2 只列选项 A/B/C，§3 给「最多 2 腿并行」，**无「本轮总共几腿、两态各几腿、选哪个选项」** | **不符**。这直接决定预算量级（2 腿 ≈37 CH vs 4 腿 ≈74 CH）与 55 CH 停止预算的正当性 |
| S6 | **无命名族/序号规则（两份都缺）** | EC §4 只写 `work/<new_package>/`；DMC §5 同 | **不符**（F4）。项目红线：「**新版本成员须另立命名族且序号高于该成员全部历史序号**」（`DOL_EC_PRODUCTION_COVERAGE_PLAN_20261027.md:211`、`PRODUCTION_ROLE_WIRING_20261027.md:44`、`wp2_ensemble_closure_plan_v1_4_2.md:594`）。**上一轮 reopt 预注册有这一条**（`DOL_EC_REOPT_PREREG_20261027.md:56`「命名族序号高于全部历史」）⇒ 本轮**回归缺失** |
| S7 | **EC 缺 `single_basin_verified` 三条件** | `INDEPENDENT_START_CRITERIA_20261027.md:67`：「**⚠ 但三个条件必须同时满足**，缺一即退化为 `known_basin_reproduction`（`verdict=unresolved` ⇒ 仍 `limited`）」——① `production_evidence` 完整（`imaginary_modes`／`final_geometry_sha256`／`log_sha256` 非空 + 过冻结五阈值 + 身份 QC）、② `search_scope_documented`（`registered_starts` 非空 且 `search_outcome` ∈ 三个合法值）、③ 该成员进 `latest_members` | **不符**。EC §3 完全未提这三条（F13） |
| S8 | **成本上限与停止预算的约束关系未交代** | DMC §3：`本轮可用预算 ≤256` 与 `停止预算 ≈55` 并列，未说明谁约束 | **不符**（F10 附带） |

**STAGE1 判定**：EC **9/9 结构成立**、DMC **10/10 结构成立**，但实质缺项 8 类（两份共享 S1/S6，其余各自）。

## 2. STAGE2 一致性检查

| 检查 | 判定 | 证据 |
|---|---|---|
| **预算口径与授权池对接** | **部分成立** | EC §2「≤32 CH（**独立于 600 CH 恢复包；须另立版本**）」——与权威账本相容：`recovery_budget_accounting.md:31`「恢复包合计 187.0/600；风险储备 300 未动用」✓。DMC §3「≤256 CH（rescue 上限）」——**与状态事实冲突**（见下） |
| **DMC 预算来源与状态事实相容** | **不符** | 两态 label 均为 `limitation_reason=rescue_budget_exhausted`（`TWO_GATE_READINESS_20261025.md:16-17`；`recovery_budget_accounting.md:37`），同文件 `:41` 明写：「**再算需要另立版本，不是继续花这一包**」；用户重启条件原文要求「**独立预算**并获批准」。⇒ 不能以「rescue 上限」作为来源，须标明是「**新授权额度**」（F8） |
| **并发上限跨草案一致** | **不符** | EC §2「并发上限 **1 腿**（**不可与 DMC 并行**）」vs DMC §3「4 核/腿，**最多 2 腿并行**（避免与 EC 冲突）」——两者不可能同时成立；且均未写账户规则「running+pending ≤2 才投下一批」（F9） |
| **版本化防自动追加** | **成立** | EC §6/§7、DMC §7/§8 均写明 v0→v1 须用户显式批准、失败不沿用旧版本 ID、**禁止自动启动/自动追加/绕过 `acceptance_decision`** |
| **停止条件跨草案一致 & 与冻结验收一致** | **不符** | DMC §4 要求「任一新起点**通过 QC（五阈值、身份、0 虚频）**→ `resolved`」✓；EC §3 **完全没有 QC 限定**，且把「单盆地」判为 `unresolved` ⇒ 与 DMC §4 及 route 判据链相反（F1，红线级） |
| **双重口径预防** | **成立** | 两份均写「只记 `AllocCPUS × ElapsedRaw`」「父行/`.batch`/`.extern` 不进结算」「失败保留实测成本，不删除、不补零」——与实装一致（`batch_cost_settlement.py:117` `per_element_core_hours()`，且 `.batch`/`.extern` 显式拒绝，见 `DOL_EC_STAGE_REPORT_20261027.md:120`） |
| **失败成本/标签不补零** | **成立** | 同上，且「系综标签只认 `accepted`，`limited` 不计入」两份均声明 |

## 3. STAGE3 红线遵守检查（逐条）

| # | 红线 | 草案声明 | 独立判定 |
|---|---|---|---|
| 1 | 阈值不放宽 | EC §9.1／DMC §10.1 ✓ | **执行层不符**：EC §3 的判定只看「是否到达另一盆地」，**没有任何五阈值限定** ⇒ 事实上允许「新盆地但未过阈值」被判 `resolved → accepted`，等价于以新颖性**替代**阈值验收。**声明成立、执行不成立**（F1） |
| 2 | 方法不替换 | EC §9.2／DMC §10.2「wB97X-D4/def2-TZVPD + SMD 不变」✓ | **成立（附条件）**：DMC §2 选项 A（xTB 预优化 3 步）/B（GFN2-xTB VeryTight 预优化）/C（直接 DFT 多起点）属**廉价预优化/多起点**，`recovery_budget_accounting.md:43` 明文列入计划预案（「直接 DFT 多起点、相关扭转扫描或不同廉价预优化」）⇒ **不构成方法替换**；但须明写「**最终 DFT 腿仍走冻结协议 + 六项验收**」（DMC §5 有、§2 缺） |
| 3 | 「40 分子 core set 不扩展」 | EC §9.3／DMC §10.3 ✓ | **不符（术语错）**：本项目 **core set = 18 分子**、**broad pool = 40 分子**（`deliverables/part1/00_项目总览/统一数据文档.md:8,33`：「core set 18 分子 / broad pool 40 分子」）。⇒ 该条应写「分子集（core 18 / broad pool 40）不扩展」（F5）。**既有两份审计都把这句话判成「✓ 与项目红线完全一致」，未核数据集定义** |
| 4 | 不将 `limited` 视为科学通过 | EC §9.4／DMC §10.4 ✓ | **成立** |
| 5 | 不因预算压力修改 `single_basin_verified` 判定标准 | EC §9.5／DMC §10.5 ✓ | **成立（声明）**；但 F1 的判定标准本身已被写反，须一并修正 |
| 6 | 不无限重复审计/自动追加 | EC §7/§9.6、DMC §7/§10.6 ✓ | **成立** |
| 7 | **命名族序号高于该成员全部历史序号**（项目红线，未列入两草案的「不变红线」段） | **两草案均无** | **不符**（F4/S6） |

**STAGE3 判定**：声明层 5/5 齐备，**执行层 3 处不成立**（#1、#3、#7）⇒ 不能给「未违反任何项目红线」。

## 4. STAGE4 与现有证据的一致性

| # | 草案主张 | 权威来源与实测 | 判定 |
|---|---|---|---|
| 4.1 | EC §1「当前 limited，**reopt 失败**」 | `work/hpc_dol_ec_recovery_v1_reopt_20261027/attempts_ledger.json`：`ec_outcome` = "reopt failed the frozen TolE again (abs 6.366e-07 = **3.18x** threshold); … the state KEEPS limited"；`production_ensemble_labels.csv`：EC `acceptance_status=limited` | **成立** |
| 4.2 | EC §8「系综 45/48 → 46/48」 | `recovery_budget_accounting.md:11`：「**45 accepted / 3 limited / 0 provisional**（分母 48 不变）」；DOL 已 accepted、EC/DMC×2 limited | **成立** |
| 4.3 | EC §8「`strict_readiness_evidence` **5/6 → 6/6**」 | `outputs/physics_completion/compliance/plan_compliance.csv:39`：`checks_passed=5/6; failed=wp5_full_target_pool_evaluated`；该检查要求**每组 `n_pool == 12`**（`:49`「n_pool=11 **is not the full 12-molecule cohort**」）。池现测：`LIMITATION_REPORT_20261027.md:157`「池随 45/48 重算为 **A=11/12（缺 DMC）、B=10/12（缺 DMC、EC）**」⇒ **EC 单独通过只把 B 变成 11/12，A 仍缺 DMC ⇒ 该检查仍为 False** | **不符**（F2） |
| 4.4 | EC §8「`plan_overall_complete` 从 `blocked_on_production` → **`partial`**」 | `build_plan_compliance.py:995-998`：`item("plan_overall_complete", "1", …, **"satisfied" if plan_complete else "blocked_on_production"**, …)`——该行**只会取两个值**，从不取 `partial`（`partial` 只是通用 `STATUSES` 成员，`:57`，不用于本行） | **不符**（F3） |
| 4.5 | DMC §1「两轮尝试均 failed QC」「第二轮（p4 筛选后）：**未提交**，因 p4 筛选无新起点」 | `DMC_DECISION_BRIEF_20261027.md:14`：P4 是 **GFN2 筛选**（job 3774215），「所有 DMC 探针弛豫回 `C01#m1` 同一极小（RMSD 0.0013 Å）」——**结果不是 production QC 失败**；`:5`「18 条失败腿 + 4 次重优化 + P4 GFN2 交叉验证」 | **不符（口径）**：§1 同一段自相矛盾（「均 failed QC」vs「第二轮未提交」），且把**筛选轮**并进「尝试」计数（F7） |
| 4.6 | DMC §1「第一轮：**TolE 超差 1.6×–2.2×**」 | `DMC_DECISION_BRIEF_20261027.md:12`：「4/5 阈值过、**MAXstep 差 1.6×** 或 **TolE 差 2.2×**」 | **不符**：`1.6×` 属 **MAXstep（TolMaxD）**，不是 TolE（F6） |
| 4.7 | DMC §2 三选项属「新机制」 | `recovery_budget_accounting.md:43`：计划预案=「**生产级覆盖诊断**（直接 DFT 多起点、相关扭转扫描或**不同廉价预优化**）」，且要求「按态逐个版本化预注册（方法、成本上限、停止条件），**不得沿用旧池回填**」 | **成立**（选项与预案 1:1 对应；且 §5「新起点登记于新包」满足不回填） |
| 4.8 | DMC §2 例「登记 torsion 合法位移，如 `tors_8_0_1_2`」 | `TWO_GATE_READINESS_20261025.md:16`：`DMC\|M_plus` 的 `registered_starts = tors_8_0_1_2` | **成立**（真实已登记起点） |
| 4.9 | DMC §3「单腿 p90（**18.41 CH**）× 2 × 1.5 ≈ 55 CH」 | `DOL_EC_PRODUCTION_COVERAGE_PLAN_20261027.md:150`：「生产腿均值 9.86、中位 8.13、**p90 18.41** CH/腿」；`cost_scenario_index.json`：`free_cation_def2TZVPD` p90 = **18.406222** | **成立**（18.41 为 18.406222 的两位舍入；算术 18.41×2×1.5=55.23≈55 ✓）。但两份草案**均未引用出处**，建议补路径 |
| 4.10 | DMC §8「`strict_readiness_evidence` 5/6 → 6/6（**若 EC 也过**）」；系综 45→47→48 | 系综算术 ✓；池：DMC 两态 + EC 全 accepted ⇒ A=12、B=12 ⇒ **池前置满足** | **部分成立**：`TWO_GATE_READINESS_20261025.md:8` 明写「但**闸门 2 不会仅因此打开**——它还要求按正式协议**重跑** A/B 回放并满足其停止预算判据」，`:33-34`（四策略×四模型×20 repeats、两相邻非耗尽预算点）。草案 §8 未提这一步（F14） |
| 4.11 | 成本数字（EC/DMC 两草案共同语境） | `settlement_per_leg_20261028.json`：DOL `0.9`（`3791416_0`，810 s）、EC `1.115555…`（`3791416_1`，1004 s）、合计 `2.015555…`；该文件 `note` 明记「per-leg assignment **CORRECTED** 2026-10-28：the ledger had DOL/EC **swapped** … JobIDRaw is NOT the element id」 | **成立**，但**识别链必须用 `<array>_<index>`**（`3791416_1`）而非 `JobIDRaw`——这正是 10-28 修掉的交叉互换缺陷（见 F11c） |
| 4.12 | EC §4「输入几何：reopt 收敛末几何（SHA256 登记于 reopt 目录）」 | 该目录确实存在（`work/hpc_dol_ec_recovery_v1_reopt_20261027/snapshots/3791416_{0,1}/job.xyz`） | **部分成立**：口径不够精确——① 未点名 **`job.xyz`**（`DOL_EC_REOPT_PREREG_20261027.md:50` 记录了「初版把 `snapshots/geom.xyz` 误认成末几何 … **真末几何是 `job.xyz`**」这一已发生过的误认）；②「SHA256 登记于 reopt 目录」指向的是**上一批的输入清单**，本轮新起点的哈希必须在**新包**里重新登记（F11） |
| 4.13 | 两草案 §2/§3「`per_element_core_hours()`」 | `scripts/wp_production/batch_cost_settlement.py:117` 实装；`DOL_EC_STAGE_REPORT_20261027.md:121` 记其含 6 个 pytest + RED | **成立** |

## 5. 边角与未验证项（如实）

1. **`xTB 预优化到 3 步`（DMC §2 选项 A）语义不明**：3 步 = 3 个优化圈？3 个梯度步？无法判定其是否会产生「与旧池不同的起点」——缺什么：该选项的 xTB 层约束（level/阈值/圈数上限）与其「起点独立性」论证。
2. **选项 A/B/C 的成本对比缺失**：三选项的预估 CH 未给（选项 C 自述「成本高」但无数值），无法判断 ≤256/≈55 哪个选项装得下。
3. **`gate code audit 通过（不新增 audit 缺陷）`（EC §7／DMC §8）范围未定义**：该审计的对象是闸门模块（`docs/handoffs/four_state_recovery_20261027_gate_code_audit/REPORT.md`），与本预注册文本无关；作为准入条件不可判定。
4. **两草案均未绑定「新产物 → 下游重生成 + `--check`」义务**（项目 7 处同型缺陷清单第 4/5 条）；仅 EC §8/DMC §8 提了「WP5 目标池须同步更新」一句。
5. **远端/超算实况**（新批次默认 profile 与墙钟、QOS 余量）：无法本地验证，本报告只依据 `recovery_contract.json:7` 的契约文本。

## 6. 与既有两份审计的差异（逐条）

| 项 | 既有审计结论 | 本报告独立结论 | 分歧要点 |
|---|---|---|---|
| EC §3 停止条件 | `ec_prereg_fast_audit:31`／`prereg_audit:15`「逻辑清晰，**可执行**」 | **不符（红线级，F1）** | 未与 `INDEPENDENT_START_CRITERIA:64-67`、`DOL_EC_PRODUCTION_COVERAGE_PLAN:220-222`、用户 H3 裁定对账；「单盆地→unresolved」正好把用户认可的恢复情形判成失败 |
| EC §8 strict 5/6→6/6 | `ec_prereg_fast_audit:12`「✓」（仅复述） | **不符（F2）** | 未核 `wp5_full_target_pool_evaluated` 的判定式（要求 n_pool==12 全组）与现测 A=11、B=10 |
| EC §8 `plan_overall_complete → partial` | 两份均未核 | **不符（F3）** | `build_plan_compliance.py:998` 该行只会取 satisfied／blocked_on_production |
| 「40 分子 core set 不扩展」 | `ec_prereg_fast_audit:45`／`dmc_prereg_fast_audit:46`／`prereg_audit:22,30`「与项目红线**完全一致**」 | **不符（F5）** | core set = 18 分子；40 = broad pool（`统一数据文档.md:8,33`） |
| DMC §3「≤256 CH rescue」 | 三份只提「p90 乘数未说明」 | **不符（F8）** | 未与 `rescue_budget_exhausted` + 账本「另立版本，不是继续花这一包」+ 用户「独立预算」对账 |
| DMC §1 失败原因归属／轮次口径 | `dmc_prereg_fast_audit:5`「✓」 | **不符（F6/F7）** | 1.6× 属 MAXstep；P4 是筛选轮非 production 尝试 |
| 并发上限 | 两份各自记录（`dmc_prereg_fast_audit:7` 记 2 腿） | **不符（F9）** | 未做跨草案一致性比对：EC「不可与 DMC 并行」vs DMC「最多 2 腿并行」 |
| 命名族红线 / 候选门前置 / 三条件 | 未检查 | **不符（F4/F12/F13）** | 上一轮 reopt 预注册有命名族条款，本轮回归缺失 |
| 反驳性证据强度 | 两份反复声明「基于 t8/t9 已验证结论」+「未见于权威账本但不构成矛盾」 | 本报告对每条给 file:line + 原文 | 既有审计多处以「草案自设、不冲突」结案，未做数值/判据级反证 |

> 说明：既有审计的 STAGE1「9/9、10/10 ✓」与 STAGE2 版本化、双重口径三项，**与本报告一致**（我独立复核后同样判成立）；分歧集中在 STAGE3/STAGE4 的**实质判据核对**上。

## 7. 缺陷清单（file:line + 触发条件 + 后果 + 建议）

| # | 严重度 | 位置 | 触发条件 | 后果 | 建议 |
|---|---|---|---|---|---|
| **F1** | **高（红线级）** | `EC_PREREG_DRAFT_20261028.md:27-30`（§3 停止条件）；同源 `DOL_EC_STAGE_REPORT_20261027.md:143` | 5 探针**仍落在同一盆地**（且若通过五阈值/身份/0 虚频） | 被判 `unresolved → limited`——**恰好把用户 H3 裁定认可的恢复情形判成失败**；且反向「到达另一盆地→resolved」**无任何 QC 限定**，等于以新颖性替代阈值验收 | 改为：**探针生产腿过冻结六项验收**（五阈值+身份+0 虚频…）且复现已登记极小 + 三条件齐 ⇒ `single_basin_verified` ⇒ `resolved ⇒ accepted`；得新极小且过 QC ⇒ `multi_basin_coverage` ⇒ 同样 accepted；**证据不完整**才 ⇒ `known_basin_reproduction` ⇒ `unresolved`。措辞须与 `DOL_EC_PRODUCTION_COVERAGE_PLAN_20261027.md:220-222` 逐字一致 |
| **F2** | **高** | `EC_PREREG_DRAFT_20261028.md:62`（§8） | EC 单态转 accepted | 「strict_readiness_evidence 5/6→6/6」**不可能达成**：`wp5_full_target_pool_evaluated` 要求每组 `n_pool==12`，EC 只补 B 池一位，A 池仍缺 DMC（现测 A=11、B=10） | 改为「5/6 不变」（或写明「须 DMC 两态也 accepted 才可能 6/6」） |
| **F3** | 中 | `EC_PREREG_DRAFT_20261028.md:61`（§8） | 引用 `plan_overall_complete` 的取值 | 该 item 只会取 `satisfied`／`blocked_on_production`（`build_plan_compliance.py:998`）⇒「→ partial」是**不存在的取值**，下游读者会误以为存在部分完成态 | 改为「`blocked_on_production` 不变；严格总闸门缺口只由 DMC 决定」或按实际取值表写 |
| **F4** | 中 | EC §4:36、§6:48-50；DMC §5:52、§7:66-68 | 新成员/新 attempt 命名 | 缺项目红线「**另立命名族且序号高于该成员全部历史序号**」⇒ 新留痕可能与历史 attempt 混淆（本轮 reopt 预注册有该条） | 两草案各补一条命名族约束，并点名新包名（如 `hpc_dol_ec_recovery_v2_*`） |
| **F5** | 中 | EC §9:70、DMC §10:89 | 引用「40 分子 core set」 | 术语错（core set=18；40=broad pool）⇒ 红线文本指向的对象错，未来执行者可能据此扩错集合 | 改为「分子集不扩展：core set 18 分子与 broad pool 40 分子均不动」 |
| **F6** | 中 | `DMC_PREREG_DRAFT_20261028.md:11`（§1） | 引用第一轮失败原因 | `1.6×` 实为 **MAXstep/TolMaxD**，非 TolE ⇒ 对「失败模式」的陈述与诊断文档不符 | 改为「MAXstep 差 1.6× 或 TolE 差 2.2×（`DMC_DECISION_BRIEF_20261027.md:12`）」 |
| **F7** | 中 | `DMC_PREREG_DRAFT_20261028.md:9-12`（§1） | 引用「两轮尝试」 | 同一段自相矛盾（「均 failed QC」vs「第二轮未提交」）；且 P4 是**筛选轮**（3774215，探针全回 `C01#m1`），其结局是「无新起点」而非 production QC 失败 ⇒ 轮次/口径失真 | 拆成三条独立事实：① 生产层 8 条失败腿（三类 failure）；② reopt1–4/v2 同型失败；③ P4 GFN2 筛选零新起点 |
| **F8** | 中 | `DMC_PREREG_DRAFT_20261028.md:38`（§3） | 以「rescue 上限 256 CH」作预算来源 | 两态 `limitation_reason=rescue_budget_exhausted`，账本明写「再算**需要另立版本**，不是继续花这一包」；用户重启条件要求「**独立预算**并获批准」⇒ 当前写法与状态事实及账本规则不符（EC 草案的写法是对照样板） | 改为「**新授权额度**（另立版本）」并明示与 600 恢复包／800 框架的关系；同时说明**每态尝试额度已耗尽**需用户重开 |
| **F9** | 中 | EC §2:19、DMC §3:39 | 两轮都对同一账户提交 | EC「1 腿／**不可与 DMC 并行**」与 DMC「**最多 2 腿并行**（避免与 EC 冲突）」冲突；且均未写 running+pending ≤2 的账户规则 | 统一为一条跨草案并发规则（建议：两轮串行；若并行须 ≤2 且写明账户余量核验） |
| **F10** | 中 | EC §2:18-21、DMC §3:36-41 | 按 ≤32 CH（EC）／≤256（DMC）执行 | 两份都**没有墙钟/profile 行**；契约一般生产墙钟 **4 h**（16 CH/腿），12 h 例外只挂 `dol_ec_recovery_v1` ⇒ EC 的 5 探针在 4 h 口径下最多 80 CH ≫ 32 CH；DMC 的 55 CH 与 256 CH 谁约束也未定 | 补：resource profile 名 + 每腿墙钟 + 每腿/累计 core-hours 上限 + 超限如何在飞阻断；并列明是否需新的 per-batch 契约例外 |
| **F11** | 中 | EC §4:34-36 | 选取起点/登记产出 | (a) 产出模板复用**已 accepted 成员的 seed** `p4_02_ring_pucker_twist`：5 个新探针的**独立性与去重身份不可核验**，且与既有成员同名易混淆；(b) 「SHA256 登记于 reopt 目录」指向上一批输入清单，本轮新起点须**新包新登记**；(c) 未点名 **`job.xyz`**（历史误认坑，`DOL_EC_REOPT_PREREG:50`），且识别链须用 `<array>_<index>`（如 `3791416_1`）而非 `JobIDRaw`（10-28 交叉互换缺陷） | 逐探针给唯一名/slot；新包登记起点几何 sha256（`job.xyz`）；识别链写明「`tasks.txt line i` → `array element i` → `sacct JobID "<array>_<i>"`」 |
| **F12** | 中 | EC §7:52-57 | EC 新起点进入注册/提交 | EC 缺 `candidate_gate_contract=validate_candidate_start_v2` 前置（DMC §8 有）；而本项目已知缺口正是「提交器不读任何 gate verdict」 | EC 补与 DMC §8 同款的候选门前置 |
| **F13** | 中 | EC §3:23-30 | 判定 `single_basin_verified` | 未列三条件（`production_evidence` 完整／`search_scope_documented`／进 `latest_members`）⇒ 缺一即静默退化为 `known_basin_reproduction` ⇒ `unresolved`，而草案会把它读成「单盆地=失败」 | 在 §3 逐条列出三条件与 `search_outcome` 合法值集合 |
| **F14** | 低-中 | DMC §8:81 | 声称 5/6→6/6 | 池前置虽满足，但闸门 2 **还要求重跑 A/B 盲回放**（`TWO_GATE_READINESS_20261025.md:8,33`）⇒ 该主张不完整 | 补「须按正式协议重跑 A/B 回放并通过停止预算判据」 |
| **F15** | 低 | EC §2:21、§3:27-30 | 读「停止预算」行 | 与 §3 重复且非数值，不可执行核验 | 把「成本上限」写成数字（累计 CH + 每腿墙钟），§3 只留状态转移 |
| **F16** | 低 | EC §7:55、DMC §8:73 | 引用「gate code audit」 | 范围未定义（该审计对象是闸门模块，不是本预注册）⇒ 准入条件不可判定 | 明确写「闸门模块审计通过」或删去该条，改引候选门契约 |

| **F17**（**补充项，不计入上文 37 项计数**） | 低-中 | DMC §9:80（`plan_overall_complete` 从 `blocked_on_production` → `satisfied`（若 EC 也过））、§10:92；EC §8:61 | 读者据 §9/§8 的 `plan_overall_complete` 取值推断「已结题」 | 用户红线「**48/48 不是完成按钮**／三终态分别报告」被措辞掩盖；且 §9 未提「池补齐后**仍须按正式协议重跑 A/B 回放**」（`TWO_GATE_READINESS_20261025.md:8,33`）⇒ 易被读成「四态 accepted 即结题」。**与并发会话 `dmc_prereg_fast_audit_recheck/REPORT.md`（DMC 20 项 13 成立 7 不符，重灾区即 §9 结题口径）同向**；我独立复核后判定：其**算术部分成立**（48/48 ⇒ `plan_complete` ⇒ `satisfied`，`build_plan_compliance.py:998`），缺陷在**缺限定 + 缺回放重跑**，而非取值错（对比 EC §8 的 `partial` 才是取值错，见 F3） | §9 补一句「本行只表示**主态闭环的机械条件满足，不等于研究结题**；三终态分别报告；闸门 2 须重跑回放」 |

## 8. 建议的最小修正集（供 Lead 审议）

1. **EC §3 与 `DOL_EC_STAGE_REPORT_20261027.md:143` 同步改写**（F1）——这是唯一会**改变科学结论方向**的一条，应优先。
2. EC §8 两处数字/取值更正（F2/F3），DMC §8 补回放前置（F14）。
3. 两份各补：墙钟/profile + 命名族序号 + 每态额度 + 候选门前置（F4/F10/F12），EC 补三条件（F13）。
4. DMC 预算来源改写为「新授权额度」（F8）；两草案并发规则统一（F9）。
5. 术语与事实更正：`40 分子 core set`（F5）、DMC 阈值归属（F6）、DMC 轮次口径（F7）。
6. EC §4 识别链与起点登记精度（F11）。

## 9. 证据出处

- 草案：§0 表中两份 sha256（行号按该快照）。
- 判据源：`INDEPENDENT_START_CRITERIA_20261027.md:53-73`（route 判据链 + 三条件）；`DOL_EC_PRODUCTION_COVERAGE_PLAN_20261027.md:13,18-19,220-222`（route→verdict→accepted 表）；`build_coverage_reviews.py:150-160,175-225`（`coverage_route` 与 `single_basin_verified` 的最终 return）。
- 闸门/合规：`scripts/wp_production/build_plan_compliance.py:995-998`（`plan_overall_complete` 取值）、`:57`（`STATUSES`）、`:773`；`outputs/physics_completion/compliance/plan_compliance.csv:39`；`strict_readiness_wiring.py:49,67-68,457,591`。
- 池与缺口：`LIMITATION_REPORT_20261027.md:12,25,157,160`；`TWO_GATE_READINESS_20261025.md:7-8,16-19,25-34`。
- 成本与状态：`work/hpc_dol_ec_recovery_v1_reopt_20261027/attempts/settlement_per_leg_20261028.json:3,24-26,38-44`；`attempts_ledger.json`（`ec_outcome`）；`outputs/physics_completion/recovery/recovery_budget_accounting.md:11,31,37,41,43`；`cost_scenario_index.json`（`free_cation_def2TZVPD` p90=18.406222）；`DOL_EC_STAGE_REPORT_20261027.md:10-11,29,97-107,119-121,143-144`.
- 契约/墙钟：`recovery_contract.json:7`（4 h 一般墙钟；12 h 仅 `dol_ec_recovery_v1`）。
- 事实/术语：`DMC_DECISION_BRIEF_20261027.md:5,12,14,21,29`；`deliverables/part1/00_项目总览/统一数据文档.md:8,33`（core set 18／broad pool 40）；`DOL_EC_REOPT_PREREG_20261027.md:50,56`（`job.xyz` 误认坑 + 命名族条款）。
- 既有审计（未覆盖，仅比对）：§0 表中三份 sha256。

---

**37 项检查 18 成立 17 不符**（另 2 项部分成立；不符项去重后 = **16 条缺陷**，其中 **F1/F2 为高**）。
本文件**未修改** `prereg_audit_20261028/REPORT.md`（并行会话产物，sha256 `052604958fae…`）；建议 Lead 按 §8 合并两份结论后再定稿。