# B4 隔离复跑与逐字段差异（登记 · 去重 · coverage）

范围：工程与来源对账；不作科学替代裁定。本轮对公共生产文件/代码**零写入**，全部产出仅在 `docs/handoffs/lead_reception_strict_rebuild_20261103/evidence/`。
零计算、零作业提交、零阈值/判据/正式标签改动。

## 1 复跑清单（三条通道）

| # | 通道 | 命令（cwd=仓库根） | exit | 产物（均在 evidence/ 下） |
|---|---|---|---|---|
| R1 | 登记+去重+coverage 重分类（`rebuild_strict_isolated.py`，sha `468dc00e…`） | `PYTHONIOENCODING=utf-8 python scripts/wp_production/rebuild_strict_isolated.py --base docs/handoffs/lead_reception_strict_rebuild_20261103/evidence/b4_isolated_rerun` | **1**（脚本尾部守卫误报，见 §3） | `b4_isolated_rerun/run_ab72884b97f0104c/{states.json, gap_actions.json, source_index.json, README.md}`；stdout `b4_rerun_stdout.txt` `dd03c038…` |
| R2 | coverage 生成器 v7 通道（`build_rows()` 默认，strict_scope=False） | `python evidence/b4_make_coverage_wrapper.py` → `python evidence/b4_coverage_rerun.py` | 0 → **0** | `b4_coverage_rerun/{full_generator_8.json, diagnostics.json, rejected_probe_members.json, freeze.json, generator.py.snapshot, input_sandbox/}`；stdout `b4_coverage_rerun_stdout.txt` `be1428c9…` |
| R3 | 八态准入通道（`build_rows(strict_scope=True)`） | `python evidence/b4_eight_admission_rerun.py` | **0** | `b4_eight_admission_rerun/`（8 文件 + input_sandbox 7 CSV）；stdout `b4_eight_rerun_stdout.txt` `db2955d5…` |

私有副本（公共文件原字节不动）：
- `evidence/b4_make_coverage_wrapper.py` `d48bb421…` — 从 `run_coverage_generator_strict_sandbox.py`（sha `f21dfdab9563ac53fa10c6e54d955264d9ebbccf081b8cf3e58ac0ce6c62f5d7`，与上游 v7 冻结值一致=未改）复制，仅改 `OUT`→evidence 目录与 import 路径；
- `evidence/b4_coverage_rerun.py` `15eb66eaf…` — 上述产物（头部注明源 sha）；
- `evidence/b4_eight_admission_rerun.py` `900cf02dd…` — 仅重定向 `run_eight_terminal_admission.OUT` 后调用其 `main()`。

## 2 通道 R1（登记+去重+coverage 重分类）逐字段差异

上游基准 `strict_rebuild_20261103/run_06c49d9e7ebe0688/`（README `c8fa2679…`、gap_actions `e7ce5ba9…`、source_index `3346f78f…`、states `779dda1c…`）。

| 文件 | 上游 sha | 本轮 sha | 结论 |
|---|---|---|---|
| `states.json` | `779dda1c3fe81718806484b675d4903f144ec945e6fce3d16ea8848b6adfbfac` | `779dda1c…`（同） | **逐字节相同**（48 态：登记审计、去重 decisions、权重、coverage claim 重分类、条件分类全同） |
| `gap_actions.json` | `e7ce5ba931dc42157ce2dd12cd7fbd27d6776ade59d274fa1f537620172a9113` | `217dfeb9465486a3676ab26d5599e6bdea538e47c82885b478a6b26170a9263b` | 46/48 逐态相同；仅 2 态差异（下表） |
| `source_index.json` | `3346f78f0e280bf910c33298845215a8afc0056c69576d97d79b2d11a05b5caf` | `6d69ef5bc69c6ef59526de7bcdcaf32ad97b5a4c531f2a8a1e315e0e040f2701` | `member_sources`、`ec_new_candidates`、`ec_new_candidate_stop`、`rule_basis`、`p1_execution_rule`、`c3_i` **全同**；`input_sha256`、`staged_dmc` 差异见下 |
| `README.md` | `c8fa2679…` | `38d0641a…` | 仅 run_id 行不同（`run_06c49d9e7ebe0688`→`run_ab72884b97f0104c`） |

**run_id 差异的两个输入原因**（`input_sha256` 逐键比对，19→20 键，仅 2 处不同）：

