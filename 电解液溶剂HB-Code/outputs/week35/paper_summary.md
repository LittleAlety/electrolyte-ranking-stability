# Week 35 / Paper：论文主文收敛包

> 阶段：下一阶段实施方案第八周（Paper）。产物目录 `outputs/week35/`，交付镜像
> `..\成果输出（part2）\week35/`。本文件由
> `scripts/build_week35_paper_convergence.py` 确定性生成，`--check`
> 逐字节复核。**零新增电子结构计算；不改动任何既有产物与论文源文件。**

## 0. 一句话结论

七张主图各有唯一科学问题、21 个 F 图资产全部在磁盘上；结果部分固定为 6 节（先物理 -> 再决策 -> 再学习 -> 最后计算资源）；10 条主结论沿用 Week 34 / WP7 的 Track 标签；16 个主文数字逐条可溯源；13 条边界声明必须写出。

本阶段**不改 docx**：它产出的是 `paper_build_handoff.json` —— 一份让论文重建变成
机械操作的规格。

## 1. 七图映射

| 主图 | 内容 | 回答的问题 | 资产 | 来源周 |
| --- | --- | --- | --- | --- |
| Fig. 1 | 三层研究框架：P/C/reference | 研究对象是什么？ | 2/2 | week1 / week25 |
| Fig. 2 | External anchors + method/uncertainty audit | 目标有多可信？ | 4/4 | week3 / week25 / week27 |
| Fig. 3 | P0/P1/P2 排序与位移分解 | 哪些物理改变排序？ | 4/4 | week4 / week9 |
| Fig. 4 | Resolution map + Top-k/decision regret | 哪些变化影响选择？ | 3/3 | week6 / week25 |
| Fig. 5 | Li+ coordination、state identity、机制案例 | 为什么发生变化？ | 3/3 | week5 / week25 |
| Fig. 6 | Direct vs delta-learning，重点 LOFO | 能否廉价预测修正？ | 2/2 | week7 |
| Fig. 7 | Active-learning decision-budget curves | 最少需要多少昂贵信息？ | 3/3 | week7 / week23 |

## 2. 结果六节（固定顺序）

| 序 | 英文标题 | 中文 | 回答的问题 | 主要来源 | 主图 |
| --- | --- | --- | --- | --- | --- |
| 1 | Model hierarchy and external-reference boundaries | 模型层级与外部参考边界 | 研究对象是什么；目标有多可信？ | WP1 / WP7 | Fig. 1, Fig. 2 |
| 2 | Ranking responses to electronic-structure and continuum physics | 电子结构与介质物理如何改变排序 | 哪些物理改变排序？ | WP2 | Fig. 3 |
| 3 | Conditional Li+ coordination and redox-state identity | Li+ 配位条件态与还原态身份 | 为什么发生变化？ | WP3 | Fig. 5 |
| 4 | Uncertainty-aware material selection | 不确定度感知的材料筛选 | 哪些变化影响选择？ | WP4 | Fig. 4 |
| 5 | Predictability of model and coordination corrections | 模型位移与配位修正的可预测性 | 能否廉价预测修正？ | WP5 | Fig. 6 |
| 6 | Minimum expensive-information budget | 最小昂贵信息预算 | 最少需要多少昂贵信息？ | WP6 | Fig. 7 |

## 3. 结论-轨道标签（沿用 Week 34 / WP7，不新造）

