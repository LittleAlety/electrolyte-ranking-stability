# DMC 阈值故障判读（计划 action item 6）——2026-10-25，全部从原始日志实测

> 数据源：`production_ensemble_structures.csv` 的 18 条 DMC/DOL/EC 失败腿 + 各腿 `log_path` 指向的原始 ORCA 日志
> （逐腿解析 24–49 个优化循环的五项判据表）。**不跑任何新计算**；本文只做判读。

## 0. 判读结论（三行）

1. **DMC 两态的失败全部是「close-enough 平台」，不是真发散**：ORCA 在梯度项全面达标后宣布
   「gradient convergence is overachieved with reasonable convergence on the displacements」并**提前宣布收敛**——
   但**位移项**（MAX step 0.000324 / RMS step 0.000093→0.000136 区间震荡）**永远差一步**过 `TolMaxD=2e-4`。
   这是 ORCA 的 **「close-enough」提前收敛机制**踩到了本项目「五阈值全过」的**严格**定义。
2. **`max_cycles_exhausted`（49 循环撞 ORCA 缺省 `MaxIter=50`）是同一种病的晚期**：循环 45–48 的五项判据
   **整体震荡**（E/RMSg/MAXg 间歇过、位移项持续 NO），没有任何一项在系统性下降——**再给循环也不会收敛**。
3. **`strict_reopt_required`（`orca_close_enough_but_frozen_tolE_missed`）是第三形态**：SCF 间能量变化
   达到 ORCA 自己的 `TolE 1e-8`，但**几何优化轮间** ΔE > 冻结的 `TolE 2e-7`（例：4.344e-07 > 2e-07，差 2.2 倍）。

**共性根因**：DMC 体系（DMC|M_plus 的甲基转子、DMC|LiM_2plus 的 Li 配位簇）在 VeryTightOpt 区间存在
**浅赝平坦谷**——梯度已经小到 2e-6（比阈值好 4 倍），但位移/能量在阈值边缘震荡。**这不是「再试一次」
能解决的**：三种 failure class 都是同一个物理事实的三种表现。

## 1. 逐腿证据（五项终值实测）

### 1.1 `DMC|M_plus|tors_6/7/8`（`verytight_convergence`，att=0，3747714_4/5）

| 循环 | Energy change (TolE 2e-7) | RMS grad (8e-6) | MAX grad (3e-5) | RMS step (1e-4) | MAX step (2e-4) |
|---|---|---|---|---|---|
| 21 | 1.0e-7 ✅ | 3.8e-6 ✅ | 1.24e-5 ✅ | 1.37e-4 ❌ | 3.62e-4 ❌ |
| 22 | −1.1e-7 ✅ | 2.9e-6 ✅ | 6.9e-6 ✅ | 4.35e-4 ❌ | 1.22e-3 ❌ |
| **23（末）** | **−1.14e-7 ✅** | **2.18e-6 ✅** | **6.0e-6 ✅** | **9.29e-5 ✅** | **3.24e-4 ❌** |

末循环 **4/5 过**，唯一不过的 MAX step＝3.24e-4（阈 2e-4，**差 1.6 倍**）；ORCA 判「close-enough」宣布收敛
（日志 17958-17960 原文：`The gradient convergence is overachieved with reasonable convergence on the
displacements / Convergence will therefore be signaled now`）。而**本项目的验收器正确地拒了它**。
**注意 RMS step 在阈值边缘横跳**（cyc21 1.37e-4 ❌ → cyc23 9.29e-5 ✅）——**平台特征，非单调收敛**。

### 1.2 `DMC|LiM_2plus|tors_8/6`（`max_cycles_exhausted`，49 循环，3747714_6/7）

| 循环 | E | RMSg | MAXg | RMSstep | MAXstep |
|---|---|---|---|---|---|
| 45 | 1.57e-6 ❌ | 7.2e-6 ✅ | 1.68e-5 ✅ | 7.1e-4 ❌ | 2.16e-3 ❌ |
| 47 | 4.2e-7 ❌ | 3.2e-6 ✅ | 8.8e-6 ✅ | 1.69e-3 ❌ | 7.4e-3 ❌ |
| 48（末） | −3.1e-7 ❌ | 1.07e-5 ❌ | 3.12e-5 ❌ | 1.01e-3 ❌ | 4.47e-3 ❌ |

**49 循环全震荡，末循环反而全面恶化**（RMSg/MAXg 双双失守）——**增加循环数的「有界续算」救不了它**
（计划原文「max-cycles 才有界续算」的前提不成立：这不是差一点，是平台+漂移）。

### 1.3 `DMC|LiM_2plus|tors_7` att=12（`verytight_convergence`，3749453_0）

