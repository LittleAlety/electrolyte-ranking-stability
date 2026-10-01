# Week 21 报告 —— 批次 A：把结题前必须堵掉的五个统计/措辞漏洞堵上

> 上游：`docs/31_plan_revision_expert_review.md`（外部评审的可执行条目表 R1–R12）。
> 本轮只做**批次 A**（R1 + R10、R2、R3、R6、R4a）：全部为**纯分析**，
> **零**新增电子结构作业、**零**冻结件改动。
> 冻结件状态：`config/prereg.yaml` 与 `config/scientific_definitions.yaml` **0 改动** → **Gate 0 保持 CLOSED**；
> **Gate 1 仍为 NOT CLOSED**（唯一 blocker：溶液锚点 31 行 `method=est`）。

---

## 0. 一句话结论

把三臂对齐到同一批 10 个分子之后，ΔSCF 的 τ_b 仍是三者最高（0.911 vs 0.778 vs 0.689），但与另外两臂的差距在配对检验下全部跨 0（配对 95% CI [−0.200, +0.550]，精确配对置换 p = 0.805）——所以从本周起，项目对外只能说「MAE 的排序与 τ_b 的排序不一致」，不能说「ΔSCF 的排序显著更好」。

三条互不依赖的收获，都在**不新增任何计算**的前提下：

- **R1**：三臂此前算在**不同的分子集**上（n = 12 / 10 / 12），所以 0.911 与 0.606 / 0.727 **不是同一个量**。
  查清排除原因（ΔSCF 臂的来源审计表只有 12 个分子，VC 与 MA 从未被提交给它，**不是** SCF 失败、**不是** `unbound_anion`）、
  对齐到共同 10 分子重算、并补上**配对** bootstrap 与**精确配对置换**检验之后：点估计排序不变，
  但**两两差异的配对 95% CI 全部跨 0**（配对置换 p = 0.721–0.828）——**排序差异未达显著**。
- **R2**：Week 9 的 ρ(std, τ_b) = -0.851 降级为「现象示意（10 点 / 5 台阶）」。合成数据相图给出机制侧的定量边界：
  换到 std 轴，相图上的秩相关是 **-1.000**；氧化靶轴上 τ_b 均值跌破 0.8 于 std = 0.45 eV、跌破 0.5 于 1.20 eV
  （还原靶轴 0.25 / 0.70 eV）。而 ρ(|mean|, τ_b) = -0.535 被判定为**共线性伪影**：
  实测点上 ρ(|mean|, std) = +0.758，相图里同一相关系数是 0.000。
- **R3**：T1–T5 的定位由「拟合精度」改写为**代数恒等式**，并补了一次**先冻结、后打分**的样本外检验：带符号规则 3/4、朴素规则 2/4。

---

## 1. 本轮范围（`docs/31` §4 批次 A）

| # | 条目 | 类型 | 落点 |
| --- | --- | --- | --- |
| R1 (+R10) | 三臂子集对齐 + 配对显著性 | 纯分析 | `scripts/analyze_p1_core_set.py`、`docs/10_week4_report.md` §2.3.1 |
| R2 | −0.851 降级 + 合成数据相图 | 纯计算 | `scripts/analyze_sigma_synthetic.py`、`docs/19` §0、`docs/20` §0/§3 |
| R3 | 恒等式措辞 + 前瞻检验 | 纯分析 | `scripts/analyze_sigma_prospective.py`、`docs/20` §7.4 |
| R6 | 「结构性不可能」写死适用范围 | 纯措辞 | `docs/26` §0/§4.7、`docs/assets/data.js`、交付层模板 |
| R4(a) | 「CDS 对垂直量精确为 0」进正文 | 纯措辞 | `docs/22_week12_report.md` §7.1 |

**刻意不做的**：批次 B（R9 xTB 热修正抽样、R4b 导体极限、R11 NEB 精修）需要新计算；
批次 C 的 R7 要动 Stage 1 冻结件与 Gate 关闭判据，**必须等 PI 裁决**；批次 D（R8、R12）不阻塞结题。

---

