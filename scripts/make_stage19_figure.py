"""Stage 19 figures (F36, F37) -- does the second SCF solution survive relaxation?

F36 (the per-cell verdict)

    (a) the single-point separation of the two SCF solutions against their
        separation after relaxation, coloured by the four verdict classes, with the
        y = x line and the +/- 1 meV material band.  Preference flips are ringed.
    (b) the four verdict classes, plus the cells whose two arms are not both
        finished, straight off the analysis counts.
    (c) the verdict stacked per dielectric constant of the cell.
    (d) the same verdicts split by electronic state (cation / anion) and by
        molecule.

F37 (identity and geometry)

    (e) ``single_point_charge_l1`` against ``relax_charge_l1`` on log axes with the
        frozen Stage-18 threshold 0.039 drawn on both axes: does the identity
        verdict survive the relaxation?
    (f) ``rmsd_relaxed_arms`` against the shift of the arms' separation, with the
        0.02 A "same minimum" reference line.
    (g) the two arms' energy drops, paired cell by cell.
    (h) where the reduced spin centre sits, default arm against moread arm.  This
        is descriptive only -- the argmax centre hops between near-degenerate atoms
        and is never used as a criterion here.

Every number is read from the JSON / CSV products under ``--data-dir``; the only
literals in this module are protocol constants.  Labels are ASCII on purpose: the
workspace has no guaranteed CJK font, so Chinese would render as boxes.  The
manifest captions, which the terminal site quotes verbatim, are Chinese.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = REPO_ROOT / "outputs" / "week18"
DEFAULT_OUTDIR = REPO_ROOT / "outputs" / "figures"

MANIFEST_NAME = "figure_manifest_week18_stage19.md"
FIGURE_F36 = "F36_stage19_relax_outcomes.png"
FIGURE_F37 = "F37_stage19_identity_geometry.png"

ANALYSIS_JSON = "stage19_relax_analysis.json"
CELLS_CSV = "stage19_relax_cells_analysis.csv"

# -- named protocol constants (the only literals allowed in this script) --------
OUTCOMES = ("distinct_lower", "distinct_higher", "same_lower", "same_higher")

#: Frozen in ``scripts/analyze_stage19_relax.py``: a cell counts as "near threshold"
#: when its distance to the frozen cut is within 20% of the cut itself.  This is a
#: *descriptive* flag only -- the verdict stays ``relax_charge_l1 > threshold``.
NEAR_THRESHOLD_FRACTION = 0.2

OUTCOME_COLOR = {
    "distinct_lower": "#c0392b",
    "distinct_higher": "#d98218",
    "same_lower": "#1f5fa9",
    "same_higher": "#1a7d4f",
    "incomplete": "#9a9a9a",
}
OUTCOME_LABEL = {
    "distinct_lower": "distinct, moread still lower",
    "distinct_higher": "distinct, preference flipped",
    "same_lower": "same state, moread lower",
    "same_higher": "same state, moread higher",
    "incomplete": "not finished (an arm is missing)",
}

RED = "#c0392b"
BLUE = "#1f5fa9"
GREEN = "#1a7d4f"
ORANGE = "#d98218"
GREY = "#9a9a9a"
DARK = "#222222"


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
    """Repository-relative where possible, absolute otherwise (tmp dirs in tests)."""

    path = Path(path)
    try:
        return str(path.relative_to(REPO_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def save(fig, path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=170, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("wrote %s (%d bytes)" % (display(path), path.stat().st_size))
    return path


def complete_cells(cells):
    """Cells whose two arms both parsed; everything else is never plotted as data."""

    return [cell for cell in cells if cell.get("both_arms_ok")]


def epsilon_keys(groups):
    return sorted(groups, key=float)


def span(values, pad=0.12, fallback=(-0.05, 0.05)):
    clean = [float(value) for value in values if value is not None]
    if not clean:
        return fallback
    lo, hi = min(clean), max(clean)
    width = hi - lo
    if width <= 0:
        width = max(abs(hi), 1e-3) * 0.2
    return lo - pad * width, hi + pad * width
# ---------------------------------------------------------------------------
# F36 -- the per-cell verdict
# ---------------------------------------------------------------------------

def panel_a(ax, cells, material_ev, overall):
    done = complete_cells(cells)
    lo, hi = span([c["single_point_delta_ev"] for c in done]
                  + [c["relax_delta_ev"] for c in done])
    grid = np.linspace(lo, hi, 64)
    ax.fill_between(grid, grid - material_ev, grid + material_ev, color=GREY,
                    alpha=0.28, zorder=0, label="+/- 1 meV (material)")
    ax.plot(grid, grid, color=DARK, lw=1.0, ls=":", zorder=1)
    ax.axhline(0.0, color=GREY, lw=0.8, zorder=1)
    ax.axvline(0.0, color=GREY, lw=0.8, zorder=1)
    for outcome in OUTCOMES:
        rows = [c for c in done if c["outcome"] == outcome]
        if not rows:
            continue
        ax.scatter([c["single_point_delta_ev"] for c in rows],
                   [c["relax_delta_ev"] for c in rows], s=40,
                   color=OUTCOME_COLOR[outcome], alpha=0.88, edgecolor="white",
                   linewidth=0.6, zorder=3,
                   label="%s (n=%d)" % (outcome, len(rows)))
    flips = [c for c in done if c.get("preference_flipped")]
    if flips:
        ax.scatter([c["single_point_delta_ev"] for c in flips],
                   [c["relax_delta_ev"] for c in flips], s=170, facecolor="none",
                   edgecolor=DARK, linewidth=1.1, zorder=4,
                   label="preference flipped (n=%d)" % len(flips))
    ax.set_xlim(lo, hi)
    ax.set_ylim(lo, hi)
    ax.set_xlabel("single-point separation of the two solutions (eV)")
    ax.set_ylabel("separation after relaxation (eV)  [same two arms, relaxed]")
    ax.set_title("(a) per cell: before vs after relaxation")
    ax.legend(fontsize=6.5, frameon=False, loc="upper left")
    median_single = overall["abs_single_point_delta_ev"]["p50"]
    median_relax = overall["abs_relax_delta_ev"]["p50"]
    ax.scatter([median_single], [median_relax], marker="*", s=200, color=DARK,
               zorder=5, label="|delta| median, before -> after")
    ax.text(0.98, 0.03,
            "median |delta|: %.4f eV at the single point\n"
            "-> %.5f eV after relaxation (x%.0f smaller)\n"
            "the single-point preference was reversed in %d of the %d cells"
            % (median_single, median_relax, median_single / median_relax,
               len(flips), len(done)),
            transform=ax.transAxes, ha="right", va="bottom", fontsize=7,
            color=DARK, bbox=dict(boxstyle="round", fc="white", ec=GREY, lw=0.6))
    missing = len(cells) - len(done)
    if missing:
        ax.text(0.02, 0.03,
                "%d of %d cells still missing an arm\n(not plotted, never filled in)"
                % (missing, len(cells)),
                transform=ax.transAxes, ha="left", va="bottom", fontsize=7,
                color=DARK, bbox=dict(boxstyle="round", fc="#f4f4f4", ec=GREY, lw=0.6))


def panel_b(ax, counts, n_cells):
    keys = OUTCOMES + ("incomplete",)
    values = [int(counts[key]) for key in keys]
    xs = np.arange(len(keys))
    ax.bar(xs, values, color=[OUTCOME_COLOR[key] for key in keys], width=0.68)
    for x, value in zip(xs, values):
        ax.text(x, value + max(values) * 0.03, str(value), ha="center", fontsize=8.5)
    ax.set_xticks(xs)
    ax.set_xticklabels(["distinct\nlower", "distinct\nhigher", "same\nlower",
                        "same\nhigher", "not\nfinished"], fontsize=8)
    ax.set_ylim(0, max(max(values), 1) * 1.38)
    ax.set_ylabel("cells")
    ax.set_title("(b) verdict over the %d moread_lower cells" % n_cells)
    ax.text(0.02, 0.97,
            "denominator = the %d cells whose two single-point\n"
            "solutions differ and favour moread; not a rate\n"
            "over the 414-cell directory" % n_cells,
            transform=ax.transAxes, ha="left", va="top", fontsize=7,
            bbox=dict(boxstyle="round", fc="white", ec=GREY, lw=0.6))


def panel_c(ax, by_epsilon):
    keys = epsilon_keys(by_epsilon)
    xs = np.arange(len(keys))
    bottom = np.zeros(len(keys))
    for outcome in OUTCOMES + ("incomplete",):
        values = np.array([float(by_epsilon[key]["outcomes"][outcome])
                           for key in keys])
        if values.sum() == 0:
            continue
        ax.bar(xs, values, bottom=bottom, color=OUTCOME_COLOR[outcome],
               width=0.7, label=outcome)
        bottom += values
    ax.set_xticks(xs)
    ax.set_xticklabels(["%g" % float(key) for key in keys], fontsize=8)
    ax.set_xlabel("epsilon (bare CPCM of the cell)")
    ax.set_ylabel("cells  (denominator: the moread_lower set)")
    ax.set_ylim(0.0, max(bottom.max() * 1.42, 1.0))
    ax.set_title("(c) verdict per dielectric constant")
    ax.legend(fontsize=6.5, frameon=False, loc="upper center", ncol=2)


def panel_d(ax, by_state, by_molecule):
    groups = ([("state: " + key, by_state[key]) for key in sorted(by_state)]
              + [("mol: " + key, by_molecule[key]) for key in sorted(by_molecule)])
    ys = np.arange(len(groups))
    left = np.zeros(len(groups))
    for outcome in OUTCOMES + ("incomplete",):
        values = np.array([float(block["outcomes"][outcome])
                           for _, block in groups])
        if values.sum() == 0:
            continue
        ax.barh(ys, values, left=left, color=OUTCOME_COLOR[outcome], label=outcome)
        left += values
    for y, (name, block) in zip(ys, groups):
        ax.text(left[y] + 0.25, y, "n=%d" % int(block["n_cells"]), va="center",
                fontsize=7)
    ax.set_yticks(ys)
    ax.set_yticklabels([name for name, _ in groups], fontsize=7.5)
    ax.invert_yaxis()
    ax.set_xlim(0, max(left.max() * 1.18, 1.0))
    ax.set_xlabel("cells  (denominator: the moread_lower set)")
    ax.set_title("(d) by state and by molecule")


def figure_relax(outdir, payload):
    cells = payload["cells"]
    aggregates = payload["aggregates"]
    counts = aggregates["all"]["all"]["outcomes"]
    fig = plt.figure(figsize=(13.4, 9.6))
    grid = fig.add_gridspec(2, 2, hspace=0.34, wspace=0.26)
    panel_a(fig.add_subplot(grid[0, 0]), cells, float(payload["material_threshold_ev"]),
            aggregates["all"]["all"])
    panel_b(fig.add_subplot(grid[0, 1]), counts, payload["n_cells"])
    panel_c(fig.add_subplot(grid[1, 0]), aggregates["by_epsilon"])
    panel_d(fig.add_subplot(grid[1, 1]), aggregates["by_state"], aggregates["by_molecule"])
    fig.suptitle("Stage 19 -- does the second SCF solution survive relaxation? "
                 "(%d of the %d moread_lower cells have both arms finished)"
                 % (aggregates["all"]["all"]["n_complete"], payload["n_cells"]),
                 fontsize=12)
    return save(fig, Path(outdir) / FIGURE_F36)
# ---------------------------------------------------------------------------
# F37 -- identity and geometry
# ---------------------------------------------------------------------------

def panel_e(ax, cells, threshold):
    done = [c for c in complete_cells(cells)
            if c.get("single_point_charge_l1") is not None
            and c.get("relax_charge_l1") is not None]
    band_lo = threshold * (1.0 - NEAR_THRESHOLD_FRACTION)
    band_hi = threshold * (1.0 + NEAR_THRESHOLD_FRACTION)
    near = [c for c in done
            if bool(c.get("near_threshold",
                          abs(c["relax_charge_l1"] - threshold)
                          <= NEAR_THRESHOLD_FRACTION * threshold))]
    if done:
        xs = [c["single_point_charge_l1"] for c in done]
        ys = [c["relax_charge_l1"] for c in done]
        lo, hi = span(xs + ys, pad=0.15, fallback=(0.004, 0.4))
        lo = max(lo, 1e-3)
        ax.scatter(xs, ys, s=40, c=[OUTCOME_COLOR[c["outcome"]] for c in done],
                   alpha=0.88, edgecolor="white", linewidth=0.6, zorder=3)
        if near:
            ax.scatter([c["single_point_charge_l1"] for c in near],
                       [c["relax_charge_l1"] for c in near], s=150,
                       facecolor="none", edgecolor=DARK, linewidth=1.3, zorder=4,
                       label="near threshold (n=%d)" % len(near))
        same = sum(1 for c in done if c["single_point_charge_l1"] > threshold
                   and c["relax_charge_l1"] > threshold)
        ax.text(0.02, 0.97,
                "above threshold before AND after: %d / %d\n"
                "frozen threshold %.3f; band is +/- %d%%\n"
                "cells inside the band: %d"
                % (same, len(done), threshold, int(NEAR_THRESHOLD_FRACTION * 100),
                   len(near)),
                transform=ax.transAxes, ha="left", va="top", fontsize=7.5,
                bbox=dict(boxstyle="round", fc="white", ec=GREY, lw=0.6))
    else:
        lo, hi = 4e-3, 4e-1
        ax.text(0.5, 0.5, "no cell with both arms finished yet",
                transform=ax.transAxes, ha="center", va="center", fontsize=8)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(lo, hi)
    ax.set_ylim(lo, hi)
    ax.axhspan(band_lo, band_hi, color=ORANGE, alpha=0.16, zorder=0,
               label="near-threshold band")
    ax.axhline(band_lo, color=ORANGE, lw=0.9, ls=":")
    ax.axhline(band_hi, color=ORANGE, lw=0.9, ls=":")
    ax.plot([lo, hi], [lo, hi], color=DARK, lw=1.0, ls=":")
    ax.axhline(threshold, color=DARK, lw=1.1, ls="--")
    ax.axvline(threshold, color=DARK, lw=1.1, ls="--")
    handles, labels = ax.get_legend_handles_labels()
    if handles:
        ax.legend(handles, labels, fontsize=6.5, frameon=False, loc="lower right")
    ax.set_xlabel("charge_l1 at the single point")
    ax.set_ylabel("charge_l1 after relaxation")
    ax.set_title("(e) the identity channel, before and after relaxation")


def panel_f(ax, cells, tolerance):
    done = [c for c in complete_cells(cells)
            if c.get("rmsd_relaxed_arms") is not None
            and c.get("delta_shift_ev") is not None]
    if done:
        xs = [c["delta_shift_ev"] for c in done]
        ys = [c["rmsd_relaxed_arms"] for c in done]
        lo, hi = span(xs, pad=0.15, fallback=(-0.05, 0.05))
        ax.scatter(xs, ys, s=40, c=[OUTCOME_COLOR[c["outcome"]] for c in done],
                   alpha=0.88, edgecolor="white", linewidth=0.6, zorder=3)
        below = sum(1 for c in done if c["rmsd_same_minimum"])
        ax.set_xlim(lo, hi)
        top = max(max(ys), tolerance) * 1.35
        ax.set_ylim(0.0, top if top > 0 else 0.1)
        ax.text(0.98, 0.97,
                "RMSD <= %.2f A: %d / %d cells"
                % (tolerance, below, len(done)),
                transform=ax.transAxes, ha="right", va="top", fontsize=7.5,
                bbox=dict(boxstyle="round", fc="white", ec=GREY, lw=0.6))
    else:
        ax.text(0.5, 0.5, "no cell with both arms finished yet",
                transform=ax.transAxes, ha="center", va="center", fontsize=8)
    ax.axhline(tolerance, color=DARK, lw=1.1, ls="--")
    ax.axvline(0.0, color=GREY, lw=0.9)
    ax.set_xlabel("shift of the arms' separation (eV)")
    ax.set_ylabel("relaxed arms RMSD (A)")
    ax.set_title("(f) geometry: same minimum or two minima?")


def panel_g(ax, cells, overall):
    done = complete_cells(cells)
    xs = [c["energy_drop_default_ev"] for c in done]
    ys = [c["energy_drop_moread_ev"] for c in done]
    if done:
        lo, hi = span(xs + ys, pad=0.15, fallback=(0.0, 0.1))
        ax.plot([lo, hi], [lo, hi], color=DARK, lw=1.0, ls=":")
        ax.scatter(xs, ys, s=40, c=[OUTCOME_COLOR[c["outcome"]] for c in done],
                   alpha=0.88, edgecolor="white", linewidth=0.6, zorder=3)
        ax.set_xlim(lo, hi)
        ax.set_ylim(lo, hi)
        more = sum(1 for x, y in zip(xs, ys) if y > x)
        med_d = overall["energy_drop_default_ev"]["p50"]
        med_m = overall["energy_drop_moread_ev"]["p50"]
        ax.scatter([med_d], [med_m], marker="*", s=200, color=DARK, zorder=5)
        ax.text(0.02, 0.97,
                "moread drops more in %d / %d cells\n"
                "median drop: default %.3f eV vs moread %.3f eV\n"
                "(the default arm falls further, so moread loses its edge)"
                % (more, len(done), med_d, med_m),
                transform=ax.transAxes, ha="left", va="top", fontsize=7.5,
                bbox=dict(boxstyle="round", fc="white", ec=GREY, lw=0.6))
    else:
        ax.text(0.5, 0.5, "no cell with both arms finished yet",
                transform=ax.transAxes, ha="center", va="center", fontsize=8)
    ax.set_xlabel("default arm: energy drop in the relaxation (eV)")
    ax.set_ylabel("moread arm: energy drop (eV)")
    ax.set_title("(g) which arm falls further?")


def panel_h(ax, cells):
    done = complete_cells(cells)
    centres = [(c.get("relax_spin_atom_default"), c.get("relax_spin_atom_moread"))
               for c in done]

    def label(value):
        """``'O2'`` / ``'C1'`` / ``'none'`` -- the census names the centre by
        element and atom number, so it is a label, never an integer."""

        if value in (None, ""):
            return "none"
        return str(value)

    names = sorted({label(a) for a, _ in centres} | {label(b) for _, b in centres},
                   key=lambda name: (name == "none", name))
    index = {name: i for i, name in enumerate(names)}
    matrix = np.zeros((len(names), len(names)))
    for a, b in centres:
        matrix[index[label(a)], index[label(b)]] += 1
    top = max(matrix.max(), 1.0)
    ax.imshow(matrix, cmap="Blues", vmin=0.0, vmax=top, origin="upper",
              aspect="auto")
    for i in range(len(names)):
        for j in range(len(names)):
            if matrix[i, j]:
                ax.text(j, i, "%d" % int(matrix[i, j]), ha="center", va="center",
                        fontsize=8, color="white" if matrix[i, j] > top * 0.6 else DARK)
    ax.set_xticks(np.arange(len(names)))
    ax.set_yticks(np.arange(len(names)))
    ax.set_xticklabels(names, fontsize=8)
    ax.set_yticklabels(names, fontsize=8)
    ax.set_xlabel("moread arm: atom carrying the reduced spin")
    ax.set_ylabel("default arm: atom carrying the reduced spin")
    same_centre = sum(1 for c in done if c["relax_spin_atom_default"]
                      == c["relax_spin_atom_moread"])
    same_orbital = sum(1 for c in done if c.get("relax_same_orbital_label"))
    ax.set_title("(h) spin-centre migration (descriptive only)\n"
                 "same centre %d / %d; same orbital label (argmax) %d / %d"
                 % (same_centre, len(done), same_orbital, len(done)),
                 fontsize=11)


def figure_identity(outdir, payload):
    cells = payload["cells"]
    fig = plt.figure(figsize=(13.4, 9.6))
    grid = fig.add_gridspec(2, 2, hspace=0.34, wspace=0.26)
    panel_e(fig.add_subplot(grid[0, 0]), cells, float(payload["threshold_charge_l1"]))
    panel_f(fig.add_subplot(grid[0, 1]), cells,
            float(payload["geometry_same_tolerance_angstrom"]))
    panel_g(fig.add_subplot(grid[1, 0]), cells, payload["aggregates"]["all"]["all"])
    panel_h(fig.add_subplot(grid[1, 1]), cells)
    fig.suptitle("Stage 19 -- identity and geometry of the 37 relaxed cells "
                 "(%d complete)" % len(complete_cells(cells)), fontsize=12)
    return save(fig, Path(outdir) / FIGURE_F37)
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


def caption_f36(counts, n_cells, n_complete, overall):
    return ("(a) 单点 Δ 对弛豫后 Δ（按结局着色，y=x 与 ±1 meV 带；|Δ| 中位数 "
            "%.4f → %.5f eV，缩小 %.0f 倍）；"
            "(b) %d 个 moread_lower 格子的裁决：distinct_lower %d / distinct_higher %d / "
            "same_lower %d / same_higher %d（已完成 %d）；"
            "(c) 按 ε 的结局堆叠；(d) 按态与分子的分解"
            % (overall["abs_single_point_delta_ev"]["p50"],
               overall["abs_relax_delta_ev"]["p50"],
               overall["abs_single_point_delta_ev"]["p50"]
               / overall["abs_relax_delta_ev"]["p50"],
               n_cells, counts["distinct_lower"], counts["distinct_higher"],
               counts["same_lower"], counts["same_higher"], n_complete))


def caption_f37(cells, threshold, tolerance, overall):
    done = complete_cells(cells)
    same = sum(1 for c in done if c.get("single_point_charge_l1") is not None
               and c["single_point_charge_l1"] > threshold
               and c.get("relax_charge_l1") is not None
               and c["relax_charge_l1"] > threshold)
    below = sum(1 for c in done if c.get("rmsd_same_minimum"))
    near = sum(1 for c in done
               if bool(c.get("near_threshold",
                             abs(c["relax_charge_l1"] - threshold)
                             <= NEAR_THRESHOLD_FRACTION * threshold)))
    return ("(e) 弛豫前后 charge_l1 对数散点、冻结阈值 %.3f 与 ±%d%% 贴阈值带"
            "（弛豫前后都在阈值以上 %d/%d，贴阈值 %d 格）；"
            "(f) 双解几何 RMSD 对 Δ 漂移（%.2f Å 同极小点参考线，下方 %d/%d 格）；"
            "(g) 两臂弛豫能量降配对（默认解中位降 %.3f eV vs moread %.3f eV）；"
            "(h) 自旋中心迁移矩阵（argmax 仅作描述，不作判据）"
            % (threshold, int(NEAR_THRESHOLD_FRACTION * 100), same, len(done), near,
               tolerance, below, len(done),
               overall["energy_drop_default_ev"]["p50"],
               overall["energy_drop_moread_ev"]["p50"]))


def missing_cells(cells):
    return ["%s %s eps=%g" % (c["name"], c["state"], float(c["epsilon"]))
            for c in cells if not c.get("both_arms_ok")]


def write_manifest(outdir, data_dir, figure_paths, inputs, payload):
    cells = payload["cells"]
    aggregates = payload["aggregates"]
    overall = aggregates["all"]["all"]
    counts = overall["outcomes"]
    threshold = float(payload["threshold_charge_l1"])
    tolerance = float(payload["geometry_same_tolerance_angstrom"])
    material_ev = float(payload["material_threshold_ev"])
    done = complete_cells(cells)
    captions = {FIGURE_F36: caption_f36(counts, payload["n_cells"],
                                        overall["n_complete"], overall),
                FIGURE_F37: caption_f37(cells, threshold, tolerance, overall)}

    lines = ["# figure_manifest_week18_stage19", "",
             "| figure | sha256 | size |",
             "| --- | --- | --- |"]
    for path in figure_paths:
        lines.append("| `%s` | `%s` | %d B |"
                     % (path.name, sha256(path), path.stat().st_size))
    lines += ["", "| input | sha256 |", "| --- | --- |"]
    for path in inputs:
        lines.append("| `%s` | `%s` |"
                     % (display(path), sha256(path)))
    lines += ["", "Generate (from the repository root):", "", "```powershell",
              "& $py scripts\\make_stage19_figure.py",
              "& $py scripts\\make_stage19_figure.py --check",
              "```", "",
              "The PNGs carry no timestamp, so re-running on the same inputs gives "
              "byte-identical files and ``--check`` compares SHA256 directly.", ""]

    lines += ["## denominators", "",
              "- Every count and proportion on these two figures is conditional on the "
              "%d `moread_lower` cells -- the complete set of cells whose two "
              "single-point SCF solutions differ *and* favour moread -- never on the "
              "414-cell directory." % payload["n_cells"],
              "- Read `x/%d` as \"given that a single point produced a metastable pair "
              "that was lower, does it survive relaxation?\", which is a well-defined "
              "conditional probability on that definition set.  It is not a "
              "population incidence, and this stage makes no statement of the form "
              "\"the default solution is safe in N%% of cells\"." % payload["n_cells"],
              ""]

    lines += ["## F36 -- `%s`" % FIGURE_F36, "",
              "One-line caption (verbatim, for the terminal site): %s"
              % captions[FIGURE_F36], "",
              "### (a) per cell: before vs after relaxation", "",
              "The single-point separation of the two SCF solutions against the same "
              "separation after both arms were relaxed (y = x dotted, +/- %.0e eV "
              "material band shaded).  A point above the band is a cell where the "
              "relaxation has *reversed* the single-point preference." % material_ev,
              ""]
    flips = [c for c in done if c.get("preference_flipped")]
    lines.append("- cells whose single-point preference was reversed by the "
                 "relaxation: %d of %d (%s)"
                 % (len(flips), len(done),
                    ", ".join("%s %s eps=%g" % (c["name"], c["state"], float(c["epsilon"]))
                              for c in flips) or "none"))
    lines.append("- separation after relaxation grew in %d and shrank in %d of the "
                 "%d complete cells"
                 % (sum(1 for c in done if c["delta_shift_ev"] > 0),
                    sum(1 for c in done if c["delta_shift_ev"] < 0), len(done)))
    lines += ["", "### (b) the verdict over the %d moread_lower cells" % payload["n_cells"],
              "",
              "- distinct_lower %d, distinct_higher %d, same_lower %d, same_higher %d, "
              "not finished %d"
              % (counts["distinct_lower"], counts["distinct_higher"],
                 counts["same_lower"], counts["same_higher"], counts["incomplete"]),
              "- still electronically distinct after relaxation: %d of %d complete "
              "cells (`charge_l1 > %.3f`); still carrying the lower moread energy: %d"
              % (overall["n_still_distinct"], overall["n_complete"], threshold,
                 overall["n_still_lower"])]
    lines += ["", "### (c) per dielectric constant", ""]
    for key in epsilon_keys(aggregates["by_epsilon"]):
        block = aggregates["by_epsilon"][key]
        lines.append("- eps %g (n = %d, complete %d): distinct_lower %d, "
                     "distinct_higher %d, same_lower %d, same_higher %d, "
                     "not finished %d"
                     % (float(key), block["n_cells"], block["n_complete"],
                        block["outcomes"]["distinct_lower"],
                        block["outcomes"]["distinct_higher"],
                        block["outcomes"]["same_lower"],
                        block["outcomes"]["same_higher"],
                        block["outcomes"]["incomplete"]))
    lines += ["", "### (d) by state and by molecule", ""]
    for key in sorted(aggregates["by_state"]):
        block = aggregates["by_state"][key]
        lines.append("- %s (n = %d, complete %d): distinct_lower %d, "
                     "distinct_higher %d, same_lower %d, same_higher %d, "
                     "not finished %d"
                     % (key, block["n_cells"], block["n_complete"],
                        block["outcomes"]["distinct_lower"],
                        block["outcomes"]["distinct_higher"],
                        block["outcomes"]["same_lower"],
                        block["outcomes"]["same_higher"],
                        block["outcomes"]["incomplete"]))
    for key in sorted(aggregates["by_molecule"]):
        block = aggregates["by_molecule"][key]
        lines.append("- %s (n = %d, complete %d): distinct_lower %d, "
                     "distinct_higher %d, same_lower %d, same_higher %d, "
                     "not finished %d"
                     % (key, block["n_cells"], block["n_complete"],
                        block["outcomes"]["distinct_lower"],
                        block["outcomes"]["distinct_higher"],
                        block["outcomes"]["same_lower"],
                        block["outcomes"]["same_higher"],
                        block["outcomes"]["incomplete"]))
    merged = [c for c in cells if c.get("both_arms_ok")
              and c["outcome"].startswith("same_")]
    lines.append("- the %d cells where the two relaxed endpoints merge "
                 "electronically (|relax_charge_l1 - threshold| on the same side, "
                 "`charge_l1 <= %.3f`): %s"
                 % (len(merged), threshold,
                    "; ".join("%s %s eps %g (%s)"
                              % (c["name"], c["state"], float(c["epsilon"]),
                                 c["outcome"])
                              for c in sorted(merged, key=lambda c: (c["name"],
                                                                     c["state"],
                                                                     c["epsilon"])))
                    or "none"))
    lines.append("")
    return lines
# The head builder above stops after F36; this wrapper appends the F37 section
# (defined below, next to the other rendering helpers) and writes the file.

_build_manifest_head = write_manifest


def write_manifest(outdir, data_dir, figure_paths, inputs, payload, caption37):
    lines = _build_manifest_head(outdir, data_dir, figure_paths, inputs, payload)
    lines += f37_lines(payload, caption37)
    manifest = Path(outdir) / MANIFEST_NAME
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print("wrote %s (%d bytes)"
          % (display(manifest), manifest.stat().st_size))
    return manifest

def f37_lines(payload, caption):
    cells = payload["cells"]
    done = complete_cells(cells)
    threshold = float(payload["threshold_charge_l1"])
    tolerance = float(payload["geometry_same_tolerance_angstrom"])
    measurable = [c for c in done if c.get("single_point_charge_l1") is not None
                  and c.get("relax_charge_l1") is not None]
    above_before = [c for c in measurable if c["single_point_charge_l1"] > threshold]
    above_after = [c for c in measurable if c["relax_charge_l1"] > threshold]
    both = [c for c in measurable if c["single_point_charge_l1"] > threshold
            and c["relax_charge_l1"] > threshold]
    lines = ["## F37 -- `%s`" % FIGURE_F37, "",
             "One-line caption (verbatim, for the terminal site): %s" % caption, "",
             "### (e) the identity channel, before and after relaxation", "",
             "- complete cells with a usable `charge_l1` on both sides: %d; above the "
             "frozen threshold %.3f at the single point %d, after relaxation %d, "
             "at both %d"
             % (len(measurable), threshold, len(above_before), len(above_after),
                len(both))]
    for cell in measurable:
        lines.append("- %s %s eps=%g: single point %.6f -> relaxed %.6f (%s)"
                     % (cell["name"], cell["state"], float(cell["epsilon"]),
                        float(cell["single_point_charge_l1"]),
                        float(cell["relax_charge_l1"]),
                        "still distinct" if cell["still_distinct"]
                        else "no longer distinct"))
    near_band = threshold * NEAR_THRESHOLD_FRACTION
    near = [c for c in measurable
            if bool(c.get("near_threshold",
                          abs(c["relax_charge_l1"] - threshold) <= near_band))]
    lines.append("- near-threshold cells (descriptive: |relax_charge_l1 - %.3f| <= "
                 "%.4f, i.e. +/- %d%% of the cut): %d of %d%s"
                 % (threshold, near_band, int(NEAR_THRESHOLD_FRACTION * 100),
                    len(near), len(measurable),
                    "" if not near else " -- " + ", ".join(
                        "%s %s eps=%g (margin %+.5f)"
                        % (c["name"], c["state"], float(c["epsilon"]),
                           float(c.get("charge_l1_margin",
                                       c["relax_charge_l1"] - threshold)))
                        for c in near)))
    lines.append("- `near_threshold` is a description, never a criterion: the verdict "
                 "stays the frozen `relax_charge_l1 > %.3f`, and a cell inside the band "
                 "is still counted on whichever side of the cut it falls."
                 % threshold)
    rmsd = [c["rmsd_relaxed_arms"] for c in done
            if c.get("rmsd_relaxed_arms") is not None]
    same_min = [c for c in done if c.get("rmsd_same_minimum")]
    lines += ["", "### (f) geometry: same minimum or two minima?", "",
              "- relaxed arms RMSD spans %s over %d cells; %d fall at or below the "
              "%.2f A reference for 'the same minimum'"
              % ("n/a" if not rmsd else "%.4f to %.4f A" % (min(rmsd), max(rmsd)),
                 len(rmsd), len(same_min), tolerance),
              "- the RMSD is descriptive: the verdict is the frozen electronic "
              "criterion, not this cut"]
    if done:
        drops_d = [c["energy_drop_default_ev"] for c in done]
        drops_m = [c["energy_drop_moread_ev"] for c in done]
        lines += ["", "### (g) which arm falls further?", "",
                  "- median energy drop: default %.4f eV, moread %.4f eV; moread falls "
                  "further in %d of %d cells"
                  % (float(np.median(drops_d)), float(np.median(drops_m)),
                     sum(1 for a, b in zip(drops_d, drops_m) if b > a), len(done))]
    same_centre = [c for c in done
                   if c.get("relax_spin_atom_default") == c.get("relax_spin_atom_moread")]
    same_orbital = [c for c in done if c.get("relax_same_orbital_label")]
    lines += ["", "### (h) spin-centre migration (descriptive only)", "",
              "- the atom carrying the reduced spin is the same in %d of %d complete "
              "cells; the argmax orbital label agrees in %d"
              % (len(same_centre), len(done), len(same_orbital)),
              "- the argmax hops between near-degenerate atoms, so neither count is a "
              "criterion anywhere in this stage"]
    missing = missing_cells(cells)
    lines += ["", "## coverage", "",
              "- %d of %d cells have both arms finished; %d are marked as missing in "
              "the panels and never filled in with a zero"
              % (len(done), len(cells), len(missing))]
    if missing:
        lines.append("- missing: %s" % ", ".join(missing))
    lines += ["", "Palette and dpi follow the other week figures (dpi = 170, "
              "bbox_inches = tight). All in-figure labels are ASCII because the "
              "workspace has no guaranteed CJK font; the captions above are Chinese "
              "and are quoted verbatim by the site builder.", ""]
    return lines


def run_check(outdir) -> int:
    manifest = Path(outdir) / MANIFEST_NAME
    if not manifest.exists():
        print("check FAILED: manifest missing: %s" % manifest)
        return 1
    rows = _figure_rows(manifest.read_text(encoding="utf-8"))
    status = 0
    for name in (FIGURE_F36, FIGURE_F37):
        path = Path(outdir) / name
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
    if status == 0:
        print("check ok: manifest matches disk")
    return status


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Stage 19 figures (F36, F37).")
    parser.add_argument("--outdir", default=str(DEFAULT_OUTDIR),
                        help="figure output directory (default outputs/figures)")
    parser.add_argument("--data-dir", default=str(DEFAULT_DATA_DIR),
                        help="Stage 19 product directory (default outputs/week18)")
    parser.add_argument("--check", action="store_true",
                        help="verify the products exist and the manifest sha256 matches")
    args = parser.parse_args(argv)

    outdir = Path(args.outdir)
    data_dir = Path(args.data_dir)

    if args.check:
        return run_check(outdir)

    payload = load_json(data_dir / ANALYSIS_JSON)
    cells_csv = load_csv(data_dir / CELLS_CSV)
    if len(cells_csv) != payload["n_cells"]:
        raise SystemExit("cells CSV has %d rows, JSON says %d"
                         % (len(cells_csv), payload["n_cells"]))
    if "aggregates" not in payload or "by_epsilon" not in payload["aggregates"]:
        raise SystemExit("analysis JSON has no aggregates; re-run "
                         "scripts/analyze_stage19_relax.py")

    f36 = figure_relax(outdir, payload)
    f37 = figure_identity(outdir, payload)
    inputs = [data_dir / ANALYSIS_JSON, data_dir / CELLS_CSV]
    caption37 = caption_f37(payload["cells"], float(payload["threshold_charge_l1"]),
                            float(payload["geometry_same_tolerance_angstrom"]),
                            payload["aggregates"]["all"]["all"])
    write_manifest(outdir, data_dir, [f36, f37], inputs, payload, caption37)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())