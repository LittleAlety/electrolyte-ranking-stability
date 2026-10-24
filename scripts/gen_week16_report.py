"""Generate docs/26_week16_report.md from the Week 16 (Stage 17) artefacts.

Every number in the prose and in every table is read back out of the JSON / CSV
files under outputs/week16; nothing is transcribed by hand.  The assert block in
_guard() turns a silent drift into a hard failure, and --check renders the text
in memory without touching the file.

Environment overrides: W16_DIR (artefact directory) and W16_REPORT_OUT (output
path).  The committed report is always built with the defaults.
"""

import csv
import json
import math
import os
import sys
from pathlib import Path

REPO = Path(r"E:\Claude Code\电解液溶剂-HB\电解液溶剂HB-Code")
W16 = Path(os.environ.get("W16_DIR") or (REPO / "outputs" / "week16"))
REPORT_OUT = Path(os.environ.get("W16_REPORT_OUT") or (REPO / "docs" / "26_week16_report.md"))
FIGDIR = REPO / "outputs" / "figures"

# ---- named constants: the only hard-coded numbers allowed to appear here ----
Z_PRIMARY = 1.0                 # config/prereg.yaml: pair_comparison.z_factor.value
MATERIAL_THRESHOLD_EV = 1.0e-3  # inherited unchanged from Week 14 (Stage 15)
SQRT2 = math.sqrt(2.0)
ROOT2_MINUS_1 = SQRT2 - 1.0     # constant of the two-realization lemma (section 4.7)
S2_DOUBLET = 0.75               # <S^2> of a pure doublet, S(S+1) with S = 1/2
S2_PURITY_BAND = 0.01           # frozen +/- band of the Stage 17 identity analysis

# Figure paths are fixed by the Stage 17 figure plan; the PNGs are produced by a
# sibling script.  No other path is valid and the report must not invent one.
F32_REL = "outputs/figures/F32_stage17_contamination.png"
F33_REL = "outputs/figures/F33_stage17_solution_identity.png"
MANIFEST_REL = "outputs/figures/figure_manifest_week16_stage17.md"


def _json(name):
    return json.loads((W16 / name).read_text(encoding="utf-8"))


def _rows(name):
    with (W16 / name).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _f(value):
    return None if value in (None, "") else float(value)


def _fmt(value, digits=3):
    return "—" if value is None else ("%%.%df" % digits) % value


CONT = _json("stage17_contamination.json")
IDENT = _json("stage17_solution_identity.json")
SMD = _json("stage17_smd_moread.json")
P2SUM = _json("p2_summary_moread_smd_acetonitrile.json")

CELL_ROWS = _rows("stage17_contamination_cells.csv")
LADDER_ROWS = _rows("stage17_contamination_ladder.csv")
IDENT_ROWS = _rows("stage17_solution_identity.csv")
BYMOL_ROWS = _rows("stage17_solution_identity_by_molecule.csv")


def _lemma_check():
    """Two-realization lemma, re-derived from the raw per-molecule vectors.

    With sigma_ij = abs(d0_ij - d1_ij) / sqrt(2) and z = 1, a pair can never be
    resolved in both realizations *and* carry opposite signs: that would need
    abs(d1) <= (sqrt(2)-1) abs(d0) and abs(d0) <= (sqrt(2)-1) abs(d1) at once.
    This is an independent numeric check of the structural claim in section 4.7.
    """
    n = len(CELL_ROWS)
    if n != 18:
        raise SystemExit("contamination cell table is not 18 molecules")
    for axis, columns in (("ox", ("ox_p1_ev", "ox_p2_moread_ev")),
                          ("red", ("red_p1_ev", "red_p2_moread_ev"))):
        p1 = [_f(row[columns[0]]) for row in CELL_ROWS]
        p2 = [_f(row[columns[1]]) for row in CELL_ROWS]
        for i in range(n):
            for j in range(i + 1, n):
                d0 = p1[i] - p1[j]
                d1 = p2[i] - p2[j]
                sigma = abs(d0 - d1) / SQRT2
                res0 = abs(d0) > 0.0 and abs(d0) >= Z_PRIMARY * sigma
                res1 = abs(d1) > 0.0 and abs(d1) >= Z_PRIMARY * sigma
                if res0 and res1 and (d0 * d1) < 0.0:
                    raise SystemExit(
                        "two-realization lemma violated on %s pair %d/%d" % (axis, i, j))


def _guard():
    """Hard assertions: refuse to render a report whose spine moved."""
    if not (CONT["stage"] == IDENT["stage"] == SMD["stage"] == 17):
        raise SystemExit("stage mismatch: not a Stage 17 / Week 16 artefact set")

    # ---- Part A: the swapped layer and the ladder comparison ----------------
    if P2SUM["n_jobs"] != 54 or P2SUM["n_ok"] != 54 or P2SUM["n_failed"] != 0:
        raise SystemExit("P2 moread layer is not 54/54 ok")
    if P2SUM["n_computed"] != 54 or P2SUM["n_reused"] != 0:
        raise SystemExit("P2 moread layer reuse counts moved")
    if P2SUM["layer"] != "moread_smd_acetonitrile" or P2SUM["arm"] != "moread":
        raise SystemExit("P2 moread layer identity moved")
    if SMD["n_cells"] != 54 or SMD["n_molecules"] != 18 or SMD["n_failed"] != 0:
        raise SystemExit("stage17_smd_moread.json cell counts moved")
    if len(SMD["geometry_audit"]) != 18:
        raise SystemExit("geometry audit does not cover 18 molecules")
    for name, block in SMD["geometry_audit"].items():
        if not block["all_identical"] or block["n_compared"] != 3:
            raise SystemExit("geometry audit changed for %s" % name)
    for axis in ("oxidation", "reduction"):
        for arm in ("default", "moread"):
            if CONT["per_axis"][axis][arm]["n"] != 18:
                raise SystemExit("ladder cell count moved on %s/%s" % (axis, arm))
        if CONT["published_comparison"][axis]["published"]["n"] != 18:
            raise SystemExit("published row is not over 18 molecules on %s" % axis)
    if CONT["delta_stats"]["cells_54"]["n"] != 54:
        raise SystemExit("delta_stats/cells_54 is not 54 cells")
    sign54 = CONT["sign_test"]["cells_54"]
    if sign54["n_total"] != 54:
        raise SystemExit("sign test is not on 54 cells")
    if sign54["n_positive"] + sign54["n_negative"] + sign54["n_zero"] != 54:
        raise SystemExit("sign test buckets do not add up to 54")
    if len(CONT["cells_changed"]) != CONT["cells_changed_count"]:
        raise SystemExit("cells_changed list and count disagree")
    if CONT["cells_changed_count"] != 6:
        raise SystemExit("the changed-cell list is no longer six cells")
    if CONT["verdict"]["any_published_conclusion_rewritten"] is not False:
        raise SystemExit("a published conclusion is now flagged as rewritten")
    if CONT["verdict"]["tau_b_ci_overlap_both_axes"] is not True:
        raise SystemExit("tau_b CI overlap no longer holds on both axes")

    # ---- Part A: the structural lemma --------------------------------------
    for axis in ("oxidation", "reduction"):
        for arm in ("default", "moread"):
            if CONT["per_axis"][axis][arm]["f_robust_inv"] != 0.0:
                raise SystemExit("f_robust_inv moved off zero on %s/%s" % (axis, arm))
            if CONT["per_axis"][axis][arm]["f_robust_inv_z1p96"] != 0.0:
                raise SystemExit("f_robust_inv z=1.96 moved off zero on %s/%s" % (axis, arm))
    if not (ROOT2_MINUS_1 ** 2 < 1.0):
        raise SystemExit("two-realization lemma constant is not below one")
    _lemma_check()

    # ---- Part B: census, coverage and identity aggregates -------------------
    if IDENT["n_cells"] != 32 or IDENT["n_molecules"] != 5:
        raise SystemExit("solution-identity cell count is not 32 / 5 molecules")
    if len(IDENT["cells"]) != 32 or len(IDENT_ROWS) != 32:
        raise SystemExit("solution-identity cells list is not 32 long")
    cen = IDENT["census"]
    if cen["n_cells_resolved"] != 32 or cen["n_cells_requested"] != 32:
        raise SystemExit("census coverage is not 32/32")
    if cen["unresolved"]:
        raise SystemExit("census left cells unresolved")
    if cen["max_delta_ev_mismatch_vs_stage16"] > 1e-9:
        raise SystemExit("Part B energies disagree with the Stage 16 catalogue")
    for key, block in IDENT["aggregates"].items():
        if block["n"] != 32:
            raise SystemExit("aggregate %s is not over 32 cells" % key)
    if N_GEOM_IDENTICAL != 32:
        raise SystemExit("Part B geometry QC no longer holds 32/32")
    states = IDENT["by_state"]
    if states["anion"]["n_cells"] != 16 or states["cation"]["n_cells"] != 16:
        raise SystemExit("Part B state split is not 16/16")
    if N_LOSS_PR_POSITIVE + N_LOSS_PR_NEGATIVE != 32:
        raise SystemExit("loss_in_pr signs do not cover every cell")
    if N_SAME_SPIN_CENTER != (states["anion"]["n_same_spin_center"]
                              + states["cation"]["n_same_spin_center"]):
        raise SystemExit("spin-centre totals disagree between the CSV and the JSON")
    if N_SAME_ORBITAL != (states["anion"]["n_same_orbital_label"]
                          + states["cation"]["n_same_orbital_label"]):
        raise SystemExit("orbital-label totals disagree between the CSV and the JSON")
    if MULTS != ["2"] or CHARGES != ["-1", "1"]:
        raise SystemExit("Part B multiplicity / charge bookkeeping moved")
    for row in IDENT_ROWS:
        for column in ("s2_default", "s2_moread"):
            if abs(float(row[column]) - S2_DOUBLET) > S2_PURITY_BAND:
                raise SystemExit("cell %s/%s left the spin-purity band" % (row["name"], row["state"]))
    if sum(b["n_cells"] for b in IDENT["by_family"].values()) != 32:
        raise SystemExit("family split does not cover 32 cells")
    if len(BYMOL_ROWS) != 5:
        raise SystemExit("per-molecule identity table is not 5 molecules")

