# F52 图清单 · Week 25 · Gate 1 排序一致性负结果

## 图件

| 项 | 值 |
|---|---|
| 文件名 | `outputs/figures/F52_gate1_ordering.png` |
| 尺寸 | 6.3 × 7.1 in @ 200 dpi（1260 × 1420 px） |
| 面板 | (a) 实验序 vs P1 序散点；(b) 位次迁移斜率图；(c) 锚点噪声 bootstrap 分布；(d) 逐分子敲除 τ_b |
| 生成脚本 | `scripts/analyze_w25_figure_f52.py` |
| 数据来源 | `outputs/week25/gate1_oxidation.json`（唯一输入，图上无硬编码数值） |
| 复现方式 | `python scripts/analyze_w25_figure_f52.py --check`（内存重渲染 + 逐像素比对） |
| 字体 | Microsoft YaHei / SimHei，`axes.unicode_minus=False` |
| 配色 | 与 `make_stage24_figure.py` / `make_w24_flowchart.py` 同族：INK/ACCENT/WARN/OK/MUTED/GRID |

## 图注（可直接引用）

图 F52 Gate 1 排序一致性负结果诊断。锚点为 Ue1994/Okoshi2015 氧化系列（纯溶剂 + Et₄NBF₄，无 Li⁺，对应 C0 梯级；14 行中 7 行属 18 分子核心集，给出 21 对可用对）。(a) 实验位次与注册臂 P1（`p1_ox_ev`）位次对照，对角虚线为完全一致；EC 由实验的第 5 位被模型排到第 1 位，是唯一显著偏离的物种。(b) 同一两组位次的斜率图，6 对不一致表现为 4 条交叉线（EC、EMC、PC、MA、SL 参与）。(c) 实验值按 N(v, 0.1² V) 扰动 2×10⁴ 次的 τ_b 分布（0.1 V 为 PI 声明的系列重复性，非来源报告的不确定度）；95% 区间 [0.3333, 0.6190] 整体低于冻结判据 0.9，观测值 0.4286 位于分布中心附近。(d) 注册臂上逐分子敲除后的 τ_b，剔除 EC 后由 0.4286 升至 0.7333（升幅最大），说明不一致由 EC 主导。

## 复现命令

```powershell
.venv\Scripts\python.exe scripts\analyze_w25_gate1_oxidation.py
.venv\Scripts\python.exe scripts\analyze_w25_gate1_oxidation.py --check
.venv\Scripts\python.exe scripts\analyze_w25_figure_f52.py
.venv\Scripts\python.exe scripts\analyze_w25_figure_f52.py --check
```

## 纪律声明

- 零新增电子结构计算；全部数值来自仓库既有产物。
- 未改动 `论文/`、`docs/`、`成果输出/`、`data/anchors/`、`outputs/week2/series_rel_ordering_check.json`。
- 图上所有数字经 `--check` 逐像素 / 逐字段验证，数据变动即报错。
