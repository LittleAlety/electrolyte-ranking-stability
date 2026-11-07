# FINAL CONCLUSIONS — 10 个问题（结论 → 数字 → evidence path → limitation）

> 由 `scripts/build_final_conclusions.py` 从 `outputs/` 的冻结产物确定性生成；`--check` 逐字节复核。
> 本文件是**研究成果索引**（只回答 10 个问题）；逐周工作日志见 `README.md`。
> **Scope**：本仓库不建立电解液溶剂的最终排行榜（见 `README.md` 顶部 Scope）。

## 读前必读（两个最容易误读的点）

1. **`f_robust_inv = 0` 不等于「排序稳定」。** Stage 10 的 20 个 (台阶, 轴) 组合里，robust inversion 最大值 = **0 observed**（没有任何 pair 被**反向证明**），同一批数据 `f_unresolved` 最高 **80.0%**（证据**不足以判定**方向）。正确读法：「不可判定主导」。唯一真正出现 robust inversion 的地方是 **P1v → P1a 绝热阶梯**（n = 12，robust inversion = 2）。

2. **`n = 18` 只支持四层里的三层。** 机制验证 = 可以成立；排序普适性 = 不能宣称；大规模筛选 = 未验证；方法学 proof-of-concept = 成立（完整表格见 `README.md`）。本文件所有结论都受此限制。

---

## Q1. cheap → target 会不会改变排序？

**结论**：**会。** 廉价代理量不能替代指定计算目标：P0 → P1v 已经把排序改写，终点 P0 → P2a 同样不一致；预注册判词 `A_cheap_proxy_already_stable` 被判 **NOT SUPPORTED**。

**数字**：P0→P1v 氧化 τ_b = **0.673**、还原 τ_b = **0.595**（n = 18，CI95 氧化 [0.39, 0.90]）；P1v→P2a 氧化 τ_b = 0.895（唯一接近阈值的一级）、还原 τ_b = 0.673；P0→P2a 氧化 τ_b = 0.673、还原 τ_b = 0.791。判词证据原文：「P0 -> P2 氧化轴上 tau_b = 0.673、Top-10% 重叠 0.000、后一层 f_unresolved = 0.229（见 p2_decision_stability.json 的 p0_to_p2）」

**Evidence path**：`outputs/week4/p1_decision_stability.json`、`outputs/week4/p2_decision_stability.json`、`outputs/week9/stage10_ladder.json`（verdicts）、`outputs/decision_state/decision_state_report.json`

**Limitation**：n = 18；τ_b 的 bootstrap CI 宽；子集抽样 N = 10 时 P0→P1 氧化 τ_b 抽样标准差 = **0.126**（`outputs/week10/stage11_sigma_anatomy.json`）——报 τ_b 必须同时报 N 与子集。本文件不给出任何绝对性能排名结论。

## Q2. 改变主要来自 mean shift 还是 dispersion？

**结论**：**离散度（dispersion）。** 排序是否被改写由位移的**离散度**主导；位移的平均幅度与 τ_b 的关系统计上不稳健。

**数字**：ρ(shift std, τ_b) = **-0.851**（percentile CI95 [-0.99, -0.42]，**不含 0**）；ρ(|mean shift|, τ_b) = **-0.535**（CI95 [-0.96, 0.25]，**跨 0**）；ρ(shift std, f_unresolved) = **0.894**。闭式恒等 `f_unresolved(z) = Pr(q_ij > √2/z)` 在 20 个点上与实测误差精确为 0（T4）。

**Evidence path**：`outputs/week22_hardening/stats_b1_b2.json`、`outputs/week9/stage10_ladder.json`（hypothesis_test）、`outputs/week10/stage11_sigma_anatomy.json`（theorems T1–T5）

**Limitation**：10 个点**不独立**：同一 rung 的两轴共享分子、相邻 rung 共享分子；bootstrap CI 把点当可交换 → **乐观**，只作 within-sample 稳定性检查。剔除条件态后 n = 6、ρ = -0.943（更强）——结论对子集选择不稳。

## Q3. 哪个轴更脆弱？

**结论**：**还原轴。** 还原轴的 σ 更大、unresolved 更高，是决策稳定性最脆弱的一侧（C0→C1 还原轴甚至出现负的 τ_b）。

**数字**：P0→P1v 还原轴 f_unresolved(P_target) = **62.1%**（氧化 15.7%）；P0→P2a 还原轴 **68.0%**（氧化 22.9%）；σ_median（P1v→P2a）还原 **0.217 eV** 对 氧化 0.198 eV；C0→C1 还原轴 τ_b = **-0.467**。

**Evidence path**：`outputs/week4/p1_decision_stability.json`、`outputs/week4/p2_decision_stability.json`、`outputs/week5/c1_decision_stability.json`、`outputs/decision_state/decision_state_report.json`

