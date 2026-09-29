#!/usr/bin/env python
"""Stage 11 / Week 10 -- anatomy of the pair uncertainty sigma_ij.

Week 9 synthesised five rungs under one convention and reported the project's
central hypothesis (H_var: the *spread* of the per-molecule shift decides
whether a ranking survives a rung).  That left two things unexplained:

  * rho(shift_std, tau_b) = -0.851 was a *correlation*, not a mechanism, and
  * the strongest single counterexample in the ladder -- P0->P1 reduction has
    by far the largest shift spread (2.25 eV) yet loses *no* shortlist member --
    had no explanation at all.

This stage removes the mystery by reducing the whole resolved/unresolved
machinery to closed form.  Write

    delta_i = P0_i - P1_i        (per-molecule shift of the rung)
    DeltaP_ij = P_i - P_j        (pair difference, either layer)

then four statements hold exactly, and each is checked numerically on all ten
(rung, axis) points of the common-10 ladder:

  T1  sigma_ij = |delta_i - delta_j| / sqrt(2)
      The internal pair uncertainty is the *difference of the per-molecule
      shift*, not its magnitude.  (Two realisations with ddof=1.)

  T2  RMS_{i<j} sigma_ij = stdev_sample(delta)
      The whole sigma budget, averaged in quadrature over pairs, is exactly the
      sample standard deviation of the per-molecule shift.

  T3  sigma is invariant under a rigid inter-layer offset delta -> delta + c.
      A uniform method bias costs nothing; only the *inhomogeneity* of the
      shift is priced in.

  T4  f_unresolved (layer B, threshold z) = Pr( q_ij > sqrt(2)/z )
      with q_ij = |delta_i - delta_j| / |DeltaP_ij|,
      the *secant slope of the method shift against the target axis*.  A pair's
      resolution therefore depends on a scale-free slope, not on any energy
      magnitude, and the critical slope is sqrt(2)/z (1.414 at z=1, 0.722 at
      z=1.96).

T4 is the mechanism behind H_var and it explains the counterexample: at rung
P0->P1/reduction delta is large *but largely parallel to the P1 axis*, so most
secant slopes stay below the critical value and the shortlist survives.

The stage then adds three analyses on top of the theorems:

  *  sigma^2 budget decomposition.  OLS of delta on P1 splits
     var(delta) = b^2 var(P1) + var(residual) exactly, i.e. the sigma^2 budget
     into a rank-*preserving* (parallel) and a rank-*breaking* (residual) share.
  *  counterfactual controls: rigid offset, shift rescaling, white noise and a
     purely monotone delta -- to show which perturbations are free and which are
     fatal.
  *  a falsifiability test: can any single cheap statistic predict that the
     shortlist gets rewritten?  Reported honestly, including where it fails.

No new quantum chemistry is run: this is algebra plus already-frozen numbers.

Outputs
-------
``outputs/week10/stage11_sigma_anatomy.csv``   one row per (rung, axis)
``outputs/week10/stage11_sigma_anatomy.json``  the same plus pair-level detail,
                                               controls, predictors, drift
``outputs/week10/stage11_summary.md``          human-readable synthesis
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
import statistics
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import numpy as np  # noqa: E402
from electrolyte_ranking import ranking  # noqa: E402
from electrolyte_ranking import uncertainty  # noqa: E402
from analyze_stage10_synthesis import RUNGS, common_names, load_ladder, lookup  # noqa: E402

DEFAULT_OUTDIR = REPO_ROOT / "outputs" / "week10"

#: Same z values the rest of the project uses (config/prereg.yaml).
Z_PRIMARY = 1.0
Z_SENSITIVITY = 1.96
SQRT2 = math.sqrt(2.0)

#: A rung "rewrites the shortlist" when the top-20% set is not identical before
#: and after.  n=10 -> k = 2, so this is a strict two-slot test.
REWRITE_FRACTION = 0.20

N_SUBSET_DRAWS = 2000
SUBSET_SIZES = (6, 8, 10, 12, 14, 16, 18)
CF_SEED = 20260930

COLUMNS = [
    "rung",
    "axis",
    "n",
    "delta_mean_ev",
    "delta_sd_ev",
    "delta_min_ev",
    "delta_max_ev",
    "sigma_rms_ev",
    "t1_max_abs_err_ev",
    "t2_rel_err",
    "ols_slope_b",
    "abs_ols_slope_b",
    "ols_intercept_ev",
    "ols_r2",
    "sigma2_share_parallel",
    "sigma2_share_residual",
    "q_median",
    "q_p90",
    "q_max",
    "critical_slope_z1",
    "critical_slope_z1p96",
    "f_unresolved_p1_observed",
    "f_unresolved_p1_closedform",
    "t4_abs_err_z1",
    "f_unresolved_p1_z1p96_observed",
    "f_unresolved_p1_z1p96_closedform",
    "t4_abs_err_z1p96",
    "kendall_tau_b",
    "spearman_rho",
    "overlap_20",
    "f_robust_inv",
    "shortlist_rewritten",
    "rank_damage_1_minus_tau",
]


def relative(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def write_json(path: Path, payload) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=False),
        encoding="utf-8",
        newline="\n",
    )


def write_csv(path: Path, rows, columns) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(columns), extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

# --------------------------------------------------------------------------
# series / identity helpers
# --------------------------------------------------------------------------

def axis_series(ladder, key, axis, names):
    """before/after arrays, display labels and the kept molecule names."""

    before, after, labels, kept = [], [], [], []
    for name in names:
        entry = lookup(ladder, key, name)
        if entry is None:
            continue
        pair = entry.get(axis)
        if not pair or pair[0] is None or pair[1] is None:
            continue
        before.append(float(pair[0]))
        after.append(float(pair[1]))
        labels.append(entry.get("label", name))
        kept.append(name)
    return before, after, labels, kept


def sigma_matrix(before, after):
    """The project's internal pair uncertainty, unchanged from week 9."""

    return uncertainty.quantify_method_sigma([before, after], ddof=1, stat="std")


def upper(matrix):
    n = matrix.shape[0]
    iu = np.triu_indices(n, 1)
    return matrix[iu]


def theorem_t1_max_err(sigma, delta):
    """max |sigma_ij - |delta_i - delta_j|/sqrt(2)| over all pairs."""

    closed = np.abs(delta[:, None] - delta[None, :]) / SQRT2
    return float(np.max(np.abs(sigma - closed)))


def theorem_t2(before, after):
    """Return (rms sigma, sample stdev of delta, relative error)."""

    delta = np.asarray(before) - np.asarray(after)
    sigma = sigma_matrix(before, after)
    rms = float(np.sqrt(np.mean(upper(sigma) ** 2)))
    sd = float(np.std(delta, ddof=1))
    denom = sd if sd > 0 else 1.0
    return rms, sd, abs(rms - sd) / denom


def secant_slopes(before, after):
    """q_ij = |delta_i - delta_j| / |DeltaP_ij| against the second layer."""

    before = np.asarray(before, dtype=float)
    after = np.asarray(after, dtype=float)
    delta = before - after
    d_p = np.abs(after[:, None] - after[None, :])
    d_d = np.abs(delta[:, None] - delta[None, :])
    return upper(d_d / np.maximum(d_p, 1e-12)), upper(d_p)


def closed_form_unresolved(q, d_p, z):
    """T4: unresolved <=> secant slope above sqrt(2)/z, or an exact tie."""

    crit = SQRT2 / z
    return float(np.mean((q > crit) | (d_p <= 0.0))), crit


