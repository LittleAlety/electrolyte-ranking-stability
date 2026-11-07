"""Stage 24 figures (F45, F46) -- pricing the two-guess targeting and the shell-3 check.

F45 (R8: what does targeting the near-degenerate cells actually buy?)

    (a) the per-cell `|effect|` whose maximum *is* the missed-solution allowance:
        one strip per axis on a shared log axis, each carrying its own `A_axis`
        (solid), its own frozen `delta_m` (dashed) and the Stage 16 material
        threshold.  The two axes differ by an order of magnitude, so they get one
        sub-axis each instead of a shared y.
    (b) `targeted_fraction` against the near-degeneracy threshold, read straight off
        the four-rung ladder; the allowance rung is the only rung that is affordable
        *before* any second guess is run.
    (c) protocol check: the targeted two-leg ranking against the full two-leg ranking,
        per epsilon, with the single-leg protocol as the control.
    (d) the Top-k list variant: protect only the boundary of the top-k list.

F46 (R5: a third coordination shell of EC at GFN2-xTB)

    (a) the shift ladder n = 0..3, both axes.
    (b) the increments dd(n->n-1), which is where "consistent with saturation" is read.
    (c) the cross-level comparison in the only currency that transfers between two
        methods: a dimensionless ratio, not an absolute shift.

Every number is read from the JSON/CSV products under `--data-dir`; the only literals
are protocol constants, colours and the three top-k fractions.  In-figure text is ASCII
on purpose (no guaranteed CJK font); the manifest captions, which the week report quotes
verbatim, are Chinese.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import shutil
import tempfile
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.ticker import NullFormatter  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = REPO_ROOT / "outputs" / "week23"
DEFAULT_OUTDIR = REPO_ROOT / "outputs" / "figures"
CELLS_CSV = REPO_ROOT / "outputs" / "week15" / "stage16_cells.csv"

MANIFEST_NAME = "figure_manifest_week23_stage24.md"
FIGURE_F45 = "F45_targeted_two_guess.png"
FIGURE_F46 = "F46_shell3_saturation.png"

#: frozen Hartree -> eV conversion used by every decision quantity in the project
HARTREE_EV = 27.211386245988
#: Stage 16 material threshold, inherited unchanged (week 14 -> week 15)
MATERIAL_EV = 0.001
#: the three list-variant fractions the product carries; asserted against the data
TOP_K_FRACTIONS = (0.1, 0.2, 0.3)

AXES = (("oxidation", "cation"), ("reduction", "anion"))

INK = "#1f2933"
GRID = "#d6dde5"
ACCENT = "#2f6fb2"
WARN = "#c05621"
OK = "#2f855a"
ALT = "#6b46c1"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def save(fig, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(str(path), dpi=170, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path


def _style(ax) -> None:
    ax.set_facecolor("white")
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
    ax.grid(True, color=GRID, linewidth=0.6, alpha=0.9)
    ax.tick_params(colors=INK, labelsize=8)
    ax.set_axisbelow(True)


def _write(path: Path, text: str) -> Path:
    """Write UTF-8 with LF endings, through a temporary file, so the bytes are stable."""

    path.parent.mkdir(parents=True, exist_ok=True)
    handle, name = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    os.close(handle)
    tmp = Path(name)
    try:
        with io.open(tmp, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()
    return path


def per_cell_effects(path: Path) -> dict:
    """Recompute, per axis, the per-cell effect that the allowance is the maximum of.

    A missed solution moves the decision quantity `value = (E_charged - E_neutral) *
    Ha2eV`, so the effect is the difference of the two arms on the **full** expression.
    Taking only the charged term, `|E_charged(moread) - E_charged(default)|`, leaves a
    residual of up to the frozen convention gap (1.6e-5 eV here) and no longer reproduces
    the frozen allowance to 1e-9.  The 16-cell material subset is identical either way.
    """

    rows = list(csv.DictReader(io.open(path, encoding="utf-8")))
    table = {}
    for row in rows:
        table[(row["name"], row["state"], float(row["epsilon"]))] = (
            float(row["e_default_eh"]), float(row["e_moread_eh"]), float(row["delta_ev"]))
    names = sorted({row["name"] for row in rows})
    epsilons = sorted({float(row["epsilon"]) for row in rows})

    effects = {}
    for axis, state in AXES:
        cells = []
        for epsilon in epsilons:
            for name in names:
                neutral = table[(name, "neutral", epsilon)]
                charged = table[(name, state, epsilon)]
                effect = (((charged[1] - neutral[1]) - (charged[0] - neutral[0]))
                          * HARTREE_EV)
                cells.append({"name": name, "epsilon": epsilon, "effect_ev": effect,
                              "abs_effect_ev": abs(effect), "delta_ev": charged[2]})
        effects[axis] = cells
    return effects


def material_cells(cells: list) -> list:
    """The Stage 16 material subset: `|delta_ev| >= 0.001` on the charged term."""

    return [cell for cell in cells if abs(cell["delta_ev"]) >= MATERIAL_EV]


def check_allowance(effects: dict, payload: dict) -> dict:
    """The two frozen maxima, re-derived.  Raises rather than drawing a wrong number."""

    out = {}
    for axis, _state in AXES:
        material = material_cells(effects[axis])
        if len(material) != 16:
            raise SystemExit("F45: %s has %d material cells, expected 16"
                             % (axis, len(material)))
        top = max(material, key=lambda cell: cell["abs_effect_ev"])
        frozen = payload["allowance_ev"][axis]
        if abs(top["abs_effect_ev"] - frozen) >= 1e-9:
            raise SystemExit("F45: %s max per-cell |effect| = %.12f eV does not reproduce "
                             "the frozen allowance %.12f eV"
                             % (axis, top["abs_effect_ev"], frozen))
        detail = payload["allowance_detail"][axis]
        if (top["name"] != detail["worst_cell"]["name"]
                or float(top["epsilon"]) != float(detail["worst_cell"]["epsilon"])):
            raise SystemExit("F45: %s worst cell %s@%g disagrees with allowance_detail %s@%g"
                             % (axis, top["name"], top["epsilon"],
                                detail["worst_cell"]["name"], detail["worst_cell"]["epsilon"]))
        out[axis] = {"max_ev": frozen, "worst": top}
    return out


def figure_f45(outdir: Path, payload: dict, effects: dict, limits: dict) -> Path:
    names = payload["names"]
    epsilons = payload["epsilons"]
    if len(names) != 12 or len(epsilons) != 10:
        raise SystemExit("F45: expected 12 molecules x 10 epsilons, got %d x %d"
                         % (len(names), len(epsilons)))
    per_axis = payload["axes"]["oxidation"]["ladder"][0]["n_cells_total"]
    if per_axis != len(names) * len(epsilons) or payload["n_cells_total"] != 2 * per_axis:
        raise SystemExit("F45: %d cells per axis / %d in total disagree with %d x %d"
                         % (per_axis, payload["n_cells_total"], len(names), len(epsilons)))
    if any(payload["axes"][axis]["ladder"][0]["n_cells_total"] != per_axis
           for axis, _state in AXES):
        raise SystemExit("F45: the two axes carry different cell counts")

    fig = plt.figure(figsize=(13.4, 9.8))
    outer = fig.add_gridspec(2, 1, height_ratios=[1.06, 1.0], hspace=0.30)
    top = outer[0].subgridspec(1, 2, wspace=0.34)
    bottom = outer[1].subgridspec(1, 3, wspace=0.42)

    # ---------------------------------------------------------------- (a)
    for index, (axis, _state) in enumerate(AXES):
        ax = fig.add_subplot(top[0, index])
        _style(ax)
        entry = payload["axes"][axis]
        detail = payload["allowance_detail"][axis]
        material = sorted(material_cells(effects[axis]),
                          key=lambda cell: cell["abs_effect_ev"])
        values = [cell["abs_effect_ev"] for cell in material]
        allowance = entry["allowance_ev"]
        colours = [WARN if abs(value - allowance) < 1e-12 else ACCENT for value in values]
        positions = np.arange(len(material))
        ax.barh(positions, values, color=colours, height=0.7)
        ax.set_yticks(positions)
        ax.set_yticklabels(["%s@%g" % (cell["name"], cell["epsilon"]) for cell in material],
                           fontsize=6.4, color=INK)
        ax.set_xscale("log")
        ax.set_xlim(min(values) * 0.5, entry["delta_m_ev"] * 2.0)
        ax.axvline(allowance, color=WARN, lw=1.9,
                   label="A_axis = %.4f eV = %.1f%% of delta_m"
                         % (allowance, 100.0 * entry["allowance_over_delta_m"]))
        ax.axvline(entry["delta_m_ev"], color=ALT, lw=1.4, ls="--",
                   label="frozen delta_m = %.4f eV" % entry["delta_m_ev"])
        ax.axvline(MATERIAL_EV, color=GRID, lw=1.2, ls=":",
                   label="1 meV material threshold")
        ax.set_xlabel("per-cell |effect| on the decision quantity (eV, log)",
                      fontsize=8, color=INK)
        worst = limits[axis]["worst"]
        ax.set_title("(a) %s axis: the 16 material cells whose max is A_axis\n"
                     "worst = %s@eps=%g (%.6f eV); median %.6f, p90 %.6f"
                     % (axis, worst["name"], worst["epsilon"], worst["abs_effect_ev"],
                        detail["material_median_ev"], detail["material_p90_ev"]),
                     fontsize=9, color=INK, loc="left")
        ax.legend(fontsize=6.3, frameon=False, loc="lower right")

    # ---------------------------------------------------------------- (b)
    ax = fig.add_subplot(bottom[0, 0])
    _style(ax)
    markers = {"allowance": ("o", 9), "delta_m": ("s", 8), "delta_star_post_hoc": ("^", 8)}
    rungs = []
    for axis, colour in (("oxidation", WARN), ("reduction", ACCENT)):
        entry = payload["axes"][axis]
        ladder = sorted(entry["ladder"], key=lambda item: item["delta_ev"])
        ax.step([item["delta_ev"] for item in ladder],
                [item["targeted_fraction"] for item in ladder],
                where="post", color=colour, lw=1.7, label="%s axis" % axis)
        for item in ladder:
            spec = markers.get(item["delta_kind"])
            if spec is None:
                continue
            ax.plot([item["delta_ev"]], [item["targeted_fraction"]], spec[0], color=colour,
                    ms=spec[1], markeredgecolor=INK, markeredgewidth=0.5, zorder=5)
        rungs.append((axis, colour,
                      [item for item in ladder if item["delta_kind"] == "allowance"][0]))
    ax.set_xscale("log")
    ax.set_xticks([0.14, 0.2, 0.3, 0.5, 0.7, 1.0, 2.0])
    ax.set_xticklabels(["0.14", "0.2", "0.3", "0.5", "0.7", "1.0", "2.0"],
                       fontsize=7.2, color=INK)
    ax.xaxis.set_minor_formatter(NullFormatter())
    ax.set_ylim(0.30, 1.12)
    ax.set_xlabel("near-degeneracy threshold delta (eV, log)", fontsize=8, color=INK)
    ax.set_ylabel("fraction of the %d cells to treat" % per_axis,
                  fontsize=8, color=INK)
    ax.set_title("(b) targeting fraction vs threshold", fontsize=9, color=INK, loc="left")
    ax.legend(fontsize=7, frameon=False, loc="center right")
    for index, (axis, colour, rung) in enumerate(rungs):
        ax.text(0.025, 0.185 - 0.072 * index,
                "%s: A = %.4f eV -> target %.1f%%, saves %.1f%%, missed %d"
                % (axis, rung["delta_ev"], 100.0 * rung["targeted_fraction"],
                   100.0 * rung["savings_fraction"], rung["n_flips_missed"]),
                transform=ax.transAxes, fontsize=6.2, color=colour)
    ax.text(0.025, 0.030, "key: circle A_axis, square delta_m, triangle delta_star",
            transform=ax.transAxes, ha="left", va="bottom", fontsize=6.2, color=INK)

    # ---------------------------------------------------------------- (c)
    ax = fig.add_subplot(bottom[0, 1])
    _style(ax)
    for axis, colour, marker in (("oxidation", WARN, "s"), ("reduction", ALT, "^")):
        protocol = payload["axes"][axis]["protocol"]
        rows = protocol["tau_b_single_vs_full"]
        if len(rows) != len(epsilons):
            raise SystemExit("F45: %s carries %d protocol epsilons, expected %d"
                             % (axis, len(rows), len(epsilons)))
        ax.plot([row["epsilon"] for row in rows], [row["tau_b"] for row in rows],
                marker=marker, color=colour, lw=1.5, ms=5,
                label="single-leg vs full (%s), min %.4f"
                      % (axis, protocol["min_tau_b_single_vs_full"]))
        if any(abs(row["tau_b"] - 1.0) > 1e-12 for row in protocol["tau_b_vs_full"]):
            raise SystemExit("F45: the %s targeted protocol is not exactly the full "
                             "two-leg ranking" % axis)
    targeted = payload["axes"]["oxidation"]["protocol"]["tau_b_vs_full"]
    ax.plot([row["epsilon"] for row in targeted], [row["tau_b"] for row in targeted],
            color=OK, lw=2.4, marker="o", ms=5,
            label="targeted vs full two-leg\n(both axes, exactly 1.000 at every epsilon)")
    ax.set_xscale("log")
    ax.set_ylim(0.82, 1.07)
    ax.axhline(1.0, color=GRID, lw=1.0, ls=":")
    ax.set_xlabel("epsilon (log)", fontsize=8, color=INK)
    ax.set_ylabel("Kendall tau_b against the full two-leg ranking", fontsize=8, color=INK)
    ax.set_title("(c) protocol check, per epsilon", fontsize=9, color=INK, loc="left")
    ax.text(0.975, 0.965, "targeted = full two-leg\nsingle-leg = control",
            transform=ax.transAxes, ha="right", va="top", fontsize=6.6, color=INK)
    ax.legend(fontsize=6.5, frameon=False, loc="lower left")

    # ---------------------------------------------------------------- (d)
    ax = fig.add_subplot(bottom[0, 2])
    _style(ax)
    width = 0.36
    for index, (axis, colour) in enumerate((("oxidation", WARN), ("reduction", ACCENT))):
        variants = payload["axes"][axis]["list_variant"]
        fractions = tuple(item["k_fraction"] for item in variants)
        if fractions != TOP_K_FRACTIONS:
            raise SystemExit("F45: %s list variants %s do not match %s"
                             % (axis, fractions, TOP_K_FRACTIONS))
        positions = np.arange(len(variants)) + (index - 0.5) * width
        savings = [100.0 * item["boundary_savings"] for item in variants]
        ax.bar(positions, savings, width, color=colour, edgecolor=INK, linewidth=0.6,
               label="%s axis" % axis)
        for position, item, value in zip(positions, variants, savings):
            ax.text(position, value + 1.8, "%.1f%%\n%d/%d"
                    % (value, item["n_boundary_cells"], per_axis),
                    ha="center", fontsize=6.6, color=INK)
    ax.set_xticks(np.arange(len(TOP_K_FRACTIONS)))
    ax.set_xticklabels(["k=1\n(10%)", "k=2\n(20%)", "k=4\n(30%)"], fontsize=7.5, color=INK)
    ax.set_ylim(0.0, 118.0)
    ax.set_ylabel("cells that skip the second guess (savings, %)", fontsize=8, color=INK)
    ax.set_title("(d) Top-k list variant", fontsize=9, color=INK, loc="left")
    ax.text(0.02, 0.98, "labels: boundary cells / %d" % per_axis,
            transform=ax.transAxes, ha="left", va="top", fontsize=6.2, color=INK)
    ax.legend(fontsize=7, frameon=False, loc="upper right")

    fig.suptitle("F45  R8: pricing the targeted two-guess -- the allowance is sound, but it "
                 "buys almost nothing; the Top-k variant is what really saves work",
                 fontsize=10.5, color=INK, x=0.005, ha="left", y=0.985)
    return save(fig, outdir / FIGURE_F45)


def figure_f46(outdir: Path, payload: dict) -> Path:
    rows = payload["rows"]
    increments = payload["increments"]
    reference = payload["stage9_reference"]
    if not reference.get("available"):
        raise SystemExit("F46: the Stage 9 r2SCAN-3c reference rows are not available")

    fig, axes = plt.subplots(1, 3, figsize=(13.4, 4.9))

    # ---------------------------------------------------------------- (a)
    ax = axes[0]
    _style(ax)
    ns = [row["n"] for row in rows]
    ax.plot(ns, [row["d_ip_ev"] for row in rows], "o-", color=WARN, lw=1.8, ms=6,
            label="oxidation: dIP(n)")
    ax.plot(ns, [row["d_ea_ev"] for row in rows], "s-", color=ACCENT, lw=1.8, ms=6,
            label="reduction: dEA(n)")
    for row in rows[1:]:
        ax.annotate("%.3f" % row["d_ip_ev"], (row["n"], row["d_ip_ev"]),
                    textcoords="offset points", xytext=(5, 4), fontsize=6.6, color=WARN)
        ax.annotate("%.3f" % row["d_ea_ev"], (row["n"], row["d_ea_ev"]),
                    textcoords="offset points", xytext=(5, -10), fontsize=6.6, color=ACCENT)
    ax.axhline(0.0, color=GRID, lw=1.0)
    ax.set_xticks(ns)
    ax.set_xticklabels(["%d\n%s" % (row["n"], row["reference_label"]) for row in rows],
                       fontsize=6.2, color=INK)
    ax.set_ylim(-0.7, max(row["d_ea_ev"] for row in rows) * 1.26)
    ax.set_ylabel("shift against free EC (eV)", fontsize=8, color=INK)
    ax.set_title("(a) GFN2-xTB shell ladder, n = 0..3", fontsize=9, color=INK, loc="left")
    ax.legend(fontsize=7, frameon=False, loc="upper right")
    ax.text(0.02, 0.03, "absolute values are comparable only inside this panel",
            transform=ax.transAxes, ha="left", va="bottom", fontsize=6.2, color=INK)

    # ---------------------------------------------------------------- (b)
    ax = axes[1]
    _style(ax)
    steps = sorted(int(key) for key in increments["d_ip_ev"])
    if steps != sorted(int(key) for key in increments["d_ea_ev"]):
        raise SystemExit("F46: the two axes carry different increment ladders")
    positions = np.arange(len(steps))
    width = 0.36
    ip = [increments["d_ip_ev"][str(step)] for step in steps]
    ea = [increments["d_ea_ev"][str(step)] for step in steps]
    ax.bar(positions - width / 2, ip, width, color=WARN, edgecolor=INK, linewidth=0.6,
           label="oxidation")
    ax.bar(positions + width / 2, ea, width, color=ACCENT, edgecolor=INK, linewidth=0.6,
           label="reduction")
    for position, value in zip(positions - width / 2, ip):
        ax.text(position, value + (0.14 if value >= 0 else -0.28), "%.3f" % value,
                ha="center", va="bottom" if value >= 0 else "top", fontsize=6.8, color=WARN)
    for position, value in zip(positions + width / 2, ea):
        ax.text(position, value + (0.14 if value >= 0 else -0.28), "%.3f" % value,
                ha="center", va="bottom" if value >= 0 else "top", fontsize=6.8, color=ACCENT)
    ax.axhline(0.0, color=INK, lw=0.9)
    ax.set_xticks(positions)
    ax.set_xticklabels(["dd(%d->%d)" % (step, step - 1) for step in steps],
                       fontsize=7.5, color=INK)
    ax.set_ylim(min(min(ip), min(ea)) * 1.90, max(max(ip), max(ea)) * 1.32)
    ax.set_ylabel("increment dd(n->n-1) (eV)", fontsize=8, color=INK)
    ratio = increments["ratio"]
    ax.set_title("(b) increments: same sign, shrinking size\n"
                 "ratio ox %.3f / red %.3f"
                 % (ratio["ip"], ratio["ea"]),
                 fontsize=9, color=INK, loc="left")
    ax.legend(fontsize=7, frameon=False, loc="upper right")
    ax.text(0.02, 0.02,
            "dd(3->2)/dd(2->1); sign ox=%s red=%s, shrink ox=%s red=%s; %s"
            % (increments["sign_persists"]["ip"], increments["sign_persists"]["ea"],
               increments["magnitude_shrinks"]["ip"], increments["magnitude_shrinks"]["ea"],
               payload["verdict"]["label"]),
            transform=ax.transAxes, fontsize=5.9, color=INK)

    # ---------------------------------------------------------------- (c)
    ax = axes[2]
    _style(ax)
    groups = (("oxidation", reference["ratio_ip"], increments["ratio_2to1"]["ip"]),
              ("reduction", reference["ratio_ea"], increments["ratio_2to1"]["ea"]))
    positions = np.arange(len(groups))
    theirs = [group[1] for group in groups]
    ours = [group[2] for group in groups]
    ax.bar(positions - width / 2, theirs, width, color=ALT, edgecolor=INK, linewidth=0.6,
           label=reference["method"])
    ax.bar(positions + width / 2, ours, width, color=OK, edgecolor=INK, linewidth=0.6,
           label="GFN2-xTB (this work)")
    for position, value in zip(positions - width / 2, theirs):
        ax.text(position, value - 0.02, "%.3f" % value, ha="center", va="top",
                fontsize=7, color=ALT)
    for position, value in zip(positions + width / 2, ours):
        ax.text(position, value - 0.02, "%.3f" % value, ha="center", va="top",
                fontsize=7, color=OK)
    ax.axhline(0.0, color=INK, lw=0.9)
    ax.set_xticks(positions)
    ax.set_xticklabels(["%s axis" % group[0] for group in groups], fontsize=8, color=INK)
    ax.set_ylim(min(min(theirs), min(ours)) * 1.45, 0.10)
    ax.set_ylabel("dd(2->1)/dd(1->0) (dimensionless)", fontsize=8, color=INK)
    deviations = [100.0 * abs(group[2] - group[1]) / abs(group[1]) for group in groups]
    ax.set_title("(c) cross-level check, ratios only", fontsize=9, color=INK, loc="left")
    ax.text(0.975, 0.965, "deviation from r2SCAN-3c: ox %.0f%%, red %.0f%%"
            % (deviations[0], deviations[1]),
            transform=ax.transAxes, ha="right", va="top", fontsize=6.6, color=INK)
    ax.legend(fontsize=6.6, frameon=False, loc="lower right")
    ax.text(0.02, 0.02, "absolute values do not transfer (docs/18)",
            transform=ax.transAxes, fontsize=6.0, color=INK)

    fig.suptitle("F46  R5: a third EC shell at GFN2-xTB -- the sign and the shrinking step "
                 "survive, the absolute numbers do not transfer",
                 fontsize=10.5, color=INK, x=0.005, ha="left", y=1.00)
    fig.tight_layout()
    fig.subplots_adjust(wspace=0.34)
    return save(fig, outdir / FIGURE_F46)


AXIS_CN = {"oxidation": "氧化", "reduction": "还原"}


def caption_f45(payload: dict, effects: dict, limits: dict) -> str:
    per_axis = []
    for axis, _state in AXES:
        entry = payload["axes"][axis]
        detail = payload["allowance_detail"][axis]
        rung = [item for item in entry["ladder"] if item["delta_kind"] == "allowance"][0]
        worst = limits[axis]["worst"]
        per_axis.append(
            f"{AXIS_CN[axis]}轴：A_axis = **{entry['allowance_ev']:.6f} eV**"
            f"（冻结 delta_m {entry['delta_m_ev']:.6f} eV 的 "
            f"{100.0 * entry['allowance_over_delta_m']:.1f}%，"
            f"最坏格子 {worst['name']}@eps={worst['epsilon']:g}）；"
            f"16 个 material 格子中位数 {detail['material_median_ev']:.6f} eV、"
            f"p90 {detail['material_p90_ev']:.6f} eV；"
            f"按 A_axis 靶向，{rung['n_cells_total']} 格里只需双腿 {rung['n_targeted_cells']} 格"
            f"（{100.0 * rung['targeted_fraction']:.1f}%，省 {100.0 * rung['savings_fraction']:.1f}%），"
            f"实测翻转 {entry['n_flips']}/{entry['n_pairs']} 对，漏掉 {rung['n_flips_missed']} 个。")
    head = ("**R8 —— 给「靶向双腿」定价。** 容许量 A_axis 定义为逐格效应量的最大值，"
            "即一次漏解能给单个格子带来的最大位移。") + "".join(per_axis)
    protocol = []
    for axis, _state in AXES:
        entry = payload["axes"][axis]["protocol"]
        protocol.append(f"{AXIS_CN[axis]} min tau_b = {entry['min_tau_b_vs_full']:.4f}"
                        f"（单腿对照 {entry['min_tau_b_single_vs_full']:.4f}）")
    variants = []
    for axis, _state in AXES:
        entry = payload["axes"][axis]
        star = [item for item in entry["ladder"]
                if item["delta_kind"] == "delta_star_post_hoc"][0]
        missed = "、".join(star["missed_pairs"]) if star["missed_pairs"] else "无"
        first, last = entry["list_variant"][0], entry["list_variant"][-1]
        variants.append(
            f"{AXIS_CN[axis]}事后 delta_star = {star['delta_ev']:.6f} eV 省 "
            f"{100.0 * star['savings_fraction']:.1f}%（但漏 {star['n_flips_missed']} 个翻转：{missed}）；"
            f"只保护 Top-k 清单边界的变体 k=1 省 {100.0 * first['boundary_savings']:.1f}%"
            f"（{first['n_boundary_cells']}/120 格），k=4 省 {100.0 * last['boundary_savings']:.1f}%"
            f"（{last['n_boundary_cells']}/120 格）。")
    tail = ("(a) 两条轴的 16 个 material 逐格效应量与各自的 A_axis、冻结 delta_m 画在同一对数轴上；"
            "(b) 靶向比例随阈值 delta 的阶梯。(c) 协议校验：靶向协议在 10 个 eps 上与全双腿逐层同排序，"
            + "，".join(protocol) + "。(d) 只有保护清单边界的变体真正省钱："
            + "".join(variants)
            + "结论：靶向规则**安全但几乎不省钱** —— 12 分子 x 10 介电的 pair 谱本来就密，"
              "真正省下计算的是只保护 Top-k 清单边界的变体；A_axis 是**靶向之前**就能算出来的量，"
              "delta_star 只有把双腿全部算完才拿得到。")
    return head + tail


def caption_f46(payload: dict) -> str:
    rows = payload["rows"]
    increments = payload["increments"]
    reference = payload["stage9_reference"]
    ladder = "；".join(
        f"n={row['n']} {row['reference_label']} dIP {row['d_ip_ev']:.3f} / dEA {row['d_ea_ev']:.3f} eV"
        for row in rows)
    steps = sorted(int(key) for key in increments["d_ip_ev"])
    inc = "；".join(
        f"dd({step}->{step - 1}) 氧化 {increments['d_ip_ev'][str(step)]:+.3f} / "
        f"还原 {increments['d_ea_ev'][str(step)]:+.3f} eV"
        for step in steps)
    signs = increments["sign_persists"]
    shrink = increments["magnitude_shrinks"]
    ratios = increments["ratio"]
    cross = increments["ratio_2to1"]
    deviation_ip = 100.0 * abs(cross["ip"] - reference["ratio_ip"]) / abs(reference["ratio_ip"])
    deviation_ea = 100.0 * abs(cross["ea"] - reference["ratio_ea"]) / abs(reference["ratio_ea"])
    return ("**R5 —— EC 第三配位壳的符号/形状检验（GFN2-xTB，非 r2SCAN-3c）。** "
            f"阶梯（相对自由 EC）：{ladder}。"
            f"增量：{inc}；两个轴的 dd(3->2) 与 dd(2->1) 同号且绝对值更小"
            f"（sign_persists 氧化 {signs['ip']} / 还原 {signs['ea']}，"
            f"magnitude_shrinks 氧化 {shrink['ip']} / 还原 {shrink['ea']}），"
            f"比值 dd(3->2)/dd(2->1) 氧化 {ratios['ip']:.3f} / 还原 {ratios['ea']:.3f}，"
            f"判决 `{payload['verdict']['label']}`。"
            f"跨层级只比无量纲比值 dd(2->1)/dd(1->0)：氧化 {cross['ip']:.3f} vs r2SCAN-3c "
            f"{reference['ratio_ip']:.3f}（偏差 {deviation_ip:.0f}%），还原 {cross['ea']:.3f} vs "
            f"{reference['ratio_ea']:.3f}（偏差 {deviation_ea:.0f}%）—— 还原轴这一比值受 "
            "state-identity 影响，**不可搬运**，只能当提示。"
            f"(a) n = 0..3 的阶梯（共 {payload['n_jobs']} 个 xTB 作业），"
            "(b) 增量柱状图，(c) 跨层级比值对照。GFN2-xTB 的绝对值不得与 docs/18 的 r2SCAN-3c "
            "阶梯并列（产物自带的 level_caveat），只有符号与单调性可比。")


def inputs_for(data_dir: Path) -> list:
    return [data_dir / "targeted_two_guess.json",
            data_dir / "shell3_xtb_sign_test.json",
            CELLS_CSV]


def write_manifest(outdir: Path, figures: list, inputs: list, caption45: str, caption46: str,
                   payload45: dict, payload46: dict) -> Path:
    """A hash table, then the captions the week report quotes verbatim."""

    total = payload45["n_cells_total"]
    per_axis = payload45["axes"]["oxidation"]["ladder"][0]["n_cells_total"]
    if 2 * per_axis != total:
        raise SystemExit("F45: %d cells per axis does not halve the %d-cell total"
                         % (per_axis, total))
    lines = ["# figure_manifest_week23_stage24", ""]
    lines += ["| figure | sha256 | size |", "| --- | --- | --- |"]
    for path in figures:
        lines.append("| `%s` | `%s` | %d B |"
                     % (path.name, sha256(path), path.stat().st_size))
    lines.append("")
    lines += ["| input | sha256 |", "| --- | --- |"]
    for path in inputs:
        if path.exists():
            lines.append("| `%s` | `%s` |"
                         % (path.relative_to(REPO_ROOT).as_posix(), sha256(path)))
        else:
            lines.append("| `%s` | MISSING |" % path.relative_to(REPO_ROOT).as_posix())
    lines.append("")
    lines += ["Generate (from the repository root):", "", "```powershell",
              r"& $py scripts\make_stage24_figure.py", "```", "",
              "The PNGs carry no timestamp, so re-running on the same inputs gives",
              "byte-identical files.", "",
              "## F45 -- `%s`" % FIGURE_F45, "",
              "One-line caption (verbatim, for the terminal site): " + caption45, "",
              "## F46 -- `%s`" % FIGURE_F46, "",
              "One-line caption (verbatim, for the terminal site): " + caption46, "",
              "## denominators", ""]
    lines += [
        "- F45 panel (a): **16 material cells per axis** (the Stage 16 threshold",
        "  `|delta_ev| >= 1 meV`, inherited unchanged), out of %d cells per axis" % per_axis,
        "  (%d across both axes: %d molecules x %d epsilons).  The per-cell effect is"
        % (total, len(payload45["names"]), len(payload45["epsilons"])),
        "  re-derived here from",
        "  `outputs/week15/stage16_cells.csv` as the change of the **full** decision",
        "  quantity between the two arms, so the maximum reproduces the frozen",
        "  `allowance_ev` to better than 1e-9 eV; `check_allowance` asserts it, along",
        "  with the identity of the worst cell quoted in `allowance_detail`.",
        "- F45 panels (b)-(d): the ladder, the protocol check and the list variant are read",
        "  verbatim from `outputs/week23/targeted_two_guess.json`; each axis carries",
        "  %d molecule pairs over %d cells."
        % (payload45["axes"]["oxidation"]["n_pairs"], per_axis),
        "- F45 panel (c): the targeted protocol rows are exactly 1.000 on both axes and are",
        "  asserted before anything is drawn; the control is the single-leg protocol.",
        "- F46: GFN2-xTB only, %d jobs in `shell3_xtb_sign_test.json` (4 cluster sizes x"
        % payload46["n_jobs"],
        "  3 charge states, plus the free-EC reference).  Absolute shifts must never be",
        "  placed next to the `docs/18` r2SCAN-3c ladder -- the product carries that",
        "  caveat itself.  Panel (c) compares a ratio with a ratio and nothing else; the",
        "  Stage 9 reference is %s." % payload46["stage9_reference"]["method"],
        "",
    ]
    return _write(outdir / MANIFEST_NAME, "\n".join(lines))


def verify_manifest(path: Path, figures: list) -> list:
    """The manifest must record exactly the digests that are on disk."""

    text = path.read_text(encoding="utf-8")
    problems = []
    for figure in figures:
        rows = [line for line in text.splitlines()
                if line.startswith("| `%s`" % figure.name)]
        if len(rows) != 1:
            problems.append("%s: %d manifest rows" % (figure.name, len(rows)))
            continue
        recorded = rows[0].split("|")[2].strip().strip("`")
        actual = sha256(figure)
        if recorded != actual:
            problems.append("%s: manifest says %s, disk says %s"
                            % (figure.name, recorded, actual))
    return problems


def build(outdir: Path, data_dir: Path) -> list:
    payload45 = load_json(data_dir / "targeted_two_guess.json")
    payload46 = load_json(data_dir / "shell3_xtb_sign_test.json")
    effects = per_cell_effects(CELLS_CSV)
    limits = check_allowance(effects, payload45)
    inputs = inputs_for(data_dir)
    produced = [figure_f45(outdir, payload45, effects, limits),
                figure_f46(outdir, payload46)]
    write_manifest(outdir, produced, inputs, caption_f45(payload45, effects, limits),
                   caption_f46(payload46), payload45, payload46)
    problems = verify_manifest(outdir / MANIFEST_NAME, produced)
    if problems:
        raise SystemExit("stage 24 figures: manifest self-check failed:\n  "
                         + "\n  ".join(problems))
    return produced


def run_check(outdir: Path, data_dir: Path) -> int:
    status = 0
    manifest = outdir / MANIFEST_NAME
    for path in (outdir / FIGURE_F45, outdir / FIGURE_F46, manifest):
        if not path.exists():
            print("check FAILED: missing %s" % path)
            status = 1
    if status:
        return status
    workdir = Path(tempfile.mkdtemp(prefix="stage24_figure_check_"))
    try:
        fresh = build(workdir, data_dir)
        for produced in fresh:
            kept = outdir / produced.name
            if kept.read_bytes() != produced.read_bytes():
                print("check FAILED: %s differs from a fresh render" % produced.name)
                status = 1
            else:
                print("check ok: %s reproduces byte for byte (%d bytes)"
                      % (produced.name, produced.stat().st_size))
        if (workdir / MANIFEST_NAME).read_bytes() != manifest.read_bytes():
            print("check FAILED: %s differs from a fresh render" % MANIFEST_NAME)
            status = 1
        else:
            print("check ok: %s reproduces byte for byte" % MANIFEST_NAME)
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
    return status


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Stage 24 figures (F45, F46).")
    parser.add_argument("--outdir", default=str(DEFAULT_OUTDIR),
                        help="figure output directory (default outputs/figures)")
    parser.add_argument("--data-dir", default=str(DEFAULT_DATA_DIR),
                        help="week 23 product directory (default outputs/week23)")
    parser.add_argument("--check", action="store_true",
                        help="verify the products exist and reproduce byte for byte")
    args = parser.parse_args(argv)
    if args.check:
        return run_check(Path(args.outdir), Path(args.data_dir))
    produced = build(Path(args.outdir), Path(args.data_dir))
    for path in produced:
        print("wrote %s (%d bytes, sha256 %s)"
              % (path.name, path.stat().st_size, sha256(path)[:16]))
    print("wrote %s" % MANIFEST_NAME)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
