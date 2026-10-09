# Week 28 / WP1 数据字典：统一科学证据主表

> 本文件由 `scripts/build_week28_evidence_table.py` 确定性生成（`--check` 逐字节复核）。
> 目录：`outputs/week28/`。上游口径：`config/scientific_definitions.yaml`、`config/prereg.yaml`。

## 0. 三层口径（每一条结论都按这三层表述）

- **模型事实**：两个指定计算模型给出的数值、排序或选择不同。
- **统计判定**：这种差异是否超出独立、可辩护的不确定度。
- **材料意义**：该差异是否影响具体筛选决策，以及目标是否具有外部参考支持。

## 1. 表清单与行数

| 表 | 文件 | 行数 | 说明 |
| --- | --- | --- | --- |
| `molecule_registry` | `outputs/week28/molecule_registry.csv` | 58 | 化学空间定义（core 18 + broad 40） |
| `state_registry` | `outputs/week28/state_registry.csv` | 242 | 每个计算对象的电荷/多重度/化学计量/motif 与 QC、state identity |
| `property_table` | `outputs/week28/property_table.csv` | 392 | 每个 (对象, rung, 轴) 的统一物理目标、数值与来源 |
| `pairwise_table` | `outputs/week28/pairwise_table.csv` | 1326 | 每个 (i, j, 对比, 轴) 的 pair 差、sigma_ij 与 R13 三态判定 |
| `decision_table` | `outputs/week28/decision_table.csv` | 45 | 每个 (对比, scope, 轴, k) 的 Top-k overlap / Jaccard / regret |
| `cost_table` | `outputs/week28/cost_table.csv` | 11 | 每个 rung 的 feature availability、job 数、wall seconds、失败数 |

## 2. value_status 词表

| 取值 | 含义 | 是否允许带数值 |
| --- | --- | --- |
| `ok` | 来源表里有可解析的数值且来源 status 为 ok | 是 |
| `missing` | 该对象在本 rung 的声明范围内，但仓库里没有存数值 | 否 |
| `not_converged` | 作业跑过但 QC 未通过（SCF / 几何 / 状态） | 允许（会带 status_reason） |
| `not_applicable` | 冻结规则把该对象排除出本 rung（例：`unbound_anion` 排除 P1a 还原轴） | 否 |

`UNRESOLVED` **不是** value_status，它只作为 pair 层的 `decision_state` 出现。

## 3. rung 注册表（把「模型」写清楚）

