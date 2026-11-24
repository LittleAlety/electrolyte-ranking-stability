# SCIENTIFIC_HOLD 解锁规格（A-1/A-2/A-3）—— 待用户裁决后执行

> 状态：**未执行**。依派单「Lead 仅在 A 未发 SCIENTIFIC_HOLD 时实施」，A 已发 HOLD ⇒ 本文件只是**待批规格**。
> 依据：`work/exp_line20261031/SCIENCE_ACCEPTABILITY_AUDIT_20261031.md`（A，已审议批准）+ 我的独立复核。
> 基线 HEAD `80933e54f8a605d9dd6d033c0f2861e33b591c13`；正式记录 **45 accepted / 3 limited（分母 48）** 不变。

## 0. 为什么是"零计算"解锁

A 的判定：阻塞**不是**科学身份/几何/取证，而是**验收链的登记与命名**。⇒ 解锁全部落在"让这条腿被覆盖审看见、且不被排除集吃掉"，**不需要任何新计算、不新增额度、不动 64 CH 授权**。

## 1. A-1：让导入器能发现这个包（0 CH，本线写入面）

**实测三个 glob 都不匹配现路径**（`import_ensemble_structures.py`）：`PACKAGES=("work/hpc_production_ensemble_r*_*","work/hpc_production_ensemble_strict_recovery_v1*")`（`:154-155`）、`RECOVERY_PACKAGE_GLOB="work/hpc_production_ensemble_strict_recovery_v1*"`（`:158`）、`TORSION_PACKAGE_GLOB="work/hpc_torsion_probe_v*"`（`:163`）。
**唯一免改代码的通道**：`iter_packages()` 第三条通道（`:1279-1285`）——`REPO.glob("work/hpc_*")` 下任何 **manifest 含非空 `members`** 的包会被当作系综包（活证：`work/hpc_ec_strict_convergence_v1`）。

**动作（两步，均在 `work/` 层，不碰 tracked）**：
1. 包从 `work/exp_line_20261031/hpc_dmc_lim2plus_vtscf16_v1/` 移到 **`work/hpc_dmc_lim2plus_vtscf16_v1/`**（`work/hpc_*` 一层）；
2. manifest 增加非空 `members` 数组（形状照抄活例，见 §2 的字段表）。

**注意**：移动后 `PACKAGE_SHA256SUMS` 与包内相对路径不变（清单是相对路径），但**必须在移动后重跑** `sha256sum -c` 复验 14/14。

## 2. A-2：候选登记 + seed 命名（0 CH，**tracked 文件，Lead 写**）

**三条硬约束（每条都有实测出处）**：

| # | 约束 | 出处 | 违反后果 |
|---|---|---|---|
| 1 | `member_role` 必须以 `recovery_v1` 开头 | `build_coverage_reviews.py:61` `RECOVERY_ROLE_PREFIX="recovery_v1"`；`:266-272` 用它过滤 `members` | 不进 `members` ⇒ `R3` 永不成立 ⇒ 永远 `unresolved_qc` |
| 2 | **入账 `status` 必须写 `computed`，不能写 `ready`** | `:176-177` `if any(r.get("status") in ("pending","ready") ...): return "pending"` | 写成 `ready` ⇒ route=`pending` ⇒ **同样不是 resolved**（我本轮独立复核：`primary` 行正是 `ready`，只因角色是 `primary` 才不进 `members`） |
| 3 | **seed 绝不能复用 `tors_7_0_1_2`** | `_rejected_probe_members()` `:143-151`：`replaces_cancelled_job=3747724` 触发，把 `tasks/<name>/<slot>__<seed>` 转成**整键** `DMC\|LiM_2plus\|tors_7_0_1_2` 加入排除集 | 该键被 `:266-272` 的 `member_key not in rejected` 整键剔除 ⇒ **静默失效**，新腿永远不进 `members` |

**候选表新增行**（列序实测自 `production_ensemble_candidates.csv` 表头）：

```
DMC,C01,DMC,LiM_2plus,recovery_v1_start,p5li_vtscf16,vtscf_strict_opt_v1_start,work/hpc_frontier_localization_v1/tasks/DMC__LiM_2plus__primary/geom.xyz,f619c13234e5455fe0651b7444728e423c1df9975e456c4af0692ce901f8d505,,,2,2,planned,
```

**manifest 的 `members` 条目**（字段形状实测自 `work/hpc_ec_strict_convergence_v1/manifest.json`）：

