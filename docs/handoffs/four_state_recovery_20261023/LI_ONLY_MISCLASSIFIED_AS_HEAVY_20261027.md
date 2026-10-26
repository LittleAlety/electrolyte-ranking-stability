# 权威门把「纯 Li 位移」误分类为 `ok_heavy_fragment`（2026-10-27，**待裁定缺陷**）

> **⚠ 本文更正我方上一轮的结论（`4e0fa6c`）。**
> 我上轮报告两个 DOL/EC 起点「**重骨架 RMSD 0.1675 / 0.2098（非塌缩）**」——
> **实测：纯骨架 RMSD = 0.0000，那两个数字全部来自 Li 位移（0.45 / 0.60 Å）。**
> **该判断错误，已撤回。** 本文给出机制、影响范围与处置建议。**纯只读，不改门、不改 verdict。**

## 1. 事实（每步实测）

| 起点 | 含 Li 的「重原子」RMSD | **纯骨架 RMSD（排除 H 与 Li）** | **Li 位移** |
|---|---|---|---|
| `DOL\|LiM_2plus li_coordination_away_01` | 0.1675 | **0.0000** | **0.45 Å** |
| `EC\|LiM_2plus li_coordination_away_02` | 0.2098 | **0.0000** | **0.60 Å** |

门的返回：

| 起点 | `declared_li_change` | 门判定 | `heavy_pair_change_a` | `pair_distance_change_a` |
|---|---|---|---|---|
| DOL | **False** | **`ok_heavy_fragment`** | **0.4500** | 0.4500 |
| EC | **False** | **`ok_heavy_fragment`** | **0.5999** | 0.5999 |

⇒ **`heavy_pair_change_a` 完全等于 `pair_distance_change_a`**，且**纯骨架 RMSD 为 0** ⇒
**这两个「重骨架扭转变体」实际上只是 Li 被平移了**。

## 2. 机制（代码级根因）

`build_torsion_probe_package.py` 里有两个不同的「重原子」概念：

| 位置 | 定义 | 是否含 Li |
|---|---|---|
| **`:322`** `heavy = [i for i, s in enumerate(symbols) if s != "H"]` | **按质量** | **含 Li** ✅ |
| **`:407`** `non_li_heavy = [... if s != "H" and s != "Li"]` | **按共价骨架** | **不含 Li** ✅ |

⇒ **`:407` 的注释本身就说明了正确概念**：
> 「*Li is a heavy atom by mass, **but not part of the covalent skeleton***」

**但 `non_li_heavy` 只在 `declared_li_change=True` 分支被使用**（`:406-416`）。
**当 `declared_li_change=False` 时**，分类走的是 `heavy_change`（`:322-325`，**含 Li**）⇒
**纯 Li 位移会把 `heavy_change` 顶上去**，于是被判为 `ok_heavy_fragment`（`probe_class: heavy_fragment_torsion`）。

## 3. 影响范围（实测）

本轮的 **28 条复评**里，25 条被判 `ok_heavy_fragment`。**其中有多少条是「纯 Li 位移」需逐条区分**
（即 `heavy_pair_change_a == pair_distance_change_a` 且纯骨架变化 ~0）：
- **已确认**：我选出的 **2 条 DOL/EC 起点都属于这一类**（纯骨架 RMSD 0.0000）；
- **未逐条核**：其余 23 条（**含 DMC 的 3 条**）尚未区分——**本文不下结论**。

> **不影响的部分**：这**不改变**「28 条证据已登记」这件事，也**不改变**任何已发布的 verdict；
> 它只影响**「哪些探针有资格当独立起点」**这一判断。

## 4. 处置建议（**不自行执行**）

| # | 建议 | 理由 |
|---|---|---|
| 1 | **撤回**我上轮给的 DOL/EC 起点推荐（`away_01` / `away_02`） | 实测纯骨架 0.0000，**不是骨架独立起点** |
| 2 | **逐条复评 28 条**，用「**纯骨架**（排除 Li）变化」重新分类，输出真正的合格起点清单 | 这是**唯一**能回答「有没有合格起点」的方式 |
| 3 | 是否修门（让 `heavy_change` 也用 `non_li_heavy`）**须你裁定** | 改门会影响**历史分类**（且可能翻转既有判定）——按项目纪律须先做**无翻转证明** |
| 4 | 若「纯骨架合格起点」数量很少或为 0 ⇒ 回到用户裁定的第 2 步选项：**新开筛选批次**（须版本化重分配） | 这才是「找不到独立起点」时的正路 |

**⚠ 我不擅自动手的两个原因**：
① 改 `validate_candidate_start` 会**改写历史分类语义**（P4/v2 的建包期判定都基于它）；
② 用户裁定的第 2 步明确要求「**经过非刚体与身份预检的独立起点**」——
**这道门当前的 `ok_heavy_fragment` 并不足以证明这一点**，需要先把这个口径问题交给你。

## 5. 我的判断（供参考）

**倾向**：**先做第 2 项（逐条复评，纯骨架口径）**——它零成本、只读，且**直接决定**「是否必须新开筛选批次」。
**不做第 3 项（改门）**，除非你要求：因为一旦改门，**P4/v2 的历史分类与已登记证据的口径都会变**，
那时需要一整套**无翻转证明 + 版本化**流程。

## 6. 守线

- ⛔ 不改 `validate_candidate_start`；
- ⛔ 不改任何已发布 verdict / 已登记证据；
- ⛔ 不把「纯 Li 位移」的起点**当成**骨架独立起点去提交生产（那会白烧 512 额度）；
- ⛔ 不改 `heavy_array`（它是聚合器共用原语，被多处依赖）。

## 7. 证据出处

- 门与两套「重原子」定义：`build_torsion_probe_package.py:322`（含 Li）、`:407`（不含 Li）
- 实测：`work/_screening_probe_regate.py` 的复评 + 本轮纯骨架/含 Li 对照（`kabsch_rmsd`）
- 含 Li 的 `heavy_array`：`build_production_ensemble_aggregator.py::heavy_array`（`s != "H"`）
- 被更正的我方结论：`4e0fa6c`（`DOL_EC_PRODUCTION_COVERAGE_PLAN_20261027.md §2.1`）