# 机制案例页（最多 3 例）

选择规则（事先冻结）：优先选证据最强的稳健翻转，再选影响 Top-k 的 unresolved 边界，再选有身份改变的代表；**无稳健翻转时不强行补案例**。

口径：本页只登记既有冻结产物（P1v→P1a 氧化台阶，n=12，66 pair，源自 `outputs/phase2_p1a/p1v_vs_p1a.json`），**零新增电子结构计算**。方案 §7.3 的六项证据逐例逐项标注 **已具 / 部分 / 未具**；凡缺原始产物支撑的一律标 部分 或 未具，不把日志里的定性描述说成计算证据。数字与既有产物逐字一致；不一致处在第 4、5 项显式登记，不做调和。

## 六项覆盖总览（逐例）

| 项目（§7.3） | CASE1 EMC \| GBL | CASE2 EMC \| SL |
| --- | --- | --- |
| 原始结构 | 已具 | 已具 |
| 电子密度/自旋 | 部分 | 部分 |
| 配位变化 | 部分 | 部分 |
| E/G 分解 | 部分 | 部分 |
| 方法敏感性 | 已具 | 已具 |
| 实际选集影响 | 已具 | 已具 |

> 六项里「电子密度本体、多 motif/生产系综配位、G_ensemble」三处仍待补，故整体仍记 **partial**，不写 satisfied。

## CASE1：EMC | GBL

- 轴：oxidation (P1v -> P1a vertical-to-adiabatic)
- d_lower = 0.250050009 eV；d_upper = -0.455791550 eV；sigma = 0.206521142 eV
- 判定：ROBUST_INVERSION
- 选集影响（pair 级）：flips the relative oxidation order of the pair under relaxation

## CASE2：EMC | SL

- 轴：oxidation (P1v -> P1a vertical-to-adiabatic)
- d_lower = 0.408539433 eV；d_upper = -0.277578589 eV；sigma = 0.206521142 eV
- 判定：ROBUST_INVERSION
- 选集影响（pair 级）：flips the relative oxidation order of the pair under relaxation

## 原始结构证据（既有冻结几何，零新增计算）

| 分子 | 家族 | 原子数 | 元素序列一致 | 重原子成键对 | 平均 abs(dr) (Å) | 最大 abs(dr) (Å) | 最大变化键 | 该键 dr (Å) | dIP (eV) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| EMC | linear_carbonate | 15 | true | 6 | 0.053936 | 0.089787 | C4-O5 | 0.089787 | -0.9503160071914678 |
| GBL | ester | 12 | true | 6 | 0.037918 | 0.085612 | C2-O6 | -0.085612 | -0.244474448699469 |
| SL | sulfone | 15 | true | 5 | 0.009897 | 0.015528 | C5-C6 | -0.015528 | -0.26419798480917933 |

结构来源（既有冻结路径；按交付层纪律不复制原始几何文件，只交付派生的键长变化）：中性松弛几何 `outputs/week4/t2_opt_freq/{name}/{name}_G2.xyz`（已核验存在）；阳离子松弛几何 `outputs/phase2_p1a/geometry_relaxation/{name}/{name}_cation_opt.xyz`（已核验存在）。逐键表见 `outputs/physics_completion/pair_evidence/mechanism_bond_changes.csv`（17 条键），汇总见 `outputs/physics_completion/pair_evidence/mechanism_geometry.csv`。成键对只用 1.8 Å 几何截断枚举，不是力常数判据；键长是平移/旋转不变量，因此不需要结构叠合。

## 逐项证据与来源路径

### 1. 原始结构 —— 已具

- 中性 + 阳离子两套原始几何都在冻结路径上（见上表 `neutral_geometry` / `cation_geometry` 列，两文件均已核验存在），派生的逐键键长变化（`mechanism_bond_changes.csv`）可由冻结 .xyz 独立重算（`tests/test_physics_completion_batch.py::test_mechanism_bond_changes_recompute_from_frozen_geometry`）。
- CASE1：EMC 平均 |Δr| = 0.053936 Å、最大 0.089787 Å（C4-O5，伸缩 +0.089787）；GBL 平均 0.037918 Å、最大 0.085612 Å（C2-O6，-0.085612）。
- CASE2：SL 平均 0.009897 Å、最大 0.015528 Å（C5-C6，-0.015528）；EMC 同 CASE1。
- 缺口：无。原始几何留在冻结路径、未复制进交付层（这是交付层纪律，不是缺证据）。

### 2. 电子密度/自旋 —— 部分（自旋/电荷布居 已具；电子密度本体与 frontier 局域化 未具、待补）

