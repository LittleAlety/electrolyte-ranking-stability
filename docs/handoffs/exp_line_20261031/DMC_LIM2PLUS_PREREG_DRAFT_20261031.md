# DMC|LiM_2plus 16 核一次试验 — 预注册草案 v1（状态：**HOLD**，未提交）

- 实验线：`exp_line_20261031`（本会话）；单写入者：本会话（写入面见 §11）
- 包路径：`work/exp_line_20261031/hpc_dmc_lim2plus_vtscf16_v1/`（已冻结，`PACKAGE_SHA256SUMS` 自校验 13/13 OK）
- 基线 HEAD：`80933e54f8a605d9dd6d033c0f2861e33b591c13`
- 授权状态：**已授权的一次性试验**（16 核 / 最长 4 h / 最坏预留 64 CH，自救援额度支取）。**当前处于"授权在手、前置条件未满足"状态**：受保护提交器尚未支持 16 核 profile、候选登记与导入发现路径未接通、A/B/C 三道门尚未全过。在全部条件满足且 Agent C 给出 GO 之前**不提交**；本次授权在本条腿结束后即终止（**不是**无限循环授权）。

---

## 1. 这条腿的目标（说清楚它到底改什么）

目标不是"让作业正常结束"，而是让 `DMC|LiM_2plus` 多出一条**QC 通过（status = `computed`）**的回收成员，从而走通既有的 coverage 复核路线、把该态从 `limited` 推到 `accepted`（45/48 → 46/48）。

依据是生产代码里的两条判定，不是我推测的：

| 判定 | 出处 | 实测现状 |
|---|---|---|
| 一个态要有 ≥2 个"存活（未被去重吸收）成员"才不算池受限 | `build_production_ensemble_aggregator.py:960` → `pool_limited = len(kept) < 2` | DMC\|LiM_2plus `n_unique=1`、`pool_limited=true` |
| 历史限制只能被一次**明确的 coverage 复核**解除，且复核声明的成员必须真在 kept 池里（反作弊） | 同文件 `:619-657`（`acceptance_decision`：`n_limited and not cov_resolved → limited`） | 该态当前 `coverage_status=review_unresolved` |
| 复核路线判定 | `build_coverage_reviews.py:167-227` | 当前 CSV 行：`route=unresolved_qc`、`verdict=unresolved`、说明"registered recovery start(s) exist but none passed QC" |

**route 的判定条件（`coverage_route`，逐条读代码）**：
1. 该态**不能有** `pending`/`ready` 的回收成员（`:176`）；
2. 必须至少有一个 `status == "computed"` 的成员（`:179`）——这就是"QC 必须真过"；
3. 这些成员的 dedup novelty 必须可用（`:197-201`，`unresolved` → `dedup_evidence_required`，仍不算 resolved）；
4. 若每个 computed 起点**都落在已知极小**上，且生产证据齐、搜索范围已登记 → **`single_basin_verified`**（`:224-227`），verdict = `resolved`；
5. 若有一个起点落在**新奇盆地**上 → `multi_basin_coverage`（`:203-210`），verdict = `resolved`。

⇒ **两条路线都通向 resolved，而且第 4 条正是"再起点落在同一极小"的情形**。也就是说：本试验的合格形态不是"必须找到新盆地"，而是"**产生一条严格协议下独立复现已知极小的腿**"。这一点必须在实验前固定，免得事后用结果反推标准。

