# 45 Week 25 追加 —— 对照核心文件要求的论文 v6 优化

- 生成日期：2026-10-02（Asia/Shanghai）
- 性质：**交付物修订**（论文源码 + 重建 docx/pdf）与随附说明。**零新增电子结构计算**；不改动任何冻结件、判据或数值。
- 修订对象（唯一真源）：`论文/build_paper_docx.py`（v5 → v6）。
- 对照对象（核心文件）：`核心文件/ranking-electrolyte-materials-v2.md`（§7.1、§17.1、§25.2、§26、§27、§28）。
- 上游依据：`docs/41_week25_corefile_gap_audit.md`（87 条逐条对照 + Top-8 优化项）、`docs/43_week25_corefile_figure_alignment.md`（§24 七图双向对齐）。
- 产物：`论文/电解液溶剂氧化还原描述符决策稳定性_结题论文_v6.docx` / `_v6.pdf`（35 页）。

---

## 1. 本轮定位：把「已在周报告登记、但未进论文正文」的结构性缺口补齐

`docs/41` 的 87 条对照判定为：已满足 63、部分满足 19、未满足 5。Top-8 优化项中第 1、2、3、5、7 项（规模偏差表、metadata 补列、二维层级图、计算预算台账、逐家族统计）已在 v5 落地；本轮处理**剩余的三类结构性缺口**（第 4、6、8 项）以及 `docs/43` 标出的唯一 PARTIAL（§24 Figure 4）：

1. §7.1 方法审计的两个维度（两种合理 DFT functional、≥2 基组/弥散变体）此前未在论文显式登记；
2. §17.1 微溶剂化 targeted check 的实际覆盖（候选数、四类抽样、化学计量）未声明；
3. §28 的推荐目录骨架与仓库实际路径不同构，缺等价映射；§27 的 Phase II–IV 未与论文表 13 对齐编号；
4. §24 Figure 4（robust rank-flow map）在本项目只能作语义替代，需在论文中明确登记为 negative result。

同时把 `docs/41` 中 P2/P4 两处「部分满足」补齐：§25.2 的增量与 §26 的科学意义此前只散见正文，未成逐条落点。

## 2. 论文改动（`论文/build_paper_docx.py`）

### 2.1 §5.3 创新边界：增补 §25.2 与 §26 的逐条落点

在原有「本文的增量有三 / 不声称的范围」两段后新增一段，把核心文件要求逐条落到小节：free/coordination 概念分离（2.2、3.5）；电子局域与态身份（3.5、5.6 表 12）；robust inversion 须超过方法不确定度（2.4、3.6）；随机插值与留一家族出外推分开（3.13）；特征成本记账（2.7）；外部锚点区分 model-to-model 保序与 accuracy（3.1、3.15）；主动学习针对材料决策（3.14）。§26 四条科学意义同理（3.1/3.6、3.11、2.4/3.6、3.8/3.15/5.1）。

### 2.2 §5.4 表 10：新增方法审计两行

- 「方法审计：两种合理 DFT functional 的敏感性」→ **部分使用**：以 GFN2-xTB ↔ r2SCAN-3c 的跨引擎对照与 P0′ ΔSCF 臂替代，**未引入第二个 DFT 泛函**；
- 「方法审计：≥2 基组 / 弥散变体」→ **已使用**：T5 弥散对照（r2SCAN 同泛函，def2-mTZVPP / def2-TZVPP / def2-TZVPD 三级；4 分子 × 中性/阴离子）。

### 2.3 §5.8 表 14：§24 Figure 4 明确登记为 negative result

原文只写「须并读一条负结果」；现改为：20 个（台阶 × 轴 × 口径）组合上 `f_robust_inv` 全为 0，本文未观测到任何**可画的**超阈值稳健翻转，故以未过滤的两轴位次迁移作语义替代，并在 §5.1 分支 C 与 §5.10 表 16 如实登记；图 6 的 Koopmans 还原轴是定性失效，不作为机制发现。

### 2.4 新增 §5.10「核心方案结构性要求的落点」+ 表 16、表 17

