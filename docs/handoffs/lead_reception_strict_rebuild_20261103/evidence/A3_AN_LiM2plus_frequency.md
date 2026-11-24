# A3 · AN|LiM²⁺ 前沿频率证据核对（新 strictOpt vs 旧 NumFreq vs 既有 AnFreq）

- 任务：派单 A3「核对新 strictOpt 与旧 NumFreq 的几何、协议、阶段来源及 −115.27 cm⁻¹ 振型；说明固定几何 AnFreq 究竟检验什么、各结果如何改变下一步；不得预先把虚频归因于数值误差」。
- 本轮边界：只读取证，零新增计算、零作业提交、零共享生产文件写入；未改任何标签/账本/阈值；本文不构成任何准入结论。
- 取证脚本：`docs/handoffs/lead_reception_strict_rebuild_20261103/evidence/a3_geometry_probe.py`（只读解析日志几何块与 NORMAL MODES 表）。
- 复现命令（退出码 0）：
  `cd 电解液溶剂HB-Code && PYTHONIOENCODING=utf-8 python docs/handoffs/lead_reception_strict_rebuild_20261103/evidence/a3_geometry_probe.py`

## 0. 结论摘要（逐项对应派单）

1. **阶段来源已查清**：所谓「新 strictOpt」与「旧 NumFreq」是**同一历史作业的两个阶段**——远端 `hpc_verytight_rescue_20261015/tasks/AN/LiM_2plus/attempts/3700781_2_3706757/job.log`（数组父 3700781、元素 2、作业号 3706757），单输入 `Opt NumFreq`：第 1 阶段 Opt（五项实测全过）→ 第 2 阶段 NumFreq 在 Opt 末几何上给出 **−115.27 cm⁻¹ 虚频**。本轮找回该日志（`raw/74240733….log`）后才被核实，故称「新 strictOpt」；NumFreq 是该历史作业自带的频率阶段，故称「旧 NumFreq」。
2. **几何核对**：NumFreq 的计算几何 = Opt 末几何 = `raw/AN_LiM2plus_job.xyz`（SHA `d7d0b63c…`），日志末坐标块与返回 xyz 最大差 **4.976953599800105e-07 Å**（与提案登记值逐位一致）。该几何与生产 primary（`23d738cf…`）最大原始坐标差 **0.0031721326 Å**、正规转动全原子 RMSD 0.0025159 Å。**既有 AnFreq 与旧 superseded NumFreq 都跑在 primary 几何上**（实测与 primary 差 4.798e-07 Å、与 strict 差 0.00317166891646 Å），不是 strict 几何。
3. **协议核对**：三条记录的 方法/基组/溶剂 完全一致（wB97X-D4 / def2-TZVPD / SMD(acetonitrile) / TightSCF SlowConv / nprocs 4 / MaxIter 300）；差异只有两点——Opt 收紧度（strict=VeryTightOpt vs 旧=TightOpt vs AnFreq=无 Opt 单点）与频率方法（NumFreq 数值微分 vs AnFreq 解析 Hessian）。
4. **2×2 证据矩阵（如实并列，不做归因）**：primary 几何上 NumFreq=−127.20（虚）、AnFreq=+37.07（实，两次独立运行逐字节复现）；strict 几何上 NumFreq=−115.27（虚）、AnFreq=**缺失**（正是提案要补的格子）。归因（数值微分误差 / 几何真实软模 / 解析 Hessian 局限）**未确定**，按红线不预判。
5. **−115.27 振型（第 6 模，唯一虚模）**：质量加权份额 3×甲基 H 合计 **87.5%**、Li 7.5%、N 3.3%、C 1.7%；换算实际位移 甲基 H 43.0% / Li 25.3% / N 22.1% / C 9.9% —— **甲基主导的扭/摆型运动，带 Li–N 骨架参与**。对照 AnFreq 的最低模 +37.07 实际位移以 N 40.5%+Li 35.1% 为主（Li···N 配位型），两者**不是同一个运动**。
6. **固定几何 AnFreq 检验什么**：在 **strict 末几何逐原子冻结**、协议冻结（wB97X-D4/def2-TZVPD/SMD/charge 2/mult 2/TightSCF SlowConv）、不带新 Opt 的前提下做一次解析频率 → 补上「方法×几何」矩阵缺失的第四格，**分离方法因素与几何因素**（见 §5 分支表）。它**不**单独闭合身份/登记/去重/覆盖（提案自身 expected_gate 原话），失败即维持 unresolved，不自动派生救援 Opt/更严 SCF/第二作业。
7. 提案状态：`PROPOSED_NOT_AUTHORIZED_NOT_SUBMITTED`（`FIRST_EVIDENCE_PROPOSAL.json`，未授权未提交；96 core-hour 预留上限未批准）。

