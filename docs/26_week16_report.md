# Week 16 报告 —— Stage 17：亚稳态对已发布台阶结论的污染上限，与两个 SCF 解的电子结构身份

> 本文由 `scripts/gen_week16_report.py` 从 `outputs/week16/` 的 JSON / CSV 逐数读出生成，数字不手抄；
> 重跑该脚本即可刷新（`--check` 只渲染不落盘）。
> 生成时间基准：`stage17_smd_moread.json` 的 `generated_utc` = 2026-09-30T14:02:57.024190+00:00、
> `p2_summary_moread_smd_acetonitrile.json` 的 `generated_utc` = 2026-09-30T14:11:41.911192+00:00
>（Part A 与 Part B 的分析产物同批生成）。

## 0. 一句话结论

**Part A（污染上限）**：把 Week 9「五级台阶」第 2 级 `P1 -> P2` 的 **P2 腿**（取自 **SMD(乙腈)** 层）从 ORCA 自带初猜换成 moread 初猜重算（18 分子 x 3 态 = 54 格，全部 ok）之后，两条轴上的 `tau_b` / `O_20%` / `f_unresolved` / `f_robust_inv` **没有任何一条被改写**：oxidation `tau_b` 0.8954 -> 0.9216（Δ +0.0261）、reduction `tau_b` 0.6732 -> 0.6732（Δ +0.0000），两臂 `tau_b` 的 95% CI 都重叠（污染被 CI 吸收）。更强的一条是：**在本项目这条具体流水线、这批格子、这套估计量下**（`sigma_ij = abs(d0_ij - d1_ij)/sqrt(2)` 且 `z_primary = 1.0`），`f_robust_inv` 从 0 变非 0 是**结构性不可能**（§4.7 的两行证明），不是「本周恰好看不到」。**这不是普适定理**：换 `z`、换 `sigma` 的定义、或补进第三条 realization，这条不可能性都会解除。

**Part B（解的电子结构身份）**：受影响 32 格的两个 SCF 解都是**自旋纯双重态**（`<S^2>` 全部落在 0.75±0.01，32/32），所以这**不是**破缺对称性 / 自旋污染伪影，而是同一自旋量子数下的两个不同 SCF 驻点；差异的主轴是**电荷重组**（`charge_l1` 均值 0.983）而不只是自旋重排。阴离子的自旋中心在两臂完全一致（16/16），阳离子只有 5/16 —— 「默认初猜把空穴放在哪」比「把电子放在哪」更不稳定。

## 1. 为什么要有这一步（Stage 17 的动机）

Stage 17 直接执行 Week 15 §11 的第 1 条与第 4 条。Week 15 的原文是：

> 1. **把漏解回填到 sigma 台阶结论上（最高优先）**：Week 9–12 的台阶分析用的是 P0/P1 的默认初猜能量。
>    既然默认初猜在某些 (分子, 状态, 电介质) 上会停在高解，就要量化「台阶结论被污染的上限」——
>    把本周目录里 `delta < -1 meV` 的单元格按台阶归类，看它们是否真的改写过 tau_b / Top-k / 清单。

> 4. **把「第二解」从能量现象升级为电子结构现象**：对漏解单元格比较两条解的占据轨道与 Mulliken 自旋
>    分布，回答「低解多了什么」——是某个 sigma*/pi* 轨道被额外占据，还是自旋重新定域。

Week 15 自己留了一句免责：目录只知道两条臂的能量不同，没有比较它们的占据轨道、自旋分布或键长（Week 15 §10 第 6 条）。Stage 17 把这两件事同时补上，并刻意选了**最便宜、也最像真实污染源**的路：

- **Part A** 不重算整条台阶，只把 Week 9 第 2 级台阶 `P1 -> P2` 的 P2 腿（SMD(乙腈) 层）从默认初猜换成
  moread 重算。这是「已发布结论直接架在默认初猜上、且污染有明确物理来源」的唯一一处：
  Week 9 报告的台阶定义原文是「环境：气相 P1 -> SMD(乙腈) P2」，来源表 `outputs/week4/p2_environment_effects.csv`。
- **Part B** 不新开任何量化作业，只读**已经存在**的 `.out`，把两条解的 `<S^2>`、自旋中心、轨道标签、
  定域性（参与率 PR）与 Mulliken 电荷 / 自旋的 L1 差逐格对照——这正是 Week 15 §11 第 4 条要求的升级。

两个问题的意义不同：Part A 回答「已发布的东西还站得住吗」（防守），Part B 回答「两个解到底差在哪」
（机制）。合起来，Stage 17 把 Week 15 的「漏解是能量现象」推进成「漏解是一个可量化的污染上限，
而且它的电子结构身份可以被刻画」。

## 2. 口径与记号

### 2.1 沿用不变的部分

- 方法：**r2SCAN-3c**（气相与连续介质同法），**ORCA 6.1.1**，几何固定为 **G1**（不做任何重优化）。
- 状态：中性 / 阳离子 / 阴离子三态，垂直量语义与 Week 4–15 完全一致。
- 判据约定（产物 `convention` 字段原文）：`p_red = -EA; higher_is_better = True on both axes`。
- 材料阈值：**1 meV**，原样继承 Week 14（Stage 15），本周**不重新标定**。
- 台阶定义（Week 9 §2.3 原文）：第 2 级 `P1_to_P2` = 「环境：气相 P1 -> SMD(乙腈) P2」，
  来源表 `outputs/week4/p2_environment_effects.csv`。**本周只动这一级的 P2 腿。**