**2026-10-31 机械复核（Lead 独立完成，逐行读代码 + 实测现有表）**：
- "已登记搜索范围"要求**今天已经满足**：恢复清单 `strict_recovery_v1_manifest.csv:2` 的 `search_outcome = no_new_minimum_found`（属 `_search_scope_documented` 认可取值）；`start_1_basin`/`start_2_basin` 虽为空，但 `starts` 另有来源——`_probe_starts()` 从候选表取 `seed.startswith("tors_")` 或 `source_kind=="p4v2_screening_v1_start"` 的行，而该态已有 `tors_7_0_1_2 / source_kind=torsion_probe_v1_start / member_role=recovery_v1_start` ⇒ **`starts = ["tors_7_0_1_2"]` 非空**。
- **唯一缺件 = 没有一条 `status=="computed"` 的 `recovery_v1*` 成员**：`structures` 表该态 8 行里，`tors_6/tors_7/tors_8` 全是 `technical_complete_qc_failed`/`superseded`（其中 `pending` 那行被 `_rejected_probe_members()` 按"取消数组陈旧 pending"排除）⇒ `computed = 0` ⇒ route 停在 `unresolved_qc`（与现 `coverage_reviews.csv` 行一致）。
⇒ **合格登记的三条硬要求**（全部走生成器，不手改）：① `member_role = recovery_v1_start`（同时满足聚合器 `:696` 白名单与复核器 `recovery_v1` 前缀）② `status = computed` ③ **`imaginary_modes` / `final_geometry_sha256` / `log_sha256` 三项非空**（否则 `production_evidence=False` ⇒ route 变 `known_basin_reproduction` ⇒ 仍 unresolved）；④ **必须跑去重生成器**，让该成员进 `production_ensemble_dedup.csv`（否则 novelty = `unresolved` ⇒ `dedup_evidence_required`）。
⇒ **不得**为迎合 `_probe_starts` 把新起点 seed 改名成 `tors_*`（用户 2026-10-27 裁定明令禁止把 P4/v2 起点改名冒充旧扭转探针家族）；本路径**不依赖**新增候选行。
细节与可复算命令：`work/exp_line_20261031/ACCEPTANCE_PATH_ANALYSIS_20261031.md`。

## 2. 起点（已逐项证明同源，本会话亲自复核）

| 项 | 值 | 出处 |
|---|---|---|
| 路径 | `work/hpc_frontier_localization_v1/tasks/DMC__LiM_2plus__primary/geom.xyz` | 实测 |
| sha256 | `f619c13234e5455fe0651b7444728e423c1df9975e456c4af0692ce901f8d505` | `sha256sum` 实测 |
| 电荷/多重度声明 | `* xyzfile 2 2 geom.xyz` | 同目录 `job.inp:5` |
| 运行时电子身份 | `Total Charge 2` / `Multiplicity 2` / `Number of Electrons 49` | `…/primary/attempt/job.log:585,586,587` |
| 原子数/组成 | `Number of atoms … 13`；组成 C3 H6 O3 Li1（1 个 Li） | `job.log:388` + 几何文件实测 |
| 正常终止 | `****ORCA TERMINATED NORMALLY****` | `job.log:1873` |
| 生产表里的身份（**已更正**） | `DMC\|LiM_2plus\|primary` 的 **`final_geometry_sha256`** 就是 `f619c132…`（该行 `start_geometry_sha256` 为**空**；`log_sha256 = 45d4a8b0…` 与其 `work/hpc_anfreq_cohort_20261016/hpc_runs/DMC_LiM_2plus/job.log` 实测哈希一致） | `outputs/physics_completion/ensembles/production_ensemble_structures.csv:38` |

**未确定项（如实登记，不当作已知）**：该几何的生产者 Opt 末能量 `-350.979560146132 Eh` 与后续单点/AnFreq 的 `-350.979562164385 Eh` 相差约 `2.02e-6 Eh`，成因未查到证据，本预注册不据此下任何结论；也不把任何旧容差当作协议可比性容差。

**排除清单**：11 组历史候选已逐一排除并给出理由（含唯一一条电荷写错的腿 `hpc_torsion_probe_v1_reopt_v3`，其输入为 `* xyzfile 0 2`、日志 `Total Charge 0 / NEL 51`），完整见 `work/exp_line_20261031/DMC_LIM2PLUS_START_AUDIT.md`（只读子代理交付，本会话已抽查其关键引用）。

## 3. 冻结项与被声明的新数值协议

| 类别 | 内容 |
|---|---|
| **物理方法（冻结，不得改）** | `wB97X-D4 / def2-TZVPD / SMD(acetonitrile) / 298.15 K` |
| **五项阈值（冻结）** | TolE `2e-7`、TolMaxG `3e-5`、TolRMSG `8e-6`、TolMaxD `2e-4`、TolRMSD `1e-4` |
| **本次声明的新数值协议** | `VeryTightSCF` + `EnforceStrictConvergence TRUE`（连同五项 Tol 显式写进 `%geom`） |
| **布局** | 分阶段 `Opt` → `AnFreq`，**同一 Slurm 作业内**、两份独立输入、两个独立日志，**永不拼接** |
| **不得同批改动** | 网格、SCF 参数以外的设置、坐标体系、任何自动追加构象 |
| **如实声明** | SCF 严谨度与停止策略**同时变化**，本次试验**不隔离**任一分项 |

