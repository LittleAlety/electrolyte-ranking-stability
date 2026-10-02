# 电解液溶剂HB —— 决策稳定性研究（Electrolyte Ranking Stability）

在**很小的分子集**（core set = **18** 个分子）上，用**两种**高效量子化学方法（GFN2-xTB 与 r2SCAN-3c），研究「从廉价代理量走向更真实的电子结构 / 环境模型」时，**哪些改变只是数值平移、哪些会真正翻转材料筛选决策**，以及这些翻转背后的物理机制。

> 核心不是「筛出最好的电解液」，而是：
> cheap proxy → validated target → uncertainty-aware rank change → mechanism → minimal budget

**项目状态**：`Gate 0` **CLOSED** · `Gate 1` **未闭合**（排序层已评估：`ordering_disagrees`，τ_b = 0.4286 < 0.90，n_pairs = 21；绝对标定层按 limitation 处理）。

> 本 README 由 `scripts/build_github_readme.py` 确定性生成：逐周关键数字尽量从 `outputs/` 的冻结产物读回，`--check` 逐字节复核。全量汇总另见仓库外 `成果输出/数据结果汇总.md` 与 `成果输出/统一数据文档.md`。

## 科学定位与核心问题

- **廉价代理 → 经验证目标**：P0 = GFN2-xTB Koopmans 代理；P1 = ORCA r2SCAN-3c 三态垂直 IP/EA（气相）；P2 = P1 + CPCM(SMD, 乙腈)。相邻层之间**只有一个变量**在变（P0→P1 换电子结构方法，P1→P2 换环境），几何 G1 与构象全层共享。
- **不确定性感知的排序变化**：pair 级主判据是 `resolved(i,j) ⇔ |ΔP_ij| ≥ max(z·σ_ij, delta_m)`；`config/prereg.yaml` 冻结 `z = 1.0` 为主口径，`z = 1.96` 只作并列敏感性。
- **机制**：位移的**离散度**（而非幅度）决定排序是否被改写 —— `f_unresolved(z) = Pr(q_ij > √2/z)`，其中 `q` 是位移相对目标轴的割线斜率；符号比幅度重要。
- **最小信息预算**：闭式判据（花钱前预判）+ 介电层自相似（可稀疏采样）+ 配位层只算第一壳 + 漏解只做靶向。
- 科学方案：`核心文件/ranking-electrolyte-materials-v2.md`；阅读清单：`核心文件/ranking-electrolyte-materials-reading-list.md`；项目计划：`计划.md`。

## 逐周工作日志（Week 1 – Week 25）

每周列出「做了什么 + 关键数字 + 产物路径」。数字旁注的文件是唯一来源；`outputs/week22`（Stage 23 批次 B）与 `outputs/week22_hardening`（W22-H）为两个不同工作包，`outputs/week24_corealign` 对应 Week 24，`outputs/week25` 对应 Week 25。

### Week 1 —— Stage 0：定义冻结与 Gate 0（`outputs/week1`）

- 冻结科学定义与预注册（`config/scientific_definitions.yaml`、`config/prereg.yaml`）；本 README 现场重算 `prereg.yaml` SHA256 = `e89f2e2ab714ac42…`。
- 建立 chemical-space 元数据：core set **18** 行、broad pool **40** 行（`data/metadata/core_set.csv`、`data/metadata/broad_pool.csv`）。
- Gate 0 = **CLOSED**：4 项检查全部通过、`amendment_log` 为空、冻结产物逐字节重算一致（`outputs/week1/gate0_record.md`、`docs/00_stage0_definitions.md`）。

### Week 2 —— Stage 1：方法审计与外部锚点（`outputs/week2`）

- GFN2-xTB 12 分子三态方法审计：Koopmans MAE **1.320 eV**（τ_b 0.689）对 ΔSCF MAE **4.451 eV**（τ_b 0.911）——值误差更小的量排序反而更差（`outputs/week2/method_audit_xtb_summary.json`）。
- 气相阴离子不束缚 **2** 个；溶液相锚点 **31** 行逐条证据审计后仍全部 `est`，升级为 `exp`/`calc` 的行数 = **0**（`outputs/week2/solution_anchor_audit.json`）。
- Gate 1 = **NOT CLOSED**：记录 `outputs/week2/gate1_record.md`；周报 `docs/03_week1_2_report.md`。

### Week 3 —— Stage 2：broad cheap pool（P0）（`outputs/week3`）

- GFN2-xTB P0 代理：core **18/18**、broad **40/40** 成功，合并池 **58**，`n_failed = 0`（`outputs/week3/p0_summary.json`）。
- 氧化轴 vs 还原轴（合并池）Kendall τ_b = **-0.302**；参考配体 primary_R = **DME (C08)**（`outputs/week3/decision_stability_preview.md`）。
- 覆盖 / 家族分布图与 ORCA runner dry-run 就绪：`outputs/week3/fig1_family_counts.png`、`coverage_report.md`、`orca_pilot_summary.json`。

