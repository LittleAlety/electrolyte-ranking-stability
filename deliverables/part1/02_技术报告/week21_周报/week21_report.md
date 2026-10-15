# Week 21 成果小结 —— Stage 22（批次 A：三臂对齐 + σ 相图 + 前瞻检验）

Week 21 执行 `docs/31_plan_revision_expert_review.md` 的批次 A：**R1（含 R10）、R2、R3、R6、R4(a)**。
全部是纯分析与纯措辞，零新增电子结构、零冻结件改动——所以本周没有一条新的 SCF / Opt 记录，
所有结论都来自已有产物的重新组织与前一轮判据的留出检验。

> 周内最不可回避的一条更正是口径上的：Week 4 那张表里的三条臂并不在同一批分子上评分
> （n = 12 / 10 / 12），所以它们印在一起的 `tau_b` 本来不可比。本周先把三条臂对齐到同一批 10 个分子，
> 再谈谁高谁低；对齐之后，三对配对检验的 95% CI **全部跨 0**。

完整版本见 `week21_report_full.md`。

## 1. 本周做了什么

批次 A 是纯分析、纯措辞的一轮（零新增电子结构、零冻结件改动）：R1（含 R10）把 Week 4 的三条臂对齐到同一批 10 个分子之后再做配对检验；R2 用合成的（均值, 离散度）相图取代 Week 9 的 rho(std, tau_b) = -0.851；R3 把 Week 10 的判据先在发现集上冻结、再到留出集上打分；R6 / R4(a) 只改措辞。

## 2. 关键数字

对齐后（n = 10）：P0 Koopmans MAE 1.349 eV、tau_b 0.6889；GFN2 Delta-SCF MAE 4.481 eV、tau_b 0.9111；P1 r2SCAN-3c MAE 0.255 eV、tau_b 0.7778。配对 Delta tau_b（GFN2 - P1）= +0.1333，95% CI [-0.200, 0.550]，精确配对置换 p = 0.8049，CI 跨 0 ⇒ 三条臂两两之间全部 unresolved。相图：max abs Delta tau_b（均值平移）= 0.000、合成 rho(std, tau_b) = -1.000、合成 rho(abs(mean), tau_b) = 0.000、实测 rho(std, tau_b) = -0.8511。前瞻：带符号规则命中 3/4、朴素规则命中 2/4。

## 3. R1 + R10：三臂对齐到同一批分子之后，排序差异并不显著

| 臂 | n | MAE (eV) | bias (eV) | tau_b |
| --- | --- | --- | --- | --- |
| P0 Koopmans（GFN2-xTB） | 10 | 1.3495 | +1.2314 | 0.6889 |
| GFN2 Delta-SCF（xTB） | 10 | 4.4811 | +4.4811 | 0.9111 |
| P1 r2SCAN-3c（ORCA） | 10 | 0.2546 | -0.1694 | 0.7778 |

| 配对（A - B） | Delta tau_b | 配对 95% CI | 精确置换 p | 跨 0 |
| --- | --- | --- | --- | --- |
| GFN2_dSCF_xTB - P1_r2scan3c | +0.1333 | [-0.200, 0.550] | 0.8049 | 是 |
| GFN2_dSCF_xTB - P0_koopmans_xTB | +0.2222 | [-0.177, 0.650] | 0.7210 | 是 |
| P1_r2scan3c - P0_koopmans_xTB | +0.0889 | [-0.203, 0.488] | 0.8283 | 是 |

> 从本周起，项目对外只能说「MAE 的排序与 `tau_b` 的排序不一致」，不能说「Delta-SCF 的排序显著更好」：
> 观测到的 Delta tau_b = +0.1333 落在 95% CI [-0.200, +0.550] 内，精确配对置换 p = 0.805。

## 4. R2：把 rho = -0.851 换成一张可以直接读的相图

| 量 | 值 |
| --- | --- |
| 网格 | 均值 33 格 x 离散度 41 格，每格 2000 次重复（曲线 20000 次） |
| max abs Delta tau_b（均值平移 vs mean = 0） | 0.0000 |
| 合成 rho(std, tau_b) / rho(abs(mean), tau_b) | -1.000 / 0.000 |
| 实测 rho(std, tau_b)（native -0.8146） | -0.8511 |
| 实测 rho(abs(mean), tau_b) | -0.5350 |
| 实测 rho(std, f_unresolved) | 0.8936 |
| 实测 rho(abs(mean), std) | 0.7576 |
| 临界 std：氧化 tau_b 跌破 0.8 / 0.5、overlap 跌破 1（eV） | 0.45 / 1.20 / 0.25 |
| 临界 std：还原 tau_b 跌破 0.8 / 0.5、overlap 跌破 1（eV） | 0.25 / 0.70 / 0.10 |
| 子集敏感性同向 / 实测点数 / 台阶数 | 是 / 10 / 5 |

