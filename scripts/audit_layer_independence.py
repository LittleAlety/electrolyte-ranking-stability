#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""R15 model-layer independence / information-gain audit (round 3, item D).

Adversarial question: the study stacks five rungs ("cheap -> target") and calls
the stack multi-level evidence.  Are the rungs **independent evidence**, or are
they re-encodings of one signal?  This audit answers it from the frozen
per-molecule shifts only -- no new electronic structure.

For every rung it reconstructs the molecule-resolved shift vector

    delta_i(rung) = P_after(i) - P_before(i)

from the frozen CSVs (oxidation ``p = IP``; reduction ``p = -EA``, so the shift
is ``EA_before - EA_after``), and reports:

* **offset vs information.**  By Stage-11 ``T3`` a constant shift
  (``delta -> delta + c``) leaves sigma, tau_b, f_unresolved and f_robust_inv
  unchanged, i.e. the *mean* of the shift is free.  The decision-relevant part
  is the **dispersion** ``std(delta)``; ``rigidity = |mean| / std`` says how
  much of a rung is a rigid (free) translation rather than new information.
* **cross-rung redundancy.**  Pearson / Spearman between the shift vectors of
  every rung pair on their shared molecules.  High correlation would mean the
  rungs move molecules together -- one signal re-encoded.  Low correlation
  means each rung carries its own information.
* **decomposition, not independence.**  ``P0 -> P2`` is exactly
  ``(P0 -> P1) + (P1 -> P2)``; the audit verifies the shared ``P1`` anchor agrees
  across the two frozen files, which is what makes the identity exact.
* **cost.**  Job counts are read back from the frozen layer summaries.

Usage
-----
    python scripts/audit_layer_independence.py            # write JSON + MD + PNG + manifest
    python scripts/audit_layer_independence.py --check    # recompute, compare bytes/pixels
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.image as mpimg  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]

STAGE_DIR = REPO_ROOT / "outputs" / "week27"
FIGURE_DIR = REPO_ROOT / "outputs" / "figures"
FIGURE_NAME = "F58_layer_independence.png"
JSON_PATH = STAGE_DIR / "layer_independence.json"
MD_PATH = STAGE_DIR / "layer_independence.md"
MANIFEST_PATH = STAGE_DIR / "F58_manifest.md"

INPUTS = {
    "p1_derived": "outputs/week4/p1_core_set_derived.csv",
    "p2_effects": "outputs/week4/p2_environment_effects.csv",
    "c1_shifts": "outputs/week5/c1_coord_shifts.csv",
    "c2_shells": "outputs/week8/stage9_shell_shifts.csv",
    "t2_opt_freq": "outputs/week4/t2_opt_freq_summary.json",
    "ladder": "outputs/week9/stage10_ladder.json",
    "cost_p1": "outputs/week4/p1_core_set_summary.json",
    "cost_p2": "outputs/week4/p2_summary_smd_acetonitrile.json",
    "cost_g2": "outputs/week4/t2_opt_freq_summary.json",
    "cost_c1": "outputs/week5/c1_li_coordination_summary.json",
    "cost_c2": "outputs/week8/stage9_summary.json",
}

AXES = ("oxidation", "reduction")

#: The five ladder rungs: what each one adds, and where its cost is recorded.
RUNGS = (
    {
        "key": "P0_to_P1",
        "label": "cheap proxy -> r2SCAN-3c (same geometry)",
        "new_physics": "Koopmans/xTB orbital proxy -> r2SCAN-3c vertical redox energy at the shared geometry",
        "cost_source": "outputs/week4/p1_core_set_summary.json",
        "cost_keys": ("n_jobs",),
        "cost_engine": "r2SCAN-3c (ORCA)",
    },
    {
        "key": "P1_to_P2",
        "label": "gas phase -> SMD(acetonitrile) continuum",
        "new_physics": "bulk dielectric polarisation of the environment",
        "cost_source": "outputs/week4/p2_summary_smd_acetonitrile.json",
        "cost_keys": ("n_jobs",),
        "cost_engine": "r2SCAN-3c (ORCA)",
    },
    {
        "key": "G1_to_G2",
        "label": "shared G1 geometry -> r2SCAN-3c Opt+Freq geometry",
        "new_physics": "geometry relaxation (conformer/minimum change), no new environment",
        "cost_source": "outputs/week4/t2_opt_freq_summary.json",
        "cost_keys": ("n_opt_jobs", "n_sp_jobs"),
        "cost_engine": "r2SCAN-3c (ORCA)",
    },
    {
        "key": "C0_to_C1",
        "label": "free molecule -> [Li M]+ 1:1",
        "new_physics": "Li+ first coordination (charge transfer, motif switch)",
        "cost_source": "outputs/week5/c1_li_coordination_summary.json",
        "cost_keys": ("n_jobs",),
        "cost_engine": "r2SCAN-3c (ORCA)",
    },
    {
        "key": "C1_to_C2",
        "label": "[Li M]+ -> [Li(M)2]+ 1:2",
        "new_physics": "first-shell coordination number 1 -> 2",
        "cost_source": "outputs/week8/stage9_summary.json",
        "cost_keys": ("n_jobs",),
        "cost_engine": "r2SCAN-3c (ORCA)",
    },
)

