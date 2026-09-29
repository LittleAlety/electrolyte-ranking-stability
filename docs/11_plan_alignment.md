# 11 新执行计划 v1.0 ↔ 本项目实际执行：对齐与偏差分析

- 项目: 电解液溶剂 ranking 稳定性 (decision-centric ranking stability)
- 文档性质: 横向对齐审查报告 (只读；不修改任何科学定义或已冻结项)
- 日期: 2026-09-29
- 上游依据:
  - `核心文件/ranking-electrolyte-materials-v2.md` (下称 v2；科学定义的权威来源)
  - 详细执行计划 v1.0 (2026-09-29，本科 MVP，8–12 周；纯文本提取见 `outputs/_plan_docx.txt`，共 546 行)
- 本项目执行记录: `计划.md`、`README.md`、`docs/00`–`docs/10`、`config/*.yaml`、`outputs/week1`–`week4`
- 核实原则: 报告中每个数字都能在仓库文件中回溯；无法核实的量标注「待核实」，绝不编造。

---

## 0. 术语与代号速查

| 代号 | 含义 | 冻结/定义位置 |
| --- | --- | --- |
| `P0` | 廉价标量代理 (xTB `-eps_HOMO` / `+eps_LUMO`) | `config/scientific_definitions.yaml` `axis_A_proxy_hierarchy.P0` |
| `P1` | 气相分子 redox 热力学 (本项目实为**垂直** IP/EA) | 同上 `.P1`；实现见 `docs/10` |
| `P2` | 固定连续介质 redox 热力学 (本项目 = SMD 乙腈) | 同上 `.P2`；`docs/08` §2 |
| `C0` / `C1` / `C2` | 自由分子 / Li+ 条件态 / 显式微溶剂化 | 同上 `axis_B_environment_states` |
| `R_gas` / `R_sol` / `R_env` | 气相 / 溶液相 / 环境外部锚点 | 同上 `axis_C_external_reference` |
| `X0` / `X1` / `X2` | 特征成本层级 (query 前 / 自由分子 DFT 后 / Li 配合物 DFT 后) | `config/prereg.yaml` `feature_cost` |
| `G1` / `G2` | 廉价层几何 (xTB `--opt`) / 目标层几何 (r2SCAN-3c `Opt`) | `docs/08` §3 |
| `delta_m` | 与方法不确定度无关的固定 pair tolerance (兜底阈值) | `config/prereg.yaml` `pair_comparison.delta_m` |
| `sigma_ij` | pair 级不确定度 (方法/构象/环境/bootstrap 来源) | `config/prereg.yaml` `uncertainty`；`docs/08` §5 |
| `M0`–`M6` | 六个里程碑 | 新执行计划 §1.3 |

---

## 1. 两份文档的关系

| 角色 | 文档 | 回答的问题 |
| --- | --- | --- |
| 科学定义层 (权威) | v2 `ranking-electrolyte-materials-v2.md` | 为什么做、做什么 |
| 执行层 (通用模板) | 新执行计划 v1.0 | 谁来做、按什么顺序、用什么参数、做到什么程度算完成、出问题怎么办 |
| 执行层 (本项目实例) | `计划.md` + `docs/00`–`docs/10` + `config/*` + `outputs/week*` | 同一课题在一个「物理机制小数据集」实例上的真实执行 |

**1.1 新执行计划 v1.0 是 v2 的执行层。** 新计划 §1.2 原文规定：本计划「不改变 v2 的科学定义，只补充执行细节」（具体分子清单、软件与参数、逐周安排、逐 Stage 交付物与放行 Gate、预算、风险预案），并明确「凡本计划与 v2 不一致处，**以 v2 的科学定义为准并记录偏差原因**」。本项目严格按此条规定执行——本报告 §4 即为该条的落地记录。

**1.2 本项目是同一课题的一个「物理机制小数据集」实例。** 新计划是覆盖 Stage 0–9（含 Stage 7–9 的 ML、主动学习、显式微溶剂化）的**通用本科 MVP 模板**，规模设定为 core N≈64、broad pool N≈500。本项目在**相同的科学问题、相同的科学定义、相同的判据**下，主动把规模压到 core N=18、broad pool N=40，并把方法栈压到「GFN2-xTB + r2SCAN-3c」两种。因此两者的差异集中在**规模**与**方法栈**，而非科学问题或判据。

**1.3 两层在科学定义上是一致**（不是两套课题）：

| 项 | v2 / 新计划 | 本项目 | 一致性 |
| --- | --- | --- | --- |
| 氧化目标量 | `S_ox = ΔG_ox`, maximize | `config/scientific_definitions.yaml` `objectives` 同 | 一致 |
| 还原目标量 | `S_red = ΔG_red`, maximize | 同上 | 一致 |
| Top-k | k/N = 10% / 20% / 30% | `config/prereg.yaml` `top_k.fractions` = [0.10, 0.20, 0.30] | 一致 |
| 参考配体 R | 建议 DME，Stage 0 冻结后不得更换 | `reference_ligand.primary_R` = C08 DME | 一致 |
| pair 判据 | `unresolved` / robust inversion / p_ij 阈值 | `config/prereg.yaml` `pair_comparison` 同骨架 | 一致 |
| 三层臂 | P0/P1/P2、C0/C1/C2、R_gas/R_sol/R_env | `docs/00` §2 同 | 一致 |

