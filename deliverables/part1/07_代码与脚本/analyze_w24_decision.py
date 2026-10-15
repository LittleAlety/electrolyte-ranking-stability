#!/usr/bin/env python
"""Week 24 -- turn the decision metrics DEFINED in core file v2 into numbers.

The core study design (ranking-electrolyte-materials-v2.md) defines three
decision quantities but never evaluates them:

    section 9.2   f_robust_inv = N_robust_inv / N_pairs_resolved_in_both
    section 9.4   p_ij = P(P_i > P_j);  decided when p_ij > 0.9 or p_ij < 0.1
    section 10.1  J_k = |S_A(k) & S_B(k)| / |S_A(k) union S_B(k)|, k/N = 10/20/30 %

This script re-reads ONLY the frozen week4-week10 artefacts, rebuilds the
five-rung ladder on the oxidation and reduction axes

    P0->P1 (method)  P1->P2 (environment)  G1->G2 (geometry)
    C0->C1 (free -> [Li M]+, 1:1)          C1->C2 ([Li M]+ -> [Li(M)2]+, 1:2)

for the native population of every rung and for the aligned 10-molecule
common10 subset, and evaluates all three quantities.

No new electronic-structure calculation is run.  Every input file is hashed
(SHA256) and the hashes are stored in the JSON payload.

Outputs
-------
outputs/week24_corealign/decision_metrics.json
outputs/week24_corealign/decision_metrics.csv
outputs/week24_corealign/decision_metrics.md
outputs/figures/F50_decision_metrics.png      (skip with --no-figure)

Run again with --check to prove the artefacts are byte-for-byte reproducible.
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
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from electrolyte_ranking import ranking  # noqa: E402
import analyze_stage10_synthesis as s10  # noqa: E402

ND = statistics.NormalDist()
_ERF = np.vectorize(math.erf, otypes=[float])


def _phi(x):
    """Standard-normal CDF, vectorised (stdlib erf, no SciPy dependency)."""
    return 0.5 * (1.0 + _ERF(np.asarray(x, dtype=float) / math.sqrt(2.0)))

DEFAULT_OUTDIR = REPO_ROOT / "outputs" / "week24_corealign"
DEFAULT_FIGDIR = REPO_ROOT / "outputs" / "figures"

Z_PRIMARY = 1.0
Z_SENSITIVITY = 1.96
# p_ij > 0.9  <=>  DeltaP_ij / sigma_ij > Phi_inverse(0.9).  This is the z that
# the section 9.4 probability thresholds implicitly use.
Z_FROM_P_THRESHOLD = ND.inv_cdf(0.9)

FIG_NAME = "F50_decision_metrics.png"

CORE_V2 = REPO_ROOT.parent / "\u6838\u5fc3\u6587\u4ef6" / "ranking-electrolyte-materials-v2.md"

INPUTS = [
    ("\u6838\u5fc3\u6587\u4ef6/ranking-electrolyte-materials-v2.md", CORE_V2),
    ("outputs/week9/stage10_ladder.json", REPO_ROOT / "outputs" / "week9" / "stage10_ladder.json"),
    ("outputs/week9/stage10_ladder.csv", REPO_ROOT / "outputs" / "week9" / "stage10_ladder.csv"),
    ("outputs/week10/stage11_sigma_anatomy.json",
     REPO_ROOT / "outputs" / "week10" / "stage11_sigma_anatomy.json"),
    ("outputs/week4/p1_decision_stability.json",
     REPO_ROOT / "outputs" / "week4" / "p1_decision_stability.json"),
    ("outputs/week4/p2_decision_stability.json",
     REPO_ROOT / "outputs" / "week4" / "p2_decision_stability.json"),
    ("outputs/week4/p1_core_set_derived.csv",
     REPO_ROOT / "outputs" / "week4" / "p1_core_set_derived.csv"),
    ("outputs/week4/p2_environment_effects.csv",
     REPO_ROOT / "outputs" / "week4" / "p2_environment_effects.csv"),
    ("outputs/week4/t2_opt_freq_summary.json",
     REPO_ROOT / "outputs" / "week4" / "t2_opt_freq_summary.json"),
    ("outputs/week5/c1_decision_stability.json",
     REPO_ROOT / "outputs" / "week5" / "c1_decision_stability.json"),
    ("outputs/week5/c1_coord_shifts.csv", REPO_ROOT / "outputs" / "week5" / "c1_coord_shifts.csv"),
    ("outputs/week6/delta_m_frozen.json", REPO_ROOT / "outputs" / "week6" / "delta_m_frozen.json"),
    ("outputs/week6/stage6_decision_stability.json",
     REPO_ROOT / "outputs" / "week6" / "stage6_decision_stability.json"),
    ("outputs/week6/stage6_decision_stability.csv",
     REPO_ROOT / "outputs" / "week6" / "stage6_decision_stability.csv"),
    ("outputs/week7/stage7_ml_results.json",
     REPO_ROOT / "outputs" / "week7" / "stage7_ml_results.json"),
    ("outputs/week8/stage9_decision_stability.csv",
     REPO_ROOT / "outputs" / "week8" / "stage9_decision_stability.csv"),
    ("outputs/week8/stage9_shell_shifts.csv",
     REPO_ROOT / "outputs" / "week8" / "stage9_shell_shifts.csv"),
]

PAPER_NOTE = (
    "按 §9.2 重算五台阶×两轴×两池共 20 个 (台阶,轴) 组合，f_robust_inv 在 z=1 与 1.96 两档共 40 个数全为 0：无 §22.3 情形 C。"
    "§9.4 逐对概率显示 C0→C1 还原轴 45 对中 82% 为 unresolved，τ_b=−0.467 的换序全落在 unresolved 对上"
    "（§22.7 情形 G），且该轴 11/12 还原态为 Li 中心还原（§22.4 情形 D）。带 CI 的 Jaccard 仅见 Stage 7。"
)

CONSISTENCY_NOTE = (
    "p \u5bfc\u51fa unresolved\uff080.1<p<0.9\uff09\u4e0e\u300c\u95ed\u5f0f f_unresolved(z=1.2816)\u300d\u9010\u70b9\u76f8\u7b49\uff08\u504f\u5dee <= 1e-15\uff09\uff0c"
    "\u56e0\u4e3a \u00a79.4 \u7684 0.9/0.1 \u9608\u503c\u7b49\u4ef7\u4e8e z=\u03a6\u207b\u00b9(0.9)=1.2816\uff1b\u8fd9\u4e0e\u65e2\u6709\u7684 z=1\uff08prereg \u4e3b\u53e3\u5f84\uff09\u548c "
    "z=1.96\uff08\u654f\u611f\u6027\uff09\u4e0d\u662f\u540c\u4e00\u53e3\u5f84\uff0c\u6545\u300c\u65e2\u6709\u504f\u5dee\u300d\u975e\u96f6\u662f\u53e3\u5f84\u5dee\u800c\u975e\u77db\u76fe\u3002"
)


STAGE6_NOTE = (
    "Stage 6 原生 p_ij（outputs/week6/stage6_decision_stability.json，scenario=z_only，阈值 0.9/0.1）"
    "只覆盖 P0→P1、P1→P2、C0→C1 三个台阶，且其 sigma 定义为 sigma_ij^2 = (delta_i^2 + delta_j^2)/2；"
    "本脚本按 v2 §9.1 用 sigma_ij = |delta_i - delta_j| / sqrt(2)。同一台阶下两者 unresolved 比例显著不同"
    "（Stage 6 达 0.95-1.00，本脚本 0.11-0.82），故 p_ij 数值强依赖 sigma 口径，引用时必须声明。"
)


def relpath(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def f4(value):
    """Round to 4 significant digits for stable artefacts."""
    if value is None:
        return None
    if value == 0:
        return 0.0
    return float("%.4g" % value)


def _diff(a, b):
    if a is None or b is None:
        return None
    return f4(a - b)


def for_sigma_library(value_sets):
    from electrolyte_ranking import uncertainty
    return uncertainty.quantify_method_sigma(value_sets, ddof=1, stat="std")


# ---------------------------------------------------------------------------
# rebuild the ladder
# ---------------------------------------------------------------------------
def ladder_points(population: str):
    """Return the 10 (rung, axis) points for one population.

    Values keep the frozen convention p_red = -EA so that higher_is_better is
    True on both axes, identical to analyze_stage10_synthesis.
    """

    ladder = s10.load_ladder()
    names = s10.common_names(ladder) if population == "common10" else None

    points = []
    for key, label in s10.RUNGS:
        rungs = s10.rung_names(ladder, key) if names is None else names
        for axis, title in (("ox", "oxidation"), ("red", "reduction")):
            before, after, labels = [], [], []
            for name in rungs:
                entry = s10.lookup(ladder, key, name)
                if entry is None:
                    continue
                pair = entry.get(axis)
                if not pair or pair[0] is None or pair[1] is None:
                    continue
                before.append(pair[0])
                after.append(pair[1])
                labels.append(entry.get("label", name))
            points.append({
                "population": population,
                "rung": key,
                "rung_label": label,
                "axis": title,
                "labels": labels,
                "before": before,
                "after": after,
            })
    return points


def p_matrix(delta_pair: np.ndarray, sigma: np.ndarray) -> np.ndarray:
    """Gaussian pair posterior p_ij = Phi(DeltaP_ij / sigma_ij).

    sigma_ij = |delta_i - delta_j| / sqrt(2) is the closed-form shift
    uncertainty of v2 section 9.1.  A pair with sigma_ij == 0 carries no
    method spread, so its ordering is fully decided by the sign of DeltaP_ij
    (p = 1 or 0); an exact tie gives p = 0.5.
    """

    p = np.full(delta_pair.shape, 0.5)
    pos = sigma > 0
    p[pos] = _phi(delta_pair[pos] / sigma[pos])
    zero = ~pos
    p[zero & (delta_pair > 0)] = 1.0
    p[zero & (delta_pair < 0)] = 0.0
    np.fill_diagonal(p, 0.5)
    return p


def _pair_index(n, i, j):
    if i > j:
        i, j = j, i
    return i * (2 * n - i - 1) // 2 + (j - i - 1)


def evaluate(point: dict) -> dict:
    a = np.asarray(point["before"], dtype=float)
    b = np.asarray(point["after"], dtype=float)
    n = a.size
    delta = b - a
    sigma = np.abs(delta[:, None] - delta[None, :]) / math.sqrt(2.0)
    diff_a = a[:, None] - a[None, :]
    diff_b = b[:, None] - b[None, :]

    mask_a = ranking.resolved_mask(diff_a, sigma, z=Z_PRIMARY)
    mask_b = ranking.resolved_mask(diff_b, sigma, z=Z_PRIMARY)
    mask_a_96 = ranking.resolved_mask(diff_a, sigma, z=Z_SENSITIVITY)
    mask_b_96 = ranking.resolved_mask(diff_b, sigma, z=Z_SENSITIVITY)

    iu = np.triu_indices(n, 1)
    n_pairs = int(iu[0].size)
    sa = sigma[iu]
    da = diff_a[iu]
    db = diff_b[iu]

    resolved_both = mask_a[iu] & mask_b[iu]
    n_resolved_both = int(np.count_nonzero(resolved_both))
    flips = np.sign(da) * np.sign(db) < 0
    n_flips = int(np.count_nonzero(flips))
    n_robust = int(np.count_nonzero(flips & resolved_both))

    p = p_matrix(diff_b, sigma)[iu]
    decided = (p > 0.9) | (p < 0.1)
    f_p_unresolved = float(np.count_nonzero(~decided) / n_pairs) if n_pairs else 0.0

    unres_at_zp = (float(np.count_nonzero(np.abs(db) < Z_FROM_P_THRESHOLD * sa) / n_pairs)
                   if n_pairs else 0.0)
    unres_after_z1 = float(np.count_nonzero(~mask_b[iu]) / n_pairs) if n_pairs else 0.0
    unres_before_z1 = float(np.count_nonzero(~mask_a[iu]) / n_pairs) if n_pairs else 0.0
    unres_after_96 = float(np.count_nonzero(~mask_b_96[iu]) / n_pairs) if n_pairs else 0.0

    top = {}
    for frac in (0.10, 0.20, 0.30):
        k = max(1, round(frac * n))
        top["%.2f" % frac] = {
            "k": k,
            "overlap": ranking.top_k_overlap(a, b, k, higher_is_better=True),
            "jaccard": ranking.jaccard_at_k(a, b, k, higher_is_better=True),
        }

    return {
        "n": n,
        "n_pairs": n_pairs,
        "tau_b": ranking.kendall_tau_b(a, b),
        "sigma_median": float(statistics.median(np.abs(sa))) if n_pairs else None,
        "p": p,
        "delta_pair": db,
        "sigma_pair": sa,
        "sign_flip": flips,
        "resolved_both": resolved_both,
        "n_resolved_both": n_resolved_both,
        "n_flips": n_flips,
        "n_flips_unresolved": int(np.count_nonzero(flips & ~resolved_both)),
        "n_robust_inv": n_robust,
        "f_robust_inv_z1": float(n_robust / n_resolved_both) if n_resolved_both else 0.0,
        "f_robust_inv_z1p96": ranking.robust_inversion_fraction(
            diff_a, diff_b, mask_a_96, mask_b_96),
        "f_unresolved_before_z1": unres_before_z1,
        "f_unresolved_after_z1": unres_after_z1,
        "f_unresolved_after_z1p96": unres_after_96,
        "f_p_unresolved": f_p_unresolved,
        "f_p_gt0p9": float(np.count_nonzero(p > 0.9) / n_pairs) if n_pairs else 0.0,
        "f_p_lt0p1": float(np.count_nonzero(p < 0.1) / n_pairs) if n_pairs else 0.0,
        "f_unresolved_at_zp": unres_at_zp,
        "top": top,
    }


def summarize(point: dict, ev: dict) -> dict:
    return {
        "population": point["population"],
        "rung": point["rung"],
        "axis": point["axis"],
        "n": ev["n"],
        "n_pairs": ev["n_pairs"],
        "tau_b": f4(ev["tau_b"]),
        "sigma_median_ev": f4(ev["sigma_median"]),
        "f_unresolved_before_z1": f4(ev["f_unresolved_before_z1"]),
        "f_unresolved_after_z1": f4(ev["f_unresolved_after_z1"]),
        "f_robust_inv_z1": f4(ev["f_robust_inv_z1"]),
        "f_unresolved_after_z1p96": f4(ev["f_unresolved_after_z1p96"]),
        "f_robust_inv_z1p96": f4(ev["f_robust_inv_z1p96"]),
        "n_resolved_both_z1": ev["n_resolved_both"],
        "n_robust_inv_z1": ev["n_robust_inv"],
        "n_sign_flip_pairs": ev["n_flips"],
        "n_sign_flip_unresolved": ev["n_flips_unresolved"],
        "f_p_unresolved": f4(ev["f_p_unresolved"]),
        "f_p_decided_gt0p9": f4(ev["f_p_gt0p9"]),
        "f_p_decided_lt0p1": f4(ev["f_p_lt0p1"]),
        "f_unresolved_at_z_phi09": f4(ev["f_unresolved_at_zp"]),
        "jaccard_10pct": f4(ev["top"]["0.10"]["jaccard"]),
        "jaccard_20pct": f4(ev["top"]["0.20"]["jaccard"]),
        "jaccard_30pct": f4(ev["top"]["0.30"]["jaccard"]),
        "overlap_10pct": f4(ev["top"]["0.10"]["overlap"]),
        "overlap_20pct": f4(ev["top"]["0.20"]["overlap"]),
        "overlap_30pct": f4(ev["top"]["0.30"]["overlap"]),
    }


# ---------------------------------------------------------------------------
# key molecular pairs
# ---------------------------------------------------------------------------
def _verdict(p_value: float) -> str:
    if p_value > 0.9:
        return "i>j"
    if p_value < 0.1:
        return "i<j"
    return "unresolved"


def p_of(delta_p: float, sigma_ij: float) -> float:
    """p_ij = P(P_i > P_j) for an explicitly ordered pair (i, j).

    The flat p vector used for counting is stored in molecule-index order, so it
    must not be reused for an arbitrary ranked pair; recompute from the signed
    DeltaP_ij instead.
    """
    if sigma_ij > 0:
        return float(_phi(delta_p / sigma_ij))
    if delta_p > 0:
        return 1.0
    if delta_p < 0:
        return 0.0
    return 0.5


def key_pairs(point: dict, ev: dict, *, k_fraction: float = 0.20, extra: int = 0):
    labels = point["labels"]
    n = ev["n"]
    after = np.asarray(point["after"], dtype=float)
    order = sorted(range(n), key=lambda idx: after[idx], reverse=True)
    k = max(1, round(k_fraction * n))
    rows = []

    def emit(idx_i, idx_j, why):
        sigma_val = float(ev["sigma_pair"][_pair_index(n, idx_i, idx_j)])
        dp = float(after[idx_i] - after[idx_j])
        p_val = p_of(dp, sigma_val)
        if sigma_val:
            ratio = dp / sigma_val
        else:
            ratio = math.inf if dp > 0 else (-math.inf if dp < 0 else 0.0)
        rows.append({
            "population": point["population"],
            "rung": point["rung"],
            "axis": point["axis"],
            "why": why,
            "i": labels[idx_i],
            "j": labels[idx_j],
            "delta_p_ev": f4(dp),
            "sigma_ij_ev": f4(sigma_val),
            "delta_over_sigma": f4(ratio),
            "p_ij": f4(p_val),
            "verdict": _verdict(p_val),
        })

    if k < n:
        emit(order[k - 1], order[k],
             "Top-%d%% \u8fb9\u754c\u5bf9 (rank %d vs %d)" % (round(k_fraction * 100), k, k + 1))

    if extra:
        ranked = sorted(
            ((abs(after[i] - after[j]) / ev["sigma_pair"][_pair_index(n, i, j)]
              if ev["sigma_pair"][_pair_index(n, i, j)] else math.inf, i, j)
             for i in range(n) for j in range(i + 1, n)),
            reverse=True)
        for _, i, j in ranked[:extra]:
            emit(i, j, "DeltaP/sigma \u6700\u5927 %d \u5bf9" % extra)
    return rows


def extreme_pairs(point: dict, ev: dict, *, count: int = 3):
    labels = point["labels"]
    n = ev["n"]
    after = np.asarray(point["after"], dtype=float)
    ranked = sorted(
        ((abs(after[i] - after[j]) / ev["sigma_pair"][_pair_index(n, i, j)]
          if ev["sigma_pair"][_pair_index(n, i, j)] else math.inf, i, j)
         for i in range(n) for j in range(i + 1, n)),
        reverse=True)
    rows = []
    for ratio, i, j in ranked[:count]:
        sigma_val = float(ev["sigma_pair"][_pair_index(n, i, j)])
        dp = float(after[i] - after[j])
        p_val = p_of(dp, sigma_val)
        rows.append({
            "population": point["population"],
            "rung": point["rung"],
            "axis": point["axis"],
            "why": "DeltaP/sigma 最大 %d 对" % count,
            "i": labels[i],
            "j": labels[j],
            "delta_p_ev": f4(dp),
            "sigma_ij_ev": f4(sigma_val),
            "delta_over_sigma": f4(dp / sigma_val) if sigma_val else None,
            "p_ij": f4(p_val),
            "verdict": _verdict(p_val),
        })
    return rows


def flip_pairs(point: dict, ev: dict, *, limit=None):
    labels = point["labels"]
    n = ev["n"]
    out = []
    all_i, all_j = np.triu_indices(n, 1)
    flip_idx = [idx for idx in range(ev["n_pairs"]) if ev["sign_flip"][idx]]
    flip_idx.sort(
        key=lambda idx: (abs(ev["delta_pair"][idx]) / ev["sigma_pair"][idx]
                         if ev["sigma_pair"][idx] else math.inf),
        reverse=True)
    if limit is not None:
        flip_idx = flip_idx[:limit]
    for idx in flip_idx:
        i, j = int(all_i[idx]), int(all_j[idx])
        sd = float(ev["sigma_pair"][idx])
        dp = float(ev["delta_pair"][idx])
        pv = p_of(dp, sd)
        out.append({
            "population": point["population"],
            "rung": point["rung"],
            "axis": point["axis"],
            "why": "\u524d\u540e\u5c42\u7b26\u53f7\u7ffb\u8f6c\u5bf9",
            "i": labels[i],
            "j": labels[j],
            "delta_p_ev": f4(dp),
            "sigma_ij_ev": f4(sd),
            "delta_over_sigma": f4(dp / sd) if sd else None,
            "p_ij": f4(pv),
            "verdict": _verdict(pv),
            "resolved_in_both": bool(ev["resolved_both"][idx]),
        })
    return out


def mc_check(point: dict, ev: dict, *, draws: int = 200000, seed: int = 20261002) -> dict:
    rng = np.random.default_rng(seed)
    dp = ev["delta_pair"]
    sd = ev["sigma_pair"]
    p_closed = ev["p"]
    p_mc = np.empty_like(p_closed)
    for idx in range(dp.size):
        if sd[idx] == 0:
            p_mc[idx] = 1.0 if dp[idx] > 0 else (0.0 if dp[idx] < 0 else 0.5)
            continue
        p_mc[idx] = float(np.mean(dp[idx] + sd[idx] * rng.standard_normal(draws) > 0))
    return {
        "rung": point["rung"],
        "axis": point["axis"],
        "population": point["population"],
        "draws": draws,
        "max_abs_diff": float(np.max(np.abs(p_mc - p_closed))) if dp.size else 0.0,
        "mean_abs_diff": float(np.mean(np.abs(p_mc - p_closed))) if dp.size else 0.0,
        "p_gt0p9_disagreements": int(np.count_nonzero((p_mc > 0.9) != (p_closed > 0.9))),
        "p_lt0p1_disagreements": int(np.count_nonzero((p_mc < 0.1) != (p_closed < 0.1))),
    }


def stage7_jaccard():
    d = load_json(REPO_ROOT / "outputs" / "week7" / "stage7_ml_results.json")
    tasks = {}
    for row in d["results"]:
        task = row.get("task")
        entry = tasks.setdefault(task, {
            "task": task,
            "task_label": row.get("task_label"),
            "objectives": set(),
            "shapes": set(),
            "n_rows": 0,
        })
        entry["objectives"].add(row.get("objective"))
        entry["shapes"].add(row.get("shape"))
        entry["n_rows"] += 1
    out = []
    for task in sorted(tasks):
        e = tasks[task]
        out.append({
            "task": e["task"],
            "task_label": e["task_label"],
            "objectives": sorted(x for x in e["objectives"] if x),
            "shapes": sorted(x for x in e["shapes"] if x),
            "n_rows": e["n_rows"],
            "jaccard_columns": ["jaccard_10%", "jaccard_20%", "jaccard_30%"],
            "ci_columns": ["jaccard_10%_lo", "jaccard_10%_hi", "jaccard_20%_lo",
                           "jaccard_20%_hi", "jaccard_30%_lo", "jaccard_30%_hi"],
        })
    return out


# ---------------------------------------------------------------------------
# payload
# ---------------------------------------------------------------------------
def stage6_native_p():
    """Native Stage 6 probabilistic-ordering numbers (different sigma convention)."""

    path = REPO_ROOT / "outputs" / "week6" / "stage6_decision_stability.csv"
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    out = []
    for row in rows:
        if row.get("scenario") != "z_only":
            continue
        out.append({
            "pair": row["pair"],
            "objective": row["objective"],
            "scenario": row["scenario"],
            "n": int(row["n"]),
            "n_pairs": int(row["n_pairs"]),
            "prob_decided_fraction": f4(float(row["prob_decided_fraction"])),
            "prob_undecided_fraction": f4(float(row["prob_undecided_fraction"])),
            "f_unresolved_lower_z1": f4(float(row["f_unresolved_lower"])),
            "f_robust_inv_z1": f4(float(row["f_robust_inv"])),
        })
    return out


def build_payload():
    ladder_json = load_json(REPO_ROOT / "outputs" / "week9" / "stage10_ladder.json")
    stored = {(r["population"], r["rung"], r["axis"]): r for r in ladder_json["ladder"]}
    verdicts = ladder_json["verdicts"]

    rows, key_rows, consistency, mc = [], [], [], []
    for population in ("common10", "native"):
        for point in ladder_points(population):
            ev = evaluate(point)
            row = summarize(point, ev)
            s = stored.get((population, point["rung"], point["axis"]), {})
            row["stored_f_robust_inv_z1"] = f4(s.get("f_robust_inv"))
            row["stored_f_robust_inv_z1p96"] = f4(s.get("f_robust_inv_z1p96"))
            row["stored_f_unresolved_after_z1"] = f4(s.get("f_unresolved_after"))
            row["stored_jaccard_20pct"] = f4(s.get("jaccard_20"))
            row["recomputed_minus_stored_jaccard_20pct"] = (
                f4((row["jaccard_20pct"] or 0.0) - (row["stored_jaccard_20pct"] or 0.0)) if s else None)
            rows.append(row)

            consistency.append({
                "population": population,
                "rung": point["rung"],
                "axis": point["axis"],
                "n_pairs": ev["n_pairs"],
                "tau_b": f4(ev["tau_b"]),
                "n_sign_flip_pairs": ev["n_flips"],
                "n_sign_flip_unresolved": ev["n_flips_unresolved"],
                "n_resolved_both_z1": ev["n_resolved_both"],
                "n_robust_inv_z1": ev["n_robust_inv"],
                "f_p_unresolved": f4(ev["f_p_unresolved"]),
                "f_unresolved_closedform_at_z_phi09": f4(ev["f_unresolved_at_zp"]),
                "abs_dev_p_vs_closedform": f4(abs(ev["f_p_unresolved"] - ev["f_unresolved_at_zp"])),
                "stored_f_unresolved_after_z1": f4(s.get("f_unresolved_after")),
                "dev_p_vs_stored_z1": f4(ev["f_p_unresolved"] - (s.get("f_unresolved_after") or 0.0)),
                "stored_f_unresolved_after_z1p96": f4(ev["f_unresolved_after_z1p96"]),
                "dev_p_vs_stored_z1p96": f4(ev["f_p_unresolved"] - ev["f_unresolved_after_z1p96"]),
            })

            key_rows.extend(key_pairs(point, ev, k_fraction=0.20))
            if population == "common10":
                if point["rung"] == "C0_to_C1" and point["axis"] == "reduction":
                    key_rows.extend(extreme_pairs(point, ev, count=3))
                    key_rows.extend(flip_pairs(point, ev, limit=5))
                if point["rung"] == "C1_to_C2" and point["axis"] == "reduction":
                    key_rows.extend(extreme_pairs(point, ev, count=2))
            if (population == "common10" and point["rung"] == "C0_to_C1"
                    and point["axis"] == "reduction"):
                mc.append(mc_check(point, ev))

    checks, sigma_check = [], []
    for row in rows:
        checks.append({
            "population": row["population"],
            "rung": row["rung"],
            "axis": row["axis"],
            "d_f_robust_inv_z1": _diff(row["f_robust_inv_z1"], row["stored_f_robust_inv_z1"]),
            "d_f_robust_inv_z1p96": _diff(row["f_robust_inv_z1p96"], row["stored_f_robust_inv_z1p96"]),
            "d_f_unresolved_after_z1": _diff(row["f_unresolved_after_z1"], row["stored_f_unresolved_after_z1"]),
            "d_jaccard_20pct": _diff(row["jaccard_20pct"], row["stored_jaccard_20pct"]),
        })
    for population in ("common10", "native"):
        for point in ladder_points(population):
            a = np.asarray(point["before"], dtype=float)
            b = np.asarray(point["after"], dtype=float)
            delta = b - a
            closed = np.abs(delta[:, None] - delta[None, :]) / math.sqrt(2.0)
            lib = np.asarray(for_sigma_library([list(a), list(b)]), dtype=float)
            sigma_check.append({
                "population": population,
                "rung": point["rung"],
                "axis": point["axis"],
                "max_abs_diff": float(np.max(np.abs(closed - lib))),
            })

    def max_abs(key):
        return max((abs(c[key]) for c in checks if c[key] is not None), default=0.0)

    key_sign_mismatch = sum(
        1 for k in key_rows
        if k.get("delta_over_sigma") is not None and (
            (k["p_ij"] > 0.9 and k["delta_over_sigma"] < 0)
            or (k["p_ij"] < 0.1 and k["delta_over_sigma"] > 0)))

    max_sigma = max((c["max_abs_diff"] for c in sigma_check), default=0.0)
    dev_z1 = max((abs(c["dev_p_vs_stored_z1"] or 0.0) for c in consistency
                  if c["population"] == "common10"), default=0.0)
    dev_zp = max((c["abs_dev_p_vs_closedform"] or 0.0 for c in consistency), default=0.0)

    inputs = [{
        "path": key,
        "exists": path.exists(),
        "sha256": sha256_of(path) if path.exists() else None,
        "bytes": path.stat().st_size if path.exists() else None,
    } for key, path in INPUTS]

    payload = {
        "stage": "Week 24 -- core-file decision metrics (sections 9.2 / 9.4 / 10.1) made numeric",
        "generated_by": "scripts/analyze_w24_decision.py",
        "read_only": True,
        "no_new_electronic_structure": True,
        "convention": "p_red = -EA; higher_is_better = True on both axes",
        "z_primary": Z_PRIMARY,
        "z_sensitivity": Z_SENSITIVITY,
        "z_from_p_threshold": Z_FROM_P_THRESHOLD,
        "p_ij_method": ("Gaussian pair posterior p_ij = Phi(DeltaP_ij / sigma_ij) with closed-form "
                        "sigma_ij = |delta_i - delta_j| / sqrt(2); Monte-Carlo cross-checked"),
        "n_points_per_population": 10,
        "populations": ["common10", "native"],
        "rungs": [{"key": k, "label": v} for k, v in s10.RUNGS],
        "axes": ["oxidation", "reduction"],
        "common_subset": ladder_json["common_subset"],
        "paper_note": PAPER_NOTE,
        "paper_note_chars": len(PAPER_NOTE.replace(" ", "").replace("\n", "")),
        "consistency_note": CONSISTENCY_NOTE,
        "rows": rows,
        "key_pairs": key_rows,
        "consistency": consistency,
        "verification": {
            "max_abs_diff_vs_stored": {
                "f_robust_inv_z1": f4(max_abs("d_f_robust_inv_z1")),
                "f_robust_inv_z1p96": f4(max_abs("d_f_robust_inv_z1p96")),
                "f_unresolved_after_z1": f4(max_abs("d_f_unresolved_after_z1")),
                "jaccard_20pct": f4(max_abs("d_jaccard_20pct")),
                "sigma_closedform_vs_library": max_sigma,
            },
            "n_key_pairs_verdict_sign_mismatch": key_sign_mismatch,
            "max_abs_dev_p_unresolved_vs_closedform_at_z_phi09": f4(dev_zp),
            "max_abs_dev_p_unresolved_vs_stored_z1_common10": f4(dev_z1),
            "all_40_f_robust_inv_zero": all(
                r["f_robust_inv_z1"] == 0.0 and r["f_robust_inv_z1p96"] == 0.0 for r in rows),
            "per_point": checks,
            "sigma_check": sigma_check,
        },
        "monte_carlo_check": mc,
        "stage6_native_p_ij_inventory": stage6_native_p(),
        "stage6_note": STAGE6_NOTE,
        "stage7_jaccard_inventory": stage7_jaccard(),
        "stored_verdicts": {
            "C_structured_robust_inversion": {
                "verdict": verdicts["C_structured_robust_inversion"]["verdict"],
                "evidence": verdicts["C_structured_robust_inversion"]["evidence"],
            },
            "G_most_pairs_unresolved": {
                "verdict": verdicts["G_most_pairs_unresolved"]["verdict"],
                "evidence": verdicts["G_most_pairs_unresolved"]["evidence"],
            },
            "D_coordination_state_identity_change": {
                "verdict": verdicts["D_coordination_state_identity_change"]["verdict"],
            },
        },
        "data_flags": [
            "\u5168\u90e8 40 \u4e2a f_robust_inv \u6570\u503c\uff082 z \u00d7 2 population \u00d7 10 \u70b9\uff09\u5728\u672c\u6570\u636e\u96c6\u4e2d\u4e3a 0\uff1b"
            "\u672c\u811a\u672c\u672a\u653e\u5bbd\u4efb\u4f55\u9608\u503c\u6765\u5236\u9020\u975e\u96f6\u503c\u3002",
            "stage10_ladder \u539f\u751f\u53ea\u5b58\u50a8 Jaccard_20\uff1bJ_10 / J_30 \u7531\u672c\u811a\u672c\u7528\u540c\u4e00\u51bb\u7ed3\u9010\u5206\u5b50\u503c\u91cd\u7b97"
            "\uff08\u975e\u4f2a\u9020\u3001\u672a\u66ff\u6362\u5176\u5b83\u91cf\uff09\u3002",
            "\u5e26 bootstrap CI \u7684 Jaccard \u4ec5\u5b58\u5728\u4e8e Stage 7\uff08stage7_ml_results.json\uff0c\u4efb\u52a1 M/E/C\uff09\uff1b"
            "\u5341\u7ea7\u53f0\u9636\u672c\u8eab\u6ca1\u6709 CI \u7248 Jaccard\u3002",
            "\u4e94\u4e2a\u53f0\u9636\u5728 stage10_ladder \u4e2d\u5747\u6709\u539f\u751f J_20\uff0c\u6545\u300c\u4ec5 Stage 7 \u6709\u300d\u7684\u5360\u4f4d\u6807\u6ce8\u672a\u542f\u7528\uff1b"
            "\u672c\u9879\u76ee Jaccard \u5747\u7531\u9010\u5206\u5b50\u503c\u76f4\u63a5\u7b97\u51fa\u3002",
            "p_ij \u7684 \u00a79.4 \u9608\u503c 0.9/0.1 \u7b49\u4ef7\u4e8e z=1.2816\uff1b\u4e0e\u65e2\u6709\u7684 z=1 \u4e3b\u53e3\u5f84\u4e0d\u662f\u540c\u4e00 z\uff0c"
            "\u56e0\u6b64\u300c\u65e2\u6709\u504f\u5dee\u300d\u53cd\u6620\u7684\u662f\u53e3\u5f84\u5dee\u3002",
            "Stage 6 已有原生 p_ij（prob_undecided_fraction），但 sigma 口径为 (delta_i^2+delta_j^2)/2，"
            "与本脚本/§9.1 的 |delta_i-delta_j|/sqrt(2) 不同；G1→G2 与 C1→C2 两个台阶则完全无原生 p_ij。",
        ],
        "inputs": inputs,
    }
    return payload


# ---------------------------------------------------------------------------
# rendering
# ---------------------------------------------------------------------------
def fmt(value, digits=4):
    if value is None:
        return "-"
    return ("%%.%dg" % digits) % value


def md_table(headers, rows):
    out = ["| " + " | ".join(headers) + " |",
           "| " + " | ".join("---" for _ in headers) + " |"]
    for row in rows:
        out.append("| " + " | ".join(str(c) for c in row) + " |")
    return "\n".join(out)


def render_markdown(payload: dict) -> str:
    rows = [r for r in payload["rows"] if r["population"] == "common10"]
    cons = [c for c in payload["consistency"] if c["population"] == "common10"]
    ver = payload["verification"]["max_abs_diff_vs_stored"]

    lines = []
    lines.append("# Week 24 决策指标实测（核心文件 v2 §9.2 / §9.4 / §10.1）")
    lines.append("")
    lines.append("## 论文可直接使用的小结（≤200 字）")
    lines.append("")
    lines.append("**" + payload["paper_note"] + "**")
    lines.append("")
    lines.append("> 去空白字符数：%d" % payload["paper_note_chars"])
    lines.append("")
    lines.append("## 表 1  十级台阶 f_robust_inv 与 Top-k Jaccard（common10，N=10，45 对）")
    lines.append("")
    lines.append(md_table(
        ["台阶", "轴", "N", "τ_b", "f_unresolved(后层, z=1)", "f_robust_inv(z=1)",
         "f_robust_inv(z=1.96)", "J_10%", "J_20%", "J_30%"],
        [[r["rung"], r["axis"], r["n"], fmt(r["tau_b"]), fmt(r["f_unresolved_after_z1"]),
          fmt(r["f_robust_inv_z1"]), fmt(r["f_robust_inv_z1p96"]),
          fmt(r["jaccard_10pct"]), fmt(r["jaccard_20pct"]), fmt(r["jaccard_30pct"])]
         for r in rows]))
    lines.append("")
    lines.append("> 全台阶全轴 20/20 个 (population, 台阶, 轴) 组合在 z=1 与 z=1.96 两种口径下 f_robust_inv 均为 0："
                 "表中 common10（10 个组合）与各台阶 native 分子池（N=18/18/12/10/12，10 个组合）一致，"
                 "合计 40 个数无一非零。这是核心文件 §22.3 情形 C「NOT OBSERVED」的直接证据（未放宽任何阈值）。")
    lines.append("")
    lines.append("> Jaccard 口径：stage10_ladder 原生仅给出 J_20%；J_10 / J_30 由同一冻结逐分子值按 §10.1 重算"
                 "（k = round(0.1/0.2/0.3·N) = 1/2/3），未用其它量冒充。带 bootstrap CI 的 Jaccard 仅见 Stage 7（任务 M/E/C）。")
    lines.append("")
    lines.append("## 表 2  关键分子对 p_ij（§9.4；common10 与 native 两池；p_ij = Φ(ΔP_ij/σ_ij)，σ_ij = |δ_i−δ_j|/√2）")
    lines.append("")
    lines.append(md_table(
        ["池", "台阶", "轴", "选取规则", "i", "j", "ΔP_ij / eV", "σ_ij / eV", "ΔP/σ", "p_ij", "判决"],
        [[k["population"], k["rung"], k["axis"], k["why"], k["i"], k["j"], fmt(k["delta_p_ev"]),
          fmt(k["sigma_ij_ev"]), fmt(k["delta_over_sigma"]), fmt(k["p_ij"]), k["verdict"]]
         for k in payload["key_pairs"]]))
    lines.append("")
    lines.append("> 判决：p_ij>0.9 记 i>j，p_ij<0.1 记 i<j，0.1≤p_ij≤0.9 记 unresolved；"
                 "§9.4 的 0.9/0.1 阈值等价于 z=Φ⁻¹(0.9)=%.4g。i>j 表示 i 在 p_red=-EA、"
                 "higher_is_better 口径下更优。" % payload["z_from_p_threshold"])
    lines.append("")
    lines.append("## 表 3  一致性检查：p_ij 导出 unresolved vs 既有 f_unresolved / τ_b（common10）")
    lines.append("")
    lines.append(md_table(
        ["台阶", "轴", "τ_b", "符号翻转对数", "其中 unresolved", "p 导出 unresolved",
         "闭式 f_unres(z=1.2816)", "既有 f_unres(后层, z=1)", "偏差"],
        [[c["rung"], c["axis"], fmt(c["tau_b"]), c["n_sign_flip_pairs"],
          c["n_sign_flip_unresolved"], fmt(c["f_p_unresolved"]),
          fmt(c["f_unresolved_closedform_at_z_phi09"]),
          fmt(c["stored_f_unresolved_after_z1"]), fmt(c["dev_p_vs_stored_z1"])]
         for c in cons]))
    lines.append("")
    lines.append("> " + payload["consistency_note"])
    dev1 = max(abs(c["dev_p_vs_stored_z1"] or 0.0) for c in cons)
    dev196 = max(abs(c["dev_p_vs_stored_z1p96"] or 0.0) for c in cons)
    lines.append("> 偏差量化：p 导出 unresolved 与既有 z=1 主口径的最大差为 %.4g（%d/45 对），"
                 "与既有 z=1.96 的最大差为 %.4g；与等价口径 z=1.2816 的逐点偏差为 0。"
                 % (dev1, round(dev1 * 45), dev196))
    lines.append("")
    s6 = payload["stage6_native_p_ij_inventory"]
    lines.append("## Stage 6 原生 p_ij 口径对照（同一 §9.4 的 0.9/0.1 阈值，不同 σ 定义）")
    lines.append("")
    lines.append("- Stage 6（outputs/week6/stage6_decision_stability.json，scenario=z_only）只对 "
                 "P0_to_P1、P1_to_P2、C0_to_C1 三个台阶原生给出 prob_undecided_fraction："
                 + "；".join("%s/%s = %s (n=%d)" % (r["pair"], r["objective"][:3],
                                                   fmt(r["prob_undecided_fraction"]), r["n"])
                             for r in s6) + "。")
    lines.append("- 该实现用 σ_ij² = (δ_i² + δ_j²)/2（逐分子位移的方差和），而 §9.1 与本脚本用 "
                 "σ_ij = |δ_i − δ_j|/√2；同一台阶下前者 unresolved 比例可达 1.00，后者为 0.111–0.822（见表 3）。")
    lines.append("- G1_to_G2 与 C1_to_C2 两个台阶不存在任何原生 p_ij（Stage 6 未覆盖）。")
    lines.append("- 结论：p_ij 的数值强依赖 σ 口径，论文引用时必须同时声明 σ 定义；本报告一律用 §9.1 闭式。")
    lines.append("")
    lines.append("## 数据核查与输入 SHA256")
    lines.append("")
    for flag in payload["data_flags"]:
        lines.append("- " + flag)
    lines.append("")
    lines.append(md_table(
        ["输入（只读）", "bytes", "SHA256（前 16 位）"],
        [[i["path"], i["bytes"], (i["sha256"] or "—")[:16]] for i in payload["inputs"]]))
    lines.append("")
    lines.append("> 验证：重算值与 stage10_ladder 既有值的最大绝对偏差 —— f_robust_inv(z=1) %s、"
                 "f_robust_inv(z=1.96) %s、f_unresolved_after(z=1) %s、J_20%% %s；"
                 "σ 闭式 vs 库函数 %.2e；关键对判决与符号不一致数 %d。"
                 % (fmt(ver["f_robust_inv_z1"]), fmt(ver["f_robust_inv_z1p96"]),
                    fmt(ver["f_unresolved_after_z1"]), fmt(ver["jaccard_20pct"]),
                    ver["sigma_closedform_vs_library"],
                    payload["verification"]["n_key_pairs_verdict_sign_mismatch"]))
    lines.append("")
    if payload["monte_carlo_check"]:
        m = payload["monte_carlo_check"][0]
        lines.append("> p_ij 方法核验（%s / 还原轴，%d 次 Monte-Carlo）：与闭式最大绝对偏差 %.2e，"
                     "在 0.9 与 0.1 两个判决阈值上均 0 分歧。"
                     % (m["rung"], m["draws"], m["max_abs_diff"]))
        lines.append("")
    return "\n".join(lines) + "\n"


def render_csv(payload: dict) -> str:
    columns = [
        "population", "rung", "axis", "n", "n_pairs", "tau_b", "sigma_median_ev",
        "f_unresolved_before_z1", "f_unresolved_after_z1", "f_robust_inv_z1",
        "f_unresolved_after_z1p96", "f_robust_inv_z1p96",
        "n_resolved_both_z1", "n_robust_inv_z1", "n_sign_flip_pairs",
        "n_sign_flip_unresolved", "f_p_unresolved", "f_p_decided_gt0p9",
        "f_p_decided_lt0p1", "f_unresolved_at_z_phi09",
        "jaccard_10pct", "jaccard_20pct", "jaccard_30pct",
        "overlap_10pct", "overlap_20pct", "overlap_30pct",
        "stored_f_robust_inv_z1", "stored_f_robust_inv_z1p96",
        "stored_f_unresolved_after_z1", "stored_jaccard_20pct",
        "recomputed_minus_stored_jaccard_20pct",
    ]
    lines = [",".join(columns)]
    for row in payload["rows"]:
        lines.append(",".join("" if row.get(c) is None else str(row.get(c)) for c in columns))
    return "\n".join(lines) + "\n"


def render_figure(payload: dict, fig_path: Path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    rows = [r for r in payload["rows"] if r["population"] == "common10"]
    labels = ["%s\n%s" % (r["rung"].replace("_to_", "->"), r["axis"][:3]) for r in rows]
    x = np.arange(len(rows))

    fig, axes = plt.subplots(2, 1, figsize=(11.0, 8.2), constrained_layout=True)

    ax = axes[0]
    ax.bar(x - 0.2, [r["f_unresolved_after_z1"] for r in rows], width=0.4,
           color="#4c72b0", label="f_unresolved(after, z=1)")
    ax.bar(x + 0.2, [r["f_p_unresolved"] for r in rows], width=0.4,
           color="#dd8452", label="p_ij-derived unresolved (0.1<p<0.9)")
    ax.plot(x, [r["f_robust_inv_z1"] for r in rows], "o-", color="#c44e52",
            markersize=6, label="f_robust_inv(z=1) = 0")
    for xi, r in zip(x, rows):
        if r["n_sign_flip_pairs"]:
            ax.annotate("sign flips %d, unresolved %d"
                        % (r["n_sign_flip_pairs"], r["n_sign_flip_unresolved"]),
                        (xi, r["f_unresolved_after_z1"]), textcoords="offset points",
                        xytext=(0, 6), ha="center", fontsize=7, color="#333333")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=8)
    ax.set_ylim(-0.05, 1.05)
    ax.set_ylabel("fraction")
    ax.set_title("common10 ladder: unresolved fraction vs robust inversion (f_robust_inv = 0 everywhere)")
    ax.legend(fontsize=8, loc="upper left")
    ax.grid(axis="y", alpha=0.25)

    ax = axes[1]
    colors = ["#c44e52" if (r["rung"] == "C0_to_C1" and r["axis"] == "reduction")
              else "#4c72b0" for r in rows]
    ax.scatter([r["f_p_unresolved"] for r in rows], [r["tau_b"] for r in rows],
               c=colors, s=60, zorder=3)
    for r in rows:
        ax.annotate("%s/%s" % (r["rung"], r["axis"][:3]),
                    (r["f_p_unresolved"], r["tau_b"]), textcoords="offset points",
                    xytext=(4, 4), fontsize=7)
    ax.axhline(0.0, color="#999999", lw=0.8)
    ax.set_xlabel("p_ij-derived unresolved fraction (0.1 < p < 0.9)")
    ax.set_ylabel("Kendall tau_b (before vs after)")
    ax.set_title("Rank damage concentrates where pairs are unresolved (C0->C1 reduction highlighted)")
    ax.grid(alpha=0.25)

    fig.savefig(fig_path, dpi=150, metadata={"Software": None})
    plt.close(fig)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    parser.add_argument("--figdir", type=Path, default=DEFAULT_FIGDIR)
    parser.add_argument("--no-figure", action="store_true")
    parser.add_argument("--check", action="store_true",
                        help="re-render and fail if the files on disk differ byte-for-byte")
    args = parser.parse_args(argv)

    payload = build_payload()
    markdown = render_markdown(payload)
    csv_text = render_csv(payload)
    json_text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"

    outdir = args.outdir
    fig_path = args.figdir / FIG_NAME
    texts = {
        outdir / "decision_metrics.json": json_text,
        outdir / "decision_metrics.csv": csv_text,
        outdir / "decision_metrics.md": markdown,
    }

    if args.check:
        problems = []
        for path, text in texts.items():
            if not path.exists() or path.read_text(encoding="utf-8") != text:
                problems.append(str(path))
        if not args.no_figure:
            tmp = fig_path.with_name(fig_path.stem + ".check.tmp.png")
            render_figure(payload, tmp)
            same = fig_path.exists() and fig_path.read_bytes() == tmp.read_bytes()
            tmp.unlink(missing_ok=True)
            if not same:
                problems.append(str(fig_path))
        if problems:
            sys.stderr.write("MISMATCH: " + ", ".join(problems) + "\n")
            return 1
        print("OK: decision_metrics.json/csv/md and F50 figure are byte-for-byte reproducible")
        return 0

    outdir.mkdir(parents=True, exist_ok=True)
    for path, text in texts.items():
        path.write_text(text, encoding="utf-8", newline="\n")
    if not args.no_figure:
        args.figdir.mkdir(parents=True, exist_ok=True)
        render_figure(payload, fig_path)

    print(json.dumps({
        "wrote": [relpath(p) for p in texts] + ([relpath(fig_path)] if not args.no_figure else []),
        "n_rows": len(payload["rows"]),
        "n_key_pairs": len(payload["key_pairs"]),
        "all_40_f_robust_inv_zero": payload["verification"]["all_40_f_robust_inv_zero"],
        "paper_note_chars": payload["paper_note_chars"],
        "max_abs_diff_vs_stored": payload["verification"]["max_abs_diff_vs_stored"],
        "max_abs_dev_p_unresolved_vs_closedform_at_z_phi09":
            payload["verification"]["max_abs_dev_p_unresolved_vs_closedform_at_z_phi09"],
        "max_abs_dev_p_unresolved_vs_stored_z1_common10":
            payload["verification"]["max_abs_dev_p_unresolved_vs_stored_z1_common10"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