### Week 4 —— Stage 3（P1）+ Stage 4（P2）+ T5/T3/T2（`outputs/week4`）

- T1：core 18 × 3 电子态 r2SCAN-3c 气相单点 **54/54 成功、0 失败**，墙钟中位 **29.77 s**（`outputs/week4/p1_core_set_summary.json`）；独立复核 `energy_mismatch = 0`、`scf_failed = 0`、`unbound_anion = 18`（`outputs/week4/p1_core_set_audit.json`）。
- 三臂 vs 气相锚点 MAE：P0 Koopmans **1.377** / GFN2 ΔSCF **4.481** / P1 r2SCAN-3c **0.251 eV**（`outputs/week4/p1_anchor_comparison.json`）。
- P0→P1 决策稳定性：氧化 τ_b **0.673**、还原 τ_b **0.595**（`outputs/week4/p1_decision_stability.json`）。
- 同周还跑了 P2 环境层（SMD 乙腈）、T5 弥散函数对照 24 作业、T3 bare CPCM ε 扫描 144/144、T2 Opt+Freq + G2 三态单点，全部 0 失败（`outputs/week4/t5_diffuse_control_summary.json`、`t3_cpcm_eps_scan_summary.json`、`t2_opt_freq_summary.json`）。

### Week 5 —— Stage 5 / T4：Li+ 配位条件态 C1（`outputs/week5`）

- 生成 `[Li M]+` motif：候选 **46** → 保留 **12**（覆盖 10 个分子）；DFT 作业 **92** 个、`ok` **91**（1 个 `execution_failed`）（`outputs/week5/li_motif_generation.json`、`c1_li_coordination_summary.json`）。
- C0→C1 决策稳定性：氧化 τ_b **0.689**、还原 τ_b **-0.467**（还原态 12 个里 11 个电子落在 Li 上）（`outputs/week5/c1_decision_stability.json`、`c1_state_identity.json`）。
- 方法 / 几何 / 环境 / 条件态四台阶同口径 σ 对比；产物 `c1_coord_shifts.csv`、`c1_ligand_exchange.csv`、`figure_manifest_week5_*.md`。

### Week 6 —— Stage 6：T6 构象 / T7 虚频 / T8 `delta_m` / T9 决策稳定性（`outputs/week6`）

- T6 构象系综 σ_conf（12 分子 / 32 构象）组装出 `delta_m`：氧化 **0.700 eV**、还原 **2.074 eV**，主导项均为 `method`（`outputs/week6/delta_m_frozen.json`、`t6_conformer_spread.json`）。
- T9 并入 `delta_m` 后 P0→P1 氧化 τ_b **0.667**、还原 τ_b **0.545**（docx_max 口径，`outputs/week6/stage6_decision_stability.json`）。
- T7 C1 虚频检查 10/10 成功；还原轴在 `f_robust_inv` 分母降为 0 时**不可判定**，该指标不得读成「稳定」。

### Week 7 —— Stage 7（ML / Δ-learning）+ Stage 8（active-learning replay）（`outputs/week7`）

- Stage 7：三种拆分 × direct/shift × 6 模型 × 5 种子 = **288** 行结果；LOFO 外推普遍显示 shift 学习优于 direct（`outputs/week7/stage7_ml_results.json`）。
- Stage 8：4 条 acquisition 曲线、**296** 行曲线、20 组冻结种子；给出 `n_T → τ_b` 的最小昂贵信息预算曲线（`outputs/week7/stage8_al_results.json`、`stage8_al_curves.csv`）。
- 特征成本分级 X0 / X1 / X2 与 `outputs/week7/feature_manifest.json` 一并冻结。

### Week 8 —— Stage 9：显式微溶剂化 C2 = `[Li(M)2]+` 第一溶剂壳（`outputs/week8`）

- `[Li(M)2]+` 第一溶剂壳：**12** 个 motif（覆盖 **8** 个家族）、DFT 作业 **36/36 ok**（`outputs/week8/stage9_summary.json`）。
- C1→C2 排序稳定性：氧化 τ_b **0.697**、还原 τ_b **0.848**（all12 口径，`outputs/week8/stage9_results.json`）。
- 壳层枚举 18432 个放置 → 10401 无冲突 → 48 打分 → 12 入选；`f_robust_inv` 全 0 但 `f_unresolved` 最高 0.273（`stage9_shell_shifts.csv`）。

### Week 9 —— Stage 10：五级台阶合成与决策稳定性总判（`outputs/week9`）

