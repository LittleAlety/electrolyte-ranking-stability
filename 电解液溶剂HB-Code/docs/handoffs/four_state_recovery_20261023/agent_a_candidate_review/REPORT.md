# Agent A：P4 筛选包候选合法性独立复核（Lead 接手完成）

## 0. 交付状态（如实记录）
- 承担本任务的 subagent（`11163fa0-8d1b-4eec-b4c9-ea6638c1ae10`）在写本报告前**失败退出，无收尾消息**。
- 它实际留下的产物只有 `review.py`（70,803 B）。该脚本**可运行且完整输出**，Lead 已独立复跑：
  `review.py` → **69 项检查 / 66 通过 / 3 不符 / 0 无法复现**，退出码 1（脚本以"有重要观察"为退出码 1）。
- 因此本文件由 **Lead** 在 A 的中断点之后补齐，并对 A 的每一条数字**另用独立代码路径复算**（见 §3）。
- **没有 A 的原始中间步骤可引用**：本报告只承认可复现的实测值。

## 1. 被审对象（冻结输入，全部只读）
| 输入 | 路径 |
|---|---|
| P4 包清单 | `work/hpc_four_state_p4_xtb_screening_v1/manifest.json` |
| 尝试账本 | `work/hpc_four_state_p4_xtb_screening_v1/attempts_ledger.json` |
| 选择锁 | `work/hpc_four_state_p4_xtb_screening_v1/selection.lock.json` |
| 根哈希清单 | `work/hpc_four_state_p4_xtb_screening_v1/PACKAGE_SHA256SUMS` |
| 逐任务目录 | `work/hpc_four_state_p4_xtb_screening_v1/tasks/<state>/<candidate>/`（`geom.xyz`/`job.inp`/`cores.txt`/`candidate.json`/`inputs.sha256`） |
| 权威电子身份 | `outputs/physics_completion/free_states/production_ledger.csv` |
| 扭转自由度登记 | `outputs/physics_completion/recovery/torsion_freedom_registry.csv` |
| 生成器（只读参考） | `scripts/wp_production/build_torsion_probe_package.py` |

## 2. Lead 自己的独立审计（另一条代码路径，`work/_p4_audit.py`）
**293 项检查全绿**，覆盖：manifest 不变量（`xtb_screening_v1`、`cores_per_task=2`、`budget_cap_core_hours=32`、`task_count=8`、单数组 `0-7%2`、`submission_gate=HOLD`、`submitted=false`、gate 契约 `validate_candidate_start_v2`）、8 条 attempts（全 `planned`、`stage=xtb_screening`、cores=2、wall=2、`8×2×2=32`）、每任务 5 文件、`inputs.sha256` 自洽、根清单**闭包**（除自身外不多列不漏列，46 行）、`geom.xyz` 哈希与 `candidate_geometry_sha256` 一致、`job.inp` 无 `%pal`、`cores.txt==2`、`candidate.json` 与 manifest 八字段一致。

### 身份表（实测，逐任务）
| state_key | mol_id | record_id | charge | multiplicity | spin | job.inp |
|---|---|---|---|---|---|---|
| DMC\|LiM_2plus ×2 | C01 | C01\|LiM_2plus | 2 | 2 | 1 | `$chrg 2` / `$spin 1` |
| DMC\|M_plus ×2 | C01 | C01\|M_plus | 1 | 2 | 1 | `$chrg 1` / `$spin 1` |
| DOL\|LiM_2plus ×2 | C09 | C09\|LiM_2plus | 2 | 2 | 1 | `$chrg 2` / `$spin 1` |
| EC\|LiM_2plus ×2 | C04 | C04\|LiM_2plus | 2 | 2 | 1 | `$chrg 2` / `$spin 1` |

三个 `LiM_2plus` 的 `charge=2 / multiplicity=2 / spin=1` **全部与权威账本一致**；`mol_id`（分子号）与 `record_id`（态号）在正式 manifest 里**已分离**，P3 历史 JSON 把 `record_id` 塞进 `mol_id` 的问题不再存在。

## 3. 三条「不符」（均为 Important，且**不构成冻结契约违反**）

Lead 在新代码路径（`work/_p4_geom_check.py`，直接解析冻结几何，未复用 A 的 `review.py`）上复算，**逐位吻合**：

