# Week 1–2 执行报告 (Stage 0 + Stage 1)

**日期:** 2026-09-29
**范围:** v2 第 19 节的 Stage 0–1 与 **Gate 0 / Gate 1**
**结论:** Gate 0 **已关闭**;Gate 1 **未关闭**(2 个明确 blocker,见 §4)。这是预期状态,不是失败。

---

## 1. 本轮定位

本课题侧重**物理/化学机制**,数据集刻意做小:
core set = **18** 个分子,匹配 v2「宁可缩小 core set,也不批量生成物理定义不一致的数据」的原则。
计算只保留两种:**GFN2-xTB**(几何/频率/廉价代理)与 **r2SCAN-3c**(单点电子能,ORCA)。

---

## 2. 交付物

### Stage 0 — 科学定义冻结
| 文件 | 内容 |
| --- | --- |
| config/scientific_definitions.yaml | P0/P1/P2 代理量层级、C0/C1/C2 条件态、R_gas/R_sol/R_env、目标量与筛选方向、标准态/温度/参考电极、reference ligand R、两类 continuum sensitivity |
| config/prereg.yaml | k=10/20/30%、delta_m 与 z、bootstrap 2000×20 seeds、决策阈值来源规则、append-only amendment 政策 |
| data/metadata/core_set.csv | 18 分子 × 14 列(含 donor/柔性/氟化多轴标签与入选理由) |
| data/metadata/broad_pool.csv | 40 分子廉价层池 |
| data/metadata/chemical_space_metadata.md | 多轴 chemical-space 标签体系与 core/broad 选择原则 |
| docs/00_stage0_definitions.md | Stage 0 汇总 + Gate 0 判据 |
| scripts/build_metadata.py | CSV 由脚本确定性重建;--check 校验,手改即失败 |

**核心集 family 覆盖(18):** linear_carbonate 3 / cyclic_carbonate 4 / ether 3 / ester 3 / sulfone 1 / sulfoxide 1 / nitrile 2 / phosphate 1。
**机理对照分子 3 个:** FEC(氟化 vs 非氟化)、VC(不饱和 vs 饱和)、SN(双齿 vs 单齿腈)。

### Stage 1 — 锚点、方法审计、工具链
| 文件 | 内容 |
| --- | --- |
| data/anchors/gas_phase_anchors.csv | 39 行 / 26 物种气相 IP、EA |
| data/anchors/solution_redox_anchors.csv | 31 行 / 16 物种溶液相氧化/还原电位 |
| data/anchors/README.md | curated vs estimated 的逐条声明 |
| docs/01_stage1_external_anchors.md | 三类锚点用途与 tolerance 来源 |
| docs/02_stage1_method_audit.md | 8–10 分子审计集、四类 arms、Gate 1 判据 |
| scripts/validate_anchors.py | schema/单位/范围/DOI 校验,含负向测试 |
| scripts/check_environment.py | 环境自检(缺二进制也返回 0;--require 才失败) |
| scripts/activate_toolchain.ps1 | 指向仓库内 .toolchain 的工具链 |
| src/electrolyte_ranking/toolchain.py | 二进制探测、版本捕获、DryRunBackend |
| src/electrolyte_ranking/xtb.py | 单线程确定性 GFN2 优化/单点/频率 + 输出解析 |
| src/electrolyte_ranking/orca.py | r2SCAN-3c 输入生成(Opt/Freq/SP、SMD/CPCM)+ 能量解析 |
| src/electrolyte_ranking/provenance.py | v2 §7.4 全字段溯源记录 |
| src/electrolyte_ranking/qc.py | v2 §20 QC 状态机(8 正常态 + 9 异常分支) |
| src/electrolyte_ranking/ranking.py | tau_b、unresolved fraction、robust inversion、Top-k、regret |
| src/electrolyte_ranking/uncertainty.py | bootstrap CI、sigma 估计、delta-learning 定义 |
| scripts/run_xtb_job.py | SMILES → 几何 → xTB → 解析 → provenance 的一体化运行器 |
| scripts/freeze_gates.py | 冻结产物摘要 + 生成两份 gate 记录 |
| tests/fixtures/ | **真实** xTB 6.7.1 输出,用于解析器回归 |

---

## 3. 验证结果(可复现)

| 检查 | 命令 | 结果 |
| --- | --- | --- |
| 单元测试 | pytest | **113 passed** |
| 元数据一致性 | build_metadata.py --check | OK(有/无 RDKit 两条路径一致) |
| 锚点校验 | validate_anchors.py | PASS,0 error / 0 warning |
| 环境自检 | check_environment.py | xtb FOUND(6.7.1pre);crest/orca MISSING |
| **真实 xTB 烟雾测试** | run_xtb_job.py | **通过**(见 §5) |
| **Stage 1 xTB 审计臂** | run_method_audit_xtb.py | **12 分子已跑**;MAE/τ_b 见 §5.1 |
| Gate 0 | freeze_gates.py | **CLOSED** |
| Gate 1 | freeze_gates.py | **NOT CLOSED**(2 blockers) |

---

## 4. Gate 1 的 blocker(诚实记录)

1. **溶液相 redox 锚点 31 行全部是 method=est**,没有可确证、条件统一的实验表。气相的 30 行来自 NIST WebBook 等,可回溯。
2. **ORCA 未安装**(需学术许可注册) → 无法产出任何 r2SCAN-3c 单点。