## 2. R1 —— 三臂对齐，然后做真正的配对检验

### 2.1 查清的排除原因（此前留白）

被 ΔSCF 臂丢掉的两个有锚点分子是 **VC、MA**。原因不是 SCF 不收敛、也不是 `unbound_anion`（那是 EA 侧的质量标记），
而是这一臂的来源表 `outputs/week2/method_audit_xtb.csv` **只有 12 个分子**：

```
AN; DEC; DMC; DME; DMSO; DOL; EA; EC; GBL; PC; SL; TMP
```

core set 里**从未被提交给该臂**的 6 个分子是：EMC、FEC、VC、TEGDME、MA、SN。
锚点表恰好也有 VC、MA 的气相 IP，于是「有锚点 × 三臂齐备」的交集只剩 **10 个分子**：DMC、EC、DME、DOL、EA、GBL、SL、DMSO、AN、TMP。

### 2.2 对齐后重算（同一估计量）

| 臂 | n | MAE (eV) | bias (eV) | Kendall tau_b [95% CI] | 参照物 |
| --- | --- | --- | --- | --- | --- |
| P0 Koopmans（GFN2-xTB） | 10 | 1.349 | +1.231 | 0.689 [0.26, 1.00] | anchor-referenced (gas-phase experimental IP) |
| GFN2-xTB ΔSCF | 10 | 4.481 | +4.481 | 0.911 [0.69, 1.00] | anchor-referenced (gas-phase experimental IP) |
| P1 r2SCAN-3c | 10 | 0.255 | -0.169 | 0.778 [0.42, 1.00] | anchor-referenced (gas-phase experimental IP) |

**连带项（公式内推，不是新判据）**：Top-k 规则 `config/prereg.yaml k_abs = max(1, floor(frac * N + 0.5))` 在 N = 18 时给出 k = 2 / 4 / 5；
对齐到 N = 10 后按**同一公式**得 k = 1 / 2 / 3（`ranking._resolve_k` 的 `round(frac*N)` 在这些分数上与冻结式逐项相同，
`arm_alignment.k_abs` 逐项记了这个核对）。

### 2.3 配对检验与 headline 改写

| 对比 | Δ tau_b | 配对 95% CI | 配对置换 p | 精确 |
| --- | --- | --- | --- | --- |
| ΔSCF − P1 r2SCAN-3c | +0.133 | [-0.200, +0.550] | 0.805 | 是（1024 种赋值全枚举） |
| ΔSCF − P0 Koopmans | +0.222 | [-0.177, +0.650] | 0.721 | 是（1024 种赋值全枚举） |
| P1 − P0 | +0.089 | [-0.203, +0.488] | 0.828 | 是（1024 种赋值全枚举） |

**结论**：三个配对区间全部跨 0，`arm_alignment.verdict.status = "not_significant"`、
`all_three_pairwise_tests_unresolved = true`。
按 `docs/31` R1 的验收判据，headline 已改写为「**排序差异未达显著**」——见 `docs/10_week4_report.md` §2.3.1。

### 2.4 两类 τ_b 的参照物（禁止混引）

| 族 | 参照物 | 本项目取值 |
| --- | --- | --- |
| anchor-referenced | 实验气相 IP（`data/anchors/gas_phase_anchors.csv`） | 0.606 / 0.911 / 0.727（原 n = 12 口径）/ 0.689 / 0.911 / 0.778（共同 n = 10 口径） |
| target-model-referenced | 目标模型 P1 自身（无外部参照） | 氧化 0.673 / 还原 0.595（n = 18） |

### 2.5 R10：小样本纪律

- 所有关键对比改为报**配对差值分布**（本节 §2.3 是一次示范）；
- 「Week 9 被迫统一到共同 10 分子」已写进 `docs/19_week9_report.md` §2.6；
- 子集敏感性：同一组秩相关在 native 与 common-10 上**同向** ——
  ρ(std, τ_b)：-0.815（native）vs -0.851（common-10）；ρ(|mean|, τ_b)：-0.456 vs -0.535；ρ(std, f_unresolved)：0.879 vs 0.894。

---

## 3. R2 —— 相图取代相关系数

