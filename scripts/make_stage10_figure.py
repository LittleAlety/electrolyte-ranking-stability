"""Stage 10 figure (F19) -- the five-rung ladder on one yardstick.

Week 9 asks one question and answers it with one scatter plot per hypothesis:

    does the *spread* of a rung's shift, rather than its *size*, decide whether
    the rung rewrites the ranking?

    (a) tau_b of every rung/axis, rungs ordered by increasing shift std
    (b) shift std vs tau_b        -> the H_var evidence (rho = -0.851)
    (c) abs(shift mean) vs tau_b  -> the H_mean control  (rho = -0.535)
    (d) shift std vs f_unresolved -> the mechanism (rho = +0.894)

All 10 points in (b)-(d) are the common-10 subset, i.e. the same ten molecules
at every rung. Labels are ASCII on purpose: the workspace has no guaranteed
CJK font.

Usage:
    .venv\\Scripts\\python.exe scripts\\make_stage10_figure.py
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
WEEK9 = REPO_ROOT / "outputs" / "week9"
FIGDIR = REPO_ROOT / "outputs" / "figures"
LADDER_CSV = WEEK9 / "stage10_ladder.csv"
MANIFEST = FIGDIR / "figure_manifest_week9_stage10.md"

OX_COLOR = "#b45309"
RED_COLOR = "#1d4ed8"
FIT_COLOR = "#6b7280"

SHORT = {
    "P0_to_P1": "P0->P1",
    "P1_to_P2": "P1->P2",
    "G1_to_G2": "G1->G2",
    "C0_to_C1": "C0->C1",
    "C1_to_C2": "C1->C2",
}
AXIS_SHORT = {"oxidation": "ox", "reduction": "red"}


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


def spearman(x, y) -> float:
    """Spearman rho without scipy, on the finite pairs of x and y."""
    xs, ys = np.asarray(x, float), np.asarray(y, float)
    keep = np.isfinite(xs) & np.isfinite(ys)
    xs, ys = xs[keep], ys[keep]
    if xs.size < 3:
        return float("nan")

    def rank(values):
        order = np.argsort(values, kind="mergesort")
        ranks = np.empty(values.size, float)
        ranks[order] = np.arange(values.size, dtype=float)
        # average ties
        sorted_vals = values[order]
        start = 0
        for i in range(1, sorted_vals.size + 1):
            if i == sorted_vals.size or sorted_vals[i] != sorted_vals[start]:
                if i - start > 1:
                    ranks[order[start:i]] = ranks[order[start:i]].mean()
                start = i
        return ranks

    rx, ry = rank(xs), rank(ys)
    rx = rx - rx.mean()
    ry = ry - ry.mean()
    denom = float(np.sqrt((rx ** 2).sum() * (ry ** 2).sum()))
    return float((rx * ry).sum() / denom) if denom else float("nan")


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Render figure F19.")
    parser.add_argument("--ladder", type=Path, default=LADDER_CSV)
    parser.add_argument("--outdir", type=Path, default=FIGDIR)
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    return parser.parse_args(argv)


def _ladder_panel(ax, rows):
    by_rung = {}
    for row in rows:
        by_rung.setdefault(row["rung"], {})[row["axis"]] = row
    order = sorted(
        by_rung,
        key=lambda key: np.nanmean([_f(by_rung[key][axis]["shift_std_ev"])
                                    for axis in ("oxidation", "reduction")
                                    if axis in by_rung[key]]))
    y = np.arange(len(order))
    height = 0.36
    for offset, axis, colour in ((-height / 2, "oxidation", OX_COLOR),
                                 (height / 2, "reduction", RED_COLOR)):
        values = [_f(by_rung[key].get(axis, {}).get("kendall_tau_b")) for key in order]
        ax.barh(y + offset, values, height, color=colour,
                label="oxidation" if axis == "oxidation" else "reduction")
        for yi, key, value in zip(y + offset, order, values):
            if np.isfinite(value):
                if value < 0:
                    ax.text(value - 0.02, yi, "%.2f" % value, va="center",
                            ha="right", fontsize=6.5, color="#374151")
                else:
                    ax.text(value + 0.02, yi, "%.2f" % value, va="center",
                            fontsize=6.5, color="#374151")
    ax.set_yticks(y)
    ax.set_yticklabels(["%s\nstd=%.3f" % (SHORT[key],
                                          np.nanmean([_f(by_rung[key][a]["shift_std_ev"])
                                                      for a in ("oxidation", "reduction")
                                                      if a in by_rung[key]]))
                        for key in order], fontsize=7.5)
    ax.axvline(0, color="#111827", linewidth=0.8)
    ax.set_xlim(-0.62, 1.12)
    ax.set_xlabel("Kendall tau_b of the rung", fontsize=8)
    ax.set_title("(a) every rung on the common-10 subset, ordered by shift std",
                 fontsize=9)
    ax.legend(fontsize=7.5, loc="lower right")
    ax.grid(axis="x", alpha=0.25)


def _scatter_panel(ax, rows, xkey, ykey, xlabel, title, rho, abs_x=False,
                   ylabel="Kendall tau_b"):
    for axis, colour in (("oxidation", OX_COLOR), ("reduction", RED_COLOR)):
        subset = [row for row in rows if row["axis"] == axis]
        xs = [_f(row[xkey]) for row in subset]
        if abs_x:
            xs = [abs(v) for v in xs]
        ys = [_f(row[ykey]) for row in subset]
        ax.scatter(xs, ys, s=52, color=colour, zorder=3, edgecolor="white",
                   linewidth=0.9,
                   label="oxidation" if axis == "oxidation" else "reduction")
        for row, x, y in zip(subset, xs, ys):
            if not (np.isfinite(x) and np.isfinite(y)):
                continue
            ax.annotate("%s %s" % (SHORT[row["rung"]], AXIS_SHORT[axis]), (x, y),
                        fontsize=6.2, xytext=(4, 3), textcoords="offset points",
                        color="#374151")
    xs, ys = [], []
    for row in rows:
        x = _f(row[xkey])
        if abs_x:
            x = abs(x)
        xs.append(x)
        ys.append(_f(row[ykey]))
    xs, ys = np.asarray(xs), np.asarray(ys)
    keep = np.isfinite(xs) & np.isfinite(ys)
    if keep.sum() >= 3:
        slope, intercept = np.polyfit(xs[keep], ys[keep], 1)
        grid = np.linspace(xs[keep].min(), xs[keep].max(), 50)
        ax.plot(grid, slope * grid + intercept, color=FIT_COLOR, linewidth=1.1,
                linestyle="--", zorder=1)
    ax.set_xlabel(xlabel, fontsize=8)
    ax.set_ylabel(ylabel, fontsize=8)
    ax.set_title(title, fontsize=9)
    ax.margins(x=0.20)
    ax.text(0.03, 0.04, "Spearman rho = %+.3f (n = %d)" % (rho, int(keep.sum())),
            transform=ax.transAxes, fontsize=7.5, color="#111827",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.85,
                      edgecolor="#d1d5db"))
    ax.grid(alpha=0.25)
    return rho


def main(argv=None) -> int:
    args = parse_args(argv)
    args.outdir.mkdir(parents=True, exist_ok=True)
    ladder = read_csv(args.ladder)
    rows = [row for row in ladder if row["population"] == "common10"]

    def col(key, abs_value=False):
        values = [_f(row[key]) for row in rows]
        return [abs(v) for v in values] if abs_value else values

    tau = col("kendall_tau_b")
    std = col("shift_std_ev")
    mean = col("shift_mean_ev", abs_value=True)
    unresolved = col("f_unresolved_after")
    rho_std = spearman(std, tau)
    rho_mean = spearman(mean, tau)
    rho_unres = spearman(std, unresolved)

    fig = plt.figure(figsize=(15.5, 10.5))
    grid = fig.add_gridspec(2, 2, hspace=0.30, wspace=0.22)

    _ladder_panel(fig.add_subplot(grid[0, 0]), rows)
    _scatter_panel(fig.add_subplot(grid[0, 1]), rows, "shift_std_ev",
                   "kendall_tau_b", "shift std (eV)",
                   "(b) H_var: spread decides the ranking", rho_std)
    _scatter_panel(fig.add_subplot(grid[1, 0]), rows, "shift_mean_ev",
                   "kendall_tau_b", "abs(shift mean) (eV)",
                   "(c) H_mean control: size alone does not", rho_mean, abs_x=True)
    _scatter_panel(fig.add_subplot(grid[1, 1]), rows, "shift_std_ev",
                   "f_unresolved_after", "shift std (eV)",
                   "(d) spread also drives undecidability", rho_unres,
                   ylabel="f_unresolved(after)")

    path = args.outdir / "F19_stage10_ladder.png"
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)

    lines = [
        "# Figure manifest - Week 9 / Stage 10 (F19)",
        "",
        "| figure | file | figure SHA256 | inputs (SHA256) |",
        "| --- | --- | --- | --- |",
        "| F19 | `%s` | %s | `stage10_ladder.csv` %s |"
        % (path.name, sha256(path), sha256(args.ladder)),
        "",
        "Common-10 subset only: the ten molecules (DMC, EC, DME, DOL, GBL, SL,",
        "DMSO, AN, TMP, SN) that have a valid entry at every one of the five rungs.",
        "The rung-4 / rung-5 rows use the primary m1 motif as the molecule-level",
        "representative, so `n = 10` is comparable across panels.",
        "",
        "Panel (a): tau_b of each rung and axis, rungs ordered by increasing shift",
        "std (the mean of the two axes). Reading down the list is reading the",
        "increasing order of the independent variable of (b).",
        "",
        "Panel (b): the H_var evidence. Spearman rho(shift std, tau_b) = %+.3f."
        % rho_std,
        "Panel (c): the H_mean control. Spearman rho(abs(shift mean), tau_b) = %+.3f;"
        % rho_mean,
        "the rung with the largest mean shift (P0->P1 reduction, +7.06 eV) is *not*",
        "the rung with the worst tau_b in the same direction, but the rung with the",
        "largest spread is. The two variables are themselves correlated on this",
        "small panel, so (c) is a control, not a rival model.",
        "",
        "Panel (d): Spearman rho(shift std, f_unresolved_after) = %+.3f." % rho_unres,
        "This is the mechanistic link: a wide shift spread widens the method-",
        "disagreement matrix sigma_ij, which is what `f_unresolved` counts. Note",
        "that `f_robust_inv = 0` on every one of these ten points is therefore NOT",
        "evidence that the ranking is stable -- see the report, section on reading",
        "discipline.",
        "",
        "Palette and dpi follow the other week figures (OKABE-ITO-like warm/cool",
        "pair for the oxidation/reduction axes, dpi = 160, bbox_inches = tight).",
        "",
        "`stage10_summary.md` is the narrative companion of this figure.",
        "",
    ]
    args.manifest.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("[F19] %s" % path)
    print("[manifest] %s" % args.manifest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())