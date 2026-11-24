# A5 · 其余 36 态：缺口机制分组、优先序与实验建议边界（科学证据分析）

- 派单 A5：「其余 36 态按缺口机制分组、排优先序；仅对证据已充分核清的对象给实验建议，**不按态数机械生成作业**」。
- 本轮只读；零作业生成、零共享生产写入、零预算变更。可复跑提取器：`python docs/handoffs/lead_reception_strict_rebuild_20261103/evidence/a5_gap_extract.py` → **exit 0，ALL ASSERTIONS PASSED**（输出 `a5_gap_extract_output.txt`）。

## 0. 口径

**36 态 = 系综 45 accepted − 9 具名态**（9 具名 = 5 条件池 DEC|LiM_2plus/DEC|M_plus/GBL|LiM_plus/PC|M_plus/TMP|M + AN|M_plus + AN|LiM_2plus + TMP|M_plus + TMP|LiM_2plus）。
另 3 态非 accepted **不入本组**：DMC|M_plus、DMC|LiM_2plus（limited）、EC|LiM_2plus（provisional）——其 recovery_class = `需要明确规则裁定` ×3（actions=「逐候选核原始输入与末态身份…规则未批前只保留独立结果」）。

| 源 | sha256 | 角色 |
|---|---|---|
| `run_06c49d9e7ebe0688/gap_actions.json` | `e7ce5ba931dc42157ce2dd12cd7fbd27d6776ade59d274fa1f537620172a9113` | 48 态阻塞原因码 |
| `recovery_decisions_20261103_v9/decisions.csv` | `ac430d378c05444c9f2afc08b0ac477b6221ff4d64a78dedd7d3f8136cc1ae5d` | 逐态 recovery_class/零计算动作/预算 |
| `verification_20261103/coverage_recheck.json` | `182d32aba5e99e7ff13f7f922f42d4e3fe473f26e8a276710419ddcc1cbc8a6d` | 8 态 recheck 判定 |
| `verification_20261103/README.md` | `61e930b842abc97c082e11e9fa0662f356e25be3411aabce0774e4b3206ddf3e` | 46/2/48/补算边界（行 7/8/10/21） |
| `production_ensemble_labels.csv` | `c21003f5e18a2faaf4e3c8e91c379ea3ab16659706d13786ed25df0038ae0c80` | 48 态接受/覆盖/登记 |
| `recovery/coverage_reviews.csv` | `e89188f6eac28bbf2dd309a95ec19ea9b1cc78969a262883820f939eec28ba40` | 14 审查 |

提取器：`a5_gap_extract.py` sha `45f271de426e342daedb0458c680cb04010625e70d756970d36ec3bd24912c6b`；输出 `a5_gap_extract_output.txt` sha `4a23f6c10ae8d692fc2ed9c62ad78fe01a6918d008feaf526efecba429995d06`。

## 1. 机制分组（互斥分区，4+2+2+4+24 = 36）

分组优先级判据（一个态只入最高优先级组）：物种身份未验证 > 五项表整行缺失且无超限 > 零登记起点 > 覆盖已审 > 其余三门全开。

| 组 | 缺口机制 | 态数 | 成员态 | 未关门（逐门） | 承重证据 |
|---|---|---|---|---|---|
| **G1 物种身份未验证** | `SPECIES_IDENTITY_UNVERIFIED`（成员级物种核验未过） | 4 | DEC\|M, DME\|LiM_2plus, DME\|M_plus, SL\|LiM_2plus | 物种身份 + 身份源复核 + 数值QC；覆盖已审 | gap_actions 原因码（SL\|LiM_2plus 2 条、余各 1 条）；4 态 labels 均 `resolved_by_review` |
| **G2 五项表结构缺行** | 最佳成员五项表**缺 Energy change 行**且全表无超限记录（无法判定，禁补零） | 2 | DME\M（缺 3 成员含 primary）, DOL\M（缺 2 含 primary） | 数值QC（无法判定）+ 身份源复核 + 覆盖未审 | README 行 7/10：「另 2 条 DME\|M、DOL\|M 缺 Energy change…保持证据缺失，不能补零」 |
| **G3 零登记起点** | `n_registered=0`、`pool_limited=true`，登记入口缺失 | 2 | DME\|LiM_plus, EMC\|LiM_2plus | 登记 + 数值QC + 身份源复核 + 覆盖未审 | labels reg=0（全表仅此 2 accepted 态） |
| **G4 覆盖已审、无物种问题** | 覆盖门已关（resolved），但最佳成员五项超限、身份源未复核 | 4 | DMSO\|LiM_plus, DOL\|LiM_2plus, EMC\|M_plus, TMP\|LiM_plus | 数值QC + 身份源复核（**2 门**）；另有成员级 `NOT_CURRENT_NUMERIC_MEMBER`/`NOT_IN_FORMAL_CANDIDATE_REGISTER` 标记（4 态共 4 条） | coverage_reviews 4 行 resolved；gap_actions 原因码 |
| **G5 三门全开** | 五项超限 + 打印容差不一致 + 覆盖未审 + 身份源未复核 | 24 | AN\|LiM_plus, AN\|M, DEC\|LiM_plus, DMC\|LiM_plus, DMC\|M, DMSO\|LiM_2plus, DMSO\|M, DMSO\|M_plus, DOL\|LiM_plus, DOL\|M_plus, EC\|LiM_plus, EC\|M, EC\|M_plus, EMC\|LiM_plus, EMC\|M, GBL\|LiM_2plus, GBL\|M, GBL\|M_plus, PC\|LiM_2plus, PC\|LiM_plus, PC\|M, SL\|LiM_plus, SL\|M, SL\|M_plus | 数值QC + 协议容差 + 覆盖 + 身份源（≥4 门） | 同上；labels `not_reviewed` |