- **表 16**：四条结构性要求的落点与判定（§7.1 部分满足、§17.1 部分满足、§27 已满足、§28 部分满足）。关键实得值均可回溯：审计分子集 12；T5 三级弥散基组；微溶剂化 11 分子 × 12 motif、仅 1:2 [Li(M)2]+；`f_unresolved` 0.133→0.267（primary_m1 氧化轴）；全项目 `f_robust_inv = 0`。
- **表 17**：§28 推荐目录骨架 ↔ 实际路径（`data/metadata/`、`structures/`、`outputs/week3,4,5,8,22`、`data/anchors/`、`src/electrolyte_ranking/`、`outputs/figures/`、`成果输出/`）的等价映射，注明承载阶段；原则是不新增第二套真源。
- 结尾说明 11 项可追溯字段由 `config/scientific_definitions.yaml:provenance_requirements` 冻结、`src/electrolyte_ranking/provenance.py` 与各周 `--check` 共同保证。

## 3. 重建与自检

- 构建：`PAPER_OUT=..._v6.docx` → `python 论文/build_paper_docx.py`；`scripts/docx2pdf.ps1` 转 PDF。
- 结果：**35 页**（v5 为 34）；图号范围仍 **1–22**；表号范围 **1–15 → 1–17**。
- 版面断言（pypdf 抽取）：中/英文摘要（含 `Key Words`）与中图分类号在同页且完整落**第 1 页**；`图 1…22`、`表 1…17` 首次出现顺序单调无缺号；`5.10`、`表 16`、`表 17` 均在正文出现。
- 交付层断言：`scripts/build_week24_deliverables.py` 的 `PAPER_EXPECTED_TABLES` 由 15 同步为 **17**；重建 `成果输出/week24_corealign/` 后 **37/37 全通过、0 stale**（含 `paper.pages ≥ 26`、图/表单调、`Key Words` 在第 1 页）。
- README：`scripts/build_github_readme.py` 增补 Week 25 的 v6 条目并把「当前 `_v5`」改为 `_v6`，重生成后 `--check` 通过（33016 字节）。

## 4. 明确**不做**的项（与 `docs/41` §4 一致）

1. 不为补齐 §7.1 的「两种 DFT functional」新增 ωB97X 级别的生产单点——超预算，且会变更已冻结的方法学口径；本轮只把它显式登记为偏差。
2. 不为扩充 §17.1 的候选数或化学计量新增微溶剂化计算——会改变现有 `f_unresolved` 口径。
3. 不新增与证据链无关的图以凑 §24 的图数；§24 Figure 4 的缺口是**现象未观测**，不是排版问题。
4. 不改动任何冻结件（`config/`、`outputs/week2/`、`data/anchors/within_series_ordering.csv`）或既有判决；新增内容全部为表述与对齐。

## 5. 边界与红线（本批已遵守）

- §4.2：未把 `S_ox/red` 简写为「真实电化学稳定窗口」；§3.2：未把 `[LiM]+` 描述为更高保真度估计。
- Gate 1 仍记为「排序层已评估但未闭合」。本批未改其任何表述方向。
- 文字红线：§5.10 登记的两处「部分满足」均为主动取舍，与唯一真实未闭合项（Gate 1）分开标注；未宣称液相锚定。
- 命名空间：本批未新增 `outputs/weekN` 产物，只修订论文与两处脚本字符串/常量、重建交付镜像。

## 6. 未覆盖 / 不确定

- 未解析 `论文/..._v6.pdf` 的逐页图像做人工排版复查（仅用 pypdf 文本层 + 关键页 PNG 目视抽查 §5.3、§5.10、表 16、表 17）。
- 未重跑任何电子结构计算；表 16 的所有实得值取自仓库既有产物（`outputs/week4/t5_diffuse_control*`、`outputs/week8/stage9_*`、`config/scientific_definitions.yaml` 等）。
- 站点（`docs/index.html`、`docs/assets/data.js`）本轮未改：其中不含论文版本号声明，README 已承接 v6 记录。

---

来源：`核心文件/ranking-electrolyte-materials-v2.md`、`docs/41`、`docs/43`、`论文/build_paper_docx.py`、`outputs/week4/t5_diffuse_control_summary.json`、`outputs/week8/stage9_summary.md`、`config/scientific_definitions.yaml`。