# Week 17 成果小结 —— Stage 18（全目录电子身份普查与零成本自诊断）

## 0. 一页结论
- 做了什么：把 Week 16 已经算完的两个 SCF 解当成一个**全目录的电子身份普查**来做（414 对 = 发现集 360 + 留出臂 54，**零新增量子化学作业**）：对每一对只问一句「这两个解的电子身份是同一个，还是两个？」，判据只有 `charge_l1 > 0.039` 一条；同时把默认臂自己那一份 `.out` 里已经打印出来的字段（SCF 轨迹、ORCA 的 small-gap 警告、身份指标、轨道能量）拿来问「能不能看出它停在了高解」。
- 关键数字：身份普查：切点 0.039 落在发现集留下的空隙里（coincident 最大 0.038509、moread_lower 最小 0.039383），可测子集 AUC = 1.000、混淆 TP 37 / FN 0 / FP 0 / TN 239，留出臂套同一刀仍然 AUC = 1.000；分类与身份判定在 414/414 对上一致，规则不一致 0 格。家族分裂：ester / nitrile / sulfone / sulfoxide 四个家族零漏解，漏解全部集中在 cyclic_carbonate（15）、phosphate（10）、linear_carbonate（10）、ether（2）。自诊断：冻结的 `gap_warn_value <= -0.0395` 在发现集 LOO 0.9167（> 基线 0.9111，精确 p = 2.56e-19）却在留出的 54 格上只到 0.7963、**输给**多数类 0.9074，且 5 个真漏解 TP = 0；多变量上限（前 3 特征）LOO AUC 0.836、留出 0.833，同样不及基线。唯一站得住的是单边结论：警告在 37/37 个正例上都出现（反例 0），所以「无警告」可以安全放行，但 237/377 个负例也带警告，故不能反推漏解。
- 质检：核心 QC：1066 个 `.out` 全扫、414 对全部解析（unresolved 0、两臂零缺失）；能量复核 max|delta| = 0.000 eV（容差 1e-09）、几何 414/414 逐字符相同；分类与规则不一致 0 格；身份判定一致 414/414。Part B 的 AUC 精确零分布用 tie-aware Mann-Whitney DP（p = 2.56e-19），留出臂混淆矩阵与单边筛查的必要条件/特异度全部现算并写入。逐项实测值见本目录 verification.json 的 checks。
- 限制：Part A 的 AUC = 1.000 只覆盖 276 个**可测**配对：138 个闭壳层中性格不打印自旋块，它们的 `identity_differs = False` 是从「能量重合到 1e-7 eV + 几何逐位相同」**推断**出来的，不是实测；因此这是对能量分类的**必要条件 test**，**不是**一个新的独立预报量，也不能当成预报模型。Part B 的 `gap_warn_value <= -0.0395` 输在样本外：池化多数类基线被 120 个中性格抬到 0.911，留出臂分辨率只有 1/54；必要条件只由 37 个正例支持，且留出臂 5 个正例**全是阴离子**，阳离子若出现无警告漏解，本语料抓不到（这是已知盲区）。同一 (分子, 态) 的 3-10 个 eps 不是独立行，计数会高估有效样本量；P2 腿仍是 r2SCAN-3c/C-PCM 单点协议，两者都继承 Week 16 的口径。

本文可独立阅读；逐项细节、物理机制与需裁决项见同目录 `week17_report_full.md`。

## 1. 协议与规模
### 协议与规模

- **本周零新增量子化学作业**：Part A 与 Part B 都只读已经存在的 `.out`。全目录扫描 1066 个 `.out`（standard 756 + holdout 108），414 对请求格**全部解析**、`unresolved = []`、default/moread 臂缺失各 0 / 0 格。
- **设计**：414 对 = 发现集 360（12 分子 x 3 态 x 10 电介质）+ 留出臂 54（6 分子 x 3 态 x 3 电介质）。每一对都是「同一格、同一个几何、只换 SCF 初猜」的两个解。
- **Part A（身份普查）**：用 Stage 17 已在用的身份指标（<S^2>、Mulliken/Löwdin 原子自旋、自旋参与率 PR、约化轨道通道）比较两个解，判据只有一条：两臂电荷差的 L1 距离 `charge_l1 > 0.039`。
- **Part B（零成本自诊断）**：只读**默认臂那一个** `.out` 已经打印出来的字段 —— SCF 迭代轨迹、ORCA 自己的 `Small HOMO/LUMO gap` 警告（含带符号值）、上面那套身份指标、以及轨道能量块；协议逐条镜像 Stage 16（发现集筛特征 → 冻结一条规则 → 留一 → AUC 精确零分布 → 留出臂原样打分 → 事后按态分层 → 多变量上限）。

