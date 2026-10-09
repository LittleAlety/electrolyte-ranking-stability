# Week 36 独立数字复算审计报告

**审计对象**：结题论文 v7（`电解液溶剂氧化还原描述符决策稳定性_结题论文_v7.docx`）与 Week 35 冻结溯源记录（`outputs/week35/paper_number_lineage.csv`，L01–L16）。
**审计方式**：不信任 Week 35 已写好的 CSV 结论，一律回到冻结源文件**重新独立复算**后再比对。
**审计日期**：2026-10-09。

> **编者按（结题汇编时补记，2026-10-09）**：本报告是审计时点的记录，其复算结论（L01–L16 全部 OK、
> 0 MISMATCH）不因后续收尾而改变。审计之后为结题提交做了三件事，与读者相关：
> 1. docs/50 的过期数字（2062 行 / `property_table` 380 行、§5 只列 8 个 rung）已按冻结载荷改为
>    **2074 行 / 392 行 / 11 个 rung**，并重建 week28 镜像（见 `SUBMISSION.json` 的 D1）。
> 2. 论文 v7 重建后，week35 的措辞合规载荷由 **1272 行 / 0 处允许措辞 / `naming_update_required = True`**
>    重建为 **1499 行 / 7 处 / False**；week34 的命名扫描随 docs/50 行数刷新（见 D4）。
> 3. 因此本报告「残留提示」中『仓库 v7 生成器与 week35 冻结镜像的 `44c026c5…`（v6）不同』的观察
>    已不再成立：week35 镜像现与仓库同为 v7，`build_week35_deliverables.py --check` 已是 43 files
>    byte-identical。v6 原件保留为 `论文/_backup_build_paper_docx_v6.py`（sha256 仍为 `44c026c5…`），
>    其哈希可独立复核。
>
> 结题最终状态一律以 `SUBMISSION.json` / `verification.json` 为准。**纪律**：只读既有文件；未修改任何既存文件；未运行任何会写盘的构建脚本（`build_week35_deliverables.py` 仅以 `--check` 只读运行）。

## 0. 环境与工具

- 仓库：`E:\Claude Code\电解液溶剂-HB\电解液溶剂HB-Code`（shell = PowerShell，读文件用 `Get-Content -Encoding UTF8`）。
- 计算用解释器：`.venv\Scripts\python.exe`（Python 3.10.11，无第三方包）。
- 读 .docx 用解释器：`C:\Users\Little Alety\AppData\Local\Programs\Python\Python310\python.exe`（含 python-docx）。
- CSV 数值比较一律经 `float()`，不做字符串比较。

## 1. 溯源数字复算对照表（L01–L16）

镜像根：`E:\Claude Code\电解液溶剂-HB\成果输出（part2）\week35\<source>`。源 sha256 = CSV 记录的 `source_sha256`；镜像 sha256 = 镜像文件实测值。所有 16 行的**源 sha256 均与记录一致、镜像文件均存在且与源逐字节一致**（9 个不同的源文件，全部 MATCH）。

