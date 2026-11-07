# W25 · Gate 1 还原轴判定（旁证级数据，不可判定）

> 生成脚本：`scripts/analyze_w25_gate1_reduction.py`（确定性，无随机数；`--check` 可复验）

## 0. 结论先行

- **该轴不可能通过 Gate 1 的排序层判据**：文件内只有 3 个物种，最多组成 C(3,2) = **3 对**，低于预注册的 `n_pairs >= 18`。
- 定性为 **`insufficient_pairs`（不可判定 / 仅旁证）**，而不是“判负”。**“证据不足”与“排序不一致”是两回事**：前者是样本量问题，后者才是结论冲突。
- 真正判负的是**氧化轴**：`n_pairs=21`、`tau_b=0.4286 < 0.9`（`outputs/week25/series_rel_ordering_check.json`）。若把还原轴这 3 对拿去报 τ_b，会把“没数据”包装成“有结论”。
- 要满足 `n_pairs >= 18`，一条同判据系列至少需覆盖 **7 个核心集分子**（C(7,2)=21）。当前缺口 15 对。

## 1. 为什么这条轴“不可能”通过

| 项目 | 值 |
|---|---|
| 系列 | `DOE_APR_FY2016`（adjudication = secondary）|
| 物种 | EC, FEC, VC |
| 可用对数 | **3**（C(3,2)）|
| 预注册门槛 | n_pairs >= 18，且 tau_b >= 0.9 |
| 缺口 | **15 对** |
| 判定 | `not_evaluable_secondary_only` / `insufficient_pairs` |

该 3 行数据本身**也不是一条同装置系列**：FEC/VC rows are Si-Gr half cells, the EC row is a graphite half cell, and the descriptor is a first-cycle dQ/dV peak (not an LSV onset at 1 mA/cm2); the three rows are not one (paper, apparatus, criterion) series。

## 2. 取向口径（本判定的关键前提）

| 侧 | 量 | 取向 |
|---|---|---|
| 模型 | `p_red = E(anion) - E(neutral) = -EA (P1: p1_red_ev; P2: E(anion)-E(neutral))` | **larger = harder to reduce = more stable** |
| 实验 | `reduction potential in V vs Li/Li+ (DOE dQ/dV first-cycle peak)` | **larger = reduced sooner = easier to reduce** |

因此一致判据是 `sign(exp_i - exp_j) == -sign(model_i - model_j)`。

**与 `scripts/check_series_rel_ordering.py` 的差异（必须说明）**：该脚本对两个性质一律使用 `sign(exp) == sign(model)`（第 230–247 行）。这对 `p1_ox_ev`（= IP，越大越难氧化、实验氧化电位越高）成立，但对 `p1_red_ev`（= −EA，越大越难还原、实验还原电位越低）**取向相反**——脚本 docstring 里“两个键与实验电位同向”的说法只对氧化轴成立。

该缺陷目前是**潜伏的**：`data/anchors/within_series_ordering.csv` 只有氧化行，还原分支从未执行。本模块**只报告、不修改**——`scripts/check_series_rel_ordering.py` 与 `outputs/week2/series_rel_ordering_check.json` 均为冻结件，未作任何改动。

## 3. 三对逐一对照

DOE 旁证序（易还原 → 难还原）：**FEC > VC > EC**。

### 3.1 P1（气相 r2SCAN-3c 垂直，−EA）

| 物种 | p1_red_ev (eV) | 实验电位 (V vs Li) |
|---|---|---|
| VC | 1.9893 | 0.74 |
| FEC | 2.5564 | 1.20 |
| EC | 2.5903 | 0.70 |

P1 计算序（易 → 难）：**VC < FEC < EC**；与实验序一致：**否**。

| 对 | 实验符号 | 模型符号 | 物理取向判据 | 冻结脚本判据 |
|---|---|---|---|---|
| EC / FEC | -1 | +1 | 一致 | **不一致** |
| EC / VC | -1 | +1 | 一致 | **不一致** |
| FEC / VC | +1 | +1 | **不一致** | 一致 |

- **符号一致数（本模块取向）：2 / 3**；按冻结脚本取向则为 1 / 3。
- 唯一分歧对：FEC 与 VC 的相对位置（实验 FEC 更易还原；模型判 VC 更易还原）。其余两对（FEC/EC、VC/EC）两种取向都给出一致。

### 3.2 P2（CPCM/SMD 乙腈，G1 几何上的垂直量）

| 物种 | E(anion)−E(neutral) (eV) | 实验电位 (V vs Li) |
|---|---|---|
| VC | -0.0966 | 0.74 |
| FEC | 0.5512 | 1.20 |
| EC | 0.5883 | 0.70 |

P2 计算序（易 → 难）：**VC < FEC < EC**；与实验序一致：**否**。

- **符号一致数（本模块取向）：2 / 3**；按冻结脚本取向则为 1 / 3——与 P1 完全相同。
- 隐式溶剂下仍只有 **VC** 的ΔE 为负（阴离子真正束缚）；EC、FEC 仍为正。

## 4. P1 气相阴离子全部不束缚 → P1 还原排序不是物理结论

