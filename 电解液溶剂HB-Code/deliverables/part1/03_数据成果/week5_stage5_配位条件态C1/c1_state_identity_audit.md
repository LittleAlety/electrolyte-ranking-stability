# C1 state-identity QC — 独立对抗式审计报告

审计人：独立审计子代理（只读原始数据，未修改任何既有产物）
审计时间：2026-09-29
审计对象：`outputs/week5/c1_state_identity.csv` / `.json` / `.md`（生成脚本 `scripts/analyze_c1_state_identity.py`）
原始证据：`outputs/week5/c1/<NAME>/*.out`（ORCA）+ `<stem>_c1_record.json`
方法：自写解析器（**未 import** `analyze_c1_state_identity.py`），从每个 `.out` 的**最后一个** `MULLIKEN ATOMIC CHARGES [AND SPIN POPULATIONS]` 块独立取 Li 的 Mulliken 电荷与自旋布居，按冻结阈值重算标签，再与 CSV/JSON/MD 逐行比对。
阈值（复算用，与脚本常量一致）：`|spin_Li| >= 0.5` 或 `|dq_Li| >= 0.5` → Li 中心；`|spin_Li| <= 0.15` 且 `|dq_Li| <= 0.25` → 分子中心；Li-给体接触阈值 `3.0 Å`。

---

## 1. 审计结论（一句话）

**标签与计数全部一致（24/24 行逐行复核无差异，dication = 8+4、reduced = 11+1、总 24 行，CSV/JSON/MD 三者互洽）；但发现 5 处“证据来源/字段语义”层面的实质问题——4 个双阳离子行与 TMP-m2 参考行的“弛豫密度”其实是**未弛豫初始几何**的密度（ORCA 未写出最终布居块），另有 1 行 `li_min_distance_a` 被当成“Li-给体距离”实为 Li···H 距离，以及 1 处 `state_identity_ambiguous` 判定逻辑与该模块自身 `DEFINITION` 不符。以上均**不改变任何 `state_identity_label`**。**

---

## 2. 逐项核验结果

### 2.1 独立重解析（item 1）— 全部复现
对 24 个主证据行，我从 `.out` 最后一个 Mulliken 块独立取出的 `q_Li`、`spin_Li`、`spin_total`、`spin_molecule`、`top_spin_carriers`，与 CSV 对应列 **24/24 完全一致**（含 `C :` 与 `Li:` 字段宽度差异、两位元素符号、正负号）。解析器对每个 `.out` 统计到的 Mulliken 块数：

| 文件类别 | Mulliken 块数 | 末块是否在最后一步几何之后 |
| --- | --- | --- |
| 收敛的 `*_opt.out`（EC、DMC-m1、DME、GBL、SL-reduced、TMP-m1、DOL-reduced、DMSO-reduced、AN-reduced、SN-reduced、各 cation_opt） | 2 | 是（正确） |
| 单点 `*_sp.out`（全部） | 1 | 是（唯一几何） |
| **不收敛**的 `AN/DMSO/DOL/SN _m1_dication_opt.out` + `TMP_m2_cation_opt.out` | **1** | **否（见 4.1）** |
| `SL_m1_dication_opt.out`（超时失败） | 1 | 否（文件被截断） |

### 2.2 复算标签（item 2）— 24/24 一致，0 处不一致
按冻结阈值重算的 24 行 `(molecule, motif, state)` 标签与 CSV `state_identity_label` 逐行比对：**差异 0 行**。同时 `q_li_ref`、`q_li_state`、`dq_li`、`spin_li_state`、`spin_total_state`、`spin_molecule_state`、`vertical_label`、`relaxed_label`、`geometry_changes_identity`、`parent_bonds_intact`、`top_spin_carriers`、`primary_output` 列也逐格复算，**0 处不一致**。

关键复算数值（Li 自旋 / dq_Li，单位 e）：