| number_id | metric | 记录值 | 复算值 | float 差 | 源 sha256 匹配 | 镜像匹配 | 独立复算方法 | 判定 |
|---|---|---|---|---|---|---|---|---|
| L01 | Gate 1 排序一致性 Kendall tau_b | 0.42857142857142855 | 0.42857142857142855 | 0.0 | MATCH | MATCH | 由 `data/anchors/within_series_ordering.csv` × `outputs/week4/p1_core_set_derived.csv` 的 p1_ox_ev 重算 21 对 → C=15/D=6 | OK |
| L02 | Gate 1 within-series 可用 pair 数 | 21 | 21 | 0.0 | MATCH | MATCH | 7 个可配对物种 C(7,2)=21 | OK |
| L03 | Gate 1 concordant | 15 | 15 | 0.0 | MATCH | MATCH | 同上重算，一致对数 = 15 | OK |
| L04 | 溶液相 anchor 仍为 estimates 的行数 | 31 | 31 | 0.0 | MATCH | MATCH | `solution_anchor_audit.json`：len(rows)=31，且全部 decision 全为 est 值、still_est_count=31 | OK |
| L05 | P0→P1v 氧化轴 tau_b | 0.673202614379085 | 0.673202614379085 | 0.0 | MATCH | MATCH | `decision_state_report.json` rungs[P0->P1v].oxidation.kendall_tau_b | OK |
| L06 | P0→P1v 氧化轴 UNRESOLVED pair 数 | 70 | 70 | 0.0 | MATCH | MATCH | 同源 decision_state_counts.UNRESOLVED=70（83+70+0=153） | OK |
| L07 | P1v vs P1a 绝热阶梯分子数 | 12 | 12 | 0.0 | MATCH | MATCH | `p1v_vs_p1a.json` len(per_molecule)=12 | OK |
| L08 | P1v vs P1a tau_b | 0.7878787878787878 | 0.7878787878787878 | 0.0 | MATCH | MATCH | 由 per_molecule 的 ip_p1v_ev × ip_p1a_ev 重算 66 对 → C=59/D=7 → 52/66 | OK |
| L09 | P1v vs P1a ROBUST_INVERSION 数 | 2 | 2 | 0.0 | MATCH | MATCH | decision_state_counts.ROBUST_INVERSION=2 | OK |
| L10 | 反转不可能阈值 z* = 1/√2 | 0.7071067811865475 | 0.7071067811865475 | 0.0 | MATCH | MATCH | `estimator_circularity.json` theorems.T6a_inversion_impossible.z_max_for_inversion | OK |
| L11 | 双方解析子集最大反向 pair 数（T6b） | 0 | 0 | 0.0 | MATCH | MATCH | theorems.T6b_no_certifiable_disagreement.max_n_discordant_both=0；另逐块核 3×2 个 n_discordant_both 全为 0 | OK |
| L12 | WP5 与 Stage 7 对账的 OOF 预测行数 | 288 | 288 | 0.0 | MATCH | MATCH | `wp5_delta_learning.json` reconciliation.n_rows_compared=288、n_exactly_identical.top_k_overlap_20=288 | OK |
| L13 | 主动学习曲线单元格数 | 296 | 296 | 0.0 | MATCH | MATCH | `stage8_al_results.json` len(curves)=296；Week 33 独立重算 n_cells=296 | OK |
| L14 | 主动学习逐 repeat 记录数 | 5920 | 5920 | 0.0 | MATCH | MATCH | counts.n_run_rows=5920 | OK |
| L15 | WP2 主表行数 | 299 | 299 | 0.0 | MATCH | MATCH | `wp2_physics_response.json` n_rows_total=299 | OK |
| L16 | WP4 主表行数 | 918 | 918 | 0.0 | MATCH | MATCH | `wp4_decision_identifiability.json` n_rows_total=918 | OK |

**复算表计数：OK = 16，MISMATCH = 0，UNVERIFIABLE = 0。**

源文件 sha256 实测（与 CSV 记录逐字一致）：

