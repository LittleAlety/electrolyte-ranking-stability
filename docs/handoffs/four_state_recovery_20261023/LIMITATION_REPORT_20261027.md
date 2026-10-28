# 四态恢复 · 限制报告（2026-10-27）——按机器闸门签发，**严格目标保持未完成**

> 依据：计划最后一条 action item 的后半——「若有界预算后仍不足，出**逐态失败证据、真实成本和下一轮新假设**；
> 研究报告可以收口，**严格目标保持未完成**」。
> 本报告**不改 48 分母、不降五阈值、不手写 accepted、不清零历史成本**；所有数字实测。

## 0. 三终态分别报告（不得混同）

| 终态 | 结论 | 依据 |
|---|---|---|
| ① **四态科学恢复** | **未达成**：系综 **44/48 accepted**；四态仍 `limited`（`rescue_budget_exhausted`） | `production_ensemble_labels.csv` 实测 |
| ② **正式研究闭环** | **未达成**（**但根因已查明为①的下游**）：闸门 2 `wp5_full_target_pool_evaluated` 仍 False（A **11/12**、B **9/12**） | `AB_axis_endpoint.csv` + `strict_readiness` |
| ③ **工程可复现性** | **已核验**：**41 项只读门 40 通过**（唯一失败 `check-mirror` 已定位并修复，见 §4） | `work/_run_readonly_gates.py` |

> **②的根因更正（2026-10-27，`8b3d515`，见 `WP5_GATE2_ROOT_CAUSE_20261027.md`）**：
> 本报告初版把 ② 与 ① 并列为**两个独立未达成**。实测**不成立**——A 11/12、B 9/12 **完全由 ① 决定**：
> 目标池本身是**完整的 12/12**，回放排除了 `qc_complete_pair=False` 的分子，而**这些分子恰是
> 有非 `accepted` 态的那三个**（B 池缺失集合 `{DMC,DOL,EC}` 与系综非 accepted 集合**完全相等**）。
> ⇒ **②是①的下游信号，不是平行任务**；四态一旦恢复，门2 自动满足。
> 此处**保留原记录**（不抹除历史），仅补根因更正。

> **③的补充（2026-10-27 后续轮）**：只读门清单扩展并**全部通过**（见 §3）；但**同时发现三处「静默阻塞」**
> （§1.1）——**工程可复现性「绿」不等于「恢复路径通」**：门会响，但**登记链会静默吞掉结果**。

**严格总闸门**：`complete = false`，`blocked_by = [ensemble_not_48_accepted, wp5_full_target_pool_evaluated]`
（与裁决前**逐字一致**，未因本轮改动漂移）。

## 1. 逐态失败证据（真实已运行尝试）

| 态 | 已运行尝试 | failure class / 结论 | 证据 |
|---|---|---|---|
| `DMC\|M_plus` | 生产层 **18 条失败腿**（含 superseded）⚠**口径更正（2026-10-27）**：18 = DMC/DOL/EC **三家合计**（判读文档 `DMC_THRESHOLD_DIAGNOSIS:3` 原文口径）；**DMC 单家实为 14**（8 条 QC 失败 + 6 条 superseded，`production_ensemble_structures.csv` 现测）；筛选层 P4 2 探针 | `verytight_convergence` / `max_cycles_exhausted` / `strict_reopt_required` **三类同型** | `production_ensemble_structures.csv` + 原始 ORCA 日志逐循环解析 |
| `DMC\|LiM_2plus` | 同上家族 | 同上 | 同上 |
| `DOL\|LiM_2plus` | 筛选层 `strict_recovery_v1`（**0 起点**）+ P4 2 探针 + v2 10 探针 | 三轮独立方法**未找到新重骨架盆地**；**且当前无登记通道可用**（见 §1.1） | `P4/V2_RESULTS_ADJUDICATION`、`DOL_EC_NO_CANDIDATE_ROOT_CAUSE` |
| `EC\|LiM_2plus` | 同上（v2 10 探针） | 同上；**但 EC 侧 10/10 涉机器 `no_duplicate`** ⇒ 存在冻结规则下合格候选 | `P4_V2_NO_DUPLICATE_CORRECTION` |

