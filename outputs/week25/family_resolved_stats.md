# Week 25 · Stage 6：family-resolved 与 cross-family 统计

本文件回应核心文件 v2 §19 Stage 6（L1229-1251）列出的两项交付（family-resolved statistics 与 cross-family statistics），并落实 §13.3（L915-919）对 60-100 个 core points 的统计边界要求：**每个 family 的统计量必须带 bootstrap 区间，且不得读成显著性**。

零新增电子结构计算：全部数字由 `outputs/week9/stage10_ladder.json` 已冻结的五级台阶逐分子产物重算得到，口径与 `outputs/week9` 完全一致。

## 0. 口径与随机种子

- 轴约定：`p_red = -EA`，两条轴都 `higher_is_better`（沿用 stage10）。
- pair tolerance 口径：`ranking.resolved_mask`，`resolved(i,j) <=> |dP_ij| >= max(z*sigma_ij, delta)`；sigma 由两级台阶作为两次实现、`quantify_method_sigma(ddof=1, stat=std)` 给出（与 `layer_stability` / `stage10_ladder.json` 同一口径）。
- `z = 1.0`（冻结于 `config/prereg.yaml` 的 `pair_comparison.z_factor.value`）；既有产物未施加 `delta_m`，故本文件`tolerance = 0.0 eV`，另报 `z = 1.96` 敏感性列。
- 家族内 τ_b 仅在家族分子数 ≥ 3 时定义；n = 2（只有 1 对）与 n = 1 一律 `not_estimable`。
- 随机种子：`seed = 20261002`；bootstrap `draws = 5000`；CI 水平 95%。
- population：native-18 与 common-10 **分别报告**（n 不同，绝不合并）。

## 1. 家族构成（8 个家族，18 分子）

| 家族 | 分子数 | 成员 | 家族内 τ_b 是否可估计 |
|---|---|---|---|
| cyclic_carbonate | 4 | EC, FEC, PC, VC | 是 |
| ester | 3 | EA, GBL, MA | 是 |
| ether | 3 | DME, DOL, TEGDME | 是 |
| linear_carbonate | 3 | DEC, DMC, EMC | 是 |
| nitrile | 2 | AN, SN | 否（n_equals_2_single_pair） |
| phosphate | 1 | TMP | 否（single_molecule_family） |
| sulfone | 1 | SL | 否（single_molecule_family） |
| sulfoxide | 1 | DMSO | 否（single_molecule_family） |

## 2. 计数

- (population × 台阶 × 轴 × 家族) 组合总数：**160**
- 家族内 τ_b 可估计：**16**；`not_estimable`：**144**
  - native-18：组合 80，可估计 16，`not_estimable` 64
  - common-10：组合 80，可估计 0，`not_estimable` 80
- `not_estimable` 原因分布：n_equals_2_single_pair=40, single_molecule_family=104
- 重建校验：对 `outputs/week9/stage10_ladder.json` 的 `shift_mean/std/tau_b/f_unresolved` 共 100 个数值逐项重算，最大绝对偏差 = 1.110e-16（OK）。

## 3. family-resolved：家族内逐分子位移 mean / std / n

位移 = after - before（eV）；单元格为 `mean / std / n`。

### native-18

