# 电解液溶剂 redox 代理可审计性项目 —— 成果输出包

本目录**只放蒸馏产物**（结果表、图、报告、校验清单）。原始 ORCA / xTB 运行输出
（`.out`、`.gbw`、`.inp`、几何等）保留在仓库 `outputs/` 内，**不**进入本目录；
唯一例外是 `week3/orca_smoke/`：它保留了 4 个冒烟作业的原始 `.inp/.out/.xyz`，
用来证明 ORCA 6.1.1 在本机可运行（该例外已在 `docs/09` §2.6 说明）。

## 目录结构

    成果输出/
    ├── README.md              本文件
    ├── 数据结果汇总.md          项目级总汇总
    ├── week1/                Stage 0 定义冻结 / Gate 0
    ├── week2/                Stage 1 方法审计与外部锚点
    ├── week3/                Stage 2 broad cheap pool（P0）
    ├── week4/                Stage 3（P1）+ Stage 4（P2）+ T5 + T3 + T2
    ├── week5/                Stage 5（T4：Li+ 配位条件态 C1）
    ├── week6/                Stage 6（T6 构象系综 + T7 虚频 + T8 delta_m + T9 决策稳定性）
    ├── week7/                Stage 7（ML / Δ-learning）+ Stage 8（active-learning replay）
    ├── week8/                Stage 9（显式微溶剂化：[Li(M)2]+ 第一溶剂壳复核）
    ├── week9/                Stage 10（五级台阶合成与决策稳定性总判）
    ├── week10/               Stage 11（sigma 的代数解剖与分辨率判据）
    ├── week11/               Stage 12（介电自相似律与事前预警协议）
    ├── week12/               Stage 13（介电极限与 ORCA 能量账本）
    ├── week13/               Stage 14（畸变项归因与 EMC 离群点诊断）
    ├── week14/               Stage 15（双初猜协议、电子弥散度描述符与溶液锚点扫描）
    ├── week15/               Stage 16（全核心集双初猜目录与事前预警规则）
    ├── week16/               Stage 17（亚稳态污染上限与两个 SCF 解的电子结构身份）
    ├── week17/               Stage 18（全目录电子身份普查与零成本自诊断）
    ├── week18/               Stage 19（几何弛豫检验：第二个 SCF 解能不能扛住弛豫）
    ├── week19/               Stage 20（第六级台阶与第二解的跨方法存亡）
    ├── week20/               Stage 21（临界带的能量裁决 + 溶剂壳氧化还原 + 真回填）
    ├── week21/               Stage 22（批次 A：三臂对齐 + σ 相图 + 前瞻检验）
    ├── week22/               Stage 23（批次 B：热修正抽样 + 导体极限 + NEB 精修）
    ├── week23/               Stage 24（批次 C+D：R5 三次配位 + R8 靶向双腿 + R12 叙事）
    ├── week22_hardening/     W22-H（论文加固：统计证据 B1–B5 + 数据统一；扁平文件 + SHA256SUMS）
    ├── week24_corealign/     W24-C（核心文件对齐：ML/AL 蒸馏 + 决策量补全 + F51；扁平文件 + artifacts/ + verification.json）
    └── week25_gate1/         W25（Gate 1 排序层判据首次评估 + 家族分辨 + §24 Figure 5 描述符标签关联；data/docs/outputs/scripts + verification.json）

每个 week 目录包含：

    weekN/
    ├── <蒸馏产物：.csv / .json / .md>
    ├── artifacts/            图（F0–F55 中属于该周的部分）
    ├── weekN_report.md       本周小结（可独立阅读）
    ├── SHA256SUMS            `<sha256>  <相对路径>`，与仓库 outputs/week1 同格式
    └── verification.json     结构化校验记录

`verification.json` 字段：`week`、`topic`、`generated_utc`、`n_files`、`files`（相对路径 → sha256）、
`checks`（`[{name, ok, detail}]`）、`gate_status`、`source_commands`，另附
`excluded_binary_scratch` 与 `missing_sources`。

