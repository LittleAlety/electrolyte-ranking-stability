# 「独立起点」判据的实测核验（2026-10-27）——DOL/EC 恢复链自洽性

> 用户裁定第 2 步要求：「从**可追溯、经过非刚体与身份预检的独立起点**出发」，且
> 「**单纯重复提交已知极小的相同几何，不能冒充独立搜索**」。
> 本文**逐条核验**这两条判据是否真的成立。**纯只读、零计算。**

## 1. 判据一：起点**不是同一几何**（不能是已知极小的拷贝）

| 态 | 候选起点 | 起点 `geom.xyz` sha256 | vs 全部已登记极小 |
|---|---|---|---|
| `DOL\|LiM_2plus` | `p4_02_ring_pucker_twist` | `60436e57ebde…` | 与 `C09#m2`/`C09#m1`/`C09\|LiM_plus#m1` **字节均不同** |
| `EC\|LiM_2plus` | `p4_02_ring_pucker_twist` | `3d0d5f0efc3d…` | 与 `C04#m1`/`C04\|LiM_plus#m1` **字节均不同** |

⇒ **✅ 证明力（已按用户 2026-10-27 裁定收窄）**：sha256 不同**只能证明文件字节不同**，
即**不构成「重复提交相同几何（同一份文件）」**；**它不能单独证明「几何独立」**——
几何独立要看下面的骨架对距证据，并最终由 **DFT 优化后的去重**判定。

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

| 态 | 已登记极小 | best heavy RMSD | 起点-层面的 RMSD 观察 |
|---|---|---|---|
| `DOL\|LiM_2plus` | `C09#m2` | **0.0962** | < 0.35（仅 RMSD 条件） |
| `DOL\|LiM_2plus` | `C09#m1` | 0.1016 | < 0.35 |
| `EC\|LiM_2plus` | `C04#m1` | **0.1224** | < 0.35 |
| `EC\|LiM_2plus` | `C04\|LiM_plus#m1` | 0.1495 | < 0.35 |

> **⚠ 更正（用户 2026-10-27 裁定）**：本表原写「⇒ 均判 `duplicate`」——**已撤回**。
> **不能据起点 RMSD < 0.35 预先断言最终是 `duplicate`**，因为冻结去重还要求
> **同态、拓扑映射、扭转（10°）与 Li 给体一致**；且**最终结论必须针对 DFT 优化后的结构产生**，
> 不是针对起点几何。本表只是**起点层面的 RMSD 观察**，供选点参考，**不预判去重结果**。

## 4. ⇒ **这条链与用户裁定精确吻合**（这是本轮的结论）

用户原话要旨：「**DOL/EC 不必强行找到第二个极小才能恢复，但必须证明独立起点在生产方法下通过了验证。**」

按 `coverage_route` 的判据链复述（`:175-220`）：

```
生产腿跑完 → 该成员 status=computed
   ↓ dedup 对【DFT 优化后结构】判为 "known" 或 "new"   ← 最终由生产去重产生，不预判
   ↓ production_evidence 完整（imaginary_modes + final_geometry_sha256 + log_sha256 非空）
   ↓ _search_scope_documented（registered_starts 非空 且 search_outcome 有文档）
   ⇒ route = single_basin_verified 或 multi_basin_coverage
   ⇒ verdict = resolved ⇒ acceptance = accepted
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

## 5. 尚存项的裁定结果（用户 2026-10-27 已全部裁定）

| # | 项 | 裁定 |
|---|---|---|
| 1 | 环形变是否算独立起点 | **可以**作为本轮有限范围的、几何不同的启动点；**用原始扰动几何，不能用筛选后塌缩的末几何**；其独立性 ≠ 已证明新盆地或采样充分 |
| 2 | 搜索范围文档 | 由新登记通道按**显式 `source_kind` + 激活登记**提供（不靠改名伪装 `tors_` 前缀） |
| 3 | 生产批 | **2 腿、各首次执行一次、预留 96 CH、走 512**；墙钟 **C+D**（新增专用 4 核 / **12 h** profile + 同步版本化修订本批契约）；未使用的第二起点与救援**不自动启动** |

> **36.8 CH 只是「两倍单腿 p90」的规划估算**；**实际消耗必须按终态账单结算，不能用估值释放预留**。
> 12 h 是基于已有最长约 8 h 记录留出的**工程余量，并非完成保证**。

## 6. 证据出处

- 判据一：`sha256(geom.xyz)` vs `sha256(kept motif)` 逐个比对
- 判据二/三：`work/_regate_skeleton_only.py`、生产聚合器 `bond_adjacency`/`find_topology_mappings`/`kabsch_rmsd`
  （`DUP_RMSD_A = 0.35`）
- route 判据链：`build_coverage_reviews.py:150-160`（搜索范围）、`:175-220`（路由）
- 相关：`LI_ONLY_MISCLASSIFIED_AS_HEAVY_20261027.md`、`FOUR_STATE_ACCEPTANCE_PATH_20261027.md`、`0mvp79e3`