# Figure manifest - Week 11 / Stage 12 (F22, F23)

| figure | file | figure SHA256 | inputs (SHA256) |
| --- | --- | --- | --- |
| F22 | `F22_dielectric_scaling.png` | 43058408d59a8ca218d1045341950e75e4d003dabe9a75a9dda7e086a2c8065f | `stage12_prescreen.json` 0502c3d1106ec8a3ca166bc1fd85cf21a709e071c616d0e4ae54d9b22de6b706 |
| F23 | `F23_prescreening.png` | 8f04adc076a0318413c6c50ec897e984c141c4da9506980401beab722cdb7c19 | `stage12_prescreen.csv` edf852744797ae552128f08dd9cba5546631a8826f18eeb8ea15a1c2008fdcfe |

Common-10 subset only.  F22 uses the four bare-CPCM dielectric rungs
(plus the gas limit as eps = 1); F23 uses all 18 (rung, axis) points.

F22 panel (a): delta(eps) = p(gas) - p(eps) against u = 1 - 1/eps, four
points per molecule and axis.  If the response is Born every four-point
series is a straight line through the origin.  Mean R2 = 0.993624 for Born
against 0.883528 for the Onsager reaction field (eps-1)/(2eps+1).

F22 panel (b): the measured increment ratios.  Doubling eps must halve
the increment; measured r2 = 1.9755 and r3 = 1.9867 against the Born
prediction of 2.0000 for both.  Onsager predicts 1.8636 and 1.9286.

F22 panel (c): abs(mean), sd(delta) and abs(b) of the four dielectric
rungs on one log axis.  All three collapse onto the same geometric
sequence, whose ratio is exactly c = u(hi) - u(lo) (grey line).  This
is the whole content of the one-parameter statement: the ladder is a
single vector times a known scalar, so the SIGN of b cannot change.

F22 panel (d): delta(eps=40) forecast from the cheap end only.  The
three-level fit (gas, eps=5, 10, 20) reaches 2.4% maximum relative
error; the two-level fit (gas and eps=5 only) reaches 4.6%.
No eps=40 datum enters either fit.

F23 panel (a): the pilot budget.  A single random pilot of k molecules
reaches AUC 0.853 at k = 3 and 0.946 at k = 5; averaging b_hat over all
pilots of that size reaches 1.000 already at k = 3.  The worst pilot
only catches every dangerous rung at k = 8.

F23 panel (b): b_hat across all pilots of size 5, per rung, sorted by
the full-sample slope.  Red rungs are the three whose shortlist is
actually rewritten; the pilot lands on the correct side of zero for
all of them, and the p05..p95 width shrinks as |b| grows.

F23 panel (c): one dot per 3-molecule pilot, b_hat against the value
obtained from all ten molecules.  The SIGN is stable over the whole
plane; the magnitude is compressed towards zero.

F23 panel (d): the same 18 points in the plane the decision rule
actually uses.  The rule flags a rung when b < 0 or q_median exceeds
sqrt(2)/z; the three rewritten rungs are the stars.

Palette and dpi follow the other week figures (warm/cool pair for the
oxidation/reduction axes, dpi = 160, bbox_inches = tight).

`stage12_summary.md` is the narrative companion of these figures.
