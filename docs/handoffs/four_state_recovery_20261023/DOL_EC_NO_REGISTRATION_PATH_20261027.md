# DOL/EC 生产起点**没有登记通道**（2026-10-27，阻塞级接线缺口）

> **本文更正/收紧此前的方案假设。** `DOL_EC_PRODUCTION_COVERAGE_PLAN_20261027.md` 假设
> 「选定起点 → 提交生产 → 结果登记为 `recovery_v1_start` → 走 `single_basin_verified`」。
> 本轮实测：**「结果登记为 `recovery_v1_start`」这一步，DOL/EC 目前根本没有通道。**
> **纯只读，不改任何代码、账本或 verdict。**

## 1. 事实（逐项实测）

`build_production_ensemble_manifest.py` 里只有**两条**产出 `recovery_v1_start` 候选行的通道：

| 通道 | 读什么 | 实测产出 |
|---|---|---|
| `recovery_candidate_rows()`（`:411`） | `outputs/.../recovery/strict_recovery_v1_manifest.csv`（`RECOVERY_MANIFEST`，`:364`） | **11 行**，`source_kind = strict_recovery_v1_start` |
| `torsion_probe_candidate_rows()`（`:454`） | `work/hpc_torsion_probe_v*/manifest.json`（`:478` 的 **glob 只匹配这一个前缀**） | **3 行**，`source_kind = torsion_probe_v1_start` |

**两条通道的按态覆盖（实测）**：

| 通道 | 覆盖的态 |
|---|---|
| `recovery_candidate_rows` | `DEC\|M`、`DME\|LiM_2plus`、`DME\|M_plus`、`DMSO\|LiM_plus`、`SL\|LiM_2plus`(2)、`TMP\|LiM_2plus`、`TMP\|LiM_plus`(2)、`TMP\|M_plus`(2) |
| `torsion_probe_candidate_rows` | `AN\|M_plus`、`DMC\|LiM_2plus`、`DMC\|M_plus` |

**⇒ `DOL\|LiM_2plus` 与 `EC\|LiM_2plus` 在两条通道里都为空。**

## 2. 候选表现状（`production_ensemble_candidates.csv`，119 行）

| `source_kind` | 行数 |
|---|---|
| `production_leg:*`（主态腿） | 12×4 = 48 |
| `free_conformer` | 32 |
| `li_motif` | 25 |
| `strict_recovery_v1_start` | **11** |
| `torsion_probe_v1_start` | **3** |

`member_role` 分布：`primary` 48、`round1_extra` 57、**`recovery_v1_start` 14**（= 11 + 3）。

**逐态核对 `recovery_v1_start` 的有无**：

| 态 | 候选表里的行 | 有 `recovery_v1_start` 吗 |
|---|---|---|
| **`DOL\|LiM_2plus`** | `primary`(production_leg)、`round1_extra`×2（`c05`/`c01`，`li_motif`） | **❌ 无** |
| **`EC\|LiM_2plus`** | `primary`(production_leg)、`round1_extra`×1（`c03`，`li_motif`） | **❌ 无** |
| `DMC\|M_plus` | `primary`、`round1_extra`(`28`)、**`recovery_v1_start`(`tors_8_0_1_2`)** | ✅ 有 |
| `DMC\|LiM_2plus` | `primary`、`round1_extra`(`c06`)、**`recovery_v1_start`(`tors_7_0_1_2`)** | ✅ 有 |

⇒ **DMC 两态有登记通道（来自 `hpc_torsion_probe_v*`），DOL/EC 没有。**

## 3. 为什么这是阻塞级（不是「以后再说」）

按已实测的接受链（`0mvp79e3`、`0mvp7xbj`）：

```
生产腿跑完 → 结果进 production_ensemble_structures.csv
   ↓ 必须 member_role ∈ {round1_extra, recovery_v1_start}（:610/:696 白名单）
   ↓ 该成员才会进 latest_members
   ↓ coverage_route 才看得到 computed 成员
   ⇒ 才可能 resolved ⇒ accepted
```

