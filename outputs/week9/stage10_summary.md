# Stage 10 -- 五级台阶合成与决策稳定性总判（Week 9）

把 Week 4-8 的五级台阶放到**同一口径**（`p_red = -EA`，两个轴都 `higher_is_better`）
与**同一分子子集**上重算，然后检验本项目中心命题：

> 决定排序是否被改写的是位移的**离散度**，不是位移的**大小**。

## 1. 共同子集（N = 10）上的五级台阶

| 台阶 | 轴 | n | 位移均值 (eV) | 位移 std (eV) | tau_b | O_10% | O_20% | f_unres(after) | f_robust_inv | sigma_median |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 电子结构方法：Koopmans P0 -> r2SCAN-3c P1 | oxidation | 10 | -1.299 | **0.786** | **0.733** | 0.000 | 0.000 | 0.133 | 0.000 | 0.271 |
| 电子结构方法：Koopmans P0 -> r2SCAN-3c P1 | reduction | 10 | 7.064 | **2.253** | **0.600** | 0.000 | 1.000 | 0.733 | 0.000 | 1.422 |
| 环境：气相 P1 -> SMD(乙腈) P2 | oxidation | 10 | -2.465 | **0.269** | **0.911** | 1.000 | 1.000 | 0.111 | 0.000 | 0.211 |
| 环境：气相 P1 -> SMD(乙腈) P2 | reduction | 10 | -2.172 | **0.286** | **0.778** | 0.000 | 1.000 | 0.200 | 0.000 | 0.213 |
| 几何：GFN2-xTB G1 -> r2SCAN-3c Opt+Freq G2 | oxidation | 10 | -0.012 | **0.051** | **0.956** | 1.000 | 1.000 | 0.022 | 0.000 | 0.043 |
| 几何：GFN2-xTB G1 -> r2SCAN-3c Opt+Freq G2 | reduction | 10 | -0.125 | **0.086** | **0.867** | 1.000 | 1.000 | 0.067 | 0.000 | 0.053 |
| 条件态：自由分子 C0 -> [Li M]+（1:1） | oxidation | 10 | 4.887 | **0.595** | **0.689** | 1.000 | 1.000 | 0.200 | 0.000 | 0.420 |
| 条件态：自由分子 C0 -> [Li M]+（1:1） | reduction | 10 | -6.578 | **0.832** | **-0.467** | 0.000 | 0.000 | 0.800 | 0.000 | 0.633 |
| 条件态：[Li M]+ -> [Li(M)2]+（1:2） | oxidation | 10 | -1.700 | **0.259** | **0.867** | 1.000 | 1.000 | 0.089 | 0.000 | 0.192 |
| 条件态：[Li M]+ -> [Li(M)2]+（1:2） | reduction | 10 | 1.199 | **0.335** | **0.289** | 0.000 | 0.000 | 0.356 | 0.000 | 0.176 |

`sigma_median` 是 `layer_stability` 内部的方法散布估计（两层作为两次实现，
`sigma_ij = |dP0_ij - dP1_ij| / sqrt(2)`），与 `f_unresolved` 使用同一个矩阵。

## 2. 中心命题的定量检验

在 10 个 (台阶, 轴) 点上：

| 假设 | 统计量 | 值 |
| --- | --- | --- |
| H_var：位移**离散度**决定 tau_b | Spearman rho(shift std, tau_b) | **-0.851** |
| H_mean：位移**大小**决定 tau_b | Spearman rho(abs(shift mean), tau_b) | -0.535 |
| 辅助：离散度 vs 不可判定比例 | Spearman rho(shift std, f_unresolved) | 0.894 |

n = 10 的秩相关只能读方向与量级，不能读显著性；这里给出它是因为这是本项目
**唯一**一处能把「位移大」与「决策坏」分开的定量证据。

## 3. v2 第 22 节：情形判定

