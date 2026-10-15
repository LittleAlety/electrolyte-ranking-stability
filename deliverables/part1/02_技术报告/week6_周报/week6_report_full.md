# 13 Week 6 报告：Stage 6 不确定性感知排序分析

- 项目：电解液溶剂 ranking 稳定性（decision-centric ranking stability）
- 对应执行计划：Stage 6「不确定性感知排序分析（预注册统计计划）」，第 9 周
- 日期：2026-09-29
- 上游依据：`核心文件/ranking-electrolyte-materials-v2.md`；详细执行计划 v1.0 §6（纯文本见 `outputs/_week5_scratch/plan_docx.txt`）；冻结预注册 `config/prereg.yaml`
- 本轮新增产物：`outputs/week6/*`、`structures/conformers/*`、`outputs/figures/F14/F15`、`tests/test_t6_conformer_spread.py`、`tests/test_delta_m.py`、`tests/test_stage6.py`

---

## 1. 本轮解决的问题

Week 5 结束时有两个卡口：**（a）** Stage 6 的全部指标虽然已经在 `src/electrolyte_ranking/ranking.py` 里实现，但一直只跑「临时口径」`|ΔP_ij| ≥ z·σ_ij`（z = 1.0）；预注册里那个**固定兜底容差 `delta_m`** 从未被赋值，`ranking.resolved_mask()` 的 `tolerance` 参数从未被启用。**（b）** Week 5 遗留的 6 条冲突里，有 4 条没有收口。

本轮按四个任务（T6/T7/T8/T9）把这两件事一起做完：

| 任务 | 内容 | 关键产物 |
|---|---|---|
| **T6** | 构象系综展宽 `σ_conf`（`delta_m` 的构象项） | `outputs/week6/t6_conformer_spread.*`、`structures/conformers/` |
| **T7** | C1 `[Li M]+` 优化几何的**虚频检查**（Week 5 冲突 5） | `outputs/week6/t7_c1_freq_check.*` |
| **T8** | `delta_m` 组装（按预注册 source_rule + docx §6.2 的 max 规则） | `outputs/week6/delta_m_frozen.*` |
| **T9** | 三口径（`z_only` / `floor_only` / `docx_max`）下的全套 Stage 6 指标 | `outputs/week6/stage6_decision_stability.*`、`F14`、`F15` |

**一句话结论：** 启用 `delta_m` 之后，**还原轴几乎整体失效**——在 T8 候选（`docx_max`）下，P1→P2 与 C0→C1 的还原比较里「双方都解析」的 pair 数从 46 / 4 掉到 **0 / 0**；因此 `f_robust_inv = 0` 在这些情形下**不是**「排序稳定」的证据，而是**分母塌成零**的结果。这正是预注册 `unresolved_fraction.must_report` 那条「某模型 inversion 很少但绝大多数 pair 未解析时，不得称为筛选稳定」要拦的误读。

---

## 2. T6：构象系综展宽 `σ_conf`

### 2.1 系综如何构建（规则在读数前写定）

仓库里此前所有 P0 / P1 / C1 数值都是在**单一** GFN2-xTB 几何（G1）上算的，所以「构象不确定度」这一项一直没有数据。`scripts/build_conformers.py` 补上这一块：

- RDKit ETKDGv3 嵌入 → MMFF 预优化 → 每个构象**逐构象冻结**单线程 GFN2-xTB `--opt`（`OMP_NUM_THREADS=1`，保证确定性）；
- **G1 参考几何强制入系综**，编号 `conf_0` 且豁免数量上限。理由写在脚本里：仓库所有 P0/P1/C1 数值都是在 G1 上测的，若系综不含 G1，`σ_conf` 就在测量势能面的另一片区域；它的能量用**冻结单点**重算，与其它构象同口径；
- 稀释规则（都是**选择规则**，在读数前固定）：能量窗口 12.0 kJ/mol（相对全系综最低能）、重原子 RMSD（Kabsch 对齐、去 H）0.35 Å、额外构象上限 4 个；生成期的 `pruneRmsThresh = 0.3` 属于**生成参数**，不是选择规则；
- 结果：**12 分子 / 32 个保留构象**。刚体分子（AN、DMC、DMSO、DOL、EC、GBL、PC、SL）确实只找到 1 个独特构象，脚本按声明**强制保留次低者**以维持「系综」语义，其构象展宽因此诚实为 0；柔性分子（DME 5、TMP 5、EMC 3、SN 3）才给出真实展宽。

