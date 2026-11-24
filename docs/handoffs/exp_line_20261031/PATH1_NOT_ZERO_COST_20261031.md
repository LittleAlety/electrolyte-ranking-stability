# 第 1 条路（补 `start_1/2_basin`）实测判定：**不是 0 CH 可做的事**（2026-10-31）

> 上一轮我提出"改生成物源补 `start_1_basin`/`start_2_basin`，0 CH、工作量中等"。
> 本轮把该生成器读透后，**这条判断是错的**，必须撤回。下面是实测依据。

## 1. `start_1_basin` 是怎么来的（生成器原文）

`scripts/wp_production/build_strict_recovery_manifest.py`：

```python
# :355-364
# Li states take their starts from the recovery MOTIF search; free /
# cationic states from the conformer search.  Both are registered
# artifacts -- no start is ever synthesised here.
recovery_minima = (_li_recovery_starts().get(key, [])
                   if "Li" in state else _search_minima().get(key, []))
for m in recovery_minima:
    if len(starts) >= MAX_STARTS_PER_STATE: break
    starts.append(m.get("basin_id", ""))
    start_sha.append(m.get("geometry_sha256", ""))
...
"start_1_basin": starts[0],          # :403
"start_2_basin": starts[1],          # :404
```

**两个数据源，都是"已登记产物"，且都明确禁止合成**：

| 函数 | 数据源文件 | docstring 原文 |
|---|---|---|
| `_li_recovery_starts()`（:242） | `LI_RECOVERY_EXEC`（round-3 Li motif 执行产物） | "**Nothing here is invented**: the row's motif geometry and hash are carried verbatim"；只收 `kept=true` **且** `new_vs_round1=true` 的行 |
| `_search_minima()`（:280） | `SEARCH_POOL`（`strict_recovery_v1_search_pool.csv`） | "The search pool is the **ONLY** source of new starts for `new_search_required` states -- **starts are never invented**"；只收 `status == "candidate_start"` |

## 2. 现网该态的实际字段（实测）

| 字段 | 值 | 含义 |
|---|---|---|
| `historical_limitation` | `rescue_budget_exhausted` | 预算耗尽 |
| `unused_pool_basins` | `''` | **冻结池里没有可用盆地** |
| `start_1_basin` / `start_2_basin` | `''` / `''` | **无已登记起点** |
| `max_new_starts` | `2` | 还缺 2 个 |
| `needs_versioned_search` | `true` | **明确要求版本化搜索** |
| `search_outcome` | `no_new_minimum_found` | 曾做过搜索、没找到新极小 |
| `status` | `planned` | 尚未执行 |

## 3. 因此第 1 条路不成立

要在 `start_1_basin` 里出现值，**必须**上游 `SEARCH_POOL` 出现该态的 `status=candidate_start` 行（或 `LI_RECOVERY_EXEC` 出现 `kept=true && new_vs_round1=true` 行）。
而这些行**只能由真正的搜索产生**——即：
- 多个独立起点、覆盖构象/配位空间的一次**实际搜索**；
- 其结果（哪些是真新盆地）才能写成 `candidate_start`。

**换句话说**：`start_1_basin` 是**搜索的结论**，不是**可填的配置**。手填它等于伪造搜索结果，且生成器下次重建会覆盖（它是生成物），更会与 `search_outcome`、`unused_pool_basins` 三者互相矛盾。

⇒ **撤回我上一轮"0 CH 可做"的说法**。三条路的真实代价应更正为：

| 路 | 真实代价 | 状态 |
|---|---|---|
| ① 补 `start_1/2_basin` | **需真实搜索**（不是改配置） | 与 ② 实为同一条 |
| ② 真跑一次多起点搜索 | **新计算，需新授权** | 不在本轮 64 CH 授权内 |
| ③ 接受 `tors_7_0_1_2` 作为历史搜索范围证据 | 0 CH | **你已明确不批** |

## 4. 那么本轮 64 CH 授权还剩什么价值（诚实评估）

**这条腿本身仍有技术价值，但没有"推进 45→46"的价值**：

| 它**能**产出 | 它**不能**产出 |
|---|---|
| 一条严格数值协议（VeryTightSCF + EnforceStrictConvergence）下、对已登记单一极小的**独立复现**证据 | 该态的**搜索范围**证据（因为起点是已知极小，不探索新空间） |
| 若 Opt 五项全过 + 0 虚频 ⇒ 一条 `computed` 成员，可**增加该态的成员数**（`n_unique` 可能 1→2，但若被 dedup 判同簇则不变） | `single_basin_verified`（缺 `starts`）；也不能证明"该态只有一个盆地" |
| 验证 16 核 vs 4 核的墙钟/core-hours 收益（这是你最初问的"核数收益"） | 45→46 的标签推进 |

⇒ **若目标是推进 45→46**：本轮 64 CH 授权**不足以**达成，需要另立一次**搜索类**实验授权。
⇒ **若目标是测核数收益**：这条腿仍可做，但**须先明确**它不会被记作"覆盖审通过"。

## 5. 当前状态（本轮零生产写入）

| 项 | 值 |
|---|---|
| 提交 | **0**（无 journal／无锁） |
| 包 | `HOLD`、`submitted=false`、`sha256sum -c` **14/14 OK** |
| 候选表 | **未改**（123 行） |
| 正式记录 | **45 accepted / 3 limited，分母 48** |
| A 复检（t10） | 已派发、**仍未认领** |

## 6. 需要你裁决（这次是目标层面的）

1. **是否放弃用这 64 CH 推进 45→46**（因缺搜索范围证据），改为：**(a)** 仅测核数收益、明确不记作覆盖审通过；或 **(b)** 把 64 CH 留着、另立搜索类实验授权；或 **(c)** 本轮直接收口、不提交。
2. 若选 (a)，请同时确认：该腿落地后**不进入** coverage 复核流程（因为注定 `unresolved`），只在报告里作为"数值协议复现证据 + 核数收益数据"呈现。