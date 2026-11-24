# SCIENTIFIC_HOLD —— DMC|LiM_2plus 16 核试验本轮停止（2026-10-31）

> 依用户派单：「**Lead：仅在 A 未发 SCIENTIFIC_HOLD 时实施**」。Agent A（t1）于 2026-10-31 12:59 在
> `work/exp_line20261031/SCIENCE_ACCEPTABILITY_AUDIT_20261031.md` **首行写下 `SCIENTIFIC_HOLD`**。
> ⇒ **Lead 的五项生产改动（t3–t6）与提交一律停止**；本轮**未做任何生产写入、未提交作业**。

## 1. A 的判定与其性质（它自己写明的）

- 判定：**"不能形成正式证据（就当前冻结形态而言）"** → 首行 `SCIENTIFIC_HOLD`。
- 性质（A 原话要旨）：阻塞项**不是**科学身份错误、**不是**几何不合法、**不是** EC 式取证缺失，而是**验收链的登记缺口 + 种子命名**；三项字节/身份/机理结论**均为正向**。⇒ **解锁不需要重算、不需要新授权**，只需 Lead 在 t5/t6 补三条登记与命名。

## 2. Lead 的独立复核（未采信转述）

| A 的断言 | 我的复核 | 判定 |
|---|---|---|
| 排除集 `_rejected_probe_members()` **按 member_key 整键剔除**，`replaces_cancelled_job` 分支会把 `tasks/<name>/<slot>__<seed>` 转成整键 | 逐行读 `build_coverage_reviews.py:122-151`；`work/hpc_torsion_probe_v1_batch2_fragmentfix_20261022/manifest.json` 的 `replaces_cancelled_job=3747724`、`requested_tasks` 含 `tasks/DMC/LiM_2plus__tors_7_0_1_2` ⇒ `DMC\|LiM_2plus\|tors_7_0_1_2` **整键进入排除集**（`rejected` 两条只涉及 EC） | **属实** ⇒ 新腿**绝不能复用 seed `tors_7_0_1_2`** |
| 起点处第 1 轮两项可判量均超冻结阈值 ⇒ 必然 ≥2 轮 ⇒ `Energy change` 必打印 | 起点产者末表 `work/wp2prod/DMC/LiM_2plus/superseded_numfreq/DMC_LiM_2plus.log:21859/:21860` = `RMS gradient 0.0000271576` / `MAX gradient 0.0000855657`；对冻结 TolRMSG `8e-6` / TolMaxG `3e-5` ⇒ **3.39× / 2.85×** | **属实** ⇒ 比我先前"概率高"的判断更强：这是**推导**，不是估计 |
| 我此前的说法"`starts` 已非空、唯一缺件是 computed 成员" | 只在"**R7 今天已被旧 seed 满足**"这一层成立；但要让 `R3`（computed 成员）成立，新腿必须**能进入 `members`**（候选表一行、`member_role` 以 `recovery_v1` 开头、且 **member_key 不在排除集内**）——而**复用旧 seed 会触雷** | **A 的表述更完整；我的表述不充分**，以 A 为准 |

## 3. 三项解锁动作（A 的建议；**0 CH，无需新授权**，但按派单需用户放行）

| # | 动作 | 依据 | 代价 |
|---|---|---|---|
| **A-1** | 让本包**被导入器发现**：包移到 `work/hpc_<name>/` ＋ manifest 给非空 `members`（无需改导入器代码） | `import_ensemble_structures.py:154-155/158/163` 三个 glob 皆不匹配现路径 | 0 CH（本线写入面） |
| **A-2** | 候选表登记一行，`member_role=recovery_v1_start`，**seed 用新键**（例如 `tors_9_*`，或显式 `source_kind=p4v2_screening_v1_start` 的新 seed） | `build_coverage_reviews.py:266-272`（进 members）+ `:143-151`（旧 `tors_7_0_1_2` 整键被排除） | 0 CH（**tracked** 文件，Lead 写） |
| **A-3** | 明确 R7 的**证据强度**取向：接受"旧 `tors_7_0_1_2` 提供的 registered_starts（其来源是被取消并替换的探针）"，还是要求覆盖审以**本次新起点**命名搜索范围（那 seed 必须满足 `:104-105`） | A §2.3 末段；用户 2026-10-27 禁止"把 P4/v2 起点改名冒充扭转家族" | 0 CH（**口径选择**，需裁决） |

**注意**：A-1/A-2 都是 **0 core-hour 的登记与命名**，不是新计算；A-3 是**科学口径选择**，属用户裁决面。

## 4. 本轮的实际状态（可核查）

| 项 | 值 |
|---|---|
| 提交 | **0**；包 `submission_gate=HOLD`；无 `submission_journal.json`、无提交锁 |
| 生产面写入 | **本轮 0**（t3–t6 未执行；t7 的账本修补发生在上一轮且已审议） |
| 正式记录 | **历史协议 45/48**（未宣称 46/48，未宣称严格 48/48） |
| 队列 / 在飞 | 空 / 0（Agent B 三次实测） |
| 费用 | 最保守口径池余 389.9416667；预留 64 后 325.9416667 ⇒ **64 CH 可用**（t2/t7 已证） |

## 5. 需要用户裁决的一件事

派单把 Lead 的实施**条件在"A 未发 SCIENTIFIC_HOLD"**上；A 发了 HOLD ⇒ 我已停止。
但 A 同时说明：**阻塞是登记/命名缺口，解锁不需要重算或新授权**。
⇒ 请裁决：**(a)** 放行上面 A-1/A-2（0 CH 的登记与命名）并在完成后**重跑 A 的科学门**；还是 **(b)** 本轮到此为止、把该态继续留在 limited。
（若选 (a)，A-3 的证据强度取向也需一并指定；我不会自行选定。）