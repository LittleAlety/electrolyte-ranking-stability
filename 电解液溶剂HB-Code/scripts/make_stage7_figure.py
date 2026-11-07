"""Stage 7 figures (F16, F17).

F16 -- direct vs conditional-shift (Delta) learning under extrapolation.
       Panel (a): best-per-shape Kendall tau_b under leave-one-family-out.
       Panel (b): the same chosen combinations under random / group / LOFO,
                  i.e. how much a random split flatters the score.
       Panel (c): tau_b(shift) - tau_b(direct) on the full model ladder; a
                  positive cell means the conditional-shift target helped.

F17 -- minimal expensive-information budget: n_T -> tau_b for four
       acquisition baselines, plus the last non-trivial point as a bar chart.

Labels are ASCII on purpose: the workspace has no guaranteed CJK font.

Usage:
    .venv\\Scripts\\python.exe scripts\\make_stage7_figure.py
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
WEEK7 = REPO_ROOT / "outputs" / "week7"
FIGDIR = REPO_ROOT / "outputs" / "figures"
STAGE7_CSV = WEEK7 / "stage7_ml_results.csv"
STAGE8_CSV = WEEK7 / "stage8_al_curves.csv"
MANIFEST = FIGDIR / "figure_manifest_week7_s7s8.md"

DIRECT_COLOR = "#2563eb"
SHIFT_COLOR = "#f59e0b"
SPLIT_COLORS = {"random": "#94a3b8", "group": "#38bdf8", "lofo": "#7c3aed"}
BASELINE_COLORS = {"random": "#94a3b8", "diversity": "#10b981",
                   "uncertainty": "#f59e0b", "ranking_aware": "#7c3aed"}
BASELINE_ORDER = ("random", "diversity", "uncertainty", "ranking_aware")


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
        number = float(value)
    except (TypeError, ValueError):
        return float("nan")
    return number


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Render figures F16 and F17.")
    parser.add_argument("--results", type=Path, default=STAGE7_CSV)
    parser.add_argument("--curves", type=Path, default=STAGE8_CSV)
    parser.add_argument("--outdir", type=Path, default=FIGDIR)
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    return parser.parse_args(argv)


def _short(task, feature_set, objective):
    obj = "ox" if objective == "oxidation" else "red"
    return "%s %s %s" % (task, feature_set.replace("+", "+"), obj)


def _figure_f16(results, outdir: Path) -> Path:
    keys, models = [], []
    for row in results:
        key = (row["task"], row["feature_set"], row["objective"])
        if key not in keys:
            keys.append(key)
        if row["model"] not in models:
            models.append(row["model"])

    def pick(split, shape, key, model=None):
        rows = [row for row in results
                if row["split"] == split and row["shape"] == shape
                and (row["task"], row["feature_set"], row["objective"]) == key
                and (model is None or row["model"] == model)]
        if not rows:
            return None
        return max(rows, key=lambda row: _f(row["kendall_tau_b"]))

    fig = plt.figure(figsize=(16.5, 11.0))
    grid = fig.add_gridspec(2, 2, height_ratios=[1.0, 1.0], hspace=0.55, wspace=0.22)

    labels = [_short(*key) for key in keys]
    x = np.arange(len(keys))
    width = 0.38

    ax = fig.add_subplot(grid[0, 0])
    direct_rows = [pick("lofo", "direct", key) for key in keys]
    shift_rows = [pick("lofo", "shift", key) for key in keys]
    direct = np.array([_f(row["kendall_tau_b"]) for row in direct_rows])
    shift = np.array([_f(row["kendall_tau_b"]) for row in shift_rows])
    direct_err = np.array([[direct[i] - _f(direct_rows[i]["kendall_tau_b_lo"]),
                            _f(direct_rows[i]["kendall_tau_b_hi"]) - direct[i]]
                           for i in range(len(keys))]).T
    shift_err = np.array([[shift[i] - _f(shift_rows[i]["kendall_tau_b_lo"]),
                           _f(shift_rows[i]["kendall_tau_b_hi"]) - shift[i]]
                          for i in range(len(keys))]).T
    ax.bar(x - width / 2, direct, width, yerr=np.nan_to_num(direct_err),
           capsize=2, color=DIRECT_COLOR, label="direct  P_T = f(X)")
    ax.bar(x + width / 2, shift, width, yerr=np.nan_to_num(shift_err),
           capsize=2, color=SHIFT_COLOR, label="shift  P_T = P_L + f(X)")
    for i, key in enumerate(keys):
        ax.text(i - width / 2, 0.04, direct_rows[i]["model"], rotation=90,
                ha="center", va="bottom", fontsize=5.5, color="#1e3a8a")
        ax.text(i + width / 2, 0.04, shift_rows[i]["model"], rotation=90,
                ha="center", va="bottom", fontsize=5.5, color="#92400e")
    ax.axhline(0.0, color="#111827", linewidth=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=7)
    ax.set_ylabel("Kendall tau_b (LOFO, median)")
    ax.set_title("(a) Leave-one-family-out: best model per shape\n"
                 "(bar label = selected model)", fontsize=9)
    ax.legend(fontsize=7, loc="lower right")
    ax.grid(axis="y", alpha=0.25)

    ax = fig.add_subplot(grid[0, 1])
    chosen = []
    for key in keys:
        best = None
        for shape in ("direct", "shift"):
            row = pick("lofo", shape, key)
            if row is None:
                continue
            if best is None or _f(row["kendall_tau_b"]) > _f(best[0]["kendall_tau_b"]):
                best = (row, shape)
        chosen.append(best)
    width3 = 0.26
    for offset, split in enumerate(("random", "group", "lofo")):
        values = []
        for key, best in zip(keys, chosen):
            if best is None:
                values.append(np.nan)
                continue
            row = pick(split, best[1], key, model=best[0]["model"])
            values.append(_f(row["kendall_tau_b"]) if row else np.nan)
        ax.bar(x + (offset - 1) * width3, values, width3,
               color=SPLIT_COLORS[split], label=split)
    ax.axhline(0.0, color="#111827", linewidth=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=7)
    ax.set_ylabel("Kendall tau_b (median)")
    ax.set_title("(b) Same chosen model under three splits\n"
                 "(random flatters the score)", fontsize=9)
    ax.legend(fontsize=7, loc="lower right")
    ax.grid(axis="y", alpha=0.25)

    ax = fig.add_subplot(grid[1, :])
    matrix = np.full((len(keys), len(models)), np.nan)
    for i, key in enumerate(keys):
        for j, model in enumerate(models):
            direct_row = pick("lofo", "direct", key, model=model)
            shift_row = pick("lofo", "shift", key, model=model)
            if direct_row is None or shift_row is None:
                continue
            matrix[i, j] = _f(shift_row["kendall_tau_b"]) - _f(direct_row["kendall_tau_b"])
    finite = matrix[np.isfinite(matrix)]
    limit = max(0.05, float(np.max(np.abs(finite))) if finite.size else 0.05)
    image = ax.imshow(matrix, cmap="RdBu_r", vmin=-limit, vmax=limit, aspect="auto")
    ax.set_xticks(np.arange(len(models)))
    ax.set_xticklabels(models, fontsize=8)
    ax.set_yticks(np.arange(len(keys)))
    ax.set_yticklabels(labels, fontsize=8)
    for i in range(len(keys)):
        for j in range(len(models)):
            if not np.isfinite(matrix[i, j]):
                continue
            ax.text(j, i, "%+.2f" % matrix[i, j], ha="center", va="center",
                    fontsize=7,
                    color="#111827" if abs(matrix[i, j]) < 0.6 * limit else "white")
    ax.set_title("(c) LOFO  tau_b(shift) - tau_b(direct) over the model ladder; "
                 "red = shift target better, blue = direct better", fontsize=9)
    fig.colorbar(image, ax=ax, fraction=0.025, pad=0.01)

    path = outdir / "F16_stage7_direct_vs_shift.png"
    fig.savefig(path, dpi=170, bbox_inches="tight")
    plt.close(fig)
    return path


def _figure_f17(curves, outdir: Path) -> Path:
    targets, seen = [], set()
    for row in curves:
        key = (row["task"], row["objective"])
        if key not in seen:
            seen.add(key)
            targets.append(key)
    order = {"M": 0, "E": 1, "C": 2}
    targets.sort(key=lambda key: (order.get(key[0], 9),
                                  key[1] != "oxidation"))

    fig = plt.figure(figsize=(15.0, 12.0))
    grid = fig.add_gridspec(4, 2, hspace=0.52, wspace=0.20)
    for position, (task, objective) in enumerate(targets):
        if position >= 6:
            break
        ax = fig.add_subplot(grid[position // 2, position % 2])
        for baseline in BASELINE_ORDER:
            rows = sorted([row for row in curves if row["task"] == task
                           and row["objective"] == objective
                           and row["baseline"] == baseline],
                          key=lambda row: int(row["n_T"]))
            if not rows:
                continue
            xs = [int(row["n_T"]) for row in rows]
            ys = [_f(row["kendall_tau_b"]) for row in rows]
            lo = [_f(row["kendall_tau_b_lo"]) for row in rows]
            hi = [_f(row["kendall_tau_b_hi"]) for row in rows]
            ax.plot(xs, ys, marker="o", markersize=3, linewidth=1.6,
                    color=BASELINE_COLORS[baseline], label=baseline)
            ax.fill_between(xs, lo, hi, color=BASELINE_COLORS[baseline], alpha=0.12)
        ax.axhline(0.0, color="#111827", linewidth=0.8)
        ax.axhline(0.8, color="#ef4444", linewidth=0.8, linestyle="--")
        ax.set_xlabel("n_T (expensive labels bought)", fontsize=8)
        ax.set_ylabel("Kendall tau_b", fontsize=8)
        pool = max(int(row["n_T"]) for row in curves
                   if row["task"] == task and row["objective"] == objective)
        ax.set_title("%s / %s   (pool n = %d)" % (task, objective, pool), fontsize=9)
        ax.tick_params(labelsize=7)
        ax.grid(alpha=0.25)
        if position == 0:
            ax.legend(fontsize=7, loc="lower right")

    ax = fig.add_subplot(grid[3, :])
    labels, series = [], []
    for task, objective in targets:
        horizon = sorted({int(row["n_T"]) for row in curves
                          if row["task"] == task and row["objective"] == objective})
        if not horizon:
            continue
        previous = horizon[-2] if len(horizon) > 1 else horizon[-1]
        labels.append("%s/%s\nn_T=%d" % (task, objective, previous))
        series.append({row["baseline"]: _f(row["kendall_tau_b"]) for row in curves
                       if row["task"] == task and row["objective"] == objective
                       and int(row["n_T"]) == previous})
    x = np.arange(len(labels))
    width = 0.2
    for offset, baseline in enumerate(BASELINE_ORDER):
        values = [entry.get(baseline, np.nan) for entry in series]
        ax.bar(x + (offset - 1.5) * width, values, width,
               color=BASELINE_COLORS[baseline], label=baseline)
    ax.axhline(0.8, color="#ef4444", linewidth=0.9, linestyle="--")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=7)
    ax.set_ylabel("Kendall tau_b (median)", fontsize=8)
    ax.set_title("(g) Last non-trivial point: one expensive label short of the full set",
                 fontsize=9)
    ax.legend(fontsize=7, ncol=4, loc="lower right")
    ax.grid(axis="y", alpha=0.25)

    path = outdir / "F17_stage8_active_learning.png"
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)
    return path


def main(argv=None) -> int:
    args = parse_args(argv)
    args.outdir.mkdir(parents=True, exist_ok=True)
    results = read_csv(args.results)
    curves = read_csv(args.curves)
    f16 = _figure_f16(results, args.outdir)
    f17 = _figure_f17(curves, args.outdir)

    lines = ["# Figure manifest - Week 7 / Stage 7+8 (F16, F17)", "",
             "| figure | file | figure SHA256 | inputs (SHA256) |",
             "| --- | --- | --- | --- |",
             "| F16 | `%s` | %s | `stage7_ml_results.csv` %s |"
             % (f16.name, sha256(f16), sha256(args.results)),
             "| F17 | `%s` | %s | `stage8_al_curves.csv` %s |"
             % (f17.name, sha256(f17), sha256(args.curves)),
             "",
             "F16 panel (a): the best model of each shape under leave-one-family-out; "
             "whiskers are the bootstrap/median interval stored in the results CSV. "
             "Panel (b): the same selected combination read under random, group and "
             "LOFO splits - the gap between the grey and purple bar is the optimism "
             "of a random split. Panel (c): tau_b(shift) - tau_b(direct) for every "
             "model in the prereg complexity ladder.",
             "",
             "F17: n_T -> Kendall tau_b for random / diversity / uncertainty / "
             "ranking-aware acquisition, median over 20 frozen-seed repeats with a "
             "2.5-97.5 percentile band; the dashed line is tau_b = 0.8. The bottom "
             "panel is the last non-trivial point (n_T = n - 1), where every curve "
             "still has one unlabelled candidate. The trivial endpoint n_T = n "
             "(tau_b = 1 by construction) is deliberately not plotted.",
             ""]
    args.manifest.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("[F16] %s" % f16)
    print("[F17] %s" % f17)
    print("[manifest] %s" % args.manifest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())