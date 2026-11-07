# 核心方案阅读入口

整理日期：2026-10-27。本文件仅整理文档，不修改方案、授权或验收标准。

## 先读哪一份

2026-10-29 执行更新：综合核心方案新增 §21，完整任务板见[执行补充 L00–L14](../电解液溶剂HB-Code/docs/plans/CORE_PLAN_EXECUTION_SUPPLEMENT_20261029.md)，可直接复制[DeepSeek Harness 长任务提示词](../电解液溶剂HB-Code/docs/handoffs/long_run_20261029/DEEPSEEK_GOAL_PROMPT.md)。45/48阶段交付与EC/DMC条件分支分别说明，新增计算预算仍须有实际授权。

1. [电解液排序稳定性—综合核心方案 v3.0](电解液排序稳定性-综合核心方案-v3.0.md)：两份源方案比较整合后的科学设计与验收依据。
2. [仓库现行执行计划](../电解液溶剂HB-Code/计划.md)：行动入口；数字有快照日期，不等于实时状态。
3. [计划文档总索引](../电解液溶剂HB-Code/docs/PLAN_INDEX.md)：恢复专题、历史版本、机器可读账本与交接材料的分类导航。

## 源方案与参考资料

| 文件 | 角色 |
| --- | --- |
| [ranking-electrolyte-materials-v2.md](ranking-electrolyte-materials-v2.md) | 原始研究框架；保留供追溯 |
| [electrolyte-ranking-implementation-plan (1).md](<electrolyte-ranking-implementation-plan (1).md>) | 原始实施方案；保留供追溯 |
| [文献阅读清单](ranking-electrolyte-materials-reading-list.md) | 支撑文献，不是生产排程 |
| [六篇核心文献精读](文献解读/六篇核心文献精读_v2方案对照_详版.docx) | 文献解读与方案对照 |
| [M 文献解读](文献解读/M文献解读.html) | 文献辅助材料 |
| [Gate1 溶液锚点电位表](<参照数据/Gate1_溶液锚点电位表 (1).csv>) | 数据材料，不等同于科学可比性验收 |

原文全部保留原位。不按文件名版本号机械覆盖规则；后续变更应核对批准记录、版本化契约及当前产物。此目录位于代码仓库外，不会随代码仓库的 Git 提交自动发布。

## 内部分类（2026-11-07）

判据是**引用计数**：只有「零引用」的文件才允许移动，被代码或文档引用的**一律原位**（`git grep -l -F "<路径>"` 于代码仓库统计）。

| 子目录 | 放什么 | 依据 |
| --- | --- | --- |
| `文献/` | 14 篇 PDF（`分支a-d/` 7 篇 + `新建文件夹/` 7 篇） | 原文既有结构，保留 |
| `文献解读/` | `M文献解读.html`、`六篇核心文献精读_v2方案对照_详版.docx` | 路径引用数 **0** ⇒ 可归位 |
| `参照数据/` | `Gate1_溶液锚点电位表 (1).csv` | 引用数 **0** ⇒ 可归位 |

**原位不动**：`电解液排序稳定性-综合核心方案-v3.0.md`（**4**，权威方案）、`ranking-electrolyte-materials-v2.md`（**89**）、`ranking-electrolyte-materials-reading-list.md`（**17**）、`electrolyte-ranking-implementation-plan (1).md`（0，但与 v3.0 同属"方案"层，不单独立目录）、`文献/新建文件夹/`（**6**）⇒ **目录名保留**：改名会打断 6 条已登记路径，其中 4 条在冻结交付镜像（`deliverables/part1|part2`）内、1 条在 `docs/24_week14_report.md`、1 条在 `data/anchors/solution_anchor_verification.md`。

