# Week 5 —— T4：Li+ 配位条件态 C1（机制解释）

> 对应 v2 §7.1（条件态层次 C0 -> C1）与 v2 §9（sigma 分源报告）；协议见
> `docs/08_stage2_production_protocol.md` §3.4/§5/§7。本报告只报告数据，不改协议。
> 冻结规则：`config/scientific_definitions.yaml` 的
> `conformers_and_states.li_motif_generation`（8 步）与 `reference_ligand`
> （`dGdG_bind(M;R) = G([LiM]+) + G(R) - G([LiR]+) - G(M)`）。

---

## 1. 本周目标与「唯一变量」约束

`docs/08` §6 把条件态层次定为 **C0（自由分子）-> C1（Li+ 配位）**，并规定
**C1 只做机制解释**，除非其 feature 在 query 前真实可得（prereg §6 的 X2 规则）。
本周只补 C1 这一层，电子结构臂、泛函、几何协议一律不动：

| 量 | 定义 | 几何 | 环境 |
| --- | --- | --- | --- |
| C0（已在上游完成） | r2SCAN-3c 垂直 IP / EA | **G2**（自由分子自身最优几何，T2） | gas |
| **C1（本周）** | r2SCAN-3c 垂直 IP / EA | **G2_Li**（`[Li M]+` 自身最优几何） | gas（另加 SMD 副本） |

因此 C0 -> C1 的**唯一变量是化学状态**：自由分子 vs 与 Li+ 配位的同一个分子。
配位态的三个电子态是 `[Li M]+`（charge +1, singlet）、`[Li M]2+`（charge +2,
doublet）、`[Li M]0`（charge 0, doublet），于是

- `IP(C1) = E([Li M]2+) - E([Li M]+)`，`EA(C1) = E([Li M]+) - E([Li M]0)`；

与 C0 侧的 `IP = E(M+) - E(M)`、`EA = E(M) - E(M-)` 逐字同构（符号约定见
`docs/10` §2.1 与 `scripts/analyze_p1_core_set.py`）。
`docs/08` §4 的层级规则（同一统计内不得混用「电子能量近似」与「热校正」）在本周同样执行：
C0 与 C1 都是**电子能量层**（`dG ~ dE_SCF`，无 ZPE/热校正），不混层。

参考配体为冻结的 **R = DME（C08，双齿 2×O）**，robustness 检查用
**R = AN（C16，单齿 N）**；按冻结要求报告的是**配体交换量** `dGdG_bind`，
不是裸绝对结合能（`config/scientific_definitions.yaml` 明令后者不得作为核心
mechanistic truth）。

### 1.1 代表分子集（10 个，全部在 T2/T3 审计子集内）

`C1_NAMES = EC, DMC, DME, DOL, GBL, SL, DMSO, AN, SN, TMP`：core set 的 8 个结构
家族各 1 个，外加第二个醚（DOL）与第二个腈（SN），让**齿合度在家族内部**变化，
而不是与家族混淆。DME 同时是冻结主参考配体 R、AN 是次参考配体，所以配体交换那条腿
不需要额外分子。10 个分子的 C0 参考（r2SCAN-3c 在 G2 上的垂直 IP/EA）已由 T2 提供。

---

## 2. 结果

### 2.1 Li+ motif 枚举（冻结规则 8 步，`scripts/build_li_motifs.py`）

运行记录：`outputs/week5/li_motif_generation.json`
（`"command": "scripts/build_li_motifs.py --jobs 4 --energy-window-kj 25"`，
xtb 6.7.1pre，46 个候选 -> **12 个 motif**，10 个分子全部至少 1 个 motif，
能量窗口 25 kJ/mol、每分子上限 2）。

| mol_id | 分子 | 家族 | motif | Li 实际接触给体 | ΔE(xTB) kJ/mol | 初始位点类型 |
| --- | --- | --- | --- | --- | --- | --- |
| C04 | EC | cyclic_carbonate | m1 | O4（单齿） | 0.000 | bidentate |
| C01 | DMC | linear_carbonate | m1 | O3（单齿） | 0.000 | bidentate |
| C01 | DMC | linear_carbonate | m2 | O1;O4（双齿） | 24.621 | monodentate |
| C08 | DME | ether | m1 | O1;O4（双齿螯合） | 0.000 | esp_min |
| C09 | DOL | ether | m1 | O2;O4（螯合） | 0.000 | monodentate |
| C13 | GBL | ester | m1 | O0（环内酯羰基 O，单齿） | 0.000 | monodentate |
| C14 | SL | sulfone | m1 | O0;O2（双齿） | 0.000 | bidentate |
| C15 | DMSO | sulfoxide | m1 | O3（S=O 氧，单齿） | 0.000 | esp_min |
| C16 | AN | nitrile | m1 | N2（腈氮，单齿） | 0.000 | monodentate |
| C18 | SN | nitrile | m1 | N0;N5（**折叠螯合**，N···N 2.885 Å） | 0.000 | monodentate |
| C17 | TMP | phosphate | m1 | O3（P=O 氧，单齿） | 0.000 | bidentate |
| C17 | TMP | phosphate | m2 | O1;O4;O6（三齿） | 14.743 | monodentate |

> **注意**：「初始位点类型」是候选的**起始放置方式**，不等于最终齿合度；最终齿合度看
> 「Li 实际接触给体」这一列 —— 例如 EC/DMC/SL/TMP 的 m1 由双齿起点出发，弛豫后滑入
> 单齿或保持双齿，这正是冻结规则第 6 步要求的判重键（**Li 实际接触的给体全集**，
> 而非初始位点给体）。

候选与去重统计（`outputs/week5/li_motif_generation.csv`，46 行全部保留，**不静默丢弃**）：

| 项 | 值 |
| --- | --- |
| 候选总数 | 46（monodentate 22 / bidentate 16 / bidentate_long 1 / esp_min 7） |
| 保留 | 12（`kept=True`），对应 `structures/li_motifs/*.xyz` 12 个文件 |
| 丢弃原因 | `duplicate_geometry_of_*` 31、`duplicate_connectivity_of_*` 1、`parent_bonds_broken` 1、`no_donor_contact` 1 |
| QC 旗标 | `motif_switch` 32、`no_intact_minimum_found` 1、`dissociated_optimized_product` 1 |
| donor 规则核对 | `donor_rule_check = elements_match`，10/10 分子与 `data/metadata/core_set.csv` 的 `donor_atoms` 一致 |

四条可直接读出的机制结论（**齿合度一律以 Li 实际接触的给体全集为准**，不是初始位点类型）：