## 一周一张表
| week | 主题 | 关键结果 | Gate |
| --- | --- | --- | --- |
| week1 | Stage 0 定义冻结 | 6 个冻结产物；core 18 / broad 40 行 | Gate 0 **CLOSED** |
| week2 | Stage 1 方法审计与外部锚点 | 12 分子方法审计；溶液锚点 31 行仍为 est | Gate 1 **NOT CLOSED** |
| week3 | Stage 2 broad cheap pool（P0） | core 18/18、broad 40/40；合并池 58 | Gate 1 NOT CLOSED |
| week4 | Stage 3 + Stage 4 + T5 + T3 + T2 | 三臂 MAE 1.377 / 4.481 / 0.251 eV；三级台阶 tau_b：方法 0.673 / 环境 0.895 / 几何 0.939；T3 T2 作业 0 失败 | Gate 0 CLOSED |
| week5 | Stage 5（T4：Li+ 配位 C1） | Li+ 配位条件态（C0 -> C1）：[Li M]+ motif 枚举 + 三态垂直量；方法 / 几何 / 环境 / 条件态四台阶同口径 σ 对比 | Gate 0 CLOSED |
| week7 | Stage 7（ML / Δ-learning）+ Stage 8（AL replay） | 特征表 cost 分级 `X0`/`X1`/`X2`（core 18 / broad 40）；三种拆分下的 direct vs Δ-learning；`n_T → τ_b` 四条 acquisition 曲线 | Gate 0 CLOSED |
| week6 | Stage 6（T6/T7/T8/T9） | 构象系综 `sigma_conf`（12 分子 / 32 构象）；`delta_m`（氧化 0.700 / 还原 2.074 eV）；并入 `delta_m` 后还原轴不可判定 | Gate 0 CLOSED |
| week8 | Stage 9（显式微溶剂化 C2） | [Li(M)2]+ 第一溶剂壳（12 motif / 8 家族）；C1 -> C2 的垂直量位移与同口径排序稳定性 | Gate 0 CLOSED |
| week9 | Stage 10（五级台阶合成） | 五个台阶同口径重算（common-10）：rho(std, tau_b) = -0.851 vs rho(|mean|, tau_b) = -0.535；唯一负 tau_b 在 C0->C1 还原轴 | Gate 0 CLOSED |
| week10 | Stage 11（sigma 解剖） | 四条恒等式（T1–T4）+ 精确分解（T5）；判据 `f_unresolved(z) = Pr(q_ij > sqrt(2)/z)` 与实测误差精确为 0；带符号斜率 AUC 1.000（精确 p = 1/120），无符号的 sd(delta) 仅 0.810；N=10 时 tau_b 抽样标准差 0.126 | Gate 0 CLOSED |
| week12 | Stage 13（介电极限 + ORCA 能量账本） | 6 个介电点实测 Born 形式（mean R2 0.9936）；eps = 200 距导体极限 < 50 meV；环境位移四项精确分解（CDS / D4 / gCP 对垂直量为 0） | Gate 0 CLOSED |
| week11 | Stage 12（介电自相似 + 事前预警） | 介电扫描落在 Born 单参数族（mean R2 0.9936 vs Onsager 0.8835）；18 个台阶事件里 8 个介电台阶全部良性（b > 0、tau_b >= 0.867、无一改写清单）；预警协议 k = 5 平均抓 96%（AUC 0.946）、k = 8 一次不漏 | Gate 0 CLOSED |
| week14 | Stage 15（双初猜协议 + 弥散度描述符 + 锚点扫描） | 90 点双初猜里 12 点超 1 meV 且**全部为负**、反向 0 次（最大惩罚 0.2860 eV）；EMC 还原轴九点 Born R2 0.6788 -> 0.9556、符号变化 4 -> 0、偶极粗糙度 1.99 -> 0.08；eps = 200 -> 1000 只走 11.3 meV 而六点缺口 +33.2 -> -30.8 meV（**没有变小**）；`D_anion` 最佳留一 R2 0.162 -> 0.556（`spin_maxfrac`，rho = +0.811），中性/阳离子 `delta_loo = 0`；31 行锚点 4 行可裁定、3 改 1 确认 | Gate 0 CLOSED |
| week13 | Stage 14（畸变项归因 + EMC 离群点） | 逐态畸变惩罚 D_neutral / D_cation / D_anion = 0.0685 / 0.1120 / 0.3710 eV（全部 72/72 为正，变分检验无例外）；唯一稳健关系是 D_neutral 对自身偶极矩（rho = +0.909，留一 R2 0.634）；§14 的 (-0.0465, +0.3272) eV 被 510 种聚合穷举证否；63 个密集网格作业零失败、四个共享介电点逐位复现 | Gate 0 CLOSED |
| week15 | Stage 16（全核心集双初猜目录 + 事前预警规则） | 360 个配对单元格里 32 个 MORead 更低、0 个更高；最大赤字 -0.2860 eV；10 点阶梯下 5/12 个分子被判定存在漏解 | Gate 0 CLOSED |
| week16 | Stage 17（亚稳态污染上限 + 两个 SCF 解的电子结构身份） | 54 格单腿替换：6 个格子 |delta| > 1 meV（最坏 0.1562 eV）；两臂 tau_b 的 95% CI 两轴均重叠、published 结论 0 条被改写；32 个漏解格里两个 SCF 解都是自旋纯双重态（<S^2> 32/32 落 0.75±0.01） | Gate 0 CLOSED |
| week17 | Stage 18（全目录电子身份普查 + 零成本自诊断） | 414 对身份普查：可测子集 AUC 1.000、混淆 TP 37 / FN 0 / FP 0 / TN 239；ester / nitrile / sulfone / sulfoxide 四个家族零漏解；零成本自诊断的冻结规则在留出臂 0.7963 输给多数类 0.9074（TP 0）；单边结论：small-gap 警告在 37/37 个正例上都出现（反例 0），但 237/377 个负例也出现 | Gate 0 CLOSED |
| week18 | Stage 19（几何弛豫检验） | 37 个 moread_lower 格各做两臂 Opt（74 个作业、74 ok / 0 failed）：仍保持 moread 更低 5/37（distinct_lower 5 + same_lower 0）；两解在终点合并 8 格；偏好被反转 32 格；|delta| 中位 0.11983 -> 0.00196 eV | Gate 0 CLOSED |
| week19 | Stage 20（第六级台阶 + 第二解的跨方法存亡） | 零新增计算把弛豫放回台阶（逐分子跨 eps 极差中位 0.0263 eV）；74 个 GFN2-xTB 作业：同一几何上方法一致率 33/37（89%）、xTB 弛豫把两臂能量差压掉约 34 倍、6/37 格两臂合并；跨判据裁决一致率 17/37 | Gate 0 CLOSED |
| week20 | Stage 21（临界带能量裁决 + 判据预检 + 溶剂壳氧化还原 + 真回填） | Part A：3 格 x 21 帧 = 63 个冻结单点，EC/cation/eps=5 弦上鼓包只有 0.00424 eV（k_B T 的 16.5%），Stage 19 的 `distinct_lower` 属过度判定，2/3 格与 RMSP 裁决一致；Part B：阈值重导 0.038946、borderline 3 格、闭壳层反例 0 格越阈；Part C：24 个 Opt 全部结构 QC 通过，氧化轴弛豫修正 -0.4053 eV、rho=0.797；Part D：严格 P2 腿 7/54 可回填，氧化轴排序被改写（Top-10% 重叠 0.000）、还原轴未被改写 | Gate 0 CLOSED |
| week21 | Stage 22（批次 A：三臂对齐 + σ 相图 + 前瞻检验） | 三条臂对齐到同一批 10 个分子之后，GFN2 Delta-SCF 的 tau_b 仍是三者最高（0.9111111111111111 vs P1 0.7777777777777778、P0 0.6888888888888889），但配对 Delta tau_b = 0.1333333333333333 的 95% CI 是 [-0.20000000000000007, 0.55]、精确置换 p = 0.8048780487804879，三对检验全部跨 0；σ 相图把 Week 9 的 rho(std, tau_b) = -0.851 换成一条机制判读（合成 rho = -1.0、均值平移严格不动排序，max abs Delta tau_b = 0.0）；前瞻检验里带符号规则 3/4、朴素规则 2/4。 | Gate 0 CLOSED |
| week22 | Stage 23（批次 B：热修正 + 导体极限 + NEB 精修） | R9 的热修正分子间离散度只有同轴 delta_m 的 8.3% / 3.7%（整项略去不改排序）；R4b 把「介电层免费」量化成 `abs(dE) x eps = 2057-2178 meV` 的幂律（eps = 200 的残余最大 19.62 meV，是氧化轴 delta_m 的 2.80%）；R11 用真 NEB 读到 EC/cation/eps=5 的峰高只有 0.000141 eV（直线界 0.00424 eV 的 1/30.0），Stage 19 的 0.02 A RMSD 阈值在该格**过度判定**，与 RMSD 判决冲突 1 格 | Gate 0 CLOSED |
| week23 | Stage 24（批次 C+D：R5 三次配位 + R8 靶向双腿 + R12 叙事） | R8 把漏解框成 A_axis = 0.1523 / 0.2860 eV（冻结 delta_m 的 21.7% / 13.8%），靶向规则抓住全部 19 / 21 次真实翻转、漏 0，且与全双腿逐层等价（对照单腿 tau_b 降到 0.9394 / 0.8788）；R5 的第三个配位点在 xTB 层级上没有换号（增量同号且绝对值递减，判定「与饱和一致」）；R12 给出「哪些层可以不算」的定性回答 | Gate 0 CLOSED |
| week22_hardening | W22-H（论文加固：统计证据 B1–B5 + 漏解容许量 + broad 池预算） | broad 池 40 分子只升级「值得升」子集（主判据 Top-10% 并集 21/40，省 47.5%）；P0 闭式判据不可分辨比例氧化 37.4% → 19.5%、还原 17.3% → 76.0%（z = 1）；漏解容许量 A_axis = 0.1523 eV（氧化 TMP@ε=5.0）/ 0.2860 eV（还原 EMC@ε=1000.0），2·A_axis 严格界保护 120/120；ρ(std,τ_b) = -0.851 [-0.987, -0.424]，Δτ_b = 0.184 [-0.177, 0.607]（P(Δ>0) = 0.839）；多重比较 9 个预警子 Bonferroni / Holm 均 0 条显著 | Gate 0 CLOSED；Gate 1 **NOT CLOSED** |
| week24_corealign | W24-C（核心文件对齐：ML/AL 蒸馏 + 决策量补全 + F51 流程图） | ML 蒸馏：LOFO 8 分组中 7 个 Δτ_b > 0（3 个配对区间不含 0、中位 +0.463），24 个组合中 19 个不可区分；AL 预算：τ_b ≥ 0.80 需 n_T = 8–9（10 分子池）/ 12–15（18 分子池）；决策量补全：40 个 f_robust_inv 全为 0 = True，p_ij 与闭式 f_unresolved(z = 1.2816) 逐点相等（偏差 0.0） | Gate 0 CLOSED；Gate 1 **NOT CLOSED**（W24-D 审计判决 NOT_CLOSABLE） |
| week25_gate1 | W25（Gate 1 排序层判据首次评估 + 家族分辨统计 + §24 Figure 5 描述符标签关联） | Gate 1 排序层：Ue1994 / Okoshi2015 氧化系列 7 个核心集分子 / 21 对首次可评，Kendall τ_b = 0.4286 < 0.90 → ok = False（reason = ordering_disagrees，一致 15 / 不一致 6）；还原旁证（DOE 2016，3 分子 / 3 对 < 18）判 not_evaluable_secondary_only；家族分辨：160 个组合中 16 个可估计（native-18 全部、common-10 为 0）；跨家族 τ_b(氧化 vs 还原) = 0.2857，95% CI [-0.455, 0.917] | Gate 1 **NOT CLOSED**（排序层已评估，ordering_disagrees） |

