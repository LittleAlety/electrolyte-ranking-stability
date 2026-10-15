# Week 25 计算预算与执行规模台账

核心文件 §21《计算预算与执行规模》对照审计。**零新增电子结构计算**：全部数字由
`scripts/build_compute_budget_ledger.py` 从既有产物 `outputs/**` 与冻结 `config/**` 重算，
并写死关键口径断言；数据一改即报错。

- 核心文件：`../核心文件/ranking-electrolyte-materials-v2.md`（§21 = 第 1305–1338 行）
- 机器可读：`outputs/week25/compute_budget_ledger.json`、`outputs/week25/compute_budget_ledger.csv`
- 复算：`python scripts/build_compute_budget_ledger.py`；幂等校验：`python scripts/build_compute_budget_ledger.py --check`

## 0. 口径与机时声明

- 已执行作业工件口径：`outputs/<week*>/**.out` 下的 `.out`（1 个 `.out` = 1 次已执行的 ORCA/xTB 作业工件），排除 `outputs/_*_scratch/**`（中间/探针运行，653 个）与 `outputs/smoke/**`（烟测，2 个）。
- **本台账不含任何绝对机时（CPU-core-hours）估算**：仓库只在 50 个 JSON 里记录 wall-clock 秒
  （如 `outputs/week4/p1_core_set_summary.json:wall_clock_seconds_median = 29.77` s、
  `outputs/week5/c1_li_coordination_summary.json:timing_seconds.median_job = 37.66` s），
  但**没有任何 CPU-time 或 `nprocs x wall` 的 CPU-core-hours 字段**；因此 §21 的 median CPU-core-hours 记为 `not_available_in_repo`。
- 每层作业规模只做“已执行计数”，不做单作业机时外推。

## 1. §21 原文口径逐条摘录

| 编号 | 行号 | 原文摘录（≤60 字/条） |
| --- | --- | --- |
| S1 | §21 L1307–1319 | `N_{\mathrm{mol}} \times N_{\mathrm{charge}} \times N_{\mathrm{conformer}} \times N_{\mathrm{environment}} \times N_{\mathrm{motif}}.` |
| S2 | §21 L1321 | `60 个母分子很容易扩展成上千次 optimization/frequency/single-point jobs。因此…` |
| S3 | §21 L1323 | `- median CPU-core-hours；` |
| S4 | §21 L1324 | `- 90th percentile job cost；` |
| S5 | §21 L1325 | `- failure rate；` |
| S6 | §21 L1326 | `- conformer survival rate；` |
| S7 | §21 L1327 | `- Li-motif survival rate；` |
| S8 | §21 L1328 | `- frequency cost fraction。` |
| S9 | §21 L1330 | `之后再冻结 core-set 最终规模。` |
| S10 | §21 L1332–1336 | `如果 frequency 成本过高，应在 benchmark 后决定是否：` |
| R1 | §5.1 L352 | `建议 $N_{\mathrm{core}}\approx60$–100。` |
| R2 | §5.1 L358 | `建议 $N_{\mathrm{pool}}\approx300$–1000，视自动化和资源而定。` |
| R3 | §19 Stage1 L1153 | `1. 选 8–10 个 method-audit molecules；` |
| R4 | §7.3 L527 | `可从 range-separated hybrid + triple-$\zeta$ basis 作为生产候选，例如 $…` |
| R5 | §5.1 L366 | `若项目时间有限，broad pool 可以只做到 $P_0$，但结构和 metadata 仍应一次性建立。` |

## 2. §21 逐条对照台账（主表）

