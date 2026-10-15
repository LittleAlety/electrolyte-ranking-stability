# Week 2 成果小结 —— Stage 1 方法审计与外部锚点

## 1. 本周做了什么
- 建立并校验外部气相 redox 锚点库（`docs/01_stage1_external_anchors.md`）。
- 方法审计：对 12 个分子跑 GFN2-xTB 的中性 / 阳离子 / 阴离子三态，比较 Koopmans 与 ΔSCF
  （`docs/02`、`docs/04`；产物 `method_audit_xtb.csv`、`method_audit_xtb_summary.json`）。
- 溶液相锚点审计：31 行逐条核对证据等级（`docs/06`；产物 `solution_anchor_audit.csv/.json`）。
- Gate 1 检查，留下 `outputs/week2/gate1_record.md`。
- 本目录额外收录 `docs/03_week1_2_report.md`（Week 1–2 的连续叙述）。

## 2. 关键数字
| 项目 | 值 | 来源 |
| --- | --- | --- |
| 方法审计分子数 | 12 | `method_audit_xtb_summary.json` |
| 其中气相不束缚的阴离子 | 2 | 同上 |
| 溶液锚点总行数 | 31 | `solution_anchor_audit.json` |
| 审计后仍为 `est` 的行数 | 31 | 同上 |
| 被升级为 `exp` / `calc` 的行数 | 0 | 同上 |
| 一致性检查 | `True`（0 处冲突） | 同上 |
| Gate 1 状态 | **NOT CLOSED** | `gate1_record.md` |

溶液锚点 31 行的证据类型分布：`solvent_anion_coupling` 7、`condition_mismatch` 5、`no_reference` 5、
`review_trend_only` 5、`computational_not_retrieved` 5、`mis_citation` 2、
`source_does_not_cover_species` 1、`source_does_not_provide_value` 1。合计 31 行，**没有任何一行**
能升级为 `exp` 或 `calc`。

## 3. 质量与复核（QC）
- Gate 1 检查中 `anchors:validate_anchors` 与两条 toolchain 检查通过；绝对标定级
  `anchors:solution_absolute_calibration` 未通过（31 行仍为 `est`），按 R7 记为 limitation；
  排序一致性级 `anchors:series_rel_ordering` 亦未通过（`n_pairs = 0`，低于预注册下限 18）。
- 方法审计与溶液锚点审计的数字均从本目录 JSON 现场解析，见 `verification.json`。
- 关键限制由锚点审计显式记录，而不是被静默吸收。

## 4. 产物清单
- `01_stage1_external_anchors.md`
- `02_stage1_method_audit.md`
- `03_week1_2_report.md`
- `04_stage1_xtb_audit_result.md`
- `06_stage1_solution_anchor_audit.md`
- `gate1_record.md`
- `method_audit_xtb/AN/anion_opt.xyz`
- `method_audit_xtb/AN/cation_opt.xyz`
- `method_audit_xtb/AN/neutral_opt.xyz`
- `method_audit_xtb/AN/neutral_start.xyz`
- `method_audit_xtb/DEC/anion_opt.xyz`
- `method_audit_xtb/DEC/cation_opt.xyz`
- `method_audit_xtb/DEC/neutral_opt.xyz`
- `method_audit_xtb/DEC/neutral_start.xyz`
- `method_audit_xtb/DMC/anion_opt.xyz`
- `method_audit_xtb/DMC/cation_opt.xyz`
- `method_audit_xtb/DMC/neutral_opt.xyz`
- `method_audit_xtb/DMC/neutral_start.xyz`
- `method_audit_xtb/DME/anion_opt.xyz`
- `method_audit_xtb/DME/cation_opt.xyz`
- `method_audit_xtb/DME/neutral_opt.xyz`
- `method_audit_xtb/DME/neutral_start.xyz`
- `method_audit_xtb/DMSO/anion_opt.xyz`
- `method_audit_xtb/DMSO/cation_opt.xyz`
- `method_audit_xtb/DMSO/neutral_opt.xyz`
- `method_audit_xtb/DMSO/neutral_start.xyz`
- `method_audit_xtb/DOL/anion_opt.xyz`
- `method_audit_xtb/DOL/cation_opt.xyz`
- `method_audit_xtb/DOL/neutral_opt.xyz`
- `method_audit_xtb/DOL/neutral_start.xyz`
- `method_audit_xtb/EA/anion_opt.xyz`
- `method_audit_xtb/EA/cation_opt.xyz`
- `method_audit_xtb/EA/neutral_opt.xyz`
- `method_audit_xtb/EA/neutral_start.xyz`
- `method_audit_xtb/EC/anion_opt.xyz`
- `method_audit_xtb/EC/cation_opt.xyz`
- `method_audit_xtb/EC/neutral_opt.xyz`
- `method_audit_xtb/EC/neutral_start.xyz`
- `method_audit_xtb/GBL/anion_opt.xyz`
- `method_audit_xtb/GBL/cation_opt.xyz`
- `method_audit_xtb/GBL/neutral_opt.xyz`
- `method_audit_xtb/GBL/neutral_start.xyz`
- `method_audit_xtb/PC/anion_opt.xyz`
- `method_audit_xtb/PC/cation_opt.xyz`
- `method_audit_xtb/PC/neutral_opt.xyz`
- `method_audit_xtb/PC/neutral_start.xyz`
- `method_audit_xtb/SL/anion_opt.xyz`
- `method_audit_xtb/SL/cation_opt.xyz`
- `method_audit_xtb/SL/neutral_opt.xyz`
- `method_audit_xtb/SL/neutral_start.xyz`
- `method_audit_xtb/TMP/anion_opt.xyz`
- `method_audit_xtb/TMP/cation_opt.xyz`
- `method_audit_xtb/TMP/neutral_opt.xyz`
- `method_audit_xtb/TMP/neutral_start.xyz`
- `method_audit_xtb.csv`
- `method_audit_xtb_summary.json`
- `series_rel_ordering_check.json`
- `solution_anchor_audit.csv`
- `solution_anchor_audit.json`

## 5. 已知限制
- **Gate 1 未关闭**：blocker 是排序一致性级 —— within-series 锚点对 `n_pairs = 0`，低于预注册下限 18
  （`scripts/check_series_rel_ordering.py`）；绝对标定级（31 行 `est`）按 R7 记为 limitation，不再单列 blocker。
- 因此 week2 之后的所有 P1/P2 结果都以**气相锚点**为主判据，溶液相只作定性对照。
- xTB scratch（`xtbrestart` / `xtbtopo.mol` / `xtboptok` / `wbo` / `charges`）按约定不进入交付包。

## 6. 源文件缺失
- 无（全部源路径均存在）
