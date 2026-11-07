"""Stage 6 / T9 -- uncertainty-aware ranking analysis (the prereg statistical plan).

Why this module exists
----------------------
Stages 2-5 produced four single-variable comparisons (P0->P1 method, P1->P2
environment, C0->C1 coordination) and each was reported with the *temporary*
rule ``|dP| >= z * sigma_ij`` (z = 1.0 from the prereg, sigma_ij from the two
realisations themselves). Stage 6 adds the piece the prereg always asked for
and which the repository never had: the fixed pair tolerance ``delta_m``.

The prereg (``config/prereg.yaml`` -> ``pair_comparison.delta_m``) defines
delta_m as a *fixed* tolerance that is independent of the method uncertainty:

    unresolved  <=>  |dP_ij| < delta_m  OR  |dP_ij| < z * sigma_ij

and the execution plan (docx section 6.2) fixes how delta_m is built
(``max(conformer spread, inter-method spread, 0.05 eV)``). This module takes the
candidate delta_m from ``outputs/week6/delta_m_frozen.json`` and re-runs every
Stage 2-5 comparison under

    z_only      delta_m = 0            (the Week 5 temporary rule)
    floor_only  delta_m = 0.05 eV      (plan docx numerical floor)
    docx_max    delta_m = T8 candidate (primary; the plan docx max rule)

so the *effect* of the tolerance is visible instead of assumed.

Metrics (all preregistered, section 6.1)
----------------------------------------
* f_unresolved = N_unresolved / C(N, 2), per side;
* f_robust_inv = N_robust_inversions / N_pairs_resolved_in_both;
* Kendall tau_b with a 20-seed bootstrap interval, Spearman rho as auxiliary;
* Top-k overlap O_k and Jaccard J_k, k/N = 10/20/30 %, plus selection regret;
* probabilistic pair ordering p_ij with the 0.9 / 0.1 band;
* family-resolved and cross-family unresolved fractions.

threshold_decision_error is reported as ``not_applicable``: the prereg
(``threshold_decisions.if_unavailable``) forbids substituting a data quantile
for a missing external design threshold, and no compliant external threshold is
registered for this objective set.

Outputs
-------
outputs/week6/stage6_decision_stability.csv/.json/.md
outputs/figures/F14_delta_m_derivation.png, F15_stage6_decision_metrics.png
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import math
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from electrolyte_ranking import ranking, uncertainty  # noqa: E402

HARTREE_TO_EV = 27.211386245988
Z_PRIMARY = 1.0        # config/prereg.yaml: pair_comparison.z_factor.value (frozen)
Z_SENSITIVITY = 1.96   # conservative 95% two-sided band, reported alongside
TOP_K_FRACTIONS = (0.10, 0.20, 0.30)
PROB_HIGH, PROB_LOW = 0.90, 0.10

BOOTSTRAP_REPETITIONS = 2000
BOOTSTRAP_ALPHA = 0.05
BOOTSTRAP_SEEDS = (101, 211, 307, 401, 503, 601, 701, 809, 907, 1009,
                   1103, 1201, 1301, 1409, 1511, 1601, 1709, 1801, 1901, 2003)

AUDIT_SUBSET = (
    "EC", "PC", "DMC", "EMC", "DME", "DOL",
    "GBL", "AN", "SN", "DMSO", "SL", "TMP",
)

#: Layer pairs compared. Each entry is (label, lower layer, upper layer).
PAIRS = (
    ("P0_to_P1", "P0", "P1"),
    ("P1_to_P2", "P1", "P2"),
    ("C0_to_C1", "C0", "C1"),
)

SCENARIOS = ("z_only", "floor_only", "docx_max")


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="T9: Stage 6 uncertainty-aware decision-stability analysis."
    )
    parser.add_argument("--derived", type=Path, default=REPO_ROOT / "outputs/week4/p1_core_set_derived.csv")
    parser.add_argument("--p2", type=Path, default=REPO_ROOT / "outputs/week4/p2_core_set_cpcm_10.csv")
    parser.add_argument("--c1", type=Path, default=REPO_ROOT / "outputs/week5/c1_coord_shifts.csv")
    parser.add_argument("--delta-m", type=Path, default=REPO_ROOT / "outputs/week6/delta_m_frozen.json")
    parser.add_argument("--outdir", type=Path, default=REPO_ROOT / "outputs/week6")
    parser.add_argument("--subset", default=",".join(AUDIT_SUBSET))
    return parser.parse_args(argv)


def load_derived(path: Path) -> dict:
    """name -> family + P0/P1 values on the maximise convention (ox = IP, red = -EA)."""

    table = {}
    with io.open(path, encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row.get("status") != "ok":
                continue
            def number(column):
                raw = (row.get(column) or "").strip()
                return None if raw == "" else float(raw)
            table[row["name"]] = {
                "family": row.get("family", ""),
                "P0": {"ox": number("p0_ox_ev"), "red": number("p0_red_ev")},
                "P1": {"ox": number("p1_ox_ev"), "red": number("p1_red_ev")},
            }
    return table


def load_p2(path: Path) -> dict:
    """P2 (r2SCAN-3c + CPCM) long table -> {name: {'ox': IP, 'red': -EA}}."""

    energies: dict = {}
    with io.open(path, encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row.get("status") != "ok":
                continue
            raw = (row.get("final_energy_eh") or "").strip()
            if raw == "":
                continue
            energies.setdefault(row["name"], {})[row["state"]] = float(raw)
    table = {}
    for name, states in energies.items():
        if not {"neutral", "cation", "anion"} <= set(states):
            continue
        ip = (states["cation"] - states["neutral"]) * HARTREE_TO_EV
        ea = (states["neutral"] - states["anion"]) * HARTREE_TO_EV
        table[name] = {"ox": ip, "red": -ea}
    return table


def load_c1(path: Path) -> dict:
    """C0/C1 values for the primary motif (ox = IP, red = -EA)."""

    table = {}
    with io.open(path, encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if (row.get("is_primary") or "").strip().lower() not in ("true", "1", "yes"):
                continue
            def number(column):
                raw = (row.get(column) or "").strip()
                return None if raw == "" else float(raw)
            table[row["name"]] = {
                "family": row.get("family", ""),
                "C0": {"ox": number("ip_c0_g2_ev"), "red": (lambda v: None if v is None else -v)(number("ea_c0_g2_ev"))},
                "C1": {"ox": number("ip_c1_ev"), "red": (lambda v: None if v is None else -v)(number("ea_c1_ev"))},
            }
    return table
# ---------------------------------------------------------------------------
# metrics
# ---------------------------------------------------------------------------
def tau_b_interval(a, b):
    """Prereg-compliant bootstrap interval for Kendall tau_b (20 seeds x 2000)."""

    if len(a) < 3:
        return None
    lows, highs = [], []
    for seed in BOOTSTRAP_SEEDS:
        low, high = uncertainty.bootstrap_tau_b_ci(
            a, b, BOOTSTRAP_REPETITIONS, seed, BOOTSTRAP_ALPHA
        )
        lows.append(low)
        highs.append(high)
    return [statistics.median(lows), statistics.median(highs)]


def normal_cdf(z: float) -> float:
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def probabilistic_ordering(values_a, values_b):
    """p_ij = P(P_i > P_j) under a normal model whose sd is the two-realisation spread.

    Each molecule's value is modelled as Gaussian around the realisation mean
    with sd = |v_A - v_B| / sqrt(2) (the same two-realisation estimate the pair
    uncertainty uses). Then P_i - P_j is normal with mean v_i - v_j and
    variance sd_i^2 + sd_j^2, and p_ij follows in closed form. This is the
    "posterior / bootstrap" quantity of v2 section 9.4 without paying for a
    bootstrap that would only resample molecules, not the method.
    """

    n = len(values_a)
    p = np.zeros((n, n), dtype=float)
    sds = [abs(a - b) / math.sqrt(2.0) for a, b in zip(values_a, values_b)]
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            variance = sds[i] ** 2 + sds[j] ** 2
            if variance <= 0.0:
                p[i, j] = 1.0 if values_a[i] > values_a[j] else 0.0
            else:
                p[i, j] = normal_cdf((values_a[i] - values_a[j]) / math.sqrt(variance))
    return p


def family_split(labels, families):
    within, cross = [], []
    for i in range(len(labels)):
        for j in range(i + 1, len(labels)):
            key = (i, j)
            if families[i] and families[i] == families[j]:
                within.append(key)
            else:
                cross.append(key)
    return within, cross


def mask_fraction(mask, index_pairs) -> float:
    if not index_pairs:
        return 0.0
    total = sum(1 for i, j in index_pairs if mask[i, j])
    return total / len(index_pairs)


def compare(pair_label, labels, families, lower, upper, delta_m_ev) -> dict:
    """One layer pair, one objective, one delta_m scenario."""

    n = len(labels)
    a_values = [row[0] for row in lower]
    b_values = [row[0] for row in upper]

    sigma = uncertainty.quantify_method_sigma([a_values, b_values], ddof=1, stat="std")
    diff_a = ranking.pair_differences(a_values)
    diff_b = ranking.pair_differences(b_values)
    mask_a = ranking.resolved_mask(diff_a, sigma, z=Z_PRIMARY, tolerance=delta_m_ev)
    mask_b = ranking.resolved_mask(diff_b, sigma, z=Z_PRIMARY, tolerance=delta_m_ev)
    mask_a_z196 = ranking.resolved_mask(diff_a, sigma, z=Z_SENSITIVITY, tolerance=delta_m_ev)
    mask_b_z196 = ranking.resolved_mask(diff_b, sigma, z=Z_SENSITIVITY, tolerance=delta_m_ev)

    top_k = {}
    for fraction in TOP_K_FRACTIONS:
        k = max(1, round(fraction * n))
        top_k["k=%.2f" % fraction] = {
            "k": k,
            "overlap": ranking.top_k_overlap(a_values, b_values, k),
            "jaccard": ranking.jaccard_at_k(a_values, b_values, k),
            "selection_regret": ranking.selection_regret(b_values, a_values, k),
        }

    within, cross = family_split(labels, families)
    p = probabilistic_ordering(a_values, b_values)
    decided = undecided = 0
    for i in range(n):
        for j in range(i + 1, n):
            value = max(p[i, j], p[j, i])
            if value > PROB_HIGH:
                decided += 1
            else:
                undecided += 1
    n_pairs = n * (n - 1) // 2

    # Denominator of f_robust_inv (pairs resolved on BOTH sides) and the count of
    # pairs where delta_m is the binding constraint (z*sigma alone would resolve
    # them). Both are needed to read f_robust_inv honestly: a small f_robust_inv
    # with a collapsing denominator is not evidence of a stable screen.
    iu = np.triu_indices(n, 1)
    resolved_both = int(np.count_nonzero(mask_a[iu] & mask_b[iu]))
    mask_a_z_only = ranking.resolved_mask(diff_a, sigma, z=Z_PRIMARY, tolerance=0.0)
    mask_b_z_only = ranking.resolved_mask(diff_b, sigma, z=Z_PRIMARY, tolerance=0.0)
    delta_m_binding = int(np.count_nonzero(
        (mask_a_z_only[iu] & ~mask_a[iu]) | (mask_b_z_only[iu] & ~mask_b[iu])
    ))

    return {
        "pair": pair_label,
        "n": n,
        "n_pairs": n_pairs,
        "labels": labels,
        "higher_is_better": True,
        "delta_m_ev": delta_m_ev,
        "z_primary": Z_PRIMARY,
        "n_pairs_resolved_in_both": resolved_both,
        "n_pairs_delta_m_is_binding": delta_m_binding,
        "kendall_tau_b": ranking.kendall_tau_b(a_values, b_values),
        "kendall_tau_b_ci95": tau_b_interval(a_values, b_values),
        "spearman_rho": ranking.spearman_rho(a_values, b_values),
        "f_unresolved_lower": ranking.unresolved_pair_fraction(mask_a),
        "f_unresolved_upper": ranking.unresolved_pair_fraction(mask_b),
        "f_robust_inv": ranking.robust_inversion_fraction(diff_a, diff_b, mask_a, mask_b),
        "f_unresolved_lower_z1p96": ranking.unresolved_pair_fraction(mask_a_z196),
        "f_unresolved_upper_z1p96": ranking.unresolved_pair_fraction(mask_b_z196),
        "f_robust_inv_z1p96": ranking.robust_inversion_fraction(diff_a, diff_b, mask_a_z196, mask_b_z196),
        "sigma_median_ev": float(statistics.median([abs(sigma[i, j]) for i in range(n) for j in range(n) if i != j])),
        "family_within_f_unresolved_lower": mask_fraction(~mask_a, within),
        "family_within_f_unresolved_upper": mask_fraction(~mask_b, within),
        "family_cross_f_unresolved_lower": mask_fraction(~mask_a, cross),
        "family_cross_f_unresolved_upper": mask_fraction(~mask_b, cross),
        "n_pairs_within_family": len(within),
        "n_pairs_cross_family": len(cross),
        "prob_decided_fraction": decided / n_pairs if n_pairs else None,
        "prob_undecided_fraction": undecided / n_pairs if n_pairs else None,
        "threshold_decision_error": None,
        "threshold_decision_error_note": "not_applicable: config/prereg.yaml "
        "threshold_decisions.if_unavailable forbids substituting a data quantile for a "
        "missing external design threshold, and no compliant external threshold is registered",
        "top_k": top_k,
        "pair_differences": [
            {
                "i": labels[i],
                "j": labels[j],
                "d_lower_ev": float(diff_a[i, j]),
                "d_upper_ev": float(diff_b[i, j]),
                "sigma_ev": float(sigma[i, j]),
                "resolved_lower": bool(mask_a[i, j]),
                "resolved_upper": bool(mask_b[i, j]),
            }
            for i in range(n)
            for j in range(i + 1, n)
        ],
    }
# ---------------------------------------------------------------------------
# assembly
# ---------------------------------------------------------------------------
def gather(pair_label, lower_layer, upper_layer, tables, subset) -> tuple:
    """Return (labels, families, lower values, upper values) for one layer pair."""

    labels, families, lower, upper = [], [], [], []
    for name in subset:
        row = tables.get(name)
        if row is None:
            continue
        if lower_layer not in row or upper_layer not in row:
            continue
        for objective in ("ox", "red"):
            if row[lower_layer][objective] is None or row[upper_layer][objective] is None:
                break
        else:
            labels.append(name)
            families.append(row.get("family", ""))
            lower.append(row[lower_layer])
            upper.append(row[upper_layer])
    return labels, families, lower, upper


def delta_m_for(layer, objective, scenario, candidates) -> tuple:
    """Return (value_ev, source_note) for one scenario."""

    if scenario == "z_only":
        return 0.0, "no fixed tolerance (Week 5 temporary rule)"
    if scenario == "floor_only":
        return 0.05, "plan docx numerical floor"
    block = candidates.get(layer, {}).get(objective)
    if block is not None:
        return block["delta_m_ev"], "T8 candidate (plan docx max rule) for layer %s" % layer.upper()
    proxy = candidates.get("p0", {}).get(objective)
    if proxy is None:
        return 0.05, "T8 candidate unavailable; fell back to the numerical floor"
    return (
        proxy["delta_m_ev"],
        "T8 candidate derived on the P0/P1 evidence; layer-specific evidence for "
        "%s is not available in this round" % layer.upper(),
    )


def write_markdown(path: Path, payload: dict) -> None:
    lines = []
    lines.append("# Stage 6：不确定性感知排序分析（T9）")
    lines.append("")
    lines.append("## 1. 本轮解决的问题")
    lines.append("")
    lines.append(
        "Week 5 及之前所有对比用的是**临时口径** `|dP_ij| >= z*sigma_ij`（z=1.0），"
        "预注册里一直有一个固定兜底容差 `delta_m` 却从未启用。本轮把 `delta_m` 装上，"
        "并给出它在 3 个口径下的效果差："
    )
    lines.append("")
    lines.append("| 口径 | delta_m | 含义 |")
    lines.append("|---|---|---|")
    for scenario in SCENARIOS:
        lines.append(
            "| `%s` | %s | %s |"
            % (scenario, payload["scenario_definition"][scenario]["delta_m_text"],
               payload["scenario_definition"][scenario]["note"])
        )
    lines.append("")
    lines.append("判据（全部来自 `config/prereg.yaml`）："
                 "`unresolved <=> |dP_ij| < delta_m 或 |dP_ij| < z*sigma_ij`；"
                 "`f_robust_inv = N_robust / N_pairs_resolved_in_both`；"
                 "`f_unresolved = N_unresolved / C(N,2)`。")
    lines.append("")
    lines.append("## 2. 主表（docx_max 口径）")
    lines.append("")
    lines.append("| 层对 | 目标 | n | tau_b [CI95] | rho | f_unresolved(下/上) | 双方均解析 pair 数 | delta_m 起决定作用的 pair 数 | f_robust_inv | O_20% | R_20% |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|")
    for key, block in payload["results"]["docx_max"].items():
        for objective in ("oxidation", "reduction"):
            item = block[objective]
            ci = item["kendall_tau_b_ci95"]
            ci_text = "-" if ci is None else "[%.2f, %.2f]" % (ci[0], ci[1])
            lines.append(
                "| %s | %s | %d | %.3f %s | %.3f | %.3f / %.3f | %d / %d | %d | %.3f | %.3f | %.4f |"
                % (
                    key, objective, item["n"], item["kendall_tau_b"], ci_text, item["spearman_rho"],
                    item["f_unresolved_lower"], item["f_unresolved_upper"],
                    item["n_pairs_resolved_in_both"], item["n_pairs"],
                    item["n_pairs_delta_m_is_binding"], item["f_robust_inv"],
                    item["top_k"]["k=0.20"]["overlap"], item["top_k"]["k=0.20"]["selection_regret"],
                )
            )
    lines.append("")
    lines.append("## 3. delta_m 的效果（3 个口径对比）")
    lines.append("")
    lines.append("| 层对 | 目标 | f_unresolved(下) z_only / floor / docx_max | f_unresolved(上) z_only / floor / docx_max | f_robust_inv z_only / floor / docx_max |")
    lines.append("|---|---|---|---|---|")
    for key in payload["results"]["docx_max"]:
        for objective in ("oxidation", "reduction"):
            cells = []
            for side in ("f_unresolved_lower", "f_unresolved_upper", "f_robust_inv"):
                triple = [
                    payload["results"][scenario][key][objective][side] for scenario in SCENARIOS
                ]
                cells.append(" / ".join("%.3f" % value for value in triple))
            lines.append("| %s | %s | %s | %s | %s |" % (key, objective, cells[0], cells[1], cells[2]))
    lines.append("")
    lines.append("## 4. 家族内 / 跨家族")
    lines.append("")
    lines.append("| 层对 | 目标 | 家族内对 | 跨家族对 | 家族内 f_unresolved(下) | 跨家族 f_unresolved(下) |")
    lines.append("|---|---|---|---|---|---|")
    for key, block in payload["results"]["docx_max"].items():
        for objective in ("oxidation", "reduction"):
            item = block[objective]
            lines.append(
                "| %s | %s | %d | %d | %.3f | %.3f |"
                % (key, objective, item["n_pairs_within_family"], item["n_pairs_cross_family"],
                   item["family_within_f_unresolved_lower"], item["family_cross_f_unresolved_lower"])
            )
    lines.append("")
    lines.append("## 5. 未报告项")
    lines.append("")
    lines.append(
        "- `threshold_decision_error`：记为 `not_applicable`。"
        "`config/prereg.yaml` 的 `threshold_decisions.if_unavailable` 禁止用数据分位数临时替代外部设计阈值，"
        "而本 objective 集合没有登记合规的外部阈值来源。"
    )
    lines.append("")
    lines.append("## 6. 一致性自检")
    lines.append("")
    for item in payload["consistency_checks"]:
        lines.append("- %s" % item)
    lines.append("")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


CSV_COLUMNS = [
    "pair", "objective", "scenario", "delta_m_ev", "n", "n_pairs",
    "kendall_tau_b", "tau_b_ci_low", "tau_b_ci_high", "spearman_rho",
    "n_pairs_resolved_in_both", "n_pairs_delta_m_is_binding",
    "f_unresolved_lower", "f_unresolved_upper", "f_robust_inv",
    "f_unresolved_lower_z1p96", "f_unresolved_upper_z1p96", "f_robust_inv_z1p96",
    "sigma_median_ev", "family_within_f_unresolved_lower", "family_cross_f_unresolved_lower",
    "n_pairs_within_family", "n_pairs_cross_family",
    "overlap_10", "overlap_20", "overlap_30",
    "jaccard_10", "jaccard_20", "jaccard_30",
    "regret_10", "regret_20", "regret_30",
    "prob_decided_fraction", "prob_undecided_fraction",
]


def write_csv(path: Path, results: dict) -> None:
    rows = []
    for scenario, pairs in results.items():
        for key, block in pairs.items():
            for objective in ("oxidation", "reduction"):
                item = block[objective]
                ci = item["kendall_tau_b_ci95"]
                row = {
                    "pair": key,
                    "objective": objective,
                    "scenario": scenario,
                    "delta_m_ev": item["delta_m_ev"],
                    "n": item["n"],
                    "n_pairs": item["n_pairs"],
                    "kendall_tau_b": item["kendall_tau_b"],
                    "tau_b_ci_low": None if ci is None else ci[0],
                    "tau_b_ci_high": None if ci is None else ci[1],
                    "spearman_rho": item["spearman_rho"],
                    "n_pairs_resolved_in_both": item["n_pairs_resolved_in_both"],
                    "n_pairs_delta_m_is_binding": item["n_pairs_delta_m_is_binding"],
                    "f_unresolved_lower": item["f_unresolved_lower"],
                    "f_unresolved_upper": item["f_unresolved_upper"],
                    "f_robust_inv": item["f_robust_inv"],
                    "f_unresolved_lower_z1p96": item["f_unresolved_lower_z1p96"],
                    "f_unresolved_upper_z1p96": item["f_unresolved_upper_z1p96"],
                    "f_robust_inv_z1p96": item["f_robust_inv_z1p96"],
                    "sigma_median_ev": item["sigma_median_ev"],
                    "family_within_f_unresolved_lower": item["family_within_f_unresolved_lower"],
                    "family_cross_f_unresolved_lower": item["family_cross_f_unresolved_lower"],
                    "n_pairs_within_family": item["n_pairs_within_family"],
                    "n_pairs_cross_family": item["n_pairs_cross_family"],
                    "prob_decided_fraction": item["prob_decided_fraction"],
                    "prob_undecided_fraction": item["prob_undecided_fraction"],
                }
                for fraction, tag in ((0.10, "10"), (0.20, "20"), (0.30, "30")):
                    block_k = item["top_k"]["k=%.2f" % fraction]
                    row["overlap_" + tag] = block_k["overlap"]
                    row["jaccard_" + tag] = block_k["jaccard"]
                    row["regret_" + tag] = block_k["selection_regret"]
                rows.append(row)
    with io.open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
def main(argv=None) -> int:
    args = parse_args(argv)
    subset = [item.strip() for item in args.subset.split(",") if item.strip()]

    derived = load_derived(args.derived)
    p2 = load_p2(args.p2)
    c1 = load_c1(args.c1)

    tables = {}
    for name, row in derived.items():
        if name not in subset:
            continue
        tables[name] = {"family": row["family"], "P0": row["P0"], "P1": row["P1"]}
    for name, values in p2.items():
        if name in tables:
            tables[name]["P2"] = values
    for name, row in c1.items():
        if name in tables:
            tables[name]["C0"] = row["C0"]
            tables[name]["C1"] = row["C1"]
            tables[name].setdefault("family", row.get("family", tables[name]["family"]))

    with io.open(args.delta_m, encoding="utf-8") as handle:
        delta_payload = json.load(handle)
    candidates = {
        layer: {objective: value for objective, value in block.items()}
        for layer, block in delta_payload["per_layer"].items()
    }

    results = {}
    scenario_definition = {}
    for scenario in SCENARIOS:
        pairs = {}
        for pair_label, lower_layer, upper_layer in PAIRS:
            labels, families, lower_values, upper_values = gather(
                pair_label, lower_layer, upper_layer, tables, subset
            )
            if len(labels) < 3:
                continue
            entry = {}
            for objective, key in (("oxidation", "ox"), ("reduction", "red")):
                delta_value, note = delta_m_for(
                    lower_layer.lower(), objective, scenario, candidates
                )
                lower = [(row[key],) for row in lower_values]
                upper = [(row[key],) for row in upper_values]
                item = compare(pair_label, labels, families, lower, upper, delta_value)
                item["objective"] = objective
                item["delta_m_source"] = note
                entry[objective] = item
            pairs[pair_label] = entry
        results[scenario] = pairs
        scenario_definition[scenario] = {
            "delta_m_text": {
                "z_only": "delta_m = 0（等于不启用固定容差）",
                "floor_only": "delta_m = 0.05 eV（4.8242 kJ/mol）",
                "docx_max": "delta_m = max(构象 90 分位展宽, 方法 pstdev, 0.05 eV)，见 T8",
            }[scenario],
            "note": {
                "z_only": "Week 5 及之前的临时口径，作为对照基线",
                "floor_only": "只看规划文档的数值下限，隔离 delta_m 中\"证据驱动\"部分的效果",
                "docx_max": "主口径：完整 docx §6.2 合成规则",
            }[scenario],
        }

    consistency = []
    stored = REPO_ROOT / "outputs" / "week5" / "c1_decision_stability.json"
    if stored.exists():
        with io.open(stored, encoding="utf-8") as handle:
            reference = json.load(handle)
        for objective in ("oxidation", "reduction"):
            mine = results["z_only"].get("C0_to_C1", {}).get(objective)
            if mine is None:
                continue
            theirs = reference[objective]["kendall_tau_b"]
            ok = abs(mine["kendall_tau_b"] - theirs) < 1e-9
            consistency.append(
                "C0→C1 %s 的 tau_b：本轮复算 %.6f，Week 5 记录 %.6f → %s"
                % (objective, mine["kendall_tau_b"], theirs, "一致" if ok else "**不一致**")
            )
    consistency.append(
        "P1→P2 与 C0→C1 的 delta_m 复用了 P0/P1 证据（见每行的 delta_m_source 字段），"
        "因为本仓库内 P2 层与 C1 层没有第二个同层级方法可对照。"
    )

    payload = {
        "stage": "T9 (Stage 6)",
        "title": "uncertainty-aware ranking analysis: z*sigma with and without delta_m",
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "prereg": {
            "z_primary": Z_PRIMARY,
            "z_sensitivity": Z_SENSITIVITY,
            "unresolved_rule": "|dP_ij| < delta_m 或 |dP_ij| < z*sigma_ij",
            "unresolved_denominator": "C(N,2)",
            "robust_inv_denominator": "N_pairs_resolved_in_both",
            "bootstrap": {"repetitions": BOOTSTRAP_REPETITIONS, "alpha": BOOTSTRAP_ALPHA,
                          "seeds": list(BOOTSTRAP_SEEDS)},
            "prob_band": [PROB_LOW, PROB_HIGH],
        },
        "layers": {
            "P0": "GFN2-xTB Koopmans (ox = -eps_HOMO, red = -EA_koopmans)",
            "P1": "r2SCAN-3c vertical, gas, G1 geometry",
            "P2": "r2SCAN-3c vertical, CPCM eps=10",
            "C0": "r2SCAN-3c vertical at the G2 geometry (T2)",
            "C1": "r2SCAN-3c vertical at the optimised [Li M]+ geometry, primary motif m1",
            "direction": "ox = IP (ev), red = -EA (ev); both maximise",
        },
        "delta_m_candidates": candidates,
        "scenario_definition": scenario_definition,
        "subset": subset,
        "results": results,
        "consistency_checks": consistency,
        "command": " ".join(sys.argv),
    }

    json_path = args.outdir / "stage6_decision_stability.json"
    json_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    csv_path = args.outdir / "stage6_decision_stability.csv"
    write_csv(csv_path, results)
    md_path = args.outdir / "stage6_decision_stability.md"
    write_markdown(md_path, payload)

    for scenario in SCENARIOS:
        for key, block in results[scenario].items():
            for objective in ("oxidation", "reduction"):
                item = block[objective]
                print(
                    "[T9] %-9s %-11s %-9s delta_m=%.4f  f_unres(lo/hi)=%.3f/%.3f  f_robust_inv=%.3f"
                    % (scenario, key, objective, item["delta_m_ev"],
                       item["f_unresolved_lower"], item["f_unresolved_upper"], item["f_robust_inv"])
                )
    print("[T9] wrote %s" % json_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())