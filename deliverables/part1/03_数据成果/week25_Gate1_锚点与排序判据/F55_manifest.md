# F55 图清单 · Week 25 · §24 Figure 5 配位位移 × 描述符标签（补全）

## 图件

| 项 | 值 |
|---|---|
| 文件名 | outputs/figures/F55_coord_descriptor_tags.png |
| 尺寸 | 6.3 × 6.6 in @ 200 dpi（1260 × 1320 px） |
| 布局 | (a) 逐分子两轴配位位移 + 标签；(b) Spearman ρ 热图（精确置换 p）；(c) 标签分层中位数（齿数 / donor 元素 / donor_count / 态身份）；(d) dIP vs tpsa 与 dIP vs donor_count 散点 |
| 生成脚本 | scripts/analyze_w25_figure_f55.py |
| 统计负载 | outputs/week25/figure_f55_stats.json（唯一数据负载；图上无硬编码数值） |
| 子集 | C1 n = 10；置换数 3628800 |
| 复现方式 | python scripts/analyze_w25_figure_f55.py --check（重算 + 逐像素 / 逐字节比对） |
| 字体 | Microsoft YaHei / SimHei，axes.unicode_minus=False（照抄 make_w24_flowchart.py） |

## 输入文件与 sha256

| 输入 | sha256 |
|---|---|
| data/metadata/core_set.csv | 630b0ee8c09dc4141124e335181572bf27a63f297a8df95f9c774683a10cf91b |
| outputs/week5/c1_coord_shifts.csv | 1f9597ba376ffb19610e855e4d83a4e2360a8ac5009209cf764be91008634b5d |
| outputs/week5/c1_state_identity.csv | cc035b941936842a739d2c23833552acfa3c010283e280276849e0be8d6d1aa3 |
| outputs/week5/c1_summary.json | 0fe14aa91e1cdd6aeb1860a6d590ab4b169d78a68c5ba27ba024a3bef58da530 |
| outputs/week5/c1_li_coordination_summary.json | 772d35d250312382829a74fc6b07dd8fa980a88eaffb392fe750d5038f1a5022 |
| outputs/week9/stage10_ladder.json | 3eb6b36d5622ec0e3147dd827a6437aabac2ea38c53936fddc974e85376ac3cf |
| outputs/week23/shell3_xtb_sign_test.json | 56976591123c0e3cdd1ed287e47d3773c90ffe2be42a51f95a1276236d6d70c5 |

## 输出文件与 sha256

| 输出 | sha256 |
|---|---|
| outputs/week25/figure_f55_stats.json | 8ba005f6b2071df60d2acb04baa6d495f62149ae2bc1a15d89aefe7c50e3f25f |
| outputs/week25/figure_f55_stats.md | 70ed3dfb55e9269c588f278a0fcecdc196b7a87b3067c237166c79f07d1ca534 |
| outputs/figures/F55_coord_descriptor_tags.png | c549be55a5841f28becf16b822d2dd9b5b1f29e5d0a9024cf5ccd01d20fefd91 |

## 关键数字（脚本内硬断言守卫）

| 元素 | 值 | 来源文件 · 字段 |
|---|---|---|
| C0→C1 氧化位移均值（native/common-10，n=10） | 4.8872 eV | outputs/week9/stage10_ladder.json · ladder[C0_to_C1,oxidation,native].shift_mean_ev |
| C0→C1 还原位移均值（-dEA 约定） | -6.5782 eV | outputs/week9/stage10_ladder.json · ladder[C0_to_C1,reduction,native].shift_mean_ev |
| 重算氧化均值（逐分子） | 4.8872 eV | outputs/week5/c1_coord_shifts.csv · d_ip_ev（is_primary） |
| 重算还原均值（-dEA） | -6.5782 eV | outputs/week5/c1_coord_shifts.csv · d_ea_ev（is_primary） |
| 氧化位移 sd（ladder，ddof=1） | 0.5946 eV | outputs/week9/stage10_ladder.json · ladder[C0_to_C1,oxidation,native].shift_std_ev |
| C1 子集分子数 | 10 | outputs/week5/c1_li_coordination_summary.json · len(molecules) |
| C1 motif 数 | 12 | outputs/week5/c1_li_coordination_summary.json · n_motifs |
| 第三壳 targeted 作业 | 14 | outputs/week23/shell3_xtb_sign_test.json · n_jobs |

## 图注（可直接引用）

图 F55 配位位移与描述符标签的关系（§24 Figure 5 的 ΔΔG_coord–标签维度）。子集为具有 C1（Li+ 配位条件态）的 10 个分子；每个分子的氧化轴位移 dIP = IP([LiM]+) − IP(M) 与还原轴位移 dEA = EA([LiM]+) − EA(M) 取自 week5 的 C1 逐分子产物，标签取自 core_set.csv。(a) 按 dIP 升序列出逐分子两轴位移，右侧标注该分子的 Li 接触数 n_Li、donor 杂原子数 d 与二价阳离子态身份；(b) 7 个描述符与两条轴的 Spearman ρ，格内给出精确置换 p（n=10，全部 10! 种排列枚举，非正态近似）；(c) 按配位齿数 / donor 元素 / donor_count / 态身份分层的中位数与四分位距，n 标在右侧；(d) dIP 与 tpsa、donor_count 的散点。所有数值为小样本提示性证据：n=10，未作多重比较校正，不得表述为显著；ESP 描述符仓库内不存在（not_available_in_repo）；本图不改变任何既有判决。

## 复现命令

    .venv\Scripts\python.exe scripts\analyze_w25_figure_f55.py
    .venv\Scripts\python.exe scripts\analyze_w25_figure_f55.py --check

## 纪律声明

- 零新增电子结构计算；全部数值来自仓库既有产物（week5 C1 逐分子产物、core_set.csv、week9 ladder、week23 第三壳），图上无硬编码数字。
- 未改动 论文/、成果输出/、scripts/build_deliverables.py、scripts/build_week24_deliverables.py、scripts/build_week25_deliverables.py；未 git commit。
- 只新建 scripts/analyze_w25_figure_f55.py、outputs/figures/F55_coord_descriptor_tags.png、outputs/week25/figure_f55_stats.json、outputs/week25/figure_f55_stats.md、outputs/week25/F55_manifest.md。
