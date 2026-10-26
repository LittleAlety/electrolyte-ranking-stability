# DOL/EC 无候选行的**根因链**（2026-10-27 精确化）——不是「缺一条通道」，而是「起点列本身就是空」

> 本轮把上一轮的结论（`DOL_EC_NO_REGISTRATION_PATH_20261027.md`）**精确化**：
> 上轮说「DOL/EC 没有登记通道」；本轮查明**更根本的一层**——
> **`strict_recovery_v1_manifest.csv` 里 DOL/EC 的 `start_1_basin` / `start_2_basin` 就是空的**，
> 所以 `recovery_candidate_rows()` 自然产不出行。**纯只读。**

## 1. 实测（三层证据）

**第一层：聚合器判定成员只读 `CANDIDATES`**
- `load_candidates()`（`build_production_ensemble_aggregator.py:599-612`）**只读** `production_ensemble_candidates.csv`（`:66`）；
  **文件缺失直接 `raise ValueError`**（`:602-603`）。
- `STRUCTURES`（`:65`）只在 `:772-776` 用来取 **`primary` 且 `status=ready`** 的行；
  **非 primary 成员的资格完全由 candidates 决定**。
⇒ **没有 candidate 行 ⇒ 该成员在判定中不存在。**

**第二层：两条候选通道的覆盖（上轮已测）**

| 通道 | 读什么 | 产出 | 覆盖 |
|---|---|---|---|
| `recovery_candidate_rows()`（`build_production_ensemble_manifest.py:411`） | `strict_recovery_v1_manifest.csv` | **11 行** | 无 DOL/EC |
| `torsion_probe_candidate_rows()`（`:454`） | glob **只匹配 `work/hpc_torsion_probe_v*`**（`:478`） | **3 行** | AN、DMC 两态 |

**第三层（本轮新查，根因）：清单里的起点列本身为空**

`outputs/physics_completion/recovery/strict_recovery_v1_manifest.csv`（**13 行**）实测：

| 态 | `start_1_basin` | `start_2_basin` |
|---|---|---|
| **`DOL\|LiM_2plus`** | **（空）** | **（空）** |
| **`EC\|LiM_2plus`** | **（空）** | **（空）** |
| `DMC\|M_plus` / `DMC\|LiM_2plus` | （空） | （空） |
| AN / DEC / DME×2 / DMSO / SL / TMP×3 | **有值** | 部分有值 |

⇒ **`recovery_candidate_rows()` 对空起点 `continue`（`:427-428`）** ⇒ 自然不产出 DOL/EC 行。
**这不是 bug，而是「该态当时确实没有登记过起点」的如实反映。**

## 2. 因此「阻塞」的准确表述

| 上轮的表述 | 本轮精确化 |
|---|---|
| 「DOL/EC 没有登记通道」 | 更准确：**DOL/EC 在 `strict_recovery_v1_manifest.csv` 里的起点列为空**，且 **P4/v2 的包不在 `hpc_torsion_probe_v*` 命名族内** ⇒ 两条通道**都无料可产** |

**⇒ 两条可能的解法（都须你批准）**：
1. **新增一条版本化通道**，直接读 P4/v2 的包（`source_kind = p4v2_screening_v1_start`）——
   **只收骨架真动的 13 条**、排除 15 条纯 Li 位移（见 `LI_ONLY_MISCLASSIFIED_AS_HEAVY_20261027.md`）；
2. 或**把 P4/v2 的合格起点写进 `strict_recovery_v1_manifest.csv` 的 `start_1_basin`**——
   但**该文件是 `build_strict_recovery_manifest.py` 的生成物**（`OUT_CSV`，`:58`），
   **手工改会被重建覆盖**；且 `:418-442` 有回填逻辑，须理解其来源才能正改。

**⇒ 方案 1 更干净**（不动既有生成物、语义显式、可版本化）；**方案 2 需要改生成器的回填逻辑**，影响面更大。

## 3. 一个**不是**解法的做法（必须写明）

**把 `torsion_probe_candidate_rows()` 的 glob 从 `hpc_torsion_probe_v*` 扩到 `hpc_xtb_screening_v2`** ——
**不可取**，因为：
- P4/v2 的 `probe_class` 是**错的** `heavy_fragment_torsion`（纯 Li 位移被误判，见
  `LI_ONLY_MISCLASSIFIED_AS_HEAVY_20261027.md`）⇒ 扩 glob 会让 **15 条纯 Li 位移**混进候选；
- 且会**改变既有包的登记语义**（`hpc_torsion_probe_v*` 这一族的历史含义），须无翻转证明。

## 4. 与用户裁定的关系（不越界）

用户裁定：「P4/v2 作为**筛选证据**登记＝是；直接作为**生产级 `computed` 成员**＝否。」
⇒ 本轮的「补候选通道」**不是**把筛选结果当生产成员，而是**把合格起点登记为待跑的生产起点**
（`status=planned`，`member_role=recovery_v1_start`），**结果仍须由真实生产计算产生**。
**这与裁定一致**——但**新增通道本身属新增登记语义，须你批准**。

## 5. 守线

- ⛔ 不改 `torsion_probe_candidate_rows()` 的 glob；
- ⛔ 不手工改 `strict_recovery_v1_manifest.csv`（生成物）；
- ⛔ 不改 `load_candidates()` 的白名单；
- ⛔ 未获授权前不提交、不建包。

## 6. 证据出处

- 聚合器：`build_production_ensemble_aggregator.py:65-66`（两表路径）、`:599-612`（`load_candidates`）、`:772-776`（`STRUCTURES` 仅取 primary）
- 通道：`build_production_ensemble_manifest.py:411`（recovery 通道）、`:427-428`（空起点 `continue`）、
  `:454`/`:478`（torsion 通道与 glob）
- 清单：`outputs/physics_completion/recovery/strict_recovery_v1_manifest.csv`（13 行，DOL/EC 起点列空）
- 生成器：`build_strict_recovery_manifest.py:58`（`OUT_CSV`）、`:374-375`（写起点列）、`:418-442`（回填逻辑）
- 相关：`DOL_EC_NO_REGISTRATION_PATH_20261027.md`、`LI_ONLY_MISCLASSIFIED_AS_HEAVY_20261027.md`、`0mvp79e8`（用户裁定）