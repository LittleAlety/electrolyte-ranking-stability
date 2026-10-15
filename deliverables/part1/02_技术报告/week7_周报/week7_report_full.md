# 15 Week 7 报告：Stage 7（ML / direct vs Δ-learning）+ Stage 8（active-learning replay）

本报告对应 `核心文件/ranking-electrolyte-materials-v2.md` §11–§14 与
`config/prereg.yaml` §5–§8。全部数字来自仓库内真实产物（`outputs/week7/*`），
可用 `outputs/figures/figure_manifest_week7_s7s8.md` 的 SHA256 逐字节核对。
本周不新增任何 DFT 计算；只消费 Stage 2–5 已有的 P0/P1/P2/C0/C1 结果。

---

## 1. 本轮解决的问题

1. **廉价描述符能不能学到「昂贵层」？** 把 P0→P1（方法）、P1→P2（环境）、C0→C1（配位）
   三步各自当成一个学习任务，比较 **直接学目标层** 与 **只学该步位移（Δ-learning）** 两种形态。
2. **随机划分会不会说谎？** 强制同一张表同时给出 random / group（家族|环系|F）/ LOFO
   （留一家族）三种拆分的指标，而不是只报最好看的那个。
3. **误差在「哪一类候选对」上翻转子次序？** 指标不只看 R² / MAE，而是
   `τ_b` / Top-k overlap / selection regret —— 决策导向而非拟合导向。
4. **要买多少次昂贵计算才能恢复目标排序？** 用 retrospective replay
   （把 core set 的完整标签重新藏起来）画出 `n_T → τ_b / O_k / R_k`。
5. **文献空白是否真的存在？** 见 §7 与 `docs/14_reading_list_qa.md` 的检索结果矩阵。

---

## 2. 特征表与 cost 分级（`scripts/build_ml_features.py`）

### 2.1 三级 cost（互相排斥，`prereg.yaml` §6）

| 级别 | 列数 | 需要什么才能拿到 | 列名 |
| --- | --- | --- | --- |
| `X0` | 12 | SMILES + 秒级 GFN2-xTB 单点 | `mw, donor_count, n_heavy, rotatable_bonds, tpsa, is_cyclic, has_fluorine, p0_ox_ev, p0_red_ev, hl_gap_ev, dipole_debye, aux_alpha_bohr3` |
| `X1` | 6 | 自由分子 DFT（P1/P2），**不含 Li** | `p1_ox_ev, p1_red_ev, p2_ox_ev, p2_red_ev, env_d_ox_ev, env_d_red_ev` |
| `X2` | 4 | 必须做完 Li 络合物 DFT | `x2_dgdg_bind_ev, x2_li_min_distance_a, x2_li_contacts_n, x2_motif_switch` |

**`X2` 是机制列，不是特征列。** `run_stage7_ml.py` 在 `run_matrix()` 入口对每个特征集做
`X2 ∩ features` 断言，一旦命中直接 `SystemExit`；`tests/test_stage7_ml.py` 用一个人造的
泄漏 manifest 把这个断言钉住。因此本仓库不可能出现「用 C1 衍生描述符证明可以低成本预测 C1」
的循环论证。

### 2.2 三条任务轴

| 任务 | 参照层 → 目标层 | 可用样本 | 丢弃的分子 |
| --- | --- | --- | --- |
| `M` 方法 | `P0` → `P1` | 18 | 无 |
| `E` 环境 | `P1` → `P2` | 18 | 无 |
| `C` 配位 | `C0` → `C1` | **10** | `EMC, DEC, PC, FEC, VC, TEGDME, EA, MA`（Week 5 未做 C1 的 8 个） |

两条筛选轴**分开报告**（v2 §4.1 禁止合并）：`ox = IP`、`red = −EA`，两者都是「越大越稳」。
`P0` 层按 Koopmans 存 `p0_ox = −ε_HOMO`、`p0_red = +ε_LUMO`；因此 `P1_red − P0_red`
在数值上等于底层 EA 修正的**相反数**——这是口径的后果，不是符号 bug，manifest 里已显式记录。

### 2.3 产物

- `outputs/week7/features_core.csv`（18 行 × 39 列）、`features_broad.csv`（40 行 × 17 列，只有 `X0`）。
- `outputs/week7/feature_manifest.json` / `.md`：cost 分级、任务定义、上游 10 个源文件的 SHA256。

---

## 3. Stage 7：三种拆分下的模型阶梯

### 3.1 为什么 LOFO 是主证据

