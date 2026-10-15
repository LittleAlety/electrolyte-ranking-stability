#!/usr/bin/env python
"""Week 25 figure F52 -- Gate 1 ordering consistency, four panels.

F52 (Gate 1, ordering-consistency tier: the negative result, diagnosed)

    (a) experimental rank vs registered-arm (P1) rank, species labelled.  The
        diagonal is agreement; EC is the species that leaves it.
    (b) the same two orderings as a slopegraph, so the migration of every
        discordant pair is readable as a crossing.
    (c) the anchor-noise bootstrap distribution of tau_b with the frozen 0.9
        threshold and the observed statistic marked.
    (d) leave-one-molecule-out tau_b on the registered arm, one bar per dropped
        anchor species.

Every number is read from ``outputs/week25/gate1_oxidation.json``; the script holds
no literals beyond the criteria it draws as reference lines (0.9, and the frozen
observed tau_b taken from the payload).  In-figure text is Chinese, rendered with
Microsoft YaHei / SimHei.

Usage
-----
    python scripts/analyze_w25_figure_f52.py            # write the PNG
    python scripts/analyze_w25_figure_f52.py --check    # re-render in memory and
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

REPO_ROOT = Path(__file__).resolve().parents[1]
PAYLOAD = REPO_ROOT / "outputs" / "week25" / "gate1_oxidation.json"
DEFAULT_OUTDIR = REPO_ROOT / "outputs" / "figures"
FIGURE_NAME = "F52_gate1_ordering.png"

DPI = 200
FIG_WIDTH_IN = 6.3
FIG_HEIGHT_IN = 7.1

INK = "#1f2933"
MUTED = "#61707d"
GRID = "#d6dde5"
ACCENT = "#2f6fb2"
WARN = "#c05621"
OK = "#2f855a"
FACE = "#ffffff"


def read_json(path):
    with io.open(path, "r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()


def resolve(payload):
    """Flatten the payload into exactly the numbers the figure draws."""

    names = list(payload["species"]["anchored"])
    arms = payload["arms"]
    discordant = [(pair["a"], pair["b"]) for pair in arms["P1"]["discordant_pairs"]]
    discordant_names = set()
    for a, b in discordant:
        discordant_names.add(a)
        discordant_names.add(b)
    lomo = sorted(payload["leave_one_molecule_out"], key=lambda item: item["tau_b"])
    return {
        "names": names,
        "exp_ranks": list(payload["species"]["experiment_ranks"]),
        "p1_ranks": list(arms["P1"]["ranks"]),
        "tau_b": {arm: arms[arm]["tau_b"] for arm in ("P0", "P1", "P2")},
        "observed": payload["reproduction"]["tau_b"],
        "min_tau_b": payload["constants"]["min_tau_b"],
        "n_pairs": payload["reproduction"]["n_pairs"],
        "skipped": list(payload["species"]["skipped_not_in_core_set"]),
        "discordant": discordant,
        "discordant_names": discordant_names,
        "dominant": payload["dominant_species"]["by_tau_b_recovery"],
        "dominant_tau_b_without": payload["dominant_species"]["tau_b_without"],
        "lomo_names": [item["dropped"] for item in lomo],
        "lomo_tau_b": [item["tau_b"] for item in lomo],
        "hist_edges": list(payload["bootstrap"]["histogram"]["bin_edges"]),
        "hist_counts": list(payload["bootstrap"]["histogram"]["counts"]),
        "boot_q025": payload["bootstrap"]["tau_b_q025"],
        "boot_q975": payload["bootstrap"]["tau_b_q975"],
        "boot_prob_pass": payload["bootstrap"]["prob_pass"],
        "boot_prob_observed": payload["bootstrap"]["prob_at_least_observed"],
        "boot_draws": payload["bootstrap"]["draws"],
        "sigma_V": payload["bootstrap"]["sigma_V"],
        "p_perm": payload["permutation"]["p_one_sided"],
    }


def style(ax):
    ax.set_facecolor(FACE)
    ax.tick_params(labelsize=7, colors=INK, length=2.5)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(GRID)
    ax.spines["bottom"].set_color(GRID)
    ax.grid(True, color=GRID, linewidth=0.5, alpha=0.65, zorder=0)


def draw(payload):
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
    plt.rcParams["font.family"] = "sans-serif"
    plt.rcParams["axes.unicode_minus"] = False

    number = resolve(payload)
    names = number["names"]
    exp_ranks = number["exp_ranks"]
    p1_ranks = number["p1_ranks"]
    dominant = number["dominant"]
    observed = number["observed"]
    threshold = number["min_tau_b"]

    fig, axes = plt.subplots(2, 2, figsize=(FIG_WIDTH_IN, FIG_HEIGHT_IN), dpi=DPI)
    fig.patch.set_facecolor(FACE)

    # ---- (a) rank vs rank ---------------------------------------------------
    ax = axes[0][0]
    ax.plot([0.4, 7.6], [0.4, 7.6], linestyle="--", linewidth=0.9, color=GRID, zorder=1)
    for index, name in enumerate(names):
        moved = exp_ranks[index] != p1_ranks[index]
        is_dominant = name == dominant
        colour = WARN if is_dominant else (ACCENT if moved else MUTED)
        ax.scatter(
            exp_ranks[index],
            p1_ranks[index],
            s=52 if is_dominant else 30,
            color=colour,
            edgecolor="white",
            linewidth=0.7,
            zorder=4 if is_dominant else 3,
        )
        ax.annotate(
            name,
            (exp_ranks[index], p1_ranks[index]),
            textcoords="offset points",
            xytext=(7, 4),
            fontsize=7,
            color=colour,
            fontweight="bold" if is_dominant else "normal",
        )
    ax.set_xlim(0.4, 7.6)
    ax.set_ylim(0.4, 7.6)
    ax.set_xticks(range(1, 8))
    ax.set_yticks(range(1, 8))
    ax.set_xlabel("实验位次（1 = 最难氧化）", fontsize=7.5, color=INK)
    ax.set_ylabel("P1 模型位次", fontsize=7.5, color=INK)
    ax.set_title(
        "(a) 实验序 vs P1 序（τ_b=%.4f）" % number["tau_b"]["P1"],
        fontsize=8,
        loc="left",
        color=INK,
    )
    ax.text(
        0.03,
        0.97,
        "对角虚线 = 完全一致\n橙色 = 敲除后 τ_b 回升最多的物种",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=6.2,
        color=MUTED,
    )
    style(ax)

    # ---- (b) slopegraph -----------------------------------------------------
    ax = axes[0][1]
    for index, name in enumerate(names):
        left, right = exp_ranks[index], p1_ranks[index]
        is_dominant = name == dominant
        moved = left != right
        colour = WARN if is_dominant else (ACCENT if moved else MUTED)
        ax.plot(
            [0, 1],
            [left, right],
            color=colour,
            linewidth=2.0 if is_dominant else (1.3 if moved else 0.9),
            alpha=0.95 if is_dominant else (0.9 if moved else 0.5),
            marker="o",
            markersize=4.0 if is_dominant else 3.0,
            zorder=4 if is_dominant else (3 if moved else 2),
        )
        for xpos, ypos, ha, dx in ((0, left, "right", -7), (1, right, "left", 7)):
            ax.annotate(
                name,
                (xpos, ypos),
                textcoords="offset points",
                xytext=(dx, 0),
                ha=ha,
                va="center",
                fontsize=7,
                color=colour,
                fontweight="bold" if is_dominant else "normal",
            )
    ax.set_xlim(-0.36, 1.36)
    ax.set_ylim(7.7, 0.3)
    ax.set_xticks([0, 1])
    ax.set_xticklabels(["实验", "P1 模型"], fontsize=7.5, color=INK)
    ax.set_yticks(range(1, 8))
    ax.set_ylabel("位次（1 = 最难氧化）", fontsize=7.5, color=INK)
    ax.set_title(
        "(b) 位次迁移：%d 对不一致" % len(number["discordant"]),
        fontsize=8,
        loc="left",
        color=INK,
    )
    style(ax)

    # ---- (c) bootstrap ------------------------------------------------------
    ax = axes[1][0]
    edges = np.asarray(number["hist_edges"], dtype=float)
    counts = np.asarray(number["hist_counts"], dtype=float)
    ax.bar(
        edges[:-1],
        counts,
        width=np.diff(edges),
        align="edge",
        color=ACCENT,
        alpha=0.72,
        edgecolor="white",
        linewidth=0.35,
        zorder=2,
    )
    top = float(counts.max()) * 1.38
    ax.axvline(threshold, color=WARN, linestyle="--", linewidth=1.3, zorder=4)
    ax.axvline(observed, color=INK, linestyle="-", linewidth=1.3, zorder=4)
    ax.annotate(
        "冻结判据 0.9",
        xy=(threshold, top),
        xytext=(threshold - 0.025, top),
        ha="right",
        va="top",
        rotation=90,
        fontsize=6.6,
        color=WARN,
    )
    ax.annotate(
        "观测 %.4f" % observed,
        xy=(observed, top),
        xytext=(observed - 0.025, top),
        ha="right",
        va="top",
        rotation=90,
        fontsize=6.6,
        color=INK,
    )
    ax.text(
        0.985,
        0.58,
        "95%% 区间 [%.4f, %.4f]\nP(τ_b≥0.9) = %.1e\nP(τ_b≥观测) = %.3f"
        % (
            number["boot_q025"],
            number["boot_q975"],
            number["boot_prob_pass"],
            number["boot_prob_observed"],
        ),
        transform=ax.transAxes,
        ha="right",
        va="top",
        fontsize=6.4,
        color=INK,
    )
    ax.set_xlim(float(edges[0]) - 0.03, float(edges[-1]) + 0.03)
    ax.set_ylim(0.0, top)
    ax.set_xlabel(
        "τ_b（锚点噪声 bootstrap，%d 次，σ=%.1f V）" % (number["boot_draws"], number["sigma_V"]),
        fontsize=7.5,
        color=INK,
    )
    ax.set_ylabel("频数", fontsize=7.5, color=INK)
    ax.set_title("(c) 实验重复性噪声下的 τ_b 分布", fontsize=8, loc="left", color=INK)
    style(ax)

    # ---- (d) leave-one-molecule-out ----------------------------------------
    ax = axes[1][1]
    positions = np.arange(len(number["lomo_names"]))
    colours = [
        WARN if name == dominant else (OK if value < observed else ACCENT)
        for name, value in zip(number["lomo_names"], number["lomo_tau_b"])
    ]
    ax.bar(positions, number["lomo_tau_b"], color=colours, width=0.66, zorder=2)
    ax.axhline(observed, color=INK, linestyle=":", linewidth=1.1, zorder=3)
    ax.axhline(threshold, color=WARN, linestyle="--", linewidth=1.1, zorder=3)
    for position, value in zip(positions, number["lomo_tau_b"]):
        ax.annotate(
            "%.3f" % value,
            (position, value),
            textcoords="offset points",
            xytext=(0, 3),
            ha="center",
            fontsize=6.2,
            color=INK,
        )
    ax.annotate(
        "全量 %.4f" % observed,
        xy=(-0.42, observed),
        textcoords="offset points",
        xytext=(0, -8),
        ha="left",
        va="top",
        fontsize=6.3,
        color=INK,
    )
    ax.annotate(
        "判据 0.9",
        xy=(-0.42, threshold),
        textcoords="offset points",
        xytext=(0, 4),
        ha="left",
        va="bottom",
        fontsize=6.3,
        color=WARN,
    )
    ax.set_xticks(positions)
    ax.set_xticklabels(number["lomo_names"], fontsize=7.5, color=INK)
    ax.set_xlim(-0.62, 6.62)
    ax.set_ylim(0.0, 1.0)
    ax.set_xlabel("剔除的锚点物种", fontsize=7.5, color=INK)
    ax.set_ylabel("τ_b（P1，留一）", fontsize=7.5, color=INK)
    ax.set_title("(d) 逐分子敲除：%s 主导不一致" % dominant, fontsize=8, loc="left", color=INK)
    style(ax)

    fig.subplots_adjust(left=0.095, right=0.985, top=0.935, bottom=0.105, hspace=0.50, wspace=0.30)
    fig.text(
        0.095,
        0.024,
        "锚点：Ue1994/Okoshi2015 氧化系列（纯溶剂 + Et4NBF4，%d 个核心集物种 / %d 对，转录未回原刊核验）；"
        "\n"
        "模型：P1 r2SCAN-3c 气相 IP；bootstrap 仅扰动实验端；另有 %d 行锚点无核心集模型值，按跳过处理。"
        % (len(names), number["n_pairs"], len(number["skipped"])),
        fontsize=5.7,
        color=MUTED,
        linespacing=1.4,
    )
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
    number = resolve(payload)
    target = DEFAULT_OUTDIR / FIGURE_NAME

    if args.check:
        if not target.exists():
            print("CHECK FAILED -- %s is missing" % target)
            return 1
        disk = mpimg.imread(target)
        memory = mpimg.imread(io.BytesIO(png))
        if disk.shape != memory.shape or not np.array_equal(disk, memory):
            print("CHECK FAILED -- pixels differ from %s" % target)
            return 1
        print("CHECK OK -- %s re-renders pixel-identical" % target.relative_to(REPO_ROOT))
    else:
        DEFAULT_OUTDIR.mkdir(parents=True, exist_ok=True)
        with target.open("wb") as handle:
            handle.write(png)
        print("wrote %s" % target.relative_to(REPO_ROOT))

    print("  payload sha256      : %s" % sha256(PAYLOAD))
    print(
        "  tau_b P0/P1/P2      : %.4f / %.4f / %.4f"
        % tuple(number["tau_b"][arm] for arm in ("P0", "P1", "P2"))
    )
    print("  observed / criterion: %.4f / %.1f" % (number["observed"], number["min_tau_b"]))
    print(
        "  dominant species    : %s (tau_b %.4f -> %.4f)"
        % (number["dominant"], number["observed"], number["dominant_tau_b_without"])
    )
    print(
        "  bootstrap 95%%       : [%.4f, %.4f], P(pass)=%.2e"
        % (number["boot_q025"], number["boot_q975"], number["boot_prob_pass"])
    )
    print("  permutation p       : %.4f" % number["p_perm"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