- 受影响格子的定义（Part B）：`delta = E_moread - E_default < -1 meV`，即默认初猜停在一个更高的 SCF 解上。

### 2.2 两个冻结判据的原文定义（引用，不改写）

`sigma` 与 `f_unresolved` 不是本周新造的量：它们自 Week 4 起被使用，在 Week 10 被化简为闭式，
在 Week 11 §2 以记号表的形式冻结。本报告一律**引用原文**，不做改写：

- `sigma` 的闭式（`docs/20_week10_report.md` T1 原文）：

  > **命题**：`sigma_ij = abs(delta_i - delta_j) / sqrt(2)`。

- `f_unresolved` 的等价写法（`docs/20_week10_report.md` T4 原文）：

  > f_unresolved(z) = Pr_{i<j}( q_ij > sqrt(2)/z )

- 记号与判据（`docs/21_week11_report.md` §2 记号表原文）：

  > | delta | `delta_i = before_i - after_i`，逐分子位移 |
  > | b | OLS 斜率 of `delta` on `after`（含截距） |
  > | q_ij | `abs(delta_i - delta_j) / abs(after_i - after_j)`，位移对轴的割线斜率 |
  > | 不可分辨 | `q_ij > sqrt(2)/z`（z = 1 为主判据，z = 1.96 为敏感性） |

- 同一条件的另一种写法（`docs/21_week11_report.md` §1 原文）：

  > 一对候选可分辨，当且仅当 `q_ij = abs(delta_i - delta_j) / abs(P1_i - P1_j) <= sqrt(2)/z`。

`z` 取预注册值 `z_primary = 1`（`config/prereg.yaml` 的 `pair_comparison.z_factor.value`，产物里逐格记为 `z_primary`），敏感性列为 `z = 1.96`。
本报告使用 `sigma` / `f_unresolved` / `f_robust_inv` 时，含义与上面引用的原文逐字一致。

### 2.3 单腿替换许可证（Part A 为什么只换一条腿）

本阶段只替换 `P1 -> P2` 的 **P2 腿**：`P1` 的数值、G1 几何、方法层（r2SCAN-3c / SMD(乙腈)）以及其余四级
台阶（`P0_to_P1`、`G1_to_G2`、`C0_to_C1`、`C1_to_C2`）**全部未动**。因此本部分给出的是**单腿敏感性**，
不是整条台阶的重算——它回答「这一条腿的初猜会不会改写已发布结论」，不回答「重算整条台阶会怎样」。
它的合法性来自 3.1 的几何审计：新作业与 Week 4 参照**逐位同几何**，所以被替换的只有初猜这一个变量。

### 2.4 Part B 的判据（只读既有 `.out`，零新增作业）

Part B 只读**已经存在**的 `.out`：默认臂来自 Week 12/13 的 CPCM 目录，moread 臂来自 Week 14 的同名目录。
普查扫过 `outputs/week*/orca*/**/*.out` 共 1051 个文件，其中 756 个可解析为 C-PCM 臂输出。
「受影响格子」的判据仍是 `delta_ev < -1 meV`（Stage 16 目录的 32 格），**本周不新开任何量化作业**。

## 3. 本周新增的计算

### 3.1 Part A：54 个 SMD moread 单点

- 规模：**54 格** = 18 分子 x 3 态 x 1 层（`moread_smd_acetonitrile`）；`n_ok = 54`，`n_failed = 0`。
- 调度：`--jobs 2 --nprocs 8`（本机 16 逻辑核），与既有各层协议相同。
- **逐层墙钟中位数：15.66 s**（`p2_summary_moread_smd_acetonitrile.json` 的 `wall_clock_seconds_median`）。全部为新算：`n_computed = 54`、`n_reused = 0`。
- 参照表：`outputs/week4/p2_core_set_smd_acetonitrile.csv`（default 臂，Week 4 冻结；产物原文：「ORCA's own guess, as frozen in week 4 -- read from the reference CSV, never recomputed here」），零格缺参照（`n_cells_without_reference = 0`）。
- 初猜协议（产物原文）：`moread` = 「! MORead + %moinp <gas-phase gbw of the same charge state>」。
  需要暂存目录 `C:\Users\LITTLE~1\AppData\Local\Temp\electrolyte_stage17_gbw`，原因是产物原文写的：「ORCA guess_restart aborts on a non-ASCII %moinp path; the repository lives under a Chinese directory name」。

**G1 几何复用审计（`stage17_smd_moread.json` 的 `geometry_audit`）**：18 个分子逐一比对，每个比 3 个态，全部 `all_identical = True`。这是「单腿替换许可证」（2.3）的实测依据：

