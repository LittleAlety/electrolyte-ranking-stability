# T3 —— bare CPCM 介电常数扫描：sigma_env 曲线与 robust inversion 检查

唯一变量：连续介质的**介电常数**。环境为 **bare CPCM**（只有 `epsilon`，不混入 SMD 的
非静电项）；电子结构方法固定 `r2SCAN-3c`，几何固定 **G1**（复用 T1，未重新优化），
全部为**垂直量**。气相参考就是 P1 表本身（`outputs/week4/p1_core_set.csv`），不重算。

## 1. 子集与家族覆盖

分子清单按名字指定，`mol_id` 由 `data/metadata/core_set.csv` 解析（脚本内不硬编码 mol_id）：

| mol_id | 分子 | 家族 | 角色 |
| --- | --- | --- | --- |
| C04 | EC | cyclic_carbonate | solvent |
| C05 | PC | cyclic_carbonate | co-solvent |
| C01 | DMC | linear_carbonate | solvent |
| C02 | EMC | linear_carbonate | solvent |
| C08 | DME | ether | solvent |
| C09 | DOL | ether | co-solvent |
| C13 | GBL | ester | co-solvent |
| C16 | AN | nitrile | co-solvent |
| C18 | SN | nitrile | additive |
| C15 | DMSO | sulfoxide | co-solvent |
| C14 | SL | sulfone | co-solvent |
| C17 | TMP | phosphate | additive |

覆盖家族 **8/8**：cyclic_carbonate, ester, ether, linear_carbonate, nitrile, phosphate, sulfone, sulfoxide。
core set 的全部家族都已覆盖。

## 2. 位移随介电常数的饱和行为

`dIP = IP(CPCM eps) - IP(gas P1)`，`dEA = EA(CPCM eps) - EA(gas P1)`，单位 eV。

| eps | n | dIP 均值 | dIP std | dIP 范围 | dEA 均值 | dEA std | dEA 范围 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 5 | 12 | -1.873 | 0.191 | -2.223 .. -1.425 | +1.907 | 0.197 | +1.628 .. +2.243 |
| 10 | 12 | -2.112 | 0.213 | -2.499 .. -1.630 | +2.188 | 0.233 | +1.867 .. +2.543 |
| 20 | 12 | -2.232 | 0.224 | -2.636 .. -1.732 | +2.307 | 0.229 | +1.991 .. +2.695 |
| 40 | 12 | -2.292 | 0.229 | -2.705 .. -1.783 | +2.376 | 0.234 | +2.054 .. +2.772 |

## 3. sigma_env(eps)

定义（原样写进 summary JSON 的 `definitions` 字段）：

> sigma_env_ev(eps) = population standard deviation (statistics.pstdev) across the N molecules of the oxidation (vertical IP) vertical shift from the gas-phase P1 layer to bare CPCM(eps); a pure common translation would give 0.0 eV, so it measures the molecule-dependent (family-dependent) part of the dielectric screening.

> sigma_env_ea_ev(eps) = population standard deviation (statistics.pstdev) across the N molecules of the reduction (vertical EA) vertical shift from the gas-phase P1 layer to bare CPCM(eps); a pure common translation would give 0.0 eV, so it measures the molecule-dependent (family-dependent) part of the dielectric screening.

| eps | sigma_env(dIP) (eV) | sigma_env(dEA) (eV) | σ_ij 中位数（取两轴较大者，eV） |
| --- | --- | --- | --- |
| 5 | 0.191 | 0.197 | 0.149 |
| 10 | 0.213 | 0.233 | 0.188 |
| 20 | 0.224 | 0.229 | 0.184 |
| 40 | 0.229 | 0.234 | 0.191 |

### 3.1 多来源合成 sigma

`docs/10` §2.4 的 `sigma_ij` 来自两臂（P0、P1）的离散度；按 `docs/08` §5 的要求，
这里把**气相 P1 + 四个 bare CPCM 层 = 5 个 realization** 一次性交给
`uncertainty.quantify_method_sigma(ddof=1, stat="std")` 得到合成 sigma，
再用 `ranking.resolved_mask(z = 1.0)` 重新数一遍 unresolved / robust inversion。

| 轴 | 合成 σ_ij 中位数 (eV) | eps | f_unresolved(CPCM) | f_robust_inv | n_pairs_total | n_pairs_resolved_in_both | n_robust_inversions | f_robust_inv (z=1.96) | n_robust_inversions (z=1.96) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 氧化 | 0.090 | 5 | 0.061 | 0.017 | 66 | 60 | 1 | 0.000 | 0 |
| 氧化 | 0.090 | 10 | 0.106 | 0.018 | 66 | 57 | 1 | 0.000 | 0 |
| 氧化 | 0.090 | 20 | 0.121 | 0.018 | 66 | 56 | 1 | 0.000 | 0 |
| 氧化 | 0.090 | 40 | 0.121 | 0.018 | 66 | 56 | 1 | 0.000 | 0 |
| 还原 | 0.121 | 5 | 0.121 | 0.000 | 66 | 54 | 0 | 0.000 | 0 |
| 还原 | 0.121 | 10 | 0.167 | 0.020 | 66 | 51 | 1 | 0.000 | 0 |
| 还原 | 0.121 | 20 | 0.167 | 0.000 | 66 | 51 | 0 | 0.000 | 0 |
| 还原 | 0.121 | 40 | 0.167 | 0.000 | 66 | 51 | 0 | 0.000 | 0 |

## 4. 决策指标（每个 eps 对气相 P1）

