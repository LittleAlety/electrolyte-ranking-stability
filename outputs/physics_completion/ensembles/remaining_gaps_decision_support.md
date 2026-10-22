# 未 accepted 系综态：决策支持（v1.4.2 缺口分诊；上限 14，随恢复递减）

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
| 1 | C15 (C15) | 6.351 | — |
| 2 | C08 (C08) | 6.597 | 5.689 |
| 3 | C09 (DOL) | 7.008 | 9.461 |
| 4 | C03 (C03) | 7.316 | 7.114 |
| 5 | C13 (C13) | 7.703 | 8.920 |
| 6 | C14 (C14) | 7.751 | 1.097 |
| 7 | C17 (C17) | 7.945 | 4.481 |
| 8 | C02 (C02) | 8.108 | 3.750 |
| 9 | C05 (C05) | 8.155 | 1.086 |
| 10 | C04 (EC) | 8.281 | 2.906 |
| 11 | C01 (DMC) | 8.305 | 0.557 |
| 12 | C16 (AN) | 9.060 | 17.422 |

Top-3：C15 (C15), C08 (C08), C09 (DOL)

**Li_conditioned 轴**（eV，低 = 更易氧化/更易再电离）：

| # | 分子 | 轴值 | 与前一名间距 (kcal) |
| --- | --- | --- | --- |
| 1 | C15 (C15) | 7.166 | — |
| 2 | C09 (DOL) | 7.411 | 5.639 |
| 3 | C08 (C08) | 7.621 | 4.843 |
| 4 | C14 (C14) | 8.251 | 14.527 |
| 5 | C13 (C13) | 8.370 | 2.741 |
| 6 | C03 (C03) | 8.448 | 1.811 |
| 7 | C02 (C02) | 8.503 | 1.261 |
| 8 | C17 (C17) | 8.536 | 0.770 |
| 9 | C05 (C05) | 8.553 | 0.393 |
| 10 | C04 (EC) | 8.752 | 4.580 |
| 11 | C01 (DMC) | 8.830 | 1.805 |
| 12 | C16 (AN) | 9.666 | 19.273 |

Top-3：C15 (C15), C09 (DOL), C08 (C08)

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
- **成员处置**：c06->rescue_budget_exhausted(strict_reopt_required); tors_6_0_1_2->unresolved_qc_failure(max_cycles_exhausted); tors_7_0_1_2->unresolved_qc_failure(strict_reopt_required); tors_8_0_1_2->unresolved_qc_failure(max_cycles_exhausted)
- **已烧毁盆地**：1 个（drift/budget-exhausted——重跑不能恢复身份）
- **池**：审计判定 `not_in_audit_set`（池内上限 —）；**未用独立盆地 0 个**（池已全部尝试或烧毁）
- **worst-case 额外拉低**：0.000000 kcal（0.0 meV）＝ max(RT ln N 界 0.000000 kcal，实测 ceiling 无)
- **排序敏感判定**：**排序不敏感**——Top-3 翻转（氧化轴 否 / Li 条件轴 否），逐对翻轴：none；该态所在轴最多移动 0.000 kcal（0.000 eV）
无未用盆地——冻结池已全部尝试或烧毁，限制原因是终局证据，登记限制即可

### C01 DMC（M_plus）

- **状态**：limited（rescue_budget_exhausted）；n_unique=1，n_registered 见 labels；在途救援 0 个
- **成员处置**：28->rescue_budget_exhausted(strict_reopt_required); tors_6_0_1_2->unresolved_qc_failure(verytight_convergence); tors_7_0_1_2->unresolved_qc_failure(verytight_convergence); tors_8_0_1_2->unresolved_qc_failure(verytight_convergence)
- **已烧毁盆地**：1 个（drift/budget-exhausted——重跑不能恢复身份）
- **池**：审计判定 `not_in_audit_set`（池内上限 —）；**未用独立盆地 0 个**（池已全部尝试或烧毁）
- **worst-case 额外拉低**：0.000000 kcal（0.0 meV）＝ max(RT ln N 界 0.000000 kcal，实测 ceiling 无)
- **排序敏感判定**：**排序不敏感**——Top-3 翻转（氧化轴 否 / Li 条件轴 否），逐对翻轴：none；该态所在轴最多移动 0.000 kcal（0.000 eV）
无未用盆地——冻结池已全部尝试或烧毁，限制原因是终局证据，登记限制即可

### C04 EC（LiM_2plus）

- **状态**：limited（rescue_budget_exhausted）；n_unique=1，n_registered 见 labels；在途救援 0 个
- **成员处置**：c03->rescue_budget_exhausted(imaginary_modes); tors_2_3_4_10->unresolved_qc_failure(); tors_5_3_4_10->unresolved_qc_failure()
- **已烧毁盆地**：1 个（drift/budget-exhausted——重跑不能恢复身份）
- **池**：审计判定 `not_in_audit_set`（池内上限 —）；**未用独立盆地 0 个**（池已全部尝试或烧毁）
- **worst-case 额外拉低**：0.000000 kcal（0.0 meV）＝ max(RT ln N 界 0.000000 kcal，实测 ceiling 无)
- **排序敏感判定**：**排序不敏感**——Top-3 翻转（氧化轴 否 / Li 条件轴 否），逐对翻轴：none；该态所在轴最多移动 0.000 kcal（0.000 eV）
无未用盆地——冻结池已全部尝试或烧毁，限制原因是终局证据，登记限制即可

### C09 DOL（LiM_2plus）

- **状态**：limited（rescue_budget_exhausted）；n_unique=1，n_registered 见 labels；在途救援 0 个
- **成员处置**：c01->rescue_budget_exhausted(imaginary_modes); c05->computed(strict_reopt_not_needed)
- **已烧毁盆地**：1 个（drift/budget-exhausted——重跑不能恢复身份）
- **池**：审计判定 `not_in_audit_set`（池内上限 —）；**未用独立盆地 0 个**（池已全部尝试或烧毁）
- **worst-case 额外拉低**：0.000000 kcal（0.0 meV）＝ max(RT ln N 界 0.000000 kcal，实测 ceiling 无)
- **排序敏感判定**：**排序不敏感**——Top-3 翻转（氧化轴 否 / Li 条件轴 否），逐对翻轴：none；该态所在轴最多移动 0.000 kcal（0.000 eV）
无未用盆地——冻结池已全部尝试或烧毁，限制原因是终局证据，登记限制即可

### C16 AN（M_plus）

- **状态**：limited（rescue_budget_exhausted）；n_unique=1，n_registered 见 labels；在途救援 0 个
- **成员处置**：10->rescue_budget_exhausted(strict_reopt_required); tors_3_0_1_2->computed(strict_reopt_not_needed); tors_4_0_1_2->computed(strict_reopt_not_needed); tors_5_0_1_2->computed(strict_reopt_not_needed)
- **已烧毁盆地**：1 个（drift/budget-exhausted——重跑不能恢复身份）
- **池**：审计判定 `not_in_audit_set`（池内上限 —）；**未用独立盆地 0 个**（池已全部尝试或烧毁）
- **worst-case 额外拉低**：0.000000 kcal（0.0 meV）＝ max(RT ln N 界 0.000000 kcal，实测 ceiling 无)
- **排序敏感判定**：**排序不敏感**——Top-3 翻转（氧化轴 否 / Li 条件轴 否），逐对翻轴：none；该态所在轴最多移动 0.000 kcal（0.000 eV）
无未用盆地——冻结池已全部尝试或烧毁，限制原因是终局证据，登记限制即可

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

