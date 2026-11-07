# CLAIMS_AUDIT —— 本轮报告 7 条具体声明的独立复核（audit_claims_20261023）

> 复核人：wp2-gap-triage（独立会话；只读审计，零改动：未触碰 `scripts/**`、`tests/**`、`outputs/**`；只写本目录 + `work/_tc*` 临时探针）
> 复核时间：2026-10-24 15:30–17:30（期间仓库有并发写入；对会动的输入一律以复核时刻实测为准并注明）
> 可复跑验证：本目录 `verify.py`（`exit 0` = 7 条全证实；`exit 1` = 有未证实项；当前实测 **exit 1，4/7 证实**）

## 总判定表

| # | 声明 | 判定 | 一行证据 |
|---|---|---|---|
| C1 | 严格总闸门恰好 3 个缺口：`ensemble_not_48_accepted`、`wp5_full_target_pool_evaluated`、`execution_cost_provenance_complete` | **部分证实（历史口径）/ 当前已过时** | 用 `derive_checks()+strict_readiness()` 实测：当前 `blocked_by` = **2** 缺口（`ensemble_not_48_accepted` + `wp5_full_target_pool_evaluated`）；第 3 项 `execution_cost_provenance_complete` 已在 **P7（commit 9f347cd，"3 → 2"）闭合**——Lead 自己的提交信息记录了这个迁移，声明是 P7 之前写的 |
| C2 | 系综 44 accepted / 4 limited；四态 DMC 两态 + DOL/EC LiM_2plus；四态 `limitation_reason` 均 `rescue_budget_exhausted`；覆盖复核分级 DMC 两态 `unresolved_qc`、DOL/EC `search_exhausted` | **证实** | labels CSV：44/4 恰好；四态身份逐一比对一致；四态 reason 全部 `rescue_budget_exhausted`；`coverage_reviews.csv` route 列：DMC 两态 `unresolved_qc`，DOL/EC `search_exhausted` |
| C3 | DMC 两态各有 7 个从未被合法探过的登记二面角 | **证实** | `torsion_freedom_registry.csv` 每态 10 个登记二面角；structures 账本里每态已探 `tors_6/7/8_0_1_2`（3 个，全部属被声明无效的 v1 刚性族 `{6,7,8}-0-1-2`）；10 − 3 = **7 个未探且合法**，与 P3 JSON `group_1 raw=7` 相互印证 |
| C4 | `DOL\|LiM_2plus\|c05` 是 QC 通过（computed）且是加权成员 | **证实** | structures 最新 attempt=1 `status=computed`（`analytical_hessian`）；weights 表恰一行、`boltzmann_weight=1.000000000`（n_unique=1，即它承载全部系综权重）；dispositions `disposition=computed`、reason `scientific QC passed`——三处一致 |
| C5 | 测试套件声明式 skip 恰好 8 个 | **未证实（当前实测 9）** | 按 task 指定口径（`pytest -q -rs`，排除 orca_run/toolchain/bundled_toolchain/orca_input）实测 **9** 个 SKIPPED：7×week36（`结题提交包尚未构建`，模块级 `skipif`）+ 1×hpc_numfreq（`external raw continuation fixture … unavailable`——实测 fixture `work/wp2prod/DEC/LiM_2plus/DEC_LiM_2plus.log.stdout.tmp`、`…​.xyz` 当前不存在）+ 1×submit_budget_gate（`attempt_ledger.json not built yet`）。若声明时点 fixture 齐全则是 8——但**当前树**上无法复现 8 |
| C6 | 链 79/79 全绿 | **未证实（实测 78/79）** | `pwsh -NoProfile -File scripts/wp_production/finalize_wp2.ps1`（无 -Commit）实测 **79 步中 78 绿、`pytest-offline` 红**（ABORT，exit 1）。链内 pytest 3 项失败：`test_orca_run::…clears_a_stale_density…`、`test_toolchain::…probe_version…`、`test_round3_adversarial_audit::…audit_claim_scope…`；**三项隔离重跑全部绿**。隔离再跑同一 pytest 命令，失败集在 13→5 项间漂移（week19–23 report render 漂移 + terminal_site payload 漂移 + refreeze_manifest），同样逐项隔离绿 |
| C7 | `P3_CANDIDATES_20261023.json` 的计数（raw/accepted/refused）与 MD 表格逐格一致 | **证实** | 从 JSON 重算 8 个 (态×组) 单元格：raw/accepted/refused 与 MD 表全部一致（DMC|M_plus 7/3/4、DMC|LiM_2plus 7/1/6 与 6/3/3、DOL/EC 30/9/21、组2 DMC|M_plus 0/0/0）；拒因分布一致（equivalent_start/li_coordination_changed/ring_broken 各计数）；heavy 位移抽样一致（0.2743/0.2432/0.0000-甲基、0.4874、pucker 0.0375–0.0771 与 0.0199–0.0549、Li 0.15/0.30/0.45）；恒等式 raw=accepted+refused 全部成立 |

