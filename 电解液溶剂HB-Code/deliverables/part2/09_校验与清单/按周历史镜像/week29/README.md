# Week 29 / WP2 交付件：哪些电子结构与介质物理改变候选排序

> 镜像目录 `E:\Claude Code\电解液溶剂-HB\成果输出（part2）\week29`。part1 覆盖 week1–week25，part2 从 week28（= WP1）起。
> 本目录由 `scripts/build_week29_deliverables.py` 确定性重建：源缺失即报错，
> `--check` 逐文件复核 SHA256。目录内**不含**任何 ORCA / xTB 原始输出与二进制 scratch。

## 内容

| 路径 | 内容 |
| --- | --- |
| `outputs/week29/displacement_table.csv` | 逐 (对比, scope, 轴, 分子) 的 delta_i |
| `outputs/week29/family_displacement.csv` | 逐 (对比, 轴, family) 的 delta 分布 |
| `outputs/week29/shift_models.csv` | 三种解释模型 RMSE 与族内外方差分解 |
| `outputs/week29/decision_response.csv` | Top-k overlap / Jaccard / regret / 候选交换 |
| `outputs/week29/bootstrap_ci.csv` | 分子级 bootstrap 95% 区间 |
| `outputs/week29/ladder_incremental.csv` | 阶梯相对终端 P2a 的逐级信息增量 |
| `outputs/week29/ladder_additivity.csv` | 阶梯位移可加性自检 |
| `outputs/week29/wp2_physics_response.json` | 全量载荷 + 7 项自检的机器可读证据 |
| `outputs/week29/wp2_summary.md` | 汇总报告 |
| `outputs/week29/manifest.json` | 逐表行数与 SHA256 |
| `docs/51_week29_wp2_physics_response.md` | 周报 |
| `src/electrolyte_ranking/wp2.py` | WP2 分析原语（可复用） |
| `outputs/week28/evidence_master_table.json` | 冻结输入参照（Week 28 主表） |
| `scripts/`, `tests/` | 生成器与回归测试 |

## 本阶段最重要的一条

重算的 Top-k overlap / Jaccard / selection regret / tau_b / rho 与 Week 28 的
`decision_table` **逐位一致（最大绝对差 0.000e+00）**，说明 WP2 不是并行于主表的另一套
定义，而是同一对象上的物理机制补充。

## 复核方式

```powershell
cd 电解液溶剂HB-Code
.venv\Scripts\python.exe scripts\build_week29_wp2_physics_response.py --check
.venv\Scripts\python.exe -m pytest tests/test_week29_wp2_physics_response.py -q
.venv\Scripts\python.exe scripts\build_week29_deliverables.py --check
```

## 限制（与结论一起读）

- 零新增电子结构计算；Gate 1 仍 NOT CLOSED，本阶段不提供任何外部有效性支持。
- `P1v_to_P1a` 只有 12 分子且只有氧化轴；该轴的选择稳定性不能外推到 core18。
- `scope='all'` 的 n 随对比变化（18/12），跨行不可比；每行请看 `common_set_label`。
- `ROBUST_INVERSION` 恒为 0 是**结构性**的（z = 1.0 > 1/√2），不得读成「排序稳定」。
- bootstrap 以分子为单元，n=18/12 很小，区间较宽；区间用仓库自身的 tau_b 定义。
