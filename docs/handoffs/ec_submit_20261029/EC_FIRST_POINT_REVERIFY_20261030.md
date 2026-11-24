# 首点收敛例外：58 条独立复核

**日期**：2026-10-30  
**性质**：只读复核，绑定原始日志 sha256，**未改动任何正式产物**

**统一口径**：「历史协议记录 45/48 accepted；其中首点收敛例外的严格五项证据完整性正在复核。」

---

## 一、结论摘要（先看这里）

| 项 | 结果 |
|---|---|
| 58 条是否真首轮收敛 | **58/58 是**（仅 1 张收敛表、四项几何达标、容差为冻结值、HURRAY） |
| 58 条是否缺 `Energy change` | **58/58 缺** ⇒ `\|ΔE\| ≤ 2e-7` **无值可判** |
| 受影响状态（kept 池口径） | **31**（不是 34） |
| 若拒收后的 accepted | **45 → 14**（两种处置假设一致，**不是 11**） |
| 例外是否有用户批准记录 | **未找到**；定性为「缺值不造数」的数据卫生处理 |

---

## 二、集合关系澄清（三个数字不可相加）

| 集合 | 定义 | 数量 |
|---|---|---:|
| S1 | 有首点例外成员的状态 | **38** |
| S1a | S1 中 computed 成员全部为例外 | **34** |
| S1b | S1 中 computed 部分为例外 | **3**（DEC\|M_plus、TMP\|M、TMP\|M_plus） |
| S1c | S1 中无 computed 成员 | **1**（EC\|LiM_2plus，已 limited） |
| S2 | 保留非例外 computed 证据的状态 | **8** |

- `S1 = 34 + 3 + 1 = 38` ✅
- `S2 = S1b(3) + 无例外成员但有非例外 computed 的状态(5) = 8` ✅
- **S2 与 S1 不是包含关系**；34、8、38 三个口径**不可相加**。

---

## 三、逐态模拟重建（修正 45→11）

### 3.1 方法

1. 取**权威 kept 池**（`production_ensemble_weights.csv`，80 行），不从 structures 推断；
2. 剔除属于首点例外的 kept 成员，得「存活 kept」；
3. 套用**真实 `acceptance_decision` 逻辑** + coverage 反作弊（claimed 证据必须存活）。

### 3.2 修正：受影响状态是 31，不是 34

| 口径 | 数量 |
|---|---:|
| 结构表「computed 全为例外」 | 34 |
| **kept 池「kept 中有例外成员」** | **31** |

差异来自 5 个态的例外成员**已被去重剔除、从未进 kept 池**：
`DMC|M`、`DMSO|M`、`DMSO|M_plus`、`EC|LiM_plus`、`GBL|M_plus`（其 kept 仅 `primary`）。

### 3.3 两种处置假设（都给，不预判）

| 假设 | 含义 | accepted |
|---|---|---:|
| **S-A** | 例外成员＝可修复 strict-reopt 缺口（n_rescue>0 ⇒ unresolved>0） | 45 → **14**（provisional） |
| **S-B** | 例外成员＝终局限制（n_limited>0 且无 resolved 覆盖） | 45 → **14**（limited） |

**⇒ 两假设都收敛到 14。修正后：45 → 14（减少 31 态），不是 45 → 11。**

### 3.4 分类明细

| 类别 | 数量 | 说明 |
|---|---:|---|
| 剔除后**无存活 kept 成员** | **10** | 全部 kept 证据都来自例外成员 |
| 有存活成员但 **coverage 证据不存活** | **21** | claimed 证据本身是例外成员 ⇒ 反作弊失败 |
| coverage 证据存活 | **0** | — |

**无存活成员的 10 态**：`AN|M`、`DMSO|LiM_plus`、`DOL|LiM_2plus`、`DOL|LiM_plus`、`DOL|M`、`EC|M`、`PC|LiM_plus`、`PC|M`、`SL|LiM_plus`、`SL|M`

### 3.5 边界：`primary` 本身也没有能量证据

