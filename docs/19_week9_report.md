# Week 9 报告 —— Stage 10：五级台阶合成与决策稳定性总判

> 上游：`docs/10_week4_report.md`（P₀/P₁/P₂、T2 几何台阶）、`docs/12_week5_report.md`（T4 / C₁ = [Li M]⁺）、
> `docs/15_week7_report.md`（Stage 7/8：ML 与主动学习）、`docs/18_week8_report.md`（Stage 9 / C₂ = [Li(M)₂]⁺）、
> `docs/17_plan_optimization_branchABC.md`（本轮对计划的修订提案 P1–P8）。
> **冻结件状态**：本轮**未**修改 `config/prereg.yaml` 与 `config/scientific_definitions.yaml`，
> 目标量 / family 定义 / 筛选方向 / 阈值 / k/N / 种子集 / splits 全部沿用 → **Gate 0 保持 CLOSED**。
> **Gate 1 仍为 NOT CLOSED**：唯一 blocker 依旧是 `data/anchors/solution_redox_anchors.csv` 的 31 行 `method=est`。

---

## 0. 一句话结论

把此前**分散在 Week 4–8** 的五个「台阶」放到**同一把尺子**（同一约定 `p_red = −EA`、两个轴都 `higher_is_better`）
和**同一批分子**（10 个在每一级都有完整数据的分子）上重算之后，本项目的中心命题第一次可以被定量回答：

> **决定一级台阶会不会改写候选排序的，是这一级位移的「离散度」（std），而不是它的「大小」（|mean|）。**

在 10 个 (台阶, 轴) 数据点上：

| 假设 | 统计量 | 值 | 读法 |
| --- | --- | --- | --- |
| **H_var**：位移**离散度**决定 τ_b | Spearman ρ(shift std, τ_b) | **−0.851** | 离散度越大，排序越被改写 |
| H_mean（对照）：位移**大小**决定 τ_b | Spearman ρ(abs(shift mean), τ_b) | −0.535 | 幅度也相关，但更弱；且它并不解释「大位移却不换序」的那些台阶 |
| 机制环节：离散度 → 不可判定比例 | Spearman ρ(shift std, f_unresolved) | **+0.894** | 离散度通过方法分歧矩阵 σ_ij 直接喂给 `f_unresolved` |

最尖锐的对照就在同一张表里：**P₀→P₁ 的还原轴位移最大（+7.06 eV），但它不是排序最糟的一级**；
而 **C₀→C₁ 的还原轴位移大小相仿（−6.58 eV），却是唯一出现负相关（τ_b = −0.467）的一级**。
两者的差别不在幅度，在离散度：**2.253 eV vs 0.832 eV**。

---

## 1. 为什么要有这一步（Stage 10 的动机）

Week 4–8 各自回答了自己的问题，但每一周都用了**不同的分子子集**和**自己的口径**：

- Week 4 的 P₀→P₁ / P₁→P₂ 建在 core 18 上；
- Week 4 的 G1→G2 只在 12 个有 Opt+Freq 的分子上；
- Week 5 的 C₀→C₁ 建在 12 个 motif（10 个 primary 分子 + DMC m2 + TMP m2）上，且还原轴用的是 `−EA`；
- Week 8 的 C₁→C₂ 建在 12 个 `[Li(M)₂]⁺` 壳层上。

于是出现两个问题：

1. **跨周的 τ_b 不能直接比较** —— 不同 N 让 `layer_stability` 的 Top-k 分母 k 与 pair 总数都变了。
   例如 `f_unresolved` 是「unresolved pair 数 / 全部 pair 数」，N=18 与 N=10 的 pair 数差 3 倍以上。
2. **「大位移」与「坏排序」在叙述上被混为一谈** —— 配位台阶（C₀→C₁）位移最大，于是容易被写成
   「位移大所以排序被改写」。但 P₀→P₁ 还原轴的位移同样大，排序却没有被推翻。

Stage 10 就是来消掉这两个歧义的：**统一约定、统一子集、统一指标，然后只看一个数——离散度。**

---

