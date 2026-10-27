# 2026-10-27 evidence_gate / batch_cost_settlement 只读代码复核（含边角猎杀）

> 审计者角色：**只读复核方**。本报告只写这一个文件；未建任何脚本/测试，未碰生产代码，未 git 写，未调超算，**未运行** `work/_evidence_gate_red.py`。
> 允许运行的唯一测试：`.\.venv\Scripts\python.exe -m pytest tests/test_evidence_gate_and_cost.py -q -p no:cacheprovider` → **16 passed, exit=0**（我另加 `PYTHONDONTWRITEBYTECODE=1` 以避免测试把字节码写进 `scripts/wp_production/`，理由见 §F-14）。

## 0. 审计对象 sha256 留痕（审计前后均校，未漂移）

| 对象 | sha256 | 字节 | mtime (UTC) |
|---|---|---|---|
| `scripts/wp_production/evidence_gate.py` | `b863fbe54748333983190dfde28182a51cf62365bdefe6bdaf3b4ba933db7df4` | 6110 | 2026-10-27T05:11:15Z |
| `scripts/wp_production/batch_cost_settlement.py` | `10cb69350708faaaadaa8cabbae31df37a9e21dda917858d06f6f59a4f0df732` | 3282 | 2026-10-27T05:11:15Z |
| `tests/test_evidence_gate_and_cost.py` | `adaff91365504af1385de455cc3929b444cbf2290185413837af2b719f7dea51` | 7853 | 2026-10-27T05:08:53Z |
| `work/_evidence_gate_red.py` | `587aa7f78a60d1a58c2c9b0089198a1b6dd591df1181cb06f17fd64364a7d187` | 3814 | 2026-10-27T05:10:26Z |

**仓库基线漂移（据用户并发会话纪律必须绑定快照）**：审计开始时 HEAD=`e030bfaa313979289e812d4349bc1a474aa46361`；审计中途另一会话提交，HEAD→`bd754f8f0fce2076bc4d80591c6e0f9afecc293b`（"按 2026-10-27 执行方案补两模块 + 16 测试（RED 5/5 PROVEN）+ 四处登记 + DOL 腿真实结算 4.2756 CH"）。**上述四个对象 sha256 在两时点逐字节相同**，故本报告结论对这四份成立；本报告**不**对其余文件（含 `submit_hpc_batch.py`，sha256=`3fb8037c915f4fab2c9c2cee7b10655b52794bff20b1b0ba23788f0187a146b6`）下全局结论，仅就"是否接线"作事实陈述（该文件在 `bd754f8` 中**未被修改**）。

---

## A. 用户 8 条最低清单 → 测试映射表（逐条核"断言是否真钉住"）

| # | 清单条目 | 对应测试（tests/test_evidence_gate_and_cost.py） | 断言是否真钉住该行为 | 判定 |
|---|---|---|---|---|
| 1 | 预检 STALE → HOLD | `test_preflight_stale_blocks_submission` :52-53 | `preflight_ok=False` → `is NextAction.HOLD`。因 `_evidence()` 默认 `submission_status="absent"` 且其余 ready，:56 已证同参数下才得 SUBMIT_ONCE ⇒ HOLD 确实由 preflight 造成 | **成立**（行为）；"STALE"≠一般失败这一语义无表示 |
| 2 | 已有提交尝试但响应不明 → RECONCILE，不得再投 | `test_unclear_submission_reconciles_never_resubmits` :68-71（parametrize 三态 `submitting/submit_failed/unknown`） | 三种不明状态**逐一**断言 `is RECONCILE`（:68 的 parametrize 决定覆盖面无遗漏） | **成立** |
| 2b | （同上）"没有任何路径回到 SUBMIT_ONCE" | 无 | 无任何测试断言此点。我穷举 11 个 status 值（见 §C-1），**仅 `absent` 能得 `submit_once`** ⇒ 结构性成立，但**测试未钉住** | **部分成立** |
| 3 | Slurm COMPLETED、尚无 QC → 仍需回收和 QC | `test_completed_without_artifacts_then_fetch_then_qc` :75-80 + `test_not_terminal_yet_then_wait` :83-86 | :77 断 FETCH（未回收）、:80 断 QC（回收后无 QC → 仍需 QC）、:86 断 WAIT（未终态） | **成立** |
| 3b | "COMPLETED"这一事实的映射 | 无 | 测试用 `terminal_states_verified` **布尔**代指 "COMPLETED"，不经 `sacct_terminal_states`；"COMPLETED 行 → verified=True" 的派生无测试（无 adapter，见 §E-3） | **部分成立** |
| 4 | QC 失败但证据完整 → 可结算并出限制报告 | `test_qc_failed_still_settles_and_reports` :90-97 | 断言 `qc_results_complete=True, cost_settled=False` → SETTLE（:95）、全完成 → REPORT（:96-97）。**但模块内不存在任何"失败"表示**：只有一个 bool，测试无法区分"都通过"与"每腿都有判定（含失败）"。"失败仍结算"完全依赖 adapter 的映射约定 | **部分成立**（行为链成立、语义未被钉住） |
| 5 | 一个数组元素费用缺失 → 拒绝结算，不补零 | `test_missing_cost_record_refuses_not_zero` :101-104 | `pytest.raises(ValueError, match="MISSING")`，期望 2 元素只给 1 条 4/3610 记录 ⇒ 消息级钉住"拒绝且不补零" | **成立** |
| 6 | 父任务及 .batch 记录 → 不重复计费 | `test_parent_and_batch_rows_not_billed` :108-116 | :115-116 断言**精确总额** `== Decimal("4")*3610/3600`；若父行被计费（99999 秒）总额必变 ⇒ 真钉住 | **成立**（"真违反必被抓"） |
| 7 | 相同数组元素多条记录 → 拒绝简单相加 | `test_duplicate_record_refuses_simple_addition` :120-126 | `pytest.raises(..., match="重复调度记录")`，消息级钉住 | **成立** |
| 8 | DMC / 第三任务 / 储备起点混入 → 提交前拒绝 | `test_third_task_or_dmc_mixed_in_refused` :130-142；`test_real_batch_is_exactly_the_two_activated` :145-149 | **未真钉住**：:136-138 造 **3 行** tasks.txt，而 `batch_is_exactly_activated` 在 :131 `if len(tasks) != 2: return False` **先拦下**，`return pkg_keys == act`（:138）**根本没被执行**。:142 的 `next_action(...HOLD)` 也只钉住 `if not e.batch_tasks_exactly_activated`（:67） | **部分成立** |
| 8b | 三方核对（activation / candidates / tasks.txt） | 仅 `test_real_batch_is_exactly_the_two_activated`（happy path，实测未 skip ⇒ 真实包现为 True） | `if act != cand or len(act) != 2`（:126）**无任何测试**；:138 的 key 集合比对亦无测试（见上）。我实测 :138 **有牙齿**：2 行、把 DOL 换成 DMC → `False`；2 行、改 seed → `False`（见 §C-5） | **不符**（守卫工作但未被钉住） |

