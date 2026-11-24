# 首点收敛例外：统一协议裁定材料

**日期**：2026-10-31  
**性质**：零计算裁定材料。**未改动任何正式标签、未运行任何生成器写入、未提交任何作业。**  
**对外口径（本轮维持）**：正式历史记录仍是 **45/48（历史协议）**；**14/48 是情形 B 的模拟值**，严格五项证据的模拟结果正在复核。模拟数**不得**写入正式验收表。

**本文所有数字的唯一权威计算**：`work/_fpc_ruling_per_state_20261031.py` → `work/_fpc_ruling_per_state_20261031.json`。  
**独立复核**（不同代码路径、只读 JSON 原始字段重实现规则）：`work/_fpc_ruling_crosscheck_20261031.py` → 四情形 **28/14/15/14 逐项一致、0 处分歧**。  
早前两份产物（`_fpc_ruling_material_20261031.py`、`_fpc_state_sim_20261030.py`）中与本文不一致的数字，一律以本文第 1 节结论为准；其分歧本身在第 1.3 节交代。

---

## 1. 为什么 45→11 变成 45→14（不是四舍五入，是两处口径差）

### 1.1 两个推演版本的输入与判定差异

| 版本 | 判定规则 | 塌陷态 | 模拟 accepted |
|---|---|---:|---:|
| **V1（已废）** | 一个态的**全部 computed 成员**都是例外成员 ⇒ 该态塌陷（只看成员表） | **34** | **11** |
| **V2（现行）** | 剔除例外成员后，**权威 kept 池**里再无可用成员；或承重覆盖审的 claim 证据本身是例外成员（反作弊失效） | **17** | **28** |
| **V3（现行，加处置假设）** | 同 V2，但把「例外成员降级」视为**产生新限制**（需 resolved 覆盖审覆盖） | **31** | **14** |

**V1 的两处错**：
1. **把被去重剔除的例外成员当承重成员数**。实测 58 条例外成员中只有 **36 条**进入 kept 池，**10 条被 `dedup kept=false` 剔除**（重复极小本就不承重）；这使 5 个态被误判塌陷：`DMC|M`、`DMSO|M`、`DMSO|M_plus`、`EC|LiM_plus`、`GBL|M_plus`（其 kept 池仅 `primary`，例外成员从未承重）。
2. **没看覆盖审的反作弊**：V1 完全不读 `coverage_reviews.csv`。

**V1 同时漏判 2 个态**（`B \ V1`，逐态理由不同，不可并叙）：

| 态 | 实测 | 为何 V1 漏、V2/V3 抓到 |
|---|---|---|
| `TMP\|M_plus` | kept 含 1 例外 + 2 非例外；`multi_basin_coverage` 审 claim = `TMP\|M_plus\|r3_c42`（例外成员） | **承重覆盖审的反作弊失效**，情形 A 与 B 均塌陷；V1 因「仍有非例外 computed 成员」而放行 |
| `DEC\|M_plus` | kept 含 1 例外 + 2 非例外；**无覆盖审记录** | 仅在 D1=新限制（情形 B）塌陷：有例外成员却无 resolved 审可覆盖；A 情形不塌陷 |

**净变化 = 5 恢复 − 2 新抓 = 3**，即 34 → 31。

### 1.2 恢复的 5 个态逐态依据（V1 → V2/V3）

| 态 | V1 判据 | 实测 | 结论 |
|---|---|---|---|
| `DMC\|M` | computed 全为例外 | kept 池 = `['DMC\|M\|primary']`；例外成员 `DMC\|M\|8` **`kept=false`** | 例外成员不承重，**不塌陷** |
| `DMSO\|M` | 同上 | kept = `primary`；例外成员去重剔除 | 同上 |
| `DMSO\|M_plus` | 同上 | kept = `primary`；例外成员去重剔除 | 同上 |
| `EC\|LiM_plus` | 同上 | kept = `primary`；例外成员去重剔除 | 同上 |
| `GBL\|M_plus` | 同上 | kept = `primary`；例外成员去重剔除 | 同上 |

### 1.3 必须主动交代的剩余分歧

