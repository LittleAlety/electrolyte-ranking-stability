# 汇总 · strict_rebuild 只读接收轮（A/B 两线）终稿

> 状态：**终稿** — A1/A2/A3/A4/A5、B1/B2/B3/B4 全部交付并经 Lead 对原始材料抽验。
> 红线遵守：零新增计算、零作业提交、零共享生产写入、未改阈值/判据/正式标签、未手填 `resolved`、未做 δ 选择、未生成 comparability_criterion、未迁移未批准跨协议成员；本文件为只读核验产出，**不构成准入结论或用户签认**。

## 0. 元信息

| 项 | 值 |
|---|---|
| 仓库根 | `E:\Claude Code\电解液溶剂-HB\电解液溶剂HB-Code` |
| 仓库 HEAD | `80933e54f8a605d9dd6d033c0f2861e33b591c13`（`work/` gitignored） |
| 产出目录 | `docs/handoffs/lead_reception_strict_rebuild_20261103/evidence/`（本轮唯一写入面） |
| 上游交接 | `docs/handoffs/strict_rebuild_20261103/`（未跟踪 242 文件） |
| 协调登记 | `.dsh-coordination/SESSION_CLAIMS.md` 已追加本轮 claim（260,475 → 262,430 B） |

---

## 1. 任务 A · 科学证据分析（逐项结论）

### A1 · 五态覆盖（`docs/handoffs/lead_reception_strict_rebuild_20261103/evidence/A1_five_state_coverage.md`，sha256 `c42b4d6c3a3a6100863864443fc3cbe58366ff8797c7e3e5057608c6b4e30134`，196 行）

**总判定：五态全部为「证据已有但未绑定」，无一态判为「覆盖证据不足」。**

| 态 | 搜索范围（原始记录） | 真实起点 | 作业与终态 | 身份 | 去重 | 判定 |
|---|---|---|---|---|---|---|
| DEC\|LiM_2plus (c02) | li_motif round1 10 起点（screen:42-51, c02 kept:44）+ motif_plan:7 + round2 计划:5/执行:2-28（3 父×9 布局, 1 kept）+ audit:9 | `work/limotif/C03_LiM_2plus/…c02/xtbopt.xyz`（`c17e9705…`，父 `493596b3…`） | 3723647_9 computed / imag=0 / 69.86 | c02 verified（frontier:7）；coverage_8 = `FROZEN_FRONTIER_CHAIN_VERIFIED` | primary→c02（0.003 Å / 0.6°） | 证据已有但未绑定 |
| DEC\|M_plus (15) | conformer_set:11-14（4 结构, 3 选中）+ audit:7 + sampling_index round1+round2 起点池 | `work/sampling/DEC/M_plus/c15/xtbopt.xyz`（`f2897bb8…`） | attempt0 3720638_1 superseded → attempt3 3721460_1 computed / imag=0 / 52.12 | 15 verified（:10） | 三成员全 unique（n_unique=3） | 证据已有但未绑定 |
| GBL\|LiM_plus (c03) | li_motif round1 4 起点（screen:137-140, c03 kept:140）+ motif_plan:16 + sampling_index「4 starts screened」；**round-2 与 audit 行限定检索未找到** | `work/limotif/C13_LiM_plus/…c03/xtbopt.xyz`（`adb7e3a4…`，父 `c916bc4d…`） | 3723647_3 computed / imag=0 / 43.97 | c03 verified（:55） | primary→c03（0.012 Å / 2.7°），n_members=1 pool_limited=true | 证据已有但未绑定（**范围证据五态最弱**） |
| PC\|M_plus (46) | conformer_set:18（唯一结构 r2_c46）+ pool_limited_states；**无 audit 行（PC 非 designated）** | `work/sampling/PC/M_plus/r2_c46/xtbopt.xyz`（`ff038bb4…`） | 3720638_4 computed / imag=0 / 102.57 | 46 verified（:62） | primary 与 46 均 unique | 证据已有但未绑定 |
| TMP\|M (27) | conformer_set:41-42（2 结构均选中）+ audit:14（`sampling_limited`，结论基于过期账本哈希不可沿用）+ pool_limited_states | `work/sampling/TMP/M/r2_c27/xtbopt.xyz`（`d97d3c27…`） | 3718293_15 computed / imag=0 / 46.40；48 attempt0 superseded（8.598e-07>2e-07）、attempt1 缺 energy_change | 27 verified（:80）；48 的 frontier 行限定未找到 | 48→27（0.007 Å / 1.1°），primary unique | 证据已有但未绑定 |