**A 段小结**：8 条中 6 条真钉住（1/2/3/5/6/7），2 条部分成立（4 的语义、8 的 key 比对）；另 8b 三 registry 比对无测试。

---

## B. `next_action` 分支次序审计：混入检查优先于 RECONCILE 是否合理

**代码现状（`evidence_gate.py:66-93`）**

```python
66: def next_action(e: Evidence) -> NextAction:
67:     if not e.batch_tasks_exactly_activated:
70:         return NextAction.HOLD            # 最先判
73:     if e.submission_status in ("submitting", "submit_failed", "unknown"):
74:         return NextAction.RECONCILE
75:     if e.submission_status == "absent":
76:         ready = (e.preflight_ok and e.authorization_bound
77:                  and e.package_verified and e.budget_reserved)
78:         return NextAction.SUBMIT_ONCE if ready else NextAction.HOLD
79:     if e.submission_status != "submitted":
80:         return NextAction.HOLD
81:     if not e.job_mapping_verified: return NextAction.RECONCILE
83:     if not e.terminal_states_verified: return NextAction.WAIT
85:     if not e.artifacts_verified: return NextAction.FETCH
87:     if not e.qc_results_complete: return NextAction.QC
89:     if not e.cost_settled: return NextAction.SETTLE
91:     if not e.downstream_checks_ok: return NextAction.REBUILD
93:     return NextAction.REPORT
```

**实测（逐 status 探针，`batch_tasks_exactly_activated=False` vs 干净）**

| `submission_status` | 混入批次 | 干净批次 |
|---|---|---|
| `absent` | **hold** | submit_once |
| `submitting` / `submit_failed` / `unknown` | **hold** | reconcile_submission |
| `submitted` | **hold** | publish_stage_report |
| `rejected` / `Rejected` / `complete` / `''` / `SUBMITTED` / `"absent "` | hold | hold |

**判定：合理，成立。** 理由：
1. **RECONCILE 本身是一个"动作"**，其语义是"把调度器行绑定到本批次的成员集合上"。一旦批次含未授权任务，被绑定的**目标集合未定义**——把不明提交"核对"进那两条授权腿，等于把混入**洗白**成已知状态。HOLD 是唯一不产生新绑定的选择。
2. **HOLD 严格更保守**：它同时阻断了 SUBMIT_ONCE 与 RECONCILE/WAIT/FETCH/QC/SETTLE 全部下游（实测 `submitted` 也被拦为 hold）。
3. 与代码 docstring `:68-69` "refuse BEFORE anything else, even before reconciliation of an in-flight attempt" 一致，且是**范围违规的终止态**（红线违规不该有自动前路）。

**两点保留（非安全性，属可复核性/覆盖）**：
- **该优先级无测试钉住**：:142 用的是 `_evidence()` 默认 `submission_status="absent"`（提交前态），**没有**"混入 + `submitting`/`submitted` → HOLD 而非 RECONCILE"的用例。若有人日后把 :67 移到 :73 之后，16 项仍全绿。
- **HOLD 无诊断字段**：`NextAction` 是纯枚举（:36-45），`next_action` 返回时不携带"哪个 registry 不合格"（是 DMC 混入、还是 tasks.txt 计数不对、还是包名不对）。调用方只能记 `hold`，人需再跑 `batch_is_exactly_activated` 才知道原因——**fail-closed 但不可定位**。建议返回 `(NextAction, reason)` 或让 `batch_is_exactly_activated` 返回失败项名。

---

## C. 边角猎杀（逐项：触发条件 → 实测 → 判定）

### C-1 `submission_status="rejected"` 或其它未列值 → 落到哪、是否安全
**落点**：`evidence_gate.py:79-80` `if e.submission_status != "submitted": return NextAction.HOLD`。
**实测**（11 个值，含 `rejected`/`Rejected`/`complete`/`''`/`SUBMITTED`/`"absent "` 带尾空格）：除 `absent` 外**全部 hold**，无一能到 `SUBMIT_ONCE`。
**判定：安全（fail-closed）**，但有两点需要说明：
- 大小写/空白变体（`SUBMITTED`、`"absent "`）→ hold，即"拼写偏差一律停"而非"一律放行"，方向正确（若 `"absent "` 被判成 absent 反而会提交）。
- **词表靠约定**：状态以字符串相等逐个枚举（:73、:75、:79），无闭集校验。`"rejected"` 字面意味着"提交被拒"⇒ 按第 2 条原则（已有尝试即必须核对）本可 RECONCILE；HOLD 更保守所以不危险，但它把"必须核对的尝试"静默降级成"停"，并**不会报错**。建议构造期用 `Literal`/`Enum` 校验，未知词 loud 失败。

