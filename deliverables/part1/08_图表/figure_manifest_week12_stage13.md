# figure_manifest_week12_stage13

| figure | sha256 | size |
| --- | --- | --- |
| `F24_dielectric_limit.png` | `7c060a238c426105940f1a12b21882ed6cd57ac65c53b13d1cba3a209bea3a47` | 377022 B |
| `F25_environment_ledger.png` | `268b5825d9fca4d1c94add5ed7ec413794675c1999a13626f9ac5149642724f8` | 237962 B |

| input | sha256 |
| --- | --- |
| `outputs/week12/stage13_analysis.json` | `0fadd2908135f76ab2b77348380544c7f5de34c4115f4c14e630fd61c9c479b8` |
| `outputs/week12/stage13_shift_split.csv` | `19ab07535bd39091e0d96881780387296f05d927a3cae31bdffaeec9e177bb36` |
| `outputs/week12/stage13_state_ledger.csv` | `eff3d25c3816a16ca70e4b8d1a9537b00815e43a793c23c944b1c684bd1549d5` |
| `outputs/week12/stage13_rungs.csv` | `a3e73cfb6ee73427cf593acc09d98d0c69e5994cf0e8b0fd4450fe66e64db1c8` |

F24 panel (a): the seven bare levels (gas, eps = 5/10/20/40/80/200) plotted
against u = 1 - 1/eps.  All 24 curves pass through the origin, which is what
makes the through-origin Born fit the right comparison.

F24 panel (b): mean R2 = 0.9861 (Born), 0.8779 (Onsager), 0.9935 (two-parameter).
The two-parameter family's own best fit returns k = 0.0779 +/- 0.1004, i.e. Born.

F24 panel (c): the error of a forecast made from eps <= 20 grows in proportion
to how far the fit had to reach (max error 0.0637 / 0.0763 / 0.0841 eV at eps = 40 / 80 / 200).

F24 panel (d): the measured eps = 200 shift sits within 33 meV of the fitted
eps -> infinity limit, so nothing beyond eps = 200 can move these numbers.

F25 panels (a) and (b): one self-consistent SMD calculation per state already
contains the split -- the CPCM dielectric term points down, the solute
distortion term points back up, and the diamond (the measured total) is their sum.

F25 panel (c): the SMD CDS term is identical for neutral, cation and anion
(24 molecule-layer groups, spread 0.0e+00 eV), so it cancels in every vertical IP/EA.

F25 panel (d): the cancellation fraction is a property of the axis, not of the
molecule: the reduction axis loses much more of its dielectric shift to distortion.

Palette and dpi follow the other week figures (warm/cool pair for the
oxidation/reduction axes, dpi = 160, bbox_inches = tight).

`outputs/week12/stage13_summary.md` is the narrative companion of these figures.
