#!/usr/bin/env python
"""Stage 17 / Week 16 -- Part A: the contamination bound on the published P1 -> P2 rung.

Week 9 published a five-rung ladder whose second rung ``P1 -> P2`` used the
SMD(acetonitrile) P2 single-point energies in
``outputs/week4/p2_environment_effects.csv``. Week 15 found that ORCA's default
initial guess can stop on a non-lowest SCF solution on a few cells; the running
``scripts/run_stage17_smd_moread.py`` recomputes the *same* SMD layer with a
``moread`` (gas-phase MO restart) guess over 18 molecules x 3 states = 54 cells,
writing ``outputs/week16/p2_core_set_moread_smd_acetonitrile.csv``.

This script answers one question: **if the P1 -> P2 rung were computed with the
moread arm, how much would the published Week 9 decision-stability conclusions
move, and how large is the contamination bound?**

The convention is *identical* to Week 9 -- no new formula is written here. We
reuse, verbatim:

* ``scripts/analyze_p1_core_set.py``
    - ``layer_stability``      (line 346)  the canonical tau_b / Top-k overlap /
                                           jaccard / selection regret /
                                           f_unresolved / f_robust_inv / sigma
                                           code that Week 9 (and Week 4) used;
    - ``tau_b_interval``       (line 67)   the Week 9 bootstrap CI (20 frozen
                                           seeds x 2000 paired resamples).
* ``scripts/analyze_stage10_synthesis.py``
    - ``load_csv``             (line 119);
    - ``P2_EFFECTS``           (line 58)   the published P1 -> P2 summary.
* ``scripts/analyze_p2_environment.py``
    - ``HARTREE_TO_EV``        (line 46);
    - the ``molecule_record`` P2 formulas (lines 101-134):
      ``p2_ox = (E_cation - E_neutral) * Ha->eV`` and
      ``p2_red = -EA = (E_anion - E_neutral) * Ha->eV`` (the ``p_red = -EA``
      convention that put both axes on ``higher_is_better = True``).

Molecule ordering follows Week 9 as well: ``sorted(name)`` exactly as
``analyze_stage10_synthesis.rung_names`` produced it, so the reproduced default
arm matches the published ``stage10_ladder.json`` row bit-for-bit.

Outputs
-------
``outputs/week16/stage17_contamination_ladder.csv``  two arms x two axes x every metric (+ published columns)
``outputs/week16/stage17_contamination_cells.csv``   18 rows (one per molecule) x both axes
``outputs/week16/stage17_contamination.json``        structured result
``outputs/week16/stage17_contamination_summary.md``  Chinese summary (<= 120 lines)
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from analyze_stage10_synthesis import P2_EFFECTS, load_csv, _float  # noqa: E402
from analyze_p1_core_set import layer_stability                     # noqa: E402
from analyze_p2_environment import HARTREE_TO_EV                    # noqa: E402
from electrolyte_ranking import uncertainty                         # noqa: E402

DEFAULT_OUTDIR = REPO_ROOT / "outputs" / "week16"
DEFAULT_MOREAD = DEFAULT_OUTDIR / "p2_core_set_moread_smd_acetonitrile.csv"
DEFAULT_REFERENCE = REPO_ROOT / "outputs" / "week4" / "p2_core_set_smd_acetonitrile.csv"
PUBLISHED_LADDER = REPO_ROOT / "outputs" / "week9" / "stage10_ladder.json"

AXES = (("oxidation", "ox"), ("reduction", "red"))
ARMS = ("default", "moread")
STATES = ("neutral", "cation", "anion")
CELL_TOL_EV = 1e-3

LADDER_COLUMNS = [
    "arm", "axis", "n", "names",
    "shift_mean_ev", "shift_std_ev", "shift_min_ev", "shift_max_ev",
    "kendall_tau_b", "tau_b_ci_low", "tau_b_ci_high",
    "tau_b_ci95_seeded_low", "tau_b_ci95_seeded_high",
    "spearman_rho", "overlap_10", "overlap_20", "overlap_30",
    "jaccard_20", "regret_20",
    "f_unresolved_before", "f_unresolved_after", "f_robust_inv",
    "f_robust_inv_z1p96", "sigma_median_ev",
    "published_kendall_tau_b", "published_overlap_20",
    "published_f_unresolved_after", "published_f_robust_inv",
    "delta_kendall_tau_b", "delta_overlap_20",
    "delta_f_unresolved", "delta_f_robust_inv",
]
# --------------------------------------------------------------------------- #
# small helpers
# --------------------------------------------------------------------------- #
def relative(path: Path) -> str:
    try:
        return str(Path(path).resolve().relative_to(REPO_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def load_raw_states(path: Path) -> dict:
    """(name, state) -> {"status": str, "energy_eh": float | None}."""
    out = {}
    for row in load_csv(path):
        out[(row.get("name"), row.get("state"))] = {
            "status": (row.get("status") or "").strip(),
            "energy_eh": _float(row.get("final_energy_eh")),
        }
    return out


def derive_p2(states: dict, name: str):
    """One arm's P2 ox/red (eV) on the ``p_red = -EA`` convention.

    Mirrors ``analyze_p2_environment.molecule_record`` (lines 101-134).
    Returns ``(p2_ox, p2_red)``; either is ``None`` when a state cell is
    missing or not ``status == "ok"``.
    """

    def energy(state):
        record = states.get((name, state))
        if record is None or record["status"] != "ok":
            return None
        return record["energy_eh"]

    neu, cat, an = energy("neutral"), energy("cation"), energy("anion")
    ox = None if None in (neu, cat) else (cat - neu) * HARTREE_TO_EV
    red = None if None in (neu, an) else (an - neu) * HARTREE_TO_EV
    return ox, red


def sign_test(deltas, tol: float = 1e-12) -> dict:
    """Exact sign test on a list of paired differences.

    ``p_two_sided = 2 * P(Binomial(n, 0.5) <= min(n_pos, n_neg))`` (capped at 1)
    is the primary statistic; the one-sided ``P(Binomial(n, 0.5) >= n_pos)`` is
    reported alongside. ``n = n_pos + n_neg`` (exact zeros drop out). If every
    difference is a tie the test is undefined and we record ``p = 1.0``.
    """

    values = [d for d in deltas if d is not None]
    pos = sum(1 for d in values if d > tol)
    neg = sum(1 for d in values if d < -tol)
    zero = len(values) - pos - neg
    n = pos + neg
    out = {
        "n_total": len(values),
        "n_positive": pos,
        "n_negative": neg,
        "n_zero": zero,
        "n_informative": n,
        "tolerance_ev": tol,
        "side": "two_sided (primary) + one_sided_greater",
        "p_two_sided": None,
        "p_one_sided_greater": None,
    }
    if n == 0:
        out["p_two_sided"] = 1.0
        out["p_one_sided_greater"] = 1.0
        out["note"] = "all deltas within tolerance (no + and no -); sign test undefined, recorded as p = 1.0"
        return out
    k = min(pos, neg)
    p_two = 2.0 * sum(math.comb(n, i) for i in range(0, k + 1)) / (2 ** n)
    out["p_two_sided"] = min(1.0, p_two)
    out["p_one_sided_greater"] = sum(math.comb(n, i) for i in range(pos, n + 1)) / (2 ** n)
    return out


def delta_stats(pairs) -> dict:
    """mean/std/max/min/argmax/argmin over ``[(label, delta_ev), ...]``."""

    clean = [(label, d) for label, d in pairs if d is not None]
    if not clean:
        return {"n": 0}
    values = [d for _, d in clean]
    argmax = max(clean, key=lambda p: p[1])
    argmin = min(clean, key=lambda p: p[1])
    return {
        "n": len(values),
        "mean_ev": statistics.fmean(values),
        "std_ev": statistics.stdev(values) if len(values) > 1 else 0.0,
        "max_ev": max(values),
        "min_ev": min(values),
        "max_abs_ev": max(abs(v) for v in values),
        "argmax": argmax[0],
        "argmin": argmin[0],
    }
# --------------------------------------------------------------------------- #
# core metrics
# --------------------------------------------------------------------------- #
def metrics_row(arm: str, axis: str, names, before, after,
                seed: int, draws: int) -> dict:
    """Every published metric for one (arm, axis), via Week 9's own code."""

    result = layer_stability(list(before), list(after), list(names),
                             higher_is_better=True)
    paired = [(a, b) for a, b in zip(before, after) if a is not None and b is not None]
    shifts = [b - a for a, b in paired]
    row = {
        "arm": arm,
        "axis": axis,
        "n": result.get("n", len(paired)),
        "names": ";".join(names),
        "shift_mean_ev": statistics.fmean(shifts) if shifts else None,
        "shift_std_ev": statistics.stdev(shifts) if len(shifts) > 1 else None,
        "shift_min_ev": min(shifts) if shifts else None,
        "shift_max_ev": max(shifts) if shifts else None,
    }
    if len(paired) < 2 or "kendall_tau_b" not in result:
        return row
    top = result.get("top_k") or {}
    ci = result.get("kendall_tau_b_ci95") or [None, None]
    try:
        slo, shi = uncertainty.bootstrap_tau_b_ci(list(before), list(after),
                                                  draws, seed, 0.05)
    except Exception:  # pragma: no cover - defensive
        slo, shi = (None, None)
    row.update({
        "kendall_tau_b": result.get("kendall_tau_b"),
        "tau_b_ci_low": ci[0],
        "tau_b_ci_high": ci[1],
        "tau_b_ci95_seeded_low": slo,
        "tau_b_ci95_seeded_high": shi,
        "spearman_rho": result.get("spearman_rho"),
        "overlap_10": (top.get("k=0.10") or {}).get("overlap"),
        "overlap_20": (top.get("k=0.20") or {}).get("overlap"),
        "overlap_30": (top.get("k=0.30") or {}).get("overlap"),
        "jaccard_20": (top.get("k=0.20") or {}).get("jaccard"),
        "regret_20": (top.get("k=0.20") or {}).get("selection_regret"),
        "f_unresolved_before": result.get("f_unresolved_p0"),
        "f_unresolved_after": result.get("f_unresolved_p1"),
        "f_robust_inv": result.get("f_robust_inv"),
        "f_robust_inv_z1p96": result.get("f_robust_inv_z1p96"),
        "sigma_median_ev": result.get("sigma_median_ev"),
    })
    return row


