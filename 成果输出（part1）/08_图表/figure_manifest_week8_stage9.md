# Figure manifest - Week 8 / Stage 9 (F18)

| figure | file | figure SHA256 | inputs (SHA256) |
| --- | --- | --- | --- |
| F18 | `F18_stage9_explicit_shell.png` | 8f3ac1ec91639cdfd1fd59be29d51942bba1f82b70608bb7206b013bfaa44d2d | `stage9_shell_shifts.csv` ce206cbd8c7ce81031b4f247c0c45d5ab24a0013ef49bfb35fae2da27c24e348 |

F18 panel (a,b): per-motif coordination shift dIP / dEA computed with a
1:1 first shell (Week 5) against the same quantity with a homoleptic 1:2
shell (this stage). Both are r2SCAN-3c vertical ionisation energies taken
at the optimised reference geometry of their own complex; the free-molecule
reference C0 is identical in the two columns. The dashed line is identity,
so a point off the diagonal is a shell-size effect on the coordination shift.

Panel (c): the rank each motif takes in dIP under the two shell sizes;
coloured lines cross when the shell size changes the ordering.

Panel (d): the frozen decision metrics of `layer_stability`
(`analyze_p1_core_set.py`) applied to shell 1:1 -> shell 1:2, for the
oxidation and reduction axes and for the all-12 and primary-m1 populations.
`f_unresolved(1:2)` is the unresolved-pair fraction of the 1:2 ranking, at
the preregistered z = 1.0.

`stage9_decision_stability.csv` SHA256 2ce2d1aff0090d87e5e339c7deca6604c2693f67fce45ed20c0ed9010039fa6d

