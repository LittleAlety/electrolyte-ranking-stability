# F54 图清单 · Week 25 · §24 Figure 1 二维层级图（双轴 + 外部参考层）

## 图件

| 项 | 值 |
|---|---|
| 文件名 | outputs/figures/F54_two_axis_hierarchy.png |
| 尺寸 | 6.3 × 6.35 in @ 200 dpi（1260 × 1270 px） |
| 对应 | 核心文件 v2 §24 Figure 1（L1449–1461）；论文/build_paper_docx.py 图 2 |
| 布局 | 纵轴 Axis A = proxy 层级（P0 → P1 → P2）；横轴 Axis B = 条件态层级（C0 → C1 → C2）；右侧单列外部参考层 R_gas / R_sol / R_env |
| 生成脚本 | scripts/make_w25_figure_f54_two_axis_hierarchy.py |
| 图 sha256 | accc74661564510efd0ca5992997862c5e319a229a20035ef79e261daa9d1038 |
| 复现方式 | python scripts/make_w25_figure_f54_two_axis_hierarchy.py --check（解算全部数字 + 内存重渲染 + 逐像素比对 + 清单逐字节比对） |
| 字体 | Microsoft YaHei / SimHei，axes.unicode_minus=False（照抄 make_w24_flowchart.py） |
| 配色 | 与 make_w24_flowchart.py / analyze_w25_figure_f53.py 同族：INK/ACCENT/WARN/OK/ALT/MUTED/GRID |

## 输入文件与 sha256

| 输入 | sha256 |
|---|---|
| outputs/week24_corealign/audit_tables.json | 60947a47af12ffbcf057294c19fbc2537a7ac517618a5641ea545ecaf1d620d1 |
| outputs/week22_hardening/broad_pool_demo.json | 670d067f8b74380f258d52e03c658d1c86bc233c526a35d77097101fa34fc6f0 |
| outputs/week5/c1_li_coordination_summary.json | 772d35d250312382829a74fc6b07dd8fa980a88eaffb392fe750d5038f1a5022 |
| outputs/week5/c1_summary.json | 0fe14aa91e1cdd6aeb1860a6d590ab4b169d78a68c5ba27ba024a3bef58da530 |
| outputs/week25/gate1_oxidation.json | d4d0b7d65d5dd344c22b6c3465b4f192753962a335eb5042f44c042e4eac14c1 |
| outputs/week9/stage10_ladder.json | 3eb6b36d5622ec0e3147dd827a6437aabac2ea38c53936fddc974e85376ac3cf |
| outputs/week4/p1_core_set_summary.json | b941d7fb1124900c5e148c6108478c0f00395e9430ee59da291bca878db42809 |
| outputs/week25/anchor_ingest_provenance.json | 1e14e0e9cad0fc3c57c2f270aef792ba3a3739796ace503ee208702d069a45bf |
| outputs/week23/shell3_xtb_sign_test.json | 56976591123c0e3cdd1ed287e47d3773c90ffe2be42a51f95a1276236d6d70c5 |
| outputs/week2/solution_anchor_audit.json | bec6f71270fac92066cfe1cc9239e012d2e595f48c84fa1ec233d3b111e34719 |
| outputs/week8/stage9_results.json | f783b564b1b8a42dfdb2e02a633ce80e7c660e9b6a23f98f22959377c536b012 |
| data/anchors/gas_phase_anchors.csv | a957ef0126efb817d115d4e0ed663207e401e42b5e6e63ffbb78942660c347b0 |

## 图上每个数字的来源（按点路径解析，脚本内硬断言守卫）