同一份输入下，我对「两个未裁定选择」的旧脚本给出过 C/D 情形 = **6 / 5**，现行脚本给出 **15 / 14**。差值 = **9**：
`AN|LiM_2plus`、`AN|M_plus`、`DMC|M`、`DME|LiM_plus`、`DMSO|M`、`DMSO|M_plus`、`EC|LiM_plus`、`EMC|LiM_2plus`、`GBL|M_plus` —— 这些态 kept 池**仅为 primary 且不含任何例外成员**。若裁定「primary 也须自带五项证据」（选择 D2），它们会塌陷，但**与首点例外无关**，属独立问题，已从本议题剥出单列（见第 4 节末）。

---

## 2. 「成员失去资格」≠「状态失去资格」：逐态拆解

判据三问，逐态独立回答，不按「缺能量字段的成员数」聚合计数：
① 剔除例外成员后 kept 池是否仍有可用成员？② 承重覆盖审的 claim 证据是否随之失效？③ 若例外成员降级为「新限制」，是否有 resolved 审覆盖它？

**输入哈希（完整 64 位，可直接比对）**：

| 输入 | sha256 |
|---|---|
| `production_ensemble_structures.csv` | `3f2c692d2207d935347c3508e095e183e7f25a192952dc84b430b2d023d55df6` |
| `production_ensemble_weights.csv` | `201e19545bf0c1ccc209ca017e4ed55c581085d15ceb1df117f31f7e36494101` |
| `production_ensemble_labels.csv` | `c454fb7bf3fcb4b29ed7b4ec3c4babbadde791af51b7f3e1ad8fd8751823d594` |
| `coverage_reviews.csv` | `db61c188c6ef1652f9551cf1cd554b2c0f9b00b5f2321550b6f3bde0de696876` |

> **更正记录（2026-10-31，用户现场核对出）**：本节原先声明「JSON 内载全量 64 位」，而生成脚本
> `_fpc_ruling_per_state_20261031.py:107-111` 实际写的是 `hexdigest()[:16]` —— **该声明与产物不符**，
> 属我对自有产物的虚假陈述。已改为写全量并重新生成；重跑后四项模拟值（28/14/15/14）**未漂移**。
> 逐条日志哈希与归档清单此前已是全量，不受影响。

**独立复核**：`work/_fpc_ruling_crosscheck_20261031.py` 以**不同代码路径**只读 JSON 的原始逐态字段、
自行重实现 R1/R2/R3 三条规则，四情形结果 28/14/15/14 **逐项一致，0 处分歧**；并证实
A 情形 17 = R1（无可使用成员）10 + R2（覆盖审反作弊失效）7。

| 态 | 例外成员(kept) | 非例外成员(kept) | 覆盖审 route/verdict | claim 存活 | A 掉 | B 掉 |
|---|---:|---:|---|---|---|---|
| AN\|M | 1 | 0 | — | — | **是** | **是** |
| DOL\|M | 1 | 0 | — | — | **是** | **是** |
| EC\|M | 1 | 0 | — | — | **是** | **是** |
| PC\|M | 1 | 0 | — | — | **是** | **是** |
| SL\|M | 1 | 0 | — | — | **是** | **是** |
| DOL\|LiM_plus | 1 | 0 | — | — | **是** | **是** |
| PC\|LiM_plus | 1 | 0 | — | — | **是** | **是** |
| SL\|LiM_plus | 1 | 0 | — | — | **是** | **是** |
| DMSO\|LiM_plus | 1 | 0 | single_basin_verified | **否** | **是** | **是** |
| DOL\|LiM_2plus | 1 | 0 | single_basin_verified | **否** | **是** | **是** |
| DEC\|M | 2 | 1 | multi_basin_coverage | **否** | **是** | **是** |
| DME\|LiM_2plus | 1 | 1 | multi_basin_coverage | **否** | **是** | **是** |
| DME\|M_plus | 2 | 1 | multi_basin_coverage | **否** | **是** | **是** |
| EMC\|M_plus | 1 | 1 | multi_basin_coverage | **否** | **是** | **是** |
| SL\|LiM_2plus | 1 | 1 | multi_basin_coverage | **否** | **是** | **是** |
| TMP\|LiM_plus | 2 | 1 | multi_basin_coverage | **否** | **是** | **是** |
| TMP\|M_plus | 1 | 2 | multi_basin_coverage | **否** | **是** | **是** |
| AN\|LiM_plus | 1 | 1 | — | — | | **是** |
| DEC\|LiM_plus | 1 | 1 | — | — | | **是** |
| DMC\|LiM_plus | 1 | 1 | — | — | | **是** |
| DME\|M | 2 | 1 | — | — | | **是** |
| DMSO\|LiM_2plus | 1 | 1 | — | — | | **是** |
| DOL\|M_plus | 1 | 1 | — | — | | **是** |
| EC\|M_plus | 1 | 1 | — | — | | **是** |
| EMC\|LiM_plus | 2 | 1 | — | — | | **是** |
| EMC\|M | 1 | 1 | — | — | | **是** |
| GBL\|LiM_2plus | 1 | 1 | — | — | | **是** |
| GBL\|M | 1 | 1 | — | — | | **是** |
| PC\|LiM_2plus | 1 | 1 | — | — | | **是** |
| SL\|M_plus | 1 | 1 | — | — | | **是** |
| DEC\|M_plus | 1 | 2 | — | — | | **是** |

