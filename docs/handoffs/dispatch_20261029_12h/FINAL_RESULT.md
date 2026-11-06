# 12 小时执行单 · 最终结果（dispatch_20261029_12h）

- 接收/开始：**2026-10-29 09:26（北京时间）**，`received_at=started_at=2026-10-29T01:26:35Z`
- 期限：**2026-10-29 21:22（北京）/ 13:22 UTC**；**最终版（2026-10-29 提交）**，`commit=a065e7f`
- 基线 HEAD：`6a5f9ef`（`site: repo-inventory refresh after L14 handoff`）
- 角色：Lead 单写入者；两名子会话（`gate-code-auditor`、`dol-log-auditor`）只读、只写各自目录
- 计算授权：**没有新增**；本任务未提交任何作业、未调用 bridge submit、零 core-hour

## 1. 三项任务状态

| 任务 | 状态 | 证据 |
|---|---|---|
| 一、EC 合同接入真实提交入口 | **完成** | 代码 + 21 项入口测试（全部负向断言 fake runner 调用数=0）+ 22 项合同测试 + RED PROVEN + 真实包 31/31 |
| 二、DMC 起点独立性更正 | **完成** | 坐标现算表 + 汇总 + 更正版机制判断 + 2 项回归测试 + 独立复核 |
| 三、一致性收口与最终交付 | **完成** | L02/L03/L04/L05/L09/L10 已更新；核心方案 §22 已加；finalize 与镜像/页面复跑见 §5 |

## 2. 任务一：EC 真实提交入口（文件与调用链）

- 接入点：`scripts/wp_production/submit_hpc_batch.py` 的 `submit_batch()`，
  **在** `_load_package` → `submission_resources` → 账本/profile 校验 → journal/预留重复检查**之后**，
  **在** `doctor`/远端锁/`squeue`/submit **之前**调用 `_enforce_ec_contract(...)`。
  任何拒绝都发生在**零副作用**处（负向测试断言 `FakeRunner.calls == []`）。
- 状态来源（不信任调用方布尔值）：包内 `manifest.json`、`tasks/<...>/candidate.json`、`geom.xyz` 现算 SHA、
  以及共享战役账本 `work/ec_recovery_v2_campaign/campaign_ledger.json`。
- 门规则：未提交⇒p4；p4 在飞/accepted/`accepted` 缺失/证据不全⇒停；p4 明确未通过且证据完整⇒才开放 p7；
  p7 已提交⇒停（永无第三腿）。bridge 失败或无 JobID ⇒ `submission_unknown`（submitted=True、terminal=False、
  accepted=null），保守占用次数与 16 CH 预留。
- **独立审查（t11）发现的 R1/R2 已修**：① `submission_gate != OPEN` 或 `submitted != false` 直接拒（HOLD 机器强制）；
  ② 身份绑定（包名 `hpc_ec_recovery_v2*` / profile / `campaign_contract` 任一命中即必须用 EC profile），
  改 manifest profile 不能降级到 800 CH/免账本；③ campaign id 必填；④ 战役账本改名 `campaign_ledger.json`；
  ⑤ 作业级预留下限；⑥ CLI 账本缺失转 `REFUSED`+exit 2；⑦ 合同模块 sha 记入账本。
- 旧 profile（`orca_production_v1`/`12h`/`xtb_*`/`h2_*`）不进入该分支（有正向回归测试）。
- 真实 HOLD 包 `work/hpc_ec_recovery_v2_p4_20261029/`：入口函数**拒绝**（HOLD）；仅把 gate 改 OPEN 的临时副本通过 31/31。
- **残余风险（如实）**：R4 战役账本本身可被改写（无哈希链）；R8 本地 journal 与账本同时被删时无法区分
  「从未提交」与「被删除」。

## 3. 任务二：DMC 起点独立性（现算数字与更正）

