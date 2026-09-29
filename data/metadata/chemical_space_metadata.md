# Chemical-space metadata (多轴标签体系)

本文件说明本数据集为什么使用**多轴** chemical-space 标签, 而不是单一 family 轴,
以及 core set 与 broad pool 两层的选择原则。

- 数据集根目录: `data/metadata/`
- 构建脚本: `scripts/build_metadata.py` (确定性重建; CSV 是产物, 不是手改文件)
- 科学定义: `config/scientific_definitions.yaml`
- 依据: `ranking-electrolyte-materials-v2.md` 第 5.2 / 5.3 节

---

## 1. 为什么不能只用单一 family 轴

v2 第 5.2 节明确要求: "**chemical-space metadata 必须是多轴而非单一 family**"。

原因是一个骨架家族内部的性质差异可能大于跨家族的差异。例如:

- `EC` 与 `VC` 同属环状碳酸酯, 但一个饱和、一个不饱和, 还原机理完全不同
  (开环 vs 还原聚合/成膜)。
- `DME` 与 `TEGDME` 同属醚, 但配位数 (2 vs 5) 与柔性 (3 vs 12 个可旋转键) 差异极大。
- `DMC` 与 `FEMC` 同属线性碳酸酯, 但后者含氟, 还原路径与界面化学完全不同。

因此若只用 `family` 一轴做 group split 或 LOFO, 会把"同一母骨架枚举出的极相似衍生物"
当成独立样本, 从而高估模型的外推能力 (v2 §5.3 明确禁止这种切分方式)。

---

## 2. 使用的轴

| 轴 | 取值来源 | CSV 列 | 说明 |
|---|---|---|---|
| A. 骨架主家族 family | 互斥枚举 | `family` | 唯一定义骨架化学的轴; 见第 3 节 |
| B. 给体原子类型 donor type | 由分子图导出 | `donor_atoms`, `donor_count` | `O=` / `O-` / `N`; 决定 Li+ 配位化学 |
| C. 氟化/卤化度 halogenation | 标签 | `functionalization_tags` 中的 `fluorinated` / `halogenated` | 跨家族的取代轴, **不得**成为独立 family |
| D. 柔性 flexibility | `rotatable_bonds` (+ `flexible` 标签) | `rotatable_bonds` | 构象采样复杂度的主要驱动量 |
| E. 环-链与不饱和度 topology/unsaturation | 标签 | `linear` / `cyclic` / `unsaturated` / `aromatic` / `acetal` | 环张力、开环倾向、共轭效应 |
| F. 用途 role | 人工指定 | `role` | `solvent` / `co-solvent` / `additive` |

### 明确规则

1. **氟化不是 family**。v2 §5.2 指出 "fluorinated analogues 不再作为与
   carbonate / ether 平行的 structural family, 因为氟化是一种跨家族 functionalization"。
   因此本数据集中 `HFE347` / `HFE7100` / `BTFE` 等氟代醚的 `family` 记为
   `ether`, 氟化信息记在 `functionalization_tags` 中。
   若下游需要 "fluoroether" 视图, 应由 `family=ether AND tag=fluorinated` 派生,
   而不是另立 family。
2. **给体原子类型不看 family**。碳酸酯与醚都含 O, 但前者有 `O=` 与 `O-` 两类,
   后者只有 `O-`; 腈只有 `N`。这一轴与 family 正交。
3. **family 枚举是闭集**, 新 family 必须写进 `config/scientific_definitions.yaml`
   的 `controlled_vocabularies.family.values` 并记录在案。

---

## 3. family 取值 (受控词表)

`linear_carbonate`, `cyclic_carbonate`, `ether`, `ester`, `sulfone`,
`sulfoxide`, `nitrile`, `phosphate`, `sulfite`, `sultone`, `siloxane`

其中 core set 使用前 8 个; broad pool 额外引入 `sulfite` / `sultone` / `siloxane` 三个新家族。

