# Week 7 成果小结 —— Stage 7（ML / direct vs Δ-learning）+ Stage 8（active-learning replay）

本周把 Stage 2–5 的产物整理成带 **cost 分级** 的特征表，然后在同一条模型阶梯上比较
**直接学习目标层** 与 **只学位移（Δ-learning）** 两种形态，并且强制报告三种拆分
（random / group / leave-one-family-out）。随后用 retrospective replay 回答
「要买多少次昂贵计算才恢复目标排序」。本文可独立阅读；逐项细节见同目录
`week7_report_full.md`。

## 1. 本周做了什么
用 `scripts/build_ml_features.py` 把 Stage 2–5 的产物整理成带 **cost 分级** 的特征表（`X0` 12 列 / `X1` 6 列 / `X2` 4 列，互斥；`X2` 只许做机制解释），再用 `scripts/run_stage7_ml.py` 在 `constant / ridge / krr / gpr / rf / gbdt` 六级模型阶梯上、对 `M`（方法 P0→P1）、`E`（环境 P1→P2）、`C`（配位 C0→C1）三种位移各自跑 **direct** 与 **conditional-shift** 两种学习形态，三种拆分（random / group / leave-one-family-out）全报告；每个 replicate 的随机种子由 `sha256` 派生，跨进程可复现。`scripts/run_stage8_al.py` 再做 retrospective active-learning replay（初始 4 个种子、每次买 1 个标签、20 组冻结种子重复），给出 `n_T -> τ_b / O_k / R_k`。

## 2. 关键数字
- Stage 7 结果行 **288** 条（task × feature set × objective × split × shape × model）；估计器抛异常而回落到家族均值的折数 **0**。
- LOFO 下 **shift** 形态胜过 direct 的组合数：**6 / 8**。

## 3. Stage 7：特征表与三种拆分下的模型阶梯
| 任务 · 特征集 · 轴 | LOFO 最佳 direct | LOFO 最佳 shift | shift − direct | 同组合 random τ_b |
| --- | --- | --- | --- | --- |
| M · X0 · oxidation | `krr` 0.294 | `constant` 0.595 | +0.301 | 0.752 |
| M · X0 · reduction | `rf` 0.359 | `constant` 0.556 | +0.196 | 0.595 |
| E · X0+P1 · oxidation | `ridge` 0.843 | `rf` 0.922 | +0.078 | 0.948 |
| E · X0+P1 · reduction | `rf` 0.686 | `krr` 0.739 | +0.052 | 0.725 |
| C · X0 · oxidation | `krr` 0.111 | `krr` 0.644 | +0.533 | 0.733 |
| C · X0 · reduction | `gbdt` 0.422 | `krr` 0.022 | -0.400 | 0.156 |
| C · X0+X1 · oxidation | `ridge` 0.244 | `rf` 0.644 | +0.400 | 0.689 |
| C · X0+X1 · reduction | `gbdt` 0.289 | `ridge` 0.200 | -0.089 | 0.200 |

## 4. Stage 8：`n_T -> tau_b / O_k / R_k`
| 任务 · 轴 | 池 n | `random` | `diversity` | `uncertainty` | `ranking_aware` |
| --- | --- | --- | --- | --- | --- |
| C · oxidation | 10 | 0.844（≥0.8 @ 9） | 0.956（≥0.8 @ 8） | 0.956（≥0.8 @ 8） | 0.867（≥0.8 @ 9） |
| C · reduction | 10 | 0.867（≥0.8 @ 9） | 0.956（≥0.8 @ 9） | 0.956（≥0.8 @ 9） | 0.844（≥0.8 @ 9） |
| E · oxidation | 18 | 0.974（≥0.8 @ 15） | 0.974（≥0.8 @ 14） | 1.000（≥0.8 @ 12） | 0.987（≥0.8 @ 13） |
| E · reduction | 18 | 0.961（≥0.8 @ 14） | 0.961（≥0.8 @ 13） | 0.961（≥0.8 @ 13） | 0.974（≥0.8 @ 13） |
| M · oxidation | 18 | 0.987（≥0.8 @ 13） | 1.000（≥0.8 @ 13） | 0.987（≥0.8 @ 12） | 0.987（≥0.8 @ 13） |
| M · reduction | 18 | 0.967（≥0.8 @ 13） | 0.974（≥0.8 @ 13） | 0.974（≥0.8 @ 13） | 0.987（≥0.8 @ 13） |

## 5. 质量与复核（QC）
- X2（配位衍生特征）由运行期断言拒绝，任何特征集都不可能含 X2；三种拆分的折覆盖经单元测试验证「每个分子恰好被预测一次」；`render_summary` / `week7_blocks` 的所有数字都从 JSON 现场解析。 Stage 8 的 acquisition 只用 `X0`，每轮的标准化与模型拟合只看到当轮可见标签（由单元测试断言 scaler 均值等于可见行均值）。
- 上述每一项都由本目录 `verification.json` 的 `checks` 数组从真实产物现场解析得出。

## 6. 产物清单
- `artifacts/F16_stage7_direct_vs_shift.png`
- `artifacts/F17_stage8_active_learning.png`
- `artifacts/figure_manifest_week7_s7s8.md`
- `feature_manifest.json`
- `feature_manifest.md`
- `features_broad.csv`
- `features_core.csv`
- `reading_list_qa.md`
- `stage7_ml_predictions.csv`
- `stage7_ml_results.csv`
- `stage7_ml_results.json`
- `stage7_ml_summary.md`
- `stage8_al_curves.csv`
- `stage8_al_results.json`
- `stage8_al_runs.csv`
- `stage8_al_summary.md`
- `stage8_al_trajectories.csv`
- `week7_report_full.md`

## 7. 已知限制
1. core set 只有 18 个分子（配位任务 `C` 只有 10 个），group / LOFO 折内训练行数常低至个位数；本报告只能支持**方法学**结论，不能当作定量精度结论。
2. **配位任务 `C` 的样本只有 10 个**，其 LOFO 折等价于单点外推，只能读方向不能读幅度。
3. Gate 0 保持 CLOSED；Gate 1 仍未关闭（溶液相锚点 31 行仍为 `est`），本周边界结论只依赖气相锚点。
4. Stage 8 的 acquisition 只用 `X0`；`X2` 特征被运行期断言拒绝，只许出现在机制解释里。
5. Week 6 的遗留项（`delta_m` 是否 append 进 `config/prereg.yaml`）仍待 PI 裁决。
6. 逐项细节见同目录 `week7_report_full.md` 与 `reading_list_qa.md`。

## 8. 源文件缺失
- 无（全部源路径均存在）
