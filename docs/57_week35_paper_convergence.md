# Week 35 / Paper：论文主文收敛包

> 阶段：下一阶段实施方案第八周（Paper）。产物目录 `outputs/week35/`，交付镜像
> `..\成果输出（part2）\week35/`。数字由
> `scripts/build_week35_paper_convergence.py` 确定性生成，`--check` 逐字节复核。
> **零新增电子结构计算；不改动任何既有产物与论文源文件。**

## 0. 本轮解决的问题

前七步把「物理机制 -> 决策可靠性 -> 最小信息预算」做成了可复核的闭环，Week 34 又定死了结论边界。
最后一步是把它们**收敛成一篇论文**。实施方案对这一周的验收是：主图、结果、讨论、局限与补充材料。

本阶段不改 docx，而是产出一个**可校验的收敛包**，让 `论文/build_paper_docx.py` 的重建
变成机械操作。它回答四个问题：

1. 七张主图各自对应哪个科学问题，各自的资产是否真的在磁盘上？
2. 结果部分按什么顺序组织？
3. 每个主结论属于哪条轨道？
4. 哪些边界声明必须在论文里出现？

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

**21 个 F 图资产全部在磁盘上**（缺失 0），由构建脚本逐文件核对。
保留 v2 的七图结构，而不是另造一套以审计为中心的图集。

## 2. 结果六节（固定顺序）

| 序 | 英文标题 | 中文 | 主要来源 | 主图 |
| --- | --- | --- | --- | --- |
| 1 | Model hierarchy and external-reference boundaries | 模型层级与外部参考边界 | WP1 / WP7 | Fig. 1, Fig. 2 |
| 2 | Ranking responses to electronic-structure and continuum physics | 电子结构与介质物理如何改变排序 | WP2 | Fig. 3 |
| 3 | Conditional Li+ coordination and redox-state identity | Li+ 配位条件态与还原态身份 | WP3 | Fig. 5 |
| 4 | Uncertainty-aware material selection | 不确定度感知的材料筛选 | WP4 | Fig. 4 |
| 5 | Predictability of model and coordination corrections | 模型位移与配位修正的可预测性 | WP5 | Fig. 6 |
| 6 | Minimum expensive-information budget | 最小昂贵信息预算 | WP6 | Fig. 7 |

顺序与 v2 原方案一致：**先物理，再决策，再学习，最后计算资源优化**。
注意 v6 正文当前的 3.1-3.17 是「物理优先」的连续推进顺序，**不是**这六节；收敛时必须重排。

## 3. 结论-轨道标签

直接沿用 Week 34 / WP7 的 10 条，论文不新造标签：

| 轨道 | 条数 | 内容 |
| --- | --- | --- |
| Track A | 6 | A1-A6：指定 computational target 下的决策稳定性结论 |
| Track B | 2 | B1 绝对标定（未建立）、B2 排序一致性（tau_b=0.4286，未建立） |
| 待验证推断 | 2 | P1 真实体系里的稳定性排序、P2 预算外推 |

## 4. 主文数字溯源

16 个主文数字逐条指向冻结产物，并记录来源 sha256 与复现命令。样例：

| 编号 | 指标 | 值 | 来源 |
| --- | --- | --- | --- |
| L01 | Gate 1 排序一致性 Kendall tau_b | 0.428571 | outputs/week25/series_rel_ordering_check.json |
| L04 | 溶液相 anchor 仍为 estimates 的行数 | 31 | outputs/week2/solution_anchor_audit.json |
| L05 | P0->P1v 氧化轴 tau_b | 0.673203 | outputs/gate1/gate1_dual_track.json |
| L08 | P1v vs P1a tau_b | 0.787879 | outputs/phase2_p1a/p1v_vs_p1a.json |
| L10 | 反转不可能阈值 z* = 1/sqrt(2) | 0.707107 | outputs/week27/estimator_circularity.json |
| L11 | 双方解析子集内最大反向 pair 数（T6b） | 0 | outputs/week27/estimator_circularity.json |
| L13 | 主动学习曲线单元格数 | 296 | outputs/week7/stage8_al_results.json |

## 5. WP6 预算高估：两条口径都要报

| 口径 | 定义 | 高估组合数 | 总组合数 |
| --- | --- | --- | --- |
| tau_b_only | 中位数曲线比「≥80% 重复满足 tau_b ≥ 0.80」更早达标 | **14** | 24 |
| combined | 中位数曲线比「≥80% 重复同时满足 tau_b ≥ 0.80 ∧ Top-20% overlap 全中 ∧ regret ≤ 极差 5%」更早达标 | **21** | 24 |

只说 `14/24` 会被读成「只差一点」；按组合口径实际是 `21/24`。
两个数字都进论文。**注意这里必须按数值比较**：按字符串比较会把 `"9" > "18"` 算成更高，
得到 17 而不是 21（本阶段构建时踩到并修掉了这个 bug）。

## 6. 补充材料落点

