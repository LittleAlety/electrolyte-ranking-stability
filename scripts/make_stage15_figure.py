"""Stage 15 figures (F28, F29) -- the two-guess protocol and the electron's spread.

F28 is the guess story:

    (a) dE = E_moread - E_default on the ten-point ladder, per molecule and state.
        Zero everywhere means the default guess is fine; the few non-zero points
        are exactly the metastable solutions Stage 14 could only describe.
    (b) the independent observable: the EMC anion dipole across the ladder, under
        both protocols, on the same axes.
    (c) the EMC/reduction shift against the Born abscissa, both protocols, with
        eps = 1000 as a *measured* point instead of a fitted one.
    (d) the conductor limit: the nine-point extrapolation against the measurement.

F29 is the descriptor story:

    (e) the reduction-axis anion penalty against the electron's concentration,
        which is the descriptor that finally works.
    (f) the same penalty against the inverse participation ratio -- a stronger
        rank correlation but a bowed, non-linear one.
    (g) leave-one-out R2 of the best descriptor per target, before and after.
    (h) the layer-by-layer spin polarisation, which finds the one layer where a
        different SCF solution was reached without using any energy at all.

Labels are ASCII on purpose: the workspace has no guaranteed CJK font.

Usage:
    .venv\\Scripts\\python.exe scripts\\make_stage15_figure.py
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

WEEK14 = REPO_ROOT / "outputs" / "week14"
FIGDIR = REPO_ROOT / "outputs" / "figures"

ANALYSIS_JSON = WEEK14 / "stage15_two_guess_analysis.json"
ENERGY_CSV = WEEK14 / "stage15_two_guess_energy.csv"
DIFFUSE_JSON = WEEK14 / "stage15_diffuseness.json"
DIFFUSE_CSV = WEEK14 / "stage15_diffuseness.csv"

OX = "#1f5fa9"
RED = "#c0392b"
GREY = "#6b6b6b"
GREEN = "#1a7d4f"
ORANGE = "#d98218"
PURPLE = "#6a3d9a"

MOL_COLOR = {"EMC": RED, "DMC": OX, "EC": GREEN}
MOL_MARKER = {"EMC": "o", "DMC": "s", "EC": "^"}
STATE_STYLE = {"neutral": ("-", 0.55), "cation": ("--", 0.75), "anion": ("-", 1.0)}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 16), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_csv(path: Path):
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def save(fig, path: Path) -> Path:
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)
    return path


# ------------------------------------------------------------------ F28


def figure_f28(analysis, energy_rows, outdir: Path) -> Path:
    fig, axes = plt.subplots(2, 2, figsize=(12.4, 8.6))
    ladder = analysis["ladder"]
    x = np.arange(len(ladder))

    # (a) the energy difference
    ax = axes[0][0]
    by_state = {}
    for row in energy_rows:
        by_state.setdefault((row["name"], row["state"]), {})[
            float(row["epsilon"])] = float(row["delta_ev"])
    for (name, state), series in sorted(by_state.items()):
        ys = [series.get(eps, np.nan) for eps in ladder]
        ax.plot(x, ys, linestyle=STATE_STYLE[state][0],
                alpha=STATE_STYLE[state][1], marker=MOL_MARKER[name],
                markersize=3.6, linewidth=1.2, color=MOL_COLOR[name],
                label="%s/%s" % (name, state))
    ax.axhline(0.0, color="black", linewidth=0.8)
    worst = analysis["energy"]["max_default_excess_ev"]
    ax.annotate("E_moread - E_default\n< 0 : the default guess\nmissed the lower state",
                xy=(0.03, 0.93), xycoords="axes fraction", fontsize=7.4,
                va="top", color=RED)
    ax.set_xticks(x)
    ax.set_xticklabels(["%g" % eps for eps in ladder], rotation=45, ha="right",
                       fontsize=7.5)
    ax.set_xlabel("dielectric constant  eps")
    ax.set_ylabel("dE  [eV]")
    ax.set_title("(a) restarting from the gas-phase MOs, ten dielectrics\n"
                 "the default guess sat up to %.3f eV too high" % worst, fontsize=10)
    ax.legend(fontsize=6.2, ncol=3, frameon=False, loc="lower left")
    ax.grid(alpha=0.25, linewidth=0.5)
    ax.set_axisbelow(True)

    # (b) the EMC anion dipole, both protocols
    ax = axes[0][1]
    for protocol, color, marker in (("default", RED, "o"), ("moread", GREEN, "D")):
        series = analysis["emc_reduction_curves"][protocol]["anion_dipole_ten"]
        ys = [series.get("%g" % eps) for eps in ladder]
        ax.plot(x, ys, marker=marker, markersize=4.4, linewidth=1.4, color=color,
                label="%s guess" % protocol)
    ax.set_xticks(x)
    ax.set_xticklabels(["%g" % eps for eps in ladder], rotation=45, ha="right",
                       fontsize=7.5)
    ax.set_xlabel("dielectric constant  eps")
    ax.set_ylabel("EMC anion dipole  [D]")
    ax.set_title("(b) the dipole is an independent witness of which\n"
                 "SCF solution was reached", fontsize=10)
    ax.legend(fontsize=8, frameon=False)
    ax.grid(alpha=0.25, linewidth=0.5)
    ax.set_axisbelow(True)

    # (c) the Born curve
    ax = axes[1][0]
    for protocol, color, marker in (("default", RED, "o"), ("moread", GREEN, "D")):
        block = analysis["emc_reduction_curves"][protocol]["ten"]
        xs = [1.0 - 1.0 / eps for eps in ladder]
        ys = [block["delta_by_eps"]["%g" % eps] for eps in ladder]
        ax.plot(xs, ys, marker=marker, markersize=4.4, linewidth=1.3, color=color,
                label="%s  (R2 nine pts %.3f)"
                      % (protocol, analysis["emc_reduction_curves"][protocol]["nine"]
                         ["born_through_origin"]["r2"]))
        slope = analysis["conductor_limit"][protocol]["born_slope_from_nine_points_ev"]
        ax.plot([0, 1], [0, slope], linestyle=":", color=color, linewidth=0.9,
                alpha=0.7)
    measured = analysis["conductor_limit"]["moread"]["delta_at_eps1000_ev"]
    ax.axvline(1.0 - 1.0 / 1000.0, color=GREY, linewidth=0.8, linestyle="-.")
    ax.annotate("eps = 1000\n(measured,\n%.3f eV)" % measured, xy=(0.999, measured),
                xytext=(0.80, measured - 0.30), fontsize=7.0, color=GREY,
                arrowprops=dict(arrowstyle="->", color=GREY, linewidth=0.7))
    ax.set_xlabel("Born abscissa   1 - 1/eps")
    ax.set_ylabel("EA(eps) - EA(gas)  [eV]")
    ax.set_title("(c) the reduction-axis shift on the same axis as the\n"
                 "Born form the fit assumes", fontsize=10)
    ax.legend(fontsize=7.4, frameon=False, loc="upper left")
    ax.grid(alpha=0.25, linewidth=0.5)
    ax.set_axisbelow(True)

    # (d) extrapolation against the measurement
    ax = axes[1][1]
    labels, extrapolated, at200, at1000 = [], [], [], []
    for protocol in ("default", "moread"):
        block = analysis["conductor_limit"][protocol]
        labels.append(protocol)
        extrapolated.append(block["born_slope_from_nine_points_ev"])
        at200.append(block["delta_at_eps200_ev"])
        at1000.append(block["delta_at_eps1000_ev"])
    pos = np.arange(len(labels))
    width = 0.26
    ax.bar(pos - width, extrapolated, width, color=GREY,
           label="nine-point slope (= extrapolated limit)")
    ax.bar(pos, at200, width, color=ORANGE, label="eps = 200")
    ax.bar(pos + width, at1000, width, color=PURPLE, label="eps = 1000 (measured)")
    for index, value in enumerate(at1000):
        ax.annotate("%.4f" % value, xy=(pos[index] + width, value),
                    xytext=(0, 3), textcoords="offset points", ha="center",
                    fontsize=7.2)
    ax.set_xticks(pos)
    ax.set_xticklabels(labels)
    ax.set_ylabel("EMC/reduction shift  [eV]")
    ax.set_title("(d) the conductor limit: fitted vs measured\n"
                 "extrapolation error at eps = 1000 is %+.4f eV"
                 % analysis["conductor_limit"]["moread"]["extrapolation_error_at_1000_ev"],
                 fontsize=10)
    ax.legend(fontsize=7.4, frameon=False)
    ax.grid(axis="y", alpha=0.25, linewidth=0.5)
    ax.set_axisbelow(True)

    fig.suptitle("F28  Stage 15A -- two guesses, one ladder: is the EMC anomaly a "
                 "metastable solution?", fontsize=11.5)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    return save(fig, outdir / "F28_two_guess_protocol.png")


# ------------------------------------------------------------------ F29


def figure_f29(diffuse, layer_rows, outdir: Path) -> Path:
    fig, axes = plt.subplots(2, 2, figsize=(12.4, 8.6))
    per_mol = [row for row in diffuse["per_molecule"] if row["state"] == "anion"]
    ys = [row["d_state_cpcm6_ev"] for row in per_mol]

    # (e) the descriptor that works
    ax = axes[0][0]
    xs = [row["spin_maxfrac"] for row in per_mol]
    names = [row["name"] for row in per_mol]
    ax.scatter(xs, ys, s=40, color=OX, zorder=3)
    for label, xv, yv in zip(names, xs, ys):
        ax.annotate(label, xy=(xv, yv), xytext=(3, 3), textcoords="offset points",
                    fontsize=7.0, color=GREY)
    design = np.column_stack([np.ones(len(xs)), np.asarray(xs)])
    coef, *_ = np.linalg.lstsq(design, np.asarray(ys), rcond=None)
    grid = np.linspace(min(xs), max(xs), 50)
    ax.plot(grid, coef[0] + coef[1] * grid, color=RED, linewidth=1.2)
    block = diffuse["verdicts"]["anion"]
    ax.set_xlabel("max single-atom Mulliken spin population")
    ax.set_ylabel("D_anion  [eV]")
    ax.set_title("(e) the penalty follows how *concentrated* the added\n"
                 "electron is   rho = %+.3f, LOO R2 = %.3f"
                 % (block["extended_best_rho"], block["extended_best_loo_r2"]),
                 fontsize=10)
    ax.grid(alpha=0.25, linewidth=0.5)
    ax.set_axisbelow(True)

    # (f) the participation ratio: strong rank signal, bowed
    ax = axes[0][1]
    xs = [row["spin_participation"] for row in per_mol]
    ax.scatter(xs, ys, s=40, color=PURPLE, zorder=3)
    for label, xv, yv in zip(names, xs, ys):
        ax.annotate(label, xy=(xv, yv), xytext=(3, 3), textcoords="offset points",
                    fontsize=7.0, color=GREY)
    rho = next(row["spearman"]["rho"] for row
               in diffuse["extended_table"]
               if row["group"] == "anion"
               and row["descriptor"] == "spin_participation")
    loo = next(row["ols"]["loo_r2"] for row
               in diffuse["extended_table"]
               if row["group"] == "anion"
               and row["descriptor"] == "spin_participation")
    ax.set_xscale("log")
    ax.set_xlabel("inverse participation ratio  1 / sum s_i^2   (large = concentrated)")
    ax.set_ylabel("D_anion  [eV]")
    ax.set_title("(f) the same physics as a rank statistic\n"
                 "rho = %+.3f but a straight line gives LOO R2 = %.2f" % (rho, loo),
                 fontsize=10)
    ax.grid(alpha=0.25, linewidth=0.5)
    ax.set_axisbelow(True)

    # (g) LOO R2 before and after
    ax = axes[1][0]
    states = ["neutral", "cation", "anion"]
    baseline = [diffuse["verdicts"][state]["baseline_best_loo_r2"] for state in states]
    extended = [diffuse["verdicts"][state]["extended_best_loo_r2"] for state in states]
    pos = np.arange(len(states))
    width = 0.36
    ax.bar(pos - width / 2, baseline, width, color=GREY,
           label="Stage 14 set (14 descriptors)")
    ax.bar(pos + width / 2, extended, width, color=GREEN,
           label="with diffuseness (21 descriptors)")
    for index in range(len(states)):
        ax.annotate("%.3f" % baseline[index], xy=(pos[index] - width / 2, baseline[index]),
                    xytext=(0, 3), textcoords="offset points", ha="center", fontsize=7.2)
        ax.annotate("%.3f" % extended[index], xy=(pos[index] + width / 2, extended[index]),
                    xytext=(0, 3), textcoords="offset points", ha="center", fontsize=7.2,
                    fontweight="bold")
    ax.axhline(0.0, color="black", linewidth=0.8)
    ax.set_xticks(pos)
    ax.set_xticklabels(["D_neutral", "D_cation", "D_anion"])
    ax.set_ylabel("leave-one-out R2 of the best descriptor")
    ax.set_title("(g) the negative result of Stage 14 is repaired on the\n"
                 "one target where it mattered", fontsize=10)
    ax.legend(fontsize=7.8, frameon=False)
    ax.grid(axis="y", alpha=0.25, linewidth=0.5)
    ax.set_axisbelow(True)

    # (h) the layer-by-layer spin polarisation
    ax = axes[1][1]
    layers = list(diffuse["layers"])
    molecules = sorted({row["name"] for row in layer_rows})
    lookup = {(row["name"], row["layer"]): float(row["sum_spin_abs"])
              for row in layer_rows}
    medians = {name: float(np.median([lookup[(name, layer)] for layer in layers]))
               for name in molecules}
    order = sorted(molecules, key=lambda name: -medians[name])
    xpos = np.arange(len(order))
    for offset, layer in enumerate(layers):
        values = [lookup[(name, layer)] for name in order]
        ax.scatter(xpos + (offset - 2.5) * 0.08, values, s=11,
                   color=plt.cm.viridis(offset / max(1, len(layers) - 1)),
                   label="eps = %s" % layer.replace("cpcm_", "") if offset in (0, 5) else None,
                   zorder=3)
    ax.plot(xpos, [medians[name] for name in order], color=RED, linewidth=0.9,
            linestyle="--", zorder=2, label="per-molecule median")
    outliers = diffuse["layer_outliers"]
    for name, layer, value in outliers:
        ax.annotate("%s/%s" % (name, layer), xy=(order.index(name), value),
                    xytext=(-6, 6), textcoords="offset points", fontsize=7.4,
                    color=RED, fontweight="bold")
    ax.axhline(1.0, color=GREEN, linewidth=0.9, linestyle=":")
    ax.annotate("sum |s_i| = 1 (all spin on the molecule)", xy=(0.02, 1.0),
                xycoords=("axes fraction", "data"), fontsize=7.0, color=GREEN,
                va="bottom")
    ax.set_xticks(xpos)
    ax.set_xticklabels(order, rotation=45, ha="right", fontsize=7.6)
    ax.set_ylabel("spin polarisation  sum |s_i|")
    ax.set_title("(h) six bare-CPCM layers per molecule: the one layer\n"
                 "that left the molecule's own median is EMC/cpcm_10",
                 fontsize=10)
    ax.legend(fontsize=6.6, frameon=False, ncol=2)
    ax.grid(axis="y", alpha=0.25, linewidth=0.5)
    ax.set_axisbelow(True)

    fig.suptitle("F29  Stage 15B -- the added electron's spread, and the descriptor "
                 "that was missing", fontsize=11.5)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    return save(fig, outdir / "F29_diffuseness_descriptor.png")


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--manifest", type=Path,
                        default=REPO_ROOT / "outputs" / "figures"
                        / "figure_manifest_week14_stage15.md")
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    for needed in (ANALYSIS_JSON, ENERGY_CSV, DIFFUSE_JSON, DIFFUSE_CSV):
        if not needed.exists():
            print("error: %s missing -- run the Stage 15 analyses first" % needed,
                  file=sys.stderr)
            return 2
    analysis = json.loads(ANALYSIS_JSON.read_text(encoding="utf-8"))
    diffuse = json.loads(DIFFUSE_JSON.read_text(encoding="utf-8"))
    energy_rows = load_csv(ENERGY_CSV)
    layer_rows = load_csv(DIFFUSE_CSV)

    FIGDIR.mkdir(parents=True, exist_ok=True)
    f28 = figure_f28(analysis, energy_rows, FIGDIR)
    f29 = figure_f29(diffuse, layer_rows, FIGDIR)

    energy = analysis["energy"]
    verdict = analysis["verdict"]
    conductor = analysis["conductor_limit"]
    domain = diffuse["descriptor_domain"]
    anion = diffuse["verdicts"]["anion"]

    lines = [
        "# figure_manifest_week14_stage15",
        "",
        "| figure | sha256 | size |",
        "| --- | --- | --- |",
        "| `F28_two_guess_protocol.png` | `%s` | %d B |" % (sha256(f28), f28.stat().st_size),
        "| `F29_diffuseness_descriptor.png` | `%s` | %d B |" % (sha256(f29), f29.stat().st_size),
        "",
        "| input | sha256 |",
        "| --- | --- |",
        "| `outputs/week14/stage15_two_guess_analysis.json` | `%s` |" % sha256(ANALYSIS_JSON),
        "| `outputs/week14/stage15_two_guess_energy.csv` | `%s` |" % sha256(ENERGY_CSV),
        "| `outputs/week14/stage15_diffuseness.json` | `%s` |" % sha256(DIFFUSE_JSON),
        "| `outputs/week14/stage15_diffuseness.csv` | `%s` |" % sha256(DIFFUSE_CSV),
        "",
        "F28 panel (a): %d of the %d (molecule, state, dielectric) points give the same"
        % (energy["n_identical_to_scf_convergence"], energy["n_points"]),
        "energy to SCF convergence.  The magnitude histogram over thresholds is",
        "%s, so the material threshold is set at %.0e eV: above it there are %d points,"
        % (", ".join("%s: %d" % (key, energy["magnitude_histogram"][key])
                     for key in energy["magnitude_histogram"]),
           energy["material_threshold_ev"], energy["n_material_differences"]),
        "and *all* of them are negative (`E_moread - E_default < 0`), i.e. the default",
        "guess settled on a state that is not the lowest one.  The remaining %d points"
        % energy["n_material_restart_above_the_default_state"],
        "where the restart would be worse is zero, and the worst value inside the noise",
        "band is %.1e eV.  Biggest case of the default guess being too high: %.4f eV."
        % (energy["worst_of_the_noise_ev"], energy["max_default_excess_ev"]),
        "Affected: %s, states %s."
        % (", ".join(energy["affected_molecules"]), ", ".join(energy["affected_states"])),
        "",
        "F28 panel (b): the dipole moves with the energy, and it moves *between two",
        "branches*.  EMC default-guess dipoles on the nine-point ladder span %.2f D with"
        % analysis["emc_reduction_curves"]["default"]["anion_dipole_stats_nine"]["span_debye"],
        "roughness %.2f; restarting from the gas-phase MOs collapses that to %.2f D and"
        % (analysis["emc_reduction_curves"]["default"]["anion_dipole_stats_nine"]["roughness"],
           analysis["emc_reduction_curves"]["moread"]["anion_dipole_stats_nine"]["span_debye"]),
        "roughness %.2f."
        % analysis["emc_reduction_curves"]["moread"]["anion_dipole_stats_nine"]["roughness"],
        "",
        "F28 panel (c): the Born abscissa is `1 - 1/eps`, so the fitted slope *is* the",
        "extrapolated eps -> infinity limit.  eps = 1000 has x = 0.999 and is the first",
        "measured point that close to the limit.",
        "",
        "F28 panel (d), numbers: default protocol, nine-point slope %.4f eV, eps = 200"
        % conductor["default"]["born_slope_from_nine_points_ev"],
        "%.4f eV, eps = 1000 %.4f eV (extrapolation error %+.4f eV).  moread protocol,"
        % (conductor["default"]["delta_at_eps200_ev"],
           conductor["default"]["delta_at_eps1000_ev"],
           conductor["default"]["extrapolation_error_at_1000_ev"]),
        "nine-point slope %.4f eV, eps = 200 %.4f eV, eps = 1000 %.4f eV (extrapolation"
        % (conductor["moread"]["born_slope_from_nine_points_ev"],
           conductor["moread"]["delta_at_eps200_ev"],
           conductor["moread"]["delta_at_eps1000_ev"]),
        "error %+.4f eV)." % conductor["moread"]["extrapolation_error_at_1000_ev"],
        "",
        "F28 reproduction of the Stage 14 numbers: six-point Born R2 %.4f, nine-point"
        % analysis["stage14_reproduction"]["recomputed_default_six_point_r2"],
        "Born R2 %.4f, sign changes %d.  Stage 14 published 0.8468 / 0.6788 / 4, so the"
        % (analysis["stage14_reproduction"]["recomputed_default_nine_point_r2"],
           analysis["stage14_reproduction"]["recomputed_default_nine_sign_changes"]),
        "restart experiment is being compared against the same curve it is meant to fix.",
        "",
        "F29 panel (e): the added electron's spread is measured from the `MULLIKEN ATOMIC",
        "CHARGES AND SPIN POPULATIONS` block of the anion, averaged over the six bare-CPCM",
        "layers.  The single-atom concentration predicts the reduction-axis penalty with",
        "rho = %+.3f and leave-one-out R2 = %.3f, against %.3f for the best Stage 14"
        % (anion["extended_best_rho"], anion["extended_best_loo_r2"],
           anion["baseline_best_loo_r2"]),
        "descriptor (`%s`)." % anion["baseline_best_descriptor"],
        "",
        "F29 panel (f): the inverse participation ratio has the stronger *rank* signal",
        "(rho = %.3f) but is strongly non-linear -- a straight line through it has"
        % next(row["spearman"]["rho"] for row in diffuse["extended_table"]
               if row["group"] == "anion"
               and row["descriptor"] == "spin_participation"),
        "leave-one-out R2 = %.2f.  Reporting only the rank statistic would have been"
        % next(row["ols"]["loo_r2"] for row in diffuse["extended_table"]
               if row["group"] == "anion"
               and row["descriptor"] == "spin_participation"),
        "misleading, which is why both are shown.",
        "",
        "F29 panel (g): leave-one-out R2 of the best descriptor per target.  D_neutral is",
        "unchanged at %.3f (its Stage 14 champion is still the best), D_cation stays at"
        % diffuse["verdicts"]["neutral"]["extended_best_loo_r2"],
        "%.3f, and D_anion rises from %.3f to %.3f."
        % (diffuse["verdicts"]["cation"]["extended_best_loo_r2"],
           anion["baseline_best_loo_r2"], anion["extended_best_loo_r2"]),
        "",
        "F29 panel (h): the descriptor's own validity screen.  The spin populations are",
        "normalised (worst `|sum s - 1|` = %.1e over %d rows, worst `|sum q + 1|` = %.1e)."
        % (domain["worst_abs_sum_spin_minus_one"], domain["n_rows"],
           domain["worst_abs_sum_charge_plus_one"]),
        "Mulliken spin is signed, so `max |s_i| > 1` is a polarisation signature, not an",
        "unbound anion.  One layer leaves its molecule's own median by more than 20%%:",
        "%s.  That is the same layer the Part A energy screen flags, found here without"
        % ", ".join("%s/%s (sum |s| = %.3f)" % tuple(item)
                   for item in diffuse["layer_outliers"]),
        "using any energy at all -- which is the cross-check that makes the diagnosis",
        "credible rather than convenient.",
        "",
        "The gas-phase anion was rejected as a source before any of this was computed:",
        "for %s the gas-phase spin is outside the domain spanned by the six layers, so the"
        % ", ".join(diffuse["gas_phase_screen"]["outside_layer_domain"]) or "none",
        "descriptor would have been extrapolating.",
        "",
        "Palette and dpi follow the other week figures (dpi = 160, bbox_inches = tight).",
        "",
        "`outputs/week14/stage15_summary.md` is the narrative companion of these figures.",
        "",
    ]
    args.manifest.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print("wrote %s" % f28.relative_to(REPO_ROOT).as_posix())
    print("wrote %s" % f29.relative_to(REPO_ROOT).as_posix())
    print("wrote %s" % args.manifest.relative_to(REPO_ROOT).as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())