# P9 · 长期可复现证据归档（Plan action item 9 · 第一轮）

> 会话：公共处理会话（唯一共享生产写入者）｜2026-11-03。本批只读+写入本 evidence 目录；**未做任何 git 提交**（理由见 §2）。

## 1. 归档清单（不自指、逐文件哈希）

`evidence/ARCHIVE_MANIFEST.json`（schema `evidence_archive_manifest/v1`，sha256 见本节末行——由生成命令实测输出，避免清单与本文件互指循环）：

| 项 | 实测 |
|---|---|
| 收录文件 | **91**（排除项=清单自身 + 引用清单的本文件，`excluded=[self, P9_evidence_archive.md]`，清单不自指且无互指循环） |
| 总字节 | 3,522,838 |
| 清单 sha256 | `75fd96b688833a395919f6a9b879ddb0e36d404f0d0a0f6cf5c08acc8b7ae34f`（终值；清单不含本文件，故本文件后续编辑不影响该值） |
| 逐文件 | `sha256` + `bytes` 全量逐条 |
| 范围 | `docs/handoffs/lead_reception_strict_rebuild_20261103/evidence/` 全目录（A1–A5、B1–B4、SUMMARY、BATCH1、P1–P7、P5b 视图、P6 三跑产物、baseline） |
| 获取方式 | 仓库内相对路径直读；无外部 URL、无临时位置 |

校验（逐条对照，非重生成；cwd=仓库根）：

```bash
python -c "
import hashlib,json
from pathlib import Path
root=Path('docs/handoffs/lead_reception_strict_rebuild_20261103/evidence')
man=json.loads((root/'ARCHIVE_MANIFEST.json').read_text(encoding='utf-8'))
bad=[f for f,v in man['files'].items()
     if hashlib.sha256((root/f).read_bytes()).hexdigest()!=v['sha256'] or (root/f).stat().st_size!=v['bytes']]
print('entries=',len(man['files']),'mismatch=',bad)   # 期望 mismatch=[]
"   # exit 0
```

## 2. 纳入版本管理现状（实测 git，未提交）

| 文件 | git 状态 |
|---|---|
| `scripts/wp_production/build_coverage_reviews.py`（P3 修改对象） | TRACKED（改动呈 M，属 61 个并行 M 之一） |
| `scripts/wp_production/submit_hpc_batch.py` / `evidence_gate.py` | TRACKED |
| `scripts/wp_production/rebuild_strict_isolated.py`（P6 修改对象） | UNTRACKED（`??`，本就未跟踪） |
| `tests/test_exclusion_source_completeness.py`（P3 新增） | UNTRACKED |
| `tests/test_dmc_reception_registration.py` | UNTRACKED |
| `evidence/SUMMARY.md` 及全 evidence 目录 | UNTRACKED |
| 当前工作树 | **61 M + 75 ??** |

**不提交原因**：工作树含 61 个并行会话的在途修改，整树提交会把他人工作卷入；按 plan「其他会话的候选只通过交接接收」，提交范围=**Open question 3（归档位置与版本管理边界由谁确认）**。建议提交集（交 Lead 拍板）：本 evidence 目录 + P3/P6 受控改动 + 新增测试，逐文件核对后单独成提交，**禁 `git reset`**。

## 3. 已声明可复现检查（命令+exit code，均为本 session 实测记录；输入未变，按停止规则不重复跑）

| 批次 | 命令 | exit | 结果 |
|---|---|---|---|
| P1-R5 | `python -m pytest work/test_dmc_staged_receiver_v5.py -q` | 1 | 35 过 + 5 败（全 rdkit 缺环境，非逻辑） |
| P1-R1..R4,R6,R7 | `sha256sum`/`grep`/`diff` 钉三轴+签章 | 0 | 见 P1 §6 逐条 |
| P3 | `python -m pytest tests/test_exclusion_source_completeness.py -q` + 消费方 5 文件 | 0 | 22 用例全过 + 消费方 5/5 |
| P4 | `p4_five_state_binding.py --negative-selftest`；正式跑 | 0 | 负测命中拒收；正式 `states=5\|sources=8\|excluded=1` |
| P5 | `tests/test_dmc_reception_registration.py` | 0 | 11 passed |
| P5 | 门套件 5 文件 | 1 | 47 过 + 5 败（全 rdkit 导入期）+ 1 跳 |
| P5b | `admission_state_view.py` | 0 | 五维自检全绿 |
| P6 | `p6_entry.py` 三跑 | 0 | A/B 字节一致、C 规范化全等、三冻结全真 |
| P7 | 3 个守卫测试文件 | 0 | 60 过 + 1 声明跳（attempt_ledger 未建） |
| 终审 | `final_integrity_audit.py`（文档钉住 sha ↔ 活文件 18 对） | 0 | **18/18 全等，mismatches=0** |
| A 线 | `search_evidence` A1–A5 | 见 SUMMARY | A5 提取 `45/2/1` 复算一致 |

## 4. 口径冲突检查（README/交接/正式机器产物，已查范围）

| 口径 | 正式机器源 | 文档声明 | 判定 |
|---|---|---|---|
| 历史状态 45/2/1 | `production_ensemble_labels.csv`（`c21003f5…`，48 行，`acceptance_status`=`accepted:45/limited:2/provisional:1` 实测复算） | `remote_closure README:49`、`closeout.json:21`、`blocker_resolution README:7`、`recovery_decisions_v9 README:3`、`write_recovery_closeout.py:89`、A1 `:133`、BATCH1、P4、P6 | **一致**（grep 全量命中方逐条对照，无矛盾数值） |
| 36 态口径 | 45 accepted − 9 具名 = 36（A5 复算） | `SUMMARY.md:87`（并钉 `48 gap − 9 = 39 ≠ 36` 的排除口径） | 一致 |
| 五态 status | binding `PENDING_INDEPENDENT_COVERAGE_AND_IDENTITY_REVIEW` ×5 | P4/A1/P5b | 一致 |

**未查尽**：站点（site）全量正文与全仓 README 的逐句口径——需在 item 8 发布授权后随发布批 `--check` 一并核（本轮不作「既有整体豁免」，记为随批义务）。

## 5. 外部依赖与无法复现范围（明确声明）

1. **rdkit 缺失**：本机三解释器均无 → P1 receiver 5 例、P5 门套件 5 例**在本环境未证**（导入期失败，非旁路）。
2. **Slurm/sacct 端到端**：`submit_hpc_batch` 实际提交与 terminal sacct 结算需真实集群，本机不可重放（不自动申请计算）。
3. **`work/wp2prod` 等 gitignored 原始层**：git 忽略的原始证据以 `work/*` 就地留存，持久归档位置=**Open question 3**；本地存在≠永久可获取（本清单只收 evidence 目录内证据）。
4. **未重建对象**：site/正式产物重建属 item 8，待发布授权。

## 6. 发布了什么 / 如何恢复

- **正式发布 = 零**；本批新增仅 `ARCHIVE_MANIFEST.json` + 本文件，均在 evidence 目录内。
- 恢复：`rm evidence/ARCHIVE_MANIFEST.json evidence/P9_evidence_archive.md` 即回到本批前；无生产文件改动。