| 分子 | 参照目录 | 比对态数 | 逐位一致 |
| --- | --- | --- | --- |
| AN | `outputs/week4/orca_smd_acetonitrile/AN` | 3 | 是 |
| DEC | `outputs/week4/orca_smd_acetonitrile/DEC` | 3 | 是 |
| DMC | `outputs/week4/orca_smd_acetonitrile/DMC` | 3 | 是 |
| DME | `outputs/week4/orca_smd_acetonitrile/DME` | 3 | 是 |
| DMSO | `outputs/week4/orca_smd_acetonitrile/DMSO` | 3 | 是 |
| DOL | `outputs/week4/orca_smd_acetonitrile/DOL` | 3 | 是 |
| EA | `outputs/week4/orca_smd_acetonitrile/EA` | 3 | 是 |
| EC | `outputs/week4/orca_smd_acetonitrile/EC` | 3 | 是 |
| EMC | `outputs/week4/orca_smd_acetonitrile/EMC` | 3 | 是 |
| FEC | `outputs/week4/orca_smd_acetonitrile/FEC` | 3 | 是 |
| GBL | `outputs/week4/orca_smd_acetonitrile/GBL` | 3 | 是 |
| MA | `outputs/week4/orca_smd_acetonitrile/MA` | 3 | 是 |
| PC | `outputs/week4/orca_smd_acetonitrile/PC` | 3 | 是 |
| SL | `outputs/week4/orca_smd_acetonitrile/SL` | 3 | 是 |
| SN | `outputs/week4/orca_smd_acetonitrile/SN` | 3 | 是 |
| TEGDME | `outputs/week4/orca_smd_acetonitrile/TEGDME` | 3 | 是 |
| TMP | `outputs/week4/orca_smd_acetonitrile/TMP` | 3 | 是 |
| VC | `outputs/week4/orca_smd_acetonitrile/VC` | 3 | 是 |

### 3.2 Part B：零新增作业（普查 + 覆盖 QC）

- 受影响格子：**32** 个（`delta_ev < -1 meV`），覆盖 5 个分子、2 个电荷态。
- 普查（`stage17_solution_identity.json` 的 `census`）：扫描 `outputs/week*/orca*/**/*.out` 共 **1051** 个文件，其中 **756** 个可解析为 C-PCM 臂输出；**36** 个 `(arm, 分子, 态, epsilon)` 键存在重复路径（共 36 条冗余路径，按最新周 / 最新 mtime 去重）。
- 覆盖 QC：**32/32** 每臂各唯一解析到一个 `.out`，未解析 0 个；两臂能量与 Stage 16 目录的最大偏差 `max_delta_ev_mismatch_vs_stage16 = 0 eV`（同源）。
- 按 (分子, 态) 拆开（逐格遍历 `stage17_solution_identity.csv`）：

| 分子 | 态 | 受影响格子数 |
| --- | --- | --- |
| DMC | cation | 1 |
| EC | cation | 5 |
| EMC | anion | 6 |
| PC | anion | 10 |
| TMP | cation | 10 |

受影响格子的能量差 `delta_ev` 落在 [-0.2860, -0.0015] eV，均值 -0.1199 eV（`aggregates.delta_ev`）。注意：Part B 的 32 格是 **Stage 16 CPCM 目录**（10 个电介质）里的格子，与 Part A 的 SMD(乙腈) 层不是同一批，
两部分的 `delta` 不能相加或混读。

## 4. Part A：污染上限（P1 -> P2 台阶的第 2 级，只换 P2 腿）

### 4.1 逐轴对照表（published / default / moread）

| 轴 | 臂 | n | tau_b | tau_b 95% CI | O_20% | f_unresolved(after) | f_robust_inv | sigma 中位(eV) | shift 均值(eV) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 氧化轴 | **published** | 18 | 0.895 | [0.714, 1.000] | 0.750 | 0.111 | 0.000 | 0.198 | -2.393 |
| 氧化轴 | default | 18 | 0.895 | [0.714, 1.000] | 0.750 | 0.111 | 0.000 | 0.198 | -2.393 |
| 氧化轴 | moread | 18 | 0.922 | [0.774, 1.000] | 0.750 | 0.111 | 0.000 | 0.188 | -2.401 |
| 还原轴 | **published** | 18 | 0.673 | [0.403, 0.873] | 0.500 | 0.222 | 0.000 | 0.217 | -2.173 |
| 还原轴 | default | 18 | 0.673 | [0.403, 0.873] | 0.500 | 0.222 | 0.000 | 0.217 | -2.173 |
| 还原轴 | moread | 18 | 0.673 | [0.413, 0.871] | 0.500 | 0.255 | 0.000 | 0.226 | -2.187 |

> 来源：`stage17_contamination.json` 的 `published_comparison.<轴>.published`（published 行）与 `per_axis.<轴>.<臂>`（default / moread 行）；published 行的原始出处是该 JSON 里 `published.source` 指向的 `outputs/week9/stage10_ladder.json`（`population=native`, `rung=P1_to_P2`）。

`O_20%` 两臂完全相同（ox 0.750/0.750，red 0.500/0.500）——也就是说，即使 `tau_b` 动了，**被选进 Top-20% 的那批分子一个都没换**。

### 4.2 moread - published 逐项 delta

| 轴 | Δtau_b | ΔO_20% | Δf_unresolved(after) | Δf_robust_inv | Δsigma 中位(eV) |
| --- | --- | --- | --- | --- | --- |
| 氧化轴 | +0.0261 | +0.0000 | +0.0000 | +0.0000 | -0.0099 |
| 还原轴 | +0.0000 | +0.0000 | +0.0327 | +0.0000 | +0.0093 |

> 来源：`stage17_contamination.json` 的 `published_comparison.<轴>.moread_minus_published`。

对照 `published_comparison.<轴>.default_minus_published`（全部为 0.0）可见：default 臂在逐项上都**精确复原**
了 published 值（`default_matches_published_max_abs_ev = 0` eV 氧化轴 / 0 eV 还原轴），所以 4.2 的每一列都只反映 moread 这一条腿。

### 4.3 delta = p2_moread - p2_default：统计与符号检验

