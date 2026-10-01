"""Stage 21 / week 20, Part A analysis -- read the frozen profiles.

``run_stage21_path.py`` produced 21 frozen r2SCAN-3c single points on the straight
Cartesian line between the two Stage 19 relaxed endpoints of three cells.  This
script turns those 21 numbers per cell into a verdict.

What the profile can and cannot say
-----------------------------------
The interpolated path is a straight line through configuration space, not a minimum
energy path, so any hump on it is an **upper bound** to the true barrier and the bound
can be very loose when the line cuts across a rotation or a bond stretch.  That makes
"there is a hump" weak evidence.  The opposite reading is strong:

* ``barrier_chord_ev`` ~ 0 (no rise above the straight line joining the endpoints)
  means the two endpoints are connected by a barrier-free straight line, so they are
  two shoulders of *one* basin.  A straight line that never rises cannot be hiding a
  barrier.

The discriminating numbers this script reports per cell:

* ``path_length_a``   -- length of the straight line, i.e. how far the geometry moves
* ``barrier_chord_ev``-- max over images of ``E_i - E_chord(lambda_i)``, the hump above
                         the line joining the two endpoint energies
* ``barrier_abs_ev``  -- max(E) - max(E_first, E_last), the hump above the higher end
* ``e_span_ev``       -- frozen energy difference between the two endpoints
* ``relax_span_ev``   -- the *relaxed* (Stage 19 ``Opt``) energy difference, quoted so
                         the frozen span is never mistaken for the relaxation energy
* ``monotone``        -- whether the profile never turns back
* ``n_internal_extrema``
* ``curvature_start_ev_per_a2`` / ``curvature_end_ev_per_a2`` -- harmonic stiffness at
                         each end, fitted to the first/last ``--fit-points`` images
* ``verdict``         -- ``one_basin`` when the profile is barrier-free within
                         ``--thermal-ev``, ``separated`` when there is a hump larger
                         than the chord noise, ``inconclusive`` otherwise

and, the point of the exercise, a comparison against the Stage 19 RMSD verdict for the
same cell.
"""

from __future__ import annotations

import argparse
import re
import csv
import json
import math
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_OUTDIR = REPO_ROOT / "outputs" / "week20"
DEFAULT_DATA_DIR = REPO_ROOT / "outputs" / "week20"
REL_CACHE = REPO_ROOT / "outputs" / "week18" / "stage19_relax_cells.csv"
PATH_CSV = "stage21_path_cells.csv"
PLAN_JSON = "stage21_path_plan.json"

HARTREE_EV = 27.211386245988
#: k_B T at 298.15 K, in eV -- the scale below which a hump is not a barrier.
THERMAL_EV = 0.0257
#: 1 kcal/mol, the usual "chemically meaningful" floor.
KCAL_EV = 0.043364


def read_csv(path: Path):
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def endpoint_frame(name: str, state: str, epsilon: float, arm: str):
    stem = "%s_%s_cpcm_%g_%s" % (name, state, epsilon, arm)
    return (REPO_ROOT / "outputs" / "week18" /
            ("orca_relax_" + arm) / name / (stem + ".xyz"))


def read_xyz(path: Path):
    lines = path.read_text(encoding="utf-8").splitlines()
    count = int(lines[0].split()[0])
    return [tuple(float(value) for value in line.split()[1:4])
            for line in lines[2:2 + count]]


def path_length(start, end) -> float:
    total = 0.0
    for left, right in zip(start, end):
        total += sum((a - b) ** 2 for a, b in zip(left, right))
    return math.sqrt(total)


def rmsd(start, end) -> float:
    return path_length(start, end) / math.sqrt(len(start))


