# `scripts/wp_production/` —— physics_completion_v1 批次（WP0–WP6）的生产流水线

这里放的是**生成已提交交付物的那套脚本**。它们原先散落在未跟踪的 `work/pilot12/`，
导致「仓库里的 `outputs/physics_completion/**` 到底怎么来的」在仓库内无法复现；
迁移到 `scripts/` 后，交付物与生成器同处一个被跟踪的命名空间。

## 一键收口

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\wp_production\finalize_wp2.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\wp_production\finalize_wp2.ps1 -Commit
```

顺序：`anchors` → `emit-wp2` → `generator` → `closure` → `figures` → `mirror` →
`site` → `freeze` → `clean-room` → 五个 `--check` → `pytest`。任一非零即 `ABORT`，不提交。

## 各脚本职责

| 脚本 | 职责 |
| --- | --- |
| `check_wp2_anchors.py` | 复核 `emit_wp2.py` 的补丁锚点在当前生成器基线里唯一存在 |
| `emit_wp2.py` | 把 `work/wp2prod/**` 已跑完的状态折进生成器：重打 `WP2_PRODUCTION_LEDGER` 等补丁块 |
| `run_batch.py` | 12 主集分子 × 4 主态的 xTB/ORCA 批量驱动与公共工具（几何、ORCA/xTB 路径、片段分析） |
| `run_wp2_production.py` | 生产级 Opt+NumFreq 驱动（`M` / `M_plus` / `LiM_plus` / `LiM_2plus`） |
| `run_wp2_extra.py` | 与带电腿**基组一致**的中性腿 `M_tzvpd`（def2-TZVPD）驱动 |
| `emit_wp1.py` + `wp1_audit_src.txt` | 把 WP1 方法审计矩阵折进生成器 |
| `run_method_audit.py` | WP1 的 128 单点 / 32 弛豫腿本机方法审计驱动 |
| `make_commit_msg.py` | 按当前已落地子集生成提交信息（写 `work/_wp2_commit_msg.txt`） |
| `finalize_wp2.ps1` | 上面那条一键收口链 |

## 边界

* **原始 ORCA/xTB 输出不入库**：留在仓库外 `work/`（生产为 `work/wp2prod/`，审计为 `work/audit/`）。
  交付镜像里只有派生的 CSV/JSON；派生数值与原始日志的对应关系见
  `outputs/physics_completion/provenance/job_archive_manifest.csv`。
* **生成器是派生物**：`scripts/build_physics_completion_batch.py` 由 `emit_wp2.py` 从
  「最近的未打补丁基线 + 补丁块」确定性重打；手工改它会失效。基线缓存在 `work/pilot12/gen_baseline.py`。
* **零新增电子结构**：除 WP1/WP2 两段显式登记的本机作业外，收口链不引入任何新的电子结构计算。