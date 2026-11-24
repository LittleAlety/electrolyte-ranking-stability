# 独立串行超算实验线 — 第一阶段交付与第二阶段门禁（2026-10-31）

- 会话：`exp_line_20261031`（用户指派为"单独的实验栏"，可开一条独立超算实验线，一次只跑一个任务）
- 基线 HEAD：`80933e54f8a605d9dd6d033c0f2861e33b591c13`
- 桥状态：`hpc.ps1 doctor` **通过（0 项提醒）**；真实 `squeue` **空**
- 本轮**未提交任何作业**，**未改任何验收标签**，正式科学状态保持 **45 accepted / 3 limited**

---

## 1. 单项状态

| 用户第一阶段要求 | 状态 | 交付物（路径 + 哈希/测试） |
|---|---|---|
| ① 完成 rev5 接收器独立复审（可信起点/身份/哈希来源是否独立于调用者；协议可比性、去重、coverage） | **⛔ 部分完成**：机制按规格实现（14 项探针，7 项期望达标 + 机制类全过），但**生产链未闭合**，故**不能判"复审通过"**，也**不能迁入** `scripts/wp_production/` | `docs/handoffs/exp_line_20261031/REV5_INDEPENDENT_REVIEW_20261031.md`；探针 `work/exp_line_20261031/audit_v5/probe_v5_trust.py` + `PROBE_V5_TRUST_RESULT.json`；语料复跑 `C_cases_raw.txt`/`cases_results.json`（19 tag） |
| ② 为 DMC\|LiM_2plus 选一份有效末几何并逐项证明同源；冻结起点 SHA/输入/验收/失败分类/停止条件 | **✅ 完成** | 起点 `work/hpc_frontier_localization_v1/tasks/DMC__LiM_2plus__primary/geom.xyz` = `f619c132…f8d505`，电荷 +2 / 重态 2 / **49 电子** 三项证据齐全（`job.inp:5`、`attempt/job.log:585-587`，本会话亲自复核）；预注册 `docs/handoffs/exp_line_20261031/DMC_LIM2PLUS_PREREG_DRAFT_20261031.md`；排除清单 `work/exp_line_20261031/DMC_LIM2PLUS_START_AUDIT.md`（11 组，含唯一一条电荷写错腿 `* xyzfile 0 2` / `NEL 51`） |
| ③ 实时账本核算 + 对照真实 Slurm 队列与提交 journal 排除重复作业；形成可审查预注册与任务包，**保持 HOLD** | **⚠ 完成但入口被堵** | `docs/handoffs/exp_line_20261031/LEDGER_SLURM_JOURNAL_AUDIT_20261031.md` + `work/exp_line_20261031/LEDGER_AND_JOURNAL_20261031.json`；任务包 `work/exp_line_20261031/hpc_dmc_lim2plus_vtscf16_v1/`（14 文件已冻结自校验，`sha256sum -c` 14/14 OK；入口自检 34 项 **0 failed**） |

## 2. 第二阶段（一次性 16 核 / 最长 4 h / 最坏 64 CH）：**未执行**

用户给的前置条件是"第一阶段证据齐全、余额足够、受保护提交器全部检查通过"。第三条**今天不成立**，而且是机器证明、不是判断：

```
[OK ] R-1 submission_resources refuses: ValueError: unknown manifest resource_profile: 'orca_dmc_vtscf_16c_4h_v1'
[OK ] R-2 _enforce_submission_gate refuses: ValueError: package '...' is not authorized for submission (submission_gate='HOLD')
```

- 提交器 `scripts/wp_production/submit_hpc_batch.py:26-114` 的 profile 表**全部 orca profile 都是 4 核**；`:725-731` 会把输入声明的 `%pal nprocs` 与 profile 核数比对，不符即拒绝，提示语本身就写了 **"version the submitter instead"**。
- 因此"16 核 + `%pal nprocs 16` 与 Slurm 分配一致"这一形态，**必须先给提交器版本化加一个 profile**（精确内容见预注册 §7）。那是对生产代码的写入，**属执行 Lead 写入面，本线没写**。
- 余额一侧没问题：600 池可用 **≈399.7 CH**（口径 A）或 **≈408.5 CH**（口径 B），在飞预留 **0**，容纳 64 CH 绰绰有余。

