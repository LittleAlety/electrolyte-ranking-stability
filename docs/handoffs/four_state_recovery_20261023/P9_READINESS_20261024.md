# P9 就绪报告（2026-10-24）

> 本文件按计划的终验口径，**分别**报告三个状态，**不压成一个"完成"**。
> 一切数字都是本文件生成时从产物实测得来，并给出可复核路径；不含预测值。

## 一、三阶段终态

| # | 阶段 | 状态 | 依据 |
|---|---|---|---|
| 1 | **四态科学恢复** | **未达成** — 系综 **44 accepted / 4 limited** | `outputs/physics_completion/ensembles/production_ensemble_labels.csv` |
| 2 | **正式研究闭环** | **部分达成** — 成本来源已闭合；**WP5 全 12 分子未达成**（A=11 / B=9 子池）；WP3 阶梯 **10 computed + 2 screen-only** | 见 §三 |
| 3 | **工程可复现性** | **已核验通过** | 见 §二 |

**"48/48 不是项目完成按钮"**：即使第 1 项达成，也仍需第 2 项的各项独立验收。

## 二、工程可复现性（已核验，全部可复跑）

| 检查 | 实测结果 | 命令 |
|---|---|---|
| 收口链 | **79/79 步 exit 0**，末行 `OFFLINE CLOSURE GREEN`（**核验于 HEAD `001cfad`、`CHAIN_EXIT=0`**；此前每个提交各跑过一次同样全绿） | `pwsh -NoProfile -File scripts/wp_production/finalize_wp2.ps1` |
| 只读检查无写盘 | **逐文件 `(size, mtime_ns)` 不变**（含失败路径） | `pytest tests/test_checks_are_read_only.py -q` |
| **干净环境复现** | 仅跟踪文件（无 `work/`）的检出跑全量：**0 failed**（**核验于 HEAD `d2f8aa5`、`PYTEST_EXIT=0`、`FAILED` 计数 0**；此前 `06d08aa` 同样 0 failed，该步可随时复跑），跳过均带显式理由（9 个） | `git worktree add --detach <tmp> HEAD`，再在该树跑 `pytest tests` |
| 冻结清单复算 | 三个周清单 **CHECK OK**（**核验于 HEAD `001cfad`**，链内 `refreeze-week1/2/3` 三步 exit 0；真树 external=0；干净克隆把 18 个**有意 gitignore** 的 `.cpcm/.property.txt` 记为 `external_machine_local` 而非 `missing`） | `refreeze_manifest.py --manifest outputs/weekN/SHA256SUMS --check` |
| 归档复算 | `[manifest] OK`；账本逐字段 **300 处比对 / 不符 0 / sha256 不符 0 / 归档缺条目 0**（**核验于 HEAD `001cfad`**，链内 `archive-verify` exit 0） | `verify_archive.py --latest --ledger --gate-when-complete` |
| `git diff --check` | 干净（无空白/冲突标记） | `git diff --check` |
| 未提交状态 | 仅并行会话的 `docs/handoffs/wp5_formal_replay_guard_20261023/README.md`（他人所有，不并入） | `git status --porcelain` |

**本阶段修掉的真实缺陷**：① 冻结清单把"有意忽略、从未入库"的文件判成"缺失" → 干净克隆永远红（改用 `git check-ignore` 语义分层，**"应发货却缺失"仍响亮失败**）；② 约 50 个"把 gitignored 的 `work/` 当输入"的测试改为**声明式跳过**（锚 `work/wp2prod`，因 `work/` 会被测试自己创建）；③ 站点指向 gitignored `work/` 的**死链**与过期的测试计数。

## 三、四态与正式研究闭环（未达成的部分）

### 3.1 四个 limited 态（逐态一行）

| 态 | 覆盖分级 | 失败机制 | 可用独立起点 |
|---|---|---|---|
| `DMC/M_plus` | `unresolved_qc` | `verytight_convergence`（各仅 1 次真实计算）+ `strict_reopt_required` | 登记二面角 10，已合法探 3，**7 个从未被合法探过**；去重后 **2 个不同重骨架操作**（heavy 0.2743 / 0.2432 Å）+1 甲基转子 |
| `DMC/LiM_2plus` | `unresolved_qc` | `max_cycles_exhausted` / `strict_reopt_required` | 7 候选中 2 接受（heavy 0.4874 Å）+**5 个声明式 Li 配位探针**（0.15/0.30/0.45 Å） |
| `DOL/LiM_2plus` | `search_exhausted` | **筛选级单盆地**（复核原文：是筛选层的物理发现，不是预算失败） | **0 个登记扭转**（五元环刚性）；`c05` 是加权成员且已 QC 通过 |
| `EC/LiM_2plus` | `search_exhausted` | `imaginary_modes` 2 次已尽；两条原登记 `tors_*` 是 **C=O 伪扭转**（1.186 Å，被单键门拒收） | **0 个登记扭转** |

**几何事实（不是预算问题）**：环 pucker 的合法位移只有 **0.02–0.08 Å**，远低于项目自己的 0.35 Å 盆地分离规则；把振幅放大到能到达别的盆地（±0.60/±0.80）会**把环键拉断**（实测被 `ring_broken` 拒收）。故 DOL/EC 的大位移只能来自**声明式 Li 配位探针**。

### 3.2 已就绪但**未提交**的下一步（P4 筛选轮）