- `outputs/week25/series_rel_ordering_check.json` = `9eac280f1edc6def1d390c03c216abbb1a2e30e8cbd7a8693597abd2178949ae`（L01/L02/L03）
- `outputs/week2/solution_anchor_audit.json` = `bec6f71270fac92066cfe1cc9239e012d2e595f48c84fa1ec233d3b111e34719`（L04）
- `outputs/gate1/gate1_dual_track.json` = `2487b779530d43ff80b6a5e603e5aaac1662ee94f66ff652772cf87324b5b0e1`（L05/L06）
- `outputs/phase2_p1a/p1v_vs_p1a.json` = `71c7fad051e82a47cb08a95c29e285a7fad974d293268c7fc0827eca261501f0`（L07/L08/L09）
- `outputs/week27/estimator_circularity.json` = `7701e27c1bd56586ea30e948785448505b4ea605d59522a8dfd7412387f9c757`（L10/L11）
- `outputs/week32/wp5_delta_learning.json` = `2e641278b7b63d1b3c3ea7292fb3c6849869eb46cf1ed26dcb57a41038e55625`（L12）
- `outputs/week7/stage8_al_results.json` = `d2a6298cb47f604a32b0fb92f9b7812cfe1475b03417317e15ed54f71aa069fd`（L13/L14）
- `outputs/week29/wp2_physics_response.json` = `9470afb7b3843b5ba7dd8e256098bd0a245eca2d533aade6e06703e4090a6515`（L15）
- `outputs/week31/wp4_decision_identifiability.json` = `8e3ffd7e6fa2c9801a6e2b0425d69077134bc63a5f0612d56b58fb0b14312afd`（L16）

镜像自洽性抽查：`..\成果输出（part2）\week35\outputs\week35\paper_number_lineage.csv` 实测 sha256 = `db4efe52b1d49e7b65aa4dfba214fa10bb124dac0c607a37d9662afaf5a11310`，与 `week35\SHA256SUMS` 第 34 行记录一致；`paper_convergence.json` 实测 = `fa99551c5004bf3e7e3590e4e93ab9d775d7196f13407f1d3afee1aaee1e4560`，与 SHA256SUMS 第 30 行一致。

## 2. docx 结构性检查

文件：`E:\Claude Code\电解液溶剂-HB\论文\电解液溶剂氧化还原描述符决策稳定性_结题论文_v7.docx`（存在，大小 5,737,606 字节；python-docx 解析成功）。

| 检查项 | 期望 | 实测 | 判定 |
|---|---|---|---|
| 内嵌图数量 inline_shapes | 24 | 24 | OK |
| 表格数量 tables | 19 | 19 | OK |
| 段落数 paragraphs | — | 293 | 记录 |
| 禁用词 `validated target` 次数 | 0 | 0 | OK |
| 禁用词 `physically validated target` 次数 | 0 | 0 | OK |
| `designated computational target` 次数 | >0 | 5 | OK |
| `designated reference model` 次数 | >0 | 2 | OK |

**结果六节标题（按固定顺序，正文实际顺序）**：

1. `3.1  模型层级与外部参考边界`
2. `3.2  电子结构与介质物理如何改变排序`
3. `3.3  Li+ 配位条件态与还原态身份`
4. `3.4  不确定度感知的材料筛选`
5. `3.5  模型位移与配位修正的可预测性`
6. `3.6  最小昂贵信息预算`

顺序与要求完全一致（物理/机制 1–3 → 决策 4 → 学习 5 → 计算预算 6）。六节下的子节 3.1.1–3.6.3 均存在且编号连续。

**边界/溯源编号在正文的出现**：

- G01–G13：13/13 全部出现在正文（`G01:True ... G13:True`）。
- L01–L16：16/16 全部出现在正文（`L01:True ... L16:True`）。

**T6a/T6b 定义性文字落位**（正文段落检索）：

- 段落 143（3.4.1）：明确写出 “稳健反转只在 z ≤ 1/√2 时才有可能 …（z* = 0.7071067811865475）。因此 frobustinv ≡ 0 是一个定义性结果 … 而不是关于本体系的经验发现”，并给出 T6b “maxndiscordantboth = 0 … 从不认证任何分歧”。
- 段落 267–268（补充材料 S2.3）：T6a 完整表述，含阈值 0.7071067811865475 与冻结 z=1.0/1.96 均大于该上界。
- 段落 1035：`frobustinv = 0 是定义性结果（定理 T6a/T6b），不是经验发现`。
- 计数：`T6a` 出现 4 次、`T6b` 出现 5 次、数值 `0.7071067811865475` 出现 2 次。

