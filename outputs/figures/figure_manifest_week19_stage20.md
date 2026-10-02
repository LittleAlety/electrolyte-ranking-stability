# figure_manifest_week19_stage20

| figure | sha256 | size |
| --- | --- | --- |
| `F38_stage20_relax_rung.png` | `f38fc939ddbcf9706d6c854fed756f936a90df999793fd8aa2ee10215b766b8f` | 400820 B |
| `F39_stage20_xtb_arms.png` | `06e073d4909ba53759141ef2588c9651bd42e49b09ac35603a7c9e635b800b32` | 518316 B |

| input | sha256 |
| --- | --- |
| `outputs/week19/stage20_relax_rung.json` | `e1a9cdd2ba5d5b65d84641d002ac42f9bbe8721e27e7e1c80ab49538181fd827` |
| `outputs/week19/stage20_relax_rung_cells.csv` | `0ca188cd0bd2aba6cecef6c2d1411d3ec1f06598aea2867d49b7154d3edf6aff` |
| `outputs/week19/stage20_relax_rung_ladder.csv` | `f87e3ce8c230727c18312251fd49df090f39ab757742ee409bd2f65091e939b4` |
| `outputs/week19/stage20_relax_rung_epsilon.csv` | `64b574f54ee5b452a02581bce750d2f90cf426b683c274855536b7b7e3ff3649` |
| `outputs/week19/stage20_xtb_arms_analysis.json` | `30042094148ee0a0c37c3eafb3aa12405ce44d23142caf3a65f381fb4415c9fc` |
| `outputs/week19/stage20_xtb_arms_cells_analysis.csv` | `d25449e22c4c0d0b575dfbb7c38f1657edf98a0466fa22a866ec09cbcae11565` |
| `outputs/week18/stage19_relax_cells_analysis.csv` | `7e1333d553ebb72fe98049b094f61fcd93d9f66f79aa6872dff350f050ef79aa` |

Generate (from the repository root):

```powershell
& $py scripts\make_stage20_figure.py
& $py scripts\make_stage20_figure.py --check
```

The PNGs carry no timestamp, so re-running on the same inputs gives byte-identical files; ``--check`` re-renders into a temporary directory and compares both PNGs and this file byte for byte.

## denominators

- F38 works on the 37 cells of the Part 1 sixth rung (one electronic state per molecule, so rank metrics stay omitted); F39 works on the same 37 `moread_lower` cells -- the complete set of cells whose two single-point SCF solutions differ *and* favour moread.
- Read `x/37` as "given that a single point produced a metastable pair that was lower, does it survive this step?" -- a well-defined conditional proportion on that definition set, never a population incidence over the 414-cell directory.
- The two `distinct` notions are **not the same criterion**: Stage 19 uses the frozen electronic identity cut `charge_l1 > 0.039`, Part 2 only has the geometric `RMSD <= 0.02 A` of a cheap optimiser.  The agreement rate between the two *verdicts* is therefore a comparison across criteria, unlike panel (b), which compares two methods on one geometry.
- The xTB jobs are **gas phase** (no CPCM); `epsilon` only labels which CPCM cell the starting geometry came from, so the epsilon strata here are not a dielectric effect.
- `0.02 A` and `0.001 eV` are fixed descriptive thresholds, chosen before the jobs ran; nothing here is tuned after the fact.

## F38 -- `F38_stage20_relax_rung.png`

One-line caption (verbatim, for the terminal site): (a) 37 个格子的弛豫位移 Δ = −能量降（eV）对 ε（对数轴，按态着色、逐分子连线；逐分子 ε 极差中位 0.0263 eV、最大 0.215 eV（DEC），即弛豫修正几乎与介电常数无关）；(b) 同一把尺子：4 个可比 population 上 5 个冻结台阶与第六级台阶（弛豫）的相对散布 std/|mean|（对数轴；斜纹柱 = 氧化轴 G1→G2 的 |mean|≈0，相对散布无意义）；(c) (|mean|, std) 平面：6 个台阶 × population 共 30 行，实心大点 = 新台阶；(d) 7 个分子的 Δ 均值，误差棒 = 跨 ε 极差——还原支近乎刚性平移（均值 -1.953 eV、std 0.160 eV、相对散布 0.08），氧化支为散布型（均值 -0.610 eV、std 0.315 eV、相对散布 0.52）

### (a) the shift is flat in epsilon

- 37 cells, 7 molecules, 10 distinct epsilon values
- per-molecule range of Delta across its own eps: median 0.0263 eV, max 0.2150 eV (DEC, n_eps=3)
- overall: mean -1.3724 eV, std 0.7143 eV, range -2.4405 to -0.1910 eV
- by state: anion mean -1.9530 eV (std 0.1601, rel. disp. 0.08, 21 cells); cation mean -0.6104 eV (std 0.3150, rel. disp. 0.52, 16 cells)

### (b)(c) the same ruler