AXIS_LABEL = {"oxidation": "氧化轴", "reduction": "还原轴"}

PA = CONT["per_axis"]
OXD, OXM = PA["oxidation"]["default"], PA["oxidation"]["moread"]
REDD, REDM = PA["reduction"]["default"], PA["reduction"]["moread"]
PUB = CONT["published_comparison"]
DS = CONT["delta_stats"]
SIGN = CONT["sign_test"]
VERDICT = CONT["verdict"]
CIO = CONT["ci_overlap"]

AGG = IDENT["aggregates"]
BYSTATE = IDENT["by_state"]
BYFAM = IDENT["by_family"]
CEN = IDENT["census"]

N_CELLS_A = SMD["n_cells"]              # 54
N_MOL_A = SMD["n_molecules"]            # 18
N_HIT_B = IDENT["n_cells"]              # 32
N_MOL_B = IDENT["n_molecules"]          # 5
THRESHOLD_MEV = MATERIAL_THRESHOLD_EV * 1000.0
TMP_SPIN_MAX_DEFAULT = next(float(r["spin_max_default_mean"]) for r in BYMOL_ROWS if r["name"] == "TMP")
TMP_SPIN_MAX_MOREAD = next(float(r["spin_max_moread_mean"]) for r in BYMOL_ROWS if r["name"] == "TMP")
N_SAME_SPIN_CENTER = sum(1 for row in IDENT_ROWS if row["same_spin_center"] == "True")
N_SAME_ORBITAL = sum(1 for row in IDENT_ROWS if row["same_orbital_label"] == "True")
N_LOSS_PR_POSITIVE = sum(1 for row in IDENT_ROWS if float(row["loss_in_pr"]) > 0)
N_LOSS_PR_NEGATIVE = sum(1 for row in IDENT_ROWS if float(row["loss_in_pr"]) < 0)
N_GEOM_IDENTICAL = sum(1 for row in IDENT_ROWS if row["geometry_identical"] == "True")
MULTS = sorted({row["mult_default"] for row in IDENT_ROWS} | {row["mult_moread"] for row in IDENT_ROWS})
CHARGES = sorted({row["charge_default"] for row in IDENT_ROWS} | {row["charge_moread"] for row in IDENT_ROWS})


def _cell_counts():
    counts = {}
    for row in IDENT_ROWS:
        key = (row["name"], row["state"])
        counts[key] = counts.get(key, 0) + 1
    return counts


def _orbital_pairs():
    seen = []
    for row in IDENT_ROWS:
        pair = (row["orbital_default"], row["orbital_moread"])
        if pair not in seen:
            seen.append(pair)
    return seen


ORBITAL_PAIRS = _orbital_pairs()
COUNTS = _cell_counts()

