# 图形证据核查报告（agent3）

- 核查日期：2026-10-02
- 核查对象：结题论文成品页位图 `pw_01.png` … `pw_14.png`（14 页）+ 原始图形资产 `电解液溶剂HB-Code\outputs\figures\*.png`
- 方法：**逐张用 view_image 打开看过**，不按文件名推断；另用 `_pagemeta_w22.json`（每页文本块坐标）与 `_fulltext_w22.txt`（文本层）做交叉验证。凡写"分辨率不足以判读"处即为确实看不清。

## 裁决速览

| # | 评审意见 | 判定 | 一句话依据 |
|---|---|---|---|
| 1 | 页眉是乱码的自动抓取字符串 | **未复现（页眉）/ 复现（病灶）** | 14 页页眉逐页均为正常模板串 `WHU 2023 级 基础化学实验 研究性实验`；但评审引用的三串文本确实存在于 PDF 中——它们是**图内英文工作标题**（含 F 编号），排在版心首行 |
| 2 | 图 1 图注与图内标签对不上 | **复现** | 图内只有 P0 / P1 / P2 / C1 / decision stability 五个框；图注的"排序变化量／机理归因"两段在图内无对应标签 |
| 3 | 图 3 存在 MAE 2.92 eV 且 τb = 1.000 的点 | **复现** | 橙色数据点标签原文 `dSCF vertical EA (MAE 2.92 eV, tau_b 1.000)` |
| 4 | 图 9(a) P0→P1 氧化轴是 0.60、表 2 是 0.673 | **部分复现** | 图 9(a) 该行读到两个值：`0.73`（橙 = 氧化）与 `0.60`（蓝 = 还原）；表 2 为 0.673 / 0.595。不一致存在，但 0.60 是**还原**那条，不是氧化 |
| 5 | 图 11 图内标题写 "six dielectrics" | **复现** | 图内总标题 `F24 the dielectric ladder, measured to eps = 200`；panel (a) 副标题 `six dielectrics: every curve is a straight line through 0`；图注写"七级阶梯"；正文 §3.8 写"10 个介电点" |
| 6 | 图 10(d) 是 9 个预测子的单变量 AUC，signed-slope p = 0.008 | **复现** | F20 panel (d) 恰有 9 根条；`ols_slope_b = 1.000 (p=0.008)`。**但 F31 不是这张图**（见 §6） |
| 7 | F28 panel (a) 的样本点数 90 还是 360 | **部分复现** | 资产 panel (a) 是 vs ε 的折线（9 条系列 × 10 个 ε = 90 点），360 是全普查数、并未画进 panel；(a) 横轴标签原文 `dielectric constant  eps` |

---

## 1. 页眉乱码

**评审原话**：多页运行页眉显示损坏的自动抓取字符串（如 "F24 the dielectric ladder, measured to eps = 200"、含 "orbita al" 的那条、"45 R8: prcinq t"）。看起来是把图片内部标题/文件名错误地送进了页眉且字体子集损坏。

**我看到的**：

1. 14 页全部逐页打开。**每一页最上方都是同一条正常的模板运行页眉**，原文逐字为：`WHU 2023 级 基础化学实验 研究性实验`（页面顶部居中，其下一条横线）。首页、偶数页、奇数页都一样，**没有任何 F 编号、英文句子或乱码字符出现**。
2. 评审引用的三串文本我在 PDF 里都找到了，但它们**不在页眉，而在"图内英文工作标题"**，且这些图恰好是所在页版心的第一行文字（因为那几页正文从图开始）：
   - `F24 the dielectric ladder, measured to eps = 200` —— 图 11 的**图内总标题**，与资产 `F24_dielectric_limit.png` 的 suptitle **逐字一致**。该页（第 11 页）版心第一行就是它。
   - `F45 R8: pricing the targeted two-guess -- the allowance is sound, but it buys almost nothing; the Top-k variant is what really saves work` —— 图 12 的**图内总标题**（资产 `F45_targeted_two_guess.png` 逐字一致）。评审写的 "45 R8: prcinq t" 与其中 "pricing" 被撕裂成 "prcinq t" 完全对应；同样位于第 12 页版心首行。
   - `Reduction axis: the cheap orbital proxy is not even qualitatively right` —— 图 5 的图内总标题（资产 `F5_reduction_axis_koopmans_vs_dscf.png` 逐字一致），位于第 6 页版心首行。评审记的 "orbita al" 即 "orbital" 被断行/字体撕裂后的形态。
