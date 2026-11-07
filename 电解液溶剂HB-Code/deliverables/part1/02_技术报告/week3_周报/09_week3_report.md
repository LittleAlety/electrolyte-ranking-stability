# Week 3 报告 —— Stage 2：廉价层 P0、覆盖检查、锚点核验、ORCA 就绪

日期：2026-09-29。对应 v2 §7.1（先审计再冻结生产协议）、§19 Stage 2、计划 §10 的 Week 3–4。

> 本报告只陈述**真实跑出来的**数字。P0 是轨道能代理量，**不是**真实氧化还原电位；
> 本轮**没有** r2SCAN-3c 数据（ORCA 未安装），所有排序结论都只是「P0 内部」的预演。

---

## 1. 本轮四条线

| 线 | 内容 | 状态 |
| --- | --- | --- |
| A | broad pool（40）+ core set（18）的 P0 廉价层批量计算 | ✅ 58/58 `ok`，0 失败 |
| B | core vs broad 的多轴化学空间覆盖检查 + 决策稳定性预演 | ✅ 报告 + 3 图 |
| C | 溶液相 redox 锚点（31 行）逐行核验 | ✅ 核验完成，**0 行升级**（诚实保留 `est`） |
| D | ORCA / r2SCAN-3c 臂「就绪化」（runner + 安装指南 + mock 测试） | ✅ 可 dry-run；真跑待安装 |

生产协议的**预注册**见 `docs/08_stage2_production_protocol.md`（三层臂、几何 G0/G1/G2、
状态与参考态、sigma 来源、预算优先级、图表清单）。

---

## 2. 结果

### 2.1 P0 廉价层（GFN2-xTB 6.7.1，几何 G1）

- 运行：**58/58 成功**（broad 40/40，core 18/18），**0 个 QC flag**，无 imaginary mode、无未收敛。
- `p0_ox = -eps_HOMO`：10.176 / 11.439 / 13.857 eV（min / median / max）；
  `p0_red = +eps_LUMO`：-6.825 / -5.394 / **+0.898** eV。
- **6 个分子的 LUMO 为正**（B09 DEE、B12 THF、B13 2MeTHF、B14 DIOX、B15 DMM、C08 DOL）：
  这些醚类的**气相**自由基阴离子大概率不束缚，P1 阶段预计会标 `unbound_anion`——
  这是 v2「醚类还原稳定性不能只用 LUMO 判断」的预期表现，不是 bug。
- 氟化分子占据氧化侧高端（B17 HFE347、B18 HFE7100、B32 TFP、B05 TFMEC、B19 BTFE）；
  硅氧烷 / 亚砜在低端。
- xTB 6.7.1 的 `--opt` 输出本身已含 `Mol. a(0)` 与偶极，故 `aux_alpha_bohr3` 全量有值；
  另对 10 个分子跑了独立 `--alpha` 作业做交叉确认（例：MPC 74.715048 vs 74.715051，一致）。
  **alpha / dipole 只作 auxiliary，不参与 P0 排序**（`scientific_definitions.yaml` 明确排除）。

### 2.2 与 Week 2 的交叉可复现性

Week 2 的 12 个审计分子与 Week 3 重算结果逐一对齐：`p0_ox` 最大绝对偏差 **0.0063 eV**
（仅 EA 一个分子，来自独立的 RDKit 嵌入/优化路径），其余 **0.0000 eV**。
→ 管线可复现，P0 定义没有在两次运行之间漂移。

### 2.3 化学空间覆盖（图见 §5）

- broad pool 相对 core set 的扩展轴：**family 数**（8 → 14）、**氟化对照**（新增 HFE347/HFE7100/
  BTFE/TFP/FEMC 等）、**硅氧烷 / 亚硫酸酯 / 磺内酯**等新家族、**分子量跨度**（上探至 TFP 344 g/mol）。
- 仍稀疏的轴：**芳香族仅 1 个**（DPC）、**非氟卤素仅 1 个**（ClEC）、
  siloxane / sulfite / sultone 各 1–2 个；**donor_count 的上限其实在 core set**（5 > broad 的 4）。
