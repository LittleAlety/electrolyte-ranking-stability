# 电解液溶剂HB — 决策稳定性研究 (Electrolyte Ranking Stability)

在**很小的分子集**(core set = 18 个分子)上,用**两种**高效量子化学方法
(GFN2-xTB 与 r2SCAN-3c),研究「从廉价代理量到更真实的电子结构 / 环境模型」时,
**哪些改变只是数值平移,哪些会真正翻转材料筛选决策**,以及这些翻转背后的物理机制。

> 本项目的核心不是"筛出最好的电解液",而是
> cheap proxy → validated target → uncertainty-aware rank change → mechanism → minimal budget

## 科学依据

- 主方案: `核心文件/ranking-electrolyte-materials-v2.md`(v2)
- 阅读清单: `核心文件/ranking-electrolyte-materials-reading-list.md`
- 本项目计划: `计划.md`

## 快速开始

```powershell
# 0. 指向仓库内置的 xTB(6.7.1 Windows 构建,SHA256 已校验);装好 ORCA 后同样无需环境变量
. .\scripts\activate_toolchain.ps1

# 0b. ORCA 下载完成后一条命令放到位(默认建 junction,不额外占空间)
# .\scripts\setup_orca.ps1 -Source "E:\Downloads\orca_6_1_1_win64"

# 1. 环境自检(无 xtb/ORCA 也会正常返回)
.venv\Scripts\python.exe scripts\check_environment.py

# 2. 重建/校验元数据(CSV 是产物,不是手改文件)
.venv\Scripts\python.exe scripts\build_metadata.py --check

# 3. 校验外部锚点
.venv\Scripts\python.exe scripts\validate_anchors.py

# 4. 单元测试
.venv\Scripts\python.exe -m pytest -q

# 5. 重生成项目图（输出 outputs/figures/,含清单与 SHA256）
.venv\Scripts\python.exe scripts\make_summary_figures.py
```

## 计算栈

| 层 | 方法 | 工具 | 现状 |
| --- | --- | --- | --- |
| 几何 / 频率 / 廉价描述符 | GFN2-xTB | `xtb` | **已就绪**(仓库 `.toolchain/`,6.7.1pre) |
| 单点电子能 | r2SCAN-3c | `ORCA` | **已装 6.1.1**(Windows AVX2 **msmpi** 构建,装到 `E:\ORCA\orca_6_1_1`,仓库内经 junction `.toolchain\orca\orca_6_1_1` 使用;`check_environment.py` 现输出 `orca FOUND ... version 6.1.1 [bundled]`;安装/版本探测/msmpi 并行与路径约束/scratch 策略/性能标定/真实冒烟见 `docs/07_orca_setup_and_runner.md` §10–§15) |

代码在缺少二进制时以 `dry_run` / fake backend 运行,保证测试与流水线可先跑通;
真实数值计算需先完成 Stage 1 的 Gate 1。

## 首个科学结果(Stage 1, 已跑)

12 个有气相锚点的分子上用 GFN2 做 ΔSCF,与 NIST 锚点比较(10 个有 IP):

| 变体 | n | MAE (eV) | 误差 std (eV) | Kendall τ_b |
| --- | --- | --- | --- | --- |
| ΔSCF 垂直 IP(近似 $P_1$) | 10 | 4.451 | 0.343 | **0.911** |
| Koopmans −ε_HOMO($P_0$) | 10 | **1.320** | 0.668 | 0.689 |

值误差更小的量排序反而更差 —— v2「值误差 ≠ 排序误差」被实测证实。
完整结论与 caveat 见 `docs/04_stage1_xtb_audit_result.md`。

## Week 4 结果(T1 主扫描,已完成)

T1 = core set **18 分子 × 3 电子态** {neutral(0,1)、cation(+1,2)、anion(−1,2)} 的 **r2SCAN-3c 气相单点**,
几何为 **G1**(GFN2-xTB 优化几何,与 P0 层共用)。