| ID | 主结论 | 轨道 | 判定 |
| --- | --- | --- | --- |
| A1 | 在 designated computational target 下，缺失物理（P1v 显式介质 / P1a 绝热 / P2a 隐式溶剂 / P2eps）会改变一部分候选对的决策状态：robust inversion = 0，但 UNRESOLVED 占比可观 | Track A | established (computational target only) |
| A2 | P1v 与 P1a 的垂直-绝热差异本身足以翻转个别候选对（n=12，tau_b=0.788，robust inversion=2） | Track A | established (computational target only) |
| A3 | C1 还原态身份分层（Li-centered 与 molecule-centered）使主排序样本塌到 n=1，还原轴排序在 C1 条件下无定义 | Track A | established (definitional limitation) |
| A4 | 在 designated target 内，候选可被分成确定 / 边界 / 未解析三类（resolution map），Top-k 与 decision regret 只在这三类内解释 | Track A | established (computational target only) |
| A5 | Δ-learning（便宜参考层 + 学到的位移）相对 direct 模型在 LOFO 下 6/8 个组合的 tau_b 更好，但收益只部分转化为 Top-k 与 regret 改善 | Track A | established (computational target only) |
| A6 | 池内插值下四策略的预算-收益曲线可用；family-held-out 的 AL 曲线不可用，池内端点 tau_b=1.0 是自检端点而非成绩 | Track A | established with an explicit declared gap |
| B1 | 绝对电位尺度（V vs Li/Li+）可与真实实验条件匹配比较 | Track B | NOT established (0/31 rows upgraded) |
| B2 | within-series 相对排序被 target model 复现（tau_b >= 0.9） | Track B | NOT established (tau_b=0.4286 -> ordering_disagrees) |
| P1 | 被 designated target 排到前面的候选，在真实电解液体系中同样更稳定 | 待验证推断 | untestable until Gate 1 closes |
| P2 | 昂贵标签预算的收益阈值可以外推到真实筛选中的「最少需要多少张 DFT」 | 待验证推断 | untestable (no external calibration) |

计数：Track A 6 / Track B 2 / 待验证推断 2。

## 4. 主文数字溯源

| 编号 | 指标 | 值 | 来源 |
| --- | --- | --- | --- |
| L01 | Gate 1 排序一致性 Kendall tau_b | 0.42857142857142855 | outputs/week25/series_rel_ordering_check.json |
| L02 | Gate 1 within-series 可用 pair 数 | 21 | outputs/week25/series_rel_ordering_check.json |
| L03 | Gate 1 concordant / discordant | 15 | outputs/week25/series_rel_ordering_check.json |
| L04 | 溶液相 anchor 仍为 estimates 的行数 | 31 | outputs/week2/solution_anchor_audit.json |
| L05 | P0->P1v 氧化轴 tau_b | 0.673202614379085 | outputs/gate1/gate1_dual_track.json |
| L06 | P0->P1v 氧化轴 UNRESOLVED pair 数 | 70 | outputs/gate1/gate1_dual_track.json |
| L07 | P1v vs P1a 绝热阶梯分子数 | 12 | outputs/phase2_p1a/p1v_vs_p1a.json |
| L08 | P1v vs P1a tau_b | 0.7878787878787878 | outputs/phase2_p1a/p1v_vs_p1a.json |
| L09 | P1v vs P1a ROBUST_INVERSION 数 | 2 | outputs/phase2_p1a/p1v_vs_p1a.json |
| L10 | 反转不可能阈值 z* = 1/sqrt(2) | 0.7071067811865475 | outputs/week27/estimator_circularity.json |
| L11 | 双方解析子集内最大反向 pair 数（T6b） | 0 | outputs/week27/estimator_circularity.json |
| L12 | WP5 与 Stage 7 对账的 OOF 预测行数 | 288 | outputs/week32/wp5_delta_learning.json |
| L13 | 主动学习曲线单元格数 | 296 | outputs/week7/stage8_al_results.json |
| L14 | 主动学习逐 repeat 记录数 | 5920 | outputs/week7/stage8_al_results.json |
| L15 | WP2 主表行数 | 299 | outputs/week29/wp2_physics_response.json |
| L16 | WP4 主表行数 | 918 | outputs/week31/wp4_decision_identifiability.json |

每个数字都附带来源 sha256 与复现命令（见 `paper_number_lineage.csv`）。

## 5. WP6 预算高估：两条口径都要报

| 口径 | 定义 | 高估组合数 | 总组合数 |
| --- | --- | --- | --- |
| tau_b_only | median tau_b curve reaches tau_b >= 0.80 earlier than the point where >= 80% of the 20 repeats do | 14 | 24 |
| combined | median tau_b curve reaches tau_b >= 0.80 earlier than the point where >= 80% of repeats satisfy tau_b >= 0.80 AND Top-20% overlap complete AND regret <= 5% of the in-pool target range | 21 | 24 |

