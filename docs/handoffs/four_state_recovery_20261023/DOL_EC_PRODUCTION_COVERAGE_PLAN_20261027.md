# DOL/EC 生产级覆盖验证方案（预注册草案，2026-10-27）

> 执行**用户裁定第 2 步**：「为 DOL/EC 各准备一个**生产级覆盖验证方案**。从**可追溯、经过非刚体与身份预检的
> 独立起点**出发，冻结**候选、次数、成本和停止条件**。**单纯重复提交已知极小的相同几何，不能冒充独立搜索。**」
>
> 状态：**draft / 未授权 / 零作业**。本文**只出方案**，不动 512/256 额度、不提交。

## 1. 这一步要解决什么（先把问题定义准确）

| 事实（实测） | 含义 |
|---|---|
| `DOL\|LiM_2plus` 与 `EC\|LiM_2plus` 的复核 `verdict = search_exhausted` | 当前**没有生产恢复成员**（`latest_members` 空） |
| `accepted` 只认 `verdict == "resolved"`；`resolved` 只由 `multi_basin_coverage` / **`single_basin_verified`** 产生 | 要恢复**必须有生产级证据** |
| 28 条 P4/v2 筛选证据**已登记**（`SCREENING_EVIDENCE_REGISTRATION_20261027.md`） | 但**筛选证据 ≠ 生产证据**；登记**不改变** route |
| 用户裁定 | 「**DOL/EC 不必强行找到第二个极小才能恢复，但必须证明独立起点在生产方法下通过了验证**」 |

⇒ **目标不是「找第二个极小」，而是「让一个独立起点过生产 QC」**：
- 若该起点**复现已接受极小** + 搜索范围等证据齐全 ⇒ **`single_basin_verified`** ⇒ `resolved` ⇒ **`accepted`**；
- 若得**新极小** ⇒ `multi_basin_coverage` ⇒ 同样 `resolved`；
- QC 失败 ⇒ 继续 `limited`，如实记原因与成本。

## 2. 起点从哪里来（**必须过权威预检**）

**唯一候选门**：`build_torsion_probe_package.validate_candidate_start`（`:258`）。实测其拒绝项共 **11 类**，
其中与用户要求直接对应的三项：

| 拒绝理由 | 对应要求 | 实测 |
|---|---|---|
| **`rigid_transformation`** | **「相同几何不能冒充独立搜索」** | ✅ **已验证**：把某起点与**自身**比对 ⇒ 返回 `rigid_transformation`、`accepted=False` |
| **`ring_broken`** | 非刚体变化（环完整性） | 门内建 |
| **`li_coordination_changed`** | Li 身份/配位（**须 `declared_li_change=True` 才可能接受**） | 门内建 |
| 另含 `malformed_input` / `not_a_single_bond_rotor` / `collision_or_new_bond` / `mapping_unresolved`（fail-closed）/ `equivalent_start` 等 | 身份与拓扑预检 | 门内建 |

**接受类别**只有两类：`ok_methyl_rotor`（重骨架未动）、`ok_heavy_fragment`（重骨架真动）。
**⇒ 「独立起点」的定义是机器判定的**，不是我口头声明。

**DOL/EC 的候选来源（按用户裁定的 4 步衔接）**：
1. **首选**：P4/v2 已登记筛选证据中，**被权威预检判为 `ok_heavy_fragment` 的起点**（重骨架真动 ⇒ 最有资格算独立）；
2. 次选：若上一步为空，则**另出新的筛选批次**（须预注册 + 走 32 CH 筛选余量的版本化重分配）；
3. **禁止**：拿 `ring_pucker` 的塌缩结果、或与已登记极小**同一几何**去充当独立起点。

> **✅ 前置判据已跑（2026-10-27，零成本只读）**：`work/_screening_probe_regate.py` 用**同一权威门**
> 复核了 28 条已登记筛选证据（结果落 `work/screening_probe_regate.json`）：
>
> | 态 | `ok_heavy_fragment`（合格独立起点） | `li_coordination_changed` |
> |---|---|---|
> | **DOL\|LiM_2plus** | **10** | 2 |
> | **EC\|LiM_2plus** | **12** | 0 |
> | DMC\|M_plus | 2 | 0 |
> | DMC\|LiM_2plus | 1 | 1 |
> | **合计** | **25 / 28** | 3 |
>
> ⇒ **DOL 有 10 条、EC 有 12 条被判定为「重骨架真动」**，**足够直接选出独立起点，无需新开筛选批次**
> （⇒ 第 2 点「是否批准版本化重分配」**当前不需要**）。
> **3 条 `li_coordination_changed`** 是 Li 配位改变类：该门只在显式 `declared_li_change=True` 时才可能接受，
> 本方案的起点选择**避开这 3 条**（它们仍作为筛选证据保留）。
>
> **⚠ 一处自查更正（如实记录）**：该脚本首版把父级几何字段名写成 `source_relpath`，
> 实测 **28/28 全部 `parent_missing`**（无效结果）；查盘后确认真实字段是 **`source_geometry`**，改正后得出上表。
> **若不复核就会把「我的字段名写错」误报成「28 条全不合格」。**

## 2.1 起点已按机械规则选出（2026-10-27，`work/_pick_production_starts.py`）

**规则先写死、再取值**（同 H2 纪律，排除挑有利结果）：
> candidates＝权威门判为 `ok_heavy_fragment` 的探针；
> score＝**探针与父级的重原子 RMSD**（越大＝重骨架越不同）；**取最大**；**并列取最小叶子名**。