- **54/54 作业全部成功,0 失败**;单作业墙钟中位数 **29.77 s**(`nprocs 8`,本机 16 逻辑核,同时跑 2 个作业)。
- 独立复核 `scripts\audit_p1_core_set.py` 直接从 ORCA 原始 `.out` 重新解析并交叉核对:54 条记录、18 个分子全部三态齐全,
  `energy_mismatch = 0`、`scf_failed = 0`、`abnormal_termination = 0`、`spin_contamination_flag = 0`
  (阳/阴离子 ⟨S²⟩ 都落在 0.75±0.05 内),但 **`unbound_anion = 18`**(18 个分子的气相自由基阴离子全部不束缚)。
- 与外部气相 IP 锚点比较(12 个分子有锚点):

| 变体 | MAE (eV) | bias (eV) |
| --- | --- | --- |
| $P_0$ Koopmans(GFN2-xTB `-eps_HOMO`) | 1.377 | +1.279 |
| GFN2-xTB ΔSCF 垂直 IP | 4.481 | +4.481 |
| **$P_1$ r2SCAN-3c 垂直 IP** | **0.251** | −0.179 |

- 决策稳定性 $P_0\to P_1$:氧化侧 Kendall $\tau_b$ **0.673**、top-20% 名单重叠 0.5、top-10% 重叠 0.0;
  还原侧 $\tau_b$ **0.595**、top-20% 重叠 0.5。

产物与脚本:`outputs/week4/p1_core_set.csv`、`outputs/week4/p1_core_set_summary.json`、
每分子 `outputs/week4/orca/<name>/`;复核 `outputs/week4/p1_core_set_audit.{csv,json,md}`;
派生/比较/稳定性 `outputs/week4/p1_core_set_derived.csv`、`outputs/week4/p1_anchor_comparison.json`、
`outputs/week4/p1_decision_stability.{json,md}`;批量 runner `scripts\run_core_set_p1.py`(可断点续跑)、
P2 环境层 `scripts\run_core_set_p2.py`(同样 3 个态打开 SMD acetonitrile,几何复用 T1)、
复核脚本 `scripts\audit_p1_core_set.py`、分析脚本 `scripts\analyze_p1_core_set.py`。

Week 4 图(清单见 `outputs/figures/figure_manifest_week4.md`):
`outputs/figures/F4_rank_migration_p0_to_p1.png`、`F5_reduction_axis_koopmans_vs_dscf.png`、
`F6_decision_stability_indicators.png`、`F7_shift_structure.png`。

**Week 4 收尾(2026-09-29 补)**

- **P2 环境层分析**:`outputs/week4/p2_environment_effects.csv`、`p2_decision_stability.{json,md}`、图 `F8`。
  唯一变量 = 环境(气相 -> SMD 乙腈),方法/基组/几何全不变。
  ΔIP 均值 **−2.393 eV**(std 0.293,跨度 4.55 eV)、ΔEA 均值 **+2.173 eV**(std 0.311);
  P1→P2 氧化 Kendall τ_b **0.895**、还原 **0.673**。
- **两级台阶对比(核心结论)**:P0→P1(换方法)IP 位移 −1.550 eV 但 **std 0.714 eV**、氧化 τ_b 0.673;
  P1→P2(换环境)位移更大(−2.393 eV)却 **std 只有 0.293 eV**、氧化 τ_b 0.895。
  即 **位移更大不等于决策更坏——决定决策是否被改写的是位移的方差,不是位移本身**。
- **`z` 因子修正**:分析脚本原先把 pair 解析阈值写死为 `z = 1.96`,与 `config/prereg.yaml` 冻结的
  `pair_comparison.z_factor.value = 1.0` 不一致;现改为**主判据 `z = 1.0` + 敏感性 `z = 1.96` 并列报告**。
  未改动任何冻结项(`config/prereg.yaml` 逐字节不变,sha256 `e89f2e2a…f340`),**Gate 0 仍为 CLOSED**。