1. **单齿 m1 的给体都是「只剩一个有效孤对方向」的给体**：EC（碳酸酯羰基 O4，Li-O 1.660 Å）、
   DMC m1（羰基 O3，1.657 Å）、GBL（环内酯羰基 O0，1.668 Å）、DMSO（亚砜 S=O 的 O3，1.631 Å）、
   TMP m1（磷酸 P=O 的 O3，1.604 Å）、AN（腈 N2，1.860 Å）。这类给体（sp2 羰基/亚砜/磷酸氧、
   线性腈氮）周围只有一个有效孤对方向，第二个给体在真实几何里够不着。直接证据：EC、DMC、TMP
   的 m1 **起点**本来是双齿位点（EC c06、DMC c06、TMP c08 起点均为 `bidentate`），
   xTB 预优化后都只保留**一个**接触给体 —— 这正是冻结规则第 6 步要求按「实际接触给体」
   而不是「初始位点」判重的原因。
2. **真正形成螯合的只有三类**（都是两个给体能同时指向 Li+ 的几何）：
   (a) **两个醚氧**：DME（O1;O4，Li-O 1.798 / 1.797 Å，O···O 2.645 Å）、
   DOL（O2;O4，1.978 / 1.970 Å，O···O 2.166 Å）；
   (b) **同一个硫上的两个 S=O 氧**：SL（O0;O2，1.889 / 1.889 Å，O···O 2.333 Å）；
   (c) **折叠腈**：SN（N0;N5，2.041 / 2.042 Å，N···N 2.885 Å）。
   ⚠️ 两条容易写错的事实：**SL 的 m1 是双齿，不是单齿**；**DMSO 虽是亚砜，但只有一个 S=O 氧，
   只能单齿**。唯一的例外是 DMC m2：它的两个烷氧氧（O1;O4，1.870 / 1.870 Å，O···O 2.162 Å）
   也形成螯合，但相对能 +24.621 kJ/mol，落在能量窗口内、作为次 motif 保留。
3. **DME 被选为冻结参考配体 R 的依据在本轮得到验证**：DME 的 5 个候选
   （起点 `monodentate` 2 / `esp_min` 2 / `bidentate` 1）**全部收敛到同一个 O1;O4 双齿 motif**，
   即配位模式唯一、没有第二个可竞争的 connectivity。
4. **SN 的折叠螯合是 motif 层的可报告发现**，也直接验证了 `config/scientific_definitions.yaml`
   把 C18 SN 列为 `mechanism_control_molecules`（"双齿 vs 单齿腈，对照 C16 AN"）的设计意图：
   自由分子 G1 几何里两个腈氮相距 **4.318 Å**（= 2 × Li-N 目标距离 2.00 Å 的 1.08 倍），
   几何上已无法让一个 Li+ 同时处于两个氮的化学键长上；冻结规则因此走 `bidentate_long` 分支
   （把候选放在垂心、交给 xTB 预优化裁决）。预优化后分子**折叠**，Li+ 桥在两个氮之间：
   N···N 收缩到 **2.885 Å**（比自由分子收缩 1.43 Å）、Li-N 2.041 / 2.042 Å。
   对照单腈 AN 只能单齿（Li-N 1.860 Å）。

> **参数说明（必须随报告给出）**：motif 能量窗口取 **25 kJ/mol**（实跑命令 `--energy-window-kj 25`，
> 命令行已逐字记在 `li_motif_generation.json`；**脚本默认值已同步为 25**，以免日后默认重跑静默变成 11 个 motif）。
> 这个取值决定了 DMC m2（ΔE = 24.621 kJ/mol）能否进入 DFT，也就是「12 个 motif」
> 这个数字的直接成因。每分子 motif 上限 2；ESP 补充位点最多 3 个。
### 2.2 C1 扫描与 QC（92 个作业）

运行记录：`outputs/week5/c1_li_coordination_summary.json`（ORCA 6.1.1，`! r2SCAN-3c`，SMD 溶剂 = `acetonitrile`）。几何 G2_Li 由 `[Li M]+` 自身重优化得到，随后**冻结几何做垂直单点**；C0 -> C1 的唯一变量是化学状态。

| 作业类型 | 数目 |
| --- | --- |
| `opt+freq` @ gas | 0 |
| `opt+freq` @ smd | 0 |
| `opt` @ gas | 32 |
| `opt` @ smd | 0 |
| `sp` @ gas | 24 |
| `sp` @ smd | 36 |

| 作业状态 | 数目 |
| --- | --- |
| `execution_failed` | 1 |
| `ok` | 91 |

| QC 旗标 | 数目 |
| --- | --- |
| `dissociated_optimized_product` | 0 |
| `electron_count_mismatch` | 0 |
| `geometry_failed` | 1 |
| `imaginary_mode_unresolved` | 0 |
| `motif_switch` | 0 |
| `no_intact_minimum_found` | 4 |
| `scf_failed` | 0 |
| `spin_contamination_flag` | 0 |
| `state_identity_ambiguous` | 0（结构性零，见下） |
| `unbound_anion` | 0 |

**关于 `state_identity_ambiguous` = 0（§2.2 的 QC 表）**：C1 runner 只**计数**这个已冻结的旗标，没有任何代码路径会给某个作业**赋值**它（它是给「一次运行被迫同时改变两件事」准备的通用旗标，见 `docs/08` §1「三层臂（arms）与唯一变量」），所以这一行的 0 是**结构性零**，本身不构成对态同一性（state identity）的复核。态的**分类**由新增的 `scripts/analyze_c1_state_identity.py` 独立完成（只读已产出的 ORCA 密度，不跑新计算），见 §2.8；那里的 0 是**对 24 行逐个显式求值后**的结果。

单作业墙钟：中位 **37.7 s**、最长 **1944.7 s**、全部作业之和 **4.9 h**（并发 2 作业 x `nprocs 8`，单作业上限 `--timeout 1800 s`）。

**xTB (G1_xtb) 预优化位点 vs r2SCAN-3c (G2_Li) 优化位点的 Li-最近重原子距离**（检验 xTB 预优化是否把 Li 留在真实配位几何附近）：

| 分子 | motif | xTB Li-最近重原子 (A) | r2SCAN-3c Li-最近重原子 (A) | 差 (A) |
| --- | --- | --- | --- | --- |
| EC | m1 | 1.659 | 1.749 | +0.090 |
| DMC | m2 | 1.870 | 1.950 | +0.080 |
| DMC | m1 | 1.657 | 1.744 | +0.087 |
| DME | m1 | 1.797 | 1.872 | +0.075 |
| DOL | m1 | 1.970 | 2.030 | +0.061 |
| GBL | m1 | 1.668 | 1.762 | +0.094 |
| SL | m1 | 1.889 | 2.011 | +0.123 |
| DMSO | m1 | 1.631 | 1.727 | +0.096 |
| AN | m1 | 1.860 | 1.906 | +0.046 |
| SN | m1 | 2.041 | 2.050 | +0.009 |
| TMP | m2 | 2.004 | 1.911 | -0.092 |
| TMP | m1 | 1.604 | 1.722 | +0.118 |

