# t6 第三方复核：§四之七 三处记录级缺陷（独立重算）

复核人：submitter-bypass-audit（与 t2 同纪律——不抄 Lead 数字，全部从当前磁盘现算）。
方式：`recheck.py`（本目录，只读、不写仓库任何文件、不触桥/网/集群/git）+ 一次补充单行检视。
命令与退出码：
```
cd "E:\Claude Code\电解液溶剂-HB\电解液溶剂HB-Code"
.\.venv\Scripts\python.exe -B docs\handoffs\four_state_recovery_20261023\audit_ledger_defects_crosscheck_20261026\recheck.py   # EXIT=0
```
（frontier_identity_evidence 列名补充检视同为 `.venv\Scripts\python.exe -B -c`，EXIT=0。）

## 0. 总结论

| 项 | 判定 |
|---|---|
| ① `wp2_state_identity_qc`（行 25）state_identity 口径内一致 | **确认**（含一处措辞不符，见 §1.3） |
| ② `wp5_pool_extension`（行 42）`extension_rows=0` 读错来源文件 | **确认**（全部数字吻合） |
| ③ `wp6_explicit_ligand`（行 43）两名一量 + 边界结论 | **确认**（全部数字吻合，含函数实跑） |
| 42 行分布 22+13+3+2+2 求和闭合 / 未满足 17 | **确认** |

**曾报「与 §四之七不符」1 处，经 Lead 盘上裁定不成立**：本复核把 `molden_status` 列当成了 `status` 列（`"status" in col` 取到 `fc[0]`），实际 `status={'computed':80}` 与 Lead 一致（详见 §1.3 裁定）。**三处缺陷全部确认、与 §四之七零分歧**。

## 1. 缺陷①：frontier_localization=not_computed 在其数据源口径内一致

### 1.1 state_identity 侧（台账所读来源）——一致
- `outputs/physics_completion/state_identity/state_identity_qc.csv`：DictReader **60 行**；列 `frontier_localization_status` 分布 = **`{'not_computed': 60}`**（与 §四之七"60 行全 not_computed"吻合）。
- `state_identity_acceptance.csv`：**13 行**（"13 项自检"吻合）；**第 12 项（1-based）** `check_id=frontier_localization_is_registered_not_guessed`、`ok=true`——与 §四之七引用逐字一致；13 项全部 ok=true。
- 台账行 25 原文实测：`qc_checks_ok=13/13; …frontier_localization=not_computed`，状态 `partial` ⇒ **判定与自身数据源一致，维持 partial 是对的**（成员原判、Lead 复核、我方三方向一致）。

### 1.2 frontier 管线侧（另一口径，80 行）
- `frontier/frontier_identity_evidence.csv`：**80 行**；`identity_qc_status` 分布 = **`{'verified': 80}`**（与 Lead 称 80 verified 吻合）。

### 1.3 原报「与 §四之七不符」——**经 Lead 盘上裁定不成立（本复核误读列名）**
- **原断言**：`frontier_localization.csv` 80 行 `status` 实测 = `{'parsed': 80}`，§四之七 写 `computed` 是"值名引用不准"。
- **裁定**：**不成立——是我的复核读错了列，Lead 的 `computed` 是对的。** 同文件（`csv.DictReader`，80 行）有**四个**含 "status" 的列并存：`status={'computed':80}`、`molden_status={'parsed':80}`、`fmopop_status={'parsed':80}`、`identity_qc_status={'verified':80}`；生成器 `build_frontier_localization.py:370-371` 明确 `row["status"] = "computed" if molden_status=="parsed" and fmopop_status=="parsed" else "parse_failed"`。⇒ 我报的 `parsed` 是 **`molden_status`** 列（`fc[0]`，`"status" in col` 命中它），打印标签却写成 `status`。
- **结论**：§四之七 的 **80 computed / 80 verified 保持不变**，**不更正 Lead**。缺陷①的定界（台账只读 §6.3 口径、未引用 frontier 管线）由本复核**确认**，且**不因该误读改变**。
- **教训归档**：读 CSV 一律按**完整列名**取列（`row["status"]`），禁止用子串反推列；这与本任务 §2 那处"子串启发式误报"是同一族陷阱，已写入 P9 §四之七裁定段。

## 2. 缺陷②：extension_rows=0 读错来源文件