- 结论：broad pool 扩的是**化学多样性**，不是**配位数上限**；这不是缺陷，但报告覆盖时必须说清楚。

### 2.4 决策稳定性预演（**仅 P0 内部**）

| 量 | 值 | 含义 |
| --- | --- | --- |
| Kendall tau(P0_ox, P0_red)，合并 58 分子 | **-0.302** | 氧化侧与还原侧排序**负相关** |
| top-k 重叠（ox vs red），k=10% / 20% | **0.000 / 0.000** | 两个目标选出的分子集**几乎不相交** |
| top-k 重叠（ox vs red），k=30% | 0.176（Jaccard 0.097） | 仍很低 |
| core-only 领袖在新池中的存活比例 | 1/2、3/4、5/5（k=10/20/30%） | pool 扩大后 top-k 会换人，**必须报告 pool 定义** |
| 「优于 DME」vs「优于 AN」集合 Jaccard | 0.568 | reference ligand 的选择确实会改变「谁入选」 |
| P0_ox 整体平移后 tau | **1.000** | P0 排序本身**不含 R**，R 依赖性只能到 P1/P2 才能判 |
| MW / TPSA / alpha / dipole 的 top-k 与 P0_ox 的 Jaccard | ≈ 0（最高 0.259） | P0 不可被平凡廉价描述符复现 |

**这是本轮最有决策意义的发现**：同一种「便宜代理量」在**不同目标方向**上给出的候选集
几乎不重叠——所以「用 P0 排序稳不稳」这句话，脱离目标方向与 pool 定义是没有意义的。

### 2.5 溶液相锚点核验（31 行 / 16 物种）

- 逐行核验后 **0 行升级**：没有找到条件统一、可直接引用的原始实验表。
- 失败原因分类：solvent–anion 耦合 7、计算型筛选未取到数值 5、实验条件不匹配 5、
  无可回溯来源 5、仅二手综述趋势 5、**引用错配 2**、来源不含该物种 1、来源不含数值 1。
- **两处引用错配**（重要）：
  1. **SL（sulfolane）**：所引 `10.1149/1.1838419` 研究的是**非环状不对称砜**，不是环状 sulfolane；
  2. **EC 还原 0.9 V**：所引 `10.1149/1.1415547` 实为 **THF 稀溶液 CV**，与行内「纯溶剂 / 1 M LiPF6 / LSV」不符。
- 不确定度按确定性规则放大（还原 +0.2 V、氧化 +0.3 V，上限 0.8 V），规则写在
  `scripts/audit_solution_anchors.py` 内可复算。
- 证据表：`data/anchors/solution_anchor_verification.md`；报告：`docs/06_stage1_solution_anchor_audit.md`。
- **Gate 1 未因此关闭**：`method=est` 行数仍为 31，这是真实状态而非遗漏。

### 2.6 ORCA / r2SCAN-3c 就绪化

- `src/electrolyte_ranking/orca.py` 补齐驱动层：`run_orca`、`ORCAResult`、`parse_orca_output`、
  `read_orca_version`、`resolve_nprocs`、`ORCAExecutionError`；QC flag 只使用既有词表。
- `scripts/run_orca_job.py` 支持 `--dry-run`（**没装 ORCA 也能验证输入**）、`--xyz`（生产协议要求
  用 xTB 优化几何喂进来）、`%pal` 自适应、scratch 隔离。
- 安装指南：`docs/07_orca_setup_and_runner.md`。
- mock 测试覆盖：正常终止、SCF 不收敛、opt 失败、缺能量、非零退出、空输出、超时、
  nprocs 自适应、版本解析、imaginary mode 映射。真实 ORCA 用例 `skipif` 待装。

---

## 3. Gate 现状（不粉饰）

| Gate | 状态 | 说明 |
| --- | --- | --- |
| Gate 0 | **CLOSED** | 定义 / 预注册 / metadata 未被改动 |
| Gate 1 | **NOT CLOSED** | 2 个 blocker 仍然存在：① ORCA 未安装 ② 溶液锚点 31 行仍为 `est` |

本轮解除了**第三个**潜在阻塞点：生产协议从未冻结 → 已在 `docs/08` 冻结（§1–§6）。
但按 v2 的判据，这不足以关闭 Gate 1。