- **T5 弥散函数对照(裁断气相 EA 符号)**:在同泛函 r2SCAN、只换基组的三臂对照下
  (`def2-TZVPP` 无弥散 / `def2-TZVPD` 含弥散 / `r2SCAN-3c` 生产基准),加弥散把 EA
  **系统性下拉 0.34–1.60 eV**(四个分子方向完全一致),但**不足以翻转符号**
  (`def2-TZVPD` 下 `E(anion) − E(neutral)` 仍为 +0.87 ~ +0.93 eV)。
  结论:气相「全不束缚」**方向上确系基组缺弥散所致**,而 0.01 eV 量级的束缚判定
  **超出本方法适用域**(这是一个 applicability-domain 结论,不是对实验的判决)。
  产物 `outputs/week4/t5_diffuse_control.csv`、`t5_diffuse_control_summary.json`、
  `outputs/week4/t5_diffuse_control/`;脚本 `scripts\run_diffuse_control.py`;图 `F9`。
- **与新《详细执行计划 v1.0》的对齐**:逐 Stage 映射、里程碑 M0–M6 达成情况与偏差记录 D1–D7 见
  `docs/11_plan_alignment.md`;摘要见 `计划.md` §15。

## 图表（每轮成果都带图）

项目级图由 `scripts/make_summary_figures.py` **确定性重生成**，清单与输入/输出的 SHA256 见
`outputs/figures/figure_manifest.md`：

| 图 | 内容 |
| --- | --- |
| `outputs/figures/F0_project_pipeline.png` | 项目五段式流水线（proxy → target → rank change → mechanism → budget） |
| `outputs/figures/F1_chemical_space_coverage.png` | core set vs broad pool 的 family / donor 覆盖 |
| `outputs/figures/F2_p0_distributions_by_family.png` | 各 family 的 P0 分布（按氟化着色） |
| `outputs/figures/F3_value_error_vs_rank_error.png` | **值误差 vs 排序误差**（核心反直觉结论） |

Week 3 专用图（由 `scripts/run_broad_pool_p0.py` 产出）：
`outputs/week3/fig1_family_counts.png`、`fig2_mw_donor.png`、`fig3_p0_ox_fluorinated.png`。

Week 4 专用图(由 `scripts\analyze_p1_core_set.py` 产出,清单见 `outputs/figures/figure_manifest_week4.md`):
`outputs/figures/F4_rank_migration_p0_to_p1.png`、`F5_reduction_axis_koopmans_vs_dscf.png`、
`F6_decision_stability_indicators.png`、`F7_shift_structure.png`。

## 跑一个真实 xTB 任务

```powershell
. .\scripts\activate_toolchain.ps1
.venv\Scripts\python.exe scripts\run_xtb_job.py `
    --name EC --smiles "C1COC(=O)O1" --charge 0 --job opt --outdir outputs\smoke
