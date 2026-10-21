# WP2 生产系综 v1.4.2 执行与验收记录

更新时间：2026-10-19。本文件记录已落地的机制、实际排产与待完成的科学工作；Slurm 技术完成不等于 QC 或系综 accepted。

## 已落地的 P0 修复

- 生产去重按同一拓扑映射对 A/B 几何做正旋转 RMSD、扭转与 Li 给体位点联合比较。纠正旧的 B/B 自比较、直链误判环、预算耗尽默认 unique、浅镜像漏判。映射无法穷尽时阻止正式验收。
- 单成员也要求规范几何与 SHA256；同一态所有成员在去重前核验冻结电荷、多重度、方法/基组、AnFreq、协议、qRRHO、温度与有限自由能。运行时核验权重归一和 `0 ≤ G_min−G_ens ≤ RT ln N`。
- 聚合器 `--check` 只读重算并核验索引、来源文件与实际几何。compliance 使用这个检查及冻结48态键集合；无效时 WP2、WP6 和总闸门均不能数 accepted。收口链遇上游失败即停止，pytest 排除三个真实 ORCA/xtB 节点；真实集成测试只在超算进行。
- 新 Slurm 模板为每个 JobID/数组项/重启次数建唯一运行目录。回收通过 whu-hpc 命令桥，保存不可变快照、Slurm 记录、远端逐文件 SHA256 与本地收据。旧 `--fetch` 已禁用；导入器优先验证快照及其输入哈希，第三轮重优化登记为 attempt 3。
- **2026-10-19 新增（防重复排产）**：`import_ensemble_structures.members_in_flight()` 让「已提交但结果尚未导入」的救援包继续拥有其成员。没有这道门时，`--build-reopt` 会把 3725968/3725969 里的 12 个成员再打一次包，等于同一计算提交两遍并白花成员的唯一救援预算。只有当结构表里出现该成员该 attempt 的行（computed 或新失败）后，成员才重新可用。回归测试 `test_submitted_rescue_package_blocks_a_duplicate_rebuild` 钉死此行为。
- **2026-10-19 修复（limited 必须说明原因）**：聚合器原来只在 `len(kept)==1` 分支赋 `limitation_reason`，导致 DEC/M、DME/M_plus、EMC/M_plus 这类「2 个成员通过但 1 个预算耗尽」的 limited 态原因列为空——与 bug 无法区分。现改为：`n_limited` 命中即写 `rescue_budget_exhausted`（有界救援梯子用尽＝研究限制，绝不写成"该体系无极小值"）；单成员池写 `single_basin_pool`。回归测试 `test_every_limited_state_carries_a_nonempty_limitation_reason` 钉住「limited 必有非空原因」不变量。
- **2026-10-19 修复（未收敛腿也记录物种漂移）**：`candidate_bond_graph` 门原先只在收敛腿上执行，`max_cycles_exhausted` 在其之前短路——batch3 的 TMP/LiM_plus/c04、DME/LiM_2plus/c01、SL/LiM_2plus/c03 三条未收敛腿各自丢失了 1–2 条键（独立复核证实），但账本里 `candidate_bond_graph_ok` 留空。现把候选身份比较抽成 `_cand_identity()` 共享助手，max-cycles 短路前也调用：漂移证据照样入列（`qc_flags` 追加 `candidate_bond_graph_changed`），`failure_class` 仍是 `max_cycles_exhausted`（路由到 continuation 包的依据不变）。"跑完圈数"和"漂移成了另一个分子"是两种不同的失败，现在账本能同时记录两者。
- **2026-10-19 修复（flip ladder 第四态契约）**：R4 引入 `limited` 态（bounded-coverage：有数值、note 写明 NOT counted as computed）后，`test_computed_rungs_carry_a_value_and_uncomputed_ones_stay_empty` 仍按三态断言而误报。测试更新为四态契约：`limited` 必须带非空 `delta_ev` 且 note 必须含 "NOT counted as computed"；数值可见、状态不冒充。
- **2026-10-19 下午（reopt5 完成回收 + SL/c02 入账）**：`3726156_9`（SL/LiM_2plus/c02）终态 COMPLETED 后经幂等回收（前 9 份只验证、_9 新传输，SHA256 对账）；五要素全过，attempt=1 转 `computed`（strict_reopt_not_needed）。pending 清零：**computed 40/40、accepted=32/provisional=8/limited=8 稳定**（weights=71、去重=88）。主态四维早已全齐（48/48·12/12·12/12·12/12），**生产系综 32/48 是唯一主缺口**。
- **2026-10-19 下午（continuation 提交前物种身份门 + continuation4 新包）**：`build_dol_continuation_package()` 在选出最低能轨迹帧后新增身份比较——帧 vs 候选登记几何的原子序 + 冻结 1.3× 键图（Li 配位由同一键图覆盖）；不一致者以机器可读原因（`restart_species_drift` / `candidate_atom_order_changed` / `candidate_geometry_unreadable`）登记进 manifest 的 `pre_submission_rejections`，**绝不进 tasks.txt**。实测拦下 batch3 漂移的 3 项（TMP/LiM_plus/c04、DME/LiM_2plus/c01、SL/LiM_2plus/c03——各自丢 1–2 条键，与快照复核一致），其余 6 项合格建包 `continuation4`（6 任务）；原 `continuation3` 保留作证据、不覆盖不提交。3 条回归测试：漂移帧拒收 / 原子序改变拒收 / 完好帧接受（MaxIter-200 输入 + 全套 provenance）。设计依据：从漂移帧续算会"忠实重优化另一个分子"（EMC|M_plus/4 attempt-1 的教训），身份不可由重试恢复。
- **2026-10-19 晚（round-2 审计腿的跟随包）**：`import_ensemble_structures.py --build-r2-followup` 为未过 QC 的 round-2 审计腿建**恰好一次**跟随，分两类：`strict_reopt`（已收敛、频率/热化学完整、仅冻结 VeryTightOpt 阈值未达标，从该腿自己收敛末几何重启，提交前过原子序 + 键图身份门）与 `technical_retry`（段错误/异常终止等技术故障，输入**逐字节**复用并核验登记的起点 sha256，不扣救援预算）。跟随成员保留 `member_role=round2_audit_extra`，attempt N+1 才是 3→6 ceiling 通道聚合的那一行，旧 attempt 标 `superseded` 留证；谱系已有 2 次真实计算则拒绝。包 `hpc_production_ensemble_r2_reopt`（4 任务：DME|M|39、DME|M|5、DME|M|25 严格重优化 + DME|M_plus|55 技术重试）经受保护提交器单次提交＝**3728519**（array 0-3）；上传 tar sha256、远端逐任务 `sha256sum -c`（ok=8/bad=0）、4 核/24h、账户级 running+pending 均已在提交前核验。8 条回归测试（含「包能被受保护提交器加载」「篡改起点按 `snapshot_integrity` 拒」「第 3 次尝试被拒」）。
- **2026-10-19 晚（第二轮 Li motif 搜索已执行 + 实测池进 3→6 审计）**：`run_li_motif_round2.py` 执行预注册计划——对每个**磁盘哈希与登记值一致**的中性 M 盆地做替代父几何（不一致即 `parent_hash_stale` 拒用，不换父、不造结构），枚举规则复用 `build_li_motifs.py`、保留规则复用 `screen_li_motifs.py`（25 kJ/mol 窗口、同类重原子 Kabsch RMSD 0.35 Å、每腿 ≤3），每个保留 motif 与 round-1 保留结构逐对比，**只有真不同的极小**计入新盆地。8 腿 / 178 候选 / 35 秒 / 6 并发：**9 个新独立盆地**、5 次塌缩回 round-1、4 个父体被拒（EMC 两个父体磁盘哈希与登记值不符，两腿登记 `no_verified_parents`）。实测上限：DEC|LiM_plus 4、DEC|LiM_2plus 2、DME|LiM_plus **1**（36 候选全塌缩，受限是测出来的）、DME|LiM_2plus 3、TMP|LiM_plus **5**、TMP|LiM_2plus 3；EMC 维持 2/1。**TMP|LiM_plus 实测 5 > 登记上限 4**：登记上限是 `round1_kept + 已验证父体` 的**启发式**值（假设每盆地最多贡献一个新极小），单盆地可承载多个独立极小——报告一律用实测列，登记值不改。`build_sampling_audit_3to6.py` 新增 round-2 通道：Li 池取实测上限、round-1 计数用该腿真实保留数、核验不过的腿保持 round-1 池并注明原因。
- **2026-10-19 晚（登记纪律）**：在 `scripts/wp_production/` 新增脚本必须同步四处登记，否则收口链在 `check-*` 步骤红：① `scripts/wp_production/README.md` 逐脚本条目；② `docs/65_repo_layout.md` §3.1 表格；③ 布局里的硬编码计数（现 **51** 个跟踪文件：45 `*.py` + 4 `*.ps1` + 2）与 `tests/test_wp2_cost_semantics.py` 的 `{"all":51,"py":45,"ps1":4}`；④ 产物写进别人已有输出目录时，给那一层 `--check` 加**兄弟产物白名单**（例：`build_li_motif_sampling_plan.py` 的 `ROUND2_OUTPUTS`），否则被判 stray。
- **2026-10-19 夜（ceiling 聚合语义修正 + 第二轮救援包）**：`build_sampling_3to6_diff.py` 的 ceiling 侧原先**只聚合已登记的 round-2 成员**——这会把每条腿里最低的 round-1 极小全部丢掉，算出任何真实池都产生不出来的偏高 `G_ens`。现改为：ceiling 集合＝**round-1 极小（primary + computed extras）∪ 已登记且 QC 通过的 round-2 成员**，去重**直接调用聚合器的 `dedup_members()`**（拓扑映射 → Li 给体 → 重原子 RMSD → 扭转，不在报告层重述规则），塌缩成员记录在案但不重复计数；complete 行新增 `ceiling_note` 记录 `union of X round-1 and Y round-2 -> N unique`。同一轮还修掉 `state_rows` 里 `rows = []` **遮蔽同名参数**的 bug（它把空列表静默传给聚合，少了 round-1 成员且零报错）。真实数据干跑：DME/M 的 union = 5 行（primary+14+22 + 39/5），去重全部 unique，一旦 `DME|M|25` 通过即可聚合。**回归测试 6 条**，其中一条断言 ceiling 值精确等于 `g_min − RT·ln2`（只算新增会得到更高的值）。
- **2026-10-19 夜（r2 救援第二包 + 续算分支）**：`--build-r2-followup` 新增 `max_cycles_exhausted → 续算` 分支（从轨迹最低能帧重启、输入只加一行 `%geom MaxIter 200 end` 且只加一次、身份门照样先比原子序与键图），包名自动递增 `r2_reopt`/`r2_reopt2`，已提交包绝不覆盖。`r2_reopt2`（3 任务）＝DEC|M_plus|23 严格重优化、DME|M_plus|46 严格重优化、DME|M_plus|13 续算；`DME|M|25` 因谱系已有 2 次真实计算被拒（`rescue_budget_exhausted`）。**待裁决**：`DME|M_plus|55` 现为「1 次技术故障 + 1 次科学超差」，按现规则已到顶，DME/M_plus 的 ceiling 因此不可完整；宽限一次严格重优化需用户明确同意，未擅自执行。
- **2026-10-19 夜（EMC Li 池受限：诊断 + 已修复登记源）**：第二轮 Li motif 搜索里 EMC 两腿原为 `no_verified_parents`，根因是 `li_motif_plan_round2.csv` 的父体取自 `ensemble_raw_records.csv`（池文件重算前的记录：raw 记 −24.78265/−24.78204 Eh，rel 0.697/1.054 kcal），而磁盘 `work/sampling/EMC/M/{r2_c57,c14}/xtbopt.xyz` 现为 −24.86894/−24.86786 Eh（差 ~0.086 Eh），哈希必然不符——拒用是正确行为，错在登记源。**修复**：`build_li_motif_plan_round2.py` 的父体来源改为**已注册的冻结池 `sampling_conformer_set.csv`**（其 EMC 四行哈希与磁盘逐字节一致，DEC/DME/TMP 与旧计划逐字节相同，故对已完成部分零影响），计划重建后重跑执行器：EMC|LiM_plus 18 候选 → 保留 3、**新增 2 个盆地**（实测上限 4），EMC|LiM_2plus 18 候选 → 保留 2、**新增 1 个**（实测上限 2）；全 8 腿 214 候选、12 个新盆地、0 拒父、0 检查失败。**EMC 的 3 个新盆地只登记为 `round2_audit_candidates_deferred`**（理由：该分子的生产批未获批，注册会让 ceiling 永远等一条不存在的腿），其池实数进入采样审计：16 态现为 **1 executable / 9 executable_partial / 6 sampling_limited**；3→6 报告对 EMC Li 态给出「2 个盆地已测但未注册（无已批生产批）」的明确原因。


