# 9 个单点诊断执行报告（2026-11-01）

用户明确要求“请您进行并汇报”后，已按 RESUBMISSION_PLAN.md 的 9 个冷启动单点方案完成构建、校验、上传和真实提交。WHU HPC doctor 通过；提交前队列为空。

| Slurm 数组作业 | 目标 | 元素 | 资源 | 串行条件 |
|---|---|---|---|---|
| 3942220 | EC/LiM²⁺ | 0 TightSCF；1 VeryTightSCF-A；2 VeryTightSCF-B | 每元素 4 核 × 5 分钟 | 数组 %1 |
| 3942222 | DMC/LiM²⁺ | 同上 | 同上 | afterany:3942220，数组 %1 |
| 3942223 | DMC/M⁺ | 同上 | 同上 | afterany:3942222，数组 %1 |

共 9 个元素，最坏预留 3 CH；三个提交日志的 reserved_core_hours 合计已断言为 3。使用现有 h2_single_point_v1 资源配置，每包 3 元素预留 1 CH；未修改生产提交器或新增资源配置。三个数组均 --no-requeue，每次执行独立目录，无 GBW/MO 继承；不自动重提失败元素。

输入的泛函、基组、溶剂、几何、核数、SCF MaxIter 一致，受控变量为 TightSCF / VeryTightSCF。A/B 输入逐字节一致，只使用不同的新运行目录。所有输入增加相同的 FMOPop 输出选项，保存自旋通道前沿轨道的 Mulliken/Loewdin 布居；每次正常完成后在同一 Slurm 时间额度内运行 orca_2mkl 导出 Molden，保留 GBW、日志与结果哈希。若计算完成而轨道导出未完成，也必须报告该缺件，不能记为完整电子身份验证。

每组几何的原子数、元素核电荷之和、目标电荷和电子数已预检，三项起点哈希与计划完全一致。上传前及远端均已验证 PACKAGE_SHA256SUMS；每个元素在计算节点运行前再次核验输入。运行目录创建不使用覆盖模式。

本报告写入时：3942220_0 已在计算节点 n0362 运行，其他 EC 元素受数组并发限制等待，DMC 两数组受依赖等待。尚无完整三组结果，因此**不报告**协议可比性通过、电子解一致或正式标签提升。技术完成后需从原始日志、波函数/布居和真实 sacct 用量回收核验。

上一轮 3928499 / 3928500 / 3928501 三个本实验账本已按 sacct 元素行结算，保留原始账本备份、预留历史及真实 JobID/JobIDRaw。实际合计 10.661111111111111 CH；优化腿误标 diagnostic_only=true 已依据原 manifest 修正为 false。未写入旧 ec_recovery_v2 合同账本，未改变任何正式验收标签。费用结算快照见 PREVIOUS_CAMPAIGN_SETTLEMENT.json。

耐久提交快照：DIAGNOSTIC_SUBMISSION_EVIDENCE.json（授权、输入、几何、作业脚本、manifest、journal 及各自 SHA256）。可执行构建/提交脚本在 work/ec_dmc_diag_20261101.py，执行包在 work/hpc_scfdiag_*_20261101；现有 journal 会阻止再次运行提交命令。

本批仅补电子层诊断，独立构象搜索覆盖、协议可比性阈值、受审接收器及正式候选登记仍需按原方案完成，不能据单点能差小就直接写 accepted。
