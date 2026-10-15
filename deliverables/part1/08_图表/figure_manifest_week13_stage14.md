# figure_manifest_week13_stage14

| figure | sha256 | size |
| --- | --- | --- |
| `F26_distortion_attribution.png` | `53c0a18b6d650a49d77ccf6740e6c0559685b4d9a0f727433920ce0faef248f8` | 214402 B |
| `F27_emc_outlier.png` | `aedfbae12a72e01370bfdd7cc01d1d865331e3267b5bde6044122ae461d73cf8` | 287509 B |

| input | sha256 |
| --- | --- |
| `outputs/week13/stage14_attribution.json` | `0dfd93420527f8cce22da2e93ea0bb7c89dd24ca74625f89a9d5433f25e6c5ff` |
| `outputs/week13/stage14_distortion_states_by_molecule.csv` | `94f796d0dcd6e290ca3e65f3f41acfbdde26a6e9acc20b9a88171eb0db3c2550` |
| `outputs/week13/stage14_outlier.json` | `d7431b6c41f39a4fb80d71518a59b969fe2be0ba12855d3ecaee1bbae85cffbe` |
| `outputs/week13/stage14_outlier.csv` | `8801343115c4caab0fecbedb424bcf1f277b5038454f9a97d43deaf9140dec9a` |

F26 panel (a): D_X(t) = bare(X,t) - bare(X,gas) for the six bare-CPCM layers,
averaged per molecule.  Every one of the 216 molecule-state penalties is positive
(worst minimum +0.011 eV), which is the variational check: the solvent-adapted
density is not the bare-energy minimiser, so relaxing back cannot lower the energy.
The channel asymmetry of Stage 13 is a per-state fact: D_anion = 0.3710 eV against
D_neutral = 0.0685 eV and D_cation = 0.1120 eV.

F26 panel (b): the stored `dist_ev` is rebuilt from the state ledger alone for all
192 molecule-layer rows; the largest residual is 6.7e-12 eV.
The axis-visible distortion is therefore exactly D_hi - D_lo -- a *difference* of
two penalties, which is why it inherits none of the single-state correlations.

F26 panel (c): the only robust signal in the whole screen.  D_neutral tracks the
molecule's own gas-phase dipole with rho = +0.909 and leave-one-out R2 = 0.634.

F26 panel (d): best single descriptor per target, scored by leave-one-out R2.
Only the neutral penalty clears zero; nothing predicts the anion penalty, which is
the term that produces the 7x channel asymmetry, and nothing predicts either axis
observable.  The negative result is the point: the needed descriptor is the spatial
extent of the added electron, which no stored quantity measures.

F27 panels (e) and (f): all six curves on the nine-point ladder
eps = 5, 7, 10, 14, 20, 28, 40, 80, 200.

F27 panel (g): EMC/reduction on the nine-point ladder, with every marker coloured
by which SCF solution the EMC anion settled on, as revealed by its *dipole*
(~2.5 D vs ~6.6 D).  The energy and the dipole hop in phase, so the anomaly is
a solution-selection artefact of bare CPCM, not a breakdown of the Born form:
adding points makes the Born R2 *worse* (0.8468 at six points, 0.6788 at nine) and
increases the sign changes from 2 to 4, the opposite of under-sampling.

F27 panel (g), numbers: the EMC anion dipole takes 2.54/6.65/2.50 D across the ladder while
DMC and EC stay inside 0.09 D and 3.40 D of drift.  A screen over all twelve
audited molecules x three charge states (36 dipole ladders, no new electronic
structure) finds exactly one suspect: EMC/anion, roughness 1.99 against a smooth
population whose median is 0.235.

F27 panel (h): Born R2 against the number of grid points used, for all six curves.
Five of the six curves are flat in the number of points; only EMC/reduction falls

Reproducibility: the four shared points (eps = 5/10/20/40) were re-measured and
compared with the frozen Stage 13 numbers; 36 of 36 energies agree to all printed
digits, worst deviation 0.0e+00 Eh (0.0e+00 eV).  Verdict: reproduced.

Palette and dpi follow the other week figures (dpi = 160, bbox_inches = tight).

`outputs/week13/stage14_summary.md` is the narrative companion of these figures.