实测 `primary` 成员 **48/48 全部 `status=ready`、`energy_change_Eh` 为空**，不走本表五阈值门。
⇒ **「primary 存活」≠「primary 满足严格五项」**。若要求所有成员（含 primary）都有严格五项证据，受影响面可能扩大到全部 48 态——**这是尚未验证的独立问题**，不能与 31/34 混谈。

---

## 四、例外条款的授权来源（关键）

### 4.1 引入时点

`energy_change_absent` 与 `first_point_convergence_geometry_never_moved` 首次出现于同一提交：

```
685f8de  week37-week44 增量收口（五十九）：WP2 生产首段登记 48/48 个主态的真实 Opt+Freq 自由能标签
         2026-10-21 08:11:22 +0800
```

### 4.2 该提交记载的生产口径

> 「生产口径：wB97X-D4 … SMD(acetonitrile)，**Opt NumFreq TightOpt TightSCF SlowConv** 在同一 ORCA 作业」

**写的是 `TightOpt`，不是 `VeryTightOpt`。**

### 4.3 仓库内未找到「用户批准该例外」的记录

全仓 `docs/**` 检索 `首点收敛|first.point.convergence|energy_change_absent|geometry_never_moved`：
除本次报告外，只有 `ACCEPTANCE_CHAIN_AUDIT_20261024.md:12` 提及，定性为
**「缺值不造数」**（`Energy change` 行缺失时登记该标记）——**属数据卫生约定，不是科学例外批准**。

### 4.4 结论

**该例外目前只能认定为「实现自行添加的数据卫生处理」，不能认定为「用户明确批准的首点例外」。**
⇒ 历史获批协议的结果**保留版本身份**，但**不得冒充满足更严格的五项证据要求**。

---

## 五、可以确认 / 不能确认

### 可以确认
1. 58 条全部为**真首轮收敛**（单表、四项达标、冻结容差、HURRAY）。
2. 58 条全部**缺 `Energy change`** ⇒ `|ΔE| ≤ 2e-7` **无值可判**。
3. 若拒收，按 kept 池模拟 **accepted 45 → 14**（两种处置一致）。
4. 该例外**未见用户批准记录**，是实现层添加，定性「缺值不造数」。

### 不能确认
1. **不能**确认 45→11（已修正为 45→14）。
2. **不能**断言这些腿满足严格五项（能量项无值）。
3. **不能**断言 `primary` 满足严格五项（48/48 无 `energy_change_Eh`）。
4. **不能**断言 ORCA 无最少轮数控制（只能说「所查 6.0 文档未找到」；实际 6.1.1 待核）。
5. 模拟重建**≠**权威重建——权威结果需运行生成器（会写产物），本次**未运行**。

---

## 六、两条并行口径（此后固定）

| 口径 | 表述 | 边界 |
|---|---|---|
| **A：历史协议** | 「历史协议记录 **45/48 accepted**」 | 保留版本身份；**不得**宣称严格验收完成 |
| **B：严格五项** | 「严格五项证据下可确认的结果**待定**；首点收敛例外正在复核」 | **不得**凭未复核推演直接降到 14 |

**两条都不许越界**：不能为保住 45 而掩盖缺口，也不能凭未复核推演直接宣布降到 14。

---

## 七、本轮未做

- 未改动任何正式标签、未运行任何生成器 `--write`
- 未提交任何新计算
- 未批准 34 态补算
- DMC 接收器漏洞修复为并行任务，本文件未涉及

---

## 八、逐条原始结果（附日志 sha256）


## 汇总

| 检查 | 结果 |
|---|---:|
| 成员总数 | 58 |
| 日志可解析 | 58 |
| Q1 仅 1 个收敛表（真首轮收敛） | 58 |
| Q1 出现多个收敛表（**非**首轮收敛） | 0 |
| Q2 末表缺 `Energy change` | 58 |
| Q3 四项几何达冻结阈值 | 58 |
| Q3 回显容差 = 冻结值 | 58 |
| 日志含 `HURRAY` | 58 |

## 逐条结果

