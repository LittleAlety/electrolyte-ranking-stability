r"""Stage 6 figures (F14, F15).

F14 -- where delta_m comes from: the three terms of the plan docx max rule
       (conformer 90th-percentile spread, inter-method spread, 0.05 eV floor)
       for each layer x objective, plus the per-molecule P0 -> P1 shift that
       makes the inter-method term the dominant one.

F15 -- what delta_m does: f_unresolved (both sides), f_robust_inv, Kendall tau_b
       and the Top-k overlap for every layer pair, under the three scenarios
       z_only / floor_only / docx_max.

Labels are ASCII/English on purpose: the workspace has no guaranteed CJK font.

Usage:
    .venv\Scripts\python.exe scripts\make_stage6_figure.py
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
WEEK6 = REPO_ROOT / "outputs" / "week6"
FIGDIR = REPO_ROOT / "outputs" / "figures"
DELTA_JSON = WEEK6 / "delta_m_frozen.json"
STAGE6_JSON = WEEK6 / "stage6_decision_stability.json"
MANIFEST = FIGDIR / "figure_manifest_week6_t9.md"

SCENARIO_COLOR = {"z_only": "#94a3b8", "floor_only": "#38bdf8", "docx_max": "#7c3aed"}
PAIR_LABEL = {"P0_to_P1": "P0 -> P1\n(method)", "P1_to_P2": "P1 -> P2\n(environment)", "C0_to_C1": "C0 -> C1\n(coordination)"}
OX_COLOR = "#2563eb"
RED_COLOR = "#dc2626"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Render figures F14 and F15.")
    parser.add_argument("--outdir", type=Path, default=FIGDIR)
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    return parser.parse_args(argv)


def figure_delta_m(delta: dict, outdir: Path) -> Path:
    per_layer = delta["per_layer"]
    layers = [layer for layer in ("p0", "p1") if layer in per_layer]
    objectives = ["oxidation", "reduction"]

    fig, axes = plt.subplots(1, 2, figsize=(13.0, 5.2))

    ax = axes[0]
    width = 0.35
    x = np.arange(len(layers) * len(objectives))
    tick_labels = []
    conformer, method, floor, maxima = [], [], [], []
    for layer in layers:
        for objective in objectives:
            block = per_layer[layer][objective]
            terms = block["terms"]
            conformer.append(terms.get("conformer_p90_ev") or 0.0)
            method.append(terms.get("method_sigma_ev") or 0.0)
            floor.append(terms["floor_ev"])
            maxima.append(block["delta_m_ev"])
            tick_labels.append("%s\n%s" % (layer.upper(), objective))
    ax.bar(x - width, conformer, width, label="conformer p90 spread", color="#0d9488")
    ax.bar(x, method, width, label="inter-method pstdev (P1-P0)", color="#7c3aed")
    ax.bar(x + width, floor, width, label="0.05 eV floor", color="#94a3b8")
    ax.plot(x, maxima, "kD", markersize=7, label="delta_m = max(terms)")
    for index, value in enumerate(maxima):
        ax.annotate("%.3f" % value, (index, value), textcoords="offset points",
                    xytext=(0, 7), ha="center", fontsize=9)
    ax.set_xticks(x)
    ax.set_xticklabels(tick_labels, fontsize=9)
    ax.set_ylabel("contribution to delta_m [eV]")
    ax.set_title("(a) delta_m terms (plan 6.2 max rule)")
    ax.legend(fontsize=8)
    ax.grid(axis="y", alpha=0.3)

    ax = axes[1]
    for objective, key, color in (("oxidation", "oxidation", OX_COLOR), ("reduction", "reduction", RED_COLOR)):
        block = delta["method_evidence"][key]
        names = [row["name"] for row in block["per_molecule"]]
        shifts = [row["shift_ev"] for row in block["per_molecule"]]
        ax.plot(range(len(names)), shifts, "o-", color=color, label="%s (pstdev %.3f eV)" % (objective, block["sigma_method_ev"]))
    ax.axhline(0.0, color="k", linewidth=0.8)
    ax.set_xticks(range(len(names)))
    ax.set_xticklabels(names, rotation=60, fontsize=8)
    ax.set_ylabel("P1 - P0 shift [eV]")
    ax.set_title("(b) per-molecule inter-method shift")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)

    fig.suptitle("F14  delta_m: conformer vs method vs floor (Stage 6 input)", fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    path = outdir / "F14_delta_m_derivation.png"
    fig.savefig(path, dpi=160)
    plt.close(fig)
    return path


def figure_stage6(stage6: dict, outdir: Path) -> Path:
    results = stage6["results"]
    scenarios = list(results.keys())
    pairs = list(results[scenarios[0]].keys())
    objectives = ["oxidation", "reduction"]

    fig, axes = plt.subplots(1, 2, figsize=(13.5, 5.4))

    ax = axes[0]
    labels = []
    series = {(side, scenario): [] for side in ("lower", "upper") for scenario in scenarios}
    for pair in pairs:
        for objective in objectives:
            labels.append("%s\n%s" % (PAIR_LABEL.get(pair, pair), objective))
            for scenario in scenarios:
                item = results[scenario][pair][objective]
                series[("lower", scenario)].append(item["f_unresolved_lower"])
                series[("upper", scenario)].append(item["f_unresolved_upper"])
    x = np.arange(len(labels))
    width = 0.13
    slot = 0
    for side, hatch in (("lower", ""), ("upper", "//")):
        for scenario in scenarios:
            position = -2.5 * width + slot * width
            ax.bar(x + position, series[(side, scenario)], width,
                   color=SCENARIO_COLOR[scenario], hatch=hatch, edgecolor="white",
                   label="%s (%s)" % (side, scenario))
            slot += 1
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=8)
    ax.set_ylabel("f_unresolved")
    ax.set_ylim(0, 1.05)
    ax.set_title("(a) unresolved-pair fraction vs delta_m")
    ax.legend(fontsize=7, ncol=2)
    ax.grid(axis="y", alpha=0.3)

    ax = axes[1]
    values_robust, values_tau, values_ov = [], [], []
    for pair in pairs:
        for objective in objectives:
            item = results["docx_max"][pair][objective]
            values_robust.append(item["f_robust_inv"])
            values_tau.append(item["kendall_tau_b"])
            values_ov.append(item["top_k"]["k=0.20"]["overlap"])
    x = np.arange(len(labels))
    width = 0.26
    ax.bar(x - width, values_tau, width, label="Kendall tau_b", color="#7c3aed")
    ax.bar(x, values_ov, width, label="Top-20% overlap", color="#0d9488")
    ax.bar(x + width, values_robust, width, label="f_robust_inv", color="#dc2626")
    ax.axhline(0.0, color="k", linewidth=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=8)
    ax.set_title("(b) rank agreement at delta_m = docx_max")
    ax.legend(fontsize=8)
    ax.grid(axis="y", alpha=0.3)

    fig.suptitle("F15  Stage 6 decision stability: what the fixed tolerance changes", fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    path = outdir / "F15_stage6_decision_metrics.png"
    fig.savefig(path, dpi=160)
    plt.close(fig)
    return path


def main(argv=None) -> int:
    args = parse_args(argv)
    args.outdir.mkdir(parents=True, exist_ok=True)

    with io.open(DELTA_JSON, encoding="utf-8") as handle:
        delta = json.load(handle)
    with io.open(STAGE6_JSON, encoding="utf-8") as handle:
        stage6 = json.load(handle)

    f14 = figure_delta_m(delta, args.outdir)
    f15 = figure_stage6(stage6, args.outdir)

    lines = []
    lines.append("# Figure manifest - Stage 6 / T9 (F14, F15)")
    lines.append("")
    lines.append("| figure | file | figure SHA256 | inputs (SHA256) |")
    lines.append("| --- | --- | --- | --- |")
    lines.append("| F14 | `%s` | %s | `delta_m_frozen.json` %s |"
                 % (f14.name, sha256(f14), sha256(DELTA_JSON)))
    lines.append("| F15 | `%s` | %s | `stage6_decision_stability.json` %s |"
                 % (f15.name, sha256(f15), sha256(STAGE6_JSON)))
    lines.append("")
    lines.append("F14 panel (a): the three delta_m contributions and the max rule; "
                 "the max is marked with a diamond and annotated. Panel (b): the "
                 "per-molecule P1 - P0 shift whose population spread is the "
                 "inter-method term.")
    lines.append("")
    lines.append("F15 panel (a): f_unresolved for the lower and upper side of every "
                 "layer pair under delta_m = 0 / 0.05 eV / docx max. Panel (b): the "
                 "rank-agreement metrics at the docx max tolerance. f_robust_inv is "
                 "zero everywhere, which is a statement about the denominator as much "
                 "as about the ranking.")
    args.manifest.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("[F14] %s" % f14)
    print("[F15] %s" % f15)
    print("[manifest] %s" % args.manifest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())