# R15 — selection / multiplicity audit（对抗审计第 3 轮 · C 项）

> 本文档由 `scripts/audit_selection_multiplicity.py` 从冻结产物现算。
> **只读：不重算任何科学量，只清点与分类。**

## 0. 一句话结论

分析空间被完整清点并分类：**确认性端点由 `config/prereg.yaml` 写成，探索性比较全部登记**，
唯一产生过「筛选声明」的家族（Stage 11 的 9 个 predictor）带 Bonferroni 与 Holm 校正且
**0 条存活**；决策阈值按预注册规则报 `not_applicable`、任何产物里都没有用数据分位数顶替；
所有 `post_hoc` 量都写在自己的键名里、只当上界用。

判定：**PASS**。

## 1. 预注册口径（确认性）

- 文件：`config/prereg.yaml`（sha256 `43c269611d108bef`）
- 冻结日期：2026-09-29
- 必须报告的端点：

  - Kendall tau_b (含 unresolved 处理)
  - f_unresolved
  - f_robust_inv
  - Top-k overlap 与 Jaccard (k = 10% / 20% / 30%)
  - selection regret
  - median + 95% CI over seeds

- 冻结的禁止声明：

  - 把 S_ox / S_red 简写为真实电化学稳定窗口
  - 在未报告 unresolved fraction 的情况下宣称排序稳定
  - 使用接近目标层成本的 feature 去证明'低成本预测'

- 阈值来源规则：T 只能来自 (a) 外部设计要求, (b) 实验基准, 或 (c) 事先定义的工程标准; 且必须在看到 target-vs-proxy 排序结果之前写定并记录出处。
- 无合规来源时：若无合规来源, 该项报告为 not_applicable, 不得用数据分位数临时替代

## 2. 比较空间清点

| 量 | 值 |
| --- | --- |
| 带 p 值的产物文件 | 6 |
| p 值单元总数 | 86 |
| 带区间（CI）的产物文件 | 10 |
| 区间单元总数 | 14758 |

报告矩阵（预注册要求的逐 k / 逐拆分报告，非假设检验）：

| 家族 | 行数 |
| --- | --- |
| Stage 7 ML 矩阵（3 拆分 × 6 模型 × 2 形状 × k） | 288 |
| Stage 8 active-learning 曲线 | 296 |
| Stage 10 ladder 组合 | 20 |
| Stage 24 family-resolved 公共子集 | 10 |

## 3. 带 p 值的家族与校正状态

| 文件 | 家族 | 分类 | 校正 | p 单元 | 校正结果 |
| --- | --- | --- | --- | ---: | --- |
| `outputs/week10/stage11_sigma_anatomy.json` | Stage 11 predictability table (9 predictors screening shortlist_rewritten) | exploratory | bonferroni+holm | 9 | Bonferroni 存活 0 / Holm 存活 0（n = 9） |
| `outputs/week22_hardening/multiple_compare_b3.json` | B3 family-wise control for the Stage 11 table | control_layer | bonferroni+holm | 20 | 未校正（探索性） |
| `outputs/week15/stage16_predictor.json` | Stage 16 gas-phase descriptor screen (11 descriptors, discovery/validation split) | exploratory | none | 37 | 未校正（探索性） |
| `outputs/week17/stage18_selfdiagnosis.json` | Stage 18 contamination self-diagnosis | exploratory | none | 14 | 未校正（探索性） |
| `outputs/week4/p1_anchor_comparison.json` | Stage 3 P1 anchor comparison (permutation test) | exploratory | none | 4 | 未校正（探索性） |
| `outputs/week25/gate1_oxidation.json` | Gate 1 oxidation-axis exact permutation endpoint (single preregistered endpoint) | confirmatory | single-endpoint | 2 | 单端点，无需族校正 |

## 4. 决策阈值选择（预注册禁止事后挑阈值）

- 状态：**not_applicable**（合规：True）
- 产物中的 `threshold_decision_error` 键：36 个（其中数值型 0 个）
- 依据：docs/41_week25_corefile_gap_audit.md (F7): no compliant source exists, so E_decision is reported as not_applicable and never replaced by a data quantile

## 5. 事后量（只允许当上界）