| 台阶 | 轴 | cyclic_carbonate | ester | ether | linear_carbonate | nitrile | phosphate | sulfone | sulfoxide |
|---|---|---|---|---|---|---|---|---|---|
| P0_to_P1 | oxidation | -1.822 / 0.295 / 4 | -1.339 / 0.107 / 3 | -2.238 / 0.685 / 3 | -1.725 / 0.204 / 3 | 0.106 / 0.599 / 2 | -1.847 / -- / 1 | -1.457 / -- / 1 | -1.610 / -- / 1 |
| P0_to_P1 | reduction | 8.920 / 0.263 / 4 | 8.916 / 0.056 / 3 | 3.412 / 0.655 / 3 | 9.116 / 0.140 / 3 | 8.425 / 0.384 / 2 | 4.819 / -- / 1 | 6.830 / -- / 1 | 8.140 / -- / 1 |
| P1_to_P2 | oxidation | -2.623 / 0.131 / 4 | -2.340 / 0.061 / 3 | -2.219 / 0.521 / 3 | -2.246 / 0.149 / 3 | -2.749 / 0.224 / 2 | -1.919 / -- / 1 | -2.361 / -- / 1 | -2.401 / -- / 1 |
| P1_to_P2 | reduction | -2.066 / 0.080 / 4 | -2.298 / 0.042 / 3 | -2.091 / 0.657 / 3 | -2.479 / 0.137 / 3 | -2.264 / 0.410 / 2 | -1.901 / -- / 1 | -1.788 / -- / 1 | -2.027 / -- / 1 |
| G1_to_G2 | oxidation | 0.037 / 0.035 / 2 | 0.039 / -- / 1 | 0.050 / 0.024 / 2 | 0.023 / 0.009 / 2 | -0.056 / 0.009 / 2 | -0.077 / -- / 1 | -0.058 / -- / 1 | -0.040 / -- / 1 |
| G1_to_G2 | reduction | -0.110 / 0.048 / 2 | -0.119 / -- / 1 | -0.084 / 0.035 / 2 | -0.208 / 0.172 / 2 | -0.081 / 0.076 / 2 | -0.174 / -- / 1 | -0.115 / -- / 1 | -0.037 / -- / 1 |
| C0_to_C1 | oxidation | 4.321 / -- / 1 | 4.901 / -- / 1 | 5.645 / 0.722 / 2 | 4.335 / -- / 1 | 4.941 / 0.232 / 2 | 4.029 / -- / 1 | 4.929 / -- / 1 | 5.184 / -- / 1 |
| C0_to_C1 | reduction | -6.155 / -- / 1 | -6.178 / -- / 1 | -7.564 / 0.703 / 2 | -7.157 / -- / 1 | -6.000 / 1.517 / 2 | -6.477 / -- / 1 | -6.220 / -- / 1 | -6.466 / -- / 1 |
| C1_to_C2 | oxidation | -1.763 / -- / 1 | -1.731 / -- / 1 | -1.574 / 0.018 / 2 | -1.491 / -- / 1 | -1.900 / 0.006 / 2 | -1.147 / -- / 1 | -2.011 / -- / 1 | -1.908 / -- / 1 |
| C1_to_C2 | reduction | 1.469 / -- / 1 | 1.023 / -- / 1 | 1.475 / 0.038 / 2 | 1.273 / -- / 1 | 0.863 / 0.669 / 2 | 1.281 / -- / 1 | 0.962 / -- / 1 | 1.303 / -- / 1 |

### common-10

