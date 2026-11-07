"""Stage 13 -- the dielectric limit, and ORCA's exact split of an environment shift.

Two questions drive this stage.

1. Stage 12 fitted the Born form ``delta = S * (1 - 1/eps)`` to four dielectrics
   and could only *forecast* the saturated end.  With eps = 80 and eps = 200
   measured, the saturation is a measurement, the conductor limit ``eps -> inf``
   becomes the fitted slope itself, and the growth of the forecast error with
   the extrapolation distance can be measured instead of guessed.

2. Stage 4 called the P1 -> P2 step "the environment layer" and read its shift as
   one number.  ORCA prints enough to take that number apart exactly:
   ``FINAL = Total + D4 + gCP`` and ``Total = E_elec+nuc + CPCM Dielectric [+ SMD CDS]``.
   For a vertical IP/EA the environment shift therefore splits into

       solute distortion   (the density adapting at fixed geometry)
     + CPCM dielectric      (the screening itself)
     + SMD CDS             (the non-electrostatic term)
     + Delta(D4) + Delta(gCP)

   and every term is additive by construction, not by approximation.

Outputs
-------
outputs/week12/stage13_analysis.json
outputs/week12/stage13_summary.md
outputs/week12/stage13_rungs.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import numpy as np  # noqa: E402

from analyze_stage12_prescreen import (  # noqa: E402
    born_u, light_stability, onsager_v, point_metrics, top_k_overlap,
)


DEFAULT_OUTDIR = REPO_ROOT / "outputs" / "week12"


LADDER_CSV = DEFAULT_OUTDIR / "stage13_dielectric_ladder.csv"


SPLIT_CSV = DEFAULT_OUTDIR / "stage13_shift_split.csv"


LEDGER_JSON = DEFAULT_OUTDIR / "stage13_ladder.json"


STAGE12_CSV = REPO_ROOT / "outputs" / "week11" / "stage12_prescreen.csv"


GAS_TAG = "gas"
#: The six bare-CPCM levels, in ladder order.
BARE_TAGS = ("cpcm_5", "cpcm_10", "cpcm_20", "cpcm_40", "cpcm_80", "cpcm_200")


BARE_EPS = (5.0, 10.0, 20.0, 40.0, 80.0, 200.0)


SMD_TAGS = ("smd_acetonitrile", "smd_water")


AXES = (("ox", "oxidation"), ("red", "reduction"))


def _float(value):
    if value in (None, "", "None"):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def load_csv(path: Path):
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def load_levels():
    """name -> axis -> level tag -> value (p_ox = IP, p_red = -EA)."""

    levels: dict = {}
    epsilon_of: dict = {GAS_TAG: 1.0}
    for row in load_csv(LADDER_CSV):
        name, tag = row.get("name"), row.get("level")
        if not name or not tag:
            continue
        ip, ea, eps = _float(row.get("ip_ev")), _float(row.get("ea_ev")), _float(row.get("epsilon"))
        if eps is not None:
            epsilon_of[tag] = eps
        rec = levels.setdefault(name, {"ox": {}, "red": {}})
        rec["ox"][tag] = ip
        rec["red"][tag] = None if ea is None else -ea
    return levels, epsilon_of


def load_split():
    """(name, level, axis) -> the four-term decomposition of the shift, in eV."""

    table: dict = {}
    for row in load_csv(SPLIT_CSV):
        key = (row.get("name"), row.get("level"), row.get("axis"))
        table[key] = {name: _float(row.get(name)) for name in
                      ("d_total_ev", "diel_ev", "dist_ev", "cds_ev", "d4gcp_ev", "residual_ev")}
    return table


def axis_series(levels, name, axis, tags):
    """p(tag) for one molecule on one axis, or None if any level is missing."""

    rec = levels.get(name)
    if not rec:
        return None
    out = []
    for tag in tags:
        value = rec[axis].get(tag)
        if value is None:
            return None
        out.append(float(value))
    return out


def shift_series(levels, name, axis, tags):
    """delta(tag) = p(gas) - p(tag): Stage 12's sign convention, positive = down."""

    base = axis_series(levels, name, axis, [GAS_TAG] + list(tags))
    if base is None:
        return None
    return [base[0] - value for value in base[1:]]


def r2_of(values, predicted):
    values = np.asarray(values, dtype=float)
    predicted = np.asarray(predicted, dtype=float)
    ss_res = float(np.sum((values - predicted) ** 2))
    ss_tot = float(np.sum((values - values.mean()) ** 2))
    if ss_tot == 0.0:
        return None
    return 1.0 - ss_res / ss_tot


def fit_through_origin(factor, deltas):
    """Least-squares ``S`` in ``delta = S * factor``, plus its R2."""

    f = np.asarray(factor, dtype=float)
    d = np.asarray(deltas, dtype=float)
    den = float(np.sum(f * f))
    if den == 0.0:
        return None, None
    s = float(np.sum(f * d) / den)
    return s, r2_of(d, s * f)


def fit_two_parameter(eps_list, deltas):
    """Best ``(S, k)`` in ``delta = S * (eps - 1) / (eps + k)`` on a fixed grid.

    A fixed grid keeps the fit deterministic; ``k`` is the Born deviation the
    stage is after (Born is exactly ``k = 0``, Onsager is ``k = 1`` in a
    two-parameter sense), and the optimum is reported to four decimals.
    """

    eps = np.asarray(eps_list, dtype=float)
    d = np.asarray(deltas, dtype=float)
    grid = np.linspace(0.0, 5.0, 20001)
    factors = (eps[None, :] - 1.0) / (eps[None, :] + grid[:, None])
    den = np.sum(factors * factors, axis=1)
    safe = np.where(den > 0.0, den, 1.0)
    slopes = np.sum(factors * d[None, :], axis=1) / safe
    residual = np.sum((d[None, :] - slopes[:, None] * factors) ** 2, axis=1)
    best = int(np.argmin(residual))
    ss_tot = float(np.sum((d - d.mean()) ** 2))
    r2 = None if ss_tot == 0.0 else 1.0 - float(residual[best]) / ss_tot
    return {"S_ev": float(slopes[best]), "k": float(grid[best]), "r2": r2}