### C-2 `SACCT_NON_TERMINAL` 含 `CANCELLED` ⇒ 被 scancel 的腿永远 WAIT —— **真缺陷（本段最重要的发现）**
**代码**：`evidence_gate.py:141-142`
```python
141: #: states that mean the scheduler itself never finished accounting for a job
142: SACCT_NON_TERMINAL = {"PENDING", "RUNNING", "SUSPENDED", "COMPLETING", "CANCELLED"}
```
**实测**：
| State 输入 | `sacct_terminal_states(...)` 返回 |
|---|---|
| `'CANCELLED'` | **`{}`** ⇒ 调用方读作"未终态"→ `WAIT` |
| `'CANCELLED by 59540'` | **`{'9_0': 'CANCELLED by 59540'}`** ⇒ 判为终态 |
| `'WEIRD_STATE'` | **`{'9_0': 'WEIRD_STATE'}`** ⇒ 判为终态（见 C-4） |
| `'RUNNING'` / `'PENDING'` / `''` | `{}` |
| `'COMPLETED'` / `'FAILED'` / `'TIMEOUT'` | 返回状态映射 |

**判定：真缺陷，且是双向的不一致**：
1. **字面 `CANCELLED` 永久 WAIT**：Slurm 语义里 `CANCELLED` **是终态**（本项目自己的词表就这么写——`submit_hpc_batch.py:73-74` `TERMINAL_STATES = {..., "CANCELLED", "PREEMPTED", ...}`）。凡是状态被规范成裸 `CANCELLED` 的场景，这条腿永远不会进 FETCH/QC/SETTLE，只能空转 `WAIT`。
2. **本项目历史反证**：`work/_recovery_sacct.txt:39` 载真实记录 `3747724_[0-2]|CANCELLED by 59540|0:0|00:00:00|0`；`docs/handoffs/four_state_recovery_20261023/FOUR_STATE_STARTING_LEDGER_20261025.md:44,49` 与 `agent_ledger_verify_20261025/REPORT.md:59` 都把这个 `CANCELLED` 元素按 **0 core-hours 的终态**结算入账（"`Elapsed=00:00:00`、`AllocCPUS=0` ⇒ 计 0 core-hours"）。⇒ 项目实践认定 CANCELLED 是终态，与本模块把它列为非终态**直接冲突**。
3. **同一事实存在两套互相矛盾的词表**：`submit_hpc_batch.TERMINAL_STATES`（含 CANCELLED=终态）vs `evidence_gate.SACCT_NON_TERMINAL`（含 CANCELLED=非终态）。这正是项目已知教训的形状——**"同一事实存两份副本必须有跨副本一致性守卫，否则副本独立漂移且不报错"**（lesson `0mvp9qk7j-519dd9fa9d874bb5b12b3ac9f5`；另见"冻结常量多处副本判据"`0mvnjx6fo`）。此处漂移已实际发生：两份词表对 `CANCELLED` 给出相反判定，且没有任何测试或守卫比对它们。
4. **缺少归一化**：同仓 `submit_hpc_batch.py:216` 有 `state = state.rstrip("+")`（说明作者知道 sacct 会在状态后加 `+` 截断），本模块**无**该归一化，也无 `" by <uid>"` 剥离。后果：`PENDING+`/`RUNNING+` 之类若出现，会**因为不在黑名单里而被判成终态**（方向上比"漏判终态"更危险）。
5. **修复建议（按优先级）**：① 改为**白名单**终态判定并复用 `submit_hpc_batch.TERMINAL_STATES`（消灭第二份词表；`CANCELLED` 自然归终态），其余一律返回 `{}`；② 判定前归一化：`state.split(" by ")[0].strip().rstrip("+")`；③ 补测试：裸 `CANCELLED`、`CANCELLED by <uid>`、`PENDING+`、未知名四种输入各自断言语义。

### C-3 `ElapsedRaw="Invalid"` / `AllocCPUS="0"` 的行为
**代码**：`batch_cost_settlement.py:60-63`
```python
60:         cores = int(row["AllocCPUS"])
61:         seconds = int(row["ElapsedRaw"])
62:         if cores <= 0 or seconds < 0:
63:             raise ValueError("非法费用字段: %s" % job_id)
```
**实测**：
| 输入 | 结果 |
|---|---|
| `AllocCPUS="0"` | `ValueError: 非法费用字段: 1_0`（项目自己的消息） |
| `ElapsedRaw="Invalid"` | `ValueError: invalid literal for int() with base 10: 'Invalid'`（**Python 原生消息，非项目消息**） |
| `ElapsedRaw="-5"` | 同上路径 → `非法费用字段` |
| 行缺 `ElapsedRaw` 列（仓内真实捕获格式） | **`KeyError: 'ElapsedRaw'`** |
| 行缺 `AllocCPUS` 列 | **`KeyError: 'AllocCPUS'`** |

**判定：拒绝方向成立（不会补零、不会算错），但错误类型/消息不一致，属受控性缺陷**：
- 用户第 5 条说的是"**记录缺失** → 拒绝"，其消息是 `MISSING`（:56-57）。而"字段非法/字段缺失列"走的是**另外两种异常**（原生 `ValueError`、`KeyError`）。若上游按 docstring 的 `MISSING` 语义去 `except ValueError:` 决定"保留预留、不释放"，那么 `KeyError` **不被捕获**，会让结算路径直接崩，而不是一次受控拒绝。
- `parse_sacct_rows` 用 `dict(zip(header, parts))`（:33），列名完全由输入决定 ⇒ 列缺失不会在解析期被拦，只会推迟成 `KeyError`。
- 建议：入口处显式校验必需列（缺列 → `ValueError("MISSING_COLUMNS: ...")`）与数值格式（用正则/`Decimal`），把三类失败统一到项目消息；或定义专用异常类型。
- **另有一处口径张力（见 §F-7）**：`cores <= 0` 把 `AllocCPUS=0` 判为"非法字段"，但本项目历史上 `AllocCPUS=0` 表示"**取消前未运行、计 0 CH**"（`3747724`，同 C-2 的引文）。⇒ 一条被取消的腿在新规则下**根本无法结算**（永远拿不到 `cost_settled=True`），而历史账本却能。若恢复批次出现"提交后取消"，该模块给不出终态。