`group` 与 `lofo` 都会把整个家族挡在训练集之外；`random` 会把同族分子同时放进训练与测试
（例如 EC / PC / FEC / VC 同属 `cyclic_carbonate`），于是模型可以靠「记住这个家族的样子」
刷分。v2 §13 把分族留出写成硬要求，原因就在这里。

### 3.2 LOFO 主表（`τ_b` 中位数，共 8 个组合 × 6 个模型 × 2 种形态）

| 任务 · 特征集 · 轴 | 最佳 direct | 最佳 shift | shift − direct |
| --- | --- | --- | --- |
| M · X0 · ox | `krr` 0.294 | `constant` **0.595** | **+0.301** |
| M · X0 · red | `rf` 0.359 | `constant` **0.556** | **+0.196** |
| E · X0+P1 · ox | `ridge` 0.843 | `rf` **0.922** | +0.078 |
| E · X0+P1 · red | `rf` 0.686 | `krr` **0.739** | +0.052 |
| C · X0 · ox | `krr` 0.111 | `krr` **0.644** | **+0.533** |
| C · X0 · red | `gbdt` **0.422** | `krr` 0.022 | **−0.400** |
| C · X0+X1 · ox | `ridge` 0.244 | `rf` **0.644** | **+0.400** |
| C · X0+X1 · red | `gbdt` **0.289** | `ridge` 0.200 | −0.089 |

**8 个组合里 6 个由 Δ-learning 胜出**，两个例外都出现在 `C` 任务的还原轴。
注意 `direct` 在 M 轴与 C 轴上的数值**可以低到 −0.7**（例如 `constant` + direct 的
M·ox = −0.725）：直接学目标层时，最低复杂度基线会给出**比随机排序还差**的次序，
因为它把「家族均值」当成了全局结构。完整阶梯（含 Top-20% overlap 与 20% regret）见
`outputs/week7/stage7_ml_summary.md` §2。

### 3.3 随机划分乐观了多少（含一个反例）

对每个组合取 LOFO 下 τ_b 最高的形态/模型，再读它在另一种拆分下的同一个组合：

| 任务 · 特征集 · 轴 | 选中组合 | random τ_b | group τ_b | LOFO τ_b | LOFO − random |
| --- | --- | --- | --- | --- | --- |
| M · X0 · ox | `constant` (shift) | 0.752 | 0.529 | 0.595 | **−0.157** |
| M · X0 · red | `constant` (shift) | 0.542 | 0.111 | 0.556 | +0.013 |
| E · X0+P1 · ox | `rf` (shift) | 0.935 | 0.922 | 0.922 | −0.013 |
| E · X0+P1 · red | `krr` (shift) | 0.725 | 0.673 | 0.739 | +0.013 |
| C · X0 · ox | `krr` (shift) | 0.733 | 0.600 | 0.644 | −0.089 |
| C · X0 · red | `gbdt` (direct) | 0.156 | 0.333 | 0.422 | **+0.267** |
| C · X0+X1 · ox | `rf` (shift) | 0.689 | 0.689 | 0.644 | −0.044 |
| C · X0+X1 · red | `gbdt` (direct) | 0.200 | 0.244 | 0.289 | +0.089 |

**结论必须写清楚，不能只挑顺手的说：**

- 在 `E` 轴上三种拆分几乎一致（差异 ≤ 0.013）——因为环境位移本身接近「平移」，不依赖家族身份。
- 在 `M` 轴与 `C` 氧化轴上，`random` 确实把成绩说高了 0.09–0.16。
- **但 `C · X0 · red` 是反例：`random`（0.156）显著低于 `LOFO`（0.422）。** 原因是该任务
  n = 10 且只有 8 个 LOFO 折，每折训练行数低到 2–9；随机划分把 10 个点切成 5 折后，
  每折只有 2 个测试点，τ_b 在小样本上极不稳定。**这条反例的作用是提醒：随机划分不只是
  乐观，它也可能是纯粹的噪声源。** 不能把 §3.3 简化成「random 永远偏高」。

### 3.4 模型复杂度阶梯

`constant → ridge → krr → gpr → rf → gbdt` 全部报告。按 `prereg.yaml` §8，
更高复杂度若不能超出不确定度地更好，就不得声称更优。在 LOFO 下：

- `constant`（家族均值，未知家族回落全局均值）在 M 轴与 C 轴上是**最强或接近最强**的 shift 模型；
- `rf` / `gbdt` 在 `E` 轴上取得最好值，但相对 `ridge` 的优势（0.843 → 0.922）与
  replicate 区间宽度同量级，**不足以声称复杂度更高一定更好**；
