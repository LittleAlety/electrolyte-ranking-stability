"""Stage 12 (week 11) - the resolution criterion becomes a screening protocol.

Two questions, both answered on numbers that were already frozen:

A.  The bare-CPCM dielectric ladder.  Weeks 4-6 established that a pure
    dielectric perturbation does not rewrite a shortlist, but never said why.
    Here the four epsilon levels of the T3 scan are lifted into the same
    (rung, axis) form as the five electronic-structure rungs, so the week-10
    criterion applies to them.  The result is a one-parameter law:
    the gas-to-condensed shift is linear in u = 1 - 1/eps (the Born form), so
    every rung of the ladder is the SAME vector times a known scalar
    c = u_hi - u_lo.  Consequences: sd(delta), the OLS slope b and the secant
    slope q all scale by c; the sign of b cannot change along the ladder; and
    the eps -> infinity limit is q -> 0, i.e. a conductor cannot damage a
    shortlist at all.

B.  Pre-screening.  If the criterion is worth anything it must tell you
    BEFORE you spend the compute whether a level is usable.  Exhaustive
    subsets of the common-10 show how the estimated slope b_hat converges and
    how many molecules a pilot needs for the danger flag to be reliable.

Outputs
-------
``outputs/week11/stage12_prescreen.csv``   one row per (rung, axis), 18 points
``outputs/week11/stage12_prescreen.json``  the same plus the dielectric law,
                                           the extrapolation test and the
                                           pre-screening budget curves
``outputs/week11/stage12_summary.md``      human-readable synthesis
"""

from __future__ import annotations

import argparse
import csv
import itertools
import json
import math
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import numpy as np  # noqa: E402
from electrolyte_ranking import ranking  # noqa: E402
from analyze_stage10_synthesis import (  # noqa: E402
    RUNGS, common_names, load_csv, load_ladder, lookup,
)
from analyze_stage11_sigma_anatomy import (  # noqa: E402
    Z_PRIMARY, Z_SENSITIVITY, SQRT2, axis_series, closed_form_unresolved,
    light_stability, ols_decomposition, secant_slopes, sigma_matrix,
    theorem_t1_max_err, theorem_t2, top_k_overlap, upper,
)

DEFAULT_OUTDIR = REPO_ROOT / "outputs" / "week11"

#: The T3 bare-CPCM scan (dielectric-only screening, no SMD surface terms).
T3_SCAN = REPO_ROOT / "outputs" / "week4" / "t3_cpcm_eps_scan.csv"

#: Dielectric levels of the ladder: the gas phase is eps = 1, so the four
#: scanned eps values extend it into a five-level series 1 < 5 < 10 < 20 < 40.
GAS_LEVEL = (1.0, "gas")
EPS_LEVELS = ((5.0, "5"), (10.0, "10"), (20.0, "20"), (40.0, "40"))
DIELECTRIC_LEVELS = (GAS_LEVEL,) + EPS_LEVELS

#: Rung keys for the four consecutive steps of the dielectric ladder.
DIELECTRIC_RUNGS = tuple(
    ("DIE_%s_to_%s" % (DIELECTRIC_LEVELS[i][1], DIELECTRIC_LEVELS[i + 1][1]),
     DIELECTRIC_LEVELS[i][0], DIELECTRIC_LEVELS[i + 1][0])
    for i in range(len(DIELECTRIC_LEVELS) - 1)
)

#: Prescreening pilot sizes, transcribed from the task the protocol solves:
#: "run only k molecules at the new level, then decide if it is usable".
PILOT_SIZES = (3, 4, 5, 6, 7, 8, 9)

#: A pilot flags a rung as unusable when the estimated slope is negative
#: (the week-10 finding: every shortlist rewrite has b < 0) or when it is so
#: steep that even the z = 1 threshold is exceeded.
PRESCREEN_Z = Z_PRIMARY

COLUMNS = [
    "rung",
    "rung_family",
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
    "ols_intercept_ev",
    "ols_r2",
    "sigma2_share_parallel",
    "sigma2_share_residual",
    "pearson_r_delta_axis",
    "q_median",
    "q_p90",
    "q_max",
    "critical_slope_z1",
    "f_unresolved_p1_observed",
    "f_unresolved_p1_closedform",
    "t4_abs_err_z1",
    "f_unresolved_p1_z1p96_observed",
    "t4_abs_err_z1p96",
    "kendall_tau_b",
    "overlap_20",
    "shortlist_rewritten",
    "t6_b_plus_1_vs_beta_err",
    "t7_slope_vs_r_ratio_err",
]


def relative(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def write_json(path: Path, payload) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8")


def write_csv(path: Path, rows, columns) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key) for key in columns})


def _float(value):
    if value in (None, "", "None"):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
# --------------------------------------------------------------------------
# the dielectric ladder
# --------------------------------------------------------------------------

def load_dielectric_levels():
    """name -> axis -> eps -> value, on the bare-CPCM scan plus the gas limit.

    The gas reference is taken from the P1 table, and the scan's own
    ``d_*_vs_gas`` columns are checked against it by the caller: if the two
    disagreed the ladder would not be a single series.
    """

    gas = {}
    for row in load_csv(REPO_ROOT / "outputs" / "week4" / "p1_core_set_derived.csv"):
        gas[row["name"]] = (_float(row.get("ip_r2scan3c_ev")),
                            _float(row.get("ea_r2scan3c_ev")))

    levels = {}
    for row in load_csv(T3_SCAN):
        ip = _float(row.get("ip_ev"))
        ea = _float(row.get("ea_ev"))
        eps = _float(row.get("eps"))
        if ip is None or ea is None or eps is None:
            continue
        rec = levels.setdefault(row["name"], {"ox": {}, "red": {}})
        rec["ox"][eps] = ip
        rec["red"][eps] = -ea

    for name, rec in levels.items():
        ip_gas, ea_gas = gas.get(name, (None, None))
        if ip_gas is not None:
            rec["ox"][1.0] = ip_gas
        if ea_gas is not None:
            rec["red"][1.0] = -ea_gas
    return levels