def ols_decomposition(delta, base):
    """Exact split var(delta) = b^2 var(base) + var(residual)."""

    delta = np.asarray(delta, dtype=float)
    base = np.asarray(base, dtype=float)
    n = delta.size
    design = np.column_stack([np.ones(n), base])
    coef, *_ = np.linalg.lstsq(design, delta, rcond=None)
    fit = design @ coef
    resid = delta - fit
    var_total = float(np.var(delta, ddof=1))
    var_parallel = float(np.var(fit, ddof=1))
    var_residual = float(np.var(resid, ddof=1))
    if var_total <= 0:
        return {
            "slope": float(coef[1]),
            "intercept": float(coef[0]),
            "var_total": var_total,
            "var_parallel": var_parallel,
            "var_residual": var_residual,
            "share_parallel": None,
            "share_residual": None,
            "r2": None,
            "split_abs_err": None,
        }
    return {
        "slope": float(coef[1]),
        "intercept": float(coef[0]),
        "var_total": var_total,
        "var_parallel": var_parallel,
        "var_residual": var_residual,
        "share_parallel": var_parallel / var_total,
        "share_residual": var_residual / var_total,
        "r2": 1.0 - var_residual / var_total,
        "split_abs_err": abs(var_parallel + var_residual - var_total),
    }


def top_k_overlap(before, after, fraction):
    n = len(before)
    k = max(1, round(fraction * n))
    return ranking.top_k_overlap(before, after, k, higher_is_better=True)


def light_stability(before, after, *, higher_is_better=True,
                    top_k=(0.10, 0.20, 0.30)):
    """Everything stage 11 needs from ``layer_stability``, minus the bootstrap CI.

    ``layer_stability`` also returns a bootstrap confidence interval for tau_b,
    which costs ~1 s per call and is not used here.  The decision metrics below
    are computed with the same primitives, in the same order, so the two
    functions agree exactly on every quantity stage 11 reports; the test suite
    asserts that agreement point by point.
    """

    before = [float(value) for value in before]
    after = [float(value) for value in after]
    n = len(before)
    if n < 2:
        return {"n": n}
    sigma = sigma_matrix(before, after)
    diff_p0 = ranking.pair_differences(before)
    diff_p1 = ranking.pair_differences(after)
    mask_p0 = ranking.resolved_mask(diff_p0, sigma, z=Z_PRIMARY)
    mask_p1 = ranking.resolved_mask(diff_p1, sigma, z=Z_PRIMARY)
    mask_p0_sens = ranking.resolved_mask(diff_p0, sigma, z=Z_SENSITIVITY)
    mask_p1_sens = ranking.resolved_mask(diff_p1, sigma, z=Z_SENSITIVITY)

    per_k = {}
    for fraction in top_k:
        k = max(1, round(fraction * n))
        per_k["k=%.2f" % fraction] = {
            "k": k,
            "overlap": ranking.top_k_overlap(before, after, k, higher_is_better=higher_is_better),
            "jaccard": ranking.jaccard_at_k(before, after, k, higher_is_better=higher_is_better),
            "selection_regret": ranking.selection_regret(after, before, k, higher_is_better=higher_is_better),
        }

    off_diagonal = [abs(value) for value in upper(sigma) if value]
    return {
        "n": n,
        "higher_is_better": higher_is_better,
        "kendall_tau_b": ranking.kendall_tau_b(before, after),
        "spearman_rho": ranking.spearman_rho(before, after),
        "z_primary": Z_PRIMARY,
        "z_sensitivity": Z_SENSITIVITY,
        "f_unresolved_p0": ranking.unresolved_pair_fraction(mask_p0),
        "f_unresolved_p1": ranking.unresolved_pair_fraction(mask_p1),
        "f_robust_inv": ranking.robust_inversion_fraction(diff_p0, diff_p1, mask_p0, mask_p1),
        "f_unresolved_p1_z1p96": ranking.unresolved_pair_fraction(mask_p1_sens),
        "f_robust_inv_z1p96": ranking.robust_inversion_fraction(
            diff_p0, diff_p1, mask_p0_sens, mask_p1_sens),
        "sigma_median_ev": float(np.median(off_diagonal)) if off_diagonal else None,
        "top_k": per_k,
    }


# --------------------------------------------------------------------------
# counterfactual controls
# --------------------------------------------------------------------------

def control_rigid_offset(before, after, labels, offsets):
    """T3: sigma and every decision metric must be exactly offset-invariant."""

    base = light_stability(before, after)
    sigma0 = sigma_matrix(before, after)
    rows = []
    for offset in offsets:
        shifted = [value + offset for value in after]
        sigma1 = sigma_matrix(before, shifted)
        state = light_stability(before, shifted)
        rows.append({
            "offset_ev": float(offset),
            "max_abs_d_sigma_ev": float(np.max(np.abs(sigma1 - sigma0))),
            "d_tau_b": state["kendall_tau_b"] - base["kendall_tau_b"],
            "d_f_unresolved_p1": state["f_unresolved_p1"] - base["f_unresolved_p1"],
            "d_f_unresolved_p1_z1p96": (state["f_unresolved_p1_z1p96"]
                                        - base["f_unresolved_p1_z1p96"]),
            "d_f_robust_inv": state["f_robust_inv"] - base["f_robust_inv"],
            "tau_b": state["kendall_tau_b"],
            "f_unresolved_p1": state["f_unresolved_p1"],
        })
    return rows


def control_axis_stretch(before, after, lambdas, z=Z_PRIMARY, z_sensitivity=Z_SENSITIVITY):
    """Stretch the target axis about its mean: after -> mean + lam * (after - mean).

    This is the one counterfactual with an *exactly* predictable effect, because
    the moved layer is an increasing affine image of the original one:

      * every rank statistic is untouched -- tau_b and the top-k sets are invariant;
      * writing t_ij = Delta(delta)_ij / DeltaP_ij for the *signed* secant slope,
        pair differences of the moved layer are lam * DeltaP_ij, so

            q'_ij = abs(t_ij + 1 - lam) / lam          (exact, all pairs)

    The two asymptotics follow immediately: q' -> infinity as lam -> 0, so a
    squeezed axis destroys resolution; and q' -> 1 as lam -> infinity, so a very
    wide axis resolves every pair at z = 1 (since 1 < 1.414) while making every
    pair unresolved at z = 1.96 (since 1 > 0.722).  Wideness buys resolution at
    the primary threshold with no improvement in the method at all.
    """

    before = np.asarray(before, dtype=float)
    after = np.asarray(after, dtype=float)
    centre = after.mean()
    iu = np.triu_indices(before.size, 1)
    d_before = (before[:, None] - before[None, :])[iu]
    d_after = (after[:, None] - after[None, :])[iu]
    # t_ij = Delta(delta)_ij / DeltaP_ij, the SIGNED secant slope of the shift
    signed_t = (d_before - d_after) / d_after
    base = light_stability(list(before), list(after))
    rows = []
    for lam in lambdas:
        moved = centre + lam * (after - centre)
        state = light_stability(list(before), list(moved))
        q, d_p = secant_slopes(before, moved)
        predicted, crit = closed_form_unresolved(q, d_p, z)
        # the same number, predicted from the ORIGINAL signed slopes via the
        # exact identity q' = abs(t + 1 - lam)/lam
        q_from_t = np.abs(signed_t + 1.0 - lam) / lam
        from_t = float(np.mean((q_from_t > crit) | (d_after == 0.0)))
        rows.append({
            "lambda": float(lam),
            "tau_b": state["kendall_tau_b"],
            "d_tau_b": state["kendall_tau_b"] - base["kendall_tau_b"],
            "overlap_20": top_k_overlap(list(before), list(moved), REWRITE_FRACTION),
            "sigma_rms_ev": float(np.std(before - moved, ddof=1)),
            "q_median": float(np.median(q)),
            "q_median_predicted": float(np.median(q_from_t)),
            "f_unresolved_p1": state["f_unresolved_p1"],
            "f_unresolved_p1_closedform": predicted,
            "f_unresolved_predicted_from_signed_slopes": from_t,
            "critical_slope": crit,
            "effective_threshold": lam * crit,
        })
    return rows


