# WP1 还原态三项检查 —— 协议登记（先登记、未计算）

> 本文件只是 **协议登记**：把方案 §5.1 对还原态的「电子空间扩展 / 脱附稳定性 / 波函数身份」三项检查
> 写成可操作判据，并说明每一项**现在能否从已有产物算出**、哪些**必须先补一条还原腿**。
> 本轮 **未运行任何电子结构计算**（机器被生产作业占用，不排队、不调用 ORCA / xTB / DFT）；
> 文中所有尚未产生的数值一律写「尚未计算」，不预填、不外推。
>
> 触发来源：合规台账 `outputs/physics_completion/compliance/plan_compliance.csv` 的
> `wp1_reduction_state_checks` 行 = `exempt`，`has_reduced_leg=False`，`eligible_reduction_objects=0`。
> `exempt` 仅表示本批次按 `unbound_anion` 规则没有可执行对象、因此不计入未闭合项；它不表示三项检查通过。
> 方案原话：「还原必须使用含弥散函数的设定，并检查电子空间扩展、脱附稳定性和波函数身份。
> 有限基组能收敛不能证明束缚，旧 unbound 标记是历史 QC 决定，不是所有方法下的普适物理结论。」

## 0. 范围与纪律

- 这是新批次 `physics_completion_v1` 的登记件，append-only，不改写 `config/scientific_definitions.yaml`、
  不改 `data/metadata/physics_completion_set.csv`（冻结）、不覆写任何历史产物或结论。
- 判据、阈值、基组规则在**结果产生前**登记；不按结果反推、不按翻转数选方法。
- 本文件不承诺任何尚不可证的结论；「未做」显式记为未做，而不是默认通过。

## 1. 固定条件与基组/弥散设定

沿用 WP1 冻结条件（见 `docs/59_week38_wp1_method_audit.md` 与 `docs/66_wp1_production_method_freeze.md`）：

- 溶剂模型：SMD 乙腈；温度 298.15 K；溶液标准态 1 mol/L；几何起点 r2SCAN-3c。
- 方法矩阵四个设定：

  | 设定 | 泛函 | 基组 | 含弥散 |
  |---|---|---|---|
  | S1 | wB97X-D4 | def2-TZVP | 否 |
  | **S2** | **wB97X-D4** | **def2-TZVPD** | **是（生产 / target-label）** |
  | S3 | PBE0-D4 | def2-TZVP | 否 |
  | **S4** | **(PBE0-D4)** | **def2-TZVPD** | **是（审计对照）** |

- **还原态必须使用含弥散函数的设定（S2 生产 / S4 对照）**。无弥散设定（S1/S3）的还原格即使收敛，
  也标 `valid_for_decision=false` 并排除出决策统计——这与方法审计里 32 个无弥散还原格的处理一致。
- 判据是「有限基组能收敛 **不** 证明束缚」：无弥散基组下的阴离子极小可能只是伪束缚痕迹。
- 旧 `unbound_anion` 标记（`outputs/week4/p1_core_set_audit.json`，气相 r2SCAN-3c，18/18）
  记录为**历史 QC 决定**，对每个新方法必须重新测量，不跨方法继承。

## 2. 三项检查的**可操作判据**

三项检查共用同一个还原腿（reduced leg）：母态 M（中性）与还原态 M⁻（自由基阴离子，多自旋二重态），
在同一 SMD 乙腈、同一几何层级下用含弥散设定分别计算。判据如下。

### 2.1 电子空间扩展（electronic spatial extent）

- **看什么量**：额外电子（对二重态即自旋密度）在空间上的展宽，以及相对分子自身尺寸的归一化展宽。
  可直接取材于本仓库已定义的描述符族（见 `outputs/week14/stage15_diffuseness.json` 的
  `descriptor_definitions`）：
  - `spin_extent_ang2 = Σ|s_i|·|r_i − CM|² / Σ|s_i|`（自旋密度二阶矩，CM = 质心）
  - `spin_rms_ang = sqrt(spin_extent_ang2)`
  - `spin_maxfrac = max|s_i|`（单原子最大自旋份额）
  - `spin_participation = 1 / Σ s_i²`（逆参与比，越大越离域）
  - `spin_extent_norm = spin_extent_ang2 / <r²>_mass`（相对分子自身尺寸的归一化）
  - `chg_extent_ang2` / `chg_extent_norm`（用 `q_anion − q_neutral` 权重的同类二阶矩）
- **可操作判据（待冻结）**：若额外电子几乎落在单个原子上（`spin_maxfrac` 高于冻结阈值）且
  `spin_extent_norm` 低于冻结阈值 → 判为**分子中心、局域**；若自旋/电荷展宽远超分子自身尺寸、
  或未成对自旋离域到分子之外（弥散/溶剂束缚） → 判为**非分子中心**，按状态身份结果单列，
  不进入主 ranking。
