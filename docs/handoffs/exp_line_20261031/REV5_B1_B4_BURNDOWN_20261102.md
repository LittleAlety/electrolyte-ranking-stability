# rev5 接收器 B1–B4 核销记录（2026-11-02）

**身份**：本会话现为 rev5 负责人（用户 2026-11-02 明确指派）。
**写入面**：`work/dmc_staged_receiver_v5.py`、`work/test_dmc_staged_receiver_v5.py`、`work/_dmc_emit_staging_record.py`、`work/dmc_attempt_registry/**`、`work/dmc_rev5_freeze/**`。
**未触碰**：`scripts/**`、`outputs/**`、正式 labels/weights/coverage、`work/dmc_staged_receiver.py`（rev4 原件）、`work/test_dmc_staged_receiver.py`（rev4 测试原件）。

---

## 一、四项 blocker 全部闭合

| # | 缺口 | 状态 | 关键证据 |
|---|---|---|---|
| **B1** | 无密封 attempt 登记文件，生产入口从未在真实证据上跑通 | **CLOSED** | 见 §2 |
| **B2** | 发射器仍 import rev4、调测试入口 | **CLOSED** | 见 §3 |
| **B3** | 无任何测试覆盖 rev5 | **CLOSED** | 见 §4 |
| **B4** | 文档过度声称：块头声明的原子数未被解析 | **CLOSED** | 见 §5 |

---

## 二、B1：密封登记 + 真实证据端到端

**密封文件**：`work/dmc_attempt_registry/v1.json`（schema `dmc_attempt_registry/v1`）
**出带摘要**：`work/dmc_attempt_registry/REGISTRY_FREEZE.json` → `registry_sha256 = c13e43c35b77d9ca…`

**为什么这才叫"密封"**：摘要不在登记文件旁边，而在独立的冻结清单里；调用方必须从冻结清单取摘要。这正是 2026-10-31 裁定要求的「期望值须来自调用者在同一次请求里无法替换、且来源已被独立审定的位置」。

**封存前做了什么**（不通过则拒绝封存）：
- 逐项重算 7 个 `stage_sha256`，与盘上证据字节比对
- 结果：**7/7 全部吻合**（opt_input / opt_log / opt_final_xyz / freq_input / freq_log / freq_geometry / freq_hessian）
- 起点几何 `a2e5c861ef0afb50…` 与登记值一致

**真实证据端到端运行**：

```
receive_attempt(EV, attempt_id="3894976_0_0",
                registry_path=.../v1.json, registry_sha256=<来自冻结清单>,
                recovery_path=RECOVERY.json, recovery_sha256=64e4df96…,
                start_geometry=.../M_plus__adj_Rk1/geom.xyz)
  -> status        : qc_passed_candidate_staged
  -> trust.boundary: sealed_registry
```

---

## 三、B2：发射器改走生产入口

**改动**：
- `from dmc_staged_receiver import ... receive` → `from dmc_staged_receiver_v5 import receive_attempt, register, ReceiverRefusal`
- 删除调用方自带的 `expected_hashes` / `expected_identity` / `registered_starts` / `expected_member`（这些正是 rev5 设计上拒绝的"同一次调用里替换期望值"）
- 只保留 `attempt_id` + 路径 + **出带摘要**
- 摘要来自 `REGISTRY_FREEZE.json`，并**先核对冻结清单与盘上文件一致**，不一致即 `REGISTRY_DIGEST_MISMATCH`

**真实运行**：
```
appended: False   reason: duplicate_member
status: qc_passed_candidate_staged
trust.boundary: sealed_registry
```

`duplicate_member` 是**正确的幂等行为**——该成员已由 rev4 时代写入账本（见 §6 遗留项）。

---

## 四、B3：测试覆盖 rev5

**新增** `work/test_dmc_staged_receiver_v5.py`（11 项，全绿）：
- 真实证据经生产入口通过并打戳 `sealed_registry`
- 未密封记录被 `TRUST_BOUNDARY_UNSEALED` 拒
- 伪造登记摘要被 `REGISTRY_DIGEST_MISMATCH` 拒
- 伪造 recovery 摘要被 `RECOVERY_DIGEST_MISMATCH` 拒
- 未登记 attempt_id 被 `ATTEMPT_UNREGISTERED` 拒
- 起点换错被 `START_LABEL_MISMATCH` 拒
- 密封记录可登记（`appended=True`）
- B4 三条：声明的原子数不符被拒 / 无声明仍接受 / 声明相符仍接受

**回归**：rev4 的 49 项测试**仍全绿**（rev4 行为未变）。三者合计 **71 项全绿**。

---

## 五、B4：块头声明的原子数现在真被解析

**旧代码的缺陷**：`coordinate_blocks` 注释声称 "exactly `expected_atoms` four-field atom lines"，但**块头声明的数字从未被读**。复审 P10d 实测：头写 99、实带 13 → **被接受**。

