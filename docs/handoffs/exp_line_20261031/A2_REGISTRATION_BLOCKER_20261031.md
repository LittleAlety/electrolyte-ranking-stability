# A-2 阻塞报告：版本化登记源不接纳本起点（2026-10-31）

> 结论：**A-1 已完成并验证；A-2 按你指定的"走生成器/版本化登记源"路径实测走不通**，
> 需要你在两条路之间裁决。**未手改任何会被重建的 CSV；未提交作业；包仍 HOLD。**

## 1. A-1 已完成（零计算，已实测验证）

| 步骤 | 结果 |
|---|---|
| 包移到 `work/hpc_dmc_lim2plus_vtscf16_v1/`（`work/hpc_*` 一层） | 完成；原路径已移除；目标此前不存在（防覆盖检查通过） |
| 移动前后哈希核对 | `sha256sum -c PACKAGE_SHA256SUMS` **14/14 OK**；清单自身 sha `5265178162694d5f…` **与移动前完全一致**；起点几何 `f619c132…`、manifest 未变 |
| manifest 增加 `members` | 已加（19 字段，`member_role=recovery_v1_start`、`seed=p5li_vtscf16`、`status=PLANNED_NOT_RUN`） |
| **导入器能否发现** | **能**——`iter_packages()` 实测命中 **48** 个包，含 `hpc_dmc_lim2plus_vtscf16_v1` |
| 是否借了被取消探针的背书 | **没有**——`seed` 不以 `tors_` 开头、`source_kind=vtscf_strict_opt_v1_start` ≠ `p4v2_screening_v1_start` ⇒ `_probe_starts` 判据实测 **False** |

（附带更正一条旧认知：`_probe_starts` **现已接受** `source_kind == "p4v2_screening_v1_start"`（2026-10-27 裁定已实施），不是只认 `tors_` 前缀。）

## 2. A-2 为什么走不通（实测，不是推测）

按你的指示，我不手改 `production_ensemble_candidates.csv`，而去用它的**版本化登记源**
`config/recovery_start_activation_v1.json` → 生成器 `build_production_ensemble_manifest.py::p4v2_candidate_rows()`。
该函数**自带硬校验**（`p4v2_candidate_rows` 内，缺证据/哈希漂移/闸判不符一律 `raise`，注释写明 loud by design）：

```python
verdict = _tpg.validate_candidate_start(syms, src, cxyz, _agg.bond_adjacency(syms, src),
                                        check_li_shell=True, declared_li_change=...)
if verdict["reason"] != "ok_heavy_fragment":
    raise ValueError("activated start %s: the authoritative gate says %r, not "
                     "ok_heavy_fragment -- a pure-Li displacement must never be "
                     "activated as a skeleton start" % (entry["state_key"], verdict["reason"]))
```

**我对本起点实测该闸**：

| 项 | 实测 |
|---|---|
| 组成一致（源几何 vs 包内几何） | `True` |
| `validate_candidate_start(...)` 的 `reason` | **`rigid_transformation`** |
| `probe_class` / `skeleton_pair_change_a` | `None` / `None` |

⇒ `reason != "ok_heavy_fragment"` ⇒ **生成器会 `raise`**。
**根因（合理，不是 bug）**：该通道的语义是"**骨架位移**起点"（`p4v2_screening_v1_start`，2026-10-27 授权，只收骨架真动的 13 条）；我的起点是**同一个极小**（与 primary 末几何**同字节**），对它而言这是**刚性变换**而非骨架变化。所以**它不是这条通道该收的东西**。

**顺带确认另一条生成器路径也不适用**：`--register-recovery` 的 help 原文写着
`"also register strict_recovery_v1 starts as candidates (only AFTER their results exist: registering a planned member would turn the state provisional)"`
⇒ 它是"**结果存在之后**"才登记，而我需要在**提交前**就有登记行。

## 3. 因此 A-2 只剩两条路（需你裁决）

| 选项 | 做法 | 代价 / 风险 |
|---|---|---|
| **A-2a 扩一条版本化通道**（改代码） | 在生成器里新增一个**独立于 `p4v2` 骨架闸**的登记通道（例如读一个新配置节 `vtscf_strict_opt`，校验项改为"身份 2/2/49 + 几何 SHA + 来源路径"，**不**要求骨架位移），由它写出 `member_role=recovery_v1_start`、`status=planned` 的候选行 | 属 **tracked 生产代码改动**（`build_production_ensemble_manifest.py`），须守四处登记纪律 + 回归测试；但它符合你"落生成器/版本化登记源"的要求 |
| **A-2b 手写候选行**（不改代码） | 直接往 `production_ensemble_candidates.csv` 加一行 | 与你的指示冲突（"不要只手改会被重建覆盖的 CSV"）——**重建即丢失**，我不推荐；且这会让"重建后静默失效"，正是我们一路在防的失败 |

**我的建议**：**A-2a**。理由：本起点的语义（严格协议下对已登记单一极小的独立复现）与 `p4v2` 的骨架位移通道**本就不同类**，硬塞进去会污染那条通道的语义（并触发它的 loud 校验）；另立一条只校验"身份+哈希+来源"的通道，才是诚实的做法，也满足你"落在生成器/版本化登记源"的要求。

**需要你补充确认一件事**：A-2a 是 **tracked 生产代码改动**（新增一条登记通道 + 配置节 + 测试）。按派单"唯一生产写入者"由我执行，但这是**新增功能**而非纯登记，是否仍在 (a) 的放行范围内？

## 4. 当前状态（实测）

| 项 | 值 |
|---|---|
| 提交 | **0**——无 `submission_journal.json`、无提交锁 |
| 包 | `submission_gate=HOLD`、`submitted=false`、`sha256sum -c` **14/14 OK** |
| 候选表 | **未改**（`production_ensemble_candidates.csv` 无本尝试行） |
| 正式记录 | **45 accepted / 3 limited，分母 48** |
| 生产面写入 | 仅 A-1：包移动 + manifest 加 `members`（均在本线写入面，`work/` 层） |

## 5. 待 A 复检的两问（已按你的要求准备好，等 A-2 有登记行后启动）

1. **代码路由**：新成员能否被**导入、去重、coverage** 正确看见（不是"程序返回 resolved"就算数）。
2. **科学依据**：**不借已取消探针背书**时，现有证据能否支持 `single_basin_verified`——须分别给出代码路由与科学依据，不得以"程序返回 resolved"代替后者。