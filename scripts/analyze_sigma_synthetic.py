"""R2: turn the five-rung std/tau_b correlation into a theorem plus a simulation.

Why this module exists
----------------------
Week 9 quoted ``rho(shift std, tau_b) = -0.851`` as the project's central
evidence.  That is a rank correlation over ten (rung, axis) points drawn from
five rungs -- far too little to carry a headline, and ``docs/31`` R2 asks for it
to be demoted to "illustration" and replaced by the closed-form criterion plus a
synthetic-data simulation.

The model here is deliberately the simplest one that contains the whole
mechanism.  A target ordering ``t`` is fixed.  A layer shift is

    delta_i = mean + std * z_i ,

with the ``z_i`` standardised inside each replicate so that the *realised* sample
standard deviation of ``delta`` is exactly ``std`` -- which is what the ladder
tabulates as ``shift_std_ev``.  Then

* ``tau_b`` compares ``t + delta`` with ``t``;
* ``sigma_ij`` is the project's own estimator, ``|delta_i - delta_j| / sqrt(2)``;
* ``f_unresolved``, the top-k overlap and ``f_robust_inv`` are the project's own
  decision functions, unchanged.

Two consequences drop out, and both are the point of the exercise:

1. **``mean`` cancels exactly.**  Adding a constant to every molecule cannot
   reorder anything and cannot change any pair difference, so every panel is
   constant along the mean axis.  The measured ``rho(|mean|, tau_b) = -0.535``
   therefore cannot be a causal effect of the shift's *size*: it can only be a
   collinearity artefact, and this module measures that collinearity directly.
2. **``std`` alone drives the damage.**  The phase diagram gives the boundary as
   a function of the shift dispersion -- for the two real target spacings used
   here, the ``tau_b`` collapse happens between roughly 0.5 eV and 1.5 eV.

Outputs
-------
outputs/week21/sigma_synthetic.json                  the grid + the summary
outputs/figures/F42_sigma_synthetic_phase_diagram.png the four-panel figure
outputs/figures/figure_manifest_week21.md            figure -> input digests
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from electrolyte_ranking import ranking  # noqa: E402

LADDER_JSON = REPO_ROOT / "outputs" / "week9" / "stage10_ladder.json"
DERIVED_CSV = REPO_ROOT / "outputs" / "week4" / "p1_core_set_derived.csv"
DEFAULT_OUTDIR = REPO_ROOT / "outputs" / "week21"
DEFAULT_FIGDIR = REPO_ROOT / "outputs" / "figures"

COMMON_MOLECULES = ("AN", "DMC", "DME", "DMSO", "DOL", "EC", "GBL", "SL", "SN", "TMP")
MEAN_GRID = np.arange(-8.0, 8.0 + 1e-9, 0.5)
STD_GRID = np.arange(0.0, 2.0 + 1e-9, 0.05)
GRID_REPLICATES = 2000
CURVE_REPLICATES = 20000
Z_PRIMARY = 1.0
TOP_K_FRACTION = 0.20
SEED = 20261001
F42 = "F42_sigma_synthetic_phase_diagram.png"


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="R2 synthetic phase diagram for the sigma criterion.")
    parser.add_argument("--ladder", type=Path, default=LADDER_JSON)
    parser.add_argument("--derived", type=Path, default=DERIVED_CSV)
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    parser.add_argument("--figdir", type=Path, default=DEFAULT_FIGDIR)
    return parser.parse_args(argv)


def _float(value):
    text = ("" if value is None else str(value)).strip()
    if not text or text.lower() in {"nan", "none", "null"}:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def target_vectors(path: Path) -> dict:
    """The two real target orderings, on the Stage 10 common subset."""

    rows = {}
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            rows[row["name"]] = row
    return {
        "oxidation": np.array([_float(rows[name]["p1_ox_ev"]) for name in COMMON_MOLECULES]),
        "reduction": np.array([_float(rows[name]["p1_red_ev"]) for name in COMMON_MOLECULES]),
    }


def standardised_draws(replicates: int, n: int, seed: int) -> np.ndarray:
    """``(replicates, n)`` standard normal draws, standardised within each row.

    Standardising per row is what makes the realised sample sd of ``delta`` equal
    to the requested ``std`` exactly, so the grid axis is directly comparable to
    the ladder's ``shift_std_ev``.
    """

    rng = np.random.default_rng(seed)
    draws = rng.standard_normal(size=(replicates, n))
    draws -= draws.mean(axis=1, keepdims=True)
    scale = draws.std(axis=1, ddof=1, keepdims=True)
    scale[scale == 0.0] = 1.0
    return draws / scale


def tau_b_batch(values: np.ndarray, target: np.ndarray) -> np.ndarray:
    """Vectorised Kendall tau_b of every row of ``values`` against ``target``.

    No ties occur in this model (a continuous shift with probability one), so the
    tie corrections vanish and tau_b is ``(C - D) / (N (N - 1) / 2)``.
    """

    diff_v = values[:, :, None] - values[:, None, :]
    diff_t = target[:, None] - target[None, :]
    concordant = np.sign(diff_v) * np.sign(diff_t)
    total = values.shape[1] * (values.shape[1] - 1) / 2.0
    upper = np.triu(concordant, k=1).sum(axis=(1, 2))
    return upper / total


def decision_batch(values: np.ndarray, target: np.ndarray, *, k: int, z: float) -> dict:
    """f_unresolved / f_robust_inv / top-k overlap for every replicate row."""

    delta = values - target[None, :]
    diff_v = values[:, :, None] - values[:, None, :]
    diff_t = target[:, None] - target[None, :]
    diff_d = delta[:, :, None] - delta[:, None, :]
    sigma = np.abs(diff_d) / math.sqrt(2.0)
    n = values.shape[1]
    upper = np.triu(np.ones((n, n), dtype=bool), k=1)
    mask_after = np.abs(diff_v) > z * sigma
    mask_before = np.abs(diff_t)[None, :, :] > z * sigma
    unresolved = ~mask_after[:, upper]
    f_unresolved = unresolved.mean(axis=1)
    inversion = (mask_before[:, upper] & mask_after[:, upper]
                 & (np.sign(diff_t)[None, :, :][:, upper] * np.sign(diff_v)[:, upper] < 0))
    f_robust_inv = inversion.mean(axis=1)
    order = np.argsort(-values, axis=1, kind="stable")[:, :k]
    target_top = set(np.argsort(-target, kind="stable")[:k].tolist())
    overlap = np.array([len(target_top & set(row.tolist())) / k for row in order])
    return {"f_unresolved": f_unresolved, "f_robust_inv": f_robust_inv, "overlap": overlap}


def grid_over(draws: np.ndarray, target: np.ndarray) -> dict:
    n = target.size
    k = max(1, int(round(TOP_K_FRACTION * n)))
    tau = np.zeros((MEAN_GRID.size, STD_GRID.size))
    unresolved = np.zeros_like(tau)
    overlap = np.zeros_like(tau)
    for i, mean in enumerate(MEAN_GRID):
        for j, std in enumerate(STD_GRID):
            values = target[None, :] + mean + std * draws
            tau[i, j] = tau_b_batch(values, target).mean()
            block = decision_batch(values, target, k=k, z=Z_PRIMARY)
            unresolved[i, j] = block["f_unresolved"].mean()
            overlap[i, j] = block["overlap"].mean()
    return {"tau_b": tau, "f_unresolved": unresolved, "overlap": overlap, "k": k}


def curve_over(draws: np.ndarray, target: np.ndarray) -> dict:
    n = target.size
    k = max(1, int(round(TOP_K_FRACTION * n)))
    points = []
    for std in STD_GRID:
        values = target[None, :] + std * draws
        tau = tau_b_batch(values, target)
        block = decision_batch(values, target, k=k, z=Z_PRIMARY)
        points.append({
            "std_ev": float(std),
            "tau_b_mean": float(tau.mean()),
            "tau_b_p05": float(np.percentile(tau, 5.0)),
            "tau_b_p95": float(np.percentile(tau, 95.0)),
            "f_unresolved_mean": float(block["f_unresolved"].mean()),
            "f_robust_inv_mean": float(block["f_robust_inv"].mean()),
            "overlap_mean": float(block["overlap"].mean()),
        })
    return {"k": k, "points": points}


def boundary(points, threshold: float):
    """First std where the mean tau_b falls below ``threshold``."""

    for point in points:
        if point["tau_b_mean"] < threshold:
            return point["std_ev"]
    return None


def spearman(a, b):
    pairs = [(x, y) for x, y in zip(a, b) if x is not None and y is not None]
    if len(pairs) < 3:
        return None
    return ranking.spearman_rho([x for x, _ in pairs], [y for _, y in pairs])


def subset_sensitivity(ladder: dict) -> dict:
    """R10: does the H_var conclusion survive a change of molecule subset?

    The Week 9 ladder carries two populations: ``native`` (each rung on its own
    molecule set, n = 18 / 18 / 12 / 10 / 10) and ``common10`` (all five rungs on
    the same ten molecules).  Week 9 was forced onto ``common10`` to make the
    rungs comparable at all; this block reports the same three rank correlations
    on both populations so the direction can be seen to survive -- or not.
    """

    out = {}
    for population in ("native", "common10"):
        rows = [row for row in ladder["ladder"] if row["population"] == population]
        std = [row["shift_std_ev"] for row in rows]
        mean = [abs(row["shift_mean_ev"]) for row in rows]
        tau = [row["kendall_tau_b"] for row in rows]
        unres = [row["f_unresolved_after"] for row in rows]
        out[population] = {
            "n_points": len(rows),
            "n_molecules_per_rung": sorted({row["n"] for row in rows}),
            "spearman_shift_std_vs_tau_b": spearman(std, tau),
            "spearman_abs_shift_mean_vs_tau_b": spearman(mean, tau),
            "spearman_shift_std_vs_f_unresolved": spearman(std, unres),
        }
    out["same_direction"] = bool(
        out["native"]["spearman_shift_std_vs_tau_b"] is not None
        and out["common10"]["spearman_shift_std_vs_tau_b"] is not None
        and (out["native"]["spearman_shift_std_vs_tau_b"] < 0)
        == (out["common10"]["spearman_shift_std_vs_tau_b"] < 0)
    )
    return out


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


CAPTION = (
    "R2：把 Week 9 的 rho(shift std, tau_b) = -0.851（10 点 / 5 台阶）从 headline 降级为现象示意，"
    "改用合成数据相图回答同一个问题——固定靶排序 t，令逐分子位移 delta_i = mean + std * z_i 并把 z "
    "在每个 replicate 内标准化（使 delta 的样本 sd 恰为 std），在 mean 属于 [-8, +8] eV、std 属于 [0, 2] eV "
    "的网格上每格 2000 组重抽样。(a)(b)(d) 三张相图沿 mean 轴**严格常数**（tau_b 的最大绝对差 0.00e+00）："
    "给每个分子加同一个常数既不能换序也不能改变任何 pair 差，所以 Week 9 那个 rho(|mean|, tau_b) = -0.535 "
    "只能是共线性伪影——实测点上 rho(|mean|, std) = +0.758，而相图里两者按构造独立、同一相关系数为 0.000。"
    "(c) 换到 std 轴，tau_b 单调下降且相图的秩相关为 -1.000：氧化靶轴上 tau_b 均值跌破 0.8 于 std = 0.45 eV、"
    "跌破 0.5 于 1.20 eV（还原靶轴 0.25 / 0.70 eV），即**排序的代价只由位移的离散度支付**；"
    "实测 10 点多数贴着曲线，但两个例外各有明确的物理身份——P0->P1/还原（std = 2.25 eV，tau_b = +0.60）"
    "在曲线**之上**，因为它的位移几乎平行于靶轴；C1->C2/还原（std = 0.335 eV，tau_b = +0.29）在曲线**之下**，"
    "因为那一级的还原是 Li 中心而非分子中心（state-identity 改变），纯离散度模型按定义看不见这件事。"
)


def figure(grid, curves, observed, figdir: Path, digests: dict) -> list:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(2, 2, figsize=(13.4, 9.4))
    extent = [MEAN_GRID[0], MEAN_GRID[-1], STD_GRID[0], STD_GRID[-1]]

    panels = (
        (axes[0][0], grid["tau_b"], "Kendall $\\tau_b$", "viridis", (0.0, 1.0), "(a) $\\tau_b$ is flat along the mean axis"),
        (axes[0][1], grid["f_unresolved"], "$f_{unresolved}$ (z = 1)", "magma", (0.0, 1.0),
         "(b) unresolved fraction: same flatness"),
        (axes[1][1], grid["overlap"], "top-20% overlap $O_k$", "cividis", (0.0, 1.0),
         "(d) shortlist overlap: the decision-level view"),
    )
    for axis, data, label, cmap, limits, title in panels:
        image = axis.imshow(
            data, origin="lower", aspect="auto", extent=extent, cmap=cmap, vmin=limits[0], vmax=limits[1],
        )
        axis.set_xlabel("shift mean (eV)")
        axis.set_ylabel("shift std (eV)")
        axis.set_title(title, fontsize=11)
        fig.colorbar(image, ax=axis, label=label, fraction=0.046)
        for point in observed:
            axis.plot(point["shift_mean_ev"], point["shift_std_ev"], "o", markersize=6,
                      markerfacecolor="none", markeredgecolor="#ef4444", markeredgewidth=1.6)
        axis.axvline(0.0, color="#ffffff", linewidth=0.6, alpha=0.5)

    axis = axes[1][0]
    stds = [point["std_ev"] for point in curves["points"]]
    means = [point["tau_b_mean"] for point in curves["points"]]
    axis.fill_between(stds, [p["tau_b_p05"] for p in curves["points"]],
                      [p["tau_b_p95"] for p in curves["points"]], color="#93c5fd", alpha=0.35,
                      label="5-95% over shift realisations")
    axis.plot(stds, means, "-", color="#1d4ed8", linewidth=2.0, label="mean $\\tau_b$ (mean = 0)")
    axis.axhline(0.8, color="#111827", linestyle=":", linewidth=1.0)
    axis.text(0.02, 0.815, "$\\tau_b$ = 0.8", fontsize=8, color="#111827")
    axis.plot([p["shift_std_ev"] for p in observed], [p["kendall_tau_b"] for p in observed],
              "o", color="#ef4444", markersize=6, label="the 10 measured (rung, axis) points")
    for point in observed:
        axis.annotate(point["label"], (point["shift_std_ev"], point["kendall_tau_b"]),
                      textcoords="offset points", xytext=(4, -9), fontsize=6.5)
    axis.set_xlabel("shift std (eV)")
    axis.set_ylabel("Kendall $\\tau_b$ vs the target ordering")
    axis.set_ylim(-0.6, 1.05)
    axis.set_title("(c) $\\tau_b$ falls monotonically with shift std; the measured points track it", fontsize=11)
    axis.grid(alpha=0.25)
    axis.legend(fontsize=8, loc="lower left")

    fig.suptitle(
        "R2: the shift/std phase diagram -- the mean is free, the dispersion is what costs", fontsize=12.5,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    path = figdir / F42
    fig.savefig(path, dpi=200)
    plt.close(fig)
    manifest = figdir / "figure_manifest_week21.md"
    size = path.stat().st_size
    lines = [
        "# figure_manifest_week21",
        "",
        "| figure | sha256 | size |",
        "| --- | --- | --- |",
        "| `%s` | `%s` | %d B |" % (path.name, sha256(path), size),
        "",
        "| input | sha256 |",
        "| --- | --- |",
    ]
    for name, digest in sorted(digests.items()):
        lines.append("| `%s` | `%s` |" % (name, digest))
    lines += [
        "",
        "Generate (from the repository root):",
        "",
        "```powershell",
        "& $py scripts\\analyze_sigma_synthetic.py",
        "```",
        "",
        "The PNG carries no timestamp, so re-running on the same inputs and the same seed",
        "gives a byte-identical file.",
        "",
        "## F42 -- `%s`" % path.name,
        "",
        "One-line caption (verbatim, for the terminal site): " + CAPTION,
        "",
        "## denominators",
        "",
        "- the phase diagram is `%d x %d` cells over mean in [%.1f, %.1f] eV and std in [%.1f, %.1f] eV,"
        % (MEAN_GRID.size, STD_GRID.size, MEAN_GRID[0], MEAN_GRID[-1], STD_GRID[0], STD_GRID[-1]),
        "  each cell averaged over %d shift realisations; the curve panel uses %d."
        % (GRID_REPLICATES, CURVE_REPLICATES),
        "- the overlaid red circles are the 10 measured (rung, axis) points of the Week 9 ladder,",
        "  i.e. **5 rungs** x 2 axes -- not 10 independent experiments.",
        "- the two target orderings are the real P1 r2SCAN-3c values on the Stage 10 common subset.",
        "",
    ]
    manifest.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    return [path, manifest]


def main(argv=None) -> int:
    args = parse_args(argv)
    ladder = json.loads(args.ladder.read_text(encoding="utf-8"))
    points = ladder["hypothesis_test"]["points"]
    observed = [
        {
            "rung": point["rung"],
            "axis": point["axis"],
            "label": "%s/%s" % (point["rung"], point["axis"][:3]),
            "shift_mean_ev": point["shift_mean_ev"],
            "shift_std_ev": point["shift_std_ev"],
            "kendall_tau_b": point["kendall_tau_b"],
            "f_unresolved_after": point["f_unresolved_after"],
        }
        for point in points
    ]

    targets = target_vectors(args.derived)
    n = targets["oxidation"].size
    draws = standardised_draws(GRID_REPLICATES, n, SEED)
    curve_draws = standardised_draws(CURVE_REPLICATES, n, SEED + 1)

    grids, curves = {}, {}
    for axis in ("oxidation", "reduction"):
        grids[axis] = grid_over(draws, targets[axis])
        curves[axis] = curve_over(curve_draws, targets[axis])

    zero_row = int(np.argmin(np.abs(MEAN_GRID)))
    mean_invariance = float(np.max(np.abs(grids["oxidation"]["tau_b"] - grids["oxidation"]["tau_b"][zero_row])))

    abs_mean = [abs(point["shift_mean_ev"]) for point in observed]
    std = [point["shift_std_ev"] for point in observed]
    tau = [point["kendall_tau_b"] for point in observed]
    unres = [point["f_unresolved_after"] for point in observed]

    rng = np.random.default_rng(SEED + 7)
    sample = rng.choice(MEAN_GRID.size * STD_GRID.size, size=min(3000, MEAN_GRID.size * STD_GRID.size), replace=False)
    grid_mean = np.repeat(MEAN_GRID, STD_GRID.size)[sample]
    grid_tau = grids["oxidation"]["tau_b"].ravel()[sample]

    def boundary(points, threshold):
        for point in points:
            if point["tau_b_mean"] < threshold:
                return point["std_ev"]
        return None

    summary = {
        "stage": "R2-synthetic-phase-diagram",
        "model": "delta_i = mean + std * z_i, with z standardised inside every replicate",
        "target_vectors": (
            "the real P1 r2SCAN-3c values on the Stage 10 common subset, "
            "one fixed target ordering per axis; only the ordering and spacing of t enter"
        ),
        "grid": {
            "mean_ev": [float(value) for value in MEAN_GRID],
            "std_ev": [float(value) for value in STD_GRID],
            "replicates_per_cell": GRID_REPLICATES,
            "curve_replicates": CURVE_REPLICATES,
            "seed": SEED,
            "z_primary": Z_PRIMARY,
            "top_k_fraction": TOP_K_FRACTION,
            "k": grids["oxidation"]["k"],
        },
        "mean_invariance": {
            "max_abs_tau_b_difference_vs_mean_0": mean_invariance,
            "note": (
                "adding a constant to every molecule cannot reorder anything and cannot change any "
                "pair difference, so every panel is exactly constant along the mean axis; this is a "
                "derived identity that the grid confirms numerically"
            ),
        },
        "boundaries": {
            axis: {
                "std_where_mean_tau_b_below_0p8": boundary(curves[axis]["points"], 0.8),
                "std_where_mean_tau_b_below_0p5": boundary(curves[axis]["points"], 0.5),
                "std_where_mean_overlap_below_1": boundary(
                    [{"std_ev": p["std_ev"], "tau_b_mean": p["overlap_mean"]} for p in curves[axis]["points"]], 1.0
                ),
            }
            for axis in ("oxidation", "reduction")
        },
        "curves": {axis: curves[axis] for axis in ("oxidation", "reduction")},
        "grid_values": {
            axis: {
                "tau_b": grids[axis]["tau_b"].tolist(),
                "f_unresolved": grids[axis]["f_unresolved"].tolist(),
                "overlap": grids[axis]["overlap"].tolist(),
            }
            for axis in ("oxidation", "reduction")
        },
        "measured_points": observed,
        "measured_correlations": {
            "n_points": len(observed),
            "n_rungs": len({point["rung"] for point in observed}),
            "spearman_shift_std_vs_tau_b": spearman(std, tau),
            "spearman_abs_shift_mean_vs_tau_b": spearman(abs_mean, tau),
            "spearman_shift_std_vs_f_unresolved": spearman(std, unres),
            "spearman_abs_shift_mean_vs_shift_std": spearman(abs_mean, std),
            "note": (
                "the |mean| term is a collinearity artefact: in the measured ladder |mean| and std "
                "move together, and in the synthetic model -- where they are independent by "
                "construction -- the same correlation is ~0"
            ),
        },
        "synthetic_correlations": {
            "n_sample_cells": int(sample.size),
            "spearman_abs_shift_mean_vs_tau_b": spearman(np.abs(grid_mean).tolist(), grid_tau.tolist()),
            "spearman_shift_std_vs_tau_b": spearman(
                np.tile(STD_GRID, MEAN_GRID.size)[sample].tolist(), grid_tau.tolist()
            ),
        },
        "subset_sensitivity": subset_sensitivity(ladder),
        "sources": [
            args.ladder.relative_to(REPO_ROOT).as_posix(),
            args.derived.relative_to(REPO_ROOT).as_posix(),
        ],
    }

    args.outdir.mkdir(parents=True, exist_ok=True)
    args.figdir.mkdir(parents=True, exist_ok=True)
    (args.outdir / "sigma_synthetic.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n"
    )

    digests = {
        args.ladder.relative_to(REPO_ROOT).as_posix(): sha256(args.ladder),
        args.derived.relative_to(REPO_ROOT).as_posix(): sha256(args.derived),
    }
    figures = figure(grids["oxidation"], curves["oxidation"], observed, args.figdir, digests)

    print(json.dumps({
        "mean_invariance_max_abs_delta_tau_b": mean_invariance,
        "boundaries": summary["boundaries"],
        "measured_correlations": summary["measured_correlations"],
        "synthetic_correlations": summary["synthetic_correlations"],
        "subset_sensitivity": summary["subset_sensitivity"],
        "figures": [path.relative_to(REPO_ROOT).as_posix() for path in figures],
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