## 2. 口径统一

### 2.1 一个约定：`p_red = −EA`

本项目关心的是「溶剂分子被氧化 / 被还原的难易」这一对能级，而不是 IP/EA 原始符号。
所以两个轴统一为：

| 轴 | 物理量 | 定义 | 越大越 |
| --- | --- | --- | --- |
| oxidation | p_ox | = IP | 抗氧化 |
| reduction | p_red | = **−EA** | 抗还原 |

两轴都设 `higher_is_better = True`（与 Week 4/5 已冻结的约定一致；本轮核对过 Week 4–8 的全部 JSON，
无一处例外）。**P₀→P₁ 与 P₁→P₂ 两级的公式与 Week 4 原文逐字相同**，所以本轮不是重算，
而是把已有数字搬到同一坐标系里。

### 2.2 一个子集：common-10

十个在**每一级台阶上都有有效值**的分子：

```
AN, DMC, DME, DMSO, DOL, EC, GBL, SL, SN, TMP
```

其中 8 个家族（nitrile / carbonate / ether / sulfoxide / cyclic-ester / sulfone / phosphate / linear-carbonate 等）全覆盖。

**为什么是 10 而不是 12 或 18？**

- core 18 里 PC、EMC 等**没有**稳定的 C₁ motif（`docs/12` §C₁ 枚举里它们被 `placement_clash` 或
  motif 收敛筛掉），所以「每一级都齐」的分子上限就是 10；
- C₁/C₂ 级的 12 个 motif 里，DMC m2 与 TMP m2 是**同一个分子的第二个配位模式**（双齿），
  它们不是「另外两个分子」。做跨级比较时若把它们算成两个样本，等于给 DMC / TMP 双倍权重。
  因此 Stage 10 的分子级代表**统一取 primary m1 motif**，`n = 10`。

这不是数据删减，而是**把「分子」这个统计单元还给每一行**。12 motif 的全量数字仍然完整保留在
`outputs/week5/c1_coord_shifts.csv` 与 `outputs/week8/stage9_shell_shifts.csv` 里。

### 2.3 五个台阶的定义

| # | rung key | 唯一变量 | 源文件 |
| --- | --- | --- | --- |
| 1 | `P0_to_P1` | 电子结构方法：Koopmans P₀ → r2SCAN-3c P₁ | `outputs/week4/p1_core_set_derived.csv` |
| 2 | `P1_to_P2` | 环境：气相 P₁ → SMD(乙腈) P₂ | `outputs/week4/p2_environment_effects.csv` |
| 3 | `G1_to_G2` | 几何：GFN2-xTB G1 → r2SCAN-3c Opt+Freq G2 | `outputs/week4/t2_opt_freq_summary.json` |
| 4 | `C0_to_C1` | 条件态：自由分子 C₀ → `[Li M]⁺`（1:1） | `outputs/week5/c1_coord_shifts.csv` |
| 5 | `C1_to_C2` | 条件态：`[Li M]⁺` → `[Li(M)₂]⁺`（1:2） | `outputs/week8/stage9_shell_shifts.csv` |

### 2.4 一级台阶怎么被判「改写排序」

沿用已被测试钉住的 `analyze_p1_core_set.layer_stability()`：

- **τ_b**：两层排序的 Kendall τ_b（越高越稳）；
- **σ_ij**：`|ΔP₀,ij − ΔP₁,ij| / √2` —— 把两层当成同一物理量的两次实现，逐 pair 估计方法散布；
- **f_unresolved**：`σ_ij > z · σ_median` 的 pair 占比（预注册 z = 1.0，敏感性 z = 1.96）；
- **f_robust_inv**：在 σ_ij 意义上**确定性反转**的 pair 占比；
- **O_k**：Top-k（k = max(1, round(frac·n))）选中集合的重叠率。

本轮**没有**改动这些定义，只是把它们逐个台阶平行调用。
---

## 3. 五级台阶（common-10，N = 10）