| 文件 | 键 | 值 |
| --- | --- | --- |
| `outputs/week15/stage16_predictor.json` | `post_hoc` | True |
| `outputs/week17/stage18_selfdiagnosis.json` | `best_abs_auc_above_half_in_state_post_hoc` | 0.0 |
| `outputs/week17/stage18_selfdiagnosis.json` | `best_abs_auc_above_half_in_state_post_hoc` | 0.43870192307692313 |
| `outputs/week17/stage18_selfdiagnosis.json` | `best_abs_auc_above_half_in_state_post_hoc` | 0.4110576923076923 |
| `outputs/week17/stage18_selfdiagnosis.json` | `best_abs_auc_above_half_in_state_post_hoc` | 0.3674879807692308 |
| `outputs/week17/stage18_selfdiagnosis.json` | `best_feature_in_state_post_hoc` | scf_n_cycles |
| `outputs/week17/stage18_selfdiagnosis.json` | `best_feature_in_state_post_hoc` | loewdin_spin_n90 |
| `outputs/week17/stage18_selfdiagnosis.json` | `best_feature_in_state_post_hoc` | scf_final_diiserr |
| `outputs/week17/stage18_selfdiagnosis.json` | `best_feature_in_state_post_hoc` | gap_warn_value |
| `outputs/week17/stage18_selfdiagnosis.json` | `holdout_accuracy_post_hoc` | 0.7962962962962963 |
| `outputs/week17/stage18_selfdiagnosis.json` | `holdout_accuracy_post_hoc` | 0.8333333333333334 |
| `outputs/week17/stage18_selfdiagnosis.json` | `holdout_accuracy_post_hoc` | 0.7777777777777778 |
| `outputs/week17/stage18_selfdiagnosis.json` | `holdout_accuracy_post_hoc` | 0.9074074074074074 |
| `outputs/week17/stage18_selfdiagnosis.json` | `holdout_accuracy_post_hoc` | 0.8333333333333334 |
| `outputs/week17/stage18_selfdiagnosis.json` | `holdout_accuracy_post_hoc` | 0.7777777777777778 |
| `outputs/week17/stage18_selfdiagnosis.json` | `holdout_accuracy_post_hoc` | 0.9444444444444444 |
| `outputs/week17/stage18_selfdiagnosis.json` | `holdout_accuracy_post_hoc` | 0.42592592592592593 |
| `outputs/week17/stage18_selfdiagnosis.json` | `holdout_accuracy_post_hoc` | 0.9074074074074074 |
| `outputs/week17/stage18_selfdiagnosis.json` | `holdout_accuracy_post_hoc` | 0.9074074074074074 |
| `outputs/week17/stage18_selfdiagnosis.json` | `holdout_accuracy_post_hoc` | 0.9259259259259259 |
| `outputs/week17/stage18_selfdiagnosis.json` | `holdout_accuracy_post_hoc` | 0.9259259259259259 |
| `outputs/week17/stage18_selfdiagnosis.json` | `holdout_accuracy_post_hoc` | 0.9444444444444444 |
| `outputs/week17/stage18_selfdiagnosis.json` | `holdout_accuracy_post_hoc` | 0.7962962962962963 |
| `outputs/week17/stage18_selfdiagnosis.json` | `holdout_accuracy_post_hoc` | 0.8703703703703703 |
| `outputs/week17/stage18_selfdiagnosis.json` | `holdout_accuracy_post_hoc` | 0.9074074074074074 |
| `outputs/week17/stage18_selfdiagnosis.json` | `holdout_accuracy_post_hoc` | 0.8888888888888888 |
| `outputs/week17/stage18_selfdiagnosis.json` | `holdout_accuracy_post_hoc` | 0.9074074074074074 |
| `outputs/week17/stage18_selfdiagnosis.json` | `holdout_accuracy_post_hoc` | 0.9074074074074074 |
| `outputs/week17/stage18_selfdiagnosis.json` | `holdout_accuracy_post_hoc` | 0.8888888888888888 |
| `outputs/week17/stage18_selfdiagnosis.json` | `holdout_accuracy_post_hoc` | 0.8888888888888888 |
| `outputs/week17/stage18_selfdiagnosis.json` | `holdout_accuracy_post_hoc` | 0.48148148148148145 |
| `outputs/week17/stage18_selfdiagnosis.json` | `holdout_accuracy_post_hoc` | 0.9259259259259259 |
| `outputs/week17/stage18_selfdiagnosis.json` | `holdout_accuracy_post_hoc` | 0.9259259259259259 |
| `outputs/week17/stage18_selfdiagnosis.json` | `holdout_accuracy_post_hoc` | 0.8703703703703703 |
| `outputs/week17/stage18_selfdiagnosis.json` | `holdout_majority_accuracy_post_hoc` | 0.9074074074074074 |
| `outputs/week17/stage18_selfdiagnosis.json` | `holdout_majority_accuracy_post_hoc` | 0.9074074074074074 |
| `outputs/week17/stage18_selfdiagnosis.json` | `holdout_majority_accuracy_post_hoc` | 0.9074074074074074 |
| `outputs/week17/stage18_selfdiagnosis.json` | `holdout_majority_accuracy_post_hoc` | 0.9074074074074074 |
| `outputs/week17/stage18_selfdiagnosis.json` | `holdout_majority_accuracy_post_hoc` | 0.9074074074074074 |
| `outputs/week17/stage18_selfdiagnosis.json` | `holdout_majority_accuracy_post_hoc` | 0.9074074074074074 |
| `outputs/week17/stage18_selfdiagnosis.json` | `holdout_majority_accuracy_post_hoc` | 0.9074074074074074 |
| `outputs/week17/stage18_selfdiagnosis.json` | `holdout_majority_accuracy_post_hoc` | 0.9074074074074074 |
| `outputs/week17/stage18_selfdiagnosis.json` | `holdout_majority_accuracy_post_hoc` | 0.9074074074074074 |
| `outputs/week17/stage18_selfdiagnosis.json` | `holdout_majority_accuracy_post_hoc` | 0.9074074074074074 |
| `outputs/week17/stage18_selfdiagnosis.json` | `holdout_majority_accuracy_post_hoc` | 0.9074074074074074 |
| `outputs/week17/stage18_selfdiagnosis.json` | `holdout_majority_accuracy_post_hoc` | 0.9074074074074074 |
| `outputs/week17/stage18_selfdiagnosis.json` | `holdout_majority_accuracy_post_hoc` | 0.9074074074074074 |
| `outputs/week17/stage18_selfdiagnosis.json` | `holdout_majority_accuracy_post_hoc` | 0.9074074074074074 |
| `outputs/week17/stage18_selfdiagnosis.json` | `holdout_majority_accuracy_post_hoc` | 0.9074074074074074 |
| `outputs/week17/stage18_selfdiagnosis.json` | `holdout_majority_accuracy_post_hoc` | 0.9074074074074074 |
| `outputs/week17/stage18_selfdiagnosis.json` | `holdout_majority_accuracy_post_hoc` | 0.9074074074074074 |
| `outputs/week17/stage18_selfdiagnosis.json` | `holdout_majority_accuracy_post_hoc` | 0.9074074074074074 |
| `outputs/week17/stage18_selfdiagnosis.json` | `holdout_majority_accuracy_post_hoc` | 0.9074074074074074 |
| `outputs/week17/stage18_selfdiagnosis.json` | `holdout_majority_accuracy_post_hoc` | 0.9074074074074074 |
| `outputs/week17/stage18_selfdiagnosis.json` | `holdout_majority_accuracy_post_hoc` | 0.9074074074074074 |
| `outputs/week17/stage18_selfdiagnosis.json` | `holdout_majority_accuracy_post_hoc` | 0.9074074074074074 |
| `outputs/week17/stage18_selfdiagnosis.json` | `holdout_majority_accuracy_post_hoc` | 0.9074074074074074 |
| `outputs/week17/stage18_selfdiagnosis.json` | `holdout_majority_accuracy_post_hoc` | 0.9074074074074074 |
| `outputs/week17/stage18_selfdiagnosis.json` | `holdout_majority_accuracy_post_hoc` | 0.9074074074074074 |
| `outputs/week17/stage18_selfdiagnosis.json` | `post_hoc` | True |
| `outputs/week17/stage18_selfdiagnosis.json` | `post_hoc` | True |
| `outputs/week17/stage18_selfdiagnosis.json` | `post_hoc` | True |
| `outputs/week17/stage18_selfdiagnosis.json` | `post_hoc` | True |
| `outputs/week23/targeted_two_guess.json` | `delta_star_post_hoc_ev` | 0.14629177061489607 |
| `outputs/week23/targeted_two_guess.json` | `delta_star_post_hoc_ev` | 0.2534219656753691 |

