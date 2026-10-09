# Week 28 / WP1：统一科学证据主表

**阶段**：下一阶段（评审实施方案）工作包 **WP1**
**唯一变量 / 新增计算**：**零新增电子结构计算**。本阶段只做整理、口径冻结与一致性审计，全部数值来自 Week 1–27 的冻结产物。
**产物目录**：`outputs/week28/`（仓库内）；交付镜像 `..\成果输出（part2）\week28/`（仓库外）
**生成器**：`scripts/build_week28_evidence_table.py`（确定性；`--check` 逐字节复核）
**测试**：`tests/test_week28_evidence_table.py`（10 项）

---

## 0. 一句话结论

把 Week 1–27 散落各处的物理量、状态身份、排序指标与计算成本收敛成**六张主表**（共 2074 行），
每一行都能追到明确的 `molecule x model x charge state x motif` 与**具体来源字段**；并且在
`all` scope / `z_only` / `z = 1.0` 下**逐位复现**了 Week 6 已冻结的 pair 数字
（354 个 pair，最大绝对误差 `0.000e+00` eV），证明这张主表是已发表数字的**同一个对象**，
而不是并行的一套定义。

这一条是本阶段最重要的事实：下一次有人认为主表与旧结论不一致时，可以直接跑
`--check` 与 `frozen_number_reproduction` 来定位，而不必靠记忆。

---

## 1. 为什么先做这一件事

评审把下一阶段定义为 WP1 → WP7，并明确「回到 v2 的材料筛选科学问题，利用现有结果补齐机制、
决策与信息预算的证据链」，而不是继续第四轮对抗审计。WP1 是其余六个工作包的**共同前提**：
在证据本身没有被整理成一张可引用、可版本冻结、可机器复核的表之前，WP2 的位移分解、
WP3 的 state-identity 机制、WP4 的决策可靠性都只能各自重算一遍，必然出现口径漂移。

因此 WP1 的验收标准不是「跑出新的结论」，而是：
**所有主文数字都能追溯到明确的分子、模型、状态与原始计算记录，且不把缺失样本强行补齐。**

---

## 2. 六张主表

| 表 | 行数 | 内容 |
| --- | --- | --- |
| `molecule_registry` | 58 | 化学空间：core 18 + broad 40，含 family / role / donor / 官能化标签 |
| `state_registry` | 242 | 每个计算对象的电荷、多重度、化学计量、motif、QC 状态与 state identity |
| `property_table` | 392 | 每个 `(对象, rung, 轴)` 的统一物理目标、数值、`value_status` 与来源字段 |
| `pairwise_table` | 1326 | 每个 `(i, j, 对比, scope, 轴)` 的 `d_lower` / `d_upper` / `sigma_ij` / 掩码 / `decision_state` |
| `decision_table` | 45 | 每个 `(对比, scope, 轴, k)` 的 Top-k overlap、Jaccard、selection regret 与三态构成 |
| `cost_table` | 11 | 每个 rung 的 feature availability、对象数、wall seconds、失败数 |

rung 注册表（R13 命名，逐条写清「模型」是什么）：

| rung | 目标定义 | 几何策略 | 溶剂 | 代价 |
| --- | --- | --- | --- | --- |
| `P0` | GFN2-xTB Koopmans 轨道能代理 | G1 共享几何 | 气相 | 廉价 |
| `P1v` | r2SCAN-3c 气相**垂直** redox（三态同一几何） | G1 共享 | 气相 | 昂贵 |
| `P1a` | r2SCAN-3c 气相**绝热** redox（逐电荷态弛豫） | G2（逐态 Opt） | 气相 | 昂贵 |
| `P2a` | 固定连续介质目标 CPCM(SMD, acetonitrile) | G1 | SMD 乙腈 | 昂贵 |
| `P2eps@ε` | bare CPCM 纯介电扫描 ε = 5 / 10 / 20 / 40 | G1 | bare CPCM | 昂贵 |
| `C0` | 自由分子在 G2 几何上的垂直单点 | G2 | 气相 | 昂贵 |
| `C1` | 条件态 `[LiM]+`（主 motif） | 优化后的复合物几何 | 气相 | 昂贵 |
| `C2` | 第一溶剂壳 `[Li(M)2]+`（配位数 2） | 优化后的 1:2 复合物 | 气相 | 昂贵 |