| 台阶 | 轴 | cyclic_carbonate | ester | ether | linear_carbonate | nitrile | phosphate | sulfone | sulfoxide |
|---|---|---|---|---|---|---|---|---|---|
| P0_to_P1 | oxidation | -1.633 / -- / 1 | -1.445 / -- / 1 | -1.851 / 0.201 / 2 | -1.503 / -- / 1 | 0.106 / 0.599 / 2 | -1.847 / -- / 1 | -1.457 / -- / 1 | -1.610 / -- / 1 |
| P0_to_P1 | reduction | 8.674 / -- / 1 | 8.873 / -- / 1 | 3.589 / 0.817 / 2 | 9.278 / -- / 1 | 8.425 / 0.384 / 2 | 4.819 / -- / 1 | 6.830 / -- / 1 | 8.140 / -- / 1 |
| P1_to_P2 | oxidation | -2.708 / -- / 1 | -2.341 / -- / 1 | -2.506 / 0.220 / 2 | -2.410 / -- / 1 | -2.749 / 0.224 / 2 | -1.919 / -- / 1 | -2.361 / -- / 1 | -2.401 / -- / 1 |
| P1_to_P2 | reduction | -2.002 / -- / 1 | -2.253 / -- / 1 | -2.449 / 0.311 / 2 | -2.325 / -- / 1 | -2.264 / 0.410 / 2 | -1.901 / -- / 1 | -1.788 / -- / 1 | -2.027 / -- / 1 |
| G1_to_G2 | oxidation | 0.012 / -- / 1 | 0.039 / -- / 1 | 0.050 / 0.024 / 2 | 0.017 / -- / 1 | -0.056 / 0.009 / 2 | -0.077 / -- / 1 | -0.058 / -- / 1 | -0.040 / -- / 1 |
| G1_to_G2 | reduction | -0.144 / -- / 1 | -0.119 / -- / 1 | -0.084 / 0.035 / 2 | -0.330 / -- / 1 | -0.081 / 0.076 / 2 | -0.174 / -- / 1 | -0.115 / -- / 1 | -0.037 / -- / 1 |
| C0_to_C1 | oxidation | 4.321 / -- / 1 | 4.901 / -- / 1 | 5.645 / 0.722 / 2 | 4.335 / -- / 1 | 4.941 / 0.232 / 2 | 4.029 / -- / 1 | 4.929 / -- / 1 | 5.184 / -- / 1 |
| C0_to_C1 | reduction | -6.155 / -- / 1 | -6.178 / -- / 1 | -7.564 / 0.703 / 2 | -7.157 / -- / 1 | -6.000 / 1.517 / 2 | -6.477 / -- / 1 | -6.220 / -- / 1 | -6.466 / -- / 1 |
| C1_to_C2 | oxidation | -1.763 / -- / 1 | -1.731 / -- / 1 | -1.574 / 0.018 / 2 | -1.491 / -- / 1 | -1.900 / 0.006 / 2 | -1.147 / -- / 1 | -2.011 / -- / 1 | -1.908 / -- / 1 |
| C1_to_C2 | reduction | 1.469 / -- / 1 | 1.023 / -- / 1 | 1.475 / 0.038 / 2 | 1.273 / -- / 1 | 0.863 / 0.669 / 2 | 1.281 / -- / 1 | 0.962 / -- / 1 | 1.303 / -- / 1 |

## 4. family-resolved：家族内 τ_b（可估计者才给数值）

`n.e.` = not_estimable（家族分子数 < 3）。完整清单见 json。

### native-18

| 台阶 | 轴 | cyclic_carbonate | ester | ether | linear_carbonate | nitrile | phosphate | sulfone | sulfoxide |
|---|---|---|---|---|---|---|---|---|---|
| P0_to_P1 | oxidation | 1.000 | 0.333 | 1.000 | 1.000 | n.e. | n.e. | n.e. | n.e. |
| P0_to_P1 | reduction | 1.000 | 1.000 | 0.333 | -0.333 | n.e. | n.e. | n.e. | n.e. |
| P1_to_P2 | oxidation | 1.000 | 1.000 | 1.000 | 1.000 | n.e. | n.e. | n.e. | n.e. |
| P1_to_P2 | reduction | 1.000 | 1.000 | -0.333 | 1.000 | n.e. | n.e. | n.e. | n.e. |
| G1_to_G2 | oxidation | n.e. | n.e. | n.e. | n.e. | n.e. | n.e. | n.e. | n.e. |
| G1_to_G2 | reduction | n.e. | n.e. | n.e. | n.e. | n.e. | n.e. | n.e. | n.e. |
| C0_to_C1 | oxidation | n.e. | n.e. | n.e. | n.e. | n.e. | n.e. | n.e. | n.e. |
| C0_to_C1 | reduction | n.e. | n.e. | n.e. | n.e. | n.e. | n.e. | n.e. | n.e. |
| C1_to_C2 | oxidation | n.e. | n.e. | n.e. | n.e. | n.e. | n.e. | n.e. | n.e. |
| C1_to_C2 | reduction | n.e. | n.e. | n.e. | n.e. | n.e. | n.e. | n.e. | n.e. |

### common-10

