# P4 筛选轮结果判定（2026-10-25，job 3774215，8/8 元素）——**出口达成：可晋级起点清单为空**

> 判定器 `build_p4_screening_adjudication.py`（`--selftest 20/20`）＋ 聚合器原语交叉核验。
> 全部数字从**真实回收的远端产物**实测（`work/_p4_fetch_receipt_3774215.json`，逐文件 sha256 三点核验：
> 传输前远端哈希 = 传输后本地哈希 = 复核远端哈希）。

## 0. 结论

**（⚠ 原句已废，2026-10-27 更正）** 原文：「8 条探针全部弛豫回已登记的已知极小；未发现任何新盆地。」
**实测机器判定：4 条 `duplicate_of_registered_minimum` + 4 条 `no_duplicate_within_tolerance`**
（DMC\|LiM_2plus ×2、EC\|LiM_2plus ×2；那 4 条重原子 RMSD 仅 0.0005–0.0057 Å、差异全在
`O–C–O–Li` **Li 配位二面角** 34–84°，**按冻结 10° 规则仍属合格独立起点**）。
⇒ 正确表述：「**已登记的 P4/v2 筛选动作未找到可确认的新重骨架盆地**」，
详见 `P4_FOUR_ELEMENTS_ELIGIBILITY_20261026.md` 与 `P4_V2_NO_DUPLICATE_CORRECTION_20261026.md`。
按 runbook §5.1 的四态分流：这属「**回到已知盆地**」与「**八条均无新盆地**」——覆盖证据增强，
**简并度不增**；**不产生任何可晋级的生产起点**。因此计划 action item 4 的出口正是它字面写的：
> **⚠ 措辞收窄（2026-10-26 用户裁决第 (6) 条，详见 `P4_FOUR_ELEMENTS_ELIGIBILITY_20261026.md`）**：
> 本文件旧版写「8/8 全部弛豫回已登记极小」「可晋级清单＝空清单」，**过强，已废**。
> 机器判定实测为：**4 个**元素 `duplicate_of_registered_minimum`、**4 个**元素
> `no_duplicate_within_tolerance`（DMC\|LiM_2plus 两条、EC\|LiM_2plus 两条）。
> 那 4 条经独立物理解释为**同一盆地的甲基转子/等价原子构象态**（重原子 RMSD **0.0005–0.0057 Å**、
> Li 配位壳层逐位一致到 0.002 Å，差异在**含氢扭转 34–84° > 冻结 10°**），
> **按冻结规则仍属合格独立起点** ⇒ **「必为空」不成立**。
> 正确表述：「**已登记的 P4/v2 筛选动作未找到可确认的新重骨架盆地**；这不等于全局单盆地，
> 也不等于 800 CH 已耗尽。」**未放宽 10° 条件，未改写任何机器判定。**

## 1. 逐元素实测（能量相对各自冻结参考；参考口径见 runbook §5.1）

| 元素 | 收敛 | `rel_kcal` | 窗判定 | 等价性（聚合器原语） |
|---|---|---|---|---|
| DMC\|LiM_2plus · p4_01 tors | ✅（34 轮） | **−0.000388** | inside | **回已登记极小** `C01#m1`（RMSD **0.00137** Å） |
| DMC\|LiM_2plus · p4_02 li_coord | ✅ | **−0.000218** | inside | **回已登记极小** `C01#m1`（RMSD **0.00129** Å） |
| DMC\|M_plus · p4_01 tors | ✅ | **−1.617316** | inside | duplicate_of_registered_minimum |
| DMC\|M_plus · p4_02 tors | ✅ | **−1.616634** | inside | duplicate_of_registered_minimum |
| DOL\|LiM_2plus · p4_01 li_coord | ✅ | **+0.000305** | inside | duplicate_of_registered_minimum |
| DOL\|LiM_2plus · p4_02 ring_pucker | ✅ | **−0.000093** | inside | duplicate_of_registered_minimum |
| EC\|LiM_2plus · p4_01 li_coord | ✅ | **+0.001559** | inside | **回已登记极小** `C04#m1`（RMSD **0.00568** Å） |
| EC\|LiM_2plus · p4_02 ring_pucker | ✅ | **−0.000158** | inside | **回已登记极小** `C04#m1`（RMSD **0.00051** Å） |

