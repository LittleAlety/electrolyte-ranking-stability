# 48 态零计算隔离重建

运行 ID：`4ed1af288fcebdb4`。本次未写正式表、账本或费用。输入与逐成员原始证据哈希见 `source_index.json`。
规则依据是用户指定的隔离技术重建；未记录虚构的用户签名。C3(i) 等效几何/频率规则尚未批准，保持关闭。

## 结果

- 当前结构成员 132，结构账本原始行 246；资格核查：{'NOT_ELIGIBLE': 124, 'ELIGIBLE': 8}。
- 48 态条件分类：{'NO_QUALIFIED_MEMBER': 40, 'COVERAGE_CLAIM_REVIEW_REQUIRED': 3, 'CONDITIONAL_EVIDENCE_SUFFICIENT': 5}。任何 `CONDITIONAL_*` 均非正式 accepted。
- DMC 五条暂存候选仍单列；EC 新候选未进入生产结构成员表，本次不暗中接入。
- P1 按 primary 与其他成员同样五项实测执行，已逐一读取其原始优化日志；历史资格和严格资格分开。原裁定草案中的 `PRIMARY_RULE_PENDING` 不用于本次技术筛选。
- `3928500_0` 的结算表称旧 TightSCF，但接收记录与原始 Opt 输入为 VeryTightSCF；这是协议来源冲突，须核对原始作业与结算标签，不能据旧标签走 C2。
- 旧 28/14/15/14 仅为历史模拟，不是本次重建预期值。逐态具体停点见 `gap_actions.json`。

