# Week 9 成果小结 —— Stage 10（五级台阶合成与决策稳定性总判）

Week 4-8 各自回答了自己的问题，但每一周用了不同的分子子集和自己的口径，跨周的 tau_b 因此
不能直接比较。本周把五个台阶放到**同一口径**（`p_red = -EA`，两轴都 `higher_is_better`）与
**同一批分子**（common-10：在每一级都有完整值的 10 个分子）上重算，然后回答本项目的中心命题：

> 决定排序是否被改写的，是这一级位移的**离散度**（std），不是它的**大小**（|mean|）。

本文可独立阅读；逐项细节、物理机制与需裁决项见同目录 `week9_report_full.md`。

## 1. 本周做了什么
把 Week 4-8 的**五级台阶**放到**同一口径**（`p_red = -EA`，两个轴都 `higher_is_better = True`）与**同一分子子集**上重算：电子结构方法（P0 -> P1）、环境（P1 -> P2）、几何（G1 -> G2）、配位条件态（C0 -> C1）与第二溶剂壳（C1 -> C2）。共同子集为 **10 个分子**（AN、DMC、DME、DMSO、DOL、EC、GBL、SL、SN、TMP），它们在**每一级都有完整值**；第 4/5 级取 primary m1 motif 作为分子级代表，以免给 DMC / TMP 的第二个配位模式双倍权重。**本阶段不跑新的电子结构计算**，只重读已冻结的 week-4/5/8 产物。

## 2. 关键数字
- 中心命题：离散度决定排序是否被改写。Spearman rho(shift std, tau_b) = **-0.851**；rho(abs(shift mean), tau_b) = -0.535（对照）；rho(shift std, f_unresolved) = **0.894**
- 最锋利的对照：P0 -> P1 还原轴位移最大（+7.064 eV，std 2.253）却保住了排序（tau_b 0.600）；C0 -> C1 还原轴位移相仿（-6.578 eV，std 0.832）却**换号**（tau_b -0.467）——差别在离散度
- 20 个 (台阶, 轴) 组合中 `f_robust_inv` 恒为 0.000（z = 1.96 也全为 0），但 `f_unresolved` 最高达 0.800：这个 0 是「不可判定」而非「稳定」
- v2 §23 最小成果判据：11 条中 10 条 PASS，唯一 PARTIAL 是溶液锚点（Gate 1 blocker）

## 3. 共同子集（N = 10）上的五级台阶
| 台阶 | 轴 | n | 位移均值 (eV) | 位移 std (eV) | tau_b | O_10% | O_20% | f_unresolved (after) | f_robust_inv | sigma_median (eV) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P0 -> P1 (方法) | 氧化 | 10 | -1.299 | 0.786 | 0.733 | 0.000 | 0.000 | 0.133 | 0.000 | 0.271 |
| P0 -> P1 (方法) | 还原 | 10 | +7.064 | 2.253 | 0.600 | 0.000 | 1.000 | 0.733 | 0.000 | 1.422 |
| P1 -> P2 (环境) | 氧化 | 10 | -2.465 | 0.269 | 0.911 | 1.000 | 1.000 | 0.111 | 0.000 | 0.211 |
| P1 -> P2 (环境) | 还原 | 10 | -2.172 | 0.286 | 0.778 | 0.000 | 1.000 | 0.200 | 0.000 | 0.213 |
| G1 -> G2 (几何) | 氧化 | 10 | -0.012 | 0.051 | 0.956 | 1.000 | 1.000 | 0.022 | 0.000 | 0.043 |
| G1 -> G2 (几何) | 还原 | 10 | -0.125 | 0.086 | 0.867 | 1.000 | 1.000 | 0.067 | 0.000 | 0.053 |
| C0 -> C1 (配位) | 氧化 | 10 | +4.887 | 0.595 | 0.689 | 1.000 | 1.000 | 0.200 | 0.000 | 0.420 |
| C0 -> C1 (配位) | 还原 | 10 | -6.578 | 0.832 | -0.467 | 0.000 | 0.000 | 0.800 | 0.000 | 0.633 |
| C1 -> C2 (壳层) | 氧化 | 10 | -1.700 | 0.259 | 0.867 | 1.000 | 1.000 | 0.089 | 0.000 | 0.192 |
| C1 -> C2 (壳层) | 还原 | 10 | +1.199 | 0.335 | 0.289 | 0.000 | 0.000 | 0.356 | 0.000 | 0.176 |