**绑定缺口的共同证据**（Lead 已独立复核全 PASS）：labels 五态 `coverage_status=not_reviewed` + `coverage_review_id=''`（5/5）；`coverage_reviews.csv` 14 条 review 精确匹配五态 **0 命中**；`coverage_8` 五态 `route=pending` / `coverage_gate=HELD` / `registered_starts=[]`（5/5）；`strict_recovery_v1_manifest` 13 行 0 命中。**每态一句话结论**：缺的是把范围与合格代表绑定进 coverage 登记，而非新证据。

**未确定事项**：① frontier `sha256_job_log` 与 structures/source_index 对同一成员不等（如 TMP|M|27：`bdd901b3…` vs `7dec22f1…`），关系说明未找到，未作调和；② 五态 coverage review 记录限定检索未找到（不写成不存在）；③ audit index 记录 `structures=3f2c692d…` ≠ 当前 `3a795ce8…`（已证过期，其状态结论不可沿用）；④ GBL 无 round-2/无 audit、PC 无 audit、Li 态不在 sampling_conformer_set（均按「限定范围内未找到」）；⑤ DEC|M_plus|15 attempt3 起点 `34352b0d…` ≠ 登记 `f2897bb8…`；DEC|M_plus|23 与 c03_c03 未入正式候选登记；⑥ verification README:21 明示不能证明任何一态已穷尽现有文件、未确认最小实验清单或预算。

**新物理证据**：无（五态均 `NOT_AUTHORIZED` / `NONE_JUSTIFIED_YET`）。

**抽验**：文件 sha256/196 行 ✓；上述绑定缺口 4 项全 PASS；文末 27 文件哈希清单抽验 26 OK / 0 mismatch（1 个为路径前缀提取问题、同文件随即命中）。

### A2 · AN M⁺（`evidence/A2_AN_Mplus_identity.md`，修正版 sha256 `b962efaa62ad0e9fac2ccebc69728fce6d3274ec8d5b44cec3460acec942aa4c`）

**两结论分离给出：**

- **(a) 前沿身份材料：未闭合。** 唯一严格合格代表 `AN|M_plus|tors_3_0_1_2` 的独立前沿身份链在本地限定来源内未找到：frontier 三表（`frontier_identity_evidence/localization/legs.csv`，各 81 行含表头=数据 80 行）检索 `tors_3_0_1_2` **0 命中**（`AN|M_plus|primary` 行 5）；`work/hpc_frontier_localization_v1/tasks` 81 项、AN 5 项无 tors 目录（`frontier_task_exists=false`）；`coverage_8[0]` = `IDENTITY_EVIDENCE_NOT_IN_FRONTIER_REGISTER` / `geometry_hash_bound=false` / `raw_four_files_rehashed=false` / `coverage_gate=HELD` / `route=single_basin_verified` / `production_evidence_files_present_and_hashed=true`。**身份门保持 HELD**——这是「本地限定来源未找到 + 远端 `INACCESSIBLE_NOT_VERIFIED`」，**不是身份失败**，也不归因数值误差。
- **(b) 单盆地证据：未闭合。** 同一组证据在两套输入语义下路由相反（历史 dedup → `single_basin_verified/resolved`；严格池 → `single_basin_scope_review/unresolved`，见 B4 复跑 `full_generator_8.json[0]`）；独立复核 `coverage_recheck.json:3-13` = `UNRESOLVED_RECHECK_REQUIRED`，`zero_compute_action = reconstruct search scope, qualified starts and dedup clusters; do not inherit old resolved`。故「单盆地已成立」目前不成立；**停点是范围与证据审查状态，非科学失败**。

