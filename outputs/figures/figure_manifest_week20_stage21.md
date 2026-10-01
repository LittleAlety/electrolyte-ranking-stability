# figure_manifest_week20_stage21

| figure | sha256 | size |
| --- | --- | --- |
| `F40_stage21_path_profiles.png` | `511f682a4243bdeee7516a4225a8eda2bcdc10ae54211d5cecd28811f77a2010` | 222871 B |
| `F41_stage21_shell_redox.png` | `cc2a234d089245fbbdc4a494c4df841ffb365d35da024569c30dcb115175c9c8` | 167759 B |

| input | sha256 |
| --- | --- |
| `outputs/week20/stage21_path_analysis.json` | `f5ec25c2f007dbd42bb42631db01d2e24c0225ee011ee02ded607e4f349954e8` |
| `outputs/week20/stage21_path_analysis.csv` | `677655075dd1c28d685a84d7cd6ab2356f69c0b59ae48fc25372ea6861e3e199` |
| `outputs/week20/stage21_shell_redox_analysis.json` | `749f06cbae69dde8f3dc6227a9bc0144f3b5c9d942ec1a89d647d4430640bc7b` |
| `outputs/week20/stage21_shell_redox_analysis.csv` | `e52939124d96cc9dfd4f20a1a01debc46d06036db53a033a23028f9aa9286413` |
| `outputs/week20/stage21_protocol.json` | `cb717d2e5920c1b37ab181bd57d723d20eca34222bcd524d30bc000a463b6291` |
| `outputs/week20/stage21_refill.json` | `bb424fee1e0c01e9a71609fb1b3bf9a93ee27d7e38a014ec37c8f9199ce06cd4` |

Generate (from the repository root):

```powershell
& $py scripts\make_stage21_figure.py
& $py scripts\make_stage21_figure.py --check
```

The PNGs carry no timestamp, so re-running on the same inputs gives byte-identical files; ``--check`` re-renders into a temporary directory and compares both PNGs and this file byte for byte.

## denominators

- F40 works on the 3 walked cells (3 cells x 21 images) of Part A -- chosen to bracket the Stage 19 RMSD threshold, not sampled.
- F41 works on the 24 shells (12 labels x 2 redox states); 24 of them produced a usable frame and 0 were excluded.
- Part B (the ``charge_l1`` precheck) and Part D (the P2-leg refill) contribute no figure of their own; their products are listed as inputs so the week's figure set is pinned to the same data the report reads.

## F40 -- `F40_stage21_path_profiles.png`

One-line caption (verbatim, for the terminal site): F40：把 Stage 19 最脆的那条判据换一把尺子重读。三个格子在两条松弛几何之间做直线内插、每点一个冻结 r2SCAN-3c 单点（共 63 个），各自纵轴不同**不可互比**。(a) EC/cation/ε=5：Stage 19 因两臂几何相差 0.100 Å 判它 `distinct_lower`，但内插路径全称无鼓包（相对弦最大仅 0.00424 eV ≪ k_B T = 0.0257 eV），两臂弛豫能量只差 -0.00972 eV——**过度判定**，它其实是同一个平坦盆地的两个肩。(b) EC/cation/ε=20：判据另一侧的对照，路径同样无鼓包（0.00001 eV），`same_higher` 成立。(c) TEGDME/anion/ε=20（RMSD 2.214 Å）的鼓包约 66 eV，是直线路径让原子互穿的假象，只用来确认两解确实分立。内插路径是笛卡尔直线、不是最小能量路径，所以鼓包只是**上界**；反过来说「直线全程不抬升」是强证据：它不可能藏着一个势垒。结论：临界带（0.021–0.100 Å）上 RMSD 阈值把至少一格判错了，该由能量判据而非几何阈值来裁决。

### the three walked cells

| cell | Stage 19 RMSD (A) | Stage 19 verdict | path length (A) | chord hump (eV) | hump / SCF noise | relaxed delta (eV) | this stage | agrees |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| EC/cation/5 | 0.1000 | distinct_lower | 0.3172 | 0.004245 | 31.7 | -0.009722 | one_basin | **NO** |
| EC/cation/20 | 0.0210 | same_higher | 0.0649 | 0.000008 | 44.0 | +0.000043 | one_basin | yes |
| TEGDME/anion/20 | 2.2140 | distinct_lower | 13.5359 | 66.144563 | 31.5 | -0.065615 | separated | yes |

### what the profile does and does not prove

- the path is a straight Cartesian line, not a minimum-energy path, so any hump on it is only an **upper bound** to the true barrier;
- the asymmetry is the point: a straight line that never rises cannot be hiding a barrier, so a barrier-free profile is *strong* evidence that the two endpoints sit in one basin, while a hump is weak evidence of separation;
- the SCF noise floor is the median absolute second difference of the profile; humps at that level are numerical;
- 2 of 3 cells agree with the Stage 19 RMSD verdict and the one that does not is the fragile cell, not the control.

## F41 -- `F41_stage21_shell_redox.png`

