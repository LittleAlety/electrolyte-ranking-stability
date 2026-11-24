# P10 · D8 受控切换与账本处置预案（SWITCH PLAN · 未授权 · 未执行）

**状态：HOLD —— 本文档是预案，不是执行记录。** 依 Lead 2026-11-03 处置：
「D8 切换与迁移继续 HOLD：先恢复可复现环境、补入口测试及崩溃恢复测试、完成绑定当前字节的 D7/D8 独立复审，再申请切换。」
本文件产出 = 切换步骤 / 备份与恢复步骤 / 迁移后断言；**公共处理不自行切换共享模块或账本**。

- 作者角色：公共处理（本会话）；**独立复审 = 非作者**（审计报告见 §6，由 subagent 独立执行、Lead 复验）。
- 冻结对象：`evidence/p10_switch_plan/freeze_manifest.json`（16 对象，逐 sha256/bytes/mtime，见 §1）。
- 写入面声明：本文件与冻结清单只写唯一生产写入面 `evidence/`；共享模块、账本、登记册、labels **零触碰**（字节复核见 §7）。

## 1. 冻结对象（freeze_manifest.json 实测，锚值与 P1 §8 全等）

| 对象 | SHA256（前16） | 字节 | 状态 |
|---|---|---|---|
| 共享模块 `work/dmc_staged_receiver_v5.py` | `205f1ba93d9a0b69` | 98,779 | FROZEN（切换源=当前字节） |
| D8 候选 `work/admission_closure_20261102/rev5_candidate_d8/dmc_staged_receiver_v5_candidate.py` | `138df33b6c2a677a` | 114,142 | FROZEN（切换目标字节） |
| 测试 `work/test_dmc_staged_receiver_v5.py` | `ee6b9f2987542aa9` | 29,921 | FROZEN |
| 测试 `work/test_dmc_staged_receiver.py`（v4） | `8dac1aa061da31aa` | 26,493 | FROZEN |
| 主账本 `work/dmc_staged_staging_ledger.json` | `c336acb5051deb31` | 111,047 | FROZEN（schema=v2 实测，见 P1 §3） |
| 登记册 `work/dmc_attempt_registry/REGISTRY_FREEZE.json` | `ea3c6c209aaa198c` | 1,312 | FROZEN |
| 登记册 `work/dmc_attempt_registry/v1.json` | `c13e43c35b77d9ca` | 2,256 | FROZEN |
| P3 目标/基线 | `a7eee5aa3df733cd` / `ed2b621d30f8df5c` | 29,558 / 27,332 | FROZEN |
| P6 目标/基线 | `83581f169d26a8d3` / `468dc00ee21a50f5` | 22,475 / 22,313 | FROZEN |
| D8 MANIFEST_v2 `…/MANIFEST_v2_20261103T080255.json` | `9de6c2e0f09622c8` | 5,298 | FROZEN（`missing=[]`、`all_hashed=true`） |
| D8 NARROW_CONFIRMATION.json | `4cf03e6f15ec4b1a` | 9,585 | FROZEN |

## 2. 切换前置条件（**全部满足前保持 HOLD**）