## 2. 36 态机制频次（实测，提取器断言钉住）

| 机制（原因码） | 出现态数 | 与 verification README 交叉 |
|---|---|---|
| `PRIMARY_IDENTITY_SEPARATE_SOURCE_NOT_REVERIFIED` 身份源未复核 | **36/36**（全局 48/48） | 行 8：「48 条电子身份来源仍待独立复核，**不记为身份失败**」 |
| `FIVE_ITEM_EXCEEDS_STRICT_LIMIT` 五项超限 | **34/36** | 行 7：「46 条 primary 实测至少一项超过严格阈值」（另 2 = G2 缺行态） |
| `PRINTED_OPT_TOLERANCE_DIFFERS` 打印容差不一致 | **34/36**（全局 46/48） | 行 8：「46 条打印容差不同，**是独立的协议状态**」 |
| `SPECIES_IDENTITY_UNVERIFIED` 物种未验证 | 4（G1） | — |
| 覆盖 `not_reviewed` / `resolved_by_review` | 28 / 8 | labels 实测 |
| `n_registered=0` | 2（G3） | labels |
| recovery_class = `检索尚未完成` | **36/36** | decisions.csv |
| `new_computation_budget` | **NONE_JUSTIFIED_YET ×48** | decisions.csv（无一态有获批预算） |

动作分布（decisions.csv，36 态内）：**34 态 =「先找同一成员后续优化循环/严格接续日志补 Energy change；若确为首点且无后续记录，保留该项缺证」**（零计算检索）；**2 态 =「先找同盆地严格优化归档或合格替代成员；归档确实无证后才提出该盆地有界严格优化实验」**（G3 两态，条件性实验路径）。

## 3. 优先序（推荐，零计算先行；不是授权）

| 级 | 组（态数） | 理由 | 首个零计算动作 |
|---|---|---|---|
| **P1** | G1（4） | 身份凌驾一切分支（项目规则「身份漂移凌驾一切分支」）；物种未验证是最硬的门，须先于任何其他取证裁定 | 从既有日志/输入核 4 态物种身份（只读），身份过门后才谈其余门 |
| **P2** | G4（4） | 覆盖门已关，**只剩 2 门**，单位工作量的关门产出最高；且 4 态均带成员级册籍标记需一并核 | 检索严格合格成员归档 + 身份源复核（只读） |
| **P3** | G2（2） | 结构性缺行——数值门**无法判定**，与 46 态超限是不同性质（判定缺输入 vs 输入超限）；处置与首点例外统一裁定（F1–F5，**待裁**）联动 | 检索同成员后续循环/严格接续日志（补行来自原日志，非补零）；确为首点则维持缺证 |
| **P4** | G3（2） | 零登记＝检索入口本身缺失；同时是 36 态内唯二带条件性实验路径的态 | 穷尽同盆地严格归档检索，确认「归档确实无证」后才可拟最小实验 |
| **P5** | G5（24） | 三门全开、体量最大，按 P1–P4 同一套零计算流程批量推进 | 逐态检索严格合格成员（34 态同样走补 Energy change 检索动作） |

> 说明：排序是**证据优先 + 关门产出**的推荐，不是裁定；如按「距闭合门数最少」排，P2 可与 P1 并列，但身份门不因效率让位（此为项目既有规则）。

## 4. 实验建议边界（派单要求：仅对证据已充分核清者给建议）

| 对象 | 证据是否已核清 | 实验建议 |
|---|---|---|
| **36 态全部** | **否** — recovery_class 全为 `检索尚未完成`；README 行 21 补算边界原文：「**当前不能证明任何一态已穷尽现有文件与候选路径，因此未确认最小新增实验清单或预算**」 | **不给**（不按态数机械生成作业） |
| G3 两态（DME\|LiM_plus, EMC\|LiM_2plus） | 条件性——动作明写「归档**确实无证后**才提出」；前置检索未穷尽 | **不构成现阶段建议**（提案前置条件未满足） |
| AN\|LiM_2plus（具名，不在 36 内） | 已核清到可提案层（A3 交付：五项 PASS、几何谱系、`−115.27 cm⁻¹` 振型分解、固定几何 AnFreq 提案） | **唯一提案对象**：`FIRST_EVIDENCE_PROPOSAL.json`（`PROPOSED_NOT_AUTHORIZED_NOT_SUBMITTED`，待批；估算 0.5–4 CH ≠ 预留 96 CH，授权独立） |
| 8 recheck 态（5 条件池 + AN\|M⁺ + TMP 两态，不在 36 内） | `已有合格替代证据，进入隔离准入链`（decisions.csv）——是**零计算隔离重审**，不是实验 | 不涉实验 |
| 3 态非 accepted（DMC×2 + EC） | `需要明确规则裁定` | 规则未批前不提实验 |

## 5. 未确定事项

1. **「检索尚未完成」到何种程度算穷尽**：上游 README 明示不可判定（行 21）；本组 36 态未逐态核过归档范围——本报告只按上游已分类原因码分组，**不新造搜索结论**。
2. G2 两态的最终处置依赖首点例外统一裁定（F1–F5，待裁）——在裁前只能维持缺证。
3. G1 四态物种身份核验的具体结论**未做**（本轮只读分组；逐态取证属 A 线后续或上游义务）。
4. 覆盖绑定仍全部按 B3 判定：36 态中 8 态 resolved 审查未被 recheck 否定（recheck 仅覆盖 8 个具名态），但其绑定前提是 Task A 证据通过后按既有通道重审——**本轮未绑定**。
