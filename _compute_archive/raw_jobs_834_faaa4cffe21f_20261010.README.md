# 原始作业输出归档（独立于仓库）

- 来源：`outputs/physics_completion/provenance/job_archive_manifest.csv`
- 作业数：834，文件数：2518，未压缩大小：33.6 MB
- evidence_digest：`faaa4cffe21f778d304cb784d2b51da042829580911b159d3195cf619c0df04b`
- 内嵌登记表 `_manifest/job_archive_manifest.csv`：sha256 `a2bf2e11839fbe4a11fef773e381d0664eed298af9068b98dd680d51e3914291`（834 行）

## 如何复核

1. 解压；2. 对每个条目重算 sha256，与 `raw_jobs_834_faaa4cffe21f_20261010.index.csv` 逐行比对；
3. 与 manifest 的同名 sha256 列再比一次（两处应一致）。
4. 判断本归档是否过期：把内嵌的 `_manifest/job_archive_manifest.csv` 与仓库当前那份逐字节比较，
   不一致就说明归档早于最新登记，需要重新 `--build`。

也可直接：`python scripts/wp_production/archive_raw_outputs.py --check raw_jobs_834_faaa4cffe21f_20261010.zip`