3. 文本层交叉证据：`_pagemeta_w22.json` 里每一页的 `top` 字段（= 该页最上方文字块）分别为——p2 `targeted two-guess reruns miss zero flips out of 660 pairs per axis…`、p3 `图1项目五段式流水线：廉价代理→经验证目标→`、p4 `为检查基组对EA的影响…`、p5 `图3值误差与排序误差的分离…`、p11 `图11介电极限：(a)七级阶梯对u = 1−1/ε`…… 也就是说，**任何按"取每页第一行"当作页眉的抽取流程，都会得到这类图题/正文串**，与评审描述的现象一致。

**判定**：**未复现**"页眉损坏"这一现象本身（模板页眉逐页正常、无乱码）；但评审描述的"自动抓取字符串"**来源已复现**——是**图内英文工作标题（含 F 编号）被直接排进版心首行**，字符撕裂（`prcinq t`、`orbita al`）属字体子集/断行在抽取侧的二次损伤。
**修法建议**：删除所有图内 F 编号与英文工作标题（图题只保留中文图注）；若模板要求运行页眉，须在图层面明确区分 header 与 body，避免首行被误判。

**证据文件**：`E:\Claude Code\电解液溶剂-HB\论文\_dossier\pw_01.png` … `pw_14.png`（14 张逐一打开）；`...\电解液溶剂HB-Code\outputs\figures\F24_dielectric_limit.png`、`F45_targeted_two_guess.png`、`F5_reduction_axis_koopmans_vs_dscf.png`；`...\论文\_dossier\_pagemeta_w22.json`、`_fulltext_w22.txt`。

---

## 2. 图 1（F0）图注与图内标签

**评审原话**：图 1 图注（"五段式流水线：廉价代理→经验证目标→…"）与图内文字（P0/P2/C1 标签）对不上。

**我看到的**（资产 `F0_project_pipeline.png` 全分辨率 + 第 3 页渲染一致）：

- 图内总标题：`What changes the MATERIALS DECISION, and by which physical mechanism?`
- 五个方框，从左到右依次为：
  1. `P0 cheap proxy` / `GFN2-xTB HOMO/LUMO`
  2. `P1 validated target` / `r2SCAN-3c gas redox`
  3. `P2 env. target` / `continuum eps scan`
  4. `C1 conditional species` / `Li+ coordination`
  5. `decision stability` / `top-k / robust inversion`
- 图底部斜体一行：`model complexity != accuracy != physical representativeness != materials decision`
- 图注（第 3 页）原文：`图 1 项目五段式流水线：廉价代理→经验证目标→排序变化量→机理归因→最小信息预算`

对照：段 1 `廉价代理` = P0 ✓；段 2 `经验证目标` = P1 ✓；段 3 `排序变化量` ≠ 图内 P2（`env. target / continuum eps scan`）；段 4 `机理归因` ≠ 图内 C1（`conditional species / Li+ coordination`）；段 5 `最小信息预算` ≈ 图内 `decision stability`（语义相近，但不是同一措辞）。

**判定**：**复现**（图注的五段切分与图内五个框的语义切分不是同一套：图注按"研究步骤"命名，图内按"计算层级 P0/P1/P2/C1/决策"命名，第 3、4 段直接对不上）。

**证据文件**：`...\电解液溶剂HB-Code\outputs\figures\F0_project_pipeline.png`；`...\论文\_dossier\pw_03.png`。

---

## 3. 图 3（F3）的 MAE 2.92 eV / τb = 1.000 点

**评审原话**：图 3 里那个 "dSCF vertical EA（MAE 2.92 eV, τb = 1.000）"的完美点必须交代清楚。

**我看到的**（资产 `F3_value_error_vs_rank_error.png` 全分辨率；与第 5 页渲染一致）：