（未列出的 accepted 态不含例外成员，不受本议题影响。）

**两类机制，务必分开**：
- **「无存活成员」10 态**：AN\|M、DOL\|M、EC\|M、PC\|M、SL\|M、DOL\|LiM_plus、PC\|LiM_plus、SL\|LiM_plus、DMSO\|LiM_plus、DOL\|LiM_2plus。
- **「成员还在、但覆盖审反作弊失效」7 态**：DEC\|M、DME\|LiM_2plus、DME\|M_plus、EMC\|M_plus、SL\|LiM_2plus、TMP\|LiM_plus、TMP\|M_plus。其 `multi_basin_coverage` 审所 claim 的成员本身就是例外成员 → 审失效；**即使态内仍有 primary 与其他 computed 成员**，也失去 accepted 依据。
- **合计 A 情形 = 17 态**（10 + 7，实测无 orphan 重复：去重头被剔而 `kept=false` 追随者成孤儿的情况为 0）。

---

## 3. 授权来源核验（三类严格分开，不得互替）

### 3.1 类别一：明确批准的协议
**无。** 全仓 `docs/**` 检索 `首点收敛|first.point.convergence|energy_change_absent|geometry_never_moved`，**不存在**任何批准「首点收敛可豁免能量判据」的裁定文档。

（已明确批准的是别的事，不得移用：五项阈值冻结、`search_exhausted` 非永久终局、DMC 本轮停止、EC/DMC 各 16 CH 独立额度、接收器 rev5 信任入口方案。）

### 3.2 类别二：代码自行实现的规则

```
685f8de  2026-10-21 08:11  week37-week44 增量收口（五十九）：WP2 生产首段登记 48/48 个主态
                          的真实 Opt+Freq 自由能标签
```
该提交同时引入 `energy_change_absent` 与 `first_point_convergence_geometry_never_moved`，且其自述生产口径为：

> 「生产口径：wB97X-D4 … SMD(acetonitrile)，**Opt NumFreq TightOpt TightSCF SlowConv** 在同一 ORCA 作业」

⇒ 引入例外的批次用的是 **TightOpt（默认阈值）**，**不是**冻结验收所依据的 **VeryTightOpt**。例外与现行阈值的绑定关系并非同时设立。

现行代码（tracked）：`scripts/wp_production/import_hpc_opt_numfreq.py` sha `f71fb93c47b9bc00…`（`:109-139` 判「四几何齐即完整」，`:153-162` 记 `energy_change_absent`）；`scripts/wp_production/import_ensemble_structures.py` sha `551c6244b6b40503…`（`:938-939` 转 `convergence_note`）；聚合器 sha `7f6dd47f5583dfaf…`（`acceptance_decision` 只认 `verdict==resolved`）。

### 3.3 类别三：仅存在于注释/文档的解释

