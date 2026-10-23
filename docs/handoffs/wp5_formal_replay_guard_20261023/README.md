# WP5 正式回放外层审计

状态：**IMPLEMENTED / AWAITING INDEPENDENT REVIEW**。本目录由 Codex 单一 writer 实现；生产文件由其他工作面负责，请勿混合提交。

本工具只读审计现有证据，不训练模型、不提交作业、不改正式输出，不是授权或科学完成闸门。

## 1. 用法与退出码

在仓库根目录运行；仅向 stdout 输出一个 JSON 对象。始终使用 `-B`，工具也设置
`sys.dont_write_bytecode=True`，不产生生产目录的 `__pycache__`。

```powershell
.venv\Scripts\python.exe -B docs/handoffs/wp5_formal_replay_guard_20261023/audit.py --repo-root . --acq-version knn_v1
.venv\Scripts\python.exe -B docs/handoffs/wp5_formal_replay_guard_20261023/audit.py --repo-root . --acq-version model_v2
```

| 退出码 | integrity | full_pool | 含义 |
| --- | --- | --- | --- |
| 0 | PASS | PASS | 当前正式主集 12 分子全部准入，两任务 32 轴证据结构与现有停止算法一致；**不是所有策略都达到停止预算，更不是项目科学完成** |
| 2 | PASS | BLOCKED | 子池证据完整、一致，但全 12 分子未齐；小池不能容纳两个非耗尽预算点时端点应是 `blocked_target_pool` |
| 1 | FAIL | BLOCKED | 缺失、过期、坏输入、结构/身份/算法对账失败；查看 `issues[].code` |

所有结果固定保留 `authority=AUDIT_ONLY`、`evidence_scope=ARTIFACT_CONSISTENCY`、
`submission_gate=HOLD`、`formal_model_v2_ready=false`。合法 `not_reached_within_pool`
不是损坏数据，不会被改写为 computed。`full_pool` 只认证主集准入覆盖，不认证成本完备或科学完成。

版本目录严格隔离：

- `knn_v1`：`outputs/physics_completion/active_learning/blind_replay/`。
- `model_v2`：同级 `blind_replay_model_v2/`。
- target pool 始终来自正式 `blind_replay/target_pool_AB.csv`。
- 请求 model_v2 而其索引或输出不存在时报告 `MISSING`，不回退 control。

## 2. 实际核验内容

1. 从 `data/metadata/physics_completion_set.csv` 的 `in_main=true` 取**独立的 12 名字集合**。
   元数据允许同分子跨 main/method/sampling cohort 重复登记；不能从回放的现有行数反推或缩小分母。
2. 系综 labels 必须恰好匹配该集合的 48 个主态；target 必须有 24 个唯一 task/name 键。
   target 的腿状态、限制原因须与 labels 一致；A 双 free 腿、B 四腿全 accepted 才准入。
   验证 G→eV 的已打印目标投影及 B 的 `S_Li = S_f + D_coord`，九位小数允许有限舍入误差。
3. 读取 target index 与版本专属 AB index，核验固定 labels、target、cost、features 输入依赖及
   SHA256。兼容路径中的 `\` 与 `/`，但拒绝越界、绝对路径、重复规范化别名和未知依赖。
4. 32 轴固定为 A/B × `knn_baseline/ridge_std/krr_rbf/gpr_rbf` ×
   `random/diversity/uncertainty/ranking_aware`；index 与全部表行的模型/版本/查询器身份一致。
   model_v2 的 legacy 查询仍是 kNN，random/diversity 仍不使用模型输出，不假装所有轴都模型驱动。
5. 每轴恰好 20 repeats，每 repeat 完整预算 `4..n_pool`，含耗尽点；键唯一，不接受整数截断。
   O_3 必须在 [0,1]、R_3 非负且有限。端点预算与状态逐轴调用现有
   `scripts/wp_production/wp5_replay_contract.py::empirical_stop_budget` 复算，**不复制或改写联合 16/20 算法**。
6. 每轮候选集合准确且唯一，queried 数为 n_T、不能撤回、每轮新增一个；同 task/repeat
   的四模型四策略共享初始四标签。control 全查询序列及两版本 label-free 序列跨模型保持一致。
   true_ev 对 target 的六位打印误差进行核对；**不从舍入后的 pred_ev 强行重算排序**，也不要求已查询预测恒等真值。
7. 打印成本采用 Decimal 检查非负/有限及“总成本=两项打印值之和”。A 前置为 0/not_applicable；
   B 的全主集 free 前置成本与 24 腿数跨模型、策略、repeat、预算恒定。
   `MISSING` 要保留空白并传播到总成本，不伪装零成本。

完整性通过但存在合法 MISSING 时，报告 `cost_evidence_complete=false` 和 `missing_cost_rows`。
该字段无缺失时为 true，也仅限 `cost_evidence_scope=PRINTED_COMPONENTS_ONLY_NOT_ALLOCATION_JOIN`，
不表示已审核 Slurm allocation、失败重试或共享作业的真实计费 join。

## 3. 同源快照与只读边界

每个被读文件冻结原始字节并登记 SHA256；结束时重新读盘核对，变化则
`SNAPSHOT_CHANGED`，不会自动重建或修复任何文件。报告最多两个受限长度的问题摘要和有限源哈希集合。
文件哈希只证明“这次审计读到了哪些字节”，不是数字签名、可信执行证明或完整来源认证。

不导入 replay runner、NumPy、训练模型、ORCA、xtB 或 HPC 桥。只执行仓库中已知纯标准库的停止规则 helper；
检查它的 imports 且将其源码哈希列入快照。这不是执行不受信任 Python 的沙箱，helper 仍属于受信任仓库代码。
CSV 单文件上限 64 MiB、200000 行；当前全 12 池规模在限内。初始池少于四个不能执行冻结的四初始标签契约，报告坏输入。

本工具**没有**证明无标签泄漏、重新训练或验证模型预测、核算 sacct、取得执行授权、
做几何/电子身份科学 QC，也**没有自动接入正式收口链**。

## 4. 自测与初次 RED

```powershell
.venv\Scripts\python.exe -B -m unittest discover -s docs/handoffs/wp5_formal_replay_guard_20261023/tests -p '*.py' -v
```

测试全部在临时目录构造合成元数据、labels、targets、index 和回放表；仅复用仓库中的纯算法源码，
不依赖私人 work 数据、不训练模型。覆盖合法 full/subset/small-pool、model_v2 隔离、缺轴/重复/缺预算点、
整数与指标边界、输入哈希、路径别名、端点预算篡改、联合 16 规则、候选重复/撤回/初始配对、
B 四腿准入、成本/MISSING、快照变化及各退出路径文件字节与 mtime 不变。

初次 RED：先写自测、未实现 audit.py；上述 unittest 命令退出 1，
`FileNotFoundError: audit.py`、`FAILED (errors=1)`。该证据保存在执行工具输出中；随后实现并迭代自测。

## 5. 接线建议（仅建议，不在本目录执行）

1. 由正式链在目标池与选定版本回放生成之后调用本审计，显式捕获退出码及结构化报告。
2. 数据完整性 FAIL 必须使接线检查失败；合法子池退出 2 单列 full12 blocked，不能被包装成科学失败或全部完成。
3. cost MISSING 与 `not_reached` 分别作为独立证据状态消费，禁止平均值代替停止预算。
4. 任何正式合规升级还需真实模型/泄漏、成本 allocation join、身份与核心计划的独立审查；
   不能仅因本审计 PASS 解除限制，也不能静默从 model_v2 回退 knn_v1。
