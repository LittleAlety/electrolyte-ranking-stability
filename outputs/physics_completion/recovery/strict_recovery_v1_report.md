# strict_recovery_v1 批次结果报告

> 生成器 `build_strict_recovery_report.py`（`--check` 完全只读）。
> 只报告观测到的状态：**不把失败改写成通过、不清空 n_limited、不放宽任何阈值**。

## 系综口径

| 状态 | 态数 |
|---|---|
| accepted | 43 |
| provisional | 0 |
| limited | 5 |

分母固定 48；未 accepted 共 **5** 态（`provisional` = 有登记补救在飞，`limited` = 首轮搜索耗尽）。

## 恢复腿终局统计（按**最后一次真实运行**；规划中的补救另计）

| 状态 | 腿数 |
|---|---|
| `computed` | 13 |
| `never_ran` | 8 |
| `technical_complete_qc_failed` | 2 |

**在飞补救（已提交、尚未产出结果）**：8 条腿


失败类分布（最后一次真实运行）：

- `strict_reopt_not_needed`: 13
- `verytight_convergence`: 2

## 覆盖复核裁决（离开 `limited` 的唯一通道）

| verdict | 态数 |
|---|---|
| `pending` | 3 |
| `search_exhausted` | 1 |
| `unresolved` | 1 |

## 本批放行的态（覆盖复核 resolved）

| 态 | 系综状态 | n_unique | 历史 n_limited（保留） | g_ensemble (Eh) |
|---|---|---|---|---|
| `DEC|M` | `accepted` | 3 | **1** | -422.45386546854 |
| `DME|LiM_2plus` | `accepted` | 2 | **2** | -316.18568257157 |
| `DME|M_plus` | `accepted` | 3 | **1** | -308.75146090372 |
| `DMSO|LiM_plus` | `accepted` | 1 | **1** | -560.78564823000 |
| `EMC|M_plus` | `accepted` | 2 | **1** | -382.82477506813 |
| `SL|LiM_2plus` | `accepted` | 2 | **1** | -713.21346632930 |
| `TMP|LiM_2plus` | `accepted` | 3 | **1** | -769.48074188281 |
| `TMP|LiM_plus` | `accepted` | 3 | **1** | -769.79444611358 |
| `TMP|M_plus` | `accepted` | 3 | **2** | -762.03948794417 |

`n_limited` 一列是**故意保留的历史计数**：这些态经复核放行，但「曾经有限制」这件事仍然记在账本里——不是清空它。


## 逐态明细（仅未 accepted 的态）

| 态 | 系综状态 | 复核 verdict | 搜索结论 | 注册起点 | 腿（尝试次数 / 最后真实结果 / 当前） |
|---|---|---|---|---|---|
| AN\|M_plus | `limited` | `unresolved` | `no_new_minimum_found` | 0 | M_plus\|tors_3_0_1_2（1/2；结果 computed/strict_reopt_not_needed；当前 computed）<br>M_plus\|tors_4_0_1_2（1/2；结果 computed/strict_reopt_not_needed；当前 computed）<br>M_plus\|tors_5_0_1_2（1/2；结果 computed/strict_reopt_not_needed；当前 computed） |
| DMC\|LiM_2plus | `limited` | `pending` | `no_new_minimum_found` | 0 | LiM_2plus\|tors_6_0_1_2（0/2；结果 未跑；当前 pending）<br>LiM_2plus\|tors_7_0_1_2（0/2；结果 未跑；当前 pending）<br>LiM_2plus\|tors_8_0_1_2（0/2；结果 未跑；当前 pending） |
| DMC\|M_plus | `limited` | `pending` | `no_new_minimum_found` | 0 | M_plus\|tors_6_0_1_2（0/2；结果 未跑；当前 pending）<br>M_plus\|tors_7_0_1_2（0/2；结果 未跑；当前 pending）<br>M_plus\|tors_8_0_1_2（0/2；结果 未跑；当前 pending） |
| DOL\|LiM_2plus | `limited` | `search_exhausted` | `no_new_minimum_found` | 0 | —（无恢复腿） |
| EC\|LiM_2plus | `limited` | `pending` | `no_new_minimum_found` | 0 | LiM_2plus\|tors_2_3_4_10（0/2；结果 未跑；当前 pending）<br>LiM_2plus\|tors_5_3_4_10（0/2；结果 未跑；当前 pending） |

## 本轮无法恢复的态（需换搜索方法，不在本批预算内）

- `AN|M_plus` — no_new_minimum_found
- `DMC|LiM_2plus` — no_new_minimum_found
- `DMC|M_plus` — no_new_minimum_found
- `DOL|LiM_2plus` — no_new_minimum_found
- `EC|LiM_2plus` — no_new_minimum_found

## 尝试预算已用尽的腿（不再自动重试，保留原因）

- `TMP|M_plus|c10` — `verytight_convergence`：VeryTightOpt final criterion not met: energy_change_Eh=3.13e-07 > 2e-07;hess_act
- `DME|LiM_2plus|r3m_c03` — `verytight_convergence`：VeryTightOpt final criterion not met: energy_change_Eh=2.63e-07 > 2e-07;hess_act

**结论口径**：本报告不改变任何验收判定。系综达到 43/48；`plan_overall_complete` 与 WP6 只有在 48/48 时才可能开闸。