| 台阶 | 轴 | cyclic_carbonate | ester | ether | linear_carbonate | nitrile | phosphate | sulfone | sulfoxide |
|---|---|---|---|---|---|---|---|---|---|
| P0_to_P1 | oxidation | n.e. | n.e. | n.e. | n.e. | n.e. | n.e. | n.e. | n.e. |
| P0_to_P1 | reduction | n.e. | n.e. | n.e. | n.e. | n.e. | n.e. | n.e. | n.e. |
| P1_to_P2 | oxidation | n.e. | n.e. | n.e. | n.e. | n.e. | n.e. | n.e. | n.e. |
| P1_to_P2 | reduction | n.e. | n.e. | n.e. | n.e. | n.e. | n.e. | n.e. | n.e. |
| G1_to_G2 | oxidation | n.e. | n.e. | n.e. | n.e. | n.e. | n.e. | n.e. | n.e. |
| G1_to_G2 | reduction | n.e. | n.e. | n.e. | n.e. | n.e. | n.e. | n.e. | n.e. |
| C0_to_C1 | oxidation | n.e. | n.e. | n.e. | n.e. | n.e. | n.e. | n.e. | n.e. |
| C0_to_C1 | reduction | n.e. | n.e. | n.e. | n.e. | n.e. | n.e. | n.e. | n.e. |
| C1_to_C2 | oxidation | n.e. | n.e. | n.e. | n.e. | n.e. | n.e. | n.e. | n.e. |
| C1_to_C2 | reduction | n.e. | n.e. | n.e. | n.e. | n.e. | n.e. | n.e. | n.e. |

### 4.1 可估计组合的 τ_b 与 bootstrap 95% CI

| population | 台阶 | 轴 | 家族 | n | τ_b | CI95 low | CI95 high | 有效重抽样 |
|---|---|---|---|---|---|---|---|---|
| native-18 | P0_to_P1 | oxidation | cyclic_carbonate | 4 | 1.000 | 1.000 | 1.000 | 4922 |
| native-18 | P0_to_P1 | oxidation | ester | 3 | 0.333 | -1.000 | 1.000 | 4452 |
| native-18 | P0_to_P1 | oxidation | ether | 3 | 1.000 | 1.000 | 1.000 | 4451 |
| native-18 | P0_to_P1 | oxidation | linear_carbonate | 3 | 1.000 | 1.000 | 1.000 | 4431 |
| native-18 | P0_to_P1 | reduction | cyclic_carbonate | 4 | 1.000 | 1.000 | 1.000 | 4928 |
| native-18 | P0_to_P1 | reduction | ester | 3 | 1.000 | 1.000 | 1.000 | 4484 |
| native-18 | P0_to_P1 | reduction | ether | 3 | 0.333 | -1.000 | 1.000 | 4457 |
| native-18 | P0_to_P1 | reduction | linear_carbonate | 3 | -0.333 | -1.000 | 1.000 | 4444 |
| native-18 | P1_to_P2 | oxidation | cyclic_carbonate | 4 | 1.000 | 1.000 | 1.000 | 4909 |
| native-18 | P1_to_P2 | oxidation | ester | 3 | 1.000 | 1.000 | 1.000 | 4458 |
| native-18 | P1_to_P2 | oxidation | ether | 3 | 1.000 | 1.000 | 1.000 | 4485 |
| native-18 | P1_to_P2 | oxidation | linear_carbonate | 3 | 1.000 | 1.000 | 1.000 | 4434 |
| native-18 | P1_to_P2 | reduction | cyclic_carbonate | 4 | 1.000 | 1.000 | 1.000 | 4910 |
| native-18 | P1_to_P2 | reduction | ester | 3 | 1.000 | 1.000 | 1.000 | 4427 |
| native-18 | P1_to_P2 | reduction | ether | 3 | -0.333 | -1.000 | 1.000 | 4485 |
| native-18 | P1_to_P2 | reduction | linear_carbonate | 3 | 1.000 | 1.000 | 1.000 | 4437 |

> CI 由对该家族 n 个分子**有放回重抽样**得到；n 只有 3-4，区间很宽且不稳定，仅供参考，不得读作显著。

## 5. family-resolved：家族内 f_unresolved

单元格为 `f_unresolved(after, z=1.0)`（冻结口径）；n < 2 时无 pair，记 `--`。

### native-18

