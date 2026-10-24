# 独立挑战报告：候选预检门序与 P3 生成器（audit_gate_20261023）

日期：2026-10-23 · 审计人：wp5-blind-replay（独立于 Lead 实现）
对象：`scripts/wp_production/build_torsion_probe_package.py` 的
`validate_candidate_start` / `ring_atoms` / `ring_pucker_candidates` /
`li_coordination_candidates` / `select_candidates` / `_distance_fingerprint`，
对照 `ROUTE_DECISIONS_P2.md` 与 `P3_CANDIDATES_20261023.md` 的全部数字声明。

**可复跑探针**：`probe.py`（同目录）。退出码实测 **1**（70 检查：68 复现/通过，
2 项为**测得的实现缺陷**——见 §3）。运行方式：

```powershell
.venv\Scripts\python.exe -B -X utf8 docs\handoffs\four_state_recovery_20261023\audit_gate_20261023\probe.py
```

---

## 1. 声明 vs 实测（逐条）

### 1.1 代表几何 SHA256（ROUTE_DECISIONS_P2 §1–§4）

| 态 | 声明路径 | 声明 sha（前 16） | 实测 sha（前 16） | 判定 |
|---|---|---|---|---|
| DMC\|M_plus | `…frontier…/DMC__M_plus__primary/geom.xyz` | `5b9e93e0146333f7` | `5b9e93e0146333f7` | **符合** |
| DMC\|LiM_2plus | `…frontier…/DMC__LiM_2plus__primary/geom.xyz` | `f619c13234e5455f` | `f619c13234e5455f` | **符合** |
| DOL\|LiM_2plus | `…frontier…/DOL__LiM_2plus__c05/geom.xyz` | `f0b2558e0cf2cf9b` | **`079dd8b35c5839c0`** | **不符（见疑点 S1）** |
| EC\|LiM_2plus | `…frontier…/EC__LiM_2plus__primary/geom.xyz` | `16774e2151551a5e` | `16774e2151551a5e` | **符合** |

### 1.2 登记二面角（torsion_freedom_registry.csv）

| 声明 | 实测 | 判定 |
|---|---|---|
| DMC 两态各有 10 个登记二面角 | DMC\|M_plus=10，DMC\|LiM_2plus=10（剔除 `detail` 非 4 原子的行） | **符合** |
| DMC\|M_plus 已探 3（v1 刚性族 tors_6/7/8）→ 7 个未探 | 7 个（0-1-2-3, 0-1-2-4, 1-2-4-5, 3-2-4-5, 2-4-5-9/10/11） | **符合** |
| DOL\|LiM_2plus、EC\|LiM_2plus 无登记扭转 | 0（registry 行=`no rotatable non-ring dihedral found`） | **符合** |

### 1.3 DMC|M_plus：7 个未探二面角过修好的 gate（**两文档互相矛盾——见疑点 S2**）

同一批 7 个二面角、同一 gate、两种 dedup 模式：

| 口径 | 声明来源 | 声明 | 实测 | 判定 |
|---|---|---|---|---|
| **无** `prior_starts` | ROUTE_DECISIONS_P2 行 21「7 个全部接受，4 heavy + 3 rotor」 | 7 接受（4+3） | heavy=4 rotor=3 | **该声明在此口径下复现** |
| **带** `prior_starts`（P2 §5.3 自己冻结的规则） | P3_CANDIDATES 表「7 raw → 接受 3 / 拒 4」 | 3 接受 + 4 `equivalent_start` | heavy=2（0.2743/0.2432 Å）+ rotor=1 + 拒 4 全 `equivalent_start` | **该声明在此口径下复现** |