> 相图给出的机制判读是：排序的存亡由位移的离散度决定，均值只负责把整条轴平移。
> 实测点上的 rho(abs(mean), tau_b) = -0.535 是共线性（rho(abs(mean), std) = +0.758）的假象，
> 不是一条独立的效应。

## 5. R3：先冻结判据，再到留出集上打分

| 预测集 | 轴 | n | k | sd(delta) (eV) | OLS 斜率 b | 带符号判 | 朴素判 | 实测 | 重叠 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| all_non_discovery | oxidation | 8 | 2 | 0.563 | +0.423 | 保留 | **改写** | **保留** | 1.00 |
| all_non_discovery | reduction | 8 | 2 | 2.104 | -0.221 | 保留 | **改写** | **改写** | 0.50 |
| stage16_holdout | oxidation | 6 | 1 | 0.660 | +0.435 | 保留 | **改写** | **保留** | 1.00 |
| stage16_holdout | reduction | 6 | 1 | 2.436 | -0.881 | **改写** | **改写** | **改写** | 0.00 |

阈值都在 10 个发现点上拟合、先冻结后打分：带符号斜率 b <= -0.3635 判「改写」（低 = 危险），朴素 sd(delta) >= 0.3104 eV 判「改写」（高 = 危险）；命中带符号 3/4、朴素 2/4。

> 带符号规则 3/4、朴素规则 2/4——4 个预测的样本量不足以宣称任何一条规则更优，
> 这是本周主动写进限制里的结论。

## 6. 文件清单

| 文件 | 内容 |
| --- | --- |
| `sigma_synthetic.json` | R2：33 x 41 的（均值, 离散度）网格，每格 2000 次重复的 tau_b / f_unresolved / overlap 相图，外加均值不变性、实测相关性、临界 std 边界与子集敏感性。 |
| `sigma_prospective_frozen.json` | R3：在任何留出结果出现之前先落盘并取 SHA256 的冻结判据（带符号 OLS 斜率与朴素 sd(delta) 两条规则、各自的阈值与 10 个发现点）。 |
| `sigma_prospective.json` / `sigma_prospective.md` | R3：4 个留出预测的命中率（带符号 3/4、朴素 2/4）与逐条观测结果。 |
| `outputs/week4/p1_anchor_comparison.json`（新增 `arm_alignment` / `tau_b_reference`） | R1 + R10：三条臂对齐到同一批 10 个分子后的 tau_b、配对 Delta tau_b 的 CI 与精确置换 p，以及两类 tau_b 的分列口径。 |

## 7. QC 与限制

- QC：三个新脚本都可 `--check` 复跑（相图 2000 次重复的产物重跑逐字节相同）；`sigma_prospective_frozen.json` 在打分之前落盘并取 SHA256（25288a6eedba…），打分文件回写同一摘要（25288a6eedba…）；R1 的精确置换把 2^10 = 1024 种赋值全部枚举；全量测试全绿；Gate 0 CLOSED，Gate 1 的唯一 blocker 是排序一致性级（within-series 锚点对 n_pairs = 0），绝对标定级的 31 行 est 记为 limitation。
- 边界：(1) R2 的相图是合成模型（delta_i = mean + std * z_i，z 在每个 replicate 内标准化），它证明的是「在这个模型里排序只由离散度决定」，不是「真实体系里只有离散度有影响」；(2) R1 的配对检验只有 n = 10，虽然精确置换把 2^10 种赋值全部枚举过，但 VC、MA 这 2 个分子从未进入 GFN2 Delta-SCF 臂，任何跨臂结论都只在这 10 个分子上成立；(3) R3 的留出集只有 4 个预测，带符号规则 3/4、朴素规则 2/4 都落在「4 次里错 1-2 次」的噪声带内，不构成「规则更优」的证据。

## 8. 本周产物

- `artifacts/F42_sigma_synthetic_phase_diagram.png`
- `artifacts/figure_manifest_week21.md`
- `sigma_prospective.json`
- `sigma_prospective.md`
- `sigma_prospective_frozen.json`
- `sigma_synthetic.json`
- `week21_report_full.md`

## 9. 缺失源

- 无（全部源路径均存在）
