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
| `submit_hpc_batch.py` | 唯一允许的批次提交入口：只走受保护 `hpc.ps1` 桥；doctor 后先原子获取账户级 `~/project/electrolyte_wp2/.wp2_submit.lock`，持锁完成真实 `squeue`、**运行中 + 排队中 ≤20** 门禁、submit 响应与本地 durable journal，再在 finally 经桥释放。并发/陈旧锁一律 fail-closed、不得静默删除。`--collect-sacct ATTEMPT_DIR` 通过桥独立采集终态 `sacct.terminal`；缺它不得做自动技术重试分类。**不得直接调用 `hpc submit`** | HPC 包提交 journal；或 attempt 的 scheduler 终态证据 |
| `import_hpc_numfreq.py` | 超算 NumFreq 结果的**只读校验 + 非覆盖导入**：拒绝混用梯度（`Restart` 复用位移几何且最大位移 > 2e-6 Å 即拒收）、拒绝源 Opt 未收敛 / 源已有频率、核对 HPC 起始几何与本地部分腿逐原子一致、要求热化学完整且 `G = E + 热校正`；**虚频结果照样登记但写 `status=failed` / `qc_flag=imaginary_modes`（退出码仍为 0，判定必须读 status）**；写盘一律不覆盖内容不同的既有文件 | `work/hpc_results/<job>/…` + `work/wp2prod/<name>/<state>/` → `<NAME>_<STATE>.{json,log,_opt.xyz}` + `hpc_import/provenance.json` |
| `import_hpc_opt_numfreq.py` | **自包含 HPC Opt+NumFreq 腿**的只读校验 + 非覆盖导入：新包必须显式传入 `tasks/<NAME>/<STATE>/attempts/<attempt-id>`，旧包仍兼容固定 `run/`；严格要求 checksum 两行唯一、manifest 单腿全字段绑定，并导入/哈希 schema 声明的运行环境、journal 与 Slurm stdout 证据。默认只收冻结输入；仅受控 continuation 可增加精确 `%geom MaxIter 200 end`。正常终止只是技术证据；优化收敛与虚频仍由 importer 独立科学 QC，虚频记 `status=failed` 而不触发技术重试。批量回收可对各腿使用 `--apply --defer-finalize`，全部写入后只运行一次 `finalize_wp2.ps1`，避免重复全量哈希与测试 | 明确 attempt 目录 → `work/wp2prod/**` + `hpc_import/provenance.json`/`evidence/` |
| `build_descriptor_analysis.py` | 方案 §7.3 描述符层（派生层，零新增计算）：只读冻结的样本元数据、氧化标签与廉价 ESP，对 donor type / chelation / flexibility / functionalization / 廉价 ESP 报**全部**检验（含不显著），Holm 与 BH 两种多重比较并列，TPSA 仅探索性；n=12 不拟合多参数机制模型 | 冻结产物 → `outputs/physics_completion/pair_evidence/descriptor_analysis.{csv,md}` |
| `reopt_saddle.py` | 收敛到**鞍点**（虚频）的生产腿的**可复现逃逸**（原先只活在 gitignore 的 `work/wp2prod/_reopt/` 里，导致账本引用的扰动起点无人能复现）：解析腿日志 NORMAL MODES 的虚频位移向量、把收敛几何沿它位移（最大单原子位移 = `--amplitude`，默认 0.20 Å）、写出扰动起点 + JSON（模式号/频率/符号/幅度/源文件 sha256/方案 §6.3 原文）；**先校验该模式确是虚频**否则拒收；`--leg-dir` 指向 `work/wp2prod/_saddle_attempt1/` 可复现历史输入（已对 GBL 验证：归一化行尾后逐字节相同）；`--run` 才起本机 ORCA，超算路线是「扰动几何打包 → `import_hpc_opt_numfreq.py` 导入」 | 腿 `work/wp2prod/<NAME>/<STATE>/{log,_opt.xyz}` → `work/wp2prod/_reopt/*_perturbed_s<±>_a<amp>.{xyz,json}` |
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