| 载体 | 原文 | 性质 |
|---|---|---|
| `import_hpc_opt_numfreq.py:113-116`（docstring） | 「converges at the first check **without ever moving an atom** … Demanding all 15 entries there would reject the legs that need no work」 | **解释**，非裁定 |
| `ACCEPTANCE_CHAIN_AUDIT_20261024.md:12`（tracked，sha `d8694392f8fb102d…`） | 「**缺值不造数**：`Energy change` 行缺失时登记 `energy_change_absent`（首点即收敛、原子未动）；其它行缺失直接抛错」 | 定位为**数据卫生**，非验收豁免 |
| `CORE_PLAN_EXECUTION_SUPPLEMENT_20261029.md:148`（**未跟踪**） | 「TolE 用绝对值；**首点收敛或缺某列写 MISSING 并解释，不补零**、不拿上一任务段末值」 | 要求**登记缺口**，恰与「当作已满足」相反 |

⇒ **三类不可互替**：类别三的两条文字都只授权「记 MISSING、不造数」，**不授权**据此给出 accepted；类别二是一条实现规则，其自述前提（原子未动）已被第 5 节实测否定。

---

## 4. 统一处理选项及影响

模拟终点**不是一个数**，由两个未裁定选择共同决定（同一份输入，一次算全）：

| 情形 | D1 处置 | D2 primary 资格 | 塌陷态 | 模拟 accepted |
|---|---|---|---:|---:|
| **A** | 降级但不生新限制 | primary 算有效 | 17 | **28** |
| **B** | 降级即新限制 | primary 算有效 | 31 | **14** |
| **C** | 降级但不生新限制 | primary 须自带五项 | 30 | **15** |
| **D** | 降级即新限制 | primary 须自带五项 | 31 | **14** |

嵌套关系成立：A ⊆ B、A ⊆ C ⊆ D（塌陷集）；故 28 ≥ 15 ≥ 14。

| 选项 | 内容 | 适用范围 | 科学局限 | 下游影响 |
|---|---|---|---|---|
| **O1 保留历史协议标签** | 45/48 继续作为**历史协议**结果；例外成员标「能量项证据不完整」 | 全部 31 个受影响 accepted 态 | **不得**再据 45/48 称严格五项已证实；缺项仍是缺项 | 零翻转；WP3/WP5/WP6 与 `G_ens` 权重不动；限制报告须补「两条口径」段 |
| **O2 按严格证据重分类** | 依 D1/D2 裁定，逐态重判 | A→28 / B→14 / C→15 / D→14 | 重分类幅度取决于两个未裁定选择；若采 C/D 还牵出 **9 个与本议题无关的 primary-only 态**（须另行裁定，不得顺手并案） | 系综池、`G_ens`/权重、WP5 池 A/B、WP3 Top-3、WP6 触发条件全链重建；阶段性结题口径改写 |
| **O3 有界补证** | 见第 5.3 节**待补证候选清单**（按情形分列，非作业清单） | 情形相关的候选对象（A 内 26 / B·D 内 49 个成员） | 现有材料**补不出**「该步 ΔE 满足 2e-7」（5.2 已否定替代量）；要判只能重跑 | 新计算须逐次独立授权、新预算；不得动用已释放额度；**本文不提出任何申请** |

**不预设必须保住 45。** 但 O2 的任何数字在**独立复核 + 权威重建**（运行生成器）之前都只是模拟，**不得写入正式表**。

---

## 5. 最小补证清单（本轮不提交计算）

### 5.1 关键实测：例外的前提「原子未动」被否定

对带注记者的**自身 `computed` 日志**逐条解析（`work/_fpc_energy_semantics_20261031.py` → `.json`）：

| 检查 | 结果 |
|---|---|
| 带注记的行 | 58（其中 55 `status=computed`、3 `technical_complete_qc_failed`） |
| 观测到的优化循环数 | **全部 = 1**（无第二例外日志） |
| banner 前 `FINAL SINGLE POINT ENERGY` 条数 | 每条 = 2 |
| banner 前 `CARTESIAN COORDINATES` 块数 | 每条 = 2 |
| **首块与末块完全相同** | **0 / 55** ⇒ 几何确实改变了 |

⇒ `import_hpc_opt_numfreq.py` docstring 的「**without ever moving an atom**」与代码值 `first_point_convergence_geometry_never_moved` **与实际日志不符**：真实机制是「该作业只有 1 个几何评估步」，而非「未移动」。类别三的解释不能当裁定依据。

