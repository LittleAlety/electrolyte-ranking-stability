# W25 核心集 chemical-space metadata 补列映射（核心文件 v2 §5.2）

- 依据：`E:\Claude Code\电解液溶剂-HB\核心文件\ranking-electrolyte-materials-v2.md` §5.2（L368–388），要求每个候选保存 13 项多轴 metadata。
- 冻结件：`data/metadata/core_set.csv`（14 列，18 行）**不改**，本次另建 `data/metadata/core_set_metadata_ext.csv`。
- 生成脚本：`scripts/build_core_set_metadata_ext.py`（确定性、幂等，支持 `--check`；**零新增电子结构计算**，只抽取既有产物）。
- 新增产物：`data/metadata/core_set_metadata_ext.csv`，列 = `mol_id,name,formal_charge,conformer_count,Li_motif_count,state_identity_status,reactivity_status,qc_status,source_refs`，恰 18 数据行。

**硬性纪律**：任何在仓库内找不到可靠来源的字段一律写 `not_available_in_repo`，不推算、不编造；子集字段只在子集写值，其余写 `not_available_in_repo`。每行 `source_refs` 逐字段写明"取自哪个文件、哪个字段/键"。

---

## 1. §5.2 全部 13 项字段 → 本文来源 → 覆盖率

| # | §5.2 字段 | 含义 | 本仓库来源（文件:字段/键） | 覆盖率 | 判定 |
|---|---|---|---|---|---|
| 1 | `molecule_id` | 唯一编号 | `data/metadata/core_set.csv:mol_id` | 18/18 | 已在 core_set.csv |
| 2 | `canonical_smiles` | 规范结构 | `data/metadata/core_set.csv:smiles` | 18/18 | 已在 core_set.csv |
| 3 | `structural_family` | carbonate / ether / nitrile / sulfone / phosphate 等互斥主家族 | `data/metadata/core_set.csv:family` | 18/18 | 已在 core_set.csv |
| 4 | `functionalization_tags` | fluorinated / unsaturated / cyclic / chelating 等可多选标签 | `data/metadata/core_set.csv:functionalization_tags` | 18/18 | 已在 core_set.csv |
| 5 | `use_role` | solvent / co-solvent / additive / anchor | `data/metadata/core_set.csv:role` | 18/18 | 已在 core_set.csv |
| 6 | `donor_atoms` | 潜在 Li 配位原子 | `data/metadata/core_set.csv:donor_atoms` | 18/18 | 已在 core_set.csv |
| 7 | `formal_charge` | 母分子形式电荷 | `outputs/week3/p0_core_set.csv:charge` | 18/18 | 已落表（本次补列） |
| 8 | `rotatable_bonds` | 柔性指标 | `data/metadata/core_set.csv:rotatable_bonds` | 18/18 | 已在 core_set.csv |
| 9 | `conformer_count` | 进入 QC 的构象数 | `outputs/week6/t6_conformer_manifest.json:molecules[].n_kept` | 12/18 | 已落表（子集） |
| 10 | `Li_motif_count` | 配位异构体数 | `outputs/week5/li_motif_generation.csv:motif_id`（仅 `kept=True` 行） | 10/18 | 已落表（子集） |
| 11 | `state_identity_status` | redox 状态身份 QC | `outputs/week5/c1_state_identity.csv:state_identity_label` | 10/18 | 已落表（子集） |
| 12 | `reactivity_status` | intact / motif switch / dissociation 等 | `outputs/week5/li_motif_generation.csv:qc_flags`（仅 `kept=True` 行） | 10/18 | 已落表（子集） |
| 13 | `qc_status` | 各模型层计算状态 | `outputs/week3/p0_core_set.csv:status` + `outputs/week4/p1_core_set.csv:status` + `outputs/week4/p2_core_set_smd_acetonitrile.csv:status`（+ `outputs/week5/c1_li_coordination.csv:status`） | 18/18（p0/p1/p2 臂）；c1 臂 10/18 | 已落表 |

- **无任何 §5.2 字段整体落 `not_available_in_repo`**；`not_available_in_repo` 只按行出现，用于第 9–12 项在子集之外的分子。
- `core_set.csv` 另含 §5.2 未列出的派生列 `donor_count`、`heteroatom_count`、`n_heavy`、`mw`、`tpsa`、`reason_included`；本次补列表不重复它们，也不改动原表。

