# DMC 预注册草案快速审核 —— 独立复核报告（t9，STAGE1-2，2026-10-28）

## 0. 交付路径冲突声明（**请 Lead 先读本节**）

- 任务 t9 指定的输出路径 `docs/handoffs/four_state_recovery_20261023/dmc_prereg_fast_audit/REPORT.md` 在我开始核验时**已被另一会话占用**：该文件 sha256 `A1FA211ECDF9E06631717EBC37C1B43FE038291EBD37FBC0A888B51C040C0FE7`，5,196 B，mtime 2026-10-29 0:30:06，结论为「**19 项检查，19 成立，0 项不符**」。
- 依项目准则「**单写入者**——生产代码/测试/产物/文档同一时刻只一个会话写」「只读方不争写入面」，**我未覆盖该文件**（它也非我所写）。本报告是我的**独立复核**，落在**我自建的新目录**，未与任何他人写入面冲突。
- 本次唯一写入产物 = 本文件；未创建脚本/测试，未 git，未提交/预算/启动任何计算。
- **两条结论差异极大**（我 13/20 vs 被占文件 19/19）。差异对账见 §5，其中**被占文件至少有一处事实错误**（它称 256 CH「未见于任何权威预算账本」，实为 `recovery_contract.json:28` 的 rescue `core_hours_cap`）。
- **路径说明**：本项目仓库根 = `电解液溶剂HB-Code/`，本报告及所引相对路径均相对该根。

## 1. 所读输入的 sha256（结论绑定）

| 文件（相对 `电解液溶剂HB-Code/`） | sha256 |
|---|---|
| `docs/handoffs/four_state_recovery_20261023/DMC_PREREG_DRAFT_20261028.md`（**审核对象**，92 行 / 4,066 B） | `6FB2F48E25F4F0EFA2A078810CC161CA8EBB8738D729B275647555513F43FBAE` |
| `.../recovery_contract.json` | `C9D45851A9F6502AB71FCEC7360BCA935879C53183EEFEF4BD865542C5B38D6D` |
| `.../DMC_DECISION_BRIEF_20261027.md` | `4E7510270C6B0AAB7AB0F43BF06B58B1BAAE5C73B81C357B831E5980B2AD6176` |
| `.../DMC_THRESHOLD_DIAGNOSIS_20261025.md` | `4943A9F27A10218116A3F4326CCD63DA67DC6D26AE920C17CC2E723B5FDD263D` |
| `.../EC_PREREG_DRAFT_20261028.md`（姊妹草案） | `306CA7729BE4CDB519A488AB706274CDD7BC35AC791099A5A3EC70AFCEA1BDAF` |
| `.../FOUR_STATE_STARTING_LEDGER_20261025.md` | `FB1E27EA3CC2E6CD2AC2EFE7A59C81DD6AB47F72BD9B1CB064AB6FF5DE3AE38A` |
| `.../FOUR_STATE_ENDGAME_20261026.md` | `B2FF2C94BCE8618943E9AF88558C8A394696B11C0AC1C96DB1DA114A110FB194` |
| `.../DECISIONS_PENDING_20261027.md`（137 行） | `A282698EBE381364BDC48ADAA86D031A6462F90E679C38BCBF5744C8447857F0` |
| `.../ec_prereg_fast_audit/REPORT.md`（并发会话产物） | `38ED79620A846AC089CD67BDBE7EBB9CF5ED3C4EFF3369E3BD0CC1B2F6E76F65` |
| `.../dmc_prereg_fast_audit/REPORT.md`（**被占用的既有产物**，仅读未改） | `A1FA211ECDF9E06631717EBC37C1B43FE038291EBD37FBC0A888B51C040C0FE7` |
| `.../DOL_EC_PRODUCTION_COVERAGE_PLAN_20261027.md` | `3B9F9653CD3795E6655AE467BA6903D67EA4C82C375017BE537BA08C3EBA34E8` |
| `outputs/physics_completion/compliance/plan_compliance.csv` | `621E208D05EF69B8ACC3CC14BE6B654095E298100D121D939180FC0ACA0B8526` |
| `outputs/physics_completion/ensembles/production_ensemble_labels.csv` | `C454FB7BF3FCB4B29ED7B4EC3C4BABBADDE791AF51B7F3E1AD8FD8751823D594` |
| `outputs/physics_completion/active_learning/blind_replay/AB_axis_endpoint.csv` | `37B0256C251159EB9EAC4D8DC22B500878AE8DCAA36E76C549968634767E80E7` |
| `scripts/wp_production/build_plan_compliance.py` | `AB68416601CD2E15234441CEA1CAB00302557A617313C43422E510C4CEF08A50` |

