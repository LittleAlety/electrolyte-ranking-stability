# figure_manifest_week23_stage24

| figure | sha256 | size |
| --- | --- | --- |
| `F45_targeted_two_guess.png` | `fe2a690f7c7a6857f1ecae27d14a4b78bfbf596f06a8b764169ce2e4220e4076` | 328909 B |
| `F46_shell3_saturation.png` | `53f98c2f13f396d1dd0e106f7597503b268f1217dcc94b3b92e50a04c95a2202` | 172726 B |

| input | sha256 |
| --- | --- |
| `outputs/week23/targeted_two_guess.json` | `c6ca4fbbdd50c79e82a9251a69916c75cd29e288f9f571971da8ebf22b14756a` |
| `outputs/week23/shell3_xtb_sign_test.json` | `56976591123c0e3cdd1ed287e47d3773c90ffe2be42a51f95a1276236d6d70c5` |
| `outputs/week15/stage16_cells.csv` | `60f5dc3aecb632293e2a6d006b1bb2190c7d42700375abf786e562f190ddb3bc` |

Generate (from the repository root):

```powershell
& $py scripts\make_stage24_figure.py
```

The PNGs carry no timestamp, so re-running on the same inputs gives
byte-identical files.

## F45 -- `F45_targeted_two_guess.png`

One-line caption (verbatim, for the terminal site): **R8 —— 给「靶向双腿」定价。** 容许量 A_axis 定义为逐格效应量的最大值，即一次漏解能给单个格子带来的最大位移。氧化轴：A_axis = **0.152252 eV**（冻结 delta_m 0.700245 eV 的 21.7%，最坏格子 TMP@eps=5）；16 个 material 格子中位数 0.134273 eV、p90 0.147105 eV；按 A_axis 靶向，120 格里只需双腿 86 格（71.7%，省 28.3%），实测翻转 19/660 对，漏掉 0 个。还原轴：A_axis = **0.285963 eV**（冻结 delta_m 2.074299 eV 的 13.8%，最坏格子 EMC@eps=1000）；16 个 material 格子中位数 0.095349 eV、p90 0.282145 eV；按 A_axis 靶向，120 格里只需双腿 116 格（96.7%，省 3.3%），实测翻转 21/660 对，漏掉 0 个。(a) 两条轴的 16 个 material 逐格效应量与各自的 A_axis、冻结 delta_m 画在同一对数轴上；(b) 靶向比例随阈值 delta 的阶梯。(c) 协议校验：靶向协议在 10 个 eps 上与全双腿逐层同排序，氧化 min tau_b = 1.0000（单腿对照 0.9394），还原 min tau_b = 1.0000（单腿对照 0.8788）。(d) 只有保护清单边界的变体真正省钱：氧化事后 delta_star = 0.146292 eV 省 40.0%（但漏 1 个翻转：EMC/TMP@eps=7）；只保护 Top-k 清单边界的变体 k=1 省 91.7%（10/120 格），k=4 省 66.7%（40/120 格）。还原事后 delta_star = 0.253422 eV 省 6.7%（但漏 1 个翻转：AN/EMC@eps=1000）；只保护 Top-k 清单边界的变体 k=1 省 83.3%（20/120 格），k=4 省 53.3%（56/120 格）。结论：靶向规则**安全但几乎不省钱** —— 12 分子 x 10 介电的 pair 谱本来就密，真正省下计算的是只保护 Top-k 清单边界的变体；A_axis 是**靶向之前**就能算出来的量，delta_star 只有把双腿全部算完才拿得到。

## F46 -- `F46_shell3_saturation.png`

One-line caption (verbatim, for the terminal site): **R5 —— EC 第三配位壳的符号/形状检验（GFN2-xTB，非 r2SCAN-3c）。** 阶梯（相对自由 EC）：n=0 free EC dIP 0.000 / dEA 0.000 eV；n=1 [Li(EC)]+ dIP 3.897 / dEA 6.291 eV；n=2 [Li(EC)2]+ dIP 2.015 / dEA 5.672 eV；n=3 [Li(EC)3]+ dIP 1.292 / dEA 5.336 eV。增量：dd(1->0) 氧化 +3.897 / 还原 +6.291 eV；dd(2->1) 氧化 -1.882 / 还原 -0.619 eV；dd(3->2) 氧化 -0.723 / 还原 -0.336 eV；两个轴的 dd(3->2) 与 dd(2->1) 同号且绝对值更小（sign_persists 氧化 True / 还原 True，magnitude_shrinks 氧化 True / 还原 True），比值 dd(3->2)/dd(2->1) 氧化 0.384 / 还原 0.543，判决 `consistent_with_saturation`。跨层级只比无量纲比值 dd(2->1)/dd(1->0)：氧化 -0.483 vs r2SCAN-3c -0.408（偏差 18%），还原 -0.098 vs -0.239（偏差 59%）—— 还原轴这一比值受 state-identity 影响，**不可搬运**，只能当提示。(a) n = 0..3 的阶梯（共 14 个 xTB 作业），(b) 增量柱状图，(c) 跨层级比值对照。GFN2-xTB 的绝对值不得与 docs/18 的 r2SCAN-3c 阶梯并列（产物自带的 level_caveat），只有符号与单调性可比。

## denominators

- F45 panel (a): **16 material cells per axis** (the Stage 16 threshold
  `|delta_ev| >= 1 meV`, inherited unchanged), out of 120 cells per axis
  (240 across both axes: 12 molecules x 10 epsilons).  The per-cell effect is
  re-derived here from
  `outputs/week15/stage16_cells.csv` as the change of the **full** decision
  quantity between the two arms, so the maximum reproduces the frozen
  `allowance_ev` to better than 1e-9 eV; `check_allowance` asserts it, along
  with the identity of the worst cell quoted in `allowance_detail`.
- F45 panels (b)-(d): the ladder, the protocol check and the list variant are read
  verbatim from `outputs/week23/targeted_two_guess.json`; each axis carries
  660 molecule pairs over 120 cells.
- F45 panel (c): the targeted protocol rows are exactly 1.000 on both axes and are
  asserted before anything is drawn; the control is the single-leg protocol.
- F46: GFN2-xTB only, 14 jobs in `shell3_xtb_sign_test.json` (4 cluster sizes x
  3 charge states, plus the free-EC reference).  Absolute shifts must never be
  placed next to the `docs/18` r2SCAN-3c ladder -- the product carries that
  caveat itself.  Panel (c) compares a ratio with a ratio and nothing else; the
  Stage 9 reference is r2SCAN-3c (ORCA).
