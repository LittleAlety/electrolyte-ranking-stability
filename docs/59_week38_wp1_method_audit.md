# Week 38 / WP1 — 独立方法审计表（首轮登记）

**状态**：矩阵与规则已冻结；排序层只盘点既有电子能层作业（零新增计算）；本机方法回显与 smoke 核验为支撑性检查，见下节。

## 冻结内容

- 固定条件：SMD 乙腈、298.15 K、溶液标准态 1 mol/L；几何起点 r2SCAN-3c。
- 方法矩阵：8 分子 × 4 状态 × 4 设定 = **128** 单点上限。
- 生产候选 ωB97X-D4（def2-TZVP / def2-TZVPD）；审计对照 PBE0-D4（同两基组）。
- 还原态必须使用含弥散函数设定（S2 / S4）；有限基组能收敛**不能**证明束缚。
- 方法选择规则：QC 可用率 / 数值稳定性 / 气相 anchor 可比 / rank sensitivity / 实测成本；**不**按翻转数量选方法。

## 验收（9/9 通过）

| check | ok | detail |
| --- | --- | --- |
| matrix_is_full_factorial | PASS | n_rows=128 |
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
| `outputs/week4/p1_core_set.csv` | P1v (gas-phase vertical) | 54 | 18 | electronic-energy layer only | no diffuse functions; no thermal correction |
| `outputs/phase2_p1a/p1a_adiabatic.csv` | P1a (gas-phase adiabatic) | 12 | 12 | relaxation effect only | reduction axis excluded by the unbound_anion rule |
| `outputs/week5/c1_coord_shifts.csv` | C1 (Li-coordination) | 12 | 10 | conditional shift demonstration | single representative motif; identity stratification applies |

## 本机方法回显与 smoke 核验（方案 15.4）

工具链：ORCA 6.1.1 - RELEASE；xTB 6.7.1pre (5071a88)。原始日志留在仓库外，不入交付镜像。

| 设定 | 方案拼写 | ORCA 可用关键字 | 泛函回显 | HF 分数 | 色散 | 溶剂 |
| --- | --- | --- | --- | --- | --- | --- |
| S1 | omegaB97X-D4 | `wB97X-D4 def2-TZVP` | WB97X-V (range-separated) | 0.167000 | DFTD4 V3.4.0 (atom-pairwise) | ACETONITRILE (SMD) |
| S2 | omegaB97X-D4 | `wB97X-D4 def2-TZVPD` | WB97X-V (range-separated) | 0.167000 | DFTD4 V3.4.0 (atom-pairwise) | ACETONITRILE (SMD) |
| S3 | PBE0-D4 | `PBE0 D4 def2-TZVP` | PBE (hybrid) | 0.250000 | DFTD4 V3.4.0 (atom-pairwise) | ACETONITRILE (SMD) |
| S4 | PBE0-D4 | `PBE0 D4 def2-TZVPD` | PBE (hybrid) | 0.250000 | DFTD4 V3.4.0 (atom-pairwise) | ACETONITRILE (SMD) |

smoke run（water，SMD 乙腈；只作支撑性检查，非排序证据）：

| run | 状态 | q/mult | 关键字 | 基函数 | SCF | 末单点 (Eh) | 正常结束 | 墙钟 (s) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | neutral_M | 0/1 | `wB97X-D4 def2-TZVP` | 43 | 20 | -76.482423279072 | true | 7.245 |
| B | neutral_M_audit_control | 0/1 | `PBE0 D4 def2-TZVPD` | 58 | 17 | -76.388928931275 | true | 6.100 |
| C | neutral_M_numfreq | 0/1 | `wB97X-D4 def2-TZVP NumFreq` | 43 | 11 | -76.482428352560 | true | 29.269 |
| D | cation_M_plus | 1/2 | `wB97X-D4 def2-TZVPD` | 58 | 17 | -76.136730138462 | true | 6.656 |

频率：NumFreq 在 SMD 乙腈下完成，水 3N=9 模式中 6 个近零 + 3 个实频（1588.03 / 3892.52 / 3972.24 cm^-1），**无虚频**。

**方案拼写须改写**：`omegaB97X-D4` 与 `PBE0-D4` 在 ORCA 6.1.1 下被拒（`UNRECOGNIZED OR DUPLICATED KEYWORD(S)`）；正确形式为 `wB97X-D4` 与 `PBE0 D4`（色散作独立关键字）。

## 限制

- 已完成本机方法回显与 smoke 核验（方案 15.4）；方案拼写 `omegaB97X-D4` / `PBE0-D4` 须改写为 `wB97X-D4` / `PBE0 D4`。
- 回显与 smoke 仅覆盖单一几何（water）与固定条件，**不**等于候选泛函/基组的完整验证，也**不**是排序证据。
- 既有作业是气相 r2SCAN-3c（无弥散），不能裁断 0.01 eV 量级的阴离子束缚，也不含热校正。
- 独立方法审计是 sensitivity assessment，不等于校准的概率误差；1.96×spread 不得自动标成 95% 置信度。
