# C1 state-identity QC（每态分类，来自已产出的 ORCA Mulliken 块）

判据原文（本模块 `DEFINITION`）：

> state_identity_label per (molecule, motif, redox state). Geometry outranks the electrons: a redox state whose optimised geometry lost the Li-M minimum is labelled no_intact_minimum_found, and one whose parent connectivity broke is labelled dissociated_optimized_product. Otherwise the label follows the redox electron: |Mulliken spin on Li| >= 0.5 or |dq(Li)| >= 0.5 eV/e means Li_centered_or_mixed_redox; |spin on Li| <= 0.15 and |dq(Li)| <= 0.25 means molecule_centered_redox; a disagreement between the two indicators (one places the electron on Li while the other places it on the molecule), and any reading that neither indicator resolves, means state_identity_ambiguous. Reference state is [Li M]+ at the same motif.

阈值（在读数之前写定，见脚本 docstring）：`|spin_Li| >= 0.5` 或 `|dq_Li| >= 0.5` 判为 Li 中心；`|spin_Li| <= 0.15` 且 `|dq_Li| <= 0.25` 判为分子中心；其余记为 `state_identity_ambiguous`。`reaction_path_verified` 永不指派。

## 1. 逐态分类计数

| 氧化还原方向 | n | 标签 | 计数 |
| --- | --- | --- | --- |
| dication | 12 | `molecule_centered_redox` | 8 |
| dication | 12 | `no_intact_minimum_found` | 4 |
| reduced | 12 | `Li_centered_or_mixed_redox` | 11 |
| reduced | 12 | `molecule_centered_redox` | 1 |

## 2. 逐体系证据（`来源` = 几何分支 / 电子分支；实际采用的 ORCA 文件见 CSV 的 `primary_output`）

| 分子 | family | motif | 态 | 标签 | 来源 | q_Li(ref) | q_Li(态) | dq_Li | spin_Li | Li 到最近原子 (A) | 主证据收敛 | 主要自旋载体 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| EC | cyclic_carbonate | m1 | dication | `molecule_centered_redox` | electron | 0.940 | 0.981 | 0.041 | -0.000 | 2.026 | yes | O5:+0.283;O2:+0.282;H9:+0.110 |
| EC | cyclic_carbonate | m1 | reduced | `Li_centered_or_mixed_redox` | electron | 0.940 | -0.054 | -0.994 | 1.012 | 1.867 | yes | Li10:+1.012;C3:-0.030;C0:+0.012 |
| DMC | linear_carbonate | m2 | dication | `molecule_centered_redox` | electron | 0.928 | 0.964 | 0.036 | -0.001 | n/a | n/a | O3:+0.298;O1:+0.246;O4:+0.246 |
| DMC | linear_carbonate | m2 | reduced | `Li_centered_or_mixed_redox` | electron | 0.928 | -0.087 | -1.016 | 1.019 | n/a | n/a | Li12:+1.019;O4:-0.008;O1:-0.008 |
| DMC | linear_carbonate | m1 | dication | `molecule_centered_redox` | electron | 0.926 | 0.971 | 0.045 | -0.000 | 1.985 | yes | O1:+0.343;O4:+0.336;C2:-0.091 |
| DMC | linear_carbonate | m1 | reduced | `Li_centered_or_mixed_redox` | electron | 0.926 | -0.083 | -1.009 | 1.030 | 1.854 | yes | Li12:+1.030;O3:-0.013;C2:-0.010 |
| DME | ether | m1 | dication | `molecule_centered_redox` | electron | 0.884 | 0.940 | 0.056 | -0.005 | 2.064 | yes | O4:+0.310;O1:+0.309;H11:+0.088 |
| DME | ether | m1 | reduced | `Li_centered_or_mixed_redox` | electron | 0.884 | -0.108 | -0.991 | 1.006 | 1.980 | yes | Li16:+1.006;C0:-0.009;C5:-0.009 |
| DOL | ether | m1 | dication | `no_intact_minimum_found` | geometry | 0.915 | 0.970 | 0.055 | -0.001 | 6.892 | NO | O2:+0.364;O4:+0.363;H5:+0.077 |
| DOL | ether | m1 | reduced | `Li_centered_or_mixed_redox` | electron | 0.915 | -0.085 | -1.000 | 1.014 | 2.227 | yes | Li11:+1.014;C3:-0.023;H9:+0.012 |
| GBL | ester | m1 | dication | `molecule_centered_redox` | electron | 0.930 | 0.977 | 0.047 | -0.000 | 2.005 | yes | O5:+0.370;H10:+0.170;H11:+0.169 |
| GBL | ester | m1 | reduced | `Li_centered_or_mixed_redox` | electron | 0.930 | 0.042 | -0.888 | 0.899 | 1.849 | yes | Li12:+0.899;C1:+0.102;C2:-0.032 |
| SL | sulfone | m1 | dication | `molecule_centered_redox` | electron | 0.883 | 0.932 | 0.049 | 0.001 | 2.333 | n/a | O2:+0.259;O0:+0.258;C6:+0.175 |
| SL | sulfone | m1 | reduced | `Li_centered_or_mixed_redox` | electron | 0.883 | -0.089 | -0.972 | 0.994 | 2.219 | yes | Li15:+0.994;C4:+0.004;C5:+0.004 |
| DMSO | sulfoxide | m1 | dication | `no_intact_minimum_found` | geometry | 0.901 | 0.959 | 0.058 | 0.000 | 7.239 | NO | O3:+0.515;S1:+0.318;C0:+0.060 |
| DMSO | sulfoxide | m1 | reduced | `Li_centered_or_mixed_redox` | electron | 0.901 | 0.005 | -0.896 | 0.913 | 1.828 | yes | Li10:+0.913;S1:+0.108;O3:-0.022 |
| AN | nitrile | m1 | dication | `no_intact_minimum_found` | geometry | 0.949 | 0.988 | 0.039 | 0.001 | 9.046 | NO | N2:+0.654;C0:+0.166;H4:+0.131 |
| AN | nitrile | m1 | reduced | `Li_centered_or_mixed_redox` | electron | 0.949 | -0.082 | -1.031 | 1.039 | 2.020 | yes | Li6:+1.039;C1:-0.053;N2:+0.026 |
| SN | nitrile | m1 | dication | `no_intact_minimum_found` | geometry | 0.943 | 0.981 | 0.039 | 0.000 | 7.339 | NO | N0:+0.345;N5:+0.344;H7:+0.082 |
| SN | nitrile | m1 | reduced | `molecule_centered_redox` | electron | 0.943 | 0.814 | -0.128 | 0.007 | 1.850 | yes | C4:+0.614;N5:+0.147;N0:+0.120 |
| TMP | phosphate | m2 | dication | `molecule_centered_redox` | electron | 0.909 | 0.941 | 0.031 | -0.002 | n/a | n/a | O4:+0.277;O3:+0.272;O6:+0.219 |
| TMP | phosphate | m2 | reduced | `Li_centered_or_mixed_redox` | electron | 0.909 | -0.074 | -0.983 | 0.990 | n/a | n/a | Li17:+0.990;C5:+0.010;O4:-0.005 |
| TMP | phosphate | m1 | dication | `molecule_centered_redox` | electron | 0.908 | 0.957 | 0.050 | -0.000 | 1.869 | yes | O4:+0.289;O6:+0.287;O1:+0.232 |
| TMP | phosphate | m1 | reduced | `Li_centered_or_mixed_redox` | electron | 0.908 | -0.087 | -0.994 | 1.019 | 1.817 | yes | Li17:+1.019;O3:-0.010;P2:-0.004 |