## 1. 作业与阶段来源（stage provenance）

| 项 | 实测 | 来源 |
|---|---|---|
| 远端路径 | `/home/pengqihang/project/electrolyte_wp2/hpc_verytight_rescue_20261015/tasks/AN/LiM_2plus/attempts/3700781_2_3706757/job.log` | `remote_closure_20261103/fetch_receipts.txt` 第 6 条 |
| 数组别名 | 父 **3700781**、元素/任务 **2**、作业号 **3706757**（`3700781_2_3706757` 三段式） | 同上（路径段）；B1 对账另报 |
| 调度实测 | `3706757\|COMPLETED\|0:0\|983\|4\|3932`（983 s × 4 核 = 3932 核秒 = **1.0922222 core-hour**） | `remote_closure_20261103/remote_job_ledger.txt` |
| 输入（159 B） | `! wB97X-D4 def2-TZVPD Opt NumFreq SMD(acetonitrile) VeryTightOpt TightSCF SlowConv` / `%maxcore 2000` / `%pal nprocs 4 end` / `%scf MaxIter 300 end` / `* xyzfile 2 2 geom.xyz`（charge 2, mult 2, 7 原子） | `raw/AN_LiM2plus_job.inp`（SHA `3ed23496…`）；日志回显 line 233 同文 |
| 阶段 1 Opt | 8 个几何收敛步 → `*** THE OPTIMIZATION HAS CONVERGED ***`（line 6049） | `raw/74240733….log`（SHA `74240733…`，371,202 B） |
| 五项收敛表（line 6034–6041，实测值 vs 阈值） | Energy change −0.0000001824 ≤ 0.0000002000 **YES**；RMS gradient 0.0000036530 ≤ 0.0000080000 **YES**；MAX gradient 0.0000087545 ≤ 0.0000300000 **YES**；RMS step 0.0000249047 ≤ 0.0001000000 **YES**；MAX step 0.0000872516 ≤ 0.0002000000 **YES** | 同日志（与 README「6 份新日志中只有该 job.log 五项实测通过」一致） |
| 阶段 2 NumFreq | `36 displaced gradients` → `VIBRATIONAL FREQUENCIES`（line 7245）→ 模式 6 = **−115.27 cm⁻¹ ***imaginary mode***（line 7256）→ `ORCA TERMINATED NORMALLY`（line 7672） | 同日志 |
| 返回几何 | `raw/AN_LiM2plus_job.xyz`（577 B，7 原子，头 `Coordinates from ORCA-job job E -139.957603326526`） | SHA `d7d0b63cece256cdfbc863363d42d59a9da4e6afb0116a5ba7cce145cf79ece6` |
| Hessian | `raw/AN_LiM2plus_job.hess`（24,054 B，`$orca_hessian_file`） | SHA `a9e9898b545f69aef634a9d32f48b9818daf28bab9525f75b99d26ab4bffb3f2` |
| 同目录另一 Opt 日志 | `raw/9bafa96f….log`（2.26 MB）= 远端 `hpc_tmp_conformation_rescue_20261015/tasks/TMP/LiM_plus__c04`，与 AN 无关（内含的 115.27 是二面角 `A(O 3,P 2,O 4)` 打印，非频率） | `fetch_receipts.txt` 第 2 条 + 内容核验 |

