# 28 条筛选证据的版本化登记（2026-10-27，执行用户裁定第 1 步）

> 用户裁定（2026-10-27）第 1 步：「**补齐 28 条筛选证据的登记与引用**。按态拆分：DOL/EC 合计 24 条、
> DMC 两态合计 4 条。注明这是**历史执行证据的补接线，不能伪装成事前生产预注册**。
> **补登记后的验收预期仍为 44/4。**」
>
> 本文记录该补接线的完成情况与**它不做的事**。

## 1. 登记结果（实测）

| 批次 | JobID | 元素 | 引擎/方法 | 登记性质 |
|---|---|---|---|---|
| `p4_xtb_screening_v1` | `3774215` | 8 | xtb / GFN2-xTB | **历史执行证据补接线** |
| `xtb_screening_v2` | `3777206` | 20 | xtb / GFN2-xTB | **历史执行证据补接线** |

**按态拆分（与用户划分逐项一致）**：

| 态 | 条数 |
|---|---|
| `DOL\|LiM_2plus` | **12** |
| `EC\|LiM_2plus` | **12** |
| `DMC\|LiM_2plus` | **2** |
| `DMC\|M_plus` | **2** |
| **合计** | **28**（**DOL/EC = 24**、**DMC = 4** ✅） |

**每条记录带**：`batch` / `job_id` / `engine` / `method`（GFN2-xTB）/
`state_key` / `task_path` / **`geometry_sha256`（现算）** / `rel_kcal_gfn2` / `machine_verdict`，
以及两条**资格声明**：
- `admissible_as: search_scope_documentation_only`
- **`NOT_admissible_as: production_computed_member`**

## 2. **登记不改变任何结论**（必须说清）

登记文件自身**显式声明**：

> These records back-wire **already-executed** screening runs (P4 job `3774215`, v2 job `3777206`).
> They are **NOT** a pre-registered production batch, and they are **NOT** production
> `computed` members — registering them does **not** and **cannot** turn a
> `search_exhausted` state into an accepted one.

并写入 `expected_acceptance_after_registration: unchanged (44/48)`。

**原因（已实测，见 `PROBE_REGISTRATION_GAP_20261027.md`）**：`search_exhausted` 的成立条件是
**没有生产恢复成员（`latest_members` 为空）**；**只补 `registered_starts` 不改变 route**（用户反例，我方已复现）。
⇒ **补登记是接线，不是恢复**；要恢复必须**有生产级 `computed` 成员**。

## 3. 交付物与位置

| 项 | 路径 | 说明 |
|---|---|---|
| 登记表 | `work/screening_evidence_registration_v1/screening_evidence.json` | 28 行 + 批次溯源 + 显式声明 |
| 汇总 | `work/screening_evidence_registration_v1/summary.json` | `total 28`、`dol_ec 24`、`dmc 4` |
| 生成器 | `work/_h2_register_screening_evidence.py` | `--check` 用**现算哈希**防漂移 |

> **均在 `work/`（gitignored 机器本地层）**，按项目纪律**不入库**；以本文留痕。

**`--check` 实测**：`problems: none` ⇒ `SCREENING EVIDENCE OK (28 rows)`；
它**重新计算每个几何的 sha256** 并与登记值比对（`geometry drifted:` 即报错），故登记无法静默过期。

## 4. 明确**未**做的事（守线）

- ⛔ **未**把这 28 条写成 `production_ensemble_candidates.csv` 的 registered start——
  那会让 `_probe_starts()` 误把它们当**生产起点**，**混淆筛选证据与生产证据**；
- ⛔ **未**修改 `coverage_reviews.csv` 的任何 `verdict`；
- ⛔ **未**改 `coverage_route` / `_probe_starts` 的前缀过滤；
- ⛔ **未**声称补登记后 DOL/EC 可被接受（**预期仍 44/48**）。

## 5. 后续（用户裁定的第 2–4 步，待授权/待预算）

2. **为 DOL/EC 各准备一个生产级覆盖验证方案**（从可追溯、经非刚体与身份预检的**独立起点**出发，
   冻结候选/次数/成本/停止条件；**不得用已知极小的相同几何冒充独立搜索**）；
3. **通过真实生产计算补足证据**（冻结方法下严格优化 + `AnFreq` + 身份 QC + 去重，由 importer 验证方法；
   `imaginary_modes` 与两个哈希「非空」**不足以**证明生产证据合格）；
4. **按结果自动走覆盖路线**：通过 QC 且复现已接受极小 + 搜索范围等证据齐全 ⇒ `single_basin_verified`；
   通过 QC 且得新极小 ⇒ `multi_basin_coverage`；QC 失败或证据不完整 ⇒ 继续 `limited`。

> 用户核心结论（原话要旨）：「**DOL/EC 不必强行找到第二个极小才能恢复，
> 但必须证明独立起点在生产方法下通过了验证。『版本化登记』能够建立这条证据链，不能替代其中的计算。**」

## 6. 证据出处

- 登记生成器与产物：`work/_h2_register_screening_evidence.py`、
  `work/screening_evidence_registration_v1/{screening_evidence,summary}.json`
- 判定输入：`work/_p4_triage_out.json`（8 行）、`work/_v2_triage_out.json`（20 行）
- 几何：`work/hpc_four_state_p4_xtb_screening_v1/tasks/**/xtbopt.xyz`、
  `work/hpc_xtb_screening_v2/tasks/**/xtbopt.xyz`（sha256 现算）
- 相关：`PROBE_REGISTRATION_GAP_20261027.md`（含 §3.5 用户裁定）、`FOUR_STATE_ACCEPTANCE_PATH_20261027.md`