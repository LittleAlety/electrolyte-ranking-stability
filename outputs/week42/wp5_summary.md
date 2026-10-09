# Week 42 / WP5 — Δ-learning 与成本感知主动查询

**状态**：任务定义、泄漏防线与成功端点在回放前冻结；既有 Δ-learning / AL 表已复算。

## 冻结内容

- 任务 A：用 X0 与廉价 P0 预测完成 QC 的自由分子 `Gox_ensemble`；任务 B：以 X0+X1 预测配位 shift 并恢复 `Gox_Li`，
  且 **B 的成本显式包含获得 free 标签的成本**。
- 主模型只用岭回归/核岭与 GPR；direct/shift 同特征、同外层 split、同调参预算；保留 random 与 family-group/LOFO。
- 回放：12 个完整标签池内，初始 4 标签、每轮 1 个、20 配对种子；隐藏标签只由离线 evaluator 使用。
- 成功端点（回放前冻结）：O3≥2/3 且 R3≤0.10 eV；tau_b≥0.80 为辅助端点。

## 既有证据复算

- `delta_vs_direct.csv`：24 格，其中 shift 在 tau_b 上更好 **15** 格。
- `success_budget.csv`：24 行 / 6 个 (task,axis) 场景；`budget_to_threshold.csv` 24 行。
- 成本账本：7 项相对预算；**3 项绝对成本缺字段（MISSING）**，故只给相对预算、不给金额。
- 冻结族口径（方案 9.1）：把既有 stage7 复算表（288 行）限制到 ridge/krr/gpr，逐格对比选型；全模型最优落在族外（gbdt/rf/constant）的格子：tau 21/48、MAE 26/48 —— 这些格子只作旁证。

## 验收（7/7 通过）

| check | ok | detail |
| --- | --- | --- |
| task_A_and_B_separated | PASS | B 的成本显式包含获得 free 标签的成本，不隐含为免费 |
| shift_better_count_recomputed | PASS | shift_better=15 / 24 格 |
| success_endpoint_frozen | PASS | 端点由 freeze 规则给出，不由结果反推 |
| replay_not_pretended_blind | PASS | 已声明旧数据大致行为已知；真实前瞻性需另留未计算分子 |
| absolute_cost_missing_flagged | PASS | MISSING=3 |
| frozen_family_view_covers_every_cell | PASS | 288/288 行；48 格，每格冻结族候选 [3] 个 |
| frozen_family_winner_consistent_with_published | PASS | tau 越族胜出 21/48 格；MAE 越族胜出 26/48 格 |

## 限制

- 回放门槛因已知旧数据大致行为，只能作为新批次协议/方法评估，**不伪装成对旧数据完全盲的预注册**。
- 池内端点 tau_b=1.0 是自检端点而非成绩；预算数字不外推到真实项目。
- 规模不足时 AL 仍可作工作流演示，不能证明普适最低标签数；首轮无需扩到 60-100/300-1000。
