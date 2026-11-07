# 00 Stage 0 科学定义冻结 (Gate 0)

- 项目: 电解液溶剂 ranking 稳定性 (decision-centric ranking stability)
- 阶段: Stage 0 — 冻结科学定义与 metadata
- 状态: **FROZEN**
- 冻结日期: 2026-09-29（**R13 修订: 2026-10-08**，见 `docs/46_definitional_amendment_r13.md`）
- 依据: `核心文件/ranking-electrolyte-materials-v2.md` 第 3 / 4 / 5 / 6 / 8 节与第 19 节 Stage 0

本文件是 Stage 0 的收口文档: 汇总"科学定义冻结"的全部内容, 并给出可判定的 Gate 0 判据。
所有字段名使用英文, 说明使用中文; 文件编码 UTF-8。

---

## 1. Stage 0 操作清单与产物映射

v2 第 19 节列出 Stage 0 的 8 项操作。其落盘位置如下:

| # | v2 Stage 0 操作 | 产物 |
|---|---|---|
| 1 | 确定 core set 与 broad pool | `data/metadata/core_set.csv` (18), `data/metadata/broad_pool.csv` (40) |
| 2 | 建立 structural_family / functionalization_tags / use_role | `data/metadata/chemical_space_metadata.md`, `config/scientific_definitions.yaml` |
| 3 | 定义 oxidation / reduction quantity 与方向 | `config/scientific_definitions.yaml` 的 `objectives` |
| 4 | 冻结 common embedding 的物理含义 | `config/scientific_definitions.yaml` 的 `axis_A_proxy_hierarchy.P2a` / `P2eps` 与 `axis_C_external_reference` |
| 5 | 预注册 k/N = 10%, 20%, 30% | `config/prereg.yaml` 的 `top_k` |
| 6 | 预注册 robust-pair tolerance 的确定方法 | `config/prereg.yaml` 的 `pair_comparison` |
| 7 | 冻结 reference ligand R | `config/scientific_definitions.yaml` 的 `reference_ligand` |
| 8 | 冻结 external anchor 搜集规则 | `config/scientific_definitions.yaml` 的 `axis_C_external_reference` |

另外新增 (本项目主动加严):

| # | 补充操作 | 产物 |
|---|---|---|
| 9 | 多轴 chemical-space 标签体系 | `data/metadata/chemical_space_metadata.md` |
| 10 | 数据集确定性重建 + 一致性校验 | `scripts/build_metadata.py` (`--check`) |

---

## 2. 科学定义冻结摘要

### 2.1 Axis A: proxy / electronic-structure hierarchy

| 层级 | 定义 | 方向 |
|---|---|---|
| `P0` | cheap scalar proxy: `P0_ox = -eps_HOMO`; `P0_red = +eps_LUMO` (或符号统一的 xTB vertical EA proxy) | maximize |
| `P1` | gas-phase molecular redox thermodynamics: `dG_ox_gas = G_gas(M+) - G_gas(M)`; `dG_red_gas = G_gas(M-) - G_gas(M)` | maximize |
| `P2` | fixed-background continuum redox thermodynamics: `dG_ox_cont`, `dG_red_cont` | maximize |

关键约束:

- `P0` 必须是**标量**代理量。偶极矩、极化率、ESP、fingerprint 属于 features,
  **不得**当作一个 "fidelity level"。
- `P0` 只回答"极低成本 scalar proxy 是否已保留目标排序", **不得**解释为真实 redox potential。
- `P1` 中若气相阴离子不是稳定束缚态, 标记 `unbound_anion`, 不给出伪精确 adiabatic EA。
- `P2` 是"共同 embedding 引起的 rank shift", 不是每个候选自己的 neat-liquid bulk。

### 2.2 Axis B: environment / conditional-species hierarchy

