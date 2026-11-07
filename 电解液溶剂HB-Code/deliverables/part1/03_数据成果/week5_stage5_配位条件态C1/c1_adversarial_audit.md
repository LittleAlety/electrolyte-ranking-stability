> **归档说明（收尾时追加）**：本文是 2026-09-29 对 C1 分析层的对抗性审计原始记录，15 条发现（含 7 条显式「通过」）。文中所有 `文件:行号` 指向**审计当时**的版本；收尾期间该两个脚本又被修改过（见末节处置清单），行号可能已漂移。
> 本文件随交付包发布（`artifacts/`），作为 Stage 5 的科学 QC 证据。

# 审计报告 —— C1 数学/口径（`scripts/analyze_c1_coordination.py`、`scripts/make_c1_figure.py`）

只读审计，未修改任何被审脚本或产物。生成时间：2026-09-29。

## 0. 审计范围与基准原文摘录

**审计对象**
- `scripts/analyze_c1_coordination.py`（784 行，本文简称 analyze）
- `scripts/make_c1_figure.py`（293 行，本文简称 figure）

**对照基准（原文引用，带 文件:行号）**

`config/scientific_definitions.yaml` C1 条件态量与参考配体：
```
 94:   C1:
 95:     label: "Li+-coordinated conditional state"
 96:     species: "[LiM]+ 及其相应 redox states"
 98:     quantities:
 99:       dG_ox_free: "G(M+) - G(M)"
100:       dG_ox_Li: "G([LiM]2+) - G([LiM]+)"
101:       dG_red_free: "G(M-) - G(M)"
102:       dG_red_Li: "G([LiM]0) - G([LiM]+)"
103:       dGdG_ox_coord: "dG_ox_Li - dG_ox_free"
104:       dGdG_red_coord: "dG_red_Li - dG_red_free"
```

```
186:   exchange_reaction: "[LiR]+ + M -> [LiM]+ + R"
188:     symbol: dGdG_bind
189:     definition: "dGdG_bind(M;R) = G([LiM]+) + G(R) - G([LiR]+) - G(M)"
206:     definition: "dG_bind_abs = G([LiM]+) - G(Li+) - G(M)"
212:     policy: "可保留作辅助量, 但不作为核心 mechanistic truth"
```

`docs/08_stage2_production_protocol.md` §4/§5/§6：
```
102: - 能量换算的两个层级必须**分开报告**，不得混用：
103:   1. **电子能量近似**：dG ~ dE_SCF（无热校正）—— 廉价、全量；
105:   任何一个排序 / Top-k / inversion 统计内部，只允许出现同一层级的值。
115: | sigma_method | ... r2SCAN-3c 臂**已实测**（同子集 P0 -> P1 位移 std = 0.700 eV，dIP ... |
118: | sigma_env | CPCM eps = 5,10,20,40 的离散度 | **已实测**：dIP 0.191–0.229 eV ... |
121: **四个台阶在同一组分子上重算（2026-09-29，C1）**：`outputs/week5/c1_summary.json` 的
122: `four_step_sigma` 把 method / geometry / environment / coordination 四个单变量台阶都在 **C1 的同一
123: 10 个分子**上、用同一估计量（population std）算出，因此这四个数与本表 §3.4/§5 的 **12 分子子集**值
124: （如 sigma_geom dIP 0.049 eV）**不可直接并列**；其中 **environment 台阶是 SMD 位移**
125: （`IP(P2 SMD) - IP(P1@G1)`），**不是**本表的 `sigma_env`（bare CPCM `eps = 5/10/20/40` 的离散度）。
137: - Top-k：k = 10%/20%/30% ...
138: - 指标：O_k（重叠）、J_k（Jaccard）、selection regret、f_unresolved、f_robust_inv、tau_b。
140: - 条件态层次：C0（自由分子）-> C1（Li+ 配位）。C1 只做**机制解释** ...
```

`docs/10_week4_report.md` §2.1/§2.6（IP/EA 符号与适用域）：
```
 33: | 作业数 | 18 分子 × 3 态 = **54** |
 57: | `unbound_anion`（E(anion) > E(neutral)） | **18 / 18** |
166: | P1 r2SCAN-3c 垂直 EA（ΔSCF） | **−4.087** .. −1.854 eV | **0 / 18** |
170: 同一个量在两层的定性结论相反。
172: 按协议（`docs/08` §4、v2 §7.3），P1 侧记录为 `unbound_anion` 而不给一个虚构的 EA 数值；
191: - 与此形成对照，**氧化侧（IP）不受这个限制** ... **两轴的结论可信度不同，必须分开陈述。**
```

