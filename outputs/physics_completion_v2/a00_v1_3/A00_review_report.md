# A00-v1.3 审查报告：本地证据冻结、跨代对账与 72 态注册表修订

> **状态：`A00_HOLD`** — 审计材料已交付且 12 项自动审核中 11 项通过，但仍有 **1 项代际冲突**和
> **7 条主张等待人类裁决**。按授权规则，这些未裁决项禁止当作新论文发现使用。
>
> 生成器：`scripts/v2/a00_audit.py`（`a00_v1_3/1.0.0`）· 输出目录：
> `outputs/physics_completion_v2/a00_v1_3/` · 契约测试：`tests/test_a00_v1_3_contract.py`
>
> **本次只做只读审计。未提交任何 HPC 作业、未启动任何 ORCA/xTB 计算、未覆盖任何冻结产物、
> 未删除任何历史记录、未重置分支、未 push。**

---

## 0. 一句话结论

计划 v1.2 对第一仓库的骨架判断是对的，但它审计的是 **2026-11-07 的公开推送**；本地真实状态是
一个 **2026-11-16—11-22 的 18×4 closure 周期**。A00 把这两者放到同一张表上之后，得到的不是
"计划有错"，而是 **三个不同代际的同一组数字同时在仓库里生效**。全部 72 个位置在执行轴上已经完成，
真正的缺口是 **系综轴**（27/72 缺系综），而不是计划假设的"24 态还没开始"。

---

## 1. 八份交付物及其可校验入口

| 交付物 | 内容 | 校验方式 |
|---|---|---|
| `repo_snapshot.json` | git 三分叉、四类工作树文件、work/ 证据索引、已知冲突 | `git.working_tree`、`evidence_inventory.summary` |
| `core18_v2_state_registry.csv` | 72 行 canonical 位置，保留 A1–A5 五轴 | `A00-01` / `A00-02` / `A00-06` 审核 |
| `science_claim_correction_matrix.csv` | 26 条旧结论→新证据→裁决 | `A00-07` 逐条 hash 复核 |
| `authorization_record.json` | 本次授权边界与预算状态 | `A00-10` 审核 |
| `v1_v2_baseline_reconciliation.csv` | 22 行逐来源数值对账 | `A00-07` |
| `A00_validation.json` | 11 项自动审核 + 1 项回归测试 | `python scripts/v2/a00_audit.py validate` |
| `A00_evidence_manifest.csv` | 9,749 文件级 SHA256 + 目录级聚合摘要 | `A00-11` |
| `A00_review_report.md` | 本文件 | — |

复现：

```powershell
python scripts/v2/a00_audit.py all          # 重建 + 验证
python scripts/v2/a00_audit.py determinism  # 二次构建字节一致性
python -m pytest tests/test_a00_v1_3_contract.py -q
```

---

## 2. 自动审核结果

| ID | 检查项 | 结果 |
|---|---|---|
| A00-01 | 72 个 canonical key 完整且唯一 | **PASS** |
| A00-02 | 60 历史腿 → 48 canonical 位置映射 | **PASS** |
| A00-03 | extension pool 6 + 5 角色过滤 | **PASS** |
| A00-04 | CSV 与 summary 同代，或显式标记 stale | **HOLD**（设计如此，见 §3.1） |
| A00-05 | 从权威账本逐行复算 45/2/1 | **PASS** |
| A00-06 | 24 扩展态执行与系综分别计数 | **PASS** |
| A00-07 | 每条关键结论有真实可校验来源 | **PASS** |
| A00-08 | 无静默覆盖/凭空补缺/历史回写 | **PASS** |
| A00-09 | 工作树四类分类 | **PASS** |
| A00-10 | 授权记录与授予范围一致 | **PASS** |
| A00-11 | 证据清单自一致 | **PASS** |
| A00-12 | 审计来源自建库以来未被改动 | **PASS**（并作为并发写入守卫保留） |
| REG-01 | 旧 summary 4 NOT_STARTED vs 新 CSV 24/24 | **FIRED_AS_DESIGNED** |

