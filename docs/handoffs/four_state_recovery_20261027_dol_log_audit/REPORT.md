# DOL 生产腿（job 3782517）ORCA 日志形式 QC 判读 —— 独立复核报告

- 复核性质：**只读核验者**独立读数；先完整测出本报告的全部数字，**再**与 Lead 读数比对（未被 Lead 读数锚定）。
- 复核范围：仅下述文件的形式 QC（A–I 九项）。不评估化学结论、不评估 dedup 口径、不调超算、不跑全量 pytest、不 git。
- 本报告是本次核验**唯一**的写入产物；未创建任何脚本/测试文件。

## 0. 路径更正（重要）

任务给出的相对路径 `work/dol_ec_recovery_v1/...` **不以会话工作目录为根**。实际解析根为工作目录下的 `电解液溶剂HB-Code/`（项目检出目录）。全部输入实际位于：

```
E:\Claude Code\电解液溶剂-HB\电解液溶剂HB-Code\work\dol_ec_recovery_v1\tasks\DOL\LiM_2plus__p4_02_ring_pucker_twist\
```

以下行号均在 `snapshots/3782517_0/` 下该任务的文件内。

## 1. 所读文件与 sha256（数据源绑定）

`Get-FileHash <file> -Algorithm SHA256`

| 文件 | 字节 | 行数 | sha256 | 与 receipt 声明 |
|---|---|---|---|---|
| `snapshots/3782517_0/job.log` | 1,377,070 | 26,932 | `86cdba1d982c9897bea1b04d0aecf66df05d001ad47927dcd52f91a39bc884bd` | ✔ 一致 |
| `snapshots/3782517_0/job.xyz` | 953 | 14 | `4e0db8d3bbc73f4f88cc5e8dbba5f6f2b17a933d9768b29bd8d21a340f08938d` | ✔ 一致 |
| `snapshots/3782517_0/job.hess` | 63,410 | 761 | `0f0e072145984e3a963fe91dcff8b0065d54c72268fe258557d1386df85e3ccc` | ✔ 一致 |
| `snapshots/3782517_0/job.stderr` | 263,961 | 4,853 | `88aaacd68896532b51d0fd192986a3f119d8b41421ac7bc682d3ca7190cefe64` | ✔ 一致 |
| `geom.xyz`（任务目录） | 696 | 14 | `60436e57ebde4bd01101b17ea1d08775593f4221554c3fd42b0cff555838eb17` | ✔ 与 `inputs.sha256` 及 `manifest.json` 的 `geometry_sha256` 均一致 |
| `job.inp`（任务目录） | 158 | 5 | `72608d6b4b2f3be658906c2cf22787cdadcdff4b07f24f6ba2b58391078b48d0` | ✔ 与 `inputs.sha256` 一致 |

附加核对：`snapshots/3782517_0/geom.xyz` 与 `snapshots/3782517_0/job.inp` 分别与任务目录同名文件的哈希**逐位相同**（60436e…、72608d…），即已被计算过的输入与导入的输入同一份，无就地改写。

`job.inp` 原文：

```
! wB97X-D4 def2-TZVPD Opt AnFreq SMD(acetonitrile) VeryTightOpt TightSCF SlowConv
%maxcore 2000
%pal nprocs 4 end
%scf MaxIter 300 end
* xyzfile 2 2 geom.xyz
```

阈值来源说明：D 项所用五条冻结阈值（2e-7 / 8e-6 / 3e-5 / 1e-4 / 2e-4）**与日志内 ORCA 自己打印的 Tolerance 列逐位相同**，且与冻结输入里的 `VeryTightOpt` 关键字对应，构成可追溯的阈值出处。

`job.log` 是**单一连续作业**：`ORCA TERMINATED NORMALLY` 全文仅 1 次（见 A），无中途二次作业拼接。

---

## A. 正常终止

原始命令（PowerShell `Select-String`，等价于 `grep -n`）：

```powershell
Select-String -Path job.log -Pattern 'ORCA TERMINATED NORMALLY|TOTAL RUN TIME'
```