**Limitation**：气相阴离子不束缚（T1 里 18/18 阴离子 `unbound_anion`），因此还原轴在 P0/P1 层的代理量不是同一物理量；还原轴结论只以 P2 / C1 为载体。r2SCAN-3c 的 def2-mTZVPP 无弥散函数，不能裁断 0.01 eV 量级的阴离子束缚。

## Q4. dielectric 是否真的导致 ranking inversion？

**结论**：**没有观察到。** 介电层主要是数值平移，且不同 ε 之间自相似；但「没有 robust inversion」≠「排序稳定」。

**数字**：bare CPCM 扫描 ε ∈ {5、10、20、40}、n = 12 分子、144/144 作业 ok；两种 σ 约定下 max f_robust_inv（z = 1.0 / 1.96）= **0.00**（any_gt_0 = false）。ε = 5 时氧化 τ_b = 0.939（CI95 [0.73, 1.00]）；SMD 乙腈层 P1v→P2a 氧化 τ_b = 0.895 / 还原 0.673。

**Evidence path**：`outputs/week4/t3_cpcm_eps_scan_summary.json`、`outputs/week4/p2_decision_stability.json`、`outputs/week11/stage12_prescreen.json`

**Limitation**：bare CPCM 只含静电项（无 SMD 非静电项）；几何为 G1（vertical，未弛豫）；n = 12 子集；`f_robust_inv = 0` 的含义是「不可判定主导」，不是「稳定」。

## Q5. Li+ coordination 是否改变结论？

**结论**：**会，而且改变了量的身份。** Li⁺ 配位把还原轴从「分子还原」变成「Li 中心 / 混合还原」，主 ranking 必须只用 `molecule_centered_redox`。

**数字**：C0→C1 氧化位移均值 4.887 eV（std 0.595）、τ_b = 0.689；还原位移均值 -6.578 eV（std 0.832）、τ_b = **-0.467**；12 个还原态标签：`Li_centered_or_mixed_redox` 11 / `molecule_centered_redox` 1 → 分层后还原轴 n = 1，**排序无定义**。

**Evidence path**：`outputs/week9/stage10_ladder.json`、`outputs/week5/c1_decision_stability.json`、`outputs/state_identity/state_identity_stratification.json`、`docs/state_identity_protocol.md`

**Limitation**：C1 只覆盖 10 个分子 / 12 motif；C1 DFT 作业 91/92 ok（1 个 execution_failed）；分层后还原轴只剩 1 个分子，无法给任何还原排序结论。

## Q6. microsolvation 是否改变结论？

**结论**：**不推翻氧化轴结论，但它自己的偏移已让相当一部分 pair 不可判定。**

**数字**：C1→C2（all12）氧化 τ_b = **0.697**、还原 τ_b = 0.848；36/36 作业 ok；f_unresolved(shell2) 最高 **27.3%**；第三壳靶向符号检验（GFN2-xTB）n_jobs = 14，裁决 = `consistent_with_saturation`。

**Evidence path**：`outputs/week8/stage9_results.json`、`outputs/week8/stage9_summary.json`、`outputs/week23/shell3_xtb_sign_test.json`

**Limitation**：C2 是 **first-shell microsolvation（CN = 2）**，不是 second solvation shell；n = 12；第三壳只做 GFN2-xTB 符号 / 形状检验（`level_caveat`：绝对值不得与 r2SCAN-3c 阶梯并列）。

## Q7. conformer uncertainty 是否足以覆盖 ranking gap？

**结论**：**是（还原轴）。** 构象系综给出的不确定度 floor 足以覆盖还原轴的排序 gap，这正是还原轴不可判定的机制来源。

**数字**：T6 构象系综 32 构象 / 12 分子；组装出的 delta_m：氧化 **0.700 eV**、还原 **2.074 eV**，主导项均为 `method`；方法 σ：氧化 0.700 eV、还原 2.074 eV；构象 p90：氧化 0.091 eV、还原 0.230 eV。

**Evidence path**：`outputs/week6/t6_conformer_spread.json`、`outputs/week6/delta_m_frozen.json`

**Limitation**：T6 只做 12 分子子集、单分子平均 2–4 个构象（不是全局构象搜索）；delta_m 是**候选值**（`delta_m_frozen.json.status` = CANDIDATE - NOT YET WRITTEN INTO config/prereg.yaml）；构象分布来自 GFN2-xTB 优化的中性几何。

## Q8. SCF alternative 是否是真实物理态差异？

**结论**：**大多数是假象，少数是真不同态。** 单点能量差主要来自 SCF 落在不同（或较高）的局域解；一旦两条腿都允许几何弛豫，偏好大多反转。

