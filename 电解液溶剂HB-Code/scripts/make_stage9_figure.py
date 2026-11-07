"""Stage 9 figure (F18).

The question of Stage 9 is narrow and answerable: when the first Li+ solvation
shell is made more realistic -- one explicit solvent molecule (Week 5, C1) vs
two (this stage, homoleptic [Li(M)2]+) -- does the coordination-induced shift of
the redox descriptors, and the ranking of the candidates it produces, survive?

    (a) dIP(1:2) vs dIP(1:1) per motif, against the identity line
    (b) dEA(1:2) vs dEA(1:1) per motif, against the identity line
    (c) rank flow from shell 1 to shell 2 on both axes
    (d) the frozen decision metrics for shell 1 -> shell 2, all 12 vs m1 only

Labels are ASCII on purpose: the workspace has no guaranteed CJK font.

Usage:
    .venv\\Scripts\\python.exe scripts\\make_stage9_figure.py
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
WEEK8 = REPO_ROOT / "outputs" / "week8"
FIGDIR = REPO_ROOT / "outputs" / "figures"
SHIFTS_CSV = WEEK8 / "stage9_shell_shifts.csv"
STABILITY_CSV = WEEK8 / "stage9_decision_stability.csv"
MANIFEST = FIGDIR / "figure_manifest_week8_stage9.md"

OX_COLOR = "#b45309"
RED_COLOR = "#1d4ed8"
IDENTITY = "#111827"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_csv(path: Path):
    with io.open(path, encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _f(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Render figure F18.")
    parser.add_argument("--shifts", type=Path, default=SHIFTS_CSV)
    parser.add_argument("--stability", type=Path, default=STABILITY_CSV)
    parser.add_argument("--outdir", type=Path, default=FIGDIR)
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    return parser.parse_args(argv)


def _paired_panel(ax, shifts, key1, key2, colour, title, xlabel):
    one = np.array([_f(row[key1]) for row in shifts])
    two = np.array([_f(row[key2]) for row in shifts])
    finite = np.isfinite(one) & np.isfinite(two)
    ax.scatter(one[finite], two[finite], s=42, color=colour, zorder=3,
               edgecolor="white", linewidth=0.8)
    for row, x, y in zip(shifts, one, two):
        if not (np.isfinite(x) and np.isfinite(y)):
            continue
        ax.annotate(row["name"] + "/" + row["motif_id"], (x, y), fontsize=6.5,
                    xytext=(4, 3), textcoords="offset points", color="#374151")
    if finite.any():
        low = min(one[finite].min(), two[finite].min())
        high = max(one[finite].max(), two[finite].max())
        pad = 0.08 * (high - low)
        ax.plot([low - pad, high + pad], [low - pad, high + pad],
                color=IDENTITY, linewidth=0.9, linestyle="--", zorder=1)
        ax.set_xlim(low - pad, high + pad)
        ax.set_ylim(low - pad, high + pad)
    ax.set_xlabel(xlabel, fontsize=8)
    ax.set_ylabel("shell 1:2  (eV)", fontsize=8)
    ax.set_title(title, fontsize=9)
    ax.grid(alpha=0.25)


def _rank_panel(ax, shifts, key1, key2, colour, title):
    rows = [row for row in shifts
            if np.isfinite(_f(row[key1])) and np.isfinite(_f(row[key2]))]
    order1 = sorted(rows, key=lambda row: _f(row[key1]), reverse=True)
    order2 = sorted(rows, key=lambda row: _f(row[key2]), reverse=True)
    rank1 = {row["name"] + "/" + row["motif_id"]: i + 1 for i, row in enumerate(order1)}
    rank2 = {row["name"] + "/" + row["motif_id"]: i + 1 for i, row in enumerate(order2)}
    labels = [row["name"] + "/" + row["motif_id"] for row in order1]
    for index, label in enumerate(labels):
        first, second = rank1[label], rank2[label]
        moved = first != second
        ax.plot([0, 1], [len(labels) - first, len(labels) - second],
                color=colour if moved else "#cbd5e1",
                linewidth=1.6 if moved else 0.9,
                marker="o", markersize=3.4, zorder=2 if moved else 1)
        ax.annotate(label, (0, len(labels) - first), fontsize=6.2, ha="right",
                    va="center", xytext=(-5, 0), textcoords="offset points")
        ax.annotate(label, (1, len(labels) - second), fontsize=6.2, ha="left",
                    va="center", xytext=(5, 0), textcoords="offset points")
    ax.set_xlim(-0.55, 1.55)
    ax.set_xticks([0, 1])
    ax.set_xticklabels(["shell 1:1", "shell 1:2"], fontsize=8)
    ax.set_yticks([])
    ax.set_title(title, fontsize=9)
    for spine in ("top", "right", "left"):
        ax.spines[spine].set_visible(False)


def _metric_panel(ax, stability):
    keys = ("kendall_tau_b", "overlap_20", "f_robust_inv", "f_unresolved_shell2")
    nice = ("tau_b", "O_20%", "f_robust_inv", "f_unresolved(1:2)")
    rows = [row for row in stability if row.get("kendall_tau_b")]
    labels = ["%s\n%s" % (row["axis"][:3], row["population"]) for row in rows]
    x = np.arange(len(rows))
    width = 0.2
    colours = (OX_COLOR, "#0f766e", "#be123c", "#6d28d9")
    for index, (key, name, colour) in enumerate(zip(keys, nice, colours)):
        values = [max(0.0, _f(row[key])) for row in rows]
        ax.bar(x + (index - 1.5) * width, values, width, color=colour, label=name)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=7.5)
    ax.set_ylabel("value", fontsize=8)
    ax.set_title("(d) decision metrics, shell 1:1 -> 1:2", fontsize=9)
    ax.legend(fontsize=7, ncol=4, loc="upper center")
    ax.set_ylim(0, 1.05)
    ax.grid(axis="y", alpha=0.25)


def main(argv=None) -> int:
    args = parse_args(argv)
    args.outdir.mkdir(parents=True, exist_ok=True)
    shifts = read_csv(args.shifts)
    stability = read_csv(args.stability)

    fig = plt.figure(figsize=(15.5, 10.5))
    grid = fig.add_gridspec(2, 2, hspace=0.32, wspace=0.22)

    _paired_panel(fig.add_subplot(grid[0, 0]), shifts, "d_ip_shell1_ev",
                  "d_ip_shell2_ev", OX_COLOR,
                  "(a) coordination shift of IP: 1:1 vs 1:2 shell", "shell 1:1  (eV)")
    _paired_panel(fig.add_subplot(grid[0, 1]), shifts, "d_ea_shell1_ev",
                  "d_ea_shell2_ev", RED_COLOR,
                  "(b) coordination shift of EA: 1:1 vs 1:2 shell", "shell 1:1  (eV)")
    _rank_panel(fig.add_subplot(grid[1, 0]), shifts, "d_ip_shell1_ev",
                "d_ip_shell2_ev", OX_COLOR,
                "(c) rank flow, oxidation shift (dIP)")
    _metric_panel(fig.add_subplot(grid[1, 1]), stability)

    path = args.outdir / "F18_stage9_explicit_shell.png"
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)

    lines = [
        "# Figure manifest - Week 8 / Stage 9 (F18)",
        "",
        "| figure | file | figure SHA256 | inputs (SHA256) |",
        "| --- | --- | --- | --- |",
        "| F18 | `%s` | %s | `stage9_shell_shifts.csv` %s |"
        % (path.name, sha256(path), sha256(args.shifts)),
        "",
        "F18 panel (a,b): per-motif coordination shift dIP / dEA computed with a",
        "1:1 first shell (Week 5) against the same quantity with a homoleptic 1:2",
        "shell (this stage). Both are r2SCAN-3c vertical ionisation energies taken",
        "at the optimised reference geometry of their own complex; the free-molecule",
        "reference C0 is identical in the two columns. The dashed line is identity,",
        "so a point off the diagonal is a shell-size effect on the coordination shift.",
        "",
        "Panel (c): the rank each motif takes in dIP under the two shell sizes;",
        "coloured lines cross when the shell size changes the ordering.",
        "",
        "Panel (d): the frozen decision metrics of `layer_stability`",
        "(`analyze_p1_core_set.py`) applied to shell 1:1 -> shell 1:2, for the",
        "oxidation and reduction axes and for the all-12 and primary-m1 populations.",
        "`f_unresolved(1:2)` is the unresolved-pair fraction of the 1:2 ranking, at",
        "the preregistered z = 1.0.",
        "",
        "`stage9_decision_stability.csv` SHA256 %s" % sha256(args.stability),
        "",
    ]
    args.manifest.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("[F18] %s" % path)
    print("[manifest] %s" % args.manifest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())