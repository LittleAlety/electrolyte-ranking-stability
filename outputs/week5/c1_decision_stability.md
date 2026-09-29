# Stage 5 / T4 -- C1 (Li+ coordinated) coordination shift

Reference ligand R = DME (frozen primary reference of config/scientific_definitions.yaml).
C0 = P1 at G2 (r2SCAN-3c, free molecule, fully optimised geometry, from T2).
C1 = r2SCAN-3c at the fully optimised [Li M]+ geometry, vertical.

## 1. C1 - C0 vertical shifts (primary motif m1)

dIP = IP(C1) - IP(C0), literally the frozen `dGdG_ox_coord`.
dEA = EA(C1) - EA(C0); the frozen `dGdG_red_coord` is its **negative**
(`config/scientific_definitions.yaml`: `dG_red = G(reduced) - G(oxidised)`),
so dEA must not be quoted under the `dGdG_red_coord` name.

The reduction *ranking* below is built on -EA (see `layer_stability` call),
which is the frozen S_red scale (`analyze_p1_core_set.py:253`).

| mol | dIP (C1-C0) eV | dIP kJ/mol | dEA (C1-C0) eV | dEA kJ/mol | dIP relaxed | dEA relaxed |
| --- | --- | --- | --- | --- | --- | --- |
| C04 EC | +4.321 | +416.896 | +6.155 | +593.869 | +3.858 | +6.209 |
| C01 DMC | +4.335 | +418.274 | +7.157 | +690.588 | +3.914 | +7.213 |
| C08 DME | +5.134 | +495.389 | +7.067 | +681.903 | +4.792 | +7.138 |
| C09 DOL | +6.156 | +593.927 | +8.061 | +777.768 | +3.058 | +8.146 |
| C13 GBL | +4.901 | +472.886 | +6.178 | +596.060 | +4.308 | +6.231 |
| C14 SL | +4.929 | +475.553 | +6.220 | +600.170 | n/a | +6.314 |
| C15 DMSO | +5.184 | +500.213 | +6.467 | +623.922 | +3.647 | +6.532 |
| C16 AN | +5.105 | +492.600 | +7.073 | +682.447 | +2.986 | +7.097 |
| C18 SN | +4.778 | +460.960 | +4.927 | +475.409 | +3.425 | +6.116 |
| C17 TMP | +4.029 | +388.768 | +6.477 | +624.889 | +3.372 | +6.575 |

Population statistics over the primary motifs:

- dIP: n=10, mean +4.887 eV, std 0.564 eV, range [+4.029, +6.156] eV
- dEA: n=10, mean +6.578 eV, std 0.790 eV, range [+4.927, +8.061] eV

## 2. Decision stability C0 vs C1 (same frozen metrics as week 4)

| axis | tau_b (95% CI) | O_10% | O_20% | O_30% | J_10% | J_20% | J_30% | f_unresolved(C0) | f_unresolved(C1) | f_robust_inv | f_robust_inv(z=1.96) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| oxidation | 0.689 [0.139, 1.000] | 1.000 | 1.000 | 0.667 | 1.000 | 1.000 | 0.500 | 0.178 | 0.200 | 0.0000 | 0.0000 |
| reduction | -0.467 [-0.950, 0.105] | 0.000 | 0.000 | 0.333 | 0.000 | 0.000 | 0.200 | 0.444 | 0.800 | 0.0000 | 0.0000 |

## 3. Ligand exchange dGdG_bind(M;R)

Energy level: dE_SCF (electronic, no ZPE / thermal correction; see
docs/08 section 4). The g_liM_cation_eh / g_lir_cation_eh columns are raw
G([LiM]+) / G([LiR]+) electronic energies, not binding energies, and are
not the dG_bind_abs that the config forbids as a core quantity.

| R | continuum | n | mean kJ/mol | std kJ/mol | min | max | self-exchange check |
| --- | --- | --- | --- | --- | --- | --- | --- |
| AN | gas | 10 | -28.04 | 31.57 | -82.48 | +30.24 | +0.000000 |
| AN | smd | 10 | -13.05 | 19.68 | -56.25 | +7.56 | +0.000000 |
| DME | gas | 10 | +54.44 | 31.57 | +0.00 | +112.72 | +0.000000 |
| DME | smd | 10 | +43.21 | 19.68 | +0.00 | +63.81 | +0.000000 |

## 4. Four single-variable steps on the same molecules

| step | n(dIP) | mean dIP eV | sigma(dIP) eV | n(dEA) | mean dEA eV | sigma(dEA) eV |
| --- | --- | --- | --- | --- | --- | --- |
| method | 10 | -1.299 | 0.745 | 7 | -8.384 | 1.155 |
| geometry | 10 | -0.012 | 0.048 | 10 | +0.125 | 0.082 |
| environment | 10 | -2.465 | 0.256 | 10 | +2.172 | 0.271 |
| coordination | 10 | +4.887 | 0.564 | 10 | +6.578 | 0.790 |

population spread (pstdev) of the per-molecule shift caused by ONE single-variable change, all on the same molecules: method = IP(P1@G1) - IP(P0@G1); geometry = IP(P1@G2) - IP(P1@G1); environment = IP(P2 SMD) - IP(P1@G1); coordination = IP(C1) - IP(C0@G2).