### 2.2 P0 层（GFN2-xTB，Koopmans）

每个构象一个中性单点，取 `p0_ox = -ε_HOMO`、`p0_red = +ε_LUMO`（与 `scripts/run_broad_pool_p0.py` 完全同口径）。

| 目标 | `σ_conf` [eV] | 90 分位展宽 [eV] | 中位数展宽 [eV] | 最大展宽 [eV] | n |
|---|---|---|---|---|---|
| 氧化 | **0.0207** | **0.0350** | 0.0000 | 0.2027 | 12 |
| 还原 | **0.0951** | **0.2212** | 0.0000 | 0.7443 | 12 |

逐分子（单位 eV）：只有 4 个分子有非零展宽 —— DME（IP 0.203 / EA 0.744）、TMP（0.036 / 0.224）、SN（0.022 / 0.192）、EMC（0.025 / 0.007）；其余 8 个为 0（刚体，系综只有一个独特构象）。

**机制读法：** 还原侧的构象展宽（0.095 / 0.221 eV）比氧化侧（0.021 / 0.035 eV）大一个量级。这与「还原由 LUMO 控制、而 LUMO 对 O–C–O 骨架的扭转/醚链构象敏感」一致——氧化侧的 HOMO 主要由氧孤对与 C=O 决定，构象变化影响小。中位数展宽为 0 说明**半数以上分子根本没有构象自由度**，所以 docx 用的是 90 分位而非中位数，这是对的选择。

### 2.3 P1 层（r2SCAN-3c，ORCA）

对同一批 32 个构象各跑 3 个电子态（neutral / cation / anion）单点，`IP = E(M+) − E(M)`、`EA = E(M) − E(M−)`，与 T1 的垂直量定义完全一致（唯一变量是构象）。**96 个作业全部成功**（`n_failures = 0`，12/12 分子完整）。

| 目标 | `σ_conf` [eV] | 90 分位展宽 [eV] | 中位数展宽 [eV] | 最大展宽 [eV] | n |
|---|---|---|---|---|---|
| 氧化 | **0.0200** | **0.0907** | 0.000007 | 0.1478 | 12 |
| 还原 | **0.0581** | **0.2303** | 0.00006 | 0.4334 | 12 |

逐分子（单位 eV）：DME（IP 0.148 / EA 0.433）、SN（0.089 / 0.240）、EMC（0.091 / 0.147）、TMP（0.048 / 0.085）有非零展宽；PC / SL 只有 ∼1e−4 的数值噪声；其余 6 个刚体分子为 0。

**P0 → P1 的对比：** `σ_conf` 几乎不变（氧化 0.0207 → 0.0200，还原 0.0951 → 0.0581），90 分位展宽在氧化侧从 0.035 升到 0.091 eV。也就是说，“构象展宽”这个小量本身对方法不敏感——它是几何效应，不是电子结构效应。这对 `delta_m` 的含义很重要：构象项是**几何侧**的下限，不会因为换泛函而变大。

### 2.4 三个 σ 同口径对比

三个台阶用的是**同一个估计量**（逐分子展宽在审计子集上的总体标准差 `statistics.pstdev`）与**同一批 12 个分子**：

| 台阶 | 定义 | σ(氧化) [eV] | σ(还原) [eV] |
|---|---|---|---|
| 构象 `σ_conf`（T6, P0） | 同一分子不同低能构象的展宽 | 0.0207 | 0.0951 |
| 几何 `σ_geom`（T2） | G1 → r2SCAN-3c Opt+Freq 驻点 G2 的位移 | 0.0494 | 0.0764 |
| 环境 `σ_env`（T3, bare CPCM ε=10） | 气相 → 连续介质的位移 | 0.2125 | 0.2329 |

