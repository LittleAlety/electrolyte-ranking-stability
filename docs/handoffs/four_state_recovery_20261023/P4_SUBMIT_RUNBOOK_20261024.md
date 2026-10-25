# P4 筛选轮提交运行手册（2026-10-24 离线准备；**提交仍停在授权门**）

本文件只记录**离线已核验**的步骤与命令。**它本身不构成提交授权**：`manifest.json` 与
`selection.lock.json` 仍为 `submission_gate=HOLD`、`submitted=false`。

## 0. 当前冻结事实（实测）
| 项 | 值 |
|---|---|
| 包路径 | `work/hpc_four_state_p4_xtb_screening_v1/`（47 文件 / 8 任务 / 5 文件每任务） |
| 资源协议 | `xtb_screening_v1` = engine `xtb`、2 核、2 h、cap **32** core-hours、**要求 attempts ledger** |
| 数组 | 单数组 `--array=0-7%2`（最多 2 并发） |
| 预算不变量（真实账本） | committed=`0` + reserved=`32` = cap=`32`，剩余 `0` |
| 身份 | 三个 `LiM_2plus` 均 `charge=2/mult=2/spin=1`（`$chrg 2`/`$spin 1`）；`DMC|M_plus` 为 `$chrg 1` |
| 核数声明 | 每任务 `cores.txt` = `2` == allocation 2 |
| 脚本规范 | `batch_1.sbatch`/`batch_1.txt`/`tasks.txt` 均 **无 BOM + 纯 LF** |
| 索引映射 | `manifest.tasks` 顺序 == `batch_1.txt` 行序（`sed -n "$((SLURM_ARRAY_TASK_ID+1))p"`） |
| 离线模拟提交 | 17/17 通过，**bridge 调用尝试 = 0**（`work/_p4_mock_submit.py`） |

### 0.0 实时超算只读核验（2026-10-25，**Lead 自己经命令桥实测，未提交任何作业**）
| 项 | 实测 |
|---|---|
| `hpc.ps1 doctor` | **通过（0 项提醒）**：ssh 客户端 / 专用密钥 `id_ed25519_whu` / 三个节点 TCP / 免密登录 / `~/project` / module 系统 / 远端 `timeout` 全通过；`~/scratch` 按预期跳过 |
| `hpc.ps1 jobs` | **队列空**（表头无行 ⇒ 0 running / 0 pending） |
| 远端是否已有本包 | `ls -d ~/project/electrolyte_wp2/*p4*` → **No such file or directory（exit 2）** ⇒ **不存在重复提交** |
| P4 作业脚本依赖的远端装备 | `~/project/soft/xtb/env.sh`（450 B）与 `~/project/soft/xtb/bin/xtb`（63,253,248 B）**均存在**（exit 0）⇒ sbatch 里 `source …/env.sh` 与 `…/bin/xtb` 的假设**端到端成立** |

⇒ 本轮实耗 **0 core-hours**、在途 **0**、800 未动；提交侧仍停在授权门。

**本地半侧一键核验（只读，一命令）**：`work/_p4_preflight_local.py`
——7 项本地检查（包完整性 / 293 项包审计 / 离线模拟提交 17-17 且 0 次 bridge 调用 /
判定器原型自测 19-19 / 冻结清单 refreeze / 站点 `--check` / 包仍为 HOLD+未提交+cap 32）
**实测 7/7 通过、退出码 0**，并把「仍需桥或授权」的四步（doctor、实时 `squeue`、上传+远端根哈希、
受保护提交器）显式单列，避免误以为本地绿等于可提交。

### 0.1 bundle 的 `preflight.py` 当前报 `STALE`（退出码 2）——**这是真陈述，不是包坏了**
2026-10-24 在 HEAD `f1c0483` 实测：`preparation_status = "STALE"`，
`changed_sources = [build_coverage_reviews.py, import_ensemble_structures.py, submit_hpc_batch.py, HEAD]`。
独立复算（`work/_bundle_baseline_drift.py`，读 `baseline_snapshot.json` 的 `source_hashes`）**与之完全一致**：

