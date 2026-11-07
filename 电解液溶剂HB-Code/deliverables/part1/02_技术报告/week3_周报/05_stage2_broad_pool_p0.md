# Week 3 / Stage 2 -- broad pool 廉价层 P0 + 化学空间覆盖

- 生成脚本: scripts/run_broad_pool_p0.py (一条命令产出本篇所属的全部产物)
- 引擎: GFN2-xTB 6.7.1pre (.toolchain/xtb/xtb-6.7.1/bin/xtb.exe)
- 产物目录: outputs/week3/
- 原始记录: outputs/_week3_scratch/<mol_id>/<name>_xtb.json (可用 --force 重算)

---

## 1. 目的

Stage 2 的目标是把"最廉价的标量 proxy (P0)"铺到整个 broad pool (40 分子), 并对
core set (18 分子) 做同样处理, 用于:

1. **化学空间覆盖检查** -- broad pool 相对 core set 到底扩展了哪些轴, 哪些轴仍稀疏;
2. **决策稳定性预演** -- 在还没有 r2SCAN-3c 对照的情况下, 先量化 P0 内部 (objective、
   pool、reference ligand、proxy 选择) 对 top-k 筛选决策的影响。

P0 的定义被 config/scientific_definitions.yaml 冻结为"只能是轨道能标量":

    P0_ox(M)  = -eps_HOMO(M)     氧化侧, objective_direction = maximize
    P0_red(M) = +eps_LUMO(M)     还原侧, objective_direction = maximize

偶极 mu、极化率 alpha、ESP、分子体积、fingerprint 属于 explicitly_excluded_from_P0,
在本工作中**只作为 auxiliary 列**记录, 绝不参与 P0 排序。

---

## 2. 方法 (冻结参数)

每个分子的流程与 scripts/run_xtb_job.py 完全一致 (直接复用其 write_xyz / build_geometry):

    SMILES --RDKit ETKDG embed(seed=0xC0FFEE) + MMFF 预优化--> .xyz
           --GFN2-xTB --opt--> 解析 -eps_HOMO / +eps_LUMO / gap / dipole / alpha
           --> outputs/_week3_scratch/<mol_id>/<name>_xtb.json (+ <name>_opt.out)

| 项 | 取值 |
|---|---|
| 引擎 / 版本 | xtb 6.7.1pre (GFN2-xTB) |
| 参数 | --opt --gfn 2 --chrg 0 --uhf 0 (中性单重态, 单一构象) |
| 几何来源 | RDKit 2D->3D ETKDG (seed 0xC0FFEE) + MMFF 预优化, 再做 GFN2 优化 |
| 线程 | 子进程强制 OMP/MKL 单线程 (来自 electrolyte_ranking.xtb) |
| 相位 | gas-phase (无溶剂模型) |
| P0 单位 | eV (p0_ox_ev / p0_red_ev) |
| auxiliary | hl_gap_ev, dipole_debye, aux_alpha_bohr3 |

**断点续跑**: 若 scratch 下已有 <name>_xtb.json 且未给 --force, 直接复用, 40 分子跑一晚
不会白跑。失败分子 (嵌入失败 / xTB 执行错误 / 缺 P0 字段) 一律保留并逐条记录, 不静默丢弃。

---

## 3. 结果摘录

本轮 **58 个分子全部收敛, 0 失败** (core 18/18, broad 40/40)。

### 3.1 描述符统计 (真实计算结果)

| 量 | broad pool min / median / max | core set min / median / max |
|---|---|---|
| p0_ox_ev | 10.176 / 11.439 / 13.857 | 10.424 / 11.745 / 12.996 |
| p0_red_ev | -6.825 / -5.394 / +0.898 | -6.877 / -5.774 / +0.718 |
| hl_gap_ev | 4.337 / 6.305 / 11.951 | 5.003 / 6.248 / 11.567 |
| dipole_debye | 0.000 / 3.624 / 6.595 | 0.579 / 3.393 / 6.010 |
| aux_alpha_bohr3 | 41.133 / 66.071 / 189.551 | 29.435 / 53.488 / 146.985 |

### 3.2 极端端点 (broad pool, 仅 P0)

- 氧化侧最难氧化 (P0_ox 最大): B17 HFE347 = 13.857, B18 HFE7100 = 13.538,
  B32 TFP = 13.271, B05 TFMEC = 13.146, B19 BTFE = 12.929 -- 均为**氟化**分子, 与
  "氟化提高氧化稳定性"的先验一致。
- 氧化侧最易氧化 (P0_ox 最小): B40 OMTS = 10.176, B23 DESO = 10.244, B24 THTO = 10.297
  -- 硅氧烷与亚砜 (弱给体 / 易氧化硫中心)。
