# Week 14 小结 —— Stage 15：双初猜协议、电子弥散度描述符与文献锚点扫描

本文件是 `F28_two_guess_protocol.png` 与 `F29_diffuseness_descriptor.png`
的文字 companion。所有数字都由 `outputs/week14/stage15_two_guess_analysis.json`、
`outputs/week14/stage15_diffuseness.json` 与 `outputs/week14/stage15_anchor_scan.json`
读出，不手抄。完整推导、物理读法与需裁决项见 `docs/24_week14_report.md`。

---

## 0. 一句话结论

Week 13 留下一个「已知但未解释」的 EMC 离群点、一个**否定性**归因结果，
以及一个一直没被真正回答的 Gate 1 blocker。本周三件一起处理：

1. **「解不唯一」升级为「初猜选错」，并且修好了**。90 个「分子 x 态 x 介电」点里
   78 个在收敛精度内一致，**12 个差值超过 1 meV 且全部为负**，
   反向 **0 次**。最大惩罚 **0.2860 eV**（EMC 阴离子，`eps = 1000`）。
   EMC 还原轴九点 Born `R^2` **0.6788 -> 0.9556**，符号变化 **4 -> 0**，
   偶极粗糙度 **1.99 -> 0.08**，修复后偶极严格单调（`rho = +1.000`）。
2. **导体极限从外推变实测**。`eps = 1000`（`x = 0.999`）实测 `delta = 2.5449 eV`，
   与 `eps = 200` 只差 **11.3 meV**；而六点口径下 `eps = 200` 距极限 **+33.2 meV**
   （逐位复现 Week 12 的 worst case），修复后变成 **-30.8 meV**。
   缺口**没有变小** —— 所以修掉的是解选择伪影，不是 Born 形式的偏差。
3. **Stage 14 的否定结果被翻正**。从六层 bare-CPCM 的 Mulliken 自旋布居构造
   7 个弥散度描述符（**0 个新作业**），阴离子畸变惩罚 `D_anion` 的最佳留一
   `R^2` 从 **0.162 升到 0.556**（`spin_maxfrac`，`rho = +0.811`，`p = 0.0014`），
   中位数口径 **0.630**，配对最好 **0.647**。
   中性与阳离子最优描述符**完全不变**（0.634 / 0.071，`delta_loo = 0`）。
4. **溶液锚点从「还缺数据」变成「可核查的否证」**。13 篇 PDF 全部可读，
   但与审计表引用的 7 个 DOI 只有 **1 个**交集；31 行里 11 行引它、
   只有 **4 行**的引用集合完全在手，因此 4 行可裁定：**3 改 1 确认**。
   **Gate 1 仍是 NOT CLOSED，31 行仍为 `est`**，但理由现在是可核验的。

---

## 1. Part A：双初猜协议（`F28_two_guess_protocol.png`）

**F28 面板 (a)** —— 90 个点里 78 个给出同一个能量（到 SCF 收敛精度）。
幅度直方图（阈值 -> 超阈点数）：`1e-08: 90, 1e-07: 86, 1e-06: 72, 1e-05: 27,
1e-04: 16, 1e-03: 12, 1e-02: 7, 1e-01: 6`。
所以 `material` 阈值定在 `1e-03 eV`：其上是 **12 个点**，且**全部为负**
（`E_moread - E_default < 0`，默认初猜停在的一个更高能量的解上）。
反向点数为 **0**；噪声带内最大值 **8.3e-04 eV**；最大惩罚 **0.2860 eV**。
受影响：`DMC / EC / EMC`，态 `anion / cation`。

**F28 面板 (b)** —— 偶极跟着能量一起动，而且是在**两个分支之间**动。
EMC 默认初猜的偶极在九点阶梯上跨度 4.65 D、粗糙度 **1.99**；
从气相 MO 重启后塌到 1.54 D 跨度、粗糙度 **0.08**。
失败集 `{5, 20, 40, 80, 200, 1000}` 与成功集 `{7, 10, 14, 28}` **交错** ——
所以这不是「大介电才出错」的单调故事，而是两个 SCF 解的吸引域交错。

**F28 面板 (c)** —— Born 横坐标是 `1 - 1/eps`，所以**拟合斜率本身就是
`eps -> infinity` 的外推极限**。`eps = 1000` 对应 `x = 0.999`，
是第一个把横坐标推到极限千分之一的实测点。

**F28 面板 (d) 数字** ——

| 口径 | 默认初猜 | MORead |
| --- | --- | --- |
| 六点斜率 | 2.5668 | 2.7848 |
| 六点斜率下 `eps = 200` 缺口 | **+33.2 meV** | **-30.8 meV** |
| 九点斜率 | 2.6304 | 2.7778 |
| `delta(200)` | 2.5335 | 2.8157 |
| `delta(1000)` | 2.5449 | 2.8308 |
| 外推误差 @200 | -96.9 meV | +37.8 meV |
| 外推误差 @1000 | -85.6 meV | +53.0 meV |
| 200 -> 1000 位移 | **11.3 meV** | 15.1 meV |

**Stage 14 数字的复现** —— 六点 Born `R^2` 0.8468、九点 0.6788、符号变化 4。
Stage 14 公布的是 0.8468 / 0.6788 / 4，所以重启实验确实是拿同一根曲线做对比。

---

## 2. Part B：电子弥散度描述符（`F29_diffuseness_descriptor.png`）

