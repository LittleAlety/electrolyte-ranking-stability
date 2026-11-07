# Week 5 成果小结 —— Stage 5（T4：Li+ 配位条件态 C1）

本周把状态轴从 **C0（自由分子）** 推进到 **C1（[Li M]+ 配位态）**：按冻结的 motif 生成规则
（`config/scientific_definitions.yaml` §`conformers_and_states.li_motif_generation`）枚举 Li+ 的
配位结构，在 r2SCAN-3c 上优化几何并做三态垂直量，再与同一分子的自由分子 C0（P1 @ G2）逐分子相减。
本文可独立阅读；逐项细节见同目录 `week5_report_full.md`。

## 1. 本周做了什么
1. **motif 枚举（T4-step1）**：对 10 个分子（8 个结构家族各 1 + 第二醚 DME + 第二腈 AN/SN）按冻结的
   7 步规则生成 [Li M]+ 初始结构（`scripts/build_li_motifs.py`）。
2. **C1 条件态扫描（T4-step2）**：对每个主 motif 做 [Li M]+ `Opt`，并做双阳离子 / 还原态单点与重弛豫、
   以及 CPCM(SMD) 三态单点（`scripts/run_c1_li_coordination.py`）；失败作业照实记为
   `geometry_failed` / `dissociated_optimized_product`，不静默丢弃。
3. **C1 分析（T4-step3）**：逐分子 dIP / dEA、配体交换量 `dGdG_bind(M;R)`（主参考 R = DME，
   次参考 R = AN）、C0 -> C1 决策稳定性，以及方法 / 几何 / 环境 / 条件态四个单变量台阶的同口径 σ。
4. **C1（Li+ 配位条件态，T4）**：按冻结的 motif 生成规则枚举 [Li M]+，在 r2SCAN-3c 上优化配位几何并做三态垂直量，与自由分子 C0（P1 @ G2）逐分子相减；`outputs/week5/*` 已自动纳入本目录。

## 2. 关键数字
### 2.8 C1：Li+ 配位条件态（唯一变量 = 条件态；自由分子 C0 -> [Li M]+ C1）

对 10 个分子（EC、DMC、DME、DOL、GBL、SL、DMSO、AN、SN、TMP）按冻结的 motif 生成规则枚举 [Li M]+ 初始结构（12 个 motif），
在 r2SCAN-3c 上优化配位几何并做三态垂直量；C0 参考取同一分子在 P1 @ G2 上的自由分子值。
唯一变量是条件态（是否带一个 Li+），方法、基组与环境口径全部沿用同一套。

| 量 | n | 均值 (eV) | 总体标准差 (eV) |
| --- | --- | --- | --- |
| dIP = IP(C1) - IP(C0) | 10 | +4.887 | **0.564** |
| dEA = EA(C1) - EA(C0) | 10 | +6.578 | **0.790** |

**四个单变量台阶的同口径对比**（同一批分子、同一估计量 population std；见 `F12` 面板 (b)）：

| 台阶 | IP 位移均值 | **IP 位移 std** | n |
| --- | --- | --- | --- |
| 方法（P0 -> P1） | -1.299 eV | **0.745 eV** | 10 |
| 几何（G1 -> G2） | -0.012 eV | **0.048 eV** | 10 |
| 环境（气相 -> SMD 乙腈） | -2.465 eV | **0.256 eV** | 10 |
| 条件态（C0 -> C1，Li+ 配位） | +4.887 eV | **0.564 eV** | 10 |

配位台阶的 IP 位移离散度（0.564 eV）与方法台阶（0.745 eV）之比为 0.76。

C0 -> C1 决策量：氧化 tau_b **0.689**、f_robust_inv **0.000**；还原 tau_b **-0.467**、f_robust_inv **0.000**。