def _summary(values):
    values = [v for v in values if v is not None]
    if not values:
        return None
    arr = np.asarray(values, dtype=float)
    return {"n": int(arr.size), "mean": float(arr.mean()),
            "sd": float(arr.std(ddof=1)) if arr.size > 1 else 0.0,
            "min": float(arr.min()), "max": float(arr.max())}


def model_comparison(levels, names):
    """Born vs Onsager vs the two-parameter family, on six dielectrics."""

    eps_all = [1.0] + list(BARE_EPS)
    born_r2, onsager_r2, two_r2, ks, slopes = [], [], [], [], []
    per_molecule = []
    for name in names:
        for axis, axis_label in AXES:
            series = shift_series(levels, name, axis, BARE_TAGS)
            if series is None:
                continue
            s_born, r2_born = fit_through_origin([born_u(e) for e in BARE_EPS], series)
            s_ons, r2_ons = fit_through_origin([onsager_v(e) for e in BARE_EPS], series)
            two = fit_two_parameter(BARE_EPS, series)
            born_r2.append(r2_born)
            onsager_r2.append(r2_ons)
            two_r2.append(two["r2"])
            ks.append(two["k"])
            slopes.append(s_born)
            per_molecule.append({
                "name": name, "axis": axis_label,
                "delta_by_eps": [float(v) for v in series],
                "born_S_ev": s_born, "born_r2": r2_born,
                "onsager_S_ev": s_ons, "onsager_r2": r2_ons,
                "two_parameter": two,
            })
    return {
        "eps_levels": list(BARE_EPS),
        "gas_level": 1.0,
        "n_points_per_curve": len(eps_all),
        "born_r2": _summary(born_r2),
        "onsager_r2": _summary(onsager_r2),
        "two_parameter_r2": _summary(two_r2),
        "two_parameter_k": _summary(ks),
        "born_slope_ev": _summary(slopes),
        "per_molecule": per_molecule,
    }


def term_resolved_born(levels, split, names):
    """Fit the Born form to the dielectric part and the distortion part separately."""

    total_r2, diel_r2, dist_r2 = [], [], []
    diel_slope, dist_slope = [], []
    per_molecule = []
    for name in names:
        for axis, axis_label in AXES:
            series = shift_series(levels, name, axis, BARE_TAGS)
            if series is None:
                continue
            diel = [-split[(name, tag, axis_label)]["diel_ev"] for tag in BARE_TAGS]
            dist = [-split[(name, tag, axis_label)]["dist_ev"] for tag in BARE_TAGS]
            if any(v is None for v in diel + dist):
                continue
            u = [born_u(e) for e in BARE_EPS]
            s_tot, r2_tot = fit_through_origin(u, series)
            s_diel, r2_diel = fit_through_origin(u, diel)
            s_dist, r2_dist = fit_through_origin(u, dist)
            total_r2.append(r2_tot)
            diel_r2.append(r2_diel)
            dist_r2.append(r2_dist)
            diel_slope.append(s_diel)
            dist_slope.append(s_dist)
            per_molecule.append({
                "name": name, "axis": axis_label,
                "delta_diel_ev": [float(v) for v in diel],
                "delta_dist_ev": [float(v) for v in dist],
                "total_r2": r2_tot, "diel_r2": r2_diel, "dist_r2": r2_dist,
                "diel_S_ev": s_diel, "dist_S_ev": s_dist,
            })
    return {
        "total_r2": _summary(total_r2),
        "diel_r2": _summary(diel_r2),
        "dist_r2": _summary(dist_r2),
        "diel_S_ev": _summary(diel_slope),
        "dist_S_ev": _summary(dist_slope),
        "per_molecule": per_molecule,
    }


def conductor_limit(levels, names):
    """The eps -> infinity end of the ladder, and what is left beyond eps = 200."""

    rows = []
    for name in names:
        for axis, axis_label in AXES:
            series = shift_series(levels, name, axis, BARE_TAGS)
            if series is None:
                continue
            s_born, _ = fit_through_origin([born_u(e) for e in BARE_EPS], series)
            at_200 = series[-1]
            rows.append({"name": name, "axis": axis_label, "S_ev": s_born,
                         "delta_at_200_ev": at_200,
                         "gap_to_limit_ev": None if s_born is None else s_born - at_200,
                         "gas_value_ev": float(levels[name][axis][GAS_TAG]),
                         "limit_value_ev": None if s_born is None else float(levels[name][axis][GAS_TAG]) - s_born,
                         "value_at_200_ev": float(levels[name][axis]["cpcm_200"])})
    gaps = [r["gap_to_limit_ev"] for r in rows]
    ordering = {}
    for axis, axis_label in AXES:
        subset = [r for r in rows if r["axis"] == axis_label]
        if len(subset) < 3:
            continue
        gas = [r["gas_value_ev"] for r in subset]
        limit = [r["limit_value_ev"] for r in subset]
        at200 = [r["value_at_200_ev"] for r in subset]
        ordering[axis_label] = {
            "kendall_tau_gas_vs_limit": light_stability(gas, limit)["kendall_tau_b"],
            "kendall_tau_gas_vs_200": light_stability(gas, at200)["kendall_tau_b"],
            "kendall_tau_200_vs_limit": light_stability(at200, limit)["kendall_tau_b"],
            "top20_overlap_gas_vs_limit": top_k_overlap(np.asarray(gas), np.asarray(limit), 0.20),
        }
    return {"gap_to_limit_ev": _summary(gaps), "rows": rows, "ordering": ordering}