| 项 | 行号 | 实测 |
|---|---|---|
| `****ORCA TERMINATED NORMALLY****` | 26931 | 出现 **1 次** |
| `TOTAL RUN TIME` | 26932（全文最后一行） | `0 days 1 hours 4 minutes 5 seconds 825 msec` |

**判定：成立。** 交叉核对：`fetch_receipt.json` 的 accounting = `["3782517_0","COMPLETED","0:0","01:04:08","4"]` → 墙钟 1h04m08s，与 ORCA 内部计时 1h04m05.825s 相差 2.2s；`started.utc` 2026-10-26T18:04:05Z → `normal_termination.utc` 2026-10-26T19:08:12Z 差 64m07s。三者自洽。

## B. SCF 收敛

```powershell
Select-String -Path job.log -Pattern 'SCF CONVERGED AFTER'
```

**实测出现 35 次**（不是 4 次）。逐次（绝对行号 / 圈数）：

| # | 行 | cycles | # | 行 | cycles | # | 行 | cycles | # | 行 | cycles |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 862 | 26 | 10 | 7841 | 12 | 19 | 14107 | 12 | 28 | 20305 | 4 |
| 2 | 2237 | 16 | 11 | 8537 | 12 | 20 | 14801 | 10 | 29 | 20991 | 3 |
| 3 | 2943 | 16 | 12 | 9234 | 13 | 21 | 15492 | 8 | 30 | 21677 | 3 |
| 4 | 3646 | 18 | 13 | 9931 | 13 | 22 | 16180 | 5 | 31 | 22364 | 4 |
| 5 | 4346 | 16 | 14 | 10628 | 13 | 23 | 16868 | 5 | 32 | 23051 | 4 |
| 6 | 5045 | 15 | 15 | 11325 | 13 | 24 | 17555 | 4 | 33 | 23737 | 3 |
| 7 | 5747 | 17 | 16 | 12020 | 11 | 25 | 18243 | 5 | 34 | 24423 | 3 |
| 8 | 6447 | 15 | 17 | 12715 | 11 | 26 | 18929 | 3 | 35 | 25277 | 2 |
| 9 | 7145 | 14 | 18 | 13411 | 12 | 27 | 19618 | 6 | | | |

序列（按出现次序）：`26, 16, 16, 18, 16, 15, 17, 15, 14, 12, 12, 13, 13, 13, 13, 11, 11, 12, 12, 10, 8, 5, 5, 4, 5, 3, 6, 4, 3, 3, 4, 4, 3, 3, 2`

分段（以 `THE OPTIMIZATION HAS CONVERGED` 行 24707 与频率段起点 26313 为界）：
- 行区间 862–24423：**34 次**，对应 34 个几何步（与 `|Geometry convergence|` 横幅出现 34 次一致）；
- 行 25277：**1 次**（2 圈），是 `AnFreq` 最终单点/解析 Hessian 前的 SCF，位于 24707 与 26313 之间。

`SCF CONVERGED AFTER` 一次也没有以「未收敛」形式出现：`Select-String -Pattern 'NOT CONVERGED'` 在 `job.log` 与 `job.stderr` 中命中均为 **0**。

**判定：成立**（全部 SCF 均收敛；但出现次数是 **35**，与 Lead 的 4 次不符 —— 见 I）。

## C. 优化收敛标志

```powershell
Select-String -Path job.log -Pattern 'THE OPTIMIZATION HAS CONVERGED'
```

- 出现 **1 次**，行 **24707**：`***        THE OPTIMIZATION HAS CONVERGED     ***`（位于 `****HURRAY****` 横幅内，24706–24708）。
- 全文仅此一处；未出现第二个 HURRAY 或第二轮 Opt。

**判定：成立。**

## D. 最终 Geometry convergence 表（含独立阈值判定）

```powershell
Select-String -Path job.log -Pattern '\|Geometry convergence\|'          # 共 34 个横幅，最后一个在行 24687
```

