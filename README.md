# 电解液溶剂HB —— 决策稳定性研究（Electrolyte Ranking Stability）

> **Scope.** This repository does not establish a definitive electrolyte-solvent ranking. It studies the stability, instability, and information cost of ranking decisions under progressively more realistic computational models.
>
> 本仓库**不**给出「18 个溶剂谁最好」的最终排行榜；它研究的是**排序决策**在逐步更真实的计算模型下的**稳定性 / 不稳定性 / 信息成本**。任何把本仓库引用成「最终性能排行榜」的读法都是误读。

## 当前工作入口（与历史阶段分开）

本阶段：12 分子 × 4 主态，wB97X-D4/def2-TZVPD + SMD；解析梯度优化 / AnFreq。以下读自版本化产物，不代表实时超算队列。

**周次口径**：本仓库的 `week` 指**工作轮次**，**不是日历周、也不是真实时间**；历史产物与文件名沿用 `weekNN` 前缀（如 `outputs/week25/`、`docs/40_week25_gate1_report.md`），正文与路径指同一编号。

| 验收层 | 当前快照 | 权威来源 |
| --- | --- | --- |
| primary 优化 / 频率 QC | 48/48（全成员身份另列） | [主态账本](outputs/physics_completion/free_states/production_ledger.csv) |
| 生产系综 | **accepted 44/48** · provisional 0 · limited 4 | [系综标签](outputs/physics_completion/ensembles/production_ensemble_labels.csv) |
| 全成员前沿 / 身份登记 | 解析 80/80 · 证据表标记 verified 80/80；不代表独立完整科学身份 QC | [前沿报告](outputs/physics_completion/frontier/frontier_localization.md) · [证据表](outputs/physics_completion/frontier/frontier_identity_evidence.csv) |
| 现有合规总体项 | **blocked_on_production**（不是完整 v3 严格目标证书） | [合规台账](outputs/physics_completion/compliance/plan_compliance.md) |
| **逐项严格总闸门** | **未通过** · 缺口 `ensemble_not_48_accepted`、`wp5_full_target_pool_evaluated` | [strict_readiness_wiring](scripts/wp_production/strict_readiness_wiring.py) |

未 accepted：`DMC/M_plus`、`DMC/LiM_2plus`、`DOL/LiM_2plus`、`EC/LiM_2plus`。

**四态现状（逐态一行，勿读成"只差四态"）**：`DMC/M_plus`、`DMC/LiM_2plus` = `unresolved_qc`（`draft_torsion_probe`：各有 **7 个从未被合法探过的登记二面角**，去重后为 2 个 / 1 个重骨架操作＋5 个可声明配位探针）；`DOL/LiM_2plus`、`EC/LiM_2plus` = `search_exhausted`（**筛选级单盆地、0 个登记扭转**；路线是合法环形变＋声明式 Li 配位探针，而环 pucker 的合法位移只有 0.02–0.08 Å，放大到能到达别的盆地就会断环）。[路由表](outputs/physics_completion/recovery/probe_routes.csv)

**筛选轮打包就绪但未提交**：`work/hpc_four_state_p4_xtb_screening_v1` · **8 任务** · `xtb_screening_v1` · **2 核 × 2 h** · `submitted=False` · gate **HOLD**。包内每任务含 `geom.xyz` / `job.inp` / `cores.txt` /`inputs.sha256` / `candidate.json`，`candidate_gate_contract=validate_candidate_start_v2`，并附 `PACKAGE_SHA256SUMS` 与确定性重建锁 `selection.lock.json`。**未提交**是因为一次性授权尚未由用户发出——工程就绪不等于执行授权。

**干净环境复现（工程可复现性）**：`work/` 是 gitignored 的机器本地层（约 12 GB，干净克隆没有）。依赖它的**构建器会响亮拒绝**（不是静默降级），依赖它的**测试会带理由跳过**（`tests/test_clean_clone_dependencies.py` 钉住拒绝侧）。

**五分钟自证**（任一条都可独立复核）：

```bash
.venv/Scripts/python.exe -B docs/handoffs/four_state_recovery_20261023/preflight.py   # 0=契约一致（不等于可提交）
pwsh -NoProfile -File scripts/wp_production/finalize_wp2.ps1                          # 79 步 + OFFLINE CLOSURE GREEN
pwsh -NoProfile -File scripts/wp_production/finalize_wp2.ps1 -Commit                  # 仅当全部一致才提交
```

工程检查通过不等于科学完成；完整身份、正式 WP5 与触发后的 WP6 仍须单独核验。

**先读**：[项目导航 / 下一步 / 核心代码](docs/PROJECT_GUIDE.md) · [当前恢复报告](outputs/physics_completion/recovery/strict_recovery_v1_report.md) · [科学协议](docs/physics_completion_protocol.md) · [目录地图](docs/65_repo_layout.md)

**网页**：[静态页面源码](docs/index.html)。仓库可见性与 Pages 托管由 GitHub 设置决定；前端假密码仅为演示门禁，不是保密措施。

---

## 历史研究与证据

**项目状态**：`Gate 0` **CLOSED** · `Gate 1` **未闭合且 NOT CLOSABLE**（排序层已评估：`ordering_disagrees`，τ_b = 0.4286 < 0.90，n_pairs = 21；绝对标定层按 limitation 处理；预注册要求的同源序列在公开文献中不存在，**不再尝试把它做成 PASS**，见 `docs/gate1_negative_result.md`）。