契约测试：`tests/test_a00_v1_3_contract.py` **19 项全部通过**
（`A00_pytest.xml`，junit `tests="19" failures="0"`）。

`determinism`：文档级 `DETERMINISTIC`（5 份交付物二次构建零差异）；证据树聚合值有漂移，
原因见 §3.6。

---

## 3. 六个必须由人裁决的证据冲突

### 3.1 同一组数字有三个代际，其中两个在同一个文件里互相矛盾

| 代际 | 出处 | 写入时间 | extension6 执行 | A5 系综 |
|---|---|---|---|---|
| G1 | `EVIDENCE_MATRIX_18x4_summary.json` | 2026-11-17 20:51 | 20 完成 / **4 未开始** | 45 / 26+1 |
| G2 | `FINAL_VERDICT.json#matrix_18x4_current` 与 `#matrix_integrity_after_rebuild` | 2026-11-22 17:45 | **4 未开始** | 45 / 26 / 1 |
| G3 | `EVIDENCE_MATRIX_18x4.csv` + `FINAL_VERDICT.json#evidence_matrix_after_tegdme` | 2026-11-22 17:10 / 17:45 | **24/24 完成** | 45 / 27 / 0 |

`FINAL_VERDICT.json` **同一个文件**里同时存在 G2 和 G3 两套互斥的计数。G1 的 summary 比它
所描述的 CSV 早 5 天且从未重生成。

**需要决定**：G3 是否就是当前权威？（A00 的立场是"两个来源一致才采信"，而 G3 有 CSV 与
verdict 双源一致，因此注册表按 G3 构建，同时把 G1/G2 记为 `STALE_SUMMARY`。）

### 3.2 DMC 两态的失败分类：`sampling_limited` 还是 `E_single_screened_QC_failed`？

- 冻结表 `production_ensemble_labels.csv`：`sampling_limited` + `rescue_budget_exhausted`
- `FINAL_VERDICT.json#e_class_all_closed`：候选构象 QC 失败 **且** 与已保留成员几何重复
  （RMSD 0.035–0.048 Å），"用现有起始材料无法闭合"
- 计划 A04：把它当成"数值验收"问题，要求走几何五阈值逐条判定

三个说法指向三种不同的补救动作。报告里的实际失败是 VeryTightOpt 收敛判据
（`energy_change 4.344e-07 > 2e-07`）与 `max_cycles_exhausted`——这是**优化收敛 QC**，
不是几何五阈值，也不是"预算不够所以没搜"。

**需要决定**：72 行处置表采用哪一套 taxonomy。在决定之前 **A04 不得开新的救援计算臂**。

### 3.3 `ROBUST_INVERSION`：0 还是 2？

- 仓库里唯一的冻结 pair 表 `pair_evidence.csv`：**2**（STABLE 55 / UNRESOLVED 9 / 共 66 对，单 σ 列）
- 计划 v1.2 §0.1：**0**，并限定为"双来源 sigma"

工作树里不存在任何双来源 σ 的产物。因此 0 与 2 不是矛盾，而是**两个未命名的估计量**。

**需要决定**：要么给出双来源 σ 的估计量定义与输入表，要么撤回 0 这个数字。

### 3.4 协议洁净子集：7 个分子，还是全部 48 腿？

`README.md`（2026-11-22 17:28）仍按 matrix **v2** 表述："协议干净的是 7 个分子，
第 3–4 名间隔 4.84 kcal/mol"。而 `EVIDENCE_MATRIX_18x4_summary.json` 的 schema 是
`v3_geometry_authoritative`，其 note 明确写道 v2 的 `PROTOCOL_DEVIATION/LABEL` 是
"不完整候选池造成的假象"，v3 下 60 条主线腿全部是生产级 SMD Opt 驻点。

**需要决定**：4.84 kcal/mol 与"7 个洁净分子"这个结论要么在 v3 下重新推导，要么明确标为已被取代。
在此之前**不得引用**这两个数。

### 3.5 45/2/1 与 A5 的 45/27 是同一次晋升的两个投影，不是两个结果

