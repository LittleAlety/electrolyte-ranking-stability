# ORCA / r2SCAN-3c 安装指南与 runner 说明（Week 2 → 3 桥梁）

**目的：** 把 ORCA 臂「就绪化」。ORCA **已在本机安装并跑通**（版本 **6.1.1**，Windows AVX2 **msmpi** 构建），
Gate 1 的这条 blocker（`orca binary not installed`）已经清掉；另一个 blocker 是溶液相锚点仍是 `method=est`。
这份文档记录两件事：

1. ORCA 怎么装到位（学术免费、但**不是开源软件**，必须自行注册下载）——本机实测步骤见 §10；
2. `orca.exe` 放到位之后，**一条命令**就能跑通 r2SCAN-3c 臂；本机已跑通，实测数据见 §15。

> 安装并跑通之后，`scripts/freeze_gates.py --stage 1` 的 `toolchain:orca` 一项转绿，
> 不再出现 `orca binary not installed; production runs cannot start`。
> Gate 1 目前只剩溶液相锚点（`solution_redox_anchors.csv` 的 31 行 `method=est`）这一个 blocker。

**相关文件**

- 驱动逻辑：`src/electrolyte_ranking/orca.py`（`run_orca`、`parse_orca_output`、`read_orca_version`）
- CLI：`scripts/run_orca_job.py`
- 环境探测：`scripts/check_environment.py`
- 测试：`tests/test_orca_run.py`（mock，可跑）、`tests/test_orca_input.py`（输入/解析）
- Gate：`scripts/freeze_gates.py`（`bundled_environment()` 会在 `.toolchain` 下自动寻找 `orca.exe`）

---

## 1. 为什么必须自己下载

ORCA 对**学术用户免费**，但：

- **不是开源软件**，不能从包管理器（conda / pip / winget）装；
- 需要到官方论坛 **https://orcaforum.kofo.mpg.de/** 注册账号并登录；
- 注册时**用单位/学校邮箱最稳**（个人邮箱可能被拒或被延迟审核）；
- 登录后走 **My Downloads → ORCA（6.x）→ Windows x86-64 zip**（约 **1–2 GB**）。

> 不要相信任何第三方镜像或「绿色版」ORCA。许可证决定它不能这样分发，而且来路不明的
> 可执行文件与「结果可溯源」这个项目目标直接冲突。

> 说明：我没法替你确认你账户里具体显示哪个版本号、压缩包叫什么文件名，
> **以你登录后看到的实际页面为准**。

---

## 2. 解压到哪、怎么让脚本找到它

查找顺序（`toolchain.find_executable("orca")`，也就是 `check_environment.py` 与
`run_orca_job.py` 共用的那一处）：

1. 环境变量 **`ELECTROLYTE_ORCA`**（优先级最高）；
2. 系统 `PATH`；
3. **仓库内的 `.toolchain/`**（零配置路径，递归查找 `orca.exe`）。

所以最省事的方式是把它放进 `.toolchain\orca\`，**不用配任何环境变量**：

```text
.toolchain\orca\orca_6_1_1\orca.exe      <-- 推荐
```

目录层级随便多深，递归查找会命中第一个 `orca.exe`。整个 `.toolchain` 的位置也可以用
`ELECTROLYTE_TOOLCHAIN_ROOT` 改到别处（例如放到空间更大的盘）。

**一条命令完成放置（推荐）**

```powershell
# 指向你解压出来的文件夹（默认建立目录 junction，不额外占空间）
.\scripts\setup_orca.ps1 -Source "E:\Downloads\orca_6_1_1_win64"

# 或者直接指向 zip（自动解压到 .toolchain\orca\）
.\scripts\setup_orca.ps1 -Zip "E:\Downloads\orca_6_1_1_win64.zip"