### 1.1 三处「静默阻塞」（**本轮新增，是本报告最重要的结构发现**）

四态的四个缺口**不只是「找不到起点」**——即使找到起点，还有**三层登记/资格过滤**会**静默**吞掉结果：

| # | 约束 | 漏掉的后果 | 证据 |
|---|---|---|---|
| 1 | 离开 `search_exhausted` **必须有生产恢复成员**（`latest_members` 非空） | 只补 `registered_starts` **不改变 route**（实测仍 `search_exhausted`） | `build_coverage_reviews.py:172-190`；用户反例已复现 |
| 2 | `member_role` 必须 ∈ `{round1_extra, recovery_v1_start}` | 该成员**永不进 `latest`**，状态永远 `limited`（`:691-696` 注释即事故报告） | `build_production_ensemble_aggregator.py:610`/`:696`；四角色实测 |
| 3 | **候选表 `production_ensemble_candidates.csv` 里必须先有该态的行** | **生产腿跑完也无处挂靠**（`load_candidates()` 只读该表，缺失即 `raise`） | `:599-612`；DOL/EC 实测无 `recovery_v1_start` 行 |

**共同点：「有结果」≠「被系统看见」**，而**每一环失败都不报错**（显为 `n_pending` / `limited`，像「还在进行中」）。

**DOL/EC 的具体阻塞（第三条）**：`strict_recovery_v1_manifest.csv`（13 行）里 DOL/EC 的
`start_1_basin`/`start_2_basin` **均为空** ⇒ `recovery_candidate_rows()` 无料可产；
而 `torsion_probe_candidate_rows()` 的 glob **只匹配 `work/hpc_torsion_probe_v*`**，**不覆盖 P4/v2 包**
⇒ **两条通道都无料可产**。**故 DOL/EC 当前无法经生产腿恢复**，除非补一条版本化登记通道（**待裁定**）。

**DMC 的判读（item 6）**：三种 failure class 是**同一浅赝平坦谷**的三种表现——
末循环常 **4/5 过**（唯一不过的 MAXstep 3.24e-4 vs 2e-4）；49 循环者在末期**反而恶化**；
重优化后 SCF 达标而几何轮间 ΔE 仍超冻结 TolE。**同设置重试已被 18 条腿证伪**，故不投 v2。

**EC 的例外（必须写明）**：`find_rotatable_bonds` 返回的四原子**全非 H**，产生最差扭转的二面角是
**`O–C–O–Li`**（含 Li、不含 H；全 24 条含 Li 14 / 含 H 0）⇒ 差异是**Li 配位取向**，
**按冻结 10° 规则仍属合格独立起点**。**不把它改写成「重复」**（用户明令）。

## 2. 真实成本（分口径，不混算）

| 段 | 实测 | 采用（裁决口径） |
|---|---|---|
| P4 筛选 job `3774215` | 8 元素 × 4 核，raw **0.002222 CH** | **0.54 CH**（每元素 ≥4 核×1 分钟） |
| v2 扩搜 job `3777206` | 20 元素，raw **0.006667 CH**（6 元素各 1 s） | **1.34 CH**（同口径向上记） |
| **筛选层合计** | — | **1.88 CH** |
| 首轮生产 512 / 有因救援 256 | **未动** | 无起点可投 |
| **历史成本（不清零）** | 四态活动 **227.43 CH**；主生产账本 **591.8 CH** | 记录在册 |

**筛选额度**：原 32 − 1.88 = **余 30.12 CH**。

## 3. 机器闸门实测（本轮）

| 项 | 结果 |
|---|---|
| 收口链的 **`--check` 步骤** | **36/37 通过** |
| 附加只读门（settled-p4 / settled-v2 / refreeze / site） | **4/4 通过** |
| **合计** | **40/41**（唯一失败 `check-mirror`，原因见 §4，**已修复且复核 OK**） |
| 全量 pytest | **EXIT=0 / 0 FAILED**（`work/_pytest_r13.log`） |
| `strict_readiness` 组合口径 | `complete=false`，`blocked_by` 两项 |