**读法：** 在**同一个分子内部**做扰动时，构象与几何的贡献都在 0.02–0.10 eV 量级，环境在 0.21–0.23 eV 量级。三者都远小于下面第 3 节的方法项（0.70 / 2.07 eV）。

---

## 3. T8：`delta_m` 组装

### 3.1 规则原文（`config/prereg.yaml` → `pair_comparison.delta_m`）

> `meaning`：与方法不确定度无关的固定 pair tolerance，兜底阈值，单位 kJ/mol
> `per_objective`：oxidation 与 reduction 各自独立确定，不允许共用一个未经检验的值
> `source_rule`：(1) 外部 anchor 自身的实验离散度 → (2) method audit 中同一分子在不同 method / conformer 下的 target quantity 离散度 → (3) `delta_default`
> `delta_default`：2.0 kJ/mol（= 0.0207 eV）
> `units_policy`：`dP_ij` 与 `delta_m` 必须使用同一单位（默认 kJ/mol）

执行计划 docx §6.2 的合成规则：`delta_m = max(构象系综 90 分位展宽, 方法审计 inter-method 展宽, 0.05 eV 下限)`。

### 3.2 source_rule (1) 不可用

`scripts/analyze_delta_m.py` 对 `data/anchors/solution_redox_anchors.csv` 做了机器可读的可用性检查：**31 行 / 31 个 series / 0 个重复测量 series / 0 行非 `est` 方法**。也就是说表里没有任何一个物种带有重复测量，**无法构造 within-series 实验标准差**。因此按 source_rule 的顺序落到 (2)。

（这与 `docs/06` §4.3 及 `data/anchors/solution_anchor_verification.md` 的核验结论一致：31 行**全部**仍为 `est`，Gate 1 因此保持 NOT CLOSED。详见第 6 节。）

### 3.3 方法项（inter-method 展宽）

本仓库的「method audit」就是 **P0 ↔ P1 在同一冻结几何上的逐分子位移**（与 C1 四台阶审计里的 `method` 步完全同一定义，见 `outputs/week5/c1_summary.json` 的 `four_step_sigma.definition`），这里限制在**同一批 12 个审计分子**上，以便与构象项共口径：

| 目标 | 逐分子位移 P1−P0 的均值 [eV] | 逐分子位移的总体标准差 `σ_method` [eV] | 90 分位 |位移| [eV] |
|---|---|---|---|
| 氧化 | −1.373 | **0.7002** | 1.839 |
| 还原 | +7.378 | **2.0743** | 9.034 |

还原侧的位移均值高达 +7.4 eV、逐分子标准差 2.07 eV，**这正是 Koopmans 定理对 EA 失效**留下的痕迹（P0 用 `+ε_LUMO` 近似 EA，而中性闭壳层的 LUMO 常常预示一个不束缚的阴离子）。这一点在 Week 4 已经定性看到（`F5`），本轮第一次把它量化成 `delta_m` 的数值。

### 3.4 四个数值

| 层 | 目标 | `delta_m` [eV] | `delta_m` [kJ/mol] | 主导项 |
|---|---|---|---|---|
| P0 | 氧化 | **0.7002** | 67.563 | 方法 |
| P0 | 还原 | **2.0743** | 200.139 | 方法 |
| P1 | 氧化 | **0.7002** | 67.563 | 方法 |
| P1 | 还原 | **2.0743** | 200.139 | 方法 |

**主导项是方法项，不是构象项。** 构象项（0.035 / 0.221 eV）比方法项小 1–2 个量级；0.05 eV 下限在当前证据下从未成为约束。这直接回答了「`delta_m` 到底由 `σ_conf` 还是 `σ_method` 主导」。

`outputs/week6/delta_m_frozen.json` 另外记了 5 个候选口径供敏感性检查：`z_only`=0、`floor_only`=0.05 eV、`conformer_p90`=0.035/0.221 eV、`method_only`=0.700/2.074 eV、`docx_max`=0.700/2.074 eV。