`config/prereg.yaml` 决策量定义：
```
 28:   absolute_k_rule: "k_abs = max(1, floor(frac * N + 0.5))  (四舍五入, 且至少为 1)"
 41:     - top_k_overlap: "O_k = |S_A(k) ∩ S_B(k)| / k"
 42:     - top_k_jaccard: "J_k = |S_A(k) ∩ S_B(k)| / |S_A(k) ∪ S_B(k)|"
 43:     - selection_regret: "R_k = mean_{i in S_T(k)} P_T(i) - mean_{i in S_M(k)} P_T(i)"
 74:     fraction: "f_robust_inv = N_robust_inversions / N_pairs_resolved_in_both"
 77:     formula: "f_unresolved = N_unresolved / C(N,2)"
 89:     primary: "Kendall tau_b (显式允许 ties/unresolved)"
149:     project_default: "oxidation 与 reduction 均为 maximize"
186:     - "Top-k overlap 与 Jaccard (k = 10% / 20% / 30%)"
187:     - "selection regret"
```

`docs/12_week5_report.md`（本轮自身报告，作为「声称」的对照）：
```
 22: 因此 C0 -> C1 的**唯一变量是化学状态**：自由分子 vs 与 Li+ 配位的同一个分子。
 26: - `IP(C1) = E([Li M]2+) - E([Li M]+)`，`EA(C1) = E([Li M]+) - E([Li M]0)`；
 28: 与 C0 侧的 `IP = E(M+) - E(M)`、`EA = E(M) - E(M-)` 逐字同构 ...
164: 3. **coordination 台阶与其它三个台阶不同基线**：C0 是中性分子，C1 的参考态是 `[Li M]+` 阳离子，因此
165:    `dIP_coord = IP([LiM]+ -> [LiM]2+) − IP(M -> M+)` 同时包含「配位场」与「参考态电荷态」两件事，
166:    其量级（约 +4 ~ +5 eV）**不可**与 σ_method / σ_geom / σ_env 直接比较，也不构成可加分解。
169: 6. **电子能量层**：全部 Δ 为 `dE_SCF` 层级（无 ZPE/热校正）；`dGdG_bind` 的符号是 G，实现值是 ΔE_SCF ...
170: 7. **还原侧的量纲陷阱**：... C1 的「EA」是**阳离子**接受一个电子，恒为正，二者不可混为一谈。
```

---

## 1. 发现表