| 项目 | 核心文件要求 | 实际执行 | 来源(文件:字段) | 状态 | 备注 |
| --- | --- | --- | --- | --- | --- |
| S1 | N_{\mathrm{mol}} \times N_{\mathrm{charge}} \times N_{\mathrm{conformer}} \times N_{\mathrm{environment}} \times N_{\mathrm{motif}}. | N_mol: core 18 + broad 40; N_charge: 3 态; N_conformer: T6 子集 32 个构象/12 分子; N_environment: 预注册 4 层 (+SMD acetonitrile/water); N_motif: 12 个保留 motif | config/scientific_definitions.yaml:dataset.core_set.n_rows|broad_pool.n_rows; outputs/week6/t6_conformer_spread.json:counts.p1.n_conformers_total; outputs/week22/dielectric_limit.json:preregistered_epsilon_values; outputs/week5/li_motif_generation.json:n_kept_motifs | **PASS** | 五个因子均可在仓库定位；无单一乘积字段。构象因子仅覆盖 12 分子审计子集，非全 core。 |
| S2 | 60 个母分子很容易扩展成上千次 optimization/frequency/single-point jobs。因此… | 母分子 core 18 + broad 40 = 58；published .out 作业工件 1657（>1000）；全目录 .out 2312 | outputs/**/*.out (script artifacts scan) | **PASS** | “>1000 jobs”成立（published 1657）。母分子合计 58 接近 60，但 core 单独仅 18（见 R1）。 |
| S3 | - median CPU-core-hours； | 无 CPU-core-hours 字段。wall-clock: P1 core median 29.77 s（total 2194.13 s, nprocs 8）；C1 median job 37.66 s / max 1944.73 s | outputs/week4/p1_core_set_summary.json:wall_clock_seconds_median; outputs/week5/c1_li_coordination_summary.json:timing_seconds.median_job | **PARTIAL** | median CPU-core-hours = not_available_in_repo（无 CPU-time / 无 nprocs*wall 记录）；仅有 wall-clock 秒。 |
| S4 | - 90th percentile job cost； | 90th percentile job cost = not_available_in_repo；仓库仅有 median 与 max。 | outputs/week4/p1_core_set_summary.json:wall_clock_seconds_by_state (median/max) | **MISSING** | T6 的 p90_spread_ev 是构象能量离散度，不是作业成本。 |
| S5 | - failure rate； | C1: n_jobs 92 / n_ok 91 / execution_failed 1（rate 0.0109）；其余多数 summary n_failed=0；全目录 .out 硬失败 2（均在 scratch，published 0） | outputs/week5/c1_li_coordination_summary.json:status_counts; outputs/week*/**/*.json:n_failed | **PASS** | failure rate 可算且有明确来源；但无跨阶段统一汇总表（多数 summary 不写 n_failed）。 |
| S6 | - conformer survival rate； | T6: 12 分子、构象 total 32 / scored 32、failures 0；manifest n_confs 24 / keep 4 | outputs/week6/t6_conformer_spread.json:counts.p1; outputs/week6/t6_conformer_manifest.json:parameters | **PARTIAL** | 有构象计数与 0 失败，但无显式 conformer survival rate 字段，且仅 12 分子审计子集。 |
| S7 | - Li-motif survival rate； | motif 预筛: candidates 46 -> kept 12（keep ratio 0.2609）；有 motif 分子 10；DFT 臂 91/92 ok | outputs/week5/li_motif_generation.json:n_candidates/n_kept_motifs; outputs/week5/c1_li_coordination_summary.json:n_ok | **PASS** | 预筛保留率 12/46 与 DFT 执行存活 91/92 均可复算；无单一 frozen survival 字段。 |
| S8 | - frequency cost fraction。 | frequency cost fraction = not_available_in_repo；T2 记 n_opt_jobs 12、n_sp_jobs 36、n_imaginary_unresolved 2，但 opt+freq 合并计时、无 frequency-only 成本 | outputs/week4/t2_opt_freq_summary.json:n_opt_jobs/n_sp_jobs/per_molecule.opt_seconds | **MISSING** | 无 frequency-only 机时或占比字段。 |
| S9 | 之后再冻结 core-set 最终规模。 | core-set 规模已冻结为 18（category: family 覆盖分子；含 2-3 机理对照） | config/scientific_definitions.yaml:dataset.core_set.n_rows/size_note | **PARTIAL** | 规模已冻结且有书面理由；但冻结并非建立在 §21 六项统计齐备之上（六项中有 2 项 MISSING、2 项 PARTIAL）。 |
| S10 | 如果 frequency 成本过高，应在 benchmark 后决定是否： | 三项处置均有记录：near-degenerate 定向升级已实现（R8 targeted two-guess）；热修正选择完全不做（0 K 电子能 + 垂直 gap）；frequency 仅对 G2 审计子集做 | docs/17_plan_optimization_branchABC.md:25; docs/31_plan_revision_expert_review.md:340; outputs/week23/targeted_two_guess.json | **PARTIAL** | 非逐条对照核心文件三选项；「只对低能构象做 freq」仅以 12 分子审计子集局部实现。 |

