# 方案 6.1 / 执行第 3 步：主集 Li 配位 motif 采样预注册

> 由 `scripts/wp_production/build_li_motif_sampling_plan.py` 生成；**零新增电子结构计算**。
> 规则在任何 motif 筛选跑出结果之前登记，不随后续结果修改。
> 对象 = `data/metadata/physics_completion_set.csv` 的 `in_main` 分子集（12 个）x 两个 Li 态 = 24 条腿。

## 为什么必须先冻结这条规则

方案 6.1 要求带电态补独立种子、且 motif 切换时重新检查电子身份与连接关系。已登记的 round-0 pilot 单点直接给出了证据：

| 分子 | LiM_plus 身份 | LiM_2plus 身份 |
| --- | --- | --- |
| DMC | intact_monodentate_carbonyl | intact_monodentate_carbonyl |
| EMC | intact_monodentate_carbonyl | intact_monodentate_carbonyl |
| DEC | intact_monodentate_carbonyl | intact_monodentate_carbonyl |
| EC | intact_monodentate_carbonyl | intact_monodentate_carbonyl |
| PC | intact_monodentate_carbonyl | intact_monodentate_carbonyl |
| DME | intact_bidentate_ether | dissociated_ether |
| DOL | intact_bidentate_ether | intact_monodentate_ether |
| GBL | intact_monodentate_carbonyl | intact_monodentate_carbonyl |
| SL | intact_bidentate_sulfone | intact_monodentate_sulfone |
| DMSO | intact_monodentate_sulfoxide | intact_monodentate_sulfoxide |
| AN | intact_monodentate_nitrile | dissociated_nitrile |
| TMP | intact_monodentate_phosphoryl | intact_monodentate_phosphoryl |

即：**同一分子的两个 Li 态 motif 并不总是同一个**（上表差异即为证），而生产 Li 腿目前各自只从**一个冻结几何**起步（`n_conformers = 1`，`production_start_kind = single_frozen_motif`）。因此本层登记 motif 系综的选取规则，不宣称 motif 采样已完成。

## 冻结的选取规则

* object = the 12 in_main molecules of physics_completion_set.csv x the two Li states LiM_plus / LiM_2plus = 24 legs
* the molecule list is derived from the frozen cohort file, never transcribed into this script
* each leg is constructed from its own charge and multiplicity; the two Li states are never chained
* candidates = monodentate placements on the round-0 donor class plus bidentate pairs whose donor-donor distance allows a Li bridge, layered with the state's own conformer seeds
* screen level = gas-phase GFN2-xTB (a screen, never a production free energy)
* deduplicate by coordination mode and heavy-atom RMSD / torsion; keep the lowest 3 independent motifs
* extend 3 -> 6 only if the key-pair Li rung is sensitive to the motif choice; the escalation is registered in advance, never decided from the outcome
* stop rule = after two screen rounds without resolution report sampling_limited / unresolved
* only one selected representative motif enters the DFT single-conformer production leg; the other independent motifs stay registered for the 3 -> 6 expansion

## 作业计划（24 条腿，逐条登记）