**1.4 如何读本报告。** §2 给出 Stage 0–9 的逐项映射与缺口；§3 给出里程碑 M0–M6 的达成状态；§4 是本报告最重要的一节，逐条记录偏差（编号 D1–D7）并给出处置；§5 按价值排序给出未做项；§6 是结论。所有引用均为仓库内相对路径。

---
**1.5 新计划 Stage 到本项目文档 / 产物的对应**

| 新计划 Stage | 本项目对应文档 | 本项目对应产物 |
| --- | --- | --- |
| Stage 0 定义冻结 | `docs/00_stage0_definitions.md` | `config/*.yaml`、`outputs/week1/gate0_record.md` |
| Stage 1 方法审计 | `docs/01`、`docs/02`、`docs/04`、`docs/06` | `outputs/week2/*`（`method_audit_xtb*`、`solution_anchor_audit*`、`gate1_record.md`） |
| Stage 2 broad pool | `docs/05`、`docs/09` | `outputs/week3/*` |
| Stage 3 core 自由分子 | `docs/08`、`docs/10` | `outputs/week4/p1_core_set*`、`outputs/week4/orca/` |
| Stage 4 固定连续介质 | `docs/08`、`docs/10` | `outputs/week4/p2_*`、`outputs/week4/orca_smd_acetonitrile/` |
| Stage 5 Li+ 配位 | （无） | （无） |
| Stage 6 排序统计 | `docs/02` §4、`docs/08` §6 | `outputs/week4/p1_decision_stability*`、`outputs/week4/p2_decision_stability*` |
| Stage 7–8 ML / AL | 协议在 `config/prereg.yaml` §5–§8 | （无） |
| Stage 9 微溶剂化 | （无） | （无） |

---

## 2. Stage 0–9 逐项映射

列含义：**Stage** = 新计划的阶段号；**新计划要求** = v1.0 原文要点（不逐字复述）；**本项目状态** = 实际完成度；**证据文件/产物** = 可回溯落点；**缺口** = 尚未满足的部分。

| Stage | 新计划要求 | 本项目状态 | 证据文件 / 产物 | 缺口 |
| --- | --- | --- | --- | --- |
| **Stage 0** 定义冻结 | §2：冻结目标量方向、k 值、δ 确定规则、reference ligand、anchor 搜集规则；预注册文件提交并打 tag (v0.1-prereg) | **已完成**。`config/scientific_definitions.yaml` + `config/prereg.yaml` 均 `frozen: true`、`frozen_date 2026-09-29`；Gate 0 **CLOSED** | `config/scientific_definitions.yaml`、`config/prereg.yaml`、`docs/00_stage0_definitions.md`、`outputs/week1/gate0_record.md` | `delta_m` 的**数值**按预注册规则延后到 Gate 1 冻结（规则本身已冻结）；文件名用 `prereg.yaml` 而非计划建议的 `preregistration.yaml`；未打 git tag（改用 `frozen` 标志 + SHA256 清单固化） |
| **Stage 1** 方法审计 | §4.2：8–10 个审计分子的 functional/basis/diffuse/continuum sensitivity；gas 与 solution anchor 比对；production protocol 冻结 | **部分完成**。xTB 审计臂已跑（12 分子 ΔSCF / Koopmans）；r2SCAN-3c 的 `wB97X-D4` 与 `def2-TZVPD` 对照臂**未跑**；溶液锚点未收口；Gate 1 **NOT CLOSED** | `docs/02_stage1_method_audit.md`、`docs/04_stage1_xtb_audit_result.md`、`docs/06_stage1_solution_anchor_audit.md`、`outputs/week2/method_audit_xtb.csv`、`outputs/week2/method_audit_xtb_summary.json`、`outputs/week2/gate1_record.md` | ① 溶液锚点 `data/anchors/solution_redox_anchors.csv` 31 行 / 16 物种**全部 `method=est`**（0 exp / 0 calc），含 2 处引用错配（SL、EC）；② `wB97X-D4`、`def2-TZVPD` 对照臂未跑；③ `delta_m` 数值未冻结 |
| **Stage 2** broad cheap pool | §5.1 / §3.2：broad pool N≈500（可扩至 1000）的 X(0) 与 P0；core 自由分子 P1 完成并过 QC | **已完成**（规模不同）。broad pool **N=40** 全部 P0；core **N=18** P0；合计 **58/58 收敛、0 失败**；core P1（T1）54/54 成功并独立复核 | `docs/05_stage2_broad_pool_p0.md`、`docs/09_week3_report.md`、`outputs/week3/p0_broad_pool.csv`、`outputs/week3/p0_core_set.csv`、`outputs/week4/p1_core_set.csv`、`outputs/week4/p1_core_set_audit.*` | 规模差异见 §4 D1；X(0) 多维描述符未单独成表（随 metadata 一并维护） |
| **Stage 3** core 自由分子电子结构 | §5.2：core 三电荷态（M / M.+ / M.−）在**目标层几何**上做 `Opt`+`Freq`，得 P1 | **部分完成**。P0（xTB 单点）+ **P1 = r2SCAN-3c 垂直 IP/EA @ G1**，N=18、54/54；但几何为 **G1（xTB 优化）**、且为**垂直单点**，目标层 `Opt`+`Freq`（T2）未做 | `docs/08_stage2_production_protocol.md` §3、`docs/10_week4_report.md` §1–2、`outputs/week4/p1_core_set.csv`、`outputs/week4/p1_core_set_derived.csv` | T2（G2 几何 + 虚频检查 + `sigma_geom`）未做；无绝热量 / 热校正（详见 §4 D6） |

