# Week 3 成果小结 —— Stage 2 broad cheap pool（P0）

## 1. 本周做了什么
- 用 GFN2-xTB 对 core set（18）与 broad pool（40）跑 P0 廉价代理，产物 `p0_core_set.csv`、
  `p0_broad_pool.csv`（Koopmans：`p0_ox = -eps_HOMO`、`p0_red = +eps_LUMO`）。
- 化学空间覆盖与家族分布图：`fig1_family_counts.png`、`fig2_mw_donor.png`、
  `fig3_p0_ox_fluorinated.png`、`fig4_ec_ionization_pilot.png`；汇总图 F1 / F2 收在 `artifacts/`。
- 决策预览：Top-k 重叠 / Jaccard、参考配体 DME 与 AN 的定位（`decision_stability_preview.md`）。
- ORCA 冒烟测试（`orca_smoke/`），为 Week 4 的 P1 层打通通路。

## 2. 关键数字
| 项目 | 值 | 来源 |
| --- | --- | --- |
| core P0 成功 | 18 / 18 | `p0_core_set_summary.json` |
| broad P0 成功 | 40 / 40 | `p0_broad_pool_summary.json` |
| 合并可用于决策的池规模 | 58 | `p0_summary.json` |
| 氧化轴 vs 还原轴 Kendall tau_b（合并池） | −0.302 | 同上 |
| 参考配体 primary_R | DME（C08，双齿 2×O 螯合） | 同上 |
| 第二参考 R | AN（C16，仅 robustness check） | 同上 |
| core P0 ox 范围 | 10.424 .. 12.996 eV | `p0_core_set_summary.json` |
| core P0 red 范围 | −6.877 .. 0.718 eV | 同上 |
| core HOMO-LUMO gap 中位数 | 6.248 eV | 同上 |
| core 偶极中位数 | 3.393 D | 同上 |

氧化轴与还原轴在廉价层上**负相关**（tau_b = −0.302）：耐氧化与耐还原在本代理层上相互拉扯，
这正是后面必须引入真实电子结构层来裁断的动机。

## 3. 质量与复核（QC）
- 两个池均 `n_ok == n_total`、`n_failed = 0`、`n_abnormal_termination = 0`、
  `n_missing_p0_fields = 0`（现场从 JSON 解析，见 `verification.json`）。
- 与 week2 方法审计的交叉核对状态记录在 `p0_summary.json` 的 `cross_check_vs_week2`。
- P0 的 `--alpha` 单点作业仅作辅助交叉确认，**不参与任何排序**。

## 4. 产物清单
- `05_stage2_broad_pool_p0.md`
- `09_week3_report.md`
- `artifacts/F1_chemical_space_coverage.png`
- `artifacts/F2_p0_distributions_by_family.png`
- `coverage_report.md`
- `decision_stability_preview.md`
- `fig1_family_counts.png`
- `fig2_mw_donor.png`
- `fig3_p0_ox_fluorinated.png`
- `fig4_ec_ionization_pilot.png`
- `orca_pilot_summary.json`
- `orca_smoke/EC_anion.inp`
- `orca_smoke/EC_anion.out`
- `orca_smoke/EC_anion.xyz`
- `orca_smoke/EC_anion_orca.json`
- `orca_smoke/EC_cation.inp`
- `orca_smoke/EC_cation.out`
- `orca_smoke/EC_cation.xyz`
- `orca_smoke/EC_cation_orca.json`
- `orca_smoke/EC_gas.inp`
- `orca_smoke/EC_gas.out`
- `orca_smoke/EC_gas.xyz`
- `orca_smoke/EC_gas_orca.json`
- `orca_smoke/EC_smd.inp`
- `orca_smoke/EC_smd.out`
- `orca_smoke/EC_smd.xyz`
- `orca_smoke/EC_smd_orca.json`
- `p0_broad_pool.csv`
- `p0_broad_pool_summary.json`
- `p0_core_set.csv`
- `p0_core_set_summary.json`
- `p0_summary.json`

## 5. 已知限制
- P0 是 Koopmans 代理，与真实垂直 IP/EA **不是同一物理量**；其还原轴尤其不可直接解读为 EA。
- 单构象几何（RDKit ETKDG 单次嵌入 + MMFF 预优化），未做构象搜索。
- Gate 1 仍未关闭；本周不宣称任何「最终筛选名单」。

## 6. 源文件缺失
- 无（全部源路径均存在）
