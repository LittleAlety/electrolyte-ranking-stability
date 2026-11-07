# Week 33 / WP6 交付件：最小昂贵信息预算（RQ4 后半）

> 镜像目录 `E:\Claude Code\电解液溶剂-HB\成果输出（part2）\week33`。part1 覆盖 week1–week25，part2 从 week28（= WP1）起。
> 本目录由 `scripts/build_week33_deliverables.py` 确定性重建：源缺失即报错，
> `--check` 逐文件复核 SHA256。目录内**不含**任何 ORCA / xTB 原始输出与二进制 scratch。

## 内容

| 路径 | 内容 |
| --- | --- |
| `outputs/week33/al_protocol_audit.csv` | 逐 target 的协议与目标尺度审计（含 regret 容忍值来源） |
| `outputs/week33/budget_curves.csv` | n_T → τ_b / overlap / regret 的 median 与 2.5/97.5 |
| `outputs/week33/curve_reconciliation.csv` | 冻结曲线 vs 逐 repeat 重算的逐格残差 |
| `outputs/week33/budget_to_threshold.csv` | median τ_b 首次达到 0.80 / 0.90 的 n_T |
| `outputs/week33/success_criteria.csv` | 逐格的「多数重复」达标比例 |
| `outputs/week33/success_budget.csv` | 中位数曲线 vs 多数重复两条口径的预算 |
| `outputs/week33/strategy_comparison.csv` | 非随机策略 vs random 的配对胜负率 |
| `outputs/week33/family_coverage.csv` | 已查询集合覆盖的家族数（池内覆盖代理） |
| `outputs/week33/holdout_vs_inpool.csv` | 池内端点 vs 静态 LOFO；声明 family-held-out 不可用 |
| `outputs/week33/wp6_acceptance.csv` | 四个验收问题的结论与证据 |
| `outputs/week33/wp6_active_learning.json` | 全量载荷 + 10 项自检 |
| `outputs/week33/wp6_summary.md` | 汇总报告 |
| `docs/55_week33_wp6_active_learning_budget.md` | 周报 |
| `src/electrolyte_ranking/wp6.py` | WP6 分析原语（可复用） |
| `outputs/week7/stage8_*` | 冻结输入参照（Stage 8 replay 曲线 / 逐重复 / 轨迹 / 台账） |
| `outputs/week7/stage7_ml_results.csv` | 静态 held-out（LOFO）参照 |
| `scripts/`, `tests/` | 生成器与回归测试 |

## 本阶段最重要的一条

达标必须在**多数重复**中成立，而不是只在中位数曲线上成立：24 个 (target, 策略) 组合里有
**14 个**的中位数曲线比「多数重复」更早达标 —— 只看中位数曲线会低估所需的昂贵标签数。
另一条同样重要：冻结 replay 只有**池内插值**口径，池内端点 τ_b 恒为 1.0（自检端点，不是成绩），
而静态 LOFO 参照最高只有 0.843。family-held-out 的主动学习曲线**不可用**，本阶段不做外推。

## 复核方式

```powershell
cd 电解液溶剂HB-Code
.venv\Scripts\python.exe scripts\build_week33_wp6_active_learning_budget.py --check
.venv\Scripts\python.exe -m pytest tests/test_week33_wp6_active_learning_budget.py -q
.venv\Scripts\python.exe scripts\build_week33_deliverables.py --check
```

## 限制（与结论一起读）

- 零新增电子结构计算，零重跑 acquisition；Gate 1 仍 NOT CLOSED。
- core set 只有 18（C 任务 10）个分子，每 target 只有 15（C 为 7）个预算点；
  20 次重复的 2.5/97.5 百分位本身很粗，只比较方法的相对行为。
- 成功标准是内部操作性标准，未经外部校准，不得读成「真实项目需要买多少张 DFT」。
- posterior sampling 来自 GPR 后验协方差（样本 256），未做 uncertainty calibration。