**最后一个含 `Energy change` 的竖排五行表：起始横幅行 24687，表体行 24690–24694。** 原文逐行抄录（`Get-Content` 按绝对行号取）：

```
24687:           ----------------------|Geometry convergence|-------------------------
24688:           Item                value                   Tolerance       Converged
24689:           ---------------------------------------------------------------------
24690:           Energy change       0.0000000337            0.0000002000      YES
24691:           RMS gradient        0.0000015319            0.0000080000      YES
24692:           MAX gradient        0.0000057862            0.0000300000      YES
24693:           RMS step            0.0000684374            0.0001000000      YES
24694:           MAX step            0.0002478440            0.0002000000      NO
24695:           -------------------------------------------------------------------------
```

判定列由我独立计算（ratio = value / 冻结阈值；ratio ≤ 1 即 PASS），**不是**照抄 ORCA 的 YES/NO：

| 行 | Item | ORCA value | ORCA Tolerance | ORCA 自标 Converged | 冻结阈值 | 我的 ratio | 我的判定 |
|---|---|---|---|---|---|---|---|
| 24690 | Energy change | 3.37e-08 | 2e-07 | YES | TolE 2e-07 | 0.1685 | **PASS** |
| 24691 | RMS gradient | 1.5319e-06 | 8e-06 | YES | TolRMSG 8e-06 | 0.1915 | **PASS** |
| 24692 | MAX gradient | 5.7862e-06 | 3e-05 | YES | TolMaxG 3e-05 | 0.1929 | **PASS** |
| 24693 | RMS step | 6.84374e-05 | 1e-04 | YES | TolRMSD 1e-04 | 0.6844 | **PASS** |
| 24694 | MAX step | 2.478440e-04 | 2e-04 | **NO** | TolMaxD 2e-04 | **1.2392** | **FAIL** |

**判定：4/5 PASS，1/5 FAIL**（MAX step 超阈 **1.2392×**）。我的独立判定与 ORCA 自标的 YES/NO **五项全部一致**，即 ORCA 并未误标。

附带实测（不与上表混同）：34 个横幅共承载 **169 行**五行表条目（33 个横幅各 5 行 + 1 个横幅 4 行 = 169）；唯一缺 `Energy change` 行的是**第一个**横幅（行 1802，表体 1805–1808），因首个几何步无前序能量可比，属正常；最后一个表 5 行齐全。全部表的 `Energy change` 共 **33** 个值，范围 `-0.0576370919` … `3.9244e-06`。

> 记账（自查纠错）：我第一遍用 `[\d.]+` 作数值正则，**漏掉了带负号的 `Energy change` 行**（如行 2510 的 `-0.0576370919`），一度得到「145 行」的错误计数；改用 `-?[\d.]+` 后为 169。此坑**不影响 D 的结论** —— 末表的 5 个值在两版正则下均命中，且已逐行抄录复核。

末尾表下方的小量内坐标变化（行 24697–24698）另记为 `Max(Bonds) 0.0001 / Max(Angles) 0.01 / Max(Dihed) 0.01 / Max(Improp) 0.00`。

## E. close-enough 声明

同一收敛表之后（行 24699 空行起），原文**逐字**抄录（行 24701 行尾含 **1 个尾随空格**，本块保留）：

```
24701:        The gradient convergence is overachieved with 
24702:        reasonable convergence on the displacements
24703:        Convergence will therefore be signaled now
```

对应命令：

```powershell
Select-String -Path job.log -Pattern 'overachieved|signaled now|close enough|close-enough'
```

全文命中 2 行：24701、24703（另 `close enough`/`close-enough` 字面 **0** 次 —— ORCA 用的是 overachieved / signaled 措辞）。

**判定：成立。** 措辞逐字与任务描述的「The gradient convergence is overachieved … Convergence will therefore be signaled now」一致，出现在收敛表**之后**（24701 > 24694），据此 ORCA 才在 24707 宣布收敛 —— 即该 HURRAY 属 **close-enough 路径**，而非 5/5 严格过阈。此点与 D 的 MAX step FAIL 1.2392× 互为印证（梯度三行均 0.19 倍余量「overachieved」，步长 MAX 行超阈）。