- 还原侧最易还原 (P0_red 最大): B09 DEE = +0.898, B15 DMM = +0.826, B12 THF = +0.518 --
  简单醚的 LUMO 甚至高于真空, 说明其 **Koopmans 还原在气相极难发生** (对应 P1 中预期
  unbound_anion; 本轮 P0 只算中性分子, 不产生 unbound_anion 标志)。
- 还原侧最难还原 (P0_red 最小): B05 TFMEC = -6.825, B08 ClEC = -6.770, B29 MN = -6.769。

### 3.3 与 Week-2 method audit 的一致性交叉检查

core set 中与 Week-2 method audit 重叠的 12 个分子, 其本轮的 p0_ox 与 week2 的
ip_koopmans_ev (= -eps_HOMO) 对比: **最大绝对偏差 = 0.0063 eV** (仅 EA 一个分子为 0.0063,
其余 11 个为 0.0000)。说明 P0 管线可复现 (微小差异来自 GFN2 优化落点/SCF 末位的构象微差),
详见 outputs/week3/p0_summary.json 的 cross_check_vs_week2。

完整逐分子数值见 outputs/week3/p0_broad_pool.csv 与 outputs/week3/p0_core_set.csv。

---

## 4. 化学空间覆盖结论

详见 outputs/week3/coverage_report.md (含 3 张英文标签图):

- fig1_family_counts.png -- family 计数对比
- fig2_mw_donor.png -- MW vs donor_count 散点 (按 family 着色, 形状分 core/broad)
- fig3_p0_ox_fluorinated.png -- 氟化 / 非氟化 的 p0_ox 分布

**要点**:

- **被扩展的轴**: (a) family -- broad 新增 siloxane / sulfite / sultone 三个 core 完全没有的
  骨架 (core 8 个 family, broad 11 个); (b) 分子量上限 222 -> 344 g/mol; (c) 氟化 -- core 仅
  1/18 氟化, broad 6/40, 把氟化从单一 FEC 扩展到氟代碳酸酯、氟代醚、氟代磷酸酯;
  (d) 卤素对照新增 ClEC (非氟卤素); (e) 高柔档 (rotatable_bonds 5+) 密度 core 1 -> broad 6。
- **仍稀疏 / 未覆盖的轴**: 芳香族仅 1 个 (DPC); 非氟卤素仅 1 个; siloxane/sulfite/sultone
  各 1-2 个, 属"探点"而非系统序列; 没有系统同族取代扫描; 阴离子/盐/Li 配合物完全未覆盖
  (符合 P0 只针对中性 free molecule 的设计)。
- **给体齿数**: 上限其实在 core (donor_count=5, TEGDME), broad 最高为 4 -- 该轴上 core 反而更宽。

---

## 5. 决策稳定性预演结论

详见 outputs/week3/decision_stability_preview.md。**这只是 P0 内部预演, 还没有 r2SCAN-3c 对照。**

| 比较 | n | k(10%) | k(20%) | k(30%) |
|---|---|---|---|---|
| core: top-k(P0_ox) vs top-k(P0_red) overlap | 18 | 0.000 | 0.000 | 0.000 |
| broad: 同上 | 40 | 0.000 | 0.000 | 0.167 |
| combined: 同上 | 58 | 0.000 | 0.000 | 0.176 |
| combined: Kendall tau(P0_ox, P0_red) | 58 | -0.302 | | |
| pool 扩展: core-only 领袖在新池中存活比例 | 18->58 | 0.500 (1/2) | 0.750 (3/4) | 1.000 (5/5) |

关键结论 (均可回溯到上面的数字):

1. **objective 敏感**: P0_ox 与 P0_red 在合并集合上 Kendall tau = -0.302, 且在 k=10%/20%
   下 top-k 完全不相交 (overlap = 0)。即"抗氧化"与"抗还原"是两套几乎相反的分子集合,
   把两个方向当成一个排序是错的。这是本项目"必须分 objective_direction 报告"的直接证据。
2. **pool 扩展敏感**: 在 k=10% 时 core-only 的两个领袖只有 1 个 (C06 FEC) 能留在 core+broad
   的 top-6 里, 另一半位置被新的氟化 broad 分子 (B05 B17 B18 B19 B32) 占据; k=30% 时
   core 领袖 5/5 全部保留。说明小 k 下的筛选集合对"是否把 broad pool 纳入"很敏感。
3. **reference ligand**: 以参照分子的 P0 为门槛时, "优于 DME" 有 44 个候选, "优于 AN" 只有
   25 个 (Jaccard = 0.568)。但把 P0_ox 整体平移 (换成以 R 为参照的相对量) 后 Kendall tau = 1.000
   -- **P0 的排序本身对 R 完全不敏感**, 因为 P0 定义里根本不含 R。因此真正的 R-dependence
   只能在 P1/P2 (Li-complex exchange 反应) 阶段评估。