**失败也是结果**：`execution_failed` x1。1 个 redox 态重弛豫（`[Li M]2+` / `[Li M]0` 上的 `Opt`）在 30 min 单作业上限内未收敛（大分子双阳离子/双阴离子重弛豫是主要成本），按「失败也是结果」记为 `geometry_failed`，**不做任何静默补算**。本报告的全部 dIP/dEA 都取自**单点**，不受这些 `Opt` 影响；受影响的只有 §2.7 的弛豫诊断。

### 2.3 逐分子 C1 位移（dIP / dEA，主 motif m1）

C0 = 自由分子在 **G2** 上的垂直 IP/EA（T2：`outputs/week4/t2_opt_freq.csv` 的 `ip_g2_ev` / `ea_g2_ev`）；C1 = 同一分子在 **G2_Li**（`[Li M]+` 自身最优几何）上的垂直量。符号沿用 `docs/10` §2.1：`IP = E(阳离子) - E(中性)`、`EA = E(中性) - E(阴离子)`。

| 分子 | mol_id | 家族 | Li 接触给体 | IP(C0) eV | IP(C1) eV | dIP eV | dIP kJ/mol | EA(C0) eV | EA(C1) eV | dEA eV | dEA kJ/mol |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| EC | C04 | cyclic_carbonate | [4] | +10.781 | +15.102 | +4.321 | +416.9 | -2.446 | +3.709 | +6.155 | +593.9 |
| DMC | C01 | linear_carbonate | [3] | +10.597 | +14.932 | +4.335 | +418.3 | -3.135 | +4.023 | +7.157 | +690.6 |
| DME | C08 | ether | [1, 4] | +8.890 | +14.024 | +5.134 | +495.4 | -3.620 | +3.447 | +7.067 | +681.9 |
| DOL | C09 | ether | [2, 4] | +9.381 | +15.536 | +6.156 | +593.9 | -4.028 | +4.033 | +8.061 | +777.8 |
| GBL | C13 | ester | [0] | +9.990 | +14.891 | +4.901 | +472.9 | -2.460 | +3.718 | +6.178 | +596.1 |
| SL | C14 | sulfone | [0, 2] | +9.735 | +14.664 | +4.929 | +475.6 | -2.862 | +3.358 | +6.220 | +600.2 |
| DMSO | C15 | sulfoxide | [3] | +8.774 | +13.959 | +5.184 | +500.2 | -2.743 | +3.724 | +6.466 | +623.9 |
| AN | C16 | nitrile | [2] | +12.091 | +17.197 | +5.105 | +492.6 | -3.169 | +3.904 | +7.073 | +682.4 |
| SN | C18 | nitrile | [0, 5] | +11.541 | +16.319 | +4.778 | +461.0 | -1.719 | +3.208 | +4.927 | +475.4 |
| TMP | C17 | phosphate | [3] | +9.980 | +14.010 | +4.029 | +388.8 | -2.739 | +3.738 | +6.477 | +624.9 |

- dIP：+4.887 +- 0.564 (n=10, range [+4.029, +6.156]) eV
- dEA：+6.578 +- 0.790 (n=10, range [+4.927, +8.061]) eV

**这两条轴不是同一个物理量**：§2.8 的 state-identity 分类显示，C1 还原态 `[Li M]0` 在 **11/12** 个体系里把外加电子放在了 **Li** 上（`|spin_Li| >= 0.9`），而 C0 的还原轴测的是**分子**得到电子。因此 `dEA(C1)` 在多数体系里是「Li 得到一个电子」的位移，与 C0 的 EA **不可直接并置**；氧化侧则相反——8/12 的空穴落在给体原子上，与 C0 **同类型**（其余 4 个双阳离子弛豫后 Li+ 完全脱离，见 §2.8）。

次 motif（能量窗口内的第二配位模式，只做垂直单点、不做 redox 重弛豫）：

| 分子 | motif | Li 接触给体 | 是否主 motif | IP(C1) eV | dIP eV | EA(C1) eV | dEA eV |
| --- | --- | --- | --- | --- | --- | --- | --- |
| DMC | m2 | [1, 4] | 否 | +15.513 | +4.916 | +3.991 | +7.126 |
| TMP | m2 | [1, 4, 6] | 否 | +14.266 | +4.285 | +3.730 | +6.469 |

---

### 2.4 配体交换 dGdG_bind(M;R)（报交换量，不报裸绝对结合能）

冻结定义逐字取自 `config/scientific_definitions.yaml` 的 `reference_ligand`：

> `dGdG_bind(M;R) = G([LiM]+) + G(R) - G([LiR]+) - G(M)`

主参考配体 R = **DME（C08，双齿 2xO）**，稳健性检查用 R = **AN（C16，单齿 N）**；同一冻结文件明令**裸绝对结合能不得作为核心 mechanistic truth**，故本表只报交换量。自交换（M = R）按定义恒为 0，是这张表的内部一致性检查。

**能量层级**：与本周其它 Δ 一致，`dGdG_bind` 的实现值是 **ΔE_SCF**（不含量子化学热校正、无 ZPE）；写成 G 只是沿用冻结定义的符号。交换表里的 `g_liM_cation_eh` / `g_lir_cation_eh` 两列是 `[LiM]+` / `[LiR]+` 的**原始电子能量**（为可追溯性保留），**不是**结合能，不得被当作冻结文件所禁止的 `dG_bind_abs` 使用。

**R = DME（C08）**

