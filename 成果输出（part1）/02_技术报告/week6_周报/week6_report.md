# Week 6 成果小结 —— Stage 6（T6 构象系综 / T7 C1 虚频 / T8 delta_m / T9 决策稳定性）

本周把「不确定性」写进 pair 判定：先用构象系综量出 `sigma_conf`（T6），再按冻结规则把
`delta_m = max(构象 90 分位展宽, 方法 pstdev, 0.05 eV)` 组装成**候选**值（T8），最后在
`delta_m = 0 / 0.05 eV / docx_max` 三个口径下重算决策稳定性（T9）；并对 Week 5 的 C1
`[Li M]+` 优化几何做纯 Freq 虚频检查（T7）。本文可独立阅读；逐项细节见同目录
`week6_report_full.md`。

## 1. 本周做了什么
构建 12 分子构象系综得到 `sigma_conf`（T6）；按冻结规则组装 `delta_m` 候选值（T8）；在 `delta_m = 0 / 0.05 eV / docx_max` 三个口径下重算决策稳定性（T9）；并对 C1 `[Li M]+` 优化几何做纯 Freq 虚频检查（T7）。

## 2. 关键数字
`delta_m`（docx_max）氧化 **0.700 eV**（67.6 kJ/mol，主导项 method）、还原 **2.074 eV**（200.1 kJ/mol、主导项 method）；并入后 P0->P1 氧化 tau_b 0.667、还原 tau_b 0.545。

## 3. T6：构象系综展宽 `sigma_conf`
| 层 | 目标 | `sigma_conf` [eV] | 90 分位展宽 [eV] | 最大展宽 [eV] | n 分子 |
| --- | --- | --- | --- | --- | --- |
| P0 | 氧化 | **0.021** | 0.035 | 0.203 | 12 |
| P0 | 还原 | **0.095** | 0.221 | 0.744 | 12 |
| P1 | 氧化 | **0.020** | 0.091 | 0.148 | 12 |
| P1 | 还原 | **0.058** | 0.230 | 0.433 | 12 |

构象系综：12 分子 / 32 构象；P0 失败 0、P1 失败 0。

## 4. T8：`delta_m` 组装（候选，尚未写入预注册）
| 目标 | 构象 90 分位 [eV] | 方法 pstdev [eV] | 0.05 eV 下限 [eV] | **delta_m [eV]** | delta_m [kJ/mol] | 主导项 |
| --- | --- | --- | --- | --- | --- | --- |
| 氧化 | 0.091 | 0.700 | 0.050 | **0.700** | 67.6 | method |
| 还原 | 0.230 | 2.074 | 0.050 | **2.074** | 200.1 | method |

source_rule (1) 不可用：锚点 31 行、重复 series **0** 个、非估计方法行 0 个 → `available=False`。

## 5. T9：决策稳定性（主口径 `docx_max`）
| 层对 | 目标 | tau_b [CI95] | f_unresolved（下/上） | 双方均解析 / 总 pair | delta_m 起决定作用 | O_k(20%) | f_robust_inv |
| --- | --- | --- | --- | --- | --- | --- | --- |
| P0 -> P1 | 氧化 | 0.667 [0.133, 1.000] | 0.636 / 0.364 | **22** / 66 | 24 | 0.000 | 0.000 |
| P0 -> P1 | 还原 | 0.545 [-0.016, 0.900] | 0.530 / 1.000 | **0** / 66 | 30 | 1.000 | 0.000 |
| P1 -> P2 | 氧化 | 0.909 [0.700, 1.000] | 0.333 / 0.379 | **39** / 66 | 25 | 1.000 | 0.000 |
| P1 -> P2 | 还原 | 0.848 [0.533, 1.000] | 0.985 / 1.000 | **0** / 66 | 63 | 1.000 | 0.000 |
| C0 -> C1 | 氧化 | 0.689 [0.150, 1.000] | 0.311 / 0.333 | **23** / 45 | 9 | 1.000 | 0.000 |
| C0 -> C1 | 还原 | -0.467 [-0.950, 0.105] | 0.978 / 1.000 | **0** / 45 | 29 | 0.000 | 0.000 |

