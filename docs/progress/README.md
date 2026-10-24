# 进度与研究日志索引

本目录把原先集中在根 README 的逐周流水账，改按**研究问题和证据用途**拆分。周次仍保留，方便定位历史提交和冻结产物，但不再作为理解项目的第一层结构。

## 阅读路线

| 主题日志 | 历史范围 | 主要问题 |
| --- | --- | --- |
| [基础、基线与计算台阶](01_foundations_and_ladders.md) | Week 1–8 | 定义、锚点、P0/P1/P2、构象与配位层如何建立？ |
| [排序稳定性与机制](02_stability_and_mechanisms.md) | Week 9–15 | 排序何时变化，介电、畸变和 SCF 初猜为什么重要？ |
| [状态身份、加固与收口](03_identity_hardening_and_closeout.md) | Week 16–27 | 电子态身份、反例审计、Gate 1 与 clean-room 复现如何收口？ |
| [工作包与物理证据补强](04_work_packages_and_physics.md) | Week 28–44 | WP0–WP7 如何把问题重新组织为定义、自由能、机制、ML 与预算工作包？ |
| [当前生产与恢复](05_current_production.md) | physics_completion_v1 | 当前 12×4 主态、系综、前沿身份与严格闸门进展在哪里看？ |

## 权威层级

1. 机器可读账本、CSV/JSON 与原始作业清单是数字的权威来源。
2. `outputs/` 下的 Markdown 是对应批次的人读摘要。
3. 本目录负责跨周解释和导航，不覆盖冻结产物。
4. 根 README 只展示当前状态和入口；完整结论矩阵见 [`FINAL_CONCLUSIONS.md`](../../FINAL_CONCLUSIONS.md)。

## 路径约定

- `outputs/week*`：历史冻结证据，保留原位，不继续作为新工作默认落点。
- `docs/NN_*.md`：历史阶段报告和方案修订，文件名用于稳定链接。
- `outputs/physics_completion/`：当前主题化生产证据。
- `docs/handoffs/`：特定恢复任务的交接与预注册记录。
- `deliverables/`：对外交付镜像，不是计算源数据。

新增工作应优先进入稳定的主题目录，例如 `outputs/physics_completion/ensembles/`，并在本索引对应主题下补链接；只有确需复刻历史批次时才新增 week 路径。
