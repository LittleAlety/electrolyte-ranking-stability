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

**仍开放（需用户一个决定）**：仓库根下两个 `Permission denied` 的 pytest scratch 目录（`.pytest_tmp_wp2_optimizer`、`.pytest_tmp_wp2_stale_baseline`）——用 `diagnose-windows-sandbox-acl` 技能实测**连对象 ACL 都读不出**（`WinError 5`、Medium 完整性、unconfined 亦不提升）⇒ 病因无法证明；技能给**仓库根**补了缺失的 `WRITE_OWNER`（已备份 + 验证，回滚脚本在 `E:\Claude Code\电解液溶剂-HB\.dsh-coordination\acl-repair-20261024\`），重复原操作后**警告仍在**；仓库内**无引用**、**未被 gitignore 覆盖** ⇒ 建议**由用户在管理员 shell 删除**这两个目录（不删内容不可列的未知目录、不提权）。

**另一道待裁决的科学门**（不动冻结的 P4 计划）：筛选轮 4 个起点的几何风险——① 旋转轴非纯单键；② 位移后 Li–O<1.6 Å 无最小接触护栏。三选一：**原包提交 / 换冻结集合内的 offset / 预注册 v2**。

## 五、要用户裁决的两件事（其余都已就绪）

1. **是否发出一次性限额授权**（800 core-hours：筛选 ≤32 / 首产 ≤512 / 有因补救 ≤256；每态 ≤2 独立起点 + ≤1 有因补救）。
   发出后执行序：提交筛选轮（8 任务 / 2 核 × 2 h / 32 core-hours，活跃 ≤2）→ 回收逐文件哈希 → GFN2 判定（**6 kcal/mol 仅筛选层；全塌缩则按预注册分支如实填"零"，不伪称新极小**）→ 生产包 → P5 八项 QC → P6 只经 `importer→dedup→coverage review→aggregator` 更新 → P8 重算触发 → P9 终验。
2. **WP6 与新分子（8–12）扩池的计算启动**：属新增科学范围，**需各自的数值预算**，不得从 800 偷支。

**若第 1 项在 800 core-hours 或有界尝试内不能达成 48/48**，最可信的结论就是"四态仍有限制、还需要明确的新机制和下一轮预算"——而不是继续无限续算。这也保护现有 **44 个真实 accepted 标签**不被一次激进救援污染。