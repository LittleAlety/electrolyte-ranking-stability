# R14 — 第二轮外部评审收口（close-out）

- 日期：2026-10-08
- 类型：收口工程（close-out），**零新增电子结构计算**
- 判定：自本轮起，本仓库作为**研究成果库**（research result）收口，而非实验记录库（run log）
- 冻结件：`FINAL_CONCLUSIONS.md`、`outputs/week26/`（F56 汇总图 + 统计 + manifest + clean-room 审计）、`docs/47_clean_room_reproduction_audit.md`、`docs/48_round2_closeout.md`
- Gate 状态：`Gate 0` **CLOSED**；`Gate 1` **NOT CLOSED 且 NOT CLOSABLE**（作为 negative result 报告，不再尝试救回）

本文档回答一个问题：**按第二轮外部评审的 6 条意见，这个仓库最终该怎么收口、哪条落在哪里、哪条明确不做。**

评审的核心判断是：仓库已不是「方案没做完」，而是「能不能作为经得起外部评审的科学研究仓库收口」，因此真正值得做的是最后一轮**收口工程**，而不是继续加 Week 26/27/28 的计算。

---

## 0. 结论：6 项对照

| 优先级 | 评审项 | 评审判断 | R14 落地 | 位置 |
| --- | --- | --- | --- | --- |
| 🔴 P0 | 1. Gate 1 闭合 | 不要再做成 PASS；正式定性为研究结果 | Gate 1 双轨定性 **NOT CLOSED 且 NOT CLOSABLE**，写入 `closability` 判据 | `scripts/gate1_dual_track_report.py`、`outputs/gate1/gate1_dual_track.json`、`docs/gate1_negative_result.md` |
| 🔴 P0 | 2. 研究问题 ≠ 最终排名 | 需要一句硬 Scope | README 顶部加英文 Scope 原文 + 中文解释 | `scripts/build_github_readme.py`、`README.md` |
| 🟠 P1 | 3. `f_robust_inv = 0` 防误读 | 视觉层面再防一次 | README 防误读块（现算 20 组合）+ 新图 **F56** 把「0 robust inversions ≠ 0 ranking instability」画进图 | `outputs/figures/F56_r13_summary.png`、`outputs/week26/figure_f56_stats.json` |
| 🟠 P1 | 4. `n = 18` 外部效度 | 分层声明，而非补到 60–100 | README 新增「n = 18 的四层可声明边界」表 | `README.md` |
| 🟠 P1 | 5. 缺最终结论矩阵 | 需要 `FINAL_CONCLUSIONS.md` | 10 问 × 四段式（结论 → 数字 → evidence path → limitation），确定性生成 | `FINAL_CONCLUSIONS.md`、`scripts/build_final_conclusions.py` |
| 🟠 P1 | 6. 从零复现审计 | clean-room reproduction test | 离线只读审计 C1–C7 + JSON/MD 报表 + 说明文档 | `scripts/audit_clean_room.py`、`outputs/week26/clean_room_audit.json`、`docs/47_clean_room_reproduction_audit.md` |

---

## 1. 🔴 Gate 1：从「待办缺陷」变成「研究结果」

评审原话（摘要）：

> 现在最科学的做法是：**Gate 1 = NOT CLOSED / NOT CLOSABLE → 正式作为研究结果。** 在预注册要求的同装置、同判据、≥7 个核心分子的同源序列条件下，公开可验证数据不足，因此无法完成排序层外部锚定。

R14 落地：

- `outputs/gate1/gate1_dual_track.json` 顶层新增 `gate1_closability = "NOT CLOSABLE"`，`track_B.closability` 同值。
- `track_B.components.closability` 记录 `verdict / statement / detail / prereg_requirement / evidence / consequence / source`。
- 判据一致：τ_b = 0.4286 < 0.90（n_pairs = 21，一致 15 / 不一致 6）；还原轴仅 3 对（门槛 ≥ 18）；本地文献最长同装置/同判据同源序列 **k = 1**；绝对标定 31 行仍为 `est`、升级 0。
- **禁止**把 Gate 1 读成待办缺陷，也禁止事后通过剔除分子 / 替换模型列 / 放宽容差把它救成 PASS。

---

## 2. 🔴 研究问题 ≠ 电解液最终排名（硬 Scope）

README 顶部新增（原文）：

> **Scope.** This repository does not establish a definitive electrolyte-solvent ranking. It studies the stability, instability, and information cost of ranking decisions under progressively more realistic computational models.

中文解释紧随其后：本项目研究的是 decision stability / rank change / mechanism / minimal budget，**不回答「哪个溶剂最好」**；别人引用本仓库结果时不应读成「18 个电解液的最终性能排行榜」。

---

## 3. 🟠 `f_robust_inv = 0` 的视觉防误读

