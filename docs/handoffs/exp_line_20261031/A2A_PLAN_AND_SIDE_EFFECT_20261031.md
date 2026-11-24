# A-2a 施工方案 + 必须报备的副作用（2026-10-31）

> 状态：**方案已备好，未执行**。原因：本方案会在**正式表**上产生可见改动（`limited → provisional`），
> 按纪律必须先报备。**当前候选表未改、正式记录仍 45 accepted / 3 limited。**

## 1. 已完成的 A-1（可复核）

| 项 | 实测 |
|---|---|
| 包位置 | `work/hpc_dmc_lim2plus_vtscf16_v1/`（`work/hpc_*` 一层） |
| 移动前后哈希 | `sha256sum -c` **14/14 OK**；清单 sha `5265178162694d5f…` **与移动前一致** |
| manifest `members` | 已加（19 字段，`member_role=recovery_v1_start`、`seed=p5li_vtscf16`、`status=PLANNED_NOT_RUN`） |
| 导入器发现 | `iter_packages()` 实测 **命中**（48 个包中含本包） |
| 是否借被取消探针背书 | **否**（`seed` 非 `tors_`、`source_kind` ≠ `p4v2_screening_v1_start`，`_probe_starts` 判据实测 False） |

## 2. A-2a 的施工方案（走生成器，不手改 CSV）

### 2.1 为什么不复用 `p4v2` 通道（实测）

`p4v2_candidate_rows()` 内置硬闸：`validate_candidate_start(...)` 必须返回 `ok_heavy_fragment`，否则 `raise`（"a pure-Li displacement must never be activated as a skeleton start"）。
**我对本起点实测该闸 = `rigid_transformation`**（`probe_class`/`skeleton_pair_change_a` 均 `None`）⇒ 生成器会 `raise`。
根因合理：那条通道的语义是"**骨架位移**起点"，而本起点与 primary 末几何**同字节**，对它而言是刚性变换 ⇒ 本就不是该通道该收的东西。

### 2.2 拟新增：一条独立、只校验"身份+哈希+来源"的版本化通道

| 项 | 内容 |
|---|---|
| 版本化登记源 | `config/vtscf_strict_opt_registration_v1.json`（新增） |
| 生成器函数 | `build_production_ensemble_manifest.py` 新增 `vtscf_strict_opt_candidate_rows()`，与 `p4v2_candidate_rows()` **并列**、**互不影响** |
| 硬校验（全部 fail-loud） | ① `state_key` 可解析且 `charge=2 / multiplicity=2 / NEL=49`（**读 ORCA 日志原文行**校验，不靠算术）② 包内 `geom.xyz` 的 sha 等于登记值与源几何 sha ③ 源几何路径存在 ④ 该 `member_key` 不在 `_rejected_probe_members()` 排除集内（避免重蹈 `tors_7_0_1_2` 覆辙） |
| 写出行 | `member_role=recovery_v1_start`、`seed=<登记值>`、`source_kind=<登记值>`、`status=planned`、`charge=2`、`multiplicity=2` |
| 触发方式 | 与既有 `--register-recovery` **同一个 flag**（生成器注释明写"注册在同一 flag 下，使普通重建不会静默丢掉一次授权"） |
| 纪律 | 属 tracked 生产代码改动 ⇒ 须补**回归测试**；按仓库约定，新增测试先交独立目录再由 Lead 合入（本线已有此惯例） |

### 2.3 必须先报备的副作用（**这是本轮停下的原因**）

`load_candidates()`（`build_production_ensemble_aggregator.py:599-613`）把 `recovery_v1_start` 当作**一等成员**（"counts toward the state's acceptance"）。而在主循环 `:809-814`：

```python
mem = latest.get("%s|%s|%s" % (r["name"], r["slot"], r["seed"]))
if mem is None:
    n_pending += 1          # registered, no result yet
```

**只读推演（未改任何文件）**：

| 量 | 现网 | 加候选行后 |
|---|---|---|
| `DMC\|LiM_2plus` 的 `n_pending` | **0** | **1** |
| `unresolved` | 0 | >0 |
| `acceptance_status`（按 `acceptance_decision :653-657`） | **`limited`** | **`provisional`** |
| `limitation_reason` | `rescue_budget_exhausted` | 清空 |

⇒ **加这条 planned 候选会让该态从 `limited` 变成 `provisional`**，这是**正式表上的可见改动**，并会改变 45/48 的计数结构（`provisional` 与 `limited` 在 48 分母里的含义不同）。

生成器自己的 docstring 就警告过这一点：
> "The aggregator treats every `planned` `recovery_v1_start` as registered work, so a registered-but-never-run start would park its state `pending` forever."

**这正是 A 反复强调的"不得以程序返回值代替科学结论"的同类风险**——登记一行就会移动正式标签。

## 3. 因此需要你在三选一里再定一步

| 选项 | 做法 | 后果 |
|---|---|---|
| **A-2a-i（登记 + 接受 provisional）** | 按 §2.2 施工并重建候选表 | 该态 `limited → provisional`；**必须在正式表与报告里如实记录这次状态迁移及其原因**（一次已授权、尚未运行的登记） |
| **A-2a-ii（登记，但保持 limited）** | 施工，但**不重建**候选表，或把登记行 `status` 写成聚合器**不计入 pending** 的取值（需先实测确认哪个取值安全，例如让 `latest.get` 命中一个显式 `superseded` 成员） | 需要额外设计，且可能让"登记"形同虚设 ⇒ 与 A-2 的目的冲突 |
| **A-2a-iii（不登记，先让 A 只审"若登记后会怎样"）** | 保持现状，把 §2.2 的登记源与生成器改动做成**只读预演**，让 A 先回答"代码路由 + 科学依据"两问；若 A 判定科学上不成立，则**连登记都不必做** | **0 副作用、0 生产写入**；但 A-2 暂不落地 |

**我的建议：A-2a-iii 先行**。理由：A 复检的两问里，"**不借已取消探针背书时，现有证据能否支持 `single_basin_verified`**"是**纯科学判断**，不依赖候选行是否存在；若 A 判定不成立，登记就白做且还要承担 `limited→provisional` 的标签迁移。先拿到 A 的科学结论，再决定是否值得付这个代价。

## 4. 当前状态（实测，未变）

| 项 | 值 |
|---|---|
| 提交 | **0**（无 `submission_journal.json`、无提交锁） |
| 包 | `submission_gate=HOLD`、`submitted=false`、`sha256sum -c` **14/14 OK** |
| 候选表 | **未改**（无本尝试行） |
| 正式记录 | **45 accepted / 3 limited，分母 48** |
| 生产面写入 | 仅 A-1（`work/` 层：包移动 + manifest `members`） |