**未确定事项**：远端来源未核（`INACCESSIBLE_NOT_VERIFIED`）；`coverage_8` 与 `full_generator_8` 同态异路由的输入语义差异未裁定；身份链「未找到」的范围限定已写明。
**新物理证据**：无。

**抽验**：frontier 三表 0 命中/行 5 ✓、tasks 81/AN5/无tors ✓、coverage_8 五键 ✓、recheck ✓、dedup primary kept/tors `duplicate_of=primary`（0.0015 Å）✓、member_statuses 值 ✓；两处引用瑕疵（计数单位、列名）已回传修正并复验（行 36/37/41 PASS）。

### A3 · AN LiM²⁺ 固定几何频率（`evidence/A3_AN_LiM2plus_frequency.md`，sha256 `ddc1570386700b6c149334f19eeb68dadf9aeb90f0a4063940c6c729b89933d6`）

1. **阶段来源已查清**：「新 strictOpt」与「旧 NumFreq」是同一历史作业的两个阶段——远端 `hpc_verytight_rescue_20261015/tasks/AN/LiM_2plus/attempts/3700781_2_3706757/job.log`（数组父 3700781、元素 2、作业号 3706757），单输入 `Opt NumFreq`：阶段 1 Opt 五项实测全过（Energy change −1.824e-07 ≤ 2e-07 等 5/5 YES）→ 阶段 2 NumFreq 在 Opt 末几何给出 **−115.27 cm⁻¹ 虚频**（line 7256，找回日志 `raw/74240733….log`）。
2. **几何核验**：strict 与 primary 几何 maxdelta **0.0031721326 Å**；找回的 3706757 final 几何 = strict 几何（4.98e-07）。
3. **2×2 证据矩阵**（如实并列，**不做归因**）：

| | NumFreq | AnFreq |
|---|---|---|
| primary 几何 | −127.20（虚） | **+37.07（实，两次独立运行逐字节复现）** |
| strict 几何 | **−115.27（虚）** | **缺失** ← `FIRST_EVIDENCE_PROPOSAL.json` 要补的唯一格 |

4. **−115.27 振型（第 6 模，唯一虚模）**：质量加权 3×甲基 H 合计 **87.5%**（H5 34.3 / H4 31.7 / H3 21.5）、Li 7.5%、N 3.3%；实际位移 甲基 H 43.0% / Li 25.3% / N 22.1% —— **甲基主导扭/摆型 + Li–N 骨架参与**。AnFreq +37.07 实际位移以 N 40.5% + Li 35.1% 为主（Li···N 配位型），**两者不是同一个运动**。
5. **−127.20 vs −115.27 Δ 11.93 cm⁻¹**，两 NumFreq 间模式 7–20 差 ≤0.5%（modes 9–20 ≤0.7% 口径见报告 §4.2）。
6. **固定几何 AnFreq 检验什么**：补「strict 几何上解析 Hessian 是否给出实频」这一格，使 −115.27 成因（数值微分伪影 / 几何真实失稳 / 解析法局限）三选一可收窄；**当前归因未确定，按红线不预判**。
7. **提案**：五项 PASS、0.5–4 core-h 估算、预留 96 core-h **未批**（`PROPOSED_NOT_AUTHORIZED_NOT_SUBMITTED`）。

**未确定事项**：−115.27 成因未定（等第四格）；`raw/AN_LiM2plus_job.hess` 与 3706757 的绑定为同源合理推断、无机器级绑定证明。
**新物理证据**：**唯一实验/计算提案** = 固定几何 AnFreq（**待批，未提交**）。

**抽验**：`raw/74240733….log:7256` −115.27 虚频行、`raw/AN_LiM2plus_job.hess:321` −115.27、`FIRST_EVIDENCE_PROPOSAL.json:11` 三处互证 ✓。

### A4 · TMP 两态（`evidence/A4_TMP_two_states.md`，sha256 `db85e2deca83af8a07b2433fa43cc1f8abece3193f55d66d89df2f667ea45a0b`）