- README 防误读块从 `outputs/week9/stage10_ladder.json` **现算** 20 个 (台阶, 轴) 组合，报 `robust inversion 0 observed`、`unresolved 最高 80.0%`。
- 新图 **F56**（`outputs/figures/F56_r13_summary.png`，1260 × 1400 px @ 200 dpi）四面板把这句话画进图：(a) 三态堆叠条、(b) f_unresolved(z) 分辨率曲线、(c) Gate 1 双轨卡片（Track A established；Track B NOT CLOSED 且 NOT CLOSABLE）、(d) 防误读卡片「0 robust inversions ≠ 0 ranking instability」。

数字（读回冻结产物，非新算）：Stage 10 ladder 20 组合 `f_robust_inv` 全 0；`f_unresolved` 最高 **0.800**（C0→C1 reduction，τ_b **−0.467**）。

---

## 4. 🟠 `n = 18` 的四层可声明边界

| 层面 | 当前状态 |
| --- | --- |
| 机制验证 | **可以成立** |
| 排序规律的普适性 | **不能宣称成立** |
| 大规模筛选能力 | **未验证** |
| 方法学 proof-of-concept | **成立** |

core set 实际 18（v2 建议 60–100）、broad pool 实际 40（v2 建议 300–1000）。R14 **不**把集合扩到 60–100：项目价值落在机制 + decision-stability 方法论，而不是大规模筛选。

---

## 5. 🟠 `FINAL_CONCLUSIONS.md`：10 个问题

`scripts/build_final_conclusions.py` 确定性生成 `FINAL_CONCLUSIONS.md`（`--check` 逐字节；`--trace` 91/91 read、0 miss）。每个问题四段式：**结论 → 数字 → evidence path → limitation**，所有数字从冻结产物读回。

Q1 cheap→target 是否改变排序 · Q2 mean shift vs dispersion · Q3 哪个轴更脆弱 · Q4 dielectric 是否真的导致 ranking inversion · Q5 Li+ coordination 是否改变结论 · Q6 microsolvation 是否改变结论 · Q7 conformer uncertainty 是否覆盖 ranking gap · Q8 SCF alternative 是否是真实物理态差异 · Q9 哪些额外计算最值得花预算 · Q10 Gate 1 最终为什么不能闭合。

文件顶部另有「读前必读」两个防误读点。

---

## 6. 🟠 clean-room 复现审计

`scripts/audit_clean_room.py`（离线只读，零电子结构）逐项检查 C1–C7，输出 `outputs/week26/clean_room_audit.json` / `.md`，说明见 `docs/47_clean_room_reproduction_audit.md`。

| 检查 | 内容 | 本轮结果 |
| --- | --- | --- |
| C1 | 仓库内复现面（12 个顶层入口） | PASS |
| C2 | 验证入口点（7 个） | PASS |
| C3 | 触及仓库外交付层的脚本（均非验证入口） | INFO |
| C4 | tests 不外伸 | PASS |
| C5 | 外部二进制对验证可选 | INFO |
| C6 | 冻结清单可重算 | PASS |
| C7 | 收口文档与产物一致 | PASS |

关键纪律：审计报表**不含任何机器路径 / 盘符 / 用户名**（机外信息只打印到 stdout），因此 `--check` 在全新 clone 里可复现。C3 登记的 6 个脚本只用于**生成新交付物**，不是验证入口；README 里那三条仓库外路径（`..\成果输出\`、`..\核心文件\`、`..\论文\`）是交付层，不影响「从零 clone → 跑 tests → 重建图 → 复核 hash」。

---

## 7. 本轮**不做**的事（拒绝项）

- 不再加 Week 26/27/28 的电子结构计算；不加 core set 到 60–100，不加 broad pool 到 300–1000。
- 不把 Gate 1 做成 PASS（不改判据、不剔分子、不放宽阈值）。
- 不改 week1–week25 的任何既有产物数字。

---

## 8. 证据链（全部可追溯）

| 事实 | 来源 |
| --- | --- |
| Gate 1 排序层 ordering_disagrees | `outputs/week25/series_rel_ordering_check.json` |
| 本地文献最长同源序列 k = 1 | `docs/40_week25_gate1_report.md` |
| 三态判据 / f_unresolved(z) | `outputs/decision_state/decision_state_report.json` |
| 五级台阶 20 组合 f_robust_inv 全 0 | `outputs/week9/stage10_ladder.json` |
| F56 输出 hash | `outputs/week26/F56_manifest.md` |
| clean-room C1–C7 | `outputs/week26/clean_room_audit.json` |

本文件与上述全部产物一致；`scripts/freeze_gates.py` 重跑后 Gate 0 仍 CLOSED、Stage 2 清单重新冻结。
