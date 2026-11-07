# R15 — 模型层独立性 / 信息增益审计（对抗审计第 3 轮 · D 项）

> 本文档由 `scripts/audit_layer_independence.py` 从冻结产物现算。
> **只读：从已冻结的逐分子位移重建每一级，不跑新电子结构。**

## 0. 一句话结论

五级阶梯的每一级都是一个独立位移向量：同轴 rung 对之间的 |Pearson| 中位 **0.383**、最大 **0.791**，
因此层不是同一信号的再编码。但阶梯本身是**分解**而非互相独立的证据：
`P0→P2 ≡ (P0→P1) + (P1→P2)`，共享的 P1 锚点在两个冻结文件里一致（最大偏差 0.00e+00 eV）。

判定：**PASS**。

## 1. 每级矩阵

| rung | 新增物理 | 分子 | job | 氧化 mean ± std | 氧化 rigidity | 还原 mean ± std | 还原 rigidity |
| --- | --- | ---: | ---: | --- | ---: | --- | ---: |
| `P0_to_P1` | Koopmans/xTB orbital proxy -> r2SCAN-3c vertical redox energy at the shared geometry | 18 | 54 | -1.550 ± 0.735 | 2.11 | +7.592 ± 2.209 | 3.44 |
| `P1_to_P2` | bulk dielectric polarisation of the environment | 18 | 54 | -2.393 ± 0.302 | 7.93 | -2.173 ± 0.320 | 6.78 |
| `G1_to_G2` | geometry relaxation (conformer/minimum change), no new environment | 12 | 48 | -0.002 ± 0.052 | 0.04 | -0.118 ± 0.080 | 1.48 |
| `C0_to_C1` | Li+ first coordination (charge transfer, motif switch) | 10 | 92 | +4.887 ± 0.595 | 8.22 | -6.578 ± 0.832 | 7.90 |
| `C1_to_C2` | first-shell coordination number 1 -> 2 | 10 | 36 | -1.700 ± 0.259 | 6.55 | +1.199 ± 0.335 | 3.58 |

`rigidity = |mean| / std`：按 Stage-11 `T3`，常数位移对 sigma / tau_b / f_unresolved / f_robust_inv 完全无影响，
因此 rigidity 越高，该级越接近一个“免费”的刚性平移，**携带信息的是 dispersion**。

## 2. 每级对排序的伤害（冻结 ladder 读回）

| rung | 轴 | tau_b | 1 - tau_b | f_unresolved before | f_unresolved after | f_robust_inv |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `P0_to_P1` | oxidation | 0.6732 | 0.3268 | 0.3595 | 0.1569 | 0.0000 |
| `P0_to_P1` | reduction | 0.5948 | 0.4052 | 0.1699 | 0.6209 | 0.0000 |
| `P1_to_P2` | oxidation | 0.8954 | 0.1046 | 0.0915 | 0.1111 | 0.0000 |
| `P1_to_P2` | reduction | 0.6732 | 0.3268 | 0.2353 | 0.2222 | 0.0000 |
| `G1_to_G2` | oxidation | 0.9394 | 0.0606 | 0.0152 | 0.0303 | 0.0000 |
| `G1_to_G2` | reduction | 0.8485 | 0.1515 | 0.0455 | 0.0606 | 0.0000 |
| `C0_to_C1` | oxidation | 0.6889 | 0.3111 | 0.1778 | 0.2000 | 0.0000 |
| `C0_to_C1` | reduction | -0.4667 | 1.4667 | 0.4444 | 0.8000 | 0.0000 |
| `C1_to_C2` | oxidation | 0.8667 | 0.1333 | 0.1333 | 0.0889 | 0.0000 |
| `C1_to_C2` | reduction | 0.2889 | 0.7111 | 0.3556 | 0.3556 | 0.0000 |

## 3. 跳板对位移相关（同轴、共享分子上现算）