| 态 | 承重成员 | 缺口 | 最小补证（既有材料，不构成计算申请） |
|---|---|---|---|
| TMP\|M_plus | **`27`**（严格合格池唯一成员，`isolated_eligible=True`、`ISOLATED_CONDITIONAL_POOL`，前沿身份 `FROZEN_FRONTIER_CHAIN_VERIFIED`，日志 `22089565…b0b9` 实测一致） | 登记起点 `c10`/`r3_c42` 均不合格（`qualified_registered_starts=[]` → `route=unresolved_qc`）；`r3_c42` 五项缺 `energy_change_Eh`（`FIVE_ITEM_MISSING:energy_change_Eh`）；严格去重簇/搜索范围未重建；生产 review 以 `r3_c42` 承重且 `n_unique=3` 与严格池不一致；搜索新最小值 `r3_c20` 未进成员登记 | 回收 `r3_c42` 单份 job.log 收敛表 `energy_change_Eh` 字段 + 以本态 5 个成员既有几何重建去重簇/合格起点登记 + 出具生产与严格并列裁定记录 |
| TMP\|LiM_2plus | **`c13`**（严格合格池唯一成员，`isolated_eligible=True`，`FROZEN_FRONTIER_CHAIN_VERIFIED`，日志 `5a0da9c4…a861` 实测一致） | 登记起点 `r3m_c00` 物种身份未核（`SPECIES_IDENTITY_UNVERIFIED`；其前沿登记行 73 却 verified，两门并列未见裁决）；`c08` 登记/执行未闭合（`NOT_CURRENT_NUMERIC_MEMBER`，另有 technical_complete_qc_failed/strict_reopt_required/rescue_budget_exhausted 记载）；本态不在 `states_searched` 版本化搜索范围（manifest `search_outcome=released_by_review, max_new_starts=0`）；生产 review 以 `r3m_c00` 承重且 `n_unique=3` 与严格池不一致 | 核 `r3m_c00` 物种身份既有来源（前沿登记行 73 + 腿行 73 + 任务目录四文件重哈希）+ 以本态 3 个 unique 成员既有几何重建去重簇 + `c13` 态级身份裁决记录 |

**前提更正（子代理 6 条已知线索核验：5 证 1 改）**：`coverage_reviews.csv` **无 `TMP|M` 行**（含 TMP 仅行 13/14/15 + 行 2 AN）；labels `TMP,M = not_reviewed`（非 resolved）；`r2_c48_c00` 不是严格池成员而是 `r3m_c00` 的 seed 几何路径（candidates.csv:113，实测 candidates 中 1 行）；`r3m_c00` 严格不合格原因是物种身份未核、非数值五项缺失。

**两态 `new_computation_budget = NONE_JUSTIFIED_YET`；未提出任何计算申请。**
**抽验（全 PASS）**：两态 `qualified_registered_starts=[]`+`route=unresolved_qc` ✓；identity `FROZEN_FRONTIER_CHAIN_VERIFIED` ✓；recheck 两态 `UNRESOLVED_RECHECK_REQUIRED` ✓；production review `n_unique=3` 且 kept 分别为 `r3_c42`/`r3m_c00` ✓；member_statuses 串精确吻合（`r3m_c00::SPECIES_IDENTITY_UNVERIFIED`、`r3_c42::FIVE_ITEM_MISSING:energy_change_Eh`）✓。

### A5 · 其余 36 态缺口机制分组与优先序（`evidence/A5_gap_mechanism_36states.md`，脚本 `a5_gap_extract.py` sha256 `45f271de…` exit 0，输出 `a5_gap_extract_output.txt` `4a23f6c1…`）

**36 态口径（钉死）**：45 accepted − 9 具名（5 条件池 + AN M⁺ + AN LiM²⁺ + TMP M⁺ + TMP LiM²⁺）= 36；另 3 非 accepted 不入组（DMC|M⁺、DMC|LiM²⁺ limited、EC|LiM²⁺ provisional，recovery_class=`需要明确规则裁定`）。48 gap_actions − 9 具名 = 39 ≠ 36。

