# 本轮基线冻结 + 超算实时核验（2026-10-23 14:22 +0800）

本文件是四态恢复目标执行顺序**第 1 步**的交付物。它只记录**已核实的事实**，
不授予任何提交权限、也不代表未来时刻的队列状态。

## 1. 代码基线

| 项 | 值 |
|---|---|
| HEAD | `462f7f8b06a72684084cb2a33319bf10cedd5699` |
| 工作树 | **干净**（`git status --porcelain` 行数 = 0） |
| 收口链 | `finalize_wp2.ps1` **79/79 全绿**（末行 `OFFLINE CLOSURE GREEN`） |
| 全量离线 pytest | 全绿（排除 4 个预存 ORCA/xtb 活动节点文件） |

## 2. 协议与输入哈希（sha256 前缀，用于判断基线是否漂移）

> ⚠ **这张表是「冻结时点」的快照，不是「当前值」**。它记的是冻结那一刻各输入的样子，因此**之后被合法重建过的产物必然与当前文件不同**——这是快照的设计，不是漂移。
> 实测（2026-10-24）：`outputs/physics_completion/compliance/plan_compliance_meta.json` 在本表里是 `5f826c8ff3d7cb71`，当前实际是 `91822dc2f74d3498`（compliance 随计算每轮重建）。
> **判断"是否漂移"的正确用法**：拿**同一时点**的记录互相比（如与 `preflight.py` 的 `baseline_snapshot.json` 比），**不要用当前文件来"验证"这张表**；若某个**协议/科学输入**（`config/`、`data/metadata/`）的哈希变了，那才是需要审查的漂移。
> 另：本包内文档里的相对路径（如 `tests/test_preflight.py`）一律**按本包目录**解析，**不是仓库根相对**。

| 输入 | sha256[:16] |
|---|---|
| `data/metadata/physics_completion_set.csv` | `f07340d7e203b527` |
| `config/physics_completion_v1.yaml` | `778a18f378bc9574` |
| `outputs/physics_completion/ensembles/production_ensemble_labels.csv` | `822be3b13978227e` |
| `outputs/physics_completion/compliance/plan_compliance_meta.json` | `5f826c8ff3d7cb71` |

冻结协议（未改动）：`wB97X-D4/def2-TZVPD(带电+Li)`、中性用 M_tzvpd、SMD(acetonitrile)、
`Opt VeryTightOpt AnFreq`、4 核；五阈值 `TolE=2e-7 / TolMaxG=3e-5 / TolRMSG=8e-6 /
TolMaxD=2e-4 / TolRMSD=1e-4`。

## 3. 科学状态（严格闸门现算，不是宽松检查器的输出）

- 生产系综：**44 accepted / 4 limited**（分母固定 48，未缩小）。
- **严格闸门 `strict_readiness` 未通过项 = 2**（于 2026-10-23 重写接线后）：
  1. `wp5_full_target_pool_evaluated` —— A/B 池是 **11 / 9** 分子子集，**不是 12 分子全池**；
  2. `execution_cost_provenance_complete` —— 2 条 DEC 腿 `cost_status=incomplete`，
     且成本台账**没有 `cost_scope` 列**，声明只存在于 work/ 侧车，台账无法自证。
- 与之并列的总体缺口：`ensemble_not_48_accepted`（44/48）。
- 因此「唯一缺口是 ensemble_not_48_accepted」的旧说法**已被推翻**。

## 4. 四态失败谱系（当前 4 个 limited 的原因）

| 态 | 路由 | 真实终局 | 再开版本的依据 |
|---|---|---|---|
| `DMC/M_plus` | `unresolved_qc` | 已收敛、0 虚频，未过冻结五阈值（最低实频 76.88 cm⁻¹） | 真实计算次数已尽，**需用户新授权** |
| `DMC/LiM_2plus` | `unresolved_qc` | 同上（74.30 cm⁻¹）；含另立版本 `reopt_v3` 后仍差阈值 | 同上 |
| `DOL/LiM_2plus` | `search_exhausted` | 五元环全刚性（扭转自由度 **0**）、motif 搜索零新独立候选 | 需**环构象探针**新路线（尚未实现） |
| `EC/LiM_2plus` | `search_exhausted` | 两个登记二面角**都穿过 C=O 中心** | 需**合法环/配位自由度**新路线（尚未实现） |

历史尝试与费用**全部保留**（不删除、不改名、不清零）；`n_limited` 从未清空。

## 5. 已用预算

| 项 | 值 |
|---|---|
| 恢复包（strict_recovery_v1 全族） | **187.0 / 600 core-hours** |
| 本轮新批次 | **0**（未提交任何作业） |
| 风险储备 | 300 core-hours，未动用 |

## 6. 超算实时核验（2026-10-23 14:22 +0800，`ssh -i ~/.ssh/id_ed25519_whu`）

命令与**实测原始结果**：

```
$ squeue -u pengqihang -o "%.12i %.30j %.9T %.11M %.5D"
       JOBID                           NAME     STATE        TIME NODES
                                                    <- 仅表头：队列完全空闲

$ sacct -u pengqihang --starttime=now-7days --format=JobID,JobName%28,State,Elapsed -X
3747714_5  wp2-ens-r1  COMPLETED   00:53:57
3747714_6  wp2-ens-r1  COMPLETED   01:26:48
3747714_7  wp2-ens-r1  COMPLETED   01:26:12
3747724_[0-+ wp2-ens-r1 CANCELLED+  00:00:00
3748336_0  wp2-ens-r1  COMPLETED   01:37:48
3749450_0  wp2-ens-r1  COMPLETED   00:13:33
3749450_1  wp2-ens-r1  COMPLETED   01:05:09
3749453_0  wp2-ens-r1  COMPLETED   01:08:21
       <- 近 7 天全部终态（COMPLETED / CANCELLED），无 RUNNING / PENDING

$ sacctmgr -n show assoc where user=pengqihang format=Account,Partition,QOS
pengqihang       hpxg               normal
       <- 授权未变：仍只有 hpxg/normal 一条
```

结论：**无滞留工作、队列空闲、账号授权不变**。
`3747724` 的 `CANCELLED` 元素即历史记录中的批次映射错误，已按红线保留为历史。

## 7. 明确不构成授权的事项

1. **800 core-hours 是否为本轮实际上限** —— 属决策边界，**本轮未动用**。
2. **WP6 与新分子扩样的独立预算** —— 另行决定。
3. **生产级采样容差** —— 继续「只报告差异，不判收敛」，直到独立冻结。
4. 本文件的队列核验**只描述核验时刻**；提交前必须**重新 doctor**。