| `WATCHED` 源（共 12） | baseline → 现在 |
|---|---|
| `scripts/wp_production/build_coverage_reviews.py` | `3ab3caf0185e` → `387d26b792ea` |
| `scripts/wp_production/import_ensemble_structures.py` | `badbce9f6f06` → `ec41475a2ff7`（含本轮的 **SCF 收敛门**） |
| `scripts/wp_production/submit_hpc_batch.py` | `59440414885d` → `086f113b73f6` |
| 其余 9 项（含 `config/production_method_freeze_v1.json`、全部产物 CSV、`orca_derivative_policy.py`） | **全部 ok（未漂移）** |

**刷新协议存在，但没有生成器**：`baseline_snapshot.json` 自带 `baseline_refresh_review`
（记 `previous_head` / `current_head` / `watched_hash_changes` 逐源 before-after / `reason`），
上一次刷新的 reason 写的是「authorised G0 …」。全仓检索确认**没有任何脚本会生成该基线**
（只有 `preflight.py --baseline` 的默认路径）。⇒ 刷新 = **对这几处脚本变更背书「已复核、已授权」**，
是一项**需要给出理由的复核动作**，不能手改抹掉。**本轮未刷新**：3 处漂移中 2 处是并行会话的脚本改动，
本会话无依据为其背书；本会话自己贡献的 1 处（SCF 门）也不能单独刷新。
**提交轮刷新时必须**：记 `previous_head=462f7f8b`、`current_head=<刷新时 HEAD>`、上表三条 before/after，
并在 `reason` 里**明确覆盖 `import_ensemble_structures.py` 的 SCF 收敛门**（本轮 `f64b954`）。

## 1. 授权到手后的固定顺序（不得跳步）
1. 阅读 `E:\软件\超算连接\AGENTS.md`（命令桥规程）。
2. `hpc.ps1 doctor` —— 未通过即**停止远端操作**，不得绕过命令桥。
3. 经命令桥**上传**包，远端**逐文件**核对根 `PACKAGE_SHA256SUMS`。
4. 查真实 `squeue`：确认本账户 `running+pending ≤ 20`、无同身份任务已在跑。

   **上传前的本地三级完整性核验（2026-10-24 实测已全过，可复跑；上传后第 3 步再在远端复核一次）**：

   ```bash
   cd work/hpc_four_state_p4_xtb_screening_v1
   sha256sum -c PACKAGE_SHA256SUMS          # 包级：46 条 = 40 个任务文件 + 6 个顶层文件 → 实测 0 FAILED
   for d in tasks/*/*/; do (cd "$d" && sha256sum -c inputs.sha256) || echo "FAIL $d"; done
                                            # 逐任务：8/8 目录通过（相对路径 ⇒ 必须在任务目录内执行）
   ```

   - 包内共 **47 个文件**（= `PACKAGE_SHA256SUMS` 46 条 + 该清单自身，不含自身是设计）；
   - 实测结果：`PACKAGE_SHA256SUMS` **0 FAILED**、逐任务 `inputs.sha256` **OK=8 / FAIL=0**；
   - 该格式为**相对路径**，与远端回收阶段「在任务目录内跑 `sha256sum -c inputs.sha256`」完全同构——本地先跑可提前暴露路径/格式问题，避免上传后才发现。

5. 调用受保护提交器（**唯一入口**，外层脚本不得绕过预算门）：

   ```powershell
   .\.venv\Scripts\python.exe scripts\wp_production\submit_hpc_batch.py `
     work\hpc_four_state_p4_xtb_screening_v1 `
     --batch 1 `
     --remote-workdir ~/project/electrolyte_wp2/p4_xtb_screening_v1 `
     --attempts-ledger work\hpc_four_state_p4_xtb_screening_v1\attempts_ledger.json
   ```

   - `--budget-cap-core-hours` 只作一致性断言（必须等于 `32`），**不能放宽 profile**。
   - 缺 `--attempts-ledger` 时 xtb profile **在 doctor 之前即拒收**（已实测）。