### 3.1 降级

`docs/19_week9_report.md` §0 与 `outputs/week9/stage10_summary.md` 的同一张表现在把 −0.851 标为
**「现象示意（n = 10 点 / 5 台阶）」**，并新增「证据等级」一列。降级的两条硬理由：

1. 10 个点来自 **5 个台阶**（每级两个轴），有效自由度接近 5；
2. `|mean|` 那一行是共线性伪影（下表）。

### 3.2 合成数据相图

模型：固定靶排序 `t`（取本项目真实的 P1 靶值），令 `delta_i = mean + std * z_i`，
并把 `z` 在每个 replicate 内标准化，使 `delta` 的**样本 sd 恰为 std**。
网格 33 × 41（mean ∈ [-8.0, 8.0] eV，std ∈ [0.0, 2.0] eV），每格 2000 组重抽样。

| 量 | 实测 10 点（5 台阶） | 相图（1353 格） | 读法 |
| --- | --- | --- | --- |
| ρ(std, τ_b) | -0.851 | -1.000 | 两个数据源都指向「离散度决定损伤」 |
| ρ(|mean|, τ_b) | -0.535 | 0.000 | 实测那个 −0.535 **不是** mean 的因果作用 |
| ρ(|mean|, std) | 0.758 | （按构造独立） | 实测的共线性正是 −0.535 的来源 |
| ρ(std, f_unresolved) | 0.894 | — | 离散度经 σ_ij 直接喂给不可判定比例 |

**mean 轴严格常数**：三张相图沿 mean 轴的最大绝对差 = **0.00e+00**。
这不是数值巧合而是可证的恒等式：给每个分子加同一个常数，既不能换序、也不能改变任何 pair 差。

**std 轴上的定量边界**：

| 靶轴 | τ_b 均值跌破 0.8 | 跌破 0.5 | Top-20% 重叠跌破 1.0 |
| --- | --- | --- | --- |
| 氧化 | std = 0.45 eV | std = 1.20 eV | std = 0.25 eV |
| 还原 | std = 0.25 eV | std = 0.70 eV | std = 0.10 eV |

### 3.3 实测点与曲线的关系（诚实边界）

F42 的 (c) 面板把实测 10 点叠在合成曲线上：多数点贴着曲线，但**两个例外各有明确的物理身份**，
它们恰好说明了为什么闭式判据（含 `q_ij` 的对齐信息）必须是主角、离散度只能当旁证：

- `P0_to_P1/还原`（std = 2.25 eV，τ_b = +0.600）落在曲线**之上**：位移几乎平行于靶轴，
  所以离散度很大而顺序几乎没动（`docs/20` T4/T5 的机制）；
- `C1_to_C2/还原`（std = 0.335 eV，τ_b = +0.289）落在曲线**之下**：这一级的还原是 **Li 中心**而非分子中心
  （state-identity 改变），纯离散度模型按定义看不见这件事。

**因此本节的结论必须这样写**：合成相图把「离散度」从 5 个点的相关升级为**一条可计算的边界**，
但它**不能单独**解释全部台阶；能单独解释的是 `q_ij <= sqrt(2)/z` 的闭式判据 —— 见 §4。

---

## 4. R3 —— 恒等式与一次真正的样本外检验

### 4.1 措辞改写

`docs/20_week10_report.md` §3 开头新增定位段：T1–T5 是**代数恒等式**，
「与实测误差 0.00e+00」**不是精度证据**；恒等式的价值在**可外推**。§3.4 的「数值验证」改为「数值**复核**」。

### 4.2 前瞻检验（先落盘、后打分）

规则与阈值**只用** `docs/20` §7 的 10 个发现点拟合：带符号 `ols_slope_b`（低 = 危险，阈值 -0.3635）、
朴素 `sd(delta)`（高 = 危险，阈值 0.3104 eV）。预测先写入 `outputs/week21/sigma_prospective_frozen.json`，
带 UTC 时间戳 `2026-10-01T15:56:07+00:00` 与 SHA256 `25288a6eedba469c…`，**然后**才计算实际结果。