| 编号 | 严重度 | 现象 | 证据（文件:行号 + 代码片段） | 建议 |
| --- | --- | --- | --- | --- |
| 1-P | 通过 | Q1：C0 与 C1 的 IP/EA 用**同一约定**，C0↔C1 之间没有符号翻反。C0 侧 `IP=E(M+)-E(M)`、`EA=E(M)-E(M-)`；C1 侧把参考态换成 `[LiM]+`，`IP=E([LiM]2+)-E([LiM]+)`、`EA=E([LiM]+)-E([LiM]0)`，二者同构，且 C1 的 EA 是阳离子接收电子、恒正 | `analyze_p1_core_set.py:214-215`（`ip_p1=(e_cation-e_neutral)*HARTREE_TO_EV` / `ea_p1=(e_neutral-e_anion)*HARTREE_TO_EV`）；`analyze_c1_coordination.py:220-221`（`ip = oxidised - cation` / `ea = cation - reduced`）；`:240-242`（`vertical_ip_ea(energies["cation_gas"], energies["dication_gas"], energies["reduced_gas"])`）；`docs/12:26-28`。实测 EC：`EA_C1 = E([LiEC]+) − E([LiEC]0) = +3.709 eV > 0`（`outputs/week5/c1_coord_shifts.csv`），`EA_C0 = −2.446 eV` | 无需改动；建议在报告里保留「两侧同构」这句 |
| 1-1 | F2 | Q1：C1 侧的 `d_ea` 与 config 冻结量 `dGdG_red_coord` **符号相反**。config 定义 `dG_red = G(还原态) − G(氧化态)`，故 `dGdG_red_coord = −(EA_C1 − EA_C0)`；而脚本/报告把 `d_ea = EA_C1 − EA_C0` 直接标成 `dGdG_red_coord`（§1 标题「dGdG_ox/red^coord」）。氧侧 `d_ip` 与 `dGdG_ox_coord` 同号，于是同一张表里 ox 与 red 相对冻结定义一正一负 | config `:101-104`；analyze 模块 docstring `:7-8`（"the ``dGdG_ox_coord`` / ``dGdG_red_coord`` table -- the C1 minus C0 shift of the vertical ionisation energy and electron affinity"）；`:266-273`（`d_ea_ev = ea_c1 - ea_c0`）；报告 `:513`（`## 1. dGdG_ox/red^coord`）。数值：EC 的 `d_ea = +6.155 eV`，而按冻结公式 `dGdG_red_coord = −6.155 eV` | 若该表意图是冻结量 `dGdG_red_coord`，red 列应取 `EA_C0 − EA_C1`（或加注「本列是 EA 位移，= −dGdG_red_coord」）；ox/red 两列必须统一到同一符号约定 |
| 2-P | 通过 | Q2：`four_step_sigma` 四个台阶的**实际表达式**与模块 docstring / `definition` 字符串**逐字一致**：method=`IP(P1@G1)-IP(P0@G1)`、geometry=`IP(P1@G2)-IP(P1@G1)`、environment=`IP(P2 SMD)-IP(P1@G1)`、coordination=`IP(C1)-IP(C0@G2)` | analyze `:37-40`（docstring 四台阶）对 `:429-436`（`add("method", ip_p1-ip_p0 ...)` / `add("geometry", d_ip_geom ...)` / `add("environment", ip_smd-ip_p1 ...)` / `add("coordination", d_ip_coord ...)`）；`:450-456`（definition 串） | 无需改动表达式；但见 2-1/2-2 |
| 2-1 | F1 | Q2/Q4：四台阶被当作「同一组分子」比较，但 **coordination 台阶实际只有 n=2**（10 个 primary 分子里只有 EC、AN 有完整的 `[LiM]2+/[LiM]0` 数据），method 的 EA 台阶只有 n=7；而 summary 与图**按 10 报**。`four_step_sigma.n_molecules = len(names) = 10`，figure (b) 直接印 "n = 10 molecules" | `outputs/week5/c1_summary.json`：`method ip n=10/ea n=7`、`coordination ip n=2/ea n=2`；analyze `:457`（`"n_molecules": len(names)`，names=全部 primary）、`:659-661`（`names = [row["name"] for row in primary]`）；report `:611`（`## 4. Four single-variable steps on the same molecules`）；figure `:146-148`（`"n = %d molecules\nsame estimator as week 4" % summary["n_molecules"]`）；`outputs/week5/c1_coord_shifts.csv` 中 DME/DOL/GBL/SL/DMSO/SN/TMP 的 `d_ip_ev` 为空 | 在四台阶表/图里**逐台阶打印 n**；coordination 与 n=10 的三台阶不得并列为一个「可比」家族；n 过小时标 n/a |
| 2-2 | F2 | Q2：模块 docstring 与 manifest 声称四台阶「literally comparable / one molecule set」，与冻结报告 `docs/12:164-166`（coordination「**不可**与 σ_method/σ_geom/σ_env 直接比较，也不构成可加分解」）**直接冲突**；`docs/08:121-125` 也要求不得与 12 分子子集并列 | analyze `:32-35`（"...so the four numbers in F12(b) are literally comparable"）；figure `:246-250`（"Panel (b) puts the coordination term next to the three terms week 4 measured, with one estimator and one molecule set."）；对照 `docs/12:164-166` | 图注/图内文字改为与 `docs/12` 一致：注明 coordination 混合了配位场与参考态电荷态、且目前 n=2，禁止直接比大小 |
| 2-3 | F2 | Q2：docstring 称 C0→C1「**唯一**变量是化学状态」，但几何基准也从自由分子 G2 变成 Li 复合物自身最优几何 G2Li；coordination 台阶 `IP(C1@G2Li)-IP(C0@G2)` 的减法里同时改了化学状态**与几何** | analyze `:23-27`（"C1 is r2SCAN-3c at the fully optimised Li-complex geometry ... The only thing that changes between the two columns is the chemical state"）；实现 `:436`（`add("coordination", d_ip_coord, d_ea_coord)`，其中 `d_ip_coord = ip_c1 - ip_c0`，`ip_c0` 来自 T2 的 G2）；`docs/12:19-20`（C1 几何 = G2_Li） | 表述改为「几何基准同时改变（G2→G2Li），coordination 量是条件态位移，不是单一变量位移」，或另列几何对照 |
| 2-4 | F2 | Q2：`environment` 台阶是 **SMD 位移**（`IP(P2 SMD)-IP(P1@G1)`），与 `docs/08 §5` 的 `sigma_env`（bare CPCM `eps=5/10/20/40` 的离散度）**同名不同量**；F12(b) 的柱标签写作 "environment (gas -> SMD AN) fixed continuum"，易被读成 `sigma_env` | analyze `:393-403`（`smd_ip_ea` 用 P2 SMD 的 neutral/cation/anion）、`:433-435`（`add("environment", ip_smd-ip_p1, ...)`）；figure `:53`（`STEP_LABEL["environment"] = "environment\n(gas -> SMD AN)\nfixed continuum"`）；对照 `docs/08:118` vs `:124-125` | 柱标签与图注写明「env = SMD 位移」且「≠ sigma_env（eps 扫描）」 |
| 2-5 | 通过 | Q2：代码**没有**把四个台阶相加、也没有声称「可加分解」——四台阶各自独立取 population std，只做并列展示 | analyze `:450-469`（仅 `population(values)`，无求和）；全文无 "additiv/可加/sum" 逻辑（`rg -i "additiv|可加" scripts docs config src` 无命中 analyze/figure） | 代码层面通过；文字层面见 2-2 |
| 3-P | 通过 | Q3：`dGdG_bind(M;R)` 实现与 config 公式**逐字一致**：`delta = (cation + reference_free) - (reference_cation + free)` = `G([LiM]+) + G(R) - G([LiR]+) - G(M)` | analyze `:360`（`delta = (cation + reference_free) - (reference_cation + free)`）、`:302-308` docstring、`:374-375`；config `:189`。数值复核 DME 参考、M=EC：`(-349.713276) + (-308.777456) - (-316.161192) - (-342.352336) = +59.85 kJ/mol`（`outputs/week5/c1_ligand_exchange.csv` 一致） | 无需改动 |
| 3-P2 | 通过 | Q3：自交换（M=R）**精确为 0**（构造上 `cation=reference_cation` 且 `free=reference_free`），且没有任何趋零容差/四舍五入掩盖；**未**使用裸绝对结合能（未出现 `dG_bind_abs`） | analyze `:360`；`outputs/week5/c1_ligand_exchange.csv`（DME 参考/DME、AN 参考/AN 的 `dGdG_bind_kj` 均为 `0`，status=ok）；报告 `:585-607`（self-exchange check `+0.000000`）；对照 config `:206-212`（绝对结合能不得作核心量） | 无需改动 |
| 3-1 | F3 | Q3：docstring 声称「自交换恒 0 是本模块在结尾 assert 的 sanity check」，但**全文没有任何 `assert`**（唯一的 "assert" 字样就在该 docstring 里） | analyze `:305-307`（"...which is the sanity check the module asserts at the end."）；`rg -n "assert" scripts/analyze_c1_coordination.py` 只命中 `:307` | 要么真的加一个自交换≈0 的断言/校验，要么删掉「asserts」措辞；实际自交换 0 由报告表给出 |
| 3-2 | F3 | Q3：交换表列名 `dG_bind_liM_eh` / `dG_bind_lir_eh` 装的是 `G([LiM]+)` / `G([LiR]+)` 的**原始电子能量**，不是「结合能」；与 config 里被禁止当核心量的 `dG_bind_abs` 字面相近，易误读 | analyze `:108-124`（EXCHANGE_COLUMNS）、`:349-352`（写入 `cation` / `reference_cation`）；config `:206-212` | 改名为 `g_liM_cation_eh` / `g_lir_cation_eh`（与已有 `g_R_eh` / `g_M_eh` 对齐） |
| 3-3 | F2 | Q3：`dGdG_bind` 符号是 G、单位 kJ/mol，但实现是 **ΔE_SCF**（电子能量近似，无 ZPE/热校正）；报告 §3 只印 mean/std，未标注层级 | analyze `:374-375`（`delta * HARTREE_TO_EV * EV_TO_KJ`，用 `final_energy_eh`）、`:583-607`（§3 表无层级注）；`docs/08:103`（允许 `dG~dE_SCF` 但必须标注层级）；`docs/12:169`（已承认） | 在 C1 报告 §3 与 CSV 头注明「ΔE_SCF 层级」；不改数值 |
| 4-P | 通过 | Q4：`kendall_tau_b_ci95` 用**真 bootstrap**（20 个冻结 seed × 2000 次 paired percentile），**不是**正态近似；样本不足时如实返回 `None`（`len(a) < 3` 即 None），报告据此打印 `[n/a, n/a]` | `analyze_p1_core_set.py:67-84`（`if len(a) < 3: return None`，否则 20 seed 循环 `uncertainty.bootstrap_tau_b_ci`）、`:406`（`"kendall_tau_b_ci95": tau_b_interval(...)`）；`uncertainty.py:117-158`（paired bootstrap，percentile）；`outputs/week5/c1_summary.json` 两轴 `"kendall_tau_b_ci95": null`；报告 `:563`。故 n=10（若成对齐全）会给出数值 CI，n<3 才 None——代码如实处理 | 无需改动；见 4-2（当前 n=2，CI 为 None 是正确行为，但不应把 tau_b 本身当结果） |
| 4-1 | F1 | Q4：**还原轴方向反了**。week4/prereg 的还原目标量是 `S_red = dG_red`（maximize），因此 week4 用 `p1_red = −EA` 且 `higher_is_better=True`；C1 却把**原始 EA** 传给 `layer_stability(..., higher_is_better=True)`，等价于「最大化 EA」＝挑最容易被还原的一端，Top-k/Jaccard/selection regret 的取向与 week4 相反 | week4：`analyze_p1_core_set.py:253`（`"p1_red_ev": -ea_p1`）、`:922-924`（`layer_stability([p0_red],[p1_red, higher_is_better=True])`）；C1：`analyze_c1_coordination.py:670-676`（`red = layer_stability([c0_g2[name]["ea_g2_ev"]...], [row["ea_c1_ev"]...], higher_is_better=True)`）；prereg `:142-145,149`（S_red = G(M-)−G(M)，maximize）。注：`tau_b` 对整体取负不变，故 `tau_b` 不受影响，但 `O_k/J_k/selection_regret` 受影响（当前 n=2/k=1 时两个取向恰好都给 O=0，全量 n=10 会不同） | 还原轴改用 `−EA`（与 week4 同向），或对该轴传 `higher_is_better=False`；否则「与 week4 直接可比」的声称只对 `tau_b` 成立 |
| 4-2 | F2 | Q4：C0↔C1 决策层的成对样本只有 **n=2**（只有 EC、AN 两轴齐全），`tau_b = 1.000 / −1.000` 是两点秩相关，`f_unresolved`、`f_robust_inv` 也在 n=2 上给出；但图/表/manifest **没有任何 n 或「仅 2 点」提示**，manifest 还把 `tau_b(ox) 1.0, tau_b(red) -1.0` 当结果印出 | `outputs/week5/c1_decision_stability.json`（`oxidation.n = 2`、`reduction.n = 2`；`kendall_tau_b = 1.0 / -1.0`）；analyze `:663-676`（`ox_labels` 过滤后只剩 EC/AN）；报告 `:556-580`（决策表无 n 列）；figure `:265-268`（manifest 直接串 tau_b / f_robust_inv） | 决策表/图/manifest 增列 n，并在 n<3（或 n 远小于名义 10）时显式标注「不构成排序结论」 |
| 4-3 | F2 | Q4：`selection regret`（prereg `must_report`，`docs/08 §6` 要求）**没有出现在 C1 报告**，也未进入 `c1_summary.json` 的 `decision_stability` 块；报告 §2 标题却称 "same frozen metrics as week 4"（week4 §2.4 表是含 selection regret 的） | analyze `:556`（决策表列头无 selection regret）；`:721-750`（summary 只拷贝 n/tau_b/ci/spearman/f_unresolved/f_robust_inv/sigma_median，**不含** `top_k`）；`layer_stability` 其实已算出 `top_k[k].selection_regret`（`analyze_p1_core_set.py:385`）；prereg `:43,187`；`docs/08:138` | 决策表补 selection regret 列（各 k），并把 `top_k` 一并写入 summary |
| 5-P | 通过 | Q5：F12 四个面板**确实**读取其声明的数据源，未见「编造数值」：(a) 读 `c1_coord_shifts.csv` + `c1_summary.json`；(c) 读 `c1_ligand_exchange.csv`；(d) 读 `c1_decision_stability.json`；(b) 读 `c1_summary.json.four_step_sigma` | figure `:31-40`（路径常量）；`main():281-285`（`summary←c1_summary.json`、`shifts←c1_coord_shifts.csv`、`exchange←c1_ligand_exchange.csv`、`stability←c1_decision_stability.json`）；`:93-97`(a)、`:129-131`(b)、`:150-158`(c)、`:177-191`(d) | 无需改动 |
| 5-1 | F1 | Q5：(a)/(c) 面板用 `number(x) or 0.0` 把**缺失值当成 0.0 画出来**。(a) 的 10 个 primary 里 8 个没有 `d_ip_ev`，于是画出 8 根标着 `+0.00` 的柱子，读起来像「配位位移为零」，而真相是「无数据」 | figure `:93-97`（`d_ip = [number(row["d_ip_ev"]) or 0.0 for row in primary]`、`d_ea = [number(row["d_ea_ev"]) or 0.0 ...]`）、`:104-109`（`bar_label(fmt="%+.2f")`）；`:157-158`（(c) 同样 `or 0.0`）；数据见 `outputs/week5/c1_coord_shifts.csv`（8 行 `d_ip_ev` 为空） | 缺失应画成 `None`/留空或灰色「n/a」条，绝不能填 0；区分「0 位移」与「无数据」 |
| 5-2 | F2 | Q5：(c) 面板把参考配体 `"DME"` **硬编码**过滤，而非从数据/摘要读 `reference_ligand`（若参考改成 AN，面板会静默变空）；(b) 注释印 `n = 10 molecules`（见 2-1）；(c) 还有 `n_robust` 默认 0.0 等硬编码兜底 | figure `:150-151`（`row["reference_ligand_name"] == "DME"`）、`:146-148`（n=10 文案）、`:206-208`（`n_robust = 0.0`） | 参考配体从 `summary`/CSV 读；n 逐台阶打印；去掉静默 `or 0.0` 兜底 |
| 5-3 | F3 | Q5：`make_c1_figure.py` **没有 CLI**，`FIGDIR/FIGNAME/MANIFEST` 是模块常量，`main()` 固定把 `FIGDIR` 传给 `build_figure`，因此**无法覆盖输出路径做预览**（`build_figure` 虽收 `outdir` 形参，但无入口传入）；manifest 还固定覆写仓库内文件 | figure `:38-40`（常量）、`:278-289`（`main` 无 `argv`；`:285` `build_figure(..., FIGDIR)`）、`:223-224`（`path = outdir / FIGNAME`）、`:274`（`MANIFEST.write_text`）；`rg -n "argparse" scripts/make_c1_figure.py` 无命中 | 加 `--outdir/--figname` 参数（默认不变），便于预览而不覆盖交付文件 |
| 5-4 | F3 | Q2/Q5：`method` 台阶的 IP 用 Koopmans P0（`ip_koopmans_ev`），EA 却用 xTB ΔSCF P0（`ea_xtb_dscf_ev`）——同一步里两个 P0 代理不同；report 只给 J_20% 而 prereg 要求 k=10/20/30 的 J | analyze `:409-412`（`ip_p0 = column(derived, name, "ip_koopmans_ev")` vs `ea_p0 = column(derived, name, "ea_xtb_dscf_ev")`）；report `:556`（仅 `J_20%`）；prereg `:186` | 注明两个 P0 代理不同；补 J_10/J_30（或说明与 week4 表格保持一致的取舍） |

