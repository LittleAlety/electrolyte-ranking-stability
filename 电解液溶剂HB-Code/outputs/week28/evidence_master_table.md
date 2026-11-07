# Week 28 / WP1：统一科学证据主表（unified scientific evidence master table）

> 阶段：下一阶段（评审实施方案）WP1。产物目录 `outputs/week28/`，交付镜像
> `..\成果输出（part2）\week28/`。本文件由 `scripts/build_week28_evidence_table.py`
> 确定性生成，`--check` 逐字节复核。零新增电子结构计算：全部数值来自 Week 1–27 的冻结产物。

## 0. 一句话结论

把 Week 1–27 散落的物理量、状态身份、排序指标与成本收敛成 6 张主表（共 2074 行），每一行都能追到 `molecule x model x charge state x motif` 与具体来源字段；并且在 `all` scope / `z_only` / `z = 1.0` 下**逐位复现**了 Week 6 已冻结的 pair 数字，证明这张主表就是已发表数字的同一个对象，而不是并行的一套定义。

## 1. 主表规模

| 表 | 行数 |
| --- | --- |
| `molecule_registry` | 58 |
| `state_registry` | 242 |
| `property_table` | 392 |
| `pairwise_table` | 1326 |
| `decision_table` | 45 |
| `cost_table` | 11 |

## 2. 四项必查结论

| check | 问题 | 结论 | 关键数字 |
| --- | --- | --- | --- |
| `provenance_completeness` | 主文数字是否都能追溯到明确的分子、模型、状态和原始计算记录？ | **PASS** | 392 property 行全部带 source_file + source_field；0 个来源文件缺失 |
| `same_target_quantity` | 同一个 pair 的两个模型是否比较同一可解释的目标量？ | **PASS** | 1326 个 pair 行全部使用 (quantity=IP / -EA, units=eV, direction=maximise)；没有任何 molecule x axis 在不同 rung 间混用不同目标量 |
| `p1v_vs_p1a_distinct` | P1v 和 P1a 是否有不同的属性定义（而非只改了标签）？ | **PASS** | 定义层：几何策略（G1 shared by neutral/cation/anion (single point only) vs G2 (per-charge-state r2SCAN-3c Opt started from G1)）与热化学（vertical: no relaxation and no ZPE for the charged state vs adiabatic: relaxed charged state, no ZPE）都不同；经验层：12 个共同分子上 |IP(P1a)-IP(P1v)| > 0 全部成立，中位 0.3181 eV；还原轴按 unbound_anion 规则全部排除 |
| `li_centered_not_misused_as_molecular` | Li-centered reduction 是否被误用为 molecule-centered reduction？ | **PASS** | C1/C2 的还原轴严格按 R13 闸门过滤：C1 的 10 个候选里只有 SN 通过闸门，另外 9 个被排除在 primary scope 之外；旧的 all scope 还原排序（含 Li-centered 对象）Kendall tau_b = -0.4666666666666667，说明不加闸门时这条排序轴在物理上不是同一件事 |
| `status_vocabulary_separated` | 缺失、未收敛、未解析、不适用是否被分别编码？ | **PASS** | property 层的 value_status 只用 ok/missing/not_converged/not_applicable；未解析（UNRESOLVED）只作为 pairwise 层的 decision_state 出现，从不写进 value_status |
| `frozen_number_reproduction` | 本主表是否就是已发表冻结数字的同一个对象（而不是并行的一套定义）？ | **PASS** | 逐位复现 outputs/week6 的 6 组 stored pair 数值（最大绝对误差 0.000e+00 eV），并用 tau_b / spearman 复核 outputs/week4 的 4 组 P2a 数值（最大绝对误差 0.000e+00），从而证明主表与已冻结数字是同一个对象、且 P2a/P2eps 的命名映射正确 |

## 3. 复核：主表 vs Week 6 冻结数字