- 已有（原始产物支撑）：`outputs/physics_completion/state_identity/state_identity_qc.csv` 逐态给出 Mulliken 与 Löwdin 原子电荷/自旋，并带原始日志路径与 sha256（如 `work/wp2prod/EMC/M_plus/EMC_M_plus.log`）。
  - 氧化态 M_plus 的自旋求和：EMC `spin_sum_mulliken` = 0.999999、GBL = 1.000002、SL = 1.000002（各一个未配对电子）；电荷求和与登记总电荷一致（`state_identity/state_identity_acceptance.csv` 的 `whole_atom_charge_sum...` 与 `whole_atom_spin_sum_matches_two_s` 均 ok=true）。
  - Li 条件态的自旋/电荷局域化类：EMC/GBL/SL 的 LiM_plus = Li_centered（`state_identity/Li_centered_states.csv`，share 0.950012 / 0.952082 / 0.921887），LiM_2plus = solvent_centered。
- 缺口（未具、待补）：没有电子密度本体产物——无 .cube/.dens、无密度差、无自旋密度分布图；frontier 轨道局域化在 `outputs/physics_completion/state_identity/thresholds.json` 里显式登记为 `frontier_localization.status = not_computed`（理由：生产 Opt 日志未要求逐轨道原子组成）。
- 结论：自旋/电荷布居这一半已具且可复算、带哈希；电子密度本体与 frontier 局域化未具 → 整项 部分。

### 3. 配位变化 —— 部分（三例分子的单构象条件态 Li 腿 已具；多 motif / 生产系综 未具、待补；且非本例轴）

- 已有（原始产物支撑，三个案例分子都在四分子生产子集内）：
  - `outputs/physics_completion/closure/four_molecule_state_closure.csv`：EMC/GBL/SL 的 LiM_plus、LiM_2plus 均 `register_status = produced_single_conformer`；Li–O 距离 `li_o_ang`：EMC 1.816 / 1.901，GBL 1.833 / 1.923，SL 2.053 / 2.439 Å；身份 bound/intact。
  - `outputs/physics_completion/free_states/production_redox.csv`：Li 条件态 IP 与配位位移 `coordination_shift_e_ev` / `_g_ev`：EMC 0.446461 / 0.373529，GBL 0.880186 / 0.707681，SL 0.582285 / 0.558920 eV。
  - `outputs/physics_completion/state_identity/state_identity_qc.csv`：Li–给体接触距离与 Mayer 键价（SL 的 LiM_plus 接触为 `O:2.0530;O:2.0545;S:2.5027`，valence 0.1491）。
  - `outputs/physics_completion/free_states/pilot_coordination_shift.csv`（更多分子的同类量）。
  - 条件态阶梯（筛选层 GFN2）：`outputs/physics_completion/ensembles/ensemble_pair_rungs.csv` 与 `closure/flip_persistence.csv` 的 R4_screen——EMC|GBL 的 Li 条件态 sign = negative，EMC|SL 的 Li 条件态 sign = negative（均为 screen，非生产）。
- 缺口（未具、待补）：每态只有 1 个 motif / 1 个构象（`li_motif_sampling/li_motif_screen.csv` 每态只保留 m1）；没有多 motif 或生产系综层的配位变化；且本案例轴是自由态氧化，配位变化属条件副轴（C0→C1），不是该翻转的成因。
- 结论：单构象条件态配位证据已具，多 motif / 生产系综未具 → 整项 部分。

### 4. E/G 分解 —— 部分（E 与 G_single 已具；G_ensemble 未具、待补）

- 已有（原始产物支撑）：
  - 逐态 E 与 G：`outputs/physics_completion/closure/four_molecule_state_closure.csv` 给出 `e_sp_solution_ev`、`g_single_ev`、`zpe_ev`、`thermal_corr_ev`、`std_state_corr_ev`（EMC/GBL/SL 各四主态）。
  - 单构象自由能标签：`outputs/physics_completion/free_states/production_redox.csv` 的 `eox_adiabatic_ev` / `gox_single_ev` / `thermal_step_free_ev`——EMC 8.191111 / 8.128207 / -0.062904，GBL 7.754285 / 7.685265 / -0.069020，SL 7.905012 / 7.776312 / -0.128700 eV。
  - pair 级 E 与 G：`outputs/physics_completion/closure/flip_persistence.csv` R2（溶液优化电子能）EMC|GBL = +0.436826、EMC|SL = +0.286099；R3（单构象自由能）EMC|GBL = +0.442942、EMC|SL = +0.351895。
- 缺口（未具、待补）：G_ensemble（生产 R4）未做——`flip_persistence.csv` R4 = `not_computed`；现有系综只有筛选层 GFN2（`outputs/physics_completion/ensembles/ensemble_free_energies.csv`，气相 GFN2），不能冒充生产 G_ensemble。
- **不一致（如实报告，不调和）**：R2/R3 的符号为正（+），与冻结的 R1b（负）相反。也就是说，垂直→绝热的这一对翻转**没有保留到溶液优化的电子能与单构象自由能层**（见 `outputs/physics_completion/closure/closure_summary.md` 的「固定几何 → 溶液各态优化 = 符号改变」）。
- 结论：E 与 G_single 分解已具，G_ensemble 未具 → 整项 部分。

### 5. 方法敏感性 —— 已具

