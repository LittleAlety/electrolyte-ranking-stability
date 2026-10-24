# 排序稳定性与机制

覆盖 Round 9–15。这个阶段把多个计算台阶放进同一判据，重点从“算出了什么”转向“什么变化会改写决定，以及为什么”。

| 阶段 | 核心问题 | 结论摘要 | 证据入口 |
| --- | --- | --- | --- |
| Round 9 | 五类台阶能否统一比较？ | `f_robust_inv = 0` 与高 `f_unresolved` 同时出现，证明“没观察到反转”不等于稳定 | [报告](../19_week9_report.md) · [`outputs/week9`](../../outputs/week9) |
| Round 10 | 不可判定比例能否代数解释？ | 建立位移割线斜率与 `f_unresolved(z)` 的精确关系；子集漂移要求 τ 同时报 N | [报告](../20_week10_report.md) · [`outputs/week10`](../../outputs/week10) |
| Round 11–13 | 介电响应、导体极限与畸变如何分解？ | bare CPCM 接近单参数自相似；介电位移与几何畸变可分账；离群点需要加密扫描 | [W11](../21_week11_report.md) · [W12](../22_week12_report.md) · [W13](../23_week13_report.md) |
| Round 14–15 | SCF 初猜是否隐藏更低解？ | 双初猜目录发现多个更低解；描述符可辅助事后诊断，但留出臂不足以支持可靠事前预报 | [W14](../24_week14_report.md) · [W15](../25_week15_report.md) |

## 可复用结论

- 位移的**离散度和符号结构**比平均位移幅度更能解释排序改写。
- 介电台阶在当前样本上相对平滑，不代表所有环境与配位台阶都可稀疏采样。
- 初猜敏感性是状态搜索问题，不能仅用一次 SCF 收敛作为电子态唯一性的证据。
- 所有“稳定”表述都必须同时检查 unresolved 分母；零 robust inversion 单独不构成稳健性证明。

对应冻结产物位于 `outputs/week9`–`outputs/week15`；图表清单位于 [`outputs/figures`](../../outputs/figures)。
