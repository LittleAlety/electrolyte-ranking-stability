# B3 · coverage 证据状态核对（只核状态，不作科学替代裁定）

- 任务派单 B3：「coverage 证据状态核对——证据不足保持未决、不手填 resolved；收到数据分析通过的覆盖证据后才按既有生成通道绑定」。
- 本轮动作：只读核对 + 哈希复核；**未做任何绑定、未改 coverage_route() 判据、未手填任何 resolved、未写共享生产文件**。
- 写入面：本目录 `docs/handoffs/lead_reception_strict_rebuild_20261103/evidence/`（本文件）。

## 1. 共享面冻结哈希复核（起止两列）

| 文件 | 本轮起点实测 | 本轮终点复测 | stable |
|---|---|---|---|
| `outputs/physics_completion/recovery/coverage_reviews.csv` | `e89188f6eac28bbf2dd309a95ec19ea9b1cc78969a262883820f939eec28ba40`（14 行） | `e89188f6eac28bbf2dd309a95ec19ea9b1cc78969a262883820f939eec28ba40`（终测，见 §5） | **是** |
| `outputs/physics_completion/ensembles/production_ensemble_labels.csv` | `c21003f5e18a2faaf4e3c8e91c379ea3ab16659706d13786ed25df0038ae0c80`（48 行） | `c21003f5e18a2faaf4e3c8e91c379ea3ab16659706d13786ed25df0038ae0c80`（终测，见 §5） | **是** |

> 局限声明：前后哈希相同只证明**本轮期间未变**，不证明历史未变。

## 2. 生产 coverage_reviews 现状（14 审查，实测）

`coverage_reviews.csv` SHA `e89188f6…`（=冻结值，未变）：

| verdict | route | 态 |
|---|---|---|
| resolved（11） | multi_basin_coverage（8） | DEC\|M, DME\|LiM_2plus, DME\|M_plus, EMC\|M_plus, SL\|LiM_2plus, **TMP\|LiM_2plus, TMP\|LiM_plus, TMP\|M_plus** |
| resolved（同上） | single_basin_verified（3） | **AN\|M_plus**, DMSO\|LiM_plus, DOL\|LiM_2plus |
| **unresolved（3）** | unresolved_qc（3） | DMC\|M_plus, DMC\|LiM_2plus, EC\|LiM_2plus（=2 limited + 1 provisional 三态） |

labels 侧 coverage_status 分布（48 态实测）：`not_reviewed 34 / resolved_by_review 11 / review_unresolved 3`。

## 3. strict recheck 对生产 resolved 的否定面（关键交叉）

`verification_20261103/coverage_recheck.json`（8 态）与生产审查交叉后，**3 态的生产 resolved 不可继承**：

| 态 | 生产标签 | 生产审查 | recheck 判定 | 本轮有效状态 |
|---|---|---|---|---|
| AN\|M_plus | `resolved_by_review`（route single_basin_verified） | review_id `…\|AN\|M_plus` | **UNRESOLVED_RECHECK_REQUIRED**（old claim `AN\|M_plus\|primary` 不在严格合格代表 `tors_3_0_1_2` 中） | **未决（不得继承 resolved）** |
| TMP\|M_plus | `resolved_by_review`（multi_basin） | review `…\|TMP\|M_plus` | **UNRESOLVED_RECHECK_REQUIRED**（old claim `r3_c42` vs 合格代表 `27`） | **未决** |
| TMP\|LiM_2plus | `resolved_by_review`（multi_basin） | review `…\|TMP\|LiM_2plus` | **UNRESOLVED_RECHECK_REQUIRED**（old claim `r3m_c00` vs 合格代表 `c13`） | **未决** |
| DEC\|LiM_2plus / DEC\|M_plus / GBL\|LiM_plus / PC\|M_plus / TMP\|M（5 条件池） | `not_reviewed`（无 review 行） | 无 | **PENDING_INDEPENDENT_COVERAGE_AND_IDENTITY_REVIEW**（合格代表 c02/15/c03/46/27） | **未审，待独立核验** |
| DMC\|M_plus / DMC\|LiM_2plus / EC\|LiM_2plus | `review_unresolved` | verdict unresolved（unresolved_qc） | 未列入 recheck | **未决（维持）** |

recheck 的 `zero_compute_action` 原文（8 态一致方向）：UNRESOLVED 三态 = `reconstruct search scope, qualified starts and dedup clusters; do not inherit old resolved`；5 条件池 = `verify terminal identity and coverage evidence before formal admission`。

## 4. 绑定判定（本轮）

| 检查项 | 结果 |
|---|---|
| 是否存在「数据分析通过、可按既有生成通道绑定」的新覆盖证据？ | **无**。Task A 五态/AN/TMP 取证本轮进行中，尚未形成通过结论；8 态 recheck 全部未决 |
| 本轮是否执行绑定？ | **否** — 无证据通过对象，按派单「证据不足保持未决」 |
| 是否手填 resolved？ | **否** — `coverage_reviews.csv`/labels 未写（哈希 §1 佐证） |
| `coverage_route()` 判据是否改动？ | **未改** — 本轮零代码写入；resolved 仍只能经 `multi_basin_coverage`/`single_basin_verified` 两路由（`build_coverage_reviews.py` 判据原样） |
| 后续绑定的触发条件 | ① Task A 对应态取证逐项通过（身份/单盆地/去重/覆盖承重成员齐全）→ ② 按既有生成通道（`build_coverage_reviews.py` 等）重新生成 → ③ 独立复核后才进入生产；在此之前全部保持现状态 |

## 5. 终测（交付前复测，两列哈希）

终测附录（实测于本轮全部 B 任务收尾后、B4 三条隔离复跑通道完成后）：

| 文件 | 终测 sha256 | 与起点 | 复测命令 |
|---|---|---|---|
| `outputs/physics_completion/recovery/coverage_reviews.csv` | `e89188f6eac28bbf2dd309a95ec19ea9b1cc78969a262883820f939eec28ba40` | **相同** | `sha256sum outputs/physics_completion/recovery/coverage_reviews.csv` |
| `outputs/physics_completion/ensembles/production_ensemble_labels.csv` | `c21003f5e18a2faaf4e3c8e91c379ea3ab16659706d13786ed25df0038ae0c80` | **相同** | `sha256sum outputs/physics_completion/ensembles/production_ensemble_labels.csv` |

（B4 §7 另有含费用/权重/去重在内的 8 文件起止哈希表，结论一致：正式标签与费用未变。）
