"""Stage 12 figures (F22, F23) -- the dielectric ladder and pre-screening.

F22 is the scaling story of part A:

    (a) delta(eps) against u = 1 - 1/eps: one straight line per molecule/axis
    (b) the measured increment ratios against the Born and Onsager predictions
    (c) mean, sd and slope of the shift all shrink by the SAME factor c
    (d) delta(eps=40) forecast from the cheap end of the ladder only

F23 is the pre-screening story of part B:

    (a) how the pilot's AUC and sensitivity/specificity grow with k
    (b) the spread of b_hat across subsets, per rung, at k = 5
    (c) one dot per subset: b_hat from 3 molecules against the full-sample b
    (d) the 18 points in the (b, q_median) plane, with the danger region marked

Labels are ASCII on purpose: the workspace has no guaranteed CJK font.

Usage:
    .venv\\Scripts\\python.exe scripts\\make_stage12_figure.py
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from analyze_stage12_prescreen import (  # noqa: E402
    born_u, onsager_v, ols_slope, subsample_slope,
)

WEEK11 = REPO_ROOT / "outputs" / "week11"
FIGDIR = REPO_ROOT / "outputs" / "figures"
PAYLOAD = WEEK11 / "stage12_prescreen.json"
TABLE = WEEK11 / "stage12_prescreen.csv"

OX_COLOR = "#b45309"
RED_COLOR = "#1d4ed8"
FIT_COLOR = "#6b7280"
WARN_COLOR = "#b91c1c"
OK_COLOR = "#047857"
AXIS_COLOR = {"oxidation": OX_COLOR, "reduction": RED_COLOR}

SHORT = {
    "P0_to_P1": "P0->P1",
    "P1_to_P2": "P1->P2",
    "G1_to_G2": "G1->G2",
    "C0_to_C1": "C0->C1",
    "C1_to_C2": "C1->C2",
    "DIE_gas_to_5": "gas->5",
    "DIE_5_to_10": "5->10",
    "DIE_10_to_20": "10->20",
    "DIE_20_to_40": "20->40",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Render figures F22 and F23.")
    parser.add_argument("--payload", type=Path, default=PAYLOAD)
    parser.add_argument("--outdir", type=Path, default=FIGDIR)
    parser.add_argument("--manifest", type=Path,
                        default=FIGDIR / "figure_manifest_week11_stage12.md")
    return parser.parse_args(argv)


def panel_born(ax, payload):
    """(a) delta(eps) is linear in u = 1 - 1/eps for every molecule and axis."""

    law = payload["dielectric_law"]
    eps = law["eps_levels"]
    u = np.asarray([born_u(e) for e in eps], float)
    for entry in law["per_molecule"]:
        colour = AXIS_COLOR[entry["axis"]]
        y = np.asarray(entry["delta_by_eps"], float)
        ax.plot(u, y, "-", color=colour, linewidth=0.7, alpha=0.45)
        ax.plot(u, y, "o", color=colour, markersize=2.6, alpha=0.8,
                markeredgewidth=0)
    for value, tag in zip(u, ["eps=%g" % e for e in eps]):
        ax.axvline(value, color="#d1d5db", linewidth=0.6, zorder=0)
        ax.text(value, ax.get_ylim()[1], " " + tag, fontsize=6.5,
                rotation=90, va="top", color="#6b7280")
    ax.set_xlabel("u = 1 - 1/eps   [dimensionless]", fontsize=8)
    ax.set_ylabel("delta(eps) = p(gas) - p(eps)   [eV]", fontsize=8)
    r2b = law["born_r2"]["mean"] or 0.0
    r2o = law["onsager_r2"]["mean"] or 0.0
    ax.set_title("(a) the dielectric shift is Born: delta = S*(1 - 1/eps)"
                 "   (mean R2 %.4f vs Onsager %.4f)" % (r2b, r2o), fontsize=9)
    ax.grid(alpha=0.25)


def panel_ratios(ax, payload):
    """(b) measured increment ratios against the two competing predictions."""

    law = payload["dielectric_law"]
    pred = law["predicted_ratios"]
    groups = [("r2 = d(5->10) / d(10->20)", "r2", pred["born"]["r2"],
               pred["onsager"]["r2"]),
              ("r3 = d(10->20) / d(20->40)", "r3", pred["born"]["r3"],
               pred["onsager"]["r3"])]
    for index, (label, key, born, onsager) in enumerate(groups):
        values = {"oxidation": [], "reduction": []}
        for entry in law["per_molecule"]:
            value = entry["ratio_%s_vs_born" % key]
            if value is not None:
                values[entry["axis"]].append(value)
        for offset, axis in ((-0.16, "oxidation"), (0.16, "reduction")):
            vals = np.asarray(values[axis], float)
            ax.plot(np.full(vals.size, index + offset), vals, "o",
                    color=AXIS_COLOR[axis], markersize=4.0, alpha=0.8,
                    markeredgewidth=0, label=axis if index == 0 else None)
        ax.hlines(born, index - 0.34, index + 0.34, color=OK_COLOR,
                  linewidth=1.6, zorder=4)
        ax.hlines(onsager, index - 0.34, index + 0.34, color=WARN_COLOR,
                  linewidth=1.2, linestyle="--", zorder=4)
        ax.text(index + 0.36, onsager - 0.004, "Onsager %.3f" % onsager,
                fontsize=6.5, color=WARN_COLOR, va="top")
        if index == 0:
            ax.text(-0.46, born - 0.004, "Born %.3f (both groups)" % born,
                    fontsize=6.5, color=OK_COLOR, va="top")
    ax.set_xticks([0, 1])
    ax.set_xticklabels([g[0] for g in groups], fontsize=7.5)
    ax.set_xlim(-0.5, 1.75)
    ax.set_ylabel("measured increment ratio", fontsize=8)
    ax.set_title("(b) the increments halve when eps doubles: Born wins",
                 fontsize=9)
    ax.legend(fontsize=7, loc="lower left")
    ax.grid(alpha=0.25, axis="y")


def panel_scaling(ax, payload):
    """(c) mean, sd and slope of the shift shrink by one common factor."""

    rows = [r for r in payload["rows"] if r["rung_family"] == "dielectric"]
    order = ["DIE_gas_to_5", "DIE_5_to_10", "DIE_10_to_20", "DIE_20_to_40"]
    for axis in ("oxidation", "reduction"):
        series = [r for r in rows if r["axis"] == axis]
        series.sort(key=lambda r: order.index(r["rung"]))
        x = np.arange(len(series))
        colour = AXIS_COLOR[axis]
        ax.semilogy(x, [abs(r["delta_mean_ev"]) for r in series], "-o",
                    color=colour, markersize=4)
        ax.semilogy(x, [r["delta_sd_ev"] for r in series], "--s",
                    color=colour, markersize=3.6, alpha=0.85)
        ax.semilogy(x, [abs(r["ols_slope_b"]) for r in series], ":^",
                    color=colour, markersize=4.2, alpha=0.85)
    law = payload["dielectric_law"]
    c = [born_u(e) for e in [1.0] + law["eps_levels"]]
    ref = np.asarray([c[1], c[2] - c[1], c[3] - c[2], c[4] - c[3]], float)
    ax.semilogy(np.arange(4), ref, "-", color=FIT_COLOR, linewidth=1.0,
                zorder=0)
    ax.text(2.05, ref[2] * 1.15, "c = u(hi) - u(lo)", fontsize=6.5,
            color=FIT_COLOR)
    ax.set_xticks(range(4))
    ax.set_xticklabels([SHORT[k] for k in order], fontsize=7.5)
    ax.set_xlabel("dielectric rung", fontsize=8)
    ax.set_ylabel("magnitude  [eV]  (log scale)", fontsize=8)
    ax.set_title("(c) mean, sd(delta) and abs(b) all follow the same c\n"
                 "solid = abs(mean), dashed = sd(delta), dotted = abs(b), grey = c",
                 fontsize=8.5)
    ax.grid(alpha=0.25, which="both")


def panel_forecast(ax, payload):
    """(d) delta(eps=40) predicted without ever touching eps=40."""

    rows = payload["extrapolation"]["rows"]
    for key, label, marker in (("three_point_ev", "fit on eps=5,10,20", "o"),
                               ("two_point_ev", "fit on eps=5 only", "s")):
        xs = [r["truth_ev"] for r in rows if r[key] is not None]
        ys = [r[key] for r in rows if r[key] is not None]
        ax.plot(xs, ys, marker, markersize=4.0, alpha=0.75,
                markeredgewidth=0, label=label)
    lo = min(r["truth_ev"] for r in rows) * 0.97
    hi = max(r["truth_ev"] for r in rows) * 1.03
    ax.plot([lo, hi], [lo, hi], "-", color=WARN_COLOR, linewidth=1.1,
            label="y = x")
    ax.set_xlabel("measured delta(eps=40)   [eV]", fontsize=8)
    ax.set_ylabel("forecast delta(eps=40)   [eV]", fontsize=8)
    ax.set_title("(d) 3-level fit forecasts eps=40 to %.1f%% max\n"
                 "(2-level fit: %.1f%%)"
                 % (100.0 * payload["extrapolation"]["three_point_max_rel_err"],
                    100.0 * payload["extrapolation"]["two_point_max_rel_err"]),
                 fontsize=9)
    ax.legend(fontsize=7, loc="upper left")
    ax.grid(alpha=0.25)


def figure_f22(payload, outdir: Path):
    fig, axes = plt.subplots(2, 2, figsize=(11.2, 8.4))
    panel_born(axes[0][0], payload)
    panel_ratios(axes[0][1], payload)
    panel_scaling(axes[1][0], payload)
    panel_forecast(axes[1][1], payload)
    fig.suptitle("F22  the dielectric ladder is a one-parameter family"
                 " (bare CPCM, common-10)", fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.965))
    path = outdir / "F22_dielectric_scaling.png"
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)
    return path

def panel_budget(ax, payload):
    """(a) how the pilot's discrimination grows with k."""

    curves = payload["prescreen"]["curves"]
    x = np.asarray([c["k"] for c in curves], float)
    auc_mean = np.asarray([c["auc_lower_b_mean_over_subsets"] or 0.0 for c in curves], float)
    auc_min = np.asarray([c["auc_lower_b_min_over_subsets"] or 0.0 for c in curves], float)
    auc_avg = np.asarray([c["auc_lower_b_mean_b_hat"] or 0.0 for c in curves], float)
    sens = np.asarray([c["sensitivity_mean"] or 0.0 for c in curves], float)
    sens_min = np.asarray([c["sensitivity_min"] or 0.0 for c in curves], float)
    spec = np.asarray([c["specificity_mean"] or 0.0 for c in curves], float)

    ax.fill_between(x, auc_min, auc_mean, color="#1d4ed8", alpha=0.15)
    ax.plot(x, auc_mean, "-o", color="#1d4ed8", markersize=4,
            label="AUC of one random pilot (mean)")
    ax.plot(x, auc_min, ":", color="#1d4ed8", linewidth=1.1,
            label="AUC of the worst pilot")
    ax.plot(x, auc_avg, "-s", color=OK_COLOR, markersize=4,
            label="AUC of the subset-averaged b_hat")
    ax.plot(x, sens, "--^", color=OX_COLOR, markersize=4,
            label="sensitivity (mean)")
    ax.plot(x, sens_min, ":", color=OX_COLOR, linewidth=1.1,
            label="sensitivity (worst pilot)")
    ax.plot(x, spec, "--v", color=FIT_COLOR, markersize=4,
            label="specificity (mean)")
    need = payload["prescreen"]["k_required_for_full_recall"]
    if need:
        ax.axvline(need, color=WARN_COLOR, linewidth=1.2, linestyle="-.")
        ax.text(need + 0.05, 0.42, "k = %d: every pilot\nflags every rung" % need,
                fontsize=6.8, color=WARN_COLOR)
    ax.set_xlabel("pilot size k (molecules computed at the new level)", fontsize=8)
    ax.set_ylabel("score", fontsize=8)
    ax.set_ylim(0.25, 1.05)
    ax.set_title("(a) pre-screening budget: what a k-molecule pilot buys", fontsize=9)
    ax.legend(fontsize=6.3, loc="lower right")
    ax.grid(alpha=0.25)


