# D7/D8 语义级独立复审（C5 后半）· 非作者 fresh-context 只读复审 + Lead 复验 + 运行时补测

- 复审执行：子代理 `5ae70b98-36b9-4691-b1ca-40af331587a0`（非作者、fresh context、全程只读；审计产物仅落临时目录；未运行任何 `work/` 脚本、未跑 pytest、无 git 写操作）。
- Lead 复验与运行时补测：本会话 Lead（兼公处理），2026-11-04。
- 本文件结论 = **证据充分性评估，不构成切换授权**（切换仍按 `SWITCH_PLAN.md` C1–C6 + S0–S7 执行）。

## §0 复审对象与 sha256 核验（子代理 `sha256sum -c` → exit=0，6/6 OK；Lead 抽验一致）

| # | 对象 | 期望 sha256（…前12位/全值） | 实测字节 | 判定 |
|---|---|---|---|---|
| 1 | `work/dmc_staged_receiver_v5.py`（shared） | `205f1ba93d9a0b69f2ea5f86595eef527da03db6d6aa8b2a331dd25a2ca9bb66` | 98,779 | ✅ MATCH |
| 2 | `work/admission_closure_20261102/rev5_candidate_d8/dmc_staged_receiver_v5_candidate.py` | `138df33b6c2a677ac2697825ae3680650c0ea1b3235d219a66e7d4dd13dd153c` | 114,142 | ✅ MATCH |
| 3 | `work/test_dmc_staged_receiver_v5.py` | `ee6b9f2987542aa998e63e9a52f2b6a0bbb79abc4109b254cdc8237181e2a7f2` | 29,921 | ✅ MATCH |
| 4a | `work/admission_closure_20261102/D7_FIX_VERIFICATION.json` | `e0c47ef990ae33c4953cc00098c66af5413069475c7dd9a92e51fa06ed1eb022` | 7,716 | ✅ MATCH |
| 4b | `work/lead_reception_20261102/rev5_baselines/dmc_staged_receiver_v5__rev5.4.py` | `94186049e5ed6bb3edce3754aa26d5a7c9bb9ba33d986f5879666cba5db69838` | 96,336 | ✅ MATCH |
| 5 | `…/p10_switch_plan/freeze_manifest.json`（其 shared/d8_candidate/test_v5 三条登记 vs 盘上逐字节） | `4ddbdf10b42f6ac1703b6427eaf9b3864fea19367f4c39b7419993f879a2bf8b` | 4,566 | ✅ 一致 |

路径来源：`P1_D7D8_version_reconciliation.md` §6/§8（D8 缺陷位点登记 `:1821`）。无任何不匹配，未触发停止条件。

## §A 候选 vs 共享模块全量 diff（逐 hunk 分类）

- `git diff --no-index --numstat` → **exit=1（git 语义），`279 3`**；`--unified=0 | grep -c '^@@'` → **5 hunk**；全量 diff 319 行逐行读毕；三文件 `ast.parse` OK（仅解析未执行）。
- **Lead 复验**：numstat `279 3` ✓、hunk 数 `5` ✓（独立重跑一致）。

| hunk | 位置(shared→cand) | 行数 | 内容 | 分类 |
|---|---|---|---|---|
| 1 | `@@ -62,6 +62,7` | +1/−0 | `import os`（迁移用 `os.replace`；shared 内 `\bos.` 使用=0，纯新增零影响） | ① D8 |
| 2 | `@@ -70,7 +71,15` | +9/−1 | `HERE` 向上锚定 `work/` 放置兼容层 + 注释 | ② **非 D8 语义**：模块在 `work/` 时循环零次执行、三元回落 `_SELF`，与原 `HERE = Path(__file__).resolve().parent` **逐字等价**（仅候选字节含此分支） |
| 3 | `@@ -95,6 +104,40` | +34/−0 | `RECEIVER_VERSION` / `LEDGER_SCHEMA_READABLE` / `RECORD_SCHEMA_KNOWN` / `LEDGER_SCHEMA_V3_REQUIREMENTS` 常量 | ① D8 |
| 4 | `@@ -1818,7 +1861,34` | +28/−1 | 缺陷位点 `:1821` register 校验替换（D8 核心） | ① D8 |
| 5 | `@@ -1863,4 +1933,210` | +207/−1 | `_validate_ledger_document()`、`migrate_ledger()`、EOF 补换行 | ① D8（含 1 行 ② 性质 EOF 修正） |

**对账**：1+9+34+28+207=279；−1×3=3，与 numstat 完全一致。被删 3 行 = `HERE = …`、`doc = {"schema": loaded.get(…)…`、`path.write_text(...)`（EOF 换行）。

**③ 无关改动 = 0 条（红旗 0）**。需明示的仅 hunk 2（放置兼容层）与 hunk 1（`import os`）——均不改变共享模块部署在 `work/` 时的行为，不构成红旗。

## §B D7 修复是否绑定当前字节