| 粒度 | n | mean(eV) | std(eV) | min(eV) | max(eV) | argmin | argmax |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 54 格（分子 x 态） | 54 | -0.007224 | 0.035743 | -0.156165 | 0.092274 | TEGDME/anion | EC/anion |
| 18 分子（氧化轴） | 18 | -0.007368 | 0.031615 | -0.134039 | 0.001382 | TMP | DEC |
| 18 分子（还原轴） | 18 | -0.014300 | 0.053620 | -0.156162 | 0.092273 | TEGDME | EC |

> 来源：`stage17_contamination.json` 的 `delta_stats`（`definition` 字段原文：「delta = p2_moread - p2_default (eV)」）。

| 粒度 | 正 | 负 | 零 | 双侧 p | 单侧(正) p |
| --- | --- | --- | --- | --- | --- |
| 54 格（分子 x 态） | 22 | 32 | 0 | 0.220 | 0.933 |
| 18 分子（氧化轴） | 10 | 8 | 0 | 0.815 | 0.407 |
| 18 分子（还原轴） | 9 | 9 | 0 | 1.000 | 0.593 |

> 来源：`stage17_contamination.json` 的 `sign_test`（`side` 字段原文：「two_sided (primary) + one_sided_greater」，容差 `tolerance_ev = 1e-12`）。

主判据是 **54 格**那一行：正 22 / 负 32 / 零 0，双侧 p = 0.220——**moread 与 default 的差别在符号层面完全不显著**，这与「两臂在绝大多数格子上收敛到同一个解」一致。

### 4.4 改变的格子（|delta| > 1 meV）

共 **6** 个格子（判据 |delta| > 1 meV）：

| 分子 | 态 | delta(eV) | 所属轴 |
| --- | --- | --- | --- |
| TEGDME | anion | -0.156165 | reduction |
| TMP | cation | -0.134038 | oxidation |
| PC | anion | -0.118323 | reduction |
| EC | anion | +0.092274 | reduction |
| DEC | anion | -0.075211 | reduction |
| DEC | cation | +0.001381 | oxidation |

> 来源：`stage17_contamination.json` 的 `cells_changed`（`cells_changed_count` 与其长度一致，生成器断言）。

六个格里五个是 moread **更低**（`delta < 0`），只有 **EC / anion 是 +0.0923 eV**——moread 反而**更高**。这条正向残差必须原样保留：它说明
「读气相轨道当起点」并不是无条件更好，只是在本周这条台阶上不足以改写任何结论（4.5）。

### 4.5 哪些结论被改写：三个 scenario verdict 复核

产物判定：`any_published_conclusion_rewritten = False`，`tau_b_ci_overlap_both_axes = True`。
逐项「未被改写」的理由（`verdict.conclusions_unchanged` 原文）：

- oxidation: f_robust_inv stays 0.0 (unchanged)
- oxidation: tau_b moves by 0.026 (<= 0.05, unchanged)
- oxidation: Top-k overlap_20 moves by 0.000 (<= 0.10, unchanged)
- oxidation: f_unresolved(after) moves by 0.000 (<= 0.05, unchanged)
- reduction: f_robust_inv stays 0.0 (unchanged)
- reduction: tau_b moves by 0.000 (<= 0.05, unchanged)
- reduction: Top-k overlap_20 moves by 0.000 (<= 0.10, unchanged)
- reduction: f_unresolved(after) moves by 0.033 (<= 0.05, unchanged)

三个 scenario 的复核（`verdict.scenario_verdicts` 原文）：

- **B_large_shift_small_rank_damage**（原判：SUPPORTED）—— 复核依据：moread oxidation tau_b = 0.9215686274509803, O_20% = 0.75, f_robust_inv = 0.0
  复核结论：still SUPPORTED (large shift, stable ranking, low f_robust_inv)
- **C_structured_robust_inversion**（原判：NOT OBSERVED）—— 复核依据：moread f_robust_inv = 0.0 / 0.0 (oxidation / reduction)
  复核结论：still NOT OBSERVED (both arms keep f_robust_inv at 0)
- **A_cheap_proxy_already_stable**（原判：NOT SUPPORTED）—— 复核依据：A rests on the P0->P2 rung; here only the P2 leg of P1->P2 is swapped. moread tau_b(P1,P2) oxidation = 0.9215686274509803
  复核结论：the P1->P2 ordering barely moves, so A's P2-leg dependence is unaffected by the contamination

一句话：**没有任何一条 published 结论被改写**；B 仍 SUPPORTED、C 仍 NOT OBSERVED、
A 的 P2 腿依赖不受影响。

### 4.6 上限声明：CI 是否吸收污染

- **氧化轴**：default CI = [0.714, 1.000]，moread CI = [0.774, 1.000]，重叠 = 是
- **还原轴**：default CI = [0.403, 0.873]，moread CI = [0.413, 0.871]，重叠 = 是

> 来源：`stage17_contamination.json` 的 `ci_overlap`（`method` 字段原文：「Week 9 tau_b_interval: 20 frozen seeds x 2000 paired resamples, median of percentile bounds」）。

两个轴的两臂 CI 都重叠，因此本次单腿替换带来的位移**落在 Week 9 冻结的区间估计之内**——
这就是「污染上限」的确切含义：即便把这条腿换掉，`tau_b` 的不确定区间也不足以把它与 published 分开。

### 4.7 为什么 `f_robust_inv` 从 0 变非 0 在本项目的这条流水线、这批格子、这套估计量下是结构性不可能