- `krr` 在 `C · X0 · ox` 上把 τ_b 从 0.111 拉到 0.644，是本轮唯一「高阶模型明显赢」的组合。

---

## 4. direct vs conditional-shift

### 4.1 结论

**Δ-learning 在这里不是技巧，而是与任务结构匹配的建模方式。** 三步位移的物理含义完全不同：
方法步是「同一分子换泛函/基组」的**系统偏移**，环境步是「同一分子加连续介质」的**近乎平移**，
配位步是「加一个 Li⁺」的**状态改变**。把它们当成「预测一个绝对值」来学，等于要求模型
重新发现整条 P0 尺度；改学位移则只需要发现一个低维修正。

- 位移的可学性排序：`C(配位) > M(方法) > E(环境)`（相对增益 +0.53 / +0.30 / +0.08）。
- 最戏剧化的一格是 `C · X0 · ox`：`constant` + shift 的 LOFO τ_b = 0.600，
  Top-20% overlap = **1.000**，regret = **0.000** —— 只用「可见分子的 ΔIP 均值」就能在
  留一家族条件下选出正确的 Top-2，而任何 direct 模型的 overlap 都是 0.000。

### 4.2 为什么 `constant` + shift 能赢

因为位移的**家族内一致性**很高：同一个家族里，加 Li⁺ 引起的 ΔIP 变化方向一致、幅度接近。
这时最稳的估计量就是「已知分子的位移均值」，任何高方差回归器在 n ≤ 18 的情况下都更容易过拟合。
这条结论本身就是 v2 §13 追求的「机制型结论」：**位移是可迁移的，绝对值不是。**

### 4.3 唯一的反转：`C` 还原轴

`C · X0 · red` 与 `C · X0+X1 · red` 上 direct 胜出（0.422 / 0.289 vs 0.022 / 0.200）。
机制上说得通：还原轴涉及「额外电子进入哪个轨道」，Li⁺ 配位会**改变接受电子的位置**
（C=O 的 π* 与 Li⁺ 的静电场竞争），位移因此不再是一个「平移量」而更像「换了一把尺子」。
这个解释与 Week 4 §3.3「还原侧定性失效」、Week 6 T9「并入 `δ_m` 后还原轴双方均解析的 pair 数归零」是同一现象的三种观测。

---

## 5. 位移的方差 vs 完整 target 的方差

把「学绝对值」换成「学位移」是否可行，取决于位移方差与目标方差的比：

| 任务 · 轴 | n | target pstdev (eV) | target 极差 (eV) | shift pstdev (eV) | shift 极差 (eV) | shift/target |
| --- | --- | --- | --- | --- | --- | --- |
| M · ox | 18 | 1.0345 | 4.545 | 0.7145 | 3.541 | 0.69 |
| M · red | 18 | 0.5376 | 2.233 | **2.1465** | 6.282 | **3.99** |
| E · ox | 18 | 0.8862 | 3.283 | 0.2933 | 1.262 | **0.33** |
| E · red | 18 | 0.4678 | 1.620 | 0.3114 | 1.293 | 0.67 |
| C · ox | 10 | 0.9985 | 3.238 | 0.5640 | 2.126 | 0.56 |
| C · red | 10 | 0.2609 | 0.825 | **0.7896** | 3.134 | **3.03** |

两个比值极端值解释了很多现象：

- `E · ox`：位移方差只有目标方差的 **1/3** —— 环境步接近纯平移，所以 `constant` + shift 的
  τ_b = 0.882，几乎追平最好的 `rf`（0.922），而 direct 的 `constant` 只有 −0.725。
- `M · red` 与 `C · red`：位移方差**大于**目标方差（3.99 / 3.03）。这说明在这两条轴上，
  「换个方法」或「加个 Li⁺」造成的重排比分子间的固有差异还大 —— **排序是被位移支配的，
  不是被绝对能级支配的**。也正因为如此，这两条轴上「位移」本身难学（它承载了主要方差），
  于是 §3.2 的反转恰好出现在 `C · red`。

---

## 6. Stage 8：最小昂贵信息预算

### 6.1 协议（`prereg.yaml` §7）

- 池 = core set 自身（18 个；`C` 任务 10 个）——v2 §14.2 的原话就是「core set 已有完整
  target labels 后，把它们暂时隐藏」。