| 计数 | 值 | 含义 |
| --- | --- | --- |
| robust inversion | **0 observed** | 在 20 个 (台阶, 轴) 组合中，没有任何 pair 被**反向证明**（1σ 主口径） |
| unresolved（最高） | **80.0%** | 大量 pair 的证据**不足以判定**方向 |

> **0 robust inversions ≠ 0 ranking instability.** 把 `f_robust_inv = 0` 读成「排序稳定」是本项目最容易被误读的一处；正确的读法是「不可判定主导（`evidence insufficient to resolve`）」。汇总图 `outputs/figures/F56_r13_summary.png` 把这句话画进了图里。

## 这个仓库回答什么

本项目把电解液候选的排序看成一个需要审计的**决策过程**，而不是一张静态排行榜。研究主线是 `cheap proxy → designated computational target → uncertainty-aware rank change → mechanism → minimal budget`。

- **排序何时可信**：同时报告 `STABLE / UNRESOLVED / ROBUST_INVERSION`，不把证据不足误写成稳定。
- **哪一层改变了决定**：分离方法、环境、几何、配位与显式第一溶剂壳的影响。
- **为什么改变**：核心观察是位移的离散度比平均位移更能解释排序改写。
- **需要算多少**：用预注册判据、Δ-learning 与主动查询估计达到指定决策分辨率的信息成本。

核心边界：core set = **18**、broad pool = **40**；它们支持方法学与机制层面的 proof-of-concept，不支持对整个电解液化学空间作普适排名。

## 从哪里开始

| 你要找的内容 | 入口 |
| --- | --- |
| 当前任务、下一步与核心代码 | [项目导航](docs/PROJECT_GUIDE.md) |
| 按研究主题拆分的历史进度 | [进度与日志索引](docs/progress/README.md) |
| 10 个研究问题的结论矩阵 | [最终结论](FINAL_CONCLUSIONS.md) |
| 当前生产批次科学协议 | [physics completion 协议](docs/physics_completion_protocol.md) |
| 目录、权威产物与复现边界 | [仓库地图](docs/65_repo_layout.md) |
| 脚本用途与入口 | [脚本索引](scripts/README.md) |

周次现在只作为历史定位符，不再承担仓库导航职责。原始 `outputs/week*`、编号周报与交付镜像均保留原位；新的主题日志只做索引和解释，不复制或改写证据。

## Gate 与声明边界

| Gate | 状态 | 解释 |
| --- | --- | --- |
| Gate 0：定义冻结 | **CLOSED** | 定义、阈值与 amendment 记录已冻结。 |
| Gate 1（方法 / 锚点） | **NOT CLOSED** | **排序一致性层**首次可评但未通过：Kendall **tau_b = 0.4286 < 0.90**、**n_pairs = 21**，判 **`ordering_disagrees`**（一致 15 / 不一致 6）（`outputs/week25/series_rel_ordering_check.json`）。**绝对标定层**：溶液相锚点 31 行 `est` 按 R7 裁决记为 **limitation**，不再单列 blocker。**可闭合性**：判 **NOT CLOSABLE**（预注册要求的同装置 / 同判据 / ≥ 7 分子同源序列在公开文献中不存在，最长 k = 1），作为 negative result 记录，不事后救援。 |
| 严格生产总闸门 | **未通过** | 当前缺口以 README 顶部的逐项严格总闸门为准。 |

**0 robust inversions ≠ 0 ranking instability.** 大量 pair 仍为 `UNRESOLVED`；零次稳健反转不能单独作为“排序稳定”的证据。

**NOT CLOSABLE ≠ NO SUCH DATA EXIST ANYWHERE.** 这里的 NOT CLOSABLE 只表示：在预注册的检索和验证标准下，没有定位到足以闭合 Gate 1 的同源序列；未来若出现合格数据，该判断可被证伪。

## 快速复核

```powershell
python scripts/build_github_readme.py --check
python -m pytest tests/test_repo_layout.py tests/test_terminal_site.py -q
pwsh -NoProfile -File scripts/wp_production/finalize_wp2.ps1
git diff --check
```

`finalize_wp2.ps1` 是当前生产链的一致性检查入口；不带 `-Commit` 不会提交计算。ORCA / xTB 计算只在受控环境运行，本地复核主要读取已版本化的账本和派生产物。

## 目录约定

| 路径 | 角色 |
| --- | --- |
| `config/` | 冻结定义、预注册阈值与批次配置 |
| `data/` | 元数据与外部锚点 |
| `src/electrolyte_ranking/` | 可复用的排序、QC、不确定性与 provenance 库 |
| `scripts/` | 构建、审计、分析与收口入口 |
| `outputs/` | 版本化证据；历史周目录保持不动 |
| `docs/` | 协议、主题日志、交接与解释性文档 |
| `deliverables/` | 对外交付镜像 |
| `work/` | 本机临时计算层；不作为 GitHub 可复现证据 |

## 维护规则

- README 由 `scripts/build_github_readme.py` 确定性生成；不要直接手改派生数字。
- 新进展先写入对应主题日志，再把机器可读证据放入稳定的 `outputs/` 主题路径。
- 历史 `week*` 路径只归档，不再继续扩展新的周次导航。
- 任何结论都应给出 evidence path、适用样本、判据和 limitation。

## 引用与许可

引用本仓库时，请把它描述为**排序决策稳定性与信息成本研究**，不要描述成最终溶剂性能排行榜。若需复核具体数字，从 [最终结论](FINAL_CONCLUSIONS.md) 或 [主题日志](docs/progress/README.md) 进入对应冻结产物。
