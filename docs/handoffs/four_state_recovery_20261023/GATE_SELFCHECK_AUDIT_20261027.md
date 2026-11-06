# 机器闸门的自证风险审计（2026-10-27）

> 触发：`b0e7b01` 修掉 H2 包 `--check` 的自证盲区后，**同一标准必须应用到全部机器闸门**——
> 否则我只是修好了一个点，而面上仍是盲的。

## 0. 判据（本轮提出的分类）

| 类型 | 特征 | 风险 |
|---|---|---|
| **A. 自证（危险）** | 只比对**同一份产物内**的两个字段（如 `manifest.reservation` vs `manifest.cap`） | **读不出被测物错了**；本轮在 H2 包上实证 |
| **B. 重算式（安全）** | 从**输入重新计算**，与磁盘产物**逐字节比对** | 输入变 ⇒ 产物对不上 ⇒ 变红 |
| **C. 输入哈希锚定（最强）** | 既重算，又比对**保存的输入哈希 vs 重算的输入哈希** | 能抓到「上游变了但产物看起来自洽」 |

## 1. 逐个生成器 `--check` 的核对结果

| 生成器 | 类型 | 证据 |
|---|---|---|
| `build_strict_recovery_manifest` | **B** | `:561-581` `build_rows()` 重算 → `disk != buf.getvalue()` |
| `build_coverage_reviews` | **B** | `:446-463` 同上；`--help` 自述「READ-ONLY: recompute in memory and byte-compare」 |
| `build_production_ensemble_aggregator` | **B** | `:768` 同上；另有 `checked()` 校验登记摘要 |
| `build_plan_compliance` | **C（最强）** | 重算 + **`:1178-1181` 比对 `runtime_input_sha256` / `scientific_ledger_sha256`** + `stale` 标志 |
| **H2 包 `_h2_build_package --check`（修复前）** | **A（危险）** | 只做 `manifest.reservation > manifest.cap`；`b0e7b01` 已改为**穿过真实提交器解析** |

**只读性核对**：四个生成器的 `check()` 函数体内**均无写操作**（`write_outputs`/`write_text`/`open('w')`）——确认只读。

## 2. 实证：`build_plan_compliance --check` 能抓到上游变更（RED PROVEN）

`work/_input_hash_red.py`（在**副本**上篡改，绝不动真实产物）：

| 篡改（副本内） | `--check` |
|---|---|
| 保存的 `runtime_input_sha256` 翻转 | **exit=1 RED-OK** ✅ |
| 保存的 `scientific_ledger_sha256` 翻转 | **exit=1 RED-OK** ✅ |

⇒ **证明它属于类型 C**：它比的是「**保存的输入哈希 vs 重算的输入哈希**」，
因此能抓到「上游科学证据变了、但产物自身仍然自洽」这种最难发现的情形。
**这正是 H2 包原先缺少的东西。**

## 3. H2 包现在的归属

修复后 `_h2_build_package --check` 已从 **A** 变为**「穿过真实下游解析」**：
它调用 `submit_hpc_batch.submission_resources()` 解析包，再断言 profile 名 / 墙钟 / cap /
`declared_task_cores == profile.cores` / `committed + reserved ≤ cap` / `manifest.profile == 解析结果`。
RED 3/3（profile 改回旧值、`job.inp` 加 `Opt`、删 `--partition` 各报 STALE）。

## 4. 结论与后续

- **面上没有发现第二处类型 A 的闸门**——其余四个生成器都是 B 或 C。
- **`build_plan_compliance` 是标杆**：它有输入哈希锚定 + `stale` 标志，可作为其他生成器的参照模板。
- **本轮不新增闸门**：因为没有发现新的漏洞，**不为了「做了点什么」而制造改动**。

## 5. 证据出处

- 只读性核对：本轮对四个 `check()` 函数体的正则扫描（写操作 = 无）
- RED：`work/_input_hash_red.py`（挂在 `work/`，gitignored，按纪律不入库，以本文留痕）
- 相关前序：`b0e7b01`（H2 包防自证）、`0mvp5lzc`（方法论 lesson）