| 层级 | 目标物种 | 回答的问题 |
|---|---|---|
| `C0` | 自由分子 `M` | 自由态下的 redox proxy |
| `C1` | `[LiM]+` 及其 redox states | 处于 Li+ 配位态时 redox proxy 如何变化 |
| `C2` | 少量代表体系的显式微溶剂化 cluster | C1 的 1:1 配位图像是否对关键 inversion 稳健 |

- 这一轴**不**称为"更高 fidelity", 因为环境变化可能同时改变 chemical species。
- 核心量为 conditional coordination shift `dGdG_ox_coord` 与 `dGdG_red_coord`。
- `C2` 只做 targeted sensitivity check, 禁止把不同化学计量的 cluster 做简单 Boltzmann 平均。

### 2.3 Axis C: external reference layer

| 层级 | 内容 | 审计对象 |
|---|---|---|
| `R_gas` | 约 8-10 个实验 IP/EA 或高等级计算的可靠分子 | `P1` 的绝对标度、family 趋势、排序 |
| `R_sol` | 约 10-20 个条件尽量统一的实验 solution redox 数据 | `P2` |
| `R_env` | 少量典型 Li-coordination case 的已发表结果/趋势 | `C1` (定性/半定量) |

条件不可统一时, **不**做绝对值 pooled regression, 优先 within-series 相对排序, 条件写入 metadata。

### 2.4 目标量与筛选方向

- `S_ox(M) = dG_ox(M) = G(M+) - G(M)`, `objective_direction = maximize`;
  `S_ox` 越大 => 一电子氧化越困难。
- `S_red(M) = dG_red(M) = G(M-) - G(M)`, `objective_direction = maximize`;
  `S_red` 越大 => 电子附着越不利 => 该一电子还原越困难。
- 所有 Top-k / selection regret / threshold metric **必须**分别记录 `objective_direction`,
  代码禁止默认"所有指标越大越好"。
- 口径: 只研究 **intact-species / conditional-species one-electron redox thermodynamic proxies**,
  **不等于**完整电化学稳定窗口。

### 2.5 热化学约定

- 温度: `T = 298.15 K`; `RT = 2.4789 kJ/mol = 0.025693 eV`。
- 标准态: 气相 `p = 1 bar`; 溶液 `c = 1 mol/L` (理想气体/理想溶液)。
- 参考电极: 主约定 `Li/Li+ (1 M, 298.15 K)`; `E(Li/Li+) = -3.0401 V vs SHE`;
  `F = 96485.33212 C/mol`。以 kJ/mol 报告为主, 换算为电位刻度时必须显式记录约定。
- **molecularity 警告**: redox difference 前后 molecularity 不变, 标准态与平动项大量抵消;
  但 `Li+ + M -> [LiM]+` 改变 molecularity, 会引入明显的平动熵 artifact。
  因此 `G = E_elec + G_thermal + dG_solv` **不得**当作无需说明的通用公式。

### 2.6 Reference ligand R (v2 §8.2)

- 交换反应: `[LiR]+ + M -> [LiM]+ + R`
- 定义: `dGdG_bind(M;R) = G([LiM]+) + G(R) - G([LiR]+) - G(M)`
- 理由: 反应前后 molecularity 相同, 显著降低标准态与平动熵伪差, 并减少对 Li+ 绝对
  solvation free energy 的依赖。
- **主参考 R = DME (C08)**: 在 core set 内; 双齿 2x O 螯合、配位 motif 唯一;
  无环张力/无开环副反应通道; 分子量小、易得高纯样品。
- 被排除的候选及理由: DOL (开环/聚合倾向), EC (高熔点固体 + 还原开环),
  AN (单齿 N, 与多数 O 给体候选模式差异过大, chelate 偏置), TMP (既成膜又有多个等价 O)。
- **第二参考 R = AN (C16)**, 仅用于 robustness check; 若关键结论在 R = DME 与 R = AN 下不一致,
  必须标记为 R-dependent。
- 绝对结合量 `dG_bind_abs` 可保留作辅助量, 但**不**作为核心 mechanistic truth。

