# 方案 11：剩余生产成本情景（低 / 中 / 高）

> 由 `scripts/wp_production/build_wp2_cost_scenarios.py` 生成；零新增电子结构计算，只汇总已登记台账。
> 口径：`wall hours = core-hours / (workers x 4)`；core-hours 与并发无关。

## 已测作业（20 条生产腿）

| 类别 | n | min | median | p90 | max | 单位 |
| --- | --- | --- | --- | --- | --- | --- |
| free_cation_def2TZVPD | 4 | 11.646 | 14.696 | 18.406 | 18.406 | core-hour |
| free_neutral_def2TZVP | 4 | 4.373 | 6.051 | 8.233 | 8.233 | core-hour |
| free_neutral_def2TZVPD | 4 | 3.695 | 6.805 | 8.397 | 8.397 | core-hour |
| li_complex_def2TZVPD | 8 | 7.627 | 11.515 | 15.354 | 15.354 | core-hour |

## 待补 0 条腿的情景

| 分子 | 态 | 类别 | 实测类别? | low | mid | high | 口径 |
| --- | --- | --- | --- | --- | --- | --- | --- |

**0 条待补腿**：注册的四分子 20 腿子集已全部落地（见 `closure/four_molecule_state_closure.csv`），因此本子集的剩余成本为 **0 core-hour**，逐腿情景表为空是「没有剩余」而不是「没有估算」。完整 48 态计划的剩余预算仍单列在 `cost_ledger.csv` 的 `main_production_state_structures`（planned）。

| 情景 | core-hours | 墙上时间 @2 worker | @3 worker | @4 worker |
| --- | --- | --- | --- | --- |
| low | 0.000 | 0.00 h | 0.00 h | 0.00 h |
| mid | 0.000 | 0.00 h | 0.00 h | 0.00 h |
| high | 0.000 | 0.00 h | 0.00 h | 0.00 h |

* 每个作业类别都至少有一条实测腿（待补 0 条），本轮没有任何数字来自声明下界。

## 分项成本（方案 11 要求先检查 Opt / Freq / SP）

* 固定几何单点：pilot 与 WP1 审计分别有 60 / 160 条实测；合并中位 `0.059167` core-hour/SP。
* 只跑频率（freq-only）：实测 1 条（`C01|M|orca_freq`，1.254556 core-hour）。
* 只做优化（opt-only）：唯一一条是 `A161`（r2SCAN-3c），方法口径与生产腿不同，不能当作 wB97X-D4 的 Opt 成本。
* 生产腿是 Opt + NumFreq 联合作业，Opt 与 Freq 无法从同一作业的墙上时间里拆分，本条如实登记而不估算。

## 绝对成本三项（四分子闭环后按实测台账现算；闭环前留空并标 MISSING）

* 闭环状态：四分子四态已齐备；绝对成本三项 已按实测台账填入。

| item | status | note |
| --- | --- | --- |
| cpu_core_hours | measured | 项目级 allocated core-hours（不是 process CPU time）：四分子 20/20 条腿闭环后按现算填入，口径 = 方法审计 + pilot + 生产 + 靶向复核四个逐作业台账里 314 条带 core-hours 记录的作业之和；闭环前留空，不拿已跑的那部分作业冒充 headline 数。 |
| p90_job_cost | measured | 逐作业 core-hours 的最近秩 p90（小样本下等于最大值，不插值假装样本充足）；逐类中位 / p90 另见 outputs/physics_completion/cost/remaining_cost_scenarios.csv；闭环前留空。 |
| frequency_only_cost | measured | 只做频率的作业（phase=orca_freq，1 条，C01|M|orca_freq = wB97X-D4/def2-TZVP SMD NumFreq）的中位 core-hours；闭环前留空。 |

## 历史口径

* `outputs/week25/compute_budget_ledger.json` 的 `cpu_core_hours_available=false` 描述的是 week25 时的仓库；
  自本批次起 allocated core-hours 已逐作业记录。按方案 13「历史产物不被覆盖」不改写该文件。