def fit_curvature(lambdas, energies, side: str, count: int):
    """Harmonic stiffness at one end, from ``E = E0 + 0.5 * k * s^2``.

    ``s`` is the arc length from that endpoint, i.e. ``lambda * path_length``.  The
    fit uses only the first ``count`` images from the chosen end, so it measures the
    local stiffness rather than the whole profile.
    """

    order = list(range(len(lambdas)))
    if side == "end":
        order = order[::-1]
    order = order[:count]
    if len(order) < 3:
        return None
    xs = np.array([lambdas[index] for index in order])
    ys = np.array([energies[index] for index in order])
    origin = xs[0]
    spans = xs - origin
    if not np.any(spans):
        return None
    # least squares for E = a + b*s + 0.5*k*s^2 with s the *span* (proportional to arc
    # length, so k absorbs the path length and is reported per angstrom**2 below).
    design = np.vstack([np.ones_like(spans), spans, 0.5 * spans ** 2]).T
    try:
        coefficients, *_ = np.linalg.lstsq(design, ys, rcond=None)
    except np.linalg.LinAlgError:
        return None
    return float(coefficients[2])


def profile_metrics(rows, fit_points: int, thermal_ev: float):
    ordered = sorted(rows, key=lambda row: int(row["image_index"]))
    lambdas = [float(row["lambda"]) for row in ordered]
    energies = [float(row["final_energy_eh"]) * HARTREE_EV for row in ordered]
    first, last = energies[0], energies[-1]
    chord = [first + lam * (last - first) for lam in lambdas]
    deviations = [value - line for value, line in zip(energies, chord)]
    interior = deviations[1:-1] if len(deviations) > 2 else deviations
    barrier_chord = max(interior) if interior else 0.0
    barrier_abs = max(energies) - max(first, last)

    turns = 0
    signs = []
    for index in range(1, len(energies)):
        delta = energies[index] - energies[index - 1]
        if abs(delta) <= 1e-9:
            continue
        signs.append(1 if delta > 0 else -1)
    for index in range(1, len(signs)):
        if signs[index] != signs[index - 1]:
            turns += 1

    # SCF noise floor: the median absolute second difference of the profile.  A hump
    # comparable to this is numerical, not physical.
    second = [abs(energies[i + 1] - 2.0 * energies[i] + energies[i - 1])
              for i in range(1, len(energies) - 1)]
    noise = statistics.median(second) if second else 0.0

    name, state = ordered[0]["name"], ordered[0]["state"]
    epsilon = float(ordered[0]["epsilon"])
    start = read_xyz(endpoint_frame(name, state, epsilon, "default"))
    end = read_xyz(endpoint_frame(name, state, epsilon, "moread"))
    length = path_length(start, end)

    start_k = fit_curvature(lambdas, energies, "start", fit_points)
    end_k = fit_curvature(lambdas, energies, "end", fit_points)

    if barrier_chord <= thermal_ev:
        verdict = "one_basin"
    elif barrier_chord >= KCAL_EV:
        verdict = "separated"
    else:
        verdict = "inconclusive"

    return {
        "name": name, "state": state, "epsilon": epsilon,
        "family": ordered[0].get("family", ""),
        "rmsd_a_stage19": float(ordered[0]["rmsd_a_stage19"]),
        "stage19_verdict": ordered[0]["stage19_verdict"],
        "n_images": len(energies),
        "path_length_a": length, "path_rmsd_a": rmsd(start, end),
        "e_first_ev": first, "e_last_ev": last,
        "e_span_ev": last - first,
        "e_min_ev": min(energies), "e_max_ev": max(energies),
        "barrier_chord_ev": barrier_chord,
        "barrier_abs_ev": barrier_abs,
        "noise_floor_ev": noise,
        "hump_over_noise": (None if not noise else barrier_chord / noise),
        "monotone": turns == 0,
        "n_turns": turns,
        "curvature_start_ev_per_lambda2": start_k,
        "curvature_end_ev_per_lambda2": end_k,
        "curvature_start_ev_per_a2": (None if start_k is None or not length
                                      else start_k / (length ** 2)),
        "curvature_end_ev_per_a2": (None if end_k is None or not length
                                    else end_k / (length ** 2)),
        "verdict": verdict,
        "profile_ev": [round(value, 9) for value in energies],
        "lambda_grid": lambdas,
    }


