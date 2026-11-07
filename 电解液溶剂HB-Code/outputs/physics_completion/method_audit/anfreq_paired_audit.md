# AnFreq vs NumFreq 配对审计（全 cohort）

计划 v1.2 条③④ 要求的配对诊断。**每条腿用自己 NumFreq 用过的同一收敛几何**
做 AnFreq 频率单点（无 Opt），因此两法在同一势面点上直接可比。

> **纪律（v1.2 ④）**：本审计只作 Hessian-method sensitivity 登记，
> **不得择优混算、不进 48 态验收分母**。若拟采纳，须走全协议修订并全 cohort 统一重算。

- 已配对：**60/60** 条
- 结论一致：**54** 条
- 结论不一致：**6** 条
- |ΔG| 最大 **4.11 kJ/mol**、中位 0.44 kJ/mol

## 一、不一致清单（分歧全部落在问题腿上）

| 腿 | NumFreq 虚频 | AnFreq 虚频 | NumFreq 虚频值 | AnFreq 虚频值 | ΔG (kJ/mol) | 来源 |
| --- | --- | --- | --- | --- | --- | --- |
| AN/LiM_2plus | 1 | 0 | -127.20 | — | -3.70 | hpc |
| TMP/LiM_2plus | 1 | 0 | -87.23 | — | -2.00 | hpc |
| TMP/LiM_plus | 3 | 2 | -68.14 -51.54 -39.16 | -56.99 -20.02 | +2.18 | hpc |
| TMP/M | 2 | 0 | -46.68 -22.13 | — | -3.01 | hpc |
| TMP/M_plus | 2 | 0 | -70.16 -22.89 | — | -4.11 | hpc |
| TMP/M_tzvpd | 2 | 0 | -72.74 -45.54 | — | -2.24 | hpc |

## 二、一致清单（方法选择在这些腿上无影响）

| 腿 | 虚频(两法一致) | 最低实频 | ΔG (kJ/mol) | 来源 |
| --- | --- | --- | --- | --- |
| AN/LiM_plus | 0 | 117.74 | +0.10 | hpc |
| AN/M | 0 | 406.88 | +0.07 | hpc |
| AN/M_plus | 0 | 301.84 | +0.76 | hpc |
| AN/M_tzvpd | 0 | 405.64 | +0.06 | hpc |
| DEC/LiM_2plus | 0 | 71.38 | +1.06 | hpc |
| DEC/LiM_plus | 0 | 57.67 | +1.33 | hpc |
| DEC/M | 0 | 55.38 | +1.28 | hpc |
| DEC/M_plus | 0 | 61.38 | +0.39 | hpc |
| DEC/M_tzvpd | 0 | 55.53 | +2.64 | hpc |
| DMC/LiM_2plus | 0 | 106.30 | +0.04 | hpc |
| DMC/LiM_plus | 0 | 79.31 | +0.97 | hpc |
| DMC/M | 0 | 117.74 | +0.71 | hpc |
| DMC/M_plus | 0 | 62.07 | +0.03 | hpc |
| DMC/M_tzvpd | 0 | 117.72 | +0.98 | hpc |
| DME/LiM_2plus | 0 | 58.80 | +1.31 | local |
| DME/LiM_plus | 0 | 74.56 | +0.64 | local |
| DME/M | 0 | 54.48 | +1.04 | local |
| DME/M_plus | 0 | 40.80 | -0.17 | local |
| DME/M_tzvpd | 0 | 39.12 | +1.80 | local |
| DMSO/LiM_2plus | 0 | 51.09 | +0.48 | hpc |
| DMSO/LiM_plus | 0 | 65.68 | +0.14 | hpc |
| DMSO/M | 0 | 198.76 | +0.32 | hpc |
| DMSO/M_plus | 0 | 141.78 | +0.72 | hpc |
| DMSO/M_tzvpd | 0 | 202.59 | +0.07 | hpc |
| DOL/LiM_2plus | 0 | 79.87 | -0.02 | local |
| DOL/LiM_plus | 0 | 139.09 | -0.03 | local |
| DOL/M | 0 | 50.96 | +0.28 | local |
| DOL/M_plus | 0 | 170.91 | +0.04 | local |
| DOL/M_tzvpd | 0 | 23.78 | +1.09 | local |
| EC/LiM_2plus | 0 | 39.33 | -0.66 | local |
| EC/LiM_plus | 0 | 72.82 | +0.42 | local |
| EC/M | 0 | 160.31 | +0.09 | hpc |
| EC/M_plus | 0 | 145.98 | -0.35 | hpc |
| EC/M_tzvpd | 0 | 160.59 | +0.07 | hpc |
| EMC/LiM_2plus | 0 | 45.98 | -0.32 | hpc |
| EMC/LiM_plus | 0 | 70.19 | +0.44 | hpc |
| EMC/M | 0 | 80.52 | +0.54 | hpc |
| EMC/M_plus | 0 | 53.04 | +0.68 | hpc |
| EMC/M_tzvpd | 0 | 80.01 | +0.76 | hpc |
| GBL/LiM_2plus | 0 | 63.94 | +0.78 | hpc |
| GBL/LiM_plus | 0 | 59.80 | +0.49 | hpc |
| GBL/M | 0 | 155.26 | +0.16 | local |
| GBL/M_plus | 0 | 176.55 | +0.15 | hpc |
| GBL/M_tzvpd | 0 | 153.79 | +0.19 | local |
| PC/LiM_2plus | 0 | 86.22 | +0.12 | local |
| PC/LiM_plus | 0 | 77.57 | +0.28 | local |
| PC/M | 0 | 98.93 | +0.23 | local |
| PC/M_plus | 0 | 101.34 | +0.10 | local |
| PC/M_tzvpd | 0 | 98.67 | +0.25 | local |
| SL/LiM_2plus | 0 | 61.08 | -0.32 | hpc |
| SL/LiM_plus | 0 | 50.08 | +1.06 | hpc |
| SL/M | 0 | 42.96 | +0.22 | hpc |
| SL/M_plus | 0 | 69.78 | -0.23 | hpc |
| SL/M_tzvpd | 0 | 44.18 | +0.58 | hpc |

## 四、判读

1. **分歧是问题腿特异的**：一致集合覆盖全部常规腿，说明两种 Hessian 在正常体系上等价；
2. 不一致的腿在 AnFreq 下虚频归零或大幅减少，且 ΔG 差异可达数 kJ/mol ——
   量级足以改变排序稳定性判定，故属**协议级**问题而非单腿问题；
3. 部分保留的腿（虚频数减少但未归零）应单独处置，不可与全归零者混为一谈。

**下一步**：由用户裁决是否按 v1.2 ④ 启动全协议修订（全 cohort 统一 AnFreq + 全量重算）。

