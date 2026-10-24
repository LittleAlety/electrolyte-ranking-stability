# Week 29 / WP2：哪些电子结构与介质物理改变候选排序

> 阶段：下一阶段（评审实施方案）WP2（RQ1）。产物目录 `outputs/week29/`，交付镜像
> `..\成果输出（part2）\week29/`。本文件由手工撰写，数字由
> `scripts/build_week29_wp2_physics_response.py` 确定性生成并 `--check` 逐字节复核。
> **零新增电子结构计算**：唯一输入是 Week 28 冻结主表。

## 0. 本轮解决的问题

Week 28（WP1）把 Week 1–27 的物理量、状态身份、排序指标与成本收敛成一张版本冻结的主表，
并逐位复现了 Week 6 的 354 个 stored pair。WP2 用这张主表回答 RQ1：

> 从极廉价代理量 `P0` 到电子结构 `P1v`/`P1a`，再到固定连续介质 `P2a`，哪些模型变化会
> **改变候选排序**？变化发生在哪些候选上，是否超出原始数据的分辨能力？

## 1. 口径与输入

- 唯一输入：`outputs/week28/{property,pairwise,decision}_table.csv` 与 `molecule_registry.csv`。
- 对比集合（Axis-A 阶梯）：`P0_to_P1v`、`P1v_to_P1a`、`P1v_to_P2a`、`P1v_to_P2eps10`、`P0_to_P2a`。
  C0/C1/C2（环境条件态）属于 WP3，不在本轮。
- 恒等式：`delta_i(A->B) = P_B(i) - P_A(i)`，于是 `dP_ij^B = dP_ij^A + (delta_i - delta_j)`。
  排序变化只由**候选间的差异性响应** `delta_i - delta_j` 驱动；共同偏移不改变排序。
- 统计口径复用 `electrolyte_ranking.ranking`（`kendall_tau_b` / `spearman_rho` /
  `top_k_overlap` / `jaccard_at_k` / `selection_regret`），`k = round(k_fraction * n)`。

## 2. 结果

### 2.1 逐级位移与家族分层

`delta_i` 的分子级汇总（eV），以及三种解释模型的残差：

| 对比 | 轴 | n | RMSE 共模 | RMSE 家族偏移 | RMSE 分子校正 | 族效应占比 |
| --- | --- | --- | --- | --- | --- | --- |
| P0_to_P1v | oxidation | 18 | 1.0397 | 0.4424 | ~0 | 0.8190 |
| P0_to_P1v | reduction | 18 | 3.1237 | 0.3848 | ~0 | 0.9848 |
| P1v_to_P1a | oxidation | 12 | 0.3051 | 0.1853 | ~0 | 0.6309 |
| P1v_to_P2a | oxidation | 18 | 0.4269 | 0.2860 | ~0 | 0.5511 |
| P1v_to_P2a | reduction | 18 | 0.4532 | 0.3585 | ~0 | 0.3745 |
| P1v_to_P2eps10 | oxidation | 12 | 0.3139 | 0.1507 | ~0 | 0.7697 |
| P1v_to_P2eps10 | reduction | 12 | 0.3440 | 0.1862 | ~0 | 0.7070 |
| P0_to_P2a | oxidation | 18 | 0.8486 | 0.2830 | ~0 | 0.8888 |
| P0_to_P2a | reduction | 18 | 2.9951 | 0.3184 | ~0 | 0.9887 |

「族效应占比」= `SS_between_family / SS_total`（`delta_i` 的族间方差占比）。在无序完全对
（每个分子与其余 n-1 个成对）下它与 `R2_family_vs_common` 恒等 —— 这是一条代数事实，
本阶段用 `family_variance_identity` 断言把它钉住。

关键读数：

- **还原轴 `P0->P1v` 的族效应占比 0.985**：跨家族位移均值 2.43 eV，家族内只有 0.34 eV。
  廉价代理量在这个轴上的误差基本是**家族级**的，家族偏移模型把 RMSE 从 3.12 压到 0.38。
