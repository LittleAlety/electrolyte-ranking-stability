# P1 · D7/D8 版本核收（Plan 首批第 1 项：D7/D8 版本核收）

> 会话：公共处理会话（Plan 唯一共享生产写入者）｜轮次：Plan 首个执行批次
> 权限声明：**本文件为只读核收**——零共享源改动、零账本改动、零切换、零迁移、零新增计算。
> 核收 ≠ 切换授权：按 D8 独立审计原文「本审计不构成切换授权……切换另行授权，不由『复审通过』自动触发」，本核收同样**不构成切换、不构成正式准入、不构成对共享 rev5 的改动**。
> 复核时间：2026-11-03（仓库 HEAD `80933e54f8a605d9dd6d033c0f2861e33b591c13`）。

## 1. 接收器版本轴（receiver axis）

| 版本 | SHA256 | 字节 | 角色 | 复审/签章绑定 |
|---|---|---|---|---|
| rev4 `work/dmc_staged_receiver.py` | `32501b7185d61d7ac05ba1cd4f03ae1f4b85d1f5c8225992a8272a1ce7374278` | 49,075 | 历史 v4 | — |
| rev5.3 基线 | `ad3d940f195a5e07abb4e11a0bfe7cef0ce3b59d47528f3246614b128869c74e` | 96,523 | 旧基线 | — |
| rev5.4 基线 | `94186049e5ed6bb3edce3754aa26d5a7c9bb9ba33d986f5879666cba5db69838` | 96,336 | LIVE 复审对象 | `REV5_INDEPENDENT_REVIEW.json`（64 例 61P/2F/1P，2 FAIL=D7）+ `REV5_RUNTIME_REVIEW.json` 均绑定此字节 |
| **当前共享模块（rev5.5）** | **`205f1ba93d9a0b69f2ea5f86595eef527da03db6d6aa8b2a331dd25a2ca9bb66`** | **98,779**（mtime 11-02 22:37） | **D7 已修、D8 未修** | `D7_FIX_VERIFICATION.json` 绑定此字节；D8 审计以其为 baseline 并 Z1 前后钉住（审计期前后哈希不变） |
| 快照（与当前逐字节同） | 同 `205f1ba9…` | 98,779 | `rev5_snapshot_205f1ba9/module__…py` | MANIFEST_v2 的 baseline 条目 |
| D8 候选 #1 | `a39e51364f83124bcc489e0e42d3b2b4aae38f5cbc01d85122058852c97ee28d` | 112,825 | 首轮审计对象 | MANIFEST_v0（已 SUPERSEDED） |
| D8 候选 #2 | `177db542f3bf557e9574a40ac0d072c0b0108834d2292a6aedc61dadc185b96c` | 114,382 | 07:55:33 就地重写 | `D8_INDEPENDENT_REVIEW` 绑定 |
| **D8 候选 #3（盘上现值）** | **`138df33b6c2a677ac2697825ae3680650c0ea1b3235d219a66e7d4dd13dd153c`** | **114,142** | 二次重写，H24/O1 修复后字节 | `NARROW_CONFIRMATION.json` + **MANIFEST_v2**（`9de6c2e0…`，frozen_at 2026-11-03T08:02:55，`missing=[]`、`all_hashed=true`） |

**当前模块相对 rev5.4 的差异**：diff 52 行，全部为 rev5.5 D7 修复增量（`RE_POP_LINE`/`RE_POP_VALUE`、`_population_lines()` 拒绝路径、alpha/beta 成对完整性检查），无其他行为改动。

## 2. D7（单条非有限布居值静默跳过）现状

- **修复在活路径上**（当前模块实测行号）：
  - `:411 identity_lines()` → `:422-423` 调 `_population_lines()`（**不再走旧数值路径**）；
  - `:392-408 _population_lines()`：`RE_POP_LINE`（`:167-180`，`N(Alpha)\s*:(.*)$` 全行捕获，NaN/inf 尾巴可入）→ `RE_POP_VALUE` 严格有限小数匹配，不匹配即 `ReceiverRefusal("POPULATION_NOT_INTEGRAL")`，**拒绝而非静默丢弃**；
  - `:427-431` alpha/beta 行数不等 → `IDENTITY_LINES_DISAGREE` 拒绝；整段缺失保持 `IDENTITY_MISSING`（长期契约，`:424` 注释）；
  - 旧 `RE_NALPHA/RE_NBETA`（`:165/:166`）**已成死码**——全文件仅定义、零调用点（grep 实测仅 2 行命中）。