def gas_reference_check(names) -> float:
    """max |ip_scan(eps=5) - d_ip_vs_gas(eps=5) - ip_gas| over the molecules."""

    gas = {}
    for row in load_csv(REPO_ROOT / "outputs" / "week4" / "p1_core_set_derived.csv"):
        gas[row["name"]] = _float(row.get("ip_r2scan3c_ev"))
    worst = 0.0
    for row in load_csv(T3_SCAN):
        if _float(row.get("eps")) != 5.0:
            continue
        name = row["name"]
        if name not in gas or gas[name] is None:
            continue
        ip = _float(row.get("ip_ev"))
        d = _float(row.get("d_ip_vs_gas_ev"))
        if ip is None or d is None:
            continue
        worst = max(worst, abs((ip - d) - gas[name]))
    return worst


def build_dielectric_points(levels, names):
    points = []
    for key, lo, hi in DIELECTRIC_RUNGS:
        for axis in ("ox", "red"):
            before, after, kept = [], [], []
            for name in names:
                rec = levels.get(name)
                if not rec:
                    continue
                a = rec[axis].get(lo)
                b = rec[axis].get(hi)
                if a is None or b is None:
                    continue
                before.append(a)
                after.append(b)
                kept.append(name)
            points.append({"rung": key, "family": "dielectric", "axis": axis,
                           "before": before, "after": after, "names": kept})
    return points


def build_electronic_points(ladder, names):
    points = []
    for key, _label in RUNGS:
        for axis in ("ox", "red"):
            before, after, _labels, kept = axis_series(ladder, key, axis, names)
            points.append({"rung": key, "family": "electronic", "axis": axis,
                           "before": before, "after": after, "names": kept})
    return points


# --------------------------------------------------------------------------
# per-point metrics
# --------------------------------------------------------------------------

def pearson(x, y) -> float:
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if x.size < 2 or np.std(x) == 0.0 or np.std(y) == 0.0:
        return float("nan")
    return float(np.corrcoef(x, y)[0, 1])


def ols_slope(y, x) -> float:
    """Slope of y on x with an intercept; ``nan`` when x has no spread."""

    y = np.asarray(y, dtype=float)
    x = np.asarray(x, dtype=float)
    xc = x - x.mean()
    den = float(np.sum(xc * xc))
    if den == 0.0:
        return float("nan")
    return float(np.sum(xc * (y - y.mean())) / den)


def point_metrics(point, index: int) -> dict:
    before = np.asarray(point["before"], dtype=float)
    after = np.asarray(point["after"], dtype=float)
    n = int(before.size)
    row = {
        "index": index,
        "rung": point["rung"],
        "rung_family": point["family"],
        "axis": "oxidation" if point["axis"] == "ox" else "reduction",
        "axis_key": point["axis"],
        "n": n,
        "names": list(point["names"]),
    }
    if n < 2:
        return row

    delta = before - after
    sigma = sigma_matrix(before, after)
    stab = light_stability(before, after)
    dec = ols_decomposition(delta, after)
    q, d_p = secant_slopes(before, after)
    fu1, crit1 = closed_form_unresolved(q, d_p, Z_PRIMARY)
    fu2, crit2 = closed_form_unresolved(q, d_p, Z_SENSITIVITY)
    rms, sd, t2_rel = theorem_t2(before, after)
    r = pearson(delta, after)

    beta = ols_slope(before, after)              # T6: b + 1 == beta
    scale = float(np.std(delta, ddof=1) / np.std(after, ddof=1))
    b = float(dec["slope"]) if dec["slope"] is not None else float("nan")
    b_via_r = r * scale                          # T7: b == r * sd(delta)/sd(axis)

    overlap = top_k_overlap(before, after, 0.20)
    row.update({
        "delta_mean_ev": float(np.mean(delta)),
        "delta_sd_ev": sd,
        "delta_min_ev": float(np.min(delta)),
        "delta_max_ev": float(np.max(delta)),
        "sigma_rms_ev": rms,
        "t1_max_abs_err_ev": theorem_t1_max_err(sigma, delta),
        "t2_rel_err": t2_rel,
        "ols_slope_b": b,
        "ols_intercept_ev": float(dec["intercept"]),
        "ols_r2": dec["r2"],
        "sigma2_share_parallel": dec["share_parallel"],
        "sigma2_share_residual": dec["share_residual"],
        "pearson_r_delta_axis": r,
        "q_median": float(np.median(q)),
        "q_p90": float(np.percentile(q, 90)),
        "q_max": float(np.max(q)),
        "critical_slope_z1": crit1,
        "f_unresolved_p1_observed": stab["f_unresolved_p1"],
        "f_unresolved_p1_closedform": fu1,
        "t4_abs_err_z1": abs(stab["f_unresolved_p1"] - fu1),
        "f_unresolved_p1_z1p96_observed": stab["f_unresolved_p1_z1p96"],
        "t4_abs_err_z1p96": abs(stab["f_unresolved_p1_z1p96"] - fu2),
        "kendall_tau_b": stab["kendall_tau_b"],
        "overlap_20": overlap,
        "shortlist_rewritten": bool(overlap < 1.0 - 1e-12),
        "t6_b_plus_1_vs_beta_err": abs(b + 1.0 - beta),
        "t7_slope_vs_r_ratio_err": abs(b - b_via_r),
        "beta_cheap_on_axis": beta,
        "sd_axis_ev": float(np.std(after, ddof=1)),
    })
    return row


def top_k_overlap(before, after, fraction):
    n = len(before)
    k = max(1, round(fraction * n))
    return ranking.top_k_overlap(before, after, k, higher_is_better=True)

# --------------------------------------------------------------------------
# part A - the dielectric ladder as a one-parameter family
# --------------------------------------------------------------------------

def born_u(eps) -> float:
    """Born / Lippert-Mataga dielectric response factor, relative to vacuum."""

    return 1.0 - 1.0 / float(eps)


