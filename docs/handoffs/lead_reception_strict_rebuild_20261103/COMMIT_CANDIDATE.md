# COMMIT_CANDIDATE · 提交候选清单与验证结果（2026-11-04）

> 位置说明：本文件在 `evidence/` **之外**（handoff 根），故不入 `ARCHIVE_MANIFEST_G2.json`（避免互指循环，沿 P9 先例）。
> 状态：**候选清单，未提交**——等用户拍板；本 goal 不执行 `git commit`。执行时按 §3 检查清单走。
> 依据：`evidence/p10_switch_plan/freeze_manifest.json`（16 对象）+ `independent_audit.md`（sha `5523335f5442b29bc1c398eec6a09743a75ec18f130dd1750a4a164303132079`）+ 本文件 §2 实测。

## 1. 拟提交文件（精确清单）

### A. 经审工程修改（4 个文件）

| # | 路径 | git 态 | sha256（当前字节） | bytes | 说明 |
|---|---|---|---|---|---|
| 1 | `scripts/wp_production/build_coverage_reviews.py` | **M** | `a7eee5aa3df733cddd3fe4282a6b179c328fbe4b9b1c4ad319829b16ec07c765` | 29,558 | P3 目标。vs HEAD = **74+/10−（84 行）= 层B先存 v2→v3（29+/7−，7 hunk）+ 层A经审 exclusion guard（45+/3−，4 hunk）**，两层可加无重叠（Lead numstat 三组复验，见 `independent_audit.md` §2） |
| 2 | `scripts/wp_production/rebuild_strict_isolated.py` | **??** | `83581f169d26a8d3df1f7a7438a5b06d296ff812fff9458b2a6f20052570fc22` | 22,475 | P6 新文件。vs `.orig` 基线 = **4+/1− 单 hunk（仅 :342 corrections 补比对）** |
| 3 | `tests/test_exclusion_source_completeness.py` | **??** | `22610644847f1f65c9c37ca89f26e929daf1ee65c3c4b234f4478860a430ecdc` | 6,189 | P3 对应测试，8 用例 |
| 4 | `tests/test_strict_coverage_single_cluster.py` | **??** | `e089aefc683355514e6e19639fa0886c992964c4e38cecba6c2793f6f03c55da` | 5,797 | P3 对应测试，5 用例 |

⚠ **拍板点 1**：文件 1 的工作树 diff **必然同时带入层B**（v2→v3，早前会话的未提交改动）——同一文件无法只提交层A。层B 已由 `.orig` 基线 + P3 文档完整登记并经本轮非作者审计定性；**若坚持「不夹带其他会话改动」字面执行，则文件 1 只能整体不提交**（P3 交付随之悬置）。默认建议：**整体提交两层**（层B 属本 handoff 链前序会话产物、已被审计覆盖），在提交信息中明写两层构成。

### B. evidence 归档（1 个目录）

| # | 路径 | 内容 | 关键钉 |
|---|---|---|---|
| 5 | `docs/handoffs/lead_reception_strict_rebuild_20261103/`（整目录） | `evidence/` **100 文件**（G2 清单钉 99 + 清单自指 1）+ 本文件 = **101 文件**，excl. `__pycache__`（gitignored） | G2 `ARCHIVE_MANIFEST_G2.json` = **99 文件/3,597,255 B**，sha `b44c6066009c130d4a71d08255acb2e1e11985cd1c0d2c5b93af9d1d6cce6bbe`，generated_utc `2026-11-03T17:16:14Z`；G1（P9 钉）=91 文件/3,522,838 B；**G2 vs G1 = +8 / ~2 / −0**（added：ARCHIVE_MANIFEST.json、P9 索引、ENV_RECOVERY、p10 四件〔SWITCH_PLAN/freeze_manifest/independent_audit/d7d8_semantic_review〕、crash 测试；changed：P2 矩阵、entry gap 测试）；`independent_audit.md` sha `5523335f…`；`d7d8_semantic_review.md` sha `5caa524123bdc8ab9d88a5aedb4b32be377fc79ce44dcebfefacadba9b32d09d`；`ENV_RECOVERY.md` 见 G2 钉值 |

### C. 明确排除（不夹带，实测 61 M + 76 ?? 中的其余部分）

- **其他会话 M（59 个）**：`scripts/` 5（README、build_production_ensemble_manifest、evidence_gate、import_hpc_opt_numfreq、strict_readiness_wiring、submit_hpc_batch 等）、`tests/` 8（test_ec_submit_entry 等）、`docs/`、`outputs/`、根目录等既有改动。
- **docs/handoffs 内他会话 M（2 个）**：`four_state_recovery_20261023/`、`wp5_formal_replay_guard_20261023/`。
- **其余 ??（约 70 项）**：`config/`、`outputs/`、`docs/plans/`、其他 handoff 目录（ec_dmc_*、strict_*、long_run 等）、`scripts/` 其他 17 个 untracked、`tests/` 其余 untracked（**含 `test_dmc_reception_registration.py`（P5）与 `config/dmc_reception_registration_v1.json`——属 P5 门禁链，不在用户指定的「P3/P6 对应测试」字面范围内**）。
- **仓库根 `.py`**（25,627 B，= HEAD 版 build_coverage_reviews 全等拷贝，来源存疑）——排除，待处置。
- **权限残留 `.pytest_*`/`.pytest_tmp_*` 目录（23 个，Permission denied）**——既有问题，非本交付面，未处理（ACL 修复需审批，本会话禁审批）。
- **`work/*`**（`.gitignore:76` 忽略，本就不入库）。