| rung | Axis A | 目标定义 | 几何策略 | 热化学 | 溶剂 | 代价 | 来源 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `P0` | P0 | cheap scalar proxy (GFN2-xTB Koopmans orbital energy) | G1 (single shared geometry, RDKit/MMFF seed, xTB single point) | none (orbital energy) | gas-phase (no continuum) | cheap (GFN2-xTB only) | `outputs/week3/p0_core_set.csv` |
| `P1v` | P1v | gas-phase vertical redox-energy proxy (r2SCAN-3c, three states on one geometry) | G1 shared by neutral/cation/anion (single point only) | vertical: no relaxation and no ZPE for the charged state | gas-phase (no continuum) | expensive (r2SCAN-3c single point) | `outputs/week4/p1_core_set_derived.csv` |
| `P1a` | P1a | gas-phase adiabatic redox thermodynamics (r2SCAN-3c, each charged state relaxed) | G2 (per-charge-state r2SCAN-3c Opt started from G1) | adiabatic: relaxed charged state, no ZPE | gas-phase (no continuum) | expensive (r2SCAN-3c geometry optimisation) | `outputs/phase2_p1a/p1a_adiabatic.csv` |
| `P2a` | P2a | fixed continuum target: CPCM(SMD, acetonitrile) at G1 | G1 (shared, unchanged) | vertical single points inside the production solvent model | CPCM(SMD, acetonitrile) | expensive (r2SCAN-3c single point in solvent) | `outputs/week4/p2_core_set_smd_acetonitrile.csv` |
| `C0` | C0 | free molecule at the G2 geometry (vertical single points) | G2 (T2 relaxed neutral geometry) | vertical single points at the relaxed neutral geometry | gas-phase (no continuum) | expensive (r2SCAN-3c single point) | `outputs/week4/t2_opt_freq.csv` |
| `C1` | C1 | conditional state [LiM]+ (primary motif), vertical at the optimised complex geometry | optimised [LiM]+ motif geometry (m_primary) | vertical single points on the complex | gas-phase (no continuum) | expensive (r2SCAN-3c single point on the complex) | `outputs/week5/c1_coord_shifts.csv` |
| `C2` | C2 | first-shell microsolvation [Li(M)2]+ (coordination number 2) | optimised [Li(M)2]+ geometry | vertical single points on the 1:2 complex | gas-phase (no continuum) | expensive (r2SCAN-3c single point on the 1:2 complex) | `outputs/week8/stage9_shell_shifts.csv` |
| `P2eps@5.0` | P2eps | bare CPCM dielectric scan (eps = 5.0) at G1 | G1 (shared, unchanged) | vertical single points, dielectric-only continuum (no SMD non-electrostatic terms) | bare CPCM, eps = 5.0 | expensive (r2SCAN-3c single point in solvent) | `outputs/week4/p2_core_set_cpcm_5.csv` |
| `P2eps@10.0` | P2eps | bare CPCM dielectric scan (eps = 10.0) at G1 | G1 (shared, unchanged) | vertical single points, dielectric-only continuum (no SMD non-electrostatic terms) | bare CPCM, eps = 10.0 | expensive (r2SCAN-3c single point in solvent) | `outputs/week4/p2_core_set_cpcm_10.csv` |
| `P2eps@20.0` | P2eps | bare CPCM dielectric scan (eps = 20.0) at G1 | G1 (shared, unchanged) | vertical single points, dielectric-only continuum (no SMD non-electrostatic terms) | bare CPCM, eps = 20.0 | expensive (r2SCAN-3c single point in solvent) | `outputs/week4/p2_core_set_cpcm_20.csv` |
| `P2eps@40.0` | P2eps | bare CPCM dielectric scan (eps = 40.0) at G1 | G1 (shared, unchanged) | vertical single points, dielectric-only continuum (no SMD non-electrostatic terms) | bare CPCM, eps = 40.0 | expensive (r2SCAN-3c single point in solvent) | `outputs/week4/p2_core_set_cpcm_40.csv` |

## 4. 逐表字段

### `molecule_registry`

| 字段 | 含义 |
| --- | --- |
| `mol_id` | 项目内唯一分子 ID（core C01..C18 / broad B01..B40） |
| `name` | 分子名（主表所有其它表的连接键） |
| `smiles` | SMILES |
| `family` | 化学家族（linear_carbonate / ether / ester / sulfone / ...） |
| `role` | 用途角色（solvent / co-solvent / additive） |
| `population` | 所属分子池：core（18，双方法）或 broad（40，仅廉价层） |
| `donor_atoms` | 给体原子标记（O=;O- 等） |
| `donor_count` | 给体原子数 |
| `donor_types` | 去重后的给体元素类型（O / N / P / S） |
| `heteroatom_count` | 杂原子数 |
| `n_heavy` | 重原子数 |
| `mw` | 分子量 |
| `rotatable_bonds` | 可旋转键数 |
| `tpsa` | 拓扑极性表面积 |
| `functionalization_tags` | 官能化标签（cyclic / fluorinated / chelating / ...） |
| `source_file` | 该行元数据的来源文件 |

### `state_registry`