| 态 | 合格候选数 | **选出** | 重原子 RMSD vs 父级 |
|---|---|---|---|
| **`DOL\|LiM_2plus`** | 10 | **`li_coordination_away_01`** | **0.1675** |
| **`EC\|LiM_2plus`** | 12 | **`li_coordination_away_02`** | **0.2098** |

**并列已按规则打破**（两态都触发）：DOL 的 `away_01`/`away_04` 同为 **0.1675**、EC 的 `away_02`/`away_05` 同为 **0.2098**
⇒ 均取**最小叶子名**。

**完整候选表**落 `work/production_start_selection.json`（含每条 RMSD），可逐项复核。

> **⚠ 注意（诚实标注）**：两个选出的起点都属 **`li_coordination_away`** 类——
> 即「Li **远离**位移」。它们通过权威门是因为**重骨架 RMSD 达 0.17–0.21 Å**（非塌缩），
> 但**它们改变的是 Li 配位方向**。这与「DOL/EC 的差异主要在 `O–C–O–Li` 配位二面角」的既有认识一致。
> **是否接受这类起点作为「独立起点」，仍属你裁定的口径问题**——
> 本方案只保证它**过了权威预检门**且**机械规则可复核**，不替你做这项科学判断。
## 3. 生产级验证的执行形态（若批准）

| 项 | 方案 |
|---|---|
| 方法 | **完全冻结**：`wB97X-D4 / def2-TZVPD / SMD(乙腈) 298.15 K`、`Opt VeryTightOpt AnFreq` 解析梯度（**禁 NumGrad**）、`TightSCF SlowConv` |
| 每态起点数 | **1 个**（先各态一个最有证据的起点；取得 QC 与去重结果后才决定是否用第二个，符合计划 item 7） |
| 救援 | 每态**≤1 次**「有原因且父作业已终结」的救援（计划纪律） |
| 资源 | `orca_production_v1`（4 核）+ `%pal nprocs 4` 一致；**核数三方一致**（脚本 / profile / `cores.txt`） |
| **成本口径（两种，分开写）** | **实测基准**：生产腿均值 **9.86**、中位 8.13、**p90 18.41** CH/腿；**提交器预留**＝`核 × 墙钟 × 元素数`（须按 profile 的 `wall_hours` 算，**不能只写脚本 `--time`**） |
| **本批上界（建议）** | **2 态 × 1 起点 = 2 条生产腿**；按 **p90 18.41** 估 ⇒ **≈37 CH**；预留按墙钟另算 |
| **支付来源** | **512 首轮生产额度**（**不是** 30.12 筛选余量）——须**单独冻结**并在提交前重验 `committed + reserved ≤ 800` |
| 停止条件 | ① 该腿 QC 通过 ⇒ 停（不再补第二起点，除非用户另行批准）；② 身份漂移 / 技术失败 ⇒ 如实记，**不重试**（漂移终点永不续作）；③ 超阈值 ⇒ 只允许**有界** `max-cycles` 续算，**不得降阈值** |

## 4. 每腿完成后自动走覆盖路线（用户裁定第 4 步）

| 实测结果 | route | verdict | ⇒ acceptance |
|---|---|---|---|
| QC 通过 + **复现已接受极小** + 搜索范围等证据齐全 | **`single_basin_verified`** | `resolved` | **`accepted`** |
| QC 通过 + **得新极小** | `multi_basin_coverage` | `resolved` | **`accepted`** |
| QC 失败 / 证据不完整（含缺哈希、缺搜索范围文档） | `known_basin_reproduction` 或维持 | `unresolved` | 继续 `limited` |

**关键纪律**：**由机器路线自动决定**，**不手工写 verdict**、**不为凑 48/48 放宽 route 准入**。

## 5. 明确**不做**（守线）

- ⛔ 不降五阈值、不改 48 分母、不手写 `accepted`；
- ⛔ **不用同一几何**重复提交冒充独立搜索（已有 `rigid_transformation` 机器守卫）；
- ⛔ 不把 28 条筛选证据当生产证据；
- ⛔ 不从 30.12 筛选余量支取（本批属**首轮生产**，须走 512 并单独冻结）；
- ⛔ 未获授权前不提交任何作业（`submission_gate=HOLD`）。

## 6. 需要你批准的点

1. ~~是否先执行 §2 的前置判据~~ ⇒ **已完成**（25/28 `ok_heavy_fragment`；DOL 10 条、EC 12 条）；
2. ~~若需新开筛选批次~~ ⇒ **当前不需要**（DOL/EC 各有充足合格起点）；
3. **生产批预算冻结**：是否按 §3 的「**2 腿**（DOL/EC 各 1）、**p90 估 ≈37 CH**、**走 512 首轮生产额度**」冻结
   ——**这是本方案唯一需要你决定的钱**；
4. **起点选择确认**：从 DOL 的 10 条 / EC 的 12 条 `ok_heavy_fragment` 中，
   按**机械规则**（如「与已登记极小的重原子 RMSD 最大者优先，并列取最小叶子名」）各选 1 条，
   规则先写死再取值（同 H2 的做法）——请确认该规则；
5. **是否批准提交**（在 3–4 明确之后）。

## 7. 证据出处

- 权威门：`build_torsion_probe_package.py::validate_candidate_start`（`:258-`，11 类拒绝 / 2 类接受）
- 实测：自比 ⇒ `rigid_transformation`、`accepted=False`（本轮，**零成本复核**）
- 筛选证据：`SCREENING_EVIDENCE_REGISTRATION_20261027.md`（28 条，DOL/EC 24 + DMC 4）
- 成本基准：`production_cost_ledger.csv`（60 腿，p90 18.41 / 中位 8.13）
- 用户裁定：`PROBE_REGISTRATION_GAP_20261027.md §3.5`、记忆 `0mvp79e8`