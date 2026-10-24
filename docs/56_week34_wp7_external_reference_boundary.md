# Week 34 / WP7：外部验证与结论边界

> 阶段：下一阶段实施方案 WP7。产物目录 `outputs/week34/`，交付镜像
> `..\成果输出（part2）\week34/`。数字由
> `scripts/build_week34_wp7_external_reference_boundary.py` 确定性生成，
> `--check` 逐字节复核。**零新增电子结构计算、零数据剔除、零阈值改动。**

## 0. 本轮解决的问题

WP1–WP6 把「哪些缺失物理会改变筛选决策、候选能不能被分辨、便宜模型能不能学到位移、最少要花
多少昂贵标签」做成了内部可复核的闭环。这些结论都成立在 **designated computational target**
之下。WP7 不新增任何物理结论，只回答一个**边界问题**：这些结论到哪儿为止？

实施方案对 WP7 有三条硬要求：

- **Gate 1 不能因为内部结果丰富就被跳过，也不应强迫其关闭。**
- **下一步优先是对现有外部 anchors 做条件一致性与 provenance 复核，而不是为了提高 tau
  人为筛掉不一致数据。**
- **每个主结论必须注明它属于 Track A、Track B，还是需要进一步验证的推断。**

三层表述纪律贯穿本文件：**模型事实**（`anchor_inventory`、
`anchor_row_audit`、`ordering_recheck`）/ **统计判定**
（`gate1_status`、`gate1_components`、`track_separation`）/
**材料意义**（`claim_track_assignment`、`wp7_acceptance`）。

## 1. 两条轨道

| 轨道 | 名称 | 状态 | 可以下什么结论 |
| --- | --- | --- | --- |
| Track A | decision-stability validity | computationally_established | 在指定 designated computational target 下得出结论 |
| Track B | external / experimental validity | **NOT CLOSED / NOT CLOSABLE** | 只有参考证据支持时才能推广到真实筛选 |

Track B 未闭合**不**使 Track A 失效；它只限制「绝对尺度 / 真实排序」这类声明的强度。

## 2. Gate 1：既不跳过，也不强迫关闭

### 2.1 组件状态

| 组件 | 状态 | 观测值 |
| --- | --- | --- |
| ordering_consistency | ordering_disagrees | tau_b=0.4286 over n_pairs=21（一致 15 / 不一致 6） |
| absolute_calibration | limitation（按 R7，不再是独立 blocker） | 31/31 行仍为 `est`，升级 0 行 |
| reduction_axis_secondary | not_evaluable_secondary_only | 只有 3 个 pair（门槛 18）：**不足**，不是**不一致** |
| upstream_feasibility | not_closable_on_current_literature | 本地文献里最长同装置 / 同判据同源序列只有 k = 1 |
| closability | **NOT CLOSABLE** | 见 §2.2 |

### 2.2 预注册关闭条件逐条对账

| 条件 | 要求 | 现状 | 是否满足 |
| --- | --- | --- | --- |
| same_apparatus | 序列内同一装置 | 单 series，单一电极（glassy carbon） | 是 |
| same_criterion | 序列内同一判据 | 全部为 `j_onset = 1 mA/cm2` | 是 |
| same_state | 同一态阶梯 | 无锂盐 -> C0 态 | 是 |
| min_species_covering_core_set | ≥ 7 个核心集分子 | 单序列 7 个可用分子 | 是（计数） |
| min_pairs | ≥ 18 个可用对 | 21 对 | 是（计数） |
| **min_tau_b** | **≥ 0.90** | **0.4286** | **否（决定性）** |
| primary_source_provenance | 序列回溯到一次原始测量 | 0/14 行升级，全部 `transcription_only_not_reverified_against_primary` | 否 |
| absolute_calibration_upgrade | ≥ 1 行升级 | 0/31 | 否 |

三条未达成。其中 **tau_b = 0.4286 < 0.90** 是唯一给出 `ordering_disagrees` 的
否决项；provenance 与绝对标定两条是「输入本身还没被回溯到一次可复现的测量」。

### 2.3 为什么是「不可闭合」而不是「还没做完」

> 在预注册要求的同装置 / 同判据 / 至少 7 个核心集分子的同源序列条件下，公开可验证数据不足，
> 因此无法完成排序层外部锚定。

并且**措辞边界必须同时发布**：

```text
NOT CLOSABLE
!=  NO SUCH DATA EXIST ANYWHERE
=
NO SUFFICIENTLY VERIFIED DATA WERE LOCATED
UNDER THE PRE-REGISTERED DISCOVERY / VALIDATION CRITERIA
```

这是**可被证伪的负结果**：若日后出现满足全部预注册条件的同源序列，本判定应被该数据推翻。
**不允许**用「删分子 / 换模型列 / 放宽容差」把它「救」成 PASS。

## 3. anchor 条件一致性与 provenance 复核（一行未删）

| anchor 文件 | 相 | 行数 | series | 可用于排序层 | provenance |
| --- | --- | --- | --- | --- | --- |
| `within_series_ordering.csv` | solution | 14 | Ue1994_Okoshi2015 | 是 | transcription_only_not_reverified_against_primary |
| `ue1994_okoshi2015_oxidation.csv` | solution | 14 | Ue_refs12_Okoshi2015_Fig1 | 是 | transcription_only |
| `doe_apr2016_reduction_secondary.csv` | solution | 3 | DOE_APR_FY2016 | 否（secondary：两种电芯 / 两种判据） | transcription_only |
| `solution_redox_anchors.csv` | solution | 31 | (无 series) | 否（全为 `est` 估计值） | est |
| `gas_phase_anchors.csv` | gas | 39 | (气相) | 否（不同层级） | calc;exp;na |