- 初始种子 4 个、每次买 1 个、20 组冻结种子（`[101 … 2003]`，与 `prereg.yaml` §3 同一列表）；
  **同一 repeat 下四个 baseline 共用同一组初始种子**（`repeats_rule`）。
- 四个 baseline：`random` / `diversity`（标准化 `X0` 空间里离已标注集合最远）/
  `uncertainty`（GPR 后验标准差最大）/ `ranking_aware`（从 256 个后验样本估计
  `p_i = P(i ∈ Top-k)`，取二元熵 `H_i` 最大者）。
- **in-loop hygiene**：每轮的 `StandardScaler` 与 GPR 都只看当轮可见标签；
  `tests/test_stage8_al.py` 直接断言 `scaler.mean_ == X[visible].mean(axis=0)`。
- acquisition **只用 `X0`**；`X2` 严禁进入（否则就等于「先做昂贵计算再决定要不要做昂贵计算」）。
- 每轮排序 = 「已知标签用真值 + 未标注用模型预测」，因此 `n_T = n` 时 τ_b ≡ 1，
  这是**自检端点**而非成绩；图上不画。

### 6.2 `n_T → τ_b`（median，20 组种子，2.5–97.5 百分位带）

见 `outputs/figures/F17_stage8_active_learning.png` 与 `outputs/week7/stage8_al_curves.csv`。
代表性轨迹（`E · oxidation`，池 n = 18）：

| n_T | random | diversity | uncertainty | ranking_aware |
| --- | --- | --- | --- | --- |
| 4 | 0.265 | 0.265 | 0.265 | 0.265 |
| 8 | 0.462 | 0.560 | 0.542 | 0.448 |
| 12 | 0.686 | 0.752 | 0.804 | 0.712 |
| 16 | 0.948 | 0.974 | 0.974 | 0.974 |
| 17 | 0.974 | 0.974 | **1.000** | 0.987 |

### 6.3 预算表：median τ_b 首次达到 ≥ 0.80 所需的 `n_T`

| 任务 · 轴 | `random` | `diversity` | `uncertainty` | `ranking_aware` |
| --- | --- | --- | --- | --- |
| C · ox | 9 | **8** | **8** | 9 |
| C · red | 9 | 9 | 9 | 9 |
| E · ox | 15 | 14 | **12** | 13 |
| E · red | 14 | 13 | 13 | 13 |
| M · ox | 13 | 13 | **12** | 13 |
| M · red | 13 | 13 | 13 | 13 |

**可以说的：** 在 `E · ox` 上 `uncertainty` 比 `random` 早 3 个标签达到 τ_b ≥ 0.8
（12 vs 15，省 20%）；`C · ox` 上 `diversity` / `uncertainty` 比 `random` 早 1 个（8 vs 9）。
方向与 v2 §14.3 的预期一致：**信息量导向的 acquisition 在这个池子上不劣于随机，且在目标方差
被位移支配的那条轴上增益最大。**

**不能说的：** 见 §8 第 3、4 条。18/10 个点的池子上，曲线本身只有 15/7 个点，
20 组重复的百分位带很宽；把它换算成「真实项目要买多少张 DFT」是**不允许**的外推。

---

## 7. 与 Yang et al. 2025 的差异（本项目的 prior-art 立足点）

`docs/14_reading_list_qa.md` §4 对 6 篇文献做了逐词检索，命中次数矩阵如下（摘要）：

| 检索词 | Peljo 2018 | Marenich 2014 | Itkis 2021 | Borodin 2019 | Yang 2025 | Husch 2015 |
| --- | --- | --- | --- | --- | --- | --- |
| `inversion` / `invert` | 0 | 0 | 0 | 0 | **0** | 0 |
| `Top-k` / `Top-10` | 0 | 0 | 0 | 0 | **0** | 0 |
| `regret` | 0 | 0 | 0 | 0 | **0** | 0 |
| `Spearman` | 0 | 0 | 0 | 0 | **0** | 0 |
| `Kendall` | 0 | 0 | 0 | 0 | 0 | 7（只作相关系数 τ） |
| `leave-one` / `holdout` | 0 | 0 | 0 | 0 | **0** | 0 |
| `uncertaint*` | 0 | 4 | 1 | 0 | **0** | 0 |
| `famil*` | 0 | 0 | 0 | 0 | **0** | 0 |

据此，本项目的定位与 Yang 2025（最接近的先行工作）差异是**明确的**：

