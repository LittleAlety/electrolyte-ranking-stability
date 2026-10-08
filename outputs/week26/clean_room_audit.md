# Clean-room 复现审计（R14）

> 由 `scripts/audit_clean_room.py` 生成：官方离线静态审计，不跑新电子结构、不联网。

**定义**：Static, offline audit of what a fresh clone can reproduce without the local ORCA/xTB install and without the out-of-repo delivery layer.

**裁决**：**OK**

| 检查 | 级别 | 项目 | 详情 |
| --- | --- | --- | --- |
| C1 | PASS | in-repo reproducibility surface | 12/12 top-level entries present |
| C2 | PASS | verification entry points | 7/7 present |
| C3 | INFO | scripts reaching outside the repository | 6 script(s) reference the out-of-repo delivery layer (the auditor itself is excluded by construction); none of them is a verification entry point. analyze_w24_alignment.py; analyze_w24_audit.py; analyze_w24_decision.py; build_compute_budget_ledger.py; build_week25_deliverables.py; scan_stage15_anchor_literature.py |
| C4 | PASS | tests never reach outside the repository | 0 references |
| C5 | INFO | external binaries are optional for verification | no verification entry point needs ORCA or xTB; they are required only for NEW electronic structure. Their presence is printed to stdout, not written into this report, so the report stays machine-independent and --check works in a clean clone. |
| C6 | PASS | frozen manifests recompute | 7480/7480 rows match; broken: none |
| C7 | PASS | close-out documents match the products | README Scope + NOT CLOSABLE present; FINAL_CONCLUSIONS.md answers 10 questions |

## 冻结清单复算

| manifest | 行数 | 匹配 | 不匹配 | 缺文件 |
| --- | --- | --- | --- | --- |
| `outputs/week1/SHA256SUMS` | 6 | 6 | 0 | 0 |
| `outputs/week2/SHA256SUMS` | 30 | 30 | 0 | 0 |
| `outputs/week3/SHA256SUMS` | 7444 | 7444 | 0 | 0 |

## 仓库外依赖（非验证路径）

以下脚本会读 / 写仓库外的交付层（`..\成果输出\`、`..\核心文件\`、`..\论文\`），它们**不是** README 里的验证入口：

- `scripts/analyze_w24_alignment.py`（3 处）
- `scripts/analyze_w24_audit.py`（4 处）
- `scripts/analyze_w24_decision.py`（1 处）
- `scripts/build_compute_budget_ledger.py`（1 处）
- `scripts/build_week25_deliverables.py`（1 处）
- `scripts/scan_stage15_anchor_literature.py`（1 处）

## 纪律声明

- 本审计只读本仓库；未跑新电子结构，未访问网络，未修改任何冻结产物。
- 本机的 ORCA / xTB 安装目录只影响**新增**电子结构计算，不影响本仓库任何 `--check`、manifest 复算或测试。

