# Week 4 成果小结 —— Stage 3（P1 电子结构）+ Stage 4（P2 环境）+ T5 + T3 + T2

本周交付了本项目最关键的一级结果：廉价代理层（P0）与电子结构层（P1）、环境层（P2）之间的
「值误差 vs 排序误差」分离，以及两级台阶的对照。本文可独立阅读；逐项细节见同目录
`week4_report_full.md`。

## 1. 本周做了什么
1. **P1（电子结构层）**：对 18 个 core-set 分子在冻结几何 G1 上跑 ORCA 6.1.1 r2SCAN-3c 的
   neutral / cation / anion 三态，共 54 个作业（气相、垂直量）。
2. **P1 QC 审计**：能量一致性、SCF 收敛、异常终止、自旋污染、阴离子束缚性
   （`p1_core_set_audit.json`）。
3. **P1 决策稳定性分析**：与 12 个外部气相锚点比较三臂误差，并做 P0→P1 的排序 / 决策迁移分析。
4. **P2（环境层）**：对同一 18 个分子、同一 G1 几何，用 CPCM(SMD, acetonitrile) 重跑 54 个作业；
   唯一变量是环境（气相 → 隐式溶剂）。
5. **T5 弥散函数对照**：同一泛函 r2SCAN、只换基组（def2-TZVPP 无弥散 / def2-TZVPD 含弥散 /
   r2SCAN-3c 生产基准），对 AN / DMSO / SN / VC 做气相阴离子对照。
6. **T3（CPCM ε 扫描）**：bare CPCM 介电常数扫描（ε = 5/10/20/40）× 12 分子 × 3 态 = 144/144 作业成功，覆盖 core set 全部 8 个结构家族（含补跑的 SL、TMP），几何复用 G1、未重新优化。`outputs/week4/t3_*` 三项已自动纳入本目录。
7. **T2（Opt+Freq / G2 几何台阶）**：对 T3 用的同一 12 分子审计子集，在 r2SCAN-3c 上从 G1 出发做中性 `Opt+Freq` 得到 G2，再在 G2 上重算三态单点；唯一变量是几何。`outputs/week4/t2_*` 两项已自动纳入本目录，虚频照实记录为 `imaginary_mode_unresolved`。

## 2. 关键数字

### 2.1 P0 → P1：三臂与外部气相锚点的值误差（垂直 IP，锚点 = NIST / 已发表值）
| 臂 | n | MAE (eV) | bias (eV) | max abs err (eV) | err std (eV) | Kendall tau_b | Spearman rho |
| --- | --- | --- | --- | --- | --- | --- | --- |
| P0 Koopmans (GFN2-xTB) | 12 | **1.377** | +1.279 | 2.002 | 0.637 | 0.606 [0.16, 0.90] | 0.783 |
| GFN2-xTB ΔSCF | 10 | **4.481** | +4.481 | 5.191 | 0.319 | 0.911 [0.69, 1.00] | 0.976 |
| P1 r2SCAN-3c | 12 | **0.251** | −0.179 | 0.587 | 0.268 | 0.727 [0.38, 0.97] | 0.874 |

读法：**MAE 大不等于决策错**。ΔSCF 的 MAE 是 P0 Koopmans 的 3.3 倍，但它的 tau_b（0.911）
反而最高；P1 的 MAE 最小（0.251 eV），tau_b 却只有 0.727。值误差与排序误差是两件事。

### 2.2 决策层 P0 → P1（N=18，唯一变量 = 电子结构方法）
| 轴 | n | Kendall tau_b | O_k(10%) | O_k(20%) | O_k(30%) | J_k(20%) | selection regret(20%) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 氧化 | 18 | **0.673** | **0.000** | **0.500** | 0.600 | 0.333 | 0.656 eV |
| 还原 | 18 | **0.595** | 1.000 | **0.500** | 0.400 | 0.333 | 0.263 eV |

氧化轴 Top-10% **完全换人**（O_k = 0.000）：廉价层选出的 2 个分子，在 P1 眼中一个都不在前 10%。
还原轴 Top-10% 反而是 1.000，但这是「廉价层还原代理与真实 EA 不是同一物理量」的伪一致（见 §3.3）。

### 2.3 P1 → P2：环境层（唯一变量 = 环境，气相 → SMD 乙腈）
| 量 | n | 均值 | std | 范围 |
| --- | --- | --- | --- | --- |
| 垂直 IP 位移 | 18 | **−2.393 eV** | **0.293 eV** | −2.907 (AN) .. −1.645 (TEGDME) |
| 垂直 EA 位移 | 18 | **+2.173 eV** | **0.311 eV** | +1.376 (TEGDME) .. +2.669 (DOL) |

