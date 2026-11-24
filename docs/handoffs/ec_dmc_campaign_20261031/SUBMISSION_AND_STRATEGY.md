# EC / DMC 新一轮提交与成功条件（2026-10-31）

本次用户直接要求思考现状并尝试提交几个计算包。已新建三个独立、限额、串行实验；旧 HOLD 包、历史额度和正式验收标签未修改。历史口径仍为 45 accepted / 3 limited，不代表严格五项证据已经全部闭合。

| 作业 | 目标 | 资源上限 | 串行依赖 |
|---|---|---|---|
| 3928499 | EC/LiM²⁺ 原始 p7 起点，严格 Opt → 条件 AnFreq | 4 核 × 4 h = 16 CH | 首项 |
| 3928500 | DMC/LiM²⁺ primary 起点，VeryTightSCF 严格 Opt → 条件 AnFreq | 4 核 × 4 h = 16 CH | afterany:3928499 |
| 3928501 | DMC/M⁺ 已成功末几何，TightSCF 同几何单点 | 4 核 × 5 min = 1/3 CH | afterany:3928500 |

总最坏预留 **32⅓ CH**。资金按救援池保守口径记录：既有核算余量 389.9416667 CH，本轮预留后 357.6083334 CH；本轮提交前实时队列为空、2026-10-31 sacct 查询无已运行条目。该余额依赖既有 10 月核算，并非超算中心账户余额。新预留不是释放旧额度再用；未触碰原独立实验线的 64 CH 包。每包通过正式 submit_hpc_batch 提交器的额度、防重复和实时队列检查；跨包总预留另见 campaign PLAN。三个作业已关闭 Slurm Requeue。

## 为什么选这些计算

- EC：直接从末几何重启会首点收敛，不能凭空补 ΔE。此次使用历史 p7 的原始几何，SHA256 `4cf903d4ff3afa2165cb696044c862ca1cd7d9e1a59660b3b842b2a7be183133`；历史同起点日志首处 RMS/MAX gradient 为 0.0001876480 / 0.0005689979 Eh/bohr，均超冻结阈值。这提高发生实际优化步和打印完整判据的机会，仍不能保证新 SCF 设定下必然多步。
- DMC/LiM²⁺：起点 SHA256 `f619c13234e5455fe0651b7444728e423c1df9975e456c4af0692ce901f8d505`，来自既有 primary。历史末表 RMS/MAX gradient 2.71576e-5 / 8.55657e-5，超冻结阈值。本次 VeryTightSCF + MaxIter 120；保持 4 核，避免把没有证实的 16 核加速当成功条件。
- DMC/M⁺：已有严格 Opt + 0 虚频结果；再次盲目优化收益有限。新单点起点 SHA256 `5b0fc24d033b5f8a80f4609739fb7534089a8920d0daaeecf522b0839282c367`，补齐 TightSCF 与既有 VeryTightSCF 同几何的电子能量/自旋/轨道对照。它只测电子层差异，不能独立批准热校正、协议可比性或系综覆盖。

## 如何提高可验收概率并完整记录

物理方法保持 wB97X-D4/def2-TZVPD + SMD(acetonitrile)。两条优化均用 VeryTightSCF、VeryTightOpt、EnforceStrictConvergence TRUE；五阈值固定为 TolE 2e-7、TolMaxG 3e-5、TolRMSG 8e-6、TolMaxD 2e-4、TolRMSD 1e-4。MaxIter 120 只增加同次作业内步数，不改变验收阈值。ORCA 官方手册也提醒正常终止不等于优化收敛：[Geometry Optimizations](https://www.faccts.de/docs/orca/6.1/manual/contents/structurereactivity/optimizations.html)。

优化完成后必须核对正常终止、真实电荷/重态/电子数、严格收敛回显、最后一表五项数值及冻结容差、原子顺序和连接关系；缺项或失败即停止，不花剩余时间计算频率。通过才在同一分配剩余时间内执行 AnFreq。频率需完整 3N 模式、无负频率、存在 Hessian。两阶段仍需生产级独立科学复核。

每次执行置于唯一 attempts/JobID_元素_重启次数目录；保留输入、stdout/stderr、ORCA 默认轨迹/优化文件、末几何、轨道、Hessian、opt_qc.json 和 workflow_result.json。输入上传前与计算节点启动时都校验 SHA256；本地 submission_journal 与 attempts_ledger 保留真实提交身份。超时仍保留原始输出；不自动重试。

**计算成功与正式验收有区别**：本轮没有新增构象搜索覆盖证据。新数值设置相对于历史协议的可比性、去重和覆盖审仍待处理；禁止借被取消探针背书，禁止改名冒充扭转搜索。完成后应先回收日志和 Hessian、用 sacct 实耗结算，再讨论接入正式候选与下游重建。三包不直接参与自动生产发现，不会单凭技术状态抬升标签。

## 检查与证据

两份实际包驱动器分别用正确电子数验证：2 个合法日志通过；缺 ΔE、超能量阈值、错误电子数、严格回显 False 共 8 个反例全部拒绝。既有针对性测试 20 通过 / 1 失败：失败测试复制已经真实提交过的历史包，带入旧 journal，触发既有防重复提交保护；未改旧包或测试来掩盖该失败。

版本化快照见同目录 `EVIDENCE.json`；全量执行包在 `work/hpc_ec_dmc_*_20261031/`，本轮汇总、授权、上传校验输出在 `work/ec_dmc_campaign_20261031/`。work 层被 gitignore，原始计算输出须终态回收后另行耐久归档。
