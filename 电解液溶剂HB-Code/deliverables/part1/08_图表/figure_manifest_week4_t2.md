# Figure manifest - T2 Opt+Freq geometry sensitivity (F11)

| figure | file | figure SHA256 | inputs (SHA256) |
| --- | --- | --- | --- |
| F11 | `F11_opt_freq_g2_sensitivity.png` | 3ec30faa6508f1a73f42fb395f7d9a90a7ff4eb852f0b2a857cbf195be23d3fe | `t2_opt_freq_summary.json` eb383c6c1760cd04ae5d84807de660e518c032d16e65778051df88bca7f23b17 | `p1_core_set_derived.csv` 2987f8771b722d5a07517289a18a486fb2da24ed5775a196ffd7baf2c57517d3 | `t3_cpcm_eps_scan_summary.json` ce04777bf324683526183ef783177073cb70512f94d623b7bd559391706a28d4 |

F11 note: panel (a) is the per-molecule vertical shift produced by replacing the
shared G1 geometry (GFN2-xTB, the geometry P0 and P1 both use) with G2, the
r2SCAN-3c Opt+Freq stationary point, evaluated with r2SCAN-3c in the gas phase.
Positive dEA means the re-optimisation destabilises the anion. Panel (b) puts the
population standard deviation of that shift over the 12-molecule audit subset
next to the same statistic for two other perturbations. All three use one
estimator and one molecule set, so they answer the docs/08 section 3.4 question
directly: if the geometry term were comparable to the method term, the P0 -> P1
change could not be attributed to the electronic-structure method alone.

- n_molecules: 12, n_opt_jobs: 12, n_opt_ok: 12, n_failed: 0
- n_sp_jobs: 36, n_sp_ok: 12
- n_imaginary_unresolved: 2 (a real r2SCAN-3c result on G2, recorded, not suppressed)
- sigma_geom: dIP -0.002 (mean) / 0.049 (pop std) eV; dEA +0.118 / 0.076 eV
- sigma_method (same subset, P0 -> P1): dIP -1.373 / 0.700 eV; dEA -7.378 / 2.074 eV
- sigma_env (gas -> bare CPCM 40): dIP 0.229 eV; dEA 0.234 eV
- sigma_conf: not computed in this round (docs/08 section 5)
- generated_utc: 2026-09-29T06:27:41Z

## Geometry diagnostics (G1 -> G2 displacement)

G1 is the shared GFN2-xTB geometry (provenance outputs/_week3_scratch/<mol_id>/xtbopt.xyz);
G2 is the r2SCAN-3c Opt+Freq stationary point. RMSD is computed after optimal rigid-body
superposition (Kabsch), so a molecule that merely rotated does not look displaced.

| molecule | Kabsch RMSD (A) | max atom move (A) | dIP (eV) | dEA (eV) | imaginary mode |
| --- | --- | --- | --- | --- | --- |
| TMP | 0.1916 | 0.2998 | -0.0766 | +0.1741 | no |
| DME | 0.1710 | 0.2478 | +0.0335 | +0.1089 | no |
| PC | 0.1573 | 0.2334 | +0.0615 | +0.0761 | no |
| GBL | 0.0415 | 0.0540 | +0.0387 | +0.1194 | no |
| SL | 0.0384 | 0.0585 | -0.0579 | +0.1153 | no |
| SN | 0.0381 | 0.0539 | -0.0625 | +0.1349 | no |
| DOL | 0.0283 | 0.0399 | +0.0674 | +0.0594 | yes |
| DMSO | 0.0252 | 0.0355 | -0.0399 | +0.0366 | no |
| EMC | 0.0251 | 0.0312 | +0.0289 | +0.0868 | no |
| EC | 0.0148 | 0.0241 | +0.0120 | +0.1440 | yes |
| AN | 0.0145 | 0.0250 | -0.0493 | +0.0278 | no |
| DMC | 0.0108 | 0.0182 | +0.0168 | +0.3297 | no |

mean Kabsch RMSD = 0.0631 A (max 0.1916 A, TMP); correlation with the vertical shift over these 12 molecules: r(dIP) = +0.019, r(dEA) = +0.004. The displacement size therefore does NOT predict the size or sign of the geometry-induced shift.

Labels are English on purpose (no guaranteed CJK font in the workspace).