6. 提交成功后**立刻**登记：数组 JobID、8 个元素→任务映射、`submission_journal.json`。
7. **响应不明时先查 `squeue/sacct`，绝不重复提交**（journal + reservation 双保险会拒绝重复；已实测）。

## 2. 边界（红线）
- ORCA/xTB/GFN2 **只在 Slurm 计算节点**运行；登录节点严禁计算。
- 提交侧仍有三步**从未执行**（也因此从未触网）：`doctor`、账户级远端提交锁、实时 `squeue` 余量。
- 800 core-hours 是**建议上限、不是已授权余额**；筛选层上限为 32。
- 本包 8 个任务的科内容与「重建前后」逐字节一致（仅 `generator_sha256` 及根清单中该行变化）。

## 3. 提交前仍需用户裁决的两道科学门
1. **DMC 两态 `tors_0_1_2_3` 轴的单键性**：实测轴键长 `DMC|LiM_2plus`=**1.2733 Å**、
   `DMC|M_plus`=**1.2850 Å**（典型 C–O 单键 1.43 Å，Pauling 键级≈1.5）；registry 的单键证据
   来自**中性**拓扑，在阳离子态被削弱 —— 与 EC「排除 C=O 假扭转」同类。
   维持 registry 口径（保留但注明）／从严撤下或重新登记，需裁决。
2. **Li 位移的最小接触护栏**：冻结 offset {0.15,0.30,0.45} Å 无下界，实测
   `EC|LiM_2plus/toward_4` 被推到 Li–O **1.4528 Å**、`DMC|LiM_2plus/toward_3` 到 **1.4768 Å**
   （Li⁺–O 常见 1.9–2.1 Å）。这两个元素很可能直接弛豫回源极小 → 属成本有效性问题。

## 4. 明令禁止（已实测其在结构上不可被链调用，但执行者仍可能手 run）
- **禁止运行 `work/_p3_run.py` 与 `work/_p4_screen_plan.py`**：它们是旧 scratch 生成器，
  会用**错误的电子身份与资源配置**覆盖正式结果（历史字段曾把 `record_id` 塞进 `mol_id`、
  三个 `LiM_2plus` 曾错成 `1/1`）。实测：在 `scripts/`、`tests/` 与交接文档中
  **引用数 = 0**，即收口链与测试**不会**调用它们，危险只来自手 run。
- 生成与只读复核**只用**：`build_torsion_probe_package.py --build-p4-screening` /
  `--check-p4-screening`。

## 5. 授权后回收阶段的对应阶段
提交 → 回收（`ensemble_hpc_io.py`，幂等）→ 逐元素收终态/`xtbopt.log`/`stderr.log`/`xtbopt.xyz`/
启动终止时间/实测成本 → 按冻结 **6 kcal/mol** 窗筛选 → 四态分流（新盆地／回已知盆地／身份漂移／
八条均无新盆地）→ 有界生产计算（每态 ≤2 起点 + ≤1 有因补救）→ 逐腿六项验收。

### ⚠️ 5.1 提交前的就绪缺口：**回收后的「判定」尚无专用消费者**（2026-10-25 实测）
上文那条链里，**「回收」与「验收」两半都有工具，中间的「判定」这一半没有**：
| 环节 | 现有工具 | 状态 |
|---|---|---|
| 生成/校验筛选包 | `build_torsion_probe_package.py --build/--check-p4-screening` | ✅ |
| 提交 | `submit_hpc_batch.py`（受保护） | ✅ |
| 取回文件 | `ensemble_hpc_io.py`（幂等） | ✅ |
| 逐文件哈希/溯源 | `build_compute_provenance.py`（含 xTB 的 `xtbopt.log`/`xtbopt.xyz`） | ✅ |
| **判定（6 kcal 窗 + 等价原子映射/拓扑去重 → 四态分流）** | **无** | ❌ **缺口** |