### C-4 未知状态 fail-open —— **真缺陷（与自身 docstring 矛盾）**
**代码**：`evidence_gate.py:145-166`，判定式为**黑名单**：`if any(s in SACCT_NON_TERMINAL or s == "" for s in seen.values()): return {}`（:164）。
**docstring**（:149-150）："Non-terminal or **unknown** states return {} (callers read that as "wait"), never a fabricated terminal verdict."
**实测**：`'WEIRD_STATE'` → `{'9_0': 'WEIRD_STATE'}`，即**被判为终态**。
**判定：不符，fail-open，方向错误。** 后果链：一个拼错/未知/被截断的状态（如 `PENDING+`、`OUT_OF_MEM+`、`CANCELLED+`）会被当作"已终态" ⇒ `Evidence.terminal_states_verified=True` ⇒ 门推进到 FETCH/QC/SETTLE，对**实际还在跑或状态未知**的作业做出终态裁决——正是本闸门要防的"不编造终态"。修复同 C-2 第 5 点（白名单）。

### C-5 `batch_is_exactly_activated` 只比 `(name, seed)`，slot 未参与 —— **真缺陷（slot 盲）**
**代码**：
```python
101:         name, _slot = str(entry["state_key"]).split("|")   # slot 丢进 _slot，从不使用
102:         out.add((name, str(entry["leaf"])))
...
137:         pkg_keys.add((parts[1], parts[-1].split("__", 1)[1]))   # 只取 name 与 __ 之后的 seed
```
**实测**（内存构造假包，不写盘）：把两条 `tasks/<NAME>/<SLOT>__<seed>` 的 SLOT **都写成 `EC`**（真实值应为 `LiM_2plus`，见 `config/recovery_start_activation_v1.json:12,19` 的 `state_key` 与 `work/dol_ec_recovery_v1/tasks.txt:1-2`）→ **返回 `True`（放行）**。
**判定：不符，真缺陷。** 后果：`tasks/<NAME>/<SLOT>__<seed>` 的 SLOT 段就是溶剂环境，**slot 写错＝跑错化学体系**（如把 DOL 的几何放进 EC 环境），而三方核对（activation / candidates / tasks.txt）**两侧都把 slot 丢掉了**，门依然全绿。当前真实包恰好 slot 正确（`LiM_2plus`），故是**潜伏缺陷**；一旦有人复制包、改 slot 而忘改 state_key，或反过来，无人能发现。
**测试侧同源缺陷**：`tests/...:137` `lines = ["tasks/%s/LiM_2plus__%s" % (n, s) for (n, s) in keys]` —— **把 slot 硬编码成同一个常量**，结构上永远不可能发现 slot 错配。
**修复建议**：把 slot 纳入键元组（activation 侧 `state_key.split("|")` 本就有 slot，`_slot` 直接用起来）；`pkg_keys.add((parts[1], parts[-2]... ))` 需按 `parts[2].split("__")[0]` 取 slot；并补一条"slot 错配必须 False"的测试。
**附**：:137 对畸形 tasks.txt 会抛 **`IndexError`**（实测：2 个空白分隔 token 且其一无 `/` 或无 `__`，如 `"tasks/DOL/LiM_2plus__p4_...  nosep"`、`".../foo"`）。它是"崩"而非"返回 False"——不静默放行（fail-closed），但调用方 `if batch_is_exactly_activated(pkg)` 会异常退出而不是 HOLD。建议加 `if len(parts) < 3 or "__" not in parts[-1]: return False`。

### C-6 Evidence 的 12 个布尔有无"两份副本、无一致性守卫"风险 —— **风险成立（当前潜伏、接线即真）**
**现状**：`Evidence`（`evidence_gate.py:48-63`）是 `@dataclass(frozen=True)`，**无 `__post_init__`**（实测 `hasattr(Evidence,'__post_init__') is False`）⇒ 12 个字段可任意填、无跨字段不变量。
**与项目教训的对照**：已知教训的具体形状（lesson `0mvp9qk7j`：`check()` 只校验 `manifest.json` 的 `members`，**从不读同一事实的第二份副本 `member.json`** ⇒ 篡改副本静默通过）在本模块**以变体复现**：
- 事实的"权威计算"在同一对模块里已有三处：`batch_is_exactly_activated()`（:115）、`sacct_terminal_states()`（:145）、`batch_cost_settlement.allocated_core_hours()`（:37）；
- 而 Evidence 里对应的 `batch_tasks_exactly_activated`、`terminal_states_verified`、`cost_settled` **是独立填写的第二份副本**，**没有任何代码把 bool 与那三个函数绑起来**（全仓 grep：这三个函数与 `Evidence` 均**只被 tests 调用**，见 §E-3）。
- 结果：副本可独立漂移且不报错。`docstring:6-7` "every ``Evidence`` field is filled by a real-evidence adapter upstream, **never by a human typing `True`**" 是**约定**，不是守卫。
**判定**：教训同族风险成立。**建议**：把唯一构造口收敛成 `Evidence.from_artifacts(...)`（内部**必须**调用那三个函数来派生 bool），或加 `__post_init__` 不变量，或干脆删掉可由函数计算的 bool 字段（"可重算的事实不存第二份"）。

### C-7 计费用 Decimal 而核数/秒用 int；`int("4.0")` 会崩 —— sacct 会不会输出小数 AllocCPUS？
**实测**：`int("4.0")` → `ValueError: invalid literal for int() with base 10: '4.0'`（真崩，非静默）。
**sacct 是否输出小数 AllocCPUS：无法确定。** 缺什么：一次真实超算侧 `sacct -P -o JobIDRaw,AllocCPUS,ElapsedRaw` 原始输出（本任务禁止调超算）。**仓内可得证据**：`work/_recovery_sacct.txt` 全 42 条数据行（含父数组行 `3747724_[0-2]`）的 AllocCPUS 均为整数 `4` / `0`；Slurm 的 `AllocCPUS` 语义是**整数核数**（`--cpus-per-task` 计数），`ElapsedRaw` 是整数秒。⇒ 风险低，但**类型契约不自洽**（`Decimal` 总额 vs `int` 输入，且转换用的是最脆的 `int(str)`）。
**判定：低风险 + 类型契约不够硬。** 建议：显式 `int(Decimal(row["AllocCPUS"]))` 或正则 `^\d+$` 校验 + 项目消息，避免 `"4.0"` / `"4 "` / `"4\n"` 这类形态造成无消息崩溃（`" 4 "` 目前能过，`"4.0"` 不能，行为不一致）。