| 口径 | 分母 | 未接受 |
|---|---|---|
| 冻结表 `acceptance_status` | 48（仅主集 12 分子） | 2 limited + 1 provisional |
| matrix `A5_sampling_ensemble` | 72（含扩展 6 分子） | 3 主集 + 24 扩展 = 27 |

两者对主集完全一致（3 个非接受位置相同），差别只在分母和**扩展分子从不在系综表里**。
注册表把 `C04|LiM_2plus` 的 `provisional` 原样保留在 `ensemble_label_status` 列，
同时在 A5 轴记为 `MISSING_EVIDENCE`，两列并存不互相覆盖。

**需要决定**：论文里引用哪一个口径时必须明写分母；任何一个数都不许只写"27/72"或"45/48"了事。

### 3.6 `work/` 不是静态的——审计期间有并发写入，而且是**写我们正在冻结的那批文件**

本次审计期间观察到两次并发写入：

| 时间 | 位置 | 内容 |
|---|---|---|
| 19:02–19:03 | `work/research_completion_20261119/B_replay/` | 5 个文件被重写，含 `_rerun_check.log` = `CHECK OK -- knn_v1 A/B replay tables match recomputation` |
| 19:22:22–23 | `work/evidence18_strict_closure_20261116_codex/` | **整个 closure 包被重新生成**：`FINAL_VERDICT.json`、`CLAIM_LEDGER.csv`、`FINAL_CONCLUSIONS_20261117.md`、`COMPLIANCE_CHECK.csv`、`CROSSDOC_CONSISTENCY.csv`、`INVENTORY_CHECK.csv` 等 |

也就是说：**本会话进行期间，另一个进程或会话正在同一个工作树里跑 WP5 replay 审计，并重新生成我正在冻结的 closure 权威文件。**

应对：

- `A00-12` 是为此新增的守卫：构建完成后如果任何被引用的来源文件字节改变，直接 `HOLD` 并报
  `SOURCE_MUTATED_DURING_AUDIT`，不允许交付一个"在移动靶上打出的快照"。
- `determinism` 的文档级比较仍是 `DETERMINISTIC`（5 份交付物二次构建零差异），
  但证据树聚合值按设计会漂移，已单独登记为 `live_tree_diffs`。
- 交付时点的一致性已复核：`EVIDENCE_MATRIX_18x4.csv` 与 `FINAL_VERDICT.json` 的当前 sha256
  与注册表/主张矩阵记录的完全一致（见 `A00-12`）。

**需要决定**：A12 只读发布前必须在**静止**工作树上重取一次快照，并声明取数窗口；
在此之前本交付的定位是"某一时刻的可审计读数"，不是"可发布的最终冻结"。

---

## 4. 计划 v1.2 需要就地改写的四处

| 位置 | 现文 | 应改为 |
|---|---|---|
| §0.1 | 严格系综 44 accepted / 4 limited | **45 / 2 / 1**（分母 48） |
| §0.1 + A04 | 四个 limited：DMC×2、DOL、EC | **2 limited（DMC×2）+ 1 provisional（EC）**；`DOL\|LiM_2plus` 已由 coverage review 放行，历史 `n_limited=1` 保留 |
| §0.1 | 新增六分子 24 态"不是已实际跑完的 24 态" | 执行轴 **24/24 COMPLETED**（A1），缺的是**系综轴 24/24 MISSING_EVIDENCE** |
| A04 | DMC 走几何五阈值逐条判定 | 先裁定 §3.2 的 taxonomy；收敛 QC、几何五阈值、系综缺失是三个独立判据 |

另有两处不是错误但需要点明：

- **A05/A06 的起点要重排**：A05 的六分子化学筛查、A06 的 24 态生产在本地已经完成（见 §5），
  按"0 起步"排期会至少白排 6 周。省下来的窗口应该给系综补齐。
