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
## 2.2 ⚠ **§2.1 的起点推荐已撤回——权威门把「纯 Li 位移」误分类为 `ok_heavy_fragment`**（2026-10-27）

**实测更正**：`validate_candidate_start` 的 `heavy` 定义（`:322`）是 `s != "H"` ⇒ **含 Li**。
于是 `declared_li_change=False` 的**纯 Li 平移**探针，其 `heavy_change` 等于整体距离变化，
被判 **`ok_heavy_fragment` / `probe_class: heavy_fragment_torsion`**——
**而纯骨架（排除 H 与 Li）RMSD = 0.0000**。详细机制见 `LI_ONLY_MISCLASSIFIED_AS_HEAVY_20261027.md`。

| §2.1 选出的起点 | 含 Li RMSD | **纯骨架 RMSD** | Li 位移 | 判定 |
|---|---|---|---|---|
| `DOL li_coordination_away_01` | 0.1675 | **0.0000** | 0.45 Å | ❌ **纯 Li 位移** |
| `EC li_coordination_away_02` | 0.2098 | **0.0000** | 0.60 Å | ❌ **纯 Li 位移** |

⇒ **两者都不是骨架独立起点，推荐撤回。**

### 2.3 按**纯骨架口径**重新分类 28 条证据（`work/_regate_skeleton_only.py`，零成本只读）

| 态 | 骨架**真动** | 纯 Li 位移 | 真骨架起点（叶子名 @ 骨架对距变化） |
|---|---|---|---|
| **DOL\|LiM_2plus** | **5** | 7 | `ring_pucker_00`(0.0601)、`_01`(0.0187)、`_02`(0.0185)、`_03`(0.0490)、`p4_02_ring_pucker_twist`(**0.0771**) |
| **EC\|LiM_2plus** | **5** | 7 | `ring_pucker_00`(0.0252)、`_01`(0.0199)、`_02`(0.0210)、`_03`(0.0232)、`p4_02_ring_pucker_twist`(**0.0549**) |
| DMC\|M_plus | 2 | 0 | `p4_01_torsion…`(0.2743)、`p4_02_torsion…`(0.2432) |
| DMC\|LiM_2plus | 1 | 1 | `p4_01_torsion…`(0.2623) |
| **合计** | **13 / 28** | **15** | — |

⇒ **DOL/EC 各有 5 条真骨架起点可用**（**不是** 10/12）：
**仍无需新开筛选批次**，但**可选范围收窄**，且**合格的都属 `ring_pucker`（环形变）类**。

**新的起点推荐（同一机械规则，但只在「骨架真动」集合内取值）**：
> **`DOL\|LiM_2plus` ⇒ `p4_02_ring_pucker_twist`（骨架 0.0771，最大）**；
> **`EC\|LiM_2plus` ⇒ `p4_02_ring_pucker_twist`（骨架 0.0549，最大）**。
> （两态的最大者都是 P4 的 ring_pucker twist；**无并列**，规则唯一确定。）

> **⚠ 注意**：这两个起点是 **`ring_pucker`（环形变）类**，而 P4 判定曾记它们「塌缩回源」；
> 但**骨架对距变化 0.055–0.077 Å > 1e-5 阈值** ⇒ 按本项目口径**算「动过」**。
> 是否够「独立」**仍属需要你确认的科学口径**（与 §5 的 `li_coordination_away` 问题同类，但对象不同）。

## 2.4 🚫 **阻塞级前置：DOL/EC 目前没有登记通道**（2026-10-27 实测，见 `DOL_EC_NO_REGISTRATION_PATH_20261027.md`）

**本方案 §2.1–§2.3 的起点选择，在「登记」这一步会被卡住。** 实测：

| 通道（`build_production_ensemble_manifest.py`） | 读什么 | 覆盖的态 |
|---|---|---|
| `recovery_candidate_rows()`（`:411`） | `strict_recovery_v1_manifest.csv`（`:364`） | DEC/DME/DMSO/SL/TMP 系列（**无 DOL/EC**） |
| `torsion_probe_candidate_rows()`（`:454`） | glob **只匹配 `work/hpc_torsion_probe_v*/manifest.json`**（`:478`） | AN\|M_plus、**DMC** 两态（**无 DOL/EC**） |

