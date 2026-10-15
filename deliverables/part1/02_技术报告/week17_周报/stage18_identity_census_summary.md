# Stage 18 / Week 17 · Part A —— 全目录电子结构身份普查

- 配对总数 **414**（发现集 360 + 留出臂 54）；判为重合 **377** 对、漏解 **37** 对。
- 一句话结论：分类与身份**完全自洽**——判为 `coincident` 的对两臂身份逐位相同，判为 `moread_lower` 的对身份确有差异，全目录未发现反例。

## 1. 覆盖 QC
- `outputs/week*/orca*/**/*.out` 扫描 **1066** 个文件；Stage 17 正则直接命中 756 个，留出臂 `holdout` 命名 108 个经「去除该 token 后复用同一正则」入索引（未新写解析器）。
- 索引键 828 个；重复键 36 个（冗余路径 36 条，按最新周/最新 mtime 去重取用）。
- 覆盖 QC：请求 **414** 对，解析 **414** 对，未解析 **0** 对（default 臂缺 0，moread 臂缺 0）。
- 两臂唯一解析：**414/414**；未解析即 `raise SystemExit`，不跳过、不伪造。

## 2. 能量复核（独立于 Stage 16 表）
- 从 `.out` 重算 `delta_ev = e_moread − e_default`（eV），与 Stage 16 对齐表逐对比对（414 对），**max|Δ| = 0.000e+00 eV**（容差 1e-09 eV）→ 通过。

## 3. 几何 QC
- 两臂 `CARTESIAN COORDINATES (ANGSTROEM)` 逐位相同：**414/414**（全部一致）。

## 4. 分类计数复核
- 发现集：{'coincident': 328, 'moread_lower': 32}；Stage 16 公布值 {'coincident': 328, 'moread_lower': 32, 'moread_higher': 0}。
- 留出臂：{'coincident': 49, 'moread_lower': 5}。
- `classification` 与规则（moread_lower when delta_ev < -0.001 eV）不一致的对：**0**。

## 5. coincident 子集的身份重合率（独立于能量的交叉验证）
- 全部 `coincident` 对 377 对：该子集中可测的都判为「相同」，即 **239/239**；另有 138 对为闭壳层、身份量不可测（自旋通道平凡相同，无电荷表可读，见第 9 节）。
- 只看开壳层可测子集：**239/239** = 1.0000，即两臂电荷/自旋分布逐位重合，无一对被判为身份不同。
- 漏解子集：身份判为「不同」 **37/37** = 1.0000，无一对被判为相同。
- 全目录一致性：**414/414** （可测 276 对 + 不可测 138 对）。

## 6. 漏解子集上的分离度
- 冻结判据：`charge_l1 > 0.039` 判为「身份不同」（open-shell 才可测，见第 9 节）。
- 校准口径：只用**发现集**定阈值。发现集里 coincident 的最大 `charge_l1` = 0.038509，moread_lower 的最小 = 0.039383，两者之间是空隙；取空隙中点并取整为 0.039（等价于发现集 ROC 的 Youden-J 最大点）。
- 全目录 AUC(`charge_l1`) = **1.000000**；混淆矩阵 tp/fn/fp/tn = 37/0/0/239，敏感度 1.0000、特异度 1.0000、Youden J = 1.0000。
- 其他通道 AUC：`spin_l1` 0.999661、`delta_s2` 0.275133、`loss_in_pr` 0.379095、`spin_max_moread` 0.770234（仅作参考通道，不进入判据）。
- 分布（全目录，coincident 可测 239 对 / moread_lower 可测 37 对）：
  - `charge_l1` coincident min 0.000451 / p50 0.001719 / max 0.038509；
  - `charge_l1` moread_lower min 0.039383 / p50 0.938032 / max 4.050934；
  - `spin_l1` coincident min 0.000150 / p50 0.001716 / max 0.074962；
  - `spin_l1` moread_lower min 0.039056 / p50 0.878885 / max 3.935645；
  - `delta_s2` coincident min -0.000375 / p50 0.000000 / max 0.000140；moread_lower min -0.004534 / p50 -0.000164 / max 0.001457。
  - `loss_in_pr` coincident min -0.230546 / p50 0.000000 / max 0.023797；moread_lower min -1.054358 / p50 -0.184623 / max 0.834168。
  - 自旋中心同一原子 / 轨道标签同一：coincident 206/377、233/377；moread_lower 24/37、13/37。

