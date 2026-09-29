# Stage 1：方法审计与 external reference anchors

> 对应 v2 文档：§3.3（Axis C：external reference layer）、§7.1（先做 method audit，再冻结 production protocol）、
> §9.1–§9.3（tolerance δ / robust inversion / Kendall τ_b）、§15（外部 reference anchors）、
> §19 Stage 1（操作与 Gate 1）。
> 数据文件与可信度分级见 `data/anchors/README.md`；校验脚本 `scripts/validate_anchors.py`。

---

## 1. 为什么需要 external anchors

没有 external reference 时，本项目最多只能严谨地说：

> 「模型 A 能否恢复 target model B 的排序。」

这句话里 **A 和 B 都是模型**。它回答的是 *ranking preservation*，**不能**回答
*「这个排序离真实可观测量有多远」*。两者必须分开（v2 §15.3）。

引入 external anchors 之后，才能把命题升级为：

> 「在这些**已验证的 chemical / experimental domain** 内，某个廉价模型能够保持
> **experimentally anchored** 的 ranking decisions。」

因此 anchors 的职责是 **judge accuracy**，而不是定义模型复杂度（v2 §3.3）。

$$
\boxed{\text{model complexity} \neq \text{accuracy} \neq \text{physical representativeness}}
$$

---

## 2. 三类锚点对应三个用途

| 锚点 | 数据文件 | 审计对象 | 用途 |
| --- | --- | --- | --- |
| `R_gas` | `data/anchors/gas_phase_anchors.csv` | `P_1`（气相分子 redox 热力学） | 绝对标度 / family trend / ranking |
| `R_sol` | `data/anchors/solution_redox_anchors.csv` | `P_2`（固定背景连续介质 redox） | within-series 相对排序 |
| `R_env` | （本阶段无数值，见 §5） | `C_1` / `C_2`（Li 配位 / 显式微溶剂化） | 定性–半定量趋势校验 |

### 2.1 Gas-phase anchor（`R_gas`）

目标 **不是** 让整个项目依赖昂贵的 wave-function 计算，而是验证 production DFT 是否
至少在典型体系上给出合理的（v2 §15.1）：

1. **absolute scale**：例如 NIST 实验 `H2O IP = 12.62 eV`、`DME IP = 9.30 eV`；
2. **family trend**：碳酸酯 / 醚 / 酯 / 砜 / 腈 / 磷酸酯 的相对高低；
3. **ranking**：同一 family 内的顺序。

数据表中的 `method` 列区分 `exp` 与 `calc`，`source_type` 列区分 `nist_webbook` 与
`high_level_calc`。**不要把 DFT 值填进 `exp` 行**。

### 2.2 Solution anchor（`R_sol`）

优先使用 **同一实验系列** 中条件尽量一致的分子（v2 §15.2）：

- solvent、supporting salt、concentration、temperature、reference electrode、scan 条件。

条件无法统一时：

- **不** 强行对全部文献做绝对值 pooled regression；
- **只做 within-series relative ranking**。

`config/scientific_definitions.yaml` 的 `axis_C_external_reference.R_sol.condition_fields`
冻结了六个必须保存的条件字段，`solution_redox_anchors.csv` 的落位如下：

| condition field | 落在哪一列 |
| --- | --- |
| `solvent` | `solvent`（`<缩写> (neat)` 表示该电位指纯溶剂的**本征**行为） |
| `supporting_salt` | `electrolyte_note`（`supporting_salt=...`） |
| `concentration` | `electrolyte_note`（`concentration=...`） |
| `scan_conditions` | `electrolyte_note`（`scan_conditions=...`） |
| `temperature` | `temperature_K` |
| `reference_electrode` | `reference_electrode` |

**单位换算约定**：`thermochemistry.units_policy` 规定，若把自由能差换算为电位刻度，
必须显式记录换算常数与 reference electrode。本表每一行的 `source_note` 末尾都带：

```text
| unit convention: reference electrode Li/Li+ (1 M Li+, 298.15 K); 1 V = 96.485 kJ/mol (F = 96485.33212 C/mol)
```

项目**主报告量**仍是 kJ/mol 的自由能差；用 V 只是为了与实验电化学文献对照。