- 把方法 / 环境 / 几何 / 条件态 / 第二壳五个台阶放到 common-10 同一口径重算，得 **10** 个 (台阶, 轴) 组合（`outputs/week9/stage10_ladder.json`）。
- 中心命题：位移**离散度**决定排序是否被改写 —— Spearman ρ(std, τ_b) = **-0.851**、ρ(|mean|, τ_b) = -0.535、ρ(std, f_unresolved) = +0.894（`outputs/week9/stage10_ladder.json`，W22-H 复核见 `outputs/week22_hardening/stats_b1_b2.json`）。
- `f_robust_inv` 在 20 个组合中恒为 **0.000**，但 `f_unresolved` 最高 0.800 —— 这个 0 是「不可判定」而非「稳定」；v2 §23 最小成果判据 11 条中 10 PASS、1 PARTIAL。

### Week 10 —— Stage 11：σ 的代数解剖与分辨率判据（`outputs/week10`）

- 证明并数值验证 4 条恒等式（T1–T4）+ 1 条精确分解（T5）；判据 `f_unresolved(z) = Pr(q_ij > √2/z)`，闭式与实测在 20 个点上误差**精确为 0**（`outputs/week10/stage11_sigma_anatomy.json`）。
- 可预测性：带符号斜率 `ols_slope_b` 的 AUC = **1.000**（精确置换 p = 1/120 = 0.0083、LOO 10/10），无符号 `sd(delta)` 仅 0.810。
- 子集漂移：N = 10 时 P0→P1 氧化轴 τ_b 抽样标准差 **0.126** —— 报 τ_b 必须同时报 N 与子集。

### Week 11 —— Stage 12：介电自相似律与事前预警协议（`outputs/week11`）

- 把 bare CPCM 介电扫描提升为第 6 类台阶，凑成 **18** 个台阶事件（8 介电 + 10 电子结构），全部落在 common-10 上（`outputs/week11/stage12_prescreen.json`）。
- 介电位移落在 Born 单参数自相似族：20 条曲线 mean R² = **0.9936**（Onsager 对照 0.8835）；只用 ε = 5/10/20 预测 ε = 40，最大相对误差 2.44%。
- 8 个介电台阶全部良性（`b > 0`、τ_b ≥ 0.867、无一改写清单）；事前预警 k = 5 平均抓 96%（AUC 0.946）、k = 8 一次不漏（`outputs/week11/stage12_prescreen.json`）。

### Week 12 —— Stage 13：介电极限与 ORCA 能量账本（`outputs/week12`）

- 新增 108 个 ORCA 单点（ε = 80/200 + SMD 水），介电阶梯由 5 级升到 7 级；6 个介电点 Born 形式 mean R² = **0.9861**、Onsager 0.8779（`outputs/week12/stage13_analysis.json`）。
- 导体极限触达：ε = 200 与 u → 1 平均只差 **0.0037 eV**（最差 0.0332 eV）；外推 ε = 40/80/200 最大绝对误差 0.0637/0.0763/0.0841 eV。
- 环境账本（SMD 乙腈）：氧化位移 -2.4489 = 介电 -2.5328 + 畸变 +0.0839；SMD CDS / Δ(D4) / Δ(gCP) 对垂直量精确为 0（`stage13_state_ledger.csv`）。

### Week 13 —— Stage 14：畸变项归因与 EMC 离群点诊断（`outputs/week13`）

- 逐态畸变惩罚 D_neutral / D_cation / D_anion = **0.0685 / 0.1120 / 0.3710 eV**（216/216 为正、变分检验无例外，通道不对称 6.95 倍）（`outputs/week13/stage14_attribution.json`）。
- 唯一稳健关系：D_neutral 对自身偶极 ρ = +0.909、留一 R² = 0.634；D_anion 与两个轴观测量**不可预测**（§14 的区间被 510 种聚合穷举证否）。
- EMC 离群点：插入 5 个新介电点（**63** 个 ORCA 作业、0 失败），九点阶梯把拐点定位到 ε 10 → 20（`outputs/week13/stage14_outlier.json`）。

### Week 14 —— Stage 15：双初猜协议、电子弥散度描述符与溶液锚点扫描（`outputs/week14`）

- 双初猜 90 点中 **12** 点超 1 meV 且**全部为负**、反向 0 次，最大惩罚 **0.2860 eV**（`outputs/week14/stage15_two_guess_analysis.json`）。
- EMC 还原轴九点 Born R² 0.6788 → **0.9556**、符号变化 4 → 0；ε = 200 → 1000 只走 11.3 meV。
- 弥散度描述符把 D_anion 最佳留一 R² 从 0.162 提到 **0.630**（`spin_maxfrac`，ρ = +0.811）（`outputs/week14/stage15_diffuseness.json`）；31 行溶液锚点 4 行可裁定、3 改 1 确认，Gate 1 仍 NOT CLOSED。

### Week 15 —— Stage 16：全核心集双初猜目录与事前预警规则（`outputs/week15`）

- 12 分子 × 3 态 × 10 电介质 × 2 初猜 = **360** 个配对单元格：一致 328、**32** 个 MORead 更低、**0** 个更高（`outputs/week15/stage16_catalogue_analysis.json`）。
- 最大赤字 **-0.2860 eV**（EMC / anion / ε = 1000）；10 点阶梯下 **5/12** 个分子被判定存在漏解。
- 事前预警规则在留出臂失败（发现集 LOO 0.708 < 多数类 0.792、留出真阳 0）—— 结论只能是「事后靶向 + 容许量」，不是「事前预报」。

