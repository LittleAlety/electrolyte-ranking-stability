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
- 新阶段批次：`physics_completion/`，其下 17 个子包：
  `active_learning/`、`anchor/`、`closure/`、`compliance/`、`cost/`、`definition/`、`ensembles/`、
  `explicit_ligand/`、`free_states/`、`li_motif_sampling/`、`li_states/`、`method_audit/`、
  `ml/`、`pair_evidence/`、`provenance/`、`sampling/`、`state_identity/`。
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
镜像的周覆盖：**`成果输出（part1）` = week1–week25、`成果输出（part2）` = week28–week44**
（part2 = week28–36 旧阶段 + week37–44 新阶段）；**week26、week27 两段镜像都未覆盖**。

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
- `scripts/wp_production/`：新阶段生产链（**32** 个跟踪文件）；逐脚本职责见 §3.1，一键收口与边界见 `scripts/wp_production/README.md`。

### 3.1 `scripts/wp_production/` 逐脚本职责

新阶段（physics_completion_v1）生产链的每个 `*.py` 一行在这里登记，由 `tests/test_repo_layout.py` 强制覆盖：
该目录下若新增脚本而没写进本表，测试即失败。非 Python 的跟踪文件见本表之后。

| 脚本（`.py`） | 职责 | 主要输入 → 输出 |
| --- | --- | --- |
| `run_wp2_queue.py` | 20 条腿（4 分子 × {`M`,`M_tzvpd`,`M_plus`,`LiM_plus`,`LiM_2plus`}）的幂等队列器：统一调度、并发上限（2 worker × 4 核）、断点续跑、逐次开跑与周期复查 `smpd` | 队列登记表 → `work/wp2prod/**` 现场 + `_queue_<NAME>_<STATE>.out` |
| `run_wp2_production.py` | 生产级 Opt+NumFreq 驱动（`M` / `M_plus` / `LiM_plus` / `LiM_2plus`） | 起始几何 → ORCA 输入/日志/几何（`work/wp2prod/`） |
| `run_wp2_extra.py` | 与带电腿**基组一致**的中性腿 `M_tzvpd`（def2-TZVPD）驱动 | 中性几何 → ORCA 现场（`work/wp2prod/`） |
| `run_batch.py` | 12 主集分子 × 4 主态的 xTB/ORCA 批量驱动与公共工具（几何、ORCA/xTB 路径、片段分析）；`ORCA_CORES` 定义处 | 分子/态清单 → `work/pilot12/**` |
| `run_method_audit.py` | WP1 的 128 单点 / 32 弛豫腿本机方法审计驱动 | 审计清单 → `work/audit/**` |
| `run_pair_recheck.py` | 靶向复核执行器：在已登记的生产 Opt 几何上跑 S3/S4 单点（不重优化、不算频率），串行、每作业 2 核 | 计划表 `job_plan.csv` → 仓库外 `work/recheck/<record_id>/` 现场 |
| `run_to_closure.py` | 队列收尾：把已 computed 的腿折进 production_ledger / 四分子闭环表 / 标签 / week37–44 镜像，未齐的腿留空并显式列出；**折入前先跑关键 pair 第二泛函靶向复核**（重建计划 → 在已登记的生产 Opt 几何上补跑 S3/S4 单点 → 折进 `recheck_results.csv`），腿一落地 ready 行就变多、不补跑则收口链 ABORT；`--check`/`--dry-run`/`--commit`/`--require-complete`/`--skip-recheck` | `work/wp2prod/**` + `work/recheck/**` + 生成器 → 交付层 CSV |
| `supervisor_policy.py` | 监守收敛判据（纯函数，有单测）：`--computed-count` 按队列 `inventory()` 口径数已 computed 的腿，`--decide` 判断继续 / 完成 / 停摆或轮数上限而停 | 队列快照 → `done`/`continue`/`stop_stalled`/`stop_round_cap` |
| `emit_wp2.py` | 把 `work/wp2prod/**` 已跑完的状态**折进生成器**：确定性重打 `WP2_PRODUCTION_LEDGER` 等补丁块 | 生产现场 + 生成器基线 → `scripts/build_physics_completion_batch.py` |
| `emit_wp1.py` | 把 WP1 方法审计矩阵折进生成器（读带 SECTION 标记的 `wp1_audit_src.txt`） | `wp1_audit_src.txt` + 生成器基线 → 生成器补丁块 |
| `emit_pair_recheck.py` | 靶向复核**手工折步**：把 `work/recheck/` 的原始单点折成 `recheck_results.csv`（逐行带几何 sha256）；输入在仓库外，故不进收口链 | `work/recheck/**` → `outputs/physics_completion/pair_evidence/targeted_recheck/recheck_results.csv` |
| `check_wp2_anchors.py` | 复核 `emit_wp2.py` 的补丁锚点在当前生成器基线里唯一存在 | 生成器基线 → 锚点自检结论 |
| `make_commit_msg.py` | 按当前已落地子集生成提交信息 | 交付层状态 → `work/_wp2_commit_msg.txt` |
| `build_compute_provenance.py` | 逐作业复现证据清单 + 从各自 `.log` 推导 `failure_reason`（派生层） | `work/wp2prod/**` + 生产 ledger → `outputs/physics_completion/provenance/**` |
| `build_wp2_closure.py` | 四分子四态闭环 + 翻转持续性 + 逐作业复现证据（派生层） | 生产 ledger → `outputs/physics_completion/closure/**` |
| `build_plan_compliance.py` | 方案 4-14 节逐条合规台账：状态与数字全部从产物现算（四分子闭环 / 方法审计 / 翻转持续性 / 锚点审计 / AL 预算），源码里不写死；作为「都做完没有」的机器可查答案 | 交付层 CSV → `outputs/physics_completion/compliance/**` |
| `build_state_identity_qc.py` | 方案 6.3 态身份 QC：读被 gitignore 的 `work/wp2prod/**` 里原始 ORCA 日志的**最后一段**布居块，现算 fragment charge/spin（Mulliken + Loewdin 双分区，两个分区不一致就记 ambiguous）与 Li 的 Mayer bonded valence；Li-给体**键级**与 Li-给体**接触距离（Angstrom）**分列登记（弱接触低于 ORCA 打印阈值时留空、不补零），按结果前冻结阈值分成 intact / Li_centered / mixed / ambiguous / fragmented / no_li 六张分表；frontier 定位显式登记为 not_computed（派生层） | 原始日志 + production_ledger → `outputs/physics_completion/state_identity/**` |
| `build_anchor_condition_audit.py` | 方案 8(a)/8(c) 锚点条件元数据并表 + 检索协议执行状态：把四组既有锚点源里本就有的条件列（溶剂 / 盐与浓度 / 温度 / 扫描速率 / 误差来源 / 原始标度与数值 / 页码表号 / primary 源状态）并到一张 87 行表，缺的字段留空并写明原因、绝不补 0；同时断言检索协议已登记**且已执行**（executed=true + 执行记录在盘上），本轮新命中可纳入 0 条、按 §6 停止规则保留 external-validity limitation，tier_1 保持 0（派生层） | data/anchors/** + data/references/anchor_retrieval_{protocol,execution}.md → `outputs/physics_completion/anchor/**` |
| `build_wp2_sampling.py` | 气相 GFN2 构象筛选层（派生层） | 生产 ledger → `outputs/physics_completion/sampling/**` |
| `build_wp2_cost_scenarios.py` | 方案 11：按类中位 / p90 与剩余成本低-中-高情景（派生层） | 生产 ledger → `outputs/physics_completion/cost/**` |
| `build_pair_recheck_plan.py` | 方案 5.3 / 11：关键 pair 第二泛函靶向复核的**结果前预注册** + 复核跑完后只读 `recheck_results.csv`、现算逐 (pair, 设定) 的 delta | 规则/对象/设定/几何来源 → `targeted_recheck/` 计划与验收层 |
| `build_li_motif_sampling_plan.py` | 方案 6.1 / 执行第 3 步：四分子 Li 配位 motif 采样的结果前预注册（派生层，零新增计算） | 结构登记 → `outputs/physics_completion/li_motif_sampling/**` |
| `make_physics_completion_figures.py` | 方案 14 的六张主图（F59-F64）与图清单 | 交付层 CSV → `outputs/figures/**` |
| `build_physics_completion_deliverables.py` | 建交付镜像（仓库外 `成果输出（part2）/week37..week44`）：week44 收结题报告、协议、配置、样本、锚点审计、本骨架图、生成器源码、测试与全部 `outputs/physics_completion/**`；`--check` 逐文件复核 byte-identical | 仓库源路径 → 仓库外 part2 镜像 |
| `archive_raw_outputs.py` | 把 provenance 登记的原始作业文件打成**确定性、可复核的 zip 归档**（`--build` 默认落仓库外 `_compute_archive/`；`--check <zip>` 逐条复算 sha256） | `job_archive_manifest.csv` + 仓库外原始日志 → `_compute_archive/*.zip` + `.index.csv` |
| `verify_archive.py` | 归档的**可重新解析性**核验：拿归档原始日志按仓库口径重算登记值，与 manifest 逐字段比对；`--ledger` 再重算交付账本；缺条目/哈希不符/数值不符 → 退出码 1 | `*.zip` + `job_archive_manifest.csv`（+ `production_ledger.csv`） → 核验结论 |

非 Python 的跟踪文件：`finalize_wp2.ps1`（一键收口链）、`supervise_pending.ps1`（无人值守监守）、
`watch_smpd.ps1`（轻量 smpd 看护）、`watch_supervisor.ps1`（监守看护：接住监守 `exit 3` 的信号）、
`wp1_audit_src.txt`（WP1 分段源码）、`README.md`（本目录索引）。
无人值守链的形状是**两个看护 + 一个监守**：`watch_smpd` 兜住 smpd 级联秒败，`watch_supervisor`
在「还有腿没算完、又没有活跃监守」时重新拉起监守，监守跑完队列后调 `run_to_closure.py --commit` 折入交付层。

## 4. 收口链

`scripts/wp_production/finalize_wp2.ps1` 一条命令跑完：

anchors → emit-wp2 → generator → closure → compliance → state-identity → provenance → sampling → li-motif-plan → cost
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

## 7. 复现证据链落点

「派生数字能对回原始作业、且原始作业可被独立重算」这条主张的落点如下。只想要结论就读 CSV/JSON；
想独立取得并重算，走 §7.2、§7.3 的归档 + 核验两步。

### 7.1 入库的派生证据（在仓库内）

- `outputs/physics_completion/provenance/`
  - `job_archive_manifest.csv`：逐作业的原始文件清单与 sha256，以及从原始日志登记的关键值（能量 / 频率 / QC）。
  - `derived_to_job_map.csv`：**派生值 → 作业 ID** 的映射（交付层每个数字该由哪个作业解释）。
  - `provenance_acceptance.csv`：证据链自检（缺文件 / 哈希不符 / 字段缺失）。
  - `provenance_index.json`：上述三者的机器可读索引；`provenance_summary.md` 是人读摘要。
  - `leg_reconciliation.csv`：**四分子 20 条腿的现场核对**——把「清单登记了哪些作业」与 `work/wp2prod/` 的磁盘事实对上；
    `duplicate_work_risk=true` 是唯一告警（磁盘上已有正常结束的原始输出、清单却没有 computed 作业行 = 重复计算的入口）。
    这条把方案第 1 步「提交前先核对正在运行 / 已完成未入库的作业」钉成可复核的检查。
- `outputs/physics_completion/pair_evidence/targeted_recheck/`
  - `recheck_results.csv`：第二泛函（S3/S4）靶向复核**原始层**结果，逐行带几何 sha256。
  - `job_plan.csv`、`selection_rule.json`、`selection_rule.md`：跑之前冻结的预注册层（对象、设定、几何来源、预算、选择规则）。
  - `acceptance.csv`、`recheck_pair_gaps.csv`：复核层验收与缺口登记。
  - 仓库内只有这些派生表，**没有原始 ORCA 输入/日志**。

### 7.2 仓库外的原始现场（不入库）

- 原始现场留在仓库外 `work/`：生产 `work/wp2prod/<NAME>/<STATE>/`、审计 `work/audit/`、
  靶向复核 `work/recheck/<record_id>/`（该 `<record_id>` 即 `recheck_results.csv` 的行标识）。
- `work/` 被 `.gitignore` 忽略，**永不入库**；它在交付里的替身是 §7.3 的确定性归档。

### 7.3 归档与「可重新解析」主张

- `archive_raw_outputs.py --build`：按 `job_archive_manifest.csv` 把登记的原始文件打成**确定性 zip 归档**，
  默认落在仓库外 `_compute_archive/`（附 `.index.csv` + `.README.md`）；`--check <zip>` 逐条复算 sha256。
- `verify_archive.py --archive <zip> --ledger`：这是「归档可被重新解析」主张的核验器——拿归档里的原始日志，
  按**仓库口径**重算登记值，与 `job_archive_manifest.csv` 逐字段比对；`--ledger` 再用同一份归档重算交付账本
  `production_ledger.csv` 的数值列。缺条目 / sha256 不符 / 数值不符 → 退出码 1；`--limit N` 调试、
  `--strict` 把「算不出来」也算失败。
- 语义提示：生产在跑期间归档必然落后于 manifest，`verify_archive.py` 会报「登记晚于归档」的**预期漂移**；
  队列停掉后重建归档再核验才应回到 0 不符。所以「归档能被重新解析」是**可执行、可复算**的断言，不是一句口号。