---

## D. RED 脚本只读审计（`work/_evidence_gate_red.py`，**未运行**，纯静态）

### D-1 五个篡改目标（`old` 字符串）在当前生产源码中是否都还存在 —— **全部存在**
| # | 篡改标签 | `old` 原文 | grep 命中 | 存在 |
|---|---|---|---|---|
| 1 | drop RECONCILE branch | `if e.submission_status in ("submitting", "submit_failed", "unknown"):` | `evidence_gate.py:73` | ✔ |
| 2 | drop missing-record refusal | `if set(selected) != expected:` | `batch_cost_settlement.py:54` | ✔ |
| 3 | drop duplicate refusal | `if job_id in selected:` | `batch_cost_settlement.py:51` | ✔ |
| 4 | bill parent rows too | `if job_id not in expected:` | `batch_cost_settlement.py:49` | ✔ |
| 5 | drop batch-mixing refusal | `if not e.batch_tasks_exactly_activated:` | `evidence_gate.py:67` | ✔ |

（脚本 `:67` 另有 `if old not in src:` 兜底并把"目标找不到"记入 `failures` ⇒ 目标漂移不会静默。✔）

### D-2 还原是否完整（finally）—— **成功路径完整、逐字节等价；异常/硬杀路径不完备**
**代码**：`:76-80` `finally:` 无条件把 `ORIGINAL_GATE` / `ORIGINAL_COST` 写回两个文件（无论哪个被篡改、无论是否 `continue`）；`:82-86` 再跑一次全套作控制组。
**等价性实测**：四个目标文件**均为纯 LF**（`evidence_gate.py` CRLF=0/LF=165；`batch_cost_settlement.py` CRLF=0/LF=81；tests CRLF=0/LF=182；RED 脚本 CRLF=0/LF=97），而篡改与还原都传 `newline="\n"`（:70、:78、:80）⇒ 还原内容与原文**逐字节相同**（不会因行尾转换改哈希）。**判定：成立。**
**不完备处**：还原**无任何校验**（不比对 sha256、不比对 `read_text()` 是否等于 `ORIGINAL_*`），唯一"控制组"是"全套 16 项绿"（:82-86）——若还原失败同时又把测试改坏，控制组可能仍绿。且篡改与还原之间**只在进程级 finally 兜底**：`TerminateProcess`/断电/沙箱强杀不触发 finally。**没有备份文件、没有 atexit、没有信号处理**。

### D-3 **真缺陷：脚本 docstring 与提交信息都声称"不动盘上文件"，实现却真改生产文件**
- `work/_evidence_gate_red.py:3-4` 原文：*"Tampers the PRODUCTION modules **in memory (sys.modules replacement, files on disk untouched)** and asserts the mapped test goes red."*
- `bd754f8` 提交信息原文：*"RED 实证（`work/_evidence_gate_red.py`，**改副本文件**+finally 还原）"*
- **实现**（`work/_evidence_gate_red.py:19`、`:70`）：
```python
19: PROD = REPO / "scripts" / "wp_production"
70:             p.write_text(src.replace(old, new, 1), encoding="utf-8", newline="\n")
```
`p = PROD / fname` 是**真实生产文件**；`sys.modules` 在那行只用于脚本自身导入，子进程 pytest 读的是**盘上被改过的**文件。⇒ **两份文字描述都与实现相反**，真实行为比文档所述**危险**：篡改窗口内（父进程暂停、子进程跑 pytest 期间）生产代码是被削弱的（如 `if False:`），只是靠 finally 收回。
**后果**：任何在此期间并行读这四份文件/复用工作区的会话（本项目明文存在并发会话，见用户纪律"多会话并发同一工作区"）会读到**被削弱的守卫**当"当前生产源码"，并可能据此下结论或留痕哈希。
**建议**：① 真的改成在**副本目录**上篡改（复制到 `tempfile.mkdtemp()` 或按项目惯例的工作镜像目录，再对该副本跑 pytest——与"自测不得写仓库"lesson `0mvnum9na` 同族）；② 若坚持原地改，则还原后**强制自校 sha256** 并断言等价；③ 修正 docstring 与提交信息措辞。

### D-4 **真缺陷：RED 用例 4 不忠实——父行从未被计费，红的是别的原因**
`:48-51`
```python
48:     ("bill parent rows too (double-bill trap)", "batch_cost_settlement.py",
49:      'if job_id not in expected:',
50:      'if job_id not in expected and "." not in job_id and "_" not in job_id.replace("1_0",""):',
51:      "test_parent_and_batch_rows_not_billed"),
```
**实测替换后谓词**（expected=`{"1_0"}`）：
| 行 id | 篡改后 | 说明 |
|---|---|---|
| `1`（父） | **SKIPPED（仍未计费）** | 篡改**没有**让父行进入计费 |
| `1_0` | SELECTED | 正常 |
| `1_0.b` / `1_0.e` | SELECTED | 变成多余选中 |

⇒ 该用例变红**不是因为父行被计费**，而是因为 `.b`/`.e` 被选中后撞上 `:54` 的完备性检查（抛 `MISSING`）。即**证明的是另一条守卫**（完备性），不是它标注的那条（父行不双计）。**判定：不符**（RED 结论"父行双计会让测试红"未被真正证实）。
**对照**：测试本身**有效**——`:115-116` 用精确总额断言，若父行（`ElapsedRaw=99999`）真被计费，总额必变、断言必红。所以这是**RED 用例的忠实性缺陷，不是生产缺陷**。
**附**：RED 的 5 个用例**未覆盖** `:126`（`act != cand`）与 `:138`（`pkg_keys == act`）⇒ 与 §A-8b 的测试缺口一致；即便把 `:138` 改成 `return True`，RED 也会**全绿**（正是 lesson `0mvp9qk7j` 通则①"RED 没全红先问是不是该属性根本没被校验"的同类盲区，此处表现为"RED 用例集不覆盖该行"）。

