# 第二轮搜索预注册稿（EMC|M_plus 已执行并排除；剩余 5 态待用户裁决）

> 生成器 `build_second_search_preregistration.py`（`--check` 完全只读）。
> 方案原文：「如决定新一轮搜索，先版本化预注册新池、成本上限和停止规则，再计算；不回填旧池。」

## 本批恢复不了的 4 态（按限制原因分类）

| 态 | 限制原因 | 首轮证据 |
|---|---|---|
| DMC\|LiM_2plus | `rescue_budget_exhausted` | round-3 motif 搜索：9 候选、保留 1、**新独立盆地 0** |
| DMC\|M_plus | `rescue_budget_exhausted` | 64 个独立 GFN2 阳离子起点：**新极小 0 个**（全部塌缩到已有极小，RMSD 0.0000） |
| DOL\|LiM_2plus | `rescue_budget_exhausted` | round-3 motif 搜索：6 候选、保留 2、**新独立盆地 0** |
| EC\|LiM_2plus | `rescue_budget_exhausted` | round-3 motif 搜索：9 候选、保留 1、**新独立盆地 0** |

## 已执行的第二轮：EMC|M_plus（结论：**换方法无效，已排除**）

用户 2026-10-21 裁决只搜 `EMC|M_plus` 后已实测执行：GFN2-xTB + **ALPB(乙腈)**、**256** 个 ETKDGv3 起点（首轮 64）、seed 20261022，256/256 全部收敛。

| 第二轮盆地 | rel (kcal/mol) | 与已有极小 RMSD | 判定 |
|---|---|---|---|
| v2_c042 | 0.000 | 0.0102 Å | 同一盆地 |
| v2_c117 | 2.046 | 0.1181 Å | 同一盆地 |

**真正新盆地 = 0** → 停止规则触发 `search_method_exhausted`。

**更关键的是：这个态本来就不缺盆地**——它的 `limitation_reason` 是 `species_drift_unrecoverable`（`n_unique=2`），结构表显示 `EMC|M_plus|4` 是 `candidate_bond_graph_changed`：该盆地在生产级优化时**键图改变、重排成别的物种**。冻结协议对身份改变明令「直接判失败、不重试」，所以换任何搜索方法都补不上它。

**后果（2026-10-23 更新，此前口径已作废）**：早先由此断言「WP3 的 R4 阶梯里那 2 对（EMC vs GBL、EMC vs SL）**永久停在 limited**、R4 上限就是 8/12 computed」。**该断言已过时**：`EMC|M_plus` 后来经**覆盖复核 `qualified_all`**（计入 primary 的 ready 行）放行（系综 39→41），R4 那 2 对随即可以计算。当前 `closure/flip_persistence.csv` 实测为 **6 个 rung × 2 对 = 12 格**：**10 `computed` + 2 `computed_screen_only`**，其中 **`R4` 两对均为 `computed`**、`R4_screen` 仅筛选级。**漂移结论本身的适用范围也随之收窄**：它只说明「该*失败尝试*的起点会重排成别的物种、重试无法恢复身份」，**不等于**「该态没有别的盆地」——后者要由覆盖复核判定。

## 剩余 5 态：候选方法变更（每项都需单独版本化登记，组合由用户裁决）

### 阳离子单极小态（AN/DMC/EMC 的 M_plus）

| 变更 | 具体做法 |
|---|---|
| larger conformational ensemble | 每态 256 起点（当前 64），同一 ETKDGv3 但更大样本 |
| different embedding family | ETKDGv2 / Omega / 系统扭转扫描（当前 ETKDGv3） |
| implicit-solvent screening | GFN2 + ALPB(acetonitrile) 而非气相（当前气相） |
| higher screening level | r2SCAN-3c 筛选（当前 GFN2），代价高约一个量级 |

### 配位态（DMC/DOL/EC 的 LiM_2plus）

| 变更 | 具体做法 |
|---|---|
| wider motif enumeration | 增加给体组合与 Li 距离/角度网格（当前 1 父体 × 枚举规则） |
| multiple neutral parents | 对每个中性 M 盆地都做 motif 放置，而非单一父体 |
| explicit-solvent motif | 在显式乙腈壳层下构造配位起点 |
| MD-derived snapshots | 短程 MD 采样的配位构型作为起点 |

## 预注册必须冻结的四件事（缺一不可）

1. **方法变更的唯一定义**——写明改了哪一项（如 64→256 起点）、其余保持不变；
2. **成本上限**——搜索级（GFN2，本机，便宜）+ 生产级（每条新盆地一条 ORCA 腿，实测恢复腿均值 3–12 core-hours）；
3. **停止条件**——每态新起点 ≤2；两次都无新极小 → 登记 `search_method_exhausted`，该态在冻结方法族下永久 limited；
4. **不回填旧池**——新盆地进入新的版本化池，旧池记录保持原状。

## 成本的量级参考（不是承诺）

* 搜索级：本机 GFN2，每态 256 起点约与首轮 64 起点同量级（分钟到半小时）；
* 生产级：只在**找到新盆地时**才提交，按每态 ≤2 腿计；
* 若 6 态都找到 2 个新盆地：12 腿 × ~6 core-hours ≈ **70 core-hours**；
* 这批的失败模式是「搜索无果」，所以最可能的结果是**只花搜索级成本**。

**本稿不选方法、不算具体预算、不启动任何计算。已执行的部分只有 EMC|M_plus（用户授权），其余 5 态的选定由用户裁决。**
