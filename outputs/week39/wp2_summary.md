# Week 39 / WP2 — 固定背景配对自由能标签

**状态**：账本与系综规则已冻结；48 行生产模板中已登记 8/16 个主态的真实 Opt+Freq 账本行（其余行热校正保持为空，缺值不写 0）。已另跑 12 主集自由态 + Li 配位态 pilot（新增计算，方案 15.5/15.6），见下节。

## 交付

- `state_ledger_template.csv`：12 主集 × 4 主状态 = **48** 行记账模板（Opt/Freq/SP 分列）。
- `sampling_plan.csv`：4 个采样审计分子 × 4 状态，3→6 结构升级规则。
- `ensemble_rules.csv`：7 条系综/窗口/去重规则。
- `existing_electronic_layer.csv`：32 条既有电子能层数值（12 个分子），全部标注 `thermal_correction=absent`。

## 验收（22/22 通过）

| check | ok | detail |
| --- | --- | --- |
| ledger_covers_main_x_four_states | PASS | n_rows=48 |
| thermal_fields_left_empty_not_zero | PASS | planned=40 行留空；produced=8 行有值（无 0 填充） |
| sampling_plan_has_escalation_rule | PASS | n_rows=16 |
| existing_electronic_layer_is_labelled | PASS | 32 条既有数值 / 12 个分子 |
| ensemble_rules_frozen | PASS | n_rules=7 |
| pilot_free_state_jobs_all_converged | PASS | free-state rows=36 over 12 main-set molecules |
| pilot_vertical_ip_is_basis_consistent | PASS | DMC=8.957162 eV,EMC=8.537180 eV,DEC=8.592402 eV,EC=8.603601 eV,PC=8.542029 eV,DME=6.831624 eV,DOL=7.184396 eV,GBL=8.034424 eV,SL=7.937598 eV,DMSO=6.475203 eV,AN=9.463296 eV,TMP=8.715843 eV |
| pilot_ledger_instance_is_complete | PASS | record=C01|M; G=-9354.960153462 eV |
| pilot_cost_ledger_records_core_hours | PASS | jobs=109; total=6.546039 core-hours |
| pilot_li_states_converged_and_intact | PASS | rows=24; LiM_plus bound 12/12; dissociated=C08|LiM_2plus,C16|LiM_2plus |
| pilot_covers_all_four_master_states | PASS | free=36 + li=24 rows over 12 main-set molecules |
| pilot_donor_placement_recorded | PASS | families=carbonyl,ether,nitrile,phosphoryl,sulfone,sulfoxide |
| pilot_covers_all_twelve_main_molecules | PASS | molecules=12 |
| pilot_coordination_shift_computed | PASS | 10 interpretable + 2 dissociated(not interpretable); d_ip 0.357-0.897 eV over interpretable |
| pilot_flags_dissociated_dication_states | PASS | dissociated=[DME,AN] |
| wp2_production_states_terminated_without_imaginary | PASS | 9 条已生产账本行（主态 + 额外 def2-TZVPD 中性腿）全部 terminated / Opt 收敛 / 无虚频 |
| wp2_production_gibbs_decomposes_from_the_solution_sp | PASS | max |G - (E_SP + G-E(el))| = 1.000e-08 Eh over 9 state(s) |
| wp2_production_is_a_registered_subset | PASS | states 8/16 over 4/4 molecules; extra legs 1 |
| wp2_production_fills_only_the_produced_template_rows | PASS | produced=8 planned=40; planned rows carry empty G |
| wp2_production_li_states_record_binding_metrics | PASS | li_states=0 bound=0 |
| wp2_production_cost_records_allocated_core_hours | PASS | jobs=9; total=91.012667 core-hours |
| wp2_production_redox_uses_basis_consistent_legs | PASS | extra_legs=1; free_computed=GBL 7.685265; li_computed=none |

## 12 主集四主态 pilot（方案 15.5 / 15.6，新增计算）