| 台阶 | 轴 | cyclic_carbonate | ester | ether | linear_carbonate | nitrile | phosphate | sulfone | sulfoxide |
|---|---|---|---|---|---|---|---|---|---|
| P0_to_P1 | oxidation | 0.000 (n=4) | 0.333 (n=3) | 0.000 (n=3) | 0.000 (n=3) | 1.000 (n=2) | -- | -- | -- |
| P0_to_P1 | reduction | 0.167 (n=4) | 0.333 (n=3) | 0.333 (n=3) | 0.667 (n=3) | 0.000 (n=2) | -- | -- | -- |
| P1_to_P2 | oxidation | 0.167 (n=4) | 0.333 (n=3) | 0.667 (n=3) | 0.000 (n=3) | 1.000 (n=2) | -- | -- | -- |
| P1_to_P2 | reduction | 0.000 (n=4) | 0.000 (n=3) | 1.000 (n=3) | 0.000 (n=3) | 0.000 (n=2) | -- | -- | -- |
| G1_to_G2 | oxidation | 0.000 (n=2) | -- | 0.000 (n=2) | 0.000 (n=2) | 0.000 (n=2) | -- | -- | -- |
| G1_to_G2 | reduction | 0.000 (n=2) | -- | 0.000 (n=2) | 1.000 (n=2) | 0.000 (n=2) | -- | -- | -- |
| C0_to_C1 | oxidation | -- | -- | 0.000 (n=2) | -- | 0.000 (n=2) | -- | -- | -- |
| C0_to_C1 | reduction | -- | -- | 1.000 (n=2) | -- | 1.000 (n=2) | -- | -- | -- |
| C1_to_C2 | oxidation | -- | -- | 0.000 (n=2) | -- | 0.000 (n=2) | -- | -- | -- |
| C1_to_C2 | reduction | -- | -- | 0.000 (n=2) | -- | 1.000 (n=2) | -- | -- | -- |

### common-10

| 台阶 | 轴 | cyclic_carbonate | ester | ether | linear_carbonate | nitrile | phosphate | sulfone | sulfoxide |
|---|---|---|---|---|---|---|---|---|---|
| P0_to_P1 | oxidation | -- | -- | 0.000 (n=2) | -- | 1.000 (n=2) | -- | -- | -- |
| P0_to_P1 | reduction | -- | -- | 1.000 (n=2) | -- | 0.000 (n=2) | -- | -- | -- |
| P1_to_P2 | oxidation | -- | -- | 1.000 (n=2) | -- | 1.000 (n=2) | -- | -- | -- |
| P1_to_P2 | reduction | -- | -- | 1.000 (n=2) | -- | 0.000 (n=2) | -- | -- | -- |
| G1_to_G2 | oxidation | -- | -- | 0.000 (n=2) | -- | 0.000 (n=2) | -- | -- | -- |
| G1_to_G2 | reduction | -- | -- | 0.000 (n=2) | -- | 0.000 (n=2) | -- | -- | -- |
| C0_to_C1 | oxidation | -- | -- | 0.000 (n=2) | -- | 0.000 (n=2) | -- | -- | -- |
| C0_to_C1 | reduction | -- | -- | 1.000 (n=2) | -- | 1.000 (n=2) | -- | -- | -- |
| C1_to_C2 | oxidation | -- | -- | 0.000 (n=2) | -- | 0.000 (n=2) | -- | -- | -- |
| C1_to_C2 | reduction | -- | -- | 0.000 (n=2) | -- | 1.000 (n=2) | -- | -- | -- |

## 6. cross-family：家族平均位移之间的 Kendall τ_b（8 家族）

主定义：同一 (population, 台阶) 下，8 个家族各给一个氧化轴平均位移与一个还原轴平均位移，τ_b 比较这两个长度 8 的家族向量。

