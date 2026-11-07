#!/usr/bin/env python
"""Week 24 -- leave-one-rung-out (LORO) prospective check of the sigma criterion.

Background
----------
``outputs/week10/stage11_sigma_anatomy.json`` proves a family of *identities*:
``sigma_ij = |delta_i - delta_j| / sqrt(2)``, so the whole resolved / unresolved
machine collapses to one dimensionless number ``q_ij = |delta_i - delta_j| /
|DeltaP_ij|`` compared against ``sqrt(2)/z``.  An identity has zero fit error by
construction, so reproducing it is not evidence of anything.  ``outputs/week21``
ran a *molecule-level* hold-out; the external review asked for the complementary
**rung-level** leave-one-rung-out test: fit the "shift distribution -> decision
damage" mapping on nine of the ten (physical rung x axis) points and predict the
tenth *before* looking at it.

Degradation, stated up front
----------------------------
A pair-level LORO ("which molecule pairs are unresolvable on the held-out rung?")
is **not** possible from the frozen data: the *identity* of the unresolved pairs
barely transfers between rungs (pairwise Jaccard of the unresolved sets: median
0.00, maximum 0.33), because being unresolved is a property of the rung, not of
the molecule pair.  This script therefore runs the closest honest version --
rung-level LORO of the aggregate decision quantities (Kendall ``tau_b`` and
``f_unresolved``) -- and *measures* the failed pair-level transfer, so the
degradation is documented instead of hidden.

Honest boundary
---------------
The LORO here is **within-family interpolation**: the ten points are
(5 physical rungs) x (2 axes) measured on ONE shared ten-molecule set, so the
points are not independent and nine of them are always in the training set.  The
predictor (shift dispersion, or the shift's slope on the target layer) is itself
a rung diagnostic that requires the expensive layer, so this is *not* a free
screen; what it tests is whether the discreteness -> damage relation transfers
across rungs.

No new electronic-structure calculation is run.  Every input file is hashed.

Outputs
-------
outputs/week24_corealign/loro.json
outputs/week24_corealign/loro.md
outputs/week24_corealign/loro_folds.csv

Run again with ``--check`` to prove byte-for-byte reproducibility.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import json
import math
import random
import statistics
import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from electrolyte_ranking import ranking  # noqa: E402

ANATOMY_JSON = REPO_ROOT / "outputs" / "week10" / "stage11_sigma_anatomy.json"
LADDER_CSV = REPO_ROOT / "outputs" / "week9" / "stage10_ladder.csv"
DEFAULT_OUTDIR = REPO_ROOT / "outputs" / "week24_corealign"

Z_PRIMARY = 1.0
CRITICAL_Q = math.sqrt(2.0) / Z_PRIMARY

#: pre-registered hit tolerance on the held-out rung.  tau_b and f_unresolved are
#: both O(1) numbers on a 45-pair rung; 0.10 is the tolerance the review asked for
#: on tau_b and is used for f as well (= 4.5 pairs out of 45).
TOL = 0.10
TOL_SENSITIVITY = (0.05, 0.15)

FOLD_PERMUTATION_SEED = 20261002

PREDICTORS = (
    ("dispersion_std", "std_delta_ev", "位移离散度 std(delta) [eV]"),
    ("abs_slope", "abs_slope_ev", "位移对目标层的割线斜率 |b| [eV]"),
    ("signed_slope", "signed_slope_ev", "带符号割线斜率 b [eV]"),
)

TARGETS = (
    ("tau_b", "kendall_tau_b", "Kendall tau_b（排序保真度）"),
    ("f_unresolved", "f_unresolved_observed", "未解析对比例 f_unresolved(z=1)"),
)

SPECS = ("linear", "log", "theil")
PRIMARY_SPEC = "linear"
#: log needs a strictly positive predictor, so the signed slope gets linear+robust only.
SPECS_BY_PREDICTOR = {
    "dispersion_std": SPECS,
    "abs_slope": SPECS,
    "signed_slope": ("linear", "theil"),
}


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def relpath(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def fmt(value, digits=4):
    if value is None:
        return "-"
    return ("%%.%dg" % digits) % value


def theil_sen(x, y):
    """Median-of-pairwise-slopes robust line (no SciPy dependency)."""
    slopes = []
    for i in range(len(x)):
        for j in range(i + 1, len(x)):
            if x[j] != x[i]:
                slopes.append((y[j] - y[i]) / (x[j] - x[i]))
    slope = statistics.median(slopes)
    intercept = statistics.median([y[i] - slope * x[i] for i in range(len(x))])
    return float(slope), float(intercept)


def fit_predict(xs, ys, x0, spec):
    """Fit ``y = a + b * f(x)`` on the training folds and predict at ``x0``."""
    x = np.asarray(xs, dtype=float)
    y = np.asarray(ys, dtype=float)
    if spec == "linear":
        slope, intercept = np.polyfit(x, y, 1)
        pred = intercept + slope * x0
    elif spec == "log":
        slope, intercept = np.polyfit(np.log(x), y, 1)
        pred = intercept + slope * math.log(x0)
    elif spec == "theil":
        slope, intercept = theil_sen(list(x), list(y))
        pred = intercept + slope * x0
    else:  # pragma: no cover - guarded by SPECS
        raise ValueError(f"unknown spec: {spec}")
    return float(pred), float(slope), float(intercept)

def load_points():
    """The ten (physical rung x axis) points, on the aligned common-10 subset."""
    payload = json.loads(ANATOMY_JSON.read_text(encoding="utf-8"))
    pair_detail = payload["pair_detail"]
    points = []
    for row in payload["rows"]:
        key = "%s|%s" % (row["rung"], row["axis"])
        detail = pair_detail[key]
        n_unresolved = sum(1 for q in detail["q_ij"] if q > CRITICAL_Q)
        points.append({
            "label": key,
            "rung": row["rung"],
            "axis": row["axis"],
            "n_molecules": row["n"],
            "std_delta_ev": float(row["delta_sd_ev"]),
            "abs_slope_ev": abs(float(row["ols_slope_b"])),
            "signed_slope_ev": float(row["ols_slope_b"]),
            "kendall_tau_b": float(row["kendall_tau_b"]),
            "f_unresolved_observed": float(row["f_unresolved_p1_observed"]),
            "f_unresolved_closedform": float(row["f_unresolved_p1_closedform"]),
            "shortlist_rewritten": bool(row["shortlist_rewritten"]),
            "n_pairs": len(detail["q_ij"]),
            "n_unresolved_pairs": n_unresolved,
            "overlap_20": float(row["overlap_20"]),
        })
    return points, payload


def rung_level_loro(xs, ys, spec):
    """Hold out each rung in turn; return one record per fold."""
    n = len(xs)
    folds = []
    for k in range(n):
        train = [i for i in range(n) if i != k]
        pred, slope, intercept = fit_predict(
            [xs[i] for i in train], [ys[i] for i in train], xs[k], spec
        )
        train_median = statistics.median([ys[i] for i in train])
        folds.append({
            "held_out": k,
            "x_value": float(xs[k]),
            "y_observed": float(ys[k]),
            "y_predicted": float(pred),
            "abs_err": abs(pred - ys[k]),
            "hit": bool(abs(pred - ys[k]) <= TOL),
            "train_median": float(train_median),
            "predicted_side": ("above" if pred > train_median
                               else "below" if pred < train_median else "tie"),
            "observed_side": ("above" if ys[k] > train_median
                              else "below" if ys[k] < train_median else "tie"),
            "direction_hit": bool((pred - train_median) * (ys[k] - train_median) > 0),
            "train_slope": slope,
            "train_intercept": intercept,
        })
    return folds


def summarize_folds(folds, ys):
    predicted = [f["y_predicted"] for f in folds]
    observed = [f["y_observed"] for f in folds]
    err = np.abs(np.asarray(predicted) - np.asarray(observed))
    out = {
        "n_folds": len(folds),
        "mae": float(err.mean()),
        "rmse": float(math.sqrt(float((err ** 2).mean()))),
        "max_abs_err": float(err.max()),
        "hits_tol_%.2f" % TOL: int((err <= TOL).sum()),
        "hit_rate_tol_%.2f" % TOL: float((err <= TOL).mean()),
        "direction_hits": int(sum(1 for f in folds if f["direction_hit"])),
        "direction_rate": float(sum(1 for f in folds if f["direction_hit"]) / len(folds)),
        "kendall_pred_vs_observed": float(ranking.kendall_tau_b(predicted, observed)),
        "spearman_pred_vs_observed": float(ranking.spearman_rho(predicted, observed)),
        "pearson_r2_pred_vs_observed": float(np.corrcoef(predicted, observed)[0, 1] ** 2),
    }
    for tol in TOL_SENSITIVITY:
        out["hits_tol_%.2f" % tol] = int((err <= tol).sum())
    out["abs_err_per_fold"] = [float(v) for v in err]
    return out


def naive_ordinal(xs, ys, higher_x_means_worse):
    """Parameter-free rule: larger dispersion -> worse ranking / more unresolved."""
    n = len(xs)
    folds = []
    for k in range(n):
        train = [i for i in range(n) if i != k]
        x_median = statistics.median([xs[i] for i in train])
        y_median = statistics.median([ys[i] for i in train])
        x_high = xs[k] > x_median
        predicted_damaged = x_high
        observed_damaged = (ys[k] < y_median) if higher_x_means_worse else (ys[k] > y_median)
        folds.append({
            "held_out": k,
            "x_value": float(xs[k]),
            "x_train_median": float(x_median),
            "y_train_median": float(y_median),
            "y_observed": float(ys[k]),
            "predicted_damaged": bool(predicted_damaged),
            "observed_damaged": bool(observed_damaged),
            "hit": bool(predicted_damaged == observed_damaged),
        })
    return folds


def naive_constant(xs, ys):
    """Value-task null: predict the training mean for every held-out rung."""
    n = len(xs)
    err = []
    for k in range(n):
        train = [i for i in range(n) if i != k]
        pred = statistics.fmean([ys[i] for i in train])
        err.append(abs(pred - ys[k]))
    err = np.asarray(err)
    return {
        "mae": float(err.mean()),
        "rmse": float(math.sqrt(float((err ** 2).mean()))),
        "max_abs_err": float(err.max()),
        "abs_err_per_fold": [float(v) for v in err],
    }

def leave_two_out(xs, ys, spec=PRIMARY_SPEC):
    n = len(xs)
    err = []
    for k1, k2 in itertools.combinations(range(n), 2):
        train = [i for i in range(n) if i not in (k1, k2)]
        for k in (k1, k2):
            pred, _, _ = fit_predict(
                [xs[i] for i in train], [ys[i] for i in train], xs[k], spec
            )
            err.append(abs(pred - ys[k]))
    err = np.asarray(err)
    return {
        "n_held_out_evaluations": int(err.size),
        "mae": float(err.mean()),
        "median_abs_err": float(np.median(err)),
        "p90_abs_err": float(np.quantile(err, 0.9)),
    }


def fold_order_invariance(xs, ys, spec=PRIMARY_SPEC):
    """LORO must be invariant to the order the rungs are visited in."""
    n = len(xs)
    baseline = [f["y_predicted"] for f in rung_level_loro(xs, ys, spec)]
    order = list(range(n))
    random.Random(FOLD_PERMUTATION_SEED).shuffle(order)
    permuted = []
    for pos, k in enumerate(order):
        train = [order[p] for p in range(n) if p != pos]
        pred, _, _ = fit_predict(
            [xs[i] for i in train], [ys[i] for i in train], xs[k], spec
        )
        permuted.append((k, pred))
    permuted.sort()
    max_diff = max(abs(p - b) for (_, p), b in zip(permuted, baseline))
    return {
        "n_folds": n,
        "seed": FOLD_PERMUTATION_SEED,
        "max_abs_diff_vs_sorted_order": float(max_diff),
        "invariant": bool(max_diff < 1e-12),
    }


def loo_correlation_stability(xs, ys, labels):
    """How fragile is the reported Spearman rho to dropping a single rung?"""
    full = float(ranking.spearman_rho(xs, ys))
    values = []
    for k in range(len(xs)):
        train = [i for i in range(len(xs)) if i != k]
        values.append((labels[k], float(ranking.spearman_rho(
            [xs[i] for i in train], [ys[i] for i in train]))))
    numbers = [v for _, v in values]
    most_influential = max(values, key=lambda item: abs(item[1] - full))
    return {
        "full_sample": full,
        "drop_min": float(min(numbers)),
        "drop_median": float(statistics.median(numbers)),
        "drop_max": float(max(numbers)),
        "most_influential_drop": most_influential[0],
        "most_influential_value": most_influential[1],
    }


def pair_level_transfer(points, anatomy):
    """Measure how badly the *identity* of the unresolved pairs transfers."""
    detail = anatomy["pair_detail"]
    labels = list(detail[points[0]["label"]]["pair_labels"])
    sets = {}
    for point in points:
        data = detail[point["label"]]
        sets[point["label"]] = {
            label for label, q in zip(data["pair_labels"], data["q_ij"])
            if q > CRITICAL_Q
        }
    jaccards = []
    for a, b in itertools.combinations(points, 2):
        sa, sb = sets[a["label"]], sets[b["label"]]
        union = sa | sb
        jaccards.append((a["label"], b["label"],
                         len(sa & sb) / len(union) if union else 0.0))
    values = [j for _, _, j in jaccards]
    return {
        "n_molecule_pairs": len(labels),
        "n_rung_pairings": len(jaccards),
        "jaccard_median": float(statistics.median(values)),
        "jaccard_mean": float(statistics.fmean(values)),
        "jaccard_max": float(max(values)),
        "n_zero_overlap_pairings": int(sum(1 for v in values if v == 0.0)),
        "max_pairing": list(max(jaccards, key=lambda item: item[2])[:2]),
        "per_rung_unresolved_counts": {
            p["label"]: len(sets[p["label"]]) for p in points
        },
    }


def cross_check_week9(points):
    """The anatomy rows must reproduce the frozen week9 ladder on common10."""
    with LADDER_CSV.open(encoding="utf-8", newline="") as handle:
        rows = [r for r in csv.DictReader(handle) if r["population"] == "common10"]
    index = {(r["rung"], r["axis"]): r for r in rows}
    diffs = {"std": [], "tau_b": [], "f_unresolved": []}
    for point in points:
        ref = index[(point["rung"], point["axis"])]
        diffs["std"].append(abs(float(ref["shift_std_ev"]) - point["std_delta_ev"]))
        diffs["tau_b"].append(abs(float(ref["kendall_tau_b"]) - point["kendall_tau_b"]))
        diffs["f_unresolved"].append(abs(float(ref["f_unresolved_after"])
                                         - point["f_unresolved_observed"]))
    worst = max(max(v) for v in diffs.values())
    return {
        "n_points_checked": len(points),
        "max_abs_diff_std_ev": float(max(diffs["std"])),
        "max_abs_diff_tau_b": float(max(diffs["tau_b"])),
        "max_abs_diff_f_unresolved": float(max(diffs["f_unresolved"])),
        "ok": bool(worst < 1e-9),
    }

def build_payload():
    points, anatomy = load_points()
    labels = [p["label"] for p in points]

    vectors = {name: [p[column] for p in points] for name, column, _ in PREDICTORS}
    targets = {name: [p[column] for p in points] for name, column, _ in TARGETS}

    folds = {}
    summaries = {}
    for pred_name, _, _ in PREDICTORS:
        for target_name, _, _ in TARGETS:
            for spec in SPECS_BY_PREDICTOR[pred_name]:
                key = "%s|%s|%s" % (pred_name, target_name, spec)
                records = rung_level_loro(vectors[pred_name], targets[target_name], spec)
                folds[key] = records
                summaries[key] = summarize_folds(records, targets[target_name])

    primary = {}
    for pred_name, _, _ in PREDICTORS:
        for target_name, _, _ in TARGETS:
            key = "%s|%s|%s" % (pred_name, target_name, PRIMARY_SPEC)
            primary["%s|%s" % (pred_name, target_name)] = summaries[key]

    naive = {
        "tau_b": {
            "rule": "std(delta) 高于训练折中位数 => 预测该台阶 tau_b 低于训练折中位数",
            "folds": naive_ordinal(vectors["dispersion_std"], targets["tau_b"], True),
        },
        "f_unresolved": {
            "rule": "std(delta) 高于训练折中位数 => 预测该台阶 f_unresolved 高于训练折中位数",
            "folds": naive_ordinal(vectors["dispersion_std"], targets["f_unresolved"], False),
        },
        "constant_tau_b": naive_constant(vectors["dispersion_std"], targets["tau_b"]),
        "constant_f_unresolved": naive_constant(vectors["dispersion_std"], targets["f_unresolved"]),
    }
    for name in ("tau_b", "f_unresolved"):
        hits = sum(1 for f in naive[name]["folds"] if f["hit"])
        naive[name]["hits"] = hits
        naive[name]["hit_rate"] = hits / len(naive[name]["folds"])

    paired = {}
    for target_name in ("tau_b", "f_unresolved"):
        loro_folds = folds["dispersion_std|%s|%s" % (target_name, PRIMARY_SPEC)]
        naive_folds = naive[target_name]["folds"]
        both = only_loro = only_naive = neither = 0
        disagreement = []
        for lf, nf in zip(loro_folds, naive_folds):
            l_hit, n_hit = lf["direction_hit"], nf["hit"]
            if l_hit and n_hit:
                both += 1
            elif l_hit and not n_hit:
                only_loro += 1
            elif n_hit and not l_hit:
                only_naive += 1
            else:
                neither += 1
            if l_hit != n_hit:
                disagreement.append(lf["held_out"])
        paired[target_name] = {
            "task": "把台阶分到训练折中位数的哪一侧（序数/决策任务）",
            "loro_direction_hits": sum(1 for f in loro_folds if f["direction_hit"]),
            "naive_hits": naive[target_name]["hits"],
            "n_folds": len(loro_folds),
            "both": both, "only_loro": only_loro,
            "only_naive": only_naive, "neither": neither,
            "disagree_fold_indices": disagreement,
            "disagree_fold_labels": [labels[i] for i in disagreement],
        }

    value_task = {}
    for target_name in ("tau_b", "f_unresolved"):
        loro_mae = summaries["dispersion_std|%s|%s" % (target_name, PRIMARY_SPEC)]["mae"]
        const_mae = naive["constant_%s" % target_name]["mae"]
        value_task[target_name] = {
            "task": "预测台阶决策量的数值（值任务）",
            "loro_mae": loro_mae,
            "naive_constant_mae": const_mae,
            "mae_delta_loro_minus_naive": loro_mae - const_mae,
            "loro_better": bool(loro_mae < const_mae),
        }

    loo_corr = {}
    l2o = {}
    invar = {}
    for pred_name, _, _ in PREDICTORS:
        for target_name, _, _ in TARGETS:
            key = "%s|%s" % (pred_name, target_name)
            loo_corr[key] = loo_correlation_stability(
                vectors[pred_name], targets[target_name], labels)
            l2o[key] = leave_two_out(vectors[pred_name], targets[target_name])
            invar[key] = fold_order_invariance(vectors[pred_name], targets[target_name])

    physical_rungs = sorted({p["rung"] for p in points})
    return {
        "stage": "W24-LORO",
        "convention": "delta = 目标层 - 廉价层；sigma_ij = |delta_i - delta_j|/sqrt(2)；"
                      "unresolved <=> q_ij > sqrt(2)/z",
        "critical_q_z1": CRITICAL_Q,
        "hit_tolerance": TOL,
        "hit_tolerance_sensitivity": list(TOL_SENSITIVITY),
        "primary_spec": PRIMARY_SPEC,
        "points": points,
        "folds": folds,
        "summary": summaries,
        "primary_summary": primary,
        "naive": naive,
        "paired": paired,
        "value_task": value_task,
        "loo_correlation_stability": loo_corr,
        "leave_two_out": l2o,
        "fold_order_invariance": invar,
        "pair_level_transfer": pair_level_transfer(points, anatomy),
        "non_independence": {
            "n_points": len(points),
            "n_physical_rungs": len(physical_rungs),
            "physical_rungs": physical_rungs,
            "n_axes": 2,
            "shared_molecule_set_size": points[0]["n_molecules"],
            "statement": "10 个点 = 5 个物理台阶 × 2 条轴，且全部落在同一 10 分子公共子集上；"
                         "同一台阶的两条轴共享分子、相邻台阶共享分子，因此 10 个点不独立，"
                         "有效样本量小于 10，所有统计均为描述性而非推断性。",
        },
        "honesty": {
            "within_family_interpolation": "留出的台阶与训练台阶同属一个台阶族、同一分子集，"
                                           "9 个训练点始终覆盖留出点邻域，这是族内插值而不是盲测。",
            "predictor_is_not_free": "std(delta) 与割线斜率 b 都需要目标层的数值才能算出，"
                                     "因此 LORO 检验的是『离散度→决策损伤』关系能否跨台阶迁移，"
                                     "而不是无需目标层即可预测。",
            "pair_level_impossible": "未解析对的『身份』几乎不跨台阶传递（Jaccard 中位 0.00，最大 0.33），"
                                     "故逐对前瞻在本数据上不可行，已退化为台阶级 LORO。",
            "identities_are_not_evidence": "闭式 sigma 恒等式是代数恒等式，其零误差不构成证据；"
                                           "本脚本度量的是映射的跨台阶迁移能力。",
        },
        "cross_check_week9": cross_check_week9(points),
        "inputs": {
            relpath(ANATOMY_JSON): sha256_of(ANATOMY_JSON),
            relpath(LADDER_CSV): sha256_of(LADDER_CSV),
        },
    }

def md_table(headers, rows):
    out = ["| " + " | ".join(str(h).replace("|", "\\|") for h in headers) + " |",
           "| " + " | ".join("---" for _ in headers) + " |"]
    for row in rows:
        out.append("| " + " | ".join(str(c).replace("|", "\\|") for c in row) + " |")
    return "\n".join(out)


def render_markdown(payload):
    points = payload["points"]
    labels = [p["label"] for p in points]
    primary = payload["primary_summary"]
    lines = []
    add = lines.append

    add("# Week 24 — 留一台阶（LORO）前瞻性检验：闭式分辨率判据")
    add("")
    add("**一句话结论：** 位移离散度 → 未解析比例的映射在台阶级留一中稳定迁移"
        "（|b| 预测 f_unresolved 的 MAE = %s，预测-实测 R² = %s）；"
        "但离散度 → tau_b 的**数值**映射在留一台阶下崩溃（MAE = %s，命中 %d/10），"
        "其稳健内容只剩序数方向（朴素规则即可 %d/10 命中）。"
        "即论文 rho = -0.851 的故事在**排序方向**上成立、在**数值预测**上不成立。"
        % (fmt(primary["abs_slope|f_unresolved"]["mae"]),
           fmt(primary["abs_slope|f_unresolved"]["pearson_r2_pred_vs_observed"]),
           fmt(primary["dispersion_std|tau_b"]["mae"]),
           primary["dispersion_std|tau_b"]["hits_tol_0.10"],
           payload["naive"]["tau_b"]["hits"]))
    add("")
    add("> 口径：10 点 = 5 个物理台阶 × 氧化/还原两轴，全部落在同一 10 分子公共子集（N=10）。"
        "命中容差 %.2f；std 为位移离散度，|b| 为位移对目标层的割线斜率绝对值。" % payload["hit_tolerance"])
    add("")

    add("## 1  口径、退化与诚实边界")
    add("")
    add("Stage 11 的 sigma 恒等式（sigma_ij = |delta_i - delta_j| / sqrt(2)）是**代数恒等式**，"
        "其零拟合误差不构成证据。本脚本做评审要求的前瞻性补强：**留一台阶**——"
        "用其余 9 个台阶拟合「位移分布 → 决策损伤」映射，事前预测第 10 个台阶，再对照实测。")
    add("")
    pl = payload["pair_level_transfer"]
    add("- **退化原因（已实测）**：逐对前瞻（预测哪些分子对不可分辨）在本数据上不可行——"
        "未解析对的**身份**跨台阶几乎不传递，%d 组台阶两两 Jaccard 中位 %s、最大 %s、"
        "完全无重叠 %d 组。故退化为台阶级 LORO。"
        % (pl["n_rung_pairings"], fmt(pl["jaccard_median"]), fmt(pl["jaccard_max"]),
           pl["n_zero_overlap_pairings"]))
    add("- **这是族内插值，不是盲测**：%s" % payload["honesty"]["within_family_interpolation"])
    add("- **预测子不是免费的**：%s" % payload["honesty"]["predictor_is_not_free"])
    add("- **点不独立**：%s" % payload["non_independence"]["statement"])
    add("")

    add("## 2  十个台阶（common10, N=10）")
    add("")
    add(md_table(
        ["台阶|轴", "std(delta) [eV]", "|b| [eV]", "tau_b", "f_unres(z=1)", "未解析对/45", "改写短名单"],
        [[p["label"], fmt(p["std_delta_ev"]), fmt(p["abs_slope_ev"]),
          fmt(p["kendall_tau_b"]), fmt(p["f_unresolved_observed"]),
          p["n_unresolved_pairs"], "是" if p["shortlist_rewritten"] else "否"]
         for p in points]))
    add("")

    add("## 3  主结果：台阶级 LORO 的逐折预测（线性规格）")
    add("")
    section = 0
    for pred_name, _, pred_label in PREDICTORS:
        for target_name, _, target_label in TARGETS:
            section += 1
            key = "%s|%s" % (pred_name, target_name)
            folds = payload["folds"]["%s|%s" % (key, payload["primary_spec"])]
            sm = payload["summary"]["%s|%s" % (key, payload["primary_spec"])]
            add("### 3.%d  %s -> %s（MAE=%s，命中@%.2f %d/10，方向命中 %d/10）"
                % (section, pred_label, target_label, fmt(sm["mae"]),
                   payload["hit_tolerance"], sm["hits_tol_0.10"], sm["direction_hits"]))
            add("")
            add(md_table(
                ["留出台阶", "预测子 x", "实测 y", "预测 yhat", "|误差|", "命中", "方向命中"],
                [[labels[f["held_out"]], fmt(f["x_value"]), fmt(f["y_observed"]),
                  fmt(f["y_predicted"]), fmt(f["abs_err"]),
                  "OK" if f["hit"] else "MISS", "OK" if f["direction_hit"] else "MISS"]
                 for f in folds]))
            add("")

    add("## 4  汇总指标（线性 / log / Theil-Sen 三种规格）")
    add("")
    rows = []
    for pred_name, _, _ in PREDICTORS:
        for target_name, _, _ in TARGETS:
            for spec in SPECS_BY_PREDICTOR[pred_name]:
                sm = payload["summary"]["%s|%s|%s" % (pred_name, target_name, spec)]
                rows.append([pred_name, target_name, spec, fmt(sm["mae"]),
                             "%d/10" % sm["hits_tol_0.10"],
                             "%d/10" % sm["direction_hits"],
                             fmt(sm["kendall_pred_vs_observed"]),
                             fmt(sm["spearman_pred_vs_observed"]),
                             fmt(sm["pearson_r2_pred_vs_observed"])])
    add(md_table(["预测子", "目标", "规格", "MAE", "命中@0.10", "方向命中",
                  "Kendall(yhat,y)", "Spearman(yhat,y)", "R2"], rows))
    add("")
    add("读法：std -> tau_b 的三种规格 MAE 都在 0.32-0.48（线性规格最大，命中仅 %d/10），"
        "因为 std 跨 0.05-2.25 eV（44 倍），把线性/对数模型外推到留出的极端台阶即失效，"
        "且最大误差都落在同两个杠杆点（P0_to_P1|reduction、C0_to_C1|reduction）；"
        "|b| -> f_unresolved 的三种规格都好（线性 MAE %s、R2 %s）。"
        % (primary["dispersion_std|tau_b"]["hits_tol_0.10"],
           fmt(primary["abs_slope|f_unresolved"]["mae"]),
           fmt(primary["abs_slope|f_unresolved"]["pearson_r2_pred_vs_observed"])))
    add("")

    add("## 5  与朴素规则的配对比较（同一留出方案）")
    add("")
    add("### 5.1 值任务：预测台阶决策量的数值")
    add("")
    add(md_table(
        ["目标", "LORO(std) MAE", "朴素(训练均值) MAE", "Delta(LORO-朴素)", "LORO 更优?"],
        [[t, fmt(payload["value_task"][t]["loro_mae"]),
          fmt(payload["value_task"][t]["naive_constant_mae"]),
          "%+.3f" % payload["value_task"][t]["mae_delta_loro_minus_naive"],
          "是" if payload["value_task"][t]["loro_better"] else "否"]
         for t in ("tau_b", "f_unresolved")]))
    add("")
    add("### 5.2 序数/决策任务：把台阶分到训练折中位数的哪一侧")
    add("")
    add(md_table(
        ["目标", "LORO(std) 方向命中", "朴素规则命中", "两者都对", "仅 LORO 对",
         "仅朴素对", "都不对", "分歧台阶"],
        [[t, "%d/10" % payload["paired"][t]["loro_direction_hits"],
          "%d/10" % payload["paired"][t]["naive_hits"],
          payload["paired"][t]["both"], payload["paired"][t]["only_loro"],
          payload["paired"][t]["only_naive"], payload["paired"][t]["neither"],
          ", ".join(payload["paired"][t]["disagree_fold_labels"]) or "—"]
         for t in ("tau_b", "f_unresolved")]))
    add("")
    add("关键对照：**tau_b 方向上，朴素规则（std 大 => 排序差）10/10 命中，"
        "而 LORO 线性回归只有 5/10**——即『离散度越大排序越差』这条论文口径在**序数层面**"
        "完全站得住，但把它当成**数值模型**去外推就不成立。"
        "f_unresolved 上两者接近（LORO 9/10 vs 朴素 8/10）。")
    add("")

    add("## 6  敏感性")
    add("")
    add("### 6.1 留一台阶的散点相关稳定性（丢弃任一台阶后的 Spearman）")
    add("")
    add(md_table(
        ["预测子~目标", "全样本 rho", "丢 1 点后 min", "median", "max", "影响最大的丢弃点"],
        [[k, fmt(v["full_sample"]), fmt(v["drop_min"]), fmt(v["drop_median"]),
          fmt(v["drop_max"]), v["most_influential_drop"]]
         for k, v in payload["loo_correlation_stability"].items()]))
    add("")
    add("std~tau_b 丢任一点后 rho 仍在 [-0.91, -0.80]，说明**相关本身不脆弱**；"
        "脆弱的是把它当作跨台阶的**数值**预测（见 §4、§5.2）——两者必须分开陈述。")
    add("")
    add("### 6.2 留二台阶（每次留出 2 个，共 45 组 x 2 = 90 次评估）")
    add("")
    add(md_table(
        ["预测子->目标", "MAE", "中位|误差|", "p90|误差|"],
        [[k, fmt(v["mae"]), fmt(v["median_abs_err"]), fmt(v["p90_abs_err"])]
         for k, v in payload["leave_two_out"].items()]))
    add("")
    add("### 6.3 折叠顺序不变性")
    add("")
    add("随机化台阶访问顺序（固定种子 %d）后，LORO 预测与排序遍历**逐点相同**"
        "（最大差 %s），故结果不依赖折叠顺序。"
        % (FOLD_PERMUTATION_SEED,
           fmt(max(v["max_abs_diff_vs_sorted_order"]
                   for v in payload["fold_order_invariance"].values()))))
    add("")

    add("## 7  为什么不能做逐对前瞻（退化依据）")
    add("")
    add("把每个台阶在 z=1 下判为未解析的分子对取集合，再两两求 Jaccard：")
    add("")
    add(md_table(
        ["台阶两两组合数", "Jaccard 中位", "Jaccard 均值", "Jaccard 最大", "零重叠组合数", "最大重叠组合"],
        [[pl["n_rung_pairings"], fmt(pl["jaccard_median"]), fmt(pl["jaccard_mean"]),
          fmt(pl["jaccard_max"]), pl["n_zero_overlap_pairings"],
          " vs ".join(pl["max_pairing"])]]))
    add("")
    add("未解析对的集合几乎不跨台阶共享 ⇒ 『哪些对不可分辨』是**台阶属性**而非**分子对属性**，"
        "在没有目标层数值的前提下无法逐对前置预测。这是退化为台阶级 LORO 的实测依据，"
        "也是论文不应声称『可在花钱之前预判具体哪些分子对不可分辨』的证据边界。")
    add("")

    add("## 8  交叉核对")
    add("")
    cc = payload["cross_check_week9"]
    add("本脚本 10 点全部取自 Stage 11 解剖文件，并与冻结的 week9 台阶表（common10）逐点核对："
        "std 最大差 %s、tau_b 最大差 %s、f_unresolved 最大差 %s（%s）。"
        % (fmt(cc["max_abs_diff_std_ev"]), fmt(cc["max_abs_diff_tau_b"]),
           fmt(cc["max_abs_diff_f_unresolved"]), "一致" if cc["ok"] else "不一致"))
    add("")

    add("## 9  复现")
    add("")
    add("```")
    add("python scripts/analyze_w24_loro.py           # 生成 loro.json / loro.md / loro_folds.csv")
    add("python scripts/analyze_w24_loro.py --check   # 逐字节校验可复现")
    add("```")
    add("")
    add("输入哈希：")
    add("")
    add(md_table(["文件", "SHA256"], [[k, v] for k, v in payload["inputs"].items()]))
    add("")
    return "\n".join(lines) + "\n"

def render_csv(payload):
    header = ["predictor", "target", "spec", "held_out_label", "rung", "axis",
              "x_value", "y_observed", "y_predicted", "abs_err", "hit", "direction_hit"]
    lines = [",".join(header)]
    index = {p["label"]: p for p in payload["points"]}
    for pred_name, _, _ in PREDICTORS:
        for target_name, _, _ in TARGETS:
            for spec in SPECS_BY_PREDICTOR[pred_name]:
                for fold in payload["folds"]["%s|%s|%s" % (pred_name, target_name, spec)]:
                    label = payload["points"][fold["held_out"]]["label"]
                    point = index[label]
                    lines.append(",".join([
                        pred_name, target_name, spec, label,
                        point["rung"], point["axis"],
                        "%.10g" % fold["x_value"],
                        "%.10g" % fold["y_observed"],
                        "%.10g" % fold["y_predicted"],
                        "%.10g" % fold["abs_err"],
                        "1" if fold["hit"] else "0",
                        "1" if fold["direction_hit"] else "0",
                    ]))
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    parser.add_argument("--check", action="store_true",
                        help="re-render and fail if the files on disk differ byte-for-byte")
    args = parser.parse_args(argv)

    payload = build_payload()
    markdown = render_markdown(payload)
    csv_text = render_csv(payload)
    json_text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"

    texts = {
        args.outdir / "loro.json": json_text,
        args.outdir / "loro.md": markdown,
        args.outdir / "loro_folds.csv": csv_text,
    }

    if args.check:
        problems = [str(path) for path, text in texts.items()
                    if not path.exists() or path.read_text(encoding="utf-8") != text]
        if problems:
            sys.stderr.write("MISMATCH: " + ", ".join(problems) + "\n")
            return 1
        print("OK: loro.json / loro.md / loro_folds.csv are byte-for-byte reproducible")
        return 0

    args.outdir.mkdir(parents=True, exist_ok=True)
    for path, text in texts.items():
        path.write_text(text, encoding="utf-8", newline="\n")

    primary = payload["primary_summary"]
    print(json.dumps({
        "wrote": [relpath(p) for p in texts],
        "n_points": len(payload["points"]),
        "dispersion_std_to_tau_b_mae": primary["dispersion_std|tau_b"]["mae"],
        "dispersion_std_to_tau_b_hits": primary["dispersion_std|tau_b"]["hits_tol_0.10"],
        "dispersion_std_to_tau_b_dir_hits": primary["dispersion_std|tau_b"]["direction_hits"],
        "abs_slope_to_f_unresolved_mae": primary["abs_slope|f_unresolved"]["mae"],
        "abs_slope_to_f_unresolved_r2": primary["abs_slope|f_unresolved"]["pearson_r2_pred_vs_observed"],
        "naive_tau_b_hits": payload["naive"]["tau_b"]["hits"],
        "loro_tau_b_direction_hits": payload["paired"]["tau_b"]["loro_direction_hits"],
        "pair_level_jaccard_median": payload["pair_level_transfer"]["jaccard_median"],
        "cross_check_week9_ok": payload["cross_check_week9"]["ok"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())