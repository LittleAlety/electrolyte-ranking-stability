# 溶液锚点核验记录与 within-series 判据（R7）

本文件承担两件事，且**顺序不可颠倒**：

1. **§1–§3 是预注册**（2026-10-02 写定并先行提交）：判据、阈值、比较单元、样本量下限。
   它们在任何 within-series 比对**之前**落盘，用 git 历史可审计（协议提交早于结果提交）。
   纪律依据：`config/prereg.yaml` §4「T 必须…在看结果之前写定」、
   「严禁看完数据后人为挑选一个最有利的阈值」。
2. **§4 起是核验结果**（后补）：三条线索的逐个核验判定、可入表的数值、以及核验失败的如实记录。

---

## 1. 为什么需要这一层（R7 的物理不对称）

实验 LSV/CV 测的是**纯溶剂电解液分解电流的 onset**，是一个**动力学量**；
本项目算的是**固定背景中完整物种的一电子热力学 proxy**。两者的桥接**只能停在排序层面**——
把实验 onset 当作绝对标定去校准计算绝对值，是没有物理依据的。因此 R7 把 Gate 1 拆成两级：

| 级别 | 内容 | 现状 |
| --- | --- | --- |
| **绝对标定级** | 本表 31 行的绝对电位可追溯到「条件匹配」的一次测量 | **承认为未达成**，写成 limitation |
| **排序一致性级** | within-series（同一来源、同一装置/判据）的相对排序与 target model 一致 | 由本文件 §2 的判据决定 |

「该条件组合（neat solvent + 1 M LiPF6 + 其自身分解 onset）下公开可比数据稀缺」本身是 findings，
不是本项目的疏漏。

## 2. 预注册判据（排序一致性级）

排序一致性级**关闭**当且仅当以下三条**同时**成立：

1. **样本量**：可用的 within-series 锚点对数 `n_pairs >= 18`。
   —— 直接沿用 `docs/31` R7 §3 已写定的下限，本次不重新选择。
2. **排序一致性**：target model 的 within-series 相对排序与实验序列的
   **Kendall τ_b >= 0.9**。
3. **同源**：参与比较的每一对必须来自**同一个来源序列**（同一篇文献 / 同一装置 / 同一判据）。
   跨文献合并绝对值一律不得进入这一级（依据线索 3）。

### 2.1 阈值登记（`config/prereg.yaml` §4 要求的 recorded_fields）

| 字段 | 值 |
| --- | --- |
| `T` | **0.9** |
| `objective_direction` | higher_is_better（τ_b 越大越一致；单侧） |
| `source_type` | pre_defined_engineering_standard |
| `source_reference` | `config/prereg.yaml` §2 `probabilistic_pair_ordering.thresholds.strong_i_gt_j = 0.9` —— 本文件不新造数字，直接复用已冻结的 strong 档 |
| `frozen_date` | 2026-10-02 |

**为什么是 0.9 而不是别的数**：0.9 是 prereg 里**已经冻结**的「strong」档；取它有两个好处——
(a) 不引入计划外的新阈值，(b) 它比 Week 21 σ 相图里用的参考线 0.8 **更严**，
因此不能用「把阈值放松到刚好通过」来解释任何结论。

## 3. 与 Gate 0 的关系

本文件**不修改** `config/prereg.yaml` 与 `config/scientific_definitions.yaml`，
因此 Gate 0 保持 CLOSED。若将来要把上述阈值写进 prereg，则必须走 `amendment_log`
并接受 Gate 0 变 NOT CLOSED（`docs/31` §5）。

## 4. 核验结果

（待补：三条线索的逐条判定与可入表数值。）