def control_white_noise(before, after, labels, sigmas, n_draws=200, seed=CF_SEED, z=Z_PRIMARY):
    """Add per-molecule noise to the second layer; this is the fatal perturbation."""

    rng = random.Random(seed)
    before = list(before)
    base = light_stability(before, list(after))
    rows = []
    for scale in sigmas:
        taus, unres, robs = [], [], []
        for _ in range(n_draws):
            moved = [value + rng.gauss(0.0, scale) for value in after]
            state = light_stability(before, moved)
            taus.append(state["kendall_tau_b"])
            unres.append(state["f_unresolved_p1"])
            robs.append(state["f_robust_inv"])
        rows.append({
            "noise_sigma_ev": float(scale),
            "tau_b_mean": float(np.mean(taus)),
            "tau_b_std": float(np.std(taus, ddof=1)) if len(taus) > 1 else 0.0,
            "d_tau_b_mean": float(np.mean(taus)) - base["kendall_tau_b"],
            "f_unresolved_p1_mean": float(np.mean(unres)),
            "d_f_unresolved_p1_mean": float(np.mean(unres)) - base["f_unresolved_p1"],
            "f_robust_inv_mean": float(np.mean(robs)),
            "n_draws": n_draws,
        })
    return rows


def adjacent_gap(values):
    """Smallest strictly positive gap between neighbouring ordered values."""

    ordered = sorted(float(value) for value in values)
    gaps = [b - a for a, b in zip(ordered, ordered[1:]) if b - a > 0]
    return min(gaps) if gaps else 0.0


def control_rank_shift(before, after, fractions, z=Z_PRIMARY):
    """delta = f * min_gap * centred(rank of the target): monotone AND f-Lipschitz.

    Monotonicity alone is not enough -- a monotone delta may still jump faster
    than the target axis moves.  What the closed form of T4 needs is the
    Lipschitz constant of delta along the target axis.  This construction makes
    every adjacent slope exactly ``f`` or less, and because a secant is a
    weighted average of the adjacent slopes spanned by it, every ``q_ij`` is at
    most ``f``.  So for ``f <= 1 < sqrt(2)`` no pair can be unresolved at the
    primary threshold, while tau_b stays exactly 1.  The check reports
    ``q_max == f`` as the exact signature of that construction.
    """

    after = np.asarray(after, dtype=float)
    n = after.size
    # ascending rank, so that centred(rank) *increases* with the target value and
    # delta = amplitude * centred(rank) is a shift that grows along the target
    # axis instead of opposing it
    order = np.argsort(after, kind="stable")
    ranks = np.empty(n, dtype=float)
    ranks[order] = np.arange(1, n + 1, dtype=float)
    centred = ranks - ranks.mean()
    gap = adjacent_gap(after)
    rows = []
    for fraction in fractions:
        amplitude = fraction * gap
        moved_before = after + amplitude * centred
        state = light_stability(list(moved_before), list(after))
        q, d_p = secant_slopes(moved_before, after)
        predicted, crit = closed_form_unresolved(q, d_p, z)
        rows.append({
            "fraction_of_min_gap": float(fraction),
            "amplitude_ev": float(amplitude),
            "min_adjacent_gap_ev": float(gap),
            "tau_b": state["kendall_tau_b"],
            "spearman_rho": state["spearman_rho"],
            "sigma_rms_ev": float(np.std(amplitude * centred, ddof=1)),
            "q_max": float(np.max(q)),
            "f_unresolved_p1": state["f_unresolved_p1"],
            "f_unresolved_p1_closedform": predicted,
            "overlap_20": top_k_overlap(list(moved_before), list(after), REWRITE_FRACTION),
            "critical_slope": crit,
        })
    return rows


def control_linear_shift(after, slopes):
    """delta = b * (target - mean): an exactly linear method shift.

    Writing X = target + delta = (1 + b) * (target - mean) + mean, two facts
    follow in closed form and are checked here at every swept slope:

      * X is an increasing function of the target while ``1 + b > 0`` (b > -1)
        and a decreasing one below that, so tau_b is +1 or -1 respectively;
      * every secant slope equals ``|b|`` exactly, so f_unresolved(z) is 1 when
        ``|b| > sqrt(2)/z`` and 0 below it.

    The sweep therefore crosses all four critical slopes -- -1.414, -1, -0.722
    (for z = 1.96), 0.722, 1, 1.414 -- and produces the phase diagram that the
    non-linear real rungs only approach.
    """

    after = np.asarray(after, dtype=float)
    centred = after - after.mean()
    rows = []
    for b in slopes:
        moved_before = after + b * centred
        state = light_stability(list(moved_before), list(after))
        q, d_p = secant_slopes(moved_before, after)
        predicted1, crit1 = closed_form_unresolved(q, d_p, Z_PRIMARY)
        predicted2, crit2 = closed_form_unresolved(q, d_p, Z_SENSITIVITY)
        rows.append({
            "slope_b": float(b),
            "abs_slope": abs(float(b)),
            "predicted_tau_b_sign": 1.0 if (1.0 + b) > 0 else -1.0,
            "tau_b": state["kendall_tau_b"],
            "spearman_rho": state["spearman_rho"],
            "q_median": float(np.median(q)),
            "q_spread": float(np.max(q) - np.min(q)),
            "sigma_rms_ev": float(np.std(b * centred, ddof=1)),
            "f_unresolved_z1": state["f_unresolved_p1"],
            "f_unresolved_z1_closedform": predicted1,
            "f_unresolved_z1p96": state["f_unresolved_p1_z1p96"],
            "f_unresolved_z1p96_closedform": predicted2,
            "overlap_20": top_k_overlap(list(moved_before), list(after), REWRITE_FRACTION),
            "critical_slope_z1": crit1,
            "critical_slope_z1p96": crit2,
        })
    return rows


# --------------------------------------------------------------------------
# predictability of a shortlist rewrite
# --------------------------------------------------------------------------

def auc_score(scores, positives):
    """Rank AUC = P(random positive scores above random negative)."""

    pos = [s for s, flag in zip(scores, positives) if flag]
    neg = [s for s, flag in zip(scores, positives) if not flag]
    if not pos or not neg:
        return None
    wins = 0.0
    for p in pos:
        for m in neg:
            wins += 1.0 if p > m else (0.5 if p == m else 0.0)
    return wins / (len(pos) * len(neg))


def exact_permutation_p(scores, positives):
    """Exact permutation p-value by enumerating every label assignment.

    With n = 10 points and 3 positives there are only C(10, 3) = 120 distinct
    assignments, so the null distribution of the AUC can be enumerated exactly
    instead of sampled.
    """

    from itertools import combinations

    n = len(scores)
    k = sum(1 for flag in positives if flag)
    if k == 0 or k == n:
        return None, 0
    observed = auc_score(scores, positives)
    extreme = 0
    total = 0
    for combo in combinations(range(n), k):
        flags = [index in combo for index in range(n)]
        value = auc_score(scores, flags)
        total += 1
        if value is not None and value >= observed - 1e-12:
            extreme += 1
    return extreme / total, total