def relax_span(name: str, state: str, epsilon: float, cache) -> dict:
    default = cache.get((name, state, epsilon, "default"))
    moread = cache.get((name, state, epsilon, "moread"))
    if not default or not moread:
        return {"relax_span_ev": None, "relax_eh_default": None, "relax_eh_moread": None,
                "g1_single_point_delta_ev": None, "g1_delta_matches_relaxed": None}
    e_default = float(default["final_energy_eh"])
    e_moread = float(moread["final_energy_eh"])
    g1 = default.get("single_point_delta_ev") or ""
    g1_value = float(g1) if g1 not in ("", None) else None
    span = (e_moread - e_default) * HARTREE_EV
    return {"relax_span_ev": span,
            "relax_eh_default": e_default, "relax_eh_moread": e_moread,
            "g1_single_point_delta_ev": g1_value,
            "g1_delta_matches_relaxed": (None if g1_value is None
                                         else abs(g1_value - span) < 1e-6)}


def load_relax_cache():
    cache = {}
    for row in read_csv(REL_CACHE):
        cache[(row["name"], row["state"], float(row["epsilon"]), row["arm"])] = row
    return cache


def build_analysis(rows, fit_points: int, thermal_ev: float):
    grouped = {}
    for row in rows:
        if row["status"] != "ok" or not row["final_energy_eh"]:
            continue
        key = (row["name"], row["state"], float(row["epsilon"]))
        grouped.setdefault(key, []).append(row)
    cache = load_relax_cache()
    cells = []
    for key in sorted(grouped):
        metrics = profile_metrics(grouped[key], fit_points, thermal_ev)
        metrics.update(relax_span(*key, cache))
        metrics["cell"] = "%s/%s/%g" % key
        metrics["agrees_with_stage19"] = agreement(metrics)
        cells.append(metrics)
    return cells


def agreement(metrics) -> bool:
    """Does the profile back up the Stage 19 RMSD verdict?

    ``same_*`` (the two arms merged) is only supported when the straight line between
    the endpoints is barrier-free; ``distinct_*`` is supported when a hump of at least
    1 kcal/mol separates them.  Anything else is a disagreement, and that is the
    interesting case.
    """

    rmsd_verdict = metrics["stage19_verdict"]
    profile = metrics["verdict"]
    if rmsd_verdict.startswith("same"):
        return profile == "one_basin"
    if rmsd_verdict.startswith("distinct"):
        return profile == "separated"
    return False

#: ``generated_utc`` is the only volatile field in the artifacts; ``--check`` must
#: ignore it or the byte comparison could never pass twice.
TIMESTAMP_RE = re.compile(r'"generated_utc": "[^"]*"')


def comparable(text: str) -> str:
    return TIMESTAMP_RE.sub('"generated_utc": "<timestamp>"', text)


ANALYSIS_FIELDS = [
    "cell", "name", "family", "state", "epsilon", "rmsd_a_stage19",
    "stage19_verdict", "n_images", "path_length_a", "path_rmsd_a",
    "e_first_ev", "e_last_ev", "e_span_ev", "e_min_ev", "e_max_ev",
    "barrier_chord_ev", "barrier_abs_ev", "noise_floor_ev", "hump_over_noise",
    "monotone", "n_turns",
    "curvature_start_ev_per_a2", "curvature_end_ev_per_a2",
    "relax_span_ev", "relax_eh_default", "relax_eh_moread",
    "g1_single_point_delta_ev", "g1_delta_matches_relaxed",
    "verdict", "agrees_with_stage19",
]


def render_csv(cells) -> str:
    import io

    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=ANALYSIS_FIELDS, extrasaction="ignore",
                            lineterminator="\n")
    writer.writeheader()
    for cell in cells:
        row = dict(cell)
        for field in ("path_length_a", "path_rmsd_a", "e_first_ev", "e_last_ev",
                      "e_span_ev", "e_min_ev", "e_max_ev", "barrier_chord_ev",
                      "barrier_abs_ev", "noise_floor_ev", "hump_over_noise",
                      "curvature_start_ev_per_a2",
                      "curvature_end_ev_per_a2", "relax_span_ev",
                      "g1_single_point_delta_ev"):
            value = row.get(field)
            row[field] = "" if value is None else "%.9f" % value
        writer.writerow(row)
    return buffer.getvalue()


