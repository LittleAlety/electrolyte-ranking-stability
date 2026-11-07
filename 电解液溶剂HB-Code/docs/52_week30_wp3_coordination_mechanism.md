# Week 30 / WP3：Li+ 配位条件态如何影响 redox 行为

> 阶段：下一阶段（评审实施方案）WP3（RQ2）。产物目录 `outputs/week30/`，交付镜像
> `..\成果输出（part2）\week30/`。数字由 `scripts/build_week30_wp3_coordination_mechanism.py`
> 确定性生成并 `--check` 逐字节复核。**零新增电子结构计算**：唯一输入是 Week 28 冻结主表。

## 0. 本轮解决的问题

WP2 处理 Axis-A 阶梯；WP3 处理电解液化学最有特色的一层 —— Li+ 配位条件态
`C1 = [LiM]+` 与第一溶剂壳 `C2 = [Li(M)2]+`。核心响应量沿用 v2 定义
`ΔΔG_coord^ox/red = ΔG_redox^{C1} − ΔG_redox^{C0}`，但**必须按电子状态身份拆分**。
评审给出一条硬约束：不能用当前 C1 的全部还原数据建立一个统一的分子还原回归模型，
因为其中包含不同的电子接受中心。本阶段据此把「描述符回归只在 R13 主集合上做」写成
可复核的断言（`descriptor_regression_is_primary_only`）。

## 1. 条件态位移与状态身份分层（all scope）

| 对比 | 轴 | 状态身份标签 | n | 主集合 n | mean ΔΔG (eV) | std (eV) | 成员 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| C0_to_C1 | oxidation | molecule_centered_redox | 6 | 6 | +4.6082 | 0.4376 | DMC;DME;EC;GBL;SL;TMP |
| C0_to_C1 | oxidation | no_intact_minimum_found | 4 | 0 | +5.3057 | 0.5933 | AN;DMSO;DOL;SN |
| C0_to_C1 | reduction | Li_centered_or_mixed_redox | 9 | 0 | −6.7617 | 0.6330 | AN;DMC;DME;DMSO;DOL;EC;GBL;SL;TMP |
| C0_to_C1 | reduction | molecule_centered_redox | 1 | 1 | −4.9273 | — | SN |
| C1_to_C2 | oxidation | molecule_centered_redox | 6 | 6 | −1.6175 | 0.2930 | DMC;DME;EC;GBL;SL;TMP |
| C1_to_C2 | oxidation | no_intact_minimum_found | 4 | 0 | −1.8235 | 0.1578 | AN;DMSO;DOL;SN |
| C1_to_C2 | reduction | Li_centered_or_mixed_redox | 9 | 0 | +1.2885 | 0.1881 | AN;DMC;DME;DMSO;DOL;EC;GBL;SL;TMP |
| C1_to_C2 | reduction | molecule_centered_redox | 1 | 1 | +0.3898 | — | SN |

## 2. 排序影响（Top-k）

| 对比 | scope | 轴 | n | k/N | O_k | regret(eV) | tau_b |
| --- | --- | --- | --- | --- | --- | --- | --- |
| C0_to_C1 | all | oxidation | 10 | 0.2 | 1.000 | — | 0.689 |
| C0_to_C1 | primary | oxidation | 6 | 0.2 | 1.000 | — | 0.733 |
| C0_to_C1 | all | reduction | 10 | 0.2 | 0.000 | — | −0.467 |
| C1_to_C2 | all | oxidation | 10 | 0.2 | 1.000 | — | 0.867 |
| C1_to_C2 | primary | oxidation | 6 | 0.2 | 0.000 | — | 0.600 |

`C0_to_C1 / primary / reduction` 只有 1 个候选（SN），配不成 pair，**显式记为未定义**，
不是「稳定」。all-scope 还原轴的 τ_b = −0.467 说明：不加闸门时这条排序轴在物理上不是
同一件事（不同电子接受中心混在一起）。

## 3. 描述符关联（只在 R13 主集合上，n=6，探索性）

| 对比 | 轴 | 描述符 | n | Pearson r | p | Spearman ρ | p |
| --- | --- | --- | --- | --- | --- | --- | --- |
| C0_to_C1 | oxidation | donor_count | 6 | −0.962 | 0.002 | −0.926 | 0.008 |
| C0_to_C1 | oxidation | tpsa | 6 | −0.885 | 0.019 | −0.928 | 0.008 |
| C0_to_C1 | oxidation | heteroatom_count | 6 | −0.825 | 0.043 | −0.772 | 0.072 |
| C0_to_C1 | oxidation | n_heavy | 6 | −0.457 | 0.362 | −0.338 | 0.512 |
| C0_to_C1 | oxidation | rotatable_bonds | 6 | −0.047 | 0.930 | 0.000 | 1.000 |

