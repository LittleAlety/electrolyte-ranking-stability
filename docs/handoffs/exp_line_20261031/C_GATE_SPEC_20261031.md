# Agent C 提交门预备规格（未启动，等 Lead 改动完成）

> 状态：**预备**。C 的门禁必须在 Lead 的五项改动完成后才启动（派单第 ④ 步）。
> 本文件只把 C 要核的**每一条**与其**可执行的验证方式**先写清，避免门禁临时拼凑。

## 0. 为什么现在不能启动 C

派单顺序：A 科学门 → Lead 五项（t3 rev5／t4 profile／t5 登记／t6 改包／t7 账本，t7 已完成）→ **C 的 GO/NO_GO** → 提交。
当前 A 发 HOLD ⇒ Lead 五项中的 t3/t4/t5/t6 **未执行** ⇒ C 无对象可审。
（历史上 t8 曾被自动派活误认领，已取消；本轮不重建，**等 Lead 改完再建**，遵守"Lead-only 任务不入板"的教训。）

## 1. C 必须逐项给出的判定（GO / NO_GO）

| # | 检查项 | 可执行验证 | 期望 |
|---|---|---|---|
| C1 | **A 的科学门结论被诚实继承** | 读 `SCIENCE_ACCEPTABILITY_AUDIT_20261031.md` + `SCIENCE_RECHECK_AFTER_A1_20261031.md`；核对首行判定与包的实际形态是否一致 | 不得把 HOLD 当通过；不得把"程序返回 resolved"当科学结论 |
| C2 | **B 的费用门** | 复算 `committed_core_hours()` 逐包；`600 − 已用 − 在飞 ≥ 64` | 与 `COST_AND_DUPLICATE_AUDIT_20261031.md` 一致；池余 389.9416667 |
| C3 | **rev5 真实入口** | 确认发射器 `work/_dmc_emit_staging_record.py` 调用的是 `receive_attempt`（而非 `receive`）；跑 `work/exp_line20261031/test_rev5_real_sealed_entry.py` | **9/9 绿**；记录 `trust.boundary == sealed_registry` |
| C4 | **16 核 profile 三方一致** | `declared_task_cores(pkg)==16`、`profile["cores"]==16`、`%pal nprocs 16`、`--ntasks-per-node=16` | 全等，且 `cap=64` |
| C5 | **候选登记与导入链** | `iter_packages()` 命中本包；候选表有该行且 `member_role` 合白名单；`_rejected_probe_members()` **不含**本 member_key | 全过；且**未**复用 `tors_7_0_1_2` |
| C6 | **失败即停止** | 读 `stage_driver.py`：Opt 五项不过 ⇒ 不启动 AnFreq；无自动重试 | 代码层面成立 |
| C7 | **"Opt 五项全过才 AnFreq"** | 同上 + 读 `AUTHORIZATION.json` 的 conditions | 条件与实际代码一致 |

## 2. C 必须做的**入口级负测**（六种非法请求都要被拒）

| # | 非法请求 | 期望拒绝点 |
|---|---|---|
| N1 | `submission_gate=HOLD` 时提交 | `_enforce_submission_gate`（`:470-491`） |
| N2 | 输入声明 16 核但 profile 是 4 核 | `:725-731` `refusing to silently change the resource` |
| N3 | manifest 写错电荷（如 `* xyzfile 1 2`） | 接收器 `identity` 校验（`normal_and_identity`） |
| N4 | 起点哈希与登记不符（旧起点） | `START_LABEL_MISMATCH` |
| N5 | Opt 缺 `Energy change` 行 | `dmc_staged_receiver_v5.py:835-839` `EVIDENCE_INCOMPLETE` |
| N6 | 重复提交（journal/lock 已存在） | `:686-693` |

## 3. C 的输出要求

- **首行**必须是 `GO` 或 `NO_GO`；
- **任何 Critical / Important 遗留 ⇒ NO_GO**（不得用"整体可接受"含糊过去）；
- 每条结论带**文件:行号** + 相关文件 sha256（多会话并发纪律：行号会漂移）；
- **唯一写入** = 新建 `work/exp_line20261031/PRE_SUBMIT_GATE_REVIEW_20261031.md`。

## 4. 当前可先复核的部分（C 若提前启动）

| 项 | 现在就能核 | 状态 |
|---|---|---|
| C2 费用门 | ✔ | 已证：池余 389.9416667、预留 64 后 325.9416667 |
| C3 rev5 入口 | ✔ | 已预验证 6/6 + 测试 9/9 |
| C4 profile | ✘ | **待 t4**（当前 `RESOURCE_PROCESS` 无该 profile，fail closed 实测） |
| C5 候选登记 | ✘ | **待 t5**（候选表 123 行、无本尝试） |
| C1 科学门 | ✘ | **待 A 复检** |
| C6/C7 失败即停 | ✔ | `stage_driver.py` 代码层面已成立 |

⇒ **C 现在启动会得到 NO_GO**（C1/C4/C5 未过），因此**不启动**。