**渲染说明（非内容缺陷）**：论文对 `f_robust_inv` 以“下标”形式渲染，python-docx 取回的纯文本是 `frobustinv`（去掉下划线），因此字面量 `f_robust_inv` 的计数为 0；语义内容完整存在。同理 `1/sqrt(2)` 以数学符号 `1/√2` 呈现。

## 3. Gate 1 复核

**独立复算（不取用任何已写好的结论）**：直接读原始表 `data/anchors/within_series_ordering.csv`（14 行）与模型表 `outputs/week4/p1_core_set_derived.csv` 的 `p1_ox_ev` 列，重新配对计算 Kendall tau_b：

- 系列 `Ue1994_Okoshi2015`，oxidation_potential，共 14 行；7 个物种有模型值（EMC 7.0、PC 6.9、MA 6.7、SL 6.6、EC 6.5、DOL 5.5、DMSO 4.8，单位 V vs Li/Li+）；7 个物种缺模型值被跳过（GN、BC、NE、MPN、MAN、NMO、DMI）。
- 可用对 n_pairs = C(7,2) = **21**；tied_experiment = 0、tied_model = 0；**concordant = 15，discordant = 6**。
- tau_b = (15−6)/√((15+6)·(15+6)) = 9/21 = **0.42857142857142855**。

该独立复算值与冻结的 `outputs/week25/series_rel_ordering_check.json` 的 `tau_b`（0.42857142857142855）、`concordant`（15）、`discordant`（6）、`n_pairs`（21）**逐位一致（差 = 0）**，并与 `outputs/week34/wp7_external_reference.json` 的 `recompute.diffs` 全 0 记录相符。

**冻结判定（`outputs/gate1/gate1_dual_track.json`）**：

- 判据：`min_pairs = 18`、`min_tau_b = 0.9`（冻结，未重调）。
- Track A（决策稳定性）status = `computationally_established`。
- Track B（外部/实验效度）status = `NOT CLOSED`，closability = `NOT CLOSABLE`。
- ordering 组件：`kendall_tau_b = 0.42857142857142855`、`n_pairs = 21`、`concordant = 15`、`discordant = 6`。

**结论**：τ_b = 0.4286 **< 0.90** 成立（n_pairs = 21 ≥ 18 满足“最小对数”条件，但 τ_b = 0.4286 < 0.90 未达阈值，故排序一致性判据不通过，返回 `ordering_disagrees`。）因此 Gate 1 维持 **NOT CLOSED / NOT CLOSABLE**，与论文与 Week 34 记录一致。

（附：closure 8 条预注册关闭条件中满足 5 条、未满足 3 条，决定性未满足项为 `min_tau_b`；31 行 est anchor 一行未删、零新增电子结构计算、零阈值改动 —— 与 `gate1_dual_track.json` 及 `wp7_external_reference.json` 的 checks 相符。）

## 4. 口径差异确认

### 4.1 WP5：论文配对口径 7/8 vs 冻结逐格口径 6/8

**冻结逐格口径（源 `outputs/week32/delta_vs_direct.csv`，24 行，其中 LOFO 8 格）** 独立重算：LOFO 下 `shift_better_tau == true` 的格数 = **6/8**；两个 False 恰好为 **C|X0|reduction**（τ_direct 0.4222 → τ_shift 0.0222）与 **C|X0+X1|reduction**（τ_direct 0.2889 → τ_shift 0.2）。
与 `wp5_delta_learning.json` 的 `delta_learning_direction_reported` 判词“部分成立：6/8 个 (任务,特征集,轴) 在 LOFO 下 Delta-learning 的 tau_b 更高”一致。

**论文配对口径** 独立核对 docx 正文：