---

## 2. 真缺陷 vs 风格问题

**真缺陷（会改变数值结论或与冻结定义冲突，必须处理）**
- **4-1（F1，最关键）**：还原轴把 `+EA` + `higher_is_better=True` 传给冻结实现，方向与 week4/prereg（`−EA`、S_red maximize）相反，Top-k/Jaccard/selection regret 的取向被翻转；「与 week4 直接可比」只在 `tau_b` 上成立。
- **5-1（F1）**：F12(a) 用 `or 0.0` 把 8/10 个缺失分子的 dIP/dEA 画成 `+0.00`，把「无数据」伪装成「零位移」，直接误导读图。
- **2-1（F1）**：四台阶把 coordination（实际 n=2，method-EA n=7）与 n=10 的其他台阶并列，并在图上写「n = 10」，比较结论（配位位移 vs 方法/几何/环境）建立在不成立的样本假设上。
- **1-1（F2，按冻结符号可升级为 F1）**：`d_ea` 与 config 的 `dGdG_red_coord` 符号相反，而报告 §1 直接把它标成 `dGdG_ox/red^coord`；同一张表 ox 同号、red 反号。
- **2-2（F2）**、**2-3（F2）**、**2-4（F2）**、**4-2（F2）**、**4-3（F2）**、**5-2（F2）**：图注/manifest 的「literally comparable / one molecule set」与 `docs/12:164-166` 冲突；「唯一变量是化学状态」忽略了 G2→G2Li 的几何变化；environment 台阶与 `sigma_env` 同名不同量；决策层 n=2 被当结果呈现；selection regret 缺失；图内硬编码 "DME"/n=10。

