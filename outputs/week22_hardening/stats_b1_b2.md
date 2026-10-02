# Week 22 加固统计证据 B1 / B2

- 生成时间(UTC): `2026-10-02T06:45:56.995581+00:00`
- 随机种子: B1=20261002, B2(12 重抽)=20261003, B2(匹配 10)=20261004
- Bootstrap 次数: B1=20000, B2=20000
- 置信区间口径: percentile (primary) and BCa (reported alongside); B2 uses percentile because the tau_b statistic is a rank statistic with a discrete/non-smooth support where the BCa acceleration is not uniquely defined.
- 环境: Python 3.10.11 / numpy 2.2.6

## B1: 台阶点秩相关

数据来源: `outputs/week9/stage10_ladder.json` 的 `hypothesis_test.points`（10 个点，每个点 = 一个 (rung, axis) 组合）。
三个统计量定义: ρ(shift_std, τ_b)、ρ(|shift_mean|, τ_b)、ρ(shift_std, f_unresolved)。

| 口径 | ρ(shift_std, τ_b) | ρ(|shift_mean|, τ_b) | ρ(shift_std, f_unresolved) |
|---|---|---|---|
| 观测点估计(全 10 点) | -0.8511 | -0.5350 | 0.8936 |
| 剔除 C0→C1 还原轴后 (9 点) | -0.8285 | -0.3933 | 0.8703 |
| 剔除全部条件态台阶后 (6 点) | -0.9429 | -0.6000 | 0.9429 |

95% CI（percentile / BCa）:

| 口径 | 统计量 | 观测 | percentile 95% CI | BCa 95% CI |
|---|---|---|---|---|
| 全 10 点 | ρ(std,τ_b) | -0.8511 | [-0.9874, -0.4242] | [-0.9901, -0.4502] |
| 全 10 点 | ρ(|mean|,τ_b) | -0.5350 | [-0.9608, 0.2453] | [-0.9479, 0.3548] |
| 全 10 点 | ρ(std,f_unres) | 0.8936 | [0.4396, 1.0000] | [0.3885, 1.0000] |
| 剔除 C0→C1 还原轴 (9 点) | ρ(std,τ_b) | -0.8285 | [-1.0000, -0.2730] | [-1.0000, -0.3504] |
| 剔除 C0→C1 还原轴 (9 点) | ρ(|mean|,τ_b) | -0.3933 | [-0.9825, 0.5179] | [-0.9652, 0.5897] |
| 剔除 C0→C1 还原轴 (9 点) | ρ(std,f_unres) | 0.8703 | [0.2769, 1.0000] | [0.1429, 1.0000] |
| 剔除全部条件态 (6 点) | ρ(std,τ_b) | -0.9429 | [-1.0000, -0.5152] | [-1.0000, 0.0000] |
| 剔除全部条件态 (6 点) | ρ(|mean|,τ_b) | -0.6000 | [-1.0000, 0.8000] | [-1.0000, 1.0000] |
| 剔除全部条件态 (6 点) | ρ(std,f_unres) | 0.9429 | [0.5000, 1.0000] | [0.0000, 1.0000] |

**独立性说明**: 10 个点不独立 —— 同一台阶的两个轴（氧化/还原）共享同一批分子，且相邻台阶复用同一批分子。因此 bootstrap 把点当作可交换的做法偏乐观，该 CI 只作为样本内稳定性检查，不作总体推断。

剔除的点:
- `drop_C0_to_C1_reduction`: C0_to_C1/reduction
- `drop_all_conditional`: C0_to_C1/oxidation, C0_to_C1/reduction, C1_to_C2/oxidation, C1_to_C2/reduction

σ-anatomy 交叉核对（P0→P1 台阶的 f_unresolved）:
- oxidation: ladder=0.1333, stage11=0.1333, 一致=True
- reduction: ladder=0.7333, stage11=0.7333, 一致=True

## B2: 气相锚点配对 bootstrap（GFN2-xTB ΔSCF P0′ vs r2SCAN-3c P1）

数据来源: `outputs/week4/p1_anchor_comparison.json` 的逐分子 `pairs`（P1_r2SCAN3c 与 GFN2_dSCF_xTB），锚点来自 `data/anchors/gas_phase_anchors.csv`（property=IP，12 个实验值）。
- 12 个锚点分子: DMC, EC, VC, DME, DOL, EA, MA, GBL, SL, DMSO, AN, TMP
- GFN2-xTB ΔSCF 覆盖率: 仅 10 个分子（缺 MA, VC）

### 主口径: 从 12 个锚点有放回重抽（重现表 1 的 0.911 vs 0.727）

- 两臂点估计: τ_b(P0′) = 0.9111, τ_b(P1) = 0.7273
- Δτ_b 点估计 = 0.1838
- Δτ_b 95% percentile CI = [-0.1774, 0.6072]
- P(Δτ_b > 0) = 0.8389  (P(<0) = 0.1477, P(=0) = 0.0134)
- 有效重抽数 = 20000

### 稳健口径: 覆盖率匹配的 10 分子（两臂同一重抽集）

- 分子: DMC, EC, DME, DOL, EA, GBL, SL, DMSO, AN, TMP
- 两臂点估计: τ_b(P0′) = 0.9111, τ_b(P1) = 0.7778
- Δτ_b 点估计 = 0.1333
- Δτ_b 95% percentile CI = [-0.1951, 0.5500]
- P(Δτ_b > 0) = 0.7313

说明: 主口径下两臂覆盖不同（P0′ n=10, P1 n=12），与表 1 印刷值一致；匹配口径把两臂放在同一分子集上比较，是更严格的"配对"检验。两者结论一致时方可写入论文。

## 文件清单

- `scripts/analyze_w22_stats.py`
- `outputs/week22_hardening/stats_b1_b2.json`
- `outputs/week22_hardening/stats_b1_b2.md`
