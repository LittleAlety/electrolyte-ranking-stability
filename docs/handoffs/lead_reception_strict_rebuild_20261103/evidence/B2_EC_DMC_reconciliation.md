# B2 取证报告：EC 四份阶段输入哈希核对 + DMC 元数据更正前后值

- 仓库根：`E:\Claude Code\电解液溶剂-HB\电解液溶剂HB-Code`（下文 `<REPO>`）
- 模式：**只读取证**。本轮未修改任何既有文件、未提交作业、未新增计算；仅写入本目录下两个新文件。
- 哈希算法：SHA256。机器可读明细见同目录 [`B2_EC_input_hashes.json`](./B2_EC_input_hashes.json)。

---

## 一、EC 四份阶段输入核对表

四份输入路径：`<REPO>\docs\handoffs\strict_rebuild_20261103\remote_closure_20261103\ec_inputs\`

| # | 文件 | 字节数 | 重算 SHA256 | 首行 |
|---|---|---:|---|---|
| 1 | `ring_o2_monodentate_opt.inp` | 276 | `fd5f03c341f58c348a202a65ea1b2ea6f4a8490f0960a9134efe8dbf1252ed92` | `! wB97X-D4 def2-TZVPD Opt VeryTightOpt SMD(acetonitrile) VeryTightSCF SlowConv` |
| 2 | `ring_o2_monodentate_freq.inp` | 145 | `e2f4dfc6f6033dd216acb504446adb66aa551395214448217ee03e69f4b13588` | `! wB97X-D4 def2-TZVPD AnFreq SMD(acetonitrile) VeryTightSCF SlowConv` |
| 3 | `ring_o2_o5_bidentate_opt.inp` | 276 | `fd5f03c341f58c348a202a65ea1b2ea6f4a8490f0960a9134efe8dbf1252ed92` | 同 #1 |
| 4 | `ring_o2_o5_bidentate_freq.inp` | 145 | `e2f4dfc6f6033dd216acb504446adb66aa551395214448217ee03e69f4b13588` | 同 #2 |

**结论：4/4 全部对上，0 处不一致。**

### 1.1 各对照来源核对

| 来源 | 文件（哈希） | 声明值 | 判定 |
|---|---|---|---|
| S1 远端找回回执 | `remote_closure_20261103\fetch_receipts.txt`（`dd1577cd…`） | 第 7–10 行：远端 `…/hpc_ec_safe_coord_20261102/tasks/ring_o2_monodentate/attempts/3953361_0_0/{opt/job_opt.inp, freq/job_freq.inp}`、`…/ring_o2_o5_bidentate/attempts/3953361_1_0/{opt,freq}` → 本地四文件；**只记路径不含哈希** | 一致（路径与 stage 一一对应） |
| S2 证据闭环 | `remote_closure_20261103\remote_evidence_closure.json`（`63e0c53e…`，144KB） | 顶层键 `ec_inputs`（JSON 第 2452–2477 行）四条 sha256 分别为 `fd5f03…`/`e2f4dfc6…`/`fd5f03…`/`e2f4dfc6…`，且 `matches_original_package_and_result: true` | 一致（4/4） |
| S3 交付清单 | `remote_closure_20261103\DELIVERY_SHA256.json`（`8b188c6e…`） | 第 32–35 行四条路径→哈希，与上表逐字相同 | 一致（4/4） |
| S4 原始提交包 | `work\ec_coord_safe_20261102\hpc_ec_safe_coord_20261102.tar.gz`（`809d138d…`） | 包内两条 task 的 `inputs.sha256`：`job_opt.inp`/`job.inp` = `fd5f03…`、`job_freq.inp` = `e2f4dfc6…`（**两条 task 相同**）；解包目录 `work\hpc_ec_safe_coord_20261102\tasks\*` 实测同值；`UPLOAD_CHECK.txt`（`8df2b29e…`）对 `job_opt.inp/job_freq.inp/inputs.sha256` 均 `OK`；`submission_journal.json`（`27ef5cc6…`）`job_id=3953361` | 一致（4/4；任务给定线索 Opt=`fd5f03…`、Freq=`e2f4dfc6…` 核实为**两条 task 共同值**，故“另一条 task 的哈希”同样是这两个值） |
| S5 机器证据 | `blocker_resolution_20261103\candidate_sources.json`（`3bccdb41…`） | `ec.job_id=3953361`、`remote_workdir=hpc_ec_safe_coord_20261102`；两候选 `archive_input_sha256 == workflow_input_sha256`，`matches=true`、`input_first_line_echo_matches=true`；日志哈希 `086f32cc…`/`6d4e7886…`/`1144f0d5…`/`b620aceb…`、`workflow_result.json` `a5d641b1…`/`fa406838…`（本轮全部重算，全部相符） | 一致（4/4 输入 + 4/4 日志 + 包/回执/journal） |
| S6 文字证据 | `blocker_resolution_20261103\CANDIDATE_SOURCES.md`（`64fa07bf…`）第 7 行（第 2 条） | 来源是 `3953361 / hpc_ec_safe_coord_20261102`，**不是** `3954954 / hpc_ec_endpoint_pair_20261103`；原包 Opt=`fd5f03…`、Freq=`e2f4dfc6…`；返还日志哈希与第一行输入回显吻合 | 一致 |
| S7 端点对交接 | `docs\handoffs\ec_endpoint_pair_20261103\`（REPORT.md、RESULTS_AND_SUBMISSION_EVIDENCE.json） | 全文检索 `fd5f03c3`/`e2f4dfc6` **0 处**；其自身输入 `work\hpc_ec_endpoint_pair_20261103\tasks\*\job.inp` 首行是 `EnGrad … TightSCF SlowConv FMOPop`，两 task 同哈希 `0b41a8ad…`，journal `job_id=3954954` | **不涉及**（且反证四输入不来自 3954954） |
| S8 目录说明 | `remote_closure_20261103\README.md` | 目录级说明，未逐个声明四输入哈希 | 不涉及 |

### 1.2 按内容哈希建立的对应表（禁止按文件名猜配对）

| EC 输入（本地） | 重算 SHA256 | 原包成员（按哈希命中） | `cmp` 字节比对 | 候选级绑定依据 |
|---|---|---|---|---|
| `ring_o2_monodentate_opt.inp` | `fd5f03…` | `hpc_ec_safe_coord_20261102/tasks/ring_o2_monodentate/job_opt.inp` | exit 0 | `fetch_receipts.txt:7`（`attempts/3953361_0_0/opt`） |
| `ring_o2_monodentate_freq.inp` | `e2f4dfc6…` | `…/ring_o2_monodentate/job_freq.inp` | exit 0 | `fetch_receipts.txt:8`（`…_0_0/freq`） |
| `ring_o2_o5_bidentate_opt.inp` | `fd5f03…` | `…/ring_o2_o5_bidentate/job_opt.inp` | exit 0 | `fetch_receipts.txt:9`（`attempts/3953361_1_0/opt`） |
| `ring_o2_o5_bidentate_freq.inp` | `e2f4dfc6…` | `…/ring_o2_o5_bidentate/job_freq.inp` | exit 0 | `fetch_receipts.txt:10`（`…_1_0/freq`） |

**配对限制（重要）**：四份输入只有 **2 种唯一字节内容**（`cmp` 实测：两份 opt 完全相同、两份 freq 完全相同）。因此**内容哈希只能唯一确定 stage（opt/freq），不能区分 monodentate 与 bidentate**——两候选的几何差异在 `geom.xyz`（包内 `570f6e71…` vs `f76256de…`）。候选级归属由两条**独立且互相一致**的路径证据给出：`fetch_receipts.txt` 的远端 `attempts/3953361_0_0` vs `3953361_1_0` 映射，以及 `remote_evidence_closure.json` 的 `local_file` 字段。任务给定的“已知线索”两条哈希经核实正是两条 task 的共同值。

---

## 二、DMC 元数据更正前后值表

### 2.1 更正记录

| 项 | 值 |
|---|---|
| 更正文件 | `outputs\physics_completion\recovery\candidate_source_metadata_corrections.jsonl`（1 行，3813 B，`bc5eee7912a6305739133a6ff280ef111978e1234ca6f38c3d20f28a2c10346e`） |
| correction_id | `DMC_3928500_0_PROTOCOL_20261103_V1` |
| candidate / job | `3928500_0` / `3928500` |
| **更正前值** | `old protocol (TightSCF)` |
| **更正后值** | `new_numerical (VeryTightSCF + strict; SlowConv)`（协议事实：`VeryTightSCF SlowConv`） |
| 来源文件（旧值） | `work\lead_reception_20261102\AUTHORITATIVE_SETTLEMENT.json`，`source_sha256 = faee9c7fd98e1b366d3cf8e23bfd9c417ca1c87fe469603069411cea847813a2`（本轮重算**相符**） |
| 依据 | same-job submission bytes, returned stage inputs, workflow hashes and log echoes agree |
| scope | `source metadata fact correction only; no membership promotion, no cost change` |
| c3_i | `CLOSED_UNAPPROVED_EQUIVALENCE_RULE` |

### 2.2 有效值快照（234 B）

`docs\handoffs\strict_rebuild_20261103\remote_closure_20261103\DMC_protocol_metadata_effective.json`
（`15d1c9b42fdc46d074ddd22ac6e0a1ae57e9945a30bfc0d131591b96e6b20785`）

| 键 | 值 |
|---|---|
| `original` | `old protocol (TightSCF)` |
| `effective` | `new_numerical (VeryTightSCF + strict; SlowConv)` |
| `correction_ids` | `["DMC_3928500_0_PROTOCOL_20261103_V1"]` |
| `c3_i` | `CLOSED_UNAPPROVED_EQUIVALENCE_RULE`（C3(i) 关闭保留） |

### 2.3 旧值出现在哪里（grep 核实，只报事实、不改）

| 文件 | 行 | 键/字段 | 旧值 |
|---|---:|---|---|
| `work\lead_reception_20261102\AUTHORITATIVE_SETTLEMENT.json` | 149→151 | `reference_rows_already_settled[].job_element="3928500_0"` → `.protocol` | `old protocol (TightSCF)` |
| `work\lead_reception_20261102\RECEPTION.json` | 1208 | `handoff_protocol_label_errors[0].handoff_says` | `old (TightSCF)`（同条目已记 `input_deck_sha256=91499225…`） |
| `work\lead_reception_20261102\RECEPTION.json` | 1326 | `recheck_findings_adopted[0].finding` | “3928500_0 is labelled old (TightSCF) … but its own input deck and the log's SCF echo are VeryTightSCF” |
| `docs\handoffs\strict_rebuild_20261103\run_e5457aa74a6fea32\source_index.json` | 10035 | `settlement_protocol_label`（伴生 `protocol_source_conflict: true`、`effective_opt_scf_from_receiver: "VeryTightSCF"`） | `old protocol (TightSCF)` |
| `docs\handoffs\strict_rebuild_20261103\run_e09e1bcf681da10a\source_index.json` | 10039 | 同上 | `old protocol (TightSCF)` |
| `docs\handoffs\strict_rebuild_20261103\run_764b5dcb0f60320b\source_index.json` | 9050 | 同上 | `old protocol (TightSCF)` |
| `docs\handoffs\strict_rebuild_20261103\run_6aff6e9daf188c1b\source_index.json` | 10060 | 同上 | `old protocol (TightSCF)` |
| `docs\handoffs\strict_rebuild_20261103\run_4ed1af288fcebdb4\source_index.json` | 10060 | 同上 | `old protocol (TightSCF)` |
| `docs\handoffs\strict_rebuild_20261103\run_06c49d9e7ebe0688\source_index.json` | 10060 | 同上 | `old protocol (TightSCF)` |
| `tests\test_source_metadata_corrections.py` | 16、18、19 | 测试夹具 | `old protocol (TightSCF)` |

以上均为**既有文件中的旧标签原样留存**，本轮未作任何修改；账本旧值仍可被检索到，符合“更正仅追加留档”的约定。

### 2.4 更正后值的来源证据（实测）

| 证据 | 实测结果 |
|---|---|
| Opt 日志 `work\ec_dmc_campaign_20261031\results\3928500_0\opt\job_opt.log`（`326197e8…`） | **第 229 行** `|  1> ! wB97X-D4 def2-TZVPD Opt VeryTightOpt SMD(acetonitrile) VeryTightSCF SlowConv`（`grep -n` 命中 229，exit 0） |
| Freq 日志 `…\freq\job_freq.log`（`fabf18c1…`） | **第 225 行** `|  1> ! wB97X-D4 def2-TZVPD AnFreq SMD(acetonitrile) VeryTightSCF SlowConv`（`grep -n` 命中 225，exit 0）——与 `CANDIDATE_SOURCES.md` 第 9 行所述行号**完全一致** |
| Opt 输入 `…\opt\job_opt.inp` | 276 B，`914992255efb679ce770ea14a5645a3222df062ac868fb9de4845ec03e452bf3`（与更正记录声明值相符） |
| Freq 输入 `…\freq\job_freq.inp` | 145 B，`e2f4dfc6f6033dd216acb504446adb66aa551395214448217ee03e69f4b13588`（与更正记录相符；与 EC 四份之一同模板） |
| 提交绑定 `work\ec_dmc_campaign_20261031\SUBMISSIONS.json`（`2a3294a7…`） | 第 49 行 `job_id: 3928500`（第 78 行 `serial_dependency_afterany: 3928500`） |
| 文字记录 `blocker_resolution_20261103\CANDIDATE_SOURCES.md` 第 9 行（第 3 条） | “DMC 3928500_0：实际协议为 VeryTightSCF SlowConv … Opt 日志第 229 行、Freq 日志第 225 行均回显 … C3(i) 尚未批准，晋升仍关闭；本轮未迁移正式账本” |
| 读取器 | `scripts\wp_production\rebuild_strict_isolated.py:197` 读取该 jsonl 应用哈希绑定的更正 |

### 2.5 边界声明

1. **未修改账本**：`AUTHORITATIVE_SETTLEMENT.json`、`RECEPTION.json`、各 `source_index.json` 全部原样保留（本轮只读）。
2. **未走 C3(i)**：`c3_i = CLOSED_UNAPPROVED_EQUIVALENCE_RULE`，几何/频率等效规则未批准。
3. **未迁移任何正式成员**：无 membership promotion；`3928500_0` 仍为 staged/COMPUTED_NOT_PROMOTED。
4. **无费用变化**：3928500_0 实耗 2.7200 CH 仍记 `ALREADY SETTLED`。
5. **本轮无新计算**：仅执行只读命令与哈希计算，未提交作业、未写入既有文件。

---

## 三、复现命令与退出码

工作目录：`<REPO>`（下列命令均在 bash 中执行）

| # | 命令 | 退出码 | 关键输出 |
|---:|---|---|---|
| 1 | `cd docs/handoffs/strict_rebuild_20261103/remote_closure_20261103 && sha256sum ec_inputs/*.inp` | 0 | 见 §一表（2 个唯一哈希） |
| 2 | `wc -c ec_inputs/*.inp` | 0 | 276 / 145 / 276 / 145 |
| 3 | `cat -A ec_inputs/*.inp` | 0 | 首行 `! wB97X-D4 … VeryTightSCF SlowConv` |
| 4 | `grep -n 'fd5f03c3…\|e2f4dfc6…' -r remote_closure_20261103 --include=*.json --include=*.txt` | 0 | DELIVERY 第 32–35 行、closure 第 2454/2461/2468/2475 行 |
| 5 | `tar -tzf work/ec_coord_safe_20261102/hpc_ec_safe_coord_20261102.tar.gz` | 0 | 含两条 task 的 `job_opt.inp/job_freq.inp/inputs.sha256` |
| 6 | `tar -xOzf <tar> hpc_ec_safe_coord_20261102/tasks/<task>/inputs.sha256`（两条 task 各一次） | 0 | 均列 `fd5f03… job_opt.inp`、`e2f4dfc6… job_freq.inp` |
| 7 | `sha256sum work/hpc_ec_safe_coord_20261102/tasks/*/job_{opt,freq}.inp */job.inp` | 0 | `fd5f03…`×2 opt、`e2f4dfc6…`×2 freq |
| 8 | `sha256sum <fetch_receipts.txt> <remote_evidence_closure.json> <DELIVERY_SHA256.json> <candidate_sources.json> <tar.gz> <UPLOAD_CHECK.txt> <submission_journal.json> <corrections.jsonl> <DMC_protocol_metadata_effective.json> <CANDIDATE_SOURCES.md>` | 0 | 见各表“文件哈希”列 |
| 9 | `cmp ec_inputs/<f> work/hpc_ec_safe_coord_20261102/tasks/<t>/<stage>.inp`（4 次） | 0 | 全部字节相同 |
| 10 | `cmp ec_inputs/ring_o2_monodentate_opt.inp ec_inputs/ring_o2_o5_bidentate_opt.inp` | 0 | 两 opt 输入完全相同（配对限制的实证） |
| 11 | `grep -n 'fd5f03c3\|e2f4dfc6' docs/handoffs/ec_endpoint_pair_20261103/{REPORT.md,RESULTS_AND_SUBMISSION_EVIDENCE.json}` | 0 | 无匹配行（该交接不涉及） |
| 12 | `sha256sum work/ec_followup_20261103/results/*/…/{job_opt,job_freq}.log` 与 `workflow_result.json` | 0 | 与 `candidate_sources.json` 六个声明值全部相符 |
| 13 | `grep -n 'VeryTightSCF SlowConv' …/3928500_0/opt/job_opt.log` | 0 | `229` |
| 14 | `grep -n 'VeryTightSCF SlowConv' …/3928500_0/freq/job_freq.log` | 0 | `225` |
| 15 | `sha256sum …/3928500_0/{opt/job_opt.inp,freq/job_freq.inp,opt/job_opt.log,freq/job_freq.log}` | 0 | `91499225…` / `e2f4dfc6…` / `326197e8…` / `fabf18c1…` |
| 16 | `grep -n 3928500 work/ec_dmc_campaign_20261031/SUBMISSIONS.json` | 0 | 第 49 行 `job_id`、第 78 行依赖 |
| 17 | `grep -n TightSCF work/lead_reception_20261102/AUTHORITATIVE_SETTLEMENT.json` | 0 | 第 151 行 `old protocol (TightSCF)` |
| 18 | `grep -rn 'old protocol \(TightSCF\)' <repo>`（shell 限时 120 s） | 超时（1） | 改用 ripgrep 重跑，见 #19 |
| 19 | ripgrep：`old protocol \(TightSCF\)` 全库 | 0 | 13 处匹配（见 §2.3 + 更正文件 + effective 文件 + 测试） |

---

## 四、未确定事项

1. **候选级哈希配对不可判定**：四份 EC 输入只有 2 种唯一哈希，`monodentate` 与 `bidentate` 的输入字节完全相同，内容哈希只能确定 stage；候选归属依赖 `fetch_receipts.txt` 远端 `attempts/3953361_0_0` vs `3953361_1_0` 路径映射与 `remote_evidence_closure.json.local_file`（两条独立证据同向）。
2. **`remote_evidence_closure.json` 并未内含 EC 阶段日志哈希**：该文件只有 `ec_inputs` 段；EC 阶段日志哈希实际存于 `candidate_sources.json` 的 `stages[].log_sha256`（本轮已重算并相符）。
3. **远端阶段文件本轮未访问**：未读取 `hpc_ec_safe_coord_20261102` 远端目录，沿用 `CANDIDATE_SOURCES.md` 的“远端阶段文件独立复核仍未完成”表述，不据此推断远端证据存在与否。
4. 任务给定的目录名 `work\ec_coord_safe_20261032` 在仓库中不存在；实际为 `work\ec_coord_safe_20261102`（与 `candidate_sources.json`/`CANDIDATE_SOURCES.md` 一致），本报告按实际路径取证。
5. `AUTHORITATIVE_SETTLEMENT.json` 不在 `DELIVERY_SHA256.json` 覆盖范围内（该清单只覆盖 remote_closure 目录 + 更正 jsonl 等），其完整性以更正记录内的 `source_sha256` 绑定（本轮重算相符）为准。

---

## 五、本轮产出文件

- `docs\handoffs\lead_reception_strict_rebuild_20261103\evidence\B2_EC_input_hashes.json`（机器可读）
- `docs\handoffs\lead_reception_strict_rebuild_20261103\evidence\B2_EC_DMC_reconciliation.md`（本文件）
