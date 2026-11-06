# coverage 发布申请（最终修订；待授权，未执行）

> `d483f76a…` 的**引用载体已找到**：`round23.../RELEASE_APPLICATION_FINAL.md` 第 38 行；对应结果字节/生成方式 **UNVERIFIED**（现 `rebuild_run/REPLAY_RESULT.json` 为 `213b7a1b…`，旧字节未保留）。`coverage_review_20261106/RELEASE_APPLICATION.md`（`7b5e2cf6…`）不含 d483。当前绑定改为外部记录的结果 `19f02168…`；`REPLAY_RESULT.json` 不内嵌自身哈希。
> 本申请绑定 v2 结果 `19f02168a0d9cf30b602e9fc663530bb73cff3e6c0097c5259cdd2c90609f49f`（76990 B，`rebuild_run_rev2_20261107/REPLAY_RESULT.json`）。

## 1. 源→目标文件集

| # | 文件 | 当前 | 目标 | 写入性质 |
|---|---|---|---|---|
| 1 | `scripts/wp_production/build_coverage_reviews.py` | `a7eee5aa…`/29,558 | `7e8584e8…`/32,312 | 内容替换 |
| 2 | `outputs/.../recovery/coverage_reviews.csv` | `e89188f6…`/6,102 | `2de94de3…`/6,139 | 内容变化 |
| 3 | `outputs/.../ensembles/production_ensemble_labels.csv` | `c21003f5…`/11,831 | `2458f0af…`/11,778 | 内容变化 |
| 4 | `weights.csv` | `201e1954…`/5,850 | 同 | 会重写，预期字节不变 |
| 5 | `dedup.csv` | `1f3ea929…`/7,398 | 同 | 会重写，预期字节不变 |
| 6 | `dedup_pairs.csv` | `4d294544…` | 同 | 会重写，预期字节不变 |
| 7 | `production_ensemble_index.json` | 当前 | 聚合器重写 | 内容变化（含时间戳） |
| 8 | `coverage_reviews_index.json` | 当前 | 生成器重写 | 内容变化（含时间戳） |

**只读输入**（前后须同）：structures `3a795ce8…`、candidates `6096cd12…`、dispositions `56bbc82c…`、aggregator `7f6dd47f…`、config/manifest/search/geometry/probe manifests 共 145 件登记于 `REPLAY_RESULT.dependencies_before`。

## 2. 结果与绑定

- 四版 counts：45/2/1、44/3/1、43/4/1、43/4/1；labels/weights/dedup_pairs 见 `CLOSURE_REPORT.md`。
- 入口脚本 `47f8e3036abd938c1e9206f9e29265b83982dcbb809cd7effcf9aa03547cebf4`；负测四种退出码 2/3/4/5 均被拒（子步骤失败为真实 SyntaxError）。
- 环境 Python 3.10.11 / numpy 1.26.4。
- 正式输入 before=after；`formal_unchanged=true`。

## 3. 标签口径

- **DOL|LiM_2plus**：disk→shared 版本重推导影响（accepted→limited）。
- **AN|M_plus**：shared→old 缺陷修复影响（accepted→limited，F1）。
- **43/4/1**：拟发布规则下标签，**不是严格验收 43 态通过**；历史 45/2/1 保留。

## 4. 备份与回退

落地前建备份目录，逐件复制 §1 的 1–8 文件并记完整 SHA；失败按备份恢复，不删旧版。两个 index 的 `generated_at_utc` 等时间戳字段非确定，确定性字段（labels/weights/dedup/dedup_pairs/coverage）按上表核验。

## 5. 未闭合

- B/C 条件回归 OPEN（仅索引 6/6）。
- 三态 L2b、可比性、EC 10°、`coord_1`、新增成员准入均单列。
- 未发布；等明确授权。
