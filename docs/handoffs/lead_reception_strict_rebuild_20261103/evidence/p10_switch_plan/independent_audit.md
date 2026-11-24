# P10 · 独立审计报告（非作者 · 冻结清单 / P3·P6 分层 diff / 套件复跑 / 卫生）

> 执行者：非作者独立子代理（fresh context，未参与 P3/P6/D8/任何被审对象的编写）｜时间 2026-11-04 00:2x–00:37:48
> 被审对象 = `evidence/p10_switch_plan/freeze_manifest.json` 钉定的 16 个对象 + P3/P6 修改层 + 交付卫生。
> 审计员自报**零仓库写入**（仅复跑 pytest 生成 2 个 gitignored `__pycache__/*.pyc`；脚本与 junitxml 全在系统临时目录）；**未运行 `p6_entry.py` / `rebuild_strict_isolated.py`**；未重生成任何 evidence 产物。
> 本文件由 Lead 落盘（审计员按只读纪律未写仓库）；§3 = Lead 独立复验（子代理自报≠验收）。

## 1. 审计员实测（自报）

### 1.1 冻结清单核验（16 objects）

命令：`PYTHONIOENCODING=utf-8 python <Temp>/audit_freeze_check.py`（标准库逐对象重算 sha256+bytes）→ 首跑 exit 1（其脚本键名笔误，已修正）→ 修正后 exit 0；**00:29、00:37:48 复跑均 exit 0，三次一致**。

**结果：OK 15 / ABSENT 1 / MISMATCH 0**（`frozen_at_utc=2026-11-03T16:12:22Z`，object_count=16）：

| # | key | sha12 / bytes（清单=实测） | 判定 |
|---|---|---|---|
| 1 | shared_module_v5 | `205f1ba93d9a` / 98,779 | OK |
| 2 | d8_candidate | `138df33b6c2a` / 114,142 | OK |
| 3 | test_v5 | `ee6b9f298754` / 29,921 | OK |
| 4 | test_v4 | `8dac1aa061da` / 26,493 | OK |
| 5 | ledger_main | `c336acb5051d` / 111,047 | OK |
| 6 | registry_freeze | `ea3c6c209aaa` / 1,312 | OK |
| 7 | registry_v1 | `c13e43c35b77` / 2,256 | OK |
| 8 | p3_target | `a7eee5aa3df7` / 29,558 | OK |
| 9 | p3_baseline | `ed2b621d30f8` / 27,332 | OK |
| 10 | p6_target | `83581f169d26` / 22,475 | OK |
| 11 | p6_baseline | `468dc00ee21a` / 22,313 | OK |
| 12 | gap_test_v1 | `957c39e1b3a6` / 4,647 | OK |
| 13 | gap_test_crash | `3d2b98ba0f89` / 4,919 | OK |
| 14 | manfest_v2_d8 | — | **ABSENT（文件不存在，与清单 status 声明一致）** |
| 15 | d8_narrow_confirmation | `4cf03e6f15ec` / 9,585 | OK |
| 16 | d8_manifest_v2 | `9de6c2e0f096` / 5,298 | OK |

8 个完整 64 位锚值（`205f1ba9…`/`138df33b…`/`c336acb5…`/`a7eee5aa…`/`ed2b621d…`/`83581f16…`/`468dc00e…`/`9de6c2e0…`）**8/8 匹配，0 MISMATCH**。

### 1.2 P3 分层 diff（`git diff --no-index --numstat`，均 exit 1=有差异）

| 层 | 对 | 插入/删除 | hunk | 定性 |
|---|---|---|---|---|
| **A＝经审改动** | `.orig` → 工作树 | **45 / 3 = 48 行** | 4 | H1 新增 `EXCLUSION_SOURCE_PROVENANCE` 常量（纯新增）；H2 docstring+`import hashlib`+`provenance=[]`；H3 核心守卫：`read_text`→`read_bytes`，**删除原 `except (OSError, ValueError): continue` 静默跳过**，改 OSError / ValueError+UnicodeDecodeError / 非 dict 三路 `raise SystemExit`，逐源 append `{path, bytes, sha256}`；H4 成功后 `global … = provenance`。**4 hunk 全在模块常量与 `_rejected_probe_members()` 内，无夹带**。附带行为面（守卫语义内）：不可读/不可解析由跳过→中止；非对象由 AttributeError→SystemExit |
| **B＝先存改动** | HEAD → `.orig` | **29 / 7 = 36 行** | 7 | 主题=v2→v3 strict basin guard：docstring 资格措辞、`REVIEW_VERSION`→`coverage_review_v3_strict_basin_guard_20261103`、新增 `strict_member_evidence_required`、`multi_basin_coverage`→`single_basin_scope_review`、`build_rows(*, strict_scope=False)`、新增 `coverage_registration_required`、verdict 路由扩展。**7 hunk 与 exclusion guard 无关** |
| 合计 | HEAD → 工作树 | **74 / 10 = 84 行** | — | **84 = 36 + 48 精确相加 → 两层不重叠、可加**（`--histogram` 与 Python difflib 双法交叉复算同值） |