---
| **Stage 4** 固定背景连续介质 | §5.3：core 全部候选 P2 就绪；全部候选同一固定背景；首轮 P0→P1→P2 排序稳定性矩阵 | **已完成 P2**（SMD 乙腈，N=18）；P0→P1、P1→P2、P0→P2 排序稳定性矩阵已产出 | `docs/08` §2、`docs/10` §2.4–2.5、`outputs/week4/p2_core_set_smd_acetonitrile.csv`、`outputs/week4/p2_environment_effects.csv`、`outputs/week4/p2_decision_stability.*` | CPCM `eps` 扫描（T3，`sigma_env` 曲线）未做；continuum 两类 sensitivity 只落地 `A_fixed_solvent_benchmark`（SMD），`B_dielectric_only` 未做 |
| **Stage 5** 条件 Li+ 配位态 (C1) | §5.4：motif 枚举 → DFT → state-identity QC → `ΔΔG_coord` 与 ligand-exchange | **未开始**（T4 已在生产协议中排定优先级，未执行） | `docs/08` §7（T4 计划）；`config/scientific_definitions.yaml` 的 `axis_B_environment_states.C1` 与 `li_motif_generation` | 全部：Li motif 生成、C1 优化/单点、state-identity QC、`ΔΔG_coord` |
| **Stage 6** 不确定性感知排序 | §6：τ_b / unresolved / robust inversion / Top-k / regret 全套 + bootstrap；`delta_m` 按 §6.2 的 max() 规则写入预注册 | **指标已实现并已产出**。`ranking.py` / `uncertainty.py` 已就位；`p1_decision_stability.*`、`p2_decision_stability.*` 已出（含 `f_unresolved`、`f_robust_inv`、`O_k` / `J_k`、`regret`、`tau_b`）。但 `delta_m` 的 max() 数值**未冻结**；`z` 因子实现为 1.96（预注册为 1.0） | `src/electrolyte_ranking/ranking.py`、`src/electrolyte_ranking/uncertainty.py`、`outputs/week4/p1_decision_stability.{json,md}`、`outputs/week4/p2_decision_stability.{json,md}` | `delta_m` 数值冻结；`z` 因子一致性（§4 D3）；bootstrap 方法差异（§4 D4）；决策阈值项 `E_decision` 尚无合规来源（记为 `not_applicable`） |
| **Stage 7** 机器学习 | §7：特征成本分层 X0/X1/X2；random / group / LOFO 三拆分；direct vs Δ-learning | **未开始**（协议已在预注册冻结：`model_complexity_order`、`splits`、`feature_cost`） | `config/prereg.yaml` §5 / §6 / §8、`docs/00` §4 | 全部 ML 结果与机制分析 |
| **Stage 8** 主动学习 | §7.4：active-learning replay（≥8 seeds × ≥10 次重复）；n_T → τb / O_k / R_k 曲线 | **未开始**（协议已在预注册冻结：`active_learning`） | `config/prereg.yaml` §7 | 全部 AL 结果与「最小昂贵信息预算」曲线 |
| **Stage 9** 显式微溶剂化（可选） | §8.1：8–12 候选的 targeted microsolvation check | **未开始**（新计划亦声明「本科项目时间有限时，Stage 9 不作为项目完成必要条件」） | — | 可选；不建议在核心闭环（Stage 5–6）未完成前启动 |

**2.1 映射状态汇总**

| 状态 | Stage |
| --- | --- |
| **已完成** | 0、2、4 |
| **部分完成** | 1（唯一 blocker = 溶液锚点）、3（缺目标层几何 T2）、6（缺 `delta_m` 数值 + `z` 一致性） |
| **未开始** | 5、7、8、9 |

**2.2 跨 Stage 的三个共同缺口**