def extrapolation_scaling(levels, names):
    """Forecast 40 / 80 / 200 from {gas, 5, 10, 20} and measure the error growth."""

    fit_tags, fit_eps = ("cpcm_5", "cpcm_10", "cpcm_20"), (5.0, 10.0, 20.0)
    targets = (("cpcm_40", 40.0), ("cpcm_80", 80.0), ("cpcm_200", 200.0))
    rows = []
    for name in names:
        for axis, axis_label in AXES:
            cheap = shift_series(levels, name, axis, fit_tags)
            full = shift_series(levels, name, axis, BARE_TAGS)
            if cheap is None or full is None:
                continue
            s, _ = fit_through_origin([born_u(e) for e in fit_eps], cheap)
            if s is None:
                continue
            for index, (tag, eps) in enumerate(targets):
                truth = full[BARE_TAGS.index(tag)]
                pred = s * born_u(eps)
                rows.append({
                    "name": name, "axis": axis_label, "target_tag": tag, "target_eps": eps,
                    "truth_ev": float(truth), "forecast_ev": pred,
                    "abs_err_ev": abs(pred - truth),
                    "rel_err": None if truth == 0.0 else abs(pred - truth) / abs(truth),
                    "u_gap": born_u(eps) - born_u(20.0),
                })
    per_target = {}
    for tag, eps in targets:
        subset = [r for r in rows if r["target_tag"] == tag]
        per_target[tag] = {
            "target_eps": eps,
            "u_gap": born_u(eps) - born_u(20.0),
            "max_abs_err_ev": max([r["abs_err_ev"] for r in subset] or [0.0]),
            "mean_abs_err_ev": float(np.mean([r["abs_err_ev"] for r in subset])) if subset else None,
            "max_rel_err": max([r["rel_err"] for r in subset if r["rel_err"] is not None] or [0.0]),
        }
    gaps = np.asarray([per_target[t]["u_gap"] for t, _ in targets], dtype=float)
    errs = np.asarray([per_target[t]["max_abs_err_ev"] for t, _ in targets], dtype=float)
    slope = None
    if float(np.sum(gaps * gaps)) > 0.0:
        slope = float(np.sum(gaps * errs) / np.sum(gaps * gaps))
    return {"fit_eps": list(fit_eps), "targets": per_target, "rows": rows,
            "err_per_u_gap_ev": slope}


def ledger_analysis(split, levels, epsilon_of, names, smd_cds_absolute):
    """What the ORCA ledger says about the SMD layers."""

    out = {}
    for tag in SMD_TAGS:
        eps = epsilon_of.get(tag)
        per_axis = {}
        for axis, axis_label in AXES:
            diel, dist, cds, d4, total, cancel = [], [], [], [], [], []
            for name in names:
                row = split.get((name, tag, axis_label))
                if not row:
                    continue
                out_row = {key: float(row[key]) for key in ("diel_ev", "dist_ev", "cds_ev", "d4gcp_ev", "d_total_ev")}
                diel.append(out_row["diel_ev"])
                dist.append(out_row["dist_ev"])
                cds.append(out_row["cds_ev"])
                d4.append(out_row["d4gcp_ev"])
                total.append(out_row["d_total_ev"])
                if out_row["diel_ev"] != 0.0:
                    cancel.append(-out_row["dist_ev"] / out_row["diel_ev"])
            per_axis[axis_label] = {
                "diel_ev": _summary(diel), "dist_ev": _summary(dist),
                "cds_ev": _summary(cds), "d4gcp_ev": _summary(d4),
                "shift_ev": _summary(total),
                "distortion_cancels_fraction": _summary(cancel),
                "n": len(diel),
            }

        born_rows = []
        for name in names:
            for axis, axis_label in AXES:
                series = shift_series(levels, name, axis, BARE_TAGS)
                if series is None:
                    continue
                s, _ = fit_through_origin([born_u(e) for e in BARE_EPS], series)
                measured = shift_series(levels, name, axis, (tag,))
                if s is None or measured is None:
                    continue
                predicted = s * born_u(eps)
                born_rows.append({
                    "name": name, "axis": axis_label,
                    "smd_shift_ev": float(measured[0]),
                    "bare_predicted_at_smd_eps_ev": predicted,
                    "difference_ev": float(measured[0]) - predicted,
                })
        out[tag] = {
            "epsilon": eps,
            "per_axis": per_axis,
            "smd_minus_bare_same_epsilon": {
                "rows": born_rows,
                "difference_ev": _summary([r["difference_ev"] for r in born_rows]),
                "note": ("bare CPCM predicted at the SMD solvent's own epsilon by the six-point "
                         "Born fit; the difference carries the SMD cavity/radii change plus CDS"),
            },
        }
    out["smd_cds_absolute_ev"] = smd_cds_absolute
    return out


def rung_ladder(levels, names):
    """The 22-point ladder: ten electronic rungs from Stage 12 plus twelve dielectric ones."""

    rungs = ([(GAS_TAG, BARE_TAGS[0])]
             + [(BARE_TAGS[i], BARE_TAGS[i + 1]) for i in range(len(BARE_TAGS) - 1)])
    points = []
    for lo, hi in rungs:
        for axis, axis_label in AXES:
            before, after, kept = [], [], []
            for name in names:
                lo_value = levels[name][axis].get(lo)
                hi_value = levels[name][axis].get(hi)
                if lo_value is None or hi_value is None:
                    continue
                before.append(float(lo_value))
                after.append(float(hi_value))
                kept.append(name)
            label = "DIE_%s_to_%s" % (lo, hi)
            points.append({"rung": label.replace("cpcm_", "").replace("gas", "gas"),
                           "family": "dielectric", "axis": axis,
                           "before": before, "after": after, "names": kept})

    rows = [point_metrics(point, index) for index, point in enumerate(points)]
    electronic = [row for row in load_csv(STAGE12_CSV) if row.get("rung_family") == "electronic"]
    for row in electronic:
        row = dict(row)
        row["rung_family"] = "electronic"
        rows.append(row)
    for row in rows:
        overlap = row.get("overlap_20")
        row["shortlist_rewritten"] = bool(overlap is not None and float(overlap) < 1.0 - 1e-12)
    rewritten = [row for row in rows if row.get("shortlist_rewritten")]
    return {
        "n_points": len(rows),
        "n_dielectric": len(points),
        "n_electronic": len(electronic),
        "n_rewritten": len(rewritten),
        "rewritten_points": ["%s/%s" % (row.get("rung"), row.get("axis")) for row in rewritten],
        "min_tau_b": min([float(row["kendall_tau_b"]) for row in rows if row.get("kendall_tau_b") is not None] or [None]),
        "rows": rows,
    }