⇒ **`DOL\|LiM_2plus` 与 `EC\|LiM_2plus` 在 `production_ensemble_candidates.csv`（119 行、14 条 `recovery_v1_start`）里
没有任何 `recovery_v1_start` 行**（只有 `primary` 与 `round1_extra`/`li_motif`）。

**后果**：manifest 由 candidates 驱动 ⇒ 无候选行 ⇒ 进不了 structures 表 ⇒ 进不了 `latest_members`
⇒ `coverage_route` 看不到 `computed` 成员 ⇒ **即使生产腿跑完，状态永远 `limited`**。

**⇒ 在补上登记通道之前，本方案的 §3（提交生产）不应执行。**

**补通道的要点（须你批准）**：
① 版本化新增一条通道，`source_kind = p4v2_screening_v1_start`；
② **只收权威门判为骨架真动的 13 条**（`work/skeleton_only_reclassification.json`），**排除 15 条纯 Li 位移**；
③ **不得**简单把 glob 扩到 `hpc_xtb_screening_v2`——那会让纯 Li 位移探针进候选
（P4/v2 的 `probe_class` 是**错的** `heavy_fragment_torsion`，见 `LI_ONLY_MISCLASSIFIED_AS_HEAVY_20261027.md`）。

## 3. 生产级验证的执行形态（若批准）

| 项 | 方案 |
|---|---|
| 方法 | **完全冻结**：`wB97X-D4 / def2-TZVPD / SMD(乙腈) 298.15 K`、`Opt VeryTightOpt AnFreq` 解析梯度（**禁 NumGrad**）、`TightSCF SlowConv` |
| 每态起点数 | **1 个**（先各态一个最有证据的起点；取得 QC 与去重结果后才决定是否用第二个，符合计划 item 7） |
| 救援 | 每态**≤1 次**「有原因且父作业已终结」的救援（计划纪律） |
| 资源 | `orca_production_v1`（4 核）+ `%pal nprocs 4` 一致；**核数三方一致**（脚本 / profile / `cores.txt`） |
| **成本口径（两种，分开写）** | **实测口径**：生产腿均值 **9.86**、中位 8.13、**p90 18.41** CH/腿；**提交器预留口径**＝`核 × 墙钟 × 元素数` = **4 核 × 24 h = 96 CH/腿**（见 §3.1） |
| **本批（建议）** | **2 态 × 1 起点 = 2 条生产腿**；**实测预期 ≈36.8 CH**（2 × p90 18.41）；**在飞预留 192 CH**（2 × 96）；两者均 **< 512** |
| **支付来源** | **512 首轮生产额度**（**不是** 30.12 筛选余量）——须**单独冻结**并在提交前重验 `committed + reserved ≤ 800` |
| 停止条件 | ① 该腿 QC 通过 ⇒ 停（不再补第二起点，除非用户另行批准）；② 身份漂移 / 技术失败 ⇒ 如实记，**不重试**（漂移终点永不续作）；③ 超阈值 ⇒ 只允许**有界** `max-cycles` 续算，**不得降阈值** |

## 3.1 生产 profile 的预留口径实测（2026-10-27，**与 H2 同族的坑**）

| 项 | 实测值 |
|---|---|
| `orca_production_v1` | `cores=4`、**`wall_hours=24`** ⇒ 提交器注入 `--time=24:00:00`、cap 800 |
| **每腿预留** | **`4 核 × 24 h = 96 CH`**（**不是** p90 的 18.41） |
| **2 腿在飞预留** | **192 CH** |
| 生产腿实测墙钟（按 4 核换算） | min **0.10 h** / 中位 **2.03 h** / **p90 4.60 h** / max **7.98 h** |