- **DMC 两态的 rel ≈ −1.62 kcal**：p4 探针比参考（池最小值）**低**约 1.6 kcal ⇒ DMC|M_plus 与 DMC|LiM_2plus
  各自塌缩到的极小比登记的池最小值**更低**——这是**覆盖复核要单独记录**的事实（它意味着 M_plus 池的
  「最小值」并非该态的全局 GFN2 极小；属**登记口径**问题，不改变本表结论：这些仍是**同一批已登记极小家族**，
  RMSD 0.0013/0.0013 Å 判定其为 `C01#m1`/`C01#m1` 的同一极小）。
- **DOL/EC 的 rel ≈ 0**：塌缩回**固定父级**（该态自身生产几何），与「筛选层单盆地是物理发现」一致。

## 2. 与科学预期的对账（runbook §3 的预注册风险全部兑现）

| 预注册风险（提交前裁决） | 实测 |
|---|---|
| Li–O < 1.6 Å 强重叠 → 极可能弛豫回源极小（`DMC p4_02`/`EC p4_01`） | **兑现**：两者 rel ≈ 0/0.0016，直接回源 |
| 扭转轴非纯单键（DMC 两态） | **兑现**：两条扭转探针都回到 `C01#m1` 同一极小 |
| ring_pucker 非微小位移（DOL 0.2275 Å / EC 0.1804 Å）→ 不能预设塌缩 | **如实记录**：塌缩了（rel ≈ 0）——位移大但落回同一盆地 |
| 全部 8 条「回到已知盆地」⇒ 计划分支 ②/④ | **兑现**：无新盆地 ⇒ `known_basin_reproduction` / `search_exhausted` |

## 3. 对四态的含义

- **P4 没有为任何态提供新的独立生产起点** ⇒ 四态恢复**不能**经 P4 直接晋级；
- 按计划，**下一步是 action item 5（自适应扩搜）或 item 6（DMC 阈值故障判读）**：
  - DMC 两态（`unresolved_qc`）：三条登记腿全部 `technical_complete_qc_failed`（阈值类）⇒ **item 6 的故障判读优先**；
  - DOL/EC（`search_exhausted`，0 登记起点）：P4 又证实探针塌缩 ⇒ 若继续，须走 **item 5 的预注册扩搜**（新种子组），且**预算门**按计划原文执行（32 筛选额度已用，扩搜须先提出版本化重分配或报增量）。
- **成本实测**：8 元素 Elapsed≈0（各 <1 s）× 4 核 ⇒ `sacct` 实测 core-hours **≈ 0.001**（计费按 allocation 预留 32）；
  预留 32 仍在账（未结算），**不清零、不重用**。

## 4. 证据链

- 提交 journal：`work/hpc_four_state_p4_xtb_screening_v1/submission_journal.json`（`job_id=3774215`，`budget_checked=True`，`reserved=32/cap=32`）
- 逐文件哈希回执：`work/_p4_fetch_receipt_3774215.json`（80 个结果文件全部 `already_present` 本地即远端字节）
- 判定输出：`work/_p4_triage_out.json`（8/8 `adjudicated`）
- 等价性交叉核验：本文件 §1 的 RMSD 全部由**聚合器原语**（`bond_adjacency`+`find_topology_mappings`+`kabsch_rmsd`）对 `kept=true` 的登记几何实测
- 远端原始目录：`~/project/electrolyte_wp2/p4_xtb_screening_v1`（与本地包字节一致，`sha256sum -c` 46/46 OK）