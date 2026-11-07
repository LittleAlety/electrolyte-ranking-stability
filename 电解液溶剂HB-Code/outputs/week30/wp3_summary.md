# Week 30 / WP3：Li+ 配位条件态如何影响 redox 行为

> 阶段：下一阶段实施方案 WP3（RQ2）。产物目录 `outputs/week30/`，交付镜像
> `..\成果输出（part2）\week30/`。本文件由 `scripts/build_week30_wp3_coordination_mechanism.py`
> 确定性生成，`--check` 逐字节复核。**零新增电子结构计算**：唯一输入是 Week 28 冻结主表。

## 0. 一句话结论

Li+ 配位除了改变 redox 数值，还会**改变被还原态的电子身份**：12 个还原态里只有 1 个
（SN）保持分子中心还原，其余 9 个外加电子落在 Li 上。因此 C1 还原轴的排序必须在
state-identity 分层之后才可解释；把它当成「同一个分子被还原的难度」是 observable
identity failure，而不是 ranking instability。氧化轴可以分层后排序（主集合 n=6，tau_b=0.733）。

## 1. 条件态位移与状态身份分层（all scope）

| 对比 | 轴 | 状态身份标签 | n | 主集合 n | mean ΔΔG (eV) | std (eV) | 成员 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| C0_to_C1 | oxidation | no_intact_minimum_found | 4 | 0 | +5.3057 | 0.5933 | AN;DMSO;DOL;SN |
| C0_to_C1 | oxidation | molecule_centered_redox | 6 | 6 | +4.6082 | 0.4376 | DMC;DME;EC;GBL;SL;TMP |
| C0_to_C1 | reduction | Li_centered_or_mixed_redox | 9 | 0 | -6.7617 | 0.6330 | AN;DMC;DME;DMSO;DOL;EC;GBL;SL;TMP |
| C0_to_C1 | reduction | molecule_centered_redox | 1 | 1 | -4.9273 | 0.0000 | SN |
| C1_to_C2 | oxidation | no_intact_minimum_found | 4 | 0 | -1.8235 | 0.1578 | AN;DMSO;DOL;SN |
| C1_to_C2 | oxidation | molecule_centered_redox | 6 | 6 | -1.6175 | 0.2930 | DMC;DME;EC;GBL;SL;TMP |
| C1_to_C2 | reduction | Li_centered_or_mixed_redox | 9 | 0 | +1.2885 | 0.1881 | AN;DMC;DME;DMSO;DOL;EC;GBL;SL;TMP |
| C1_to_C2 | reduction | molecule_centered_redox | 1 | 1 | +0.3898 | 0.0000 | SN |

## 2. 排序影响（Top-k）

| 对比 | scope | 轴 | n | k/N | O_k | regret(eV) | tau_b |
| --- | --- | --- | --- | --- | --- | --- | --- |
| C0_to_C1 | all | oxidation | 10 | 0.2 | 1.000 | 0.0000 | 0.689 |
| C0_to_C1 | primary | oxidation | 6 | 0.2 | 1.000 | 0.0000 | 0.733 |
| C0_to_C1 | all | reduction | 10 | 0.2 | 0.000 | 0.4573 | -0.467 |
| C1_to_C2 | all | oxidation | 10 | 0.2 | 1.000 | 0.0000 | 0.867 |
| C1_to_C2 | primary | oxidation | 6 | 0.2 | 0.000 | 0.1020 | 0.600 |
| C1_to_C2 | all | reduction | 10 | 0.2 | 0.000 | 0.5143 | 0.289 |
| C0_to_C1 | primary | reduction | 1 | - | - | - | - |
| C1_to_C2 | primary | reduction | 1 | - | - | - | - |

`C0_to_C1 / primary / reduction` 只有 1 个候选，配不成 pair，显式记为未定义（不是「稳定」）。

## 3. 描述符关联（只在 R13 主集合上）