- 两个声明**各自可复现**，但**互相矛盾**：ROUTE_DECISIONS 行 21 的「7 个全部接受」是无去重测量，与同文件行 22 自己写的「去重后 2 个重骨架操作」以及 P3 的 3 接受不一致。
- heavy 数值 0.2743 / 0.2432 Å、以及「0-1-2-3 与 0-1-2-4 等价、3-2-4-5 与 1-2-4-5 等价、2-4-5-9/10/11 三胞胎」的等价结构**全部实测复现**。
- **判定**：P3（带去重）是符合冻结规则的口径；ROUTE_DECISIONS 行 21 的计数按文档原文读是**错误的/过时口径**，应改为「7 个原始、去重后 3 个不同操作」。

### 1.4 DMC|LiM_2plus（ROUTE_DECISIONS §2）

| 声明 | 实测 | 判定 |
|---|---|---|
| 7 raw → 接受 1（0-1-2-3，heavy 0.4874 Å） | 接受 1，heavy=0.4874 | **符合** |
| 拒 6 = 1×equivalent + 5×li_coordination_changed | 1×`equivalent_start`（0-1-2-4）+ 5×`li_coordination_changed`（1-2-4-5, 3-2-4-5, 2-4-5-9/10/11） | **符合** |
| 声明式 `declared_li_change=True` 把 5 个 li 拒收翻转为接受 | 5/5 翻转为 `ok_li_coordination_change` | **符合** |
| 声明后 heavy：`1/3-2-4-5`=0.4667、`2-4-5-9/10/11`=1.7274 | 未逐一复算（见「未覆盖」） | 未覆盖 |

### 1.5 P3 表格逐格（P3_CANDIDATES_20261023.md §1 + JSON）

| 态 | 组 | 声明 raw/acc/ref | 实测（JSON 重读+生成器重跑） | 判定 |
|---|---|---|---|---|
| DMC\|M_plus | 1 | 7/3/4 | 7/3/4（3 接受=0.2743+0.2432+rotor 0.0000；拒 4 全等价） | **符合** |
| DMC\|M_plus | 2 | 0/0/0（无环无 Li） | 0/0/0 | **符合** |
| DMC\|LiM_2plus | 1 | 7/1/6 | 7/1/6，拒=1 等价+5 li | **符合** |
| DMC\|LiM_2plus | 2 | 6/3/3 | 6/3/3（toward_3 × 0.15/0.30/0.45；拒 3 全等价） | **符合** |
| DOL\|LiM_2plus | 1 | 0/0/0 | 0/0/0 | **符合** |
| DOL\|LiM_2plus | 2 | 30/9/21 | 30/9/21（pucker 6 + Li 3；拒 12 全 `ring_broken`） | **符合** |
| EC\|LiM_2plus | 1 | 0/0/0 | 0/0/0 | **符合** |
| EC\|LiM_2plus | 2 | 30/9/21 | 30/9/21 | **符合** |

### 1.6 环原子集（P3 声明 vs 真实几何重算）

| 声明 | 实测（`ring_atoms` 对生成器实际读取的几何） | 判定 |
|---|---|---|
| DOL 五元环 `[0,1,2,3,4]` | `[[0,1,2,3,4]]` | **符合** |
| EC 五元环 `[0,1,2,3,5]` | `[[0,1,2,3,5]]` | **符合** |
| DMC 两态无环 | `[]` | **符合** |

### 1.7 pucker heavy 位移范围

| 声明 | 实测（JSON 6 条记录） | 判定 |
|---|---|---|
| DOL 0.0375–0.0771 | 0.0375/0.0478/0.0478/0.0490/0.0672/0.0771（min/max 精确命中） | **符合** |
| EC 0.0199–0.0549 | 0.0199/0.0210/0.0232/0.0252/0.0536/0.0549 | **符合** |

### 1.8 拒收原因分布

| 声明 | 实测 | 判定 |
|---|---|---|
| DMC\|LiM_2plus 组1 = 1×equivalent + 5×li_coordination_changed | 精确一致 | **符合** |
| DOL/EC 组2 = 12 条过大振幅全 `ring_broken` | 精确一致（且每条拒收带 `lost_bonds`/pair-change 证据，非静默丢弃） | **符合** |

