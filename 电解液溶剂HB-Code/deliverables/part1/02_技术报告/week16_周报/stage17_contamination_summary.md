# Stage 17 / Week 16 · Part A：漏解污染上限（P1 → P2 台阶）

## 0. 一句话结论

把 P1→P2 台阶的 P2 腿换成 moread 臂后，两条轴的 tau_b / Top-k 重叠 / f_unresolved / f_robust_inv 均未被改写；两臂 tau_b 的 95% CI 重叠（污染被 CI 吸收）。

## 1. 逐轴对照表（published / default / moread）

| 轴 | 臂 | n | tau_b | tau_b 95% CI | O_20% | f_unresolved(after) | f_robust_inv | sigma 中位(eV) | shift 均值(eV) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| oxidation | **published** | 18 | 0.895 | [0.714, 1.000] | 0.750 | 0.111 | 0.000 | 0.198 | -2.393 |
| oxidation | default | 18 | 0.895 | [0.714, 1.000] | 0.750 | 0.111 | 0.000 | 0.198 | -2.393 |
| oxidation | moread | 18 | 0.922 | [0.774, 1.000] | 0.750 | 0.111 | 0.000 | 0.188 | -2.401 |
| reduction | **published** | 18 | 0.673 | [0.403, 0.873] | 0.500 | 0.222 | 0.000 | 0.217 | -2.173 |
| reduction | default | 18 | 0.673 | [0.403, 0.873] | 0.500 | 0.222 | 0.000 | 0.217 | -2.173 |
| reduction | moread | 18 | 0.673 | [0.413, 0.871] | 0.500 | 0.255 | 0.000 | 0.226 | -2.187 |

## 2. moread − published 逐项 delta

| 轴 | Δtau_b | ΔO_20% | Δf_unresolved(after) | Δf_robust_inv | Δsigma 中位 |
| --- | --- | --- | --- | --- | --- |
| oxidation | 0.026 | 0.000 | 0.000 | 0.000 | -0.010 |
| reduction | 0.000 | 0.000 | 0.033 | 0.000 | 0.009 |

## 3. delta = p2_moread − p2_default 统计

| 粒度 | n | mean(eV) | std(eV) | min(eV) | max(eV) | argmin | argmax |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 54 格（分子×态） | 54 | -0.007224 | 0.035743 | -0.156165 | 0.092274 | TEGDME/anion | EC/anion |
| 18 分子（氧化轴） | 18 | -0.007368 | 0.031615 | -0.134039 | 0.001382 | TMP | DEC |
| 18 分子（还原轴） | 18 | -0.014300 | 0.053620 | -0.156162 | 0.092273 | TEGDME | EC |

## 4. 符号检验（双侧为主，另附单侧）

| 粒度 | 正 | 负 | 零 | 双侧 p | 单侧(正) p |
| --- | --- | --- | --- | --- | --- |
| 54 格（分子×态） | 22 | 32 | 0 | 0.22 | 0.933 |
| 18 分子（氧化轴） | 10 | 8 | 0 | 0.815 | 0.407 |
| 18 分子（还原轴） | 9 | 9 | 0 | 1 | 0.593 |

## 5. 改变的格子（|delta| > 1e-3 eV）

| 分子 | 态 | delta(eV) | 所属轴 |
| --- | --- | --- | --- |
| TEGDME | anion | -0.156165 | reduction |
| TMP | cation | -0.134038 | oxidation |
| PC | anion | -0.118323 | reduction |
| EC | anion | 0.092274 | reduction |
| DEC | anion | -0.075211 | reduction |
| DEC | cation | 0.001381 | oxidation |

## 6. 哪些结论被改写 / 未被改写

**没有任何一条 published 结论被改写。**

**未被改写：**
- oxidation: f_robust_inv stays 0.0 (unchanged)
- oxidation: tau_b moves by 0.026 (<= 0.05, unchanged)
- oxidation: Top-k overlap_20 moves by 0.000 (<= 0.10, unchanged)
- oxidation: f_unresolved(after) moves by 0.000 (<= 0.05, unchanged)
- reduction: f_robust_inv stays 0.0 (unchanged)
- reduction: tau_b moves by 0.000 (<= 0.05, unchanged)
- reduction: Top-k overlap_20 moves by 0.000 (<= 0.10, unchanged)
- reduction: f_unresolved(after) moves by 0.033 (<= 0.05, unchanged)

**三个 scenario verdict 复核：**
- **B_large_shift_small_rank_damage**（原判：SUPPORTED）—— moread oxidation tau_b = 0.9215686274509803, O_20% = 0.75, f_robust_inv = 0.0 | 复核：still SUPPORTED (large shift, stable ranking, low f_robust_inv)
- **C_structured_robust_inversion**（原判：NOT OBSERVED）—— moread f_robust_inv = 0.0 / 0.0 (oxidation / reduction) | 复核：still NOT OBSERVED (both arms keep f_robust_inv at 0)
- **A_cheap_proxy_already_stable**（原判：NOT SUPPORTED）—— A rests on the P0->P2 rung; here only the P2 leg of P1->P2 is swapped. moread tau_b(P1,P2) oxidation = 0.9215686274509803 | 复核：the P1->P2 ordering barely moves, so A's P2-leg dependence is unaffected by the contamination

## 7. 上限声明（CI 是否吸收污染）

- **oxidation**：default CI = [0.714, 1.000]，moread CI = [0.774, 1.000]，重叠 = True
- **reduction**：default CI = [0.403, 0.873]，moread CI = [0.413, 0.871]，重叠 = True

CI 用法：Week 9 冻结设置（20 个 seed × 2000 次 paired bootstrap，取百分位上下界的 20 次中位数）。

## 8. 限制

- The default arm's P2 is derived independently from p2_core_set_smd_acetonitrile.csv; its max departure from the published value is 0.0 eV (expected 0).
- Only the P2 leg of the P1->P2 rung is swapped; P1 values, geometry, method layer and the other four rungs are untouched.
- With two realizations and z_primary = 1.0 the sigma estimator makes f_robust_inv structurally ~0, so a 0->non-0 flip is essentially impossible from this swap alone.
- A moread cell with status != ok makes layer_stability drop that molecule/axis, so n can fall below 18; this shows up in n and in cells_changed.
- The primary sign-test delta is the 54 (molecule, state) cells; the two 18-molecule axis deltas are reported alongside.
- The tau_b CI overlap test uses Week 9's tau_b_interval (20 seeds x 2000); --draws/--seed give a separate single-seed CI as a sensitivity column.
