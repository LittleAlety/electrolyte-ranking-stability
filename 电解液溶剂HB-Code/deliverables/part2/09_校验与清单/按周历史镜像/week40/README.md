# week40 / WP3 排序、独立不确定度与机制

> 由 `scripts/wp_production/build_physics_completion_deliverables.py` 从仓库源路径镜像生成；
> `--check` 逐文件复核 byte-identical。所有路径保持仓库相对形状。

## 交付内容

| 项 | 值 |
| --- | --- |
| 周次 | week40 |
| 工作包 | WP3 排序、独立不确定度与机制 |
| 文件数 | 16 |
| 验收项 | 11 |
| 校验 | 5/5 通过 |

## 文件清单

- `docs/61_week40_wp3_pair_evidence_mechanism.md`
- `outputs/physics_completion/pair_evidence/conservative_interval_protocol.md`
- `outputs/physics_completion/pair_evidence/frozen_rung_ladder.csv`
- `outputs/physics_completion/pair_evidence/mechanism_bond_changes.csv`
- `outputs/physics_completion/pair_evidence/mechanism_cases.csv`
- `outputs/physics_completion/pair_evidence/mechanism_cases.md`
- `outputs/physics_completion/pair_evidence/mechanism_geometry.csv`
- `outputs/physics_completion/pair_evidence/pair_evidence.csv`
- `outputs/week40/manifest.json`
- `outputs/week40/wp3_acceptance.csv`
- `outputs/week40/wp3_pair_evidence.json`
- `outputs/week40/wp3_summary.md`
- `scripts/build_physics_completion_batch.py`
- `scripts/wp_production/build_physics_completion_deliverables.py`
- `src/electrolyte_ranking/pc_batch.py`
- `tests/test_physics_completion_batch.py`

## 口径纪律

Gate 0 CLOSED；Gate 1 NOT CLOSED 且 NOT CLOSABLE（本批次只登记与复算既有冻结数据：不复核、不关闭、不跳过；排序/配对证据零新增电子结构计算、零数据剔除、零阈值改动；WP1 另计 161 个本机独立方法审计作业（128 单点 + 32 弛豫腿 + 1 EMC Li 松弛）、WP2 另计 12 分子四主态 pilot，以及 4 分子 x 4 主态生产 Opt/Freq（目标 16 态，实际登记进度见 week39 载荷与 production_ledger.csv），原始日志不入镜像）

三层表述（模型事实 / 统计判定 / 材料意义）不得混写；方向 ox = IP、red = -EA（均 maximise）；主结论带 Track A / Track B / 待验证推断标签；措辞只用 designated computational target / designated reference model，Gate 1 闭合前禁用 validated target；NOT CLOSABLE 不等于 NO SUCH DATA EXIST ANYWHERE。