| # | 前置条件 | 状态（2026-11-04 实测） |
|---|---|---|
| C1 | 授权：Open question 1 的书面切换授权（Lead/用户） | **未获 → HOLD** |
| C2 | 可复现测试环境（Python+rdkit+依赖版本与复现命令） | 进行中（`E:\Claude Code\电解液溶剂-HB\.venv-review-20261103\`，独立环境不覆盖共享 `.venv`；见 `ENV_RECOVERY.md`） |
| C3 | 入口测试补齐：P2 七类全部真实入口验证 | 5/7 上轮已证；跨作业错配、v4 重复接收待 C2 后复跑；崩溃恢复 3 过+1 skip（skip=迁移工具不存在）已完成 |
| C4 | 崩溃恢复测试（写入中断→拒收→备份恢复→重跑） | **已补** `evidence/p2_item2_gap_tests/test_item2_crash_recovery.py`（`3d2b98ba…`，3 过+1 skip，exit 0） |
| C5 | **绑定当前字节的 D7/D8 独立复审**（非作者） | **已完成（2026-11-04）**：审计半边（`independent_audit.md` §1–2）+ 语义半边（`d7d8_semantic_review.md`，sha `5caa524123bdc8ab9d88a5aedb4b32be377fc79ce44dcebfefacadba9b32d09d`/11,554 B）——6/6 字节绑定、279/3+5 hunk ③类=0、D7 绑定当前字节、候选目录运行时 **100/100 全过**（工作区外 venv，junit 双证 exit 0）。剩余缺口（授权层）：`D7_FIX_VERIFICATION.json` 作者独立性未声明（P1 §7①） |
| C6 | 账本迁移工具（若批准迁移）：六步显式迁移实现 | **实现已存在于候选** `migrate_ledger()`（C5 语义复审核验：六步顺序与 R5 一致、`os.replace` 原子写、回读复检）→ 是否批准迁移仍属**授权层**；不以 register 隐式迁移替代 |

## 3. 切换步骤（S0–S7，**仅在 C1–C6 全满足后执行**）

| 步 | 动作 | 断言/退出判据 |
|---|---|---|
| S0 | 取得书面授权并记录（授权人、范围、时间） | 无授权 → 中止 |
| S1 | 环境就绪：用 `ENV_RECOVERY.md` 的复现命令装好独立环境 | `python -c "import rdkit,…"` 打印版本全匹配 |
| S2 | **备份**（先于任何写入）：①共享模块 `205f1ba9…`→ `evidence/p10_switch_plan/backup/dmc_staged_receiver_v5.205f1ba9.py`；②主账本 `c336acb5…`→ `backup/dmc_staged_staging_ledger.c336acb5.json`；③登记册两文件同法 | 备份文件重读 sha256 与源逐一相等 |
| S3 | 候选核验：候选字节 sha=`138df33b…`/114,142；MANIFEST_v2 `9de6c2e0…` `missing=[]` `all_hashed=true` | 任一不符 → 中止 |
| S4 | 切换写入：以**原子写**（临时文件+`os.replace`）把候选字节写入 `work/dmc_staged_receiver_v5.py`；写后重读 | 重读 sha256 == `138df33b…`（第三份字节，P4 语义：切换后须重冻重绑） |
| S5 | 账本处置：**R5 裁定倾向不迁移（append-once）** → 默认账本不动，仅记录「模块期望 v3/v5 vs 账本 v2」的轴偏斜继续显式登记；若授权迁移 → 仅用 C6 迁移工具，按 §5 六步。**⚠ 运行时影响（C5 语义复审实测确认）**：盘上账本确为 v2 → 切换后在「默认账本不动」下所有 `register()` 将一律 `LEDGER_SCHEMA_MIGRATION_REQUIRED` 拒收（fail-closed，设计非缺陷）→ **授权层须先裁定「迁移 or 停摆」，切换与可继续追加互斥** | 迁移仅允许显式工具，禁只改版本号（R5） |
| S6 | 切换后断言（§5.1 全表） | 任一失败 → 按 §4 回滚 |
| S7 | 切换后复审：v5 套件 40 例（含 5 rdkit 例）+ D8 专项套件 + gap/crash 套件，非作者复跑 | 全绿（exit 0）且审计报告留档 |

## 4. 备份与恢复步骤（可独立执行的命令级手册）

```bash
# —— 恢复共享模块到切换前字节（唯一允许的回退方式；禁 git reset）——
cp evidence/p10_switch_plan/backup/dmc_staged_receiver_v5.205f1ba9.py work/dmc_staged_receiver_v5.py
sha256sum work/dmc_staged_receiver_v5.py   # 断言 == 205f1ba93d9a0b69f2ea5f86595eef527da03db6d6aa8b2a331dd25a2ca9bb66