| 轴 | Kendall tau_b | O_k(10%) | O_k(20%) | J_k(20%) |
| --- | --- | --- | --- | --- |
| 氧化 | **0.895** | 1.000 | 0.750 | 0.600 |
| 还原 | **0.673** | 0.500 | 0.500 | 0.333 |

### 2.4 两级台阶对比（最核心的对照）
| 台阶 | 唯一变量 | IP 位移均值 | **IP 位移 std** | 氧化轴 tau_b | 氧化 Top-20% 重叠 |
| --- | --- | --- | --- | --- | --- |
| P0 → P1 | 电子结构方法（GFN2-xTB → r2SCAN-3c） | −1.550 eV | **0.714 eV** | **0.673** | 0.50 |
| P1 → P2 | 环境（气相 → SMD 乙腈） | −2.393 eV | **0.293 eV** | **0.895** | 0.75 |
| G1 -> G2 | 几何（同一方法 r2SCAN-3c；xTB 几何 vs Opt+Freq 驻点） | -0.002 eV | **0.049 eV** | **0.939** | 1.000 |

**结论：位移更大不等于决策更坏；决定决策是否被改写的是位移的方差。**
环境台阶的平均位移（−2.393 eV）比方法台阶（−1.550 eV）**大 54%**，但它的分子间离散度只有方法
台阶的 **41%**（0.293 vs 0.714 eV），于是排序被破坏得**更少**（tau_b 0.895 vs 0.673；
Top-20% 重叠 0.75 vs 0.50）。这条规律与 §2.1 的锚点结论（MAE 排序与 tau_b 排序不一致）互相印证。

### 2.5 T5 弥散函数对照
| 臂 | 基组 | 含弥散 | AN | DMSO | SN | VC |
| --- | --- | --- | --- | --- | --- | --- |
| tzvpp | def2-TZVPP | 无 | 2.264 | 2.476 | 1.244 | 1.965 |
| tzvpd | def2-TZVPD | 有 | 0.932 | 0.872 | 0.902 | 0.893 |
| scan3c | def2-mTZVPP | 无 | 3.196 | 2.779 | 1.854 | 1.989 |

（`EA_dscf = (E_anion - E_neutral) * 27.211386245988`；**正值表示气相阴离子不束缚**。）

加弥散把气相 EA 系统性下拉 **0.34–1.60 eV**（tzvpd − tzvpp），但四个分子在三个臂下**都不翻转
符号**。AN（0.011 eV）与 DMSO（0.014 eV）的外部锚点落在 0.01 eV 量级，比任何 DFT 泛函的误差棒
（~0.1–0.2 eV）低两个数量级。因此这是一个**方法适用域结论**：本方法不能裁断 0.01 eV 量级的
阴离子束缚与否；T5 测的是弥散位移的**方向与大小**，不是 AN 到底束不束缚。氧化侧（IP）不受此限制。

### 2.6 z 因子修正说明
决策指标的主判据是 `config/prereg.yaml` 冻结的 `z_factor.value = 1.0`（一倍不确定度）；
`z = 1.96`（95% 双侧带）作为**保守敏感性**并列报告。本轮之前分析脚本把 `z = 1.96` 写死，与冻结值
不一致；已改为「主判据 z=1.0 + 敏感性 z=1.96」并列输出。这属于**代码缺陷修复**，不是预注册变更：
`config/prereg.yaml` 逐字节未变，Gate 0 仍为 **CLOSED**。

### 2.7 T2：Opt+Freq 几何台阶（G1 -> G2，唯一变量 = 几何）

对 T3 用的**同一 12 分子审计子集**，在 r2SCAN-3c 上**从 G1 出发**做中性 `Opt+Freq`（得到 G2），
再在 G2 上重算三态单点；方法、基组、电子态、环境全部不动，**唯一变量是几何**。
G2 取自输出里**最后一个** `CARTESIAN COORDINATES (ANGSTROEM)` 块，未做任何额外优化。

| 量 | n | 均值 (eV) | 总体标准差 (eV) | 对该台阶的 Kendall tau_b | Top-20% 重叠 |
| --- | --- | --- | --- | --- | --- |
| dIP = IP(G2) - IP(G1) | 12 | -0.002 | **0.049** | **0.939** | **1.000** |
| dEA = EA(G2) - EA(G1) | 12 | +0.118 | **0.076** | —— | —— |

同口径（位移在 12 个分子上的总体标准差）的三台阶对比见 `F11` 面板 (b)：
**方法（P0 -> P1）0.700 eV；几何（G1 -> G2）0.049 eV；环境（气相 -> bare CPCM 40）0.229 eV**。

