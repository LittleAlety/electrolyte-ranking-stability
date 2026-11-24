# 仓库重整交接（2026-11-07）：`scripts/wp_production/` → `scripts/production/`

> 本文件记录**本轮实际做了什么、怎么验的、以及哪些事没做**。
> 判据口径：每条「已做」都绑定当次实测证据；未做的单列，不混进完成声明。

## 1. 做了什么

| 项 | 内容 |
| --- | --- |
| 搬迁 | **108** 个文件：103 `*.py` + 4 `*.ps1` + `wp1_audit_src.txt` |
| 分类 | `jobs` 26（23 py + 3 ps1）｜`ingest` 8（7 py + 1 txt）｜`validation` 23｜`ensembles` 27｜`analysis` 18｜`release` 6（5 py + 1 ps1） |
| 旧路径 | **107** 个兼容入口（HISTORICAL_ENTRY）：103 py + 4 ps1。`wp1_audit_src.txt` 不留入口（它是数据文件，随 `emit_wp1.py` 一起迁到 `ingest/`） |
| 权威映射 | `scripts/production/registry.json`（旧路径 → 新路径 + 分类），所有派生件都从它生成 |
| 生成索引 | `scripts/production/SCRIPT_INDEX.md`、`scripts/wp_production/README.md`（由 `build_script_index.py` 生成，带 `--check`） |
| 手写说明 | `scripts/production/README.md`（旧 `wp_production/README.md` 的导数政策/收口链/队列纪律原文迁入，路径已更新） |

**兼容入口的实现方式**（重要）：不是复制符号，而是**在入口模块自己的命名空间里 exec 真实源码**，
并把 `__file__` 指向真实实现。原因：222 个测试用 `spec_from_file_location` 加载模块后
`monkeypatch.setattr(m, ...)`；若只复制函数对象，函数仍引用目标模块的 `__dict__`，
补丁会**静默失效**。实测：`build_ensemble_cost_by_family` 打补丁后其函数 `__globals__` 内 `REPO` 确为新值。

## 2. 地址与定位的改法

| 旧写法 | 新写法 | 处理量 |
| --- | --- | --- |
| `HERE.parents[1]` / `Path(__file__).resolve().parents[2]` | `_paths.REPO_ROOT` | 81 个文件 |
| `HERE / "peer.py"`（跨目录起子进程） | `_paths.script_path("peer.py")` | 15 处 |
| `REPO / "scripts" / "wp_production"`（sys.path） | `_paths.PRODUCTION_DIR` | 若干 |
| `finalize_wp2.ps1` 的仓库根推导 | 向上找 `pyproject.toml` 的循环（与深度解耦） | 1 处 |
| `finalize_wp2.ps1` 的步骤地址 | 全部改指 `scripts\production\<cat>\*.py` | 73 处 |

`_paths.py` 的定位判据：**同时存在 `pyproject.toml` 与 `src/electrolyte_ranking/`**。
运行时目录（`task_dir.parents[2]` 等 2 处）**未改**——它们不是仓库定位。

## 3. 验收证据（当次实测）

| 检查 | 结果 |
| --- | --- |
| `python -X utf8 scripts/production/build_script_index.py --check` | `CHECK OK -- 108 scripts across 6 categories; 107 legacy entries consistent` |
| 全部 103 个真实实现 `import` | 0 失败 |
| 全部 103 个兼容入口 `import` | 0 失败 |
| 兼容入口子进程执行（`build_probe_routes.py --check`、`run_wp2_queue.py --status`） | 与真实路径输出一致、退出 0 |
| PowerShell 语法（`supervise_pending.ps1`） | 12 errors → **0**（见 §5 BOM） |
| 全量 pytest：基线 43 failed → 本次 40 failed | **新增失败 0**；另有 3 个原本失败的布局/索引测试转绿 |

**基线口径**：搬迁前先跑一次全量 pytest 存 `work/reorg_20261107/pytest_baseline.log`（43 失败），
搬迁后同样存 `pytest_after2.log`（40 失败），再对两个失败集合做 `comm` 差集。
剩余 40 个失败全部是既有问题（torsion 登记表漂移、P4 包、coverage v4 在改、`.venv` 空壳缺 numpy 等），
本轮**未修**也不声称修过。