- **与状态身份挂钩**：`state_identity_label != molecule_centered_redox` 的态一律记为 identity outcome，
  不强行拼排序（与协议 §2「只有 molecule_centered_redox 进入主 ranking」一致）。

### 2.2 脱附稳定性（detachment stability）

- **看什么量**：还原态相对母态的电子脱附能差 `ΔE_det = E(M) − E(M⁻) = −EA`。
  按统一约定，`EA_dscf = E(M⁻) − E(M)`：**负值 = 阴离子在母态之下 = 束缚**；正值 = 不束缚。
  方向语义与协议 `Sred = −EA`（maximize）一致。
- **可操作判据（待冻结）**：
  1. 只在含弥散设定（S2/S4）上取判定；无弥散格 `valid_for_decision=false`。
  2. 要求在**预先接受的方法设定上符号一致**，且 `|ΔE_det|` 超过该腿的方法展宽才判 bound/unbound；
     符号不稳定或与展宽相当 → 记 `unresolved`。
  3. 与无弥散腿对照：**只有无弥散基组给出束缚**时判为有限基组伪束缚（不束缚）。
  4. 判定在**固定 SMD 乙腈条件**下定义（溶剂稳定阴离子）；气相值只作 anchor 单列，
     不把气相 bound/unbound 直接当作溶液结论。
- **历史锚点的正确用法**：旧 `unbound_anion=18/18`（气相、无弥散）与 `t5_diffuse_control`（4 分子）
  只作方向与量级的旁证，**不**等于冻结方法下的普适结论。

### 2.3 波函数身份（wavefunction identity）

- **看什么量**（SCF 解身份 + 电子态身份）：
  - `<S²>`（自旋污染；二重态理想 0.75），超出冻结容差则报警；
  - 优化后还原态的**连接关系/母键是否完整**（`parent_bonds_intact`）、碎片电荷/自旋；
  - 前沿/自旋轨道**局域位置**：额外电子落在目标给体/氧化还原中心，还是落到 Li⁺ 或溶剂（`top_spin_carriers`、
    `spin_molecule_state` vs `spin_li_state`，见 `outputs/week5/c1_state_identity.csv` 的字段）；
  - SCF **解身份**：默认初猜解与 `MORead` 重启解是否同一根（重启落到更低/不同解 = 身份风险，
    见 `outputs/week15/stage16_*`）。
- **可操作判据（待冻结）**：还原态进入主还原 ranking，当且仅当
  `state_identity_label == molecule_centered_redox` **且**母键完整 **且** `<S²>` 在冻结容差内 **且**
  自旋/电荷局域在目标分子上。否则记 identity outcome，与 intact / Li-centered / mixed / ambiguous /
  fragmented 分开表（与 §6.3 身份分层一致）。

## 3. 现在能算 vs 必须先补还原腿

以「是否已有产物可用于该判据」为界，不用「允许」把缺口说成完成。

| 检查 | 现在能从已有产物读到的 | 必须先补还原腿才能算的 |
|---|---|---|
| 电子空间扩展 | **可读**：`outputs/week14/stage15_diffuseness.json` 已给出 12 个分子的自旋/电荷二阶矩描述符（气相 + CPCM 层） | **缺**：冻结生产方法（S2/S4，SMD 乙腈，生产几何）下的 M⁻ 自旋/电荷展宽——尚未计算 |
| 脱附稳定性 | **部分可读**：气相符号 `p1_core_set_derived.csv:ea_r2scan3c_bound`；气相无弥散 `p1_core_set_audit.json`；4 分子弥散对照 `t5_diffuse_control_*`；SMD 溶剂相符号 `p2_core_set_smd_acetonitrile.csv`（r2SCAN-3c，无弥散） | **缺**：含弥散、S2（+S4）设定下、SMD 乙腈、生产几何的 M/M⁻ 脱附腿——尚未计算；这正是 `has_reduced_leg=False` 指的缺口 |
| 波函数身份 | **部分可读**：`<S²>`（`t5_diffuse_control_*`，AN/DMSO/SN/VC ≈0.75）；还原/配位态身份标签 `outputs/week5/c1_state_identity.csv`（12 行 reduced）；SCF 解身份诊断 `outputs/week15/stage16_*` | **缺**：生产还原腿的母键完整性、前沿局域、`<S²>`、fragment 电荷/自旋；且 `frontier localization` 在 `thresholds.json` 记 `not_computed` |

小结：**三项检查的判定都需要一条含弥散的生产还原腿**；已有产物只覆盖它在气相 / 无弥散 / 旧方法
（r2SCAN-3c）下的旁证级版本。因此本行保持 `not_satisfied`，直到新还原腿产出并逐项复核。

## 4. 可复用的还原相关产物清单（逐条）

以下路径均已存在于盘上，可**只读复用**；「可否复用」按判据口径标注。

