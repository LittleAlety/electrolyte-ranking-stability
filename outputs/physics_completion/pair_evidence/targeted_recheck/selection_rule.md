# 方案 5.3 / 11：关键 pair 第二泛函靶向复核 —— 预注册计划

> 由 `scripts/wp_production/build_pair_recheck_plan.py` 生成；**零新增电子结构计算**。
> 本文件在任何一个复核单点跑出结果之前登记；规则不随后续结果修改。

## 选取规则（结果前冻结）

* pairs = exactly the pairs certified as a robust inversion on the frozen-geometry method axis
* molecules = the members of those pairs that also belong to the four-molecule production subcohort
* legs = every scoped molecule x the four main states M / M_plus / LiM_plus / LiM_2plus
* settings = the two pre-accepted second-functional settings S3 and S4
* geometry = the leg production Opt geometry; no re-optimisation and no frequency
* trigger = a leg two single points are queued only after that leg production Opt/Freq is registered
* prohibited = no result-based point selection, no adding or dropping rows by outcome, no re-running the whole 128 single-point matrix

| 项 | 值 |
| --- | --- |
| 认证的 pair | EMC|GBL、EMC|SL |
| pair 成员 | EMC、GBL、SL |
| 本次范围内的分子 | EMC、GBL、SL |
| 落在四分子分母之外的成员 | 无 |
| 主态 | M / M_plus / LiM_plus / LiM_2plus |
| 第二泛函设定 | S3 (PBE0-D4/def2-TZVP) / S4 (PBE0-D4/def2-TZVPD) |
| 计划单点总数 | 24 |
| 方案 11 预算 | 16-32 |
| 可用（生产腿已登记） | 14 |
| 阻塞（生产腿未登记） | 10 |

## 作业计划（24 行，逐行登记）