- **溶液锚点**：贯穿 Stage 1 与 Gate 1，是 M1 放行的唯一剩余条件（`docs/06` §5、`outputs/week2/gate1_record.md`）。
- **目标层几何 T2（G2 `Opt`+`Freq`）**：决定 P1 是否只是「垂直代理」，并给出 `sigma_geom`（`docs/08` §3.4、`docs/10` §7）。
- **`delta_m` 数值与 `z` 一致性**：决定 Stage 6 的 pair 判定口径能否从「临时的 `z·sigma`」升级为「预注册规则」（`config/prereg.yaml` §2、§4 D3 / D5）。

---
**2.3 时间线对照（新计划周次 vs 本项目实际）**

| 新计划周次 | 新计划阶段 | 本项目实际 |
| --- | --- | --- |
| 第 1 周 | Stage 0 + Stage 1 启动 | 已完成：Gate 0 CLOSED（`outputs/week1`） |
| 第 2 周 | Stage 1 审计 | 部分完成：xTB 臂已跑；r2SCAN-3c 对照臂与溶液锚点未收口（`docs/03`、`docs/04`、`docs/06`） |
| 第 3–4 周 | Stage 2 + Stage 3 | Stage 2 完成；Stage 3 部分完成（P1 垂直量已出，T2 几何未做）（`docs/09`、`docs/10`） |
| 第 5–6 周 | Stage 4 | P2（SMD 乙腈）完成；CPCM `eps` 扫描未做（`docs/10` §2.4–2.5） |
| 第 7–8 周 | Stage 5 | 未开始 |
| 第 9 周 | Stage 6 | 指标已出；`delta_m` / `z` 待收口 |
| 第 10–12 周 | Stage 7–9 | 未开始 |

---

## 3. 里程碑 M0–M6 达成表

| 里程碑 | 计划时点 | 放行判据 | 本项目状态 | 说明 |
| --- | --- | --- | --- | --- |
| **M0** 定义冻结 | 第 1 周末 | 预注册签署：目标量方向、k 值、δ 确定规则、reference ligand、anchor 搜集规则全部冻结并记入版本库 | ✅ **已达成** | Gate 0 **CLOSED**（`outputs/week1/gate0_record.md`，frozen artefacts 6 件）；`config/prereg.yaml`、`config/scientific_definitions.yaml` 均 `frozen: true`。`delta_m` 的**数值**按预注册规则延后到 Gate 1（规则本身已冻结，符合 M0 判据） |
| **M1** 方法审计通过 | 第 2 周末 | 8–10 审计分子的 functional / basis / continuum sensitivity 完成；gas-phase anchor 偏差与排序一致性达标；生产协议冻结 | ❌ **未达成** | Gate 1 **NOT CLOSED**，唯一 blocker = 溶液锚点 31 行全 `est`（`docs/06` §5、`outputs/week2/gate1_record.md`）。ORCA 阻塞**已解除**（6.1.1 已装并跑通）；生产协议已 DRAFT-FROZEN（`docs/08`，2026-09-29）。barrier 数量从 2 减到 1 |
| **M2** cheap pool 完成 | 第 4 周中 | broad pool 全部候选 X(0) / P0 就绪；core 自由分子 P1 完成并过 QC | ✅ **已达成**（规模不同） | broad P0 40/40 + core P0 18/18 = **58/58**（`outputs/week3`）；core P1 **54/54 成功**、独立复核 0 分歧、18 分子三态齐全（`outputs/week4/p1_core_set_audit.*`）。规模为 §4 D1 的缩小版，判据本身满足 |
| **M3** continuum 完成 | 第 6 周末 | core 全部候选 P2 就绪；首轮 P0→P1→P2 排序稳定性矩阵产出 | ✅ **已达成** | P2 = SMD 乙腈，N=18（`outputs/week4/p2_core_set_smd_acetonitrile.csv`）；P0→P1（`outputs/week4/p1_decision_stability.*`）与 P1→P2、P0→P2（`outputs/week4/p2_decision_stability.*`）矩阵已出 |
| **M4** 配位态完成 | 第 8 周末 | core 的 C1 条件态计算与 state-identity QC 完成；`ΔΔG_coord` 表冻结 | ⛔ **未到** | Stage 5 未开始；无任何 C1 产物 |
| **M5** 统计与 ML 完成 | 第 10 周末 | robust inversion 机制分析、direct vs Δ-learning、LOFO 结果齐备 | ⛔ **未到** | Stage 6 指标已出但 `delta_m` 未冻结、`z` 因子待回归 1.0；Stage 7 未开始 |
| **M6** 项目闭环 | 第 12 周末 | active-learning replay 曲线、最终图表与报告完成；全部数据可追溯 | ⛔ **未到** | Stage 8–9 未开始 |

**3.1 说明。** M0 / M2 / M3 的「已达成」是以本项目的缩小规模为口径；若按新计划原规模（core N≈64、broad N≈500），则 M2 的判据（broad pool 全部候选 X(0)/P0）**尚未满足**。本报告两种口径均如实标注，不作含糊处理。