**风格问题（不改数值，但应统一）**
- **3-1（F3）**：docstring 声称「结尾 assert 自交换为 0」，实际无 `assert`。
- **3-2（F3）**：CSV 列名 `dG_bind_liM_eh` / `dG_bind_lir_eh` 装的是阳离子电子能量、并非结合能。
- **3-3（F2/F3）**：`dGdG_bind` 名为 G、实为 `ΔE_SCF`，报告 §3 未标层级（`docs/12:169` 已承认，属回填问题）。
- **5-3（F3）**：figure 无 CLI、输出路径不可覆盖。
- **5-4（F3）**：method 台阶 IP 用 Koopmans、EA 用 xTB ΔSCF 的代理不一致；J 只报 20%。

**总体**：IP/EA 符号在 C0↔C1 之间自洽（1-P 通过）、`four_step_sigma` 四台阶表达式与注释逐字一致（2-P 通过、且无可加分解声明 2-5）、`dGdG_bind` 与 config 公式逐字一致且自交换精确为 0（3-P/3-P2 通过）、`kendall_tau_b_ci95` 用真 bootstrap 且 n<3 如实返回 None（4-P 通过）、四面板确读声明数据源（5-P 通过）。需要动手的核心是 **4-1、5-1、2-1** 三条 F1，以及 **1-1** 的符号口径。