## 3. 本轮发现、需要用户裁决的三件事（我不自行选定）

| # | 事项 | 现状证据 | 为什么必须你定 |
|---|---|---|---|
| D1 | **16 核形态的 profile 由谁版本化？** | R-1 实测拒绝；需要新增 `orca_dmc_vtscf_16c_4h_v1`（cores 16 / wall 4 / cap "64"）并做四处登记 | **已由用户派单裁定（2026-10-31）**：指定 Lead 为唯一生产写入者 ⇒ 由 Lead 版本化（看板 t4）；其他会话对该文件只读 |
| D2 | **EC 战线那 8.81 CH 记在哪个池？** | 口径 A → 600 池可用 399.7 CH；口径 B → 408.5 CH。仓库里**没有任何机器记录**说明 EC 严格收敛实验 16 CH 的池归属（其 `AUTHORIZATION.json` 只写"独立 16 CH 总帽"） | 直接影响"剩余预算"这句话的真值；且用户明令"剩余预算≠新增授权""不得挪用" |
| D3 | **要不要先结清两笔"已花但未记账"再花新钱？** | `work/hpc_dmc_adjacent_step_v2/attempts_ledger.json`：8 行终态却无 `measured_core_hours`/`slurm_allocation_id` → 提交器自己的 `committed_core_hours()` **抛异常**；实测 **0.84778 CH** 无账。`work/hpc_dmc_numerical_probe_v1/attempts_ledger.json`：6 行仍是 `planned`，但 `3869232_0..5` 早已跑完 → 实测 **1.40778 CH** 对任何预算检查都不可见。**合计 2.25556 CH** | 合同口径 `missing_terminal_cost = block_do_not_assume_zero`；且第 1 个文件会让任何读它的后续提交直接报错 |

## 4. 单写入者指定（用户明确要求）

| 面 | 唯一写入者 | 其他会话 |
|---|---|---|
| `work/exp_line_20261031/**`、`docs/handoffs/exp_line_20261031/**`、`.dsh-coordination/exp_line_20261031/**` | **本会话（exp_line_20261031）** | 只读 |
| `scripts/wp_production/submit_hpc_batch.py`（仅新增一个 16 核 profile） | **待用户裁决**：提议仍由**本会话**执行（因为只有本线会提交这条腿）；若判给执行 Lead，则本线把预注册 §7 的 patch 内容交出去，**在写入与复审完成前不提交** | 除指定者外**只读** |
| `work/dmc_staged_receiver*.py`、`work/test_dmc_staged_receiver.py`、`work/_dmc_emit_staging_record.py` | 执行 Lead（rev5 单人写） | 本线**只读**（已按此执行） |
| `work/_fpc_*_20261031.*`、`docs/handoffs/ec_submit_20261029/**` | 正在活跃写入的另一个会话 | 本线**只读**（未触碰） |

占用登记：`.dsh-coordination/exp_line_20261031/CLAIM.md`。
实测并发证据：本节所有只读断言均基于 2026-10-31 02:2x–02:45 的现场（HEAD、git status、文件 mtime、squeue、sacct）。

## 5. 建议的下一步顺序（等 D1–D3 裁决后执行，**本线不抢跑**）