## 4. v2 第 22 节：情形 A-G 判定
| 情形 | 判定 | 依据 |
| --- | --- | --- |
| A：廉价 proxy 已足够 | **NOT SUPPORTED** | P0 -> P2 氧化轴上 tau_b = 0.673、Top-10% 重叠 0.000、后一层 f_unresolved = 0.229（见 p2_decision_stability.json 的 p0_to_p2） |
| B：位移大但排序稳 | **SUPPORTED** | P1 -> P2 氧化轴位移均值 -2.393 eV、位移 std 0.302 eV，而 tau_b = 0.895、O_20% = 0.750、f_robust_inv = 0.000 |
| C：结构集中的 robust inversion | **NOT OBSERVED** | 五个台阶、两个轴、两种口径共 20 个 (台阶, 轴) 组合中，f_robust_inv 的取值全部为 0.000；z=1.96 敏感性列同样全为 0.000 |
| D：配位引发 state-identity 改变 | **OBSERVED** | Week 5 state-identity（`outputs/week5/c1_state_identity.json`）：还原态 12 个里 **11 个是 Li_centered_or_mixed_redox**、1 个 molecule_centered_redox；氧化态 12 个里 molecule_centered_redox = 8、no_intact_minimum_found = 4。判定阈值：abs(Mulliken spin on Li) >= 0.5 或 abs(dq(Li)) >= 0.5 e 记为 Li 中心。 |
| E：Δ-learning 优于 direct | **SUPPORTED（6/8）；例外：C/reduction/X0、C/reduction/X0+X1** | LOFO 拆分下、每个 (任务, 轴, 特征档) 上取模型阶梯最优的 kendall_tau_b（预测排序对真值的保真度）：C/oxidation/X0 direct 0.111 (krr) -> shift 0.644 (krr), +0.533；C/oxidation/X0+X1 direct 0.244 (ridge) -> shift 0.644 (rf), +0.400；C/reduction/X0 direct 0.422 (gbdt) -> shift 0.022 (krr), -0.400；C/reduction/X0+X1 direct…… |
| F：Δ 无法从廉价特征学出 | **NOT SUPPORTED（Δ 在 6/8 个分组上可从廉价特征学出）；例外：C/reduction/X0、C/reduction/X0+X1（与情形 D 同一根还原轴）** | LOFO 拆分下、每个 (任务, 轴, 特征档) 上取模型阶梯最优的 kendall_tau_b（预测排序对真值的保真度）：C/oxidation/X0 direct 0.111 (krr) -> shift 0.644 (krr), +0.533；C/oxidation/X0+X1 direct 0.244 (ridge) -> shift 0.644 (rf), +0.400；C/reduction/X0 direct 0.422 (gbdt) -> shift 0.022 (krr), -0.400；C/reduction/X0+X1 direct…… |
| G：大部分 pair 不可判定 | **PARTIALLY SUPPORTED (还原轴 C0 -> C1)** | C0 -> C1 还原轴：tau_b = -0.467，f_unresolved(after) = 0.800，O_10% = 0.000；同一级的氧化轴作对照：tau_b = 0.689、f_unresolved(after) = 0.200；P0 -> P1 还原轴 f_unresolved(after) = 0.733 |


## 5. 质量与复核（QC）
- 20 行（native + common10 各 10 行）× 25 列，由 `analyze_stage10_synthesis.py` 从 5 个已冻结源文件现场重算；A-G 情形判定 + § 23 判据对照均由同一脚本产出；判据 5 = PARTIAL，判据 7 = PASS (negative)。
- 上述每一项都由本目录 `verification.json` 的 `checks` 数组从真实产物现场解析得出。

## 6. 产物清单
- `artifacts/F19_stage10_ladder.png`
- `artifacts/figure_manifest_week9_stage10.md`
- `stage10_ladder.csv`
- `stage10_ladder.json`
- `stage10_summary.md`
- `stage10_verdicts.json`
- `week9_report_full.md`

## 7. 已知限制
1. common-10 是小样本（n = 10 个台阶事件），秩相关只能读方向与量级，不能读显著性；Top-k 的 k 随 N 变化，跳台阶比较只看趋势。C0 -> C1 还原轴的位移测的是「Li 中心还原」（11/12 个还原态的电子落在 Li 上），与其他台阶不是同一物理过程，其 tau_b 不得用于「方法可迁移性」论证。
2. 本项目所有秩相关都在 n <= 20 个台阶事件上计算，只能读方向与量级，不能读显著性。
3. Gate 0 保持 CLOSED；Gate 1 仍未关闭（溶液相锚点 31 行仍为 `est`）。
4. Stage 10 是**探索性合成分析**（重读已冻结产物，不跑新电子结构）；若要把 Spearman 汇总
   提升为必报指标，须走 `config/prereg.yaml` 的 `amendment_log`，届时 Gate 0 由 CLOSED 变为
   NOT CLOSED。
5. 逐项细节见同目录 `week9_report_full.md`。

## 8. 源文件缺失
- 无（全部源路径均存在）