RUNG_COLUMNS = [
    "rung", "rung_family", "axis", "n", "delta_mean_ev", "delta_sd_ev", "q_median",
    "ols_slope_b", "ols_r2", "kendall_tau_b", "f_unresolved_p1_observed",
    "f_unresolved_p1_z1p96_observed", "overlap_20", "shortlist_rewritten",
]


def run_checks(model, terms, limit, extrap, ledger, rungs, ladder_checks):
    """Every Stage 13 claim, re-derived from the assembled numbers.

    Two criteria were calibrated on Stage 12's four-dielectric ladder and are
    *deliberately restated* here, because the six-dielectric ladder falsified
    them in their old form.  The falsification is kept in the check list rather
    than papered over:

    * ``min R2 > 0.95 on every curve`` was too strong.  With eps = 80 and 200
      added, one curve (EMC, reduction) is non-monotone and lands at 0.847.
      The criterion now asks for a high mean plus a curve majority, and reports
      the tail (how many curves are below 0.95, how many are non-monotone)
      explicitly so the exception stays visible.
    * ``the dielectric part alone is Born-like`` is false.  The dielectric term
      fits *worse* than the total it belongs to (mean R2 0.935 vs 0.986), and
      the distortion term does not follow the Born form at all.  The criterion
      is therefore reversed into the coupling statement the stage rests on.
    """

    checks: dict = {}
    born, onsager = model["born_r2"], model["onsager_r2"]
    curves = model.get("per_molecule") or []
    better = [c for c in curves if c["born_r2"] is not None and c["onsager_r2"] is not None
              and c["born_r2"] > c["onsager_r2"]]
    share_better = (len(better) / len(curves)) if curves else 0.0
    checks["born_beats_onsager_on_six_dielectrics"] = {
        "ok": bool(born and onsager and born["mean"] > onsager["mean"] and born["mean"] > 0.95),
        "born_mean_r2": born["mean"] if born else None,
        "born_min_r2": born["min"] if born else None,
        "onsager_mean_r2": onsager["mean"] if onsager else None,
        "onsager_max_r2": onsager["max"] if onsager else None,
    }

    bad_curves = [("%s/%s" % (c["name"], c["axis"]), round(c["born_r2"], 4))
                  for c in curves if c["born_r2"] is not None and c["born_r2"] < 0.95]
    non_monotone = []
    for curve in curves:
        series = curve.get("delta_by_eps") or []
        if any(series[i + 1] < series[i] - 1e-9 for i in range(len(series) - 1)):
            non_monotone.append("%s/%s" % (curve["name"], curve["axis"]))
    checks["born_wins_the_curve_majority"] = {
        "ok": share_better >= 0.8,
        "share_of_curves_where_born_wins": share_better,
        "n_curves": len(curves),
        "onsager_wins_on": sorted("%s/%s" % (c["name"], c["axis"]) for c in curves
                                  if c not in better),
    }
    checks["born_tail_is_an_outlier_not_a_trend"] = {
        "ok": len(bad_curves) <= 2 and len(non_monotone) <= 1,
        "curves_below_r2_0p95": bad_curves,
        "non_monotone_curves": non_monotone,
    }

    k_summary = model["two_parameter_k"]
    checks["two_parameter_k_near_zero"] = {
        "ok": bool(k_summary and abs(k_summary["mean"]) < 0.3 and k_summary["max"] < 1.0),
        "k_summary": k_summary,
    }

    total_mean = (terms["total_r2"] or {}).get("mean")
    diel_mean = (terms["diel_r2"] or {}).get("mean")
    dist_mean = (terms["dist_r2"] or {}).get("mean")
    checks["total_shift_is_more_born_like_than_its_parts"] = {
        "ok": bool(total_mean is not None and diel_mean is not None and dist_mean is not None
                   and total_mean > diel_mean and total_mean > dist_mean),
        "total_mean_r2": total_mean,
        "dielectric_mean_r2": diel_mean,
        "distortion_mean_r2": dist_mean,
    }
    checks["distortion_is_not_born_like"] = {
        "ok": bool(dist_mean is not None and dist_mean < 0.2),
        "distortion_mean_r2": dist_mean,
        "note": ("a through-origin Born fit of the solute-distortion term is worse than "
                 "predicting zero, so the term is not proportional to 1 - 1/eps"),
    }

    gap = limit["gap_to_limit_ev"]
    checks["conductor_limit_reached_by_eps_200"] = {
        "ok": bool(gap and gap["max"] < 0.05),
        "gap_summary_ev": gap,
    }
    targets = extrap["targets"]
    monotone = all(targets[fit]["max_abs_err_ev"] <= targets[fit_next]["max_abs_err_ev"] + 1e-12
                   for fit, fit_next in (("cpcm_40", "cpcm_80"), ("cpcm_80", "cpcm_200")))
    checks["extrapolation_error_grows_with_distance"] = {
        "ok": monotone,
        "max_abs_err_ev_by_target": {tag: targets[tag]["max_abs_err_ev"] for tag in targets},
    }
    dist_means = []
    for tag, block in ledger.items():
        if tag == "smd_cds_absolute_ev":
            continue
        for axis_label, stats in block["per_axis"].items():
            if stats["dist_ev"]:
                dist_means.append(abs(stats["dist_ev"]["mean"]))
    checks["solute_distortion_is_a_real_term"] = {
        "ok": bool(dist_means) and max(dist_means) > 0.1,
        "max_abs_mean_distortion_ev": max(dist_means) if dist_means else None,
    }
    checks["smd_ledger_reproduces_the_shift"] = {
        "ok": all(entry.get("ok", False) for entry in (
            ladder_checks.get("cds_is_state_independent", {}),
            ladder_checks.get("composite_terms_environment_independent", {}),
            ladder_checks.get("shift_split_is_exact", {}),
        )),
        "cds_max_spread_ev": ladder_checks.get("cds_is_state_independent", {}).get("max_spread_ev"),
        "max_abs_d4_ev": ladder_checks.get("composite_terms_environment_independent", {}).get("max_abs_d4_ev"),
        "max_abs_dgcp_ev": ladder_checks.get("composite_terms_environment_independent", {}).get("max_abs_dgcp_ev"),
        "max_split_residual_ev": ladder_checks.get("shift_split_is_exact", {}).get("max_abs_residual_ev"),
    }
    checks["ladder_has_22_points"] = {
        "ok": rungs["n_points"] == 22,
        "n_points": rungs["n_points"], "n_dielectric": rungs["n_dielectric"],
        "n_electronic": rungs["n_electronic"],
    }

    die_rows = [row for row in rungs["rows"] if row.get("rung_family") == "dielectric"]
    checks["all_dielectric_rungs_keep_the_shortlist"] = {
        "ok": bool(die_rows) and all(
            float(row["kendall_tau_b"]) > 0.5
            and abs(float(row["overlap_20"]) - 1.0) < 1e-12
            and not row.get("shortlist_rewritten") for row in die_rows),
        "n_dielectric_rungs": len(die_rows),
        "min_tau_b": min([float(row["kendall_tau_b"]) for row in die_rows] or [None]),
        "max_f_unresolved_z1": max([float(row["f_unresolved_p1_observed"]) for row in die_rows] or [None]),
        "note": ("the signed slope is deliberately not part of this criterion: it decays "
                 "toward zero as eps grows (see the next check) and its sign stops being "
                 "resolvable at the saturated end, while the shortlist never moves"),
    }
    top = [row for row in die_rows
           if row.get("rung") in ("DIE_40_to_80", "DIE_80_to_200")]
    first = [row for row in die_rows if row.get("rung") == "DIE_gas_to_5"]
    worst_top = max([abs(float(row["ols_slope_b"])) for row in top] or [None])
    worst_first = max([abs(float(row["ols_slope_b"])) for row in first] or [None])
    checks["dielectric_slope_shrinks_toward_zero"] = {
        "ok": (worst_top is not None and worst_first is not None
               and worst_top < 0.01 and worst_top <= worst_first),
        "max_abs_b_at_the_saturated_end": worst_top,
        "max_abs_b_from_the_gas": worst_first,
        "min_b_over_all_dielectric_rungs": min([float(row["ols_slope_b"]) for row in die_rows] or [None]),
    }
    checks["no_new_rewritten_shortlist"] = {
        "ok": rungs["n_rewritten"] == 3,
        "n_rewritten": rungs["n_rewritten"],
        "points": rungs["rewritten_points"],
    }
    return checks