---

## 2. STAGE1：完整性检查（草案 10 节逐节）

| # | 节 | 应有要素 | 实测 | 判定 |
|---|---|---|---|---|
| 1 | §1 目标态与现状 | 目标态/现状/历史/诊断 | 目标态 `DMC\|M_plus`+`DMC\|LiM_2plus`、两轮历史、诊断结论齐备 | ✓ |
| 2 | §2 机制选项 | 选项集 + 不预决声明 | A/B/C + §2:32「用户裁决前…不预决」 | ✓ |
| 3 | §3 预算与资源 | 可用预算/并发/核算口径/停止预算 | 4 行表齐备（§3:36-41） | ✓ |
| 4 | §4 停止条件 | 各出口→状态 | 4 类出口（§4:45-48） | ✓ |
| 5 | §5 标识链与输入哈希 | 起点来源/**几何哈希**/方法模板/禁止项 | 起点路径与 `candidate.json`+`inputs.sha256` ✓；**方法模板只写「冻结方法不变」未点名任何路径** | **✗** |
| 6 | §6 双重口径预防 | 成本口径/失败保留/标签口径 | 4 条齐备（§6:59-62） | ✓ |
| 7 | §7 版本化与可逆性 | v0→v1/拒绝归档/失败不沿用 | 3 条齐备（§7:66-68） | ✓ |
| 8 | §8 提交与授权条件 | 必须项 + 禁止项 | 4「必须」+1「禁止」（§8:72-76） | ✓ |
| 9 | §9 下游影响 | 闸门/系综/目标池 | 4 项影响（§9:80-83） | ✓ |
| 10 | §10 不变的红线 | 红线清单 | **6 条**（§10:87-92） | ✓ |

**STAGE1：10 项，9 成立，1 不符。**

### F-1 §5 方法模板未点名（完整性缺口）

- **主张**：§5 要求方法可核对，却未给出任何方法源文件路径。
- **原始命令/file:line**：`DMC_PREREG_DRAFT_20261028.md:54`「方法模板：冻结方法不变，预优化选项须在 prereg 中声明」；对照 `recovery_contract.json:20` `"method_source": "config/production_method_freeze_v1.json"`，姊妹草案 `EC_PREREG_DRAFT_20261028.md:35` 给出 `config/physics_completion_v1.yaml` + `orca_input_template.inp`。
- **实测值**：草案全文无任何 `config/` 路径；§5 该行仅为自指表述。
- **判定**：**不完整**。冻结方法（`wB97X-D4/def2-TZVPD + SMD`，`recovery_contract.json:21`）无法据草案机械核对。建议补 `method_source` 与 `.inp` 模板名。

---

## 3. STAGE2：一致性检查（10 项）

### F-2 §1 量名张冠李戴：1.6× 属 MAX step，不属 TolE —— 不符

- **主张**：§1「第一轮：**TolE** 超差 **1.6×–2.2×**」。
- **file:line**：`DMC_PREREG_DRAFT_20261028.md:11`。
- **实测值**：`DMC_THRESHOLD_DIAGNOSIS_20261025.md:31`「唯一不过的 **MAX step＝3.24e-4**（阈 2e-4，**差 1.6 倍**）」；`:54`「**只差 TolE 一项**，ΔE 4.344e-07 > 2e-07，**差 2.2 倍**」；`DMC_DECISION_BRIEF_20261027.md:12` 亦并列写「**MAXstep 差 1.6×** 或 **TolE 差 2.2×**」。
- **判定**：**不符**。数值对、量名错。应改为「MAX step 超 1.6× 或 TolE 超 2.2×」。

