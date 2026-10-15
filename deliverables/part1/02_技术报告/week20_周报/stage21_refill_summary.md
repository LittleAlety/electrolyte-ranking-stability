# Stage 21 / Part D —— P2 腿「真回填」敏感性检查

> 零新增量化计算：本文的每一个数字都来自已落盘的冻结产物，无任何新的 ORCA / xTB 作业。

## 0. 一句话结论

严格 P2 腿有 7/54 格带弛豫数据，可做部分真回填。

## 1. 被回填的是哪条腿（定义原文）

- 五级台阶第 2 级（`scripts/analyze_stage10_synthesis.py:66`）：`("P1_to_P2", "环境：气相 P1 -> SMD(乙腈) P2")`
- 「P2 腿」= 该级的终点层 = **SMD(乙腈)** 层；规模原文（`docs/26_week16_report.md:11`）：`18 分子 x 3 态 = 54 格`
- 位移定义原文（`scripts/analyze_stage10_synthesis.py:254`）：

      shifts.append(pair[1] - pair[0])

- 轴口径原文（`scripts/analyze_stage10_synthesis.py:15-17 / :131-133`）：“puts them on ONE axis convention (``p_red = -EA`` so that ``higher_is_better`` is True on both axes / Reduction is stored as ``p_red = -EA`` so that a larger value always means "more stable", which is what weeks 4-5 assumed (``higher_is_better=True``).”
- 符号约定：Delta = -drop；两轴都是越大越稳，所以回填后 p2' = p2 - drop

本脚本不自己重写合成：台阶数据由 `analyze_stage10_synthesis` 的 `load_ladder` / `ladder_rows` / `lookup` / `common_names` 直接读取与重算，本文件只替换 `P1_to_P2` 这一级的 P2 端点。

## 2. 覆盖率（能回填几格 / 共几格）

| 腿的定义 | 格数 | ORCA 弛豫 | xTB 弛豫 | 可回填 | 覆盖率 |
| --- | --- | --- | --- | --- | --- |
| 严格 P2 腿（SMD） | 54 | 7 | 7 | **7** | 13.0% |
| 介电子腿（裸 CPCM） | 414 | 37 | 37 | 37 | 8.94% |

> 严格 P2 腿（SMD）的弛豫覆盖为 0：Stage 19/20 的 37 个弛豫格全部落在裸 CPCM 介电子腿上（layer = relax_cpcm_<eps>），没有一格是 SMD。因此「把 P2 腿直接换成弛豫后能量」在现有数据下不可执行，只能按 Stage 20 的态内量假设做转移。

可回填的分子：DEC, DMC, EC, EMC, PC, TEGDME, TMP（氧化轴 DMC, EC, TMP；还原轴 DEC, EMC, PC, TEGDME）。

## 3. 逐轴数字（完全回填子集）

子集 = 「该轴上每一个成员都有 Δ 」的最小分子集，这是唯一不混入“单边干预”的读数。

| 轴 | n | 排序（前） | 排序（回填后） | Spearman rho | Kendall tau | Top-10% 重叠 | 是否被改写 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| oxidation | 3 | DMC > TMP > EC | EC > DMC > TMP | -0.5000 | -0.3333 | 0.000 | 是 |
| reduction | 4 | TEGDME > DEC > EMC > PC | TEGDME > DEC > PC > EMC | 0.8000 | 0.6667 | 1.000 | 否 |

## 4. 稳健性：三种 Δ 估计量

| 估计量 | 轴 | rho | tau | Top-10% 重叠 |
| --- | --- | --- | --- | --- |
| orca_mean_eps | oxidation | -0.5000 | -0.3333 | 0.000 |
| orca_mean_eps | reduction | 0.8000 | 0.6667 | 1.000 |
| orca_largest_eps | oxidation | -0.5000 | -0.3333 | 0.000 |
| orca_largest_eps | reduction | 0.6000 | 0.3333 | 0.000 |
| xtb_mean_eps | oxidation | -1.0000 | -1.0000 | 0.000 |
| xtb_mean_eps | reduction | -0.8000 | -0.6667 | 0.000 |

### 台阶级读数（tau_b: P1 -> P2 前 vs 后，orca_mean_eps）

| 人口/轴 | n | tau_b 前 | tau_b 后 | shift_std 前 | shift_std 后 |
| --- | --- | --- | --- | --- | --- |
| common/oxidation | 10 | 0.9111 | 0.9111 | 0.2694 | 0.2274 |
| common/reduction | 10 | 0.7778 | 0.7778 | 0.2858 | 0.2858 |
| native/oxidation | 18 | 0.8954 | 0.8431 | 0.3018 | 0.3108 |
| native/reduction | 18 | 0.6732 | 0.3203 | 0.3205 | 0.8994 |

### 台阶级读数（tau_b: P1 -> P2 前 vs 后，orca_largest_eps）

| 人口/轴 | n | tau_b 前 | tau_b 后 | shift_std 前 | shift_std 后 |
| --- | --- | --- | --- | --- | --- |
| common/oxidation | 10 | 0.9111 | 0.9111 | 0.2694 | 0.2267 |
| common/reduction | 10 | 0.7778 | 0.7778 | 0.2858 | 0.2858 |
| native/oxidation | 18 | 0.8954 | 0.8431 | 0.3018 | 0.3103 |
| native/reduction | 18 | 0.6732 | 0.3333 | 0.3205 | 0.8896 |

### 台阶级读数（tau_b: P1 -> P2 前 vs 后，xtb_mean_eps）

| 人口/轴 | n | tau_b 前 | tau_b 后 | shift_std 前 | shift_std 后 |
| --- | --- | --- | --- | --- | --- |
| common/oxidation | 10 | 0.9111 | 0.9111 | 0.2694 | 0.2658 |
| common/reduction | 10 | 0.7778 | 0.7778 | 0.2858 | 0.2858 |
| native/oxidation | 18 | 0.8954 | 0.8431 | 0.3018 | 0.3227 |
| native/reduction | 18 | 0.6732 | 0.5686 | 0.3205 | 0.3176 |

## 5. 已知限制

1. **严格 P2 腿的回填不可执行**：Stage 19/20 的 37 个弛豫格全部在裸 CPCM 介电子腿上，SMD 层一格也没有。因此下面的数字靠的是 Stage 20 的**态内量转移**假设。
2. **转移是近似**：日志已在 `docs/29_week19_report.md` §7 第 7 条明写“不可读成「P2 腿错了 1.9 eV」”。本文的结论只能读成「在转移假设下」。
3. **子集很小**：氧化轴 n=3、还原轴 n=4，不足 5 个分子，不能当作发布级推断，只能当作该子集上的描述。
4. **部分干预不是物理场景**：在全部 18 个分子上只改有 Δ 的 7 个会把秩序拉开，那是算术后果，不是 P2 腿的性质。
5. **单边界面没有逐格真回填**：`refill.n_applied = 7`（分子,态）格，其余 11 个分子的 P2 值保持冻结。

## 6. 产物

- `outputs/week20/stage21_refill_cells.csv`：每一行 = （格, 来源, 臂）
- `outputs/week20/stage21_refill.json`：覆盖率、估计量、逐轴对比、结论
- `outputs/week20/stage21_refill_summary.md`：本文