| 组 | 机制 | 数量 | 成员 |
|---|---|---|---|
| G1 | 物种身份未验证 | 4 | DEC\|M、DME\|LiM_2plus、DME\|M_plus、SL\|LiM_2plus |
| G2 | 五项表结构缺行 | 2 | DME\|M、DOL\|M |
| G3 | 零登记 | 2 | DME\|LiM_plus、EMC\|LiM_2plus |
| G4 | 覆盖已审无物种问题 | 4 | DMSO\|LiM_plus、DOL\|LiM_2plus、EMC\|M_plus、TMP\|LiM_plus |
| G5 | 三门全开 | 24 | 其余 |

- **频次**：身份源未复核 36/36；五项超限 34/36；打印容差不一致 34/36；物种未验证 4；cov `not_reviewed` 28 / `resolved` 8；reg=0 2；recovery_class `检索尚未完成` ×36；budget `NONE_JUSTIFIED_YET` ×48。
- **优先序**：P1 G1 → P2 G4 → P3 G2 → P4 G3 → P5 G5。
- **实验建议**：36 态内**零**（全 `检索尚未完成` + `NONE_JUSTIFIED_YET` + verification README:21「未确认最小新增实验清单或预算」）；唯一提案 = AN|LiM²⁺ 固定几何 AnFreq（待批）。
- **排除 12 态**：8=`已有合格替代证据，进入隔离准入链`、1=`检索尚未完成`（AN|LiM²⁺）、3=`需要明确规则裁定`。

---

## 2. 任务 B · 工程与来源对账（逐项结论）

### B1 · 调度数组别名完整映射（`evidence/B1_scheduling_mapping.csv` + `B1_scheduling_mapping.md` —— **已交付验收**）

**CSV 结构**：127 数据行 × 19 列（`remote_job_id, state, elapsed_s, alloc_cpus, exit_code, cputime_raw_s, campaign, task, member, array_parent_id, element_id, attempt, input_sha256, output_sha256, cost_key, mapping_status, match_basis, candidates, evidence_source`）。

**分类统计（Lead 独立抽验全过）**：

| 维度 | 实测 |
|---|---|
| 行数/id 唯一 | 127 / 127 唯一；与 `remote_job_ledger.txt`（127 行）**集合与顺序全等** |
| mapping_status | MAPPED **88** + AMBIGUOUS **39**（行级 MISSING=0 = 每行至少 1 个权威候选） |
| match_basis 分层 | recorded 5（= 4 条 tuple 唯一 + 1 条元组歧义由记录裁决 `3706757→3700781_2`）/ tuple_unique 83 / tuple_ambiguous 39 |
| 结构性核验 | MAPPED element ⊆ plan 元素、**无重复映射**（防重复计费）；AMBIGUOUS 候选 ⊆ plan；`mapped ∪ candidates = plan` 全覆盖（88+39=127）；`final_remote_check_plan.json#job_ids_requested` 127 元素、不含家长 id |
| 费用键 | 非 MISSING **恰 1 条** = `3791416_0: adopted_charge_core_hours=0.900000`（attempts_ledger 引用）；其余一律 MISSING，不推算不重复计费 |
| 字段级 MISSING | attempt 41 / input_sha256 39 / output_sha256 43（如实标注） |
| 5 条 recorded 绑定（与 Lead 独立证据逐一吻合） | 3705521→3700781_0（`tasks/DME/M_tzvpd/attempts/3700781_0_3705521/`）、3706416→3700781_1（DOL）、3706915→3700781_5（TMP/LiM_plus）、3706757→3700781_2（AN/LiM_2plus，`fetch_receipts.txt:6`）、3791417→3791416_0（`batch_cost_settlement.py:124`，raw 交叉实例） |

**语义空间说明**：plan#`job_ids_requested` = 元素 id 空间（带 `_` 后缀）；台账/CSV `remote_job_id` = JobIDRaw 裸数字——两空间不可直接比集合（Lead 首次比错已纠正），正确比法见上「结构性核验」行。

**未确定/边界**：AMBIGUOUS 39 行的候选集逐行给在 `candidates` 列，**不猜配对**；attempt/哈希字段级 MISSING 不补写；「MAPPED_UNIQUETUPLE 83」为唯一元组推导（确定性连接、无权威记录绑定），与 recorded 5 分开表述。

