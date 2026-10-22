# 仓库骨架（repo layout map）

> 用途：给审阅者和新会话一张「目录 → 职责 → 产物落点」的对照图，并说清哪些东西**不可改**。
> 本文档由 `tests/test_repo_layout.py` 强制覆盖：顶层目录、`scripts/` 子包、
> `outputs/physics_completion/` 子包、`outputs/` 非周子目录、新的 `outputs/weekNN/`、
> `src/electrolyte_ranking/` 模块、`data/` 子目录，以及 `docs/NN_*.md` 的编号区间——
> 只要没登记，测试就失败。

## 1. 顶层

新读者先看 [PROJECT_GUIDE.md](PROJECT_GUIDE.md)：权威账本、后续安排、核心实现和网页维护入口。
根 README 与 Pages 当前进度由生成器读取账本；历史周报与当前生产不混为同一验收快照。
发布层将 primary、系综 accepted、前沿解析与身份证据登记分层展示；前沿分母由当前
`production_ensemble_weights.csv` 的成员集推导，并与 `frontier_localization.csv`、
`frontier_identity_evidence.csv` 交叉核对及登记源字节哈希。`verified` 仅是证据表标记，
不是发布生成器独立认证的完整科学身份 QC。下方职责表中的历史计数和“未启动”描述不作为实时队列依据。
[2026-10-22 批次/片段修复记录](hpc_batch2_repair_20261022.md) 保存已授权范围、拒绝任务、非敏感来源哈希与新作业身份；
核心片段旋转/分批映射的回归位于 `tests/test_build_torsion_probe_package.py`，不把预检通过视为新盆地验收。

| 路径 | 职责 | 是否入交付 |
| --- | --- | --- |
| `config/` | 版本化配置：`scientific_definitions.yaml`（旧定义，冻结）、`physics_completion_v1.yaml`（新阶段 WP0-WP6 的量名 / 样本 / 预算 / 停止规则）、`prereg.yaml` | 是（week37 收录 v1） |
| `data/` | 输入与参考：`anchors/`（氧化锚点及其原始复核）、`metadata/`（样本集）、`references/`、`structures/` | 是 |
| `docs/` | 文档：`NN_*.md` 按编号区间分段（见 §2.2），协议、结论迁移表、结题报告、本骨架图；`docs/assets/` 是终端站点的静态资源；站点入口三件在 `docs/` 顶层：`index.html`、`404.html`、`.nojekyll` | 是 |
| `outputs/` | 全部产物：`weekNN/` 逐阶段载荷 + `manifest.json`、`physics_completion/` 新阶段、`figures/`、`gate1/`、`state_identity/`、`decision_state/`、`phase2_p1a/`、`smoke/`、`_tools/`、`_weekNN_scratch/` | 是（镜像到仓库外 `成果输出（part2）`） |
| `scripts/` | 入口脚本：顶层扁平入口 + `wp_production/` 生产子包 | 源码；生成器与关键测试随 week44 收录 |
| `src/electrolyte_ranking/` | 可复用库（17 个模块）：`orca`、`xtb`、`qc`、`provenance`、`uncertainty`、`ranking`、`robustness`、`decision_state`、`paper`、`toolchain`、`pc_batch`、`wp2`、`wp3`、`wp4`、`wp5`、`wp6`、`wp7`（`wp2`–`wp7` 属**旧** WP 编号，见 §2.1） | 部分（`pc_batch.py` 随 week44 收录） |
| `structures/` | 起始几何：`conformers/`（构象池）、`li_motifs/`（Li 配位 motif）、`microsolvation/`（微溶剂化） | 是 |
| `tests/` | pytest 契约：生成器 `--check`、镜像一致性、冻结哈希、脚本索引、骨架覆盖等 | 部分（`test_physics_completion_batch.py` 随 week44 收录） |
| `work/` | 运行期暂存：队列 stdout、生成器基线缓存、监守单实例锁、ORCA scratch | **否**（`.gitignore` 忽略 `work/*`，仅 3 个文件白名单） |
| `deliverables/` | **交付镜像入库副本**：`part1/`（Stage 0–24 / week1–week25）与 `part2/`（评审实施方案 WP1–WP7 + physics_completion_v1 批次），各含 9 类「按成果种类」目录 + `README.md` + `进度说明.md` + `SHA256SUMS_新结构.txt` + 路径映射表。与仓库外 `成果输出（part1）/`、`成果输出（part2）/` 内容一致，入库是为了让 GitHub 上可直接浏览交付件 | 是 |
| `.toolchain/`、`.venv/`、`.mamba/` | 本机工具链与运行环境（**不入库**）：`.toolchain/xtb/xtb-6.7.1/bin/xtb.exe`、`.venv/`（收口链用的解释器）、`.mamba/`；ORCA 在仓库外 `E:\orca_6_1_1\orca.exe`（定位见 `src/electrolyte_ranking/toolchain.py`）。骨架测试按 `startswith(".")` 跳过点目录，因此本行是人读登记 | 否 |

顶层文件：`README.md`（由 `scripts/build_github_readme.py` 确定性生成的逐周日志，**不要手改**）、
`计划.md`（研究计划 v1）、`FINAL_CONCLUSIONS.md`、`pyproject.toml`、
`.gitattributes`（`* text=auto eol=lf`）、`.gitignore`、`.env.example`。