---

## 2. 门序攻击（14 项，全部实测）

| # | 攻击 | 结果 | 判定 |
|---|---|---|---|
| 1 | 理想乙烷 120° 甲基旋转（真对称操作） | `equivalent_start`（拒收） | **正确拒收** |
| 2 | 一个 H 移 100 Å（历史缺陷复现） | `ring_broken`（C-H 键消失），**绝不再** `ok_methyl_rotor` | **正确拒收** |
| 3 | 整体刚体旋转 37.5° | `rigid_transformation` | **正确拒收** |
| 4 | 刚体旋转 90° + 平移 (10,-4,2) | `rigid_transformation` | **正确拒收** |
| 5 | 五元环拉断一根键（+3 Å） | `ring_broken` | **正确拒收** |
| 6 | C=O 伪扭转（轴在 adjacency、不在单键集） | `not_a_single_bond_rotor` | **正确拒收** |
| 7 | 声明轴但整体不传 registry | `missing_single_bond_registry` | **正确拒收** |
| 8 | Li 首壳变化（未声明） | `li_coordination_changed` | **正确拒收** |
| 9 | Li 首壳变化（声明式） | `ok_li_coordination_change`，`probe_class=li_coordination_change`，壳层前后写入 detail | **正确接受且单独分类** |
| 10 | 合法环褶皱（+0.25 Å 出平面） | `ok_heavy_fragment`，heavy=0.0204>1e-5 | **正确接受** |
| 11 | 阈值带：H 位移 2e-6/6e-6 → `rigid_transformation`；2e-5 → 过刚性门（此几何下落 `equivalent_start`）；1.01e-5 → 仍 `rigid`（阈值作用在 **max pair-distance change** 上，不是位移幅度——语义正确，见注） | 阈值行为与实现声明一致 | **符合** |
| 12 | 字节相同的重复候选 + prior_starts | `equivalent_start`，`against=prior_start_0` | **正确拒收** |
| 13 | 畸形输入 4 类（2D 形状/NaN/短一行/邻接短） | 全部 `malformed_input`，**无一 raise** | **正确拒收** |
| 14 | 3 个几何全同候选过选择器 | 接受 1 拒 2（全 `equivalent_start`）——prior_starts 去重真实生效 | **正确** |

**注（#11）**：`min_pair_change_a=1e-5` 的比较对象是「全原子对距离矩阵的最大变化」。把一个 H 沿 x 平移 δ 时，远处原子对的距离变化 ≈ δ·cos(θ) 可小于 δ，所以 1.01e-5 的**位移**不一定产生 1.01e-5 的**最大对距变化**。这不是缺陷——但值得在文档里写清楚「阈值在 pair-distance 空间」，否则读者会拿位移幅度对表。

**`_distance_fingerprint`**：刚体旋转+平移后哈希不变（实测一致）；0.5 Å 形变后哈希改变。**分辨率实测为 1e-4**（`%.4f` 截断）：任何全部对距变化 <1e-4 Å 的形变与原结构同哈希。门自己的等价判据是 1e-4 RMSD（`equivalent_start`），指纹只用于登记/对账，不用于门内判等，故此分辨率不构成放行漏洞——但**跨版本对账时**两个差 <1e-4 的不同几何会判为同指纹（登记层限制，见 §3-D3）。

---

## 3. 测得的缺陷与疑点

### D1（实现缺陷，探针 FAIL 之一）：`select_candidates(max_keep=…)` 静默丢弃未评估候选
`select_candidates` 在达到 `max_keep` 时直接 `break`，剩余候选**既不进 accepted 也不进 refused**。实测：6 个原始候选、`max_keep=1` → accepted=1、refused=0，**5 个无影无踪**。违反项目自己的「refusal 也是历史，不得静默丢弃」纪律。当前 P4 流程未传 `max_keep`（=None），**不影响已发布产物**；但对任何未来调用者是潜在审计断链。修法：break 前把剩余候选记为 `reason="capped_by_max_keep"` 的 refused（或单独 `deferred` 列表）。