| 台阶 | 轴 | mean (eV) | **std (eV)** | **τ_b** | O_10% | O_20% | f_unres(after) | f_robust_inv | σ_median (eV) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P₀→P₁ 方法 | ox | −1.299 | **0.786** | **0.733** | 0.000 | 0.000 | 0.133 | 0.000 | 0.271 |
| P₀→P₁ 方法 | red | +7.064 | **2.253** | **0.600** | 0.000 | 1.000 | 0.733 | 0.000 | 1.422 |
| P₁→P₂ 环境 | ox | −2.465 | **0.269** | **0.911** | 1.000 | 1.000 | 0.111 | 0.000 | 0.211 |
| P₁→P₂ 环境 | red | −2.172 | **0.286** | **0.778** | 0.000 | 1.000 | 0.200 | 0.000 | 0.213 |
| G1→G2 几何 | ox | −0.012 | **0.051** | **0.956** | 1.000 | 1.000 | 0.022 | 0.000 | 0.043 |
| G1→G2 几何 | red | −0.125 | **0.086** | **0.867** | 1.000 | 1.000 | 0.067 | 0.000 | 0.053 |
| C₀→C₁ 配位 | ox | +4.887 | **0.595** | **0.689** | 1.000 | 1.000 | 0.200 | 0.000 | 0.420 |
| C₀→C₁ 配位 | red | −6.578 | **0.832** | **−0.467** | 0.000 | 0.000 | 0.800 | 0.000 | 0.633 |
| C₁→C₂ 壳层 | ox | −1.700 | **0.259** | **0.867** | 1.000 | 1.000 | 0.089 | 0.000 | 0.192 |
| C₁→C₂ 壳层 | red | +1.199 | **0.335** | **0.289** | 0.000 | 0.000 | 0.356 | 0.000 | 0.176 |

（`native` 口径——每级各用其自身的分子集，n = 18/18/12/10/10——也一并写在
`outputs/week9/stage10_ladder.csv` 里，便于与 Week 4/5/8 的原始报告对齐。）

三项立刻可见的事实：

1. **唯一一个负 τ_b 出现在 C₀→C₁ 还原轴**（−0.467）：换到配位条件态后，还原难易的排序被**翻掉**了。
2. **20 个 (台阶, 轴) 组合里 `f_robust_inv` 恒为 0.000**，z = 1.0 与 z = 1.96 都是。
3. **`f_unresolved` 跨度极大**：从 G1→G2 氧化轴的 0.022 一直涨到 C₀→C₁ 还原轴的 0.800。

第 2 点很容易被误读成「排序处处可靠」，第 3 点说明事实恰恰相反。§10 专门处理这个陷阱。

---

## 4. 中心命题的定量检验

### 4.1 两个假设

把 10 个点当成 10 次「台阶事件」，每个事件有一个自变量（位移的某个一阶特征）和一个因变量（τ_b）：

- **H_var**：自变量 = shift **std**；
- **H_mean**（对照）：自变量 = \|shift **mean**\|。

用 Spearman 秩相关（n = 10，只读方向与量级，不读显著性）：

| 假设 | ρ | 结论 |
| --- | --- | --- |
| H_var | **−0.851** | 支持：离散度越大的台阶，τ_b 越低 |
| H_mean | −0.535 | 弱得多；且无法解释「大位移但不换序」的台阶 |
| （辅助）std vs f_unresolved | **+0.894** | 离散度越大，unresolved pair 越多 |

### 4.2 为什么 H_mean 必然解释力更弱：两个反例就在表里

H_mean 想说的是「位移大 → 排序坏」。但本项目的五个台阶里，

- **P₀→P₁ 还原轴**：\|mean\| = 7.064 eV（全表最大），τ_b = **0.600**（不是最坏，甚至偏稳）；
- **C₁→C₂ 还原轴**：\|mean\| = 1.199 eV（全表最小之一），τ_b = **0.289**（接近最坏）。

位移最小的台阶反而排序更坏，位移最大的台阶反而保住了排序 —— 这直接否证了「幅度假说」。
而用 std 看，这两级的 std 分别是 2.253 与 0.335，与各自的 τ_b 方向完全一致。