- **M_plus**：账本 7 条 attempt、6 条有作业号、**5 个不同输入坐标**（含 primary 历史输入）；
  `tors_6/7/8` 三份输入坐标**逐位相同**（坐标规范化 SHA `dde1eae5…`；文件 SHA 不同仅因第 2 行标签）。
- **LiM_2plus**：8 条 attempt、7 条有作业号、**6 个不同输入坐标**；
  `tors_6`/`tors_7`（v1，pending）/`tors_8` 输入坐标相同（`b87e3637…`）；`tors_7` 另有 fragmentfix
  （`913df88c…`）与 reopt_v3（`a4c49688…`）两个不同输入。
- **根因（已核实）**：历史包建于 **2026-10-22 15:05**，早于 `prior_starts`/`equivalent_start` 守卫接入
  `_build_state`（`30ace3a`，**2026-10-23 22:40**）⇒ 当时未拦下「同轴同片段」的三个 dihedral；
  **当前代码拒绝**（实测 `equivalent_start=True`、`validate_candidate_start → rigid_transformation`）。
- **更正**：原「不同自由度探针塌缩到同一平底谷」不成立；这 5 条腿是**同一起点的重复计算**，
  成本与失败记录保留，但不计为独立起点探索。数值（12 行 × 5 比值）不受影响。
- **机制判断改为唯一 ID**：`START-GEN-1`（先修生成并按结果坐标去重；本地零成本）为前置；
  `OPT-COORD-1`（原 B，优化器坐标/信赖域）保留但证据仅 1 个独立 M_plus 输入；`LI-SHELL-1`（原 A）与
  `PREOPT-GFN2-1`（原 C；注意旧草案 B=GFN2 预优化）首轮不推荐。DMC 仍停止，不因本任务启动。
- 回归测试：`tests/test_build_torsion_probe_package.py` 新增 2 项（同轴同片段两 dihedral 生成相同坐标；
  门对相同坐标第二起点拒绝）。
- 独立复核：`dol-log-auditor` 的 `L04_DMC_TRACE_RECHECK/REPORT.md`（17 项 16 成立，唯一不符即本更正）
  与 `agent_recheck_dmc_independence/RECHECK_START_INDEPENDENCE.csv`（12 条探针输入，坐标 SHA 独立复算一致）。

## 4. 科学状态（未变）

- 系综 **45 accepted / 3 limited / 0 provisional**；严格就绪 **5/6**（唯一未过 `wp5_full_target_pool_evaluated`）；
  WP5 池 **A=11 / B=10**；三态限制与 DMC 停止裁决均未变。
- 本任务**不改变**任何 accepted、阈值或验收口径；`submission_gate` 仍 HOLD，EC 32 CH 与 DMC 任何新预算仍**未获授权**。

## 5. 测试与检查（实测）

| 命令 | 结果 |
|---|---|
| `pytest tests/test_ec_submit_entry.py tests/test_ec_recovery_contract.py -q` | exit 0（43 项） |
| `pytest tests/test_build_torsion_probe_package.py -q` | exit 0（14 项） |
| `pytest 定向 8 文件 -q`（入口/合同/探针/证据门/提交器/路由/严格/成本） | exit 0（130 项） |
| `work/_red_ec_entry.py`（移除入口强制，期望失败） | **RED PROVEN**，生产字节已还原 |
| `work/_validate_ec_package_loader.py` | **31/31**（HOLD 被拒；gate OPEN 临时副本通过） |
| `pytest tests -q`（离线全量，排除 3 个实机节点 + 2 个 deselect） | 见 §5.1 |
| `pwsh -File scripts/wp_production/finalize_wp2.ps1`（不带 -Commit） | 见 §5.1 |
| `build_production_ensemble_aggregator / coverage_reviews / plan_compliance / wp2_closure --check` | 全部 exit 0 |

### 5.1 收口链结果（如实）

