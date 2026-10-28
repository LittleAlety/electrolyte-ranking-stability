# DMC 历史优化过程诊断与机制判断（L04/L05，2026-10-29）

只读本地既有 ORCA 日志；**未调用 ORCA/xtB、未提交任何作业、未改任何生产文件**。
产物：`DMC_OPTIMIZATION_TRACE.csv`（175 行，逐 attempt × 末 3 cycle × 五准则）、
`DMC_FAILURE_MATRIX.csv`（15 条 attempt 终态）、`INPUT_INDEX.md`（逐日志 sha256）。

## 1. 解析契约（避免把表当次数）

- 按实际表头识别 `Item / value / Tolerance / Converged` 的**竖排**几何收敛表（不是 SCF 表）；每个表 = 一个优化 cycle。
- 一个日志里可含多个优化段（如 reopt 从末几何重启）；`DMC_OPTIMIZATION_TRACE` 的 `cycle/of_cycles` 是**该段内**编号。
- 能量取表前最近的 `Current Energy .... <E> Eh`；TolE 用绝对值。
- `primary` 两行是单点/频率任务（无几何优化表）⇒ `cycles=0` 如实记，不拿它当"优化失败"。
- `tors_7_0_1_2 | pending` 无 `log_path` ⇒ `MISSING` + 原因，不补值。
- 三条 M_plus 探针日志**哈希不同**但末 cycle 五项数值与能量**逐位相同** ⇒ 是三次独立运行收敛到同一几何/同一极小，不是同一份日志的别名。

## 2. 终态证据（末 cycle，abs/tol 比值）

| 态 | attempt | 状态/类别 | cycles | TolE | RMSG | MAXG | RMSD步 | MAXD步 | ORCA 宣称收敛 |
|---|---|---|---|---|---|---|---|---|---|
| M+ | r1_000-017 `28` | superseded / strict_reopt | 22 | 10.49× | 0.61 | 0.46 | 0.34 | 0.69 | 是（close-enough） |
| M+ | r1_reopt4 `28` | **qc_failed** / strict_reopt | 2 | **3.12×** | 0.38 | 0.36 | 0.19 | 0.31 | 是（close-enough） |
| M+ | v1 `tors_6` | **qc_failed** / verytight | 24 | 0.57 | 0.27 | 0.20 | 0.93 | **1.62×** | 是（close-enough） |
| M+ | v1 `tors_7` | **qc_failed** / verytight | 24 | 0.57 | 0.27 | 0.20 | 0.93 | **1.62×** | 是（close-enough） |
| M+ | v1 `tors_8` | superseded / verytight | 24 | 0.57 | 0.27 | 0.20 | 0.93 | **1.62×** | 是（close-enough） |
| M+ | v2 realfragment `tors_8` | **qc_failed** / strict_reopt | 30 | **1.64×** | 0.29 | 0.26 | 0.42 | 0.70 | 是（close-enough） |
| Li+ | r1_036-053 `c06` | superseded / max_cycles | 49 | 11.99× | 1.46× | 0.96 | **9.00×** | **18.13×** | 否 |
| Li+ | continuation4 `c06` | **qc_failed** / strict_reopt | 18 | **1.10×** | 0.35 | 0.25 | 0.40 | 0.62 | 是（close-enough） |
| Li+ | v1 `tors_6` | **qc_failed** / max_cycles | 49 | 1.60× | 1.34× | **1.04×** | **10.14×** | **22.36×** | 否 |
| Li+ | v1 `tors_7` | superseded / strict_reopt | 45 | 4.43× | 0.28 | 0.28 | 0.42 | 0.61 | 是（close-enough） |
| Li+ | reopt_v3 `tors_7` | **qc_failed** / verytight | 30 | 2.17× | 0.33 | 0.27 | **1.51×** | **2.89×** | 是（close-enough） |
| Li+ | v1 `tors_8` | **qc_failed** / max_cycles | 49 | 1.60× | 1.34× | **1.04×** | **10.14×** | **22.36×** | 否 |

三处新事实（过程证据，非末值推断）：