合计 **101 行 anchor 全部保留**。31 行绝对标定 anchor 逐行给出未升级原因
（`condition_mismatch` / `source_does_not_cover_species` /
`source_does_not_provide_value` / `computational_not_retrieved` /
`mis_citation` / `review_trend_only` / `no_reference` /
`solvent_anion_coupling`），见 `anchor_row_audit.csv`。
**没有任何一行因为「不一致」被删除**——它们本来就只是 estimates。

## 4. 排序一致性层：独立重算 vs 冻结值

| 量 | 独立重算 | 冻结值（Week 25） | 绝对差 |
| --- | --- | --- | --- |
| n_rows | 14 | 14 | 0 |
| n_pairs | 21 | 21 | 0 |
| concordant | 15 | 15 | 0 |
| discordant | 6 | 6 | 0 |
| tau_b | 0.428571 | 0.428571 | 0 |

重算只读 `data/anchors/within_series_ordering.csv` 与
`outputs/week4/p1_core_set_derived.csv`，口径与冻结阈值一致，**逐位对账通过**。
因此 `tau_b = 0.4286` 不是一次报告事故，而是可复现的判定。

## 5. 结论-轨道映射

| ID | 主结论 | 轨道 |
| --- | --- | --- |
| A1 | 缺失物理会改变一部分候选对的决策状态（robust inversion = 0，UNRESOLVED 占比可观） | Track A |
| A2 | P1v 与 P1a 的垂直-绝热差异本身足以翻转个别候选对（n=12，tau_b=0.788，robust inversion=2） | Track A |
| A3 | C1 还原态身份分层使主排序样本塌到 n=1，该条件下排序无定义 | Track A |
| A4 | 候选可被分成确定 / 边界 / 未解析三类（resolution map） | Track A |
| A5 | Δ-learning 在 LOFO 下 6/8 组合 tau_b 更好，但收益只部分转化为 Top-k / regret | Track A |
| A6 | 池内预算-收益曲线可用；family-held-out 的 AL 曲线不可用；池内端点 tau_b=1.0 是自检端点 | Track A |
| B1 | 绝对电位尺度可与真实实验条件匹配比较 | Track B（**未建立**） |
| B2 | within-series 相对排序被 target model 复现（tau_b ≥ 0.9） | Track B（**未建立**） |
| P1 | 被 designated target 排到前面的候选在真实体系里同样更稳定 | 待验证推断 |
| P2 | 昂贵标签预算可以外推到「真实筛选最少要多少张 DFT」 | 待验证推断 |

计数：**Track A 6 条 / Track B 2 条 / 待验证推断 2 条**。Track B 的两条是**未建立**，不是
「已否证」；P1 / P2 只有在 Gate 1 CLOSED 之后才可检验。

## 6. 措辞合规

扫描 **70 个交付文件**：禁用词出现 2 次，全部是**规则文本本身**（`validated target`
-> `designated computational target` 的对照表），**违规 0 处**；允许措辞出现 5 次。

## 7. 何时才值得新增电子结构计算

| 触发条件 | 优先补充什么 | 不建议做什么 |
| --- | --- | --- |
| P1v->P1a 的关键结论因样本太少无法判断 | 少量代表家族的绝热状态计算 | 无差别扩充全部分子 |
| C1 机制被 state identity 混杂 | 对有歧义的状态做局域化和结构 QC | 把 Li-centered 数据直接并入分子还原 |
| 独立不确定性无法估计 | 小规模跨方法 / 构象基准 | 继续使用自指 sigma 得出零反转结论 |
| LOFO 家族覆盖不足 | 有目的地增加欠代表家族标签 | 只增加已有家族的近似重复分子 |
| 外部 anchor 无法匹配计算条件 | 优先复核参考条件与目标定义 | 为关闭 Gate 1 调整阈值 |

真正要扩大的首先应当是**信息覆盖度**，而不只是任务数量。

## 8. 验收

| 问题 | 结论 |
| --- | --- |
| Q1. Gate 1 是否被跳过或强迫关闭？ | 都没有：维持 NOT CLOSED / NOT CLOSABLE，并作为可证伪的负结果报告 |
| Q2. 是否为了提高 tau 人为剔除数据？ | 否：5 个 anchor 文件 101 行全保留，tau_b 独立重算与冻结值逐位一致 |
| Q3. 每个主结论是否注明轨道？ | 是：10 条主结论全部标注（Track A 6 / Track B 2 / 待验证推断 2） |
| Q4. 论文适用范围是否限定？ | 是：限定在 computational-target decision stability；Track B CLOSED 之前不得推广 |

## 9. 限制

- 零新增计算；Gate 1 仍 NOT CLOSED / NOT CLOSABLE。本阶段不产生任何新的物理结论。
- `NOT CLOSABLE != NO SUCH DATA EXIST ANYWHERE`：这是可被证伪的负结果。
- within-series 表的 14 行 provenance 均为 `transcription_only_not_reverified_against_primary`：
  排序层的**输入本身**尚未回溯到一次可复现的原始测量。
- 本阶段的 10 条主结论标签是**边界声明**，不是新的证据；Week 35 / Paper 必须沿用这些标签。
- 下一步：Week 35 / Paper（论文主文收敛，七图结构，结果六节固定顺序）。

## 10. 复现命令

```powershell
cd 电解液溶剂HB-Code
.venv\Scripts\python.exe scripts\build_week34_wp7_external_reference_boundary.py
.venv\Scripts\python.exe scripts\build_week34_wp7_external_reference_boundary.py --check
.venv\Scripts\python.exe -m pytest tests/test_week34_wp7_external_reference_boundary.py -q
.venv\Scripts\python.exe scripts\build_week34_deliverables.py
.venv\Scripts\python.exe scripts\build_week34_deliverables.py --check
```