- 左图标题：`Value error vs ranking error (n=12 molecules with an anchor)`
- 横轴：`mean absolute error vs anchor (eV)  ->  worse VALUE`（0–5）；纵轴：`Kendall tau_b vs anchor ranking -> worse RANKING`（0–1）
- 图上共 **5 个数据点**（含一个深绿与青色几乎重叠的点，位于 x≈0.25），旁注原文：
  1. 橙色，x≈2.92 / y=1.000：`dSCF vertical EA (MAE 2.92 eV, tau_b 1.000)` ← **评审指认的点存在**
  2. 蓝色，x≈4.45 / y=0.911：`dSCF vertical IP (P1-like) (MAE 4.45 eV, tau_b 0.911)`
  3. 深灰，x≈1.32 / y=0.689：`IP_koopmans_p0 (MAE 1.32 eV, tau_b 0.689)`
  4. 青色，x≈0.25 / y=0.727：`r2SCAN-3c dSCF vertical IP (P1) (MAE 0.25 eV, tau_b 0.727)`
  5. 绿色，x≈0.25 / y≈0.727：无独立标签（与 4 重叠）
- 右图标题：`A nearly constant offset keeps the RANKING intact`，y = `computed - anchor (eV)`，基线为 xtb mean bias 4.45 eV（±1 sd 0.34 eV），只画了 `GFN2-xTB dSCF vertical IP error` 与 `r2SCAN-3c dSCF vertical IP error` 两组柱。

注意：**该点标签本身不含层级前缀**（只写 "dSCF vertical EA"），既没有写 P0/P1/P2，也没写锚点是实验还是计算值——这正是评审 A5 要求"交代清楚"的地方。

**判定**：**复现**（点存在、确实是 MAE 2.92 eV 且 τb = 1.000；标签文字确为 `dSCF vertical EA`，且**未标注层级与锚点来源**）。

**证据文件**：`...\电解液溶剂HB-Code\outputs\figures\F3_value_error_vs_rank_error.png`；`...\论文\_dossier\pw_05.png`。

---

## 4. 图 9（F19）P0→P1 氧化轴的坐标

**评审原话**：表 2 的 P0→P1 氧化 τb = 0.673，图 9(a) 同台阶是 0.60——一个是各台阶原生 N、一个是 common-10 子集，表注和图注必须写明各自的 N。

**我看到的**（资产 `F19_stage10_ladder.png` 全分辨率；与第 9 页渲染一致）：

- panel (a) 标题：`(a) every rung on the common-10 subset, ordered by shift std`；横轴 `Kendall tau_b of the rung`（−0.6 … 1.0）；图例 `oxidation`（橙）/ `reduction`（蓝）
- 各行 y 轴标签与条形端头数值（逐行抄录）：
  - `P0->P1  std=1.519`：橙 `0.73`、蓝 `0.60`
  - `C0->C1  std=0.713`：橙 `0.69`、蓝 `-0.47`
  - `C1->C2  std=0.297`：橙 `0.87`、蓝 `0.29`
  - `P1->P2  std=0.278`：橙 `0.91`、蓝 `0.78`
  - `G1->G2  std=0.069`：橙 `0.87`、蓝 `0.87`
- 对照表 2（第 8 页）：P0→P1 氧化 `0.673` / 还原 `0.595`；P1→P2 氧化 `0.895` / 还原 `0.673`；G1→G2 氧化 `0.939` / 还原 `0.848`。

结论：图 9(a) 的 `0.73 / 0.60` 与表 2 的 `0.673 / 0.595` **两个轴都对不上**（不是只有氧化轴）；其中评审说的"图上 0.60"实际是**还原**那条（蓝），**氧化**那条在图上读到的是 `0.73`。图内 std 也是"两轴合并"的单值（1.519 / 0.713 / 0.297 / 0.278 / 0.069），而表 2 是逐轴 std（0.735/2.209、0.595/0.832、0.259/0.335、0.302/0.321、0.052/0.080）——两者口径确实不同，而图上只有 "common-10 subset" 一处说明，**未交代与表 2 的差异来源**。

**判定**：**部分复现**（口径不一致确实存在且不止一处；但评审对"0.60 属于氧化轴"的归属有误，图上氧化轴读到的是 0.73）。

**证据文件**：`...\电解液溶剂HB-Code\outputs\figures\F19_stage10_ladder.png`；`...\论文\_dossier\pw_09.png`（图）、`pw_08.png`（表 2）。

---

## 5. 图 11（F24）的介电点数