`f_robust_inv` 的分子是「两臂都 resolved 且反号」的 pair 数。在 `P1 -> P2` 这类台阶上，`sigma_ij`
恰好由**两个 realization**（`P1` 与 `P2`）给出：

    sigma_ij = abs(d0_ij - d1_ij) / sqrt(2)          （d0 = P1 的 pair 差，d1 = P2 的 pair 差）

设某一对被判为「两臂都 resolved 且反号」，取 `d0 > 0 > d1`，则 `abs(d0 - d1) = abs(d0) + abs(d1)`，
于是 `sigma_ij = (abs(d0) + abs(d1)) / sqrt(2)`。两条 resolved 条件（`z_primary = 1.0`）各自展开：

    |d0| >= z * sigma   <=>   (sqrt(2) - 1) * |d0| >= |d1|
    |d1| >= z * sigma   <=>   (sqrt(2) - 1) * |d1| >= |d0|

两式相乘得 `|d0||d1| <= (sqrt(2) - 1)^2 |d0||d1|`，即要求 `1 <= (sqrt(2) - 1)^2`。
而 `(sqrt(2) - 1)^2 = 0.1716 < 1`——矛盾。所以**反号且两臂都 resolved 的 pair 集合恒为空集**，
`f_robust_inv` 在这种估计量下恒等于 0，与数据无关。

**先把适用范围写死（`docs/31` R6）。** 下面这段是**本项目的这条具体流水线、这批格子、这套估计量**的结构性质，**不是普适定理（not a universal theorem）**：它成立的前提恰好是 (a) `sigma_ij` 由**两条** realization 给出、(b) `z_primary = 1.0`。任一条改动都会解除这条不可能性 —— 届时必须重跑，不得把本条结论外推。

必须说清的两点：

1. 这是**估计量的结构性质**，不是「物理上不存在稳健反转」。它成立的前提是 (a) `z_primary = 1.0`、
   (b) `sigma` 恰好由两条 realization 给出。换 `z > 1`、换成 `ddof = 0` 的 `sigma`、或补进第三条
   realization，这条不可能性都会解除。因此本周的读法只能是：**在这次单腿替换下，`f_robust_inv` 的**
   **0 -> 非 0 翻转不可能发生**，而不是「污染不可能造成稳健反转」。
2. 这条不是「事后合理化」，它被两处独立钉住：(a) 生成器对四个 (轴, 臂) 组合的 `f_robust_inv` 与
   `f_robust_inv_z1p96` 全部 `assert` 为 0；(b) `_lemma_check()` 用 `outputs/week16/stage17_contamination_cells.csv` 的原始 `P1` / `P2(moread)` 向量把两轴的
   全部 18x18 pair 重算了一遍，断言「没有任何一对同时满足反号与两臂 resolved」。

## 5. Part B：两个 SCF 解的电子结构身份

本节的 32 个格子全部来自 Stage 16 CPCM 目录中 `delta_ev < -1 meV` 的配对格，
只读既有 `.out`，零新增作业。所有数字来自 `stage17_solution_identity.json`（聚合量）与
`stage17_solution_identity.csv`（逐格）。

### 5.1 自旋纯度 `<S^2>`

- 两臂 `<S^2>` 都落在 **0.75 ± 0.01** 的格子：**32/32**（都是自旋纯双重态，未与四重态混杂）。
- 均值：default = **0.753788**，moread = **0.753104**；两臂各自的范围 default [0.751100, 0.759675]、moread [0.750799, 0.758960]。
- `delta_s2` 范围 **[-0.004534, +0.001457]**，均值 -0.000684。
- 多重度：两臂在每个格子上都是 **2**（双重态），电荷取值 -1, 1（阳离子 / 阴离子），逐格一致。

> 来源：`stage17_solution_identity.json` 的 `aggregates.s2_default` / `s2_moread` / `delta_s2`；
> 逐格字段 `s2_default` / `s2_moread` / `mult_default` / `mult_moread` / `charge_default` /
> `charge_moread` 见 `stage17_solution_identity.csv`。

### 5.2 自旋中心与轨道标签

| 判据 | 一致格子数 | 拆分 |
| --- | --- | --- |
| 承载最大 \|Mulliken 自旋\| 的原子在两臂相同 | 21/32 | anion 16/16、cation 5/16 |
| reduced-orbital SPIN 子块最大 \|贡献\| 的原子-轨道标签相同 | 11/32 | anion 10/16、cation 1/16 |

> 来源：`stage17_solution_identity.json` 的 `by_state.anion` / `by_state.cation`（键 `n_same_spin_center`、`n_same_orbital_label`）；逐格布尔字段同名的见 CSV。

出现过的 `(default -> moread)` 轨道标签对（逐格遍历 `stage17_solution_identity.csv`，按首次出现排序）：

- `O4 pz -> O4 pz`
- `O2 pz -> O5 pz`
- `C3 py -> C3 s`
- `C4 s -> C4 s`
- `O1 py -> O3 px`

这 5 组标签里既有 `pz -> pz`（同通道），也有 `py -> s`、`s -> s`、`py -> px`（换通道）。
**不要在弥散基组下把它读成「就是 pi* 的 pz 通道」**——见 7.2 的口径纪律。

### 5.3 定域性（参与率 PR）