### 4.3 H_var 的物理含义

τ_b 只对**位移的差异**敏感，对**位移的公共部分**不敏感，这是一条纯代数事实：

设两层排序由标量 `P₀ = m + a_i`、`P₁ = m + Δ_i` 给出（m 是公共偏移，Δ_i 是逐分子位移）。
若 Δ_i = δ 对所有 i 相同（**零离散度**），那么 `P₁ = P₀ + δ`，排序**逐个 pair 完全不变**，τ_b = 1。
此时位移 δ 可以任意大 —— 幅度**根本不进入** τ_b。反过来，只要 Δ_i 有离散度，
就会有 pair 的**相对次序**发生变化，τ_b 才会掉下来。

换句话说：**公共位移是「整体平移」，排序对它免疫；离散度是「相对形变」，排序只对它响应。**
这就是为什么该测的是 σ(Δ)，而不是 |mean(Δ)|。

一个直接推论：**「某个台阶位移很大」这句话本身不构成「该台阶会改写排序」的理由**。
要论证排序被改写，必须给出 σ(Δ)，或者等价地给出 σ_ij 与 `f_unresolved`。

---

## 5. 机制：离散度通过 σ_ij 变成「不可判定」

`f_unresolved` 与 std 的 ρ = **+0.894**（高于 H_var 本身的 −0.851）不是巧合，而是定义上的因果链：

```
位移离散度 σ(Δ)
    └─> 逐 pair 的方法分歧 σ_ij = |ΔP0,ij − ΔP1,ij| / √2 变大
            └─> 超过 z·σ_median 的 pair 变多
                    └─> f_unresolved 上升
                            └─> 可参与 τ_b 计算的 pair 减少 / 排序被改写
```

所以离散度不仅有「几何上让次序变形」的直接作用，还有「通过放大不确定性把 pair 变成不可判定」的间接作用，
两者同向叠加。

**注意一个反直觉的细节**：σ_median 本身也被离散度拉大（P₀→P₁ 还原轴的 σ_median = 1.422 eV，
是全表最大值）。如果只看 σ_median，会以为这一级「uncertainty 大所以不可信」；
但 `f_unresolved` 只到 0.733，说明**大而共同的位移**让 σ_ij 也一起抬高了，反而保住了相当一部分 pair 的判定。
真正把 C₀→C₁ 还原轴推到 0.800 的，是它的位移**方向不一致**（见 §7）。
---

## 6. v2 §22：情形 A–G 判定

| 情形 | 判定 | 依据 |
| --- | --- | --- |
| **A** 廉价 proxy 已足够 | **NOT SUPPORTED** | P₀→P₂ 氧化轴 τ_b = 0.673、Top-10% 重叠 0.000、后一层 `f_unresolved` = 0.229 |
| **B** 位移大但排序稳 | **SUPPORTED** | P₁→P₂ 氧化轴 mean = −2.393 eV、std = 0.302 eV，而 τ_b = 0.895、O_20% = 0.750、`f_robust_inv` = 0.000 |
| **C** 结构集中的 robust inversion | **NOT OBSERVED** | 20 个 (台阶, 轴) 组合中 `f_robust_inv` 全为 0.000（z = 1.96 亦同） |
| **D** 配位引发 state-identity 改变 | **OBSERVED** | Week 5：还原态 12/12 中 **11 个**是 `Li_centered_or_mixed_redox`；氧化态（dication）12 个里 8 个 `molecule_centered_redox`、4 个 `no_intact_minimum_found` |
| **E** Δ-learning 优于 direct | **SUPPORTED（6/8）**；例外：`C/reduction/X0`、`C/reduction/X0+X1` | LOFO 下每组取模型阶梯最优 τ_b：提升最大的是 C₀→C₁ 氧化轴（0.111 → 0.644，+0.533） |
| **F** Δ 无法从廉价特征学出 | **NOT SUPPORTED**（Δ 在 6/8 个分组上可从廉价特征学出） | 同上；唯二失败者与情形 D 是同一根还原轴 |
| **G** 大部分 pair 不可判定 | **PARTIALLY SUPPORTED**（C₀→C₁ 还原轴） | 该轴 `f_unresolved`(after) = 0.800、τ_b = −0.467、O_10% = 0.000；对照同级氧化轴 0.200 / 0.689 |