**数字**：37 个 `moread_lower` 格：|Δ| 单点中位 **0.11983 eV** → 弛豫后 **0.00196 eV**（缩小 ~61×）；偏好反转 **32 / 37**；结局 distinct_lower 5 / distinct_higher 24 / same_higher 8。

**Evidence path**：`outputs/week18/stage19_relax_analysis.json`、`docs/28_week18_report.md`、`outputs/week23/targeted_two_guess.json`

**Limitation**：只对 `moread_lower` 的 37 格做（非全量）；材料阈值 1 meV；仍有 24 格弛豫后仍是不同态（真差异），未做路径 / NEB 级别的判定；结论限于 r2SCAN-3c 与这些 ε。

## Q9. 哪些额外计算最值得花预算？

**结论**：**先用 0 计算量的闭式判据 + 自相似律筛掉可预测的层级，再把预算集中到还原轴的构象 / 态身份靶向复核。**

**数字**：预算账本 §21（10 条）：PASS 4 / PARTIAL 4 / MISSING 2；判据预筛（z = 1.0）在 18 个点上标出 3 个「预测不可用」点：`P0_to_P1/oxidation` / `C0_to_C1/reduction` / `C1_to_C2/reduction`；介电自相似（Born 因子）最大相对散布 14.9%（氧化 1.0%）；三点点外推最大绝对误差 0.053 eV；AL 预算关键点 n_T = 9（C 轴）/ 15（E 轴）。

**Evidence path**：`outputs/week25/compute_budget_ledger.json`、`outputs/week11/stage12_prescreen.json`、`outputs/week7/stage8_al_results.json`、`outputs/week10/stage11_sigma_anatomy.json`

**Limitation**：仓库内**没有** CPU-core-hours / p90 作业成本 / frequency-only 成本字段（账本中 2 条 MISSING）→ 只能给相对预算，不能给绝对金额；AL 曲线只在 10 分子 common subset 上。

## Q10. Gate 1 最终为什么不能闭合？

**结论**：**因为预注册要求的同源序列在公开可验证数据里不存在。** Gate 1 = NOT CLOSED **且** NOT CLOSABLE，作为 negative result 记录。

**数字**：排序一致性层：τ_b = **0.4286 < 0.90**、n_pairs = 21（一致 15 / 不一致 6）→ `ordering_disagrees`；覆盖层：最长同装置 / 同判据同源序列 **k = 1**（要求 ≥ 7）；还原轴只有 3 个 pair（门槛 18）= 数据不足，不是不一致；绝对标定层：31 行仍 `est`，升级 0 行。

**Evidence path**：`outputs/week25/series_rel_ordering_check.json`、`outputs/week24_corealign/gate1_anchor_feasibility.md`、`outputs/gate1/gate1_dual_track.json`、`docs/gate1_negative_result.md`

**Limitation**：数值本身不得事后通过剔除分子 / 替换模型列 / 放宽容差「救回」；要闭合需要一条覆盖 ≥ 7 个核心集分子、同装置 / 同判据、描述符在溶剂间真有离散度的新同源序列 —— 这属于**新的实验数据**，不是新的计算量。

---

## 收口清单

**可以声称的**：机制（位移离散度决定排序是否被改写）、方法学（三态判据 + 分辨率曲线 + 最小信息预算）、已冻结产物的可复现性。

**不能声称的**：任何形式的绝对性能排名、排序规律的普适性、大规模筛选能力、`validated target` 一类措辞（Gate 1 闭合前禁用）。

**未决 / 下一步若有资源**：先补预算账本的 2 条 MISSING（CPU-core-hours、p90 作业成本），再做还原轴构象 / 态身份的靶向复核；不建议为 Gate 1 继续堆周次计算（它是 NOT CLOSABLE）。

**工程入口**：`scripts/build_final_conclusions.py --check`、`outputs/figures/F56_r13_summary.png`、`docs/47_clean_room_reproduction_audit.md`、`scripts/audit_clean_room.py`。

## 新阶段批次登记（physics_completion_v1）

本仓库另登记了一个**新批次** `physics_completion_v1`（`config/physics_completion_v1.yaml`，week37-week44）：
它把《电解液排序稳定性：物理证据补强与决策预算研究执行方案》登记为可追溯产物，**零数据剔除、零阈值改动**。
登记层不引入新计算，增量推进则在同一批次号下登记了新的 ORCA 作业（WP1 方法审计 128 个单点 + 32 条弛豫腿
+ 1 条 EMC-Li 几何准备；WP2 生产已折入 7 条腿），这些新计算只增补证据，
逐周镜像见仓库外 `成果输出（part2）/week37..week44`。
该批次**不改变本文件 10 个问题的任何答案**（Gate 1 仍为 NOT CLOSED / NOT CLOSABLE）；
其研究问题→结果→证据→限制另见 `docs/physics_completion_final_report.md`。