### D2（实现缺陷，探针 FAIL 之二）：`rotated_bond` 负索引不做范围检查
门的范围检查只查 `axis[1] >= len(symbols)` 与 `axis[0]==axis[1]`，**不查负数**。实测 `rotated_bond=(-1,1)`：无 registry → `missing_single_bond_registry`；有 registry → `not_a_single_bond_rotor`。两分支都 fail-closed（负索引不会匹配任何真 registry），**无科学后果**；但 `malformed_input` 分支对负索引不可达，与文档「malformed_input = shape/索引不可用」的语义不符。修法一行：`axis[0] < 0 or axis[1] >= len(symbols)`。

### S1（疑点，文档层）：ROUTE_DECISIONS 对 DOL 代表几何的「路径+sha」配对自相矛盾
行 43 写「代表几何 `DOL__LiM_2plus__c05/geom.xyz`（frontier 树），sha256 `f0b2558e…`」。实测该文件 sha=`079dd8b3…`；`f0b2558e…` 属于**另一个文件**——`work/hpc_production_ensemble_r1_036-053/tasks/DOL/LiM_2plus__c05/geom.xyz`，而后者才是生成器 resolver（`_state_geometry`）实际读取、且与 P3 JSON `source_geometry_sha256` 一致的源。**判定**：数字本身没造假（两文件都实测在盘、sha 与 P3 JSON 一致），但行 43 的**路径引用错了树**。frontier 树的 `geom.xyz` 是 fetch 回收后的几何（079dd8b3 = 该任务 `final_geom`，行 44 自己也是这么写的），ensemble 包里才是 P3 用的起点几何。建议把行 43 的路径改为 ensemble 包路径，或注明「sha 指起点几何（ensemble 包），路径写的是同任务 frontier 现场」。

### S2（疑点，文档层）：ROUTE_DECISIONS 行 21 与 P3 同态计数互相矛盾
见 §1.3：行 21「7 个全部接受（4 heavy+3 rotor）」是无 `prior_starts` 的测量；P3 按同文件 §5.3 冻结的 dedup 规则报 3 接受。两套数字都实测可复现，但文档间不自洽。P3 是正确口径；行 21 应改写或加注。

### D3（登记层限制，非缺陷）：距离指纹分辨率 1e-4 Å
`_distance_fingerprint` 用 `%.4f`——全部对距变化 <1e-4 Å 的两个不同几何共享同一指纹。P3 用它做「结果指纹」登记与 P4 seed 复原对账：实测 21/21 接受记录 seed 复原唯一且指纹一致，当前无实际碰撞。**未覆盖**：构造指纹碰撞下的 P4 `--check` 行为。

---

## 4. 「永不触发」判据清查（逐分支喂触发输入）

| 分支 | 触发方式 | 可触发？ |
|---|---|---|
| `malformed_input` | 2D 形状 / NaN / 短行 / 坏邻接 / 坏 rotated_bond(oob/self) | **是**（负索引除外，见 D2） |
| `missing_single_bond_registry` | 声明轴、不传 registry | **是** |
| `not_a_single_bond_rotor` | C=O 轴（adjacency 有、单键集无） | **是** |
| `rigid_transformation` | 全等/整体刚体/微小位移 | **是** |
| `ring_broken` | H 100 Å / 拉断环键 / 过大 pucker | **是** |
| `collision_or_new_bond` | 把 H 摆到同碳兄弟 H 旁 0.70 Å（保自身键、增 H–H 边） | **是**（首版攻击构造错误地触发 ring_broken；换构造后触发） |
| `li_coordination_changed` | O 推出 Li 2.6 Å 首壳、未声明 | **是** |
| `mapping_unresolved` | 喂形状不一致的 prior（等效映射 ValueError → fail-closed） | **是** |
| `equivalent_start` | 120° 对称旋转 / 字节重复 / 等价二面角 | **是** |
| `ok_methyl_rotor` / `ok_heavy_fragment` / `ok_li_coordination_change` | 合法 60° / 环褶皱 / 声明式 Li | **是** |