# 源目录在移动硬盘、随时会拔掉时改用复制
.\scripts\setup_orca.ps1 -Source "D:\orca" -Copy
```

脚本做四件事：定位 `orca.exe` -> 检查同级 `orca_*.exe` 辅助程序是否齐全 -> 把整个目录
链接/复制到 `.toolchain\orca\<名字>\` -> 自动重跑 `check_environment.py` 让你立刻看到结果。

**不要只拷 `orca.exe`**：它会调用同目录的 `orca_scf.exe`、`orca_gtoint.exe` 等辅助程序和
若干 `*.dll`，必须整个目录一起放。

手工路径也可以（当前会话）：

```powershell
$env:ELECTROLYTE_ORCA = "D:\path\to\orca\orca.exe"
```

需要长期生效就写进用户环境变量：

```powershell
[Environment]::SetEnvironmentVariable("ELECTROLYTE_ORCA", "D:\path\to\orca\orca.exe", "User")
```

---

**硬件与运行库**

- 官方 Windows x86-64 包是 **AVX2 构建**，需要 CPU 支持 **AVX2**：
  - 2013 年之后的主流 Intel / AMD 基本都支持；
  - 可用 **CPU-Z**（CPU 页 → Instructions 一栏应能看到 `AVX2`）确认；
    `Get-ComputerInfo` 能看到处理器型号，再对照厂商规格判断。
  - 如果 CPU 不支持 AVX2，ORCA 会在启动时报错退出（这种情况需要换 AVX/SSE 构建或换机器）。
- 若运行时弹出缺少 DLL、或与 openmp 相关的错误，通常是缺 **VC++ 运行库**：
  安装 **Microsoft Visual C++ Redistributable (x64)** 后重试。

---

## 3. 装好后自检（确切命令）

在仓库根目录执行：

```powershell
# 1) 环境探测：orca 应显示 FOUND，并带一个版本号（从 Program Version 横幅解析）
.venv\Scripts\python.exe scripts\check_environment.py
```

期望看到类似：

```
  orca   FOUND     ...\orca_6_1_1\orca.exe   version 6.1.1   [bundled]