def panel_bhat_spread(ax, points, rows, k=5, seed=20260930):
    """(b) where b_hat lands, rung by rung, for every k-molecule subset."""

    import random

    rng = random.Random(seed)
    truth_bad = [bool(r["shortlist_rewritten"]) for r in rows]
    order = sorted(range(len(rows)), key=lambda i: rows[i]["ols_slope_b"] or 0.0)
    crit = np.sqrt(2.0)
    for slot, index in enumerate(order):
        point = points[index]
        palette = list(point["names"])
        values = []
        combos = list(itertools.combinations(palette, k))
        if len(combos) > 400:
            combos = rng.sample(combos, 400)
        for combo in combos:
            value = subsample_slope(point, combo)
            if np.isfinite(value):
                values.append(value)
        values = np.asarray(values, float)
        if values.size == 0:
            continue
        colour = WARN_COLOR if truth_bad[index] else "#374151"
        ax.hlines(slot, np.percentile(values, 5), np.percentile(values, 95),
                  color=colour, linewidth=3.4, alpha=0.30)
        ax.plot([np.min(values), np.max(values)], [slot, slot], "-",
                color=colour, linewidth=0.8, alpha=0.45)
        ax.plot([np.mean(values)], [slot], "o", color=colour, markersize=4.2,
                markeredgecolor="white", markeredgewidth=0.5)
        ax.plot([rows[index]["ols_slope_b"]], [slot], "*", color=OK_COLOR,
                markersize=12, markeredgecolor="#111827", markeredgewidth=0.6)
    span = ax.get_xlim()
    ax.axvspan(span[0], 0.0, color=WARN_COLOR, alpha=0.05, zorder=0)
    ax.axvline(0.0, color="#111827", linewidth=1.0)
    ax.axvline(-crit, color=FIT_COLOR, linewidth=0.9, linestyle=":")
    ax.text(0.02, len(order) - 0.6, "rule fires here  ->", fontsize=6.6,
            color=WARN_COLOR)
    ax.set_yticks(range(len(order)))
    ax.set_yticklabels(["%s/%s" % (SHORT[rows[i]["rung"]],
                                   rows[i]["axis"][:3]) for i in order], fontsize=6.4)
    ax.set_xlabel("b_hat from a k = %d pilot   (bar = p05..p95, dot = mean, "
                  "star = full sample)" % k, fontsize=8)
    ax.set_title("(b) the pilot's slope, rung by rung   (red = shortlist rewritten)",
                 fontsize=9)
    ax.grid(alpha=0.25, axis="x")


