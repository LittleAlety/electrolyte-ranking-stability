# Week 39 / WP2 — 固定背景配对自由能标签

**状态**：账本与系综规则已冻结；48 行生产模板中已登记 48/48 个主态的真实 Opt+Freq 账本行（其余行热校正保持为空，缺值不写 0）。已另跑 12 主集自由态 + Li 配位态 pilot（新增计算，方案 15.5/15.6），见下节。

## 交付

- `state_ledger_template.csv`：12 主集 × 4 主状态 = **48** 行记账模板（Opt/Freq/SP 分列）。
- `sampling_plan.csv`：4 个采样审计分子 × 4 状态，3→6 结构升级规则。
- `ensemble_rules.csv`：7 条系综/窗口/去重规则。
- `existing_electronic_layer.csv`：32 条既有电子能层数值（12 个分子），全部标注 `thermal_correction=absent`。

## 验收（23/23 通过）

| check | ok | detail |
| --- | --- | --- |
| ledger_covers_main_x_four_states | PASS | n_rows=48 |
| thermal_fields_left_empty_not_zero | PASS | planned=0 行留空；produced=48 行有值（无 0 填充） |
| sampling_plan_has_escalation_rule | PASS | n_rows=16 |
| existing_electronic_layer_is_labelled | PASS | 32 条既有数值 / 12 个分子 |
| ensemble_rules_frozen | PASS | n_rules=7 |
| pilot_free_state_jobs_all_converged | PASS | free-state rows=36 over 12 main-set molecules |
| pilot_vertical_ip_is_basis_consistent | PASS | DMC=8.957162 eV,EMC=8.537180 eV,DEC=8.592402 eV,EC=8.603601 eV,PC=8.542029 eV,DME=6.831624 eV,DOL=7.184396 eV,GBL=8.034424 eV,SL=7.937598 eV,DMSO=6.475203 eV,AN=9.463296 eV,TMP=8.715843 eV |
| pilot_ledger_instance_is_complete | PASS | record=C01|M; G=-9354.960153462 eV |
| pilot_cost_ledger_records_core_hours | PASS | jobs=109; total=6.546039 core-hours |
| pilot_cost_ledger_records_verifiable_provenance | PASS | raw verified=109/109; memory=MISSING; retry=UNVERIFIABLE |
| pilot_li_states_converged_and_intact | PASS | rows=24; LiM_plus bound 12/12; dissociated=C08|LiM_2plus,C16|LiM_2plus |
| pilot_covers_all_four_master_states | PASS | free=36 + li=24 rows over 12 main-set molecules |
| pilot_donor_placement_recorded | PASS | families=carbonyl,ether,nitrile,phosphoryl,sulfone,sulfoxide |
| pilot_covers_all_twelve_main_molecules | PASS | molecules=12 |
| pilot_coordination_shift_computed | PASS | 10 interpretable + 2 dissociated(not interpretable); d_ip 0.357-0.897 eV over interpretable |
| pilot_flags_dissociated_dication_states | PASS | dissociated=[DME,AN] |
| wp2_production_states_terminated_without_imaginary | PASS | 60 条已生产账本行（主态 + 额外 def2-TZVPD 中性腿）全部 terminated / Opt 收敛 / 无虚频 |
| wp2_production_gibbs_decomposes_from_the_solution_sp | PASS | max |G - (E_SP + G-E(el))| = 1.000e-08 Eh over 60 state(s) |
| wp2_production_is_a_registered_subset | PASS | states 48/48 over 12/12 molecules; extra legs 12 |
| wp2_production_fills_only_the_produced_template_rows | PASS | produced=48 planned=0; planned rows carry empty G |
| wp2_production_li_states_record_binding_metrics | PASS | li_states=24 bound=24 |
| wp2_production_cost_records_allocated_core_hours | PASS | jobs=60; complete=58; explicit_incomplete=2; invalid=0; known_subtotal=557.184769 core-hours |
| wp2_production_redox_uses_basis_consistent_legs | PASS | extra_legs=12; free_computed=DMC 8.304819,EMC 8.127378,DEC 7.282164,EC 8.296614,PC 8.171614,DME 6.594137,DOL 7.021654,GBL 7.684749,SL 7.767838,DMSO 6.350743,AN 9.060062,TMP 7.918973; li_computed=DMC,EMC,DEC,EC,PC,DME,DOL,GBL,SL,DMSO,AN,TMP |

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
进度：已登记 **48/48** 个主态（完成分子 C01,C02,C03,C04,C05,C08,C09,C13,C14,C15,C16,C17）；未完成的状态不出现在表里，也不写成 0。
账本 G = E_SP + (G - E(el)) + 标准态项（RT ln V_m，1 atm -> 1 mol/L）；标准态项在同一化学计量差值中相消。