---

## 4. 偏差记录表（本报告最重要的一节）

> 记录格式对应新计划 §1.2：「凡本计划与 v2 不一致处，以 v2 的科学定义为准并记录偏差原因」。
> 其中 **D3 属实现缺陷**（非有意设计），**D1 / D2 / D4 / D5 / D6 / D7 属有意的受约束实例化**（用户要求 + 工程权衡）。

| 编号 | 项 | 新执行计划 v1.0 | 本项目实际 | 偏差理由 | 处置 |
| --- | --- | --- | --- | --- | --- |
| **D1** | 数据规模 | core **N≈64**（建议清单 72，最终冻结 60–70）；broad pool **N≈500**，可扩至 1000 | core **N=18**；broad pool **N=40**（`data/metadata/core_set.csv`、`data/metadata/broad_pool.csv`） | 用户明确要求「不需要大量数据，侧重物理 / 化学机制」；`config/scientific_definitions.yaml` 的 `dataset.core_set.size_note` 已记录该主动缩小，并写明保留 2–3 个机理对照分子（FEC / VC / SN，对应 C06 / C07 / C18） | 维持小数据集为主路线；把 N≈64 / 500 标注为「**可选扩展**」，并把扩展触发条件写入 §5（当 ML / LOFO 结论因 n 太小而区间过宽、需要更多标签时，再扩 broad pool 与 core labels） |
| **D2** | 方法栈 | §4.3：几何/频率 r2SCAN-3c；单点 `wB97X-D4/def2-TZVP`；阴离子另启 `ma-def2-TZVP` | 几何 **G1 = GFN2-xTB `--opt`**；单点 **r2SCAN-3c**（垂直量 @ G1）；`wB97X-D4`、`def2-TZVPD` 仅列为待跑对照臂（`docs/08` §2） | 用户要求「简单 & 高效，只用 xtb 和 r2SCAN-3c」；`计划.md` §4 已冻结该协议，与 `config/prereg.yaml` 一致 | 保留简化。**已知代价（必须明示）**：r2SCAN-3c 的复合基组是 **def2-mTZVPP、不含弥散函数**，因此气相阴离子 EA 的「全部不束缚」结论受方法边界限制（`docs/10` §2.6：18/18 气相自由基阴离子在 r2SCAN-3c 下不束缚）。处置：把「弥散函数对照臂 `def2-TZVPD`」列为当前**最高优先级的裁断任务**（见 §5 第 ②） |
| **D3** | `z` 因子 | §6.1 / §6.2 取 `z = 1` | `config/prereg.yaml` 的 `pair_comparison.z_factor.value = 1.0`（并规定 probabilistic pair ordering 为主判据）；但分析脚本实现为 **1.96**：`scripts/analyze_p1_core_set.py` 第 54 行 `Z_BAND = 1.96`（`scripts/analyze_p2_environment.py` 同） | **实现与冻结预注册不一致，属缺陷而非有意设计**（1.96 是常见 95% 双侧系数，被误当作默认值写死） | **已修正**：`scripts/analyze_p1_core_set.py` 与 `scripts/analyze_p2_environment.py` 现在**同时报告** `z=1.0`（预注册主判据）与 `z=1.96`（保守敏感性），主判据回归 `1.0`；新增回归测试 `tests/test_analysis_z_bands.py`。**未向 `amendment_log` 追加条目，也无需追加**：`z_factor.value` 始终是 `1.0`，本次没有改动任何冻结的科学定义，只是让**实现回归冻结值**，属代码缺陷修复而非预注册变更。因此 `config/prereg.yaml` 保持**逐字节不变**（sha256 `e89f2e2a…f340`），Gate 0 仍为 **CLOSED**。证据见 `docs/10_week4_report.md` §2.4 与 §3。 |
| **D4** | bootstrap 设置 | §6.3：**1000 次 BCa 95% CI** | 20 个固定 seed × 2000 次 paired **percentile**，报告 20 个区间中位数 | `config/prereg.yaml` 的 `uncertainty.bootstrap`（`repetitions: 2000`、`ci_method: percentile`、`random_seeds` 20 个）已冻结，且**更保守**：多 seed 消除单次运气，percentile 在 n=18 时比 BCa 更稳，避免小样本下 BCa 的覆盖率失真 | 保留 prereg 设置，记录偏差；报告统一给出「区间中位数」（见 `outputs/week4/p1_decision_stability.md` §1 注、`docs/10` §2.3） |
| **D5** | `delta_m` 规则 | §6.2：`delta_m = max(构象 ensemble 90 分位展宽, 方法审计 inter-method 展宽, 0.05 eV 下限)` | `config/prereg.yaml` 定义的是 `delta_m`（**固定兜底阈值**，`delta_default = 2.0 kJ/mol`，`source_rule` 三优先级）+ `z·sigma_ij` 两臂离散度；当前实际使用的是 `z·sigma` 路线，`delta_m` 的 max() 数值**尚未冻结** | 新计划的 max() 规则需要 Stage 1 的构象展宽与方法展宽（`sigma_conf`、`sigma_method`）作为输入，而 Stage 1 未收口（`docs/08` §5 明确 `sigma_conf`/`sigma_env`/`sigma_geom` 均为「待算」） | Stage 1 / Gate 1 关闭时，按新计划 §6.2 的 max() 规则补齐数值并 append 写入 prereg；在此之前所有 pair 判定标注为「基于 `z·sigma` 的**临时口径**」，不得对外称为已冻结 |
| **D6** | P1 量的定义 | Stage 3：core 三电荷态在**目标层几何**上做 `Opt`+`Freq`，P1 为弛豫后的 `G(M±) − G(M)` | 本项目 P1 = **垂直** IP/EA（ΔSCF 单点 @ 中性 **G1** 几何），无 `Opt` / `Freq`、无热校正（`docs/10` §1、§7） | 为满足「唯一变量 = 电子结构方法」（P0→P1 只换方法，`docs/08` §1 明令禁止同时改两件事）与「与实验 PE 值可比」（`docs/10` §1），并按用户要求压到最小方法栈 | 明确标注 P1 为**垂直量**（已在 `docs/10` §7 声明，不得当作热力学量用于电位换算）；把 T2（G2 `Opt`+`Freq`、虚频、`sigma_geom`）列入 §5 第 ③ 优先 |
| **D7** | pool 构建方式 | §3.2：broad pool 来自 Electrolyte Genome / PubChem / 课题组历史分子，经 RDKit 可解析 + MW≤250 等规则自动筛至 N≈500 | 本项目 broad pool 为**人工策展的 40 分子**，逐分子带 `pool_reason`，覆盖 11 个 family（core 8 个，`outputs/week3/coverage_report.md`） | 小数据集路线下，**逐分子可解释性与 family 覆盖**优先于自动筛选规模；保证每分子都能回溯入选理由与 anchor 可识别性 | 保留人工策展；若未来扩池，再引入计划 §3.2 的自动筛选规则与 fingerprint + PCA/UMAP 覆盖检查（该流程当前**未**在 config 中冻结） |