### 2.3 作为 tolerance δ 的来源（v2 §9.1 / §9.2 / §9.3）

这是 anchors 最容易被忽视、但对本项目最关键的作用。

定义 pair difference：

$$
\Delta P_{ij}^{(m)} = P_i^{(m)} - P_j^{(m)}.
$$

若

$$
|\Delta P_{ij}^{(m)}| < \delta_m
\quad\text{或}\quad
|\Delta P_{ij}^{(m)}| < z\,\sigma_{ij}^{(m)},
$$

则该 pair 在模型 $m$ 下记为 `unresolved/tied`。

**`δ_m` 从哪里来？** 从 external anchors：

- `R_gas` 给出 ICP/EA 的**方法误差**（DFT vs 实验 / WFT）；
- `R_sol` 给出溶液相 redox 的**实验分散度 + 方法误差**；
- `σ_{ij}^{(m)}` 还应叠加构象/方法不确定性。

有了 `δ_m`，才能定义 **robust inversion**（v2 §9.2）——只有两个模型都能解析该 pair、
且符号相反时才算：

$$
\operatorname{sign}\left(\Delta P_{ij}^{(A)}\right) \neq \operatorname{sign}\left(\Delta P_{ij}^{(B)}\right),
\quad \text{两侧 separation 均超过 uncertainty threshold.}
$$

并同时报告

$$
f_{\mathrm{robust\ inv}} = \frac{N_{\mathrm{robust\ inversions}}}{N_{\mathrm{pairs\ resolved\ in\ both}}},
\qquad
f_{\mathrm{unresolved}} = \frac{N_{\mathrm{unresolved\ pairs}}}{\binom{N}{2}}.
$$

> 若某模型看起来 inversion 很少，但绝大部分 pairs 实际无法区分，它 **不能** 被称为筛选稳定。
> 这就是为什么 §9.3 要求用允许 ties 的 Kendall $\tau_b$，而不是简单的 $\tau$。

**具体操作建议**：把 `data/anchors/*.csv` 的 `uncertainty_eV` / `uncertainty_V` 聚合，
得到每个轴的经验分散度，作为 `δ_m` 的**下界**；再叠加 production protocol 自身的
method sensitivity（§4.1 测出来的）作为实际使用的 `δ_m`。两个来源都要在 log 里留痕。

> 这与 `config/prereg.yaml` 的 `pair_comparison.delta_m.source_rule` 完全一致：
> δ_m 只能依次取自 (1) **外部 anchor 的实验离散度**；(2) method audit 的离散度；
> (3) 预注册默认值 `delta_default = 2.0 kJ/mol`。
> 本目录提供的是第 (1) 条所需的原材料。

---

## 3. 如何用 anchors 做 method audit（v2 §7.1 + §19 Stage 1）

### 3.1 原则

> **先做 method audit，再冻结 production protocol。**

必须严格区分：

- **method sensitivity**：不同合理方法之间差多少（只需要比较方法，不需要外部参考）；
- **method accuracy**：离真实值有多远（**必须** 依赖 external reference）。

只有后者用得上 `data/anchors/`。

### 3.2 audit 内容（至少包含）

1. 选 **8–10 个 method-audit molecules**，覆盖主要 structural family、柔性程度、配位模式；
2. **两种合理 DFT functional**；
3. **至少两个 basis-set 级别或 diffuse-basis variants**；
4. **continuum model sensitivity**；
5. **gas-phase external anchor**（`gas_phase_anchors.csv`）；
6. **solution experimental anchor**（若可得；`solution_redox_anchors.csv`）。

### 3.3 建议 audit 流程

| 步骤 | 做什么 | 判据 / 输出 |
| ---: | --- | --- |
| 1 | 对 audit set 跑 geometry+frequency | 无虚频、SCF 收敛、无 spin contamination |
| 2 | 同一几何上做单点，扫描 functional × basis × diffuse | method sensitivity 矩阵 |
| 3 | 与 `R_gas` 的 `exp` 行逐物种比 | 绝对误差（ME/MAE）、family trend、rank（Kendall τ_b） |
| 4 | 若有溶液相：与 `R_sol` 比 | 只在同一 `solvent`/`electrode`/`temperature_K` 组内比相对排序 |
| 5 | 检查阴离子 | 是否出现 `unbound_anion`（`R_gas` 已显式标出这类物种） |
| 6 | 比较 absolute error 与 rank stability | 两者可能背离——这正是本项目要研究的 |
| 7 | 冻结 production protocol | 记录 §7.4 的全部机器可读参数 |