| 态 | 行 | 复算 spin_Li | 复算 dq_Li | 复算标签 |
| --- | --- | --- | --- | --- |
| dication | EC / DMC-m2 / DMC-m1 / DME / GBL / SL / TMP-m2 / TMP-m1 | -0.000148 / -0.001094 / -0.000337 / -0.004571 / -0.000042 / +0.001179 / -0.002426 / -0.000054 | +0.041 / +0.036 / +0.045 / +0.056 / +0.047 / +0.049 / +0.031 / +0.050 | `molecule_centered_redox` |
| dication | DOL / DMSO / AN / SN | -0.000772 / +0.000222 / +0.001349 / +0.000474 | +0.055 / +0.058 / +0.039 / +0.039 | `no_intact_minimum_found`（几何优先） |
| reduced | EC / DMC-m2 / DMC-m1 / DME / DOL / GBL / SL / DMSO / AN / TMP-m2 / TMP-m1 | 1.012 / 1.019 / 1.030 / 1.006 / 1.014 / 0.899 / 0.994 / 0.913 / 1.039 / 0.990 / 1.019 | -0.994 / -1.016 / -1.009 / -0.991 / -1.000 / -0.888 / -0.972 / -0.896 / -1.031 / -0.983 / -0.994 | `Li_centered_or_mixed_redox` |
| reduced | SN | +0.007424 | -0.128169 | `molecule_centered_redox` |

### 2.3 复算计数（item 3）— 一致
| 方向 | 期望 | 我的独立复算 |
| --- | --- | --- |
| dication | 8 `molecule_centered_redox` + 4 `no_intact_minimum_found` | 8 + 4 ✅ |
| reduced | 11 `Li_centered_or_mixed_redox` + 1 `molecule_centered_redox` | 11 + 1 ✅ |
| 总行数 | 24 | 24 ✅ |

### 2.4 兄弟产物一致性（item 4）— 三者互洽
- CSV 24 行标签 ↔ JSON `rows[*].state_identity_label`：完全一致。
- JSON `per_redox_state`：dication `{molecule_centered_redox:8, no_intact_minimum_found:4}`，reduced `{Li_centered_or_mixed_redox:11, molecule_centered_redox:1}`，`n_rows=24`；与 CSV 一致。
- MD「## 1 逐态分类计数」4 行与上述一致；MD「## 2 逐体系证据」24 行**逐行**的 (名称, motif, 态, 标签, 来源) 与 CSV 比对：**0 处不一致**。

### 2.5 主证据来源（item 5）— 判定逻辑成立
**注意：CSV 中并不存在 `relaxed_opt` / `vertical_sp` 这一列**；`label_source` 列的取值是 `geometry` / `electron`（几何优先 vs 电子判据）。「弛豫 vs 垂直」的出处实际由 `primary_output` 列承载。据此核对：

| 行 | primary_output | 应为 | 核实结论 |
| --- | --- | --- | --- |
| DMC m2 dication / reduced | `DMC_m2_*_sp.out` | vertical_sp | ✅ 不存在 `DMC_m2_*_opt.out`，无优化产物 |
| TMP m2 dication / reduced | `TMP_m2_*_sp.out` | vertical_sp | ✅ 不存在 `TMP_m2_*_opt.out` |
| SL m1 dication | `SL_m1_dication_sp.out` | vertical_sp | ✅ `SL_m1_dication_opt.out` 存在但 record `status=execution_failed`（ORCA 1800s 超时被杀），未采用 |
| 其余 19 行 | 各 `*_opt.out` | relaxed_opt | ✅ 对应 record `status=ok`；但其中 4 行密度来源有误，见 4.1 |

`label_source`（geometry/electron）与 `label` 的对应关系在 24 行上逐行成立：4 个 `no_intact_minimum_found` → `geometry`，其余 20 → `electron`。

---

## 3. 反例搜索的真实发现

