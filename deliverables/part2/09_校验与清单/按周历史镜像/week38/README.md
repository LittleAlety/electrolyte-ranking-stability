# week38 / WP1 独立方法审计表

> 由 `scripts/wp_production/build_physics_completion_deliverables.py` 从仓库源路径镜像生成；
> `--check` 逐文件复核 byte-identical。所有路径保持仓库相对形状。

## 交付内容

| 项 | 值 |
| --- | --- |
| 周次 | week38 |
| 工作包 | WP1 独立方法审计表 |
| 文件数 | 23 |
| 验收项 | 14 |
| 校验 | 5/5 通过 |

## 文件清单

- `docs/59_week38_wp1_method_audit.md`
- `outputs/physics_completion/cost/audit_cost_ledger.csv`
- `outputs/physics_completion/method_audit/audit_geometry_note.json`
- `outputs/physics_completion/method_audit/axis_sensitivity.csv`
- `outputs/physics_completion/method_audit/existing_reusable_jobs.csv`
- `outputs/physics_completion/method_audit/job_matrix.csv`
- `outputs/physics_completion/method_audit/local_method_echo.csv`
- `outputs/physics_completion/method_audit/local_smoke_runs.csv`
- `outputs/physics_completion/method_audit/local_toolchain.csv`
- `outputs/physics_completion/method_audit/method_settings.csv`
- `outputs/physics_completion/method_audit/pair_gap_sensitivity.csv`
- `outputs/physics_completion/method_audit/relaxed_leg_matrix.csv`
- `outputs/physics_completion/method_audit/robust_inversion_certification.csv`
- `outputs/physics_completion/method_audit/robust_inversion_certification.json`
- `outputs/physics_completion/method_audit/state_energy_spread.csv`
- `outputs/week38/manifest.json`
- `outputs/week38/wp1_acceptance.csv`
- `outputs/week38/wp1_method_audit.json`
- `outputs/week38/wp1_summary.md`
- `scripts/build_physics_completion_batch.py`
- `scripts/wp_production/build_physics_completion_deliverables.py`
- `src/electrolyte_ranking/pc_batch.py`
- `tests/test_physics_completion_batch.py`

## 口径纪律

Gate 0 CLOSED；Gate 1 NOT CLOSED 且 NOT CLOSABLE（本批次只登记与复算既有冻结数据：不复核、不关闭、不跳过；排序/配对证据零新增电子结构计算、零数据剔除、零阈值改动；WP1 另计 161 个本机独立方法审计作业（128 单点 + 32 弛豫腿 + 1 EMC Li 松弛）、WP2 另计 12 分子四主态 pilot，以及 4 分子 x 4 主态生产 Opt/Freq（目标 16 态，实际登记进度见 week39 载荷与 production_ledger.csv），原始日志不入镜像）

三层表述（模型事实 / 统计判定 / 材料意义）不得混写；方向 ox = IP、red = -EA（均 maximise）；主结论带 Track A / Track B / 待验证推断标签；措辞只用 designated computational target / designated reference model，Gate 1 闭合前禁用 validated target；NOT CLOSABLE 不等于 NO SUCH DATA EXIST ANYWHERE。
