# F56 manifest · R14 收口汇总图

- script：`scripts/analyze_r13_summary_figure.py`
- figure：`outputs/figures/F56_r13_summary.png`（1260 × 1400 px @ 200 dpi）
- stats：`outputs/week26/figure_f56_stats.json`、`outputs/week26/figure_f56_stats.md`
- 新电子结构计算：**0**（全部数值为冻结产物现算）

## 图注

(a) 三态计数堆叠条（STABLE / UNRESOLVED / ROBUST_INVERSION，z = 1.0）；
(b) 目标模型的 f_unresolved(z) 分辨率曲线；
(c) Gate 1 双轨定性（Track A established；Track B NOT CLOSED 且 NOT CLOSABLE）；
(d) 防误读卡片：「0 robust inversions ≠ 0 ranking instability」。

## 复现命令

```powershell
.venv\Scripts\python.exe scripts\analyze_r13_summary_figure.py --check
.venv\Scripts\python.exe scripts\analyze_r13_summary_figure.py
```

## 输入 sha256

| 路径 | sha256 |
| --- | --- |
| `outputs/decision_state/decision_state_report.json` | `efa04c9893a10081033aa5019180d48d25f1b872055c3dd971cc25a4e9566a5d` |
| `outputs/week9/stage10_ladder.json` | `3eb6b36d5622ec0e3147dd827a6437aabac2ea38c53936fddc974e85376ac3cf` |
| `outputs/gate1/gate1_dual_track.json` | `2487b779530d43ff80b6a5e603e5aaac1662ee94f66ff652772cf87324b5b0e1` |
| `outputs/week25/series_rel_ordering_check.json` | `9eac280f1edc6def1d390c03c216abbb1a2e30e8cbd7a8693597abd2178949ae` |
| `outputs/phase2_p1a/p1v_vs_p1a.json` | `71c7fad051e82a47cb08a95c29e285a7fad974d293268c7fc0827eca261501f0` |
| `outputs/state_identity/state_identity_stratification.json` | `136905f16af97170a22d033f9a1b383b2c7e85042598e373d4cc19958abc1eb7` |

## 输出 sha256

| 路径 | sha256 |
| --- | --- |
| `outputs/week26/figure_f56_stats.json` | `633cdba34c55b1e6de3c7bc889a4e419520ea2c49efdf52db111604ebbcddf96` |
| `outputs/week26/figure_f56_stats.md` | `c55b6106c0a9bd43716ede1c07ea069e77c2106d2bc2b85ae8efcb00f8b556ff` |
| `outputs/figures/F56_r13_summary.png` | `52c45fe70f46339b0567cae7f23067576fa14e8ebc31bb7d69b5d84b390b067e` |

## 纪律声明

- 本图不跑任何新电子结构；所有数字均为已冻结产物的现算读出。robust inversion = 0 的含义是 evidence insufficient to resolve，不是 ranking stable；不得把本图读成「18 个溶剂的最终性能排名」。
- 本图不改动任何既有判决；不使用仓库外文件。
- 字体：Microsoft YaHei / SimHei，axes.unicode_minus = False。