几何：RDKit ETKDG+MMFF start -> xTB 6.7.1pre GFN2 Opt (gas)；方法：wB97X-D4/def2-TZVP (neutral); wB97X-D4/def2-TZVPD (charged, diffuse); SMD acetonitrile。原始输出留在仓库外，不入交付镜像。

覆盖 **12 主集全部分子**的**四主态**：自由态 M、M+ 与 Li 配位态 LiM_plus、LiM_2plus。

| 分子 | 量 | 一致基组 | E(中性) Eh | E(阳离子) Eh | Eox_vertical (eV) |
| --- | --- | --- | --- | --- | --- |
| DMC | Eox_vertical | def2-TZVPD (same basis for neutral and cation) | -343.856181464206 | -343.527011826787 | 8.957162 |
| EMC | Eox_vertical | def2-TZVPD (same basis for neutral and cation) | -383.213141521146 | -382.899405959663 | 8.537180 |
| DEC | Eox_vertical | def2-TZVPD (same basis for neutral and cation) | -422.570563717756 | -422.254798778826 | 8.592402 |
| EC | Eox_vertical | def2-TZVPD (same basis for neutral and cation) | -342.650103844399 | -342.333927357547 | 8.603601 |
| PC | Eox_vertical | def2-TZVPD (same basis for neutral and cation) | -382.009785515284 | -381.695871733911 | 8.542029 |
| DME | Eox_vertical | def2-TZVPD (same basis for neutral and cation) | -309.102759637016 | -308.851702088551 | 6.831624 |
| DOL | Eox_vertical | def2-TZVPD (same basis for neutral and cation) | -268.551257729030 | -268.287236055064 | 7.184396 |
| GBL | Eox_vertical | def2-TZVPD (same basis for neutral and cation) | -306.737875285260 | -306.442615657033 | 8.034424 |
| SL | Eox_vertical | def2-TZVPD (same basis for neutral and cation) | -706.153885628549 | -705.862184264030 | 7.937598 |
| DMSO | Eox_vertical | def2-TZVPD (same basis for neutral and cation) | -553.370194407920 | -553.132235081139 | 6.475203 |
| AN | Eox_vertical | def2-TZVPD (same basis for neutral and cation) | -132.866896538774 | -132.519126824547 | 9.463296 |
| TMP | Eox_vertical | def2-TZVPD (same basis for neutral and cation) | -762.426072838656 | -762.105771531730 | 8.715843 |

自由能账本实例（1 行，qRRHO）：

| 记录 | 级别 | E_SP (Eh) | ZPE (Eh) | E→G 热项 (Eh) | 熵项 (Eh) | G_single (Eh) | G (eV) | 标准态项 (eV) | 虚频 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| C01\|M | wB97X-D4/def2-TZVP SMD(acetonitrile) NumFreq (qRRHO) | -343.854211229029 | 0.09601496 | 0.06577493 | -0.03825196 | -343.78844462 | -9354.960153462 | 0.082148 | 0 |

成本账本：109 个作业（ORCA 61 / xTB 48），合计 **6.546039 core-hours**（allocated cores × wall clock）。

Li 配位两态（SMD，def2-TZVPD，Li 按给体类型沿外侧 1.9 A 起点后 GFN2 优化；donor_contacts = 2.60 A 内给体数）：

