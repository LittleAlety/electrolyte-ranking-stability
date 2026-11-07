"""Stage 14 figures (F26, F27) -- distortion attribution and the EMC outlier.

F26 is the attribution story:

    (a) the three per-state distortion penalties D_X, molecule by molecule
    (b) the axis terms are differences of those penalties -- verified identity
    (c) the one robust relationship: D_neutral against the molecule's own dipole
    (d) the descriptor screen, scored by leave-one-out R2 so that fragile fits
        cannot masquerade as predictions

F27 is the outlier story:

    (a) the oxidation axis on the nine-point bare-CPCM ladder, EMC vs controls
    (b) the reduction axis, same ladder
    (c) the Stage 13 four-point grid against the nine-point ladder, EMC/reduction
    (d) the Born R2 as a function of how many grid points it was fitted to

Labels are ASCII on purpose: the workspace has no guaranteed CJK font.

Usage:
    .venv\\Scripts\\python.exe scripts\\make_stage14_figure.py
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

WEEK13 = REPO_ROOT / "outputs" / "week13"
WEEK12 = REPO_ROOT / "outputs" / "week12"
FIGDIR = REPO_ROOT / "outputs" / "figures"

ATTRIBUTION_JSON = WEEK13 / "stage14_attribution.json"
STATES_CSV = WEEK13 / "stage14_distortion_states_by_molecule.csv"
SPLIT_CSV = WEEK12 / "stage13_shift_split.csv"
LEDGER_CSV = WEEK12 / "stage13_state_ledger.csv"
OUTLIER_JSON = WEEK13 / "stage14_outlier.json"
OUTLIER_CSV = WEEK13 / "stage14_outlier.csv"

OX = "#1f5fa9"
RED = "#c0392b"
GREY = "#6b6b6b"
GREEN = "#1a7d4f"
ORANGE = "#d98218"
PURPLE = "#6a3d9a"

STATE_COLOR = {"neutral": GREY, "cation": RED, "anion": OX}
MOL_COLOR = {"EMC": RED, "DMC": OX, "EC": GREEN}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 16), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_csv(path: Path):
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


# ---------------------------------------------------------------- F26


def panel_a(ax, state_rows):
    """Grouped bars: the three per-state penalties for every molecule."""

    by_name = {}
    for row in state_rows:
        by_name.setdefault(row["name"], {})[row["state"]] = float(row["d_state_cpcm6_ev"])
    order = sorted(by_name, key=lambda name: -by_name[name]["anion"])
    x = np.arange(len(order))
    width = 0.26
    for offset, state in ((-1, "neutral"), (0, "cation"), (1, "anion")):
        values = [by_name[name][state] for name in order]
        ax.bar(x + offset * width, values, width, color=STATE_COLOR[state],
               label="D_%s" % state, edgecolor="white", linewidth=0.4)
    ax.set_xticks(x)
    ax.set_xticklabels(order, fontsize=8, rotation=45, ha="right")
    ax.set_ylabel("distortion penalty  D  [eV]")
    ax.set_title("(a) the solvent re-shapes every state, the anion most of all",
                 fontsize=10)
    ax.legend(fontsize=8, frameon=False)
    ax.grid(axis="y", alpha=0.25, linewidth=0.5)
    ax.set_axisbelow(True)
    return by_name


def panel_b(ax, split_rows, ledger_rows):
    """The axis terms really are differences of the panel (a) penalties."""

    def number(value):
        return float(value) if value not in ("", None) else 0.0

    bare = {}
    for row in ledger_rows:
        key = (row["name"], row["level"], row["state"])
        bare[key] = (number(row["total_energy_ev"]) - number(row["cpcm_dielectric_ev"])
                     - number(row["smd_cds_ev"]))
    stored, rebuilt = [], []
    for row in split_rows:
        level = row["level"]
        if level == "gas":
            continue
        penalty = {}
        for state in ("neutral", "cation", "anion"):
            penalty[state] = bare[(row["name"], level, state)] - bare[(row["name"], "gas", state)]
        if row["axis"] == "oxidation":
            value = penalty["cation"] - penalty["neutral"]
        else:
            value = penalty["neutral"] - penalty["anion"]
        stored.append(float(row["dist_ev"]))
        rebuilt.append(value)
    residual = max(abs(a - b) for a, b in zip(stored, rebuilt))
    ax.plot([-0.8, 0.4], [-0.8, 0.4], color=GREY, linewidth=0.8, linestyle="--",
            label="y = x")
    ax.scatter(stored, rebuilt, s=14, color=PURPLE, alpha=0.75, zorder=3,
               label="%d molecule-layer rows" % len(stored))
    ax.set_xlabel("stored  dist_ev  [eV]")
    ax.set_ylabel("rebuilt from the state ledger  [eV]")
    ax.set_title("(b) the axis term is a difference of two penalties", fontsize=10)
    ax.text(0.03, 0.95, "max |residual| = %.1e eV" % residual,
            transform=ax.transAxes, fontsize=8, va="top")
    ax.legend(fontsize=8, frameon=False, loc="lower right")
    ax.grid(alpha=0.25, linewidth=0.5)
    ax.set_axisbelow(True)


def panel_c(ax, attribution, state_rows):
    """The one relationship that survives leave-one-out."""

    entry = None
    for row in attribution["correlations"]["state_penalty"]["table"]:
        if row["group"] == "neutral" and row["descriptor"] == "mu_neutral_debye":
            entry = row
    xs = [float(row["mu_neutral_debye"]) for row in state_rows if row["state"] == "neutral"]
    ys = [float(row["d_state_cpcm6_ev"]) for row in state_rows if row["state"] == "neutral"]
    names = [row["name"] for row in state_rows if row["state"] == "neutral"]
    fit = np.polyfit(xs, ys, 1)
    grid = np.linspace(min(xs) * 0.9, max(xs) * 1.05, 50)
    ax.plot(grid, np.polyval(fit, grid), color=RED, linewidth=1.2,
            label="OLS  slope %.4f eV/D" % fit[0])
    ax.scatter(xs, ys, s=34, color=GREY, zorder=3)
    for x, y, name in zip(xs, ys, names):
        ax.annotate(name, (x, y), textcoords="offset points", xytext=(4, 3),
                    fontsize=7, color="#333333")
    ax.set_xlabel("gas-phase dipole of the neutral  [D]")
    ax.set_ylabel("D_neutral  [eV]")
    ax.set_title("(c) a polar molecule pays a bigger re-shaping penalty", fontsize=10)
    ax.text(0.03, 0.95,
            "spearman rho = %+.3f  (p = %.4f)\nleave-one-out R2 = %.3f"
            % (entry["spearman"]["rho"], entry["spearman"]["p"],
               entry["ols"]["loo_r2"]),
            transform=ax.transAxes, fontsize=8, va="top")
    ax.legend(fontsize=8, frameon=False, loc="lower right")
    ax.grid(alpha=0.25, linewidth=0.5)
    ax.set_axisbelow(True)


def panel_d(ax, attribution):
    """Descriptor screen: only one target is predictable at all."""

    rows = attribution["correlations"]
    best = {}
    for group in ("neutral", "cation", "anion"):
        table = [row for row in rows["state_penalty"]["table"] if row["group"] == group]
        best["D_%s" % group] = max(table, key=lambda row: row["ols"]["loo_r2"])
    for axis in ("oxidation", "reduction"):
        table = [row for row in rows["axis_distortion"]["table"] if row["group"] == axis]
        best["dist %s" % axis] = max(table, key=lambda row: row["ols"]["loo_r2"])
    labels = list(best)
    values = [best[label]["ols"]["loo_r2"] for label in labels]
    colors = [GREEN if value > 0.4 else (ORANGE if value > 0.05 else GREY)
              for value in values]
    y = np.arange(len(labels))
    ax.barh(y, values, color=colors, edgecolor="white", linewidth=0.5)
    ax.axvline(0.0, color="#333333", linewidth=0.8)
    ax.axvline(0.5, color=GREY, linewidth=0.8, linestyle=":")
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=8)
    ax.invert_yaxis()
    ax.set_xlabel("leave-one-out R2 of the best single descriptor")
    ax.set_title("(d) only the neutral penalty is predictable", fontsize=10)
    for index, (label, value) in enumerate(zip(labels, values)):
        row = best[label]
        ax.text(max(value, 0.0) + 0.015, index,
                "%s (%+.2f)" % (row["descriptor"].replace("_debye", ""), value),
                fontsize=7, va="center")
    ax.set_xlim(-0.65, 1.35)
    ax.grid(axis="x", alpha=0.25, linewidth=0.5)
    ax.set_axisbelow(True)


def figure_f26(attribution, state_rows, split_rows, ledger_rows, outdir):
    figure, axes = plt.subplots(2, 2, figsize=(12.4, 9.0))
    panel_a(axes[0][0], state_rows)
    panel_b(axes[0][1], split_rows, ledger_rows)
    panel_c(axes[1][0], attribution, state_rows)
    panel_d(axes[1][1], attribution)
    figure.suptitle("F26  what sets the size of the solute distortion term", fontsize=13)
    figure.tight_layout(rect=(0, 0, 1, 0.97))
    path = outdir / "F26_distortion_attribution.png"
    figure.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(figure)
    return path


# ---------------------------------------------------------------- F27


def panel_e(ax, curves, axis, ladder):
    for name in ("EMC", "DMC", "EC"):
        curve = curves["%s/%s" % (name, axis)]
        xs = [1.0 - 1.0 / eps for eps in ladder]
        ys = [curve["delta_at_eps"]["%g" % eps] for eps in ladder]
        style = "-" if name != "EMC" else "--"
        ax.plot(xs, ys, style, marker="o", markersize=3.4, linewidth=1.3,
                color=MOL_COLOR[name], label=name)
    ax.set_xlabel("u = 1 - 1/eps")
    ax.set_ylabel("delta(eps)  [eV]")
    ax.set_title("(%s) %s axis, nine bare-CPCM points"
                 % ("e" if axis == "oxidation" else "f", axis), fontsize=10)
    ax.legend(fontsize=8, frameon=False)
    ax.grid(alpha=0.25, linewidth=0.5)
    ax.set_axisbelow(True)


def panel_g(ax, curves, ladder):
    """EMC/reduction on the dense ladder, with the points coloured by SCF branch."""

    curve = curves["EMC/reduction"]
    xs = [1.0 - 1.0 / eps for eps in ladder]
    ys = [curve["delta_at_eps"]["%g" % eps] for eps in ladder]
    branch = curve["anion_dipole_branch_by_eps"]
    dipole = curve["anion_dipole_debye_by_eps"]

    control = curves["DMC/reduction"]
    ax.plot(xs, [control["delta_at_eps"]["%g" % eps] for eps in ladder], ":",
            color=OX, linewidth=1.4, label="DMC/reduction (same-family control)")
    ax.plot(xs, ys, "-", color=GREY, linewidth=1.0, zorder=1)
    for side, colour, marker in (("low", RED, "o"), ("high", GREEN, "s")):
        sx = [x for x, eps in zip(xs, ladder) if branch["%g" % eps] == side]
        sy = [y for y, eps in zip(ys, ladder) if branch["%g" % eps] == side]
        if not sx:
            continue
        values = [dipole["%g" % eps] for eps in ladder if branch["%g" % eps] == side]
        ax.plot(sx, sy, marker, markersize=7.0, color=colour, linestyle="none",
                zorder=3, label="anion dipole ~%.1f D (%s branch)"
                % (sum(values) / len(values), side))
    ax.set_xlabel("u = 1 - 1/eps")
    ax.set_ylabel("delta(eps)  [eV]")
    ax.set_title("(g) EMC / reduction: the points are coloured by which "
                 "SCF solution the anion found", fontsize=10)
    ax.text(0.03, 0.06,
            "EMC anion dipole roughness = %.2f  vs  DMC %.3f, EC %.3f\n"
            "(%d branch hops over the nine dielectrics)"
            % (curve["anion_dipole_roughness"],
               curves["DMC/reduction"]["anion_dipole_roughness"],
               curves["EC/reduction"]["anion_dipole_roughness"],
               curve["anion_dipole_branch_hops"]),
            transform=ax.transAxes, fontsize=7.5)
    ax.legend(fontsize=7.5, frameon=False, loc="upper left")
    ax.grid(alpha=0.25, linewidth=0.5)
    ax.set_axisbelow(True)


def panel_h(ax, curves):
    keys = ["EMC/oxidation", "EMC/reduction", "DMC/oxidation", "DMC/reduction",
            "EC/oxidation", "EC/reduction"]
    colors = [RED, RED, OX, OX, GREEN, GREEN]
    styles = ["-", "--", "-", "--", "-", "--"]
    for key, color, style in zip(keys, colors, styles):
        density = curves[key]["born_r2_by_grid_density"]
        xs = [item["n_points"] for item in density]
        ys = [item["r2"] for item in density]
        ax.plot(xs, ys, style, marker="o", markersize=3.4, linewidth=1.2,
                color=color, label=key)
    ax.axhline(0.95, color=GREY, linewidth=0.8, linestyle=":")
    ax.set_xlabel("number of bare-CPCM points in the Born fit")
    ax.set_ylabel("Born R2 (through origin)")
    ax.set_title("(h) the Born R2 is not an artefact of the grid size", fontsize=10)
    ax.legend(fontsize=7, frameon=False, ncol=2)
    ax.grid(alpha=0.25, linewidth=0.5)
    ax.set_axisbelow(True)


def figure_f27(analysis, outdir):
    ladder = analysis["ladder_eps"]
    curves = analysis["curves"]
    figure, axes = plt.subplots(2, 2, figsize=(12.4, 9.0))
    panel_e(axes[0][0], curves, "oxidation", ladder)
    panel_e(axes[0][1], curves, "reduction", ladder)
    panel_g(axes[1][0], curves, ladder)
    panel_h(axes[1][1], curves)
    figure.suptitle("F27  the EMC reduction outlier on a denser dielectric grid",
                    fontsize=13)
    figure.tight_layout(rect=(0, 0, 1, 0.97))
    path = outdir / "F27_emc_outlier.png"
    figure.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(figure)
    return path


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Stage 14 figures (F26, F27).")
    parser.add_argument("--manifest", type=Path,
                        default=FIGDIR / "figure_manifest_week13_stage14.md")
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    for needed in (ATTRIBUTION_JSON, OUTLIER_JSON, STATES_CSV, OUTLIER_CSV):
        if not needed.exists():
            print("error: %s missing -- run the Stage 14 analyses first" % needed,
                  file=sys.stderr)
            return 2
    attribution = json.loads(ATTRIBUTION_JSON.read_text(encoding="utf-8"))
    outlier = json.loads(OUTLIER_JSON.read_text(encoding="utf-8"))
    state_rows = load_csv(STATES_CSV)
    split_rows = load_csv(SPLIT_CSV)
    ledger_rows = load_csv(LEDGER_CSV)

    FIGDIR.mkdir(parents=True, exist_ok=True)
    f26 = figure_f26(attribution, state_rows, split_rows, ledger_rows, FIGDIR)
    f27 = figure_f27(outlier, FIGDIR)

    correction = attribution["correction"]
    states = attribution["state_penalties"]
    verdict = outlier["verdict"]
    curves = outlier["curves"]
    reproducibility = outlier["reproducibility"]
    best_neutral = max(
        [row for row in attribution["correlations"]["state_penalty"]["table"]
         if row["group"] == "neutral"], key=lambda row: row["ols"]["loo_r2"])

    lines = [
        "# figure_manifest_week13_stage14",
        "",
        "| figure | sha256 | size |",
        "| --- | --- | --- |",
        "| `F26_distortion_attribution.png` | `%s` | %d B |" % (sha256(f26), f26.stat().st_size),
        "| `F27_emc_outlier.png` | `%s` | %d B |" % (sha256(f27), f27.stat().st_size),
        "",
        "| input | sha256 |",
        "| --- | --- |",
        "| `outputs/week13/stage14_attribution.json` | `%s` |" % sha256(ATTRIBUTION_JSON),
        "| `outputs/week13/stage14_distortion_states_by_molecule.csv` | `%s` |" % sha256(STATES_CSV),
        "| `outputs/week13/stage14_outlier.json` | `%s` |" % sha256(OUTLIER_JSON),
        "| `outputs/week13/stage14_outlier.csv` | `%s` |" % sha256(OUTLIER_CSV),
        "",
        "F26 panel (a): D_X(t) = bare(X,t) - bare(X,gas) for the six bare-CPCM layers,",
        "averaged per molecule.  Every one of the %d molecule-state penalties is positive"
        % (states["neutral"]["n"] + states["cation"]["n"] + states["anion"]["n"]),
        "(worst minimum %+.3f eV), which is the variational check: the solvent-adapted"
        % states["variational_check"]["worst_minimum_ev"],
        "density is not the bare-energy minimiser, so relaxing back cannot lower the energy.",
        "The channel asymmetry of Stage 13 is a per-state fact: D_anion = %.4f eV against"
        % states["anion"]["mean_ev"],
        "D_neutral = %.4f eV and D_cation = %.4f eV."
        % (states["neutral"]["mean_ev"], states["cation"]["mean_ev"]),
        "",
        "F26 panel (b): the stored `dist_ev` is rebuilt from the state ledger alone for all",
        "%d molecule-layer rows; the largest residual is %.1e eV."
        % (len(split_rows) - 24, correction["penalty_identity_max_abs_residual_ev"]),
        "The axis-visible distortion is therefore exactly D_hi - D_lo -- a *difference* of",
        "two penalties, which is why it inherits none of the single-state correlations.",
        "",
        "F26 panel (c): the only robust signal in the whole screen.  D_neutral tracks the",
        "molecule's own gas-phase dipole with rho = %+.3f and leave-one-out R2 = %.3f."
        % (best_neutral["spearman"]["rho"], best_neutral["ols"]["loo_r2"]),
        "",
        "F26 panel (d): best single descriptor per target, scored by leave-one-out R2.",
        "Only the neutral penalty clears zero; nothing predicts the anion penalty, which is",
        "the term that produces the 7x channel asymmetry, and nothing predicts either axis",
        "observable.  The negative result is the point: the needed descriptor is the spatial",
        "extent of the added electron, which no stored quantity measures.",
        "",
        "F27 panels (e) and (f): all six curves on the nine-point ladder",
        "eps = %s." % ", ".join("%g" % eps for eps in outlier["ladder_eps"]),
        "",
        "F27 panel (g): EMC/reduction on the nine-point ladder, with every marker coloured",
        "by which SCF solution the EMC anion settled on, as revealed by its *dipole*",
        "(~%.1f D vs ~%.1f D).  The energy and the dipole hop in phase, so the anomaly is"
        % (verdict["emc_anion_dipole_branches_debye"]["low"],
           verdict["emc_anion_dipole_branches_debye"]["high"]),
        "a solution-selection artefact of bare CPCM, not a breakdown of the Born form:",
        "adding points makes the Born R2 *worse* (%.4f at six points, %.4f at nine) and"
        % (verdict["emc_reduction_born_r2_stage13_grid"],
           verdict["emc_reduction_born_r2_full_grid"]),
        "increases the sign changes from %d to %d, the opposite of under-sampling."
        % (verdict["emc_reduction_sign_changes_stage13_grid"],
           verdict["emc_reduction_sign_changes_full_grid"]),
        "",
        "F27 panel (g), numbers: the EMC anion dipole takes %s D across the ladder while"
        % "/".join("%.2f" % verdict["emc_anion_dipole_by_eps"][key]
                  for key in ("5", "10", "20")),
        "DMC and EC stay inside %.2f D and %.2f D of drift.  A screen over all twelve"
        % (curves["DMC/reduction"]["anion_dipole_span_debye"],
           curves["EC/reduction"]["anion_dipole_span_debye"]),
        "audited molecules x three charge states (36 dipole ladders, no new electronic",
        "structure) finds exactly one suspect: EMC/anion, roughness %.2f against a smooth"
        % verdict["emc_anion_roughness"],
        "population whose median is %.3f."
        % verdict["solution_screen"]["median_roughness_of_smooth_population"],
        "",
        "F27 panel (h): Born R2 against the number of grid points used, for all six curves.",
        "Five of the six curves are flat in the number of points; only EMC/reduction falls",
        "",
        "Reproducibility: the four shared points (eps = 5/10/20/40) were re-measured and",
        "compared with the frozen Stage 13 numbers; %d of %d energies agree to all printed"
        % (reproducibility["n_identical_strings"], reproducibility["n_points_compared"]),
        "digits, worst deviation %.1e Eh (%.1e eV).  Verdict: %s."
        % (reproducibility["max_abs_delta_eh"], reproducibility["max_abs_delta_ev"],
           reproducibility["verdict"]),
        "",
        "Palette and dpi follow the other week figures (dpi = 160, bbox_inches = tight).",
        "",
        "`outputs/week13/stage14_summary.md` is the narrative companion of these figures.",
        "",
    ]
    args.manifest.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print("wrote %s" % f26.relative_to(REPO_ROOT).as_posix())
    print("wrote %s" % f27.relative_to(REPO_ROOT).as_posix())
    print("wrote %s" % args.manifest.relative_to(REPO_ROOT).as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())