### 3.1 产物零改动的证据（当次实测）

| 检查 | 结果 |
| --- | --- |
| `git status --porcelain outputs deliverables` | 44 条修改，**全部在会话开始前就存在**（含并行会话在 `production_ensemble_*` / `d6_*` / `blind_replay` 上的在飞工作） |
| 4 个 mtime 变新的产物（`AB_round_summary.csv`、`candidate_rounds.csv`、`d6_ranking_sensitive_preregistration_draft.md`、`week20/stage21_shell_redox_plan.json`） | `git status` 为空 ⇒ **内容与 HEAD 逐字节相同**；mtime 变新来自测试套件的"重建后恢复"，不是内容修改 |
| `outputs/week27/claim_scope.{json,md}` | 曾被 `audit_claim_scope.py` 重写（改 README 的连带），已 `git checkout` 回滚，现干净 |
| **冻结面逐类清点**（`git status --porcelain`）：`outputs/week*` | **1 个**改动：`outputs/week3/SHA256SUMS`，**mtime 2026-10-29**、diff 仅 1 行（`F64_physics_completion_budget_curve.png` 的哈希），**早于本会话 9 天，非本轮所改** |
| **冻结面逐类清点**：`deliverables/**` | **0 个**改动 |
| **冻结面逐类清点**：`docs/00_*`–`docs/64_*` | **0 个**改动（本轮只改 `docs/65_repo_layout.md` 与不带编号的文档） |
| 收口链步数声明 | 实测 `grep -cE '^Step "' finalize_wp2.ps1` = **79**，与 `docs/PROJECT_GUIDE.md`、骨架图、README 生成器里的「79 步」一致 |

### 3.2 ⑦「历史与本机材料」审计结果（只审计，不搬动）

| 对象 | 现有索引 | 结论 |
| --- | --- | --- |
| `outputs/week1..week43/`、`week22_hardening`、`week24_corealign` | [骨架 §2](../../65_repo_layout.md) 的「周 ↔ WP」表 + [progress/README](../../progress/README.md) 的主题路由 | **已有索引，不新建**。周目录保留原位：`week2|week3/SHA256SUMS` 与各 `manifest.json` 记录脚本与产物路径 |
| `docs/NN_*.md`（0–67） | 骨架 §2.2 的编号区间表 + progress 主题日志 | **已有索引，不新建**；区间由 `test_layout_doc_covers_every_numbered_docs_prefix` 钉住 |
| `deliverables/part1|part2` | 各自 `README.md` + `进度说明.md` + `SHA256SUMS_新结构.txt` + 路径映射表 | **已有索引**；镜像由生成器维护，本轮不重排（见 §4） |
| `work/`（**56** 个跟踪文件，实测 `git ls-files work \| wc -l`） | 无索引 | 拆分为 **50 + 3 + 3**：50 个在 `work/coverage_fix_20261106/**`、3 个在 `work/coverage_review_20261106/**`（两者都由 HEAD 提交 `06fca61` 作为 `FROZEN_FOR_GITHUB_NOT_DEPLOYED` **有意发布**，且各带 `.gitattributes * -text` 保字节，合计 **53**）；另 3 个是 `.gitignore` 白名单（`check_paper.py`、`week36_number_audit.md`、`week36_wp_mapping.json`）。**解跟踪阻塞在用户裁决**（见 §4） |
| 五跳阅读路径 | 本轮新增 `docs/PROJECT_GUIDE.md` §0（入口→当前生产流程→权威证据→历史归档→对外交付），并由 `test_the_reading_path_is_written_down_and_resolves` 钉住五跳与落点存在 | **本轮补齐的缺口**：此前没有任何一页把"生产流程"和"交付镜像"串进同一条路径 |



### 3.3 新旧路径等价性扫描（50 个 `--check`）

脚本：`work/reorg_20261107/equivalence_sweep.py`，结果：`work/reorg_20261107/EQUIVALENCE_SWEEP.json`。
做法：对 registry 里**每个含 `--check` 的脚本**，分别用新路径（`scripts/production/<cat>/x.py`）
与兼容入口（`scripts/wp_production/x.py`）各跑一次，比对**退出码 + 末行输出**。