- `D7_FIX_VERIFICATION.json`（232 行读毕）：`module.path=work/dmc_staged_receiver_v5.py`、`bytes=98779`、`sha256=205f1ba9…bb66` ⇒ **绑定当前 shared 字节（非旧版）**。内容：21 个 dirty 案例逐案 `POPULATION_NOT_INTEGRAL`、`dirty_cases_all_refused=true`、缺行 `IDENTITY_MISSING`、成对 `IDENTITY_LINES_DISAGREE`、clean 过、10 条真实 log 全过。
- 字节级证明（只读比对 rc=0）：shared `165–471` vs candidate `208–514` sha 前缀同为 `436672d471a3ff93`（13,513 B，equal）；未改动区间 shared `101–1817` == candidate `144–1860`。
- **结论：D7 修复既被 JSON 绑定于当前 shared 字节，也逐字节存在于当前 candidate。** 缺口继承：JSON **未声明作者独立性**、未单独签 candidate 字节（P1 §7① 仍未闭合）。

## §C 缺陷位点 `:1821` ±30 行核对

- **shared（缺陷仍在）** `:1812-1822`：只查 JSON 解析与 `members is list`；`:1821` 盘上 `v2` 原样保留，`:1848-1853` 追加 v5 记录覆写 = **把 v5 记录写进 v2 标签（静默降级）**；缺 `schema` 键时默认冒充 v3。周围拒绝码未改（`LEDGER_UNREADABLE` `:1816`、`LEDGER_MALFORMED_ENTRY` `:1819`、`LEDGER_TAMPERED` `:1836`、`MEMBER_NOT_UNIQUE` `:1843`）。
- **candidate（修复后）** `:1855-1892`：显式 `on_disk_schema` → 空/非串 `LEDGER_SCHEMA_MISSING`；不在 `(v2,v3)` `LEDGER_SCHEMA_UNKNOWN`；`!= v3` → **`LEDGER_SCHEMA_MIGRATION_REQUIRED`（拒收、文件不动、指向迁移工具）**；`_validate_ledger_document()` 统一校验（缺 record schema/身份缺失 → `LEDGER_MALFORMED_ENTRY`；未知 → `LEDGER_RECORD_SCHEMA_UNKNOWN`；body 不符 → `LEDGER_TAMPERED`）；仅盘上已是 v3 才续写。`MEMBER_NOT_UNIQUE` 仍可达（`:1913`）。迁移 `migrate_ledger()` 六步与 R5 顺序一致（路径安全→加载→目标契约校验→顶层键守卫 `LEDGER_MIGRATION_CHANGED_TOP_LEVEL_KEYS`+成员规范相等→`os.replace` 原子写→回读复检），报告 `ledger_migration_report/v2`，明示 raw 字节相等 NOT_TESTED。
- **运行时影响（必须写入切换预案）**：盘上主账本 `work/dmc_staged_staging_ledger.json`（`c336acb5…`/111,047，冻结登记）顶层 `schema=dmc_staged_staging_ledger/v2`（**Lead 实测确认**）⇒ 切换到候选后所有 `register()` 一律 `LEDGER_SCHEMA_MIGRATION_REQUIRED` 拒收，直至显式迁移。与 R5「倾向不迁移」**互斥**——属既定 fail-closed 设计、非缺陷，但「切换」与「可继续追加」在当前盘上账本下不可兼得，**授权层必须先裁定迁移 or 停摆**。

## §D 测试覆盖映射（只读源码，子代理未运行）

- `work/test_dmc_staged_receiver_v5.py`：36 个 `def test_`（AST 一致），R6 参数化 → 40 例；**导入共享模块，不测候选**。覆盖 D7 全族（R1–R7、R2b/R2c、D1 电池）。
- **冻结 `test_v5` 对 D8 缺陷位点覆盖 = 0**：仅两处 `R.register`（`:99/:112`）且均为新建 `tmp_path/ledger.json`；无预置 v2 账本用例，不涉 `LEDGER_SCHEMA_*`/`migrate_ledger`/`_validate_ledger_document`。
- **D8 覆盖在 `rev5_candidate_d8/test_d8_schema.py`**（35 个 `def test_`：不就地续写、各类 fail-closed、迁移族 `:135-224`、D7 参数化回归 `:248-275`、同路径/别名拒写、契约守卫、双路径一致性），导入**候选**。
- 该文件 **不在 p10 冻结清单**（16 对象无它），由 `MANIFEST_v5/v6`、`NARROW_CONFIRMATION.json`、`work/receiver_switch_20261103/MANIFEST_v1_20261104T002904.json` 以 **`d23e45d91b48…`/21,085 B** 绑定（Lead 实测一致；`MANIFEST_v2` 的 `47425d6b…`/19,439 为已登记 FREEZE_LAG 旧值）。

## §E 运行时补测（Lead 执行，关闭复审「充分条件未满足」缺口）