- **§1.1 的 [E] 清单经核实全部真实存在**，包括 `scripts/production/analysis/build_anchor_condition_audit.py`。
  `scripts/wp_production/` 下的 103 个同名文件是 `build_script_index.py --emit-shims` 生成的
  HISTORICAL_ENTRY 兼容壳（每个都在模块 docstring 里声明"实现已迁移"），不是第二套实现。
  这条判断计划是对的；但 v2 新脚本必须 import `scripts/production/...` 而不是兼容壳路径。

---

## 5. 72 态登记表读出来的真实图景

```
72 个位置
├─ 执行轴 A1  COMPLETED            72/72   （主集 48 + 扩展 24）
├─ 数值轴 A2  VERIFIED             72/72
├─ 目标物种 A3  VERIFIED 71 / FAILED 1   （MA|LiM_2plus 解离端点，有意保留的缺口）
├─ 身份协议 A4  PROTOCOL_CLEAN 48 + CLEAN_VERYTIGHTOPT 24 = 72/72
└─ 系综轴 A5  accepted 45 / 缺失 27      ← 唯一的真实缺口
```

27 个系综缺口分成两类，**不能合并报告**：

- **3 个主集位置**（`C01|M_plus`、`C01|LiM_2plus`、`C04|LiM_2plus`）：搜过了，候选 QC 失败
  且是几何重复，用现有材料闭合不了。
- **24 个扩展位置**：单构象点有了，但**从来没进过系综候选池**。

注册表的每条位置都带 `registry_disposition`、`open_gap_classes`、`missing_reason`；
`AUDIT_OPEN_*` 的行不允许 `missing_reason` 为空（`A00-08` 强制）。

---

## 6. 顺带发现的两个硬问题

### 6.1 54 个已提交的证据文件在工作树上被删除了（C26）

`commit 06fca61`（2026-11-07，"Archive reviewed coverage v4 candidate and bounded replay evidence"）
把 `work/coverage_fix_20261106/` 和 `work/coverage_review_20261106/` 强制加入了 git；现在这些
路径在工作树上是 `D` 状态，**磁盘上没有字节**。工作树共 54 个删除项：其中 53 个属于上述两个
coverage 目录，第 54 个是 `scripts/wp_production/wp1_audit_src.txt`。

字节可以从 HEAD 恢复，但任何读它们的脚本现在都会失败。A12 要在"干净检出 + 可复现"的前提下发布，
这条必须先解决：要么 `git restore` 恢复，要么出一份书面退役决定。

### 6.2 20 个位置的电荷/多重度在权威矩阵里是空的（C22）

`FEC / VC / EA / MA / SN × 4 态 = 20 行` 的 `charge_multiplicity` 单元为空；
其余 52 行有值且**全部符合** canonical 映射（M 0/1、M_plus 1/2、LiM_plus 1/1、LiM_2plus 2/2），
只是格式不统一（`1/2` 与 `+1/2` 混用）。

注册表没有替它们"顺手补上"：`expected_charge/expected_multiplicity` 是定义值，
`observed_*` 留空并记 `charge_mult_consistent = not_evaluated`，`open_gap_classes` 带
`charge_multiplicity_absent_in_source`。这是 §"不存在凭空补缺"的字面执行。

---

## 7. 关于 `M_tzvpd` 的登记方式（注册表最容易被搞错的一处）

`production_ledger.csv` 有 60 条腿 = 12 分子 × **5** 个状态标签，而冻结协议
`production_method_freeze_v1.json` 的 `basis_by_state` 规定四态全为 `def2-TZVPD`。

真实情况是：中性腿跑过两次。原始 `M` 行 basis 是 `def2-TZVP`；为满足冻结的靶基组规则，
中性腿以 `M_tzvpd` 重跑。所以：

- **`M_tzvpd` 不是第五个电子态**，它是 canonical 中性态 `M` 的生产级腿。
- 60 腿 → 48 canonical 位置：`M` 与 `M_tzvpd` 折叠成同一个位置。
- 任何"从 ledger 机械生成 72 行"的实现都会得到 **84 行或 60 行，永远不是 72 行**（C25）。

