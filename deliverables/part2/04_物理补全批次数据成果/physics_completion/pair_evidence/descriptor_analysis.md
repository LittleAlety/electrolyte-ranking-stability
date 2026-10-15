# WP3 §7.3 描述符分析（donor type / chelation / flexibility / functionalization / 廉价 ESP）

本页由 `scripts/wp_production/build_descriptor_analysis.py` 只读派生，数据只来自冻结产物，不含任何新的电子结构计算。缺值留空并按名字登记，绝不补 0、绝不插值。

生成命令：

```
.venv/Scripts/python.exe -X utf8 scripts/wp_production/build_descriptor_analysis.py
```

## 1. 口径

- 样本：`data/metadata/physics_completion_set.csv` 中 cohort=main 的 12 个分子（n=12）。
- 方法：n=12 不拟合多参数机制模型；每个描述符只与**单个**氧化排序量做一次单变量检验。
- 检验：数值描述符用 Spearman 秩相关；二值描述符用 Mann-Whitney U；多水平分类描述符用 Kruskal-Wallis H。弱值、不显著、退化一律进表。
- 多重比较：在同一 target 的检验族内做 Holm（主，任意依赖下控 FWER）与 Benjamini-Hochberg（次，控 FDR）。两列同时给出，不按结果挑。

## 2. 描述符来源（不臆造列名）

| 描述符 | 类型 | 来源 | 口径 |
|---|---|---|---|
| donor_type | 分类 | derived_from_family | 由冻结 family 列映射到给体原子/类型 |
| chelation_capable | 二值 | derived_from_donor_count | donor_count>=2 的多给体计数代理（非已证螯合） |
| flexibility_rotatable_bonds | 数值 | frozen_column | 冻结列 rotatable_bonds |
| functionalization_family | 分类 | frozen_column | 冻结列 family |
| cheap_esp | — | not_available | 允许来源无该标量 |
| tpsa | — | not_available | 允许来源无该列，且方案定为仅探索性 |

> `donor_type` 与 `functionalization_family` 在 12 个分子上高度共线：碳酸酯的两个子族在 donor_type 里同为 `carbonyl_O`，其余族一一对应。二者不是独立重复——这正是多重比较用 Holm（不假定独立）而不用 BH 的原因之一。

## 3. 逐分子描述符矩阵与氧化排序量

| name | family | donor_count | rotatable_bonds | donor_type | chelation_capable | rigidity_class | Eox_vertical_P1v_eV | Eox_adiabatic_P1a_eV | Eox_vertical_wB97X_SMD_eV |
|---|---|---|---|---|---|---|---|---|---|
| DMC | linear_carbonate | 3 | 0 | carbonyl_O | true | rigid | 10.579877 | 10.174174 | 8.957162 |
| EMC | linear_carbonate | 3 | 1 | carbonyl_O | true | semi_flexible | 10.201591 | 9.251275 | 8.537180 |
| DEC | linear_carbonate | 3 | 2 | carbonyl_O | true | flexible | 9.984333 | not_available | 8.592402 |
| EC | cyclic_carbonate | 3 | 0 | carbonyl_O | true | rigid | 10.769123 | 10.394139 | 8.603601 |
| PC | cyclic_carbonate | 3 | 0 | carbonyl_O | true | rigid | 10.538833 | 10.214086 | 8.542029 |
| DME | ether | 2 | 3 | ether_O | true | flexible | 8.856018 | 8.446041 | 6.831624 |
| DOL | ether | 2 | 0 | ether_O | true | rigid | 9.313142 | 9.172386 | 7.184396 |
| GBL | ester | 2 | 0 | ester_O | true | rigid | 9.951541 | 9.707067 | 8.034424 |
| SL | sulfone | 2 | 0 | sulfonyl_O | true | rigid | 9.793052 | 9.528854 | 7.937598 |
| DMSO | sulfoxide | 1 | 0 | sulfoxide_O | false | rigid | 8.814169 | 8.530923 | 6.475203 |
| AN | nitrile | 1 | 0 | nitrile_N | false | rigid | 12.140437 | 11.828994 | 9.463296 |
| TMP | phosphate | 4 | 3 | phosphate_O | true | flexible | 10.056812 | 9.437639 | 8.715843 |

- `Eox_vertical_P1v`（r2SCAN-3c 气相竖直 E(M+)-E(M)（layer=P1v），primary）：n=12/12；全部有值。
- `Eox_adiabatic_P1a`（r2SCAN-3c 气相弛豫电子能差（layer=P1a），sensitivity）：n=11/12；缺值分子（留空不补）：DEC。
- `Eox_vertical_wB97X_SMD`（wB97X-D4 / SMD(乙腈) 单点竖直 IP，sensitivity）：n=12/12；全部有值。

## 4. 全部检验（含不显著的）