| 分子集 | 轴 | n | k | sd(δ) /eV | `ols_slope_b` | 带符号预测 | 朴素预测 | 实测 | 重叠 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| all_non_discovery | oxidation | 8 | 2 | 0.563 | +0.423 | 保留 | 改写 | **保留** | 1.00 |
| all_non_discovery | reduction | 8 | 2 | 2.104 | -0.221 | 保留 | 改写 | **改写** | 0.50 |
| stage16_holdout | oxidation | 6 | 1 | 0.660 | +0.435 | 保留 | 改写 | **保留** | 1.00 |
| stage16_holdout | reduction | 6 | 1 | 2.436 | -0.881 | 改写 | 改写 | **改写** | 0.00 |

**命中率：带符号规则 3/4 = 0.750；朴素规则 2/4 = 0.500。**

**失败案例（与命中数一起读）**：3 处落空 —— all_non_discovery / oxidation（带符号命中、朴素**落空**，实测保留）；all_non_discovery / reduction（带符号**落空**、朴素命中，实测改写）；stage16_holdout / oxidation（带符号命中、朴素**落空**，实测保留）。

**诚实边界**：这些分子的能量在仓库里已经存在，所以这是**样本外留出检验**、不是盲前瞻试验；
真正按时间排序的是**规则**（Week 10 冻结、阈值从未被留出分子影响）。而且 n = 4 个预测，
0.750 与 0.500 的差别在这个样本量上**不显著**——只能说方向与 §7.2 一致。

---

## 5. R6 与 R4(a) —— 两处措辞的适用范围

- **R6**：`f_robust_inv` 从 0 变非 0 的「结构性不可能」已在 `docs/26` §0、§4.7 标题与正文、
  `docs/assets/data.js` 的静态文案、以及交付层 `scripts/build_deliverables.py` 的生成模板里
  写死适用范围：**在本项目这条具体流水线、这批格子、这套估计量下**（`sigma_ij = |d0_ij - d1_ij|/sqrt(2)` 且 `z_primary = 1.0`），
  并明确**不是普适定理**。
- **R4(a)**：`SMD CDS` 在三电荷态上完全相同（spread = 0.0 eV）→ 对任何垂直 IP / EA **精确为 0**，
  已从 §0 搬进 `docs/22_week12_report.md` §7.1 的正文（并保留「量级不小但不可见」的读法纪律）。

---

## 6. Gate 状态

| Gate | 状态 | 依据 |
| --- | --- | --- |
| Gate 0（定义冻结） | **CLOSED** | 本轮 R1–R6/R4a 全部为分析或措辞；`config/prereg.yaml` 与 `config/scientific_definitions.yaml` **0 改动**（`scripts/freeze_gates.py --stage 0` 重跑后仍 CLOSED，见 `outputs/week1/gate0_record.md`） |
| Gate 1（方法 / 锚点） | **NOT CLOSED** | 唯一 blocker 仍是 `data/anchors/solution_redox_anchors.csv` 的 31 行 `method=est`；R7（两级化 + within-series 锚点）属批次 C，**本轮未执行**，需 PI 裁决 |

---

## 7. 产物

| 类型 | 路径 |
| --- | --- |
| R1 扩展产物 | `outputs/week4/p1_anchor_comparison.json` 的 `arm_alignment` 与 `tau_b_reference` 两个新块 |
| R2 相图数据 | `outputs/week21/sigma_synthetic.json` |
| R2 图与清单 | `outputs/figures/F42_sigma_synthetic_phase_diagram.png`、`outputs/figures/figure_manifest_week21.md` |
| R3 冻结预测 | `outputs/week21/sigma_prospective_frozen.json` |
| R3 打分 | `outputs/week21/sigma_prospective.json`、`outputs/week21/sigma_prospective.md` |
| 脚本 | `scripts/analyze_sigma_synthetic.py`、`scripts/analyze_sigma_prospective.py`、`scripts/analyze_p1_core_set.py`（扩展）、`scripts/gen_week21_report.py` |
| 测试 | `tests/test_week21_report.py`、`tests/test_sigma_synthetic.py`、`tests/test_sigma_prospective.py` |