- **2026-10-20（提交纪律事故 + 三个包重提）**：`submit_hpc_batch.py` **只上传 sbatch 脚本、从不上传任务负载**——`r2_reopt2`/`r2_reopt3`/`r2_audit_li_emc` 三包直接提交后，远端包目录里只有 `.out` 与脚本，`tasks/` 与 `tasks.txt` 缺失，7 个 array 任务全部 `FAILED 00:00:00`（`ens-r1-*.out` 里写着 `sed: can't read tasks.txt`）。**修法**：按既有正确顺序先 `tar czf` → `scp` → 远端 `tar xzf -C <包目录>` → **逐任务 `sha256sum -c inputs.sha256` 全过** → 再提交；因 journal 拒绝重提同一 batch，改为 **batch 2**（manifest 增 `batch:2,count:N` 条目，`batch_2.sbatch`/`batch_2.txt` 与 batch 1 同源，顺手修掉 `r2_reopt3` 手工 sbatch 里 `date -u +%%FT%%TZ` 的双重转义）。重提成功：**3731145**（reopt2，3 任务）、**3731148**（reopt3 = 55 例外，1 任务）、**3731149**（EMC Li 三盆地，3 任务），实测立刻进入 RUNNING/PENDING 而非秒退。`submission.json` 如实登记 attempt0 失败原因与 batch-2 JobID。教训沉淀：**提交前必须核对远端包目录内 `tasks/`+`tasks.txt` 实际存在**，不能只看 JobID 是否返回。
## 当前计算与剩余顺序

1. **round-1 五批全部技术完成并已回收**：`3718293`（batch1 18项）、`3720638`（batch2 18项）、`3721460`（reopt3 9项）、`3723647`（batch3 18项）、`3725115`（batch4 3项）均已由 `sacct` 证实 `COMPLETED/0:0`，并经命令桥逐文件 SHA256 对账、以不可变快照回收（batch3 18/18、batch4 3/3，每项 7–8 个工件）。账户队列在回收完成后为 0。
2. **2026-10-19 重建账本**（导入器，含 batch3/4、reopt4 全部 10 项、reopt5 已完成的 2 项）：结构表 152 行 = primary `ready` 48 + extras `computed` 34 / `pending` 9 / `superseded` 47 / `technical_complete_qc_failed` 14。聚合器：48/48 标签、**accepted=29、provisional=14、limited=5**、weights=67、去重判定 82。旧 `accepted=18/48` 是 batch3/4 导入前口径，已过期。
   - **reopt4 实测战果（10/10 全部回收）**：8 项由「差一点没过 TolE」直接转为 `computed`（TMP/M/48、EMC/M_plus/4、GBL/M_plus/9、SL/M_plus/53、DMC/LiM_plus/c05、EMC/LiM_plus/c02、EMC/LiM_plus/c08、DEC/LiM_plus/c09），证明「从各自收敛几何重启」这条裁决在多数成员上一次到位；2 项补救后仍差 TolE（DMC/M_plus/28、AN/M_plus/10）→ 计入 `rescue_budget_exhausted`，不再重试。
   - **⚠ 新增 QC 门（2026-10-19，`candidate_bond_graph_changed`）**：`EMC|M_plus|4` 的 attempt 0 在优化过程中把 H8 从 C0 迁到 O4（C–H 1.122 Å → O–H 0.987 Å），attempt 1 从该几何「忠实重启」于是重优化的是**另一个分子**；但导入器原先只比「任务起点 vs 终点」，两次都判 `connectivity_ok=true`，这个物种漂移被静默接受为 `computed`。**修法**：导入器新增「候选身份」双粒度检查——① 冻结的 `connectivity_signature`（片段元素组成，能抓断键/Li 解离，抓不到片段内质子转移）；② **严格键图比较** `bond_graph()`（同一 1.3× 共价半径约定，逐键索引对），新增列 `candidate_species_ok` / `candidate_bond_graph_ok`。该成员据此改判 `technical_complete_qc_failed`，accepted 从 30 回落到 29 ——**这是一次真实的科学拒绝，不是回归**。回归测试 `test_candidate_bond_graph_change_rejects_the_leg` + `test_bond_graph_sees_a_hop_the_fragment_signature_cannot` 钉死两件事：这种腿必须被拒；片段签名确实看不见这种漂移。
3. **31 个未解决成员已全部建包（无遗漏、无重复）**：10 项 strict reopt + 2 项 continuation（`reopt4`=**3725968**、`continuation2`=**3725969**），10 项 strict reopt（`reopt5`=**3726156**），9 项 continuation（`continuation3`，**已上传校验，因配额未提交**）。每个成员只贡献一次统计权重，旧 attempt 保留并标 `superseded`；`rescue_budget_exhausted` 现有 4 个（DEC/M/3、DME/M_plus/14 属 reopt3 后仍失败；DMC/M_plus/28、AN/M_plus/10 属 reopt4 补救后仍失败），不再自动重试。
4. **配额实测与两次提交**：`reopt5` 首次提交被 `QOSMaxSubmitJobPerUserLimit` 拒绝（当时 12 活跃元素 + 10 > 20，**未创建任何作业**）；等活跃元素降到 6 后重提成功＝**3726156**。`continuation3`（9 项）此刻不能提交：队列 16 元素 + 9 = 25 > 20，等释放后直接 `sbatch ensemble.sbatch`，**不要重新上传**。
5. 3→6 审计（**round-2 Li 实测值已接入**）：16 个审计态里 `executable` 1（DME/M，池 6）、`executable_partial` **7**（DEC/M_plus、DME/M_plus、DEC/LiM_plus 4、DEC/LiM_2plus 2、DME/LiM_2plus 3、TMP/LiM_plus 5、TMP/LiM_2plus 3）、`sampling_limited` **8**（EMC/M、EMC/M_plus、EMC/LiM_plus、EMC/LiM_2plus、DEC/M、DME/LiM_plus、TMP/M、TMP/M_plus）。旧口径「13 个 sampling_limited、8 个 Li 态都要第二轮搜索」已被第二轮实测取代。用户 2026-10-19 决定：本轮先报告各态 `G_ensemble` 差异、氧化轴/Li 条件轴位移、Top-k 与 regret 变化，**暂不判采样收敛**；1.00 kcal/mol 只是 GFN2 筛选阈值，不得用于生产级验收；独立容差与稳定性判据须在后续评价前冻结。**ceiling 侧仍全部 `not_computed`**：池可用（筛选层）≠ 已登记且 QC 通过的第二轮生产成员，新盆地要转 accepted 必须另跑生产级 ORCA 腿（另一笔成本，需单独决定）。
6. **2026-10-20 00:10 队列快照**：三个救援包（continuation4 `3727606`、round-2 审计 `3727721`、round-2 跟随 `3728519`）**已全部回收入账**（round-1 extras 无 pending）；`3728918_[0-8]`（9 条 Li 新盆地生产腿）4 跑 5 排；`r2_reopt2`（3 任务：DEC|M_plus|23 严格重优化、DME|M_plus|46 严格重优化、DME|M_plus|13 续算）已建包，按纪律等活跃元素 ≤2 再提交。任一终态即幂等回收 → 导入 → 重聚合 → 整链重跑（本轮实测：导入器重建**字节确定**，两次运行 ledger 与 dispositions 哈希一致）。
7. QC→去重→系综→采样审计→WP3/WP5→compliance 顺序重建。WP6 仍需 Li 配对≥9/12（现 12/12）和系综 48/48 accepted（现 34/48）。所有 `--check`、归档复算和离线 pytest 通过后才讨论一次性一致性提交；现阶段不提交或推送。


8. **2026-10-20 00:20 队列快照（阶段转换：从「让第二轮腿跑起来」转到「回收验收 + 科学缺口」）**：`3728918_[0-8]`（9 条 Li 新盆地生产腿）**9/9 Slurm COMPLETED、已全部幂等回收、逐文件 SHA256 对账、导入完成**——但结果不是「9 项 QC 通过」：其中 0 项转 `computed`，9 项全部 `technical_complete_qc_failed`（DEC|LiM_plus|c13_c03 max_cycles、DEC|LiM_plus|c23_c03 差 TolE、DME|LiM_2plus|c05_c03 max_cycles、DME|LiM_2plus|c05_c05 差 TolE、TMP|LiM_plus|c27_c07/c27_c08/c48_c05 max_cycles 且**键图漂移**、TMP|LiM_2plus|c48_c00 max_cycles、DEC|LiM_2plus|c03_c03 strict_reopt_required）。`round2_audit_extra` 账本现为 computed 2 / superseded 4 / qc_failed 14 / **pending 3**（pending 正是 EMC 三盆地，已随 **3731149** 提交）。**已建但不得原样提交**：`r2_reopt4`（5 任务）由自动递增构建器产出，其中 DEC|M_plus|23、DME|M_plus|13、DME|M_plus|46 **与 `r2_reopt2` 重复**——只能取它独有的两条 DEC|LiM_plus 腿另建小包，禁止整包提交（重复排产会白花成员的唯一救援预算）。**3→6 ceiling 仍 16/16 `not_computed`**，`plan_overall_complete` 仍关。

9. **2026-10-20（独立科学 QC 复核：9 条 Li 腿逐项重推导）**：不依赖导入器的判定，直接读每条腿的不可变快照 (`job.log`/`job.xyz`/`job.hess`) 重算五个标记，与账本结论逐列对照，9/9 一致——
   
   | 成员 | terminated | converged | cycles | imag | hess | 账本判据 | 键图 |
   |---|---|---|---|---|---|---|---|
   | DEC\|LiM_plus\|r2_c13_c03 | ✓ | ✗ | 57 | 0 | ✗ | max_cycles_exhausted | 未变 |
   | DEC\|LiM_plus\|r2_c23_c03 | ✓ | ✓ | 31 | 0 | ✓ | verytight_convergence | 未变 |
   | TMP\|LiM_plus\|c48_c05 / c27_c08 / c27_c07 | ✓ | ✗ | 54 | 0 | ✗ | max_cycles_exhausted | **已漂移** |
   | DEC\|LiM_2plus\|c03_c03 | ✓ | ✓ | 48 | 0 | ✓ | strict_reopt_required | 未变 |
   | DME\|LiM_2plus\|c05_c03 | ✓ | ✗ | 51 | 0 | ✗ | max_cycles_exhausted | 未变 |
   | DME\|LiM_2plus\|c05_c05 | ✓ | ✓ | 46 | 0 | ✓ | verytight_convergence | 未变 |
   | TMP\|LiM_2plus\|r2_c48_c00 | ✓ | ✗ | 54 | 0 | ✗ | max_cycles_exhausted | 未变 |
   
   **没有任何一条腿带虚频**（0 条 `***imaginary mode***`）——9 条失败的共同原因是「撞优化圈数上限」或「只差冻结阈值」，而不是势面/频率问题；3 条 TMP\|LiM_plus 同时有键图漂移，重试无法恢复身份。这条独立复核把「作业 COMPLETED」与「QC 通过」之间的差距固定成可复查的证据，而不是靠导入器自证。
   
   **扩展到全部 round-2 行（21 行，按 attempt 逐行对齐它自己的快照）**：21/21 与账本判定一致，无一条矛盾。其中两条 `computed`（`DME|M|39`、`DME|M|5`）的 att1 快照都是「收敛 + hess 存在 + 0 虚频、cycles=1」——从各自收敛末几何重启后一圈即达标，正是 strict_reopt 的预期形态，不是空值充数；`DME|M|25` 的 att1 则是「日志收敛但**无 hess**」→ `abnormal_termination`（优化后崩溃、从未进频率段），`DME|M_plus|55` 的 att0 同样是「收敛但无 hess」→ 段错误，att1 才拿到 hess 并只差 TolE。复核脚本留在 `work/_audit_attempts.py`（按 `log_sha256` 把账本行钉到它自己的快照，避免用最新一次尝试的判定去比最早一次的日志）。