| 记录 | 分子 | 态 | q/m | round-0 身份 | 给体接触 | Li–O (Å) | round-0 实测 core-hour | round-1 起点 | 保留 | 筛选状态 | 筛选保留 motif |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| C01|LiM_plus | DMC | LiM_plus | 1/1 | intact_monodentate_carbonyl | 1 | 1.654 | 0.077889 | 16 | 3 | computed | 2 |
| C01|LiM_2plus | DMC | LiM_2plus | 2/2 | intact_monodentate_carbonyl | 1 | 1.805 | 0.095667 | 16 | 3 | computed | 1 |
| C02|LiM_plus | EMC | LiM_plus | 1/1 | intact_monodentate_carbonyl | 1 | 1.659 | 0.132333 | 16 | 3 | computed | 2 |
| C02|LiM_2plus | EMC | LiM_2plus | 2/2 | intact_monodentate_carbonyl | 1 | 1.782 | 0.215778 | 16 | 3 | computed | 1 |
| C03|LiM_plus | DEC | LiM_plus | 1/1 | intact_monodentate_carbonyl | 1 | 1.653 | 0.090556 | 16 | 3 | computed | 2 |
| C03|LiM_2plus | DEC | LiM_2plus | 2/2 | intact_monodentate_carbonyl | 1 | 1.736 | 0.108000 | 16 | 3 | computed | 1 |
| C04|LiM_plus | EC | LiM_plus | 1/1 | intact_monodentate_carbonyl | 1 | 1.658 | 0.069000 | 16 | 3 | computed | 1 |
| C04|LiM_2plus | EC | LiM_2plus | 2/2 | intact_monodentate_carbonyl | 1 | 1.852 | 0.075778 | 16 | 3 | computed | 1 |
| C05|LiM_plus | PC | LiM_plus | 1/1 | intact_monodentate_carbonyl | 1 | 1.651 | 0.105667 | 16 | 3 | computed | 1 |
| C05|LiM_2plus | PC | LiM_2plus | 2/2 | intact_monodentate_carbonyl | 1 | 1.800 | 0.165222 | 16 | 3 | computed | 1 |
| C08|LiM_plus | DME | LiM_plus | 1/1 | intact_bidentate_ether | 2 | 1.795 | 0.074778 | 16 | 3 | computed | 1 |
| C08|LiM_2plus | DME | LiM_2plus | 2/2 | dissociated_ether | 0 | 11.298 | 0.074667 | 16 | 3 | computed | 1 |
| C09|LiM_plus | DOL | LiM_plus | 1/1 | intact_bidentate_ether | 2 | 1.973 | 0.063667 | 16 | 3 | computed | 1 |
| C09|LiM_2plus | DOL | LiM_2plus | 2/2 | intact_monodentate_ether | 1 | 2.505 | 0.084222 | 16 | 3 | computed | 2 |
| C13|LiM_plus | GBL | LiM_plus | 1/1 | intact_monodentate_carbonyl | 1 | 1.667 | 0.087000 | 16 | 3 | computed | 1 |
| C13|LiM_2plus | GBL | LiM_2plus | 2/2 | intact_monodentate_carbonyl | 1 | 1.815 | 0.116778 | 16 | 3 | computed | 1 |
| C14|LiM_plus | SL | LiM_plus | 1/1 | intact_bidentate_sulfone | 2 | 1.885 | 0.099111 | 16 | 3 | computed | 1 |
| C14|LiM_2plus | SL | LiM_2plus | 2/2 | intact_monodentate_sulfone | 1 | 1.721 | 0.097889 | 16 | 3 | computed | 3 |
| C15|LiM_plus | DMSO | LiM_plus | 1/1 | intact_monodentate_sulfoxide | 1 | 1.628 | 0.052667 | 16 | 3 | computed | 1 |
| C15|LiM_2plus | DMSO | LiM_2plus | 2/2 | intact_monodentate_sulfoxide | 1 | 1.802 | 0.063778 | 16 | 3 | computed | 1 |
| C16|LiM_plus | AN | LiM_plus | 1/1 | intact_monodentate_nitrile | 1 | 1.859 | 0.024222 | 16 | 3 | computed | 1 |
| C16|LiM_2plus | AN | LiM_2plus | 2/2 | dissociated_nitrile | 0 | 10.953 | 0.023889 | 16 | 3 | unresolved | 0 |
| C17|LiM_plus | TMP | LiM_plus | 1/1 | intact_monodentate_phosphoryl | 1 | 1.604 | 0.177333 | 16 | 3 | computed | 2 |
| C17|LiM_2plus | TMP | LiM_2plus | 2/2 | intact_monodentate_phosphoryl | 1 | 1.684 | 0.237444 | 16 | 3 | computed | 2 |

## 已执行的筛选结果（运行记录 li_motif_screen.json）