| 输入 | 上游 run 记录 | 现在 | 说明 |
|---|---|---|---|
| `scripts/wp_production/rebuild_strict_isolated.py` | `6cc36a77cb415f3a9e16d9526c52eb3b397713d8ea73f9baf230db804cab1d04` | `468dc00ee21a50f5e8cc605c5e855ec67b4a78823352ce09a6f0cc42a78c0bcd` | 上游 run 之后该脚本被改（文件未跟踪、git 无历史，旧字节不可得，改动内容只能由行为差异推断） |
| `outputs/physics_completion/recovery/candidate_source_metadata_corrections.jsonl` | 不存在 | `bc5eee7912a6305739133a6ff280ef111978e1234ca6f38c3d20f28a2c10346e` | 上游 run 之后创建（DMC 协议元数据更正） |
| 其余 18 输入 | — | — | **与上游 run 记录逐键相同（0 差异）** |

**gap_actions 仅有的 2 态差异（DMC|M_plus、DMC|LiM_2plus）**，均为更正应用的直接后果，字段级：

- `staged_candidate_action`：`"…resolve 3928500_0 protocol-source conflict; C3(i) remains closed"` → `"…apply hash-bound 3928500_0 metadata correction if present; C3(i) remains closed"`。

**source_index.staged_dmc（5 行）差异**（递归比对）：
- 5 行全部新增字段 `protocol_metadata_correction_ids`（= `[]`×4 + `["DMC_3928500_0_PROTOCOL_20261103_V1"]`×1）与 `settlement_protocol_label_original`；
- 行[3]（`leg_id=3928500_0`，即 DMC M⁺ 的第 4 条 staged 记录；行[0]=`3894976_0` 无更正）：
  - `settlement_protocol_label`：`"old protocol (TightSCF)"`（上游）→ `"new_numerical (VeryTightSCF + strict; SlowConv)"`（本轮，应用更正后有效标签）；
  - `settlement_protocol_label_original`：`"old protocol (TightSCF)"` — **更正前值原样保留**（与 B2 台账一致）；
  - `protocol_source_conflict`：`true` → `false`（更正闭合冲突）。

## 3 R1 守卫误报（结构性 bug，独立证明 0 漂移）

脚本尾部守卫（`rebuild_strict_isolated.py:342-343`）：

```python
if {str(p.relative_to(ROOT)).replace("\\","/"): digest(p) for p in INPUTS} != input_hashes:
    raise RuntimeError("An input changed during the isolated rebuild; discard this run")
```

- 起始 `input_hashes` = `INPUTS`（19 键）**+ corrections jsonl（1 键）= 20 键**；末检只遍历 `INPUTS`（19 键）→ 键集永不可相等 → **corrections 文件存在时该守卫必然误报**（bug 由「上游 run 后给起始哈希加 corrections 键、末检未同步」引入）。
- 独立零漂移证明（绕开守卫，直接复算）：重跑结束后重算全部 19 个 `INPUTS` 哈希 vs 本轮起始记录 → **漂移 0**；`states.json` 与上游逐字节相同亦互证。
- 处置：R1 的 4 个产物在守卫触发前已写完，经上述独立验证后保留为证据；**该 run 不用于任何绑定**。
- 最小修复提案（**本轮不执行，公共代码改动需用户确认**）：末检改为 `{**{k:…for k in INPUTS}, **{corrections_rel: digest(corrections)}}` 或直接用 `input_paths = INPUTS + (corrections_path,)` 统一两侧键集，并补一条「corrections 存在时守卫通过」的回归测试。

## 4 通道 R2（v7 coverage 生成器）逐文件差异