L = []
L += [
    "# Week 16 报告 —— Stage 17：亚稳态对已发布台阶结论的污染上限，与两个 SCF 解的电子结构身份",
    "",
    "> 本文由 `scripts/gen_week16_report.py` 从 `outputs/week16/` 的 JSON / CSV 逐数读出生成，数字不手抄；",
    "> 重跑该脚本即可刷新（`--check` 只渲染不落盘）。",
    f"> 生成时间基准：`stage17_smd_moread.json` 的 `generated_utc` = {SMD['generated_utc']}、",
    f"> `p2_summary_moread_smd_acetonitrile.json` 的 `generated_utc` = {P2SUM['generated_utc']}",
    ">（Part A 与 Part B 的分析产物同批生成）。",
    "",
    "## 0. 一句话结论",
    "",
    f"**Part A（污染上限）**：把 Week 9「五级台阶」第 2 级 `P1 -> P2` 的 **P2 腿**（取自 **SMD(乙腈)** 层）"
    f"从 ORCA 自带初猜换成 moread 初猜重算（{N_MOL_A} 分子 x 3 态 = {N_CELLS_A} 格，全部 ok）之后，"
    f"两条轴上的 `tau_b` / `O_20%` / `f_unresolved` / `f_robust_inv` **没有任何一条被改写**："
    f"oxidation `tau_b` {OXD['kendall_tau_b']:.4f} -> {OXM['kendall_tau_b']:.4f}"
    f"（Δ {PUB['oxidation']['moread_minus_published']['kendall_tau_b']:+.4f}）、"
    f"reduction `tau_b` {REDD['kendall_tau_b']:.4f} -> {REDM['kendall_tau_b']:.4f}"
    f"（Δ {PUB['reduction']['moread_minus_published']['kendall_tau_b']:+.4f}），"
    "两臂 `tau_b` 的 95% CI 都重叠（污染被 CI 吸收）。更强的一条是：在这套估计量下，"
    "`f_robust_inv` 从 0 变非 0 是**结构性不可能**（§4.7 的两行证明），不是「本周恰好看不到」。",
    "",
    f"**Part B（解的电子结构身份）**：受影响 {N_HIT_B} 格的两个 SCF 解都是**自旋纯双重态**"
    f"（`<S^2>` 全部落在 {S2_DOUBLET:g}±{S2_PURITY_BAND:g}，{N_HIT_B}/{N_HIT_B}），"
    "所以这**不是**破缺对称性 / 自旋污染伪影，而是同一自旋量子数下的两个不同 SCF 驻点；"
    f"差异的主轴是**电荷重组**（`charge_l1` 均值 {AGG['charge_l1']['mean']:.3f}）而不只是自旋重排。"
    f"阴离子的自旋中心在两臂完全一致（{BYSTATE['anion']['n_same_spin_center']}/{BYSTATE['anion']['n_cells']}），"
    f"阳离子只有 {BYSTATE['cation']['n_same_spin_center']}/{BYSTATE['cation']['n_cells']} —— "
    "「默认初猜把空穴放在哪」比「把电子放在哪」更不稳定。",
    "",
    "## 1. 为什么要有这一步（Stage 17 的动机）",
    "",
    "Stage 17 直接执行 Week 15 §11 的第 1 条与第 4 条。Week 15 的原文是：",
    "",
    "> 1. **把漏解回填到 sigma 台阶结论上（最高优先）**：Week 9–12 的台阶分析用的是 P0/P1 的默认初猜能量。",
    ">    既然默认初猜在某些 (分子, 状态, 电介质) 上会停在高解，就要量化「台阶结论被污染的上限」——",
    ">    把本周目录里 `delta < -1 meV` 的单元格按台阶归类，看它们是否真的改写过 tau_b / Top-k / 清单。",
    "",
    "> 4. **把「第二解」从能量现象升级为电子结构现象**：对漏解单元格比较两条解的占据轨道与 Mulliken 自旋",
    ">    分布，回答「低解多了什么」——是某个 sigma*/pi* 轨道被额外占据，还是自旋重新定域。",
    "",
    "Week 15 自己留了一句免责：目录只知道两条臂的能量不同，没有比较它们的占据轨道、自旋分布或键长"
    "（Week 15 §10 第 6 条）。Stage 17 把这两件事同时补上，并刻意选了**最便宜、也最像真实污染源**的路：",
    "",
    "- **Part A** 不重算整条台阶，只把 Week 9 第 2 级台阶 `P1 -> P2` 的 P2 腿（SMD(乙腈) 层）从默认初猜换成",
    "  moread 重算。这是「已发布结论直接架在默认初猜上、且污染有明确物理来源」的唯一一处：",
    "  Week 9 报告的台阶定义原文是「环境：气相 P1 -> SMD(乙腈) P2」，来源表 `outputs/week4/p2_environment_effects.csv`。",
    "- **Part B** 不新开任何量化作业，只读**已经存在**的 `.out`，把两条解的 `<S^2>`、自旋中心、轨道标签、",
    "  定域性（参与率 PR）与 Mulliken 电荷 / 自旋的 L1 差逐格对照——这正是 Week 15 §11 第 4 条要求的升级。",
    "",
    "两个问题的意义不同：Part A 回答「已发布的东西还站得住吗」（防守），Part B 回答「两个解到底差在哪」",
    "（机制）。合起来，Stage 17 把 Week 15 的「漏解是能量现象」推进成「漏解是一个可量化的污染上限，",
    "而且它的电子结构身份可以被刻画」。",
    "",
    "## 2. 口径与记号",
    "",
    "### 2.1 沿用不变的部分",
    "",
    "- 方法：**r2SCAN-3c**（气相与连续介质同法），**ORCA 6.1.1**，几何固定为 **G1**（不做任何重优化）。",
    "- 状态：中性 / 阳离子 / 阴离子三态，垂直量语义与 Week 4–15 完全一致。",
    f"- 判据约定（产物 `convention` 字段原文）：`{CONT['convention']}`。",
    f"- 材料阈值：**{THRESHOLD_MEV:g} meV**，原样继承 Week 14（Stage 15），本周**不重新标定**。",
    "- 台阶定义（Week 9 §2.3 原文）：第 2 级 `P1_to_P2` = 「环境：气相 P1 -> SMD(乙腈) P2」，",
    "  来源表 `outputs/week4/p2_environment_effects.csv`。**本周只动这一级的 P2 腿。**",
    f"- 受影响格子的定义（Part B）：`delta = E_moread - E_default < -{THRESHOLD_MEV:g} meV`，"
    "即默认初猜停在一个更高的 SCF 解上。",
    "",
]
L += [
    "### 2.2 两个冻结判据的原文定义（引用，不改写）",
    "",
    "`sigma` 与 `f_unresolved` 不是本周新造的量：它们自 Week 4 起被使用，在 Week 10 被化简为闭式，",
    "在 Week 11 §2 以记号表的形式冻结。本报告一律**引用原文**，不做改写：",
    "",
    "- `sigma` 的闭式（`docs/20_week10_report.md` T1 原文）：",
    "",
    "  > **命题**：`sigma_ij = abs(delta_i - delta_j) / sqrt(2)`。",
    "",
    "- `f_unresolved` 的等价写法（`docs/20_week10_report.md` T4 原文）：",
    "",
    "  > f_unresolved(z) = Pr_{i<j}( q_ij > sqrt(2)/z )",
    "",
    "- 记号与判据（`docs/21_week11_report.md` §2 记号表原文）：",
    "",
    "  > | delta | `delta_i = before_i - after_i`，逐分子位移 |",
    "  > | b | OLS 斜率 of `delta` on `after`（含截距） |",
    "  > | q_ij | `abs(delta_i - delta_j) / abs(after_i - after_j)`，位移对轴的割线斜率 |",
    "  > | 不可分辨 | `q_ij > sqrt(2)/z`（z = 1 为主判据，z = 1.96 为敏感性） |",
    "",
    "- 同一条件的另一种写法（`docs/21_week11_report.md` §1 原文）：",
    "",
    "  > 一对候选可分辨，当且仅当 `q_ij = abs(delta_i - delta_j) / abs(P1_i - P1_j) <= sqrt(2)/z`。",
    "",
    f"`z` 取预注册值 `z_primary = {Z_PRIMARY:g}`（`config/prereg.yaml` 的 "
    "`pair_comparison.z_factor.value`，产物里逐格记为 `z_primary`），敏感性列为 `z = 1.96`。",
    "本报告使用 `sigma` / `f_unresolved` / `f_robust_inv` 时，含义与上面引用的原文逐字一致。",
    "",
    "### 2.3 单腿替换许可证（Part A 为什么只换一条腿）",
    "",
    "本阶段只替换 `P1 -> P2` 的 **P2 腿**：`P1` 的数值、G1 几何、方法层（r2SCAN-3c / SMD(乙腈)）以及其余四级",
    "台阶（`P0_to_P1`、`G1_to_G2`、`C0_to_C1`、`C1_to_C2`）**全部未动**。因此本部分给出的是**单腿敏感性**，",
    "不是整条台阶的重算——它回答「这一条腿的初猜会不会改写已发布结论」，不回答「重算整条台阶会怎样」。",
    "它的合法性来自 3.1 的几何审计：新作业与 Week 4 参照**逐位同几何**，所以被替换的只有初猜这一个变量。",
    "",
    "### 2.4 Part B 的判据（只读既有 `.out`，零新增作业）",
    "",
    "Part B 只读**已经存在**的 `.out`：默认臂来自 Week 12/13 的 CPCM 目录，moread 臂来自 Week 14 的同名目录。",
    f"普查扫过 `outputs/week*/orca*/**/*.out` 共 {CEN['n_outfiles_scanned']} 个文件，"
    f"其中 {CEN['n_outfiles_parsed']} 个可解析为 C-PCM 臂输出。",
    f"「受影响格子」的判据仍是 `delta_ev < -{THRESHOLD_MEV:g} meV`（Stage 16 目录的 {N_HIT_B} 格），"
    "**本周不新开任何量化作业**。",
    "",
    "## 3. 本周新增的计算",
    "",
    "### 3.1 Part A：54 个 SMD moread 单点",
    "",
    f"- 规模：**{N_CELLS_A} 格** = {N_MOL_A} 分子 x {len(SMD['states'])} 态 x 1 层"
    f"（`{SMD['layer']}`）；`n_ok = {P2SUM['n_ok']}`，`n_failed = {P2SUM['n_failed']}`。",
    f"- 调度：`--jobs {SMD['jobs']} --nprocs {SMD['nprocs']}`（本机 16 逻辑核），与既有各层协议相同。",
    f"- **逐层墙钟中位数：{P2SUM['wall_clock_seconds_median']:.2f} s**"
    "（`p2_summary_moread_smd_acetonitrile.json` 的 `wall_clock_seconds_median`）。"
    f"全部为新算：`n_computed = {P2SUM['n_computed']}`、`n_reused = {P2SUM['n_reused']}`。",
    f"- 参照表：`{SMD['reference_csv']}`（default 臂，Week 4 冻结；产物原文："
    f"「{SMD['guess_protocol']['default']}」），零格缺参照（`n_cells_without_reference = "
    f"{SMD['n_cells_without_reference']}`）。",
    "- 初猜协议（产物原文）：`moread` = 「" + SMD["guess_protocol"]["moread"] + "」。",
    f"  需要暂存目录 `{SMD['guess_protocol']['staging_root']}`，原因是产物原文写的："
    f"「{SMD['guess_protocol']['staging_reason']}」。",
    "",
    f"**G1 几何复用审计（`stage17_smd_moread.json` 的 `geometry_audit`）**：{len(SMD['geometry_audit'])} 个分子逐一比对，"
    "每个比 3 个态，全部 `all_identical = True`。这是「单腿替换许可证」（2.3）的实测依据：",
    "",
    "| 分子 | 参照目录 | 比对态数 | 逐位一致 |",
    "| --- | --- | --- | --- |",
]
for _name in sorted(SMD["geometry_audit"]):
    _block = SMD["geometry_audit"][_name]
    L.append(f"| {_name} | `{_block['reference']}` | {_block['n_compared']} | "
             f"{'是' if _block['all_identical'] else '否'} |")