## 3. 机制读数（由本表直接得出）

- **氧化态 `[Li M]2+`**：8/12 个体系的标签是 `molecule_centered_redox`——空穴的 Mulliken 自旋落在给体原子（O/N/S）上，Li 上的自旋 <= 0.01，说明被移走的是**分子**的孤对电子。
  其中 4 个体系（DOL、DMSO、AN、SN）的**弛豫**双阳离子把 Li+ 完全甩掉（Li 到最近原子（含 H）的距离 6.9-9.0 A），按「几何优先」规则记为 `no_intact_minimum_found`：垂直量仍可用，但该态已不再是条件配合物。
- **还原态 `[Li M]0`**：11/12 个体系记为 `Li_centered_or_mixed_redox`——外加电子的 Mulliken 自旋几乎全部落在 Li 上（|spin_Li| >= 0.9），Li 的 Mulliken 电荷相对 `[Li M]+` 下降约 1 e。也就是说 `[Li M]0` 的最优结构是**把电子给了 Li**，而不是形成分子自由基阴离子。
  例外是 SN（`molecule_centered_redox`，|spin_Li| <= 0.007）：该分子的电子亲和足以把电子留在分子上。
- **因此**：C1 的还原轴（`dEA(C1)`）在多数体系里测的是「Li 得到一个电子」，而自由分子 C0 的还原轴测的是「分子得到一个电子」；这两者**不是同一个物理量**，这正是还原轴 `tau_b = -0.467`、`f_unresolved` 高达 0.444/0.800 的机制解释，也对应新计划附录 C 的情形 D（Li 配位引发 state identity 改变）。任何把该轴与自由分子还原轴并置比较的表述都必须先做这一步分类。
## 4. 口径与限制

- `来源`（CSV 列名 `label_source`）只区分**几何分支**与**电子分支**：前者由弛豫几何决定，后者由密度决定。实际采用的 ORCA 输出记在 CSV 的 `primary_output`。
- `primary_converged` / `reference_converged` 说明该输出是否**证明了几何收敛**：`yes` = 有 `THE OPTIMIZATION HAS CONVERGED`；`NO` = ORCA 报「did not converge but reached the maximum number of optimization cycles」；`n/a` = 垂直单点，不涉及几何收敛。
- **4 条记录的主证据来自未收敛的几何优化**（DOL dication、DMSO dication、AN dication、SN dication）。该 `.out` 只写出**第 0 步**的布居块，所以这些行的 `q_Li(态)` / `dq_Li` / `spin_Li` 实际上等于**初始几何**的读数；它们全部由**几何分支**定性（Li 已离开给体，或母体断键），标签不受影响，但**不得**把这些电子读数当作弛豫后的密度解读。
- **2 条记录的 `q_Li(ref)` 来自未收敛的阳离子参考几何**（TMP m2），因此其 `dq_Li` 与其余 motif（弛豫阳离子参考）口径不同；这些行的电子读数位于阈值远侧，标签对参考态口径不敏感。
- `li_min_distance` 是 Li 到**任意原子（含 H）**的距离，**不是** Li-给体距离：审计发现 DOL 双阳离子的 6.892 A 来自 Li...H，其 Li-O 距离为 8.395 A。几何规则的另一条证据是 runner 记录的 `li_contacts`（给体接触列表，为空即超截断）。
- runner 按 ORCA 的**正常终止**记 `status=ok`，所以「几何未收敛」不会自动降级为失败；本表用 `primary_converged` / `reference_converged` 把这一点显式化。