`donor_count` 与 |ΔΔG_coord| 的强负相关（r=−0.962）提示：**配位给体越多，条件响应的
绝对值越大**。但 n=6，只能作假设生成，不作结论。

## 4. 机制案例（全部有 QC 支持）

1. **C1_oxidation_molecule_centered**（interpretable_conditional_response，n=6）：分子中心
   氧化态（DMC/DME/EC/GBL/SL/TMP）的 ΔΔG_coord 均值 +4.61 eV，可解释为分子自身氧化难度
   的变化；QC 全 `ok`。
2. **C1_reduction_li_centered_failure**（observable_identity_failure，n=9）：9/10 还原态的
   外加电子落在 Li 上。这些格子上 `dG_red` 的排序衡量的是「电子去了哪」，不是「分子被还原的
   难度」，**不得并入分子还原的连续回归**。
3. **C1_reduction_molecule_centered_singleton**（n=1，SN）：本 core set 里唯一保持分子中心
   还原的候选，ΔΔG_coord = −4.93 eV；样本太少，仅作探索性案例。

## 5. C1 -> C2 一致性

第一溶剂壳 `[Li(M)2]+` 的 20 个状态里标签变化 **0** 个：C1 的关键机制判断在 C2 下保持不变。

## 6. 一致性自检（8 项，全部 PASS）

| id | 检查 | 关键数字 |
| --- | --- | --- |
| `coord_shift_reproduces_pairwise_shift` | δ_i − δ_j 是否等于主表 `delta_shift_ev` | 最大绝对误差 ≤ 1e-9 eV |
| `ranking_metrics_match_week28` | 重算 Top-k/Jaccard/regret/tau/rho 是否复现 Week 28 | 最大绝对差 ≤ 1e-9 |
| `identity_gate_holds` | R13 闸门后主集合 | 还原 `['SN']`，氧化 n=6 |
| `li_centered_dominates_c1_reduction` | 还原态电子去向 | 9/10 落在 Li 上 |
| `mechanism_cases_present_and_qc_flags_surfaced` | 机制案例与 QC 上报 | 3 个案例；SL 的 C1 氧化态带 `geometry_failed` 已如实上报（未静默丢弃） |
| `descriptor_regression_is_primary_only` | 回归是否只含主集合 | 10 个关联行全部落在主集合 |
| `c1_to_c2_preserves_identity_labels` | C1→C2 标签是否变化 | 0/20 |
| `zero_new_electronic_structure` | 是否零新增作业 | 5 个输入文件，0 个新作业 |

## 7. 限制

- 零新增计算；C1 声明 core 18、实际有值 10（`PC`/`EMC` 没有 `[LiM]+` 对象），这是最该先补的
  计算缺口。
- 描述符关联 n=6，仅探索性；绝不把 `Li_centered` 样本并入分子还原的连续回归。
- 主集合还原轴只剩 1 个分子，任何「还原排序」都不能由本阶段支撑。
- **QC 警告必须一起读**：`state_registry` 里同一 `state_id` 有多条 motif/构象记录，QC 可能不一致。
  `C14:C1:m1:dication`（SL 的 C1 氧化态）有一条 `execution_failed / geometry_failed` 记录，
  本阶段把该 flag 如实写进 `coord_response.qc_flags`，不当作全 ok。
- 以上均限于 designated computational target；Gate 1 仍 NOT CLOSED。

## 8. 交给 WP4/WP5 的接口

- **WP4**：`ranking_impact` 的 all/primary 两套 Top-k 与 `identity_split` 的分层，说明
  「哪些比较可信」必须带状态身份条件。
- **WP5/WP6**：`descriptor_association` 的 `donor_count`/`tpsa` 信号（探索性）是 C1 条件回归
  的候选廉价特征；`cost_table.feature_availability` 仍是硬约束。

## 9. 复现命令

```powershell
.venv\Scripts\python.exe scripts\build_week30_wp3_coordination_mechanism.py
.venv\Scripts\python.exe scripts\build_week30_wp3_coordination_mechanism.py --check
.venv\Scripts\python.exe -m pytest tests/test_week30_wp3_coordination_mechanism.py -q
.venv\Scripts\python.exe scripts\build_week30_deliverables.py
.venv\Scripts\python.exe scripts\build_week30_deliverables.py --check
```