| 成员 | 状态 | 收敛表数 | 缺能量项 | 四项几何 | 容差一致 | HURRAY | 日志 sha256 |
|---|---|---:|---|---|---|---|---|
| EC|LiM_plus|c06 | computed | 1 | 是 | 过 | 一致 | 是 | `4cb64e4bd418b18a…` |
| DMSO|LiM_2plus|c01 | computed | 1 | 是 | 过 | 一致 | 是 | `53752db3692c1c26…` |
| DMC|M|8 | computed | 1 | 是 | 过 | 一致 | 是 | `04a96eea7904fbc0…` |
| EMC|M|14 | computed | 1 | 是 | 过 | 一致 | 是 | `31baf686a89bc434…` |
| DEC|M|13 | computed | 1 | 是 | 过 | 一致 | 是 | `c3939300800b7578…` |
| EC|M|63 | computed | 1 | 是 | 过 | 一致 | 是 | `09e8c19f90dc97ba…` |
| SL|M|16 | computed | 1 | 是 | 过 | 一致 | 是 | `3ab4cf51d60694c1…` |
| DMSO|M|50 | computed | 1 | 是 | 过 | 一致 | 是 | `c1b4598b7f79ca57…` |
| AN|M|34 | computed | 1 | 是 | 过 | 一致 | 是 | `631937351a795a5a…` |
| EMC|M|57 | computed | 1 | 是 | 过 | 一致 | 是 | `8e79507e9cdfc0d3…` |
| PC|M|25 | computed | 1 | 是 | 过 | 一致 | 是 | `4526b44ba28ef3ee…` |
| DME|M|14 | computed | 1 | 是 | 过 | 一致 | 是 | `a9bc256d0c52622b…` |
| DME|M|22 | computed | 1 | 是 | 过 | 一致 | 是 | `283ffa83f4c736a4…` |
| DOL|M|15 | computed | 1 | 是 | 过 | 一致 | 是 | `1cce8b1bd6c09226…` |
| GBL|M|2 | computed | 1 | 是 | 过 | 一致 | 是 | `87a85d1f3252c4ce…` |
| EMC|M_plus|21 | computed | 1 | 是 | 过 | 一致 | 是 | `fef80e6c638867db…` |
| DEC|M_plus|22 | computed | 1 | 是 | 过 | 一致 | 是 | `26588e46f20eaeec…` |
| EC|M_plus|0 | computed | 1 | 是 | 过 | 一致 | 是 | `745ea9b92cbfe843…` |
| DME|M_plus|23 | computed | 1 | 是 | 过 | 一致 | 是 | `81ac57701fc249d8…` |
| DOL|M_plus|40 | computed | 1 | 是 | 过 | 一致 | 是 | `e74185d793ebf6c5…` |
| DMSO|M_plus|20 | computed | 1 | 是 | 过 | 一致 | 是 | `4c9199f2690e966a…` |
| TMP|M|48 | computed | 1 | 是 | 过 | 一致 | 是 | `f633cc782e0f1af3…` |
| EMC|M_plus|4 | technical_complete_qc_failed | 1 | 是 | 过 | 一致 | 是 | `237efd5b948460df…` |
| GBL|M_plus|9 | computed | 1 | 是 | 过 | 一致 | 是 | `8968e16ab7e6c112…` |
| SL|M_plus|53 | computed | 1 | 是 | 过 | 一致 | 是 | `f49e3db40559cf36…` |
| DMC|LiM_plus|c05 | computed | 1 | 是 | 过 | 一致 | 是 | `93104fdc73645fd3…` |
| EMC|LiM_plus|c02 | computed | 1 | 是 | 过 | 一致 | 是 | `f1c192c517369ce2…` |
| EMC|LiM_plus|c08 | computed | 1 | 是 | 过 | 一致 | 是 | `428dce6582ab9f8b…` |
| DEC|LiM_plus|c09 | computed | 1 | 是 | 过 | 一致 | 是 | `e07e09189b08309c…` |
| PC|LiM_plus|c01 | computed | 1 | 是 | 过 | 一致 | 是 | `e2c263c83962c8d8…` |
| DOL|LiM_plus|c02 | computed | 1 | 是 | 过 | 一致 | 是 | `89cbaaf2704d09fc…` |
| SL|LiM_plus|c02 | computed | 1 | 是 | 过 | 一致 | 是 | `4a05d1df0d29ed7d…` |
| AN|LiM_plus|c01 | computed | 1 | 是 | 过 | 一致 | 是 | `9db6da3210ee298f…` |
| EC|LiM_2plus|c03 | technical_complete_qc_failed | 1 | 是 | 过 | 一致 | 是 | `4887d4ed7391cd18…` |
| PC|LiM_2plus|c04 | computed | 1 | 是 | 过 | 一致 | 是 | `22e4d11010992fbf…` |
| DOL|LiM_2plus|c05 | computed | 1 | 是 | 过 | 一致 | 是 | `984fa74170976b47…` |
| DOL|LiM_2plus|c01 | technical_complete_qc_failed | 1 | 是 | 过 | 一致 | 是 | `6a80a3e9455e4781…` |
| GBL|LiM_2plus|c04 | computed | 1 | 是 | 过 | 一致 | 是 | `724441d99b6ab5c0…` |
| SL|LiM_2plus|c02 | computed | 1 | 是 | 过 | 一致 | 是 | `ff2d2dbc2bc5db52…` |
| DME|M|39 | computed | 1 | 是 | 过 | 一致 | 是 | `a07e0d8f7dbc9a49…` |
| DME|M|5 | computed | 1 | 是 | 过 | 一致 | 是 | `d8b0db3e3cdb82fa…` |
| DEC|M_plus|23 | computed | 1 | 是 | 过 | 一致 | 是 | `05008a8ddb5e535e…` |
| DME|M_plus|46 | computed | 1 | 是 | 过 | 一致 | 是 | `905efb2100cc5dd9…` |
| DME|M_plus|55 | computed | 1 | 是 | 过 | 一致 | 是 | `e5bc61243e171c25…` |
| DEC|LiM_plus|r2_c23_c03 | computed | 1 | 是 | 过 | 一致 | 是 | `cc15f48172b6db13…` |
| DME|LiM_2plus|c05_c05 | computed | 1 | 是 | 过 | 一致 | 是 | `36b2eca677120872…` |
| EMC|LiM_plus|c14_c00 | computed | 1 | 是 | 过 | 一致 | 是 | `b7b7b5a9b6331e8b…` |
| EMC|LiM_plus|c14_c05 | computed | 1 | 是 | 过 | 一致 | 是 | `666de56033f4d978…` |
| DEC|M|r2_c23 | computed | 1 | 是 | 过 | 一致 | 是 | `d9ff402b21cb354f…` |
| DME|M_plus|c07 | computed | 1 | 是 | 过 | 一致 | 是 | `79c8180e50ec553c…` |
| DME|LiM_2plus|r3m_c05 | computed | 1 | 是 | 过 | 一致 | 是 | `e9877dcfafd492e8…` |
| SL|LiM_2plus|r3m_c00 | computed | 1 | 是 | 过 | 一致 | 是 | `cd3c2dc58b4e3741…` |
| SL|LiM_2plus|r3m_c01 | computed | 1 | 是 | 过 | 一致 | 是 | `6d8aba30452a5e2b…` |
| TMP|M_plus|r3_c42 | computed | 1 | 是 | 过 | 一致 | 是 | `b76ab94e3ad0eadb…` |
| DMSO|LiM_plus|r3m_c00 | computed | 1 | 是 | 过 | 一致 | 是 | `bd386540c01d240c…` |
| TMP|LiM_plus|r3m_c05 | computed | 1 | 是 | 过 | 一致 | 是 | `f11030aecbd581e4…` |
| TMP|LiM_plus|r3m_c08 | computed | 1 | 是 | 过 | 一致 | 是 | `7026ef7bab713266…` |
| DOL|LiM_2plus|p4_02_ring_pucker_twist | computed | 1 | 是 | 过 | 一致 | 是 | `56cb5e35c447192b…` |