| 循环 | E | RMSg | MAXg | RMSstep | MAXstep |
|---|---|---|---|---|---|
| 28 | −3.4e-7 ❌ | 4.8e-6 ✅ | 1.53e-5 ✅ | 6.28e-5 ✅ | 2.92e-4 ❌ |
| 29（末） | −4.3e-7 ❌ | 2.6e-6 ✅ | 8.0e-6 ✅ | 1.51e-4 ❌ | 5.77e-4 ❌ |

convergence_note 实测：`energy_change_Eh=4.344e-07 > 2e-07`——**只差 TolE 一项，差 2.2 倍**；
位移项同样边缘震荡（RMSstep cyc28 ✅ → cyc29 ❌）。

### 1.4 `strict_reopt_required` 家族（`28`/`c06`/`tors_7`att=5/`tors_8`att=2）

convergence_note 一致：`orca_close_enough_but_frozen_tolE_missed_reopt_required`——**重优化后
SCF 层面达标、几何轮间 ΔE 仍超冻结 TolE**。这是「从自身末几何重启」的**已有通道**（reopt1–4 + reopt_v2 已跑过），
其结果证明：**从平台腿重启，得到的仍是平台**（att=1/2/5/12 全部同型失败）。

## 2. 三种 failure class 的统一判读

| failure class | 表现 | 故障假设（判读认定） | 有界续算可救？ |
|---|---|---|---|
| `verytight_convergence` | 4/5 过、MAXstep 差 1.6 倍或 TolE 差 2.2 倍 | **浅平坦谷**：梯度过达标但位移/能量在阈值边缘震荡（RMSstep ✅↔❌ 横跳） | **否**——循环 16–23 显示是平台不是尾巴 |
| `max_cycles_exhausted` | 49 循环末反而恶化 | 同一平台 + 漂移；`MaxIter=50` 只是让病拖到最后 | **否**——「加循环」前提不成立 |
| `strict_reopt_required` | 重优化后 SCF 达标、几何 ΔE 仍超 | 从平台重启仍得平台（att 1/2/5/12 同型失败已证） | **否**——已被 4 次重优化尝试证伪 |

**结论：DMC 两态的失败是「冻结数值设置下的浅赝平坦谷」，不是坐标/步长/SCF 的技术错误。**

## 3. 对「下一步唯一允许动作」的含义（按计划原文）

计划原文：「若必须改网格、SCF 或 Hessian 设定，先进行**版本化、全 cohort 可比性评估**；不得只对 DMC 两态换设置取有利结果。」

- **判读不支持「再提交同设置的起点」**：三种 failure class 都是同一物理事实，同设置重试已被 18 条失败腿证伪。
- **判读也不支持「只对 DMC 改设置」**：若 DMC 系因平台需要不同优化设定（如换 Hessian 初猜/坐标系统），
  须**版本化**（另立命名族、序号高于该成员一切历史序号）并**全 cohort 可比性评估**——这超出本轮 800 预算的
  「每态 ≤2 起点 + ≤1 救援」框架（每次评估本身就要重算全 cohort 才能谈可比性）。
- **DMC 两态的正确出口（判读认定）**：按计划的限制报告路径——**逐态失败证据、真实成本、下一轮新假设**。
  即：DMC 两态在本轮**保持 `limited`**（`rescue_budget_exhausted` 的语义与实测一致：18 条腿的尝试额度已用尽），
  严格目标如实保持未完成；**不冒充、不降阈值、不删历史**。

## 4. 与 P4 结果的一致性（交叉验证）

P4 筛选（job 3774215）从**GFN2 层**独立发现：DMC 两态的全部探针弛豫回 `C01#m1` 同一极小
（RMSD 0.0013 Å）——**与生产层「浅平坦谷」判读互洽**：GFN2 下该极小是清晰的单一盆地，
wB97X-D4 下它变成 VeryTightOpt 阈值边缘的浅平台。**两层证据都指向：DMC 不缺新起点，缺的是
能通过五阈值的优化设定**——而那恰是冻结项。

## 5. 证据出处

- 18 条失败腿的 `failure_class`/`convergence_note`：`outputs/physics_completion/ensembles/production_ensemble_structures.csv`
- 五项判据逐循环实测：本仓库内 4 份原始 ORCA 日志（`work/hpc_torsion_probe_v1/tasks/DMC/.../snapshots/3747714_{4,5,6,7}/job.log`、
  `work/hpc_torsion_probe_v1_reopt_v3/.../3749453_0/job.log`），解析脚本按「主张/循环/五项值」逐表输出（本文件 §1 的表即原始解析结果）
- `MaxIter 50` 的出处：job.log:246（`Max. no of cycles MaxIter .... 50`）；job.inp 无 `%geom MaxIter` 覆盖（只有 `%scf MaxIter 300`）
- close-enough 提前收敛的原文：3747714_4/job.log:17958-17960