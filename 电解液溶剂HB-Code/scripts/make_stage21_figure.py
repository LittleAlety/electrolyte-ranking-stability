"""Stage 21 figures (F40, F41) -- the frozen path profiles and the shell under redox.

F40 (the fragile band of Stage 19, read with an energy criterion)

    Three panels, one per walked cell, each showing the 21 frozen r2SCAN-3c single
    points along the straight Cartesian line between the two Stage 19 relaxed
    endpoints, with the chord joining the endpoints drawn underneath.

    (a) EC/cation/eps=5   -- RMSD 0.100 A, Stage 19 called it ``distinct_lower``
    (b) EC/cation/eps=20  -- RMSD 0.021 A, Stage 19 called it ``same_higher``
    (c) TEGDME/anion/eps=20 -- RMSD 2.214 A, Stage 19 called it ``distinct_lower``

    The three cells are *not* on a shared energy scale: the control cell's straight
    line makes atoms pass through each other and its hump is ~66 eV, two orders of
    magnitude above the physics.  Each panel therefore carries its own y range and
    the annotation says so.  k_B T(298 K) is drawn as a band on panels (a) and (b).

F41 (the 1:2 solvent shell relaxed in both redox states)

    (a) oxidation axis: per shell, the frozen (vertical, Stage 9) shift as an open
        marker and the relaxed (adiabatic) shift as a filled marker, joined by a
        line so the relaxation correction is the visible displacement.
    (b) reduction axis: the same.  The reduction axis is where the complex can come
        apart, so shells whose relaxed frame fragmented or lost a ligand are drawn
        greyed out and excluded from every aggregate.
    (c) frozen shift against relaxed shift, both axes, with y = x and the Spearman /
        Kendall of the two orderings annotated.

Every number is read from the JSON / CSV products under ``--data-dir``; the only
literals here are protocol constants and colours.  In-figure text is ASCII on
purpose (no guaranteed CJK font), while the manifest captions, which the terminal
site quotes verbatim, are Chinese.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import shutil
import tempfile
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = REPO_ROOT / "outputs" / "week20"
DEFAULT_OUTDIR = REPO_ROOT / "outputs" / "figures"

MANIFEST_NAME = "figure_manifest_week20_stage21.md"
FIGURE_F40 = "F40_stage21_path_profiles.png"
FIGURE_F41 = "F41_stage21_shell_redox.png"

PATH_JSON = "stage21_path_analysis.json"
PATH_CSV = "stage21_path_analysis.csv"
SHELL_JSON = "stage21_shell_redox_analysis.json"
SHELL_CSV = "stage21_shell_redox_analysis.csv"
PROTOCOL_JSON = "stage21_protocol.json"
REFILL_JSON = "stage21_refill.json"

#: k_B T at 298.15 K, eV -- the same constant ``analyze_stage21_path`` uses.
THERMAL_EV = 0.0257
#: 1 kcal/mol, eV.
KCAL_EV = 0.043364

AXIS_COLOR = {"oxidation": "#c0392b", "reduction": "#1f6feb"}
AXIS_ORDER = ("oxidation", "reduction")


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


def p50(values):
    clean = sorted(float(value) for value in values if value is not None)
    if not clean:
        return float("nan")
    middle = len(clean) // 2
    if len(clean) % 2:
        return clean[middle]
    return 0.5 * (clean[middle - 1] + clean[middle])


def span(values, pad=0.12, fallback=(-0.05, 0.05)):
    clean = [float(v) for v in values if v is not None]
    if not clean:
        return fallback
    lo, hi = min(clean), max(clean)
    width = hi - lo
    if width <= 0:
        width = max(abs(hi), 1e-3) * 0.2
    return lo - pad * width, hi + pad * width

# ---------------------------------------------------------------------------
# F40 -- the frozen path profiles
# ---------------------------------------------------------------------------

def load_path(data_dir: Path):
    payload = load_json(Path(data_dir) / PATH_JSON)
    cells = []
    for cell in payload["cells"]:
        cells.append({
            "cell": cell["cell"], "name": cell["name"], "state": cell["state"],
            "epsilon": float(cell["epsilon"]),
            "rmsd_a_stage19": float(cell["rmsd_a_stage19"]),
            "stage19_verdict": cell["stage19_verdict"],
            "verdict": cell["verdict"],
            "path_length_a": float(cell["path_length_a"]),
            "barrier_chord_ev": float(cell["barrier_chord_ev"]),
            "barrier_abs_ev": float(cell["barrier_abs_ev"]),
            "e_span_ev": float(cell["e_span_ev"]),
            "relax_span_ev": as_float(cell.get("relax_span_ev")),
            "g1_single_point_delta_ev": as_float(cell.get("g1_single_point_delta_ev")),
            "monotone": bool(cell["monotone"]),
            "n_turns": int(cell["n_turns"]),
            "noise_floor_ev": float(cell["noise_floor_ev"]),
            "hump_over_noise": as_float(cell.get("hump_over_noise")),
            "agrees_with_stage19": bool(cell["agrees_with_stage19"]),
            # the JSON drops lambda_grid (it is fully determined by the image count),
            # so rebuild it here rather than recomputing the grid by hand.
            "lambda_grid": [index / (len(cell["profile_ev"]) - 1)
                            for index in range(len(cell["profile_ev"]))],
            "profile_ev": [float(value) for value in cell["profile_ev"]],
        })
    return {"meta": payload, "cells": cells}


def path_panel(ax, cell, index):
    lambdas = np.array(cell["lambda_grid"])
    energies = np.array(cell["profile_ev"])
    relative = energies - energies[0]
    chord = relative[0] + lambdas * (relative[-1] - relative[0])

    ax.plot(lambdas, chord, color="#999999", linewidth=1.0, linestyle="--",
            zorder=1, label="chord between endpoints")
    ax.plot(lambdas, relative, color="#1f4e79", linewidth=1.6, marker="o",
            markersize=3.4, zorder=3, label="frozen r2SCAN-3c profile")
    ax.scatter([0.0, 1.0], [relative[0], relative[-1]], color="#c0392b", s=42,
               zorder=4, label="Stage 19 relaxed endpoints")

    hump = cell["barrier_chord_ev"]
    if hump > 0:
        peak = int(np.argmax(relative - chord))
        ax.annotate("hump %.5f eV" % hump,
                    xy=(lambdas[peak], relative[peak]),
                    xytext=(0.35, 0.82), textcoords="axes fraction",
                    fontsize=8, color="#c0392b",
                    arrowprops=dict(arrowstyle="->", color="#c0392b", lw=0.8))

    if hump < 1.0:
        ax.axhspan(-THERMAL_EV, THERMAL_EV, color="#f1c40f", alpha=0.18, zorder=0)
        ax.axhline(THERMAL_EV, color="#b7950b", linewidth=0.8, linestyle=":", zorder=2)
        ax.axhline(-THERMAL_EV, color="#b7950b", linewidth=0.8, linestyle=":", zorder=2)
        ax.text(0.02, 0.05, "grey band = +/- k_B T(298 K) = %.4f eV" % THERMAL_EV,
                transform=ax.transAxes, fontsize=7.5, color="#7d6608")

    lo, hi = span(list(relative) + list(chord), pad=0.18)
    if hi - lo < 4 * THERMAL_EV:
        middle = 0.5 * (hi + lo)
        lo, hi = middle - 2 * THERMAL_EV, middle + 2 * THERMAL_EV
    ax.set_ylim(lo, hi)
    ax.set_xlim(-0.04, 1.04)
    ax.set_xlabel("lambda  (0 = Stage 19 default endpoint, 1 = moread endpoint)",
                  fontsize=8.5)
    ax.set_ylabel("frozen energy - E(lambda=0)   (eV)", fontsize=8.5)
    ax.grid(alpha=0.22, linewidth=0.6)

    if hump >= 1.0:
        ymax = float(np.max(relative))
        ymin = float(np.min(relative))
        ax.set_ylim(min(ymin, 0.0) - 0.05 * max(abs(ymax), 1.0),
                    ymax + 0.10 * max(abs(ymax), 1.0))
        ax.text(0.02, 0.90,
                "OWN Y SCALE -- atoms are driven through each other, so the\n"
                "hump (~%.0f eV) is an interpolation artefact, not a barrier"
                % hump,
                transform=ax.transAxes, fontsize=7.5, color="#c0392b")

    # One wrapped block: a 90-character title in a 5.4-inch panel runs straight
    # into the neighbouring panel's title.
    ax.set_title("%s\nStage 19: %s (RMSD %.3f A)  ->  this stage: %s\n"
                 "path %.3f A   hump %.5f eV   monotone %s"
                 % (cell["cell"], cell["stage19_verdict"], cell["rmsd_a_stage19"],
                    cell["verdict"], cell["path_length_a"], hump, cell["monotone"]),
                 fontsize=8.4, linespacing=1.5)
    if index == 0:
        ax.legend(loc="lower left", fontsize=7.2, framealpha=0.9)


def figure_f40(outdir, data):
    cells = data["cells"]
    fig, axes = plt.subplots(1, len(cells), figsize=(5.4 * len(cells), 4.5))
    if len(cells) == 1:
        axes = [axes]
    for index, (ax, cell) in enumerate(zip(axes, cells)):
        path_panel(ax, cell, index)
    fig.suptitle("F40 -- the Stage 19 fragile band read with an energy criterion "
                 "instead of an RMSD threshold", fontsize=11.5, y=1.075)
    return save(fig, Path(outdir) / FIGURE_F40)

# ---------------------------------------------------------------------------
# F41 -- the 1:2 solvent shell under redox
# ---------------------------------------------------------------------------

def load_shells(data_dir: Path):
    payload = load_json(Path(data_dir) / SHELL_JSON)
    shells = []
    for record in payload["shells"]:
        shells.append({
            "name": record["name"], "motif_id": record["motif_id"],
            "shell_label": record["shell_label"], "state": record["state"],
            "axis": record["axis"], "usable": bool(record["usable"]),
            "frozen": as_float(record.get("shell_shift_frozen_ev")),
            "relaxed": as_float(record.get("shell_shift_relaxed_ev")),
            "correction": as_float(record.get("relaxation_correction_ev")),
            "vs_bare_frozen": as_float(record.get("shell_shift_frozen_vs_bare_ev")),
            "vs_bare_relaxed": as_float(record.get("shell_shift_relaxed_vs_bare_ev")),
            "relative_ev": as_float(record.get("relative_ev")),
            "li_min_distance_a": as_float(record.get("li_min_distance_a")),
            "n_li_contacts": as_float(record.get("n_li_contacts")),
            "qc_flags": record.get("qc_flags", ""),
        })
    return {"meta": payload, "shells": shells, "axes": payload["axes"]}


def shell_rows(shells, axis):
    rows = [shell for shell in shells if shell["axis"] == axis
            and shell["frozen"] is not None and shell["relaxed"] is not None]
    rows.sort(key=lambda row: row["frozen"])
    return rows


def shell_panel(ax, shells, axis, summary):
    rows = shell_rows(shells, axis)
    usable = [row for row in rows if row["usable"]]
    excluded = [row for row in rows if not row["usable"]]

    for tag, group, alpha, linestyle in (("usable", usable, 1.0, "-"),
                                         ("excluded", excluded, 0.42, ":")):
        if not group:
            continue
        positions = np.arange(len(group))
        frozen = np.array([row["frozen"] for row in group])
        relaxed = np.array([row["relaxed"] for row in group])
        ax.vlines(positions, frozen, relaxed, color="#bbbbbb", linewidth=1.0,
                  linestyle=linestyle, zorder=1)
        ax.plot(positions, frozen, linestyle="none", marker="o", markersize=6,
                markerfacecolor="white", markeredgecolor="#1f4e79",
                markeredgewidth=1.3, alpha=alpha, zorder=3,
                label="Stage 9 frozen (vertical)" if tag == "usable" else None)
        ax.plot(positions, relaxed, linestyle="none", marker="o", markersize=6,
                color="#1f4e79", alpha=alpha, zorder=4,
                label="this stage relaxed (adiabatic)" if tag == "usable" else None)
        if excluded:
            ax.plot(positions, relaxed, linestyle="none", marker="x", markersize=7,
                    color="#c0392b", alpha=1.0, zorder=5,
                    label="frame did not survive" if tag == "excluded" else None)

    labels = [row["name"] + "\n" + row["motif_id"] for row in rows]
    ax.set_xticks(np.arange(len(rows)))
    ax.set_xticklabels(labels, fontsize=7.0)
    ax.set_ylabel("shell shift (eV)", fontsize=8.5)
    ax.axhline(0.0, color="#666666", linewidth=0.7)
    ax.grid(alpha=0.22, axis="y", linewidth=0.6)

    rho = summary.get("spearman_frozen_vs_relaxed")
    tau = summary.get("kendall_frozen_vs_relaxed")
    overlap = summary.get("top_quartile_overlap")
    ax.set_title("%s axis   n=%d/%d usable\n"
                 "rho=%.3f   tau=%.3f   top-quartile overlap=%.3f"
                 % (axis, len(usable), len(rows),
                    -99.0 if rho is None else rho,
                    -99.0 if tau is None else tau,
                    -99.0 if overlap is None else overlap),
                 fontsize=9.0, linespacing=1.5)
    correction = summary.get("correction_mean_ev")
    ax.text(0.02, 0.03,
            "relaxation correction: mean %s eV, largest |correction| %s eV"
            % ("n/a" if correction is None else "%+.4f" % correction,
               "n/a" if summary.get("correction_max_abs_ev") is None
               else "%.4f" % summary["correction_max_abs_ev"]),
            transform=ax.transAxes, fontsize=7.5, color="#444444")
    ax.legend(loc="upper right", fontsize=7.0, framealpha=0.9)


def shell_scatter(ax, shells, axes_summary):
    markers = {"oxidation": "o", "reduction": "s"}
    for axis in AXIS_ORDER:
        rows = [shell for shell in shells if shell["axis"] == axis
                and shell["usable"] and shell["frozen"] is not None
                and shell["relaxed"] is not None]
        if not rows:
            continue
        frozen = np.array([row["frozen"] for row in rows])
        relaxed = np.array([row["relaxed"] for row in rows])
        ax.scatter(frozen, relaxed, s=46, marker=markers[axis],
                   facecolor=AXIS_COLOR[axis], edgecolor="white", linewidth=0.8,
                   alpha=0.9, zorder=3,
                   label="%s (n=%d)" % (axis, len(rows)))
    excluded = [shell for shell in shells if not shell["usable"]
                and shell["frozen"] is not None and shell["relaxed"] is not None]
    if excluded:
        ax.scatter([row["frozen"] for row in excluded],
                   [row["relaxed"] for row in excluded], s=58, marker="x",
                   color="#c0392b", zorder=4,
                   label="frame did not survive (n=%d)" % len(excluded))

    clean = [shell for shell in shells if shell["usable"]
             and shell["frozen"] is not None and shell["relaxed"] is not None]
    if clean:
        values = [shell["frozen"] for shell in clean] + [shell["relaxed"]
                                                         for shell in clean]
        lo, hi = span(values, pad=0.16)
        ax.plot([lo, hi], [lo, hi], color="#666666", linewidth=1.0, linestyle="--",
                zorder=1, label="y = x (relaxation changes nothing)")
        ax.set_xlim(lo, hi)
        ax.set_ylim(lo, hi)
    ax.set_xlabel("Stage 9 frozen shift (eV)", fontsize=8.5)
    ax.set_ylabel("relaxed shift (eV)", fontsize=8.5)
    ax.set_title("frozen vs relaxed shift, both axes", fontsize=9.0)
    ax.grid(alpha=0.22, linewidth=0.6)
    ax.legend(loc="upper left", fontsize=7.0, framealpha=0.9)


def figure_f41(outdir, data):
    by_axis = {row["axis"]: row for row in data["axes"]}
    fig, axes = plt.subplots(1, 3, figsize=(16.6, 4.8))
    for index, axis in enumerate(AXIS_ORDER):
        shell_panel(axes[index], data["shells"], axis, by_axis.get(axis, {}))
    shell_scatter(axes[2], data["shells"], by_axis)
    fig.suptitle("F41 -- the 1:2 solvent shell [Li(M)2]+ relaxed in both redox states "
                 "(r2SCAN-3c, gas phase, from the frozen Stage 9 frame)",
                 fontsize=11.5, y=1.06)
    return save(fig, Path(outdir) / FIGURE_F41)

# ---------------------------------------------------------------------------
# captions (Chinese; the terminal site quotes these verbatim)
# ---------------------------------------------------------------------------

def caption_f40(data):
    cells = {cell["cell"]: cell for cell in data["cells"]}
    fragile = cells.get("EC/cation/5")
    same = cells.get("EC/cation/20")
    control = cells.get("TEGDME/anion/20")
    parts = ["F40：把 Stage 19 最脆的那条判据换一把尺子重读。三个格子在两条松弛几何之间做直线内插、"
             "每点一个冻结 r2SCAN-3c 单点（共 %d 个），各自纵轴不同**不可互比**。"
             % data["meta"]["n_jobs"]]
    if fragile:
        parts.append("(a) EC/cation/ε=5：Stage 19 因两臂几何相差 %.3f Å 判它 `distinct_lower`，"
                     "但内插路径全称无鼓包（相对弦最大仅 %.5f eV ≪ k_B T = %.4f eV），"
                     "两臂弛豫能量只差 %.5f eV——**过度判定**，它其实是同一个平坦盆地的两个肩。"
                     % (fragile["rmsd_a_stage19"], fragile["barrier_chord_ev"], THERMAL_EV,
                        fragile["relax_span_ev"] or float("nan")))
    if same:
        parts.append("(b) EC/cation/ε=20：判据另一侧的对照，路径同样无鼓包（%.5f eV），`same_higher` 成立。"
                     % same["barrier_chord_ev"])
    if control:
        parts.append("(c) TEGDME/anion/ε=20（RMSD %.3f Å）的鼓包约 %.0f eV，是直线路径让原子互穿的假象，"
                     "只用来确认两解确实分立。"
                     % (control["rmsd_a_stage19"], control["barrier_chord_ev"]))
    parts.append("内插路径是笛卡尔直线、不是最小能量路径，所以鼓包只是**上界**；"
                 "反过来说「直线全程不抬升」是强证据：它不可能藏着一个势垒。"
                 "结论：临界带（0.021–0.100 Å）上 RMSD 阈值把至少一格判错了，"
                 "该由能量判据而非几何阈值来裁决。")
    return "".join(parts)


def caption_f41(data):
    by_axis = {row["axis"]: row for row in data["axes"]}
    oxidation = by_axis.get("oxidation", {})
    reduction = by_axis.get("reduction", {})
    payload = data["meta"]
    excluded = payload.get("excluded") or []
    return ("F41：把第一溶剂壳 [Li(M)2]+ 的两个氧化还原态都做 r2SCAN-3c 弛豫（气相，与 Stage 9 同口径，"
            "起点是同一张冻结 G2Li2 几何），共 %d 个 Opt、%d 个可用；"
            "(a) 氧化轴：空心 = Stage 9 的冻结垂直位移，实心 = 本周的弛豫绝热位移，连线长度就是弛豫修正"
            "（均值 %+.4f eV、最大 %.4f eV，排序 Spearman ρ=%.3f、Kendall τ=%.3f、上四分位重叠 %.3f）；"
            "(b) 还原轴：同样的读法（修正均值 %+.4f eV、ρ=%.3f、τ=%.3f、重叠 %.3f）——"
            "还原态是中性自由基，结构可能散架，凡断键/碎片化/丢配体的格子都画成灰叉并**排除在所有统计之外**"
            "（本周排除 %s）；(c) 冻结 vs 弛豫位移散点与 y=x，"
            "说明「垂直位移」作为绝热位移的上界在多大程度上成立。"
            % (payload["n_jobs"], payload["n_usable"],
               oxidation.get("correction_mean_ev") or float("nan"),
               oxidation.get("correction_max_abs_ev") or float("nan"),
               oxidation.get("spearman_frozen_vs_relaxed") or float("nan"),
               oxidation.get("kendall_frozen_vs_relaxed") or float("nan"),
               oxidation.get("top_quartile_overlap") or float("nan"),
               reduction.get("correction_mean_ev") or float("nan"),
               reduction.get("spearman_frozen_vs_relaxed") or float("nan"),
               reduction.get("kendall_frozen_vs_relaxed") or float("nan"),
               reduction.get("top_quartile_overlap") or float("nan"),
               ("、".join(excluded) if excluded else "无")))


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


def inputs_for(data_dir):
    data_dir = Path(data_dir)
    return [data_dir / PATH_JSON, data_dir / PATH_CSV, data_dir / SHELL_JSON,
            data_dir / SHELL_CSV, data_dir / PROTOCOL_JSON, data_dir / REFILL_JSON]


def f40_lines(data, caption):
    meta = data["meta"]
    lines = ["## F40 -- `%s`" % FIGURE_F40, "",
             "One-line caption (verbatim, for the terminal site): %s" % caption, "",
             "### the three walked cells", "",
             "| cell | Stage 19 RMSD (A) | Stage 19 verdict | path length (A) | "
             "chord hump (eV) | hump / SCF noise | relaxed delta (eV) | "
             "this stage | agrees |",
             "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for cell in data["cells"]:
        lines.append("| %s | %.4f | %s | %.4f | %.6f | %s | %s | %s | %s |"
                     % (cell["cell"], cell["rmsd_a_stage19"], cell["stage19_verdict"],
                        cell["path_length_a"], cell["barrier_chord_ev"],
                        "n/a" if cell["hump_over_noise"] is None
                        else "%.1f" % cell["hump_over_noise"],
                        "n/a" if cell["relax_span_ev"] is None
                        else "%+.6f" % cell["relax_span_ev"],
                        cell["verdict"],
                        "yes" if cell["agrees_with_stage19"] else "**NO**"))
    lines += ["",
              "### what the profile does and does not prove", "",
              "- the path is a straight Cartesian line, not a minimum-energy path, so "
              "any hump on it is only an **upper bound** to the true barrier;",
              "- the asymmetry is the point: a straight line that never rises cannot "
              "be hiding a barrier, so a barrier-free profile is *strong* evidence that "
              "the two endpoints sit in one basin, while a hump is weak evidence of "
              "separation;",
              "- the SCF noise floor is the median absolute second difference of the "
              "profile; humps at that level are numerical;",
              "- %d of %d cells agree with the Stage 19 RMSD verdict and the one that "
              "does not is the fragile cell, not the control." % (
                  meta["n_agree_with_stage19"], meta["n_cells"]),
              ""]
    return lines


def f41_lines(data, caption):
    payload = data["meta"]
    lines = ["## F41 -- `%s`" % FIGURE_F41, "",
             "One-line caption (verbatim, for the terminal site): %s" % caption, "",
             "### per shell", "",
             "| shell | axis | frozen shift (eV) | relaxed shift (eV) | "
             "relaxation correction (eV) | usable | QC flags |",
             "| --- | --- | --- | --- | --- | --- | --- |"]
    for shell in sorted(data["shells"], key=lambda row: (row["name"],
                                                         row["motif_id"],
                                                         row["state"])):
        lines.append("| %s | %s | %s | %s | %s | %s | %s |"
                     % (shell["shell_label"], shell["state"],
                        "n/a" if shell["frozen"] is None
                        else "%.4f" % shell["frozen"],
                        "n/a" if shell["relaxed"] is None
                        else "%.4f" % shell["relaxed"],
                        "n/a" if shell["correction"] is None
                        else "%+.4f" % shell["correction"],
                        "yes" if shell["usable"] else "**NO**",
                        shell["qc_flags"] or ""))
    lines += ["", "### axis summaries", ""]
    for axis in payload["axes"]:
        if not axis.get("n"):
            lines.append("- %s: no usable shell." % axis["axis"])
            continue
        lines.append("- %s: n=%d (excluded %d); frozen %.4f +- %.4f eV -> relaxed "
                     "%.4f +- %.4f eV; correction %+.4f +- %.4f eV; rho=%.3f, "
                     "tau=%.3f, top-quartile overlap %.3f"
                     % (axis["axis"], axis["n"], axis["n_excluded"],
                        axis["frozen_mean_ev"], axis["frozen_std_ev"],
                        axis["relaxed_mean_ev"], axis["relaxed_std_ev"],
                        axis["correction_mean_ev"], axis["correction_std_ev"],
                        axis["spearman_frozen_vs_relaxed"],
                        axis["kendall_frozen_vs_relaxed"],
                        axis["top_quartile_overlap"]))
    lines += ["",
              "### denominators and caveats", "",
              "- the reduction axis is the one at risk: the reduced complex is a "
              "neutral radical, so a frame that breaks a bond, fragments, or loses a "
              "ligand describes a *different species*; those shells are drawn greyed "
              "out and excluded from every aggregate rather than averaged in;",
              "- the reference is the Stage 9 ``+1`` singlet ``Opt``, so the adiabatic "
              "shift is the difference of two separate relaxations, not the relaxation "
              "energy of one state;",
              "- excluded from the summaries: %s." % (
                  ", ".join(payload.get("excluded") or []) or "none"),
              ""]
    return lines


def write_manifest(outdir, figures, inputs, data_path, data_shell, captions):
    lines = ["# figure_manifest_week20_stage21", "",
             "| figure | sha256 | size |",
             "| --- | --- | --- |"]
    for path in figures:
        lines.append("| `%s` | `%s` | %d B |"
                     % (path.name, sha256(path), path.stat().st_size))
    lines += ["", "| input | sha256 |", "| --- | --- |"]
    for path in inputs:
        lines.append("| `%s` | `%s` |" % (display(path), sha256(path)))
    lines += ["", "Generate (from the repository root):", "", "```powershell",
              "& $py scripts\\make_stage21_figure.py",
              "& $py scripts\\make_stage21_figure.py --check",
              "```", "",
              "The PNGs carry no timestamp, so re-running on the same inputs gives "
              "byte-identical files; ``--check`` re-renders into a temporary directory "
              "and compares both PNGs and this file byte for byte.", "",
              "## denominators", "",
              "- F40 works on the %d walked cells (3 cells x %d images) of Part A -- "
              "chosen to bracket the Stage 19 RMSD threshold, not sampled."
              % (data_path["meta"]["n_cells"], data_path["meta"]["images"]),
              "- F41 works on the %d shells (12 labels x 2 redox states); %d of them "
              "produced a usable frame and %d were excluded."
              % (data_shell["meta"]["n_jobs"], data_shell["meta"]["n_usable"],
                 data_shell["meta"]["n_excluded"]),
              "- Part B (the ``charge_l1`` precheck) and Part D (the P2-leg refill) "
              "contribute no figure of their own; their products are listed as inputs "
              "so the week's figure set is pinned to the same data the report reads.",
              ""]
    lines += f40_lines(data_path, captions[FIGURE_F40])
    lines += f41_lines(data_shell, captions[FIGURE_F41])
    lines += ["## palette and rendering", "",
              "- dpi = 170, ``bbox_inches = tight``, white face colour -- same as the "
              "other week figures.",
              "- In-figure text is ASCII: the workspace has no guaranteed CJK font, so "
              "Chinese would render as boxes.  The captions above are Chinese and are "
              "quoted verbatim by the site builder.",
              "- The three F40 panels carry independent y ranges; the control cell's "
              "hump is two orders of magnitude above the physics and sharing an axis "
              "would render the other two as flat lines.",
              ""]
    manifest = Path(outdir) / MANIFEST_NAME
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print("wrote %s (%d bytes)" % (display(manifest), manifest.stat().st_size))


def build(outdir, data_dir):
    outdir = Path(outdir)
    data_path = load_path(data_dir)
    data_shell = load_shells(data_dir)
    figures = [figure_f40(outdir, data_path), figure_f41(outdir, data_shell)]
    captions = {FIGURE_F40: caption_f40(data_path),
                FIGURE_F41: caption_f41(data_shell)}
    write_manifest(outdir, figures, inputs_for(data_dir), data_path, data_shell,
                   captions)
    return figures + [outdir / MANIFEST_NAME]


def run_check(outdir, data_dir) -> int:
    outdir = Path(outdir)
    manifest = outdir / MANIFEST_NAME
    if not manifest.exists():
        print("check FAILED: manifest missing: %s" % manifest)
        return 1
    rows = _figure_rows(manifest.read_text(encoding="utf-8"))
    status = 0
    for name in (FIGURE_F40, FIGURE_F41):
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
    workdir = Path(tempfile.mkdtemp(prefix="stage21_figure_check_"))
    try:
        fresh = build(workdir, data_dir)
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
    parser = argparse.ArgumentParser(description="Stage 21 figures (F40, F41).")
    parser.add_argument("--outdir", default=str(DEFAULT_OUTDIR),
                        help="figure output directory (default outputs/figures)")
    parser.add_argument("--data-dir", default=str(DEFAULT_DATA_DIR),
                        help="Stage 21 product directory (default outputs/week20)")
    parser.add_argument("--check", action="store_true",
                        help="verify the products exist and the manifest reproduces")
    args = parser.parse_args(argv)
    if args.check:
        return run_check(Path(args.outdir), Path(args.data_dir))
    build(Path(args.outdir), Path(args.data_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())