| 对比 | 轴 | 描述符 | n | Pearson r | p | Spearman ρ | p |
| --- | --- | --- | --- | --- | --- | --- | --- |
| C0_to_C1 | oxidation | donor_count | 6 | -0.962 | 0.002 | -0.926 | 0.008 |
| C0_to_C1 | oxidation | heteroatom_count | 6 | -0.825 | 0.043 | -0.772 | 0.072 |
| C0_to_C1 | oxidation | n_heavy | 6 | -0.457 | 0.362 | -0.338 | 0.512 |
| C0_to_C1 | oxidation | rotatable_bonds | 6 | -0.047 | 0.930 | +0.000 | 1.000 |
| C0_to_C1 | oxidation | tpsa | 6 | -0.885 | 0.019 | -0.928 | 0.008 |
| C1_to_C2 | oxidation | donor_count | 6 | -0.771 | 0.073 | -0.617 | 0.192 |
| C1_to_C2 | oxidation | heteroatom_count | 6 | -0.622 | 0.187 | -0.309 | 0.552 |
| C1_to_C2 | oxidation | n_heavy | 6 | -0.446 | 0.375 | -0.169 | 0.749 |
| C1_to_C2 | oxidation | rotatable_bonds | 6 | -0.695 | 0.125 | -0.621 | 0.188 |
| C1_to_C2 | oxidation | tpsa | 6 | -0.378 | 0.461 | -0.406 | 0.425 |

**探索性**：n=6，`donor_count` 与 |ΔΔG_coord| 呈强负相关（r=-0.962, p=0.002），
提示配位数越多的给体条件响应越大；但样本太小，只作假设生成，不作结论。

## 4. 机制案例（全部有 QC 支持）

- **C1_oxidation_molecule_centered**（interpretable_conditional_response，n=6）：max |DeltaDeltaG_coord| = 5.1343 eV, mean = 4.6082 eV。
- **C1_reduction_li_centered_failure**（observable_identity_failure，n=9）：9 / 10 reduced states put the electron on Li。
- **C1_reduction_molecule_centered_singleton**（interpretable_conditional_response，n=1）：DeltaDeltaG_coord = -4.9273 eV。

## 5. C1 -> C2 一致性

第一溶剂壳 `[Li(M)2]+` 的 20 个状态里标签变化 0 个：C1 的关键机制判断在 C2 下保持不变。

## 6. 一致性自检

- `coord_shift_reproduces_pairwise_shift`: PASS -- delta_i - delta_j 与 pairwise_table.delta_shift_ev 的最大绝对误差 1.332e-15 eV（210 个 pair 行）
- `ranking_metrics_match_week28`: PASS -- C0/C1/C2 重算的 overlap/Jaccard/regret/tau_b/rho 对齐 Week 28 decision_table，最大绝对差 overlap=0.000e+00, jaccard=0.000e+00, selection_regret_ev=0.000e+00, kendall_tau_b=0.000e+00, spearman_rho=0.000e+00
- `identity_gate_holds`: PASS -- R13 闸门后 C1 主集合：还原轴 ['SN']（n=1），氧化轴 n=6
- `li_centered_dominates_c1_reduction`: PASS -- C1 还原态 9/10 的外加电子落在 Li 上（molecule-centered 仅 1 个）
- `mechanism_cases_present_and_qc_flags_surfaced`: PASS -- 3 个机制案例；2 个主集合状态带 QC 警告且已如实上报（未静默丢弃）：SL:geometry_failed;SL:geometry_failed
- `descriptor_regression_is_primary_only`: PASS -- 所有描述符关联的成员都落在 R13 主集合内 = True（10 个关联行；绝不把混合身份样本并进同一回归）
- `c1_to_c2_preserves_identity_labels`: PASS -- C1 -> C2 的 20 个状态里标签变化 0 个：第一溶剂壳不改变关键机制判断
- `zero_new_electronic_structure`: PASS -- 唯一输入是 outputs/week28/*.csv；未运行任何电子结构作业

## 7. 限制

- 零新增计算；C1 声明 core 18、实际有值 10（PC/EMC 没有 [LiM]+ 对象），这是最该先补的计算缺口。
- 描述符关联 n=6，仅探索性；绝不把 Li_centered 样本并入分子还原的连续回归。
- 主集合还原轴只剩 1 个分子，任何「还原排序」都不能由本阶段支撑。

## 8. 复现命令

```powershell
.venv\Scripts\python.exe scripts\build_week30_wp3_coordination_mechanism.py
.venv\Scripts\python.exe scripts\build_week30_wp3_coordination_mechanism.py --check
.venv\Scripts\python.exe -m pytest tests/test_week30_wp3_coordination_mechanism.py -q
```