| 量 | default | moread | 差（moread - default） |
| --- | --- | --- | --- |
| 参与率 PR 均值 | 4.6665 | 4.4499 | -0.2165 |
| 最大原子自旋 `spin_max` 均值 | 0.7647 | 0.9785 | +0.2138 |
| n90（承载 90% 自旋所需原子数）均值 | 6.8125 | 6.5625 | -0.2500 |

> 来源：`stage17_solution_identity.json` 的 `aggregates.spin_pr_default` / `spin_pr_moread` /
> `spin_max_default` / `spin_max_moread` / `spin_n90_default` / `spin_n90_moread` / `loss_in_pr`
> （`loss_in_pr = PR_moread - PR_default`，**正 = moread 解更离域**）。

- `loss_in_pr > 0` 的格子：**11/32**；`< 0` 的格子：21/32。
- `loss_in_pr` 均值 **-0.2165**，范围 [-0.9261, +0.7656]。
- `spin_max` 从 0.7647 抬到 **0.9785**：moread 解把自旋**更集中**堆在少数原子上，但整体 PR 反而更低——两者并不矛盾：
PR 描述的是全部分布的「有效参与原子数」，`spin_max` 只描述最大的那一个。

### 5.4 电荷重组（Mulliken 逐原子 L1 差）

- `charge_l1`：均值 **0.9826**，范围 [0.0394, 3.1386]。
- `spin_l1`：均值 **0.9537**，范围 [0.0391, 2.4061]。

> 来源：`stage17_solution_identity.json` 的 `aggregates.charge_l1` / `aggregates.spin_l1`；
> 逐格 `charge_l1` / `spin_l1` 见 `stage17_solution_identity.csv`。

`charge_l1` 与 `spin_l1` 量级相当，说明两个解之间**电荷在动**，不只是自旋在换位置。

### 5.5 按电荷态

| 态 | 格子 | Δ<S^2> 均值 | loss_in_pr 均值 | charge_l1 均值 | spin_l1 均值 | 自旋中心相同 | 轨道标签相同 | 分子 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| anion | 16 | -0.001792 | -0.3878 | 1.7267 | 1.4327 | 16/16 | 10/16 | EMC, PC |
| cation | 16 | +0.000424 | -0.0453 | 0.2384 | 0.4747 | 5/16 | 1/16 | DMC, EC, TMP |

> 来源：`stage17_solution_identity.json` 的 `by_state.anion` / `by_state.cation`。

对比很干净：阴离子的自旋中心在两臂**完全一致**（16/16），阳离子只有 5/16；而且阴离子的 `loss_in_pr`（-0.3878）比阳离子（-0.0453）更负，`charge_l1` 也大一个量级。

### 5.6 按分子家族

| 家族 | 格子 | 分子 | loss_in_pr 均值 | charge_l1 均值 | 自旋中心相同 | 轨道标签相同 |
| --- | --- | --- | --- | --- | --- | --- |
| cyclic_carbonate | 15 | EC, PC | -0.5025 | 0.6689 | 15/15 | 10/15 |
| linear_carbonate | 7 | DMC, EMC | +0.4034 | 2.5862 | 6/7 | 1/7 |
| phosphate | 10 | TMP | -0.2215 | 0.3305 | 0/10 | 0/10 |

> 来源：`stage17_solution_identity.json` 的 `by_family.cyclic_carbonate` / `linear_carbonate` / `phosphate`。

家族分裂比电荷态更锋利：cyclic_carbonate 的 `loss_in_pr` = **-0.503**（moread 更定域）而 linear_carbonate = **+0.403**（moread 更离域），两条方向相反；linear 的 `charge_l1` = 2.586，是 cyclic（0.669）的约 3.9 倍。TMP（phosphate）的自旋中心 0/10 全部翻转，
原因见 6(iv) 与 9.4——那是近简并表观，不是稳健判据。

### 5.7 几何 QC

- 两臂 `CARTESIAN COORDINATES (ANGSTROEM)` 逐位相同的格子：**32/32**。

> 来源：`stage17_solution_identity.csv` 的 `geometry_identical` 列（逐格）；
> 按态/家族汇总见 `stage17_solution_identity.json` 的 `by_state.*.n_geometry_identical` 与
> `by_family.*.n_geometry_identical`。

这条 QC 的意义：`.out` 里的两臂坐标完全相同，所以 5.1–5.4 的差异**只能来自 SCF 解本身**，
不是几何松弛走了另一条路径。

## 6. 物理读法

**(i) 这不是破缺对称性伪影。** 两个解都是自旋纯双重态（5.1，32/32 落在 0.75±0.01），多重度都是 2。所以它们**不是**同一个态在 UKS 下的自旋污染产物，而是**同一自旋量子数下的
两个不同 SCF 驻点**——能量不同、电子结构不同，但都是合法的双重态。这句话把「漏解」从一个「收敛
问题」升级成了「解的多重性」问题。

**(ii) 空穴比电子更难安放。** 阴离子的自旋中心在两臂完全一致（16/16），阳离子只有 5/16。也就是说：**默认初猜倾向把多余电子放在哪里基本是可复现的，
而它倾向把空穴放在哪里则高度依赖初猜**。这与 Week 15 §7.2 的机制一致——阳离子的近简并让 SCF
更容易落进不同分支，而阴离子的自旋在缺弥散基组下被迫定域到一个可预判的位点。