**MD（198 行）已交付**：完整 SHA256 = `477510e293d0d551fe1fd5726b68dec67f0541f49c8de9d281300a0bc0b08613`（内嵌规则自哈希 `eb545ddb…`，置 0 法，R4 实测自洽）；含 §5 AMBIGUOUS 39 行逐行候选清单（4 组：2 候选×3 行、8 候选×16 行（p4 FAILED 等两组）、20 候选×20 行）、§6 逐列 MISSING 理由（campaign 31/parent 31/element 39/task·member 39/attempt 41/input 39/output 43/cost 126）、§7 复现命令 R1–R7（实测 R1/R4/R5/R6 全 exit 0）、§8 四条声明（未改账本、未强行配对、未重算费用、无新计算）。
**附录（Lead 裁决，保守未采纳）**：双射消解仅使 `3725973`（候选 {3700781_2, 3725968_3}）收敛为 `3725968_3`，其余 38 行仍 ≥2 候选、0 冲突；CSV 保守保留 AMBIGUOUS。命名空间警示：raw `3791416`（属元素 `3791416_1`）/`3774076` 与他数组家长 id 撞号，**绝不可把台账行当家长行计费**。

### B2 · EC 四份输入哈希 + DMC 元数据更正（`evidence/B2_EC_DMC_reconciliation.md` sha256 `79b1559b53a2c2e964f59ef6177bd18988f7f0bac0861b08b8e62e1da39a0199`；`evidence/B2_EC_input_hashes.json` sha256 `cd9a6be1dbfe4798f89d5198fc59218c9c50b0954c249cf1a3b9cada4caa3adf`）

- **EC 四份阶段输入哈希核对**：4 份文件仅 **2 个唯一内容**——opt `fd5f03c3…`（2 份相同）、freq `e2f4dfc6…`（2 份相同）。
- **DMC 元数据更正前后值及来源**（`work/lead_reception_20261102/AUTHORITATIVE_SETTLEMENT.json` 为权威结算）：Opt line 229 `! wB97X-D4 def2-TZVPD Opt VeryTightOpt SMD(acetonitrile) VeryTightSCF SlowConv`；更正前 `old protocol (TightSCF)` → 更正后 `new_numerical (VeryTightSCF + strict; SlowConv)`（`protocol_source_conflict` true→false，correction id `DMC_3928500_0_PROTOCOL_20261103_V1`，详见 B4 §2 staged_dmc 行[3]）；DMC 成本权威 settlement **15.3178 CH**（18.5278 作废）。
- **已验**（上一轮 B2 交付即抽验通过）。

### B3 · coverage 状态核对（`evidence/B3_coverage_state_check.md` sha256 `0758a9e6a9f07afaeeade77aeb5ef7f1497ddba39de342910fcff0fc9040cf90`）

- §1 终测列已填实：coverage `e89188f6…` 与 labels `c21003f5…` **= 起点 = stable，是**。
- §5 终测附录：两哈希复测命令与结果已录，并指向 B4 §7 的 8 共享面文件起止哈希表。
- 结论：本轮结束时正式标签与 coverage 状态**零漂移**。

### B4 · 隔离复跑与逐字段差异（`evidence/B4_isolated_rerun_reconciliation.md` sha256 `e343c71cd8b5b0c9e8d9d9c3722a93a809e95a5b868792ac8b7356fcd3339716`）