| 记录 | E_SP (Eh) | ZPE (Eh) | E->G 热项 (Eh) | G_single (Eh) | G (eV) | 虚频 | 最低频 (cm^-1) | Li-O/N (A) | 非 Li 片段 | 身份 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| C01|M | -343.85475940 | 0.09598335 | 0.06546995 | -343.78928945 | -9354.983142458 | 0 | 117.74 | - | - | intact |
| C01|M_plus | -343.54453238 | 0.09011551 | 0.05837850 | -343.48615388 | -9346.734403378 | 0 | 62.07 | - | - | intact |
| C01|LiM_plus | -351.31132513 | 0.09813624 | 0.06572720 | -351.24559793 | -9557.879632476 | 0 | 79.31 | 1.821 | 1 | bound |
| C01|LiM_2plus | -350.97956216 | 0.09178989 | 0.05846457 | -350.92109760 | -9549.049528660 | 0 | 106.30 | 1.927 | 1 | bound |
| C02|M | -383.21194574 | 0.12448485 | 0.09225832 | -383.11968742 | -10425.217792828 | 0 | 80.52 | - | - | intact |
| C02|M_plus | -382.91291074 | 0.12304180 | 0.08982815 | -382.82308258 | -10417.146763964 | 0 | 53.04 | - | - | intact |
| C02|LiM_plus | -390.66882279 | 0.12641893 | 0.09230080 | -390.57652199 | -10628.128598485 | 0 | 70.19 | 1.816 | 1 | bound |
| C02|LiM_2plus | -390.35140012 | 0.12233111 | 0.08702094 | -390.26437918 | -10619.634759918 | 0 | 45.98 | 1.901 | 1 | bound |
| C03|M | -422.56949630 | 0.15291357 | 0.11896191 | -422.45053439 | -11495.464661110 | 0 | 55.38 | - | - | intact |
| C03|M_plus | -422.30045800 | 0.15008069 | 0.11545800 | -422.18500001 | -11488.239102535 | 0 | 61.38 | - | - | intact |
| C03|LiM_plus | -430.02668009 | 0.15504600 | 0.11943763 | -429.90724246 | -11698.372024527 | 0 | 57.67 | 1.810 | 1 | bound |
| C03|LiM_2plus | -429.70749487 | 0.14777631 | 0.11084362 | -429.59665125 | -11689.920407147 | 0 | 71.38 | 1.905 | 1 | bound |
| C04|M | -342.64991152 | 0.07615162 | 0.04776292 | -342.60214860 | -9322.679394260 | 0 | 160.31 | - | - | intact |
| C04|M_plus | -342.33942928 | 0.06931037 | 0.04006740 | -342.29936187 | -9314.440147600 | 0 | 145.98 | - | - | intact |
| C04|LiM_plus | -350.10590933 | 0.07774207 | 0.04704453 | -350.05886480 | -9525.586978905 | 0 | 72.82 | 1.834 | 1 | bound |
| C04|LiM_2plus | -349.77636958 | 0.07054803 | 0.03913422 | -349.73723536 | -9516.834995985 | 0 | 39.33 | 1.903 | 1 | bound |
| C05|M | -382.00960517 | 0.10394432 | 0.07385295 | -381.93575222 | -10393.001274810 | 0 | 98.93 | - | - | intact |
| C05|M_plus | -381.70642968 | 0.09994368 | 0.06880413 | -381.63762555 | -10384.888834843 | 0 | 101.34 | - | - | intact |
| C05|LiM_plus | -389.46606331 | 0.10575137 | 0.07362342 | -389.39243988 | -10595.908082842 | 0 | 77.57 | 1.833 | 1 | bound |
| C05|LiM_2plus | -389.14621326 | 0.10146949 | 0.06828603 | -389.07792723 | -10587.349757644 | 0 | 86.22 | 1.896 | 1 | bound |
| C08|M | -309.10114509 | 0.14213739 | 0.11052079 | -308.99062430 | -8408.063224216 | 0 | 54.48 | - | - | intact |
| C08|M_plus | -308.85947440 | 0.14143207 | 0.10844355 | -308.75103085 | -8401.543554306 | 0 | 40.80 | - | - | intact |
| C08|LiM_plus | -316.57862493 | 0.14556226 | 0.11287913 | -316.46574580 | -8611.471642588 | 0 | 74.56 | 1.906 | 1 | bound |
| C08|LiM_2plus | -316.28719473 | 0.14111822 | 0.10678792 | -316.18040682 | -8603.707173393 | 0 | 58.80 | 1.903 | 1 | bound |
| C09|M | -268.55082322 | 0.09400365 | 0.06635453 | -268.48446869 | -7305.834578572 | 0 | 50.96 | - | - | intact |
| C09|M_plus | -268.29079749 | 0.09005016 | 0.06184695 | -268.22895054 | -7298.881575500 | 0 | 170.91 | - | - | intact |
| C09|LiM_plus | -276.00117131 | 0.09649443 | 0.06768243 | -275.93348887 | -7508.532743845 | 0 | 139.09 | 2.083 | 1 | bound |
| C09|LiM_2plus | -275.72141501 | 0.09100446 | 0.06041241 | -275.66100259 | -7501.118014433 | 0 | 79.87 | 2.415 | 1 | bound |
| C13|M | -306.73708368 | 0.09947380 | 0.07092793 | -306.66615574 | -8344.811212413 | 0 | 155.26 | - | - | intact |
| C13|M_plus | -306.45395798 | 0.09750884 | 0.06829190 | -306.38566609 | -8337.178700209 | 0 | 176.55 | - | - | intact |
| C13|LiM_plus | -314.19479513 | 0.10114532 | 0.07039960 | -314.12439553 | -8547.760256054 | 0 | 59.80 | 1.833 | 1 | bound |
| C13|LiM_2plus | -313.87748744 | 0.09344939 | 0.06163998 | -313.81584747 | -8539.364235618 | 0 | 63.94 | 1.923 | 1 | bound |
| C14|M | -706.15322046 | 0.12431782 | 0.09366672 | -706.05955374 | -19212.859229489 | 0 | 42.96 | - | - | intact |
| C14|M_plus | -705.86571925 | 0.12049892 | 0.08852866 | -705.77719059 | -19205.175736753 | 0 | 69.78 | - | - | intact |
| C14|LiM_plus | -713.61011358 | 0.12590202 | 0.09355628 | -713.51655730 | -19415.774633598 | 0 | 50.08 | 2.053 | 1 | bound |
| C14|LiM_2plus | -713.29821835 | 0.12163066 | 0.08744900 | -713.21076936 | -19407.453719853 | 0 | 61.08 | 2.439 | 1 | bound |
| C15|M | -553.37139513 | 0.08022422 | 0.05214680 | -553.31924833 | -15056.583783647 | 0 | 198.76 | - | - | intact |
| C15|M_plus | -553.13963333 | 0.07970904 | 0.05050149 | -553.08913183 | -15050.321994684 | 0 | 141.78 | - | - | intact |
| C15|LiM_plus | -560.83721043 | 0.08206664 | 0.05169696 | -560.78551347 | -15259.751208187 | 0 | 65.68 | 1.778 | 1 | bound |
| C15|LiM_2plus | -560.57066665 | 0.08068462 | 0.04894971 | -560.52171694 | -15252.572938919 | 0 | 51.09 | 1.990 | 1 | bound |
| C16|M | -132.86684672 | 0.04560634 | 0.02162819 | -132.84521853 | -3614.902552353 | 0 | 406.88 | - | - | intact |
| C16|M_plus | -132.52780620 | 0.03997516 | 0.01506330 | -132.51274290 | -3605.855429567 | 0 | 301.84 | - | - | intact |
| C16|LiM_plus | -140.32153435 | 0.04733538 | 0.02091290 | -140.30062145 | -3817.774400828 | 0 | 117.74 | 1.935 | 1 | bound |
| C16|LiM_2plus | -139.95760255 | 0.04001090 | 0.01156698 | -139.94603558 | -3808.125627762 | 0 | 37.07 | 2.180 | 1 | bound |
| C17|M | -762.42635895 | 0.13511986 | 0.09909453 | -762.32726442 | -20743.981637980 | 0 | 49.46 | - | - | intact |
| C17|M_plus | -762.13626398 | 0.13404801 | 0.09677624 | -762.03948774 | -20736.150835588 | 0 | 42.17 | - | - | intact |
| C17|LiM_plus | -769.88051347 | 0.13676141 | 0.09891624 | -769.78159723 | -20946.824367279 | 0 | 36.61 | 1.769 | 1 | bound |
| C17|LiM_2plus | -769.57034612 | 0.13169543 | 0.09259697 | -769.47774916 | -20938.556240086 | 0 | 26.77 | 1.834 | 1 | bound |
| C01|M_tzvpd | -343.85676019 | 0.09592557 | 0.06540984 | -343.79135035 | -9355.039222404 | 0 | 117.72 | - | - | intact |
| C02|M_tzvpd | -383.21392558 | 0.12440377 | 0.09216737 | -383.12175821 | -10425.274141894 | 0 | 80.01 | - | - | intact |
| C03|M_tzvpd | -422.57150869 | 0.15284884 | 0.11889410 | -422.45261459 | -11495.521266236 | 0 | 55.53 | - | - | intact |
| C04|M_tzvpd | -342.65196153 | 0.07609280 | 0.04770472 | -342.60425681 | -9322.736761577 | 0 | 160.59 | - | - | intact |
| C05|M_tzvpd | -382.01171235 | 0.10387898 | 0.07378555 | -381.93792681 | -10393.060448419 | 0 | 98.67 | - | - | intact |
| C08|M_tzvpd | -309.10372202 | 0.14208860 | 0.11036110 | -308.99336092 | -8408.137691440 | 0 | 39.12 | - | - | intact |
| C09|M_tzvpd | -268.55300547 | 0.09392518 | 0.06601388 | -268.48699158 | -7305.903229907 | 0 | 23.78 | - | - | intact |
| C13|M_tzvpd | -306.73892667 | 0.09940528 | 0.07085127 | -306.66807540 | -8344.863449023 | 0 | 153.79 | - | - | intact |
| C14|M_tzvpd | -706.15622156 | 0.12422095 | 0.09356819 | -706.06265336 | -19212.943574446 | 0 | 44.18 | - | - | intact |
| C15|M_tzvpd | -553.37466454 | 0.08021394 | 0.05214721 | -553.32251734 | -15056.672737941 | 0 | 202.59 | - | - | intact |
| C16|M_tzvpd | -132.86729741 | 0.04558352 | 0.02160338 | -132.84569403 | -3614.915491367 | 0 | 405.64 | - | - | intact |
| C17|M_tzvpd | -762.42958844 | 0.13508001 | 0.09908382 | -762.33050462 | -20744.069808314 | 0 | 53.34 | - | - | intact |