- 氧化轴 `P0->P1v` 的族效应占比 0.819；介质层 `P1v->P2a` 只有 0.55（氧化）/ 0.37（还原），
  更偏**分子级**差异。

### 2.2 排序响应与候选交换（k/N = 20%）

| 对比 | 轴 | k | O_k | J_k | regret (eV) | tau_b | 进入 | 退出 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P0_to_P1v | oxidation | 4 | 0.500 | 0.333 | 0.6563 | 0.673 | AN;SN | DMC;PC |
| P0_to_P1v | reduction | 4 | 0.500 | 0.333 | 0.2630 | 0.595 | DEC;DMC | TEGDME;TMP |
| P1v_to_P1a | oxidation | 2 | 1.000 | 1.000 | 0.0000 | 0.788 | - | - |
| P1v_to_P2a | oxidation | 4 | 0.750 | 0.600 | 0.0272 | 0.895 | DMC | EC |
| P1v_to_P2a | reduction | 4 | 0.500 | 0.333 | 0.1752 | 0.673 | SL;TEGDME | DEC;DMC |
| P1v_to_P2eps10 | oxidation | 2 | 1.000 | 1.000 | 0.0000 | 0.909 | - | - |
| P1v_to_P2eps10 | reduction | 2 | 1.000 | 1.000 | 0.0000 | 0.848 | - | - |
| P0_to_P2a | oxidation | 4 | 0.500 | 0.333 | 0.5448 | 0.673 | AN;SN | EC;PC |
| P0_to_P2a | reduction | 4 | 0.750 | 0.600 | 0.0445 | 0.791 | SL | TMP |

读法：

1. **廉价代理量 `P0->P1v` 是选择变化的主要来源**（氧化 Top-20% overlap 0.5；`AN/SN` 顶掉
   `DMC/PC`，regret 0.656 eV）。
2. **固定连续介质 `P1v->P2a` 带来中等改变**（氧化 overlap 0.75，仅 `DMC`/`EC` 互换，regret 0.027 eV）。
3. **同方法内两个 rung 不改变 Top-k 选择**：垂直/绝热 `P1v->P1a` 与裸介电 `P1v->P2eps10` 在
   12 分子审计集上 overlap = 1.000。它们改变了数值，但没有改变**选择**；其位移以家族级
   共同偏移为主（族效应占比 0.63–0.77），被家族偏移吸收后残差很小。

### 2.3 分辨率约束

小样本下必须与分辨率一起读。`decision_response.csv` 给出每组的 `f_unresolved_lower/upper`
与 `swapped_pairs_resolved_both`（k=20% 的 entries×leaves 交换对里，两侧都通过门槛的个数）。
注意：WP2 的 5 个对比里 `ROBUST_INVERSION` 恒为 0，且这是**结构性**的（`z = 1.0 > 1/√2`
时反向 pair 不可能两侧同时过门槛），不得读成「排序稳定」。

### 2.4 阶梯信息增量与 bootstrap

- `ladder_incremental.csv`：以终端模型 `P2a` 为参考，逐级报告各 rung 的 Top-k overlap 与
  marginal 改善。氧化轴上 `P0` 相对 `P2a` 只有 0.5，`P1v` 到 0.75，`P2a` 到 1.0。
- `bootstrap_ci.csv`：以**分子**为单元有放回重采样（B=2000, seed=0）给出 `tau_b` / `rho` /
  Top-20% overlap 的 95% 区间。例如 `P0_to_P1v` 氧化 `tau_b` 点估计 0.673、区间约
  [0.36, 0.90]，说明 18 分子样本下全局排序关系本身也有不可忽略的抽样不确定性。
  区间用仓库自己的 `ranking.kendall_tau_b`（并列按 atol 处理），与 scipy 默认在无并列时一致。

## 3. 一致性自检（7 项，全部 PASS）