两个 scope：
`all` 不做 state-identity 过滤（Week 5/6 原始口径，只用于复核）；`primary` 是 R13 口径，
C1/C2 的还原轴只让 `molecule_centered_redox` 进入主 ranking。
当某对比不含条件态 rung、或两者候选集合相同时只输出 `all` 行（此时「没有 primary 行」≡「primary 与 all 相同」）。

---

## 3. 四项必查结论（评审指定）+ 两项附加

| check | 结论 | 关键数字 |
| --- | --- | --- |
| `provenance_completeness` | **PASS** | 392 property 行全部带 `source_file` + `source_field`；0 个来源文件缺失 |
| `same_target_quantity` | **PASS** | 1326 pair 行全部用（`IP` / `-EA`, eV, maximise）；没有任何 `molecule x 轴` 在不同 rung 间混用目标量 |
| `p1v_vs_p1a_distinct` | **PASS** | 定义层几何策略与热化学都不同；经验层 12 个共同分子 `\|IP(P1a)-IP(P1v)\| > 0` **全部成立**，中位 0.3181 eV、最大 0.9503 eV，且**全部为负**（绝热弛豫降低 IP） |
| `li_centered_not_misused_as_molecular` | **PASS** | C1 的 10 个候选里只有 **SN** 通过还原轴闸门；另外 9 个 Li-centered/mixed 被排除出 `primary`；旧 `all` scope 的还原排序 `tau_b = -0.4667` |
| `status_vocabulary_separated`（附加） | **PASS** | `value_status` 只用 `ok / missing / not_converged / not_applicable`；`UNRESOLVED` 只作 pair 层 `decision_state`，从不进 `value_status` |
| `frozen_number_reproduction`（附加） | **PASS** | 逐位复现 Week 6 的 6 组 stored pair（最大误差 `0.000e+00` eV，354 个 pair，mask 不一致 0）；并用 `tau_b`/`spearman` 复核 Week 4 的 4 组 P2a 数值 |

### 3.1 `li_centered_not_misused_as_molecular` 为什么不是空检查

初版这个 check 是空洞的：`primary` scope 下还原轴的候选只剩 1 个，无法构成 pair，
于是「误用」集合天生为空。现在的版本改为直接在 **rung 层**验证闸门：

- C1 的 10 个候选 → 通过还原轴闸门的只有 `SN`；
- 被排除的 9 个与 stratification 里的 `Li_centered_or_mixed_redox` 集合逐一对应；
- 反面对照：把 `all` scope 的还原排序算出来，`tau_b(C0 → C1) = -0.4667` —— 也就是说
  若不加闸门，这条「分子还原」排序轴与自由分子的还原性呈**负相关**，
  因为该轴上测的其实是 Li 上的电子局域化。这正是 R13 要防的那个错误。

---

## 4. 本阶段确认的七个口径事实（均带机器可查证据）

1. **P1a 只有氧化轴。** `unbound_anion` 规则（`config/scientific_definitions.yaml:P1a.failure_rule`）
   把 P1a 的还原轴整体排除：主表里 12 行 `value_status = not_applicable`，`value` 为空，
   **不是 `missing`、也不是 0**。P1v 侧 18 个分子的 `ea_r2scan3c_bound` 全为 `False`，与之一致。
2. **C1/C2 还原轴的 `primary` ranking 只剩分子中心还原。** stratification 中
   `molecule_centered_redox` 的还原对象仅 `SN`；其余 9 个 Li-centered/mixed 对象仍在表中，
   但只以 `all` scope 存在。