| 项 | 值 |
|---|---|
| 包 | `work/hpc_four_state_p4_xtb_screening_v1` |
| 任务 | **8 个**（每任务 `geom.xyz` / `job.inp` / `cores.txt` / `inputs.sha256` / `candidate.json`） |
| 资源协议 | **`xtb_screening_v1` = 2 核 × 2 h**（核心计划的协议口径，**不接受按 core-hours 乘积等价**） |
| 预算 | **32 core-hours**（上限：筛选 ≤32 / 首产 ≤512 / 有因补救 ≤256，合计 ≤800） |
| 门 | `candidate_gate_contract=validate_candidate_start_v2`；`PACKAGE_SHA256SUMS` + 确定性重建锁 `selection.lock.json` |
| 状态 | **`submitted=false`**，`submission_gate=HOLD` |

**未提交的原因**：计划文本自带的一次性限额授权明确「**只有你作为用户把它发送到 Harness 会话，它才构成指令**」，而该授权尚未发出。**工程就绪 ≠ 执行授权**。

**本轮复验（2026-10-26 深夜，授权轮前最后一次对当前输入核对）**：`--check-p4-screening` → **`P4 SCREENING PACKAGE OK`（exit 0）**；包级 `PACKAGE_SHA256SUMS` → **46 条全 OK / 0 FAILED**；**8 个叶子任务**（`tasks/<mol>__<state>/<probe>/`，即 4 态 × 2 探针）逐个 `inputs.sha256` → **各 4 OK / 0 FAIL**（合计 32 个文件核对全过）。⇒ **包与当前磁盘输入仍一致，授权一到即可过门**（不是"曾经一致"）。

### 3.3 其余闭环项

| 项 | 状态 |
|---|---|
| 电子身份 | **80/80 verified**（FMOPop 正式 Löwdin 口径；HOMO 侧 Li 全部 <0.01，LUMO 侧 34/80 由 Li 主导，12 分子无一例外） |
| 成本来源 | **已完成**（原第 3 缺口：上游已声明的 `cost_scope` 接出到台账，13→14 列，`cost_status`/`core_hours` 一字未改） |
| 采样差异（3→6） | **只报差异、不判收敛**；容差已冻结 0.10 kcal/mol（依据 B，评价新批次之前冻结） |
| WP3 阶梯（flip persistence） | **12 格 = 10 `computed` + 2 `computed_screen_only`**：6 个 rung × 2 对（`EMC|GBL`、`EMC|SL`）全部出数，**`R4`（生产系综级）两对均为 `computed`**；`R4_screen` 仅筛选级，明确标注 NOT the production value。**⚠ 此前"R4 停在 8/12、EMC 两对永久 limited"的口径已过时**——那是 `EMC|M_plus` 放行（41/48）之前的结论，放行后这两对即可计算 | `outputs/physics_completion/closure/flip_persistence.csv`（逐行 `status`） |
| WP5 正式验收 | **未达成**：正式池是 **A=11 / B=9** 子池（≠ 全 12），32 轴中 19 轴有停止预算；`wp5_full_target_pool_evaluated` 仍 False。专项复核 7/7 PASS（含"接口不泄标签""仅正式模型驱动"），但**复核通过不等于全池验收** |
| WP6 / 扩池 | **未触发**（需 48/48 + Li 配对 ≥9/12）；其计算**需各自独立预算，不从 800 偷支** |

## 三之二、独立挑战者交付物（证据目录索引）

本轮的**独立复核**由多个执行者并行产出，各自只写自己的新目录、不改生产代码。**它们报告的是发现，不是完成**：

| 目录 | 内容 | 与本报告的关系 |
|---|---|---|
| `audit_gate_20261023/` | 候选预检门序与 P3 生成器的 **70 项独立挑战**（探针可复跑、两次运行 byte-identical）：门序 14 项攻击**零误放行**、12 个判据分支**全部可触发**、P3 计数逐格复现；报出 **D1**（`select_candidates(max_keep)` 静默丢弃候选）与 **D2**（`rotated_bond` 负索引绕过 `malformed_input`） | 两个缺陷**均已修并入库**（见 `build_torsion_probe_package.py` 内联注释） |
| `audit_claims_20261023/` | 7 条对外声明的独立复核：4 证实 / 1 部分证实（历史口径）/ 2 未证实 | 其"未证实"两条已收口：① 闸门口径统一为 **2 缺口**；② 链恢复到 **79/79** |
| `agent_a_candidate_review/`、`agent_d_fix_review/` | 候选层与修复层的独立复审 | 由对应执行者维护；**并入前须由 Lead 复跑**（本报告不为其结论背书） |

**读法**：这些目录里的探针**退出码非 0 是常态**（表示"发现了与声明不符之处"），不等于项目失败也不等于完成；
判定以 §一/§二/§四 的产物推导为准。

## 四、严格总闸门（逐项，机械推导）

| 检查 | 结果 |
|---|---|
| `ensemble_not_48_accepted` | **False**（44/48） |
| `wp5_full_target_pool_evaluated` | **False**（A=11/B=9 ≠ 12） |
| 其余必需项（覆盖复核 / 身份 / 采样审计 / WP3 证据 / 成本来源） | **True** |
| **`blocked_by`** | **`["ensemble_not_48_accepted", "wp5_full_target_pool_evaluated"]`（2 项）** |

推导来源：`scripts/wp_production/strict_readiness_wiring.py` 的 `derive_checks()` + `strict_readiness.py` 的 `strict_readiness()`（README 顶部同一口径，异常时写"无法判定"，**绝不默认通过**）。

## 四之二、本轮（2026-10-24）清掉的「会静默误导」缺陷（各附 commit）

> 共同形态：**产物里印出无法核对的内容**——数字没有出处 / 口径与冻结条款相反 / 状态断言超出判据。处置一律**改生成器**（不手改产物）+ 让文案只陈述可核对的字段，并**把旧错误措辞做成反向断言**。