**评审原话**：ε 点数三处不一致：图 11 内标题 "six dielectrics"、图注 "七级阶梯"、§3.8 "10 个介电点"。

**我看到的**（资产 `F24_dielectric_limit.png` 全分辨率；与第 11 页渲染一致）：

- 图内总标题（suptitle）原文：`F24 the dielectric ladder, measured to eps = 200`
- panel (a) 副标题原文：`(a) six dielectrics: every curve is a straight line through 0`
- panel (a) 横轴 `u = 1 - 1/eps [dimensionless]`（0.800–1.000），图上实际画出的 ε 竖直标线为：`eps=5`、`eps=10`、`eps=20`、`eps=40`、`eps=80`、`eps=200` —— 共 **6** 个，与 "six dielectrics" 自洽
- panel (b) `(b) the data pick Born back out of a two-parameter family`：`Born 0.9861`、`Onsager 0.8779`、`two-parameter 0.9835`；注释框 `fitted k = 0.0779 +/- 0.1004 (range 0.0000 .. 0.3352)  Born is k = 0`
- panel (c) `(c) extrapolation error is set by the distance, not the target`：`through-origin: 2.031 eV per unit u`，点 `eps=40 (0.063)`、`eps=80 (0.077)`、`eps=200 (0.083)`
- panel (d) `(d) eps = 200 is within 33 meV of the conductor limit`：注释框 `mean remaining gap to eps -> inf: 0.0037 eV (worst 0.0332 eV)`
- 图注（第 11 页）原文：`图 11 介电极限：(a) 七级阶梯对 u = 1−1/ε；(b) 三个模型的 R²；(c) 外推误差；(d) ε = 200 距导体极限`
- 正文 §3.8（同页）原文：`在 12 个分子 × 3 态 × 10 个介电点共 360 个格子上普查`

**判定**：**复现**（同一件事在成品里出现 6 / 7 / 10 三种计数；且 "F24" 这个内部编号被排进了图内标题）。

**证据文件**：`...\电解液溶剂HB-Code\outputs\figures\F24_dielectric_limit.png`；`...\论文\_dossier\pw_11.png`；文本层 `_fulltext_w22.txt`。

---

## 6. 图 10（F20）与 F31：哪张有 4 个 panel、(d) 是 9 个气相描述符的 AUC

**评审原话**：图 10(d) 的多重比较——9 个预测子各做一次 AUC 检验，signed-slope 的 p = 0.008 在 Bonferroni 校正（α≈0.0056）下不幸存。

**我看到的**：

- **F20**（资产 `F20_sigma_anatomy.png`，对应成品第 10 页的图 10）：4 个 panel，标题分别为
  - `(a) T1: sigma is the shift difference (max err 1.1e-15 eV)`
  - `(b) T4: resolution is a secant-slope tail (diamond = median)`
  - `(c) T4: 20 points, z = 1 and z = 1.96 (max err 0.0e+00)`
  - `(d) the predictor is the SIGNED slope, not the magnitude` —— 横轴原文 `AUC for predicting a top-2 shortlist rewrite`（0.0–1.2，虚线在 0.5 = 随机基线）
  - (d) 的 9 根条与标注（原样抄录，自上而下）：
    1. `sigma2_share_parallel` — `1.000 (p=0.008)`
    2. `ols_slope_b` — `1.000 (p=0.008)`（**红色高亮**，即 signed slope）
    3. `rank_damage_1_minus_tau` — `0.905 (p=0.033)`
    4. `abs_ols_slope_b` — `0.905 (p=0.033)`
    5. `q_median` — `0.857 (p=0.058)`
    6. `f_unresolved_p1_observed` — `0.810 (p=0.092)`
    7. `sigma_rms_ev` — `0.810 (p=0.092)`
    8. `q_p90` — `0.762 (p=0.133)`
    9. `sigma2_share_residual` — `0.000 (p=1.000)`
  - 图内注解：`share_parallel and share_residual are complements (1 - x): the residual share is anti-predictive under its natural hypothesis`
  - ⇒ 确为 **9 个预测子**、确有一个 `p=0.008` 的 signed-slope（`ols_slope_b`），Bonferroni α = 0.05/9 ≈ 0.0056 ⇒ **0.008 > 0.0056，校正后不存活**。评审这一条的算术与图完全对得上。