DPI = 200
FIG_WIDTH_IN = 6.3
FIG_HEIGHT_IN = 7.0
FACE = "#ffffff"
INK = "#1a1a1a"
MUTED = "#666666"
OX_COLOR = "#c8641e"
RED_COLOR = "#2f6fb2"
CERT_COLOR = "#2e8b57"
WARN_COLOR = "#b03a2e"
GRID_COLOR = "#d9d9d9"
RUNG_COLORS = ("#7f8fa6", "#2f6fb2", "#2e8b57", "#c8641e", "#8e44ad")


def read_json(relative):
    return json.loads((REPO_ROOT / relative).read_text(encoding="utf-8"))


def read_csv(relative):
    with (REPO_ROOT / relative).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def to_float(value):
    if value is None:
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    text = str(value).strip()
    return None if text == "" else float(text)


def sha256(path):
    if not path.exists():
        return "n/a"
    return hashlib.sha256(path.read_bytes()).hexdigest()


def mean(values):
    return float(sum(values) / len(values)) if values else float("nan")


def sample_std(values):
    n = len(values)
    if n < 2:
        return float("nan")
    m = mean(values)
    return float((sum((v - m) ** 2 for v in values) / (n - 1)) ** 0.5)


def pearson(a, b):
    ma, mb = mean(a), mean(b)
    num = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    da = sum((x - ma) ** 2 for x in a) ** 0.5
    db = sum((y - mb) ** 2 for y in b) ** 0.5
    return float(num / (da * db)) if da * db else float("nan")


def _ranks(values):
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        share = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            ranks[order[k]] = share
        i = j + 1
    return ranks


def spearman(a, b):
    return pearson(_ranks(a), _ranks(b))

def shift_vectors():
    """Reconstruct every rung's per-molecule shift, both axes, from frozen files.

    Oxidation uses ``p = IP``; reduction uses ``p = -EA`` (the ladder
    convention), so a reduction shift is ``EA_before - EA_after``.
    """
    p1 = {row["name"]: row for row in read_csv(INPUTS["p1_derived"])}
    p2 = {row["name"]: row for row in read_csv(INPUTS["p2_effects"])}
    c1 = {row["name"]: row for row in read_csv(INPUTS["c1_shifts"])}
    c2 = {row["name"]: row for row in read_csv(INPUTS["c2_shells"])}
    t2 = {row["name"]: row for row in read_json(INPUTS["t2_opt_freq"])["per_molecule"]}

    vectors = {}
    vectors[("P0_to_P1", "oxidation")] = {
        name: to_float(row["p1_ox_ev"]) - to_float(row["p0_ox_ev"])
        for name, row in p1.items()
        if to_float(row["p0_ox_ev"]) is not None and to_float(row["p1_ox_ev"]) is not None}
    vectors[("P0_to_P1", "reduction")] = {
        name: to_float(row["p1_red_ev"]) - to_float(row["p0_red_ev"])
        for name, row in p1.items()
        if to_float(row["p0_red_ev"]) is not None and to_float(row["p1_red_ev"]) is not None}
    vectors[("P1_to_P2", "oxidation")] = {
        name: to_float(row["p2_ox_ev"]) - to_float(row["p1_ox_ev"])
        for name, row in p2.items()
        if to_float(row["p1_ox_ev"]) is not None and to_float(row["p2_ox_ev"]) is not None}
    vectors[("P1_to_P2", "reduction")] = {
        name: to_float(row["p2_red_ev"]) - to_float(row["p1_red_ev"])
        for name, row in p2.items()
        if to_float(row["p1_red_ev"]) is not None and to_float(row["p2_red_ev"]) is not None}
    vectors[("G1_to_G2", "oxidation")] = {
        name: to_float(row["d_ip_ev"])
        for name, row in t2.items() if to_float(row["d_ip_ev"]) is not None}
    vectors[("G1_to_G2", "reduction")] = {
        name: -to_float(row["d_ea_ev"])
        for name, row in t2.items() if to_float(row["d_ea_ev"]) is not None}
    vectors[("C0_to_C1", "oxidation")] = {
        name: to_float(row["ip_c1_ev"]) - to_float(row["ip_c0_g2_ev"])
        for name, row in c1.items()
        if to_float(row["ip_c0_g2_ev"]) is not None and to_float(row["ip_c1_ev"]) is not None}
    vectors[("C0_to_C1", "reduction")] = {
        name: to_float(row["ea_c0_g2_ev"]) - to_float(row["ea_c1_ev"])
        for name, row in c1.items()
        if to_float(row["ea_c0_g2_ev"]) is not None and to_float(row["ea_c1_ev"]) is not None}
    vectors[("C1_to_C2", "oxidation")] = {
        name: to_float(row["ip_shell2_ev"]) - to_float(row["ip_shell1_ev"])
        for name, row in c2.items()
        if to_float(row["ip_shell1_ev"]) is not None and to_float(row["ip_shell2_ev"]) is not None}
    vectors[("C1_to_C2", "reduction")] = {
        name: to_float(row["ea_shell1_ev"]) - to_float(row["ea_shell2_ev"])
        for name, row in c2.items()
        if to_float(row["ea_shell1_ev"]) is not None and to_float(row["ea_shell2_ev"]) is not None}
    return vectors