**F29 面板 (e)** —— 多加进去的电子的空间摊开程度取自阴离子输出的
`MULLIKEN ATOMIC CHARGES AND SPIN POPULATIONS` 块，对六层 bare-CPCM 取平均。
单原子集中度 `spin_maxfrac` 预测还原轴惩罚：`rho = +0.811`、留一 `R^2 = 0.556`，
对照 Stage 14 最好的描述符 `mu_anion_smd_acn_debye` 的 0.162。

**F29 面板 (f)** —— 逆参与比 `spin_participation` 的**秩**信号更强
（`rho = -0.846`），但严重非线性：直线拟合的留一 `R^2 = -2.90`。
只报秩统计会严重误导 —— 这就是两个统计量都要画出来的理由。

**F29 面板 (g)** —— 每个目标的最佳描述符留一 `R^2`：
`D_neutral` 不变 0.634（它的 Stage 14 冠军仍是最好的）、
`D_cation` 停在 0.071、`D_anion` 从 0.162 升到 **0.556**。

**F29 面板 (h)** —— 描述符**自己的**有效性检验。自旋布居是归一化的
（72 行里最坏 `|sum s - 1| = 3.0e-06`、最坏 `|sum q + 1| = 3.0e-06`）。
Mulliken 自旋是**有符号**的，所以 `max |s_i| > 1` 是自旋极化的标志、
**不是**「阴离子不束缚」。只有**一个**层偏离其分子自身中位数 20% 以上：
**EMC/cpcm_10**（`sum |s| = 2.799`，是其自身中位数 1.061 的 **2.64 倍**，
同层 `spin_maxfrac` 从 ~0.747 跳到 1.737、`spin_participation` 从 ~1.70 掉到 0.308）。
这正是 Part A 能量筛查（**完全不用能量**）命中的同一个层 ——
两条互不依赖的线索互相印证，所以这是交叉检验、不是循环论证。

**气相排除** —— 在任何计算之前就排除了：AN 的气相自旋落在六层张成的域之外，
拿它当描述符就是外推。`n_available = 12` / `n_inside_domain = 11`。

---

## 3. Part C：溶液锚点文献扫描

- 语料：13 篇 PDF（`分支a-d` 7 篇 + `新建文件夹` 6 篇），全部可读。
- 审计表引用 7 个 DOI，语料里**只有 1 个在手**：`10.1016/j.coelec.2018.10.015`
  （Borodin 2019，`M5-Borodin-2019-electrolyte-stability-window.pdf`）。
- 31 行中 11 行引用它，只有 **4 行**的引用集合完全在手。

| 行 | 物种 | 性质 | 裁定 |
| --- | --- | --- | --- |
| 14 | DMSO | 还原 | `review_trend_only` -> `source_does_not_cover_species` |
| 15 | AN | 还原 | `review_trend_only` -> `source_does_not_provide_value` |
| 25 | DOL | 氧化 | `review_trend_only` -> `source_does_not_cover_species` |
| 24 | DME | 氧化 | **确认** `review_trend_only`（唯一的数是 +0.5–1.0 V 的**增强量**）|

`n_corrections_adopted = 3`、`confirmed_rows = ["24"]`、
`n_upgrades_meeting_conditions = 0`、`n_rows_still_est_after_scan = 31`、
`gate1_status = "NOT CLOSED"`。

3 条修正**不写回**冻结表 `outputs/week2/solution_anchor_audit.csv`，
以 overlay `outputs/week14/stage15_anchor_corrections.csv` 作为 correction of record。

---

## 4. 产物清单（`outputs/week14/`）

| 产物 | 内容 |
| --- | --- |
| `stage15_two_guess.json` | 99 作业运行记录（`failures = 0`、`jobs = 2`、`nprocs = 8`）|
| `stage15_two_guess_analysis.json` | Part A 全部分析 |
| `stage15_two_guess_energy.csv` / `_dipole.csv` | 90 点双协议能量 / 偶极 |
| `stage15_diffuseness.json` | Part B 描述符、域检验、判决、配对搜索 |
| `stage15_diffuseness.csv` / `_by_molecule.csv` | 72 行逐层 / 12 行逐分子 |
| `stage15_anchor_scan.json` / `.csv` | Part C 语料、DOI 交集、31 行裁定 |
| `stage15_anchor_corrections.csv` | 3 条修正的 overlay |
| `orca_cpcm_1000/` + `orca_moread_cpcm_*/` | 99 个 `.out`（每个同时留 `.gbw` `.xyz`）|
| `p2_core_set_*.csv` / `p2_summary_*.json` | 12 层能量表与逐层汇总 |

图表：`outputs/figures/F28_two_guess_protocol.png`、`F29_diffuseness_descriptor.png`、
`figure_manifest_week14_stage15.md`（含 2 张图与 4 个输入产物的 SHA256）。
调色板与 dpi 沿用其他周（`dpi = 160`，`bbox_inches = tight`）。

---

## 5. Gate 状态

`Gate 0 CLOSED; Gate 1 NOT CLOSED`。唯一 blocker 仍是审计表 31 行全部为
`method = est`（需要外部一手数据）。本周的净贡献是把这个 blocker 的性质
从「还没找到」精确化成「审计表引用的 7 个来源里 6 个不在手，
而唯一在手的那篇恰好不含这些物种」。