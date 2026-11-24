# DMC|M_plus 接收器 rev5 — 独立复审（exp_line_20261031，2026-10-31）

- 复审人：本实验线（独立于 rev5 作者的那个会话）
- 复审方式：**只读**。代码逐段阅读 + 复用独立审计者的 rev4 对抗语料（仅改 import 指向 rev5）+ 自写信任边界探针 + R8 直接测定
- 结论绑定哈希（**下述结论只对这几个字节成立；其中任何一个变化，本复审即作废**）

| 角色 | 文件 | sha256（2026-10-31 02:2x 实测） |
|---|---|---|
| 被审对象 rev5 | `work/dmc_staged_receiver_v5.py` | `628a2cdf7426fde995ea34b97aa8108dc9d44d55ab9d7c96a945d84fa0ba4523` |
| 前一代 rev4 | `work/dmc_staged_receiver.py` | `32501b7185d61d7ac05ba1cd4f03ae1f4b85d1f5c8225992a8272a1ce7374278` |
| 测试文件 | `work/test_dmc_staged_receiver.py` | `8dac1aa061da31aa8c4e906ac63a2c1d81cfdf054c1f7a423f94b8005bde1012` |
| 侧车发射器 | `work/_dmc_emit_staging_record.py` | `5cef828eab1f4932f7a39c0cc343f7c7bc18e74d79d654963d6d79addfbd8e23` |
| 暂存账本 | `work/dmc_staged_staging_ledger.json` | `54d663175c812028a65701eea3fe5f921dcf82a4a0d6956fe0fe0da0e1db1c12` |

**没有任何"四者哈希冻结"记录存在**（全库未找到 `dmc_attempt_registry/v1` 登记文件，也没有 rev5 的冻结清单）。rev5 的 mtime 是 01:41，另一个会话在 02:13–02:21 仍在写 `work/_fpc_*_20261031.*`；本条目冻结状态**不成立**。

---

## 1. 一句话结论

**rev5 的信任边界"按规格实现了"（机制 10/10 测点符合预期），但交付链没闭合**：没有密封登记文件、发射器仍驱动 rev4 的测试入口、没有任何测试覆盖 rev5。因此按用户给出的认证判据（"期望值来自调用者在同一次请求里无法替换的、且其可信来源已被独立审定的位置"），现在**不能判 rev5 复审通过**，也不能迁入 `scripts/wp_production/`。

---

## 2. 机制测点（自写探针 `work/exp_line_20261031/audit_v5/probe_v5_trust.py`，14 项测定）

| 测点 | 期望 | 实测 | 判定 |
|---|---|---|---|
| P1 `receive()` 打戳 | `caller_supplied_expectations` | 同 | ✅ |
| P2 `register()` 拒绝未密封记录 | `TRUST_BOUNDARY_UNSEALED` | 同，且账本未落盘 | ✅ |
| P3 带外摘要不符 | `REGISTRY_DIGEST_MISMATCH` | 同 | ✅ |
| P4 诚实密封路径端到端 | PASS + `sealed_registry` | 同 | ✅ |
| P5a 声明端点为起点、日志诚实 | `START_GEOMETRY_NOT_USED` | 同（新增的有效门） | ✅ |
| P5b **自洽伪造**（日志首块改成端点 + 把端点登记为 Rk1） | 按裁定属"带外边界" | **PASS + `sealed_registry`** | ⚠ 见 §3 |
| P6 把 P5b 记录登记进账本 | — | **appended=True** | ⚠ 见 §3 |
| P10a 正常坐标块计数 | 1 块 | 1 块 | ✅ |
| P10b 原子数不足 | `MALFORMED_GEOMETRY` | 同 | ✅ |
| P10c `Mu parameter` 诱饵行被当块 | `MALFORMED_GEOMETRY` | 同 | ✅ |
| P10d 块头声明的原子数被校验 | 拒绝 | **接受**（头行被跳过、根本没解析） | ❌ 文档过度声称 |
| P7 仓库内存在密封登记文件 | ≥1 个 `dmc_attempt_registry/v1` | **0 个** | ❌ |
| P8 发射器是否走生产入口 | import rev5 且调 `receive_attempt` | **两者皆否**（仍是 `from dmc_staged_receiver import ... receive`，即 rev4 的测试入口） | ❌ |
| P9 覆盖 rev5 的测试 | ≥1 个测试模块 | **0 个**（`work/test_dmc_staged_receiver.py` 的 49 个 test 都 `from dmc_staged_receiver import`，即 rev4） | ❌ |

原始输出：`work/exp_line_20261031/audit_v5/PROBE_V5_TRUST_RESULT.json`。

### 2.1 rev4 对抗语料在 rev5 上的复跑（19 个 tag，只改 import）

语料与驱动器来自独立审计者 `work/_audit_rev4_ds/`（原件未动，副本在 `work/exp_line_20261031/audit_v5/`，仅把目标模块指向 rev5；两处 `REPO` 锚点因目录深度变化而修正）。