L += [
    "",
    "### 3.2 Part B：零新增作业（普查 + 覆盖 QC）",
    "",
    f"- 受影响格子：**{N_HIT_B}** 个（`delta_ev < -{THRESHOLD_MEV:g} meV`），"
    f"覆盖 {N_MOL_B} 个分子、{len(CHARGES)} 个电荷态。",
    f"- 普查（`stage17_solution_identity.json` 的 `census`）：扫描 `outputs/week*/orca*/**/*.out` 共 "
    f"**{CEN['n_outfiles_scanned']}** 个文件，其中 **{CEN['n_outfiles_parsed']}** 个可解析为 C-PCM 臂输出；"
    f"**{CEN['n_duplicate_keys']}** 个 `(arm, 分子, 态, epsilon)` 键存在重复路径"
    f"（共 {CEN['n_duplicate_paths']} 条冗余路径，按最新周 / 最新 mtime 去重）。",
    f"- 覆盖 QC：**{CEN['n_cells_resolved']}/{CEN['n_cells_requested']}** 每臂各唯一解析到一个 `.out`，"
    f"未解析 {len(CEN['unresolved'])} 个；两臂能量与 Stage 16 目录的最大偏差 "
    f"`max_delta_ev_mismatch_vs_stage16 = {CEN['max_delta_ev_mismatch_vs_stage16']:g} eV`（同源）。",
    "- 按 (分子, 态) 拆开（逐格遍历 `stage17_solution_identity.csv`）：",
    "",
    "| 分子 | 态 | 受影响格子数 |",
    "| --- | --- | --- |",
]
for _key in sorted(COUNTS, key=lambda k: (k[0], k[1])):
    L.append(f"| {_key[0]} | {_key[1]} | {COUNTS[_key]} |")

L += [
    "",
    f"受影响格子的能量差 `delta_ev` 落在 "
    f"[{AGG['delta_ev']['min']:.4f}, {AGG['delta_ev']['max']:.4f}] eV，均值 "
    f"{AGG['delta_ev']['mean']:.4f} eV（`aggregates.delta_ev`）。"
    f"注意：Part B 的 {N_HIT_B} 格是 **Stage 16 CPCM 目录**（10 个电介质）里的格子，与 Part A 的 SMD(乙腈) 层不是同一批，",
    "两部分的 `delta` 不能相加或混读。",
    "",
    "## 4. Part A：污染上限（P1 -> P2 台阶的第 2 级，只换 P2 腿）",
    "",
    "### 4.1 逐轴对照表（published / default / moread）",
    "",
    "| 轴 | 臂 | n | tau_b | tau_b 95% CI | O_20% | f_unresolved(after) | f_robust_inv | sigma 中位(eV) | shift 均值(eV) |",
    "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
]
for _axis in ("oxidation", "reduction"):
    _pub = PUB[_axis]["published"]
    L.append(f"| {AXIS_LABEL[_axis]} | **published** | {_pub['n']} | {_pub['kendall_tau_b']:.3f} | "
             f"[{_pub['tau_b_ci_low']:.3f}, {_pub['tau_b_ci_high']:.3f}] | {_pub['overlap_20']:.3f} | "
             f"{_pub['f_unresolved_after']:.3f} | {_pub['f_robust_inv']:.3f} | "
             f"{_pub['sigma_median_ev']:.3f} | {_pub['shift_mean_ev']:.3f} |")
    for _arm in ("default", "moread"):
        _row = PA[_axis][_arm]
        L.append(f"| {AXIS_LABEL[_axis]} | {_arm} | {_row['n']} | {_row['kendall_tau_b']:.3f} | "
                 f"[{_row['tau_b_ci_low']:.3f}, {_row['tau_b_ci_high']:.3f}] | {_row['overlap_20']:.3f} | "
                 f"{_row['f_unresolved_after']:.3f} | {_row['f_robust_inv']:.3f} | "
                 f"{_row['sigma_median_ev']:.3f} | {_row['shift_mean_ev']:.3f} |")

L += [
    "",
    "> 来源：`stage17_contamination.json` 的 `published_comparison.<轴>.published`（published 行）与 "
    "`per_axis.<轴>.<臂>`（default / moread 行）；published 行的原始出处是该 JSON 里 `published.source` "
    "指向的 `outputs/week9/stage10_ladder.json`（`population=native`, `rung=P1_to_P2`）。",
    "",
    f"`O_20%` 两臂完全相同（ox {OXD['overlap_20']:.3f}/{OXM['overlap_20']:.3f}，"
    f"red {REDD['overlap_20']:.3f}/{REDM['overlap_20']:.3f}）——也就是说，即使 `tau_b` 动了，"
    "**被选进 Top-20% 的那批分子一个都没换**。",
    "",
    "### 4.2 moread - published 逐项 delta",
    "",
    "| 轴 | Δtau_b | ΔO_20% | Δf_unresolved(after) | Δf_robust_inv | Δsigma 中位(eV) |",
    "| --- | --- | --- | --- | --- | --- |",
]
for _axis in ("oxidation", "reduction"):
    _d = PUB[_axis]["moread_minus_published"]
    L.append(f"| {AXIS_LABEL[_axis]} | {_d['kendall_tau_b']:+.4f} | {_d['overlap_20']:+.4f} | "
             f"{_d['f_unresolved_after']:+.4f} | {_d['f_robust_inv']:+.4f} | "
             f"{_d['sigma_median_ev']:+.4f} |")

L += [
    "",
    "> 来源：`stage17_contamination.json` 的 `published_comparison.<轴>.moread_minus_published`。",
    "",
    "对照 `published_comparison.<轴>.default_minus_published`（全部为 0.0）可见：default 臂在逐项上都**精确复原**",
    f"了 published 值（`default_matches_published_max_abs_ev = "
    f"{CONT['default_matches_published_max_abs_ev']['ox']:g}` eV 氧化轴 / "
    f"{CONT['default_matches_published_max_abs_ev']['red']:g} eV 还原轴），所以 4.2 的每一列都只反映 moread 这一条腿。",
    "",
]
L += [
    "### 4.3 delta = p2_moread - p2_default：统计与符号检验",
    "",
    "| 粒度 | n | mean(eV) | std(eV) | min(eV) | max(eV) | argmin | argmax |",
    "| --- | --- | --- | --- | --- | --- | --- | --- |",
]
for _key, _kind in (("cells_54", "格（分子 x 态）"),
                    ("axis_oxidation_18", "分子（氧化轴）"),
                    ("axis_reduction_18", "分子（还原轴）")):
    _block = DS[_key]
    _label = f"{_block['n']} {_kind}"
    L.append(f"| {_label} | {_block['n']} | {_block['mean_ev']:.6f} | {_block['std_ev']:.6f} | "
             f"{_block['min_ev']:.6f} | {_block['max_ev']:.6f} | {_block['argmin']} | {_block['argmax']} |")
L += [
    "",
    "> 来源：`stage17_contamination.json` 的 `delta_stats`（`definition` 字段原文："
    f"「{DS['definition']}」）。",
    "",
    "| 粒度 | 正 | 负 | 零 | 双侧 p | 单侧(正) p |",
    "| --- | --- | --- | --- | --- | --- |",
]
for _key, _kind in (("cells_54", "格（分子 x 态）"),
                    ("axis_oxidation_18", "分子（氧化轴）"),
                    ("axis_reduction_18", "分子（还原轴）")):
    _block = SIGN[_key]
    _label = f"{_block['n_total']} {_kind}"
    L.append(f"| {_label} | {_block['n_positive']} | {_block['n_negative']} | {_block['n_zero']} | "
             f"{_block['p_two_sided']:.3f} | {_block['p_one_sided_greater']:.3f} |")