成本：60 个 Opt+Freq 作业，已知小计 557.184769 core-hours；2 个作业总成本未知（非零成本，非完整总计）。

基组一致（同为 def2-TZVPD）的自由腿 Gox_single 与 Li 腿配位位移（两条腿分开登记）：

| 分子 | 自由腿 | Li 腿 | 整行 | Eox_adiabatic (eV) | Gox_single (eV) | E->G 台阶 (eV) | Li IP (E, eV) | Li IP (G, eV) | 配位位移 (E, eV) | 配位位移 (G, eV) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| DMC | computed | computed | computed | 8.496152 | 8.304819 | -0.191333 | 9.027730 | 8.830104 | 0.531579 | 0.525285 |
| EMC | computed | computed | computed | 8.191031 | 8.127378 | -0.063653 | 8.637511 | 8.493839 | 0.446480 | 0.366461 |
| DEC | computed | computed | computed | 7.375665 | 7.282164 | -0.093501 | 8.685472 | 8.451617 | 1.309807 | 1.169454 |
| EC | computed | computed | computed | 8.504436 | 8.296614 | -0.207822 | 8.967233 | 8.751983 | 0.462798 | 0.455369 |
| PC | computed | computed | computed | 8.307165 | 8.171614 | -0.135551 | 8.703563 | 8.558325 | 0.396399 | 0.386712 |
| DME | computed | computed | computed | 6.646316 | 6.594137 | -0.052179 | 7.930220 | 7.764469 | 1.283903 | 1.170332 |
| DOL | computed | computed | computed | 7.135043 | 7.021654 | -0.113388 | 7.612557 | 7.414729 | 0.477514 | 0.393075 |
| GBL | computed | computed | computed | 7.754393 | 7.684749 | -0.069644 | 8.634382 | 8.396020 | 0.879989 | 0.711272 |
| SL | computed | computed | computed | 7.904971 | 7.767838 | -0.137133 | 8.487102 | 8.320914 | 0.582131 | 0.553076 |
| DMSO | computed | computed | computed | 6.395525 | 6.350743 | -0.044782 | 7.253026 | 7.178269 | 0.857501 | 0.827526 |
| AN | computed | computed | computed | 9.238026 | 9.060062 | -0.177965 | 9.903089 | 9.648773 | 0.665062 | 0.588711 |
| TMP | computed | computed | computed | 7.981765 | 7.918973 | -0.062792 | 8.440084 | 8.268127 | 0.458318 | 0.349154 |