## 3. 质量与复核（QC）
- C1 作业 **91 / 92** 成功，状态计数 `{'ok': 91, 'execution_failed': 1}`；QC 标记：geometry_failed=1, no_intact_minimum_found=4（`c1_li_coordination_summary.json`）。
- 全部为垂直量；C1 的几何是 r2SCAN-3c 优化得到的 [Li M]+ 驻点，与 C0 的 G2 自由分子几何不同 ——
  这正是被改变的那一个变量。
- 以上每一项都由 `verification.json` 的 `checks` 数组从本目录真实产物现场解析得出。

## 4. 产物清单
- `artifacts/F12_li_coordination_c1.png`
- `artifacts/F13_c1_state_identity.png`
- `artifacts/figure_manifest_week5_c1.md`
- `artifacts/figure_manifest_week5_state_identity.md`
- `c1_adversarial_audit.md`
- `c1_coord_shifts.csv`
- `c1_decision_stability.json`
- `c1_decision_stability.md`
- `c1_li_coordination.csv`
- `c1_li_coordination_summary.json`
- `c1_ligand_exchange.csv`
- `c1_records/AN_m1_cation_opt_c1_record.json`
- `c1_records/AN_m1_cation_opt_orca.json`
- `c1_records/AN_m1_cation_sp_smd_c1_record.json`
- `c1_records/AN_m1_cation_sp_smd_orca.json`
- `c1_records/AN_m1_dication_opt_c1_record.json`
- `c1_records/AN_m1_dication_opt_orca.json`
- `c1_records/AN_m1_dication_sp_c1_record.json`
- `c1_records/AN_m1_dication_sp_orca.json`
- `c1_records/AN_m1_dication_sp_smd_c1_record.json`
- `c1_records/AN_m1_dication_sp_smd_orca.json`
- `c1_records/AN_m1_reduced_opt_c1_record.json`
- `c1_records/AN_m1_reduced_opt_orca.json`
- `c1_records/AN_m1_reduced_sp_c1_record.json`
- `c1_records/AN_m1_reduced_sp_orca.json`
- `c1_records/AN_m1_reduced_sp_smd_c1_record.json`
- `c1_records/AN_m1_reduced_sp_smd_orca.json`
- `c1_records/DMC_m1_cation_opt_c1_record.json`
- `c1_records/DMC_m1_cation_opt_orca.json`
- `c1_records/DMC_m1_cation_sp_smd_c1_record.json`
- `c1_records/DMC_m1_cation_sp_smd_orca.json`
- `c1_records/DMC_m1_dication_opt_c1_record.json`
- `c1_records/DMC_m1_dication_opt_orca.json`
- `c1_records/DMC_m1_dication_sp_c1_record.json`
- `c1_records/DMC_m1_dication_sp_orca.json`
- `c1_records/DMC_m1_dication_sp_smd_c1_record.json`
- `c1_records/DMC_m1_dication_sp_smd_orca.json`
- `c1_records/DMC_m1_reduced_opt_c1_record.json`
- `c1_records/DMC_m1_reduced_opt_orca.json`
- `c1_records/DMC_m1_reduced_sp_c1_record.json`
- `c1_records/DMC_m1_reduced_sp_orca.json`
- `c1_records/DMC_m1_reduced_sp_smd_c1_record.json`
- `c1_records/DMC_m1_reduced_sp_smd_orca.json`
- `c1_records/DMC_m2_cation_opt_c1_record.json`
- `c1_records/DMC_m2_cation_opt_orca.json`
- `c1_records/DMC_m2_cation_sp_smd_c1_record.json`
- `c1_records/DMC_m2_cation_sp_smd_orca.json`
- `c1_records/DMC_m2_dication_sp_c1_record.json`
- `c1_records/DMC_m2_dication_sp_orca.json`
- `c1_records/DMC_m2_dication_sp_smd_c1_record.json`
- `c1_records/DMC_m2_dication_sp_smd_orca.json`
- `c1_records/DMC_m2_reduced_sp_c1_record.json`
- `c1_records/DMC_m2_reduced_sp_orca.json`
- `c1_records/DMC_m2_reduced_sp_smd_c1_record.json`
- `c1_records/DMC_m2_reduced_sp_smd_orca.json`
- `c1_records/DME_m1_cation_opt_c1_record.json`
- `c1_records/DME_m1_cation_opt_orca.json`
- `c1_records/DME_m1_cation_sp_smd_c1_record.json`
- `c1_records/DME_m1_cation_sp_smd_orca.json`
- `c1_records/DME_m1_dication_opt_c1_record.json`
- `c1_records/DME_m1_dication_opt_orca.json`
- `c1_records/DME_m1_dication_sp_c1_record.json`
- `c1_records/DME_m1_dication_sp_orca.json`
- `c1_records/DME_m1_dication_sp_smd_c1_record.json`
- `c1_records/DME_m1_dication_sp_smd_orca.json`
- `c1_records/DME_m1_reduced_opt_c1_record.json`
- `c1_records/DME_m1_reduced_opt_orca.json`
- `c1_records/DME_m1_reduced_sp_c1_record.json`
- `c1_records/DME_m1_reduced_sp_orca.json`
- `c1_records/DME_m1_reduced_sp_smd_c1_record.json`
- `c1_records/DME_m1_reduced_sp_smd_orca.json`
- `c1_records/DMSO_m1_cation_opt_c1_record.json`
- `c1_records/DMSO_m1_cation_opt_orca.json`
- `c1_records/DMSO_m1_cation_sp_smd_c1_record.json`
- `c1_records/DMSO_m1_cation_sp_smd_orca.json`
- `c1_records/DMSO_m1_dication_opt_c1_record.json`
- `c1_records/DMSO_m1_dication_opt_orca.json`
- `c1_records/DMSO_m1_dication_sp_c1_record.json`
- `c1_records/DMSO_m1_dication_sp_orca.json`
- `c1_records/DMSO_m1_dication_sp_smd_c1_record.json`
- `c1_records/DMSO_m1_dication_sp_smd_orca.json`
- `c1_records/DMSO_m1_reduced_opt_c1_record.json`
- `c1_records/DMSO_m1_reduced_opt_orca.json`
- `c1_records/DMSO_m1_reduced_sp_c1_record.json`
- `c1_records/DMSO_m1_reduced_sp_orca.json`
- `c1_records/DMSO_m1_reduced_sp_smd_c1_record.json`
- `c1_records/DMSO_m1_reduced_sp_smd_orca.json`
- `c1_records/DOL_m1_cation_opt_c1_record.json`
- `c1_records/DOL_m1_cation_opt_orca.json`
- `c1_records/DOL_m1_cation_sp_smd_c1_record.json`
- `c1_records/DOL_m1_cation_sp_smd_orca.json`
- `c1_records/DOL_m1_dication_opt_c1_record.json`
- `c1_records/DOL_m1_dication_opt_orca.json`
- `c1_records/DOL_m1_dication_sp_c1_record.json`
- `c1_records/DOL_m1_dication_sp_orca.json`
- `c1_records/DOL_m1_dication_sp_smd_c1_record.json`
- `c1_records/DOL_m1_dication_sp_smd_orca.json`
- `c1_records/DOL_m1_reduced_opt_c1_record.json`
- `c1_records/DOL_m1_reduced_opt_orca.json`
- `c1_records/DOL_m1_reduced_sp_c1_record.json`
- `c1_records/DOL_m1_reduced_sp_orca.json`
- `c1_records/DOL_m1_reduced_sp_smd_c1_record.json`
- `c1_records/DOL_m1_reduced_sp_smd_orca.json`
- `c1_records/EC_m1_cation_opt_c1_record.json`
- `c1_records/EC_m1_cation_opt_orca.json`
- `c1_records/EC_m1_cation_sp_smd_c1_record.json`
- `c1_records/EC_m1_cation_sp_smd_orca.json`
- `c1_records/EC_m1_dication_opt_c1_record.json`
- `c1_records/EC_m1_dication_opt_orca.json`
- `c1_records/EC_m1_dication_sp_c1_record.json`
- `c1_records/EC_m1_dication_sp_orca.json`
- `c1_records/EC_m1_dication_sp_smd_c1_record.json`
- `c1_records/EC_m1_dication_sp_smd_orca.json`
- `c1_records/EC_m1_reduced_opt_c1_record.json`
- `c1_records/EC_m1_reduced_opt_orca.json`
- `c1_records/EC_m1_reduced_sp_c1_record.json`
- `c1_records/EC_m1_reduced_sp_orca.json`
- `c1_records/EC_m1_reduced_sp_smd_c1_record.json`
- `c1_records/EC_m1_reduced_sp_smd_orca.json`
- `c1_records/GBL_m1_cation_opt_c1_record.json`
- `c1_records/GBL_m1_cation_opt_orca.json`
- `c1_records/GBL_m1_cation_sp_smd_c1_record.json`
- `c1_records/GBL_m1_cation_sp_smd_orca.json`
- `c1_records/GBL_m1_dication_opt_c1_record.json`
- `c1_records/GBL_m1_dication_opt_orca.json`
- `c1_records/GBL_m1_dication_sp_c1_record.json`
- `c1_records/GBL_m1_dication_sp_orca.json`
- `c1_records/GBL_m1_dication_sp_smd_c1_record.json`
- `c1_records/GBL_m1_dication_sp_smd_orca.json`
- `c1_records/GBL_m1_reduced_opt_c1_record.json`
- `c1_records/GBL_m1_reduced_opt_orca.json`
- `c1_records/GBL_m1_reduced_sp_c1_record.json`
- `c1_records/GBL_m1_reduced_sp_orca.json`
- `c1_records/GBL_m1_reduced_sp_smd_c1_record.json`
- `c1_records/GBL_m1_reduced_sp_smd_orca.json`
- `c1_records/SL_m1_cation_opt_c1_record.json`
- `c1_records/SL_m1_cation_opt_orca.json`
- `c1_records/SL_m1_cation_sp_smd_c1_record.json`
- `c1_records/SL_m1_cation_sp_smd_orca.json`
- `c1_records/SL_m1_dication_opt_c1_record.json`
- `c1_records/SL_m1_dication_opt_orca.json`
- `c1_records/SL_m1_dication_sp_c1_record.json`
- `c1_records/SL_m1_dication_sp_orca.json`
- `c1_records/SL_m1_dication_sp_smd_c1_record.json`
- `c1_records/SL_m1_dication_sp_smd_orca.json`
- `c1_records/SL_m1_reduced_opt_c1_record.json`
- `c1_records/SL_m1_reduced_opt_orca.json`
- `c1_records/SL_m1_reduced_sp_c1_record.json`
- `c1_records/SL_m1_reduced_sp_orca.json`
- `c1_records/SL_m1_reduced_sp_smd_c1_record.json`
- `c1_records/SL_m1_reduced_sp_smd_orca.json`
- `c1_records/SN_m1_cation_opt_c1_record.json`
- `c1_records/SN_m1_cation_opt_orca.json`
- `c1_records/SN_m1_cation_sp_smd_c1_record.json`
- `c1_records/SN_m1_cation_sp_smd_orca.json`
- `c1_records/SN_m1_dication_opt_c1_record.json`
- `c1_records/SN_m1_dication_opt_orca.json`
- `c1_records/SN_m1_dication_sp_c1_record.json`
- `c1_records/SN_m1_dication_sp_orca.json`
- `c1_records/SN_m1_dication_sp_smd_c1_record.json`
- `c1_records/SN_m1_dication_sp_smd_orca.json`
- `c1_records/SN_m1_reduced_opt_c1_record.json`
- `c1_records/SN_m1_reduced_opt_orca.json`
- `c1_records/SN_m1_reduced_sp_c1_record.json`
- `c1_records/SN_m1_reduced_sp_orca.json`
- `c1_records/SN_m1_reduced_sp_smd_c1_record.json`
- `c1_records/SN_m1_reduced_sp_smd_orca.json`
- `c1_records/TMP_m1_cation_opt_c1_record.json`
- `c1_records/TMP_m1_cation_opt_orca.json`
- `c1_records/TMP_m1_cation_sp_smd_c1_record.json`
- `c1_records/TMP_m1_cation_sp_smd_orca.json`
- `c1_records/TMP_m1_dication_opt_c1_record.json`
- `c1_records/TMP_m1_dication_opt_orca.json`
- `c1_records/TMP_m1_dication_sp_c1_record.json`
- `c1_records/TMP_m1_dication_sp_orca.json`
- `c1_records/TMP_m1_dication_sp_smd_c1_record.json`
- `c1_records/TMP_m1_dication_sp_smd_orca.json`
- `c1_records/TMP_m1_reduced_opt_c1_record.json`
- `c1_records/TMP_m1_reduced_opt_orca.json`
- `c1_records/TMP_m1_reduced_sp_c1_record.json`
- `c1_records/TMP_m1_reduced_sp_orca.json`
- `c1_records/TMP_m1_reduced_sp_smd_c1_record.json`
- `c1_records/TMP_m1_reduced_sp_smd_orca.json`
- `c1_records/TMP_m2_cation_opt_c1_record.json`
- `c1_records/TMP_m2_cation_opt_orca.json`
- `c1_records/TMP_m2_cation_sp_smd_c1_record.json`
- `c1_records/TMP_m2_cation_sp_smd_orca.json`
- `c1_records/TMP_m2_dication_sp_c1_record.json`
- `c1_records/TMP_m2_dication_sp_orca.json`
- `c1_records/TMP_m2_dication_sp_smd_c1_record.json`
- `c1_records/TMP_m2_dication_sp_smd_orca.json`
- `c1_records/TMP_m2_reduced_sp_c1_record.json`
- `c1_records/TMP_m2_reduced_sp_orca.json`
- `c1_records/TMP_m2_reduced_sp_smd_c1_record.json`
- `c1_records/TMP_m2_reduced_sp_smd_orca.json`
- `c1_state_identity.csv`
- `c1_state_identity.json`
- `c1_state_identity.md`
- `c1_state_identity_audit.md`
- `c1_summary.json`
- `li_motif_generation.csv`
- `li_motif_generation.json`
- `li_motif_generation.md`
- `plan_alignment.md`
- `structures/li_motifs/AN_m1.xyz`
- `structures/li_motifs/DMC_m1.xyz`
- `structures/li_motifs/DMC_m2.xyz`
- `structures/li_motifs/DME_m1.xyz`
- `structures/li_motifs/DMSO_m1.xyz`
- `structures/li_motifs/DOL_m1.xyz`
- `structures/li_motifs/EC_m1.xyz`
- `structures/li_motifs/GBL_m1.xyz`
- `structures/li_motifs/SL_m1.xyz`
- `structures/li_motifs/SN_m1.xyz`
- `structures/li_motifs/TMP_m1.xyz`
- `structures/li_motifs/TMP_m2.xyz`
- `week5_report_full.md`

## 5. 已知限制
1. **C1（Li+ 配位）只覆盖主 motif**：每个分子只取一个主 motif，本台阶的逐分子样本数为 **10**；未在 motif 之间做能量加权或构象平均。
2. **还原侧不可用**：气相阴离子在 r2SCAN-3c 下全部不束缚（见 week4 报告）；C1 的还原量同样只能在
   条件态内部比较。
3. **单构象**：C1 的 [Li M]+ 结构由几何规则生成并优化，未做构象搜索，也未在 motif 之间做能量加权。
4. **Gate 1 仍未关闭**：溶液相锚点 31 行仍为 `est`，本报告的主结论只依赖气相锚点。
5. 逐项细节见同目录 `week5_report_full.md`。

## 6. 源文件缺失
- 无（全部源路径均存在）