## 4. 资源、预算与门控（HOLD 状态）

| 项 | 值 |
|---|---|
| 核数 / 墙钟 | 16 核 / 最长 4 h（`%pal nprocs 16` 与 Slurm 分配一致；sbatch 断言 `SLURM_NTASKS == 16`） |
| 最坏预留 | **64 core-hours**（16 × 4，**不得向下舍入**） |
| 来源 | `recovery_rescue_pool_600ch`（池上限 600；不动筛选余额；**不提高池上限**） |
| 提交次数 | **1 次**；失败/超时/身份异常一律停止，**不自动重启、不自动续算** |
| 结算 | 终态后按 `sacct AllocCPUS × ElapsedRaw` 实测结算，不用 64 CH 预留冒充实际 |
| 门控 | `submission_gate=HOLD`；`attempts_ledger.json` 只有一条 `planned` 行记录这 64 CH |

池余额核对（详见 `LEDGER_SLURM_JOURNAL_AUDIT_20261031.md`）：真实队列为空、在飞预留 0；600 池在"报告基准 187.0 CH + 报告后实测 13.30223 CH"下可用约 **399.7 CH**（口径 A）或 **408.5 CH**（口径 B，EC 战线另计）。**结论：余额足以容纳 64 CH 且不触及 300 CH 储备。**

## 5. 验收规则（逐项 fail-closed，缺一即拒收，不填 0）

Opt 阶段（任一不过 → **不得启动 AnFreq**，作业按失败分类退出）：

1. `ORCA TERMINATED NORMALLY` 存在，且日志内无 ORCA 错误；
2. 运行期电子身份 `charge=2 / mult=2 / NEL=49`（两阶段都必须）；
3. `Strict Convergence ... True` 全程存在；
4. `THE OPTIMIZATION HAS CONVERGED` 存在；
5. 末次几何收敛表**五项**全部 `≤` 冻结阈值且打印的 Tolerance **等于**冻结值（回显容差必须逐位相符）；
6. 末几何与日志末坐标块数值一致（模板驱动按 `bond_graph` 检查物种/原子序/连通性不变）。

AnFreq 阶段（`freq/geom.xyz` 必须字节等于本次 Opt 末几何）：

7. 正常终止 + 电子身份同上；
8. 频率条数 = 3N 且编号连续（39）；
9. **零虚频**；
10. 新鲜 Hessian 文件存在且与几何链接（沿用既有的 `validate_hessian_geometry_invariant` 口径）；
11. 热化学完整、`qRRHO=True`、298.15 K、1 atm、截止频率 = 冻结值 1.00 cm⁻¹。

入账后（**不由本包自行判定**，是生产链的事）：

12. 该成员以 `status=computed` 进入候选/结构表；
13. dedup 给出**可用**的 novelty（`known` 或 `new`，不能是 `unresolved`）；
14. coverage 复核重算 route，得到 `single_basin_verified` 或 `multi_basin_coverage` → `verdict=resolved` → 接受；
15. 只有当 12–14 全过，才谈 45/48 → 46/48。

**本预注册不承诺 13/14 必然成立**：如果这条腿落在既非重复也非新奇的灰区（dedup 证据不可用），它会停在 `dedup_evidence_required`，该态仍然 limited。这正是"不得先要求必须 resolved"的意思。

## 6. 失败分类与停止条件

| 分类 | 触发 | 后续动作 |
|---|---|---|
| `protocol_mismatch` | 输入关键词与登记不符（漏 `VeryTightOpt`/`EnforceStrictConvergence`、`NumGrad`/`NumFreq` 出现） | 停止，修正冻结项后需**新的一次授权** |
| `opt_qc_failed` | 五项中任一超阈、未收敛、严格回显 False | 停止，**禁止同输入重投** |
| `identity_anomaly` | 电荷/多重度/电子数/物种/键图/Li 齿数异常 | 停止，按身份问题处理 |
| `frequency_qc_failed` | 有虚频 | 停止，登记虚频值 |
| `hessian_linkage_failed` | Hessian 与几何不匹配 | 停止 |
| `timeout` | 4 h 用尽 | 停止，按实际核时结算，**不追加** |

停止条件（全部硬性）：单次提交；失败不自动续；不换同起点同机制重投；不通过补 0 或豁免能量项凑齐；不放宽任何阈值；不缩小 48 分母。

## 7. 提交入口缺口（**当前阶段二的硬阻塞**，已机器证明）