- **F31**（`F31_apriori_warning_rule.png`）**不是**评审说的那张图。它是 4 个 panel，但编号是 `(d)(e)(f)(g)`：
  - `(d) The chosen a priori descriptor, discovery set filled, held-out set drawn as purple outline`
  - `(e) Every gas-phase descriptor's single-variable AUC on the discovery set (24 open-shell rows)` —— 横轴原文 `AUC - 0.5 (red: larger value is riskier)`，共 **10** 个描述符：`gas_small_gap_value 0.14`、`gas_min_spin 0.31`、`gas_gyration_ang2 0.68`、`gas_sum_spin_abs 0.66`、`gas_spin_extent_norm 0.39`、`gas_spin_rms_ang 0.61`、`gas_spin_maxfrac 0.58`、`gas_mulliken_shift 0.45`、`gas_dipole_debye 0.45`、`gas_gap_ev 0.48`（**只给 AUC，未标 p 值**）
  - `(f) Held-out arm: X = the rule got it wrong`
  - `(g) The rule and its ceiling` 文本块：`frozen rule  gas_small_gap_value <= -0.071`、`AUC 0.137 on 24 rows (5 positive)`、`leave-one-out accuracy 0.708`、`majority-class baseline 0.792`、`beats that baseline? NO -- the trivial rule wins`、`exact permutation p = 0.0116 over 42504 assignments`、`two-descriptor logistic ceiling  leave-one-out AUC 0.821  held-out accuracy 0.750`

**判定**：**复现**（第 6 条所指的 9 描述符 AUC panel = **F20 的 panel (d)**，p=0.008 的 signed slope = `ols_slope_b`）；附带说明：F31 是另一条证据链（事前预警规则），其 AUC panel 是 (e) 且描述符数 10、无 p 值，**不要与 F20(d) 混淆**。另外注意 F31 的数字与 §3.8 正文（0.7083 / 0.7917 / 0.750 / AUC 0.821）一致，但 **F31 未进入 14 页正文**，正文只给数字不给图。

**证据文件**：`...\电解液溶剂HB-Code\outputs\figures\F20_sigma_anatomy.png`、`F31_apriori_warning_rule.png`；`...\论文\_dossier\pw_10.png`、`pw_12.png`。

---

## 7. F28（双初猜）panel (a) 的样本点数与横轴标签

**评审原话**：panel (a) 的样本点数是 90 还是 360？横轴标签是什么？

**我看到的**（资产 `F28_two_guess_protocol.png` 全分辨率）：

- 图内总标题：`F28  Stage 15A -- two guesses, one ladder: is the EMC anomaly a metastable solution?`
- panel (a) 标题：`(a) restarting from the gas-phase MOs, ten dielectrics` / 第二行 `the default guess sat up to 0.286 eV too high`
- **panel (a) 横轴标签原文：`dielectric constant  eps`**，刻度为 `5, 7, 10, 14, 20, 28, 40, 80, 200, 1000`（共 **10** 个）
- y 轴：`dE [eV]`，图例共 **9 条系列** = 3 个分子（DMC / EC / EMC）× 3 个状态（anion / cation / neutral），红叉标注 `E_moread - E_default < 0: the default guess missed the lower state`；曲线在 ε=5/20/28 处最深，凹陷幅值最大约 −0.286 eV（与正文 `最大缺陷 −0.285961 eV` 一致）
- 因此 panel (a) 实际画出的点数是 **9 × 10 = 90**；**360 不在这个 panel 里**——360 是 §3.8 的"12 分子 × 3 态 × 10 介电点"全普查格数。
- panel (b) `(b) the dipole is an independent witness of which SCF solution was reached`；panel (c) `(c) the reduction-axis shift on the same axis as the Born form the fit assumes`（`eps = 1000 (measured, 2.831 eV)`，R² nine pts `0.679` vs `0.956`）；panel (d) `(d) the conductor limit: fitted vs measured`，注释 `extrapolation error at eps = 1000 is +0.0530 eV`，柱值 `2.5449`（default, nine-point slope）、`2.8308`（moread, eps=1000 measured）
- 补充：同一目录的 `《论文》\_dossier\figure_index.txt` 把 F28(a) 描述为 `(a) 90 点能量差幅度直方图与 1 meV material 阈值（12 点全部为负）` —— **与资产实际画面不符**（资产是 vs ε 的折线，不是直方图；面板里也没有 1 meV 阈值线，那条线在 F30(b) 里）。索引与图不同源，建议同步。