### Week 16 —— Stage 17：亚稳态污染上限与两个 SCF 解的电子结构身份（`outputs/week16`）

- SMD 层改用 moread 初猜重算 54 格：仅 **6** 格 |Δ| > 1 meV，最坏 **0.1562 eV**（`outputs/week16/stage17_contamination.json`）。
- 两臂 τ_b 的 95% CI 两条轴均重叠，published 结论被改写的条数 = **0**（`any_published_conclusion_rewritten = False`）；`f_robust_inv` 保持 0。
- 32 个漏解配对格里两个 SCF 解都是自旋纯双重态（⟨S²⟩ 32/32 落在 0.75 ± 0.01）；该「0 变非 0 结构性不可能」是本流水线结论，不是普适定理。

### Week 17 —— Stage 18：全目录电子身份普查与零成本自诊断（`outputs/week17`）

- **414** 对身份普查（零新增 QM）：判据 `charge_l1 > 0.039`，可测子集 AUC = **1.000**、混淆 TP 37 / FN 0 / FP 0 / TN 239（`outputs/week17/stage18_identity_census.json`）。
- 漏解全部集中在 cyclic_carbonate(15)、phosphate(10)、linear_carbonate(10)、ether(2)；ester / nitrile / sulfone / sulfoxide 四个家族零漏解。
- 零成本自诊断失败：冻结规则在留出臂只有 **0.796**、输给多数类 0.907（TP 0）；唯一站得住的是单边必要条件 —— 无警告可安全放行（37/37 正例都带警告）。

### Week 18 —— Stage 19：几何弛豫检验（第二个 SCF 解能不能扛住弛豫）（`outputs/week18`）

- 37 个 `moread_lower` 格各做两臂 Opt（**74 作业、74 ok / 0 failed**）；弛豫后仍 moread 更低 **5/37**、两解在终点合并 **8/37**、偏好被反转 **32** 格（`outputs/week18/stage19_relax_analysis.json`）。
- |Δ| 中位从单点 **0.11983 eV** 塌到 **0.00196 eV**（缩小 61 倍）。
- 结论：「身份差异多数是真的，但单点上的能量偏好多数是假象」；0.02 Å 阈值只是描述列，不是「同一驻点」的证明。

### Week 19 —— Stage 20：第六级台阶与第二解的跨方法存亡（`outputs/week19`）

- Part 1（零新增计算）把弛豫修正放回台阶：逐分子跨 ε 极差中位 0.0263 eV；还原支 mean/std/相对散布 = -1.953 / 0.160 / 0.08，氧化支 -0.610 / 0.315 / 0.52（`outputs/week19/stage20_relax_rung.json`）。
- Part 2：**74** 个冻结 GFN2-xTB 作业 —— 同一几何上偏好方向一致 **n/a/37（89.2%）**，xTB 自身弛豫把两臂能量差压掉约 **34 倍**（中位 |Δ| 0.0072 → 0.00021 eV）（`outputs/week19/stage20_xtb_arms_analysis.json`）。
- 逐格裁决与 Stage 19 一致度仅 **17/37（45.9%）**，但那是**跨判据**比较（身份判据 vs 几何 RMSD）。

### Week 20 —— Stage 21：临界带能量裁决 + 判据预检 + 溶剂壳氧化还原 + 真回填（`outputs/week20`）

- Part A：3 格 × 21 帧 = **63** 个冻结单点；EC/cation/ε = 5 的弦上鼓包 **0.00424 eV**（k_B T 的 16.5%），Stage 19 的 `distinct_lower` 属过度判定；2/3 格与 RMSD 裁决一致（`outputs/week20/stage21_path_analysis.json`）。
- Part B 阈值重导为 **0.038946**（空档宽 0.000874、无数据点），borderline 3 格、闭壳层反例 0 格越阈（`stage21_protocol.json`）。
- Part C 溶剂壳氧化还原 **24/24** 作业 OK，氧化轴弛豫修正 -0.4053 eV（ρ = 0.797）、还原轴 -5.4512 eV（ρ = −0.790）（`stage21_shell_redox_analysis.json`）。
- Part D：严格 P2 腿 **7/54** 可回填；氧化轴排序被改写（Top-10% 重叠 0.000）、还原轴未被改写（`stage21_refill.json`）。

### Week 21 —— Stage 22 批次 A：三臂对齐 + σ 相图 + 前瞻检验（`outputs/week21`）