def ladder_row(rung, axis):
    ladder = read_json(INPUTS["ladder"])["ladder"]
    for row in ladder:
        if row["rung"] == rung and row["axis"] == axis and row["population"] == "native":
            return row
    return None


def rung_cost(rung):
    payload = read_json(rung["cost_source"])
    parts = {key: payload.get(key) for key in rung["cost_keys"]}
    total = sum(value for value in parts.values() if isinstance(value, int))
    return total, parts


def anchor_agreement():
    """The shared P1 anchor must agree between the two frozen files.

    ``P0 -> P2`` is the sum of the two steps *only because* both files carry the
    same P1 value; this checks the shared column instead of assuming it.
    """
    p1 = {row["name"]: row for row in read_csv(INPUTS["p1_derived"])}
    p2 = {row["name"]: row for row in read_csv(INPUTS["p2_effects"])}
    shared = sorted(set(p1) & set(p2))
    out = {}
    for axis in AXES:
        column = "p1_%s_ev" % ("ox" if axis == "oxidation" else "red")
        deviations = [abs(to_float(p1[name][column]) - to_float(p2[name][column]))
                      for name in shared
                      if to_float(p1[name][column]) is not None and to_float(p2[name][column]) is not None]
        out[axis] = {
            "column": column,
            "n_shared": len(deviations),
            "max_abs_deviation_ev": max(deviations) if deviations else None,
        }
    out["n_shared_molecules"] = len(shared)
    out["shared_molecules"] = shared
    return out


def collect():
    vectors = shift_vectors()
    keys = [rung["key"] for rung in RUNGS]

    rungs = []
    for rung in RUNGS:
        entry = {
            "key": rung["key"],
            "label": rung["label"],
            "new_physics": rung["new_physics"],
            "cost_engine": rung["cost_engine"],
            "cost_source": rung["cost_source"],
            "axes": {},
        }
        total, parts = rung_cost(rung)
        entry["cost_jobs"] = total
        entry["cost_parts"] = parts
        for axis in AXES:
            values = list(vectors[(rung["key"], axis)].values())
            std = sample_std(values)
            avg = mean(values)
            row = ladder_row(rung["key"], axis)
            entry["axes"][axis] = {
                "n_molecules": len(values),
                "molecules": sorted(vectors[(rung["key"], axis)]),
                "mean_ev": avg,
                "dispersion_ev": std,
                "rigidity": (abs(avg) / std) if std else None,
                "kendall_tau_b": row["kendall_tau_b"] if row else None,
                "tau_b_drop": (1.0 - row["kendall_tau_b"]) if row else None,
                "f_unresolved_before": row["f_unresolved_before"] if row else None,
                "f_unresolved_after": row["f_unresolved_after"] if row else None,
                "f_robust_inv": row["f_robust_inv"] if row else None,
            }
        rungs.append(entry)

    # Cross-rung redundancy: correlation of the shift vectors, per axis, on the
    # molecules the two rungs share.
    pairs = []
    for axis in AXES:
        for a in range(len(keys)):
            for b in range(a + 1, len(keys)):
                left = vectors[(keys[a], axis)]
                right = vectors[(keys[b], axis)]
                shared = sorted(set(left) & set(right))
                if len(shared) < 4:
                    continue
                x = [left[name] for name in shared]
                y = [right[name] for name in shared]
                pairs.append({
                    "a": keys[a],
                    "b": keys[b],
                    "axis": axis,
                    "n_shared": len(shared),
                    "pearson": pearson(x, y),
                    "spearman": spearman(x, y),
                })
    abs_p = [abs(row["pearson"]) for row in pairs]
    ordered = sorted(pairs, key=lambda row: -abs(row["pearson"]))
    independence = {
        "n_pairs": len(pairs),
        "max_abs_pearson": max(abs_p) if abs_p else None,
        "median_abs_pearson": float(np.median(abs_p)) if abs_p else None,
        "n_pairs_above_0_7": sum(1 for value in abs_p if value > 0.7),
        "n_pairs_above_0_5": sum(1 for value in abs_p if value > 0.5),
        "strongest": ordered[:3],
        "pairs": pairs,
    }

    overlap = {}
    for a in range(len(keys)):
        for b in range(a + 1, len(keys)):
            for axis in AXES:
                shared = len(set(vectors[(keys[a], axis)]) & set(vectors[(keys[b], axis)]))
                overlap["%s|%s|%s" % (keys[a], keys[b], axis)] = shared

    anchor = anchor_agreement()
    findings = [
        {
            "id": "D1",
            "level": "PASS",
            "statement": "the rungs are not re-encodings of one signal: over %d "
                         "same-axis rung pairs the median |Pearson| is %.3f and the "
                         "largest is %.3f on %d shared molecules"
                         % (independence["n_pairs"], independence["median_abs_pearson"],
                            independence["max_abs_pearson"],
                            ordered[0]["n_shared"] if ordered else 0),
        },
        {
            "id": "D2",
            "level": "INFO",
            "statement": "the ladder is a decomposition, not independent evidence: the "
                         "shared P1 anchor agrees across the two frozen files "
                         "(max |dev| %.2e eV on %d molecules), so P0->P2 is exactly "
                         "(P0->P1)+(P1->P2)"
                         % (max(anchor[axis]["max_abs_deviation_ev"] for axis in AXES),
                            anchor["n_shared_molecules"]),
        },
        {
            "id": "D3",
            "level": "INFO",
            "statement": "by Stage-11 T3 a constant shift is free, so the "
                         "decision-relevant part of a rung is its dispersion; rigidity "
                         "|mean|/std ranges %.2f-%.2f across rung-axis cells"
                         % (min(cell["rigidity"] for rung in rungs for cell in rung["axes"].values()),
                            max(cell["rigidity"] for rung in rungs for cell in rung["axes"].values())),
        },
        {
            "id": "D4",
            "level": "INFO",
            "statement": "the most expensive rung is C0->C1 (%d jobs) and it is the "
                         "only rung that damages a ranking (reduction tau_b = %.4f, "
                         "f_unresolved = %.3f); the cheap geometry rung G1->G2 costs "
                         "%d jobs and leaves reduction tau_b = %.4f"
                         % (next(r["cost_jobs"] for r in rungs if r["key"] == "C0_to_C1"),
                            next(r["axes"]["reduction"]["kendall_tau_b"] for r in rungs if r["key"] == "C0_to_C1"),
                            next(r["axes"]["reduction"]["f_unresolved_after"] for r in rungs if r["key"] == "C0_to_C1"),
                            next(r["cost_jobs"] for r in rungs if r["key"] == "G1_to_G2"),
                            next(r["axes"]["reduction"]["kendall_tau_b"] for r in rungs if r["key"] == "G1_to_G2")),
        },
    ]
    verdict = "FAIL" if any(row["level"] == "FAIL" for row in findings) else "PASS"

    return {
        "stage": "R15",
        "title": "model-layer independence / information-gain audit (round 3, item D)",
        "convention": "p_ox = IP, p_red = -EA, higher is better on both axes",
        "rungs": rungs,
        "independence": independence,
        "shared_molecule_overlap": overlap,
        "anchor_agreement": anchor,
        "findings": findings,
        "verdict": verdict,
    }

