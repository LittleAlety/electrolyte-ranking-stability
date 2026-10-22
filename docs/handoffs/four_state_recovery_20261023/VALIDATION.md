# 前置包验证记录（2026-10-23）

## 范围

仅验证本目录的前置契约、模板和只读助手。没有运行 ORCA/xtb、上传/提交/取消作业、重建科学产物或执行全仓库收口链。

起始 HEAD：`eb8210c49686f3919111964c026b6b2be5058c66`。工作区中另一执行者正在处理 acquisition v2，未覆盖其改动。

## 测试与独立复核

1. 初版：29 unittest 通过；默认预检 CONSISTENT/HOLD。复制到不含仓库与私人 work 的临时目录，29项同样通过。实测包内文件字节和mtime零变化。
2. 独立 reviewer 发现3项Important：Slurm父数组/元素与ID别名混计；JSON bool/int及版本边界；极端finite Decimal异常退出。另发现Git可选索引刷新Minor。
3. 单一 optimizer 先加入反例：40测试运行得到45个失败子项和2个错误，确认原实现存在问题；随后仅修预检与测试文件。
4. 最终本包测试：41/41通过。独立 reviewer 重读并复验，原问题全部修复，无新的Critical/Important，结论 **Ready for preparation handoff only**。
5. 协调者末轮验证：本地41/41、隔离目录41/41；显式更新快照后的默认预检为CONSISTENT/HOLD；9个包内文件字节和mtime均无变化；`git diff --check`通过。代码哈希与独立审核记录一致。

验证命令（从仓库根运行）：

```powershell
.\.venv\Scripts\python.exe -B -X utf8 -m unittest discover -s docs/handoffs/four_state_recovery_20261023/tests -v
.\.venv\Scripts\python.exe -B -X utf8 docs/handoffs/four_state_recovery_20261023/preflight.py
```

审核代码 SHA256：

- `preflight.py`：`1d61154be835a230fc689965bdff67e70890df1f3c62602666805111c82f67a0`
- `tests/test_preflight.py`：`15ed10422fff46698445cb6e831818a01e3cb83feb048bae46d8be5ef443e21a`

## 并发提交与快照更新

复核期间另一工作流提交了 `db34809c18fa03320e5c1c3401e3d22d2760e4e9`（acquisition v2），并将本包主体一并纳入提交；本协调者没有执行commit/push。测试末尾补充与本验证记录不因此自动获得提交状态。

预检首先真实返回 `STALE / changed_sources=[HEAD] / HOLD`。随后明确比对12项受监测科学输入/源码哈希，全部未变，才显式刷新 baseline_snapshot.json 并记录前后HEAD。此刷新不表示本轮审核了另一执行者的WP5数值结果。

以后HEAD或源文件再变，预检仍会拒绝旧快照；不得静默自动刷新压绿。

## 保留的限制

- 八条候选记录是未填槽位，不是八个合格结构。
- 800 core-hours是本轮建议预算，不是Slurm可用余额，也不是提交授权。
- ledger helper没有认证sacct证据或起点独立性，也未接入WP5生产成本join。
- 默认预检不查询实时队列，始终显示HOLD。
- 还需真实几何生成、预注册、正式消费者接线、科学预检和受保护提交器，才能启动任务。
- 本包只做独立自测；没有宣称全仓库pytest/收口链本轮通过。
