# physics_completion_v1 结题报告（研究问题 → 结果 → 证据 → 限制）

> 本报告汇总新阶段 WP0-WP6 的**首轮**产物。它只登记定义、样本、方法与既有冻结数据上的复算；
> **排序/配对证据零新增电子结构计算、零数据剔除、零阈值改动**（WP1 的 161 个独立方法审计作业、WP2 的 12 分子四主态 pilot 与 4 分子 x 4 主态生产 Opt/Freq 单列，原始日志留在仓库外，不入交付镜像）。旧结论（含 Gate 1 NOT CLOSED / NOT CLOSABLE）原样保留。

## 1. 研究问题与可声明边界

续问：哪些缺失物理会改变候选选择；这种变化是否超过独立评估的方法与采样敏感性；恢复指定计算目标的选择需要多少额外信息。
氧化为首轮确认性主轴；还原为有条件探索性副轴（只允许 `molecule_centered_redox` 进入主 ranking）。
本批次**不**给出真实电解液稳定窗口、最佳配方或 SEI/CEI 性能。

## 2. 逐工作包结果

| WP | 周 | 产物 | 首轮结果 | 关键限制 |
| --- | --- | --- | --- | --- |
| WP0 | week37 | 定义迁移表 + 协议 + 样本 | 7 个量名/方向/状态身份登记；5 条历史结论迁移；12/8/4 样本 | 只登记，未产生新计算 |
| WP1 | week38 | 独立方法审计表 + 128 格实测矩阵 | 4 设定 × 4 状态 × 8 分子 = 128 单点全部收敛（另 32 格弛豫腿）；泛函效应 >> 基组效应；2 个冻结翻转的方法轴 certified=True | 气相 r2SCAN-3c 冻结几何；8 分子口径；采样界限未纳入 |
| WP2 | week39 | 固定背景配对自由能标签 | 48 行账本；4 主集分子 x 4 主态生产中已登记 6/16 个真实 Opt+Freq G 标签（60.810223 core-hours，另含 1 条 def2-TZVPD 中性腿）| 生产首段每态单构象；其余状态在产；基组一致 redox 的自由腿与 Li 腿分开登记，未齐不补数 |
| WP3 | week40 | pair 证据表 + 机制案例 | P1v→P1a（n=12，66 pair）逐对复算 55/9/2；2 个机制案例 | 单 rung 演示；多方法范围已由 WP1 审计给出（方法轴） |
| WP4 | week41 | 外部可比性审计 | 7 氧化锚点逐条重算 tau_b=0.4286；三级分类 | transcription-only；21 pair 非独立样本 |
| WP5 | week42 | Δ-learning + 成本账本 | 端点/泄漏防线冻结；成本 3 项 MISSING | 回放非盲预注册；绝对成本缺失 |
| WP6 | week43 | 显式配体检查（可选） | R=DME 协议登记；不纳入首轮闭环 | 依赖关键 free→Li 结论先可解析 |

## 3. 证据分层

- **模型事实**：所有量名、方向、状态身份、矩阵、账本、判据与停规则（WP0-WP2、WP5 协议）。
- **统计判定**：三态判据（STABLE/UNRESOLVED/ROBUST_INVERSION）、分辨率曲线、tau_b、端点（WP3、WP4、WP5）。
- **材料意义**：本报告不给绝对性能排名、不给配方建议；一切材料级结论标记为**待验证推断**。

## 4. 关键数字（可复算）

- WP3：P1v→P1a 氧化 n=12、66 pair；复算 STABLE 55 / UNRESOLVED 9 / ROBUST_INVERSION 2，与冻结载荷一致。
- WP1：128 格本机单点 + 32 格弛豫腿全部收敛；竖直 IP 的泛函效应中位 0.369492 eV、基组效应中位 0.027111 eV；EMC|GBL、EMC|SL 的稳健翻转在 4 设定下方法轴 certified=True。
- WP4：Ue1994_Okoshi2015 序列 14 行、被模型覆盖 7 个；逐对一致 15 / 不一致 6 → tau_b = 0.428571（< 0.90）。
- WP2：48 行状态账本，其中 4 主集分子 x 4 主态生产已登记 6/16 个真实 Opt+Freq 自由能标签（qRRHO，合计 60.810223 core-hours），另登记 1 条 def2-TZVPD 中性腿；未完成的主态保持空串（None），未把缺值写成 0。
- WP5：shift 在 tau_b 上更好的格数与冻结表一致；成本账本 3 项 MISSING。

## 5. 限制与停止规则

- 方法分歧与目标间距相当 → `unresolved`；两轮采样不收敛 → `sampling_limited`；
  无分子中心还原态 → `identity_outcome`；外部量不可比 → `validation_limitation`；AL 不胜随机 → 报告无证据支持节省。
- WP2 生产：主态只登记 6/16；Li 配位态（LiM_plus / LiM_2plus）生产侧全部未开始（0/8，只有 12 分子的 xTB/SP 级 pilot）；每态仍是**单一代表结构**（n_conformers = 1），方案 6.1 的多构象 / 多 motif 系综（12x4 起步、上限 144、6 kcal/mol 窗口、最多 3 结构）尚未执行；基组一致 redox 只完成自由腿 1/4（GBL，def2-TZVPD 中性腿 + TZVPD 阳离子腿）与 Li 腿 0/4，未齐的腿留空。
- WP4：7 个氧化锚点只做到 transcription 级，回原文页码 / 表号复核因本机网络不可达 + 主要候选源付费墙而处于**硬阻塞**。
- WP3：pair rung 的 12 个成员与主集差一个分子（含 SN、不含 DEC）。
- Gate 1 保持 NOT CLOSED / NOT CLOSABLE；`NOT CLOSABLE` != `NO SUCH DATA EXIST ANYWHERE`。
- 措辞只用 designated computational target / designated reference model；禁用 validated target。

## 6. 三种可能都算完成

若无稳健翻转：可得出「在所测模型与独立敏感性界限内没有认证翻转」，但仍明确 unresolved 比例。
若出现翻转：必须跨合理方法/采样稳健且状态可比。若绝大多数 unresolved：输出候选可接受集合，停止伪精确排名。
首轮已把 WP1 独立方法审计从「登记」推进到「128 格实测 + 方法轴认证」，并把 WP2 自由能标签从 1 行 pilot 推进到 4 分子 x 4 主态的真实 Opt+Freq（本次登记 6/16 个主态，另含 1 条 def2-TZVPD 中性腿，其余在产）；余下状态、多构象采样界限与外部锚点可比性仍待补，故完整翻转判定仍未闭合。