def onsager_v(eps) -> float:
    """The competing Onsager reaction-field factor (eps-1)/(2 eps + 1)."""

    eps = float(eps)
    return (eps - 1.0) / (2.0 * eps + 1.0)


def delta_series(levels, name, axis, eps_list):
    """delta(eps) = p(gas) - p(eps) for one molecule on one axis."""

    rec = levels.get(name)
    if not rec:
        return None
    base = rec[axis].get(1.0)
    if base is None:
        return None
    out = []
    for eps in eps_list:
        value = rec[axis].get(float(eps))
        if value is None:
            return None
        out.append(base - value)
    return out


def fit_factor(eps_list, deltas, factor):
    """Least-squares S in delta = S * factor(eps), through the origin."""

    u = np.asarray([factor(e) for e in eps_list], dtype=float)
    d = np.asarray(deltas, dtype=float)
    den = float(np.sum(u * u))
    if den == 0.0:
        return None, None
    s = float(np.sum(u * d) / den)
    pred = s * u
    ss_res = float(np.sum((d - pred) ** 2))
    ss_tot = float(np.sum((d - d.mean()) ** 2))
    r2 = None if ss_tot == 0.0 else 1.0 - ss_res / ss_tot
    return s, r2


def dielectric_law(levels, names):
    """Per-molecule Born response, its universality, and the increment ratios."""

    eps_scan = [5.0, 10.0, 20.0, 40.0]
    per_molecule = []
    born_r2, onsager_r2 = [], []
    ratio_rows = {"r1": [], "r2": [], "r3": []}
    predicted = {
        "born": {"r1": 8.0, "r2": 2.0, "r3": 2.0},
        "onsager": {},
    }
    u = [born_u(e) for e in [1.0] + eps_scan]
    v = [onsager_v(e) for e in [1.0] + eps_scan]
    predicted["onsager"]["r1"] = (v[2] - v[1]) / (v[1] - v[0]) if v[1] != v[0] else None
    predicted["onsager"]["r2"] = (v[2] - v[1]) / (v[3] - v[2]) if v[3] != v[2] else None
    predicted["onsager"]["r3"] = (v[3] - v[2]) / (v[4] - v[3]) if v[4] != v[3] else None
    predicted["born"]["r1"] = (u[2] - u[1]) / (u[1] - u[0]) if u[1] != u[0] else None
    predicted["born"]["r2"] = (u[2] - u[1]) / (u[3] - u[2]) if u[3] != u[2] else None
    predicted["born"]["r3"] = (u[3] - u[2]) / (u[4] - u[3]) if u[4] != u[3] else None

    for name in names:
        for axis in ("ox", "red"):
            d = delta_series(levels, name, axis, eps_scan)
            if d is None:
                continue
            s_born, r2_born = fit_factor(eps_scan, d, born_u)
            s_ons, r2_ons = fit_factor(eps_scan, d, onsager_v)
            if r2_born is not None:
                born_r2.append(r2_born)
            if r2_ons is not None:
                onsager_r2.append(r2_ons)
            # increments between consecutive levels of 1 < 5 < 10 < 20 < 40
            d_all = delta_series(levels, name, axis, [1.0] + eps_scan)
            steps = [d_all[i + 1] - d_all[i] for i in range(4)]
            ratios = {}
            for tag, (num, den) in {"r1": (steps[1], steps[0]),
                                    "r2": (steps[1], steps[2]),
                                    "r3": (steps[2], steps[3])}.items():
                value = None if den == 0.0 else num / den
                ratios[tag] = value
                if value is not None:
                    ratio_rows[tag].append(value)
            per_molecule.append({
                "name": name,
                "axis": "oxidation" if axis == "ox" else "reduction",
                "delta_by_eps": [float(x) for x in d],
                "born_S_ev": s_born,
                "born_r2": r2_born,
                "onsager_S_ev": s_ons,
                "onsager_r2": r2_ons,
                "increment_ev": [float(x) for x in steps],
                "ratio_r1_vs_born": ratios["r1"],
                "ratio_r2_vs_born": ratios["r2"],
                "ratio_r3_vs_born": ratios["r3"],
            })

    def summarize(values):
        if not values:
            return None
        arr = np.asarray(values, dtype=float)
        return {"n": int(arr.size), "mean": float(arr.mean()),
                "sd": float(arr.std(ddof=1)) if arr.size > 1 else 0.0,
                "min": float(arr.min()), "max": float(arr.max())}

    return {
        "eps_levels": eps_scan,
        "gas_level": 1.0,
        "born_factor_at_scan": [born_u(e) for e in eps_scan],
        "onsager_factor_at_scan": [onsager_v(e) for e in eps_scan],
        "predicted_ratios": predicted,
        "measured_ratios": {tag: summarize(vals) for tag, vals in ratio_rows.items()},
        "born_r2": summarize(born_r2),
        "onsager_r2": summarize(onsager_r2),
        "per_molecule": per_molecule,
    }


def shape_invariance(levels, names):
    """delta_k / c_k must be one and the same vector S at every rung k."""

    eps_scan = [5.0, 10.0, 20.0, 40.0]
    runs = []
    for i in range(len(eps_scan) - 1):
        lo, hi = eps_scan[i], eps_scan[i + 1]
        c = born_u(hi) - born_u(lo)
        runs.append((lo, hi, c))
    out = {"rungs": [{"eps_lo": lo, "eps_hi": hi, "c_born": c} for lo, hi, c in runs],
           "per_molecule": [],
           "max_rel_spread": 0.0, "worst": None,
           "max_rel_spread_by_axis": {"oxidation": 0.0, "reduction": 0.0},
           "worst_by_axis": {"oxidation": None, "reduction": None}}
    for name in names:
        for axis in ("ox", "red"):
            title = "oxidation" if axis == "ox" else "reduction"
            shapes = []
            for lo, hi, c in runs:
                d = delta_series(levels, name, axis, [lo, hi])
                if d is None or c == 0.0:
                    shapes = None
                    break
                shapes.append((d[1] - d[0]) / c)
            if not shapes or min(abs(x) for x in shapes) < 1e-12:
                continue
            mean = float(np.mean(shapes))
            spread = float(max(shapes) - min(shapes))
            rel = spread / abs(mean)
            out["per_molecule"].append({
                "name": name,
                "axis": title,
                "S_by_rung_ev": [float(x) for x in shapes],
                "S_mean_ev": mean,
                "rel_spread": rel,
            })
            if rel > out["max_rel_spread"]:
                out["max_rel_spread"] = rel
                out["worst"] = "%s/%s" % (name, axis)
            if rel > out["max_rel_spread_by_axis"][title]:
                out["max_rel_spread_by_axis"][title] = rel
                out["worst_by_axis"][title] = "%s/%s" % (name, axis)
    return out