| rev4 审计编号 | tag | rev5 实测 | 状态 |
|---|---|---|---|
| 基线（真实证据必须被接受） | `baseline` | **PASS** | ✅ 正向对照成立 |
| R2 伪造块 + 伪造 CYCLE 标记 | `n3` | `TABLE_CYCLE_MISMATCH` | 已闭合 |
| R3 伪造收敛表 | `n7` | `TABLE_CYCLE_MISMATCH` | 已闭合 |
| R4 30 个频率里改 29 个 | `n9` | `FREQUENCY_SPECTRUM_MISMATCH` | 已闭合 |
| R6 多重度只由奇偶约束 | `n12` / `n12b` | `OCCUPANCY_INCONSISTENT` | 已闭合 |
| R7 打印的截止频率未被使用 | `n17` | `CUTOFF_NOT_FROZEN` | 已闭合 |
| R1 注册表是调用方数据 | `a8_forged_registry` | 在 `receive()` 层仍 **PASS**（设计如此） | 见 §3 |
| 尾部伪造块 / 尾部伪造表 / 全量伪造频率 | `f4` / `h4` / `i6` | `LOG_TRAILING_CONTENT` / `LOG_TRAILING_CONTENT` / `ZPE_INCONSISTENT_WITH_MODES` | 仍拒 |
| 起点标签不符 | `a8_strict` | `START_LABEL_MISMATCH` | ✅ |
| R5 全合成 Hessian | `n16` | **不可复跑**（语料用的 `record["hessian_lowest_positive_cm1"]` 字段在 rev5 记录里不存在，harness KeyError） | 未测定 |
| R8 "块计数把非坐标行算进去" | `n18` | **不可复跑**（`coordinate_blocks()` 新增必填参数 `expected_atoms`） | 改用 P10 直接测定，见上 |
| 4 个"合法外形"探针（rev4 审计 §9 的误拒风险） | `l1`–`l4` | 仍全部拒绝：`CYCLE_SEGMENT_INCOMPLETE` / `LOG_TRAILING_CONTENT` / `LOG_BANNER_COUNT` / `MALFORMED_GEOMETRY` | ⚠ 未消解的误拒风险 |

原始输出：`work/exp_line_20261031/audit_v5/C_cases_raw.txt`、`cases_results.json`。

**注意语料的性质**：这是 rev5 作者已经回答过的那份语料，通过属于"预期之内"，**不构成独立性证据**；它的价值在于**失败会立刻暴露**。n16/n18 不可复跑这一点本身必须如实记为"未测定"，不能记"通过"。

---

## 3. R1 的真实边界（本复审最重要的一条）

rev5 的密封只对"摘要来源独立"这件事有效。实测：

- **P5a**：日志诚实、只把端点冒充起点 → 被新的 `START_GEOMETRY_NOT_USED` 挡住（这是 rev5 相对 rev4 的实质改进）。
- **P5b**：把日志首块也改成端点，并把端点登记为 Rk1（`a8_forged_registry` 的构造），再由调用方自己提供该伪造登记文件的摘要 → `receive_attempt()` **PASS**，记录打戳 `sealed_registry`；**P6**：`register()` 接受它并写入账本。

⇒ 结论：**密封的价值完全取决于那个带外摘要来自哪里**。用户 2026-10-31 的裁定已把"攻击者同时控制代码与所有信任锚"判为不必继续堆检查的无限威胁模型，所以 P5b/P6 不是 rev5 的缺陷；但它意味着**在出现一个"独立审定"的登记文件之前，R1 在端到端意义上仍是敞开的**。今天仓库里没有这个文件（P7 = 0）。

---

## 4. 门（Blockers）：进入正式链之前必须补齐的四件事

| # | 缺口 | 证据 | 归属 |
|---|---|---|---|
| B1 | 没有密封的 attempt 登记文件（`dmc_attempt_registry/v1`），生产入口从未在真实证据上跑通过 | P7 = 0 命中；P4 只在自造登记上通过 | 执行 Lead（生产面写入者） |
| B2 | 发射器 `_dmc_emit_staging_record.py` 仍 import rev4、调 `receive()`（测试入口）；现有账本条目（schema `dmc_staged_receiver/v4`）在 rev5 的 `register()` 下会被 `TRUST_BOUNDARY_UNSEALED` 拒绝 | P8；`work/dmc_staged_staging_ledger.json` schema=v4 | 执行 Lead |
| B3 | 没有任何测试覆盖 rev5（49 个 test 全指向 rev4） | P9；`work/test_dmc_staged_receiver.py:26` | 执行 Lead |
| B4 | 文档过度声称：`coordinate_blocks` 的注释说 "exactly `expected_atoms` four-field atom lines"，但块头声明的原子数**根本没被解析**（P10d：头写 99、实带 13 行 → 接受） | `work/dmc_staged_receiver_v5.py:214` 与实测 P10d | 执行 Lead（文档/代码口径） |

**未消解项**：`l1`–`l4` 四个"合法外形"仍被结构性门拒绝。rev4 审计把它们标为"constructed, not observed from ORCA"，因此现在只能记为**误拒风险**，不能记为已证实的误拒——除非能拿出至少一份真实生产 ORCA 日志呈现该外形。

---

## 5. 复审动作范围声明（可核查）

- 本复审写入面：仅 `work/exp_line_20261031/audit_v5/**` 与 `docs/handoffs/exp_line_20261031/**`。
- 未修改：`work/dmc_staged_receiver*.py`、`work/test_dmc_staged_receiver.py`、`work/_dmc_emit_staging_record.py`、`work/dmc_staged_staging_ledger.json`、`work/_audit_rev4_ds/**`、`scripts/**`、`outputs/**`。
- 未执行 git 写操作；未提交超算作业；未触碰 `E:\软件\超算连接` 下的桥（除只读 `doctor`/`jobs`/`sacct` 查询）。