**而「进 structures 表」的前提是「先在 candidates 表里有这一行」**（manifest 由 candidates 驱动）。
**DOL/EC 没有 candidates 行 ⇒ 即使生产腿跑完并导入，也无处挂靠 ⇒ 状态永远 `limited`。**

**⇒ 这正是计划 item 2 警告的「计算成功之后才发现验收器无入口」的实例**，
而且是**第三处**（前两处：`search_exhausted` 需生产成员、`member_role` 白名单）。

## 4. P4/v2 的探针为什么接不上（根因）

`torsion_probe_candidate_rows()` 的 glob 是 **`work/hpc_torsion_probe_v*/manifest.json`**（`:478`）——
**只认 `hpc_torsion_probe_v*` 这一个命名族**。而本批的证据在：
- `work/hpc_four_state_p4_xtb_screening_v1/manifest.json`
- `work/hpc_xtb_screening_v2/manifest.json`

**两个都不匹配该 glob** ⇒ 即使它们各有 `members` 数组，也**不会被任何通道读取**。

## 5. 处置建议（**不自行执行**）

| # | 建议 | 说明 |
|---|---|---|
| 1 | **必须补一条登记通道**（版本化） | 让 P4/v2 证据能产出 `recovery_v1_start` 候选行；**须你批准**，因为它是**新增登记语义** |
| 2 | 通道设计要点 | 只收**权威门判为骨架真动**的探针（`work/skeleton_only_reclassification.json`，13 条）；**排除纯 Li 位移**（15 条）；每条带 `geometry`/`sha256`/`probe_class`/`source_kind=p4v2_screening_v1_start` |
| 3 | **不要**把 glob 扩到 `hpc_xtb_screening_v2` 了事 | 那会让**纯 Li 位移**探针也进候选（因为 P4/v2 的 `probe_class` 是**错的** `heavy_fragment_torsion`，见 `LI_ONLY_MISCLASSIFIED_AS_HEAVY_20261027.md`）⇒ **必须先修分类口径或在新通道内重算** |
| 4 | 无通道时的替代路径 | 若你不想新增通道，则 DOL/EC **无法通过生产腿恢复**，只能按 H3「本轮以 `limited` 结题」 |

## 6. 与「静默阻塞」三处约束的汇总

| # | 约束 | 漏掉的后果 | 出处 |
|---|---|---|---|
| 1 | 必须有**生产恢复成员**才能离开 `search_exhausted` | 只补 `registered_starts` 无效 | `0mvp79e3` |
| 2 | `member_role` 必须在 `{round1_extra, recovery_v1_start}` | 永不进 `latest`，永远 `limited` | `0mvp7xbj` |
| 3 | **候选表里必须先有该态的行**（本轮） | **生产腿跑完也无处挂靠** | 本文 |

**共同点：「有结果」≠「被系统看见」**，中间隔着**登记链**，而每一环**失败都不报错**。

## 7. 守线

- ⛔ 不改 `torsion_probe_candidate_rows()` 的 glob（会改变历史登记语义）；
- ⛔ 不改 candidates 表（生成物）；
- ⛔ 不把纯 Li 位移探针塞进候选；
- ⛔ 未获授权前不提交。

## 8. 证据出处

- 通道定义：`build_production_ensemble_manifest.py:411`（`recovery_candidate_rows`）、`:454`（`torsion_probe_candidate_rows`）、
  `:478`（glob）、`:364`（`RECOVERY_MANIFEST`）、`:615`（`--register-recovery` 开关）
- 白名单：`build_production_ensemble_aggregator.py:610`、`:696`
- 实测：`recovery_candidate_rows()` 11 行、`torsion_probe_candidate_rows()` 3 行、
  `production_ensemble_candidates.csv` 119 行（`recovery_v1_start` 14 行，**DOL/EC 为 0**）
- 相关：`DOL_EC_PRODUCTION_COVERAGE_PLAN_20261027.md`、`PRODUCTION_ROLE_WIRING_20261027.md`、
  `LI_ONLY_MISCLASSIFIED_AS_HEAVY_20261027.md`