仓库外同级目录：`成果输出（part1）/`、`成果输出（part2）/`（交付镜像；其入库副本见上表 `deliverables/`）、
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
| `66-66` | WP1 生产方法冻结（`66_wp1_production_method_freeze.md`，机器可读件 `config/production_method_freeze_v1.json`） |
| `67-67` | WP1 还原态三项检查协议登记（`67_wp1_reduction_state_check_protocol.md`；判据与缺口先登记、本轮未计算） |

不带数字前缀的文档（`claim_migration.md`、`gate1_negative_result.md`、
`physics_completion_final_report.md`、`physics_completion_protocol.md`、
`state_identity_protocol.md`、`p1v_vs_p1a.md`）是跨阶段的结论 / 协议，不受区间约束。

## 3. `scripts/` 约定

- 顶层扁平 **169** 个入口（166 `*.py` + 3 `*.ps1`），另有 `README.md` 作为逐条索引。
- **不物理搬动**历史脚本：冻结产物与 `manifest.json` 里记录了脚本路径，搬动即破坏可追溯性。
- 命名族：`build_*`（生成器，多数带 `--check`）、`run_*`（执行器 / 队列）、
  `audit_*` 与 `check_*`（审计与校验）、`make_*`（图与提交包）、`freeze_gates.py`（冻结门）。
- 强制索引：新增顶层入口必须登记到 `scripts/README.md`，否则 `tests/test_scripts_index.py` 失败。
- `scripts/wp_production/`：新阶段生产链（**81** 个跟踪文件：75 `*.py` + 4 `*.ps1` + `wp1_audit_src.txt` + `README.md`）；逐脚本职责见 §3.1，一键收口与边界见 `scripts/wp_production/README.md`。

### 3.1 `scripts/wp_production/` 逐脚本职责

新阶段（physics_completion_v1）生产链的每个 `*.py` 一行在这里登记，由 `tests/test_repo_layout.py` 强制覆盖：
该目录下若新增脚本而没写进本表，测试即失败。非 Python 的跟踪文件见本表之后。