| 图上元素 | 值 | 来源文件 · 字段 |
|---|---|---|
| P0×C0 格点 | core 18 + broad 40 | week22_hardening/broad_pool_demo.json · meta.core_n ｜ week22_hardening/broad_pool_demo.json · meta.broad_n |
| P0/P1/P2×C0 格点 | n = 18（core） | week4/p1_core_set_summary.json · n_molecules |
| C1 列分子数 | n = 10（motif 12） | week5/c1_li_coordination_summary.json · len(molecules) ｜ week5/c1_li_coordination_summary.json · n_motifs |
| C1×P2 格点 | n = 10 | week5/c1_summary.json · delta_ip_smd_ev.n |
| C1×P0 格点（xTB 对照） | 12 motif | week5/c1_li_coordination_summary.json · len(li_min_distance_xtb_vs_dft) |
| C2 列 1:2 校核 | n = 10 | week9/stage10_ladder.json · ladder[C1_to_C2,native].n |
| C2 第三壳 targeted | 14 作业 | week23/shell3_xtb_sign_test.json · n_jobs |
| C0→C1 氧化位移（脚注） | 4.89 eV | week9/stage10_ladder.json · ladder[C0_to_C1,oxidation,native].shift_mean_ev |
| R_gas | 39 行 / 26 物种 | data/anchors/gas_phase_anchors.csv · data rows ｜ data/anchors/gas_phase_anchors.csv · unique species |
| R_sol | 31 行（全部 est） | week2/solution_anchor_audit.json · summary.rows_total |
| R_env | 无落盘数值（Phase IV） | week24_corealign/audit_tables.json · tables.phase1_not_done.rows[R_env].done |
| 锚点 ① 氧化 | 14 行（7 行属 core 18） | week25/anchor_ingest_provenance.json · n_oxidation_rows ｜ week25/anchor_ingest_provenance.json · n_core_set_oxidation |
| 锚点 ① 还原旁证 | 3 行 | week25/anchor_ingest_provenance.json · n_reduction_rows |
| 锚点 ② tau_b | 0.4286 | week25/gate1_oxidation.json · frozen_verdict.tau_b |
| 锚点 ② n_pairs | 21 | week25/gate1_oxidation.json · frozen_verdict.n_pairs |
| 锚点 ② ok | False | week25/gate1_oxidation.json · frozen_verdict.ok |

## 格点状态（实心 = 已算 / 斜纹 = 仅 targeted / 留白 = 未算）

| 格点 | 状态 | 内容 |
|---|---|---|
| P0×C0 | 实心 | GFN2-xTB Koopmans 标量代理；core 18 + broad 40 |
| P1×C0 | 实心 | r2SCAN-3c 气相 ΔSCF 垂直量；n = 18 |
| P2×C0 | 实心 | r2SCAN-3c + CPCM/SMD（乙腈）；n = 18 |
| P1×C1 | 实心 | r2SCAN-3c 气相 [LiM]+；n = 10 |
| P2×C1 | 实心 | r2SCAN-3c + SMD [LiM]+；n = 10（还原轴决策载体） |
| P0×C1 | 斜纹 | 仅 GFN2-xTB 级几何 / 距离对照，非 redox 臂；12 motif |
| P1×C2 | 斜纹 | 仅 targeted 敏感性检验：[Li(M)2]+ 1:2 校核 n = 10；第 3 壳仅 EC @ GFN2-xTB |
| P0×C2 | 留白 | 未算（可定义 ≠ 已计算） |
| P2×C2 | 留白 | 未算（可定义 ≠ 已计算） |

## 图注（可直接引用）

图 F54 双轴模型层级与外部参考层。纵轴 Axis A 为 proxy / 电子结构层级（P0 廉价标量代理 = GFN2-xTB Koopmans → P1 气相分子 redox 热力学 = r2SCAN-3c ΔSCF → P2 固定背景连续介质 = CPCM/SMD 乙腈）；横轴 Axis B 为环境 / 条件态层级（C0 自由分子态 → C1 Li+ 配位条件态 [LiM]+ → C2 显式微溶剂化 [Li(M)2]+）；最右列单列外部参考层 R_gas / R_sol / R_env，明确不属于计算层级。实心格为本项目实际计算过的组合，斜纹格为仅 targeted / 敏感性检验，留白格为未计算——「可定义」不等于「已计算」。

## 复现命令

    .venv\Scripts\python.exe scripts\make_w25_figure_f54_two_axis_hierarchy.py
    .venv\Scripts\python.exe scripts\make_w25_figure_f54_two_axis_hierarchy.py --check

## 纪律声明

- 零新增电子结构计算；全部数值来自仓库既有 JSON / CSV 产物，图上无硬编码数字。
- 未改动 论文/、成果输出/、scripts/build_deliverables.py、scripts/build_week25_deliverables.py；未 git commit。
- 只新建 scripts/make_w25_figure_f54_two_axis_hierarchy.py、outputs/figures/F54_two_axis_hierarchy.png、outputs/week25/F54_manifest.md。
