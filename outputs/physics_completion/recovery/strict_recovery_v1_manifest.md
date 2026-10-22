# strict_recovery_v1：14 个 limited 态的恢复批次 manifest（登记，未启动）

> 生成器 `build_strict_recovery_manifest.py`（`--check` 完全只读）。
> 用户 2026-10-21 严格目标裁决：14 态全部排入恢复计划，每态 ≤2 个新独立起点，
> 总上限 28 条；**历史失败保留原状态**，本 manifest 只登记将来要做什么。

## 编排总览

| 项 | 值 |
|---|---|
| 态数 | 13 |
| 新起点上限 | 每态 2 个，合计 **28** 条 |
| 可直接用冻结池盆地 | 1 态（TMP|M_plus） |
| 池盆地 + 需补搜索 | 0 态（无） |
| 必须版本化新搜索 | 7 态 |
| 成本依据合计 | 178.2 core-hours（5 态无实测依据 → MISSING） |
| 批次预算 | 恢复包 **600** + 风险储备 **300** core-hours（首批实测后冻结，非全计划总预算） |

## 逐态登记

| 优先级 | 态 | 路径 | 起点 1 | 起点 2 | 历史限制 | 上限 |
|---|---|---|---|---|---|---|
| P0 | AN\|M_plus | new_search_required | （待注册） | （待注册） | rescue_budget_exhausted | 2.728 |
| P1 | DMC\|LiM_2plus | new_search_required | （待注册） | （待注册） | rescue_budget_exhausted | 23.853 |
| P0 | DMC\|M_plus | new_search_required | （待注册） | （待注册） | rescue_budget_exhausted | 23.592 |
| P1 | DOL\|LiM_2plus | new_search_required | （待注册） | （待注册） | rescue_budget_exhausted | 13.998 |
| P1 | EC\|LiM_2plus | new_search_required | （待注册） | （待注册） | rescue_budget_exhausted | 18.084 |
| P0 | TMP\|M_plus | frozen_basin | c10 | r3_c42 | rescue_budget_exhausted | 46.961 |
| released | DEC\|M | released | r2_c23 | （待注册） | — |  |
| released | DME\|LiM_2plus | released | r3m_c05 | （待注册） | — |  |
| released | DME\|M_plus | released | c07 | （待注册） | — |  |
| P1 | DMSO\|LiM_plus | new_search_required | r3m_c00 | （待注册） | rescue_budget_exhausted | 8.999 |
| released | SL\|LiM_2plus | released | r3m_c00 | r3m_c01 | species_drift_unrecoverable |  |
| released | TMP\|LiM_2plus | released | r3m_c00 | （待注册） | — |  |
| P1 | TMP\|LiM_plus | new_search_required | r3m_c05 | r3m_c08 | species_drift_unrecoverable | 40.011 |

## 停止条件（冻结）

1. 每态最多 2 个新独立生产起点；两个都失败 → 该态保持 `limited`，总闸门继续阻塞，
   具体原因逐态登记（`species_drift_unrecoverable` / `rescue_budget_exhausted` / 新类别）。
2. 不放宽几何阈值、不把失败结构改记 `computed`、不删除历史失败、不直接改绿合规表。
3. 起点搜索方法变更可单独登记；最终能量/热化学方法变更需统一 cohort 修订。
4. 预算耗尽即停——恢复包 600 core-hours，风险储备 300 另计，首批实测后冻结。

**本 manifest 只是登记：任何提交都要用户逐态确认或按本表一次性批准。**
