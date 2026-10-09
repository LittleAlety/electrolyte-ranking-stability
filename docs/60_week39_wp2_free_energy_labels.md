# Week 39 / WP2 — 固定背景配对自由能标签

**状态**：账本与系综规则已冻结；48 行生产模板的热校正仍为空。已另跑 DMC/EMC 自由态 pilot（新增计算，方案 15.5/15.6），见下节。

## 交付

- `state_ledger_template.csv`：12 主集 × 4 主状态 = **48** 行记账模板（Opt/Freq/SP 分列）。
- `sampling_plan.csv`：4 个采样审计分子 × 4 状态，3→6 结构升级规则。
- `ensemble_rules.csv`：7 条系综/窗口/去重规则。
- `existing_electronic_layer.csv`：32 条既有电子能层数值（12 个分子），全部标注 `thermal_correction=absent`。

## 验收（12/12 通过）

| check | ok | detail |
| --- | --- | --- |
| ledger_covers_main_x_four_states | PASS | n_rows=48 |
| thermal_fields_left_empty_not_zero | PASS | 48 行的 g_single_ev / thermal_corr_ev 均为空串 |
| sampling_plan_has_escalation_rule | PASS | n_rows=16 |
| existing_electronic_layer_is_labelled | PASS | 32 条既有数值 / 12 个分子 |
| ensemble_rules_frozen | PASS | n_rules=7 |
| pilot_free_state_jobs_all_converged | PASS | free-state rows=6; molecules=DMC,EMC |
| pilot_vertical_ip_is_basis_consistent | PASS | DMC=8.958413 eV,EMC=8.538134 eV |
| pilot_ledger_instance_is_complete | PASS | record=C01|M; G=-9354.960153462 eV |
| pilot_cost_ledger_records_core_hours | PASS | jobs=19; total=1.855470 core-hours |
| pilot_li_states_converged_and_intact | PASS | li rows=4; Li-O 1.654-1.805 A |
| pilot_covers_all_four_master_states | PASS | free-state rows=6 + li-state rows=4 over DMC,EMC |
| pilot_coordination_shift_computed | PASS | DMC d_ip=0.553513 eV,EMC d_ip=0.724703 eV |

## DMC/EMC 四主态 pilot（方案 15.5 / 15.6，新增计算）

几何：RDKit ETKDG+MMFF start -> xTB 6.7.1pre GFN2 Opt (gas)；方法：wB97X-D4/def2-TZVP (neutral); wB97X-D4/def2-TZVPD (cation, diffuse); SMD acetonitrile。原始输出留在仓库外，不入交付镜像。

覆盖 DMC/EMC 的**四主态**：自由态 M、M+ 与 Li 配位态 LiM_plus、LiM_2plus。

| 分子 | 量 | 一致基组 | E(中性) Eh | E(阳离子) Eh | Eox_vertical (eV) |
| --- | --- | --- | --- | --- | --- |
| DMC | Eox_vertical | def2-TZVPD (same basis for neutral and cation) | -343.856181464212 | -343.526965851004 | 8.958413 |
| EMC | Eox_vertical | def2-TZVPD (same basis for neutral and cation) | -383.213141521146 | -382.899370886410 | 8.538134 |

自由能账本实例（1 行，qRRHO）：

| 记录 | 级别 | E_SP (Eh) | ZPE (Eh) | E→G 热项 (Eh) | 熵项 (Eh) | G_single (Eh) | G (eV) | 标准态项 (eV) | 虚频 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| C01\|M | wB97X-D4/def2-TZVP SMD(acetonitrile) NumFreq (qRRHO) | -343.854211229029 | 0.09601496 | 0.06577493 | -0.03825196 | -343.78844462 | -9354.960153462 | 0.082148 | 0 |

成本账本：19 个作业（ORCA 11 / xTB 8），合计 **1.855470 core-hours**（allocated cores × wall clock）。

Li 配位两态（SMD，def2-TZVPD，Li 置于羰基 O 外侧 1.9 A 起点后 GFN2 优化）：

| 记录 | 电荷/多重度 | 基函数 | SCF | 末单点 (Eh) | Li-O (A) | 非 Li 片段数 | 身份 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| C01\|LiM_plus | 1/1 | 302 | 20 | -351.306668533885 | 1.654 | 1 | intact_monodentate_carbonyl |
| C01\|LiM_2plus | 2/2 | 302 | 20 | -350.957111705625 | 1.805 | 1 | intact_monodentate_carbonyl |
| C02\|LiM_plus | 1/1 | 357 | 20 | -390.664261343481 | 1.659 | 1 | intact_monodentate_carbonyl |
| C02\|LiM_2plus | 2/2 | 357 | 31 | -390.323858369572 | 1.782 | 1 | intact_monodentate_carbonyl |

配位位移（SMD 自洽口径）：d_ip = IP(Li 复合物) - IP(自由分子)。

| 分子 | E([LiM]+) Eh | E([LiM]2+) Eh | IP_Li (eV) | IP_free (eV) | d_ip (eV) | 冻结 C1 motif | 冻结 d_ip_smd (eV) | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| DMC | -351.306668533885 | -350.957111705625 | 9.511926 | 8.958413 | 0.553513 | m1 | -1.75858 | frozen C1 value exists but mixes conventions; not directly comparable |
| EMC | -390.664261343481 | -390.323858369572 | 9.262837 | 8.538134 | 0.724703 | - | - | no frozen C1 row for this molecule |

## 限制

- 48 行**生产模板**的热校正仍为空（尚未做生产频率）；pilot 只单独给出 1 条 DMC 中性完整账本行。
- pilot 只覆盖 2 个分子（DMC/EMC）的四主态，且几何来自 xTB GFN2 而非 r2SCAN-3c；不能替代 12 主集完整生产。
- pilot 配位位移为 SMD 自洽口径；冻结 C1（DMC m1）把气相自由 IP 当作 SMD 参考，属混口径，两者不可直接相比；EMC 无冻结 C1 行。
- 标准态项把理想气体 1 atm 自由能换到溶液 1 mol/L（RT ln V_m）；同一化学计量的 redox 差值中该项相消。
- 既有 P1v/P1a/C1 数值是 r2SCAN-3c 气相电子能差，不能直接当作固定背景 SMD 自由能标签。
- 采样窗口 6 kcal/mol 与上限 3 结构是**资源规则**，不是已经证明收敛的采样尺度。