### 5.2 关键否定：现有能量差**不能**充当 TolE

零计算反证（`work/_fpc_rule_validation_20261031.py` → `.json`）：取**印有** `Energy change` 行的 **13 个非例外成员**，用「末两次 FSPE 之差」复现该行：

```
复现一致：0 / 13        复现不一致：13 / 13
例：TMP|M|27  印出 -1.486E-7   推得 1.355127E-6
    PC|M_plus|46 印出 6.27E-8   推得 3.432498E-6
```
⇒ 「末两次 FSPE 之差」**不是**冻结 `Energy change` 判据所量的东西。**禁止**用它补齐那 55 条。（即便 55 条中 4 条该差值恰 < 2e-7，也不得据此判通过。）

### 5.3 待补证候选清单（**按裁定情形分列，不是作业清单**）

> **更正记录（2026-10-31，用户指出原文过满）**：本节原写「真正需要新计算的只有 55 个成员／至多 10 个态」。
> 该表述有两处错：**55 只是带注记且 `computed` 的成员计数，不是经裁定的重算清单**；
> 7 个覆盖审失效态能否仅靠现有成员恢复**尚待逐态复核**，我当时并无依据断言。
> 现改为**候选清单**，且成员数随情形变动——不得据此申请任何作业。

实测分布：55 个带注记的 `computed` 成员散布在 **37 个态**；随情形不同，落在塌陷态内的成员数为

| 情形 | 塌陷态 | 其中带注记的 computed 成员 | 落在仍 accepted 态内（该情形下无需动作） |
|---|---:|---:|---:|
| A（降级、primary 算有效） | 17 | **26** | 29 |
| B（即新限制、primary 算有效） | 31 | **49** | 6 |
| C（降级、primary 须自带五项） | 30 | **47** | 8 |
| D（即新限制、primary 须自带五项） | 31 | **49** | 6 |

B 相对 A 多塌陷 14 态（`AN|LiM_plus`、`DEC|LiM_plus`、`DEC|M_plus`、`DMC|LiM_plus`、`DME|M`、`DMSO|LiM_2plus`、`DOL|M_plus`、`EC|M_plus`、`EMC|LiM_plus`、`EMC|M`、`GBL|LiM_2plus`、`GBL|M`、`PC|LiM_2plus`、`SL|M_plus`）——它们**只在 D1=「降级即新限制」时**才失格，是否需要补证完全取决于 D1。

**三类候选（按现有材料能否解决分列，逐类附实测依据）**：

| 类别 | 对象 | 缺什么 | 现有材料能否解决（**实测事实，非承诺**） | 若不能则属 |
|---|---|---|---|---|
| **(a) 仅登记/复核层** | 5 个「例外成员已被去重剔除」的态：`DMC\|M`、`DMSO\|M`、`DMSO\|M_plus`、`EC\|LiM_plus`、`GBL\|M_plus` | 无（不承重） | **能**：其承重证据本就是非例外成员 | 不需要 |
| **(a) 仅登记/复核层** | 3 个带注记但 `technical_complete_qc_failed` 的成员 | 无（未承重 accepted） | **能**：不参与 accepted 判定 | 不需要 |
| **(b) 重新出审可能解决，待逐态复核** | A 情形下「覆盖审反作弊失效」7 态 | 一个 claim 证据为可用成员的 resolved 审 | **未裁定**。实测：其中 **6 态**（`DEC\|M`、`DME\|LiM_2plus`、`DME\|M_plus`、`EMC\|M_plus`、`SL\|LiM_2plus`、`TMP\|LiM_plus`）剔除例外后**只剩 primary**，重新出审只能引 primary，而 primary 资格属 **D2 未裁事项**；仅 `TMP\|M_plus` 另有非例外成员 `TMP\|M_plus\|27` 可引 → **该 1 态最可能零计算解决，其余 6 态取决于 D2** | 视 D2 而定 |
| **(c) 现有日志不能解决，若要判只能重跑** | 带注记且 `computed` 的成员（情形 A 内 **26**、B/D 内 **49**） | 该步 `Energy Change` 的**打印值** | **不能**：5.1 证几何确有移动；5.2 证「末两次 FSPE 差」复现 **0/13** 不是冻结判据 ⇒ 无任何现有量可替代 | **候选重算**，须另行批准 |