| 文件 | v7 sha | 本轮 sha | 结论 |
|---|---|---|---|
| `full_generator_8.json` | `acd48d381e71d8939b0ecbc24b077919a96f8762053e0581c06309e18d9ba15c` | 同 | **逐字节相同**（8 行：AN\|M_plus=single_basin_scope_review，7=pending） |
| `diagnostics.json` | `b53ad6b344412a08cf3ea8c5f6b4199bded23b034f655410aadd85461e163d47` | 同 | 逐字节相同 |
| `rejected_probe_members.json` | `1e93d4f6a09e430dee59f30223411ee3a90903bf2534f01b7918bd2fc280eee1` | 同 | 逐字节相同 |
| `input_sandbox/` 6 CSV | 见 freeze | 同 | **全部逐字节相同**（candidates `20145ec3…`、dedup `c5be5d9c…`、labels `9f5e1e9f…`、structures `f2d94a23…`、weights `b73372ea…`、manifest `a1e28a5a…`） |
| `generator.py.snapshot` | `1fa9501189392669f7416db5d4e60bd0daf331032d401f3cd6edc59417c56ff9` | `ed2b621d30f8df5c2f3088f56012d7ca66447591918b2f00114ff06af2ad6784` | 模块版本差异（§5），**不影响本通道输出**（上三行同字节即证） |
| `freeze.json` | `2bd2343d570200365888af681668d096a3398c3353b8ff7448a67d25f235b2e2` | `5f9cba153452dec96eae97d2a5c1584c2303303613d75ee57f7e8012b96d6e40` | 键数同为 20；差异=①路径键改名（9 对 ADD/DEL 值全同）、②runner 条目互换（v7 记 `run_coverage_generator_strict_sandbox.py f21dfdab…` ↔ 我方记私有副本 `b4_coverage_rerun.py 15eb66ea…`）、③`build_coverage_reviews.py` 条目 `1fa95011…`→`ed2b621d…`（§5 版本链）；**无内容性差异** |

## 5 `build_coverage_reviews.py` 版本链（公共代码盘点·一）

| 版本 | sha256 | 行数 | 内容 |
|---|---|---|---|
| git HEAD | `5a73d88f2d6fc8d9c43e88d76fa1e716723124f2ace8d53015a0e19e4129c137` | 536 | `REVIEW_VERSION=coverage_review_v2_dedup_aware_20261027`；novelty→`multi_basin_coverage` |
| v7 快照（v7 run 所用） | `1fa9501189392669f7416db5d4e60bd0daf331032d401f3cd6edc59417c56ff9` | 543 | **v3** `coverage_review_v3_strict_basin_guard_20261103`：+7 行（novelty 单独不证第二合格盆地→`single_basin_scope_review`、verdict 清单扩容、文档措辞） |
| 当前工作树（本轮 R2/R3 所用，git ` M` **未提交**） | `ed2b621d30f8df5c2f3088f56012d7ca66447591918b2f00114ff06af2ad6784` | 558 | v7 + 15 行：`strict_member_evidence_required` 早返回、`build_rows(*, strict_scope=False)`、`coverage_registration_required` 路线 |

- `strict_scope=True` **唯一调用方** = `scripts/wp_production/run_eight_terminal_admission.py:53`（未跟踪，sha `20e0e987…`）；生产 coverage 主通道（`build_coverage_reviews.py:532/552`）走默认 `False`。
- `run_coverage_generator_strict_sandbox.py` 现行 sha `f21dfdab…` = 上游 v7 冻结值 → **未改**。
- v3 升级与 strict_scope 均处于**未提交工作树状态**（HEAD 仍 v2）——属上游交付工作面；本轮不提交、不改（正式发布另行确认）。

## 6 通道 R3（八态准入 strict_scope）逐文件差异

`eight_admission_v2/`（上游，11:25 生成，其 freeze 记录模块 = 当前 `ed2b621d…`）。

| 文件 | 上游 sha | 本轮 sha | 结论 |
|---|---|---|---|
| `full_generator_8.json` | `acd48d38…` | 同 | 逐字节相同 |
| `diagnostics.json` | `b53ad6b3…` | 同 | 逐字节相同 |
| `full_obligation_generator_8.json` | `7ce00c57e7721e1a38e0a247111b4c6c54a7f199a1d89b6b85676f386978c784` | 同 | **逐字节相同**（strict_scope 路线：AN=single_basin_scope_review；DEC/GBL/PC/TMP\|M=coverage_registration_required；TMP\|LiM_2plus、TMP\|M_plus=strict_member_evidence_required） |
| `member_terminal_dispositions.json` | `b12c5c71…` | 同 | 逐字节相同 |
| `rejected_probe_members.json` | `1e93d4f6…` | 同 | 逐字节相同 |
| `generator.py.snapshot` | `ed2b621d…` | 同 | 逐字节相同（模块自 11:25 起未变） |
| `input_sandbox/` 7 CSV | 见 freeze | 同 | 全部逐字节相同（含 `…_with_terminal.csv` `f798152c…`） |
| `terminal_input_sha256.json` | `d004b775…` | `0edf03d6…` | **纯路径改名**：唯一 ADD/DEL 对的值 `f798152c…` 完全相同，仅键前缀 `remote_closure_20261103/eight_admission_v2`↔`lead_reception…/evidence/b4_eight_admission_rerun` |
| `freeze.json` | `3a187b76…` | `8053eb54…` | 8 组 ADD/DEL 纯路径改名，**每对 sha 全同**（snapshot `ed2b621d…`、6 sandbox CSV、rejected `1e93d4f6…`） |