10. **2026-10-20（batch-2 首批终态：55 例外与 46 一次到位，两条仍在跑）**：`3731145_2`（DME|M_plus|46 严格重优化）与 `3731148_0`（DME|M_plus|55 **用户特批例外、末次尝试**）双双 COMPLETED 并回收导入——两条都是「从 att1 收敛末几何重启后一圈即达标」（`strict_reopt_not_needed`、cycles=1、hess 完整、0 虚频），**一次到位转 `computed`**。55 的例外就此**闭环**：att0 段错误（技术）→ att1 差 TolE 9.9e-7（科学超差）→ att2 一次到位；「最后一次尝试」的停止条件已用满，无论后续如何不再为该成员计算。`3731145_0`（DEC|M_plus|23）与 `3731145_1`（DME|M_plus|13）仍在 RUNNING（~22 min），`3731149_0/_1`（EMC 三盆地中的前两条）刚开始跑。**ceiling 通道如实响应**：DEC/M_plus 与 DME/M_plus 仍 `not_computed`（分别等 23 与 13 这两条在途腿），理由文案精确到成员——已通过的 46/55 没有让任何 ceiling 提前 complete，这正是「登记数≠通过数即不聚合」守卫的设计行为。round2_audit_extra 账本：computed 4 / qc_failed 10 / pending 5 / superseded 8。

11. **2026-10-20（DME|M_plus|13 续算后只差 TolE → 预算用尽；r2_reopt6/reopt7 拆包）**：`3731145_1`（DME|M_plus|13 的 MaxIter-200 续算）COMPLETED 并回收——五项阈值里**只有 TolE 一项未过**（energy change 4.858e-7 vs 冻结 2e-7，其余四项全过），ORCA 走 close-enough 路径收敛。按 2026-10-17 裁决这正是 `strict_reopt_required`（真实严格收敛缺口，补救=从末几何再严格重优化一次）；但该成员谱系已带 2 次真实计算（att0 max_cycles + att1 续算），构建器正确拒绝第三次（`rescue_budget_exhausted`）。**DME/M_plus 的 ceiling 因此定局为 `not_computed`**（登记 3：46✓、55✓、13✗ 预算尽）——与 DME/M（25 预算尽）同因。`3731145_0`（DEC|M_plus|23）仍在跑。
   同轮：`--build-r2-followup` 自动产出 `r2_reopt6`（6 任务），但其中两条 DEC|LiM_plus 腿与已预置的 `r2_reopt5` 重复——按拆包纪律取其独有 4 条建 **`r2_reopt7`**（DEC|LiM_2plus|c03_c03 严格重优化、DME|LiM_2plus|c05_c03 续算、c05_c05 严格重优化、TMP|LiM_2plus|r2_c48_c00 续算），`r2_reopt6` 放 `DO_NOT_SUBMIT.txt` 禁用；构建期拒绝 5 条如实记录在 r2_reopt6 manifest（13/25 预算尽；TMP 三条 LiM_plus 键图漂移不可恢复）。`r2_reopt7` 已 tar→scp→远端解包→逐任务 sha 4/4 通过，等队列 ≤2 一条命令提交。MaxIter 守卫复核：两条续算腿各恰 1 行、两条 strict 腿 0 行。

12. **2026-10-20（首个 ceiling complete：DEC/M_plus）**：`3731145_0`（DEC|M_plus|23 严格重优化）一次到位——收敛、**cycles=1**、0 虚频、hess 完整，转 `computed`。DEC/M_plus 成为**第一个通过全守卫的 ceiling**：round-1 G_ens = −264925.087287，ceiling G_ens = −264925.087314，**Δ = −0.000027 kcal/mol**（union of 3 round-1 + 1 round-2 → 4 unique minima）。3→6 扩样对该态排序的影响可忽略，且是守卫全过的完整聚合、非部分和。`ceiling_pending` 从 16 降到 15。
   **DME/M 的 ceiling 维持 not_computed 的精确原因**：登记 3（39✓、5✓、25✗）——25 谱系 2 次真实计算且第二次 `abnormal_termination`，按有界预算不再重试；守卫按设计拒绝部分聚合。同因定局的还有 DME/M_plus（登记 3：46✓、55✓、13✗ 预算尽）。**当前 8 个等计算的态、其缺口成员与在途/预置包的对应关系**：EMC|LiM_plus(2，3731149_0/_1 在跑)、EMC|LiM_2plus(1，3731149_2 在跑)、DEC|LiM_plus(2，r2_reopt5 已预置)、DEC|LiM_2plus(1，r2_reopt7)、DME|LiM_2plus(2，r2_reopt7)、TMP|LiM_2plus(1，r2_reopt7)、TMP|LiM_plus(3，**键图漂移已定局**——三条的跟随会被身份门拒绝，该态 ceiling 将以 species-drift 事实长期 not_computed，除非用户为它预注册全新独立起点)。EMC 三条 Li 腿预计本轮内出终态。

13. **2026-10-20（EMC 首两条出结果；r2_reopt5/7 提交；reopt9 预置）**：`3731149_0`（EMC|LiM_plus|c14_c05，46 圈收敛）只差冻结 TolE → `strict_reopt` 分支可救；`3731149_1`（c14_c00，50 圈撞顶）→ `continuation` 分支可救；两条身份干净（键图未变）。第三条 `3731149_2`（EMC|LiM_2plus|r2_c57_c07）仍在跑（2h+，LiM_2plus 全新起点偏慢正常，日志 mtime 实时更新确认非卡死）。
   **第三次跨包重复+拆包**：`--build-r2-followup` 产出 `r2_reopt8`（8 任务），其中 6 条与已预置的 reopt5（2 条 DEC|LiM_plus）/reopt7（4 条）重复——按纪律取独有 2 条建 **`r2_reopt9`**（EMC|LiM_plus|c14_c05 strict、c14_c00 continuation），reopt8 放 `DO_NOT_SUBMIT.txt`。reopt9 已 tar→scp→远端 sha 2/2，**等 3731149_2 出终态后与第三条 EMC 腿的跟随一起提交**（避免同分子抢并发位）。
   **触发 ≤2 纪律，两个预置包已提交**：`r2_reopt5` = **3731703**（2 任务）、`r2_reopt7` = **3731705**（4 任务），各自 `submission.json` 登记（headroom 19/17）。至此 DEC|LiM_plus 两条、DEC|LiM_2plus/DME|LiM_2plus×2/TMP|LiM_2plus 各自在途，**全部 8 个等计算的态中 6 个的在途/预置链完整**（其余 2 个=EMC LiM_plus 等第三条腿+reopt9、EMC LiM_2plus 等第三条腿；TMP|LiM_plus 三条键图漂移已定局不救）。子代理并行独立复核 round-2 账本一致性已启动。

14. **2026-10-20（子代理独立复核：27 行 round-2 账本与原始日志零矛盾）**：按用户「启用 agent 集群」指示，子代理对全部 round2_audit_extra 行做只读审计——26 个 job.log 的 sha256 全部唯一反查匹配、无多解。**结论：18 个非 superseded 非 pending 行的五标记与账本判定 100% 一致**——
   
   * 7 条 max_cycles（cyc=50–57）：均正常终止、未收敛、无 hess、0 虚频——「AnFreq never validated」自洽；
   * 2 条 verytight_convergence（cyc=31/46）：ORCA 自报收敛、hess 存在、0 虚频，账本按更严冻结 TolE 判未达标——逻辑正确；
   * 3 条 strict_reopt_required（含 DME|M_plus|13 att1 cyc=3）：close-enough 路径，五项里只有 TolE 为 NO（4.858e-7 vs 2e-7）；
   * 1 条 abnormal_termination（DME|M|25 att1）：日志确无 TERMINATED 字样、无 hess；
   * **5 条 computed（46/55/23/39/5）逐条验真**：正常终止+收敛+hess+0 虚频，cycles 恰为 1（first-point 形态），n_freq 与日志频数逐条一致，最低实频 39.15–65.29 cm⁻¹ 全为正。账本无空值充数。
   
   这份第三方复核与此前 `work/_audit_attempts.py` 的 21 行复核相互印证：**「作业 COMPLETED ≠ QC 通过」的账本口径经得起独立重推导**。唯一 pending（EMC|LiM_2plus|r2_c57_c07）无日志，与 3731149_2 仍在跑一致。

15. **2026-10-20（EMC 第三条也撞圈数；reopt9 重建为 3 任务并提交＝3731781——最后一个可提交跟随包）**：`3731149_2`（EMC|LiM_2plus|r2_c57_c07，跑了 2h09）COMPLETED——50 圈撞顶、正常终止、无 hess、0 虚频、键图干净 → `continuation` 可救。**至此 3728918+3731149 两批共 12 条 round-2 Li 腿全部回收完毕、逐项 QC、账本与日志经第三方复核零矛盾**。
   构建器自动产出 `r2_reopt10`（3 任务），其中 2 条与已预置 reopt9 重复——因 reopt9 **尚未提交**（无 submission.json），按纪律**原位重建** reopt9 为 3 任务全量（EMC|LiM_plus|c14_c05 strict + c14_c00/r2_c57_c07 continuation），reopt8/reopt10 各放 `DO_NOT_SUBMIT.txt`。MaxIter 守卫：两条续算腿恰 1 行、strict 腿 0 行；远端 sha 3/3 后提交＝**3731781**（headroom 14）。
   **排队现状**：3731703（reopt5，DEC|LiM_plus×2）RUNNING；3731705（reopt7，4 任务）2 跑 2 排；3731781（reopt9，EMC×3）PENDING。**全部 9 个可救 round-2 成员都已在途**（6 跑/3 排），无任何遗漏；三个禁用包（reopt4/6/8/10）留作构建记录。理论终局：若 9 条全过，ceiling 将达 complete 7/16（DEC/M_plus + 5 个 Li 态）+ DME/M 1 个（39/5 已过但 25 预算尽，受守卫约束仍 not_computed）。

16. **2026-10-20（第三批跟随全部回收：computed 10/27，ceiling complete 3/16；round-2 跟随链到此收官）**：3731703/3731705/3731781 三包九条腿全部 COMPLETED 并回收导入——
   
   * **一次到位（cycles=1，strict_reopt_not_needed）6 条**：DEC|LiM_plus|r2_c23_c03、DME|LiM_2plus|c05_c05、TMP|LiM_2plus|r2_c48_c00、EMC|LiM_plus|c14_c00、c14_c05，加此前的 DEC|M_plus|23、DME|M_plus|46/55、DME|M|39/5；
   * **几圈后仍差冻结 TolE（strict_reopt_required / verytight_convergence）5 条**：DEC|LiM_plus|r2_c13_c03（4 圈）、DEC|LiM_2plus|c03_c03（6 圈）、DME|LiM_2plus|c05_c03（13 圈）、EMC|LiM_2plus|r2_c57_c07（27 圈）——**这五条的谱系都已带 2 次真实计算，构建器全部正确拒绝第三次**（rescue_budget_exhausted）；
   * **TMP|LiM_plus 三条 att0 键图漂移**：身份门拒（restart_species_drift），不可恢复。
   
   **ceiling 现状：complete 3 / not_computed 13**——
   | 态 | 状态 | Δ (kcal/mol) |
   |---|---|---|
   | DEC/M_plus | **complete** | −0.000027 |
   | EMC/LiM_plus | **complete** | **−0.974119** |
   | TMP/LiM_2plus | **complete** | **−0.801113** |
   
   **EMC/LiM_plus 的 −0.974 是本项目第一个有科学分量的 3→6 差异**：扩样把 G_ens 拉低近 1 kcal/mol，说明该态 round-1 单极小确实低估了配位熵贡献；DEC/M_plus 的 −0.000027 则说明该态 3 结构已足够。两类结果都符合「先报差异、不判收敛」的口径。
   
   **13 个 not_computed 的最终归因（无遗漏）**：6 池耗尽（pool-limited）；2 预算尽定局（DME/M 的 25、DME/M_plus 的 13——登记数≠通过数守卫拒部分聚合）；3 TMP|LiM_plus 键图漂移不可恢复；2 等差 TolE 腿的第三次机会已被预算拒绝（DEC|LiM_plus、DEC|LiM_2plus、DME|LiM_2plus——各态登记的成员全部计算到预算上限）。**round-2 跟随链到此收官：没有任何成员还剩未用的救援预算，构建器产出空包（tasks=0）即证明。**