### 3.4 阴离子 / diffuse basis 的专门要求（v2 §7.3）

对阴离子必须单独建立 diffuse-basis protocol，至少检查：

- diffuse augmentation；
- SOMO 空间扩展；
- electron detachment stability；
- SCF solution 是否为伪束缚态。

**如果 gas-phase anion 不稳定，则标记 `unbound_anion`，不强行生成一个
gas-phase adiabatic reduction ranking。** `gas_phase_anchors.csv` 里已经把 EC / PC / DMC /
DME / DOL / THF 的气相 EA 留空并标为 `unbound_anion`，正是同一个逻辑：**宁可留空，不要编造。**

### 3.5 Gate 1

只有 production protocol 对典型体系的 **state identity、SCF stability、gas-phase anchor、
solution trend** 均无明显系统性失败后，才能启动 Stage 2 的批量计算。

---

## 4. 使用 anchors 时的硬性纪律

1. **绝对标度与相对排序分开报告**。absolute error 小 ≠ ranking 稳；ranking 稳 ≠ 物理正确。
2. **跨系列不合并**。不同 `solvent` / `electrolyte_note` / `reference_electrode` 的行不得直接
   pooled 成单一绝对值 benchmark（v2 §15.2）。
3. **`doi` 的语义是「本行数值的来源」**。估算值必须留空 `doi`，只在 `source_note` 里写
   「建议核对来源」；详见 `data/anchors/README.md` §2.1。
4. **Δ 的来源要留痕**。报告 `δ_m` 时说明它来自 anchors 的实验不确定度、方法误差，还是两者叠加。
5. **不要用 anchors 反推去调参**。anchors 是审计集，不是训练集；用它调参会让
   §13 的 random/group/LOFO 三种拆分的结论失效。

---

## 5. `R_env` 的现状与限制

v2 §3.3 规定：对少量典型 Li-coordination cases，可使用已发表的 explicit-cluster、
溶液模拟或相关实验趋势作为**定性/半定量** anchor，且 **第一阶段不要求这一层完整覆盖全部候选**。

因此 `data/anchors/` **当前没有** `R_env` 数值文件。使用时请注意：

- 不要把 `R_gas` / `R_sol` 的结论外推到 Li 配位条件态（$C_1$）；
- 若确需 `R_env`，应单独提交文件并说明：来源、条件、是定量还是定性趋势。

---

## 6. 已知局限（务必与 `data/anchors/README.md` §4 对照阅读）

- `gas_phase_anchors.csv`：**有值的 30 行全部是 curated-literature**（NIST 实验 27 行 +
  Fadel 2019 DLPNO-CCSD(T) 2 行 + CO2 EA 1 行）；另有 **9 行为显式空缺**（3 个 `not_curated`、
  6 个 `unbound_anion`），**没有** estimated 数值。
- `solution_redox_anchors.csv`：**31 行全部是 `est`**，`doi` 全空。
  它目前只能支撑「量级 / 相对排序」级别的定性审计，**不能** 当作绝对 benchmark。
- 若日后拿到可信的实验溶液相 redox 表并升级为 `exp`，请同步更新 `README.md` §1.2 的计数与
  §4 的待核清单。

---

## 7. 与决策指标的关系

`δ_m` / uncertainty 不只影响 §9 的 ranking 定义，还会传导到 §10 的筛选决策指标：

- Top-$k$ overlap：`δ` 越大，越容易把 near-tie 的 pair 判为不可解析；
- Selection regret：需要同时报告「因数值误差」与「因 unresolved」造成的 regret；
- Threshold-based decision error：阈值附近的候选天然不可靠，必须显式统计。

**结论**：external anchors 的最终价值，是把「我们离真实可观测量有多远」这个**外部**问题，
转化为一个可进入 tolerance δ、进而进入决策指标的**内部**参数。