# —— 恢复主账本到切换前字节（回滚迁移/污染的唯一手段）——
cp evidence/p10_switch_plan/backup/dmc_staged_staging_ledger.c336acb5.json work/dmc_staged_staging_ledger.json
sha256sum work/dmc_staged_staging_ledger.json   # 断言 == c336acb5051deb31c276dc54c8bfefbcc64bf93d0244c82cb722a8869fd382d2
```

- 备份目录在**唯一写入面内**（evidence/），随证据归档；恢复动作本身也是一次写入 → 必须记入 SESSION_CLAIMS 并留恢复前后哈希。
- 账本损坏（写入中断）时的现场恢复：`test_item2_crash_recovery.py::test_backup_restore_after_crash_recovers_and_continues` 即演练脚本（备份→覆盖→重跑成功，A+B 都在）。

## 5. 迁移后断言（若且仅若 S5 授权迁移）

### 5.1 断言表

| # | 断言 | 判据 |
|---|---|---|
| A1 | 成员载荷未变 | 迁移前后 `members` 数组 `json.dumps(sort_keys=True)` 逐字节相等 |
| A2 | body 摘要重算全等 | 逐成员 `_body_sha256` 重算 == 存储值（0 处不符） |
| A3 | 成员数不变 | 迁移前后 `len(members)` 相等（当前 5 成员，`c336acb5…`） |
| A4 | 目标 schema 版本 | 顶层 `schema` == 目标版本；记录数与结构满足目标契约全 7 条（`LEDGER_SCHEMA_V3_REQUIREMENTS`，须在工具内显式列出） |
| A5 | 读回可复验 | 用切换后模块读回账本：对既有成员 register → `appended=false, reason=duplicate_member`（幂等，不双计） |
| A6 | 原子性 | 迁移工具用 tmp+`os.replace`；半成品（仅 tmp 存在、target 未替换）任何入口都读不回 |
| A7 | 迁移留痕 | `validation_executed`（写盘前跑了哪些校验、写盘后是否复验）写入迁移报告，随证据归档 |

### 5.2 迁移工具六步（R5 正确迁移顺序；工具=前置条件 C6）

① 路径安全（source≠target、target 不存在）→ ② 载入 source → ③ **用目标版本完整契约校验 source 载荷** → ④ 证明成员载荷未变（A1）→ ⑤ 原子写（tmp+`os.replace`）→ ⑥ 重读 target 再跑同一套完整校验。
**迁移涉及持久化证据，不得由一次普通 register 操作隐式触发**；「只改版本号」在完成 ③ 之前永远非法（R5）。

## 6. 非作者独立审计（已回填 · 2026-11-04）

- **报告**：`evidence/p10_switch_plan/independent_audit.md`｜**sha256 `5523335f5442b29bc1c398eec6a09743a75ec18f130dd1750a4a164303132079`**｜10,639 B。
- 执行者：fresh 非作者 subagent（无作者上下文）；**Lead 独立复验全部关键声明并采信**（报告 §2）。
- 实测结论：**冻结 16 对象 = OK 15 / ABSENT 1 / MISMATCH 0**（审计员三次复算 00:2x/00:29/00:37:48 + Lead 抽样 3/3 + 锚值 8/8 全 64 位一致）；**P3 分层**：层A（经审）45/3=48 行 4 hunk 无夹带、层B（先存 v2→v3）29/7=36 行 7 hunk、合计 74/10=84 可加无重叠；**P6**：4/1 单 hunk 与预期一致；**套件复跑**：22/22、5/5、9 过+1 跳（junit 双证 exit 0）；**卫生**：密钥 0、tmp/bak 0、pyc 2 个（gitignored，审计复跑产物）。
- 诚实缺口（非通过项）：`p6_verification.json` 缺 `input_hashes`/`status` 字段（hash 依据=runs/*/source_index.json）；p6 三跑为只读核对未复现；23 个既有 `.pytest_*` 权限目录未读。
- ⚠ **并发警告**：审计发现 `work/` 有他会话持续写入（至 00:35）→ **提交前必须重跑冻结清单，哈希全等才可提交**。
- **D7/D8 绑定当前字节的语义级独立复审（C5 后半）：已完成（2026-11-04）** → `evidence/p10_switch_plan/d7d8_semantic_review.md`｜**sha256 `5caa524123bdc8ab9d88a5aedb4b32be377fc79ce44dcebfefacadba9b32d09d`**｜11,554 B。执行者：fresh 非作者 subagent（只读，未跑任何脚本）+ Lead 复验与运行时补测。结论：6/6 字节绑定自洽；候选 vs shared **279/3、5 hunk 全归 ①D8/②兼容层，③ 类无关改动=0（红旗 0）**；**D7 绑定当前字节成立**（JSON `205f1ba9…` + 区间字节等价双证）；缺陷位点 `:1821` shared 缺陷仍在、候选 fail-closed 修复到位；**运行时补测：`rev5_candidate_d8/` 整目录 100/100 全过 exit 0**（工作区外独立 venv `venv-d8-20261104`，junit 双证；工作区 venv 下 1 例被 `[Errno 13]` ACL 阻断=环境限制非语义，已绕行关闭）。**运行时影响（授权层必读）**：盘上主账本确为 `schema=v2`（实测）→ 切换后所有 `register()` 一律 `LEDGER_SCHEMA_MIGRATION_REQUIRED` 拒收直至显式迁移，与 R5「倾向不迁移」互斥——**「切换」与「可继续追加」在当前账本下不可兼得，须先裁定迁移 or 停摆**。缺口继承：G1 D7 独立性声明未闭合、G2 `test_d8_schema.py`/`test_candidate_receiver.py` 不在冻结清单（`d23e45d9…` MANIFEST 链绑定，建议 S2 冻结为 v2 增量）、G3 `test_v5` 文件头文案与 FROZEN 表述矛盾、G5 工作区 venv ACL 限制。**本复审不构成切换授权。**

## 7. 本预案不做什么（边界）

1. 不切换共享模块、不迁账本、不改 labels/coverage/身份结论（C1 未满足）。
2. 不新增计算、不改阈值、不选 δ、不生成 `config/comparability_criterion_v1.json`。
3. 「复审通过 ≠ 切换授权」；「余额 ≠ 授权」。
4. 回退只用 §4 备份复制，**禁 `git reset`**。
