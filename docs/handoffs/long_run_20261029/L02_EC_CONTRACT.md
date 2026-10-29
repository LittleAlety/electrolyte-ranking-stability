# L02 EC 机器合同修正与负向用例（2026-10-29）

范围：只修 **机器合同**，不创建提交包、不申请预算、不提交任何作业。
依据：`docs/plans/CORE_PLAN_EXECUTION_SUPPLEMENT_20261029.md` §5.2。

## 1. 改了什么

| 项 | 改前 | 改后 | 理由 |
|---|---|---|---|
| `RESOURCE_PROFILES["orca_production_4h_v1"]["attempts_ledger_required"]` | `False` | **`True`** | 补充计划 §5.2 明写「必须在此新 profile 范围内强制真实账本」；历史 profile（`orca_production_v1` / `xtb_*` / `h2_*` / `12h_*`）语义**未动** |
| 新增 `scripts/wp_production/ec_recovery_contract.py` | — | 纯函数合同 | 把「p4→p7、一次在飞、≤2 次提交、16 CH/元素、32 CH 帽、错候选/低报/第三腿拒绝」变成**机器可验**，供 L03 建包器与提交器共用 |

`ec_recovery_contract.py` 的固定常量：`EC_CANDIDATES=("ec_v2_p4","ec_v2_p7")`、`EC_PROFILE="orca_production_4h_v1"`、`EC_CORES=4`、`EC_WALL_HOURS=4`、`EC_ELEMENT_CORE_HOURS=16`、`EC_CAP_CORE_HOURS=32`、`EC_MAX_SUBMITTED_ELEMENTS=2`。

- `next_candidate(history)`：未提交 ⇒ p4；p4 在飞 ⇒ `None`；p4 通过 ⇒ `None`（campaign 结束）；p4 终态失败 ⇒ p7；p7 已提交 ⇒ `None`（**永无第三腿**）。
- `check_campaign_contract(...)` 依次拒绝：未登记候选、非下一步（p7 抢跑）、错 profile、错核数、错墙钟、元素数 ≠ 1、**低报预留**（声明值 ≠ 16×元素数）、第三腿、超 32 CH 帽、已有 active/pending。全部 `raise ContractViolation`（fail-closed，调用方无法降级为告警）。

## 2. 负向用例（`tests/test_ec_recovery_contract.py`，18 项）

覆盖四类点名拒绝 + 资源形状：
1. **漏账本**：断言 `orca_production_4h_v1.attempts_ledger_required is True`（且历史 profile 保持原语义）；
2. **错候选**：`ec_v2_p3` 拒、`p7` 抢跑拒；
3. **低报预留**：声明 8 CH 拒；
4. **第三腿**：已提交 2 个仍投拒；
5. 另含：超帽、active/pending 在飞、错 profile/核数、多元素在飞、p4 通过即停、p4 失败才开 p7。

## 3. 验证（全部只读、零计算）

```text
pytest tests/test_ec_recovery_contract.py tests/test_wp2_cost_semantics.py tests/test_scripts_index.py -q  -> 26 passed
pytest tests/test_repo_layout.py tests/test_submit_hpc_batch.py tests/test_evidence_gate_and_cost.py -q     -> 59 passed
work/_validate_ec_v2_presubmission.py                                                                      -> 5 passed, 0 failed
```

`work/_validate_ec_v2_presubmission.py` 末行仍为 `Status: HOLD (awaiting user approval)`。

## 4. 边界（防误读）

- 本步**没有**创建 `tasks/`、`batch_*.txt`、`sbatch`、`PACKAGE_SHA256SUMS`，**不是**可提交包——那是 L03。
- 本步**没有**申请或占用任何 core-hour；`32 CH` 仍是**提议**，不是已批准额度。
- `attempts_ledger_required=True` 只改变**未来**对 `orca_production_4h_v1` 的提交要求，未回溯任何历史包。

## 5. 下一步

L03：按 schema-2 生成 `p4` 单腿可执行 HOLD 包（与 `build_dol_ec_recovery_package.py` 同形；p7 只留不进入生产候选表的模板），并用真实加载器/提交器门函数离线验证；L04 并行诊断 DMC 历史过程。


