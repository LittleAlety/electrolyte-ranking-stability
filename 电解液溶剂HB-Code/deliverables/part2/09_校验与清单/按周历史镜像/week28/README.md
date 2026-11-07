# Week 28 / WP1 交付件：统一科学证据主表

> 镜像目录 `E:\Claude Code\电解液溶剂-HB\成果输出（part2）\week28`。part1 覆盖 week1–week25，part2 从本阶段（week28 = WP1）起。
> 本目录由 `scripts/build_week28_deliverables.py` 确定性重建：源缺失即报错，
> `--check` 逐文件复核 SHA256。目录内**不含**任何 ORCA / xTB 原始输出与二进制 scratch。

## 内容

| 路径 | 内容 |
| --- | --- |
| `outputs/week28/*.csv` | 六张主表：molecule_registry / state_registry / property_table / pairwise_table / decision_table / cost_table |
| `outputs/week28/evidence_master_table.json` | 全量载荷，含六项一致性审计的机器可读证据 |
| `outputs/week28/evidence_master_table.md` | 汇总报告 |
| `outputs/week28/data_dictionary.md` | 数据字典（与表结构同步生成） |
| `outputs/week28/sample_flow.md` | 样本流转图 + 被规则挡掉的样本 |
| `outputs/week28/manifest.json` | 逐表行数与 SHA256 |
| `docs/50_week28_wp1_evidence_table.md` | 周报 |
| `config/*.yaml` | 冻结定义与预注册（口径来源） |
| `outputs/week6/stage6_decision_stability.json` | 复核参照：冻结的 pair 数字 |
| `outputs/week4/p2_decision_stability.json` | 复核参照：P2a 命名映射 |
| `scripts/`, `tests/` | 生成器与回归测试 |

## 本阶段最重要的一条

主表在 `all` scope / `z_only` / `z = 1.0` 下**逐位复现**了 Week 6 已冻结的 pair 数字
（354 个 pair，最大绝对误差 `0.000e+00` eV，mask 不一致 0）。也就是说这张表不是并行的一套
定义，而是已发表数字的同一个对象；`verification.json` 的
`week6_numbers_reproduced_bit_for_bit` 断言就在检查这一点。

## 复核方式

```powershell
cd 电解液溶剂HB-Code
.venv\Scripts\python.exe scripts\build_week28_evidence_table.py --check
.venv\Scripts\python.exe -m pytest tests/test_week28_evidence_table.py -q
.venv\Scripts\python.exe scripts\build_week28_deliverables.py --check
```

## 限制（与结论一起读）

- 零新增电子结构计算；Gate 1 仍 NOT CLOSED，本阶段不提供任何外部有效性支持。
- 昂贵层 n = 18 / 12 / 10；`primary` scope 下 C0→C1、C1→C2 的还原轴闸门后只剩 1 个候选，
  该轴的 pair 行显式 `skipped`，不得读成「稳定」或「零反转」。
- **分母陷阱**：`scope='all'` 的 `n_molecules` 随对比变化（18 / 12 / 10），`decision_table` 里
  `f_unresolved` / `jaccard` / `overlap` 跨行不可比；每行请看 `common_set_label`，
  JSON 的 `coverage` 块给出 declared / available / used 对账。
- **`C1` 声明 core 18、实际 10**：`PC` / `EMC` 没有 `[LiM]+` 对象，主表记为 `missing`（16 行），
  这是下一阶段最该先补的计算缺口。
- `not_converged` 词表齐备但当前零命中（失败作业落在非主 motif 上）。
- `P0` 与 `P1a` 的 `wall_seconds = 0.0` 表示来源蒸馏表**未记录**，不是零成本。