- ladder rows: 30 (rungs 6, populations 6); comparable populations drawn in (b): ox_dmc_ec_tmp_eps5, ox_carbonates_eps5, red_dec_emc_pc_tegdme_eps20, red_dec_emc_pc_eps5
- new rung on ox_dmc_ec_tmp_eps5: mean -0.4625 eV, std 0.3422 eV, rel. disp. 0.7400 (n = 3 molecules)
- new rung on ox_carbonates_eps5: mean -0.2686 eV, std 0.0943 eV, rel. disp. 0.3509 (n = 2 molecules)
- new rung on ox_all_eps_mean: mean -0.4587 eV, std 0.3421 eV, rel. disp. 0.7458 (n = 3 molecules)
- new rung on red_dec_emc_pc_tegdme_eps20: mean -2.0096 eV, std 0.2543 eV, rel. disp. 0.1265 (n = 4 molecules)
- new rung on red_dec_emc_pc_eps5: mean -1.9470 eV, std 0.0226 eV, rel. disp. 0.0116 (n = 3 molecules)
- new rung on red_all_eps_mean: mean -2.0238 eV, std 0.2598 eV, rel. disp. 0.1284 (n = 4 molecules)
- degenerate rungs flagged as not meaningful: G1_to_G2 (oxidation)

### (d) the seven molecules

- DEC anion: mean -1.8420 eV, across eps -1.9725 to -1.7575 eV (range 0.2150, n_eps=3)
- PC anion: mean -1.9003 eV, across eps -1.9296 to -1.8762 eV (range 0.0534, n_eps=10)
- EMC anion: mean -1.9445 eV, across eps -1.9653 to -1.9390 eV (range 0.0263, n_eps=6)
- TEGDME anion: mean -2.4085 eV, across eps -2.4405 to -2.3764 eV (range 0.0640, n_eps=2)
- EC cation: mean -0.1954 eV, across eps -0.2020 to -0.1910 eV (range 0.0110, n_eps=5)
- DMC cation: mean -0.3353 eV, across eps -0.3353 to -0.3353 eV (range 0.0000, n_eps=1)
- TMP cation: mean -0.8454 eV, across eps -0.8501 to -0.8428 eV (range 0.0072, n_eps=10)

## F39 -- `F39_stage20_xtb_arms.png`

One-line caption (verbatim, for the terminal site): (a) 两臂起点 RMSD 对 xTB 弛豫后 RMSD（Å，对数轴，按 4 类结局着色，虚线 = 0.02 Å 同极小点阈值；起点中位 0.4716 → 弛豫后中位 0.8078 Å，6/37 格两臂合并）；(b) 同一几何上 xTB 单点 Δ 对 ORCA r2SCAN-3c 弛豫 Δ（eV，y=x 与 ±1 meV 带；偏好方向一致 33/37 = 89%，4 个分歧已圈出）；(c) 两臂能量差的四个读数（ORCA 单点 / ORCA 弛豫 / xTB 单点 / xTB 弛豫，对数轴，中位 1.198e-01 / 1.960e-03 / 7.171e-03 / 2.133e-04 eV）——xTB 弛豫把差异压掉约 33.6 倍；(d) 单臂漂移对起点双解 RMSD（Å，y=x，对数轴；两臂漂移中位 0.651 / 0.657 Å 与起点差异中位 0.4716 Å 同量级，故几何 distinct 部分继承自起点）。分母：Stage 19 单点两解不同且 moread 更低的 37 格，不是 414 格总体的发生率

### (a) separation before and after the cheap relaxation

- start RMSD p50 0.4716 A (min 8.86e-08, max 3.8527); relaxed RMSD p50 0.8078 A (min 6.84e-05, max 4.0312)
- merged into one minimum (RMSD <= 0.02 A): 6 of 37; the xTB outcome counts are distinct_lower 15, distinct_higher 16, same_lower 0, same_higher 6
- xTB verdict against the Stage 19 electronic verdict: agrees in 17 of 37

### (b) the same geometry, a cheaper method

- xTB single point against ORCA r2SCAN-3c relaxed Delta, both on the Stage-19 endpoints: sign agrees in 33 of 37 (89.2%)
- disagreements: EC cation eps=5 (xTB 0.00717 eV vs ORCA -0.00972 eV), EC cation eps=14 (xTB -0.00731 eV vs ORCA -0.00021 eV), EC cation eps=20 (xTB -0.00267 eV vs ORCA 0.00004 eV), TMP cation eps=80 (xTB -0.00391 eV vs ORCA -0.00026 eV)

### (c) four readings of the separation (median of |Delta|)

- ORCA single point: 1.1983e-01 eV
- ORCA relaxed: 1.9600e-03 eV
- xTB single point: 7.1711e-03 eV
- xTB relaxed: 2.1334e-04 eV
- xTB relaxation compresses the xTB separation by 33.6 x

### (d) one-arm drift versus the start separation

- drift p50: default 0.6515 A, moread 0.6573 A; start separation p50 0.4716 A
- cells where both arms drift by more than the 0.02 A tolerance: 36 of 37

## palette and rendering

- dpi = 170, ``bbox_inches = tight``, white face colour -- same as the other week figures.
- In-figure text is ASCII: the workspace has no guaranteed CJK font, so Chinese would render as boxes.  The captions above are Chinese and are quoted verbatim by the site builder.
