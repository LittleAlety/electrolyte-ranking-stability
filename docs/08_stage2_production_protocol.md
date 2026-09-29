# Stage 2–3 生产协议（Pre-registered / FROZEN draft）

对应 v2 §7.1（先 method audit，再冻结 production protocol）、§8（solution thermochemistry）、
§19 Stage 2–3，以及 Gate 1 第 5 条（production protocol 必须显式冻结并写入 provenance）。

> **冻结声明。** 本文件中的方法、几何协议、状态定义、参考态与换算常数、不确定度来源与
> 优先级顺序，必须在**查看任何 P1/P2 排序结果之前**冻结。任何修改只能以 append-only
> 方式追加到 `config/prereg.yaml` 的 `amendment_log`，并在此文件 §11 记录。
>
> **当前状态：DRAFT-FROZEN（2026-09-29）。** r2SCAN-3c 臂的软件参数已冻结，
> **ORCA 6.1.1 已到位并完成标定**（§7，见「实测标定」）；科学定义部分仍保持冻结原样。
> 标定属于「运行参数」而非「科学定义」，标定结果记入 §11。

---

## 1. 三层臂（arms）与唯一变量

| 层 | 目标量 | 电子结构方法 | 几何来源 | 环境 |
| --- | --- | --- | --- | --- |
| **P0** | -eps_HOMO / +eps_LUMO | GFN2-xTB 单点 | G1 | gas |
| **P1** | dG_ox_gas / dG_red_gas | r2SCAN-3c | G1（主）/ G2（几何敏感性臂） | gas |
| **P2** | dG_ox_cont / dG_red_cont | r2SCAN-3c | G2 | CPCM eps 扫描 + SMD 固定参考溶剂 |

**唯一变量原则。** 每条对比只允许**一个**维度变化：

- P0 -> P1：只变电子结构方法（几何同为 G1、同为气相）；
- P1 -> P2：只变环境（连续介质），几何与泛函相同；
- G1 -> G2：只变几何（见 §3.4）。

若某次运行被迫同时改变两件事，该数据必须标记 `state_identity_ambiguous`，
**不得**用于 robust inversion 统计。

---

## 2. 软件与版本（冻结）

| 项 | 冻结值 | 现状 |
| --- | --- | --- |
| xTB | `xtb 6.7.1`（官方 Windows x86-64 构建，SHA256 已校验） | 已装并跑通 |
| xTB 方法 | `GFN2-xTB`，默认参数；不额外加 `--gfnff` / `--alpb` | 已冻结 |
| ORCA | 已装 **6.1.1**（Windows AVX2 **msmpi** 构建，administrative install 到 `E:\ORCA\orca_6_1_1`，经 `.toolchain\orca\orca_6_1_1` junction 使用） | 已装并跑通 |
| ORCA 方法 | `! r2SCAN-3c`（composite：r2SCAN + D4 + def2-mTZVPP + RIJCOSX/def2-J） | 已跑通（见 `outputs/week3/orca_smoke/`） |
| 泛函敏感性对照 | `! wB97X-D4 def2-TZVPP`（仅审计臂，不进生产排序） | 待运行 |
| diffuse 对照 | `def2-TZVPD`（仅审计臂，专查阴离子伪束缚态） | 待运行 |
| 溶剂化 | `%cpcm epsilon <e>`（纯介电）与 `%cpcm smd true SMDsolvent "<name>"`（SMD）**两类分开报告** | 待运行 |
| 标准态 | T = 298.15 K，p = 1 atm，溶液 1 mol/L | 冻结 |
| 并行 | `%pal nprocs N`（N <= 物理核数），`%maxcore` 按内存设置 | 已标定（本机 16 核，实测 `nprocs 8`；非 ASCII 路径自动降级 `nprocs 1`） |

**换算常数（冻结，必须与锚点表一致）：**