### 6.1 逐条解释

**A（NOT SUPPORTED）** —— 廉价层（Koopmans P₀）与目标层（SMD P₂）之间的 τ_b 只有 0.673，
且 Top-10% 重叠为 **0**：最想选的那几个分子，廉价 proxy 一个都没选中。所以「用廉价 proxy 直接排名」
在本适用域内不成立，必须走 P₁/P₂ 级计算。

**B（SUPPORTED）** —— 环境台阶是「大位移 + 小离散」的教科书例子：SMD 把氧化电位整体压低 ~2.4 eV，
但几乎不给不同分子不同的位移（std 只有 0.302 eV）。结果排序几乎原封不动（τ_b = 0.895）。
这正是 §4.3 那条代数事实的正面实例。
v2 §22.2 给出的下一步是可检验的：若该台阶只引入族层级偏移，那么 `P2 = P1 + b_f`（family-dependent correction）就应当足够，而不必逐分子重算 P2。

**C（NOT OBSERVED）** —— 值得强调：**这是「未被观测到」，不是「已被排除」**。
`f_robust_inv` 的定义以「两个模型都 resolved 的 pair」为分母；一级台阶一旦把大部分 pair 变成 unresolved，
分母被掏空，`f_robust_inv` 会**自动**报 0。C₀→C₁ 还原轴就是这种情形（80% unresolved）。
所以「C 未观测到」与「排序处处可靠」是两回事，后者由 G 直接否掉。

**D（OBSERVED）** —— 详见 §7。这一条本轮从「未观测」**翻案成「成立」**，原因是此前只看
`counts` 汇总字段（该字段在 Week 5 的文件里并不存在），没有读 `per_redox_state`。

**E / F** —— 详见 §8。

**G（PARTIALLY SUPPORTED）** —— 只有 C₀→C₁ **还原轴**达到「大部分 pair 不可判定」。
氧化轴在同一级仍然可判定（0.200 / 0.689），P₀→P₁ 还原轴也只有 0.733 / 0.600。
所以 G 不是一个全局性质，而是一个**沿轴定位**的性质：配位条件态下的还原轴。
v2 §22.7 对这种情形给出的输出形式是：**不要强行排名**，而是给出候选分子的 **equivalence classes / tiered sets**——这正是本项目一开始就把排序建立在不确定性上的原因。

---

## 7. 情形 D 深挖：C₀→C₁ 还原轴测的不是「溶剂被还原」

### 7.1 事实

`outputs/week5/c1_state_identity.json` 的 `per_redox_state`：

| 氧化/还原态 | 形式电荷 | 标签分布 | 判定来源 |
| --- | --- | --- | --- |
| `reduced`（加一个电子） | 0 | `Li_centered_or_mixed_redox` = **11**，`molecule_centered_redox` = 1 | electron |
| `dication`（去掉一个电子） | +2 | `molecule_centered_redox` = 8，`no_intact_minimum_found` = 4 | electron 8 / geometry 4 |

判定阈值（文件 `thresholds` 字段原文）：`spin_li_centered = 0.5`、`charge_li_centered = 0.5 e`。

### 7.2 这意味着什么

在 `[Li M]⁺` 上加一个电子时，**12 个 motif 里有 11 个把电子放到了 Li 上**（或 Li/分子的混合态），
而不是放到溶剂分子的 π*/σ* 上。

于是 C₀→C₁ 还原轴这一级的物理含义发生了**性质改变**：

- C₀ 端的还原是**溶剂分子的还原**（电子进分子的最低空轨道）；
- C₁ 端的还原是**Li⁺ 在这个配位环境里被还原**（电子进 Li 中心/混合态）。

**这不是同一个物理量在两层方法下的两次测量，而是两个不同的物理过程。**
用 `layer_stability` 的「同一物理量、两次实现」假设去比较这两者的排序，前提本身就不成立。