## F. 虚频

```powershell
Select-String -Path job.log -Pattern 'VIBRATIONAL FREQUENCIES'
```

频率段头 **行 26313** `VIBRATIONAL FREQUENCIES`，数据行 **26318–26353**。抄录（全 36 行，idx 0–35）：

```
26316: Scaling factor for frequencies =  1.000000000  (already applied!)
26318:      0:       0.00 cm**-1        26327:      9:     231.73 cm**-1
26319:      1:       0.00 cm**-1        26328:     10:     295.05 cm**-1
26320:      2:       0.00 cm**-1        26329:     11:     636.78 cm**-1
26321:      3:       0.00 cm**-1        26330:     12:     679.93 cm**-1
26322:      4:       0.00 cm**-1        26331:     13:     777.18 cm**-1
26323:      5:       0.00 cm**-1        26332:     14:     811.69 cm**-1
26324:      6:      84.78 cm**-1        26333:     15:     906.89 cm**-1
26325:      7:     162.92 cm**-1        26334:     16:     917.65 cm**-1
26326:      8:     168.62 cm**-1        ...   (26335–26353 至)
26353:     35:    3222.11 cm**-1
```

独立计数（`python -c` 单行正则解析，未写任何文件）：

| 量 | 实测 |
|---|---|
| 条目总数 | **36**（idx 0..35） |
| **负频率条数（< 0）** | **0** |
| 恰好 0.00 的条数 | **6**（idx 0–5，即 3 平动 + 3 转动） |
| 最小的 3 个频率值（全体） | `0.00, 0.00, 0.00` |
| 最小的 3 个**非零**频率值 | `84.78, 162.92, 168.62` cm**-1 |
| 最大频率 | 3222.11 cm**-1 |

**计数口径（如实声明）**：3N = 3×12 = **36** 个模式条目；其中 6 个为刚体模式（平动/转动，ORCA 投影后打印为**恰好** 0.000000，非「0 附近小值」）；余下 **36 − 6 = 30** 个为真实振动模式。ORCA 自己在行 26630 明确写出：`The total number of vibrations considered is 30`，与 3N−6 = 30 一致。

**独立交叉校验（`job.hess`）**：`job.hess` 行 315–352 的 `$vibrational_frequencies` 块自称条数 `36`（行 316），数值与日志逐项吻合（`84.7779630928742165`、`162.9222958954703131`、`168.6170304549444836` … `3222.1108141228173736`），且前 6 项为 `0.0000000000000000`；`$hessian` 块（行 16 起）自称维度 `36`（行 17），即 36×36 Hessian。两条独立通道互证：**36 个模式、0 个负频**。

**判定：成立（本任务无虚频，属极小点而非鞍点）。**

两点口径更正（仅记账，不影响结论）：
1. 任务描述的负频行形如 `   1:       -12.345678`；本日志实际格式为 `     6:      84.78 cm**-1`（带 `cm**-1` 后缀、2 位小数），字面无 `-12.345678` 式样。我按实际格式解析，故「负频率条数」的判据是数值字段 < 0。
2. 任务描述中「总振动模式数是否 = 3N（N=12 原子 ⇒ 30 个振动模式……振动模式从第 7 行起数）」把 3N = 36 与 3N−6 = 30 写在了一处。实测：**总数 36（=3N）**，**振动模式 30（=3N−6，从第 7 行 idx 6 起）**；两种口径都已给出，无歧义。

## G. 热化学

```powershell
Select-String -Path job.log -Pattern 'Zero point energy|Final Gibbs free energy|Total Enthalpy|Total entropy correction'
```

得**完整**热化学段，起点行 26634 `THERMOCHEMISTRY AT 298.15K`（头信息行 26637–26641）：