def load_published() -> dict:
    """Published Week 9 P1 -> P2 rows (native population), keyed by axis."""

    if not PUBLISHED_LADDER.exists():
        return {}
    data = json.loads(PUBLISHED_LADDER.read_text(encoding="utf-8"))
    out = {}
    for row in data.get("ladder", []):
        if row.get("population") == "native" and row.get("rung") == "P1_to_P2":
            out[row.get("axis")] = row
    return out

# --------------------------------------------------------------------------- #
# the analysis
# --------------------------------------------------------------------------- #
def analyze(moread_csv: Path, reference_csv: Path, effects_csv: Path,
            draws: int, seed: int) -> dict:
    published = load_published()

    effects = load_csv(effects_csv)
    by_name = {row["name"]: row for row in effects}
    names = sorted(by_name)  # Week 9 (analyze_stage10_synthesis.rung_names) order

    p1_ox = [_float(by_name[n].get("p1_ox_ev")) for n in names]
    p1_red = [_float(by_name[n].get("p1_red_ev")) for n in names]
    pub_ox = [_float(by_name[n].get("p2_ox_ev")) for n in names]
    pub_red = [_float(by_name[n].get("p2_red_ev")) for n in names]

    default_states = load_raw_states(reference_csv)
    moread_states = load_raw_states(moread_csv)

    default_p2 = {n: derive_p2(default_states, n) for n in names}
    moread_p2 = {n: derive_p2(moread_states, n) for n in names}

    arm_vectors = {
        "default": {"ox": [default_p2[n][0] for n in names],
                    "red": [default_p2[n][1] for n in names]},
        "moread": {"ox": [moread_p2[n][0] for n in names],
                   "red": [moread_p2[n][1] for n in names]},
    }
    p1_vectors = {"ox": p1_ox, "red": p1_red}

    # sanity: default arm must reproduce the published P2 values exactly
    sanity = {}
    for key, published_values in (("ox", pub_ox), ("red", pub_red)):
        diffs = [abs(a - b) for a, b in zip(arm_vectors["default"][key], published_values)
                 if a is not None and b is not None]
        sanity[key] = max(diffs) if diffs else None

    rows = []
    per_axis = {}
    for title, key in AXES:
        per_axis[title] = {}
        for arm in ARMS:
            row = metrics_row(arm, title, names, p1_vectors[key],
                              arm_vectors[arm][key], seed, draws)
            rows.append(row)
            per_axis[title][arm] = row

    # ---- published comparison -------------------------------------------------
    comparison = {}
    for title, key in AXES:
        block = published.get(title, {})
        entry = {
            "published": {
                "kendall_tau_b": block.get("kendall_tau_b"),
                "tau_b_ci_low": block.get("tau_b_ci_low"),
                "tau_b_ci_high": block.get("tau_b_ci_high"),
                "overlap_20": block.get("overlap_20"),
                "f_unresolved_after": block.get("f_unresolved_after"),
                "f_robust_inv": block.get("f_robust_inv"),
                "sigma_median_ev": block.get("sigma_median_ev"),
                "shift_mean_ev": block.get("shift_mean_ev"),
                "shift_std_ev": block.get("shift_std_ev"),
                "n": block.get("n"),
                "source": relative(PUBLISHED_LADDER) + " (ladder: population=native, rung=P1_to_P2)",
            },
        }
        for arm in ARMS:
            row = per_axis[title][arm]
            entry[arm + "_minus_published"] = {}
            for metric in ("kendall_tau_b", "overlap_20", "f_unresolved_after",
                           "f_robust_inv", "sigma_median_ev"):
                pv = entry["published"][metric]
                av = row.get(metric)
                entry[arm + "_minus_published"][metric] = (
                    None if pv is None or av is None else av - pv)
        comparison[title] = entry
    # ---- per-molecule cells ---------------------------------------------------
    cell_rows = []
    cell_pairs = []          # 54 (label, delta_ev) at (molecule, state) granularity
    ox_delta_pairs = []      # 18, p2_ox_moread - p2_ox_default
    red_delta_pairs = []     # 18, p2_red_moread - p2_red_default
    for n in names:
        d_ox, d_red = default_p2[n]
        m_ox, m_red = moread_p2[n]
        cell = {
            "mol_id": by_name[n].get("mol_id", ""),
            "name": n,
            "family": by_name[n].get("family", ""),
            "role": by_name[n].get("role", ""),
            "ox_p1_ev": by_name[n].get("p1_ox_ev"),
            "ox_p2_default_ev": d_ox,
            "ox_p2_moread_ev": m_ox,
            "ox_delta_ev": None if None in (d_ox, m_ox) else m_ox - d_ox,
            "red_p1_ev": by_name[n].get("p1_red_ev"),
            "red_p2_default_ev": d_red,
            "red_p2_moread_ev": m_red,
            "red_delta_ev": None if None in (d_red, m_red) else m_red - d_red,
        }
        for state in STATES:
            de = default_states.get((n, state))
            me = moread_states.get((n, state))
            delta = None
            if (de is not None and me is not None and de["status"] == "ok"
                    and me["status"] == "ok" and de["energy_eh"] is not None
                    and me["energy_eh"] is not None):
                delta = (me["energy_eh"] - de["energy_eh"]) * HARTREE_TO_EV
            cell[state + "_delta_ev"] = delta
            cell_pairs.append(("%s/%s" % (n, state), delta))
        ox_delta_pairs.append((n, cell["ox_delta_ev"]))
        red_delta_pairs.append((n, cell["red_delta_ev"]))
        cell_rows.append(cell)

    cells_changed = []
    for label, delta in cell_pairs:
        if delta is not None and abs(delta) > CELL_TOL_EV:
            name, state = label.split("/")
            axes_hit = []
            if state in ("neutral", "cation"):
                axes_hit.append("oxidation")
            if state in ("neutral", "anion"):
                axes_hit.append("reduction")
            cells_changed.append({
                "molecule": name,
                "state": state,
                "cell": label,
                "delta_ev": delta,
                "axes": axes_hit,
            })
    cells_changed.sort(key=lambda item: abs(item["delta_ev"]), reverse=True)

    # ---- sign tests -----------------------------------------------------------
    sign_tests = {
        "cells_54": sign_test([d for _, d in cell_pairs]),
        "axis_oxidation_18": sign_test([d for _, d in ox_delta_pairs]),
        "axis_reduction_18": sign_test([d for _, d in red_delta_pairs]),
    }
    stats = {
        "definition": "delta = p2_moread - p2_default (eV)",
        "cells_54": delta_stats(cell_pairs),
        "axis_oxidation_18": delta_stats(ox_delta_pairs),
        "axis_reduction_18": delta_stats(red_delta_pairs),
    }

    # ---- CI overlap verdict ---------------------------------------------------
    ci_overlap = {}
    for title, _ in AXES:
        d = per_axis[title]["default"]
        m = per_axis[title]["moread"]
        dlo, dhi = d.get("tau_b_ci_low"), d.get("tau_b_ci_high")
        mlo, mhi = m.get("tau_b_ci_low"), m.get("tau_b_ci_high")
        overlap = None
        if None not in (dlo, dhi, mlo, mhi):
            overlap = not (dhi < mlo or mhi < dlo)
        ci_overlap[title] = {
            "default_ci": [dlo, dhi],
            "moread_ci": [mlo, mhi],
            "overlap": overlap,
            "method": ("Week 9 tau_b_interval: 20 frozen seeds x 2000 paired "
                       "resamples, median of percentile bounds"),
        }
    # ---- verdict --------------------------------------------------------------
    rewritten, unchanged = [], []
    for title, _ in AXES:
        cmp_block = comparison[title]
        dt = cmp_block["moread_minus_published"]["kendall_tau_b"]
        dov = cmp_block["moread_minus_published"]["overlap_20"]
        dfu = cmp_block["moread_minus_published"]["f_unresolved_after"]
        finv_d = per_axis[title]["default"].get("f_robust_inv")
        finv_m = per_axis[title]["moread"].get("f_robust_inv")
        flipped = ((finv_d or 0.0) == 0.0) != ((finv_m or 0.0) == 0.0)
        if flipped:
            rewritten.append("%s: f_robust_inv %s -> %s (0/non-0 state changed)"
                             % (title, finv_d, finv_m))
        else:
            unchanged.append("%s: f_robust_inv stays %s (unchanged)"
                             % (title, finv_m))
        if dt is not None and abs(dt) > 0.05:
            rewritten.append("%s: tau_b moves by %.3f (> 0.05)" % (title, dt))
        else:
            unchanged.append("%s: tau_b moves by %s (<= 0.05, unchanged)"
                             % (title, "None" if dt is None else "%.3f" % dt))
        if dov is not None and abs(dov) > 0.10:
            rewritten.append("%s: Top-k overlap_20 moves by %.3f (> 0.10)" % (title, dov))
        else:
            unchanged.append("%s: Top-k overlap_20 moves by %s (<= 0.10, unchanged)"
                             % (title, "None" if dov is None else "%.3f" % dov))
        if dfu is not None and abs(dfu) > 0.05:
            rewritten.append("%s: f_unresolved(after) moves by %.3f (> 0.05)" % (title, dfu))
        else:
            unchanged.append("%s: f_unresolved(after) moves by %s (<= 0.05, unchanged)"
                             % (title, "None" if dfu is None else "%.3f" % dfu))

    any_rewritten = bool(rewritten)
    ox_m = per_axis["oxidation"]["moread"]
    red_m = per_axis["reduction"]["moread"]
    any_finv = any((per_axis[t][a].get("f_robust_inv") or 0.0) > 0.0
                   for t, _ in AXES for a in ARMS)
    scenario = {}
    scenario["B_large_shift_small_rank_damage"] = {
        "published": "SUPPORTED",
        "recheck": ("moread oxidation tau_b = %s, O_20%% = %s, f_robust_inv = %s"
                    % (ox_m.get("kendall_tau_b"), ox_m.get("overlap_20"),
                       ox_m.get("f_robust_inv"))),
        "assessment": ("still SUPPORTED (large shift, stable ranking, low f_robust_inv)"
                       if (ox_m.get("kendall_tau_b") or 0) >= 0.7
                       and (ox_m.get("f_robust_inv") or 0.0) == 0.0
                       else "needs restatement: the moread arm changes the shift/rank/inversion relation"),
    }
    scenario["C_structured_robust_inversion"] = {
        "published": "NOT OBSERVED",
        "recheck": "moread f_robust_inv = %s / %s (oxidation / reduction)"
                   % (ox_m.get("f_robust_inv"), red_m.get("f_robust_inv")),
        "assessment": ("still NOT OBSERVED (both arms keep f_robust_inv at 0)"
                       if not any_finv else
                       "needs restatement: the moread arm produces f_robust_inv > 0"),
    }
    scenario["A_cheap_proxy_already_stable"] = {
        "published": "NOT SUPPORTED",
        "recheck": ("A rests on the P0->P2 rung; here only the P2 leg of P1->P2 is "
                    "swapped. moread tau_b(P1,P2) oxidation = %s" % ox_m.get("kendall_tau_b")),
        "assessment": ("the P1->P2 ordering barely moves, so A's P2-leg dependence is "
                       "unaffected by the contamination"
                       if not any_rewritten else
                       "the P1->P2 rung is rewritten, so A's P0->P2 evidence must be re-checked"),
    }

    payload = {
        "stage": 17,
        "part": "A -- contamination bound on the published P1->P2 rung",
        "generated_from": {
            "moread_csv": relative(moread_csv),
            "reference_csv": relative(reference_csv),
            "effects_csv": relative(effects_csv),
        },
        "convention": "p_red = -EA; higher_is_better = True on both axes",
        "population": "native (all %d molecules of the week-9 ladder population)" % len(names),
        "molecules": names,
        "arms": list(ARMS),
        "reused_from_week9": {
            "layer_stability": "scripts/analyze_p1_core_set.py:346 (all metrics)",
            "tau_b_interval": "scripts/analyze_p1_core_set.py:67 (bootstrap CI)",
            "load_csv/P2_EFFECTS": "scripts/analyze_stage10_synthesis.py:119,58",
            "P2 formulas": "scripts/analyze_p2_environment.py:46,101-134",
        },
        "default_matches_published_max_abs_ev": sanity,
        "per_axis": per_axis,
        "published_comparison": comparison,
        "delta_stats": stats,
        "sign_test": sign_tests,
        "cells_changed": cells_changed,
        "cells_changed_count": len(cells_changed),
        "ci_overlap": ci_overlap,
        "verdict": {
            "any_published_conclusion_rewritten": any_rewritten,
            "tau_b_ci_overlap_both_axes": all(ci_overlap[t]["overlap"] for t, _ in AXES
                                              if ci_overlap[t]["overlap"] is not None),
            "conclusions_rewritten": rewritten,
            "conclusions_unchanged": unchanged,
            "scenario_verdicts": scenario,
        },
        "limits": [
            ("The default arm's P2 is derived independently from "
             "p2_core_set_smd_acetonitrile.csv; its max departure from the published "
             "value is %s eV (expected 0)." % sanity.get("ox")),
            "Only the P2 leg of the P1->P2 rung is swapped; P1 values, geometry, method layer and the other four rungs are untouched.",
            "With two realizations and z_primary = 1.0 the sigma estimator makes f_robust_inv structurally ~0, so a 0->non-0 flip is essentially impossible from this swap alone.",
            "A moread cell with status != ok makes layer_stability drop that molecule/axis, so n can fall below 18; this shows up in n and in cells_changed.",
            "The primary sign-test delta is the 54 (molecule, state) cells; the two 18-molecule axis deltas are reported alongside.",
            "The tau_b CI overlap test uses Week 9's tau_b_interval (20 seeds x 2000); --draws/--seed give a separate single-seed CI as a sensitivity column.",
        ],
        "_cell_rows": cell_rows,
    }
    return payload