3. **`ROBUST_INVERSION` 在 `z = 1.0` 下结构性不可检验。** `sigma_ij` 由两个模型共同定义，
   反向 pair 两侧同时过门槛需要 `z <= 1/√2 = 0.7071`；因此 `f_robust_inv = 0` **不是**排序稳定的
   证据。`pairwise_table.structurally_non_testable` 逐行标注，全部 1326 行为 `True`。
4. **`P2` 在仓库里有两套同名含义。** Week 4 的 `p2_decision_stability.json` 把 “P2” 记为
   CPCM(SMD, acetonitrile)，Week 6 的 `analyze_stage6.py` 把 “P2” 记为 bare CPCM ε=10。
   两者各自正确但同名，跨周引用必踩坑。R13 的 `P2a` / `P2eps` 拆分消除歧义：主表分别登记为
   `P2a` 与 `P2eps@10.0`，Week 6 的 `P1_to_P2` 对应 `P1v_to_P2eps10`。该映射已用 `tau_b` 复核。
5. **信息覆盖度显著不对称。** 廉价层声明覆盖 58 个分子，昂贵层只到 18（`P1v`/`P2a`）
   或 10–12（`P1a`/`C0`/`C1`/`C2`/`P2eps`）。主表把 broad pool 的 P0 也登记进来
   （40 分子 × 2 轴 = 80 行显式 `missing`），因此 WP4/WP6 的信息预算可以直接从
   `cost_table` 读覆盖度，不必翻各周目录。

6. **`scope='all'` 的分母随对比变化。** `n_molecules` 是「两个 rung 都有 ok 数值」的分子数，
   本阶段为 18（P0/P1v/P2a 系）、12（P1a / P2eps / C0）、10（C0→C1、C1→C2）。因此
   `decision_table` 里 `f_unresolved` / `jaccard` / `overlap` **跨行不可比**，每行都带
   `common_set_label`（`core18` / `audit12` / `subsetNN` / `single_candidate`）作为分母标签，
   JSON 的 `coverage` 块给出 declared / available / used 三者对账。
7. **`C1` 的声明范围是 core 18，实际只做到 10。** `config/scientific_definitions.yaml:dataset.core_set.purpose`
   明写 core set「完成 P0 / P1 / P2 以及 C1 conditional Li-coordination」，但仓库里 C1 只有 10 个分子
   （`PC` / `EMC` 没有 `[LiM]+` 对象）。这 8 个缺口在主表里是 `missing`（16 行），不是被静默丢掉。
   `coverage.C0_to_C1.oxidation` 给出：声明交集 12、实际可得 10、`unavailable_declared = ["EMC", "PC"]`。
   **这是下一阶段扩充计算时最应该先补的地方。**

---

## 4.1 独立复核（免费车道子智能体，只读）

主表另做过一次**独立复核**：一个只读子智能体在不知道生成代码结论的情况下自行重算。数值层面全部对上：

| 复核项 | 独立重算结果 |
| --- | --- |
| `sigma_ev = abs(d_lower - d_upper) / sqrt(2)`（P0_to_P1v / oxidation / all，153 行） | 与表内 `sigma_ev` 最大绝对误差 `4.44e-16`（浮点噪声）；`resolved` 判据不一致 0 行 |
| 对 Week 6 的 `z_only.P0_to_P1.oxidation`（66 个 pair） | 66/66 全部可见；最大绝对误差 `d_lower` 2.22e-16 / `d_upper` 4.44e-16 / `sigma` 1.11e-16 |
| P1a 还原轴 | 12 行全部 `not_applicable`、`value` 全空 |
| C1/C2 还原轴 `in_primary_ranking=True` | 只有 `SN`（C1 −3.207882 eV、C2 −2.818096 eV），标签均 `molecule_centered_redox` |
| 状态一致性 | `ok` 但值为空 0 行；非 `ok` 却有数值 0 行；`UNRESOLVED` 不出现在 `value_status` |

它提出的两条质疑已被采纳并修正：