```json
{
  "state_key": "DMC|LiM_2plus", "candidate_id": "dmc_lim2plus_vtscf16_p5li",
  "leaf": "LiM_2plus__opt_p5li", "kind": "vtscf_strict_opt", "label": "vtscf16_strict",
  "charge": 2, "multiplicity": 2, "spin": 1,
  "geometry_sha256": "f619c13234e5455fe0651b7444728e423c1df9975e456c4af0692ce901f8d505",
  "source_geometry": "work/hpc_frontier_localization_v1/tasks/DMC__LiM_2plus__primary/geom.xyz",
  "source_geometry_sha256": "f619c13234e5455fe0651b7444728e423c1df9975e456c4af0692ce901f8d505",
  "source_kind": "vtscf_strict_opt_v1_start", "member_role": "recovery_v1_start",
  "status": "ACTIVE", "name": "DMC", "slot": "LiM_2plus", "seed": "p5li_vtscf16",
  "mol_id": "C01", "member_key": "DMC|LiM_2plus|p5li_vtscf16"
}
```

**seed 取名说明（诚实标注，不蹭通道）**：`p5li_vtscf16` 不以 `tors_` 开头、`source_kind` 也不写 `p4v2_screening_v1_start` ⇒ 它**不会**进入 `_probe_starts`（`:104-105`）。这是有意的：不冒充旧扭转探针家族（用户 2026-10-27 裁定），代价是它**不提供**搜索范围证据（见 A-3）。

## 3. A-3：R7 证据强度取向（**口径裁决，0 CH**）

| 选项 | 含义 | 代价 | 风险 |
|---|---|---|---|
| **R7-现状** | 接受"`starts` 由旧 `tors_7_0_1_2` 提供 + `search_outcome=no_new_minimum_found`"作为搜索范围证据 | 0 | 该 seed 的来源是被**取消并替换**的探针（`replaces_cancelled_job=3747724`）；虽被排除集剔除出 `members`，但它仍经 `_probe_starts` 提供 `starts` ⇒ **用被取消的探针给新腿背书**，报告里必须写明 |
| **R7-新起点** | 要求覆盖审以**本次新起点**命名搜索范围 ⇒ seed 须满足 `:104-105`（以 `tors_` 开头 **或** `source_kind="p4v2_screening_v1_start"`） | 0 | 与"禁止改名冒充扭转家族"直接冲突；若走 `p4v2_screening_v1_start` 则须证明它**真是** P4/v2 派生起点（本包不是）⇒ **技术上不可诚实地满足** |

⇒ **我的建议**：取 **R7-现状**，但在预注册与最终报告里**显式声明**："本腿不新增任何搜索范围信息；`registered_starts` 来自既有 `tors_7_0_1_2` 候选行，其来源为被取消并替换的探针（job 3747724）；本腿的科学价值是**严格数值协议下对已登记单一极小的独立复现**。"——这正是 A §6-B6 钉死的表述，且不许写成"独立构象搜索通过"。

## 4. 起点选择（A §3.3 的反直觉结论，必须遵守）

| 起点 | 与成员字节 | 第 1 轮两项梯度 | 结论 |
|---|---|---|---|
| `f619c132…`（现冻结） | **与 primary 末几何同字节** | 3.39× / 2.85× **超阈** | **保留**：首轮不可能判收敛 ⇒ `Energy change` 必打印；且它是"独立复现已知极小"路线的正确对象 |
| `0458134d…` | 与 primary 不同字节（是 `tors_7` att5 末几何） | **0.28× / 0.28× PASS** | **禁止**：首轮即收敛风险**升高**，且它本身就是已登记成员的末几何 |
| `ea672e7a…` | 不同字节、身份三行齐 | 未测（A 未做该项测定） | 仅当改判"要真正独立起点"时用；距极小 **0.6874 Å**、`MaxIter 50` 与本态 `max_cycles_exhausted` 失败谱系冲突 ⇒ 超时/轮数风险最高 |

⇒ **不要按"不同字节＝更安全"选起点**（A 的原话：这条会加重 EC 式问题）。

## 5. 若获放行，执行顺序（仍受 C 门禁约束）

1. A-1 移包 + 加 `members` → 重跑 `sha256sum -c`（14/14）→ 用 `iter_packages()` 实测确认本包**被发现**；
2. A-2 候选表加行（tracked，Lead 写）→ 用 `build_coverage_reviews` 的 `_probe_starts`/`members` 逻辑实测确认**本腿会进 `members`**、且 `member_key` **不在**排除集；
3. **重跑 A 的科学门**（新的只读审计，或 A 复检）确认判定变为"能形成正式证据"；
4. 之后才轮到 t3（rev5 交付链）/t4（16 核 profile）→ C 的 GO/NO_GO → 提交一次。

**在此之前，一律不动生产面、不提交、不改任何标签。**

## 6. 红线自查

本文件仅写在 `work/exp_line20261031/`（本线写入面）；未改 `scripts/`、`outputs/`、账本、接收器、提交包；未提交作业；未 git 写操作；正式记录仍 **45/48 历史协议**。