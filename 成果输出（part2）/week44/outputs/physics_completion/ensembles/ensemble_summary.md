# 方案 6.1 / 6.2：四分子系综层（气相 GFN2 筛选层）

> 由 `scripts/wp_production/build_wp2_ensemble_free_energies.py` 生成。
> 本层把两个**已登记**的池（自由态构象池 + Li motif 池）在 GFN2 `--ohess` 自由能层面求 Boltzmann 系综，
> 用来回答「采样是否足以改变结论」的**廉价那一半**。它**不是**生产自由能，
> 也**不替代**生产 R4 台阶（那需要 wB97X-D4 + SMD 的额外结构腿）。
> 两种口径并列且**不可互换**：`G_state` 含构象熵（<= G_min），`G_avg` 是布居平均（>= G_min）。

## 逐腿系综

| 记录 | 登记结构 | 计入系综 | 虚频剔除 | 最低 G (Eh) | G_state (Eh) | G_avg (Eh) | G_state-G_min (kJ/mol) | G_avg-G_min (kJ/mol) | E_avg-E_min (kJ/mol) | 3->6 状态 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| C01|LiM_2plus | 1 | 1 | 0 | -20.878369261 | -20.878369261 | -20.878369261 | 0.000 | 0.000 | 0.000 | - |
| C01|LiM_plus | 2 | 2 | 0 | -21.564068616 | -21.564068659 | -21.564068189 | -0.000 | 0.001 | 0.001 | - |
| C01|M | 1 | 1 | 0 | -21.640327426 | -21.640327426 | -21.640327426 | 0.000 | 0.000 | 0.000 | registered_pending_round1_free_energy_check |
| C01|M_plus | 1 | 0 | 1 | - | - | - | - | - | - | registered_pending_round1_free_energy_check |
| C02|LiM_2plus | 1 | 1 | 0 | -24.051502567 | -24.051502567 | -24.051502567 | 0.000 | 0.000 | 0.000 | - |
| C02|LiM_plus | 2 | 1 | 1 | -24.709735233 | -24.709735233 | -24.709735233 | 0.000 | 0.000 | 0.000 | - |
| C02|M | 2 | 2 | 0 | -24.782647517 | -24.783045764 | -24.782437958 | -1.046 | 0.550 | 0.971 | registered_pending_round1_free_energy_check |
| C02|M_plus | 2 | 1 | 1 | -24.256662501 | -24.256662501 | -24.256662501 | 0.000 | 0.000 | 0.000 | registered_pending_round1_free_energy_check |
| C03|LiM_2plus | 1 | 1 | 0 | -27.213616746 | -27.213616746 | -27.213616746 | 0.000 | 0.000 | 0.000 | - |
| C03|LiM_plus | 2 | 2 | 0 | -27.853632325 | -27.853639614 | -27.853597037 | -0.019 | 0.093 | 0.084 | - |
| C03|M | 3 | 3 | 0 | -27.923665978 | -27.924382968 | -27.923438255 | -1.882 | 0.598 | 2.120 | registered_pending_round1_free_energy_check |
| C03|M_plus | 4 | 3 | 1 | -27.411143542 | -27.411325952 | -27.410775978 | -0.479 | 0.965 | 1.305 | registered_pending_round1_free_energy_check |
| C04|LiM_2plus | 1 | 1 | 0 | -19.872774293 | -19.872774293 | -19.872774293 | 0.000 | 0.000 | 0.000 | - |
| C04|LiM_plus | 1 | 1 | 0 | -20.570115942 | -20.570115942 | -20.570115942 | 0.000 | 0.000 | 0.000 | - |
| C04|M | 1 | 1 | 0 | -20.642593926 | -20.642593926 | -20.642593926 | 0.000 | 0.000 | 0.000 | registered_pending_round1_free_energy_check |
| C04|M_plus | 1 | 0 | 1 | - | - | - | - | - | - | registered_pending_round1_free_energy_check |
| C05|LiM_2plus | 1 | 1 | 0 | -23.040903373 | -23.040903373 | -23.040903373 | 0.000 | 0.000 | 0.000 | - |
| C05|LiM_plus | 1 | 1 | 0 | -23.719826713 | -23.719826713 | -23.719826713 | 0.000 | 0.000 | 0.000 | - |
| C05|M | 1 | 1 | 0 | -23.788914392 | -23.788914392 | -23.788914392 | 0.000 | 0.000 | 0.000 | registered_pending_round1_free_energy_check |
| C05|M_plus | 1 | 1 | 0 | -23.236528928 | -23.236528928 | -23.236528928 | 0.000 | 0.000 | 0.000 | registered_pending_round1_free_energy_check |
| C08|LiM_2plus | 1 | 1 | 0 | -20.964038624 | -20.964038624 | -20.964038624 | 0.000 | 0.000 | 0.000 | - |
| C08|LiM_plus | 1 | 1 | 0 | -21.614711074 | -21.614711074 | -21.614711074 | 0.000 | 0.000 | 0.000 | - |
| C08|M | 6 | 6 | 0 | -21.667772335 | -21.668465998 | -21.667208288 | -1.821 | 1.481 | 1.181 | registered_pending_round1_free_energy_check |
| C08|M_plus | 6 | 4 | 2 | -21.182572185 | -21.183171407 | -21.182181685 | -1.573 | 1.025 | 3.473 | registered_pending_round1_free_energy_check |
| C09|LiM_2plus | 2 | 2 | 0 | -16.779108148 | -16.779750150 | -16.779095774 | -1.686 | 0.032 | 0.005 | - |
| C09|LiM_plus | 1 | 1 | 0 | -17.449903387 | -17.449903387 | -17.449903387 | 0.000 | 0.000 | 0.000 | - |
| C09|M | 1 | 0 | 1 | - | - | - | - | - | - | registered_pending_round1_free_energy_check |
| C09|M_plus | 1 | 1 | 0 | -17.028290571 | -17.028290571 | -17.028290571 | 0.000 | 0.000 | 0.000 | registered_pending_round1_free_energy_check |
| C13|LiM_2plus | 1 | 1 | 0 | -18.965822431 | -18.965822431 | -18.965822431 | 0.000 | 0.000 | 0.000 | - |
| C13|LiM_plus | 1 | 1 | 0 | -19.636092278 | -19.636092278 | -19.636092278 | 0.000 | 0.000 | 0.000 | - |
| C13|M | 1 | 1 | 0 | -19.703253973 | -19.703253973 | -19.703253973 | 0.000 | 0.000 | 0.000 | registered_pending_round1_free_energy_check |
| C13|M_plus | 1 | 1 | 0 | -19.167682540 | -19.167682540 | -19.167682540 | 0.000 | 0.000 | 0.000 | registered_pending_round1_free_energy_check |
| C14|LiM_2plus | 3 | 2 | 1 | -23.222196725 | -23.222847041 | -23.222192591 | -1.707 | 0.011 | 0.001 | - |
| C14|LiM_plus | 1 | 1 | 0 | -23.884483030 | -23.884483030 | -23.884483030 | 0.000 | 0.000 | 0.000 | - |
| C14|M | 1 | 1 | 0 | -23.924709137 | -23.924709137 | -23.924709137 | 0.000 | 0.000 | 0.000 | registered_pending_round1_free_energy_check |
| C14|M_plus | 1 | 1 | 0 | -23.411962922 | -23.411962922 | -23.411962922 | 0.000 | 0.000 | 0.000 | registered_pending_round1_free_energy_check |
| C15|LiM_2plus | 1 | 1 | 0 | -13.865365655 | -13.865365655 | -13.865365655 | 0.000 | 0.000 | 0.000 | - |
| C15|LiM_plus | 1 | 1 | 0 | -14.523758064 | -14.523758064 | -14.523758064 | 0.000 | 0.000 | 0.000 | - |
| C15|M | 1 | 1 | 0 | -14.572544714 | -14.572544714 | -14.572544714 | 0.000 | 0.000 | 0.000 | registered_pending_round1_free_energy_check |
| C15|M_plus | 1 | 1 | 0 | -14.074780347 | -14.074780347 | -14.074780347 | 0.000 | 0.000 | 0.000 | registered_pending_round1_free_energy_check |
| C16|LiM_plus | 1 | 1 | 0 | -8.582325710 | -8.582325710 | -8.582325710 | 0.000 | 0.000 | 0.000 | - |
| C16|M | 1 | 1 | 0 | -8.667091980 | -8.667091980 | -8.667091980 | 0.000 | 0.000 | 0.000 | registered_pending_round1_free_energy_check |
| C16|M_plus | 1 | 0 | 1 | - | - | - | - | - | - | registered_pending_round1_free_energy_check |
| C17|LiM_2plus | 2 | 2 | 0 | -29.135570388 | -29.136181130 | -29.135527732 | -1.604 | 0.112 | 0.009 | - |
| C17|LiM_plus | 2 | 2 | 0 | -29.784329286 | -29.784330135 | -29.784323335 | -0.002 | 0.016 | 0.013 | - |
| C17|M | 2 | 1 | 1 | -29.836346909 | -29.836346909 | -29.836346909 | 0.000 | 0.000 | 0.000 | registered_pending_round1_free_energy_check |
| C17|M_plus | 3 | 2 | 1 | -29.314440838 | -29.314930283 | -29.314293147 | -1.285 | 0.388 | 2.949 | registered_pending_round1_free_energy_check |