### 2.7 Continuum 两类 sensitivity test 必须分开

- A. **Fixed-solvent continuum benchmark**: 所有候选使用同一个被明确参数化的固定参考溶剂;
  具体溶剂在 Stage 1 / Gate 1 冻结。
- B. **Dielectric-only sensitivity**: CPCM/COSMO 类, `eps = 5, 10, 20, 40`。
- 禁止把 SMD 的 solvent-specific non-electrostatic 参数与"只改变介电常数"混为同一操作。

### 2.8 构象与状态采样

- 母分子构象: SMILES -> 3D -> CREST/GFN2-xTB 搜索 -> 能量窗口 -> 聚类 -> 3-10 个低能构象进 DFT;
  neutral / cation / anion **不**假定共享同一最优构象空间。
- ensemble 自由能: `G_q^ens = -RT ln sum_i g_i exp(-G_q,i / RT)`; 不同 charge state 分别建 ensemble。
- Li+ motif 生成: 识别 O/N/S/P donor -> 单齿 -> 允许的双齿 -> ESP minima 补充 -> xTB 预优化 ->
  去重 -> 低能 motif 进 DFT; 不同 redox state 重新允许 motif relaxation。
- State identity QC 标签: `molecule_centered_redox`, `Li_centered_or_mixed_redox`,
  `motif_switch`, `no_intact_minimum_found`, `dissociated_optimized_product`,
  `reaction_path_verified`。只有具备额外 reaction-path/TS/动力学证据时才可解释为已验证反应路径;
  几何优化导致断键本身不能证明无势垒。

### 2.9 R13 定义修订 (2026-10-08)

append-only amendment (`config/prereg.yaml` 的 `amendment_log`), schema 1.0 -> 2.0。要点:

- **P1 -> P1v + P1a**: 早期 "P1" 实为同一几何上的三态单点 (vertical), 正式更名 `P1v`
  (`IP_v = E(M+;G1) - E(M;G1)`); 新增 `P1a` (adiabatic, 每态各自弛豫)。气相阴离子不束缚时 `EA_a`
  按 `unbound_anion` 规则排除。
- **P2 -> P2a + P2eps**: `P2a` = 固定溶剂 (SMD 乙腈); `P2eps` = bare CPCM 介电扫描。二者是不同物理实验, 不得混成同一条溶剂阶梯。
- **C2 更名**: `[Li(M)2]+` 是第一配位壳 (coordination number 2), 不是 second solvation shell。
- **C1 还原态分层**: 主还原 ranking 只接受 `molecule_centered_redox`; 其余标签作为 mechanistic state-identity outcome 单独统计。
- **pairwise 三态判据**: `STABLE` / `UNRESOLVED` / `ROBUST_INVERSION` (+ 描述性 `WEAK_SHIFT`) 与 `f_unresolved(z)` resolution curve (z = 1.0 / 1.645 / 1.96 / 2.576)。
- **target 命名**: Gate 1 闭合前统一称 `designated computational target/reference`, 禁用 `validated target`。

---

## 3. 数据集冻结

| 层 | 文件 | N | 计算深度 |
|---|---|---|---|
| Core paired benchmark set | `data/metadata/core_set.csv` | 18 | `P0` + `P1` + `P2` + `C1` |
| Broad cheap pool | `data/metadata/broad_pool.csv` | 40 | 廉价结构 descriptor + xTB (`P0`) |

- Core set family 覆盖: `linear_carbonate(3)`, `cyclic_carbonate(4)`, `ether(3)`,
  `ester(3)`, `sulfone(1)`, `sulfoxide(1)`, `nitrile(2)`, `phosphate(1)`;
  含 3 个机理对照分子: `FEC (C06)`, `VC (C07)`, `SN (C18)`。
