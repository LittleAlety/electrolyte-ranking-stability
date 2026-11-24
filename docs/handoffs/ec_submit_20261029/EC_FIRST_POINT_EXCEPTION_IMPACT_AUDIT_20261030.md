# 首点收敛例外：历史影响审计（零计算）

> **⚠ 2026-10-30 裁定（d）：先冻结标签、核验影响评估，再统一裁定**
>
> **本报告的 45→11 推演尚未经独立复核，不得作为结论引用，更不得据此改动任何正式标签。**
>
> 统一口径（此后对外一律使用）：
> **「历史协议记录 45/48 accepted；其中首点收敛例外的严格五项证据完整性正在复核。」**
> 暂停据此宣称严格验收完成。
>
> 两处推断已收紧：
> 1. **四舍五入后同为 0.0000 Å，不等于证据等价。** 重原子 RMSD 不能替代全原子位移、ORCA 内部坐标步长或能量判据。
> 2. **成员缺能量项，不必然意味着整个状态必须 limited。** 必须逐态重算其他有效成员、去重、覆盖条件及接受依据，才能确认 45→11。本报告第 3 节的集合关系需按下述澄清阅读。
>
> 本节以下内容为**初版推演**，保留备查；以 `EC_FIRST_POINT_REVERIFY_20261030.md`（独立复核）为准。

---


**日期**：2026-10-30
**性质**：只读审计，**正式表全部未改动**
**目的**：在统一裁定前，先暴露「若严格五项口径」会翻转哪些标签与下游结果
**裁定依据**：用户 2026-10-30 指示——「暂不溯及修改标签，先审计历史」「应做翻转影响评估，不能预先要求必须无翻转」

---

## 0. 一句话结论

**58 个历史成员、38 个状态使用首点收敛例外；其中 34 个状态的 computed 证据 100% 依赖该例外。**
**若严格拒收这些成员，系综将从 45 accepted / 3 limited 变为 11 accepted / 37 limited。**

---

## 1. 审计范围与方法

| 项 | 说明 |
|---|---|
| 数据源 | `outputs/physics_completion/ensembles/production_ensemble_structures.csv`（242 行） |
| 标签源 | `outputs/physics_completion/ensembles/production_ensemble_labels.csv` |
| 识别条件 | `convergence_note` 以 `first_point_convergence` 开头 |
| 位移字段 | `relaxation_heavy_rmsd_a`（= `heavy_rmsd()`，排除 H、**含 Li**、Kabsch 对齐，`%.4f` 存储） |
| 只读性 | 仅读 CSV，**未写任何产物、未改任何标签** |

---

## 2. 分布统计

### 2.1 规模

| 维度 | 数量 |
|---|---:|
| 使用例外的成员 | **58** |
| 涉及状态 | **38** |
| 其中 `status=computed` | 55 |
| 其中 `technical_complete_qc_failed` | 3 |

### 2.2 成员角色分布

| member_role | 数量 |
|---|---:|
| `round1_extra` | 39 |
| `recovery_v1_start` | 10 |
| `round2_audit_extra` | 9 |

### 2.3 能量项缺失情况

**58 / 58 的 `energy_change_Eh` 为空** —— 这正是例外的定义（ORCA 未打印该行）。

### 2.4 位移分布（项目自有口径）

| 统计 | 值 |
|---|---|
| 有值 | 58 / 58 |
| min | 0.0000 Å |
| median | 0.0000 Å |
| max | **0.0001 Å** |

> 注意：该字段为 4 位小数，`0.0000` 表示 < 5e-5 Å，不是严格零。

### 2.5 本次 3910076 用同一口径实测

用项目自身 `heavy_rmsd()`（排除 H、含 Li、Kabsch）计算：

```
3910076: heavy_rmsd = 3.22595e-05 A  ->  CSV 记录为 0.0000
```

**落在历史 58 条的同一区间内（0.0000–0.0001）**。

⇒ **按项目自有口径，3910076 与历史 58 条是同一现象**；无法只拒收 3910076 而保留那 58 条。

---

## 3. 影响评估（核心）

### 3.1 A 类：computed 证据 100% 依赖首点例外的状态（34 个）

这些状态**没有任何非例外的 computed 成员**；严格五项下将失去全部 computed 证据。