| rung A | rung B | 轴 | 共享分子 | Pearson | Spearman |
| --- | --- | --- | ---: | ---: | ---: |
| `P0_to_P1` | `P1_to_P2` | oxidation | 18 | -0.612 | -0.346 |
| `P0_to_P1` | `G1_to_G2` | oxidation | 12 | -0.466 | -0.308 |
| `P0_to_P1` | `C0_to_C1` | oxidation | 10 | +0.064 | -0.042 |
| `P0_to_P1` | `C1_to_C2` | oxidation | 10 | -0.494 | -0.576 |
| `P1_to_P2` | `G1_to_G2` | oxidation | 12 | -0.162 | -0.070 |
| `P1_to_P2` | `C0_to_C1` | oxidation | 10 | -0.443 | -0.188 |
| `P1_to_P2` | `C1_to_C2` | oxidation | 10 | +0.611 | +0.321 |
| `G1_to_G2` | `C0_to_C1` | oxidation | 10 | +0.461 | +0.479 |
| `G1_to_G2` | `C1_to_C2` | oxidation | 10 | +0.170 | +0.285 |
| `C0_to_C1` | `C1_to_C2` | oxidation | 10 | -0.340 | -0.333 |
| `P0_to_P1` | `P1_to_P2` | reduction | 18 | -0.350 | -0.424 |
| `P0_to_P1` | `G1_to_G2` | reduction | 12 | -0.127 | -0.161 |
| `P0_to_P1` | `C0_to_C1` | reduction | 10 | +0.427 | +0.188 |
| `P0_to_P1` | `C1_to_C2` | reduction | 10 | -0.345 | -0.382 |
| `P1_to_P2` | `G1_to_G2` | reduction | 12 | -0.218 | -0.434 |
| `P1_to_P2` | `C0_to_C1` | reduction | 10 | +0.742 | +0.685 |
| `P1_to_P2` | `C1_to_C2` | reduction | 10 | -0.416 | -0.418 |
| `G1_to_G2` | `C0_to_C1` | reduction | 10 | -0.075 | -0.261 |
| `G1_to_G2` | `C1_to_C2` | reduction | 10 | +0.093 | +0.333 |
| `C0_to_C1` | `C1_to_C2` | reduction | 10 | -0.791 | -0.430 |

## 4. 分解性校验（共享 P1 锚点）

| 轴 | 列 | 共享分子 | 最大绝对偏差（eV） |
| --- | --- | ---: | ---: |
| oxidation | `p1_ox_ev` | 18 | 0.00e+00 |
| reduction | `p1_red_ev` | 18 | 0.00e+00 |

因此 `P0→P2 ≡ (P0→P1) + (P1→P2)` 是严格恒等式：中间级没有额外独立信息，
只有在不同分子集 / 不同物理机制时才是新证据。

## 5. 逐条发现

| id | 级别 | 说明 |
| --- | --- | --- |
| D1 | **PASS** | the rungs are not re-encodings of one signal: over 20 same-axis rung pairs the median |Pearson| is 0.383 and the largest is 0.791 on 10 shared molecules |
| D2 | **INFO** | the ladder is a decomposition, not independent evidence: the shared P1 anchor agrees across the two frozen files (max |dev| 0.00e+00 eV on 18 molecules), so P0->P2 is exactly (P0->P1)+(P1->P2) |
| D3 | **INFO** | by Stage-11 T3 a constant shift is free, so the decision-relevant part of a rung is its dispersion; rigidity |mean|/std ranges 0.04-8.22 across rung-axis cells |
| D4 | **INFO** | the most expensive rung is C0->C1 (92 jobs) and it is the only rung that damages a ranking (reduction tau_b = -0.4667, f_unresolved = 0.800); the cheap geometry rung G1->G2 costs 48 jobs and leaves reduction tau_b = 0.8485 |

## 6. 纪律声明

- 本审计不跑任何新电子结构；所有数字均为已冻结产物的现算读出。
- 本审计不改变任何既有判决；不读取仓库外文件。
- “独立”在本文中只指位移向量不相关，不指物理机制互斥。