### 3.1 两个电子指标互相冲突、本该 ambiguous 的行？
**没有。** 对 24 行逐一测试 `|spin_Li|` 与 `|dq_Li|`：不存在「spin 指向 Li 而 dq 指向分子」（或反之）的行，也不存在「两者都不触发」的行。所有行要么两指标同向 Li（11 个还原态），要么同向分子（12 个 + SN 还原态）。
**但有一个逻辑缺口（不影响本次结果）**：`DEFINITION` 与 docstring 明确写「a disagreement between the two indicators means `state_identity_ambiguous`」，而 `electron_label()` 实际实现中 `li_side = spin>=0.5 or dq>=0.5`、`molecule_side = spin<=0.15 and dq<=0.25`，两者**不可能同时为真**，因此「both fire」分支不可达；真正的“两指标矛盾”（例如 spin=0.9 + dq=0.05）会被静默判成 `Li_centered_or_mixed_redox`，**永远不会**产出 `state_identity_ambiguous`。本次数据未触发该缺口，但代码与自身判据文本不符。

### 3.2 4 个 `no_intact_minimum_found` 里是否其实还有 Li 配位（< 3.0 Å）？
**没有。** 我从各自 `*_dication_opt.out` 的**最终** Cartesian 块独立计算 Li 到全部给体(O/N/S/P)的最小距离：

| 分子 | 我的独立 Li–给体最小距离 (Å) | record `li_min_distance_a` (Å) | `li_contacts` |
| --- | --- | --- | --- |
| DOL | **8.3952** | 6.8923（见 4.3，其实是最远原子中的 H） | 空 |
| DMSO | 7.2385 | 7.2385 | 空 |
| AN | 9.0463 | 9.0463 | 空 |
| SN | 7.3395 | 7.3395 | 空 |

四者 Li–给体均 ≫ 3.0 Å，`no_intact_minimum_found` 判定成立。

### 3.3 唯一被判 `molecule_centered_redox` 的还原态 SN，证据是否支持「电子留在分子上」？
**支持。** 主证据 `SN_m1_reduced_opt.out`（末块在最后几何之后，状态正常收敛，`scf_converged=true`，`n_scf_cycles=6`）独立复算：`q_Li=0.814339`、`dq_Li=-0.128169`、`spin_Li=+0.007424`、`spin_total=1.0000`、`spin_molecule=0.9926`；主要自旋载体 `C4:+0.614; N5:+0.147; N0:+0.120`（自旋集中在分子骨架，不在 Li）。两指标同时落在「分子中心」区间，判定正确。

### 3.4 有 opt 作业失败而回退垂直单点的行，来源是否标注正确？
**正确。** `SL_m1_dication_opt` 的 record 为 `status=execution_failed`，`error="ORCA timed out after 1800.0s"`；该行 `primary_output=SL_m1_dication_sp.out`，`li_min_distance_a` / `relaxed_label` 留空。DMC-m2、TMP-m2 无 opt 产物同样回退到 `_sp.out`。三者均符合「弛豫优化输出存在且成功 → relaxed_opt，否则 vertical_sp」的冻结逻辑。

### 3.5 文件完整性：有没有被截断却当正常解析的 `.out`？
- `SL_m1_dication_opt.out` **确实被截断**（无 `ORCA TERMINATED NORMALLY`，末尾停在 `Finished LeanSCF`），但该文件**未被采用**（record `execution_failed`），处理正确。
- 其余被采用的文件均 `ORCA TERMINATED NORMALLY`，且末个 Mulliken 块位置正常。
- **但发现 5 个「未截断却也没有最终布居块」的文件**（AN/DMSO/DOL/SN 双阳离子 opt + TMP_m2_cation_opt）：文件正常结束，但**最后一个** Mulliken 块停在优化第 0 步，脚本无从察觉，见下节 4.1。

### 3.6 电子计数完整性（补充）
全目录 `outputs/week5/c1/**/*.out` 均无 `LOEWDIN FINDS ... ELECTRONS INSTEAD OF`（历史 stale-gbw 事件已修复）；被采用文件最后一个 `Sum of atomic charges` 均等于形式电荷（cation=1、dication=2、reduced=0）。未发现电子数不对却正常结束的可用文件。

---

## 4. 发现清单（均不改变标签；按严重度排序）