| 状态 | 当前标签 | 例外成员数 |
|---|---|---:|
| AN\|LiM_plus | accepted | 1 |
| AN\|M | accepted | 1 |
| DEC\|LiM_plus | accepted | 2 |
| DEC\|M | accepted | 2 |
| DMC\|LiM_plus | accepted | 1 |
| DMC\|M | accepted | 1 |
| DME\|LiM_2plus | accepted | 2 |
| DME\|M | accepted | 4 |
| DME\|M_plus | accepted | 4 |
| DMSO\|LiM_2plus | accepted | 1 |
| DMSO\|LiM_plus | accepted | 1 |
| DMSO\|M | accepted | 1 |
| DMSO\|M_plus | accepted | 1 |
| DOL\|LiM_2plus | accepted | 3 |
| DOL\|LiM_plus | accepted | 1 |
| DOL\|M | accepted | 1 |
| DOL\|M_plus | accepted | 1 |
| EC\|LiM_plus | accepted | 1 |
| EC\|M | accepted | 1 |
| EC\|M_plus | accepted | 1 |
| EMC\|LiM_plus | accepted | 4 |
| EMC\|M | accepted | 2 |
| EMC\|M_plus | accepted | 2 |
| GBL\|LiM_2plus | accepted | 1 |
| GBL\|M | accepted | 1 |
| GBL\|M_plus | accepted | 1 |
| PC\|LiM_2plus | accepted | 1 |
| PC\|LiM_plus | accepted | 1 |
| PC\|M | accepted | 1 |
| SL\|LiM_2plus | accepted | 3 |
| SL\|LiM_plus | accepted | 1 |
| SL\|M | accepted | 1 |
| SL\|M_plus | accepted | 1 |
| TMP\|LiM_plus | accepted | 2 |

### 3.2 B 类：部分成员为例外（3 个）

这些状态**仍有非例外的 computed 成员**，状态本身不一定失去全部证据，但成员数与权重会变。

| 状态 | 当前标签 | 例外成员 | 非例外 computed |
|---|---|---:|---:|
| DEC\|M_plus | accepted | 2 | 1 |
| TMP\|M | accepted | 1 | 1 |
| TMP\|M_plus | accepted | 1 | 1 |

### 3.3 C 类：严格五项下仍保留非例外 computed 证据的状态（8 个）

`AN|M_plus`、`DEC|LiM_2plus`、`DEC|M_plus`、`GBL|LiM_plus`、`PC|M_plus`、`TMP|LiM_2plus`、`TMP|M`、`TMP|M_plus`

> 注：这 8 个与 B 类有重叠（B 类 3 个均在此列）。合并去重后为 **8 个状态**。

### 3.4 汇总影响（**推演值，未经独立复核，不得作为结论**）

| 指标 | 当前 | 若严格拒收（推演） | 变化 |
|---|---:|---:|---:|
| accepted | **45** | **11** | **−34** |
| limited | 3 | **37** | **+34** |
| 分母 | 48 | 48 | 不变 |

**⚠ 该推演有两处必须收紧（2026-10-30 用户指出）**：
1. 「成员缺能量项」**不必然**导致整个状态 limited——须逐态重算其余有效成员、去重、覆盖条件与接受依据后才能确认。
2. 上表按「一个状态的全部 computed 都是例外成员」直接判其失去证据，**是简化推演**；真实结果需经模拟重建。

### 3.5 集合关系澄清（防止把三个数字直接相加）

| 集合 | 定义 | 数量 |
|---|---|---:|
| S1 | 有首点例外成员的状态 | **38** |
| S1a | S1 中 computed 成员全部为例外（`computed>0` 且 `other==0`） | **34** |
| S1b | S1 中 computed 部分为例外（`computed>0` 且 `other>0`） | **3** |
| S1c | S1 中无 computed 成员（EC\|LiM_2plus，已 limited） | **1** |
| S2 | 保留非例外 computed 证据的状态（`other>0`） | **8** |

**关系**：`S1 = S1a + S1b + S1c = 34 + 3 + 1 = 38` ✅
**S2 与 S1 不是包含关系**：`S2 = S1b(3) + 无例外成员但有非例外 computed 的状态(5) = 8`。
⇒ **34、8、38 是三个不同口径的集合，不可相加**。

---

## 4. 下游连锁影响（预估，未执行）

若 34 个状态转为 limited，以下下游结果**将随之失效或需重算**：