### C9.7 轴键长的「单键性」被削弱
| 任务 | 轴原子对 | 结果几何键长 | Pauling 参考键级 n=exp((1.43−R)/0.37) |
|---|---|---|---|
| DMC\|LiM_2plus / p4_01_torsion_tors_0_1_2_3 | (1,2) | **1.273271 Å** | 1.53 |
| DMC\|M_plus / p4_01_torsion_tors_0_1_2_3 | (1,2) | **1.284952 Å** | 1.48 |
| DMC\|M_plus / p4_02_torsion_tors_1_2_4_5 | (2,4) | 1.472089 Å | 0.89 |

前两条的旋转轴在**带电态几何里已带明显双键性质**（典型 C–O 单键 1.43 Å）。被审生成器的"单键证据"来自上游 registry（中性分子键级拓扑），在阳离子态被削弱 → 「自由旋转自由度」的前提对这两条候选不成立。
**注**：这不违反生成器的冻结契约（契约只认 registry 登记），但**属于与 EC「排除 C=O 假扭转」同类的科学风险**，需要在提交前显式裁决。

### C11.5 「改壳层」与「只挪 Li」被区分
| 任务 | Li 索引 | O 壳(≤2.6 Å) before → after | 判定 |
|---|---|---|---|
| DMC\|LiM_2plus / p4_02_li_coordination_toward_3 | 12 | [3] → O 壳不变；但 C2 由 3.0222 → **2.5828 Å** 进入 2.6 Å 截距 | **改壳层** |
| DOL\|LiM_2plus / p4_01_li_coordination_toward_4 | 11 | [4] → [4]，唯一给体 2.0830 → **1.6330 Å** | 只挪 Li |
| EC\|LiM_2plus / p4_01_li_coordination_toward_4 | 10 | [4] → [4]，唯一给体 1.9028 → **1.4528 Å** | 只挪 Li |

这与**上游预注册**（探针类 B：「0.15 Å 位移若不改变壳层成员则仍可作为普通 Li 位移被接受——即『改壳层』与『只挪 Li』是两个不同事实，不得混同」）**一致**；仅与审查任务的口头措辞（"成员改变与声明一致"）不一致。**不属契约违反。**

### C11.7 位移后 Li–给体接触距离的物理合理性
| 任务 | 位移后 Li–声明给体 | 位移前 | 判定 |
|---|---|---|---|
| DMC\|LiM_2plus / p4_02_li_coordination_toward_3 | **1.4768 Å** | 1.9268 Å | 远短于 Li⁺–O 常见 1.9–2.1 Å |
| EC\|LiM_2plus / p4_01_li_coordination_toward_4 | **1.4528 Å** | 1.9028 Å | 远短于常见值 |
| DOL\|LiM_2plus / p4_01_li_coordination_toward_4 | 1.6330 Å | 2.0830 Å | 偏短 |

冻结的 offset 集合 {0.15, 0.30, 0.45} Å **未设最小接触距离护栏**；对给体原本就短的态（EC 1.9028 Å），+0.45 Å 把 Li 推到 1.4528 Å 的强重叠区。**GFN2 优化很可能直接弛豫回源极小** → 该筛选元素可能拿不到独立盆地证据。这是**成本有效性**风险（32 core-hours 里至少 2 个元素命中概率下降），不是身份/合法性违规。

## 4. 需要用户裁决的具体门（提交前）
1. **是否接受 DMC 两态的 `tors_0_1_2_3` 作为合法自由旋转**：若按 EC 口径（排除 C=O 假扭转）从严处理，这条候选应被撤下或以"轴键级"为附加证据重新登记；若维持 registry 口径，则保留但须在结果报告里注明"轴已非纯单键"。
2. **是否对 Li 位移加最小接触距离护栏**：若加，则 EC 的 `toward_4`（1.4528 Å）与 DMC|LiM_2plus 的 `toward_3`(1.4768 Å) 需改 offset 或改方向——这会改动冻结的 P4 plan，**必须由用户批准**。

以上两项**均属改动冻结 P4 计划**，Lead 不自行修改。

## 5. 本报告未覆盖的范围
- 未运行任何 ORCA/xTB 计算；未上传、未提交任何作业。
- 未复核 GFN2 筛选层之后的分流（那需要真实 Slurm 结果）。
- `review.py` 的 69 项检查里，Lead 只对 §3 的 3 条与 §2 的身份/哈希类做了独立复算；其余检查项**未全部独立重写**（但 `work/_p4_audit.py` 与 `review.py` 是两条独立代码路径，二者在重叠面上结论一致）。