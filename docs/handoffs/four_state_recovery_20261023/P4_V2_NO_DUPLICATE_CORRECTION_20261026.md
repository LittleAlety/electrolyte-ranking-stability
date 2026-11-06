# 更正：P4/v2 的 `no_duplicate` 差异**不是**甲基转子，而是 **Li 配位二面角**（2026-10-26）

> 触发：用户裁决第 (6) 条要求逐条裁定「等价氢映射／转子差异」还是「冻结规则下可进 DFT 的独立起点」，
> 并指出 **v2 的 20/20 `attempt_id` 错配**与其判定可能未真正执行。
> 本文**撤回**我在 `P4_FOUR_ELEMENTS_ELIGIBILITY_20261026.md` 里的物理解释，并给出实测更正。

## 1. 撤回的结论（我错了）

| 我先前的说法 | 实测 | 判定 |
|---|---|---|
| 「差异是**甲基转子**（H7↔H10 置换）」 | `find_rotatable_bonds` 返回的 `(a,b,na,nb)` **四个原子全非 H**；`mapped_torsion_worst` 用的正是这四个 ⇒ 最差扭转是**纯重原子二面角** | **错，撤回** |
| 「差异是**等价原子置换**」 | 产生最差扭转的二面角是 **`O–C–O–Li`**（含 Li、**不含 H**）；另外两条重原子扭转 delta 仅 **0.1°** | **错，撤回** |
| 「v2 20/20 全为 `duplicate_of_registered_minimum`」 | 我只比了 RMSD，**没跑冻结的扭转条件**；见 §3 | **错，撤回** |

**实测全量（24 条元素）**：最差扭转**全部是 `O–C–O–Li`**；**含 Li 14 条、含 H 0 条**；
DOL 的 10 条 `n_rot=0`（无可旋转键，故无扭转条件可比）。

## 2. 正确的物理解释

差异**只在 Li 的配位二面角取向**（`O–C–O–Li`，100–174° 差），而：
- **重原子骨架几乎完全同一**：RMSD **0.0004–0.0068 Å**；
- **Li 配位壳层的近邻距离逐位一致**（DMC 1.804 vs 1.803 Å；EC 1.851 vs 1.849 Å；`<1.6 Å` 紧接触 = 0）；
- 产生差异的键**两端均为重原子**（如 `C–O`），却因 `O–C–O–Li` 二面角含 Li 而改变。

⇒ 物理读数：**同一盆地内 Li 相对碳酸酯平面的取向态**（Li 是配位中心，非共价骨架的一部分）。
**它既不是等价氢映射，也不是骨架无关的噪声**——因此**不能**按「等价映射」把它归为重复，
**也不能**按「构象噪声」忽略它。**按冻结 10° 规则它仍是独立的合格起点**（用户裁定：不得静默改写）。

## 3. 我的 v2 判定从未真正执行（第二个真缺陷）

- `build_p4_screening_adjudication.mol_name()` 只接受**裸 record id**（`C01`），
  而 v2 的 `candidate.json` 存**复合形式** `C09|LiM_2plus` ⇒ 整个 v2 包**判定失败**
  （`mol_id C09|LiM_2plus has no registered name in either screening pool`）。
  **我此前的 v2 结论是用自写脚本、只比 RMSD 得到的**，不等于冻结五条件。
- **修复**：`mol_name()` 先剥 `"|"` 后缀（`C09|LiM_2plus` → `C09` → 查池得 `DOL`）；
  `--selftest` 仍 **20/20**。
- **修复后的真实 v2 机器判定**（`--package work/hpc_xtb_screening_v2`，20/20 `adjudicated`）：

| 组 | 机器结论（冻结五条件） |
|---|---|
| DOL `li_coordination_away` ×6 | 全部 `duplicate_of_registered_minimum` |
| DOL `ring_pucker` ×4 | 全部 `duplicate_of_registered_minimum` |
| EC `ring_pucker` ×4 | 全部 `no_duplicate_within_tolerance` |
| EC `li_coordination_away` ×6 | **混合**：2 条 `duplicate`、4 条含 `no_duplicate` |

⇒ **P4 4 条 + v2 的 6 条 `no_duplicate` + 4 条混合 = 与并行核验者一致的「14 条涉 `no_duplicate`」口径**。

## 4. 对结论的影响（措辞再收窄）

- **DOL**：v2 10 条**全为机器判定重复**，P4 2 条亦然 ⇒ DOL 的「未找到新盆地」**有冻结规则支撑**。
- **EC**：v2 10 条中 **10 条涉 `no_duplicate`**（4 纯 + 6 混合）⇒ EC 侧**存在冻结规则下合格的候选**，
  「单盆地」的说法对 EC **尤其不成立**。
- **全局**：仍维持用户裁定的表述——「**已登记的 P4／v2 筛选动作未找到可确认的新重骨架盆地**；
  不等于全局单盆地，不等于 800 CH 已耗尽」。

## 5. 证据

- 复算脚本：`work/_p4_four_elements.py`（RMSD/扭转/壳层）、`work/_v2_triage_out.json`（修复后的 v2 判定）
- 判定器修复：`build_p4_screening_adjudication.py::mol_name`（剥 `"|"` 后缀）
- 规则常量与实现：`find_rotatable_bonds` / `mapped_torsion_worst` / `torsion_deg`（聚合器）