受保护提交器 `scripts/wp_production/submit_hpc_batch.py` 的 profile 表（`:26-114`）里**所有 orca profile 都是 4 核**；提交时会比对输入声明的核数与 profile（`:725-731`），不符即拒绝，并明确提示 `"refusing to silently change the resource (version the submitter instead)"`。

实测（`work/exp_line_20261031/hpc_dmc_lim2plus_vtscf16_v1/entry_blocker_probe.py`，输出见同目录 `ENTRY_BLOCKER_PROBE_OUTPUT.txt`）：

```
[OK ] R-1 submission_resources refuses: ValueError: unknown manifest resource_profile: 'orca_dmc_vtscf_16c_4h_v1'
[OK ] R-2 _enforce_submission_gate refuses: ValueError: package 'hpc_dmc_lim2plus_vtscf16_v1' is not authorized for submission (submission_gate='HOLD')
```

⇒ 要让 16 核成为可提交形态，必须先给提交器**版本化加一个 profile**（生产代码写入，属执行 Lead 写入面，本线未改）：

```json
"orca_dmc_vtscf_16c_4h_v1": {"engine": "orca", "cores": 16, "wall_hours": 4,
                             "budget_cap_core_hours": "64",
                             "attempts_ledger_required": True}
```

并按仓库既有纪律做**四处登记**（`README.md`、`docs/65_repo_layout.md`、计数句、`tests/test_wp2_cost_semantics.py`）。备选方案：若用户改判为 4 核，则用现成的 `orca_dmc_vtscf_4h_v1`（cap 16 CH），无需改任何生产代码——**但那就不是用户已授权的 16 核形态，且拿不到"核数收益"这条信息**。

## 7.1 入口缺陷（**2026-10-31 自查更正**：不需要改导入器代码）

即使那条腿完美通过 QC，它今天也**进不了正式表**，但原因与我最初判断的不同：

| 缺口 | 实测证据 | 修法 |
|---|---|---|
| 包的位置 + manifest 缺 `members` | `import_ensemble_structures.py:1260-1285` 的 `iter_packages()` 有**第三条与包名无关的通道**：`REPO.glob("work/hpc_*")` 下任何 **manifest 含非空 `members`** 的包都会被当作系综包（活证：`work/hpc_ec_strict_convergence_v1/manifest.json` 有 `members` 即被发现）；本包嵌在 `work/exp_line_20261031/hpc_...` 且无 `members` | ① 包移到 `work/hpc_<name>/`；② manifest 给出非空 `members` —— **均无需改代码** |
| 候选表里没有本尝试 | `production_ensemble_candidates.csv` 检索 `repaired`/`vtscf` 零命中 | 加一行；`member_role` 必须 ∈ {`round1_extra`, `recovery_v1_start`}（`build_production_ensemble_aggregator.py:696` 硬过滤，代码注释明写缺角色会让状态永远 limited） |

⇒ 第二阶段的提交前检查清单是 **5 项**（§7 的 profile、本节的布局+`members`、候选登记、B6 可比性判据、B7 证据归档），其中只有"候选登记"与"profile"两处属 tracked 生产写入。可执行补丁见 `work/exp_line_20261031/PRODUCTION_PATCH_SPEC_20261031.md`。

## 7.2 协议可比性判据（B6）：今天这个轴**不拦任何东西**

实测：`protocol_comparability` / `coverage_acceptance` 这两个标签在 `scripts/`、`src/`、`tests/`、`config/` 全目录**零消费者**（只在两份文档里被提到）；已实现的"消费者默认排除 pending"只作用于 **coverage-review 轴**（`build_production_ensemble_aggregator.py:644`、`strict_readiness_wiring.py:184-185`）。

含意有两层，必须说清：
1. 好消息：协议可比性 `pending` 不会**卡住**入账链（它不是门）；
2. 坏消息：也就意味着"可比性已通过"这句话今天**没有机器含义**——项目里**没有任何已冻结的可比性判据**（0.10 eV 与 0.10 kcal/mol 都被明令禁止当可比性容差）。所以预报里的"协议可比性"只能在**先立判据**之后才可能被判定，而"立判据"是用户/Lead 的裁决面，不是我能自定的。

## 8. 去重/覆盖的前置测量（Lead 用生产代码的 `kabsch_rmsd` 实测）