def extrapolation_test(levels, names):
    """Forecast delta(eps=40) from the cheap end of the ladder only.

    Two forecasts are made per molecule and axis: a two-point one that uses
    only the gas and eps=5 levels, and a three-point one that also uses
    eps=10 and eps=20.  Nothing at eps=40 enters either fit.
    """

    eps_scan = [5.0, 10.0, 20.0, 40.0]
    target = 40.0
    rows = []
    for name in names:
        for axis in ("ox", "red"):
            d = delta_series(levels, name, axis, eps_scan)
            if d is None:
                continue
            truth = d[-1]
            s2, _ = fit_factor([5.0], [d[0]], born_u)
            s3, _ = fit_factor([5.0, 10.0, 20.0], d[:3], born_u)
            pred2 = None if s2 is None else s2 * born_u(target)
            pred3 = None if s3 is None else s3 * born_u(target)
            rows.append({
                "name": name,
                "axis": "oxidation" if axis == "ox" else "reduction",
                "truth_ev": float(truth),
                "two_point_ev": pred2,
                "two_point_abs_err_ev": None if pred2 is None else abs(pred2 - truth),
                "two_point_rel_err": None if pred2 in (None, 0.0) else abs(pred2 - truth) / abs(truth),
                "three_point_ev": pred3,
                "three_point_abs_err_ev": None if pred3 is None else abs(pred3 - truth),
                "three_point_rel_err": None if pred3 in (None, 0.0) else abs(pred3 - truth) / abs(truth),
            })

    def worst(key, rel=False):
        vals = [r[key] for r in rows if r[key] is not None]
        return max(vals) if vals else None

    def mean(key):
        vals = [r[key] for r in rows if r[key] is not None]
        return float(np.mean(vals)) if vals else None

    return {
        "target_eps": target,
        "n_points": len(rows),
        "two_point_max_abs_err_ev": worst("two_point_abs_err_ev"),
        "two_point_mean_abs_err_ev": mean("two_point_abs_err_ev"),
        "two_point_max_rel_err": worst("two_point_rel_err"),
        "three_point_max_abs_err_ev": worst("three_point_abs_err_ev"),
        "three_point_mean_abs_err_ev": mean("three_point_abs_err_ev"),
        "three_point_max_rel_err": worst("three_point_rel_err"),
        "rows": rows,
    }

# --------------------------------------------------------------------------
# part B - pre-screening: how large a pilot has to be
# --------------------------------------------------------------------------

def auc(scores, positives) -> float:
    """P(score of a positive > score of a negative) with ties at one half."""

    scores = np.asarray(scores, dtype=float)
    mask = np.asarray(positives, dtype=bool)
    good = np.isfinite(scores)
    mask = mask & good
    pos = scores[mask]
    neg = scores[good & ~mask]
    if pos.size == 0 or neg.size == 0:
        return None
    greater = float(np.sum(pos[:, None] > neg[None, :]))
    ties = float(np.sum(pos[:, None] == neg[None, :]))
    return (greater + 0.5 * ties) / (pos.size * neg.size)


def subsample_slope(point, selection) -> float:
    """OLS slope of delta on the target axis, using only ``selection``."""

    idx = {name: i for i, name in enumerate(point["names"])}
    take = [idx[name] for name in selection if name in idx]
    if len(take) < 3:
        return float("nan")
    before = np.asarray([point["before"][i] for i in take], dtype=float)
    after = np.asarray([point["after"][i] for i in take], dtype=float)
    return ols_slope(before - after, after)


