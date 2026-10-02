# Week 23 报告（Stage 24：批次 C/D 收尾）

> 上游：`docs/31_plan_revision_expert_review.md` 的「批次 C/D」——`R5`（措辞修订 + n = 3 符号检验）、`R8`（漏解靶向双腿）、`R12`（叙事重写）。
> 本文件由 `scripts/gen_week23_report.py` 从 `outputs/week23/` 的产物渲染；`--check` 逐字节复核。三个工作包**不新增冻结量**，唯一新增电子结构是 `structures/microsolvation/EC_m1_shell3.xyz`（须登记）。

---

## 0. 一句话结论

R5 的第三个配体在 GFN2-xTB 级继续同号且增量继续变小（dd(2->1) 氧化 -1.882 / 还原 -0.619 eV，dd(3->2) 氧化 -0.723 / 还原 -0.336 eV），与「次线性、与饱和一致」相容，但三个点定不出渐近线，不构成饱和的证明；R8 把「漏解要不要全局双算」压成一条安全定理——|d0-d1| <= A_axis，任何 |d0| >= A_axis 的 pair 都不可能翻转，实测 19/660（氧化）与 21/660（还原）次翻转 0 漏，靶向双腿与全双腿的 tau_b 最小值都是 1.0000，但它几乎不省钱（氧化省 28.3%、还原省 3.3%）；真正省钱的是只保护 Top-1 清单边界的变体（氧化省 91.7%、还原省 83.3%）；R12 因此把三条结论合并成对 v2「minimal information budget」的定性回答：闭式判据（q_ij <= sqrt(2)/z，可在花钱前预判）+ 介电层免费（|dE| x eps 约 2.1 eV 幂律）+ 配位饱和（第一壳之后次线性）——大规模筛选时，这几层可以不算。

---

## 1. R5：第三个配体的符号检验（GFN2-xTB 级）

### 1.1 层级声明（必须与数字同时引用）

- 引擎 **GFN2-xTB**（xtb 6.7.1pre），目标 **EC / m1**（donor = 4+5，bidentate），作业 14 个。
- 层级提醒（逐字）：GFN2-xTB, not r2SCAN-3c: absolute values must never be placed next to the docs/18 ladder; only sign and monotonicity are comparable
- 本节只回答一个问题：第三个配体的增量是否**继续同号、继续变小**。唯一的冻结台阶结论仍来自 `docs/18`（ORCA r2SCAN-3c），本节数值不写入任何冻结量。

### 1.2 阶梯（同一层级内部可比）

| n | 参考态 | 电荷/多重度 | IP (eV) | EA (eV) | dIP (eV) | dEA (eV) |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | free EC | 0 / 1 | 15.590 | 1.747 | 0.000 | 0.000 |
| 1 | [Li(EC)]+ | 1 / 1 | 19.487 | 8.039 | 3.897 | 6.291 |
| 2 | [Li(EC)2]+ | 1 / 1 | 17.605 | 7.420 | 2.015 | 5.672 |
| 3 | [Li(EC)3]+ | 1 / 1 | 16.882 | 7.084 | 1.292 | 5.336 |

### 1.3 增量与判据

| 量 | 氧化轴 | 还原轴 |
| --- | --- | --- |
| dd(2->1) = d(2) - d(1) | -1.882 | -0.619 |
| dd(3->2) = d(3) - d(2) | -0.723 | -0.336 |
| sign(dd(3->2)) == sign(dd(2->1)) | True | True |
| abs(dd(3->2)) < abs(dd(2->1)) | True | True |
| 比值 abs(dd(3->2)) / abs(dd(2->1)) | 0.384 | 0.543 |

**判定**：`consistent_with_saturation` —— 两个轴的 dd(3->2) 都与 dd(2->1) 同号，且绝对值更小 —— 第三个点与「次线性、与饱和一致」的形状相容。这只支持措辞「与饱和一致」，**不支持**「证明了饱和」：三个点仍然定不出渐近线。

### 1.4 跨层级的**无量纲**对照（只比形状比，不比绝对值）

