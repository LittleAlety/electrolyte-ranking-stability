# 轮次 30 终报：DMC|LiM_2plus 16 核/64 CH 试验线——未提交，科学门 HOLD 成立

> 时间：2026-10-31（UTC 07:57Z 机器实测）。Goal `goal-e3baaecc-32a1-47a8-b9ff-60f1e0e825e1` 第 30/30 轮。

## 1. 结论（先说结论）

**本授权的 16 核/≤4 h/最坏 64 CH 作业没有提交，以后也不会在本授权下提交。**
原因不是资源不足（B 已证明 64 CH 可用），而是 **Agent A 的科学门两次独立复审均为 `SCIENTIFIC_HOLD`**，
且一个更深层的、诚实的科学事实成立：

> **本包的起点（`f619c132…`）与 `DMC|LiM_2plus|primary` 的末几何字节完全相同**——
> 从已知极小的同字节重启，可以提供新数值协议下的收敛、频率与复现证据，但单独不足以证明构象覆盖。
> 覆盖是否充分，须结合有效的搜索范围与去重证据判断；起点字节不同也不能单独证明构象独立。
> 不借被取消探针 `tors_7_0_1_2`（job `3747724`）背书时，`registered_starts=[]`、
> `_search_scope_documented=False`，coverage 腿停在 `known_basin_reproduction → unresolved`。

两份复审报告首行均为 `SCIENTIFIC_HOLD`：
- `work/exp_line_20261031/SCIENCE_RECHECK_AFTER_A1_20261031.md`（Agent A，t10）
- `work/exp_line_20261031/SCIENCE_RECHECK_SUBAGENT_20261031.md`（独立 subagent，全新上下文）

二者在同一结论上收敛，且都给出了**代码路由断链**（导入器把该腿判 `member_identity_unknown`）
与**科学依据不足**两条独立理由。

## 2. 关键更正（对我自己早先说法的纠正，落盘）

A 的复审指出我早先一句表述不成立：**"没有借 tors_7 背书"**。
实情是 `_probe_starts` 是对本态**所有候选行**筛选，`candidates.csv:119` 仍登记着
`tors_7_0_1_2`，因此 `registered_starts` 至今仍是 `['tors_7_0_1_2']`——
机器今天仍在借那枚被取消探针的 seed。这恰恰印证了用户红线：**不能拿被取消作业当凭证**。
摘掉它之后 coverage 腿立即落回 `unresolved`，这正是"不借背书则证据不足"的机器证明。

## 3. 状态快照（全部机器实测）

| 项 | 值 |
|---|---|
| 我的 64 CH 包 `work/hpc_dmc_lim2plus_vtscf16_v1/` | `gate=HOLD`、`submitted=false`、**无 journal、无锁**、`sha256sum -c` 14/14 OK |
| 本授权提交次数 | **0** |
| 正式标签 | **45 accepted / 3 limited，分母 48**（limited 三态：`EC\|LiM_2plus`、`DMC\|M_plus`、`DMC\|LiM_2plus`，原因均 `rescue_budget_exhausted`）|
| 候选表 | 未改（123 行） |
| `scripts/` 生产代码 | 0 改动 |
| 队列 | 已空：另一条战役（`ec_dmc_campaign_20261031`）的 3 个作业均已 COMPLETED（3928499_0 / 3928500_0 / 3928501_0，sacct 见 `work/ec_dmc_campaign_20261031/SACCT_SETTLEMENT_20261101.txt`），实耗 10.6611 CH，验收文档见 `work/ec_dmc_campaign_20261031/CAMPAIGN_ACCEPTANCE_20261031.md` |
| 16 核 profile | 未注册（t4 未执行，因 A HOLD） |
| 池 | 600 池保守口径剩余 389.9416667 CH；本线 64 CH **未动用** |

## 4. 本线留下的资产（可复用）

- A-1 包搬迁 + manifest `members` 零计算登记（已落地，14/14 OK）
- t4 的 16 核 profile 补丁规格 `docs/handoffs/exp_line_20261031/T4_PATCH_READY_20261031.md`（未应用）
- C 提交门预备规格 `docs/handoffs/exp_line_20261031/C_GATE_SPEC_20261031.md`（未启动）
- 完整交接文档集 `docs/handoffs/exp_line_20261031/`（含 `STATUS_SNAPSHOT_20261031.md`）
- rev5 接收器 + 真实入口测试 9/9

## 5. 若用户未来想重启这条线，唯一诚实的路径

1. **换起点**：必须是一个与 primary 极小**字节不同**的真实起点（否则永远是同字节复现）。
2. **补搜索范围证据**：一条真实的新构象搜索计算，或用户明确接受某条已有证据——
   不能再用被取消的 `tors_7_0_1_2`。
3. 只有 A 复审给出非 HOLD，才依次走 t4（16 核 profile）→ C 门禁 → 提交一次。

## 6. 红线遵守确认

- 未宣称 46/48 或严格 48/48；正式记录始终 45/3/48。
- 未 git reset、未删用户文件、未覆盖他人会话（另一战役 `ec_dmc_campaign_20261031` 的文件全部保留）。
- 未动 `outputs/` 正式表（sha `3f2c692d…`，A 与 subagent 均机检验证未变）。
- 本授权到此结束，未自动提交下一条。