### F-3 §3 预算：数字与 contract 一致，但授权链缺失 —— 数字成立 / 完整性不符

- **主张**：§3「本轮可用预算 **≤256 CH**（rescue 上限；须用户明确授权）」。
- **file:line**：`DMC_PREREG_DRAFT_20261028.md:38` vs `recovery_contract.json:28` `"rescue": {..."core_hours_cap": 256}`。
- **实测值（数字）**：**256 与 contract 的 rescue `core_hours_cap` 逐位一致** ⇒ 成立。
- **实测值（授权链）**：① `recovery_contract.json:24` `budget.status = "proposed_new_round_ceiling_not_submission_permission"`（**额度上限 ≠ 提交许可**），草案未引此语义；② `recovery_contract.json:28` rescue `max_attempts=4`、`max_per_state=1`，而 `DMC_DECISION_BRIEF_20261027.md:21` 明确「**「每态 ≤2 起点 + ≤1 救援」的尝试额度已用尽**」⇒ DMC 两态的**尝试额度已耗尽**，256 是未花掉的**池**而非"可动用的通道"；③ 另有两处口径不同：`FOUR_STATE_ENDGAME_20261026.md:52`「有因救援 | 256 | **未动**」、`DECISIONS_PENDING_20261027.md:125`「有因救援 | 256 | **未动**」。
- **判定**：**数字成立，授权链不完整**。草案须写明「新轮次 = 需新的预算授权 + 尝试额度重建」，并澄清「池未动」与「尝试额度已尽」并存的两口径。**需 Lead/用户裁决**。

### F-4 §3 并发上限与姊妹草案**直接互斥** —— 不符

- **主张**：§3「并发上限 | 4 核/腿，**最多 2 腿并行**（避免与 EC 冲突）」。
- **file:line**：`DMC_PREREG_DRAFT_20261028.md:39` vs `EC_PREREG_DRAFT_20261028.md:19`「并发上限 | **1 腿（不可与 DMC 并行）**」。
- **实测值**：两份**同日（2026-10-28）**草案对同一资源给出互斥约束——DMC 允许自身并行 2 腿且对 EC 只作"避免"的**软**表述；EC 硬性规定 1 腿且**明确不可与 DMC 并行**。二者同时生效则同一时刻可出现在飞 3 腿（>`recovery_contract.json:39` `dol_ec_recovery_v1` 的 `max_legs=2`；DMC 新轮次本身无对应 batch 条目）。
- **判定**：**不符**。须统一为可执行的互斥规则（如「在飞总量 2 腿、EC 与 DMC 不并行」），把"避免冲突"由软措辞改为硬约束。

### F-5 §2 选项 A 的示例起点是**已用过的旧起点**（命名歧义 → 与"不可沿用旧池"冲突） —— 不符

- **主张**：§2 选项 A「起点：Li 配位探针（登记 torsion 合法位移，**如 `tors_8_0_1_2`**）」。
- **file:line**：`DMC_PREREG_DRAFT_20261028.md:18` vs `FOUR_STATE_STARTING_LEDGER_20261025.md:20`「`DMC|M_plus` … `tors_8_0_1_2` | 1 | 2 / 1」（同行记录 `limited` / `rescue_budget_exhausted` / `unresolved_qc`）。
- **实测值**：`tors_8_0_1_2` 正是 **DMC\|M_plus 第一轮已登记且已跑过的起点**（令牌逐字相同）。
- **判定**：**不符（命名歧义至少需消解）**。草案 §1 自称「**不可沿用旧池**」、§7 要求「v1 失败后 v2 必须改变机制…不允许沿用 v1 配置」。二选一：① 若为新探针 → 须**另立序号族**（对齐 `DMC_DECISION_BRIEF_20261027.md:29` 的纪律「序号高于全部历史序号」）；② 若确为复用 → 须删去"不可沿用旧池"或写明复用理由与可比性边界。**按现文，读者只能理解为复用旧起点，即与 §1 自相矛盾。**

### F-6 §1 诊断未回应已闭环反证、也未对齐权威待裁路径 —— 不符（缺一致性说明）