## 3. §21 状态统计

| 状态 | 条数 |
| --- | --- |
| PASS | 4 |
| PARTIAL | 4 |
| MISSING | 2 |
| NOT_APPLICABLE | 0 |

- §21 直接条款共 10 条：PASS 4、PARTIAL 4、MISSING 2、NOT_APPLICABLE 0。

## 4. 关联预算口径（§5.1 / §7.3 / §19 Stage 1）

| 项目 | 核心文件要求 | 实际执行 | 来源(文件:字段) | 状态 | 备注 |
| --- | --- | --- | --- | --- | --- |
| R1 | 建议 $N_{\mathrm{core}}\approx60$–100。 | core set 实际 18（建议 60–100） | config/scientific_definitions.yaml:dataset.core_set.n_rows/size_note | **PARTIAL** | 主动取舍：明确书面记录缩小到 18 以侧重机制，非疏漏。 |
| R2 | 建议 $N_{\mathrm{pool}}\approx300$–1000，视自动化和资源而定。 | broad cheap pool 实际 40（建议 300–1000） | config/scientific_definitions.yaml:dataset.broad_pool.n_rows | **PARTIAL** | 主动取舍：只做 P0（见 R5），规模远低于建议区间。 |
| R3 | 1. 选 8–10 个 method-audit molecules； | method-audit molecules 实际 12（xTB：neutral/cation/anion） | outputs/week2/method_audit_xtb_summary.json:n_molecules | **PASS** | 分子数达标（12 ≥ 8–10）；泛函/基组维度覆盖另有 gap（见 docs/41 D1/D3），不在本条口径内。 |
| R4 | 可从 range-separated hybrid + triple-$\zeta$ basis 作为生产候选，例如 $… | 生产单点 = r2SCAN-3c（def2-mTZVPP 复合基组，含 D4/RIJCOSX）；wB97X-D4/def2-TZVPP 仅列为审计臂 | outputs/week4/p1_core_set_summary.json:method; docs/08_stage2_production_protocol.md:42-43 | **PARTIAL** | 「由 audit 冻结方法」要求满足；但未采用 RS-hybrid 作为生产方法（主动取舍，RS-hybrid 仅审计臂）。 |
| R5 | 若项目时间有限，broad pool 可以只做到 $P_0$，但结构和 metadata 仍应一次性建立。 | broad pool 仅做 P0（GFN2-xTB opt，40 分子），结构与 metadata 一次性建立 | outputs/week3/p0_broad_pool_summary.json:n_total; config/scientific_definitions.yaml:dataset.broad_pool | **PASS** | 与核心文件「时间有限时 broad pool 可只做到 P0」一致。 |

- 关联口径共 5 条：PASS 2、PARTIAL 3、MISSING 0。

## 5. 每层作业规模（已执行计数）