### 3.5 与预注册 units_policy 的一致性

预注册默认单位是 kJ/mol，本报告同时给出 kJ/mol（换算常数 **1 eV = 96.48533 kJ/mol**，F = 96485.33212 C/mol）。Stage 6 的 `dP_ij` 是**气相垂直 IP/EA 的能量差**，不涉及任何电极，因此**没有**任何 reference-electrode 换算需要记录——这正是 `units_policy` 中「若换算为 V，必须记录换算常数与 reference electrode」那一支不适用。

### 3.6 冻结前必须由操作者裁决的事项

`scripts/analyze_delta_m.py` **没有**、也不应该自动写入 `config/prereg.yaml`。原因是 `scripts/freeze_gates.py` 一见 `amendment_log` 非空就把 Gate 0 记为未关闭（`result.closed = False`），这是要由人拍板的动作。候选文件里记了两条路：

- **选项 A**：把上表数值以 append-only 方式追加进 `pair_comparison.delta_m` 的 `amendment_log`。代价：Gate 0 会因为存在 amendment 而显示未关闭，直到周报与 gate 记录把这次追加解释清楚。
- **选项 B**：数值冻结在 `outputs/week6/delta_m_frozen.json` + 本报告，`config/prereg.yaml` 保持**逐字节不变**。代价：与 docx §6.2「分析脚本从预注册文件读取，不写死」的措辞有张力；缓解办法是 Stage 6 脚本把该文件列为显式输入并在产物里回链（已实现：`stage6_decision_stability.json` 的 `delta_m_candidates` 与逐行 `delta_m_source`）。

**目前采用选项 B**（本轮未改预注册），因此 Gate 0 仍为 CLOSED、`amendment_log` 仍为空。

另外两条口径问题一并留待裁决：
1. **P1 层的 method term** 复用了 P0↔P1 的证据（本仓库内 P1 层没有第二个同层级方法可对照）；若认为 P1 应另取证据，则 `δ_m(P1) = max(构象项, 0.05 eV)`。
2. **下限的数值**：预注册 `delta_default = 2.0 kJ/mol`（0.0207 eV）与 docx 下限 `0.05 eV`（4.8242 kJ/mol）**不是同一个数**。本表按 docx 取 0.05 eV 下限，把 2.0 kJ/mol 保留为 source_rule (3) 的兜底；两者差别在当前证据下不影响结果（方法项远大于二者）。
---

## 4. T9：Stage 6 决策稳定性（三口径）

### 4.1 三个口径

| 口径 | `delta_m` | 含义 |
|---|---|---|
| `z_only` | 0（等于不启用固定容差） | Week 5 及之前的临时口径，作为对照基线 |
| `floor_only` | 0.05 eV | 只看规划文档的数值下限，隔离「证据驱动」部分的效果 |
| `docx_max` | 0.7002 eV（氧化）/ 2.0743 eV（还原） | 主口径：完整 docx §6.2 合成规则（T8 候选） |

判据（全部来自预注册）：`unresolved ⇔ |ΔP_ij| < delta_m 或 |ΔP_ij| < z·σ_ij`，z = 1.0；`f_unresolved = N_unresolved / C(N,2)`；`f_robust_inv = N_robust / N_pairs_resolved_in_both`；`σ_ij` 由两个 realization 自身给出（`quantify_method_sigma`，`ddof=1`），沿用 `scripts/analyze_p1_core_set.py` 的口径。`τ_b` 给 20 seed × 2000 次 percentile bootstrap 的区间中位数。

### 4.2 主表（`docx_max` 口径）