- **主张**：§1「本轮诊断结论：需**新机制**（改变起点策略、预优化路径或配位几何），不可沿用旧池」。
- **file:line**：`DMC_PREREG_DRAFT_20261028.md:13`。
- **实测值（对草案不利的权威表述）**：`DMC_DECISION_BRIEF_20261027.md:14`「**DMC 不缺新起点，缺的是能过五阈值的优化设定，而那是冻结项**」；`:16` 建议决断为「**现有条件下停止（保留 `limited`）**」；`:13`「从平台重启仍得平台（已被 4 次证伪）」；`:29` 唯一有依据的恢复路径为 B1（版本化优化设定评估，全 cohort 60 腿 × p90 18.41 ≈ **1105 CH，远超 800**）。
- **实测值（对草案有利、须公平记录）**：`DECISIONS_PENDING_20261027.md:62` 明确 DMC 两态复核为 `unresolved_qc`（与 DOL/EC 的 `search_exhausted` 处境不同），「**理论上仍可由新的、能过 QC 的起点转成 `resolved` ⇒ `accepted`**」；`:57-64`（H1）把"改优化设定救 DMC"列为**成本最高**的待裁选项，硬约束是**全 cohort 可比性评估**。
- **判定**：**不符（缺一致性说明），但并非方向违规**。草案取"新起点/新机制"方向**有** `DECISIONS_PENDING:62` 的依据；缺陷在于它**未引用**该依据、**未回应** `:14`/`:13` 的两条闭环反证（新起点为何能突破已证伪的平台）、**也未说明** A/B/C 与 H1/B1 及"全 cohort 可比性"的关系。**需 Lead/用户裁决**：是按 :62 补论证后推进，还是改为对 H1/B1 的呈报。

### F-7 §9 `plan_overall_complete → satisfied` 无证据支持 —— 不符（**本单最重要**）

- **主张**：§9「通过 2 态：`plan_overall_complete` 从 `blocked_on_production` → **`satisfied`**（若 EC 也过）」。
- **file:line**：`DMC_PREREG_DRAFT_20261028.md:80`。
- **原始命令**：读 `plan_compliance.csv` 的 `plan_overall_complete`/`wp2_sampling_extension` 行 + 核 `build_plan_compliance.py` 的合取式。
- **实测值**：`build_plan_compliance.py:967-978` 的 `plan_complete` 是 **10 项合取**，除系综 48/48 外**还要求** `samp_extension_ok`（:974）与 `strict_evidence_ok`（:977）。盘上：
  - `plan_compliance.csv:40`（`plan_overall_complete`）status=`blocked_on_production`，measured=`main_states=48/48; main_four_state_complete=12/12; free_labels=12/12; li_labels=12/12; **production_ensembles=45/48**; **sampling_complete=False**; flip_rungs=10/10; pilot_subset=20/20`；
  - `plan_compliance.csv:14`（`wp2_sampling_extension`）status=`partial`，measured=`acceptance_ok=9/9; **escalation_pending=24/24**; executed=C01,C02,C03,C04,C05,C08,C09,C13,C14,C15,C16,C17; designated=C02,C03,C08,C17`（**executed ≠ designated**）；note 自述「两件事都还没发生…实际采样集 DMC/EMC/GBL/SL 不等于方案 3.3 指定的 EMC/DEC/DME/TMP」。
- **判定**：**不符**。上述采样阻塞（24/24 未决 + executed≠designated + 采样集不符）**与 DMC/EC 恢复无因果关系**，48/48 不会令 `samp_extension_ok` 转真 ⇒ `plan_complete` **仍为 False**。应改为「production_ensembles 45→47/48；`plan_overall_complete` **仍 `blocked_on_production`**（采样侧独立阻塞）」。

### F-8 §9 系综 45/48 → 47/48（若 EC 过则 48/48）—— 成立

