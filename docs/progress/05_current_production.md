# 当前生产与恢复

当前批次为 `physics_completion_v1`：12 个分子 × 4 个主态，使用 wB97X-D4/def2-TZVPD + SMD，解析梯度优化与 AnFreq。这里不复制会变化的计数；状态以根 README 和机器可读账本为准。

| 问题 | 权威证据 |
| --- | --- |
| 主态优化与频率 QC | [`production_ledger.csv`](../../outputs/physics_completion/free_states/production_ledger.csv) |
| 系综成员与 accepted/provisional/limited | [`production_ensemble_labels.csv`](../../outputs/physics_completion/ensembles/production_ensemble_labels.csv) |
| 恢复尝试、去重与剩余缺口 | [严格恢复报告](../../outputs/physics_completion/recovery/strict_recovery_v1_report.md) |
| 前沿轨道解析 | [前沿报告](../../outputs/physics_completion/frontier/frontier_localization.md) |
| 全成员身份证据登记 | [`frontier_identity_evidence.csv`](../../outputs/physics_completion/frontier/frontier_identity_evidence.csv) |
| 方案合规与新鲜度 | [合规台账](../../outputs/physics_completion/compliance/plan_compliance.md) |
| 原始作业到派生结论的来源链 | [provenance 摘要](../../outputs/physics_completion/provenance/provenance_summary.md) |
| 当前任务与下一步 | [项目导航](../PROJECT_GUIDE.md) |

## 状态解释

- `accepted` 表示通过冻结的生产系综验收，不等同于所有科学身份问题都已独立复核。
- `limited` 和 `unresolved_qc` 必须保留失败尝试、预算和搜索覆盖证据，不能用空值或最近一次收敛掩盖。
- `search_exhausted` 只对登记的方法集和预算成立，不是化学上不存在其他构象的普适断言。
- 生产总闸门逐项检查系综、身份、WP5 和触发后的 WP6；任何单项完成都不能自动推出项目完成。

## 收口入口

```powershell
pwsh -NoProfile -File scripts/wp_production/finalize_wp2.ps1
```

该命令执行离线一致性检查。提交计算需要额外、明确的授权；工程就绪与计算授权是两件事。