| Week 6 对比 | 主表对比 | 轴 | 分子数 | 复核 pair 数 | 最大绝对误差 (eV) | mask 不一致 |
| --- | --- | --- | --- | --- | --- | --- |
| P0_to_P1 | P0_to_P1v | oxidation | 12 | 66 | 0.000e+00 | 0 |
| P0_to_P1 | P0_to_P1v | reduction | 12 | 66 | 0.000e+00 | 0 |
| P1_to_P2 | P1v_to_P2eps10 | oxidation | 12 | 66 | 0.000e+00 | 0 |
| P1_to_P2 | P1v_to_P2eps10 | reduction | 12 | 66 | 0.000e+00 | 0 |
| C0_to_C1 | C0_to_C1 | oxidation | 10 | 45 | 0.000e+00 | 0 |
| C0_to_C1 | C0_to_C1 | reduction | 10 | 45 | 0.000e+00 | 0 |
| p1_to_p2.oxidation (outputs/week4/p2_decision_stability.json) | P1v_to_P2a | oxidation | 18 | metric only | 0.000e+00 | 0 |
| p1_to_p2.reduction (outputs/week4/p2_decision_stability.json) | P1v_to_P2a | reduction | 18 | metric only | 0.000e+00 | 0 |
| p0_to_p2.oxidation (outputs/week4/p2_decision_stability.json) | P0_to_P2a | oxidation | 18 | metric only | 0.000e+00 | 0 |
| p0_to_p2.reduction (outputs/week4/p2_decision_stability.json) | P0_to_P2a | reduction | 18 | metric only | 0.000e+00 | 0 |

## 4. 逐 rung 的候选与成本

| rung | 代价 | ok 行 | missing | not_converged | not_applicable | QC 标记 | wall seconds | 失败作业 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `P0` | cheap (GFN2-xTB only) | 36 | 80 | 0 | 0 | 0 | 0.0 | 0 |
| `P1v` | expensive (r2SCAN-3c single point) | 36 | 0 | 0 | 0 | 0 | 2194.1 | 0 |
| `P1a` | expensive (r2SCAN-3c geometry optimisation) | 12 | 0 | 0 | 12 | 0 | 0.0 | 0 |
| `P2a` | expensive (r2SCAN-3c single point in solvent) | 36 | 0 | 0 | 0 | 0 | 2915.0 | 0 |
| `C0` | expensive (r2SCAN-3c single point) | 24 | 0 | 0 | 0 | 4 | 3453.9 | 0 |
| `C1` | expensive (r2SCAN-3c single point on the complex) | 20 | 16 | 0 | 0 | 14 | 17737.6 | 1 |
| `C2` | expensive (r2SCAN-3c single point on the 1:2 complex) | 20 | 4 | 0 | 0 | 14 | 12333.7 | 0 |
| `P2eps@5.0` | expensive (r2SCAN-3c single point in solvent) | 24 | 0 | 0 | 0 | 0 | 877.7 | 0 |
| `P2eps@10.0` | expensive (r2SCAN-3c single point in solvent) | 24 | 0 | 0 | 0 | 0 | 1103.7 | 0 |
| `P2eps@20.0` | expensive (r2SCAN-3c single point in solvent) | 24 | 0 | 0 | 0 | 0 | 983.9 | 0 |
| `P2eps@40.0` | expensive (r2SCAN-3c single point in solvent) | 24 | 0 | 0 | 0 | 0 | 763.1 | 0 |

## 5. 本阶段确认的七个口径事实（都带机器可查证据）