- `build_plan_compliance.py:797`（与 Lead 称行号一致）：`ext_rows = [r for r in cfg_set if r.get("cohort") == "extension" and r.get("mol_id")]`——确实在 `cfg_set` 上筛。
- `data/metadata/physics_completion_set.csv`：DictReader **30 行**；`cohort` 分布 = **`{'main': 12, 'method_audit': 8, 'sampling_audit': 4, 'excluded': 6}`**；**cohort=="extension" 的行数 = 0**（全部与 Lead 数字吻合，含"无 extension"）。
- `data/metadata/physics_completion_extension_pool.csv`：**11 个候选（DictReader 数据行，不含表头；原始文件含表头共 12 行）**；`registration_status` = **11/11 `FROZEN_NOT_COMPUTED`**（吻合；t3 成员"11 vs 12"的口径差就是含不含表头，本行已写明）。
- `strict_readiness_wiring.py:492-502` `derive_pool_extension_trigger(wp5_full_pool_ok)`：**只以 wp5_full_target_pool_evaluated 布尔为入参**，源码不读任何 extension 计数（我的 `recheck.py` 里那句启发式 `reads ext_rows? True` 是子串误报——docstring 里含 `wp5_pool_extension` 一词即命中 `ext`，**以函数签名与实跑为准**，正式判定：**不读**）。实跑三输入：`None→unknown`、`False→not_triggered`、`True→triggered`——与 Lead 实测一致 ⇒ **"已核不影响触发闸门"确认**。
- 台账行 42 原文实测：`extension_rows=0; replay_pool=legacy_pool_not_blind`，状态 `not_satisfied` ⇒ 缺陷为记录级（读数 0 的成因是查错文件），状态方向不变，**确认**。

## 3. 缺陷③：li_pair_complete 两名一量 + 边界结论

- **台账侧（行 43 原文实测）**：`li_pair_complete=12/12 … production_ensembles=44/48 gate_ready=false trigger_state=not_triggered scope=optional`，状态 `blocked_on_production`。
  - 来源链确认：`build_plan_compliance.py:318` `live_counts = strict_main_counts(set_main, progress["scientific"]["accepted_legs"])` → `:320 li_pair_ok` → `:170` 按 `LI_STATES=('LiM_plus','LiM_2plus')`（:81）对 **主态生产腿 accepted** 计数 ⇒ **12/12 与 scientific=48/48 口径自洽**。
- **触发侧**：`strict_readiness_wiring._complete_li_pairs(labels)`（:505-512，按**系综 labels** 双 Li accepted）实跑 = **9/12**：`AN, DEC, DME, DMSO, EMC, GBL, PC, SL, TMP`；不成对的 3 分子 = **DMC / DOL / EC，各缺 `LiM_2plus`**（labels 48 行，accepted 44 / limited 4）——与 Lead 声称逐项吻合。
- **边界结论验证（函数实跑，非目测）**：`build_plan_compliance.wp6_gate_ready`（:158-161，要求 `ensembles ≥ WP6_REQUIRED_PRODUCTION_ENSEMBLES=48`，:61）：
  - `wp6_gate_ready(12, 44) = False`（台账侧 12/12 单过不触发）
  - `wp6_gate_ready(9, 44) = False`（触发侧 9/12 单过不触发）
  - `wp6_gate_ready(9, 48) = wp6_gate_ready(12, 48) = True`（48/48 后两侧必同时为真）
  - ⇒ **未 48/48 时两侧同假 ⇒ 不改 `blocked_on_production`**：**确认**。
  - `derive_wp6_trigger(当前 labels)` 实跑 = `not_triggered`，与行 43 `trigger_state=not_triggered` 一致。

## 4. 求和闭合复算（独立数表）

`plan_compliance.md` 数据行（按 6 列反引号 item_id + 状态词表匹配）：
- 总行数 = **42**；分布 = **satisfied 22 / partial 13 / exempt 3 / not_satisfied 2 / blocked_on_production 2**（22+13+3+2+2=42 闭合）；
- 未满足（partial+not_satisfied+blocked，exempt 不计）= **13+2+2 = 17**——与 §四之七/Lead 口径**逐项吻合**（旧简报"16"确为错）。
- 三个目标行的 md 行号：`wp2_state_identity_qc` = **行 25**、`wp5_pool_extension` = **行 42**、`wp6_explicit_ligand` = **行 43**（与简报所引行号一致）。

## 5. 未覆盖 / 边界

- 未重算 42 行中除三行外的其余行的判定链（那是 t5/partial-audit 的面，本任务只核 §四之七三处 + 分布闭合）。
- `frontier_localization.csv` 的四列状态语义（`molden_status` / `fmopop_status` / `identity_qc_status` / `status` 之间的关系）起初未逐一展开，本复核因此把 `molden_status=parsed` 误当作 `status`；**经 Lead 补查生成器 `build_frontier_localization.py:370-371` 后才定死：`status` 是由前两者派生的 `computed`**（见 §1.3 裁定）。教训：该文件**四个列名都含 "status"**，任何按子串选列的读法都会踩。
- 真实集群/桥未触达（无授权，本任务全部只读磁盘 + 本地函数实跑）；未改任何生产文件；未 git commit。
- 方法注记：§2 的启发式子串检查误报已在报告内自我更正，教训同类于 t2 的"尺子先于结论"。