**两条结论**：
1. **不会撞 512 cap**：2 腿在飞预留 192 CH ≪ 512；结算后按实测（2 × p90 18.41 = **36.82 CH**）释放。
2. **但墙钟被放大 3.0 倍**（24 h vs 实测 max 7.98 h）⇒ **预留 ×3**，这会**压缩可同时在飞的腿数**
   —— 若将来要一次投多腿，`96 CH/腿` 会很快吃掉 512（**512 / 96 ≈ 5.3 腿**）。

> **⚠ 与 H2 的关系（必须说清）**：H2 那次的问题是「**单点误用生产腿基准**」；
> 这次的问题是「**profile 墙钟远大于实测墙钟**」——**两者同族**（都是**口径/参数与实测不符**），
> 但**本批不因此改动 profile**：`orca_production_v1` 是**全仓共用的生产 profile**（还有 60 条历史腿与 800 总 cap 依赖它），
> 擅改会波及既有账本与验收口径。**故本方案只用「申报即按 96 CH/腿 预留」这一事实**，
> 并在提交前重验 `committed + reserved ≤ 800`（H2 式五门之一）。

**若你希望降低预留占用**，可选（**需你批准，我不擅改**）：
新增一个专用生产 profile（如 `orca_production_8h`，`wall_hours=8`）⇒ 预留降至 **32 CH/腿**；
但**必须先做「无翻转证明」**（证明它不改变任何既有已提交腿的成本/验收），且**须与 `--time` 实测上限一致**。

### 3.2 ⚠ **登记接线要求**：`member_role` 写错 = 静默阻塞整条接受路径（2026-10-27 新增，`PRODUCTION_ROLE_WIRING_20261027.md`）

`build_production_ensemble_aggregator.py` 有**角色白名单**（`:610` 与 `:696`）：

```
if r["member_role"] not in ("round1_extra", "recovery_v1_start"): continue
```

**`:691-696` 的注释就是一份事故报告**：
> 「*EVERY first-class member role must be listed here. A missing role is not a cosmetic omission:
> the member then never enters `latest` … and the state can never leave `limited` —
> `recovery_v1_start` was missing exactly so, which silently blocked the whole acceptance path.*」

**现有四类角色**（`production_ensemble_structures.csv`，238 行实测）：

| `member_role` | 行数 | 进 `latest`？ | 计入接受？ |
|---|---|---|---|
| `primary` | 48 | 走另一条路 | 基线 |
| **`round1_extra`** | 110 | **✅** | **✅** |
| **`recovery_v1_start`** | 44 | **✅** | **✅** |
| **`round2_audit_extra`** | 36 | **❌** | **仅 ceiling（ceiling-only）** |

⇒ **本批新腿必须登记为 `recovery_v1_start`**（其语义即「a NEW independent minimum … first-class member」，`:606-608`）；
**登记成 `round2_audit_extra` 会静默阻塞**（状态永远 `limited` 且**不报错**）。

**同时必须满足的 6 条**（逐条可复核）：
1. `member_role = recovery_v1_start`（或经裁定用 `round1_extra`）；
2. `member_key` 与该态在 `coverage_reviews.csv` 的证据列一致（聚合器 `:649-651` 以 `kept_keys` 反作弊）；
3. `status` 最终为 **`computed`**（`build_coverage_reviews.py:175` 只计 `computed`）；
4. **`production_evidence` 三字段非空**：`imaginary_modes`、`final_geometry_sha256`、`log_sha256`
   （`build_coverage_reviews.py:334-338`），**且过冻结五阈值与身份 QC**；
5. `search_outcome` 属三类之一 **且** `registered_starts` 非空（`build_coverage_reviews.py:150-160`）；
6. **命名族序号高于该成员全部历史序号**（项目红线）。

> **这是本方案第二处「静默阻塞」类约束**（第一处见 `0mvp79e3`：必须有生产恢复成员才能离开 `search_exhausted`）。
> **共同点：「有结果」≠「被系统看见」**，中间隔着一层登记/白名单，**失败时不报错**。

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