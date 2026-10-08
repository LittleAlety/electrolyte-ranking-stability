#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""R14 close-out summary figure F56 -- what to read before quoting f_robust_inv = 0.

Round-2 external review, item 3: ``f_robust_inv = 0`` is the single number in this
repository that a reviewer is most likely to mis-read.  This figure is the visual
de-misreading device the review asked for.  It runs zero new electronic structure:
every number is read back from products already frozen in the repository.

    three-state counts      outputs/decision_state/decision_state_report.json
    f_unresolved(z) curve   outputs/decision_state/decision_state_report.json
    the 20-combination max  outputs/week9/stage10_ladder.json
    Gate 1 dual track       outputs/gate1/gate1_dual_track.json
    ordering tier evidence  outputs/week25/series_rel_ordering_check.json
    P1v vs P1a              outputs/phase2_p1a/p1v_vs_p1a.json
    C1 state identity       outputs/state_identity/state_identity_stratification.json

Panel A  three-state stacked bars (STABLE / UNRESOLVED / ROBUST_INVERSION)
Panel B  the f_unresolved(z) resolution curve, oxidation vs reduction
Panel C  Gate 1: Track A established, Track B NOT CLOSED and NOT CLOSABLE
Panel D  the annotation card: 0 robust inversions != 0 ranking instability

Usage
-----
    python scripts/analyze_r13_summary_figure.py            # write JSON + MD + PNG + manifest
    python scripts/analyze_r13_summary_figure.py --check    # recompute, compare bytes/pixels
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib import image as mpimg  # noqa: E402
from matplotlib.patches import FancyBboxPatch  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTDIR = REPO_ROOT / "outputs" / "figures"
FIGURE_NAME = "F56_r13_summary.png"
STAGE_DIR = REPO_ROOT / "outputs" / "week26"
JSON_PATH = STAGE_DIR / "figure_f56_stats.json"
MD_PATH = STAGE_DIR / "figure_f56_stats.md"
MANIFEST_PATH = STAGE_DIR / "F56_manifest.md"

DPI = 200
FIG_WIDTH_IN = 6.3
FIG_HEIGHT_IN = 7.0

INK = "#1f2933"
MUTED = "#61707d"
GRID = "#d6dde5"
FACE = "#ffffff"
OX_COLOR = "#2f6fb2"
RED_COLOR = "#c05621"
STABLE_COLOR = "#2f855a"
UNRESOLVED_COLOR = "#b7791f"
INVERSION_COLOR = "#c53030"
CARD_FACE = "#f5f7fa"
CARD_EDGE = "#c7d2dd"

INPUTS = {
    "decision_state": "outputs/decision_state/decision_state_report.json",
    "ladder": "outputs/week9/stage10_ladder.json",
    "gate1": "outputs/gate1/gate1_dual_track.json",
    "ordering": "outputs/week25/series_rel_ordering_check.json",
    "p1a": "outputs/phase2_p1a/p1v_vs_p1a.json",
    "state_identity": "outputs/state_identity/state_identity_stratification.json",
}

Z_GRID = [1.0, 1.645, 1.96, 2.576]
RUNGS = ["P0->P1v", "P1v->P2a", "P0->P2a"]
AXES = ["oxidation", "reduction"]
AXIS_COLOR = {"oxidation": OX_COLOR, "reduction": RED_COLOR}
AXIS_LABEL = {"oxidation": "氧化轴", "reduction": "还原轴"}
RUNG_STYLE = {"P0->P1v": "-", "P1v->P2a": "--", "P0->P2a": ":"}

DISCIPLINE = (
    "本图不跑任何新电子结构；所有数字均为已冻结产物的现算读出。"
    "robust inversion = 0 的含义是 evidence insufficient to resolve，不是 ranking stable；"
    "不得把本图读成「18 个溶剂的最终性能排名」。"
)


def read_json(rel: str) -> dict:
    path = REPO_ROOT / rel
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def sha256(path: Path) -> str:
    if not path.exists():
        return "n/a"
    return hashlib.sha256(path.read_bytes()).hexdigest()