| 轴 | r2SCAN-3c（`outputs/week8/stage9_shell_shifts.csv`） | GFN2-xTB（本节） |
| --- | --- | --- |
| 氧化 | -0.4080 | -0.4829 |
| 还原 | -0.2386 | -0.0984 |

两层的**绝对值一律不得并列**（GFN2-xTB 的 IP/EA 与 r2SCAN-3c 相差 eV 量级）。可搬运的只有形状比：氧化轴 -0.4080 vs -0.4829 接近，还原轴 -0.2386 vs -0.0984 不接近 —— 还原轴在 Stage 9 已被 state-identity 标记（C1 还原态在 11/12 个体系里电子落在 Li 上），xTB 与 r2SCAN-3c 对「电子落在哪」的判断不必一致，故这一条只作提示、不是结论。

### 1.5 措辞修订落点（本工作包的必做部分）

- `docs/18_week8_report.md`：L20/L47/L264/L266 改写为「与饱和一致」（consistent with saturation），并新增 §5.5「措辞修订（R5）」；「翻号」一律改写为**条件态语言**（M 与 [Li M]+ 是两个不同的化学物种，不是同一 observable 的高低精度）。
- `docs/12_week5_report.md`：§2.6 前加 R5 读法纪律 —— 还原轴 tau_b = -0.467 是**换号**但**不是精度比较**，禁止写成「加 Li+ 后电位变得更准」。
- `docs/10_week4_report.md`：L327「位移随介电常数饱和」→「快速衰减（Week 22 的 R4b 表明它其实是几乎严格的 1/eps 幂律）」。

---

## 2. R8：漏解靶向双腿（安全定理 + 代价）

> 背景：`docs/31` 的 R8。Stage 16 的结论是「漏解只在 pair 接近简并时才可能改变决策」，所以不必对全部格子双跑：只对接近简并的 pair 涉及的格子重跑双腿，其余格子保留单腿并在不确定性预算里加一项 **missed-solution allowance**。

- 决策量口径：`ox = (E_cation - E_neutral) * Ha2eV; larger = more stable`；`red = (E_anion - E_neutral) * Ha2eV; larger = more stable`。
- 决策网格每轴 120 个格子、660 对 pair；allowance 由 Stage 16 的 32 个 material cell 实测估计。
- 口径自检：与 Stage 16 的 `delta_ev` 列最大偏差 1.61e-05 eV —— 本节是**复制口径**，不重算能量。

### 2.1 allowance：漏解对单个格子的最大效应量

| 轴 | A_axis (eV) | 最坏格子 | material 中位数 (eV) | material p90 (eV) | A_axis / delta_m |
| --- | --- | --- | --- | --- | --- |
| 氧化 | **0.152252** | TMP @ eps = 5 | 0.134273 | 0.147105 | 21.7% |
| 还原 | **0.285963** | EMC @ eps = 1000 | 0.095349 | 0.282145 | 13.8% |

定义（逐字）：max over cells of |value_moread - value_default| on the decision quantity: the largest change a missed solution can make to any single cell。
对照冻结 delta_m：氧化 0.700245 eV、还原 2.074299 eV（`outputs/week6/delta_m_frozen.json`）。

### 2.2 安全定理（与可预报性无关）

- **不等式**：flip requires abs(d0 - d1) = abs(d0) + abs(d1) > abs(d0), and abs(d0 - d1) <= A_axis, so any pair with abs(d0) >= A_axis cannot flip。
- 读法：翻转要求默认臂间距 `abs(d0)` 被抹平，即 `abs(d0-d1) = abs(d0) + abs(d1) > abs(d0)`；而 `abs(d0-d1) <= A_axis`。所以只要 `abs(d0) >= A_axis`，这对 pair 就**不可能翻转**。靶向规则因此是**充分的**，而且它不需要预判哪个格子会漏解。
- 实测（delta = A_axis 靶向）：氧化轴 19/660 对发生翻转、还原轴 21/660 对，两轴各漏 **0** 个 —— 定理给出的 0 漏是实测确认的。