- dG -> E：E [V] = -dG / (nF)，F = 96485.33212 C/mol，n = 1。
- 绝对电位标度与参照电极换算**只允许使用一处定义**（`config/scientific_definitions.yaml`
  的 `axis_C_external_reference.R_sol` 换算约定），并在 provenance 中记录 reference electrode。
- 计算结果**不得**直接与「vs Li/Li+」或「vs SHE」的实验值相减，除非两端都做过同一换算
  且写明了换算依据。

---

## 3. 几何协议（G0 -> G1 -> G2）

### 3.1 G0（起始几何）
- RDKit `ETKDG` 嵌入，`randomSeed` 固定并记录（core set 用 seed = 0xC0FFEE）；
- `MMFF94s` 预优化；
- **中文路径注意**：不用 `MolToXYZFile`，用仓库自写的 `write_xyz`（`scripts/run_xtb_job.py`）。

### 3.2 G1（廉价层几何）
- `xtb --opt`（GFN2-xTB），默认收敛判据，保留 `xtbopt.xyz` 与优化后能量；
- **必须解析优化后能量**，不得使用优化前能量（已有真实输出回归测试守住这一点）；
- G1 同时是 P0（单点）与 P1（主臂）的几何。

### 3.3 G2（目标层几何）
- `! r2SCAN-3c Opt`（必要时加 `TightOpt`）；
- 以 G1 结果作起点（坐标直接来自 `xtbopt.xyz`）；
- 每个分子做 `Freq` 以确认无虚频（针对审计子集，见 §7 预算）。

### 3.4 几何敏感性臂（把「几何效应」从「方法效应」里拆出来）
- 对审计子集中的分子，额外算 **P1@G2**（r2SCAN-3c 在 G2 几何上的气相 redox）；
- 与 **P1@G1** 相减得到 sigma_geom（几何诱导的数值/排序变化）；
- 若 sigma_geom 与 sigma_method 同量级，则所有结论必须显式说明
  「P0 -> P1 的变化不能全部归因于电子结构方法」。

### 3.5 构象（只对柔性分子）
- 对 `rotatable_bonds >= 5` 或 tags 含 `flexible` 的 core set 分子，抽 <= 5 个构象；
- 用 ETKDG 多 seed + RMS 去重；**不做** CREST 全搜索（预算考虑，CREST 仅作可选升级）；
- 构象 spread 记入 sigma_conf；**不允许**只保留最低能量构象而不报告 spread。

---

## 4. 电子态与参考态（冻结）

| 物种 | charge | multiplicity | 说明 |
| --- | --- | --- | --- |
| 中性 M | 0 | 1（singlet） | 闭壳层 |
| 氧化态 M.+ | +1 | 2（doublet） | 垂直/绝热分别记录 |
| 还原态 M.- | -1 | 2（doublet） | 气相若不稳定 -> `unbound_anion`，**不填数值** |

- 不施加超出自旋污染检查的额外对称性约束；出现 `spin_contamination_flag` 的条目照实记录。
- 能量换算的两个层级必须**分开报告**，不得混用：
  1. **电子能量近似**：dG ~ dE_SCF（无热校正）—— 廉价、全量；
  2. **热校正**：dG = dE_SCF + dZPE + dH_thermal - T*dS —— 仅在做了 `Freq` 的子集上。
  任何一个排序 / Top-k / inversion 统计内部，只允许出现同一层级的值。
- 溶液相使用**同一个**固定背景（同一套 eps 或同一个 SMD 溶剂参数），
  **不得**为每个候选单独挑「自己最舒服」的溶剂参数（v2 §8.3）。

---

## 5. 不确定度 sigma 的来源（每个都必须单独报告）

| 符号 | 来源 | 当前状态 |
| --- | --- | --- |
| sigma_method | method audit 中不同方法/泛函的同一可观测量离散度 | xTB 臂已有实测（`docs/04_stage1_xtb_audit_result.md`）；r2SCAN-3c 臂待 ORCA |
| sigma_conf | 构象集合 spread | 待算（审计子集） |
| sigma_geom | P1@G1 vs P1@G2 | 待算 |
| sigma_env | CPCM eps = 5,10,20,40 的离散度 | 待算 |
| sigma_boot | bootstrap 重采样（prereg 冻结的 20 seeds x 2000 次） | 库已就绪 |

