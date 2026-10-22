# 四态恢复前置交接包

本包为 DeepSeek Harness / 后续执行者准备。用户当前授权是**准备前置文件**；本包不提交、取消、重试或监控超算作业，也不授予提交权限。800 core-hours 是上一轮方案的**建议新轮次上限**，不是已经发生的消耗。真正执行前要在生产提交记录中绑定用户的执行授权。

目标：在冻结标准下恢复 DMC/M_plus、DMC/LiM_2plus、DOL/LiM_2plus、EC/LiM_2plus，并通过真实覆盖复核争取 48/48 accepted。预算耗尽时目标仍未完成。

## 从这里开始

1. 阅读 [GOAL.md](GOAL.md)：连续执行顺序、四态分支、停止与验收条件。
2. 阅读 [recovery_contract.json](recovery_contract.json)：科学门槛、四态电荷/多重度、预算和角色边界。
3. 阅读 [baseline_snapshot.json](baseline_snapshot.json)：生成时的真实哈希与状态，不代表实时 Slurm。
4. 用 [candidate_slots.template.json](candidate_slots.template.json) 填写真实起点。八行是**空槽位**，不是八个已生成、独立或通过 QC 的候选。
5. 用 [attempt_ledger.template.json](attempt_ledger.template.json) 创建本轮资源账本。历史费用另保留，不能改名清零。

## 本地验证（从仓库根目录执行）

```powershell
.\.venv\Scripts\python.exe -B docs/handoffs/four_state_recovery_20261023/preflight.py
.\.venv\Scripts\python.exe -B -m unittest discover -s docs/handoffs/four_state_recovery_20261023/tests -v
```

预检只读 JSON/CSV、配置、文件哈希和 Git 状态，不执行 ORCA、xtB、SSH 或 Slurm，不写产物。退出码：0=交接契约和快照一致，1=输入非法/缺失，2=基线过期。**退出 0 不等于可提交**，输出始终包含 `submission_gate=HOLD_NOT_A_SCIENTIFIC_OR_LIVE_QUEUE_GATE`。

需刷新快照时运行 `preflight.py --snapshot`，检查其 stdout 与旧快照差异后显式保存；普通预检不会自动刷新基线掩盖变化。外部会话修改科学源文件时，先完成交接，不能用刷新哈希代替审查。

独立审核资源账本：

```powershell
.\.venv\Scripts\python.exe -B docs/handoffs/four_state_recovery_20261023/preflight.py --ledger docs/handoffs/four_state_recovery_20261023/attempt_ledger.template.json
```

自测使用临时合成数据，既不读私人 `work/` 夹具，也不改正式账本。本包位于可版本管理目录，但当前**没有 commit/push**；独立目录的测试不会自动成为正式流水线验收。后续集成时必须迁移/登记共用实现与生产入口测试，不能只在文档目录测试通过就宣称生产已覆盖。

## 能做与不能做

本包已提供：预算核算与结构校验、四态身份核对、原始字节哈希基线、失败/救援/重复作业反例、可执行本地自测。

本包没有提供：候选几何生成器、ORCA 输入、可提交 sbatch、真实独立性证明、Slurm 实时容量检查、科学 QC 或提交授权验证。以上必须由生产流程补齐；手动把模板状态改成 ready 不构成证据。

数值成本校验只是**新轮次尝试账本的参考实现**，没有接入 WP5 的生产成本 join。其测试不能代替 WP5 成本接线测试。

## 共享工作区

创建本包时，另一执行者正在改 WP5 acquisition 与回放产物。不要覆盖其代码、重跑全链冲掉在写文件或混合提交。先重读 `git status`，按文件所有权协调。

2026-10-23 前一轮只读检查曾显示超算队列为空；这不是当前实时状态。正式执行前必须在命令桥工作区完整读 AGENTS，运行 doctor，再核验 squeue/sacct 和真实日志。旧报告中的“在飞”文字不能代替队列证据。

## 正式源码锚点（均为仓库内路径）

- `config/production_method_freeze_v1.json`：唯一冻结方法与五阈值来源。
- `scripts/wp_production/orca_derivative_policy.py`：解析梯度 / AnFreq 门。
- `scripts/wp_production/build_torsion_registry.py`：旧自由度登记，需检查与提交预检是否同源。
- `scripts/wp_production/build_torsion_probe_package.py`：带键级拓扑、片段旋转及批次索引。
- `scripts/wp_production/submit_hpc_batch.py`：受保护提交器；不能绕过。
- `scripts/wp_production/import_ensemble_structures.py`：科学 QC 与尝试导入。
- `scripts/wp_production/build_coverage_reviews.py`：新版本成员可见性和覆盖复核。
- `scripts/wp_production/build_production_ensemble_aggregator.py`：最终接受状态与去重。
- `scripts/wp_production/finalize_wp2.ps1`：不带 `-Commit` 的收口入口。

不要把本包的源码锚点/计划文字当作已实现或已运行的证明。