## 7. 留出臂（6 个验证分子 / 54 对）
- 分类：{'coincident': 49, 'moread_lower': 5}；出现漏解的分子：DEC (3); TEGDME (2)。
- AUC(`charge_l1`) = **1.000000**；tp/fn/fp/tn = 5/0/0/31。
- 用发现集冻结的阈值 0.039 直接套用：留出臂 coincident 可测 31 对全部判为相同、moread_lower 5 对全部判为不同。
- 结论：留出臂与发现集**同一种模式**，且 Week 15 报告的 DEC、TEGDME 两处漏解在身份指标上同样落在漏解一侧。

## 8. 按电荷态 / 按家族 / 按分类
- **anion**：138 对，coincident 117/moread_lower 21，identity_differs 21（可测 138），charge_l1 均值 0.300433。
- **cation**：138 对，coincident 122/moread_lower 16，identity_differs 16（可测 138），charge_l1 均值 0.030321。
- **neutral**：138 对，coincident 138/moread_lower 0，identity_differs 0（可测 0），charge_l1 均值 n/a。
- **cyclic_carbonate**（EC; FEC; PC; VC）：78 对，coincident 63/moread_lower 15，identity_differs 15，charge_l1 均值 0.197125。
- **ester**（EA; GBL; MA）：48 对，coincident 48/moread_lower 0，identity_differs 0，charge_l1 均值 0.002450。
- **ether**（DME; DOL; TEGDME）：69 对，coincident 67/moread_lower 2，identity_differs 2，charge_l1 均值 0.179600。
- **linear_carbonate**（DEC; DMC; EMC）：69 对，coincident 59/moread_lower 10，identity_differs 10，charge_l1 均值 0.513163。
- **nitrile**（AN; SN）：60 对，coincident 60/moread_lower 0，identity_differs 0，charge_l1 均值 0.001434。
- **phosphate**（TMP）：30 对，coincident 20/moread_lower 10，identity_differs 10，charge_l1 均值 0.165695。
- **sulfone**（SL）：30 对，coincident 30/moread_lower 0，identity_differs 0，charge_l1 均值 0.002417。
- **sulfoxide**（DMSO）：30 对，coincident 30/moread_lower 0，identity_differs 0，charge_l1 均值 0.001424。

## 9. 口径纪律
- **事后刻画，不是事前预警**：阈值 0.039 是在已知能量分类之后、从发现集上读出来的。它描述「两类长什么样」，不能反过来当成「未跑 MORead 就能预测哪里会漏解」的筛选器；留出臂只作外样本核对，没有参与定阈值。
- **闭壳层无可测身份量**：中性分子输出只印 `MULLIKEN ATOMIC CHARGES`（无自旋列），Stage 17 的读取器按 `...AND SPIN POPULATIONS` 表头定位，因此闭壳层返回空表，`charge_l1`/`spin_l1`/`delta_s2` 等均为未定义。全目录 138 对闭壳层落在可测集之外，其 `identity_differs=False` 是「能量 1e-7 eV 级重合 + 几何逐位相同 + 自旋通道平凡为零」的推断，而非电荷测量结果；第 5 节因此同时给出全体与可测子集两个重合率。
- **轨道标签用的是 reduced-orbital SPIN 子块里 |值| 最大的原子-轨道通道**；在弥散基组下该最大值常落在弥散 s 通道，而不是 π* 的 pz 通道，所以 `orbital_*` / `same_orbital_label` 应读作「弥散自旋通道是否同一」而非「π* 轨道是否同一」。
- `same_spin_center` / `same_orbital_label` 取的是 argmax，在两个近简并原子之间会跳变，因此只作描述列，不进入判据。
- `geometry_identical` 是两臂坐标块的逐字符比较；`loss_in_pr` = PR(moread) − PR(default)，为正表示更多解更弥散。
- 全部数字由 `stage18_identity_census.json` / `.csv` 现算，本文件不手工抄写。

