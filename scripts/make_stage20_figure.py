"""Stage 20 figures (F38, F39) -- the sixth rung and the cross-method verdict.

F38 (the sixth rung: P2 single point -> P2 relaxed)

    (a) the per-cell relaxation shift ``Delta = -energy_drop_default_ev`` (eV)
        against the dielectric constant of the cell (log x), one line per molecule,
        coloured by electronic state.  The point of the panel is that this shift is
        flat in epsilon, unlike the environment shift of the same molecules.
    (b) the same ruler: for the four comparable populations of Part 1, the relative
        dispersion ``std/|mean|`` of the five frozen rungs against the sixth rung.
        The G1->G2 oxidation rungs have ``|mean| ~ 0`` and are hatched and labelled
        "rate not meaningful".
    (c) the ``(|mean|, std)`` plane with every rung x population row of the ladder
        file; the new rung is drawn as a filled large marker.
    (d) the seven molecules: mean Delta with the across-epsilon range as an error
        bar, separating the near-rigid reduction branch from the spread oxidation
        branch.

F39 (the cross-method verdict: 74 frozen GFN2-xTB jobs on the Stage-19 endpoints)

    (a) the two arms' separation (RMSD, A) at the start against their separation
        after the frozen xTB relaxation, log-log, with y = x and the 0.02 A
        "same minimum" band.
    (b) on the very same (Stage-19 relaxed) geometry: the xTB single-point Delta
        against the ORCA r2SCAN-3c relaxed Delta, with the y = x line and the
        +/- 1 meV material band; the four disagreements are ringed.
    (c) the four absolute separation readings side by side on a log axis (ORCA
        single point / ORCA relaxed / xTB single point / xTB relaxed).
    (d) one-arm drift against the start separation, y = x, log-log.

Every number is read from the JSON / CSV products under ``--data-dir`` (plus the
Stage 19 cells CSV under ``--stage19-dir``, which feeds the ORCA single-point
separation of F39(c)); the only literals in this module are protocol constants and
colours.  In-figure text is ASCII on purpose: the workspace has no guaranteed CJK
font, so Chinese would render as boxes.  The manifest captions, which the terminal
site quotes verbatim, are Chinese.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import tempfile
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = REPO_ROOT / "outputs" / "week19"
DEFAULT_STAGE19_DIR = REPO_ROOT / "outputs" / "week18"
DEFAULT_OUTDIR = REPO_ROOT / "outputs" / "figures"

MANIFEST_NAME = "figure_manifest_week19_stage20.md"
FIGURE_F38 = "F38_stage20_relax_rung.png"
FIGURE_F39 = "F39_stage20_xtb_arms.png"

RUNG_JSON = "stage20_relax_rung.json"
RUNG_CELLS_CSV = "stage20_relax_rung_cells.csv"
RUNG_EPS_CSV = "stage20_relax_rung_epsilon.csv"
RUNG_LADDER_CSV = "stage20_relax_rung_ladder.csv"
XTB_JSON = "stage20_xtb_arms_analysis.json"
XTB_CELLS_CSV = "stage20_xtb_arms_cells_analysis.csv"
STAGE19_CELLS_CSV = "stage19_relax_cells_analysis.csv"

# -- protocol constants (the only literals allowed in this module) --------------
NEW_RUNG = "P2sp_to_P2relax"
FROZEN_RUNGS = ("P0_to_P1", "P1_to_P2", "G1_to_G2", "C0_to_C1", "C1_to_C2")
RUNG_ORDER = FROZEN_RUNGS + (NEW_RUNG,)

#: the four "same batch" populations of the Part 1 ladder file (the two
#: per-molecule-mean aggregates are kept out of the grouped-bar panel)
COMPARABLE_POPULATIONS = (
    "ox_dmc_ec_tmp_eps5",
    "ox_carbonates_eps5",
    "red_dec_emc_pc_tegdme_eps20",
    "red_dec_emc_pc_eps5",
)
ALL_POPULATIONS = COMPARABLE_POPULATIONS + ("ox_all_eps_mean", "red_all_eps_mean")

#: ``(rung, axis)`` pairs whose mean shift is ~ 0, so ``std/|mean|`` diverges and
#: is *not* a dispersion.  Part 1 summary section 6 says so in words; this is the
#: flag that makes the figures say it too.
DEGENERATE_RUNG_AXIS = {("G1_to_G2", "oxidation")}

RUNG_LABEL = {
    "P0_to_P1": "P0->P1 method",
    "P1_to_P2": "P1->P2 environment",
    "G1_to_G2": "G1->G2 geometry",
    "C0_to_C1": "C0->C1 1:1 salt",
    "C1_to_C2": "C1->C2 1:2 salt",
    NEW_RUNG: "P2sp->P2relax NEW",
}
POP_LABEL = {
    "ox_dmc_ec_tmp_eps5": "ox\nDMC;EC;TMP\neps 5",
    "ox_carbonates_eps5": "ox\nDMC;EC\neps 5",
    "red_dec_emc_pc_tegdme_eps20": "red\nDEC;EMC;PC;\nTEGDME eps 20",
    "red_dec_emc_pc_eps5": "red\nDEC;EMC;PC\neps 5",
    "ox_all_eps_mean": "ox per-molecule\nmean over eps",
    "red_all_eps_mean": "red per-molecule\nmean over eps",
}
#: short tags used to label the NEW-rung markers of panel (c)
POP_TAG = {
    "ox_dmc_ec_tmp_eps5": "ox DMC;EC;TMP eps5",
    "ox_carbonates_eps5": "ox DMC;EC eps5",
    "ox_all_eps_mean": "ox per-molecule mean",
    "red_dec_emc_pc_tegdme_eps20": "red DEC;EMC;PC;TEGDME eps20",
    "red_dec_emc_pc_eps5": "red DEC;EMC;PC eps5",
    "red_all_eps_mean": "red per-molecule mean",
}
POP_TAG_OFFSET = {
    "ox_dmc_ec_tmp_eps5": (10, 12, "left"),
    "ox_all_eps_mean": (-10, 26, "right"),
    "ox_carbonates_eps5": (10, -17, "left"),
    "red_dec_emc_pc_tegdme_eps20": (-12, -8, "right"),
    "red_all_eps_mean": (-12, 26, "right"),
    "red_dec_emc_pc_eps5": (-12, -18, "right"),
}
#: label fan-out for the four sign disagreements of F39(b), keyed by epsilon
ZOOM_TAG_OFFSET = {
    5: (10, 7, "left"),
    14: (-8, -11, "right"),
    20: (8, -11, "left"),
    80: (-8, 7, "right"),
}
ZOOM_TAG_NAME = {"DEC": "DEC", "DMC": "DMC", "EC": "EC", "EMC": "EMC",
                 "PC": "PC", "TEGDME": "TEGDME", "TMP": "TMP"}
RUNG_COLOR = {
    "P0_to_P1": "#4c72b0",
    "P1_to_P2": "#dd8452",
    "G1_to_G2": "#55a868",
    "C0_to_C1": "#8172b3",
    "C1_to_C2": "#8c8c3a",
    NEW_RUNG: "#c44e52",
}

ANION = "#1f5fa9"
CATION = "#c0392b"
DARK = "#222222"
GREY = "#9a9a9a"
STATE_COLOR = {"anion": ANION, "cation": CATION}
OUTCOME_COLOR = {
    "distinct_lower": "#c0392b",
    "distinct_higher": "#d98218",
    "same_lower": "#1f5fa9",
    "same_higher": "#1a7d4f",
    "incomplete": "#9a9a9a",
}
OUTCOME_LABEL = {
    "distinct_lower": "xTB: distinct, moread lower",
    "distinct_higher": "xTB: distinct, preference flipped",
    "same_lower": "xTB: same state, moread lower",
    "same_higher": "xTB: same state, moread higher",
    "incomplete": "xTB: not finished",
}
OUTCOMES = ("distinct_lower", "distinct_higher", "same_lower", "same_higher")

#: readings of the two-arm separation drawn in F39(c), in display order
READING_COLOR = {
    "orca_sp": "#1f5fa9",
    "orca_relax": "#6baed6",
    "xtb_sp": "#c0392b",
    "xtb_relax": "#e5989b",
}
READING_LABEL = {
    "orca_sp": "ORCA\nsingle point",
    "orca_relax": "ORCA\nrelaxed",
    "xtb_sp": "xTB\nsingle point",
    "xtb_relax": "xTB\nrelaxed",
}
READING_ORDER = ("orca_sp", "orca_relax", "xtb_sp", "xtb_relax")

#: floor for the log axes of F39(c): every reading has at least one near-degenerate
#: cell, and ``log(0)`` is not a plot.  Clipped points are drawn as open triangles.
LOG_FLOOR = 1.0e-7


def sha256(path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 16), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_csv(path):
    with Path(path).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def as_float(value):
    if value in (None, "", "None"):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def as_bool(value):
    return str(value).strip().lower() == "true"


def display(path) -> str:
    path = Path(path)
    try:
        return str(path.resolve().relative_to(REPO_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def save(fig, path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=170, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("wrote %s (%d bytes)" % (display(path), path.stat().st_size))
    return path


def span(values, pad=0.12, fallback=(-0.05, 0.05)):
    clean = [float(v) for v in values if v is not None]
    if not clean:
        return fallback
    lo, hi = min(clean), max(clean)
    width = hi - lo
    if width <= 0:
        width = max(abs(hi), 1e-3) * 0.2
    return lo - pad * width, hi + pad * width


def p50(values):
    clean = [float(v) for v in values if v is not None]
    return float(np.median(clean)) if clean else float("nan")


def fmt(value, digits=4):
    return "n/a" if value is None or value != value else ("%.*f" % (digits, value))

def legend_swatch(ax, color, label, marker="s"):
    """An empty artist that only exists to carry a legend entry."""

    ax.plot([], [], marker, color=color, markersize=8, label=label)


# ---------------------------------------------------------------------------
# F38 -- the sixth rung
# ---------------------------------------------------------------------------

def panel_a(ax, cells, epsilon_rows, ladder):
    by_mol = {}
    for cell in cells:
        by_mol.setdefault(cell["name"], []).append(cell)
    order = sorted(by_mol, key=lambda n: (by_mol[n][0]["state"] != "anion", n))
    ys_all = [c["delta_ev"] for c in cells]
    lo, hi = span(ys_all, pad=0.10)
    ax.set_xscale("log")
    ax.set_xlim(3.0, 3200.0)
    ax.set_ylim(lo - 0.30 * (hi - lo), hi)
    ylo, yhi = ax.get_ylim()
    height = yhi - ylo
    placed = []
    for name in order:
        rows = sorted(by_mol[name], key=lambda c: c["epsilon"])
        color = STATE_COLOR[rows[0]["state"]]
        xs = [c["epsilon"] for c in rows]
        ys = [c["delta_ev"] for c in rows]
        ax.plot(xs, ys, "-", color=color, lw=1.1, alpha=0.5, zorder=2)
        ax.plot(xs, ys, "o", color=color, ms=5.2, mec="white", mew=0.6, zorder=3)
        label_x, label_y = xs[-1], ys[-1]
        while any(abs(np.log10(label_x) - np.log10(px)) < 0.40
                  and abs(label_y - py) < 0.055 * height for px, py in placed):
            label_y -= 0.055 * height
        placed.append((label_x, label_y))
        ax.text(label_x * 1.35, label_y, name, color=color, fontsize=8.5,
                va="center", clip_on=False)
    legend_swatch(ax, ANION, "anion (reduction axis)", marker="o-")
    legend_swatch(ax, CATION, "cation (oxidation axis)", marker="o-")
    ax.axhline(0.0, color=DARK, lw=0.8, ls=":")
    ranges = [row["delta_range_ev"] for row in epsilon_rows]
    widest = max(epsilon_rows, key=lambda r: r["delta_range_ev"])
    env_abs = [abs(row["shift_mean_ev"]) for row in ladder if row["rung"] == "P1_to_P2"]
    ax.annotate("the relaxation shift is flat in epsilon:\n"
                "per-molecule range over its own eps: median %.4f eV, max %.3f eV (%s)\n"
                "for scale, the environment rung P1->P2 has |mean| = %.2f-%.2f eV\n"
                "on the same populations (part 1 summary, sections 3-4)"
                % (p50(ranges), widest["delta_range_ev"], widest["name"],
                   min(env_abs), max(env_abs)),
                xy=(0.02, 0.03), xycoords="axes fraction", fontsize=8.2,
                va="bottom", ha="left", color=DARK,
                bbox=dict(boxstyle="round,pad=0.35", fc="#f4f4f4", ec="#bbbbbb", lw=0.7))
    ax.set_yticks(np.arange(-2.5, 0.01, 0.5))
    ax.set_xlabel("dielectric constant of the cell  epsilon  (log)")
    ax.set_ylabel("relaxation step  Delta = -energy drop  (eV)")
    ax.set_title("(a) per cell: Delta against epsilon   (n = %d cells, %d molecules)"
                 % (len(cells), len(by_mol)), fontsize=10)
    ax.grid(alpha=0.22, ls=":")
    ax.legend(fontsize=8, loc="upper right", framealpha=0.9)


def panel_b(ax, ladder):
    lookup = {(row["population"], row["rung"]): row for row in ladder}
    pops = list(COMPARABLE_POPULATIONS)
    rungs = [r for r in RUNG_ORDER if any((p, r) in lookup for p in pops)]
    width = 0.82 / len(rungs)
    base = np.arange(len(pops))
    n_hidden = 0
    for i, rung in enumerate(rungs):
        for j, pop in enumerate(pops):
            row = lookup.get((pop, rung))
            if row is None:
                continue
            value = float(row["relative_dispersion"])
            degen = (rung, row["axis"]) in DEGENERATE_RUNG_AXIS
            if degen:
                n_hidden += 1
            x = base[j] + (i - (len(rungs) - 1) / 2.0) * width
            ax.bar(x, value, width=width * 0.92, color=RUNG_COLOR[rung],
                   edgecolor=DARK if rung == NEW_RUNG else "white",
                   linewidth=1.3 if rung == NEW_RUNG else 0.6,
                   hatch="///" if degen else None, zorder=3)
            ax.annotate("%.3g" % value, (x, value * 1.18), ha="center", va="bottom",
                        fontsize=6.2, rotation=90, color=DARK, zorder=4)
    for rung in rungs:
        legend_swatch(ax, RUNG_COLOR[rung], RUNG_LABEL[rung], marker="s")
    ax.set_yscale("log")
    ax.set_ylim(1.5e-3, 14.0)
    ax.set_xticks(base)
    ax.set_xticklabels([POP_LABEL[p] for p in pops], fontsize=6.9)
    ax.set_xlim(-0.6, len(pops) - 0.4)
    ax.set_ylabel("relative dispersion  std / |mean|   (log)")
    ax.set_title("(b) the same ruler: five frozen rungs vs the sixth rung",
                 fontsize=10, pad=30)
    ax.grid(alpha=0.22, ls=":", axis="y")
    ax.legend(fontsize=7.0, loc="lower center", bbox_to_anchor=(0.5, 1.005),
              ncol=3, framealpha=0.9)
    ax.annotate("hatched bars: G1->G2 on the oxidation axis has |mean| ~ 0.01 eV,\n"
                "so std/|mean| is not a dispersion at all (%d bars here)" % n_hidden,
                xy=(0.97, 0.96), xycoords="axes fraction", ha="right", va="top",
                fontsize=7.4, color="#7a4b12",
                bbox=dict(boxstyle="round,pad=0.3", fc="#fff7e6", ec="#e0b070", lw=0.7))


def panel_c(ax, ladder):
    grid = np.logspace(-2.2, 1.05, 64)
    for k in (0.1, 0.5, 1.0):
        ax.plot(grid, k * grid, ls=":", color=GREY, lw=0.9, zorder=1)
        ax.annotate("std = %.1f |mean|" % k, (grid[-1], k * grid[-1]),
                    xytext=(-4, 4), textcoords="offset points", fontsize=7,
                    color="#666666", ha="right")
    for row in ladder:
        new = row["rung"] == NEW_RUNG
        ax.plot(abs(float(row["shift_mean_ev"])), float(row["shift_std_ev"]),
                "o", ms=9.5 if new else 5.4,
                color=RUNG_COLOR[row["rung"]],
                mec=DARK if new else "white", mew=1.1 if new else 0.6,
                zorder=5 if new else 3, alpha=0.95)
    for row in ladder:
        if row["rung"] != NEW_RUNG:
            continue
        dx, dy, ha = POP_TAG_OFFSET.get(row["population"], (8, 8, "left"))
        ax.annotate(POP_TAG.get(row["population"], row["population"]),
                    (abs(float(row["shift_mean_ev"])), float(row["shift_std_ev"])),
                    xytext=(dx, dy), textcoords="offset points", fontsize=7.0,
                    color=RUNG_COLOR[NEW_RUNG], zorder=6, ha=ha,
                    bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none",
                              alpha=0.75))
    for rung in RUNG_ORDER:
        if any(row["rung"] == rung for row in ladder):
            legend_swatch(ax, RUNG_COLOR[rung], RUNG_LABEL[rung], marker="o")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("|shift mean|  (eV, log)")
    ax.set_ylabel("shift std  (eV, log)")
    ax.set_title("(c) (|mean|, std) plane: every rung x population row (n = %d)"
                 % len(ladder), fontsize=10, pad=30)
    ax.grid(alpha=0.22, ls=":", which="both")
    ax.legend(fontsize=7.0, loc="lower center", bbox_to_anchor=(0.5, 1.005),
              ncol=3, framealpha=0.95)
    ax.annotate("far left cluster = the degenerate\nG1->G2 oxidation rungs",
                xy=(0.02, 0.96), xycoords="axes fraction", fontsize=7.2,
                color="#7a4b12", va="top",
                bbox=dict(boxstyle="round,pad=0.3", fc="#fff7e6", ec="#e0b070", lw=0.7))


def panel_d(ax, epsilon_rows, by_state):
    rows = sorted(epsilon_rows,
                  key=lambda r: (r["state"] != "anion", abs(r["delta_mean_ev"])))
    ys = list(range(len(rows)))
    for y, row in zip(ys, rows):
        color = STATE_COLOR[row["state"]]
        mid = float(row["delta_mean_ev"])
        lo = float(row["delta_min_ev"])
        hi = float(row["delta_max_ev"])
        ax.errorbar([mid], [y], xerr=[[mid - lo], [hi - mid]], fmt="o",
                    color=color, ecolor=color, ms=6.5, capsize=3.5, lw=1.5,
                    mec="white", mew=0.6, zorder=3)
    ax.axvline(0.0, color=DARK, lw=0.8, ls=":")
    ax.set_yticks(ys)
    ax.set_yticklabels(["%s %s, %d eps" % (row["name"], row["state"], row["n_eps"])
                        for row in rows], fontsize=8.2)
    ax.invert_yaxis()
    ax.set_xlim(-2.75, 0.30)
    ax.set_xlabel("relaxation step  Delta = -energy drop  (eV)")
    ax.set_title("(d) per molecule: mean Delta, bar = across-epsilon range",
                 fontsize=10)
    ax.grid(alpha=0.22, ls=":", axis="x")
    legend_swatch(ax, ANION, "anion", marker="o")
    legend_swatch(ax, CATION, "cation", marker="o")
    ax.legend(fontsize=8, loc="upper right", framealpha=0.9)
    anion = by_state.get("anion", {})
    cation = by_state.get("cation", {})
    ax.annotate("reduction branch: near-rigid translation\n"
                "(mean %.3f eV, std %.3f eV, rel. disp. %.2f)\n"
                "oxidation branch: spread\n"
                "(mean %.3f eV, std %.3f eV, rel. disp. %.2f)"
                % (anion.get("shift_mean_ev", float("nan")),
                   anion.get("shift_std_ev", float("nan")),
                   anion.get("relative_dispersion", float("nan")),
                   cation.get("shift_mean_ev", float("nan")),
                   cation.get("shift_std_ev", float("nan")),
                   cation.get("relative_dispersion", float("nan"))),
                xy=(0.02, 0.04), xycoords="axes fraction", ha="left", va="bottom",
                fontsize=7.6, color=DARK,
                bbox=dict(boxstyle="round,pad=0.35", fc="#f4f4f4", ec="#bbbbbb", lw=0.7))


def figure_rung(outdir, part1):
    fig = plt.figure(figsize=(13.6, 9.8))
    grid = fig.add_gridspec(2, 2, hspace=0.36, wspace=0.24)
    panel_a(fig.add_subplot(grid[0, 0]), part1["cells"], part1["epsilon_rows"],
            part1["ladder"])
    panel_b(fig.add_subplot(grid[0, 1]), part1["ladder"])
    panel_c(fig.add_subplot(grid[1, 0]), part1["ladder"])
    panel_d(fig.add_subplot(grid[1, 1]), part1["epsilon_rows"],
            part1["aggregates"]["by_state"])
    overall = part1["aggregates"]["overall"]
    fig.suptitle("Stage 20 part 1 -- the sixth rung: P2 single point -> P2 relaxed "
                 "(mean %.3f eV, std %.3f eV, rel. disp. %.2f over %d cells)"
                 % (overall["shift_mean_ev"], overall["shift_std_ev"],
                    overall["relative_dispersion"], overall["n_cells"]),
                 fontsize=12)
    return save(fig, Path(outdir) / FIGURE_F38)

# ---------------------------------------------------------------------------
# F39 -- the cross-method verdict
# ---------------------------------------------------------------------------

def panel_e(ax, cells, tolerance):
    for outcome in OUTCOMES:
        xs = [c["xtb_rmsd_start_arms"] for c in cells if c["outcome"] == outcome]
        ys = [c["xtb_relax_rmsd_arms"] for c in cells if c["outcome"] == outcome]
        if not xs:
            continue
        ax.plot(xs, ys, "o", ms=6.2, color=OUTCOME_COLOR[outcome], mec="white",
                mew=0.6, zorder=3,
                label="%s (%d)" % (OUTCOME_LABEL[outcome], len(xs)))
    lo, hi = 4e-8, 8.0
    ax.fill_between([lo, hi], lo, tolerance, color=GREY, alpha=0.16, zorder=0)
    ax.plot([lo, hi], [lo, hi], ls=":", color=DARK, lw=1.0, zorder=1)
    ax.axhline(tolerance, color=GREY, lw=0.9, ls="--", zorder=1)
    ax.axvline(tolerance, color=GREY, lw=0.9, ls="--", zorder=1)
    ax.annotate("start RMSD p50 %.4f -> relaxed RMSD p50 %.4f A\n"
                "xTB relaxation merges the two arms in %d of %d cells\n"
                "shaded corner: both RMSD below the %.2f A tolerance\n"
                "(denominator: the %d moread_lower cells)"
                % (p50([c["xtb_rmsd_start_arms"] for c in cells]),
                   p50([c["xtb_relax_rmsd_arms"] for c in cells]),
                   sum(1 for c in cells if c["xtb_same_minimum"]), len(cells),
                   tolerance, len(cells)),
                xy=(0.03, 0.96), xycoords="axes fraction", fontsize=7.8, va="top",
                color=DARK, bbox=dict(boxstyle="round,pad=0.35", fc="#f4f4f4",
                                      ec="#bbbbbb", lw=0.7))
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(lo, hi)
    ax.set_ylim(lo, hi)
    ax.set_xlabel("start separation of the two arms  RMSD (A, log)")
    ax.set_ylabel("separation after frozen GFN2-xTB relaxation  RMSD (A, log)")
    ax.set_title("(a) does the pair survive a cheap relaxation?", fontsize=10)
    ax.grid(alpha=0.22, ls=":", which="both")
    ax.legend(fontsize=7.2, loc="lower right", framealpha=0.92)


def panel_f(ax, cells, material_ev):
    disagree = [c for c in cells if not c["xtb_sp_matches_stage19_relax"]]
    for state in ("anion", "cation"):
        rows = [c for c in cells if c["state"] == state]
        ax.plot([c["stage19_relax_delta_ev"] for c in rows],
                [c["xtb_sp_delta_ev"] for c in rows], "o", ms=6.4,
                color=STATE_COLOR[state], mec="white", mew=0.6, zorder=3,
                label="%s (%d)" % (state, len(rows)))
    ax.plot([c["stage19_relax_delta_ev"] for c in disagree],
            [c["xtb_sp_delta_ev"] for c in disagree], "o", ms=6.4,
            mfc="none", mec=DARK, mew=1.5, zorder=4,
            label="sign disagrees (%d)" % len(disagree))
    lo, hi = span([c["stage19_relax_delta_ev"] for c in cells]
                  + [c["xtb_sp_delta_ev"] for c in cells], pad=0.18)
    grid = np.linspace(lo, hi, 64)
    ax.fill_between(grid, grid - material_ev, grid + material_ev, color=GREY,
                    alpha=0.30, zorder=0, label="+/- 1 meV (material)")
    ax.plot(grid, grid, ls=":", color=DARK, lw=1.0, zorder=1)
    n_agree = sum(1 for c in cells if c["xtb_sp_matches_stage19_relax"])
    inside = [c for c in disagree if abs(c["stage19_relax_delta_ev"]) <= material_ev]
    ax.annotate("same geometry, cheaper method: the preferred arm agrees in\n"
                "%d of %d cells (%.0f%%).  The +/- 1 meV band is thinner than a\n"
                "pixel at this scale, so the zoom below shows it: %d of the %d\n"
                "disagreements sit inside that band"
                % (n_agree, len(cells), 100.0 * n_agree / max(len(cells), 1),
                   len(inside), len(disagree)),
                xy=(0.03, 0.96), xycoords="axes fraction", fontsize=7.6, va="top",
                color=DARK, bbox=dict(boxstyle="round,pad=0.35", fc="#f4f4f4",
                                      ec="#bbbbbb", lw=0.7))
    ax.set_xlim(lo, hi)
    ax.set_ylim(lo, hi)
    ax.set_xlabel("ORCA r2SCAN-3c relaxed Delta  (eV)")
    ax.set_ylabel("xTB single-point Delta, same geometry  (eV)")
    ax.set_title("(b) xTB single point vs ORCA, on the Stage-19 endpoints",
                 fontsize=10)
    ax.grid(alpha=0.22, ls=":")
    ax.legend(fontsize=7.4, loc="lower right", framealpha=0.92)
    zoom = ax.inset_axes([0.10, 0.10, 0.42, 0.42])
    lim = 0.014
    zgrid = np.linspace(-lim, lim, 32)
    zoom.fill_between(zgrid, zgrid - material_ev, zgrid + material_ev, color=GREY,
                      alpha=0.45, zorder=0)
    zoom.plot(zgrid, zgrid, ls=":", color=DARK, lw=1.0, zorder=1)
    for state in ("anion", "cation"):
        rows = [c for c in cells if c["state"] == state
                and abs(c["stage19_relax_delta_ev"]) <= lim
                and abs(c["xtb_sp_delta_ev"]) <= lim]
        zoom.plot([c["stage19_relax_delta_ev"] for c in rows],
                  [c["xtb_sp_delta_ev"] for c in rows], "o", ms=5.0,
                  color=STATE_COLOR[state], mec="white", mew=0.5, zorder=3)
    for cell in disagree:
        zoom.plot([cell["stage19_relax_delta_ev"]], [cell["xtb_sp_delta_ev"]],
                  "o", ms=5.0, mfc="none", mec=DARK, mew=1.3, zorder=4)
    for cell in disagree:
        dx, dy, ha = ZOOM_TAG_OFFSET.get(round(float(cell["epsilon"])), (10, 8, "left"))
        zoom.annotate("%s %g" % (ZOOM_TAG_NAME.get(cell["name"], cell["name"]),
                                 cell["epsilon"]),
                      (cell["stage19_relax_delta_ev"], cell["xtb_sp_delta_ev"]),
                      xytext=(dx, dy), textcoords="offset points", fontsize=6.4,
                      color=DARK, zorder=6, ha=ha)
    zoom.set_xlim(-lim, lim)
    zoom.set_ylim(-lim, lim)
    zoom.axhline(0.0, color=GREY, lw=0.6)
    zoom.axvline(0.0, color=GREY, lw=0.6)
    zoom.tick_params(labelsize=6.4)
    zoom.set_title("zoom: |Delta| <= %.0f meV" % (1000 * lim), fontsize=7.2)
    zoom.grid(alpha=0.2, ls=":")


def panel_g(ax, readings, material_ev):
    rng = np.random.default_rng(20)
    n_clipped = 0
    for i, key in enumerate(READING_ORDER):
        values = [abs(float(v)) for v in readings[key]]
        jitter = rng.uniform(-0.22, 0.22, len(values))
        keep = [max(v, LOG_FLOOR) for v in values]
        low = [v < LOG_FLOOR for v in values]
        n_clipped += sum(1 for flag in low if flag)
        xs = [i + j for j, flag in zip(jitter, low) if not flag]
        ys = [v for v, flag in zip(keep, low) if not flag]
        if xs:
            ax.plot(xs, ys, "o", ms=4.6, color=READING_COLOR[key], alpha=0.62,
                    mec="none", zorder=2)
        xs = [i + j for j, flag in zip(jitter, low) if flag]
        ys = [v for v, flag in zip(keep, low) if flag]
        if xs:
            ax.plot(xs, ys, "v", ms=5.4, mfc="none", mec=READING_COLOR[key],
                    mew=1.2, alpha=0.9, zorder=3)
        median = max(p50(values), LOG_FLOOR)
        ax.plot([i - 0.34, i + 0.34], [median, median], color=READING_COLOR[key],
                lw=2.8, zorder=5, solid_capstyle="butt")
        ax.annotate("%.3e" % median, (i + 0.36, median), xytext=(2, 0),
                    textcoords="offset points", fontsize=7.0, va="center",
                    color=DARK, zorder=6)
    ax.axhline(material_ev, color=GREY, lw=0.9, ls="--")
    ax.annotate("1 meV material cut", (3.45, material_ev), xytext=(0, 4),
                textcoords="offset points", fontsize=7.0, color="#555555", ha="right")
    sp = [abs(float(v)) for v in readings["xtb_sp"]]
    relax = [abs(float(v)) for v in readings["xtb_relax"]]
    ratio = p50(sp) / max(p50(relax), LOG_FLOOR)
    ax.annotate("xTB relaxation compresses the separation by %.1f x\n"
                "(%.4g -> %.4g eV).  Each point is one cell of the %d;\n"
                "open triangles sit on the floor: %d readings below %.0e eV"
                % (ratio, p50(sp), p50(relax), len(sp), n_clipped, LOG_FLOOR),
                xy=(0.02, 0.03), xycoords="axes fraction", fontsize=7.6, va="bottom",
                color=DARK, bbox=dict(boxstyle="round,pad=0.35", fc="#f4f4f4",
                                      ec="#bbbbbb", lw=0.7))
    ax.set_yscale("log")
    ax.set_ylim(LOG_FLOOR * 0.85, 1.2)
    ax.set_xticks(range(len(READING_ORDER)))
    ax.set_xticklabels([READING_LABEL[k] for k in READING_ORDER], fontsize=8.2)
    ax.set_xlim(-0.5, len(READING_ORDER) - 0.25)
    ax.set_ylabel("|two-arm separation|  (eV, log)")
    ax.set_title("(c) the four readings of the two-arm separation", fontsize=10)
    ax.grid(alpha=0.22, ls=":", axis="y")


def panel_h(ax, cells, tolerance):
    xs = [c["xtb_rmsd_start_arms"] for c in cells]
    for key, marker, color, label in (
            ("xtb_drift_default", "o", "#4c72b0", "default arm"),
            ("xtb_drift_moread", "^", "#dd8452", "moread arm")):
        ax.plot(xs, [c[key] for c in cells], marker, ms=5.8, color=color, mec="white",
                mew=0.5, alpha=0.9, zorder=3,
                label="%s drift (p50 %.3f A)" % (label, p50([c[key] for c in cells])))
    lo, hi = 4e-8, 8.0
    ax.plot([lo, hi], [lo, hi], ls=":", color=DARK, lw=1.0, zorder=1)
    ax.annotate("y = x", (2e-2, 2e-2), xytext=(6, -10), textcoords="offset points",
                fontsize=7.4, color=DARK, ha="left")
    ax.axhline(tolerance, color=GREY, lw=0.9, ls="--", zorder=1)
    n_big = sum(1 for c in cells
                if min(c["xtb_drift_default"], c["xtb_drift_moread"]) > tolerance)
    ax.annotate("start RMSD p50 %.4f A vs one-arm drift p50 %.3f / %.3f A:\n"
                "the drift is of the same order as the start separation.\n"
                "Both arms drift by more than the %.2f A tolerance in %d of %d\n"
                "cells, so a geometric `distinct` is largely inherited from\n"
                "the starting pair, not created by the cheap relaxation"
                % (p50(xs), p50([c["xtb_drift_default"] for c in cells]),
                   p50([c["xtb_drift_moread"] for c in cells]), tolerance,
                   n_big, len(cells)),
                xy=(0.03, 0.96), xycoords="axes fraction", fontsize=7.4, va="top",
                color=DARK, bbox=dict(boxstyle="round,pad=0.35", fc="#f4f4f4",
                                      ec="#bbbbbb", lw=0.7))
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(lo, hi)
    ax.set_ylim(lo, hi)
    ax.set_xlabel("start separation of the two arms  RMSD (A, log)")
    ax.set_ylabel("one-arm drift start -> xTB relaxed  RMSD (A, log)")
    ax.set_title("(d) the drift is as large as the start difference itself",
                 fontsize=10)
    ax.grid(alpha=0.22, ls=":", which="both")
    ax.legend(fontsize=7.4, loc="lower right", framealpha=0.92)


def figure_xtb(outdir, part2):
    cells = part2["cells"]
    fig = plt.figure(figsize=(13.6, 9.8))
    grid = fig.add_gridspec(2, 2, hspace=0.32, wspace=0.24)
    panel_e(fig.add_subplot(grid[0, 0]), cells, part2["tolerance"])
    panel_f(fig.add_subplot(grid[0, 1]), cells, part2["material_threshold"])
    panel_g(fig.add_subplot(grid[1, 0]), part2["readings"], part2["material_threshold"])
    panel_h(fig.add_subplot(grid[1, 1]), cells, part2["tolerance"])
    overall = part2["aggregates"]["all"]["all"]
    fig.suptitle("Stage 20 part 2 -- frozen GFN2-xTB on the Stage-19 endpoints: "
                 "%d of %d cells still carry two minima after the cheap relaxation"
                 % (overall["n_cells"] - overall["n_xtb_same_minimum"],
                    overall["n_cells"]), fontsize=12)
    return save(fig, Path(outdir) / FIGURE_F39)


# ---------------------------------------------------------------------------
# loading
# ---------------------------------------------------------------------------

def load_part1(data_dir):
    data_dir = Path(data_dir)
    payload = load_json(data_dir / RUNG_JSON)
    cells_csv = load_csv(data_dir / RUNG_CELLS_CSV)
    ladder_csv = load_csv(data_dir / RUNG_LADDER_CSV)
    eps_csv = load_csv(data_dir / RUNG_EPS_CSV)
    if len(cells_csv) != payload["n_cells"]:
        raise SystemExit("rung cells CSV has %d rows, the JSON says %d; re-run "
                         "scripts/analyze_stage20_relax_rung.py"
                         % (len(cells_csv), payload["n_cells"]))
    if len(ladder_csv) != len(payload["ladder_rows"]):
        raise SystemExit("rung ladder CSV has %d rows, the JSON says %d"
                         % (len(ladder_csv), len(payload["ladder_rows"])))
    if len(eps_csv) != len(payload["epsilon_rows"]):
        raise SystemExit("rung epsilon CSV has %d rows, the JSON says %d"
                         % (len(eps_csv), len(payload["epsilon_rows"])))
    cells = [{"name": r["name"], "state": r["state"], "axis": r["axis"],
              "epsilon": as_float(r["epsilon"]), "arm_set": r["arm_set"],
              "outcome": r["outcome"], "delta_ev": as_float(r["delta_ev"]),
              "delta_moread_ev": as_float(r["delta_moread_ev"]),
              "energy_drop_default_ev": as_float(r["energy_drop_default_ev"]),
              "energy_drop_moread_ev": as_float(r["energy_drop_moread_ev"]),
              "rmsd_relaxed_arms": as_float(r["rmsd_relaxed_arms"])}
             for r in cells_csv]
    ladder = [{"population": r["population"], "rung": r["rung"], "axis": r["axis"],
               "n_molecules": int(r["n_molecules"]),
               "shift_mean_ev": as_float(r["shift_mean_ev"]),
               "shift_std_ev": as_float(r["shift_std_ev"]),
               "relative_dispersion": as_float(r["relative_dispersion"])}
              for r in ladder_csv]
    epsilon_rows = [{"name": r["name"], "state": r["state"],
                     "n_eps": int(r["n_eps"]), "eps_min": as_float(r["eps_min"]),
                     "eps_max": as_float(r["eps_max"]),
                     "delta_min_ev": as_float(r["delta_min_ev"]),
                     "delta_max_ev": as_float(r["delta_max_ev"]),
                     "delta_range_ev": as_float(r["delta_range_ev"]),
                     "delta_mean_ev": as_float(r["delta_mean_ev"])}
                    for r in eps_csv]
    return {"payload": payload, "cells": cells, "ladder": ladder,
            "epsilon_rows": epsilon_rows, "aggregates": payload["aggregates"]}


def load_part2(data_dir, stage19_dir):
    data_dir = Path(data_dir)
    stage19_dir = Path(stage19_dir)
    payload = load_json(data_dir / XTB_JSON)
    cells_csv = load_csv(data_dir / XTB_CELLS_CSV)
    s19_csv = load_csv(stage19_dir / STAGE19_CELLS_CSV)
    if len(cells_csv) != payload["n_cells"]:
        raise SystemExit("xtb cells CSV has %d rows, the JSON says %d; re-run "
                         "scripts/analyze_stage20_xtb_arms.py"
                         % (len(cells_csv), payload["n_cells"]))
    s19 = {}
    for row in s19_csv:
        s19[(row["name"], row["state"], round(as_float(row["epsilon"]), 6))] = row
    cells = []
    missing = []
    for row in cells_csv:
        key = (row["name"], row["state"], round(as_float(row["epsilon"]), 6))
        source = s19.get(key)
        if source is None:
            missing.append(key)
            continue
        cells.append({
            "name": row["name"], "state": row["state"], "arm_set": row["arm_set"],
            "epsilon": as_float(row["epsilon"]),
            "outcome": row["outcome"], "stage19_outcome": row["stage19_outcome"],
            "stage19_single_point_delta_ev": as_float(source["single_point_delta_ev"]),
            "stage19_relax_delta_ev": as_float(row["stage19_relax_delta_ev"]),
            "xtb_sp_delta_ev": as_float(row["xtb_sp_delta_ev"]),
            "xtb_relax_delta_ev": as_float(row["xtb_relax_delta_ev"]),
            "xtb_rmsd_start_arms": as_float(row["xtb_rmsd_start_arms"]),
            "xtb_relax_rmsd_arms": as_float(row["xtb_relax_rmsd_arms"]),
            "xtb_drift_default": as_float(row["xtb_drift_default"]),
            "xtb_drift_moread": as_float(row["xtb_drift_moread"]),
            "xtb_same_minimum": as_bool(row["xtb_same_minimum"]),
            "xtb_sp_matches_stage19_relax": as_bool(row["xtb_sp_matches_stage19_relax"]),
            "agrees_with_stage19": as_bool(row["agrees_with_stage19"]),
        })
    if missing:
        raise SystemExit("no Stage 19 row for %d xtb cells: %s"
                         % (len(missing), ", ".join("%s/%s/eps=%g" % k for k in missing)))
    readings = {
        "orca_sp": [c["stage19_single_point_delta_ev"] for c in cells],
        "orca_relax": [c["stage19_relax_delta_ev"] for c in cells],
        "xtb_sp": [c["xtb_sp_delta_ev"] for c in cells],
        "xtb_relax": [c["xtb_relax_delta_ev"] for c in cells],
    }
    return {"payload": payload, "cells": cells, "readings": readings,
            "tolerance": float(payload["geometry_same_tolerance_angstrom"]),
            "material_threshold": float(payload["material_threshold_ev"]),
            "aggregates": payload["aggregates"]}


# ---------------------------------------------------------------------------
# captions (Chinese: the terminal site quotes these verbatim)
# ---------------------------------------------------------------------------

def caption_f38(part1):
    overall = part1["aggregates"]["overall"]
    anion = part1["aggregates"]["by_state"]["anion"]
    cation = part1["aggregates"]["by_state"]["cation"]
    ranges = [row["delta_range_ev"] for row in part1["epsilon_rows"]]
    widest = max(part1["epsilon_rows"], key=lambda row: row["delta_range_ev"])
    return ("(a) %d 个格子的弛豫位移 Δ = −能量降（eV）对 ε（对数轴，按态着色、逐分子连线；"
            "逐分子 ε 极差中位 %.4f eV、最大 %.3f eV（%s），即弛豫修正几乎与介电常数无关）；"
            "(b) 同一把尺子：4 个可比 population 上 5 个冻结台阶与第六级台阶（弛豫）的相对散布 std/|mean|"
            "（对数轴；斜纹柱 = 氧化轴 G1→G2 的 |mean|≈0，相对散布无意义）；"
            "(c) (|mean|, std) 平面：6 个台阶 × population 共 %d 行，实心大点 = 新台阶；"
            "(d) 7 个分子的 Δ 均值，误差棒 = 跨 ε 极差——还原支近乎刚性平移"
            "（均值 %.3f eV、std %.3f eV、相对散布 %.2f），氧化支为散布型"
            "（均值 %.3f eV、std %.3f eV、相对散布 %.2f）"
            % (len(part1["cells"]), p50(ranges), widest["delta_range_ev"],
               widest["name"], len(part1["ladder"]),
               anion["shift_mean_ev"], anion["shift_std_ev"],
               anion["relative_dispersion"], cation["shift_mean_ev"],
               cation["shift_std_ev"], cation["relative_dispersion"]))


def caption_f39(part2):
    cells = part2["cells"]
    overall = part2["aggregates"]["all"]["all"]
    readings = part2["readings"]
    agree = sum(1 for c in cells if c["xtb_sp_matches_stage19_relax"])
    medians = {key: p50([abs(float(v)) for v in readings[key]])
               for key in READING_ORDER}
    ratio = medians["xtb_sp"] / medians["xtb_relax"]
    return ("(a) 两臂起点 RMSD 对 xTB 弛豫后 RMSD（Å，对数轴，按 4 类结局着色，虚线 = 0.02 Å 同极小点阈值；"
            "起点中位 %.4f → 弛豫后中位 %.4f Å，%d/%d 格两臂合并）；"
            "(b) 同一几何上 xTB 单点 Δ 对 ORCA r2SCAN-3c 弛豫 Δ（eV，y=x 与 ±1 meV 带；"
            "偏好方向一致 %d/%d = %.0f%%，4 个分歧已圈出）；"
            "(c) 两臂能量差的四个读数（ORCA 单点 / ORCA 弛豫 / xTB 单点 / xTB 弛豫，对数轴，"
            "中位 %.3e / %.3e / %.3e / %.3e eV）——xTB 弛豫把差异压掉约 %.1f 倍；"
            "(d) 单臂漂移对起点双解 RMSD（Å，y=x，对数轴；两臂漂移中位 %.3f / %.3f Å 与起点差异中位 %.4f Å 同量级，"
            "故几何 distinct 部分继承自起点）。分母：Stage 19 单点两解不同且 moread 更低的 %d 格，"
            "不是 414 格总体的发生率"
            % (p50([c["xtb_rmsd_start_arms"] for c in cells]),
               p50([c["xtb_relax_rmsd_arms"] for c in cells]),
               overall["n_xtb_same_minimum"], overall["n_cells"],
               agree, len(cells), 100.0 * agree / max(len(cells), 1),
               medians["orca_sp"], medians["orca_relax"], medians["xtb_sp"],
               medians["xtb_relax"], ratio,
               p50([c["xtb_drift_default"] for c in cells]),
               p50([c["xtb_drift_moread"] for c in cells]),
               p50([c["xtb_rmsd_start_arms"] for c in cells]), len(cells)))

# ---------------------------------------------------------------------------
# manifest
# ---------------------------------------------------------------------------

def _figure_rows(text):
    rows = {}
    for line in text.splitlines():
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 2:
            continue
        name = cells[0].strip("`")
        digest = cells[1].strip("`")
        if name.endswith(".png") and len(digest) == 64:
            rows[name] = digest
    return rows


def inputs_for(data_dir, stage19_dir):
    data_dir = Path(data_dir)
    stage19_dir = Path(stage19_dir)
    return [data_dir / RUNG_JSON, data_dir / RUNG_CELLS_CSV,
            data_dir / RUNG_LADDER_CSV, data_dir / RUNG_EPS_CSV,
            data_dir / XTB_JSON, data_dir / XTB_CELLS_CSV,
            stage19_dir / STAGE19_CELLS_CSV]


def f38_lines(part1, caption):
    overall = part1["aggregates"]["overall"]
    anion = part1["aggregates"]["by_state"]["anion"]
    cation = part1["aggregates"]["by_state"]["cation"]
    ranges = sorted(row["delta_range_ev"] for row in part1["epsilon_rows"])
    new_rows = [row for row in part1["ladder"] if row["rung"] == NEW_RUNG]
    lines = ["## F38 -- `%s`" % FIGURE_F38, "",
             "One-line caption (verbatim, for the terminal site): %s" % caption, "",
             "### (a) the shift is flat in epsilon", "",
             "- %d cells, %d molecules, %d distinct epsilon values"
             % (overall["n_cells"],
                len({cell["name"] for cell in part1["cells"]}),
                len({cell["epsilon"] for cell in part1["cells"]})),
             "- per-molecule range of Delta across its own eps: median %.4f eV, "
             "max %.4f eV (%s, n_eps=%d)"
             % (p50(ranges), max(ranges),
                max(part1["epsilon_rows"], key=lambda r: r["delta_range_ev"])["name"],
                max(part1["epsilon_rows"],
                    key=lambda r: r["delta_range_ev"])["n_eps"]),
             "- overall: mean %.4f eV, std %.4f eV, range %.4f to %.4f eV"
             % (overall["shift_mean_ev"], overall["shift_std_ev"],
                overall["shift_min_ev"], overall["shift_max_ev"]),
             "- by state: anion mean %.4f eV (std %.4f, rel. disp. %.2f, %d cells); "
             "cation mean %.4f eV (std %.4f, rel. disp. %.2f, %d cells)"
             % (anion["shift_mean_ev"], anion["shift_std_ev"],
                anion["relative_dispersion"], anion["n_cells"],
                cation["shift_mean_ev"], cation["shift_std_ev"],
                cation["relative_dispersion"], cation["n_cells"]),
             "",
             "### (b)(c) the same ruler", "",
             "- ladder rows: %d (rungs %d, populations %d); comparable populations "
             "drawn in (b): %s"
             % (len(part1["ladder"]), len({r["rung"] for r in part1["ladder"]}),
                len({r["population"] for r in part1["ladder"]}),
                ", ".join(COMPARABLE_POPULATIONS))]
    for row in new_rows:
        lines.append("- new rung on %s: mean %.4f eV, std %.4f eV, rel. disp. %.4f "
                     "(n = %d molecules)"
                     % (row["population"], row["shift_mean_ev"], row["shift_std_ev"],
                        row["relative_dispersion"], row["n_molecules"]))
    lines += ["- degenerate rungs flagged as not meaningful: %s"
              % ", ".join("%s (%s)" % pair for pair in sorted(DEGENERATE_RUNG_AXIS)),
              "",
              "### (d) the seven molecules", ""]
    for row in sorted(part1["epsilon_rows"],
                      key=lambda r: (r["state"] != "anion", abs(r["delta_mean_ev"]))):
        lines.append("- %s %s: mean %.4f eV, across eps %.4f to %.4f eV "
                     "(range %.4f, n_eps=%d)"
                     % (row["name"], row["state"], row["delta_mean_ev"],
                        row["delta_min_ev"], row["delta_max_ev"],
                        row["delta_range_ev"], row["n_eps"]))
    lines.append("")
    return lines


def f39_lines(part2, caption):
    cells = part2["cells"]
    overall = part2["aggregates"]["all"]["all"]
    readings = part2["readings"]
    medians = {key: p50([abs(float(v)) for v in readings[key]])
               for key in READING_ORDER}
    agree = sum(1 for c in cells if c["xtb_sp_matches_stage19_relax"])
    disagree = [c for c in cells if not c["xtb_sp_matches_stage19_relax"]]
    lines = ["## F39 -- `%s`" % FIGURE_F39, "",
             "One-line caption (verbatim, for the terminal site): %s" % caption, "",
             "### (a) separation before and after the cheap relaxation", "",
             "- start RMSD p50 %.4f A (min %.3g, max %.4f); relaxed RMSD p50 %.4f A "
             "(min %.3g, max %.4f)"
             % (p50([c["xtb_rmsd_start_arms"] for c in cells]),
                min(c["xtb_rmsd_start_arms"] for c in cells),
                max(c["xtb_rmsd_start_arms"] for c in cells),
                p50([c["xtb_relax_rmsd_arms"] for c in cells]),
                min(c["xtb_relax_rmsd_arms"] for c in cells),
                max(c["xtb_relax_rmsd_arms"] for c in cells)),
             "- merged into one minimum (RMSD <= %.2f A): %d of %d; the xTB outcome "
             "counts are %s"
             % (part2["tolerance"], overall["n_xtb_same_minimum"], len(cells),
                ", ".join("%s %d" % (key, overall["outcomes"].get(key, 0))
                          for key in OUTCOMES)),
             "- xTB verdict against the Stage 19 electronic verdict: agrees in %d of %d"
             % (overall["n_agree_with_stage19"], len(cells)),
             "",
             "### (b) the same geometry, a cheaper method", "",
             "- xTB single point against ORCA r2SCAN-3c relaxed Delta, both on the "
             "Stage-19 endpoints: sign agrees in %d of %d (%.1f%%)"
             % (agree, len(cells), 100.0 * agree / max(len(cells), 1)),
             "- disagreements: %s"
             % ", ".join("%s %s eps=%g (xTB %.5f eV vs ORCA %.5f eV)"
                         % (c["name"], c["state"], c["epsilon"],
                            c["xtb_sp_delta_ev"], c["stage19_relax_delta_ev"])
                         for c in disagree),
             "",
             "### (c) four readings of the separation (median of |Delta|)", ""]
    for key in READING_ORDER:
        lines.append("- %s: %.4e eV" % (READING_LABEL[key].replace("\n", " "),
                                        medians[key]))
    lines += ["- xTB relaxation compresses the xTB separation by %.1f x"
              % (medians["xtb_sp"] / medians["xtb_relax"]),
              "",
              "### (d) one-arm drift versus the start separation", "",
              "- drift p50: default %.4f A, moread %.4f A; start separation p50 %.4f A"
              % (p50([c["xtb_drift_default"] for c in cells]),
                 p50([c["xtb_drift_moread"] for c in cells]),
                 p50([c["xtb_rmsd_start_arms"] for c in cells])),
              "- cells where both arms drift by more than the %.2f A tolerance: %d of %d"
              % (part2["tolerance"],
                 sum(1 for c in cells
                     if min(c["xtb_drift_default"], c["xtb_drift_moread"])
                     > part2["tolerance"]), len(cells)),
              ""]
    return lines


def write_manifest(outdir, figures, inputs, part1, part2, captions):
    lines = ["# figure_manifest_week19_stage20", "",
             "| figure | sha256 | size |",
             "| --- | --- | --- |"]
    for path in figures:
        lines.append("| `%s` | `%s` | %d B |"
                     % (path.name, sha256(path), path.stat().st_size))
    lines += ["", "| input | sha256 |", "| --- | --- |"]
    for path in inputs:
        lines.append("| `%s` | `%s` |" % (display(path), sha256(path)))
    lines += ["", "Generate (from the repository root):", "", "```powershell",
              "& $py scripts\\make_stage20_figure.py",
              "& $py scripts\\make_stage20_figure.py --check",
              "```", "",
              "The PNGs carry no timestamp, so re-running on the same inputs gives "
              "byte-identical files; ``--check`` re-renders into a temporary "
              "directory and compares both PNGs and this file byte for byte.", "",
              "## denominators", "",
              "- F38 works on the %d cells of the Part 1 sixth rung (one electronic "
              "state per molecule, so rank metrics stay omitted); F39 works on the "
              "same %d `moread_lower` cells -- the complete set of cells whose two "
              "single-point SCF solutions differ *and* favour moread." 
              % (part1["aggregates"]["overall"]["n_cells"],
                 part2["aggregates"]["all"]["all"]["n_cells"]),
              "- Read `x/37` as \"given that a single point produced a metastable pair "
              "that was lower, does it survive this step?\" -- a well-defined "
              "conditional proportion on that definition set, never a population "
              "incidence over the 414-cell directory.",
              "- The two `distinct` notions are **not the same criterion**: Stage 19 "
              "uses the frozen electronic identity cut `charge_l1 > 0.039`, Part 2 "
              "only has the geometric `RMSD <= %.2f A` of a cheap optimiser.  The "
              "agreement rate between the two *verdicts* is therefore a comparison "
              "across criteria, unlike panel (b), which compares two methods on one "
              "geometry." % part2["tolerance"],
              "- The xTB jobs are **gas phase** (no CPCM); `epsilon` only labels which "
              "CPCM cell the starting geometry came from, so the epsilon strata here "
              "are not a dielectric effect.",
              "- `%.2f A` and `%.3f eV` are fixed descriptive thresholds, chosen "
              "before the jobs ran; nothing here is tuned after the fact."
              % (part2["tolerance"], part2["material_threshold"]),
              ""]
    lines += f38_lines(part1, captions[FIGURE_F38])
    lines += f39_lines(part2, captions[FIGURE_F39])
    lines += ["## palette and rendering", "",
              "- dpi = 170, ``bbox_inches = tight``, white face colour -- same as the "
              "other week figures.",
              "- In-figure text is ASCII: the workspace has no guaranteed CJK font, so "
              "Chinese would render as boxes.  The captions above are Chinese and are "
              "quoted verbatim by the site builder.",
              ""]
    manifest = Path(outdir) / MANIFEST_NAME
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print("wrote %s (%d bytes)" % (display(manifest), manifest.stat().st_size))
    return manifest


def build(outdir, data_dir, stage19_dir):
    outdir = Path(outdir)
    part1 = load_part1(data_dir)
    part2 = load_part2(data_dir, stage19_dir)
    figures = [figure_rung(outdir, part1), figure_xtb(outdir, part2)]
    captions = {FIGURE_F38: caption_f38(part1), FIGURE_F39: caption_f39(part2)}
    manifest = write_manifest(outdir, figures, inputs_for(data_dir, stage19_dir),
                              part1, part2, captions)
    return [path for path in figures] + [manifest]


def run_check(outdir, data_dir, stage19_dir) -> int:
    outdir = Path(outdir)
    manifest = outdir / MANIFEST_NAME
    if not manifest.exists():
        print("check FAILED: manifest missing: %s" % manifest)
        return 1
    rows = _figure_rows(manifest.read_text(encoding="utf-8"))
    status = 0
    for name in (FIGURE_F38, FIGURE_F39):
        path = outdir / name
        if not path.exists():
            print("check FAILED: missing %s" % path)
            status = 1
            continue
        actual = sha256(path)
        recorded = rows.get(name)
        if recorded is None:
            print("check FAILED: %s not listed in %s" % (name, manifest.name))
            status = 1
        elif recorded != actual:
            print("check FAILED: %s sha256 mismatch\n  manifest: %s\n  on disk : %s"
                  % (name, recorded, actual))
            status = 1
        else:
            print("check ok: %s (%d bytes, sha256 %s)"
                  % (name, path.stat().st_size, actual))
    workdir = Path(tempfile.mkdtemp(prefix="stage20_figure_check_"))
    try:
        fresh = build(workdir, data_dir, stage19_dir)
        for produced in fresh:
            kept = outdir / produced.name
            if not kept.exists():
                print("check FAILED: %s is produced but not on disk" % produced.name)
                status = 1
                continue
            if kept.read_bytes() != produced.read_bytes():
                print("check FAILED: %s differs from a fresh render" % produced.name)
                status = 1
            else:
                print("check ok: %s reproduces byte for byte (%d bytes)"
                      % (produced.name, produced.stat().st_size))
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
    if status == 0:
        print("check ok: manifest and both PNGs reproduce from the data")
    return status


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Stage 20 figures (F38, F39).")
    parser.add_argument("--outdir", default=str(DEFAULT_OUTDIR),
                        help="figure output directory (default outputs/figures)")
    parser.add_argument("--data-dir", default=str(DEFAULT_DATA_DIR),
                        help="Stage 20 product directory (default outputs/week19)")
    parser.add_argument("--stage19-dir", default=str(DEFAULT_STAGE19_DIR),
                        help="Stage 19 product directory (default outputs/week18)")
    parser.add_argument("--check", action="store_true",
                        help="verify the products exist and the manifest reproduces")
    args = parser.parse_args(argv)
    if args.check:
        return run_check(Path(args.outdir), Path(args.data_dir),
                         Path(args.stage19_dir))
    build(Path(args.outdir), Path(args.data_dir), Path(args.stage19_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())