| 分子 | mol_id | 家族 | motif | continuum | dGdG_bind eV | dGdG_bind kJ/mol | 自交换 | status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AN | C16 | nitrile | m1 | gas | +0.855 | +82.5 |  | ok |
| DMC | C01 | linear_carbonate | m1 | gas | +0.888 | +85.7 |  | ok |
| DME | C08 | ether | m1 | gas | +0.000 | +0.0 | 是（= 0） | ok |
| DMSO | C15 | sulfoxide | m1 | gas | +0.263 | +25.3 |  | ok |
| DOL | C09 | ether | m1 | gas | +1.168 | +112.7 |  | ok |
| EC | C04 | cyclic_carbonate | m1 | gas | +0.620 | +59.9 |  | ok |
| GBL | C13 | ester | m1 | gas | +0.571 | +55.1 |  | ok |
| SL | C14 | sulfone | m1 | gas | +0.322 | +31.1 |  | ok |
| SN | C18 | nitrile | m1 | gas | +0.601 | +58.0 |  | ok |
| TMP | C17 | phosphate | m1 | gas | +0.354 | +34.1 |  | ok |
| AN | C16 | nitrile | m1 | smd | +0.583 | +56.3 |  | ok |
| DMC | C01 | linear_carbonate | m1 | smd | +0.588 | +56.7 |  | ok |
| DME | C08 | ether | m1 | smd | +0.000 | +0.0 | 是（= 0） | ok |
| DMSO | C15 | sulfoxide | m1 | smd | +0.211 | +20.3 |  | ok |
| DOL | C09 | ether | m1 | smd | +0.648 | +62.5 |  | ok |
| EC | C04 | cyclic_carbonate | m1 | smd | +0.563 | +54.3 |  | ok |
| GBL | C13 | ester | m1 | smd | +0.509 | +49.1 |  | ok |
| SL | C14 | sulfone | m1 | smd | +0.393 | +38.0 |  | ok |
| SN | C18 | nitrile | m1 | smd | +0.661 | +63.8 |  | ok |
| TMP | C17 | phosphate | m1 | smd | +0.322 | +31.1 |  | ok |

自交换检查（R = DME）：dGdG_bind = +0.000000 kJ/mol，与定义的 0 在数值精度内一致。

**R = AN（C16）**

| 分子 | mol_id | 家族 | motif | continuum | dGdG_bind eV | dGdG_bind kJ/mol | 自交换 | status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AN | C16 | nitrile | m1 | gas | +0.000 | +0.0 | 是（= 0） | ok |
| DMC | C01 | linear_carbonate | m1 | gas | +0.033 | +3.2 |  | ok |
| DME | C08 | ether | m1 | gas | -0.855 | -82.5 |  | ok |
| DMSO | C15 | sulfoxide | m1 | gas | -0.592 | -57.1 |  | ok |
| DOL | C09 | ether | m1 | gas | +0.313 | +30.2 |  | ok |
| EC | C04 | cyclic_carbonate | m1 | gas | -0.235 | -22.6 |  | ok |
| GBL | C13 | ester | m1 | gas | -0.284 | -27.4 |  | ok |
| SL | C14 | sulfone | m1 | gas | -0.532 | -51.4 |  | ok |
| SN | C18 | nitrile | m1 | gas | -0.254 | -24.5 |  | ok |
| TMP | C17 | phosphate | m1 | gas | -0.501 | -48.4 |  | ok |
| AN | C16 | nitrile | m1 | smd | +0.000 | +0.0 | 是（= 0） | ok |
| DMC | C01 | linear_carbonate | m1 | smd | +0.005 | +0.5 |  | ok |
| DME | C08 | ether | m1 | smd | -0.583 | -56.3 |  | ok |
| DMSO | C15 | sulfoxide | m1 | smd | -0.372 | -35.9 |  | ok |
| DOL | C09 | ether | m1 | smd | +0.065 | +6.2 |  | ok |
| EC | C04 | cyclic_carbonate | m1 | smd | -0.020 | -1.9 |  | ok |
| GBL | C13 | ester | m1 | smd | -0.074 | -7.2 |  | ok |
| SL | C14 | sulfone | m1 | smd | -0.190 | -18.3 |  | ok |
| SN | C18 | nitrile | m1 | smd | +0.078 | +7.6 |  | ok |
| TMP | C17 | phosphate | m1 | smd | -0.261 | -25.2 |  | ok |

自交换检查（R = AN）：dGdG_bind = +0.000000 kJ/mol，与定义的 0 在数值精度内一致。

---

### 2.5 决策稳定性：C0 vs C1

同一批分子在 C0（自由分子，`P1 @ G2` 气相近垂直量）与 C1（`[Li M]+` 几何上的垂直量）两种状态下的排序一致性。`tau_b` 为 Kendall tau-b；pair 判定用预注册的 `z = 1.0` 作主判据，并附 `z = 1.96` 的保守敏感性（`docs/11` §4 D3）。`f_unresolved` = 无法区分（`|dP_ij| <= z * sigma_ij`）的 pair 占比；`f_robust_inv` = 在两层都分辨出来的 pair 中，**符号翻转且翻转本身也被分辨**的占比。

| 方向 | n | tau_b | tau_b 95% CI | Spearman rho | f_unresolved(C0) | f_unresolved(C1) | f_robust_inv (z=1.0) | f_robust_inv (z=1.96) | sigma_pair 中位 eV |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 氧化 (IP) | 10 | +0.689 | [+0.139, +1.000] | +0.770 | +0.178 | +0.200 | +0.000 | +0.000 | +0.420 |
| 还原 (EA) | 10 | -0.467 | [-0.950, +0.105] | -0.552 | +0.444 | +0.800 | +0.000 | +0.000 | +0.633 |

Top-k 命中（`k` 为取样比例，`O_k` = top-k 集合重叠率，`J_20%` = k=0.20 的 Jaccard，`selection regret` = 取错 top-k 造成的目标量损失）：

| 方向 | O_10% | O_20% | O_30% | J_20% | selection regret (20%, eV) |
| --- | --- | --- | --- | --- | --- |
| 氧化 (IP) | +1.000 | +1.000 | +0.667 | +1.000 | +0.0000 |
| 还原 (EA) | +0.000 | +0.000 | +0.333 | +0.000 | +0.4573 |

还原轴的低一致性有一条**机制解释**（§2.8 的 state-identity 分类）：C1 的还原态 `[Li M]0` 在 11/12 个体系里是**电子落在 Li 上**，而 C0 的还原轴测的是**分子**得到电子。也就是说 `tau_b = -0.467` 与 `f_unresolved = 0.444/0.800` 有相当一部分来自「两层在测不同的物理量」，而不只是排序噪声。氧化轴没有这个问题：8/12 的氧化态空穴落在给体原子上，与 C0 同类（另外 4 个双阳离子弛豫后 Li+ 完全脱离）。

---

### 2.6 四个单变量台阶的 sigma 对比（同一批 10 个分子上重算）

定义原文（`outputs/week5/c1_summary.json` 的 `four_step_sigma.definition`）：

> population spread (pstdev) of the per-molecule shift caused by ONE single-variable change, all on the same molecules: method = IP(P1@G1) - IP(P0@G1); geometry = IP(P1@G2) - IP(P1@G1); environment = IP(P2 SMD) - IP(P1@G1); coordination = IP(C1) - IP(C0@G2).

