# P4 · 五态隔离绑定（Plan 首批第 4 项后半）

> 会话：公共处理会话（唯一共享生产写入者）｜权限：Plan 首个执行批次「五态隔离绑定」——**隔离演练**，非正式发布。
> 边界：不写任何正式路径、不改 `coverage_status`、不填 `resolved`、不新增计算、不迁账本、身份与 coverage 裁定权在数据分析/Lead。
> 复核时间：2026-11-03（仓库 HEAD `80933e54f8a605d9dd6d033c0f2861e33b591c13`）。

## 1. 绑定配方来源（只读依据）

`docs/handoffs/strict_rebuild_20261103/remote_closure_20261103/README.md:43`（交给用户的未做事项 #2）：
> 五态覆盖范围绑定尚未完成。应继续对照 `sampling_conformer_set.csv`、`sampling_index.json`、`sampling_audit_index.json`、原候选登记和原起点几何，将具体范围与合格代表绑定；没有理由先申请新计算。旧 sampling 审核索引引用的结构账本哈希已过期，不能直接沿用其状态结论。

五态清单与合格代表：`verification_20261103/coverage_recheck.json`（A1 §3 已逐态取证）。

## 2. 改了什么

**只新增本隔离目录 2 个文件，受控面（scripts/config/outputs）零写入**（实测：P3 基线之后受控面仅 `build_coverage_reviews.py` 一处 P3 授权改动）。

| 文件 | sha256 | 字节 |
|---|---|---|
| `evidence/p4_five_state_binding/p4_five_state_binding.py` | `a67d718a4803d9793e11ccb0412203bf296b6a38ee90ab5fd8548479d54336db` | — |
| `evidence/p4_five_state_binding/binding_package.json` | `4a35436ef5ffae5b5ee1c95ecdcced78903314bb0d0e5b219fa22288dd037d64` | 10,837 |

绑定器行为（`mode=ISOLATED_READ_ONLY`）：

1. **冻结复核**：`freeze.json` 列出的 4 个输入逐个 SHA256 对照，不符即 `P4 REFUSING`；
2. **范围与登记源**：`coverage_recheck.json`（状态原文逐字保留）、`sampling_conformer_set.csv`、`sampling_index.json`、`production_ensemble_structures.csv`（须等于冻结哈希 `3a795ce8…`）记哈希入包；
3. **显式排除** `sampling_audit_index.json`：只读其记录的 `inputs.production_ensemble_structures.csv` 做**过期自检**（recorded `3f2c692d…` ≠ actual `3a795ce8…` → 过期成立才继续；相等则拒），**绝不消费其状态结论**；
4. 每态绑定 = 合格代表（原候选登记行）+ 范围行（free_conformer_pool / li_motif_screening）+ 起点指针（li_motif note 的 parent sha256 / conformer source_index）+ 状态原文；
5. 自检断言：包内**无 `resolved` 键**、五态全 `ISOLATED_CANDIDATE_BINDING`、全 `production_written=false`、全 `coverage_status=NOT_TOUCHED`。

## 3. 证明了什么（实测）

```
$ python …/p4_five_state_binding.py --negative-selftest
negative_selftest: OK (missing freeze + drifted frozen input both refused)   # exit 0
$ python …/p4_five_state_binding.py
states = 5 | sources = 8 | excluded = 1
   DEC|LiM_2plus | DEC|LiM_2plus|c02 | li_motif_screening rows=1 | ISOLATED_CANDIDATE_BINDING
   DEC|M_plus    | DEC|M_plus|15     | free_conformer_pool rows=4 | ISOLATED_CANDIDATE_BINDING
   GBL|LiM_plus  | GBL|LiM_plus|c03  | li_motif_screening rows=1 | ISOLATED_CANDIDATE_BINDING
   PC|M_plus     | PC|M_plus|46      | free_conformer_pool rows=1 | ISOLATED_CANDIDATE_BINDING
   TMP|M         | TMP|M|27          | free_conformer_pool rows=2 | ISOLATED_CANDIDATE_BINDING
selfcheck OK (no resolved key, isolation intact)                            # exit 0
```