这是 `docs/08` §3.4 要求的判据：若几何项与方法项同量级，则 P0 -> P1 的变化不能全部归因于
电子结构方法。实测几何项远小于方法项，因此「方法台阶改写决策」这一结论**未被几何不确定性推翻**。

虚频检查：共 2 个分子报告了虚频（EC、DOL），按 QE 词表记为 `imaginary_mode_unresolved`，照实记录、不予静默删除。


## 3. 质量与复核（QC）
- P1 作业：**54 / 54** 成功，0 失败（`p1_core_set_summary.json`，`n_failed = 0`）。
- P1 审计（`p1_core_set_audit.json`，54 条记录 / 18 分子）：`energy_mismatch = 0`、
  `scf_failed = 0`、`abnormal_termination = 0`、`spin_contamination_flag = 0`；
  `unbound_anion = 18`（18 个分子的气相阴离子在 P1 下**全部**不束缚）。
- P2 作业：**54 / 54** 成功，0 失败（`p2_summary_smd_acetonitrile.json`）。
- T5 作业：**24 / 24** 成功，0 失败（`t5_diffuse_control_summary.json`）。
- T2 作业：**12 / 12** 个 Opt+Freq 成功、12 个 G2 单点成功，失败 **0**；`imaginary_mode_unresolved` = 2（`t2_opt_freq_summary.json`）。
- 全部为垂直量、冻结几何 G1、单一构象；几何在两臂之间完全共享，因此位移只能归因于被改变的那一个变量。
- 以上每一项都由 `verification.json` 的 `checks` 数组从本目录真实产物现场解析得出。

### 3.1 逐分子 IP / EA 对照（可回溯到 `p1_core_set.csv` 与 `p1_anchor_comparison.json`）
| 分子 | 家族 | IP anchor (eV) | P0 Koopmans IP | P1 r2SCAN-3c IP | P0 err | P1 err | EA Koopmans | EA r2SCAN-3c | 气相阴离子束缚 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| DMSO | sulfoxide | 9.10 | 10.42 | 8.81 | +1.32 | −0.29 | 5.36 | −2.78 | NO |
| DME | ether | 9.30 | 10.85 | 8.86 | +1.55 | −0.44 | −0.72 | −3.73 | NO |
| SL | sulfone | 9.80 | 11.25 | 9.79 | +1.45 | −0.01 | 3.85 | −2.98 | NO |
| DOL | ether | 9.90 | 11.02 | 9.31 | +1.12 | −0.59 | 0.08 | −4.09 | NO |
| TMP | phosphate | 10.00 | 11.90 | 10.06 | +1.90 | +0.06 | 1.91 | −2.91 | NO |
| EA | ester | 10.01 | 11.34 | 10.00 | +1.33 | −0.01 | 6.16 | −2.74 | NO |
| VC | cyclic_carbonate | 10.08 | 11.88 | 9.62 | +1.80 | −0.46 | 6.88 | −1.99 | NO |
| MA | ester | 10.20 | 11.43 | 10.20 | +1.23 | 0.00 | 6.24 | −2.74 | NO |
| GBL | ester | 10.26 | 11.40 | 9.95 | +1.14 | −0.31 | 6.29 | −2.58 | NO |
| EC | cyclic_carbonate | 10.40 | 12.40 | 10.77 | +2.00 | +0.37 | 6.08 | −2.59 | NO |
| DMC | linear_carbonate | 11.00 | 12.08 | 10.58 | +1.08 | −0.42 | 5.81 | −3.46 | NO |
| AN | nitrile | 12.20 | 11.61 | 12.14 | −0.59 | −0.06 | 5.50 | −3.20 | NO |
| EMC | linear_carbonate | — | 11.97 | 10.20 | — | — | 5.73 | −3.32 | NO |
| DEC | linear_carbonate | — | 11.89 | 9.98 | — | — | 5.65 | −3.37 | NO |
| PC | cyclic_carbonate | — | 12.26 | 10.54 | — | — | 5.96 | −2.89 | NO |
| FEC | cyclic_carbonate | — | 13.00 | 11.32 | — | — | 6.74 | −2.56 | NO |
| TEGDME | ether | — | 10.61 | 7.60 | — | — | 0.19 | −2.87 | NO |
| SN | nitrile | — | 11.92 | 11.60 | — | — | 6.30 | −1.85 | NO |

只有 12 个分子有外部气相 IP 锚点，故 err 两列对另外 6 个分子为空。EA r2SCAN-3c 列为
`EA_conventional = E_neutral - E_anion`（负值 = 阴离子不束缚）；**18 个分子在 P1 下气相阴离子
全部不束缚**（最后一列全为 NO），这是「还原侧定性失效」的逐分子证据。

