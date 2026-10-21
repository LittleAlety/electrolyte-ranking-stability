# 14 个未 accepted 系综态：决策支持（v1.4.2 缺口分诊）

> 生成器：`scripts/wp_production/build_gap_decision_support.py`（`--check` 完全只读）。
> 只读冻结证据：48 态生产标签、成员处置、结构账本（round1_extra **与 round2_audit_extra**）、
> 3→6 审计与差异报告、自由构象冻结池、Li motif 筛选池、round-2 实测盆地。
> **零新增计算、零阈值改动、零验收语义改动。**
> 用户 2026-10-20 裁决：只有「会改变关键排序」的态才值得预注册独立新起点；不为 48/48 数字续算。

## 排序敏感的量化口径（先冻结）

- 两条轴：氧化 = G(M_plus)−G(M)，Li 条件 = G(LiM_2plus)−G(LiM_plus)，单位 eV
  （`ΔEh × 27.211386245988`，与 `sampling_3to6_diff` 同口径）；
- **Top-3 = 轴值最低的 3 个分子**（最易氧化方向，与 3→6 报告的 top-k 一致）；
- worst-case 额外拉低取三条证据通道的**最大值**：
  (a) `RT ln N_max − RT ln n_unique`（固定 G_min 的数学上界；N_max = n_unique + 未用盆地 + 在途救援）；
  (b) 3→6 审计已实测完成的 ceiling 落差（真实新极小可以**低于** G_min，测量值优先于数学界）；
  (c) 其余为 0，绝不猜测；
- **排序敏感 = Top-3 集合变化，或任一轴上任何逐对次序交换**；
- 漂移/预算尽的盆地已烧毁（重跑不能恢复身份），不参与 N_max。

## 基线（当前 48 标签）

**oxidation 轴**（eV，低 = 更易氧化/更易再电离）：

| # | 分子 | 轴值 | 与前一名间距 (kcal) |
| --- | --- | --- | --- |
| 1 | C15 (DMSO) | 6.351 | — |
| 2 | C08 (DME) | 6.601 | 5.761 |
| 3 | C09 (DOL) | 7.008 | 9.389 |
| 4 | C03 (DEC) | 7.292 | 6.560 |
| 5 | C13 (C13) | 7.703 | 9.474 |
| 6 | C14 (SL) | 7.751 | 1.097 |
| 7 | C17 (TMP) | 7.945 | 4.481 |
| 8 | C02 (EMC) | 8.108 | 3.750 |
| 9 | C05 (C05) | 8.155 | 1.086 |
| 10 | C04 (EC) | 8.281 | 2.906 |
| 11 | C01 (DMC) | 8.305 | 0.557 |
| 12 | C16 (AN) | 9.060 | 17.422 |

Top-3：C15 (DMSO), C08 (DME), C09 (DOL)

**Li_conditioned 轴**（eV，低 = 更易氧化/更易再电离）：

| # | 分子 | 轴值 | 与前一名间距 (kcal) |
| --- | --- | --- | --- |
| 1 | C15 (DMSO) | 7.163 | — |
| 2 | C09 (DOL) | 7.411 | 5.724 |
| 3 | C08 (DME) | 7.764 | 8.153 |
| 4 | C17 (TMP) | 8.206 | 10.173 |
| 5 | C14 (SL) | 8.251 | 1.043 |
| 6 | C13 (C13) | 8.370 | 2.741 |
| 7 | C03 (DEC) | 8.448 | 1.811 |
| 8 | C02 (EMC) | 8.503 | 1.261 |
| 9 | C05 (C05) | 8.553 | 1.163 |
| 10 | C04 (EC) | 8.752 | 4.580 |
| 11 | C01 (DMC) | 8.830 | 1.805 |
| 12 | C16 (AN) | 9.666 | 19.273 |

Top-3：C15 (DMSO), C09 (DOL), C08 (DME)