**「新 strictOpt」与「旧 NumFreq」的关系结论**：同一日志、同一输入卡的先后两阶段；Opt 的末几何就是 NumFreq 的计算几何（单作业 `Opt NumFreq` 的 ORCA 语义；实测日志末坐标块 vs 返回 xyz 差 4.977e-07 Å）。二者**几何同源、协议同卡**，不存在"两次独立作业协议不一致"的问题；不一致的是**与既有记录之间**（§3、§4）。

## 2. 几何核对（实测，探针输出）

| 记录 | 日志坐标块数 | 首块 vs primary | 末块 vs primary | 末块 vs strict | 判读 |
|---|---|---|---|---|---|
| primary 参照 `AN_LiM_2plus_opt.xyz`（`23d738cf…`） | — | — | — | **0.0031721326 Å**（原始坐标最大差） | 与 strict 差 0.003 Å 级 |
| strict 末几何 `raw/AN_LiM2plus_job.xyz`（`d7d0b63c…`） | — | — | — | 0 | 提案固定几何 |
| AnFreq `hpc_anfreq_audit_20261016`（`60c353e2…`） | 1（单点） | **4.7978073e-07** | 同左 | 0.00317166891646 | **跑在 primary** |
| AnFreq `hpc_anfreq_cohort_20261016`（`708d9573…`） | 1（单点） | **4.7978073e-07** | 同左 | 0.00317166891646 | **跑在 primary** |
| 旧 NumFreq `superseded_numfreq/AN_LiM_2plus.log`（`db71f140…`） | 37（Opt 迭代） | 0.226606133（起点远离） | **4.7978073e-07** | 0.00317166891646 | TightOpt 从远离处收敛**到 primary**，NumFreq 在 primary |
| 新 strictOpt+NumFreq `raw/74240733….log`（`74240733…`） | 10（Opt 迭代） | **4.7978073e-07**（输入=primary） | **4.9769535998e-07**（=strict） | 4.9769535998e-07 | 以 primary 为输入，VeryTightOpt 再走 0.00317 Å 到 strict，NumFreq 在 strict |

- 备注：AnFreq/旧 NumFreq 末块与 primary 差 4.8e-07 Å 是日志打印精度（6 位小数）造成的残差，二者与 primary 是同一几何；binding 文件登记的 0.00317166891646 是「日志坐标 vs strict」，与提案登记的 0.003172132582920005（xyz 文件 vs strict）互为精度不同的同一事实。
- 这同时解释了上游事实「46 条 primary 实测至少一项超过严格阈值、仅 1 条（AN LiM²⁺）严格收敛五项通过」：primary 是 TightOpt 收敛点，strict 是 VeryTightOpt 再收紧后的收敛点，位移仅 0.003 Å。

## 3. 协议核对（输入回显逐行）

| 记录 | 输入卡（日志回显行号） | Opt 阶段 | 频率方法 |
|---|---|---|---|
| 新 strictOpt+NumFreq（3706757，找回） | `! wB97X-D4 def2-TZVPD Opt NumFreq SMD(acetonitrile) VeryTightOpt TightSCF SlowConv`（line 233） | **VeryTightOpt**（五项过） | NumFreq（数值微分，36 位移梯度） |
| 旧 superseded NumFreq | `! wB97X-D4 def2-TZVPD Opt NumFreq SMD(acetonitrile) TightOpt TightSCF SlowConv`（line 233） | TightOpt（收敛到 primary） | NumFreq |
| 既有 AnFreq ×2 | `! wB97X-D4 def2-TZVPD AnFreq SMD(acetonitrile) TightSCF SlowConv`（audit line 225；`* xyzfile 2 2 geom.xyz` line 229） | **无 Opt**（单点，输入=primary） | AnFreq（解析 Hessian） |