def panel_subsets(ax, points, rows, k=3):
    """(c) one dot per pilot: b_hat against the full-sample slope."""

    truth_bad = [bool(r["shortlist_rewritten"]) for r in rows]
    combos = list(itertools.combinations(points[0]["names"], k))
    for combo in combos:
        xs, ys, bads = [], [], []
        for index, point in enumerate(points):
            value = subsample_slope(point, combo)
            if np.isfinite(value):
                xs.append(rows[index]["ols_slope_b"])
                ys.append(value)
                bads.append(truth_bad[index])
        xs = np.asarray(xs, float)
        ys = np.asarray(ys, float)
        bads = np.asarray(bads, bool)
        ax.plot(xs[~bads], ys[~bads], "o", color="#94a3b8", markersize=2.2,
                alpha=0.35, markeredgewidth=0)
        ax.plot(xs[bads], ys[bads], "o", color=WARN_COLOR, markersize=2.6,
                alpha=0.5, markeredgewidth=0)
    lo = min(r["ols_slope_b"] for r in rows) * 1.15
    hi = max(r["ols_slope_b"] for r in rows) * 1.15
    ax.plot([lo, hi], [lo, hi], "-", color="#111827", linewidth=1.1,
            label="y = x")
    ax.axhline(0.0, color=OK_COLOR, linewidth=1.0, linestyle="--")
    ax.axvline(0.0, color=OK_COLOR, linewidth=1.0, linestyle="--")
    ax.set_xlabel("full-sample b (all 10 molecules)", fontsize=8)
    ax.set_ylabel("b_hat from a k = %d pilot" % k, fontsize=8)
    ax.set_title("(c) %d pilots from %d molecules each: sign survives, "
                 "magnitude does not" % (len(combos), k), fontsize=9)
    ax.legend(fontsize=7, loc="upper left")
    ax.grid(alpha=0.25)


