# 仓库骨架（repo layout map）

> 用途：给审阅者和新会话一张「目录 → 职责 → 产物落点」的对照图，并说清哪些东西**不可改**。
> 本文档由 `tests/test_repo_layout.py` 强制覆盖：顶层目录、`scripts/` 子包、
> `outputs/physics_completion/` 子包、`outputs/` 非周子目录，或新的 `outputs/weekNN/`
> 只要没登记，测试就失败。

## 1. 顶层

| 路径 | 职责 | 是否入交付 |
| --- | --- | --- |
| `config/` | 版本化配置：`scientific_definitions.yaml`（旧定义，冻结）、`physics_completion_v1.yaml`（新阶段 WP0-WP6 的量名 / 样本 / 预算 / 停止规则）、`prereg.yaml` | 是（week37 收录 v1） |
| `data/` | 输入与参考：`anchors/`（氧化锚点及其原始复核）、`metadata/`（样本集）、`references/`、`structures/` | 是 |
| `docs/` | 文档：`NN_weekNN_*.md` 阶段报告（编号 50-64）、协议、结论迁移表、结题报告、本骨架图；`docs/assets/` 是终端站点的静态资源 | 是 |
| `outputs/` | 全部产物：`weekNN/` 逐阶段载荷 + `manifest.json`、`physics_completion/` 新阶段、`figures/`、`gate1/`、`state_identity/`、`decision_state/`、`phase2_p1a/`、`smoke/`、`_tools/`、`_weekNN_scratch/` | 是（镜像到仓库外 `成果输出（part2）`） |
| `scripts/` | 入口脚本：顶层扁平入口 + `wp_production/` 生产子包 | 源码；生成器与关键测试随 week44 收录 |
| `src/electrolyte_ranking/` | 可复用库：`orca`、`xtb`、`qc`、`provenance`、`uncertainty`、`ranking`、`robustness`、`decision_state`、`paper`、`pc_batch`、`toolchain`、`wp2`-`wp7` | 部分（`pc_batch.py` 随 week44 收录） |
| `structures/` | 起始几何 | 是 |
| `tests/` | pytest 契约：生成器 `--check`、镜像一致性、冻结哈希、脚本索引、骨架覆盖等 | 部分（`test_physics_completion_batch.py` 随 week44 收录） |
| `work/` | 运行期暂存：队列 stdout、生成器基线缓存、监守单实例锁、ORCA scratch | **否**（`.gitignore` 忽略 `work/*`，仅 3 个文件白名单） |

顶层文件：`README.md`（由 `scripts/build_github_readme.py` 确定性生成的逐周日志，**不要手改**）、
`计划.md`（研究计划 v1）、`FINAL_CONCLUSIONS.md`、`pyproject.toml`、
`.gitattributes`（`* text=auto eol=lf`）、`.gitignore`、`.env.example`。

仓库外同级目录：`成果输出（part1）/`、`成果输出（part2）/`（交付镜像）、
`_compute_archive/`（原始作业输出的确定性 zip 归档 + `.index.csv` + `.README.md`）。

### `outputs/` 子目录

- 逐周载荷：`week1` 到 `week43` 的 `weekNN/`，每个目录带自己的 `manifest.json`。
- 特殊命名的周：`week22_hardening/`（W22-H 复核）、`week24_corealign/`（Week 24 主协变对齐）。
- 跨阶段公共产物：`figures/`（含 F59-F64 六张主图）、`gate1/`、`state_identity/`、
  `decision_state/`、`phase2_p1a/`、`smoke/`。
- 新阶段批次：`physics_completion/`，其下 15 个子包：
  `active_learning/`、`anchor/`、`closure/`、`cost/`、`definition/`、`ensembles/`、
  `explicit_ligand/`、`free_states/`、`li_motif_sampling/`、`li_states/`、`method_audit/`、
  `ml/`、`pair_evidence/`、`provenance/`、`sampling/`。
- 历史试算暂存：`_tools/`、`_weekNN_scratch/`（被 `.gitignore` 的 `outputs/_*/` 忽略）。

## 2. 周编号与 WP 的对应