## 2. Part A：电子身份普查
### 硬 QC（全部由脚本现算）

- 能量复核：414 对全部比对，`max |delta_E| = 0.000 eV`（容差 1e-09），`passed = True` —— 两个解的能量就是同一次计算的产物，不是两次独立运行。
- 几何 QC：414 / 414 对的两个几何**逐字符相同**（`all_identical = True`）。
- 分类与规则不一致的格子：**0** 个（规则：`moread_lower when delta_ev < -0.001 eV`）。

### 冻结切点落在一个真实空隙里

- 发现集里 coincident 的最大 `charge_l1` = **0.038509**，moread_lower 的最小 = **0.039383**，切点冻结在 **0.039**，正好落在空隙中（标定范围：discovery arm only; the holdout arm was not consulted）。
- 可测子集上的 AUC：`charge_l1` **1.000000**、`spin_l1` 0.999661、`spin_max_moread` 0.770234、`loss_in_pr` 0.379095、`delta_s2` 0.275133；切点处混淆矩阵 TP 37 / FN 0 / FP 0 / TN 239，Youden J = 1.000。
- 留出臂用**发现集冻结的同一个切点**打分：AUC = 1.000000，TP 5 / FN 0 / FP 0 / TN 31。
- **口径限制（重要）**：138 / 414 对是闭壳层中性分子，它们的输出**不打印自旋块**，所以 `charge_l1 / spin_l1 / delta_s2` 在这些格上**无定义**；可测的只有 276 对。中性格的 `identity_differs = False` 是**推断**（能量重合到 1e-7 eV + 几何逐位相同），不是实测。因此上面的 AUC = 1.000 是「在可测子集上完美分离」，**不能**读成一个新的独立预报量。

### 家族分裂

| 家族 | 格数 | coincident | moread_lower | 身份不同 | 可测 |
| --- | --- | --- | --- | --- | --- |
| cyclic_carbonate | 78 | 63 | 15 | 15 | 52 |
| ether | 69 | 67 | 2 | 2 | 46 |
| linear_carbonate | 69 | 59 | 10 | 10 | 46 |
| nitrile | 60 | 60 | 0 | 0 | 40 |
| ester | 48 | 48 | 0 | 0 | 32 |
| phosphate | 30 | 20 | 10 | 10 | 20 |
| sulfone | 30 | 30 | 0 | 0 | 20 |
| sulfoxide | 30 | 30 | 0 | 0 | 20 |

- 四个家族（ester / nitrile / sulfone / sulfoxide）**一个漏解都没有**；漏解全部落在 cyclic_carbonate、linear_carbonate、phosphate、ether 里。家族比电荷态更锋利：中性格 0 格漏解，阳离子 16 格、阴离子 21 格。

## 3. Part B：零成本自诊断（一条失败规则）
### 冻结规则（发现集，镜像 Stage 16 的选择规则）

- 特征 `gap_warn_value`（signed gap in Eh quoted by the warning; +1.0 when the warning did not fire (a large gap is the healthy case)）：方向 **越小越危险**，阈值 `-0.0395`。
- 记录在案：ORCA 未报警时该字段被填成 +1.0 Eh（gap 大＝健康），全表 140/414 行如此。

### 样本内很好看

- 样本内 accuracy 0.9167 vs 多数类 0.9111；留一 accuracy 0.9167、平衡准确率 0.6864。
- AUC 的精确零分布（exact_mann_whitney_dp，tie-aware Mann-Whitney DP）：观测 AUC 0.0840，**精确 p = 2.561e-19**。这个 p 是真的，但它只回答「这个特征在发现集上有没有信号」，不回答「这条规则能不能用」。

### 样本外输给平凡基线

- 留出臂 accuracy **0.7963** vs 多数类 **0.9074**：**输**。混淆矩阵 TP 0 / FP 6 / TN 43 / FN 5 —— 5 个真漏解**一个都没抓到**。
- 多变量上限（前 3 特征留一逻辑回归）LOO AUC 0.8358、留出 accuracy 0.8333 —— 加参数也没有换来一条可用规则。
- 事后按态：cation 层留一 0.8833 胜过该层基线 0.8667，anion 层 0.7750 **输给** 0.8667。留出臂那 5 个真漏解全是阴离子，所以 anion 层的失败就是全表失败。

## 4. 那条失败规则里唯一站得住的东西：单边筛查
### 那条失败规则里，唯一站得住的一件东西