---

## 4. Core set 选择原则 (18 个分子)

依据 v2 §5.3, core set 必须同时覆盖:

- 不同 donor atom 类型 (`O=` / `O-` / `N` / 以及 S、P 为中心的受主);
- 单齿与潜在双齿配位 (螯合);
- 不同极性与极化率;
- 刚性与柔性分子 (`rotatable_bonds` 从 0 到 12);
- 同家族内部的系统取代 (DMC/EMC/DEC, EC/PC, EA/MA, DME/G2/G3/TEGDME 思想的极小版本);
- 跨家族的结构差异 (碳酸酯 / 醚 / 酯 / 砜 / 亚砜 / 腈 / 磷酸酯);
- 若干常见电解液分子作为 anchors (EC, DMC, EMC, DEC, FEC, VC, DME, DOL, EA, GBL, SL, AN, TMP)。

本课题侧重物理与化学机制, 因此 **主动把 core set 从 v2 建议的 60-100 缩小到 18 个**,
换取每个分子上更严格的 paired 计算与机制分析。

### 机理对照分子 (2-3 个)

| mol_id | name | 对照维度 |
|---|---|---|
| C06 | FEC | 氟化 vs 非氟化环状碳酸酯 (对照 C04 EC / C05 PC), F 取代 -> LiF 生成路径 |
| C07 | VC | 不饱和 vs 饱和环状碳酸酯 (对照 C04 EC), 还原开环/聚合路径 |
| C18 | SN | 双齿 vs 单齿腈 (对照 C16 AN), 螯合与配位数效应 |

### family 覆盖统计 (core set, N = 18)

| family | n | mol_id |
|---|---|---|
| linear_carbonate | 3 | C01 DMC, C02 EMC, C03 DEC |
| cyclic_carbonate | 4 | C04 EC, C05 PC, C06 FEC, C07 VC |
| ether | 3 | C08 DME, C09 DOL, C10 TEGDME |
| ester | 3 | C11 EA, C12 MA, C13 GBL |
| sulfone | 1 | C14 SL |
| sulfoxide | 1 | C15 DMSO |
| nitrile | 2 | C16 AN, C18 SN |
| phosphate | 1 | C17 TMP |

### 多轴分布 (core set)

- 给体类型: 纯 O 给体 13 个, 含 N 给体 2 个 (AN, SN), S 中心 (S=O) 2 个 (SL, DMSO),
  P 中心 (P=O) 1 个 (TMP)。
- donor_count: 1 (AN, DMSO) -> 2 (DME, DOL, EA, MA, GBL, SL, SN) -> 3 (DMC, EMC, DEC, EC, PC, FEC, VC)
  -> 4 (TMP) -> 5 (TEGDME)。
- 柔性: `rotatable_bonds` = 0 的刚性分子 9 个; = 1-3 的 7 个; = 12 的柔性端点 1 个 (TEGDME);
  TMP = 3。
- 卤化: 氟化 1 个 (FEC)。
- 不饱和: 1 个 (VC)。
- 拓扑: 环状 8 个, 线性 10 个。

---

## 5. Broad cheap pool 选择原则 (40 个分子)

用途: 只做廉价结构 descriptor 与 xTB proxy (P0), 用于

1. 化学空间覆盖检查 (core set 是否落在 pool 覆盖范围内, 是否有空洞);
2. active-learning 候选池 (回答"从大候选池中如何选择最值得做昂贵 C1 或 P2 的点")。

选择原则:

- **同类扩展**: 每个 core family 补充 3-5 个系统取代成员 (链长、环大小、甲基取代、卤代);
- **甘醇醚链长序列**: DME -> G2 -> G3 -> TEGDME 的配位数梯度;
- **新家族**, 但只引入与核心机制相关者: `sulfite` (ES), `sultone` (PS), `siloxane` (HMDSO/OMTS);
- **氟代化学**: 通过 `fluorinated` 标签跨 family 覆盖 (碳酸酯、醚、磷酸酯), 不另立 family;
- **极端点**: 给体强度下限 (HFE7100)、位阻最大 (DPC)、柔性最大 (TBP, OMTS),
  用于界定描述符适用边界。

