# `baseline_snapshot.json` 刷新复核草稿（DRAFT —— **尚未应用**）

本文件只是**提交轮刷新基线时可直接引用的复核材料**。**它不修改任何东西**：
`baseline_snapshot.json` 的 `source_hashes` 与 `baseline_refresh_review` **当前未被本文件改动**，
`preflight.py` 仍报 `STALE`（退出码 2）。

## 0. 基线的时点与自洽性核对（实测）
- 基线记录的 `head = 462f7f8b`，在历史中**存在**（`git cat-file -e` 通过）。
- 逐源核对：基线的 `source_hashes` 与 `462f7f8b` 处同名文件的 sha256 **逐一致**
  （`build_coverage_reviews.py` `3ab3caf0185e`、`import_ensemble_structures.py` `badbce9f6f06`、
  `submit_hpc_batch.py` `59440414885d`、`orca_derivative_policy.py` `81fd3267b75b` 全部 MATCH）
  ⇒ 基线是**自洽的时点快照**，STALE 只表示「此后脚本演进了」，不是基线坏了。

## 1. 漂移清单（12 项 `WATCHED` 中 **3 项**，其余 9 项未漂移）
| 源 | baseline → 现在 | 改动提交 | 规模 |
|---|---|---|---|
| `scripts/wp_production/build_coverage_reviews.py` | `3ab3caf0185e` → `387d26b792ea` | `192b6b6` | +11 / −1 |
| `scripts/wp_production/import_ensemble_structures.py` | `badbce9f6f06` → `ec41475a2ff7` | `f64b954` | +15 / −0 |
| `scripts/wp_production/submit_hpc_batch.py` | `59440414885d` → `086f113b73f6` | `e7326f4`、`0489601`、`1514ed0` | +173 / −3 |

## 2. 逐源的复核结论（事实层；理由与证据）
### 2.1 `build_coverage_reviews.py` ← `192b6b6`
**改了什么**：clean clone 缺 `work/` 时由「静默给空」改为**响亮拒绝**。
**理由（可引用）**：契合本项目既有纪律「`work/` 是 gitignored 机器本地层，**依赖它的构建器必须响亮拒绝而非静默降级**」，
且属交接指令阶段 0 的「干净克隆复现」要求。**行为影响**：无 `work/` 的环境从「给空结果」变为「报错」——
方向是**更严**，不会放宽任何验收。
**待补**：本源的授权口径（见 §4）。

### 2.2 `import_ensemble_structures.py` ← `f64b954`（**本会话自做，证据最全**）
**改了什么**：新增 `RE_SCF_CONVERGED` 与 `qc_task` 中的 SCF 收敛门（缺签名 ⇒ `scf_not_converged`
⇒ 既有逻辑转 `technical_complete_qc_failed`）。
**理由（可引用）**：计划 §6.3 把 SCF 收敛列为**不可被其它项替代**的检查之一，而此前该路径只断言
`ORCA TERMINATED NORMALLY`（技术标记）、`import_hpc_opt_numfreq` 的 heavy guard 守的是热化学↔末次单点能、
`build_state_identity_qc` 只在文档字符串提 SCF ⇒ 此前**没有任何 SCF 断言**。
**不翻转证据**：`structures.csv` 全部有日志的行（含 89 superseded + 31 qc_failed）**235/235 带签名**；
`work/hpc_*/**` 包日志 **434 个、431 带签名（99.3%）**；3 个无签名者中 2 个是批处理驱动日志，
第 3 个**无任何现行行引用**。**RED 实证**：中和门后负向测试按预期 `AssertionError`。
**行为影响**：方向是**更严**，且经测量对本 campaign 现行状态零翻转。

### 2.3 `submit_hpc_batch.py` ← `e7326f4` + `0489601` + `1514ed0`
**改了什么**：受保护提交器内部实现 P4 提交门——核心小时预算不变量（未结束全额预留 / 已结束按
Slurm allocation 去重计一次 / 终态缺来源即报错绝不按 0）、输入声明核数校验（ORCA 认 `%pal nprocs`、
非 ORCA 认 `cores.txt`）、资源协议 `xtb_screening_v1` = 2 核 × 2 h / cap 32 / 强制 attempts ledger。
**理由（可引用）**：**有专门文档** `docs/handoffs/four_state_recovery_20261023/P4_SUBMISSION_GATE_20261023.md`
（明写「这是不变量，不是独立提交程序；实际提交仍调用现有 `submit_hpc_batch.py`；不能在外层脚本偷偷绕开提交器」）。
**行为影响**：新增/收紧提交侧校验；**不影响科学验收**，且离线模拟提交实测 17/17、bridge 调用尝试 0。
**待补**：本源的授权口径（见 §4）。

## 3. 刷新时应当写入的字段（依既有 `baseline_refresh_review` 形状）
- `previous_head` = `462f7f8b06a72684084cb2a33319bf10cedd5699`
- `current_head` = 刷新时 HEAD（**刷新时现取，不要照抄本文件的撰写时 HEAD**）
- `watched_hash_changes` = §1 表格三条（`before` / `after` 十六进制全文）
- `reason` = 必须点名三个源与对应提交（`192b6b6`、`f64b954`、`e7326f4`+`0489601`+`1514ed0`）

## 4. 本草稿**刻意不代填**的部分（需 Lead / 用户确认）
既有 `baseline_refresh_review` 的 `reason` 写的是「**authorised G0 …**」——即刷新本身就是一句
「这些脚本变更**已复核、已授权**」的背书。本文件只提供**事实与证据**（§2），
**不为 2.1 与 2.3 两处非本会话的改动代写授权口径**；2.2 是本会话自做，可背书到证据级。
⇒ 提交轮刷新前需确认：这三处脚本演进各自属于哪一次授权/哪个阶段目标。
**未经确认不要写入 `baseline_snapshot.json`。**