### D-5 运行性风险（未运行，仅记录）
`run_case`（:28-30）用 `subprocess.run(..., capture_output=True)`：在受限沙箱下"子进程管道 stdio"会被拒（EPERM）。此时异常仍落在 `finally` 内 ⇒ 生产文件会被还原（风险可控），但脚本会中途中断、`failures` 不完整，且**控制组不会跑**。按简报我**未运行它**。

---

## E. 与用户方案原文的偏离

### E-1 原文核对的可核性（诚实声明）
**无法确定（原文不在仓内可检索到）**：我按字段名与措辞做了全仓检索，`preflight_ok|authorization_bound|budget_reserved|job_mapping_verified|terminal_states_verified|downstream_checks_ok` 在**全部 `*.md` 中 0 命中**；仓内只有**模块级登记**（`scripts/wp_production/README.md:101`、`docs/65_repo_layout.md:196`），未列 `Evidence` 字段清单。缺什么：用户 2026-10-27 执行方案中 `Evidence` 骨架的**原文段落**（应在会话简报层，不在仓库）。⇒ 本节以 Lead 简报给出的前提（"骨架无 `batch_tasks_exactly_activated`，是我们加的第 8 条防线"）为准，仅审计其**语义风险**，不核"是否照抄"。

### E-2 **`batch_tasks_exactly_activated: bool = True` 默认值 ⇒ 旧调用方静默绕过混入检查（风险成立、高危）**
**代码**：`evidence_gate.py:48-63`
```python
48: @dataclass(frozen=True)
49: class Evidence:
50:     preflight_ok: bool
...
55:     submission_status: str
...
61:     downstream_checks_ok: bool
62:     # 2026-10-27 ruling: the batch may ONLY carry the two activated tasks.
63:     batch_tasks_exactly_activated: bool = True
```
**实测**：省略该 kwarg 构造 → `Evidence(...).batch_tasks_exactly_activated == True`；`hasattr(Evidence,'__post_init__') is False`（无任何不变量）。
**判定：不符，风险成立且是本模块最危险的一处"默认值语义"。** 理由：
1. **不对称**：其余 **11 个字段全部无默认值**（构造必须显式传、漏传即 `TypeError`），**唯独**"10-27 新增的第 8 条提交前红线"给了默认 `True`。⇒ 唯一新增的、直接守"混入即拒"的防线，是**唯一 opt-in** 的。
2. **静默**：任何按 10-27 之前骨架写的调用方（或任何漏传该字段的新 adapter）构造出的 `Evidence` 都**自动宣称"批次恰好只含两条激活任务"**，而 `next_action` 的**第一个分支**（:67）就是读它——绕过不仅静默，还伪装成"正常放行"。
3. **当前尚无调用方**（见 E-3），所以此刻是**潜伏**；一旦接线，正是"新守卫被旧骨架默认值吃掉"的经典事故。
**建议**：① 把默认值去掉（与其余 11 字段一致，强制显式），或反过来默认 `False`（fail-closed——忘了填只会 HOLD，不会放行）；② 若必须留默认，改由 `Evidence.from_artifacts()` 内部**调用** `batch_is_exactly_activated()` 派生，禁止外部直接填。

### E-3 **接线缺口（与 E-2 同根因）：两模块 + 16 测试目前是"有入口无供给"的孤岛**
- **全仓 grep**：`next_action(Evidence)` / `allocated_core_hours` / `batch_is_exactly_activated` / `sacct_terminal_states` 的调用点**只在 `tests/test_evidence_gate_and_cost.py`**；`scripts/` 内仅自身定义（`evidence_gate.py:66,115,145`；`batch_cost_settlement.py:37`），**无任何生产调用方**，也无 `Evidence(` 的生产构造。`docs/65_repo_layout.md:196` 自己也写着"Evidence 适配器（真实证据填充） → NextAction"——**该适配器不存在**。
- **采集侧未按方案改造**（事实陈述，非本四对象缺陷）：`scripts/wp_production/submit_hpc_batch.py:201-202` 现为
  `"sacct -n -X -j %s -o JobIDRaw,State,ExitCode -P" % job_id` —— **未加 `AllocCPUS`/`ElapsedRaw`**（方案要求"，且 `-X` 会把数组元素**聚合**成一行（仓内真实捕获即 `3747724_[0-2]` 单行），**拿不到精确元素 id**，与 `allocated_core_hours` 的"精确数组元素 ID 匹配"前提冲突。
- **解析器与采集器格式冲突**：`batch_cost_settlement.parse_sacct_rows` docstring（:25）写 *"Parse ``sacct -P -n`` output with a header line"* —— `-n` 的定义恰恰是**不输出表头**。**实测**：把无表头的 `-n` 输出喂进解析器 ⇒ 第一**数据行**被当成字段名，N 行塌成 **1 行垃圾 dict**（`{'3738029_0':'3747714_0','COMPLETED':'COMPLETED',...}`），随后 `row["AllocCPUS"]` → `KeyError`。⇒ 该 parser 只能吃"有表头"的输出，与现有 `-n` 采集器**不兼容**（fail-closed，但会崩不是拒）。
- **已记录的既有缺口**：记忆 `0mvpe9rxt`（2026-10-26）已载"权威门只在 5 处中的 2 处被调用；**提交器 `submit_hpc_batch` 本身不查门、没有最后防线**；P1 的提交前这一半尚未落实"，并建议"让任何未来新打包路径都无法绕过"。⇒ **本项属已知缺口的延续，不是本次新发现**；`Evidence` 适配器与其"最后防线"接线仍缺。

---

## F. 真缺陷 / 缺口清单（去重后 14 条，按"file:line + 触发条件 + 后果 + 建议"）

