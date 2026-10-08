"""P1v vs P1a: does geometry relaxation change the screening decision?

Why this module exists
----------------------
R13 splits the gas-phase redox layer into ``P1v`` (vertical, three single points
on the shared G1 -- the Week-4 layer) and ``P1a`` (adiabatic, each charged state
relaxed -- ``outputs/phase2_p1a``).  The question this stage answers is the one
the external review named first:

    *is geometry relaxation itself a missing physics that changes the decision?*

The comparison is only defined where both layers exist.  Gas-phase adiabatic
**electron affinities** are excluded by the frozen ``unbound_anion`` rule (the
Week-4 audit flags all 18 core-set anions), so this report closes the **oxidation
axis** and records the reduction axis as excluded-by-rule rather than inventing a
number.

Uncertainty convention: this rung's per-candidate sigma is the population spread
of the relaxation displacement ``d = IP_a - IP_v`` over the subset.  That is the
quantity the rung is *about* (the geometry-induced, candidate-specific shift), so
using it as the evidence scale keeps the decision-state classification honest
rather than borrowing an unrelated method sigma.
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

import numpy as np  # noqa: E402

from electrolyte_ranking.decision_state import (  # noqa: E402
    DECISION_LABELS,
    decision_state_fractions,
    decision_state_matrix,
    resolution_curve,
)
from electrolyte_ranking.ranking import (  # noqa: E402
    kendall_tau_b,
    pair_differences,
    resolved_mask,
    spearman_rho,
    top_k_overlap,
)

P1A_CSV = REPO_ROOT / "outputs" / "phase2_p1a" / "p1a_adiabatic.csv"
DEFAULT_OUTDIR = REPO_ROOT / "outputs" / "phase2_p1a"
DEFAULT_DOC = REPO_ROOT / "docs" / "p1v_vs_p1a.md"


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Compare P1v (vertical) with P1a (adiabatic).")
    parser.add_argument("--csv", type=Path, default=P1A_CSV)
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    parser.add_argument("--doc", type=Path, default=DEFAULT_DOC)
    return parser.parse_args(argv)


def load_rows(path: Path) -> list:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def oxidation_pairs(rows):
    """(names, IP_v, IP_a, d) for rows where both layers are defined."""

    names, ipv, ipa = [], [], []
    for row in rows:
        v, a = _float(row["ip_p1v_ev"]), _float(row["ip_p1a_ev"])
        if v is None or a is None:
            continue
        names.append(row["name"])
        ipv.append(v)
        ipa.append(a)
    return names, ipv, ipa, [a - v for a, v in zip(ipa, ipv)]


def build_report(rows) -> dict:
    names, ipv, ipa, d = oxidation_pairs(rows)
    report = {
        "stage": "P1v vs P1a (oxidation axis)",
        "definition": (
            "P1v = gas-phase vertical redox-energy proxy (three single points on G1); "
            "P1a = gas-phase adiabatic redox thermodynamics (each charged state relaxed)."
        ),
        "axis": "oxidation",
        "n": len(names),
        "members": names,
        "per_molecule": [
            {"name": name, "ip_p1v_ev": v, "ip_p1a_ev": a, "d_ip_ev": delta}
            for name, v, a, delta in zip(names, ipv, ipa, d)
        ],
        "displacement": {
            "mean_ev": None if not d else statistics.fmean(d),
            "population_std_ev": None if len(d) < 2 else statistics.pstdev(d),
            "min_ev": None if not d else min(d),
            "max_ev": None if not d else max(d),
        },
        "reduction_axis": {
            "defined": False,
            "reason": (
                "gas-phase adiabatic EA is excluded by the frozen unbound_anion rule "
                "(outputs/week4/p1_core_set_audit.json flags all 18 core-set anions); "
                "only the oxidation axis supports a P1v -> P1a comparison"
            ),
        },
    }
    if len(names) < 2:
        report["ranking"] = {"defined": False, "note": "fewer than two molecules with both layers"}
        return report

    sigma = statistics.pstdev(d) if len(d) >= 2 else 0.0
    report["ranking"] = {
        "defined": True,
        "kendall_tau_b": kendall_tau_b(ipv, ipa),
        "spearman_rho": spearman_rho(ipv, ipa),
        "top_k_overlap": {
            "k=0.10": top_k_overlap(ipv, ipa, 0.10),
            "k=0.20": top_k_overlap(ipv, ipa, 0.20),
            "k=0.30": top_k_overlap(ipv, ipa, 0.30),
        },
        "sigma_convention": (
            "population std of the relaxation displacement d = IP_a - IP_v over the subset, "
            "applied to both models"
        ),
        "sigma_ev": sigma,
    }
    diff_v = pair_differences(ipv)
    diff_a = pair_differences(ipa)
    sigma_matrix = np.full(diff_v.shape, sigma)
    mask_v = resolved_mask(diff_v, sigma_matrix, z=1.0)
    mask_a = resolved_mask(diff_a, sigma_matrix, z=1.0)
    matrix = decision_state_matrix(diff_v, diff_a, mask_v, mask_a)
    report["decision_state_counts"] = _counts(matrix)
    report["decision_state_fractions"] = decision_state_fractions(matrix)
    report["resolution_curve"] = {
        "p1v": resolution_curve(diff_v, sigma_matrix),
        "p1a": resolution_curve(diff_a, sigma_matrix),
    }
    return report


def _counts(matrix) -> dict:
    import numpy as np

    counts = {label: 0 for label in DECISION_LABELS}
    n = matrix.shape[0]
    for i in range(n):
        for j in range(i + 1, n):
            counts[str(matrix[i, j])] = counts.get(str(matrix[i, j]), 0) + 1
    return counts


def write_doc(path: Path, report: dict) -> None:
    lines = [
        "# P1v vs P1a —— geometry relaxation 是不是一种会改变决策的缺失物理？（R13）",
        "",
        "> 由 `scripts/compare_vertical_adiabatic.py` 从 `outputs/phase2_p1a/p1a_adiabatic.csv` 现算。",
        "",
        "## 定义",
        "",
        "- **P1v**：气相 vertical redox-energy proxy（中性/阳离子/阴离子共用几何 G1，只做单点）→ Week-4 层。",
        "- **P1a**：气相 adiabatic redox thermodynamics（每个电荷态各自 r2SCAN-3c Opt 到自身极小）→ 本层。",
        "",
        "## 氧化轴结果",
        "",
        "| 量 | 值 |",
        "| --- | --- |",
        "| n | %d |" % report["n"],
    ]
    if report.get("ranking", {}).get("defined"):
        ranking = report["ranking"]
        lines += [
            "| Kendall τ_b(P1v, P1a) | %.3f |" % ranking["kendall_tau_b"],
            "| Spearman ρ | %.3f |" % ranking["spearman_rho"],
            "| Top-10%% / 20%% / 30%% overlap | %.2f / %.2f / %.2f |"
            % (
                ranking["top_k_overlap"]["k=0.10"],
                ranking["top_k_overlap"]["k=0.20"],
                ranking["top_k_overlap"]["k=0.30"],
            ),
            "| 位移 d = IP_a − IP_v：mean / std / min / max | %.3f / %.3f / %.3f / %.3f eV |"
            % (
                report["displacement"]["mean_ev"],
                report["displacement"]["population_std_ev"],
                report["displacement"]["min_ev"],
                report["displacement"]["max_ev"],
            ),
        ]
        lines += [
            "",
            "三态计数（sigma = 位移 population std = %.3f eV）：" % ranking["sigma_ev"],
            "",
            "| 状态 | n | 占比 |",
            "| --- | --- | --- |",
        ]
        for label in DECISION_LABELS:
            lines.append(
                "| %s | %d | %.3f |"
                % (
                    label,
                    report["decision_state_counts"].get(label, 0),
                    report["decision_state_fractions"].get(label, 0.0),
                )
            )
    else:
        lines.append("| 排序 | 不足两个分子同时具备两层，未定义 |")

    lines += [
        "",
        "## 还原轴：按规则排除，而不是补一个数",
        "",
        "%s。" % report["reduction_axis"]["reason"],
        "这不是 runner 的缺陷，而是 P1a 这一层存在的理由：**气相阴离子不束缚，绝热 EA 在气相无物理意义**。",
        "还原轴若要 adiabatic 处理，只能放到有溶剂/配位环境（P2a / C1）里做。",
        "",
        "## 逐分子",
        "",
        "| name | IP_v (eV) | IP_a (eV) | d (eV) |",
        "| --- | --- | --- | --- |",
    ]
    for row in report["per_molecule"]:
        lines.append(
            "| %s | %.4f | %.4f | %+.4f |"
            % (row["name"], row["ip_p1v_ev"], row["ip_p1a_ev"], row["d_ip_ev"])
        )
    lines.append("")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def main(argv=None) -> int:
    args = parse_args(argv)
    rows = load_rows(args.csv)
    report = build_report(rows)
    (args.outdir / "p1v_vs_p1a.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n"
    )
    write_doc(args.doc, report)
    print("P1v vs P1a: n=%d, ranking defined=%s" % (report["n"], report.get("ranking", {}).get("defined")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
