# Week 32 / WP5 交付件：Δ-learning 与跨家族泛化（RQ4 前半）

> 镜像目录 `E:\Claude Code\电解液溶剂-HB\成果输出（part2）\week32`。part1 覆盖 week1–week25，part2 从 week28（= WP1）起。
> 本目录由 `scripts/build_week32_deliverables.py` 确定性重建：源缺失即报错，
> `--check` 逐文件复核 SHA256。目录内**不含**任何 ORCA / xTB 原始输出与二进制 scratch。

## 内容

| 路径 | 内容 |
| --- | --- |
| `outputs/week32/feature_cost_audit.csv` | 逐 (任务, 特征集) 的成本审计（X2 硬约束） |
| `outputs/week32/cross_family_generalization.csv` | random / group / LOFO 与乐观偏差 |
| `outputs/week32/delta_vs_direct.csv` | 最佳 direct vs 最佳 Δ-learning |
| `outputs/week32/screening_conversion.csv` | MAE 排名与筛选排名是否一致 |
| `outputs/week32/state_identity_stratification.csv` | C 任务样本的状态身份分层（R13） |
| `outputs/week32/oof_metrics_reconciliation.csv` | 重算 vs 冻结的逐组合对账 |
| `outputs/week32/wp5_acceptance.csv` | 验收问题的结论与证据 |
| `outputs/week32/wp5_delta_learning.json` | 全量载荷 + 8 项自检 |
| `outputs/week32/wp5_summary.md` | 汇总报告 |
| `outputs/week32/manifest.json` | 逐表行数与 SHA256 |
| `docs/54_week32_wp5_delta_learning.md` | 周报 |
| `src/electrolyte_ranking/wp5.py` | WP5 分析原语（可复用） |
| `outputs/week7/stage7_ml_results.csv` | 冻结输入参照（Stage 7 指标表） |
| `scripts/`, `tests/` | 生成器与回归测试 |

## 本阶段最重要的一条

「数值变好」与「选择变好」不等价：组内 6 个模型上，MAE 最优同时是 τ_b 最优的只有 19/48 个组，
MAE 与 τ_b 的秩相关在有 2 个组里甚至是正的。只看 MAE 会选出对材料筛选没有帮助的模型。
另外，冻结的 Stage 7 预测表按 ~6 位小数存储，排序型指标（τ_b / regret）在存储分辨率
以内的近并列处不可复现 —— 本阶段把这条残差逐条归因（7 个 τ_b 分歧、1 个 regret 离群，
全部落在 35 个近并列组合上），而不是放宽容差抹掉。

## 复核方式

```powershell
cd 电解液溶剂HB-Code
.venv\Scripts\python.exe scripts\build_week32_wp5_delta_learning.py --check
.venv\Scripts\python.exe -m pytest tests/test_week32_wp5_delta_learning.py -q
.venv\Scripts\python.exe scripts\build_week32_deliverables.py --check
```

## 限制（与结论一起读）

- 零新增电子结构计算；Gate 1 仍 NOT CLOSED，本阶段不提供任何外部有效性支持。
- core set 只有 18 个分子（C 任务 10 个）；LOFO 每一折是「预测一个从未见过的家族」，
  某些家族只有 1 个分子，该折等价于单点外推。
- C 任务还原轴经状态身份闸门后只剩 SN（n=1），只能作探索性分析。
- 本阶段是对 Stage 7 冻结预测的复算与再解释，不是重训。