| 字段 | 含义 |
| --- | --- |
| `state_id` | 计算对象唯一 ID：<mol_id>:<geometry/motif>:<charge_state> |
| `mol_id` | 所属分子 ID |
| `name` | 分子名 |
| `family` | 化学家族 |
| `object_class` | C0_free_molecule / C1_conditional_LiM / C2_firstshell_microsolvation |
| `geometry_label` | 几何标签（G1 = xTB 共享几何；G2 = T2 Opt+Freq 中性几何；motif id） |
| `charge` | 形式电荷 |
| `multiplicity` | 自旋多重度 |
| `stoichiometry` | 该对象的化学计量（free molecule / LiM / Li(M)2） |
| `motif_id` | Li+ 配位 motif ID（C0 为空） |
| `coord_number` | 第一配位壳 Li 的接触数（C2 为 2） |
| `state_identity_label` | R13 state identity 标签（仅条件态；C0 为空） |
| `label_source` | state identity 的判定依据（electron / ...） |
| `energy_reference` | 该对象能量所在文件与字段（无独立能量时标 derived_only） |
| `energy_availability` | explicit / derived_only |
| `qc_state` | 来源表里的 status 字段 |
| `qc_flags` | QC flag 词表（v2 §20） |
| `parent_bonds_intact` | 优化后母体分子键是否完整（条件态） |
| `source_file` | 该行来源文件 |

### `property_table`

| 字段 | 含义 |
| --- | --- |
| `mol_id` | 分子 ID |
| `name` | 分子名（pair 连接键） |
| `family` | 化学家族 |
| `population` | core / broad |
| `rung` | 物理层级：P0 / P1v / P1a / P2a / P2eps@e / C0 / C1 / C2 |
| `axis_A` | 该 rung 在 Axis A 上的归属（P0 / P1v / P1a / P2a / P2eps；条件态同其父层） |
| `axis` | oxidation（IP，越大越难氧化）或 reduction（-EA，越大越难还原） |
| `quantity` | 统一目标量名（IP / -EA） |
| `units` | 单位（eV） |
| `direction` | 优化方向（maximise） |
| `value` | 数值（eV）；非 ok 状态为空 |
| `value_status` | ok / missing / not_converged / not_applicable |
| `status_reason` | 非 ok 状态的原因（可追溯） |
| `qc_flags` | 该对象的 QC flag |
| `state_id` | 对应 state_registry.state_id（无条件态时为空） |
| `state_identity_label` | 条件态的 state identity 标签 |
| `in_primary_ranking` | 是否进入 R13 主 ranking（条件态还原轴闸门） |
| `source_file` | 数值来源文件（相对仓库根） |
| `source_field` | 数值来源字段 |

### `pairwise_table`

| 字段 | 含义 |
| --- | --- |
| `comparison` | 阶梯对比名（P0_to_P1v / P1v_to_P1a / P1v_to_P2a / P1v_to_P2eps10 / P0_to_P2a / C0_to_C1 / C1_to_C2） |
| `scope` | all（无 state-identity 过滤）或 primary（R13 主 ranking 集合） |
| `axis` | oxidation / reduction |
| `n_molecules` | 该对比在该 scope 下的**实际候选数**（= 两个 rung 都有 ok 数值的分子，再按 scope 过滤） |
| `common_set_label` | 候选集合的可读名字：core18 / audit12 / subsetNN / single_candidate；跨行比较 f_unresolved 前必须先看这一列 |
| `rung_lower` | 下台阶 rung |
| `rung_upper` | 上台阶 rung |
| `i` | 候选 i（高值优先） |
| `j` | 候选 j |
| `d_lower_ev` | 下台阶的 pair 差 P_i - P_j（eV） |
| `d_upper_ev` | 上台阶的 pair 差 P_i - P_j（eV） |
| `delta_shift_ev` | (d_upper - d_lower)，即差异性位移 delta_i - delta_j（eV） |
| `sigma_ev` | 冻结的双臂 pair 不确定度 sigma_ij = |d_lower - d_upper| / sqrt(2)（eV） |
| `z_primary` | 主判据的 z（1.0，config/prereg.yaml） |
| `threshold_ev` | z * sigma_ij（eV） |
| `resolution_ratio_lower` | |d_lower| / threshold（无量纲） |
| `resolution_ratio_upper` | |d_upper| / threshold（无量纲） |
| `resolved_lower` | 下台阶是否 resolve（|d| >= z*sigma） |
| `resolved_upper` | 上台阶是否 resolve |
| `resolved_both` | 两侧是否都 resolve（f_robust_inv 的分母成员） |
| `decision_state` | STABLE / UNRESOLVED / ROBUST_INVERSION |
| `structurally_non_testable` | Week 27 的代数约束：两侧都用同一 sigma_ij 且 z > 1/sqrt(2) 时不可能出现反向 pair |