只说 `14/24` 会被读成「只差一点」；按组合口径实际是 `21/24`。两个数字都进论文。

## 6. 补充材料落点

| 条目 | 内容 | 建议落点 | 理由 |
| --- | --- | --- | --- |
| F57 | 指标稳健性与排序可识别性（政策带 / f_tie / 可分层层数 / 近临界 pair） | Fig. 2 局部面板 或 补充材料 S2 | 支撑「目标有多可信」，但四联面板放主图会挤占 anchor 叙事 |
| F58 | 模型层独立性 / 信息增益审计（位移 dispersion、rung 间 |Pearson|、逐级 tau_b） | 补充材料 S2（Fig. 2 的支撑推导） | 证明「阶梯是分解而非同一信号的再编码」属于方法学论证 |
| T6a | 反转不可能定理：ROBUST_INVERSION 需 z <= 1/sqrt(2)，冻结 z 全部排除（z*=0.707107） | Fig. 2 或 Fig. 4 的局部面板（**必须出现**） | f_robust_inv = 0 是定义性结果，不是经验发现；不写会误导读者 |
| T6b | 双方解析子集内反向 pair 数为 0（max_n_discordant_both = 0） | 与 T6a 并列，Fig. 4 面板或补充材料 | 同上：说明该流水线从不认证分歧 |

## 7. 必须写出的边界声明

| ID | 声明 | 来源 | 位置 |
| --- | --- | --- | --- |
| G01 | Gate 1 = NOT CLOSED 且 NOT CLOSABLE（ordering_disagrees, tau_b=0.4286） | outputs/gate1/gate1_dual_track.json; docs/gate1_negative_result.md | 讨论 / 局限（必须） |
| G02 | NOT CLOSABLE != NO SUCH DATA EXIST ANYWHERE（可被证伪的负结果） | outputs/gate1/gate1_dual_track.json#track_B.components.closability.scope_caveat | 局限（必须） |
| G03 | 论文适用范围限定在 computational-target decision stability | docs/56_week34_wp7_external_reference_boundary.md | 摘要 / 结论（必须） |
| G04 | f_robust_inv = 0 是**定义性**结果（T6a/T6b），不是经验发现 | outputs/week27/estimator_circularity.json | 结果 4 节 / 方法（必须） |
| G05 | 自指 sigma：独立不确定性无法用现有数据估计（不得把零反转读成经验结论） | outputs/week27/estimator_circularity.json#verdict | 局限（必须） |
| G06 | family-held-out 的主动学习曲线**不可用**（冻结 replay 只有池内插值） | outputs/week33/holdout_vs_inpool.csv | 结果 6 节（必须） |
| G07 | 池内端点 tau_b = 1.0 是自检端点，不是成绩 | outputs/week33/wp6_active_learning.json#conventions | 结果 6 节（必须） |
| G08 | C1 还原态身份分层后主排序样本塌到 n = 1（还原轴在 C1 下无定义） | outputs/gate1/gate1_dual_track.json#track_A.evidence | 结果 3 节（必须） |
| G09 | WP5 的 6/8 不是「普遍更好」，反例必须列出 | outputs/week32/delta_vs_direct.csv | 结果 5 节（必须） |
| G10 | WP6 的成功标准是内部操作性标准，未经外部校准 | outputs/week33/wp6_active_learning.json#conventions.success_standard | 结果 6 节 / 局限（必须） |
| G11 | within-series 表 14 行 provenance 均为 transcription-only，未回溯到原始测量 | data/anchors/within_series_ordering.csv | 结果 1 节 / 局限（必须） |
| G12 | 核心集只有 18 个分子（C 任务 10），20 次重复的 2.5/97.5 百分位本身很粗 | outputs/week33/al_protocol_audit.csv | 局限（必须） |
| G13 | 全程零新增电子结构计算：不新增 ORCA/xTB 作业，结论只对已有冻结数据成立 | outputs/week28..week34 各 payload 的 inputs.new_electronic_structure_jobs | 方法（必须） |

## 8. 论文生成器措辞合规