`outputs/week4/p1_core_set_audit.json` 记录 `unbound_anion = 18`（共 18 个分子），即 P1 气相阴离子 **18/18 不束缚**。因此 P1 的还原量是有限基组下的伪束缚痕迹，**P1 还原排序不可作为物理结论**；还原轴的结论只以 **P2 / C1 为载体**（与论文 §2.3、§3.2 口径一致）。这也是本模块把 P2 并列汇报的原因。

## 5. C1 条件态：覆盖不足，无法补位

`outputs/week5/c1_coord_shifts.csv` 的主 motif 行覆盖 10 个分子，其中与 DOE 三物种的交集只有 **EC**，可组成 **0 对**。即便把条件态纳入，也无法形成任何一对，因为 FEC 与 VC 从未进入 Li 配位集。

另需注意 C1 的态身份问题：`redox_state=reduced` 的 12 行中，AN、DMC、DME、DMSO、DOL、EC、GBL、SL、TMP 的电子落在 Li⁺ 上（`state_identity_label != molecule_centered_redox`），所以 C1 的“还原”序本质上是 Li 中心的，不是裸溶剂的还原序。

## 6. Gate 1 当前状态

| 轴 | 数据 | 对数 | 结果 |
|---|---|---|---|
| 氧化 | Ue1994 / Okoshi2015（同装置 LSV 系列 `Ue1994_Okoshi2015`）| 21 | **判负**：tau_b = 0.4286 < 0.9（`ordering_disagrees`）|
| 还原 | DOE APR FY2016 旁证 3 行 | 3 | **不可判定**：不足 18 对（`insufficient_pairs`）|

因此 Gate 1 仍然**未闭合**，但两个轴的未闭合方式不同：氧化轴是“结论冲突”，还原轴是“证据缺失”。

## 7. 若要把还原轴做成 ≥ 7 个同判据锚点，还需要什么

- 最低要求：one series_id covering >= 7 of the 18 core-set molecules with a differentiating reduction descriptor -> C(7,2)=21 usable pairs >= 18
- 同装置：电极材料、电解池、参比电极及其盐桥均一致（same apparatus: electrode material, cell, reference electrode and junction）
- 同判据：例如统一的“电流密度达到某一阈值时的 LSV 起始电位”，或在惰性电极 + 惰性阳离子条件下的 CV 峰位（same criterion）
- 同态：Li 盐体系锚定的是 C1/C2 梯级，不能用来裁决 C0 梯级（same state）
- 给出参比电极换算关系与可重复性数值（stated conversion and reproducibility）
- 描述符在 7 个以上溶剂之间必须真有离散度——被共同分解极限钉死的系列不含排序信息

候选来源（**均为 PI 提供的文献线索，本仓库未取到原文、未核验数值**）：

| 来源 | DOI | 预期覆盖 | 已知限制 |
|---|---|---|---|
| Delp et al., Electrochim. Acta 2016, 209, 498-510 | 10.1016/j.electacta.2016.05.100 | EC, DMC, FEC, VC | 4 species -> 6 pairs, still < 18; Li-salt electrolyte, so it anchors the C1/C2 tier rather than C0 |
| Borodin, Behl, Jow, J. Phys. Chem. C 2013 | — | DMC, EMC, EC, PC, VC, TMS, TMP | per-entry criteria differ; pooling it as one series would violate the same-criterion requirement |
| Ue 1994 / Ue 1997 reduction limits | 10.1149/1.2059270 / 10.1149/1.1837882 | many solvents | the reduction limit is capped near -3.0 V vs SCE by Et4N+ decomposition, so the series has no discriminating power for solvent reduction |

本轮**明确没有做**的事：
- no uncertainty was assigned to the three DOE rows (the source states none)
- no attempt was made to reach 18 pairs by pooling unlike apparatuses

## 8. 可复现性与来源

| 输入 | SHA256 |
|---|---|
| `data/anchors/doe_apr2016_reduction_secondary.csv` | `32905b49bd655678ed0777ffe687438be00e6cd7614eed8874fe1cd395dd227a` |
| `data/anchors/within_series_ordering.csv` | `bd54233799154343c1f8da3cf3e753588f593d159c4098dd086cf50efe57f2c5` |
| `outputs/week4/p1_core_set_derived.csv` | `2987f8771b722d5a07517289a18a486fb2da24ed5775a196ffd7baf2c57517d3` |
| `outputs/week4/p2_core_set_smd_acetonitrile.csv` | `b6a9b9170a795d21c15006e7f3bc3aec767560203e82de62b63d994f97a2e7e8` |
| `outputs/week4/p1_core_set_audit.json` | `d796fcfd4477ec7be9cdcf6951f2980a2b9c3252e4a08a5346f32c7088809a48` |
| `outputs/week5/c1_coord_shifts.csv` | `1f9597ba376ffb19610e855e4d83a4e2360a8ac5009209cf764be91008634b5d` |
| `outputs/week5/c1_state_identity.csv` | `cc035b941936842a739d2c23833552acfa3c010283e280276849e0be8d6d1aa3` |
| `outputs/week25/series_rel_ordering_check.json` | `9eac280f1edc6def1d390c03c216abbb1a2e30e8cbd7a8693597abd2178949ae` |

复验：`python scripts/analyze_w25_gate1_reduction.py --check`（输出与磁盘逐字节一致才返回 0）。