```

> **版本探测（实测）：** `orca.exe --version` 会打印 `Program Version 6.1.1  -  RELEASE`，
> 但它的**退出码是 2**（不是 0），所以不能按退出码判断成功，必须解析 stdout 里的
> `Program Version X.Y.Z` 横幅。若横幅没读到会显示 `version unknown`，**不影响**运行；
> 真正的版本会记录在每次运行的 `.out` 里。详见 §11。

```powershell
# 2) 不运行 ORCA，只检查输入文件是否正确生成（现在就可用，装 ORCA 之前也能用）
.venv\Scripts\python.exe scripts\run_orca_job.py --name EC --smiles "O=C1OCCO1" --job sp --solvent acetonitrile --outdir outputs\week3\orca_smoke --dry-run
```

期望：退出码 0，打印 `"status": "not_run"`，并在 `outputs\week3\orca_smoke\` 下生成
`EC.inp`、`EC.xyz`、`EC_orca.json`。

```powershell
# 3) 真正跑一次单点（需要 ORCA 已就位；先拿最小的 EC 做冒烟）
.venv\Scripts\python.exe scripts\run_orca_job.py --name EC --smiles "O=C1OCCO1" --job sp --solvent acetonitrile --outdir outputs\week3\orca_smoke
```

期望：`"status": "ok"`，并且 `EC_orca.json` 里的 `result.final_energy_eh` 是一个
约 `-4xx` 的 Hartree 数、`scf_converged` 为 `true`、`version` 为你安装的版本号。

---

## 4. runner 用法

```powershell
.venv\Scripts\python.exe scripts\run_orca_job.py --name EC --smiles "O=C1OCCO1" --job sp --charge 0 --multiplicity 1 --solvent acetonitrile --outdir outputs\week3\orca_smoke
```

参数（与 `scripts/run_xtb_job.py` 同风格）：

| 参数 | 说明 |
| --- | --- |
| `--name` | 分子/记录名，决定输出文件名 |
| `--smiles` 或 `--xyz` | 二选一。`--smiles` 用 RDKit 建初始几何（Embed + MMFF）；`--xyz` 直接复用已有几何 |
| `--charge` | 电荷，默认 0 |
| `--multiplicity` | 自旋多重度，默认 1 |
| `--job {sp,opt,freq,opt+freq}` | 作业类型，默认 `sp`（生产协议用单点） |
| `--solvent` / `--epsilon` | 二选一。`--solvent` 走 SMD（如 `acetonitrile`）；`--epsilon` 走裸 CPCM 介电常数；都不给 = 气相 |
| `--outdir` | 输出目录（必填） |
| `--timeout` | 秒，默认 3600 |
| `--nprocs` | 显式指定 `%pal nprocs`；不给则自动（见下） |
| `--maxcore` | 每核内存 MB，写进 `%maxcore`；不给则不写 |
| `--scratch-root` | ORCA 实际运行的 scratch 目录；仅在输出目录非 ASCII 安全时才需要（本仓库在中文路径下，默认回退到 `%TEMP%\electrolyte_orca_scratch`） |
| `--live-log` | 把 ORCA 的输出**边跑边**镜像到这个文件（追加模式），长作业可用 `Get-Content <文件> -Wait` 实时看；`.out` 仍是作业结束后才写 |
| `--dry-run` | 只生成输入文件 + `status="not_run"` 记录，**不需要 ORCA** |

**为什么需要 `--live-log`：** ORCA 的 stdout 在 `toolchain.run_command` 里是**被 Python 捕获**的
（`capture_output=True`），要等进程结束才由 `run_orca` 一次性写成 `<name>.out`；而 ORCA 又是在一个
**跑完就删掉**的 scratch 目录里运行。结果是**作业期间磁盘上没有任何可读的输出**。
`--live-log` 走的是流式分支（`toolchain._run_command_streaming`，底层是 `Popen` + 行缓冲 flush）：
每一行既写进日志文件、又照旧返回给调用方解析，所以它**不改变任何解析结果**，只是让长作业变得可观察。

**几何来源与 RDKit：** `--smiles` 走的是与 xTB 臂**相同**的建几何函数
（`run_xtb_job.build_geometry` / 自写 `write_xyz`）。之所以不用 RDKit 自带的
`MolToXYZFile`，是因为它在**中文路径**下会失败；这是本仓库既有的约定，ORCA 臂沿用。

**建议的工作流：** 生产里 r2SCAN-3c 单点应当坐在 **xTB 优化过的几何**上。
所以一般是先用 `run_xtb_job.py --job opt` 得到优化几何，再把那份 `.xyz`
用 `--xyz` 喂给 `run_orca_job.py`（而不是直接用 MMFF 几何）。

---

## 5. 产物布局与 scratch

每次运行在 `--outdir` 下产生：

```
<outdir>\
  <name>.xyz           使用的几何（来自 --smiles 或复制自 --xyz）
  <name>.inp           生成的 ORCA 输入（保留，便于复核）
  <name>.out           捕获的 ORCA 标准输出（若 ORCA 自己也写了 .out，则用它的那份）
  <name>.gbw           从 scratch 拷回的关键文件（可能是其它名字，取决于 ORCA）
  <name>_orca.json     记录：result + provenance + qc_flags + 输入内容 + 命令行
  <name>_scratch\      ORCA 实际运行的工作目录（结束后被删除；超时则保留）
```

**为什么有 scratch：** ORCA 会在它运行的工作目录里写一大堆临时文件
（`.gbw`、`.densities`、`.bas*`、`.tmp`……）。为了不把 `--outdir` 弄乱，
`run_orca` 会在 `outdir` 下建一个独立的 `<name>_scratch\` 子目录，让 ORCA 在那里跑，
跑完把关键文件（`*.out`、`*.gbw`、`*.xyz`）拷回 `outdir`，再删掉 scratch 目录。
如果发生**超时**，scratch 会被保留，方便你去里面查现场。

> 局限（**未实测**）：Windows 版 ORCA 究竟写哪些辅助文件、`.xyz` 是否总会生成，
> 我没有实机验证过。`run_orca` 用「**广搜 + 拷贝**」的方式收集产物，
> 所以即使文件名/种类与预期不同也不会报错，只是可能少拷或多拷个别文件——
> 等 ORCA 装上后可以按实际输出再微调 `ORCA_ARTIFACT_PATTERNS`。
>
> **2026-09-29 更新：** 已在真机 6.1.1 msmpi 构建上跑通（见 §15），
> `*.out` / `*.gbw` / `*.xyz` 均正常产出与回收；scratch 目录策略见 §13。

---

## 6. `%pal` / `%maxcore` / `%cpcm` 的关系

生成的 `.inp` 由 `build_orca_input` 渲染，模块顺序固定：

```
! r2SCAN-3c [Opt] [Freq]            ← 冻结的方法（FROZEN_METHOD），作业关键字
%pal
  nprocs N                          ← --nprocs，或自动