| 步骤 | 环境 | 结果 | 证据 |
|---|---|---|---|
| E-a | 工作区 venv（`.venv-review-20261103`）跑 `test_d8_schema.py` | **1 败**：`test_manifest_supersedes_lives_inside_the_json`。根因两层：① 子进程 `subprocess.run(text=True)` 按本地 GBK 解码 UTF-8 输出 → reader 线程 `UnicodeDecodeError` 掩盖真实返回码（断言串接再抛 TypeError）；② 手动复跑定位真实失败 = `freeze_candidate.py:83 write_text` → **`PermissionError: [Errno 13]` 写仓库子目录** = 本会话已知的工作区进程 ACL 限制（`ENV_RECOVERY.md` §4），**非 D8 语义缺陷** | 日志 `.pytest_tmp_review/d8_schema.log`、`freeze_child.log`（987 B 含完整 traceback） |
| E-b | 副作用核查 | `MANIFEST_v*.json` 仍 **7 个**（无 v7=幂等成立）；`dmc_staged_receiver_v5_candidate.py` sha 仍 `138df33b…`；E-a 期间 `CANDIDATE_DIFF_vs_205f1ba9.diff` 未被触及 | 目录 ls + sha256 |
| E-c | **工作区外独立 venv**（`C:/Users/Little Alety/AppData/Local/Temp/venv-d8-20261104`，基础 py3.10.11 建、同轮子离线装、不覆盖任何既有环境；先实测 `repo_write_ok`）跑 `test_d8_schema.py` | **60 tests / 0 fail / 0 error / 0 skip，exit 0**（60 > 35 因参数化展开） | junit `d8_out/d8_schema.xml`（tests=60, failures=0, errors=0, skipped=0, time=3.525） |
| E-d | 同 venv 跑整个 `rev5_candidate_d8/`（schema + candidate_receiver 两文件） | **100 tests / 0 fail / 0 error / 0 skip，exit 0** | junit `d8_out/d8_dir.xml`（time=6.174） |
| E-e | E-c/D 写副作用 | `CANDIDATE_DIFF` 被子进程**重写**（mtime 更新为 2026-11-04 01:13:47）但**内容等价**：17,233 B、+279/−3 与 `MANIFEST_v6` 记录一致（生成确定性、输入字节未变）；MANIFEST 仍 7 个 | ls + sha256 `4c0afa2f…` |

复现命令（E-c）：
```bash
py -3.10 -m venv "$V2"   # V2=C:/Users/Little Alety/AppData/Local/Temp/venv-d8-20261104
"$V2/Scripts/python.exe" -m pip install -q --no-index \
  --find-links "E:/Claude Code/电解液溶剂-HB/.venv-review-20261103/wheels" \
  rdkit pytest numpy pandas scipy pyyaml python-dateutil   # → exit 0
cd E:/Claude Code/电解液溶剂-HB/电解液溶剂HB-Code
PYTHONDONTWRITEBYTECODE=1 "$V2/Scripts/python.exe" -m pytest \
  work/admission_closure_20261102/rev5_candidate_d8/ -q -p no:cacheprovider \
  --basetemp="$OUT/bt2" --junitxml="$OUT/d8_dir.xml"   # → exit 0, 100/100
```
版本：`3.10.11 | rdkit 2026.09.1 | pytest 9.2.0 | numpy 2.2.6 | pandas 2.3.3 | scipy 1.15.3 | pyyaml 6.0.3`。

## §F 采纳结论与缺口继承（Lead）

**已满足（证据充分性）**：
1. 六对象字节绑定自洽（子代理 6/6 + Lead 抽验全一致）；候选 vs shared **279/3、5 hunk 全部归 ①D8/②兼容层，③ 类无关改动 = 0**。
2. **D7 绑定当前字节成立**（JSON `205f1ba9…` + 区间字节等价双证）。
3. D8 修复语义到位且 fail-closed；共享缺陷位点 `:1821` 状态与拒绝码面核对完毕。
4. **运行时**：候选目录测试 **100/100 全过**（工作区外独立 venv，可复现命令已记录），D8 缺陷位点运行时面由 `test_d8_schema.py` 覆盖并全绿——复审报告「充分条件未满足」的运行时缺口**已关闭**（在新环境下，非原环境）。

**缺口继承（不掩盖，均属授权层或清单层）**：
- G1 `D7_FIX_VERIFICATION.json` 作者独立性未声明、未单独签 candidate 字节（P1 §7①）。
- G2 `test_d8_schema.py`/`test_candidate_receiver.py` **不在 p10 冻结清单**（由 `d23e45d9…` MANIFEST 链绑定）——建议切换时（S2）冻结这两文件，作为 freeze_manifest v2 增量。
- G3 `test_v5` 文件头自述「not part of the frozen suite yet」与 p10 `FROZEN` 登记**表述矛盾**（字节无矛盾，属文案项）。
- G4 切换后「v2 账本 → 全部 register 拒收」的处置（迁移 or 停摆）属授权层（见 §C 运行时影响）。
- G5 工作区 venv 下该套件 1 例被 ACL 阻断（见 §E-a），属环境限制非语义；已在 §E 用工作区外 venv 关闭。

**本复审不构成切换授权。**