```

输出 `EC_xtb.json`(解析结果 + provenance + QC flags)与 `EC_opt.out`(原始输出)。
阴离子会正确得到 `unbound_anion` 标记而不是伪精确的绝热电子亲和能。

## 目录

| 路径 | 内容 |
| --- | --- |
| `计划.md` | 主计划(定位/规模/协议/周计划/交付物) |
| `config/` | `scientific_definitions.yaml`(定义冻结)、`prereg.yaml`(预注册阈值) |
| `data/metadata/` | `core_set.csv`(18)、`broad_pool.csv`(~40) |
| `data/anchors/` | 气相 / 溶液相外部参考锚点 |
| `src/electrolyte_ranking/` | 库: toolchain / xtb / orca / ranking / uncertainty / provenance / qc |
| `scripts/` | 环境自检、元数据构建、锚点校验、运行器 |
| `tests/` | 单元测试(无 QM 二进制也必须通过) |
| `docs/` | Stage 说明文档 |
| `outputs/weekN/` | 每周可复现产物 |

## 工程约定(轻量借鉴 `电解质ML`)

- **可审计**: 每个数值可追溯到 mol_id / motif / 几何 / 方法 / 原始输出 / QC 状态。
- **确定性**: xTB 子进程固定单线程,避免 OpenMP 归约次序导致的几何漂移。
- **预注册**: 阈值、k 值、随机种子在看结果前冻结(`config/prereg.yaml`)。
- **verifier**: 关键产物由脚本重建而非手改(`build_metadata.py --check`)。

## 状态

- [x] 项目骨架 / 计划文档
- [x] Week 1 — Stage 0: 定义冻结、核心集、QC 状态机 → **Gate 0 CLOSED** (`outputs/week1/gate0_record.md`)
- [x] Week 2 — Stage 1: 外部锚点、方法审计、工具链、统计库 → **Gate 1 NOT CLOSED**(2 个 blocker:ORCA 未装、溶液锚点待核,见 `outputs/week2/gate1_record.md`) (2026-09-29 回填:其中「ORCA 未安装」已解除 —— ORCA **6.1.1** 已装并可跑,详见下方 Week 4)
- [x] Stage 1 xTB 审计臂已跑(12 分子 vs 气相锚点);r2SCAN-3c 臂待 ORCA (2026-09-29 回填:ORCA 6.1.1 已装,r2SCAN-3c 臂已跑,见 Week 4)
- [x] Week 3 — Stage 2 起步: broad pool(40)+core(18) 的 P0 廉价层(**58/58 成功**)、覆盖检查、决策稳定性预演;溶液锚点逐行核验(**0 行升级,诚实保留 est**);ORCA runner 就绪(dry-run 可用) → **Gate 1 仍 NOT CLOSED** (2026-09-29 回填:ORCA blocker 已解除;T1 已完成;Gate 1 仅剩溶液锚点估读)
- [x] Week 4 — Stage 3 起步: T1(core 18 × 3 电子态,r2SCAN-3c 气相单点 @ G1)**54/54 成功、0 失败**;对气相锚点的垂直 IP:MAE **0.251 eV**(r2SCAN-3c) / 1.377 eV($P_0$ Koopmans) / 4.481 eV(GFN2-xTB ΔSCF);$P_0\to P_1$ Kendall $\tau_b$ **0.673**(氧化)/ **0.595**(还原),top-20% 重叠 **0.5**;P2 环境层已启动 → **Gate 1 仅剩 1 个 blocker:溶液锚点 31 行仍为 `est`**
- [ ] Week 4-5 — Stage 3: ORCA 到位后跑 r2SCAN-3c(P1),重跑「值误差 vs 排序误差」 (2026-09-29:T1 已完成,见上;P2 已启动,重跑 F3 与不确定度仍进行中)

Week 1–2 明细见 `docs/03_week1_2_report.md`;Week 3 明细见 `docs/09_week3_report.md`;
Week 4 明细见 `docs/10_week4_report.md`;与新《详细执行计划 v1.0》的对齐见 `docs/11_plan_alignment.md`;
生产协议见 `docs/08_stage2_production_protocol.md`。

## 成果输出（交付层）

对外交付件放在与代码仓库并列的 **`E:\Claude Code\电解液溶剂-HB\成果输出`**（对标下游项目
`E:\Claude Code\电解质ML\成果输出` 的布局）：顶层 `README.md`（索引）与 `数据结果汇总.md`（全周次汇总），
以及 `week1`–`week4` 四个目录——每个含蒸馏结果表（CSV）、汇总（JSON）、报告（MD）、
`artifacts/`（PNG 图）、`SHA256SUMS`（逐文件校验）与 `verification.json`（QC 断言 + 源命令）。

该目录**只放蒸馏产物与图**，不放原始 ORCA/xTB 输出与二进制 scratch（原始输出去仓库 `outputs/` 取），
并且可以由脚本**确定性重建**：

```powershell
.venv\Scripts\python.exe scripts\build_deliverables.py
```