- Broad pool 额外引入 `sulfite`, `sultone`, `siloxane` 三个家族。
- 两个 CSV 共享同一列定义 (core 用 `reason_included`, pool 用 `pool_reason`)。
- **CSV 是产物**: 由 `scripts/build_metadata.py` 从内嵌结构表确定性重建, 不手工编辑。
- 多轴标签 (family / donor 类型 / 氟化度 / 柔性 / 拓扑 / 用途) 见
  `data/metadata/chemical_space_metadata.md`; 其中氟化**不是** family。

---

## 4. 预注册冻结 (摘要)

完整内容见 `config/prereg.yaml`。

- **Top-k**: `k/N = 10%, 20%, 30%`; 绝对值为 `k = max(1, round(frac * N))`,
  core set (N=18) => `k = 2, 4, 5`; broad pool (N=40) => `k = 4, 8, 12`。
- **Pair tolerance**: `|dP_ij| < delta_m` 或 `|dP_ij| < z * sigma_ij` => `unresolved/tied`;
  `z = 1.0`; `delta_m` 的来源规则按 (1) 实验离散度 -> (2) method audit 离散度 ->
  (3) 预注册默认值 `2.0 kJ/mol` 的顺序取第一条可用者, 具体数值在 Gate 1 冻结。
- **Robust inversion**: 两侧都解析且符号相反, 且两侧 separation 均超过各自阈值;
  分母是"两侧都被解析"的 pair 数。必须同时报告 `f_unresolved`。
- **Bootstrap**: `2000` 次, 95% percentile CI。
- **随机种子**: 固定 20 个 (`101` 到 `2003` 的素数序列), 冻结后只能追加不能增删。
- **决策阈值来源规则**: `T` 只能来自外部设计要求 / 实验基准 / 事先定义的工程标准;
  严禁看完数据后挑最有利阈值; 无合规来源则报告 `not_applicable`。
- **数据拆分**: random (5 个固定 seed) + group/scaffold + LOFO (core 8 folds), 三者必须同时报告。
- **Feature cost**: 每个 ML 表格必须含 `feature_cost_level` (`X0/X1/X2`);
  依赖 `X2` 的 acquisition 不得用于证明"低成本预测"。
- **冻结声明**: 上述各项在查看任何 ranking / inversion / Top-k 结果之前冻结,
  冻结后不得因看到数据而修改; 任何修改必须 append-only 记入 `amendment_log`。

---

## 5. Gate 0 判据

Gate 0 是**可判定**的检查: 以下每一条都必须为"是"才能进入 Stage 1。

| # | 判据 | 判定方式 |
|---|---|---|
| G0-1 | 目标量 (oxidation / reduction) 已定义, 且各自带 `objective_direction` | `config/scientific_definitions.yaml` 的 `objectives` 非空且方向明确 |
| G0-2 | 筛选方向不被代码默认化 | 代码中不存在"所有指标越大越好"的隐含假设; 指标函数必须显式接收方向 |
| G0-3 | family 定义为受控闭集, 且氟化未被当作 family | `controlled_vocabularies.family` 存在; 数据中不存在 `fluoroether` 等平行族 |
| G0-4 | core set 覆盖所有目标 family 与 2-3 个机理对照分子 | `core_set.csv` 有 18 行 8 个 family, 且含 C06/C07/C18 |
| G0-5 | broad pool 建立且只用廉价层 | `broad_pool.csv` 有 40 行, 且仅声明 `P0` |
| G0-6 | 所有 SMILES 可解析 | `python scripts/build_metadata.py --check` 通过 (RDKit 路径) |
| G0-7 | 有/无 RDKit 时产物一致 (可复现) | `python scripts/build_metadata.py --check --no-rdkit` 通过 |
| G0-8 | CSV 与内嵌结构表一致 (幂等) | 连续两次 `--check` 均为 `OK` |
| G0-9 | k 值已预注册 | `prereg.yaml` 的 `top_k.fractions = [0.10, 0.20, 0.30]` |
| G0-10 | pair tolerance 与 `delta_m` 的来源规则已冻结 | `prereg.yaml` 的 `pair_comparison.delta_m.source_rule` 非空 |
| G0-11 | bootstrap 重复次数与随机种子列表已冻结 | `uncertainty.bootstrap.repetitions` 与 `uncertainty.random_seeds` (20 个) 非空 |
| G0-12 | 决策阈值来源规则已冻结 | `threshold_decisions.source_rule` 非空且含禁止条款 |
| G0-13 | reference ligand R 已冻结并给出理由 | `reference_ligand.primary_R` = DME, 且 `rationale` 与 `excluded_alternatives` 非空 |
| G0-14 | 标准态 / 温度 / 参考电极约定已冻结 | `thermochemistry` 三项齐备 |
| G0-15 | 存在"看结果前冻结、不得看数据后修改"的书面声明 | `prereg.yaml` 的 `freeze_statement` 存在 |