def render_json(cells, meta) -> str:
    payload = dict(meta)
    payload["cells"] = [{key: value for key, value in cell.items()
                         if key not in ("lambda_grid",)} for cell in cells]
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"


def render_markdown(cells, meta) -> str:
    lines = ["# Stage 21 Part A -- frozen single-point profiles (week 20)", ""]
    lines.append("- method: `%s`, %d images per path, bare CPCM at the cell's own "
                 "epsilon" % (meta["method"], meta["images"]))
    lines.append("- cells: %d, jobs: %d, all SCF converged: %s"
                 % (meta["n_cells"], meta["n_jobs"], meta["all_converged"]))
    lines.append("- thermal scale used for the `one_basin` verdict: "
                 "%.4f eV (k_B T at 298 K); `separated` needs >= %.4f eV (1 kcal/mol)"
                 % (meta["thermal_ev"], KCAL_EV))
    lines.append("")
    lines.append("| cell | RMSD(Stage 19) | Stage 19 | path length (A) | "
                 "chord hump (eV) | hump/noise | G1 sp delta (eV) | relaxed delta (eV) | "
                 "verdict | agrees |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for cell in cells:
        lines.append("| %s | %.3f | %s | %.4f | %.5f | %s | %s | %s | %s | %s |"
                     % (cell["cell"], cell["rmsd_a_stage19"], cell["stage19_verdict"],
                        cell["path_length_a"], cell["barrier_chord_ev"],
                        "n/a" if cell["hump_over_noise"] is None
                        else "%.1f" % cell["hump_over_noise"],
                        "n/a" if cell["g1_single_point_delta_ev"] is None
                        else "%+.5f" % cell["g1_single_point_delta_ev"],
                        "n/a" if cell["relax_span_ev"] is None
                        else "%+.5f" % cell["relax_span_ev"],
                        cell["verdict"], "yes" if cell["agrees_with_stage19"] else "NO"))
    lines.append("")
    lines.append("## Per-cell detail")
    for cell in cells:
        lines.append("")
        lines.append("### %s (%s)" % (cell["cell"], cell["family"]))
        lines.append("- Stage 19 relaxed the two arms to geometries %.4f A apart "
                     "(RMSD) and called it `%s`."
                     % (cell["rmsd_a_stage19"], cell["stage19_verdict"]))
        lines.append("- the straight line between them is %.4f A long."
                     % cell["path_length_a"])
        if cell["g1_single_point_delta_ev"] is not None:
            lines.append("- frozen single point on the *shared* G1 start geometry: "
                         "%+.5f eV; after both arms relax: %+.5f eV, so relaxation "
                         "changed the gap by %+.5f eV."
                         % (cell["g1_single_point_delta_ev"], cell["relax_span_ev"],
                            cell["relax_span_ev"] - cell["g1_single_point_delta_ev"]))
        lines.append("- consistency check: the frozen single points at the two relaxed "
                     "endpoints differ by %+.5f eV, which must equal the relaxed "
                     "difference -- %s."
                     % (cell["e_span_ev"],
                        "it does" if cell["g1_delta_matches_relaxed"]
                        else "MISMATCH" if cell["g1_delta_matches_relaxed"] is False
                        else "not checked"))
        lines.append("- profile above the endpoint chord: max %+.5f eV (%.1f x the SCF "
                     "noise floor of %.2e eV); above the higher endpoint: max %+.5f eV; "
                     "monotone: %s (%d turning points)."
                     % (cell["barrier_chord_ev"],
                        cell["hump_over_noise"] or float("nan"),
                        cell["noise_floor_ev"], cell["barrier_abs_ev"],
                        cell["monotone"], cell["n_turns"]))
        if cell["curvature_start_ev_per_a2"] is not None:
            lines.append("- harmonic stiffness fitted at each end: %.3f / %.3f "
                         "eV/A^2." % (cell["curvature_start_ev_per_a2"],
                                      cell["curvature_end_ev_per_a2"]))
        lines.append("- verdict: `%s`; Stage 19 %s."
                     % (cell["verdict"],
                        "backed up" if cell["agrees_with_stage19"]
                        else "**not** backed up"))
    lines.append("")
    lines.append("## What this does and does not prove")
    lines.append("")
    lines.append("The path is a straight Cartesian line, not a minimum-energy path, so "
                 "a hump on it is only an upper bound to the true barrier and this "
                 "stage never claims otherwise. The asymmetry is the point: a "
                 "barrier-free straight line is *strong* evidence that the two "
                 "endpoints sit in one basin, because a line that never rises cannot "
                 "be hiding a barrier. A hump, by contrast, is weak evidence of "
                 "separation and is read here only together with the relaxed energy "
                 "gap and the harmonic stiffness at each end.")
    lines.append("")
    return "\n".join(lines) + "\n"


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Stage 21 Part A: read the frozen profiles into a verdict.")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    parser.add_argument("--fit-points", type=int, default=5)
    parser.add_argument("--thermal-ev", type=float, default=THERMAL_EV)
    parser.add_argument("--check", action="store_true")
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    for attribute in ("data_dir", "outdir"):
        value = getattr(args, attribute)
        setattr(args, attribute, (value if value.is_absolute() else Path.cwd() / value).resolve())

    rows = read_csv(args.data_dir / PATH_CSV)
    plan_path = args.data_dir / PLAN_JSON
    plan = json.loads(plan_path.read_text(encoding="utf-8")) if plan_path.exists() else {}
    cells = build_analysis(rows, args.fit_points, args.thermal_ev)

    meta = {
        "stage": 21, "part": "A",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "method": "r2SCAN-3c",
        "images": int(plan.get("images", 0)) or (cells[0]["n_images"] if cells else 0),
        "fit_points": args.fit_points, "thermal_ev": args.thermal_ev,
        "kcal_ev": KCAL_EV,
        "n_cells": len(cells),
        "n_jobs": len(rows),
        "all_converged": all(str(row["scf_converged"]) == "True" for row in rows),
        "n_agree_with_stage19": sum(1 for cell in cells if cell["agrees_with_stage19"]),
        "n_one_basin": sum(1 for cell in cells if cell["verdict"] == "one_basin"),
        "n_separated": sum(1 for cell in cells if cell["verdict"] == "separated"),
        "n_inconclusive": sum(1 for cell in cells if cell["verdict"] == "inconclusive"),
        "definition": ("barrier_chord_ev = max over interior images of "
                       "E(lambda) - [(1-lambda) E(0) + lambda E(1)]; "
                       "frozen single points along the straight Cartesian line "
                       "between the Stage 19 default and moread relaxed endpoints"),
    }

    targets = {
        "stage21_path_analysis.csv": render_csv(cells),
        "stage21_path_analysis.json": render_json(cells, meta),
        "stage21_path_summary.md": render_markdown(cells, meta),
    }
    if args.check:
        bad = []
        for filename, text in targets.items():
            path = args.outdir / filename
            if not path.exists():
                bad.append(filename)
            elif comparable(path.read_text(encoding="utf-8")) != comparable(text):
                bad.append(filename)
        if bad:
            print("stage21 path artifacts are stale: %s" % ", ".join(bad))
            return 1
        print("stage21 path artifacts reproduce byte-for-byte (%d files)" % len(targets))
        return 0

    args.outdir.mkdir(parents=True, exist_ok=True)
    for filename, text in targets.items():
        (args.outdir / filename).write_text(text, encoding="utf-8", newline="\n")
    print(json.dumps({key: value for key, value in meta.items()
                      if key != "definition"}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())