## 6. 2026-10-29 收尾：合同已接入**真实提交入口**（此前只接在建包器）

- 接入点：`submit_hpc_batch.submit_batch()` 在 `_load_package` → `submission_resources` → 账本/profile 校验
  → journal/锁重复检查**之后**、`doctor`/远端锁/`squeue`/submit **之前**调用 `_enforce_ec_contract(...)`。
  任何拒绝都发生在**零副作用**处（负向用例断言 fake runner 调用数 = 0）。
- 状态来源（不信任调用方布尔值）：包内 `manifest.json` + `tasks/<...>/candidate.json` + `geom.xyz` 现算 SHA
  + **共享 campaign 账本** `work/ec_recovery_v2_campaign/attempts_ledger.json`（在包目录旁，**不随拆包清零**）。
- 门规则（合同 `next_candidate`）：未提交 ⇒ p4；p4 在飞 ⇒ 停；p4 accepted ⇒ 停；p4 终态但 `accepted` 缺失/None ⇒ 停；
  证据不完整 ⇒ 停；p4 明确未通过且证据完整 ⇒ 才开放 p7；p7 已提交 ⇒ 停（永无第三腿）。
- 未知响应：bridge 失败/无 JobID 一律记 `submission_unknown`（submitted=True、terminal=False、accepted=null），
  保守占用次数与 16 CH 预留；只有 journal + 调度证据才能解除。
- 提交成功后由提交器**追加** campaign 账本条目（accepted 写显式 null，不写 false）。
- 旧 profile（`orca_production_v1`/`12h`/`xtb_*`/`h2_*`）不进入该分支，行为不变（有正向回归测试）。
- 测试：`tests/test_ec_submit_entry.py` 18 项（p4 抢跑、第三腿、p4 accepted/未知/缺字段/证据不全、超预算、
  低报预留、缺账本、并发第二腿、输入偷换、候选偷换、campaign 几何不符、旧 profile 不变、拒绝无 journal）；
  反向证明：移除接入块后这些入口测试失败（`work/_red_ec_entry.py`，RED PROVEN，生产字节已还原）。
- 真实 HOLD 包 `work/hpc_ec_recovery_v2_p4_20261029/` 经同一入口函数离线验证：30/30（`work/_validate_ec_package_loader.py`）。

### 6.1 入口审查后的加固（2026-10-29 收尾，t11 独立审查 R1/R2/R3/R5/R6/R7/R9）

- **R1 HOLD 强约束**：入口现在要求 `submission_gate == "OPEN"` 且 `submitted is False`；
  `HOLD` 包**无法通过真实提交入口**（此前 HOLD 只是散文，提交器全文不读它）。
- **R2 身份绑定（防"改 profile 绕过"）**：EC 身份由**包名**（`hpc_ec_recovery_v2*`）、
  `resource_profile` 或 `campaign_contract` 任一命中即触发；触发后**必须**使用 `orca_production_4h_v1`，
  否则拒。改 manifest 的 profile 不再能降级到 800 CH/免账本的旧口径。
- **R3 campaign id 必填**：`campaign` 缺失即拒；与共享账本 `campaign_id` 不一致即拒（不再用 `None in (None, X)` 放行）。
- **R5 账本改名**：共享战役账本改为 `ec_recovery_v2_campaign/campaign_ledger.json`，与包内通用
  `attempts_ledger.json` 区分，避免"两份同名不同架构"的误用。
- **R6 预留下限**：若 manifest 声明 `first_batch_reserved_core_hours`，它必须 ≥ 16×元素数，否则拒。
- **R7 CLI 契约**：`--attempts-ledger` 文件缺失/不可读转为 `REFUSED` + exit 2（不再 traceback）。
- **R9 合同版本留痕**：入口把合同模块 sha256 写入战役账本条目（`contract_sha256`）。
- **残余（未在本任务解决，如实登记）**：R4 战役账本本身可被改写（无哈希链）；R8 本地 journal/账本同时被删时
  「从未提交」无法与「被删除」区分；R10 已随 R2 一并解决。