- 定义：告警规则 = 「该格打印过 `Small HOMO/LUMO gap` 警告」，**零个参数**；它不是新拟合的，是 ORCA 自己在 run 开始时打的。该字段在 414 / 414 对上都有定义（包括 138 个闭壳层中性格 —— 这是身份类特征做不到的）。

### 必要条件（成立）

- **37 / 37 个正例都带警告，反例 0 个**：发现集 32/32、留出臂 5/5。即 `P(无警告 | 正例) = 0.0`。用「无警告」放行一格，**不会**放走任何一个真实漏解。
- 正例带警告时的带符号 gap 范围 -0.0470 ~ -0.0130 Eh，**全为负**；140 个完全无警告的格里 0 个是正例 —— 于是这 140 个格可以整批放行。

### 但不充分（同样成立）

- 负例里也有 **237 / 377**（假警报率 0.6286，特异度 0.3714）带警告 —— 所以蕴含只朝一个方向成立，「有警告 ⇒ 必然漏解」是**错的**。
- 按态看更极端：阴离子 137/138、阳离子 137/138 的负例都带警告（特异度约 0.008），而中性 0 格**一个警告都没有**。

| 规则 | 臂 | 灵敏度 | 特异度 | 精确率 | 准确率 | 平衡准确率 |
| --- | --- | --- | --- | --- | --- | --- |
| any_warning | discovery | 1.000 | 0.372 | 0.134 | 0.4278 | 0.686 |
| any_warning | holdout | 1.000 | 0.367 | 0.139 | 0.4259 | 0.684 |
| frozen_value_threshold | discovery | 0.406 | 0.966 | 0.542 | 0.9167 | 0.686 |
| frozen_value_threshold | holdout | 0.000 | 0.878 | 0.000 | 0.7963 | 0.439 |

### 怎么用

- 正确用法是**单边放行**：没有警告 ⇒ 这一格安全，可以从复审名单里划掉；有警告 ⇒ 不确定，仍需人工看。在 414 行上这会划掉 140 行、丢掉 0 个漏解，但**不能**反过来当成「漏解预警」。
- 纪律：该警告由 ORCA 在**预对角化**阶段打印，落点在 SCF 之前 —— 它说的是「这个体系看起来难」，不是「这个 SCF 收敛到了高解」。可迁移范围仅限同一 ORCA 版本、同一套预登记输入清单与这 414 格设计。
- 声明：必要条件只由 37 个正例支持（发现集 32 + 留出臂 5）；留出臂上的「零反例」几乎是平凡陈述，真正有信息量的是发现集那一份。

## 5. 产物与口径
### 本周产物

| 文件 | 说明 |
| --- | --- |
| `stage18_identity_census.json` | Part A 全部聚合（thresholds / census / energy_crosscheck / geometry_qc / classification_counts / separation / by_state / by_family / cells） |
| `stage18_identity_census.csv` | Part A 逐格表（414 对：两臂 .out 路径、<S^2>、自旋中心、PR、L1、几何 QC、identity_differs） |
| `stage18_identity_census_by_family.csv` / `_by_classification.csv` | Part A 按家族 / 按分类的汇总表 |
| `stage18_identity_census_summary.md` | Part A 的中文小结 |
| `stage18_selfdiagnosis.json` | Part B 全部内容（features / screen / frozen_rule / in_sample / loo / significance / holdout / by_state_post_hoc / multivariate_ceiling / one_sided_screening） |
| `stage18_selfdiagnosis_features.csv` | Part B 逐格特征表（414 行 x 34 列，全部读自默认臂那一个 .out） |
| `stage18_selfdiagnosis_features_by_state.csv` | Part B 按 (臂, 态) 的特征均值表 |
| `stage18_selfdiagnosis_summary.md` | Part B 的中文小结 |

## 6. 产物清单
- `artifacts/F34_stage18_identity_census.png`
- `artifacts/F35_stage18_selfdiagnosis.png`
- `artifacts/figure_manifest_week17_stage18.md`
- `stage18_identity_census.csv`
- `stage18_identity_census.json`
- `stage18_identity_census_by_classification.csv`
- `stage18_identity_census_by_family.csv`
- `stage18_identity_census_summary.md`
- `stage18_selfdiagnosis.json`
- `stage18_selfdiagnosis_features.csv`
- `stage18_selfdiagnosis_features_by_state.csv`
- `stage18_selfdiagnosis_summary.md`
- `week17_report_full.md`

## 7. 源文件缺失
- 无（全部源路径均存在）
