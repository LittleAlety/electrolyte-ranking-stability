# figure_manifest_week18_stage19

| figure | sha256 | size |
| --- | --- | --- |
| `F36_stage19_relax_outcomes.png` | `0f46a89086d892ed04cc2133635b34557786e2ab9ac126cfb34efcd4d1ee4ca2` | 238283 B |
| `F37_stage19_identity_geometry.png` | `904c5f1e0f1826a2c2cec5756f5080f71d5caf1a97017419b7b86d30d637507a` | 250243 B |

| input | sha256 |
| --- | --- |
| `outputs/week18/stage19_relax_analysis.json` | `90757ca1169e0e1136f58f0395a19298a91379049a0ab7cfd0f5f7f2a099b198` |
| `outputs/week18/stage19_relax_cells_analysis.csv` | `7e1333d553ebb72fe98049b094f61fcd93d9f66f79aa6872dff350f050ef79aa` |

Generate (from the repository root):

```powershell
& $py scripts\make_stage19_figure.py
& $py scripts\make_stage19_figure.py --check
```

The PNGs carry no timestamp, so re-running on the same inputs gives byte-identical files and ``--check`` compares SHA256 directly.

## denominators

- Every count and proportion on these two figures is conditional on the 37 `moread_lower` cells -- the complete set of cells whose two single-point SCF solutions differ *and* favour moread -- never on the 414-cell directory.
- Read `x/37` as "given that a single point produced a metastable pair that was lower, does it survive relaxation?", which is a well-defined conditional probability on that definition set.  It is not a population incidence, and this stage makes no statement of the form "the default solution is safe in N% of cells".

## F36 -- `F36_stage19_relax_outcomes.png`

One-line caption (verbatim, for the terminal site): (a) 单点 Δ 对弛豫后 Δ（按结局着色，y=x 与 ±1 meV 带；|Δ| 中位数 0.1198 → 0.00196 eV，缩小 61 倍）；(b) 37 个 moread_lower 格子的裁决：distinct_lower 5 / distinct_higher 24 / same_lower 0 / same_higher 8（已完成 37）；(c) 按 ε 的结局堆叠；(d) 按态与分子的分解

### (a) per cell: before vs after relaxation

The single-point separation of the two SCF solutions against the same separation after both arms were relaxed (y = x dotted, +/- 1e-03 eV material band shaded).  A point above the band is a cell where the relaxation has *reversed* the single-point preference.

- cells whose single-point preference was reversed by the relaxation: 32 of 37 (DEC anion eps=5, DEC anion eps=20, DEC anion eps=200, DMC cation eps=5, EC cation eps=14, EC cation eps=20, EMC anion eps=5, EMC anion eps=20, EMC anion eps=40, EMC anion eps=80, EMC anion eps=200, EMC anion eps=1000, PC anion eps=5, PC anion eps=7, PC anion eps=10, PC anion eps=14, PC anion eps=20, PC anion eps=28, PC anion eps=40, PC anion eps=80, PC anion eps=200, PC anion eps=1000, TMP cation eps=5, TMP cation eps=7, TMP cation eps=10, TMP cation eps=14, TMP cation eps=20, TMP cation eps=28, TMP cation eps=40, TMP cation eps=80, TMP cation eps=200, TMP cation eps=1000)
- separation after relaxation grew in 37 and shrank in 0 of the 37 complete cells

### (b) the verdict over the 37 moread_lower cells

- distinct_lower 5, distinct_higher 24, same_lower 0, same_higher 8, not finished 0
- still electronically distinct after relaxation: 29 of 37 complete cells (`charge_l1 > 0.039`); still carrying the lower moread energy: 5

### (c) per dielectric constant