## 联合最坏情形（14 个缺口态同时取到各自 worst-case）

| 轴 | 基线 Top-3 | 联合最坏 Top-3 | 翻转 | 完整排序 |
| --- | --- | --- | --- | --- |
| oxidation | C15, C08, C09 | C15, C08, C09 | 否 | 不变 |
| Li_conditioned | C15, C09, C08 | C15, C09, C08 | 否 | 不变 |

**联合最坏下无任何逐对翻轴、无 Top-3 翻转、完整排序不变**——
即使全部 14 个缺口态的每一条剩余证据都取最坏值，12 分子在两条轴上的排序也不动。

## 逐态决策证据

### C01 DMC（LiM_2plus）

- **状态**：limited（rescue_budget_exhausted）；n_unique=1，n_registered 见 labels；在途救援 0 个
- **成员处置**：c06->rescue_budget_exhausted(strict_reopt_required)
- **已烧毁盆地**：1 个（drift/budget-exhausted——重跑不能恢复身份）
- **池**：审计判定 `not_in_audit_set`（池内上限 —）；**未用独立盆地 0 个**（池已全部尝试或烧毁）
- **worst-case 额外拉低**：0.000000 kcal（0.0 meV）＝ max(RT ln N 界 0.000000 kcal，实测 ceiling 无)
- **排序敏感判定**：**排序不敏感**——Top-3 翻转（氧化轴 否 / Li 条件轴 否），逐对翻轴：none；该态所在轴最多移动 0.000 kcal（0.000 eV）
无未用盆地——冻结池已全部尝试或烧毁，限制原因是终局证据，登记限制即可

### C01 DMC（M_plus）

- **状态**：limited（rescue_budget_exhausted）；n_unique=1，n_registered 见 labels；在途救援 0 个
- **成员处置**：28->rescue_budget_exhausted(strict_reopt_required)
- **已烧毁盆地**：1 个（drift/budget-exhausted——重跑不能恢复身份）
- **池**：审计判定 `not_in_audit_set`（池内上限 —）；**未用独立盆地 0 个**（池已全部尝试或烧毁）
- **worst-case 额外拉低**：0.000000 kcal（0.0 meV）＝ max(RT ln N 界 0.000000 kcal，实测 ceiling 无)
- **排序敏感判定**：**排序不敏感**——Top-3 翻转（氧化轴 否 / Li 条件轴 否），逐对翻轴：none；该态所在轴最多移动 0.000 kcal（0.000 eV）
无未用盆地——冻结池已全部尝试或烧毁，限制原因是终局证据，登记限制即可

### C02 EMC（M_plus）

- **状态**：limited（species_drift_unrecoverable）；n_unique=2，n_registered 见 labels；在途救援 0 个
- **成员处置**：21->computed(strict_reopt_not_needed); 4->species_drift_unrecoverable(candidate_bond_graph_changed)
- **已烧毁盆地**：1 个（drift/budget-exhausted——重跑不能恢复身份）
- **池**：审计判定 `sampling_limited`（池内上限 2）；**未用独立盆地 0 个**（池已全部尝试或烧毁）
- **worst-case 额外拉低**：0.000000 kcal（0.0 meV）＝ max(RT ln N 界 0.000000 kcal，实测 ceiling 无)
- **排序敏感判定**：**排序不敏感**——Top-3 翻转（氧化轴 否 / Li 条件轴 否），逐对翻轴：none；该态所在轴最多移动 0.000 kcal（0.000 eV）
无未用盆地——冻结池已全部尝试或烧毁，限制原因是终局证据，登记限制即可

### C03 DEC（M）