| 情形 | 判定 | 依据 |
| --- | --- | --- |
| A：廉价 proxy 已足够 | **NOT SUPPORTED** | P0 -> P2 氧化轴上 tau_b = 0.673、Top-10% 重叠 0.000、后一层 f_unresolved = 0.229（见 p2_decision_stability.json 的 p0_to_p2） |
| B：位移大但排序稳 | **SUPPORTED** | P1 -> P2 氧化轴位移均值 -2.393 eV、位移 std 0.302 eV，而 tau_b = 0.895、O_20% = 0.750、f_robust_inv = 0.000 |
| C：结构集中的 robust inversion | **NOT OBSERVED** | 五个台阶、两个轴、两种口径共 20 个 (台阶, 轴) 组合中，f_robust_inv 的取值全部为 0.000；z=1.96 敏感性列同样全为 0.000 |
| D：配位引发 state-identity 改变 | **OBSERVED** | Week 5 state-identity（`outputs/week5/c1_state_identity.json`）：还原态 12 个里 **11 个是 Li_centered_or_mixed_redox**、1 个 molecule_centered_redox；氧化态 12 个里 molecule_centered_redox = 8、no_intact_minimum_found = 4。判定阈值：abs(Mulliken spin on Li) >= 0.5 或 abs(dq(Li)) >= 0.5 e 记为 Li 中心。 |
| E：Δ-learning 优于 direct | **SUPPORTED（6/8）；例外：C/reduction/X0、C/reduction/X0+X1** | LOFO 拆分下、每个 (任务, 轴, 特征档) 上取模型阶梯最优的 kendall_tau_b（预测排序对真值的保真度）：C/oxidation/X0 direct 0.111 (krr) -> shift 0.644 (krr), +0.533；C/oxidation/X0+X1 direct 0.244 (ridge) -> shift 0.644 (rf), +0.400；C/reduction/X0 direct 0.422 (gbdt) -> shift 0.022 (krr), -0.400；C/reduction/X0+X1 direct 0.289 (gbdt) -> shift 0.200 (ridge), -0.089；E/oxidation/X0+P1 direct 0.843 (ridge) -> shift 0.922 (rf), +0.078；E/reduction/X0+P1 direct 0.686 (rf) -> shift 0.739 (krr), +0.052；M/oxidation/X0 direct 0.294 (krr) -> shift 0.595 (constant), +0.301；M/reduction/X0 direct 0.359 (rf) -> shift 0.556 (constant), +0.196。对照：参考层自身的 kendall_tau_b_vs_reference = C/oxidation = 0.689、C/oxidation = 0.689、C/reduction = -0.467、C/reduction = -0.467、E/oxidation = 0.895、E/reduction = 0.673、M/oxidation = 0.673、M/reduction = 0.595。 |
| F：Δ 无法从廉价特征学出 | **NOT SUPPORTED（Δ 在 6/8 个分组上可从廉价特征学出）；例外：C/reduction/X0、C/reduction/X0+X1（与情形 D 同一根还原轴）** | LOFO 拆分下、每个 (任务, 轴, 特征档) 上取模型阶梯最优的 kendall_tau_b（预测排序对真值的保真度）：C/oxidation/X0 direct 0.111 (krr) -> shift 0.644 (krr), +0.533；C/oxidation/X0+X1 direct 0.244 (ridge) -> shift 0.644 (rf), +0.400；C/reduction/X0 direct 0.422 (gbdt) -> shift 0.022 (krr), -0.400；C/reduction/X0+X1 direct 0.289 (gbdt) -> shift 0.200 (ridge), -0.089；E/oxidation/X0+P1 direct 0.843 (ridge) -> shift 0.922 (rf), +0.078；E/reduction/X0+P1 direct 0.686 (rf) -> shift 0.739 (krr), +0.052；M/oxidation/X0 direct 0.294 (krr) -> shift 0.595 (constant), +0.301；M/reduction/X0 direct 0.359 (rf) -> shift 0.556 (constant), +0.196。对照：参考层自身的 kendall_tau_b_vs_reference = C/oxidation = 0.689、C/oxidation = 0.689、C/reduction = -0.467、C/reduction = -0.467、E/oxidation = 0.895、E/reduction = 0.673、M/oxidation = 0.673、M/reduction = 0.595。 |
| G：大部分 pair 不可判定 | **PARTIALLY SUPPORTED (还原轴 C0 -> C1)** | C0 -> C1 还原轴：tau_b = -0.467，f_unresolved(after) = 0.800，O_10% = 0.000；同一级的氧化轴作对照：tau_b = 0.689、f_unresolved(after) = 0.200；P0 -> P1 还原轴 f_unresolved(after) = 0.733 |

### 3.1 逐条读法