- **签章证据**：`work/admission_closure_20261102/D7_FIX_VERIFICATION.json`（`e0c47ef9…`，7,716 B，与模块同刻 11-02 22:37），schema `d7_fix_verification/v1`，绑定 `205f1ba9…`/98,779：`dirty_cases_all_refused=true`（NaN/nan 等逐案 `POPULATION_NOT_INTEGRAL`）、`absent_field_case=IDENTITY_MISSING`、`pairing_case`（3 alpha vs 2 beta）→ `IDENTITY_LINES_DISAGREE`、`clean_case_passes=true`、`real_logs_all_parse=true`（Rk1/probe_01 等真实 log 全过）。
- **测试实测**（本轮复跑，命令见 §6）：`work/test_dmc_staged_receiver_v5.py`（`ee6b9f29…`，29,921 B，11-02 18:25）40 用例 = **35 通过 + 5 失败**；5 失败**全部**为 `ModuleNotFoundError: No module named 'rdkit'`（`work/dmc_staged_receiver_v5.py:199` 惰性导入 `from rdkit import Chem`，仅触发元素号路径的 sealed-entry/registration/composite/cross-job 5 例）——**环境缺 rdkit，非逻辑失败**；D7 相关用例（NaN/Inf 参数化 `:289-296`、非有限拒绝 `:335/:352`、成对拒绝 `:306`）**全部在 35 通过内**。当前可定位的三个解释器（系统 python / py -3.10 / `.venv` 3.12 空壳）均无 rdkit；历史「89/89 exit=0」所用环境本轮不可定位（见 §7 未确定 ③）。
- **独立复审覆盖边界**：64 例 LIVE 复审绑定的是修复前 rev5.4；D8 审计把 `205f1ba9` 当 baseline 但只审 D8/迁移面；**未发现以 205f1ba9 为被审主体、覆盖 D7 修复面的独立复审签章**（`D7_FIX_VERIFICATION` 文件内未声明作者独立性）——记为未确定 ①。

## 3. D8（账本 schema 静默降级）现状

- **缺陷仍在当前模块**：`:1821 doc = {"schema": loaded.get("schema", LEDGER_SCHEMA), …}`——文件已存在时保留旧 schema，盘上 v2 会被原样续写；`:97 LEDGER_SCHEMA = "dmc_staged_staging_ledger/v3"`；`:82 SCHEMA = "dmc_staged_receiver/v5"`。
- **三轴偏斜实测**（盘上 `work/dmc_staged_staging_ledger.json`，`c336acb5051deb31c276dc54c8bfefbcc64bf93d0244c82cb722a8869fd382d2`，111,047 B）：
  - **ledger 轴**：盘上顶层 `schema = dmc_staged_staging_ledger/v2`，模块期望 `v3`；
  - **record 轴**：5 条成员记录 `schema = dmc_staged_receiver/v4`，当前模块写 `v5`；
  - **receiver 轴**：见 §1。
  - 偏斜=已知事实，**按 R5 用户裁定倾向先不迁移**（append-once 账本，静默迁移破坏只追加一次）；本核收**未迁移**。
- **候选修法**（仅存在于候选文件，未切换）：`:1866 on_disk_schema = loaded.get("schema")` 显式读取、`:1891` 显式续写；迁移路径 `migrated = copy.deepcopy(loaded)` 只替换 schema（H24 修复，`:2061-2065`）+ 顶层键集合守卫 `LEDGER_MIGRATION_CHANGED_TOP_LEVEL_KEYS`（`:2071-2075`）+ 迁移报告 `ledger_migration_report/v2`（`:2109-2112`）。

## 4. 候选线与 MANIFEST 时序（F1 就地重冻）

| 时刻 | 事件 |
|---|---|
| 11-03 07:43:13 | MANIFEST_v0 冻结 `a39e5136…`/112,825 |
| 07:4x–07:55 | D8 审计交件（绑定 a39e5136；2 条代码发现 H24/O1） |
| 07:55:33 | 候选就地重写 → `177db542…`/114,382（**F1 第 3 次发生**，MANIFEST 未重冻） |
| 08:02:55 | **MANIFEST_v2 重冻**（`9de6c2e0…`）：绑定候选 `138df33b…`/114,142 + baseline 快照 `205f1ba9…`，`missing=[]`、`all_hashed=true` → **F1 闭合** |
| 08:16 | `NARROW_CONFIRMATION.json` 收口 |

**独立复审处置状态**（引自 `D8_INDEPENDENT_AUDIT.md` §11.3）：H24 顶层键丢弃 = **FIXED AND VERIFIED**；O1 守卫自比较 = **FIXED**；F1 = 已由 MANIFEST_v2 闭合；H20（用户裁定不构成错误）/H30（设计取舍）/O3（硬门设计）仍 OPEN、非阻塞。

## 5. 核收结论（工程事实，非科学/准入裁定）