- **主张**：`DMC_PREREG_DRAFT_20261028.md:82`。
- **实测值**：`production_ensemble_labels.csv` 共 **48 行**，`acceptance_status` = **accepted 45 / limited 3**；3 个 limited 恰为 `C01|M_plus`(DMC)、`C01|LiM_2plus`(DMC)、`C04|LiM_2plus`(EC)。
- **判定**：**成立**。45 + DMC 两态 = 47；再 + EC = 48 ⇒ 与草案及其"（若 EC 过）"限定一致；与姊妹草案 `EC_PREREG_DRAFT_20261028.md:63`「45/48 → 46/48」不冲突。

### F-9 §9 `strict_readiness_evidence` 5/6 → 6/6（**若 EC 也过**）—— 成立，且该限定必需

- **主张**：`DMC_PREREG_DRAFT_20261028.md:81`。
- **实测值**：`plan_compliance.csv:39` status=`not_satisfied`，measured=`checks_passed=5/6; failed=wp5_full_target_pool_evaluated`。池实测（`AB_axis_endpoint.csv`，32 行）：**A 轴 n_pool=11**（16 行）、**B 轴 n_pool=10**（16 行），**无一为 12**。
- **判定**：**成立，且限定句不可省**。A 轴缺 1 个分子（DMC\|M_plus）、B 轴缺 2 个（DMC\|LiM_2plus + EC\|LiM_2plus）⇒ 只有 **DMC 两态 + EC 同时通过**才令全池 12/12。**副产物**：姊妹草案 `EC_PREREG_DRAFT_20261028.md:62` 把 `5/6 → 6/6` 写成 EC 单独通过的无条件后果，**与实测不符**（EC 单独通过后 A 轴仍 11/12）——DMC 草案在此处**比姊妹草案更准确**。

### F-10 红线 / 闸门契约 / 核算口径 —— 成立

- **主张**：§10 六条红线、§8 `candidate_gate_contract=validate_candidate_start_v2`、§3 `per_element_core_hours()`、§3「p90 18.41 × 2 × 1.5 ≈ 55 CH」。
- **实测值**：① §10 与 `recovery_contract.json:21-22`、姊妹草案 §9 一致，未见违反（第 6 条「不无限重复审计或自动追加计算」与 §7/§8 的禁止自动追加自洽）；② `validate_candidate_start_v2` 见 `P9_READINESS_20261024.md:51`、`agent_a_candidate_review/REPORT.md:23`，并与 `DECISIONS_PENDING_20261027.md:62`「能过 QC 的起点」互洽；③ `per_element_core_hours()` 见 `DOL_EC_STAGE_REPORT_20261027.md:120-121`（显式拒绝 `.batch/_b`、`.extern/_e` 子行）；④ p90 **18.41** 见 `DOL_EC_PRODUCTION_COVERAGE_PLAN_20261027.md:150`，算术 18.41×2×1.5 = **55.23 ≈ 55** ✓。
- **判定**：**成立**。

---

## 4. 未覆盖 / 需 Lead 决定

- **未覆盖（科学口径，非本单可裁）**：A/B/C 中哪一条能合法突破已被证伪的平台、预优化路径是否属"冻结项变更"——**需 Lead/用户**（§3 F-6 已给出双方证据）。
- **未覆盖**：§8「独立预算确认 ≤256 CH」与预算系统的对接实现（姊妹审核同问题）。
- **未覆盖**：`DECISIONS_PENDING_20261027.md:64` 的 H1 成本估算（≈9.9 CH/腿 × 全 cohort）未逐项复算。
- **未复算**：`plan_compliance.csv`/`AB_axis_endpoint.csv` **生成器写路径**未重跑（只做只读消费 + 合取式源码核对）；结论绑定两文件 sha256。
- **需 Lead 决定**：① 本报告的落位（见 §0，我未覆盖被占文件）；② DMC 是否应改为对齐 `DMC_DECISION_BRIEF_20261027.md` 的「停止 / 或走 B1」呈报口径；③ F-3 的两处预算口径（"尝试额度已尽" vs "256 未动"）。

---

## 5. 与「被占用的既有 DMC 快速审核报告」对账（sha256 `A1FA211E…`）

