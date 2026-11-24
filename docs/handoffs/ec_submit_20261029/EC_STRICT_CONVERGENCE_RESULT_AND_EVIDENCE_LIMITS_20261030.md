# EC 严格收敛实验结果与证据限制（2026-10-30）

**口径**：本条**不是**"strict 路线被否证"，也**不是**"TolE 再次超差"。正确口径是
**证据不完整**：本次运行开启了严格收敛、四项几何指标达标，但未打印 `Energy change`，
**无法证明满足项目五项验收**；门禁正确拒收，AnFreq 未启动。EC 仍 limited，科学计数仍
**45/48**。本轮未追加计算，未改任何验收标签。

## 1. 提交与终态（sacct 实测）

| 作业 | 终态 | ElapsedRaw | 实耗 CH | 性质 |
|---|---|---:|---:|---|
| 3895005 | 技术失败（payload 未上传，`sed: can't read tasks.txt`） | 00:00:00 | **0** | 技术失败，非科学结论 |
| 3895024 | FAILED 1:0 | 00:00:00 | **0** | 无任何 ORCA 输出 |
| 3895037 | COMPLETED 0:0 | 00:03:22 | **0.2244** | **协议不匹配**（见 §3） |
| 3910076 | COMPLETED 0:0 | 00:03:02 | **0.2022** | 输入已修，但**证据不完整**（见 §2） |
| 合计 | — | — | **0.4267** | 结算归包 owner |

三次真实提交的起点几何 sha 均为 `17830a4c4cdb6479ff03be07b409c44414025d98da20fdc99ebe80c7a556432d`（原 p7 末几何）。

## 2. 3910076：证据限制（核心）

输入（已修复）：`! wB97X-D4 def2-TZVPD Opt SMD(acetonitrile) VeryTightOpt TightSCF SlowConv` +
`%geom EnforceStrictConvergence TRUE` + 五项显式 `Tol*`。

| 项 | 实测 |
|---|---|
| 严格回显 | `Strict Convergence .... True`（1 次） |
| 回显阈值 vs 冻结 | RMS grad 8e-6 ✔ / MAX grad 3e-5 ✔ / RMS step 1e-4 ✔ / MAX step 2e-4 ✔ |
| 优化 cycle 数 | **全程只有 1 个 cycle** |
| 收敛表 | **只有 4 行，`Energy change` 行不存在** |
| ORCA 结论 | `HURRAY`（1 次），`ORCA TERMINATED NORMALLY`，3:20 |
| 两处能量 | `-349.776340719766`；`-349.776340178856` |
| 差 | **5.40910e-7 Eh** |

**为什么不能写成"TolE 超差"**：第二次能量出现在 HURRAY **之后**的
`FINAL ENERGY EVALUATION AT THE STATIONARY POINT` 段，而**不是**相邻优化 cycle 的收敛表
ΔE。因此 5.40910e-7 Eh 是"两次能量评估之差"，**不是已确认的相邻步 ΔE**，不能与 TolE
做比值并宣告能量判据失败。

**能说的**：本次运行四项几何指标达标、严格开关回显为 True，但 `Energy change` **未打印**，
五项口径**结构上无法判定**，门禁依 `INCOMPLETE_TABLE missing=['Energy change']` 拒收。
另注：**缺行不代表几何未动**——实测位移 9.487e-5 Å（包内 QC 备注）。

## 3. 3895037：协议不匹配（历史记录更正）

该次提交时 `VeryTightOpt` 被误删，ORCA 用**默认优化阈值**（TolE 5e-6、RMS grad 1e-4、
MAX grad 3e-4、RMS step 2e-3、MAX step 4e-3，比冻结值松 10–20 倍）运行。
**关键陷阱**：日志仍回显 `Strict Convergence .... True` —— 严格模式开关与阈值预设是
**两个独立的东西**，前者为 True 不代表后者生效。

⇒ 3895037 应登记为**协议不匹配、两阶段证据未完成**，**不是能量判据失败**。
泄漏原因与修法：`check_input.py` 增加提交前输入契约校验（必须含 `VeryTightOpt`、
禁 `AnFreq`/`NumGrad`、必须有 `EnforceStrictConvergence TRUE`、核数/电荷/多重度）；
`qc_opt.py` 增加**回显阈值 vs 冻结阈值比对**，不匹配报 `PROTOCOL_MISMATCH` 而非科学结论。

## 4. 不得做的表述

| 禁止 | 应有表述 |
|---|---|
| "strict 路线被否证" | "本次运行证据不完整，未能证明满足五项" |
| "TolE 再次超差（2.70×）" | "两次能量评估差 5.40910e-7 Eh；非相邻步 ΔE，不作判据比值" |
| "3895037 能量判据失败" | "3895037 协议不匹配（缺 VeryTightOpt）" |
| "该结构零虚频" | "零虚频来自原 p7（job 3885000）；本次 **AnFreq 未运行**，不可赋给本结构" |
| 缺测填 0 | 保留为空并标 `INCOMPLETE_TABLE` |

## 5. 结构性问题（供后续裁决）

ORCA 行为：优化器首轮即满足全部几何判据时，**直接打 HURRAY 而不输出 `Energy change` 行**
（无"上一轮能量"可比）。而项目冻结五阈值要求 `Energy change ≤ 2e-7`，该项在此情形下**根本
没有数值** ⇒ 五项口径结构上不可判定，门控只能报"证据不完整"。这是 ORCA 输出行为与项目
验收口径之间的固有冲突，**不是偶发**。若要判定此类首轮收敛，需另立办法（强制至少两轮，
或从能量序列自算 ΔE），**属方法变更，须先裁定**。

## 6. 状态与停止

- EC|LiM_2plus 仍 **limited**；科学计数 **45/48**。
- 停止自动续算；费用按终态结算（owner 执行）；历史失败与既有费用保留。
- 原 p7 结论不变：五项过 4 项、**0 虚频**、最低正频 32.30 cm⁻¹、TolE 8.38e-7（4.19×）拒收。