| 台阶 | 单变量改动 | dIP 均值 +- std (eV) | dIP n | dEA 均值 +- std (eV) | dEA n |
| --- | --- | --- | --- | --- | --- |
| method | 换方法/基组（P0 -> P1，同一 G1 几何） | -1.299 +- 0.745 | 10 | -8.384 +- 1.155 | 7 |
| geometry | 换几何（G1 -> G2，同一 P1 方法） | -0.012 +- 0.048 | 10 | +0.125 +- 0.082 | 10 |
| environment | 换环境（气相 P1 -> SMD 连续介质） | -2.465 +- 0.256 | 10 | +2.172 +- 0.271 | 10 |
| coordination | 换化学状态（C0 -> C1，Li+ 配位） | +4.887 +- 0.564 | 10 | +6.578 +- 0.790 | 10 |

三条**必须**随表给出的口径限制：

1. **coordination 台阶与其它三个台阶不同基线**：C0 是中性分子 M，C1 的参考态是 `[Li M]+` 阳离子，所以 `dIP_coord = IP([LiM]+ -> [LiM]2+) - IP(M -> M+)` 同时包含「配位场」与「参考态电荷态」两件事，量级比其它三个台阶大约一个数量级，**不可**与 sigma_method / sigma_geom / sigma_env 直接比较，也不构成可加分解。**此外这一步同时改了化学状态与几何**：C0 在自由分子的 G2 上，C1 在复合物自身的 G2_Li 上，配位场与几何弛豫在此未分离，故不能当作纯电子配位场解读。
2. **本表的 environment 台阶不是 `docs/08` §5 的 `sigma_env`**：`sigma_env(eps)` 是 **CPCM 介电常数离散度**（T3 的 bare CPCM 扫描），而这里的 environment 台阶是**SMD(乙腈) 相对气相 P1 的位移离散度**。两者的溶剂模型、参考层和扫描变量都不同，**不可并列**。

3. **method 台阶的两个 P0 代理不是同一物理量**：IP 侧用 Koopmans 轨道能、EA 侧用 xTB 的 ΔSCF 值（`scripts/analyze_c1_coordination.py` 的 method 台阶构造），所以该台阶的 dIP 与 dEA 是两个不同的近似层级，只能分别与同名的其它台阶比较，不能横向混读。

对照（T3，**12 个**分子的 bare CPCM 扫描；与本表 10 个 C1 分子不是同一集合，仅作口径对照）：

| eps | sigma_env(eps), IP 台阶 eV | sigma_env(eps), EA 台阶 eV | dIP 均值 +- std eV | dEA 均值 +- std eV |
| --- | --- | --- | --- | --- |
| 5 | +0.191 | +0.197 | -1.873 +- 0.191 | +1.907 +- 0.197 |
| 10 | +0.213 | +0.233 | -2.112 +- 0.213 | +2.188 +- 0.233 |
| 20 | +0.224 | +0.229 | -2.232 +- 0.224 | +2.307 +- 0.229 |
| 40 | +0.229 | +0.234 | -2.292 +- 0.229 | +2.376 +- 0.234 |

`sigma_env(eps)` 的定义原文（`outputs/week4/t3_cpcm_eps_scan_summary.json` 的 `definitions.sigma_env_ev`）：

> sigma_env_ev(eps) = population standard deviation (statistics.pstdev) across the N molecules of the oxidation (vertical IP) vertical shift from the gas-phase P1 layer to bare CPCM(eps); a pure common translation would give 0.0 eV, so it measures the molecule-dependent (family-dependent) part of the dielectric screening.

---

### 2.7 弛豫诊断：垂直量 vs redox 态重弛豫

对每个分子的主 motif m1，额外做了 `[Li M]2+` 与 `[Li M]0` 的重优化，因此可以对比「垂直量」与「弛豫后量」。这一步**只对 m1 执行**（`docs/08` §7 的预算 cap）：DMC m2 与 TMP m2 的 redox 弛豫位移**未测量**。

| 分子 | dIP 垂直 eV | dIP 弛豫后 eV | 弛豫改变 eV | dEA 垂直 eV | dEA 弛豫后 eV | 弛豫改变 eV |
| --- | --- | --- | --- | --- | --- | --- |
| EC | +4.321 | +3.858 | -0.463 | +6.155 | +6.209 | +0.054 |
| DMC | +4.335 | +3.914 | -0.421 | +7.157 | +7.213 | +0.056 |
| DME | +5.134 | +4.792 | -0.342 | +7.067 | +7.138 | +0.071 |
| DOL | +6.156 | +3.058 | -3.097 | +8.061 | +8.146 | +0.085 |
| GBL | +4.901 | +4.308 | -0.593 | +6.178 | +6.231 | +0.053 |
| SL | +4.929 | n/a | n/a | +6.220 | +6.314 | +0.094 |
| DMSO | +5.184 | +3.647 | -1.537 | +6.466 | +6.532 | +0.066 |
| AN | +5.105 | +2.986 | -2.120 | +7.073 | +7.097 | +0.024 |
| SN | +4.778 | +3.425 | -1.353 | +4.927 | +6.116 | +1.189 |
| TMP | +4.029 | +3.372 | -0.658 | +6.477 | +6.575 | +0.099 |

**机制结论：谁产生 robust inversion？**

- **纯介电 screening（T3）**：The answer depends on the sigma convention. Two-arm sigma (gas P1 + one bare-CPCM layer, the docs/10 section 2.4 convention): max f_robust_inv = 0.0000 at z=1.0 -> no robust inversion at any dielectric. Multi-source sigma (gas P1 + all four dielectrics pooled, docs/08 section 5): at most 1 of the 66 pairs are robust inversions; max f_robust_inv = 0.0196 at z=1.0. Its denominator is the number of pairs BOTH layers resolve (51-60 here), NOT the 66 pairs of the subset, so it must not be read as 1/66 = 0.0152. The absolute count, not the fraction, is the quantity to quote, and any statement about robust inversion must name the convention it uses.
- **Li+ 配位（C1，本报告）**：氧化方向 `f_robust_inv = +0.000`（z=1.0）、`+0.000`（z=1.96）；还原方向 `f_robust_inv = +0.000`（z=1.0）、`+0.000`（z=1.96），样本 10 个分子。
- **因此**：在当前的 sigma 口径与样本下，**介电 screening 与 Li+ 配位都没有产生 robust inversion**；配位带来的 dIP/dEA 位移虽然量级大，但它是**近共模的**（见 §2.3 的 std 与 §2.6 的台阶对比），所以主要改变的是**绝对位置**而不是**排序**。

---

### 2.8 state-identity QC：每个 C1 态的分类（`scripts/analyze_c1_state_identity.py`）