| 条目 | 建议落点 | 理由 |
| --- | --- | --- |
| F57 指标稳健性与排序可识别性 | Fig. 2 局部面板 或 补充材料 S2 | 支撑「目标有多可信」，四联面板放主图会挤占 anchor 叙事 |
| F58 模型层独立性 / 信息增益审计 | 补充材料 S2 | 属于方法学论证 |
| **T6a** 反转不可能定理（z* = 0.707107） | Fig. 2 或 Fig. 4 局部面板（**必须出现**） | f_robust_inv = 0 是定义性结果，不写会误导读者 |
| **T6b** 双方解析子集内反向 pair 数为 0 | 与 T6a 并列 | 说明该流水线从不认证分歧 |

## 7. 必须写出的边界声明（13 条）

其中最关键的四条：

- **G01** Gate 1 = NOT CLOSED 且 NOT CLOSABLE（ordering_disagrees, tau_b = 0.4286）。
- **G02** `NOT CLOSABLE != NO SUCH DATA EXIST ANYWHERE` —— 这是可被证伪的负结果。
- **G04** `f_robust_inv = 0` 是**定义性**结果（T6a/T6b），**不是**经验发现。
- **G06** family-held-out 的主动学习曲线**不可用**；池内端点 tau_b = 1.0 是自检端点，不是成绩。

完整 13 条见 `outputs/week35/paper_gap_register.csv`。

## 8. 论文生成器措辞合规

扫描 `论文/build_paper_docx.py`（当前 **1499** 行）：禁用词 **0** 处、违规 **0** 处、允许措辞 **7** 处。

**本阶段发现的问题**：v6 正文（当时扫描 1272 行）尚未使用 R13 之后的 `designated computational
target / designated reference model` 措辞（0 处）。收敛时必须显式补上，而不是简单改词；
这一条是收敛包要暴露的问题，v6 时点论文源文件不在本阶段的写入范围。

**现状**：该缺口已由 Week 36 的 v7 结题重建补齐（`naming_update_required` 由 `True` 变为 `False`）。
本表随论文生成器源码实时扫描，因此这里给出的是当前状态；v6 时点的记录与 v6 → v7 的溯源
（生成器 sha256 `44c026c5…` → `89dd8811…`）保留在 `成果输出（part2）/week36/SUBMISSION.json`。

## 9. 验收清单（实施方案第七节 9 项）

| 项 | 要求 | 负责阶段 | 状态 |
| --- | --- | --- | --- |
| C1 | 统一科学数据表 | week28 / WP1 | met |
| C2 | P0/P1/P2 物理分析 | week29 / WP2 | met |
| C3 | C0/C1/C2 条件态分析 | week30 / WP3 | met |
| C4 | 独立不确定性审计 | week27 + week31 / WP4 | met |
| C5 | 决策可识别性分析 | week31 / WP4 | met |
| C6 | delta-learning / LOFO | week32 / WP5 | met |
| C7 | 主动学习预算分析 | week33 / WP6 | met |
| C8 | external-reference 分层 | week34 / WP7 | met |
| C9 | 七张论文主图 | week35 / Paper | met |

每项的「met」都不是自我声明：构建脚本会打开对应的冻结载荷并检查它自己的自检是否全过
（C1-C8 的载荷各自带 checks 键且全部通过，C9 则核对七图资产 7/7、共 21 个齐备）。

## 10. 给论文重建的必要改动

1. 把 `f_robust_inv = 0` 改写为定义性结果（T6a/T6b），并同时给出 sigma 约定与分母。
2. 凡提到 P1v/P1a/P2a/P2eps 目标阶梯处，显式使用 `designated computational target /
   designated reference model`。
3. 结果部分重排为六节固定顺序。
4. 补入 WP1-WP7 的 16 个溯源数字与 13 条边界声明。
5. 把 F57/F58 与 T6a/T6b 的详细推导放入 Fig. 2/4 局部面板或补充材料。

> 状态（Week 36）：以上 5 项已由 v7 结题重建全部落地；`paper_build_handoff.json` 新增
> `required_edits_status` 逐条记录该状态。

机器可读版本：`outputs/week35/paper_build_handoff.json`。

## 11. 限制

- 本阶段**不写 docx、不改动任何源文件**：论文重建需要另一次显式操作（并需可用的 Word 环境；
  当前 `.venv` 里没有 python-docx）。
- 七图的资产清单来自 v6 生成器实际调用的 `figure()` 资产与 week25/week27 的 F52-F58
  产物；存在性逐文件核对，但「资产合适不合适」仍需人工判断。
- 全程零新增电子结构计算；结论只对已有冻结数据成立。

## 12. 复现命令

```powershell
cd 电解液溶剂HB-Code
.venv\Scripts\python.exe scripts\build_week35_paper_convergence.py
.venv\Scripts\python.exe scripts\build_week35_paper_convergence.py --check
.venv\Scripts\python.exe -m pytest tests/test_week35_paper_convergence.py -q
.venv\Scripts\python.exe scripts\build_week35_deliverables.py
.venv\Scripts\python.exe scripts\build_week35_deliverables.py --check
```