产物复核：`resolved_in_text = False`；excluded 条目 `recorded=3f2c692d… / actual=3a795ce8…`（过期本轮再证）；`sources roles = frozen_input×4 + adjudicated_recheck + range_evidence×2 + EXCLUDED_stale`；五态 `status_verbatim` 全为 `PENDING_INDEPENDENT_COVERAGE_AND_IDENTITY_REVIEW`，各 2 条 missing。

负测命中原因：缺 freeze → `P4 REFUSING: freeze.json missing`；冻结输入漂移 → `P4 REFUSING: frozen input drifted`（临时目录副本，不碰真仓）。

输入哈希总表：

| 源 | sha256 |
|---|---|
| `verification_20261103/freeze.json` | `47bd8496a7dbb0f1eaa9e58ee3fbbbd12d8fa4333c172033e39a10539e8bb266` |
| `verification_20261103/coverage_recheck.json` | `182d32aba5e99e7ff13f7f922f42d4e3fe473f26e8a276710419ddcc1cbc8a6d` |
| `sampling/sampling_conformer_set.csv` | `b4665e14dc3f2cc337e2229190115f52f98725be09bec1f49d0b7099b91b4f4c` |
| `sampling/sampling_index.json` | `6aa3bf194a1bbf5ee3210c6cdcdd72af14912f8b632c1543732aba50d2de9195` |
| `sampling/sampling_audit_index.json`（EXCLUDED_stale） | `c0180ae81d69851625c0b9e980ac46da9de61d6e62dfae055f9beab58a134fa3` |
| `ensembles/production_ensemble_structures.csv`（=冻结 `3a795ce8…` 实测一致） | `3a795ce8680e84ec0e60ef0411c78fb8236daf492e8647ebec25efbebc96732b` |

## 4. 发布了什么

**零正式发布。** 本包是隔离候选绑定：未写 `coverage_8`/任何 coverage 登记、未改任何正式标签、未动费用、无作业提交、无新增计算。历史正式状态 45/2/1 不变。

## 5. 没有关闭什么

1. **五态身份与 coverage 裁定**仍 `PENDING_INDEPENDENT_COVERAGE_AND_IDENTITY_REVIEW` → 按停止规则**交数据分析**（包内 `handovers` 已登记）；本绑定不制造登记事实。
2. **生产侧 `registered_starts` / `coverage_review_id` 绑定**需要批准，本批未做。
3. 范围证据强度不等（A1 §5 原样继承：PC|M_plus 单结构池、GBL round-2/audit 限定检索未找到等）——绑定≠覆盖已裁定。
4. 三个未确定（D7 独立签章、D8 三轴偏斜、rdkit 环境）与 Open questions（切换/发布/归档授权）不变。

## 6. 如何恢复

```bash
rm docs/handoffs/lead_reception_strict_rebuild_20261103/evidence/p4_five_state_binding/binding_package.json
rm -r docs/handoffs/lead_reception_strict_rebuild_20261103/evidence/p4_five_state_binding/
```
本目录全为新增文件，删除即回到改前状态；未用 `git reset`，未触碰任何并行工作文件。

## 7. 复现命令（cwd=仓库根）

```bash
python docs/handoffs/lead_reception_strict_rebuild_20261103/evidence/p4_five_state_binding/p4_five_state_binding.py --negative-selftest   # exit 0
python docs/handoffs/lead_reception_strict_rebuild_20261103/evidence/p4_five_state_binding/p4_five_state_binding.py                       # exit 0
sha256sum docs/handoffs/lead_reception_strict_rebuild_20261103/evidence/p4_five_state_binding/{p4_five_state_binding.py,binding_package.json}
```
