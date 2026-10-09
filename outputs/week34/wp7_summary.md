# Week 34 / WP7：外部验证与结论边界

> 阶段：下一阶段实施方案 WP7。产物目录 `outputs/week34/`，交付镜像
> `..\成果输出（part2）\week34/`。本文件由
> `scripts/build_week34_wp7_external_reference_boundary.py` 确定性生成，
> `--check` 逐字节复核。**零新增电子结构计算、零数据剔除、零阈值改动**。

## 0. 一句话结论

Gate 1 维持 **NOT CLOSED / NOT CLOSABLE**：它既没有被跳过，也没有被强迫关闭。预注册的 8 条关闭条件里有 **3 条**未达成（min_tau_b、primary_source_provenance、absolute_calibration_upgrade），其中决定性的一条是排序一致性 **tau_b = 0.4286 < 0.90**。

与之独立的是 Track A：WP1-WP6 的排序、选择与预算结论在 designated computational target 下成立，不受 Track B 未闭合影响。

## 1. 两条轨道：范围与结论权限

| 轨道 | 名称 | 状态 | 问题 | 可以下什么结论 | 升级条件 |
| --- | --- | --- | --- | --- | --- |
| Track A | decision-stability validity | computationally_established | which missing physics change the screening decision? | 可以在指定 designated computational target 下得出结论 | 无（本轨道独立成立） |
| Track B | external / experimental validity | NOT CLOSED / NOT CLOSABLE | 计算结果与实验或独立参考的一致性 | 只有参考证据支持时才能推广到真实筛选 | Gate 1（含排序一致性层）CLOSED；见 config/prereg.yaml |

**独立性规则**：Track B 未闭合**不**使 Track A 失效；它只限制「绝对尺度 / 真实排序」
这类声明的强度。

## 2. Gate 1 组件状态

| 组件 | 状态 | 观测值 | 阈值 | 对决策的意义 |
| --- | --- | --- | --- | --- |
| ordering_consistency | ordering_disagrees | kendall_tau_b=0.4286 over n_pairs=21 (concordant 15 / discordant 6) | min_pairs=18; min_tau_b=0.9 | 本组件未通过 = 无法把排序结论推广到真实筛选 |
| absolute_calibration | limitation (not a standalone blocker) | still_est=31/31; upgraded=0 | rows upgraded > 0 | 绝对电位不可与真实测量直接比较；只影响绝对尺度声明 |
| reduction_axis_secondary | not_evaluable_secondary_only | n_pairs=3 | min_pairs=18 | 数据不足（不是不一致）：还原轴不作为 Gate 1 的否决证据 |
| upstream_feasibility | not_closable_on_current_literature | longest homologous series k=1 | k >= 7 核心集分子 | 公开可验证的同源序列不足，说明不是「还没做完」 |
| closability | NOT CLOSABLE | 在预注册要求的同装置 / 同判据 / 至少 7 个核心集分子的同源序列条件下，公开可验证数据不足，因此无法完成排序层外部锚定。 | 预注册的同装置 / 同判据 / 同态 / >=7 分子同源序列 | Gate 1 作为 negative result 报告，不是待办缺陷 |

## 3. 预注册关闭条件逐条对账

| 条件 | 要求 | 现状 | 是否满足 | 备注 |
| --- | --- | --- | --- | --- |
| same_apparatus | one apparatus within the series | single series with one electrode (glassy carbon) | 是 | table-level 一致性由单 series 构造保证 |
| same_criterion | one criterion within the series | j_onset at 1 mA/cm2 throughout | 是 | table-level 一致性由单 series 构造保证 |
| same_state | same redox state tier | Li salt absent -> C0 tier | 是 | 锂盐缺席，对应 C0 态比较 |
| min_species_covering_core_set | >= 7 core-set molecules | 7 usable species in the single series | 是 | 计数满足；但 provenance 未升级（见下条） |
| min_pairs | >= 18 usable pairs | 21 pairs | 是 | 计数满足 |
| min_tau_b | >= 0.9 | tau_b=0.4286 | **否** | 决定性未通过项：ordering_disagrees |
| primary_source_provenance | series verified against the primary source | 0/14 rows verified beyond transcription; remainder repo_verification=transcription_only_not_reverified_against_primary | **否** | 0 行升级；与 W24-D 的 longest k=1 一致 |
| absolute_calibration_upgrade | rows upgraded > 0 | 0/31 rows upgraded | **否** | 记为 limitation（R7），但仍作为未达成条件列出 |

未达成：min_tau_b、primary_source_provenance、absolute_calibration_upgrade。注意「数据不足」不等于「数据不一致」：还原轴旁证只有 3 个 pair（门槛 18），
是**不足**而非**不一致**；唯一给出 ordering_disagrees 的是氧化轴。

## 4. anchor 条件一致性与 provenance 复核（一行未删）

| anchor 文件 | 相 | 行数 | series | 同装置 | 同判据 | 可用于排序层 | provenance |
| --- | --- | --- | --- | --- | --- | --- | --- |
| data/anchors/within_series_ordering.csv | solution | 14 | Ue1994_Okoshi2015 | 是 | 是 | 是 | transcription_only_not_reverified_against_primary |
| data/anchors/ue1994_okoshi2015_oxidation.csv | solution | 14 | Ue_refs12_Okoshi2015_Fig1 | 是 | 是 | 是 | transcription_only |
| data/anchors/doe_apr2016_reduction_secondary.csv | solution | 3 | DOE_APR_FY2016 | 否 | 否 | 否 | transcription_only |
| data/anchors/solution_redox_anchors.csv | solution | 31 | (none) | 是 | 是 | 否 | est |
| data/anchors/gas_phase_anchors.csv | gas | 39 | (none) | 是 | 是 | 否 | calc;exp;na |