| 脚本（`.py`） | 职责 | 主要输入 → 输出 |
| --- | --- | --- |
| `run_wp2_queue.py` | 12 主集分子 × 5 腿 = **60 条腿**（{`M`,`M_tzvpd`,`M_plus`,`LiM_plus`,`LiM_2plus`}）的幂等队列器：统一调度、并发上限（3 worker × 4 核）、断点续跑、逐次开跑与周期复查 `smpd`；覆盖范围与 `physics_completion_set.csv` 的 `in_main=true` 集合由 `tests/test_wp2_queue_scope.py` 钉死 | 队列登记表 → `work/wp2prod/**` 现场 + `_queue_<NAME>_<STATE>.out` |
| `prepare_hpc_main_remaining.py` | 把队列 `missing` 的腿打成**超算任务包**（`tasks/<name>/<state>/` + `job.inp` + `geom.xyz` + `inputs.sha256`，17+18 分批 + `manifest.json` 记源文件 sha256）；只准备，不上传、不提交、不跑 ORCA | 队列 `inventory()` → `work/hpc_main_remaining_17_18/` |
| `submit_hpc_batch.py` | 受控提交已冻结的 HPC 包：提交前核验包清单、任务身份、输入哈希、并发上限与 Slurm 现有占用；提供只读预检，实际提交必须显式启用，防止观察超时造成重复投递 | 冻结任务包 + Slurm 现场 → 单次 `sbatch` 作业号与提交记录 |
| `import_hpc_numfreq.py` | 超算 NumFreq 结果的**只读校验 + 非覆盖导入**：拒收混用梯度（`Restart` 复用位移几何且最大位移 > 2e-6 Å）、源 Opt 未收敛 / 源已有频率、几何身份不符、热化学不完整；虚频结果写 `status=failed` / `qc_flag=imaginary_modes`（**退出码仍为 0，判定要读 status**）；逐文件登记 sha256 且不覆盖内容不同者 | `work/hpc_results/<job>/…` + `work/wp2prod/<name>/<state>/` → `<NAME>_<STATE>.{json,log,_opt.xyz}` + `hpc_import/provenance.json` |
| `import_hpc_opt_numfreq.py` | **自包含 HPC Opt+NumFreq 腿**的只读校验 + 非覆盖导入：默认只收冻结输入；仅 `--start-level continued_from_unconverged_opt_frame` 可额外带唯一且精确的 `%geom MaxIter 200 end`，其他值、重复行、其他来源或额外 directive 全部 fail-closed，原始输入仍参与 sha256 与逐行回显。另校验正常终止 + 优化收敛、无频率重启、起点/终点几何、3N 有限频率、完整热化学与收敛几何电子能；虚频记 `status=failed`，任务包哈希/manifest 不符即拒收 | 包内 `tasks/<NAME>/<STATE>/run/{job.log,job.xyz,job.inp,geom.xyz}` → `work/wp2prod/<name>/<state>/<NAME>_<STATE>.{json,log,opt.xyz,inp}` + `hpc_import/provenance.json` |
| `reopt_saddle.py` | 收敛到**鞍点**（虚频）的生产腿的**可复现逃逸**：解析该腿日志 NORMAL MODES 的虚频位移向量 → 把收敛几何沿它位移（最大单原子位移 = `--amplitude`，默认 0.20 Å）→ 写出扰动起点 + JSON（模式号/频率/符号/幅度/源日志与 opt.xyz 的 sha256/最大位移原子/方案 §6.3 原文）；**先校验该模式确为虚频**，否则拒收；`--leg-dir` 可指向 `work/wp2prod/_saddle_attempt1/` 冻结现场以复现历史输入；`--run` 才起本机 ORCA（超算路线：扰动几何打包 → `import_hpc_opt_numfreq.py` 导入） | 腿 `work/wp2prod/<NAME>/<STATE>/{<NAME>_<STATE>.log,_opt.xyz}` → `work/wp2prod/_reopt/<NAME>_<STATE>_perturbed_s<±>_a<amp>.{xyz,json}` |
| `fold_anfreq_into_ledger.py` | **协议 v1.3 折入器**：把全 cohort 的 `AnFreq`（解析 Hessian）结果写回生产账本。每条腿取**自己冻结收敛几何**上的 AnFreq 日志（无 Opt，几何不得移动），复用生产同一个 `run_wp2_production` 解析器读热化学，重算虚频并改写 `level`（只写实际关键字）、`frequency_hessian`、`protocol_version`；**仍带虚频的腿写 `status=failed`**，绝不冒充可验收；旧 NumFreq 行连同日志存 `superseded_numfreq/`（v1.2 ④：两种 Hessian 算法不得静默混用）；**幂等**——目标态标志检查（`protocol_version==1.3` 且 `frequency_hessian==analytical_hessian` 时直接跳过整轮折入）+ **快照 first-copy-wins**（`superseded_numfreq/*.json`/`*.log`、`pre_rescue.json` 三处均只写一次，永不覆盖首份快照），防止二次运行或重导 NumFreq 行后二次折入静默销毁敏感性证据；默认预览、`--apply` 才写；另有 `--rescue-leg` 模式接管「救援收敛几何上的 AnFreq 频率单点」（非 Opt+freq、非 continuation 的第三形态，如 TMP/LiM_plus c04，stage 进 `anfreq_rescue/`、旧 failed 行存 `pre_rescue.json`，同样 first-copy-wins）；回归测试 `tests/test_fold_anfreq_into_ledger.py`（4 条：折两遍快照不变、重导 NumFreq 后二次折入快照仍为原件、救援两遍 pre_rescue 不变、同 rescue 日志幂等跳过） | `work/hpc_anfreq_cohort_20261016/{local_runs,hpc_runs}/<MOL>_<STATE>/job.log` → `work/wp2prod/<NAME>/<STATE>/<NAME>_<STATE>.json` + `superseded_numfreq/` + `anfreq_rescue/` |
| `build_production_ensemble_manifest.py` | **生产级 48 态系综候选清单 + HPC 分块包生成器**（方案 §6.1/§6.2）：primary（含中性 M 槽→M_tzvpd 映射）+ 池合并 → 6 kcal/mol 窗口 → 连接/Li 齿数/重原子 RMSD(0.35Å) 去重 → 每态≤3 含 primary；新结构一律冻结 v1.3 语法（Opt VeryTightOpt AnFreq def2-TZVPD）；`--build-packages work --chunk 18` 产出≤18 元素分块包；round2（3→6 审计）候选只登记不开包；扭转级去重推迟到 DFT 后 | 冻结池 + `work/wp2prod/**` → `outputs/physics_completion/ensembles/production_ensemble_{candidates.csv,manifest.json}` + `work/hpc_production_ensemble_r1_*/` |
| `import_ensemble_structures.py` | **系综结构专用导入器（primary 账本防火墙）**：只读 `work/wp2prod`，唯一写入 `production_ensemble_structures.csv`；逐结构九查（sha256/AnFreq 关键字/正常终止/VeryTight 五阈值/charge-mult/3N 频率+零虚频/G 恒等式/连接不变/Li 齿数与片段）+ Hessian 帧不变量几何联动；四态语义（pending/technical_complete_qc_failed+failure_class/computed/superseded）；`--fetch` 取回（含远端字节 sha）、`--build-reopt`（仅 strict_reopt_required，含 package manifest）、`--build-continuation`（max-cycles 独立续算，轨迹最低能帧+MaxIter 200）；`--build-r2-followup`（round-2 审计腿跟随：严格重优化 / 续算 `%geom MaxIter 200` / 技术重试，成员保留 `round2_audit_extra`，包名递增 `r2_reopt<N>`）、`--build-li-round2-legs`（第二轮 Li 新盆地 → 生产腿，只打包实测新盆地并逐字节核验起点） | `work/hpc_production_ensemble_r1_*/tasks/**` → `outputs/physics_completion/ensembles/production_ensemble_structures.csv` |
| `ensemble_hpc_io.py` | 经受策略保护的 WHU HPC 命令桥核验终态 Slurm 作业，逐文件远端/本地 SHA256 对账后保存不可变快照、收据与来源指针；不在本机运行 ORCA/xtB，也不把技术完成当 QC 通过 | 远端数组任务 `run` / `attempts` → `work/hpc_production_ensemble_r1_*/tasks/**/snapshots/**` |
| `build_production_ensemble_aggregator.py` | **生产级 48 态系综聚合器**：只读 QC 结构账本；每 molecule×slot 只收 computed 成员、primary 恒在（N=1 记 pool_limited）；DFT 后去重（连接/Li 齿数/RMSD 0.35Å/扭转）；log-sum-exp 数值稳定实现 G_ensemble 公式（298.15K、gᵢ=1、温度一致、权重和=1）；输出权重表/去重表/48 行标签/索引（含输入哈希与 stale 检测） | `production_ensemble_structures.csv` → `production_ensemble_{weights,dedup,labels}.csv` + `production_ensemble_index.json` |
| `build_sampling_audit_3to6.py` | **3→6 采样审计计划**（§6.1/v1.4 §5.2）：四审计分子×四主态逐态统计池内 6 kcal/mol 窗口的独立极小真实数，判定 `executable` / `executable_partial` / `sampling_limited`；不足 6 只登记真实上限不凑数；Li 态标记需第二轮 motif 搜索；产出 CSV+MD+索引，`--check` 只读 | 冻结池 + 结构账本 → `sampling/sampling_audit_3to6.csv` + `.md` + `sampling_audit_index.json` |
| `build_tolerance_preregistration.py` | 采样容差预注册稿：三条候选依据 + 所需证据，不选数值（由用户裁决）；当前差异仅作参考 | `sampling/tolerance_preregistration_draft.md` |
| `build_sampling_ceiling_classification.py` | ceiling 缺口四分类（容差未冻结，只描述差异；跨账本矛盾 WARNING） | `sampling/sampling_ceiling_classification.{csv,md}` |
| `build_sampling_3to6_diff.py` | **3→6 采样差异报告**（§6.1 / v1.4.2 第 4 条；按用户 2026-10-19 决定**只报差异、不判采样收敛**）：预注册四审计分子×四主态的比较量与口径（`G_ensemble`、氧化轴 `G(M_plus)−G(M)`、Li 条件轴 `G(LiM_2plus)−G(LiM_plus)`、审计集 Top-k 与 selection regret，主 k=2、辅助 k=1/3——审计集只有 4 个分子），round-1 侧从生产系综标签填，ceiling 侧在无生产 DFT 腿时**留空并写原因（绝不补零）**；GFN2 1.00 kcal/mol 只作筛选阈值；产出 CSV×3 + MD + 索引，`--check` 只读 | `ensembles/production_ensemble_labels.csv` + `sampling/sampling_audit_3to6.csv` + `ensembles/production_ensemble_manifest.json` → `sampling/sampling_3to6_diff{,_axes,_selection}.csv` + `.md` + `sampling_3to6_diff_index.json` |
| `run_wp2_production.py` | 生产级 Opt+NumFreq 驱动（`M` / `M_plus` / `LiM_plus` / `LiM_2plus`） | 起始几何 → ORCA 输入/日志/几何（`work/wp2prod/`） |
| `run_wp2_extra.py` | 与带电腿**基组一致**的中性腿 `M_tzvpd`（def2-TZVPD）驱动 | 中性几何 → ORCA 现场（`work/wp2prod/`） |
| `run_batch.py` | 12 主集分子 × 4 主态的 xTB/ORCA 批量驱动与公共工具（几何、ORCA/xTB 路径、片段分析）；`ORCA_CORES` 定义处 | 分子/态清单 → `work/pilot12/**` |
| `run_method_audit.py` | WP1 的 128 单点 / 32 弛豫腿本机方法审计驱动 | 审计清单 → `work/audit/**` |
| `run_pair_recheck.py` | 靶向复核执行器：在已登记的生产 Opt 几何上跑 S3/S4 单点（不重优化、不算频率），串行、每作业 2 核 | 计划表 `job_plan.csv` → 仓库外 `work/recheck/<record_id>/` 现场 |
| `run_to_closure.py` | 队列收尾：把已 computed 的腿折进 production_ledger / 四分子闭环表 / 标签 / week37–44 镜像，未齐的腿留空并显式列出；**折入前先跑关键 pair 第二泛函靶向复核**（重建计划 → 在已登记的生产 Opt 几何上补跑 S3/S4 单点 → 折进 `recheck_results.csv`），腿一落地 ready 行就变多、不补跑则收口链 ABORT；`--check`/`--dry-run`/`--commit`/`--require-complete`/`--skip-recheck` | `work/wp2prod/**` + `work/recheck/**` + 生成器 → 交付层 CSV |
| `supervisor_policy.py` | 监守收敛判据（纯函数，有单测）：`--computed-count` 按队列 `inventory()` 口径数已 computed 的腿，`--decide` 判断继续 / 完成 / 停摆或轮数上限而停 | 队列快照 → `done`/`continue`/`stop_stalled`/`stop_round_cap` |
| `emit_wp2.py` | 把 `work/wp2prod/**` 已跑完的状态**折进生成器**：确定性重打 `WP2_PRODUCTION_LEDGER` 等补丁块 | 生产现场 + 生成器基线 → `scripts/build_physics_completion_batch.py` |
| `wp2_progress.py` | 只读 12×5 现场 payload 与固化 production ledger，分离 runtime computed、四主态严格科学验收与固化交付；生成聚合 sha256 与 stale 判定 | `work/wp2prod/**` + production ledger → 内存快照（供 compliance 使用） |
| `orca_derivative_policy.py` | 机器强制的 ORCA 导数策略（纯函数，有单测）：禁止 `NumGrad`（数值一阶导），保留冻结协议里的 `NumFreq`（在支持的 DFT 方法上由解析梯度构造数值 Hessian）；`AnFreq` 属独立的二阶导/协议变更，需显式记录兼容性研究；另校验优化收敛层级（normal/tight/verytight）与 verytight 阈值 | ORCA 输入文本 → 通过/拒收结论（fail-closed） |
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
| `build_descriptor_analysis.py` | 方案 §7.3 描述符层（派生层，零新增计算）：donor type / chelation / flexibility / functionalization / 廉价 ESP 报**全部**检验（含不显著），Holm 与 BH 并列，TPSA 仅探索性；n=12 不拟合多参数模型 | 冻结产物 → `outputs/physics_completion/pair_evidence/descriptor_analysis.{csv,md}` |
| `build_li_motif_sampling_plan.py` | 方案 6.1 / 执行第 3 步：四分子 Li 配位 motif 采样的结果前预注册（派生层，零新增计算） | 结构登记 → `outputs/physics_completion/li_motif_sampling/**` |
| `build_li_motif_plan_round2.py` | **第二轮 Li motif 搜索预注册**（v1.4.2 项 5）：第一轮已对单一父几何穷举全部配位规则，8 个审计 Li 态仍只 1–2 个独立极小；第二轮空间＝同一冻结规则 × **冻结自由态构象池的其他中性盆地做替代父几何**（EMC 2/DEC 4/DME 6/TMP 3 盆地，sha256 磁盘核验）；登记 round-1 kept + 已核验父数＝诚实上界（去重可能合并，真实数只能执行后测）；零新增计算，执行为显式独立步骤 | 冻结池 + 第一轮 screen → `li_motif_sampling/li_motif_plan_round2.{csv,_index.json}` |
| `build_frontier_identity_evidence.py` | **身份证据链装配（v3.1 第 2 项）**：每成员验证同一次执行的input/log/geometry/molden 四文件存在且记原始哈希；方法(wB97X-D4/def2-TZVPD)/SCF(TightSCF)/正常终止/电荷多重度与登记一致；自旋通道与声明波函数一致 → identity_qc_status=pending→verified；缺本地文件记 awaiting（不等于需重算） | `frontier/frontier_identity_evidence.csv` + `_index.json` |
| `build_torsion_probe_package.py` | **片段扭转与分批修复**：核实中心单键，只旋转其一侧共价片段；全原子拓扑保持等价映射 + proper Kabsch 拒绝刚体/对称等价。每批独立清单、任务分区无重复无缺失；修复包只纳入获批原候选，双键拒绝不替补。旧 11 起点不计独立新构象证据 | [修复记录](hpc_batch2_repair_20261022.md)；新 Job 3748336；`tests/test_build_torsion_probe_package.py` |
| `build_torsion_registry.py` | **扭转自由度登记表（v3.1 第 4 项预检）**：从生产几何按共价半径邻接推导键/二面角；可旋转判据＝B-C 键不在 ≤7 元环内（环变形须另行登记，不等同扭转）；每条登记带源几何哈希。实测：AN 3 / DMC 10 / DMC_Li 12 / **DOL 0（五元环全刚性）** / EC 2 | `recovery/torsion_freedom_registry.csv` + `_index.json` |
| `build_probe_routes.py` | **五态实测路由（v3.1 第 4 项的派生输出）**：probe_route 的六输入全部从数据推导（primary 登记行不算在途）；当前五态全部 preflight_required（池内无未用构象、无新独立 motif、无扭转自由度登记表）——下一步是候选/身份/对称去重/起点哈希预检，不是直接提交计算 | `recovery/probe_routes.csv` + `_index.json` |
| `probe_route.py` | **五态逐态路由（v3.1 第 4 项，草案 B）**：在途→等待；身份未验→先验身份；预检三要素 None→preflight_required；优先级 unused_starts > new_li_motifs > eligible_torsions > independent_reproductions；全零→limited_no_registered_executable_probe（零=本次预检范围内无可执行候选，**不表示物理上不存在其他极小**） | 库模块（draft_* 仍须登记候选预算授权） |
| `wp5_formal_models.py` | **WP5 正式预测器（计划 v3.1 第 5 项）**：ridge_std（闭式解、仅可见行标准化）、krr_rbf（RBF 核岭回归）、gpr_rbf（GP 后验均值）三个**真实可执行**模型；超参冻结（gamma=1/7、lambda=1e-3、noise=1e-2，无逐回放调参）；纯函数——只见 (features, visible, labels)，无偷看；model_contract() 记录实际执行的模型/特征/可见集。替代旧的 kNN 邻近均值口径（邻近均值不再冒充模型契约） | 库模块；契约记入回放产物 |
| `frontier_spin_qc.py` | **同自旋同轨道的正式 FMO 解析（计划 v3.1 草案 A）**：`formal_frontiers(log, symbols, wavefunction)` 按声明的波函数（R→单通道，U→alpha+beta）逐自旋通道输出 operator/spin/orbital_index + Li/给体 Löwdin 权重；原子组成/顺序与成员几何交叉核对；非物理逐原子权重拒绝（列和校验之上）；重复 FMO 块、缺通道、RO 未契约一律 raise | `frontier/frontier_spin_records.csv`（244 条自旋记录） |
| `frontier_fmopop.py` | **ORCA `! FMOPop` 输出解析器**（Mulliken+Löwdin 双口径前沿布居）：解析每 operator 块（UHF 有 OP=0/1 两块）的原子行（`0-C 0.207071 0.189913 ...` 四列＝HOMO/LUMO 的 Mulliken/Loewdin），强制校验每列布居和≈1、块必须以闭合线结束、缺 operator 即 raise（fail-closed，绝不产出部分权重表）。`frontier_populations()` 输出 Li/给体的四列正式布居 | 库模块；产物列在 frontier_localization.csv |
| `frontier_lowdin.py` | **Löwdin 轨道原子权重**（按计划算法）：从 AO 重叠矩阵做对称正交化，population=|S^(1/2)c|^2 后按原子求和；强制校验 AO 维度一致性/原子映射/有限性/Hermitian/正定谱/MO 归一化/布居和为 1，任何违反直接 raise（不静默回退到 |c|² 捷径） | 库模块 |
| `build_bgroup_pilot_preregistration.py` | **B组试点预注册（未启动）**：AN/DMC 的 M_plus生产级覆盖诊断——方法结论由冻结池数据**自动推导**（两态池内构象已全部上过生产级 → 直接 DFT 多起点无候选 → 应改走相关扭转扫描，须另行登记）；停止条件冻结（每态≤2腿、双塌缩→production_single_basin生产级单盆地证据、不自动扩态）；预算 ~48 core-hours | `recovery/bgroup_pilot_preregistration.md` + `_index.json` |
| `build_recovery_budget_accounting.py` | **恢复包预算核算与终局报告**：按包实测 core-hours（从验证快照的 started/normal_termination 时间戳推、4 核/腿）、主账本合计、9 个 limited 态的终局原因分组（历史保留）、下一轮授权须知（预算余量、漂移态不可再算、预算尽态需另立版本） | `recovery/recovery_budget_accounting.md` + `_index.json` |
| `strict_readiness.py` + `strict_readiness_wiring.py` | **严格总闸门（逐项证据检查）**：`strict_readiness(labels, expected_keys, checks)` 按计划实现——不只数 48 个标签，而是检查六项必需要求（覆盖复核有效/电子身份全成员完整/采样审计完成/WP3 证据完整/WP5 全池评估/成本溯源完整）＋WP6 与扩样"触发后才检查"的条件；返回 `{complete, blocked_by}`，把缺口逐项列出而非一个布尔。wiring 层从磁盘产物**机械推导**每个布尔（缺失/不可解析/不完整一律 False，fail-closed），不接收任何手设标志 | 不写文件（库模块；wiring 打印 JSON） |
| `run_second_search_emc.py` | **已执行的第二轮换方法搜索（仅 EMC\|M_plus）**：GFN2-xTB + ALPB(乙腈)、256 个 ETKDGv3 起点（首轮 64）、seed 20261022，`--opt tight`。预注册四要素写在模块文档里（方法改动轴、成本上限、停止规则、不回填旧池）。**结论：真新盆地 0**（两条与已有极小 RMSD 0.0102 / 0.1181）→ `search_method_exhausted`；且该态真实限制是 `species_drift_unrecoverable`（键图改变），换方法本就无效 | `recovery/strict_recovery_v2_emc_pool.csv` + `_index.json` |
| `build_strict_recovery_report.py` | **恢复批次结果报告（只报告不改判）**：逐态列出系综状态、覆盖复核 verdict、搜索结论、注册起点数、每条恢复腿的**已用/允许尝试次数**与终局状态；另列「本轮无法恢复的态」与「尝试预算已用尽的腿（保留原因，不再自动重试）」。明确不把失败改写成通过、不清空 n_limited、不放宽阈值 | `recovery/strict_recovery_v1_report.md` + `_index.json` |
| `build_second_search_preregistration.py` | 第二轮搜索方法预注册稿：本批恢复不了的 6 态 + 候选方法变更 + 预注册四要素（不选方法） | `recovery/second_search_preregistration_draft.md` |
| `build_strict_recovery_manifest.py` | strict_recovery_v1 恢复批次登记：14 态、≤2 起点/态、28 腿上限、实测成本依据、停止条件；盆地双拼写规范化 | `recovery/strict_recovery_v1_manifest.{csv,md}` |
| `build_frontier_localization.py` | frontier 定域分析：解析 Molden 出 HOMO/LUMO 组成与 frontier_class（阈值先冻结）；缺文件/解析失败如实登记 | `frontier/frontier_localization.csv` |
| `build_frontier_legs.py` | frontier/电子身份腿清单：73 个计入系综成员、几何按 final_geometry_sha256 精确匹配、单点+Molden 输出（分析独立成步） | `frontier/frontier_legs.csv` |
| `run_strict_recovery_search.py` | 恢复批次独立盆地搜索（本地 GFN2 筛选，Kabsch RMSD 去重，零结果也登记） | `recovery/strict_recovery_v1_search_pool.csv` |
| `build_coverage_reviews.py` | 覆盖复核：limited→accepted 的唯一证据通道（派生 verdict，不重写历史失败，不清空 n_limited） | `recovery/coverage_reviews.csv` |
| `build_d6_preregistration_draft.py` | D6 预注册稿（草案）：四敏感态 Top-3 威胁、预注册四要素、默认限制报告分支；index 确定性 | `ensembles/d6_ranking_sensitive_preregistration_draft.{md,_index.json}` |
| `run_wp5_AB_replay.py` | WP5 A/B 验收回放：12 分子池四策略配对种子、16/20 停止预算、实测成本台账（B 携带 free 成本） | `active_learning/blind_replay/AB_*` |
| `build_wp5_target_pool.py` | WP5 A/B 验收目标池：最终 labels 派生的 12+12 行 free 氧化 / Li 条件移位目标，带 acceptance provenance；与 legacy demo 池分开 | `active_learning/blind_replay/target_pool_AB.{csv,_index.json}` |
| `wp5_replay_contract.py` | WP5 盲回放 v2 契约：sha256 稳定种子、配对初始集、16/20 逐点停止预算（排除耗尽池平凡解）、描述统计与停止预算分离 | 被 run_wp5_blind_replay.py 导入，无独立输出 |
| `run_wp5_blind_replay.py` | WP5 候选级盲回放：Acquirer 无完整标签（结构性盲）、精确 k=3 端点取池耗尽前一轮、逐候选预测落盘、ASSUMED_CONSTANT 成本口径 | `active_learning/blind_replay/*` |
| `build_gap_decision_support.py` | 14 个非 accepted 系综态的缺口决策证据：成员处置分布、**未用盆地**（池 relpath leaf 规范化 `r2_c13`/`c03`→`13`/`3` 与账本 basin 集合差，绝不硬编码）、RT ln(N_new/N_unique) 额外 bound、氧化轴 Top-3 排序敏感性、四档建议；不判收敛 | `ensembles/remaining_gaps_decision_support.{csv,md,_index.json}` |
| `member_next_action.py` | 成员下一步处置的冻结判定契约（纯函数）：漂移凌驾一切且不可续算；技术故障不扣预算；预算按去重 (attempt, log) 对计数、两次即 limited；strict/verytight → 从自身收敛末几何重优化一次；max_cycles → 身份门后续算；导入器处置表由此派生。测试 10 项钉死三分支 | 被导入器导入，无独立输出 |
| `run_li_motif_round2.py` | **第二轮 Li motif 搜索执行器**（v1.4.2 项 7 科学侧）：读预注册的第二轮计划，对每个磁盘哈希与登记值一致的中性 M 盆地做替代父几何（不一致 `parent_hash_stale` fail-closed，绝不换父或造结构），沿用冻结的枚举规则与保留规则（25 kJ/mol、同类重原子 RMSD 0.35 Å、每腿 ≤3）；每个保留 motif 与 round-1 保留结构逐对比，只有真不同的极小计入 `new_independent_basins`，给出**实测上限**（登记上限为启发式上界，不改动）；`--check` 复核 CSV/motif/父体/计划四层哈希（计划重建后旧执行记录判 STALE） | `li_motif_plan_round2.csv` + 冻结池 + round-1 screen → `li_motif_sampling/li_motif_round2_exec.{csv,md,_index.json}`、`work/limotif_r2/**` |
| `screen_li_motifs.py` | 方案 6.1 / 执行第 3 步的**执行器**：复用 `build_li_motifs.py` 里冻结的枚举规则（给体识别 / 单齿 / 双齿 / ESP 补点），按每条腿自己的电荷与多重度跑气相 GFN2-xTB 筛选、按配位模式 + 重原子 RMSD 去重、每腿保留最多 3 个独立 motif；`--check` 核对落盘 CSV 与运行记录同版、父几何未被重跑 | 各腿自己的生产几何（去 Li 后作为父结构）+ `work/limotif/**` → `outputs/physics_completion/li_motif_sampling/li_motif_screen.{csv,json,md}` |
| `make_physics_completion_figures.py` | 方案 14 的六张主图（F59-F64）与图清单 | 交付层 CSV → `outputs/figures/**` |
| `build_physics_completion_deliverables.py` | 建交付镜像（仓库外 `成果输出（part2）/week37..week44`）：week44 收结题报告、协议、配置、样本、锚点审计、本骨架图、生成器源码、测试与全部 `outputs/physics_completion/**`；`--check` 逐文件复核 byte-identical | 仓库源路径 → 仓库外 part2 镜像 |
| `archive_raw_outputs.py` | 把 provenance 登记的原始作业文件打成**确定性、可复核的 zip 归档**（`--build` 默认落仓库外 `_compute_archive/`；`--check <zip>` 逐条复算 sha256）；并把当次 manifest 内嵌成 `_manifest/job_archive_manifest.csv`，让「这份 zip 对应哪一版登记表」自证、过期可判 | `job_archive_manifest.csv` + 仓库外原始日志 → `_compute_archive/*.zip` + `.index.csv` + `.README.md` |
| `build_wp2_ensemble_free_energies.py` | 方案 6.1 第 3 步 / 6.2：把两个**已登记**的筛选池（自由态构象池 + Li motif 池）在 xTB GFN2 `--ohess` 自由能层面折成 Boltzmann 系综（`G_state = -RT ln Q` 与布居平均 `G_avg` 两种口径并列、不互换），并给 EMC-GBL / EMC-SL 两对输出「同分子氧化轴」的四层配对台（`free_ionisation` 与 `Li_conditioned`）；虚频结构留行并排除出系综。**是筛选层不是生产 R4**，状态一律 `computed_screen_only` | 两登记池 + gitignore 的 `work/enso/**` → `outputs/physics_completion/ensembles/**` |
| `verify_archive.py` | 归档的**可重新解析性**核验：拿归档原始日志按仓库口径重算登记值，与 manifest 逐字段比对；`--ledger` 再重算交付账本；`--latest` 自动取最新归档并先打一行 `[freshness]`（内嵌登记表是否与仓库当前那份同版）；`--gate-when-complete` 是收口链里的**结题门禁**（只在 20/20 时先重建归档再要求同版 + 0 不符，没跑完时只提示）；缺条目/哈希不符/数值不符 → 退出码 1 | `*.zip` + `job_archive_manifest.csv`（+ `production_ledger.csv`） → 核验结论 |