冻结点：`DUP_RMSD_A = 0.35`（重原子 Kabsch RMSD，`build_production_ensemble_aggregator.py:73`；判定还需扭转角一致）。

| 比较 | 重原子 Kabsch RMSD | 相对 0.35 | 含义 |
|---|---:|---|---|
| **本起点 `f619c132…` 就是该态既有 primary 成员的末几何（同字节）** | **≈0**（同一份字节） | 远小于阈值 | ⇒ dedup **必然**判同簇，route 只能是 `single_basin_verified`；这不是"预期"，是字节身份直接推出 |
| （次要参照）本起点 ↔ `outputs/week5/c1/DMC/DMC_m1_G2Li.xyz`（`2d24ffb5…`） | **0.2739 Å** | 小于阈值 | 同样落在同一极小簇 |
| （旁证，已用权威成员几何复算）`DMC\|M_plus` 新末几何 `5b0fc24d…` ↔ 其 primary 成员几何 `work/wp2prod/DMC/M_plus/DMC_M_plus_opt.xyz`（sha `5b9e93e0…`） | **0.034771 Å**；与历史 `tors_8_0_1_2` att2 末几何（`60ef9ba4…`）更只有 **0.000326 Å** | 远小于阈值 | 同簇；说明"新数值协议跑同一盆地"是这类态的常态 |

**这条测量把 16 核试验的期望形态钉住了**：它要产出的是一条"严格协议下**独立复现已知极小**"的腿（route 4），而不是一个新盆地。也因此 —— 见 §7 —— 核数收益的评估对象是"**拿到可入账 QC 通过结果所需墙钟**"，不是"找到新盆地"。

## 9. 本文件与任务包**不做**的事

不提交、不改任何标签、不改正式表、不动 `outputs/**` 与 `scripts/**`、不合并进 `work/` 下他人正在写的文件、不释放他人额度、不把这份草案当成用户授权。

## 10. 包内清单（`work/exp_line_20261031/hpc_dmc_lim2plus_vtscf16_v1/`）

| 文件 | 作用 | 校验 |
|---|---|---|
| `manifest.json` | 包身：核数/wall/64 CH/起点 SHA/身份/冻结项/`submission_gate=HOLD` | 在 `PACKAGE_SHA256SUMS` |
| `AUTHORIZATION.json` | HOLD 状态、条件、禁止项、翻到 OPEN 前的入口检查清单 | 同上 |
| `attempts_ledger.json` | 唯一一条 `planned` 行，记录 64 CH 最坏预留 | 同上 |
| `batch_1.sbatch` / `batch_1.txt` / `tasks.txt` | 16 核、4 h、`--array=0-0`、`test SLURM_NTASKS = 16`、`sha256sum -c inputs.sha256` | 同上 |
| `stage_driver.py` | 两阶段驱动（由已验证的 M_plus 驱动改写：**加 Li 共价半径**、身份改为 2/2/49） | 同上 |
| `tasks/DMC/LiM_2plus__opt_p5li/{geom.xyz,job.inp,job_opt.inp,job_freq.inp,inputs.sha256}` | 起点几何 `f619c132…` + 冻结输入（`%pal nprocs 16`、`* xyzfile 2 2`） | 同上 |
| `smoke_test_package.py` | **34 项入口自检**（含"真实 LiM_2plus 日志能被识别成 2/2/49""Li 不再触发 unexpected element"）：实测 **0 failed** | — |
| `entry_blocker_probe.py` + 输出 | 机器证明提交器现在会**拒绝**本包（R-1 未知 profile、R-2 HOLD 门） | — |
| `PACKAGE_SHA256SUMS` | 14 个文件的冻结哈希，`sha256sum -c` 全 OK（14/14） | — |

## 11. 写入面与并发

- 本线独占写：`work/exp_line_20261031/**`、`docs/handoffs/exp_line_20261031/**`、`.dsh-coordination/exp_line_20261031/**`。
- 本线**只读**：`scripts/**`、`outputs/**`、`deliverables/**`、`work/dmc_staged_*`、`work/_audit_rev4_ds/**`、`work/_fpc_*_20261031.*`、`docs/handoffs/ec_submit_20261029/**`（该目录与其他 `_fpc_*` 文件在 2026-10-31 02:13–02:21 仍被另一会话活跃写入）。
- 需要写 `scripts/wp_production/submit_hpc_batch.py` 的 profile 变更时，必须由**唯一指定写入者**执行；在本文件状态下该变更**尚未发生**。