## 配对三层台（本层口径；不是生产 R2/R3/R4）

口径与 `closure/flip_persistence.csv` 的**氧化轴**一致（`delta = IP(i) - IP(j)`），
但两侧都是**同一分子内部**的差分，因此绝不混化学计量比（登记规则 E5）：
free_ionisation 是 `L(M_plus) - L(M)`，Li_conditioned 是 `L(LiM_2plus) - L(LiM_plus)`。
差值一律是**左分子减右分子**（EMC 减 GBL / EMC 减 SL），单位 kJ/mol；正号 = 左分子更难氧化。


| pair | state | E_min | G_min | G_state | G_avg | 符号稳定 | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| EMC vs GBL | free_ionisation | -26.917 | -25.169 | -24.124 | -25.719 | 是 | the sign survives all four levels |
| EMC vs GBL | Li_conditioned | -29.282 | -31.604 | -31.604 | -31.604 | 是 | the sign survives all four levels |
| EMC vs SL | free_ionisation | 33.945 | 34.758 | 35.804 | 34.208 | 是 | the sign survives all four levels |
| EMC vs SL | Li_conditioned | -7.817 | -10.643 | -8.935 | -10.654 | 是 | the sign survives all four levels |

### Li 配位是否改变这个符号

| pair | 四层里两侧符号不一致的层 | 符号一致 | 说明 |
| --- | --- | --- | --- |
| EMC vs GBL | 无 | 是 | does Li coordination change the signed gap between the two molecules? |
| EMC vs SL | E_min, G_min, G_state, G_avg | 否 | does Li coordination change the signed gap between the two molecules? |

