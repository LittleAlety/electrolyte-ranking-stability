"""Three-state pairwise decision report + resolution curve (R13).

Why this module exists
----------------------
The repository has always reported ``f_unresolved`` *and* ``f_robust_inv``, but a
reader can still collapse them into "no robust inversions, so the ranking is
fine".  R13 (``config/scientific_definitions.yaml`` ``decision_state``) replaces
that two-number summary with an explicit per-pair state -- STABLE / UNRESOLVED /
ROBUST_INVERSION -- and with ``f_unresolved(z)`` across the frozen evidence bands
(z = 1.0 / 1.645 / 1.96 / 2.576), so the report states how much of the ranking is
*resolvable at each confidence* instead of defending a single ``z``.

No new electronic structure: every replay reads the frozen Week-4 decision-stability
pair tables (``d_p0_ev`` / ``d_p1_ev`` / ``sigma_ev``) and re-labels them.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from electrolyte_ranking.decision_state import (  # noqa: E402
    DECISION_LABELS,
    decision_state_fractions,
    decision_state_matrix,
    resolution_curve,
)
from electrolyte_ranking.ranking import resolved_mask  # noqa: E402

DEFAULT_OUTDIR = REPO_ROOT / "outputs" / "decision_state"

#: (label, source json, dotted path template with {axis}) of every frozen rung.
RUNGS = (
    ("P0->P1v", "outputs/week4/p1_decision_stability.json", "{axis}"),
    ("P1v->P2a", "outputs/week4/p2_decision_stability.json", "p1_to_p2.{axis}"),
    ("P0->P2a", "outputs/week4/p2_decision_stability.json", "p0_to_p2.{axis}"),
)
AXES = ("oxidation", "reduction")


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Re-label frozen decision tables into R13 states.")
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    parser.add_argument("--z-primary", type=float, default=1.0)
    return parser.parse_args(argv)


def dig(obj, path):
    current = obj
    for key in path.split("."):
        current = current[key]
    return current


def matrices_from_pairs(pairs):
    """(diff0, diff1, sigma, names) symmetric matrices from a frozen pair list."""

    names = sorted({pair["i"] for pair in pairs} | {pair["j"] for pair in pairs})
    index = {name: position for position, name in enumerate(names)}
    n = len(names)
    diff0 = np.zeros((n, n))
    diff1 = np.zeros((n, n))
    sigma = np.zeros((n, n))
    for pair in pairs:
        i, j = index[pair["i"]], index[pair["j"]]
        diff0[i, j], diff0[j, i] = pair["d_p0_ev"], -pair["d_p0_ev"]
        diff1[i, j], diff1[j, i] = pair["d_p1_ev"], -pair["d_p1_ev"]
        sigma[i, j] = sigma[j, i] = pair["sigma_ev"]
    return diff0, diff1, sigma, names


def analyse_block(block, z_primary):
    pairs = block.get("pair_differences")
    if not pairs:
        return None
    diff0, diff1, sigma, names = matrices_from_pairs(pairs)
    mask0 = resolved_mask(diff0, sigma, z=z_primary)
    mask1 = resolved_mask(diff1, sigma, z=z_primary)
    matrix = decision_state_matrix(diff0, diff1, mask0, mask1)
    fractions = decision_state_fractions(matrix)
    counts = {}
    iu = np.triu_indices(len(names), 1)
    for i, j in zip(iu[0], iu[1]):
        label = str(matrix[i, j])
        counts[label] = counts.get(label, 0) + 1
    ordered_counts = {label: counts.get(label, 0) for label in DECISION_LABELS}
    return {
        "n": block.get("n"),
        "n_pairs": len(pairs),
        "kendall_tau_b": block.get("kendall_tau_b"),
        "f_robust_inv_frozen": block.get("f_robust_inv"),
        "f_unresolved_p0_frozen": block.get("f_unresolved_p0"),
        "f_unresolved_p1_frozen": block.get("f_unresolved_p1"),
        "sigma_median_ev": block.get("sigma_median_ev"),
        "decision_state_counts": ordered_counts,
        "decision_state_fractions": {label: fractions.get(label, 0.0) for label in DECISION_LABELS},
        "resolution_curve_p0": resolution_curve(diff0, sigma),
        "resolution_curve_p1": resolution_curve(diff1, sigma),
        "members": names,
    }


def main(argv=None) -> int:
    args = parse_args(argv)
    outdir = args.outdir
    outdir.mkdir(parents=True, exist_ok=True)

    cache: dict = {}
    payload = {
        "stage": "R13 decision-state report",
        "definition": (
            "Each frozen pair (d_p0_ev / d_p1_ev / sigma_ev) is re-labelled at z = %s into "
            "STABLE / UNRESOLVED / ROBUST_INVERSION, with f_unresolved(z) reported across the "
            "frozen evidence bands." % args.z_primary
        ),
        "z_primary": args.z_primary,
        "rungs": {},
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    rows = []
    for label, source, template in RUNGS:
        document = cache.get(source)
        if document is None:
            document = json.loads((REPO_ROOT / source).read_text(encoding="utf-8"))
            cache[source] = document
        payload["rungs"][label] = {}
        for axis in AXES:
            block = dig(document, template.format(axis=axis))
            analysis = analyse_block(block, args.z_primary)
            payload["rungs"][label][axis] = analysis
            if analysis is None:
                continue
            rows.append(
                [
                    label,
                    axis,
                    analysis["n"],
                    analysis["n_pairs"],
                    analysis["decision_state_counts"]["STABLE"],
                    analysis["decision_state_counts"]["UNRESOLVED"],
                    analysis["decision_state_counts"]["ROBUST_INVERSION"],
                    analysis["decision_state_fractions"]["UNRESOLVED"],
                    analysis["decision_state_fractions"]["ROBUST_INVERSION"],
                ]
            )

    (outdir / "decision_state_report.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n"
    )
    with (outdir / "decision_state_report.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "rung",
                "axis",
                "n",
                "n_pairs",
                "n_STABLE",
                "n_UNRESOLVED",
                "n_ROBUST_INVERSION",
                "f_UNRESOLVED",
                "f_ROBUST_INVERSION",
            ]
        )
        writer.writerows(rows)
    _write_report(outdir / "decision_state_summary.md", payload)
    print("decision-state report: %d rung-axis rows" % len(rows))
    return 0


def _write_report(path: Path, payload) -> None:
    lines = [
        "# Pairwise decision state + resolution curve（R13）",
        "",
        "> 由 `scripts/decision_state_report.py` 从冻结的 Week-4 判据表现算；不跑新电子结构。",
        "> 判据口径：`|dP| >= z·sigma` 才算 resolve；`f_robust_inv = 0` 只有在 UNRESOLVED 很小时才意味着稳定。",
        "",
        "## 三态计数（z = %s）" % payload["z_primary"],
        "",
        "| rung | axis | n | n_pairs | STABLE | UNRESOLVED | ROBUST_INVERSION | f_UNRESOLVED | f_ROBUST_INV |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for label, axes in payload["rungs"].items():
        for axis, analysis in axes.items():
            if analysis is None:
                lines.append("| %s | %s | - | - | - | - | - | - | - |" % (label, axis))
                continue
            counts = analysis["decision_state_counts"]
            fractions = analysis["decision_state_fractions"]
            lines.append(
                "| %s | %s | %s | %d | %d | %d | %d | %.3f | %.3f |"
                % (
                    label,
                    axis,
                    analysis["n"],
                    analysis["n_pairs"],
                    counts["STABLE"],
                    counts["UNRESOLVED"],
                    counts["ROBUST_INVERSION"],
                    fractions["UNRESOLVED"],
                    fractions["ROBUST_INVERSION"],
                )
            )

    lines += [
        "",
        "## 分辨率曲线 f_unresolved(z)",
        "",
        "| rung | axis | model | z = 1.0 | z = 1.645 | z = 1.96 | z = 2.576 |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for label, axes in payload["rungs"].items():
        for axis, analysis in axes.items():
            if analysis is None:
                continue
            for model, key in (("P_cheap", "resolution_curve_p0"), ("P_target", "resolution_curve_p1")):
                rows = {row["z"]: row["f_unresolved"] for row in analysis[key]["rows"]}
                cells = " | ".join("%.3f" % rows[z] for z in (1.0, 1.645, 1.96, 2.576))
                lines.append("| %s | %s | %s | %s |" % (label, axis, model, cells))

    lines += [
        "",
        "> 读法：曲线告诉你「在 1σ / 90% / 95% / 99% 证据门槛下，多少 pair 根本无法解析」。",
        "> f_robust_inv = 0 且 f_unresolved 高，其含义是 `evidence insufficient to resolve the ranking`，而不是 ranking stable。",
        "",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    raise SystemExit(main())