1. **结清旧账**（D3）：两处 ledger 补 `measured_core_hours`/`slurm_allocation_id`，或明确登记为"不可解析、不得读取"——由账本所有者执行。
2. **闭合接收器交付链**：密封登记文件 + 发射器改走 `receive_attempt` + rev5 测试（B1/B2/B3），并**一次冻结四者哈希**后再复审；B4（`coordinate_blocks` 文档过度声称，块头原子数未解析）随同修正。
3. **版本化提交器 profile**（D1）：加 `orca_dmc_vtscf_16c_4h_v1` + 四处登记 + 回归测试。
4. **翻 HOLD → OPEN 并提交这一条腿**：16 核 × 4 h，64 CH，`%pal nprocs 16`，Opt 过五项才进 AnFreq，失败如实拒收、不补 0、不自动续。
5. **终态回收与结算**：按 `sacct` 实测核数×秒数结算；回收两阶段输入/日志/末几何/Hessian 与哈希。
6. **入账判定**：由生产链给 `status=computed` → dedup novelty 可用 → coverage 复核 route（预期 `single_basin_verified`，因为起点 `f619c132…` 距已知极小仅 **0.2739 Å** < `DUP_RMSD_A=0.35`）→ 只有全过才谈 45→46。
7. **核数收益答辩**：交付与 4 核历史作业（`3894976_0`：4 核、ElapsedRaw 1368 s、1.52 CH）的墙钟与 core-hours 对比，再决定后续是否固定 16 核。**这不是无限循环授权。**

## 6. 未决与不确定（如实登记）

- 子代理 `b047ddc7` 的"协议可比性/去重/coverage 现状核实"**已完成**，报告 `work/exp_line_20261031/COMPARABILITY_DEDUP_COVERAGE_AUDIT.md`（328 行）；其关键断言已由本会话**逐条复算**，见 §7（含一条我原先用错参照文件的自我更正）。
- 起点几何的生产者 Opt 末能量与后续单点相差约 2.02e-6 Eh，**成因未查明**，不据此下结论。
- rev4 语料的 `n16`（R5 全合成 Hessian）与 `n18`（R8 块计数）**在 rev5 上不可复跑**（harness 与 rev5 API 不兼容），记为"**未测定**"，不记为通过；R8 改用直接测定（`MALFORMED_GEOMETRY` 三例命中、块头原子数未被校验一例）。
- 4 个"合法外形"探针 `l1`–`l4` 在 rev5 上仍被拒 → 记为**未消解的误拒风险**，需一份真实生产日志才能升级为"已证实误拒"。

---

## 7. 子代理 B 的三轴审计 —— Lead 交叉核对（关键数字复算结果）

子代理 B 报 `DMC|M_plus` 候选在"协议可比性 / 去重 / coverage"三轴上的证据与缺口。**以下每条都是本会话独立复算后的结论，不是转述**：

| B 的断言 | 我的复核 | 判定 |
|---|---|---|
| Rk/Rk1 的 Tight vs VeryTight 同几何单点位移 `+1.326035e-6` / `+7.6093e-8 Eh` | 取自 `work/independent_dmc_adjacent_results_20261030/{SUMMARY.json,3886404_*/job.log,3886408_*/job.log}`；题面与出处一致 | **属实** |
| 项目里**没有任何已冻结的可比性判据** | 0.10 eV = 主动学习停止端点、0.10 kcal/mol = 3→6 采样容差，两者都被用户明令禁止当可比性容差；仓库只有"版本化 + 全 cohort 可比性评估"的流程要求 | **属实，是缺口** |
| `EnforceStrictConvergence` 在历史生产 `*.inp` 中**零命中** | 一致（该关键词只出现在本次新协议输入里） | **属实** |
| 新末几何 `5b0fc24d` 与 `tors_8_0_1_2` att2 末几何（`60ef9ba4`）重原子 RMSD = **0.000326 Å** | 我用仓库自己的 `scripts/build_li_motifs.py::kabsch_rmsd` 复算，**0.000326 Å** | **属实（逐位吻合）** |
| 与 primary 成员几何 RMSD = **0.034771 Å** | 我复算同一数字；顺带定位到权威成员几何文件是 `work/wp2prod/DMC/M_plus/DMC_M_plus_opt.xyz`（sha `5b9e93e0…`） | **属实** |
| coverage 正式 verdict 是 `unresolved`（不是账本里的 `pending`）；**判 duplicate 不必然阻断 coverage**（`single_basin_verified` 可达 resolved） | 与我在预注册 §1/§5 独立读到的 `coverage_route` 条件一致；这两个状态之间**没有映射代码** | **属实** |
| "消费者默认排除 pending" 只在 coverage 轴实现（`aggregator:644`、`strict_readiness_wiring.py:184-185`），两条协议轴**零实现** | 复核一致：`protocol_comparability`/`coverage_acceptance` 在 `scripts/`、`src/`、`tests/`、`config/` 全目录**只出现在两份文档里**，无任何消费者 | **属实** |
| `docs/handoffs/ec_submit_20261029/` **整个目录未被 git 跟踪**，底层日志又在 gitignored `work/` | 一致（该目录在 `git status` 里是 `??`）；**Rk/Rk1 全部文字证据都不在版本库内** | **属实，是耐久性风险** |
| 账本仍是 `dmc_staged_receiver/v4` + `dmc_staged_staging_ledger/v2`，而 rev5 已存在 | 与我的 P8/B2 一致 | **属实** |