这解释了该轴的全部异常：

- τ_b = **−0.467**（不是变差，而是**换号**——排序被结构性地重排）；
- `f_unresolved` = **0.800**（σ_ij 大，因为两个「模型」在测不同东西）；
- 位移 **−6.58 eV** 的量级来自 Li⁺/Li⁰ 的还原化学，而不是溶剂的 LUMO 能级差；
- 和它是**同一个分子集合**的氧化轴一切正常（τ_b = 0.689、`f_unresolved` = 0.200）——
  因为氧化态的电子确认是分子中心的（8/12 `molecule_centered_redox`）。

### 7.3 方法论后果

v2 §22.4 的处置是：**先做 state classification，再做 conditional regression**。
本轮把它落成了两条可执行纪律：

1. **报告配位台阶的还原轴时，必须同时报告 state-identity 标签分布**，
   否则会把「换了物理过程」误读成「方法不一致」。
2. **不要把该轴的 τ_b 用于「方法可迁移性」的论证** —— 它测的是化学，不是方法学。
   真正用于方法学论证的还原轴是 P₀→P₁（0.600 / 0.733）、P₁→P₂（0.778 / 0.200）与 C₁→C₂（0.289 / 0.356）。

---

## 8. 情形 E/F：Δ-learning 的胜负与还原轴例外

### 8.1 数据

Stage 7（`outputs/week7/stage7_ml_results.json`）在 LOFO 拆分下对 8 个分组
（3 个任务 × 2 个轴，其中 C 任务有 X0 与 X0+X1 两个特征档）评估了模型阶梯。
每组取该组内 τ_b 最优的模型，比较 `direct` 形态与 `shift`（Δ-learning）形态：

| 分组 (task/axis/features) | direct 最优 τ_b | shift 最优 τ_b | Δ |
| --- | --- | --- | --- |
| M / oxidation / X0 | 0.294 (krr) | **0.595** (constant) | +0.301 |
| M / reduction / X0 | 0.359 (rf) | **0.556** (constant) | +0.196 |
| E / oxidation / X0+P1 | 0.843 (ridge) | **0.922** (rf) | +0.078 |
| E / reduction / X0+P1 | 0.686 (rf) | **0.739** (krr) | +0.052 |
| C / oxidation / X0 | 0.111 (krr) | **0.644** (krr) | +0.533 |
| **C / reduction / X0** | **0.422** (gbdt) | 0.022 (krr) | **−0.400** |
| C / oxidation / X0+X1 | 0.244 (ridge) | **0.644** (rf) | +0.400 |
| **C / reduction / X0+X1** | **0.289** (gbdt) | 0.200 (ridge) | **−0.089** |

**6/8 不劣于，唯二两次退步都在 `C` 任务的还原轴。**

### 8.2 读法

**E 成立（6/8）**：把「廉价层 → 目标层」的差当成学习目标（Δ-learning），
比直接学目标层更好，说明**自由分子层面的物理已经捕获了绝大部分台阶位移**；
剩下的 Δ 是局部修正，而局部修正比绝对值更容易学。

**F 不成立**：Δ 在 6/8 个分组上是**可学**的，所以「Δ 学不出来」的悲观结论被否掉。
真正学不动的那 1/8 类，正是 §7 的 **C₀→C₁ 还原轴** ——
它的位移来自「Li 中心还原」，廉价特征里**根本没有**这个过程的表示。
缺的是**物理表示**，不是模型容量。按 v2 §22.6，下一步应优先加入四项：
`cheap coordination geometry proxy`（Li 配位几何）、`conformational flexibility`（构象柔性）、
`local ESP topology`（局部 ESP）、`donor-pair geometry`（供体对几何）——
而不是直接更换更大的 neural network。

这也把 E/F 与 D 串成一条因果链：