| # | file:line | 触发条件 | 后果 | 建议 |
|---|---|---|---|---|
| 1 | `evidence_gate.py:142,164` | 状态字符串**不在**那 5 个非终态里（含拼错、未知名、`PENDING+` 等截断形态） | **fail-open**：被判为终态 ⇒ `terminal_states_verified=True` ⇒ 对未知/仍活动的作业下终态裁决；与 `:149-150` docstring "unknown states return {}" 直接矛盾 | 改**白名单**终态判定，复用 `submit_hpc_batch.TERMINAL_STATES` |
| 2 | `evidence_gate.py:142` vs `submit_hpc_batch.py:73-74` | 同一事实两套词表 | **字面 `CANCELLED` ⇒ 永久 `WAIT`**（Slurm 语义与本项目 `3747724` 历史均认定它是终态）；`CANCELLED by 59540` 反而被判终态 ⇒ 两条现实形态处理**相反** | 消灭第二份词表 + 归一化 `split(" by ")[0].rstrip("+")` |
| 3 | `evidence_gate.py:101,137` | `tasks/<NAME>/<SLOT>__<seed>` 的 **SLOT 错配**（如两条都写 `EC`） | 三方核对全绿（实测 `True`）⇒ **跑错化学体系而不报错**；当前真实包 slot 正确故潜伏 | slot 纳入键元组（activation 的 `_slot` 现成）；`pkg_keys` 取 `parts[2].split("__")[0]` |
| 4 | `evidence_gate.py:63` | 构造 `Evidence` 时**省略** `batch_tasks_exactly_activated`（旧骨架/新 adapter 漏填） | **静默绕过**唯一新增的提交前红线，且 `next_action:67` 首分支读它 ⇒ 外观是"正常放行" | 删默认值（或默认 `False`）；改由 `from_artifacts()` 内部调用 `batch_is_exactly_activated()` 派生 |
| 5 | `evidence_gate.py:66-93,115,145` + `batch_cost_settlement.py:37` | 需要生产侧把证据填进 `Evidence` 时 | 三个权威计算函数**无生产调用**；12 个 bool 是**无一致性守卫的第二份副本**（无 `__post_init__`）⇒ 副本可独立漂移且不报错（教训 `0mvp9qk7j` 变体） | 收敛唯一构造口；把 bool 由函数派生而非人工/适配器填写 |
| 6 | `batch_cost_settlement.py:48,60-61` | 行缺 `AllocCPUS`/`ElapsedRaw` 列（仓内真实捕获格式即缺 `JobIDRaw`/`ElapsedRaw`）或值非法 | **`KeyError`** / 原生 `ValueError`（非 `MISSING` 项目消息）⇒ 按 docstring 语义 `except ValueError` 的上游**捕不到** `KeyError`，结算路径崩而非受控拒绝 | 显式校验必需列与格式，统一抛项目消息/专用异常 |
| 7 | `batch_cost_settlement.py:62-63` | 出现 `AllocCPUS=0`（**取消前未运行**的真实形态，见 `3747724`） | 被判"非法费用字段"**拒绝结算** ⇒ 该腿永远拿不到 `cost_settled=True`；而历史账本把同一形态按 **0 CH 计**入账（`agent_ledger_verify_20261025/REPORT.md:59`）⇒ 口径冲突、取消腿无终态 | 区分"记录缺失（MISSING，拒绝）"与"记录存在但分配为 0（合法 0 CH）"；`AllocCPUS=0 and Elapsed=0` 应记 0 并标注理由 |
| 8 | `batch_cost_settlement.py:68-82` vs `:61` | 采集侧给出 `Elapsed`（pretty 形态，仓内真实列名） | `allocated_core_hours` **不用** `parse_elapsed_raw` 而直接 `int(row["ElapsedRaw"])` ⇒ 该解析函数**只有测试调用**、真实 pretty 形态永远走不到它（直接 `KeyError`）；另 `"1--2:03:04"` → `79384`（接受负数分量）、`"1-2"` → 解包 `ValueError` | 让计费路径复用 `parse_elapsed_raw`（或规范列名）；拒绝任何负数分量 |
| 9 | `evidence_gate.py:137` | tasks.txt 只有 2 个空白分隔 token 且其一格式畸形（无 `/` 或无 `__`） | `IndexError`（**崩溃**而非返回 `False`）；调用方 `if batch_is_exactly_activated(...)` 异常退出 | 解析前断言 `len(parts) >= 3 and "__" in parts[-1]`，否则 `return False` |
| 10 | `batch_cost_settlement.py:24-34` vs `submit_hpc_batch.py:202` | 把现有 `-n -X` 采集输出喂进 `parse_sacct_rows` | 首数据行被当表头 ⇒ N 行塌成 1 行垃圾 dict ⇒ `KeyError`；`-X` 还使数组元素聚合（无精确元素 id） | docstring 与实现对齐（要求带表头输出），采集侧改为 `-P` 带表头 + 去掉 `-X` + 加 `AllocCPUS,ElapsedRaw` |
| 11 | `work/_evidence_gate_red.py:3-4,70,76-80` | 运行该脚本；或运行期间被硬杀/断电/并行会话读取 | docstring 与 `bd754f8` 提交信息均称"不动盘上文件/改副本文件"，实现**真改生产文件**（`:70`）；finally 无 sha256 自校 ⇒ 硬杀即留下被削弱的守卫且无痕迹 | 改在副本目录篡改；或还原后强制 sha256 自校；修正两处文字 |
| 12 | `work/_evidence_gate_red.py:48-51` | 跑 RED 用例 4 | 替换谓词实测使**父行仍 SKIPPED**，红因是 `.b`/`.e` 撞完备性检查 ⇒ **"父行双计"未被实证**（证明的是另一条守卫） | 重写篡改使父行真的进入计费（如放宽为"id 前缀匹配"），再断言测试红 |
| 13 | `tests/test_evidence_gate_and_cost.py:130-142,145-149` | 未来重构 `:126`/`:138` 的 key 比对 | 三方核对与 `pkg_keys == act` **无测试钉住**（3 行夹具被 `len(tasks)!=2` 先拦）；§B 的次序优先级、"无路径回 SUBMIT_ONCE"亦无负测 ⇒ 守卫可被改坏而 16 项仍绿 | 补：2 行 `tasks.txt` 且 name/seed 错配 → `False`；混入 + `submitting`/`submitted` → `HOLD`；非 `absent` 状态不得 `SUBMIT_ONCE` |
| 14 | `tests/test_evidence_gate_and_cost.py:26,30-34` → 迫使 `tests/test_wp2_cost_semantics.py:117-123` 放宽 | 运行该测试（不加 `PYTHONDONTWRITEBYTECODE=1`） | 在**仓库内** `scripts/wp_production/` 生成 `__pycache__/*.pyc`（`.gitignore:7` 已忽略；已见 `batch_cost_settlement.cpython-310.pyc` mtime 2026-10-27 13:11:17），并迫使既有不变量从"精确 85"改成"排除 `__pycache__` 后 88" ⇒ **把守卫放宽以容纳副作用**（"自测不得写仓库"lesson `0mvnum9na` 同族） | 测试用 `tempfile.mkdtemp()`/`importlib` 不落盘（`PYTHONDONTWRITEBYTECODE=1` 或在 `pytest.ini` 设 `addopts`），并把 85→88 的放宽收回为"排除后仍精确"的更硬断言 |