| 记录 | 起点数 | 成功 | 保留 motif | 判定 | 最低 motif |
| --- | --- | --- | --- | --- | --- |
| C01|LiM_plus | 10 | 10 | 2 | production_motif_is_lowest | monodentate_donor3 |
| C01|LiM_2plus | 10 | 10 | 1 | production_motif_within_1kj | monodentate_donor3 |
| C02|LiM_plus | 10 | 10 | 2 | production_motif_within_1kj | monodentate_donor4 |
| C02|LiM_2plus | 10 | 10 | 1 | production_motif_is_lowest | monodentate_donor4 |
| C03|LiM_plus | 10 | 10 | 2 | production_motif_is_lowest | monodentate_donor4 |
| C03|LiM_2plus | 10 | 10 | 1 | production_motif_within_1kj | monodentate_donor4 |
| C04|LiM_plus | 10 | 10 | 1 | production_motif_within_1kj | monodentate_donor4 |
| C04|LiM_2plus | 10 | 9 | 1 | production_motif_within_1kj | monodentate_donor4 |
| C05|LiM_plus | 10 | 10 | 1 | production_motif_within_1kj | monodentate_donor5 |
| C05|LiM_2plus | 10 | 10 | 1 | production_motif_within_1kj | monodentate_donor5 |
| C08|LiM_plus | 7 | 7 | 1 | production_motif_is_lowest | bidentate_donors1_4 |
| C08|LiM_2plus | 7 | 7 | 1 | production_motif_within_1kj | bidentate_donors1_4 |
| C09|LiM_plus | 7 | 7 | 1 | production_motif_within_1kj | bidentate_donors2_4 |
| C09|LiM_2plus | 7 | 6 | 2 | production_motif_within_1kj | monodentate_donor4 |
| C13|LiM_plus | 4 | 4 | 1 | production_motif_within_1kj | monodentate_donor0 |
| C13|LiM_2plus | 7 | 7 | 1 | production_motif_within_1kj | monodentate_donor0 |
| C14|LiM_plus | 7 | 7 | 1 | production_motif_within_1kj | bidentate_donors0_2 |
| C14|LiM_2plus | 7 | 7 | 3 | production_motif_is_lowest | monodentate_donor0 |
| C15|LiM_plus | 5 | 5 | 1 | production_motif_within_1kj | monodentate_donor3 |
| C15|LiM_2plus | 5 | 5 | 1 | production_motif_within_1kj | monodentate_donor3 |
| C16|LiM_plus | 5 | 5 | 1 | production_motif_within_1kj | monodentate_donor2 |
| C16|LiM_2plus | 2 | 2 | 0 | unresolved | - |
| C17|LiM_plus | 14 | 14 | 2 | production_motif_is_lowest | monodentate_donor3 |
| C17|LiM_2plus | 14 | 14 | 2 | production_motif_within_1kj | monodentate_donor3 |

> 筛选层是气相 GFN2-xTB，不是生产自由能；保留结构的几何路径见 li_motif_screen.md。
> 本次运行记录覆盖 24/24 条腿；其余 0 条腿保持 `not_computed`，等执行器重跑后补齐。


## 验收（12/13 通过）

| check | ok | detail |
| --- | --- | --- |
| covers_every_li_leg_of_the_main_cohort | PASS | 24 legs = 12 in_main molecules x 2 Li states |
| mother_and_oxidised_states_are_screened_separately | PASS | 两条 Li 态在每条腿上都单列，构造规则写明从该态自己的连通性出发 |
| single_motif_propagation_is_prohibited | PASS | 24/24 rows carry the prohibition; production_start_kind=single_frozen_motif is registered as a caveat, not as an ensemble |
| motif_switching_is_documented_from_the_pilot | PASS | round-0 pilot identities differ between the two Li states for: AN, DME, DOL, SL |
| round0_evidence_is_taken_from_the_registered_pilot | PASS | 24/24 legs have a registered round-0 identity from outputs/physics_completion/free_states/pilot_li_state_energies.csv |
| screen_level_is_cheap_and_labelled_as_a_screen | PASS | xTB GFN2 (gas phase) coordination-motif screen |
| keep_three_independent_motifs_with_registered_escalation | PASS | keep_lowest=3, max_keep=6 on every leg |
| stop_rule_is_registered | PASS | stop rule registered in selection_rule.json / selection_rule.md |
| budget_uses_the_measured_li_pilot_cost | PASS | 24 legs measured round-0 core-hours = 2.413335 (sum of cores x wall over the Li pilot single points); round-1 starts per leg = 16 |
| screen_claims_match_the_run_record | PASS | run record present: 24/24 legs carry an outcome (23 computed, 1 unresolved); 0 leg(s) without a record stay not_computed; stray record legs: none |
| sampling_index_does_not_claim_a_leg_this_layer_never_screened | PASS | all sampling_index computed claims are backed by a run-record leg |
| screen_parent_geometries_are_current | FAIL | stale parent geometry for: C05|LiM_2plus |
| uncomputed_legs_are_registered_as_uncomputed | PASS | 24/24 legs carry a run-record outcome; the remaining 0 stay not_computed (re-run scripts/wp_production/screen_li_motifs.py to close the gap) |

## 边界

* 本层只登记规则；筛选由 `scripts/wp_production/screen_li_motifs.py` 执行，运行记录写在`outputs/physics_completion/li_motif_sampling/li_motif_screen.json`。没有运行记录条目的腿仍是`motif_screen_status = not_computed`；有记录条目的腿逐条写 computed / unresolved，并核对父几何是否已被重跑。
* round-0 身份/给体接触数逐条取自已登记的 Li pilot 单点，不是推断；其成本为重测值（cores x wall）。
* 分子集从冻结的 `physics_completion_set.csv` 的 `in_main` 集合推导，不在本脚本里另抄一份。
* 生产级 Li 腿仍是单代表 motif：本层只登记「系综该怎么做、怎么做才算不违规」。