- 段落 157（3.5.1 节）：“8 个分组中有 **7 个**的配对 Δτb 为正，其中 3 个分组的区间不含 0”；并给出方法台阶（M·X0）两轴 Δτb = **+1.342 / +1.222**、环境台阶（E·X0+P1）氧化轴 **+0.389**；“最强的单格是方法台阶氧化轴上的常数模型，τb 由 **−0.725** 升到 **0.595**”。
- 段落 641/642（表/结论）：`SUPPORTED（7/8，3 个区间不含 0）`，`M·X0 两轴 Δτb = +1.342 / +1.222，E·X0+P1 氧化轴 +0.389；例外为 C0→C1 还原轴（−0.143）`。

**对 −0.725 / 0.595 的源头复算**（`outputs/week32/oof_metrics_reconciliation.csv`，行 `task=M, feature_set=X0, axis=oxidation, model=constant, split=lofo`）：

- shape=direct：`kendall_tau_b = −0.7252425898161922`（≈ −0.725）。
- shape=shift：`kendall_tau_b = 0.5947712418300654`（≈ 0.595）。

**无矛盾确认**：docx 中 `7/8` 与 `6/8` 各出现 1 次、两个反例键 `C|X0|reduction` 与 `C|X0+X1|reduction` 各出现 1 次，且正文明确写“位移学习的 6/8（冻结逐格口径）不是‘普遍更好’，两个反例必须列出”（段落 1050）。两套口径**并列记录、互不冲突**：7/8 是配对 bootstrap 的“方向为正”计法，6/8 是逐格点估计“τ_b 更高”计法，差异来源已在 3.5.1 写明。

### 4.2 `f_robust_inv = 0` 是定义性结论（T6a / T6b），不是经验发现

**冻结源 `outputs/week27/estimator_circularity.json` 独立核验**：

- `theorems.T6a_inversion_impossible.z_max_for_inversion = 0.7071067811865475`（= 1/√2），`frozen_z_values = [1.0, 1.96]`，`all_frozen_z_exclude_inversion = true`。
- `theorems.T6b_no_certifiable_disagreement.max_n_discordant_both = 0`，`ok = true`；逐块核验 3 个 block × 2 档 z 的 `n_discordant_both` 全为 0，`inversion_possible` 全为 false。
- `hypotheses[2]`（C 假设）frozen_verdict = `NOT OBSERVED`，`testability_under_frozen_convention = NOT TESTABLE`，理由：`f_robust_inv` 在两支臂 σ 且 z > 1/√2 下恒为 0。
- `multisource_contrast`：同一批分子仅换 σ 约定（R=2 → R=5）后，z=1.0 下最大 f_robust_inv 由 0 升到 0.0196、最大反向对数 = 1 —— 证明“零反转”是约定产物而非体系性质。

**论文正文落位**：段落 143、267–268、1035 均明确 `frobustinv ≡ 0 是定义性结果（T6a/T6b），不是经验发现`，且要求“报告它时必须同时给出 σ 约定与分母”。**记录一致、无矛盾。**

### 4.3 其他旁证（本轮顺带复核）

- Week 33 预算口径独立重算（`outputs/week33/success_budget.csv`，24 行）：`median_overstates_majority == true` 计 **14/24**（tau_b-only 高估）；`n_T_majority_combined > n_T_median_tau080` 计 **21/24**（combined 高估）——与论文/收敛包“同时报告 14/24 与 21/24”一致。
- `outputs/week35/paper_convergence.json`：`checks` 列表 10 项全部 `ok = true`、`checks_by_id` 10 项全部 `ok = true`，且不存在 `failing` 键（failing 列表为空）；`counts.n_lineage_numbers = 16`。Week 35 的 `verification.json` 亦记 `all_paper_checks_pass: ten Paper checks, failing = none`。

## 5. 结论与残留风险

### 5.1 结论

