# EC 首轮收敛「证据接口缺口」审查与补证预注册

> **⚠ 2026-10-30 裁定后更正（本文件为初稿，结论已被收窄）**
>
> 用户裁定：**暂不采纳方案 A，不启动方案 B**；先做零计算的历史影响审计。
> 本文件中三处表述已被推翻，请以更正后的口径为准：
> 1. **方案 A 不能替代能量判据**——「位移在阈值内」只证明步长达标，**不能证明 |ΔE|≤2e-7 Eh**；把它用于豁免缺失的能量项，实质是把「五项全过」改为「四项＋例外」，不是文案修正。
> 2. **两个位移口径不可互换**——笛卡尔位移与 ORCA 优化器报告的步长可能采用不同坐标表示与 RMS 定义；0.896×/0.894× 只能作**辅助量级参考**，不构成等价性证明。
> 3. **方案 B 表述错误**——「不同几何的两点单点能差只反映数值噪声」是**错的**：它还包含真实几何能量变化与数值误差。只有**同几何、同设定**的受控重复才有助估重复性，且不能凭一次比较确立噪声底。
>
> 另：手册结论应写作「**所查 ORCA 6.0 文档未找到最少轮数控制**」，**不得断言 ORCA 不存在**；实际运行版本为 **6.1.1**，尚需核对对应版本资料。
>
> 历史影响审计见：`EC_FIRST_POINT_EXCEPTION_IMPACT_AUDIT_20261030.md`

---


**日期**：2026-10-30
**状态**：零计算审查稿（不含任何新作业授权）
**触发**：EC 强制严格收敛实验 3910076 判为 `evidence_incomplete_energy_change_not_reported`
**适用对象**：`work/hpc_ec_strict_convergence_v1/`，起点 p7 末几何 `17830a4c…`

---

## 1. 事实（全部为实测，无推断）

### 1.1 两次真实提交

| 作业 | 状态 | 耗时 | 实耗 | 协议 |
|---|---|---|---:|---|
| 3895037 | COMPLETED 0:0 | 00:03:22 | 0.2244444 CH | ❌ 缺 `VeryTightOpt`，用默认阈值 |
| 3910076 | COMPLETED 0:0 | 00:03:02 | 0.2022222 CH | ✅ `VeryTightOpt` 生效 |

**精确费用合计**：`0.4266666667 CH`（展示为 **0.4267**）。
> 不得写作 0.4266——那是两次各自截断后再相加的结果，不是精确值。

### 1.2 3910076 的回显证据（逐项实测）

| 项 | 回显值 | 冻结值 | 判定 |
|---|---|---|---|
| `Strict Convergence` | True | 需 True | ✅ |
| RMS gradient | 8.0e-6 | 8e-6 | ✅ 一致 |
| MAX gradient | 3.0e-5 | 3e-5 | ✅ 一致 |
| RMS step | 1.0e-4 | 1e-4 | ✅ 一致 |
| MAX step | 2.0e-4 | 2e-4 | ✅ 一致 |
| **Energy change** | **未打印** | 2e-7 | ⚠️ 无法判定 |

四项几何判据全部 `YES`，日志出现 `HURRAY`（仅 1 个收敛表）。

### 1.3 几何位移实测（关键）

```
max |Δr| = 9.487461e-05 A   ( 0.896 x TolMaxD )
RMS |Δr| = 4.728137e-05 A   ( 0.894 x TolRMSD )
```

换算基准：1 Bohr = 0.529177210903 Å；`TolMaxD = 2e-4 Bohr = 1.058354e-4 Å`、`TolRMSD = 1e-4 Bohr = 5.291772e-5 Å`。

**结论**：几何**确实移动了**，但**两项位移判据都在冻结容差之内**。

### 1.4 两次独立 FSPE 的能量差（诊断数据，非收敛判定）

`−349.776340719766` → `−349.776340178856` ⇒ `ΔE = +5.40910e-7 Eh = 2.70 × TolE`。

> 这是**两次独立运行**的末能量之差，**不是**同一次优化内的相邻步 ΔE。只可作诊断线索，**不得补填收敛表**。

---

## 2. 审查结论

### 2.1 现有项目是否已有首点收敛例外？——有，但前提被本次实测部分推翻

`scripts/wp_production/import_hpc_opt_numfreq.py:109-118`（`final_geometry_convergence` 文档串）：

> "The `Energy change` row (3 more) only appears once the optimizer has a previous energy point to compare against: **a leg whose start geometry is ALREADY VeryTight-clean converges at the first check without ever moving an atom**, so ORCA prints no Delta-E row at all (v1.3 rescue runs do exactly this)."

