# figure_manifest_week21

| figure | sha256 | size |
| --- | --- | --- |
| `F42_sigma_synthetic_phase_diagram.png` | `dec8d1d6dfbffea99d017d083511c82273cfd4043980fb035d8feb7adef24fe0` | 277440 B |

| input | sha256 |
| --- | --- |
| `outputs/week4/p1_core_set_derived.csv` | `2987f8771b722d5a07517289a18a486fb2da24ed5775a196ffd7baf2c57517d3` |
| `outputs/week9/stage10_ladder.json` | `3eb6b36d5622ec0e3147dd827a6437aabac2ea38c53936fddc974e85376ac3cf` |

Generate (from the repository root):

```powershell
& $py scripts\analyze_sigma_synthetic.py
```

The PNG carries no timestamp, so re-running on the same inputs and the same seed
gives a byte-identical file.

## F42 -- `F42_sigma_synthetic_phase_diagram.png`

One-line caption (verbatim, for the terminal site): R2：把 Week 9 的 rho(shift std, tau_b) = -0.851（10 点 / 5 台阶）从 headline 降级为现象示意，改用合成数据相图回答同一个问题——固定靶排序 t，令逐分子位移 delta_i = mean + std * z_i 并把 z 在每个 replicate 内标准化（使 delta 的样本 sd 恰为 std），在 mean 属于 [-8, +8] eV、std 属于 [0, 2] eV 的网格上每格 2000 组重抽样。(a)(b)(d) 三张相图沿 mean 轴**严格常数**（tau_b 的最大绝对差 0.00e+00）：给每个分子加同一个常数既不能换序也不能改变任何 pair 差，所以 Week 9 那个 rho(|mean|, tau_b) = -0.535 只能是共线性伪影——实测点上 rho(|mean|, std) = +0.758，而相图里两者按构造独立、同一相关系数为 0.000。(c) 换到 std 轴，tau_b 单调下降且相图的秩相关为 -1.000：氧化靶轴上 tau_b 均值跌破 0.8 于 std = 0.45 eV、跌破 0.5 于 1.20 eV（还原靶轴 0.25 / 0.70 eV），即**排序的代价只由位移的离散度支付**；实测 10 点多数贴着曲线，但两个例外各有明确的物理身份——P0->P1/还原（std = 2.25 eV，tau_b = +0.60）在曲线**之上**，因为它的位移几乎平行于靶轴；C1->C2/还原（std = 0.335 eV，tau_b = +0.29）在曲线**之下**，因为那一级的还原是 Li 中心而非分子中心（state-identity 改变），纯离散度模型按定义看不见这件事。

## denominators

- the phase diagram is `33 x 41` cells over mean in [-8.0, 8.0] eV and std in [0.0, 2.0] eV,
  each cell averaged over 2000 shift realisations; the curve panel uses 20000.
- the overlaid red circles are the 10 measured (rung, axis) points of the Week 9 ladder,
  i.e. **5 rungs** x 2 axes -- not 10 independent experiments.
- the two target orderings are the real P1 r2SCAN-3c values on the Stage 10 common subset.