**(iii) 差异的主轴是电荷重组，不只是自旋重排。** `charge_l1` 均值 0.983
与 `spin_l1` 均值 0.954 同量级，但家族之间的分裂出现在电荷上：linear_carbonate 的
`charge_l1` = 2.586，是 cyclic_carbonate（0.669）的 **3.9 倍**（5.6）。
换句话说，「第二条解」在这两个家族里差别最大的不是自旋往哪跑，而是**电荷整体怎么重新分配**。

**(iv) TMP 的翻转是近简并表观，不能当判据。** TMP（phosphate）的自旋几乎均摊在三个磷酸氧上（`spin_max` 均值仅 0.2297 vs 0.3302，远低于全体两臂均值 0.7647 / 0.9785），
三个氧近简并，所以「哪个氧承载最大自旋」在两臂之间翻转（0/10 一致）几乎是投硬币的结果，
**不能读成「TMP 的解身份不稳定」**。这一条写进 9.4 的限制里。

## 7. 读法纪律（延续 Week 9 §10 / 10 §11 / 11 §11 / 12 §10 / 13 §11 / 14 §9 / 15 §8）

1. **Part A 是单腿敏感性，不是整条台阶的重算。** 本周只换了 `P1 -> P2` 的 **P2 腿**；`P1` 值、几何、
   方法层与其余四级台阶都没动（2.3）。所以结论只能写成「这条腿的初猜不足以改写已发布结论」，
   **不能**写成「整条台阶经得起重算」或「所有台阶都安全」。
2. **判「未成对电子主贡献轨道」用的是 reduced-orbital SPIN 子块里 |值| 最大的原子-轨道；
   在弥散基组下该最大值常落在弥散 s 通道而不是 pi* 的 pz 通道。** 这句话是产物 `stage17_solution_identity_summary.md` §8 的**原文**，本报告**不许把它简化成「就是 pi*」**；
   5.2 的两组 `py -> s` / `s -> s` 标签对就是这条口径的直接证据。
3. **`f_robust_inv = 0` 是估计量的结构性质，不是物理结论。** 两 realization + `z_primary = 1.0` 下
   「反号且两臂都 resolved」恒为空集（4.7）；报告里必须把「不可能翻转」的**前提**一起写出，
   否则会被误读成「物理上不存在稳健反转」。
4. **近简并造成的「中心翻转」不是身份判据。** TMP 的 0/10 一致来自三个磷酸氧的近简并（6(iv)），
   与 EC/PC 那种「自旋真的换了位点」不是同一件事；报告里把两者分开写，不让 0/10 拉低整体结论。
5. **样本小就把不确定性写在脸上。** Part B 只有 32 格、5 个分子、2 个态；家族结论每个家族只有 1–2 个
   分子（cyclic 2 个、linear 2 个、phosphate 1 个），只能当作**机制提示**，不能当作发生率估计。
6. **复用与只读都要留出处。** Part A 的 default 臂不是重算的，而是从 Week 4 参照表原样读入；
   Part B 的每一个 `.out` 路径都记在 `stage17_solution_identity.csv` 的 `default_path` / `moread_path` 列里，
   去重规则（按最新周 / 最新 mtime）写在 `census` 里。

## 8. 产物与图表

### 8.1 数据产物（`outputs/week16/`）

| 文件 | 说明 |
| --- | --- |
| `stage17_contamination.json` | Part A 的全部产物（逐轴对照 / delta_stats / 符号检验 / scenario verdict / CI 重叠） |
| `stage17_contamination_cells.csv` | Part A 逐分子表（P1 与两臂 P2 的原始能量、逐态 delta） |
| `stage17_contamination_ladder.csv` | Part A 四行 (臂, 轴) 指标表（含 published 列与 delta 列） |
| `stage17_contamination_summary.md` | Part A 的中文小结（§4 的口径对照） |
| `stage17_smd_moread.json` | Part A 计算台账 + G1 几何审计 + 初猜协议原文 |
| `stage17_smd_moread_plan.json` | Part A 运行前的作业计划（18 分子 x 3 态） |
| `stage17_solution_identity.csv` | Part B 逐格表（两臂 `.out` 路径、<S^2>、自旋中心、PR、L1、几何 QC） |
| `stage17_solution_identity.json` | Part B 全部聚合产物（census / by_state / by_family / aggregates） |
| `stage17_solution_identity_by_molecule.csv` | Part B 按 (分子, 态) 汇总表 |
| `stage17_solution_identity_summary.md` | Part B 中文小结（§8 含主贡献轨道口径原文） |

另有 Part A 的原始作业目录 `outputs/week16/orca_moread_smd_acetonitrile/`（18 个分子子目录，每个 3 态；`.inp` / `.out` / `.xyz`；`.gbw` 不入库），以及 2 个 `p2_*` 原始表（`p2_core_set_moread_smd_acetonitrile.csv` + `p2_summary_moread_smd_acetonitrile.json`）。

### 8.2 图表

![F32](outputs/figures/F32_stage17_contamination.png)

`outputs/figures/F32_stage17_contamination.png` —— Stage 17 Part A（污染上限），三块面板：
(a) 18 分子 x 2 轴的 `delta = p2_moread - p2_default`，参考带 = 材料阈值 1 meV（最坏 |delta| = 0.1562 eV，TEGDME/anion；唯一的大正残差是 EC/anion +0.0923 eV）；
(b) 排序稳定性对照（两轴两臂的 `tau_b` 与 95% CI，两轴 CI 重叠）；
(c) 决策量 default vs moread（`O_20%` / `f_unresolved(after)` / `f_robust_inv` / `sigma 中位`）与 6 个超阈值格子。本报告 §4 是它的逐数 companion。