**判定**：**部分复现**（"90" 是 panel (a) 的真实点数量级，来源清楚；但"360" 并未出现在该 panel，属于正文口径；评审问的二者关系在正文处确实**没交代**——正好对应评审 B4 的第 4 小条）。

**证据文件**：`...\电解液溶剂HB-Code\outputs\figures\F28_two_guess_protocol.png`；`...\论文\_dossier\_fulltext_w22.txt`（§3.8 段）、`figure_index.txt`。

---

## 附录 A：本次看图时额外发现（不在评审清单，但会影响图-文一致性）

| # | 发现 | 证据 | 备注 |
|---|---|---|---|
| A-1 | **图 3 与表 1／正文的 MAE 不一致**：F3 左图把 P0 标成 `MAE 1.32 eV`、把 GFN2-xTB ΔSCF 标成 `4.45 eV`；表 1 与正文为 `1.377` / `4.481`，摘要在写 `1.38` | `F3_value_error_vs_rank_error.png` vs `pw_04.png` 表 1 | 三处数字同源却不同值 |
| A-2 | **图 9(a) 与表 2 的不一致不止一处**（详见 §4）：P1→P2 还原 图上 `0.78` / 表 `0.673`；G1→G2 两轴图上都是 `0.87` / 表 `0.939`、`0.848`；std 为合并值 vs 逐轴值 | `F19_stage10_ladder.png`、`pw_08.png` | 建议图注写明 common-10 与合并口径 |
| A-3 | **ε 口径至少四种**：F22 是 4 级（gas→5→10→20→40）、F24/图 11 是 6 级（5,10,20,40,80,200）、图注写"七级"、§3.8 与 F28 是 10 级（5,7,10,14,20,28,40,80,200,1000） | `F22_dielectric_scaling.png`、`F24_dielectric_limit.png`、`F28_two_guess_protocol.png`、`pw_11.png` | 四处应统一命名或明确各自的用途 |
| A-4 | **F31 / F43 / F44 / F45 / F46 等扩展资产未进正文**，但 §3.8、§3.9、§3.10 引用了它们的数字（如 0.7083/0.7917/0.750/AUC 0.821、第三配位点 3.897/6.291/2.015/5.672/1.292/5.336） | `F31_apriori_warning_rule.png`、`F45_targeted_two_guess.png`、`F46_shell3_saturation.png`、`pw_12.png`、`pw_13.png` | 图 12 = F45、图 13 = F46 进了正文；F31 未进 | 
| A-5 | F20(d) 的 `q_median` 在资产上读作 `0.857 (p=0.058)`；在第 10 页位图（分辨率较低）我读作 `0.056`，**不确定**是否排版/渲染差异，以资产为准 | `F20_sigma_anatomy.png`、`pw_10.png` | 低置信项，建议按资产复核正文引用值 |

以上 5 条中 A-1、A-2、A-3 属"同一数字多口径"，建议在整改时一并解决，因为它们和评审 B4 是同一类问题。

---

## 附录 B：本次判定为"未复现"的项（避免误伤）

- **页眉损坏（A4 的字面表述）**：14 页页眉均为正常模板串 `WHU 2023 级 基础化学实验 研究性实验`，无乱码、无 F 编号。真正的病灶是图内英文工作标题被排进版心首行（见 §1）。
- **参考文献 [17] 与 [18] 连排 / [18] 页码截断**：本次看图时第 14 页的 [17]、[18] 各占一行、完整可读——`[17] Furness, J. W.; Kaplan, A. D.; Ning, J.; Perdew, J. P.; Sun, J. J. Phys. Chem. Lett. 2020, 11, 8208-8215.`、`[18] Barone, V.; Cossi, M. J. Phys. Chem. A 1998, 102, 1995-2001.`。**在本份 PDF 副本上未复现**（若评审看的是另一版 DOCX/PDF，请以那一版为准）。
- **中图分类号粘连**：第 1 页 `关键词：…隐式溶剂化` 与 `中图分类号：O646` 在版面上各占一行，**未复现**粘连（见 `pw_01.png`）。