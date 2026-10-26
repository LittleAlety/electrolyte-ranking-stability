# WP5 闸门 2（A 11/12、B 9/12）根因诊断（2026-10-27）

> 触发：闸门 2 `wp5_full_target_pool_evaluated` 长期为 False，但此前**只记录数字、从未诊断原因**。
> 本文给出实测根因。**纯分析、零计算、不改任何状态。**

## 1. 一句话结论

**A 11/12、B 9/12 不是模型或回放失败，而是「四个 `limited` 态的下游后果」**：
`qc_complete_pair=False` 的分子被**正确地**排除出回放池，而缺的分子恰好就是那三个有非 `accepted` 态的分子。

## 2. 实测证据

**目标池本身是完整的 A 12 / B 12**（`target_pool_AB.csv`，24 行，12 个分子 × 2 任务）：
`AN DEC DMC DME DMSO DOL EC EMC GBL PC SL TMP`。

但回放只用了 **11 / 9**，差额来自 `qc_complete_pair` 列：

| 任务 | `qc_complete_pair=True` | `=False`（被排除） | 结果 |
|---|---|---|---|
| **A**（free 氧化位移） | **11** 个 | **DMC** | **11 = 12 − 1** ✓ |
| **B**（Li 条件化位移） | **9** 个 | **DMC / DOL / EC** | **9 = 12 − 3** ✓ |

**集合等式（决定性证据）**：
- 系综中**非 `accepted`** 的分子 = `{DMC, DOL, EC}`
- **B 池缺失的分子** = `{DMC, DOL, EC}`
- ⇒ **两者完全相等**（`set(b_bad) == set(lim)` 实测 `True`）

**B 池三个缺失分子的标签表面态**（同一张 `target_pool_AB.csv`）：
`DMC` / `DOL` / `EC` 的 `S_Li_ev` 与 `D_coord_ev` **数值都在**（并非空），但 `qc_complete_pair=False`
——即**标签算出来了，但配对完整性未通过**，故按冻结规则**不得**进入回放池。

**A 池只缺 DMC 的原因**：A 只需 **free 标签**（`S_f_ev`），而 `DMC` 的 `state=M_plus` 也是 `limited`
⇒ DMC 连 free 标签的配对完整性都不成立；`DOL` 与 `EC` 的 `M/M_plus` 是 `accepted`，故 A 池可用。

## 3. 为什么这是**正确行为**而非缺陷

计划原文：「停止预算未达到可以如实 `not_reached`，**不能用子池代替全池**」。
现状恰是这条纪律的**严格执行**：
- 池子**没有**被悄悄补齐或替换（否则就是「用子池冒充全池」）；
- `stop_budget_status` 已如实记录：A 池 `computed 15 / not_reached_within_pool 1`；
  B 池 `computed 4 / not_reached_within_pool 12`，其说明原文即
  「**`not_reached_within_pool` is an honest 'the pool never reached it'**」。

## 4. 因果链（把两件事连起来）

```
四个 limited 态（DMC×2、DOL/LiM_2plus、EC/LiM_2plus）
   ↓ 其 M/M_plus 或 Li 腿未 accepted
qc_complete_pair = False（这三个分子）
   ↓ 冻结规则排除出回放池
A 池 11/12、B 池 9/12
   ↓
wp5_full_target_pool_evaluated = False
   ↓
门 2 阻塞、严格闸门不 complete
```

**⇒ 闸门 2 不是独立问题，而是四态恢复的同一后果**：把四个 limited 态救回来，
`qc_complete_pair` 变 True，A/B 自然回到 12/12，门 2 自动满足。**不需要单独为 WP5 做任何事。**

## 5. 对决策的意义（重要）

1. **不必为门 2 单独规划工作**——它是四态恢复的**下游信号**，不是平行任务；
2. **它反过来加强了 H2 的价值**：H2 检验「GFN2 单盆地」是否方法性，直接影响
   `DOL` / `EC` 两个 `LiM_2plus` 态能否被认定「已穷尽」⇒ 决定门 2 的**科学前提**；
3. **也提示了 H1/H4 的真实收益**：若 H1（DMC 优化设定）或 H4（合格 P4 元素）能把
   `DMC`/`DOL`/`EC` 推成 `accepted`，**门 2 会一并解决** ⇒ 它们的价值被此前的「四态专项」视角**低估了**。

## 6. 证据出处

- `outputs/physics_completion/active_learning/blind_replay/target_pool_AB.csv`（24 行，含 `qc_complete_pair`）
- `outputs/physics_completion/active_learning/blind_replay/AB_axis_endpoint.csv`（32 行，含 `stop_budget_status`）
- `outputs/physics_completion/ensembles/production_ensemble_labels.csv`（48 行，44 accepted）
- 脚本：`scripts/wp_production/build_wp5_target_pool.py`、`run_wp5_AB_replay.py`