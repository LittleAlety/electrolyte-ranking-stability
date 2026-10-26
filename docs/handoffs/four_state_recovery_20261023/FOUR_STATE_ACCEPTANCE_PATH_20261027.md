# 四态「转 accepted」的机器路径诊断（2026-10-27）

> 触发：计划 item 9 要求「四态稳定后一次重建下游」。本轮**离线预演**这条路径，
> 问一个此前从未问过的问题：**那四个 `limited` 态在现行机器规则下，究竟需要什么条件才能变成 `accepted`？**
> 结论**推翻了此前的隐含假设**（以为「四态稳定后重建下游即可」），并**精确澄清了 H3 的技术含义**。**纯只读、零计算、不改状态。**

## 1. 唯一通道：`acceptance_decision` 只认 `verdict == "resolved"`

`build_production_ensemble_aggregator.py` 中 `accepted` **只能**由 `acceptance_decision(...)`（`:619-657`，调用点 `:923`）产生，
而它的判据是（`:642-657`）：

```
n_limited 有 *resolved* 复核 → accepted，但**仅当**复核证据通过 kept 池反作弊；
有未决工作(unresolved)      → provisional；
n_limited 且复核未 resolved → limited。
```

**实测四种 verdict 的结果**（本机只读调用该生产函数）：

| `cov.verdict` | `acceptance_status` |
|---|---|
| `resolved` | **`accepted`** |
| **`search_exhausted`** | **`limited`** ← **不产生 accepted** |
| `unresolved` | `limited` |
| `pending` | `limited` |

（并复核：全文件中 `acceptance_status` 的赋值只有这一处 ⇒ **不存在第二条通道**。）

## 2. 四态当前的复核实况（`outputs/physics_completion/recovery/coverage_reviews.csv`，14 行）

| 分子 | 态 | `verdict` | `route` |
|---|---|---|---|
| **DMC** | `M_plus` | **`unresolved`** | `unresolved_qc` |
| **DMC** | `LiM_2plus` | **`unresolved`** | `unresolved_qc` |
| **DOL** | `LiM_2plus` | **`search_exhausted`** | `search_exhausted` |
| **EC** | `LiM_2plus` | **`search_exhausted`** | `search_exhausted` |

其余 10 行（`AN`/`DEC`/`DME`/`DMSO`/`EMC`/`SL`/`TMP` 等）均为 `resolved` —— 这就是系综目前 **44/48** 的构成。

## 3. ⇒ 三条硬结论

1. **DOL/EC（`search_exhausted`）在现行机器规则下永远不会变成 `accepted`**——
   该 verdict 是「**物理结论已定，但不是可接受的最小值**」的诚实标注；要变 `accepted` 必须有
   `resolved` 复核，而 `resolved` 的准入由 `build_coverage_reviews.py` 的五条 route 决定
   （`multi_basin_coverage` / `known_basin_reproduction` / `single_basin_verified` /
   `dedup_evidence_required` / `unresolved_qc`），**`search_exhausted` 不在其中**。

   > **这精确澄清了 H3**：H3「接受 `search_exhausted` 为最终态」**不是**把标签改成 `accepted`，
   > 而是**承认这 2 态在严格意义上不可接受**，并据此**如实用 `limited` 结题**
   > （限制报告已经这么做）。**H3 是一个「停止条件」决定，不是一条「恢复」路径。**

2. **DMC 两态（`unresolved_qc`）与 DOL/EC 的处境不同**：DMC 的复核是 `unresolved`（**没有跑完/没有过 QC**），
   理论上仍可由**新的、能过 QC 的起点**转成 `resolved`（⇒ `accepted`）。但这要求 DMC 的浅赝平坦谷
   在**不降阈值**的前提下被跨过 —— 即 **H1**（须全 cohort 可比性评估，成本按生产腿口径）。

3. **`resolved` 的准入只有三条有效 route**（`multi_basin_coverage` / `known_basin_reproduction` /
   `single_basin_verified`）。这意味着**四态若要恢复，必须产出属于这三类之一的证据**：
   - 新盆地 ⇒ `multi_basin_coverage`；
   - 复现已知极小 + 生产证据完整 ⇒ `known_basin_reproduction` / `single_basin_verified`
     （**这正是 P4 那 4 条 `no_duplicate` 元素与 H4 的潜在价值所在**）。

## 4. 对「下游重建」（item 9）的意义

- **不必为门 2 单独规划**（已由 `WP5_GATE2_ROOT_CAUSE_20261027.md` 查明是下游信号），
  而**门 1（48/48）同样不是「等着重建就会出现」**：它要求**那四个态各自拿到 `resolved` 复核**。
- ⇒ **item 9 的前提是 item 7/8 真的产出可 `resolved` 的证据**；在此之前，
  **重建下游不会有任何变化**（这也解释了为何此前每次重建都是 44/48）。
- **因此当前所有可推进动作都指向同一件事**：**产出属于那三条有效 route 之一的证据**。
  在当前授权与成本下，**唯一便宜的那条是 H2**（单点检验 GFN2 单盆地的可信度 —— 若否证，
  则 `single_basin_verified` 的科学前提成立，DOL/EC 的诚实终局也就有了依据）。

## 5. 本轮明确**不做**的事

- **不改** `acceptance_decision`、**不新增** verdict、**不放宽** route 准入 ——
  那等于**为了凑 48/48 而放松机器规则**（Scope 明确 Out）。
- **不手工修改** `coverage_reviews.csv` 的任何 verdict。
- **不把 `search_exhausted` 记成 `resolved`** —— 那是「事后把机器结论改写成有利结果」。

## 6. 证据出处

- 生产函数：`build_production_ensemble_aggregator.py` `acceptance_decision`（`:619-657`、调用 `:923`）
- 复核数据：`outputs/physics_completion/recovery/coverage_reviews.csv`（14 行）
- route 定义：`build_coverage_reviews.py` `coverage_route`（`:163-223`）
- 关联：`WP5_GATE2_ROOT_CAUSE_20261027.md`、`LIMITATION_REPORT_20261027.md`、`DECISIONS_PENDING_20261027.md`