| id | 检查 | 关键数字 |
| --- | --- | --- |
| `displacement_reproduces_pairwise_shift` | `delta_i - delta_j` 是否等于主表 `delta_shift_ev` | 最大绝对误差 1.33e-15 eV，1116 个 pair 行 |
| `decision_metrics_match_week28` | 重算 Top-k/Jaccard/regret/tau/rho 是否复现 Week 28 | 最大绝对差 **0.000e+00**（5 个指标全 0） |
| `molecule_model_is_exact` | 分子级校正残差是否为 0 | 最大 RMSE 5.95e-16 eV |
| `family_variance_identity` | `SS_between + SS_within = SS_total` 且 `R2_family ≡ 族效应占比` | 偏差 0 / 3.33e-16 |
| `ladder_additivity_exact` | `delta(P0->P2a) = delta(P0->P1v) + delta(P1v->P2a)` | 最大绝对误差 8.88e-16 eV |
| `p1a_reduction_is_rule_excluded` | `P1v_to_P1a` 还原轴是否按 `unbound_anion` 排除 | 0 行 |
| `zero_new_electronic_structure` | 是否只用 Week 28 主表、零新增作业 | 4 个输入文件，0 个新作业 |

`decision_metrics_match_week28` 的零误差说明：WP2 不是并行于 Week 28 的另一套定义，而是
在同一个对象上补物理机制。

## 4. 结论的三层表述

- **模型事实**：`P0->P1v` 与 `P1v->P2a` 改变 core18 的 Top-k 选择；`P1v->P1a` 与
  `P1v->P2eps10` 在审计集上不改变 Top-k 选择。
- **统计判定**：氧化轴 `P0->P1v` 的 `tau_b` 点估计 0.673、bootstrap 95% 区间远离 1，
  说明「廉价代理量足以定序」在这些家族上不成立；但 `f_unresolved` 提示逐 pair 的符号
  多数证据不足，不能反过来说「已证明重排」。
- **材料意义**：廉价代理量对**还原轴**的误差是家族级的（族效应占比 0.985），意味着按家族
  校正后可低成本恢复大部分决策信息 —— 这正是 WP5/WP6 要检验的假设。以上均限于
  designated computational target；Gate 1 仍 NOT CLOSED，不构成外部有效性证据。

## 5. 限制

- 零新增计算；P1a 只有 12 分子且只有氧化轴，`P1v->P1a`/`P1v->P2eps10` 的选择稳定性只在
  该审计集上成立，不能外推到 core18。
- `scope='all'` 的 n 随对比变化（18/12），跨行不可比；每行请看 `common_set_label`。
- bootstrap 以分子为单元，n=18/12 很小，区间本身较宽。

## 6. 交给 WP3/WP4 的接口

- **WP3**：`displacement_table` 的分子级 `delta_i` 与 `family_displacement` 的家族结构，可直接
  与 C0/C1/C2 的条件响应对照；`P1v->P2a` 偏分子级差异这一事实，是 WP3 机制案例的入口。
- **WP4**：`decision_response` 的 overlap/Jaccard/regret 与 `swapped_pairs_resolved_both`
  给出「哪些交换是统计上可识别的」，接上 `pairwise_table` 的分辨率列即可做决策可识别性。

## 7. 交付层

镜像写入 `..\成果输出（part2）\week29\`（保持仓库相对路径，附 `SHA256SUMS`、
`verification.json`、中文 `README.md`），并更新 `成果输出（part2）/README.md` 索引。

## 8. 复现命令

```powershell
.venv\Scripts\python.exe scripts\build_week29_wp2_physics_response.py
.venv\Scripts\python.exe scripts\build_week29_wp2_physics_response.py --check
.venv\Scripts\python.exe -m pytest tests/test_week29_wp2_physics_response.py -q
.venv\Scripts\python.exe scripts\build_week29_deliverables.py
.venv\Scripts\python.exe scripts\build_week29_deliverables.py --check
```