非 Python 的跟踪文件：`finalize_wp2.ps1`（一键收口链）、`supervise_pending.ps1`（无人值守监守）、
`watch_smpd.ps1`（轻量 smpd 看护）、`watch_supervisor.ps1`（监守看护：接住监守 `exit 3` 的信号）、
`wp1_audit_src.txt`（WP1 分段源码）、`README.md`（本目录索引）。
无人值守链的形状是**两个看护 + 一个监守**：`watch_smpd` 兜住 smpd 级联秒败，`watch_supervisor`
在「还有腿没算完、又没有活跃监守」时重新拉起监守，监守跑完队列后调 `run_to_closure.py --commit` 折入交付层。

**收口链只覆盖上表的一部分**：`finalize_wp2.ps1` 的步骤是 `emit_wp2.py` / `build_compute_provenance.py` / `build_state_identity_qc.py` / `build_anchor_condition_audit.py` / `build_wp2_sampling.py` / `build_li_motif_sampling_plan.py` / `build_wp2_ensemble_free_energies.py` / `build_wp2_closure.py` / `build_plan_compliance.py` / `build_wp2_cost_scenarios.py` / `build_pair_recheck_plan.py` / `make_physics_completion_figures.py` / `build_physics_completion_deliverables.py` / `verify_archive.py`。其余（`run_wp2_queue.py`、`run_wp2_production.py`、`run_wp2_extra.py`、`run_batch.py`、`run_method_audit.py`、`run_pair_recheck.py`、`emit_pair_recheck.py`、`archive_raw_outputs.py`、`screen_li_motifs.py`）**不是** `finalize_wp2.ps1` 的步骤，由无人值守链（`supervise_pending.ps1` → `run_to_closure.py`）或人工触发。