| 层对 | 目标 | n | τ_b [CI95] | ρ | f_unresolved（下/上） | 双方均解析 pair | delta_m 起决定作用的 pair | f_robust_inv | O_20% | R_20% |
|---|---|---|---|---|---|---|---|---|---|---|
| P0→P1 | 氧化 | 12 | 0.667 [0.133, 1.000] | 0.776 | 0.636 / 0.364 | 22 / 66 | 24 | 0.000 | 0.00 | 1.218 |
| P0→P1 | 还原 | 12 | 0.545 [−0.016, 0.900] | 0.741 | 0.530 / **1.000** | **0 / 66** | 30 | 0.000 | 1.00 | 0.000 |
| P1→P2 | 氧化 | 12 | 0.909 [0.700, 1.000] | 0.972 | 0.333 / 0.379 | 39 / 66 | 25 | 0.000 | 1.00 | 0.000 |
| P1→P2 | 还原 | 12 | 0.848 [0.533, 1.000] | 0.923 | **0.985 / 1.000** | **0 / 66** | 63 | 0.000 | 1.00 | 0.000 |
| C0→C1 | 氧化 | 10 | 0.689 [0.150, 1.000] | 0.770 | 0.311 / 0.333 | 23 / 45 | 9 | 0.000 | 1.00 | 0.000 |
| C0→C1 | 还原 | 10 | **−0.467 [−0.950, 0.105]** | −0.552 | **0.978 / 1.000** | **0 / 45** | 29 | 0.000 | 0.00 | 0.457 |

### 4.3 `delta_m` 到底改变了什么

| 层对 | 目标 | f_unresolved(下) z_only → floor → docx_max | f_unresolved(上) z_only → floor → docx_max | f_robust_inv（三口径） |
|---|---|---|---|---|
| P0→P1 | 氧化 | 0.348 → 0.348 → **0.636** | 0.106 → 0.106 → **0.364** | 0 / 0 / 0 |
| P0→P1 | 还原 | 0.227 → 0.227 → **0.530** | 0.682 → 0.682 → **1.000** | 0 / 0 / 0 |
| P1→P2 | 氧化 | 0.076 → 0.076 → **0.333** | 0.136 → 0.136 → **0.379** | 0 / 0 / 0 |
| P1→P2 | 还原 | 0.091 → 0.091 → **0.985** | 0.258 → 0.258 → **1.000** | 0 / 0 / 0 |
| C0→C1 | 氧化 | 0.178 → 0.178 → **0.311** | 0.200 → 0.200 → **0.333** | 0 / 0 / 0 |
| C0→C1 | 还原 | 0.444 → 0.444 → **0.978** | 0.800 → 0.822 → **1.000** | 0 / 0 / 0 |

三条可直接引用的结论：

1. **0.05 eV 下限几乎不起作用。** `z_only` 与 `floor_only` 的 f_unresolved 逐行相同（唯一例外：C0→C1 还原上侧 0.800 → 0.822）。原因很直接：σ_ij 的中位数本身就有 0.14–1.29 eV，`z·σ_ij` 早已把 0.05 eV 盖过。
2. **证据驱动的 `delta_m` 一到，还原轴整体塌掉。** 「双方均解析」的 pair 数：P0→P1 还原 12 → 0；P1→P2 还原 46 → 0；C0→C1 还原 4 → 0。氧化侧温和得多（39 → 22、53 → 39、30 → 23），因为氧化侧方法项只有 0.70 eV。
3. **`f_robust_inv = 0` 在还原轴上是「无意义的 0」，不是「稳定」。** 按预注册定义 `f_robust_inv = N_robust / N_pairs_resolved_in_both`，分母为 0 时该函数返回 0.0（`ranking.robust_inversion_fraction` 的文档就写了这一点）。所以第 4.2 节必须并列报出「双方均解析 pair 数」这一列——单看 `f_robust_inv` 会把「什么都没解析」误读成「一点都没翻转」。这正是预注册 `unresolved_fraction.must_report` 那条强制条款要拦的误读。

### 4.4 家族内 / 跨家族