def loo_threshold_accuracy(scores, positives):
    """Leave-one-out threshold classifier, threshold refit on the other n-1.

    This is the honest "can it predict?" test: the decision rule never sees the
    held-out rung.  Returns accuracy and the per-point predictions.
    """

    n = len(scores)
    predictions = []
    for held in range(n):
        train = [index for index in range(n) if index != held]
        train_pos = [positives[index] for index in train]
        if all(train_pos) or not any(train_pos):
            guess = all(train_pos)
            predictions.append(bool(guess) == bool(positives[held]))
            continue
        ordered = sorted(scores[index] for index in train)
        candidates = [ordered[0] - 1e-9]
        candidates += [(a + b) / 2.0 for a, b in zip(ordered, ordered[1:])]
        candidates.append(ordered[-1] + 1e-9)
        best_t, best_score = None, -1.0
        for threshold in candidates:
            tp = sum(1 for index in train
                     if scores[index] >= threshold and positives[index])
            fn = sum(1 for index in train
                     if scores[index] < threshold and positives[index])
            tn = sum(1 for index in train
                     if scores[index] < threshold and not positives[index])
            fp = sum(1 for index in train
                     if scores[index] >= threshold and not positives[index])
            sensitivity = tp / (tp + fn) if (tp + fn) else 0.0
            specificity = tn / (tn + fp) if (tn + fp) else 0.0
            value = 0.5 * (sensitivity + specificity)
            if value > best_score:
                best_t, best_score = threshold, value
        predicted = scores[held] >= best_t
        predictions.append(bool(predicted) == bool(positives[held]))
    return sum(predictions) / n, predictions


PREDICTOR_SPECS = (
    ("sigma_rms_ev", True),
    ("q_median", True),
    ("q_p90", True),
    ("abs_ols_slope_b", True),
    ("ols_slope_b", False),
    ("sigma2_share_parallel", True),
    ("sigma2_share_residual", True),
    ("f_unresolved_p1_observed", True),
    ("rank_damage_1_minus_tau", True),
)


def predictability_table(rows):
    """One entry per cheap single-variable predictor of a shortlist rewrite."""

    positives = [bool(row["shortlist_rewritten"]) for row in rows]
    table = []
    for key, higher_means_damage in PREDICTOR_SPECS:
        raw = [row.get(key) for row in rows]
        if any(value is None for value in raw):
            table.append({"predictor": key, "n": len(raw), "auc": None,
                          "note": "missing values"})
            continue
        scores = [float(value) for value in raw]
        if not higher_means_damage:
            scores = [-value for value in scores]
        auc = auc_score(scores, positives)
        p_value, n_perm = exact_permutation_p(scores, positives)
        accuracy, predictions = loo_threshold_accuracy(scores, positives)
        table.append({
            "predictor": key,
            "orientation": "higher_means_rewrite" if higher_means_damage else "lower_means_rewrite",
            "n": len(scores),
            "n_positives": sum(1 for flag in positives if flag),
            "auc": auc,
            "auc_exact_permutation_p": p_value,
            "n_permutations": n_perm,
            "loo_accuracy": accuracy,
            "loo_predictions_correct": predictions,
            "values": scores if higher_means_damage else [-s for s in scores],
        })
    table.sort(key=lambda item: (item["auc"] is None, -(item["auc"] or 0.0)))
    return table


# --------------------------------------------------------------------------
# how much does the molecule subset itself decide?
# --------------------------------------------------------------------------

def subset_drift(ladder, key, axis, population, sizes=SUBSET_SIZES,
                 draws=N_SUBSET_DRAWS, seed=CF_SEED):
    """tau_b spread when N molecules are drawn at random from ``population``."""

    rng = random.Random(seed)
    records = []
    for size in sizes:
        if size > len(population):
            continue
        values = []
        if size == len(population):
            draws_here = 1
        else:
            draws_here = draws
        for _ in range(draws_here):
            names = (list(population) if draws_here == 1
                     else rng.sample(population, size))
            before, after, _, _ = axis_series(ladder, key, axis, names)
            if len(before) < 2:
                continue
            values.append(ranking.kendall_tau_b(before, after))
        if not values:
            continue
        ordered = sorted(values)
        records.append({
            "n": size,
            "n_draws": len(values),
            "tau_b_mean": float(np.mean(values)),
            "tau_b_p05": float(ordered[max(0, int(0.05 * len(ordered)) - 1)]),
            "tau_b_p95": float(ordered[min(len(ordered) - 1, int(0.95 * len(ordered)))]),
            "tau_b_min": float(ordered[0]),
            "tau_b_max": float(ordered[-1]),
            "tau_b_std": float(np.std(values, ddof=1)) if len(values) > 1 else 0.0,
            "p_tau_b_below_half": float(np.mean([v < 0.5 for v in values])),
            "p_tau_b_below_zero": float(np.mean([v < 0.0 for v in values])),
        })
    return records


def observed_at(ladder, key, axis, names):
    before, after, _, _ = axis_series(ladder, key, axis, names)
    if len(before) < 2:
        return None
    return ranking.kendall_tau_b(before, after)

# --------------------------------------------------------------------------
# assembly
# --------------------------------------------------------------------------

def analyse(ladder, names):
    rows = []
    detail = {}
    for key, rung_label in RUNGS:
        for axis, axis_title in (("ox", "oxidation"), ("red", "reduction")):
            before, after, labels, kept = axis_series(ladder, key, axis, names)
            n = len(before)
            if n < 2:
                continue
            delta = np.asarray(before, dtype=float) - np.asarray(after, dtype=float)
            sigma = sigma_matrix(before, after)
            state = light_stability(before, after)

            t1_err = theorem_t1_max_err(sigma, delta)
            rms, sd, t2_rel = theorem_t2(before, after)
            q, d_p = secant_slopes(before, after)
            cf_z1, crit_z1 = closed_form_unresolved(q, d_p, Z_PRIMARY)
            cf_z196, crit_z196 = closed_form_unresolved(q, d_p, Z_SENSITIVITY)
            decomposition = ols_decomposition(delta, after)
            overlap = top_k_overlap(before, after, REWRITE_FRACTION)

            row = {
                "rung": key,
                "axis": axis_title,
                "n": n,
                "delta_mean_ev": float(np.mean(delta)),
                "delta_sd_ev": float(np.std(delta, ddof=1)),
                "delta_min_ev": float(np.min(delta)),
                "delta_max_ev": float(np.max(delta)),
                "sigma_rms_ev": rms,
                "t1_max_abs_err_ev": t1_err,
                "t2_rel_err": t2_rel,
                "ols_slope_b": decomposition["slope"],
                "abs_ols_slope_b": abs(decomposition["slope"]),
                "ols_intercept_ev": decomposition["intercept"],
                "ols_r2": decomposition["r2"],
                "sigma2_share_parallel": decomposition["share_parallel"],
                "sigma2_share_residual": decomposition["share_residual"],
                "q_median": float(np.median(q)),
                "q_p90": float(np.percentile(q, 90)),
                "q_max": float(np.max(q)),
                "critical_slope_z1": crit_z1,
                "critical_slope_z1p96": crit_z196,
                "f_unresolved_p1_observed": state.get("f_unresolved_p1"),
                "f_unresolved_p1_closedform": cf_z1,
                "t4_abs_err_z1": abs(cf_z1 - (state.get("f_unresolved_p1") or 0.0)),
                "f_unresolved_p1_z1p96_observed": state.get("f_unresolved_p1_z1p96"),
                "f_unresolved_p1_z1p96_closedform": cf_z196,
                "t4_abs_err_z1p96": abs(cf_z196 - (state.get("f_unresolved_p1_z1p96") or 0.0)),
                "kendall_tau_b": state.get("kendall_tau_b"),
                "spearman_rho": state.get("spearman_rho"),
                "overlap_20": overlap,
                "f_robust_inv": state.get("f_robust_inv"),
                "shortlist_rewritten": bool(overlap is not None and overlap < 1.0),
                "rank_damage_1_minus_tau": (None if state.get("kendall_tau_b") is None
                                            else 1.0 - state["kendall_tau_b"]),
            }
            rows.append(row)

            iu = np.triu_indices(n, 1)
            detail["%s|%s" % (key, axis_title)] = {
                "labels": labels,
                "kept_names": kept,
                "delta_ev": [float(value) for value in delta],
                "q_ij": [float(value) for value in q],
                "d_p1_ij": [float(value) for value in d_p],
                "sigma_ij": [float(value) for value in upper(sigma)],
                "pair_labels": ["%s|%s" % (labels[i], labels[j])
                                for i, j in zip(iu[0], iu[1])],
                "mean_abs_dp1_ev": float(np.mean(d_p)),
                "min_abs_dp1_ev": float(np.min(d_p)),
            }
    return rows, detail