## 7 正式标签与费用未变（起止哈希，全部实测）

| 共享面文件 | 本轮起始 | 复跑结束后 | 结论 |
|---|---|---|---|
| `production_ensemble_labels.csv`（正式标签） | `c21003f5e18a2faaf4e3c8e91c379ea3ab16659706d13786ed25df0038ae0c80` | 同 | 未变 |
| `cost/ensemble_cost_by_family.csv`（费用） | `e92fbeeb4a29842c4571779af48194fad55eeeea11c766ee8a26a3968256e51a` | 同 | 未变 |
| `production_ensemble_weights.csv` | `201e19545bf0c1ccc209ca017e4ed55c581085d15ceb1df117f31f7e36494101` | 同 | 未变 |
| `recovery/coverage_reviews.csv` | `e89188f6eac28bbf2dd309a95ec19ea9b1cc78969a262883820f939eec28ba40` | 同 | 未变 |
| `production_ensemble_candidates.csv` | `6096cd125210e0fe8428d526e3932cc56489ba92c2d11d4a2d84084434e58efa` | 同 | 未变 |
| `production_ensemble_dedup.csv` | `1f3ea92971d9725f407109d6a3c121b18aa4af13f80331e891ee612247377c04` | 同 | 未变 |
| `production_ensemble_structures.csv` | `3a795ce8680e84ec0e60ef0411c78fb8236daf492e8647ebec25efbebc96732b` | 同 | 未变 |
| `production_ensemble_dispositions.csv` | `56bbc82c36637b9e04d9ed12085ceb15f49989d650db004a7e85b50f61a1bee8` | 同 | 未变 |

三条复跑通道全部只读上述文件、只写 `evidence/` 新目录；`git status` 中的其他 ` M` 文件为上游交付时既有工作树状态，本轮未触碰。

## 8 重复/歧义/缺失与不猜配对

- 三条通道产物互不覆盖（各自新目录，含 `refusing to overwrite` 防护）；无重复计费面（R1–R3 零计算，不产生任何 cost 记录）。
- 上游 run 旧脚本字节 `6cc36a77…` **不可得**（文件未跟踪、git 全历史无此文件）→ 旧版对 corrections 的处理细节无法逐行 diff；只能由「18/19 输入相同 + staged_dmc/gap_actions 的更正字段差异」推断为「corrections 应用逻辑随后加入」。**此为未确定事项，不猜。**
- 调度数组别名完整映射属 B1（另行交付 `B1_scheduling_mapping.{md,csv}`），本报告不重复。

## 9 结论

1. **可复现性**：登记+去重+coverage 重分类核心产物 `states.json` 与上游逐字节相同；两条 coverage 生成通道的全部语义产物（含 strict_scope 全量义务视图）逐字节相同；全部差异收敛为（a）DMC 元数据更正的应用（有 before/after 台账）、（b）run_id/路径键、（c）公共脚本自身 sha 变化。
2. **正式标签与费用未变**：8 个共享面文件起止哈希全等（§7）。
3. **守卫误报**：`rebuild_strict_isolated.py` 末检键集与起始键集结构性不匹配，corrections 存在时必误报；已独立证明运行期间 0 输入漂移；最小修复提案待用户批准后另行执行（含回归测试与独立复审）。
4. **公共代码**：本轮零改动、零提交；v3 覆盖口径与 strict_scope 仍为未提交工作树状态，维持原样。
5. **绑定判定**：与 B3 一致——本轮无通过 Task A 的覆盖证据对象，**未绑定、未手填 resolved、未改 `coverage_route()`**。

## 10 未确定事项 / 是否需要新物理证据

- 无新增物理证据需求（本任务纯工程对账）。
- 未确定：① 旧脚本 `6cc36a77…` 具体改动行（字节不可得）；② 上游 v7 run 与 eight_admission_v2 之间模块 `1fa95011→ed2b621d` 的提交/作者归属（工作树未提交，git 无记录）——均不影响本轮输出同一性结论（同字节产物互证）。