- **状态**：limited（rescue_budget_exhausted）；n_unique=2，n_registered 见 labels；在途救援 0 个
- **成员处置**：13->computed(strict_reopt_not_needed); 3->rescue_budget_exhausted(strict_reopt_required)
- **已烧毁盆地**：1 个（drift/budget-exhausted——重跑不能恢复身份）
- **池**：审计判定 `sampling_limited`（池内上限 3）；**未用独立盆地 1 个**：r2_c23 (+1.350 kcal in pool)
- **worst-case 额外拉低**：0.240232 kcal（10.4 meV）＝ max(RT ln N 界 0.240232 kcal，实测 ceiling 无)
- **排序敏感判定**：**排序不敏感**——Top-3 翻转（氧化轴 否 / Li 条件轴 否），逐对翻轴：none；该态所在轴最多移动 -0.240 kcal（-0.010 eV）
- **建议**：有 {'mol_id': 'C03', 'name': 'DEC', 'state': 'M', 'acceptance_status': 'limited', 'limitation_reason': 'rescue_budget_exhausted', 'n_unique': '2', 'n_rescue_in_flight': '0', 'disposition_summary': '13->computed(strict_reopt_not_needed); 3->rescue_budget_exhausted(strict_reopt_required)', 'n_burned_basins': '1', 'audit_status': 'sampling_limited', 'audit_ceiling': '3', 'unused_basins': '23', 'n_unused': '1', 'unused_sources': 'r2_c23 (+1.350 kcal in pool)', 'n_max_members': '3', 'rt_extra_bound_kcal': '0.240232', 'measured_ceiling_drop_kcal': '', 'worst_extra_lowering_kcal': '0.240232', 'worst_extra_lowering_mev': '10.4', 'axis_moves_kcal': 'oxidation=-0.240', 'top3_oxidation_flip': 'false', 'top3_licond_flip': 'false', 'pair_order_flips': 'none', 'ranking_sensitive': 'false', 'recommendation': 'keep_limited_ranking_insensitive_unused_basin_on_record'} 个未用盆地但 bound 显示用尽也不改变排序——维持 limited，未用盆地登记在案不续算

### C04 EC（LiM_2plus）

- **状态**：limited（rescue_budget_exhausted）；n_unique=1，n_registered 见 labels；在途救援 0 个
- **成员处置**：c03->rescue_budget_exhausted(imaginary_modes)
- **已烧毁盆地**：1 个（drift/budget-exhausted——重跑不能恢复身份）
- **池**：审计判定 `not_in_audit_set`（池内上限 —）；**未用独立盆地 0 个**（池已全部尝试或烧毁）
- **worst-case 额外拉低**：0.000000 kcal（0.0 meV）＝ max(RT ln N 界 0.000000 kcal，实测 ceiling 无)
- **排序敏感判定**：**排序不敏感**——Top-3 翻转（氧化轴 否 / Li 条件轴 否），逐对翻轴：none；该态所在轴最多移动 0.000 kcal（0.000 eV）
无未用盆地——冻结池已全部尝试或烧毁，限制原因是终局证据，登记限制即可

### C08 DME（LiM_2plus）

- **状态**：provisional（rescue_in_flight）；n_unique=1，n_registered 见 labels；在途救援 1 个
- **成员处置**：c01->species_drift_unrecoverable(max_cycles_exhausted)
- **已烧毁盆地**：1 个（drift/budget-exhausted——重跑不能恢复身份）
- **池**：审计判定 `executable_partial`（池内上限 3）；**未用独立盆地 0 个**（池已全部尝试或烧毁）
- **worst-case 额外拉低**：0.410679 kcal（17.8 meV）＝ max(RT ln N 界 0.410679 kcal，实测 ceiling 无)
- **排序敏感判定**：**排序不敏感**——Top-3 翻转（氧化轴 否 / Li 条件轴 否），逐对翻轴：none；该态所在轴最多移动 0.411 kcal（0.018 eV）
在途救援尚未处置——先让登记的救援链落定，暂不新增任何起点

### C08 DME（M_plus）