注册表用 `neutral_leg_key = M_tzvpd` + `legacy_ledger_legs = 2` 显式记录这件事，
`A00-02` 强制 60 腿全部被消费、且 48 个主集位置无一无腿。

---

## 8. 提请注意：本环境的一次写入权限故障

A00 首次运行无法在仓库内创建目录（`WinError 5`，仓库根也同样被拒，`%TEMP%` 正常）。
检查发现 `outputs/` 只有从 `Authenticated Users` 继承的 Modify，没有当前用户自己的完全控制项；
按 `diagnose-windows-sandbox-acl` 的流程对 `E:\Claude Code\电解液溶剂-HB\电解液溶剂HB-Code\outputs`
做了一次授权内的诊断/修复（备份：`E:\Claude Code\acl-recovery-a00\acl-backup-fcf71138897c4e52ada94325ea30fa36.json`，
回滚脚本同名 `.ps1`）。之后本次会话的文件策略切换为 `danger-full-access`，写入正常。

不改动任何文件内容与所有者；若需还原权限，见上述回滚脚本。

---

## 9. 九条补救任务（人裁决后才能关闭 A00）

| ID | 责任 | 任务 |
|---|---|---|
| REM-01 | 作者 | 从 CSV 重新生成 `EVIDENCE_MATRIX_18x4_summary.json` 并记录取代关系，然后重跑 `A00-04` |
| REM-02 | 作者 | 退休或重写 `FINAL_VERDICT.json` 的 `matrix_18x4_current` / `matrix_integrity_after_rebuild`，一个文件不许带两套计数 |
| REM-03 | 作者 | 计划 v1.2 的 44/4 与四受限态枚举改写为 45/2/1 + 2 limited + 1 provisional |
| REM-04 | 科学家 | 裁定 DMC 缺口 taxonomy（§3.2）；裁定前 A04 不开新救援臂 |
| REM-05 | 科学家 | 命名"双来源 σ"估计量并给出输入表，或撤回 `ROBUST_INVERSION = 0` |
| REM-06 | 作者 | README 与 matrix v3 对齐：7 分子洁净子集与 4.84 kcal/mol 要么在 v3 下重推，要么标为被取代 |
| REM-07 | 作者 | 从扩展作业输入恢复 FEC/VC/EA/MA/SN 的声明电荷/多重度，并统一 `1/2` 与 `+1/2` 格式 |
| REM-08 | 作者 | 生成并复核 18 个中性母体的 InChIKey（`H1-01` 没有它建不起来） |
| REM-09 | 作者 | 恢复 `work/coverage_*` 被删的 53 个已提交文件（外加 `scripts/wp_production/wp1_audit_src.txt`），或出具书面退役决定 |
| REM-10 | 运行者 | 重取 A00 快照前必须先让工作树静止：审计期间有并发进程重新生成了 `work/research_completion_20261119/B_replay/`（19:02–19:03）与整个 `work/evidence18_strict_closure_20261116_codex/` 包（19:22）。`A00-12` 已在此条件上设了硬停 |

关闭 REM-01、02、04、05、06、09 并把对应主张从 `HOLD` 改为 `CLOSED` 后，
重跑 `python scripts/v2/a00_audit.py all`，`decision` 变成 `A00_PASS` 才可进入 A06 队列设计。

---

## 10. A06 系综补齐的最小必要计算队列（仅供下一步决策，本轮未提交任何作业）

按注册表读出的缺口，不是"重跑 24 态"，而是：

| 类别 | 位置数 | 性质 | 决策点 |
|---|---|---|---|
| 主集 E 类 | 3 | 搜过、候选 QC 失败且几何重复 | 需要新的起始材料来源，不是加预算 |
| 扩展 G 类 | 24 | 从未进系综候选池 | 需要先冻结候选池构建规则与预算 |

`FINAL_VERDICT.json#gap_final_characterisation` 给出的量级是 1440–2400 core-hours（扩展 24 位置）。
本轮授权 `budget_authorized_core_hours = null`，历史 800 core-hours **不自动继承**；
任何提交前必须先有写明的核时上限、队列、重启额度与停止条件。