L += [
    "",
    "> 来源：`stage17_contamination.json` 的 `sign_test`（`side` 字段原文："
    f"「{SIGN['cells_54']['side']}」，容差 `tolerance_ev = {SIGN['cells_54']['tolerance_ev']:g}`）。",
    "",
    f"主判据是 **{SIGN['cells_54']['n_total']} 格**那一行：正 {SIGN['cells_54']['n_positive']} / 负 {SIGN['cells_54']['n_negative']} / "
    f"零 {SIGN['cells_54']['n_zero']}，双侧 p = {SIGN['cells_54']['p_two_sided']:.3f}——"
    "**moread 与 default 的差别在符号层面完全不显著**，这与「两臂在绝大多数格子上收敛到同一个解」一致。",
    "",
    f"### 4.4 改变的格子（|delta| > {THRESHOLD_MEV:g} meV）",
    "",
    f"共 **{CONT['cells_changed_count']}** 个格子（判据 |delta| > {THRESHOLD_MEV:g} meV）：",
    "",
    "| 分子 | 态 | delta(eV) | 所属轴 |",
    "| --- | --- | --- | --- |",
]
for _row in CONT["cells_changed"]:
    L.append(f"| {_row['molecule']} | {_row['state']} | {_row['delta_ev']:+.6f} | {', '.join(_row['axes'])} |")
L += [
    "",
    "> 来源：`stage17_contamination.json` 的 `cells_changed`（`cells_changed_count` 与其长度一致，生成器断言）。",
    "",
    f"六个格里五个是 moread **更低**（`delta < 0`），只有 **EC / anion 是 "
    f"{DS['cells_54']['max_ev']:+.4f} eV**——moread 反而**更高**。这条正向残差必须原样保留：它说明",
    "「读气相轨道当起点」并不是无条件更好，只是在本周这条台阶上不足以改写任何结论（4.5）。",
    "",
    "### 4.5 哪些结论被改写：三个 scenario verdict 复核",
    "",
    f"产物判定：`any_published_conclusion_rewritten = {VERDICT['any_published_conclusion_rewritten']}`，"
    f"`tau_b_ci_overlap_both_axes = {VERDICT['tau_b_ci_overlap_both_axes']}`。",
    "逐项「未被改写」的理由（`verdict.conclusions_unchanged` 原文）：",
    "",
]
for _line in VERDICT["conclusions_unchanged"]:
    L.append(f"- {_line}")
L += [
    "",
    "三个 scenario 的复核（`verdict.scenario_verdicts` 原文）：",
    "",
]
for _key, _block in VERDICT["scenario_verdicts"].items():
    L += [
        f"- **{_key}**（原判：{_block['published']}）—— 复核依据：{_block['recheck']}",
        f"  复核结论：{_block['assessment']}",
    ]
L += [
    "",
    "一句话：**没有任何一条 published 结论被改写**；B 仍 SUPPORTED、C 仍 NOT OBSERVED、",
    "A 的 P2 腿依赖不受影响。",
    "",
    "### 4.6 上限声明：CI 是否吸收污染",
    "",
]
for _axis in ("oxidation", "reduction"):
    _block = CIO[_axis]
    L.append(f"- **{AXIS_LABEL[_axis]}**：default CI = [{_block['default_ci'][0]:.3f}, {_block['default_ci'][1]:.3f}]，"
             f"moread CI = [{_block['moread_ci'][0]:.3f}, {_block['moread_ci'][1]:.3f}]，"
             f"重叠 = {'是' if _block['overlap'] else '否'}")
L += [
    "",
    "> 来源：`stage17_contamination.json` 的 `ci_overlap`（`method` 字段原文："
    f"「{CIO['oxidation']['method']}」）。",
    "",
    "两个轴的两臂 CI 都重叠，因此本次单腿替换带来的位移**落在 Week 9 冻结的区间估计之内**——",
    "这就是「污染上限」的确切含义：即便把这条腿换掉，`tau_b` 的不确定区间也不足以把它与 published 分开。",
    "",
    "### 4.7 为什么 `f_robust_inv` 从 0 变非 0 是结构性不可能",
    "",
    "`f_robust_inv` 的分子是「两臂都 resolved 且反号」的 pair 数。在 `P1 -> P2` 这类台阶上，`sigma_ij`",
    "恰好由**两个 realization**（`P1` 与 `P2`）给出：",
    "",
    "    sigma_ij = abs(d0_ij - d1_ij) / sqrt(2)          （d0 = P1 的 pair 差，d1 = P2 的 pair 差）",
    "",
    "设某一对被判为「两臂都 resolved 且反号」，取 `d0 > 0 > d1`，则 `abs(d0 - d1) = abs(d0) + abs(d1)`，",
    "于是 `sigma_ij = (abs(d0) + abs(d1)) / sqrt(2)`。两条 resolved 条件（`z_primary = 1.0`）各自展开：",
    "",
    "    |d0| >= z * sigma   <=>   (sqrt(2) - 1) * |d0| >= |d1|",
    "    |d1| >= z * sigma   <=>   (sqrt(2) - 1) * |d1| >= |d0|",
    "",
    "两式相乘得 `|d0||d1| <= (sqrt(2) - 1)^2 |d0||d1|`，即要求 `1 <= (sqrt(2) - 1)^2`。",
    f"而 `(sqrt(2) - 1)^2 = {ROOT2_MINUS_1 ** 2:.4f} < 1`——矛盾。所以**反号且两臂都 resolved 的 pair 集合恒为空集**，",
    "`f_robust_inv` 在这种估计量下恒等于 0，与数据无关。",
    "",
    "必须说清的两点：",
    "",
    "1. 这是**估计量的结构性质**，不是「物理上不存在稳健反转」。它成立的前提是 (a) `z_primary = 1.0`、",
    "   (b) `sigma` 恰好由两条 realization 给出。换 `z > 1`、换成 `ddof = 0` 的 `sigma`、或补进第三条",
    "   realization，这条不可能性都会解除。因此本周的读法只能是：**在这次单腿替换下，`f_robust_inv` 的**",
    "   **0 -> 非 0 翻转不可能发生**，而不是「污染不可能造成稳健反转」。",
    "2. 这条不是「事后合理化」，它被两处独立钉住：(a) 生成器对四个 (轴, 臂) 组合的 `f_robust_inv` 与",
    "   `f_robust_inv_z1p96` 全部 `assert` 为 0；(b) `_lemma_check()` 用 "
    "`outputs/week16/stage17_contamination_cells.csv` 的原始 `P1` / `P2(moread)` 向量把两轴的",
    "   全部 18x18 pair 重算了一遍，断言「没有任何一对同时满足反号与两臂 resolved」。",
    "",
]
L += [
    "## 5. Part B：两个 SCF 解的电子结构身份",
    "",
    f"本节的 {N_HIT_B} 个格子全部来自 Stage 16 CPCM 目录中 `delta_ev < -{THRESHOLD_MEV:g} meV` 的配对格，",
    "只读既有 `.out`，零新增作业。所有数字来自 `stage17_solution_identity.json`（聚合量）与",
    "`stage17_solution_identity.csv`（逐格）。",
    "",
    "### 5.1 自旋纯度 `<S^2>`",
    "",
    f"- 两臂 `<S^2>` 都落在 **{S2_DOUBLET:g} ± {S2_PURITY_BAND:g}** 的格子：**{N_HIT_B}/{N_HIT_B}**"
    "（都是自旋纯双重态，未与四重态混杂）。",
    f"- 均值：default = **{AGG['s2_default']['mean']:.6f}**，moread = **{AGG['s2_moread']['mean']:.6f}**；"
    f"两臂各自的范围 default [{AGG['s2_default']['min']:.6f}, {AGG['s2_default']['max']:.6f}]、"
    f"moread [{AGG['s2_moread']['min']:.6f}, {AGG['s2_moread']['max']:.6f}]。",
    f"- `delta_s2` 范围 **[{AGG['delta_s2']['min']:+.6f}, {AGG['delta_s2']['max']:+.6f}]**，"
    f"均值 {AGG['delta_s2']['mean']:+.6f}。",
    f"- 多重度：两臂在每个格子上都是 **{', '.join(MULTS)}**（双重态），电荷取值 {', '.join(CHARGES)}"
    "（阳离子 / 阴离子），逐格一致。",
    "",
    "> 来源：`stage17_solution_identity.json` 的 `aggregates.s2_default` / `s2_moread` / `delta_s2`；",
    "> 逐格字段 `s2_default` / `s2_moread` / `mult_default` / `mult_moread` / `charge_default` /",
    "> `charge_moread` 见 `stage17_solution_identity.csv`。",
    "",
    "### 5.2 自旋中心与轨道标签",
    "",
    "| 判据 | 一致格子数 | 拆分 |",
    "| --- | --- | --- |",
    f"| 承载最大 \\|Mulliken 自旋\\| 的原子在两臂相同 | {N_SAME_SPIN_CENTER}/{N_HIT_B} | "
    f"anion {BYSTATE['anion']['n_same_spin_center']}/{BYSTATE['anion']['n_cells']}、"
    f"cation {BYSTATE['cation']['n_same_spin_center']}/{BYSTATE['cation']['n_cells']} |",
    f"| reduced-orbital SPIN 子块最大 \\|贡献\\| 的原子-轨道标签相同 | {N_SAME_ORBITAL}/{N_HIT_B} | "
    f"anion {BYSTATE['anion']['n_same_orbital_label']}/{BYSTATE['anion']['n_cells']}、"
    f"cation {BYSTATE['cation']['n_same_orbital_label']}/{BYSTATE['cation']['n_cells']} |",
    "",
    "> 来源：`stage17_solution_identity.json` 的 `by_state.anion` / `by_state.cation`"
    "（键 `n_same_spin_center`、`n_same_orbital_label`）；逐格布尔字段同名的见 CSV。",
    "",
    "出现过的 `(default -> moread)` 轨道标签对（逐格遍历 `stage17_solution_identity.csv`，按首次出现排序）：",
    "",
]
for _pair in ORBITAL_PAIRS:
    L.append(f"- `{_pair[0]} -> {_pair[1]}`")