⚠ 出入（如实）：任务书称 HEAD→基线「约 48 行」，实测 **36 行**；恰为 48 行的是 `.orig`→工作树层。（Lead 注：P3 文档 `P3_exclusion_source_guard.md:26` 写的「48 个 diff 行」指层A=本次经审改动，口径正确；错误口径只存在于审计任务书措辞。）

### 1.3 P3/P6/gap 套件复跑（含 junitxml 双证）

| 组 | 命令（cwd=仓库根） | exit | 实测 |
|---|---|---|---|
| 1 | `python -m pytest tests/test_exclusion_source_completeness.py tests/test_clean_clone_dependencies.py tests/test_archive_dependency_inventory.py -q -p no:cacheprovider` | **0**（junit 复跑亦 0） | 22 `.`；junit：**tests=22 failures=0 errors=0 skipped=0** |
| 2 | `python -m pytest tests/test_strict_coverage_single_cluster.py -q -p no:cacheprovider` | **0**（junit 复跑亦 0） | 5 `.`；junit：**5/0/0/0** |
| 3 | `python -m pytest docs/…/evidence/p2_item2_gap_tests/ -q -p no:cacheprovider` | **0**（junit 复跑亦 0） | `...s......`；junit：**tests=10 failures=0 errors=0 skipped=1**（skipped=`test_migration_interrupt_recovery_awaiting_tool`）→ **9 过+1 跳** |

junitxml 均写系统临时目录；未传 `--basetemp`；未启 cacheprovider。

### 1.4 P6 只读核验

- diff：`.orig` → 工作树 = **4 插入 / 1 删除，仅 1 个 hunk** `@@ -339,7 +339,10 @@`（删=旧 :342 的 input_hashes 比对；增=final_hashes 构造 + `corrections_path.is_file()` 追加 digest + 比对）→ **与预期「仅 :342 一处 4 行」一致，无其他差异**。
- `p6_verification.json`（2,041 B，mtime 11-03 21:36:26）9 键：`schema/created_utc/entry/run_ids/runs/same_input_rerun/order_variation/freeze`。**无 `status` 字段、无 "PASS" 字面**；`run_a/b/c` 各仅 `[exit, log_tail]`，**exit 全 0**，log_tail 统计三跑相同 `{states:48, members:132, NO_QUALIFIED_MEMBER:40, COVERAGE_CLAIM_REVIEW_REQUIRED:3, CONDITIONAL_EVIDENCE_SUFFICIENT:5}`；`run_ids` 三跑同 `run_e194e35c5585a7dd`；`same_input_rerun.byte_identical=true`、`diff=[]`；`order_variation` 三产物 `scientific_content_equal=true`；`freeze={inputs_unchanged:true, outputs_tree_unchanged:true, outputs_files:15118, git_status_unchanged_except_p6:true}`。
- **`input_hashes` 字段不存在**（`"input_hashes" in json → False`）→ 无法在该文件内与冻结清单 hash 级比对（字段缺失，非通过/不通过）。相邻只读依据：`runs/{a,b,c}/…/source_index.json` 的 `input_sha256`（各 20 项，三跑完全相等）含 `rebuild_strict_isolated.py = 83581f16…`（=p6_target）、corrections 输入 `candidate_source_metadata_corrections.jsonl=bc5eee79…` 在列；`p6_baseline 468dc00e…/22,313` 仅见 `baseline/BASELINE.json`（reason="P6 entry freeze-check fix (:342 omits corrections path added at :199)"）与清单一致。

### 1.5 交付卫生

