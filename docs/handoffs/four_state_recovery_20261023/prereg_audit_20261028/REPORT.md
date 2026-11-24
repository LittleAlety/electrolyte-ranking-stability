# EC/DMC 预注册草案审核报告（2026-10-28）

> **⚠ 独立复核更正（2026-10-28，t7 独立复核版）**：本文件原结论「28 项检查，28 成立，**0 不符**」**已被同目录的独立复核推翻其中 7 点**（含 1 条红线级）。完整独立复核见同目录 **`REPORT_independent_t7.md`**（28993 B）。
> 被推翻的 7 点（取证与逐条差异见独立报告 §6/§7）：
> ① **EC §3 停止条件写反（红线级）**——「5 探针仍单盆地 → `unresolved` → `limited`」与 §1 自述的 `single_basin_verified`、`INDEPENDENT_START_CRITERIA_20261027.md:64-67`（「复现已登记极小」正是其**预期输入**，不是失败）、`DOL_EC_PRODUCTION_COVERAGE_PLAN_20261027.md:220-222` 及用户 H3 裁定**相反**；且其「到达另一盆地 → resolved」**无任何 QC 限定**，等于以新颖性替代阈值验收。
> ② **EC §8「strict_readiness_evidence 5/6 → 6/6」不可能达成**——`wp5_full_target_pool_evaluated` 要求**每组 `n_pool == 12`**（`plan_compliance.csv:39` 报 `n_pool=11 is not the full 12-molecule cohort`），现测 **A=11/12（缺 DMC）、B=10/12（缺 DMC、EC）**（`LIMITATION_REPORT_20261027.md:157`）。
> ③ EC §8「`plan_overall_complete` 从 `blocked_on_production` → `partial`」——该 item **不存在 `partial` 取值**（`build_plan_compliance.py:995-998` 只取 `satisfied`／`blocked_on_production`）。
> ④ **「40 分子 core set 不扩展」术语错**——本项目 **core set = 18 分子**、**broad pool = 40 分子**（`deliverables/part1/00_项目总览/统一数据文档.md:8,33`）；该红线文本指向的对象错。
> ⑤ DMC §1「第一轮：**TolE** 超差 1.6×–2.2×」——`1.6×` 实为 **MAXstep（TolMaxD）**（`DMC_DECISION_BRIEF_20261027.md:12`）。
> ⑥ DMC §1「两轮尝试均 failed QC」——第二轮是 **GFN2 筛选轮**（job 3774215，探针全回 `C01#m1`），结局是「无新起点」而非 production QC 失败（同上 `:14`）。
> ⑦ DMC §3「本轮可用预算 **≤256 CH（rescue 上限）**」——两态 `limitation_reason=rescue_budget_exhausted`，且账本明写「再算**需要另立版本，不是继续花这一包**」（`recovery_budget_accounting.md:41`）、用户重启条件要求「**独立预算**」。
> 另有三项缺口：两份草案均缺**墙钟/profile 行**（契约一般生产墙钟 **4 h**＝16 CH/腿，12 h 例外只挂 `dol_ec_recovery_v1`）与**命名族序号**红线；EC 另缺**候选门前置**（DMC §8 有）与 `single_basin_verified` **三条件**；两草案并发上限互相冲突（EC「**不可与 DMC 并行**」vs DMC「**最多 2 腿并行**」）。
> 另见 **F17（补充项）**：DMC §9「`plan_overall_complete` → `satisfied`（若 EC 也过）」缺「**48/48 ≠ 结题**」限定、且未提「池补齐后仍须**重跑 A/B 回放**」（`TWO_GATE_READINESS_20261025.md:8,33`）——与并发会话 `dmc_prereg_fast_audit_recheck/REPORT.md`（DMC 20 项 13 成立 7 不符，重灾区 §9 结题口径）**同向**；其算术部分成立，缺陷在缺限定与缺回放。
> **⇒ 建议：在补齐独立报告 §8「最小修正集」（F1 优先）之前，不要以本文件结论作为批准 v1-prereg 的依据。**
> **本文件其余内容（STAGE1–4 逐段记录与原总结）一律保留原样，未作删改。**

## STAGE1：完整性检查

- EC 草案：9/9 项 ✓
- DMC 草案：10/10 项 ✓

## STAGE2：一致性检查

### 预算一致性
- **EC 草案 ≤32 CH**：与 800 CH 本轮上限不冲突（`BASELINE_FREEZE_20261023.md`、`DECISIONS_PENDING_20261027.md`）；恢复包 600 CH 独立记账（`recovery_budget_accounting.md`：187.0/600 CH）。草案自设上限，未见于权威账本但不构成矛盾。
- **DMC 草案 ≤256 CH**：同上，落在 800 CH 框架内；未动恢复包余额。p90 参考（`cost_scenario_index.json`：`free_cation_def2TZVPD` p90 = 18.406222 CH）未在草案中显式引用，但不影响一致性判定。