end
%maxcore M                          ← --maxcore，MB/核；不给则不写
%cpcm                               ← --solvent 或 --epsilon；都不给则不写
  smd true
  SMDsolvent "acetonitrile"
end
* xyz <charge> <multiplicity>
...几何...
*
```

- **`%pal nprocs`（并行）**：不给 `--nprocs` 时自动取 `min(机器核数, 8)`。
  上限 8 是为了**别把共享机器打死**；专用工作站可以显式 `--nprocs 16`。
- **`%maxcore`（内存）**：ORCA 里是**每核**内存 MB。不给就交给 ORCA 默认。
- **`%cpcm`（溶剂）**：`--solvent` 用 SMD（写 `smd true` + `SMDsolvent "名字"`）；
  `--epsilon` 用裸 CPCM（只写 `epsilon`）。两者**互斥**，同时给会直接报错。
  都不给 = 气相（生产里的 $P_1$ 气相量就是这种）。

---

## 7. 结果 JSON、状态与 QC flag 含义

`<name>_orca.json` 顶层关键字段：

- `status`：
  - `not_run` —— `--dry-run`，没跑 ORCA；
  - `ok` —— 正常终止（`ORCA TERMINATED NORMALLY`）；
  - `abnormal_termination` —— 有输出但没正常终止；
  - `execution_failed` —— 超时 / 非零退出码 / 无输出（`error` 字段有原因）。
- `result`：解析出的量（`final_energy_eh`、`scf_converged`、`n_scf_cycles`、
  `imaginary_modes`、`nprocs`、`version`、`normal_termination`、`qc_flags`）。
- `provenance`：方法溯源记录（软件/版本/泛函/基组/RI/色散/网格/SCF 阈值/溶剂/温度/标准态）。
- `input`：生成的 `.inp` 全文；`command`：调用的命令行。

**QC flag（全部取自 `provenance.QC_FLAGS` 的冻结词表，不自造词）：**

| flag | 触发条件（本层） |
| --- | --- |
| `scf_failed` | 输出里出现 `SCF NOT CONVERGED`，或单点作业没有正常终止 |
| `geometry_failed` | `opt` / `freq` / `opt+freq` 作业没有正常终止 |
| `imaginary_mode_unresolved` | `freq` / `opt+freq` 作业里出现 `***imaginary mode***` |

> 词表里还有 `unbound_anion`、`spin_contamination_flag` 等，属于 xTB/分析层；
> ORCA 单点层目前只用到上面三个。（`unbound_anion` 需要占据轨道信息，单点输出里没有。）

---

## 8. ORCA 就位后的方法审计步骤

ORCA 已就位（`check_environment.py` 报告 `orca FOUND ... version 6.1.1 [bundled]`），按顺序：

1. **跑 r2SCAN-3c 臂（方法审计的 ORCA 半边）。** 对 `docs/02_stage1_method_audit.md` 里
   同一套审计分子，在 xTB 几何上做 r2SCAN-3c 单点，得到 $P_1$ 级的气相 ΔSCF / 电子能量。
2. **与 xTB 的 ΔSCF / Koopmans 结果对照。** 现在的 xTB 臂结论是
   「值误差大、但排序保持」（见 `docs/04_stage1_xtb_audit_result.md`）；
   ORCA 只跑 12 个分子就可以问：**这种排序保持能否被更高层理论复现**——
   这正是 Gate 1 想回答的方法学问题。
3. **重评 Gate 1。** ORCA 就位后 `toolchain:orca` 检查转绿，
   blocker 只剩溶液相锚点（`solution_redox_anchors.csv` 里 31 行 `method=est`）。
   两个 blocker 都清掉，Gate 1 才会 CLOSED。

---

## 9. 现在就保证可测（无需 ORCA）

- `tests/test_orca_run.py`：用**假的 `orca.cmd`/`orca`**（回显输入 + 打印 ORCA 风格 stdout）
  覆盖了正常终止、SCF 不收敛、缺 `FINAL SINGLE POINT ENERGY`、超时、非零退出、
  空输出、`--dry-run`、`nprocs` 自适应与显式覆盖、版本解析、QC flag 映射、
  以及「没装 ORCA 时非 dry-run 给出中文安装提示」。
- `tests/test_orca_input.py`：输入构造与能量解析。
- 装了真机 ORCA 后，`test_run_orca_with_a_real_binary` 会自动从 skip 变成真正执行。

运行全部测试：

```powershell
.venv\Scripts\python.exe -m pytest tests -q
```

---

## 10. 安装步骤（本机实测，administrative install）

**来源压缩包：** `E:/Claude Code/Orca.6.1.1.Win64_msmpi.zip`（5.81 GB），来自 ORCA 官方论坛下载页；
包内含 `Orca6.1.1.Win64.exe`、`cabs/Orca6{1,2,3}.cab` 与 `Orca6.1.1.Win64.msi`。

**安装方式（无需管理员权限，administrative install）：** 用 MSI 管理安装把文件摊到一个目录，再直接调用：

```powershell
msiexec /a "<msi路径>" TARGETDIR=E:\ORCA\orca_6_1_1 APPDIR=E:\ORCA\orca_6_1_1 /qb
```

- 本机实测耗时约 **173 s**。
- **已知坑：** `TARGETDIR` 含空格会报 `Error 1606 Could not access network location`，
  所以目标路径**必须无空格**（这里用 `E:\ORCA\orca_6_1_1`）。

**安装结果：** `E:\ORCA\orca_6_1_1\`，共 **92 个 `.exe`**，合计 **16.12 GB**；含 `orca.exe`（267 MB）、
`openCOSMORS.exe`、自带 `xtb-6.7.1pre\`、`datasets\`；**不含 `msmpi.dll`**——并行需要系统 MPI 运行时。

**让仓库用上它（一步建 junction）：**

```powershell
.\scripts\setup_orca.ps1 -Source "E:\ORCA\orca_6_1_1"
```

这会在仓库内建软链接（junction）`.toolchain\orca\orca_6_1_1` → `E:\ORCA\orca_6_1_1`，不额外占空间。

**验证：**

```powershell
.venv\Scripts\python.exe scripts\check_environment.py
```

应输出类似 `orca FOUND ... version 6.1.1 [bundled]`（`[bundled]` 表示命中仓库内 `.toolchain`）。

---

## 11. 版本探测（--version 退出码为 2）

`toolchain.VERSION_ARGUMENTS["orca"] = ("--version",)`，即用 `orca.exe --version` 探测。本机实测打印：

```text
Program Version 6.1.1  -  RELEASE
```

**注意退出码：** `orca.exe --version` 的**退出码是 2**（不是 0）。因此**不能按退出码判断探测是否成功**，
必须解析 stdout 里的 `Program Version X.Y.Z` 横幅（`read_orca_version`）。若横幅读不到会显示
`version unknown`，但不影响运行；真正的版本仍会记录在每次运行的 `.out` 里。

此外，环境变量 `ELECTROLYTE_TOOLCHAIN_ROOT` 可覆盖工具链根目录；`find_executable` 在 bundled 层返回的是
**`resolve()` 之后的 ASCII 真实路径**（不是 junction 路径）——这是 msmpi 并行能正常启动的前提（见 §12）。

---

## 12. 并行与路径约束（msmpi，实测）

Windows 版 ORCA 是 **msmpi** 构建：`%pal nprocs > 1` 时经 `mpiexec` 启动子进程。实测结论：

1. **非 ASCII 路径直接失败。** 若 exe 路径**或其工作目录**含非 ASCII 字符，并行启动失败，
   报 `Error (5)`，日志里路径被写成 `?????`。
2. **junction 也不行，必须 `resolve()`。** 即使 exe 实际位于 ASCII 目录，只要经由含中文的 junction
   路径调用仍会失败；因此驱动在 bundled 层返回 `resolve()` 之后的真实路径。
3. **`nprocs 1`（串行）在中文路径下正常。** 实测串行与并行两条路径得到的**能量完全一致**。
4. **自动降级规则。** 当 exe 路径非 ASCII 时自动降级为 `%pal nprocs 1`，并把原因写入记录里的
   `parallel_note` 字段（`NON_ASCII_PARALLEL_NOTE`）。

---

## 13. scratch 目录策略

ORCA 会在运行目录里写一堆临时文件，所以 `run_orca` 始终在 scratch 目录里跑；问题是**scratch 放在哪**。

- 输出目录**为 ASCII 安全**时，scratch 就在输出目录旁的 `<name>_scratch\`（可追溯、好排查）。
- 输出目录**非 ASCII 安全**时（本仓库在中文路径下），自动改用 `%TEMP%\electrolyte_orca_scratch`。
- 覆盖方式（优先级从高到低）：命令行 `--scratch-root` → 环境变量 `ELECTROLYTE_ORCA_SCRATCH`
  → 输出目录（若 ASCII 安全）→ 系统 `%TEMP%`。
- 跑完把 `*.out` / `*.gbw` / `*.xyz` 拷回 `outdir` 并删除 scratch；**超时**则保留 scratch 供排查。

---

## 14. 性能标定（本机 16 逻辑核，实测 `nprocs 8`）

条件：EC（10 原子），`! r2SCAN-3c` 单点，`nprocs 8`。

| 作业 | SCF 循环 | 墙钟 |
| --- | --- | --- |
| 中性气相 | 10 | 6 s |
| 中性 + SMD(acetonitrile) | 10 | 7 s |
| 阳离子 (+1, mult 2) | 25 | 12 s |
| 阴离子 (−1, mult 2) | 30 | 13 s |

---

## 15. 真实冒烟结果（EC pilot，G1 几何）

几何用 GFN2-xTB 优化几何（G1）。产物目录 `outputs/week3/orca_smoke/`
（4 组 `.inp` / `.out` / `.gbw` / `*_orca.json`）；汇总 `outputs/week3/orca_pilot_summary.json`；
图 `outputs/week3/fig4_ec_ionization_pilot.png`；生成脚本 `scripts/report_orca_pilot.py`。

| 状态 | 能量 (Eh) |
| --- | --- |
| 中性气相 | −342.352339517519 |
| 中性 + SMD(acetonitrile) | −342.366394896331 |
| 阳离子 (+1, mult 2) | −341.956578032757 |
| 阴离子 (−1, mult 2) | −342.257191111986 |

- **溶剂化位移（SMD acetonitrile − 气相）：** −0.3825 eV。
- **垂直 IP = 10.769 eV**；NIST 气相锚点 10.400 ± 0.100 eV → 偏差 **+0.369 eV**。
- **垂直 EA = −2.589 eV** → 气相自由基阴离子不束缚，按协议记 `unbound_anion`（不给数值）。
- **⟨S²⟩：** 阳离子 0.754910、阴离子 0.751298（干净双重态，无自旋污染）。

**与 xTB 代理量的对照（同一 EC 分子）：**

| 量 | 数值 | 偏差 |
| --- | --- | --- |
| r2SCAN-3c 垂直 IP（本机） | 10.769 eV | +0.369 eV（vs NIST 10.400 ± 0.100 eV） |
| GFN2-xTB Koopmans `−eps_HOMO` | 12.402 eV | +2.00 eV |
| GFN2-xTB ΔSCF 垂直 IP | 15.591 eV | +5.19 eV |

即：r2SCAN-3c 把 EC 的垂直 IP 误差从 Koopmans 的 +2.00 eV、ΔSCF 的 +5.19 eV 压到 **+0.369 eV**，
印证「代理量值误差大、但排序可保持」这条 xTB 臂结论值得用更高层理论复核（Gate 1 的方法学问题）。