- **状态**：limited（rescue_budget_exhausted）；n_unique=2，n_registered 见 labels；在途救援 0 个
- **成员处置**：14->rescue_budget_exhausted(strict_reopt_required); 23->computed(strict_reopt_not_needed)
- **已烧毁盆地**：1 个（drift/budget-exhausted——重跑不能恢复身份）
- **池**：审计判定 `executable_partial`（池内上限 4）；**未用独立盆地 1 个**：c07 (+1.053 kcal in pool)
- **worst-case 额外拉低**：0.240232 kcal（10.4 meV）＝ max(RT ln N 界 0.240232 kcal，实测 ceiling 无)
- **排序敏感判定**：**排序不敏感**——Top-3 翻转（氧化轴 否 / Li 条件轴 否），逐对翻轴：none；该态所在轴最多移动 0.240 kcal（0.010 eV）
- **建议**：有 {'mol_id': 'C08', 'name': 'DME', 'state': 'M_plus', 'acceptance_status': 'limited', 'limitation_reason': 'rescue_budget_exhausted', 'n_unique': '2', 'n_rescue_in_flight': '0', 'disposition_summary': '14->rescue_budget_exhausted(strict_reopt_required); 23->computed(strict_reopt_not_needed)', 'n_burned_basins': '1', 'audit_status': 'executable_partial', 'audit_ceiling': '4', 'unused_basins': '7', 'n_unused': '1', 'unused_sources': 'c07 (+1.053 kcal in pool)', 'n_max_members': '3', 'rt_extra_bound_kcal': '0.240232', 'measured_ceiling_drop_kcal': '', 'worst_extra_lowering_kcal': '0.240232', 'worst_extra_lowering_mev': '10.4', 'axis_moves_kcal': 'oxidation=0.240', 'top3_oxidation_flip': 'false', 'top3_licond_flip': 'false', 'pair_order_flips': 'none', 'ranking_sensitive': 'false', 'recommendation': 'keep_limited_ranking_insensitive_unused_basin_on_record'} 个未用盆地但 bound 显示用尽也不改变排序——维持 limited，未用盆地登记在案不续算

### C09 DOL（LiM_2plus）

- **状态**：limited（rescue_budget_exhausted）；n_unique=1，n_registered 见 labels；在途救援 0 个
- **成员处置**：c01->rescue_budget_exhausted(imaginary_modes); c05->computed(strict_reopt_not_needed)
- **已烧毁盆地**：1 个（drift/budget-exhausted——重跑不能恢复身份）
- **池**：审计判定 `not_in_audit_set`（池内上限 —）；**未用独立盆地 0 个**（池已全部尝试或烧毁）
- **worst-case 额外拉低**：0.000000 kcal（0.0 meV）＝ max(RT ln N 界 0.000000 kcal，实测 ceiling 无)
- **排序敏感判定**：**排序不敏感**——Top-3 翻转（氧化轴 否 / Li 条件轴 否），逐对翻轴：none；该态所在轴最多移动 0.000 kcal（0.000 eV）
无未用盆地——冻结池已全部尝试或烧毁，限制原因是终局证据，登记限制即可

### C14 SL（LiM_2plus）

- **状态**：provisional（rescue_in_flight）；n_unique=2，n_registered 见 labels；在途救援 1 个
- **成员处置**：c02->computed(strict_reopt_not_needed); c03->species_drift_unrecoverable(max_cycles_exhausted)
- **已烧毁盆地**：1 个（drift/budget-exhausted——重跑不能恢复身份）
- **池**：审计判定 `not_in_audit_set`（池内上限 —）；**未用独立盆地 0 个**（池已全部尝试或烧毁）
- **worst-case 额外拉低**：0.240232 kcal（10.4 meV）＝ max(RT ln N 界 0.240232 kcal，实测 ceiling 无)
- **排序敏感判定**：**排序不敏感**——Top-3 翻转（氧化轴 否 / Li 条件轴 否），逐对翻轴：none；该态所在轴最多移动 0.240 kcal（0.010 eV）
在途救援尚未处置——先让登记的救援链落定，暂不新增任何起点