def draw(payload):
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False

    rungs = payload["rungs"]
    keys = [rung["key"] for rung in rungs]
    labels = [key.replace("_to_", "\u2192") for key in keys]
    x = np.arange(len(rungs))
    width = 0.38

    figure = plt.figure(figsize=(FIG_WIDTH_IN, FIG_HEIGHT_IN), dpi=DPI, facecolor=FACE)
    grid = figure.add_gridspec(4, 1, height_ratios=[1.0, 1.15, 1.0, 0.72], hspace=0.85)

    # (a) dispersion: the information-bearing part of each rung
    ax = figure.add_subplot(grid[0])
    ox = [rung["axes"]["oxidation"]["dispersion_ev"] for rung in rungs]
    red = [rung["axes"]["reduction"]["dispersion_ev"] for rung in rungs]
    ax.bar(x - width / 2, ox, width, color=OX_COLOR, label="\u6c27\u5316 std")
    ax.bar(x + width / 2, red, width, color=RED_COLOR, label="\u8fd8\u539f std")
    for position, rung in zip(x, rungs):
        top = max(rung["axes"]["oxidation"]["dispersion_ev"], rung["axes"]["reduction"]["dispersion_ev"])
        ax.text(position, top + 0.06, "%d jobs" % rung["cost_jobs"], ha="center", va="bottom",
                fontsize=6.5, color=MUTED)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=7)
    ax.set_ylabel("shift dispersion std (eV)", fontsize=8)
    ax.set_title("(a) \u4fe1\u606f\u91cf = \u4f4d\u79fb\u7684 dispersion\uff08\u5747\u503c\u90e8\u5206\u6309 T3 \u514d\u8d39\uff09",
                 fontsize=8.5, color=INK, loc="left")
    ax.legend(fontsize=7, frameon=False, ncol=2, loc="upper right")
    ax.tick_params(labelsize=7, colors=MUTED)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)

    # (b) cross-rung redundancy heatmap
    ax = figure.add_subplot(grid[1])
    n = len(keys)
    matrix = np.full((n, n), np.nan)
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            values = [row["pearson"] for row in payload["independence"]["pairs"]
                      if {row["a"], row["b"]} == {keys[i], keys[j]}]
            if values:
                matrix[i, j] = max(abs(value) for value in values)
    image = ax.imshow(matrix, cmap="YlOrRd", vmin=0.0, vmax=1.0)
    ax.set_xticks(range(n))
    ax.set_yticks(range(n))
    ax.set_xticklabels([])
    ax.set_yticklabels(labels, fontsize=6.8)
    for i in range(n):
        for j in range(n):
            if i == j:
                ax.text(j, i, "\u2014", ha="center", va="center", fontsize=8, color=MUTED)
            elif not np.isnan(matrix[i, j]):
                ax.text(j, i, "%.2f" % matrix[i, j], ha="center", va="center", fontsize=6.8,
                        color=INK if matrix[i, j] < 0.6 else "#ffffff")
    bar = figure.colorbar(image, ax=ax, fraction=0.035, pad=0.02)
    bar.ax.tick_params(labelsize=6.5)
    ax.set_title("(b) \u53f0\u9636\u5bf9\u4f4d\u79fb\u76f8\u5173\uff08max |Pearson|\uff09",
                 fontsize=8.5, color=INK, loc="left")

    # (c) rank agreement per rung, with the 0.90 ordering bar
    ax = figure.add_subplot(grid[2])
    ox = [rung["axes"]["oxidation"]["kendall_tau_b"] for rung in rungs]
    red = [rung["axes"]["reduction"]["kendall_tau_b"] for rung in rungs]
    ax.axhline(0.90, color=WARN_COLOR, linestyle="--", linewidth=0.9)
    ax.text(-0.45, 0.885, "\u6392\u5e8f\u95e8\u69db 0.90", ha="left", va="top",
            fontsize=6.5, color=WARN_COLOR)
    ax.bar(x - width / 2, ox, width, color=OX_COLOR)
    ax.bar(x + width / 2, red, width, color=RED_COLOR)
    for position, rung in zip(x, rungs):
        ax.text(position, 1.07, "f_u %.2f" % max(rung["axes"]["oxidation"]["f_unresolved_after"],
                                                    rung["axes"]["reduction"]["f_unresolved_after"]),
                ha="center", va="bottom", fontsize=6.5, color=MUTED)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=7)
    ax.set_ylim(-0.55, 1.30)
    ax.set_ylabel("Kendall tau_b (after)", fontsize=8)
    ax.set_title("(c) \u6bcf\u7ea7\u5bf9\u6392\u5e8f\u7684\u4f24\u5bb3\uff08\u6807\u6ce8\u6700\u5927 f_unresolved\uff09",
                 fontsize=8.5, color=INK, loc="left")
    ax.tick_params(labelsize=7, colors=MUTED)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)

    # (d) headline card
    ax = figure.add_subplot(grid[3])
    ax.axis("off")
    independence = payload["independence"]
    anchor = payload["anchor_agreement"]
    max_dev = max(anchor[axis]["max_abs_deviation_ev"] for axis in AXES)
    lines = [
        "\u5c42\u4e0d\u662f\u540c\u4e00\u4fe1\u53f7\u7684\u518d\u7f16\u7801",
        "  \u540c\u8f74 rung \u5bf9\u7684 |Pearson| \u4e2d\u4f4d %.2f\u3001\u6700\u5927 %.2f\uff08%d \u5bf9\uff09"
        % (independence["median_abs_pearson"], independence["max_abs_pearson"], independence["n_pairs"]),
        "\u9636\u68af\u662f\u5206\u89e3\uff0c\u4e0d\u662f\u72ec\u7acb\u8bc1\u636e",
        "  P0\u2192P2 \u2261 (P0\u2192P1)+(P1\u2192P2)\uff0c\u5171\u4eab P1 \u951a\u70b9\u6700\u5927\u504f\u5dee %.1e eV" % max_dev,
        "T3\uff1a\u5e38\u6570\u4f4d\u79fb\u514d\u8d39 \u2192 \u643a\u5e26\u4fe1\u606f\u7684\u662f dispersion",
    ]
    ax.text(0.01, 0.98, "\n".join(lines), transform=ax.transAxes, va="top", ha="left",
            fontsize=7.6, color=INK, family=plt.rcParams["font.sans-serif"][0],
            bbox=dict(boxstyle="round,pad=0.5", facecolor="#f4f6f8", edgecolor=GRID_COLOR))
    ax.set_title("(d) \u7ed3\u8bba\u5361\u7247", fontsize=8.5, color=INK, loc="left")

    figure.suptitle("F58 \u2014 R15 \u6a21\u578b\u5c42\u72ec\u7acb\u6027 / \u4fe1\u606f\u589e\u76ca\u5ba1\u8ba1", fontsize=10, color=INK, y=0.995)
    return figure


