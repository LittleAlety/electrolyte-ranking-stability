# Week 24（W24-C）计划 —— 核心文件对齐补齐（core-file alignment）

- 上游依据：`核心文件/ranking-electrolyte-materials-v2.md`（29 章）与 `ranking-electrolyte-materials-reading-list.md`（Part I / Part II）。
- 触发问题：对照核心文件逐条核查"已承诺 vs 论文已呈现"，发现**数据已算、论文未写**的系统性缺口。
- 命名：既有 `week22`(Stage 23)、`week22_hardening`(W22-H)、`week23`(Stage 24)，本周次落盘命名空间为 `week24_corealign`（W24-C），不覆盖既有产物。
- 唯一变量纪律：本周**零新增电子结构计算**，只做既有产物蒸馏、论文文本补齐与数据统一。

## 1. 缺口（已核实）

| 编号 | 核心文件条款 | 项目实际状态 | 论文现状 | 处置 |
| --- | --- | --- | --- | --- |
| G1 | §12 Δ-learning 定义；§13 direct vs Δ-learning；§23 第 9 条；§24 图 6 | `outputs/week7/stage7_ml_results.json`（288 行，random/group/LOFO × direct/shift × 6 模型 × 5 seeds） | **完全缺失** | 新增 §3.13，嵌 `F16` |
| G2 | §14 n_T→{τ_b,O_k,R_k}；§14.3 ranking-aware acquisition；§23 第 11 条；§24 图 7 | `outputs/week7/stage8_al_curves.csv`（296 行，4 baseline × 20 repeats，含 2.5/97.5 分位） | **完全缺失** | 新增 §3.14，嵌 `F17` |
| G3 | §22 情形 A–G | `stage10_ladder.json:verdicts`（A–G 已判决） | 未认领 | 新增 §5.1 分支认领表 |
| G4 | §23 最小成果判据 11 条 | `stage10_ladder.json:minimum_outcome_checklist`（11 条，含 PARTIAL） | 未呈现 | 新增 §5.2 自查表 |
| G5 | §11 feature-cost accounting；"所有 ML 表格必须含 feature_cost_level" | `outputs/week7/feature_manifest.json:feature_cost_levels`（X0/X1/X2） | 未显式列出 | 新增 §2.7 |
| G6 | §25.1/§25.2 不把 X 当创新 | 论文引言无对齐声明 | 缺失 | 新增 §5.3 |
| G7 | RL Part II 方法依据（GFN2-xTB / qRRHO / speciation / multi-fidelity / bootstrap） | 项目实际使用，但未被引用 | 未引用 | 补引 + §5.4 映射表 |
| G8 | §10.2 selection regret / §10.3 threshold decision error | `stage7/stage8` 已算 `selection_regret_*` | 未报告 | 并入 G1/G2 |
| H1 | ——（自审发现） | 论文 §4 结语第一段拼接了 A2 修订前的旧句"…τ_b 反而为 0.73"，与 A2 新口径自相矛盾 | bug | 删除旧残句 |

## 2. 工作包与并行分工

| 包 | 负责 | 写作用域 |
| --- | --- | --- |
| P1 Stage 7 蒸馏 | agent Euler | `outputs/week24_corealign/ml_*`、`scripts/analyze_w24_ml.py` |
| P2 Stage 8 蒸馏 | agent Sartre | `outputs/week24_corealign/al_*`、`scripts/analyze_w24_al.py` |
| P3 分支/判据/成本/RL 映射 | agent Meitner | `outputs/week24_corealign/core_alignment.*`、`scripts/analyze_w24_alignment.py` |
| P4 论文补齐与重建 | 主代理 | `论文/build_paper_docx.py` → `_v3.docx/.pdf` |
| P5 统一数据与交付 | 主代理 | `成果输出/统一数据文档.md`、`成果输出/week24_corealign/` |

## 3. 验收标准

1. 论文新增 §2.7、§3.13、§3.14、§5.1–§5.4；TOC 与页眉无乱码；英文摘要完整落在第 1 页。
2. 所有新增数值可追溯到脚本 + 输入 SHA256；`--check` 幂等复核通过。
3. §23 十一条判据在论文中均有落点；PARTIAL 项（溶液锚点 Gate 1）如实保留、不粉饰。
4. `成果输出/统一数据文档.md` 增列 W24-C 节与图索引；`成果输出/week24_corealign/` 含 `SHA256SUMS` 与 `verification.json`。
