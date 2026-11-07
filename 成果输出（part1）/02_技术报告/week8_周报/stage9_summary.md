# Stage 9 / T10 -- explicit first-shell microsolvation validation

C1(1:1) = r2SCAN-3c vertical IP/EA of [Li M]+ (Week 5, `outputs/week5/c1_coord_shifts.csv`).
C1(1:2) = the same quantity for the homoleptic [Li(M)2]+ shell built here.
C0 = free molecule, r2SCAN-3c at G2 (identical in both columns).

## 1. Coordination shift (eV), mean +/- std

| quantity | n | mean | std | min | max |
| --- | --- | --- | --- | --- | --- |
| dIP 1:1 | 12 | 4.839 | 0.541 | 4.029 | 6.156 |
| dIP 1:2 | 12 | 3.171 | 0.499 | 2.558 | 4.569 |
| dEA 1:1 | 12 | 6.615 | 0.738 | 4.927 | 8.061 |
| dEA 1:2 | 12 | 5.410 | 0.544 | 4.537 | 6.613 |

## 2. Decision stability: shell 1 -> shell 2

| axis | population | n | tau_b (95% CI) | O_10% | O_20% | O_30% | f_unresolved(1:1) | f_unresolved(1:2) | f_robust_inv |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| oxidation | all12 | 12 | 0.697 [0.400, 0.963] | 1.000 | 0.500 | 0.750 | 0.167 | 0.273 | 0.000 |
| oxidation | primary_m1 | 10 | 0.778 [0.432, 1.000] | 1.000 | 0.500 | 1.000 | 0.133 | 0.267 | 0.000 |
| reduction | all12 | 12 | 0.848 [0.548, 1.000] | 1.000 | 0.500 | 1.000 | 0.152 | 0.152 | 0.000 |
| reduction | primary_m1 | 10 | 0.911 [0.610, 1.000] | 1.000 | 1.000 | 1.000 | 0.133 | 0.156 | 0.000 |

## 3. Per-motif table

| mol | motif | dIP 1:1 | dIP 1:2 | dEA 1:1 | dEA 1:2 |
| --- | --- | --- | --- | --- | --- |
| C04 EC | m1 | 4.321 | 2.558 | 6.155 | 4.686 |
| C01 DMC | m2 | 4.916 | 3.342 | 7.126 | 5.896 |
| C01 DMC | m1 | 4.335 | 2.845 | 7.157 | 5.885 |
| C08 DME | m1 | 5.134 | 3.572 | 7.067 | 5.565 |
| C09 DOL | m1 | 6.156 | 4.569 | 8.061 | 6.613 |
| C13 GBL | m1 | 4.901 | 3.170 | 6.178 | 5.155 |
| C14 SL | m1 | 4.929 | 2.918 | 6.220 | 5.258 |
| C15 DMSO | m1 | 5.184 | 3.277 | 6.466 | 5.164 |
| C16 AN | m1 | 5.105 | 3.210 | 7.073 | 5.737 |
| C18 SN | m1 | 4.778 | 2.873 | 4.927 | 4.537 |
| C17 TMP | m2 | 4.285 | 2.834 | 6.469 | 5.228 |
| C17 TMP | m1 | 4.029 | 2.882 | 6.477 | 5.195 |