**另有两处非缺陷但需知会**：① `Evidence` 第 4 条 QC 语义（§A-4）——字段名 `qc_results_complete` 歧义（"每腿都有判定" vs "都通过"），反向误映射会让**失败腿永远跑 QC 而永不结算**，且无处可检；建议改名 `qc_verdicts_present` 或加显式 `qc_all_passed`。② §B 的 `HOLD` 无诊断字段。

---

## G. 未验证 / 无法确定（如实声明）

1. **`sacct` 是否可能输出小数/异形 `AllocCPUS`**：无法确定——缺一次真实超算侧 `sacct -P -o AllocCPUS` 原始输出（本任务禁止调超算）。仓内可得的两份捕获（`work/_recovery_sacct.txt` 42 行、测试夹具）均为整数。
2. **用户 2026-10-27 方案原文中 `Evidence` 骨架段落**：无法核——全仓 `*.md` 对 6 个字段名 0 命中（§E-1）；以 Lead 简报前提为准。
3. **`work/_evidence_gate_red.py` 的实跑结果**：无法确定——按简报**未运行**（它临时改生产文件）；本报告对 RED 的结论**全部**来自静态阅读 + 对替换谓词/源码的独立实测（§D）。
4. **远端超算实况**（真实 sacct/Slurm 状态词形、`-o` 列宽是否产生 `+` 截断）：无法确定——无桥输出留档可核。
5. **RED 用例 1/2/3/5 是否忠实**：未逐一复算替换谓词语义（仅核 `old` 存在性与用例 4 的谓词）；用例 5（`if False:` 后落回 `absent` → `SUBMIT_ONCE`）经静态推演成立，未实跑。
6. **本报告未运行全量 pytest**（按简报只允许那一个文件），故"16 项绿"之外的测试面（如 §F-14 涉及的 `tests/test_wp2_cost_semantics.py`）当前是否绿，未核。

## H. 证据出处

- 代码/测试/RED 脚本：四个对象的 sha256 见 §0；行号均按 §0 快照。
- 允许的测试运行：`.\.venv\Scripts\python.exe -m pytest tests/test_evidence_gate_and_cost.py -q -p no:cacheprovider` → `16 passed`，`EXIT=0`（附 `PYTHONDONTWRITEBYTECODE=1`）。
- 实测探针：全部为 `python -c` 单行（`PYTHONPATH=scripts/wp_production`，**未写任何文件**）——覆盖 status 穷举、`SACCT_NON_TERMINAL` 状态矩阵、`allocated_core_hours` 五类输入、`parse_elapsed_raw` 八类输入、`parse_sacct_rows` 无表头输入、`batch_is_exactly_activated` 五种 tasks.txt（含 slot 错配、畸形）——均在报告中随结论列出。
- 仓内真实数据：`work/_recovery_sacct.txt:1,39`（表头形态与 `3747724_[0-2]|CANCELLED by 59540|0:0|00:00:00|0`）；`config/recovery_start_activation_v1.json:10-25`；`work/dol_ec_recovery_v1/tasks.txt:1-2`；`outputs/physics_completion/ensembles/production_ensemble_candidates.csv`（`source_kind=p4v2_screening_v1_start` 恰 2 行：DOL/EC × `p4_02_ring_pucker_twist`；全表 121 行）。
- 采集侧/基线：`scripts/wp_production/submit_hpc_batch.py:73-74,201-216`（sha256 `3fb8037c...`）；`git log`：HEAD `e030bfa` → `bd754f8`，`git show --stat bd754f8`。
- 项目教训/记忆：`0mvp9qk7j-519dd9fa9d874bb5b12b3ac9f5`（副本一致性守卫/RED 判读）、`0mvnum9na-f66e04c873b84791933e4d4aa1`（自测不得写仓库）、`0mvpe9rxt`（提交器不查门、最后防线未落实）、`0mvnjx6fo`（同类常量多处副本）。
- 历史口径：`docs/handoffs/four_state_recovery_20261023/FOUR_STATE_STARTING_LEDGER_20261025.md:44,49`、`agent_ledger_verify_20261025/REPORT.md:59`（`3747724_[0-2]` 按 0 CH 终态入账）。
- 模块登记（仓内对 `Evidence` 的唯一描述）：`docs/65_repo_layout.md:196-197`、`scripts/wp_production/README.md:101-102`。

---

**35 项检查 12 成立 22 不符**（不符中含 5 项"部分成立"；另 **1 项无法确定**；22 项不符去重后为 **14 条真缺陷/缺口**，见 §F）。
最需立即处理的 4 条：**F-1 未知状态 fail-open**、**F-2 `CANCELLED` 永久 WAIT 与双词表矛盾**、**F-3 slot 盲**、**F-4 第 8 条防线默认 `True` 静默绕过**。