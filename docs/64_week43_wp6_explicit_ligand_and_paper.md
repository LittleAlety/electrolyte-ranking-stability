# Week 43 / WP6 — 显式配体检查（可选）与论文主线收敛

**状态**：可选 WP6 的协议已登记；首轮不执行，待关键 free→Li 结论可解析后启用。

## 冻结内容

- 固定 R = DME，在 EC / DME / AN / TMP 上比较 `[LiM]+` 与 `[LiMR]+`；DME 情况自动成为 `[Li(DME)2]+`。
- 所有样本同一背景配体、同一介质、相同化学计量；比较的是不同条件态的 redox 差值。
- **不**将 cluster 裸 G 跨化学计量 Boltzmann 平均；**不**模拟真实配位 population；不纳入首轮必需闭环。

## 验收（4/4 通过）

| check | ok | detail |
| --- | --- | --- |
| single_background_ligand | PASS | R=DME; 4 molecules |
| dme_auto_case_declared | PASS | 已声明 |
| no_bare_cluster_boltzmann | PASS | 禁止项已写清 |
| wp6_is_optional | PASS | 只在关键 free->Li 结论可解析后做 |

## 论文主线（六张主图）

1. 模型与条件态定义；2. 独立方法审计；3. E→G→ensemble 决策变化；
4. 固定背景配位 pair 证据与身份 outcome；5. 最多 3 个机制案例；6. 累计成本→选集恢复曲线。

主论文首先回答「在本集合中决策可否被解析」，再讨论缺失物理如何改变可解析的选择，最后讨论恢复计算目标的成本。
双源 sigma 恒等式作为**方法审计结果**，不占据主要物理发现位置。