> xtb 已解决:采用官方 \`xtb-6.7.1pre-windows-x86_64.zip\`(SHA256 校验通过),置于 \`.toolchain/\`,
> 由 \`scripts/activate_toolchain.ps1\` 或 \`.env\` 的 \`ELECTROLYTE_XTB\` 指向。
> 因此 xTB 层的生产计算可以在 Week 3 立即开始;r2SCAN-3c 层仍等待 ORCA。

### 已标注需人工核对处
- 气相:VC 的 IP(NIST 收 10.08 与 11.91 eV,差 1.8 eV)、DME 的 IP(NIST 9.3 vs Fadel 2019 引 9.8 eV)。
- 气相:PC / DEC / EMC 三行与 6 个 unbound_anion 行**故意留空**,未强行填数。
- 溶液:全部 31 行;其中氧化电位(真实氧化是 solvent–anion 耦合)与 DMSO/AN 还原电位最不可靠。

---

## 5. 真实 xTB 烟雾测试(Week 2 的关键验证)

用 \`scripts/run_xtb_job.py\`(RDKit ETKDG+MMFF 建几何 → 冻结 GFN2 优化 → 解析)跑通碳酸乙烯酯(EC):

| 体系 | charge/mult | E (Eh) | HOMO (eV) | LUMO (eV) | gap (eV) | dipole (D) | QC |
| --- | --- | --- | --- | --- | --- | --- | --- |
| EC | 0 / 1 | -20.686419864444 | -12.4023 | -6.0834 | 6.3189 | 5.786 | — |
| EC 自由基阴离子 | -1 / 2 | -20.788967165745 | **+0.573** | 5.6763 | 5.1033 | 10.771 | **unbound_anion** |

第二行是有物理意义的结果:GFN2 气相下 EC 自由基阴离子的 HOMO 为正,即**电子未被束缚**,
被 v2 §7.3 的规则正确标记为 \`unbound_anion\` 而不是硬造一个绝热电子亲和能。

### 5.1 Stage 1 方法审计臂(已跑,12 分子)

用 `scripts/run_method_audit_xtb.py` 对 12 个有气相锚点的分子做 ΔSCF,并与 NIST 锚点比较(10 个有 IP 值):

| 变体 | n | MAE (eV) | 偏差 (eV) | 误差 std (eV) | Kendall τ_b |
| --- | --- | --- | --- | --- | --- |
| ΔSCF 垂直 IP(近似 $P_1$) | 10 | 4.451 | +4.451 | 0.343 | 0.911 |
| Koopmans −ε_HOMO($P_0$) | 10 | 1.320 | +1.202 | 0.668 | 0.689 |

**这是本轮最有分量的结果**:ΔSCF 的值误差是廉价代理的 3.4 倍,排序一致性却更好;
且其误差几乎是常数平移(std 0.34 eV vs 偏差 4.45 eV)—— 即 v2「值误差 ≠ 排序误差」与
「复杂度 ≠ 准确度」两个命题在真实数据上被证实,而不是被断言。完整结论与 caveat 见
`docs/04_stage1_xtb_audit_result.md`(含 n=10 的统计不确定性、EC 阴离子双重极小的诚实记录)。
### 顺带发现并修复的真实缺陷
首个解析器是照着**想象的**输出格式写的(假定 \`(HOMO) = <Eh> <eV>\`)。真实 6.7.1 是在轨道表的 eV 列打标记
(\`-12.3826 (HOMO)\`),导致 \`homo_ev/lumo_ev/hl_gap_ev\` 全为 \`None\` 却不报错。修复内容:
1. HOMO/LUMO/HL-Gap/Fermi 正则支持真实格式(并保留旧格式兼容);
2. 极化率行是 Unicode \`Mol. α(0) /au :\`,原正则只认 ASCII \`alpha\`;
3. 偶极 \`full:\` 行在四极矩块中也会出现(6 个数),改为行尾锚定的 4 数列,避免取到 -1.929;
4. 多步优化会打印多个轨道/能量块,改为**取最后一个**(优化后结构),否则会静默报告优化前的能量;
5. 支持 Fortran \`D\` 指数。
这 5 点已由 \`tests/test_xtb_real_output.py\` 对真实 fixture 固定。

---

## 6. 工程约定(轻量借鉴 电解质ML)

- **确定性**:xTB 子进程固定 \`OMP_NUM_THREADS=1\` 并清理 \`xtbrestart\` scratch,避免 OpenMP 归约次序漂移。
- **可审计**:每个数值可追溯到 mol_id / motif / 几何 / 方法 / 原始输出 / QC 状态。
- **预注册**:阈值与 k 值在看结果前冻结,\`amendment_log\` append-only。
- **verifier**:关键产物由脚本重建而非手改,并有回归测试;解析器对真实引擎输出回归。

---

## 7. 下一步(Week 3–4)

1. Stage 2:broad pool(40)廉价层 $P_0$,并做化学空间覆盖检查。
2. Stage 3:core set 自由分子 $P_0 \to P_1$ 的 xTB 部分;r2SCAN-3c 部分待 ORCA。
3. 补齐 CREST 构象搜索 driver(Stage 3 需要)。
4. 用气相锚点给 \`prereg.yaml\` 的 delta_m 填第一条可用的经验值。
5. 获取 ORCA(学术许可)后,用真实输出建立 ORCA 解析 fixture,再关闭 Gate 1。