**4.1 偏差性质分类**

| 性质 | 编号 | 处理原则 |
| --- | --- | --- |
| 有意的受约束实例化（用户要求 + 工程权衡） | D1、D2、D4、D5、D6、D7 | 保留现状，逐条记录理由；在对外表述与最终报告中必须显式声明这些边界 |
| 实现缺陷（须修正，非设计） | D3 | 按 prereg 的 append-only 政策修正，主判据回归预注册值 `z=1.0` |

**4.2 关于「其它偏差」。** 已按要求复核 v1.0 全文与仓库产物，未发现除 D1–D7 之外的、可回溯的真实偏差；本报告不为凑数而编造条目。（预注册文件名 `prereg.yaml` vs 计划建议的 `preregistration.yaml`、以及用 SHA256 清单替代 git tag，属于形式命名差异，不构成计划偏差，已在 §2 Stage 0 行注明。）

---

## 5. 未做项与优先级（按对科学结论的价值排序）

> **状态更新（2026-09-29）**：下表 ②「弥散函数对照臂」**已于本轮完成**（脚本 `scripts/run_diffuse_control.py`，图 `F9`）。
> 结论：在同泛函 r2SCAN、只换基组的三臂对照下，加弥散把气相 EA **系统性下拉 0.34–1.60 eV**
> （四分子方向完全一致），但**不足以翻转符号**（def2-TZVPD 下 `E(anion) − E(neutral)` 仍为 +0.87 ~ +0.93 eV）。
> 即 `docs/10` §2.6 的「18/18 全不束缚」**方向上确系基组缺弥散所致**，而 0.01 eV 量级的束缚判定
> **超出本方法适用域**——这是一个 applicability-domain 结论，不是对实验的判决。
> 产物：`outputs/week4/t5_diffuse_control.csv`、`t5_diffuse_control_summary.json`、`outputs/week4/t5_diffuse_control/`。

