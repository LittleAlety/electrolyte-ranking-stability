# REVIEW_REV2（最终字节 + d483 定向更正）：rev2 有界收尾核收

> **版本沿革**：本文件先针对 `840a6b18`，后改绑最终入口 `47f8e303`；现按定向更正补入 **d483 引用载体已找到 / 结果字节 UNVERIFIED**。**不据此判"五项全过"**，逐项按当前字节裁定。

- **对象**：`work/coverage_fix_20261106/rebuild_run_rev2_20261107/`
  - 入口 `replay_four_versions_v2.py`：**9,956 B / `47f8e3036abd938c1e9206f9e29265b83982dcbb809cd7effcf9aa03547cebf4`**
  - 结果 `REPLAY_RESULT.json`：**76,990 B / `19f02168a0d9cf30b602e9fc663530bb73cff3e6c0097c5259cdd2c90609f49f`**
  - 外部绑定 `REPLAY_RESULT.sha256`：86 B / `fed22c75…`，内容与结果 SHA 一致
  - `CLOSURE_REPORT.md`：2,901 B / `2b93e16c…`；`RELEASE_APPLICATION_FINAL_v2.md`：2,955 B / `6116333c…`
- **d483 载体**：`work/lead2_ledger_v4_20261104/round23_an_closure_20261106/RELEASE_APPLICATION_FINAL.md`，**5,063 B / `ecfb1ef7…`**，**第 38 行**
- **旧结果**：`rebuild_run/REPLAY_RESULT.json` 6,387 B / `213b7a1b…`
- **时间**：2026-11-07 01:2x (+08:00)。未改候选/正式表/科学规则。

## 0. 执行状态

**原目录入口未重跑**（避免改写 `19f02168`）→ 原目录层为「**产物核验，非独立重放**」。
此前已在**仓库外副本**用同一脚本字节实跑：正跑 exit 0；负测 **4 / 3 / 2 / 5**（子步骤失败为真实 `SyntaxError`）。本次更正未改动入口/结果/证据，故该副本证据仍适用。

---

## 1. 逐项结论

| # | 项 | 状态 | 依据 |
|---|---|---|---|
| 1 | `d483` 引用载体 / 结果字节 | **载体已找到；结果字节 UNVERIFIED** | 载体 = `round23.../RELEASE_APPLICATION_FINAL.md` 第 38 行（`REPLAY_RESULT.json = d483f76a30db…`），文件 `ecfb1ef7…`/5,063；现 `rebuild_run/REPLAY_RESULT.json` 已是 `213b7a1b…`，**d483 旧字节未保留**，生成方式未证明 |
| 1' | 此前"d483 只在本轮新文档 / 旧申请没有该引用" | **撤回（我检索范围过窄）** | 我当时只搜了 `coverage_fix_20261106/` 与 `coverage_review_20261106/`，未覆盖 `lead2_ledger_v4_20261104/round23.../`。`coverage_review_20261106/RELEASE_APPLICATION.md`（`7b5e2cf6…`）确实不含 d483，但**它不是唯一旧申请** |
| 1b | 旧申请标 `HISTORICAL_SUPERSEDED` | **CLOSED（现在成立）** | 载体文件第 1 行现有 `HISTORICAL_SUPERSEDED（2026-11-07）`；此标记是在我上一轮检查之后追加的（当时确为 0 命中） |
| 2 | 外部绑定 `.sha256` + 申请文本；结果不内嵌自哈希 | **CLOSED（一致）/ OPEN（低，维护）** | `.sha256` 与结果一致；申请绑定 19f02168/76,990；结果 JSON 无 self 字段；**但入口不生成 `.sha256`**（手工程序），脚本 docstring 仍称"binds its own exact SHA/bytes" |
| 3 | `dedup_pairs.csv` 入写集/备份 | **CLOSED** | 申请第 6 项＋备份 1–8；正式 `4d294544…`/14,955，四版同 sha |
| 4 | 依赖 145 件 before=after | **CLOSED** | 145/145 相等；145 条全部在盘且哈希匹配；`formal_unchanged=true` |
| 5 | fail-closed 2/3/4/5，负测真实 | **CLOSED** | 副本实跑：4 / 3（真实 `SyntaxError`）/ 2 / 5，均留 `FAILURE.json`；正跑 exit 0 |
| 6 | evidence 14 件相对路径、B/C 6/6 | **CLOSED（碰撞已修）/ OPEN（低，pycache）** | 14 键唯一、B/C 并存、索引 6/6；1 件仍是 `__pycache__/*.pyc` |
| 7 | 四版 counts/labels/weights/dedup_pairs | **CLOSED** | 45/2/1、44/3/1、43/4/1、43/4/1；labels `c21003f5`/`280d78ca`/`2458f0af`；weights `201e1954`；dedup_pairs `4d294544`，由 `out/` 独立重算一致 |
| 8 | B/C 条件回归 OPEN；未发布 | **OPEN（如声明）/ 未发布 CLOSED** | 仅索引 6/6；正式表六件 SHA 未变 |

---

## 2. 结果（产物核验）

| 版本 | counts | labels | weights | dedup_pairs |
|---|---|---|---|---|
| disk | 45/2/1 | `c21003f5…` | `201e1954…` | `4d294544…` |
| shared | 44/3/1 | `280d78ca…` | `201e1954…` | `4d294544…` |
| old | 43/4/1 | `2458f0af…` | `201e1954…` | `4d294544…` |
| v4 | 43/4/1 | `2458f0af…` | `201e1954…` | `4d294544…` |

---

## 3. Findings（按定向更正）

**R1（已更正）｜d483 的结论是"载体找到 / 字节 UNVERIFIED"，不是"不存在"**
载体在 round23 申请第 38 行；d483 的**旧结果字节未保留**（现文件已是 213b7a1b），因此"该哈希如何生成、当时结果是否一致"**无法核实**。→ 记为 **UNVERIFIED**，不得据此判"五项全过"。
**我上一轮的错误**：把"只搜了两个 coverage 目录"写成"全仓检索"，属于**检索口径过窄却下了全称结论**（与"NOT_FOUND_UNDER_"同一族错误）。

**R2（低-中）｜外部绑定是手工维护**
`.sha256` 与结果一致，但入口不写它；重跑若产生不同结果，`.sha256` 会停在旧值（比对可发现，但不是自动 fail-closed）。脚本 docstring 仍称自绑定，与最终口径不一致。

**R3（低）｜evidence 仍含 `__pycache__/*.pyc`**（14 件中 1 件）。

---

## 4. 结论（不宣称"五项全过"）

- **成立**：dedup_pairs 入写集；145 依赖 before=after；fail-closed 2/3/4/5（真实负测）；四版结果与 labels/weights/dedup_pairs；外部 `.sha256` 与结果一致；`HISTORICAL_SUPERSEDED` 现已在载体中。
- **UNVERIFIED**：`d483` 对应的结果字节/生成方式（旧字节未保留）。
- **残留**：`.sha256` 手工维护；docstring 仍称自绑定；evidence 含 pyc；B/C 条件回归 OPEN。
- 未发布，正式表未动；原目录入口未重跑（产物核验，非独立重放）。

*本报告由独立非作者核收者生成；未改候选/正式文件/科学规则。*