| 层 | 任务 | 引擎 | 分子 | 作业 | 成功 | 期望/记录 | 来源 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| P0 | 廉价代理 GFN2-xTB opt（core） | GFN2-xTB | 18 | 18 | 18 | not_available_in_repo | `outputs/week3/p0_core_set_summary.json:n_total/n_ok` |
| P0 | 廉价代理 GFN2-xTB opt（broad pool） | GFN2-xTB | 40 | 40 | 40 | not_available_in_repo | `outputs/week3/p0_broad_pool_summary.json:n_total/n_ok` |
| Stage1-audit | xTB 方法审计（neutral/cation/anion） | GFN2-xTB | 12 | 12 | not_available_in_repo | not_available_in_repo | `outputs/week2/method_audit_xtb_summary.json:n_molecules` |
| P1 | 气相 r2SCAN-3c 单点 @G1（18 分子 x 3 态） | r2SCAN-3c (ORCA) | 18 | 54 | 54 | not_available_in_repo | `outputs/week4/p1_core_set_summary.json:n_jobs/n_ok` |
| P1 | P1 完整性审计（54 records / 36 ok；unbound_anion 18） | r2SCAN-3c (ORCA) | 18 | 54 | 36 | not_available_in_repo | `outputs/week4/p1_core_set_audit.json:n_records/n_ok` |
| T2 | G2 Opt+Freq（12 分子子集）+ 单点 | r2SCAN-3c (ORCA) | 12 | 48 | 12 | not_available_in_repo | `outputs/week4/t2_opt_freq_summary.json:n_opt_jobs/n_sp_jobs` |
| P2 | CPCM eps 扫描（12 分子 x 3 态 x 4 eps） | r2SCAN-3c (ORCA) | 12 | 144 | 144 | 144 | `outputs/week4/t3_cpcm_eps_scan_summary.json:n_jobs/n_ok` |
| T5 | 弥散基组对照（2 臂 x 12 分子） | r2SCAN (ORCA) | 4 | 24 | 24 | not_available_in_repo | `outputs/week4/t5_diffuse_control_summary.json:n_jobs/n_ok` |
| C1 | 条件 Li+ 配位（10 分子 / 12 motif） | r2SCAN-3c (ORCA) | 10 | 92 | 91 | not_available_in_repo | `outputs/week5/c1_li_coordination_summary.json:n_jobs/n_ok` |
| C1 | Li-motif 生成/预筛（46 candidates -> 12 kept） | GFN2-xTB | 10 | not_available_in_repo | not_available_in_repo | not_available_in_repo | `outputs/week5/li_motif_generation.json:n_candidates/n_kept_motifs` |
| T6 | 构象离散度审计（12 分子） | GFN2-xTB + r2SCAN-3c | 12 | 32 | 32 | not_available_in_repo | `outputs/week6/t6_conformer_spread.json:counts.p1` |
| C2 | 显式微溶剂化（12 shells） | r2SCAN-3c (ORCA) | 12 | 36 | 36 | not_available_in_repo | `outputs/week8/stage9_summary.json:n_jobs/n_ok` |
| Stage10 | 五台阶 ladder 合成（20 组合） | mixed | 10 | 20 | not_available_in_repo | not_available_in_repo | `outputs/week9/stage10_ladder.json:ladder` |
| Stage20 | xTB 双腿对照 | GFN2-xTB | not_available_in_repo | 74 | 74 | not_available_in_repo | `outputs/week19/stage20_xtb_arms.json:n_jobs/n_ok` |
| Stage21 | 反应路径/势垒 | ORCA | not_available_in_repo | 63 | 63 | not_available_in_repo | `outputs/week20/stage21_path.json:n_jobs/n_ok` |
| R4b | 裸 CPCM 导体极限诊断（54 rows） | r2SCAN-3c (ORCA) | not_available_in_repo | not_available_in_repo | not_available_in_repo | 54 | `outputs/week22/dielectric_limit.json:n_rows` |
| R4b | NEB 势垒精修（3 cells, 8 images） | ORCA | not_available_in_repo | 3 | 3 | not_available_in_repo | `outputs/week22/neb_refinement.json:n_cells/n_ok` |
| R9 | 热修正抽样（8 分子 x 3 态） | r2SCAN-3c (ORCA) | 8 | 24 | not_available_in_repo | not_available_in_repo | `outputs/week22/thermal_correction_sample.json:n_jobs` |
| R8 | 定向两腿重跑（12 分子 x 10 eps） | r2SCAN-3c (ORCA) | 12 | not_available_in_repo | not_available_in_repo | 240 | `outputs/week23/targeted_two_guess.json:n_material_cells/n_cells_total` |

`n_molecules` / `n_jobs` 的 `not_available_in_repo` 表示该 JSON 未落该字段（不是 0）。

## 6. 计算工件盘点（ORCA / xTB `.out`）

| 指标 | 数值 |
| --- | --- |
| 全目录 `.out`（含 scratch/smoke） | 2312 |
| 已发布 `.out`（排除 scratch/smoke） | 1657 |
| 其中 ORCA | 1485 |
| 其中 xTB | 172 |
| 其中其它 | 0 |
| ORCA 正常终止 | 1483 |
| xTB 正常终止 | 172 |
| ORCA 错误终止（全目录） | 2 |
| 已发布但无非正常/正常终止标记 | 2 |

ORCA/xTB 判定基于文件内 banner 与终止串（`O   R   C   A` / `xtb version`；
`ORCA TERMINATED NORMALLY` / `normal termination of xtb` / `error termination`）。