## 4. 收口链

`scripts/wp_production/finalize_wp2.ps1` 一条命令跑完：

anchors → emit-wp2 → generator → provenance → state-identity → anchor-condition → sampling → li-motif-plan → ensemble → closure → cost
→ recheck-plan → compliance → figures → mirror → site → freeze → clean-room → archive-verify → 各 `--check` → pytest。

`cost` / `recheck-plan` **必须**排在 `compliance` 之前：`build_plan_compliance.py` 的 §11 条目读
`cost/cost_scenario_acceptance.csv` + `cost/cost_scenario_index.json`，§5.1 条目读
`pair_evidence/targeted_recheck/job_plan.csv` + `recheck_results.csv`。顺序反了，它会读上一轮的状态，
同一轮里的 `--check` 就会报 `differs`（2026-10-11 四分子 20/20 时暴露）。

任一步非零即打印 `ABORT`，全绿才打印 `ALL GREEN`。日志重定向到 `work/_chainN.log`
（**不要**用 `Select-Object -First N` 接管道，会掐断链）。加 `-Commit` 才会提交。

> **折入前置（并发纪律）**：无人值守链收尾的 `run_to_closure.py` 在跑 `finalize_wp2.ps1` **之前**，先执行关键 pair 第二泛函靶向复核（`build_pair_recheck_plan.py` → `run_pair_recheck.py` → `emit_pair_recheck.py`），其中 `run_pair_recheck.py` **会起 ORCA**。因此折入只能在**没有任何 `orca.exe` 在跑**时执行，否则会与生产腿叠加、顶破「全机 2 个 ORCA 作业（各 4 核）」的上限；`finalize_wp2.ps1` 本身不含 ORCA 步骤。

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
  - `baseline_artifact_manifest.csv`：以方案基线提交 `d5217a1f` 的 **Git 对象**为时间边界，对当时已有关键派生产物逐字节计算
    sha256（不读今天的工作树冒充历史）；范围是根/配置/元数据关键文件与 gate1、phase2_p1a、week4-week7 的直属文件，
    嵌套原始作业树不在内。Git 对象取不到时只写 `unverifiable`，不猜哈希。
  - `derived_to_job_map.csv`：**派生值 → 作业 ID** 的映射（交付层每个数字该由哪个作业解释）。
  - `provenance_acceptance.csv`：证据链自检（缺文件 / 哈希不符 / 字段缺失）。
  - `provenance_index.json`：上述三者的机器可读索引；`provenance_summary.md` 是人读摘要。
  - `leg_reconciliation.csv`：**四分子 20 条腿的现场核对**——把「清单登记了哪些作业」与 `work/wp2prod/` 的磁盘事实对上；
    `duplicate_work_risk=true` 是唯一告警（磁盘上已有正常结束的原始输出、清单却没有 computed 作业行 = 重复计算的入口）。
    这条把方案第 1 步「提交前先核对正在运行 / 已完成未入库的作业」钉成可复核的检查。 **扫描范围提醒**：该表只扫 `work/wp2prod/<名>/<态>/`，对 `work/pilot/`、`work/pilot12/`、`work/audit/`、`work/recheck/` 里的同名单点**完全盲区**；`duplicate_work_risk=false` 只表示「wp2prod 现场内没有重复」，不等于「全机没有可复用的既有输出」。
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
  归档里**内嵌了建它时的那份 `_manifest/job_archive_manifest.csv`**：这份 zip 对应哪一版登记表由它自证，
  不靠猜（README 同时印出该登记表的 sha256 与行数）。
- `verify_archive.py --latest --ledger`：这是「归档可被重新解析」主张的核验器——拿归档里的原始日志，
  按**仓库口径**重算登记值，与 `job_archive_manifest.csv` 逐字段比对；`--ledger` 再用同一份归档重算交付账本
  `production_ledger.csv` 的数值列。缺条目 / sha256 不符 / 数值不符 → 退出码 1；`--limit N` 调试、
  `--strict` 把「算不出来」也算失败。开头先打一行 `[freshness]`：内嵌登记表与仓库当前那份同版即「新鲜」，
  不同版即「过期」。
- `--gate-when-complete` 是**结题门禁**（已进收口链）：只在队列 20/20 全 computed 时才动手——先重建归档，
  再要求它与当前登记表同版且逐字段核验 0 不符；队列没跑完时只打印一行提示、不算失败。
- 语义提示：生产在跑期间归档必然落后于 manifest，`verify_archive.py` 会报「登记晚于归档」的**预期漂移**；
  队列停掉后重建归档再核验才应回到 0 不符。所以门禁只在 20/20 时生效，针对的正是
  「拿着过期归档声称可复核」这种唯一不能容忍的情形；「归档能被重新解析」因此是**可执行、可复算**的断言，不是一句口号。