---

## 4. 局限

- P0 无溶剂、无显式 Li+、无构象系综；top-k 未使用 delta_m / sigma_ij（需 P1/P2 的不确定度）。
- 决策稳定性预演只在 P0 内部比较，**不能**回答「P0 是否保留了 P1/P2 的排序」——那需要 ORCA。
- 溶液锚点仍是估算值，只能用于量级/相对排序级审计，**禁止**用于 pooled absolute regression。
- ORCA 的 Windows 产物行为（`.gbw`/`.xyz` 命名、`.out` 落盘）未经真机实测。

---

## 5. 图表清单

项目级图（`scripts/make_summary_figures.py`，清单与 SHA256 见 `outputs/figures/figure_manifest.md`）：

| 图 | 文件 | 内容 |
| --- | --- | --- |
| F0 | `outputs/figures/F0_project_pipeline.png` | 项目五段式流水线示意 |
| F1 | `outputs/figures/F1_chemical_space_coverage.png` | core vs broad 的 family / donor 覆盖 |
| F2 | `outputs/figures/F2_p0_distributions_by_family.png` | 各 family 的 P0 分布，按氟化着色 |
| F3 | `outputs/figures/F3_value_error_vs_rank_error.png` | **值误差 vs 排序误差**（本轮核心反直觉结论） |

Week 3 专用图（`scripts/run_broad_pool_p0.py` 产出）：
`outputs/week3/fig1_family_counts.png`、`fig2_mw_donor.png`、`fig3_p0_ox_fluorinated.png`。

---

## 6. 下一步（Week 4–5）

1. **安装 ORCA**（用户侧，见 `docs/07` §1–§3）→ 跑 `check_environment.py` 确认 FOUND；
2. 用 `run_orca_job.py --dry-run` 生成 EC/PC/DMC 的 r2SCAN-3c 输入，肉眼确认关键词与 `%cpcm`；
3. 真跑 T1（core set 18 x {M, M.+, M.-} 单点 @ G1），按 `docs/08` §7 的优先级推进；
4. 用 T1 结果重跑 F3（**值误差 vs 排序误差**），检验「P0 的排序是否被 r2SCAN-3c 保留」；
5. 重评 Gate 1（气相锚点趋势 + SCF 稳定性 + state identity）。

**后续进展（2026-09-29 回填）：** ORCA **6.1.1**（Windows AVX2 **msmpi** 构建）已安装并跑通（装到 `E:\ORCA\orca_6_1_1`，用 `msiexec /a` 做 administrative install，无需管理员权限，约 173 s；仓库内经 junction `.toolchain\orca\orca_6_1_1` 使用），`scripts\check_environment.py` 现输出 `orca FOUND ... version 6.1.1 [bundled]`。因此 §3 中 Gate 1 的 blocker ①「ORCA 未安装」**已解除** —— **Gate 1 现只剩 1 个 blocker：溶液锚点 `data/anchors/solution_redox_anchors.csv` 31 行仍全部为 `est`（不可回溯）**。同时 Week 4 的 T1 主扫描（core set 18 分子 × 3 电子态 r2SCAN-3c 气相单点 @ G1）已完成，**54/54 成功、0 失败**，详见 `docs/10_week4_report.md` 与 `outputs/week4/`；ORCA 细节见 `docs/07_orca_setup_and_runner.md` §10–§15 与 `docs/08_stage2_production_protocol.md` §2、§7。

---

## 7. 复现

```powershell
. .\scripts\activate_toolchain.ps1
.venv\Scripts\python.exe -m pytest tests -q                 # 全绿
.venv\Scripts\python.exe scripts\build_metadata.py --check  # OK
.venv\Scripts\python.exe scripts\validate_anchors.py        # PASS
.venv\Scripts\python.exe scripts\run_broad_pool_p0.py --pool both --jobs 4
.venv\Scripts\python.exe scripts\audit_solution_anchors.py
.venv\Scripts\python.exe scripts\make_summary_figures.py
.venv\Scripts\python.exe scripts\freeze_gates.py --stage all
.venv\Scripts\python.exe scripts\freeze_gates.py --stage 2
```