## 如何复现
```powershell
cd "E:\Claude Code\电解液溶剂-HB\电解液溶剂HB-Code"
$env:PYTHONIOENCODING = "utf-8"
.venv\Scripts\python.exe scripts\build_deliverables.py --dry-run
.venv\Scripts\python.exe scripts\build_deliverables.py
```

- `--out`：输出根目录（默认 `E:\Claude Code\电解液溶剂-HB\成果输出`）。
- `--weeks`：默认 `1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23`。
- `--force`：覆盖已存在的**复制**文件（默认跳过已存在项）。
- `--dry-run`：只打印计划，不写任何文件。

## 口径说明
- **幂等**：重复运行不产生差异。唯一例外是 `verification.json` 的 `generated_utc`（生成时刻），
  该字段允许变化，且不参与任何校验。
- 生成文件（`weekN_report.md`、`SHA256SUMS`、`verification.json`、本文件、`数据结果汇总.md`）
  每次都重写；复制文件默认跳过，需 `--force` 才覆盖。
- `SHA256SUMS` 与 `verification.json` **互相排除**（避免自指），但 `verification.json` 的 `files`
  与 `SHA256SUMS` 的条目集合完全一致。
- 二进制 scratch（`.gbw` / `.bas` / `.tmp` / `.wfn` / `.densities` / `.pot` / `.xtbrestart` /
  `.xtbtopo.mol` / `.xtboptok`，以及 `wbo` / `charges`）一律**不复制**；被跳过的数量记录在
  `verification.json` 的 `excluded_binary_scratch`。
