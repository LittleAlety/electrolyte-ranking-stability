"""physics_completion_v1 main figures F59-F64 (plan section 14).

Six figures built from registered batch artefacts only: this script runs no
electronic-structure job.  F60 plots the measured WP1 audit matrix; every other
panel states which rungs are frozen evidence and which are still pending WP2
production, so the set cannot be mistaken for a finished method audit.

    F59  model / conditional-state definition and cohort membership
    F60  independent method audit: measured 128-cell matrix and axis spread
    F61  E -> G -> ensemble decision change on the one frozen rung
    F62  fixed-background pair evidence and state-identity outcome
    F63  mechanism cases (with the frozen relaxation-geometry evidence)
    F64  cumulative cost -> selection recovery curves (frozen AL replay)

Labels are ASCII/English on purpose: the workspace has no guaranteed CJK font.

Usage:
    .venv\\Scripts\\python.exe scripts\\make_physics_completion_figures.py
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from electrolyte_ranking import pc_batch as PB  # noqa: E402

FIGDIR = REPO_ROOT / "outputs" / "figures"
MANIFEST = FIGDIR / "figure_manifest_week45_physics_completion.md"

RUNG = REPO_ROOT / "outputs" / "phase2_p1a" / "p1v_vs_p1a.json"
JOB_MATRIX = REPO_ROOT / "outputs" / "physics_completion" / "method_audit" / "job_matrix.csv"
REUSABLE = REPO_ROOT / "outputs" / "physics_completion" / "method_audit" / "existing_reusable_jobs.csv"
AXIS = REPO_ROOT / "outputs" / "physics_completion" / "method_audit" / "axis_sensitivity.csv"
PAIR_EVIDENCE = REPO_ROOT / "outputs" / "physics_completion" / "pair_evidence" / "pair_evidence.csv"
MECH_CASES = REPO_ROOT / "outputs" / "physics_completion" / "pair_evidence" / "mechanism_cases.csv"
MECH_GEOM = REPO_ROOT / "outputs" / "physics_completion" / "pair_evidence" / "mechanism_geometry.csv"
IDENTITY = REPO_ROOT / "outputs" / "state_identity" / "state_identity_stratification.csv"
BUDGET_CURVES = REPO_ROOT / "outputs" / "week33" / "budget_curves.csv"
LADDER = REPO_ROOT / "outputs" / "physics_completion" / "pair_evidence" / "frozen_rung_ladder.csv"

INK = "#111827"
MUTED = "#6b7280"
BLUE = "#2563eb"
GREEN = "#059669"
AMBER = "#d97706"
RED = "#dc2626"
PURPLE = "#7c3aed"
GRID = dict(color="#e5e7eb", linewidth=0.8)
STATE_COLOUR = {"STABLE": GREEN, "UNRESOLVED": AMBER, "ROBUST_INVERSION": RED}


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path):
    with io.open(path, encoding="utf-8") as handle:
        return json.load(handle)


def load_csv(path: Path):
    with io.open(path, encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def style(ax):
    ax.tick_params(colors=INK, labelsize=8)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color("#d1d5db")
    ax.grid(True, axis="y", **GRID)
    ax.set_axisbelow(True)


def finish(fig, path: Path):
    FIGDIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=160)
    plt.close(fig)
    return path


# ----------------------------------------------------------------- F59
def figure_definition(path: Path):
    fig, (ax_a, ax_b) = plt.subplots(1, 2, figsize=(11.0, 5.2))

    names = [q["name"] for q in PB.QUANTITIES]
    direction = [q.get("objective_direction", "") for q in PB.QUANTITIES]
    roles = [q.get("role", "") for q in PB.QUANTITIES]
    y = np.arange(len(names))[::-1]

    style(ax_a)
    colours = {"maximize": GREEN, "minimize": AMBER}
    ax_a.barh(y, [1.0] * len(names),
              color=[colours.get(d, MUTED) for d in direction], alpha=0.18, height=0.62)
    for yi, name, direct, role in zip(y, names, direction, roles):
        ax_a.text(0.02, yi, name, va="center", ha="left", fontsize=9, color=INK)
        ax_a.text(0.60, yi, direct, va="center", ha="left", fontsize=8, color=MUTED)
        ax_a.text(0.84, yi, role, va="center", ha="left", fontsize=7, color=MUTED)
    ax_a.set_yticks([])
    ax_a.set_xticks([])
    ax_a.set_xlim(0, 1.30)
    ax_a.grid(False)
    ax_a.set_title("(a) Registered quantities, objective direction, role", fontsize=9.5, color=INK)

    cohorts = [("main paired", len(PB.COHORTS["main"]), BLUE),
               ("method audit", len(PB.COHORTS["method_audit"]), PURPLE),
               ("sampling audit", len(PB.COHORTS["sampling_audit"]), GREEN),
               ("core-set excluded", len(PB.MAIN_SET_EXCLUSIONS), RED)]
    style(ax_b)
    xs = np.arange(len(cohorts))
    ax_b.bar(xs, [item[1] for item in cohorts], 0.6,
             color=[item[2] for item in cohorts], edgecolor="white", linewidth=0.8)
    for xi, item in zip(xs, cohorts):
        ax_b.text(xi, item[1] + 0.25, str(item[1]), ha="center", fontsize=10, color=INK)
    ax_b.set_xticks(xs)
    ax_b.set_xticklabels([item[0] for item in cohorts], fontsize=8.5)
    ax_b.set_ylabel("number of molecules")
    ax_b.set_ylim(0, 15)
    ax_b.set_title("(b) Cohort membership (every exclusion has a written reason)", fontsize=9.5, color=INK)

    fig.suptitle("F59  physics_completion_v1 defined on frozen inputs (plan WP0): quantities, directions and cohorts",
                 fontsize=10.5, color=INK)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    return finish(fig, path)


# ----------------------------------------------------------------- F60
def figure_method_audit(path: Path):
    matrix = load_csv(JOB_MATRIX)
    axis = load_csv(AXIS)
    names = []
    for row in matrix:
        if row["name"] not in names:
            names.append(row["name"])
    states = PB.FOUR_STATES
    settings = sorted({row["setting_id"] for row in matrix})
    grid = np.zeros((len(names), len(states) * len(settings)))
    computed = 0
    flagged = 0
    for row in matrix:
        r = names.index(row["name"])
        c = states.index(row["state"]) * len(settings) + settings.index(row["setting_id"])
        if row["valid_for_decision"] == "false":
            grid[r, c] = 2.0
            flagged += 1
        else:
            grid[r, c] = 1.0
        if row["status"] == "computed":
            computed += 1

    fig, (ax_a, ax_b) = plt.subplots(1, 2, figsize=(12.4, 5.0),
                                     gridspec_kw={"width_ratios": [3.1, 1.25]})
    ax_a.imshow(grid, aspect="auto",
                cmap=matplotlib.colors.ListedColormap(["#ffffff", "#dbeafe", "#fde68a"]),
                vmin=0, vmax=3)
    for c in range(len(states) * len(settings)):
        ax_a.axvline(c + 0.5, color="#f3f4f6", linewidth=0.6)
    for index, state in enumerate(states):
        ax_a.text(index * len(settings) + (len(settings) - 1) / 2.0, -1.15, state,
                  ha="center", fontsize=8.5, color=INK)
    ax_a.text(-0.9, -1.15, "state", ha="center", fontsize=8.5, color=MUTED)
    for index, setting in enumerate(settings):
        ax_a.text(index, -1.75, setting, ha="center", fontsize=7.5, color=MUTED)
    ax_a.text(-0.9, -1.75, "setting", ha="center", fontsize=8.5, color=MUTED)
    ax_a.set_yticks(range(len(names)))
    ax_a.set_yticklabels(names, fontsize=8)
    ax_a.set_xticks([])
    ax_a.set_xlim(-0.5, grid.shape[1] - 0.5)
    ax_a.set_ylim(len(names) - 0.5, -2.1)
    ax_a.grid(False)
    ax_a.set_title("(a) WP1 single-point matrix: %d/%d computed; %d reduction-state cells "
                   "flagged no-diffuse (amber)"
                   % (computed, len(matrix), flagged), fontsize=9.5, color=INK)

    style(ax_b)
    labels = [row["name"] for row in axis]
    functional = [float(row["vertical_functional_effect_ev"]) for row in axis]
    basis = [float(row["vertical_basis_effect_ev"]) for row in axis]
    xs = np.arange(len(labels))
    ax_b.bar(xs - 0.19, functional, 0.36, color=BLUE, edgecolor="white", linewidth=0.8,
             label="functional")
    ax_b.bar(xs + 0.19, basis, 0.36, color=AMBER, edgecolor="white", linewidth=0.8,
             label="basis")
    top = max(max(functional), max(basis))
    ax_b.set_xticks(xs)
    ax_b.set_xticklabels(labels, fontsize=7, rotation=60, ha="right")
    ax_b.set_ylim(0, top * 1.30)
    ax_b.set_ylabel("vertical-IP method spread (eV)")
    ax_b.legend(fontsize=7, frameon=False, loc="upper right")
    ax_b.set_title("(b) Oxidation-axis method spread\n(4 settings x 8 molecules)",
                   fontsize=9.5, color=INK)

    fig.suptitle("F60  independent method audit measured: 128 single points + 32 relaxed-leg cells; "
                 "functional effect dominates the basis-set effect", fontsize=10.5, color=INK)
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    return finish(fig, path)


# ----------------------------------------------------------------- F61
def figure_ladder(path: Path):
    rung = load_json(RUNG)
    per_mol = rung["per_molecule"]
    counts = rung["decision_state_counts"]

    fig, (ax_a, ax_b, ax_c) = plt.subplots(1, 3, figsize=(16.2, 5.2),
                                           gridspec_kw={"width_ratios": [1.45, 0.92, 1.05]})
    style(ax_a)
    order = sorted(per_mol, key=lambda row: float(row["ip_p1v_ev"]))
    xs = np.arange(len(order))
    v = [float(row["ip_p1v_ev"]) for row in order]
    a = [float(row["ip_p1a_ev"]) for row in order]
    for xi, lo, hi in zip(xs, v, a):
        ax_a.annotate("", xy=(xi, hi), xytext=(xi, lo),
                      arrowprops=dict(arrowstyle="->", color="#9ca3af", linewidth=1.1))
    ax_a.scatter(xs, v, s=34, color=BLUE, zorder=3, label="P1v vertical (frozen)")
    ax_a.scatter(xs, a, s=34, color=RED, zorder=3, label="P1a adiabatic (frozen)")
    ax_a.set_xticks(xs)
    ax_a.set_xticklabels([row["name"] for row in order], fontsize=8, rotation=45, ha="right")
    ax_a.set_ylabel("oxidation potential proxy  [eV]")
    ax_a.legend(fontsize=8, frameon=False)
    ax_a.set_title("(a) Vertical -> adiabatic relaxation shift, n=%d (G layers pending)" % len(order),
                   fontsize=9.5, color=INK)

    style(ax_b)
    keys = ["STABLE", "UNRESOLVED", "ROBUST_INVERSION"]
    values = [int(counts.get(key, 0)) for key in keys]
    xb = np.arange(len(keys))
    ax_b.bar(xb, values, 0.55, color=[STATE_COLOUR[key] for key in keys],
             edgecolor="white", linewidth=0.8)
    for xi, value in zip(xb, values):
        ax_b.text(xi, value + 0.8, str(value), ha="center", fontsize=10, color=INK)
    ax_b.set_xticks(xb)
    ax_b.set_xticklabels(["STABLE", "UNRESOLVED", "ROBUST\nINVERSION"], fontsize=8.5)
    ax_b.set_ylabel("pairs (of 66)")
    ax_b.set_ylim(0, 63)
    ax_b.set_title("(b) Three-state verdicts on the frozen rung", fontsize=9.5, color=INK)

    style(ax_c)
    ladder = load_csv(LADDER)
    rung_order = []
    for row in ladder:
        if row["rung"] not in rung_order:
            rung_order.append(row["rung"])
    for axis, colour in (("oxidation", BLUE), ("reduction", RED)):
        series = [row for row in ladder if row["axis"] == axis]
        series = sorted(series, key=lambda row: rung_order.index(row["rung"]))
        xs_c = [rung_order.index(row["rung"]) for row in series]
        ys_c = [float(row["kendall_tau_b"]) for row in series]
        ax_c.plot(xs_c, ys_c, marker="o", markersize=4, linewidth=1.5, color=colour, label=axis)
        for xi, row in zip(xs_c, series):
            ax_c.annotate("f=%.2f" % float(row["f_unresolved_after"]), (xi, ys_c[xs_c.index(xi)]),
                          textcoords="offset points", xytext=(0, -13), ha="center",
                          fontsize=6.5, color=colour)
    ax_c.axhline(0.90, color=MUTED, linestyle="--", linewidth=1.0)
    ax_c.text(len(rung_order) - 1, 0.915, "ordering gate 0.90", ha="right", fontsize=7, color=MUTED)
    ax_c.axhline(0.0, color="#d1d5db", linewidth=0.9)
    ax_c.set_xticks(range(len(rung_order)))
    ax_c.set_xticklabels(rung_order, fontsize=7.5, rotation=30, ha="right")
    ax_c.set_ylabel("Kendall tau_b of the rung")
    ax_c.set_ylim(-0.62, 1.06)
    ax_c.legend(fontsize=8, frameon=False, loc="lower left")
    ax_c.set_title("(c) Frozen 5-rung ladder (frozen aggregates)", fontsize=9.5, color=INK)

    fig.suptitle("F61  E -> G -> ensemble ladder: the frozen evidence stops at the electronic-energy "
                 "and geometry rungs (plan WP3; ROBUST_INVERSION is a label, not a certified flip)",
                 fontsize=10.5, color=INK)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    return finish(fig, path)


# ----------------------------------------------------------------- F62
def figure_pair_identity(path: Path):
    pairs = load_csv(PAIR_EVIDENCE)
    identity = load_csv(IDENTITY)

    fig, (ax_a, ax_b) = plt.subplots(1, 2, figsize=(11.6, 5.2),
                                     gridspec_kw={"width_ratios": [1.0, 1.25]})
    style(ax_a)
    order = sorted(pairs, key=lambda row: float(row["d_upper_ev"]))
    values = [float(row["d_upper_ev"]) for row in order]
    xs = np.arange(len(order))
    ax_a.bar(xs, values, 0.9,
             color=[STATE_COLOUR.get(row["state"], MUTED) for row in order], edgecolor="none")
    ax_a.axhline(0.0, color=INK, linewidth=1.2)
    sigma = float(pairs[0]["sigma_ev"])
    for z, dash in ((1.0, "--"), (1.645, ":")):
        ax_a.axhline(sigma * z, color=MUTED, linewidth=0.9, linestyle=dash)
        ax_a.axhline(-sigma * z, color=MUTED, linewidth=0.9, linestyle=dash)
    ax_a.text(len(order) - 1, sigma * 1.645 + 0.02, "z=1.645 band", ha="right",
              fontsize=7.5, color=MUTED)
    ax_a.set_xticks([])
    ax_a.set_xlabel("66 pairs sorted by the relaxed separation")
    ax_a.set_ylabel("d_upper (P1a)  [eV]")
    ax_a.set_title("(a) Every pair: colour = three-state verdict", fontsize=9.5, color=INK)
    handles = [plt.Rectangle((0, 0), 1, 1, color=STATE_COLOUR[key]) for key in STATE_COLOUR]
    ax_a.legend(handles, list(STATE_COLOUR), fontsize=7.5, frameon=False, loc="upper left")

    style(ax_b)
    ox_labels = sorted({row["oxidation_label"] for row in identity})
    red_labels = sorted({row["reduction_label"] for row in identity})
    ox_counts = [sum(1 for row in identity if row["oxidation_label"] == label) for label in ox_labels]
    red_counts = [sum(1 for row in identity if row["reduction_label"] == label) for label in red_labels]
    labels = ["ox: " + label for label in ox_labels] + ["red: " + label for label in red_labels]
    values = ox_counts + red_counts
    colours = [GREEN] * len(ox_labels) + [RED] * len(red_labels)
    yb = np.arange(len(labels))[::-1]
    ax_b.barh(yb, values, 0.6, color=colours, edgecolor="white", linewidth=0.8)
    for yi, value in zip(yb, values):
        ax_b.text(value + 0.08, yi, str(value), va="center", fontsize=9, color=INK)
    ax_b.set_yticks(yb)
    ax_b.set_yticklabels(labels, fontsize=7.5)
    ax_b.set_xlim(0, max(values) + 1.6)
    ax_b.set_xlabel("conditional states (C1 motif m1)")
    ax_b.grid(True, axis="x", **GRID)
    ax_b.set_title("(b) State identity: only molecule-centred redox may rank", fontsize=9.5, color=INK)

    fig.suptitle("F62  fixed-background pair evidence and the identity outcome (plan WP3, frozen rung)",
                 fontsize=10.5, color=INK)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    return finish(fig, path)


# ----------------------------------------------------------------- F63
def figure_mechanism(path: Path):
    cases = load_csv(MECH_CASES)
    geom = load_csv(MECH_GEOM)

    fig, (ax_a, ax_b) = plt.subplots(1, 2, figsize=(11.6, 5.2))
    style(ax_a)
    xs = np.arange(len(geom))
    max_dr = [float(row["max_abs_bond_change_ang"]) for row in geom]
    colors = {"EMC": RED, "GBL": PURPLE, "SL": BLUE}
    ax_a.bar(xs, max_dr, 0.55, color=[colors.get(row["name"], MUTED) for row in geom],
             edgecolor="white", linewidth=0.8)
    for xi, row, value in zip(xs, geom, max_dr):
        ax_a.text(xi, value + 0.0018, "%.3f" % value, ha="center", fontsize=9, color=INK)
        ax_a.text(xi, 0.0020, row["max_bond_pair"], ha="center", fontsize=7.5, color="white")
    ax_a.set_xticks(xs)
    ax_a.set_xticklabels([row["name"] for row in geom], fontsize=9)
    ax_a.set_ylabel("max |dr| neutral -> cation  [Angstrom]")
    ax_a.set_ylim(0, max(max_dr) * 1.25)
    ax_a.set_title("(a) Frozen relaxation geometry: the heaviest change sits on EMC",
                   fontsize=9.5, color=INK)

    style(ax_b)
    xb = np.arange(len(cases))
    lower = [float(row["d_lower_ev"]) for row in cases]
    upper = [float(row["d_upper_ev"]) for row in cases]
    width = 0.32
    ax_b.bar(xb - width / 2, lower, width, color=BLUE, edgecolor="white", linewidth=0.8,
             label="d_lower (P1v, frozen)")
    ax_b.bar(xb + width / 2, upper, width, color=RED, edgecolor="white", linewidth=0.8,
             label="d_upper (P1a, frozen)")
    ax_b.axhline(0.0, color=INK, linewidth=1.2)
    for xi, lo, hi in zip(xb, lower, upper):
        ax_b.text(xi - width / 2, lo + (0.03 if lo >= 0 else -0.07), "%.2f" % lo,
                  ha="center", fontsize=8, color=INK)
        ax_b.text(xi + width / 2, hi + (0.03 if hi >= 0 else -0.07), "%.2f" % hi,
                  ha="center", fontsize=8, color=INK)
    ax_b.set_xticks(xb)
    ax_b.set_xticklabels([row["pair"].replace(" | ", "\nvs ") for row in cases], fontsize=8.5)
    ax_b.set_ylabel("pair separation  [eV]")
    ax_b.set_ylim(min(upper) * 1.55, max(lower) * 1.35)
    ax_b.legend(fontsize=8, frameon=False)
    ax_b.set_title("(b) The two ROBUST_INVERSION cases (sign flips under relaxation)",
                   fontsize=9.5, color=INK)

    fig.suptitle("F63  mechanism cases (plan 7.3): raw frozen structures + the case pairs; "
                 "density/spin, coordination and G-layer evidence still pending",
                 fontsize=10.5, color=INK)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    return finish(fig, path)


# ----------------------------------------------------------------- F64
def figure_budget(path: Path):
    rows = [row for row in load_csv(BUDGET_CURVES)
            if row["task"] == "C" and row["axis"] == "oxidation"]
    strategies = sorted({row["baseline"] for row in rows})
    palette = {"random": MUTED, "diversity": BLUE, "uncertainty": AMBER, "ranking_aware": GREEN}

    fig, (ax_a, ax_b) = plt.subplots(1, 2, figsize=(11.6, 5.2))
    style(ax_a)
    for baseline in strategies:
        series = sorted([row for row in rows if row["baseline"] == baseline],
                        key=lambda row: int(row["n_T"]))
        x = [int(row["n_T"]) for row in series]
        y = [float(row["tau_b"]) for row in series]
        ax_a.plot(x, y, marker="o", markersize=3.5, linewidth=1.5,
                  color=palette.get(baseline, INK), label=baseline)
    series = sorted([row for row in rows if row["baseline"] == "ranking_aware"],
                    key=lambda row: int(row["n_T"]))
    x = [int(row["n_T"]) for row in series]
    ax_a.fill_between(x, [float(row["tau_b_lo"]) for row in series],
                      [float(row["tau_b_hi"]) for row in series], color=GREEN, alpha=0.10)
    ax_a.axhline(0.80, color=RED, linestyle="--", linewidth=1.0)
    ax_a.text(x[-1], 0.815, "auxiliary endpoint tau_b = 0.80", ha="right", fontsize=7.5, color=RED)
    ax_a.set_xlabel("queried labels  n_T")
    ax_a.set_ylabel("Kendall tau_b")
    ax_a.set_ylim(0, 1.02)
    ax_a.legend(fontsize=8, frameon=False, loc="lower right")
    ax_a.set_title("(a) Recovery of the 12-label selection (frozen 20-seed replay)",
                   fontsize=9.5, color=INK)

    style(ax_b)
    for baseline in strategies:
        series = sorted([row for row in rows if row["baseline"] == baseline],
                        key=lambda row: int(row["n_T"]))
        x = [int(row["n_T"]) for row in series]
        y = [float(row["o30"]) for row in series]
        ax_b.plot(x, y, marker="o", markersize=3.5, linewidth=1.5,
                  color=palette.get(baseline, INK), label=baseline)
    ax_b.axhline(2.0 / 3.0, color=RED, linestyle="--", linewidth=1.0)
    ax_b.text(x[-1], 2.0 / 3.0 + 0.015, "endpoint O_3 = 2/3", ha="right", fontsize=7.5, color=RED)
    ax_b.set_xlabel("queried labels  n_T")
    ax_b.set_ylabel("Top-3 overlap  O_3")
    ax_b.set_ylim(0, 1.05)
    ax_b.legend(fontsize=8, frameon=False, loc="lower right")
    ax_b.set_title("(b) Same replay against the frozen success endpoint", fontsize=9.5, color=INK)

    fig.suptitle("F64  cumulative cost -> selection recovery (plan WP5): frozen in-pool replay, "
                 "not a blind pre-registration", fontsize=10.5, color=INK)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    return finish(fig, path)


FIGURES = [
    ("F59", "F59_physics_completion_definition.png", figure_definition),
    ("F60", "F60_physics_completion_method_audit.png", figure_method_audit),
    ("F61", "F61_physics_completion_ladder.png", figure_ladder),
    ("F62", "F62_physics_completion_pair_identity.png", figure_pair_identity),
    ("F63", "F63_physics_completion_mechanism_cases.png", figure_mechanism),
    ("F64", "F64_physics_completion_budget_curve.png", figure_budget),
]

INPUTS = [RUNG, JOB_MATRIX, AXIS, REUSABLE, PAIR_EVIDENCE, MECH_CASES, MECH_GEOM, IDENTITY, BUDGET_CURVES, LADDER,
          REPO_ROOT / "config" / "physics_completion_v1.yaml",
          REPO_ROOT / "data" / "references" / "anchor_primary_audit.csv"]

CAPTIONS = {
    "F59": "Cohort sizes and the seven registered quantities with their objective direction.",
    "F60": "The WP1 audit matrix is measured: all 128 single points plus the 32 relaxed-leg cells "
           "terminated. The 32 no-diffuse reduction-state cells are excluded from the decision "
           "statistics. Panel (b) shows the vertical-IP method spread; the functional effect is about "
           "an order of magnitude larger than the basis-set effect.",
    "F61": "Panel (c) is the frozen R15 five-rung ladder (n=18/18/12/10/10 per axis) with "
           "tau_b and f_unresolved; the vertical->adiabatic rung is recomputed pairwise here. "
           "G_single / G_ensemble and the reduction Li branch still need WP2 production, so "
           "ROBUST_INVERSION stays uncertified.",
    "F62": "All 66 frozen pairs with their three-state verdict, next to the C1 state-identity "
           "stratification that gates the reduction axis.",
    "F63": "The two robust inversions sit on EMC, whose frozen relaxation geometry moves the most; "
           "density/spin, coordination and G-layer evidence are still pending.",
    "F64": "Frozen 20-seed in-pool replay: tau_b and Top-3 overlap against the frozen endpoints.",
}


def build(check: bool) -> int:
    written = []
    for tag, name, builder in FIGURES:
        target = FIGDIR / name
        if not check:
            builder(target)
        written.append((tag, target))
    lines = [
        "# Figure manifest - physics_completion_v1 main figures (F59-F64)",
        "",
        "Six figures from plan section 14; every plotted number comes from a registered batch artefact.",
        "The 128 WP1 audit cells and the 32 relaxed-leg cells are derived-only deliveries: the raw ORCA",
        "logs stay outside the repository and outside the delivery mirror.",
        "",
        "| figure | file | inputs (SHA256) |",
        "| --- | --- | --- |",
    ]
    for tag, target in written:
        inputs = " ; ".join("`%s` %s" % (item.relative_to(REPO_ROOT).as_posix(), sha256_of(item))
                            for item in INPUTS)
        lines.append("| %s | `%s` | %s |" % (tag, target.name, inputs))
    lines += ["", "| figure | caption |", "| --- | --- |"]
    for tag, _ in written:
        lines.append("| %s | %s |" % (tag, CAPTIONS[tag]))
    lines += [
        "",
        "Scope note: F60 reports the measured audit matrix and the oxidation-axis method spread; the",
        "certification covers the method axis only (4 settings), not conformational sampling. F61 carries",
        "only the electronic-energy rung, so its ROBUST_INVERSION label is a method-axis-only certification.",
        "F64 is an in-pool replay of already-known data, not a blind pre-registration; R_3 is not",
        "tabulated in the frozen curve, so panel (b) uses the Top-3 overlap instead.",
        "",
        "Labels are English on purpose (no guaranteed CJK font in the workspace).",
        "",
    ]
    text = "\n".join(lines)
    if check:
        if MANIFEST.read_text(encoding="utf-8") != text:
            print("CHECK FAILED -- %s differs" % MANIFEST.relative_to(REPO_ROOT).as_posix())
            return 1
        for tag, target in written:
            if not target.is_file():
                print("CHECK FAILED -- missing %s" % target.name)
                return 1
        print("CHECK OK -- %d figures present and manifest is byte-identical" % len(written))
        return 0
    MANIFEST.write_text(text, encoding="utf-8", newline="\n")
    print("wrote %d figures + %s" % (len(written), MANIFEST.relative_to(REPO_ROOT).as_posix()))
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Build the physics_completion_v1 main figures.")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    return build(args.check)


if __name__ == "__main__":
    raise SystemExit(main())