---

## 逐条详情（命令 + 原始输出摘要）

### C1 —— 总闸门缺口数

**命令**（可复跑，见 `verify.py` c1）：
```
.venv/Scripts/python.exe -X utf8  # 内联：
  sys.path += scripts/wp_production
  checks = strict_readiness_wiring.derive_checks()
  verdict = strict_readiness.strict_readiness(labels, {(n,s) for ...}, checks)
```
**实测输出**：
```
blocked_by: ['ensemble_not_48_accepted', 'wp5_full_target_pool_evaluated']
execution_cost_provenance_complete  passed=True
wp5_full_target_pool_evaluated      passed=False  problems=[('A','knn_baseline','random') n_pool=11 is not the full 12-molecule cohort, …×32 组]
```
- **缺口 1** `ensemble_not_48_accepted`：4 个非 accepted 态 = DMC|M_plus、DMC|LiM_2plus、DOL|LiM_2plus、EC|LiM_2plus（与 C2 一致）。
- **缺口 2** `wp5_full_target_pool_evaluated`：`AB_axis_endpoint.csv` 全部 32 个 (task, model, baseline) 组 `n_pool` ∈ {11, 9} ≠ 12（qc_complete_pair 子集——B 池缺 DOL|LiM_2plus 与 EC|LiM_2plus 的完整对、A 池缺其一腿），每组的逐项 reason 都在 `derive_check_details()` 里。
- **缺口 3（声明的）** `execution_cost_provenance_complete`：**当前 passed=True**。提交记录：`9f347cd P7：接出上游已声明的 cost_scope —— 严格闸门第 3 个缺口闭合（3 → 2）`。结论：声明记录的是 P7 前的事实；**当下口径应为 2 缺口**（README 顶部最新口径也是 2，与本实测一致）。

### C2 —— 44/4 与覆盖分级

**实测**：`production_ensemble_labels.csv` 计数 `{'accepted': 44, 'limited': 4}`；四态集合与 reason 逐一断言通过。`coverage_reviews.csv`（14 行）route 列：DMC 两态 `unresolved_qc`、DOL/EC `search_exhausted`（verdict 列相应为 `unresolved`/`search_exhausted`，evidence_note 原文与 P0 手册一致）。

### C3 —— DMC 未探二面角

**实测**（`work/_tc3_tors2_out.txt`）：
```
M_plus:    registered(10) probed(3)=[tors_6_0_1_2, tors_7_0_1_2, tors_8_0_1_2] unprobed(7)
LiM_2plus: registered(10) probed(3)=[同上]                              unprobed(7)
probed inside {6,7,8}-0-1-2 family: 全部 3 个
```
已探的 3 个全部属 `{6,7,8}-0-1-2`（即被声明无效的 v1 刚性族，三者是 0-1-2 端的甲基/H 终端等价族），10−3=7 成立。交叉印证：P3 JSON 两态 `group_1_registered_torsions.raw = 7`。

### C4 —— DOL|LiM_2plus|c05 三处一致