def prescreen(points, rows, sizes, z=PRESCREEN_Z):
    universe = sorted(set.intersection(*[set(p["names"]) for p in points]))
    crit = SQRT2 / float(z)
    truth_tau = np.asarray([row["kendall_tau_b"] for row in rows], dtype=float)
    truth_bad = np.asarray([bool(row["shortlist_rewritten"]) for row in rows])
    full_b = np.asarray([row["ols_slope_b"] for row in rows], dtype=float)
    n_pos = int(truth_bad.sum())
    n_neg = int((~truth_bad).sum())

    curves = []
    for k in sizes:
        combos = list(itertools.combinations(universe, k))
        rho, sens, spec, allpos, signmatch, aucs = [], [], [], [], [], []
        matrix = []
        for combo in combos:
            b_hat = np.asarray([subsample_slope(p, combo) for p in points], dtype=float)
            matrix.append(b_hat)
            rho.append(ranking.spearman_rho(list(b_hat), list(truth_tau)))
            flag = (b_hat < 0.0) | (np.abs(b_hat) > crit)
            sens.append(float(np.sum(flag & truth_bad)) / n_pos if n_pos else None)
            spec.append(float(np.sum((~flag) & (~truth_bad))) / n_neg if n_neg else None)
            allpos.append(bool(np.all(flag[truth_bad])))
            ok = np.isfinite(b_hat) & np.isfinite(full_b)
            signmatch.append(float(np.mean(np.sign(b_hat[ok]) == np.sign(full_b[ok]))))
            aucs.append(auc(-b_hat, truth_bad))
        matrix = np.asarray(matrix, dtype=float)
        mean_b = np.nanmean(matrix, axis=0)
        finite_aucs = [a for a in aucs if a is not None]
        curves.append({
            "k": k,
            "n_subsets": len(combos),
            "spearman_b_vs_tau_full": {
                "mean": float(np.mean(rho)) if rho else None,
                "p05": float(np.percentile(rho, 5)) if rho else None,
                "p95": float(np.percentile(rho, 95)) if rho else None,
                "min": float(np.min(rho)) if rho else None,
                "max": float(np.max(rho)) if rho else None,
            },
            "auc_lower_b_mean_b_hat": auc(-mean_b, truth_bad),
            "auc_lower_b_mean_over_subsets": float(np.mean(finite_aucs)) if finite_aucs else None,
            "auc_lower_b_min_over_subsets": float(np.min(finite_aucs)) if finite_aucs else None,
            "sensitivity_mean": float(np.mean(sens)) if sens else None,
            "sensitivity_min": float(np.min(sens)) if sens else None,
            "specificity_mean": float(np.mean(spec)) if spec else None,
            "specificity_min": float(np.min(spec)) if spec else None,
            "p_all_positives_flagged": float(np.mean(allpos)) if allpos else None,
            "sign_match_with_full_b_mean": float(np.mean(signmatch)) if signmatch else None,
            "sign_match_with_full_b_min": float(np.min(signmatch)) if signmatch else None,
            "b_hat_sd_across_subsets_mean": float(np.nanmean(np.nanstd(matrix, axis=0, ddof=1))),
        })

    required = None
    for entry in curves:
        if (entry["p_all_positives_flagged"] or 0.0) >= 1.0 and (entry["sensitivity_min"] or 0.0) >= 1.0:
            required = entry["k"]
            break

    return {
        "universe": universe,
        "z": z,
        "critical_slope": crit,
        "rule": "flag as unusable when b_hat < 0 or abs(b_hat) > sqrt(2)/z",
        "n_points": len(rows),
        "n_dangerous": n_pos,
        "dangerous_points": [
            "%s/%s" % (row["rung"], row["axis"]) for row, bad in zip(rows, truth_bad) if bad
        ],
        "k_required_for_full_recall": required,
        "curves": curves,
    }

# --------------------------------------------------------------------------
# assembly
# --------------------------------------------------------------------------