**A 情形下「无任何可用成员」的 10 态**（若最终采 A/B 且走重算，则它们是最小闭环的候选对象）：
`AN|M`、`DOL|M`、`EC|M`、`PC|M`、`SL|M`、`DOL|LiM_plus`、`PC|LiM_plus`、`SL|LiM_plus`、`DMSO|LiM_plus`、`DOL|LiM_2plus`

**本清单不构成申请。** 在 D1、D2 裁定与 (b) 类逐态复核完成前，**不申请、不提交**任何补算作业；确需计算时也须独立预算与逐次授权（现有余额不构成授权）。

---

## 6. 归档与可复现（gitignored ≠ 可长期复现）

本文依赖的材料现全在 `work/`（`.gitignore:76 work/*`，实测 `git check-ignore` 命中）——**按项目纪律不得入库**，但**最终裁定依赖它**，故须由**指定写入者**纳入可追踪归档。清单如下（`sha256` 供核对，前 16 位）：

| 文件 | 用途 |
|---|---|
| `work/_fpc_reverify_20261030.py` / `work/_fpc_reverify_20261030.json` | 58 条逐条独立复核（绑定各日志 sha256） |
| `work/_fpc_state_sim_20261030.py` / `work/_fpc_state_sim_20261030.json` | 较早的 kept 池模拟（**其数字已被本文取代**，留痕用） |
| `work/_fpc_ruling_material_20261031.py` / `.json` | 情形矩阵初版（C/D 口径偏宽，见 1.3，留痕用） |
| **`work/_fpc_ruling_per_state_20261031.py` / `.json`** | **本文唯一权威计算** |
| `work/_fpc_energy_semantics_20261031.py` / `.json` | 循环数/块数/几何是否移动 |
| `work/_fpc_rule_validation_20261031.py` / `.json` | 替代 ΔE 的 0/13 反证 |
| `docs/handoffs/ec_submit_20261029/EC_FIRST_POINT_REVERIFY_20261030.md` | 复核报告 |
| `docs/handoffs/ec_submit_20261029/EC_FIRST_POINT_EXCEPTION_IMPACT_AUDIT_20261030.md` | 影响审计（含 45→11 初版推演，需按本文第 1 节更正） |
| `docs/handoffs/ec_submit_20261029/EC_FIRST_POINT_CONVERGENCE_REVIEW_20261030.md` | 补证方案审查 |

**建议**：由 rev5/统一裁定 Lead 一次性冻结上述文件哈希并纳入跟踪（`docs/` 下归档或迁入正式脚本目录时再守四处登记）。**本会话不代做该迁移**（写入面归属）。

**输入侧哈希**（本文所有数字的来路）：`production_ensemble_structures.csv 3f2c692d…`、`production_ensemble_weights.csv 201e1954…`、`production_ensemble_labels.csv c454fb7b…`、`coverage_reviews.csv db61c188…`；正式表**未写**。

---

## 7. 待裁定问题（仅 5 项）

1. **D1**：例外成员降级后，是否**产生新限制**（须 resolved 覆盖审覆盖）？——决定 28 vs 14。
2. **D2**：`status=ready` 的 primary 是否具备严格五项资格（该表内它也无 `Energy change`）？——注意会牵连 9 个**与本议题无关**的态。
3. **是否接受 O1 双口径长期并行**（历史协议 45/48 ＋ 严格证据另表登记），还是必须走 O2 重分类？
4. **7 个覆盖审失效态**可否走「重新出审、引用非例外成员」的零计算路径（5.3）？
5. **(c) 类候选**是否需要 O3 补算——数量随 D1/D2 而定（情形 A 内 26 个成员 / B·D 内 49 个），**本文不作申请**；若要，请给独立预算与逐次授权（现有余额不构成授权）。  
   附带：**(b) 类 7 态**中 6 态的可恢复性**取决于 D2**（剔除例外后只剩 primary），仅 `TMP|M_plus` 另有非例外成员 `TMP|M_plus|27` 可引——请一并裁定是否授权「逐态重新出审」这条零计算路径。
