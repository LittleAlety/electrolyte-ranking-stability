# P1v vs P1a —— geometry relaxation 是不是一种会改变决策的缺失物理？（R13）

> 由 `scripts/compare_vertical_adiabatic.py` 从 `outputs/phase2_p1a/p1a_adiabatic.csv` 现算。

## 定义

- **P1v**：气相 vertical redox-energy proxy（中性/阳离子/阴离子共用几何 G1，只做单点）→ Week-4 层。
- **P1a**：气相 adiabatic redox thermodynamics（每个电荷态各自 r2SCAN-3c Opt 到自身极小）→ 本层。

## 氧化轴结果

| 量 | 值 |
| --- | --- |
| n | 12 |
| Kendall τ_b(P1v, P1a) | 0.788 |
| Spearman ρ | 0.923 |
| Top-10% / 20% / 30% overlap | 1.00 / 1.00 / 0.75 |
| 位移 d = IP_a − IP_v：mean / std / min / max | -0.380 / 0.207 / -0.950 / -0.141 eV |

三态计数（sigma = 位移 population std = 0.207 eV）：

| 状态 | n | 占比 |
| --- | --- | --- |
| STABLE | 55 | 0.833 |
| UNRESOLVED | 9 | 0.136 |
| ROBUST_INVERSION | 2 | 0.030 |

## 还原轴：按规则排除，而不是补一个数

gas-phase adiabatic EA is excluded by the frozen unbound_anion rule (outputs/week4/p1_core_set_audit.json flags all 18 core-set anions); only the oxidation axis supports a P1v -> P1a comparison。
这不是 runner 的缺陷，而是 P1a 这一层存在的理由：**气相阴离子不束缚，绝热 EA 在气相无物理意义**。
还原轴若要 adiabatic 处理，只能放到有溶剂/配位环境（P2a / C1）里做。

## 逐分子

| name | IP_v (eV) | IP_a (eV) | d (eV) |
| --- | --- | --- | --- |
| EC | 10.7691 | 10.3941 | -0.3750 |
| PC | 10.5388 | 10.2141 | -0.3247 |
| DMC | 10.5799 | 10.1742 | -0.4057 |
| EMC | 10.2016 | 9.2513 | -0.9503 |
| DME | 8.8560 | 8.4460 | -0.4100 |
| DOL | 9.3131 | 9.1724 | -0.1408 |
| GBL | 9.9515 | 9.7071 | -0.2445 |
| AN | 12.1404 | 11.8290 | -0.3114 |
| SN | 11.6036 | 11.3707 | -0.2329 |
| DMSO | 8.8142 | 8.5309 | -0.2832 |
| SL | 9.7931 | 9.5289 | -0.2642 |
| TMP | 10.0568 | 9.4376 | -0.6192 |

