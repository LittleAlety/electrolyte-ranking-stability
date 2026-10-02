"""W24-C figure F51 -- the minimal-information-budget decision flowchart.

One portrait flowchart that turns two *textual* sections of the paper into a single
top-down decision path:

    section 3.11  minimal *calculation-layer* budget -> which layers must be computed
    section 3.14  minimal *expensive-label* budget   -> how many labels must be bought

The two budgets are orthogonal and must never be added together; the figure says so
explicitly in its footer.

Every number in the figure is resolved from a JSON product by dotted path at run time
(`resolve()`), so a stale figure cannot survive a data change.  The primary anchors are
the five named in the task brief; three further numbers live in files that those anchors
*declare as their own sources*, or that the paper's section 3.11 quotes verbatim.  Every
such hop is listed in `TRANSITIVE` and printed by `--check`, so provenance stays auditable.

Usage
-----
    python scripts/make_w24_flowchart.py             # write the PNG
    python scripts/make_w24_flowchart.py --check     # resolve every number, write nothing
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import warnings
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyBboxPatch  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTDIR = REPO_ROOT / "outputs" / "figures"
FIGURE_NAME = "F51_minimal_budget_flowchart.png"

#: the five primary anchors named in the task brief
ANCHORS = {
    "broad": "outputs/week22_hardening/broad_pool_demo.json",
    "decision": "outputs/week24_corealign/decision_metrics.json",
    "al": "outputs/week24_corealign/al_budget.json",
    "core": "outputs/week24_corealign/core_alignment.json",
    "ladder": "outputs/week9/stage10_ladder.json",
}

#: numbers that live one hop away, together with the anchor that declares the hop
TRANSITIVE = {
    # week22_hardening/allowance_factor2.json lists this under `sources.allowance`
    "allowance": (
        "outputs/week23/targeted_two_guess.json",
        "declared by outputs/week22_hardening/allowance_factor2.json:sources.allowance",
    ),
    # quoted verbatim by the paper's section 3.11 (dielectric residual at eps >= 200)
    "dielectric": (
        "outputs/week22/dielectric_limit.json",
        "quoted by paper section 3.11 (eps >= 200 residual)",
    ),
    # the 18/18 unbound-anion flag behind core_alignment.json / audit_tables.json
    "p1audit": (
        "outputs/week4/p1_core_set_audit.json",
        "quoted by outputs/week24_corealign/audit_tables.json:tables.qc_ledger",
    ),
}

# ---- house palette (same family as scripts/make_stage24_figure.py) ------------------
INK = "#1f2933"
MUTED = "#61707d"
ACCENT = "#2f6fb2"
WARN = "#c05621"
OK = "#2f855a"
ALT = "#6b46c1"
FACE = "#f7f9fb"

# ---- portrait layout constants (data units) -----------------------------------------
X0, X1 = 4.0, 96.0
PAD_TOP = 1.5
PAD_BOTTOM = 1.4
TITLE_STEP = 2.35
LINE_STEP = 2.20
SRC_STEP = 2.05
GAP = 2.9
FOOT_H = 6.0
UNIT_IN = 0.0665  # inches per data unit: A4 usable height is 9.16 in, so keep <= ~8.6 in


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()


def load(rel: str) -> dict:
    path = REPO_ROOT / rel
    if not path.exists():
        raise FileNotFoundError(f"data anchor missing: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


_TOKEN = re.compile(r"^(?P<key>[^\[\]]+)(?:\[(?P<idx>\d+)\])?$")


def resolve(data, dotted: str):
    """Walk `data` by a dotted path such as ``budget.union.n_full`` or ``ladder[0].n``."""

    node = data
    for token in dotted.split("."):
        match = _TOKEN.match(token)
        if not match:
            raise KeyError(f"unparsable path token {token!r} in {dotted!r}")
        key, index = match.group("key"), match.group("idx")
        node = node[int(key)] if isinstance(node, list) else node[key]
        if index is not None:
            node = node[int(index)]
    return node


def pick(text: str, pattern: str, label: str) -> float:
    """Read a number that a JSON *string* already carries, instead of re-hardcoding it."""

    match = re.search(pattern, text)
    if not match:
        raise KeyError(f"cannot find {label!r} (pattern {pattern!r}) in {text[:120]!r}")
    groups = [g for g in match.groups() if g is not None]
    return float(groups[0])


def collect() -> dict:
    """Resolve every number the figure shows.  Raises instead of silently degrading."""

    broad = load(ANCHORS["broad"])
    decision = load(ANCHORS["decision"])
    al = load(ANCHORS["al"])
    core = load(ANCHORS["core"])
    ladder = load(ANCHORS["ladder"])
    allowance = load(TRANSITIVE["allowance"][0])
    dielectric = load(TRANSITIVE["dielectric"][0])
    p1audit = load(TRANSITIVE["p1audit"][0])

    n = {}

    # -- input ------------------------------------------------------------------------
    n["core_n"] = resolve(broad, "meta.core_n")
    n["broad_n"] = resolve(broad, "meta.broad_n")
    n["common_n"] = resolve(ladder, "common_subset_size")
    n["native_n"] = resolve(ladder, "ladder[0].n")
    assert (n["core_n"], n["broad_n"], n["native_n"]) == (18, 40, 18), n
    assert n["common_n"] == 10, n

    # -- (1) is the cheap proxy already good enough? ----------------------------------
    rows = resolve(core, "tables.s22_branch_claims.rows")
    row_a = next(r for r in rows if r["letter"] == "A")
    n["branch_a_verdict"] = row_a["verdict"]
    assert n["branch_a_verdict"] == "NOT SUPPORTED", n["branch_a_verdict"]
    n["branch_a_tau"] = pick(row_a["evidence"], r"(?:τ_b|tau_b)\s*=\s*([0-9.]+)", "branch A tau_b")
    n["branch_a_overlap"] = pick(row_a["evidence"], r"Top-10%\s*重叠\s*([0-9.]+)", "overlap")
    n["branch_a_funres"] = pick(row_a["evidence"], r"f_unresolved\s*=\s*([0-9.]+)", "f_unres")
    assert abs(n["branch_a_tau"] - 0.673) < 5e-4, n

    # -- (2) the closed-form indistinguishability test ---------------------------------
    n["sqrt2"] = resolve(broad, "meta.sqrt2")
    n["z_from_p"] = resolve(decision, "z_from_p_threshold")
    n["n_pairs_common"] = resolve(decision, "rows[0].n_pairs")
    devs = [abs(resolve(r, "abs_dev_p_vs_closedform")) for r in resolve(decision, "consistency")]
    n["max_dev_p_vs_closedform"] = max(devs)
    assert n["max_dev_p_vs_closedform"] <= 1e-15, n["max_dev_p_vs_closedform"]
    assert n["n_pairs_common"] == 45, n

    # -- (3) missed-solution targeting -------------------------------------------------
    for axis, state in (("oxidation", "ox"), ("reduction", "red")):
        node = resolve(allowance, f"axes.{axis}")
        rung = resolve(node, "ladder[0]")
        assert rung["delta_kind"] == "allowance", rung["delta_kind"]
        assert abs(rung["delta_ev"] - resolve(node, "allowance_ev")) < 1e-12, rung
        n[f"{state}_a_axis"] = resolve(node, "allowance_ev")
        n[f"{state}_saving"] = 100.0 * rung["savings_fraction"]
        n[f"{state}_flips"] = rung["n_flips"]
        n[f"{state}_missed"] = resolve(node, "soundness_missed_flips")
        assert n[f"{state}_missed"] == 0, n
        n[f"{state}_topk_saving"] = 100.0 * resolve(node, "list_variant[0].boundary_savings")
        assert resolve(node, "list_variant[0].k_fraction") == 0.1, n
    assert n["ox_flips"] == 19 and n["red_flips"] == 21, n

    # -- (4) broad-pool upgrade list ---------------------------------------------------
    union = resolve(broad, "budget.union")
    n["union_full"] = resolve(union, "n_full")
    n["union_k10_n"] = resolve(union, "n_worth_union_axes_k10")
    n["union_k10_saving"] = resolve(union, "saving_union_axes_k10_pct")
    n["union_allk_n"] = resolve(union, "n_worth_union_axes_allk")
    n["union_allk_saving"] = resolve(union, "saving_union_axes_allk_pct")
    assert (n["union_full"], n["union_k10_n"], n["union_k10_saving"]) == (40, 21, 47.5), n
    assert (n["union_allk_n"], n["union_allk_saving"]) == (38, 5.0), n

    # -- (5) what may be skipped -------------------------------------------------------
    geo = [row for row in resolve(ladder, "ladder")
           if row["rung"] == "G1_to_G2" and row["population"] == "native"]
    assert len(geo) == 2, len(geo)
    n["geo_std_min"] = min(r["shift_std_ev"] for r in geo)
    n["geo_std_max"] = max(r["shift_std_ev"] for r in geo)
    n["geo_tau_min"] = min(r["kendall_tau_b"] for r in geo)
    n["geo_funres_max"] = max(r["f_unresolved_after"] for r in geo)
    n["geo_n"] = geo[0]["n"]
    assert n["geo_tau_min"] >= 0.848 and n["geo_funres_max"] <= 0.061, n

    n["eps200_residual_mev"] = resolve(dielectric, "pairs.200.max_abs_mev")
    n["delta_m_ox_mev"] = resolve(dielectric, "delta_m_mev.oxidation")
    n["eps200_share_pct"] = 100.0 * n["eps200_residual_mev"] / n["delta_m_ox_mev"]
    assert abs(n["eps200_share_pct"] - 2.80) < 0.01, n["eps200_share_pct"]

    n["unbound_anion"] = resolve(p1audit, "flag_counts.unbound_anion")
    n["unbound_total"] = resolve(p1audit, "n_molecules")
    assert n["unbound_anion"] == n["unbound_total"] == 18, n

    # -- (6) expensive-label budget ----------------------------------------------------
    sizes = resolve(al, "pool_sizes")
    by_pool = resolve(al, "key_n_T_by_pool")
    budget = resolve(al, "tau80_budget")
    small = [r["budget_n_T"] for r in budget if r["pool_n"] == 10]
    large = [r["budget_n_T"] for r in budget if r["pool_n"] == 18]
    assert small and large, by_pool
    n["label_small_min"], n["label_small_max"] = min(small), max(small)
    n["label_large_min"], n["label_large_max"] = min(large), max(large)
    # every per-(task, axis) key budget must sit inside its own pool's range
    for key, value in by_pool.items():
        lo, hi = (n["label_small_min"], n["label_small_max"]) if sizes[key] == 10 \
            else (n["label_large_min"], n["label_large_max"])
        assert lo <= value <= hi, (key, value, lo, hi)
    n["tau_threshold"] = resolve(al, "tau_threshold")
    n["n_endpoint_rows"] = resolve(al, "endpoint_self_check.n_endpoint_rows")
    n["n_repeats"] = resolve(al, "n_repeats")
    assert (n["label_small_min"], n["label_small_max"]) == (8, 9), n
    assert (n["label_large_min"], n["label_large_max"]) == (12, 15), n
    assert n["tau_threshold"] == 0.8, n

    return n


def halfwidth(text: str) -> int:
    """Width in half-width units, so a CJK glyph counts twice an ASCII one."""

    return sum(2 if ord(ch) > 0x2E80 else 1 for ch in text)


def wrap_src(text: str, budget: int = 130) -> list:
    """Greedy wrap for the provenance line, which is the only over-long text."""

    lines, current, width = [], "", 0
    for word in re.findall(r"\S+\s*", text):
        size = halfwidth(word)
        if current and width + size > budget:
            lines.append(current.rstrip())
            current, width = "", 0
        current += word
        width += size
    if current.strip():
        lines.append(current.rstrip())
    return lines or [""]


def box_height(n_lines: int, n_src: int = 1) -> float:
    return PAD_TOP + TITLE_STEP + n_lines * LINE_STEP + n_src * SRC_STEP + PAD_BOTTOM


def draw_box(ax, y_top: float, title: str, lines, src_lines, edge: str) -> float:
    height = box_height(len(lines), len(src_lines))
    y0 = y_top - height
    ax.add_patch(FancyBboxPatch((X0, y0), X1 - X0, height,
                                boxstyle="round,pad=0,rounding_size=1.0",
                                linewidth=1.3, edgecolor=edge, facecolor=FACE, zorder=2))
    ax.add_patch(FancyBboxPatch((X0, y0 + 0.9), 1.5, height - 1.8,
                                boxstyle="square,pad=0", linewidth=0,
                                facecolor=edge, zorder=3))
    cursor = y_top - PAD_TOP
    ax.text(X0 + 2.8, cursor, title, va="top", ha="left", fontsize=8.6,
            fontweight="bold", color=edge, zorder=4)
    cursor -= TITLE_STEP
    for line in lines:
        text, colour = line if isinstance(line, tuple) else (line, INK)
        ax.text(X0 + 2.8, cursor, text, va="top", ha="left", fontsize=7.3,
                color=colour, zorder=4)
        cursor -= LINE_STEP
    src_cursor = y0 + PAD_BOTTOM + 0.2 + SRC_STEP * (len(src_lines) - 1)
    for line in src_lines:
        ax.text(X0 + 2.8, src_cursor, line, va="bottom", ha="left",
                fontsize=5.6, color=MUTED, style="italic", zorder=4)
        src_cursor -= SRC_STEP
    return y0


def arrow(ax, y_from: float, y_to: float, label: str) -> None:
    ax.annotate("", xy=(50.0, y_to), xytext=(50.0, y_from),
                arrowprops=dict(arrowstyle="-|>", color=ACCENT, linewidth=1.5,
                                shrinkA=0, shrinkB=0, mutation_scale=13), zorder=1)
    if label:
        ax.text(52.0, (y_from + y_to) / 2.0, label, va="center", ha="left",
                fontsize=6.0, color=MUTED, zorder=4)


def build(n: dict, outpath: Path) -> Path:
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
    plt.rcParams["font.family"] = "sans-serif"
    plt.rcParams["axes.unicode_minus"] = False

    dev = n["max_dev_p_vs_closedform"]
    dev_text = "0" if dev == 0 else f"{dev:.1e}"

    boxes = [
        dict(
            title="【输入】候选分子集与分子对",
            lines=[
                f"core 集 {n['core_n']:.0f} 个分子（台阶 n = {n['native_n']:.0f}；两轴共享 {n['common_n']:.0f} 分子公共子集）；"
                f"broad 池 {n['broad_n']:.0f} 个分子",
                "目标：Top-k 候选清单的排序（不是绝对能量值）；两条轴：氧化 / 还原",
            ],
            src="week9/stage10_ladder.json · common_subset_size, ladder[0].n ｜ week22_hardening/broad_pool_demo.json · meta.core_n, meta.broad_n",
            edge=INK,
        ),
        dict(
            title="① 最便宜的那一层够用吗？",
            lines=[
                f"否 —— 廉价代理不能替代目标层（§22 分支 A = {n['branch_a_verdict']}）",
                f"P0 → P2 氧化轴 τ_b = {n['branch_a_tau']:.3f}；Top-10% 重叠 = {n['branch_a_overlap']:.3f}；"
                f"f_unresolved = {n['branch_a_funres']:.3f}",
                "→ 值误差与排序都被改写：必须继续往下走，不能只跑 P0 就交差",
            ],
            src="week24_corealign/core_alignment.json · tables.s22_branch_claims.rows[0]（数字取自该字段原文）",
            edge=WARN,
        ),
        dict(
            title="② 零成本先剔除「本来就不可能被分辨」的分子对",
            lines=[
                f"闭式判据  q_ij ≤ √2 / z，其中 σ_ij = |δ_i − δ_j| / √2（√2 = {n['sqrt2']:.6f}）",
                f"取 §9.4 的 0.1 / 0.9 阈值 → z = Φ^(-1)(0.9) = {n['z_from_p']:.4f}",
                "一致性验证：逐对概率 p_ij 导出的 unresolved 与闭式 f_unresolved 逐点相等，"
                f"max|Δ| = {dev_text}（判据 ≤ 1e-15；{n['n_pairs_common']:.0f} 对逐对比较）",
            ],
            src="week24_corealign/decision_metrics.json · consistency[].abs_dev_p_vs_closedform, z_from_p_threshold ｜ week22_hardening/broad_pool_demo.json · meta.sqrt2",
            edge=ACCENT,
        ),
        dict(
            title="③ 自洽场多解：哪些格子必须「双腿」重算？",
            lines=[
                "方案：保护所有 |d0| < A_axis 的格子（靶向双腿），其余格子单腿",
                f"氧化轴 A_axis = {n['ox_a_axis']:.4f} eV：覆盖 {n['ox_flips']:.0f} 次翻转、"
                f"漏 {n['ox_missed']:.0f} 次，省 {n['ox_saving']:.1f}% 重算量",
                f"还原轴 A_axis = {n['red_a_axis']:.4f} eV：覆盖 {n['red_flips']:.0f} 次翻转、"
                f"漏 {n['red_missed']:.0f} 次，省 {n['red_saving']:.1f}% 重算量",
                f"若只保护 Top-10% 清单的边界对，则可省 {n['ox_topk_saving']:.1f}% / {n['red_topk_saving']:.1f}%",
            ],
            src="week23/targeted_two_guess.json · axes.{oxidation,reduction}.allowance_ev, ladder[0].{savings_fraction,n_flips}, soundness_missed_flips, list_variant[0].boundary_savings",
            edge=ALT,
        ),
        dict(
            title=f"④ 哪些分子值得升级到 P2 / C1？（broad 池 {n['broad_n']:.0f} 分子实测）",
            lines=[
                f"主判据（两轴并集、保护 Top-10% 清单、z = 1）：只需升级 {n['union_k10_n']:.0f}/{n['union_full']:.0f}，"
                f"省 {n['union_k10_saving']:.1f}%",
                f"保守口径（Top-10/20/30% 全保护）：需升级 {n['union_allk_n']:.0f}/{n['union_full']:.0f}，"
                f"仅省 {n['union_allk_saving']:.1f}%",
            ],
            src="week22_hardening/broad_pool_demo.json · budget.union.{n_worth_union_axes_k10, saving_union_axes_k10_pct, n_worth_union_axes_allk, saving_union_axes_allk_pct}",
            edge=OK,
        ),
        dict(
            title="⑤ 哪些计算层可以直接跳过？",
            lines=[
                (f"■ 可跳过：几何台阶 G1→G2 —— 位移 std {n['geo_std_min']:.3f}–{n['geo_std_max']:.3f} eV、"
                 f"τ_b ≥ {n['geo_tau_min']:.3f}、f_unresolved ≤ {n['geo_funres_max']:.3f}（n = {n['geo_n']:.0f}）", OK),
                (f"■ 可跳过：ε ≥ 200 的介电加密点 —— 残余 ≤ {n['eps200_residual_mev']:.1f} meV，"
                 f"仅占 δ_m(氧化) {n['delta_m_ox_mev']:.1f} meV 的 {n['eps200_share_pct']:.2f}%", OK),
                (f"■ 不可省：单一连续介质（环境）层 —— 气相阴离子 {n['unbound_anion']:.0f}/{n['unbound_total']:.0f} 不束缚，"
                 "还原轴必须带连续介质才算物理量", WARN),
            ],
            src="week9/stage10_ladder.json · ladder[G1_to_G2] ｜ week22/dielectric_limit.json · pairs.200.max_abs_mev, delta_m_mev.oxidation ｜ week4/p1_core_set_audit.json · flag_counts.unbound_anion",
            edge=ACCENT,
        ),
        dict(
            title="⑥ 层定好之后：还要买多少个昂贵标签？",
            lines=[
                f"中位 τ_b 首次 ≥ {n['tau_threshold']:.2f} 所需标签数：10 分子池 "
                f"{n['label_small_min']:.0f}–{n['label_small_max']:.0f} 个；18 分子池 "
                f"{n['label_large_min']:.0f}–{n['label_large_max']:.0f} 个",
                f"（{n['n_repeats']:.0f} 组冻结种子回溯重放；已排除 n_T = n 的构造性端点 {n['n_endpoint_rows']:.0f} 行）",
                "提示性结论：uncertainty 最省；ranking_aware 未稳定胜出（区间两两重叠，不可写成「显著更优」）",
            ],
            src="week24_corealign/al_budget.json · key_n_T_by_pool, pool_sizes, tau_threshold, endpoint_self_check.n_endpoint_rows",
            edge=INK,
        ),
    ]
    arrows = ["① 先探最便宜的一层", "否 → 必须升级", "先给出不可分辨对清单",
              "多解风险已定价", "升级清单已定", "层已定 → 给标签定价"]

    for spec in boxes:
        spec["src_lines"] = wrap_src(spec["src"])

    total = (sum(box_height(len(b["lines"]), len(b["src_lines"])) for b in boxes)
             + GAP * len(arrows) + FOOT_H + 2.0)
    fig = plt.figure(figsize=(6.3, total * UNIT_IN), facecolor="white")
    ax = fig.add_axes([0.0, 0.0, 1.0, 1.0])
    ax.set_xlim(-1.5, 101.5)
    ax.set_ylim(-1.5, total + 1.5)
    ax.axis("off")

    cursor = total
    for index, spec in enumerate(boxes):
        cursor = draw_box(ax, cursor, spec["title"], spec["lines"], spec["src_lines"],
                          spec["edge"])
        if index < len(arrows):
            arrow(ax, cursor, cursor - GAP, arrows[index])
            cursor -= GAP

    cursor -= 1.0
    ax.add_patch(FancyBboxPatch((X0, cursor - FOOT_H + 1.0), X1 - X0, FOOT_H - 2.0,
                                boxstyle="round,pad=0,rounding_size=0.8", linewidth=1.1,
                                edgecolor=INK, facecolor="#eef2f6", zorder=2))
    ax.text((X0 + X1) / 2.0, cursor - 1.7,
            "两条预算互不相加：§3.11 计算层预算 = 该算哪些层；§3.14 昂贵标签预算 = 该买多少标签",
            va="top", ha="center", fontsize=7.4, fontweight="bold", color=INK, zorder=4)
    ax.text((X0 + X1) / 2.0, cursor - 4.1,
            "全部数字由 JSON 产物按点路径解析；标注为上游的来自锚点文件自身声明的来源",
            va="top", ha="center", fontsize=5.8, color=MUTED, zorder=4)

    outpath.parent.mkdir(parents=True, exist_ok=True)
    # a tofu box is a silent, reviewable defect: refuse to ship a figure with a missing glyph
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        fig.savefig(str(outpath), dpi=200, facecolor="white")
    missing = [str(w.message) for w in caught if "missing from font" in str(w.message)]
    if missing:
        raise RuntimeError("missing glyphs in figure (would render as boxes): " + "; ".join(missing))
    plt.close(fig)
    return outpath


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outdir", default=str(DEFAULT_OUTDIR))
    parser.add_argument("--check", action="store_true",
                        help="resolve every number and report provenance; write nothing")
    args = parser.parse_args()

    n = collect()
    if args.check:
        print("F51 minimal-information-budget flowchart -- resolved numbers")
        print("-" * 68)
        for key in sorted(n):
            print(f"  {key:26s} {n[key]!r}")
        print("-" * 68)
        for key, (rel, why) in TRANSITIVE.items():
            path = REPO_ROOT / rel
            print(f"  hop {key:11s} {rel}  ({why})  sha256={sha256(path)[:12]}")
        for key, rel in ANCHORS.items():
            print(f"  anchor {key:9s} {rel}")
        target = Path(args.outdir) / FIGURE_NAME
        print(f"  figure {target} exists={target.exists()}")
        return 0

    outpath = build(n, Path(args.outdir) / FIGURE_NAME)
    print(f"wrote {outpath} ({outpath.stat().st_size} bytes) sha256={sha256(outpath)[:16]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