---

## 3. 收尾处置清单（2026-09-29 收尾时追加）

审计提到的每一条真缺陷都已处置；处置方式与证据如下。另列**两条审计之后才发现的缺陷**。

### 3.1 审计发现的真缺陷

| 编号 | 严重度 | 处置 | 证据 |
| --- | --- | --- | --- |
| **4-1** | F1 | **已修**。还原决策层不再把原始 `+EA` 交给 `higher_is_better=True`：新增 `reduction_axis()`，把 EA 映射为冻结尺度 `S_red = dG_red = -EA`，`main()` 的氧化/还原两层都改由它构造。氧化侧仍是 `+IP`，与 `analyze_p1_core_set.py:253` 的 `p1_red_ev = -ea` 同源。 | `scripts/analyze_c1_coordination.py` 的 `reduction_axis()` / `c0_axis()`；回归测试 `tests/test_c1_li_coordination.py::test_reduction_axis_uses_minus_ea_so_the_ranking_is_not_inverted` 与 `::test_c1_reduction_decision_layer_uses_the_frozen_minus_ea_scale`（后者用 raw `overlap=0.0` vs frozen `overlap=1.0` 钉住 Top-k 家族，并显式断言 τ_b 对共同变号不敏感） |
| **5-1** | F1 | **已修**。面板 (a)/(c)/(d) 不再用 `or 0.0` 把缺失值画成 0：新增 `as_float()`/`fmt_bar()`/`is_missing()`，缺失映射为 `NaN` + 刻度标签 `(n/a)`，真实 `0.0` 仍保留（修掉 `or` 把 `0.0` 当缺失的旧 bug）。 | `scripts/make_c1_figure.py`（`as_float` / `fmt_bar` / NaN 柱 + `(n/a)` 轴标签 + 图例说明） |
| **2-1** | F1 | **已修**。四台阶逐台阶打印可用 n：报告 §4 表新增 `n(dIP)` / `n(dEA)` 两列；图 (b) 每根柱标 `n=…`，标题改为「同一清单、同一估计量，但各台阶可用 n 可不同」。 | `scripts/analyze_c1_coordination.py` 的报告 §4；`scripts/make_c1_figure.py` 面板 (b) |
| **1-1** | F2 | **已修**。报告 §1 明确写成 `dEA = EA(C1) − EA(C0)`，并写明冻结量 `dGdG_red_coord` 是它的**负值**、不得挂 `dGdG_red_coord` 的名字；模块 docstring 口径同步更正。 | `scripts/analyze_c1_coordination.py` 模块 docstring 与 `write_report` §1 |
| **2-2 / 2-3 / 2-4** | F2 | **已修（表述层）**。docstring / 图注 / manifest 不再声称四台阶「literally comparable」或「唯一变量是化学状态」：改为「同一清单、同一估计量、**只有离散度尺度可比**、基线不可加」，并写明 coordination 台阶**同时**改变了化学状态与几何（G2 → G2_Li），environment 台阶是 SMD 位移、**不是** `docs/08` §5 的 `sigma_env`（CPCM eps 扫描）。 | `scripts/analyze_c1_coordination.py` 模块 docstring；`scripts/make_c1_figure.py` 模块 docstring 与面板 (b) 说明 |
| **5-2** | F2 | **已修**。面板 (c) 的参考配体改为从数据读（`stability["reference_ligand"]`，兼容 mol_id 或分子名），不再硬编码 `"DME"`；找不到时在图上写明并跳过柱子。 | `scripts/make_c1_figure.py` 面板 (c) |
| **3-1** | F3 | **已修**。`ligand_exchange_rows` 的 docstring 不再声称「模块结尾 assert 自交换为 0」；自交换 0 由报告 §3 的 `self-exchange check` 列逐行给出。 | `scripts/analyze_c1_coordination.py` |
| **3-2** | F3 | **已修**。交换表列名 `dG_bind_liM_eh` / `dG_bind_lir_eh` 改为 `g_liM_cation_eh` / `g_lir_cation_eh`，与既有 `g_R_eh` / `g_M_eh` 对齐：这两列装的是 `G([LiM]+)` / `G([LiR]+)` 的**原始电子能量**，不是结合能，更不是被 config 禁止当核心量的 `dG_bind_abs`。 | `scripts/analyze_c1_coordination.py` 的 `EXCHANGE_COLUMNS` 与两处写入点 |
| **3-3** | F2/F3 | **已修**。报告 §3 顶部新增能量层级说明：实现值是 **dE_SCF**（无 ZPE/热校正，`docs/08` §4 允许但要求标注），写成 G 只是沿用冻结定义的符号。 | `scripts/analyze_c1_coordination.py` 的报告 §3 |
| **5-3** | F3 | **已修**。`make_c1_figure.py` 新增 CLI：`--summary / --shifts / --exchange / --stability / --outdir / --figure-name / --manifest`，默认值即原常量，因此可以在不覆盖交付文件的前提下出预览图。 | `scripts/make_c1_figure.py` 的 `build_arg_parser()` / `main(argv)` |
| **5-4** | F3 | **已修（报数）+ 已注明（代理差异）**。报告 §2 现在同时给 `J_10% / J_20% / J_30%`（prereg 要求 k = 10/20/30）；「method 台阶的 IP 用 Koopmans P0、EA 用 xTB ΔSCF P0，两个 P0 代理不同」已写入 `docs/12` §2.2/§2.6，不再让读者以为是一个代理。 | `scripts/analyze_c1_coordination.py` 的报告 §2；`docs/12_week5_report.md` §2.2/§2.6 |