- **A：廉价 proxy 已足够** —— 廉价层不能替代目标层：值误差与排序都被改写。
- **B：位移大但排序稳** —— 环境台阶是「大位移 + 小离散」的典型：位移被排序保留下来。
- **C：结构集中的 robust inversion** —— 本项目**没有**在任何一级台阶上抓到 robust inversion。需要注意这不是「排序处处可靠」：见情形 G。
- **D：配位引发 state-identity 改变** —— **这一条成立，而且它改写了还原轴的解读**：在 C1 复合物上加一个电子时，电子主要落在 **Li** 上（11/12 个还原态是 Li_centered_or_mixed_redox），而不是落在溶剂分子上。因此 C0 -> C1 的还原轴位移（-6.6 eV，按 p_red = -EA 记）测的不是「溶剂分子更难被还原」，而是「Li+ 在这个配位环境里被还原」——这是一个不同的物理过程，其能量随 motif 的变化方式与配体还原不同。这正是还原轴在 C0 -> C1 上 tau_b = -0.467、80% 的 pair unresolved 的原因。v2 §22.4 因此要求：先做 state classification，再做 conditional regression。
- **E：Δ-learning 优于 direct** —— **Δ-learning 在 6/8 个分组上不劣于 direct**，提升最大的正是 C0 -> C1 的氧化轴（tau_b 0.111 -> 0.644，+0.53）；唯二的两次退步都落在 C0 -> C1 的**还原轴**——正是情形 D 指出的 Li 中心还原轴。也就是说，「自由分子层面的物理已捕获大部分变化」在除该轴以外的所有台阶上成立。
- **F：Δ 无法从廉价特征学出** —— **不成立（Δ 是可学的）**：廉价特征加 Δ 形态在 6/8 个分组上达到或超过 direct。真正学不动的只有 C0 -> C1 还原轴，与情形 D 一致——缺的不是模型容量，而是「Li 中心还原」这一不同物理过程的表示（配位几何 / 局部 ESP / 供体对几何）。
- **G：大部分 pair 不可判定** —— 还原轴在配位台阶上整体不可判定；氧化轴仍然可判定。这就是为什么 `f_robust_inv = 0` 必须与 `f_unresolved` 一起读。

## 4. v2 第 23 节：最小成果判据对照

| # | 判据 | 状态 | 证据 |
| --- | --- | --- | --- |
| 1 | metadata 严格、chemical-space 平衡的 core set（18 分子） | **PASS** | Week 1-3：core 18 / broad 40，family 平衡，`data/metadata/core_set.csv` |
| 2 | broad cheap pool（40 分子廉价层） | **PASS** | Week 3：`outputs/week3/p0_pool.csv`，58 分子合并池 |
| 3 | P0 / P1 / P2 的一致定义 | **PASS** | Week 1 冻结（`config/scientific_definitions.yaml`），Week 3-4 全部执行 |
| 4 | C1 Li-coordination conditional analysis | **PASS** | Week 5（T4）：12 motif / 8 家族；另见 Week 8 的 C2 复核 |
| 5 | external gas / solution anchors | **PARTIAL** | 气相锚点已用（Week 2/4）；溶液锚点 31 行仍为 `method=est`（Gate 1 未关闭） |
| 6 | uncertainty-aware rank comparison | **PASS** | Week 4-8：tau_b / O_k / Jaccard / regret / f_unresolved / f_robust_inv |
| 7 | robust inversion mechanism analysis | **PASS (negative)** | Week 9 本文件：五个台阶上 f_robust_inv 恒为 0，机制归属见 §情形 C |
| 8 | random / group / LOFO 三种拆分 | **PASS** | Week 7 / Stage 7：`outputs/week7/stage7_ml_results.json` |
| 9 | direct vs Δ-learning | **PASS** | Week 7：F16 |
| 10 | feature-cost-aware active-learning replay | **PASS** | Week 7 / Stage 8：`outputs/week7/stage8_al_results.json`、F17 |
| 11 | high-cost-label budget vs decision accuracy 曲线 | **PASS** | Week 7：`n_T -> tau_b` 四条 acquisition 曲线（F17） |

## 5. 读法纪律

- `f_robust_inv = 0` **必须**与 `f_unresolved` 一起读。本项目的 `robust_inversion_fraction`
  以「两个模型都 resolved 的 pair 数」为分母；当一级台阶把大部分 pair 变成 unresolved 时
  分母被掏空，`f_robust_inv` 会**自动**变成 0。那是**不可判定**，不是**稳定**。
- Top-k 指标的分母 k 随 N 变化（N=10/12/18 时 k = 1/2/4 等），跨台阶比较只看趋势。
- 五个台阶的「唯一变量」是人为指定的：P0->P1 同时改变方法**与**几何来源（Koopmans 用 xTB
  几何），因此 G1->G2 这一级是用来**分离几何贡献**的对照，不是独立台阶。
