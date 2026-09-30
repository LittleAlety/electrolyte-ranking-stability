# figure_manifest_week17_stage18

| figure | sha256 | size |
| --- | --- | --- |
| `F34_stage18_identity_census.png` | `eb73cfdef38ad4a67599c4769420bae3d31a111786b6a9e62f6e2149e4bbe13f` | 182593 B |
| `F35_stage18_selfdiagnosis.png` | `ca116d15649a278a56fa46cdeae71de1f0d94d204ed1427107e2aeeb5fab9f6e` | 245682 B |

| input | sha256 |
| --- | --- |
| `outputs/week17/stage18_identity_census.json` | `3e89f63b86b51af383c12e4f242e28a93ad8457ecdbeb698e9b8fb5f3b8856b7` |
| `outputs/week17/stage18_identity_census.csv` | `a6dab39a0f98b9995bdb2bdf42913432af14fb33531464a808df8d3b2b2ceaf3` |
| `outputs/week17/stage18_selfdiagnosis.json` | `12fb287b17a6aca867751b8da02608d23cffe33d209f83d8a3c3007a3bbe6734` |
| `outputs/week17/stage18_selfdiagnosis_features.csv` | `5ce76e14b9dcf29db66aa861b5d2a8211c9a05771b382d2bd72a820fb7c5e8ee` |

Generate (from the repository root):

```powershell
& $py scripts\make_stage18_figure.py
& $py scripts\make_stage18_figure.py --check
```

## F34 -- `F34_stage18_identity_census.png`

One-line caption (verbatim, for the terminal site): (a) charge_l1 双峰：coincident 239 / moread_lower 37（仅开壳层可测），冻结阈值 0.039 落在 0.0385-0.0394 空档；(b) 五通道 x 三臂 AUC；(c) 按家族的重合率；(d) 留出臂 54 格 delta_ev 与 1 meV 阈值

### (a) the primary identity channel

`charge_l1` of the 276 measurable open-shell pairs: coincident (n = 239) against moread_lower (n = 37).  The frozen threshold 0.039 sits in the empty calibration band [0.038509, 0.039383] read off the discovery arm only; tp/fn/fp/tn = 37/0/0/239 and AUC = 1.000000 on the whole directory.

### (b) separation per channel and arm

- all (n+ = 37): charge_l1 1.000000, spin_l1 0.999661, spin_max_moread 0.770234, loss_in_pr 0.379095, delta_s2 0.275133
- discovery (n+ = 32): charge_l1 1.000000, spin_l1 0.999549, spin_max_moread 0.745236, loss_in_pr 0.344703, delta_s2 0.315655
- holdout (n+ = 5): charge_l1 1.000000, spin_l1 1.000000, spin_max_moread 0.930612, loss_in_pr 0.600000, delta_s2 0.006452

### (c) per family

- cyclic_carbonate (n = 78): coincident 63, moread_lower 15, mean charge_l1 0.197125
- ester (n = 48): coincident 48, moread_lower 0, mean charge_l1 0.002450
- ether (n = 69): coincident 67, moread_lower 2, mean charge_l1 0.179600
- linear_carbonate (n = 69): coincident 59, moread_lower 10, mean charge_l1 0.513163
- nitrile (n = 60): coincident 60, moread_lower 0, mean charge_l1 0.001434
- phosphate (n = 30): coincident 20, moread_lower 10, mean charge_l1 0.165695
- sulfone (n = 30): coincident 30, moread_lower 0, mean charge_l1 0.002417
- sulfoxide (n = 30): coincident 30, moread_lower 0, mean charge_l1 0.001424

### (d) held-out arm

- classification: coincident 49, moread_lower 5; misses on DEC (3), TEGDME (2); identity AUC 1.000000 with tp/fn/fp/tn = 5/0/0/31
- energy cross-check over 414 pairs: max|delta| = 0.0e+00 eV (tolerance 1e-09); geometry identical 414/414

## F35 -- `F35_stage18_selfdiagnosis.png`

One-line caption (verbatim, for the terminal site): (e) 单变量筛查前 8 名 |AUC-0.5| 与 LOO 裁决（gap_warn_value 第一、LOO 胜基线但留出臂输）；(f) gap_warn_value 正负例分布与冻结阈值 -0.0395；(g) 留出臂 54 格按冻结规则逐行打分（TP=0）；(h) 单边筛查：presence 规则放行 140/414、敏感度 1.000、特异度 0.371

### (e) the single-variable screen

- 1. `gap_warn_value`: AUC 0.084032, |AUC-0.5| 0.4160, threshold -0.0395, LOO 0.9167 vs majority 0.9111 (beats), holdout 0.7963
- 2. `spin_n90`: AUC 0.814596, |AUC-0.5| 0.3146, threshold 8.5, LOO 0.9389 vs majority 0.9111 (beats), holdout 0.8333
- 3. `loewdin_spin_n90`: AUC 0.809070, |AUC-0.5| 0.3091, threshold 8.5, LOO 0.9389 vs majority 0.9111 (beats), holdout 0.7778
- 4. `scf_last_abs_de`: AUC 0.785823, |AUC-0.5| 0.2858, threshold 0.0002044945, LOO 0.9083 vs majority 0.9111 (loses), holdout 0.9074
- 5. `loewdin_spin_pr`: AUC 0.780393, |AUC-0.5| 0.2804, threshold 7.290672808545057, LOO 0.9056 vs majority 0.9111 (loses), holdout 0.8333
- 6. `spin_pr`: AUC 0.755335, |AUC-0.5| 0.2553, threshold 6.6300712641493575, LOO 0.9278 vs majority 0.9111 (beats), holdout 0.7778
- 7. `orbital_abs`: AUC 0.717893, |AUC-0.5| 0.2179, threshold 1.1063395, LOO 0.9194 vs majority 0.9111 (beats), holdout 0.9444
- 8. `gap_warn_present`: AUC 0.685976, |AUC-0.5| 0.1860, threshold 0.5, LOO 0.4278 vs majority 0.9111 (loses), holdout 0.4259

### (f) the frozen descriptor

- `gap_warn_value` smaller_is_riskier `-0.0395`; in-sample accuracy 0.9167, LOO 0.9167, exact p = 2.561e-19
- positives span [-0.047, -0.013] Eh (all negative: True); negatives that did carry the warning span [-0.069, +0.047] Eh, which brackets the positive range.

### (g) the held-out arm

- accuracy 0.7963 against majority 0.9074; TP=0 FP=6 TN=43 FN=5, i.e. the frozen rule flags no true positive at all.

### (h) the one-sided screen

- presence rule, pooled: sensitivity 1.0000, specificity 0.3714, precision 0.1350 (it flags 274 of 414 rows).
- necessary condition: 37/37 positives carry the warning (counterexamples 0); discovery 32/32, holdout 5/5.
- screening yield: clearing the silent rows releases 140 of 414 cells and loses 0 positives; the false-alarm rate of the warning on negatives is 0.6286.
- per-epsilon sensitivity of the presence rule: eps 5.0 6/6, eps 7.0 3/3, eps 10.0 3/3, eps 14.0 3/3, eps 20.0 6/6, eps 28.0 2/2, eps 40.0 3/3, eps 80.0 3/3, eps 200.0 5/5, eps 1000.0 3/3

Palette and dpi follow the other week figures (dpi = 170, bbox_inches = tight). All labels are ASCII because the workspace has no guaranteed CJK font.