### family 覆盖统计 (broad pool, N = 40)

| family | n | mol_id |
|---|---|---|
| linear_carbonate | 3 | B01, B02, B03 |
| cyclic_carbonate | 5 | B04, B05, B06, B07, B08 |
| ether | 11 | B09, B10, B11, B12, B13, B14, B15, B16, B17, B18, B19 |
| ester | 4 | B33, B34, B35, B36 |
| sulfone | 3 | B20, B21, B22 |
| sulfoxide | 2 | B23, B24 |
| nitrile | 5 | B25, B26, B27, B28, B29 |
| phosphate | 3 | B30, B31, B32 |
| sulfite | 1 | B37 |
| sultone | 1 | B38 |
| siloxane | 2 | B39, B40 |

> 其中 `ether` 的 11 个成员包含 3 个氟代醚 (B17-B19); 它们按第 2.1 条规则计入
> `ether` 而非独立 family。

---

## 6. Core set 多轴明细表

| mol_id | name | family | role | donor_atoms | donor_count | rotatable_bonds | n_heavy | mw | tpsa | functionalization_tags |
|---|---|---|---|---|---|---|---|---|---|---|
| C01 | DMC | linear_carbonate | solvent | O=;O- | 3 | 0 | 6 | 90.08 | 35.53 | linear |
| C02 | EMC | linear_carbonate | solvent | O=;O- | 3 | 1 | 7 | 104.10 | 35.53 | linear |
| C03 | DEC | linear_carbonate | co-solvent | O=;O- | 3 | 2 | 8 | 118.13 | 35.53 | linear |
| C04 | EC | cyclic_carbonate | solvent | O=;O- | 3 | 0 | 6 | 88.06 | 35.53 | cyclic |
| C05 | PC | cyclic_carbonate | co-solvent | O=;O- | 3 | 0 | 7 | 102.09 | 35.53 | cyclic |
| C06 | FEC | cyclic_carbonate | additive | O=;O- | 3 | 0 | 7 | 106.05 | 35.53 | cyclic\|fluorinated |
| C07 | VC | cyclic_carbonate | additive | O=;O- | 3 | 0 | 6 | 86.05 | 43.35 | cyclic\|unsaturated |
| C08 | DME | ether | solvent | O- | 2 | 3 | 6 | 90.12 | 18.46 | linear\|chelating |
| C09 | DOL | ether | co-solvent | O- | 2 | 0 | 5 | 74.08 | 18.46 | cyclic |
| C10 | TEGDME | ether | co-solvent | O- | 5 | 12 | 15 | 222.28 | 46.15 | linear\|chelating\|flexible |
| C11 | EA | ester | solvent | O=;O- | 2 | 1 | 6 | 88.11 | 26.30 | linear |
| C12 | MA | ester | solvent | O=;O- | 2 | 0 | 5 | 74.08 | 26.30 | linear |
| C13 | GBL | ester | co-solvent | O=;O- | 2 | 0 | 6 | 86.09 | 26.30 | cyclic |
| C14 | SL | sulfone | co-solvent | O= | 2 | 0 | 7 | 120.17 | 34.14 | cyclic\|sulfur_containing |
| C15 | DMSO | sulfoxide | co-solvent | O= | 1 | 0 | 4 | 78.14 | 17.07 | linear\|sulfur_containing |
| C16 | AN | nitrile | co-solvent | N | 1 | 0 | 3 | 41.05 | 23.79 | linear |
| C17 | TMP | phosphate | additive | O=;O- | 4 | 3 | 8 | 140.07 | 44.76 | linear\|phosphorus_containing |
| C18 | SN | nitrile | additive | N | 2 | 1 | 6 | 80.09 | 47.58 | linear\|chelating |