| 项 | 行 | 实测值 |
|---|---|---|
| Temperature | 26637 | 298.15 K |
| Pressure | 26638 | 1.00 atm |
| Total Mass | 26639 | 81.02 AMU |
| Quasi RRHO | 26640 | True |
| Cut-Off Frequency | 26641 | 1.00 cm^-1 |
| Electronic energy | 26699 | -275.72217540 Eh |
| Zero point energy | 26700 | 0.09101732 Eh（57.11 kcal/mol） |
| Total thermal energy | 26705 | -275.62463573 Eh |
| Total enthalpy | 26790 | -275.62369152 Eh |
| Total entropy correction | 26791 | -0.03789072 Eh（-23.78 kcal/mol） |
| **Final Gibbs free energy** | **26793** | **-275.66158224 Eh** |
| G-E(el) | 26796 | 0.06059317 Eh（38.02 kcal/mol） |

**单位：Eh（Hartree）。**

原文 26793：`Final Gibbs free energy         ...   -275.66158224 Eh`

**判定：成立。** 热化学段完整（ZPE、内能/焓、熵、G、G-E(el) 齐备），且 `job.xyz` 首行注释的电子能 `E -275.722175404553` 与行 26699 的 `-275.72217540 Eh` 独立吻合。附带：`Total Mass 81.02 AMU` 与 C3H6O2Li 的 81.019 AMU（3×12.011 + 6×1.008 + 2×15.999 + 6.94）一致，是元素组成的第三条独立佐证。

> 提醒（防止误读）：`Select-String -Pattern 'Electronic energy'` 会在 `job.log` 命中文中 35 处形如 `Electronic Energy  :  -488.22… Eh` 的行（如行 883）；那是 `TOTAL SCF ENERGY` 段下的**分量**（电子能 = 总能量 − 核排斥），**不是总能量**。本腿总能量为 -275.61…/-275.72… Eh 量级。若按字面 grep 取值会得到错误结论（-488 与 -275 相差约 213 Eh）。

## H. 原子数一致性

`python -c`（只读解析，未写文件）逐元素计数：

| 文件 | 首行原子数 | 实际原子行数 | 元素组成 | 合计 | 多余行 |
|---|---|---|---|---|---|
| `geom.xyz`（任务目录，输入） | 12 | 12 | C:3, H:6, Li:1, O:2 | 12 | 0 |
| `snapshots/3782517_0/geom.xyz`（快照输入） | 12 | 12 | C:3, H:6, Li:1, O:2 | 12 | 0 |
| `snapshots/3782517_0/job.xyz`（ORCA 末几何） | 12 | 12 | C:3, H:6, Li:1, O:2 | 12 | 0 |

**判定：成立。** 三者首行原子数均为 **12**，逐元素计数**完全相同**（C3H6O2Li），且首行声明值与实际原子行数一致（无截断/多余行）。坐标数值不同属预期（输入几何 vs 优化后几何），`job.xyz` 首行注释 `Coordinates from ORCA-job job E -275.722175404553`；组成未变，即优化过程中无原子丢失/元素替换。

## I. 与 Lead 读数比对（测完后进行）

| # | Lead 读数 | 我的独立实测 | 结论 |
|---|---|---|---|
| 1 | Energy 3.37e-8 ✓ | 行 24690 = 3.37e-08，ratio 0.1685，PASS | **一致** |
| 2 | RMS grad 1.53e-6 ✓ | 行 24691 = 1.5319e-06，ratio 0.1915，PASS | **一致** |
| 3 | MAX grad 5.79e-6 ✓ | 行 24692 = 5.7862e-06，ratio 0.1929，PASS | **一致** |
| 4 | RMS step 6.84e-5 ✓ | 行 24693 = 6.84374e-05，ratio 0.6844，PASS | **一致** |
| 5 | MAX step 2.478e-4 ✗（超 1.24×） | 行 24694 = 2.478440e-04，Tol 2e-04，ratio **1.2392**，FAIL | **一致** |
| 6 | ⇒ 4/5 过 | 我独立判定 4 PASS / 1 FAIL | **一致** |
| 7 | SCF 标志共出现 4 次（26/16/16/18 cycles） | 实测 **35 次**；其前 4 次恰为 26/16/16/18 | **不一致**（次数）／数字本身一致 |
| 8 | ORCA 宣布收敛属 close-enough | 行 24701–24703 原文命中，且 ORCA 自标 MAX step = NO | **一致** |

