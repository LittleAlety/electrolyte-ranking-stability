# 进度复核、口径更正与追加提交（2026-11-01，北京时间约14:00）

## 最新作业

- **3944657** 三个 VeryTightSCF 梯度均 COMPLETED 0:0，耗时173/193/168秒；原日志与engrad已取回，实耗0.5933333333 CH。
- **3944659_0 EC/LiM²⁺ 配位探针**：内部89分钟时间额度耗尽，Slurm FAILED 2:0，5342秒（5.9355555556 CH）。停止前最新表为能量变化4.739e-7 > 2e-7，其他四项YES；没有完整五项通过，不启动频率，也不自动重试。驱动结果 reason=shared allocation time budget exhausted；不能把宽泛状态名 execution_or_identity_failed 误解为证实了身份错误。
- **3944659_1 DMC/LiM²⁺ 配位探针**：已接替EC开始运行，结果尚未产生。

## 一项必须更正的分析

此前将 `.engrad` 的未变换笛卡尔分量 RMS/MAX 直接与优化器最后收敛表阈值比较，再据此判“原几何驻点条件失败”，这个结论撤回。ORCA默认使用冗余内坐标；在没有统一坐标变换/投影和梯度口径前，不能把这些数字当同一判据。[官方坐标系统说明](https://www.faccts.de/docs/orca/6.1/manual/contents/structurereactivity/optimizations.html)

本轮将新冷启动 **VeryTight 笛卡尔梯度**与原始Opt日志最后 **CARTESIAN GRADIENT** 做同类比较，得到：

| 体系 | 原Opt末步笛卡尔RMS | 新VeryTight笛卡尔RMS |
|---|---:|---:|
| EC/LiM²⁺ | 4.56572e-5 | 4.56503e-5 |
| DMC/LiM²⁺ | 1.79641e-5 | 1.78473e-5 |
| DMC/M⁺ | 1.60225e-5 | 1.56981e-5 |

两者数值接近。这里仍只报告同类数值，不把“接近”写成通过新的阈值。原始优化五项表的通过证据保持有效；正式标签未改。已在前轮分析报告顶部标记更正，原始日志与数值证据不改写。机器可读比对在 GRADIENT_METRIC_CORRECTION.json。

Tight/VeryTight的固定几何频率、能量和梯度仍可做方法敏感性诊断；这些诊断本身没有冻结的全队列可比性验收判据，故尚不能自动合并成正式系综。

## 新增计算已实际入队

| 作业号 | 内容 | 资源上限 | 依赖 |
|---|---|---:|---|
| **3945086** | EC/LiM²⁺、DMC/LiM²⁺、DMC/M⁺ 三个相同成功几何，VeryTightSCF + DefGrid3 EnGrad | 3元素，各4核×15分钟，共3 CH | afterany:3944659 |
| **3945087** | DMC/M⁺ 两个不同桥键的原始+60°重骨架起点，严格Opt→条件AnFreq | 2元素，各4核×90分钟，共12 CH | afterany:3945086 |

新增 **5个元素、15 CH**，数组均%1串行、no-requeue，不自动续算。原始准备/旧失败包不覆盖，不把历史费用清零。

### 为什么追加这些

**积分网格诊断**：保持原始几何、泛函、基组、溶剂、VeryTightSCF不变，只加入DefGrid3，后续与本次已取得的同类笛卡尔梯度比较。ORCA手册把DefGrid3定义为更高质量但更重的积分网格；这是检查积分敏感性的手段，不能预先断言它必能消除EC的ΔE波动，更不能自动把生产协议换成DefGrid3。[数值积分说明](https://www.faccts.de/docs/orca/6.1/manual/contents/essentialelements/numericalintegration.html)

**DMC/M⁺ 构象验证**：使用此前气相xTB已保持共价结构的原始扰动起点 probe_01 / probe_03，对应桥键(1,2)、(2,4)，全原子拓扑登记为真实单键；本轮重新调用 validate_candidate_start，二者均为 heavy_fragment_torsion，且彼此不是同一等价起点。采用原始扰动而非高度汇聚的xTB终点；不声称两者一定能形成新极小。它们与在途Li配位探针属于不同坐标方向，补充实际生产级覆盖证据。

两腿均电荷+1、双重态、47电子；严格阈值不变，优化步数最多120，内部总时限89分钟。只有五项全通过及结构身份检查通过才在剩余时间做频率。技术完成后仍待完整身份、去重、协议可比性与coverage，不自动抬升accepted。

## 提交前检查与耐久证据

两个新资源配置已版本化登记：orca_grid_gradient_4c_15m_v1、orca_conformer_probe_4c_90m_v1。相关资源/提交门测试 **16项通过**，覆盖15分钟/90分钟真实提交参数、元素数与费用上限、超额拒绝。没有更改旧资源配置语义。

全部任务表、根包清单与内层inputs.sha256按原始字节检查无CR，并逐文件核对存在性与哈希；上传后再由远端sha256sum检查。提交仍通过受保护WHU HPC桥及项目的队列、防重复和费用检查。实际队列依赖已核对。

授权、输入/几何/驱动器/manifest/journal与SHA256快照见 NEW_SUBMISSION_EVIDENCE.json；实时Slurm快照见SACCT.txt。执行目录是work/hpc_grid3_gradients_20261101、work/hpc_dmc_heavy_probes_20261101，授权汇总在work/ec_dmc_next_queue_20261101。
