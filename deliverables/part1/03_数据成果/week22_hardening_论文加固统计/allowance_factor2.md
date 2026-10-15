# A3 — 漏解安全定理的因子 2：allowance 的两种严格口径

> 本文档由 `scripts/analyze_w22_allowance.py` 从
> `outputs/week23/targeted_two_guess.json` 与 `outputs/week23/targeted_two_guess_pairs.csv` 渲染。
> **只读复核，不产生新电子结构，不改动任何冻结量或 Stage 16 判定。**

## 0. 一句话结论

论文现用的阈值 `|d0| >= A_axis` 只用了**单格**最大效应 `A_axis`；但一对分子的间距受**两格**扰动，
严格上界是 `2 * A_axis`。用 `2 * A_axis` 重算，**两轴都要保护全部 120 格（节约 0%）**——
这正是 A3 要暴露的代价。把 `A` 重定义到 **pair 级** `max|e_i - e_j|` 后，阈值只比 `A_axis` 高一点点，
节约几乎回到现行口径（86/120、116/120）。三种口径的真实翻转漏检数**全为 0**。

## 1. `A_axis` 定义与来源复核

`A_axis` 的定义（直接引自 `allowance_detail`）：

> max over cells of |value_moread - value_default| on the decision quantity:
> the largest change a missed solution can make to any single cell

| 轴 | `A_axis` (eV) | 最坏格子 | 材料格子数 | 该轴格子总数 |
| --- | --- | --- | --- | --- |
| oxidation | **0.152252** | TMP @ eps=5 | 16 | 120 |
| reduction | **0.285963** | EMC @ eps=1000 | 16 | 120 |

来源：`outputs/week23/targeted_two_guess.json` 的 `allowance_ev` / `allowance_detail`，由 `scripts/plan_targeted_two_guess.py`
从 Stage 16 双初猜目录换算得到。定义是**单格**效应上界。

## 2. 因子 2 的严格上界，与 pair 级重定义

一对 (i, j) 的间距变化为 `|e_i - e_j| <= |e_i| + |e_j| <= 2 * A_axis`，
所以单常数严格可证的上界是 `2 * A_axis`；把它换成 pair 级最大值
`max over pairs |e_i - e_j|` 则是让定理在这份目录上取等的最紧常数。

| 轴 | `A_axis` (eV) | `2 * A_axis` (eV) | pair 级上界 (eV) | pair 级最坏 pair |
| --- | --- | --- | --- | --- |
| oxidation | 0.152252 | **0.304503** | **0.152279** | SL/TMP @ eps=5 |
| reduction | 0.285963 | **0.571926** | **0.285978** | EMC/SN @ eps=1000 |

注：pair 级上界只在 `A_axis` 之上极小的量（氧化的 `+2.77e-05 eV`、还原的 `+1.50e-05 eV`），
说明真实数据里 `|e_i - e_j|` 几乎就等于单格最大值；但这不是定理，只是本目录的实测。

## 3. 三种口径的靶向代价对照

靶向判据：某格被保护 `iff` 它参与的某个 pair 满足 `|d0| < delta`。

### oxidation（实测翻转 19 / 660 对）

| 口径 | delta (eV) | 靶向格子 / 全部 | 节约 | 漏检翻转 |
| --- | --- | --- | --- | --- |
| `current_A_axis` | 0.152252 | **86 / 120** | **28.3%** | **0** |
| `factor2_2A_axis` | 0.304503 | **120 / 120** | **0.0%** | **0** |
| `pair_level_bound` | 0.152279 | **86 / 120** | **28.3%** | **0** |

### reduction（实测翻转 21 / 660 对）

| 口径 | delta (eV) | 靶向格子 / 全部 | 节约 | 漏检翻转 |
| --- | --- | --- | --- | --- |
| `current_A_axis` | 0.285963 | **116 / 120** | **3.3%** | **0** |
| `factor2_2A_axis` | 0.571926 | **120 / 120** | **0.0%** | **0** |
| `pair_level_bound` | 0.285978 | **116 / 120** | **3.3%** | **0** |

## 4. 读法（必须与数字同时写出）

1. 论文的 `A_axis` 口径在本目录上漏检为 0，但它的充分性**不是**定理：定理给的是 `2 * A_axis`。
2. 用 `2 * A_axis` 时节约为 0——即严格的单常数证明要求**保护全部格子**，靶向不再省事。
3. 把 `A` 重定义到 pair 级可让定理取等，且节约基本回归（氧化 86/120 省 28.3%；还原 116/120 省 3.3%）。
4. 三口径漏检均为 0：在这份 1320 对的实测目录上，靶向都是充分的；差别在**可证性**与**代价**。

---

生成时间（UTC）：2026-10-02T06:43:18.324642+00:00
