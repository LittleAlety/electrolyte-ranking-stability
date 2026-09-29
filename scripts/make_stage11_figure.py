"""Stage 11 figures (F20, F21) -- anatomy of the pair uncertainty sigma_ij.

F20 answers "what is sigma, exactly?":

    (a) sigma_ij against |delta_i - delta_j| / sqrt(2)   -> T1, an identity
    (b) the secant-slope distribution q_ij per rung        -> T4, closed form
    (c) f_unresolved observed against the closed form      -> T4, exact
    (d) AUC of every cheap predictor of a shortlist rewrite

F21 shows the counterfactual controls that fix the causal direction:

    (a) the linear-shift phase diagram in b = d(delta)/d(target)
    (b) a monotone f-Lipschitz shift: tau_b = 1, f_unresolved = 0, sigma grown
    (c) shift inflation and rigid offset side by side
    (d) how much the molecule subset itself decides (tau_b vs N)

Labels are ASCII on purpose: the workspace has no guaranteed CJK font.

Usage:
    .venv\\Scripts\\python.exe scripts\\make_stage11_figure.py
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
WEEK10 = REPO_ROOT / "outputs" / "week10"
FIGDIR = REPO_ROOT / "outputs" / "figures"
ANATOMY_JSON = WEEK10 / "stage11_sigma_anatomy.json"
ANATOMY_CSV = WEEK10 / "stage11_sigma_anatomy.csv"

OX_COLOR = "#b45309"
RED_COLOR = "#1d4ed8"
FIT_COLOR = "#6b7280"
WARN_COLOR = "#b91c1c"
OK_COLOR = "#047857"

SHORT = {
    "P0_to_P1": "P0->P1",
    "P1_to_P2": "P1->P2",
    "G1_to_G2": "G1->G2",
    "C0_to_C1": "C0->C1",
    "C1_to_C2": "C1->C2",
}
AXIS_COLOR = {"oxidation": OX_COLOR, "reduction": RED_COLOR}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Render figures F20 and F21.")
    parser.add_argument("--anatomy", type=Path, default=ANATOMY_JSON)
    parser.add_argument("--outdir", type=Path, default=FIGDIR)
    parser.add_argument("--manifest", type=Path,
                        default=FIGDIR / "figure_manifest_week10_stage11.md")
    return parser.parse_args(argv)


def panel_t1(ax, payload):
    xs, ys = [], []
    for key, block in payload["pair_detail"].items():
        delta = np.asarray(block["delta_ev"], float)
        iu = np.triu_indices(delta.size, 1)
        closed = np.abs(delta[:, None] - delta[None, :])[iu] / np.sqrt(2.0)
        sig = np.asarray(block["sigma_ij"], float)
        xs.extend(closed)
        ys.extend(sig)
    xs, ys = np.asarray(xs), np.asarray(ys)
    ax.loglog(xs, ys, "o", markersize=3.6, color="#1f2937", alpha=0.65,
              markeredgewidth=0)
    lo = max(min(xs.min(), ys.min()), 1e-4)
    hi = max(xs.max(), ys.max()) * 1.4
    ax.plot([lo, hi], [lo, hi], "-", color=WARN_COLOR, linewidth=1.2,
            label="y = x")
    err = payload["theorems"]["T1_sigma_is_shift_difference"]["max_abs_err_ev"]
    ax.set_xlabel("abs(delta_i - delta_j) / sqrt(2)   [eV]", fontsize=8)
    ax.set_ylabel("sigma_ij   [eV]", fontsize=8)
    ax.set_title("(a) T1: sigma is the shift difference  (max err %.1e eV)" % err,
                 fontsize=9)
    ax.legend(fontsize=7, loc="upper left")
    ax.grid(alpha=0.25, which="both")
    return err


def panel_q(ax, payload):
    crit1 = payload["critical_slope_z1"]
    crit2 = payload["critical_slope_z1p96"]
    rows = sorted(payload["rows"], key=lambda r: r["q_median"])
    for index, row in enumerate(rows):
        block = payload["pair_detail"]["%s|%s" % (row["rung"], row["axis"])]
        q = np.asarray(block["q_ij"], float)
        jitter = (np.random.default_rng(11 + index).random(q.size) - 0.5) * 0.34
        ax.semilogx(q, index + jitter, ".", markersize=3.0,
                    color=AXIS_COLOR[row["axis"]], alpha=0.75)
        ax.semilogx([row["q_median"]], [index], "D", markersize=5.0,
                    color="#111827", zorder=5)
    ax.axvline(crit1, color=OK_COLOR, linestyle="--", linewidth=1.1)
    ax.axvline(crit2, color=WARN_COLOR, linestyle=":", linewidth=1.1)
    ax.text(crit1 * 1.06, len(rows) - 0.4, "sqrt(2)/z = %.3f (z=1)" % crit1,
            fontsize=7, color=OK_COLOR, rotation=90, va="top")
    ax.text(crit2 * 1.06, len(rows) - 0.4, "sqrt(2)/z = %.3f (z=1.96)" % crit2,
            fontsize=7, color=WARN_COLOR, rotation=90, va="top")
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels(["%s %s" % (SHORT[row["rung"]], row["axis"][:3])
                        for row in rows], fontsize=7)
    ax.set_ylim(-0.7, len(rows) - 0.3)
    ax.set_xlabel("q_ij = abs(d_i - d_j) / abs(dP_ij)   [dimensionless slope]", fontsize=8)
    ax.set_title("(b) T4: resolution is a secant-slope tail  (diamond = median)",
                 fontsize=9)
    ax.grid(alpha=0.25, axis="x")


def panel_closed_form(ax, payload):
    obs, pred, colours = [], [], []
    for row in payload["rows"]:
        obs.extend([row["f_unresolved_p1_observed"], row["f_unresolved_p1_z1p96_observed"]])
        pred.extend([row["f_unresolved_p1_closedform"], row["f_unresolved_p1_z1p96_closedform"]])
        colours.extend([AXIS_COLOR[row["axis"]]] * 2)
    ax.plot([-0.03, 1.03], [-0.03, 1.03], "-", color=WARN_COLOR, linewidth=1.1,
            label="y = x")
    ax.scatter(obs, pred, s=34, c=colours, edgecolor="#111827", linewidth=0.5,
               zorder=4)
    err = max(payload["theorems"]["T4_closed_form_unresolved"]["max_abs_err_z1"],
              payload["theorems"]["T4_closed_form_unresolved"]["max_abs_err_z1p96"])
    ax.set_xlim(-0.05, 1.05)
    ax.set_ylim(-0.05, 1.05)
    ax.set_xlabel("f_unresolved observed (layer P1)", fontsize=8)
    ax.set_ylabel("Pr( q_ij > sqrt(2)/z )   [closed form]", fontsize=8)
    ax.set_title("(c) T4: 20 points, z = 1 and z = 1.96  (max err %.1e)" % err,
                 fontsize=9)
    ax.legend(fontsize=7, loc="upper left")
    ax.grid(alpha=0.25)


def panel_auc(ax, payload):
    table = [item for item in payload["predictability"]["table"]
             if item.get("auc") is not None]
    table.sort(key=lambda item: item["auc"])
    names = [item["predictor"] for item in table]
    aucs = [item["auc"] for item in table]
    colours = [WARN_COLOR if name == "ols_slope_b" else "#9ca3af" for name in names]
    y = np.arange(len(table))
    ax.barh(y, aucs, color=colours, height=0.62)
    for yi, value, item in zip(y, aucs, table):
        ax.text(value + 0.012, yi, "%.3f  (p=%.3f)" % (value, item["auc_exact_permutation_p"]),
                va="center", fontsize=6.5, color="#374151")
    ax.axvline(0.5, color="#111827", linestyle="--", linewidth=1.0)
    ax.set_yticks(y)
    ax.set_yticklabels(names, fontsize=7)
    ax.set_xlim(0.0, 1.28)
    ax.set_xlabel("AUC for predicting a top-2 shortlist rewrite", fontsize=8)
    ax.set_title("(d) the predictor is the SIGNED slope, not the magnitude",
                 fontsize=9)
    ax.text(0.52, 0.06, "share_parallel and share_residual are\ncomplements (1 - x): "
                        "the residual share\nis anti-predictive under its natural "
                        "hypothesis",
            transform=ax.transAxes, fontsize=6.2, color="#374151",
            bbox=dict(boxstyle="round", fc="#f9fafb", ec="#d1d5db", lw=0.6))
    ax.grid(alpha=0.25, axis="x")


def figure_f20(payload, outdir: Path):
    fig, axes = plt.subplots(2, 2, figsize=(11.2, 8.4))
    panel_t1(axes[0][0], payload)
    panel_q(axes[0][1], payload)
    panel_closed_form(axes[1][0], payload)
    panel_auc(axes[1][1], payload)
    fig.suptitle("F20  sigma_ij anatomy: four exact statements about the project's "
                 "uncertainty budget (common-10)", fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.965))
    path = outdir / "F20_sigma_anatomy.png"
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)
    return path


def panel_phase(ax, payload):
    rows = payload["controls"]["linear_shift"]
    b = np.asarray([item["slope_b"] for item in rows], float)
    tau = np.asarray([item["tau_b"] for item in rows], float)
    f1 = np.asarray([item["f_unresolved_z1"] for item in rows], float)
    f196 = np.asarray([item["f_unresolved_z1p96"] for item in rows], float)
    order = np.argsort(b)
    b, tau, f1, f196 = b[order], tau[order], f1[order], f196[order]
    ax.step(b, tau, where="mid", color="#111827", linewidth=1.6, label="tau_b")
    ax.step(b, f1, where="mid", color=OK_COLOR, linewidth=1.4,
            label="f_unresolved (z=1)")
    ax.step(b, f196, where="mid", color=WARN_COLOR, linewidth=1.1, linestyle="--",
            label="f_unresolved (z=1.96)")
    for value, colour, label in ((-1.0, "#111827", "rank flip at b = -1"),
                                 (-np.sqrt(2.0), FIT_COLOR, "-sqrt(2)"),
                                 (-np.sqrt(2.0) / 1.96, FIT_COLOR, "-sqrt(2)/1.96"),
                                 (np.sqrt(2.0) / 1.96, FIT_COLOR, "+sqrt(2)/1.96"),
                                 (np.sqrt(2.0), FIT_COLOR, "+sqrt(2)")):
        ax.axvline(value, color=colour, linestyle=":", linewidth=0.9)
    ax.axhline(0.0, color="#9ca3af", linewidth=0.7)
    ax.set_ylim(-1.15, 1.15)
    ax.set_xlim(b.min() - 0.2, b.max() + 0.2)
    ax.set_xlabel("b = slope of the method shift against the target axis", fontsize=8)
    ax.set_ylabel("tau_b  /  f_unresolved", fontsize=8)
    ax.set_title("(a) linear-shift phase diagram: only the SIGN and |b| over sqrt(2)/z matter",
                 fontsize=9)
    ax.legend(fontsize=6.5, loc="center left")
    ax.grid(alpha=0.25)


def panel_lipschitz(ax, payload):
    rows = payload["controls"]["rank_shift"]
    f = np.asarray([item["fraction_of_min_gap"] for item in rows], float)
    sigma = np.asarray([item["sigma_rms_ev"] for item in rows], float)
    qmax = np.asarray([item["q_max"] for item in rows], float)
    tau = np.asarray([item["tau_b"] for item in rows], float)
    unres = np.asarray([item["f_unresolved_p1"] for item in rows], float)
    ax.plot(f, sigma, "-o", color=RED_COLOR, markersize=5, label="RMS sigma_ij [eV]")
    ax.set_ylim(0.0, sigma.max() * 1.55)
    ax.set_xlabel("f = Lipschitz constant of the shift (fraction of the min gap)",
                  fontsize=8)
    ax.set_ylabel("RMS sigma_ij   [eV]", fontsize=8, color=RED_COLOR)
    for fi, si, qi in zip(f, sigma, qmax):
        ax.text(fi, si + 0.0016, "q_max=%.2f" % qi, fontsize=6.5, ha="center",
                color="#374151")
    ax2 = ax.twinx()
    ax2.plot(f, qmax, "--s", color=FIT_COLOR, markersize=4, label="q_max (= f, exact)")
    ax2.set_ylim(0.0, max(1.75, qmax.max() * 1.75))
    ax2.axhline(np.sqrt(2.0), color=WARN_COLOR, linestyle=":", linewidth=1.0)
    ax2.text(f.min(), np.sqrt(2.0) + 0.03, "critical slope 1.414", fontsize=6.5,
             color=WARN_COLOR)
    ax2.set_ylabel("q_max", fontsize=8, color=FIT_COLOR)
    ax.set_title("(b) monotone f-Lipschitz shift: tau_b=1.000, f_unresolved=0.000 at every f",
                 fontsize=9)
    ax.text(0.03, 0.60, "tau_b = %.3f .. %.3f\nf_unresolved = %.3f .. %.3f" % (
        tau.min(), tau.max(), unres.min(), unres.max()),
        transform=ax.transAxes, fontsize=7, color=OK_COLOR,
        bbox=dict(boxstyle="round", fc="#ecfdf5", ec=OK_COLOR, lw=0.7))
    handles = ax.get_lines()[:1] + ax2.get_lines()[:1]
    ax.legend(handles, [h.get_label() for h in handles], fontsize=6.5,
              loc="lower right")
    ax.grid(alpha=0.25)


def panel_perturbation(ax, payload):
    resc = payload["controls"]["axis_stretch"]
    lam = np.asarray([item["lambda"] for item in resc], float)
    tau = np.asarray([item["tau_b"] for item in resc], float)
    f1 = np.asarray([item["f_unresolved_p1"] for item in resc], float)
    f1c = np.asarray([item["f_unresolved_p1_closedform"] for item in resc], float)
    ax.plot(lam, f1, "-o", color=WARN_COLOR, markersize=5,
            label="f_unresolved, axis stretched x lambda")
    ax.plot(lam, f1c, "--", color=WARN_COLOR, linewidth=1.0,
            label="  closed form abs(t+1-lambda)/lambda")
    ax.plot(lam, tau, "-^", color="#111827", markersize=5, label="tau_b (invariant)")
    noise = payload["controls"]["white_noise"]
    nz = np.asarray([item["noise_sigma_ev"] for item in noise], float)
    ntau = np.asarray([item["d_tau_b_mean"] for item in noise], float)
    ax.plot(nz * 20.0, ntau, "-s", color=RED_COLOR, markersize=5,
            label="d tau_b under white noise (x20 eV axis)")
    offs = payload["controls"]["rigid_offset"]
    deltas = [abs(item["d_tau_b"]) for item in offs]
    ax.plot([0.0], [max(deltas)], marker="*", markersize=13, color=OK_COLOR,
            label="rigid offset: |d tau_b| = %.0e" % max(deltas))
    ax.axhline(0.0, color="#9ca3af", linewidth=0.7)
    ax.set_xlim(-0.05, 5.3)
    ax.set_xlabel("lambda (axis stretch)  /  10 x white-noise sigma [eV]", fontsize=8)
    ax.set_ylabel("value", fontsize=8)
    ax.set_title("(c) which perturbation is free and which is fatal", fontsize=9)
    ax.legend(fontsize=6.5, loc="center left")
    ax.grid(alpha=0.25)


def panel_drift(ax, payload):
    palette = {"P0_to_P1|oxidation": OX_COLOR, "P1_to_P2|oxidation": RED_COLOR}
    for key, records in payload["subset_drift"].items():
        sizes = np.asarray([item["n"] for item in records], float)
        mean = np.asarray([item["tau_b_mean"] for item in records], float)
        lo = np.asarray([item["tau_b_p05"] for item in records], float)
        hi = np.asarray([item["tau_b_p95"] for item in records], float)
        colour = palette.get(key, "#374151")
        ax.fill_between(sizes, lo, hi, color=colour, alpha=0.18)
        ax.plot(sizes, mean, "-o", color=colour, markersize=4,
                label="%s (random subsets)" % SHORT[key.split("|")[0]])
        marks = payload["subset_drift_marks"][key]
        ax.plot([10], [marks["common10"]], "*", markersize=13, color=colour,
                markeredgecolor="#111827", markeredgewidth=0.6)
        ax.plot([18], [marks["full_population"]], "P", markersize=7, color=colour,
                markeredgecolor="#111827", markeredgewidth=0.6)
        ax.axhline(marks["common10"], color=colour, linestyle=":", linewidth=0.9,
                   alpha=0.8)
    ax.set_xlabel("subset size N (drawn from the 18-molecule population)", fontsize=8)
    ax.set_ylabel("Kendall tau_b", fontsize=8)
    ax.set_title("(d) how much the molecule subset itself decides  "
                 "(star = common-10, plus = full 18; band = p05..p95)", fontsize=9)
    ax.legend(fontsize=6.5, loc="lower left")
    ax.grid(alpha=0.25)


def figure_f21(payload, outdir: Path):
    fig, axes = plt.subplots(2, 2, figsize=(11.2, 8.4))
    panel_phase(axes[0][0], payload)
    panel_lipschitz(axes[0][1], payload)
    panel_perturbation(axes[1][0], payload)
    panel_drift(axes[1][1], payload)
    fig.suptitle("F21  counterfactual controls: what actually decides whether a rung "
                 "damages the shortlist", fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.965))
    path = outdir / "F21_sigma_controls.png"
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)
    return path


def main(argv=None) -> int:
    args = parse_args(argv)
    payload = json.loads(args.anatomy.read_text(encoding="utf-8"))
    args.outdir.mkdir(parents=True, exist_ok=True)

    f20 = figure_f20(payload, args.outdir)
    f21 = figure_f21(payload, args.outdir)

    thesis = payload["theorems"]
    table = {item["predictor"]: item for item in payload["predictability"]["table"]
             if item.get("auc") is not None}
    lin_dev = max(abs(item["q_median"] - item["abs_slope"])
                  for item in payload["controls"]["linear_shift"])
    unres_all = [row["f_unresolved_p1_observed"] for row in payload["rows"]]
    unres_all += [row["f_unresolved_p1_z1p96_observed"] for row in payload["rows"]]
    zero_count = sum(1 for value in unres_all if value == 0.0)
    one_count = sum(1 for value in unres_all if value == 1.0)
    lines = [
        "# Figure manifest - Week 10 / Stage 11 (F20, F21)",
        "",
        "| figure | file | figure SHA256 | inputs (SHA256) |",
        "| --- | --- | --- | --- |",
        "| F20 | `%s` | %s | `stage11_sigma_anatomy.json` %s |" % (
            f20.name, sha256(f20), sha256(ANATOMY_JSON)),
        "| F21 | `%s` | %s | `stage11_sigma_anatomy.csv` %s |" % (
            f21.name, sha256(f21), sha256(ANATOMY_CSV)),
        "",
        "Common-10 subset only, one row per (rung, axis), ten points in total.",
        "",
        "F20 panel (a): verified identity T1, maximum absolute error %.2e eV over all"
        % thesis["T1_sigma_is_shift_difference"]["max_abs_err_ev"],
        "pairs of all ten points. sigma_ij is the *difference* of the per-molecule",
        "shift, so sigma carries no information about the size of the shift at all.",
        "",
        "F20 panel (b): the ten per-rung secant-slope distributions",
        "q_ij = abs(delta_i - delta_j)/abs(dP_ij), with the two critical slopes",
        "sqrt(2)/z = %.3f (z=1) and %.3f (z=1.96). A pair is resolved exactly when"
        % (payload["critical_slope_z1"], payload["critical_slope_z1p96"]),
        "its slope stays below the line.",
        "",
        "F20 panel (c): T4 checked at both thresholds; maximum absolute error %.1e,"
        % max(thesis["T4_closed_form_unresolved"]["max_abs_err_z1"],
              thesis["T4_closed_form_unresolved"]["max_abs_err_z1p96"]),
        "i.e. exact. The twenty points split into %d at f = 0, %d at f = 1 and %d"
        % (zero_count, one_count, 20 - zero_count - one_count),
        "strictly in between, which is why the closed form is a real statement and",
        "not a restatement of the data.",
        "",
        "F20 panel (d): AUC of every cheap single-variable predictor of a top-2",
        "shortlist rewrite. The signed slope `ols_slope_b` reaches %.3f with exact"
        % table["ols_slope_b"]["auc"],
        "permutation p = %.4f (1/%d over %d points with %d positives), while its"
        % (table["ols_slope_b"]["auc_exact_permutation_p"],
           table["ols_slope_b"]["n_permutations"], table["ols_slope_b"]["n"],
           table["ols_slope_b"]["n_positives"]),
        "absolute value `abs_ols_slope_b` reaches only %.3f. The two unsigned"
        % table["abs_ols_slope_b"]["auc"],
        "magnitude proxies are weaker: `q_median` %.3f and `sd(delta)` %.3f."
        % (table["q_median"]["auc"], table["sigma_rms_ev"]["auc"]),
        "",
        "F21 panel (a): the linear-shift phase diagram. With delta = b*(target - mean)",
        "every secant slope equals abs(b) exactly (max deviation %.1e), so tau_b flips"
        % lin_dev,
        "sign at b = -1 and f_unresolved steps from 0 to 1 at abs(b) = sqrt(2)/z.",
        "The diagram is the closed form of the whole resolved/unresolved machinery.",
        "",
        "F21 panel (b): a shift that is monotone and f-Lipschitz with f <= 1 keeps",
        "tau_b = 1.000 and f_unresolved = 0.000 at every amplitude, with q_max = f",
        "exactly. Monotonicity alone is not sufficient; the Lipschitz constant is",
        "what T4 charges for.",
        "",
        "F21 panel (c): rigid inter-layer offsets are free (max abs(d tau_b) = %.0e),"
        % max(abs(item["d_tau_b"]) for item in payload["controls"]["rigid_offset"]),
        "while inflating the shift pushes f_unresolved towards 1 without moving tau_b,",
        "and per-molecule white noise degrades tau_b. This is why the week-9",
        "observation f_robust_inv = 0 everywhere must be read together with",
        "f_unresolved and never on its own.",
        "",
        "F21 panel (d): tau_b when N molecules are drawn at random from the",
        "18-molecule population, band = p05..p95, star = the common-10 subset,",
        "plus = the full population. The reported tau_b of a rung depends on the",
        "subset at the +/-0.1 level for N ~ 10, which is the same order as several",
        "of the rung-to-rung differences quoted in weeks 4-9.",
        "",
        "Palette and dpi follow the other week figures (warm/cool pair for the",
        "oxidation/reduction axes, dpi = 160, bbox_inches = tight).",
        "",
        "`stage11_summary.md` is the narrative companion of these figures.",
        "",
    ]
    args.manifest.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print("wrote %s" % f20.relative_to(REPO_ROOT).as_posix())
    print("wrote %s" % f21.relative_to(REPO_ROOT).as_posix())
    print("wrote %s" % args.manifest.relative_to(REPO_ROOT).as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())