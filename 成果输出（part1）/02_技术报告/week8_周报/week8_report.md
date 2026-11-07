# Week 8 成果小结 —— Stage 9（显式微溶剂化：C2 = [Li(M)2]+ 第一溶剂壳复核）

Week 5 把自由分子 C0 换成了 Li+ 配位条件态 C1（[Li M]+）。本周再往前一步：把第一溶剂壳从
1:1 扩到 **1:2**（[Li(M)2]+），在**同一条冻结计算臂**（r2SCAN-3c、气相、同一批种子）上重测
同一组三态垂直量，回答「C1 台阶上看到的位移与排序结论，会不会被第一个配体之外的溶剂化
结构改写」。本文可独立阅读；逐项细节、文献依据与计划修订见同目录
`week8_report_full.md`、`branch_abcd_qa.md` 与 `plan_optimization_branchABC.md`。

## 1. 本周做了什么
对 Week 5 的 C1(1:1) 条件态做**显式第一溶剂壳**复核：把 [Li M]+ 扩成 [Li(M)2]+，共 **12** 个壳层 motif（覆盖 **8** 个家族），复用同一条冻结计算臂（r2SCAN-3c、气相、相同种子）测同一组三态垂直量，再与 C1(1:1)（`outputs/week5/c1_coord_shifts.csv`）和自由分子 C0 做同口径的配对排序稳定性对比。壳层枚举规则：锚定 r2SCAN-3c 优化的 [Li M]+ 几何，取 G1 第二配体，Fibonacci 球面 96 方向 x 12 滚转刚体放置，剔除冲突后取前 4 个做 GFN2-xTB 打分，最低者做 xTB 优化。

## 2. 关键数字
- 逐 motif 位移（相对 C0，均值 ± 样本 std）：C1(1:1) 氧化 +4.887 ± 0.595 eV / 还原 +6.578 ± 0.832 eV；C2(1:2) 氧化 +3.187 ± 0.562 eV / 还原 +5.380 ± 0.603 eV
- 从 1:1 到 1:2 的**位移本身的变化**：ΔIP -1.700 ± 0.259 eV，ΔEA -1.199 ± 0.335 eV
- 氧化轴 C1 -> C2：n=12, tau_b **0.697**, Top-20% 重叠 0.500, f_unresolved 0.273, f_robust_inv 0.000
- 还原轴 C1 -> C2：n=12, tau_b **0.848**, Top-20% 重叠 0.500, f_unresolved 0.152, f_robust_inv 0.000

## 3. C1 -> C2 的配对排序稳定性
| 轴 | 总体 | n | tau_b | Top-10% 重叠 | Top-20% 重叠 | f_unresolved (C2) | f_robust_inv |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 氧化 | all12 | 12 | 0.697 | 1.000 | 0.500 | 0.273 | 0.000 |
| 还原 | all12 | 12 | 0.848 | 1.000 | 0.500 | 0.152 | 0.000 |
| 氧化（仅 m1） | primary_m1 | 10 | 0.778 | 1.000 | 0.500 | 0.267 | 0.000 |
| 还原（仅 m1） | primary_m1 | 10 | 0.911 | 1.000 | 1.000 | 0.156 | 0.000 |


## 4. 质量与复核（QC）
- DFT 作业 **36** 个，`ok` **36** 个；状态分布 ok=36；QC flag 无；壳层生成 18432 个放置（10401 个无冲突、48 个被打分、12 个入选），全部 `second_ligand_intact=True`
- 上述每一项都由本目录 `verification.json` 的 `checks` 数组从真实产物现场解析得出。

## 5. 产物清单
- `artifacts/F18_stage9_explicit_shell.png`
- `artifacts/figure_manifest_week8_stage9.md`
- `branch_abcd_qa.md`
- `ms_shell_generation.csv`
- `ms_shell_generation.json`
- `ms_shell_generation.md`
- `plan_optimization_branchABC.md`
- `stage9_decision_stability.csv`
- `stage9_jobs.csv`
- `stage9_results.json`
- `stage9_shell_shifts.csv`
- `stage9_summary.json`
- `stage9_summary.md`
- `structures/microsolvation/AN_m1_shell2.xyz`
- `structures/microsolvation/DMC_m1_shell2.xyz`
- `structures/microsolvation/DMC_m2_shell2.xyz`
- `structures/microsolvation/DME_m1_shell2.xyz`
- `structures/microsolvation/DMSO_m1_shell2.xyz`
- `structures/microsolvation/DOL_m1_shell2.xyz`
- `structures/microsolvation/EC_m1_shell2.xyz`
- `structures/microsolvation/EC_m1_shell3.xyz`
- `structures/microsolvation/GBL_m1_shell2.xyz`
- `structures/microsolvation/SL_m1_shell2.xyz`
- `structures/microsolvation/SN_m1_shell2.xyz`
- `structures/microsolvation/TMP_m1_shell2.xyz`
- `structures/microsolvation/TMP_m2_shell2.xyz`
- `week8_report_full.md`

## 6. 已知限制
1. Stage 9 只做**垂直**量（`--skip-relax`），因为 Week 5 的头条口径也是垂直量；氧化/还原态的再弛豫在 1:1 里本就属支线，1:2 未复现。壳层是**几何预筛**结果（xTB 打分后的最低者），不是全构象系综的最低能结构。
2. 壳层规模小（12 个 motif / 8 个家族），Top-k 指标在 12 个点上对单点扰动敏感，只读方向与量级。
3. Gate 0 保持 CLOSED；Gate 1 仍未关闭（溶液相锚点 31 行仍为 `est`）。
4. Stage 9 在本项目 v2 §19 中被定义为 **optional**；若要把它提升为必报指标，必须走
   `config/prereg.yaml` 的 `amendment_log`，届时 Gate 0 会由 CLOSED 变为 NOT CLOSED。
5. 逐项细节见同目录 `week8_report_full.md`。

## 7. 源文件缺失
- 无（全部源路径均存在）