**delta_m 冻结时点**（prereg §2 的 source_rule）：优先用外部锚点的实验离散度 (1)，
否则用 method audit 离散度 (2)，再否则用默认 2.0 kJ/mol (3)。
xTB 臂已给出 sigma 的**量级参考**（dSCF 误差 std 约 0.34 eV ≈ 33 kJ/mol，
Koopmans 约 0.67 eV ≈ 64 kJ/mol）—— 这说明**代理量层面的 pair 分辨能力很有限**。
这一事实本身是本项目的核心结论之一，**不得**用放宽 delta_m 的方式掩盖。

---

## 6. 决策量（全部沿用 prereg，冻结）

- Top-k：k = 10%/20%/30%；core set（N=18）-> 2/4/5，broad pool（N=40）-> 4/8/12。
- 指标：O_k（重叠）、J_k（Jaccard）、selection regret、f_unresolved、f_robust_inv、tau_b。
- **必须分别报告** oxidation 与 reduction，不得合并。
- 条件态层次：C0（自由分子）-> C1（Li+ 配位）。C1 只做**机制解释**，
  除非其 feature 在 query 前真实可得（prereg §6 的 X2 规则）。

---

## 7. 计算预算与优先级（按「若时间不够先做什么」排序）

> 下表「原估算」列为 ORCA 到位前的估计；ORCA 6.1.1 到位后已用 EC 冒烟作业实测标定（见下方「实测标定」）。

| 优先级 | 内容 | 分子 x 物种 | ORCA 作业数（原估算） | 单作业（原估算） | 小计（原估算） |
| --- | --- | --- | --- | --- | --- |
| **T1（必须）** | core set 18 x {M, M.+, M.-} 的 r2SCAN-3c **单点** @ G1 | 18 x 3 = 54 | 54 | 2–10 min | **2–6 h** |
| **T2（必须）** | 审计子集 12 的 `Opt` + `Freq`（几何敏感性 + 虚频检查） | 12 x 1–3 | ~20 | 10–40 min | **4–12 h** |
| **T3（必须）** | CPCM eps 扫描（12 分子 x 4 个 eps） | 12 x 4 | 48 | 2–10 min | **2–8 h** |
| **T4（重要）** | Li+ 配位 C1（core set 的 8–10 个代表分子） | 8–10 x 1–2 | ~15 | 5–20 min | **2–5 h** |
| **T5（可选）** | 泛函敏感性 `wB97X-D4`、diffuse 对照 `def2-TZVPD` | 审计子集 | ~20 | 10–40 min | 4–12 h |

**实测标定（2026-09-29，ORCA 6.1.1 msmpi，`nprocs 8`，EC 10 原子单点）：**

| 物种 | SCF 循环 | 墙钟 |
| --- | --- | --- |
| 中性气相 | 10 | 6 s |
| 中性 + SMD(acetonitrile) | 10 | 7 s |
| 阳离子 (+1, mult 2) | 25 | 12 s |
| 阴离子 (−1, mult 2) | 30 | 13 s |

- 单点实测：中性 **6–7 s**、离子 **12–13 s**（@ `nprocs 8`，EC 10 原子）。
- 因此 **T1 的 54 个作业 ≈ 10 min 墙钟**。
- 真实耗时取决于体系大小与 SCF 循环数：离子态 SCF 循环更多（阳离子 25、阴离子 30，中性 10），所以更慢。

**总预算（T1–T4）：约 10–31 h 墙钟**（**原估算**）；16 逻辑核可并行多作业，实际约 1–2 天。
原则：**T1 不砍**（它才是 P1 的主结果）；宁可砍 T5，也不要缩小 T1 的物种覆盖。

> 原表「待标定」状态已更新为**已实测标定（2026-09-29）**。

