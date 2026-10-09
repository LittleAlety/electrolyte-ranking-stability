# 仓库骨架（repo layout map）

> 用途：给审阅者和新会话一张「目录 → 职责 → 产物落点」的对照图，并说清哪些东西**不可改**。
> 本文档由 `tests/test_repo_layout.py` 强制覆盖：顶层目录、`scripts/` 子包、
> `outputs/physics_completion/` 子包、`outputs/` 非周子目录、新的 `outputs/weekNN/`、
> `src/electrolyte_ranking/` 模块、`data/` 子目录，以及 `docs/NN_*.md` 的编号区间——
> 只要没登记，测试就失败。

## 1. 顶层

| 路径 | 职责 | 是否入交付 |
| --- | --- | --- |
| `config/` | 版本化配置：`scientific_definitions.yaml`（旧定义，冻结）、`physics_completion_v1.yaml`（新阶段 WP0-WP6 的量名 / 样本 / 预算 / 停止规则）、`prereg.yaml` | 是（week37 收录 v1） |
| `data/` | 输入与参考：`anchors/`（氧化锚点及其原始复核）、`metadata/`（样本集）、`references/`、`structures/` | 是 |
| `docs/` | 文档：`NN_*.md` 按编号区间分段（见 §2.2），协议、结论迁移表、结题报告、本骨架图；`docs/assets/` 是终端站点的静态资源 | 是 |
| `outputs/` | 全部产物：`weekNN/` 逐阶段载荷 + `manifest.json`、`physics_completion/` 新阶段、`figures/`、`gate1/`、`state_identity/`、`decision_state/`、`phase2_p1a/`、`smoke/`、`_tools/`、`_weekNN_scratch/` | 是（镜像到仓库外 `成果输出（part2）`） |
| `scripts/` | 入口脚本：顶层扁平入口 + `wp_production/` 生产子包 | 源码；生成器与关键测试随 week44 收录 |
| `src/electrolyte_ranking/` | 可复用库（17 个模块）：`orca`、`xtb`、`qc`、`provenance`、`uncertainty`、`ranking`、`robustness`、`decision_state`、`paper`、`toolchain`、`pc_batch`、`wp2`、`wp3`、`wp4`、`wp5`、`wp6`、`wp7`（`wp2`–`wp7` 属**旧** WP 编号，见 §2.1） | 部分（`pc_batch.py` 随 week44 收录） |
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

### 2.1 两套 WP 编号不是一回事（读者最常混的地方）

仓库里同时存在**两套互不相干**的 WP 编号，代码与文档各按自己那套写，不要互相套用：

| 编号体系 | WP 覆盖 | 落在哪一周 | 代码落点 | 产物 |
| --- | --- | --- | --- | --- |
| **评审实施方案**（旧的，WP1–WP7） | WP1 证据表 / WP2 电子结构响应 / WP3 配位机制 / WP4 决策可辨识性 / WP5 Δ-learning / WP6 主动学习预算 / WP7 外部参照边界 | `outputs/week28..week34`（周报 `docs/50`–`56`） | 可复用原语 `src/electrolyte_ranking/wp2.py` … `wp7.py`（WP1 只出表，没有原语模块） | `outputs/week28..week34/*.csv` |
| **physics_completion_v1**（当前的，WP0–WP6） | WP0 定义迁移 / WP1 独立方法审计 / WP2 配对自由能标签 / WP3 排序证据与机制 / WP4 外部锚点可比性 / WP5 Δ-learning 与主动查询 / WP6 显式配体检查 | `outputs/week37..week43`（周报 `docs/58`–`64`） | 生产链 `scripts/wp_production/`（另有 `src/electrolyte_ranking/pc_batch.py`） | `outputs/physics_completion/**` |

同名不同物：`src/electrolyte_ranking/wp3.py` 是**旧**体系的 WP3，与
`docs/61_week40_wp3_pair_evidence_mechanism.md`（新体系 WP3）没有关系；
`scripts/wp_production/` 里的一切只属于新体系。

### 2.2 `docs/` 编号区间

`docs/NN_*.md` 的两位数字前缀按区间分段，由 `tests/test_repo_layout.py` 强制覆盖：

| 区间 | 内容 |
| --- | --- |
| `00-49` | 早期 stage / week 报告、协议与 QA |
| `50-57` | 评审实施方案 WP1–WP7 与论文收敛（week28–35） |
| `58-64` | physics_completion_v1 WP0–WP6（week37–43） |
| `65-65` | 本骨架图 |

不带数字前缀的文档（`claim_migration.md`、`gate1_negative_result.md`、
`physics_completion_final_report.md`、`physics_completion_protocol.md`、
`state_identity_protocol.md`、`p1v_vs_p1a.md`）是跨阶段的结论 / 协议，不受区间约束。

## 3. `scripts/` 约定

- 顶层扁平 **169** 个入口（166 `*.py` + 3 `*.ps1`），另有 `README.md` 作为逐条索引。
- **不物理搬动**历史脚本：冻结产物与 `manifest.json` 里记录了脚本路径，搬动即破坏可追溯性。
- 命名族：`build_*`（生成器，多数带 `--check`）、`run_*`（执行器 / 队列）、
  `audit_*` 与 `check_*`（审计与校验）、`make_*`（图与提交包）、`freeze_gates.py`（冻结门）。
- 强制索引：新增顶层入口必须登记到 `scripts/README.md`，否则 `tests/test_scripts_index.py` 失败。
- `scripts/wp_production/`：新阶段生产链（26 个跟踪文件），脚本表与边界见 `scripts/wp_production/README.md`。

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