## 8. 图表

| 编号 | 文件 | 说明 |
| --- | --- | --- |
| F42 | `outputs/figures/F42_sigma_synthetic_phase_diagram.png` | R2：把 Week 9 的 rho(shift std, tau_b) = -0.851（10 点 / 5 台阶）从 headline 降级为现象示意，改用合成数据相图回答同一个问题——固定靶排序 t，令逐分子位移 delta_i = mean + std * z_i 并把 z 在每个 replicate 内标准化（使 delta 的样本 sd 恰为 std），在 mean 属于 [-8, +8] eV、std 属于 [0, 2] eV 的网格上每格 2000 组重抽样。(a)(b)(d) 三张相图沿 mean 轴**严格常数**（tau_b 的最大绝对差 0.00e+00）：给每个分子加同一个常数既不能换序也不能改变任何 pair 差，所以 Week 9 那个 rho(|mean|, tau_b) = -0.535 只能是共线性伪影——实测点上 rho(|mean|, std) = +0.758，而相图里两者按构造独立、同一相关系数为 0.000。(c) 换到 std 轴，tau_b 单调下降且相图的秩相关为 -1.000：氧化靶轴上 tau_b 均值跌破 0.8 于 std = 0.45 eV、跌破 0.5 于 1.20 eV（还原靶轴 0.25 / 0.70 eV），即**排序的代价只由位移的离散度支付**；实测 10 点多数贴着曲线，但两个例外各有明确的物理身份——P0->P1/还原（std = 2.25 eV，tau_b = +0.60）在曲线**之上**，因为它的位移几乎平行于靶轴；C1->C2/还原（std = 0.335 eV，tau_b = +0.29）在曲线**之下**，因为那一级的还原是 Li 中心而非分子中心（state-identity 改变），纯离散度模型按定义看不见这件事。 |

图内标签一律用英文。清单与 SHA256 见 `outputs/figures/figure_manifest_week21.md`。

## 9. 已知限制

- **R1 的 n = 10**。配对检验把问题问对了，但 10 个分子撑不起「显著」二字；
  本轮的产出是**把不该说的说回去**（不能声称 ΔSCF 排序显著更好），不是新的肯定结论。
- **R2 的合成模型是「纯离散」模型**，按构造看不见 state-identity 改变（§3.3 的 `C1_to_C2/还原` 就是它失手的那一格）。
  相图给的是**边界与方向**，不是对所有台阶的完整解释。
- **R3 只有 4 个预测**，且是样本外留出而非盲前瞻；命中率差别不显著，失败案例已逐条列出。
- **R6 的措辞修订不改变任何数字**，但它改变交付件的 SHA256 —— 已按 R10 的连带纪律重跑交付层。
- 本轮的 `outputs/figures/F4–F7` 会被 `analyze_p1_core_set.py` 重绘一次；PNG 字节随环境变化，
  语义未变（同一脚本、同一数据在当前环境下的重绘），manifest 已同步更新。

## 10. 下一步（批次 B / C / D）

1. **批次 B（低成本新计算）**：R9（5–10 分子 xTB `--ohess` 热修正抽样，回答「热修正的分子间离散度是否远小于 δ_m」）、
   R4(b)（一格 ε = 10^6 导体极限，**附加诊断、不进冻结列表**）、R11 的 NEB / QST2 精修 2–3 格。
2. **批次 C（需 PI 裁决）**：R7 —— Gate 1 两级化 + Okoshi/Ue within-series 锚点核验。
   必须先完成文献核验（卷期页码 + 测量条件），未核验通过的条目不得写入锚点 CSV。
3. **批次 D（不阻塞）**：R8（近简并 pair 的靶向双腿策略）、R12（把「哪些层不用算」写成结题叙事）。
4. **结题材料**：把批次 A 的四条结论并入 `成果输出/数据结果汇总.md` 的结论节与站点首页文案。

（Gate 状态：Gate 0 CLOSED、Gate 1 NOT CLOSED —— 唯一 blocker 仍是溶液锚点 31 行 `est`。）