- 首跑 `finalize_wp2.ps1` 在 `pytest-offline` 失败：`tests/test_sbatch_syntax_gate.py` 3 项
  （根因：从 pwsh 启动时 PATH 无 `bash`，`subprocess.run(["bash","-n"])` 抛 FileNotFound）；
  已修 `build_frontier_legs._bash_executable()`（PATH → DSH 自带 bash → Git/Cygwin，找不到则响亮拒绝），
  并加 1 项解析测试；重跑结果见文末「复跑追加」。
- 其余链步骤（37 个 `--check`、镜像、站点）在首跑中均 `CHECK OK`。

## 6. 提交与文件归属

- 本轮修改：`scripts/wp_production/submit_hpc_batch.py`、`ec_recovery_contract.py`、
  `build_frontier_legs.py`、`tests/test_ec_submit_entry.py`、`tests/test_ec_recovery_contract.py`、
  `tests/test_build_torsion_probe_package.py`、`tests/test_sbatch_syntax_gate.py`、
  `docs/handoffs/long_run_20261029/{L02,L03,L09,L04_DMC_TRACE/DMC_MECHANISM_DECISION,INPUT_INDEX}`、
  `docs/handoffs/dispatch_20261029_12h/**`、核心方案 §22。
- **不代提交**：`计划.md`、`docs/handoffs/four_state_recovery_20261023/DOL_EC_STAGE_REPORT_20261027.md`、
  `docs/handoffs/wp5_formal_replay_guard_20261023/README.md`（归属不明，保持原样）。
- 提交哈希与 finalize/全量结果见文末「复跑追加」。

## 7. 剩余具体事项

1. 战役账本增加防篡改（哈希链或与 journal/sacct 交叉核验）——本轮登记为残余 R4/R8。
2. 授权后仍需：EC p4 planned 候选登记（无翻转证明）→ 受保护提交器；DMC 若选 `OPT-COORD-1`/新起点须另批预算。
3. `agent_recheck_dmc_independence/REPORT.md` 已落盘（80 行，独立复核 12 条 attempt 中 9 组独立坐标）。
4. **提交哈希**：`a065e7f`（20 文件，+1389/-74）。
5. **最终复跑**：`pytest tests/test_sbatch_syntax_gate.py -v` 6/6；`pytest tests -q --tb=no` 0 FAILED；`pwsh -File scripts/wp_production/finalize_wp2.ps1` 36/36 `CHECK OK`（含 mirror/site）。

## 8. 两种结题状态（用户区分）

### 8.1 阶段性结题（当前可达）

| 维度 | 状态 |
|---|---|
| 科学 | 45/48 accepted；3 态 limited（EC TolE 3.18×；DMC 两态用户裁决停止） |
| 工程 | EC 真实提交入口已接通、21 项负测 + RED；DMC 坐标独立性已更正；finalize 全绿 |
| 复现 | 全量离线 pytest 0 FAILED；36/36 finalize `--check`；镜像 8 周 byte-identical |
| 新计算 | **无授权、无提交、零 core-hour** |

**收尾动作**：更新 `STATUS.json`、固化提交、发布报告时明确「工程验证通过 ≠ 科学目标完成」。

### 8.2 严格结题（48/48，需用户授权）

| 缺口 | 当前需要 |
|---|---|
| **EC\|LiM_2plus** | 新实验仍为 HOLD；需明确授权后执行，再按冻结标准验收 |
| **DMC\|M_plus、DMC\|LiM_2plus** | 本轮停止裁决有效；历史部分起点重复，不能证明搜索穷尽。重启须新机制、版本化预注册和独立预算 |
| **WP5 全目标池** | 当前 A=11/12、B=10/12；缺失态解决后，重新构池、回放并验收 |
| **采样与后继工作** | 生产级采样收敛容差尚未冻结；WP6 等触发项须按核心计划逐项核定，不能由 48/48 自动替代 |

**建议**：先完成「45/48、限制明确、可复现」的阶段交付；严格 48/48 作为独立后续实验阶段，不再用重复重优化追数字，也不承诺新计算必然成功。