- **方向/符号**：`pairwise_table` 按字母序排 `i`/`j`，与 Week 6 的存储顺序可能相反（24 个 pair 反向并整体取负）。
  已在数据字典 §5.3 写明；`frozen_number_reproduction` 用 Week 6 自己的顺序，因此仍是逐位相等。
- **分母与声明范围不一致**：`declared_scope.C1` 原写作 12，与冻结声明（core 18）不符。
  已改为 18，并补 `declared_scope_source` 出处与 `coverage` 对账块（即事实 6、7）。

另有一处**本报告自身的数字勘误**（结题提交复核时发现）：§0 与 §2 原写「共 2062 行 / `property_table` 380 行」，§5 原只列 8 个 rung，均是早期快照。冻结载荷 `outputs/week28/evidence_master_table.json` 实为**2074 行、`property_table` 392 行、11 个 rung**（多出 `P2eps@5.0` / `@20.0` / `@40.0`，每个 rung 24 行）。本报告已按载荷改正；载荷本身与 `--check` 未做任何改动。

---

## 5. 逐个 rung 的候选与成本

| rung | 代价 | 分子数 | property 行 | ok | missing | not_applicable | QC 标记 | 失败作业 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `P0` | 廉价 | 58 | 116 | 36 | 80 | 0 | 0 | 0 |
| `P1v` | 昂贵 | 18 | 36 | 36 | 0 | 0 | 0 | 0 |
| `P1a` | 昂贵 | 12 | 24 | 12 | 0 | 12 | 0 | 0 |
| `P2a` | 昂贵 | 18 | 36 | 36 | 0 | 0 | 0 | 0 |
| `C0` | 昂贵 | 12 | 24 | 24 | 0 | 0 | 4 | 0 |
| `C1` | 昂贵 | 18 | 36 | 20 | 16 | 0 | 14 | 1 |
| `C2` | 昂贵 | 12 | 24 | 20 | 4 | 0 | 14 | 0 |
| `P2eps@5.0` | 昂贵 | 12 | 24 | 24 | 0 | 0 | 0 | 0 |
| `P2eps@10.0` | 昂贵 | 12 | 24 | 24 | 0 | 0 | 0 | 0 |
| `P2eps@20.0` | 昂贵 | 12 | 24 | 24 | 0 | 0 | 0 | 0 |
| `P2eps@40.0` | 昂贵 | 12 | 24 | 24 | 0 | 0 | 0 | 0 |

`wall_seconds` 一栏见 `cost_table.csv` 与 `wall_seconds_note`：`P0` 与 `P1a` 的来源蒸馏表
**没有**记录 wall time，那里的 `0.0` 表示「未记录」，不是「零成本」。

---

## 6. QC / 限制（必须与结论一起读）

- **不新增计算，因此不解决 Gate 1。** Gate 1 仍是 **NOT CLOSED**；本阶段只保证证据链可追溯，
  不提供任何外部有效性支持。`target_naming` 仍为 `designated computational target/reference`。
- **`not_converged` 目前零命中。** 词表四类齐备，但实际只用到 `ok / missing / not_applicable`。
  `C1` 的 1 个失败作业落在**非主 motif** 行上，不影响判据。这本身是一条覆盖度事实：
  主表所依赖的蒸馏产物里没有「跑过但没收敛」的主候选。
- **pair 不确定度只有两个 realization（A/B）。** `sigma_ij` 是 two-arm 定义，无法估计
  realization 数目本身带来的不确定度；`resolution_curve` 与 `f_unresolved(z)` 只能在该定义下读。
- **小样本。** 昂贵层 n = 18 / 12 / 10，`primary` scope 下 C0→C1 与 C1→C2 只有 6 个候选、
  15 个 pair。主表只给点估计；bootstrap 区间沿用各周产物，不在本阶段重算。
- **`primary` scope 的还原轴无法构成 pair。** `C0_to_C1` 与 `C1_to_C2` 的还原轴在闸门后只剩
  1 个候选，主表对这些组合显式给出 `skipped`，**不得**读成「稳定」或「零反转」。