实测证据：① builder 的全部 CLI 只有 `--repair-original-batch / --source-package / --out-package /
--build-p4-screening / --check-p4-screening`，**没有收结果模式**；② 唯一算 `rel_kcal` 与
`rmsd_to_nearest_known_a`（即新盆地/已知盆地判据）的工具 `run_strict_recovery_search.py` 是
**自己用本机打包的 xTB 重跑搜索**——`_run_xtb()` 直接调 `XTB`，`search_state()` 还会 `rmtree`
工作目录并按 SMILES 重新 embedding——**不是导入已跑完的任务目录**；③ 全仓检索确认没有任何模块
walk `work/hpc_four_state_p4_xtb_screening_v1/tasks/*/` 的结果（只有 builder、README 生成器、提交器
读它的 manifest）。

**含义**：筛选结果落地后，要把 8 个元素的输出变成「冻结窗口下的四态分流 + 覆盖证据」，
必须**先有新代码**（或改造上述 runner，但那会踩本机 xTB 的红线，且 `rmtree` 行为不可用于导入）。
⇒ **建议在提交前把这件事排进计划**：写一个**只读、幂等、可 --check 的判定器**，输入 = 任务目录
（`xtbopt.xyz`/`xtbopt.log`/`.xtboptok`/`candidate.json`），输出 = 每个元素的相对能、等价原子映射/
拓扑去重结论、四态分流 verdict，并**复用** `build_coverage_reviews.py` 的 route/verdict 词表
（该词表已由 G5 加守卫）。**本手册不自行实现它**（新脚本须按项目纪律四处登记、且需要真实结果才能验证）。

**该判定器必须先钉死的规格（否则窗口会算错）**：
1. **「6 kcal/mol 相对谁」——本项目其实有**两套**参考口径，P4 的 4 个目标态横跨两套**
   （2026-10-25 实测，**修正本手册上一版把两套混为一谈的写法**）：
   | 态族 | 参考 | 出处（列） |
   |---|---|---|
   | `M` / `M_plus`（如 `DMC|M_plus`） | **该 (name,state) 筛选池的最小值**（冻结原文 `window: 6 kcal/mol above the slot's screening minimum`，`build_production_ensemble_manifest.py:31`） | `outputs/physics_completion/sampling/sampling_conformer_set.csv`（**44 行，只有 M/M_plus**）的 `xtb_energy_eh` / `rel_kcal` |
   | `LiM_plus` / `LiM_2plus`（如 `DMC/DOL/EC|LiM_2plus`） | **该态自身生产几何（去掉 Li）这个固定父级**，`parent_kind = state_own_production_geometry_minus_Li` | `outputs/physics_completion/li_motif_sampling/li_motif_screen.csv`（99 个 LiM_2plus 行）的 `energy_eh` / `energy_rel_kj` |

   **实测判据**：对**每**个 LiM_2plus 态反推 `E_ref = E − energy_rel_kj/2625.499638`，在全部行内**恒定**
   （11 个态的离散仅 **0.0004–0.0009 kJ**＝舍入）⇒ 参考是**固定父级**，不是行内最小值。
   反例即 `DOL|LiM_2plus`：其**最优候选比该参考低 1.447 kJ**（该行 `energy_rel_kj = −1.447`；
   实测 `ref − E_min = +1.4466 kJ`，即**父级在最优候选之上**）——若按「行内最小值」当参考，
   会把这**唯一低于父级的候选**错算成 0 kcal，恰好抹掉最该看见的那条证据。
   ⇒ `sampling_conformer_set.csv` **没有 LiM_2plus 行**（只有 24 个 M/M_plus 态），
   对 3 个目标态用它当参考会直接算错窗口。