| 维度 | Yang et al. 2025 | 本项目 Stage 7/8 |
| --- | --- | --- |
| 目标 | 用 32 个描述符预测 140 个分子的氧化/还原电位 | 判断**误差何时改写筛选决策** |
| 划分 | 随机 8:2（单一划分） | random / group / **LOFO** 三种全报 |
| 指标 | R²（氧化 0.95 / 还原 0.90）、RMSE | `τ_b` / Top-k overlap / **selection regret** |
| 不确定度 | 全文 0 次 `uncertaint*` | 每个指标带 bootstrap 区间；Stage 8 用后验熵做 acquisition |
| 外推 | 未做分族留出 | LOFO 为主证据（§3.3 显示随机划分可偏差 ±0.27） |
| Li⁺ | 只取最稳定单一构型（无系综/无 Boltzmann 平均） | C1 用 motif 枚举 + 条件态；`X2` 被禁止进入特征集 |
| 预算 | 未回答 | `n_T → τ_b`（§6） |

必须承认的短板：Yang 的数据集（140 分子）比我们（18）大一个量级；他们的 R² 不能与我们的 τ_b 直接比较。
本项目的价值不在精度，而在**评估口径**与**决策相关性问题**。

---

## 8. 已知限制

1. **样本量是硬约束。** core 18（`C` 任务 10），LOFO 下训练行数常低至个位数。
   v2 §13.3 已经预警：要有基本统计力需要 **60–100 个 core points**。
   本报告的一切「模型 A 优于模型 B」都只在方法学层面成立。
2. **`C` 任务的 LOFO 折等价于单点外推**（8 个家族里 8 个被逐一留出，每折只剩 9 个点里更少的行）。
   §3.2 的 `C` 行只能读方向。
3. **Stage 8 的 acquisition 没有做不确定性校准。** v2 §14.3 明确要求「使用前检查
   uncertainty calibration」；在 18 个点上这**无法**可信地做。因此 §6.3 只能读成
   「排序行为的方向」，不能读成「uncertainty 采样的收益量」。
4. **不得把 Stage 8 的 `n_T` 外推成真实 DFT 预算。** 池子只有 18 个分子，
   且 `n_T = n` 的端点被构造成 τ_b ≡ 1。
5. **`_resolve_k` 的口径边界。** `prereg.yaml` §1 写的是 `k_abs = max(1, floor(frac·N+0.5))`，
   而 `src/electrolyte_ranking/ranking.py` 的 `_resolve_k` 用 `round(frac·N)`。
   在项目实际规模（core N = 18、broad N = 40）两者完全一致（`tests/test_stage7_ml.py`
   有一条断言钉住这一点）；但在 N = 5 时 10% 会退化为 k = 0。此为 Week 1–6 冻结代码的
   既有行为，本轮**未修改**，仅在此登记。
6. **`E` 轴的 `X0+P1` 特征集含 `p1_*`**，即环境任务允许使用 P1 层（自由分子 DFT）信息。
   这不是泄漏（P1 确实比 P2 便宜），但报告里不能把它说成「只用廉价描述符」。
7. **Gate 1 仍未关闭**：溶液相锚点 31 行仍为 `est`，本周所有结论只依赖气相锚点。
8. **Week 6 遗留**：`delta_m` 是否 append 进 `config/prereg.yaml` 仍待 PI 裁决；Gate 0 保持 CLOSED。

---

## 9. 复现命令

```powershell
cd "E:\Claude Code\电解液溶剂-HB\电解液溶剂HB-Code"
$env:PYTHONIOENCODING = "utf-8"

# Stage 7 特征表（18 行 core + 40 行 broad）
.venv\Scripts\python.exe scripts\build_ml_features.py

# Stage 7 ML 矩阵（约 25–35 分钟；288 行结果 / 9408 行 OOF 预测）
.venv\Scripts\python.exe scripts\run_stage7_ml.py

# Stage 8 AL replay（约 100 秒；5920 行 run / 296 行曲线 / 7360 行轨迹）
.venv\Scripts\python.exe scripts\run_stage8_al.py

# 图 F16 / F17 + 图清单
.venv\Scripts\python.exe scripts\make_stage7_figure.py

# 单元测试（基线 429 + 本轮新增 34 = 463）
.venv\Scripts\python.exe -m pytest tests -o addopts="" -q

# 交付包
.venv\Scripts\python.exe scripts\freeze_gates.py --stage all
.venv\Scripts\python.exe scripts\freeze_gates.py --stage 2
.venv\Scripts\python.exe scripts\build_deliverables.py --weeks 1,2,3,4,5,6,7 --force
```