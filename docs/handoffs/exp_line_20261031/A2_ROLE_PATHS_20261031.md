# A-2 的两条可行路径（已实测，待裁决）— 2026-10-31

> 状态：**均未执行**。候选表未改；包 `HOLD`、14/14 OK；正式记录 **45 accepted / 3 limited**。
> 本文件回答一个问题：**能否"登记"而不把 `DMC|LiM_2plus` 从 `limited` 推成 `provisional`？** —— **能，有两条路。**

## 1. 两个消费端的判据不同（实测，这是关键）

| 消费端 | 判据 | 出处 |
|---|---|---|
| **聚合器**（决定正式标签） | **精确集合** `member_role in ("round1_extra", "recovery_v1_start")` | `build_production_ensemble_aggregator.py:610`（`load_candidates`）与 `:696`（`latest_attempt_per_member`）**两处** |
| **覆盖审**（决定 coverage 可见性） | **前缀** `str(member_role).startswith("recovery_v1")` | `build_coverage_reviews.py:61`（`RECOVERY_ROLE_PREFIX="recovery_v1"`）与 `:271` |

⇒ **存在一个"覆盖审看得见、聚合器不认"的角色命名空间**（任何以 `recovery_v1` 开头但不等于 `recovery_v1_start` 的值）。

**标签迁移的机理**（已验证）：聚合器 `:809-814` 用 `latest.get(name|slot|seed)`；`latest` 只收精确集合内的角色（`:696`）⇒ 若候选行的角色**不在**该集合，该行**不进 `registered`**（`:610`）⇒ 不会 `n_pending += 1` ⇒ **标签不动**。

## 2. 路径 P1：角色用 `recovery_v1_start`（聚合器认）+ 接受 `provisional`

| 项 | 内容 |
|---|---|
| 做法 | 候选行 `member_role=recovery_v1_start`、`status=planned` |
| 结果 | 覆盖审**能**看见；聚合器把它当已登记工作 ⇒ `n_pending: 0→1` ⇒ **`limited` → `provisional`**、`limitation_reason` 清空 |
| 代价 | **正式表可见改动**：`provisional` 与 `limited` 在 48 分母里含义不同 ⇒ 计数结构变化，必须在报告里如实记录"一次已授权、尚未运行的登记导致的状态迁移" |
| 风险 | 该态从"预算耗尽"叙事变成"有活在飞"叙事；若最终不提交，这条 provisional 会**永久挂着**（直到有终态） |

## 3. 路径 P2：角色用前缀匹配值（覆盖审认 + 聚合器不认）+ **标签不动**

| 项 | 内容 |
|---|---|
| 做法 | 候选行 `member_role=<以 recovery_v1 开头但不等于 recovery_v1_start 的新值>`（如 `recovery_v1_pending_registration`），`status=planned` |
| 覆盖审 | `:271` 的 `startswith("recovery_v1")` **命中** ⇒ 若将来该 member_key 以 `computed` 进入 `structures.csv`，它会进 `members`（`:266-272`）⇒ **R3 可成立** |
| 聚合器 | `:610`/`:696` 的精确集合**不命中** ⇒ 不进 `registered` ⇒ **`n_pending` 不变 ⇒ 标签保持 `limited`** |
| 代价 | ① 引入一个新角色值，须在**生成器/版本化登记源**里定义并写注释说明它与 `recovery_v1_start` 的区别；② **将来该腿真的入账时**，若要让它计入聚合器（即真正推进 45→46），必须把角色**改成 `recovery_v1_start`**——那一步会再次触发标签迁移，但**那时它是 computed 而非 planned**，`n_pending` 不会增加（走 `extras_pool` 分支），所以是安全的；③ 需补测试证明"覆盖审看得见 + 聚合器不认" |
| 风险 | 一个自定义角色值若被后来的生成器重建覆盖（因为生成器只从登记源读），必须落在**版本化登记源**里才持久——与你的指示一致 |

## 4. 我的建议

**P2**，理由是它同时满足你三个约束：
1. 落在**版本化登记源/生成器**（不手改会被重建的 CSV）；
2. **不动正式标签**（不制造一次没有终态的 `provisional`）；
3. 让覆盖审**看得见**这条腿（A-2 的目的）。

并且它保留了一个干净的"升级点"：将来腿落地、QC 通过、写 `computed` 时，把角色升为 `recovery_v1_start` ⇒ 聚合器才认它 ⇒ 那才是真正推进标签的时点。

**但 P2 有一处必须你拍板**：它**新造了一个角色值**。若你认为"引入新角色命名空间"本身需要更重的审批（因为它是语义扩张），则退回 **P1**（接受 `provisional`）或 **P3**（干脆不登记、先只做 A 的复检）。

## 5. 三选一（与上一轮的 i/ii/iii 对应关系）

| 本轮编号 | 含义 | 标签影响 |
|---|---|---|
| **P1**（= i） | 用 `recovery_v1_start` 登记 | `limited → provisional` |
| **P2**（= ii） | 用新前缀角色登记 | **标签不动** |
| **P3**（= iii） | 先不登记，只做 A 复检 | 无 |

## 6. 当前状态（实测）

| 项 | 值 |
|---|---|
| 提交 | **0**（无 `submission_journal.json`、无提交锁） |
| 包 | `submission_gate=HOLD`、`submitted=false`、`sha256sum -c` **14/14 OK**（新清单 sha `56232638…`） |
| 候选表 | **未改**（无 `p5li_vtscf16` 行，仍 123 行） |
| 正式记录 | **45 accepted / 3 limited，分母 48** |
| A 复检（t10） | 已派发，**尚未认领/落盘** |

## 7. P2 机制已用真实函数端到端证实（8/8，非读码推断）

探针 `work/exp_line_20261031/probe_role_divergence.py`（只读，临时文件已清理）**直接调用**真实函数，结果：

```
RECOVERY_ROLE_PREFIX = 'recovery_v1'
aggregator exact set  = ('round1_extra', 'recovery_v1_start')
[OK] coverage reviewer sees 'recovery_v1_start'                     True
[OK] aggregator counts     'recovery_v1_start'                     True
[OK] coverage reviewer sees 'recovery_v1_pending_registration'     True   ← 覆盖审看得见
[OK] aggregator counts     'recovery_v1_pending_registration'      False  ← 聚合器不认
[OK] load_candidates() registers 'recovery_v1_start'               True  (rows=1)
[OK] load_candidates() registers 'recovery_v1_pending_registration' False (rows=0)
[OK] latest_attempt_per_member keeps 'recovery_v1_start'           True
[OK] latest_attempt_per_member keeps 'recovery_v1_pending_registration' False
measurements=8  failed=0
```

⇒ **P2 的两条断言都有函数级证据**：① 覆盖审的前缀判据确实接纳新角色值；② 聚合器的 `load_candidates()` 与 `latest_attempt_per_member()` **都不认**它 ⇒ 该候选行**不会**让 `n_pending` 增加 ⇒ **正式标签保持 `limited`**。