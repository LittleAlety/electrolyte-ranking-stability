# 三项候选来源核实

机器证据与完整 SHA256：`candidate_sources.json`；可复现本地核对入口：`scripts/wp_production/verify_recovery_candidate_sources.py`。核对直接读取原归档成员字节，与 workflow 的阶段输入哈希、已返还日志哈希及日志输入回显比较，没有生成替代输入。

1. **AN M⁺ tors_3_0_1_2：独立前沿身份链仍缺。** `work/hpc_frontier_localization_v1/tasks/` 中该态只有 `AN__M_plus__primary`，未找到该候选任务目录。候选自己的优化／频率日志存在于 `work/hpc_torsion_probe_v2_realfragment/tasks/AN/M_plus__tors_3_0_1_2/snapshots/3749450_0/job.log`，但它不构成另一个已绑定的独立前沿身份来源。本地指定来源检查不能关闭身份门，远端来源尚未核实；本轮不将这一待核项转成必须新算。

2. **EC 两条：原提交包找回并与结果输入哈希接通；远端阶段文件独立复核仍未完成。** 实际来源是 `3953361 / hpc_ec_safe_coord_20261102`，不是后续 `3954954 / hpc_ec_endpoint_pair_20261103`。`work/ec_coord_safe_20261102/hpc_ec_safe_coord_20261102.tar.gz` 的两条 task 均含原始 `job_opt.inp`、`job_freq.inp` 与 `inputs.sha256`；`UPLOAD_CHECK.txt` 对两阶段输入均为 OK；`submission_journal.json` 绑定作业 3953361。原包 Opt 输入 SHA256 为 `fd5f03c341f58c348a202a65ea1b2ea6f4a8490f0960a9134efe8dbf1252ed92`，Freq 为 `e2f4dfc6f6033dd216acb504446adb66aa551395214448217ee03e69f4b13588`，分别与两条 `workflow_result.json` 一致；返还日志哈希及第一行输入回显也吻合。可关闭“找不到原输入来源”这一项，但实际远端阶段文件尚未独立读取，不能声称该复核完成。

3. **DMC 3928500_0：实际协议为 VeryTightSCF SlowConv。** `work/ec_dmc_campaign_20261031/SUBMISSIONS.json` 将提交包绑定作业 3928500。原归档的 Opt 输入 SHA256 为 `914992255efb679ce770ea14a5645a3222df062ac868fb9de4845ec03e452bf3`，Freq 为上述 `e2f4dfc6…`；均与已返还阶段输入、workflow 输入哈希一致。Opt 日志第 229 行、Freq 日志第 225 行均回显 `VeryTightSCF SlowConv`。因此账本的旧 TightSCF 标签是待更正元数据，不能让该候选走冻结 TightSCF 协议的直接共同池路径。C3(i) 的几何／频率等效规则尚未批准，晋升仍关闭；本轮未迁移正式账本。

三项的远端核验均受同一访问边界限制：已读 whu-hpc 技能及命令桥 AGENTS，`doctor` 因专用密钥的沙箱读取权限未通过；提权重试等待审批后被中断。没有远端文件读取，也没有提交新计算。该状态记为无法访问，不推断远端证据存在或不存在。
