# Week 30 / WP3 交付件：Li+ 配位条件态机制与状态身份

> 镜像目录 `E:\Claude Code\电解液溶剂-HB\成果输出（part2）\week30`。part1 覆盖 week1–week25，part2 从 week28（= WP1）起。
> 本目录由 `scripts/build_week30_deliverables.py` 确定性重建：源缺失即报错，
> `--check` 逐文件复核 SHA256。目录内**不含**任何 ORCA / xTB 原始输出与二进制 scratch。

## 内容

| 路径 | 内容 |
| --- | --- |
| `outputs/week30/coord_response.csv` | 逐 (对比, scope, 轴, 分子) 的条件态位移 + 状态身份 + QC |
| `outputs/week30/identity_split.csv` | 逐 (对比, 轴, 状态身份标签) 的位移分布 |
| `outputs/week30/ranking_impact.csv` | C0/C1/C2 的 Top-k 影响（含 n<2 未定义行） |
| `outputs/week30/descriptor_association.csv` | 只在 R13 主集合上的描述符关联 |
| `outputs/week30/mechanism_cases.csv` | 有 QC 支持的机制案例 |
| `outputs/week30/c1_to_c2_consistency.csv` | C1 -> C2 的机制判断一致性 |
| `outputs/week30/wp3_coordination_mechanism.json` | 全量载荷 + 8 项自检 |
| `outputs/week30/wp3_summary.md` | 汇总报告 |
| `outputs/week30/manifest.json` | 逐表行数与 SHA256 |
| `docs/52_week30_wp3_coordination_mechanism.md` | 周报 |
| `src/electrolyte_ranking/wp3.py` | WP3 分析原语（可复用） |
| `outputs/week28/evidence_master_table.json` | 冻结输入参照（Week 28 主表） |
| `scripts/`, `tests/` | 生成器与回归测试 |

## 本阶段最重要的一条

Li+ 配位除了改变 redox 数值，还会**改变被还原态的电子身份**：10 个还原态里 9 个外加电子
落在 Li 上。因此 C1 还原轴的排序必须在 state-identity 分层之后才可解释 —— 这是
observable identity failure，而不是 ranking instability；把它当成「分子被还原的难度」是误读。

## 复核方式

```powershell
cd 电解液溶剂HB-Code
.venv\Scripts\python.exe scripts\build_week30_wp3_coordination_mechanism.py --check
.venv\Scripts\python.exe -m pytest tests/test_week30_wp3_coordination_mechanism.py -q
.venv\Scripts\python.exe scripts\build_week30_deliverables.py --check
```

## 限制（与结论一起读）

- 零新增电子结构计算；Gate 1 仍 NOT CLOSED，本阶段不提供任何外部有效性支持。
- C1 声明 core 18、实际有值 10（`PC`/`EMC` 无 `[LiM]+` 对象），是最该先补的计算缺口。
- 描述符关联 n=6，仅探索性；绝不把 `Li_centered` 样本并入分子还原的连续回归。
- `C0_to_C1 / primary / reduction` 只有 1 个候选，配不成 pair，显式记为未定义。
- `state_registry` 里同一 `state_id` 有多条 motif/构象记录，QC 可能不一致；SL 的 C1 氧化态
  带一条 `execution_failed / geometry_failed` 记录，已在 `coord_response.qc_flags` 如实上报。
