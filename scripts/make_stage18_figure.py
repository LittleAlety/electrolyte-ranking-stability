"""Stage 18 figures (F34, F35) -- identity census and zero-cost self-diagnosis.

F34 (Part A, the directory-wide identity census)

    (a) the primary identity channel ``charge_l1`` for the two classes, on a log
        axis, open-shell pairs only.  The frozen 0.039 threshold and the empty
        calibration band between 0.038509 and 0.039383 are drawn as references.
    (b) AUC of every reported channel, over the three arms, so it is visible that
        only the two L1 channels separate anything.
    (c) per family: coincident against moread_lower, raw counts.
    (d) the held-out arm cell by cell: delta_ev against the 1 meV threshold.

F35 (Part B, the self-diagnosis)

    (e) the single-variable screen: |AUC - 0.5| for the eight reported features,
        with the leave-one-out verdict marked on each bar.
    (f) gap_warn_value for positives and negatives with the frozen -0.0395 line.
    (g) the held-out arm row by row, scored once by the frozen rule.
    (h) the one-sided screen: the presence rule against the value rule.

Every number is read from the JSON / CSV products under --data-dir; the only
literals here are protocol constants.  Labels are ASCII on purpose: the workspace
has no guaranteed CJK font.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = REPO_ROOT / "outputs" / "week17"
DEFAULT_OUTDIR = REPO_ROOT / "outputs" / "figures"

# -- named protocol constants (the only literals allowed in this script) --------
MATERIAL_THRESHOLD_EV = 1e-3   # 1 meV, the material energy threshold
CHARGE_L1_THRESHOLD = 0.039    # frozen in the census JSON, open-shell only
CALIB_GAP = (0.03850899999999996, 0.03938299999999993)
VALUE_THRESHOLD = -0.0395      # frozen by the single-variable screen
NO_WARNING_VALUE = 1.0         # sentinel for "ORCA stayed silent"

MANIFEST_NAME = "figure_manifest_week17_stage18.md"
FIGURE_F34 = "F34_stage18_identity_census.png"
FIGURE_F35 = "F35_stage18_selfdiagnosis.png"

CENSUS_JSON = "stage18_identity_census.json"
CENSUS_CSV = "stage18_identity_census.csv"
DIAG_JSON = "stage18_selfdiagnosis.json"
DIAG_CSV = "stage18_selfdiagnosis_features.csv"

FAMILY_ORDER = ("cyclic_carbonate", "linear_carbonate", "ester", "ether",
                "nitrile", "phosphate", "sulfone", "sulfoxide")

RED = "#c0392b"
BLUE = "#1f5fa9"
GREY = "#9a9a9a"
GREEN = "#1a7d4f"
ORANGE = "#d98218"
PURPLE = "#6a3d9a"
DARK = "#222222"

CLASS_COLOR = {"coincident": BLUE, "moread_lower": RED}
ARM_COLOR = {"all": BLUE, "discovery": ORANGE, "holdout": GREEN}
CHANNEL_ORDER = ("charge_l1", "spin_l1", "spin_max_moread", "loss_in_pr", "delta_s2")
CHANNEL_LABEL = {"charge_l1": "charge_l1", "spin_l1": "spin_l1",
                 "spin_max_moread": "spin_max\n(moread)", "loss_in_pr": "loss_in_pr",
                 "delta_s2": "delta_s2"}

F34_CAPTION = ("(a) charge_l1 双峰：coincident 239 / moread_lower 37（仅开壳层可测），"
               "冻结阈值 0.039 落在 0.0385-0.0394 空档；(b) 五通道 x 三臂 AUC；"
               "(c) 按家族的重合率；(d) 留出臂 54 格 delta_ev 与 1 meV 阈值")
F35_CAPTION = ("(e) 单变量筛查前 8 名 |AUC-0.5| 与 LOO 裁决（gap_warn_value 第一、"
               "LOO 胜基线但留出臂输）；(f) gap_warn_value 正负例分布与冻结阈值 -0.0395；"
               "(g) 留出臂 54 格按冻结规则逐行打分（TP=0）；"
               "(h) 单边筛查：presence 规则放行 140/414、敏感度 1.000、特异度 0.371")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 16), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_csv(path: Path):
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


def save(fig, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=170, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("wrote %s (%d bytes)" % (path.relative_to(REPO_ROOT), path.stat().st_size))
    return path

# ---------------------------------------------------------------------------
# F34 -- Part A, the identity census
# ---------------------------------------------------------------------------

def panel_a(ax, rows, separation):
    measurable = [r for r in rows if as_bool(r["identity_measurable"])]
    coinc = [as_float(r["charge_l1"]) for r in measurable
             if r["classification"] == "coincident"]
    more = [as_float(r["charge_l1"]) for r in measurable
            if r["classification"] == "moread_lower"]
    coinc = [v for v in coinc if v is not None]
    more = [v for v in more if v is not None]
    lo = min(min(coinc), min(more)) * 0.7
    hi = max(max(coinc), max(more)) * 1.4
    bins = np.logspace(np.log10(lo), np.log10(hi), 44)
    ax.axvspan(CALIB_GAP[0], CALIB_GAP[1], color=GREEN, alpha=0.22, zorder=0,
               label="calibration gap (empty)")
    ax.hist(coinc, bins=bins, color=CLASS_COLOR["coincident"], alpha=0.78,
            label="coincident (n=%d)" % len(coinc))
    ax.hist(more, bins=bins, color=CLASS_COLOR["moread_lower"], alpha=0.72,
            label="moread_lower (n=%d)" % len(more))
    ax.axvline(CHARGE_L1_THRESHOLD, color=DARK, ls="--", lw=1.2)
    ax.set_xscale("log")
    ax.set_xlabel("charge_l1  (open-shell pairs only)")
    ax.set_ylabel("cells")
    ax.set_ylim(0, ax.get_ylim()[1] * 1.9)
    ax.set_title("(a) primary identity channel")
    ax.legend(loc="upper left", fontsize=7, frameon=False)
    conf = separation["all"]["confusion_at_threshold"]
    ax.text(0.98, 0.97,
            "threshold %.3f\ntp/fn/fp/tn = %d/%d/%d/%d\nAUC = %.6f"
            % (CHARGE_L1_THRESHOLD, conf["tp"], conf["fn"], conf["fp"], conf["tn"],
               separation["all"]["auc"]["charge_l1"]),
            transform=ax.transAxes, ha="right", va="top", fontsize=7.5,
            bbox=dict(boxstyle="round", fc="white", ec=GREY, lw=0.6))


def panel_b(ax, separation):
    arms = ("all", "discovery", "holdout")
    width = 0.26
    xs = np.arange(len(CHANNEL_ORDER))
    for i, arm in enumerate(arms):
        block = separation.get(arm) or {}
        auc = block.get("auc") or {}
        vals = [float(auc.get(ch) or 0.0) for ch in CHANNEL_ORDER]
        ax.bar(xs + (i - 1) * width, vals, width, label="%s (n+ = %s)"
               % (arm, block.get("n_positive_cells", "n/a")),
               color=ARM_COLOR[arm], alpha=0.9)
    ax.axhline(0.5, color=DARK, lw=0.9, ls=":")
    ax.text(len(CHANNEL_ORDER) - 0.55, 0.52, "chance", fontsize=7, color=DARK)
    ax.set_xticks(xs)
    ax.set_xticklabels([CHANNEL_LABEL[c] for c in CHANNEL_ORDER], fontsize=7.5)
    ax.set_ylabel("AUC (identity_differs)")
    ax.set_ylim(0.0, 1.12)
    ax.set_title("(b) separation per channel and arm")
    ax.legend(fontsize=7, frameon=False, loc="lower center", ncol=3)


def panel_c(ax, by_family):
    fams = [f for f in FAMILY_ORDER if f in by_family]
    ys = np.arange(len(fams))
    coin = np.array([int(by_family[f]["n_coincident"]) for f in fams], dtype=float)
    more = np.array([int(by_family[f]["n_moread_lower"]) for f in fams], dtype=float)
    ax.barh(ys, coin, color=CLASS_COLOR["coincident"], label="coincident")
    ax.barh(ys, more, left=coin, color=CLASS_COLOR["moread_lower"],
            label="moread_lower")
    for y, c, m in zip(ys, coin, more):
        ax.text(c + m + 1.5, y, "%d/%d" % (int(m), int(c + m)), va="center", fontsize=7)
    ax.set_yticks(ys)
    ax.set_yticklabels(fams, fontsize=8)
    ax.invert_yaxis()
    ax.set_xlabel("cells  (label: moread_lower / total)")
    ax.set_xlim(0, (coin + more).max() * 1.3)
    ax.set_title("(c) per family: how often the two arms coincide")
    ax.legend(fontsize=7, frameon=False, loc="lower right")


def panel_d(ax, rows, census):
    held = sorted((r for r in rows if r["arm_set"] == "holdout"),
                  key=lambda r: (r["name"], r["state"], float(r["epsilon"])))
    vals = [as_float(r["delta_ev"]) for r in held]
    colors = [CLASS_COLOR.get(r["classification"], GREY) for r in held]
    xs = np.arange(len(held))
    ax.bar(xs, vals, color=colors, width=0.82)
    ax.axhline(-MATERIAL_THRESHOLD_EV, color=DARK, ls="--", lw=1.1)
    ax.set_yscale("symlog", linthresh=1e-6)
    ax.set_ylim(-1.6e-1, 4e-6)
    ax.text(0.15, 0.03, "1 meV threshold", fontsize=7, color=DARK,
            transform=ax.transAxes, ha="center", va="bottom",
            bbox=dict(boxstyle="round", fc="white", ec="none", alpha=0.85))
    centres, labels = [], []
    last, start = None, 0
    for i, row in enumerate(held + [None]):
        name = row["name"] if row else None
        if last is not None and name != last:
            centres.append((start + i - 1) / 2.0)
            labels.append(last)
            start = i
        last = name
    ax.set_xticks(centres)
    ax.set_xticklabels(labels, fontsize=8)
    ax.set_ylabel("delta_ev (eV)")
    ax.set_xlabel("held-out arm: %d cells (%d molecules x 3 states x 3 epsilons)"
                  % (len(held), len(labels)))
    ax.set_title("(d) held-out arm cell by cell")
    misses = census.get("holdout_moread_molecules") or []
    ax.text(0.99, 0.03, "red = moread_lower: %s\nblue = coincident"
            % ", ".join(misses), transform=ax.transAxes, ha="right", va="bottom",
            fontsize=7.5, bbox=dict(boxstyle="round", fc="white", ec=GREY, lw=0.6))


def figure_census(data_dir, outdir, census, rows):
    fig = plt.figure(figsize=(13.4, 9.6))
    grid = fig.add_gridspec(2, 2, hspace=0.34, wspace=0.24)
    panel_a(fig.add_subplot(grid[0, 0]), rows, census["separation"])
    panel_b(fig.add_subplot(grid[0, 1]), census["separation"])
    panel_c(fig.add_subplot(grid[1, 0]), census["by_family"])
    panel_d(fig.add_subplot(grid[1, 1]), rows, census)
    fig.suptitle("Stage 18 part A -- electronic-structure identity of the two SCF "
                 "solutions (%d pairs)" % census["n_pairs"], fontsize=12)
    return save(fig, Path(outdir) / FIGURE_F34)


# ---------------------------------------------------------------------------
# F35 -- Part B, the zero-extra-cost self-diagnosis
# ---------------------------------------------------------------------------

def panel_e(ax, screen):
    top = screen[:8]
    names = [entry["descriptor"] for entry in top]
    vals = [float(entry["abs_auc_above_half"]) for entry in top]
    ys = np.arange(len(top))
    colors = [GREEN if entry["beats_majority_loo"] else GREY for entry in top]
    ax.barh(ys, vals, color=colors, alpha=0.9)
    for y, entry in zip(ys, top):
        holdout = entry.get("holdout_accuracy_post_hoc")
        ax.text(float(entry["abs_auc_above_half"]) + 0.006, y,
                "LOO %.3f  holdout %s"
                % (float(entry["loo_accuracy"]), "n/a" if holdout is None
                   else "%.3f" % float(holdout)),
                va="center", fontsize=7)
    ax.set_yticks(ys)
    ax.set_yticklabels(names, fontsize=8)
    ax.invert_yaxis()
    ax.set_xlim(0, 0.62)
    ax.set_xlabel("|AUC - 0.5| on the discovery set")
    ax.set_title("(e) single-variable screen, top 8 (green = LOO beats majority)")
    ax.axvline(0.0, color=DARK, lw=0.6)


def panel_f(ax, rows, one_sided):
    pos = [as_float(r["gap_warn_value"]) for r in rows if int(r["label"]) == 1]
    neg = [as_float(r["gap_warn_value"]) for r in rows if int(r["label"]) == 0]
    neg_warn = [v for v in neg if v is not None and v < NO_WARNING_VALUE - 1e-9]
    neg_silent = [v for v in neg if v is None or v >= NO_WARNING_VALUE - 1e-9]
    bins = np.linspace(-0.075, 0.02, 40)
    ax.hist(neg_warn, bins=bins, color=CLASS_COLOR["coincident"], alpha=0.78,
            label="negative, warned (n=%d)" % len(neg_warn))
    ax.hist(pos, bins=bins, color=CLASS_COLOR["moread_lower"], alpha=0.72,
            label="positive (n=%d)" % len(pos))
    ax.axvline(VALUE_THRESHOLD, color=DARK, ls="--", lw=1.2)
    ax.set_xlabel("gap_warn_value (Eh) quoted by ORCA's small-gap warning")
    ax.set_ylabel("cells")
    ax.set_ylim(0, ax.get_ylim()[1] * 1.5)
    ax.set_title("(f) the frozen descriptor overlaps completely")
    ax.legend(loc="upper left", fontsize=7, frameon=False)
    pos_range = one_sided["positive_gap_warn_value_range"]["pooled"]
    ax.text(0.98, 0.97,
            "frozen rule: value <= %.4f\n"
            "positives span [%.3f, %.3f]\n"
            "warned negatives span\n[%.3f, %+.3f]  (overlap)\n"
            "%d negative cells carry no warning\n(sentinel +1.0, off scale)"
            % (VALUE_THRESHOLD, pos_range["min_eh"], pos_range["max_eh"],
               min(neg_warn), max(neg_warn), len(neg_silent)),
            transform=ax.transAxes, ha="right", va="top", fontsize=7,
            bbox=dict(boxstyle="round", fc="white", ec=GREY, lw=0.6))


def panel_g(ax, holdout):
    per_row = holdout["per_row"]
    xs = np.arange(len(per_row))
    plotted = [min(max(as_float(r["value"]), -0.08), 0.02) for r in per_row]
    for i, row in enumerate(per_row):
        truth = bool(row["truth"])
        colour = CLASS_COLOR["moread_lower"] if truth else CLASS_COLOR["coincident"]
        marker = "*" if row["predicted"] else "o"
        ax.scatter(xs[i], plotted[i], s=70 if truth else 26, marker=marker,
                   color=colour, zorder=3, edgecolor="white", linewidth=0.4)
    ax.axhline(VALUE_THRESHOLD, color=DARK, ls="--", lw=1.1)
    ax.set_ylim(-0.085, 0.03)
    ax.set_xlabel("held-out rows (54 cells)")
    ax.set_ylabel("gap_warn_value (Eh), clipped")
    ax.set_title("(g) held-out arm scored once by the frozen rule")
    conf = holdout["confusion_matrix"]
    ax.text(0.02, 0.04,
            "accuracy %.4f vs majority %.4f\nTP=%d FP=%d TN=%d FN=%d\n"
            "every true positive is missed (star = flagged)"
            % (holdout["accuracy"], holdout["majority_accuracy"],
               conf["true_positive"], conf["false_positive"],
               conf["true_negative"], conf["false_negative"]),
            transform=ax.transAxes, ha="left", va="bottom", fontsize=7.5,
            bbox=dict(boxstyle="round", fc="white", ec=GREY, lw=0.6))
    from matplotlib.lines import Line2D
    handles = [Line2D([], [], marker="*", ls="", color=GREY, markersize=11,
                      label="flagged by the rule"),
               Line2D([], [], marker="o", ls="", color=GREY, markersize=6,
                      label="not flagged"),
               Line2D([], [], marker="o", ls="", color=CLASS_COLOR["moread_lower"],
                      markersize=7, label="positive (truth)"),
               Line2D([], [], marker="o", ls="", color=CLASS_COLOR["coincident"],
                      markersize=7, label="negative (truth)")]
    ax.legend(handles=handles, fontsize=6.5, frameon=False, loc="lower right",
              ncol=2, handletextpad=0.4, columnspacing=0.8)


def panel_h(ax, one_sided):
    rules = {entry["id"]: entry["by_arm"]["pooled"] for entry in one_sided["tradeoff"]}
    pres = rules["any_warning"]
    val = rules["frozen_value_threshold"]
    groups = ["presence rule\n(warning printed?)", "value rule\n(value <= %.4f)" % VALUE_THRESHOLD]
    xs = np.arange(len(groups))
    width = 0.34
    sens = [float(pres["sensitivity"]), float(val["sensitivity"])]
    spec = [float(pres["specificity"]), float(val["specificity"])]
    ax.bar(xs - width / 2, sens, width, color=RED, alpha=0.9, label="sensitivity (recall)")
    ax.bar(xs + width / 2, spec, width, color=BLUE, alpha=0.9, label="specificity")
    for i, (s1, s2) in enumerate(zip(sens, spec)):
        ax.text(xs[i] - width / 2, s1 + 0.02, "%.3f" % s1, ha="center", fontsize=7.5)
        ax.text(xs[i] + width / 2, s2 + 0.02, "%.3f" % s2, ha="center", fontsize=7.5)
    ax.set_xticks(xs)
    ax.set_xticklabels(groups, fontsize=8)
    ax.set_ylim(0, 1.28)
    ax.set_ylabel("rate on the pooled 414 cells")
    ax.set_title("(h) one-sided screen: necessary, not sufficient")
    ax.legend(fontsize=7, frameon=False, loc="upper center", ncol=2,
              bbox_to_anchor=(0.5, 1.02))
    necces = one_sided["necessity"]["overall"]
    cleared = pres["confusion_matrix"]["true_negative"] + pres["confusion_matrix"]["false_negative"]
    lost = pres["confusion_matrix"]["false_negative"]
    ax.text(0.5, 0.66,
            "necessary: %d/%d positives carry the warning\n(counterexamples %d)\n"
            "clearing the %d silent rows loses %d of them"
            % (necces["n_positive_with_warning"], necces["n_positive"],
               necces["n_positive_without_warning"], cleared, lost),
            transform=ax.transAxes, ha="center", va="center", fontsize=7.5,
            bbox=dict(boxstyle="round", fc="#f4f4f4", ec=GREY, lw=0.6))


def figure_selfdiagnosis(data_dir, outdir, diag, rows):
    fig = plt.figure(figsize=(13.4, 9.6))
    grid = fig.add_gridspec(2, 2, hspace=0.34, wspace=0.26)
    panel_e(fig.add_subplot(grid[0, 0]), diag["screen"])
    panel_f(fig.add_subplot(grid[0, 1]), rows, diag["one_sided_screening"])
    panel_g(fig.add_subplot(grid[1, 0]), diag["holdout"])
    panel_h(fig.add_subplot(grid[1, 1]), diag["one_sided_screening"])
    fig.suptitle("Stage 18 part B -- self-diagnosis from the default arm's own .out "
                 "(%d cells)" % diag["holdout"]["n_rows"], fontsize=12)
    return save(fig, Path(outdir) / FIGURE_F35)

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


def write_manifest(outdir, data_dir, figure_paths, inputs, census, diag, rows):
    sep = census["separation"]
    counts = census["classification_counts"]
    one_sided = diag["one_sided_screening"]
    necces = one_sided["necessity"]["overall"]
    insuf = one_sided["specificity"]["overall"]
    pres = {entry["id"]: entry["by_arm"]["pooled"]
            for entry in one_sided["tradeoff"]}["any_warning"]
    pres_matrix = pres["confusion_matrix"]
    cleared = pres_matrix["true_negative"] + pres_matrix["false_negative"]
    holdout_conf = diag["holdout"]["confusion_matrix"]
    frozen = diag["frozen_rule"]

    lines = ["# figure_manifest_week17_stage18", "",
             "| figure | sha256 | size |", "| --- | --- | --- |"]
    for path in figure_paths:
        lines.append("| `%s` | `%s` | %d B |"
                     % (path.name, sha256(path), path.stat().st_size))
    lines += ["", "| input | sha256 |", "| --- | --- |"]
    for path in inputs:
        lines.append("| `%s` | `%s` |"
                     % (str(path.relative_to(REPO_ROOT)).replace("\\", "/"),
                        sha256(path)))
    lines += ["", "Generate (from the repository root):", "", "```powershell",
              "& $py scripts\\make_stage18_figure.py",
              "& $py scripts\\make_stage18_figure.py --check",
              "```", ""]

    lines += ["## F34 -- `%s`" % FIGURE_F34, "",
              "One-line caption (verbatim, for the terminal site): %s" % F34_CAPTION, "",
              "### (a) the primary identity channel", "",
              "`charge_l1` of the %d measurable open-shell pairs: coincident (n = %d) "
              "against moread_lower (n = %d).  The frozen threshold %.3f sits in the "
              "empty calibration band [%.6f, %.6f] read off the discovery arm only; "
              "tp/fn/fp/tn = %d/%d/%d/%d and AUC = %.6f on the whole directory."
              % (sep["all"]["n_positive_measurable"] + sep["all"]["n_negative_measurable"],
                 sep["all"]["n_negative_measurable"], sep["all"]["n_positive_measurable"],
                 CHARGE_L1_THRESHOLD, CALIB_GAP[0], CALIB_GAP[1],
                 sep["all"]["confusion_at_threshold"]["tp"],
                 sep["all"]["confusion_at_threshold"]["fn"],
                 sep["all"]["confusion_at_threshold"]["fp"],
                 sep["all"]["confusion_at_threshold"]["tn"],
                 sep["all"]["auc"]["charge_l1"]), "",
              "### (b) separation per channel and arm", ""]
    for arm in ("all", "discovery", "holdout"):
        block = sep[arm]
        lines.append("- %s (n+ = %d): %s"
                     % (arm, block["n_positive_cells"],
                        ", ".join("%s %.6f" % (ch, block["auc"][ch])
                                  for ch in CHANNEL_ORDER)))
    lines += ["", "### (c) per family", ""]
    for family, info in census["by_family"].items():
        lines.append("- %s (n = %d): coincident %d, moread_lower %d, mean charge_l1 %s"
                     % (family, int(info["n_cells"]), int(info["n_coincident"]),
                        int(info["n_moread_lower"]),
                        "n/a" if info["n_identity_measurable"] == 0
                        else "%.6f" % float(info["charge_l1_mean"])))
    lines += ["", "### (d) held-out arm", ""]
    lines.append("- classification: coincident %d, moread_lower %d; misses on %s; "
                 "identity AUC %.6f with tp/fn/fp/tn = %d/%d/%d/%d"
                 % (counts["holdout"]["coincident"], counts["holdout"]["moread_lower"],
                    ", ".join(census.get("holdout_moread_molecules") or []),
                    sep["holdout"]["auc"]["charge_l1"],
                    sep["holdout"]["confusion_at_threshold"]["tp"],
                    sep["holdout"]["confusion_at_threshold"]["fn"],
                    sep["holdout"]["confusion_at_threshold"]["fp"],
                    sep["holdout"]["confusion_at_threshold"]["tn"]))
    lines.append("- energy cross-check over %d pairs: max|delta| = %.1e eV (tolerance "
                 "%.0e); geometry identical %d/%d"
                 % (census["energy_crosscheck"]["n_compared"],
                    census["energy_crosscheck"]["max_abs_mismatch_ev"],
                    census["energy_crosscheck"]["tolerance_ev"],
                    census["geometry_qc"]["n_geometry_identical"],
                    census["geometry_qc"]["n_pairs"]))
    lines.append("")

    lines += ["## F35 -- `%s`" % FIGURE_F35, "",
              "One-line caption (verbatim, for the terminal site): %s" % F35_CAPTION, "",
              "### (e) the single-variable screen", ""]
    for rank, entry in enumerate(diag["screen"][:8], 1):
        holdout_acc = entry.get("holdout_accuracy_post_hoc")
        lines.append("- %d. `%s`: AUC %.6f, |AUC-0.5| %.4f, threshold %s, LOO %.4f "
                     "vs majority %.4f (%s), holdout %s"
                     % (rank, entry["descriptor"], float(entry["auc"]),
                        float(entry["abs_auc_above_half"]), entry["threshold_frozen"],
                        float(entry["loo_accuracy"]), float(entry["majority_accuracy"]),
                        "beats" if entry["beats_majority_loo"] else "loses",
                        "n/a" if holdout_acc is None else "%.4f" % float(holdout_acc)))
    lines += ["", "### (f) the frozen descriptor", ""]
    lines.append("- `%s` %s `%s`; in-sample accuracy %.4f, LOO %.4f, exact p = %.4g"
                 % (frozen["descriptor"], frozen["sign"],
                    _fmt_number(frozen["threshold_frozen"]),
                    float(diag["in_sample"]["accuracy"]),
                    float(diag["loo"]["accuracy"]),
                    float(diag["significance"]["p_value"])))
    warned_negative_values = sorted(float(r["gap_warn_value"]) for r in rows
                                    if int(r["label"]) == 0
                                    and str(r["gap_warn_present"]).lower() in ("1", "true")
                                    and r["gap_warn_value"] not in ("", "None", None))
    positives = one_sided["positive_gap_warn_value_range"]["pooled"]
    lines.append("- positives span [%.3f, %.3f] Eh (all negative: %s); negatives that did "
                 "carry the warning span [%.3f, %+.3f] Eh, which brackets the positive range."
                 % (positives["min_eh"], positives["max_eh"], positives["all_negative"],
                    warned_negative_values[0], warned_negative_values[-1]))
    lines += ["", "### (g) the held-out arm", ""]
    lines.append("- accuracy %.4f against majority %.4f; TP=%d FP=%d TN=%d FN=%d, i.e. "
                 "the frozen rule flags no true positive at all."
                 % (float(diag["holdout"]["accuracy"]),
                    float(diag["holdout"]["majority_accuracy"]),
                    holdout_conf["true_positive"], holdout_conf["false_positive"],
                    holdout_conf["true_negative"], holdout_conf["false_negative"]))
    lines += ["", "### (h) the one-sided screen", ""]
    lines.append("- presence rule, pooled: sensitivity %.4f, specificity %.4f, "
                 "precision %.4f (it flags %d of %d rows)."
                 % (float(pres["sensitivity"]), float(pres["specificity"]),
                    float(pres["precision"]),
                    int(pres_matrix["true_positive"]) + int(pres_matrix["false_positive"]),
                    int(pres["n_rows"])))
    lines.append("- necessary condition: %d/%d positives carry the warning "
                 "(counterexamples %d); discovery %d/%d, holdout %d/%d."
                 % (necces["n_positive_with_warning"], necces["n_positive"],
                    necces["n_positive_without_warning"],
                    one_sided["necessity"]["by_arm"]["discovery"]["n_positive_with_warning"],
                    one_sided["necessity"]["by_arm"]["discovery"]["n_positive"],
                    one_sided["necessity"]["by_arm"]["holdout"]["n_positive_with_warning"],
                    one_sided["necessity"]["by_arm"]["holdout"]["n_positive"]))
    lines.append("- screening yield: clearing the silent rows releases %d of %d cells "
                 "and loses %d positives; the false-alarm rate of the warning on "
                 "negatives is %.4f."
                 % (cleared, int(pres["n_rows"]),
                    int(pres_matrix["false_negative"]), float(insuf["false_alarm_rate"])))
    lines.append("- per-epsilon sensitivity of the presence rule: %s"
                 % ", ".join("eps %s %d/%d" % (eps, row["n_positive_with_warning"],
                                               row["n_positive"])
                             for eps, row in sorted(one_sided["by_epsilon"]["pooled"].items(),
                                                    key=lambda item: float(item[0]))))
    lines += ["", "Palette and dpi follow the other week figures (dpi = 170, "
              "bbox_inches = tight). All labels are ASCII because the workspace has no "
              "guaranteed CJK font.", ""]

    manifest = Path(outdir) / MANIFEST_NAME
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print("wrote %s (%d bytes)"
          % (manifest.relative_to(REPO_ROOT), manifest.stat().st_size))
    return manifest


def _fmt_number(value):
    text = ("%.10f" % float(value)).rstrip("0").rstrip(".")
    return text


def run_check(outdir) -> int:
    manifest = Path(outdir) / MANIFEST_NAME
    if not manifest.exists():
        print("check FAILED: manifest missing: %s" % manifest)
        return 1
    rows = _figure_rows(manifest.read_text(encoding="utf-8"))
    status = 0
    for name in (FIGURE_F34, FIGURE_F35):
        path = Path(outdir) / name
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
    if status == 0:
        print("check ok: manifest matches disk")
    return status


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Stage 18 figures (F34, F35).")
    parser.add_argument("--outdir", default=str(DEFAULT_OUTDIR),
                        help="figure output directory (default outputs/figures)")
    parser.add_argument("--data-dir", default=str(DEFAULT_DATA_DIR),
                        help="Stage 18 product directory (default outputs/week17)")
    parser.add_argument("--check", action="store_true",
                        help="verify the products exist and the manifest sha256 matches")
    args = parser.parse_args(argv)

    outdir = Path(args.outdir)
    data_dir = Path(args.data_dir)

    if args.check:
        return run_check(outdir)

    census = load_json(data_dir / CENSUS_JSON)
    diag = load_json(data_dir / DIAG_JSON)
    census_rows = load_csv(data_dir / CENSUS_CSV)
    diag_rows = load_csv(data_dir / DIAG_CSV)

    if len(census_rows) != census["n_pairs"]:
        raise SystemExit("census CSV has %d rows, JSON says %d"
                         % (len(census_rows), census["n_pairs"]))
    if "one_sided_screening" not in diag:
        raise SystemExit("self-diagnosis JSON has no one_sided_screening block; "
                         "re-run scripts/build_stage18_selfdiagnosis.py")

    f34 = figure_census(data_dir, outdir, census, census_rows)
    f35 = figure_selfdiagnosis(data_dir, outdir, diag, diag_rows)
    inputs = [data_dir / name for name in (CENSUS_JSON, CENSUS_CSV, DIAG_JSON, DIAG_CSV)]
    write_manifest(outdir, data_dir, [f34, f35], inputs, census, diag, diag_rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())