### 4.1【中】4 个双阳离子行的“弛豫密度”其实是**未弛豫初始几何**的密度
证据：`AN/DMSO/DOL/SN _m1_dication_opt.out` 均只有 **1 个** Mulliken 块，位置在第一个 Cartesian 块之后、第一次 `FINAL SINGLE POINT ENERGY` 之前（例如 AN 在第 809 行，最后一个 Cartesian 在第 23498 行）。这些优化**未收敛**（50 步迭代上限，无 `THE OPTIMIZATION HAS CONVERGED`，末几步 Li 仍在远离）。
可判定为“初始几何密度”的硬证据——它与同几何的垂直单点几乎完全重合：

| 分子 | opt 末块 q_Li / spin_Li | sp q_Li / spin_Li | 差 |
| --- | --- | --- | --- |
| AN | 0.988270 / +0.001349 | 0.988281 / +0.001354 | 1e-5 |
| DMSO | 0.959070 / +0.000222 | 0.959048 / +0.000175 | 2e-5 |
| DOL | 0.969807 / -0.000772 | 0.969824 / -0.000793 | 2e-5 |
| SN | 0.981248 / +0.000474 | 0.981237 / +0.000486 | 1e-5 |

后果：这 4 行的 `q_li_state`、`spin_li_state`、`dq_li`、`relaxed_label`、`top_spin_carriers` 标称来自“弛豫优化后的密度”（MD 第 18 行标题如此写），实为输入几何的数值；`geometry_changes_identity=False` 也因此失去“对比弛豫 vs 垂直”的本意。
**为何标签仍正确**：这 4 行由「几何优先」分支判定（`no_intact_minimum_found`），与电子密度无关。
附带记录的风险：这 4 个几何优化未收敛，但 record 仍记为 `status=ok`（`terminated_normally=null`）。

### 4.2【中】TMP-m2 的参考密度与其余 11 个 motif 的口径不一致
`TMP_m2_cation_opt.out` 同样只有 1 个 Mulliken 块（第 956 行，最后一个 Cartesian 在第 33124 行），所以 `q_li_ref=0.909434` 取自初始阳离子几何；而其他 motif 的 `q_li_ref` 取自**弛豫后**阳离子几何（末块在最后 Cartesian 之后）。因此 12 个 motif 的“参考态”定义不统一：11 个是弛豫阳离子、1 个是初始阳离子。
**无法进一步核实**：该作业没有在“最终阳离子几何”上的单点，故无法独立算出“弛豫后 TMP-m2 阳离子”的 `q_Li`。对标签无影响（TMP-m2 dication `|dq|≈0.031`、reduced `|dq|≈0.983`，远离阈值）。

### 4.3【低-中】`li_min_distance_a` 被当作“Li-给体距离”，实为 Li 到**任意原子**的距离
脚本 `run_c1_li_coordination.py::geometry_qc` 对 `range(len(symbols_h))`（含 H）取最小值；而 CSV/MD 把该列呈现为“Li 最近给体距离 (A)”。24 行中有 1 行因此失真：

| 行 | CSV/MD 值 | 真实最近原子 | 真实 Li–给体(仅 O/N/S/P)最小距离 |
| --- | --- | --- | --- |
| DOL m1 dication | 6.8923 Å | **H（第 9 号原子）6.8923 Å** | **8.3952 Å**（O） |

MD 正文“Li-给体最近距离 6.9–9.0 Å”对 DOL 不成立（给体口径应为 7.24–9.05 Å）。结论（`no_intact_minimum_found`）不变，但**该列的名称与口径需要修正**（`li_contacts` 的 3.0 Å 接触判定本身只用给体，是正确的）。

### 4.4【低】`state_identity_ambiguous` 无法由“指标冲突”触发
见 3.1。代码与 `DEFINITION` 文本不一致；本次无受影响行。

### 4.5【提示】CSV 无 `relaxed_opt`/`vertical_sp` 列
任务描述的“检查 `label_source` 是 `relaxed_opt` 还是 `vertical_sp`”与实际 schema 不符：`label_source` ∈ {`geometry`,`electron`}，relaxed/vertical 的出处由 `primary_output` 体现。已按此核实（2.5）。

---

## 5. 无法核实的点