## 6. T7：C1 `[Li M]+` 优化几何的虚频检查
| 分子 | motif | 最低非零模式 [cm^-1] | n 虚频 | 是否极小 | QC |
| --- | --- | --- | --- | --- | --- |
| EC | m1 | -80.38 | 1 | **否** | imaginary_mode_unresolved |
| DMC | m1 | 96.44 | 0 | 是 | —— |
| DME | m1 | 75.14 | 0 | 是 | —— |
| DOL | m1 | 163.36 | 0 | 是 | —— |
| GBL | m1 | 82.89 | 0 | 是 | —— |
| SL | m1 | 64.33 | 0 | 是 | —— |
| DMSO | m1 | 117.83 | 0 | 是 | —— |
| AN | m1 | 130.84 | 0 | 是 | —— |
| SN | m1 | 109.61 | 0 | 是 | —— |
| TMP | m1 | 55.95 | 0 | 是 | —— |

## 7. 质量与复核（QC）
- T6 构象单点失败数 P0/P1 = 0/0；T7 虚频检查 10/10 成功、1 个非极小；T9 一致性自检 3 条（含 C0->C1 与 Week 5 记录的对比）。
- 上述每一项都由本目录 `verification.json` 的 `checks` 数组从真实产物现场解析得出。

## 8. 产物清单
- `artifacts/F14_delta_m_derivation.png`
- `artifacts/F15_stage6_decision_metrics.png`
- `artifacts/figure_manifest_week6_t9.md`
- `delta_m_frozen.json`
- `delta_m_frozen.md`
- `stage6_decision_stability.csv`
- `stage6_decision_stability.json`
- `stage6_decision_stability.md`
- `structures/conformers/AN/conf_0.xyz`
- `structures/conformers/AN/conf_1.xyz`
- `structures/conformers/DMC/conf_0.xyz`
- `structures/conformers/DMC/conf_1.xyz`
- `structures/conformers/DME/conf_0.xyz`
- `structures/conformers/DME/conf_1.xyz`
- `structures/conformers/DME/conf_2.xyz`
- `structures/conformers/DME/conf_3.xyz`
- `structures/conformers/DME/conf_4.xyz`
- `structures/conformers/DMSO/conf_0.xyz`
- `structures/conformers/DMSO/conf_1.xyz`
- `structures/conformers/DOL/conf_0.xyz`
- `structures/conformers/DOL/conf_1.xyz`
- `structures/conformers/EC/conf_0.xyz`
- `structures/conformers/EC/conf_1.xyz`
- `structures/conformers/EMC/conf_0.xyz`
- `structures/conformers/EMC/conf_1.xyz`
- `structures/conformers/EMC/conf_2.xyz`
- `structures/conformers/GBL/conf_0.xyz`
- `structures/conformers/GBL/conf_1.xyz`
- `structures/conformers/PC/conf_0.xyz`
- `structures/conformers/PC/conf_1.xyz`
- `structures/conformers/SL/conf_0.xyz`
- `structures/conformers/SL/conf_1.xyz`
- `structures/conformers/SN/conf_0.xyz`
- `structures/conformers/SN/conf_1.xyz`
- `structures/conformers/SN/conf_2.xyz`
- `structures/conformers/TMP/conf_0.xyz`
- `structures/conformers/TMP/conf_1.xyz`
- `structures/conformers/TMP/conf_2.xyz`
- `structures/conformers/TMP/conf_3.xyz`
- `structures/conformers/TMP/conf_4.xyz`
- `t6_conformer_manifest.csv`
- `t6_conformer_manifest.json`
- `t6_conformer_spread.csv`
- `t6_conformer_spread.json`
- `t6_conformer_spread.md`
- `t7_c1_freq_check.csv`
- `t7_c1_freq_check.json`
- `t7_c1_freq_check.md`
- `week6_report_full.md`

## 9. 已知限制
1. **Stage 6 的还原轴在当前证据下不可判定**：并入 `delta_m` 后，P0->P1 与 P1->P2 的还原轴「双方均解析」pair 数降为 0，`f_robust_inv` 的分母因此为 0；该指标不得读成「稳定」。
2. `delta_m` 当前是**候选值**，尚未写入 `config/prereg.yaml`（Gate 0 保持 CLOSED）；是否 append 由 PI 裁决。
3. **同家族内部排序当前不可回答**：所有层对 / 目标下，同家族 pair 的 `f_unresolved`（下侧）都是 1.000。
4. Gate 1 仍未关闭：溶液相锚点 31 行仍为 `est`，主结论只依赖气相锚点。
5. 逐项细节见同目录 `week6_report_full.md`。

## 10. 源文件缺失
- 无（全部源路径均存在）
