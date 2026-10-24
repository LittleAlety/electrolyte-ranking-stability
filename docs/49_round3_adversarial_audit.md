# R15 — 第三轮：对抗式科学审计（adversarial scientific audit）

- 日期：2026-10-08
- 类型：对抗审计（adversarial audit），**零新增电子结构计算**
- 目标：**不再产生新科学结果，而是用已冻结的产物攻击现有结论**
- 产物：`outputs/week27/`（5 个审计 JSON/MD）、`outputs/figures/F57`+`F58`、`src/electrolyte_ranking/robustness.py`、`tests/test_round3_adversarial_audit.py`
- Gate 状态：`Gate 0` **CLOSED**；`Gate 1` **NOT CLOSED 且 NOT CLOSABLE**（不变；本轮只加固措辞边界）

第三轮评审的要求是：进入第二阶段，找只有严苛 reviewer / 复现者 / 领域专家才可能抓到的问题，把仓库从「完成度很高的计算研究项目」推进到「可冻结、可投稿、可接受外部审查的研究 artifact」。评审给出 7 个方向（A–G），并明确禁止为了救结果而补规模、改阈值、堆周次。

本文档回答：**这 7 个方向各自查了什么、结果如何、哪几条口径必须改写。**

---

## 0. 结论

> **结论没有被推翻，而是被重新推导成了代数必然；headline 不变，且更强。**

原先的主结论是「证据不足以识别排序」。本轮证明：在被冻结的那套约定下，最容易被误读的两个数字 —— `f_robust_inv = 0` 与「未观测到结构集中型 robust inversion」—— **不是经验观察，而是恒等式**。这使主结论从「我们没看到」升级为「在这套约定下不可能看到」，并且顺带指出：真正需要改写的不是结论，而是三条**措辞**。

| 优先级 | 方向 | 本轮落地 | 位置 |
| --- | --- | --- | --- |
| 🔴 A | 指标定义稳健性 | 双源 sigma 自指性审计（T1/T6a/T6b/T7） | `scripts/audit_estimator_circularity.py`、`src/electrolyte_ranking/robustness.py` |
| 🔴 A/B | 排序可识别性 | 4 种 unresolved 口径政策带 + 可分层计数 | `scripts/audit_metric_robustness.py`、F57 |
| 🔴 C | 选择 / 多重比较 | 确认性 vs 探索性清点 + 族校正核查 | `scripts/audit_selection_multiplicity.py` |
| 🟠 D | 模型层独立性 | 20 个同轴 rung 对的位移相关 + 信息增益矩阵 | `scripts/audit_layer_independence.py`、F58 |
| 🟠 E | 负结果稳健性 | NOT CLOSABLE 的措辞边界（不对 absence of evidence 作过度推论） | `outputs/gate1/gate1_dual_track.{json,md}`、`docs/gate1_negative_result.md`、README |
| 🟠 F | 声明范围 | claim surface 过度声明扫描 | `scripts/audit_claim_scope.py` |
| 🟡 G | 复现 | F57/F58 纳入站点与冻结清单；新增 R15 测试 | `scripts/freeze_gates.py`、`scripts/build_terminal_site.py`、`tests/test_round3_adversarial_audit.py` |

---

## 1. 🔴 A：这套不确定性估计器是不是自指的

`outputs/week27/estimator_circularity.json`（`--check` 通过）。审计对象是「`sigma_ij` 与解析判据是否耦合」。

- **T1（已知）**：双源 sigma `sigma_ij = |dP_A - dP_B| / sqrt(2)`（最大误差 **8.88e-16 eV**）——它是**被比较的两个模型自身之差**，不是独立噪声。
- **T6a（本轮新）**：`ROBUST_INVERSION` 要求 `z <= 1/sqrt(2) = 0.7071`；冻结主口径 `z = 1.0`、敏感性 `z = 1.96` 都超过它 → `f_robust_inv = 0` 是**定义性不变量**。
- **T6b（更强）**：双方都解析的子集里，反向 pair **恒为 0**（8 个 block × 2 个 z 全为 0）——这套流水线**根本不能认证任何分歧**。
- **T7**：解析判据只依赖 `|dY| / |dX|` 的**纯比值律**，不含任何绝对能量尺度。
- **阳性对照**：同一批分子、同一批层，只把 sigma 换成 4 个裸 CPCM 电介质汇聚的 R = 5 多来源 sigma，`f_robust_inv` 立刻出现 **0.0196**（1 对真反转）。