第 7 项的差异归因（事实层面，非猜测性结论）：Lead 列的四个圈数 `26/16/16/18` **正好是全文前 4 次出现**、且出现在行 862–3646（即第 1–4 个几何步）。因此「4 次」应是被截断/限幅的 grep 结果（读到前 4 条即止），而非另有一份含 4 次收敛的日志 —— 同任务下**不存在**第二个含 SCF 段的日志：`snapshots/` 下只有 `3782517_0`，EC 腿目录（`tasks/EC/LiM_2plus__p4_02_ring_pucker_twist`）只有 `geom.xyz`/`job.inp`/`inputs.sha256`/`import_level.txt`，**无任何快照、无 job.log**，故不可能被误作来源。

正确读法：本腿 **35 次 SCF 全部收敛**（26, 16, 16, 18, 16, 15, 17, 15, 14, 12, 12, 13, 13, 13, 13, 11, 11, 12, 12, 10, 8, 5, 5, 4, 5, 3, 6, 4, 3, 3, 4, 4, 3, 3, 2 圈），最大 26 圈，`%scf MaxIter 300` 远未触及。

---

## J. 额外观察（超出 A–I，但属形式 QC 风险提示）

1. **形式收敛为 close-enough，非 5/5 严格过阈。** 唯一 FAIL 项 MAX step = 2.478440e-4 > TolMaxD 2.0e-4（1.2392×）。ORCA 依据 E 段声明按 close-enough 宣布收敛。故「本腿已收敛」这一陈述若被下游当作 **5 项全过**使用，则与日志不符；若下游规则本就接受 close-enough，则无需动作。**谁对谁错取决于冻结的验收规则，不在本报告裁量范围内**，此处只确证日志事实。
2. **单点性无虚频已确证**（F 项，0 个负频，且 `job.hess` 独立互证），故该结构在 wB97X-D4/def2-TZVPD + SMD(acetonitrile) 下是极小点而非鞍点。
3. `job.stderr`（4,853 行、263,961 B）经关键词扫描：`error` / `Error` / `ERROR` / `not converged` / `NOT CONVERGED` / `segmentation` / `abort` 命中**均为 0**；`Warning`/`WARNING` 命中 422 行，但全部为 OpenMPI PRTE 的同一条提示（`prte_silence_shared_fs`：scratch 目录位于共享文件系统），原文自称 `This is only a warning advisory and your job will continue.` → **非计算性告警**。
4. 作业身份与 `manifest.json` 自洽：`submission.job_id = 3782517`、`supersedes 3782423 (technical_failed)`、`batch 2`「DOL leg re-submission after the technical fix」，与 `fetch_receipt.json` 的 `job_id 3782517_0`、`COMPLETED` 一致；`members[0].geometry_sha256 = 60436e…` 与本腿 `geom.xyz` 实测哈希一致。

## K. 结论

**9 项检查（A–I）全部测出，无一项「无法测出」；8 项成立，1 项不符。**

- 不符项唯一：**I 第 7 条 —— Lead 称「SCF 标志共出现 4 次」，实测为 35 次**（前 4 次的圈数 26/16/16/18 与 Lead 所述相同，属限幅截断；本腿 SCF 无一未收敛）。
- 其余 8 项（含 Lead 的五个数值、4/5 结论、close-enough 判读）与我的独立读数**全部一致**。
- 需要下游注意的实质结论：最终几何收敛表**并非 5/5 过阈**，MAX step 超阈 1.2392×，ORCA 以 close-enough 方式宣布收敛；同时该结构**无虚频**、热化学段完整、输入/快照哈希与 receipt 全部吻合（数据链未被改写）。

**总结行：9 项检查 8 成立 1 不符（不符项：SCF 收敛标志出现次数，Lead 4 次 vs 实测 35 次）。**