| population | 台阶 | n_家族 | τ_b(ox vs red) | CI95 low | CI95 high |
|---|---|---|---|---|---|
| native-18 | P0_to_P1 | 8 | 0.286 | -0.455 | 0.917 |
| native-18 | P1_to_P2 | 8 | 0.071 | -0.579 | 0.750 |
| native-18 | G1_to_G2 | 8 | 0.143 | -0.417 | 0.760 |
| native-18 | C0_to_C1 | 8 | -0.143 | -0.833 | 0.583 |
| native-18 | C1_to_C2 | 8 | 0.286 | -0.304 | 0.810 |
| common-10 | P0_to_P1 | 8 | 0.429 | -0.217 | 0.920 |
| common-10 | P1_to_P2 | 8 | 0.357 | -0.217 | 0.889 |
| common-10 | G1_to_G2 | 8 | 0.071 | -0.500 | 0.714 |
| common-10 | C0_to_C1 | 8 | -0.143 | -1.000 | 0.583 |
| common-10 | C1_to_C2 | 8 | 0.286 | -0.263 | 0.826 |

辅助定义：同一 (population, 台阶, 轴) 下，家族平均 before 与家族平均 after 之间的 τ_b（家族级排序是否被该台阶保留）。

| population | 台阶 | 轴 | τ_b(mean before vs after) |
|---|---|---|---|
| native-18 | P0_to_P1 | oxidation | 0.714 |
| native-18 | P0_to_P1 | reduction | 0.643 |
| native-18 | P1_to_P2 | oxidation | 0.786 |
| native-18 | P1_to_P2 | reduction | 0.714 |
| native-18 | G1_to_G2 | oxidation | 0.929 |
| native-18 | G1_to_G2 | reduction | 0.929 |
| native-18 | C0_to_C1 | oxidation | 0.786 |
| native-18 | C0_to_C1 | reduction | -0.500 |
| native-18 | C1_to_C2 | oxidation | 0.786 |
| native-18 | C1_to_C2 | reduction | 0.214 |
| common-10 | P0_to_P1 | oxidation | 0.786 |
| common-10 | P0_to_P1 | reduction | 0.571 |
| common-10 | P1_to_P2 | oxidation | 0.857 |
| common-10 | P1_to_P2 | reduction | 0.929 |
| common-10 | G1_to_G2 | oxidation | 0.929 |
| common-10 | G1_to_G2 | reduction | 0.857 |
| common-10 | C0_to_C1 | oxidation | 0.786 |
| common-10 | C0_to_C1 | reduction | -0.500 |
| common-10 | C1_to_C2 | oxidation | 0.786 |
| common-10 | C1_to_C2 | reduction | 0.214 |

## 7. 诚实边界（写死在本文件与 json 中）

- 单分子 family（sulfone=SL、sulfoxide=DMSO、phosphate=TMP）无法做家族内排序：家族内 tau_b 一律 not_estimable，只能进入 cross-family 统计（家族平均位移）。
- n = 2 的 family（nitrile=AN/SN）家族内只有 1 对分子，tau_b 无统计意义，记 not_estimable；其 1 对的 f_unresolved 与位移统计仍照报。
- 所有 CI 均为「对分子有放回重抽样」的小样本 bootstrap 区间（draws=5000, seed=20261002）；n = 3-4 时区间很宽且不稳定，只能作参考，不得表述为「显著」。
- 两个 population（native-18 与 common-10）的 n 不同，本文件全程分别报告，绝不合并。
- common-10 中每个 family 的分子数都 <= 2，因此 common-10 的家族内 tau_b 全部 not_estimable；这正是 v2 §13.3 所说的统计边界。
- f_unresolved 沿用冻结的 pair tolerance 口径（ranking.resolved_mask，threshold = max(z*sigma, delta)，z = 1.0 冻结于 config/prereg.yaml）；既有 stage10 产物未施加 delta_m（tolerance = 0.0 eV），本文件保持一致，并另报 z = 1.96 敏感性列。
- 本分析不改变任何既有判决：不重算、不覆盖 outputs/week9、outputs/week4、outputs/week5、outputs/week8 的任何数字，也不改判 stage10 的 v2 §22 情形结论。

## 8. 复现命令

```powershell
.venv\Scripts\python.exe scripts\analyze_family_resolved.py
.venv\Scripts\python.exe scripts\analyze_family_resolved.py --check
.venv\Scripts\python.exe scripts\analyze_w25_figure_f53.py
.venv\Scripts\python.exe scripts\analyze_w25_figure_f53.py --check
```