## 限制
- 生产模板只回填已跑完的主态（本次 48/48）：中性腿 def2-TZVP、带电/Li 腿 def2-TZVPD，两腿相减不是基组一致的自由分子 IP，本报告不据此计算 Eox；其余行热校正保持为空（未把缺值写成 0）。
- Gox_single 与配位位移在 production_redox.csv 单列，只用两腿同为 def2-TZVPD 的差值。
- 生产首段每态只有**单一代表结构**（n_conformers = 1），不是方案 6.1 的多构象/多 motif 系综；6 kcal/mol 窗口与 3 结构上限仍是资源规则。
- pilot 覆盖 12 主集全部分子，但每态只有单一构象（GFN2 起点），不是方案 6 的多构象系综生产；几何来自 GFN2 而非 r2SCAN-3c。
- DME 与 AN 的 2+ 态在 GFN2 弛豫中 Li 解离（Li-O/N > 10 A），故其 d_ip 记为不可解释、不进入结论；这本身是 GFN2 下 2+ 复合物不稳定的 QC 结果。
- Li 配位态只对单一给体位点、单一构象做了一次；不能替代 12 主集完整生产。
- pilot 配位位移为 SMD 自洽口径；冻结 C1 层把气相自由 IP 当作 SMD 参考，属混口径，两者不可直接相比。
- 标准态项把理想气体 1 atm 自由能换到溶液 1 mol/L（RT ln V_m）；同一化学计量的 redox 差值中该项相消。
- 既有 P1v/P1a/C1 数值是 r2SCAN-3c 气相电子能差，不能直接当作固定背景 SMD 自由能标签。
- 采样窗口 6 kcal/mol 与上限 3 结构是**资源规则**，不是已经证明收敛的采样尺度。