31 行绝对标定 anchor 逐行保留、逐行给出未升级原因（见 `anchor_row_audit.csv`）；
**没有任何一行因为「不一致」被删掉**——它们本来就只是 estimates，不是条件匹配的测量。

## 5. 排序一致性层：独立重算 vs 冻结值

| 量 | 独立重算 | 冻结值 | 绝对差 |
| --- | --- | --- | --- |
| n_rows | 14 | 14 | 0 |
| n_pairs | 21 | 21 | 0 |
| concordant | 15 | 15 | 0 |
| discordant | 6 | 6 | 0 |
| tau_b | 0.428571 | 0.428571 | 0 |

重算只读 `data/anchors/within_series_ordering.csv` 与
`outputs/week4/p1_core_set_derived.csv`，口径与冻结阈值一致，逐位对账通过。
因此「tau_b = 0.4286」不是一次报告事故，而是可复现的判定。

## 6. 结论-轨道映射（每个主结论都要贴标签）

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

计数：Track A 6 条 / Track B 2 条 / 待验证推断 2 条。
Track B 的两条（B1 绝对标定、B2 排序一致性）是**未建立**，不是「已否证」；
待验证推断的两条（P1 / P2）只有在 Gate 1 CLOSED 之后才可检验。

## 7. 措辞合规

扫描 70 个交付文件：禁用词出现 2 次，全部是**规则文本本身**（禁用->允许 对照），
违规 **0** 处；允许措辞 `designated computational target / designated reference model` 出现 5 次。


## 8. 何时才值得新增电子结构计算

| 触发条件 | 优先补充什么 | 不建议做什么 |
| --- | --- | --- |
| P1v->P1a 的关键结论因样本太少无法判断 | 少量代表家族的绝热状态计算 | 无差别扩充全部分子 |
| C1 机制被 state identity 混杂 | 对有歧义的状态做局域化和结构 QC | 把 Li-centered 数据直接并入分子还原 |
| 独立不确定性无法估计 | 小规模跨方法 / 构象基准 | 继续使用自指 sigma 得出零反转结论 |
| LOFO 家族覆盖不足 | 有目的地增加欠代表家族标签 | 只增加已有家族的近似重复分子 |
| 外部 anchor 无法匹配计算条件 | 优先复核参考条件与目标定义 | 为关闭 Gate 1 调整阈值 |

真正要扩大的首先应当是**信息覆盖度**，而不只是任务数量；并且**不允许**为关闭 Gate 1
而调整阈值。

## 9. 验收

| 问题 | 结论 | 支撑 | 证据 |
| --- | --- | --- | --- |
| Q1. Gate 1 是否被跳过，或被人为强迫关闭？ | 既未跳过也未强迫关闭：保持 NOT CLOSED / NOT CLOSABLE；作为可证伪的 negative result 报告 | 8/8 | 未达成条件：min_tau_b; primary_source_provenance; absolute_calibration_upgrade |
| Q2. 是否为了提高 tau 人为剔除了一致性不足的数据？ | 否：5 个 anchor 文件全部保留（31 行 est 仍在、3 行 DOE 仍记为 secondary、14 行 within-series 未筛）；tau_b 独立重算与冻结值一致 | 5/5 | 独立重算 tau_b=0.4286 vs 冻结 0.4286；concordant/discordant=15/6 |
| Q3. 每个主结论是否注明 Track A / Track B / 待验证推断？ | 是：10 条主结论全部标注（Track A 6 条 / Track B 2 条 / 待验证推断 2 条） | 10/10 | A1=Track A;A2=Track A;A3=Track A;A4=Track A;A5=Track A;A6=Track A;B1=Track B;B2=Track B;P1=待验证推断;P2=待验证推断 |
| Q4. 论文适用范围是否被限定？ | 是：论文适用范围限定在 computational-target decision stability；只有在 Track B（含排序一致性层）CLOSED 之后才可推广到真实筛选 | 6/10 | 禁止项：validated target / 绝对性能排名 / 大规模筛选能力；措辞合规扫描 70 个文件、违规 0 处 |

## 10. 限制

- 零新增计算；Gate 1 仍 NOT CLOSED / NOT CLOSABLE。本阶段不产生任何新的物理结论。
- **NOT CLOSABLE != NO SUCH DATA EXIST ANYWHERE**：这是可被证伪的负结果，若日后出现满足
  全部预注册条件（同装置 · 同判据 · 同态 · >=7 个核心集分子的同源序列）的数据，应被推翻。
- within-series 表的 14 行 provenance 均为 `transcription_only_not_reverified_against_primary`：排序层的输入本身尚未回溯到一次可复现的原始测量。
- 本阶段的 10 条主结论标签是**边界声明**，不是新的证据；下一阶段（Week 35 / Paper）
  必须沿用这些标签。

## 11. 复现命令

```powershell
cd 电解液溶剂HB-Code
.venv\Scripts\python.exe scripts\build_week34_wp7_external_reference_boundary.py
.venv\Scripts\python.exe scripts\build_week34_wp7_external_reference_boundary.py --check
.venv\Scripts\python.exe -m pytest tests/test_week34_wp7_external_reference_boundary.py -q
```