| 项 | 既有报告 | 本次实测 | 结论 |
|---|---|---|---|
| 总判定 | 19 项检查、19 成立、**0 不符** | 20 项、13 成立、**7 不符** | **重大分歧** |
| §5 完整性 | 记 ✓「方法模板冻结」 | 草案全文**无**方法模板路径 | 既有报告**漏检**（F-1） |
| §10 红线条数 | 称「**五条**红线」（列出 5 条） | 草案 §10 实为 **六条**（第 6 条「不无限重复审计或自动追加计算」） | 既有报告**漏计 1 条** |
| 256 CH 出处 | 称「该数字**未见于任何权威预算账本**…属 draft 自设 rescue 上限」 | **`recovery_contract.json:28` `rescue.core_hours_cap = 256`** | 既有报告**事实错误** |
| F-2 量名错 | 未提 | `:11` TolE 误冠 1.6× | 既有报告**漏检** |
| F-4 并发互斥 | 未提 | 与 EC 草案 `:19` 直接互斥 | 既有报告**漏检** |
| F-5 旧起点复用 | 未提 | `tors_8_0_1_2` 为已用起点 | 既有报告**漏检** |
| F-6 诊断对证 | 未提 | 未回应 `BRIEF:13/14` 反证（但 `DECISIONS_PENDING:62` 支持其方向） | 既有报告**漏检** |
| F-7 结题口径 | 未提（其 STAGE1 第 9 项只罗列 47/48、48/48、5/6→6/6） | `plan_complete` 含 `samp_extension_ok`，48/48 **不足以** satisfied | 既有报告**漏检（最重要）** |
| 证据引用 | STAGE4 引 `DECISIONS_PENDING:50/:62` | 我复核：`:50` 确为用户裁定（H3 为本轮停止条件）、`:62` 确述 DMC 复核为 `unresolved_qc` | 既有报告**此二处引用属实**（应予肯定） |
| 姊妹草案缺陷 | 未提 | EC 草案 `:61`/`:62` 与实测不符 | 既有报告**漏检** |

**结论**：既有报告并非错误到不可用（其 STAGE4 引用属实），但**① 存在一处硬事实错误（256 的出处）；② 漏检 7 项、其中 F-7 直接影响"是否值得批新预算/能否结题"的判断**。建议 Lead：以本报告为准并入，或指派一次交叉复核后**只保留一份**（避免"两份权威"）。

## 6. 并发与去重提示

1. 姊妹产物 `ec_prereg_fast_audit/REPORT.md`（sha256 `38ED796…`）在我开始前**不存在**、其后出现，且与我同批（其结论 18/18 全过，同样未发现其草案的 `:61`/`:62` 缺陷）。
2. 被占用的 `dmc_prereg_fast_audit/REPORT.md` 也是并发产物。**三者相互独立写各自目录，无写入面冲突**，但 **DMC 对象上出现了两份结论相反的权威** ⇒ 请 Lead 裁决保留哪一份。
3. 若 t7（`prereg_audit_20261028/`）审核面亦含 DMC，将形成第三份 ⇒ 建议一并去重。

## 7. 总结

**20 项检查，13 成立，7 不符。**

- STAGE1 完整性：10 项 **9 成立 / 1 不符**（F-1 §5 方法模板未点名）。
- STAGE2 一致性：10 项 **4 成立 / 6 不符**。
  - 成立：F-3 **数字部分**（256 与 contract 一致）、F-8（系综 45→47→48）、F-9（5/6→6/6 带 EC 限定，**并反证 EC 草案此处才错**）、F-10（红线/契约/口径）。
  - 不符：**F-2**（TolE 量名错）、**F-3 授权链缺**、**F-4**（并发与 EC 草案互斥）、**F-5**（旧起点复用与"不沿用旧池"矛盾）、**F-6**（诊断未回应闭环反证/未对齐 H1）、**F-7**（`plan_overall_complete → satisfied` 无依据）。
- **最高优先级**：**F-7**（结题口径被高估）与 **F-6**（机制假设与已闭环证据的关系未交代）—— 二者直接决定"是否值得批新预算"。次优先：**F-4**（同日两草案资源互斥，会实际影响并发排程）。
- **对被占文件的处置**：未覆盖、未修改；其 sha256 已登记于 §1，供 Lead 裁量。