| 记录 | 电荷/多重度 | 基函数 | SCF | 末单点 (Eh) | Li-O/N (A) | 给体接触 | 非 Li 片段数 | 身份 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| C01\|LiM_plus | 1/1 | 302 | 20 | -351.306668426280 | 1.654 | 1 | 1 | intact_monodentate_carbonyl |
| C01\|LiM_2plus | 2/2 | 302 | 20 | -350.957111976693 | 1.805 | 1 | 1 | intact_monodentate_carbonyl |
| C02\|LiM_plus | 1/1 | 357 | 20 | -390.664261161903 | 1.659 | 1 | 1 | intact_monodentate_carbonyl |
| C02\|LiM_2plus | 2/2 | 357 | 31 | -390.323857580036 | 1.782 | 1 | 1 | intact_monodentate_carbonyl |
| C03\|LiM_plus | 1/1 | 412 | 20 | -430.021811072568 | 1.653 | 1 | 1 | intact_monodentate_carbonyl |
| C03\|LiM_2plus | 2/2 | 412 | 20 | -429.679002025732 | 1.736 | 1 | 1 | intact_monodentate_carbonyl |
| C04\|LiM_plus | 1/1 | 284 | 20 | -350.101404846212 | 1.658 | 1 | 1 | intact_monodentate_carbonyl |
| C04\|LiM_2plus | 2/2 | 284 | 18 | -349.772032662564 | 1.852 | 1 | 1 | intact_monodentate_carbonyl |
| C05\|LiM_plus | 1/1 | 339 | 20 | -389.461161737606 | 1.651 | 1 | 1 | intact_monodentate_carbonyl |
| C05\|LiM_2plus | 2/2 | 339 | 23 | -389.134132175016 | 1.800 | 1 | 1 | intact_monodentate_carbonyl |
| C08\|LiM_plus | 1/1 | 335 | 20 | -316.574613930125 | 1.795 | 2 | 1 | intact_bidentate_ether |
| C08\|LiM_2plus | 2/2 | 335 | 18 | -316.277931354453 | 11.298 | 0 | 1 | dissociated_ether |
| C09\|LiM_plus | 1/1 | 262 | 20 | -275.998301763872 | 1.973 | 2 | 1 | intact_bidentate_ether |
| C09\|LiM_2plus | 2/2 | 262 | 22 | -275.715481828471 | 2.505 | 1 | 1 | intact_monodentate_ether |
| C13\|LiM_plus | 1/1 | 299 | 20 | -314.190822388363 | 1.667 | 1 | 1 | intact_monodentate_carbonyl |
| C13\|LiM_2plus | 2/2 | 299 | 23 | -313.866423793393 | 1.815 | 1 | 1 | intact_monodentate_carbonyl |
| C14\|LiM_plus | 1/1 | 363 | 20 | -713.604058153811 | 1.885 | 2 | 1 | intact_bidentate_sulfone |
| C14\|LiM_2plus | 2/2 | 363 | 18 | -713.289177417651 | 1.721 | 1 | 1 | intact_monodentate_sulfone |
| C15\|LiM_plus | 1/1 | 231 | 20 | -560.832093775537 | 1.628 | 1 | 1 | intact_monodentate_sulfoxide |
| C15\|LiM_2plus | 2/2 | 231 | 20 | -560.561162382104 | 1.802 | 1 | 1 | intact_monodentate_sulfoxide |
| C16\|LiM_plus | 1/1 | 155 | 19 | -140.319887493920 | 1.859 | 1 | 1 | intact_monodentate_nitrile |
| C16\|LiM_2plus | 2/2 | 155 | 18 | -139.946294773154 | 10.953 | 0 | 1 | dissociated_nitrile |
| C17\|LiM_plus | 1/1 | 412 | 20 | -769.884723216208 | 1.604 | 1 | 1 | intact_monodentate_phosphoryl |
| C17\|LiM_2plus | 2/2 | 412 | 26 | -769.550930450943 | 1.684 | 1 | 1 | intact_monodentate_phosphoryl |

配位位移（SMD 自洽口径）：d_ip = IP(Li 复合物) - IP(自由分子)。