1. **版本轴可分辨**：receiver 7 版、候选 3 版、MANIFEST 3 版全部有实测 SHA256 与绑定关系，无「同名不同字节」含混。
2. **D7 = 已修在当前共享模块**（活路径+拒绝码+签章 JSON+测试覆盖），但**缺独立复审签章覆盖其修复面**（未确定 ①）。
3. **D8 = 缺陷仍在当前共享模块**；修复存在于候选 `138df33b` 并有独立复审（H24/O1 FIXED AND VERIFIED）+ MANIFEST_v2 冻结；**切换与账本迁移均未授权、未执行**（Plan open question 1；R5 裁定倾向不迁移）。
4. **盘上账本三轴偏斜（v2/v4/v3）为已知事实**，本核收原样登记，未改动账本一个字节。
5. 本核收**不触碰**科学判据、coverage、身份结论、正式标签与费用。

## 6. 复现命令与退出码（cwd=仓库根）

| 编号 | 命令 | 退出码/结果 |
|---|---|---|
| P1-R1 | `sha256sum work/dmc_staged_receiver_v5.py` | 0 → `205f1ba93d9a0b69…` |
| P1-R2 | `grep -n "RE_NALPHA\|RE_NBETA" work/dmc_staged_receiver_v5.py` | 0 → 仅 `:165/:166` 定义，无调用点 |
| P1-R3 | `grep -n 'loaded.get("schema"' work/dmc_staged_receiver_v5.py` | 0 → `:1821`（D8 缺陷位点） |
| P1-R4 | `sha256sum work/dmc_staged_staging_ledger.json` | 0 → `c336acb5051deb31…`（schema=v2 实测见 §3） |
| P1-R5 | `PYTHONIOENCODING=utf-8 py -3.10 -m pytest work/test_dmc_staged_receiver_v5.py -q -p no:cacheprovider` | **1** → 35 passed / 5 failed（5 failed 全部 `No module named 'rdkit'`，见 §2） |
| P1-R6 | `sha256sum work/admission_closure_20261102/D7_FIX_VERIFICATION.json work/admission_closure_20261102/rev5_candidate_d8/MANIFEST_v2_20261103T080255.json` | 0 → `e0c47ef990ae33c4…` / `9de6c2e0f09622c8…` |
| P1-R7 | `diff work/lead_reception_20261102/rev5_baselines/dmc_staged_receiver_v5__rev5.4.py work/dmc_staged_receiver_v5.py \| grep -c "^[<>]"` | 0 → `52`（全部为 rev5.5 D7 修复增量） |

## 7. 未确定事项

1. **`D7_FIX_VERIFICATION.json` 的作者独立性未在文件内声明**——修复验证存在且覆盖全部 D7 场景，但「独立复审签章绑定 205f1ba9 的 D7 面」缺位；是否补一次独立复审 → 交 Lead 决定。
2. **D8 切换与账本 v2→v3 迁移授权**（Plan open question 1 / R5 用户裁定）——保持不切换、不迁移；余额/复审通过 ≠ 授权。
3. **rdkit 环境缺口**：本轮三个解释器均无 rdkit，5 例元素号路径用例无法在本机复绿；历史「89/89 exit=0」环境不可定位——需要时请指明可用环境，不自行改造环境。
4. H20/H30/O3 仍 OPEN（非阻塞，设计取舍/用户裁定类）。

## 8. 本文件引用对象哈希总表

| 对象 | SHA256 |
|---|---|
| `work/dmc_staged_receiver_v5.py`（当前共享模块） | `205f1ba93d9a0b69f2ea5f86595eef527da03db6d6aa8b2a331dd25a2ca9bb66` |
| `work/lead_reception_20261102/rev5_baselines/dmc_staged_receiver_v5__rev5.4.py` | `94186049e5ed6bb3edce3754aa26d5a7c9bb9ba33d986f5879666cba5db69838` |
| `work/admission_closure_20261102/rev5_candidate_d8/dmc_staged_receiver_v5_candidate.py` | `138df33b6c2a677ac2697825ae3680650c0ea1b3235d219a66e7d4dd13dd153c` |
| `work/dmc_staged_staging_ledger.json` | `c336acb5051deb31c276dc54c8bfefbcc64bf93d0244c82cb722a8869fd382d2` |
| `work/admission_closure_20261102/D7_FIX_VERIFICATION.json` | `e0c47ef990ae33c4953cc00098c66af5413069475c7dd9a92e51fa06ed1eb022` |
| `work/admission_closure_20261102/rev5_candidate_d8/MANIFEST_v2_20261103T080255.json` | `9de6c2e0f09622c82d219c4595ed7ddcbfe0f68ae50d8f0f477a8dd823037b42` |
| `work/test_dmc_staged_receiver_v5.py` | `ee6b9f2987542aa998e63e9a52f2b6a0bbb79abc4109b254cdc8237181e2a7f2` |
| `work/dmc_staged_receiver.py`（v4 历史） | `32501b7185d61d7ac05ba1cd4f03ae1f4b85d1f5c8225992a8272a1ce7374278` |
