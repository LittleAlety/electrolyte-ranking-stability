# Stage 21 Part C -- the 1:2 solvent shell under relaxation (week 20)

- method: `r2SCAN-3c` `Opt`, gas phase (matching Stage 9's protocol: no CPCM block), starting from the frozen `_shell2_G2Li2.xyz` frame
- jobs: 24, ok: 24, usable (one intact frame + Li keeps both ligands): 24
- excluded: none

## Per shell

| shell | axis | frozen shift (eV) | relaxed shift (eV) | relaxation correction (eV) | shift vs bare, frozen (eV) | shift vs bare, relaxed (eV) | usable | QC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AN_m1 | oxidized | 15.301 | 15.079 | -0.222 | 3.210 | 2.988 | yes |  |
| AN_m1 | reduced | 2.568 | -3.079 | -5.647 | 5.737 | 0.090 | yes |  |
| DMC_m1 | oxidized | 13.441 | 13.314 | -0.127 | 2.845 | 2.718 | yes |  |
| DMC_m1 | reduced | 2.750 | -2.809 | -5.559 | 5.885 | 0.326 | yes |  |
| DMC_m2 | oxidized | 13.938 | 13.639 | -0.300 | 3.342 | 3.042 | yes |  |
| DMC_m2 | reduced | 2.762 | -3.288 | -6.049 | 5.896 | -0.153 | yes |  |
| DME_m1 | oxidized | 12.462 | 12.162 | -0.300 | 3.572 | 3.272 | yes |  |
| DME_m1 | reduced | 1.945 | -2.135 | -4.080 | 5.565 | 1.485 | yes |  |
| DMSO_m1 | oxidized | 12.051 | 11.821 | -0.230 | 3.277 | 3.046 | yes |  |
| DMSO_m1 | reduced | 2.421 | -2.903 | -5.323 | 5.164 | -0.160 | yes |  |
| DOL_m1 | oxidized | 13.949 | 12.303 | -1.647 | 4.569 | 2.922 | yes |  |
| DOL_m1 | reduced | 2.586 | -3.420 | -6.005 | 6.613 | 0.608 | yes |  |
| EC_m1 | oxidized | 13.339 | 13.124 | -0.215 | 2.558 | 2.343 | yes |  |
| EC_m1 | reduced | 2.240 | -2.806 | -5.046 | 4.686 | -0.359 | yes |  |
| GBL_m1 | oxidized | 13.160 | 12.982 | -0.178 | 3.170 | 2.992 | yes |  |
| GBL_m1 | reduced | 2.695 | -3.039 | -5.734 | 5.155 | -0.579 | yes |  |
| SL_m1 | oxidized | 12.653 | 12.307 | -0.345 | 2.918 | 2.572 | yes |  |
| SL_m1 | reduced | 2.396 | -2.591 | -4.987 | 5.258 | 0.271 | yes |  |
| SN_m1 | oxidized | 14.414 | 14.188 | -0.226 | 2.873 | 2.647 | yes |  |
| SN_m1 | reduced | 2.818 | -3.772 | -6.590 | 4.537 | -2.052 | yes |  |
| TMP_m1 | oxidized | 12.862 | 12.046 | -0.816 | 2.882 | 2.066 | yes |  |
| TMP_m1 | reduced | 2.456 | -2.725 | -5.181 | 5.195 | 0.014 | yes |  |
| TMP_m2 | oxidized | 12.814 | 12.558 | -0.256 | 2.834 | 2.577 | yes |  |
| TMP_m2 | reduced | 2.489 | -2.724 | -5.212 | 5.228 | 0.015 | yes |  |

## Axis summaries

### oxidation
- usable shells: 12 (excluded: 0)
- frozen shift: 13.3655 +- 0.8744 eV; relaxed shift: 12.9602 +- 0.9311 eV; spread change +0.0566 eV
- relaxation correction: mean -0.4053 eV, std 0.4102 eV, largest |correction| 1.6467 eV; positive (relaxation *increases* the shift) in 0 of 12 shells
- ranking frozen vs relaxed: Spearman rho = 0.797, Kendall tau-b = 0.727; top quartile overlap = 0.500
- rank changes: DMC/m1: 5 -> 4, DMC/m2: 4 -> 3, DME/m1: 11 -> 10, DOL/m1: 3 -> 9, EC/m1: 6 -> 5, GBL/m1: 7 -> 6, SL/m1: 10 -> 8, TMP/m1: 8 -> 11, TMP/m2: 9 -> 7

### reduction
- usable shells: 12 (excluded: 0)
- frozen shift: 2.5104 +- 0.2373 eV; relaxed shift: -2.9408 +- 0.4053 eV; spread change +0.1680 eV
- relaxation correction: mean -5.4512 eV, std 0.6121 eV, largest |correction| 6.5899 eV; positive (relaxation *increases* the shift) in 0 of 12 shells
- ranking frozen vs relaxed: Spearman rho = -0.790, Kendall tau-b = -0.606; top quartile overlap = 0.000
- rank changes: AN/m1: 6 -> 9, DMC/m1: 3 -> 6, DMC/m2: 2 -> 10, DME/m1: 12 -> 1, DMSO/m1: 9 -> 7, DOL/m1: 5 -> 11, EC/m1: 11 -> 5, GBL/m1: 4 -> 8, SL/m1: 10 -> 2, SN/m1: 1 -> 12, TMP/m1: 8 -> 4, TMP/m2: 7 -> 3

## Reading

A positive relaxation correction means the relaxed shift is *larger* than the vertical one, which is the opposite of the naive expectation that relaxing a charged state can only lower it: the correction here is the difference of two separate relaxations (charged state minus the ``+1`` reference), not the relaxation energy of one state.

The reduction axis is the one at risk: the reduced complex is a neutral radical and the extra electron can leave with one ligand. Every shell whose relaxed frame broke a bond, fragmented, or lost a ligand is excluded from the summaries above and listed under ``excluded``.