---

## 7. Broad pool 多轴明细表

| mol_id | name | family | role | donor_atoms | donor_count | rotatable_bonds | n_heavy | mw | tpsa | functionalization_tags |
|---|---|---|---|---|---|---|---|---|---|---|
| B01 | MPC | linear_carbonate | co-solvent | O=;O- | 3 | 2 | 8 | 118.13 | 35.53 | linear |
| B02 | DPC | linear_carbonate | additive | O=;O- | 3 | 2 | 16 | 214.22 | 35.53 | linear\|aromatic |
| B03 | FEMC | linear_carbonate | co-solvent | O=;O- | 3 | 1 | 10 | 158.07 | 35.53 | linear\|fluorinated |
| B04 | VEC | cyclic_carbonate | additive | O=;O- | 3 | 1 | 8 | 114.10 | 35.53 | cyclic\|unsaturated |
| B05 | TFMEC | cyclic_carbonate | additive | O=;O- | 3 | 0 | 10 | 156.06 | 35.53 | cyclic\|fluorinated |
| B06 | TMC | cyclic_carbonate | co-solvent | O=;O- | 3 | 0 | 7 | 102.09 | 35.53 | cyclic |
| B07 | DMEC | cyclic_carbonate | co-solvent | O=;O- | 3 | 0 | 8 | 116.12 | 35.53 | cyclic |
| B08 | ClEC | cyclic_carbonate | additive | O=;O- | 3 | 0 | 7 | 122.51 | 35.53 | cyclic\|halogenated |
| B09 | DEE | ether | co-solvent | O- | 1 | 2 | 5 | 74.12 | 9.23 | linear |
| B10 | G2 | ether | co-solvent | O- | 3 | 6 | 9 | 134.18 | 27.69 | linear\|chelating\|flexible |
| B11 | G3 | ether | co-solvent | O- | 4 | 9 | 12 | 178.23 | 36.92 | linear\|chelating\|flexible |
| B12 | THF | ether | co-solvent | O- | 1 | 0 | 5 | 72.11 | 9.23 | cyclic |
| B13 | 2MeTHF | ether | co-solvent | O- | 1 | 0 | 6 | 86.13 | 9.23 | cyclic |
| B14 | DIOX | ether | co-solvent | O- | 2 | 0 | 6 | 88.11 | 18.46 | cyclic\|chelating |
| B15 | DMM | ether | co-solvent | O- | 2 | 2 | 5 | 76.09 | 18.46 | linear\|chelating\|acetal |
| B16 | DEE2 | ether | co-solvent | O- | 2 | 5 | 8 | 118.18 | 18.46 | linear\|chelating |
| B17 | HFE347 | ether | co-solvent | O- | 1 | 3 | 12 | 200.05 | 9.23 | linear\|fluorinated |
| B18 | HFE7100 | ether | co-solvent | O- | 1 | 3 | 15 | 250.06 | 9.23 | linear\|fluorinated |
| B19 | BTFE | ether | co-solvent | O- | 1 | 2 | 11 | 182.06 | 9.23 | linear\|fluorinated |
| B20 | DMS | sulfone | co-solvent | O= | 2 | 0 | 5 | 94.13 | 34.14 | linear\|sulfur_containing |
| B21 | EMS | sulfone | co-solvent | O= | 2 | 1 | 6 | 108.16 | 34.14 | linear\|sulfur_containing |
| B22 | SULFOLENE | sulfone | additive | O= | 2 | 0 | 7 | 118.16 | 34.14 | cyclic\|unsaturated\|sulfur_containing |
| B23 | DESO | sulfoxide | co-solvent | O= | 1 | 2 | 6 | 106.19 | 17.07 | linear\|sulfur_containing |
| B24 | THTO | sulfoxide | co-solvent | O= | 1 | 0 | 6 | 104.17 | 17.07 | cyclic\|sulfur_containing |
| B25 | PN | nitrile | co-solvent | N | 1 | 0 | 4 | 55.08 | 23.79 | linear |
| B26 | BN | nitrile | co-solvent | N | 1 | 1 | 5 | 69.11 | 23.79 | linear |
| B27 | ADN | nitrile | additive | N | 2 | 3 | 8 | 108.14 | 47.58 | linear\|chelating |
| B28 | MPN | nitrile | additive | O-;N | 2 | 2 | 6 | 85.11 | 33.02 | linear\|mixed_donor |
| B29 | MN | nitrile | additive | N | 2 | 0 | 5 | 66.06 | 47.58 | linear\|chelating |
| B30 | TEP | phosphate | additive | O=;O- | 4 | 6 | 11 | 182.16 | 44.76 | linear\|phosphorus_containing |
| B31 | TBP | phosphate | additive | O=;O- | 4 | 12 | 17 | 266.32 | 44.76 | linear\|phosphorus_containing\|flexible |
| B32 | TFP | phosphate | additive | O=;O- | 4 | 6 | 20 | 344.07 | 44.76 | linear\|fluorinated\|phosphorus_containing |
| B33 | MP | ester | co-solvent | O=;O- | 2 | 1 | 6 | 88.11 | 26.30 | linear |
| B34 | EF | ester | co-solvent | O=;O- | 2 | 2 | 5 | 74.08 | 26.30 | linear |
| B35 | GVL | ester | co-solvent | O=;O- | 2 | 0 | 7 | 100.12 | 26.30 | cyclic |
| B36 | DVL | ester | co-solvent | O=;O- | 2 | 0 | 7 | 100.12 | 26.30 | cyclic |
| B37 | ES | sulfite | additive | O=;O- | 3 | 0 | 6 | 108.12 | 35.53 | cyclic\|sulfur_containing |
| B38 | PS | sultone | additive | O=;O- | 3 | 0 | 7 | 122.14 | 43.37 | cyclic\|sulfur_containing |
| B39 | HMDSO | siloxane | co-solvent | O- | 1 | 2 | 9 | 162.38 | 9.23 | linear\|silicon_containing |
| B40 | OMTS | siloxane | co-solvent | O- | 2 | 4 | 13 | 236.54 | 18.46 | linear\|silicon_containing\|flexible |

