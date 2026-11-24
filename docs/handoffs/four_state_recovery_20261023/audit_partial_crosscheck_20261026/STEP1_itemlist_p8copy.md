# STEP1：plan_compliance 未满足项清单（增量落盘）

来源：outputs/physics_completion/compliance/plan_compliance.csv（逐字以 CSV 为准，md 表格辅助）

统计：partial=13, not_satisfied=2, blocked_on_production=2, **合计 17**

| # | item_id | status | plan_section | requirement |
|---|---------|--------|--------------|-------------|
| 1 | wp2_conformer_ensemble | partial | §6 WP2 固定背景配对自由能标签 | 12 x 4 主态的生产级同态构象/配位 motif 系综自由能 G_ensemble |
| 2 | wp2_sampling_extension | partial | §6 WP2 固定背景配对自由能标签 | 采样审计集 3 -> 6 结构比较与 sampling_limited 判定 |
| 3 | wp2_state_identity_qc | partial | §6 WP2 固定背景配对自由能标签 | §6.3 每态 QC（SCF/几何收敛、虚频、spin、连接关系、Li-donor motif、fragment 电荷/自旋、frontier localization）与身份分层（intact / Li-centered / mixed / ambiguous / fragmented 分开表） |
| 4 | wp3_pair_evidence | partial | §7 WP3 排序、独立 uncertainty 与机制 | 固定模型下的保守符号一致性：STABLE / UNRESOLVED / ROBUST_INVERSION |
| 5 | wp3_targeted_second_method | partial | §7 WP3 排序、独立 uncertainty 与机制 | 关键 pair 第二泛函靶向复核（只对新优化几何的单点） |
| 6 | wp3_mechanism_cases | partial | §7 WP3 排序、独立 uncertainty 与机制 | §7.3 机制案例最多 3 个（事先规则选定），且逐例给出六项证据 |
| 7 | wp5_new_endpoint_in_budget | partial | §9 WP5 delta-learning 与成本感知主动查询 | 新端点 O_3>=2/3 且 R_3<=0.10 eV 真的用于算预算 |
| 8 | wp5_formal_ab_stop_budget_reached | partial | §9 WP5 delta-learning 与成本感知主动查询 | 正式 A/B 回放里真正达到相邻两点联合停止预算的组合数（子池口径） |
| 9 | wp5_two_consecutive_points | partial | §9 WP5 delta-learning 与成本感知主动查询 | 至少 16/20 回放在两个连续预算点达标才报经验停止预算；12 标签池回放 |
| 10 | wp5_absolute_cost_ledger | partial | §11 停止规则 | 绝对成本三项：cpu_core_hours / p90_job_cost / frequency_only_cost |
| 11 | wp5_remaining_unqueried_error | partial | §9 WP5 delta-learning 与成本感知主动查询 | §9.2 每轮报告 n_T->tau_b、O_3、R_3、remaining_unqueried_error 与累计 core-hours |
| 12 | wp5_pool_extension | not_satisfied | §9 WP5 delta-learning 与成本感知主动查询 | §9.3 扩样触发：目标池扩到约 20-24（先加 8-12 个，含一个方法审计未覆盖的家族），先冻结再计算 |
| 13 | wp6_explicit_ligand | blocked_on_production | §10 WP6 显式配体检查（可选） | 可选 WP6：固定 R=DME 的共同背景显式配体检查 |
| 14 | stop_rules_registered | partial | §11 停止规则 | 停止规则（unresolved / sampling_limited / identity outcome / validation limitation） |
| 15 | wp2_pilot_cost_fields | partial | §11 停止规则 | §11 前 2 个分子的 pilot 逐作业记录 wall time / allocated cores / core-hours / memory / failed-retry / phase / method / state / conformer / raw output |
| 16 | strict_readiness_evidence | not_satisfied | §1 研究问题与最终交付 | 逐项严格证据：覆盖复核 / 成员身份 / 采样审计 / WP3 / WP5 全池 / 成本来源 |
| 17 | plan_overall_complete | blocked_on_production | §1 研究问题与最终交付 | 原方案核心闭环：12 主集 x 4 主态、12 个 free/Li 标签、48 态生产系综与目标排序证据 |

*落盘时刻：按 Lead 指令先落盘 STEP1，再继续 STEP2。*
