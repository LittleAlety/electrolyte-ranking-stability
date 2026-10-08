# 27 · R15 估计量循环性审计（对抗审计 round 3 · 项目 A/E）

- 触发：第二轮收口后，评审要求「反过来攻击自己的负结果」——`NOT CLOSABLE` / `unresolved`
  本身是否被分析流程人为制造。
- 生成器：`scripts/audit_estimator_circularity.py`（离线只读，零新增电子结构）
- 产物：`outputs/week27/estimator_circularity.json`、`outputs/week27/estimator_circularity.md`

## 0. 一句话结论

**本仓库的解析/不可解析判据是自指的**：主约定把**被比较的两个模型本身**喂给不确定度估计器
（两臂 sigma，R = 2），于是 `sigma_ij = |dP_A - dP_B| / sqrt(2)`（T1）。由此可证：
在冻结的 `z` 下 **`ROBUST_INVERSION` 根本不可能发生**（T6a），而且**双方都解析的 pair 里
一对反向的都没有**（T6b）——也就是说，这条流水线**从来不能认证任何分歧**。
`f_robust_inv = 0` 因此不是经验观察，而是**定义性不变量**；Stage 10 的预注册假设 C
（structured robust inversion）不是「未观察到」，而是**在该约定下不可检验**。

这不是推翻结论，而是把结论**从经验巧合升级为代数必然**：数据确实无法识别排序。
但它要求三处口径改写（见 §6）。

## 1. 口径

| 项 | 值 |
| --- | --- |
| sigma | `two-arm sigma: quantify_method_sigma([model A, model B], ddof=1, stat='std')` |
| 解析 | `|dP| >= z * sigma` 且 `|dP| > 0` |
| ROBUST_INVERSION | 两模型都解析且符号相反 |
| f_robust_inv | `N_robust / N_resolved_in_both`（分母是两个模型都解析的 pair 数） |
| 冻结 z | `1`, `1.96` |

## 2. 四条定理（`--check` 逐字节复核）

| 定理 | 陈述 | 检验量 | 结果 |
| --- | --- | --- | --- |
| T1 | `sigma_ij = \|dP_A - dP_B\| / sqrt(2)` | max abs err | **8.88e-16 eV** |
| T6a | 反转需 `z <= 1/sqrt(2)`；冻结 `z` 全部超过 | `z*` = 0.707107 | **冻结 z 全部排除反转** |
| T6b | 双方解析子集内反向 pair 数为 0 | max 计数 | **0** |
| T7 | 解析判据 = `\|dY\|/\|dX\|` 的比值律 | 与 `resolved_mask` 不符数 | **0** |

比值律（T7 的显式形式）：

- 同号：`(1 - sqrt(2)/z) <= |dY|/|dX| <= (1 + sqrt(2)/z)`
- 反号：`|dY|/|dX| <= sqrt(2)/z - 1`（`z >= sqrt(2)` 时为空集）

## 3. 逐 block 结果

| rung | 轴 | n | f_robust_inv（冻结） | 双方解析(z=1) | 反向(z=1) | 双方解析(z=1.96) | 反向(z=1.96) | 比值律不符 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P0->P1v | oxidation | 18 | 0.000 | 83 | 0 | 61 | 0 | 0 |
| P0->P1v | reduction | 18 | 0.000 | 44 | 0 | 33 | 0 | 0 |
| P1v->P2a | oxidation | 18 | 0.000 | 125 | 0 | 102 | 0 | 0 |
| P1v->P2a | reduction | 18 | 0.000 | 94 | 0 | 67 | 0 | 0 |
| P0->P2a | oxidation | 18 | 0.000 | 84 | 0 | 60 | 0 | 0 |
| P0->P2a | reduction | 18 | 0.000 | 40 | 0 | 32 | 0 | 0 |
| C0->C1 | oxidation | 10 | 0.000 | 30 | 0 | 24 | 0 | 0 |
| C0->C1 | reduction | 10 | 0.000 | 4 | 0 | 4 | 0 | 0 |

## 4. 多来源 σ 对照（把假设 C 变成可检验）

同一批分子、同一批层，**只换 σ 约定**：

| σ 约定 | 实现数 R | 最大 f_robust_inv (z=1) | 是否出现反转 |
| --- | --- | --- | --- |
| 两臂（主约定） | 2 | 0.0000 | 否 |
| 多来源（docs/08 §5） | 5 | 0.0196 | 是 |

> Same molecules, same layers; only the sigma convention changes. Two-arm sigma (R = 2) yields zero inversions because T6a forbids them; the pooled five-realization sigma (R = 5) is not pinned to the pair of models being compared, so the impossibility lifts and one pair does invert. Hypothesis C is therefore testable -- just not under the convention it was frozen with.
> 绝对计数：`max_n_robust_inversions_z1p0 = 1`（分母是**双方都解析**的 51–60 对，不是 66 对）。

## 5. 预注册假设的可检验性

| 假设 | 冻结判据 | 冻结结论 | 该约定下可检验性 |
| --- | --- | --- | --- |
| `A_cheap_proxy_already_stable` | tau_b / O_k / f_unresolved | NOT SUPPORTED | **TESTABLE** |
| `B_large_shift_small_rank_damage` | tau_b / O_k / f_robust_inv | SUPPORTED | **PARTIALLY TESTABLE** |
| `C_structured_robust_inversion` | f_robust_inv | NOT OBSERVED | **NOT TESTABLE** |
| `D_coordination_state_identity_change` | state identity | OBSERVED | **TESTABLE** |
| `E_delta_learning_beats_direct` | ML error | SUPPORTED（6/8）；例外：C/reduction/X0、C/reduction/X0+X1 | **TESTABLE** |
| `F_delta_not_learnable_from_cheap` | ML transfer | NOT SUPPORTED（Δ 在 6/8 个分组上可从廉价特征学出）；例外：C/reduction/X0、C/reduction/X0+X1（与情形 D 同一根还原轴） | **TESTABLE** |
| `G_most_pairs_unresolved` | f_unresolved | PARTIALLY SUPPORTED (还原轴 C0 -> C1) | **TESTABLE** |

## 6. 必须改写的三处口径

1. **`f_robust_inv = 0` 不得再作为经验观察引用**。它是两臂 σ 约定下的定义性不变量
   （T6a：`z > 1/sqrt(2)` 即不可能）；引用时必须同时给出 σ 约定与该约定下的分母。
2. **Stage 10 假设 C 由 `NOT OBSERVED` 改判 `NOT TESTABLE`**。可检验版本必须换用
   R >= 3 的多来源 σ（§4 已给出阳性对照：同一数据下出现 1 对反转）。
3. **`f_unresolved` 是比值量**（T7）：它度量的是两个模型对同一 pair 的分歧**相对于**
   pair 自身间距的大小，不含任何绝对噪声尺度。报告应同时给出比值分布或其分位。

## 7. 产物与复现

```powershell
.venv\Scripts\python.exe scripts\audit_estimator_circularity.py --check
.venv\Scripts\python.exe scripts\audit_estimator_circularity.py
```

本审计零新增电子结构计算；全部数字从 `outputs/week4`、`outputs/week5`、`outputs/week9`
的冻结产物读回。结论见 `docs/49_round3_adversarial_audit.md`。