**实测**（`work/_tc4_c05_out.txt`）：
```
structures: attempt0 superseded / attempt1 status=computed (analytical_hessian)
weights:   DOL|LiM_2plus|c05 attempt=1 g_single_kcal=-172980.167708 boltzmann_weight=1.000000000
dispositions: disposition=computed reason='scientific QC passed'
label: DOL|LiM_2plus n_unique=1 n_members=1 G_ens=-172980.167708  (= 该成员 g_single)
```
权重=1.0 说明它是 n_unique=1 态的全部系综成员——"加权成员"与标签 G_ens 闭环一致。

### C5 —— 声明式 skip 计数

**命令**：`pytest tests -q -rs -p no:warnings --ignore=…（4 个排除项，按 task 指定）`
**实测 9 个**（`work/_tc5_pytest.txt`）：
| # | 位置 | 理由 |
|---|---|---|
| 1 | `test_hpc_numfreq_import.py:83` | external raw continuation fixture or its original local source is unavailable |
| 2 | `test_submit_budget_gate.py:88` | attempt_ledger.json not built yet (declared unavailable) |
| 3–9 | `test_week36_final_submission.py:49/56/63/70/78/86/93` | week36 结题提交包尚未构建（模块级 `pytest.mark.skipif`，`outputs/week36` 目录不存在） |

判定为**未证实**的依据：8 ≠ 9。最可能的解释是声明时点 `hpc_numfreq` 的外部 fixture（`work/hpc_results/3650157` + `work/wp2prod/DEC/LiM_2plus/DEC_LiM_2plus.log.stdout.tmp`/`.xyz`）部分在盘，使那一跳不发生；**当前树**上 `DEC_LiM_2plus.log.stdout.tmp` 与 `DEC_LiM_2plus.xyz` 不存在（该腿目录现存 `DEC_LiM_2plus.log`、`DEC_LiM_2plus_opt.xyz`——文件名已变），故 9。这不是 8 的证伪，但"恰好 8 个"在当前仓库**不可复现**。

### C6 —— 收口链步数

**命令**：`pwsh -NoProfile -File scripts/wp_production/finalize_wp2.ps1`（无 -Commit；日志 `work/_chain_audit_claims_20261024.log`，跑前已核对无并行链在跑）
**实测**：链共 **79 步**（含本轮新增的 `strict-recovery` 步）；**78 步 exit 0**；`pytest-offline` exit 1 → `ABORT`。
```
=== pytest-offline (exit 1) ===
    FAILED tests/test_orca_run.py::test_run_orca_clears_a_stale_density_left_in_the_scratch_directory
    FAILED tests/test_round3_adversarial_audit.py::test_round3_audits_rebuild_byte_identically[scripts/audit_claim_scope.py]
    FAILED tests/test_toolchain.py::test_probe_tool_captures_version_from_fake_binary
ABORT: failed dependency -> pytest-offline
```
**追因**：上述 3 项**隔离重跑全部通过**；用链同款 pytest 命令整体隔离重跑，失败集漂移为 13 项（week19–23 report `render_matches…/check_is_green` + terminal_site 4 项 + refreeze_manifest 1 项 + round2_closeout 等），再次重跑又变 5 项——**非确定、非 flake-by-timeout，而是套件内状态串扰 + 仓库 mid-flight**（本轮 Lead 的 docs 重组提交 `038a34e` 与 site/周报产物处于中间态；且链自身前段生成器会先写产物再 --check，审计会话无法在不越权的前提下把它收齐）。结论：**79/79 全绿在当前树上不可复现**；如实记录 78/79 + 红步骤名与红项明细。

### C7 —— P3 候选计数逐格比对