| 指标 | 结果 |
| --- | --- |
| 扫描脚本数 | **50**（49 `*.py` + `finalize_wp2.ps1`；后者用 python 跑无意义，PS 语法已单独验证） |
| 退出码与末行**完全一致** | **50 / 50** |
| 不一致 | **0** |
| 扫描期间 `git status(outputs,deliverables)` 是否变化 | **否**（扫描前后快照逐行相同 ⇒ 这批 `--check` 确实是只读的） |

其中绿：`build_compute_provenance`、`build_state_identity_qc`、`build_frontier_*`(3)、
`build_wp2_closure`、`build_wp2_cost_scenarios`、`refreeze_manifest`、`make_physics_completion_figures` 等。
其中**原本就红且两路径同红**（不是本轮造成的）：`build_plan_compliance`（`differs plan_compliance.md`）、
`build_coverage_reviews`（漂移，并行会话在改）、`build_production_ensemble_aggregator`（`STALE: [inputs]`）、
`build_torsion_registry`（漂移）、`build_physics_completion_deliverables`（`CHECK FAILED (21)`）、
`build_torsion_probe_package`（`No module named 'rdkit'`）、`settle_ec_campaign` / `archive_raw_outputs --check` /
`verify_archive --check`（参数要求不同，`exit=2`）。

### 3.4 文档链接与命令示例审计

脚本 `work/reorg_20261107/link_audit.py`（只读），覆盖本轮改动/新建的 **10 份文档**：

| 检查 | 结果 |
| --- | --- |
| 相对链接（含 `#anchor`）解析 | **118 条，全部存在** |
| `scripts/production/<cat>/<file>` 引用（正斜杠与反斜杠两种写法） | **145 处，全部存在** |
| `docs/65_repo_layout.md` §3 计数句 vs 磁盘 | 169 / 166 / 3 —— **一致**（修掉了重写时丢掉的「顶层」措辞，否则读者按句搜索会漏） |

### 3.5 层次契约：实现层不得反向依赖兼容层

`test_production_does_not_depend_on_the_compatibility_layer`：`scripts/production/**` 里
**不得** `import wp_production`、也不得把 `scripts/wp_production/` 当常规路径
（`_paths.py` 的兜底与 `build_script_index.py` 的生成逻辑除外）。

这是兼容层**可退休**的技术前提——只要实现层还依赖旧目录，删入口就会崩。
**负对照已实测**：往 `analysis/build_descriptor_analysis.py` 注入一行 `import wp_production`，
该测试**立刻变红（exit 1）**，随后字节恢复原样（`restored: True`）。⇒ 这条守卫会真的开火，不是恒绿空壳。

## 4. 本轮**没有**做的事（逐条给理由与可执行入口）

| 未做项 | 理由 | 可执行入口 |
| --- | --- | --- |
| 不重建 `deliverables/part2` 镜像 | 方案 Out 明确「交付镜像先保留原地址」；重建会把镜像内部布局改成 `scripts/production/**`，并把并行会话 3 个未提交的成本产物一并发布——这是发布动作，不是目录整理 | `python -X utf8 scripts/production/release/build_physics_completion_deliverables.py`（源清单已指向真实实现） |
| 不重建 `README.md` | 生成器的 `--check` 本来就 `MISMATCH`；重建会额外发布 `provisional 0→1`（来自并行会话未提交的 `production_ensemble_labels.csv`）。已手工把 README 恢复原样，只改**生成器**的路径 | `python -X utf8 scripts/build_github_readme.py`（下一次合法重建会一并更新路径与数字） |
| ~~不动 `work/` 的 Git 跟踪~~ **已于 2026-11-07 执行变体 A（用户选定）** | `work/` 原有 **56** 个跟踪文件 = **53 个有意冻结发布**（`coverage_fix_20261106/**` 50 个 + `coverage_review_20261106/**` 3 个，同属 HEAD 提交 `06fca61` 的 `FROZEN_FOR_GITHUB_NOT_DEPLOYED`）+ 3 个 `.gitignore` 白名单。按变体 A 只从索引移除这 53 个、**本地文件全部保留**；代价是这 53 个冻结证据**从 GitHub 消失** | 见下方「变体 A 执行记录」 |

