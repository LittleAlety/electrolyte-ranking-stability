# R11 例格：EC 阳离子 / CPCM(eps=5) 的 NEB 精修

这是 `docs/31` 批次 B 里 **R11** 唯一还剩的计算。你只要跑这一个文件就够尝鲜了。

## 这一格为什么重要

| 证据 | 对 EC/cation/eps=5 的判决 |
| --- | --- |
| Stage 19（几何判据，RMSD 0.100 A > 0.02 A 阈值） | `distinct_lower` —— 两个弛豫终点是**不同盆地** |
| Stage 21（能量判据，直线插值峰高 0.00424 eV < 1 kT = 0.0257 eV） | `one_basin` —— **同一盆地** |

**两条判据打架**，而且 RMSD 0.100 A 恰好落在 0.021-0.100 A 那条连续带的上端，是"一刀切"最可疑的一格。

直线插值**不是最低能路径**，它的峰高会**高估**真实势垒。所以直线说"没峰"（0.0042 eV）时，
真 NEB 只会给出**更低的峰**——这格大概率会确认 `one_basin`。
真正的价值在于把"插值猜的"换成"算出来的"。

## 文件说明

- `start.xyz` —— 反应物 = Stage 19 `default` 臂弛豫终点（E = -342.050165627717 Eh）
- `end.xyz`   —— 产物   = Stage 19 `moread` 臂弛豫终点（E = -342.050522891612 Eh）
- `neb_EC_cation_cpcm_5.inp` —— 现成的 NEB 输入，10 原子、charge 1 / mult 2、CPCM eps=5.0

## 怎么跑（GUI）

1. 打开 `dist\orca-term-gui.exe`
2. 点左边 **模式 3「跑一个现成的 .inp 文件」**
3. 点 **「添加 .inp...」**，选
   `outputs\week22\neb_example_EC_cation_eps5\neb_EC_cation_cpcm_5.inp`
4. 点 **「开始跑」**

它会**原样**把输入交给 ORCA，不改你的文件。ORCA 的产物（.out / .gbw / _MEP_trj.xyz 等）
全部落在 `.inp` 所在的同一个目录里。

命令行等价写法：

```
cd "E:\Claude Code\电解液溶剂-HB\电解液溶剂HB-Code\outputs\week22\neb_example_EC_cation_eps5"
E:\ORCA\orca_6_1_1\orca.exe neb_EC_cation_cpcm_5.inp > neb_EC_cation_cpcm_5.out
```

## 大概要多久

- `NImages` 指的是**中间镜像数**，不是总镜像数。`NImages 8` => 8 个中间像 + 2 个端点 = 10 个镜像
  （已实测确认：ORCA 输出 `Number of images (incl. end points) .... 10` / `Number of images free to move .... 8`）
- 8 个中间像：**数小时**量级（单机 8 线程，每个镜像每轮一次 r2SCAN-3c 的 SCF+梯度）
- 只想先看看它跑不跑得动：把 `NImages 8` 改成 `NImages 4`，成本大约减半
- 跑完（正常收敛）ORCA 会自己清掉工作目录里那一大堆 `*_im*.tmp` 临时文件；
  若是中途被 Ctrl+C / 被杀掉，它们会留在原地，直接删掉即可（不影响结果）
- `%pal nprocs 8` 可以按你机器空闲情况调；**注意 E:\Claude 那边可能还有别的作业在跑，别把 15 核占满**

## 跑完之后看什么

ORCA 会写一个能量剖面文件 `neb_EC_cation_cpcm_5.interp`，里面有沿路径的能量。
判据沿用 `scripts/analyze_stage21_path.py:64-66,165-168` 的**双侧口径**：

- 中间峰高（最高能量镜像相对两端的高差）**<= 1 kT = 0.0257 eV** -> `one_basin`
- 峰高 **>= 1 kcal/mol = 0.043364 eV** -> `separated`
- 中间 -> `inconclusive`

**注意**：这个阈值属**本阶段内部判据**，不回溯改写 Stage 19 的既有判决（`docs/31` §6 第 2 条的默认裁决）。

## 另外两格（同一个套路，本轮计划里的 2-3 格里剩这两格）

| 格 | 端点目录 |
| --- | --- |
| EC/cation/eps=20 | `outputs/week18/orca_relax_{default,moread}/EC/EC_cation_cpcm_20_*.xyz` |
| TEGDME/anion/eps=20 | `outputs/week18/orca_relax_{default,moread}/TEGDME/TEGDME_anion_cpcm_20_*.xyz` |

（TEGDME 是 16 原子左右，那格会比这个慢。）