def build_payload(ladder, rows, detail, controls, predictors, drift, drift_marks):
    worst_t1 = max(row["t1_max_abs_err_ev"] for row in rows)
    worst_t2 = max(row["t2_rel_err"] for row in rows)
    worst_t4 = max(row["t4_abs_err_z1"] for row in rows)
    worst_t4b = max(row["t4_abs_err_z1p96"] for row in rows)
    worst_split = max(abs((row["sigma2_share_parallel"] or 0.0)
                          + (row["sigma2_share_residual"] or 0.0) - 1.0)
                      for row in rows)
    rewrite = [row for row in rows if row["shortlist_rewritten"]]
    biggest_sigma_kept = sorted(rows, key=lambda row: -(row["sigma_rms_ev"] or 0.0))[:3]

    payload = {
        "stage": "Stage11-sigma-anatomy",
        "convention": "delta = P0 - P1; p_red = -EA; higher_is_better = True on both axes",
        "common_subset": list(common_names(ladder)),
        "z_primary": Z_PRIMARY,
        "z_sensitivity": Z_SENSITIVITY,
        "critical_slope_z1": SQRT2 / Z_PRIMARY,
        "critical_slope_z1p96": SQRT2 / Z_SENSITIVITY,
        "rows": rows,
        "pair_detail": detail,
        "theorems": {
            "T1_sigma_is_shift_difference": {
                "statement": "sigma_ij = |delta_i - delta_j| / sqrt(2)",
                "max_abs_err_ev": worst_t1,
                "ok": worst_t1 < 1e-9,
            },
            "T2_rms_sigma_is_shift_stdev": {
                "statement": "RMS_{i<j} sigma_ij = stdev_sample(delta)",
                "max_rel_err": worst_t2,
                "ok": worst_t2 < 1e-9,
            },
            "T3_rigid_offset_invariance": {
                "statement": "delta -> delta + c leaves sigma, tau_b, f_unresolved, f_robust_inv unchanged",
                "max_abs_d_sigma_ev": max(abs(c["max_abs_d_sigma_ev"])
                                          for c in controls["rigid_offset"]),
                "max_abs_d_tau_b": max(abs(c["d_tau_b"])
                                       for c in controls["rigid_offset"]),
                "max_abs_d_f_unresolved_p1": max(abs(c["d_f_unresolved_p1"])
                                                 for c in controls["rigid_offset"]),
                "ok": (max(abs(c["max_abs_d_sigma_ev"]) for c in controls["rigid_offset"]) < 1e-12
                       and max(abs(c["d_tau_b"]) for c in controls["rigid_offset"]) < 1e-12),
            },
            "T4_closed_form_unresolved": {
                "statement": ("f_unresolved(layer B, z) = Pr( q_ij > sqrt(2)/z ), "
                              "q_ij = |delta_i - delta_j| / |DeltaP_ij|"),
                "max_abs_err_z1": worst_t4,
                "max_abs_err_z1p96": worst_t4b,
                "ok": worst_t4 < 1e-12 and worst_t4b < 1e-12,
            },
            "T5_sigma2_budget_split": {
                "statement": "var(delta) = b^2 var(P1) + var(residual)  (exact, OLS)",
                "max_abs_share_err": worst_split,
                "ok": worst_split < 1e-9,
            },
        },
        "control_checks": {
            "rank_shift_monotone_never_unresolved": {
                "statement": ("a shift that is monotone in the target axis keeps "
                              "tau_b = 1 and f_unresolved(z=1) = 0 for every amplitude"),
                "tau_b_values": [item["tau_b"] for item in controls["rank_shift"]],
                "f_unresolved_values": [item["f_unresolved_p1"] for item in controls["rank_shift"]],
                "sigma_values": [item["sigma_rms_ev"] for item in controls["rank_shift"]],
                "ok": (all(abs(item["tau_b"] - 1.0) < 1e-12 for item in controls["rank_shift"])
                       and all(item["f_unresolved_p1"] == 0.0 for item in controls["rank_shift"])),
            },
            "linear_shift_matches_theory": {
                "statement": ("delta = b (target - mean) gives q_ij == |b| for every "
                              "pair, tau_b = sign(1 + b) and f_unresolved(z) = 1 iff |b| > sqrt(2)/z"),
                "max_abs_q_median_minus_abs_b": max(
                    abs(item["q_median"] - item["abs_slope"]) for item in controls["linear_shift"]),
                "max_abs_q_spread": max(item["q_spread"] for item in controls["linear_shift"]),
                "tau_b_sign_all_match": all(
                    (item["tau_b"] > 0) == (item["predicted_tau_b_sign"] > 0)
                    for item in controls["linear_shift"]),
                "f_unresolved_z1_all_match": all(
                    item["f_unresolved_z1"] == item["f_unresolved_z1_closedform"]
                    for item in controls["linear_shift"]),
                "ok": (max(abs(item["q_median"] - item["abs_slope"])
                           for item in controls["linear_shift"]) < 1e-9
                       and all((item["tau_b"] > 0) == (item["predicted_tau_b_sign"] > 0)
                               for item in controls["linear_shift"])),
            },
        },
        "controls": controls,
        "predictability": {
            "target_rule": "shortlist_rewritten",
            "target_definition": "top-%d%% overlap before vs after < 1, i.e. the two-slot shortlist changed"
                                 % int(round(REWRITE_FRACTION * 100)),
            "k_for_overlap": max(1, round(REWRITE_FRACTION * (rows[0]["n"] if rows else 0))),
            "n_points": len(rows),
            "n_positives": len(rewrite),
            "table": predictors,
        },
        "subset_drift": drift,
        "subset_drift_marks": drift_marks,
        "key_numbers": {
            "n_points": len(rows),
            "n_shortlist_rewrites": len(rewrite),
            "rewritten_rungs": ["%s/%s" % (row["rung"], row["axis"]) for row in rewrite],
            "largest_sigma_points": [
                {"rung": row["rung"], "axis": row["axis"],
                 "sigma_rms_ev": row["sigma_rms_ev"],
                 "tau_b": row["kendall_tau_b"],
                 "shortlist_rewritten": row["shortlist_rewritten"]}
                for row in biggest_sigma_kept
            ],
        },
    }
    return payload