- eps 5 (n = 6, complete 6): distinct_lower 1, distinct_higher 3, same_lower 0, same_higher 2, not finished 0
- eps 7 (n = 3, complete 3): distinct_lower 1, distinct_higher 2, same_lower 0, same_higher 0, not finished 0
- eps 10 (n = 3, complete 3): distinct_lower 1, distinct_higher 2, same_lower 0, same_higher 0, not finished 0
- eps 14 (n = 3, complete 3): distinct_lower 0, distinct_higher 2, same_lower 0, same_higher 1, not finished 0
- eps 20 (n = 6, complete 6): distinct_lower 1, distinct_higher 4, same_lower 0, same_higher 1, not finished 0
- eps 28 (n = 2, complete 2): distinct_lower 0, distinct_higher 2, same_lower 0, same_higher 0, not finished 0
- eps 40 (n = 3, complete 3): distinct_lower 0, distinct_higher 2, same_lower 0, same_higher 1, not finished 0
- eps 80 (n = 3, complete 3): distinct_lower 0, distinct_higher 2, same_lower 0, same_higher 1, not finished 0
- eps 200 (n = 5, complete 5): distinct_lower 1, distinct_higher 3, same_lower 0, same_higher 1, not finished 0
- eps 1000 (n = 3, complete 3): distinct_lower 0, distinct_higher 2, same_lower 0, same_higher 1, not finished 0

### (d) by state and by molecule

- anion (n = 21, complete 21): distinct_lower 2, distinct_higher 14, same_lower 0, same_higher 5, not finished 0
- cation (n = 16, complete 16): distinct_lower 3, distinct_higher 10, same_lower 0, same_higher 3, not finished 0
- DEC (n = 3, complete 3): distinct_lower 0, distinct_higher 3, same_lower 0, same_higher 0, not finished 0
- DMC (n = 1, complete 1): distinct_lower 0, distinct_higher 0, same_lower 0, same_higher 1, not finished 0
- EC (n = 5, complete 5): distinct_lower 3, distinct_higher 0, same_lower 0, same_higher 2, not finished 0
- EMC (n = 6, complete 6): distinct_lower 0, distinct_higher 1, same_lower 0, same_higher 5, not finished 0
- PC (n = 10, complete 10): distinct_lower 0, distinct_higher 10, same_lower 0, same_higher 0, not finished 0
- TEGDME (n = 2, complete 2): distinct_lower 2, distinct_higher 0, same_lower 0, same_higher 0, not finished 0
- TMP (n = 10, complete 10): distinct_lower 0, distinct_higher 10, same_lower 0, same_higher 0, not finished 0
- the 8 cells where the two relaxed endpoints merge electronically (|relax_charge_l1 - threshold| on the same side, `charge_l1 <= 0.039`): DMC cation eps 5 (same_higher); EC cation eps 14 (same_higher); EC cation eps 20 (same_higher); EMC anion eps 5 (same_higher); EMC anion eps 40 (same_higher); EMC anion eps 80 (same_higher); EMC anion eps 200 (same_higher); EMC anion eps 1000 (same_higher)

## F37 -- `F37_stage19_identity_geometry.png`

One-line caption (verbatim, for the terminal site): (e) 弛豫前后 charge_l1 对数散点、冻结阈值 0.039 与 ±20% 贴阈值带（弛豫前后都在阈值以上 29/37，贴阈值 0 格）；(f) 双解几何 RMSD 对 Δ 漂移（0.02 Å 同极小点参考线，下方 6/37 格）；(g) 两臂弛豫能量降配对（默认解中位降 1.876 eV vs moread 1.666 eV）；(h) 自旋中心迁移矩阵（argmax 仅作描述，不作判据）

### (e) the identity channel, before and after relaxation