- `outputs/physics_completion/method_audit/pair_gap_sensitivity.csv`：S1–S4 四设定下两对的竖直腿与弛豫腿 pair 差值，`vertical_sign_consistent` 与 `adiabatic_sign_consistent` 均 true，`sign_flip_across_legs` true。
  - EMC|GBL：竖直 0.612–0.697 eV；绝热 -0.328 … -0.345 eV（四条设定符号一致）。
  - EMC|SL：竖直 0.693–0.713 eV；绝热 -0.436 … -0.518 eV。
- `outputs/physics_completion/method_audit/robust_inversion_certification.csv`：EMC|GBL、EMC|SL 的 `certified` = true（对方法轴认证）。
- 设定与弛豫腿：`method_audit/method_settings.csv`（S1 omegaB97X-D4/def2-TZVP、S2 omegaB97X-D4/def2-TZVPD、S3 PBE0-D4/def2-TZVP、S4 PBE0-D4/def2-TZVPD）；`method_audit/relaxed_leg_matrix.csv` 32 格。
- **不一致（如实报告，不调和）**：本 CSV 与 `pair_evidence/pair_evidence.csv` 用的 `sigma = 0.206521142 eV` 是该台阶的**弛豫位移总体标准差**（`p1v_vs_p1a.json` `displacement.population_std_ev`），**不是方法 spread**；方法 spread 见 `robust_inversion_certification.csv`（EMC|GBL `adiabatic_sigma` = 0.006516 eV，EMC|SL = 0.032367 eV）。两者口径不同，不可混用。
- 反证：`outputs/physics_completion/pair_evidence/targeted_recheck/recheck_pair_gaps.csv`（S3/S4，生产 Opt 几何）给出 EMC|GBL = +0.4746 … +0.4819、EMC|SL = +0.3762 … +0.3900，均为正，`matches_frozen_r1b_sign` = false——**在生产几何上不复现冻结 R1b 的负号**（换几何与换泛函两因素不可分）。
- 结论：方法轴认证、范围与上述反证都齐 → 已具。

### 6. 实际选集影响 —— 已具

- `outputs/phase2_p1a/p1v_vs_p1a.json`（该台阶排序现算）：`kendall_tau_b` = 0.787879；`top_k_overlap` k=0.10 → 1.0、k=0.20 → 1.0、k=0.30 → 0.75；`decision_state_counts` = STABLE 55 / UNRESOLVED 9 / ROBUST_INVERSION 2。
- `outputs/physics_completion/pair_evidence/pair_evidence.csv`：66 pair 中 2 个 `state = ROBUST_INVERSION`，即本两例。
- 逐级 Top-k overlap 与 selection regret：`outputs/physics_completion/pair_evidence/frozen_rung_ladder.csv`（注意：该表 `G1_to_G2` 行是另一条 r2SCAN-3c 几何弛豫台阶，`f_robust_inversion` = 0、`top_k_overlap_main` = 1.0，**不是**本 P1v→P1a 台阶，口径不同）。
- 翻转持续性：`outputs/physics_completion/closure/flip_persistence.csv` 与 `closure_summary.md`——R1a（+）→ R1b（-）符号翻转，但 R2/R3 均为正、R4 `not_computed`；即 pair 级翻转**不保留**到生产溶液优化 E/G。
- 结论：pair 级翻转 + 该台阶的 tau_b/Top-k 均已具，并同时给出「不保留到 R2/R3」的实际边界 → 已具。

## 逐例关键数字对照

| 项目 | CASE1 EMC \| GBL | CASE2 EMC \| SL |
| --- | --- | --- |
| 原始结构 平均/最大 \|Δr\| (Å) | EMC 0.053936 / 0.089787；GBL 0.037918 / 0.085612 | EMC 同左；SL 0.009897 / 0.015528 |
| 自旋 M_plus `spin_sum_mulliken` | EMC 0.999999；GBL 1.000002 | EMC 同左；SL 1.000002 |
| 配位 `li_o_ang`（LiM+ / LiM2+） | EMC 1.816 / 1.901；GBL 1.833 / 1.923 | EMC 同左；SL 2.053 / 2.439 |
| `coordination_shift_g_ev` | EMC 0.373529；GBL 0.707681 | EMC 同左；SL 0.558920 |
| 台阶 R1a / R1b (eV) | +0.653471 / -0.336247 | +0.703086 / -0.477287 |
| 台阶 R2 / R3 (eV) | +0.436826 / +0.442942 | +0.286099 / +0.351895 |
| 方法范围 竖直 / 绝热 (eV) | 0.612–0.697 / -0.328…-0.345 | 0.693–0.713 / -0.436…-0.518 |
| 认证 | certified=true | certified=true |
| d_lower / d_upper (eV) | +0.250050009 / -0.455791550 | +0.408539433 / -0.277578589 |

> 说明：本页登记判定、原始结构、电子密度/自旋（自旋布居）、配位变化（单构象条件态）、E/G 分解（单构象）、方法敏感性与实际选集影响；**电子密度本体、多 motif/生产系综配位与 G_ensemble 仍待补**，故六项整体仍为 partial。