| 层对 | 目标 | 家族内 pair | 跨家族 pair | 家族内 f_unresolved(下) | 跨家族 f_unresolved(下) |
|---|---|---|---|---|---|
| P0→P1 | 氧化 | 4 | 62 | **1.000** | 0.613 |
| P0→P1 | 还原 | 4 | 62 | **1.000** | 0.500 |
| P1→P2 | 氧化 | 4 | 62 | **1.000** | 0.290 |
| P1→P2 | 还原 | 4 | 62 | **1.000** | 0.984 |
| C0→C1 | 氧化 | 2 | 43 | **1.000** | 0.279 |
| C0→C1 | 还原 | 2 | 43 | **1.000** | 0.977 |

**读法：** **同家族内的分子对在 `docx_max` 下 100% 不解析**——同族分子的 IP/EA 本来就彼此接近（例如 EC 与 PC），而容差 0.70 / 2.07 eV 大于它们的真实差距。因此「跨家族的粗分类」还站得住（氧化侧跨家族 f_unresolved 只有 0.28–0.61），**「同族内部谁更稳」这个精细问题在当前方法与证据下是不可回答的**。这是本轮最有物理意义的一条结论。

另外，`probabilistic pair ordering` 的 0.9 / 0.1 判据下，**decided 比例在所有层对上都是 0.00–0.045，undecided 0.955–1.000**：即没有任何一对分子能达到 p > 0.9 的强证据等级。

### 4.5 未报告项

`threshold_decision_error` 记为 **`not_applicable`**。`config/prereg.yaml` 的 `threshold_decisions.if_unavailable` 规定无合规外部阈值来源时必须记 `not_applicable`，**不得**用数据分位数临时替代；本 objective 集合没有登记合规的外部设计阈值（气相垂直 IP/EA 的「设计阈值」来自溶液相稳定性窗口，而溶液锚点 31 行全部为 `est`，见第 6 节）。

---

## 5. T7：C1 `[Li M]+` 优化几何的虚频检查（Week 5 冲突 5 收口）

Week 5 的 C1 扫描只跑了 `Opt`，没有 Hessian，所以 `docs/12` §7 只能写「未检虚频」。本轮不改动 Stage 5 的任何几何与数值，只**追加**一次**纯 Freq**（`orca.JOB_FREQUENCY`）在**已经优化好**的 `outputs/week5/c1/<NAME>/<NAME>_m1_G2Li.xyz` 上：

- 为什么不用 `run_c1_li_coordination.py --freq`：那条路会重跑 `Opt+Freq`，即对一个**已经收敛**的几何再优化一遍，白花机时；最小判据要的是「驻点处的 Hessian」。
- QC 判据采用 THEMol 数据集对自身 Hessian 子集的做法（英文原句见 `outputs/_week6_scratch/themol_note.md`）：**剔除平动/转动对应的六个近零模**后，其余本征值必须全为正，才确认是局部极小。ORCA 自己会把负频标为 `***imaginary mode***`，本表同时记录标记计数与最低的若干模式。

| 分子 | 状态 | 模式数 | 虚频数 | 最低非零模式 (cm⁻¹) | 虚频位置 (cm⁻¹) | 是极小？ |
|---|---|---|---|---|---|---|
| EC | ok | 33 | **1** | −80.4, 60.5, 64.9 | **−80.4** | **False** |
| DMC | ok | 39 | 0 | 96.4, 110.9, 147.7 | — | True |
| DME | ok | 51 | 0 | 75.1, 123.3, 161.3 | — | True |
| DOL | ok | 36 | 0 | 163.4, 207.1, 245.8 | — | True |
| GBL | ok | 39 | 0 | 82.9, 99.8, 176.6 | — | True |
| SL | ok | 48 | 0 | 64.3, 144.8, 219.1 | — | True |
| DMSO | ok | 33 | 0 | 117.8, 127.2, 186.0 | — | True |
| AN | ok | 21 | 0 | 130.8, 131.2, 411.1 | — | True |
| SN | ok | 33 | 0 | 109.6, 156.6, 205.3 | — | True |
| TMP | ok | 54 | 0 | 56.0, 58.2, 78.5 | — | True |

汇总：**10 / 10 作业成功，9 个是已确认的局部极小，1 个是鞍点。**

