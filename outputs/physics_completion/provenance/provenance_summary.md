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
* 采样 cohort 每行对应一个 ETKDG 起点目录；聚合缓存 `work/sampling/xtb_results.csv` 的 sha256 记在 `provenance_index.json` 的 `raw_cache`。
* 派生 CSV 的 `--check` 只证明内部一致；**原始日志的 sha256 才是外部可复核的证据**。
