"""Stage 16 figures (F30, F31) -- the catalogue and the warning rule.

F30 is the catalogue:

    (a) the whole grid: twelve molecules x three charge states x ten dielectrics,
        coloured by sign of dE = E_moread - E_default.  Grey means the two arms
        agreed to SCF convergence, red means the default guess was above the
        lowest solution, blue means it was below (which should not happen).
    (b) the size of the worst deficit per (molecule, state).
    (c) how many cells sit above each threshold, i.e. the same header as Stage 15
        panel (a) but for the whole core set.

F31 is the rule:

    (d) the chosen a priori descriptor against the deficit it is supposed to
        predict, with the frozen threshold drawn as a line.
    (e) every descriptor's AUC, so the reader can see the choice was not the only
        one available and how far the runner-up is.
    (f) the held-out arm: predicted against truth, or, when it has not been run,
        the ladder cross-check that decides whether the label is ladder-stable.

Labels are ASCII on purpose: the workspace has no guaranteed CJK font.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]

WEEK15 = REPO_ROOT / "outputs" / "week15"
FIGDIR = REPO_ROOT / "outputs" / "figures"

CELLS_CSV = WEEK15 / "stage16_cells.csv"
ANALYSIS_JSON = WEEK15 / "stage16_catalogue_analysis.json"
PREDICTOR_JSON = WEEK15 / "stage16_predictor.json"
DESCRIPTORS_CSV = WEEK15 / "stage16_gas_descriptors.csv"

RED = "#c0392b"
BLUE = "#1f5fa9"
GREY = "#9a9a9a"
GREEN = "#1a7d4f"
ORANGE = "#d98218"
PURPLE = "#6a3d9a"

SUBSET = ("EC", "PC", "DMC", "EMC", "DME", "DOL", "GBL", "AN", "SN", "DMSO", "SL", "TMP")
STATE_ORDER = ("neutral", "cation", "anion")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 16), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_csv(path: Path):
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def save(fig, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=170, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("wrote %s (%d bytes)" % (path.relative_to(REPO_ROOT), path.stat().st_size))
    return path

def grid(cells, molecules, states):
    levels = sorted({float(row["epsilon"]) for row in cells})
    rows = [(name, state) for name in molecules for state in states]
    values = np.full((len(rows), len(levels)), np.nan)
    lookup = {(name, state): position for position, (name, state) in enumerate(rows)}
    column = {eps: position for position, eps in enumerate(levels)}
    for row in cells:
        key = (row["name"], row["state"])
        if key not in lookup:
            continue
        delta = row["delta_ev"]
        if delta in (None, ""):
            continue
        delta = float(delta)
        if abs(delta) <= 1e-3:
            values[lookup[key], column[float(row["epsilon"])]] = 0.0
        else:
            magnitude = np.log10(abs(delta) / 1e-3)
            values[lookup[key], column[float(row["epsilon"])]] = (
                -magnitude if delta < 0 else magnitude)
    return rows, levels, values


def figure_catalogue(analysis, by_state):
    molecules = [name for name in SUBSET if name in analysis["molecules"]]
    states = [state for state in STATE_ORDER if state in analysis["states"]]
    cells = load_csv(CELLS_CSV)
    rows, levels, values = grid(cells, molecules, states)

    fig = plt.figure(figsize=(13.2, 11.0))
    outer = fig.add_gridspec(3, 1, height_ratios=[2.35, 1.15, 0.85], hspace=0.42)

    ax = fig.add_subplot(outer[0])
    shown = np.ma.masked_invalid(values)
    image = ax.imshow(shown, cmap="RdBu", vmin=-3.0, vmax=3.0, aspect="auto")
    ax.set_xticks(range(len(levels)))
    ax.set_xticklabels(["%g" % eps for eps in levels], fontsize=9)
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels(["%s %s" % (name, state) for name, state in rows], fontsize=7.5)
    ax.set_xlabel("CPCM dielectric constant (10-point Stage 13/14 ladder)", fontsize=9)
    for position in range(len(rows) + 1):
        ax.axhline(position - 0.5, color="#dddddd", lw=0.5)
    for position, (name, state) in enumerate(rows):
        if state == "neutral":
            ax.axhline(position - 0.5, color="#333333", lw=1.1)
    for position, eps in enumerate(levels):
        ax.axvline(position - 0.5, color="#eeeeee", lw=0.4)
    for position, (name, state) in enumerate(rows):
        for column, _ in enumerate(levels):
            if np.isnan(values[position, column]):
                ax.add_patch(plt.Rectangle((column - 0.5, position - 0.5), 1, 1,
                                           facecolor="#f0f0f0", edgecolor="#bbbbbb",
                                           lw=0.3, hatch="///"))
    bar = fig.colorbar(image, ax=ax, pad=0.012, fraction=0.028)
    bar.set_label("sign of dE, scaled by log10(|dE| / 1 meV)\n"
                  "red: default guess was too high   blue: restart was higher",
                  fontsize=8)
    ax.set_title("(a) The two-guess catalogue: 12 molecules x 3 states x 10 dielectrics\n"
                 "grey = the two arms agree to SCF convergence (< 1 meV); "
                 "hatched = no pair", fontsize=10.5)

    ax2 = fig.add_subplot(outer[1])
    open_shell = [row for row in by_state
                  if row["ladder"] == "ladder10" and row["state"] in ("cation", "anion")]
    open_shell.sort(key=lambda row: float(row["max_drop_ev"] or 0.0))
    labels = ["%s %s" % (row["name"], row["state"]) for row in open_shell]
    drops = [-float(row["max_drop_ev"] or 0.0) for row in open_shell]
    colors = [RED if value > 1e-3 else GREY for value in drops]
    ax2.barh(range(len(drops)), drops, color=colors, height=0.72)
    ax2.set_yticks(range(len(drops)))
    ax2.set_yticklabels(labels, fontsize=7.5)
    ax2.axvline(1e-3, color=GREEN, ls="--", lw=1.0)
    ax2.set_xscale("symlog", linthresh=1e-4)
    ax2.set_xlabel("largest deficit of the default guess, |dE| in eV (log)", fontsize=9)
    ax2.set_title("(b) Worst deficit per open-shell (molecule, state) over the whole ladder\n"
                  "green dashed line = the 1 meV material threshold", fontsize=10.5)
    ax2.grid(axis="x", alpha=0.25)

    ax3 = fig.add_subplot(outer[2])
    histogram = analysis["magnitude_histogram"]
    thresholds = analysis["magnitude_histogram_thresholds_ev"]
    counts = [histogram["%g" % thr] for thr in thresholds]
    ax3.bar(range(len(counts)), counts, color=BLUE, width=0.62)
    ax3.set_xticks(range(len(counts)))
    ax3.set_xticklabels(["%g" % thr for thr in thresholds], fontsize=8)
    ax3.set_xlabel("threshold |dE| in eV", fontsize=9)
    ax3.set_ylabel("cells above", fontsize=9)
    for position, value in enumerate(counts):
        ax3.text(position, value + 1.5, str(value), ha="center", fontsize=8)
    ax3.set_ylim(0, max(counts) * 1.22 + 2)
    ax3.set_title("(c) How many of the %d paired cells exceed each threshold"
                  % analysis["n_paired"], fontsize=10.5)

    return save(fig, FIGDIR / "F30_two_guess_catalogue.png")


def figure_rule(analysis, predictor, descriptors):
    screen = predictor.get("screen") or []
    chosen = predictor.get("chosen_rule") or {}
    by_state = load_csv(WEEK15 / "stage16_by_state.csv")
    lookup = {}
    for row in by_state:
        if row["ladder"] in ("ladder10", "validation"):
            lookup[(row["name"], row["state"])] = row

    fig = plt.figure(figsize=(13.2, 8.6))
    outer = fig.add_gridspec(2, 2, height_ratios=[1.0, 1.0], hspace=0.42, wspace=0.26)

    ax = fig.add_subplot(outer[0, 0])
    descriptor = chosen.get("descriptor")
    if descriptor:
        for record in descriptors:
            if record["state"] == "neutral":
                continue
            key = (record["name"], record["state"])
            row = lookup.get(key)
            if row is None:
                continue
            value = record.get(descriptor)
            if value in (None, "", "nan"):
                continue
            value = float(value)
            deficit = -float(row["max_drop_ev"] or 0.0)
            flagged = deficit > 1e-3
            marker = "o" if record["state"] == "anion" else "^"
            face = RED if flagged else "white"
            edge = RED if record["split"] == "discovery" else PURPLE
            ax.scatter(value, max(deficit, 5e-5), marker=marker, s=58,
                       facecolors=face, edgecolors=edge, linewidths=1.4, zorder=3)
        ax.axvline(float(chosen["threshold_frozen"]), color=GREEN, ls="--", lw=1.2,
                   label="frozen threshold %.3f" % float(chosen["threshold_frozen"]))
        ax.set_xlabel(descriptor, fontsize=9)
    ax.set_yscale("log")
    ax.set_ylabel("largest deficit of the default guess, eV", fontsize=9)
    ax.legend(fontsize=8, loc="lower right")
    ax.grid(alpha=0.25)
    ax.set_title("(d) The chosen a priori descriptor, discovery set filled,\n"
                 "held-out set drawn as purple outline (filled = the rule fires)",
                 fontsize=10.5)

    ax2 = fig.add_subplot(outer[0, 1])
    ranked = sorted(screen, key=lambda entry: abs(entry["auc"] - 0.5))
    names = [entry["descriptor"] for entry in ranked][-10:]
    scores = [entry["auc"] - 0.5 for entry in ranked][-10:]
    colors = [RED if value > 0 else BLUE for value in scores]
    ax2.barh(range(len(names)), scores, color=colors, height=0.7)
    ax2.set_yticks(range(len(names)))
    ax2.set_yticklabels(names, fontsize=7.5)
    ax2.axvline(0.0, color="#333333", lw=0.8)
    for position, entry in enumerate(ranked[-10:]):
        ax2.text(scores[position] + (0.012 if scores[position] >= 0 else -0.012),
                 position, "%.2f" % entry["auc"], va="center",
                 ha="left" if scores[position] >= 0 else "right", fontsize=7.5)
    ax2.set_xlim(-0.55, 0.55)
    ax2.set_xlabel("AUC - 0.5  (red: larger value is riskier)", fontsize=9)
    ax2.set_title("(e) Every gas-phase descriptor's single-variable AUC\n"
                  "on the discovery set (%d open-shell rows)"
                  % predictor.get("n_discovery_rows", 0), fontsize=10.5)
    ax2.grid(axis="x", alpha=0.25)

    ax3 = fig.add_subplot(outer[1, 0])
    validation = predictor.get("validation") or {}
    if validation.get("per_row"):
        entries = validation["per_row"]
        positions = range(len(entries))
        for position, entry in zip(positions, entries):
            truth = 1.0 if entry["truth"] else 0.0
            predicted = entry["predicted"]
            correct = predicted is not None and bool(predicted) == bool(entry["truth"])
            ax3.scatter(position, truth, s=90,
                        marker="o" if correct else "X",
                        facecolors=RED if entry["truth"] else "white",
                        edgecolors="#333333", linewidths=1.0, zorder=3)
            if predicted:
                ax3.axvspan(position - 0.42, position + 0.42, color="#f6e3c8", zorder=0)
        ax3.set_xticks(list(positions))
        ax3.set_xticklabels(["%s\n%s" % (entry["name"], entry["state"][:3])
                             for entry in entries], fontsize=7)
        ax3.set_yticks([0, 1])
        ax3.set_yticklabels(["no deficit", "deficit"], fontsize=8)
        ax3.set_ylim(-0.4, 1.45)
        ax3.set_title("(f) Held-out arm: X = the rule got it wrong\n"
                      "shaded columns = the rule predicts a deficit", fontsize=10.5)
    else:
        cross = predictor.get("label_ladder_crosscheck") or {}
        names = list(cross)
        values = [cross[name]["n_disagree"] for name in names]
        ax3.barh(range(len(names)), values, color=ORANGE, height=0.6)
        ax3.set_yticks(range(len(names)))
        ax3.set_yticklabels(names, fontsize=8)
        ax3.set_xlabel("rows whose label changes with the ladder", fontsize=9)
        ax3.set_title("(f) How stable the label is against the ladder", fontsize=10.5)

    ax4 = fig.add_subplot(outer[1, 1])
    ax4.axis("off")
    lines = []
    if chosen:
        lines.append("frozen rule")
        lines.append("  %s %s %.6g" % (chosen["descriptor"],
                                       ">=" if chosen["sign"] == "larger_is_riskier" else "<=",
                                       float(chosen["threshold_frozen"])))
        lines.append("  AUC %.3f on %d rows (%d positive)"
                     % (chosen["auc"], predictor["n_discovery_rows"],
                        predictor["n_discovery_positive"]))
        lines.append("  leave-one-out accuracy %.3f"
                     % chosen["loo_accuracy"])
        beats = predictor.get("chosen_rule_beats_majority_baseline")
        lines.append("  majority-class baseline %.3f"
                     % predictor["baseline_majority_accuracy"])
        lines.append("  beats that baseline? %s"
                     % ("yes" if beats else "NO -- the trivial rule wins"))
        lines.append("  balanced accuracy (tpr/tnr mean) %.3f"
                     % (chosen.get("balanced_accuracy_in_sample") or 0.0))
        lines.append("  physical prior on the sign: %s"
                     % ("kept" if chosen["matches_physical_prior"] else "reversed by the data"))
        permutation = chosen.get("auc_permutation") or {}
        if permutation:
            lines.append("  exact permutation p = %.4f over %s assignments"
                         % (permutation.get("p_value") or 0.0,
                            permutation.get("total_assignments")))
        arm_blocks = (predictor.get("per_arm_diagnostic") or {}).get("arms") or {}
        if arm_blocks:
            lines.append("")
            lines.append("per arm (post hoc, not a forecast)")
            for arm in ("cation", "anion"):
                block = arm_blocks.get(arm) or {}
                top = (block.get("screen") or [{}])[0]
                lines.append("  %-6s %-22s AUC %.3f" 
                             % (arm, top.get("descriptor") or "", top.get("auc") or 0.0))
                lines.append("         risky rows at ranks %s of %s"
                             % ("/".join(str(rank) for rank in (top.get("positive_ranks") or [])),
                                block.get("n_rows")))
                lines.append("         that cut: LOO %.3f vs baseline %.3f"
                             % (top.get("loo_accuracy") or 0.0,
                                block.get("majority_accuracy") or 0.0))
                held = block.get("validation") or {}
                if held:
                    lines.append("         same cut, held out: %.3f vs %.3f (TP %d FP %d)"
                                 % (held.get("accuracy") or 0.0,
                                    held.get("majority_accuracy") or 0.0,
                                    held["confusion_matrix"]["true_positive"],
                                    held["confusion_matrix"]["false_positive"]))
    if validation.get("accuracy") is not None:
        matrix = validation["confusion_matrix"]
        lines.append("")
        lines.append("held-out arm (%d rows, %d positive)"
                     % (validation["n_scored"], predictor["n_validation_positive"]))
        lines.append("  accuracy %.3f" % validation["accuracy"])
        lines.append("  TP %d  FP %d  TN %d  FN %d"
                     % (matrix["true_positive"], matrix["false_positive"],
                        matrix["true_negative"], matrix["false_negative"]))
    ceiling = predictor.get("multivariate_ceiling")
    if ceiling:
        lines.append("")
        lines.append("two-descriptor logistic ceiling")
        lines.append("  features %s" % ", ".join(ceiling["features"]))
        lines.append("  leave-one-out AUC %.3f" % ceiling["loo_auc"])
        if ceiling.get("validation_accuracy") is not None:
            lines.append("  held-out accuracy %.3f" % ceiling["validation_accuracy"])
    ax4.text(0.0, 1.0, "\n".join(lines), va="top", ha="left", fontsize=9.5,
             family="monospace")
    ax4.set_title("(g) The rule and its ceiling", fontsize=10.5, loc="left")

    return save(fig, FIGDIR / "F31_apriori_warning_rule.png")


def write_summary(analysis, predictor, by_state):
    """The per-panel companion text for F30 and F31."""

    flagged = analysis.get("flagged_molecules") or {}
    counts = analysis.get("n_flagged_molecules") or {}
    ladders = analysis.get("ladders") or {}
    per_state = analysis.get("per_state_counts") or {}
    agreement = analysis.get("label_agreement") or {}
    worst_at = analysis.get("worst_negative_at") or ["?", "?", "?"]

    lines = ["# stage16_summary", "",
             "F30 / F31 的逐面板文字 companion。所有数字都从 "
             "`stage16_catalogue_analysis.json` 与 `stage16_predictor.json` 读出，"
             "不手抄。", ""]

    lines += ["## F30 (a) 完整网格", "",
              ("12 个分子 x 3 个电荷态 x %d 个电介质 = %d 个单元格，全部两臂配对成功。"
               "灰色表示两臂一致到 SCF 收敛（|dE| <= 1 meV），红色表示默认初猜落在更高解上"
               "（dE < 0），蓝色表示重启反而更高（dE > 0）。"
               % (len(analysis.get("ladder_all_eps") or []), analysis.get("n_cells") or 0)),
              "",
              "- 一致 %d，MORead 更低 %d，MORead 更高 %d。"
              % (analysis.get("n_coincident") or 0, analysis.get("n_moread_lower") or 0,
                 analysis.get("n_moread_higher") or 0),
              "- 最大赤字 %.6f eV，出现在 %s / %s / eps=%g。"
              % (analysis.get("worst_negative_ev") or 0.0, worst_at[0], worst_at[1],
                 worst_at[2]),
              "- 逐态计数：中性 %d 个赤字、阳离子 %d 个、阴离子 %d 个。"
              % ((per_state.get("neutral") or {}).get("n_moread_lower", 0),
                 (per_state.get("cation") or {}).get("n_moread_lower", 0),
                 (per_state.get("anion") or {}).get("n_moread_lower", 0)),
              ""]

    lines += ["## F30 (b) 逐 (分子, 状态) 的最大赤字", ""]
    rows = [row for row in by_state if row["ladder"] == "ladder10"]
    rows.sort(key=lambda row: float(row["max_drop_ev"] or 0.0))
    for row in rows:
        drop = -float(row["max_drop_ev"] or 0.0)
        if drop <= 1e-3:
            continue
        lines.append("- %s / %s：%.6f eV（首次出现在 eps=%s，共 %s 个电介质命中）"
                     % (row["name"], row["state"], drop,
                        row["eps_flagged"].split(",")[0], row["n_moread_lower"]))
    lines.append("")

    lines += ["## F30 (c) 阈值计数", ""]
    histogram = analysis["magnitude_histogram"]
    for threshold in analysis["magnitude_histogram_thresholds_ev"]:
        lines.append("- 超过 %g eV：%d 个单元格"
                     % (threshold, histogram["%g" % threshold]))
    lines.append("")

    lines += ["## 阶梯依赖", ""]
    for key in ("core3", "focus6", "ladder10"):
        lines.append("- %s（%s）：判为存在漏解的分子 %d/%d -> %s"
                     % (key, "/".join("%g" % value for value in (ladders.get(key) or [])),
                        counts.get(key, 0), analysis.get("n_discovery_molecules") or 0,
                        ", ".join(flagged.get(key) or []) or "无"))
    for pair, entry in sorted(agreement.items()):
        lines.append("- %s：%d/%d 行标签一致%s"
                     % (pair, entry.get("n_rows", 0) - entry.get("n_disagree", 0),
                        entry.get("n_rows", 0),
                        "，差异 " + ", ".join(entry.get("disagreements") or [])
                        if entry.get("disagreements") else ""))
    lines.append("")

    screen = (predictor or {}).get("screen") or []
    chosen = (predictor or {}).get("chosen_rule") or {}
    lines += ["## F31 (d) 选定描述符与冻结阈值", ""]
    if chosen:
        lines.append("- 规则：`%s %s %.6g`"
                     % (chosen.get("descriptor"),
                        ">=" if chosen.get("sign") == "larger_is_riskier" else "<=",
                        float(chosen.get("threshold_frozen") or 0.0)))
        lines.append("- 定义：%s" % (chosen.get("definition") or ""))
        lines.append("- 符号是否与物理先验一致：%s"
                     % ("是" if chosen.get("matches_physical_prior") else "否（被数据反转）"))
        beats = (predictor or {}).get("chosen_rule_beats_majority_baseline")
        lines.append("- 与多数类基线的比较：留一 %.3f vs 基线 %.3f -> %s"
                     % (chosen.get("loo_accuracy") or 0.0,
                        (predictor or {}).get("baseline_majority_accuracy") or 0.0,
                        "**超过**" if beats else "**未超过**（平凡规则更准）"))
        lines.append("- 平衡准确率（sensitivity 与 specificity 的均值；阈值并不按它选）："
                     "样本内 %.3f，平凡单类规则恒为 %.3f"
                     % (chosen.get("balanced_accuracy_in_sample") or 0.0,
                        (predictor or {}).get("trivial_balanced_accuracy") or 0.0))
        permutation = (predictor or {}).get("permutation_test") or {}
        if permutation:
            lines.append("- 精确置换检验：%s，在 %s 种标签指派下 p = %.4f"
                         % (permutation.get("descriptor"), permutation.get("total_assignments"),
                            permutation.get("p_value") or 0.0))
    lines.append("")

    arm_blocks = ((predictor or {}).get("per_arm_diagnostic") or {}).get("arms") or {}
    if arm_blocks:
        lines += ["## F31 (h) 两臂事后诊断（post_hoc，不是预报）", "",
                  "池化规则失败的机制原因："
                  + (((predictor or {}).get("per_arm_diagnostic") or {}).get("note") or ""),
                  "",
                  "| 臂 | 行数 | 正例 | 多数类基线 | 排序最强描述符 | AUC | 正例排名 | "
                  "该描述符留一 | 超过基线 | 精确置换 p |",
                  "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
        for arm in ("cation", "anion"):
            block = arm_blocks.get(arm) or {}
            top = (block.get("screen") or [{}])[0]
            lines.append("| %s | %s | %s | %.3f | `%s` | %.3f | %s | %.3f | %s | %.4f |"
                         % (arm, block.get("n_rows"), block.get("n_positive"),
                            block.get("majority_accuracy") or 0.0,
                            top.get("descriptor") or "", top.get("auc") or 0.0,
                            "/".join(str(rank) for rank in (top.get("positive_ranks") or [])),
                            top.get("loo_accuracy") or 0.0,
                            "是" if top.get("beats_majority_baseline") else "否",
                            top.get("permutation_p") or 0.0))
        lines += ["",
                  "**这两条事后规则也在留出臂上打了分**（同一描述符、同一方向、同一阈值，"
                  "只是换到 6 个没见过的分子上）：",
                  "",
                  "| 臂 | 描述符 | 留出准确率 | 留出基线 | TP/FP/TN/FN | 超过基线 |",
                  "| --- | --- | --- | --- | --- | --- |"]
        for arm in ("cation", "anion"):
            held = (arm_blocks.get(arm) or {}).get("validation") or {}
            if not held:
                continue
            matrix = held["confusion_matrix"]
            lines.append("| %s | `%s` | %.3f | %.3f | %d/%d/%d/%d | %s |"
                         % (arm, held["descriptor"], held["accuracy"],
                            held["majority_accuracy"], matrix["true_positive"],
                            matrix["false_positive"], matrix["true_negative"],
                            matrix["false_negative"],
                            "是" if held["beats_majority_baseline"] else "否"))
        lines += ["",
                  "换句话说：两臂分工这件事在**发现集内**看起来成立，在**留出臂上同样不成立**。"
                  "所以本文给出的机制解释只是解释，不是可以拿去用的筛查规则。",
                  "",
                  "选臂用的量（电荷态）在作业开始前已知，但每臂用哪个描述符、阈值落在哪里"
                  "都是看到标签之后选的："
                  + (((predictor or {}).get("per_arm_diagnostic") or {})
                     .get("arm_selector_note") or ""),
                  ""]

    lines += ["## F31 (e) 单变量筛查", "",
              "| 描述符 | 方向 | AUC | 留一准确率 | 阈值 |",
              "| --- | --- | --- | --- | --- |"]
    for entry in screen:
        lines.append("| `%s` | %s | %.3f | %.3f | %.6g |"
                     % (entry.get("descriptor"),
                        "越大越危险" if entry.get("sign") == "larger_is_riskier"
                        else "越小越危险",
                        entry.get("auc") or 0.0, entry.get("loo_accuracy") or 0.0,
                        float(entry.get("threshold_frozen") or 0.0)))
    lines.append("")

    validation = (predictor or {}).get("validation") or {}
    lines += ["## F31 (f) 留出臂", ""]
    if validation.get("accuracy") is not None:
        matrix = validation.get("confusion_matrix") or {}
        lines.append("- 分子：%s" % ", ".join(validation.get("molecules") or []))
        lines.append("- 准确率 %.3f（%d 行）；TP %d / FP %d / TN %d / FN %d"
                     % (validation.get("accuracy") or 0.0, validation.get("n_scored") or 0,
                        matrix.get("true_positive", 0), matrix.get("false_positive", 0),
                        matrix.get("true_negative", 0), matrix.get("false_negative", 0)))
        for entry in validation.get("per_row") or []:
            lines.append("- %s / %s：描述符 %s，预测 %s，真值 %s"
                         % (entry.get("name"), entry.get("state"),
                            "%.6g" % float(entry.get("value") or 0.0),
                            "有漏解" if entry.get("predicted") else "无漏解",
                            "有漏解" if entry.get("truth") else "无漏解"))
    else:
        lines.append("- 留出臂尚未运行。")
    lines.append("")

    lines += ["## F31 (g) 多变量上限", ""]
    ceiling = (predictor or {}).get("multivariate_ceiling") or {}
    if ceiling:
        lines.append("- 特征：%s" % ", ".join(ceiling.get("features") or []))
        lines.append("- 留一 AUC %.3f" % (ceiling.get("loo_auc") or 0.0))
        if ceiling.get("validation_accuracy") is not None:
            lines.append("- 留出准确率 %.3f" % ceiling["validation_accuracy"])
    else:
        lines.append("- 未计算。")
    lines.append("")

    path = WEEK15 / "stage16_summary.md"
    path.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print("wrote %s (%d bytes)" % (path.relative_to(REPO_ROOT), path.stat().st_size))
    return path


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Stage 16 figures (F30, F31).")
    parser.parse_args(argv)

    analysis = load_json(ANALYSIS_JSON)
    by_state = load_csv(WEEK15 / "stage16_by_state.csv")
    figures = [figure_catalogue(analysis, by_state)]

    predictor = None
    if PREDICTOR_JSON.exists() and DESCRIPTORS_CSV.exists():
        predictor = load_json(PREDICTOR_JSON)
        descriptors = load_csv(DESCRIPTORS_CSV)
        if predictor.get("screen"):
            figures.append(figure_rule(analysis, predictor, descriptors))
    else:
        print("predictor outputs missing; F31 skipped")

    write_summary(analysis, predictor, by_state)

    manifest = WEEK15.parent / "figures" / "figure_manifest_week15_stage16.md"
    inputs = [CELLS_CSV, ANALYSIS_JSON, WEEK15 / "stage16_by_state.csv",
              PREDICTOR_JSON, DESCRIPTORS_CSV]
    lines = ["# figure_manifest_week15_stage16", "",
             "| figure | sha256 | size |", "| --- | --- | --- |"]
    for path in figures:
        lines.append("| `%s` | `%s` | %d B |"
                     % (path.name, sha256(path), path.stat().st_size))
    lines.append("")
    lines.append("| input | sha256 |")
    lines.append("| --- | --- |")
    for path in inputs:
        if path.exists():
            lines.append("| `%s` | `%s` |"
                         % (str(path.relative_to(REPO_ROOT)).replace("\\", "/"), sha256(path)))
    manifest.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("wrote %s" % manifest.relative_to(REPO_ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())