### 3.2 pair 分辨率（z 因子敏感性；N=18，两轴各 153 个分子对）
| 轴 | f_unresolved(P0) z=1.0 | f_unresolved(P1) z=1.0 | f_robust_inv z=1.0 | f_unresolved(P0) z=1.96 | f_unresolved(P1) z=1.96 | f_robust_inv z=1.96 | sigma 中位数 (eV) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 氧化 | 0.359 | 0.157 | 0.000 | 0.549 | 0.359 | 0.000 | 0.284 |
| 还原 | 0.170 | 0.621 | 0.000 | 0.706 | 0.699 | 0.000 | 0.786 |

`f_robust_inv` 在两轴、两个阈值下**全为 0**：没有出现「两臂都认为自己分得清、但结论相反」的
分子对。还原侧 P0 只有 0.170 的分子对说不清，P1 却升到 0.621 —— 廉价层在还原轴上「看起来
分得清」，正因为它比的不是真实 EA。放宽到 z = 1.96 时两侧都升到约 0.70，结论方向不变。

## 4. 产物清单
- `artifacts/F10_cpcm_eps_scan.png`
- `artifacts/F11_opt_freq_g2_sensitivity.png`
- `artifacts/F3_value_error_vs_rank_error.png`
- `artifacts/F4_rank_migration_p0_to_p1.png`
- `artifacts/F5_reduction_axis_koopmans_vs_dscf.png`
- `artifacts/F6_decision_stability_indicators.png`
- `artifacts/F7_shift_structure.png`
- `artifacts/F8_environment_layer_p1_to_p2.png`
- `artifacts/F9_diffuse_function_control.png`
- `artifacts/figure_manifest_week4_t2.md`
- `p1_anchor_comparison.json`
- `p1_core_set.csv`
- `p1_core_set_audit.csv`
- `p1_core_set_audit.json`
- `p1_core_set_derived.csv`
- `p1_core_set_summary.json`
- `p1_decision_stability.json`
- `p1_decision_stability.md`
- `p2_core_set_smd_acetonitrile.csv`
- `p2_decision_stability.json`
- `p2_decision_stability.md`
- `p2_environment_effects.csv`
- `p2_summary_smd_acetonitrile.json`
- `t2_opt_freq.csv`
- `t2_opt_freq_summary.json`
- `t3_cpcm_eps_scan.csv`
- `t3_cpcm_eps_scan_report.md`
- `t3_cpcm_eps_scan_summary.json`
- `t5_diffuse_control.csv`
- `t5_diffuse_control_summary.json`
- `week4_report_full.md`

## 5. 已知限制
1. **还原侧定性失效**：P1 下 18 个分子的气相阴离子全部不束缚（EA < 0），而定域在 LUMO 上的
   Koopmans 图像永远给不出这一点。廉价层的还原轴代理与真实 EA 不是同一物理量，还原侧数字只能在
   「廉价层内部比较」的意义上使用。
2. **基组无弥散**：r2SCAN-3c 的复合基组 def2-mTZVPP 不含弥散函数（见 §2.5）。氧化侧不受影响。
3. **单构象 + 隐式溶剂**：G1 为 GFN2-xTB 单构象优化几何，G2 为 r2SCAN-3c 单构象驻点（见 §2.7）；
   两者都仍是单构象、未做构象搜索（`sigma_conf` 仍为「待算」）。P2 为 CPCM(SMD) 隐式溶剂，
   不含显式溶剂分子，也不含 Li+ 配位层（C1 条件态尚未运行）。
4. **锚点 n 小**：外部气相锚点仅 12 个分子，tau_b 的 bootstrap 区间较宽（如 P0 臂为 [0.16, 0.90]）。
5. **T3 已纳入**：`outputs/week4/t3_*`（bare CPCM ε 扫描，144/144 作业）已产出并自动纳入 week4；数值复核见 `verification.json` 的 `checks`。注意 bare CPCM ≠ SMD；「是否出现 robust inversion」依赖 σ 口径，two_arm 与 multi_source 两套结果并列报告。
6. **T2 已纳入**：几何台阶与方法台阶、环境台阶用同一估计量（位移在 12 个分子上的总体标准差）并列比较（`F11`）；虚频按 QE 词表记 `imaginary_mode_unresolved`，照实报告、不静默删除。
7. **Gate 1 仍未关闭**：溶液相锚点 31 行仍为 `est`，本报告的所有主结论只依赖气相锚点。
8. 逐项细节见同目录 `week4_report_full.md`。

## 6. 源文件缺失
- 无（全部源路径均存在）