对应代码 `:153-162` 记录 `energy_change_absent = "first_point_convergence_geometry_never_moved"`，
并由 `import_ensemble_structures.py:938-939` 转成 `convergence_note = "first_point_convergence_geometry_never_moved"`。

**问题**：该例外的**字面前提是「without ever moving an atom」（原子从未移动）**。
本次实测位移 `max 9.487e-5 Å / rms 4.728e-5 Å`——**非零**。

因此：

| 读法 | 本次是否适用 |
|---|---|
| 字面读法「位移严格为 0」 | ❌ 不适用（实测非零） |
| 操作性读法「位移在 TolMaxD/TolRMSD 之内」 | ✅ 适用（0.896× / 0.894×） |

**⇒ 这是一个口径分歧，必须由用户裁定，不得自行套用历史豁免。**

### 2.2 ORCA 是否支持明确、可验证的「最少优化轮数」控制？——不支持

已核对 **ORCA 6.0** 官方手册 `%geom` 关键词表（[7.26 Geometry Optimization](https://www.faccts.de/docs/orca/6.0/manual/contents/detailed/geomopt.html)）。**⚠ 口径收窄（2026-10-30 用户指出）**：应写「**所查 ORCA 6.0 文档未找到最少轮数控制**」，**不得断言 ORCA 不存在**；实际运行版本为 **6.1.1**，尚需核对对应版本资料。就所查 6.0 文档而言：

- 迭代控制**只有** `MaxIter`（最大值，默认 3N 且至少 50）；
- **不存在** `MinIter` / `MinCycles` / 任何「最少轮数」关键词；
- 收敛阈值关键词为 `TolE / TolRMSG / TolMaxG / TolRMSD / TolMaxD` 与预设 `Convergence normal|loose|tight`；
- 手册明写：「**the calculation is only converged if all criteria are fullfilled**」。

**⇒ 就所查 6.0 文档而言，未见可通过已文档化关键词强制优化器多跑一轮的方法。** 想制造第二轮只能人为扰动起点，那会改变物理问题（起点不再是 p7 末几何），不可接受。

### 2.3 本次缺口的准确表述

**可以确认**：本次首轮收敛出现**证据接口缺口**——ORCA 在首轮判据全过时不再打印 `Energy change`，导致项目五阈值中的能量项**无值可判**。

**不能推广**：不得据此断言「该方法必然无法满足五项验收」。缺的是一项**证据**，不是一项**判据失败**。

---

## 3. 补证方案（设计稿，未执行）

### 3.1 方案 A：口径澄清（零计算）——**已裁定不采纳**

> **裁定（2026-10-30）**：方案 A **不能直接替代能量判据**。「位移在阈值内」只能证明**步长达标**，**不能证明 |ΔE| ≤ 2e-7 Eh**。把它用于豁免缺失的能量项，实质是把「五项全过」改为「**四项＋例外**」，不是单纯修正文案。**本次 EC 继续保持 `evidence_incomplete_energy_change_not_reported`，不增加 accepted。**

原文设想（保留备查，不执行）——把既有例外从「几何从未移动」改为**可验证的容差判据**：

> 首轮收敛例外成立当且仅当：
> ① 收敛表四项几何判据全部 `YES`，且回显容差逐项等于冻结值；
> ② 末几何相对输入的位移满足 `max|Δr| ≤ TolMaxD` 且 `RMS|Δr| ≤ TolRMSD`（用冻结值换算到 Å）；
> ③ 日志出现 `HURRAY` 且只有一个收敛表；
> ④ 记录 `energy_change_absent` 为**证据缺口**，不填值、不声称通过能量判据。

**代价**：零计算。**风险**：等于承认「能量判据在首轮收敛情形下不可得」——须用户明确裁定是否接受。

### 3.2 方案 B：两点能量协议（需预注册 + 可能需新计算）

用**同一末几何**做一次严格单点（`TightSCF`，无 `Opt`、无 `AnFreq`），与 Opt 阶段末能量比较。

**必须先冻结以下四项**（否则不可追溯）：

1. **每个能量对应的几何与阶段**
   - `E_opt`：Opt 阶段末能量，来自 `job_opt.log` 的 `FINAL SINGLE POINT ENERGY`，几何 = `job_opt.xyz`
   - `E_sp`：单点能量，来自 `job_sp.log`，输入几何 = **同一个** `job_opt.xyz`（sha256 必须相同）
2. **数值设定完全相同**：泛函/基组/色散/溶剂/`%scf` 全部一致，且逐项在日志回显中核对
3. **电子身份检查**：占据数、自旋期望值、SCF 收敛圈数、`NEL` 必须一致；不一致即拒收
4. **能否代表「优化步 ΔE」**——**明确回答：不能**。同一几何两次单点的差值只反映数值噪声（SCF/网格/积分），**不等于**优化器相邻两步的能量变化。故方案 B 只能给出**噪声量级**，不能判定 TolE。

**⚠ 更正（2026-10-30 用户指出）**：上文「只反映数值噪声」是**错误表述**。不同几何的两点单点能差，**还包含真实几何能量变化与数值误差**，不是纯噪声。只有**同几何、同设定**的受控重复才有助于估计重复性；且**不能仅凭一次比较确立噪声底**。

**⇒ 裁定：方案 B 暂不批准**。先明确它究竟能改变哪项决策，再谈是否值得追加计算。

### 3.3 方案 C：拒绝填值（保守兜底）

维持 `evidence_incomplete`，EC 保持 `limited`，不推进 48/48。这是当前已执行的状态。

---

## 4. 拒收规则（三方案共用）

以下任一情形**必须拒收**，不得降级为警告：

| 情形 | 处理 |
|---|---|
| 收敛表缺任一**几何**判据（RMS/MAX gradient、RMS/MAX step） | 证据不完整，拒收 |
| 回显容差 ≠ 冻结值 | 协议不匹配，拒收（非科学结论） |
| `Strict Convergence` 缺失或为 False | 拒收 |
| 位移超出 `TolMaxD` 或 `TolRMSD` | 不适用首轮收敛例外，拒收 |
| 出现多个收敛表（说明不止一轮） | 不属首轮收敛，走常规五项判定 |
| 单点复算的几何 sha256 ≠ Opt 末几何 | 拒收 |
| 单点与 Opt 的电子身份不一致（占据/自旋/NEL/SCF 圈数） | 拒收 |
| 任何缺测项 | **不填 0**，标记缺口 |
| 超时或非正常终止 | 拒收，如实记录耗时 |

---

## 5. 负测清单（预注册必须先写、先跑，再谈执行）

| # | 负测 | 期望 |
|---|---|---|
| N1 | 输入缺 `VeryTightOpt` | `check_input.py` 拒（rc=2） |
| N2 | 回显容差为默认值（5e-6 等） | `qc_opt.py` 报 PROTOCOL_MISMATCH（rc=2） |
| N3 | 收敛表缺 `Energy change` 且位移超 TolMaxD | 拒收（不适用例外） |
| N4 | 收敛表缺 `Energy change` 且位移在容差内 | 按方案 A 判「证据缺口」，仍不填值 |
| N5 | 单点几何 sha256 ≠ Opt 末几何 | 拒收 |
| N6 | 单点电子身份不一致 | 拒收 |
| N7 | 出现两个收敛表 | 走常规五项，不走首轮例外 |
| N8 | 任何缺测被填 0 | 断言失败（禁止） |

---

## 6. 需要用户裁定的事项

1. **方案 A 是否采纳**：把首点收敛例外从「原子从未移动」改为「位移在 TolMaxD/TolRMSD 之内」？
2. 若采纳，**是否溯及既往**（只影响本次 3910076，还是重判历史首点收敛腿）？溯及必须做无翻转证明。
3. **方案 B 是否值得执行**：它只能估噪声底，不能判 TolE。是否仍要做？
4. 若做方案 B，**新计算另行批准**——剩余预算（15.5733 CH）**不等于**新增尝试授权。

---

## 7. 本轮已执行动作（零计算）

- 费用口径修正：`0.2244444 + 0.2022222 = 0.4266667 CH`（展示 0.4267），剩余 `15.5733333 CH`
- 账本状态：两次尝试分别记 `protocol_mismatch` 与 `evidence_incomplete`，**均不可用于科学验收**
- EC 保持 `limited`，**禁止自动续算**
- **未提交任何新作业**

---

## 8. 证据路径

- 账本：`work/hpc_ec_strict_convergence_v1/attempts_ledger.json`
- 提交日志：`work/hpc_ec_strict_convergence_v1/submission_journal.json`、`failed_attempts.json`
- 产物快照：`work/hpc_ec_strict_convergence_v1/tasks/EC/LiM_2plus__strict_convergence_p7/snapshots/3910076_0/`
  - `job_opt.log` sha256 `195cf4077ceb8ab62448a0464d9ecb554eebeaaf7760c0db848a4987603afbe1`
  - `job_opt.xyz` sha256 `14987efb4211baaedbda4ffeb1ab2a60b1437c41fc42cc961b3d1586c815bf88`
- 项目既有例外代码：`scripts/wp_production/import_hpc_opt_numfreq.py:109-118,153-162`；`scripts/wp_production/import_ensemble_structures.py:938-939`
- ORCA 手册：<https://www.faccts.de/docs/orca/6.0/manual/contents/detailed/geomopt.html>