## 预算与停止条件清单（2026-10-20）

本周计划第 4 项要求把三类「新增计算」各自单列预算/停止条件，不混进已批准队列。以下数据全部取自当前账本与 `sampling_3to6_diff.csv`（不改任何判定）。

### A. 3→6 ceiling 的 16 个审计态：缺什么、怎样才能补上

| 缺失类型 | 态 | 精确原因（原样） |
|---|---|---|
| **池已耗尽（不是"在跑"、也不是登记遗漏）** | EMC/M(池2/R1 2)、EMC/M_plus(2/2)、DEC/M(3/3)、DME/LiM_plus(1/1)、TMP/M(2/2)、TMP/M_plus(3/3) | `pool-limited: the frozen pool holds N independent minimum(a) and round-1 already uses N, so no 3->6 extension exists` —— **冻结池里 round-1 已把每一个独立极小用光，3→6 扩样在现有池内不存在**；这不是登记遗漏，也不是等算力能解决的，要变只能先做新一轮构象/motif 搜索（改口径，须单独预注册） |
| **已登记但无一项 QC 通过** | EMC/LiM_plus(2)、EMC/LiM_2plus(1)、DEC/M_plus(1)、DEC/LiM_plus(2)、DEC/LiM_2plus(1)、DME/M_plus(3)、DME/LiM_2plus(2)、TMP/LiM_plus(3)、TMP/LiM_2plus(1) | `N round-2 member(s) registered, none QC-passed yet` —— 各自的分支已在 `r2_reopt2`(3731145) / `r2_reopt3`(3731148) / `r2_audit_li_emc`(3731149) / `r2_reopt5`(待提) 里 |
| **登记数 ≠ 通过数** | DME/M（登记 3、通过 2） | `registered round-2 members (3) != QC-passed members (2)` —— 唯一缺口是 `DME|M|25`，谱系已有 2 次真实计算且第二次 `abnormal_termination`，按规则**不再重试**，故 DME/M 的 ceiling 在本轮预算内**不可能** complete |

结论：**16 个 ceiling 里只有 10 个是"等计算"，6 个是"冻结池内没有扩样空间"**（上表第一行），再加 DME/M 的 1 条预算已尽。把 16/16 当作"再等几天就会好"的预期是错的。2026-10-20 已把报告文案改成两级：池耗尽写 `pool-limited: …`，真正缺登记才写 `no registered round-2 candidates`，两者不再共用一句话（回归测试 `test_pool_exhausted_reason_differs_from_a_booking_gap`）。

### B. DME|M_plus|55：一次、末次、有记录的例外

* 依据：用户 2026-10-20 裁决（att0 段错误属技术故障，不消耗科学救援机会；单列例外、沿用冻结阈值、设为该成员最后一次尝试）。
* 已提交：`r2_reopt3` batch 2 = **3731148**（1 任务，4 核，24 h 上限）。
* **停止条件（硬）**：无论结果如何都不再产生第 3 次真实计算；若仍差冻结 TolE（att1 实测 ΔE=9.9e-7 vs 阈值 2e-7），该成员登记 `rescue_budget_exhausted`，DME/M_plus 的 ceiling 保持 `not_computed`。
* 阈值处理：**不放松任何一项**（TolE 2e-7 / TolMaxG 3e-5 / TolRMSG 8e-6 / TolMaxD 2e-4 / TolRMSD 1e-4），"接近冻结阈值"不算通过。

### C. EMC 的三个 Li 新盆地：生产腿预算

* 依据：用户 2026-10-20 裁决（已测得的 3 个盆地从 `round2_audit_candidates_deferred` 移入正式注册，按配额提交）。
* 已提交：`r2_audit_li_emc` batch 2 = **3731149**（3 任务）。成员角色 `round2_audit_extra`，**不回溯改变任何 round-1 验收**。
* **停止条件**：每成员只有这一次生产腿；失败即记 `technical_complete_qc_failed` + 具体 `failure_class`，**不自动排下一轮**。三条都失败也不影响 EMC 的 round-1 结论（accepted 计数不变）。
* 成本口径（实测基准 p50 19 min / 均值 27 min / 最长 100 min，4 核）：3 条 Li 腿 ≈ 1–1.5 core-hour，4 并发下排队之外的墙钟 ≈ 20–60 min。

### D. 11 个 limited 态：默认不排，预注册才排

现有限制原因分布（账本实读）：`rescue_budget_exhausted` 10 个（DEC/M、AN/M_plus、DMC/M_plus、DME/M_plus、TMP/M_plus、DMSO/LiM_plus、DMC/LiM_2plus、DOL/LiM_2plus、EC/LiM_2plus、TMP/LiM_2plus），`species_drift_unrecoverable` 1 个（EMC/M_plus，重试无法恢复身份）。

* **默认**：不开全面新起点搜索（用户裁决第 3 条）。
* **允许开的口子**：只有当该态会改变关键排序或机制结论时才预注册，预注册必须写明三件事：① 起点来源（冻结池里的哪个盆地，逐字节哈希）；② 次数上限（每态 ≤2 个独立起点，与既有 §6.1 口径一致）；③ 停止条件（两条都失败即登记 `sampling_limited`，不再续）。
* 成本参考：每独立起点 ≈ 1 条生产腿（p50 19 min、均值 27 min、最长 100 min，4 核）；11 态若全开（22 腿）≈ 10 core-hour、排队之外墙钟 ≈ 2.5 h。**成本不大，问题在科学必要性**：这些态里多个已被前序审计判为"池本身受限"或"身份已漂移"，重开新起点属于改口径而非补证据。
* 需要用户逐态点名，不批量默认激活。

### E. 不在本清单内的（明确排除）

* 放宽冻结方法或阈值、判定采样收敛、commit/push：均不属本轮可自动执行范围。
* `r2_reopt4`：**已禁用**（3 成员与 `r2_reopt2` 重复），其独有两条 DEC|LiM_plus 腿已迁入 `r2_reopt5`；见 `work/hpc_production_ensemble_r2_reopt4/DO_NOT_SUBMIT.txt`。


## 本周终验（2026-10-20，第 5 项）

### 工程链（全部只读验证）

| 检查 | 结果 |
|---|---|
| `finalize_wp2.ps1` 不带 -Commit | **40/40 步 exit 0**，`OFFLINE CLOSURE GREEN`（本日累计 7 次） |
| 全部 16 个 `--check` | OK（含 sampling-diff 字节级复核） |
| 离线 pytest（排除 3 个 ORCA/xtB 活动节点） | **1710 passed, 8 skipped, 0 failed** |
| `git diff --check` | 干净 |
| 导入器/聚合器幂等 | 前轮已验证字节一致；本轮重建后 labels 48/48 稳定 |

### 科学状态（如实、分口径）

**主账本**：主态 48/48 ✅、四态 12/12、Li 配对 12/12；runtime 60/60。系综层 **accepted 34 / provisional 3 / limited 11**（分母 48，无静默缩小；round-2 审计腿按设计不参与 round-1 验收）。

**round-2 账本（27 行终态）**：computed **10** / technical_complete_qc_failed 9 / superseded 17 / pending 0。构建器产出空包（tasks=0）＝无成员剩救援预算的机器证明。队列已空。

**3→6 差异（本计划第 3 项的核心交付）**：ceiling **complete 3 / not_computed 13 / total 16**——

| 态 | Δ G_ens (kcal/mol) | 科学含义 |
|---|---|---|
| DEC/M_plus | −0.000027 | 3 结构已足够，扩样无影响 |
| **EMC/LiM_plus** | **−0.974119** | round-1 单极小低估配位熵贡献近 1 kcal/mol |
| **TMP/LiM_2plus** | **−0.801113** | 同量级实质差异 |

排序通道（Top-k / regret）按规则保持 `round1_only`：需要**全部**审计分子的 M 与 M_plus 两侧 ceiling 同时 complete 才比较，当前不满足（M 侧仅 DEC/M_plus complete、M 态 5 个池耗尽），空值不冒充。

**13 个 not_computed 的归因（可审计、无遗漏）**：
* 6 个**池耗尽**（pool-limited，round-1 已用光冻结池内每个独立极小）：EMC/M、EMC/M_plus、DEC/M、DME/LiM_plus、TMP/M、TMP/M_plus；
* 2 个**预算尽定局**：DME/M（DME\|M\|25）、DME/M_plus（DME\|M_plus\|13）——守卫拒部分聚合；
* 3 个**键图漂移不可恢复**（TMP\|LiM_plus c27_c07/c27_c08/c48_c05，身份门三次拒绝）；
* 4 个**差 TolE 腿的第三次机会被预算拒绝**（DEC\|LiM_plus\|r2_c13_c03、DEC\|LiM_2plus\|c03_c03、DME\|LiM_2plus\|c05_c03、EMC\|LiM_2plus\|r2_c57_c07——各 2 次真实计算后仍差冻结阈值，按 ≤2 规则停止）。

### 用户三项裁决的执行记录

1. **55 例外**：att2 一次到位 computed（cycles=1、0 虚频、hess 完整），末次尝试已用满——闭环。
2. **EMC 三盆地**：3 条生产腿全部跑完；2 条一次到位（c14_c05/c14_c00）、1 条两轮后差 TolE 预算尽（r2_c57_c07）。
3. **limited 不追 48/48**：未开启任何新起点；本轮唯一的例外（55）是用户点名特批。

### 本周五个计划项的完成度

| 计划项 | 状态 |
|---|---|
| ① 收证据（3728918 九项 + pending 查清 + 逐项 QC） | ✅ 12 条 Li 腿 + 7 条跟随全部回收 QC；账本经子代理独立复核与原始日志零矛盾 |
| ② 结算在途救援、不重复排产 | ✅ 4 次跨包重复全部拦截（reopt4/6/8/10 禁用）；9 个可救成员一次排齐全部跑完 |
| ③ 重建真实差异 | ✅ ceiling 3/16 complete、三个 Δ 数值交付；排序通道按规则留空 |
| ④ 新增计算单列预算 | ✅ 55 例外闭环、EMC 三盆地执行完毕、limited 清单在 §D |
| ⑤ 周末验收 | ✅ 本节 |

### 待用户裁决（默认不动）

* 差 TolE 的 5 条腿与 TMP\|LiM_plus 漂移 3 条：按裁决仅当改变关键排序才预注册新起点；**EMC/LiM_plus 的 −0.974 与 TMP/LiM_2plus 的 −0.801 已表明 Li 态扩样可以有近 1 kcal 的量级**，若用户认为值得对某个 not_computed 态追新起点，点名即按预注册流程（来源/次数/停止条件）单独立项。
* 全部改动未 commit；一致性 commit 时机由用户定。

## 失败处置判定链落地（2026-10-20 夜，用户对照报告建议项 1）

按用户「失败处置、3→6 差异和 WP5 盲回放接成可验收数据链」的方向，第一块已落地——**成员下一步处置从导入器内散落的 if/elif 提炼为冻结判定的纯函数**：