| 分子 | E([LiM]+) Eh | E([LiM]2+) Eh | IP_Li (eV) | IP_free (eV) | d_ip (eV) | 2+ 态 | 可解释 | 冻结 C1 motif | 冻结 d_ip_smd (eV) | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| DMC | -351.306668426280 | -350.957111976693 | 9.511916 | 8.957162 | 0.554754 | bound | true | m1 | -1.75858 | frozen C1 layer value exists but mixes conventions (gas-phase free IP as the SMD reference); not directly comparable |
| EMC | -390.664261161903 | -390.323857580036 | 9.262853 | 8.537180 | 0.725673 | bound | true | - | - | no frozen C1 primary row for this molecule |
| DEC | -430.021811072568 | -429.679002025732 | 9.328309 | 8.592402 | 0.735907 | bound | true | - | - | no frozen C1 primary row for this molecule |
| EC | -350.101404846212 | -349.772032662564 | 8.962674 | 8.603601 | 0.359073 | bound | true | m1 | -2.032304 | frozen C1 layer value exists but mixes conventions (gas-phase free IP as the SMD reference); not directly comparable |
| PC | -389.461161737606 | -389.134132175016 | 8.898928 | 8.542029 | 0.356899 | bound | true | - | - | no frozen C1 primary row for this molecule |
| DME | -316.574613930125 | -316.277931354453 | 8.073144 | 6.831624 | 1.241520 | dissociated (Li leaves the fragment during GFN2 relaxation) | false | m1 | -1.308041 | frozen C1 layer value exists but mixes conventions (gas-phase free IP as the SMD reference); not directly comparable |
| DOL | -275.998301763872 | -275.715481828471 | 7.695923 | 7.184396 | 0.511527 | bound | true | m1 | -0.906573 | frozen C1 layer value exists but mixes conventions (gas-phase free IP as the SMD reference); not directly comparable |
| GBL | -314.190822388363 | -313.866423793393 | 8.827335 | 8.034424 | 0.792911 | bound | true | m1 | -1.387599 | frozen C1 layer value exists but mixes conventions (gas-phase free IP as the SMD reference); not directly comparable |
| SL | -713.604058153811 | -713.289177417651 | 8.568341 | 7.937598 | 0.630743 | bound | true | m1 | -1.261894 | frozen C1 layer value exists but mixes conventions (gas-phase free IP as the SMD reference); not directly comparable |
| DMSO | -560.832093775537 | -560.561162382104 | 7.372419 | 6.475203 | 0.897216 | bound | true | m1 | -1.25523 | frozen C1 layer value exists but mixes conventions (gas-phase free IP as the SMD reference); not directly comparable |
| AN | -140.319887493920 | -139.946294773154 | 10.165976 | 9.463296 | 0.702680 | dissociated (Li leaves the fragment during GFN2 relaxation) | false | m1 | -2.177326 | frozen C1 layer value exists but mixes conventions (gas-phase free IP as the SMD reference); not directly comparable |
| TMP | -769.884723216208 | -769.550930450943 | 9.082964 | 8.715843 | 0.367121 | bound | true | m1 | -1.551212 | frozen C1 layer value exists but mixes conventions (gas-phase free IP as the SMD reference); not directly comparable |

## 生产首段：4 主集分子 x 4 主态的真实 Opt+Freq 自由能

级别：wB97X-D4 (= omegaB97X-D4) / def2-TZVP for the neutral leg and def2-TZVPD for the charged/Li legs; SMD acetonitrile; Opt NumFreq TightOpt TightSCF SlowConv；几何起点为既有冻结 r2SCAN-3c 结构，每态一个代表结构。
进度：已登记 **8/16** 个主态（完成分子 -）；未完成的状态不出现在表里，也不写成 0。
账本 G = E_SP + (G - E(el)) + 标准态项（RT ln V_m，1 atm -> 1 mol/L）；标准态项在同一化学计量差值中相消。