# --------------------------------------------------------------------------- #
# writers
# --------------------------------------------------------------------------- #
def write_ladder_csv(path: Path, rows) -> Path:
    import csv
    path.parent.mkdir(parents=True, exist_ok=True)
    axes_order = {"oxidation": 0, "reduction": 1}
    arm_order = {"default": 0, "moread": 1}
    rows = sorted(rows, key=lambda r: (axes_order.get(r["axis"], 9),
                                       arm_order.get(r["arm"], 9)))
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=LADDER_COLUMNS,
                                extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    return path


def write_cells_csv(path: Path, cell_rows) -> Path:
    import csv
    path.parent.mkdir(parents=True, exist_ok=True)
    columns = ["mol_id", "name", "family", "role",
               "ox_p1_ev", "ox_p2_default_ev", "ox_p2_moread_ev", "ox_delta_ev",
               "red_p1_ev", "red_p2_default_ev", "red_p2_moread_ev", "red_delta_ev",
               "neutral_delta_ev", "cation_delta_ev", "anion_delta_ev"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in cell_rows:
            writer.writerow(row)
    return path


def _fmt(value, digits=3):
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return ("%%.%df" % digits) % value
    return str(value)


def _sig(value):
    return "n/a" if value is None else "%.3g" % value


def write_summary(path: Path, payload) -> Path:
    per = payload["per_axis"]
    pub_table = payload["published_comparison"]
    stats = payload["delta_stats"]
    sig = payload["sign_test"]
    verdict = payload["verdict"]
    lines = []
    lines.append("# Stage 17 / Week 16 · Part A：漏解污染上限（P1 → P2 台阶）")
    lines.append("")
    lines.append("## 0. 一句话结论")
    lines.append("")
    lines.append("把 P1→P2 台阶的 P2 腿换成 moread 臂后，两条轴的 tau_b / Top-k 重叠 / "
                 "f_unresolved / f_robust_inv %s；两臂 tau_b 的 95%% CI %s。"
                 % ("被改写" if verdict["any_published_conclusion_rewritten"] else "均未被改写",
                    "重叠（污染被 CI 吸收）" if verdict["tau_b_ci_overlap_both_axes"]
                    else "不重叠（污染超出 CI）"))
    lines.append("")
    lines.append("## 1. 逐轴对照表（published / default / moread）")
    lines.append("")
    lines.append("| 轴 | 臂 | n | tau_b | tau_b 95% CI | O_20% | f_unresolved(after) | f_robust_inv | sigma 中位(eV) | shift 均值(eV) |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for title, _ in AXES:
        pub = pub_table[title]["published"]
        lines.append("| %s | **published** | %s | %s | [%s, %s] | %s | %s | %s | %s | %s |"
                     % (title, pub["n"], _fmt(pub["kendall_tau_b"]),
                        _fmt(pub["tau_b_ci_low"]), _fmt(pub["tau_b_ci_high"]),
                        _fmt(pub["overlap_20"]), _fmt(pub["f_unresolved_after"]),
                        _fmt(pub["f_robust_inv"]), _fmt(pub["sigma_median_ev"]),
                        _fmt(pub["shift_mean_ev"])))
        for arm in ARMS:
            r = per[title][arm]
            lines.append("| %s | %s | %s | %s | [%s, %s] | %s | %s | %s | %s | %s |"
                         % (title, arm, r.get("n"), _fmt(r.get("kendall_tau_b")),
                            _fmt(r.get("tau_b_ci_low")), _fmt(r.get("tau_b_ci_high")),
                            _fmt(r.get("overlap_20")), _fmt(r.get("f_unresolved_after")),
                            _fmt(r.get("f_robust_inv")), _fmt(r.get("sigma_median_ev")),
                            _fmt(r.get("shift_mean_ev"))))
    lines.append("")
    lines.append("## 2. moread − published 逐项 delta")
    lines.append("")
    lines.append("| 轴 | Δtau_b | ΔO_20% | Δf_unresolved(after) | Δf_robust_inv | Δsigma 中位 |")
    lines.append("| --- | --- | --- | --- | --- | --- |")
    for title, _ in AXES:
        d = pub_table[title]["moread_minus_published"]
        lines.append("| %s | %s | %s | %s | %s | %s |"
                     % (title, _fmt(d["kendall_tau_b"]), _fmt(d["overlap_20"]),
                        _fmt(d["f_unresolved_after"]), _fmt(d["f_robust_inv"]),
                        _fmt(d["sigma_median_ev"])))
    lines.append("")
    lines.append("## 3. delta = p2_moread − p2_default 统计")
    lines.append("")
    lines.append("| 粒度 | n | mean(eV) | std(eV) | min(eV) | max(eV) | argmin | argmax |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- | --- |")
    for label, key in (("54 格（分子×态）", "cells_54"),
                       ("18 分子（氧化轴）", "axis_oxidation_18"),
                       ("18 分子（还原轴）", "axis_reduction_18")):
        s = stats[key]
        lines.append("| %s | %s | %s | %s | %s | %s | %s | %s |"
                     % (label, s.get("n"), _fmt(s.get("mean_ev"), 6),
                        _fmt(s.get("std_ev"), 6), _fmt(s.get("min_ev"), 6),
                        _fmt(s.get("max_ev"), 6), s.get("argmin"), s.get("argmax")))
    lines.append("")
    lines.append("## 4. 符号检验（双侧为主，另附单侧）")
    lines.append("")
    lines.append("| 粒度 | 正 | 负 | 零 | 双侧 p | 单侧(正) p |")
    lines.append("| --- | --- | --- | --- | --- | --- |")
    for label, key in (("54 格（分子×态）", "cells_54"),
                       ("18 分子（氧化轴）", "axis_oxidation_18"),
                       ("18 分子（还原轴）", "axis_reduction_18")):
        s = sig[key]
        lines.append("| %s | %s | %s | %s | %s | %s |"
                     % (label, s["n_positive"], s["n_negative"], s["n_zero"],
                        _sig(s["p_two_sided"]), _sig(s["p_one_sided_greater"])))
    lines.append("")
    lines.append("## 5. 改变的格子（|delta| > 1e-3 eV）")
    lines.append("")
    changed = payload["cells_changed"]
    if not changed:
        lines.append("无：moread 与 default 的 54 格能量逐格差全部 <= 1e-3 eV。")
    else:
        lines.append("| 分子 | 态 | delta(eV) | 所属轴 |")
        lines.append("| --- | --- | --- | --- |")
        for item in changed:
            lines.append("| %s | %s | %s | %s |"
                         % (item["molecule"], item["state"], _fmt(item["delta_ev"], 6),
                            "+".join(item["axes"])))
    lines.append("")
    lines.append("## 6. 哪些结论被改写 / 未被改写")
    lines.append("")
    if verdict["conclusions_rewritten"]:
        lines.append("**被改写：**")
        for item in verdict["conclusions_rewritten"]:
            lines.append("- " + item)
    else:
        lines.append("**没有任何一条 published 结论被改写。**")
    lines.append("")
    lines.append("**未被改写：**")
    for item in verdict["conclusions_unchanged"]:
        lines.append("- " + item)
    lines.append("")
    lines.append("**三个 scenario verdict 复核：**")
    for key, block in verdict["scenario_verdicts"].items():
        lines.append("- **%s**（原判：%s）—— %s | 复核：%s"
                     % (key, block["published"], block["recheck"], block["assessment"]))
    lines.append("")
    lines.append("## 7. 上限声明（CI 是否吸收污染）")
    lines.append("")
    for title, _ in AXES:
        block = payload["ci_overlap"][title]
        lines.append("- **%s**：default CI = [%s, %s]，moread CI = [%s, %s]，重叠 = %s"
                     % (title, _fmt(block["default_ci"][0]), _fmt(block["default_ci"][1]),
                        _fmt(block["moread_ci"][0]), _fmt(block["moread_ci"][1]),
                        block["overlap"]))
    lines.append("")
    lines.append("CI 用法：Week 9 冻结设置（20 个 seed × 2000 次 paired bootstrap，"
                 "取百分位上下界的 20 次中位数）。")
    lines.append("")
    lines.append("## 8. 限制")
    lines.append("")
    for item in payload["limits"]:
        lines.append("- " + item)
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    return path

# --------------------------------------------------------------------------- #
# entry point
# --------------------------------------------------------------------------- #
def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Stage 17 / Week 16 part A -- contamination bound on the P1->P2 rung.")
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    parser.add_argument("--moread-csv", type=Path, default=DEFAULT_MOREAD)
    parser.add_argument("--reference-csv", type=Path, default=DEFAULT_REFERENCE)
    parser.add_argument("--effects-csv", type=Path, default=P2_EFFECTS)
    parser.add_argument("--draws", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=20260930)
    return parser.parse_args(argv)


def build_ladder_rows(payload) -> list:
    deltas = {"default": "default_minus_published", "moread": "moread_minus_published"}
    rows = []
    for title, _ in AXES:
        pub = payload["published_comparison"][title]["published"]
        for arm in ARMS:
            row = dict(payload["per_axis"][title][arm])
            row["published_kendall_tau_b"] = pub["kendall_tau_b"]
            row["published_overlap_20"] = pub["overlap_20"]
            row["published_f_unresolved_after"] = pub["f_unresolved_after"]
            row["published_f_robust_inv"] = pub["f_robust_inv"]
            block = payload["published_comparison"][title][deltas[arm]]
            row["delta_kendall_tau_b"] = block["kendall_tau_b"]
            row["delta_overlap_20"] = block["overlap_20"]
            row["delta_f_unresolved"] = block["f_unresolved_after"]
            row["delta_f_robust_inv"] = block["f_robust_inv"]
            rows.append(row)
    return rows


def main(argv=None) -> int:
    args = parse_args(argv)
    moread = Path(args.moread_csv)
    if not moread.exists():
        print("错误：未找到 moread 臂的 P2 产物 CSV：%s" % moread, file=sys.stderr)
        print("  该文件由另一个进程运行的 scripts/run_stage17_smd_moread.py 生成", file=sys.stderr)
        print("  （18 分子 x 3 态 = 54 格，通常全部完成后一次性写出）。", file=sys.stderr)
        print("  请等待其出现后重试，或用 --moread-csv 指定其它路径。", file=sys.stderr)
        return 2
    reference = Path(args.reference_csv)
    if not reference.exists():
        print("错误：未找到默认臂的参考 CSV：%s" % reference, file=sys.stderr)
        return 2
    effects = Path(args.effects_csv)
    if not effects.exists():
        print("错误：未找到 P1->P2 汇总 CSV：%s" % effects, file=sys.stderr)
        return 2

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    payload = analyze(moread, reference, effects, args.draws, args.seed)
    public = {k: v for k, v in payload.items() if not k.startswith("_")}

    ladder_path = write_ladder_csv(outdir / "stage17_contamination_ladder.csv",
                                   build_ladder_rows(payload))
    cells_path = write_cells_csv(outdir / "stage17_contamination_cells.csv",
                                 payload["_cell_rows"])
    json_path = outdir / "stage17_contamination.json"
    json_path.write_text(json.dumps(public, indent=2, ensure_ascii=False) + "\n",
                         encoding="utf-8", newline="\n")
    summary_path = write_summary(outdir / "stage17_contamination_summary.md", public)

    print(json.dumps({
        "stage": payload["stage"],
        "moread_csv": relative(moread),
        "cells_changed": payload["cells_changed_count"],
        "oxidation_tau_b": {"default": payload["per_axis"]["oxidation"]["default"].get("kendall_tau_b"),
                            "moread": payload["per_axis"]["oxidation"]["moread"].get("kendall_tau_b")},
        "reduction_tau_b": {"default": payload["per_axis"]["reduction"]["default"].get("kendall_tau_b"),
                            "moread": payload["per_axis"]["reduction"]["moread"].get("kendall_tau_b")},
        "any_published_conclusion_rewritten": payload["verdict"]["any_published_conclusion_rewritten"],
        "ladder_csv": relative(ladder_path),
        "cells_csv": relative(cells_path),
        "json": relative(json_path),
        "summary": relative(summary_path),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())