### 2.3 代价：安全，但几乎不省钱

| 轴 | delta 档位 | delta (eV) | 靶向格 / 全部格 | 省下 | 漏掉的翻转 |
| --- | --- | --- | --- | --- | --- |
| 氧化 | `allowance` | 0.152252 | 86 / 120 | 28.3% | 0 |
| 氧化 | `delta_m` | 0.700245 | 120 / 120 | 0.0% | 0 |
| 氧化 | `delta_star_post_hoc` | 0.146292 | 72 / 120 | 40.0% | **1** |
| 氧化 | `delta_star_post_hoc_inclusive` | 0.146292 | 72 / 120 | 40.0% | 0 |
| 还原 | `allowance` | 0.285963 | 116 / 120 | 3.3% | 0 |
| 还原 | `delta_m` | 2.074299 | 120 / 120 | 0.0% | 0 |
| 还原 | `delta_star_post_hoc` | 0.253422 | 112 / 120 | 6.7% | **1** |
| 还原 | `delta_star_post_hoc_inclusive` | 0.253422 | 112 / 120 | 6.7% | 0 |

以 delta = A_axis 靶向只省下 28.3%（氧化）/ 3.3%（还原）：**安全但几乎不省钱**，因为 12 个分子 x 10 个介电点的 pair 谱本来就密。
`delta_star_post_hoc` 是**事后**最紧 delta（用真实翻转反推）：它给出靶向比例的下界，且用严格判据会各漏掉边界那一对（EMC/TMP@eps=7 / AN/EMC@eps=1000），用 `nextafter` 收进边界后才 0 漏 —— 这正说明事后最紧 delta **永远不能当预报阈值**。

### 2.4 协议校验：靶向重跑与全双腿的排序一致

- 逐介电点（10 层）比较：靶向双腿 vs 全双腿的 tau_b 最小值 = **1.0000 / 1.0000**（氧化 / 还原）；Top-1/2/4 重叠最小值 = 1.000 / 1.000 / 1.000。
- 对照组（「什么都不做」的单腿 vs 全双腿）：tau_b 最小值 = **0.9394 / 0.8788** —— 漏解确实会改排序，不可忽略。

### 2.5 更省的变体：只保护 Top-k 清单边界

| 轴 | k | 边界格 / 全部格 | 省下 |
| --- | --- | --- | --- |
| 氧化 | 1 | 10 / 120 | 91.7% |
| 氧化 | 2 | 10 / 120 | 91.7% |
| 氧化 | 4 | 40 / 120 | 66.7% |
| 还原 | 1 | 20 / 120 | 83.3% |
| 还原 | 2 | 20 / 120 | 83.3% |
| 还原 | 4 | 56 / 120 | 53.3% |

只保护清单**边界**（半宽 = A_axis），不保护清单**内部次序**；内部翻转不影响「入选/落选」，所以这是可接受的弱化，也是唯一真正省钱的变体。

### 2.6 为什么策略只能是「事后靶向」而不是「事前预报」

R8 的正文结论包含**两次预测失败**（不可预报性本身正当化了靶向策略）：

- **发现集**：冻结规则 `gas_small_gap_value`（阈值 -0.0710）的 LOO 准确率 0.7083，多数类基线 0.7917，`beats_majority_baseline` = False；平衡准确率 0.6737、精确置换 p = 0.0116。
- **留出臂**（DEC、EA、FEC、MA、TEGDME、VC）：准确率 0.7500，真阳 **0**、假阳 1、真阴 9、假阴 2。
- **拆臂事后规则也失败**：cation `gas_small_gap_value` 准确率 0.6667 vs 基线 1.0000；anion `gas_spin_maxfrac` 准确率 0.6667 vs 基线 0.6667（两臂真阳都是 0）。
- **多变量上限**：2 特征 logistic LOO AUC 0.8211、留出验证准确率 0.7500 / 验证 AUC 0.8500 —— 用上更多描述符也补不回可预报性。

结论：靶向策略的**安全性**来自 2.2 的不等式，与「能否预报哪个格子会漏解」无关。因此 R8 只能写成「事后靶向 + 容许量」，不能写成「事前预报」。

