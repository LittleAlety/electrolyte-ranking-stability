# Stage 21 Part A -- frozen single-point profiles (week 20)

- method: `r2SCAN-3c`, 21 images per path, bare CPCM at the cell's own epsilon
- cells: 3, jobs: 63, all SCF converged: True
- thermal scale used for the `one_basin` verdict: 0.0257 eV (k_B T at 298 K); `separated` needs >= 0.0434 eV (1 kcal/mol)

| cell | RMSD(Stage 19) | Stage 19 | path length (A) | chord hump (eV) | hump/noise | G1 sp delta (eV) | relaxed delta (eV) | verdict | agrees |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| EC/cation/5 | 0.100 | distinct_lower | 0.3172 | 0.00424 | 31.7 | -0.01741 | -0.00972 | one_basin | NO |
| EC/cation/20 | 0.021 | same_higher | 0.0649 | 0.00001 | 44.0 | -0.00149 | +0.00004 | one_basin | yes |
| TEGDME/anion/20 | 2.214 | distinct_lower | 13.5359 | 66.14456 | 31.5 | -0.12052 | -0.06561 | separated | yes |

## Per-cell detail

### EC/cation/5 (cyclic_carbonate)
- Stage 19 relaxed the two arms to geometries 0.1000 A apart (RMSD) and called it `distinct_lower`.
- the straight line between them is 0.3172 A long.
- frozen single point on the *shared* G1 start geometry: -0.01741 eV; after both arms relax: -0.00972 eV, so relaxation changed the gap by +0.00769 eV.
- consistency check: the frozen single points at the two relaxed endpoints differ by -0.00972 eV, which must equal the relaxed difference -- MISMATCH.
- profile above the endpoint chord: max +0.00424 eV (31.7 x the SCF noise floor of 1.34e-04 eV); above the higher endpoint: max +0.00118 eV; monotone: False (1 turning points).
- harmonic stiffness fitted at each end: -0.041 / 0.920 eV/A^2.
- verdict: `one_basin`; Stage 19 **not** backed up.

### EC/cation/20 (cyclic_carbonate)
- Stage 19 relaxed the two arms to geometries 0.0210 A apart (RMSD) and called it `same_higher`.
- the straight line between them is 0.0649 A long.
- frozen single point on the *shared* G1 start geometry: -0.00149 eV; after both arms relax: +0.00004 eV, so relaxation changed the gap by +0.00153 eV.
- consistency check: the frozen single points at the two relaxed endpoints differ by +0.00004 eV, which must equal the relaxed difference -- MISMATCH.
- profile above the endpoint chord: max +0.00001 eV (44.0 x the SCF noise floor of 1.81e-07 eV); above the higher endpoint: max +0.00000 eV; monotone: True (0 turning points).
- harmonic stiffness fitted at each end: 0.003 / 0.029 eV/A^2.
- verdict: `one_basin`; Stage 19 backed up.

### TEGDME/anion/20 (ether)
- Stage 19 relaxed the two arms to geometries 2.2140 A apart (RMSD) and called it `distinct_lower`.
- the straight line between them is 13.5359 A long.
- frozen single point on the *shared* G1 start geometry: -0.12052 eV; after both arms relax: -0.06561 eV, so relaxation changed the gap by +0.05490 eV.
- consistency check: the frozen single points at the two relaxed endpoints differ by -0.06562 eV, which must equal the relaxed difference -- MISMATCH.
- profile above the endpoint chord: max +66.14456 eV (31.5 x the SCF noise floor of 2.10e+00 eV); above the higher endpoint: max +66.11175 eV; monotone: False (1 turning points).
- harmonic stiffness fitted at each end: 4.742 / 4.728 eV/A^2.
- verdict: `separated`; Stage 19 backed up.

## What this does and does not prove

The path is a straight Cartesian line, not a minimum-energy path, so a hump on it is only an upper bound to the true barrier and this stage never claims otherwise. The asymmetry is the point: a barrier-free straight line is *strong* evidence that the two endpoints sit in one basin, because a line that never rises cannot be hiding a barrier. A hump, by contrast, is weak evidence of separation and is read here only together with the relaxed energy gap and the harmonic stiffness at each end.