- 三条臂对齐到同一批 10 分子（`outputs/week4/p1_anchor_comparison.json:arm_alignment`）：GFN2 ΔSCF τ_b **0.911** vs P1 0.778、P0 0.689；配对 Δτ_b = 0.133，95% CI [-0.200, 0.550]、精确置换 p = 0.8049 ⇒ 三条臂两两全部 unresolved。
- σ 相图：合成模型 ρ(std, τ_b) = **-1.000**、均值平移 max|Δτ_b| = **0.000**；实测 ρ = -0.851（`outputs/week21/sigma_synthetic.json`）。
- 前瞻检验：带符号规则命中 **3/4**、朴素规则 2/4（`outputs/week21/sigma_prospective.json`）。

### Week 22 —— Stage 23 批次 B：热修正抽样 + 导体极限诊断 + NEB 精修（`outputs/week22`）

- R9 热修正抽样：8 分子 × 3 态、24 个 `--ohess` 作业；热修正分子间离散度只有同轴 `delta_m` 的 8.3% / 3.7%，整项略去不改变任何排序结论（`outputs/week22/thermal_correction_sample.json`）。
- R4b：`|dE|·ε` 近似常数（ε = 200 时 2,162 meV，约 2.1 eV）的幂律；ε = 200 残余最大 **19.62 meV**（氧化轴 `delta_m` 的 2.80%），ε = 1000 只剩 3.93 meV（`outputs/week22/dielectric_limit.json`）。
- R11 真 NEB 精修 3/3 格：EC/cation/ε = 5 峰高 **0.000141 eV**（直线界 0.004245 eV 的 1/30.0）—— Stage 19 的 0.02 Å 阈值在该格过度判定（`outputs/week22/neb_refinement.json`）。

### Week 22（W22-H）—— 论文加固、统计证据与统一数据（`outputs/week22_hardening`）

- 零新增电子结构；B1 ρ(std, τ_b) = **-0.8511**、B2 配对 Δτ_b = **0.1838** [95% CI -0.1774, 0.6072]、P(Δ > 0) = 0.8389（`outputs/week22_hardening/stats_b1_b2.json`）。
- B3 多重比较：9 个预警子 Bonferroni / Holm 显著条数 = **0 / 0**（`multiple_compare_b3.json`）。
- A3 漏解容许量 A_axis = **0.1523 eV**（氧化 TMP@ε=5）/ **0.2860 eV**（还原 EMC@ε=1000），2·A_axis 严格界保护 120/120、漏检 0（`allowance_factor2.json`）。
- B5 broad 池预算演示：主判据 Top-10% 并集 **21/40（省 47.5%）**（`outputs/week22_hardening/broad_pool_demo.json`、`outputs/figures/F47_broadpool_budget.png`）。

### Week 23 —— Stage 24 批次 C+D：R5 三次配位 + R8 靶向双腿 + R12 叙事（`outputs/week23`）

- R8：漏解可以被「框住」而不必全局翻倍 —— 靶向规则安全（19 次真实翻转、漏 **0**），氧化省 28.3%、还原省 3.3%；只保护 Top-k 清单的变体（k = 1/2）实测可省 91.7% / 83.3%（`outputs/week23/targeted_two_guess.json`，Top-k 值见 `成果输出/数据结果汇总.md`）。
- 两次预报失败：发现集 LOO **0.708** < 多数类基线 0.792、留出臂真阳 0 ⇒ 策略只能是「事后靶向 + 容许量」，不是「事前预报」。
- R5 第三个配位点在 xTB 层级没有换号（增量同号且绝对值递减，dd(3→2)/dd(2→1) = -0.483 / -0.098），判定 **`consistent_with_saturation`**（`outputs/week23/shell3_xtb_sign_test.json`）。

### Week 24 —— W24-C 核心文件对齐：ML/AL 蒸馏 + 决策量补全 + F51 流程图（`outputs/week24_corealign`）

- ML 蒸馏：LOFO 8 个分组中 **7** 个 Δτ_b > 0（**3** 个配对区间不含 0、中位 **0.463**），24 个组合中 **19** 个不可区分（`outputs/week24_corealign/ml_direct_vs_shift.json`）。
- AL 预算：τ_b ≥ 0.80 需 n_T = 8–9（10 分子池）/ 12–15（18 分子池）（`outputs/week24_corealign/al_budget.json` 的 `key_n_T_by_pool`）。
- 决策量补全：40 个 `f_robust_inv` 数值（2 z × 2 population × 10 点）全为 0，`p_ij` 与闭式 `f_unresolved(z = 1.2816)` 逐点相等、偏差 0.0（`outputs/week24_corealign/decision_metrics.json`）。
- W24-D 可行性审计：本地文献最长同源序列 k = 1，判决 Gate 1 **NOT_CLOSABLE**（`outputs/week24_corealign/gate1_anchor_feasibility.md`）。

### Week 25 —— W25-G1：Gate 1 排序层判据首次评估 + 家族分辨统计（`outputs/week25`）