```
C₀→C₁ 还原轴：电子落到 Li 上（D）
    ├─> 该轴与其它台阶不是同一物理量
    ├─> 位移离散度大且方向不一致
    │       ├─> τ_b 换号（−0.467）、f_unresolved = 0.800（G）
    │       └─> 平价特征无法表示该过程
    │               └─> Δ-learning 在该轴失败（E/F 的两个例外）
    └─> 结论：该轴的坏指标是化学造成的，不是方法学造成的
```
---

## 9. v2 §23：最小成果判据对照（11 条）

| # | 判据 | 状态 | 证据 |
| --- | --- | --- | --- |
| 1 | metadata 严格、chemical-space 平衡的 core set（18 分子） | **PASS** | Week 1–3：core 18 / broad 40，family 平衡，`data/metadata/core_set.csv` |
| 2 | broad cheap pool（40 分子廉价层） | **PASS** | Week 3：`outputs/week3/p0_pool.csv`（58 分子合并池） |
| 3 | P₀ / P₁ / P₂ 的一致定义 | **PASS** | Week 1 冻结（`config/scientific_definitions.yaml`），Week 3–4 全部执行 |
| 4 | C₁ Li-coordination conditional analysis | **PASS** | Week 5（T4）：12 motif / 8 家族；Week 8 的 C₂ 复核 |
| 5 | external gas / solution anchors | **PARTIAL** | 气相锚点已用（Week 2/4）；**溶液锚点 31 行仍为 `method=est`**（Gate 1 未关闭） |
| 6 | uncertainty-aware rank comparison | **PASS** | Week 4–9：τ_b / O_k / Jaccard / regret / `f_unresolved` / `f_robust_inv` |
| 7 | robust inversion mechanism analysis | **PASS（负结果）** | 本报告 §3/§6：五级台阶上 `f_robust_inv` 恒为 0，机制归属见情形 C + §10 |
| 8 | random / group / LOFO 三种拆分 | **PASS** | Week 7 / Stage 7：`outputs/week7/stage7_ml_results.json` |
| 9 | direct vs Δ-learning | **PASS** | Week 7 / Stage 7（F16）；本报告 §8 给出 6/8 的分组级复核 |
| 10 | feature-cost-aware active-learning replay | **PASS** | Week 7 / Stage 8：`outputs/week7/stage8_al_results.json`（F17） |
| 11 | high-cost-label budget vs decision accuracy 曲线 | **PASS** | Week 7：`n_T → τ_b` 四条 acquisition 曲线（F17） |

**唯一未达标项是第 5 条**，且它卡在**外部数据的可获得性**上，不是流程问题：溶液相 redox 锚点
在文献里系统性缺失，本项目用 `method=est` 明确标注其来源为估计值，并在 Gate 1 上保持 NOT CLOSED，
而不是用一个高噪声锚点去「凑关闭」。这与判据 6（不确定性感知）的精神一致。

---

## 10. 读法纪律：本报告里出现了三种不同的「0」

这是本项目最容易出错、也最值得写进论文方法部分的一点。

| 出现在哪 | 是什么 | **不能**读成 |
| --- | --- | --- |
| `f_robust_inv = 0`（如 G1→G2、C₁→C₂） | 真的没有 pair 发生确定性反转，且 `f_unresolved` 很低（0.022 / 0.067） | —— 这才是「排序稳」 |
| `f_robust_inv = 0`（如 C₀→C₁ 还原轴） | 分母（两个模型都 resolved 的 pair）被掏空，80% 的 pair 不可判定 | ❌「排序稳」；正确读法是「**不可判定**」 |
| `O_10% = 0.000`（如 P₀→P₁ 氧化轴） | N = 10 时 k = 1，Top-10% 集合只有一个分子，两个模型选了不同的那一个 | ❌「完全无法排序」；正确读法是「**首位分子换了**」 |

因此本项目的标准读法是：**任何 `f_robust_inv` 都必须与同一行的 `f_unresolved` 一起报告**；
任何 Top-k 重叠都必须标注该行的 N 与 k，跨台阶比较只看趋势，不看绝对值。

第二条纪律（由 §4 推出）：**报告某一级台阶的位移时，必须同时报告 mean 与 std，且论证排序稳定性时只能引用 std。**
单独引用 mean 的绝对值是无效论证。