| commit | 缺陷 | 修法 |
|---|---|---|
| `f1c0483` | 预注册稿写「搜索级（GFN2，**本机**）」，与**五处**冻结条款 + 计划正文「**只在 Slurm 计算节点**」相反（且明令禁止本地 `xtb.exe`） | 改为 Slurm 口径并**逐条点名依据**（`GOAL.md:49` 等） |
| `e874ab3` | 证据列断言「**64** 个独立起点…（**RMSD 0.0000**）」，而搜索池 CSV 只有 2 行（全是 `TMP\|M_plus`）⇒ 两数**全仓无出处**（`64` 真来源是索引 `protocol.num_confs_per_state`；逐态 RMSD 不存在） | 改读权威 `strict_recovery_v1_search_index.json`；无出处就写「未记录 / 不写 RMSD / 不得代写为 0」 |
| `efd02a6` | 恢复报告断言「**在飞补救（已提交、尚未产出结果）**」，判据却只有 `status=="pending"` ⇒ 那 2 条 EC 腿 `n_attempts=0`、**已被判 C=O 伪扭转并拒收**、队列为空、远端无 EC（**从未提交**） | 标题改「**pending 行**」+ 写明判据与边界（须与实时队列交叉核对、被拒收的登记行也会落在这里）；测试改反向断言 |
| `d2f8aa5` | `ROUTE_DECISIONS_P2.md` **S1**：代表几何写 frontier 风格路径、却配生产系综包的 sha（实测 `hpc_production_ensemble_r1_036-053/…` = `f0b2558e…` vs `hpc_frontier_localization_v1/…` = `079dd8b3…`）；**S2**：「7 个全部接受」（不带 `prior_starts` 的逐条合法性）被读成最终候选数 | S1：写全系综路径 + 新增「路径提醒」行点名易混树；S2：就地标注两口径并写明「**以带去重的那一行为准**」（P3 = 3 接受 + 4 `equivalent_start`） |
| `9de8590` | 冻结基线表被"用当前文件验证"会误判漂移 | 表头加防误读说明（快照 vs 当前值；判漂移须**同时点互比**；本包内相对路径按**包目录**解析） |
| `7be7273` | 包里自带 `PACKAGE_SHA256SUMS` 与逐任务 `inputs.sha256`，但**从未被执行过** | 本地**真跑三级**（生成一致性 / 包级 46 条 **0 FAILED** / 逐任务 **8/8**）并把命令+结果写进运行手册第 4 步 |
| 待提交（本轮） | `ROUTE_DECISIONS_P2.md` 另 **3 行**代表几何（DMC\|M_plus、DMC\|LiM_2plus、EC\|LiM_2plus）**只写了裸文件名、未限定所属树**——与 S1 同型 | 逐文件实测**三者的 sha 均属 frontier 树**（本态无同名系综副本），已补全 `work/hpc_frontier_localization_v1/tasks/…` 并注明实测 |

**同轮做的系统性清扫（避免同类残余）**：写了只读清扫器 `work/_sweep_path_sha.py`（**机器本地层**）把本包内**所有 sha 形式 token 与同行路径逐条配对核对**，并**按"文档自身目录 + 仓库根"两个基准面各试一次**。最终裁决（2026-10-24）：**12 处发现、0 处真缺陷**——`no-path` 9（提交 sha 与包内相对路径等参考资料式引用）、`mixed` 2（**对照行**同时引用冻结值与当前值，工具已把它与真不符分开）、`sha-mismatch` 1（冻结快照的**设计内**差异）。⇒ 该包**已无同类隐藏缺陷**。

**清扫范围已扩到另一个交付目录（2026-10-26）**：`docs/handoffs/wp5_formal_replay_guard_20261023/`（此前从未扫过）⇒ **0 处发现，且已自证不是空扫**：该目录只有 1 个 `README.md`、**sha 形式 token 数为 0**，即**根本不存在"路径+sha"这类断言**可核对（空扫的两种来源必须分清：**没有对象** ≠ **没有扫**）。工具已改为**接受目录参数**（`python work/_sweep_path_sha.py <dir>`），报告按目标目录命名，四态包回归仍为 **12 处 / 分类不变**。

**⚠ 工具的存放与可重建性**：该脚本在 `work/`（**gitignored**），换机器/干净克隆即不在。**若长期复用应迁入 `scripts/wp_production/` 并走「四处登记」**；在此之前，其要点足以重建：① 抓每行 `\b[0-9a-f]{16,64}\b` 与同一行反引号内的仓库相对路径；② 每个候选路径按「**文档自身目录**」再按「仓库根」各试一次；③ 判据三分——**行内无任何 sha 匹配 = `sha-mismatch`（真缺陷）**、**引用多个 hash 且至少一个匹配 = `mixed`（需人判）**、**行内无可解析路径 = `no-path`（登记待人工核）**；④ 只读，结果落盘 JSON。

