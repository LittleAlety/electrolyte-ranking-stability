#!/usr/bin/env python
"""Week 25 figure F53 -- family-resolved ranking statistics.

F53 (v2 §19 Stage 6 family-resolved / cross-family tier)

    (a) within-family Kendall tau_b vs rung, oxidation axis, with the molecule
        bootstrap 95% band per family; families whose within-family tau_b is not
        estimable (n < 3) appear as hollow markers in the not_estimable strip.
    (b) within-family unresolved-pair fraction f_unresolved(after) vs rung,
        oxidation axis.
    (c) / (d) the same two panels on the reduction axis.

Solid = native-18 population; dashed = common-10 population.  Every number is
read from outputs/week25/family_resolved_stats.json; the script holds no literals
beyond the axis limits and the reference line at tau_b = 1.

Usage
-----
    python scripts/analyze_w25_figure_f53.py            # write the PNG
    python scripts/analyze_w25_figure_f53.py --check    # re-render in memory and
                                                        # compare with the file on disk
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
from matplotlib.lines import Line2D  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
PAYLOAD = REPO_ROOT / "outputs" / "week25" / "family_resolved_stats.json"
DEFAULT_OUTDIR = REPO_ROOT / "outputs" / "figures"
FIGURE_NAME = "F53_family_resolved.png"

DPI = 200
FIG_WIDTH_IN = 6.3
FIG_HEIGHT_IN = 6.4

RUNG_KEYS = ["P0_to_P1", "P1_to_P2", "G1_to_G2", "C0_to_C1", "C1_to_C2"]
RUNG_TICKS = ["P0>P1", "P1>P2", "G1>G2", "C0>C1", "C1>C2"]
PANEL_TOP = 1.16
STRIP_Y = 1.06
TAU_YLIM = (-1.14, 1.24)
F_YLIM = (-0.10, 1.24)

INK = "#1f2933"
MUTED = "#61707d"
GRID = "#d6dde5"
FACE = "#ffffff"

FAMILY_COLORS = {
    "linear_carbonate": "#2f6fb2",
    "cyclic_carbonate": "#c05621",
    "ether": "#2f855a",
    "ester": "#6b46c1",
    "nitrile": "#b7791f",
    "sulfone": "#c53030",
    "sulfoxide": "#00838f",
    "phosphate": "#4a5568",
}
FAMILY_LABELS = {
    "linear_carbonate": "linear_carbonate (DMC/EMC/DEC)",
    "cyclic_carbonate": "cyclic_carbonate (EC/PC/FEC/VC)",
    "ether": "ether (DME/DOL/TEGDME)",
    "ester": "ester (EA/MA/GBL)",
    "nitrile": "nitrile (AN/SN)",
    "sulfone": "sulfone (SL)",
    "sulfoxide": "sulfoxide (DMSO)",
    "phosphate": "phosphate (TMP)",
}


def read_json(path):
    with io.open(path, "r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()


def index_rows(payload):
    table = {}
    for row in payload["family_resolved"]:
        table[(row["population"], row["rung"], row["axis"], row["family"])] = row
    return table


def style(ax):
    ax.set_facecolor(FACE)
    ax.tick_params(labelsize=6.6, colors=INK, length=2.2)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(GRID)
    ax.spines["bottom"].set_color(GRID)
    ax.grid(True, color=GRID, linewidth=0.5, alpha=0.6, zorder=0)


def draw_tau_panel(ax, table, axis, families):
    for family in families:
        color = FAMILY_COLORS[family]
        xs, ys, los, his, not_estimable_x = [], [], [], [], []
        for position, rung in enumerate(RUNG_KEYS):
            row = table.get(("native", rung, axis, family))
            if row is not None and row["tau_b_status"] == "ok":
                xs.append(position)
                ys.append(row["tau_b"])
                los.append(row["tau_b_ci_low"] if row["tau_b_ci_low"] is not None else row["tau_b"])
                his.append(row["tau_b_ci_high"] if row["tau_b_ci_high"] is not None else row["tau_b"])
            else:
                not_estimable_x.append(position)
        if xs:
            ax.fill_between(xs, los, his, color=color, alpha=0.13, linewidth=0, zorder=1)
            ax.plot(xs, ys, color=color, marker="o", markersize=3.2, linewidth=1.3, zorder=4)
        if not_estimable_x:
            ax.plot(not_estimable_x, [STRIP_Y] * len(not_estimable_x), linestyle="none",
                    marker="o", markersize=3.6, markerfacecolor="none",
                    markeredgecolor=color, markeredgewidth=0.9, zorder=3)
    ax.axhline(1.0, color=MUTED, linestyle=":", linewidth=0.7, zorder=2)
    ax.set_ylim(*TAU_YLIM)
    ax.set_yticks([-1.0, -0.5, 0.0, 0.5, 1.0])
    ax.set_ylabel("家族内 Kendall τ_b", fontsize=7.2, color=INK)
    ax.annotate("空心 = not_estimable (n<3)", xy=(0.02, 0.965), xycoords="axes fraction",
                fontsize=5.6, color=MUTED)
    ax.annotate("common-10：家族内 τ_b 全部 not_estimable(n≤2)", xy=(0.02, 0.02),
                xycoords="axes fraction", fontsize=5.6, color=MUTED)


def draw_f_panel(ax, table, axis, families):
    for population, linestyle, marker, filled in (
        ("native", "-", "o", True),
        ("common10", "--", "s", False),
    ):
        for family in families:
            color = FAMILY_COLORS[family]
            xs, ys, not_estimable_x = [], [], []
            for position, rung in enumerate(RUNG_KEYS):
                row = table.get((population, rung, axis, family))
                if row is not None and row["f_unresolved_after"] is not None:
                    xs.append(position)
                    ys.append(row["f_unresolved_after"])
                else:
                    not_estimable_x.append(position)
            if xs:
                ax.plot(xs, ys, color=color, linestyle=linestyle,
                        marker=marker, markersize=2.8, linewidth=1.15,
                        markerfacecolor=(color if filled else "none"),
                        markeredgecolor=color, zorder=4)
            if not_estimable_x:
                ax.plot(not_estimable_x, [STRIP_Y] * len(not_estimable_x), linestyle="none",
                        marker=marker, markersize=3.2, markerfacecolor="none",
                        markeredgecolor=color, markeredgewidth=0.8, alpha=0.75, zorder=3)
    ax.axhline(1.0, color=MUTED, linestyle=":", linewidth=0.7, zorder=2)
    ax.set_ylim(*F_YLIM)
    ax.set_yticks([0.0, 0.25, 0.5, 0.75, 1.0])
    ax.set_ylabel("家族内 f_unresolved (after, z=1.0)", fontsize=7.2, color=INK)
    ax.annotate("空心 = 无 pair (n<2)", xy=(0.02, 0.965), xycoords="axes fraction",
                fontsize=5.6, color=MUTED)


def draw(payload):
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
    plt.rcParams["font.family"] = "sans-serif"
    plt.rcParams["axes.unicode_minus"] = False

    table = index_rows(payload)
    families = [family for family in FAMILY_COLORS if family in payload["families"]]

    fig, axes = plt.subplots(2, 2, figsize=(FIG_WIDTH_IN, FIG_HEIGHT_IN))

    draw_tau_panel(axes[0][0], table, "oxidation", families)
    draw_f_panel(axes[0][1], table, "oxidation", families)
    draw_tau_panel(axes[1][0], table, "reduction", families)
    draw_f_panel(axes[1][1], table, "reduction", families)

    axes[0][0].set_title("(a) 氧化轴：家族内 τ_b 随台阶（带 95% CI 带）", fontsize=7.6, loc="left", color=INK)
    axes[0][1].set_title("(b) 氧化轴：家族内 f_unresolved(after)", fontsize=7.6, loc="left", color=INK)
    axes[1][0].set_title("(c) 还原轴：家族内 τ_b 随台阶（带 95% CI 带）", fontsize=7.6, loc="left", color=INK)
    axes[1][1].set_title("(d) 还原轴：家族内 f_unresolved(after)", fontsize=7.6, loc="left", color=INK)

    for row in axes:
        for ax in row:
            ax.set_xticks(range(len(RUNG_KEYS)))
            ax.set_xticklabels(RUNG_TICKS, fontsize=6.6, color=INK)
            ax.set_xlim(-0.35, len(RUNG_KEYS) - 0.65)
            style(ax)

    handles = [
        Line2D([0], [0], color=FAMILY_COLORS[family], marker="o", markersize=3.2,
               linewidth=1.3, label=FAMILY_LABELS[family])
        for family in families
    ]
    handles.append(Line2D([0], [0], color=INK, linestyle="-", linewidth=1.2,
                          label="native-18（实线）"))
    handles.append(Line2D([0], [0], color=INK, linestyle="--", linewidth=1.2,
                          label="common-10（虚线）"))
    fig.legend(handles=handles, loc="lower center", ncol=5, fontsize=5.6,
               frameon=False, columnspacing=0.9, handlelength=1.4,
               handletextpad=0.4, bbox_to_anchor=(0.5, 0.083))

    fig.suptitle("F53 · family-resolved 排序统计（8 家族 × 5 台阶 × 2 轴）", fontsize=8.4,
                 color=INK, y=0.985)
    fig.text(
        0.5, 0.045,
        "零新增电子结构计算；数据来自 outputs/week25/family_resolved_stats.json"
        "（重算自 week9 stage10 逐分子产物，seed=20261002, 5000 次 bootstrap）。"
        "\nCI 为 n=3–4 分子有放回重抽样，区间宽、仅作参考，不得读作显著；"
        "common-10 的家族内 τ_b 全部 not_estimable。",
        ha="center", va="top", fontsize=5.4, color=MUTED, linespacing=1.5,
    )
    fig.subplots_adjust(left=0.105, right=0.985, top=0.905, bottom=0.215,
                        hspace=0.42, wspace=0.30)
    return fig


def render_bytes(fig):
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", dpi=DPI, facecolor=FACE)
    return buffer.getvalue()


def build():
    payload = read_json(PAYLOAD)
    figure = draw(payload)
    png = render_bytes(figure)
    plt.close(figure)
    return payload, png


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--check",
        action="store_true",
        help="re-render in memory and compare the pixels with the file on disk",
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    payload, png = build()
    target = DEFAULT_OUTDIR / FIGURE_NAME
    counts = payload["counts"]

    if args.check:
        if not target.exists():
            print("CHECK FAILED -- %s is missing" % target)
            return 1
        disk = mpimg.imread(target)
        memory = mpimg.imread(io.BytesIO(png))
        if disk.shape != memory.shape or not np.array_equal(disk, memory):
            print("CHECK FAILED -- pixels differ from %s" % target)
            return 1
        print("CHECK OK -- %s re-renders pixel-identical" % target.relative_to(REPO_ROOT).as_posix())
    else:
        DEFAULT_OUTDIR.mkdir(parents=True, exist_ok=True)
        with target.open("wb") as handle:
            handle.write(png)
        print("wrote %s" % target.relative_to(REPO_ROOT).as_posix())

    print("  payload sha256     : %s" % sha256(PAYLOAD))
    print("  figure size        : %.1f x %.1f in @ %d dpi" % (FIG_WIDTH_IN, FIG_HEIGHT_IN, DPI))
    print("  combos / estimable : %d / %d"
          % (counts["combos_total"], counts["estimable_total"]))
    print("  families           : %d" % len(payload["families"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
