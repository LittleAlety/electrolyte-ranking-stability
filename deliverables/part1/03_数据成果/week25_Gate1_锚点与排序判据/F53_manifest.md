# F53 图清单 · Week 25 · family-resolved 排序统计
## 图件
| 项 | 值 |
|---|---|
| 文件名 | `outputs/figures/F53_family_resolved.png` |
| 尺寸 | 6.3 × 6.4 in @ 200 dpi（1260 × 1280 px） |
| 面板 | (a) 氧化轴：家族内 τ_b vs 台阶（带 bootstrap 95% CI 带）；(b) 氧化轴：家族内 f_unresolved(after) vs 台阶；(c) 还原轴：家族内 τ_b vs 台阶（带 95% CI 带）；(d) 还原轴：家族内 f_unresolved(after) vs 台阶 |
| 生成脚本 | `scripts/analyze_w25_figure_f53.py` |
| 数据来源 | `outputs/week25/family_resolved_stats.json`（sha256 `5be94c8d6a053821e5a92f14b1a45561872e3dd43e111fdedefb6491c14ebd36`；唯一输入，图上无硬编码数值） |
| 统计脚本 | `scripts/analyze_family_resolved.py`（重算自 `outputs/week9/stage10_ladder.json` 与 §19 Stage 6 引用的既有逐分子产物） |
| 复现方式 | `python scripts/analyze_w25_figure_f53.py --check`（内存重渲染 + 逐像素比对） |
| 字体 | Microsoft YaHei / SimHei，`axes.unicode_minus=False` |
| 配色 | 与 `analyze_w25_figure_f52.py` 同族：INK/MUTED/GRID + 8 家族固定色板 |
## 图注（可直接引用）
图 F53 family-resolved 排序统计。8 个结构家族 × 5 级台阶 × 2 条轴 = 160 个 (population, 台阶, 轴, 家族) 组合里，家族内 τ_b 只有 16 个可估计（全部落在 native-18 的 P0→P1 与 P1→P2 两级、两条轴、4 个 n≥3 的家族：linear_carbonate n=3、cyclic_carbonate n=4、ether n=3、ester n=3），其余 144 个记 not_estimable（单分子家族 104 个、n=2 单对 40 个）——这正是 v2 §13.3「每个 family 可能只有约 10 个样本、必须报 bootstrap 区间」所描述的统计边界。(a)/(c) 实线为 native-18 各家族家族内 τ_b 随台阶的变化，阴影为该家族分子有放回重抽样的 95% 区间（seed=20261002，5000 次；n=3–4，区间极宽，如 ester 氧化轴 CI = [-1.000, 1.000]），空心点为 n<3 的 not_estimable（y=1.06 处为示意条）；common-10 每个家族分子数 ≤2，家族内 τ_b 全部 not_estimable，故不画线。(b)/(d) 为家族内 f_unresolved(after)（沿用冻结 pair tolerance 口径：z=1.0、δ=0，与 `stage10_ladder.json` 同一 `resolved_mask` 口径），实线 native-18、虚线 common-10，空心点为 n<2 无 pair。所有 CI 均为小样本重抽样，不得表述为「显著」；本图不改变任何既有判决。
## 复现命令
```powershell
.venv\Scripts\python.exe scripts\analyze_family_resolved.py
.venv\Scripts\python.exe scripts\analyze_family_resolved.py --check
.venv\Scripts\python.exe scripts\analyze_w25_figure_f53.py
.venv\Scripts\python.exe scripts\analyze_w25_figure_f53.py --check
```
## 纪律声明
- 零新增电子结构计算；全部数值来自仓库既有产物（`outputs/week9/stage10_ladder.json` 等），图上所有数字经 `--check` 逐像素 / 逐字段验证，数据变动即报错。
- 未改动 `outputs/week2/`、`论文/`、`data/`、`docs/`、`outputs/week25/` 下既有文件。
- 只新建 `scripts/analyze_family_resolved.py`、`scripts/analyze_w25_figure_f53.py`、`outputs/week25/family_resolved_stats.json`、`outputs/week25/family_resolved_stats.md`、`outputs/week25/F53_manifest.md`、`outputs/figures/F53_family_resolved.png`。