1. **TMP-m2 弛豫阳离子的 `q_Li`**：不存在该几何下的单点，无法验证 `q_li_ref=0.909434` 若改用弛豫几何是否会改变 `dq_Li`（预计不改变标签）。
2. **`parent_bonds_intact` 的连通性判定**：我复算了一致性（24 行均 `True`，无 `dissociated_optimized_product`），但未独立重跑键连通/断键算法，仅核对了其取值路径与 `dissociated` 标签从未触发。
3. **`motif_switch`**：本次 24 行未产生该标签（几何优先分支中，4 行因 `li_contacts` 为空直接落到 `no_intact_minimum_found`，未走到 donor 交集判定），故该分支未被数据检验。
4. **4 个未收敛双阳离子的“真实弛豫态”**：ORCA 未写出最终布居块，也没有对最终几何补做单点，故无法给出“弛豫后”的 `q_Li/spin_Li`（只能证明被计入的是初始几何值）。

---

## 6. 只读声明

本次审计未修改 `outputs/week5/`、`outputs/figures/`、`scripts/`、`docs/`、`tests/` 下任何既有文件；未运行 ORCA、未做任何新的 QM 计算。所有临时脚本与本报告均位于 `outputs/_week5_scratch/`。
---

## 收尾处置（收尾人记录，2026-09-29）

本审计的 5 条发现，按「真缺陷 -> 处置」逐条登记。**没有**任何一条改变 `state_identity_label`。

| # | 发现 | 处置 |
| --- | --- | --- |
| A1 | `electron_label()` 的 `li_side and molecule_side` 分支**不可达**，冻结条文里「两指标冲突 -> `state_identity_ambiguous`」未被实现；真冲突会被静默判成 `Li_centered_or_mixed_redox` | **已修**：两个指标先各自定性再合并，冲突与「两边都无法分辨」都归入 `state_identity_ambiguous`。逐行重算证明**标签不变**（24 行标签变化数 = 0；正例 `spin = 0.8, dq = 0.0` 现在返回 ambiguous）。见 `docs/12` §2.8。 |
| A2 | 4 条双阳离子重弛豫（`AN` / `DOL` / `DMSO` / `SN` 的 `m1_dication_opt`）**未收敛**（ORCA 报 did not converge but reached the maximum number of optimization cycles），`.out` 只含**第 0 步**布居块，却被 runner 记为 `status=ok` | **已在产物中显式化**：新增 `primary_converged` 列，由输出文本判定（`yes` / `NO` / `n/a`），该 4 行标为 `NO`；其电子读数等于初始几何，标签仍由**几何分支**决定。runner 的「正常终止即 ok」口径**未改动**（不静默补算、不改既有记录），改以 `docs/12` §7 明示。 |
| A3 | `TMP_m2_cation_opt` 同样未收敛，故 `TMP m2` 两行的 `q_Li(ref)` 取自第 0 步，与其余 11 个 motif 口径不同 | **已在产物中显式化**：新增 `reference_converged` 列，该 2 行标为 `NO`。标签（`molecule_centered_redox`，`dq` 约 -0.03）对参考态口径不敏感。 |
| A4 | `li_min_distance_a` 实为 Li 到**任意原子（含 H）**的距离，却被标为「Li 最近给体距离」；DOL 双阳离子的 6.892 A 是 Li...H，真实 Li-O = 8.395 A | **已修口径**：产物列名与表头改为「Li 到最近原子 (A)」，并在 `c1_state_identity.md` §4 与 `docs/12` §2.8 / §7 注明；几何结论不变。 |
| A5 | `SL_m1_dication_opt.out` 被截断（1800 s 超时） | **判定正确**：该行未被采用（`status=execution_failed`），主证据回退到垂直单点（`primary_converged = n/a`），无需处置。 |

审计的独立复算结果（24/24 标签与 12 个数值列零差异、CSV / JSON / MD 互洽、4 个 `no_intact_minimum_found` 经独立几何计算确认 Li 已离开、SN 还原态确为分子中心）**未被收尾改动推翻**：收尾只增加了收敛性列与口径文字，标签与全部数值列逐格复算后与审计时完全一致。