三次记录的 方法/基组/溶剂/SCF 设置（TightSCF SlowConv、MaxIter 300、maxcore 2000、nprocs 4、charge 2 / mult 2）**全部一致**；差异仅：① 频率方法 NumFreq↔AnFreq；② Opt 收紧度 VeryTightOpt↔TightOpt↔无；③ 几何 strict↔primary。

## 4. 频率记录全表（实测原文）

### 4.1 「方法×几何」矩阵

| 几何 \ 方法 | NumFreq（数值微分） | AnFreq（解析 Hessian） |
|---|---|---|
| **primary**（`23d738cf…`） | **−127.20 cm⁻¹ 虚**（superseded，`db71f140…`，line 23185） | **+37.07 cm⁻¹ 实**（audit `60c353e2…` line 1542 / cohort `708d9573…`；两份日志除起始 banner 外**逐字节相同**——diff 仅 174–177 行的启动时间/主机/PID/工作目录：19:31:57 n0344 vs 22:59:22 n0337，频率表完全一致 = 独立两次运行确定性复现） |
| **strict**（`d7d0b63c…`） | **−115.27 cm⁻¹ 虚**（找回 3706757，`74240733…`，line 7256） | **缺失** ← `FIRST_EVIDENCE_PROPOSAL.json` 要补的唯一格（`existing_same_geometry_AnFreq_bound: false`） |

### 4.2 三条完整频率表（cm⁻¹，scaling 1.0）

| mode | NumFreq@strict（新，3706757） | NumFreq@primary（旧，superseded） | AnFreq@primary（既有 ×2） |
|---|---|---|---|
| 0–5 | 0.00（平动/转动） | 0.00 | 0.00 |
| **6** | **−115.27 虚** | **−127.20 虚** | **+37.07** |
| 7 | 102.55 | 106.61 | 108.68 |
| 8 | 198.20 | 197.38 | 127.08 |
| 9 | 217.67 | 216.61 | 217.48 |
| 10 | 394.68 | 394.45 | 395.79 |
| 11 | 529.93 | 530.39 | 507.35 |
| 12 | 800.58 | 801.43 | 798.18 |
| 13 | 1028.03 | 1026.49 | 1026.96 |
| 14 | 1058.51 | 1055.47 | 1057.82 |
| 15 | 1090.58 | 1088.54 | 1080.56 |
| 16 | 1376.75 | 1376.20 | 1375.95 |
| 17 | 2125.59 | 2125.70 | 2125.44 |
| 18 | 2647.76 | 2651.01 | 2647.09 |
| 19 | 2888.97 | 2892.56 | 2872.54 |
| 20 | 3189.72 | 3190.30 | 3184.75 |

观察（只陈述，不归因）：
- 两条 NumFreq 之间只差 0.003 Å 几何：最低虚模 −127.20→−115.27（差 11.93），模式 7–20 差 ≤0.5%。
- 方法对比（同一 primary 几何）：模式 9–20 三列互差 ≤0.7%，但 **模式 6 符号相反（−127.20 vs +37.07）**、模式 8 分叉（NumFreq 197–198 vs AnFreq 127.08）、模式 7 小差（106.61/102.55 vs 108.68）。
- 每条记录都**只有 1 个虚模**（模式 6），其余 14 个振动模全为实。
- 上述事实**不足以**判定 −115.27 的成因；按红线不将其预归因为数值误差，也不反向断言几何真实失稳。

### 4.3 −115.27 振型（第 6 模，质量加权位移表行=3N 分量，探针实测）

原子序 = 分量序 // 3（`C C N H H H Li`，`raw/AN_LiM2plus_job.xyz`）：

