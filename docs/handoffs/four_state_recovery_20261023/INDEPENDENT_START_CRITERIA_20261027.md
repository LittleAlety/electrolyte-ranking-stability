# 「独立起点」判据的实测核验（2026-10-27）——DOL/EC 恢复链自洽性

> 用户裁定第 2 步要求：「从**可追溯、经过非刚体与身份预检的独立起点**出发」，且
> 「**单纯重复提交已知极小的相同几何，不能冒充独立搜索**」。
> 本文**逐条核验**这两条判据是否真的成立。**纯只读、零计算。**

## 1. 判据一：起点**不是同一几何**（不能是已知极小的拷贝）

| 态 | 候选起点 | 起点 `geom.xyz` sha256 | vs 全部已登记极小 |
|---|---|---|---|
| `DOL\|LiM_2plus` | `p4_02_ring_pucker_twist` | `60436e57ebde…` | 与 `C09#m2`/`C09#m1`/`C09\|LiM_plus#m1` **均不同几何** |
| `EC\|LiM_2plus` | `p4_02_ring_pucker_twist` | `3d0d5f0efc3d…` | 与 `C04#m1`/`C04\|LiM_plus#m1` **均不同几何** |

⇒ **✅ 不是「重复提交相同几何」**（sha256 逐个比对为 False）。

## 2. 判据二：起点**经过非刚体与身份预检**（权威门）

两个起点均通过 `validate_candidate_start`（唯一候选门）。**但必须用正确的口径**：

| 口径 | DOL 起点 | EC 起点 |
|---|---|---|
| 含 Li（`:322` `s != "H"`） | 0.1675* | 0.2098* |
| **纯骨架（排除 H 与 Li）** | **0.0771** | **0.0549** |
| **vs 已登记极小**（纯骨架 RMSD） | **0.1912 Å** | **0.0996 Å** |

\* 上表带星号的数字**是错的口径**（`LI_ONLY_MISCLASSIFIED_AS_HEAVY_20261027.md`），此处并列以保持可追溯。

⇒ **✅ 骨架确实动过**（0.055–0.077 Å > `1e-5` 阈值），且**相对已登记极小差 0.10–0.19 Å**。

## 3. 判据三（**关键**）：起点与已登记极小的关系决定**能走哪条 route**

用**生产聚合器的真实去重原语**（`bond_adjacency` + `find_topology_mappings` + `kabsch_rmsd`，
阈值 `DUP_RMSD_A = 0.35`）复算起点与已登记极小：

| 态 | 已登记极小 | best heavy RMSD | 去重判定 |
|---|---|---|---|
| `DOL\|LiM_2plus` | `C09#m2` | **0.0962** | **duplicate（< 0.35）** |
| `DOL\|LiM_2plus` | `C09#m1` | 0.1016 | duplicate |
| `EC\|LiM_2plus` | `C04#m1` | **0.1224** | **duplicate** |
| `EC\|LiM_2plus` | `C04\|LiM_plus#m1` | 0.1495 | duplicate |

## 4. ⇒ **这条链与用户裁定精确吻合**（这是本轮的结论）

用户原话要旨：「**DOL/EC 不必强行找到第二个极小才能恢复，但必须证明独立起点在生产方法下通过了验证。**」

按 `coverage_route` 的判据链复述（`:175-220`）：

```
生产腿跑完 → 该成员 status=computed
   ↓ dedup 判为 "known"（复现已登记极小）      ← 判据三实测：会是 duplicate
   ↓ production_evidence 完整（imaginary_modes + final_geometry_sha256 + log_sha256 非空）
   ↓ _search_scope_documented（registered_starts 非空 且 search_outcome 有文档）
   ⇒ route = single_basin_verified  ⇒ verdict = resolved  ⇒ acceptance = accepted
```

**⇒ 「复现已登记极小」正是 `single_basin_verified` 的**预期输入**，不是失败。**
（若得**新**极小 ⇒ 走 `multi_basin_coverage`，同样 `resolved`；两条路都通向 `accepted`。）

**⚠ 但三个条件必须同时满足**，缺一即退化为 `known_basin_reproduction`（`verdict=unresolved` ⇒ 仍 `limited`）：
1. **`production_evidence` 完整**——要求 `imaginary_modes`、`final_geometry_sha256`、`log_sha256` **全部非空**
   （用户已提示：「`imaginary_modes` 与两个哈希『非空』**本身不足以**证明生产证据合格」⇒ 还要过**冻结五阈值 + 身份 QC**）；
2. **`search_scope_documented`**——`registered_starts` 非空 **且** `search_outcome` ∈
   {`new_minima_found`, `no_new_minimum_found`, `unused_pool_basin_no_search_needed`}（`:150-160`）；
3. **该成员进 `latest_members`**——即被选入复核的生产恢复成员（这是 `search_exhausted` 与
   `single_basin_verified` 的分界线，见 `0mvp79e3`）。

## 5. 尚存的真实不确定项（不隐瞒）

| # | 项 | 状态 |
|---|---|---|
| 1 | **起点选择口径**：`p4_02_ring_pucker_twist` 是**P4 判定曾记「塌缩回源」**的那一类 | 骨架确实动过 0.055–0.077 Å，但幅度小；**是否够「独立」需你裁定** |
| 2 | **搜索范围文档**：`registered_starts` 与 `search_outcome` 的值需在**登记批**里明确写出 | 见下 |
| 3 | **生产批成本**：2 腿、实测预期 ≈36.8 CH、在飞预留 192 CH（均 < 512） | 待批 |

## 6. 证据出处

- 判据一：`sha256(geom.xyz)` vs `sha256(kept motif)` 逐个比对
- 判据二/三：`work/_regate_skeleton_only.py`、生产聚合器 `bond_adjacency`/`find_topology_mappings`/`kabsch_rmsd`
  （`DUP_RMSD_A = 0.35`）
- route 判据链：`build_coverage_reviews.py:150-160`（搜索范围）、`:175-220`（路由）
- 相关：`LI_ONLY_MISCLASSIFIED_AS_HEAVY_20261027.md`、`FOUR_STATE_ACCEPTANCE_PATH_20261027.md`、`0mvp79e3`