`p_ox = IP`、`p_red = -EA`（越大越好）。主判据 `z = 1.0`（`config/prereg.yaml` 冻结），`z = 1.96` 作保守敏感性并列。

| eps | 轴 | tau_b [95% CI] | rho | O_k(10%) | O_k(20%) | O_k(30%) | J_k(20%) | regret(20%) eV | f_unresolved(CPCM) | f_robust_inv | f_unresolved z=1.96 | f_robust_inv z=1.96 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 5 | 氧化 | 0.939 [0.73, 1.00] | 0.979 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 0.106 | 0.000 | 0.197 | 0.000 |
| 5 | 还原 | 0.848 [0.53, 1.00] | 0.937 | 1.000 | 1.000 | 0.750 | 1.000 | 0.000 | 0.182 | 0.000 | 0.303 | 0.000 |
| 10 | 氧化 | 0.909 [0.70, 1.00] | 0.972 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 0.136 | 0.000 | 0.197 | 0.000 |
| 10 | 还原 | 0.848 [0.53, 1.00] | 0.923 | 1.000 | 1.000 | 0.750 | 1.000 | 0.000 | 0.258 | 0.000 | 0.394 | 0.000 |
| 20 | 氧化 | 0.879 [0.59, 1.00] | 0.944 | 1.000 | 1.000 | 0.750 | 1.000 | 0.000 | 0.152 | 0.000 | 0.212 | 0.000 |
| 20 | 还原 | 0.848 [0.53, 1.00] | 0.937 | 1.000 | 1.000 | 0.750 | 1.000 | 0.000 | 0.212 | 0.000 | 0.364 | 0.000 |
| 40 | 氧化 | 0.879 [0.59, 1.00] | 0.944 | 1.000 | 1.000 | 0.750 | 1.000 | 0.000 | 0.152 | 0.000 | 0.212 | 0.000 |
| 40 | 还原 | 0.848 [0.53, 1.00] | 0.937 | 1.000 | 1.000 | 0.750 | 1.000 | 0.000 | 0.227 | 0.000 | 0.348 | 0.000 |

## 5. 结论

**「有没有 robust inversion」不是一个数就能回答的问题：它依赖于 sigma 口径。**
下面两种口径都给出，且都必须给出。

**口径 1 —— 两臂 sigma**（气相 P1 + 单个 bare CPCM 层；与 `docs/10` §2.4 同口径，即 §4 表）：

- eps = 5, 10, 20, 40 下主判据 `f_robust_inv` 全为 **0**（最大值 0.000），放宽到 z = 1.96 仍为 0.000；非零的 eps 集合为 空集（即无）。
- 即**没有任何一对分子**是「气相与 CPCM 都认为自己分得清、结论却相反」：**这条口径下纯介电 screening 没有产生稳健重排。**

**口径 2 —— 合成 sigma**（气相 P1 + 四个 bare CPCM 层 = 5 个 realization 池化；§3.1 表）：

- 出现**极少量**稳健重排：`f_robust_inv` 最大 **0.020**（z = 1.0）/ 0.000（z = 1.96），对应绝对计数最多 **1 对**（z = 1.0）与 **0 对**（z = 1.96）。注意 `f_robust_inv` 的分母是**两臂都能分辨**的 pair 数（本数据为 51–60 对），而不是子集的 C(12,2) = 66 对，二者不可混读。
- 机理：池化多个 realization 会把 sigma_ij **压小**，于是少量原本「分不清」的 pair 跨过分辨率门槛、被计入稳健重排；1 对这个绝对计数太小，**不足以宣称存在稳健的介电诱导重排**。

**总括**：两臂口径下 `f_robust_inv = 0`，合成口径下最多 1 对（`f_robust_inv` 约 2.0%）。结论**依赖于 sigma 口径**，因此任何「有没有 robust inversion」的对外表述**都必须同时给出所用口径**，不能只报一个数。
- 位移**以共同平移为主**：eps = 40 时 |平均 dIP| = 2.29 eV 是其分子间离散度 sigma_env = 0.23 eV 的 10.0 倍，因此介电 screening 主要把整条轴平移，剩余的是较小的家族依赖修正。
- 排序保持性：四个 eps 下 tau_b 的范围为 0.848 .. 0.939（氧化/还原合并），介电常数只改变 screening 强度，不引入新的化学。
- `f_unresolved` 随 eps 的走向见 §4：它度量的是「在某个 eps 下多少分子对间距低于 z·sigma_ij」，与 `f_robust_inv` 是互补的两件事。

## 6. 限制（不得在对外表述中省略）

- bare CPCM 只有介电常数，**没有** SMD 的非静电项（ cavity/dispersion/repulsion），
  因此 §2 的位移与 `docs/10` §2.7 的 SMD 位移不是同一个物理量，只能各自解读。
- 全部为**垂直量**（G1 几何不弛豫），不含重组能与热校正，不能直接换算电极电位。
- 还原侧的 EA 仍受 `r2SCAN-3c`（def2-mTZVPP 无弥散函数）限制，见 T5 对照臂
  （`outputs/figures/F9_diffuse_function_control.png`）；介电扫描只改变环境，
  **不能**修复基组缺弥散带来的伪不束缚阴离子。
- 子集只含 12 个分子、C(n,2)=66 个 pair，tau_b 的 95% 区间很宽，
  排序类结论只作方向性证据。
- 作业耗时是在一台同时运行其它程序的 16 核机器上实测的，不是基准测试。