- 溶液锚点入库：Ue1994 / Okoshi2015 氧化系列 **7** 个核心集分子 / **21** 对首次可评，Kendall τ_b = **0.4286** < 0.90 ⇒ `ok = False`（`reason = ordering_disagrees`，一致 15 / 不一致 6）（`outputs/week25/series_rel_ordering_check.json`、`gate1_oxidation.json`）。
- provenance：收到文件 SHA256 `6aa15654ab5ef5ea…` 被钉死，全部入库行 `repo_verification = transcription_only_not_reverified_against_primary` —— **仓库没有独立复核过任何一行**（`outputs/week25/anchor_ingest_provenance.json`）。
- 还原旁证（DOE 2016，3 分子 / 3 对 < 18）判 `not_evaluable_secondary_only`：是「数据不足」而非「不一致」（`outputs/week25/gate1_reduction_secondary.json`）。
- 家族分辨：**160** 个组合中 **16** 个可估计（native-18 全部、common-10 为 0），跨家族 τ_b(氧化 vs 还原) = **0.2857** [95% CI -0.455, 0.917]（`outputs/week25/family_resolved_stats.json`、`outputs/figures/F52–F54`）。
- §21 计算预算账本：PASS 4 / PARTIAL 4 / MISSING 2；仓库无 CPU-core-hours / p90 作业成本 / frequency-only 成本（`outputs/week25/compute_budget_ledger.json`、`docs/44_week25_compute_budget_ledger.md`）。
- F55 / 核心文件 §24 Figure 5 补全：在 C1 子集（n = 10）上给出配位位移 × 描述符标签的关系——氧化轴 `tpsa` ρ = **−0.890**（精确置换 p = 0.0011）、`donor_count` ρ = **−0.794**（p = 0.0077），还原轴 14 条相关**全部不显著**；标签分层对比 47 条中仅 **3** 条可估计（齿数 / 态身份 / cyclic vs linear，组内 n ≥ 4），其余（组内 n < 4）判 `not_estimable`；ESP 字段仓库内不存在（`not_available_in_repo`）。**未作多重比较校正，属探索性证据、不得称显著**，也不改动任何既有判决（`scripts/analyze_w25_figure_f55.py`、`outputs/week25/figure_f55_stats.json`、`outputs/week25/F55_manifest.md`、`outputs/figures/F55_coord_descriptor_tags.png`）。
- 论文 v5 同步：新增 §3.17「配位位移与描述符标签的关系（§24 Figure 5 的补全）」与图 22，论文图数 21 → **22**（重建后 **34 页**、表 1–15），并按评审意见移除运行页眉；核心文件 §24 对齐表中 Figure 5 由 PARTIAL → **PASS**（`论文/build_paper_docx.py`、`docs/43_week25_corefile_figure_alignment.md`）。

## Gate 状态与未闭合项

| Gate | 状态 | 说明 |
| --- | --- | --- |
| Gate 0（定义冻结） | **CLOSED** | `config/scientific_definitions.yaml` + `config/prereg.yaml` 未被改动，`amendment_log` 为空（`outputs/week1/gate0_record.md`）。 |
| Gate 1（方法 / 锚点） | **NOT CLOSED** | **排序一致性层**首次可评但未通过：Kendall **τ_b = 0.4286 < 0.90**、**n_pairs = 21**，判 **`ordering_disagrees`**（一致 15 / 不一致 6）（`outputs/week25/series_rel_ordering_check.json`）。**绝对标定层**：溶液相锚点 31 行 `est` 按 R7 裁决记为 **limitation**，不再单列 blocker。 |
| Gate 2+ | 未定义 / 未触发 | —— |

- **排序层为什么未闭合**：证据是**预注册的负结果**；数值本身不得事后通过剔除分子、替换模型列或放宽容差「救回」（`docs/40_week25_gate1_report.md`）。要闭合需要一条覆盖 ≥ 7 个核心集分子、同装置 / 同判据、且描述符在溶剂间**真有离散度**的新同源序列。
- **还原轴**：旁证级数据只有 3 分子 / 3 对（< 18），判 `not_evaluable_secondary_only` —— 是「数据不足」，不是「不一致」（`outputs/week25/gate1_reduction_secondary.json`）。
- **上游可行性审计**：W24-D 发现本地文献最长同源序列 k = 1，判 Gate 1 **NOT_CLOSABLE**（`outputs/week24_corealign/gate1_anchor_feasibility.md`）。

## 目录结构与关键路径

| 路径 | 内容 |
| --- | --- |
| `src/electrolyte_ranking/` | 库：`toolchain` / `xtb` / `orca` / `ranking` / `uncertainty` / `provenance` / `qc` |
| `scripts/` | 环境自检、元数据构建、锚点校验、逐周运行器与分析脚本，以及本 README 的生成器 `build_github_readme.py` |
| `data/` | `metadata/`（`core_set.csv` 18、`broad_pool.csv` 40）、`anchors/`（气相 / 溶液相锚点、`within_series_ordering.csv`、`_received/`） |
| `outputs/` | 每周可复现产物 `week1`–`week25`（含 `week22_hardening`、`week24_corealign`）、`figures/`（F0–F55 及清单） |
| `docs/` | Stage 说明与逐周报告（`00`–`44`，**文件名前缀不连续**，以目录为准） |
| `config/` | `scientific_definitions.yaml`（定义冻结）、`prereg.yaml`（预注册阈值，append-only） |
| `tests/` | 单元测试（无 QM 二进制也必须通过） |
| `structures/` | 几何，含 `li_motifs/`、`microsolvation/` |
| `计划.md` | 主计划（定位 / 规模 / 协议 / 周计划 / 交付物） |