---

## 8. 产物与图表清单（本项目要求每轮成果都带图）

| 编号 | 图 | 数据来源 | 文件 |
| --- | --- | --- | --- |
| F1 | core vs broad pool 的 family x donor 覆盖热图 | `data/metadata/*.csv` | `outputs/week3/*.png` |
| F2 | 氟化/非氟化、柔性/刚性的 P0 分布 | `outputs/week3/p0_broad_pool.csv` | `outputs/week3/*.png` |
| F3 | **值误差 vs 排序误差**（MAE vs tau_b）双轴散点 | `outputs/week2/method_audit_xtb.csv` + r2SCAN-3c 臂 | `outputs/week3/*.png` |
| F4 | P0 -> P1 -> P2 的排序迁移图（slopegraph / bump chart） | 三层排序结果 | 待生成 |
| F5 | pair 差值 dP_ij 与不确定度带（± z*sigma）森林图 | `uncertainty.py` 输出 | 待生成 |
| F6 | f_unresolved 与 f_robust_inv 随方法层的柱状/折线 | 三层结果 | 待生成 |
| F7 | eps 扫描下目标量的连续变化曲线 | T3 | 待生成 |
| F8 | 预算曲线（Top-k 命中率 vs 计算成本） | active-learning replay | 待生成 |

图表规范：图内标签使用 ASCII/英文（避免中文字体缺失导致方框）；每张图必须能由仓库内脚本
**确定性重生成**，并在图目录附 `figure_manifest.md`，写明「图 -> 生成脚本 -> 输入数据 -> SHA256」。

---

## 9. 禁止事项（违反即结论不可用）

- 禁止把 P0（轨道能代理）解释为真实氧化还原电位；
- 禁止在未报告 f_unresolved 的情况下宣称「排序稳定」；
- 禁止把未解析 pair 的任意换序称作物理 inversion；
- 禁止混用不同几何来源（G1/G2）或不同热校正层级的数值做同一张排序表；
- 禁止为每个候选单独挑选溶剂参数；
- 禁止在看到结果后修改 k、delta_m、z、seed、family 定义或判定方向；
- 禁止用 X2 级 feature 去论证「无需做 C1 就能低成本预测 C1」。

---

## 10. 与 Gate 的关系

- Gate 1（当前 **NOT CLOSED**）的 blocker：**溶液相锚点仍为 est**（原「ORCA 未安装」一条**已解除**：
  ORCA 6.1.1 已装并跑通）。本协议 §1–§6 的冻结**不**解除 blocker，只解除「protocol 未冻结」这一潜在问题。
- Gate 1 关闭条件（`docs/02_stage1_method_audit.md` §4.2）：state identity 无系统性失败、
  SCF 稳定、气相锚点趋势正确、溶液趋势方向一致、protocol 已冻结并写入 provenance。
- T1 完成后基于实测重新评估本协议；**任何**改动走 §11。

---

## 11. 修订记录（append-only）

| 日期 | 变更 | 理由 | 依据 |
| --- | --- | --- | --- |
| 2026-09-29 | 初版：冻结三层臂、几何协议 G0/G1/G2、状态与参考态、sigma 来源、预算优先级、图表清单 | Stage 2 开工前的预注册 | v2 §7.1/§8/§19；`config/prereg.yaml` |
| 2026-09-29 | 回填 ORCA 6.1.1（msmpi）小版本号与 EC 冒烟实测：§2 现状更新、§7 增加「实测标定」、§10 blocker 更新 | ORCA 已到位并完成运行参数标定（科学定义未改动） | `outputs/week3/orca_pilot_summary.json`；`docs/07_orca_setup_and_runner.md` |

> 待办（ORCA 到位后回填）：ORCA 具体小版本号（**已填：6.1.1**）；T1–T4 的实测单作业时长
> （**已实测标定，见 §7**）；sigma_method / sigma_geom / sigma_env 的实测数值；delta_m 的最终冻结值。