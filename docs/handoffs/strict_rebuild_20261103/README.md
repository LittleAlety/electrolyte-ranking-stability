# 48 态严格证据隔离重建

最新三个具体阻塞的结果：[`blocker_resolution_20261103/README.md`](blocker_resolution_20261103/README.md)。包括 AN 生成器修复与8态实际路由、三项候选来源核实，以及37态固定范围的本地检索结果和远端无法访问边界。本轮没有新增48态汇总验收表。

修复解析器边界后的重建快照：[`run_06c49d9e7ebe0688/README.md`](run_06c49d9e7ebe0688/README.md)。它包含 48 态逐态结果；同目录的 `states.json` 是机器可读的代表、权重、coverage 与条件分类，`gap_actions.json` 列出逐态成员停点，`source_index.json` 固定输入及原始证据 SHA256。

本轮独立核验与恢复清单：[`verification_20261103/README.md`](verification_20261103/README.md)。其中 `primary_verification.json` 逐条核验 48 条 primary，`member_statuses.csv` 拆分 132 个成员的原因，`candidate_evaluation.json` 单列 5 条 DMC 与 6 条 EC 候选，`coverage_recheck.json` 标明 3 态旧 claim 的停点及 5 态条件池的剩余核验。

逐态恢复路径交付：[`recovery_decisions_20261103_v9/README.md`](recovery_decisions_20261103_v9/README.md)。`decisions.csv` / `decisions.json` 给出全部 48 态的最佳现有证据链、已闭合门、停点、下一动作与来源；`candidates.json` 逐条拆解 11 条候选；`coverage_8.json` 记录生产 coverage 路由函数在 8 态隔离输入上的实际输出。完整历史生成器的隔离试跑及单代表误判见 `coverage_generator_sandbox_20261103_v4`。较早的决策表与沙箱目录为开发快照，保留但不作为交付。

此前 `run_3e63ee06ba6de4f0`、`run_bcf56b585615d2b6`、`run_764b5dcb0f60320b`、`run_e5457aa74a6fea32`、`run_e09e1bcf681da10a`、`run_4ed1af288fcebdb4`、`run_6aff6e9daf188c1b` 是本轮开发中的只读快照，均未覆盖；以修复后的重建快照为准。

本轮无新增计算、正式准入、正式表更新、账本或费用修改。技术审阅没有被记作用户签认。