**命令**：见 `verify.py` c7（从 JSON 重算并与 MD 表格断言）。
**实测**（`work/_tc7_full_out.txt` + `work/_tc7_mdcheck_out.txt`）：
| 态 | 组 | JSON (raw/acc/ref) | MD 表 | 拒因分布 | 判定 |
|---|---|---|---|---|---|
| DMC\|M_plus | 组1 | 7/3/4 | 7 raw→接受3/拒4 | equivalent_start×4 | 一致 |
| DMC\|M_plus | 组2 | 0/0/0 | 0（无环、无 Li） | — | 一致 |
| DMC\|LiM_2plus | 组1 | 7/1/6 | 7 raw→接受1/拒6 | equiv×1 + li_coord_changed×5 | 一致 |
| DMC\|LiM_2plus | 组2 | 6/3/3 | 6 raw→接受3/拒3 | equivalent_start×3 | 一致 |
| DOL\|LiM_2plus | 组1 | 0/0/0 | 0（无登记扭转） | — | 一致 |
| DOL\|LiM_2plus | 组2 | 30/9/21 | 30 raw→接受9/拒21 | ring_broken×12 | 一致 |
| EC\|LiM_2plus | 组1 | 0/0/0 | 0 | — | 一致 |
| EC\|LiM_2plus | 组2 | 30/9/21 | 30 raw→接受9/拒21 | ring_broken×12 | 一致 |

heavy 位移抽样也逐格一致：DMC|M_plus 接受 3 项 = {0.2743, 0.2432, 0.0000(甲基转子，`probe_class=methyl_rotor` 恰 1 个)}；DMC|LiM_2plus 组1 = {0.4874}、组2 = {0.15/0.30/0.45}；DOL pucker 范围 [0.0375, 0.0771]（6 项）、EC [0.0199, 0.0549]（6 项）；ring_broken 恰 12 项（±0.60/±0.80 振幅）。恒等式 `raw = accepted + refused` 全部成立。

---

## 不符/疑点汇总（复核过程中的独立发现）

1. **C1 已过时（非错误）**："3 缺口"是 P7 之前的口径；`9f347cd` 明确写"3 → 2"。若报告重发，应更新为 2 缺口（README 已是 2）。
2. **C5 的 8→9 差一**：`work/wp2prod/DEC/LiM_2plus/` 下 `DEC_LiM_2plus.log.stdout.tmp`/`DEC_LiM_2plus.xyz` 两个文件当前不存在（现存 `.log` 与 `_opt.xyz`），使 hpc_numfreq 的 skip 在当前树发生。若这两个文件名是被有意重命名的（协议 v1.3 迁移），该 skip 理由字符串里的 fixture 期望也值得跟着更新——否则它会被读成"外部结果丢了"而不是"文件名迁移了"。
3. **C6 的红是仓库中间态**：docs 重组提交（`038a34e`）之后 site/周报生成器与产物不同步；链的 pytest-offline 在套件内被前面测试污染后表现不稳定（3→13→5 项漂移）。这不是"声明造假"，但"链全绿"在当前 HEAD **不成立**，需要重跑 site/周报生成器并提交产物后再宣称。
4. `execution_cost_provenance_complete` 的闭合质量我没有深查（那属于 task-9 的取证范围）——本条只确认它在当前树为 True。

## 未覆盖范围

- **未验证 `execution_cost_provenance_complete=True 的闭合证据质量**（DEC 两腿 cost_scope 的血缘）——属并行 task-9 的范围；我只确认了闸门位的布尔值。
- **未复核 P4 提交门/预算不变量**（`P4_SUBMISSION_GATE_20261023.md` 等）——不在本任务 7 条声明内。
- **未在干净克隆上复跑**：本审计在本机工作树（含 `work/` 本地层）进行；C5/C6 的 skip 与失败集**依赖机器本地状态**，干净克隆上的数字可能不同（尤其 hpc_numfreq fixture 与 ORCA 工具链）。
- **C6 未做根因修复**：把链收绿需要重跑 `build_terminal_site.py`、周报生成器等——写入产物超出本审计"零改动"边界，留给 Lead。
- 探针脚本 `work/_tc*.py`、链日志 `work/_chain_audit_claims_20261024.log`、pytest 原始输出 `work/_tc5*.txt`、`work/_tc6*.txt` 均留存于 `work/`（gitignored），未清理以便复查。