**修法**：解析 marker 之前的最后一个非空行，若是纯整数则作为声明数；与实际携带原子数比对，不符则 `DECLARED_ATOM_COUNT_MISMATCH`。

**验证**：

| 用例 | 修复前 | 修复后 |
|---|---|---|
| P10d 头写 99 / 带 13 | **接受** | **拒收** `DECLARED_ATOM_COUNT_MISMATCH` |
| 无声明（真实 ORCA 格式） | 接受 | **仍接受** |
| 声明 11 且带 11 | 接受 | **仍接受** |
| 真实 ORCA 日志（两份） | 接受 | **仍接受**（11 原子解析正确） |

**为什么可以不强制声明**：真实 ORCA 在 `CARTESIAN COORDINATES (ANGSTROEM)` 之后打的是分隔线、**不打原子数**。把"必须声明"写成硬要求会误拒所有真实日志。

**同时翻转了那条断言旧缺陷的测试**（原文注释就写着 "If t3 chooses to validate the header instead, this test flips"——t3 是本任务编号）。原 1 条拆成 3 条：强制 / 无声明接受 / 相符接受。

---

## 六、对抗语料回归（57 例，无回归）

| 类别 | 结果 |
|---|---|
| `baseline` 正向对照 | **PASS**（仍成立） |
| 已闭合项 n3/n7/n9/n12/n12b/n17 | **仍拒收**，码不变 |
| f4/h4/i6 | **仍拒收** |
| a8_forged_registry | 在 `receive()` 层仍 PASS（**按裁定属设计外**） |
| l1–l4 合法外形 | **仍拒收** = 未消解的**误拒风险** |
| n14/n16/n18 | **exit=1，未测定**（harness 与 rev5 记录形状不符），**不记"通过"** |

---

## 七、遗留项（如实记录，未擅自处理）

### 7.1 账本 schema 是 v2，rev5 期望 v3

`work/dmc_staged_staging_ledger.json` 现为 `dmc_staged_staging_ledger/v2`（rev4 时代写入），而 rev5 的 `LEDGER_SCHEMA = "dmc_staged_staging_ledger/v3"`。

`register()` 读账本时**沿用文件已有 schema**（`doc["schema"] = loaded.get("schema", LEDGER_SCHEMA)`），所以旧账本能继续被读写。**但这是一个显式的迁移决策点**，不该由我单方面决定：

- 选项 A：保留 v2 直到正式迁移（当前行为）
- 选项 B：写迁移器把 v2 → v3 并保留原文件

**我没有动它**。请裁定。

### 7.2 rev5 字节已变，旧复审结论需重绑

复审件 `REV5_INDEPENDENT_REVIEW_20261031.md` 绑定的 rev5 sha 是 `628a2cdf…`；因 B4 修复，现在是 **`dd88c407e994769dc29d461293b3266b`**。

按复审自己的声明「下述结论只对这几个字节成立；其中任何一个变化，本复审即作废」⇒ **需就新字节重新独立复审**。我作为执行方**不能自我复审**。

### 7.3 出带摘要的独立性

`REGISTRY_FREEZE.json` 由我（执行方）生成。严格意义上「独立审定」应由**另一个会话**复核该摘要后方可作为锚点。当前状态：**自洽检查成立，独立审定待办**。

---

## 八、冻结清单

`work/dmc_rev5_freeze/REV5_FREEZE_AND_BURNDOWN.json`

| 角色 | 文件 | SHA256 |
|---|---|---|
| 接收器 rev5 | `work/dmc_staged_receiver_v5.py` | `dd88c407e994769d…` |
| 接收器 rev4（保留） | `work/dmc_staged_receiver.py` | `32501b7185d61d7a…`（未变） |
| 测试 rev4（保留） | `work/test_dmc_staged_receiver.py` | `8dac1aa061da31aa…`（未变） |
| 测试 rev5 | `work/test_dmc_staged_receiver_v5.py` | `a92d1cb4d7835da7…` |
| 发射器 | `work/_dmc_emit_staging_record.py` | `f6082fc687b70035…` |
| 密封登记 | `work/dmc_attempt_registry/v1.json` | `c13e43c35b77d9ca…` |
| 登记冻结清单 | `work/dmc_attempt_registry/REGISTRY_FREEZE.json` | `ea3c6c209aaa198c…` |

---

## 九、EC 四条候选现在可以走这个入口吗？

**还不能直接走**——当前密封登记只含 DMC 的 `3894976_0_0`。EC 四条需**各自的登记记录**（state_key / geometry_label / start_sha / protocol_version / identity / 七项 stage hash）。

好消息：EC 的七项 stage hash **已在 `work/ec_handoff_20261101/EVIDENCE_FREEZE.json` 里逐项冻结**，只需按 `dmc_attempt_registry/v1` 格式补一份 EC 登记并密封。**这是零计算工作**，等你确认口径后我可以做。
