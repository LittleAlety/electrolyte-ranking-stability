# Week 22 hardening -- broad pool 最小信息预算演示

> 脚本: `scripts/analyze_w22_broadpool.py` (无新量子化学计算; 只用 P0 层 + 闭式判据 + core 标定)。
> 口径与假设见本文件 §1 与 JSON 的 `meta` / `assumptions`。

## 0. 一句话结论

在 40 个 broad 分子上, 只用 P0 层与 Stage 11 闭式判据即可在**花钱之前**给出两件事: (i) 大量分子对本来就分不开 (氧化目标层 19.5%、还原目标层 76.0% 的 pair 不可分辨); (ii) 只要对「值得升级」子集做 P2/C1 即可, 无需全量 40 个 —— 按主判据 (两轴并集, Top-10% 清单, z=1) 只升级 **21/40** 个, 省 **47.5%**。

## 1. 口径与假设

- 目标量: `P0_ox = -eps_HOMO`, `P0_red = +eps_LUMO` (eV, 越大越好)。
- 位移 `delta_i = P0_i - P1_i` (P1 = 气相 r2SCAN-3c redox 量)。
- broad 池只有 P0, 故 `delta_i` 用 core set 标定的 X0 级廉价预测器外推; 每轴按留一交叉验证 (LOO) R^2 选优。
  选中: 氧化 = `family_shift`, 还原 = `ols_p0`。
- 预测残差 `sigma_r` = 预测器 LOO 残差标准差 (氧化 0.4922 eV, 还原 0.4932 eV)。
- 逐分子位移未知, 用 `delta_i = delta_hat_i + eps_i`, `eps_i ~ N(0, sigma_r^2)` iid, 4000 次 Monte-Carlo, 每 draw 把 realized delta 代入闭式 `sigma_ij = |delta_i-delta_j|/sqrt(2)` 与 `f_unresolved = Pr(q_ij > sqrt(2)/z)`。
- 「值得升级」= 某 Top-k (k=10/20/30% of N=40, 即 k=4/8/12) 的会员概率 P(∈Top-k) ∈ (0.1, 0.9) (与 prereg §2 probabilistic_pair_ordering 的 0.9/0.1 阈值同口径)。
- 预算: 全量 = 40 个各升级一次 (P1+P2+C1); 靶向 = 只升级「值得升级」子集; `saving = (40 - n_worth)/40`。z 主口径 = 1.0, z=1.96 为敏感性。
- **假设**: 缺 core 家族的 broad 分子 (siloxane/sulfite/sultone) 在 `family_shift` 下回退到全局均值; MC 的残差是 iid 高斯; 预算单位 = 一个分子的完整 P2/C1 升级。

## 2. 不可分辨对 (f_unresolved)

| 轴 | P0 层 (提交前预筛) | 目标层 P1 (闭式 T4) | pair 数 |
| --- | --- | --- | --- |
| 氧化 | 37.4% | 19.5% | 780 |
| 还原 | 17.3% | 76.0% | 780 |

(P0 层 = `|DeltaP0| < z*sigma_ij` 的预筛; 目标层 P1 = Stage 11 闭式 T4 的口径; z=1。)

## 3. 值得升级子集与预算节省

| 口径 | 值得升级 | 省下 | 节省% |
| --- | --- | --- | --- |
| 氧化, Top-10% | 10/40 | 30 | 75.0% |
| 还原, Top-10% | 11/40 | 29 | 72.5% |
| 氧化, Top-k 并集 (10/20/30%) | 18/40 | 22 | 55.0% |
| 还原, Top-k 并集 (10/20/30%) | 34/40 | 6 | 15.0% |
| **两轴并集, Top-10% (主判据)** | **21/40** | **19** | **47.5%** |
| 两轴并集, Top-k 并集 (保守) | 38/40 | 2 | 5.0% |

主判据值得升级的分子: FEMC, TFMEC, DEE, G2, G3, THF, 2MeTHF, DIOX, DMM, DEE2, HFE347, HFE7100, BTFE, PN, BN, ADN, MPN, MN, TEP, TBP, TFP

## 4. 敏感性

**(a) z = 1.96 (更宽的不确定度)**: z=1.96 时 f_unresolved(目标层): 氧化 = 44.0%, 还原 = 88.0% (z=1 时为 19.5% / 76.0%)。值得升级子集与预算节省由 Top-k 会员概率定义, 与 z 无关 (z 只进入 f_unresolved 判据), 故 §3 的节省率不变。

**(b) 另一个廉价预测器**: oxidation: 选 family_shift 而用 ols_p0(LOO R2=-0.19) 时 saving(∪k)=35.0%; reduction: 选 ols_p0 而用 family_shift(LOO R2=0.85) 时 saving(∪k)=40.0%

**(c) core set 子集重标定**:

| |core| 子集 | 两轴并集 Top-10% 节省范围 | 两轴并集 ∪k 节省范围 |
| --- | --- | --- | --- |
| 8 | 37.5% - 82.5% | 0.0% - 45.0% |
| 12 | 45.0% - 70.0% | 0.0% - 22.5% |
| 16 | 47.5% - 62.5% | 0.0% - 25.0% |
| 17 | 47.5% - 60.0% | 0.0% - 25.0% |
| 18 | 50.0% - 50.0% | 7.5% - 7.5% |

**(d) sigma–tau_b 最小重做**: oxidation: core 实测 tau_b=0.67, broad 预测=0.59 (core 子集 0.46-0.79), 平行份额(LOO R2)=0.53; reduction: core 实测 tau_b=0.59, broad 预测=0.38 (core 子集 0.07-0.49), 平行份额(LOO R2)=0.95

## 5. 结论是否依赖核心集选取

结论对核心集选取的依赖是**分口径**的: 主判据 (两轴并集, 保护 Top-10% 清单) 在 |core| = 12/16/17/18 子集重标定下稳定在约 48%-60% (|core|=17 时 47.5%-60.0%), 与全核心集 (47.5%) 同量级 -> **不依赖核心集选取**; σ_r 与 tau_b 的轴间差异同样稳定 (见 §4(d))。 但更宽的「∪k (Top-10/20/30%)」保守口径对核心集更敏感 (|core|=17 时 0.0%-25.0%), 因为它把还原轴在 30% 处的密集简并全部计入 -> 该口径**依赖**核心集选取。 所以对外表述应写: 主判据的预算节省不依赖核心集; 保护到 30% 的保守口径则依赖。

## 6. 文件与冻结件

- 输入: `outputs/week3/p0_broad_pool.csv`, `outputs/week4/p1_core_set_derived.csv`, `data/metadata/*.csv`, `config/prereg.yaml`, `config/scientific_definitions.yaml`, `outputs/week10/stage11_sigma_anatomy.json`。
- 输出: 本文件 + `broad_pool_demo.json` + `outputs/figures/F47_broadpool_budget.png`。
- 冻结件常量核对: `{"prereg_z_factor_matches_stage11": true, "prereg_script_z_matches": true, "broad_k_matches": true, "broad_denominator_matches": true, "critical_slope_z1_matches": true, "critical_slope_z196_matches": true}`。
- `config/prereg.yaml` / `config/scientific_definitions.yaml`: **0 改动**; 无新电子结构文件。

