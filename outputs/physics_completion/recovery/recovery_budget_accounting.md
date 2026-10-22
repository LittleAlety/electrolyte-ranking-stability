# 恢复批次预算核算与终局报告（strict_recovery_v1）

> 生成器 `build_recovery_budget_accounting.py`（`--check` 完全只读）。
> 计划原文：「沿用现有恢复包 600 core-hours＋300储备，先核算已消耗、在途预留和余额，
> 不重复拨一份预算。」本表就是这笔账。

## 账本状态

| 项 | 值 |
|---|---|
| 系综 | **43 accepted / 5 limited / 0 provisional**（分母 48 不变）
| 主生产账本（60 腿） | 591.8 core-hours（0 条 MISSING）

## 恢复包消耗（按包实测，4 核/腿）

| 包 | 实测 core-hours | 在跑 |
|---|---|---|
| `hpc_production_ensemble_strict_recovery_v1` | 33.3 | 0 |
| `hpc_production_ensemble_strict_recovery_v1_b2` | 81.2 | 0 |
| `hpc_production_ensemble_strict_recovery_v1_cont1` | 7.9 | 0 |
| `hpc_production_ensemble_strict_recovery_v1_cont2` | 4.5 | 0 |
| `hpc_production_ensemble_strict_recovery_v1_cont3` | 1.8 | 0 |
| `hpc_production_ensemble_strict_recovery_v1_cont4` | 3.4 | 0 |
| `hpc_production_ensemble_strict_recovery_v1_cont5` | 29.1 | 0 |
| `hpc_production_ensemble_strict_recovery_v1_reopt1` | 2.9 | 0 |
| `hpc_production_ensemble_strict_recovery_v1_reopt2` | 1.7 | 0 |
| `hpc_production_ensemble_strict_recovery_v1_reopt3` | 2.1 | 0 |
| `hpc_production_ensemble_strict_recovery_v1_reopt4` | 2.1 | 0 |
| `hpc_production_ensemble_strict_recovery_v1_reopt_v2` | 17.1 | 0 |

**恢复包合计：187.0 / 600 core-hours（31.2%）；风险储备 300 未动用。**

## 9 个 limited 态的终局原因（历史保留，绝不清空）

| 原因 | 态数 | 态 |
|---|---|---|
| `rescue_budget_exhausted` | 5 | AN|M_plus, DMC|M_plus, DMC|LiM_2plus, DOL|LiM_2plus, EC|LiM_2plus |

## 下一轮授权需要知道的事

1. **预算余量充足**：恢复包剩余约 413 core-hours。但 9 个 limited 态里 6 个是`rescue_budget_exhausted`（每成员两次真实计算已用完）——**再算需要另立版本**，不是继续花这一包。
2. **`species_drift_unrecoverable`（EMC/M_plus、TMP/LiM_plus）**：身份漂移是化学事实，换搜索方法不解决；发生键图改变的那条执行继续拒收。
3. **计划预案的对应关系**：6 个预算耗尽态 → 计划「生产级覆盖诊断」（直接 DFT 多起点、相关扭转扫描或不同廉价预优化），须按态逐个版本化预注册（方法、成本上限、停止条件），不得沿用旧池回填。

**本报告只记账，不改变任何验收判定。**