## 4. 本轮发现并修复的一处**真缺口**（我自己的改动引起）

`check-mirror`（`build_physics_completion_deliverables.py --check`）报
`week44: 3 failure(s)` —— 我在执行裁决 ③ 时改了 `plan_compliance.csv/.md/_meta.json`，
但**仓库外的交付镜像** `成果输出（part2）/week44` **未随之重建**。
**处置**：重建镜像（该脚本文档明写「**只写镜像目录与 part2 根索引，绝不动仓库源路径**」）⇒
`week44: 243 files / 5 checks / 0 failed`；复核 **`CHECK OK -- all 8 weeks are byte-identical`**。
**教训**：改任何进入交付镜像的产物后，**必须重建镜像**，否则 `check-mirror` 会红（而它**不在**我那 39 步清单里，
是收口链的独立步骤）。

## 5. 下一轮新假设（供你裁定；本轮**不执行**）

| # | 假设 | 成本（按**对基准**估） | 状态 |
|---|---|---|---|
| **H1** | DMC 阈值平台可由「**同一冻结方法 + 版本化优化设定**」解决（不降阈值） | 须先做**全 cohort 可比性评估**（对全部 48 态同法重算）⇒ 成本需按生产腿口径估，**远超本轮余量** | 未批 |
| **H2** | GFN2 单盆地是**方法性**的（可用冻结方法的**单点**检验） | **单点实测中位 81 s ≈ 0.09 CH**；包内 **6 次**（3 样本 × {末几何, 已登记极小}）≈ **0.54 CH**、提交器预留 **2.0 CH**；若只投 3 次则约 **0.27 / 1.0 CH**。（原文按生产腿估 20–30 CH，**高估 74–111 倍**）⇒ 余量绰绰有余 | 未批（**唯一便宜且不越冻结项**，**且已升级为解锁门2 的关键一步**） |
| **H3** | 接受 `search_exhausted` 为**本轮**终态并据此收口 | 0 | **用户裁定：可定稿本报告**（保留 44/48），但**明确不同意「探针不属生产证据 ⇒ 永久终局」** |
| **H4** | 把**冻结规则下合格**的 P4 四元素（EC 侧为主）送 DFT 生产轮 | 需按生产腿口径估（≈9.9 CH/腿基准）并**预注册**；受「每态 ≤2 起点」约束 | 未批 |

**用户对 H3 的原话要旨（必须并列保留）**：
> 「**不同意『探针不属生产证据，所以永久终局』这个推论**」；
> 「**DOL/EC 不必强行找到第二个极小才能恢复，但必须证明独立起点在生产方法下通过了验证。**」
> 「『版本化登记』能够建立这条证据链，**不能替代其中的计算**。」

⇒ **`search_exhausted` 是本轮的诚实终态；日后若补上生产级 `computed` 证据
（严格优化 + `AnFreq` + 身份 QC + 去重、生产证据齐全），仍可走 `single_basin_verified` ⇒ `resolved` ⇒ `accepted`。
是本轮证据不足，不是永久终局。**

**共同前提**：H1/H4 涉及版本化或新起点，须**先预注册**（唯一定义/成本上限/停止条件/不回填旧池）。

## 5.1 当前唯一剩下的**硬阻塞**（待你裁定）

**DOL/EC 无登记通道**（§1.1 第三条）。两条解法：
1. **新增版本化通道**直接读 P4/v2 包（`source_kind=p4v2_screening_v1_start`），
   **只收骨架真动 13 条**、排除 **15 条纯 Li 位移**（**更干净**：不动既有生成物、语义显式）；
2. 把合格起点写进 `strict_recovery_v1_manifest.csv` 的 `start_1_basin`——
   但该文件是**生成物**，手工改会被重建覆盖（影响面更大）。