### 1.1 六字段的逐字段来源与口径

| 字段 | 抽取口径（字面聚合，无任何推算） | 覆盖率 | 未覆盖分子（写 `not_available_in_repo`） |
|---|---|---|---|
| `formal_charge` | `p0_core_set.csv` 中该 `mol_id` 的 `charge`（中性母分子形式电荷） | 18/18 | 无 |
| `conformer_count` | `t6_conformer_manifest.json` 中该分子的 `n_kept`；并用 `t6_conformer_manifest.csv` 的行数交叉校验（二者必须相等） | 12/18 | C03 DEC、C06 FEC、C07 VC、C10 TEGDME、C11 EA、C12 MA |
| `Li_motif_count` | `li_motif_generation.csv` 中 `kept=True` 行的条数（即代表 Li 配位异构体 `motif_id` 数）；并与 `c1_li_coordination.csv` 中该分子的唯一 `motif_id` 数交叉校验 | 10/18 | C02 EMC、C03 DEC、C05 PC、C06 FEC、C07 VC、C10 TEGDME、C11 EA、C12 MA |
| `state_identity_status` | `c1_state_identity.csv` 的 `state_identity_label`，按 redox 态拼成 `dication=<label>;reduced=<label>`；同分子多 motif 标签一致时合并 | 10/18 | 同上 8 个（C02/C03/C05/C06/C07/C10/C11/C12） |
| `reactivity_status` | `li_motif_generation.csv` 中 `kept=True` 行的 `qc_flags` 字面并集（`+` 连接，排序去重）；空集记 `intact` | 10/18 | 同上 8 个 |
| `qc_status` | `p0=..;p1=..;p2=..`（各层 `status` 唯一值，`+` 连接）；该分子在 week5 C1 子集内时追加 `;c1=<status>` | 18/18（p0/p1/p2）；c1 臂 10/18 | c1 臂缺失：同上 8 个 |

### 1.2 逐分子实际取值（18 行）

| mol_id | name | formal_charge | conformer_count | Li_motif_count | state_identity_status | reactivity_status | qc_status |
|---|---|---|---|---|---|---|---|
| C01 | DMC | 0 | 2 | 2 | dication=molecule_centered_redox;reduced=Li_centered_or_mixed_redox | motif_switch | p0=ok;p1=ok;p2=ok;c1=ok |
| C02 | EMC | 0 | 3 | not_available_in_repo | not_available_in_repo | not_available_in_repo | p0=ok;p1=ok;p2=ok |
| C03 | DEC | 0 | not_available_in_repo | not_available_in_repo | not_available_in_repo | not_available_in_repo | p0=ok;p1=ok;p2=ok |
| C04 | EC | 0 | 2 | 1 | dication=molecule_centered_redox;reduced=Li_centered_or_mixed_redox | motif_switch | p0=ok;p1=ok;p2=ok;c1=ok |
| C05 | PC | 0 | 2 | not_available_in_repo | not_available_in_repo | not_available_in_repo | p0=ok;p1=ok;p2=ok |
| C06 | FEC | 0 | not_available_in_repo | not_available_in_repo | not_available_in_repo | not_available_in_repo | p0=ok;p1=ok;p2=ok |
| C07 | VC | 0 | not_available_in_repo | not_available_in_repo | not_available_in_repo | not_available_in_repo | p0=ok;p1=ok;p2=ok |
| C08 | DME | 0 | 5 | 1 | dication=molecule_centered_redox;reduced=Li_centered_or_mixed_redox | motif_switch | p0=ok;p1=ok;p2=ok;c1=ok |
| C09 | DOL | 0 | 2 | 1 | dication=no_intact_minimum_found;reduced=Li_centered_or_mixed_redox | motif_switch | p0=ok;p1=ok;p2=ok;c1=ok |
| C10 | TEGDME | 0 | not_available_in_repo | not_available_in_repo | not_available_in_repo | not_available_in_repo | p0=ok;p1=ok;p2=ok |
| C11 | EA | 0 | not_available_in_repo | not_available_in_repo | not_available_in_repo | not_available_in_repo | p0=ok;p1=ok;p2=ok |
| C12 | MA | 0 | not_available_in_repo | not_available_in_repo | not_available_in_repo | not_available_in_repo | p0=ok;p1=ok;p2=ok |
| C13 | GBL | 0 | 2 | 1 | dication=molecule_centered_redox;reduced=Li_centered_or_mixed_redox | motif_switch | p0=ok;p1=ok;p2=ok;c1=ok |
| C14 | SL | 0 | 2 | 1 | dication=molecule_centered_redox;reduced=Li_centered_or_mixed_redox | intact | p0=ok;p1=ok;p2=ok;c1=execution_failed+ok |
| C15 | DMSO | 0 | 2 | 1 | dication=no_intact_minimum_found;reduced=Li_centered_or_mixed_redox | intact | p0=ok;p1=ok;p2=ok;c1=ok |
| C16 | AN | 0 | 2 | 1 | dication=no_intact_minimum_found;reduced=Li_centered_or_mixed_redox | intact | p0=ok;p1=ok;p2=ok;c1=ok |
| C17 | TMP | 0 | 5 | 2 | dication=molecule_centered_redox;reduced=Li_centered_or_mixed_redox | motif_switch | p0=ok;p1=ok;p2=ok;c1=ok |
| C18 | SN | 0 | 3 | 1 | dication=no_intact_minimum_found;reduced=molecule_centered_redox | motif_switch | p0=ok;p1=ok;p2=ok;c1=ok |

