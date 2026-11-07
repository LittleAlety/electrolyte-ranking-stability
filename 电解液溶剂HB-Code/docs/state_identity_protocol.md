# C1 状态身份协议（state-identity protocol，R13）

## 1. 为什么要有这个协议

C1 = Li⁺ 配位条件态。它的 redox 电子**可能不再落在同一个分子上**。Week-5 的
`outputs/week5/c1_state_identity.json` 给出核心事实：

```
还原态 [Li M]0（12 个 cell 的标签计数）
  Li_centered_or_mixed_redox   : 11
  molecule_centered_redox      :  1   (SN / m1)
```

也就是：**12 个还原态里有 11 个外加电子落在 Li 上。** 在这种格子上比较 `dG_red` 的排序，
衡量的其实已经不是「同一个分子被还原的难度」，而是「电子去了哪」——这是 **observable identity failure**，
不是 ranking instability。

冻结定义见 `config/scientific_definitions.yaml` 的
`axis_B_environment_states.C1.redox_state_identity_stratification`。

## 2. 标签词表（冻结）

| 标签 | 判据（几何优先于电子） |
| --- | --- |
| `no_intact_minimum_found` | 该 redox 态的优化几何已失去 Li–M 极小（Li 跑远 / 断开） |
| `dissociated_optimized_product` | 母体连接性断裂 |
| `Li_centered_or_mixed_redox` | \|Mulliken spin on Li\| ≥ 0.5 或 \|Δq(Li)\| ≥ 0.5 |
| `molecule_centered_redox` | \|spin on Li\| ≤ 0.15 且 \|Δq(Li)\| ≤ 0.25 |
| `state_identity_ambiguous` | 两个指标互相矛盾，或都测不出 |
| `reaction_path_verified` | 只有拿到额外 TS / 动力学证据才可指派（本阶段从不指派） |

判据在读数之前写定（`scripts/analyze_c1_state_identity.py` 的 docstring 与 `DEFINITION`）。

## 3. 分层规则（R13 起生效）

```
还原轴 main ranking   ← 只用 molecule_centered_redox
其余所有标签          ← mechanistic state-identity outcome，单独统计
```

实现：`scripts/classify_state_identity.py`（只读已冻结的 Week-5 产物，不跑新 QM），产物在
`outputs/state_identity/`：

```
outputs/state_identity/
├── state_identity_stratification.json      # 主结果 + 三态重标注 + 分辨率曲线
├── state_identity_stratification.csv       # 逐分子：还原/氧化标签、是否进主 ranking
├── state_identity_summary.md               # 人读版
├── molecule_centered/members.csv           # 每个冻结标签一个桶目录
├── li_centered_or_mixed/members.csv
└── no_intact_minimum/members.csv
```

## 4. 结果

| 轴 | 集合 | n | τ_b（C0→C1） |
| --- | --- | --- | --- |
| reduction | all states | 10 | **-0.467** |
| reduction | molecule-centered only | **1** | **无定义（配不成 pair）** |
| oxidation | all states | 10 | 0.689 |
| oxidation | molecule-centered only | 6 | 0.733 |

冻结还原对（45 个 pair）的三态重标注：STABLE **4**、UNRESOLVED **41**、ROBUST_INVERSION **0**。

## 5. 正确表述模板

- ❌ 「Li⁺ 配位导致还原排序翻转。」
- ✅ 「**Li⁺ 配位除了改变 redox 数值，还会改变被还原态的电子身份；在 12 个还原态里 11 个电子转移到
  Li 上。因此还原轴的排序必须在 state-identity 分层之后才可解释，而分子中心还原态在本 core set 里只剩 1 个。**」

## 6. 与氧化轴的关系

氧化态（`[Li M]2+`，空穴）12 个里 8 个是 `molecule_centered_redox`、4 个是 `no_intact_minimum_found`。
氧化轴因此**可以**做分层后的排序（n = 6，τ_b = 0.733），但同样必须把 4 个 `no_intact_minimum_found`
作为 outcome 单独报，而不是塞进数值排序。
