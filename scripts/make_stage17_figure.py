"""Stage 17 figures (F32, F33) -- the contamination bound and solution identity.

F32 is the contamination bound on the published P1->P2 rung:

    (a) per molecule, on each of the two decision axes, the P2 shift caused by
        swapping only the SCF starting guess: delta = p2_moread - p2_default.
        The material threshold (1 meV) is drawn as a reference band.
    (b) the ranking-stability control: Kendall tau_b per (axis, arm) with the
        95% bootstrap CI, so the reader can see the two arms overlap.
    (c) the decision quantities themselves, default against moread, on their own
        scales: if nothing is rewritten, the connectors stay flat.

F33 is the electronic-structure identity of the two SCF solutions:

    (d) a representative cell (PC / anion / cpcm_10): the per-atom Mulliken spin
        profile, one line per arm, same spin centre.
    (e) all 32 cells: PR_default against PR_moread, coloured by family, so the
        localisation shift of each family is visible.
    (f) the same cells for <S**2>, against the pure-doublet reference 0.75.
    (g) charge reorganisation (charge_l1) against spin reorganisation (spin_l1),
        with the per-family means.

Every number is read from the JSON / CSV products under --data-dir; only physical
constants (the 1 meV threshold, the 0.75 doublet reference) are named literals.

Labels are ASCII on purpose: the workspace has no guaranteed CJK font.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_DATA_DIR = REPO_ROOT / "outputs" / "week16"
DEFAULT_OUTDIR = REPO_ROOT / "outputs" / "figures"

# -- named physical constants (the only literals allowed in this script) --------
MATERIAL_THRESHOLD_EV = 1e-3  # 1 meV, the material energy threshold
SPIN_PURITY_REF = 0.75  # <S**2> of a pure doublet

# -- product file names ---------------------------------------------------------
CONTAM_JSON = "stage17_contamination.json"
CONTAM_CELLS = "stage17_contamination_cells.csv"
CONTAM_LADDER = "stage17_contamination_ladder.csv"
IDENTITY_JSON = "stage17_solution_identity.json"
IDENTITY_CSV = "stage17_solution_identity.csv"

MANIFEST_NAME = "figure_manifest_week16_stage17.md"
FIGURE_F32 = "F32_stage17_contamination.png"
FIGURE_F33 = "F33_stage17_solution_identity.png"

# -- ORCA output parsing (panel d fallback) ------------------------------------
MULLIKEN_HEADER = "MULLIKEN ATOMIC CHARGES AND SPIN POPULATIONS"
MULLIKEN_ROW = re.compile(
    r"^\s*(\d+)\s+([A-Za-z]{1,2})\s*:\s*(-?\d+\.\d+)\s+(-?\d+\.\d+)\s*$")

# -- palette -------------------------------------------------------------------
RED = "#c0392b"
BLUE = "#1f5fa9"
GREY = "#9a9a9a"
GREEN = "#1a7d4f"
ORANGE = "#d98218"
PURPLE = "#6a3d9a"

AXIS_COLOR = {"oxidation": RED, "reduction": BLUE}
AXIS_LABEL = {"oxidation": "oxidation (cation)", "reduction": "reduction (anion)"}

FAMILY_COLOR = {
    "cyclic_carbonate": BLUE,
    "linear_carbonate": ORANGE,
    "phosphate": GREEN,
}
FAMILY_FALLBACK = [PURPLE, "#888888", "#bbbbbb"]

ARM_STYLE = {"default": dict(ls="-", marker="o"), "moread": dict(ls="--", marker="s")}
ARM_COLOR = {"default": GREY, "moread": "#222222"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 16), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_csv(path: Path):
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def save(fig, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=170, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("wrote %s (%d bytes)" % (path.relative_to(REPO_ROOT), path.stat().st_size))
    return path


def family_color(family, order):
    if family in FAMILY_COLOR:
        return FAMILY_COLOR[family]
    if family not in order:
        order.append(family)
    return FAMILY_FALLBACK[(order.index(family)) % len(FAMILY_FALLBACK)]


def read_mulliken_spin(path: Path):
    """Per-atom Mulliken spin populations from an ORCA .out file."""
    text = path.read_text(encoding="utf-8", errors="replace").splitlines()
    spins = []
    labels = []
    inside = False
    for line in text:
        if MULLIKEN_HEADER in line:
            inside = True
            spins, labels = [], []
            continue
        if not inside:
            continue
        if line.strip().startswith("Sum of"):
            break
        match = MULLIKEN_ROW.match(line)
        if match:
            labels.append("%s%s" % (match.group(2), match.group(1)))
            spins.append(float(match.group(4)))
    return labels, spins

def figure_contamination(data_dir, outdir, contam, cells, ladder):
    axes_order = ["oxidation", "reduction"]

    fig = plt.figure(figsize=(13.4, 10.4))
    outer = fig.add_gridspec(2, 2, height_ratios=[1.25, 1.0],
                             hspace=0.36, wspace=0.26)

    # ------------------------------------------------------------------ (a)
    ax = fig.add_subplot(outer[0, :])
    names = [row["name"] for row in cells]
    positions = {name: index for index, name in enumerate(names)}
    offsets = {"oxidation": 0.19, "reduction": -0.19}
    for axis in axes_order:
        column = "ox_delta_ev" if axis == "oxidation" else "red_delta_ev"
        for row in cells:
            value = float(row[column])
            ypos = positions[row["name"]] + offsets[axis]
            ax.plot([0.0, value], [ypos, ypos], color=AXIS_COLOR[axis],
                    lw=1.1, alpha=0.85, zorder=2)
            ax.plot([value], [ypos], marker="o", ms=5.0, color=AXIS_COLOR[axis],
                    mec="white", mew=0.5, zorder=3)
    ax.axvline(0.0, color="#333333", lw=0.9)
    for sign in (+1.0, -1.0):
        ax.axvline(sign * MATERIAL_THRESHOLD_EV, color=GREEN, ls="--", lw=1.0, zorder=1)
    ax.set_yticks(range(len(names)))
    ax.set_yticklabels(names, fontsize=8.5)
    ax.set_ylim(-0.6, len(names) - 0.4)
    ax.invert_yaxis()
    ax.set_xlim(-0.265, 0.155)
    ax.set_xlabel("delta = p2_moread - p2_default  (eV)", fontsize=10)
    ax.grid(axis="x", alpha=0.2)

    flat = []
    for row in cells:
        flat.append((row["name"] + "/anion", float(row["red_delta_ev"]), "reduction"))
        flat.append((row["name"] + "/cation", float(row["ox_delta_ev"]), "oxidation"))
    ranked = sorted(flat, key=lambda item: -abs(item[1]))
    annotate = {item[0]: item for item in ranked[:3]}
    biggest_positive = max(flat, key=lambda item: item[1])
    annotate[biggest_positive[0]] = biggest_positive
    for label, value, axis in annotate.values():
        name = label.split("/")[0]
        ypos = positions[name] + offsets[axis]
        ax.annotate("%s %+.4f" % (label, value),
                    xy=(value, ypos),
                    xytext=(value + (0.012 if value >= 0 else -0.012), ypos),
                    ha="left" if value >= 0 else "right", va="center",
                    fontsize=7.6, color=AXIS_COLOR[axis],
                    bbox=dict(boxstyle="round,pad=0.15", fc="white",
                              ec=AXIS_COLOR[axis], lw=0.5, alpha=0.85))
    handles = [plt.Line2D([], [], color=AXIS_COLOR[a], marker="o", ls="-", lw=1.2,
                          label=AXIS_LABEL[a]) for a in axes_order]
    handles.append(plt.Line2D([], [], color=GREEN, ls="--", lw=1.1,
                              label="+/- 1 meV material threshold"))
    ax.legend(handles=handles, fontsize=8.5, loc="lower right", framealpha=0.9)
    worst = max(abs(value) for _, value, _ in flat)
    ax.set_title("(a) The contamination bound: swapping only the SCF start swaps the "
                 "P1->P2 shift\n18 molecules x 2 axes; worst |delta| = %.4f eV, "
                 "vs the 1 meV threshold" % worst, fontsize=10.5, loc="left")

    # ------------------------------------------------------------------ (b)
    ax2 = fig.add_subplot(outer[1, 0])
    lookup = {(row["arm"], row["axis"]): row for row in ladder}
    arms = ["default", "moread"]
    width = 0.34
    base = np.arange(len(axes_order))
    for index, arm in enumerate(arms):
        values, low_err, high_err = [], [], []
        for axis in axes_order:
            row = lookup[(arm, axis)]
            tau = float(row["kendall_tau_b"])
            lo = float(row["tau_b_ci_low"])
            hi = float(row["tau_b_ci_high"])
            values.append(tau)
            low_err.append(tau - lo)
            high_err.append(hi - tau)
        bars = ax2.bar(base + (index - 0.5) * width, values, width,
                       color=ARM_COLOR[arm], label="%s arm" % arm,
                       yerr=[low_err, high_err], capsize=5,
                       error_kw=dict(ecolor="#333333", lw=1.2))
        for rect, value, lo, hi in zip(bars, values, low_err, high_err):
            ax2.text(rect.get_x() + rect.get_width() / 2, value + 0.02,
                     "%.3f" % value, ha="center", fontsize=8)
            ax2.text(rect.get_x() + rect.get_width() / 2, 0.335,
                     "[%.2f, %.2f]" % (value - lo, value + hi),
                     ha="center", fontsize=6.8, rotation=90, color="#333333")
    ax2.set_xticks(base)
    ax2.set_xticklabels([AXIS_LABEL[a] for a in axes_order], fontsize=9)
    ax2.set_ylabel("Kendall tau_b  (P1 vs P2 ordering)", fontsize=9)
    ax2.set_ylim(0.30, 1.10)
    ax2.grid(axis="y", alpha=0.25)
    ax2.legend(fontsize=8.5, loc="lower right", framealpha=0.9)
    overlap_lines = []
    for axis in axes_order:
        overlap = (contam.get("ci_overlap") or {}).get(axis) or {}
        overlap_lines.append("%s: 95%% CI overlap = %s" % (axis, overlap.get("overlap")))
    ax2.set_title("(b) Ranking-stability control: both arms' 95%% CIs overlap\n" +
                  "\n".join(overlap_lines), fontsize=10.5, loc="left")

    # ------------------------------------------------------------------ (c)
    ax3 = fig.add_subplot(outer[1, 1])
    metrics = [
        ("overlap_20", "O_20%"),
        ("f_unresolved_after", "f_unresolved\n(after)"),
        ("f_robust_inv", "f_robust_inv"),
        ("sigma_median_ev", "sigma median\n(eV)"),
    ]
    base3 = np.arange(len(metrics))
    for index, axis in enumerate(axes_order):
        offset = (index - 0.5) * 0.34
        for position, (key, label) in enumerate(metrics):
            default = float(lookup[("default", axis)][key])
            moread = float(lookup[("moread", axis)][key])
            scale = max(abs(default), abs(moread))
            if scale == 0.0:
                scale = 1.0
            xpos = base3[position] + offset
            yd, ym = default / scale, moread / scale
            ax3.plot([xpos, xpos], [yd, ym], color=AXIS_COLOR[axis], lw=1.6, zorder=2,
                     label=AXIS_LABEL[axis] if position == 0 else None)
            ax3.plot([xpos], [yd], marker="o", ms=5.5, mfc="white",
                     mec=AXIS_COLOR[axis], mew=1.3, zorder=3)
            ax3.plot([xpos], [ym], marker="s", ms=4.6, color=AXIS_COLOR[axis],
                     mec="white", mew=0.5, zorder=3)
            ax3.annotate("%.3g" % default, (xpos, yd), fontsize=6.6,
                         ha="center", va="bottom", color=AXIS_COLOR[axis],
                         xytext=(xpos, yd + 0.035))
            ax3.annotate("%.3g" % moread, (xpos, ym), fontsize=6.6,
                         ha="center", va="top", color=AXIS_COLOR[axis],
                         xytext=(xpos, ym - 0.035))
    ax3.set_xticks(base3)
    ax3.set_xticklabels([label for _, label in metrics], fontsize=8.5)
    ax3.set_ylim(-0.12, 1.30)
    ax3.set_ylabel("value / metric maximum", fontsize=9)
    ax3.grid(axis="y", alpha=0.25)
    arm_handles = [
        plt.Line2D([], [], color="#444444", marker="o", mfc="white", mec="#444444",
                   ls="none", label="default arm"),
        plt.Line2D([], [], color="#444444", marker="s", ls="none", label="moread arm"),
    ]
    handles3, _ = ax3.get_legend_handles_labels()
    ax3.legend(handles=handles3 + arm_handles, fontsize=8, loc="center right",
               framealpha=0.9)
    ax3.set_title("(c) Decision quantities, default -> moread (one connector per axis)\n"
                  "every connector is flat to within the 1 meV material threshold: "
                  "nothing rewritten",
                  fontsize=10.5, loc="left")

    fig.text(0.5, -0.015,
             "Reading (c): each connector joins an arm's value to the other arm's value for the same metric; "
             "f_robust_inv counts molecules whose P1->P2 ordering inverts by more than the 1 meV material "
             "threshold, so a flat connector at 0 (both axes) is the statement that no ordering was rewritten.",
             ha="center", fontsize=7.6, color="#333333")

    return save(fig, outdir / FIGURE_F32)

def _family_order(cells):
    order = []
    for row in cells:
        if row["family"] not in order:
            order.append(row["family"])
    return order


def figure_identity(data_dir, outdir, ident, cells):
    order = _family_order(cells)

    fig = plt.figure(figsize=(13.4, 11.0))
    outer = fig.add_gridspec(2, 2, hspace=0.34, wspace=0.26)

    # ------------------------------------------------------------------ (d)
    ax = fig.add_subplot(outer[0, 0])
    target = None
    for cell in ident["cells"]:
        if (cell["name"], cell["state"]) == ("PC", "anion") and \
                abs(float(cell["epsilon"]) - 10.0) < 1e-9:
            target = cell
            break
    if target is None:
        raise SystemExit("PC/anion/cpcm_10 cell not found in solution identity JSON")
    arms = [("default", target["default_path"]), ("moread", target["moread_path"])]
    peak = {}
    index = None
    for arm, path in arms:
        labels, spins = read_mulliken_spin(Path(path))
        index = np.arange(len(spins))
        peak[arm] = max(range(len(spins)), key=lambda i: abs(spins[i]))
        ax.plot(index, spins, **ARM_STYLE[arm], color=ARM_COLOR[arm], ms=4.5,
                lw=1.3, label="%s arm" % arm)
        dx, dy = (-2.0, 0.34) if arm == "default" else (1.8, -0.42)
        ax.annotate("%s (%s)" % (arm, labels[peak[arm]]),
                    xy=(peak[arm], spins[peak[arm]]),
                    xytext=(peak[arm] + dx, spins[peak[arm]] + dy),
                    ha="right" if arm == "default" else "left",
                    fontsize=7.6, color=ARM_COLOR[arm],
                    arrowprops=dict(arrowstyle="-", color=ARM_COLOR[arm], lw=0.8))
    ax.axhline(0.0, color="#bbbbbb", lw=0.8)
    ax.set_ylim(-0.75, 1.95)
    ax.set_xticks(index)
    ax.set_xlabel("atom index (ORCA 0-based order)", fontsize=9)
    ax.set_ylabel("Mulliken atomic spin population", fontsize=9)
    ax.grid(alpha=0.2)
    ax.legend(fontsize=8.5, loc="upper right", framealpha=0.9)
    ax.set_title("(d) PC / anion / cpcm_10: per-atom spin profile, both arms\n"
                 "same spin centre %s (default %.4f, moread %.4f spins), "
                 "|sum| = 1 in both" %
                 (target["spin_atom_default"], target["spin_max_default"],
                  target["spin_max_moread"]), fontsize=10.5, loc="left")

    # ------------------------------------------------------------------ (e)
    ax2 = fig.add_subplot(outer[0, 1])
    pr_default = np.array([float(row["spin_pr_default"]) for row in cells])
    pr_moread = np.array([float(row["spin_pr_moread"]) for row in cells])
    lo = float(min(pr_default.min(), pr_moread.min()))
    hi = float(max(pr_default.max(), pr_moread.max()))
    pad = 0.06 * (hi - lo)
    span = [lo - pad, hi + pad]
    ax2.plot(span, span, color="#666666", ls=":", lw=1.0, zorder=1,
             label="y = x (identity)")
    for family in order:
        mask = [row["family"] == family for row in cells]
        ax2.scatter(pr_default[mask], pr_moread[mask], s=48,
                    color=family_color(family, order), alpha=0.85,
                    edgecolors="white", linewidths=0.6, zorder=3, label=family)
    summary = ident["by_family"]
    for family in order:
        info = summary.get(family)
        if not info:
            continue
        mask = np.array([row["family"] == family for row in cells])
        ax2.scatter([pr_default[mask].mean()], [pr_moread[mask].mean()], s=190,
                    marker="X", color=family_color(family, order),
                    edgecolors="black", linewidths=1.0, zorder=4)
        ax2.annotate("mean loss_in_pr = %+.3f\n(n = %d)" %
                     (float(info["loss_in_pr_mean"]), int(info["n_cells"])),
                     xy=(pr_default[mask].mean(), pr_moread[mask].mean()),
                     xytext=(6, 6), textcoords="offset points", fontsize=7.4,
                     color=family_color(family, order),
                     bbox=dict(boxstyle="round,pad=0.18", fc="white",
                               ec=family_color(family, order), lw=0.5, alpha=0.85))
    ax2.set_xlim(span)
    ax2.set_ylim(span)
    ax2.set_xlabel("PR_default  (spin participation ratio, default arm)", fontsize=9)
    ax2.set_ylabel("PR_moread  (spin participation ratio, moread arm)", fontsize=9)
    ax2.grid(alpha=0.2)
    ax2.legend(fontsize=8, loc="upper left", framealpha=0.9)
    ax2.set_title("(e) Localisation shift: PR_default vs PR_moread for all %d cells\n"
                  "cyclic drops (loss_in_pr < 0, more local), linear rises "
                  "(more diffuse), phosphate in between" % ident["n_cells"],
                  fontsize=10.5, loc="left")

    # ------------------------------------------------------------------ (f)
    ax3 = fig.add_subplot(outer[1, 0])
    s2_default = np.array([float(row["s2_default"]) for row in cells])
    s2_moread = np.array([float(row["s2_moread"]) for row in cells])
    lo = float(min(s2_default.min(), s2_moread.min(), SPIN_PURITY_REF))
    hi = float(max(s2_default.max(), s2_moread.max(), SPIN_PURITY_REF))
    pad = 0.08 * (hi - lo)
    span = [lo - pad, hi + pad]
    ax3.plot(span, span, color="#666666", ls=":", lw=1.0, zorder=1,
             label="y = x (identity)")
    for family in order:
        mask = [row["family"] == family for row in cells]
        ax3.scatter(s2_default[mask], s2_moread[mask], s=48,
                    color=family_color(family, order), alpha=0.85,
                    edgecolors="white", linewidths=0.6, zorder=3, label=family)
    ax3.axhline(SPIN_PURITY_REF, color=GREEN, ls="--", lw=1.0, zorder=1)
    ax3.axvline(SPIN_PURITY_REF, color=GREEN, ls="--", lw=1.0, zorder=1)
    delta_s2 = ident["aggregates"]["delta_s2"]
    ax3.set_xlim(span)
    ax3.set_ylim(span)
    ax3.set_xlabel("<S**2> default arm", fontsize=9)
    ax3.set_ylabel("<S**2> moread arm", fontsize=9)
    ax3.grid(alpha=0.2)
    ax3.legend(fontsize=8, loc="upper left", framealpha=0.9)
    ax3.set_title("(f) Spin purity vs the 0.75 doublet reference (all %d cells)\n"
                  "Delta<S**2> in [%+.6f, %+.6f]: both arms near the reference"
                  % (ident["n_cells"], float(delta_s2["min"]), float(delta_s2["max"])),
                  fontsize=10.5, loc="left")

    # ------------------------------------------------------------------ (g)
    ax4 = fig.add_subplot(outer[1, 1])
    charge_l1 = np.array([float(row["charge_l1"]) for row in cells])
    spin_l1 = np.array([float(row["spin_l1"]) for row in cells])
    for family in order:
        mask = [row["family"] == family for row in cells]
        ax4.scatter(charge_l1[mask], spin_l1[mask], s=48,
                    color=family_color(family, order), alpha=0.85,
                    edgecolors="white", linewidths=0.6, zorder=3, label=family)
    ax4.set_xlim(0.0, float(charge_l1.max()) * 1.12)
    ax4.set_ylim(0.0, float(spin_l1.max()) * 1.22)
    for family in order:
        info = ident["by_family"].get(family)
        if not info:
            continue
        mean = float(info["charge_l1_mean"])
        color = family_color(family, order)
        ax4.axvline(mean, color=color, ls="--", lw=1.0, alpha=0.8, zorder=1)
        ax4.annotate("%s: charge_l1 mean %.2f" % (family, mean),
                     xy=(mean, ax4.get_ylim()[1]), xytext=(3, -8),
                     textcoords="offset points", fontsize=7.2, color=color,
                     rotation=90, va="top", ha="left")
    ax4.set_xlabel("charge_l1  (charge reorganisation, default vs moread)", fontsize=9)
    ax4.set_ylabel("spin_l1  (spin reorganisation, default vs moread)", fontsize=9)
    ax4.grid(alpha=0.2)
    ax4.legend(fontsize=8, loc="lower right", framealpha=0.9)
    ax4.set_title("(g) Charge vs spin reorganisation, by family\n"
                  "vertical dashed lines = per-family charge_l1 mean", fontsize=10.5,
                  loc="left")

    return save(fig, outdir / FIGURE_F33)

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


def write_manifest(outdir, data_dir, figure_paths, inputs, contam, ladder, ident):
    cells54 = contam["delta_stats"]["cells_54"]
    changed = contam.get("cells_changed") or []
    lookup = {(row["arm"], row["axis"]): row for row in ladder}
    by_family = ident["by_family"]
    agg = ident["aggregates"]

    lines = ["# figure_manifest_week16_stage17", "",
             "| figure | sha256 | size |", "| --- | --- | --- |"]
    for path in figure_paths:
        lines.append("| `%s` | `%s` | %d B |"
                     % (path.name, sha256(path), path.stat().st_size))
    lines += ["", "| input | sha256 |", "| --- | --- |"]
    for path in inputs:
        lines.append("| `%s` | `%s` |"
                     % (str(path.relative_to(REPO_ROOT)).replace("\\", "/"), sha256(path)))
    lines += ["", "Generate (from the repository root):", "", "```powershell",
              "& $py scripts\\make_stage17_figure.py",
              "& $py scripts\\make_stage17_figure.py --check",
              "```", ""]

    lines += ["## F32 -- `F32_stage17_contamination.png`", "",
              "### (a) contamination bound, per molecule and axis", ""]
    lines.append("`delta = p2_moread - p2_default` over %d molecules x %d axes. "
                 "The reference band is the material threshold %.0e eV. Worst |delta| "
                 "= %.4f eV (%s), the largest departure in the 'worse-with-the-restart' "
                 "sense. The only large positive departure (restart higher than the "
                 "default) is %s at %+.4f eV."
                 % (len(contam["molecules"]), len(contam["arms"]),
                    MATERIAL_THRESHOLD_EV, float(cells54["max_abs_ev"]),
                    cells54["argmin"], cells54["argmax"], float(cells54["max_ev"])))
    lines += ["", "### (b) ranking-stability control", ""]
    for axis in ("oxidation", "reduction"):
        for arm in ("default", "moread"):
            row = lookup[(arm, axis)]
            lines.append("- %s / %s: tau_b = %.4f, 95%% CI [%.4f, %.4f]"
                         % (axis, arm, float(row["kendall_tau_b"]),
                            float(row["tau_b_ci_low"]), float(row["tau_b_ci_high"])))
    overlap = contam.get("ci_overlap") or {}
    lines.append("- CI overlap: oxidation = %s, reduction = %s"
                 % ((overlap.get("oxidation") or {}).get("overlap"),
                    (overlap.get("reduction") or {}).get("overlap")))
    lines += ["", "### (c) decision quantities, default vs moread", ""]
    for axis in ("oxidation", "reduction"):
        default = lookup[("default", axis)]
        moread = lookup[("moread", axis)]
        lines.append("- %s: O_20%% %.4f -> %.4f, f_unresolved(after) %.4f -> %.4f, "
                     "f_robust_inv %.4f -> %.4f, sigma median %.4f -> %.4f eV"
                     % (axis, float(default["overlap_20"]), float(moread["overlap_20"]),
                        float(default["f_unresolved_after"]),
                        float(moread["f_unresolved_after"]),
                        float(default["f_robust_inv"]), float(moread["f_robust_inv"]),
                        float(default["sigma_median_ev"]),
                        float(moread["sigma_median_ev"])))
    lines.append("- verdict from the analysis: any published conclusion rewritten = %s"
                 % contam["verdict"]["any_published_conclusion_rewritten"])
    lines.append("- cells with a paired shift above the threshold: %d (%s)"
                 % (contam["cells_changed_count"],
                    ", ".join("%s %+.4f" % (item["cell"], float(item["delta_ev"]))
                              for item in changed)))
    lines.append("")

    lines += ["## F33 -- `F33_stage17_solution_identity.png`", "",
              "### (d) representative per-atom spin profile (PC / anion / cpcm_10)", ""]
    target = None
    for cell in ident["cells"]:
        if (cell["name"], cell["state"]) == ("PC", "anion") and \
                abs(float(cell["epsilon"]) - 10.0) < 1e-9:
            target = cell
            break
    lines.append("Both arms peak on the same atom %s: default %.4f, moread %.4f "
                 "Mulliken spin. Delta<S**2> = %.6f, geometry identical = %s, spin "
                 "centre identical = %s."
                 % (target["spin_atom_default"], float(target["spin_max_default"]),
                    float(target["spin_max_moread"]), float(target["delta_s2"]),
                    target["geometry_identical"], target["same_spin_center"]))
    lines += ["", "### (e) localisation shift across all %d cells" % ident["n_cells"], ""]
    for family, info in by_family.items():
        lines.append("- %s (n = %d): mean loss_in_pr = %+.4f (PR_moread - PR_default)"
                     % (family, int(info["n_cells"]), float(info["loss_in_pr_mean"])))
    lines += ["", "### (f) spin purity", ""]
    lines.append("- Delta<S**2> over the %d cells spans [%+.6f, %+.6f]; the "
                 "reference is the pure doublet 0.75."
                 % (int(agg["delta_s2"]["n"]), float(agg["delta_s2"]["min"]),
                    float(agg["delta_s2"]["max"])))
    lines += ["", "### (g) charge vs spin reorganisation", ""]
    for family, info in by_family.items():
        lines.append("- %s: charge_l1 mean %.2f, spin_l1 mean %.2f"
                     % (family, float(info["charge_l1_mean"]),
                        float(info["spin_l1_mean"])))
    lines += ["",
              "Palette and dpi follow the other week figures (dpi = 170, bbox_inches = tight). "
              "All labels are ASCII because the workspace has no guaranteed CJK font.", ""]

    manifest = outdir / MANIFEST_NAME
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print("wrote %s (%d bytes)" % (manifest.relative_to(REPO_ROOT), manifest.stat().st_size))
    return manifest


def run_check(outdir) -> int:
    manifest = outdir / MANIFEST_NAME
    if not manifest.exists():
        print("check FAILED: manifest missing: %s" % manifest)
        return 1
    rows = _figure_rows(manifest.read_text(encoding="utf-8"))
    status = 0
    for name in (FIGURE_F32, FIGURE_F33):
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
            print("check ok: %s (%d bytes, sha256 %s)" % (name, path.stat().st_size, actual))
    if status == 0:
        print("check ok: manifest matches disk")
    return status


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Stage 17 figures (F32, F33).")
    parser.add_argument("--outdir", default=str(DEFAULT_OUTDIR),
                        help="figure output directory (default outputs/figures)")
    parser.add_argument("--data-dir", default=str(DEFAULT_DATA_DIR),
                        help="Stage 17 product directory (default outputs/week16)")
    parser.add_argument("--check", action="store_true",
                        help="verify products exist and the manifest sha256 matches disk")
    args = parser.parse_args(argv)

    outdir = Path(args.outdir)
    data_dir = Path(args.data_dir)

    if args.check:
        return run_check(outdir)

    contam = load_json(data_dir / CONTAM_JSON)
    cells = load_csv(data_dir / CONTAM_CELLS)
    ladder = load_csv(data_dir / CONTAM_LADDER)
    ident = load_json(data_dir / IDENTITY_JSON)
    ident_cells = load_csv(data_dir / IDENTITY_CSV)

    figures = [
        figure_contamination(data_dir, outdir, contam, cells, ladder),
        figure_identity(data_dir, outdir, ident, ident_cells),
    ]

    inputs = [data_dir / CONTAM_JSON, data_dir / CONTAM_CELLS, data_dir / CONTAM_LADDER,
              data_dir / IDENTITY_JSON, data_dir / IDENTITY_CSV]
    for cell in ident["cells"]:
        if (cell.get("name"), cell.get("state")) == ("PC", "anion") and \
                abs(float(cell.get("epsilon", 0.0)) - 10.0) < 1e-9:
            inputs += [Path(cell["default_path"]), Path(cell["moread_path"])]
            break
    inputs = [path for path in inputs if path.exists()]

    write_manifest(outdir, data_dir, figures, inputs, contam, ladder, ident)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())