| 优先级 | 未做项 | 对应 Stage / 任务 | 对科学结论的价值 | 依赖 / 触发条件 |
| --- | --- | --- | --- | --- |
| **① 最高** | 溶液锚点核验（Gate 1 唯一 blocker） | Stage 1 / Gate 1 | 没有它，任何「与实验对齐的绝对电位」表述都不允许；它是 M1 放行的唯一剩余条件，也是 `R_sol` 层能否成立的根基 | 需要一份条件统一、可逐条引用的实验溶液相 redox 表；同时修正 `docs/06` §4.3 记录的 2 处引用错配（SL、EC） |
| **② 高** | T2 审计子集 `Opt`+`Freq` | Stage 3 / T2 | 给出虚频检查与 `sigma_geom`，把 P0→P1 的变化拆成「方法效应 vs 几何效应」；同时是 D5 中 `delta_m` 的构象 / 方法展宽输入之一 | 生产协议 `docs/08` §3.3–3.4 已定义 G2 与几何敏感性臂；审计子集 12 分子 |
| **③ 中高** | T3 CPCM `eps` 扫描（eps = 5 / 10 / 20 / 40） | Stage 4 / T3 | 给出 `sigma_env` 随介电常数的连续曲线，把 `docs/10` §2.4 的 sigma 从「两臂差」升级为「多来源合成」，并检验纯介电 screening 是否产生 robust inversion（v2 §8.3 第二类 sensitivity） | 生产协议 `docs/08` §5；分子集与审计子集一致 |
| **④ 中** | Stage 5 Li+ 配位 C1 | Stage 5 / T4 | M4 的核心；唯一的**条件态机制层**，回答「Li+ 配位是否改变材料筛选决策」这一核心科学问题 | 依赖 Stage 1 收口与 `delta_m` 冻结；core set 的 8–10 个代表分子 |
| **⑤ 中（可选）** | Stage 7–8 ML / 主动学习 | Stage 7–8 | 「最小昂贵计算预算 vs 决策精度」曲线是项目最有方法学辨识度的产出（新计划 §7.4） | **依赖 D1 的扩展触发条件**：若 ML / LOFO 结论因 n 太小而区间过宽，则先扩 broad pool 与 core labels 再开展（对应新计划风险表「core set 规模不足以支撑 ML 结论」） |

**5.1 建议执行顺序：** ① → ② → ③ → ④ → ⑤（其中 ②、③ 是 `delta_m` 冻结的直接输入，决定 Stage 6 能否从「临时 `z·sigma` 口径」收口为「预注册规则」）。原则与新计划 §8.3 一致：**宁可缩小规模，也不牺牲 state-identity QC 与 method audit**。

**5.2 明确暂不做的项（附理由）**

- **Stage 9 显式微溶剂化**：新计划自述「本科项目时间有限时，Stage 9 不作为项目完成必要条件」；应在核心闭环（Stage 5–6）之后按余力决定，避免过早摊薄预算。
- **`E_decision` 阈值决策误差**：`config/prereg.yaml` 的 `threshold_decisions.if_unavailable` 规定无合规来源时记为 `not_applicable`，**不得**用数据分位数临时替代；当前已按此处理。
- **自动扩池流程**：在 D1 的扩展触发条件被满足之前不启动（见 §5 ⑤）。

---

## 6. 结论

本项目走的是**物理机制小数据集**路线：在 core N=18 / broad pool N=40 的小规模上，用 GFN2-xTB + r2SCAN-3c 两种方法，研究「从廉价代理量到更真实的电子结构 / 环境模型」时，哪些变化只是数值平移、哪些会真正翻转材料筛选决策。所有与 v2 / 新执行计划 v1.0 的偏差——数据规模（D1）、方法栈（D2）、`z` 因子实现（D3）、bootstrap 设置（D4）、`delta_m` 规则（D5）、P1 量的定义（D6）、pool 构建方式（D7）——均按新计划 §1.2 的规定**逐条记录原因并给出处置**；其中 D3 是须修正的实现缺陷，其余是经用户要求与工程权衡后的有意实例化。**科学定义一律以 v2 为准**：本项目的偏差不改动任何科学定义，只影响执行的规模与深度；Stage 1 未收口（溶液锚点）之前，所有排序类结论仅作方向性证据。

---

## 附录 A：本报告核实到的关键数字（均可回溯）

| 数字 | 含义 | 出处 |
| --- | --- | --- |
| 546 | 新执行计划纯文本行数 | `outputs/_plan_docx.txt` |
| 18 / 40 | core set / broad pool 分子数 | `data/metadata/core_set.csv`、`data/metadata/broad_pool.csv`、`config/scientific_definitions.yaml` `dataset` |
| 58/58 | Week 3 P0 收敛数（core 18 + broad 40），0 失败 | `docs/05` §3、`docs/09` |
| 54/54 | Week 4 T1（r2SCAN-3c 垂直 IP/EA）成功数，18 分子三态齐全 | `docs/10` §2.1–2.2、`outputs/week4/p1_core_set_audit.*` |
| 18/18 | 气相自由基阴离子在 r2SCAN-3c 下全部不束缚（`unbound_anion`） | `docs/10` §2.2、§2.6 |
| 31 / 16 | 溶液锚点行数 / 物种数，**全部 `method=est`** | `data/anchors/solution_redox_anchors.csv`、`docs/06` §4 |
| 39 / 26 | 气相锚点行数 / 物种数（`exp` 28、`calc` 2、`na` 9） | `data/anchors/gas_phase_anchors.csv`、`docs/03` §2 |
| 2 | 溶液锚点核验发现的引用错配处数（SL、EC） | `docs/06` §4.3 |
| 2000 × 20 | bootstrap 重复次数 × 固定 seed 数（percentile） | `config/prereg.yaml` `uncertainty.bootstrap` |
| 1.0 / 1.96 | 预注册 `z` 因子 / 脚本实现值 | `config/prereg.yaml` `pair_comparison.z_factor.value`；`scripts/analyze_p1_core_set.py` `Z_BAND` |
| 2.0 kJ/mol | `delta_m` 兜底默认值 `delta_default` | `config/prereg.yaml` `pair_comparison.delta_m.delta_default` |
| 0.251 eV | P1 r2SCAN-3c 垂直 IP 对 12 个气相锚点的 MAE | `docs/10` §2.3、`outputs/week4/p1_decision_stability.md` §1 |
| 153 / 780 | core set / broad pool 的 pair 数 `C(N,2)` | `config/scientific_definitions.yaml` `dataset.pair_counts` |