### C15 DMSO（LiM_plus）

- **状态**：limited（rescue_budget_exhausted）；n_unique=1，n_registered 见 labels；在途救援 0 个
- **成员处置**：c01->rescue_budget_exhausted(verytight_convergence)
- **已烧毁盆地**：1 个（drift/budget-exhausted——重跑不能恢复身份）
- **池**：审计判定 `not_in_audit_set`（池内上限 —）；**未用独立盆地 0 个**（池已全部尝试或烧毁）
- **worst-case 额外拉低**：0.000000 kcal（0.0 meV）＝ max(RT ln N 界 0.000000 kcal，实测 ceiling 无)
- **排序敏感判定**：**排序不敏感**——Top-3 翻转（氧化轴 否 / Li 条件轴 否），逐对翻轴：none；该态所在轴最多移动 0.000 kcal（0.000 eV）
无未用盆地——冻结池已全部尝试或烧毁，限制原因是终局证据，登记限制即可

### C16 AN（M_plus）

- **状态**：limited（rescue_budget_exhausted）；n_unique=1，n_registered 见 labels；在途救援 0 个
- **成员处置**：10->rescue_budget_exhausted(strict_reopt_required)
- **已烧毁盆地**：1 个（drift/budget-exhausted——重跑不能恢复身份）
- **池**：审计判定 `not_in_audit_set`（池内上限 —）；**未用独立盆地 0 个**（池已全部尝试或烧毁）
- **worst-case 额外拉低**：0.000000 kcal（0.0 meV）＝ max(RT ln N 界 0.000000 kcal，实测 ceiling 无)
- **排序敏感判定**：**排序不敏感**——Top-3 翻转（氧化轴 否 / Li 条件轴 否），逐对翻轴：none；该态所在轴最多移动 0.000 kcal（0.000 eV）
无未用盆地——冻结池已全部尝试或烧毁，限制原因是终局证据，登记限制即可

### C17 TMP（LiM_2plus）

- **状态**：limited（rescue_budget_exhausted）；n_unique=2，n_registered 见 labels；在途救援 0 个
- **成员处置**：c08->rescue_budget_exhausted(strict_reopt_required); c13->computed(strict_reopt_not_needed)
- **已烧毁盆地**：1 个（drift/budget-exhausted——重跑不能恢复身份）
- **池**：审计判定 `executable_partial`（池内上限 3）；**未用独立盆地 0 个**（池已全部尝试或烧毁）
- **worst-case 额外拉低**：0.436766 kcal（18.9 meV）＝ max(RT ln N 界 0.000000 kcal，实测 ceiling 0.436766 kcal)
- **排序敏感判定**：**排序不敏感**——Top-3 翻转（氧化轴 否 / Li 条件轴 否），逐对翻轴：none；该态所在轴最多移动 0.437 kcal（0.019 eV）
无未用盆地——冻结池已全部尝试或烧毁，限制原因是终局证据，登记限制即可

### C17 TMP（LiM_plus）

- **状态**：provisional（rescue_in_flight）；n_unique=1，n_registered 见 labels；在途救援 1 个
- **成员处置**：c04->species_drift_unrecoverable(max_cycles_exhausted)
- **已烧毁盆地**：1 个（drift/budget-exhausted——重跑不能恢复身份）
- **池**：审计判定 `executable_partial`（池内上限 5）；**未用独立盆地 0 个**（池已全部尝试或烧毁）
- **worst-case 额外拉低**：0.410679 kcal（17.8 meV）＝ max(RT ln N 界 0.410679 kcal，实测 ceiling 无)
- **排序敏感判定**：**排序不敏感**——Top-3 翻转（氧化轴 否 / Li 条件轴 否），逐对翻轴：none；该态所在轴最多移动 -0.411 kcal（-0.018 eV）
在途救援尚未处置——先让登记的救援链落定，暂不新增任何起点

