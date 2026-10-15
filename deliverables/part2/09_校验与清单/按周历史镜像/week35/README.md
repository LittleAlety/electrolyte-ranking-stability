# Week 35 / Paper 交付件：论文主文收敛包

> 镜像目录 `E:\Claude Code\电解液溶剂-HB\成果输出（part2）\week35`。part1 覆盖 week1-week25，part2 从 week28（= WP1）起。
> 本目录由 `scripts/build_week35_deliverables.py` 确定性重建：源缺失即报错，
> `--check` 逐文件复核 SHA256。目录内**不含**任何 ORCA / xTB 原始输出与二进制 scratch。

## 内容

| 路径 | 内容 |
| --- | --- |
| `outputs/week35/paper_figure_map.csv` | 七图 -> 科学问题 -> 冻结资产（21 个 F 图资产） |
| `outputs/week35/paper_section_plan.csv` | 结果六节固定顺序与来源 |
| `outputs/week35/paper_claim_track.csv` | 10 条主结论 -> Track A / Track B / 待验证推断 |
| `outputs/week35/paper_number_lineage.csv` | 16 个主文数字的溯源（source sha256 + 复现命令） |
| `outputs/week35/paper_budget_overstatement.csv` | WP6 两条口径对照（tau_b-only 14/24 vs combined 21/24） |
| `outputs/week35/paper_supplementary_plan.csv` | F57 / F58 / T6a / T6b 的落点 |
| `outputs/week35/paper_gap_register.csv` | 13 条必须写出的边界声明（G01-G13） |
| `outputs/week35/paper_naming_compliance.csv` | 论文生成器措辞合规（0 禁用词 / 0 违规 / 待更新） |
| `outputs/week35/paper_checklist.csv` | 实施方案第七节 9 项验收清单（9/9 met） |
| `outputs/week35/paper_acceptance.csv` | 四个验收问题与反例 |
| `outputs/week35/paper_convergence.json` | 全量载荷 + 10 项自检 |
| `outputs/week35/paper_build_handoff.json` | 论文重建交接单（重建时按此逐项核对） |
| `outputs/week35/paper_summary.md` | 汇总报告 |
| `docs/57_week35_paper_convergence.md` | 周报 |
| `论文/build_paper_docx.py` | 论文生成器源码（在仓库之外，按相对形状镜像） |
| `outputs/week2/`、`week25/`、`week27/`、`gate1/`、`phase2_p1a/`、`week7/` | 主文数字指向的冻结输入 |
| `outputs/week28/` ... `outputs/week34/` | WP1-WP7 七个冻结载荷（供 C1-C8 与交叉核对） |
| `data/anchors/within_series_ordering.csv` | within-series 冻结 anchor（G11） |
| `src/electrolyte_ranking/paper.py`、`scripts/`、`tests/`、`config/` | 分析原语、生成器、回归测试与口径配置 |

## 本阶段最重要的一条

本阶段**不写 docx**：它把前七周的结果收敛成一份可校验的交接单 —— 七图各对应一个科学问题、
结果六节固定顺序、16 个主文数字逐条可溯源、13 条边界声明必须出现、10 条主结论沿用 Week 34
的 Track 标签。两条**不许只报一条**的口径：WP6 预算高估在 tau_b-only 下是 14/24、在 combined
下是 21/24。措辞扫描在本阶段**主动暴露**了一个待办：v6 正文尚未使用 R13 之后的 designated
措辞（当时 `naming_update_required = True`，扫描 1272 行）。该缺口已由 Week 36 的 v7 重建
补齐：当前扫描禁用词 0 处、naming_update_required = False。收敛载荷随论文生成器源码
实时扫描，v6 时点的记录保留在 Week 36 的 `SUBMISSION.json`（frozen_snapshots）。

## 纪律

- 零新增电子结构计算；零数据改动；不动任何论文源文件。
- 结论一律带轨道标签：Track A（computational decision stability）/ Track B（external
  reference validity）/ 待验证推断。
- 措辞：只用 `designated computational target` / `designated reference model`；
  `validated target` 在 Gate 1 闭合前禁用。