def collect() -> dict:
    dec = read_json(INPUTS["decision_state"])
    ladder_doc = read_json(INPUTS["ladder"])
    g1 = read_json(INPUTS["gate1"])
    ordering = read_json(INPUTS["ordering"])
    p1a = read_json(INPUTS["p1a"])
    sid = read_json(INPUTS["state_identity"])

    three_state = []
    curves = []
    for rung in RUNGS:
        for axis in AXES:
            node = (dec.get("rungs", {}).get(rung, {}) or {}).get(axis) or {}
            if not node:
                continue
            three_state.append({
                "rung": rung,
                "axis": axis,
                "n": node.get("n"),
                "n_pairs": node.get("n_pairs"),
                "kendall_tau_b": node.get("kendall_tau_b"),
                "counts": node.get("decision_state_counts"),
                "fractions": node.get("decision_state_fractions"),
            })
            for model, key in (("P_cheap", "resolution_curve_p0"), ("P_target", "resolution_curve_p1")):
                rows = (node.get(key) or {}).get("rows") or []
                if rows:
                    curves.append({
                        "rung": rung,
                        "axis": axis,
                        "model": model,
                        "z": [row.get("z") for row in rows],
                        "f_unresolved": [row.get("f_unresolved") for row in rows],
                    })

    ladder = ladder_doc.get("ladder") or []
    worst = None
    robust_max = 0.0
    for entry in ladder:
        values = [entry.get("f_unresolved_before"), entry.get("f_unresolved_after")]
        values = [v for v in values if isinstance(v, (int, float))]
        if not values:
            continue
        local = max(values)
        if worst is None or local > worst["f_unresolved"]:
            worst = {"rung": entry.get("rung"), "axis": entry.get("axis"),
                     "f_unresolved": float(local)}
        if isinstance(entry.get("f_robust_inv"), (int, float)):
            robust_max = max(robust_max, float(entry["f_robust_inv"]))

    closability = ((g1.get("track_B") or {}).get("components") or {}).get("closability") or {}
    clos_ev = closability.get("evidence") or {}
    calibration = ((g1.get("track_B") or {}).get("components") or {}).get("absolute_calibration") or {}

    payload = {
        "title": "R14 收口汇总：三态判据 / 分辨率曲线 / Gate 1 定性",
        "definition": (
            "pair 级判据 resolved(i,j) <=> |dP_ij| >= max(z*sigma_ij, delta_m)；"
            "STABLE / UNRESOLVED / ROBUST_INVERSION 三态主口径 z = 1.0。"
        ),
        "z_grid": Z_GRID,
        "three_state": three_state,
        "curves": curves,
        "misread": {
            "n_combinations": len(ladder),
            "f_robust_inv_max": robust_max,
            "f_unresolved_max": worst["f_unresolved"] if worst else None,
            "f_unresolved_max_at": {"rung": worst["rung"], "axis": worst["axis"]} if worst else None,
            "statement": "0 robust inversions != 0 ranking instability",
        },
        "gate1": {
            "track_a": (g1.get("track_A") or {}).get("status"),
            "track_b": (g1.get("track_B") or {}).get("status"),
            "closability": g1.get("gate1_closability"),
            "tau_b": ordering.get("tau_b"),
            "min_tau_b": (ordering.get("criterion") or {}).get("min_tau_b"),
            "n_pairs": ordering.get("n_pairs"),
            "longest_series_k": clos_ev.get("longest_homologous_series_k"),
            "min_species": (closability.get("prereg_requirement") or {}).get("min_species_covering_core_set"),
            "est_rows": calibration.get("rows_total"),
            "upgraded_rows": calibration.get("upgraded"),
        },
        "p1a": {
            "n": p1a.get("n"),
            "kendall_tau_b": (p1a.get("ranking") or {}).get("kendall_tau_b"),
            "robust_inversion": (p1a.get("decision_state_counts") or {}).get("ROBUST_INVERSION"),
        },
        "state_identity": {
            "li_centered_or_mixed": (sid.get("label_counts_reduced") or {}).get("Li_centered_or_mixed_redox"),
            "molecule_centered": (sid.get("label_counts_reduced") or {}).get("molecule_centered_redox"),
            "reduction_rank_defined": (sid.get("reduction_molecule_centered") or {}).get("defined"),
        },
    }
    payload["counts"] = {
        "n_rung_axis": len(three_state),
        "n_curves": len(curves),
        "n_combinations": len(ladder),
        "n_robust_inversion": sum(
            int((row.get("counts") or {}).get("ROBUST_INVERSION") or 0) for row in three_state
        ),
    }
    return payload