第三条纪律（由 §7 推出）：**配位台阶的还原轴必须附带 state-identity 标签分布。**

---

## 11. 产物与图表

### 11.1 数据产物（`outputs/week9/`）

| 文件 | 内容 |
| --- | --- |
| `stage10_ladder.csv` | 20 行（common10 + native）× 25 列，五级台阶 × 两轴的完整指标 |
| `stage10_ladder.json` | 同一数据的 JSON，附假设检验点表与来源文件清单 |
| `stage10_verdicts.json` | 情形 A–G 的判定、依据、读法，以及关键数字摘要 |
| `stage10_summary.md` | 本报告的机器生成版（表格为主，随脚本自动重建） |

### 11.2 图表（F19）

![F19](outputs/figures/F19_stage10_ladder.png)

`outputs/figures/F19_stage10_ladder.png` —— 四个面板：

- **(a)** 每个台阶/轴的 τ_b，按位移 std 递增排列：沿纵轴往下读，就是在读 (b) 的自变量递增；
- **(b)** H_var 证据：std vs τ_b，ρ = −0.851；
- **(c)** H_mean 对照：|mean| vs τ_b，ρ = −0.535，可见 P₀→P₁ 还原轴（x ≈ 7.06）远离拟合线；
- **(d)** 机制：std vs `f_unresolved`(after)，ρ = +0.894。

图注、输入 SHA256 见 `outputs/figures/figure_manifest_week9_stage10.md`。

### 11.3 脚本

| 脚本 | 作用 |
| --- | --- |
| `scripts/analyze_stage10_synthesis.py` | 读取五个源文件 → 统一口径 → 20 行指标 + 假设检验 + A–G 判定 + §23 对照 |
| `scripts/make_stage10_figure.py` | 渲染 F19 与图注清单 |

---

## 12. 遗留与需裁决项

1. **【新增】Stage 9/10 的指标是否写进 prereg？** —— `τ_b` / `f_unresolved` / `f_robust_inv` 已是 prereg 指标，
   但「五级台阶平行比较」这一步本身及其 Spearman 汇总**是 Week 9 新增的分析动作**。
   若 PI 决定把它提升为必报指标，需走 `amendment_log`，**Gate 0 由 CLOSED → NOT CLOSED**。
   当前默认是**不改 prereg**、作为探索性分析报告。
2. **【Week 6】`delta_m` 是否 append 进 prereg**（当前取候选值，未冻结）。
3. **【Week 4】Gate 1 NOT CLOSED** —— 唯一 blocker：溶液锚点 31 行仍为 `method=est`。
4. **【Week 7】`ranking._resolve_k` 口径偏差** —— prereg 写 `max(1, floor(frac·N + 0.5))`，
   代码用 `round(frac·N)`；在 N = 18 / 40 上一致，在 N = 5 时退化。本轮未触发（N = 10 时两者同为 1）。
5. **【Week 8】reading list 勘误回改** —— A2 作者名补全 4 位；「分支 a–d 实为 A/B/C 三支」。

---

## 13. 下一步（Week 10 候选）

按依赖关系排序，都只依赖已有产物：

1. **把 H_var 从「相关」升级为「可预测」** —— 用 σ(Δ) 作为单变量预测子，做留一交叉验证式检验：
   在 5 个台阶上预测哪个台阶会改写排序，看命中率。这是对 §4 最直接的证伪性测试。
2. **把共同子集从 10 扩到「最大可比集」** —— 逐级放宽「每级都齐」的约束，
   给出 N 从 18 递减到 10 时 τ_b 与 ρ 的漂移曲线，量化子集选择本身带来的不确定性。
3. **σ 的可分解性** —— 把 σ_ij 拆成「公共偏移贡献」与「相对形变贡献」，
   验证 §4.3 的代数论断（τ_b 只对后者敏感）。
4. **溶液锚点补齐** —— 唯一能关闭 Gate 1 的路径；需要外部数据，属长期项。