| 通道 | 命令 | exit | 关键结果 |
|---|---|---|---|
| R1 登记+去重+coverage 重建 | `PYTHONIOENCODING=utf-8 python scripts/wp_production/rebuild_strict_isolated.py --base docs/handoffs/lead_reception_strict_rebuild_20261103/evidence/b4_isolated_rerun` | **1**（守卫误报，见下） | `states.json` `779dda1c…` **与上游逐字节相同**；gap_actions 46/48 同（仅 DMC 两态 `staged_candidate_action` 文案因元数据更正应用而异）；source_index 字段级差异 = `input_sha256`（script `6cc36a77…`→`468dc00e…` + 新增 corrections `bc5eee79…`）与 staged_dmc 5 行新增字段/行[3] 协议标签更正 |
| R2 v7 coverage 通道 | `python evidence/b4_coverage_rerun.py`（私有副本生成器 `b4_make_coverage_wrapper.py` `d48bb421…`） | **0** | 3 JSON（full_generator_8 `acd48d38…`、diagnostics `b53ad6b3…`、rejected `1e93d4f6…`）+ 6 input_sandbox CSV **逐字节 IDENTICAL**；`generator.py.snapshot` `1fa95011…`→`ed2b621d…` 与 freeze `2bd2343d…`→`5f9cba15…` = 版本/路径差异，freeze 键数同 20、值层面无内容差异 |
| R3 八态 strict 通道 | `python evidence/b4_eight_admission_rerun.py` | **0** | 6/8 顶层文件逐字节同 `eight_admission_v2`；`terminal_input_sha256.json` `d004b775…`→`0edf03d6…` 与 freeze `3a187b76…`→`8053eb54…` = **纯路径改名**（每对 ADD/DEL sha 全同，键前缀 remote_closure→evidence）；路由：基础层 AN\|M⁺ `single_basin_scope_review` + 7 pending；strict 层 DEC/GBL/PC/TMP\|M `coverage_registration_required`、TMP\|LiM²⁺/TMP\|M⁺ `strict_member_evidence_required` |

- **守卫缺陷（结构证明，未修公共代码）**：起始 `input_hashes` = 19 INPUTS + corrections jsonl = 20 键；末检只遍历 INPUTS（19 键）⇒ **corrections 存在时必误报**。独立验证：重跑后 19 输入**零漂移**；上游 19 输入与现值仅 `rebuild_strict_isolated.py` 自身不同。最小修复提案（统一键集 + 回归测试）**待用户批准**。
- **三版本链（`build_coverage_reviews.py`）**：HEAD `5a73d88f…`（v2，536 行）→ v7 快照 `1fa95011…`（v3，543 行，+7 行）→ 工作树 `ed2b621d…`（v3+strict_scope，558 行，**未提交**）；行为验证：默认 `strict_scope=False` 输出与 v7 **逐字节相同**；`strict_scope=True` 唯一调用方 = `run_eight_terminal_admission.py:53`，生产主通道走默认 False。
- **正式标签与费用不变（8 共享面文件起止哈希全等，§7 表）**：labels `c21003f5…`、candidates `6096cd12…`、structures `3a795ce8…`、dispositions `56bbc82c…`、coverage_reviews `e89188f6…`、cost `e92fbeeb…`、weights `201e1954…`、dedup `1f3ea929…`（另有 dmc_reception_registrations `2036b30f…`、physics_completion_set `f07340d7…` 同证）。
- **不猜配对**：B1 范围内的 raw→元素绑定未在本任务处理；DMC 两态 `C3(i)` 保持 closed。

**复跑证据文件**：`b4_rerun_stdout.txt` `dd03c038…`、`b4_coverage_rerun_stdout.txt` `be1428c9…`、`b4_eight_rerun_stdout.txt` `db2955d5…`、`b4_isolated_rerun/run_ab72884b97f0104c/`（README `38d0641a…`、states `779dda1c…`、gap_actions `217dfeb9…`、source_index `6d69ef5b…`）、`b4_coverage_rerun/`、`b4_eight_admission_rerun/`。

---

## 3. 原始来源及哈希总表（本产出）