### 变体 A 执行记录（2026-11-07，当次实测）

```powershell
# 1) 记录 53 个文件的内容哈希（只取哈希列并排序）
git ls-files work | Where-Object { $_ -notmatch '^work/(check_paper\.py|week36_)' } |
  Set-Content work/reorg_20261107/wt_paths.txt
Get-Content work/reorg_20261107/wt_paths.txt |
  ForEach-Object { git hash-object --no-filters -- $_ } | Sort-Object |
  Set-Content work/reorg_20261107/wt_hash_before.txt
# 2) 只动索引（-r 递归，--cached 保文件）
git rm -r --cached work/coverage_fix_20261106 work/coverage_review_20261106
# 3) 复核内容不变
Get-Content work/reorg_20261107/wt_paths.txt |
  ForEach-Object { git hash-object --no-filters -- $_ } | Sort-Object |
  Set-Content work/reorg_20261107/wt_hash_after.txt
Compare-Object (Get-Content work/reorg_20261107/wt_hash_before.txt) `
               (Get-Content work/reorg_20261107/wt_hash_after.txt)
```

| 判据 | 实测结果 |
| --- | --- |
| 目标清单 | **53** 个（50 + 3），与 `work/` 56 个跟踪文件减去 3 个白名单一致 |
| 内容哈希前后比对 | `diff` 无差异 ⇒ **53/53 字节未变** |
| 磁盘文件 | `coverage_fix_20261106` **346** 个、`coverage_review_20261106` **15** 个仍在盘上（含未跟踪 scratch） |
| `git status --porcelain work/` | **只有 53 个 `D `**（索引侧删除），**没有任何 `M`** |
| 白名单 | `check_paper.py`、`week36_number_audit.md`、`week36_wp_mapping.json` **仍被跟踪** |
| 防复发 | `git check-ignore -v` 显示 `.gitignore:76 work/*` 覆盖这两个目录 ⇒ 不会被 `git add -A` 重新纳入 |
| 连带面 | 站点 `repo_inventory` 只统计 `src/scripts/config/data/structures/outputs/tests/docs/deliverables` 前缀、**不含 `work/`** ⇒ `docs/assets/data.js` 不因此陈旧（实测 `--check` 仍绿） |
| 提交 | **未提交**（`git rm --cached` 只改索引） |

**变体 B：先搬到正式落点再解跟踪（保住公开可见性，代价是路径变化需留映射）—— 未被采用，保留原文备查**

```powershell
$targets = git ls-files work | Where-Object { $_ -notmatch '^work/(check_paper\.py|week36_)' }
$targets | ForEach-Object { git hash-object --no-filters -- $_ } |
  Sort-Object | Set-Content work/_hash_before.txt
New-Item -ItemType Directory -Force docs/handoffs/coverage_freeze_20261106 | Out-Null
Move-Item work/coverage_fix_20261106, work/coverage_review_20261106 docs/handoffs/coverage_freeze_20261106/
# 只比哈希**列**（路径已变，路径列不该参与比对）
git add -A docs/handoffs/coverage_freeze_20261106
git ls-files -s docs/handoffs/coverage_freeze_20261106 |
  ForEach-Object { ($_ -split '\s+')[1] } | Sort-Object | Set-Content work/_hash_after.txt
Compare-Object (Get-Content work/_hash_before.txt) (Get-Content work/_hash_after.txt)
git rm -r --cached work/coverage_fix_20261106 work/coverage_review_20261106
```

两个变体的判据相同：`Compare-Object` **必须无输出**；`.gitattributes` 的 `* -text` 必须随目录一起走，
否则换行归一化会让 blob 与 `_hash_before.txt` 不一致（实测该属性生效时，`git hash-object`
加不加 `--no-filters` 得到同一值）。**这两个变体都不提交**，只动索引，最终提交与否由你决定。
| 不跑收口链 `finalize_wp2.ps1` | 它需要 `.venv` 里的 pytest 与 `work/wp2prod` 现场；本机 `.venv` 是空壳（`include-system-site-packages=false`，site-packages 只有 3 项），链会在 pytest 步失败 | 用可用的解释器：`pwsh -NoProfile -File scripts/production/release/finalize_wp2.ps1 -PythonPath <python>` |

## 5. 本轮踩到并修掉的三个真缺陷（留档，别重犯）

1. **`from __future__` 被引导段挤到非首行** → 18 个文件语法错误。修法：引导段只允许插在
   docstring 与 `from __future__` 块之后（`repair_bootstrap.py`）。
2. **兼容入口的 `TARGET` 少了 `.py`** → 107 个入口全部指向不存在的路径（首次 `import` 测试才发现）。
   修法：模板用完整文件名，而不是 `Path(...).stem`。
3. **UTF-8 BOM 被编辑工具吃掉** → `supervise_pending.ps1` 的 PowerShell 语法检查从 0 变 12 个错误
   （PS 5.1 对无 BOM 文件按 ANSI 解码，中文注释变乱码）。修法：按 `git show HEAD` 的原始首字节恢复
   （`restore_bom.py`，实测只有该文件受影响）。

另有一条**未造成损失但值得记**：`outputs/week27/claim_scope.json` 记录了 `README.md` 的 sha256，
所以「手工改 README」会自动让该记录失效；本轮改 README 后立即回滚，`git checkout` 后该文件回到干净状态。

4. **站点数据嵌入文档摘要**：`docs/assets/data.js` 里 `docs` 每页都带一段 `summary`（取自正文首段），
   所以**只改 `docs/PROJECT_GUIDE.md` 的正文**也会让 `test_terminal_site::test_check_mode_reports_the_site_as_consistent` 变红。
   处置：改完 docs 后必须重跑 `python -X utf8 scripts/build_terminal_site.py`（本轮实测 diff 仅 6 行，
   全是该页 summary 与新增小节标题，**无任何科学数字变化**），再 `--check` 复核。

## 6. 回退方式

```powershell
# 1) 删掉新树与兼容入口，恢复旧目录（本轮全程未提交）
Remove-Item -Recurse -Force scripts\production
git checkout -- scripts\wp_production
git checkout -- docs scripts README.md tests
# 2) 校验
git status --porcelain | Select-String "scripts/wp_production"
```

因为**没有任何 `git commit`**，回退就是 checkout；`work/reorg_20261107/` 下的台账与日志可以留作记录。

## 7. 「这次迁移是否完全正确」——自查结论

**成立的部分**：新旧两条路径都能跑（import 与子进程两种方式都实测）、
**50 个 `--check` 的新旧路径退出码与末行输出 50/50 完全一致**（§3.3）、
产物字节**一个都没改**（§3.1）、已生成产物里登记的 `generator` 路径仍可解析、
**118 条文档链接与 145 处脚本引用全部存在**（§3.4）、
全量测试无新增失败、布局契约由测试钉住（`test_repo_layout.py::test_production_layout_contract_holds`）、
五跳阅读路径成文且落点存在（`test_the_reading_path_is_written_down_and_resolves`）、
**实现层不反向依赖兼容层**且负对照会开火（§3.5）。

**不成立/未闭合的部分**（不要读成「全部完成」）：

1. **兼容入口是技术债**：`scripts/` 下现在有 103 份转发文件。它们是**可删的**，但必须按
   `scripts/wp_production/README.md` 里写的三条件同时满足后才删。现状量化：`tests/` 里仍有
   **88 个文件**提到 `scripts/wp_production`，但**读实现源码的命中为 0**（源码读取已全部走
   `tests/_prod_paths.py::prod_script()`）；其余是子进程调用与 `spec_from_file_location`，
   **当前有意保留**以持续验证兼容层——退休时改成 `_prod_paths` 即可。
2. **交付镜像与 README 与仓库不一致**（§4 前两行）：这是本轮**故意留下**的不一致，
   不是遗漏——不一致的方向是「生成物落后于源」，不是「源与记录互相矛盾」。
3. **`work/` 的本地层没有被清出 Git**：与方案第 6 条的目标相反，因为那批文件是被有意冻结发布的。
4. **收口链未在本机跑通**：环境（`.venv`）不满足，本轮只验证了地址正确性、PS 语法与 50 个 `--check`
   的等价性，未验证 79 步全绿。
5. **站点数据每次改 docs 都要重建**（§5 第 4 条）：这是仓库既有性质，不是本轮引入，但**必须知道**。