- 所有文本文件为 UTF-8（无 BOM）、LF 换行。
- 复制文本产物时会规范化为 UTF-8（无 BOM）+ LF；若源文件原先带 BOM 或 CRLF，交付副本的 sha256
  会与仓库内源文件不同，这是有意为之（以本目录 `SHA256SUMS` 为准）。

## 扩展交付包

`week22_hardening`、`week24_corealign`、`week25_gate1` 三个包不经过本脚本的逐周复制流程，
由各自的构建脚本生成，因此不在上面的 `weekN/` 树内（其产物仍逐文件写入对应目录的 `SHA256SUMS`）：

- `week22_hardening/`（W22-H 论文加固周，扁平文件 + `SHA256SUMS`）：构建方式 UNVERIFIED ——
  仓库内未找到生成该镜像的构建脚本；`scripts/` 下仅有产出 `outputs/week22_hardening/*` 的分析脚本
  `analyze_w22_stats.py` / `analyze_w22_allowance.py` / `analyze_w22_broadpool.py`。
- `week24_corealign/`（W24-C 核心文件对齐周，扁平文件 + `artifacts/` + `verification.json`）：
  由 `scripts/build_week24_deliverables.py` 生成。
  复现：`python scripts/build_week24_deliverables.py`；校验：`python scripts/build_week24_deliverables.py --check`。
- `week25_gate1/`（W25 Gate 1 首评周，`data/ docs/ outputs/ scripts/` + `verification.json`）：
  由 `scripts/build_week25_deliverables.py` 生成。
  复现：`python scripts/build_week25_deliverables.py`；校验：`python scripts/build_week25_deliverables.py --check`。

图表索引（F0–F55）中：`F47` 属 `week22_hardening`，`F48`–`F51` 属 `week24_corealign`，
`F52`–`F55` 属 `week25_gate1`，逐图内容与来源见 `数据结果汇总.md` 的「图表索引」表。