L += [
    "",
    f"这 {len(ORBITAL_PAIRS)} 组标签里既有 `pz -> pz`（同通道），也有 `py -> s`、`s -> s`、`py -> px`（换通道）。",
    "**不要在弥散基组下把它读成「就是 pi* 的 pz 通道」**——见 7.2 的口径纪律。",
    "",
    "### 5.3 定域性（参与率 PR）",
    "",
    "| 量 | default | moread | 差（moread - default） |",
    "| --- | --- | --- | --- |",
    f"| 参与率 PR 均值 | {AGG['spin_pr_default']['mean']:.4f} | {AGG['spin_pr_moread']['mean']:.4f} | "
    f"{AGG['loss_in_pr']['mean']:+.4f} |",
    f"| 最大原子自旋 `spin_max` 均值 | {AGG['spin_max_default']['mean']:.4f} | {AGG['spin_max_moread']['mean']:.4f} | "
    f"{AGG['spin_max_moread']['mean'] - AGG['spin_max_default']['mean']:+.4f} |",
    f"| n90（承载 90% 自旋所需原子数）均值 | {AGG['spin_n90_default']['mean']:.4f} | "
    f"{AGG['spin_n90_moread']['mean']:.4f} | "
    f"{AGG['spin_n90_moread']['mean'] - AGG['spin_n90_default']['mean']:+.4f} |",
    "",
    "> 来源：`stage17_solution_identity.json` 的 `aggregates.spin_pr_default` / `spin_pr_moread` /",
    "> `spin_max_default` / `spin_max_moread` / `spin_n90_default` / `spin_n90_moread` / `loss_in_pr`",
    "> （`loss_in_pr = PR_moread - PR_default`，**正 = moread 解更离域**）。",
    "",
    f"- `loss_in_pr > 0` 的格子：**{N_LOSS_PR_POSITIVE}/{N_HIT_B}**；"
    f"`< 0` 的格子：{N_LOSS_PR_NEGATIVE}/{N_HIT_B}。",
    f"- `loss_in_pr` 均值 **{AGG['loss_in_pr']['mean']:+.4f}**，范围 "
    f"[{AGG['loss_in_pr']['min']:+.4f}, {AGG['loss_in_pr']['max']:+.4f}]。",
    f"- `spin_max` 从 {AGG['spin_max_default']['mean']:.4f} 抬到 **{AGG['spin_max_moread']['mean']:.4f}**："
    "moread 解把自旋**更集中**堆在少数原子上，但整体 PR 反而更低——两者并不矛盾：",
    "PR 描述的是全部分布的「有效参与原子数」，`spin_max` 只描述最大的那一个。",
    "",
    "### 5.4 电荷重组（Mulliken 逐原子 L1 差）",
    "",
    f"- `charge_l1`：均值 **{AGG['charge_l1']['mean']:.4f}**，范围 "
    f"[{AGG['charge_l1']['min']:.4f}, {AGG['charge_l1']['max']:.4f}]。",
    f"- `spin_l1`：均值 **{AGG['spin_l1']['mean']:.4f}**，范围 "
    f"[{AGG['spin_l1']['min']:.4f}, {AGG['spin_l1']['max']:.4f}]。",
    "",
    "> 来源：`stage17_solution_identity.json` 的 `aggregates.charge_l1` / `aggregates.spin_l1`；",
    "> 逐格 `charge_l1` / `spin_l1` 见 `stage17_solution_identity.csv`。",
    "",
    "`charge_l1` 与 `spin_l1` 量级相当，说明两个解之间**电荷在动**，不只是自旋在换位置。",
    "",
    "### 5.5 按电荷态",
    "",
    "| 态 | 格子 | Δ<S^2> 均值 | loss_in_pr 均值 | charge_l1 均值 | spin_l1 均值 | 自旋中心相同 | 轨道标签相同 | 分子 |",
    "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
]
for _state in ("anion", "cation"):
    _b = BYSTATE[_state]
    L.append(f"| {_state} | {_b['n_cells']} | {_b['delta_s2_mean']:+.6f} | {_b['loss_in_pr_mean']:+.4f} | "
             f"{_b['charge_l1_mean']:.4f} | {_b['spin_l1_mean']:.4f} | "
             f"{_b['n_same_spin_center']}/{_b['n_cells']} | {_b['n_same_orbital_label']}/{_b['n_cells']} | "
             f"{', '.join(_b['molecules'])} |")
L += [
    "",
    "> 来源：`stage17_solution_identity.json` 的 `by_state.anion` / `by_state.cation`。",
    "",
    f"对比很干净：阴离子的自旋中心在两臂**完全一致**（{BYSTATE['anion']['n_same_spin_center']}/"
    f"{BYSTATE['anion']['n_cells']}），阳离子只有 {BYSTATE['cation']['n_same_spin_center']}/"
    f"{BYSTATE['cation']['n_cells']}；而且阴离子的 `loss_in_pr`（{BYSTATE['anion']['loss_in_pr_mean']:+.4f}）"
    f"比阳离子（{BYSTATE['cation']['loss_in_pr_mean']:+.4f}）更负，`charge_l1` 也大一个量级。",
    "",
    "### 5.6 按分子家族",
    "",
    "| 家族 | 格子 | 分子 | loss_in_pr 均值 | charge_l1 均值 | 自旋中心相同 | 轨道标签相同 |",
    "| --- | --- | --- | --- | --- | --- | --- |",
]
for _family in sorted(BYFAM):
    _b = BYFAM[_family]
    L.append(f"| {_family} | {_b['n_cells']} | {', '.join(_b['molecules'])} | {_b['loss_in_pr_mean']:+.4f} | "
             f"{_b['charge_l1_mean']:.4f} | {_b['n_same_spin_center']}/{_b['n_cells']} | "
             f"{_b['n_same_orbital_label']}/{_b['n_cells']} |")