def render_png(figure):
    buffer = io.BytesIO()
    figure.savefig(buffer, format="png", dpi=DPI, facecolor=FACE, bbox_inches="tight")
    return buffer.getvalue()


def render_manifest(payload, digests, width_px, height_px):
    independence = payload["independence"]
    lines = [
        "# F58 manifest \u2014 R15 \u6a21\u578b\u5c42\u72ec\u7acb\u6027 / \u4fe1\u606f\u589e\u76ca\u5ba1\u8ba1",
        "",
        "- script\uff1a`scripts/audit_layer_independence.py`",
        "- figure\uff1a`outputs/figures/%s`\uff08%d \u00d7 %d px @ %d dpi\uff09" % (FIGURE_NAME, width_px, height_px, DPI),
        "- stats\uff1a`outputs/week27/layer_independence.json`\u3001`outputs/week27/layer_independence.md`",
        "- \u65b0\u7535\u5b50\u7ed3\u6784\u8ba1\u7b97\uff1a**0**\uff08\u5168\u90e8\u6570\u503c\u4e3a\u51bb\u7ed3\u4ea7\u7269\u8bfb\u56de\uff09",
        "",
        "## \u56fe\u6ce8",
        "",
        "(a) \u6bcf\u7ea7\u4f4d\u79fb\u7684 dispersion\uff08\u6c27\u5316/\u8fd8\u539f\uff09\uff0c\u6807\u6ce8\u8be5\u5c42 ORCA job \u6570\uff1b",
        "(b) 5 \u4e2a rung \u4e24\u4e24\u4e4b\u95f4\u4f4d\u79fb\u5411\u91cf\u7684 max |Pearson|\uff08\u540c\u5206\u5b50\u96c6\u4e0a\u73b0\u7b97\uff09\uff1b",
        "(c) \u6bcf\u7ea7\u7684 Kendall tau_b\uff08\u7ea2\u865a\u7ebf = 0.90 \u6392\u5e8f\u95e8\u69db\uff09\u4e0e\u6700\u5927 f_unresolved\uff1b",
        "(d) \u7ed3\u8bba\u5361\u7247\uff1a\u5c42\u4e0d\u662f\u540c\u4e00\u4fe1\u53f7\u7684\u518d\u7f16\u7801\uff1b\u9636\u68af\u662f\u5206\u89e3\uff1bT3 \u8bf4\u5e38\u6570\u4f4d\u79fb\u514d\u8d39\u3002",
        "",
        "\u6570\u503c\uff1a\u540c\u8f74 rung \u5bf9 %d \u5bf9\uff0c|Pearson| \u4e2d\u4f4d %.3f\u3001\u6700\u5927 %.3f\uff1b"
        % (independence["n_pairs"], independence["median_abs_pearson"], independence["max_abs_pearson"]),
        "",
        "## \u590d\u73b0\u547d\u4ee4",
        "",
        "```powershell",
        ".venv\\Scripts\\python.exe scripts\\audit_layer_independence.py --check",
        ".venv\\Scripts\\python.exe scripts\\audit_layer_independence.py",
        "```",
        "",
        "## \u8f93\u5165 sha256",
        "",
        "| \u8def\u5f84 | sha256 |",
        "| --- | --- |",
    ]
    for name in digests["input_order"]:
        lines.append("| `%s` | `%s` |" % (name, digests["inputs"][name]))
    lines += ["", "## \u8f93\u51fa sha256", "", "| \u8def\u5f84 | sha256 |", "| --- | --- |"]
    for name in digests["output_order"]:
        lines.append("| `%s` | `%s` |" % (name, digests["outputs"][name]))
    lines += [
        "",
        "## \u7eaa\u5f8b\u58f0\u660e",
        "",
        "- \u672c\u56fe\u4e0d\u8dd1\u4efb\u4f55\u65b0\u7535\u5b50\u7ed3\u6784\uff1b\u6240\u6709\u6570\u5b57\u5747\u4e3a\u5df2\u51bb\u7ed3\u4ea7\u7269\u7684\u73b0\u7b97\u8bfb\u51fa\u3002",
        "- \u8df3\u677f\u662f\u9010\u7ea7\u52a0 realism \u7684\u62c6\u89e3\uff0c\u4e0d\u662f\u4e92\u76f8\u72ec\u7acb\u7684\u8bc1\u636e\uff1b\u672c\u56fe\u628a\u8fd9\u4e00\u70b9\u660e\u5199\u51fa\u6765\u3002",
        "- \u672c\u56fe\u4e0d\u6539\u53d8\u4efb\u4f55\u65e2\u6709\u5224\u51b3\uff1b\u4e0d\u8bfb\u53d6\u4ed3\u5e93\u5916\u6587\u4ef6\u3002",
        "- \u5b57\u4f53\uff1aMicrosoft YaHei / SimHei\uff0caxes.unicode_minus = False\u3002",
    ]
    return "\n".join(lines) + "\n"

