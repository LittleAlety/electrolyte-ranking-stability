# `scripts/wp_production/` —— physics_completion_v1 批次（WP0–WP6）的生产流水线

这里放的是**生成已提交交付物的那套脚本**。它们原先散落在未跟踪的 `work/pilot12/`，
导致「仓库里的 `outputs/physics_completion/**` 到底怎么来的」在仓库内无法复现；
迁移到 `scripts/` 后，交付物与生成器同处一个被跟踪的命名空间。

## 导数政策（v1.2）

生产与救援优化只允许 wB97X-D4 解析一阶梯度，`NumGrad`/`%numgrad` 禁止。
冻结的 `NumFreq` 是解析梯度有限差分 Hessian；`AnFreq` 先在相同收敛几何上做配对审计，
不得逐腿择优混入账本。任务输入通过 `orca_derivative_policy.py` fail-closed 校验。
所有新任务和虚频救援进一步要求 `VeryTightOpt`；旧 `TightOpt` 仅在零虚频且其他 QC
均通过时保留。虚频处理顺序固定为严优化 → 同几何 `NumFreq` → 配对 `AnFreq` → 必要时模式扰动。

## 一键收口

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\wp_production\finalize_wp2.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\wp_production\finalize_wp2.ps1 -Commit
```

顺序：`anchors` → `emit-wp2` → `generator` → `provenance` → `state-identity` → `anchor-condition` → `sampling` → `li-motif-plan` → `ensemble` → `closure` → `cost` →
`recheck-plan` → `compliance` → `figures` → `mirror` → `site` → `freeze` → `clean-room` → 十四个 `--check` → `pytest`。
`cost` / `recheck-plan` 必须排在 `compliance` 之前（`build_plan_compliance.py` 直接读成本层与
靶向复核的产物）；顺序反了会让 `check-compliance` 读到上一轮状态而报 `differs`。
任一非零即 `ABORT`，不提交。

## 生产队列：查状态与断点续跑

四分子四态的最小完整集合是 4 分子 × {`M`, `M_tzvpd`, `M_plus`, `LiM_plus`, `LiM_2plus`}
= 20 条腿。它由**一个幂等队列器**驱动，机器重启后不必记「上一轮到底在跑什么」：

```powershell
# 只看状态，不跑任何计算
.venv\Scripts\python.exe -X utf8 scripts\wp_production\run_wp2_queue.py --status
# 把还没 computed 的腿跑完（已完成的跳过，failed / 被打断的自动重试）
.venv\Scripts\python.exe -X utf8 scripts\wp_production\run_wp2_queue.py --run
# 可选：无人值守监守（等其它 wp2 驱动退出后自动接管，最多 3 轮）
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\wp_production\supervise_pending.ps1
```

并发纪律：队列器只做调度，最多同时 3 个 worker 子进程，每个 worker 内 ORCA 用 4 核
（`run_batch.ORCA_CORES`），即全机最多 12 个 ORCA 核（本机 16 物理核）。`--run` 在开跑前会检查是否已有别的
wp2 驱动 / ORCA 在跑，有则拒绝启动（`--force` 可覆盖），防止叠加。检查时会排除队列自身进程与父进程，否则队列会把自己数成一个「已在跑的驱动」而永远自锁，使只有队列负责的 `M_tzvpd` 腿排不上。
本地 `smpd`（Microsoft MPI）在开跑前、**每个作业开跑前**、以及长跑期间每
`SMPD_RECHECK_POLLS`（15 次轮询，约 5 分钟）都复查一次：死掉就拉起；
连可执行文件都找不到时本轮**不新开作业**，既不白烧 `MAX_ATTEMPTS`，也不占机器。
2026-10-10 的一次重启就是因为它中途死掉、而队列只在启动时查过一次，导致 5 条腿在
0.2 秒内瞬败。

`supervise_pending.ps1` 持单实例锁 `work/_supervisor.lock`（锁里 PID 仍存活则自己退出，陈旧则接管）：机器重启后只要再拉起一个监守即可继续，不会出现两个监守同时接管、把并发从 3 个 ORCA 叠成 6 个。
无人值守的完整形状是**两个常驻看护 + 一个监守**：`watch_smpd.ps1` 兜住已在跑的旧驱动（smpd 死掉会级联秒败），`watch_supervisor.ps1` 接住监守 `exit 3` 的信号（否则闭环停在半路没人再拉起），监守自己负责跑队列并在结束后折入交付层。

## 各脚本职责

| 脚本 | 职责 |
| --- | --- |
| `check_wp2_anchors.py` | 复核 `emit_wp2.py` 的补丁锚点在当前生成器基线里唯一存在 |
| `emit_wp2.py` | 把 `work/wp2prod/**` 已跑完的状态折进生成器：重打 `WP2_PRODUCTION_LEDGER` 等补丁块 |
| `wp2_progress.py` | 只读 12×5 现场 payload 与固化 production ledger，分别给出运行进度、四主态严格科学验收、输入聚合哈希和 stale 判定；不把运行结束冒充 QC 通过 |
| `emit_wp1.py` + `wp1_audit_src.txt` | 把 WP1 方法审计矩阵折进生成器；`wp1_audit_src.txt` 是带 SECTION 标记的分段源码（`emit_wp1.py` 直接读它）。同内容的 `wp1_newsrc.py`（无 import、从不执行）已删除，避免在「每个 .py 都是入口」的目录里留一个假入口 |
| `run_batch.py` | 12 主集分子 × 4 主态的 xTB/ORCA 批量驱动与公共工具（几何、ORCA/xTB 路径、片段分析） |
| `run_wp2_production.py` | 生产级 Opt+NumFreq 驱动（`M` / `M_plus` / `LiM_plus` / `LiM_2plus`） |
| `run_wp2_extra.py` | 与带电腿**基组一致**的中性腿 `M_tzvpd`（def2-TZVPD）驱动 |
| `run_wp2_queue.py` | 上面两条驱动的幂等队列器：**12 主集分子 × 5 腿 = 60 条腿**的统一调度（并发上限 3 worker × 4 核）、断点续跑、逐次开跑与周期复查 smpd；覆盖范围与 `data/metadata/physics_completion_set.csv` 的 `in_main=true` 集合由 `tests/test_wp2_queue_scope.py` 钉死，防止再次无声漂移（曾写死四分子，跑完 20/20 后队列永远 empty、生产静默停在 16/48） |
| `run_to_closure.py` | 队列收尾：队列已停就把**已 computed 的腿**折进 production_ledger / 四分子闭环表 / 四分子标签 / week37-week44 镜像；未齐的腿在交付层留空并显式列出（不补数、不替换结构）——硬门禁会让某条反复失败的腿把交付层永远钉在旧数，那才是失败模式。`--check` 只报告，`--dry-run` 只打印，`--commit` 在 ALL GREEN 时提交（不 push），需要严格门禁时用 `--require-complete`。**折入前先跑关键 pair 第二泛函靶向复核**（`build_pair_recheck_plan.py` → `run_pair_recheck.py` → `emit_pair_recheck.py`）：腿一落地，`build_pair_recheck_plan.py` 的 ready 行就变多，不补跑复核则收口链的「结果表恰好覆盖 ready 行」验收失败、`-Commit` 不执行，交付层停在「腿算完了、还是旧数」；`--skip-recheck` 可跳过（一般不要用） |
| `run_method_audit.py` | WP1 的 128 单点 / 32 弛豫腿本机方法审计驱动 |
| `make_commit_msg.py` | 按当前已落地子集生成提交信息（写 `work/_wp2_commit_msg.txt`） |
| `prepare_hpc_main_remaining.py` | 把队列里 `missing` 的腿打成**超算任务包**；每个数组任务写入不可变的 `attempts/<attempt-id>`，EXIT trap 保存 Slurm/主机/资源/线程/scratch/module/MPI/ORCA/退出码证据，并用追加式 selected/success marker 区分技术运行与后续科学 QC；只准备，不上传、不提交、不跑 ORCA | 队列 `inventory()` → HPC 包 |
| `submit_hpc_batch.py` | 唯一允许的批次提交入口：只走受保护 `hpc.ps1` 桥；doctor 后先原子获取账户级 `~/project/electrolyte_wp2/.wp2_submit.lock`，持锁完成真实 `squeue`、**运行中 + 排队中 ≤20** 门禁、submit 响应与本地 durable journal，再在 finally 经桥释放。并发/陈旧锁一律 fail-closed、不得静默删除。资源由被哈希 manifest 的版本 profile 固定：历史 ORCA 默认 4核/24h/800 core-hours；`xtb_screening_v1` 固定 2核/2h/32 core-hours、强制 attempts ledger，CLI 只能断言不能放宽；引擎与 `%pal`/`cores.txt` 输入契约交叉核验。`--collect-sacct ATTEMPT_DIR` 通过桥独立采集终态 `sacct.terminal`；缺它不得做自动技术重试分类。**不得直接调用 `hpc submit`** | HPC 包提交 journal；或 attempt 的 scheduler 终态证据 |
| `import_hpc_numfreq.py` | 超算 NumFreq 结果的**只读校验 + 非覆盖导入**：拒绝混用梯度（`Restart` 复用位移几何且最大位移 > 2e-6 Å 即拒收）、拒绝源 Opt 未收敛 / 源已有频率、核对 HPC 起始几何与本地部分腿逐原子一致、要求热化学完整且 `G = E + 热校正`；**虚频结果照样登记但写 `status=failed` / `qc_flag=imaginary_modes`（退出码仍为 0，判定必须读 status）**；写盘一律不覆盖内容不同的既有文件 | `work/hpc_results/<job>/…` + `work/wp2prod/<name>/<state>/` → `<NAME>_<STATE>.{json,log,_opt.xyz}` + `hpc_import/provenance.json` |
| `import_hpc_opt_numfreq.py` | **自包含 HPC Opt+NumFreq 腿**的只读校验 + 非覆盖导入：新包必须显式传入 `tasks/<NAME>/<STATE>/attempts/<attempt-id>`，旧包仍兼容固定 `run/`；严格要求 checksum 两行唯一、manifest 单腿全字段绑定，并导入/哈希 schema 声明的运行环境、journal 与 Slurm stdout 证据。默认只收冻结输入；仅受控 continuation 可增加精确 `%geom MaxIter 200 end`。正常终止只是技术证据；优化收敛与虚频仍由 importer 独立科学 QC，虚频记 `status=failed` 而不触发技术重试。批量回收可对各腿使用 `--apply --defer-finalize`，全部写入后只运行一次 `finalize_wp2.ps1`，避免重复全量哈希与测试 | 明确 attempt 目录 → `work/wp2prod/**` + `hpc_import/provenance.json`/`evidence/` |
| `build_descriptor_analysis.py` | 方案 §7.3 描述符层（派生层，零新增计算）：只读冻结的样本元数据、氧化标签与廉价 ESP，对 donor type / chelation / flexibility / functionalization / 廉价 ESP 报**全部**检验（含不显著），Holm 与 BH 两种多重比较并列，TPSA 仅探索性；n=12 不拟合多参数机制模型 | 冻结产物 → `outputs/physics_completion/pair_evidence/descriptor_analysis.{csv,md}` |
| `reopt_saddle.py` | 收敛到**鞍点**（虚频）的生产腿的**可复现逃逸**（原先只活在 gitignore 的 `work/wp2prod/_reopt/` 里，导致账本引用的扰动起点无人能复现）：解析腿日志 NORMAL MODES 的虚频位移向量、把收敛几何沿它位移（最大单原子位移 = `--amplitude`，默认 0.20 Å）、写出扰动起点 + JSON（模式号/频率/符号/幅度/源文件 sha256/方案 §6.3 原文）；**先校验该模式确是虚频**否则拒收；`--leg-dir` 指向 `work/wp2prod/_saddle_attempt1/` 可复现历史输入（已对 GBL 验证：归一化行尾后逐字节相同）；`--run` 才起本机 ORCA，超算路线是「扰动几何打包 → `import_hpc_opt_numfreq.py` 导入」 | 腿 `work/wp2prod/<NAME>/<STATE>/{log,_opt.xyz}` → `work/wp2prod/_reopt/*_perturbed_s<±>_a<amp>.{xyz,json}` |
| `fold_anfreq_into_ledger.py` | **协议 v1.3 折入器**：把全 cohort 的 `AnFreq`（解析 Hessian）结果写回生产账本。每条腿取**自己冻结收敛几何**上的 AnFreq 日志（无 Opt，几何不得移动），用**与生产同一个** `run_wp2_production` 解析器读热化学（不另写第二套定义），重算虚频数并改写 `level`（只写实际关键字，绝不谎报算法）、`frequency_hessian=analytical_hessian`、`protocol_version=1.3`；**仍带虚频的腿写 `status=failed`/`qc_flag=imaginary_modes`**，绝不冒充可验收；旧 NumFreq 行连同其日志原样存 `superseded_numfreq/` 并登记 `superseded_numfreq_row_sha256`（v1.2 ④ 要求两种 Hessian 算法不得在同一比较里静默混用）；**幂等**——目标态标志检查（`protocol_version==1.3` 且 `frequency_hessian==analytical_hessian` 时直接跳过整轮折入）+ **快照 first-copy-wins**（`superseded_numfreq/*.json`、`*.log`、`pre_rescue.json` 三处均只写一次，永不覆盖首份快照），防止二次运行或重导 NumFreq 行后二次折入静默销毁敏感性证据；默认只预览，`--apply` 才写盘。另有 **rescue 导入模式**（`--rescue-leg/--rescue-log/--rescue-geom/--rescue-start-level`）：接管「独立作业在救援收敛几何上的 AnFreq 频率单点」这一既非 Opt+freq 也非 continuation 的形态（如 TMP/LiM_plus c04 续算几何，job 3717952），几何与日志 stage 进腿目录 `anfreq_rescue/` 并登记 sha256，旧 failed 行存 `superseded_numfreq/*.pre_rescue.json`（同样 first-copy-wins），仍带虚频即拒收；回归测试 `tests/test_fold_anfreq_into_ledger.py`（4 条：折两遍快照不变、重导 NumFreq 后二次折入快照仍为原件、救援两遍 pre_rescue 不变、同 rescue 日志幂等跳过） | `work/hpc_anfreq_cohort_20261016/{local_runs,hpc_runs}/<MOL>_<STATE>/job.log` + `work/wp2prod/<NAME>/<STATE>/<NAME>_<STATE>.json` → 同一 JSON + `superseded_numfreq/` + `anfreq_rescue/` |
| `build_production_ensemble_manifest.py` | **生产级 48 态系综的候选清单与 HPC 分块包生成器**（方案 §6.1/§6.2；对应 compliance 的 `wp2_conformer_ensemble`——只有 `production_ensemble_labels.csv` 里的 QC 通过标签计 48 分母，GFN2 筛选层永不计分母）。按冻结链选材：primary（已有 QC 生产结构，**中性 M 槽映射到同基组的 M_tzvpd 腿**）+ 自由态构象池/Li motif 池合并 → 6 kcal/mol 窗口 → 连接关系（1.3× 共价半径，`run_batch.RADII`）→ Li 给体齿数（≤3.0 Å）→ 重原子 Kabsch RMSD（0.35 Å，`build_li_motifs.kabsch_rmsd`）→ 每态≤3 结构含 primary；Li 池 `placement=production_geometry` 条目视为 primary 别名不再补腿；柔性分子的扭转级去重**刻意推迟到 DFT 后**（用户链：科学 QC + DFT 后再次去重）。新增结构一律用冻结 v1.3 语法（`prepare_hpc_main_remaining.input_text`：Opt VeryTightOpt **AnFreq**、def2-TZVPD、解析梯度）；`--build-packages work --chunk 18` 产出 18 元素以内的分块包（backfill 纪律），round2（3→6 审计）候选只登记在 manifest 里、等 round1 G_ensemble 齐了再开 | 冻结池（`sampling_conformer_set.csv`、`li_motif_screen.json`）+ `work/wp2prod/**` → `outputs/physics_completion/ensembles/production_ensemble_{candidates.csv,manifest.json}` + `work/hpc_production_ensemble_r1_*/` |
| `import_ensemble_structures.py` | **系综结构专用导入器（primary 账本防火墙）**——系综补充腿**绝不当普通主腿导入**（只读 `work/wp2prod`，唯一写入目标＝`production_ensemble_structures.csv`）。逐结构 fail-closed 九查：①`inputs.sha256`；②输入必须 `AnFreq`（v1.3、拒绝 superseded/NumGrad）；③正常终止；④VeryTightOpt 收敛五阈值（复用 `enforce_geometry_convergence`，打印容差必须等于冻结容差）；⑤charge/multiplicity 与槽位映射一致；⑥频率数=3N 且零虚频（冻结解析器）；⑦热化学齐 + G=E+thermal 恒等式（≤2e-7）；⑧连接关系起止不变（项目 1.3× 共价半径约定）；⑨Li 槽位齿数+单片段重分类；另加 **Hessian 联动**（`validate_hessian`：频率能量与热化学在打印精度内一致、Hessian 几何与最终几何一致）。缺 `run/job.log` 记 `pending`（缺席≠失败）；`--fetch` 先 scp 已完成任务（含 stderr/utc/trj/job.xyz，远端字节 sha 校验）再 QC；**四态语义**＝pending / technical_complete_qc_failed（含机器可读 failure_class：strict_reopt_required=已收敛但 TolE 超标、max_cycles_exhausted=优化圈耗尽 AnFreq 未跑、orca_error_in_log、imaginary_modes、connectivity_changed 等）/ computed / superseded（后续 attempt 取代但证据保留，attempt 列区分代数）；`--build-reopt` 生成严格重优化包（仅 strict_reopt_required，从各自收敛几何启动，含 package manifest 逐条登记源作业/源日志 sha/新起点 sha/charge-mult）；`--build-continuation` 生成 max-cycles 成员的独立续算包（轨迹最低能帧可复算选取 + `%geom MaxIter 200`；**提交前物种身份门**＝帧 vs 候选登记几何的原子序 + 冻结 1.3× 键图，漂移者以 `restart_species_drift` / `candidate_atom_order_changed` 机器可读原因记入 manifest 的 `pre_submission_rejections`、绝不进 tasks.txt——从漂移帧续算会忠实重优化另一个分子）；；**`--build-r2-followup`** 生成 round-2 审计腿的跟随包（`strict_reopt` 从自身收敛末几何重启 + 身份门；`technical_retry` 逐字节复用输入并核验登记起点 sha256、不扣救援预算；成员保留 `round2_audit_extra`、attempt N+1 才是 ceiling 聚合行）；分支还包括 **`max_cycles_exhausted` → 续算**（轨迹最低能帧 + `%geom MaxIter 200 end`，身份门同样先比原子序与键图；同一成员只给一次续算，再耗尽即登记限制）；包名自动递增 `r2_reopt`/`r2_reopt2`…，已提交的包绝不被覆盖；**`--build-li-round2-legs`** 把第二轮 Li motif 实测出的新盆地各转一条冻结协议生产腿（只打包 `new_vs_round1=true` 的盆地，起点逐字节核验登记 sha，成员 `round2_audit_extra`，不回溯改变 round-1 验收）；36 条 pytest 含「永不触碰 wp2prod」「正常终止+ORCA ERROR 仍拒收」「max-cycles 不得进 reopt 包」「身份门三态」（漂移帧拒收/原子序改变拒收/完好帧接受） | `work/hpc_production_ensemble_r1_*/tasks/**` → `outputs/physics_completion/ensembles/production_ensemble_structures.csv` |
| `ensemble_hpc_io.py` | 使用 WHU HPC 策略命令桥核验 Slurm 终态后，按远端逐文件 SHA256 回收不可变快照与收据；导入器校验该收据和输入哈希后才进行科学 QC。旧的直接 scp `--fetch` 已禁用 | 远端 `run` / `attempts` → `work/hpc_production_ensemble_r1_*/tasks/**/snapshots/**` |
| `build_production_ensemble_aggregator.py` | **生产级 48 态系综聚合器**（§6.1/§6.2；compliance 的 48 键分母来源）：只读 QC 结构账本（不碰零散日志）。每 molecule×slot：只收 `computed` 成员；primary 恒为成员（池空则 N=1 标签 + `pool_limited` 登记）；DFT 后去重（连接→Li 齿数→重原子 Kabsch RMSD 0.35 Å→扭转等价）；**log-sum-exp 数值稳定**实现 `G_ensemble = G_min − RT·ln Σᵢ gᵢ·exp(−(Gᵢ−G_min)/RT)`（298.15 K、默认 gᵢ=1 不得事后调整）；状态内温度必须一致、权重和恒为 1（测试钉死）；输出成员权重表/去重决策表/48 行标签/索引（输入哈希+生成时间+stale 标志，`--check` 用重算前快照对账，账本变动即 STALE）；6 条 pytest 覆盖单成员、重复成员、500 kcal 极大能差防下溢、登记简并度、账本驱动端到端（computed 加入/failed 排除/权重归一/stale 触发） | `production_ensemble_structures.csv` → `production_ensemble_{weights,dedup,labels}.csv` + `production_ensemble_index.json` |
| `build_sampling_audit_3to6.py` | **3→6 采样审计计划生成器**（§6.1 / v1.4 §5.2）：对冻结的四个审计分子（EMC/DEC/DME/TMP）× 四主态，逐态统计**池内 6 kcal/mol 窗口里的独立极小真实数量**、round-1 结构与 round-2 上限，据此判定 `executable` / `executable_partial` / `sampling_limited`——**池内不足 6 时只登记真实上限与搜索证据，绝不用重复构象凑数**；Li 态额外标记 `needs_second_round_motif_search`（现有 motif 池普遍仅 1–2 个，必须先补第二轮搜索）。产出 CSV+MD+索引（含输入哈希与 stale 检测，`--check` 完全只读） | `sampling/sampling_conformer_set.csv` + `li_motif_sampling/li_motif_screen.json` + `ensembles/production_ensemble_structures.csv` → `sampling/sampling_audit_3to6.csv` + `.md` + `sampling_audit_index.json` |
| `build_tolerance_preregistration.py` | **3→6 采样容差预注册稿（草案，不选数值）**：按方案「容差须来自独立数值重算或明确实用分辨率，先冻结再评价新批次，不能由当前差异倒推」登记三条候选依据（A 独立数值重算 / B 明确实用分辨率 / C 跨方法离散上界参考），每条列出所需证据与现有可复用线索；当前 3 个 complete 差异**明确标注仅作参考、绝不是容差依据**；冻结时需登记的四项（依据/证据 sha256/声明早于结果/冻结后不得调整）齐备。选定由用户裁决 | `sampling/tolerance_preregistration_draft.md` + `_index.json` |
| `build_sampling_ceiling_classification.py` | **3→6 ceiling 缺口四分类**（计划项⑤证据侧）：把 13 个 not_computed 分成「已登记待 QC」「池无独立结构」「塌缩到已有极小」「覆盖真缺失」（+ complete/unclassified），四类不可互换；**容差未冻结**故只描述差异、不给收敛结论；`strict_recovery_v1` 已登记起点单列可见（登记事实，不代表 ceiling 已变）；**跨账本矛盾会被 WARNING 抓出**（classified pool-limited 但缺口表仍有未用盆地：实测 DEC/M 与 TMP/M_plus） | `sampling/sampling_ceiling_classification.csv` + `.md` + `_index.json` |
| `build_sampling_3to6_diff.py` | **3→6 采样差异报告生成器**（§6.1 / v1.4.2 第 4 条；按用户 2026-10-19 决定**本轮只报差异、不判“采样收敛”**）：预注册比较量——各态 `G_ensemble`、氧化轴 `G(M_plus)−G(M)`、Li 条件轴 `G(LiM_2plus)−G(LiM_plus)`、审计集 Top-k 集合与 selection regret（审计集只有 4 个分子，故主 k=2、辅助 k=1/3），单位与舍入一并冻结。round-1 侧直接取生产系综标签（可复算），**ceiling 侧在第二轮结构还没有生产 DFT 腿时留空并写明原因——空格是诚实状态，绝不补零、绝不写成“无变化”**；`sampling_limited` 只表示搜索/扩样覆盖受限，不是数值收敛结论；GFN2 的 1.00 kcal/mol 只作筛选阈值。`--check` 完全只读 | `ensembles/production_ensemble_labels.csv` + `sampling/sampling_audit_3to6.csv` + `ensembles/production_ensemble_manifest.json` → `sampling/sampling_3to6_diff{,_axes,_selection}.csv` + `.md` + `sampling_3to6_diff_index.json` |
| `finalize_wp2.ps1` | 上面那条一键收口链 |
| `supervise_pending.ps1` | 无人值守监守：单实例锁 + **每轮开跑前**都等其它驱动退出后调 `run_wp2_queue.py --run`，队列结束后再调 `run_to_closure.py --commit` 把结果折进交付层（折入会先补跑关键 pair 第二泛函靶向复核；失败时有界重试 3 次——20/20 之后看护按「还有腿没 computed」判据不再重启监守，不重试就会把交付层永久停在旧数）。轮次不是固定的：只要已 computed 的腿数在涨就继续下一轮，只有**连续 `-MaxStalledRounds`（默认 3）轮毫无进展**才停；结束时若仍有腿未 computed，日志写 `INCOMPLETE` 并返回 3（重新拉起即可继续）。旧版固定跑 3 轮就退出删锁，一轮里撞上 smpd 刚死的窗口就会让闭环静默停在半路 |
| `supervisor_policy.py` | 上面那条收敛判据（纯函数，有单测）：`--computed-count` 按队列自己的 `inventory()` 口径数已 computed 的腿，`--decide` 判断该继续 / 完成 / 因停摆或轮数上限而停。把判据从 `.ps1` 的分支里拿出来，是为了它可被测试钉住——写错就会让闭环关不上 |
| `watch_smpd.ps1` | 轻量 smpd 看护（常驻、约 0 CPU）：每 `-IntervalSeconds`（默认 300）检查 Microsoft MPI 的 smpd，缺失就拉起，日志写 `work/_smpd_watch.log`。用途是兜住**已在跑的**旧驱动——它们没有队列的逐次复查，smpd 一死就会级联秒败；停止：`Get-CimInstance Win32_Process | Where-Object CommandLine -like '*watch_smpd*'` 取 PID 后 `Stop-Process` |
| `watch_supervisor.ps1` | 监守的看护（常驻、约 0 CPU）：每 `-IntervalSeconds`（默认 600）检查一次——还有腿没 computed、又没有活跃监守时，把 `supervise_pending.ps1` 重新拉起来（`-MaxHours` 默认 120）。监守是**有意**会退出的（连续无进展时写 `INCOMPLETE` 并 `exit 3`，把「要不要再来一轮」交给外部），没有这个看护，那个信号就没人接，闭环会静默停在半路。它只调 `supervise_pending.ps1`，不加 `--max-jobs` / `--force`，并发上限仍由监守守；判据走 `supervisor_policy.py --watch-decide`（纯函数，有单测）；日志写 `work/_supervisor_watch.log` |
| `archive_raw_outputs.py` | 把 provenance 里登记的原始作业文件打成**确定性、可复核的 zip 归档**（`--build` 生成，默认落在仓库外 `_compute_archive/`；`--check <zip>` 逐条复算 sha256）；并把当次 manifest 内嵌成 `_manifest/job_archive_manifest.csv`，让归档的「同版 / 过期」自证 |
| `verify_archive.py` | 归档的**可重新解析性**核验：拿归档里的原始日志按仓库口径重算登记值，与该作业在 `job_archive_manifest.csv` 里的值逐字段比对；`--ledger` 再用同一份归档重算交付账本 `production_ledger.csv` 的数值列。缺条目 / sha256 不符 / 数值不符都算失败（退出码 1），`--limit N` 调试、`--strict` 把「算不出来」也算失败；`--latest` 自动取最新归档并先打一行 `[freshness]`，`--gate-when-complete` 是收口链里的结题门禁（只在 20/20 时先重建归档再要求同版 + 0 不符）。生产在跑期间归档必然落后于 manifest，报的是「登记晚于归档」的预期漂移；队列停掉后重建归档再跑才应回到 0 |
| `build_wp2_closure.py` | 四分子四态闭环 + 翻转持续性 + 逐作业复现证据（派生层） |
| `build_plan_compliance.py` | 方案 4-14 节逐条合规台账：状态与数字全部从产物现算（四分子闭环 / 方法审计 / 翻转持续性 / 锚点审计 / AL 预算），源码里不写死；把「都做完没有」变成一条可复算的链上检查（派生层） |
| `build_state_identity_qc.py` | 方案 6.3 态身份 QC：读被 gitignore 的 `work/wp2prod/**` 里原始 ORCA 日志的最后一段布居块，现算 fragment charge/spin（Mulliken + Loewdin 双分区，两个分区不一致就记 ambiguous）与 Li 的 Mayer bonded valence；Li-给体**键级**与 **接触距离（Angstrom）**分列登记（弱接触低于 ORCA 打印阈值时留空、不补零，绝不拿 ~2 Angstrom 的键长冒充键级），按结果前冻结的阈值分成 intact / Li_centered / mixed / ambiguous / fragmented / no_li 六张分表；frontier 定位显式登记为 not_computed 并写明补法，不拿来源不清的 HOMO/LUMO 充数（派生层） |
| `build_anchor_condition_audit.py` | 方案 8(a)/8(c)：把四组既有锚点源里本就有的条件列并成一张 87 行表（溶剂 / 盐与浓度 / 温度 / 扫描速率 / 误差来源 / 原始标度与数值 / 页码表号 / primary 源状态），缺的留空并写明原因、绝不补 0；并断言检索协议已登记**且已执行**（executed=true + 执行记录 data/references/anchor_retrieval_execution.md 在盘上）、本轮新命中可纳入 0 条，tier_1 仍为 0、按协议 §6 停止规则保留 external-validity limitation（派生层） |
| `build_wp2_sampling.py` | 气相 GFN2 构象筛选层（派生层） |
| `build_compute_provenance.py` | 逐作业复现证据清单 + 从各自 `.log` 推导的 `failure_reason`，外加**四分子 20 条腿现场核对** `leg_reconciliation.csv`（登记 vs 磁盘事实；`duplicate_work_risk` 是唯一告警）（派生层） |
| `build_wp2_cost_scenarios.py` | 方案 11：按类中位 / p90 与剩余成本低-中-高情景（派生层） |
| `build_pair_recheck_plan.py` | 方案 5.3 / 11：关键 pair 第二泛函靶向复核的结果前预注册计划。预注册层（规则 / 对象 / 设定 / 几何来源 / 预算）零新增计算；复核跑完后只**读** `recheck_results.csv`、现算逐 (pair, 设定) 的 delta，并登记结果层与实测成本行 |
| `run_pair_recheck.py` | 靶向复核**执行器**：在已登记的生产 Opt 几何上跑 S3/S4 单点（不重优化、不算频率），串行、每作业 2 核；原始现场落仓库外 `work/recheck/` |
| `emit_pair_recheck.py` | 靶向复核**手工折步**：把 `work/recheck/` 的原始单点折成 `recheck_results.csv`（逐行带几何 sha256）。与 `archive_raw_outputs.py` 同性质，输入在仓库外，因此不进收口链 |
| `build_li_motif_sampling_plan.py` | 方案 6.1 / 执行第 3 步：四分子 Li 配位 motif 采样的结果前预注册（派生层，零新增计算） |
| `build_li_motif_plan_round2.py` | **第二轮 Li motif 搜索预注册**（v1.4.2 项 5）：第一轮已对单一父几何穷举全部配位规则（monodentate+bidentate+esp_min，7–14 位点/腿无截断），审计 8 个 Li 态仍只有 1–2 个独立极小；第二轮的搜索空间＝**同一冻结配位规则 × 冻结自由态构象池的其他中性盆地做替代父几何**（EMC 2 / DEC 4 / DME 6 / TMP 3 个盆地，逐个带 sha256 磁盘核验）。登记每腿 round-1 kept + 已核验替代父数＝**round-2 上界**（诚实上界：配位可能去重回同一极小，真实独立数只能执行后测得）；零新增计算，执行是显式调用的独立步骤 | 冻结池 + 第一轮 screen 记录 → `li_motif_sampling/li_motif_plan_round2.csv` + `_index.json` |
| `build_frontier_identity_evidence.py` | **身份证据链装配（v3.1 第 2 项）**：每成员验证同一次执行的input/log/geometry/molden 四文件存在且记原始哈希；方法(wB97X-D4/def2-TZVPD)/SCF(TightSCF)/正常终止/电荷多重度与登记一致；自旋通道与声明波函数一致 → identity_qc_status=pending→verified；缺本地文件记 awaiting（不等于需重算） | `frontier/frontier_identity_evidence.csv` + `_index.json` |
| `provenance_hash.py` | **来源哈希契约（2026-10-22 修复）**：文本产物按 CRLF→LF 归一化后取 sha256（git/平台稳定），二进制或未知后缀按原始字节；由 `sha256_artifact` 按后缀分派，**不允许调用方自选口径**。实测缺陷：726 个文本产物中 34 个带 CRLF，同一逻辑内容有两种哈希 | 库模块；契约串 `CONTRACT` 写进重冻记录 |
| `build_ensemble_cost_by_family.py` | **按族成本账（v3.1 第 5 项）**：区分**基础主态成本**（60 条主腿）与**完整系综标签获取成本**（额外/恢复/扭转腿）；按**唯一作业身份**（包+作业号+数组号）记账，同一次运行绝不计两次（run/ 与 snapshots/ 只取后者）；失败/取消腿保留实测 elapsed（取消=0 但绝不删除）；无终止时间戳记 in_flight_cost_unknown不计入总额；整族无时间戳（电子身份单点）如实登记为 missing 缺口，不估算 | `cost/ensemble_cost_by_family.csv` + `_index.json` |
| `refreeze_manifest.py` | **冻结清单可复现重冻 + 漂移分类**：`eol_recalibration`（同内容换口径）与 `content_change`（真实内容变化）分开记录；`--drop` 移除自引用产物（审计器输出不能冻在自己验证的清单里，无不动点）；`--check` 只读，任何漂移即失败 | `outputs/week26/provenance_refreeze_record.json` |
| `build_torsion_probe_package.py` | **有界片段扭转、候选 gate 与版本包生成器**：核实中心单键、切分共价图，仅旋转一侧片段；全原子拓扑保持映射 + proper Kabsch 拒绝刚体/对称等价起点。`build_repair_package` 只处理获批原候选。P4 xTB 路径用 `--build-p4-screening` 从权威生产账本派生电子态、重建 8 个候选并生成单数组 `0-7%2` 的 2核×2小时 HOLD 包；`--check-p4-screening` 内存重建并只读比对 raw geometry/输入/manifest/完整 SHA256 清单，绝不自动修复。 | [2026-10-22 修复记录](../../docs/hpc_batch2_repair_20261022.md)；[P4 提交门](../../docs/handoffs/four_state_recovery_20261023/P4_SUBMISSION_GATE_20261023.md)；[P4 回归](../../tests/test_p4_screening_plan.py) |
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
| `build_second_search_preregistration.py` | **第二轮搜索方法预注册稿（草案，不选方法、不启动）**：列出本批**恢复不了的 6 态**（AN/DMC/EMC 的 M_plus 首轮 64 起点全部塌缩；DMC/DOL/EC 的 LiM_2plus round-3 motif 零新盆地）及其首轮证据，登记候选方法变更（阳离子：更大样本/换嵌入族/隐式溶剂筛选/更高筛选级别；配位：更宽 motif 枚举/多父体/显式溶剂 motif/MD 快照）与预注册四要素（方法唯一定义、成本上限、停止条件、不回填旧池）。**选定由用户裁决** | `recovery/second_search_preregistration_draft.md` + `_index.json` |
| `build_strict_recovery_manifest.py` | **strict_recovery_v1 恢复批次 manifest（登记，未启动）**：14 个 limited 态逐态登记优先级/路径/≤2 个新独立起点/每腿实测成本依据/停止条件/状态上限；缺口表的裸数字盆地与池目录名做**双拼写规范化**（`_canon`）后映射，池里取不到的盆地绝不登记；`new_search_required` 态的起点留空（等版本化搜索注册，不臆造）；28 条腿 = 14×2 硬校验。**历史失败一字不改**。测试见 `tests/test_strict_recovery_coverage.py`（7 项） | `recovery/strict_recovery_v1_manifest.{csv,md}` + `_index.json` |
| `build_frontier_localization.py` | **frontier 轨道定域分析**（单点之后的独立一步）：解析 Molden（`[GTO]` 用**消耗 nprim 行的状态机**，数据行本身也是两列数字，只有计数才可靠；`[Atoms] AU` 这类带尾随文本的节头要取括号 token），给每个计入系综成员算 HOMO/LUMO 能量、gap、`li_weight`/`donor_weight`（N/O/P/S）与 `frontier_class`；**阈值先冻结**（weight 0.50 / Li 0.25，index 里登记、读结果前定）。缺 Molden 记 `not_computed`、解析失败记 `parse_failed` 带原因，绝不静默写 0。测试 4 项（含手算权重核对） | `frontier/frontier_localization.csv` + `_index.json` |
| `build_frontier_legs.py` | **电子身份/frontier 定位腿清单**（计划项④）：cohort = `production_ensemble_weights.csv` 的**全部 73 个计入系综成员**（不是 48 primary）；几何按**登记 `final_geometry_sha256` 精确匹配**递归定位（文件名随 run 类型变，hash 是唯一可信键）；单点 + `%output Print[P_Molden] 1 end`，**分析是独立一步**——跑了没分析仍记 not_computed。实测 73/73 几何全部命中 | `frontier/frontier_legs.csv` + `_index.json` |
| `run_strict_recovery_search.py` | **strict_recovery_v1 独立盆地搜索（本地 GFN2 筛选层）**：按登记 seed/n_confs 撒新起点 → GFN2 `--opt tight` → 对冻结池盆地与已保留新极小做**重原子 Kabsch RMSD**（Horn 四元数，刚体不变量）×0.35 Å 去重；电荷/多重度取自冻结池行（M_plus = +1/2，绝不猜）。只登记真正的新极小；**零结果也记录** `states_searched`（塌缩到已知盆地是物理结论，不是缺跑）。`--check` 复核几何 sha256 与独立性 | `recovery/strict_recovery_v1_search_pool.csv` + `_search_index.json` |
| `build_coverage_reviews.py` | **覆盖复核（limited→accepted 的唯一通道）**：从 structures/dispositions/weights + 恢复 manifest **派生** `verdict`（resolved 需：新起点已 computed 且经 dedup 进入 kept、态内 ≥2 个独立极小、无 pending 恢复成员）；历史失败保留原状态；初始全 `pending`（无证据不升级）。聚合器据 `verdict=resolved` 且 `claimed ⊆ kept` 才改 accepted，**绝不清空 n_limited** | `recovery/coverage_reviews.csv` + `_index.json` |
| `build_d6_preregistration_draft.py` | **D6 预注册稿生成器（草案，未启动）**：四个排序敏感 M_plus 态（AN/DMC/EMC/TMP）的决策支持文档——从冻结 labels 派生accepted Top-3 地板与各态 gap 的「已越地板」判定（**派生不硬编码**）；预注册四要素（搜索动作与独立性/成本上限按 M_plus 实测 11.75 core-hours/候选选择含排序敏感判据搜索前冻结/停止条件每态 ≤2 起点）全部从 v3.0 §13.5+D6 登记；默认分支=限制报告（用户裁决不启动，需逐态点名）。index 无 wall-clock（输入哈希 provenance）。测试 5 项（gap 派生判定、Top-3 复算、四要素关键词、index 确定性、--check 篡改检测） | `ensembles/d6_ranking_sensitive_preregistration_draft.md` + `_index.json` |
| `run_wp5_AB_replay.py` | **WP5 A/B 验收回放**（12 分子最终标签池）：四策略 （random/diversity/uncertainty/ranking_aware）× 配对初始集（wp5_replay_contract）；停止预算=逐 repeat 逐非耗尽点 16/20×2 相邻点（排除 n_T≥pool 平凡解）；**查询成本从 production_cost_ledger 实测追溯**——A=M+M_plus 腿、B=Li 双腿+free 标签获取成本（计划明文规则），缺腿即 MISSING 不造数；盲性同契约（Acquirer 无完整标签+负向测试）。20 repeats 实测：6/8 组停止预算 n_T=7–9，random 两组未达如实登记。测试 7 项 | `active_learning/blind_replay/AB_{candidate_rounds,round_summary,axis_endpoint}.csv` + `AB_index.json` |
| `build_wp5_target_pool.py` | **WP5 A/B 验收目标池**（v2 输入契约）：从**最终**`production_ensemble_labels.csv` 派生 12 分子×2 任务的目标表——A=free 氧化移位（G_ens(M_plus)−G_ens(M)，eV）、B=Li 条件移位（LiM_2plus−LiM_plus；**取得 free 标签的成本属 B 的预算联动**，成本台账另行管理、不可追溯即 MISSING）。每行带双腿 acceptance/limitation 原文与 `qc_complete_pair`（非全 accepted 的对**保留在池中并如实标注**，绝不静默丢弃）。与 legacy C/M/E 池（legacy_method_demo）彻底分开、永不混淆。测试 5 项（12+12 行、与 labels 逐值复算、provenance 保留、池标签防混淆、--check 篡改检测） | `active_learning/blind_replay/target_pool_AB.csv` + `_index.json` （输入 labels sha256 钉死） |
| `wp5_replay_contract.py` | **WP5 盲回放 v2 契约层（纯函数，无 I/O）**：`stable_seed`（sha256 派生，task\|repeat\|purpose 作用域，绝不用带进程盐的 str 哈希）；`initial_visible`（**配对初始集**——同一 task+repeat 的四策略共享同四个初始标签，键只含 task\|repeat）；`empirical_stop_budget`（方案 §9 停止规则：**逐 repeat 逐非耗尽预算点**计数 O_3≥2/3 且 R_3≤0.10 eV，两个相邻预算点各 ≥16/20 才报经验停止预算；n_T≥n_pool 的平凡完美解排除；返回 None 是诚实未达，不造数）；`descriptive_mean`（末轮均值**只作描述统计**，与停止预算两套标签永不互换）。测试 `tests/test_wp5_blind_replay_v2.py` 7 项 | 被 `run_wp5_blind_replay.py` 导入；无独立输出 |
| `run_wp5_blind_replay.py` | **WP5 候选级盲回放**：修复旧回放只留聚合曲线的缺口——每轮每候选落盘预测值（`Acquirer` 结构性拿不到完整标签向量、构造后 `_assert_blind` 自检，`Evaluator` 独占真值且仅在选定后调用）；精确 k=3 端点（O_3/R_3，eV），**端点取池耗尽前的最后一轮**（n_T=n_pool 是平凡完美解，不用）；remaining error max/mean、累计 core-hours 用**登记为 ASSUMED_CONSTANT 的 0.6/查询假设**（非实测，index 显式声明）；种子派生用 sha256 摘要（str 哈希有进程盐）；`--check` 只读字节比对。测试 7 项（盲性结构、k=3 公式、端点非平凡、MISSING 不冒充、成本口径登记、篡改检测、跨进程种子稳定） | `active_learning/blind_replay/{candidate_rounds,round_summary,axis_endpoint}.csv` + `_index.json` |
| `build_gap_decision_support.py` | **14 个非 accepted 系综态的缺口决策证据生成器**：从 labels/dispositions/structures/audit/conformer 池/Li round-2 exec 只读派生——成员处置分布、未用盆地（键规范化后的真集合差）、RT ln(N_new/N_unique) bound、氧化轴 Top-3 排序敏感性（worst case vs accepted-only 地板）、四档建议（candidate_for_preregistered_new_start 仅限排序敏感且池有余量）。测试 6 项。 | `ensembles/remaining_gaps_decision_support.{csv,md}` + `_index.json` |
| `member_next_action.py` | **成员下一步处置的冻结判定契约**（纯函数，不做任何 QC）：身份漂移（键图/物种/原子序改变）凌驾一切分支且永不从漂移帧续算；技术故障（`abnormal_termination`）不算科学失败、不扣救援预算；救援预算按**去重后的 (attempt, log_sha256) 对**计数（重复提交永不双扣），两次即 `limited_rescue_budget_exhausted`（绝不写成「无极小值」）；`strict_reopt_required`/`verytight_convergence` → 从该腿自身收敛末几何严格重优化一次；`max_cycles_exhausted` → 仅当续算起点过身份门后续算；其余 `manual_review`。导入器 `production_ensemble_dispositions.csv` 的处置名由本路由器派生（legacy 词表不变）。测试 `tests/test_member_next_action.py`（10 项）钉死三分支与重复提交拦截 | 被 `import_ensemble_structures.py` 导入；无独立输出 |
| `run_li_motif_round2.py` | **第二轮 Li motif 搜索执行器**（v1.4.2 项 7 科学侧，唯一会自己跑 xTB 的 round-2 脚本）：读预注册的 `li_motif_plan_round2.csv`，对每个**磁盘哈希与登记值一致**的中性 M 盆地做替代父几何（不一致即 `parent_hash_stale` 拒绝、不换父、不造结构），沿用 `build_li_motifs.py` 冻结的枚举规则与 `screen_li_motifs.py` 冻结的保留规则（25 kJ/mol 窗口、同类重原子 Kabsch RMSD 0.35 Å、每腿 ≤3），并把每个保留 motif 与 round-1 保留结构逐对比，只有真正不同的极小才计入 `new_independent_basins`；输出**实测上限**＝round-1 kept + 新盆地数（登记上限只是启发式上界，不改动）；`--check` 复核 CSV 哈希、motif 几何哈希、父体哈希**与计划哈希**（计划重建后旧执行记录即判 STALE，防止把重登记过的计划与旧结果错配）。8 腿全跑 178 候选、35 秒、6 并发 | `li_motif_plan_round2.csv` + 冻结池盆地 + round-1 screen → `li_motif_sampling/li_motif_round2_exec.{csv,md,_index.json}`；工作目录 `work/limotif_r2/**` |
| `screen_li_motifs.py` | 方案 6.1 / 执行第 3 步的**执行器**（唯一一个会自己跑 xTB 的派生层脚本）：复用 `build_li_motifs.py` 里冻结的枚举规则，按每条腿自己的电荷/多重度在**该腿自己的几何**上跑气相 GFN2-xTB 配位 motif 筛选，去重后每腿保留最多 3 个独立 motif；`--check` 核对落盘 CSV 与运行记录同版（8 腿全跑约 30 秒，4 并发；不占 ORCA 槽位） |
| `make_physics_completion_figures.py` | 方案 14 的六张主图（F59-F64）与图清单 |
| `build_wp2_ensemble_free_energies.py` | 方案 6.1 第 3 步 / 6.2 的**系综层**：读两个已登记筛选池（自由态构象池 + Li motif 池），用 xTB GFN2 `--ohess` 重算自由能并求 Boltzmann 系综；`G_state = -RT ln Q` 与 `G_avg = Σ wᵢGᵢ` 两种口径**并列且不互换**，并给出 EMC-GBL / EMC-SL 的「同分子氧化轴」四层配对台与 Li 条件态对照；带虚频的结构留行、排除出系综；`--check` 要求 6 个产物 byte-identical。**筛选层，不是生产 R4**（状态 `computed_screen_only`） | 两登记池 + `work/enso/**` → `outputs/physics_completion/ensembles/**` |
| `build_physics_completion_deliverables.py` | 建交付镜像（仓库外 `成果输出（part2）/week37..week44`）；week44 结题提交包收录结题报告、协议、配置、样本、锚点审计、`docs/65_repo_layout.md` 骨架图、生成器源码、测试与全部 `outputs/physics_completion/**`；`--check` 逐文件复核 byte-identical |

## 边界

* **原始 ORCA/xTB 输出不入库**：留在仓库外 `work/`（生产为 `work/wp2prod/`，审计为 `work/audit/`，
  队列的原始 stdout 为 `work/wp2prod/_queue_<NAME>_<STATE>.out`）。交付镜像里只有派生的
  CSV/JSON；派生数值与原始日志的对应关系见
  `outputs/physics_completion/provenance/job_archive_manifest.csv`。需要独立取得原始日志时，用 `archive_raw_outputs.py --build` 生成确定性 zip 归档（默认落在仓库外 `_compute_archive/`），再用 `verify_archive.py [--ledger]` 拿归档里的原始日志按仓库口径**重算**登记值（`job_archive_manifest.csv` 与交付账本 `production_ledger.csv`）。最近一次重建（2026-10-12，含新导入的集群腿）：**859 作业 / 2612 文件 / 55.6 MB → 15.0 MB**（`raw_jobs_859_0ee3686c9474_20261012.zip`），`verify_archive.py --latest --ledger` 的 `[freshness]` 同版、**manifest 2321 处 / 账本 100 处逐字段比对 0 不符**；这类数字是快照——规模随队列推进增长，生产在跑期间归档必然落后于 manifest，队列停掉后（收口链的 `archive-verify` 门禁）会重建归档再核验。
* **生成器是派生物**：`scripts/build_physics_completion_batch.py` 由 `emit_wp2.py` 从
  「最近的未打补丁基线 + 补丁块」确定性重打；手工改它会失效。基线缓存在 `work/pilot12/gen_baseline.py`。
* **`work/pilot12/` 只是暂存区**：`run_batch.py` 的原始输出与生成器基线缓存仍落在那里；
  它被 `.gitignore`/提交时排除，不是交付物来源。
* **零新增电子结构**：除 WP1/WP2 与靶向复核三段**显式登记**的本机作业外，收口链不引入任何新的电子结构计算。靶向复核的单点（2 核 × 串行；条数与实测 core-hours 逐条记在 `cost_ledger.csv` 的 `..._computed` 行，不写死）落在已登记的生产 Opt 几何上，结果与成本记在 `outputs/physics_completion/pair_evidence/targeted_recheck/recheck_results.csv` 与 `cost_ledger.csv` 的 `..._computed` 行。
* **仓库骨架**：目录职责、阶段编号与 WP 的对应、收口链与不可改清单见 `docs/65_repo_layout.md`；新增顶层目录/子包不登记会被 `tests/test_repo_layout.py` 拦下。
* **`build_p4_screening_adjudication.py`（P4 筛选结果判定器）**：补上 P4 链条里此前**没有消费者**的那半侧——
  逐元素读 `xtbopt.log`（P4 的 sbatch 把 stdout 重定向到这里）/`xtbopt.xyz`/`.xtboptok`/`candidate.json`；
  三条件判收敛（`.xtboptok` + xyz 非空 + 日志含 `GEOMETRY OPTIMIZATION CONVERGED`）；
  **双源交叉校验**能量（stdout 的 `| TOTAL ENERGY … Eh |` 与 `xtbopt.xyz` 第 2 行的 ` energy:`，差 >1e-6 Eh 即记 problem）；
  按该态**冻结参考**算相对能并套 **6 kcal/mol 窗口**（`M`/`M_plus` = 该态筛选池最小值；`LiM_plus`/`LiM_2plus` =
  该态生产几何这个**固定父级**，并断言同态内反推参考恒定）；与已登记极小的**等价性复用聚合器原语与容差**
  （`bond_adjacency` + `find_topology_mappings` WL/回溯 → Kabsch RMSD < 0.35 → 扭转 ≤ 10° → Li 供体 → 镜像/手性），
  **不另写原子映射**，也**不做** `dedup_members` 的「按 G 排代表」（筛选层无自由能）。
  缺值/失败形态如实记 `not_run_yet` / `technical_incomplete`，**不冒充成功**；`--selftest` **20/20**；
  其夹具写在**仓库外**（`tempfile.mkdtemp`）⇒ **在只读仓库里也能跑**（原先把夹具写进 `work/`，
  被成员会话的只读沙箱以 `WinError 5` 拒掉、自测在第 12 项后中断——2026-10-25 由成员会话发现，
  已修，并用 `work/_selftest_write_audit.py` 动态证明「仓库内 0 次写入」）；
  `--json` 写出 + `--check` 逐字节复核（**只读**）。用途与规格见
  `docs/handoffs/four_state_recovery_20261023/P4_SUBMIT_RUNBOOK_20261024.md` §5.1–§5.2。
