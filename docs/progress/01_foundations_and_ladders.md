# 基础、基线与计算台阶

覆盖 Week 1–8。这个阶段的目标不是产出“最佳溶剂”，而是先冻结比较对象、计算层级、状态身份和决策判据，再建立可以逐层比较的证据链。

| 阶段 | 研究动作 | 结果摘要 | 证据入口 |
| --- | --- | --- | --- |
| Week 1–2 | 冻结定义、预注册、方法审计与外部锚点 | Gate 0 关闭；Gate 1 未关闭；气相与溶液锚点的证据等级被明确区分 | [定义](../00_stage0_definitions.md) · [阶段报告](../03_week1_2_report.md) · [`outputs/week1`](../../outputs/week1) · [`outputs/week2`](../../outputs/week2) |
| Week 3 | 建立 broad cheap pool（P0） | core 18、broad 40 的廉价代理层跑通，用于覆盖和候选预览，不作为真值 | [报告](../09_week3_report.md) · [`outputs/week3`](../../outputs/week3) |
| Week 4 | 建立 P1/P2 与几何、介电对照 | r2SCAN-3c、SMD/CPCM、Opt+Freq 和弥散函数对照形成首套计算台阶 | [报告](../10_week4_report.md) · [`outputs/week4`](../../outputs/week4) |
| Week 5 | 加入 `[LiM]+` 配位态 C1 | 配位能显著改变还原侧身份；后续主排序必须区分 molecule-centered 与 Li-centered redox | [报告](../12_week5_report.md) · [`outputs/week5`](../../outputs/week5) |
| Week 6 | 构象、虚频与 `delta_m` | 把方法与构象不确定性并入 pair 级分辨阈值；“无法判定”成为正式结果类别 | [报告](../13_week6_report.md) · [`outputs/week6`](../../outputs/week6) |
| Week 7 | Δ-learning 与主动查询回放 | 建立 direct/shift 模型、拆分方案和标签预算曲线；结果只适用于冻结样本与协议 | [报告](../15_week7_report.md) · [`outputs/week7`](../../outputs/week7) |
| Week 8 | 加入 `[Li(M)2]+` 第一配位壳 C2 | 显式第一壳成为独立台阶；C2 表示 coordination number 2，不是 second solvation shell | [报告](../18_week8_report.md) · [`outputs/week8`](../../outputs/week8) |

## 这一阶段留下的约束

- `P0 → P1v → P2a` 是代理到指定计算目标的路径，不是 cheap-to-truth。
- 排序比较必须同时报告样本集合、轴、状态身份和不确定性阈值。
- C1/C2 的还原侧若发生电子身份改变，不能继续当作同一个 observable 排名。
- 原始周目录继续承担冻结证据角色；后续解释应优先链接主题日志和结论矩阵。