![F33](outputs/figures/F33_stage17_solution_identity.png)

`outputs/figures/F33_stage17_solution_identity.png` —— Stage 17 Part B（两个 SCF 解的电子结构身份），四块面板：
(d) 代表性逐原子自旋剖面（PC / anion / cpcm_10）；
(e) 三个家族的 `loss_in_pr` 均值（与 5.6 同源）；
(f) 32 格的 Δ`<S^2>`（参考线 = 纯双重态 0.75）；
(g) 三个家族的 `charge_l1` vs `spin_l1`。本报告 §5 是它的逐数 companion。

- 面板组成的权威说明、两张 PNG 的 SHA256 与输入产物哈希：`outputs/figures/figure_manifest_week16_stage17.md`。

### 8.3 脚本与测试

- `scripts/run_stage17_smd_moread.py`：Part A 的 54 格作业调度与台账（几何审计、初猜协议、`--jobs/--nprocs`）。
- `scripts/analyze_stage17_contamination.py`：Part A 分析（逐轴对照、delta_stats、符号检验、scenario verdict、CI 重叠）。
- `scripts/analyze_stage17_solution_identity.py`：Part B 分析（普查、两臂 `.out` 配对、`<S^2>` / 自旋中心 / PR / L1 聚合）。
- `scripts/gen_week16_report.py`：本报告的生成器（本节全部数字的唯一出处）。
- 图表与清单（`outputs/figures/F32_stage17_contamination.png`、`outputs/figures/F33_stage17_solution_identity.png`、`outputs/figures/figure_manifest_week16_stage17.md`）由 `scripts/make_stage17_figure.py` 生成，
  后者把两张 PNG 的 SHA256 与输入产物的哈希一并写进清单。

## 9. 已知限制

1. **Part A 只在 native 18 分子的 SMD(乙腈) P2 层上做单腿替换**：它不是整条台阶的重算，
   也没有覆盖 common-10 的其它台阶或别的环境层（2.3）。因此「污染上限」这句话的作用域就是这一条腿。
2. **`f_robust_inv ≡ 0` 是估计量的结构后果，不是物理结论**：它依赖 `z_primary = 1.0` 与「`sigma` 恰好由
   两条 realization 给出」（4.7）。换 `ddof`、补第三条 realization 或抬高 `z`，这条结论都会改变。
3. **Part B 只有 32 格、5 个分子、2 个电荷态**，判据 `delta_ev < -1 meV`
   继承自 Stage 16，本周未重标定；家族结论每个家族只有 1–2 个分子，只能当**机制提示**。
4. **TMP 的自旋近简并**：三个磷酸氧上的自旋几乎均摊，所以「哪个氧承载最大自旋」的 0/10 翻转是
   **近简并表观**，不能当作稳健判据（6(iv)）。
5. **「主贡献轨道」的口径是 reduced-orbital SPIN 子块里 |值| 最大的原子-轨道**；在弥散基组下该最大值常落在
   弥散 s 通道而不是 pi* 的 pz 通道。因此 5.2 的「轨道标签相同 11/32」**不能**读成「pi* 身份相同」。
6. **Part B 是纯读既有输出，没有做结构表征**：没有比较键长、自然轨道占据数、能量分解，也没有比较
   两解的振动或自由能。本周回答的是「两个解在 Mulliken 自旋/电荷与参与率上差多少」，不是「为什么」。
7. **`delta` 是垂直能量差**（同几何、同方法、同电荷态），不是自由能，也没有构型采样。
8. **冗余路径去重只按「最新周 / 最新 mtime」**：36 条冗余路径说明历史上多次重算过同一
   `(arm, 分子, 态, epsilon)` 键；本周选中的那一个不保证是最科学的那个，只保证是最新的。

## 10. 下一步（Week 17 候选）

按「先堵漏、再扩张」排序，并逐条标明是否需要新作业：

1. **（零新增计算）把单腿替换推广成「逐腿敏感性表」**：对五级台阶的每一条腿，列出「这条腿若换
   moread，会不会改写 tau_b / Top-k / 清单」。P0_to_P1、G1_to_G2、C0_to_C1、C1_to_C2 的更多臂能量
   大多已在 Stage 16 的 CPCM moread 目录里，可以**先纯读筛查**，只把真正会动的格子标出来。
2. **（零新增计算）把 Part B 的三条身份判据回填到 Stage 16 的全目录上**：检验「哪些
   (分子, 态, epsilon) 的漏解会伴随自旋中心翻转 / 大 `charge_l1` / 大 `loss_in_pr`」。
   如果三者能预测漏解，就得到一个**不必读 `.out`** 的事前筛查量。
3. **（需要新作业）真正的 out-of-sample 扩张**：把 moread 协议推广到 broad pool 的 40 个分子阴离子
   （Week 15 §11 第 2 条仍未做）。这是对整套协议唯一有意义的样本外检验。
4. **（需要新作业，但更便宜）用 GFN2-xTB 初猜**（Week 15 §11 第 3 条）：检验「读 xTB 轨道」能否拿到
   同样低的解，把一次气相 DFT 降成一次 xTB；若能，预警与修复的成本同时下降。
5. **（需要新作业）把 TMP 的近简并做实**：对 TMP 做指定初猜 / 更严格 SCF 收敛的定点计算，看三个
   磷酸氧的简并是否被打破——这决定 6(iv) 的「近简并表观」是否真的只是表观。

