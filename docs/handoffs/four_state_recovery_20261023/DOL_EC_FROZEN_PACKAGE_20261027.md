# DOL/EC 生产起点**冻结包**（2026-10-27，`submission_gate=HOLD`，未提交）

> 执行用户裁定第 2 步的最后一项：「**冻结候选**、次数、成本和停止条件」。
> 本包把两个经权威门核验的起点**固化成一包**，使「批准 → 接线 → 提交」不再需要重新计算或重新挑选。
> **`submission_gate=HOLD`、`submitted=false`、零作业。**

## 1. 包内容（`work/dol_ec_recovery_v1/`，7 文件 + 哈希清单）

| 成员 | 起点 | 骨架变化 | vs 已登记极小 | 冻结规则下 |
|---|---|---|---|---|
| **`DOL\|LiM_2plus`** | **`p4_02_ring_pucker_twist`** | **0.0771 Å** | **0.0962**（`C09\|LiM_2plus#m2`） | `duplicate`（< 0.35） |
| **`EC\|LiM_2plus`** | **`p4_02_ring_pucker_twist`** | **0.0549 Å** | **0.1224**（`C04\|LiM_2plus#m1`） | `duplicate`（< 0.35） |

**两起点与已登记极小的几何 sha256 均不同**（`same_geometry_as_kept_minimum=false`）⇒
**不构成「重复提交相同几何」**。

**每个成员目录含**：`geom.xyz`（起点几何）、`member.json`（全事实）、`job.inp`（冻结方法 + 注入的电荷/自旋）。

## 2. 冻结的执行参数（**账目都在包里**）

| 项 | 值 |
|---|---|
| `member_role` | **`recovery_v1_start`**（否则永不进 `latest`，见 `0mvp7xbj`） |
| `source_kind` | `p4v2_screening_v1_start` |
| `status` | `planned` |
| 方法 | `wB97X-D4 def2-TZVPD Opt AnFreq SMD(acetonitrile) VeryTightOpt TightSCF SlowConv` |
| 五阈值 | 由 **`VeryTightOpt`** 隐含（`TolE 2e-7 / TolMaxG 3e-5 / TolRMSG 8e-6 / TolMaxD 2e-4 / TolRMSD 1e-4`） |
| `%pal` | `nprocs 4`（＝分配核数，`orca_production_v1.cores=4`） |
| 电荷/自旋 | `* xyzfile 2 2`（两态均 `charge=2`、`mult=2`） |
| **成本（两口径）** | **实测口径 36.82 CH**（2 × p90 18.41）；**提交器预留 192 CH**（2 × 96） |
| **支付来源** | **`budget.production`（512 cap）**，**不是**筛选余量 30.12 |
| 停止条件 | 每态 1 腿、QC 通过即停（第二起点须另行批准）；身份漂移**不重试**；超阈值只允许**有界** `max-cycles`；**不降任何阈值** |

## 3. `--check` 的守卫（**8 条已 RED 实证**）

`work/_dol_ec_build_package.py --check` 逐条断言：

| # | 守卫 | RED 用例 |
|---|---|---|
| 1 | `submission_gate == HOLD` 且 `submitted is False` | 翻成 `OPEN` ⇒ **红** |
| 2 | 同上 | 标 `submitted=true` ⇒ **红** |
| 3 | `member_role == recovery_v1_start` | 改成 `round2_audit_extra` ⇒ **红** |
| 4 | **`member.json` 与 manifest 逐字段一致** | 谎称「骨架未动」⇒ **红** |
| 5 | 同上 | 谎称「与极小同一几何」⇒ **红** |
| 6 | `%pal nprocs 4 end` | 改成 2 ⇒ **红** |
| 7 | 冻结方法含 `AnFreq` / `VeryTightOpt` / `SMD(acetonitrile)` | 删 `AnFreq` ⇒ **红** |
| 8 | **禁 `NumGrad`** | 注入 ⇒ **红** |
| — | 起点几何哈希现算比对、骨架真动、非极小拷贝、**未泄漏进生产候选表** | — |

**RED 脚本**：`work/_dol_ec_package_check_red.py` ⇒ 实测 **8/8 红、对照组保持绿** ⇒ `RED PROVEN`。

## 4. ⚠ RED 过程中发现并修好的一处**真缺陷**

首轮 RED 有 **2 个用例仍是绿的**：我篡改了 `member.json`，但 `check()` 只校验 `manifest.json` 的
`members` 数组，**从不读 `member.json`** ⇒ **同一事实存在两份副本却无一致性守卫**，
篡改 `member.json` 会**静默通过**。

**修法**：给 `check()` 增加第 4/5 条守卫——`member.json` 与 manifest 条目**逐字段比对**
（`geometry_sha256`/`skeleton_*`/`charge`/`multiplicity`/`leaf`/`closest_kept_minimum`/`best_heavy_rmsd_*`）。
修后复跑 RED ⇒ **8/8 红**。

> **这正是我记过的「RED 全绿说明没打到」的反向用法**：RED **没全红** ⇒ 说明有守卫缺失，而不是「那个属性不重要」。

## 5. 🚫 为什么**仍然不能提交**（未变）

`manifest.blocked_reason` 明确写入：
**DOL/EC 在 `production_ensemble_candidates.csv` 里没有 `recovery_v1_start` 行**
（根因：`strict_recovery_v1_manifest.csv` 的 `start_1_basin`/`start_2_basin` 为空 +
`torsion_probe_candidate_rows()` 的 glob 只认 `hpc_torsion_probe_v*`）⇒
**即使提交并跑完，结果也无处挂靠，状态永远 `limited`**。

**⇒ 必须先批准并落地一条版本化候选通道，本包才能提交。**
`--check` 里还有一条「**未泄漏进生产候选表**」守卫（按几何 sha256 查表），保证本包**不会悄悄变成**登记。

## 6. 守线

- ⛔ 未写入 `outputs/**/production_ensemble_candidates.csv`；
- ⛔ 未修改任何生成器或契约；
- ⛔ 未提交任何作业（队列空）；
- ⛔ 不把 `duplicate` 结论改写成「新盆地」。

## 7. 证据出处

- 构建器：`work/_dol_ec_build_package.py`（`--check` 双用）
- RED：`work/_dol_ec_package_check_red.py`（8 用例 + 对照）
- 包：`work/dol_ec_recovery_v1/{manifest.json,PACKAGE_SHA256SUMS,members/*/}`
- 起点来源：`work/hpc_four_state_p4_xtb_screening_v1/tasks/{DOL,EC}__LiM_2plus/p4_02_ring_pucker_twist/`
- 阻塞根因：`DOL_EC_NO_CANDIDATE_ROOT_CAUSE_20261027.md`
- 判据：`INDEPENDENT_START_CRITERIA_20261027.md`、`PRODUCTION_ROLE_WIRING_20261027.md`