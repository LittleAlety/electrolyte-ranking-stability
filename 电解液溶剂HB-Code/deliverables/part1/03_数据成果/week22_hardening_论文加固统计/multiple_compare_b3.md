# B3 — 多重比较：Stage 11 可预测性表（Bonferroni 与 Holm）

> 本文档由 `scripts/analyze_w22_allowance.py` 从 `outputs/week10/stage11_sigma_anatomy.json` 渲染。
> **只读复核，不改动冻结量。**

## 0. 一句话结论

先验 predictor 个数 `n = 9`，Bonferroni 阈值 `alpha = 0.05 / 9 = 0.005556`。
逐条 p 都 **大于** 该阈值，Bonferroni 下 **0 条显著**；Holm 步降在第一步即失败，
同样是 **0 条显著**。因此 signed-slope（`ols_slope_b`，`p = 0.00833`）**不存活**。

## 1. 输入

- 目标规则：`shortlist_rewritten`
- 目标定义：top-20% overlap before vs after < 1, i.e. the two-slot shortlist changed
- 样本：n_points = 10，n_positives = 3
- predictor 个数（表内条数）：**n = 9**
- 显著性水平：alpha = 0.05；Bonferroni 阈值 = alpha / n = **0.005556**

## 2. Bonferroni

| predictor | AUC | p (精确置换) | p×n（校正后） | p < 0.05/n ? |
| --- | --- | --- | --- | --- |
| ols_slope_b | 1.0000 | 0.008333 | 0.0750 | **否** |
| sigma2_share_parallel | 1.0000 | 0.008333 | 0.0750 | **否** |
| abs_ols_slope_b | 0.9048 | 0.033333 | 0.3000 | **否** |
| rank_damage_1_minus_tau | 0.9048 | 0.033333 | 0.3000 | **否** |
| q_median | 0.8571 | 0.058333 | 0.5250 | **否** |
| sigma_rms_ev | 0.8095 | 0.091667 | 0.8250 | **否** |
| f_unresolved_p1_observed | 0.8095 | 0.091667 | 0.8250 | **否** |
| q_p90 | 0.7619 | 0.133333 | 1.0000 | **否** |
| sigma2_share_residual | 0.0000 | 1.000000 | 1.0000 | **否** |

Bonferroni 显著条数：**0**。

## 3. Holm（步降）

Holm：按 p 升序，第 k 个（k=1..n）与 `alpha / (n - k + 1)` 比较；一旦某步不通过即停止。

| k | predictor | p | Holm 阈值 alpha/(n-k+1) | Holm 校正后 p | 显著 ? |
| --- | --- | --- | --- | --- | --- |
| 1 | ols_slope_b | 0.008333 | 0.005556 | 0.0750 | **否** |
| 2 | sigma2_share_parallel | 0.008333 | 0.006250 | 0.0750 | **否** |
| 3 | abs_ols_slope_b | 0.033333 | 0.007143 | 0.2333 | **否** |
| 4 | rank_damage_1_minus_tau | 0.033333 | 0.008333 | 0.2333 | **否** |
| 5 | q_median | 0.058333 | 0.010000 | 0.2917 | **否** |
| 6 | sigma_rms_ev | 0.091667 | 0.012500 | 0.3667 | **否** |
| 7 | f_unresolved_p1_observed | 0.091667 | 0.016667 | 0.3667 | **否** |
| 8 | q_p90 | 0.133333 | 0.025000 | 0.3667 | **否** |
| 9 | sigma2_share_residual | 1.000000 | 0.050000 | 1.0000 | **否** |

Holm 显著条数：**0**。

## 4. signed-slope（`ols_slope_b`）判读

| 项 | 值 |
| --- | --- |
| predictor | `ols_slope_b` |
| AUC | 1.0000 |
| p | 0.008333 |
| Bonferroni 阈值 | 0.005556 |
| Bonferroni 校正后 p | 0.0750 |
| Bonferroni 显著 | **否** |
| Holm 名次 k | 1 |
| Holm 阈值 | 0.005556 |
| Holm 校正后 p | 0.0750 |
| Holm 显著 | **否** |

**判断：`ols_slope_b` 的 p = 0.00833 在 Bonferroni 与 Holm 两口径下都不存活。**
其最小可能原始 p 受精确置换分辨率限制（n = 10 点时最小 p = 0.008333），
本身已高于 Bonferroni 阈值 0.005556，故不可能在族错误率控制下存活。

---

生成时间（UTC）：2026-10-02T06:43:18.328167+00:00