扫描 `论文/build_paper_docx.py`（1499 行）：禁用词 0 处、违规 0 处；允许措辞 7 处。
**发现**：正文已使用 R13 之后的 designated 措辞（7 处）、禁用词 0 处。v6 时点该缺口为 0 处，已由 Week 36 的 v7 重建补齐；本表随论文生成器源码实时扫描，报告的是当前状态，v6 时点的记录见 Week 36 的 frozen_snapshots。

## 9. 验收清单（实施方案第七节 9 项）

| 项 | 要求 | 负责阶段 | 状态 |
| --- | --- | --- | --- |
| C1 | 统一科学数据表：全部主文数字可追溯至明确状态与原始计算 | week28 / WP1 | met |
| C2 | 完成 P0/P1/P2 物理分析：至少包含排序、位移、Top-k 和 regret | week29 / WP2 | met |
| C3 | 完成 C0/C1/C2 条件态分析：明确 state identity 与化学计量边界 | week30 / WP3 | met |
| C4 | 完成独立不确定性审计：不再把自指性零反转解释为经验结果 | week27 + week31 / WP4 | met |
| C5 | 完成决策可识别性分析：能识别确定、边界与未解析候选 | week31 / WP4 | met |
| C6 | 完成 delta-learning / LOFO：报告预测误差及实际筛选决策指标 | week32 / WP5 | met |
| C7 | 完成主动学习预算分析：四策略、重复实验、无隐藏标签泄漏 | week33 / WP6 | met |
| C8 | 完成 external-reference 分层：Gate 1 状态和适用范围一致 | week34 / WP7 | met |
| C9 | 形成七张论文主图：每张图对应一个明确科学问题 | week35 / Paper | met |

## 10. 验收

| 问题 | 结论 | 支撑 |
| --- | --- | --- |
| Q1. 七张主图是否各自对应一个明确科学问题？ | 是：7/7 张图各有唯一科学问题，且其冻结资产全部在磁盘上（21 个资产） | 7/7 |
| Q2. 结果部分是否按固定顺序组织（先物理 -> 再决策 -> 再学习 -> 最后计算资源）？ | 是：6 节固定顺序，1-3 为物理与机制，4 为决策，5 为学习，6 为计算资源 | 6/6 |
| Q3. 每个主结论是否沿用 Week 34 / WP7 的 Track 标签？ | 是：10 条主结论全部带标签（Track A 6 条 / Track B 2 条 / 待验证推断 2 条） | 10/10 |
| Q4. 论文适用范围是否被限定，且边界声明是否齐全？ | 是：13 条边界声明必须出现；验收清单 9 项中 9 项已满足（未达成：none） | 9/9 |

## 11. 给论文重建的必要改动

- 把 f_robust_inv = 0 改写为定义性结果（T6a/T6b），并同时给出 sigma 约定与分母
- 凡提到 P1v/P1a/P2a/P2eps 目标阶梯处，显式使用 designated computational target / designated reference model（v6 扫描显示两套措辞都未出现，需补齐而不是改词；已由 Week 36 的 v7 重建落地）
- 结果部分重排为六节固定顺序（v6 时点为 3.1-3.17 的物理优先顺序；已由 v7 落地）
- 补入 WP1-WP7 的 16 个溯源数字与 13 条边界声明
- 把 F57/F58 与 T6a/T6b 的详细推导放入 Fig. 2/4 局部面板或补充材料

## 12. 限制

- 本阶段不写 docx、不改动任何源文件：论文重建需要另一次显式操作（并需可用的 Word 环境）。
- 七图映射中的资产清单来自 v6 生成器实际调用的 `figure()` 资产与 week25/week27 的
  F52-F58 产物；资产存在性在构建时逐文件核对。
- 全程零新增电子结构计算；结论只对已有冻结数据成立。

## 13. 复现命令

```powershell
cd 电解液溶剂HB-Code
.venv\Scripts\python.exe scripts\build_week35_paper_convergence.py
.venv\Scripts\python.exe scripts\build_week35_paper_convergence.py --check
.venv\Scripts\python.exe -m pytest tests/test_week35_paper_convergence.py -q
.venv\Scripts\python.exe scripts\build_week35_deliverables.py
.venv\Scripts\python.exe scripts\build_week35_deliverables.py --check
```