| 记录 | 分子 | 态 | 设定 | 泛函/基组 | 几何来源 | 几何可用 | 新增几何 | 新增频率 | 状态 | 阻塞于 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| C02|M|S3 | EMC | M | S3 | PBE0-D4/def2-TZVP | `work/wp2prod/EMC/M/EMC_M_opt.xyz` | true | false | false | ready | - |
| C02|M|S4 | EMC | M | S4 | PBE0-D4/def2-TZVPD | `work/wp2prod/EMC/M/EMC_M_opt.xyz` | true | false | false | ready | - |
| C02|M_plus|S3 | EMC | M_plus | S3 | PBE0-D4/def2-TZVP | `work/wp2prod/EMC/M_plus/EMC_M_plus_opt.xyz` | true | false | false | ready | - |
| C02|M_plus|S4 | EMC | M_plus | S4 | PBE0-D4/def2-TZVPD | `work/wp2prod/EMC/M_plus/EMC_M_plus_opt.xyz` | true | false | false | ready | - |
| C02|LiM_plus|S3 | EMC | LiM_plus | S3 | PBE0-D4/def2-TZVP | `work/wp2prod/EMC/LiM_plus/EMC_LiM_plus_opt.xyz` | false | false | false | blocked_on_production_leg | C02|LiM_plus |
| C02|LiM_plus|S4 | EMC | LiM_plus | S4 | PBE0-D4/def2-TZVPD | `work/wp2prod/EMC/LiM_plus/EMC_LiM_plus_opt.xyz` | false | false | false | blocked_on_production_leg | C02|LiM_plus |
| C02|LiM_2plus|S3 | EMC | LiM_2plus | S3 | PBE0-D4/def2-TZVP | `work/wp2prod/EMC/LiM_2plus/EMC_LiM_2plus_opt.xyz` | false | false | false | blocked_on_production_leg | C02|LiM_2plus |
| C02|LiM_2plus|S4 | EMC | LiM_2plus | S4 | PBE0-D4/def2-TZVPD | `work/wp2prod/EMC/LiM_2plus/EMC_LiM_2plus_opt.xyz` | false | false | false | blocked_on_production_leg | C02|LiM_2plus |
| C13|M|S3 | GBL | M | S3 | PBE0-D4/def2-TZVP | `work/wp2prod/GBL/M/GBL_M_opt.xyz` | true | false | false | ready | - |
| C13|M|S4 | GBL | M | S4 | PBE0-D4/def2-TZVPD | `work/wp2prod/GBL/M/GBL_M_opt.xyz` | true | false | false | ready | - |
| C13|M_plus|S3 | GBL | M_plus | S3 | PBE0-D4/def2-TZVP | `work/wp2prod/GBL/M_plus/GBL_M_plus_opt.xyz` | true | false | false | ready | - |
| C13|M_plus|S4 | GBL | M_plus | S4 | PBE0-D4/def2-TZVPD | `work/wp2prod/GBL/M_plus/GBL_M_plus_opt.xyz` | true | false | false | ready | - |
| C13|LiM_plus|S3 | GBL | LiM_plus | S3 | PBE0-D4/def2-TZVP | `work/wp2prod/GBL/LiM_plus/GBL_LiM_plus_opt.xyz` | false | false | false | blocked_on_production_leg | C13|LiM_plus |
| C13|LiM_plus|S4 | GBL | LiM_plus | S4 | PBE0-D4/def2-TZVPD | `work/wp2prod/GBL/LiM_plus/GBL_LiM_plus_opt.xyz` | false | false | false | blocked_on_production_leg | C13|LiM_plus |
| C13|LiM_2plus|S3 | GBL | LiM_2plus | S3 | PBE0-D4/def2-TZVP | `work/wp2prod/GBL/LiM_2plus/GBL_LiM_2plus_opt.xyz` | false | false | false | blocked_on_production_leg | C13|LiM_2plus |
| C13|LiM_2plus|S4 | GBL | LiM_2plus | S4 | PBE0-D4/def2-TZVPD | `work/wp2prod/GBL/LiM_2plus/GBL_LiM_2plus_opt.xyz` | false | false | false | blocked_on_production_leg | C13|LiM_2plus |
| C14|M|S3 | SL | M | S3 | PBE0-D4/def2-TZVP | `work/wp2prod/SL/M/SL_M_opt.xyz` | true | false | false | ready | - |
| C14|M|S4 | SL | M | S4 | PBE0-D4/def2-TZVPD | `work/wp2prod/SL/M/SL_M_opt.xyz` | true | false | false | ready | - |
| C14|M_plus|S3 | SL | M_plus | S3 | PBE0-D4/def2-TZVP | `work/wp2prod/SL/M_plus/SL_M_plus_opt.xyz` | true | false | false | ready | - |
| C14|M_plus|S4 | SL | M_plus | S4 | PBE0-D4/def2-TZVPD | `work/wp2prod/SL/M_plus/SL_M_plus_opt.xyz` | true | false | false | ready | - |
| C14|LiM_plus|S3 | SL | LiM_plus | S3 | PBE0-D4/def2-TZVP | `work/wp2prod/SL/LiM_plus/SL_LiM_plus_opt.xyz` | true | false | false | ready | - |
| C14|LiM_plus|S4 | SL | LiM_plus | S4 | PBE0-D4/def2-TZVPD | `work/wp2prod/SL/LiM_plus/SL_LiM_plus_opt.xyz` | true | false | false | ready | - |
| C14|LiM_2plus|S3 | SL | LiM_2plus | S3 | PBE0-D4/def2-TZVP | `work/wp2prod/SL/LiM_2plus/SL_LiM_2plus_opt.xyz` | false | false | false | blocked_on_production_leg | C14|LiM_2plus |
| C14|LiM_2plus|S4 | SL | LiM_2plus | S4 | PBE0-D4/def2-TZVPD | `work/wp2prod/SL/LiM_2plus/SL_LiM_2plus_opt.xyz` | false | false | false | blocked_on_production_leg | C14|LiM_2plus |

## 复核结果（已登记 14 条，实测 0.841672 core-hours）

| pair | 设定 | Eox(i) | Eox(j) | delta | 符号 | 基组一致 | 与冻结 R1b 同号 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| EMC | GBL | S3 | 7.972485645 | 7.490565229 | 0.481920 | positive | true | false |
| EMC | GBL | S4 | 7.993057944 | 7.518449541 | 0.474608 | positive | true | false |
| EMC | SL | S3 | 7.972485645 | 7.582502579 | 0.389983 | positive | true | false |
| EMC | SL | S4 | 7.993057944 | 7.616868069 | 0.376190 | positive | true | false |