> 表内 `|` 已转义为 `\|`, 与 CSV 中的 `|` 分隔符含义相同。

---

## 8. 已知覆盖缺口与局限

- 阴离子与盐 (LiPF6, LiFSI, LiTFSI 等) **不在**本数据集范围内; 本项目对象是候选
  小分子/共溶剂/添加剂 (v2 §2.1)。
- 缺少含 S 单齿给体 (硫醚) 与含 P 三价给体; 目前 S/P 全部以 S=O / P=O 形式出现。
- 缺少多羟基/质子型溶剂; `donor_atoms` 目前没有 `O-H` 情形。
- broad pool 的 `ether` 偏多 (11/40), 这是为了覆盖甘醇醚配位数序列与氟代醚,
  但在做 family 级别统计时必须显式说明这一不均衡, 不得直接按分子数加权。
- 所有描述符是 2D 图论量, 不含构象依赖的极性/极化率; 后者归入 `X0` 的可选子集,
  由 xTB 层另行产出。

---

## 9. 扩展规则

新增分子时:

1. 把结构写入 `scripts/build_metadata.py` 的 `CORE_SET` 或 `BROAD_POOL` 表
   (分配到哪一层必须写明理由);
2. `family` 只能取受控词表内的值; 需要新值时必须先更新
   `config/scientific_definitions.yaml`, 并记录理由;
3. 运行 `python scripts/build_metadata.py` 重建 CSV, 然后 `--check` 确认一致;
4. core set 的任何增删都属于对已冻结定义的修改, 必须走
   `config/prereg.yaml` 的 `amendment_policy` (append-only), 不得静默修改。
