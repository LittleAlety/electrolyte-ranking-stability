# L01 科学与费用基线（2026-10-29）

HEAD `216a603744b5a7e2fe3d22a116919b4db81907fe`。所有数字由 `work/_l00_l01_baseline.py` 现算，产物 `L00_L01_FACTS.json`。

## 系综标签

- 行数 **48**；acceptance 分布 **{'accepted': 45, 'limited': 3}**
- 非 accepted：DMC|LiM_2plus, DMC|M_plus, EC|LiM_2plus

## 覆盖复核（docs 级）

| route | 行数 |
|---|---|
| multi_basin_coverage | 8 |
| single_basin_verified | 3 |
| unresolved_qc | 3 |

| verdict | 行数 |
|---|---|
| resolved | 11 |
| unresolved | 3 |

## 身份证据

- frontier identity rows: **80**；`identity_qc_status` = {'verified': 80}
- frontier localization rows: **80**；`status` = {'computed': 80}

## WP5 目标池（AB_axis_endpoint）

- 轴数 **32**；`n_pool` = {'11': 16, '10': 16}
- `stop_budget_status` = {'computed': 19, 'not_reached_within_pool': 13}

## 费用链（task → element → raw id → measured）

| attempt | slurm_element | job_id_raw | raw 交叉? | cores | elapsed_s | ledger CH | recomputed CH | 一致 |
|---|---|---|---|---|---|---|---|---|
| dol_ec_reopt_DOL_1 | 3791416_0 | 3791417 | 是 | 4 | 810 | 0.900000 | 0.900000 | OK |
| dol_ec_reopt_EC_1 | 3791416_1 | 3791416 | 否 | 4 | 1004 | 1.115556 | 1.115556 | OK |

说明：`JobIDRaw` 与数组元素 id 交叉是**已识别的事实**，不是缺陷；权威链为 `run job array` → `slurm_element` → 该行 `JobIDRaw`。

## EC 候选资料（不是可提交包）

- 包 `hpc_ec_recovery_v2_20261028`；候选 6 个：ec_v2_p3, ec_v2_p4, ec_v2_p5, ec_v2_p6, ec_v2_p7, ec_v2_p8
- 预选：ec_v2_p4, ec_v2_p7
- 源几何 `work/hpc_dol_ec_recovery_v1_reopt_20261027/tasks/EC/LiM_2plus__p4_02_ring_pucker_twist/snapshots/3791416_1/job.xyz`
- 源 SHA 声明 / 实测 = `a0a8d53b1e6083c4…` / `a0a8d53b1e6083c4…` ⇒ **一致**
- profile `orca_production_4h_v1`；预算 32 CH；按 16 CH/元素 × 2 = 32 CH（恰等于上限）
- **尚缺**：members / batches / tasks.txt / batch_1.txt / sbatch / 生产输入 / 完整 SHA 闭包 ⇒ 不能称端到端通过（见 L03）。