| 记录 | E_SP (Eh) | ZPE (Eh) | E->G 热项 (Eh) | G_single (Eh) | G (eV) | 虚频 | 最低频 (cm^-1) | Li-O/N (A) | 非 Li 片段 | 身份 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| C01|M | -343.85476184 | 0.09586398 | 0.06520269 | -343.78955915 | -9354.990481369 | 0 | 116.03 | - | - | intact |
| C01|M_plus | -343.54453019 | 0.09014966 | 0.05836622 | -343.48616397 | -9346.734677940 | 0 | 70.26 | - | - | intact |
| C02|M | -383.21194726 | 0.12437320 | 0.09205369 | -383.11989357 | -10425.223402455 | 0 | 77.89 | - | - | intact |
| C02|M_plus | -382.91291033 | 0.12293835 | 0.08957027 | -382.82334006 | -10417.153770352 | 0 | 62.29 | - | - | intact |
| C13|M | -306.73708477 | 0.09943860 | 0.07086694 | -306.66621783 | -8344.812901968 | 0 | 150.06 | - | - | intact |
| C13|M_plus | -306.45395804 | 0.09748803 | 0.06823672 | -306.38572132 | -8337.180203094 | 0 | 164.90 | - | - | intact |
| C14|M | -706.15322084 | 0.12428876 | 0.09358347 | -706.05963738 | -19212.861505449 | 0 | 37.15 | - | - | intact |
| C14|M_plus | -705.86571853 | 0.12059954 | 0.08861666 | -705.77710188 | -19205.173322831 | 0 | 68.25 | - | - | intact |
| C13|M_tzvpd | -306.73892277 | 0.09936051 | 0.07077317 | -306.66814960 | -8344.865468108 | 0 | 146.18 | - | - | intact |

成本：9 个 Opt+Freq 作业，合计 91.012667 core-hours（allocated cores x wall clock）。

基组一致（同为 def2-TZVPD）的自由腿 Gox_single 与 Li 腿配位位移（两条腿分开登记）：

| 分子 | 自由腿 | Li 腿 | 整行 | Eox_adiabatic (eV) | Gox_single (eV) | E->G 台阶 (eV) | Li IP (E, eV) | Li IP (G, eV) | 配位位移 (E, eV) | 配位位移 (G, eV) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| DMC | not_computed | not_computed | not_computed |  |  |  |  |  |  |  |
| EMC | not_computed | not_computed | not_computed |  |  |  |  |  |  |  |
| GBL | computed | not_computed | free_only | 7.754285 | 7.685265 | -0.069020 |  |  |  |  |
| SL | not_computed | not_computed | not_computed |  |  |  |  |  |  |  |

## 限制
- 生产模板只回填已跑完的主态（本次 8/16）：中性腿 def2-TZVP、带电/Li 腿 def2-TZVPD，两腿相减不是基组一致的自由分子 IP，本报告不据此计算 Eox；其余行热校正保持为空（未把缺值写成 0）。
- Gox_single 与配位位移在 production_redox.csv 单列，只用两腿同为 def2-TZVPD 的差值。
- 生产首段每态只有**单一代表结构**（n_conformers = 1），不是方案 6.1 的多构象/多 motif 系综；6 kcal/mol 窗口与 3 结构上限仍是资源规则。
- pilot 覆盖 12 主集全部分子，但每态只有单一构象（GFN2 起点），不是方案 6 的多构象系综生产；几何来自 GFN2 而非 r2SCAN-3c。
- DME 与 AN 的 2+ 态在 GFN2 弛豫中 Li 解离（Li-O/N > 10 A），故其 d_ip 记为不可解释、不进入结论；这本身是 GFN2 下 2+ 复合物不稳定的 QC 结果。
- Li 配位态只对单一给体位点、单一构象做了一次；不能替代 12 主集完整生产。
- pilot 配位位移为 SMD 自洽口径；冻结 C1 层把气相自由 IP 当作 SMD 参考，属混口径，两者不可直接相比。
- 标准态项把理想气体 1 atm 自由能换到溶液 1 mol/L（RT ln V_m）；同一化学计量的 redox 差值中该项相消。
- 既有 P1v/P1a/C1 数值是 r2SCAN-3c 气相电子能差，不能直接当作固定背景 SMD 自由能标签。
- 采样窗口 6 kcal/mol 与上限 3 结构是**资源规则**，不是已经证明收敛的采样尺度。