* 新脚本 `scripts/wp_production/member_next_action.py`（`next_action(row, attempts)`）：身份漂移（键图/物种/原子序）凌驾一切分支且**永不从漂移帧续算**；`abnormal_termination` 属技术故障**不扣救援预算**；预算按**去重后的 (attempt, log_sha256) 对**计数（重复提交永不双扣），两次即 `limited_rescue_budget_exhausted`——绝不写成「无极小值」；`strict_reopt_required`/`verytight_convergence` → `reopt_from_own_converged_geometry`；`max_cycles_exhausted` → `continuation_only_if_restart_identity_matches`；其余 `manual_review`。
* 测试先行：`tests/test_member_next_action.py` **10 项**钉死三条不可混淆分支 + 预算按去重对计数（首版确实按行数计数、被自己的测试当场抓出——同 attempt 同 log 的重导记录被当成了两次尝试，已修）+ 漂移凌驾 computed/technical 分支的优先级 + 重复提交拦截。
* 导入器 `production_ensemble_dispositions.csv` 生成段改为调用该路由器，legacy 词表（computed / species_drift_unrecoverable / rescue_budget_exhausted / unresolved_qc_failure / pending）经映射保留——**聚合器匹配门与既有 CSV 字节不变**：接线后重导，账本 27 行与 dispositions 全部一致（computed 43 / rescue_budget_exhausted 10 / species_drift_unrecoverable 4，与接线前逐字节相同），accepted 34/3/11 不变。
* 四处登记完成：README §3.1、docs/65 §3.1（计数 51→52、py 45→46）、test_wp2_cost_semantics（52/46/4 + 布局断言串）、无 stray 需要白名单（该脚本被导入、无独立输出）。
验证：import+next_action 测试 84 项全过；收口链重跑（本日第 9 次）。

## 多 agent 团队日收官（2026-10-20 夜）

用户指令「把所有内容做完再停下，请用多agent团队来提高效率」。三个工作面分工：wp3-rung-rebuild（队友完成）、wp2-gap-triage 与 wp5-blind-replay（两次委派的 subagent 均无声失败——无产物无退出消息，Lead 接手亲自完成）。

### ① WP3 翻转阶梯用最终标签重建（队友完成，质量高）

* 厘清口径：12 格 = 2 对（EMC|GBL、EMC|SL）× 6 级；computed 8；非 computed 4 = 2×R4(limited) + 2×R4_screen(筛选层另一档)。
* 修复 build_wp2_closure.py `r4_row` 三处缺口：原只查 M_plus 腿 acceptance（现四腿全查）；provisional 冒充 computed（现单列）；LIMITED note 硬编码 rescue-budget（现带 labels 原文 reason——EMC|M_plus 实为 species_drift_unrecoverable）。配 4 项回归，9/9 绿。
* 报告 `closure/wp3_rung_rebuild_report.md`（生成器正式产物、--check 覆盖）：**Top-3 未被 bound 覆盖**——accepted-only Top-3 = EC>PC>SL（地板 7.7506 eV），AN(9.06)/DMC(8.30)/EMC(8.11,上界8.13)/TMP(7.94,上界7.96) 四分子上界均越地板，limited 全换真值时 Top-3 可能改写；AN/DMC 的 RT ln N=0 界对漏采样盆地无约束力（弱证据，如实登记）。

### ② 14 个非 accepted 态的缺口决策证据（Lead 完成）

* 新脚本 `build_gap_decision_support.py`（6 测试）：处置分布、未用盆地、RT ln(N_new/N_unique) bound、Top-3 敏感性、四档建议。
* **关键技术发现：池/账本 basin 命名是双拼写**（池 relpath 写 r2_c13/c03，账本写 13/3）——`_basin_key` 规范化后做真集合差，否则未用盆地永远算空、--check 变成鹦鹉学舌。
* **决策结论：全部 14 态的冻结池盆地已被生产级 DFT 用尽**（unused_basins 全空，与「池耗尽」审计自洽）；排序敏感 4 态（AN/DMC/EMC/TMP 的 M_plus）全部只能「登记限制」——**没有任何态满足「可预注册新起点」的两条件（排序敏感 AND 池有余量）**。产物 `ensembles/remaining_gaps_decision_support.{csv,md,_index.json}`。

### ③ WP5 候选级盲回放（Lead 完成）

* 新脚本 `run_wp5_blind_replay.py`（7 测试）：`Acquirer` 结构性拿不到完整标签向量（构造后 `_assert_blind` 自检），`Evaluator` 独占真值且仅在每轮选定后调用；精确 k=3 端点；**端点取池耗尽前最后一轮**（n_T=n_pool 是平凡完美解，不用）；remaining error max/mean；累计 core-hours 用**登记为 ASSUMED_CONSTANT 的 0.6/查询**（非实测，index 显式声明）。
* 两个被自家测试当场抓出的 bug：str 哈希进程盐破坏跨进程确定性（改 sha256 摘要）；check 与 write 行尾不一致（统一 \n）。
* **结果（20 repeats）：三轴 9 组端点全部 pass**——O_3 0.817–1.000（阈值 2/3）、R_3 ≤ 0.088 eV（阈值 0.10），E/M 轴不再 blocked。产物 `active_learning/blind_replay/{candidate_rounds,round_summary,axis_endpoint}.csv + _index.json`（36600/2220/9 行），--check 字节级复核过。

### 登记与验证

* 四处登记两次完成（计数 52/46 → 53/47 → **54/48**，`test_wp2_cost_semantics` 布局断言串同步）。
* 新增测试 17 项（next_action 10 之外：gap 6 + blind 7 含 wp3 的 9 项回归）全绿；收口链 **40/40 OFFLINE CLOSURE GREEN**（本日第 10 次）。
* **subagent 委派教训**：wp5 与 gap 两个 subagent 均无声失败（无产物、无退出消息）——复杂工程任务跨进程委派不可靠时，Lead 直接实现更稳；wp3（口径审计型）委派则一次成功。未 commit。

## WP5 v2 升级与收口链接线（2026-10-20 深夜，用户新计划 Round 1-2）

用户裁决：三个新产物是**已验证的中间证据**而非核心方案完成——WP5 盲回放仍是旧 C/M/E 池上的方法演示；下一阶段先修口径与接线。按此完成：

### ① WP5 v2：四策略 + 配对种子 + 停止预算（Lead 亲自实现）

* 新契约层 `wp5_replay_contract.py`（纯函数 7 测试）：`stable_seed`（sha256、task|repeat|purpose 作用域）；`initial_visible`（**配对初始集**——四策略共享同四个初始标签，键只含 task|repeat）；`empirical_stop_budget`（**逐 repeat 逐非耗尽预算点**计数 O_3≥2/3 且 R_3≤0.10，两个相邻点各 ≥16/20 才报；n_T≥n_pool 平凡完美解排除；None=诚实未达）；`descriptive_mean`（均值只作描述统计，两套标签永不互换）。
* `run_wp5_blind_replay.py` 升级：四基线（新增 `ranking_aware`＝kNN 残差 bootstrap 的 top-3 成员后验熵，拟合只用可见标签）；`pool_label=legacy_method_demo` 全表标注；endpoint 新增 `stop_budget_n_T` / `stop_budget_status` / `mean_is=descriptive_statistic_not_stop_budget` 列。
* **20 repeats 实测：12 组中 11 组拿到经验停止预算 n_T=7–17**（C:random/diversity=8、uncertainty=7、ranking_aware 未达——如实 not_reached_within_pool；M:11–17；E:10–17），与旧「均值达标」口径的数字分开呈现。
* 新增测试 4 项：配对初始集、停止预算逐点非均值、**隐藏标签注入 acquirer 必须失败**（负向测试）、candidate 表（含 true_ev）永不进获取通道（构造签名白名单）。测试合计 18 项全过。

### ② A/B 验收目标池（v2 输入契约）

* 新脚本 `build_wp5_target_pool.py`（5 测试）：从**最终** `production_ensemble_labels.csv` 派生 **12 分子 × 2 任务**——A=free 氧化移位、B=Li 条件移位（free 标签成本属 B 预算联动，台账另行、不可追溯即 MISSING）；每行带双腿 acceptance/limitation 原文与 `qc_complete_pair`（11 对全 accepted、13 对如实保留不丢弃）。与 legacy demo 池彻底分开。`target_pool_AB.csv` + index（labels sha256 钉死），`--check` 字节复核过。

### ③ 收口链接线 + 基线冻结

* `finalize_wp2.ps1` 40→**46 步**：新增 `gap-decision`、`wp5-blind-replay`、`wp5-target-pool` 三个生成步（排在 closure 后、cost 前）与三个对应 `--check`。**46/46 OFFLINE CLOSURE GREEN**——三个新产物从「有 --check 的孤立脚本」变成「链内执行+链内验证」。
* `work/baseline_20261020.md` 冻结基线：三产物输入哈希与 --check 状态；并列写明「WP3 阶梯 8/12 computed」「系综 34/48 accepted」「Top-3 未被现有 bound 覆盖」+ RT ln N 仅约束已知成员的口径。
* 新增两脚本四处登记完成（计数 54/48 → **56/50**）。

### 尚未做（本计划剩余项）

* **A/B 任务的回放执行**：目标池已就位，但四策略×配对种子×停止预算的回放还没在 A/B 池上跑（A 池 12 分子 top-3 语义、B 池 free 成本联动需要新的获取成本映射）。
* emit_wp2 §9.2 与合规消费者**未改**（按用户计划：待新 A/B 回放过门后再接，避免旧 round_diagnostics 与新表同时宣称权威）。
* 可追溯成本连接：production_cost_ledger 有 60 行实测，但**无逐查询成本映射**——A/B 回放的成本列仍将是 ASSUMED_CONSTANT 情景，除非先建 per-query 成本台账。
* 未 commit；Open questions（四态新池搜索、3→6 容差冻结）等用户裁决。

### ④ A/B 验收回放执行（Round 3，计划第 7 项的成本联动落地）

新脚本 `run_wp5_AB_replay.py`（7 测试全过）在 12 分子最终标签池上执行四策略配对回放：

* **停止预算（20 repeats）**：6/8 组拿到经验停止预算——A 任务 diversity=9、uncertainty=8、ranking_aware=7；B 任务 diversity=9、uncertainty=8、ranking_aware=7；random 两组未达（A: R_3 均值 0.113、B: 0.084——如实 not_reached_within_pool，不造数）。
* **成本全部实测追溯、零 MISSING**：`_query_cost` 从 production_cost_ledger 逐腿取 core_hours——A=M+M_plus 双腿、B=Li 双腿 **+ M+M_plus free 标签获取成本**（计划明文规则）；60 条腿全覆盖（M 均值 5.88、M_plus 11.75、LiM_plus 10.63、LiM_2plus 12.43 core-hours），1440 行 summary 全部 `measured_cost_ledger`，**ASSUMED_CONSTANT 只留在 legacy demo**。
* 盲性负向测试、配对初始集、跨进程确定性（sha256 种子）全部钉死；`--check` 字节复核过、两次运行哈希一致。
* 收口链 46→**48 步**（wp5-AB-replay 生成步 + check），**48/48 OFFLINE CLOSURE GREEN**；四处登记完成（计数 → **57/51**）。

**至此 WP5 的 A/B 验收数据链完整**：target_pool（12 分子最终标签）→ A/B 回放（四策略、配对种子、16/20 停止预算、实测成本、盲性）→ `--check` → 收口链内执行。legacy C/M/E demo 与 A/B 验收彻底分层、各自 pool_label 声明。emit_wp2 §9.2 与合规消费者**仍未动**（按计划：下一步可安全接线——A/B 已过门，但接线本身属新的代码改动，留待用户确认后做）。

### ⑤ v3.0 五缺口修正（Round 4，用户复核反例后）

用户核对代码后给出五缺口与两个只读反例（[10,9,8,0] 选 [10,9,0]：旧 regret=0、集合均值损失实际 2.667；两点各 16 次但交集 12：旧函数仍返回停止预算）。全部修正：

| 缺口 | 修正 | 验证 |
|---|---|---|
| **B 任务定义** | Δ_coord = S_Li − S_f（不是裸 Li 两态差）；三列 S_f/S_Li/D_coord + `li = free + shift` 恒等式逐行测试 | 恒等式 12/12 True |
| **regret 主指标** | `R_3_mean`（v3.0 §11.2 集合均值损失）为主；旧 best-in-selected **改名** `best_selected_regret` 另列，不共用 R_3 名与 0.10 门槛 | 反例复现：R_3_mean=2.667、旧指标=0——两者分开呈现 |
| **停止规则** | 联合成功：同一批 ≥16 个 repeat 在两点**同时**成功（交集，非分别计数） | 反例复现：16+16 交集 12 → None |
| **准入** | 正式回放只收 qc_complete_pair=True（A=6、B=5 对）；受限行留 target_pool 作敏感性演示，不静默进正式池 | `_pool(admission='qc_complete_pair')` |
| **成本完整性** | M 腿基组修正为 **M_tzvpd**（标签的真实来源），不再用 legacy TZVP M 行；缺腿在 basis 字符串里点名 `MISSING_LEGS=` | A/B 成本仍全实测零缺失 |

