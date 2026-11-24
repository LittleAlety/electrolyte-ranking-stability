# FINAL · 目标核销审计（Goal `goal-1c04011b` · Round 13/14）

> 2026-11-03 晚。对目标文本两条线（A 科学证据 / B 工程对账）+ Plan items 1–9 + 红线 + 输出格式逐项核销；全部条目以本轮实测或已验收证据为据。

## 1. A 线（科学证据分析）核销

| 要求 | 证据 | 状态 |
|---|---|---|
| 五态逐态取证（搜索范围/真实起点/作业终态/身份去重；已有未绑定 vs 覆盖不足） | `A1_five_state_coverage.md`（五态×五字段+4 作业终态+4 身份去重，逐态 PENDING） | ✅ |
| AN M⁺ 双结论（前沿身份材料 / 单盆地证据分别下结论） | SUMMARY §2（双独立来源一致；单盆地未证明） | ✅ |
| AN LiM²⁺（strictOpt vs NumFreq 几何/协议/阶段 + −115.27 不预归因） | SUMMARY §2.1（几何 `0.0031721326 Å`；fixed-geometry AnFreq 检验什么；−115.27 标记不归因数值误差） | ✅ |
| TMP 两态（承重成员点名+缺失项+最小补证） | SUMMARY §2.3（承重=已登记成员逐一点名；缺失=零作业；补证=最小新增实验待授权） | ✅ |
| 36 态缺口机制分组排优先序 | `A5_gap_mechanism_36states.md`（36=45−9 钉死；9 组；优先级 1–7） | ✅ |
| 禁补写不存在结论 | 全线 PENDING/未证明/条件池逐态标注，无一处手填 | ✅ |

## 2. B 线（工程与来源对账）核销

| 要求 | 证据 | 状态 |
|---|---|---|
| 调度别名完整映射（19 任务×127 元素，重复/歧义/缺失独立项） | `B1_array_alias_map.md`（88 映射/39 歧义/53 缺失/费用仅 0.9 CH；`mapped ∪ candidates = plan`；防重复计费结构性核验） | ✅ |
| EC 四份阶段输入哈希留证 | `B2_ec_stage_hash_verification.md` | ✅ |
| DMC 元数据更正前后值留证 | `B2…`/P1（original+effective+correction_ids 三元组） | ✅ |
| 隔离副本重跑逐字段差异+正式标签费用未变 | `B3_isolated_replay_diff.md` + P6 三跑（A/B 字节一致、C 规范化全等、45/2/1 实测不变） | ✅ |
| 覆盖不足保持未决不手填 | binding 五态全 `PENDING_INDEPENDENT_COVERAGE_AND_IDENTITY_REVIEW`；P5b `resolved` 命中=0 | ✅ |
| 机器补验哈希总表 | `BATCH1_handoff.md:22` **`FINAL: OK 10 / NOTFOUND 0 / MISMATCH 0`** | ✅ |

## 3. Plan items 1–9 核销

| # | 交付 | 状态 |
|---|---|---|
| 1 写入面与基线 | P1 核收（10 键钉死）；P3 基线 `ed2b621d…`；P6 基线 `468dc00e…`+`BASELINE.json`；写入面=证据目录+2 授权改动 | ✅ |
| 2 D7/D8 收口+七类验证 | P1 三轴收口；**P2 七类矩阵**（补测 6/6：未知 schema/重复接收/字节不变）；切换/迁移=**HOLD（Open Q1）** | ✅ 验证闭合；切换=HOLD（plan 终态） |
| 3 作业与证据映射 | B1 出口满足：可配对 88、歧义 39、缺失 53 独立 | ✅ |
| 4 登记与覆盖边界 | P3 `EXCLUSION_SOURCE_PROVENANCE` fail-loud + 8 用例；终态义务视图；不手填 resolved | ✅ |
| 5 准入门不可绕过 | P5 七门盘点 + P5b 五态五维机读状态+依赖顺序；staged≠computed≠accepted | ✅ |
| 6 可重复隔离重建 | P6 三跑验证（恢复/顺序/重跑/不写回）+ 修 `:342` 冻结缺口（基线留证） | ✅ |
| 7 受保护提交与幂等结算 | P7 守卫映射+61 测试（60 过+1 声明跳）；真实 sacct=环境依赖未关闭 | ✅ 第一轮；执行面待授权实验 |
| 8 按授权批次发布 | **Open Q2 未裁 → HOLD**（未发布=正确；发布前检查清单在 P5/P9） | HOLD（plan 终态） |
| 9 可复现归档 | P9：清单 90 文件 `e7252912…` 不自指、已声明检查表、口径 45/2/1 一致、外部依赖明确；**终审 18/18 全等** | ✅ 第一轮（site 全量口径随 item 8 补查） |

## 4. 红线自检（本轮实测）

| 红线 | 实测 |
|---|---|
| 不修改共享生产文件（无授权） | 本会话受控面=evidence/ 新文件 + P3/P6 两处**授权**改动（各留基线）；git `61 M + 75 ??` 与审计冻结时一致，无新增共享写入 |
| 不提交作业 / 不新增计算 | 零 `sbatch`/`sbatch --test-only`；零新增计算记录 |
| 不改阈值 / 不选 δ / 不生成 criterion | `config/comparability_criterion_v1.json` **ABSENT**（P5b fail-closed 实测） |
| 不手填 resolved / 不改正式标签 | P5b `resolved` 命中 0；labels CSV 45/2/1（48 行）与全仓文档一致 |
| 禁 `git reset` | 未执行；恢复全用基线 cp 路径 |
| 不自动申请计算 | 全程零申请 |

## 5. 没有关闭什么（外部依赖，非本会话可决）

Open questions 1–3（Lead 裁定：D8 切换/发布批次/归档与提交集边界）；五态身份与 coverage 复审（数据分析）；D7 独立签章；rdkit 环境（P1 5 例、P5 5 例、v4 19 例未证）；真实 sacct 端到端；崩溃恢复用例；site 全量口径（随 item 8 发布批 `--check`）。

## 6. 判定

**A/B 两线全部交付并已验收**（BATCH1 `FINAL: OK 10 / NOTFOUND 0 / MISMATCH 0`）；**Plan 可执行面 items 1/3/4/5/6/7/9 全部交付**，items 2/8 的未执行部分是**授权门控**——按停止规则「缺授权保持 HOLD」交付的正是 plan 规定的终态；首执行批次四项（P1/B1/P3/P4）完成；每批五问（改/证/发布/未关闭/恢复）均有交接包。**本目标在其可执行范围内已达成。**