- **L01–L16 全部复算通过**：16/16 记录值与独立复算值在 `float()` 级完全一致（差 = 0）；16/16 源 sha256 与记录一致；9/9 源文件的 Week 35 镜像存在且逐字节一致。
- **论文 v7 结构性检查全部通过**：六节固定顺序、G01–G13（13/13）、L01–L16（16/16）、禁用词 0、允许措辞 designated 系列 5+2、内嵌图 24、表 19 —— 与预期（24 图 / 19 表）一致。
- **Gate 1 复核成立**：从原始表重算 τ_b = 0.42857142857142855（21 对，15 一致 / 6 不一致），与冻结值差 0；τ_b = 0.4286 < 0.90 → 维持 NOT CLOSED / NOT CLOSABLE，零删行、零迁阈值。
- **两处口径差异均被正确、无矛盾地记录**：WP5 的 7/8（配对口径）与 6/8（冻结逐格口径）并列，反例 C|X0|reduction 与 C|X0+X1|reduction 在正文与源 CSV 内一致；`f_robust_inv = 0` 明确定义为 T6a/T6b 的定义性结论（z* = 0.7071067811865475，max_n_discordant_both = 0），非经验发现。

### 5.2 残留风险 / 待留意项（均不构成 MISMATCH）

- **builder 版本差异（预期）**：当前仓库 `..\论文\build_paper_docx.py` 实测 sha256 = `89dd881155d522703bce3062fd963ddff7d0023a41af6134de4e01240634f8ee`（147,057 字节，v7 重构版），而 Week 35 镜像里冻结的副本 = `44c026c59d218cb27a5f6c6af23a9bd00bcd1545d83836b77c2efce555128aab`（128,493 字节，v6 版）。因此 `build_week35_deliverables.py --check` 报 `differs 论文/build_paper_docx.py`。这是 Week 35 之后 v7 重构的**预期后果**，Week 35 镜像与其自身记录仍自洽（其 SHA256SUMS 第 43 行 = 44c026c5… 与镜像文件一致）。**非溯源数字问题。**
- **L10 的 1 ULP 说明**：记录的 0.7071067811865475 是 JSON 字段 `z_max_for_inversion` 的原值；数学上的 1/√2 = 0.7071067811865476，二者相差 1 个 ULP。CSV 记录值与源字段逐位一致，无误。
- **docx 下标渲染**：`f_robust_inv`、`σ_ij`、`f_unresolved` 等在 docx 中为下标排版，纯文本检索取回的是无下划线形式（如 `frobustinv`），字面量计数为 0 属排版现象，内容完整。
- **审计范围**：本审计只读；未重跑任何写盘构建。论文 v7 的结构是按 v7 要求核验的（24 图/19 表/六节），而非按 Week 35 冻结的 v6 计划（22 图/17 表）核验——后者已由 v7 重构取代。
- **无 UNVERIFIABLE 项**：16 条溯源数字均定位到可读、可复算的冻结源文件。

### 5.3 证据文件索引

- 溯源记录：`outputs/week35/paper_number_lineage.csv`
- 收敛包：`outputs/week35/paper_convergence.json`、`..\成果输出（part2）\week35\verification.json`、`..\成果输出（part2）\week35\SHA256SUMS`
- Gate 1：`outputs/gate1/gate1_dual_track.json`、`outputs/week25/series_rel_ordering_check.json`、`outputs/week34/wp7_external_reference.json`
- Gate 1 原始输入：`data/anchors/within_series_ordering.csv`、`outputs/week4/p1_core_set_derived.csv`
- WP5：`outputs/week32/wp5_delta_learning.json`、`outputs/week32/delta_vs_direct.csv`、`outputs/week32/oof_metrics_reconciliation.csv`
- 定义性零：`outputs/week27/estimator_circularity.json`
- 预算：`outputs/week33/wp6_active_learning.json`、`outputs/week33/success_budget.csv`
- 论文 v7：`E:\Claude Code\电解液溶剂-HB\论文\电解液溶剂氧化还原描述符决策稳定性_结题论文_v7.docx`

---

*审计执行：Codex（Week 36 独立数字复算）。所有结论均已给出证据文件路径与具体数字；未修改任何既存文件。*