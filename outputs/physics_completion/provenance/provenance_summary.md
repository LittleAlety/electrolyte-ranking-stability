# 复现证据清单（per-job provenance）

> 由 `scripts/wp_production/build_compute_provenance.py` 生成；零新增电子结构计算。
> 原始 ORCA / xTB 输出不入库，本清单给出**逻辑位置 + sha256 + 解析出的引擎、方法与 QC**，
> 使独立归档可被逐条复核。

## 覆盖

| cohort | 作业数 | 有原始输出 | 正常结束 |
| --- | --- | --- | --- |
| wp1_geometry_prep | 1 | 1 | 1 |
| wp1_method_audit | 160 | 160 | 160 |
| wp2_production | 16 | 14 | 10 |
| wp2_sampling | 640 | 640 | 640 |
| wp3_recheck | 12 | 12 | 12 |

## 四分子 20 条腿现场核对

> 把「清单登记了哪些作业」与 `work/wp2prod/<NAME>/<STATE>/` 的磁盘事实对起来；`not_started` 不是失败，只是这条腿还没排上。
`duplicate_work_risk=true` 是本表唯一的告警：磁盘上已有正常结束的原始输出、
清单里却没有对应的 computed 作业行，重新排队就等于重复计算。

| 腿 | 分类 | 磁盘原始输出 | 正常结束 | 重复风险 |
| --- | --- | --- | --- | --- |
| DMC|M | computed | true | true | false |
| DMC|M_plus | computed | true | true | false |
| DMC|LiM_plus | computed | true | true | false |
| DMC|LiM_2plus | in_flight | false | false | false |
| DMC|M_tzvpd | not_started | false | false | false |
| EMC|M | computed | true | true | false |
| EMC|M_plus | computed | true | true | false |
| EMC|LiM_plus | failed | true | false | false |
| EMC|LiM_2plus | failed | true | false | false |
| EMC|M_tzvpd | not_started | false | false | false |
| GBL|M | computed | true | true | false |
| GBL|M_plus | computed | true | true | false |
| GBL|LiM_plus | in_flight | false | false | false |
| GBL|LiM_2plus | not_started | false | false | false |
| GBL|M_tzvpd | computed | true | true | false |
| SL|M | computed | true | true | false |
| SL|M_plus | computed | true | true | false |
| SL|LiM_plus | failed | true | false | false |
| SL|LiM_2plus | failed | true | false | false |
| SL|M_tzvpd | not_started | false | false | false |

## 未正常结束的作业

| job_id | state | failure_reason |
| --- | --- | --- |
| wp2prod/EMC/LiM_2plus | LiM_2plus | mpi_smpd_unavailable |
| wp2prod/EMC/LiM_plus | LiM_plus | mpi_smpd_communication_lost |
| wp2prod/SL/LiM_2plus | LiM_2plus | mpi_smpd_unavailable |
| wp2prod/SL/LiM_plus | LiM_plus | mpi_smpd_communication_lost |

* 分类只依据该作业自己 `.log` 里的字符串，不做外部推断。
* `mpi_smpd_*`：Microsoft MPI 的 smpd 在作业期间不可用或失联（主机重启后需要重新拉起，队列器 `ensure_smpd()` 已处理）。
* `orca_cannot_open_scratch_file`：ORCA 打不开自己的 scratch 文件。
* 这类残骸不构成任何物理结论，也不替代缺失的腿。

## 读法

* `job_archive_manifest.csv`：逐作业的输入 / 起始几何 / 最终几何 / 原始输出路径与 sha256，
  以及 `orca_keyword`、`orca_version`、能量与频率 QC。
* `derived_to_job_map.csv`：已提交派生表里的每一行数值对应哪个作业。
* `provenance_index.json` 的 `evidence_digest` 是对全部哈希的确定性摘要：
  解压独立归档后按同一配方重算即可复核。
* `engine` / `engine_version`：ORCA cohort 为 ORCA 及其版本（与 `orca_version` 同源，都从该作业自己的 .log 读回）；采样 cohort 为 GFN2-xTB 与 xTB 版本。`orca_keyword` / `orca_version` 只对 ORCA cohort 有值。
* `n_files_hashed`：本行登记的 sha256 个数（ORCA 行最多 4 个：inp / 起始几何 / 最终几何 / 原始输出；采样行 3 个：起始几何 / 优化几何 / xtbopt.log）。
* `wp3_recheck` 行：方案 11 的靶向第二泛函单点，起始几何是冻结的生产 Opt 几何；单点不产生新几何（`final_geometry_path` 为空），`final_sp_eh` 与 `pair_evidence/targeted_recheck/recheck_results.csv` 的 `energy_eh` 同源。
* 采样 cohort 每行对应一个 ETKDG 起点目录；聚合缓存 `work/sampling/xtb_results.csv` 的 sha256 记在 `provenance_index.json` 的 `raw_cache`。
* 派生 CSV 的 `--check` 只证明内部一致；**原始日志的 sha256 才是外部可复核的证据**。