**修正后的诚实结果**（R_3_mean + 联合停止 + 准入过滤三重收紧）：
* **legacy demo（C/M/E 池）**：旧口径 9 组 pass → **新口径只剩 2 组有停止预算**（M/diversity=14、E/diversity=10），其余 10 组 not_reached——旧 best-in-selected 指标系统性低估 regret，这就是用户反例的实证后果。
* **A/B 正式回放**：准入过滤后 A 池 6、B 池 5——**全部 8 组无法演示停止规则**：A 池唯一非耗尽预算点对是 (4,5) 而 n=4 20/20 全不达标（交集 0）；B 池 5 分子、非耗尽点只有 n=4 一个，**连两个相邻点都不存在**——按 v3.0 标 `blocked_target_pool`（与 not_reached 是两种不同的诚实表述）。
* **结论**：以当前 34/48 accepted，**A/B 正式验收在数学上不可能过停止规则**——这正是「系综标签未闭环 → WP5 验收被 blocked」的量化呈现，此前「6/8 组 n_T=7–9」确系受限池上的乐观假象，按用户指示降级为待复核中间证据。

**另发现并修**：gap-decision 生成器的 index 嵌 wall-clock 时间戳导致链内 generation 与 check 永远差一秒——改为输入哈希 provenance（确定性 index）；队友版 `_basin_key` 前导零剥离（c03→3 与账本 bare 3 对齐）。修正后 48/48 OFFLINE CLOSURE GREEN。旧测试 4 项按新契约更新、新反例测试 5 项全绿。

### ⑥ RT 常数修正（2026-10-20 深夜，v3.0 §19.1 第 1 条对照项实证）

用户核心方案 v3.0 §19.1 列出「`build_sampling_3to6_diff.py` 的 RT(Eh) 应按 §9 常量重算」——核对证实为**真 bug**：
* 现用 `RT = 0.00158760761551242`（注释误写 0.0019872041/627.5——那是 R/Eh/K 而非 RT/Eh），正确值 **RT(298.15K) = R×T/Eh = 1.98720425864083e-3 × 298.15 / 627.5094740631 = 0.0009441848676442220 Eh**；
* 旧值偏大 **1.6815×**，ceiling 的 −RT·ln(Σexp) 项被同倍放大。

**修正后的三个 complete 值**（旧值括注）：

| 态 | Δ (kcal/mol) 修正后 | （修正前） |
|---|---|---|
| DEC/M_plus | −0.000027 | （−0.000027，ln 项过小对常数不敏感） |
| **EMC/LiM_plus** | **−0.534816** | （−0.974119——高估 82%） |
| **TMP/LiM_2plus** | **−0.436766** | （−0.801113——高估 83%） |

**科学影响**：扩样差异的量级结论从「近 1 kcal/mol」下修为「**0.44–0.53 kcal/mol**」——仍是本项目仅有的三个可测 3→6 差异、方向与排序含义不变，但先前引用的 −0.974/−0.801 数字作废，以本条为准。聚合器 `build_production_ensemble_aggregator.py` 的 R_KCAL 来源正确（CODATA），不受影响；`build_gap_decision_support.py` 的 R_KCAL 同源正确。测试期望值同步修正；12/12 全过。

### ⑦ v3.0 §19.1 对照项全部关账（2026-10-20 深夜）

| # | 对照项 | 状态 | 落点 |
|---|---|---|---|
| 1 | RT(Eh) 常数重算 + 跨模块数值测试防分叉 | ✅ | sampling_3to6_diff RT 修正 1.6815×（见 ⑥ 节）；新增 `tests/test_rt_constant_identity.py` 5 项——聚合器/gap/diff 三模块的 R_KCAL、RT(Eh)、kcal 与 Eh 双路径一致到 1e-18，错误旧常量回归断言（0.0015876/RT=1.6815x 比值钉死） |
| 2 | regret 新老列区分 + 阈值结果重建 | ✅ | R_3_mean 主指标+best_selected 改名另列（v3 修正②）；legacy 停止预算从 9 组重算到 2 组 |
| 3 | B 行输出 Δ_coord 非 S_Li、恒等式 | ✅ | 三列 S_f/S_Li/D_coord + identity 逐行测试（v3 修正①） |
| 4 | 正式入口执行 cohort 准入 | ✅ | `_pool(admission='qc_complete_pair')` A=6/B=5；受限行留目标池（v3 修正④） |
| 5 | 端到端验证 + 联合成功/有限值校验 | ✅ | 配对种子、注入泄漏负向、16 交集反例、池耗尽排除、成本缺失不假设、重复记录拒绝（--check 篡改检测）——§19.1 要求的 9 类测试逐一核对通过 |

**§19.1 测试清单逐项核对结果（8 项脚本化验证）**：B 任务恒等式 ✓、RT 跨模块 ✓、regret 反例（[10,9,8,0]→R=2.667 vs 旧=0）✓、同 repeat 四策略共享初始集 ✓、隐藏标签注入必失败 ✓、两点各 16 交集 12 → None ✓、池耗尽轮排除 ✓、成本缺失不冒充实测 ✓（外加 --check 篡改即红的重复记录拒绝）。§19.1 全部关账。

### ⑧ D6 预注册稿落地（2026-10-21，v3.0 D6 顺序项）

新脚本 `build_d6_preregistration_draft.py`（5 测试全过）——四个排序敏感 M_plus 态（AN/DMC/EMC/TMP）的新池预注册**草案**（未启动）：

* **量化威胁（全部派生）**：四态 M_plus gap 全部已越 accepted Top-3 地板（7.7506 eV）——AN 9.06 / DMC 8.30 / EMC 8.11 / TMP 7.94；「已越地板」判定由 gap>floor 逐态算出，不硬编码。
* **预注册四要素**（若启动才生效）：① 搜索动作与独立性（新一轮独立构象/motif 搜索、不回填旧池、GFN2 筛选与生产 DFT 分层）；② 成本上限（M_plus 腿实测均值 11.75 core-hours，每态新盆地上限与总 core-hours 上限超限即停）；③ 候选选择（DFT 级 dedup + 身份门前置 + **排序敏感判据搜索前冻结**）；④ 停止条件（每态 ≤2 独立起点、两败即登记 sampling_limited）。
* **默认分支=限制报告**（用户裁决）：本轮不启动，四态维持 limited 及既有原因；「现有池不能认证 Top-3」作为独立事实登记。启动需用户逐态点名。
* index 无 wall-clock（输入哈希 provenance——应用 ⑥ 节的教训）；`--check` 过；四处登记完成（计数 57/51→**58/52**）；收口链 48→**50 步**（d6-prereg + check-d6-prereg 进链），**50/50 OFFLINE CLOSURE GREEN**。

**v3.0 D1-D6 顺序表现状**：D1-D5 已全部完成（前几轮）；D6 本次以「预注册稿 + 限制报告」双分支落地——限制报告为生效分支（默认），预注册稿备而未用。剩余 D7（阶段报告/发布候选）属下一工作段。

### ⑨ strict_recovery_v1：14 态严格补算批次（2026-10-21 起，进行中）

用户裁决：从 D7 报告转入新一轮**有预算、独立起点、明确验收条件**的补算，**14 个未 accepted 的态**全部排入（每态 ≤2 个新独立起点、总上限 28 条、恢复包 600 + 储备 300 core-hours）。当时这 14 个都记 `limited`；候选登记后状态改为反映实际进度——**8 个 `provisional`（恢复腿在飞）+ 6 个 `limited`（搜索耗尽）**，分母仍是 14。

**① 冻结 manifest**（`build_strict_recovery_manifest.py`）：14 态 × ≤2 起点 = 28 腿硬校验；成本依据实测合计 399.6 core-hours；3 态有未用冻结池盆地（DEC/M r2_c23、DME/M_plus c07、TMP/M_plus c10，经**盆地双拼写规范化**从缺口表裸数字映射）；11 态登记为需版本化新搜索。

**② 覆盖复核机制**（`build_coverage_reviews.py` + 聚合器 `acceptance_decision()`）：limited→accepted 的**唯一证据通道**——verdict=resolved 需「新起点已 computed 且经 dedup 进入 kept、态内 ≥2 独立极小、无 pending 恢复成员」，且**复核声称的成员必须全部真在 kept 池**（防作弊）；**`n_limited` 永不清空**，`coverage_status` 列单记 verdict。8 项单测钉死含 DEC/M 真实场景与全部防作弊分支。

**③ P0 独立搜索实测（本轮最重要的科学结论）**：本地 GFN2 `--opt tight`、每态 64 起点、登记 seed、重原子 Kabsch RMSD 0.35 Å 去重 —— **AN/DMC/EMC 的 M_plus 全部 64 起点塌缩到已有单一极小（RMSD 0.0000）**，即这三个 Top-3 边界态在筛选层**无第二构象极小**（物理事实，非预算失败）；只有 TMP/M_plus 找到 2 个新独立极小（RMSD 0.54 Å、rel 0.00 kcal）。故 P0 首批由计划的 8 腿缩为 2 腿。

**④ Li round-3 恢复搜索**：8 腿 122 候选、**10 个新独立盆地**（DME/LiM_2plus 2、SL/LiM_2plus 3、TMP/LiM_2plus 1、TMP/LiM_plus 3、DMSO/LiM_plus 1）；**DMC/EC/DOL 的 LiM_2plus 零新盆地**（→ search_exhausted，保持 limited）。`legs_above_registered_bound=3` 属已知的「启发式上界不是数学上界」，登记偏差不改预注册值。

**⑤ 三个生产批次**：

| 批次 | 内容 | 状态 |
|---|---|---|
| 1 | 4 腿（DEC/M、DME/M_plus、TMP/M_plus×2） | Job **3738029**；DEC/M 与 DME/M_plus **已完成且均 0 虚频**（最低实频 63.12 / 52.57 cm⁻¹）；TMP 两条运行中 |
| 2 | 8 条 Li 配位腿 | 已打包 + 远端 8/8 sha 校验，待提交 |
| 3 | 73 个计入系综成员的 frontier 单点（Molden 输出） | 已打包 5 批（18×4+1）、73/73 sha 校验，待提交 |

**⑥ 电子身份管线**：`build_frontier_legs.py`（cohort = `production_ensemble_weights.csv` 全部 73 个有 Boltzmann 权重的成员，几何按登记 `final_geometry_sha256` 递归精确匹配 → **73/73 命中**）+ `build_frontier_localization.py`（解析 Molden 出 HOMO/LUMO 组成与 frontier_class；**阈值读结果前冻结**：weight 0.50 / Li 0.25；缺文件记 not_computed、解析失败记 parse_failed，绝不静默写 0）。

**⑦ 采样审计**：`build_sampling_ceiling_classification.py` 把 16 态分成 complete 3 / registered_candidates_qc_pending 7 / pool_has_no_independent_structure 6（+ 0 塌缩 / 0 真缺失）；`build_tolerance_preregistration.py` 出**容差预注册稿**（三条候选依据 + 所需证据，**不选数值**，当前差异明确标注仅作参考、绝不是容差依据）。

**本轮抓到的四个真实缺陷（都已修 + 测试钉死）**：

1. **恢复腿会被静默丢弃**：`_is_round2_package()` 不认恢复包名 → 导入循环打印 「UNKNOWN task not in candidates」后 `continue`，4 条腿跑完全部消失。
2. **幻影 pending**：把「已登记但未计算」的恢复候选写进 manifest 会让聚合器算成 `n_pending`，limited 全部变 provisional（14→6），链立刻红 → 改为结果入账后才登记。
3. **用户裁决被 rebuild 静默回滚**：EMC 的 3 个 Li 盆地曾只在派生 JSON 里注册，生成器仍列 `DEFERRED_AUDIT_MOLECULES=("EMC",)` → 重建后 EMC/LiM_plus 从 complete 退回 not_computed。**裁决必须编码进生成器**。
4. **stray 白名单漏登记 ×4**（round-3 Li 产物、frontier legs、ceiling 分类、容差稿）：往别人拥有的输出目录写新文件，必须同步登记那一层白名单。

**收口链 63 步全绿**；计数 65 个跟踪文件 / 59 `*.py`。

