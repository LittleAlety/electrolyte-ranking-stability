# Week 38 / WP1 — 独立方法审计表（本机 128 格实测）

**状态**：矩阵与规则已冻结，且已在本机实测 —— 128 个单点（8 分子 × 4 状态 × 4 设定）全部正常收敛，另加 32 格阳离子弛豫腿用于认证 WP3 的稳健翻转。原始 ORCA 日志留在仓库外，交付层只含派生数值。

## 冻结内容

- 固定条件：SMD 乙腈、298.15 K、溶液标准态 1 mol/L；几何起点 r2SCAN-3c。
- 方法矩阵：8 分子 × 4 状态 × 4 设定 = **128** 单点，另加 32 格弛豫腿。
- 生产候选 ωB97X-D4（def2-TZVP / def2-TZVPD）；审计对照 PBE0-D4（同两基组）。
- 还原态必须使用含弥散函数设定（S2 / S4）；有限基组能收敛**不能**证明束缚。无弥散基组下的还原态格子照样计算，但标 valid_for_decision=false 并排除出决策统计（共 32 格）。
- 方法选择规则：QC 可用率 / 数值稳定性 / 气相 anchor 可比 / rank sensitivity / 实测成本；**不**按翻转数量选方法。

## 实测结果（本机 ORCA 6.1.1，SMD 乙腈）

氧化轴方法展宽（8 分子，跨 4 设定）：竖直 IP 的泛函效应中位 0.369492 eV / 最大 0.456267 eV，基组效应中位 0.027111 eV / 最大 0.038790 eV；绝热 IP 的泛函效应中位 0.246086 eV / 最大 0.337134 eV，基组效应中位 0.028805 eV / 最大 0.036168 eV。状态层的绝对总能级差只作原始登记（含泛函绝对能偏移），不作决策量。

氧化轴逐分子（竖直腿 = 冻结中性几何上的阳离子单点；弛豫腿 = 冻结松弛阳离子几何上的单点）：

| 分子 | 竖直 IP 展宽 (eV) | 绝热 IP 展宽 (eV) | 弛豫位移均值 (eV) |
| --- | --- | --- | --- |
| DMC | 0.476606 | 0.205247 | -0.604356 |
| EMC | 0.351508 | 0.262277 | -1.312755 |
| EC | 0.411793 | 0.196954 | -0.317326 |
| DME | 0.397488 | 0.369097 | -0.596090 |
| GBL | 0.281684 | 0.269301 | -0.323038 |
| SL | 0.370617 | 0.343828 | -0.132383 |
| AN | 0.203735 | 0.228113 | -0.256116 |
| TMP | 0.459490 | 0.322353 | -0.786219 |

## 稳健翻转认证（方案 5.3）

- 判据：each leg is resolved when its 4 method values keep one sign and the smallest absolute value exceeds that leg method spread (population std across the 4 pre-accepted settings); a pair is certified when both legs are resolved with opposite signs。
- 范围：method axis only (4 pre-accepted settings); conformational sampling bounds are not included。
- 结论：certified=**True**（2/2 冻结对）。

| pair | 竖直腿符号 | 绝热腿符号 | min abs d (竖直) | sigma (竖直) | min abs d (绝热) | sigma (绝热) | 认证 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| EMC | GBL | positive | negative | 0.612475 | 0.038732 | 0.327672 | 0.006516 | YES |
| EMC | SL | positive | negative | 0.693322 | 0.009474 | 0.436495 | 0.032367 | YES |

## 验收（14/14 通过）

| check | ok | detail |
| --- | --- | --- |
| matrix_is_full_factorial | PASS | n_rows=128 |
| audit_matrix_is_computed | PASS | computed=128/128 |
| reduction_states_without_diffuse_are_excluded | PASS | flagged=32 (no_diffuse_on_reduction_state) |
| relaxed_leg_is_computed | PASS | computed=32/32 |
| method_spread_is_measured_per_state | PASS | states=32; max spread=20.370 eV |
| robust_inversion_certification_recorded | PASS | certified=True (2/2 pairs) |
| reduction_has_diffuse_option | PASS | diffuse settings=S2,S4 |
| both_functionals_present | PASS | functionals=PBE0-D4,omegaB97X-D4 |
| existing_jobs_are_electronic_layer_only | PASS | 3 个既有载荷被盘点 |
| no_method_selected_by_flip_count | PASS | 冻结规则：QC 可用率 / 数值稳定性 / 气相 anchor 可比 / 固定介质内 rank sensitivity / 实测成本 |
| local_echo_covers_all_settings | PASS | echoed settings=S1,S2,S3,S4 |
| plan_functional_spellings_remapped | PASS | rejections=2; every setting has a verified ORCA keyword |
| smoke_runs_terminated_normally | PASS | runs=4 (neutral SP, audit SP, NumFreq, cation SP) |
| freq_and_smd_available | PASS | NumFreq completed; imaginary=0 |

