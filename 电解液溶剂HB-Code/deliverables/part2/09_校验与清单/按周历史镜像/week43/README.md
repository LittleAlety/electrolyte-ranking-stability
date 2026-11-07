# week43 / WP6 显式配体检查（可选）与论文主线

> 由 `scripts/wp_production/build_physics_completion_deliverables.py` 从仓库源路径镜像生成；
> `--check` 逐文件复核 byte-identical。所有路径保持仓库相对形状。

## 交付内容

| 项 | 值 |
| --- | --- |
| 周次 | week43 |
| 工作包 | WP6 显式配体检查（可选）与论文主线 |
| 文件数 | 19 |
| 验收项 | 4 |
| 校验 | 5/5 通过 |

## 文件清单

- `docs/64_week43_wp6_explicit_ligand_and_paper.md`
- `docs/physics_completion_final_report.md`
- `outputs/figures/F59_physics_completion_definition.png`
- `outputs/figures/F60_physics_completion_method_audit.png`
- `outputs/figures/F61_physics_completion_ladder.png`
- `outputs/figures/F62_physics_completion_pair_identity.png`
- `outputs/figures/F63_physics_completion_mechanism_cases.png`
- `outputs/figures/F64_physics_completion_budget_curve.png`
- `outputs/figures/figure_manifest_week45_physics_completion.md`
- `outputs/physics_completion/explicit_ligand/explicit_ligand_plan.csv`
- `outputs/week43/manifest.json`
- `outputs/week43/wp6_acceptance.csv`
- `outputs/week43/wp6_explicit_ligand.json`
- `outputs/week43/wp6_summary.md`
- `scripts/build_physics_completion_batch.py`
- `scripts/wp_production/build_physics_completion_deliverables.py`
- `scripts/wp_production/make_physics_completion_figures.py`
- `src/electrolyte_ranking/pc_batch.py`
- `tests/test_physics_completion_batch.py`

## 口径纪律

Gate 0 CLOSED；Gate 1 NOT CLOSED 且 NOT CLOSABLE（本批次只登记与复算既有冻结数据：不复核、不关闭、不跳过；排序/配对证据零新增电子结构计算、零数据剔除、零阈值改动；WP1 另计 161 个本机独立方法审计作业（128 单点 + 32 弛豫腿 + 1 EMC Li 松弛）、WP2 另计 12 分子四主态 pilot，以及 4 分子 x 4 主态生产 Opt/Freq（目标 16 态，实际登记进度见 week39 载荷与 production_ledger.csv），原始日志不入镜像）

三层表述（模型事实 / 统计判定 / 材料意义）不得混写；方向 ox = IP、red = -EA（均 maximise）；主结论带 Track A / Track B / 待验证推断标签；措辞只用 designated computational target / designated reference model，Gate 1 闭合前禁用 validated target；NOT CLOSABLE 不等于 NO SUCH DATA EXIST ANYWHERE。