### `decision_table`

| 字段 | 含义 |
| --- | --- |
| `comparison` | 阶梯对比名 |
| `scope` | all / primary |
| `axis` | oxidation / reduction |
| `n_molecules` | 候选数 n（该对比在该 scope 下的实际候选数；跨行不可比，见 common_set_label） |
| `common_set_label` | 候选集合名字：core18 / audit12 / subsetNN / single_candidate |
| `n_pairs` | C(n,2) |
| `k_fraction` | Top-k 的 k/n（0.10 / 0.20 / 0.30） |
| `k` | Top-k 的绝对 k（四舍五入，至少 1） |
| `selected_lower` | 下台阶选出的候选 ID（分号分隔） |
| `selected_upper` | 上台阶选出的候选 ID |
| `overlap` | Top-k 集合重叠数 / k |
| `jaccard` | Top-k Jaccard 系数 |
| `selection_regret_ev` | 以更深一层为目标、以浅一层为代理的 selection regret（eV） |
| `kendall_tau_b` | Kendall tau_b |
| `spearman_rho` | Spearman rho |
| `f_unresolved_lower` | 下台阶 UNRESOLVED pair 占比 (z=1.0) |
| `f_unresolved_upper` | 上台阶 UNRESOLVED pair 占比 (z=1.0) |
| `f_unresolved_lower_z1p96` | 下台阶 UNRESOLVED pair 占比 (z=1.96) |
| `f_unresolved_upper_z1p96` | 上台阶 UNRESOLVED pair 占比 (z=1.96) |
| `n_stable` | decision state = STABLE 的 pair 数 |
| `n_unresolved` | decision state = UNRESOLVED 的 pair 数 |
| `n_robust_inversion` | decision state = ROBUST_INVERSION 的 pair 数 |
| `f_robust_inversion` | ROBUST_INVERSION / 两侧都 resolve 的 pair 数（分母可为 0） |

### `cost_table`

| 字段 | 含义 |
| --- | --- |
| `rung` | 物理层级 |
| `axis_A` | Axis A 归属 |
| `cost_class` | cheap（仅 GFN2-xTB）或 expensive（r2SCAN-3c） |
| `feature_availability` | 该 rung 作为特征时在建模时是否可得（廉价代理可用 / 必须完成该层计算后才可得） |
| `n_objects` | 该 rung 有 property 行的**分子**数 |
| `n_property_rows` | property_table 中该 rung 的总行数（= 分子 x 轴） |
| `n_value_rows` | property_table 中该 rung 的 ok 数值行数 |
| `n_missing` | missing 行数 |
| `n_not_converged` | not_converged 行数 |
| `n_not_applicable` | not_applicable 行数 |
| `n_qc_flagged` | 带 QC flag 的对象数 |
| `wall_seconds` | 来源表记录的 wall seconds 之和（0.0 可能表示未记录） |
| `wall_seconds_note` | wall_seconds 的口径说明（未记录时明确写出，避免读成 0 成本） |
| `n_failed_jobs` | 来源表 status != ok 的作业数 |
| `source_file` | 成本统计的来源文件 |