## 既有可复用作业（只到电子能层）

| 载荷 | 层 | 行数 | 分子 | 复用范围 | 限制 |
| --- | --- | --- | --- | --- | --- |
| outputs/week4/p1_core_set.csv | P1v (gas-phase vertical) | 54 | 18 | electronic-energy layer only | no diffuse functions; no thermal correction |
| outputs/phase2_p1a/p1a_adiabatic.csv | P1a (gas-phase adiabatic) | 12 | 12 | relaxation effect only | reduction axis excluded by the unbound_anion rule |
| outputs/week5/c1_coord_shifts.csv | C1 (Li-coordination) | 12 | 10 | conditional shift demonstration | single representative motif; identity stratification applies |

## 本机方法回显与 smoke 核验（方案 15.4）

工具链：ORCA 6.1.1 - RELEASE；xTB 6.7.1pre (5071a88)。原始日志留在仓库外，不入交付镜像。

| 设定 | 方案拼写 | ORCA 可用关键字 | 泛函回显 | HF 分数 | 色散 | 溶剂 |
| --- | --- | --- | --- | --- | --- | --- |
| S1 | omegaB97X-D4 | wB97X-D4 def2-TZVP | WB97X-V (range-separated) | 0.167000 | DFTD4 V3.4.0 (atom-pairwise) | ACETONITRILE (SMD) |
| S2 | omegaB97X-D4 | wB97X-D4 def2-TZVPD | WB97X-V (range-separated) | 0.167000 | DFTD4 V3.4.0 (atom-pairwise) | ACETONITRILE (SMD) |
| S3 | PBE0-D4 | PBE0 D4 def2-TZVP | PBE (hybrid) | 0.250000 | DFTD4 V3.4.0 (atom-pairwise) | ACETONITRILE (SMD) |
| S4 | PBE0-D4 | PBE0 D4 def2-TZVPD | PBE (hybrid) | 0.250000 | DFTD4 V3.4.0 (atom-pairwise) | ACETONITRILE (SMD) |

smoke run（water，SMD 乙腈；只作支撑性检查，非排序证据）：

| run | 状态 | q/mult | 关键字 | 基函数 | SCF | 末单点 (Eh) | 正常结束 | 墙钟 (s) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | neutral_M | 0/1 | wB97X-D4 def2-TZVP | 43 | 20 | -76.482423279072 | true | 7.245 |
| B | neutral_M_audit_control | 0/1 | PBE0 D4 def2-TZVPD | 58 | 17 | -76.388928931275 | true | 6.100 |
| C | neutral_M_numfreq | 0/1 | wB97X-D4 def2-TZVP NumFreq | 43 | 11 | -76.482428352560 | true | 29.269 |
| D | cation_M_plus | 1/2 | wB97X-D4 def2-TZVPD | 58 | 17 | -76.136730138462 | true | 6.656 |

频率：NumFreq 在 SMD 乙腈下完成，水 3N=9 模式中 6 个近零 + 3 个实频（1588.03 / 3892.52 / 3972.24 cm^-1），**无虚频**。

**方案拼写须改写**：omegaB97X-D4 与 PBE0-D4 在 ORCA 6.1.1 下被拒（UNRECOGNIZED OR DUPLICATED KEYWORD(S)）；正确形式为 wB97X-D4 与 PBE0 D4（色散作独立关键字）。

## 限制

- 128 格与弛豫腿 32 格都是**气相 r2SCAN-3c 冻结几何**上的 SMD 单点，不是溶液相完全优化；8 分子口径，不等同方案 6 的完整生产。
- 电子密度/自旋、热校正与 G 层分解不在本审计范围（只有电子能层）。
- 认证只覆盖**方法轴**（4 个预先接受的设定）；构象采样界限仍未纳入，故不构成完整认证。
- 独立方法审计是 sensitivity assessment，不等于校准的概率误差；1.96×spread 不得自动标成 95% 置信度。
- 本机方法回显与 smoke 仅覆盖单一几何（water）与固定条件，**不**等于候选泛函/基组的完整验证，也**不**是排序证据。
- EMC 无冻结 C1 行，其 [Li(EMC)]+ 几何为本轮新跑的 r2SCAN-3c 松弛（登记在 audit_geometry_note.json，原始几何留在仓库外）。
