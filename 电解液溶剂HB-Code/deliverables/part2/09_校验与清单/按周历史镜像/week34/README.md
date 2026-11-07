# Week 34 / WP7 交付件：外部验证与结论边界

> 镜像目录 `E:\Claude Code\电解液溶剂-HB\成果输出（part2）\week34`。part1 覆盖 week1-week25，part2 从 week28（= WP1）起。
> 本目录由 `scripts/build_week34_deliverables.py` 确定性重建：源缺失即报错，
> `--check` 逐文件复核 SHA256。目录内**不含**任何 ORCA / xTB 原始输出与二进制 scratch。

## 内容

| 路径 | 内容 |
| --- | --- |
| `outputs/week34/anchor_inventory.csv` | 逐 anchor 文件的条件一致性、provenance 与排序层可用性 |
| `outputs/week34/anchor_row_audit.csv` | 31 行绝对标定 anchor 的逐行未升级原因（一行不少） |
| `outputs/week34/ordering_recheck.csv` | within-series tau_b 的独立重算 vs 冻结值 |
| `outputs/week34/gate1_components.csv` | Gate 1 两层组件的状态与观测值 |
| `outputs/week34/gate1_status.csv` | 8 条预注册关闭条件逐条对账 |
| `outputs/week34/track_separation.csv` | Track A / Track B 的范围与结论权限 |
| `outputs/week34/claim_track_assignment.csv` | 10 条主结论 -> 轨道映射 |
| `outputs/week34/naming_compliance.csv` | 70 个交付文件的措辞合规扫描 |
| `outputs/week34/supplemental_compute_triggers.csv` | 何时才值得新增电子结构计算 |
| `outputs/week34/wp7_acceptance.csv` | 四个验收问题的结论与证据 |
| `outputs/week34/wp7_external_reference.json` | 全量载荷 + 10 项自检 |
| `outputs/week34/wp7_summary.md` | 汇总报告 |
| `docs/56_week34_wp7_external_reference_boundary.md` | 周报 |
| `docs/gate1_negative_result.md` | Gate 1 = negative result 的落地文档 |
| `src/electrolyte_ranking/wp7.py` | WP7 分析原语（可复用） |
| `outputs/gate1/`、`outputs/week25/`、`outputs/week2/`、`outputs/week24_corealign/` | 冻结输入（双轨判定 / 排序复核 / anchor 审计 / 可行性） |
| `data/anchors/*.csv` | 冻结 anchors（101 行，一行未删） |
| `scripts/`、`tests/`、`config/` | 生成器、回归测试与口径配置 |

## 本阶段最重要的一条

Gate 1 维持 **NOT CLOSED / NOT CLOSABLE**：它既没有被跳过，也没有被强迫关闭。8 条预注册关闭
条件里 3 条未达成，决定性的一条是排序一致性 **tau_b = 0.4286 < 0.90**。同时必须一起发布
措辞边界：**NOT CLOSABLE != NO SUCH DATA EXIST ANYWHERE**——这是可被证伪的负结果。
另一条同样重要：**没有一个 anchor 行被删**。31 行 estimates 仍然只是 estimates，
它们不因为「不一致」而被移除。

## 纪律

- 零新增电子结构计算；零数据剔除；零阈值改动。
- 结论一律带轨道标签：Track A（computational decision stability）/ Track B（external
  reference validity）/ 待验证推断。
- 措辞：只用 `designated computational target` / `designated reference model`；`validated target` 在 Gate 1 闭合前禁用。
