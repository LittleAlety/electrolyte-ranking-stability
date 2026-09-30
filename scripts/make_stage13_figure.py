"""Stage 13 figures (F24, F25) -- the dielectric limit and ORCA's energy ledger.

F24 is the ladder story:

    (a) delta(eps) against u = 1 - 1/eps for all seven bare levels, 24 curves
    (b) Born / Onsager / two-parameter R2 side by side, and the fitted k
    (c) the forecast error against the distance actually extrapolated
    (d) the conductor limit: the fitted slope S against the measured eps = 200

F25 is the ledger story:

    (a) the SMD acetonitrile shift of the oxidation axis, split into its
        dielectric and solute-distortion parts, molecule by molecule
    (b) the same for the reduction axis
    (c) the SMD CDS term for all three charge states, per molecule and layer
    (d) how much of the dielectric shift the distortion term cancels, per axis

Labels are ASCII on purpose: the workspace has no guaranteed CJK font.

Usage:
    .venv\\Scripts\\python.exe scripts\\make_stage13_figure.py
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from analyze_stage12_prescreen import born_u  # noqa: E402


WEEK12 = REPO_ROOT / "outputs" / "week12"


FIGDIR = REPO_ROOT / "outputs" / "figures"


ANALYSIS = WEEK12 / "stage13_analysis.json"


SPLIT_CSV = WEEK12 / "stage13_shift_split.csv"


STATE_CSV = WEEK12 / "stage13_state_ledger.csv"


RUNG_CSV = WEEK12 / "stage13_rungs.csv"


OX = "#1f5fa9"


RED = "#c0392b"


GREY = "#6b6b6b"


GREEN = "#1a7d4f"


SMD_LABEL = {"smd_acetonitrile": "SMD acetonitrile (eps = 35.688)",
             "smd_water": "SMD water (eps = 78.355)"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_csv(path: Path):
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _f(value):
    if value in (None, "", "None"):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def panel_ladders(ax, analysis, curves):
    """(a) delta(eps) against u = 1 - 1/eps, one line per molecule and axis."""

    eps = analysis["bare_eps"]
    u = [born_u(e) for e in eps]
    for curve in curves:
        values = curve["delta_by_eps"]
        color = OX if curve["axis"] == "oxidation" else RED
        ax.plot(u, values, "-o", color=color, alpha=0.55, lw=1.1, ms=3.4)
    for e in eps:
        ax.axvline(born_u(e), color=GREY, lw=0.5, alpha=0.35)
        ax.annotate("eps=%g" % e, (born_u(e), ax.get_ylim()[1]), rotation=90,
                    fontsize=7, color=GREY, ha="right", va="top",
                    xytext=(-2, -2), textcoords="offset points")
    ax.plot([], [], "-o", color=OX, label="oxidation (IP)")
    ax.plot([], [], "-o", color=RED, label="reduction (-EA)")
    ax.set_xlabel("u = 1 - 1/eps  [dimensionless]")
    ax.set_ylabel("delta(eps) = p(gas) - p(eps)  [eV]")
    ax.set_title("(a) six dielectrics: every curve is a straight line through 0", fontsize=10)
    ax.legend(fontsize=8, loc="lower right")
    ax.grid(alpha=0.25)


def panel_models(ax, analysis):
    """(b) Born vs Onsager vs two-parameter, plus the fitted k."""

    model = analysis["model_comparison"]
    names = ["Born", "Onsager", "two-parameter"]
    means = [model["born_r2"]["mean"], model["onsager_r2"]["mean"],
             model["two_parameter_r2"]["mean"]]
    lows = [model["born_r2"]["min"], model["onsager_r2"]["min"],
            model["two_parameter_r2"]["min"]]
    highs = [model["born_r2"]["max"], model["onsager_r2"]["max"],
             model["two_parameter_r2"]["max"]]
    colors = [GREEN, GREY, OX]
    x = np.arange(len(names))
    ax.bar(x, means, color=colors, alpha=0.85, width=0.55)
    ax.errorbar(x, means, yerr=[np.array(means) - np.array(lows),
                                np.array(highs) - np.array(means)],
                fmt="none", ecolor="black", capsize=5, lw=1.2)
    for index, value in enumerate(means):
        ax.annotate("%.4f" % value, (x[index], value), ha="center", va="bottom",
                    fontsize=8, xytext=(0, 2), textcoords="offset points")
    ax.set_xticks(x)
    ax.set_xticklabels(names, fontsize=9)
    ax.set_ylim(min(lows) - 0.06, 1.02)
    ax.set_ylabel("R2 over %d curves (bar = mean, whisker = min..max)"
                    % len(analysis["model_comparison"]["per_molecule"]))
    ax.set_title("(b) the data pick Born back out of a two-parameter family", fontsize=10)
    ks = model["two_parameter_k"]
    ax.annotate("fitted k = %.4f +/- %.4f\n(range %.4f .. %.4f)\nBorn is k = 0"
                % (ks["mean"], ks["sd"], ks["min"], ks["max"]),
                (0.5, 0.06), xycoords="axes fraction", ha="center", fontsize=8.5,
                bbox=dict(boxstyle="round", fc="white", ec=GREY, alpha=0.9))
    ax.grid(axis="y", alpha=0.25)


def panel_extrapolation(ax, analysis):
    """(c) the forecast error against the distance extrapolated."""

    targets = analysis["extrapolation_scaling"]["targets"]
    gaps, errs, labels = [], [], []
    for tag in ("cpcm_40", "cpcm_80", "cpcm_200"):
        block = targets[tag]
        gaps.append(block["u_gap"])
        errs.append(block["max_abs_err_ev"])
        labels.append("eps=%g" % block["target_eps"])
    ax.plot(gaps, errs, "o", color=RED, ms=8,
            label="max abs error (%d curves)" % (2 * len(analysis["subset"])))
    slope = analysis["extrapolation_scaling"]["err_per_u_gap_ev"]
    grid = np.linspace(0.0, max(gaps) * 1.1, 50)
    ax.plot(grid, slope * grid, "-", color=GREY, lw=1.2,
            label="through-origin: %.3f eV per unit u" % slope)
    for gap, err, label in zip(gaps, errs, labels):
        ax.annotate(label, (gap, err), fontsize=8, xytext=(4, 5),
                    textcoords="offset points")
    ax.set_xlabel("u(target) - u(20): how far the fit had to reach")
    ax.set_ylabel("max absolute forecast error [eV]")
    ax.set_title("(c) extrapolation error is set by the distance, not the target", fontsize=10)
    ax.legend(fontsize=8)
    ax.grid(alpha=0.25)


def panel_conductor(ax, analysis):
    """(d) the eps = 200 value against the fitted conductor limit."""

    rows = analysis["conductor_limit"]["rows"]
    for axis_label, color in (("oxidation", OX), ("reduction", RED)):
        subset = [r for r in rows if r["axis"] == axis_label]
        ax.plot([r["S_ev"] for r in subset], [r["delta_at_200_ev"] for r in subset],
                "o", color=color, ms=7, alpha=0.85, label=axis_label)
    low = min(min(r["S_ev"], r["delta_at_200_ev"]) for r in rows)
    high = max(max(r["S_ev"], r["delta_at_200_ev"]) for r in rows)
    pad = 0.08 * (high - low)
    grid = np.linspace(low - pad, high + pad, 10)
    ax.plot(grid, grid, "-", color=GREY, lw=1.2, label="y = x (already at the limit)")
    ax.set_xlim(low - pad, high + pad)
    ax.set_ylim(low - pad, high + pad)
    gap = analysis["conductor_limit"]["gap_to_limit_ev"]
    ax.annotate("mean remaining gap to eps -> inf:\n%.4f eV (worst %.4f eV)"
                % (gap["mean"], gap["max"]),
                (0.04, 0.88), xycoords="axes fraction", fontsize=8.5,
                bbox=dict(boxstyle="round", fc="white", ec=GREY, alpha=0.9))
    ax.set_xlabel("fitted Born slope S = delta(eps -> inf)  [eV]")
    ax.set_ylabel("measured delta(eps = 200)  [eV]")
    ax.set_title("(d) eps = 200 is within %.0f meV of the conductor limit"
                 % (1000.0 * gap["max"]), fontsize=10)
    ax.legend(fontsize=8, loc="lower right")
    ax.grid(alpha=0.25)


def figure_f24(analysis, curves, outdir: Path) -> Path:
    figure, axes = plt.subplots(2, 2, figsize=(11.6, 9.0))
    panel_ladders(axes[0][0], analysis, curves)
    panel_models(axes[0][1], analysis)
    panel_extrapolation(axes[1][0], analysis)
    panel_conductor(axes[1][1], analysis)
    figure.suptitle("F24  the dielectric ladder, measured to eps = 200", fontsize=13)
    figure.tight_layout(rect=(0, 0, 1, 0.97))
    path = outdir / "F24_dielectric_limit.png"
    figure.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(figure)
    return path


def split_rows_by(split_rows, level, axis):
    return [row for row in split_rows if row["level"] == level and row["axis"] == axis]


def panel_split(ax, split_rows, level, axis, title):
    """One axis of one SMD layer, split into dielectric and distortion."""

    subset = split_rows_by(split_rows, level, axis)
    names = [row["name"] for row in subset]
    diel = [float(row["diel_ev"]) for row in subset]
    dist = [float(row["dist_ev"]) for row in subset]
    total = [float(row["d_total_ev"]) for row in subset]
    x = np.arange(len(names))
    ax.bar(x - 0.2, diel, 0.4, color=OX, label="CPCM dielectric term")
    ax.bar(x + 0.2, dist, 0.4, color=RED, label="solute distortion term")
    ax.plot(x, total, "kD", ms=5, label="measured total shift")
    ax.axhline(0.0, color="black", lw=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(names, fontsize=7.5, rotation=45)
    ax.set_ylabel("shift from gas  [eV]")
    ax.set_title(title, fontsize=10)
    ax.legend(fontsize=8, loc="lower left")
    ax.grid(axis="y", alpha=0.25)


def panel_cds(ax, state_rows):
    """The SMD CDS term, for all three charge states -- they coincide exactly."""

    order, seen = [], set()
    for row in state_rows:
        if row["name"] not in seen:
            seen.add(row["name"])
            order.append(row["name"])
    x = np.arange(len(order))
    for level, color in (("smd_acetonitrile", OX), ("smd_water", RED)):
        for state, marker, size in (("neutral", "o", 9.0), ("cation", "^", 4.5), ("anion", "x", 4.5)):
            values = []
            for name in order:
                match = [r for r in state_rows
                         if r["name"] == name and r["level"] == level and r["state"] == state]
                value = _f(match[0]["smd_cds_ev"]) if match else None
                values.append(value)
            ax.plot(x, values, marker, color=color, ms=size, alpha=0.85,
                    label="%s / %s" % (SMD_LABEL[level].split(" ")[1], state))
    ax.axhline(0.0, color="black", lw=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(order, fontsize=7.5, rotation=45)
    ax.set_ylabel("SMD CDS (Gcds)  [eV]")
    ax.set_title("(c) CDS is state-independent: all three markers coincide", fontsize=10)
    ax.annotate("spread across neutral/cation/anion = 0.0 eV\n"
                "-> CDS is a rigid offset, invisible to IP / EA",
                (0.03, 0.06), xycoords="axes fraction", fontsize=8.5,
                bbox=dict(boxstyle="round", fc="white", ec=GREY, alpha=0.9))
    ax.legend(fontsize=7, ncol=2, loc="upper left")
    ax.grid(axis="y", alpha=0.25)


def panel_cancellation(ax, split_rows):
    """How much of the dielectric shift the distortion term takes back."""

    styles = (("smd_acetonitrile", "oxidation", OX, "o"),
              ("smd_acetonitrile", "reduction", OX, "^"),
              ("smd_water", "oxidation", RED, "o"),
              ("smd_water", "reduction", RED, "^"))
    notes = []
    for level, axis, color, marker in styles:
        subset = split_rows_by(split_rows, level, axis)
        dx = [abs(float(row["diel_ev"])) for row in subset]
        dy = [abs(float(row["dist_ev"])) for row in subset]
        ax.plot(dx, dy, marker, color=color, ms=6, alpha=0.85,
                label="%s / %s" % (level.replace("smd_", ""), axis))
        ratios = [d / x for x, d in zip(dx, dy) if x != 0.0]
        ratio = float(np.mean(ratios)) if ratios else 0.0
        grid = np.linspace(0.0, max(dx) * 1.05, 10)
        ax.plot(grid, ratio * grid, "-", color=color, lw=1.0, alpha=0.6)
        notes.append("%s/%s: %.1f%%" % (level.replace("smd_", ""), axis[:3], 100.0 * ratio))
    ax.set_xlabel("|CPCM dielectric term|  [eV]")
    ax.set_ylabel("|solute distortion term|  [eV]")
    ax.set_title("(d) the distortion takes back a fixed fraction", fontsize=10)
    ax.annotate("cancellation fraction, sign-blind mean |D|/|C|\n"
                "(report quotes the signed mean D/C)\n" + "\n".join(notes),
                (0.04, 0.62), xycoords="axes fraction", fontsize=8,
                bbox=dict(boxstyle="round", fc="white", ec=GREY, alpha=0.9))
    ax.legend(fontsize=7.5, loc="lower right")
    ax.grid(alpha=0.25)


def figure_f25(split_rows, state_rows, analysis, outdir: Path) -> Path:
    figure, axes = plt.subplots(2, 2, figsize=(11.2, 8.4))
    panel_split(axes[0][0], split_rows, "smd_acetonitrile", "oxidation",
                "(a) SMD acetonitrile, oxidation axis")
    panel_split(axes[0][1], split_rows, "smd_acetonitrile", "reduction",
                "(b) SMD acetonitrile, reduction axis")
    panel_cds(axes[1][0], state_rows)
    panel_cancellation(axes[1][1], split_rows)
    figure.suptitle("F25  an environment shift is exactly dielectric + distortion", fontsize=13)
    figure.tight_layout(rect=(0, 0, 1, 0.97))
    path = outdir / "F25_environment_ledger.png"
    figure.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(figure)
    return path


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Stage 13 figures (F24, F25).")
    parser.add_argument("--manifest", type=Path,
                        default=FIGDIR / "figure_manifest_week12_stage13.md")
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    if not ANALYSIS.exists():
        print("error: %s missing -- run the Stage 13 analysis first" % ANALYSIS,
              file=sys.stderr)
        return 2
    analysis = json.loads(ANALYSIS.read_text(encoding="utf-8"))
    curves = analysis["model_comparison"]["per_molecule"]
    split_rows = load_csv(SPLIT_CSV)
    state_rows = load_csv(STATE_CSV)

    FIGDIR.mkdir(parents=True, exist_ok=True)
    f24 = figure_f24(analysis, curves, FIGDIR)
    f25 = figure_f25(split_rows, state_rows, analysis, FIGDIR)

    model = analysis["model_comparison"]
    ledger = analysis["smd_ledger"]
    lines = [
        "# figure_manifest_week12_stage13",
        "",
        "| figure | sha256 | size |",
        "| --- | --- | --- |",
        "| `F24_dielectric_limit.png` | `%s` | %d B |" % (sha256(f24), f24.stat().st_size),
        "| `F25_environment_ledger.png` | `%s` | %d B |" % (sha256(f25), f25.stat().st_size),
        "",
        "| input | sha256 |",
        "| --- | --- |",
        "| `outputs/week12/stage13_analysis.json` | `%s` |" % sha256(ANALYSIS),
        "| `outputs/week12/stage13_shift_split.csv` | `%s` |" % sha256(SPLIT_CSV),
        "| `outputs/week12/stage13_state_ledger.csv` | `%s` |" % sha256(STATE_CSV),
        "| `outputs/week12/stage13_rungs.csv` | `%s` |" % sha256(RUNG_CSV),
        "",
        "F24 panel (a): the seven bare levels (gas, eps = 5/10/20/40/80/200) plotted",
        "against u = 1 - 1/eps.  All %d curves pass through the origin, which is what"
        % len(curves),
        "makes the through-origin Born fit the right comparison.",
        "",
        "F24 panel (b): mean R2 = %.4f (Born), %.4f (Onsager), %.4f (two-parameter)."
        % (model["born_r2"]["mean"], model["onsager_r2"]["mean"],
           model["two_parameter_r2"]["mean"]),
        "The two-parameter family's own best fit returns k = %.4f +/- %.4f, i.e. Born."
        % (model["two_parameter_k"]["mean"], model["two_parameter_k"]["sd"]),
        "",
        "F24 panel (c): the error of a forecast made from eps <= 20 grows in proportion",
        "to how far the fit had to reach (max error %.4f / %.4f / %.4f eV at eps = 40 / 80 / 200)."
        % (analysis["extrapolation_scaling"]["targets"]["cpcm_40"]["max_abs_err_ev"],
           analysis["extrapolation_scaling"]["targets"]["cpcm_80"]["max_abs_err_ev"],
           analysis["extrapolation_scaling"]["targets"]["cpcm_200"]["max_abs_err_ev"]),
        "",
        "F24 panel (d): the measured eps = 200 shift sits within %.0f meV of the fitted"
        % (1000.0 * analysis["conductor_limit"]["gap_to_limit_ev"]["max"]),
        "eps -> infinity limit, so nothing beyond eps = 200 can move these numbers.",
        "",
        "F25 panels (a) and (b): one self-consistent SMD calculation per state already",
        "contains the split -- the CPCM dielectric term points down, the solute",
        "distortion term points back up, and the diamond (the measured total) is their sum.",
        "",
        "F25 panel (c): the SMD CDS term is identical for neutral, cation and anion",
        "(%d molecule-layer groups, spread %.1e eV), so it cancels in every vertical IP/EA."
        % (analysis["ladder_checks"]["cds_is_state_independent"]["n_molecule_layer_groups"],
           analysis["ladder_checks"]["cds_is_state_independent"]["max_spread_ev"]),
        "",
        "F25 panel (d): the cancellation fraction is a property of the axis, not of the",
        "molecule: the reduction axis loses much more of its dielectric shift to distortion.",
        "",
        "Palette and dpi follow the other week figures (warm/cool pair for the",
        "oxidation/reduction axes, dpi = 160, bbox_inches = tight).",
        "",
        "`outputs/week12/stage13_summary.md` is the narrative companion of these figures.",
        "",
    ]
    args.manifest.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print("wrote %s" % f24.relative_to(REPO_ROOT).as_posix())
    print("wrote %s" % f25.relative_to(REPO_ROOT).as_posix())
    print("wrote %s" % args.manifest.relative_to(REPO_ROOT).as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())