`config/scientific_definitions.yaml` 的 `state_identity_qc` 要求对每个态给出**分类**，而不只是记一个「无异常」的旗标（§2.2 已说明那个 0 是结构性零）。本节是这条要求的实现：判据在读数之前写定（模块 `DEFINITION` 与 docstring）；其中「指标冲突 → `state_identity_ambiguous`」这一支的可达性，是收尾时由测试套件发现并**标签不变地**修正的（见本节末段）。数据来自**已经产出的** ORCA 密度（每个 `.out` 的**最后**一个 `MULLIKEN ATOMIC CHARGES [AND SPIN POPULATIONS]` 块），**不跑任何新 QM 计算**。产物：`outputs/week5/c1_state_identity.{csv,json,md}`；独立对抗式审计：`outputs/week5/c1_state_identity_audit.md`。

判据原文（模块 `DEFINITION`）：

> state_identity_label per (molecule, motif, redox state). Geometry outranks the electrons: a redox state whose optimised geometry lost the Li-M minimum is labelled no_intact_minimum_found, and one whose parent connectivity broke is labelled dissociated_optimized_product. Otherwise the label follows the redox electron: |Mulliken spin on Li| >= 0.5 or |dq(Li)| >= 0.5 eV/e means Li_centered_or_mixed_redox; |spin on Li| <= 0.15 and |dq(Li)| <= 0.25 means molecule_centered_redox; a disagreement between the two indicators (one places the electron on Li while the other places it on the molecule), and any reading that neither indicator resolves, means state_identity_ambiguous. Reference state is [Li M]+ at the same motif.

`reaction_path_verified` **永不指派**：它要求额外的 reaction-path / TS / 动力学证据（`scientific_definitions.yaml` 的 `rule` 原文），本轮没有这类证据，且几何优化导致断键本身**不能**证明该反应在溶液里无势垒。

**判据可达性（收尾时由测试套件发现的真实缺陷，已修正）**：修正前，判 `state_identity_ambiguous` 的那一行写成 `li_side and molecule_side`；由于 Li 侧用的是 0.5 阈值的**或**、分子侧用的是 0.15 / 0.25 的**与**，这一支**永远不可达**——于是「自旋说电子在 Li、电荷说电子在分子」这种真正的指标冲突会被判成 `Li_centered_or_mixed_redox`，那条冻结条文实际上是**死代码**。现在两个指标先各自定性、再合并：一方指向 Li 而另一方指向分子（`|spin_Li| >= 0.5` 且 `|dq_Li| <= 0.25`，或反之）、以及两边都无法分辨的情形，都归入 `state_identity_ambiguous`。**该修正对 24 行是标签不变的**：逐行用新规则重算，标签变化数 = **0**（两个电子指标在 24 行里**全部同向**），所以下面的 8/4 与 11/1 与修正前一致；改变的是这个 0 的性质——从「不可达分支」变成**真正被逐行求值过的 0**（正例：`spin = 0.8, dq = 0.0` 现在返回 `state_identity_ambiguous`，修正前返回 `Li_centered_or_mixed_redox`）。

| 氧化还原方向 | n | 标签 | 计数 |
| --- | --- | --- | --- |
| 氧化 `[Li M]2+` | 12 | `molecule_centered_redox` | 8 |
| 氧化 `[Li M]2+` | 12 | `no_intact_minimum_found` | 4 |
| 还原 `[Li M]0` | 12 | `Li_centered_or_mixed_redox` | 11 |
| 还原 `[Li M]0` | 12 | `molecule_centered_redox` | 1 |
| 任一 | 24 | `state_identity_ambiguous` | **0** |

**主证据与收敛性**：主证据 = 该态**弛豫优化后**的密度；优化不可用（或未产出）时才退回垂直单点。CSV 用三组列把口径显式化：`label_source`（`geometry` = 标签来自几何分支，`electron` = 来自密度）、`primary_output`（实际采用的 ORCA 文件）、`primary_converged` / `reference_converged`（`yes` = 该文件证明了几何收敛，`NO` = ORCA 报「did not converge but reached the maximum number of optimization cycles」，`n/a` = 垂直单点、不涉及几何收敛）。SL 的 `[Li M]2+` 重弛豫即 §2.2 里那个 `geometry_failed`，该行的主证据因此是垂直单点（`primary_converged = n/a`）。

**收敛性是一处必须点名的 QC 缺口（独立审计发现，已显式化）**：4 条双阳离子重弛豫（**AN / DOL / DMSO / SN** 的 `m1_dication_opt`）**没有收敛**，其 `.out` 只写出**第 0 步**的布居块，因此这些行的 `q_Li(态)` / `dq_Li` / `spin_Li` 实际上等于**初始几何**的读数（它们与同几何的垂直单点几乎逐位相同）；`TMP` 的 `m2_cation_opt` 同样未收敛，故 TMP m2 两行的 `q_Li(ref)` 与其余 11 个 motif 的弛豫阳离子参考**口径不同**。这 6 行的**标签全部由几何分支决定**（Li 已离开给体），分类结论不受影响；但 runner 按 ORCA 的**正常终止**记 `status=ok`，因此「几何未收敛」不会被自动降级——本轮不改既有记录、不做静默补算，改以 `primary_converged` / `reference_converged` 把事实挂在明面上（见 §7 限制 14）。

三条机制读数：

- **氧化态**：8/12 的空穴 Mulliken 自旋落在给体原子（O/N/S）上、Li 上 `|spin_Li| <= 0.005`，即被移走的是**分子**的孤对电子——与 C0 氧化轴**同类型**。这也解释了氧化轴为何 `tau_b = +0.689`、`O_20% = 1.000` 却仍不 robust：位移近共模（§2.6）。
- 其中 4 个（**DOL、DMSO、AN、SN**）的**弛豫**双阳离子把 Li+ 完全甩掉（Li 到最近原子（含 H）的距离 6.89–9.05 A；独立审计另算 Li–给体（O/N/S）距离为 7.24–9.05 A，其中 DOL 的 6.89 A 是 Li···H、其 Li–O 为 8.40 A），按「几何优先」记为 `no_intact_minimum_found`：垂直量仍可用，但该态已**不再是条件配合物**。
- **还原态**：11/12 的外加电子 Mulliken 自旋几乎全在 Li 上（`|spin_Li| >= 0.899`），Li 的 Mulliken 电荷相对 `[Li M]+` 下降约 1 e。也就是说 `[Li M]0` 的最优描述是「**电子给了 Li**」，而不是「分子自由基阴离子」。唯一例外是 **SN**（`spin_Li = 0.007`、`dq_Li = -0.128` → `molecule_centered_redox`）：它的电子亲和足以把电子留在分子上。