def _card(ax, x, y, w, h, face=CARD_FACE, edge=CARD_EDGE):
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h, boxstyle="round,pad=0.012,rounding_size=0.02",
        linewidth=0.7, edgecolor=edge, facecolor=face, transform=ax.transAxes,
        clip_on=False,
    ))


def draw(payload: dict):
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
    plt.rcParams["font.family"] = "sans-serif"
    plt.rcParams["axes.unicode_minus"] = False

    fig = plt.figure(figsize=(FIG_WIDTH_IN, FIG_HEIGHT_IN), dpi=DPI, facecolor=FACE)
    grid = fig.add_gridspec(2, 2, left=0.135, right=0.975, top=0.905, bottom=0.065,
                            hspace=0.42, wspace=0.26)
    ax_a = fig.add_subplot(grid[0, 0])
    ax_b = fig.add_subplot(grid[0, 1])
    ax_c = fig.add_subplot(grid[1, 0])
    ax_d = fig.add_subplot(grid[1, 1])

    fig.text(0.012, 0.982, payload["title"], fontsize=8.0, color=INK,
             fontweight="bold", va="top", ha="left")
    fig.text(0.012, 0.959, payload["definition"], fontsize=5.0, color=MUTED,
             va="top", ha="left")

    rows = payload["three_state"]
    labels = ["%s\n%s" % (row["rung"].replace("->", "\u2192"), AXIS_LABEL[row["axis"]]) for row in rows]

    # ----------------------------------------------------------- Panel A ----
    ypos = np.arange(len(rows))[::-1]
    left = np.zeros(len(rows))
    for key, color, name in (("STABLE", STABLE_COLOR, "STABLE"),
                             ("UNRESOLVED", UNRESOLVED_COLOR, "UNRESOLVED"),
                             ("ROBUST_INVERSION", INVERSION_COLOR, "ROBUST_INVERSION")):
        widths = np.array([float((row.get("counts") or {}).get(key) or 0) for row in rows])
        ax_a.barh(ypos, widths, left=left, height=0.62, color=color, edgecolor=FACE,
                  linewidth=0.5, label=name)
        for y, w, lo in zip(ypos, widths, left):
            if w > 14:
                ax_a.text(lo + w / 2.0, y, "%d" % int(w), ha="center", va="center",
                          fontsize=4.6, color="white")
        left = left + widths
    ax_a.set_yticks(ypos)
    ax_a.set_yticklabels(labels, fontsize=5.0, color=INK, linespacing=1.3)
    ax_a.set_xlim(0, max(left) * 1.30 if len(left) else 1)
    ax_a.set_xlabel("pair 计数（z = 1.0）", fontsize=5.8, color=INK)
    ax_a.set_title("(a) 三态计数：0 稳健翻转 = 不可判定主导", fontsize=6.0, loc="left", color=INK)
    ax_a.legend(fontsize=4.6, frameon=False, loc="center right", handlelength=1.1,
                labelspacing=0.35, borderpad=0.2)
    ax_a.grid(axis="x", color=GRID, linewidth=0.5, alpha=0.7)
    ax_a.set_axisbelow(True)
    for spine in ("top", "right"):
        ax_a.spines[spine].set_visible(False)
    for spine in ("left", "bottom"):
        ax_a.spines[spine].set_color(GRID)
    ax_a.tick_params(axis="x", labelsize=4.8, colors=MUTED, length=2)
    ax_a.tick_params(axis="y", length=0)

    # ----------------------------------------------------------- Panel B ----
    zx = np.arange(len(payload["z_grid"]))
    for curve in payload["curves"]:
        if curve["model"] != "P_target":
            continue
        ax_b.plot(zx, curve["f_unresolved"], RUNG_STYLE.get(curve["rung"], "-"),
                  color=AXIS_COLOR[curve["axis"]], linewidth=1.1,
                  label="%s \u00b7 %s" % (curve["rung"].replace("->", "\u2192"),
                                          AXIS_LABEL[curve["axis"]]))
    ax_b.set_xticks(zx)
    ax_b.set_xticklabels(["%g" % z for z in payload["z_grid"]], fontsize=4.8)
    ax_b.set_ylim(0, 1.0)
    ax_b.set_xlabel("证据门槛 z", fontsize=5.8, color=INK)
    ax_b.set_ylabel("f_unresolved(z)", fontsize=5.8, color=INK)
    ax_b.set_title("(b) 分辨率曲线（目标模型）：z 越大越不可判定", fontsize=6.0, loc="left", color=INK)
    ax_b.legend(fontsize=4.3, frameon=False, loc="upper left", handlelength=1.6,
                labelspacing=0.3, borderpad=0.2)
    ax_b.grid(color=GRID, linewidth=0.5, alpha=0.7)
    ax_b.set_axisbelow(True)
    for spine in ("top", "right"):
        ax_b.spines[spine].set_visible(False)
    for spine in ("left", "bottom"):
        ax_b.spines[spine].set_color(GRID)
    ax_b.tick_params(labelsize=4.8, colors=MUTED, length=2)

    # ----------------------------------------------------------- Panel C ----
    g1 = payload["gate1"]
    ax_c.set_axis_off()
    ax_c.set_title("(c) Gate 1 双轨定性：NOT CLOSED 且 NOT CLOSABLE", fontsize=6.0,
                   loc="left", color=INK)
    _card(ax_c, 0.015, 0.60, 0.97, 0.33, face="#eef4fa", edge="#b9cde0")
    ax_c.text(0.045, 0.845, "Track A \u00b7 decision stability", fontsize=5.4, color=OX_COLOR,
              fontweight="bold", va="center")
    ax_c.text(0.045, 0.755, "状态：%s" % str(g1["track_a"]).replace("_", " "),
              fontsize=5.0, color=INK, va="center")
    ax_c.text(0.045, 0.665, "外部有效性未闭合并不能使 Track A 失效。",
              fontsize=4.5, color=MUTED, va="center")
    _card(ax_c, 0.015, 0.20, 0.97, 0.33, face="#fdf1ec", edge="#e6bfae")
    ax_c.text(0.045, 0.445, "Track B \u00b7 external / experimental validity",
              fontsize=5.4, color=RED_COLOR, fontweight="bold", va="center")
    ax_c.text(0.045, 0.355,
              "状态：%s \u00b7 %s" % (g1["track_b"], g1["closability"]),
              fontsize=5.0, color=INK, va="center")
    ax_c.text(0.045, 0.265,
              "\u03c4_b = %.4f < %.2f\uff0cn_pairs = %s\uff1b最长同源序列 k = %s"
              % (g1["tau_b"], g1["min_tau_b"], g1["n_pairs"], g1["longest_series_k"]),
              fontsize=4.5, color=INK, va="center")
    ax_c.text(0.045, 0.115,
              "要求 \u2265 %s 个核心集分子；绝对标定 %s 行 `est`、升级 %s 行。"
              % (g1["min_species"], g1["est_rows"], g1["upgraded_rows"]),
              fontsize=4.5, color=MUTED, va="center")
    ax_c.set_xlim(0, 1)
    ax_c.set_ylim(0, 1)

    # ----------------------------------------------------------- Panel D ----
    mis = payload["misread"]
    ax_d.set_axis_off()
    ax_d.set_title("(d) 防误读卡片", fontsize=6.0, loc="left", color=INK)
    _card(ax_d, 0.015, 0.185, 0.97, 0.715, face="#fff9e8", edge="#e3cf9a")
    ax_d.text(0.5, 0.80, "0 robust inversions", fontsize=8.6, color=STABLE_COLOR,
              fontweight="bold", ha="center", va="center")
    ax_d.text(0.5, 0.695, "\u2260", fontsize=8.6, color=INK, ha="center", va="center")
    ax_d.text(0.5, 0.59, "0 ranking instability", fontsize=8.6, color=INVERSION_COLOR,
              fontweight="bold", ha="center", va="center")
    ax_d.text(0.5, 0.475,
              "robust inversion: %d observed\uff08%d \u4e2a\uff08\u9636\u68af, \u8f74\uff09\u7ec4\u5408\uff09"
              % (int(mis["f_robust_inv_max"]), mis["n_combinations"]),
              fontsize=5.0, color=INK, ha="center", va="center")
    where = mis.get("f_unresolved_max_at") or {}
    ax_d.text(0.5, 0.385,
              "unresolved: up to %.1f%%\uff08%s \u00b7 %s\uff09"
              % (100.0 * mis["f_unresolved_max"],
                 str(where.get("rung", "")).replace("_", "\u2192"),
                 AXIS_LABEL.get(where.get("axis"), "")),
              fontsize=5.0, color=UNRESOLVED_COLOR, fontweight="bold",
              ha="center", va="center")
    ax_d.text(0.5, 0.285,
              "\u552f\u4e00\u771f\u6b63\u51fa\u73b0 robust inversion \u7684\u5730\u65b9\uff1aP1v\u2192P1a "
              "\u7edd\u70ed\u9636\u68af\uff08n = %s\uff0c%d \u4e2a\uff09"
              % (payload["p1a"]["n"], int(payload["p1a"]["robust_inversion"] or 0)),
              fontsize=4.6, color=MUTED, ha="center", va="center")
    ax_d.text(0.5, 0.205,
              "\u8bfb\u6cd5\uff1aevidence insufficient to resolve \u2014\u2014 \u4e0d\u662f ranking stable\u3002",
              fontsize=4.6, color=INK, ha="center", va="center")
    ax_d.set_xlim(0, 1)
    ax_d.set_ylim(0, 1)

    fig.text(0.012, 0.022, DISCIPLINE, fontsize=4.3, color=MUTED, va="bottom", ha="left",
             wrap=True)
    return fig