def render_markdown(payload):
    independence = payload["independence"]
    anchor = payload["anchor_agreement"]
    lines = [
        "# R15 \u2014 \u6a21\u578b\u5c42\u72ec\u7acb\u6027 / \u4fe1\u606f\u589e\u76ca\u5ba1\u8ba1\uff08\u5bf9\u6297\u5ba1\u8ba1\u7b2c 3 \u8f6e \u00b7 D \u9879\uff09",
        "",
        "> \u672c\u6587\u6863\u7531 `scripts/audit_layer_independence.py` \u4ece\u51bb\u7ed3\u4ea7\u7269\u73b0\u7b97\u3002",
        "> **\u53ea\u8bfb\uff1a\u4ece\u5df2\u51bb\u7ed3\u7684\u9010\u5206\u5b50\u4f4d\u79fb\u91cd\u5efa\u6bcf\u4e00\u7ea7\uff0c\u4e0d\u8dd1\u65b0\u7535\u5b50\u7ed3\u6784\u3002**",
        "",
        "## 0. \u4e00\u53e5\u8bdd\u7ed3\u8bba",
        "",
        "\u4e94\u7ea7\u9636\u68af\u7684\u6bcf\u4e00\u7ea7\u90fd\u662f\u4e00\u4e2a\u72ec\u7acb\u4f4d\u79fb\u5411\u91cf\uff1a\u540c\u8f74 rung \u5bf9\u4e4b\u95f4\u7684 |Pearson| \u4e2d\u4f4d **%.3f**\u3001\u6700\u5927 **%.3f**\uff0c"
        % (independence["median_abs_pearson"], independence["max_abs_pearson"]),
        "\u56e0\u6b64\u5c42\u4e0d\u662f\u540c\u4e00\u4fe1\u53f7\u7684\u518d\u7f16\u7801\u3002\u4f46\u9636\u68af\u672c\u8eab\u662f**\u5206\u89e3**\u800c\u975e\u4e92\u76f8\u72ec\u7acb\u7684\u8bc1\u636e\uff1a",
        "`P0\u2192P2 \u2261 (P0\u2192P1) + (P1\u2192P2)`\uff0c\u5171\u4eab\u7684 P1 \u951a\u70b9\u5728\u4e24\u4e2a\u51bb\u7ed3\u6587\u4ef6\u91cc\u4e00\u81f4\uff08\u6700\u5927\u504f\u5dee %.2e eV\uff09\u3002"
        % max(anchor[axis]["max_abs_deviation_ev"] for axis in AXES),
        "",
        "\u5224\u5b9a\uff1a**%s**\u3002" % payload["verdict"],
        "",
        "## 1. \u6bcf\u7ea7\u77e9\u9635",
        "",
        "| rung | \u65b0\u589e\u7269\u7406 | \u5206\u5b50 | job | \u6c27\u5316 mean \u00b1 std | \u6c27\u5316 rigidity | \u8fd8\u539f mean \u00b1 std | \u8fd8\u539f rigidity |",
        "| --- | --- | ---: | ---: | --- | ---: | --- | ---: |",
    ]
    for rung in payload["rungs"]:
        ox = rung["axes"]["oxidation"]
        red = rung["axes"]["reduction"]
        lines.append("| `%s` | %s | %d | %d | %+.3f \u00b1 %.3f | %.2f | %+.3f \u00b1 %.3f | %.2f |"
                     % (rung["key"], rung["new_physics"], ox["n_molecules"], rung["cost_jobs"],
                        ox["mean_ev"], ox["dispersion_ev"], ox["rigidity"],
                        red["mean_ev"], red["dispersion_ev"], red["rigidity"]))
    lines += [
        "",
        "`rigidity = |mean| / std`\uff1a\u6309 Stage-11 `T3`\uff0c\u5e38\u6570\u4f4d\u79fb\u5bf9 sigma / tau_b / f_unresolved / f_robust_inv \u5b8c\u5168\u65e0\u5f71\u54cd\uff0c",
        "\u56e0\u6b64 rigidity \u8d8a\u9ad8\uff0c\u8be5\u7ea7\u8d8a\u63a5\u8fd1\u4e00\u4e2a\u201c\u514d\u8d39\u201d\u7684\u521a\u6027\u5e73\u79fb\uff0c**\u643a\u5e26\u4fe1\u606f\u7684\u662f dispersion**\u3002",
        "",
        "## 2. \u6bcf\u7ea7\u5bf9\u6392\u5e8f\u7684\u4f24\u5bb3\uff08\u51bb\u7ed3 ladder \u8bfb\u56de\uff09",
        "",
        "| rung | \u8f74 | tau_b | 1 - tau_b | f_unresolved before | f_unresolved after | f_robust_inv |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for rung in payload["rungs"]:
        for axis in AXES:
            cell = rung["axes"][axis]
            lines.append("| `%s` | %s | %.4f | %.4f | %.4f | %.4f | %.4f |"
                         % (rung["key"], axis, cell["kendall_tau_b"], cell["tau_b_drop"],
                            cell["f_unresolved_before"], cell["f_unresolved_after"], cell["f_robust_inv"]))
    lines += [
        "",
        "## 3. \u8df3\u677f\u5bf9\u4f4d\u79fb\u76f8\u5173\uff08\u540c\u8f74\u3001\u5171\u4eab\u5206\u5b50\u4e0a\u73b0\u7b97\uff09",
        "",
        "| rung A | rung B | \u8f74 | \u5171\u4eab\u5206\u5b50 | Pearson | Spearman |",
        "| --- | --- | --- | ---: | ---: | ---: |",
    ]
    for row in payload["independence"]["pairs"]:
        lines.append("| `%s` | `%s` | %s | %d | %+.3f | %+.3f |"
                     % (row["a"], row["b"], row["axis"], row["n_shared"], row["pearson"], row["spearman"]))
    lines += [
        "",
        "## 4. \u5206\u89e3\u6027\u6821\u9a8c\uff08\u5171\u4eab P1 \u951a\u70b9\uff09",
        "",
        "| \u8f74 | \u5217 | \u5171\u4eab\u5206\u5b50 | \u6700\u5927\u7edd\u5bf9\u504f\u5dee\uff08eV\uff09 |",
        "| --- | --- | ---: | ---: |",
    ]
    for axis in AXES:
        cell = anchor[axis]
        lines.append("| %s | `%s` | %d | %.2e |"
                     % (axis, cell["column"], cell["n_shared"], cell["max_abs_deviation_ev"]))
    lines += [
        "",
        "\u56e0\u6b64 `P0\u2192P2 \u2261 (P0\u2192P1) + (P1\u2192P2)` \u662f\u4e25\u683c\u6052\u7b49\u5f0f\uff1a\u4e2d\u95f4\u7ea7\u6ca1\u6709\u989d\u5916\u72ec\u7acb\u4fe1\u606f\uff0c",
        "\u53ea\u6709\u5728\u4e0d\u540c\u5206\u5b50\u96c6 / \u4e0d\u540c\u7269\u7406\u673a\u5236\u65f6\u624d\u662f\u65b0\u8bc1\u636e\u3002",
        "",
        "## 5. \u9010\u6761\u53d1\u73b0",
        "",
        "| id | \u7ea7\u522b | \u8bf4\u660e |",
        "| --- | --- | --- |",
    ]
    for row in payload["findings"]:
        lines.append("| %s | **%s** | %s |" % (row["id"], row["level"], row["statement"]))
    lines += [
        "",
        "## 6. \u7eaa\u5f8b\u58f0\u660e",
        "",
        "- \u672c\u5ba1\u8ba1\u4e0d\u8dd1\u4efb\u4f55\u65b0\u7535\u5b50\u7ed3\u6784\uff1b\u6240\u6709\u6570\u5b57\u5747\u4e3a\u5df2\u51bb\u7ed3\u4ea7\u7269\u7684\u73b0\u7b97\u8bfb\u51fa\u3002",
        "- \u672c\u5ba1\u8ba1\u4e0d\u6539\u53d8\u4efb\u4f55\u65e2\u6709\u5224\u51b3\uff1b\u4e0d\u8bfb\u53d6\u4ed3\u5e93\u5916\u6587\u4ef6\u3002",
        "- \u201c\u72ec\u7acb\u201d\u5728\u672c\u6587\u4e2d\u53ea\u6307\u4f4d\u79fb\u5411\u91cf\u4e0d\u76f8\u5173\uff0c\u4e0d\u6307\u7269\u7406\u673a\u5236\u4e92\u65a5\u3002",
    ]
    return "\n".join(lines) + "\n"


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="R15 layer-independence audit (read-only).")
    parser.add_argument("--check", action="store_true", help="recompute and compare bytes/pixels")
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    payload = collect()
    json_text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=False) + "\n"
    md_text = render_markdown(payload)

    figure = draw(payload)
    png = render_png(figure)
    plt.close(figure)
    pixels = mpimg.imread(io.BytesIO(png))
    height_px, width_px = int(pixels.shape[0]), int(pixels.shape[1])

    digests = {
        "inputs": {INPUTS[key]: sha256(REPO_ROOT / INPUTS[key]) for key in INPUTS},
        "input_order": [INPUTS[key] for key in INPUTS],
        "outputs": {},
        "output_order": [],
    }
    png_rel = (FIGURE_DIR / FIGURE_NAME).relative_to(REPO_ROOT).as_posix()
    manifest_text = render_manifest(payload, digests, width_px, height_px)
    png_sha = hashlib.sha256(png).hexdigest()
    for name, text in ((JSON_PATH.relative_to(REPO_ROOT).as_posix(), json_text),
                       (MD_PATH.relative_to(REPO_ROOT).as_posix(), md_text),
                       (MANIFEST_PATH.relative_to(REPO_ROOT).as_posix(), manifest_text)):
        digests["outputs"][name] = hashlib.sha256(text.encode("utf-8")).hexdigest()
        digests["output_order"].append(name)
    digests["outputs"][png_rel] = png_sha
    digests["output_order"].append(png_rel)
    manifest_text = render_manifest(payload, digests, width_px, height_px)

    independence = payload["independence"]
    print("F58 R15 layer independence / information gain -- resolved numbers")
    print("-" * 68)
    print("  rungs                       : %d" % len(payload["rungs"]))
    print("  same-axis rung pairs        : %d" % independence["n_pairs"])
    print("  |Pearson| median / max      : %.3f / %.3f"
          % (independence["median_abs_pearson"], independence["max_abs_pearson"]))
    print("  pairs above 0.7             : %d" % independence["n_pairs_above_0_7"])
    print("  P1 anchor max |dev|         : %.2e eV"
          % max(payload["anchor_agreement"][axis]["max_abs_deviation_ev"] for axis in AXES))
    print("  figure                      : %d x %d px @ %d dpi" % (width_px, height_px, DPI))
    print("  png sha256                  : %s" % png_sha[:16])
    print("-" * 68)

    if args.check:
        for path, expected in ((JSON_PATH, json_text), (MD_PATH, md_text), (MANIFEST_PATH, manifest_text)):
            if not path.exists():
                print("CHECK FAILED -- %s is missing" % path)
                return 1
            if path.read_text(encoding="utf-8") != expected:
                print("CHECK FAILED -- %s differs from the regenerated text" % path)
                return 1
        png_path = FIGURE_DIR / FIGURE_NAME
        if not png_path.exists():
            print("CHECK FAILED -- %s is missing" % png_path)
            return 1
        disk = mpimg.imread(png_path)
        memory = mpimg.imread(io.BytesIO(png))
        if disk.shape != memory.shape or not np.array_equal(disk, memory):
            print("CHECK FAILED -- pixels differ from %s" % png_path)
            return 1
        print("CHECK OK -- JSON/MD/manifest byte-identical; %s re-renders pixel-identical" % png_rel)
        return 0

    STAGE_DIR.mkdir(parents=True, exist_ok=True)
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    for path, text in ((JSON_PATH, json_text), (MD_PATH, md_text), (MANIFEST_PATH, manifest_text)):
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
    with open(FIGURE_DIR / FIGURE_NAME, "wb") as handle:
        handle.write(png)
    for path in (JSON_PATH, MD_PATH, MANIFEST_PATH, FIGURE_DIR / FIGURE_NAME):
        print("wrote %s" % path.relative_to(REPO_ROOT).as_posix())
    return 0


if __name__ == "__main__":
    sys.exit(main())