| 态 | 历史 | 当前成员/合格 | 重建代表 | 旧追随者转代表 | 旧 coverage claim | 条件分类 |
|---|---|---:|---|---|---|---|
| AN\|LiM_2plus | accepted | 1/0 | — | — | 无 | NO_QUALIFIED_MEMBER |
| AN\|LiM_plus | accepted | 2/0 | — | — | 无 | NO_QUALIFIED_MEMBER |
| AN\|M | accepted | 2/0 | — | — | 无 | NO_QUALIFIED_MEMBER |
| AN\|M_plus | accepted | 5/1 | AN\|M_plus\|tors_3_0_1_2 | AN\|M_plus\|tors_3_0_1_2 | 需重审 | COVERAGE_CLAIM_REVIEW_REQUIRED |
| DEC\|LiM_2plus | accepted | 2/1 | DEC\|LiM_2plus\|c02 | — | 无 | CONDITIONAL_EVIDENCE_SUFFICIENT |
| DEC\|LiM_plus | accepted | 2/0 | — | — | 无 | NO_QUALIFIED_MEMBER |
| DEC\|M | accepted | 4/0 | — | — | 需重审 | NO_QUALIFIED_MEMBER |
| DEC\|M_plus | accepted | 3/1 | DEC\|M_plus\|15 | — | 无 | CONDITIONAL_EVIDENCE_SUFFICIENT |
| DMC\|LiM_2plus | limited | 5/0 | — | — | 无 | NO_QUALIFIED_MEMBER |
| DMC\|LiM_plus | accepted | 2/0 | — | — | 无 | NO_QUALIFIED_MEMBER |
| DMC\|M | accepted | 2/0 | — | — | 无 | NO_QUALIFIED_MEMBER |
| DMC\|M_plus | limited | 5/0 | — | — | 无 | NO_QUALIFIED_MEMBER |
| DME\|LiM_2plus | accepted | 4/0 | — | — | 需重审 | NO_QUALIFIED_MEMBER |
| DME\|LiM_plus | accepted | 1/0 | — | — | 无 | NO_QUALIFIED_MEMBER |
| DME\|M | accepted | 3/0 | — | — | 无 | NO_QUALIFIED_MEMBER |
| DME\|M_plus | accepted | 4/0 | — | — | 需重审 | NO_QUALIFIED_MEMBER |
| DMSO\|LiM_2plus | accepted | 2/0 | — | — | 无 | NO_QUALIFIED_MEMBER |
| DMSO\|LiM_plus | accepted | 3/0 | — | — | 需重审 | NO_QUALIFIED_MEMBER |
| DMSO\|M | accepted | 2/0 | — | — | 无 | NO_QUALIFIED_MEMBER |
| DMSO\|M_plus | accepted | 2/0 | — | — | 无 | NO_QUALIFIED_MEMBER |
| DOL\|LiM_2plus | accepted | 4/0 | — | — | 需重审 | NO_QUALIFIED_MEMBER |
| DOL\|LiM_plus | accepted | 2/0 | — | — | 无 | NO_QUALIFIED_MEMBER |
| DOL\|M | accepted | 2/0 | — | — | 无 | NO_QUALIFIED_MEMBER |
| DOL\|M_plus | accepted | 2/0 | — | — | 无 | NO_QUALIFIED_MEMBER |
| EC\|LiM_2plus | provisional | 7/0 | — | — | 无 | NO_QUALIFIED_MEMBER |
| EC\|LiM_plus | accepted | 2/0 | — | — | 无 | NO_QUALIFIED_MEMBER |
| EC\|M | accepted | 2/0 | — | — | 无 | NO_QUALIFIED_MEMBER |
| EC\|M_plus | accepted | 2/0 | — | — | 无 | NO_QUALIFIED_MEMBER |
| EMC\|LiM_2plus | accepted | 1/0 | — | — | 无 | NO_QUALIFIED_MEMBER |
| EMC\|LiM_plus | accepted | 3/0 | — | — | 无 | NO_QUALIFIED_MEMBER |
| EMC\|M | accepted | 3/0 | — | — | 无 | NO_QUALIFIED_MEMBER |
| EMC\|M_plus | accepted | 3/0 | — | — | 需重审 | NO_QUALIFIED_MEMBER |
| GBL\|LiM_2plus | accepted | 2/0 | — | — | 无 | NO_QUALIFIED_MEMBER |
| GBL\|LiM_plus | accepted | 2/1 | GBL\|LiM_plus\|c03 | — | 无 | CONDITIONAL_EVIDENCE_SUFFICIENT |
| GBL\|M | accepted | 2/0 | — | — | 无 | NO_QUALIFIED_MEMBER |
| GBL\|M_plus | accepted | 2/0 | — | — | 无 | NO_QUALIFIED_MEMBER |
| PC\|LiM_2plus | accepted | 2/0 | — | — | 无 | NO_QUALIFIED_MEMBER |
| PC\|LiM_plus | accepted | 2/0 | — | — | 无 | NO_QUALIFIED_MEMBER |
| PC\|M | accepted | 2/0 | — | — | 无 | NO_QUALIFIED_MEMBER |
| PC\|M_plus | accepted | 2/1 | PC\|M_plus\|46 | — | 无 | CONDITIONAL_EVIDENCE_SUFFICIENT |
| SL\|LiM_2plus | accepted | 5/0 | — | — | 需重审 | NO_QUALIFIED_MEMBER |
| SL\|LiM_plus | accepted | 2/0 | — | — | 无 | NO_QUALIFIED_MEMBER |
| SL\|M | accepted | 2/0 | — | — | 无 | NO_QUALIFIED_MEMBER |
| SL\|M_plus | accepted | 2/0 | — | — | 无 | NO_QUALIFIED_MEMBER |
| TMP\|LiM_2plus | accepted | 4/1 | TMP\|LiM_2plus\|c13 | — | 需重审 | COVERAGE_CLAIM_REVIEW_REQUIRED |
| TMP\|LiM_plus | accepted | 4/0 | — | — | 需重审 | NO_QUALIFIED_MEMBER |
| TMP\|M | accepted | 3/1 | TMP\|M\|27 | — | 无 | CONDITIONAL_EVIDENCE_SUFFICIENT |
| TMP\|M_plus | accepted | 5/1 | TMP\|M_plus\|27 | — | 需重审 | COVERAGE_CLAIM_REVIEW_REQUIRED |

## 下一动作边界

- `NO_QUALIFIED_MEMBER`：逐成员读取 `source_index.json` 的五项实测与原因；先查现有原始证据，不从态数推作业数。
- 有合格代表但仍有历史限制/coverage claim 的态：在已批准规则下重做 coverage，不沿用旧 `resolved` 字样。
- `CONDITIONAL_EVIDENCE_SUFFICIENT`：仅表示隔离成员池与现有登记没有在本次检查中显示阻断；仍需独立身份/协议和 coverage 复核，不作正式发布。
- 所有待补证项均为零计算检索或明确条款停点；本轮不提出未经逐项审定的补算预算。
