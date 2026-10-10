# 方案 11：剩余生产成本情景（低 / 中 / 高）

> 由 `scripts/wp_production/build_wp2_cost_scenarios.py` 生成；零新增电子结构计算，只汇总已登记台账。
> 口径：`wall hours = core-hours / (workers x 4)`；core-hours 与并发无关。

## 已测作业（13 条生产腿）

| 类别 | n | min | median | p90 | max | 单位 |
| --- | --- | --- | --- | --- | --- | --- |
| free_cation_def2TZVPD | 4 | 11.646 | 14.696 | 18.406 | 18.406 | core-hour |
| free_neutral_def2TZVP | 4 | 4.373 | 6.051 | 8.233 | 8.233 | core-hour |
| free_neutral_def2TZVPD | 1 | 6.860 | 6.860 | 6.860 | 6.860 | core-hour |
| li_complex_def2TZVPD | 4 | 8.650 | 10.851 | 15.354 | 15.354 | core-hour |

## 待补 7 条腿的情景

| 分子 | 态 | 类别 | 实测类别? | low | mid | high | 口径 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| DMC | M_tzvpd | free_neutral_def2TZVPD | true | 6.860 | 6.860 | 6.860 | class median (n=1) |
| EMC | M_tzvpd | free_neutral_def2TZVPD | true | 6.860 | 6.860 | 6.860 | class median (n=1) |
| EMC | LiM_plus | li_complex_def2TZVPD | true | 8.650 | 10.851 | 15.354 | class median (n=4) |
| EMC | LiM_2plus | li_complex_def2TZVPD | true | 8.650 | 10.851 | 15.354 | class median (n=4) |
| GBL | LiM_2plus | li_complex_def2TZVPD | true | 8.650 | 10.851 | 15.354 | class median (n=4) |
| SL | M_tzvpd | free_neutral_def2TZVPD | true | 6.860 | 6.860 | 6.860 | class median (n=1) |
| SL | LiM_2plus | li_complex_def2TZVPD | true | 8.650 | 10.851 | 15.354 | class median (n=4) |

| 情景 | core-hours | 墙上时间 @2 worker | @3 worker | @4 worker |
| --- | --- | --- | --- | --- |
| low | 55.177 | 6.90 h | 4.60 h | 3.45 h |
| mid | 63.983 | 8.00 h | 5.33 h | 4.00 h |
| high | 81.996 | 10.25 h | 6.83 h | 5.12 h |

* `li_complex_def2TZVPD` 目前没有任何实测腿，因此该类的 low / mid 都用**声明下界**（最大已测腿）而不是类别最小值；high 取该下界的 2 倍。第一条 Li 腿落地后应替换。

## 分项成本（方案 11 要求先检查 Opt / Freq / SP）

* 固定几何单点：pilot 与 WP1 审计分别有 60 / 160 条实测；合并中位 `0.059167` core-hour/SP。
* 只跑频率（freq-only）：实测 1 条（`C01|M|orca_freq`，1.254556 core-hour）。
* 只做优化（opt-only）：唯一一条是 `A161`（r2SCAN-3c），方法口径与生产腿不同，不能当作 wB97X-D4 的 Opt 成本。
* 生产腿是 Opt + NumFreq 联合作业，Opt 与 Freq 无法从同一作业的墙上时间里拆分，本条如实登记而不估算。

## 绝对成本三项（四分子闭环后按实测台账现算；闭环前留空并标 MISSING）

* 闭环状态：尚未闭环；绝对成本三项 留空并标 MISSING。

| item | status | note |
| --- | --- | --- |
| cpu_core_hours | MISSING | 项目级 allocated core-hours（不是 process CPU time）：四分子 13/20 条腿闭环后按现算填入，口径 = 方法审计 + pilot + 生产 + 靶向复核四个逐作业台账里 299 条带 core-hours 记录的作业之和；闭环前留空，不拿已跑的那部分作业冒充 headline 数。 |
| p90_job_cost | MISSING | 逐作业 core-hours 的最近秩 p90（小样本下等于最大值，不插值假装样本充足）；逐类中位 / p90 另见 outputs/physics_completion/cost/remaining_cost_scenarios.csv；闭环前留空。 |
| frequency_only_cost | MISSING | 只做频率的作业（phase=orca_freq，1 条，C01|M|orca_freq = wB97X-D4/def2-TZVP SMD NumFreq）的中位 core-hours；闭环前留空。 |

## 历史口径

* `outputs/week25/compute_budget_ledger.json` 的 `cpu_core_hours_available=false` 描述的是 week25 时的仓库；
  自本批次起 allocated core-hours 已逐作业记录。按方案 13「历史产物不被覆盖」不改写该文件。