One-line caption (verbatim, for the terminal site): F41：把第一溶剂壳 [Li(M)2]+ 的两个氧化还原态都做 r2SCAN-3c 弛豫（气相，与 Stage 9 同口径，起点是同一张冻结 G2Li2 几何），共 24 个 Opt、24 个可用；(a) 氧化轴：空心 = Stage 9 的冻结垂直位移，实心 = 本周的弛豫绝热位移，连线长度就是弛豫修正（均值 -0.4053 eV、最大 1.6467 eV，排序 Spearman ρ=0.797、Kendall τ=0.727、上四分位重叠 0.500）；(b) 还原轴：同样的读法（修正均值 -5.4512 eV、ρ=-0.790、τ=-0.606、重叠 nan）——还原态是中性自由基，结构可能散架，凡断键/碎片化/丢配体的格子都画成灰叉并**排除在所有统计之外**（本周排除 无）；(c) 冻结 vs 弛豫位移散点与 y=x，说明「垂直位移」作为绝热位移的上界在多大程度上成立。

### per shell

| shell | axis | frozen shift (eV) | relaxed shift (eV) | relaxation correction (eV) | usable | QC flags |
| --- | --- | --- | --- | --- | --- | --- |
| AN_m1 | oxidized | 15.3014 | 15.0790 | -0.2224 | yes |  |
| AN_m1 | reduced | 2.5681 | -3.0790 | -5.6471 | yes |  |
| DMC_m1 | oxidized | 13.4413 | 13.3143 | -0.1270 | yes |  |
| DMC_m1 | reduced | 2.7500 | -2.8088 | -5.5589 | yes |  |
| DMC_m2 | oxidized | 13.9384 | 13.6385 | -0.2999 | yes |  |
| DMC_m2 | reduced | 2.7615 | -3.2877 | -6.0492 | yes |  |
| DME_m1 | oxidized | 12.4619 | 12.1616 | -0.3004 | yes |  |
| DME_m1 | reduced | 1.9449 | -2.1355 | -4.0804 | yes |  |
| DMSO_m1 | oxidized | 12.0510 | 11.8207 | -0.2302 | yes |  |
| DMSO_m1 | reduced | 2.4210 | -2.9025 | -5.3235 | yes |  |
| DOL_m1 | oxidized | 13.9492 | 12.3025 | -1.6467 | yes |  |
| DOL_m1 | reduced | 2.5856 | -3.4196 | -6.0052 | yes |  |
| EC_m1 | oxidized | 13.3392 | 13.1244 | -0.2149 | yes |  |
| EC_m1 | reduced | 2.2402 | -2.8056 | -5.0458 | yes |  |
| GBL_m1 | oxidized | 13.1600 | 12.9818 | -0.1782 | yes |  |
| GBL_m1 | reduced | 2.6949 | -3.0391 | -5.7340 | yes |  |
| SL_m1 | oxidized | 12.6529 | 12.3075 | -0.3454 | yes |  |
| SL_m1 | reduced | 2.3957 | -2.5909 | -4.9867 | yes |  |
| SN_m1 | oxidized | 14.4144 | 14.1882 | -0.2262 | yes |  |
| SN_m1 | reduced | 2.8181 | -3.7718 | -6.5899 | yes |  |
| TMP_m1 | oxidized | 12.8622 | 12.0462 | -0.8160 | yes |  |
| TMP_m1 | reduced | 2.4564 | -2.7250 | -5.1814 | yes |  |
| TMP_m2 | oxidized | 12.8141 | 12.5576 | -0.2564 | yes |  |
| TMP_m2 | reduced | 2.4888 | -2.7235 | -5.2123 | yes |  |

### axis summaries

- oxidation: n=12 (excluded 0); frozen 13.3655 +- 0.8744 eV -> relaxed 12.9602 +- 0.9311 eV; correction -0.4053 +- 0.4102 eV; rho=0.797, tau=0.727, top-quartile overlap 0.500
- reduction: n=12 (excluded 0); frozen 2.5104 +- 0.2373 eV -> relaxed -2.9408 +- 0.4053 eV; correction -5.4512 +- 0.6121 eV; rho=-0.790, tau=-0.606, top-quartile overlap 0.000

### denominators and caveats

- the reduction axis is the one at risk: the reduced complex is a neutral radical, so a frame that breaks a bond, fragments, or loses a ligand describes a *different species*; those shells are drawn greyed out and excluded from every aggregate rather than averaged in;
- the reference is the Stage 9 ``+1`` singlet ``Opt``, so the adiabatic shift is the difference of two separate relaxations, not the relaxation energy of one state;
- excluded from the summaries: none.

## palette and rendering

- dpi = 170, ``bbox_inches = tight``, white face colour -- same as the other week figures.
- In-figure text is ASCII: the workspace has no guaranteed CJK font, so Chinese would render as boxes.  The captions above are Chinese and are quoted verbatim by the site builder.
- The three F40 panels carry independent y ranges; the control cell's hump is two orders of magnitude above the physics and sharing an axis would render the other two as flat lines.
