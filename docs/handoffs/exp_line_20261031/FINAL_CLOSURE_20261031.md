# 实验线收口报告：DMC|LiM_2plus 一次性 16 核试验（2026-10-31）

> 结论：**本轮未提交任何作业**。目标的可执行分支已走到派单规定的终点——
> Agent A 发 `SCIENTIFIC_HOLD` ⇒ 依派单「Lead 仅在 A 未发 SCIENTIFIC_HOLD 时实施」，
> Lead 的五项生产改动与提交**一律停止**。以下为全部既得证据与唯一待裁决项。

## 1. 三道门的最终状态

| 门 | 结论 | 产物 | 状态 |
|---|---|---|---|
| **A 科学可验收性**（t1） | **`SCIENTIFIC_HOLD`**——"不能形成正式证据（当前冻结形态）"；性质是**程序性登记/命名缺口**，非科学身份/几何/取证错误 | `work/exp_line_20261031/SCIENCE_ACCEPTABILITY_AUDIT_20261031.md`（265 行） | 已交付、**Lead 已审议批准** |
| **B 费用与重复作业**（t2） | **通过**：78 主作业全窗口 **23.0583333 CH**；41 份 journal 的 job_id 全唯一、**在飞 0**；最保守口径池余 **389.9416667**、预留 64 后 **325.9416667** ⇒ **64 CH 可用** | `work/exp_line_20261031/COST_AND_DUPLICATE_AUDIT_20261031.md` | 已交付、**已审议批准** |
| **C 提交前独立复审** | **未启动**（依赖 Lead 的五项改动，而这些改动被 A 的 HOLD 阻断） | — | 未创建（已按板面纪律取消，避免自动派活误交只读成员） |

## 2. A 的四条结论（均已由 Lead 独立复核）

1. **字节关系成立**：起点 `f619c132…` 就是 `production_ensemble_structures.csv:38` 中 `DMC|LiM_2plus|primary` 的 `final_geometry_sha256`。双证：同 sha ＋ 坐标最大差 **4.944437e-7 Å**（ORCA 6 位打印地板）；`log_sha256 45d4a8b0…` 与 cohort 日志现算一字不差；该行 `start_geometry_sha256` **为空**（`Import-Csv` 字段级解析）。
2. **真正的阻塞在验收链登记**：`members` 只剩 `tors_6/tors_8` 且均 `technical_complete_qc_failed` ⇒ `:179` ⇒ `unresolved_qc`（与磁盘 `coverage_reviews.csv:4` 逐字一致）；冻结包 seed `opt_p5li` 无候选登记、且 `import_ensemble_structures.py:154-155/158/163` 三个 glob 均不匹配 ⇒ **五项全过也进不了覆盖审**。
   附带**命名陷阱**：`DMC|LiM_2plus|tors_7_0_1_2` 被 `_rejected_probe_members`（`:143-151`，触发源 `replaces_cancelled_job=3747724`）**整键剔除**，复用即静默失效。
3. **EC 式缺行：低风险、有残余**。起点末表 `RMS grad 2.71576e-5` / `MAX grad 8.55657e-5`，对冻结 `8e-6`/`3e-5` 是 **3.39× / 2.85×** ⇒ 首轮不可能判收敛 ⇒ **`Energy change` 必打印**。残余仅来自"VeryTightSCF 下梯度 vs TightSCF 下梯度"这一未实测项；真发生则由接收器拒收为 `EVIDENCE_INCOMPLETE`（不判过、不判败、不补 0）。
4. **候选起点**：唯一合格 `ea672e7a…`（距极小 0.6874 Å，轮数/超时风险最高）；`0458134d…` 排除。

**A 纠正 Lead 两处（已采纳）**：① 步长不是几何状态量，论证只能落在两项梯度；② **反直觉**——换 `0458134d…` 起点两项梯度 **0.28× 双 PASS** ⇒ 首轮即收敛风险**升高**，**禁止按"不同字节＝更安全"选起点**。

## 3. 本轮附带完成的实质工作（非提交，全部可复算）

| 项 | 结果 |
|---|---|
| rev5 生产入口预验证 | `receive_attempt` 在**真实证据**上 **PASS**（`trust.boundary=sealed_registry`），3 个篡改用例仍拒 ⇒ **B1/B2 提前闭合**（6/6） |
| rev5 测试件 | `test_rev5_real_sealed_entry.py` **9/9 绿**（按"新用例先交独立目录"纪律） |
| 账本修补（t7） | `adjacent_step_v2 = 1.5644444`、`numerical_probe = 1.4077778`，**不再抛** `terminal cost provenance missing`（本轮回归复验通过） |
| 账目更正 | 发现并更正 Lead 快照漏记 **9.7561111 CH**（全窗口应为 23.0583333） |
| 提交前自检 | 行尾/BOM/`#SBATCH` 必填项；**核数四方一致**（桥实际 16×1 = profile 16 = `%pal nprocs` 16 = 分区上限）；两条静默降级路径（缺 profile、`budget_checked`）均**不暴露** |
| 可比性判据 | 四选项提案（A/B/C/D）＋建议，待裁决 |
| HOLD 解锁规格 | A-1/A-2/A-3 全部 **0 CH**，含完整 `members` JSON 与候选表行，待裁决 |

## 4. 最终状态（逐项实测，2026-10-31 05:19Z）

| 项 | 值 |
|---|---|
| 提交 | **0**——无 `submission_journal.json`、无 `.batch_1.submission.lock` |
| 包 | `submission_gate=HOLD`、`submitted=false`、`sha256sum -c` **14/14 OK** |
| 正式记录 | **45 accepted / 3 limited，分母 48**（未宣称 46/48，未宣称严格 48/48） |
| 生产面写入 | A 的 HOLD 之后 **0** |
| 队列 / 在飞 | 空 / 0 |
| 费用 | 池余 **389.9416667**，预留 64 后 **325.9416667**（64 CH 可用） |
| 团队 | A、B 两名只读成员均已 **retire**（历史保留） |

## 5. 唯一待用户裁决（三项选一）

A 明确说明：解锁**不需要重算、不需要新授权**，只需三条纯登记/命名（0 CH）：

- **A-1** 包移到 `work/hpc_dmc_lim2plus_vtscf16_v1/` ＋ manifest 加 `members`（免改代码通道）
- **A-2** 候选表加行（`member_role=recovery_v1_start`、**seed 用新键**、入账写 **`computed`** 而非 `ready`）
- **A-3** R7 证据强度口径（建议"现状"＋在报告中显式声明"本腿不新增搜索范围信息、来源是被取消并替换的探针 job 3747724、价值是严格协议下对已登记单一极小的独立复现"）

请选：**(a)** 放行 A-1/A-2 并重跑 A 门；**(b)** 只放行 A-1/A-2、R7 沿用现状；**(c)** 停在此处、该态继续留 `limited`。

**未获裁决前，本实验线不再动任何生产面、不提交任何作业。**