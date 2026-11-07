# Week 36 结题提交：论文 v7 成品 + 全量镜像索引

> 镜像目录 `E:\Claude Code\电解液溶剂-HB\成果输出（part2）\week36`。part1 覆盖 week1-week25，part2 从 week28（= WP1）起。
> 本目录由 `scripts/build_week36_final_submission.py` 确定性重建：源缺失即报错，
> `--check` 逐文件复核 SHA256。**含二进制成品**（论文 .docx / .pdf），
> 但**不含**任何 ORCA / xTB 原始输出与 scratch。

## 内容

| 路径 | 内容 |
| --- | --- |
| `论文/电解液溶剂氧化还原描述符决策稳定性_结题论文_v7.docx` | 结题论文成品（24 张内嵌图 / 19 张表） |
| `论文/电解液溶剂氧化还原描述符决策稳定性_结题论文_v7.pdf` | 同上 PDF（Word 导出，非 LaTeX） |
| `论文/build_paper_docx.py` | 论文生成器源码（在仓库之外，按相对形状镜像） |
| `scripts/paper_v7_restructure_results.py` | v7 结果六节重排的一次性脚本（**勿重复执行**） |
| `scripts/paper_v7_patch_content.py` | v7 定义性表述 / 措辞 / 边界补充脚本（**勿重复执行**） |
| `work/check_paper.py` | 论文验收脚本（16 项：六节顺序 / G01-G13 / L01-L16 / 措辞 / 图表数 / 范围限定） |
| `work/week36_wp_mapping.json` | WP1-WP7 -> 论文节 -> 冻结载荷 的对照映射 |
| `work/week36_number_audit.md` | 论文 16 个主文数字的独立复算审计报告 |
| `SUBMISSION.json` | 结题提交单：v7 sha256 / 验收 16-16 / WP1-WP7 对照 / week28-35 索引 / 口径纪律 |
| `verification.json` | 本目录 12 项自检 |
| `docs/50...57` | WP1-WP7 周报 + Week 35 论文收敛周报 |
| `outputs/week35/paper_*.csv|json` | 论文主文数字 / 边界声明 / 验收清单的冻结载荷 |

## 本阶段最重要的一条

结题提交**只做冻结与交付，不做新计算**：零新增电子结构计算、零数据剔除、零阈值改动。
论文 v7 的每一处结构性改动都留下了可复算的证据 —— 六个结果节固定顺序、13 条边界声明
（G01-G13）、16 个主文数字（L01-L16）逐条钉住冻结源及其 sha256、`f_robust_inv = 0` 明确写为**定义性**结论（T6a z* = 0.7071067811865475 / T6b max_n_discordant_both = 0），
Gate 1 一律标为 **NOT CLOSED / NOT CLOSABLE**。Week 35 唯一的待办（v6 未使用 designated 措辞）
已在 v7 解决，本目录重跑验收脚本确认：禁用词 0 次、允许措辞 7 处。v7 重建同时让
week34 / week35 的派生扫描载荷随仓库刷新（D4），并把 v6 -> v7 的生成器溯源
（sha256 44c026c5… -> 89dd8811…，v6 原件保留为 论文/_backup_build_paper_docx_v6.py）
钉进 `SUBMISSION.json`。

## 复现

~~~
$env:PAPER_OUT = "E:/Claude Code/电解液溶剂-HB/论文/电解液溶剂氧化还原描述符决策稳定性_结题论文_v7.docx"
python 论文/build_paper_docx.py            # 需要带 python-docx 的解释器
python work/check_paper.py <v7.docx> 论文/build_paper_docx.py
.venv/Scripts/python.exe scripts/build_week36_final_submission.py --check
~~~

## 纪律

- 三层表述（模型事实 / 统计判定 / 材料意义）分列，不混写。
- 方向 `ox = IP`、`red = -EA`（均 maximise）；`sigma_ij = |d_lower - d_upper| / sqrt(0.5)`。
- 结论一律带轨道标签：Track A（computational decision stability）/ Track B（external reference
  validity）/ 待验证推断。
- 措辞：只用 `designated computational target` / `designated reference model`；
  `validated target` 在 Gate 1 闭合前禁用。`NOT CLOSABLE` 不等于 `NO SUCH DATA EXIST ANYWHERE`。