**尚未完成**：批次 2/3 提交与回收、导入后覆盖复核重判、WP3/WP5 重跑、合规重建、WP6（需 48/48）。

### ⑩ strict_recovery_v1 批次 1 收官与天花板（2026-10-21 下午）

**批次 1（Job 3738029，4 腿）全部收尾——4 条都是合法 QC 失败，没有一条是拼写错误或脚本问题**：

| 腿 | 失败类 | 判据 | 补救 |
|---|---|---|---|
| DEC\|M\|r2_c23 | `verytight_convergence` | rms_step 1.72e-4 > 1e-4（TolRMSD） | reopt1（Job 3738937） |
| DME\|M_plus\|c07 | `verytight_convergence` | energy_change 9.44e-7 > 2e-7（TolE） | reopt1（同上） |
| TMP\|M_plus\|r3_c42 | `max_cycles_exhausted` | 51 圈撞顶、无 CONVERGED | cont1（Job 3739147） |
| TMP\|M_plus\|c10 | `max_cycles_exhausted` | 51 圈撞顶 | cont2（Job 3739236） |

**两类失败的机制区别（已用日志原文确认）**：
* `verytight_convergence` = ORCA 走 **close-enough 路径**——原文「The gradient convergence is overachieved with reasonable convergence on the displacements / Convergence will therefore be signaled now」：梯度超额达标、位移判据未达，ORCA 自行宣布收敛；补救是从**该收敛末几何**严格重优化（驻点重启首圈步长≈0，通常一圈即全绿）。
* `max_cycles_exhausted` = 优化器撞圈数上限、**从未收敛**，没有收敛末几何可用；补救是从**轨迹最低能帧**续算且只加恰好一行 `%geom MaxIter 200 end`。
* ORCA 收敛表的 Tolerance 列**正好等于项目冻结阈值**（2e-7 / 8e-6 / 3e-5 / 1e-4 / 2e-4），所以不存在「项目比 ORCA 严」的错配；但**「ORCA 说 CONVERGED」≠「过五阈值」**，必须看逐项 YES/NO。

**状态口径（候选登记之后）**：34 accepted / **8 provisional** / **6 limited**——`provisional` 表示该态有登记过的补救腿在飞（reopt/continue 或批次 2 在跑），`limited` 表示首轮搜索已耗尽。两者都计入「未 accepted 的 14 态」，分母不缩。

**本轮的科学天花板＝42/48（不是 48/48）**：当前 34 accepted + 本轮有注册起点的 8 态 = 42；另 6 态是本轮换方法也解决不了的（首轮搜索无果）：AN/DMC/EMC 的 M_plus（64 起点全塌缩）与 DMC/DOL/EC 的 LiM_2plus（motif 零新盆地）。**故 WP6 闸门（需 48/48）本轮结束后仍 blocked**，`plan_overall_complete` 同样继续 blocked。这 6 态的第二轮换方法预注册稿已备（`recovery/second_search_preregistration_draft.md`），**是否启动由用户裁决**。

**成本**（实测，非估算）：批次 1 四腿 ≈ 33 core-hours（3.1 / 5.3 / 12.2 / 12.2）；恢复批次累计 ≈ 55 core-hours = 恢复包 600 的 9%；风险储备 300 未动用。按首批实测，28 腿全跑完约 120–200 core-hours，**预算充足**。

**本阶段抓到的 9 个「跑得通但结果错/白烧算力」缺陷**（全部已修 + 测试钉死）：

| # | 缺陷 | 会造成什么 |
|---|---|---|
| 1 | `_is_round2_package` 不认恢复包 | 恢复腿跑完被静默丢弃 |
| 2 | `import_ensemble_structures --fetch` 已废弃 | 取回失败/空操作 |
| 3 | `qc_task` 期望 `run/` 而 sbatch 写 `attempts/` | 导入成功但零结果 |
| 4 | 把未计算候选写进 manifest | 幻影 pending，limited→provisional |
| 5 | 用户裁决只存在派生 JSON | rebuild 静默回滚 EMC 注册 |
| 6 | sbatch 硬编码 `batch_1.txt` + 模板参数顺序 | 批次跑到错任务 |
| 7 | 覆盖复核↔聚合器互为输入只跑一轮 | 复核永久滞后 |
| 8 | `_cont<N>` 未被 `pkg_attempt` 识别 | attempt 序号错 → supersede 与预算统计错 |
| 9 | `submission_journal.json` 不算已提交 | 已提交包的成员不被保护 → **重复排产白烧算力** |

**工程状态**：收口链 **67 步全绿**；全量 pytest 全绿（排除 4 个预存 ORCA fake-binary 环境失败）；计数 66 个跟踪文件 / 60 `*.py`。

**在跑/排队**：批次 2（8 条 Li 配位腿，Job 3738645 —— 4 跑 4 排队）+ reopt1(3738937) + cont1(3739147) + cont2(3739236)。

### ⑪ 三项用户裁决的落地与一次自我纠错（2026-10-21 傍晚）

**用户裁决（本轮回传）**：① 只对 `EMC|M_plus` 做换方法搜索；② 3→6 容差按依据 B 冻结为 **0.10 kcal/mol**；③ 接受 WP5 的 B 任务全池 free 标签前置成本口径。

**②的落地**：敏感性表显示 `0.05–0.25` 区间内三态显著性判定完全一致，故 0.10 不改变任何已有结论；稿内明确「依据是事先声明的实用分辨率，不是把观测差异倒推成阈值」。冻结发生在评价新批次之前。

**③的落地**：实测 B 前置 **24 腿 / 244.440 core-hours**（`measured_cost_ledger`），含前置的总成本 351.063 core-hours；生成器把该口径写死并注明已获用户接受。

**①的落地与结论——这是一次必须记录的自我纠错**：

第二轮方法（唯一改动轴：隐式溶剂 + 样本量）：GFN2-xTB + **ALPB(乙腈)**、**256** 个 ETKDGv3 起点（首轮 64）、seed 20261022、`--opt tight`；**256/256 全部收敛**。

| 第二轮盆地 | rel (kcal/mol) | 与已有极小的 RMSD | 判定 |
|---|---|---|---|
| v2_c042 | 0.000 | 0.0102 Å | 同一盆地 |
| v2_c117 | 2.046 | 0.1181 Å | 同一盆地 |

**真新盆地 = 0** → 触发停止规则 `search_method_exhausted`。

**两处判断错误（均已纠正并写进工具）**：

1. **误判该态「缺盆地」**。实际 `EMC|M_plus` 的 `n_unique=2`、`limitation_reason=species_drift_unrecoverable`，结构表显示 `EMC|M_plus|4` 是 `candidate_bond_graph_changed`——该盆地在生产级优化时**键图改变、重排成别的物种**，冻结协议对身份改变明令「直接判失败、不重试」。**换任何搜索方法都补不上它**，因为它不缺盆地。
2. **搜索脚本的假阳性**：首版基线只读首轮搜索池，而该态首轮搜索没有 `minima` 行 → 基线为空 → `best=inf` → **把两个旧盆地误报为「2 个全新盆地」**。改用权威基线（`sampling_conformer_set.csv` 里的两个已有极小）后真相是 0 个新盆地。**规则已固化：无基线必须判 `unknown`，绝不能默认「新」。**

**核对后的分类（6 个 search_exhausted 态其实分两类）**：

| 类别 | 态 | n_unique | 限制原因 | 换方法是否有用 |
|---|---|---|---|---|
| 漂移类 | EMC\|M_plus | 2 | `species_drift_unrecoverable` | **否（已实测排除）** |
| 真单盆地 | AN\|M_plus、DMC\|M_plus、DMC/EC/DOL 的 LiM_2plus | 1 | `rescue_budget_exhausted` | 未知，需更高描述层级才可能找到第二盆地 |

**后果**：WP3 的 R4 阶梯那 2 对（EMC vs GBL、EMC vs SL）**永久停在 limited**，**R4 上限就是 8/12 computed**——这是化学结论，不是预算或方法问题。

**工程状态**：计数 68 个跟踪文件 / 62 `*.py`；收口链 69 步全绿；全量 pytest 全绿（排除 4 个预存 ORCA fake-binary 环境失败）。

### ⑫ 覆盖复核首次放行：36/48 与三个机制级缺陷修复（2026-10-21）

**里程碑：系综首次从 34/48 推进到 36/48。** 两个态经覆盖复核机制从 `limited` 释放为 `accepted`：`DEC|M` 与 `DME|M_plus`。

**① 机制：从各自收敛末几何严格重优化（strict reoptimisation）**。两条腿的 ORCA 都在 **CYCLE 1** 收敛、四项几何判据全过、且**无 close-enough 路径**（两份 job.log 均无 "Convergence will therefore be signaled" 字样）。实测收敛值：

| 腿 | RMS gradient | MAX gradient | RMS step | MAX step | 虚频 | 最低实频 |
|---|---|---|---|---|---|---|
| DEC\|M\|r2_c23 | 8.289e-7（阈值 8e-6） | 2.419e-6（3e-5） | 2.422e-5（1e-4） | 1.073e-4（2e-4） | 0 | 63.13 cm⁻¹ |
| DME\|M_plus\|c07 | 3.137e-6（8e-6） | 9.027e-6（3e-5） | 4.701e-5（1e-4） | 1.327e-4（2e-4） | 0 | 52.60 cm⁻¹ |

两例的收敛表都**没有 "Energy change" 行**——这是已记录的 ORCA 行为：起点几何本身已 VeryTight-clean 的腿在首次检查即收敛、未移动任何原子，故不打印 delta-E 行。导入器只要求四项几何判据、能量行为可选，因此这两条腿合法有效。

**② 这验证了两步恢复设计**：第一次尝试从池盆地出发只能收敛到判据边缘（典型 3–4/5 项）被判 close-enough；第二次从该收敛几何出发时已位于驻点，首步 ≈0、一圈全过。「每成员至多两次真实计算」的预算正对应这个两阶段流程，不是浪费。

**③ 验收未清空历史**：两态仍带 `n_qc_failed = 1`、`coverage_status = resolved_by_review`，即「历史保留、凭复核释放」。系综值：DEC\|M `g_ensemble` = −422.453865468 Eh、DME\|M_plus = −308.751460903 Eh，各 `n_unique = 3`。证据路径：`work/hpc_production_ensemble_strict_recovery_v1_reopt1/tasks/DEC/M__r2_c23/snapshots/3738937_0/job.log`、`.../DME/M_plus__c07/snapshots/3738937_1/job.log`、`outputs/physics_completion/recovery/coverage_reviews.csv`、`outputs/physics_completion/ensembles/production_ensemble_labels.csv`。

**④ 导入上述结果时发现并修复的同族缺陷三个**：

| # | 缺陷 | 后果 | 修复 |
|---|---|---|---|
| 14 | `latest_attempt_per_member()` 只认 `round1_extra` 角色 | `recovery_v1_start` 行永不进池；聚合器读成「已登记无结果」（n_pending），态永远出不了 `limited`——整条验收路径的最后一个阻塞点 | 角色集扩为 `("round1_extra", "recovery_v1_start")` |
| 15 | `build_coverage_reviews.py` 用 `r.get("state")` 过滤，而结构表该列名为 `slot` | `members` 永远为空——这就是 `unresolved` 判定在整个项目史上一次都没出现过的原因 | 改读 `r.get("slot")` |
| 机制 | 覆盖复核文件只给尚未 accepted 的态发行 | 态被 accepted 后其复核行消失，聚合器找不到复核又把它落回 `limited`——**振荡而非不动点** | 作用域扩为「未 accepted 的态 ∪ 已有复核行的态」，行持久化 |

**⑤ 由此的口径变更**：多个工具原先硬编码「14 个非 accepted 态」「28 条登记腿」。这两个数是**上限（CAP）而非期望计数**——开放态集合只随恢复成功而缩小，故断言改为上界、计数改为派生。原先钉死恢复前分布的测试（14 开放态、WP5 池 A=6/B=5）改为断言不变量：「经复核释放的 accepted 态必须带 review id 且保留历史 n_limited」（`test_no_state_leaves_limited_without_a_resolved_review`）、「B 是 A 的子集」（`test_acceptance_pools_are_the_qc_complete_subset`，现 A≥6/B≥5）、「缺口表恰好覆盖开放态」（`test_every_non_accepted_state_is_covered_exactly_once`，计数从标签文件派生）。`build_strict_recovery_manifest.py` 的 `MAX_LEGS=28` 注释同步写明是冻结预算上限。相关测试 20 项实测全绿。