## 6. 逐条发现

| id | 级别 | 说明 |
| --- | --- | --- |
| C1 | **PASS** | confirmatory reporting space is fixed by prereg.yaml (reporting_requirements.must_report, 6 endpoints) and is reproduced by the frozen products |
| C2 | **PASS** | every file carrying a p-value is classified (6 files, 86 cells); unclassified: none |
| C3 | **PASS** | the only family that produced a selection claim (Stage 11, 9 predictors) carries Bonferroni and Holm control, and 0 predictors survive either correction |
| C4 | **INFO** | 3 exploratory families carry uncorrected permutation p-values (['outputs/week15/stage16_predictor.json', 'outputs/week17/stage18_selfdiagnosis.json', 'outputs/week4/p1_anchor_comparison.json']); none is used as a confirmatory headline, and Stage 16 already reports that its chosen rule does not beat the majority baseline |
| C5 | **PASS** | the decision threshold is reported as not_applicable (36 labelled leaves, 0 numeric values, 0 violations), obeying the frozen rule and never substituting a data quantile |
| C6 | **PASS** | every post-hoc quantity is labelled in its own key and used only as a bound (65 labelled leaves) |

## 7. 纪律声明

- 本审计不跑任何新电子结构；所有数字均为已冻结产物的现算读出。
- 本审计不改变任何既有判决；不读取仓库外文件。
- 探索性家族已逐条登记，不得在最终结论里被当成确认性结果引用。