⚠ **拍板点 2（可选扩展）**：是否把 P5 注册链（`tests/test_dmc_reception_registration.py` + `config/dmc_reception_registration_v1.json` + `outputs/physics_completion/recovery/dmc_reception_*`）纳入本提交？**默认不纳入**（超出用户指定范围）。

## 2. 验证结果（提交凭据，全部 exit 0 实测）

| 验证 | 结果 | 证据 |
|---|---|---|
| 冻结清单 16 对象（终态复核，防并发） | **OK 15 / ABSENT 1 / MISMATCH 0** | `freeze_manifest.json` + `independent_audit.md` §1.1（审计员三次复算 + Lead 抽样 3/3 + 锚值 8/8 全 64 位） |
| E1 v5 入口套（跨作业错配族） | **40 过** | `$VENV/_rerun20261104.log`，P2 §3.1 |
| E2 v4 入口套（重复接收族） | **49 过** | 同上 |
| E3 P5 注册 | **11 过** | 同上 |
| E4 P5 门套 5 文件 | **52 过 + 1 跳**（补 pyyaml 后全绿） | `$VENV/_s4_retry.log` |
| E5 gap + crash（拒收零写入/中断恢复） | **9 过 + 1 跳**（1 跳=迁移工具不存在，C6） | `ENV_RECOVERY.md` §5 |
| P3 组1（exclusion+clean_clone+archive_dep） | **22/22**（junit 双证） | 审计员 + `independent_audit.md` §1.3 |
| P3 组2（strict_coverage_single_cluster） | **5/5**（审计员 junit + Lead 抽跑复验） | 同上 §2 |
| P3 分层 diff | 层A **45/3=48**、层B **29/7=36**、合计 **74/10=84** 可加 | `independent_audit.md` §1.2 + §2 Lead 复验 |
| P6 diff | **4/1 单 hunk** | 同上 |
| 卫生（密钥/临时文件） | 密钥模式 **0 命中**（审计员双范围 + Lead 对本轮新增文件补扫；唯一命中=扫描模式自述假阳性）；tmp/bak/pytest_cache **0** | `independent_audit.md` §1.5 + 本轮补扫 |
| 归档完整性 | G2 **99 文件**逐文件 sha256/bytes，vs G1 **+8/~2/−0，removed 0**；提交前终态冻结复核 **OK 15/ABSENT 1/MISMATCH 0** | `evidence/ARCHIVE_MANIFEST_G2.json`（sha `b44c6066…`） |
| D7/D8 语义复审（C5） | 6/6 字节绑定、279/3+5 hunk ③类无关改动 **0**、D7 绑定当前字节 | `evidence/p10_switch_plan/d7d8_semantic_review.md`（sha `5caa524123bdc8ab9d88a5aedb4b32be377fc79ce44dcebfefacadba9b32d09d`） |
| D8 候选运行时（补测） | **100/100 全过 exit 0**（工作区外 venv `venv-d8-20261104`，junit 双证；工作区 venv 下 1 例被 `[Errno 13]` ACL 阻断=环境限制非语义） | `d8_out/d8_schema.xml` 60/60 + `d8_dir.xml` 100/100；复现命令见 `ENV_RECOVERY.md` §7 |
| 独立环境可复现 | venv 重建 + 五套复跑全绿，**重建≠原环境**（诚实边界已写明） | `evidence/ENV_RECOVERY.md` §6 |

## 3. 提交前检查清单（拍板后执行；本 goal 不执行提交）

1. **重跑冻结清单**（他会话在 work/ 并发写入的警示 → 16 对象哈希全等才可继续；任何 MISMATCH 即停）。
2. `git status --porcelain` 精确面复核 = §1 A+B（4 文件 + 1 目录），逐条对照 §1 C 排除表。
3. 对 §1 A 的 4 个文件 + 目录内全部文件做终扫（密钥模式 0；无 `__pycache__`/`.pyc` 入库——gitignore 已挡，add 后 `git status` 复核）。
4. 提交信息建议明写：P3 两层构成（48+36）、P6 :342 修复、evidence G2 钉值、独立环境验证 E1–E5 与22/5/9+1 结果；**禁 `git reset`**；不 push（除非另行授权）。
5. 提交后：把 commit sha 回填 `SESSION_CLAIMS.md` 与本文件 §4。

## 4. 提交回填区（执行后填）

- commit sha：＿＿＿＿（待执行）
- 提交时间 UTC：＿＿＿＿