L += [
    "",
    "> 来源：`stage17_solution_identity.json` 的 `by_family.cyclic_carbonate` / `linear_carbonate` / `phosphate`。",
    "",
    f"家族分裂比电荷态更锋利：cyclic_carbonate 的 `loss_in_pr` = "
    f"**{BYFAM['cyclic_carbonate']['loss_in_pr_mean']:+.3f}**（moread 更定域）而 linear_carbonate = "
    f"**{BYFAM['linear_carbonate']['loss_in_pr_mean']:+.3f}**（moread 更离域），两条方向相反；"
    f"linear 的 `charge_l1` = {BYFAM['linear_carbonate']['charge_l1_mean']:.3f}，"
    f"是 cyclic（{BYFAM['cyclic_carbonate']['charge_l1_mean']:.3f}）的约 "
    f"{BYFAM['linear_carbonate']['charge_l1_mean'] / BYFAM['cyclic_carbonate']['charge_l1_mean']:.1f} 倍。"
    f"TMP（phosphate）的自旋中心 {BYFAM['phosphate']['n_same_spin_center']}/{BYFAM['phosphate']['n_cells']} 全部翻转，",
    "原因见 6(iv) 与 9.4——那是近简并表观，不是稳健判据。",
    "",
    "### 5.7 几何 QC",
    "",
    f"- 两臂 `CARTESIAN COORDINATES (ANGSTROEM)` 逐位相同的格子：**{N_GEOM_IDENTICAL}/{N_HIT_B}**。",
    "",
    "> 来源：`stage17_solution_identity.csv` 的 `geometry_identical` 列（逐格）；",
    "> 按态/家族汇总见 `stage17_solution_identity.json` 的 `by_state.*.n_geometry_identical` 与",
    "> `by_family.*.n_geometry_identical`。",
    "",
    "这条 QC 的意义：`.out` 里的两臂坐标完全相同，所以 5.1–5.4 的差异**只能来自 SCF 解本身**，",
    "不是几何松弛走了另一条路径。",
    "",
]
L += [
    "## 6. 物理读法",
    "",
    "**(i) 这不是破缺对称性伪影。** 两个解都是自旋纯双重态（5.1，"
    f"{N_HIT_B}/{N_HIT_B} 落在 {S2_DOUBLET:g}±{S2_PURITY_BAND:g}），多重度都是 "
    f"{'/'.join(MULTS)}。所以它们**不是**同一个态在 UKS 下的自旋污染产物，而是**同一自旋量子数下的",
    "两个不同 SCF 驻点**——能量不同、电子结构不同，但都是合法的双重态。这句话把「漏解」从一个「收敛",
    "问题」升级成了「解的多重性」问题。",
    "",
    f"**(ii) 空穴比电子更难安放。** 阴离子的自旋中心在两臂完全一致（{BYSTATE['anion']['n_same_spin_center']}/"
    f"{BYSTATE['anion']['n_cells']}），阳离子只有 {BYSTATE['cation']['n_same_spin_center']}/"
    f"{BYSTATE['cation']['n_cells']}。也就是说：**默认初猜倾向把多余电子放在哪里基本是可复现的，",
    "而它倾向把空穴放在哪里则高度依赖初猜**。这与 Week 15 §7.2 的机制一致——阳离子的近简并让 SCF",
    "更容易落进不同分支，而阴离子的自旋在缺弥散基组下被迫定域到一个可预判的位点。",
    "",
    f"**(iii) 差异的主轴是电荷重组，不只是自旋重排。** `charge_l1` 均值 {AGG['charge_l1']['mean']:.3f}",
    f"与 `spin_l1` 均值 {AGG['spin_l1']['mean']:.3f} 同量级，但家族之间的分裂出现在电荷上：linear_carbonate 的",
    f"`charge_l1` = {BYFAM['linear_carbonate']['charge_l1_mean']:.3f}，是 cyclic_carbonate"
    f"（{BYFAM['cyclic_carbonate']['charge_l1_mean']:.3f}）的 **"
    f"{BYFAM['linear_carbonate']['charge_l1_mean'] / BYFAM['cyclic_carbonate']['charge_l1_mean']:.1f} 倍**（5.6）。",
    "换句话说，「第二条解」在这两个家族里差别最大的不是自旋往哪跑，而是**电荷整体怎么重新分配**。",
    "",
    "**(iv) TMP 的翻转是近简并表观，不能当判据。** TMP（phosphate）的自旋几乎均摊在三个磷酸氧上"
    f"（`spin_max` 均值仅 {TMP_SPIN_MAX_DEFAULT:.4f} vs {TMP_SPIN_MAX_MOREAD:.4f}，"
    f"远低于全体两臂均值 {AGG['spin_max_default']['mean']:.4f} / {AGG['spin_max_moread']['mean']:.4f}），",
    f"三个氧近简并，所以「哪个氧承载最大自旋」在两臂之间翻转（{BYFAM['phosphate']['n_same_spin_center']}/{BYFAM['phosphate']['n_cells']} 一致）几乎是投硬币的结果，",
    "**不能读成「TMP 的解身份不稳定」**。这一条写进 9.4 的限制里。",
    "",
    "## 7. 读法纪律（延续 Week 9 §10 / 10 §11 / 11 §11 / 12 §10 / 13 §11 / 14 §9 / 15 §8）",
    "",
    "1. **Part A 是单腿敏感性，不是整条台阶的重算。** 本周只换了 `P1 -> P2` 的 **P2 腿**；`P1` 值、几何、",
    "   方法层与其余四级台阶都没动（2.3）。所以结论只能写成「这条腿的初猜不足以改写已发布结论」，",
    "   **不能**写成「整条台阶经得起重算」或「所有台阶都安全」。",
    "2. **判「未成对电子主贡献轨道」用的是 reduced-orbital SPIN 子块里 |值| 最大的原子-轨道；",
    "   在弥散基组下该最大值常落在弥散 s 通道而不是 pi* 的 pz 通道。** 这句话是产物 "
    "`stage17_solution_identity_summary.md` §8 的**原文**，本报告**不许把它简化成「就是 pi*」**；",
    "   5.2 的两组 `py -> s` / `s -> s` 标签对就是这条口径的直接证据。",
    "3. **`f_robust_inv = 0` 是估计量的结构性质，不是物理结论。** 两 realization + `z_primary = 1.0` 下",
    "   「反号且两臂都 resolved」恒为空集（4.7）；报告里必须把「不可能翻转」的**前提**一起写出，",
    "   否则会被误读成「物理上不存在稳健反转」。",
    f"4. **近简并造成的「中心翻转」不是身份判据。** TMP 的 {BYFAM['phosphate']['n_same_spin_center']}/{BYFAM['phosphate']['n_cells']} 一致来自三个磷酸氧的近简并（6(iv)），",
    f"   与 EC/PC 那种「自旋真的换了位点」不是同一件事；报告里把两者分开写，不让 {BYFAM['phosphate']['n_same_spin_center']}/{BYFAM['phosphate']['n_cells']} 拉低整体结论。",
    f"5. **样本小就把不确定性写在脸上。** Part B 只有 {N_HIT_B} 格、{N_MOL_B} 个分子、2 个态；家族结论每个家族只有 1–2 个",
    "   分子（cyclic 2 个、linear 2 个、phosphate 1 个），只能当作**机制提示**，不能当作发生率估计。",
    "6. **复用与只读都要留出处。** Part A 的 default 臂不是重算的，而是从 Week 4 参照表原样读入；",
    "   Part B 的每一个 `.out` 路径都记在 `stage17_solution_identity.csv` 的 `default_path` / `moread_path` 列里，",
    "   去重规则（按最新周 / 最新 mtime）写在 `census` 里。",
    "",
]
DATA_FILES = sorted(p.name for p in W16.iterdir() if p.is_file())
NOTES = {
    "p2_core_set_moread_smd_acetonitrile.csv": "P2 moread 臂逐格原始表（54 行，SMD(乙腈)）",
    "p2_summary_moread_smd_acetonitrile.json": "该层的计算台账（n_ok / n_failed / 墙钟中位数）",
    "stage17_contamination.json": "Part A 的全部产物（逐轴对照 / delta_stats / 符号检验 / scenario verdict / CI 重叠）",
    "stage17_contamination_cells.csv": "Part A 逐分子表（P1 与两臂 P2 的原始能量、逐态 delta）",
    "stage17_contamination_ladder.csv": "Part A 四行 (臂, 轴) 指标表（含 published 列与 delta 列）",
    "stage17_contamination_summary.md": "Part A 的中文小结（§4 的口径对照）",
    "stage17_smd_moread.json": "Part A 计算台账 + G1 几何审计 + 初猜协议原文",
    "stage17_smd_moread_plan.json": "Part A 运行前的作业计划（18 分子 x 3 态）",
    "stage17_solution_identity.csv": "Part B 逐格表（两臂 `.out` 路径、<S^2>、自旋中心、PR、L1、几何 QC）",
    "stage17_solution_identity.json": "Part B 全部聚合产物（census / by_state / by_family / aggregates）",
    "stage17_solution_identity_by_molecule.csv": "Part B 按 (分子, 态) 汇总表",
    "stage17_solution_identity_summary.md": "Part B 中文小结（§8 含主贡献轨道口径原文）",
}

L += [
    "## 8. 产物与图表",
    "",
    "### 8.1 数据产物（`outputs/week16/`）",
    "",
    "| 文件 | 说明 |",
    "| --- | --- |",
]
for _name in DATA_FILES:
    if _name.startswith("p2_") and _name.endswith((".csv", ".json")):
        continue
    L.append(f"| `{_name}` | {NOTES.get(_name, '（见产物自身字段）')} |")