**结论（必须随还原轴一起引用）**：C1 的还原轴 `dEA(C1)` 在 11/12 个体系里测的是「Li 得到一个电子」，C0 的还原轴测的是「分子得到一个电子」，两者**不是同一个物理量**。这是 §2.5 还原轴 `tau_b = -0.467`、`f_unresolved = 0.444/0.800` 的机制解释，对应执行计划附录 C 的**情形 D**（Li 配位引发 state identity 改变）。任何把该轴与自由分子还原轴并置比较的表述，都必须先做这一步分类。

逐体系证据表（24 行：`q_Li(参考)`、`q_Li(态)`、`dq_Li`、`spin_Li`、Li 到最近原子距离 (A)、主证据收敛、主要自旋载体）见 `outputs/week5/c1_state_identity.md`（§2 证据表、§4 口径与限制）与 `c1_state_identity.csv`；独立对抗式审计见 `outputs/week5/c1_state_identity_audit.md`；图见 §5 的 **F13**。

---

## 3. Gate 状态

| Gate | 状态 | 判据 | 证据 |
| --- | --- | --- | --- |
| Gate 0 定义冻结 | **CLOSED** | 目标量方向、k 值、delta 规则、reference ligand、anchor 搜集规则全部冻结并入库 | `config/prereg.yaml`、`config/scientific_definitions.yaml`（均 `frozen: true`）、`outputs/week1/gate0_record.md` |
| Gate 1 方法审计 | **NOT CLOSED** | state identity 无系统性失败、SCF 稳定、气相锚点趋势正确、溶液趋势方向一致、protocol 已冻结 | 唯一 blocker：`data/anchors/solution_redox_anchors.csv` 31 行 / 16 物种**全部 `method=est`**（`docs/06` §5、`outputs/week2/gate1_record.md`）。ORCA 未安装一条**已解除** |
| Stage 5（T4 / C1） | **交付完成** | motif 枚举 -> C1 优化/单点 -> state-identity QC（§2.8）-> 位移、配体交换、决策稳定性 | 本报告 §2；`outputs/week5/`、`structures/li_motifs/`、`outputs/week5/c1_state_identity.{csv,json,md}`、`tests/test_c1_li_coordination.py` 与 `tests/test_c1_state_identity.py` |

Stage 5 的交付**不解除** Gate 1 的 blocker：Gate 1 卡在「溶液相锚点仍是 est」这一条方法学问题上，与 C1 无关。因此本报告只报**相对量**（位移、交换量、排序一致性），不报任何与实验对齐的绝对电位。

---

## 4. 本周产物

| 产物 | 路径 | 内容 |
| --- | --- | --- |
| motif 枚举记录 | `outputs/week5/li_motif_generation.{csv,json,md}` | 46 条候选（含被丢弃者及其 `dedup_reason`）、12 个 motif、运行参数与命令 |
| motif 几何 | `structures/li_motifs/<NAME>_m<k>.xyz`（12 个） | 每个 motif 的 xTB 预优化几何，Li 为末位原子，注释带 `rel_kj` 与 `from=` 溯源 |
| C1 扫描表 | `outputs/week5/c1_li_coordination.csv` | 一行一个 (motif, state, job, continuum)，含状态、能量、SCF、QC 旗标 |
| C1 运行记录 | `outputs/week5/c1_li_coordination_summary.json` | 作业数、状态计数、QC 计数、耗时、xTB vs DFT 的 Li–给体距离对照、命令行 |
| 每作业原件 | `outputs/week5/c1/<NAME>/` | ORCA `.inp/.out/.gbw`、`*_c1_record.json`、`*_orca.json`、`G2Li.xyz`。**交付包只收录后两类**（进 `c1_records/`）；`.out/.inp/.gbw` 体积大，留在仓库 `outputs/` 内，不进包 |
| 位移表 | `outputs/week5/c1_coord_shifts.csv` | 逐分子/逐 motif 的 C0、C1、SMD、弛豫四套 IP/EA 与 Δ（eV 与 kJ/mol） |
| 配体交换表 | `outputs/week5/c1_ligand_exchange.csv` | `dGdG_bind(M;R)`，R = DME（主）与 AN（次），gas 与 SMD 两列 continuum |
| state-identity 分类 | `outputs/week5/c1_state_identity.{csv,json,md}` | 24 行逐态 `state_identity_label`（冻结词表）与证据列（`q_Li(ref)`、`q_Li(态)`、`dq_Li`、`spin_Li`、Li 最近给体距离、主要自旋载体、`label_source`）；只读已产出的 ORCA 密度重解析，**不跑新计算** |
| 决策稳定性 | `outputs/week5/c1_decision_stability.{json,md}`、`c1_summary.json` | τ_b、O_k、J_k、selection regret、f_unresolved、f_robust_inv 与四台阶 σ |
| state-identity 审计 | `outputs/week5/c1_state_identity_audit.md` | 独立子代理从原始 ORCA 输出重解析的对抗式审计（24/24 标签与 12 个数值列零差异、三者互洽）+ 5 条发现的逐条收尾处置 |
| 图 | `outputs/figures/F12_li_coordination_c1.png`、`outputs/figures/F13_c1_state_identity.png`（含两份 `figure_manifest_*`） | F12 四面板（位移 / 四台阶 σ / 配体交换 / 决策量）；F13 三面板（自旋布居 / 电荷阶梯 / 标签计数），均含 SHA256 |
| 脚本与测试 | `scripts/build_li_motifs.py`、`scripts/run_c1_li_coordination.py`、`scripts/analyze_c1_coordination.py`、`scripts/make_c1_figure.py`、`scripts/analyze_c1_state_identity.py`、`scripts/make_c1_state_identity_figure.py`、`tests/test_c1_li_coordination.py`、`tests/test_c1_state_identity.py` | 可确定性重生成；C1 39 个测试 + state-identity 20 个测试 |
| 内部审计 | `outputs/week5/c1_adversarial_audit.md` | 对抗性科学校验记录（22 条发现：7 条「通过」、15 条 F1–F3；每条真缺陷的收尾处置见该文件末节） |

---

## 5. 图表清单

| 编号 | 图 | 数据来源 | 文件 |
| --- | --- | --- | --- |
| **F12** | Li+ 配位条件态 C1：(a) 逐分子 dIP/dEA；(b) 四个单变量台阶的 σ 对比；(c) 对冻结参考 R = DME 的配体交换；(d) 决策量（τ_b / O_20% / J_20% / 1 − f_robust_inv） | T4 | `outputs/figures/F12_li_coordination_c1.png` |
| **F13** | C1 每态的 state-identity：(a) 氧化/还原态 Li 上的 Mulliken 自旋布居（含 0.15 / 0.5 阈值线）；(b) Li 的三态 Mulliken 电荷阶梯（`[Li M]+` 参照 / 氧化 / 还原）；(c) 冻结标签计数 | T4 | `outputs/figures/F13_c1_state_identity.png` |