| 下游 | 影响 |
|---|---|
| `ensemble_not_48_accepted` 闸门 | 从「45/48」变为「11/48」，缺口急剧扩大 |
| `wp5_full_target_pool_evaluated` | 目标池 A/B 会因大量态非 accepted 而进一步缩小（当前 A=11/B=10） |
| WP3 阶梯 / accepted-only Top-3 | 池成员大幅减少，排序结果可能改变 |
| 系综 `G_ens` 与 Boltzmann 权重 | 每态成员数减少 ⇒ 权重与 `lowering_kcal` 改变 |
| WP6 触发条件 | 更不可能满足 |
| 阶段性结题口径 | 「45/48 阶段性交付」不再成立 |

**⇒ 这不是一次局部修正，而是会改变项目阶段性结论的系统性翻转。**

---

## 5. 审计发现的三个必须澄清的口径问题

### 5.1 「位移在阈值内」不能替代能量判据

如用户指出：位移达标只证明**步长**合格，**不能证明 |ΔE| ≤ 2e-7 Eh**。把位移当作能量项的豁免，实质是把「五项全过」改成「四项＋例外」。

### 5.2 两个位移口径不可直接互换

| 口径 | 定义 | 3910076 实测 | 对应阈值 |
|---|---|---|---|
| 全原子 max 位移 | 逐原子欧氏距离最大值（无对齐） | 9.487e-5 Å | TolMaxD = 1.058e-4 Å（0.896×） |
| 项目 `heavy_rmsd` | 排除 H、含 Li、Kabsch 对齐、RMS | 3.226e-5 Å | TolRMSD = 5.292e-5 Å（0.610×） |

两者坐标表示与 RMS 定义不同，**不能互相换算，也不能直接与 ORCA 优化器自报的步长比较**。
0.896× / 0.894× 只能作**辅助量级参考**，不构成等价性证明。

### 5.3 例外条款的字面表述与代码实现不完全一致

| 位置 | 表述 |
|---|---|
| `import_hpc_opt_numfreq.py:113-116`（文档串） | "converges at the first check **without ever moving an atom**" |
| 同文件 `:159-160`（代码值） | `"first_point_convergence_geometry_never_moved"` |
| 实测 58 条 | 位移 0.0000–0.0001 Å（**非严格零**，受 4 位小数截断影响） |

⇒ 文档与代码都声称「从未移动」，但实际数据是「位移极小但不保证为零」。**表述需要收紧为可验证判据，或明确承认它只是近似。**

---

## 6. 建议（供裁定，不含执行）

| 选项 | 内容 | 代价 | 风险 |
|---|---|---|---|
| **R1** | 维持现状：接受首点例外，仅要求四项几何 + 位移极小 | 0 | 等于承认能量判据在该情形不可得 |
| **R2** | 严格五项：拒收全部 58 条 | 0 计算，但 34 态翻 limited | 45→11，阶段性结论崩塌 |
| **R3** | 分级：对 A 类 34 态补证据（需新计算） | 大量算力 | 需独立预算与授权 |
| **R4** | 先澄清表述与判据（改文档/代码注释），暂不动标签 | 0 | 不解决证据缺口，只消除措辞歧义 |

**审计方立场**：本报告只提供影响面，**不主张任何选项**。按用户指示，正式表保持不动，待统一裁定。

---

## 7. 未做与不能做

- **未修改任何标签、未重算任何系综、未跑任何生成器 `--write`**
- **未提交任何新计算**
- 不能断言「该方法必然无法满足五项验收」——只能确认「首轮收敛情形下能量项无值可判」
- 不能断言 ORCA 不存在最少轮数控制——只能说「**所查 ORCA 6.0 文档未找到**」，实际运行版本 6.1.1 尚需核对对应版本资料

---

## 8. 证据路径

- 主表：`outputs/physics_completion/ensembles/production_ensemble_structures.csv`
- 标签：`outputs/physics_completion/ensembles/production_ensemble_labels.csv`
- 例外实现：`scripts/wp_production/import_hpc_opt_numfreq.py:109-118, 153-162`
- 位移字段实现：`scripts/wp_production/import_ensemble_structures.py:222-231, 997-999`
- 本次产物：`work/hpc_ec_strict_convergence_v1/tasks/EC/LiM_2plus__strict_convergence_p7/snapshots/3910076_0/`