def render_png(fig) -> bytes:
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", dpi=DPI, facecolor=FACE)
    return buffer.getvalue()


def render_markdown(payload: dict) -> str:
    lines = [
        "# F56 \u00b7 R14 \u6536\u53e3\u6c47\u603b\u56fe\uff08R13 \u9636\u6bb5\uff09",
        "",
        "> \u7531 `scripts/analyze_r13_summary_figure.py` \u4ece\u5df2\u51bb\u7ed3\u4ea7\u7269\u73b0\u7b97\uff0c"
        "\u4e0d\u8dd1\u65b0\u7535\u5b50\u7ed3\u6784\u3002",
        "",
        "**\u5224\u636e**\uff1a%s" % payload["definition"],
        "",
        "## (a) \u4e09\u6001\u8ba1\u6570\uff08z = 1.0\uff09",
        "",
        "| rung | axis | n | n_pairs | \u03c4_b | STABLE | UNRESOLVED | ROBUST_INVERSION | f_UNRESOLVED |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in payload["three_state"]:
        counts = row.get("counts") or {}
        fractions = row.get("fractions") or {}
        lines.append(
            "| %s | %s | %s | %s | %.3f | %d | %d | %d | %.3f |"
            % (row["rung"], row["axis"], row["n"], row["n_pairs"], row["kendall_tau_b"] or 0.0,
               int(counts.get("STABLE") or 0), int(counts.get("UNRESOLVED") or 0),
               int(counts.get("ROBUST_INVERSION") or 0), float(fractions.get("UNRESOLVED") or 0.0))
        )
    lines += [
        "",
        "## (b) \u5206\u8fa8\u7387\u66f2\u7ebf f_unresolved(z)\uff08\u76ee\u6807\u6a21\u578b\uff09",
        "",
        "| rung | axis | " + " | ".join("z = %g" % z for z in payload["z_grid"]) + " |",
        "| --- | --- | " + " | ".join("---" for _ in payload["z_grid"]) + " |",
    ]
    for curve in payload["curves"]:
        if curve["model"] != "P_target":
            continue
        lines.append("| %s | %s | %s |" % (
            curve["rung"], curve["axis"],
            " | ".join("%.3f" % v for v in curve["f_unresolved"]),
        ))
    mis = payload["misread"]
    g1 = payload["gate1"]
    lines += [
        "",
        "## (c) Gate 1 \u53cc\u8f68\u5b9a\u6027",
        "",
        "| \u8f68\u9053 | \u72b6\u6001 |",
        "| --- | --- |",
        "| Track A\uff08decision stability\uff09 | **%s** |" % str(g1["track_a"]).replace("_", " "),
        "| Track B\uff08external / experimental validity\uff09 | **%s / %s** |"
        % (g1["track_b"], g1["closability"]),
        "",
        "- \u6392\u5e8f\u4e00\u81f4\u6027\u5c42\uff1a\u03c4_b = %.4f < %.2f\uff0cn_pairs = %s\u3002"
        % (g1["tau_b"], g1["min_tau_b"], g1["n_pairs"]),
        "- \u53ef\u95ed\u5408\u6027\uff1a\u6700\u957f\u540c\u88c5\u7f6e / \u540c\u5224\u636e\u540c\u6e90\u5e8f\u5217 k = %s"
        "\uff0c\u8981\u6c42 \u2265 %s \u4e2a\u6838\u5fc3\u96c6\u5206\u5b50\u3002" % (g1["longest_series_k"], g1["min_species"]),
        "- \u7edd\u5bf9\u6807\u5b9a\u5c42\uff1a%s \u884c\u4ecd `est`\uff0c\u5347\u7ea7 %s \u884c\u3002"
        % (g1["est_rows"], g1["upgraded_rows"]),
        "",
        "## (d) \u9632\u8bef\u8bfb\u5361\u7247",
        "",
        "```text",
        "0 robust inversions",
        "  \u2260",
        "0 ranking instability",
        "```",
        "",
        "- robust inversion: **%d observed**\uff08%d \u4e2a\uff08\u9636\u68af, \u8f74\uff09\u7ec4\u5408\uff09\u3002"
        % (int(mis["f_robust_inv_max"]), mis["n_combinations"]),
        "- unresolved: **up to %.1f%%**\uff08%s \u00b7 %s\uff09\u3002"
        % (100.0 * mis["f_unresolved_max"],
           str((mis.get("f_unresolved_max_at") or {}).get("rung", "")).replace("_", "\u2192"),
           AXIS_LABEL.get((mis.get("f_unresolved_max_at") or {}).get("axis"), "")),
        "- \u552f\u4e00\u771f\u6b63\u51fa\u73b0 robust inversion \u7684\u5730\u65b9\uff1aP1v\u2192P1a \u7edd\u70ed\u9636\u68af"
        "\uff08n = %s\uff0c%d \u4e2a\uff09\u3002" % (payload["p1a"]["n"], int(payload["p1a"]["robust_inversion"] or 0)),
        "",
        "> %s" % DISCIPLINE,
        "",
    ]
    return "\n".join(lines) + "\n"


def render_manifest(payload: dict, digests: dict, width_px: int, height_px: int) -> str:
    lines = [
        "# F56 manifest \u00b7 R14 \u6536\u53e3\u6c47\u603b\u56fe",
        "",
        "- script\uff1a`scripts/analyze_r13_summary_figure.py`",
        "- figure\uff1a`outputs/figures/%s`\uff08%d \u00d7 %d px @ %d dpi\uff09"
        % (FIGURE_NAME, width_px, height_px, DPI),
        "- stats\uff1a`%s`\u3001`%s`" % (JSON_PATH.relative_to(REPO_ROOT).as_posix(),
                                        MD_PATH.relative_to(REPO_ROOT).as_posix()),
        "- \u65b0\u7535\u5b50\u7ed3\u6784\u8ba1\u7b97\uff1a**0**\uff08\u5168\u90e8\u6570\u503c\u4e3a\u51bb\u7ed3\u4ea7\u7269\u73b0\u7b97\uff09",
        "",
        "## \u56fe\u6ce8",
        "",
        "(a) \u4e09\u6001\u8ba1\u6570\u5806\u53e0\u6761\uff08STABLE / UNRESOLVED / ROBUST_INVERSION\uff0cz = 1.0\uff09\uff1b",
        "(b) \u76ee\u6807\u6a21\u578b\u7684 f_unresolved(z) \u5206\u8fa8\u7387\u66f2\u7ebf\uff1b",
        "(c) Gate 1 \u53cc\u8f68\u5b9a\u6027\uff08Track A established\uff1bTrack B NOT CLOSED \u4e14 NOT CLOSABLE\uff09\uff1b",
        "(d) \u9632\u8bef\u8bfb\u5361\u7247\uff1a\u300c0 robust inversions \u2260 0 ranking instability\u300d\u3002",
        "",
        "## \u590d\u73b0\u547d\u4ee4",
        "",
        "```powershell",
        ".venv\\Scripts\\python.exe scripts\\analyze_r13_summary_figure.py --check",
        ".venv\\Scripts\\python.exe scripts\\analyze_r13_summary_figure.py",
        "```",
        "",
        "## \u8f93\u5165 sha256",
        "",
        "| \u8def\u5f84 | sha256 |",
        "| --- | --- |",
    ]
    for name in digests["input_order"]:
        lines.append("| `%s` | `%s` |" % (name, digests["inputs"][name]))
    lines += [
        "",
        "## \u8f93\u51fa sha256",
        "",
        "| \u8def\u5f84 | sha256 |",
        "| --- | --- |",
    ]
    for name in digests["output_order"]:
        lines.append("| `%s` | `%s` |" % (name, digests["outputs"][name]))
    lines += [
        "",
        "## \u7eaa\u5f8b\u58f0\u660e",
        "",
        "- " + DISCIPLINE,
        "- \u672c\u56fe\u4e0d\u6539\u52a8\u4efb\u4f55\u65e2\u6709\u5224\u51b3\uff1b\u4e0d\u4f7f\u7528\u4ed3\u5e93\u5916\u6587\u4ef6\u3002",
        "- \u5b57\u4f53\uff1aMicrosoft YaHei / SimHei\uff0caxes.unicode_minus = False\u3002",
        "",
    ]
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Build the R14 close-out summary figure F56.")
    parser.add_argument("--check", action="store_true", help="recompute and compare, never write")
    args = parser.parse_args(argv)

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

    payload = collect()
    assert payload["counts"]["n_rung_axis"] == 6, payload["counts"]
    assert payload["misread"]["f_robust_inv_max"] == 0.0, "F56 assumes zero robust inversions"
    assert payload["gate1"]["track_b"] == "NOT CLOSED"
    assert payload["gate1"]["closability"] == "NOT CLOSABLE"
    assert payload["counts"]["n_robust_inversion"] == 0

    json_text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=False) + "\n"
    md_text = render_markdown(payload)

    figure = draw(payload)
    png = render_png(figure)
    plt.close(figure)

    pixels = mpimg.imread(io.BytesIO(png))
    height_px, width_px = int(pixels.shape[0]), int(pixels.shape[1])
    assert FIG_WIDTH_IN <= 6.3 + 1e-9, FIG_WIDTH_IN
    assert width_px == int(round(FIG_WIDTH_IN * DPI)), width_px
    assert height_px == int(round(FIG_HEIGHT_IN * DPI)), height_px

    json_sha = hashlib.sha256(json_text.encode("utf-8")).hexdigest()
    md_sha = hashlib.sha256(md_text.encode("utf-8")).hexdigest()
    png_sha = hashlib.sha256(png).hexdigest()

    output_paths = [JSON_PATH, MD_PATH, DEFAULT_OUTDIR / FIGURE_NAME]
    shas = {JSON_PATH: json_sha, MD_PATH: md_sha, DEFAULT_OUTDIR / FIGURE_NAME: png_sha}
    digests = {
        "inputs": {INPUTS[key]: sha256(REPO_ROOT / INPUTS[key]) for key in INPUTS},
        "input_order": [INPUTS[key] for key in INPUTS],
        "outputs": {path.relative_to(REPO_ROOT).as_posix(): shas[path] for path in output_paths},
        "output_order": [path.relative_to(REPO_ROOT).as_posix() for path in output_paths],
    }
    manifest_text = render_manifest(payload, digests, width_px, height_px)

    print("F56 R14 close-out summary -- resolved numbers")
    print("-" * 68)
    print("  rung x axis         : %d" % payload["counts"]["n_rung_axis"])
    print("  ladder combinations : %d" % payload["counts"]["n_combinations"])
    print("  robust inversion    : %d observed" % int(payload["misread"]["f_robust_inv_max"]))
    print("  f_unresolved max    : %.1f%%" % (100.0 * payload["misread"]["f_unresolved_max"]))
    print("  Gate 1              : %s / %s" % (payload["gate1"]["track_b"], payload["gate1"]["closability"]))
    print("  figure              : %d x %d px @ %d dpi" % (width_px, height_px, DPI))
    print("  png sha256          : %s" % png_sha[:16])
    print("-" * 68)

    if args.check:
        targets = {JSON_PATH: json_text, MD_PATH: md_text, MANIFEST_PATH: manifest_text}
        for path, expected in targets.items():
            if not path.exists():
                print("CHECK FAILED -- %s is missing" % path)
                return 1
            if path.read_text(encoding="utf-8") != expected:
                print("CHECK FAILED -- %s differs from the regenerated text" % path)
                return 1
        png_path = DEFAULT_OUTDIR / FIGURE_NAME
        if not png_path.exists():
            print("CHECK FAILED -- %s is missing" % png_path)
            return 1
        disk = mpimg.imread(png_path)
        memory = mpimg.imread(io.BytesIO(png))
        if disk.shape != memory.shape or not np.array_equal(disk, memory):
            print("CHECK FAILED -- pixels differ from %s" % png_path)
            return 1
        print("CHECK OK -- JSON/MD/manifest byte-identical; %s re-renders pixel-identical"
              % png_path.relative_to(REPO_ROOT).as_posix())
        return 0

    STAGE_DIR.mkdir(parents=True, exist_ok=True)
    DEFAULT_OUTDIR.mkdir(parents=True, exist_ok=True)
    with open(JSON_PATH, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(json_text)
    with open(MD_PATH, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(md_text)
    with open(MANIFEST_PATH, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(manifest_text)
    with open(DEFAULT_OUTDIR / FIGURE_NAME, "wb") as handle:
        handle.write(png)
    print("wrote %s" % JSON_PATH.relative_to(REPO_ROOT).as_posix())
    print("wrote %s" % MD_PATH.relative_to(REPO_ROOT).as_posix())
    print("wrote %s" % MANIFEST_PATH.relative_to(REPO_ROOT).as_posix())
    print("wrote %s" % (DEFAULT_OUTDIR / FIGURE_NAME).relative_to(REPO_ROOT).as_posix())
    return 0


if __name__ == "__main__":
    sys.exit(main())