2. **换算与可比性**——1 Eh = **627.5094740631** kcal/mol（同 `run_strict_recovery_search.py` 用值）；
   GFN2 能量只在**同一 level/电荷/多重度**下可比，判定器须**显式断言**（两套池都带 `charge`/`multiplicity` 列，
   P4 任务的 `$chrg/$spin` 取自权威账本）。
3. **收敛判定**沿用既有两条件：`.xtboptok` 存在 ＋ `xtbopt.xyz` 非空 ＋ 日志含
   `GEOMETRY OPTIMIZATION CONVERGED`（`run_strict_recovery_search.py:194` 口径）。
4. **去重与身份**——等价原子映射下的重原子 RMSD ＋ 拓扑签名（项目约定 1.3× 共价半径，`run_batch.RADII`；
   签名 = 逐片段原子组成排序），与**已登记池**逐个比对；**等价性判定应复用聚合器的 `dedup_members`**
   （WL＋回溯），不要另写一套映射；身份漂移**独立登记**、绝不改名塞回原态（红线）。
5. **另注**：唯一会算 `rel_kcal`/`rmsd_to_nearest_known_a` 的 `run_strict_recovery_search.py`
   **结构上无法处理 `LiM_2plus`**——它的 `POOL_CSV` 就是上表那个只有 M/M_plus 的池，且
   `_state_charge()` 在缺池行时**直接 `SystemExit`**。这独立佐证了「必须有新判定器」。

**原型已就绪（机器本地层，未登记进生产包）**：`work/_p4_screen_triage.py`
——实现上述规格 1–4，并**双源交叉校验**能量（stdout 的 `| TOTAL ENERGY … Eh |` 与
`xtbopt.xyz` 第 2 行的 ` energy: …`，两者差 >1e-6 Eh 即记为 problem）。**等价性不再另写映射**：
直接复用聚合器的原语与同一容差（`bond_adjacency` + `find_topology_mappings`（WL＋回溯）→
heavy Kabsch RMSD < `DUP_RMSD_A=0.35` → 最差扭转 ≤ `TORSION_TOL_DEG=10.0` → Li 供体位点 →
镜像/手性），**但不做** `dedup_members` 那步「按 G 排代表」——筛选层还没有自由能，
硬套会把 GFN2 当生产自由能（红线），故生产层判定仍归聚合器。
`--selftest` **19/19 通过**（含「刚性副本判为同一极小（RMSD≈2.6e-16）」「断拓扑被拒」
「有收敛签名但无能量 ⇒ `technical_incomplete`」「双源能量不一致被记为 problem」
「如实报告复用原语与容差」「序列化与键序无关」）；对真实包空跑得 **8 元素全部 `not_run_yet`**；
`--json` 写入 + `--check` **连跑两次字节一致**；跑后 293 项包审计仍全绿（**对包只读**）。
**判定器已提升进生产包（2026-10-25）**：`scripts/wp_production/build_p4_screening_adjudication.py`
—— 早先的机器本地原型 `work/_p4_screen_triage.py` 已按项目纪律完成**四处登记**
（`docs/65_repo_layout.md` §3.1 + 计数句 `85`/`79`、`scripts/wp_production/README.md` 条目、
`tests/test_wp2_cost_semantics.py` 的计数），并由登记类测试强制覆盖（`test_scripts_index` / `test_repo_layout` /
`test_wp2_cost_semantics` 共 22 项全过）。**注意**：从 `work/` 复制到 `scripts/wp_production/` 后，
`REPO` 解析必须按该目录惯例改成 `HERE = Path(__file__).resolve().parent; REPO = HERE.parents[1]`
（原型的 `parents[1]` 在新位置会算成 `scripts/`，**所有路径都会错**）——已在提升时修正并复测。
**尚未实现**：把等价结论按 `coverage_route()` 的 `novelty` 约定接成 **route/verdict**
（这一步需要真实筛选结果才能验证）。

