# DMC 起点独立性：现算汇总与更正（2026-10-29）

数据：`DMC_START_INDEPENDENCE.csv`（本目录）。方法：对每个已登记 attempt 找到其**输入** `geom.xyz`，
现算完整 SHA256、**坐标规范化 SHA256**（跳过前 2 行、保留坐标行）、原子数与原子顺序、来源路径、实际作业号；
按（slot, 坐标 SHA）分组。**未改写任何历史输入**。

## 1. 关键实测

| 项 | M_plus | LiM_2plus |
|---|---|---|
| 账本中 attempt 数 | **7** | **8** |
| 有实际作业号的 attempt | 6（primary 为历史 ready，无 log） | 7（primary 无 log） |
| 不同输入坐标数（含 primary） | **5** | **6** |
| 不同输入坐标数（不含 primary） | **4** | **5** |
| 最大相同坐标组 | `dde1eae5e08b9e62` ×3（tors_6/7/8） | `b87e3637bff03b1a` ×3（tors_6/7/8，含 1 条 pending） |

相同坐标组明细：

- **M_plus**：`tors_6_0_1_2`、`tors_7_0_1_2`、`tors_8_0_1_2` 三份输入坐标**逐位相同**（`dde1eae5…`），
  文件完整 SHA 不同仅因第 2 行标签不同（`7dad1c50…`/`10eac800…`/`6ef29785…`）。
  与源几何 `ce1df116…` 不同 ⇒ 旋转确实施加过一次，但三个 dihedral 共用同一轴 `(0,1)` + 同一移动片段，结果相同。
- **LiM_2plus**：`tors_6`、`tors_7`（v1，pending）、`tors_8` 三份输入坐标相同（`b87e3637…`）；
  `tors_7` 另有 fragmentfix（`913df88c…`）与 reopt_v3（`a4c49688…`）两个**不同**输入；与源 `5b545313…` 不同。
- `28` 的两次（r1_000-017 与 reopt4）输入不同（`80aeb6e5…` vs `b85bf16d…`），属「从平台重启」；
  `c06` 的两次（r1_036-053 与 continuation4）输入不同（`e5773ec9…` vs `9e6cd3bf…`）。

## 2. 根因（已核实，不说成"某代码 bug"以外的推断）

- **历史包** `work/hpc_torsion_probe_v1/manifest.json` 的 mtime 为 **2026-10-22 15:05**；
  而「每个新起点必须与既有起点做等价/刚体检查」的 `prior_starts` 守卫是在
  **`30ace3a`（2026-10-23 22:40）**才接入 `_build_state`（`git log -S 'prior_starts=selected'` 唯一命中）。
  ⇒ 建包时**该守卫尚不存在**，三条同轴同片段的 dihedral 被当作三个候选写入。
- **当前代码已能拦住**（实测，用历史包的真实 `geom.xyz`）：
  `equivalent_start(syms, tors_6, tors_7, adj) → True`；
  `validate_candidate_start(..., prior_starts=[tors_6], rotated_bond=(0,1)) → accepted=False, reason=rigid_transformation`。
  ⇒ 这不是"现在仍在生产重复起点"的活缺陷，而是**历史包早于守卫**；修复方向是「按结果坐标去重」的回归测试 +
  将来重建时拒绝同轴同片段重复。

## 3. 更正前后结论

| 项 | 更正前（2026-10-29 上午） | 更正后 |
|---|---|---|
| M_plus `tors_6/7/8` | 「不同自由度探针塌缩到同一平底谷」 | **同一起点的重复计算**；末值相同是预期，不构成独立起点检验 |
| LiM_2plus `tors_6/8` | 同上 | 同上（`tors_7` 的 batch2/reopt_v3 才是不同输入） |
| 这 5 条腿是否算「独立新起点探索」 | 隐含算 | **不算**；成本与失败记录保留，但不计为起点覆盖 |
| 「起点侧已尽」 | 由 5 条腿支撑 | **不成立**；在重复输入上不能推出 |
| 「平台/步长噪声/Li 壳重排」 | 部分写成解释 | 降为**假设**；末 3 cycle 数值不足以证明，需路径级证据 |
| `OPT-COORD-1`（原 B） | 推荐 | **保留推荐**，但证据只来自 1 个独立 M_plus 输入 × 多次重复 |
| `LI-SHELL-1`（原 A） | 首轮不推荐 | 仍不推荐；且缺少真正独立起点对照 |
| `PREOPT-GFN2-1`（原 C） | 不推荐 | 仍不推荐；与旧草案的「B=GFN2 预优化」区分，只用唯一 ID |
| `START-GEN-1` | 无 | **新增为前置项**：先修生成/校验并按结果坐标去重，再谈真正独立起点（本地零成本；跑新起点须另行授权） |

## 4. 交付与边界

- 权威版本：`docs/handoffs/long_run_20261029/L04_DMC_TRACE/`（Lead）+ 本目录两份；
  `docs/handoffs/long_run_20261029/agent_b_dmc_trace/` 与 `L04_DMC_TRACE_RECHECK/` 为**审计副本**，保留不删，
  但结论以本目录与更正版 `DMC_MECHANISM_DECISION.md` 为准。
- **DMC 本轮停止未变**；本文件不含任何计算授权，也未重跑历史作业。