仓库**之外**（与代码仓库并列的交付与资料层）：

| 路径 | 内容 |
| --- | --- |
| `..\成果输出\` | 对外交付层：`README.md`（索引 + 一周一张表）、`数据结果汇总.md`、`统一数据文档.md`、`weekN/` 镜像（含 `SHA256SUMS`、`verification.json`） |
| `..\核心文件\` | 科学方案 v2、阅读清单、Gate 1 溶液锚点电位表、文献 |
| `..\论文\` | 结题论文源与 PDF（`build_paper_docx.py` 重建；当前 `_v5`） |

## 快速开始 / 复现

```powershell
# 0. 指向仓库内置的 xTB（6.7.1 Windows 构建，SHA256 已校验）；装好 ORCA 后同样无需环境变量
. .\scripts\activate_toolchain.ps1

# 0b. ORCA 下载完成后一条命令放到位（默认建 junction，不额外占空间）
# .\scripts\setup_orca.ps1 -Source "E:\Downloads\orca_6_1_1_win64"

# 1. 环境自检（无 xtb / ORCA 也会正常返回）
.venv\Scripts\python.exe scripts\check_environment.py

# 2. 重建 / 校验元数据（CSV 是产物，不是手改文件）
.venv\Scripts\python.exe scripts\build_metadata.py --check

# 3. 校验外部锚点
.venv\Scripts\python.exe scripts\validate_anchors.py

# 4. 单元测试
.venv\Scripts\python.exe -m pytest -q

# 5. 重生成项目图（输出 outputs/figures/，含清单与 SHA256）
.venv\Scripts\python.exe scripts\make_summary_figures.py
```

**幂等校验入口（`--check` 逐字节 / 逐像素比对，不一致即非零退出）**：

```powershell
# 本 README 自身
.venv\Scripts\python.exe scripts\build_github_readme.py --check

# Gate 1 / Week 25
.venv\Scripts\python.exe scripts\ingest_gate1_anchor_series.py --check
.venv\Scripts\python.exe scripts\analyze_w25_gate1_oxidation.py --check
.venv\Scripts\python.exe scripts\analyze_w25_figure_f52.py --check
.venv\Scripts\python.exe scripts\analyze_w25_figure_f53.py --check
.venv\Scripts\python.exe scripts\build_week25_deliverables.py --check

# Week 24 交付镜像
.venv\Scripts\python.exe scripts\build_week24_deliverables.py --check

# 交付层（成果输出）
.venv\Scripts\python.exe scripts\build_deliverables.py --dry-run
```

跑一个真实 xTB 任务：

```powershell
. .\scripts\activate_toolchain.ps1
.venv\Scripts\python.exe scripts\run_xtb_job.py `
    --name EC --smiles "C1COC(=O)O1" --charge 0 --job opt --outdir outputs\smoke
```

## 计算栈

| 层 | 方法 | 工具 | 现状 |
| --- | --- | --- | --- |
| 几何 / 频率 / 廉价描述符 | GFN2-xTB | `xtb` | **已就绪**（仓库 `.toolchain/`，6.7.1pre） |
| 单点电子能 | r2SCAN-3c | `ORCA` | **已装 6.1.1**（Windows AVX2 msmpi 构建，装到 `E:\ORCA\orca_6_1_1`，仓库内经 junction 使用；安装 / 版本探测 / 并行与 scratch 策略见 `docs/07_orca_setup_and_runner.md` §10–§15） |

代码在缺少二进制时以 `dry_run` / fake backend 运行，保证测试与流水线可先跑通；真实数值计算需先完成 Stage 1 的 Gate 1。

## 数据与 provenance 纪律