复现命令（零新增计算，只读既有产物后重建 CSV）：

```powershell
.\.venv\Scripts\python.exe scripts\build_core_set_metadata_ext.py
.\.venv\Scripts\python.exe scripts\build_core_set_metadata_ext.py --check
```

---

## 2. 诚实边界（本列只补齐"已有产物的抽取"，不新增物理量）

1. **`formal_charge` 全为 0，是"母分子（中性）形式电荷"，不是 redox 态电荷。** `c1_state_identity.csv` 里 dication 态为 +2、reduced 态为 0，本列**未**混入这些态电荷；若下游需要态电荷，须另读 `outputs/week5/c1_state_identity.csv:formal_charge`。
2. **`conformer_count` 是"计算状态"量，不是物理量。** 它取自 week6 T6 构象离散度敏感性检验 `n_kept`（G1 参考构象 + 能量窗口/RMSD 去重后保留数，上限 4+1），**不代表**核心文件 §6.1 所说"约 3–10 个低能构象进 DFT"的生产构象数——生产一电子量仍只在 `conf_0`/G1 单构象上测量，且**未使用 CREST**。覆盖率仅 12/18（week6 子集：AN、DMC、DME、DMSO、DOL、EC、EMC、GBL、PC、SL、SN、TMP），其余 6 个母分子该检验未运行。
3. **`Li_motif_count` 是流程状态量，不是热力学配位分布。** 只统计 week5 C1 子集中被判 `kept=True` 的代表性 Li⁺ 配位异构体数（取值 0/1/2），不给出异构体相对自由能或配位分布；覆盖率 10/18。
4. **`state_identity_status` 是 QC 标签（六标签受控词表），不是物理量。** dication 态有 4 个 `no_intact_minimum_found`（DOL、DMSO、AN、SN；SL 因几何优化超时该态无 relaxed 几何）；标签依据不统一（部分 `label_source=electron`、部分 `geometry`）。覆盖率 10/18。
5. **`reactivity_status` 是"保留异构体触发/未触发反应性 flag"的状态标注，不是反应速率或能垒。** 词表映射：`motif_switch`→motif switch；`dissociated_optimized_product`→dissociation；空集记 `intact`（表示保留异构体未触发任何反应性 qc_flag）。未保留候选上的 flag 不计入。覆盖率 10/18。
6. **`qc_status` 只回答"计算是否跑成功"，不含精度/收敛阈值。** p0/p1/p2 三层对 18/18 全部 `ok`（p1/p2 各覆盖 neutral/cation/anion 三态）；c1 臂只对 10/18 子集拼接，其中 SL 出现一次 `execution_failed`（ORCA 1800 s 超时，已记录于 `outputs/week5/c1_li_coordination.csv:error`）。此外 `outputs/week4/p1_core_set_audit.json` 的 `unbound_anion`（18/18 气相阴离子不束缚）属科学标记，**未**并入本列。
7. **未覆盖即 `not_available_in_repo`，不插值。** 上述 12/18、10/18 的缺口是完全的 `not_available_in_repo`，脚本不做任何补点、拟合或外推。若要提升覆盖率，须新增 week5/week6 之外的电子结构或构象计算，超出本任务"零新增计算"范围。