### 2.7 登记状态（硬约束）

- `registration.registered` = **false**；字段 `missed_solution_allowance`。
- `config/prereg.yaml` §3 的 `variability_sources_to_separate` 登记了 **5** 项（逐字读自冻结件，本报告不重述以免漂移）；**missed-solution allowance 不在其中**。
- 因此它是**非注册项**：not one of the registered variability sources; carried here as an explicitly non-registered term and never silently treated as registered。

数据来源：`outputs/week15/stage16_cells.csv`、`outputs/week6/delta_m_frozen.json`、`outputs/week15/stage16_predictor.json`、`outputs/week15/stage16_holdout.json`、`config/prereg.yaml`。

---

## 3. R12：minimal information budget —— 大规模筛选时哪些层可以不算

> 本节**无新计算**，把项目已有的三条结论合并成对 v2「minimal information budget」主问题的定性回答。同一段文字同时落在 `成果输出/数据结果汇总.md` 的结论节、站点首页文案与 `README.md`（由交付脚本与站点构建器接线）。

### 3.1 闭式判据：可以在花钱之前预判

- Week 10（Stage 11）把用了六周的 `sigma_ij` 化简为闭式：`sigma_ij = |delta_i - delta_j| / sqrt(2)`。
- 由此得到一条无量纲判据：`f_unresolved(layer B, z) = Pr( q_ij > sqrt(2)/z ), q_ij = |delta_i - delta_j| / |DeltaP_ij|`（实测最大误差 z = 1 时 0.0e+00、z = 1.96 时 0.0e+00）。
- 临界割线斜率：z = 1.0 时为 1.4142；z = 1.96 时为 0.7215。

含义：一个 pair 会不会被判「不可分辨」，只取决于它沿目标轴的割线斜率 `q_ij` 与噪声倍数 z —— 这是**在提交任何 ORCA 作业之前**就能算出来的量。

### 3.2 介电层几乎免费：自相似、平行于轴

- Week 22（R4b，附加诊断）测到 `abs(dE) x eps` 从 eps = 7 到 1000 都是常数（2057 - 2178 meV），即残余几乎严格按 **1/eps** 衰减，prefactor 约 **2.13 eV/eps**。
- eps = 200 的残余最大只剩 **19.62 meV**，是氧化轴 delta_m（700.2 meV）的 **2.80%**。

含义：介电屏蔽近似一个**自相似的乘子**——它把整条位移向量近似等比例缩放，几乎不改变位移之间的相对结构，所以对排序是二阶效应；取一个中等 eps 就够，不必逐点扫。

### 3.3 配位在第一壳之后饱和（次线性）

- R5 的 n = 0..3 阶梯（GFN2-xTB，EC / m1）：dIP 0.000 -> 3.897 -> 2.015 -> 1.292 eV，dEA 0.000 -> 6.291 -> 5.672 -> 5.336 eV；增量 dd(2->1) = -1.882 / -0.619、dd(3->2) = -0.723 / -0.336（氧化 / 还原）。
- 两轴都**同号且绝对值更小** → 与「次线性、与饱和一致」相容；但三点定不出渐近线，措辞只能是 consistent with saturation（Week 8 的 Stage 9 用 12 个分子、2 个点得到同一形状）。
- 工程读法：**第一配位壳必须算**（它贡献 3.897 eV 量级的氧化位移）；第二、第三壳只做**是否换号**的抽查，不必逐一进入冻结台阶。

### 3.4 合并成一句话

`闭式判据（可在花钱前预判） + 介电层免费（自相似、平行于轴） + 配位饱和（次线性）` → 大规模筛选时，**介电层取一个中等 eps 不再逐点扫**、**配位层只算第一壳并对换号做抽查**、**分辨率则用 `q_ij <= sqrt(2)/z` 在提交前先筛掉不可能被判别的 pair**。这三条合起来，就是 v2「minimal information budget」的定性回答。

---

## 4. 与冻结件的关系