### C17 TMP（M_plus）

- **状态**：limited（rescue_budget_exhausted）；n_unique=2，n_registered 见 labels；在途救援 0 个
- **成员处置**：27->computed(strict_reopt_not_needed); 33->rescue_budget_exhausted(strict_reopt_required)
- **已烧毁盆地**：1 个（drift/budget-exhausted——重跑不能恢复身份）
- **池**：审计判定 `sampling_limited`（池内上限 3）；**未用独立盆地 1 个**：c10 (+4.235 kcal in pool)
- **worst-case 额外拉低**：0.240232 kcal（10.4 meV）＝ max(RT ln N 界 0.240232 kcal，实测 ceiling 无)
- **排序敏感判定**：**排序不敏感**——Top-3 翻转（氧化轴 否 / Li 条件轴 否），逐对翻轴：none；该态所在轴最多移动 0.240 kcal（0.010 eV）
- **建议**：有 {'mol_id': 'C17', 'name': 'TMP', 'state': 'M_plus', 'acceptance_status': 'limited', 'limitation_reason': 'rescue_budget_exhausted', 'n_unique': '2', 'n_rescue_in_flight': '0', 'disposition_summary': '27->computed(strict_reopt_not_needed); 33->rescue_budget_exhausted(strict_reopt_required)', 'n_burned_basins': '1', 'audit_status': 'sampling_limited', 'audit_ceiling': '3', 'unused_basins': '10', 'n_unused': '1', 'unused_sources': 'c10 (+4.235 kcal in pool)', 'n_max_members': '3', 'rt_extra_bound_kcal': '0.240232', 'measured_ceiling_drop_kcal': '', 'worst_extra_lowering_kcal': '0.240232', 'worst_extra_lowering_mev': '10.4', 'axis_moves_kcal': 'oxidation=0.240', 'top3_oxidation_flip': 'false', 'top3_licond_flip': 'false', 'pair_order_flips': 'none', 'ranking_sensitive': 'false', 'recommendation': 'keep_limited_ranking_insensitive_unused_basin_on_record'} 个未用盆地但 bound 显示用尽也不改变排序——维持 limited，未用盆地登记在案不续算

## 建议口径（按用户裁决格式）

- `candidate_for_preregistered_new_start`：排序敏感且冻结池确有未用盆地——可预注册独立新起点（须先登记来源/次数/停止条件）
- `sensitive_but_no_unused_basin_register_limitation`：排序敏感但池已用尽——只能登记限制，不得开新起点搜索
- `let_registered_rescue_settle_no_new_start`：在途救援尚未处置——先让登记的救援链落定，暂不新增任何起点
- `keep_limited_ranking_insensitive_unused_basin_on_record`：有 … 个未用盆地但 bound 显示用尽也不改变排序——维持 limited，未用盆地登记在案不续算
- `keep_provisional_ranking_insensitive_unused_basin_on_record`：有 … 个未用盆地但 bound 显示用尽也不改变排序——维持 provisional，未用盆地登记在案不续算
- `no_unused_basin_register_limitation`：无未用盆地——冻结池已全部尝试或烧毁，限制原因是终局证据，登记限制即可

## 判读规则

1. **n_unique=1 且无未用盆地的态，worst-case=0 是弱证据**（对「池外还有漏采样独立盆地」
   无约束力），只说明**冻结池内**已无剩余拉低空间，如实登记不冒充收敛证明。
2. 3 个未用盆地（DEC M r2_c23 / DME M_plus c07 / TMP M_plus c10）都是 round-1 上限
   （E2：3 结构含 primary → 每腿 ≤2 extras）排掉的 rank-3 盆地，不是采样缺陷；
   bound 显示即使全部用尽也不改变任何排序。
3. 3 个 provisional 态的在途救援按登记契约自然落定后重新聚合，
   本报告不替代那条处置链。