| 路径 | 内容 | 与三项检查的关系 | 可否复用 |
|---|---|---|---|
| `outputs/week4/p1_core_set_audit.json` | 气相 r2SCAN-3c QC 审计；`unbound_anion=18`（18 个分子） | 脱附稳定性（历史 QC 决定） | 仅作历史标志；**不可**直接当冻结方法结论 |
| `outputs/week4/p1_core_set_derived.csv` | 18 分子气相派生量，含 `ea_r2scan3c_ev`、`ea_r2scan3c_bound` | 脱附稳定性（气相符号） | 可作气相 anchor；无弥散，不作生产判定 |
| `outputs/week4/p2_core_set_smd_acetonitrile.csv` | 18 分子 neutral/cation/anion 能量，SMD 乙腈（r2SCAN-3c，无弥散） | 脱附稳定性（溶剂相符号） | 可读溶剂相符号；无弥散，需新腿复核 |
| `outputs/week4/t5_diffuse_control_summary.json` / `.csv` | AN/DMSO/SN/VC 的弥散对照（def2-TZVPP / def2-TZVPD / r2SCAN-3c），含 `anion_s_squared`、`flip_to_bound_with_diffuse` | 电子空间扩展 + 脱附稳定性（弥散方向）+ 波函数身份（`<S²>`） | 可复用方向与量级；仅 4 分子、气相 |
| `outputs/week14/stage15_diffuseness.json` | 12 分子自旋/电荷空间展宽描述符（气相 + cpcm_5..200） | 电子空间扩展 | **可复用**为现成的空间展宽口径；方法/几何为旧层级 |
| `outputs/week15/p2_core_set_holdout_cpcm_{5,20,200}.csv`、`outputs/week15/orca_holdout_cpcm_*` | 留出集 DEC/EA/FEC/MA/TEGDME/VC（+主集）阴/中/阳离子 CPCM 能量，default 与 `MORead` 两臂（r2SCAN-3c，无弥散） | 脱附稳定性（溶剂相）+ 波函数身份（SCF 解身份） | 可读扩展池分子的溶剂相阴离子数据；无弥散 |
| `outputs/week15/stage16_holdout.json`、`outputs/week15/stage16_catalogue*.json` | SCF 解身份（default vs `MORead`）与气相自旋描述符 | 波函数身份（SCF 解身份） | **可复用**为解身份诊断口径 |
| `outputs/week5/c1_state_identity.csv` | 配位/还原态身份标签、`spin_li_state`、`spin_molecule_state`、`li_min_distance_a`、`top_spin_carriers` | 波函数身份（分子中心 vs Li 中心） | **可复用**为身份分层口径（覆盖 12 reduced 行） |
| `outputs/week25/gate1_reduction_secondary.md` / `.json` | 还原副轴旁证判定；记录 P1 气相 18/18 不束缚、P2 仅 VC 束缚 | 脱附稳定性（旁证） | 仅旁证；明确「不可判定」 |
| `outputs/phase2_p1a/p1a_adiabatic.csv` | P1a 气相绝热量 | 还原轴被 `unbound_anion` 规则排除的出处 | 复用为「为何缺还原腿」的证据 |
| `outputs/week38/wp1_method_audit.json`、`outputs/physics_completion/method_audit/job_matrix.csv` | 128 格方法审计（M/M+/[LiM]+/[LiM]2+，无还原态） | 说明 `has_reduced_leg=False` | 只读；本批次无还原对象 |
| `outputs/week4/orca/<mol>/<mol>_anion.{inp,out,xyz,gbw}` | 各分子阴离子的原始 ORCA 产物 | 脱附稳定性 / 波函数身份的原始日志 | 可作原始依据；旧方法、无弥散 |

## 5. 判据冻结、产出与停止规则

- **冻结顺序**：先冻结 §2 三项判据的阈值与符号约定，再跑还原腿；阈值不得在看到还原排序后调整。
- 需要的还原腿至少覆盖：方法审计 8 分子 + 扩展池（见 `data/metadata/physics_completion_extension_pool.csv`）
  的 M/M⁻ 含弥散单点与身份诊断；具体作业量与成本在 pilot 后按 §11 口径登记，本文件不预填计数。
- 停止规则（沿用协议）：没有完整分子中心还原态 → `identity_outcome`；
  合理方法下脱附符号不稳定 → `unresolved`；不做还原轴的主 ranking 直到三项检查可执行。

## 6. 本文件**不**主张的内容

- 不主张任何分子在冻结方法下束缚或脱附稳定——**尚未计算**。
- 不把旧 `unbound_anion` 或气相/无弥散结果当作普适物理结论。
- 不修改、不覆写任何历史产物、阈值或结论。
- 本文件登记的是**协议**，不是**结果**；当前批次因 `unbound_anion` 规则得到零个合格还原对象，
  `wp1_reduction_state_checks` 记为 `exempt`。未来若纳入合格还原腿，该豁免自动失效，必须逐项复核后才能记为 `satisfied`。
