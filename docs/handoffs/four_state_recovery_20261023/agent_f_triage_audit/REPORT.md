# Agent F / t2 报告：P4 判定器原型与规格主张的复核（**Lead 接手**）

## 0. 交付状态（如实记录）
- 承担本任务的 `triage-auditor`（会话 `session-7a469da9-…`）**零产物**：回合结束（状态 `inactive` / `idle-ready`）时
  `agent_f_triage_audit/` 下**一个文件都没有**，也无收尾消息。这是本会话**第四次**「从零造产物」类委派失败
  （前三次：A 缺报告、D 零产物、route-auditor 零产物）——本次简报已刻意改成「**只写 REPORT.md、禁止写任何脚本**」，
  仍未产出。按纪律**Lead 收回自做**。
- 因此本报告的复核分两类，并**分别标注证据强度**：
  **① 第三方独立证据**（并行会话的 `audit_g5_route_coverage_20261026/`，其方法与我的不同）；
  **② Lead 自证**（我自己的复算，坦白说这不是独立第三方）。
- **任务板状态**：t2 的验收（「REPORT.md 存在且逐条给出实测」）由本文件满足；`t2` 由 Lead 以接手方式完成。

## 1. 逐条复核

| # | 主张 | 复算命令/出处 | 实测值 | 判定 | 证据强度 |
|---|---|---|---|---|---|
| 1 | 真实 xtb `--opt` 目录里，stdout 有 `\| TOTAL ENERGY … Eh \|` 与 `*** GEOMETRY OPTIMIZATION CONVERGED AFTER N ITERATIONS ***`、结尾 `normal termination of xtb` | 读 `work/pilot12/C01/xtb_LiM_2plus/xtb.log`（737 行）：`grep -n "TOTAL ENERGY"` → 第 715 行；`grep -niE "CONVERGED"` → 第 441 行；`tail` → `normal termination of xtb` | 三项均命中，各 1 处 | **成立** | Lead 自证 |
| 2 | `xtbopt.xyz` 第 2 行是 ` energy: <E> gnorm: <g> xtb: <ver>`；`.xtboptok` 存在且 0 字节 | `head -2 work/pilot12/C01/xtb_LiM_2plus/xtbopt.xyz`；`ls -la` 该目录 | ` energy: -20.925657908029 gnorm: 0.000240594364 xtb: 6.7.1pre (5071a88)`；`.xtboptok` 0 B | **成立** | Lead 自证 |
| 3 | `sampling_conformer_set.csv` 只有 M/M_plus（无 LiM_2plus），其参考=该态池最小值 | 该表 44 行、按 (name,state) 统计出的极小值只覆盖 M/M_plus 24 个态 | 44 行、无 LiM_2plus 行 | **成立** | Lead 自证 |
| 3b | LiM_2plus 的参考=**固定父级**（反推 `E_ref` 行内恒定） | 对 `li_motif_screen.csv` 的每个 LiM_2plus 态反推 `E_ref = E − energy_rel_kj/2625.499638` | 11 个态离散仅 **0.0004–0.0009 kJ**（＝舍入） | **成立** | Lead 自证；与 §2 第三方复核一致 |
| 4 | `DOL\|LiM_2plus` 的 `ref − E_min` 是**正**（父级在最优候选之上） | 对 DOL 的 6 行取 `ref` 与 `E_min` | `ref − E_min = +0.000550992 Eh = **+1.4466 kJ**`；该行 `energy_rel_kj = −1.447` | **成立**（我曾写反，已更正） | Lead 自证 |
| 5 | 原型：`--selftest` 通过、对真实包空跑全为 `not_run_yet`、`--json`/`--check` 字节稳定、对包只读 | `.venv/Scripts/python.exe work/_p4_screen_triage.py --selftest`；`--package work/hpc_four_state_p4_xtb_screening_v1 [--json … --check]`；跑前跑后 `work/_p4_audit.py audit` | **19/19**；**8 元素全部 `not_run_yet`**；`--check` 连跑两次 **CHECK OK**；审计两次均 **293/293** | **成立** | Lead 自证 |
| 6 | G5 的 route 计数（8/2/2/2 + 三个 0） | 见 §2 | 逐项一致 | **成立** | **第三方独立复核** ✅ |

## 2. 第三方独立证据（并行会话，方法不同）
`docs/handoffs/four_state_recovery_20261023/audit_g5_route_coverage_20261026/`：
- **`STAGE2_counts.md` §2.3**：逐行复现 route 计数 **8 / 2 / 2 / 2** 与三个 **0**，「**fully re-verified**」；
  并给出 route×verdict 交叉表（14 行全部与 `build_coverage_reviews.py:357-375` 的映射一致，**无一行落入 `else`**）。
- **`STAGE2_counts.md` §2.4**：指出我表里「`tests/` 引用文件数 = 0」是**加守卫之前**的测量——守卫本身点名全部 7 个 route，
  故准确说法是「**零行为测试 + 零数据行**」。我已据此更正 `ACCEPTANCE_CHAIN_AUDIT_20261024.md` 的 G5 段。
- **`STAGE3_fallback_direction.md`**：用**真实代码**（import 真模块 + `exec` 真映射块）确认错拼**一次造成两件事**
  （verdict `unresolved→pending`；`kept_evidence` 被 :388 清空），并指出 **`pending` 自身错拼行为不可见**；
  方向**分层**：模块内部看似 fail-open，**下游 fail-closed**（wiring :167/:179）。
  ⇒ 我据此把残余风险精确到「**仅 ①+②+③ 协同改名**」。

## 3. 未能覆盖
- 三条零数据 route（`known_basin_reproduction` / `pending` / `dedup_evidence_required`）**仍无行为测试**——
  不是我的守卫能替代的：需要真实筛选结果才能驱动那些分支。**这是已知残余，不是本轮遗漏。**
- 判定器的「接 `coverage_route` 的 novelty 输入」与「提升进 `scripts/wp_production/` 的四处登记」未做（需要真实结果与目录纪律）。

**总结行：6 项检查，6 项成立，0 项不符**（其中第 6 项为第三方独立复核；其余 5 项为 Lead 自证，已在表中逐条标注证据强度）。