**仍开放（需用户一个决定）**：仓库根下两个 `Permission denied` 的 pytest scratch 目录（`.pytest_tmp_wp2_optimizer`、`.pytest_tmp_wp2_stale_baseline`）——用 `diagnose-windows-sandbox-acl` 技能实测**连对象 ACL 都读不出**（`WinError 5`、Medium 完整性、unconfined 亦不提升）⇒ 病因无法证明；技能给**仓库根**补了缺失的 `WRITE_OWNER`（已备份 + 验证，回滚脚本在 `E:\Claude Code\电解液溶剂-HB\.dsh-coordination\acl-repair-20261024\`），重复原操作后**警告仍在**；仓库内**无引用**、**未被 gitignore 覆盖** ⇒ 建议**由用户在管理员 shell 删除**这两个目录（不删内容不可列的未知目录、不提权）。

**另一道待裁决的科学门**（不动冻结的 P4 计划）：筛选轮 4 个起点的几何风险——① 旋转轴非纯单键；② 位移后 Li–O<1.6 Å 无最小接触护栏。三选一：**原包提交 / 换冻结集合内的 offset / 预注册 v2**。

## 四之三、核心计划「逐项合规」的独立抽验（2026-10-26，只读）

台账 `outputs/physics_completion/compliance/plan_compliance.md`：**42 项**，状态分布实测为
**`satisfied 22 / partial 13 / exempt 3 / not_satisfied 2 / blocked_on_production 2`**。
本轮对它做了两项**独立于生成器**的复核（工具 `work/_audit_plan_compliance.py`，只读）：

| 复核 | 方法 | 结果 |
|---|---|---|
| **证据路径可解析** | 逐行取出「证据」列里的全部路径 token，核对**存在且非空**；`*`/`<占位符>` 模式按 glob 展开要求 **≥1 命中** | **75 条路径 / 0 问题** |
| **「实测」列可机械复算** | 对可复算的两项各自**从磁盘重新推导** | `wp1_method_audit_matrix` 声称 `computed=128 total=128` → **复现** ✓；`plan_main_figures_six` 声称 `figures=6 present=6` → 按其**声明的范围 F59…F64** 复算 → **6/6 present** ✓ |
| **未满足项不得无原因** | 要求 `not_satisfied`/`blocked_on_production` 的「实测」列非空 | **无空原因** ✓ |

**⚠ 如实记录：这套抽验的第一版报了 4 处 `missing` 与 1 处 `BAD`，经核实全是我的工具错**，不是台账的错：
① 把 **glob 模式** `work/wp2prod/**/<name>_<state>.json` 当字面路径（磁盘上实有 **169** 个 json）；
② 该路径含 **`<占位符>`**，字面 glob **构造上**零命中，须先把 `<…>` 折成 `*` 再展开；
③ `item_id` 单元格**带反引号**（`` `plan_main_figures_six` ``），未剥反引号导致按名查找失配、图表复算被**静默跳过**；
④ 图表那处我**自己编了个** `F5*_definition` 模式，而证据原文是**范围 `F59…F64`**（6 张）——应按**声明端点**复算。
⇒ **在该工具能覆盖的范围内，合规台账没有夸大**；同时再次说明"**先查核查工具自己**"是必须的一步。

**已委派两项互补的只读审计（结果尚未整合，不得当作结论）**：
① `docs/handoffs/wp5_formal_replay_guard_20261023/REVIEW_20261026.md`——对外层审计器（`AUDIT_ONLY`）的独立复审：它查什么、**能否被骗**（用本项目已发生过的**六类坏证据**当反例）、是否真只读、能否区分「证据没产生 / 没接线 / 存在未通过」；
② `docs/handoffs/four_state_recovery_20261023/audit_partial_items_20261026/REPORT.md`——对 16 个**未满足**项抽验：声称的阻塞原因**是否仍然成立**、有无**过时陈述**。
**两者都只是"发现"，须由 Lead 独立复跑核验后才并入结论**（零产物不计完成）。

## 四之四、对并行会话「验收链离线审计」的独立复核（2026-10-26，Lead 亲自复跑）

并行的另一执行者产出 `ACCEPTANCE_CHAIN_AUDIT_20261024.md`（G1–G5：容差同一性 / 五项数值强制 / **SCF 收敛此前无断言** / **6 kcal 筛选窗四处表示零守卫** / `coverage_route()` 三条 route 零数据零测试）。
按规矩**不由其作者自证**，我逐条复跑其**最能翻转结论**的三处：

| 其声称 | 我的独立复核 | 结果 |
|---|---|---|
| 新增 `RE_SCF_CONVERGED` 门（缺签名 ⇒ `scf_not_converged`） | `grep import_ensemble_structures.py` → `:252` 正则、`:904` 判定、`:908` 旗标 | **在位** ✓ |
| 筛选窗四处表示：三份 `WINDOW_KCAL = 6.0` + 一份 `ENERGY_WINDOW_KJ = 25.0` | 逐文件 grep（`build_production_ensemble_manifest:82`、`build_gap_decision_support:70`、`build_sampling_audit_3to6:59`、`screen_li_motifs:71`） | **逐行对上** ✓ |
| **加该门"不翻转任何现行接受状态"**（115/115 入池腿已带 SCF 签名） | 自写只读脚本 `work/_verify_scf_nodiff.py` 从 `production_ensemble_structures.csv` 取 `status ∈ {computed, ready}` 的腿，按其 `log_path` 逐条读日志匹配签名 | **`pool_legs=115 / signed=115 / 缺签名 0 / 日志缺失 0` ⇒ "no-flip holds"** ✓ |
| 三个新门测试在位 | 实跑：`-k tolerance` 1 ✓、`-k scf` 1 ✓、`-k "window or screen"` 4 ✓ | **通过** ✓ |
| 五份 RED/证明脚本 | `work/_threshold_guard_red.py`、`_tolerance_guard_red.py`、`_scf_gate_red.py`、`_window_guard_red.py`、`_scf_nodiff_proof.py` | **均存在** ✓ |

**意义**：该审计最关键的**诚实性论据**（"加门不会翻旧账"）经我**独立复算逐位成立**，故其新增的三道守卫可被当作**已复核的防线**（而非作者自述）。
**边界**：G5 的 route 覆盖率统计与其余散文陈述我**未逐条复算**（已上共享任务板 t1、成员 `g5-route-audit` 在做）；且该文件属**并行会话所有**，我**不代为提交**（其自身提交节奏由它掌握）。

## 四之五、WP5 外层审计器（AUDIT_ONLY）的 Lead 复审（2026-10-26，实跑 + 只读证明）

复审对象 `docs/handoffs/wp5_formal_replay_guard_20261023/audit.py`（413 行；自述 `IMPLEMENTED / AWAITING INDEPENDENT REVIEW`）。**四问逐条**：

| 问题 | 实测 | 结论 |
|---|---|---|
| **它到底检查什么** | `Snapshot` 只读层：`need()` fail-closed、路径逃逸拒绝、64 MiB 上限、CSV `strict=True` 拒短行、JSON 拒重复键与非有限数（`parse_constant`）、`finish()` 结束前**重哈希全部输入**防中途篡改。`check_inputs` 对固定输入集逐文件 SHA256 对账；`load_stop_rule` 只 `exec` **白名单 import**（`__future__/math/random/hashlib`）的纯标准库 helper，**从不导入回放器/模型代码**；`target_pools` 从 metadata 的 `in_main` 独立推导 12 分子、核对 48 态 label 集、`qc_complete_pair` 与 labels **实际重算比对**、B 任务 `Li=free+shift` 恒等式（≤1.6e-9 Eh） | 结构上覆盖了**此前发生过的六类坏证据**：缺键（`need` 抛）、单行自证（**对账外部 metadata**）、`not_computed` 带数（`stop_budget_status` 分语义）、`invalid_input`（`axis_of` 白名单拒）、NaN（`Decimal` 有限性 + JSON 拒非有限）、触发写死（`full_pool` 由 24 行实数据推导） |
| **退出码诚实吗** | 实跑两版：`knn_v1` → **exit 2**（`integrity=PASS`、`full_pool=BLOCKED`——子池 A11/B9 证据完整但非全 12，**不冒充全池**）；`model_v2` → **exit 1**（缺 `blind_replay_model_v2/AB_index.json` ⇒ `integrity=FAIL`，**fail-closed**，不因目录缺失而放水） | **诚实**：0/1/2 三分语义与 README 表逐字一致；结果恒带 `authority=AUDIT_ONLY`、`submission_gate=HOLD` |
| **真的只读吗** | 对 `outputs/` 全树做 `(size, mtime_ns)` 快照 → 前后 **changed=0 / added=0 / removed=0**；`__pycache__` 无残留（`-B` + `dont_write_bytecode`） | **严格只读** ✓（期间 F59–F63 图表 mtime 变化来自**并行会话**重生成，git 内容未变，与本审计无关） |
| **能否区分「没产生 / 没接线 / 未通过」** | `full_pool=BLOCKED`（子池证据完整、全池未齐）与 `integrity=FAIL`（证据本身缺失/对账失败）分列；`issues[].code` 机器可读（MISSING / STALE_INPUT_HASH / TARGET_IDENTITY / …） | **三种情形分开** ✓ |

**裁决：该审计器结构合格、退出码诚实、严格只读、语义可分**——达到「可考虑正式接线」的**质量门槛**；但**接线与否仍属用户裁决**（它仍是 `AUDIT_ONLY`；`model_v2` 目录缺失属**已知待补**，接线前须先补齐或明确只接 `knn_v1`）。所委派的复审成员零产出后已收回，本节为 **Lead 亲自复审**（首次实跑两版 + 全树只读快照证明）。

## 四之六、共享任务板审计线（t1–t6）的复核结论（2026-10-26，全部 Lead 独立复跑后采信）

并行工作面按「成员产出 → Lead 独立复算 → approve/接手收口 → 逐路径入库」跑完 **6 个任务，6/6 done**（t5/t6 于 2026-10-26 深夜收口；t5 实际作者 `p8-prereg-drafter`、t6 为 `submitter-bypass-audit`）：

| 任务 | 结论（证据目录已入库，commit `84e8ac7` / `ab69a90`） |
|---|---|
| **t1** G5 复核 | `audit_g5_route_coverage_20261026/`（6 文件 1836 行）。Lead 行号级核验全部与当前源码吻合：`coverage_route()` **`:163-223`，7 个 distinct route / 10 个 return**；route→verdict 映射 **`:357-375`**、`else: verdict="pending"` **`:373-374`**；`kept_evidence` 分支 **`:377-388`**；`strict_readiness_wiring.py` 的 `COVERAGE_ROUTES` 白名单 **`:167-168`**。CSV 实测 14 行 = `multi_basin_coverage 8 / search_exhausted 2 / single_basin_verified 2 / unresolved_qc 2`，**`known_basin_reproduction`/`pending`/`dedup_evidence_required` 三者 0 行**。**关键问题（route 名拼错的后果）用执行级证据回答**：emit 侧错拼 → 落 `else` → **两重后果**（verdict 由 `unresolved` 降为 `pending`，**且** `kept_evidence` 被清空、`duplicate_of` 证据丢弃）；方向 = **链级 fail-closed 阻塞**（wiring 响亮报 `unknown route`、闸门红），**不是放水**，但**本地误诊断**（"review still pending" 掩盖真实的 "unresolved + 证据已丢"）；`pending` 自身拼错（`pendingg`）行为不可见。守卫测试 `test_resolved_route_evidence.py` **对 emit 侧错拼会红、对 mapping 侧单独错拼不红**（靠 wiring 兜底）；**唯一残余风险 = 三处词汇副本协同改名**（全树无任何测试可抓，且恰好在三条零数据 route 上最易做不全）。该三点精化已被并行会话吸收进 `ACCEPTANCE_CHAIN_AUDIT_20261024.md`（commit `c5dbf37`「零测试→**零行为测试**；错拼同时清空 kept_evidence；方向分层」）——**本项目首例完整跨会话复核闭环**（提出→独立抽验→吸收落 commit）。 |
| **t2** 提交器 H1–H5 复现 | `audit_submitter_bypass_20261026/`。**两份独立实现各自 12/12 全绿、退出码 0、结论逐条一致**（成员完成版 `probe_output.txt` + Lead 接手版 `probe_output_final.txt`；竞态归属与真相记于任务板 review note，未改写历史）：**H2** `submission_resources:127` 缺 `resource_profile` → **静默降级 `orca_production_v1`**（cap 800/免账本），实测"提交成功、`budget_checked=False`"；**H2′** 真 xtb 输入的拒绝发生在 **doctor+mkdir 锁+squeue+rmdir 共 4 次 bridge 调用之后**；**H3** 篡改 sbatch（100 任务×16 核×24 h，潜在 38400 core-hours）仍 `budget_checked=True, reserved=32`，**`script_sha256` 与 manifest 声明不符却无人校验**；**H4** manifest 的 `task_count/cores_per_task/wall_hours/budget_cap` 全是装饰、profile 静默获胜；**H5** `submission_gate` 在提交器全文出现 **0 次**（`manifest.get(` 仅 `batches:100` + `resource_profile:127` 两处），manifest 写 HOLD 照常提交；**H1** `committed_core_hours:257` 跳过 `planned` 状态、`measured_core_hours="0"` 合法 → **两条路都把真实 20 h 成本抹成 committed=0**。**唯一有效守卫**：CLI `--budget-cap-core-hours` 与 profile cap 不符**在任何 bridge 调用之前**被拒（`:302-304`）。**并坐实无自动纠错通道**：`collect_sacct:159-170` 只取 JobID/State/ExitCode、**不取 Elapsed/AllocCPUS**，全仓无 `measured_core_hours` 生产写入点 ⇒ ledger 全靠调用方手填。**全程零集群、零网络**（C9 实测真实 spawn=0、bridge 路径 `E:\nonexistent\hpc.ps1` 不存在）。合成 `fixtures/` 已从跟踪移除（探针每次跑前须 `rm -rf`，否则残留 journal 造成"already submitted"假失败）。 |
| **t3** P8 预注册 | `p8_prereg_drafts_20261026/{WP6,POOL_EXTENSION}_PREREG_DRAFT.md`。触发条件逐条带**文件:行号**（核心方案 §14 `:386-392`、§5.2 `:127`、§13.5 `:382`、§15 `:402-403`；`计划.md:102/:115/:389-391`；`GOAL.md:85/:90`）；成本均值 Lead 现算**逐位吻合**（M 5.885 / M_plus 11.750 / LiM_plus 10.632 / LiM_2plus 12.434，60 腿 mean 9.864 / median 8.128）；扩池候选唯一指向已冻结 `extension_pool.csv`，**未发明分子**；两稿均声明「44/48 未触发——预准备非启动」与「预算与 800 core-hours 严格分离」。 |
| **t4** 双查（降级） | `audit_partial_crosscheck_20261026/`。抽验对象 `audit_partial_items_20261026/REPORT.md` **始终为 6 字节 "probe" 占位（mtime 冻结 15:22）⇒ 零产物不入库、其任务收回**；双查如实降级为"独立建 ground truth"：三方互证确立 `sampling_audit_3to6` 现值 **1 executable / 9 executable_partial / 6 sampling_limited**、**8 条 Li 腿全部执行**，据此**否定了旧背景假设**（"7/8 分割"与"EMC 两腿被过期父哈希挡在 2/1"）——两个更正已回写后续任务简报。 |
| **t5** compliance 17 行 | 原任务重发（带**路径级锚点** + **强制增量落盘**），`compliance/plan_compliance.md` 状态 ∈ {partial, not_satisfied, blocked_on_production} = **13+2+2 = 17 行**，逐行对生成器分支与当前磁盘实数三态判定。**✅ done**（入库 `555491d`；**实际作者 `p8-prereg-drafter`**——板上 owner 是 `compliance-partials-audit`，归属裁定见其 complete report）。 |
| **t6** §四之七 三缺陷第三方复核 | `submitter-bypass-audit`（`audit_ledger_defects_crosscheck_20261026/{REPORT.md, recheck.py}`，入库 `555491d`） | **✅ done+approve**。三处记录级问题（frontier 两口径 / `extension_rows=0` / `li_pair_complete` 两名一量）**独立重算全部确认**，42 行分布求和闭合、未满足 17 行数法复现 ⇒ §四之七 成**三方收敛口径**。它报的"唯一分歧"（frontier `status=parsed`）**经裁定不成立**（其 `recheck.py` 用 `"status" in col` 子串选列命中 `molden_status`；正确值 `computed`，见 `build_frontier_localization.py:370-371`），且该分歧一度被其写入我的记忆条目、已复核恢复。 |

**⇒ 对授权轮的直接影响（提交前强制人工核对清单）**：`budget_checked=true` / `ORCA TERMINATED NORMALLY` / 工程链全绿**都不能代替**下列核对（提交器自身不做，H1–H5）：
① manifest 的 `resource_profile` **必填**，缺失即停，不接受静默降级到 ORCA 800 池；
② 核数 / 墙钟 / `task_count` 与 **sbatch 脚本自身的 `#SBATCH --array/--cpus-per-task/--time` 三向一致**，并核对 `script_sha256`/`list_sha256`；
③ `submission_gate` / `submitted` 与**实时授权状态**人工对齐（提交器不读这两个字段）；
④ `attempts_ledger` 的每条 `measured_core_hours` **必须可追到 sacct 的 Elapsed×AllocCPUS**（无此链即不得放行，防"写 0 / 标 planned"抹账）；
⑤ 提交瞬间重验 `committed + reserved ≤ 800`，且运行/排队/拟提交均占额度。

## 四之七、合规台账的三处「记录级」问题定界（2026-10-26，t5 提出 + t6 三方确认；**均不翻转任何科学状态**）

抽验对象 = `outputs/physics_completion/compliance/plan_compliance.md` 的 17 个未满足行（42 行 = satisfied 22 / partial 13 / exempt 3 / not_satisfied 2 / blocked_on_production 2，求和闭合）。t4 双查已给出 **17/17 与台账一致、0 分歧**；本轮在其上加两处**显示/来源**定界：

| 缺陷 | 现象 | 实测边界（关键：**影响面到此为止**） |
|---|---|---|
| **① 口径覆盖不全** | 行 `wp2_state_identity_qc` 声称 `frontier_localization=not_computed`。该声称**与它自己的数据源一致**：`state_identity/state_identity_qc.csv` 的 `frontier_localization_status` **60 行全 not_computed**，`state_identity_acceptance.csv` 第 12 项 `frontier_localization_is_registered_not_guessed` 写明「生产输入未要求逐轨道原子组成」、ok=true ⇒ 状态维持 `partial`、**不是矛盾** | 但项目另有**同名不同口径**的 frontier identity 管线：`frontier/frontier_localization.csv` **80 行 computed**、`frontier_identity_evidence.csv` **80 行 verified**。台账**只引用前者、`证据` 列只写 `state_identity/`** ⇒ 读者据台账会误判「轨道定域/前端识别整体缺失」。**危害仅在阅读层，不改任何判据结果** |
| **② 计数读错来源文件** | 行 `wp5_pool_extension` 声称 `extension_rows=0`。根因：生成器 `build_plan_compliance.py:797` 在 `data/metadata/physics_completion_set.csv` 里筛 `cohort=="extension"`，而该文件 cohort **只有 main 12 / method_audit 8 / sampling_audit 4 / excluded 6**（**不存在 extension**）；已冻结扩展候选登记在 `data/metadata/physics_completion_extension_pool.csv` = **11 个候选、11/11 `FROZEN_NOT_COMPUTED`** ⇒ 这个 0 **不是「池里没有候选」，而是「读错了文件」** | **不影响扩池触发闸门**（已核源码 + 实跑）：`derive_pool_extension_trigger()` 只以 `wp5_full_target_pool_evaluated` 为前置、**不读该计数**，且实跑 `None→unknown / False→not_triggered / True→triggered`（由真实前置推导，非常量 False）；WP6 触发由 labels + Li 配对推导，同样不读。**残留风险**＝未来执行者/文档（含 P8 草稿引用该池）把台账的 `0` 读成「无扩展候选」。**状态仍应 `not_satisfied`**（未提交任何扩样计算、且扩池需各自预算） |

**Lead 的自我更正一并留档**（防历史载体误导）：我在 t3 的 `review_note` 里写过「extension_pool.csv **12 行** FROZEN、成员报告写 11 需对齐」——**那是我的计数错**（把含表头的文件行数当数据行数）；**草稿与成员报告写的 11 个候选才正确**。板底 note 与已推送 commit 属**不可改写历史**，不回写，以本条为准。

**③（本轮追加）同一个词 `li_pair_complete` 在两侧指不同的量**——`wp6_explicit_ligand` 行显示 `li_pair_complete=12/12 required_li_pairs=9 gate_ready=false`，而**触发闸门实际用的是另一个口径**：
| 侧 | 计算 | 当前值 |
|---|---|---|
| 台账显示 | `strict_main_counts(set_main, progress["scientific"]["accepted_legs"])` 的 `li_pair_ok`（`:170`/`:318`）＝**按「主态生产腿 accepted」计**（meta `scientific.accepted=48/48`，与系综 44/48 是两回事） | **12/12** |
| 触发判定 | `strict_readiness_wiring._complete_li_pairs(labels)`（**系综 labels 里 `LiM_plus` 与 `LiM_2plus` 双 accepted 的分子数**），与 `WP6_REQUIRED_LI_PAIRS=9` 比较 | **9/12**（缺 DMC / DOL / EC，各缺 `LiM_2plus`） |

**定界（第三方独立重放后修正本节的定论）**：成员 `p8-prereg-drafter` 只读重放 `build_plan_compliance.build_rows()`（不写盘，等价 `--check`），实测 `WP6 status=blocked_on_production`、`measured` 串与 CSV **逐字一致**（叠加 `--check` 字节一致 ⇒ CSV 无誊写错）。关键更正我原先的过头措辞：**两种口径的 Li 配对都已满足**（scientific 12 ≥ 9、labels 9 ≥ 9，**恰好压线**），因此 `gate_ready=false` **完全由 `production_ensembles=44/48` 这一半决定**——不存在我先前写的「把 12/12 读成满足会**低估缺口**」那种风险。真正残留的只是**命名可读性**：同一短语 `li_pair_complete` 在 wp2/wp6 行取 scientific ledger 分子分母（12/12），在系综行是 44/48，两个分母混在同一条 `measured` 串里；建议（待裁决项 3）把 `:838` 的串改为显式消歧命名（如 `li_pair_complete_scientific_ledger=`）。**状态判定不受影响，本项由 Lead 原判「记录级缺陷」下调为「命名可读性问题」**。P8 草稿引用的是 labels 口径（9/12），接线时仍需统一词义。

> **裁定（t6 第三方复核，2026-10-26 20:04）**：独立重算者报的「**唯一分歧**——`frontier_localization.csv` 的 80 行 `status` 实测为 `parsed`、Lead 写的 `computed` 值名不准」**不成立，是我的数字对、它读错了列**。盘上三重证据：① 同文件（`csv.DictReader`，80 行）四个含 "status" 的列并存 —— `status={'computed':80}`、`molden_status={'parsed':80}`、`fmopop_status={'parsed':80}`、`identity_qc_status={'verified':80}`；② 生成器 `build_frontier_localization.py:370-371` 明确 `row["status"] = "computed" if molden_status=="parsed" and fmopop_status=="parsed" else "parse_failed"` —— `parsed` 是**两个上游解析列**的值，`status` 列的派生值就是 `computed`；③ 根因在其自己的 `recheck.py:68-69`：`fc = [c for c in fl[0] if "status" in c.lower()]` 后取 `fc[0]`，而该文件列序是 `molden_status` → `fmopop_status` → `identity_qc_status` → `status`，**`fc[0]` 命中的是 `molden_status`，打印标签却写成 status**（其 §1.3 报的 `{'parsed':80}` 恰好等于 `molden_status` 的分布，互证）。⇒ **本节的 `80 computed / 80 verified` 保持不变**；该误读已责成其在 REPORT.md §1.3/§未覆盖 就地改正，**不把"更正 Lead"的错误断言留在交付里**（否则它就成了缺陷③同族陷阱的活样本：同文件多个近名列）。
>
> **同族教训（三方共犯）**：本轮三次踩在同一处 —— ① 我用 `Get-Content` 数出行数把 48 说成 50、把含表头的 12 行当 12 个候选（已更正）；② t6 在 §2 用**子串启发式**判断函数是否读 extension 计数，因 docstring 含 `wp5_pool_extension` 误报 True（它自己发现并自我更正，做法正确）；③ t6 又用**子串匹配选列**读错 `status`。**规则：读 CSV 一律按完整列名取列（`row["status"]`），禁止 `"x" in col` 反推列；判断函数行为只看签名 + 实跑，不看文本是否出现。**
>
> **本节作者的归属更正（重要，防误导后续读者）**：§四之七 的三处发现由 **Lead 独立重算 t5 的 17 行时**提出；随后**第一轮第三方**（`build_rows()` 内存重放 + 逐行现算）由 `p8-prereg-drafter` 完成，据此把 ③ 的定论修正为"命名可读性"；**第二轮独立复核**（自己的 `recheck.py`，函数签名+实跑）由 `submitter-bypass-audit`（t6）完成，**三处缺陷全部确认**。§四之七 现记录的是**三方收敛后的最终口径**，不再是单方结论。另记：`wp2_state_identity_qc` 的 `not_computed` 与 `wp5_pool_extension` 的 `extension_rows=0` 均**与其各自数据源一致**（第三方实测 `set.csv` cohort 取值集合 = {excluded, main, method_audit, sampling_audit}、extension 行 = 0；`sampling_escalation.csv` 24/24 仍 `registered_pending_round1_free_energy_check` ⇒ t4 时期疑的"过时陈述"**不成立**）；所以 **17 行的状态判定全部维持原样，零翻转**。

## 五、要用户裁决的事（其余都已就绪）

1. **是否发出一次性限额授权**（800 core-hours：筛选 ≤32 / 首产 ≤512 / 有因补救 ≤256；每态 ≤2 独立起点 + ≤1 有因补救）。
   发出后执行序：提交筛选轮（8 任务 / 2 核 × 2 h / 32 core-hours，活跃 ≤2）→ 回收逐文件哈希 → GFN2 判定（**6 kcal/mol 仅筛选层；全塌缩则按预注册分支如实填"零"，不伪称新极小**）→ 生产包 → P5 八项 QC → P6 只经 `importer→dedup→coverage review→aggregator` 更新 → P8 重算触发 → P9 终验。
2. **WP6 与新分子（8–12）扩池的计算启动**：属新增科学范围，**需各自的数值预算**，不得从 800 偷支。
3. **是否做台账的两处文字级改动**（均**不改变任何科学状态**，17 行判定零翻转）：(a) `build_plan_compliance.py:797` 的 `ext_rows` 改为读**真实候选来源**——注意 `extension_pool.csv` 是**独立文件、无 `cohort` 列**（第三方实测 `set.csv` cohort 取值集合只有 {excluded, main, method_audit, sampling_audit}），所以 `extension_rows=0` 在 set.csv 口径内**技术上没错**，问题在于台账用它表达「已冻结扩展候选数」，与 `extension_pool.csv` 的 11 个候选对不上，读者会误读；(b) `:838` 的 `li_pair_complete=12/12` 串改为显式消歧命名（两口径都 ≥9、不影响 `gate_ready`，纯可读性）。另有 §四之七①：`wp2_state_identity_qc` 的 `证据` 列只写 `state_identity/`，未点名 frontier identity 管线（80 computed / 80 verified），读者易误判"轨道定域整体缺失"。**我不自行翻判据、也不自行改判据文字**——尤其方向可能"变绿"的一侧。

**若第 1 项在 800 core-hours 或有界尝试内不能达成 48/48**，最可信的结论就是"四态仍有限制、还需要明确的新机制和下一轮预算"——而不是继续无限续算。这也保护现有 **44 个真实 accepted 标签**不被一次激进救援污染。