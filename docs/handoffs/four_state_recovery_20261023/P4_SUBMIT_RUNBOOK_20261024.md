# P4 筛选轮提交运行手册（2026-10-24 离线准备；**提交仍停在授权门**）

本文件只记录**离线已核验**的步骤与命令。**它本身不构成提交授权**：`manifest.json` 与
`selection.lock.json` 仍为 `submission_gate=HOLD`、`submitted=false`。

## 0. 当前冻结事实（实测）
| 项 | 值 |
|---|---|
| 包路径 | `work/hpc_four_state_p4_xtb_screening_v1/`（47 文件 / 8 任务 / 5 文件每任务） |
| 资源协议 | `xtb_screening_v1` = engine `xtb`、2 核、2 h、cap **32** core-hours、**要求 attempts ledger** |
| 数组 | 单数组 `--array=0-7%2`（最多 2 并发） |
| 预算不变量（真实账本） | committed=`0` + reserved=`32` = cap=`32`，剩余 `0` |
| 身份 | 三个 `LiM_2plus` 均 `charge=2/mult=2/spin=1`（`$chrg 2`/`$spin 1`）；`DMC|M_plus` 为 `$chrg 1` |
| 核数声明 | 每任务 `cores.txt` = `2` == allocation 2 |
| 脚本规范 | `batch_1.sbatch`/`batch_1.txt`/`tasks.txt` 均 **无 BOM + 纯 LF** |
| 索引映射 | `manifest.tasks` 顺序 == `batch_1.txt` 行序（`sed -n "$((SLURM_ARRAY_TASK_ID+1))p"`） |
| 离线模拟提交 | 17/17 通过，**bridge 调用尝试 = 0**（`work/_p4_mock_submit.py`） |

## 1. 授权到手后的固定顺序（不得跳步）
1. 阅读 `E:\软件\超算连接\AGENTS.md`（命令桥规程）。
2. `hpc.ps1 doctor` —— 未通过即**停止远端操作**，不得绕过命令桥。
3. 经命令桥**上传**包，远端**逐文件**核对根 `PACKAGE_SHA256SUMS`。
4. 查真实 `squeue`：确认本账户 `running+pending ≤ 20`、无同身份任务已在跑。
5. 调用受保护提交器（**唯一入口**，外层脚本不得绕过预算门）：

   ```powershell
   .\.venv\Scripts\python.exe scripts\wp_production\submit_hpc_batch.py `
     work\hpc_four_state_p4_xtb_screening_v1 `
     --batch 1 `
     --remote-workdir ~/project/electrolyte_wp2/p4_xtb_screening_v1 `
     --attempts-ledger work\hpc_four_state_p4_xtb_screening_v1\attempts_ledger.json
   ```

   - `--budget-cap-core-hours` 只作一致性断言（必须等于 `32`），**不能放宽 profile**。
   - 缺 `--attempts-ledger` 时 xtb profile **在 doctor 之前即拒收**（已实测）。
6. 提交成功后**立刻**登记：数组 JobID、8 个元素→任务映射、`submission_journal.json`。
7. **响应不明时先查 `squeue/sacct`，绝不重复提交**（journal + reservation 双保险会拒绝重复；已实测）。

## 2. 边界（红线）
- ORCA/xTB/GFN2 **只在 Slurm 计算节点**运行；登录节点严禁计算。
- 提交侧仍有三步**从未执行**（也因此从未触网）：`doctor`、账户级远端提交锁、实时 `squeue` 余量。
- 800 core-hours 是**建议上限、不是已授权余额**；筛选层上限为 32。
- 本包 8 个任务的科内容与「重建前后」逐字节一致（仅 `generator_sha256` 及根清单中该行变化）。

## 3. 提交前仍需用户裁决的两道科学门
1. **DMC 两态 `tors_0_1_2_3` 轴的单键性**：实测轴键长 `DMC|LiM_2plus`=**1.2733 Å**、
   `DMC|M_plus`=**1.2850 Å**（典型 C–O 单键 1.43 Å，Pauling 键级≈1.5）；registry 的单键证据
   来自**中性**拓扑，在阳离子态被削弱 —— 与 EC「排除 C=O 假扭转」同类。
   维持 registry 口径（保留但注明）／从严撤下或重新登记，需裁决。
2. **Li 位移的最小接触护栏**：冻结 offset {0.15,0.30,0.45} Å 无下界，实测
   `EC|LiM_2plus/toward_4` 被推到 Li–O **1.4528 Å**、`DMC|LiM_2plus/toward_3` 到 **1.4768 Å**
   （Li⁺–O 常见 1.9–2.1 Å）。这两个元素很可能直接弛豫回源极小 → 属成本有效性问题。

## 4. 明令禁止（已实测其在结构上不可被链调用，但执行者仍可能手 run）
- **禁止运行 `work/_p3_run.py` 与 `work/_p4_screen_plan.py`**：它们是旧 scratch 生成器，
  会用**错误的电子身份与资源配置**覆盖正式结果（历史字段曾把 `record_id` 塞进 `mol_id`、
  三个 `LiM_2plus` 曾错成 `1/1`）。实测：在 `scripts/`、`tests/` 与交接文档中
  **引用数 = 0**，即收口链与测试**不会**调用它们，危险只来自手 run。
- 生成与只读复核**只用**：`build_torsion_probe_package.py --build-p4-screening` /
  `--check-p4-screening`。

## 5. 授权后回收阶段的对应阶段
提交 → 回收（`ensemble_hpc_io.py`，幂等）→ 逐元素收终态/`xtbopt.log`/`stderr.log`/`xtbopt.xyz`/
启动终止时间/实测成本 → 按冻结 **6 kcal/mol** 窗筛选 → 四态分流（新盆地／回已知盆地／身份漂移／
八条均无新盆地）→ 有界生产计算（每态 ≤2 起点 + ≤1 有因补救）→ 逐腿六项验收。