- `config/prereg.yaml`：**0 改动**（R8 的 allowance 明确登记为**非注册项**，不写入 §3）
- `config/scientific_definitions.yaml`：**0 改动**
- `data/anchors/solution_redox_anchors.csv`：**0 改动**
- 三个工作包都不改目标量、family 定义、筛选方向、delta_m、k/N、种子集或 splits；唯一新增电子结构是 `structures/microsolvation/EC_m1_shell3.xyz`（R5 的 n = 3 壳层，须登记）。

## 5. Gate 状态

Gate 0 CLOSED、Gate 1 NOT CLOSED。

Gate 0 保持 CLOSED：本周只做措辞、靶向分析与叙事，没有一条改动落进目标量、family 定义、筛选方向、delta_m、k/N、种子集或 splits。
Gate 1 的唯一 blocker 是**排序一致性层**（R7）：`data/anchors/within_series_ordering.csv` 现有 **0** 行已核验的 within-series 数值，判据要求 `n_pairs >= 18`、`tau_b >= 0.9`（阈值取自冻结的 `config/prereg.yaml`），核验结果为「取不到同源多溶剂数值」而非「遗漏」——因此该层保持 OPEN。绝对标定层（`solution_redox_anchors.csv` 的 `method=est` 行）按 `docs/31` R7 的裁决降级为**长期限制**，不再作为 blocker。

## 6. 限制

**R5**
- 层级是 GFN2-xTB，不是 r2SCAN-3c：绝对值与 `docs/18` 相差 eV 量级，**不得并列**。
- 分子只有一个（EC / m1）；四个跂不是同一次运行的产物（n = 1/2 复用既有 xTB 几何，n = 0/3 在本脚本内优化），几何噪声没有被单独分离。
- 第三配体放置沿用 Stage 9 的确定性规则（donor x fibonacci 方向 x roll），给出的是该规则下的最低能放置，不是全局最优壳层。
- 三个点不构成饱和的证明，只是与饱和形状相容；本工作包**不写入任何冻结量**。

**R8**
- `missed-solution allowance` 是**非注册项**：它不在 `config/prereg.yaml` 的已注册变异来源里，不得静默当成已注册的不确定度来源。
- allowance 是**效应量上界**（Stage 16 的 32 个 material cell 实测），不是分布：它给的是「单个格子最多被改多少」，不能当概率用。
- 靶向策略的安全性来自不等式 `abs(d0-d1) <= A_axis`，与可预报性无关；两次预报尝试都失败，所以结论只能是「事后靶向 + 容许量」。
- `delta_star_post_hoc` 是事后口径，只给靶向比例下界，**永远不能当预报阈值**。

**R12**
- 本节无新计算，是对已有结论的合并叙述；介电层与配位饱和两条各自继承其层级约束。
- 「介电层免费」在绝对能量上是**近似**（1/eps 幂律，残余非零），不是恒等式。

## 7. 产物清单

| 产物 | 内容 |
| --- | --- |
| `outputs/week23/shell3_xtb_sign_test.{json,csv,md}` | R5 的 14 个 xTB 作业与 n = 0..3 阶梯 |
| `structures/microsolvation/EC_m1_shell3.xyz` | R5 唯一新增的电子结构（n = 3 壳层） |
| `outputs/_week23_scratch/shell3/` | R5 的原始 xTB 文本 |
| `outputs/week23/targeted_two_guess.json` | R8 的 allowance、阶梯、协议校验与预报失败 |
| `outputs/week23/targeted_two_guess.csv` | R8 逐格效应量 |
| `outputs/week23/targeted_two_guess_pairs.csv` | R8 逐 pair 间距与翻转标记 |
| `outputs/week23/targeted_two_guess.md` | R8 的可读摘要 |
| `docs/34_week23_report.md` | 本报告 |

---

生成时间（UTC）：R5 = 2026-10-02T03:15:54.237643+00:00；R8 = 2026-10-02T03:12:12.831864+00:00。

本报告由 `scripts/gen_week23_report.py` 渲染；`--check` 逐字节复核。