> 判定命令见第 6 节。任何一条为"否", 即 **Gate 0 未通过**, 不得进入 Stage 1 的
> method audit 与 external anchor 搜集。

---

## 6. 复现与判定命令

`~powershell
# 1) 重建两个 CSV (幂等)
.\.venv\Scripts\python.exe scripts\build_metadata.py

# 2) 一致性校验: 不写文件, 只比较; 不一致则以非零码退出
.\.venv\Scripts\python.exe scripts\build_metadata.py --check

# 3) 无 RDKit 的 fallback 路径也必须一致 (CI 用)
.\.venv\Scripts\python.exe scripts\build_metadata.py --check --no-rdkit

# 4) family 覆盖统计
.\.venv\Scripts\python.exe scripts\build_metadata.py --summary

# 5) YAML 语法校验
.\.venv\Scripts\python.exe -c "import yaml;[yaml.safe_load(open(p,encoding='utf-8')) for p in ['config/scientific_definitions.yaml','config/prereg.yaml']];print('YAML OK')"
`~

判定: 命令 2、3 均输出 `[ OK ]` 且退出码为 `0`, 即 G0-6 / G0-7 / G0-8 通过。

---

## 7. 冻结后的变更流程

1. 任何对 family 定义、目标量、筛选方向、k 值、tolerance、阈值来源、R ligand 的修改,
   都属于**违反 Gate 0 的静默修改**, 禁止直接改文件。
2. 允许的路径: 在 `config/prereg.yaml` 的 `amendment_log` 中 **追加** 一条记录,
   写明时间、修改项、旧值、新值、理由与触发它的事实依据; 历史条目不得删除或改写。
3. 修改后必须重跑第 6 节全部命令, 并把新的判定结果记录在本文件末尾的变更记录中。

### 变更记录

| 日期 | 变更 | 依据 |
|---|---|---|
| 2026-09-29 | 初始冻结 (本文件) | Stage 0 收口 |

---

## 8. 相关文件清单

| 文件 | 作用 |
|---|---|
| `config/scientific_definitions.yaml` | 冻结的 P0/P1/P2, C0/C1/C2, R_gas/R_sol/R_env, 目标量方向, 标准态/温度/参考电极, reference ligand R, 受控词表 |
| `config/prereg.yaml` | 预注册: k 值, pair tolerance 与 `delta_m`, bootstrap 与随机种子, 决策阈值来源规则, 拆分, feature cost, AL 协议, 冻结声明 |
| `data/metadata/core_set.csv` | core paired benchmark set, 18 行 (产物) |
| `data/metadata/broad_pool.csv` | broad cheap pool, 40 行 (产物) |
| `data/metadata/chemical_space_metadata.md` | 多轴 chemical-space 标签体系与两层选择原则 |
| `scripts/build_metadata.py` | 确定性重建两个 CSV, 提供 `--check` / `--no-rdkit` / `--summary` / `--dump-fallback` |
| `docs/00_stage0_definitions.md` | 本文件 |