- **锚点为 `transcription_only`**：Week 25 的 Ue1994 / Okoshi2015 与 DOE 2016 锚点全部是**用户提供的转录值**，`repo_verification = transcription_only_not_reverified_against_primary`，收到文件 SHA256 被钉死（`outputs/week25/anchor_ingest_provenance.json`）。`0.1 V` 是 PI 声明的系列重复性，不是来源报告的不确定度。
- **仓库未独立复核**：相关原 PDF 不在 `核心文件/文献`，且沙箱无网络（WinError 10061）——任何一行都没有被仓库独立复核过。
- **冻结产物不得回填**：`config/prereg.yaml` append-only；Week 25 的 `ordering_disagrees` 是预注册负结果，不得通过剔除分子 / 替换模型列 / 放宽容差「救回」，所有剔除只作敏感性分析并同时给出未剔除结果。
- **唯一变量规则**：相邻层只有一个变量在变（P0→P1 换方法、P1→P2 换环境、G1→G2 换几何、C0→C1 换条件态、C1→C2 加第二壳）。
- **z 因子**：`z = 1.0` 为冻结主判据，`z = 1.96` 只作并列敏感性；两者不得混用、不得择优引用。
- **CSV 是产物不是手改文件**：`build_metadata.py --check` 现场重建并逐字节比对。
- **交付层只放蒸馏产物**：原始 ORCA / xTB 输出与二进制 scratch 一律留在仓库 `outputs/`（`成果输出/README.md` 口径说明）。

## 诚实边界

- **core 18 vs 建议 60–100**：v2 建议 core set ≈ 60–100，本项目主动缩小到 18 个 family 覆盖分子，`docs/44` 账本判 **PARTIAL**（`outputs/week25/compute_budget_ledger.json`）。
- **broad 40 vs 建议 300–1000**：v2 建议 broad pool ≈ 300–1000，实际 **40**；broad 池只到 P0 廉价层。
- **未做 RS-hybrid**：v2 把 range-separated hybrid（如 ωB97X-D4 一类）列为生产候选，本项目未运行该类方法；全部能量为单参考 r2SCAN-3c 或 GFN2-xTB。
- **`f_robust_inv` 全 0 是负结果**：Stage 10 的 20 个 (台阶, 轴) 组合、Week 24 的 40 个数值（2 z × 2 population × 10 点）全部为 **0**；这是「不可判定主导」而非「处处稳定」（同一批数据 `f_unresolved` 最高 **0.800**），不得读成稳健性证据。
- **Gate 1 未闭合**：排序层 `ordering_disagrees`（τ_b = 0.4286 < 0.90，n_pairs = 21）、绝对标定层 limitation；溶液相锚点 31 行仍为 `est`（`docs/40_week25_gate1_report.md`）。
- **还原侧定性失效**：P1 气相阴离子 18/18 全部不束缚，Koopmans 还原代理与真实 EA 不是同一物理量；还原轴结论只以 P2 / C1 为载体。
- **基组无弥散**：r2SCAN-3c 的 def2-mTZVPP 不含弥散函数，不能裁断 0.01 eV 量级的阴离子束缚与否（T5）；氧化侧不受此限制。
- **单构象 + G1 / G2 两级几何**：主结果建立在 GFN2-xTB 单构象几何 G1 上，未做全局构象搜索；G2 台阶仅在 12 分子审计子集。
- **隐式溶剂**：P2 为 CPCM(SMD) 隐式溶剂，不含显式溶剂分子；C2 只做第一溶剂壳的几何预筛。
- **锚点样本小**：外部气相锚点仅 12 个分子，τ_b 的 bootstrap 区间较宽（如 P0 臂 [0.16, 0.90]）。

## 工程约定（轻量借鉴 `电解质ML`）

- **可审计**：每个数值可追溯到 mol_id / motif / 几何 / 方法 / 原始输出 / QC 状态。
- **确定性**：xTB 子进程固定单线程，避免 OpenMP 归约次序导致的几何漂移；读写一律 UTF-8（无 BOM）+ LF。
- **预注册**：阈值、k 值、随机种子在看结果前冻结（`config/prereg.yaml`）。
- **verifier**：关键产物由脚本重建而非手改（`build_metadata.py --check`、`build_github_readme.py --check`）。

## 成果输出（交付层）

对外交付件放在与代码仓库并列的 `E:\Claude Code\电解液溶剂-HB\成果输出`（对标下游项目 `E:\Claude Code\电解质ML\成果输出` 的布局）：顶层 `README.md`（索引 + 一周一张表）与 `数据结果汇总.md`、`统一数据文档.md`，以及 `week1`–`week23` 逐周目录与 `week22_hardening`、`week24_corealign`、`week25_gate1` 三个扩展包。每个包含蒸馏结果表（CSV）、汇总（JSON）、报告（MD）、`artifacts/`（PNG 图）、`SHA256SUMS` 与 `verification.json`。

该目录**只放蒸馏产物与图**，不放原始 ORCA / xTB 输出与二进制 scratch（原始输出去仓库 `outputs/` 取），并且可以由脚本**确定性重建**：

```powershell
.venv\Scripts\python.exe scripts\build_deliverables.py
.venv\Scripts\python.exe scripts\build_week24_deliverables.py --check
.venv\Scripts\python.exe scripts\build_week25_deliverables.py --check
```

图表索引 F0–F55：`F47` 属 `week22_hardening`，`F48`–`F51` 属 `week24_corealign`，`F52`–`F54` 属 `week25_gate1`；逐图内容与来源见 `成果输出/数据结果汇总.md` 的「图表索引」表。