| target | descriptor | test | n | statistic | p_raw | p_holm | p_bh | sig_holm | sig_bh | direction | status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Eox_vertical_P1v | donor_type | Kruskal-Wallis H | 12 | H=9.823077 | 0.132303 | 0.529212 | 0.355870 | false | false | n/a_multi_level | computed |
| Eox_vertical_P1v | chelation_capable | Mann-Whitney U | 12 | U=10.000000 | 1.000000 | 1.000000 | 1.000000 | false | false | lower_when_capable | computed |
| Eox_vertical_P1v | flexibility_rotatable_bonds | Spearman rho | 12 | rho=-0.200198 | 0.532721 | 1.000000 | 0.710295 | false | false | negative | computed |
| Eox_vertical_P1v | functionalization_family | Kruskal-Wallis H | 12 | H=10.192308 | 0.177935 | 0.533805 | 0.355870 | false | false | n/a_multi_level | computed |
| Eox_adiabatic_P1a | donor_type | Kruskal-Wallis H | 11 | H=7.931818 | 0.243141 | 0.729424 | 0.332545 | false | false | n/a_multi_level | computed |
| Eox_adiabatic_P1a | chelation_capable | Mann-Whitney U | 11 | U=8.000000 | 0.906186 | 0.906186 | 0.906186 | false | false | lower_when_capable | computed |
| Eox_adiabatic_P1a | flexibility_rotatable_bonds | Spearman rho | 11 | rho=-0.522233 | 0.099366 | 0.397463 | 0.332545 | false | false | negative | computed |
| Eox_adiabatic_P1a | functionalization_family | Kruskal-Wallis H | 11 | H=9.045455 | 0.249409 | 0.729424 | 0.332545 | false | false | n/a_multi_level | computed |
| Eox_vertical_wB97X_SMD | donor_type | Kruskal-Wallis H | 12 | H=9.823077 | 0.132303 | 0.529212 | 0.396433 | false | false | n/a_multi_level | computed |
| Eox_vertical_wB97X_SMD | chelation_capable | Mann-Whitney U | 12 | U=10.000000 | 1.000000 | 1.000000 | 1.000000 | false | false | higher_when_capable | computed |
| Eox_vertical_wB97X_SMD | flexibility_rotatable_bonds | Spearman rho | 12 | rho=-0.008342 | 0.979474 | 1.000000 | 1.000000 | false | false | negative | computed |
| Eox_vertical_wB97X_SMD | functionalization_family | Kruskal-Wallis H | 12 | H=9.833333 | 0.198217 | 0.594650 | 0.396433 | false | false | n/a_multi_level | computed |
| all_targets | cheap_esp | not_run |  |  | — | — | — | — | — | — | not_available |
| all_targets | tpsa | not_run |  |  | — | — | — | — | — | — | not_available |

检验族规模：每个 target 4 个描述符检验；三个 target 合计 12 个已算检验，另有 2 行显式登记为 not_available。

## 5. 多重比较处理

- **主用 Holm step-down**：在任意检验间依赖下仍控制族错误率（FWER）。选它的理由：（a）本仓库既有结论（Week22/B3）已沿用 Bonferroni/Holm 口径；（b）描述符之间不独立（上述共线），Holm 不要求独立假设；（c）n=12 极小，宁可保守也不轻易宣称某个廉价描述符「解释」了氧化排序。
- **并列 BH step-up**：控 FDR、更宽松，只作敏感性对照同时给出；因其依赖独立/PRDS 假设，在这些共线描述符上不单独作为判据。
- 校正族 = 同一 target 下的全部描述符检验（跨 target 不合并校正），因为三个 target 是同一批描述符对不同口径氧化量的重复提问，合并会二次惩罚。

## 6. 没能覆盖的部分（如实说）

- **廉价 ESP 未做**：允许来源（free_states / pair_evidence / definition / physics_completion_set）里没有分子静电势标量，记 `not_available`，不拿别的量冒充。
- **TPSA 未做**：同上，且方案本身只把 TPSA 定为探索性。
- **n=12 且族内成员极少**：多数化学族只有 1–3 个成员，Kruskal-Wallis 的组内方差很小，功效极低；即使 p 大也不能证明「无关联」，只能说明本集合无检出。
- **donor_type / chelation 是派生代理**：来自 family 与 donor_count 的映射，不是新测的几何/电子量；`chelation_capable` 只是多给体计数，不证明 DOL 等环约束分子真的螯合。
- **不构成机制证明**：这是单变量探索性筛选，不做多参数回归，也不认证任何翻转的成因；机制结论仍以 §7.3 的案例页为准。
- **target 是竖直/电子能层**：P1v/P1a 为 r2SCAN-3c 气相电子能，wB97X 行为 SMD 单点；均非生产 G_ensemble 目标，本分析只针对「氧化排序量」的廉价层。

## 7. 自检

- [x] `cohort_is_12`：cohort=main 分子数 = 12
- [x] `no_multiparameter_model`：只做单变量检验，无多参数回归
- [x] `all_tests_reported`：computed=12 not_available=2 全部进表
- [x] `missing_targets_left_empty`：缺 target 的分子在逐分子矩阵里记 not_available，未补数值
- [x] `no_fabricated_public_descriptor`：cheap_esp / tpsa 记 not_available
- [x] `deterministic`：无时间戳/随机数；排序稳定