**明确不是解法**：把 glob 扩到 `hpc_xtb_screening_v2`——会让**纯 Li 位移**混进候选
（P4/v2 的 `probe_class` 是错的 `heavy_fragment_torsion`），且改变既有包登记语义。

**若你不出这条通道** ⇒ DOL/EC **无法经生产腿恢复**，本报告即为本轮终稿。

## 6. 本报告明确**不**主张的事（守红线）

- ⛔ **不**主张「800 CH 框架内可恢复路径已穷尽」——正确表述是
  「**已登记的 P4／v2 筛选动作未找到可确认的新重骨架盆地**；不等于全局单盆地，也不等于 800 CH 已耗尽」；
- ⛔ **不**把机器 `no_duplicate` 改写成 `duplicate`；**不**放宽 10° 去重条件；
- ⛔ **不**把「正常终止 / 筛选层单盆地 / 本限制报告」冒充**严格结题**；
- ⛔ **不**从 800 支取 WP6／扩池（两者当前 **0 CH 执行额度**，触发后才各自冻结）；
- ⛔ **不**删除远端失败落点（`3774076` 日志与包副本保留）。

## 7. 证据出处

- 只读门运行器：`work/_run_readonly_gates.py`（输出 `work/_readonly_gates.txt`）
- 逐态证据：`production_ensemble_structures.csv`、`strict_recovery_v1_manifest.csv`、
  `recovery_budget_accounting.md`、`FOUR_STATE_STARTING_LEDGER_20261025.md`
- 判定与裁定：`P4_RESULTS_ADJUDICATION_20261025.md`、`XTB_V2_RESULTS_ADJUDICATION_20261026.md`、
  `P4_FOUR_ELEMENTS_ELIGIBILITY_20261026.md`、`P4_V2_NO_DUPLICATE_CORRECTION_20261026.md`、
  `DMC_THRESHOLD_DIAGNOSIS_20261025.md`
- 预算与执行账：`P4_SETTLEMENT_20261025.md`、`FOUR_STATE_EXECUTION_ACCOUNT_20261025.md`、
  `XTB_SCREENING_V2_PROTOCOL_20261025.md`

## 8. **终局附录（2026-10-27 深夜，DOL/EC 生产腿与重优化之后）——系综 45/48，严格目标仍未达成**

> 本节保留上面 §0–§7 的原记录（它们写于生产腿之前），只补**其后的真实进展**。
> 45/48 ≠ 48/48：**严格目标依然未完成**，且下面逐条写明还剩什么。

### 8.1 三终态（更新后）

| 终态 | 结论 | 依据 |
|---|---|---|
| ① 四态科学恢复 | **部分达成**：系综 **45/48 accepted**。恢复 1 态（`DOL\|LiM_2plus`）；`AN\|M_plus` 经**既有搜索证据**恢复（非本轮四态）；仍 `limited` 3 态 = `DMC\|M_plus`、`DMC\|LiM_2plus`（用户裁决本轮停止）、`EC\|LiM_2plus`（重优化二次超差） | `production_ensemble_labels.csv` 实测 |
| ② 正式闭环 | **未达成**，且根因不变：`wp5_full_target_pool_evaluated=False`，池随 45/48 重算为 **A=11/12（缺 DMC）、B=10/12（缺 DMC、EC）**——仍是 ① 的机械下游 | `AB_axis_endpoint.csv`（n_pool 11/10，32 端点）|
| ③ 工程可复现性 | **已核验**；且**本轮新增关闭一道门**：`identity_all_members_complete` 由 False → **True** | `strict_readiness` 现测 `blocked_by` **2 项** |

**严格总闸门现测**：`complete=false`，`blocked_by=[ensemble_not_48_accepted, wp5_full_target_pool_evaluated]`
（**3 项 → 2 项**：identity 已关闭）。

### 8.2 本轮真实新增计算（全部终态 sacct 结算）