- **密钥模式**（api_key / BEGIN PRIVATE KEY / password= / secret / sk-长串 / AKIA / ghp_ / xox-，大小写不敏感）：handoff 全目录 **0 命中**；`scripts/wp_production/`（含两目标文件）**0 命中**。对照组证明扫描器有效：同目录 `pytest` 30 次/8 文件、scripts 下 `def main` 80 文件。
- **残留**：`*.tmp/bak/~/pytest_cache` **0**；`*.pyc` 2 个（gap_tests `__pycache__/` 下，.gitignore:7 覆盖，由审计员组3复跑生成）；2 个 `.orig` = 清单声明的基线证据（非垃圾）。仓库根另有 **23 个 `.pytest_*` 目录 Permission denied**（既有残留、审计范围外、未处理）。
- **只读副作用**：`outputs/`、`tests/`、`scripts/` 近 25 分钟 **0 改动**；handoffs 内改动 = 5 个作者文件（mtime 与冻结清单一致）+ 2 pyc。

⚠ **环境事实**：审计期间 `work/` 下有**并发写入**（data_analysis_20261103 / receiver_switch_20261103 / archive_pkg_20261103 等，mtime 持续到 00:35，非审计员操作）→ **另一会话正在同仓库作业**；但三次冻结复算（早期/00:29/00:37:48）均 15 OK+1 ABSENT+0 MISMATCH，两个 scripts 文件 mtime 仍为 11-03 19:17:34 / 21:32:31。

### 1.6 审计员「未能验证项」（均非通过）

1. 未运行 `p6_entry.py`/`rebuild_strict_isolated.py`（任务禁止）→ 三跑**可复现性未复现**，仅只读核对既有产物。
2. `p6_verification.json` 无 `input_hashes`/`status` → 「是否全 PASS」只报 exit=0 与字段缺失；hash 依据来自 `runs/*/source_index.json`。
3. 任务书「HEAD→基线约 48 行」与实测 36 行不符，未推断成因。
4. 未复算 source_index 20 项哈希与当前工作区逐项一致（仅核脚本项 vs p6_target）；未审计 P1–P10 其他文档与 work/ 并发写入。
5. `work/` 全树 find 超时（240s）→ 改 maxdepth 2 抽查，无法穷尽证明零副作用。
6. 23 个权限拒绝 `.pytest_*` 目录未读取。
7. 未作任何准入/科学结论。

## 2. Lead 独立复验（子代理自报≠验收）

| 复验项 | Lead 命令 | 实测 | vs 审计员 |
|---|---|---|---|
| P3 层A | `git diff --no-index --numstat .orig → build_coverage_reviews.py` | **45 / 3**（ec=1） | ✅ 一致 |
| P3 层B | `git show HEAD:… > /tmp/head_p3.py`（25,627 B）→ `numstat head → .orig` | **29 / 7**（ec=1） | ✅ 一致 |
| P3 合计 | `numstat head → 工作树` | **74 / 10**（=36+48 可加） | ✅ 一致 |
| P6 | `numstat .orig → rebuild_strict_isolated.py` | **4 / 1**（ec=1） | ✅ 一致 |
| 冻结锚值抽样 3/3 | `sha256sum` shared `205f1ba93d9a…` / d8_candidate `138df33b6c2a…` / crash_test `3d2b98ba0f89…` | 全等 | ✅ 一致 |
| ABSENT 声明 | `ls …/rev5_candidate_d8/NARROW_CONFIRMATION.json` | No such file | ✅ 一致 |
| 套件抽跑（组2） | Lead 独立 venv 环境 `pytest tests/test_strict_coverage_single_cluster.py -q` | **5 `.`，exit 0** | ✅ 一致 |
| P3 文档口径 | `grep "48"` 于 P3 文档 | `:26「48 个 diff 行」`=层A 本次改动，**口径正确** | 无需修正 |

**Lead 结论：审计员关键声明全部复验一致，采信。** 两处诚实缺口如实继承：`p6_verification.json` 缺 `input_hashes`/`status` 字段；三跑可复现性属既有产物只读核对（本轮零新增计算，不重跑 p6_entry）。

## 3. 本审计在切换预案中的位置

- 满足 `SWITCH_PLAN.md` §2 **C5 的「非作者审计」半边**：冻结候选/测试/登记册/隔离账本（16 对象）已由非作者绑定当前字节核验（本文件 §1.1 + Lead 复验 §2）。
- **仍待**：绑定当前字节的 D7/D8 **语义级**独立复审（D8 候选 `138df33b…` vs shared `205f1ba9…` 逐 hunk 语义、D7 修复验证 `e0c47ef9…` 复核）——切换前置条件，HOLD 下未启动。
- **并发警告**：`work/` 有他会话写入 → **提交前必须重跑冻结清单**（哈希全等才可提交），本文件记录的三次+Lead 一次核验仅证明各自时刻未变。