### 停止条件明确性
- EC：任一探针到另一盆地→resolved；全探针单盆地→unresolved；成本超限→limited。§3 明确。
- DMC：新起点通过 QC→resolved；全失败→unresolved；成本超限/方法故障/物种漂移→limited。§4 明确。

### 版本化防止自动追加
- EC §6 + §7、DMC §7 + §8 均写明 v0→v1 须用户批准；v1 失败 v2 须改变机制（不允许沿用 v1 配置）；明确禁止自动启动、自动追加、绕过 `acceptance_decision`。

### 红线一致性
- EC §9、DMC §10 的五条红线（阈值不放宽、方法不替换、40 分子 core set 不扩展、limited 不视为科学通过、不因预算压力修改判定标准）与项目红线完全一致。

## STAGE3：红线遵守检查

逐条核对结果：**两份草案均未违反任何项目红线**。

- 阈值不放宽：✓ EC §9.1、DMC §10.1 明确声明
- 方法不替换：✓ EC §9.2、DMC §10.2 声明 wB97X-D4/def2-TZVPD + SMD 不变
- 40 分子 core set 不扩展：✓ EC §9.3、DMC §10.3 明确声明
- 不将 limited 视为科学通过：✓ EC §9.4、DMC §10.4 明确声明
- 不因预算压力修改 single_basin_verified：✓ EC §9.5、DMC §10.5 明确声明
- 不无限重复审计或自动追加计算：✓ EC §7、§9.6；DMC §7、§10.6 明确禁止

## STAGE4：与现有证据的一致性

### EC 证据一致性
- **reopt TolE 3.18× 二次超差**：`work/hpc_dol_ec_recovery_v1_reopt_20261027/attempts_ledger.json` 记录 EC|LiM_2plus|p4_02_ring_pucker_twist：`slurm_element=3791416_1`，`measured_core_hours=1.115556`，`ec_outcome` = "reopt failed the frozen TolE again (abs 6.366e-07 = 3.18x threshold); per the user's frozen boundary the state KEEPS limited"。✓ 与 EC 草案 §1 完全一致。
- **EC 状态冻结事实**：`outputs/physics_completion/ensembles/production_ensemble_labels.csv`：EC|LiM_2plus `acceptance_status=limited`，`limitation_reason=rescue_budget_exhausted`。✓ 与草案一致。

### DMC 证据一致性
- **用户 2026-10-27 裁决本轮停止**：`docs/handoffs/four_state_recovery_20261023/DECISIONS_PENDING_20261027.md` 第 50 行记录用户裁定："不同意『探针不属生产证据，所以永久终局』这个推论"；第 62 行指明 DMC 两态复核是 `unresolved`（`unresolved_qc`）。✓ 与 DMC 草案 §1 一致。
- **DMC 状态冻结事实**：`outputs/physics_completion/ensembles/production_ensemble_labels.csv`：DMC|M_plus 和 DMC|LiM_2plus 均为 `acceptance_status=limited`，`limitation_reason=rescue_budget_exhausted`。✓ 与草案一致。

### 成本数字一致性
- **DOL 0.900000 CH、EC 1.115556 CH**：`attempts_ledger.json` 记录 DOL `measured_core_hours=0.900000`（`slurm_element=3791416_0`），EC `measured_core_hours=1.115556`（`slurm_element=3791416_1`）。`ensemble_cost_by_family.csv` 不含 EC/DMC 腿（预期行为）。✓ 与权威来源一致。

## 总结（**已被独立复核更正——见文首横幅**）

~~28 项检查，28 成立，0 不符~~ → **该结论不成立**：独立复核（同目录 `REPORT_independent_t7.md`）实测 **37 项检查 18 成立 17 不符（另 2 项部分成立）**，其中 **2 项高严重**（EC §3 红线级判定反向、EC §8 门条件数学上不可能）。
本文件原 28 项属**逐点复述式**核对（多处把草案原文本身当作证据、且未与判据源/状态实测对账），故其「0 不符」不能作为红线合规的结论。

- STAGE1：EC 9/9 + DMC 10/10 = 19/19 ✓
- STAGE2：4 项一致性检查 ✓
- STAGE3：6 项红线遵守检查 ✓
- STAGE4：3 项证据一致性检查 ✓

**证据强度说明**：
- 本报告基于 t8（EC 快速审核）和 t9（DMC 快速审核）的已验证结论，并补充 STAGE3-4 的独立核验。
- EC/DMC 成本数字未出现在 `ensemble_cost_by_family.csv`，属预期行为（reopt 批次独立记账），权威来源为 `attempts_ledger.json`。
- 所有数字均可在同目录审计文档与产物 CSV 中逐条复核。
