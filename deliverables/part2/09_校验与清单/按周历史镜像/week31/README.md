# Week 31 / WP4 交付件：决策可识别性与筛选稳健性（RQ3）

> 镜像目录 `E:\Claude Code\电解液溶剂-HB\成果输出（part2）\week31`。part1 覆盖 week1–week25，part2 从 week28（= WP1）起。
> 本目录由 `scripts/build_week31_deliverables.py` 确定性重建：源缺失即报错，
> `--check` 逐文件复核 SHA256。目录内**不含**任何 ORCA / xTB 原始输出与二进制 scratch。

## 内容

| 路径 | 内容 |
| --- | --- |
| `outputs/week31/resolution_curve.csv` | 逐 (组, z) 的分辨率曲线 f_unresolved（lower/upper） |
| `outputs/week31/identifiability_summary.csv` | 三层评价汇总 + 与 Week 28 冻结值逐位对账 |
| `outputs/week31/structural_nontestability.csv` | 逐 (组, z) 的反向 pair / 稳健反转计数 |
| `outputs/week31/raw_ranking_changes.csv` | Case A：无阈值的原始排序变化 |
| `outputs/week31/selection_uncertainty.csv` | Case C：歧义区间抽样下的 Top-k 稳定性 |
| `outputs/week31/stratification_sensitivity.csv` | S1（score）vs S2（conservative）分层敏感性 |
| `outputs/week31/decision_classes.csv` | 验收交付表：确定选择 / 边界候选 / 证据不足 |
| `outputs/week31/wp4_decision_identifiability.json` | 全量载荷 + 10 项自检 |
| `outputs/week31/wp4_summary.md` | 汇总报告 |
| `outputs/week31/manifest.json` | 逐表行数与 SHA256 |
| `docs/53_week31_wp4_decision_identifiability.md` | 周报 |
| `src/electrolyte_ranking/wp4.py` | WP4 分析原语（可复用） |
| `outputs/week28/evidence_master_table.json` | 冻结输入参照（Week 28 主表） |
| `scripts/`, `tests/` | 生成器与回归测试 |

## 本阶段最重要的一条

`f_robust_inversion == 0` **不是**稳定性证据：在 `sigma = |d_upper - d_lower| / sqrt(2)` 的约定下，
只要 `z > 1/sqrt(2)`，反向 pair 就不可能两侧同时 resolved —— 全部 1326 个 pair 都标注为
`structurally_non_testable`。真正有信息的是「确定选择 / 边界候选 / 证据不足」的划分，
而它依赖不确定性假设与分层算法：k_fraction=0.2 时 15 组里有 12 组的 S1（score-lexicographic）
与 S2（conservative / resolved-only）给出不同的 Top-k 集合。

## 复核方式

```powershell
cd 电解液溶剂HB-Code
.venv\Scripts\python.exe scripts\build_week31_wp4_decision_identifiability.py --check
.venv\Scripts\python.exe -m pytest tests/test_week31_wp4_decision_identifiability.py -q
.venv\Scripts\python.exe scripts\build_week31_deliverables.py --check
```

## 限制（与结论一起读）

- 零新增电子结构计算；Gate 1 仍 NOT CLOSED，本阶段不提供任何外部有效性支持。
- 不确定性只有一个独立来源（两端模型输出的歧义区间）；来源不足处如实报为 sensitivity range。
- 「确定选择」是相对该不确定性假设与分层算法而言；换假设会改变结论。
- 每组 n 随对比变化（18/12/10/6），跨行不可比。
- 冻结的 `decision_table.selected_upper/lower` 列，其组内顺序来自 CPython set 迭代，无语义；
  Week 31 的 `selection_uncertainty.selected_upper/lower` 按数值降序，两者按集合对账。