**无「永不触发」的死判据**——12 个分支全部实测可达。（注意：这需要 `_covalent_only` 的 Li 边排除补丁在位；P2 §5.1 记录的旧版「li 变化永远先报 ring_broken」缺陷，当前代码已修——实测 `li_coordination_changed` 可独立触发。）

---

## 5. 生成器攻击结论

| 项 | 结果 |
|---|---|
| `ring_pucker_candidates` 在无环分子（DMC\|M_plus） | 返回 `[]`，不崩（实测 0 候选） |
| `li_coordination_candidates` 在无 Li 态（DMC\|M_plus） | 返回 `[]`，不崩（实测 0 候选） |
| 过大振幅（≥0.60）被「拒」而非「丢」 | 12/12 全部进 refused、`reason=ring_broken`、每条带 lost_bonds/pair-change 证据 |
| 原始数量 | DOL：pucker 24（3 模式×8 振幅）+ Li 6（2 方向×3 偏移）=30，与 P3 raw=30 一致 |
| 生成确定性 | 同输入两次生成 byte-identical（SVD 法向符号规范化实测生效） |
| P4 seed 复原 | 21/21 接受记录 `_p4_candidate_from_seed` 复原唯一、指纹一致（`--check` 的依赖成立） |

---

## 6. 未覆盖范围

1. **声明后 heavy 数值**：ROUTE_DECISIONS §2 声明的 `1/3-2-4-5`=0.4667、`2-4-5-9/10/11`=1.7274（声明式 Li 探针翻转后的 heavy 变化）未逐一复算——本审计只验证了 5/5 翻转接受与分类，没有核对这两个具体数字。
2. **指纹碰撞下的 P4 `--check` 行为**：只验证了 21/21 正常复原；未构造 <1e-4 对距差异的碰撞对去打 `_p4_candidate_from_seed`/`check_p4_screening_package` 的健壮性。
3. **`_build_state` / `build_repair_package` / `write_p4_screening_package` 的写盘路径**：本审计是只读挑战，未对包生成器的落盘产物（inputs.sha256、sbatch 模板、manifest 分批）做端到端复算；已有仓库测试覆盖调用链（spy 证明 gate 被调用），此处未重复。
4. **`equivalent_start` 的 100000 节点搜索上限**：`mapping_unresolved` 用「喂形状坏的 prior」触发；未构造真正因搜索超限触发的合法几何（需要大规模对称分子，超出本审计输入清单）。
5. **`ring_atoms(ring_max=7)` 对 >7 元环**：只用 DOL/EC 五元环与 DMC 无环验证；七元环边界（恰好 7/8 元）未测。
6. **`_repair_member` 的 v2 realfragment 包**：任务未点名 `work/hpc_torsion_probe_v2_realfragment` 为输入，相关历史成员（AN\|M_plus 等）未复核。
7. **D1 缺陷的下游影响面**：只确认 P4 现流程不传 max_keep；未审计仓库里是否存在其它 `select_candidates(max_keep=…)` 调用点。

## 7. 需要用户/Lead 裁决的问题

1. **D1**：`max_keep` 静默丢弃是修（记为 capped refused/deferred）还是先登记为已知限制？P3/P4 未触发，属低危。
2. **D2**：负索引范围检查一行修复，随下轮 P0–P9 代码面顺带修，还是单开？
3. **S1/S2**：两处文档（ROUTE_DECISIONS 行 21、行 43）由 Lead 统一改还是授权本审计出勘误附页？（本审计写范围禁止改既有文件。）