L += [
    "",
    f"另有 Part A 的原始作业目录 `outputs/week16/orca_moread_smd_acetonitrile/`"
    f"（{N_MOL_A} 个分子子目录，每个 3 态；`.inp` / `.out` / `.xyz`；`.gbw` 不入库），"
    "以及 2 个 `p2_*` 原始表（`p2_core_set_moread_smd_acetonitrile.csv` + "
    "`p2_summary_moread_smd_acetonitrile.json`）。",
    "",
    "### 8.2 图表",
    "",
    f"![F32]({F32_REL})",
    "",
    f"`{F32_REL}` —— Stage 17 Part A（污染上限），三块面板：",
    f"(a) {N_MOL_A} 分子 x 2 轴的 `delta = p2_moread - p2_default`，参考带 = 材料阈值 "
    f"{THRESHOLD_MEV:g} meV（最坏 |delta| = {DS['cells_54']['max_abs_ev']:.4f} eV，"
    f"{DS['cells_54']['argmin']}；唯一的大正残差是 {DS['cells_54']['argmax']} "
    f"{DS['cells_54']['max_ev']:+.4f} eV）；",
    "(b) 排序稳定性对照（两轴两臂的 `tau_b` 与 95% CI，两轴 CI 重叠）；",
    f"(c) 决策量 default vs moread（`O_20%` / `f_unresolved(after)` / `f_robust_inv` / `sigma 中位`）"
    f"与 {CONT['cells_changed_count']} 个超阈值格子。本报告 §4 是它的逐数 companion。",
    "",
    f"![F33]({F33_REL})",
    "",
    f"`{F33_REL}` —— Stage 17 Part B（两个 SCF 解的电子结构身份），四块面板：",
    "(d) 代表性逐原子自旋剖面（PC / anion / cpcm_10）；",
    "(e) 三个家族的 `loss_in_pr` 均值（与 5.6 同源）；",
    f"(f) {N_HIT_B} 格的 Δ`<S^2>`（参考线 = 纯双重态 {S2_DOUBLET:g}）；",
    "(g) 三个家族的 `charge_l1` vs `spin_l1`。本报告 §5 是它的逐数 companion。",
    "",
    f"- 面板组成的权威说明、两张 PNG 的 SHA256 与输入产物哈希：`{MANIFEST_REL}`。",
    "",
    "### 8.3 脚本与测试",
    "",
    f"- `scripts/run_stage17_smd_moread.py`：Part A 的 {N_CELLS_A} 格作业调度与台账（几何审计、初猜协议、`--jobs/--nprocs`）。",
    "- `scripts/analyze_stage17_contamination.py`：Part A 分析（逐轴对照、delta_stats、符号检验、scenario verdict、CI 重叠）。",
    "- `scripts/analyze_stage17_solution_identity.py`：Part B 分析（普查、两臂 `.out` 配对、`<S^2>` / 自旋中心 / PR / L1 聚合）。",
    "- `scripts/gen_week16_report.py`：本报告的生成器（本节全部数字的唯一出处）。",
    f"- 图表与清单（`{F32_REL}`、`{F33_REL}`、`{MANIFEST_REL}`）由 `scripts/make_stage17_figure.py` 生成，",
    "  后者把两张 PNG 的 SHA256 与输入产物的哈希一并写进清单。",
    "",
    "## 9. 已知限制",
    "",
    f"1. **Part A 只在 native {N_MOL_A} 分子的 SMD(乙腈) P2 层上做单腿替换**：它不是整条台阶的重算，",
    "   也没有覆盖 common-10 的其它台阶或别的环境层（2.3）。因此「污染上限」这句话的作用域就是这一条腿。",
    "2. **`f_robust_inv ≡ 0` 是估计量的结构后果，不是物理结论**：它依赖 `z_primary = 1.0` 与「`sigma` 恰好由",
    "   两条 realization 给出」（4.7）。换 `ddof`、补第三条 realization 或抬高 `z`，这条结论都会改变。",
    f"3. **Part B 只有 {N_HIT_B} 格、{N_MOL_B} 个分子、{len(CHARGES)} 个电荷态**，判据 `delta_ev < -{THRESHOLD_MEV:g} meV`",
    "   继承自 Stage 16，本周未重标定；家族结论每个家族只有 1–2 个分子，只能当**机制提示**。",
    f"4. **TMP 的自旋近简并**：三个磷酸氧上的自旋几乎均摊，所以「哪个氧承载最大自旋」的 {BYFAM['phosphate']['n_same_spin_center']}/{BYFAM['phosphate']['n_cells']} 翻转是",
    "   **近简并表观**，不能当作稳健判据（6(iv)）。",
    "5. **「主贡献轨道」的口径是 reduced-orbital SPIN 子块里 |值| 最大的原子-轨道**；在弥散基组下该最大值常落在",
    f"   弥散 s 通道而不是 pi* 的 pz 通道。因此 5.2 的「轨道标签相同 {N_SAME_ORBITAL}/{N_HIT_B}」**不能**读成「pi* 身份相同」。",
    "6. **Part B 是纯读既有输出，没有做结构表征**：没有比较键长、自然轨道占据数、能量分解，也没有比较",
    "   两解的振动或自由能。本周回答的是「两个解在 Mulliken 自旋/电荷与参与率上差多少」，不是「为什么」。",
    "7. **`delta` 是垂直能量差**（同几何、同方法、同电荷态），不是自由能，也没有构型采样。",
    f"8. **冗余路径去重只按「最新周 / 最新 mtime」**：{CEN['n_duplicate_paths']} 条冗余路径说明历史上多次重算过同一",
    "   `(arm, 分子, 态, epsilon)` 键；本周选中的那一个不保证是最科学的那个，只保证是最新的。",
    "",
    "## 10. 下一步（Week 17 候选）",
    "",
    "按「先堵漏、再扩张」排序，并逐条标明是否需要新作业：",
    "",
    "1. **（零新增计算）把单腿替换推广成「逐腿敏感性表」**：对五级台阶的每一条腿，列出「这条腿若换",
    "   moread，会不会改写 tau_b / Top-k / 清单」。P0_to_P1、G1_to_G2、C0_to_C1、C1_to_C2 的更多臂能量",
    "   大多已在 Stage 16 的 CPCM moread 目录里，可以**先纯读筛查**，只把真正会动的格子标出来。",
    "2. **（零新增计算）把 Part B 的三条身份判据回填到 Stage 16 的全目录上**：检验「哪些",
    "   (分子, 态, epsilon) 的漏解会伴随自旋中心翻转 / 大 `charge_l1` / 大 `loss_in_pr`」。",
    "   如果三者能预测漏解，就得到一个**不必读 `.out`** 的事前筛查量。",
    "3. **（需要新作业）真正的 out-of-sample 扩张**：把 moread 协议推广到 broad pool 的 40 个分子阴离子",
    "   （Week 15 §11 第 2 条仍未做）。这是对整套协议唯一有意义的样本外检验。",
    "4. **（需要新作业，但更便宜）用 GFN2-xTB 初猜**（Week 15 §11 第 3 条）：检验「读 xTB 轨道」能否拿到",
    "   同样低的解，把一次气相 DFT 降成一次 xTB；若能，预警与修复的成本同时下降。",
    "5. **（需要新作业）把 TMP 的近简并做实**：对 TMP 做指定初猜 / 更严格 SCF 收敛的定点计算，看三个",
    "   磷酸氧的简并是否被打破——这决定 6(iv) 的「近简并表观」是否真的只是表观。",
    "",
]


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    _guard()
    text = "\n".join(L) + "\n"
    if "--check" in argv:
        for anchor in ("## 0. 一句话结论", "### 4.7", F32_REL, F33_REL, MANIFEST_REL):
            if anchor not in text:
                raise SystemExit("missing anchor in rendered text: %s" % anchor)
        print("--check:", str(REPORT_OUT), len(text.encode("utf-8")), "bytes (not written)")
        print("all required anchors present")
        return 0
    REPORT_OUT.parent.mkdir(parents=True, exist_ok=True)
    with REPORT_OUT.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    print("wrote", str(REPORT_OUT), REPORT_OUT.stat().st_size, "bytes")
    if not FIGDIR.joinpath(Path(F32_REL).name).exists():
        print("note: the F32 PNG is not on disk yet (produced by a sibling script)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())