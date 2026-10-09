# 方案 6.1 / 执行第 3 步：四分子 Li 配位 motif 采样预注册

> 由 `scripts/wp_production/build_li_motif_sampling_plan.py` 生成；**零新增电子结构计算**。
> 规则在任何 motif 筛选跑出结果之前登记，不随后续结果修改。

## 为什么必须先冻结这条规则

方案 6.1 要求带电态补独立种子、且 motif 切换时重新检查电子身份与连接关系。已登记的 round-0 pilot 单点直接给出了证据：

| 分子 | LiM_plus 身份 | LiM_2plus 身份 |
| --- | --- | --- |
| DMC | intact_monodentate_carbonyl | intact_monodentate_carbonyl |
| EMC | intact_monodentate_carbonyl | intact_monodentate_carbonyl |
| GBL | intact_monodentate_carbonyl | intact_monodentate_carbonyl |
| SL | intact_bidentate_sulfone | intact_monodentate_sulfone |

即：**同一分子的两个 Li 态 motif 并不总是同一个**（上表差异即为证），而生产 Li 腿目前各自只从**一个冻结几何**起步（`n_conformers = 1`，`production_start_kind = single_frozen_motif`）。因此本层登记 motif 系综的选取规则，不宣称 motif 采样已完成。

## 冻结的选取规则

* object = the four-molecule subcohort (DMC / EMC / GBL / SL) x the two Li states LiM_plus / LiM_2plus
* each leg is constructed from its own charge and multiplicity; the two Li states are never chained
* candidates = monodentate placements on the round-0 donor class plus bidentate pairs whose donor-donor distance allows a Li bridge, layered with the state's own conformer seeds
* screen level = gas-phase GFN2-xTB (a screen, never a production free energy)
* deduplicate by coordination mode and heavy-atom RMSD / torsion; keep the lowest 3 independent motifs
* extend 3 -> 6 only if the key-pair Li rung is sensitive to the motif choice; the escalation is registered in advance, never decided from the outcome
* stop rule = after two screen rounds without resolution report sampling_limited / unresolved
* only one selected representative motif enters the DFT single-conformer production leg; the other independent motifs stay registered for the 3 -> 6 expansion

## 作业计划（8 条腿，逐条登记）

| 记录 | 分子 | 态 | q/m | round-0 身份 | 给体接触 | Li–O (Å) | round-0 实测 core-hour | round-1 起点 | 保留 | 状态 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| C01|LiM_plus | DMC | LiM_plus | 1/1 | intact_monodentate_carbonyl | 1 | 1.654 | 0.077889 | 16 | 3 | not_computed |
| C01|LiM_2plus | DMC | LiM_2plus | 2/2 | intact_monodentate_carbonyl | 1 | 1.805 | 0.095667 | 16 | 3 | not_computed |
| C02|LiM_plus | EMC | LiM_plus | 1/1 | intact_monodentate_carbonyl | 1 | 1.659 | 0.132333 | 16 | 3 | not_computed |
| C02|LiM_2plus | EMC | LiM_2plus | 2/2 | intact_monodentate_carbonyl | 1 | 1.782 | 0.215778 | 16 | 3 | not_computed |
| C13|LiM_plus | GBL | LiM_plus | 1/1 | intact_monodentate_carbonyl | 1 | 1.667 | 0.087000 | 16 | 3 | not_computed |
| C13|LiM_2plus | GBL | LiM_2plus | 2/2 | intact_monodentate_carbonyl | 1 | 1.815 | 0.116778 | 16 | 3 | not_computed |
| C14|LiM_plus | SL | LiM_plus | 1/1 | intact_bidentate_sulfone | 2 | 1.885 | 0.099111 | 16 | 3 | not_computed |
| C14|LiM_2plus | SL | LiM_2plus | 2/2 | intact_monodentate_sulfone | 1 | 1.721 | 0.097889 | 16 | 3 | not_computed |

## 验收（10/10 通过）

| check | ok | detail |
| --- | --- | --- |
| covers_every_li_leg_of_the_four_molecule_subcohort | PASS | 8 legs = 4 molecules x 2 Li states |
| mother_and_oxidised_states_are_screened_separately | PASS | 两条 Li 态在每条腿上都单列，构造规则写明从该态自己的连通性出发 |
| single_motif_propagation_is_prohibited | PASS | 8/8 rows carry the prohibition; production_start_kind=single_frozen_motif is registered as a caveat, not as an ensemble |
| motif_switching_is_documented_from_the_pilot | PASS | round-0 pilot identities differ between the two Li states for: SL |
| round0_evidence_is_taken_from_the_registered_pilot | PASS | 8/8 legs have a registered round-0 identity from outputs/physics_completion/free_states/pilot_li_state_energies.csv |
| screen_level_is_cheap_and_labelled_as_a_screen | PASS | xTB GFN2 (gas phase) coordination-motif screen |
| keep_three_independent_motifs_with_registered_escalation | PASS | keep_lowest=3, max_keep=6 on every leg |
| stop_rule_is_registered | PASS | stop rule registered in selection_rule.json / selection_rule.md |
| budget_uses_the_measured_li_pilot_cost | PASS | 8 legs measured round-0 core-hours = 0.922445 (sum of cores x wall over the 8 Li pilot single points); round-1 starts per leg = 16 |
| nothing_is_claimed_computed_yet | PASS | 8/8 motif screens not_computed; sampling_index li_motif_sampling untouched |

## 边界

* 本层**没有跑任何 motif 筛选**：8 条腿全部 `motif_screen_status = not_computed`，`outputs/physics_completion/sampling/sampling_index.json` 的 `li_motif_sampling` 占位也保持不变。
* round-0 身份/给体接触数逐条取自已登记的 Li pilot 单点，不是推断；其成本为重测值（cores x wall）。
* 生产级 Li 腿仍是单代表 motif：本层只登记「系综该怎么做、怎么做才算不违规」。