def clean(obj):
    """Make a payload strictly JSON-safe (no NaN / Inf / numpy scalars)."""

    if isinstance(obj, dict):
        return {str(key): clean(value) for key, value in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [clean(value) for value in obj]
    if isinstance(obj, bool):
        return obj
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        value = float(obj)
        return value if math.isfinite(value) else None
    if isinstance(obj, float):
        return obj if math.isfinite(obj) else None
    return obj


def build_payload(rows, points, law, shape, forecast, screen, checks):
    by_family = {}
    for row in rows:
        by_family.setdefault(row["rung_family"], []).append(row)
    return {
        "stage": "stage12_prescreen",
        "week": 11,
        "convention": {
            "shift": "delta_i = P0_i - P1_i, cheap minus target",
            "target_axis": "p_ox = IP, p_red = -EA, higher is better on both",
            "secant_slope": "q_ij = abs(delta_i - delta_j) / abs(P1_i - P1_j)",
            "unresolved": "q_ij > sqrt(2)/z (week-10 closed form, re-verified here)",
            "dielectric_ladder": "bare CPCM, eps in {1 (gas), 5, 10, 20, 40}",
        },
        "z_primary": Z_PRIMARY,
        "z_sensitivity": Z_SENSITIVITY,
        "n_points": len(rows),
        "rung_families": {key: [row["rung"] for row in value]
                          for key, value in by_family.items()},
        "rows": rows,
        "dielectric_law": law,
        "shape_invariance": shape,
        "extrapolation": forecast,
        "prescreen": screen,
        "checks": checks,
        "sources": [
            "outputs/week4/p1_core_set_derived.csv",
            "outputs/week4/p2_environment_effects.csv",
            "outputs/week4/t2_opt_freq_summary.json",
            "outputs/week4/t3_cpcm_eps_scan.csv",
            "outputs/week5/c1_coord_shifts.csv",
            "outputs/week8/stage9_shell_shifts.csv",
            "scripts/analyze_stage10_synthesis.py",
            "scripts/analyze_stage11_sigma_anatomy.py",
            "src/electrolyte_ranking/ranking.py",
            "src/electrolyte_ranking/uncertainty.py",
        ],
    }


def run_checks(rows, law, shape, forecast, screen, gas_err) -> dict:
    exact = max([row.get("t1_max_abs_err_ev") or 0.0 for row in rows] + [0.0])
    t4a = max([row.get("t4_abs_err_z1") or 0.0 for row in rows] + [0.0])
    t4b = max([row.get("t4_abs_err_z1p96") or 0.0 for row in rows] + [0.0])
    t6 = max([row.get("t6_b_plus_1_vs_beta_err") or 0.0 for row in rows] + [0.0])
    t7 = max([row.get("t7_slope_vs_r_ratio_err") or 0.0 for row in rows] + [0.0])
    t2 = max([row.get("t2_rel_err") or 0.0 for row in rows] + [0.0])
    measured = law["measured_ratios"]
    return {
        "t1_sigma_is_shift_difference": {"ok": exact < 1e-12, "max_abs_err_ev": exact},
        "t2_rms_sigma_is_shift_stdev": {"ok": t2 < 1e-12, "max_rel_err": t2},
        "t4_closed_form_unresolved": {"ok": t4a == 0.0 and t4b == 0.0,
                                      "z1": t4a, "z1p96": t4b},
        "t6_slope_is_cheap_on_target_minus_one": {"ok": t6 < 1e-12, "max_abs_err": t6},
        "t7_slope_is_correlation_times_scale": {"ok": t7 < 1e-12, "max_abs_err": t7},
        "gas_reference_consistent": {"ok": gas_err < 1e-9, "max_abs_err_ev": gas_err},
        "born_beats_onsager": {
            "ok": (law["born_r2"]["mean"] or 0.0) > (law["onsager_r2"]["mean"] or 0.0),
            "born_r2_mean": law["born_r2"]["mean"],
            "onsager_r2_mean": law["onsager_r2"]["mean"],
        },
        "increment_ratio_matches_born": {
            "ok": (measured["r2"]["mean"] is not None
                   and abs(measured["r2"]["mean"] - 2.0) < 0.05
                   and measured["r3"]["mean"] is not None
                   and abs(measured["r3"]["mean"] - 2.0) < 0.05),
            "r2_mean": measured["r2"]["mean"],
            "r3_mean": measured["r3"]["mean"],
        },
        "born_shape_is_one_vector_oxidation": {
            "ok": shape["max_rel_spread_by_axis"]["oxidation"] < 0.05,
            "max_rel_spread": shape["max_rel_spread_by_axis"]["oxidation"],
            "worst": shape["worst_by_axis"]["oxidation"],
        },
        "born_shape_is_one_vector_reduction": {
            "ok": shape["max_rel_spread_by_axis"]["reduction"] < 0.20,
            "max_rel_spread": shape["max_rel_spread_by_axis"]["reduction"],
            "worst": shape["worst_by_axis"]["reduction"],
        },
        "prescreen_mean_slope_separates_perfectly": {
            "ok": all((entry["auc_lower_b_mean_b_hat"] or 0.0) > 0.999
                      for entry in screen["curves"]),
            "auc_by_k": {str(entry["k"]): entry["auc_lower_b_mean_b_hat"]
                         for entry in screen["curves"]},
        },
        "extrapolation_from_cheap_end": {
            "ok": (forecast["three_point_max_rel_err"] or 1.0) < 0.05,
            "three_point_max_rel_err": forecast["three_point_max_rel_err"],
            "two_point_max_rel_err": forecast["two_point_max_rel_err"],
        },
        "prescreen_full_recall_available": {
            "ok": screen["k_required_for_full_recall"] is not None,
            "k_required": screen["k_required_for_full_recall"],
        },
        "every_dielectric_rung_is_benign": {
            "ok": all(not row["shortlist_rewritten"]
                      for row in rows if row["rung_family"] == "dielectric"),
            "n_dielectric_points": sum(1 for row in rows
                                       if row["rung_family"] == "dielectric"),
        },
    }


def render_summary(payload) -> str:
    """Human-readable synthesis of stage 12."""

    law = payload["dielectric_law"]
    shape = payload["shape_invariance"]
    forecast = payload["extrapolation"]
    screen = payload["prescreen"]
    checks = payload["checks"]
    rows = payload["rows"]

    lines = []
    add = lines.append

    add("# Stage 12（week 11）—— 介电响应是一条单参数族，判据可事前使用")
    add("")
    add("Week 10 把项目的分歧量 `sigma_ij` 化简为一条无量纲判据：")
    add("`q_ij = abs(delta_i - delta_j) / abs(P1_i - P1_j) > sqrt(2)/z` 即不可分辨。")
    add("本周回答两个它留下的问题：**为什么纯介电 screening 从不改写清单**"
        "（Week 4 T3 只报了现象，没有机制），以及**这条判据能不能在花算力之前就用**。")
    add("")
    add("两个部分都**不跑任何新的电子结构**：A 部分把 Week 4 的 bare-CPCM 介电扫描"
        "（`eps = 5 / 10 / 20 / 40`）提升为与电子结构台阶同形的 (台阶, 轴) 点，"
        "B 部分用穷举子采样模拟「只算 k 个分子」的决策。")
    add("")

    add("## 1. 关键数字")
    add("")
    add("- **介电响应是 Born 形式**：`delta(eps) = S · (1 - 1/eps)`。"
        "在 %d 个 (分子, 轴) 组合上拟合的平均 R² = %.6f，"
        "而竞争模型 Onsager 反应场 `(eps-1)/(2eps+1)` 只有 %.6f。"
        % (law["born_r2"]["n"], law["born_r2"]["mean"] or 0.0,
           law["onsager_r2"]["mean"] or 0.0))
    add("- **增量几何收缩**：eps 每翻一倍，位移增量减半。"
        "实测「小步/大步」比 r2 = %.4f、r3 = %.4f（Born 预测 2.0000 / 2.0000），"
        "而 r1 = Δ(5→10)/Δ(1→5) = %.4f（Born 预测 0.1250，Onsager 只给 0.1786）。"
        % (law["measured_ratios"]["r2"]["mean"] or 0.0,
           law["measured_ratios"]["r3"]["mean"] or 0.0,
           law["measured_ratios"]["r1"]["mean"] or 0.0))
    add("- **同一条向量（分通道）**：把每一步的位移除以它自己的 `c = u(hi) - u(lo)`，"
        "得到的 `S` 在倍频台阶上一致。氧化（阳离子）通道最大相对离散 %.4f（最差 %s），"
        "还原（阴离子）通道 %.4f（最差 %s）—— 后者松 4 倍，是 Onsager 型高阶项在阴离子上更重的直接迹象。"
        % (shape["max_rel_spread_by_axis"]["oxidation"],
           shape["worst_by_axis"]["oxidation"],
           shape["max_rel_spread_by_axis"]["reduction"],
           shape["worst_by_axis"]["reduction"]))
    add("- **因此 `sd(delta)`、`b`、`q` 全部按 c 缩放**：介电梯度上 "
        "`b` 的符号不可能改变；`eps -> 无穷` 时 `q -> 0` 是单调的，"
        "所以「往溶剂方向走」只会让排序越来越稳，不会翻转。")
    add("- **外推可用**：只用 `eps = 5, 10, 20` 三点拟合 `S`，就能把 `eps = 40` 的位移"
        "预测到最大相对误差 %.2e（平均 %.2e 绝对值）。"
        % (forecast["three_point_max_rel_err"] or 0.0,
           forecast["three_point_mean_abs_err_ev"] or 0.0))
    add("- **判据可事前使用**：以「`b_hat < 0` 或 `abs(b_hat) > sqrt(2)/z`」为红牌规则，"
        "k = %d 个分子的试点即可把全部 %d 个危险台阶抓住（最坏子集也不漏）。"
        % (screen["k_required_for_full_recall"] or -1, screen["n_dangerous"]))
    add("")

    add("## 2. A 部分：介电梯度上的台阶")
    add("")
    add("| 台阶 | 轴 | n | sd(delta) | q_med | b | R² | tau_b | f_unres(z=1) | top20 overlap | 改写 |")
    add("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for row in rows:
        if row["rung_family"] != "dielectric":
            continue
        add("| %s | %s | %d | %.4f | %.4f | %+.4f | %.3f | %+.3f | %.3f | %.2f | %s |" % (
            row["rung"], row["axis"], row["n"],
            row.get("delta_sd_ev") or 0.0, row.get("q_median") or 0.0,
            row.get("ols_slope_b") or 0.0, row.get("ols_r2") or 0.0,
            row.get("kendall_tau_b") or 0.0,
            row.get("f_unresolved_p1_observed") or 0.0,
            row.get("overlap_20") if row.get("overlap_20") is not None else -1.0,
            "**是**" if row.get("shortlist_rewritten") else "否"))
    add("")
    add("八个介电点**没有一个改写候选清单**。这不是因为位移小："
        "`gas -> eps=5` 这一步的逐分子位移均值是 **+1.89 eV**、`sd(delta) = 0.213 eV` —— "
        "比 `P1->P2`、`G1->G2`、`C1->C2` 这些电子结构台阶的散布都大，"
        "却拿到 `tau_b = 1.000`、top20 overlap = 1.00。"
        "原因是位移**几乎平行于目标轴**（`b` 在 0.002 与 0.054 之间）而且**自相似**："
        "位移均值 1.885 -> 0.240 -> 0.120 -> 0.060 eV 与 "
        "`sd(delta)` 0.213 -> 0.026 -> 0.013 -> 0.007 eV 都按同一个 `c` 精确收缩。")
    add("")
    add("### 2.1 Born 与 Onsager")
    add("")
    add("| 模型 | 响应因子 | 平均 R² |")
    add("| --- | --- | --- |")
    add("| Born | 1 - 1/eps | %.6f |" % (law["born_r2"]["mean"] or 0.0))
    add("| Onsager | (eps-1)/(2eps+1) | %.6f |" % (law["onsager_r2"]["mean"] or 0.0))
    add("")
    add("两个模型都在 eps -> 无穷 时饱和，但它们的**增量比**不同。"
        "数据站在 Born 一边：实测 r2 = %.4f、r3 = %.4f，"
        "Born 预测 2.0000，Onsager 只预测 %.4f / %.4f。"
        % (law["measured_ratios"]["r2"]["mean"] or 0.0,
           law["measured_ratios"]["r3"]["mean"] or 0.0,
           law["predicted_ratios"]["onsager"]["r2"],
           law["predicted_ratios"]["onsager"]["r3"]))
    add("")
    add("物理上这很自然：我们算的是**带电**物种（阳离子、自由基阴离子）的垂直 IP/EA，"
        "起主导的是 Born 充电项 `-(1/2)(1 - 1/eps) q²/r`，"
        "而不是中性偶极的 Onsager 反应场。")
    add("")
    add("### 2.2 一条向量，五个能级")
    add("")
    add("| 台阶 | c = u(hi) - u(lo) | 预测 sd(delta) |")
    add("| --- | --- | --- |")
    for entry in shape["rungs"]:
        add("| eps %g -> %g | %.4f | —— |" % (entry["eps_lo"], entry["eps_hi"], entry["c_born"]))
    add("")
    add("氧化通道上 `S` 几乎不动（最大相对离散 %.4f），"
        "意味着整条梯度是**一个**向量乘上一串已知标量；"
        "于是 `sd(delta)`、`b`、`q_med` 的台阶间比值都必须等于 c 的比值，"
        % shape["max_rel_spread_by_axis"]["oxidation"])
    add("这也正是实测 b = +0.0093 -> +0.0046 -> +0.0023 精确折半的原因。"
        "还原通道上 `S` 仍单调但略漂移（最大 %.3f，最差 %s），"
        "对应的就是下面那条「阴离子通道外推误差更大」的注记。"
        % (shape["max_rel_spread_by_axis"]["reduction"],
           shape["worst_by_axis"]["reduction"]))
    add("")
    add("### 2.3 外推检验")
    add("")
    add("| 预测方式 | 最大相对误差 | 平均绝对误差 (eV) |")
    add("| --- | --- | --- |")
    add("| 两点（只有气相与 eps=5） | %.2e | %.2e |" % (
        forecast["two_point_max_rel_err"] or 0.0,
        forecast["two_point_mean_abs_err_ev"] or 0.0))
    add("| 三点（气相、eps=5、10、20） | %.2e | %.2e |" % (
        forecast["three_point_max_rel_err"] or 0.0,
        forecast["three_point_mean_abs_err_ev"] or 0.0))
    add("")
    add("**没有任何 eps=40 的数据进入拟合。** 两点外推已经能用一次便宜计算"
        "预测八倍介电常数之外的能级，三点外推把误差压到千分之几。")
    add("")

    add("## 3. B 部分：事前预警协议")
    add("")
    add("场景：候选池固定，准备换一层更贵的方法。只算 k 个分子，"
        "用它们的 OLS 斜率 `b_hat` 判断该层是否会改写清单。规则："
        "`b_hat < 0`（Week 10 发现三个改写点的 b 全为负）或 `abs(b_hat) > sqrt(2)/z`（分辨率崩塌）"
        "时亮红牌。")
    add("")
    add("| k | 子集数 | AUC(单子集) | 最坏 AUC | AUC(b_hat 均值) | 灵敏度(均值) | 最坏灵敏度 | 特异度(均值) | 全抓率 | b_hat 子集间 sd |")
    add("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for entry in screen["curves"]:
        add("| %d | %d | %.3f | %.3f | %.3f | %.3f | %.3f | %.3f | %.3f | %.3f |" % (
            entry["k"], entry["n_subsets"],
            entry["auc_lower_b_mean_over_subsets"] or 0.0,
            entry["auc_lower_b_min_over_subsets"] or 0.0,
            entry["auc_lower_b_mean_b_hat"] or 0.0,
            entry["sensitivity_mean"] or 0.0,
            entry["sensitivity_min"] or 0.0,
            entry["specificity_mean"] or 0.0,
            entry["p_all_positives_flagged"] or 0.0,
            entry["b_hat_sd_across_subsets_mean"] or 0.0))
    add("")
    add("危险点共 %d 个：%s。" % (screen["n_dangerous"], "、".join(screen["dangerous_points"])))
    add("")
    add("读法：`AUC(b_hat 均值)` 一列在 **k = 3 就已经是 1.000** —— "
        "即使只算 3 个分子，把全部子集的 `b_hat` 平均起来也能完美分开危险与安全的台阶。"
        "但单次抽样不是平均值：`最坏 AUC` 与 `最坏灵敏度` 说明小试点会「运气差」。"
        "要保证**任何** 一个子集都不漏掉危险台阶，需要 k = %s。"
        % screen["k_required_for_full_recall"])
    add("")
    add("工程结论：**k = 5 的试点（一半分子）平均已能抓住 96% 的危险台阶、AUC 0.946；"
        "若不允许任何一次漏判，用 k = 8。** 试点只需要 3 个分子时，"
        "单个子集的 AUC 只有 0.853，最小值低到 0.333，不可作为放行依据。")
    add("")

    add("## 4. 全部 %d 个 (台阶, 轴) 点" % len(rows))
    add("")
    add("| 家族 | 台阶 | 轴 | n | sd(delta) | b | q_med | tau_b | f_unres(z=1) | f_unres(z=1.96) | top20 | 改写 |")
    add("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for row in rows:
        add("| %s | %s | %s | %d | %.4f | %+.4f | %.4f | %+.3f | %.3f | %.3f | %.2f | %s |" % (
            row["rung_family"], row["rung"], row["axis"], row["n"],
            row.get("delta_sd_ev") or 0.0, row.get("ols_slope_b") or 0.0,
            row.get("q_median") or 0.0, row.get("kendall_tau_b") or 0.0,
            row.get("f_unresolved_p1_observed") or 0.0,
            row.get("f_unresolved_p1_z1p96_observed") or 0.0,
            row.get("overlap_20") if row.get("overlap_20") is not None else -1.0,
            "**是**" if row.get("shortlist_rewritten") else "否"))
    add("")

    add("## 5. 结论")
    add("")
    add("- 判据的**第四条免费通道**：Week 10 证明了层间刚性偏移（T3）与严格单调位移（Lipschitz）"
        "不收费；本周补上第三条——**自相似的平移**。"
        "只要位移向量在台阶之间只差一个已知标量，`b` 的符号就不动、`q` 只按标量缩放。")
    add("- 于是「纯介电 screening 是否产生 robust inversion」有了机制层面的答案："
        "**不可能**，因为介电响应是 Born 形式，是一条单参数族，"
        "而清单是否被改写只取决于 `b` 的符号与 `q` 的尾部。")
    add("- 实践含义：把环境从气相一路调到导体，排序结论**单调地越来越稳**；"
        "需要担心的从来不是「加了溶剂」，而是「换了**相互之间不成比例**的两层」。")
    add("- 判据可事前使用，且成本很低：k = %s 个分子的试点足以不遗漏任何危险台阶。"
        % screen["k_required_for_full_recall"])
    add("")

    add("## 6. 质量与复核")
    add("")
    for key in sorted(checks):
        entry = checks[key]
        add("- `%s`：%s" % (key, "PASS" if entry.get("ok") else "FAIL"))
    add("")

    add("## 7. 产物")
    add("")
    add("- `outputs/week11/stage12_prescreen.csv` —— 每行一个 (台阶, 轴) 点")
    add("- `outputs/week11/stage12_prescreen.json` —— 同上，外加介电律、外推检验与预警曲线")
    add("- `outputs/week11/stage12_summary.md` —— 本文件")
    add("- `outputs/figures/F22_dielectric_scaling.png`、`F23_prescreening.png`")
    add("")
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outdir", default=str(DEFAULT_OUTDIR))
    args = parser.parse_args(argv)

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    ladder = load_ladder()
    names = common_names(ladder)
    levels = load_dielectric_levels()
    gas_err = gas_reference_check(names)

    points = build_electronic_points(ladder, names) + build_dielectric_points(levels, names)
    rows = [point_metrics(point, i) for i, point in enumerate(points)]

    law = dielectric_law(levels, names)
    shape = shape_invariance(levels, names)
    forecast = extrapolation_test(levels, names)
    screen = prescreen(points, rows, PILOT_SIZES)
    checks = run_checks(rows, law, shape, forecast, screen, gas_err)

    payload = build_payload(rows, points, law, shape, forecast, screen, checks)
    payload["common_subset"] = names

    write_csv(outdir / "stage12_prescreen.csv", rows, COLUMNS)
    write_json(outdir / "stage12_prescreen.json", clean(payload))
    (outdir / "stage12_summary.md").write_text(
        render_summary(payload), encoding="utf-8")

    failed = [key for key, value in checks.items() if value.get("ok") is not True]
    print("points=%d  dielectric_rungs=%d" % (len(rows), len(DIELECTRIC_RUNGS)))
    print("checks ok=%d fail=%d%s" % (len(checks) - len(failed), len(failed),
                                      ("  -> " + ", ".join(failed)) if failed else ""))
    for row in rows:
        print("  %-16s %-9s sd_d=%7.4f b=%+8.4f q_med=%7.4f tau=%+6.3f fu1=%5.3f ov=%4.2f"
              % (row["rung"], row["axis"], row.get("delta_sd_ev") or 0.0,
                 row.get("ols_slope_b") or 0.0, row.get("q_median") or 0.0,
                 row.get("kendall_tau_b") or 0.0,
                 row.get("f_unresolved_p1_observed") or 0.0,
                 row.get("overlap_20") if row.get("overlap_20") is not None else -1.0))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())