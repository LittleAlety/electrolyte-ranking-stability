# Figure manifest - Stage 5 / T4 C1 Li+ coordination (F12)

| figure | file | figure SHA256 | inputs (SHA256) |
| --- | --- | --- | --- |
| F12 | `F12_li_coordination_c1.png` | a8e750e5e758109378230ccb679ea937575be07c478a2c14814ee2ba35bb5473 | `c1_summary.json` 0fe14aa91e1cdd6aeb1860a6d590ab4b169d78a68c5ba27ba024a3bef58da530 | `c1_coord_shifts.csv` 1f9597ba376ffb19610e855e4d83a4e2360a8ac5009209cf764be91008634b5d |
| | | | `c1_ligand_exchange.csv` 6fbb385a5416044ac910c2d05c32ccffa588b174a6955babe4db3ba263c56a6b | `c1_decision_stability.json` da9df806884640d4ac23a9b074b858d306bfeee216ff516c0d526571b56993cb |
| | | | `c1_li_coordination.csv` 33e1192b2b12e4dbbe1094618b5edc9a99365b813b676b9d807c5228e884b431 | `li_motif_generation.json` 5a87805098a2cf4e884e9a79537e0a2a1ad227ea3ed45207258e92f29ea3de2f |

F12 note: C0 is the free molecule at its r2SCAN-3c geometry (T2, P1 at G2);
C1 is r2SCAN-3c at the optimised [Li M]+ geometry of the same molecule. Both
are vertical, so the difference isolates the chemical state, not the method,
the geometry basis or the continuum. Panel (b) places the coordination
dispersion next to the three terms week 4 measured using one estimator and one
molecule list; the usable n can differ per step and is printed on each bar. The
coordination step uses a different reference state (neutral C0 vs the [Li M]+
cation, docs/12_week5_report.md sections 2.6 and 7), so only the dispersion
scale is comparable and the four bars are not an additive decomposition.

- n_molecules: 10; molecules: EC, DMC, DME, DOL, GBL, SL, DMSO, AN, SN, TMP
- n_motifs (all, incl. secondary): 12
- dIP(C1-C0): mean +4.887 eV, pop std 0.564 eV
- dEA(C1-C0): mean +6.578 eV, pop std 0.790 eV
- sigma(method) dIP 0.745 eV / dEA 1.155 eV (n 10 / 7)
- sigma(geometry) dIP 0.048 eV / dEA 0.082 eV (n 10 / 10)
- sigma(environment, SMD AN) dIP 0.256 eV / dEA 0.271 eV (n 10 / 10)
- sigma(coordination) dIP 0.564 eV / dEA 0.790 eV (n 10 / 10)
- decision C0 vs C1: tau_b(ox) 0.6888888888888889, tau_b(red) -0.4666666666666667
- f_robust_inv: ox 0.0, red 0.0

population spread (pstdev) of the per-molecule shift caused by ONE single-variable change, all on the same molecules: method = IP(P1@G1) - IP(P0@G1); geometry = IP(P1@G2) - IP(P1@G1); environment = IP(P2 SMD) - IP(P1@G1); coordination = IP(C1) - IP(C0@G2).

Labels are English on purpose (no guaranteed CJK font in the workspace).