### 3.2 审计之后才发现的缺陷（补充）

| 编号 | 严重度 | 现象 | 处置 |
| --- | --- | --- | --- |
| **A-1** | F1 | **分析层在真实数据上直接崩溃**。`outputs/week4/t2_opt_freq.csv` 是文本读入，`main()` 把 `c0_g2[name]["ea_g2_ev"]` 这个 **字符串** 直接交给 `reduction_axis`，触发 `TypeError: bad operand type for unary -: 'str'`；氧化侧则把字符串交给 `layer_stability`，会按**字典序**排序。审计（含其 7 条「通过」）都是用**内存里的 float** 调函数，所以整条链路在单测里全绿、在真数据上必崩。 | **已修**：新增 `c0_axis()` 作为唯一边界做 `_float` 强转，`main()` 的氧化/还原两层都改用它；`reduction_axis()` 自身也改为经 `_float` 处理。回归测试 `test_c0_axis_coerces_the_text_csv_into_floats` 与 `test_c0_axis_keeps_the_numeric_order_that_text_sorting_would_break`。发现方式：用真实 92 行 CSV 做离线冒烟测试。 |
| **A-2** | F1（数据） | **一个 C1 数值被污染的 scratch 密度毁掉**。`run_orca` 复用 `<stem>_scratch` 目录，上一次被中断的运行会留下同名 `.gbw`；ORCA 把同名 `.gbw` 当作初始猜测读取，于是 `SN_m1_reduced_sp` 的 SCF 收敛到「**23 个电子而非 45 个**」（`WARNING: LOEWDIN FINDS 23.0000000 ELECTRONS INSTEAD OF 45`），能量 −126.81 Ha（应为约 −271.6 Ha），而且 `ORCA TERMINATED NORMALLY`、`scf_converged=True`，因此被记为 `status=ok`，直接污染了 SN 的 `EA_C1`（−3939.68 eV）。 | **双重修复**：(1) 根因——`run_orca` 现在**总是先清空 scratch 目录**再运行，杜绝陈旧 `.gbw` 进入猜测；(2) 护栏——新增 QC 旗标 `electron_count_mismatch`（`provenance.QC_FLAGS` 已扩展并注明理由），从此这类「正常终止但电子数不对」的作业不再与好作业无法区分。回归测试 `test_run_orca_clears_a_stale_density_left_in_the_scratch_directory` 与 `test_parse_orca_output_flags_a_wrong_electron_count`。发现方式：分析结果里 `delta_ea` 均值出现 −387.7 eV 的离群值，逐 `.out` 扫描确认 4 个文件带 `Old DensityContainer` 警告、其中 1 个真的塌缩。受污染的作业已用修复后的代码重跑。 |

### 3.3 审计中「通过」项的处理

7 条通过项（1-P、2-P、2-5、3-P、3-P2、4-P、5-P）无需改动，保留在本文第 1 节作为证据。