**待核实项（未写入任何确定数值）**：`R_env` 层当前无数值（`docs/01` §2 表注）；`sigma_conf` / `sigma_geom` / `sigma_env` 均为「待算」（`docs/08` §5）；`delta_m` 的 max() 数值未冻结（D5）。以上均按「宁可不写也不编造」处理。

---

## 附录 B：本报告依据的仓库文件清单

| 类别 | 文件 |
| --- | --- |
| 科学定义 / 预注册 | `config/scientific_definitions.yaml`、`config/prereg.yaml` |
| 执行文档 | `计划.md`、`README.md`、`docs/00`–`docs/10` |
| 数据集 | `data/metadata/core_set.csv`、`data/metadata/broad_pool.csv`、`data/metadata/chemical_space_metadata.md` |
| 外部锚点 | `data/anchors/gas_phase_anchors.csv`、`data/anchors/solution_redox_anchors.csv`、`data/anchors/solution_anchor_verification.md` |
| 产物 | `outputs/week1/`、`outputs/week2/`、`outputs/week3/`、`outputs/week4/` |
| 计划纯文本 | `outputs/_plan_docx.txt` |

---

## 附录 C：核查本报告结论的复现命令

```powershell
# 元数据与锚点一致性
.venv\Scripts\python.exe scripts\build_metadata.py --check
.venv\Scripts\python.exe scripts\validate_anchors.py
.venv\Scripts\python.exe scripts\audit_solution_anchors.py

# Gate 记录：Gate 0 应为 CLOSED；Gate 1 应为 NOT CLOSED（blocker = 溶液锚点 31 行 est）
.venv\Scripts\python.exe scripts\freeze_gates.py --stage all

# 单元测试
.venv\Scripts\python.exe -m pytest tests -q
```

---

## 附录 D：偏差 → 未做项 → 里程碑 的收口关系

| 缺口 | 相关偏差 | 对应 §5 优先项 | 影响的里程碑 |
| --- | --- | --- | --- |
| 溶液锚点（31 行 est） | D5（`delta_m` 来源之一） | ① | M1 |
| 弥散函数边界（EA 符号） | D2（方法栈简化代价） | ② | —（裁断 EA 符号） |
| 目标层几何 T2（`sigma_geom`） | D6（P1 为垂直量） | ③ | M5 |
| `eps` 扫描 T3（`sigma_env`） | D5（`delta_m` 合成来源） | ④ | M5 |
| `delta_m` 数值 / `z` 一致性 | D3、D5 | ③、④ | M5、M6 |
| C1 条件配位态 | —（未做） | ⑤ | M4 |
| ML / AL 结论强度 | D1（扩展触发条件） | ⑥ | M5、M6 |

---

## 附录 E：`docs/00`–`docs/10` 逐篇职责（本报告引用索引）

| 文档 | 职责 |
| --- | --- |
| `docs/00_stage0_definitions.md` | Stage 0 定义冻结汇总 + Gate 0 判据（15 条） |
| `docs/01_stage1_external_anchors.md` | 三类锚点用途与 tolerance 来源、条件字段落位 |
| `docs/02_stage1_method_audit.md` | 方法审计协议、四个 arms、Gate 1 判据 |
| `docs/03_week1_2_report.md` | Week 1–2 交付物与可复现验证结果 |
| `docs/04_stage1_xtb_audit_result.md` | GFN2-xTB 审计臂实测（12 分子，ΔSCF / Koopmans） |
| `docs/05_stage2_broad_pool_p0.md` | broad pool P0 与化学空间覆盖 |
| `docs/06_stage1_solution_anchor_audit.md` | 溶液锚点逐条核验（31 行仍 `est`，2 处引用错配） |
| `docs/07_orca_setup_and_runner.md` | ORCA 安装、版本探测、runner 与标定 |
| `docs/08_stage2_production_protocol.md` | 生产协议（三层臂、几何 G1/G2、sigma 来源、预算优先级） |
| `docs/09_week3_report.md` | Week 3 报告（P0 58/58、覆盖、决策稳定性预演） |
| `docs/10_week4_report.md` | Week 4 报告（T1 54/54、P2、`unbound_anion` 18/18、Gate 状态） |