## 5. scope 语义

- `all`：不做 state-identity 过滤，即 Week 5/6 的原始口径；只用于复核冻结数字。
- `primary`：R13 口径，C1/C2 的还原轴只让 `molecule_centered_redox` 进入主 ranking。
- 当某个对比不含条件态 rung、或 `primary` 与 `all` 的候选集合完全相同时，只输出 `all`
  行；此时“没有 `primary` 行”等价于“`primary` 与 `all` 相同”。

### 5.1 连接键（跨表 join 只用 `name`）

- 五张表的主连接键是 `name`（如 `EC`）；`molecule_registry` / `state_registry` / `property_table` 另外带 `mol_id`（如 `C04`）。
- `pairwise_table.i` / `pairwise_table.j` 与 `decision_table.selected_*` 用的都是 `name`。
- **不要拿 `mol_id` 去 join `pairwise_table`**：那张表里没有 `mol_id`，会静默失配。

### 5.2 分母陷阱（本表最容易被误读的一点）

- `scope='all'` **不是固定人群**：`n_molecules` 是「两个 rung 在该 scope 下都有 ok 数值」的
  分子数，随对比变化（本阶段为 18 / 12 / 10）。
- 因此 `f_unresolved` / `jaccard` / `overlap` / `n_pairs` 在 `decision_table` 的不同行之间
  **不可直接比较**；比较前先看 `common_set_label`（`core18` / `audit12` / `subsetNN` / `single_candidate`）。
- 声明范围与可得范围是两个不同的东西：`declared_scope` 是冻结设计声明的覆盖（每个 rung 的
  出处见 `declared_scope_source`），`property_table` 里的 `missing` 行就是「声明了但仓库里
  没有」的对象。`coverage` 块逐对比逐轴给出 declared / available / used 三者的对账。
- 例：`declared_scope.C1` 是 core 18（`dataset.core_set.purpose` 明写包含 C1 conditional
  Li-coordination），但 C1 实际只做到 10 个分子，所以 `C0_to_C1` 的 `n_molecules = 10`，
  `PC` / `EMC` 在 property 表里是 `missing`。

### 5.3 方向与符号陷阱

- `pairwise_table` 的 `i`/`j` 按**字母序**排列，而 Week 6 的 stored pair 用的是它自己的顺序。
  同一个无序 pair 在两张表里可能以相反方向出现，此时 `d_*` 与 `delta_shift_ev` 差一个负号；
  按无序 pair 比对时应使用 `{i, j}` 并允许整体取负。`frozen_number_reproduction` 用的是
  Week 6 自己的顺序，所以那里是逐位相等（误差 `0.000e+00`）。
- 两轴都是 `higher_is_better`：`oxidation` 的数值是 IP，`reduction` 的数值是 `-EA`。

## 6. 复用的冻结不确定度口径

```
sigma_ij = std([dP_A_ij, dP_B_ij], ddof=1) = |dP_A_ij - dP_B_ij| / sqrt(2)
resolved <=> |dP_ij| >= max(z * sigma_ij, tolerance),  z = 1.0 (prereg), tolerance = 0 (z_only)
```

该口径是 Week 6 冻结的 two-arm 定义；`pairwise_table.sigma_ev` 必须能逐位复现
`outputs/week6/stage6_decision_stability.json` 的 `sigma_ev`（见 check `frozen_number_reproduction`）。

## 7. 结构性不可检验（Week 27 代数结论）

在本约定下 `sigma_ij` 由两个模型共同定义，因此反向 pair 若两侧都要超过 `z * sigma_ij`，
需要 `z <= 1/sqrt(2) = 0.7071`。主判据 `z = 1.0` 下反向 pair **不可能**同时通过两
侧门槛，所以 `ROBUST_INVERSION = 0` 是**结构性的**，不能读成“排序稳定”的证据。
`pairwise_table.structurally_non_testable` 对这一列逐行标注。