- **`all` scope 里的 Li-centered 数据不是结论。** 它只用于复核 Week 5/6 的冻结数字。
- **`state_registry` 的 G2 组只有 derived 数值。** `outputs/week4/t2_opt_freq.csv` 只存
  折算后的 `ip_g2_ev` / `ea_g2_ev`，没有逐态能量，因此这几行标 `energy_availability = derived_only`。
- **`state_registry` 的 C1/C2 组有重复行（未携带上游 `job` 相位）。** 上游 `outputs/week5/c1_li_coordination.csv` 对同一 `(分子, motif, 电荷态)` 同时存有 `opt` 与 `sp` 两条记录（`final_energy_eh` 不同），而本表 schema 没有保留 `job` 字段，投影后成为无法区分的重复行：242 行里只有 186 个唯一 `state_id`（36 组重复），其中 51 行与另一行逐字段完全相同。该重复**不改变任何排序数字**（`property_table` 的 C1 取自 `c1_coord_shifts.csv`，键唯一；pair 构建只取双侧 `ok` 的行），但「每行对应一个可辨识计算对象」这一读法在 C1/C2 组需按本保留读。结构性修法（在 `state_registry` 增设 `job` 相位判别列并写进 `state_id`）已登记为后续改进，本阶段不改动冻结表。

---

## 7. 产物文件

| 文件 | 说明 |
| --- | --- |
| `outputs/week28/molecule_registry.csv` | 化学空间 |
| `outputs/week28/state_registry.csv` | 计算对象与 state identity |
| `outputs/week28/property_table.csv` | 统一物理目标与数值 |
| `outputs/week28/pairwise_table.csv` | pair 差、`sigma_ij`、三态判据 |
| `outputs/week28/decision_table.csv` | Top-k / regret / 决策指标 |
| `outputs/week28/cost_table.csv` | 覆盖度与成本 |
| `outputs/week28/evidence_master_table.json` | 全量载荷（含六项 check 的机器可读证据） |
| `outputs/week28/evidence_master_table.md` | 汇总报告 |
| `outputs/week28/data_dictionary.md` | 数据字典（由 schema 生成，保证与表同步） |
| `outputs/week28/sample_flow.md` | 样本流转图（mermaid）+ 被规则挡掉的样本 |
| `outputs/week28/manifest.json` | 逐表行数与 SHA256 |

---

## 8. 交付层

对外交付镜像写入与代码仓库并列的 **`E:\Claude Code\电解液溶剂-HB\成果输出（part2）\week28\`**
（part1 覆盖 week1–week25，part2 从本阶段起）。镜像内保持仓库相对路径、附 `SHA256SUMS`、
`verification.json` 与中文 `README.md`；不镜像任何 ORCA / xTB 原始输出与二进制 scratch。

```powershell
.venv\Scripts\python.exe scripts\build_week28_evidence_table.py
.venv\Scripts\python.exe scripts\build_week28_evidence_table.py --check
.venv\Scripts\python.exe -m pytest tests/test_week28_evidence_table.py -q
.venv\Scripts\python.exe scripts\build_week28_deliverables.py
.venv\Scripts\python.exe scripts\build_week28_deliverables.py --check
```

---

## 9. 交给 WP2–WP4 的接口

- **WP2**（哪些物理改变排序）：直接用 `pairwise_table` / `decision_table` 的两个 scope；
  位移分解用 `pairwise_table.delta_shift_ev`（= `δ_i - δ_j`，差异性响应）。
- **WP3**（Li⁺ 配位机制）：用 `state_registry` + `property_table.in_primary_ranking`
  组织 C0/C1/C2 机制案例；`docs/state_identity_protocol.md` 是闸门定义。
- **WP4**（决策可靠性）：用 `decision_table` 的 Top-k / regret 与 `pairwise_table` 的
  分辨率列；注意 `structurally_non_testable` 的代数约束。
- **WP5/WP6**（信息预算）：`cost_table.feature_availability` 是硬约束——预测 C1 时
  不得把必须完成 C1 计算后才得到的量当廉价输入。