**结论：** EC 的 `[Li EC]+` 在 **−80.4 cm⁻¹** 处有一个虚频（其后是 +60.5 / +64.9 cm⁻¹，间隔明显，不是数值噪声），按 ORCA 自己的标记记 `imaginary_mode_unresolved`；其余 9 个分子没有虚频，最低非零实模式落在 56–163 cm⁻¹。

这直接影响 `docs/12` §7 的表述：C1 的数值**不能**再一律称为「已优化到极小」。EC 的 C0→C1 位移（+4.32 eV / +6.16 eV）是在一个鞍点上测的，其物理解释需要打折扣。但本轮**不改动** Stage 5 的任何几何或数值（重优化属于一次口径变更，需要单独的记录与预算），只把这个事实如实登记。

---

## 6. Week 5 遗留冲突的收口状态

| # | 冲突 | 本轮状态 |
|---|---|---|
| 1 | `delta_m` 数值未冻结、`resolved_mask` 的 `tolerance` 从未启用 | **已收口**：T8 给出四个数值与来源链，T9 首次启用 `tolerance` 并给出三口径对比。预注册仍按选项 B 保持逐字节不变（Gate 0 仍 CLOSED），是否改写留待 PI 裁决（§3.6）。 |
| 2 | `docs/06` §4.3 两处引用错配 | **已确认并更正作者名**。①`10.1149/1.1838419` 实为 **Xu & Angell**, *JES* **145**, L70–L72 (1998)，讲的是**非环脂肪砜**（乙基甲基砜）报 5.8 V，**不支持** SL 行；原文档与 CSV 误写为「Ue et al.」，已在 `docs/06`、`data/anchors/README.md`、`data/anchors/solution_anchor_verification.md`、`data/anchors/solution_redox_anchors.csv`（2 行 source_note）、`scripts/audit_solution_anchors.py` 登记表五处统一更正。②`10.1149/1.1415547`（Zhang & Kostecki 2001）摘要逐字为 "The reduction potentials for all five organic carbonates were above 1 V (vs. Li/Li+)"，与 EC 行 0.9 V 直接冲突，且条件是 THF 稀溶液 CV ≠ 行内纯 EC + 1 M LiPF6 + LSV。**两处都在 `docs/06` §4.3 与 `data/anchors/solution_anchor_verification.md` 记录为「引用不支持该行」。** 更正后 `scripts/audit_solution_anchors.py` 输出 `consistency: OK`，`scripts/validate_anchors.py` 输出 `RESULT: PASS`（0 error / 0 warning）。 |
| 3 | SL「4.65 V vs Li/Li⁺」口径 | **已定性**：唯一逐字出处是 `outputs/_anchor_retrieval_raw.md:210`，即 Borodin *Curr. Opin. Electrochem.* 2019 综述正文转述的**量子化学计算预测**（1 m LiFSI-SL，vs Li/Li⁺）。本次尝试取该综述全文**只拿到摘要（付费墙）**，无法独立复核，故只能记为「项目内转述、待原始出处核验」。CSV 里 SL 现行值仍是 4.9 V / `est`，**没有**把 4.65 V 写进去。 |
| 4 | `dGdG_bind` 是否升级为热校正层级 | **维持现状（试剂级相对量，不上热校正）**。理由：`δ_m` 的构象项本轮已量化（0.035 / 0.221 eV），它本身就是「未做热校正」这一近似的量级上界；把 `dGdG_bind` 升级为热校正层级需要 `Opt+Freq` 全部配位 motif（≥20 个态）的热化学，属于新的预算项，不应在 Stage 6 内顺手改。记录在 `docs/11` 偏差表 D5/D6 的相邻条目。 |
| 5 | C1 的 m1 是否需要补 Freq | **已收口**：见第 5 节，10 个分子全部补了纯 Freq。 |
| 6 | Gate 1 唯一 blocker：溶液锚点 31 行 / 16 物种全部 `method=est` | **仍未关闭，且本轮证明了它不该被草率关闭**。独立核验（`outputs/_week6_scratch/anchor_verification.md`）结果：`verified` 0 行、`mismatch` 8 行、`not_found` 7 行、`needs_paywall` 16 行；没有任何一行在「纯溶剂 + 1 M LiPF6 + LSV + vs Li/Li⁺」条件下存在可引用的一手数值。核验同时确认 source_rule (1) 所需的「同一实验系列内重复测量标准差」在全表中**不存在**。 |