### 7.1 我原先的一处自我更正

我在预注册 §8 旁证里用 `outputs/week4/t2_opt_freq/DMC/DMC_G2_cation.xyz`（`1237e7e1…`）作 `DMC|M_plus` 的"既有成员几何"，得 RMSD 0.0788 Å。**该文件不是权威成员几何**；权威件是 `work/wp2prod/DMC/M_plus/DMC_M_plus_opt.xyz`（`5b9e93e0…`，与 `production_ensemble_structures.csv` 里 primary 的 `start_geometry_sha256` 一致），正确值 **0.034771 Å**。结论方向不变（都 ≪ 0.35 = 重复），但数值以 B 与我的复算为准。

### 7.1b 第二处自我更正（更严重，已同步改掉交付文档）

我先前把 `production_ensemble_structures.csv:38` 的字段**看错位**了：该行 `start_geometry_sha256` 实际是**空**，`f619c132…` 是它的 **`final_geometry_sha256`**（`log_sha256 = 45d4a8b0…`，与成员 `job.log` 实测哈希一致，可交叉验证我的取列）。

⇒ 结论**更强**：入选起点 `f619c132…` **就是 `DMC|LiM_2plus` 既有 primary 成员的末几何本身（同字节）**，从它再起一轮 Opt 与自身必然同簇，dedup 判重复 —— `single_basin_verified` 不是"预期"，而是由字节身份直接推出；先前那条 0.2739 Å（vs `DMC_m1_G2Li.xyz`）降为次要参照。

**教训**：CSV 行有空字段时，肉眼读 `grep` 出来的整行会列错位；必须按字段名取值核对（已记为全局 lesson）。预注册 §2/§8 已同步更正。

### 7.2 导入器发现通道 —— **本节原先的 B5 结论已被推翻（2026-10-31 自查更正）**

我原先只读了 `scripts/wp_production/import_ensemble_structures.py:154-155` 的 `PACKAGES` 元组，就断言"导入器的包发现只匹配两个家族、腿再好也进不了表、需要两处代码改动"。**这是错的。** 读全 `iter_packages()`（`:1260-1285`）后实测：

```python
patterns = (PACKAGES,) if isinstance(PACKAGES, str) else tuple(PACKAGES)
patterns = patterns + (RECOVERY_PACKAGE_GLOB, TORSION_PACKAGE_GLOB)     # :1268
...
# ADDITIONAL, name-independent channel: any injected batch whose manifest
# declares members is an ensemble package.                              # :1275-1278
for p in sorted(REPO.glob("work/hpc_*")):                               # :1279
    if not p.is_dir() or p.name in seen: continue
    doc = read_package_manifest(p)
    if doc is not None and doc.get("members"): yield p                  # :1283
```