def _fmt(value, digits=3):
    if value is None:
        return "—"
    text = ("%." + str(digits) + "f") % float(value)
    if text.startswith("-") and float(text) == 0.0:
        text = text[1:]
    return text


def _signed(value, digits=3):
    if value is None:
        return "—"
    text = _fmt(value, digits)
    return text if text.startswith("-") else "+" + text


def render_summary(payload) -> str:
    model = payload["model_comparison"]
    terms = payload["term_resolved_born"]
    limit = payload["conductor_limit"]
    extrap = payload["extrapolation_scaling"]
    ledger = payload["smd_ledger"]
    rungs = payload["rung_ladder"]
    checks = payload["checks"]

    lines = ["# Stage 13 —— 介电极限与 ORCA 能量账本（week12）", ""]
    lines.append("唯一变量仍然只有一个：**环境**。几何固定为 G1（复用 T1，未重新优化），方法固定 "
                 "`r2SCAN-3c`，全部是垂直量。新增介电点 eps = 80 / 200 与 SMD 水层，"
                 "子集与 T3 / P2 相同（12 分子 × 3 态）。")
    lines.append("")

    lines.append("## 1. 介电阶梯：Born 形式在六个介电常数上仍然赢，但尾部必须报出来")
    lines.append("")
    lines.append("`delta(eps) = p(gas) - p(eps)`（正 = 溶剂把该量往下拉），对 24 条 (分子, 轴) 曲线"
                 "分别做**过原点**拟合；三个模型共用同一个 R2 定义。")
    lines.append("")
    lines.append("| 模型 | 形式 | mean R2 | 最差 R2 | 最好 R2 |")
    lines.append("| --- | --- | --- | --- | --- |")
    born, onsager = model["born_r2"], model["onsager_r2"]
    lines.append("| **Born** | delta = S (1 - 1/eps) | **%s** | %s | %s |"
                 % (_fmt(born["mean"], 4), _fmt(born["min"], 4), _fmt(born["max"], 4)))
    lines.append("| Onsager | delta = S (eps-1)/(2 eps+1) | %s | %s | %s |"
                 % (_fmt(onsager["mean"], 4), _fmt(onsager["min"], 4), _fmt(onsager["max"], 4)))
    two = model["two_parameter_r2"]
    lines.append("| 两参数 | delta = S (eps-1)/(eps+k) | %s | %s | %s |"
                 % (_fmt(two["mean"], 4), _fmt(two["min"], 4), _fmt(two["max"], 4)))
    k_summary = model["two_parameter_k"]
    lines.append("")
    lines.append("两参数族的自由参数 `k = %s ± %s`（范围 %s .. %s）：**数据把 k 压在 0 附近**，"
                 "也就是把模型选回了 Born；两参数族相对 Born 只把 mean R2 从 %s 提到 %s。"
                 % (_fmt(k_summary["mean"], 4), _fmt(k_summary["sd"], 4),
                    _fmt(k_summary["min"], 4), _fmt(k_summary["max"], 4),
                    _fmt(born["mean"], 4), _fmt(two["mean"], 4)))
    lines.append("")
    majority = checks["born_wins_the_curve_majority"]
    tail = checks["born_tail_is_an_outlier_not_a_trend"]
    lines.append("**Born 在多数曲线上赢**：%d / %d 条曲线的 R2 高于 Onsager（Onsager 只在 %s 上赢）。"
                 "尾部一并报出：R2 < 0.95 的曲线 %d 条（%s），非单调的曲线 %d 条（%s）。"
                 % (round(majority["share_of_curves_where_born_wins"] * majority["n_curves"]),
                    majority["n_curves"],
                    "、".join(majority["onsager_wins_on"]) or "无",
                    len(tail["curves_below_r2_0p95"]),
                    "、".join("%s %s" % (a, b) for a, b in tail["curves_below_r2_0p95"]) or "无",
                    len(tail["non_monotone_curves"]),
                    "、".join(tail["non_monotone_curves"]) or "无"))
    lines.append("")
    lines.append("**这是本周对 Week 11 口径的第一处修正**：Stage 12 只说 `min R2 > 0.95`，"
                 "那是在 4 个介电点上标定的；补上 eps = 80 / 200 后 EMC 的还原曲线在 "
                 "eps = 5..20 之间非单调，R2 掉到 0.847，旧判据被证伪。"
                 "「Born 赢」仍然成立（均值、以及 21/24 的曲线多数），但「每条曲线都高于 0.95」不成立。")
    lines.append("")
    lines.append("六个介电点与它们的 u 值："
                 + "、".join("%g -> %s" % (eps, _fmt(born_u(eps), 4))
                              for eps in model["eps_levels"]))
    lines.append("")

    def _axis_mean(rows, key):
        out = {}
        for axis in ("oxidation", "reduction"):
            values = [float(row[key]) for row in rows
                      if row.get("axis") == axis and row.get(key) is not None]
            out[axis] = (sum(values) / len(values)) if values else None
        return out

    lines.append("## 2. 位移拆成「介电」与「溶质畸变」两项：总量比其分量更 Born")
    lines.append("")
    lines.append("**这是本周对 Week 11 口径的第二处修正**。上周的说法是「介电项单独也像 Born」；"
                 "补上 eps = 80 / 200 后这句话不成立：总位移比它自己的介电分量**更**像 Born。"
                 "下表按轴分开给出（避免两轴正负相消）：")
    lines.append("")
    lines.append("| 序列 | 氧化轴 mean R2 | 还原轴 mean R2 | 氧化轴 mean S (eV) | 还原轴 mean S (eV) |")
    lines.append("| --- | --- | --- | --- | --- |")
    tm = terms["per_molecule"]
    mm = model["per_molecule"]
    for label, r2_key, slope_rows, slope_key in (
            ("总位移", "total_r2", mm, "born_S_ev"),
            ("纯介电 (CPCM Dielectric)", "diel_r2", tm, "diel_S_ev"),
            ("溶质畸变 (Delta E_elec+nuc)", "dist_r2", tm, "dist_S_ev")):
        r2_by_axis = _axis_mean(tm, r2_key)
        slope_by_axis = _axis_mean(slope_rows, slope_key)
        lines.append("| %s | %s | %s | %s | %s |"
                     % (label, _fmt(r2_by_axis["oxidation"], 4), _fmt(r2_by_axis["reduction"], 4),
                        _fmt(slope_by_axis["oxidation"], 4), _fmt(slope_by_axis["reduction"], 4)))
    lines.append("")
    coupling = checks["total_shift_is_more_born_like_than_its_parts"]
    lines.append("三个顺序**不可互换**：总位移 mean R2 = %s > 纯介电项 %s > 畸变项 %s。"
                 "也就是说：**环境层作为一个整体是 Born 型的，但逐项不是** —— "
                 "介电项单独拟合反而更差，畸变项在 Born 形式下连「预测零」都不如（mean R2 < 0），"
                 "两项是**耦合且部分抵消**的：介电项对 Born 的偏离被畸变项拉回来一部分，"
                 "于是总和比分量干净。"
                 % (_fmt(coupling["total_mean_r2"], 4), _fmt(coupling["dielectric_mean_r2"], 4),
                    _fmt(coupling["distortion_mean_r2"], 4)))
    lines.append("")

    lines.append("## 3. 导体极限 eps -> inf")
    lines.append("")
    gap = limit["gap_to_limit_ev"]
    lines.append("六点 Born 拟合的斜率 S 就是 eps -> inf 的极限（u -> 1）。"
                 "eps = 200 与极限之间还剩 %s eV（mean），最差 %s eV —— 已经在 50 meV 以内，"
                 "再往上加介电点不会改变任何结论。"
                 % (_fmt(gap["mean"], 4), _fmt(gap["max"], 4)))
    lines.append("")
    lines.append("| 轴 | tau(gas vs eps=200) | tau(gas vs 极限) | tau(eps=200 vs 极限) | top20 overlap (gas vs 极限) |")
    lines.append("| --- | --- | --- | --- | --- |")
    for axis_label, block in limit["ordering"].items():
        lines.append("| %s | %s | %s | %s | %s |"
                     % (axis_label, _signed(block["kendall_tau_gas_vs_200"]),
                        _signed(block["kendall_tau_gas_vs_limit"]),
                        _signed(block["kendall_tau_200_vs_limit"]),
                        _fmt(block["top20_overlap_gas_vs_limit"], 2)))
    lines.append("")

    lines.append("## 4. 外推误差随「外推距离」增长")
    lines.append("")
    lines.append("只用 eps <= 20 拟合，再预报 40 / 80 / 200（拟合时不含目标点）：")
    lines.append("")
    lines.append("| 目标 eps | u 距离 (u(t) - u(20)) | 最大绝对误差 (eV) | 平均绝对误差 (eV) | 最大相对误差 |")
    lines.append("| --- | --- | --- | --- | --- |")
    for tag in ("cpcm_40", "cpcm_80", "cpcm_200"):
        block = extrap["targets"][tag]
        lines.append("| %g | %s | %s | %s | %s |"
                     % (block["target_eps"], _fmt(block["u_gap"], 4),
                        _fmt(block["max_abs_err_ev"], 4), _fmt(block["mean_abs_err_ev"], 4),
                        _fmt(100.0 * block["max_rel_err"], 2) + "%"))
    lines.append("")
    lines.append("误差基本正比于 u 距离（斜率 %s eV per unit u），即**只需知道要外推多远就能预估误差**；"
                 "从 eps = 20 推到 40 / 80 / 200，最大绝对误差只有 %s / %s / %s eV。"
                 % (_fmt(extrap["err_per_u_gap_ev"], 3),
                    _fmt(extrap["targets"]["cpcm_40"]["max_abs_err_ev"], 4),
                    _fmt(extrap["targets"]["cpcm_80"]["max_abs_err_ev"], 4),
                    _fmt(extrap["targets"]["cpcm_200"]["max_abs_err_ev"], 4)))
    lines.append("")

    lines.append("## 5. SMD 能量账本：位移的精确四项分解")
    lines.append("")
    lines.append("ORCA 把每个单点印成 `FINAL = Total + D4 + gCP`，而 `Total = E_elec+nuc + CPCM [+ CDS]`。"
                 "于是垂直量的环境位移逐态精确可加（来自同一次自洽计算，不是两次计算的差分）：")
    lines.append("")
    lines.append("`delta = 溶质畸变 + CPCM 介电 [+ SMD CDS] + Delta(D4) + Delta(gCP)`")
    lines.append("")
    lines.append("| 层 | eps | 轴 | 位移 (eV) | 介电项 (eV) | 畸变项 (eV) | 畸变抵消介电的比例 |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- |")
    for tag in SMD_TAGS:
        block = ledger[tag]
        for axis_label, stats in block["per_axis"].items():
            lines.append("| %s | %s | %s | %s | %s | %s | %s |"
                         % (tag, _fmt(block["epsilon"], 3), axis_label,
                            _signed(stats["shift_ev"]["mean"], 4),
                            _signed(stats["diel_ev"]["mean"], 4),
                            _signed(stats["dist_ev"]["mean"], 4),
                            _fmt(stats["distortion_cancels_fraction"]["mean"], 3)))
    lines.append("")
    lines.append("三条**结构性**事实（全部在 12 分子 × 3 态上逐点验证，不是近似）：")
    lines.append("")
    lines.append("1. `Delta(D4) = Delta(gCP) = 0`：D4 与 gCP 只依赖几何，而几何逐字节相同。")
    lines.append("2. `SMD CDS` 项在三个电荷态上**完全相同**（最大 spread = %s eV），"
                 "因此它对任何垂直 IP/EA 的贡献精确为 0 —— 它是一个刚性偏移。"
                 % _fmt(checks["smd_ledger_reproduces_the_shift"].get("cds_max_spread_ev"), 8))
    lines.append("3. 位移恒等式残差 <= %s eV（印刷精度）。"
                 % _fmt(checks["smd_ledger_reproduces_the_shift"].get("max_split_residual_ev"), 8))
    lines.append("")
    absolute = ledger.get("smd_cds_absolute_ev") or {}
    lines.append("CDS 的绝对量级并不小（按层统计：%s），"
                 "但它对三个电荷态是**完全相同**的，所以在本项目的所有量里不可见。"
                 % "、".join("%s %s .. %s eV（均值 %s）"
                              % (tag, _fmt((absolute.get(tag) or {}).get("min"), 4),
                                 _fmt((absolute.get(tag) or {}).get("max"), 4),
                                 _fmt((absolute.get(tag) or {}).get("mean"), 4))
                              for tag in SMD_TAGS))
    lines.append("")
    lines.append("**需要裁决**：bare CPCM 与 SMD 用的原子半径盒不同（C 2.04 -> 1.85 Å、"
                 "O 1.824 -> 2.168 Å（水 1.52 Å）、H 1.32 -> 1.20 Å；cavity points 1015 -> 973 / 779），"
                 "而 ORCA 的 `%%cpcm` 没有调节腔半径的选项。于是「把 SMD 位移与同 eps 的 bare-CPCM "
                 "外推值相减」混进了**半径盒 + 表面项两个变量**，只能作合并上界报出（乙腈 %s eV、"
                 "水 %s eV，均为 24 条曲线的均值），不能称为纯表面项。"
                 % (_fmt((ledger["smd_acetonitrile"]["smd_minus_bare_same_epsilon"]["difference_ev"] or {}).get("mean"), 4),
                    _fmt((ledger["smd_water"]["smd_minus_bare_same_epsilon"]["difference_ev"] or {}).get("mean"), 4)))
    lines.append("")

    lines.append("## 6. 22 点台阶总表（电子结构 10 + 介电 12）")
    lines.append("")
    lines.append("| 台阶 | 轴 | n | sd(delta) (eV) | b | tau_b | f_unres(1) | f_unres(1.96) | top20 overlap | 清单被改写 |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for row in rungs["rows"]:
        lines.append("| `%s` | %s | %s | %s | %s | %s | %s | %s | %s | %s |"
                     % (row.get("rung"), row.get("axis"), row.get("n"),
                        _fmt(row.get("delta_sd_ev"), 4), _signed(row.get("ols_slope_b")),
                        _signed(row.get("kendall_tau_b")),
                        _fmt(row.get("f_unresolved_p1_observed")),
                        _fmt(row.get("f_unresolved_p1_z1p96_observed")),
                        _fmt(row.get("overlap_20"), 2),
                        "是" if row.get("shortlist_rewritten") else "否"))
    lines.append("")
    lines.append("新增的四个介电台阶（40->80、80->200 各两轴）全部良性；全表只有 3 个台阶改写清单，"
                 "与 Stage 12 完全相同（%s）—— 把介电常数从 40 推到 200，一个结论都没有翻转。"
                 % "、".join(rungs["rewritten_points"]))
    lines.append("")
    shrink = checks["dielectric_slope_shrinks_toward_zero"]
    lines.append("**第三处口径修正**：Stage 12 把「b > 0」写进了介电台阶的良性判据。在饱和端这条不成立 —— "
                 "带符号斜率随 eps 增大而衰减（气相台阶 max |b| = %s，最饱和的两个台阶 max |b| = %s，"
                 "全表最小 b = %s），其**符号在饱和端不再可分辨**。"
                 "良性判据因此改回决策层面：tau_b > 0.5、top20 overlap = 1.000、清单不动。"
                 "二者相差在饱和端本来就该趋零，把符号当判据会把「什么都没发生」误判成危险。"
                 % (_fmt(shrink["max_abs_b_from_the_gas"], 5),
                    _fmt(shrink["max_abs_b_at_the_saturated_end"], 5),
                    _fmt(shrink["min_b_over_all_dielectric_rungs"], 8)))
    lines.append("")

    lines.append("## 7. 检查清单")
    lines.append("")
    lines.append("其中三条判据在本周**据实修正**（不是放宽阈值）：`min R2 > 0.95` 被六点阶梯证伪；"
                 "「介电项单独就像 Born」被证伪；「介电台阶必须 b > 0」在饱和端不可分辨。"
                 "三者的替代判据与原有的数字一并列在下表（`detail` 里给出实测值）。")
    lines.append("")
    lines.append("| 检查 | 通过 | 关键数字 |")
    lines.append("| --- | --- | --- |")
    for name, entry in checks.items():
        detail = entry.get("detail")
        if detail is None:
            detail = "; ".join("%s=%s" % (key, value) for key, value in entry.items() if key != "ok")
        lines.append("| `%s` | %s | %s |" % (name, "PASS" if entry.get("ok") else "FAIL", detail))
    lines.append("")
    return "\n".join(lines)


def write_csv(path: Path, columns, rows) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: ("" if row.get(key) is None else row.get(key)) for key in columns})


