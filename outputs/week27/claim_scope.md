# R15 — claim-scope 审计（对抗审计第 3 轮 · F 项）

> 本文档由 `scripts/audit_claim_scope.py` 对冻结文本现算。
> **只读：逐行扫描两份声明文档，不修改任何文件。**

## 0. 一句话结论

声明面（`README.md` · `FINAL_CONCLUSIONS.md`）上共 **10** 处命中过度声明词，**无一处未加限定**；8 条硬限定（Scope / NOT CLOSABLE / 反误读对 / 不建立最终排行榜 / Gate-1 措辞边界 / 解禁条件）全部在位。

判定：**PASS**。

## 1. 扫描范围（刻意限定）

- 声明面：`README.md`、`FINAL_CONCLUSIONS.md`
- 不扫描：docs/*_report.md (working logs) are excluded by construction

理由：每周报告是实验记录（必然出现“证明恒等式”“全局最优”一类技术词汇），不是对外声明面；
对外读者看到的声明只在上面两份文档里。边界明写在此，不隐藏。

## 2. 过度声明词扫描

| 位置 | 词 | 状态 | 原文 |
| --- | --- | --- | --- |
| `README.md:3` | definitive | **guarded** | > **Scope.** This repository does not establish a definitive electrolyte-solvent ranking. It studies the stability, instability, and information cost of ranking decisions under progressively more real |
| `README.md:5` | leaderboard_zh | **guarded** | > 本仓库**不**给出「18 个溶剂谁最好」的最终排行榜；它研究的是**排序决策**在逐步更真实的计算模型下的**稳定性 / 不稳定性 / 信息成本**。任何把本仓库引用成「最终性能排行榜」的读法都是误读。 |
| `README.md:12` | validated | **guarded** | > （R13 起：Gate 1 闭合前不称 *validated* target；外部有效性单独作为 negative result 报告，见 `docs/gate1_negative_result.md`。） |
| `README.md:18` | prove_zh | **guarded** | \| robust inversion \| **0 observed** \| 在 20 个 (台阶, 轴) 组合中，没有任何 pair 被**反向证明**（1σ 主口径） \| |
| `README.md:110` | prove_zh | **guarded** | - 证明并数值验证 4 条恒等式（T1–T4）+ 1 条精确分解（T5）；判据 `f_unresolved(z) = Pr(q_ij > √2/z)`，闭式与实测在 20 个点上误差**精确为 0**（`outputs/week10/stage11_sigma_anatomy.json`）。 |
| `README.md:160` | prove_zh | **guarded** | - 结论：「身份差异多数是真的，但单点上的能量偏好多数是假象」；0.02 Å 阈值只是描述列，不是「同一驻点」的证明。 |
| `README.md:227` | validated | **guarded** | \| 🔴 P0 \| Gate 1 双轨、停用 validated target \| `target_naming`、`docs/gate1_negative_result.md` \| |
| `FINAL_CONCLUSIONS.md:5` | leaderboard_zh | **guarded** | > **Scope**：本仓库不建立电解液溶剂的最终排行榜（见 `README.md` 顶部 Scope）。 |
| `FINAL_CONCLUSIONS.md:9` | prove_zh | **guarded** | 1. **`f_robust_inv = 0` 不等于「排序稳定」。** Stage 10 的 20 个 (台阶, 轴) 组合里，robust inversion 最大值 = **0 observed**（没有任何 pair 被**反向证明**），同一批数据 `f_unresolved` 最高 **80.0%**（证据**不足以判定**方向）。正确读法：「不可判定主导」。唯一真正出现 robust |
| `FINAL_CONCLUSIONS.md:121` | validated | **guarded** | **不能声称的**：任何形式的绝对性能排名、排序规律的普适性、大规模筛选能力、`validated target` 一类措辞（Gate 1 闭合前禁用）。 |

未加限定命中：**0**。

## 3. 硬限定是否在位

| id | 文件 | 作用 | 在位 |
| --- | --- | --- | --- |
| G1_scope_en | `README.md` | the English Scope sentence at the top of the README | ✅ |
| G2_not_closable | `README.md` | Gate 1 is reported as a negative result, not a to-do | ✅ |
| G3_anti_misread | `README.md` | the '0 robust inversions' anti-misread guard | ✅ |
| G3_anti_misread_pair | `README.md` | the matching half of the anti-misread guard | ✅ |
| G4_no_definitive_ranking | `FINAL_CONCLUSIONS.md` | the conclusion matrix repeats the hard scope | ✅ |
| G5_gate1_scope_caveat | `docs/gate1_negative_result.md` | NOT CLOSABLE is scoped to the discovery criteria, not to the world | ✅ |
| G6_lift_condition | `docs/gate1_negative_result.md` | 'validated' stays banned until Gate 1 closes | ✅ |
| G5b_caveat_machine_readable | `outputs/gate1/gate1_dual_track.json` | the scope caveat is also in the machine-readable Gate-1 record | ✅ |

## 4. 逐条发现

| id | 级别 | 说明 |
| --- | --- | --- |
| F1 | **PASS** | on the claim surface (README.md, FINAL_CONCLUSIONS.md) every over-claim term is guarded; 10 hits, 0 unguarded |
| F2 | **PASS** | all 8 hard guards are present in the frozen documents |
| F3 | **INFO** | the scanned surface is deliberately limited to the two claim documents; the per-week reports are laboratory notebooks, not claim surfaces, and are excluded by construction |

## 5. 纪律声明

- 本审计只读，不修改任何文本。
- 本审计不判断科学结论对错，只检查“声明范围”与“限定条件”。
- 被标记为 guarded 的命中不是错误；不同行的限定词就不算数。