| 原子 | 质量加权份额 | 实际位移份额（×√m） |
|---|---|---|
| H5 | 34.3% | 16.8% |
| H4 | 31.7% | 15.5% |
| H3 | 21.5% | 10.5% |
| Li6 | 7.5% | 25.3% |
| N2 | 3.3% | 22.1% |
| C1 | 1.2% | 7.2% |
| C0 | 0.5% | 2.7% |
| **合计校验** | 100.0%（归一） | 100.0% |

- **判读**：三个甲基 H 合计 87.5%（质量加权）→ **甲基主导的扭摆型虚模**，Li/N 有实质参与（实际位移口径 Li 25.3% + N 22.1%）。
- 对照：AnFreq@primary 的 +37.07 模实际位移以 **N 40.5% + Li 35.1%** 为主（Li···N 配位轴型），质量加权口径 H5 25.1%+Li 24.2%+H3 22.9%+N 13.9% —— 与 −115.27 模**不是同一运动**；两法的「最低模」在原子构成上不同，与 §4.2 模式 6–8 分叉一致。
- 分量原值（−115.27 模，质量加权）：`{0:-0.0085, 1:0.0668, 2:0.0036, 3:-0.0065, 4:-0.0609, 5:-0.0927, 6:-0.0042, 7:-0.1652, 8:-0.0722, 9:-0.3739, 10:0.2357, 11:0.1407, 12:0.3846, 13:0.2744, 14:0.307, 15:0.1458, 16:0.1662, 17:0.5423, 18:0.0116, 19:0.2248, 20:0.1561}`。

## 5. 固定几何 AnFreq 究竟检验什么；各结果如何改变下一步

**检验对象（提案原文 + 本轮核对）**：在 `raw/AN_LiM2plus_job.xyz`（`d7d0b63c…`）**逐原子冻结**、协议冻结（`wB97X-D4 def2-TZVPD SMD(acetonitrile) TightSCF SlowConv; charge=2 mult=2`）、**不带新 Opt** 的一次解析频率 → 同时给出：① 目标解析 Hessian；② 该几何下的虚模判定（按冻结判据）；③ 该候选的热力学修正。**必要性范围**：只补「该候选路径缺目标频率证据」，不证明该态所有恢复路径都要这个实验。

**它分离两个因素**（现有证据只差这一格）：

| 分支（AnFreq@strict 实测将落在哪格） | 能得出什么 | 不能得出什么 | 对下一步的改变 |
|---|---|---|---|
| **A. 实频（≈+37 量级）** | 方法因素在两个几何上都主导：primary 上 NumFreq 虚/AnFreq 实、strict 上同样 NumFreq 虚/AnFreq 实；−115.27 未获解析 Hessian 同几何确认 | 仍**不能**据此断言「−115.27 是数值误差」（也可能解析法在此软模有局限），归因仍需另行判定 | 频率门**不再**由 −115.27 单独卡死，但按提案 stopping_conditions：先回**隔离的身份/登记/去重/覆盖审查**，不自动晋升、不自动派生作业 |
| **B. 虚频（同号）** | 两法在 strict 几何一致判失稳；失稳与几何相关（primary 上解析法为实） | 不区分「几何真实鞍点」与「方法共性局限」 | 冻结虚频判据失败 → 按提案**维持 unresolved**；不自动位移、不救援 Opt、不加严 SCF、不发第二作业 |
| **C. SCF 失败 / 物种漂移 / 协议不匹配** | 无有效频率证据 | — | 按提案维持 unresolved（停止条件第 1 条） |

**无论 A/B/C**：该实验都不闭合身份、登记、去重、覆盖（提案 `expected_gate` 原话：`does not alone close identity, registration, dedup or coverage`）；且当前 AN|LiM²⁺ 生产侧还有**独立未闭合项**——`production_ensemble_labels.csv`：`acceptance=accepted, n_registered=0, n_unique=1, pool_limited=true, coverage_status=not_reviewed, coverage_review_id=空`（**零登记起点、无覆盖审查**），`coverage_recheck.json` 未列该态（它不在 8 态 recheck 池），但「accepted ≠ 覆盖已审」。频率门通过后仍须走登记/覆盖审查，这是下一步的并行必要条件。