4. **proxy 敏感**: 用分子量 / TPSA / alpha / 偶极 的 top-k 去复现 P0_ox 的 top-k, Jaccard 均
   接近 0 (最高约 0.26)。即 P0 的筛选结果**不能**被这些平凡廉价描述符替代 (它们本来也被
   explicitly_excluded_from_P0)。

---

## 6. 极化率 (alpha) 说明

先执行 xtb.exe --help, 确认 **6.7.1 支持 --alpha** ("--alpha  requests the extension of
electrical properties to static molecular dipole polarizabilities")。因此:

- 对每轮前 5 个分子 (共 10 个, core 5 + broad 5) 额外跑了基于 GFN2 优化几何的单点 --alpha 作业,
  原始输出与 JSON 存于 outputs/_week3_scratch/<mol_id>/alpha/;
- 记入 CSV 的 aux_alpha_bohr3 为 **auxiliary**, 单位 a.u. = Bohr^3, 不参与任何 P0 排序;
- 附带发现: 该版本默认的 --opt 输出本身也打印 "Mol. alpha(0)", 因此主 CSV 的 aux_alpha_bohr3
  对全部 40+18 个分子都有值; 额外 --alpha 作业与主运行数值一致 (例如 MPC 74.715048 vs 74.715051),
  起交叉确认作用。

---

## 7. 局限

- P0 只是**代理量**: -eps_HOMO / +eps_LUMO 的 Koopmans 近似的轨道能, **不是真实氧化/还原电位**,
  不得解释为 redox 窗口。
- 无溶剂模型、无显式 Li+ / [LiM]+ 配合物; 只针对 gas-phase 中性 free molecule。
- 单一构象 (RDKit+MMFF 起点的 GFN2 局部优化), 未做构象系综采样, 未评估构象不确定度。
- 无 r2SCAN-3c (ORCA 未安装) 的 validated target 对照, 因此本预演不能回答"P0 是否保留目标排序"。
- top-k 只比较集合成员, 未使用 prereg 的 delta_m / sigma_ij (需要 P1/P2 的不确定度才能定义)。
- 氟化分子的 p0_ox 普遍偏高 (图 3), 与"氟化提升氧化稳定"一致, 但仍需 P1/P2 验证其是否在真实
  redox 排序上成立。

---

## 8. 下一步

1. 待 ORCA (r2SCAN-3c) 可用后, 对 core set 生成 P1 (gas-phase Delta-SCF redox) 与 P2
   (continuum) 的 validated target, 计算 P0->target 的 rank change 与 f_robust_inv。
2. 在 Stage 1/Gate 1 冻结具体 delta_m (来自 anchor 离散度或 method audit 离散度)。
3. 对全 40 分子做构象系综 (CREST) 以量化构象引起的 P0 不确定度。
4. 用 broad pool 作为 active-learning 候选池, 以 ranking-aware acquisition 复现筛选 loop。

---

## 9. 复现命令

    # 设好工具链 (PowerShell 点源或直接设环境变量)
    $env:ELECTROLYTE_XTB = (Resolve-Path '.toolchain\xtb\xtb-6.7.1\bin\xtb.exe').Path

    # 先小规模验证流水线
    .venv\Scripts\python.exe scripts\run_broad_pool_p0.py --pool both --limit 5 --jobs 4

    # 全量 (core 18 + broad 40), 断点续跑; 需要重算加 --force
    .venv\Scripts\python.exe scripts\run_broad_pool_p0.py --pool both --jobs 4 --alpha-limit 5

    # 只跑 broad pool
    .venv\Scripts\python.exe scripts\run_broad_pool_p0.py --pool broad

    # 单元测试 (不调用真实 xTB, 仅一个端到端用例在存在二进制时运行)
    .venv\Scripts\python.exe -m pytest tests -q

---

## 10. 产物清单 (outputs/week3/)

| 文件 | 内容 |
|---|---|
| p0_broad_pool.csv | 40 分子 P0 (p0_ox_ev/p0_red_ev) + auxiliary 列 + qc/版本/几何来源 |
| p0_core_set.csv | 18 分子同上 |
| p0_broad_pool_summary.json | broad pool 方法/版本/命令行/成功失败计数/描述符 min-median-max |
| p0_core_set_summary.json | core set 同上 |
| p0_summary.json | 两池合一 + alpha 记录 + 决策预演 + week2 交叉检查 |
| coverage_report.md | 化学空间覆盖检查 (表格 + 结论) |
| decision_stability_preview.md | 决策稳定性预演 (P0 内部) |
| fig1/fig2/fig3_*.png | 3 张英文标签图 |
