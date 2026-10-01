# figure_manifest_week22_stage23

| figure | sha256 | size |
| --- | --- | --- |
| `F43_dielectric_limit_check.png` | `605a7a5ce54c2426a7a0bc7d5da6a745f8a65e806a8f2c5f9474f3f624ca49b2` | 179590 B |
| `F44_neb_refinement.png` | `48bcc944023db892d9f17c030f02a42faea19348df40cb387c2c7424e080d3eb` | 215544 B |

| input | sha256 |
| --- | --- |
| `outputs/week22/dielectric_limit.json` | `bef5d38096beb2d2baa07dacaf5884090139d41af0e1042408a22b4d0f278002` |
| `outputs/week22/neb_refinement.json` | `d64e2a0606e723d52988a33e5c766c13490ae78af397245ba4b0cf6b3d676e72` |

Generate (from the repository root):

```powershell
& $py scripts\make_stage23_figure.py
```

The PNGs carry no timestamp, so re-running on the same inputs gives
byte-identical files.

## F43 -- `F43_dielectric_limit_check.png`

One-line caption (verbatim, for the terminal site): **R4b（附加诊断，不属预注册扫描集 [5,10,20,40]）—— 裸 CPCM 离导体极限还有多远。**(a) 36 个 (分子, 电荷态) 组合上，`|E(eps) - E(1e6)|` 的均值随 eps 下降；它不是「饱和」，而是**几乎严格的 1/eps 幂律**：`|dE| x eps = 2057-2178 meV`，prefactor 约 **2.1 eV/eps**，从 eps = 7 一路测到 eps = 1000 都成立。这条律把「离导体极限还差多少」变成**可以提前算出来**的量。(b) eps = 200 时的逐分子残余：最大 **19.62 meV**（PC / anion），平均 10.81 meV；相对 eps = 1000 时最大只剩 **3.929 meV**。作为参照，冻结的决策容差 delta_m 是氧化 700 meV / 还原 2074 meV，所以 eps = 200 的残余只有它的 **2.80% / 0.95%** —— 介电层**不是严格免费**，但残差比排序论证关心的尺度小 1-2 个数量级，Stage 12/13 的「介电层免费」在实用精度上量化成立。逐分子一致性：53/54 个组合的 `dE` 随 eps 单调下降，例外 EMC/anion —— 阴离子 SCF 在不同 eps 上落到不同解分支的求解器伪迹，不是介电残差，已在该行的分析里单独标出。

## F44 -- `F44_neb_refinement.png`

One-line caption (verbatim, for the terminal site): **R11 —— 用真 NEB 取代直线插值上界。** 反应物/产物 = Stage 19 两条臂的弛豫终点（端点不重优化），regular (climbing : no)（中间像数：EC/cation/5 = 8，EC/cation/20 = 8，TEGDME/anion/20 = 4）。峰高从 ORCA 的 `<stem>.final.interp` 读，全精度。(a)-(c) 三条收敛路径，能量相对反应物，1 kT 与 1 kcal/mol 画成横线；(d) 直线界 vs 真 NEB 的对数柱状图。EC/cation/5：直线 0.00424 eV -> NEB **0.000141 eV**（one_basin，直线/NEB = 30.00） EC/cation/20：直线 0.00001 eV -> NEB **0.000053 eV**（one_basin，直线/NEB = 0.15） TEGDME/anion/20（未收敛，不给判决）2 格落在 1 kT 以下（`one_basin`）：EC/cation/5、EC/cation/20；1 格没有可用判决：TEGDME/anion/20。直线插值确实只是上界，最松的一格把峰高放大了 30.0 倍。与 Stage 19 的 RMSD 判决**冲突**的格子：EC/cation/5。

## denominators

- F43 panel (a): the mean of ``|E(eps) - E(1e6)|`` over the **36** common
  (molecule, state) pairs present at every eps on the shared grids
  (12 molecules x 3 charge states); panel (b) is those same 36 pairs at eps = 200.
- F43 is an **added diagnostic**: the pre-registered scan is ``[5, 10, 20, 40]``
  (``config/scientific_definitions.yaml``, ``STAGE0_ARTEFACTS``).
- F44 panels (a)-(c): one row per **path point** actually written by ORCA to
  ``<stem>.final.interp``.  Intermediate images per cell (read from each
  job's ORCA input): EC/cation/5 = 8，EC/cation/20 = 8，TEGDME/anion/20 = 4.
- F44 panel (d): three cells, one bar pair each -- **3 cells**, not a
  population.  The cells were chosen by ``run_stage21_path.py``; five
  EC/cation borderline cells exist and only eps = 5 and 20 were walked.