1. **P1a 只有氧化轴**：`unbound_anion` 规则把 P1a 的还原轴整体排除，主表里这些行的 `value_status = not_applicable`（不是 missing、不是 0）。
2. **C1/C2 还原轴的主 ranking 只剩分子中心还原**：stratification 里 `molecule_centered_redox` 的还原对象是 SN；其余 9 个 Li-centered/mixed 对象被排除在 `primary` scope 之外，但仍以 `all` scope 保留，供复现 Week 5/6。
3. **`ROBUST_INVERSION` 在 z = 1.0 下结构性不可检验**：`sigma_ij` 由两个模型共同定义，反向 pair 两侧同时过门槛需要 `z <= 1/sqrt(2)`，所以 `f_robust_inv = 0` 不是稳定性证据；`pairwise_table.structurally_non_testable` 逐行标注。
4. **`P2` 在仓库里有两套同名含义**：Week 4 的 `p2_decision_stability.json` 把 “P2” 记为 CPCM(SMD, acetonitrile)，Week 6 的 `analyze_stage6.py` 把 “P2” 记为 bare CPCM ε=10。两者各自正确但同名，跨周引用时必然踩坑。R13 的 P2a / P2eps 拆分消除了歧义：主表分别登记为 `P2a` 与 `P2eps@10.0`，Week 6 的 `P1_to_P2` 对应 `P1v_to_P2eps10`。该映射已用 tau_b / spearman 复核（见 check `frozen_number_reproduction` 的 metric 组）。
5. **信息覆盖度显著不对称**：廉价层声明覆盖 58 个分子（core 18 + broad 40），而昂贵层只到 18（P1v / P2a）或 10–12（P1a / C0 / C1 / C2 / P2eps）。主表把 broad pool 的 P0 也登记进来，并把昂贵层的缺口显式写成 `missing`（P0 一栏 80 行），因此 WP4/WP6 的信息预算可以直接从 `cost_table` 读覆盖度，不必翻各周目录。
6. **`scope='all'` 的分母随对比变化。** `n_molecules` 是两个 rung 都有 ok 数值的分子数，
本阶段为 18（P0/P1v/P2a 系）、12（P1a / P2eps / C0）、10（C0→C1、C1→C2）。
因此 `decision_table` 里 `f_unresolved` / `jaccard` / `overlap` **跨行不可比**，
每行都带了 `common_set_label` 作为分母标签；`coverage` 块给出 declared / available / used 对账。
7. **`C1` 的声明范围是 core 18，实际只做到 10。** `config/scientific_definitions.yaml:
dataset.core_set.purpose` 明写 core set「完成 P0 / P1 / P2 以及 C1 conditional Li-coordination」，
但仓库里 C1 只有 10 个分子（`PC` / `EMC` 没有 `[LiM]+` 对象），这 8 个缺口在主表里是
`missing` 而不是被静默丢掉。这是下一阶段扩充计算时**最应该先补**的地方。

## 5.1 独立复核（免费车道子智能体，只读）

本阶段的主表另做过一次**独立复核**：一个只读子智能体在不知道生成代码结论的情况下自行重算，
结论记录如下（它也促成了上一版的两处修正）。

| 复核项 | 独立重算结果 |
| --- | --- |
| `sigma_ev = \|d_lower - d_upper\| / sqrt(2)`（P0_to_P1v / oxidation / all，153 行） | 与表内 `sigma_ev` 最大绝对误差 `4.44e-16`（浮点噪声）；`resolved_lower == (\|d_lower\| >= z*sigma)` 不一致 0 行 |
| 对 Week 6 的 `z_only.P0_to_P1.oxidation`（66 个 pair） | 66/66 全部可见，最大绝对误差 `d_lower` 2.22e-16 / `d_upper` 4.44e-16 / `sigma` 1.11e-16；其中 24 个 pair 方向相反并整体取负 |
| P1a 还原轴 | 12 行全部 `not_applicable`、`value` 全空 |
| C1/C2 还原轴 `in_primary_ranking=True` | 只有 `SN`（C1 −3.207882 eV、C2 −2.818096 eV），标签均为 `molecule_centered_redox` |
| 状态一致性 | `ok` 但值为空 0 行；非 `ok` 却有数值 0 行；`UNRESOLVED` 不出现在 `value_status` |

它提出的两条质疑已被采纳并修正：

- **方向/符号**：`pairwise_table` 按字母序排 `i`/`j`，与 Week 6 的存储顺序可能相反 →
  已在数据字典 §5.3 写明。
- **分母与声明范围不一致**：`declared_scope.C1` 原写作 12，与冻结声明（core 18）不符；
  已改为 18 并补 `declared_scope_source` 出处与 `coverage` 对账块 → 见事实 6、7。

## 6. 交给 WP2–WP4 的接口

- WP2 直接用 `pairwise_table` / `decision_table` 的 `all` 与 `primary` 两个 scope；
- WP3 用 `state_registry` + `property_table.in_primary_ranking` 组织 C0/C1/C2 机制案例；
- WP4 用 `decision_table` 的 Top-k / regret 与 `pairwise_table` 的分辨率列；
- WP5/WP6 用 `cost_table.feature_availability` 作为硬约束（不得把昂贵层的量当廉价输入）。

## 7. 复现命令

```powershell
.venv\Scripts\python.exe scripts\build_week28_evidence_table.py
.venv\Scripts\python.exe scripts\build_week28_evidence_table.py --check
.venv\Scripts\python.exe -m pytest tests/test_week28_evidence_table.py -q
```

