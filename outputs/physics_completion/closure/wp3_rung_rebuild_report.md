# WP3 翻转阶梯与排序证据：最终验收标签重建（derived）

> 由 `scripts/wp_production/build_wp2_closure.py` 从冻结产物只读派生：
> `closure/flip_persistence.csv`（翻转阶梯本体）与
> `ensembles/production_ensemble_labels.csv`（最终验收标签 accepted/provisional/limited）。
> 零新增电子结构计算；limited/provisional 态的数值不冒充 computed；空值不是零。
> **本报告不判排序收敛**，只报差异与 bound。

## 1. 翻转阶梯 12 格现值（2 对 x 6 级）

| pair | rung | delta (eV) | sign | status | 缺口归因 |
| --- | --- | --- | --- | --- | --- |
| EMC | GBL | R1a | 0.653471 | positive | computed | — |
| EMC | GBL | R1b | -0.336247 | negative | computed | — |
| EMC | GBL | R2 | 0.436638 | positive | computed | — |
| EMC | GBL | R3 | 0.442629 | positive | computed | — |
| EMC | GBL | R4 | 0.404536 | positive | computed | — |
| EMC | GBL | R4_screen | -0.250028 | negative | computed_screen_only | 筛选层（气相 GFN2），按纪律不计入 computed |
| EMC | SL | R1a | 0.703086 | positive | computed | — |
| EMC | SL | R1b | -0.477287 | negative | computed | — |
| EMC | SL | R2 | 0.286060 | positive | computed | — |
| EMC | SL | R3 | 0.359540 | positive | computed | — |
| EMC | SL | R4 | 0.356963 | positive | computed | — |
| EMC | SL | R4_screen | 0.371082 | positive | computed_screen_only | 筛选层（气相 GFN2），按纪律不计入 computed |

计数：computed=10 / 12；limited=0（有值但不计 computed）；provisional=0；computed_screen_only=2（另一档，不计 computed）；not_computed=0。

## 2. 四个非 computed 级的逐腿归因

### EMC | GBL / R4_screen（status=computed_screen_only）

note 原文：screen-level only (gas-phase GFN2), NOT the production R4 rung; headline L(M_plus) - L(M) at L = G_state; L = G_avg gives -0.267 eV; Li-conditioned L(LiM_2plus) - L(LiM_plus) gives -0.328 eV (sign=negative); four-level ladder in outputs/physics_completion/ensembles/ensemble_pair_rungs.csv

### EMC | SL / R4_screen（status=computed_screen_only）

note 原文：screen-level only (gas-phase GFN2), NOT the production R4 rung; headline L(M_plus) - L(M) at L = G_state; L = G_avg gives 0.355 eV; Li-conditioned L(LiM_2plus) - L(LiM_plus) gives -0.093 eV (sign=negative); four-level ladder in outputs/physics_completion/ensembles/ensemble_pair_rungs.csv

## 3. accepted 标签下的氧化轴排序与 RT ln N bound 敏感性

排序量 = `G_ensemble(M_plus) - G_ensemble(M)`（eV，与 R3/R4 同定义）；
两腿都 accepted 的分子才计入 computed 排序。对含 limited/provisional 腿的分子，
受限池漏掉的更低极小只会把 `G_ensemble` 再往下拉，所以其 gap 落在
`[gap - b(M_plus), gap + b(M)]`，`b = lowering_bound_rt_ln_n_kcal`（RT ln N 上限）。

| 分子 | gap (eV) | M_plus 腿 | M 腿 | bound 区间 [lo, hi] |
| --- | --- | --- | --- | --- |
| AN | 9.0603 | limited（rescue_budget_exhausted） | accepted | [9.0603, 9.0603] |
| DMC | 8.3048 | limited（rescue_budget_exhausted） | accepted | [8.3048, 8.3048] |
| EC | 8.2807 | accepted | accepted | [8.2629, 8.2807] |
| PC | 8.1547 | accepted | accepted | [8.1369, 8.1547] |
| EMC | 8.1076 | accepted | accepted | [8.0898, 8.1254] |
| TMP | 7.9449 | accepted | accepted | [7.9271, 7.9627] |
| SL | 7.7506 | accepted | accepted | [7.7328, 7.7506] |
| GBL | 7.7030 | accepted | accepted | [7.7030, 7.7208] |
| DEC | 7.3162 | accepted | accepted | [7.2880, 7.3444] |
| DOL | 7.0077 | accepted | accepted | [6.9899, 7.0077] |
| DME | 6.5975 | accepted | accepted | [6.5692, 6.6257] |
| DMSO | 6.3507 | accepted | accepted | [6.3507, 6.3507] |

**accepted-only Top-3 = EC > PC > EMC**（n=10 个两腿 accepted 的分子）。

Top-3 地板 = EMC 的 8.1076 eV。若 11 个 limited 态全部换成真值（各分子在其 bound 区间内任意取值）：

| 分子 | 当前 gap | 区间上界 hi | 上界能否越过 Top-3 地板 |
| --- | --- | --- | --- |
| AN | 9.0603 | 9.0603 | **能** |
| DMC | 8.3048 | 8.3048 | **能** |

注意：AN, DMC 的 RT ln N bound = 0（n_unique = 1，RT ln 1 = 0）。
该界只覆盖**已计入池的 N 个成员**；limited 态漏掉的独立盆地不在 N 里，
所以这些分子的真值下降**可能超过**其 RT ln N 上界——上表对 bound=0 分子的
「不能」判定是**弱证据**（对 bound>0 分子才有约束力）。

**结论：Top-3 未被 bound 覆盖。** AN, DMC 的区间上界都越过 accepted Top-3 的地板，
若 limited 态全部换成真值，Top-3 **可能**改写（当前值已越线者可直接改写；
仅上界越线者的改写依赖其真值落点）。差异与 bound 如上，**不判排序收敛**。

口径提醒：`lowering_bound_rt_ln_n_kcal = RT ln N` 是**已计入池采样完备时额外下降的数学上限**，
不是真值的点估计，也不覆盖未采到的独立盆地；bound 覆盖不等于排序收敛，
二者都不是收敛判据（按 2026-10-19 决定）。