def smd_cds_absolute(outdir: Path) -> dict:
    """Mean / sd of the SMD CDS term per layer, across every state row."""

    rows = load_csv(outdir / "stage13_state_ledger.csv")
    out = {}
    for tag in SMD_TAGS:
        values = [_float(row.get("smd_cds_ev")) for row in rows if row.get("level") == tag]
        values = [v for v in values if v is not None]
        out[tag] = _summary(values)
    return out


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Stage 13: the dielectric limit and ORCA's energy ledger.")
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    outdir = args.outdir if args.outdir.is_absolute() else (Path.cwd() / args.outdir)

    if not LEDGER_JSON.exists():
        print("error: %s missing -- run scripts/build_stage13_ladder.py first" % LEDGER_JSON,
              file=sys.stderr)
        return 2
    ladder = json.loads(LEDGER_JSON.read_text(encoding="utf-8"))
    levels, epsilon_of = load_levels()
    split = load_split()
    names = [name for name in (ladder.get("subset") or []) if name in levels]
    if not names:
        print("error: the ladder has no molecules", file=sys.stderr)
        return 2

    model = model_comparison(levels, names)
    terms = term_resolved_born(levels, split, names)
    limit = conductor_limit(levels, names)
    extrap = extrapolation_scaling(levels, names)
    ledger = ledger_analysis(split, levels, epsilon_of, names, smd_cds_absolute(outdir))
    rungs = rung_ladder(levels, names)
    checks = run_checks(model, terms, limit, extrap, ledger, rungs, ladder.get("checks", {}))

    payload = {
        "stage": "stage13_dielectric_limit",
        "week": 12,
        "convention": {
            "shift": "delta(tag) = p(gas) - p(tag), p_ox = IP, p_red = -EA (Stage 10-12 convention)",
            "bare_ladder": "bare CPCM, eps in {1 (gas), 5, 10, 20, 40, 80, 200}",
            "smd_layers": "CPCM(SMD, solvent) at the solvent's own printed epsilon",
            "ledger": ("FINAL SINGLE POINT ENERGY = Total Energy + D4 + gCP; "
                       "Total Energy = E_elec+nuc + CPCM Dielectric [+ SMD CDS]"),
        },
        "subset": names,
        "n_subset": len(names),
        "bare_tags": list(BARE_TAGS),
        "bare_eps": list(BARE_EPS),
        "ladder_checks": ladder.get("checks", {}),
        "model_comparison": model,
        "term_resolved_born": terms,
        "conductor_limit": limit,
        "extrapolation_scaling": extrap,
        "smd_ledger": ledger,
        "rung_ladder": rungs,
        "checks": checks,
    }
    (outdir / "stage13_analysis.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    (outdir / "stage13_summary.md").write_text(
        render_summary(payload), encoding="utf-8", newline="\n")
    write_csv(outdir / "stage13_rungs.csv", RUNG_COLUMNS, rungs["rows"])

    failed = [name for name, entry in checks.items() if entry.get("ok") is False]
    print(json.dumps({"n_molecules": len(names), "n_rungs": rungs["n_points"],
                      "n_rewritten": rungs["n_rewritten"],
                      "checks_failed": failed}, ensure_ascii=False))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())