| 阶段 | 周目录 | WP | 说明 |
| --- | --- | --- | --- |
| 计划 v1：代理量 → 决策稳定性 | `outputs/week1..week23` | 早期 stage | 逐周日志见 `README.md` |
| 主协变对齐 | `outputs/week24_corealign` | Week 24 | 目录名不是 `week24/`，是历史命名 |
| 论文 v6 阶段 | `outputs/week25..week35` | Week 25-35 | 其中 `week28..week34` = **评审实施方案 WP1-WP7**（`docs/50`-`56`） |
| 论文 v7 结题 | 仅镜像 `成果输出（part2）/week36` | Week 36 | 仓库内没有 `outputs/week36/`；由 `scripts/build_week36_final_submission.py` 生成 |
| 新阶段：物理证据补强与决策预算 | `outputs/week37..week43` | **WP0-WP6** | week37=WP0 定义迁移、week38=WP1 方法审计、week39=WP2 自由能标签、week40=WP3、week41=WP4 锚点、week42=WP5 ML/AL+成本、week43=WP6 显式配体 |
| 结题提交包 | 仅镜像 `week44` | — | `scripts/wp_production/build_physics_completion_deliverables.py` |

**仓库内没有 `outputs/week24/`、`outputs/week36/`、`outputs/week44/`**：week24 用 `outputs/week24_corealign/`，
week36 与 week44 只存在于 part2 镜像。

## 3. `scripts/` 约定

- 顶层扁平 **169** 个入口（166 `*.py` + 3 `*.ps1`），另有 `README.md` 作为逐条索引。
- **不物理搬动**历史脚本：冻结产物与 `manifest.json` 里记录了脚本路径，搬动即破坏可追溯性。
- 命名族：`build_*`（生成器，多数带 `--check`）、`run_*`（执行器 / 队列）、
  `audit_*` 与 `check_*`（审计与校验）、`make_*`（图与提交包）、`freeze_gates.py`（冻结门）。
- 强制索引：新增顶层入口必须登记到 `scripts/README.md`，否则 `tests/test_scripts_index.py` 失败。
- `scripts/wp_production/`：新阶段生产链（23 个跟踪文件），脚本表与边界见 `scripts/wp_production/README.md`。

## 4. 收口链

`scripts/wp_production/finalize_wp2.ps1` 一条命令跑完：

anchors → emit-wp2 → generator → closure → provenance → sampling → li-motif-plan → cost
→ recheck-plan → figures → mirror → site → freeze → clean-room → 各 `--check` → pytest。

任一步非零即打印 `ABORT`，全绿才打印 `ALL GREEN`。日志重定向到 `work/_chainN.log`
（**不要**用 `Select-Object -First N` 接管道，会掐断链）。加 `-Commit` 才会提交。

## 5. 冻结与不可改

- `outputs/week2/SHA256SUMS`、`outputs/week3/SHA256SUMS`：只覆盖部分文件，**列表内的文件不可改**。
- `outputs/week37..week43` 不允许新增文件（生成器的 `--check` 会报 stray）。
- `outputs/physics_completion/**` 会被 `submission_sources()` 的 rglob 自动收进 week44 镜像。
- `README.md`、`docs/assets/data.js`、`docs/index.html` 是生成物，由生成器的 `--check` 复核。
- `outputs/_*/`（`_tools/`、`_weekNN_scratch/` 等）是历史试算暂存，被 `.gitignore` 忽略。

## 6. 行尾与编码

- `.gitattributes` 声明 `* text=auto eol=lf`：提交时归一化为 LF，检出按 LF。
- 生成器写文本必须显式 `newline=""`：`emit_wp2.py` 曾用默认换行在 Windows 上把生成物
  写成全 CRLF，产生噪声 diff 与告警。
- 工作区里仍有历史遗留的 CRLF 文本文件（多数是早期周次的 `outputs/**` 与 `src/**`）；
  仓库内的索引 blob 已是 LF，git 在下次 touch 时自动归一化，**不要**为统一行尾批量重写，
  否则会改动冻结产物的哈希。