| 批次 | job | 内容 | 墙钟×核 | 实测 CH |
|---|---|---|---|---|
| DOL 首轮 | 3782517 | 生产腿（Opt+AnFreq） | 01:04:08×4 | 4.2756 |
| EC 首轮 | 3789580 | 生产腿 | 00:49:57×4 | 3.3300 |
| DOL/EC 重优化 | 3791416 | 从各自末几何严格重优化 | 13:30 / 16:44 ×4 | 2.0156 |
| **DOL frontier 单点** | **3808874** | **新成员身份（Molden）单点** | **01:47×4** | **0.1189** |
| **合计** | | | | **9.7401** |

（+ 筛选 1.87 ⇒ 新轮次累计 **11.6101 CH**；历史 227.43 + 591.8 另册不清零。）

### 8.3 三态仍 limited 的逐态证据（不含任何未实证的推断）

- **`DMC\|M_plus` / `DMC\|LiM_2plus`**：生产层单家 **14 条**失败/废弃腿（8 QC 失败 + 6 superseded）；
  重优化 reopt1–4 + reopt_v2 全部同型失败；筛选层全部弛豫回 `C01#m1`。
  **用户 2026-10-27 裁决：本轮停止**（保留 limited、全部失败记录与历史成本；
  「浅赝平坦谷」仅作诊断解释；重启须新机制 + 版本化方案 + 独立预算）。
- **`EC\|LiM_2plus`**：首轮 4/5（TolE abs 比值 2.603，负值）、重优化 4/5
  （TolE abs=6.366e-7 = **3.18×**，比首轮更差）。按用户冻结边界
  「各一次新 attempt…本次仍失败即保留 limited，不自动追加下一轮」⇒ **收口**。
- **`AN\|M_plus`（已恢复，非四态）**：不做新计算——用**已登记搜索证据**
  （`strict_recovery_v1_search_index.json`：64 起点、零新极小、输入哈希现算一致）
  + 已通过生产 QC 的独立起点 + 同簇去重 ⇒ `single_basin_verified`/resolved。
  报告口径：**「复现已知单盆地」**，不是新盆地、不是预算失败。

### 8.4 下一轮的新假设（本轮**未**执行，均须新授权）

1. **DMC**：只有在提出**可检验的新机制**（非「换设置再试一次」）+ 版本化 + 全 cohort 可比性
   评估 + 独立预算时重启；定点试算被红线排除。
2. **EC 第三次**：若重开，须先说明「为何第三次可能过」的机制性理由（前两次 TolE 均超差且第二次更差）。
3. **WP6 / 扩池**：触发后**分别冻结**数值预算（结构数、core-hour 上限、停止规则、交付证据），
   **绝不从四态 800 中支取**；当前执行额度 **0 CH**。
4. **工程侧遗留**（本轮实测发现，均不阻塞科学结论）：
   - **`outputs/week3/SHA256SUMS` 的 1 条合法内容变更**：`outputs/week27/claim_scope.json`
     引用了 README 的字节，README 因 44→45/48 重生成而变 ⇒ 登记表需常规 `refreeze` 重同步
     （权威分类器 `refreeze_manifest.py`：eol=0 / **content=1** / missing=0 / dropped=0 / external=0）。
     **⚠ 本报告初稿曾写「220 条漂移」——那是错的**：my own scan hashed RAW bytes while the
     registry stores the **LF-normalised** digest (`* text=auto eol=lf` contract)；抽样复核
     `scripts/make_c1_state_identity_figure.py` 的 LF 归一化 sha = 登记值 `7a21bc16…` 逐位一致。
     ⇒ 属**我的观测手段错**，不是仓库漂移（同族教训：先证明观测手段，再相信观测结果）。
   - 仓库根存在**未跟踪且未被 gitignore** 的 `_preflight_out.json`（并行会话产物）⇒
     `test_repo_layout` 顶层登记检查变红。

### 8.5 一句话结论

**45/48 是本轮的真实科学结果**：DOL 经生产腿 + 严格重优化恢复、AN 经既有搜索证据恢复、
EC 与 DMC 两态按冻结边界与用户裁决收口。**严格 48/48 目标保持未完成**，
报告不改分母、不降阈值、不冒充结题。