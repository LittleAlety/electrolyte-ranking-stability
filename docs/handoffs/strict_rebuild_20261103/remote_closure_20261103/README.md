# 本轮收尾与未完成事项

## 已完成

**远端访问与有界核验已完成。** 合法权限会话的 doctor 通过；没有修改或复制密钥，没有绕过命令桥。固定范围为已列项目根目录、深度9的原始日志／辅助输出及根目录归档；不是全文件系统穷尽声明。316份37态相关日志中，310份与冻结本地材料同哈希，只回收并解析6份新日志。另检查关联归档族540份 `.out`（无优化收敛表）、46个 tar 归档和一个 zip 的成员清单，并取得127条关联调度记录。指定范围没有未回收的新日志；调度数组别名尚未逐条对账，列为未做。

6份新日志中，只有 AN LiM²⁺ 的 `3700781_2_3706757/job.log` 实测优化五项通过。它使用冻结 TightSCF，但旧 NumFreq 有 **−115.27 cm⁻¹** 虚频，不能当合格成员。已回收原输入、末几何和 Hessian。其几何与已存在 AnFreq 绑定几何的全原子刚性对齐 RMSD 约 **0.002516 Å**，未找到可直接绑定到该几何的现有 AnFreq。其他5份新日志未提供严格优化替代。见 `remote_evidence_closure.json`、`AN_geometry_comparison.json` 与 `raw/`。

**EC 输入来源门进一步闭合。** 两条3953361候选的4份实际远端阶段输入已回收，SHA256全部与原包及 workflow 结果一致，原先“尚未独立远端读取”事项关闭。源文件在 `ec_inputs/`，回执在 `fetch_receipts.txt`。这不替代其余身份、协议、登记、去重和coverage门。

**DMC 元数据已追加更正。** 新增 `outputs/physics_completion/recovery/candidate_source_metadata_corrections.jsonl`，保留 `old protocol (TightSCF)`、原文件哈希、同作业输入／日志证据与更正ID，有效值为 VeryTightSCF SlowConv。旧结算文件未改写；隔离重建读取器现可应用哈希绑定的更正。`DMC_protocol_metadata_effective.json` 明确保留 **C3(i)关闭**，没有正式晋升或费用变化。

## 8态逐项处置

原正式处置表已经记录相关成员终态；本次未发现“仍在计算”的实际pending成员。旧隔离输入仅保留合格成员，丢失了不合格成员的终态义务视图，导致通用pending。现在隔离视图保留全部26个当前成员及原处置，严格不合格成员仍不参与权重或去重。4条历史失败原样保留。

| 态 | 具体成员／处置 | 隔离重跑路由与剩余条件 |
|---|---|---|
| AN M⁺ | tors_3_0_1_2 已computed；指定本地、远端frontier目录及已列frontier归档均未找到该成员身份链 | single_basin_scope_review；身份来源和单盆地搜索范围仍未闭合 |
| DEC LiM²⁺ | c02 已computed；c03_c03 已rescue_budget_exhausted，无活跃pending | coverage_registration_required；将合格c02与可信起点、实际搜索范围绑定，保留旧失败 |
| DEC M⁺ | 15、22、23均已computed；严格池仅15 | coverage_registration_required；缺合格池对应的单盆地覆盖登记／范围证明 |
| GBL LiM⁺ | c03 已computed且严格数值合格 | coverage_registration_required；缺覆盖范围与承重链绑定 |
| PC M⁺ | 46 已computed且严格数值合格 | coverage_registration_required；缺覆盖范围与承重链绑定 |
| TMP M | 27、48均已computed；严格池仅27 | coverage_registration_required；缺合格池对应的覆盖登记／范围证明 |
| TMP LiM²⁺ | c08历史失败；r2_c48_c00、r3m_c00已computed但严格证据不足；c13合格 | strict_member_evidence_required；同时保留旧失败与严格缺项，不能借旧review承重 |
| TMP M⁺ | c10、33历史失败；r3_c42已computed但严格证据不足；27合格 | strict_member_evidence_required；同时保留失败与缺项，无仍在计算的pending |

以上8态 verdict 均为 **unresolved**，没有新增accepted。7态已有身份来源的既有绑定结果保留；AN身份来源缺口仍是限定来源的未找到，不是身份失败。

真实入口结果：`eight_admission_v2/full_obligation_generator_8.json`；逐成员原值、处置、严格缺项与哈希：`eight_admission_v2/member_terminal_dispositions.json`。新增真实pending优先级回归、完整八态入口回归、旧失败保留回归和元数据更正回归；相关测试 **11 passed**。只读独立复审未发现暗中通过coverage或抹除历史失败。

## 首份补证建议（未授权、未提交）

**仅建议一条 AN LiM²⁺ 固定几何 AnFreq。** 使用新回收的严格Opt末几何、冻结 TightSCF 物理协议、电荷2／双重态，不附带新Opt。目的是检验目标解析Hessian及热校正；旧NumFreq虚频不被忽略。若仍有冻结判据认定的虚频、SCF失败、物种漂移或协议不符，保留未决，不能自动追加扰动、救援Opt或更严SCF。即使通过，也仍需身份、登记、共同去重与coverage。

该候选路径缺目标频率证据，不等于整态所有恢复路径都绝对需要此实验。详细规格和停止条件见 `FIRST_EVIDENCE_PROPOSAL.json`。

预算参考：同体系旧 Opt＋NumFreq 的调度记录3706757为983秒、4核，即 **1.092 core-hour**。新AnFreq粗略计划量级 **0.5–4 core-hour**，是未校准估算，不是保证或置信区间。若沿用现有4核24小时频率专用资源档，**预留上限为96 core-hour**，不能将96当预计消耗，也不能将4当已批准硬预算。没有复用旧实验授权；实验和预留额均需另行批准。未按37态乘统一成本，也未换算货币或估计排队日期。

## 交给用户的未做事项

1. **批准或拒绝上述AnFreq及预留额。** 当前没有作业输入包、提交、预约或费用发生。
2. **五态覆盖范围绑定尚未完成。** 应继续对照 `outputs/physics_completion/sampling/sampling_conformer_set.csv`、`sampling_index.json`、`sampling_audit_index.json`、原候选登记和原起点几何，将具体范围与合格代表绑定；没有理由先申请新计算。旧sampling审核索引引用的结构账本哈希已过期，不能直接沿用其状态结论。
3. **AN M⁺身份与单盆地范围仍未关闭。** 指定来源检查已结束；若现有批准规则要求独立同几何身份来源，应另提最小身份补证申请，不能用primary替代tors_3身份，不能声称身份失败。
4. **TMP两态的严格成员补证方案尚未设计。** 需分别处理具体失败与缺项，不把历史失败撤回，不将所有腿套成Opt＋AnFreq。
5. **其余36态的逐实验设计和预算未做。** 本轮仅交一条有具体源文件依据的频率实验建议，没有全项目预算或结题日期。
6. **JobIDRaw与数组别名逐条对账未完成。** 已保存127条调度记录；没有据此修改历史费用账本。

`formal_integrity.json` 的14个正式产物／账本来源与原冻结基线一致；唯一新增正式目录文件是用户授权的元数据追加更正。历史 **45 accepted / 2 limited / 1 provisional** 不变。没有新增物理计算、正式晋升或研究结论验收。