---

## 7. 已知限制

1. **`delta_m` 尚未写入预注册**（选项 B）。`config/prereg.yaml` 逐字节未改，改动需要 append-only `amendment_log`，并会让 Gate 0 显示未关闭；这是留给 PI 的显式裁决项。
2. **P1 / P2 / C1 层的 `delta_m` 复用了 P0↔P1 的方法证据**。本仓库内这些层没有第二个同层级方法可对照，逐行 `delta_m_source` 字段已标注。
3. **构象系综是「低能构象 + 预先声明规则」，不是穷举**。窗口 12 kJ/mol、RMSD 0.35 Å、额外上限 4 个；刚体分子只有 1 个独特构象（展宽诚实为 0）。这不影响结论方向（构象项比方法项小 1–2 个量级），但不应把 `σ_conf` 当作构象空间的完整积分。
4. **`σ_method` 是逐分子位移总体标准差，不是误差传递到 pair 差分的标准做法**。选择它的理由是「与 C1 四台阶审计、与 T6 构象项共口径」；`method_p90_abs`（1.839 / 9.034 eV）作为更保守的替代口径已并列记录在 `delta_m_frozen.json` 里。
5. **`f_robust_inv = 0` 不能单独引用**。还原轴上分母为 0（§4.3），必须与「双方均解析 pair 数」并列阅读。
6. **probabilistic pair ordering 用的是解析正态模型**（每个分子取值 ~ N(均值, s²)，s = |v_A − v_B|/√2 由两个 realization 给出），不是后验抽样；0.9/0.1 判据下的 decided 比例因此在所有层对上都接近 0。
7. **C1 的 EC 是鞍点**（见第 5 节）。这会影响 EC 的 C0→C1 位移的物理解释，但不改变 Stage 5 的既有数值（本轮不改几何）。
8. **`threshold_decision_error` 未计算**，原因见 §4.5。
9. Stage 6 只覆盖 12 分子审计子集（P0/P1/P2）与 10 分子 C1 子集；`C(12,2)=66`、`C(10,2)=45` 个 pair 的样本量下，`τ_b` 的 bootstrap 区间普遍很宽（例如 P0→P1 还原 [−0.016, 0.900]），**区间含 0 即表示该层对的排序一致性根本没有建立**。

---

## 8. 复现命令

```powershell
cd "E:\Claude Code\电解液溶剂-HB\电解液溶剂HB-Code"
$env:PYTHONIOENCODING = "utf-8"

# T6 构象系综（RDKit 嵌入 + GFN2-xTB 逐构象弛豫）
.venv\Scripts\python.exe scripts\build_conformers.py --force --n-confs 24 --keep 4 --jobs 8
# T6 σ_conf：P0（便宜，秒级）与 P1（96 个 r2SCAN-3c 单点）
.venv\Scripts\python.exe scripts\run_t6_conformer_spread.py --layer p0 --p0-jobs 8
.venv\Scripts\python.exe scripts\run_t6_conformer_spread.py --layer p1 --jobs 2 --nprocs 8  --timeout 7200
# T7 C1 虚频检查（纯 Freq，不重新优化）
.venv\Scripts\python.exe scripts\run_c1_freq_check.py --jobs 2 --nprocs 8
# T8 delta_m 组装（不写预注册；产出候选文件）
.venv\Scripts\python.exe scripts\analyze_delta_m.py
# T9 Stage 6 决策稳定性 + 图
.venv\Scripts\python.exe scripts\analyze_stage6.py
.venv\Scripts\python.exe scripts\make_stage6_figure.py
# 单元测试（基线 390 + 本轮新增 39 = 429）
.venv\Scripts\python.exe -m pytest tests -o addopts="" -q
```