**活证**：`work/hpc_ec_strict_convergence_v1/manifest.json` **含 `members`（1 条）** ⇒ 尽管它不匹配 `PACKAGES`，仍会被发现。
**实测对照**：`work/hpc_dmc_mplus_opt_repaired_v1_20261030` 与我的包**都没有 `members`**。

⇒ **修正后的 B5（工作量比原判小得多）**：真实原因是我把包嵌在 `work/exp_line_20261031/hpc_...`（`work/hpc_*` glob 摸不到）**且 manifest 缺 `members`**——**不需要改导入器代码**，只需：① 包放到 `work/hpc_<name>/`；② manifest 给出非空 `members`。

**仍需要的 tracked 写入只剩 1 处**：候选表 `outputs/physics_completion/ensembles/production_ensemble_candidates.csv` 加一行，且 `member_role` 必须 ∈ {`round1_extra`, `recovery_v1_start`}（`build_production_ensemble_aggregator.py:696` 硬过滤；代码注释明写"缺一个角色 → 成员永不进 `latest` → 状态永远 `limited`"）。⇒ "提交前检查清单"**保持 5 项**（profile、布局+`members`、候选登记、可比性判据、证据归档），不是 6 项。

细节与可执行补丁见 `work/exp_line_20261031/PRODUCTION_PATCH_SPEC_20261031.md`（每条绑定打补丁前基线哈希）。

### 7.2b（原 7.2 的错误版本，仅存记录）

`scripts/wp_production/import_ensemble_structures.py:154-155`：

```python
PACKAGES = ("work/hpc_production_ensemble_r*_*",
            "work/hpc_production_ensemble_strict_recovery_v1*")
```

⇒ 导入器的包发现**只匹配这两个家族**。`work/hpc_dmc_mplus_opt_repaired_v1_20261030` 与**本实验线的 `work/exp_line_20261031/hpc_dmc_lim2plus_vtscf16_v1` 都不在匹配范围内**；同时 `outputs/physics_completion/ensembles/production_ensemble_candidates.csv`（123 行，**tracked 文件**）里检索 `repaired`/`vtscf` **零命中** —— 新尝试从未登记为候选。

**含意（对第二阶段影响很大）**：即使那条腿完美通过 QC，它也**进不了正式表**，除非额外做两处 **tracked 生产文件** 改动：① 把该 attempt 登记进 `production_ensemble_candidates.csv`；② 让导入器的包发现覆盖该包（或在既有家族命名下重建包）。这两项与 D1（提交器 profile）一样，属**单写入者 + 需复审**的生产面改动。⇒ 第二阶段的"提交前检查清单"从 3 项变成 **6 项**。

### 7.3 更新后的阻塞清单（合并 §3 与本节的 D1–D3）

| 编号 | 阻塞 | 性质 |
|---|---|---|
| B1–B4 | rev5 交付链四缺口（见 rev5 复审报告） | 生产面写入 + 复审 |
| **B5**（已更正，见 §7.2） | 包嵌在 `work/exp_line_20261031/hpc_...` + manifest 缺 `members` → 导入器发现不到；候选表未登记。**不需要改导入器代码**；需 ① 包移到 `work/hpc_<name>/` ② manifest 给 `members` ③ 候选表加一行且 `member_role ∈ {round1_extra, recovery_v1_start}` | **1 处 tracked 写入**（候选表） + 本线布局 |
| **B6** | **没有冻结的协议可比性判据**；且该轴今天**零消费者**（标签 `pending` 不拦任何东西） | 需用户/Lead 先立判据，否则"可比性已通过"无从谈起 |
| **B7** | Rk/Rk1 全部文字证据位于**未跟踪目录** + 底层日志在 gitignored `work/` | 耐久性风险，需决定是否入库 |
| D1 | 16 核 profile 版本化（谁写） | 待裁决 |
| D2 | EC 战线 8.81 CH 池归属 | 待裁决 |
| D3 | 2.25556 CH 未记账是否先结清 | 待裁决 |