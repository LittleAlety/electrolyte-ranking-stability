# figure_manifest_week14_stage15

| figure | sha256 | size |
| --- | --- | --- |
| `F28_two_guess_protocol.png` | `25366003f0434cc9f9c2ba688e44c8a9a5633256a7bc5121e1c1d28dfeb271d6` | 262529 B |
| `F29_diffuseness_descriptor.png` | `7eec8eff5cbc77a1d00c9d174f7acf41e33a7be65d43025afd94656acc6934d5` | 231568 B |

| input | sha256 |
| --- | --- |
| `outputs/week14/stage15_two_guess_analysis.json` | `338405bbbb774830e7b9b330f6c29be3ec376d18de162711035b50d278575417` |
| `outputs/week14/stage15_two_guess_energy.csv` | `db125a4a08dd2a0a8af0621373827efdb42bc1d66b3888b595cc777d0ee9de8f` |
| `outputs/week14/stage15_diffuseness.json` | `c2a758e0e8759ef08f073eb11e6f848ba041a331c8cf14067137b896097445cc` |
| `outputs/week14/stage15_diffuseness.csv` | `0a82d2c0848a8b75a02944400543e5a7fc413e9c1c04276c34a069970b2a810c` |

F28 panel (a): 78 of the 90 (molecule, state, dielectric) points give the same
energy to SCF convergence.  The magnitude histogram over thresholds is
1e-08: 90, 1e-07: 86, 1e-06: 72, 1e-05: 27, 1e-04: 16, 1e-03: 12, 1e-02: 7, 1e-01: 6, so the material threshold is set at 1e-03 eV: above it there are 12 points,
and *all* of them are negative (`E_moread - E_default < 0`), i.e. the default
guess settled on a state that is not the lowest one.  The remaining 0 points
where the restart would be worse is zero, and the worst value inside the noise
band is 8.3e-04 eV.  Biggest case of the default guess being too high: 0.2860 eV.
Affected: DMC, EC, EMC, states anion, cation.

F28 panel (b): the dipole moves with the energy, and it moves *between two
branches*.  EMC default-guess dipoles on the nine-point ladder span 4.65 D with
roughness 1.99; restarting from the gas-phase MOs collapses that to 1.54 D and
roughness 0.08.

F28 panel (c): the Born abscissa is `1 - 1/eps`, so the fitted slope *is* the
extrapolated eps -> infinity limit.  eps = 1000 has x = 0.999 and is the first
measured point that close to the limit.

F28 panel (d), numbers: default protocol, nine-point slope 2.6304 eV, eps = 200
2.5335 eV, eps = 1000 2.5449 eV (extrapolation error -0.0856 eV).  moread protocol,
nine-point slope 2.7778 eV, eps = 200 2.8157 eV, eps = 1000 2.8308 eV (extrapolation
error +0.0530 eV).

F28 reproduction of the Stage 14 numbers: six-point Born R2 0.8468, nine-point
Born R2 0.6788, sign changes 4.  Stage 14 published 0.8468 / 0.6788 / 4, so the
restart experiment is being compared against the same curve it is meant to fix.

F29 panel (e): the added electron's spread is measured from the `MULLIKEN ATOMIC
CHARGES AND SPIN POPULATIONS` block of the anion, averaged over the six bare-CPCM
layers.  The single-atom concentration predicts the reduction-axis penalty with
rho = +0.811 and leave-one-out R2 = 0.556, against 0.162 for the best Stage 14
descriptor (`mu_anion_smd_acn_debye`).

F29 panel (f): the inverse participation ratio has the stronger *rank* signal
(rho = -0.846) but is strongly non-linear -- a straight line through it has
leave-one-out R2 = -2.90.  Reporting only the rank statistic would have been
misleading, which is why both are shown.

F29 panel (g): leave-one-out R2 of the best descriptor per target.  D_neutral is
unchanged at 0.634 (its Stage 14 champion is still the best), D_cation stays at
0.071, and D_anion rises from 0.162 to 0.556.

F29 panel (h): the descriptor's own validity screen.  The spin populations are
normalised (worst `|sum s - 1|` = 3.0e-06 over 72 rows, worst `|sum q + 1|` = 3.0e-06).
Mulliken spin is signed, so `max |s_i| > 1` is a polarisation signature, not an
unbound anion.  One layer leaves its molecule's own median by more than 20%%:
EMC/cpcm_10 (sum |s| = 2.799).  That is the same layer the Part A energy screen flags, found here without
using any energy at all -- which is the cross-check that makes the diagnosis
credible rather than convenient.

The gas-phase anion was rejected as a source before any of this was computed:
for AN the gas-phase spin is outside the domain spanned by the six layers, so the
descriptor would have been extrapolating.

Palette and dpi follow the other week figures (dpi = 160, bbox_inches = tight).

`outputs/week14/stage15_summary.md` is the narrative companion of these figures.