**结论**：主结论不需要改；但 `f_robust_inv` 从此必须与它的 sigma 约定、以及那个**空分母**一起报告。

## 2. 🔴 A/B：支配性失效模式不是「反转」，而是「不可识别」

`outputs/week27/metric_robustness.json` + `outputs/figures/F57_metric_robustness.png`。冻结 0.90 门槛，把 4 种 unresolved 口径全跑一遍（8 个 block = 4 台阶 × 2 轴）：

- **8/8 block 的结论随口径翻转**：同一批数据在 optimistic 下过 0.90、在 pessimistic 下不过；政策带宽度 **0.366–1.822**（中位 0.908）。
- `f_tie`（证据无法解析的 pair 占比）区间 **0.183–0.911**；带宽度恰为 `2 * f_tie`。
- 可分层数（把相邻不可解析处置断开）：**11–17 / 18**，C0→C1 还原 block 只剩 **6 / 10**，最大一层 **3 个分子并列**；近临界 pair（比值 ∈ [1, 1.25)）**1–17 个**。
- 同时：点排序本身一致（`rho ≈ 0.80`）。

**读法纪律（本轮硬性）**：`tau_b` 是全排序点统计量；说「稳定 / 不稳定」必须给政策带或 `f_unresolved`；**不得**把「18 分子 → 11–17 层」读成「排序已确定」。支配性失效模式是 **loss of rank identifiability**。

## 3. 🔴 C：选择 / 多重比较审计

`outputs/week27/selection_multiplicity.json`。判定 **PASS**。

- 确认性端点由 `config/prereg.yaml` 写成（6 条 `must_report`）；p 值只出现在 **6 个文件 / 86 个单元**。
- 唯一产生过「筛选声明」的家族（Stage 11 的 9 个 predictor）带 **Bonferroni + Holm**，两种校正下 **0 条存活**（`outputs/week22_hardening/multiple_compare_b3.json`）。
- 另 3 个探索性家族带未校正置换 p 值（Stage 16 / Stage 18 / Stage 3 锚点比较）；它们**没有被当作确认性结论引用**，Stage 16 自己已写明所选规则不敌多数类基线。
- 决策阈值：全仓库 `threshold_decision_error` 共 36 个键，**全部为 null + `not_applicable` 注记**，0 个数值型 → 没有事后挑阈值。
- `post_hoc` 量共 **65** 个叶子，全部写在键名里、只当上界用。

## 4. 🟠 D：模型层真的「独立」吗

`outputs/week27/layer_independence.json` + `outputs/figures/F58_layer_independence.png`。判定 **PASS**。

从冻结 CSV / JSON 重建每一级的逐分子位移向量（`p_ox = IP`，`p_red = -EA`），再算：

- **不冗余**：20 个同轴 rung 对的位移 |Pearson| **中位 0.383、最大 0.791**，仅 2 对 > 0.7 → 各层不是同一信号的再编码。
- **但阶梯是分解，不是独立证据**：共享 P1 锚点在两个冻结文件间最大偏差 **0.00e+00 eV**，因此 `P0→P2 ≡ (P0→P1) + (P1→P2)` 是严格恒等式。
- **信息量 = dispersion**：按 T3，常数位移免费；`rigidity = |mean|/std` 量化每级有多接近「免费的刚性平移」。
- **最贵的一级才是改变决策的一级**：C0→C1 花了 **92** 个 job，是唯一真正伤排序的一级（还原轴 `tau_b = -0.4667`、`f_unresolved = 0.800`）；而最便宜的几何级 G1→G2（**48** job）几乎不动排序。

## 5. 🟠 E：NOT CLOSABLE ≠ 世上不存在这类数据

Gate 1 的定性不变（**NOT CLOSED 且 NOT CLOSABLE**），本轮只加固措辞，防止把 absence of evidence 读成 evidence of absence：

```text
NOT CLOSABLE
≠  NO SUCH DATA EXIST ANYWHERE
=
NO SUFFICIENTLY VERIFIED DATA WERE LOCATED
UNDER THE PRE-REGISTERED DISCOVERY / VALIDATION CRITERIA
```

机器可读形式：`outputs/gate1/gate1_dual_track.json` 的 `track_B.components.closability.scope_caveat` / `.scope_caveat_en`；文档见 `docs/gate1_negative_result.md` §1c；README 的 Gate 1 条目同步。**这是一条可被证伪的负结果**：若日后出现满足全部预注册条件的同源序列，该判定应被推翻。