| 文件 | sha256（前 16 位；完整值见各报告 §交付/附录） |
|---|---|
| A1_five_state_coverage.md | `c42b4d6c3a3a6100…`（196 行） |
| A2_AN_Mplus_identity.md（修正版） | `b962efaa62ad0e9f…` |
| A3_AN_LiM2plus_frequency.md | `ddc1570386700b6c…` |
| A4_TMP_two_states.md | `db85e2deca83af8a…` |
| A5_gap_mechanism_36states.md | `9eff5e81ff601053…` |
| B2_EC_DMC_reconciliation.md | `79b1559b53a2c2e9…` |
| B2_EC_input_hashes.json | `cd9a6be1dbfe4798…` |
| B3_coverage_state_check.md | `0758a9e6a9f07afa…` |
| B4_isolated_rerun_reconciliation.md | `e343c71cd8b5b0c9…` |
| a5_gap_extract.py / a5_gap_extract_output.txt | `45f271de426e342d…` / `4a23f6c10ae8d692…` |
| a3_geometry_probe.py | `ce98afc1fb9d4ac8…` |
| b4_make_coverage_wrapper.py / b4_coverage_rerun.py | `d48bb421441b63bb…` / `15eb66eafa874a37…` |
| b4_rerun_stdout.txt / b4_coverage_rerun_stdout.txt / b4_eight_rerun_stdout.txt | `dd03c038f59cf5f4…` / `be1428c97bbcc6c7…` / `db2955d5ac6b67c9…` |
| b4_eight_admission_rerun.py | `900cf02dd25f07ff…` |
| **B1_scheduling_mapping.md** | `477510e293d0d551fe1fd5726b68dec67f0541f49c8de9d281300a0bc0b08613`（198 行；内嵌置 0 法自哈希 `eb545ddb7b30f81873244be2a6ed8d1d7b9b9db273b7679ffd0257c553d84238`，R4 实测自洽） |
| **B1_scheduling_mapping.csv** | `8431547c9cb69ce9b233073681caa733b6a0f323bab0c74a94a7ece7c8d1bb61`（127 数据行 × 19 列） |

上游关键来源（各报告内已逐项列路径+行+完整 SHA）：`run_06c49d9e7ebe0688/`（README `c8fa2679…`、states `779dda1c…`、gap_actions `e7ce5ba9…`、source_index `3346f78f…`）、`coverage_recheck.json` `182d32ab…`、`coverage_8.json` `26ccc6e5…`、`decisions.csv` `ac430d37…`、verification README `61e930b8…`、`candidate_sources.json` `3bccdb41…`、frontier 三表 `0f8a8653…`/`7310354c…`。

---

## 4. 未确定事项（汇总）

1. **B1**：AMBIGUOUS 39 行未配对（候选全列、不猜配对——待数据侧后续裁决，含双射消解仅可解 `3725973` 一行的附录分析）；字段级 MISSING（attempt 41 / input 39 / output 43 / campaign·parent 31）不补写；raw 与家长 id 撞号警示已入档。
2. **A1**：frontier 与 structures 对同一成员 job.log 哈希不等的关系未解释；audit index 过期哈希（`3f2c692d…`≠`3a795ce8…`）；GBL/PC 范围记录限定未找到。
3. **A2**：AN M⁺ 远端来源 `INACCESSIBLE_NOT_VERIFIED`；同态双路由的输入语义差异未裁定。
4. **A3**：−115.27 cm⁻¹ 成因三选一未收窄（等固定几何 AnFreq 第四格）；hess 与 3706757 绑定为合理推断。
5. **A4**：`r3m_c00` 前沿登记行 73 verified 与严格池 `SPECIES_IDENTITY_UNVERIFIED` 两门并列未见裁决。
6. **A5**：3 态非 accepted 的 recovery_class 待规则裁定；36 态 `检索尚未完成`。
7. **B4**：`rebuild_strict_isolated.py` 守卫 20 vs 19 键缺陷未修（待用户批准）；`build_coverage_reviews.py` v3+strict_scope 未提交。

## 5. 是否需要新物理证据

- **本轮不产生任何必须的新计算**：A 线全部建议限于「回收既有 job.log 字段 / 重建去重簇与登记 / 出具并列裁定记录」；36 态零实验建议。
- **唯一科学提案** = AN|LiM²⁺ 固定几何 AnFreq（0.5–4 core-h，96 core-h 预留未批，`PROPOSED_NOT_AUTHORIZED_NOT_SUBMITTED`）——**待用户批准后才可讨论**。
- 所有对象的 `new_computation_budget = NONE_JUSTIFIED_YET`。

## 6. 边界声明

本汇总是**只读核验与隔离复跑**的产物：零新增计算、零作业提交、零共享生产写入、未改阈值/判据/正式标签、未手填 `resolved`、未做 δ 选择、未迁移未批准跨协议成员、未修改公共代码（两处缺陷只报告）。**不构成准入结论、不构成用户签认**；技术复审 ≠ 用户签认。
