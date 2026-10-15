# Figure manifest - Week 9 / Stage 10 (F19)

| figure | file | figure SHA256 | inputs (SHA256) |
| --- | --- | --- | --- |
| F19 | `F19_stage10_ladder.png` | a85c9c9c43bfa95a54f52d15b3d75074ee5f785b319822e23d4d0eab4b07098b | `stage10_ladder.csv` c4cdec417373fcd6dfb63221bc4d7a727c65a563c4923e5a433b0048bbb9ea6e |

Common-10 subset only: the ten molecules (DMC, EC, DME, DOL, GBL, SL,
DMSO, AN, TMP, SN) that have a valid entry at every one of the five rungs.
The rung-4 / rung-5 rows use the primary m1 motif as the molecule-level
representative, so `n = 10` is comparable across panels.

Panel (a): tau_b of each rung and axis, rungs ordered by increasing shift
std (the mean of the two axes). Reading down the list is reading the
increasing order of the independent variable of (b).

Panel (b): the H_var evidence. Spearman rho(shift std, tau_b) = -0.851.
Panel (c): the H_mean control. Spearman rho(abs(shift mean), tau_b) = -0.535;
the rung with the largest mean shift (P0->P1 reduction, +7.06 eV) is *not*
the rung with the worst tau_b in the same direction, but the rung with the
largest spread is. The two variables are themselves correlated on this
small panel, so (c) is a control, not a rival model.

Panel (d): Spearman rho(shift std, f_unresolved_after) = +0.894.
This is the mechanistic link: a wide shift spread widens the method-
disagreement matrix sigma_ij, which is what `f_unresolved` counts. Note
that `f_robust_inv = 0` on every one of these ten points is therefore NOT
evidence that the ranking is stable -- see the report, section on reading
discipline.

Palette and dpi follow the other week figures (OKABE-ITO-like warm/cool
pair for the oxidation/reduction axes, dpi = 160, bbox_inches = tight).

`stage10_summary.md` is the narrative companion of this figure.