**当前状态**：accepted **36** / provisional **6** / limited **6**（分母 48）；覆盖复核 **2 resolved + 6 pending + 6 search_exhausted**；收口链 69 步全绿；全量 pytest 全绿（排除 4 个预存 ORCA fake-binary 环境失败）。


### ⑬ 电子身份：全系综成员的前沿轨道组成（2026-10-21 晚）

计划项（4）要求覆盖**所有实际计入系综的成员**，不是仅 48 个 primary。本轮的 cohort 是 `production_ensemble_weights.csv` 的**全部加权成员**（当前 77 个），成员清单与几何按登记哈希定位，报告与 CSV 同源生成（`--check` 字节校验）。

**管线曾经完全不通，现已打通**（三次失败后定案）：ORCA 6.1.1 **不支持** `%output Print[P_Molden]` 的任何写法（单行/块/带内空格都被 `qcscan1.cpp line 84: Invalid assignment in OUTPUT block` 拒绝）。正解是**用捆绑的转换器**：单点跑完写出 `job.gbw`，再 `orca_2mkl job -molden` 得到 `job.molden.input`。侦察式单发（1 任务探针）先验证，再放整批——此前已白烧两批 16 个提交位。

**已解析 45/77，三个非平凡发现**：

| 指标 | HOMO 侧 | LUMO 侧 |
|---|---|---|
| Li 权重最大值 | **0.002363** | **0.310619** |
| 分类分布 | ligand 21 / donor 24 | ligand 25 / donor 14 / delocalized 5 / **li_localized 1** |

1. **Li 在 HOMO 中实质不参与**（最大权重 2.4e-03，远低于 0.25 的 Li 定域阈值）——支持「Li⁺ 氧化还原沉默」。
2. **但 Li 在 LUMO 中可以定域**：唯一一条 `li_localized` 是 `DMSO|LiM_plus|primary`（Li_LUMO = 0.3106，给体_LUMO = 0.3537）。该态的还原过程**涉及 Li 本身**，与一般规律相反。它是**结论的边界，不是噪声**——报告一般规律时必须同时报告例外。
3. **HOMO 与 LUMO 的分类并不一致**（早期 32 条样本里达 12/32）：如 `AN|LiM_plus` 是 ligand→donor、`DEC|LiM_plus|c09` 是 donor→delocalized。**只问 HOMO 会得出错误答案**，因此两个前沿分别落列（`frontier_class_homo` / `frontier_class_lumo`），阈值（weight 0.50 / Li 0.25）在读任何结果之前冻结。

**产物**：`outputs/physics_completion/frontier/frontier_localization.{csv,md}` + `_index.json`。报告的结构刻意把「两个前沿并不一致」和「Li 定域的例外」单独成节——一张只列分类的表会把例外藏起来。

**口径**：本项只描述轨道组成，**不改变任何验收判定**；覆盖率本身即「并行补电子身份」的进度。

**⑬ 续：正式口径（Löwdin）推翻早期 AO 系数结论（2026-10-21 深夜）**

按计划第三优先级的要求，正式布居改用 ORCA 6.1 原生 `! FMOPop` 输出（Mulliken 与 Löwdin
双口径，均考虑基组重叠）。两种口径的对照揭示了量级差异：

| 口径 | Li_LUMO 最大 | ≥0.25（Li 定域阈值）成员数 |
|---|---|---|
| AO 系数平方（忽略重叠，旧口径） | 0.31 | 1 条 |
| **Löwdin（正式口径，FMOPop）** | **0.9126** | **32 条 / 77 全解析** |

最戏剧性的单例：`DOL|LiM_2plus|c05` —— AO 口径 0.0002，Löwdin **0.8373**，差 **4000 倍**。
`AN|LiM_plus|primary` 差 30 倍（0.0299 → 0.9126）。

**正式结论（取代早期基于 AO 口径的判断）**：

* HOMO 侧（氧化）：Li 全部 < 0.01 ——「Li 沉默」**仅对氧化侧成立**；
  64 个已解析成员中 ligand 32 / donor 32 / li_localized **0**。
* LUMO 侧（还原）：**Li 主导**——li_localized **32 条**（ligand 40 / donor 5；LiM_plus 17 + LiM_2plus 15），
  最高 0.9126（AN/LiM_plus），EC 0.8520、DMC 0.8408、EMC 0.8385、DOL 0.8373、DEC 0.8373。

> **Li 配位体系的氧化发生在配体/给体，还原发生在 Li 中心。**
> 「Li⁺ 氧化还原沉默」这一早期表述只对了氧化半边；还原半边在正式布居下完全不沉默。
> **普适性**：77 个成员全部解析后，全部 12 个溶剂分子的 Li 配位态（LiM_plus 17 条 +
> LiM_2plus 15 条）都出现 Li 主导 LUMO（0.65–0.91）——这是 12 分子体系的共同规律。

**方法学登记（供最终报告引用）**：

* Mulliken 布居在基组重叠下可产生非物理值（实测 AN/M__34 的 Mulliken LUMO 列含
  −1.227606 与 2.736070，而同块 Löwdin 列良态）——分类一律用 Löwdin，Mulliken 值
  原样保留仅作展示，校验也只查 Löwdin 列；
* 闭壳层 FMOPop 块无 `OPERATOR` 前缀且原子表无闭合线（与 unrestricted 格式不同），
  解析器两种格式都接受；
* 旧 AO 口径列保留为 `ao_class_*` 与 `li_weight_*`（方法学对照），正式列
  `frontier_class_*` / `fmo_*` 只在有 FMOPop 数据时填——**不跨口径重归属任何数字**。

### ⑭ 冻结证据保留与 ceiling 注册守卫修正：8/16 与三个新显著差异（2026-10-21 深夜）

按计划第一、第四优先级的两处遗留缺口收尾。

**① 冻结 manifest 保留放行态（计划原文：「保留原14态冻结manifest，避免成功态从冻结证据中消失」）**

此前态一旦 accepted 就从 manifest 开放 scope 消失，其注册起点随之不可读——ceiling 的注册集读不到
starts，`TMP|LiM_2plus` 报「登记 1 ≠ QC 通过 2」后被逐出 complete 集。修法与复核层的持久化同型：
manifest 新增 `released` 列，5 个放行态以**冻结证据行**保留（starts 从 resolved 复核行的
`registered_starts` 与 `computed_new_members` 重建——member key 的 seed 段即 basin id；
`max_new_starts=0`，不再有新预算）。过程中抓到两个新缺陷：**note 自增**（marker 每轮追加，永不收敛，
改幂等追加）与 **prior 坏数据回写**（带前缀的旧 released 行被沿用，需清一次强制从复核重取）。

**② ceiling 注册守卫改子集语义（计划原文：「按成员键、角色和最新 attempt 形成集合，避免已有结果被
错误阻塞」）**

旧守卫要求「注册数 == QC 通过数」——双向都错：一条合法失败的注册腿（预算尽/漂移/等价极小）会阻塞
全部已通过成员；而真正必须拦的反向违规（QC 通过但无注册出处）反而没被检查。修法：**子集检查**——
每个 QC 通过成员的 seed 段必须在注册集；失败注册成员记注不阻塞。两个实现细节：member key 是
`name|slot|seed` 而注册表是裸 seed（**比较 seed 段**）；无身份键的 legacy 注册项（manifest.json
只有 path+sha256）**中性化**。哈希校验保留在更深层（fail-closed 层级接住了测试里的假哈希）。

**③ 效果：ceiling 4/16 → 8/16，冻结容差 0.10 kcal/mol 下的正式判定**

| 态 | Δ (kcal/mol) | 判定 |
|---|---|---|
| DEC\|LiM_plus | **-0.999288** | **显著（新最大差异）** |
| EMC\|LiM_plus | -0.534816 | 显著 |
| DME\|M | **-0.450569** | **显著** |
| DME\|M_plus | -0.050917 | 不显著 |
| DME\|LiM_2plus | -0.000370 | 不显著 |
| TMP\|LiM_2plus | -0.000049 | 不显著 |
| DEC\|M | -0.000027 | 不显著 |
| DEC\|M_plus | -0.000027 | 不显著 |

4 个被旧守卫错误阻塞的态全部解锁；其中两个的差异大到显著——**旧守卫不只是技术问题，它在掩盖
真实的科学信号**。

**④ WP5 目标池随放行态扩大后的诚实结果**：SL 放行后 B 池 6→7 分子。停止规则（同批 ≥16 repeat
在两个非耗尽相邻点同时成功）在 7 分子池上更难满足：B/uncertainty 与 ranking_aware 达到 n_T=5
停止，**B/random 与 diversity 没有达到**——按计划第五优先级的口径，这是**有效结论**而非失败
（「AL 不优于随机、没有达到停止预算，均可作为有效结论」）。

**⑤ strict_readiness 当前只剩一个缺口**：`ensemble_not_48_accepted`（39/48）。
电子身份（77/77）与成本溯源等五项证据全部就位。
## 未完成的审查和发布条件

- 2026-10-18 在 batch3 仍为 4 RUNNING + 14 PENDING 时执行不带 `-Commit` 的 `finalize_wp2.ps1`：生成器 75/75、归档账本 300 处比对零失配、全部只读 `--check`、页面校验与链内离线 pytest 退出码均为 0；三个会启动真实本机 ORCA/xtB 的集成节点按 HPC-only 规则排除。此为当时快照的技术闭合，不是 48/48 系综科学验收。
- **2026-10-19 收口链已升级为 40 步（新增 `sampling-audit` / `sampling-diff` / `check-*` 及 `pytest-offline`），不带 `-Commit` 全绿**：`OFFLINE CLOSURE GREEN; 3 live ORCA/xtb integration nodes excluded (HPC-only)`；`git diff --check` 干净。同批修掉两处 sibling-stray 误报：`build_wp2_sampling.py --check` 按 `SIBLING_ARTIFACT_PREFIXES` 登记兄弟产物前缀；`build_li_motif_sampling_plan.py --check` 新增 `ROUND2_OUTPUTS` 白名单容纳第二轮 Li 产物。
- **离线 pytest（2026-10-19 晚，`.venv` 解释器）**：仅排除 3 个真正启动 ORCA/xtB 的活动节点（`test_orca_run.py` / `test_orca_input.py` / `test_toolchain.py`），其余**全部通过**（含 7 条条件 skip、sklearn 收敛告警）；新增 `tests/test_run_li_motif_round2.py` 6 项、import 层 8 项紧随本轮改动。
- **全量 pytest（2026-10-19）**：1753 collected → **1732 passed / 8 skipped / 13 failed**，13 条全部是既有的 ORCA/xtB 子进程环境性失败（`test_orca_run.py` 11 条 + `test_orca_input.py` 1 条 + `test_toolchain.py` 的 xtb 版本探测 1 条），与本轮改动无关；站点广告的 `tests_passed` 已同步校正为 1732。

- `production_ensemble_dedup_pairs.csv` 已登记实际比较对的两份几何 SHA256、搜索节点数、穷尽性与见证映射；须随剩余成员回收更新并独立审查决定。
- `production_ensemble_dispositions.csv` 由导入器生成有界救援／限制记录：computed 34、pending 9、unresolved 9、rescue_budget_exhausted 5。31 个曾未解决成员全部进入 4 个在途包，**不允许再为同一成员建第五个包**；仍失败者登记限制，不放宽冻结五项几何阈值，不把求解失败写成“没有极小值”。`rescue_budget_exhausted` 现有 5 个：DEC/M/3、DME/M_plus/14（reopt3 后仍差 TolE）、DMC/M_plus/28、AN/M_plus/10（reopt4 后仍差 TolE）、EMC/M_plus/4（**物种已漂移，重试无意义——换起点等于换分子，不是同一成员的第 2 次尝试**）。
- 3→6 的生产级独立容差仍未确定；本轮差异报告允许先行，但不得据结果倒推阈值或给出“采样收敛”结论。
- 全套离线收口、真实超算集成与两轮救援回收完成前，不能称原方案已经完成。