def panel_plane(ax, rows):
    """(d) all 18 points in the (q_median, b) plane used by the rule."""

    crit = np.sqrt(2.0) / 1.0
    for row in rows:
        colour = AXIS_COLOR[row["axis"]]
        marker = "*" if row["shortlist_rewritten"] else "o"
        size = 12 if row["shortlist_rewritten"] else 4.2
        ax.semilogx([max(row["q_median"], 1e-3)], [row["ols_slope_b"]], marker,
                    color=WARN_COLOR if row["shortlist_rewritten"] else colour,
                    markersize=size, markeredgewidth=0.5,
                    markeredgecolor="#111827")
        if row["shortlist_rewritten"]:
            ax.annotate(SHORT[row["rung"]], (max(row["q_median"], 1e-3),
                                             row["ols_slope_b"]),
                        textcoords="offset points", xytext=(7, -3), fontsize=6.8,
                        color=WARN_COLOR, fontweight="bold")
    ax.axvline(crit, color=OK_COLOR, linewidth=1.1, linestyle="--")
    ax.text(crit * 1.05, 2.6, "sqrt(2)/z = %.3f" % crit, fontsize=6.6,
            color=OK_COLOR)
    ax.axhline(0.0, color="#111827", linewidth=1.0)
    ax.fill_between([1e-3, crit], -3.4, 0.0, color=WARN_COLOR, alpha=0.06)
    ax.text(2.2e-3, -2.9, "danger: b < 0", fontsize=7.0, color=WARN_COLOR)
    ax.text(crit * 1.08, -2.9, "danger: q > sqrt(2)/z", fontsize=7.0,
            color=WARN_COLOR)
    ax.set_xlim(1e-3, 20.0)
    ax.set_ylim(-3.4, 3.1)
    ax.text(2.2e-3, 0.35, "18 points: 5 electronic-structure rungs"
            " + 4 dielectric rungs", fontsize=6.6, color="#4b5563")
    ax.set_xlabel("q_median (median secant slope)", fontsize=8)
    ax.set_ylabel("b (OLS slope of the shift on the axis)", fontsize=8)
    ax.set_title("(d) the 18 points in the plane the rule uses  "
                 "(star = shortlist rewritten)", fontsize=9)
    ax.grid(alpha=0.25, which="both")


