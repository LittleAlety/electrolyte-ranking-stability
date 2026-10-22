# strict_recovery_v1 批次结果报告

> 生成器 `build_strict_recovery_report.py`（`--check` 完全只读）。
> 只报告观测到的状态：**不把失败改写成通过、不清空 n_limited、不放宽任何阈值**。

## 系综口径

| 状态 | 态数 |
|---|---|
| accepted | 41 |
| provisional | 0 |
| limited | 7 |

分母固定 48；未 accepted 共 **7** 态（`provisional` = 有登记补救在飞，`limited` = 首轮搜索耗尽）。

## 恢复腿终局统计（按**最后一次真实运行**；规划中的补救另计）

| 状态 | 腿数 |
|---|---|
| `computed` | 6 |
| `technical_complete_qc_failed` | 6 |

**在飞补救（已提交、尚未产出结果）**：0 条腿


失败类分布（最后一次真实运行）：

- `strict_reopt_not_needed`: 6
- `strict_reopt_required`: 4
- `verytight_convergence`: 2

## 覆盖复核裁决（离开 `limited` 的唯一通道）

| verdict | 态数 |
|---|---|
| `search_exhausted` | 5 |
| `unresolved` | 2 |

## 本批放行的态（覆盖复核 resolved）

| 态 | 系综状态 | n_unique | 历史 n_limited（保留） | g_ensemble (Eh) |
|---|---|---|---|---|
| `DEC|M` | `accepted` | 3 | **1** | -422.45386546854 |
| `DME|LiM_2plus` | `accepted` | 2 | **2** | -316.18568257157 |
| `DME|M_plus` | `accepted` | 3 | **1** | -308.75146090372 |
| `EMC|M_plus` | `accepted` | 2 | **1** | -382.82477506813 |
| `SL|LiM_2plus` | `accepted` | 2 | **1** | -713.21346632930 |
| `TMP|LiM_2plus` | `accepted` | 3 | **1** | -769.48074188281 |
| `TMP|M_plus` | `accepted` | 2 | **3** | -762.03948789889 |

`n_limited` 一列是**故意保留的历史计数**：这些态经复核放行，但「曾经有限制」这件事仍然记在账本里——不是清空它。


## 逐态明细（仅未 accepted 的态）

| 态 | 系综状态 | 复核 verdict | 搜索结论 | 注册起点 | 腿（尝试次数 / 最后真实结果 / 当前） |
|---|---|---|---|---|---|
| AN\|M_plus | `limited` | `search_exhausted` | `no_new_minimum_found` | 0 | —（无恢复腿） |
| DMC\|LiM_2plus | `limited` | `search_exhausted` | `no_new_minimum_found` | 0 | —（无恢复腿） |
| DMC\|M_plus | `limited` | `search_exhausted` | `no_new_minimum_found` | 0 | —（无恢复腿） |
| DMSO\|LiM_plus | `limited` | `unresolved` | `new_minima_found` | 1 | LiM_plus\|r3m_c00（2/2；结果 technical_complete_qc_failed/strict_reopt_required；当前 technical_complete_qc_failed） |
| DOL\|LiM_2plus | `limited` | `search_exhausted` | `no_new_minimum_found` | 0 | —（无恢复腿） |
| EC\|LiM_2plus | `limited` | `search_exhausted` | `no_new_minimum_found` | 0 | —（无恢复腿） |
| TMP\|LiM_plus | `limited` | `unresolved` | `new_minima_found` | 2 | LiM_plus\|r3m_c05（2/2；结果 technical_complete_qc_failed/verytight_convergence；当前 technical_complete_qc_failed）<br>LiM_plus\|r3m_c08（2/2；结果 technical_complete_qc_failed/strict_reopt_required；当前 technical_complete_qc_failed） |

## 本轮无法恢复的态（需换搜索方法，不在本批预算内）

- `AN|M_plus` — no_new_minimum_found
- `DMC|LiM_2plus` — no_new_minimum_found
- `DMC|M_plus` — no_new_minimum_found
- `DOL|LiM_2plus` — no_new_minimum_found
- `EC|LiM_2plus` — no_new_minimum_found

## 尝试预算已用尽的腿（不再自动重试，保留原因）

- `TMP|M_plus|c10` — `strict_reopt_required`：orca_close_enough_but_frozen_tolE_missed_reopt_required;hess_act_energy=0_anfreq
- `TMP|M_plus|r3_c42` — `strict_reopt_required`：orca_close_enough_but_frozen_tolE_missed_reopt_required;hess_act_energy=0_anfreq
- `DME|LiM_2plus|r3m_c03` — `verytight_convergence`：VeryTightOpt final criterion not met: energy_change_Eh=2.63e-07 > 2e-07;hess_act
- `DMSO|LiM_plus|r3m_c00` — `strict_reopt_required`：orca_close_enough_but_frozen_tolE_missed_reopt_required;hess_act_energy=0_anfreq
- `TMP|LiM_plus|r3m_c05` — `verytight_convergence`：VeryTightOpt final criterion not met: energy_change_Eh=2.0146e-06 > 2e-07;hess_a
- `TMP|LiM_plus|r3m_c08` — `strict_reopt_required`：orca_close_enough_but_frozen_tolE_missed_reopt_required;hess_act_energy=0_anfreq

**结论口径**：本报告不改变任何验收判定。系综达到 41/48；`plan_overall_complete` 与 WP6 只有在 48/48 时才可能开闸。