## 6. 🟠 F：声明范围审计

`outputs/week27/claim_scope.json`。判定 **PASS**。

- 扫描面刻意限定为两处对外声明面：`README.md`、`FINAL_CONCLUSIONS.md`（每周报告是实验记录，必然出现「证明恒等式」「全局最优」等技术词，**不**属于声明面；边界明写在报告里）。
- 过度声明词命中 **10** 处，**0 处未加限定**（其余全在 `does not` / `禁止` / `不称` / `没有` / `恒等式` 等同行的限定语内）。
- 8 条硬限定全部在位：英文 Scope 句、`NOT CLOSABLE`、`0 robust inversions` / `0 ranking instability` 防误读对、`FINAL_CONCLUSIONS` 的「不建立最终排行榜」、Gate-1 措辞边界、解禁条件 `lift_condition`。

## 7. 🟡 G：把 R15 纳入可复现面

- `outputs/figures/F57`、`F58` 登记进 `scripts/build_terminal_site.py` 的 `FIGURES`（图集 57 → **59**），`tests/test_terminal_site.py` 同步。
- `scripts/freeze_gates.py` 的 Stage-2 清单新增 R15 的 5 个脚本、`robustness.py`、`docs/49_*.md`、`outputs/week27/**/*`、`tests/test_round3_adversarial_audit.py`。
- 新增 `tests/test_round3_adversarial_audit.py`：逐脚本 `--check` 逐字节、两个新图 hash 与 manifest 对齐、`robustness.py` 代数恒等式、Gate-1 措辞边界、R15 产物零机器路径。
- clean-room 审计（`scripts/audit_clean_room.py`）的 C6 行数随冻结清单增长更新（见 `docs/47`）。

## 8. 三条必须改写的口径

本轮唯一的「改动」就是这三条口径（不是结果）：

| # | 旧读法 | 新读法 |
| --- | --- | --- |
| 1 | `f_robust_inv = 0` 是「未观测到反转」这一负结果 | 在冻结双源 sigma + `z > 1/√2` 下它是**定义性恒等式**（T6a/T6b）；必须与 sigma 约定和（空）分母一起报告 |
| 2 | 预注册假设 C「结构集中型 robust inversion」= `NOT OBSERVED` | 改为 **`NOT TESTABLE`**（该约定下不可能观测）；换 R ≥ 3 多来源 sigma 即可检验（阳性对照 `f_robust_inv = 0.0196`） |
| 3 | `f_unresolved` 是「能量尺度上的不确定度」 | 它是 `|dY| / |dX|` 的**纯比值律**（T7），不含绝对能量尺度 |

## 9. 本轮**不做**的事（拒绝项）

- 不把 core set 扩到 60–100、broad pool 扩到 300–1000。
- 不把 Gate 1 做成 PASS（不改判据、不剔分子、不放宽阈值）。
- 不为「看起来完整」再堆 Week 28/29 或大量图。
- 不改 week1–week26 的任何既有产物数字。
- 不修改任何已经通过的阈值。

## 10. 证据链

| 事实 | 来源 |
| --- | --- |
| T1 / T6a / T6b / T7 与三条口径改写 | `outputs/week27/estimator_circularity.json`、`src/electrolyte_ranking/robustness.py` |
| 政策带 8/8 翻转、可分层 11–17 / 18 | `outputs/week27/metric_robustness.json`、`outputs/figures/F57_metric_robustness.png` |
| 9 个 predictor 的 Bonferroni / Holm（0 存活） | `outputs/week22_hardening/multiple_compare_b3.json` |
| 阈值 `not_applicable`、65 个 post-hoc 叶子 | `outputs/week27/selection_multiplicity.json` |
| rung 位移相关中位 0.383 / 最大 0.791、P1 锚点偏差 0 | `outputs/week27/layer_independence.json`、`outputs/figures/F58_layer_independence.png` |
| Gate-1 措辞边界 | `outputs/gate1/gate1_dual_track.json`、`docs/gate1_negative_result.md` §1c |
| 声明面 10 命中 / 0 未限定、8 条硬限定 | `outputs/week27/claim_scope.json` |

本文件与上述全部产物一致；`scripts/freeze_gates.py` 重跑后 Gate 0 仍 CLOSED、Stage-2 清单重新冻结。