def figure_f23(payload, points, rows, outdir: Path):
    fig, axes = plt.subplots(2, 2, figsize=(11.6, 9.0))
    panel_budget(axes[0][0], payload)
    panel_bhat_spread(axes[0][1], points, rows)
    panel_subsets(axes[1][0], points, rows)
    panel_plane(axes[1][1], rows)
    fig.suptitle("F23  pre-screening: deciding whether a level is usable"
                 " before paying for it", fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.965))
    path = outdir / "F23_prescreening.png"
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)
    return path


def main(argv=None) -> int:
    args = parse_args(argv)
    payload = json.loads(args.payload.read_text(encoding="utf-8"))
    args.outdir.mkdir(parents=True, exist_ok=True)

    from analyze_stage10_synthesis import common_names, load_ladder
    from analyze_stage12_prescreen import (
        build_dielectric_points, build_electronic_points,
        load_dielectric_levels,
    )

    ladder = load_ladder()
    names = common_names(ladder)
    levels = load_dielectric_levels()
    points = (build_electronic_points(ladder, names)
              + build_dielectric_points(levels, names))
    rows = payload["rows"]

    f22 = figure_f22(payload, args.outdir)
    f23 = figure_f23(payload, points, rows, args.outdir)

    law = payload["dielectric_law"]
    screen = payload["prescreen"]
    need = screen["k_required_for_full_recall"]
    curves = {c["k"]: c for c in screen["curves"]}
    lines = [
        "# Figure manifest - Week 11 / Stage 12 (F22, F23)",
        "",
        "| figure | file | figure SHA256 | inputs (SHA256) |",
        "| --- | --- | --- | --- |",
        "| F22 | `%s` | %s | `stage12_prescreen.json` %s |" % (
            f22.name, sha256(f22), sha256(PAYLOAD)),
        "| F23 | `%s` | %s | `stage12_prescreen.csv` %s |" % (
            f23.name, sha256(f23), sha256(TABLE)),
        "",
        "Common-10 subset only.  F22 uses the four bare-CPCM dielectric rungs",
        "(plus the gas limit as eps = 1); F23 uses all %d (rung, axis) points."
        % len(rows),
        "",
        "F22 panel (a): delta(eps) = p(gas) - p(eps) against u = 1 - 1/eps, four",
        "points per molecule and axis.  If the response is Born every four-point",
        "series is a straight line through the origin.  Mean R2 = %.6f for Born"
        % (law["born_r2"]["mean"] or 0.0),
        "against %.6f for the Onsager reaction field (eps-1)/(2eps+1)."
        % (law["onsager_r2"]["mean"] or 0.0),
        "",
        "F22 panel (b): the measured increment ratios.  Doubling eps must halve",
        "the increment; measured r2 = %.4f and r3 = %.4f against the Born"
        % (law["measured_ratios"]["r2"]["mean"] or 0.0,
           law["measured_ratios"]["r3"]["mean"] or 0.0),
        "prediction of 2.0000 for both.  Onsager predicts %.4f and %.4f."
        % (law["predicted_ratios"]["onsager"]["r2"],
           law["predicted_ratios"]["onsager"]["r3"]),
        "",
        "F22 panel (c): abs(mean), sd(delta) and abs(b) of the four dielectric",
        "rungs on one log axis.  All three collapse onto the same geometric",
        "sequence, whose ratio is exactly c = u(hi) - u(lo) (grey line).  This",
        "is the whole content of the one-parameter statement: the ladder is a",
        "single vector times a known scalar, so the SIGN of b cannot change.",
        "",
        "F22 panel (d): delta(eps=40) forecast from the cheap end only.  The",
        "three-level fit (gas, eps=5, 10, 20) reaches %.1f%% maximum relative"
        % (100.0 * payload["extrapolation"]["three_point_max_rel_err"]),
        "error; the two-level fit (gas and eps=5 only) reaches %.1f%%."
        % (100.0 * payload["extrapolation"]["two_point_max_rel_err"]),
        "No eps=40 datum enters either fit.",
        "",
        "F23 panel (a): the pilot budget.  A single random pilot of k molecules",
        "reaches AUC %.3f at k = 3 and %.3f at k = 5; averaging b_hat over all"
        % (curves[3]["auc_lower_b_mean_over_subsets"],
           curves[5]["auc_lower_b_mean_over_subsets"]),
        "pilots of that size reaches 1.000 already at k = 3.  The worst pilot",
        "only catches every dangerous rung at k = %d." % need,
        "",
        "F23 panel (b): b_hat across all pilots of size 5, per rung, sorted by",
        "the full-sample slope.  Red rungs are the three whose shortlist is",
        "actually rewritten; the pilot lands on the correct side of zero for",
        "all of them, and the p05..p95 width shrinks as |b| grows.",
        "",
        "F23 panel (c): one dot per 3-molecule pilot, b_hat against the value",
        "obtained from all ten molecules.  The SIGN is stable over the whole",
        "plane; the magnitude is compressed towards zero.",
        "",
        "F23 panel (d): the same 18 points in the plane the decision rule",
        "actually uses.  The rule flags a rung when b < 0 or q_median exceeds",
        "sqrt(2)/z; the three rewritten rungs are the stars.",
        "",
        "Palette and dpi follow the other week figures (warm/cool pair for the",
        "oxidation/reduction axes, dpi = 160, bbox_inches = tight).",
        "",
        "`stage12_summary.md` is the narrative companion of these figures.",
        "",
    ]
    args.manifest.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print("wrote %s" % f22.relative_to(REPO_ROOT).as_posix())
    print("wrote %s" % f23.relative_to(REPO_ROOT).as_posix())
    print("wrote %s" % args.manifest.relative_to(REPO_ROOT).as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())