- complete cells with a usable `charge_l1` on both sides: 37; above the frozen threshold 0.039 at the single point 37, after relaxation 29, at both 29
- DEC anion eps=5: single point 2.916655 -> relaxed 0.209176 (still distinct)
- DEC anion eps=20: single point 1.257036 -> relaxed 0.195424 (still distinct)
- DEC anion eps=200: single point 1.277011 -> relaxed 0.191340 (still distinct)
- DMC cation eps=5: single point 0.039383 -> relaxed 0.000726 (no longer distinct)
- EC cation eps=5: single point 0.152844 -> relaxed 0.113793 (still distinct)
- EC cation eps=7: single point 0.116425 -> relaxed 0.077626 (still distinct)
- EC cation eps=10: single point 0.086566 -> relaxed 0.050570 (still distinct)
- EC cation eps=14: single point 0.064778 -> relaxed 0.018901 (no longer distinct)
- EC cation eps=20: single point 0.049116 -> relaxed 0.006971 (no longer distinct)
- EMC anion eps=5: single point 2.541366 -> relaxed 0.000001 (no longer distinct)
- EMC anion eps=20: single point 3.047638 -> relaxed 0.187827 (still distinct)
- EMC anion eps=40: single point 3.090118 -> relaxed 0.000002 (no longer distinct)
- EMC anion eps=80: single point 3.115805 -> relaxed 0.000003 (no longer distinct)
- EMC anion eps=200: single point 3.130773 -> relaxed 0.000000 (no longer distinct)
- EMC anion eps=1000: single point 3.138627 -> relaxed 0.000001 (no longer distinct)
- PC anion eps=5: single point 0.908871 -> relaxed 0.081568 (still distinct)
- PC anion eps=7: single point 0.937101 -> relaxed 0.083916 (still distinct)
- PC anion eps=10: single point 0.938032 -> relaxed 0.084656 (still distinct)
- PC anion eps=14: single point 0.955765 -> relaxed 0.086549 (still distinct)
- PC anion eps=20: single point 0.967866 -> relaxed 0.087423 (still distinct)
- PC anion eps=28: single point 0.971887 -> relaxed 0.088152 (still distinct)
- PC anion eps=40: single point 0.972029 -> relaxed 0.089019 (still distinct)
- PC anion eps=80: single point 0.971541 -> relaxed 0.089959 (still distinct)
- PC anion eps=200: single point 0.969441 -> relaxed 0.090530 (still distinct)
- PC anion eps=1000: single point 0.970856 -> relaxed 0.090841 (still distinct)
- TEGDME anion eps=20: single point 4.014055 -> relaxed 2.184831 (still distinct)
- TEGDME anion eps=200: single point 4.050934 -> relaxed 3.281649 (still distinct)
- TMP cation eps=5: single point 0.334643 -> relaxed 0.363306 (still distinct)
- TMP cation eps=7: single point 0.327257 -> relaxed 0.373899 (still distinct)
- TMP cation eps=10: single point 0.327995 -> relaxed 0.389155 (still distinct)
- TMP cation eps=14: single point 0.328593 -> relaxed 0.395850 (still distinct)
- TMP cation eps=20: single point 0.329686 -> relaxed 0.401384 (still distinct)
- TMP cation eps=28: single point 0.330415 -> relaxed 0.406808 (still distinct)
- TMP cation eps=40: single point 0.330964 -> relaxed 0.410683 (still distinct)
- TMP cation eps=80: single point 0.331602 -> relaxed 0.405218 (still distinct)
- TMP cation eps=200: single point 0.331986 -> relaxed 0.418904 (still distinct)
- TMP cation eps=1000: single point 0.332186 -> relaxed 0.420528 (still distinct)
- near-threshold cells (descriptive: |relax_charge_l1 - 0.039| <= 0.0078, i.e. +/- 20% of the cut): 0 of 37
- `near_threshold` is a description, never a criterion: the verdict stays the frozen `relax_charge_l1 > 0.039`, and a cell inside the band is still counted on whichever side of the cut it falls.

### (f) geometry: same minimum or two minima?

- relaxed arms RMSD spans 0.0000 to 3.8527 A over 37 cells; 6 fall at or below the 0.02 A reference for 'the same minimum'
- the RMSD is descriptive: the verdict is the frozen electronic criterion, not this cut

### (g) which arm falls further?

- median energy drop: default 1.8762 eV, moread 1.6655 eV; moread falls further in 0 of 37 cells

### (h) spin-centre migration (descriptive only)

- the atom carrying the reduced spin is the same in 30 of 37 complete cells; the argmax orbital label agrees in 22
- the argmax hops between near-degenerate atoms, so neither count is a criterion anywhere in this stage

## coverage

- 37 of 37 cells have both arms finished; 0 are marked as missing in the panels and never filled in with a zero

Palette and dpi follow the other week figures (dpi = 170, bbox_inches = tight). All in-figure labels are ASCII because the workspace has no guaranteed CJK font; the captions above are Chinese and are quoted verbatim by the site builder.