### 5.2 「结果落地当天」可执行清单（每步命令 + 预期输出；接口均已实测核对）
> 下列命令的**存在性与接口**已逐条核对（`--help` / 源码），但**只在授权到手后才执行第 0–1 步之后的提交动作**。

| 步 | 动作 | 命令 | 预期输出 | 是否触科学 |
|---|---|---|---|---|
| 0 | 提交筛选轮（**需授权**） | 见 §1 第 5 条（受保护提交器 + `--attempts-ledger`） | 数组 JobID（记进 `submission_journal.json`） | 是（提交） |
| 1 | **回收**（逐元素） | `.venv\Scripts\python.exe scripts\wp_production\ensemble_hpc_io.py --package work\hpc_four_state_p4_xtb_screening_v1 --job-id <数组JobID>` | 每元素一行：`verified <ID>_<i> N artifacts`；未结束的元素打印 `pending <ID>_<i>: no terminal accounting evidence` 并跳过 | **否**（只读远端 + 落快照；**不跑化学、不提交、不删证据、不覆盖已有快照**） |
| 2 | **判定**（元素级事实） | `.venv\Scripts\python.exe scripts\wp_production\build_p4_screening_adjudication.py --package work\hpc_four_state_p4_xtb_screening_v1 --json work\_p4_triage_out.json` | 每元素 `status ∈ {adjudicated, technical_incomplete, not_run_yet}` + `rel_kcal` + `window_verdict` + 与已登记极小的 `equivalence` | 否（只读解析） |
| 3 | **四态分流** | 按步骤 2 的 `equivalence` / 窗口结果落到 `coverage_route()` 的 route：新盆地→`multi_basin_coverage`；回已知盆地→`known_basin_reproduction`；身份漂移→独立登记；八条均无→`search_exhausted` | 逐态 route + verdict（词表见 `strict_readiness_wiring.COVERAGE_ROUTES`） | 否（但**这是决策点**） |
| 4 | 建**生产包**（每态 ≤2 起点 + ≤1 补救） | `python scripts\wp_production\build_production_ensemble_manifest.py --build-packages <DIR> --chunk 18 [--register-recovery]`；恢复腿用 `import_ensemble_structures.py --build-recovery-strict-reopt / --build-recovery-continuation / --build-strict-recovery / --build-li-round2-legs [--recovery-batch 1\|2]`；修补包用 `build_torsion_probe_package.py --repair-original-batch <批次号> --source-package <原包> --out-package <新包>`（**`--out-package` 是必需项**，缺它会直接 `ap.error`；`--source-package` 默认即原包） | 新目录中的任务清单 + manifest | 否（只建包） |
| 5 | 提交生产包（**需授权**） | 同 §1 第 5 条（ORCA profile 4 核 / 24 h；`%pal nprocs` 必须等于分配核数） | 生产批次 JobID | 是（提交） |
| 6 | 回收 + **QC** | 先 `ensemble_hpc_io.py`；再 `import_ensemble_structures.py`（同源几何/Hessian、正常终止、SCF、五阈值、零虚频、身份） | 结构表新增行；QC 失败的腿**不得**计入验收 | 否 |
| 7 | **只经四段流水线**更新接受状态 | `build_coverage_reviews.py` → `build_production_ensemble_aggregator.py` → 下游重建 | `production_ensemble_labels.csv` 变化；`strict_readiness_wiring.py` 重算 | 否 |
| 8 | 重跑 WP5 | 先 `build_wp5_target_pool.py` 核对 A/B 各 12 `qc_complete_pair=True`，再 `run_wp5_AB_replay.py` | 32 组端点 + 停止预算判据 | 是（重算，可复现） |

**每步纪律**：`git status` → **逐路径** `git add`（禁 `git add -A`）→ 长流水线同步执行 + 长超时；
**链一旦启动，就把它会生成/校验的文件整块让出**（多会话同工作树）。