1. **"close_enough" 被量化**：15 条 attempt 中 **9 条** ORCA 明确打印 *Convergence will therefore be signaled now* 同时至少一项 `NO`——即「ORCA 说 CONVERGED ≠ 过五阈值」在本 campaign 是**绝大多数**形态，不是边角。
2. **探针塌缩到同一点**：M_plus `tors_6/7/8` 末 cycle 五项与能量**逐位相同**（-343.544602288 Eh）、LiM_2plus `tors_6/8` 相同（-350.979520232 Eh）⇒ 不同自由度探针**都没有到达新的独立极小**，这是「同一平底谷」的直接证据（与筛选层 GFN2 的塌缩结论同向，且互相独立）。
3. **失败分成两类、机制不同**：
   - **步长受限型**（M_plus 全部 verytight 行）：能量/梯度/RMS 步全过，**唯 MAXD 步 1.62× 超**，而梯度仅 ~2×10⁻⁶ Eh/bohr ⇒ 优化器在 3×10⁻⁴ bohr 的步长噪声里停止；这是**坐标/步长控制**层面的问题，不是电子结构或势能面多极小问题。
   - **步长发散型**（LiM_2plus `tors_6/8`，49 周期）：MAXD 步 18–22×、RMSD 步 9–10×，梯度也超 ⇒ 优化在**较大幅度位移**中反复未收敛，与 Li 配位壳重排一致（仅 LiM_2plus 有 Li）。

## 3. 机制候选（逐条回答「改变什么—为何针对失败—如何否定—所需对照—冻结目标如何验证」）

### A. 显式 Li 配位处理（**只适用 LiM_2plus**）
- **改变什么**：首段优化把 Li–O/N 壳作约束或显式配位处理，再放开全自由度。
- **为何针对失败**：Li+ 的步长发散型失败（MAXD 18–22×）与 Li 壳重排一致。
- **如何否定**：若放开后仍在 ≤10 周期内 MAXD >2× 且最终几何与已登记极小 RMSD <0.35 Å，则 A 无益。
- **所需对照**：同一 P4 原始扰动几何、同一 profile、同一冻结阈值；对照=不做 Li 约束的既有 attempt（已有 49 周期数据）。
- **红线**：**M_plus 无 Li，禁止用它套 Li 配位机制**；旧 P4 重命名不算新机制；约束阶段产物不得直接当最终几何交 QC。

### B. 优化器步长/坐标系设定（推荐，版控 + 有限范围）
- **改变什么**：只改 ORCA 几何优化的坐标/信赖域控制（如 Redundant Internals → Cartesian，或调 trust radius 初值），**不改电子结构、介质、阈值、方法关键字**。
- **为何针对失败**：M_plus 是纯步长受限型（梯度已很低、唯 MAXD 1.62×），B 直接命中；LiM_2plus 的发散型也可能因坐标选择改善。
- **如何否定**：若在 ≤30 周期内 MAXD 步仍 >2× 而梯度/RMS 步已过，则 B 否定（说明是平坦谷而非坐标问题）。
- **所需对照**：与既有 24 周期 verytight attempt 逐项对比末 cycle 五准则；几何去重用生产原语；**不得只挑有利结果**。
- **可比性**：§6.2 明确「改变优化算法不自动要求全 cohort 重算」，但必须版本化并记录「仅 DMC 两态使用该设定」；阈值与验收不变。

### C. 更紧预优化 / 换泛函级别（**不推荐**）
- GFN2 更紧预优化不保证 DFT 阈值改善（既有 4 次同型失败已证）；换泛函属方法变更，超本轮范围。

## 4. 结论（有依据的推荐）

**推荐只做 B 的有限版控实验**（两态各一次、无救援自动追加）：
- 命题（可否证）：*在只改坐标/信赖域设定、其余冻结的前提下，DMC 两态能在 ≤30 周期内五项全过；否则 B 否定。*
- 规模：2 腿 × 16 CH（`orca_production_4h_v1` 4 核 × 4 h）＝ **32 CH**，从**新预算**支取（不动 800/600，也不占用 EC 的 32 CH 提议）。
- 停止：任一腿身份漂移/断环即停；SCF 不收敛即停；两腿各仅 1 次，失败即保留 `limited`，不自动追加。
- 出口：过五阈值 + 身份 + 零虚频 + 去重 ⇒ 按覆盖路线走 `single_basin_verified` / `multi_basin_coverage`；未过 ⇒ 如实保留 `limited` 并把 B 记为否证。
- **不推荐 A 作为首轮**（缺 Li 约束的对照数据，且只覆盖一半态）；**不推荐 C**（无新机制）。

## 5. 未覆盖与限制

- 未读取 `pending` 的 `tors_7` 日志（不存在）与该 batch 的 CANCELLED 元素；未核 `snapshots` 之外的 run/ 目录副本。
- `primary` 两行是单点任务，不参与优化过程判断。
- 本判断基于**末 3 cycle**；更早轨迹可用同一解析器扩展（脚本 `work/_dmc_trace.py` 可重跑）。
- 本轮 DMC 停止的裁决**未被本文件改变**：这里只是呈报可选新实验，**不构成授权**。