**预算参照（非授权）**：历史对照 3706757 = 983 s × 4 核 = 1.0922 core-hour；提案规划区间 0.5–4.0 core-hour（heuristic，非实测预测）、profile `orca_anfreq_only_4c_24h_v1`、预留上限 96 core-hour **未批准**；提案状态 `PROPOSED_NOT_AUTHORIZED_NOT_SUBMITTED`，需用户单独批准，本轮未提交任何作业。

## 6. 未确定事项 / 是否需要新物理证据

| # | 未确定事项 | 状态 |
|---|---|---|
| 1 | −115.27 cm⁻¹ 成因（数值微分伪影 / 几何真实失稳 / 解析法局限） | **归因未确定**，等固定几何 AnFreq 补第四格后才能收窄；按红线未预判 |
| 2 | strict 几何上解析 Hessian 是否同号 | 缺失（提案待批；本轮未授权未提交） |
| 3 | 模式 8 分叉（NumFreq≈198 vs AnFreq 127.08）的模式归属 | 未做全模指认（超出本轮最小需要） |
| 4 | `raw/AN_LiM2plus_job.hess` 与 3706757 的绑定 | 文件在同批找回包内、来源路径同 `hpc_verytight_rescue_20261015`，但包内无独立回执逐项绑定（与日志同源是合理推断，未做机器级绑定证明） |
| 5 | AN\|LiM²⁺ 登记为 0 起点、无覆盖审查 | 事实已固定（labels 行实测）；是否补登记/覆盖审查 = 证据判定后另行决定，本轮只报事实 |

**是否需要新物理证据**：频率维度——**是**（且已有精确到单实验的提案，等授权）；身份/登记/覆盖维度——与频率相互独立，不因频率通过而自动闭合。本报告不提出、不申请任何计算。

## 7. 本节引用文件 SHA256（本轮实测）

| 文件 | SHA256 |
|---|---|
| `raw/74240733bce010708ac42e20e28a15f726eefdf01367a3295c3f608351b7abba.log` | `74240733bce010708ac42e20e28a15f726eefdf01367a3295c3f608351b7abba` |
| `raw/AN_LiM2plus_job.inp` | `3ed23496157405828a2331f0a7b2355685d0920c1d424d334773a2fa02d2d69d` |
| `raw/AN_LiM2plus_job.xyz` | `d7d0b63cece256cdfbc863363d42d59a9da4e6afb0116a5ba7cce145cf79ece6` |
| `raw/AN_LiM2plus_job.hess` | `a9e9898b545f69aef634a9d32f48b9818daf28bab9525f75b99d26ab4bffb3f2` |
| `FIRST_EVIDENCE_PROPOSAL.json` | `9420b6746df55f5fa739382c639bf246e3a2efd23ae2e8bacf3bdfcb58bf2dce` |
| `AN_new_opt_existing_frequency_binding.json` | `65fc3d5c4ec8330703a42b523426cbc4aada3a0a2adc372472a7a2bdbb962bec` |
| `work/hpc_anfreq_audit_20261016/tasks/AN/LiM_2plus/run/job.log` | `60c353e2c13f4e995b7c85648d9cdd2ef927f2148a2dafadb6403e0557411b96` |
| `work/hpc_anfreq_cohort_20261016/hpc_runs/AN_LiM_2plus/job.log` | `708d95733237d88f980580be28f609d409920170d9e64bf672853e1daa7d5c35` |
| `work/wp2prod/AN/LiM_2plus/superseded_numfreq/AN_LiM_2plus.log` | `db71f1403ab21ac82936eef7bb667f095128924b3374602475c9ac23f530c437` |
| `work/wp2prod/AN/LiM_2plus/AN_LiM_2plus_opt.xyz`（primary） | `23d738cf9a8db8db667a142b01f4322ae9f7fd20b10f2acf0eab5f086833cdf7` |