* 在本表登记的 4 个 (pair, 设定) 上，**0 个**的 delta 符号与冻结 R1b 一致（4 个不一致）。
* 这里用的是**生产级溶液优化几何**（M 与 M_plus 各自 Opt），对应的是 R2 那一级的语义，
  不是 R1b 的冻结 r2SCAN-3c 几何；因此符号差异同时混着「换几何」与「换泛函」两个因素，
  单看这张表**不能**把它们分开。分开需要 R2 在**生产泛函**上补齐基组一致的中性腿（M_tzvpd）。
* 单点全部落在**已登记的生产 Opt 几何**上（逐行登记 geometry_sha256），不重优化、不算频率；
  原始 ORCA 现场留在仓库外 work/recheck/，recheck_results.csv 是折入后的登记表。
* 这是**第二泛函（audit control）**在溶液优化几何上的电子能层复核，不能替代生产泛函的自由能标签，
  也没有把任何结果回填进 job_plan.csv 的结果列（计划表始终不含数值列）。

## 验收（14/14 通过）

| check | ok | detail |
| --- | --- | --- |
| registered_before_any_recheck_sp | PASS | plan rows 24 (ready 14 / blocked 10); result columns in the job plan: none; registered single points live in recheck_results.csv: 14 |
| scope_is_exactly_the_certified_pairs | PASS | pairs=EMC|GBL; EMC|SL; n_pairs_certified=2 |
| molecules_are_the_certified_members_in_the_subcohort | PASS | pair members=EMC, GBL, SL; in scope=EMC, GBL, SL; outside the four-molecule subcohort=none |
| planned_sp_matches_the_rule | PASS | 3 molecules x 4 states x 2 settings = 24 single points (ready 14 / blocked 10) |
| planned_sp_inside_the_plan_11_budget | PASS | plan 11 row targeted_pair_second_method_single_points = 16-32; planned = 24 |
| settings_are_the_frozen_second_functional | PASS | S3 = PBE0-D4/def2-TZVP (role=audit_control); S4 = PBE0-D4/def2-TZVPD (role=audit_control) |
| production_registered_legs_are_ready | PASS | ready legs 7/12: C02|M, C02|M_plus, C13|M, C13|M_plus, C14|LiM_plus, C14|M, C14|M_plus |
| unregistered_legs_are_blocked_and_named | PASS | blocked rows 10, each naming its missing leg: C02|LiM_2plus, C02|LiM_plus, C13|LiM_2plus, C13|LiM_plus, C14|LiM_2plus |
| no_new_geometry_no_new_frequency_no_result_columns | PASS | result-bearing columns: none |
| results_cover_exactly_the_ready_rows | PASS | ready 14, registered 14, blocked rows carrying a result 0 |
| results_are_the_frozen_second_functional_on_the_registered_geometry | PASS | 14 rows; settings S3, S4; functional/basis match method_settings.csv row by row |
| derived_pair_gaps_are_basis_consistent_and_recomputed | PASS | EMC | GBL|S3 delta=0.481920 eV (positive); EMC | GBL|S4 delta=0.474608 eV (positive); EMC | SL|S3 delta=0.389983 eV (positive); EMC | SL|S4 delta=0.376190 eV (positive) |
| budget_row_in_cost_ledger_still_planned | PASS | targeted_pair_second_method_single_points status=planned value=16-32 |
| measured_cost_row_matches_the_registered_results | PASS | targeted_pair_second_method_single_points_computed value=14 status=measured; registered computed=14, measured core-hours=0.841672 |

## 边界

* 计划层只登记规则、对象、设定、几何来源与预算；结果另立一层 recheck_results.csv，两者不混。
* 生产腿一旦登记，按同一规则自动解锁该腿的两支单点；解锁只取决于登记状态，不取决于任何能量或符号。
* 生产腿的最终 Opt 几何与原始 ORCA 输出留在仓库外 `work/wp2prod/`，不入交付镜像（与既有边界一致）。