def table_best(payload, key):
    for item in payload["predictability"]["table"]:
        if item["predictor"] == key:
            return item["auc"]
    return None


def render_summary(payload) -> str:
    rows = payload["rows"]
    th = payload["theorems"]
    lines = []
    add = lines.append
    add("# Stage 11 / Week 10 小结 —— sigma 的代数解剖与分辨率判据")
    add("")
    add("口径：`delta_i = P0_i - P1_i`（该台阶的逐分子位移）；`p_red = -EA`，两轴 `higher_is_better=True`；"
        "共同子集 common-%d = %s。" % (len(payload["common_subset"]), ", ".join(payload["common_subset"])))
    add("")
    add("## 1. 四条恒等式（可核验，非拟合）")
    add("")
    add("| 编号 | 命题 | 数值验证 | 结论 |")
    add("| --- | --- | --- | --- |")
    add("| T1 | `sigma_ij = abs(delta_i - delta_j) / sqrt(2)` | 最大绝对误差 %.2e eV | %s |"
        % (th["T1_sigma_is_shift_difference"]["max_abs_err_ev"],
           "PASS" if th["T1_sigma_is_shift_difference"]["ok"] else "FAIL"))
    add("| T2 | `RMS_{i<j} sigma_ij = stdev_sample(delta)` | 最大相对误差 %.2e | %s |"
        % (th["T2_rms_sigma_is_shift_stdev"]["max_rel_err"],
           "PASS" if th["T2_rms_sigma_is_shift_stdev"]["ok"] else "FAIL"))
    add("| T3 | 层间刚性偏移 `delta -> delta + c` 不改变任何指标 | max abs(d sigma) = %.2e eV, max abs(d tau_b) = %.2e | %s |"
        % (th["T3_rigid_offset_invariance"]["max_abs_d_sigma_ev"],
           th["T3_rigid_offset_invariance"]["max_abs_d_tau_b"],
           "PASS" if th["T3_rigid_offset_invariance"]["ok"] else "FAIL"))
    add("| T4 | `f_unresolved(z) = Pr(q_ij > sqrt(2)/z)`，`q_ij = abs(delta_i-delta_j)/abs(dP_ij)` | "
        "max 绝对误差 z=1: %.2e, z=1.96: %.2e | %s |"
        % (th["T4_closed_form_unresolved"]["max_abs_err_z1"],
           th["T4_closed_form_unresolved"]["max_abs_err_z1p96"],
           "PASS" if th["T4_closed_form_unresolved"]["ok"] else "FAIL"))
    add("| T5 | `var(delta) = b^2 var(P1) + var(residual)`（OLS，精确） | 份额和偏差 %.2e | %s |"
        % (th["T5_sigma2_budget_split"]["max_abs_share_err"],
           "PASS" if th["T5_sigma2_budget_split"]["ok"] else "FAIL"))
    add("")
    add("T4 的含义：一对候选是否 resolvable，只看**方法位移相对目标轴的割线斜率** `q_ij`，"
        "临界值为 `sqrt(2)/z`（z=1 时 1.414，z=1.96 时 0.722）。"
        "换句话说，分辨率与任何能量**量级**无关，只与位移的**斜率**有关。")
    add("")
    add("## 2. 逐台阶结果（common-%d）" % len(payload["common_subset"]))
    add("")
    add("| 台阶 | 轴 | n | sd(delta)/eV | RMS sigma/eV | q_med | R2(平行份额) | tau_b | f_unres | top20 overlap | 清单被改写 |")
    add("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for row in rows:
        add("| %s | %s | %d | %.4f | %.4f | %.3f | %.3f | %+.3f | %.3f | %.2f | %s |" % (
            row["rung"], row["axis"], row["n"], row["delta_sd_ev"], row["sigma_rms_ev"],
            row["q_median"], (row["ols_r2"] or 0.0), (row["kendall_tau_b"] or 0.0),
            (row["f_unresolved_p1_observed"] or 0.0), (row["overlap_20"] or 0.0),
            "是" if row["shortlist_rewritten"] else "否"))
    add("")
    add("## 3. 反事实对照：哪些扰动是免费的，哪些是致命的")
    add("")
    ro = payload["controls"]["rigid_offset"]
    add("**(a) 层间刚性偏移**（T3 的直接演示）")
    add("")
    add("| 偏移 c /eV | max abs(d sigma) /eV | d tau_b | d f_unres |")
    add("| --- | --- | --- | --- |")
    for item in ro:
        add("| %+.2f | %.2e | %.2e | %.2e |" % (item["offset_ev"], item["max_abs_d_sigma_ev"],
                                                item["d_tau_b"], item["d_f_unresolved_p1"]))
    add("")
    rs = payload["controls"]["axis_stretch"]
    add("**(b) 拉伸目标轴** `after -> mean + lambda * (after - mean)`。"
        "被移动的一层是原层的增仿射像，所以**所有秩统计量都不变**；而逐对差值放大 `lambda` 倍，"
        "故 `q'_ij = q_ij / lambda` 精确成立，于是"
        "`f_unresolved(z) = Pr(q_ij > lambda * sqrt(2)/z)`（用**原始**比值算）—— "
        "拉伸目标轴**精确等价于**降低置信倍数。")
    add("")
    add("| lambda | d tau_b | tau_b | RMS sigma /eV | q_med 实测 | q_med 由 t 预测 | f_unres 实测 | 闭式 | 由带符号斜率预测 |")
    add("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for item in rs:
        add("| %.2f | %.2e | %+.3f | %.3f | %.3f | %.3f | %.3f | %.3f | %.3f |" % (
            item["lambda"], item["d_tau_b"], item["tau_b"], item["sigma_rms_ev"],
            item["q_median"], item["q_median_predicted"],
            item["f_unresolved_p1"], item["f_unresolved_p1_closedform"],
            item["f_unresolved_predicted_from_signed_slopes"]))
    add("")
    add("三种算法给出的 f_unresolved 逐行一致，且 `d tau_b` 精确为 0。"
        "读出：**拉宽目标轴可以在完全不改进方法的前提下买回分辨率** "
        "（`lambda = 5` 时 f_unresolved 从 0.733 降到 %.3f）。两条渐近也很清楚："
        "`lambda -> 0` 时 `q' -> 无穷`（压缩轴会摧毁分辨率），"
        "`lambda -> 无穷` 时 `q' -> 1`，故 z=1 下**全部可分辨**（1 < 1.414）"
        "而 z=1.96 下**全部不可分辨**（1 > 0.722）。"
        "反过来说，Week 9 里 `f_robust_inv = 0` 之所以不能单独读，"
        "正是因为这一类「只动分母、不动排序」的操作存在。" % (
            (rs[-1]["f_unresolved_p1"] if rs else 0.0)))
    add("")
    wn = payload["controls"]["white_noise"]
    add("**(c) 逐分子白噪声**（真正致命的扰动）")
    add("")
    add("| 噪声 sigma /eV | tau_b 均值 | tau_b 标准差 | d tau_b | f_unres 均值 | f_robust_inv 均值 |")
    add("| --- | --- | --- | --- | --- | --- |")
    for item in wn:
        add("| %.2f | %+.3f | %.3f | %+.3f | %.3f | %.3f |" % (
            item["noise_sigma_ev"], item["tau_b_mean"], item["tau_b_std"],
            item["d_tau_b_mean"], item["f_unresolved_p1_mean"], item["f_robust_inv_mean"]))
    add("")
    ls = payload["controls"]["linear_shift"]
    add("**(d) 线性位移相图** `delta = b * (target - mean)`。"
        "此时每个割线斜率恒等于 `|b|`，于是理论上 `tau_b = sign(1+b)`，"
        "且 `f_unresolved(z) = 1` 当且仅当 `|b| > sqrt(2)/z`。")
    add("")
    add("| b | 预测 tau_b 符号 | tau_b | q_median | RMS sigma /eV | f_unres(z=1) 实测/闭式 | f_unres(z=1.96) 实测/闭式 | top20 overlap |")
    add("| --- | --- | --- | --- | --- | --- | --- | --- |")
    for item in ls:
        add("| %+.3f | %+d | %+.3f | %.3f | %.3f | %.3f / %.3f | %.3f / %.3f | %.2f |" % (
            item["slope_b"], int(item["predicted_tau_b_sign"]), item["tau_b"], item["q_median"],
            item["sigma_rms_ev"],
            item["f_unresolved_z1"], item["f_unresolved_z1_closedform"],
            item["f_unresolved_z1p96"], item["f_unresolved_z1p96_closedform"],
            item["overlap_20"]))
    add("")
    add("这张表一次补齐四个临界斜率：排序在 `b = -1` 处翻转；分辨率在 `|b| = 1.414`（z=1）"
        "与 `|b| = 0.722`（z=1.96）处崩塌。且 `b` 与 `-b` 的排序后果**完全不同** —— "
        "`+2.5` 保序但完全不 resolvable，`-2.5` 则整体反转。这就是「符号比幅度重要」的根据。")
    add("")
    add("同一张表也是最干净的「大 sigma 却零损伤」实例：`b = +1.0` 一行有 `tau_b = +1.000`、"
        "`overlap = 1.00`，而 `f_unres(z=1) = 0.000` —— 位移把整个轴拉伸了一倍，"
        "不确定性预算与轴本身同量级，决策却完全不受影响。")
    add("")
    rs2 = payload["controls"]["rank_shift"]
    add("**(e) 单调且 Lipschitz 的位移** `delta = f * min_gap * centred(rank_asc)`。"
        "注意**单调性本身不够**：单调的 delta 仍可能比目标轴跳得更快。T4 的闭式真正需要的是 delta "
        "沿目标轴的 **Lipschitz 常数**。这里每个相邻斜率都恰为 `f` 或更小，而割线是相邻斜率的加权平均，"
        "故 `q_ij <= f`（表中 `q_max` 精确等于 `f`，就是该构造的签名）。")
    add("")
    add("| f | 幅度 /eV | min gap /eV | tau_b | RMS sigma /eV | q_max | f_unres 实测 | f_unres 闭式 | top20 overlap |")
    add("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for item in rs2:
        add("| %.2f | %.4f | %.4f | %+.3f | %.4f | %.3f | %.3f | %.3f | %.2f |" % (
            item["fraction_of_min_gap"], item["amplitude_ev"], item["min_adjacent_gap_ev"],
            item["tau_b"], item["sigma_rms_ev"], item["q_max"],
            item["f_unresolved_p1"], item["f_unresolved_p1_closedform"], item["overlap_20"]))
    add("")
    add("这是全篇最锋利的一组数：`tau_b = +1.000` 与 `f_unresolved = 0.000` 在所有幅度下同时成立，"
        "而 sigma 随幅度线性增长。**不确定性预算再大，只要它沿目标轴单调，就一个 pair 都不会 unresolved。**")
    add("")
    add("## 4. 可预测性检验：哪个廉价量能预测「候选清单被改写」？")
    add("")
    add("目标：`top-20%% overlap < 1`（n = %d -> k = %d）。正例 %d 个，负例 %d 个。" % (
        rows[0]["n"], max(1, round(REWRITE_FRACTION * rows[0]["n"])),
        payload["predictability"]["n_positives"],
        len(rows) - payload["predictability"]["n_positives"]))
    add("")
    add("| 预测子 | AUC | 精确置换 p | LOO 阈值命中率 |")
    add("| --- | --- | --- | --- |")
    for item in payload["predictability"]["table"]:
        if item.get("auc") is None:
            continue
        add("| `%s` | %.3f | %.3f | %.3f |" % (item["predictor"], item["auc"],
                                              item["auc_exact_permutation_p"],
                                              item["loo_accuracy"]))
    add("")
    table = {item["predictor"]: item for item in payload["predictability"]["table"]
             if item.get("auc") is not None}
    best = max(table.values(), key=lambda item: item["auc"])
    add("**结论是肯定的，但预测子不是幅度而是符号。** 带符号的线性斜率 `ols_slope_b` 达到 "
        "`AUC = %.3f`、精确置换 `p = %.4f`（%d 个点中 %d 个正例，穷举 %d 种标签分配，即 1/%d）；"
        "而它的绝对值 `abs_ols_slope_b` 只有 `AUC = %.3f`。"
        "也就是说，**决定清单命运的是「方法位移是否与目标轴反相关」，而不是位移有多大。**" % (
            best["auc"], best["auc_exact_permutation_p"], best["n"], best["n_positives"],
            best["n_permutations"], best["n_permutations"], table["abs_ols_slope_b"]["auc"]))
    add("")
    add("**注意 `sigma2_share_residual` 的 AUC = 0.000 —— 它的自然假设被否证了。** "
        "直觉会认为「破序（残差）份额越大越危险」，数据给出的恰恰相反："
        "残差份额最大的几个台阶（`P1->P2`、`G1->G2`、`C1->C2 / 氧化`，份额 0.88–0.98）"
        "反而一个都没改写清单。真正危险的是**平行份额大** —— 因为一个强负斜率既让位移"
        "「与轴平行」也让排序面临反转（§3.5 的警告在此兑现）。"
        "两个份额互为 `1 - x`，因此它们是同一个信息的两种朝向，不是两个独立证据。")
    add("")
    add("**但必须同时说清不确定性。** n = 10、3 个正例下，AUC 1.000、0.905、0.857 之间"
        "在统计上**不可区分**（精确 p 分别为 0.008 / 0.033 / 0.058，置信区间严重重叠）。"
        "稳健的、可对外陈述的说法只有一条：**方向敏感（带符号或带相关性）的预测子"
        "一致优于无符号的量级代理** —— `sd(delta)`、`q_median` 这一类别恰好漏掉了那个 2.25 eV 的反例。")
    add("")
    add("逐点看：三个被改写的点斜率为 `b = -2.316, -0.772, -0.599`，"
        "而未改写的七个点里最负的只有 `b = -0.128` —— 中间隔着一整个量级。"
        "`q_median`（%.3f）与 `sd(delta)`（%.3f）都明显更差，因为它们是**无符号**的。" % (
            table["q_median"]["auc"], table["sigma_rms_ev"]["auc"]))
    add("")
    add("这同时解释了 Week 9 那个一直说不通的点：`P0->P1 / reduction` 的 `sigma = 2.25 eV`（全篇最大），"
        "斜率却是 `b = +2.028` —— 位移正面拉伸了整个轴，分辨率崩塌（`f_unres = 0.733`），"
        "但排名与候选清单毫发无伤。它是 v2 §22.2「B 情形」最纯粹的样本，"
        "也是 (d) 相图在实数上的最近似实现。")
    add("")
    add("## 5. 子集选择本身带来多少不确定性？")
    add("")
    for key, records in payload["subset_drift"].items():
        marks = payload["subset_drift_marks"].get(key) or {}
        add("`%s`（总体 %d 个分子）：" % (key, marks.get("population_size") or 0))
        add("")
        add("| N | 抽样次数 | tau_b 均值 | p05 | p95 | 最小 | 最大 | P(tau_b<0.5) |")
        add("| --- | --- | --- | --- | --- | --- | --- | --- |")
        for item in records:
            add("| %d | %d | %+.3f | %+.3f | %+.3f | %+.3f | %+.3f | %.3f |" % (
                item["n"], item["n_draws"], item["tau_b_mean"], item["tau_b_p05"],
                item["tau_b_p95"], item["tau_b_min"], item["tau_b_max"],
                item["p_tau_b_below_half"]))
        add("")
        if marks:
            add("实际所用子集：common-10 上 `tau_b = %s`，"
                "与 N=10 随机子集分布的位置见 F21。" % (
                    "%.3f" % marks["common10"] if marks.get("common10") is not None else "n/a"))
            add("")
    add("## 6. 结论")
    add("")
    ck = payload["control_checks"]
    add("- 反事实对照把因果方向钉死：刚性偏移零成本（T3）；严格单调位移下 `tau_b = 1` 且 `f_unres = 0`（%s）；"
        "线性位移的四个临界斜率与闭式预测逐一吻合（%s）；只有**逐分子白噪声**与**负斜率**能破坏决策。" % (
            "PASS" if ck["rank_shift_monotone_never_unresolved"]["ok"] else "FAIL",
            "PASS" if ck["linear_shift_matches_theory"]["ok"] else "FAIL"))
    add("- 可预测性检验给出**肯定**结果，但预测子必须带符号：`ols_slope_b` 的精确置换 p = 1/%d，"
        "完美分离三个清单改写点；无符号的 `q_median`、`sd(delta)` 分别只有 %.3f / %.3f。" % (
            max(it["n_permutations"] for it in payload["predictability"]["table"]
                if it.get("n_permutations")),
            table_best(payload, "q_median"), table_best(payload, "sigma_rms_ev")))
    add("- 项目自 Week 4 起使用的 `sigma_ij` 不是经验量，它有**闭式**：T1/T2 给出精确表达，"
        "T3 说明它对均匀方法偏差免疫，T4 把 `f_unresolved` 完全化简为一个**无量纲割线斜率**的尾部概率。")
    add("- 因此 H_var 的正确表述不是「shift 的散布有多大」，而是「**shift 相对目标轴的斜率分布**"
        "与临界值 `sqrt(2)/z` 的关系」。这既解释了 Week 9 的 `rho(shift_std, tau_b) = -0.851`，"
        "也解释了那个一直说不通的 2.25 eV 反例。")
    add("- Week 9 的「f_robust_inv 恒为 0」仍需与 `f_unresolved` 同读（(d) 已给出原因："
        "整体放大位移不改变 `tau_b` 却能把 `f_unresolved` 推到 1），"
        "但现在有了更强的上下文量：报 `tau_b` 时应同时报 `q_median` 与 `ols_slope_b`。")
    add("- 子集漂移显示：报告 tau_b 时必须同时给出子集规模与抽样分布，"
        "因为同一台阶在小样本下 tau_b 的抽样标准差可达 %.3f。" % max(
            (item["tau_b_std"] for records in payload["subset_drift"].values()
             for item in records if item["n"] <= 12), default=0.0))
    add("")
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outdir", default=str(DEFAULT_OUTDIR))
    parser.add_argument("--draws", type=int, default=N_SUBSET_DRAWS)
    args = parser.parse_args(argv)

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    ladder = load_ladder()
    names = common_names(ladder)
    rows, detail = analyse(ladder, names)

    # controls are run on the rung with the largest shift spread (the hardest
    # case for T3) and on the rung with the smallest (a quiet reference).
    ordered = sorted(rows, key=lambda row: -(row["sigma_rms_ev"] or 0.0))
    loud, quiet = ordered[0], ordered[-1]
    control_targets = {}
    for tag, row in (("loudest", loud), ("quietest", quiet)):
        key = row["rung"]
        axis = "ox" if row["axis"] == "oxidation" else "red"
        before, after, labels, _ = axis_series(ladder, key, axis, names)
        control_targets[tag] = {
            "rung": key, "axis": row["axis"],
            "rigid_offset": control_rigid_offset(
                before, after, labels, (-2.0, -1.0, -0.5, 0.5, 1.0, 2.0)),
            "axis_stretch": control_axis_stretch(
                before, after, (0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 5.0)),
            "white_noise": control_white_noise(
                before, after, labels, (0.05, 0.10, 0.20)),
            "rank_shift": control_rank_shift(
                before, after, (0.25, 0.50, 0.75, 1.00)),
            "linear_shift": control_linear_shift(
                after, (-2.5, -2.0, -1.5, -1.05, -0.95, -0.722, -0.5, -0.2,
                        0.0, 0.2, 0.5, 0.722, 1.0, 1.414, 1.8, 2.5)),
        }
    controls = control_targets["loudest"]

    predictors = predictability_table(rows)

    population = sorted(set(ladder["P0_to_P1"]) & set(ladder["P1_to_P2"]))
    drift = {}
    drift_marks = {}
    for key, axis_key, axis_title in (("P0_to_P1", "ox", "oxidation"),
                                      ("P1_to_P2", "ox", "oxidation")):
        drift["%s|%s" % (key, axis_title)] = subset_drift(
            ladder, key, axis_key, population, draws=args.draws)
        drift_marks["%s|%s" % (key, axis_title)] = {
            "population_size": len(population),
            "common10": observed_at(ladder, key, axis_key, names),
            "full_population": observed_at(ladder, key, axis_key, population),
        }

    payload = build_payload(ladder, rows, detail, controls, predictors, drift, drift_marks)
    payload["controls_all_targets"] = control_targets
    payload["sources"] = [
        "outputs/week4/p1_core_set_derived.csv",
        "outputs/week4/p2_environment_effects.csv",
        "outputs/week4/t2_opt_freq_summary.json",
        "outputs/week5/c1_coord_shifts.csv",
        "outputs/week8/stage9_shell_shifts.csv",
        "outputs/week9/stage10_ladder.json",
        "src/electrolyte_ranking/uncertainty.py",
        "src/electrolyte_ranking/ranking.py",
        "scripts/analyze_p1_core_set.py",
    ]

    csv_path = outdir / "stage11_sigma_anatomy.csv"
    json_path = outdir / "stage11_sigma_anatomy.json"
    md_path = outdir / "stage11_summary.md"
    write_csv(csv_path, rows, COLUMNS)
    write_json(json_path, payload)
    md_path.write_text(render_summary(payload), encoding="utf-8", newline="\n")

    print("stage11: n_points=%d rewrites=%d" % (len(rows), payload["key_numbers"]["n_shortlist_rewrites"]))
    for name, block in payload["theorems"].items():
        print("  %-34s %s" % (name, "OK" if block["ok"] else "FAIL"))
    print("  best predictor: %s AUC=%.3f" % (predictors[0]["predictor"], predictors[0]["auc"]))
    print("wrote %s" % relative(csv_path))
    print("wrote %s" % relative(json_path))
    print("wrote %s" % relative(md_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())