图内标签为 ASCII/英文（避免中文字体缺失）；`figure_manifest_week5_c1.md` 与
`figure_manifest_week5_state_identity.md` 分别记录「图 -> 生成脚本 -> 输入数据 -> SHA256」。

---

## 6. 下一步（按优先级）

1. **① 最高**：溶液锚点核验（Gate 1 唯一 blocker，`docs/11` §5）——它决定任何「与实验对齐的绝对电位」表述是否允许。
2. **② 中**：`delta_m` 冻结 + Stage 6 收口（`z` 一致性已收口，见 `docs/11` §4 D3）；本轮的 coordination σ 与 T2/T3 的 σ 是 `delta_m` 的候选展宽来源，但**必须先在同一个分子集上重算**才能并列（见 §2.6）。
3. **③ 中（可选）**：Stage 7–8 ML / 主动学习（依赖 `docs/11` D1 的扩展触发条件）。
4. **可选（原计划 Stage 9 / 状态轴 C2）**：`docs/00` 定义的 C2 = 少量代表体系的显式微溶剂化 cluster，用来检验「C1 的 1:1 配位图像是否对关键 inversion 稳健」。只有在①②完成、且 C1 出现 robust inversion 时才值得投预算。

---

## 7. 已知限制（不得在对外表述中省略）

1. **C1 只覆盖 10 个代表分子**（8 家族各 1 + 第二醚 + 第二腈），不是 core 全部 18 个；结论不外推到全库。
2. **C1 是 1:1 配位图像**：显式溶剂、Li+ 多配位（`[Li(solvent)_n]+`）、阴离子（PF6−/FSI−）参与都不在模型内（Stage 9 的 C2 才是显式微溶剂化）。
3. **coordination 台阶与其它三个台阶不同基线**：C0 是中性分子，C1 的参考态是 `[Li M]+` 阳离子，因此
   `dIP_coord = IP([LiM]+ -> [LiM]2+) − IP(M -> M+)` 同时包含「配位场」与「参考态电荷态」两件事，
   其量级（实测值见 §2.6）**不可**与 σ_method / σ_geom / σ_env 直接比较，也不构成可加分解。
4. **redox 态重弛豫只对 m1 执行**：DMC m2 与 TMP m2 只有垂直单点，其 redox 弛豫位移未测量（冻结规则第 8 步的 cap，见 `docs/08` §7）。
5. **C1 默认不做 `Freq`**：因此 C1 三层状态**没有虚频检查**（与做了 `Freq` 的 T2 不同层级）；`[Li M]+` 的重原子模本身容易出真实虚频，此处记为「未检」而非「无虚频」。
6. **电子能量层**：全部 Δ 为 `dE_SCF` 层级（无 ZPE/热校正）；`dGdG_bind` 的符号是 G，实现值是 ΔE_SCF（`docs/08` §4 允许，但必须标注层级）。
7. **还原侧的量纲陷阱**：C0 的气相垂直 EA 在本方法适用域外（18/18 不束缚，`docs/10` §2.6）；C1 的「EA」是**阳离子**接受一个电子，恒为正，二者不可混为一谈。
8. **不含量子化学方法敏感性**：本周没有换泛函/基组的对照（T5 的弥散对照只覆盖 4 个分子）。
9. **motif 能量窗口 25 kJ/mol 是运行参数，不在预注册冻结清单内**：它决定 DMC m2 是否进入 DFT，也就是「12 个 motif」这个数字的成因（`docs/08` §7 已逐字记录）。

10. **T4 扫描曾被一次环境事故打断并按同一协议续跑**：C1 sweep 在第 69/92 个作业处因本机沙箱配置切换（工作区 `.venv` 的基础解释器被禁止执行）而中断；续跑时跳过已 `status=ok` 的 69 条记录、只补剩余作业，**协议、几何、方法、参数一律未变**，失败作业仍按「失败也是结果」记录。
11. **分析层的运行环境在收尾期间发生过一次非计划变更**：`scripts/analyze_c1_coordination.py`、`scripts/make_c1_figure.py`、`scripts/build_deliverables.py`、`pytest` 由原本的 CPython 3.10.11（工作区 `.venv`）改为同源的可执行 CPython 3.12.14 环境（numpy 2.5.3 / matplotlib 3.11.2 / scipy 1.18.1 / pytest 9.1.1 / PyYAML 6.0.3 / RDKit 2026.3.6）。**量子化学层未受影响**（ORCA 6.1.1、xTB `6.7.1pre` 逐字不变），所有电子结构数值与该环境无关；可能受影响的只有浮点末位与 `pytest` 的 `tmp_path`（沙箱要求把 `TEMP` 指到工作区内运行）。

12. **state-identity 分类是「读数」而不是「动力学证明」**：§2.8 的标签全部来自已产出的密度与几何，`reaction_path_verified` 从未指派；4 个 `no_intact_minimum_found`（DOL/DMSO/AN/SN 双阳离子）说明这些态的**重弛豫产物**已不是条件配合物，但本报告的垂直量仍取自**设计几何**，两者不可混读。还原态 11/12 的 `Li_centered_or_mixed_redox` 也**不等于**「溶液里真的会发生 Li 沉积」——它只说明在当前 1:1、单点图像下外加电子在能量上落在 Li 上。
13. **state-identity 的参考态口径**：`dq_Li` 是相对**同一 motif 的 `[Li M]+`**（不是相对中性 Li 原子）定义的，所以 `dq_Li ≈ -1 e` 应读作「相对阳离子参考多了一个电子」，而不是绝对氧化态。
14. **几何未收敛不会被自动降级为失败**：4 条双阳离子重弛豫（AN / DOL / DMSO / SN 的 `m1_dication_opt`）与 `TMP_m2_cation_opt` 达到 ORCA 的优化步数上限而**未收敛**，其 `.out` 只含第 0 步布居块；runner 按 ORCA 正常终止记 `status=ok`。本轮**不改既有记录、不补算**，改以 `primary_converged` / `reference_converged` 两列显式化（§2.8）。这 6 行的 state-identity 标签由几何分支决定，不受影响；但它们**不能**用来支撑「弛豫后的电子结构」这类表述。
15. **`li_min_distance_a` 是 Li 到任意原子（含 H）的距离**，不是 Li–给体距离：DOL 双阳离子的 6.892 A 来自 Li···H（其 Li–O 为 8.395 A）。`docs/12` §2.8 与 `c1_state_identity.md` §4 已按此口径改写；该列只作「Li 是否还在配位壳内」的粗判据，精确的给体接触以 runner 记录的 `li_contacts` 为准。