- 全目录硬失败（error termination）2 个：`outputs/_week14_scratch/libprobe/EMC_anion_moread_probe.out`、`outputs/_week14_scratch/libprobeA/EMC_moread_np1.out`
- 已发布但未分类的 2 个：`outputs/week22/neb_EC_cation_eps20/neb_EC_cation_cpcm_20.out`、`outputs/week5/c1/SL/SL_m1_dication_opt.out`

## 7. 结构化 `n_jobs` 与 active-learning 重放规模

- 含 `n_jobs` 字段的 JSON：71 个；直接求和 2349 次作业（**含 plan/summary/analysis 重复计数，仅作量级参考**）。
- Stage 8 active-learning replay：run 行 5920、curve 行 296、repeat 20（`outputs/week7/stage8_al_results.json:counts/settings`）。
- Week 24 预算合成：pool size E:oxidation 18 / C:oxidation 10；key n_T E:oxidation 15、C:oxidation 9（`outputs/week24_corealign/al_budget.json:pool_sizes/key_n_T_by_pool`）。

## 8. 数据集、方法与条件态口径

- 数据集：core `18`、broad `40`；pair count core `153` / broad `780`（`config/scientific_definitions.yaml:dataset`）。
- 生产方法：`r2SCAN-3c`（`def2-mTZVPP (composite, no diffuse)`）；RS-hybrid 进生产排序 = false；审计臂 = wB97X-D4/def2-TZVPP (docs/08 §2, 仅审计臂、不进生产排序)。
- 条件态：charge state 3 个；预注册 epsilon [5, 10, 20, 40]；实际扫描 epsilon = 5,7,10,14,20,28,40,80,200,1000,1e6；SMD 溶剂 = acetonitrile/water。

## 9. 结论（诚实口径）

### 9.1 达标
- §21 S2：1657 个已发布作业工件，>1000“上千次 jobs”成立。
- §21 S5：C1 failure rate = 1/92（`execution_failed`），有明确落盘字段。
- §21 S7：Li-motif 预筛保留 12/46，DFT 臂 91/92 ok。
- §21 S1：任务数公式五个因子均可定位（虽无单一乘积字段）。
- 关联 R3：method-audit 12 分子 ≥ 8–10；R5：broad pool P0-only 与核心文件许可一致。

### 9.2 主动取舍（有书面记录）
- core set 18（建议 60–100）、broad pool 40（建议 300–1000）：`config/scientific_definitions.yaml:dataset` 明示“侧重机制、主动缩小”。
- 生产方法 r2SCAN-3c（def2-mTZVPP，无弥散）而非 RS-hybrid 生产单点；`wB97X-D4/def2-TZVPP` 仅列为审计臂。
- 热化学路径选择 0 K 电子能 + 垂直 gap，不做 RRHO/qRRHO 修正（`docs/17_plan_optimization_branchABC.md`）。
- 构象/频率只在 12 分子审计子集做（T2/T6），非全 core。

### 9.3 未做 / 仓库不可得
- §21 S4 90th percentile job cost：`not_available_in_repo`（只有 median/max）。
- §21 S8 frequency cost fraction：`not_available_in_repo`（opt+freq 合并计时）。
- §21 S3 median CPU-core-hours：`not_available_in_repo`（只有 wall-clock 秒）。
- §21 S9 的六项统计未在冻结前齐备：规模冻结为 18 有理由，但冻结依据不是完整 §21 统计。

## 10. 统计可靠性说明

- **最不可靠的一处**：`outputs/week5/c1_li_coordination_summary.json:timing_seconds.total_wall` = 0.03 s。同一 JSON 的 `timing_seconds.sum_jobs` = 17737.6 s；
  0.03 s 对 92 个 DFT 作业物理上不可能，属占位/未计时值，引用 C1 机时时必须避开。
- 次不可靠：结构化 `n_jobs` 直接求和 = 2349 次，含 plan/summary/analysis 变体的重复计数；
  权威工件口径应取 `artifacts.out_published` = 1657。
- 两种口径差异说明见 JSON `caveats`。

## 11. 可复算性与断言

- 脚本：`scripts/build_compute_budget_ledger.py`（确定性、幂等；无时间戳）。
- 本文件由脚本从上述 JSON 渲染；`--check` 会重算 JSON/CSV/Markdown 并逐字节比对。
- 关键口径断言 44 条（core 18、broad 40、C1 92/91/1、motif 46/12、published .out 1657 等），
  任一底层数据变动都会使脚本报错而非静默出数。

