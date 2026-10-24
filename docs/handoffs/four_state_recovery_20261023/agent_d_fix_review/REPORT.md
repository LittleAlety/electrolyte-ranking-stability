# Agent D：两处选择器修复的对抗复核（Lead 接手；承担者零产物）

## 0. 交付状态（如实记录）
- 承担本任务的 subagent（`2c29a6ed-fcac-43eb-a91c-648541474ddd`）**失败退出、无收尾消息**，`agent_d_fix_review/` 下**零文件**。
- 按纪律「零产物不计完成，Lead 收回」，本报告的 **`challenge.py` 与全部结论均由 Lead 亲自跑出**，
  不是转述：D 没有留下任何可复现的中间步骤。

## 1. 被审对象（Lead 自己在本轮做的两处修复）
1. `scripts/wp_production/build_torsion_probe_package.py` → `select_candidates()`：`max_keep` 命中时
   **原为 `break`**（被截断的候选既不入 `accepted` 也不入 `refused`，静默消失），改为逐条登记
   `model` 拒绝并 `continue`，detail 带 `gate_reason` 与 `gate_evaluated`。
2. 同文件 `validate_candidate_start()`：旋转轴原只校验 `axis[1] >= len(symbols)`，
   **漏 `axis[0] < 0`**（负索引会从尾部静默取原子），补上后归入 `malformed_input`。
3. `tests/test_candidate_generators.py`：两个回归测试（cap 会计 + 负索引）。

## 2. 证伪尝试与实测（`challenge.py`，退出码 0）
| 挑战项 | 实测 | 结论 |
|---|---|---|
| 夹具规模 | DOL\|LiM_2plus 环褶皱原始候选 **24** 个 | 规模足够 |
| 会计完整性 `max_keep=None` | accepted=6 + refused=18 = **24/24** | 未被证伪 |
| 会计完整性 `max_keep=1` | accepted=1 + refused=23 = **24/24** | 未被证伪（原缺陷下为 1/24） |
| 会计完整性 `max_keep=2` | accepted=2 + refused=22 = **24/24**，且 accepted ≤ cap | 未被证伪 |
| **cap 不得遮蔽门禁失败** | 超上限但门禁失败的候选 reason = **`ring_broken`**（非 `max_keep_reached`） | 未被证伪 |
| 被 cap 候选是否已过门禁 | 5 个 `max_keep_reached` 全部 `gate_evaluated=True`、`gate_reason=ok_heavy_fragment` | 未被证伪 |
| **AST：候选能否结构性地消失** | `select_candidates` 内共 **3 个 `continue`**，逐个核对其前一条语句都是 `refused.append(...)`，**unpaired=none** | 未被证伪（结构性证明，非抽样） |
| 畸形轴穷举 | `(-1,1) (1,-1) (-1,-1) (0,99) (99,0) (2,2) (0,0)` **7/7 → `malformed_input`** | 未被证伪 |
| 是否修得过头 | 合法登记轴 `(1,2)` 未被误判为 malformed | 未被证伪 |
| 是否过度拒收真实候选 | 真实冻结包仍能构建 **8 任务 / 每态 2 个** | 未被证伪 |
| 同类索引下沉点扫描 | 构建器内 **4 处**「下标含算术」的取用点，当前均**无法被调用方以负数触达** | 未被证伪 |

**总结行：14 项挑战，14 项未被证伪，0 缺陷，退出码 0。**

## 3. 唯一保留观察（Important，非缺陷）
- `torsion_freedom_registry.csv` 的解析路径是**下一个值得盯的**索引来源：本次扫描确认它当前
  无法被调用方以负数触达，但 registry 是外部数据文件，若将来登记表出现负号原子号，护栏不在那一层。
  **最小修法（未实施）**：在 registry 解析处对原子号显式断言 `>= 0`，把 fail-closed 下沉到数据入口。
- 该观察不阻塞本次 P4 提交；已在 `P4_SUBMIT_RUNBOOK_20261024.md` 之外单独留档，供下一轮决定是否下沉。

## 4. 未覆盖范围
- 未改动、未评价 `select_candidates` 之外的候选生成器语义（环褶皱振幅集合、Li 位移 offset 量级）——
  那属 Agent A 的科学面，见 `agent_a_candidate_review/REPORT.md`。
- 未运行任何 ORCA/xTB 计算，未触网，未提交任何作业。
- 未复核 registry 数据本身的**内容正确性**（只复核了索引护栏缺口）。