## 本层给出的判断

* 登记结构总数 75，计入系综 63；有系综的腿 43 / 47。
* `G_state-G_min` 与 `G_avg-G_min` 是同一个系综的两侧边界（下界侧含构象熵、上界侧是布居平均），
  它们明显小于关键 pair 的间距时，采样不足以推翻该 pair；只有跨过独立容差或改写 Top-k 时，才按同一规则扩到 6（本层不自行扩）。
* 有虚频的结构留在 CSV 里并带虚频数，**排除出系综**，不是删掉。
* 生产级结论仍然待定：生产 R4 需要额外结构的生产腿，本层不声称完成 R4。

## 验收

| check | ok | detail |
| --- | --- | --- |
| every_registered_structure_has_a_row | True | 75 rows for 75 registered structures |
| every_geometry_still_matches_its_registered_sha256 | True | mismatched: none |
| boltzmann_weights_sum_to_one_per_leg | True | offenders: none |
| ensemble_shifts_obey_their_mathematical_bounds | True | offenders: none |
| ensemble_layer_is_labelled_as_a_screen | True | xTB GFN2 (gas phase) ensemble free energy; claim_level=screen_gfn2_gas_phase |
| imaginary_mode_structures_are_reported_not_dropped | True | 75 structures carry an imaginary-mode count |
| pair_ladder_is_fully_reported | True | 16 pair cells for 2 pairs x 2 states x 4 levels |
| pair_sign_verdict_matches_the_reported_signs | True | offenders: none |
| pair_axis_never_mixes_stoichiometries | True | offenders: none |
| registered_structures_have_unique_cache_keys | True | 75 distinct keys for 75 structures |
| leg_records_agree_with_their_leg_id | True | offenders: none |
| published_gfn2_records_are_complete | True | incomplete: none |

合计 12 项，失败 0 项。
