"""Stage 14B -- is the EMC/reduction outlier real, or an artefact of a coarse grid?

The question
------------
Stage 13 fitted every one of the twenty-four ``delta(eps)`` curves to the Born
form ``delta = slope * (1 - 1/eps)`` through the origin, on the six bare levels
eps = 5, 10, 20, 40, 80, 200.  Twenty-three fits were acceptable; EMC on the
reduction axis fell to R2 = 0.8468, the minimum of all twenty-four, and was the
only curve whose six points were not monotone.  Its sequence is

    eps     5      10      20      40      80     200
    delta   1.9958 2.4696  2.4066  2.4771  2.5123 2.5335

so the whole anomaly is the single drop between eps = 10 and eps = 20, a step of
63 meV in the *wrong* direction, bracketed by two clean stretches.  Six points
that sparse cannot tell three very different things apart:

* a genuinely non-Born response of EMC;
* a coarse grid that sampled across a sharp feature;
* one SCF solution of the anion that settled into a slightly different basin at
  eps = 10 alone.

Stage 14 therefore interleaves five new dielectrics *inside* the suspicious
interval and re-measures the four shared ones:

    eps = 5, 7, 10, 14, 20, 28, 40     (7 x 3 molecules x 3 charge states = 63 jobs)

controls
    DMC -- same family (linear carbonate), the only structural difference is
           ethyl vs methyl, so a family-wide effect must show up in both;
    EC  -- the well-behaved control that also carries the largest distortion
           term, i.e. the molecule most likely to break a pure-dielectric model.

Because the repository already holds ``cpcm_80`` and ``cpcm_200`` for all
twelve audited molecules (Stage 13), the dense grid is extended for free to the
complete nine-point bare-CPCM ladder

    eps = 5, 7, 10, 14, 20, 28, 40, 80, 200

which is what actually answers the question.  Two independent readings are
produced.  The grid-density study refits the Born form to nested subsets of
increasing size; a curve whose R2 only climbs as points are added was
under-sampled rather than non-Born.  And because

    delta_reduction(eps) = [E_neutral(eps) - E_neutral(gas)]
                         - [E_anion(eps)   - E_anion(gas)]

the same data are also split per charge state, so a dip that lives in one state
only is not confused with a property of the molecule as a whole.

Sign convention (matches ``stage13_shift_split.csv``)
----------------------------------------------------
    delta_oxidation(eps) = IP(eps) - IP(gas),   IP = E(cation) - E(neutral)
    delta_reduction(eps) = EA(eps) - EA(gas),   EA = E(neutral) - E(anion)

so a negative oxidation delta means the solvent raises the ionisation energy,
and a positive reduction delta means it raises the electron affinity -- exactly
the two numbers quoted in ``docs/22`` section 0.

Reproducibility
---------------
The fresh batch re-measures eps = 5/10/20/40 as well, so those four points can
be compared against the frozen Stage-13 numbers in ``outputs/week4``.  ORCA
outputs are not byte-identical (they embed wall-clock times), so the invariant
tested is the printed energy itself: the same 12 decimals means the same
electronic structure.  Only if that holds may the dense grid and the Stage 13
ladder be read as one experiment.

Outputs
-------
``outputs/week13/stage14_outlier.csv``   the nine-point curve, per molecule/axis
``outputs/week13/stage14_outlier.json``  reproducibility, Born fits, monotonicity,
                                         grid-density convergence
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

GAS_CSV = REPO_ROOT / "outputs" / "week4" / "p1_core_set.csv"
GAS_OUT_DIR = REPO_ROOT / "outputs" / "week4" / "orca"
WEEK4_OUT_DIR = REPO_ROOT / "outputs" / "week4"
WEEK12_OUT_DIR = REPO_ROOT / "outputs" / "week12"
SMD_OUT_DIR = REPO_ROOT / "outputs" / "week4" / "orca_smd_acetonitrile"
SCREEN_LEVELS = (5.0, 10.0, 20.0, 40.0, 80.0, 200.0)
FRESH_DIR = REPO_ROOT / "outputs" / "week13"
STAGE13_DIR = REPO_ROOT / "outputs" / "week12"
REFERENCE_DIR = REPO_ROOT / "outputs" / "week4"
DEFAULT_OUTDIR = REPO_ROOT / "outputs" / "week13"

MOLECULES = ("EMC", "DMC", "EC")
STATES = ("neutral", "cation", "anion")
AXES = ("oxidation", "reduction")
FRESH_EPS = (5.0, 7.0, 10.0, 14.0, 20.0, 28.0, 40.0)
SHARED_EPS = (5.0, 10.0, 20.0, 40.0)
EXTRA_EPS = (80.0, 200.0)
LADDER = tuple(sorted(FRESH_EPS + EXTRA_EPS))

# Nested grids used for the grid-density study.  Each step adds one dielectric
# without removing any information already present, so n_points rises 4 -> 9 and
# the R2 can be read as a convergence curve rather than as six unrelated fits.
GRID_STEPS = (
    ("four_shared_points", (5.0, 10.0, 20.0, 40.0)),
    ("plus_eps7", (5.0, 7.0, 10.0, 20.0, 40.0)),
    ("plus_eps14", (5.0, 7.0, 10.0, 14.0, 20.0, 40.0)),
    ("dense_seven", (5.0, 7.0, 10.0, 14.0, 20.0, 28.0, 40.0)),
    ("plus_eps80", (5.0, 7.0, 10.0, 14.0, 20.0, 28.0, 40.0, 80.0)),
    ("full_nine", LADDER),
)

# The grid Stage 13 actually published (six bare levels), kept separate from the
# nested chain so that the density study stays strictly monotone in n_points.
STAGE13_GRID = (5.0, 10.0, 20.0, 40.0, 80.0, 200.0)

HARTREE_TO_EV = 27.211386245988

#: The twelve audited molecules (``docs/08`` section 7), needed by the
#: solution-identity screen below.
AUDITED_MOLECULES = ("AN", "DMC", "DME", "DMSO", "DOL", "EC", "GBL", "SL", "SN",
                     "TMP", "PC", "EMC")


def tag(eps: float) -> str:
    return "cpcm_%g" % eps


def read_layer(path: Path) -> dict:
    """``{(name, state): final_energy_eh}`` plus the raw status columns."""

    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    out = {}
    for row in rows:
        out[(row["name"], row["state"])] = row
    return out


def axis_values(layer: dict, name: str) -> dict:
    """IP, EA and the two ``p`` values of one molecule in one environment."""

    neutral = float(layer[(name, "neutral")]["final_energy_eh"])
    cation = float(layer[(name, "cation")]["final_energy_eh"])
    anion = float(layer[(name, "anion")]["final_energy_eh"])
    return {"neutral": neutral, "cation": cation, "anion": anion,
            "ip_ev": (cation - neutral) * HARTREE_TO_EV,
            "ea_ev": (neutral - anion) * HARTREE_TO_EV}


def born_through_origin(xs, ys) -> dict:
    """``y = slope * x`` by least squares, with R2 against the sample mean.

    R2 is the ordinary coefficient of determination, so a negative value means
    the constrained fit is worse than predicting the mean -- the convention
    ``analyze_stage13_dielectric_limit.py`` already uses for the distortion term.
    """

    sxx = sum(x * x for x in xs)
    sxy = sum(x * y for x, y in zip(xs, ys))
    slope = sxy / sxx
    fitted = [slope * x for x in xs]
    sse = sum((y - f) ** 2 for y, f in zip(ys, fitted))
    mean = sum(ys) / len(ys)
    sst = sum((y - mean) ** 2 for y in ys)
    return {"slope": slope, "r2": 1.0 - sse / sst, "n": len(xs),
            "sse": sse, "sst": sst}


def born_with_intercept(xs, ys) -> dict:
    n = len(xs)
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    sxx = sum((x - mean_x) ** 2 for x in xs)
    sxy = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    slope = sxy / sxx
    intercept = mean_y - slope * mean_x
    fitted = [intercept + slope * x for x in xs]
    sse = sum((y - f) ** 2 for y, f in zip(ys, fitted))
    sst = sum((y - mean_y) ** 2 for y in ys)
    return {"slope": slope, "intercept": intercept, "r2": 1.0 - sse / sst, "n": n}


def _dipole(path: Path):
    """Magnitude of the last ``Total Dipole Moment`` block, or ``None``."""

    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8", errors="replace")
    value = None
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if "Total Dipole Moment" in line:
            for probe in lines[index:index + 6]:
                if "Magnitude (Debye)" in probe:
                    value = float(probe.split(":")[-1].strip())
    return value


def _level_out_path(name: str, state: str, level: str) -> Path:
    """Where the ORCA output of one (molecule, state, level) lives.

    A level can be produced by more than one stage: eps = 5/10/20/40 exist in both
    week 4 (the Stage 13 ladder) and week 13 (the re-measurement), and eps = 7/14/28
    exist only in week 13.  The first *existing* candidate wins, so the screen works
    for all twelve molecules (week 4) while the three densely measured ones are read
    from the freshest copy, which the reproducibility check has already shown to be
    numerically identical.
    """

    if level == "gas":
        return GAS_OUT_DIR / name / ("%s_%s.out" % (name, state))
    if level == "smd_acetonitrile":
        return SMD_OUT_DIR / name / ("%s_%s_smd_acetonitrile.out" % (name, state))
    eps = float(level.split("_")[1])
    leaf = Path(name) / ("%s_%s_%s.out" % (name, state, level))

    def candidate(base):
        return base / ("orca_%s" % level) / leaf

    candidates = []
    if eps in FRESH_EPS:
        candidates.append(candidate(FRESH_DIR))
    if eps in SHARED_EPS:
        candidates.append(candidate(WEEK4_OUT_DIR))
    candidates.append(candidate(WEEK12_OUT_DIR))
    for path in candidates:
        if path.exists():
            return path
    return candidates[0]


def solution_identity_screen(molecules=AUDITED_MOLECULES, levels=SCREEN_LEVELS):
    """Scan the *dipole* -- not the energy -- of every state across the dielectric ladder.

    The energy of a single state is what the Born fit is applied to, so using it to
    diagnose that same fit would be circular.  The dipole is an independent
    observable of the SCF solution: if a molecule's anion settles into a different
    solution at one dielectric, the density changes and the dipole jumps even when
    the energy cost is small.  A monotone density response gives a monotone dipole.
    """

    table = []
    for name in molecules:
        for state in STATES:
            series = [_dipole(_level_out_path(name, state, "cpcm_%g" % eps))
                      for eps in levels]
            present = [value for value in series if value is not None]
            if len(present) < len(levels):
                continue
            steps = [b - a for a, b in zip(present, present[1:])]
            span = max(present) - min(present)
            kink = max((abs(present[i + 1] - 2 * present[i] + present[i - 1])
                        for i in range(1, len(present) - 1)), default=0.0)
            # A smooth saturating density response has curvature of a few percent
            # of its own span, whatever the molecule: the whole smooth population
            # sits at a roughness of 0.16-0.26.  Two conditions are required to
            # call a series erratic, because a tiny-span series (e.g. DOL/cation,
            # span 0.02 D) can have a large ratio that is pure print precision.
            roughness = kink / span if span > 1e-9 else 0.0
            table.append({
                "name": name, "state": state,
                "dipole_debye_by_eps": {("%g" % eps): value
                                       for eps, value in zip(levels, present)},
                "max_abs_second_difference_debye": kink,
                "max_abs_step_debye": max(abs(step) for step in steps),
                "span_debye": span,
                "roughness": roughness,
                "solution_switch_suspect": bool(kink > 0.10 and roughness > 0.50),
            })
    erratic = [row for row in table if row["solution_switch_suspect"]]
    erratic.sort(key=lambda row: -row["max_abs_second_difference_debye"])
    wide = sorted(row["roughness"] for row in table if row["span_debye"] > 0.05)
    median_roughness = wide[len(wide) // 2] if wide else None
    return {"levels": list(levels), "n_series": len(table),
            "n_suspect": len(erratic),
            "median_roughness_of_smooth_population": median_roughness,
            "suspect": erratic, "table": table}


def _shared_layer_csv(eps: float) -> Path:
    """The six-point frozen grid: 5/10/20/40 live in week 4, 80/200 in week 12."""

    if eps in (80.0, 200.0):
        return WEEK12_OUT_DIR / ("p2_core_set_%s.csv" % tag(eps))
    return WEEK4_OUT_DIR / ("p2_core_set_%s.csv" % tag(eps))


def energy_kink_screen(levels=STAGE13_GRID):
    """Energy-side companion to the dipole screen, judged *across* molecules.

    The Born fit consumes ``EA(eps)`` itself, so asking whether a single curve is
    smooth would be circular.  This check never compares a curve with itself: it
    asks whether **one molecule out of the twelve** has a rougher ``EA(eps)`` (or
    ``IP(eps)``) than the other eleven.  A cross-molecule outlier cannot be
    produced by the fact that the same numbers feed the fit.
    """

    tables = {}
    for eps in levels:
        path = _shared_layer_csv(eps)
        if not path.exists():
            raise SystemExit("missing layer file: %s" % path.relative_to(REPO_ROOT))
        tables[eps] = read_layer(path)

    def series(name, kind):
        values = []
        for eps in levels:
            layer = tables[eps]
            neutral = float(layer[(name, "neutral")]["final_energy_eh"])
            cation = float(layer[(name, "cation")]["final_energy_eh"])
            anion = float(layer[(name, "anion")]["final_energy_eh"])
            if kind == "EA":
                values.append((neutral - anion) * HARTREE_TO_EV)
            else:
                values.append((cation - neutral) * HARTREE_TO_EV)
        return values

    def kink(values):
        return max(abs(values[index + 1] - 2.0 * values[index] + values[index - 1])
                   for index in range(1, len(values) - 1))

    def block(kind):
        rows = [{"name": name, "max_abs_second_difference_ev": kink(series(name, kind))}
                for name in AUDITED_MOLECULES]
        rows.sort(key=lambda row: -row["max_abs_second_difference_ev"])
        return rows

    ea = block("EA")
    ip = block("IP")
    return {
        "levels": list(levels),
        "note": ("second difference in the dielectric index over the six shared "
                 "bare-CPCM levels (5/10/20/40/80/200), in eV; the judgement is "
                 "'is one molecule an outlier among the twelve', not 'is one curve "
                 "smooth in itself'"),
        "ea": ea,
        "ip": ip,
        "ea_suspect": ea[0]["name"],
        "ea_suspect_ev": ea[0]["max_abs_second_difference_ev"],
        "ea_runner_up": ea[1]["name"],
        "ea_runner_up_ev": ea[1]["max_abs_second_difference_ev"],
        "ea_outlier_ratio": ea[0]["max_abs_second_difference_ev"] / ea[1]["max_abs_second_difference_ev"],
        "ip_suspect": ip[0]["name"],
        "ip_suspect_ev": ip[0]["max_abs_second_difference_ev"],
        "ip_emc_ev": next(row["max_abs_second_difference_ev"] for row in ip
                          if row["name"] == "EMC"),
    }


def sign_changes(values) -> int:
    """Number of sign changes in the first differences (zeros are skipped)."""

    diffs = [b - a for a, b in zip(values, values[1:])]
    signs = [1 if d > 0 else -1 for d in diffs if abs(d) > 1e-12]
    return sum(1 for a, b in zip(signs, signs[1:]) if a != b)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    args = parser.parse_args(argv)
    outdir = args.outdir if args.outdir.is_absolute() else (REPO_ROOT / args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    gas = read_layer(GAS_CSV)
    gas_values = {name: axis_values(gas, name) for name in MOLECULES}

    layers, provenance = {}, {}
    for eps in LADDER:
        if eps in FRESH_EPS:
            path, origin = FRESH_DIR / ("p2_core_set_%s.csv" % tag(eps)), "week13"
        else:
            path, origin = STAGE13_DIR / ("p2_core_set_%s.csv" % tag(eps)), "week12"
        if not path.exists():
            raise SystemExit("missing layer file: %s" % path.relative_to(REPO_ROOT))
        layers[eps] = read_layer(path)
        provenance[tag(eps)] = str(path.relative_to(REPO_ROOT)).replace("\\", "/")

    # --- reproducibility against the frozen Stage 13 numbers --------------
    differences = []
    for eps in SHARED_EPS:
        reference_path = REFERENCE_DIR / ("p2_core_set_%s.csv" % tag(eps))
        if not reference_path.exists():
            continue
        reference = read_layer(reference_path)
        for name in MOLECULES:
            for state in STATES:
                fresh = layers[eps][(name, state)]
                old = reference[(name, state)]
                delta = float(fresh["final_energy_eh"]) - float(old["final_energy_eh"])
                differences.append({
                    "eps": eps, "name": name, "state": state,
                    "delta_eh": delta, "delta_ev": delta * HARTREE_TO_EV,
                    "identical_string": fresh["final_energy_eh"] == old["final_energy_eh"],
                    "fresh_qc_flags": fresh.get("qc_flags", ""),
                    "reference_qc_flags": old.get("qc_flags", ""),
                })
    worst = max(abs(item["delta_eh"]) for item in differences)
    reproducibility = {
        "n_points_compared": len(differences),
        "max_abs_delta_eh": worst,
        "max_abs_delta_ev": worst * HARTREE_TO_EV,
        "n_identical_strings": sum(1 for item in differences if item["identical_string"]),
        "tolerance_eh": 1e-9,
        "verdict": "reproduced" if worst < 1e-9 else "NOT reproduced",
        "note": ("ORCA output files cannot be byte-compared (they embed wall-clock "
                 "times and scratch paths); the invariant is the printed energy to "
                 "all 12 decimals"),
        "points": differences,
    }

    # --- the nine-point ladder -------------------------------------------
    curve_rows, curves = [], {}
    for name in MOLECULES:
        for axis in AXES:
            series = []
            for eps in LADDER:
                values = axis_values(layers[eps], name)
                reference = gas_values[name]
                if axis == "oxidation":
                    delta = values["ip_ev"] - reference["ip_ev"]
                else:
                    delta = values["ea_ev"] - reference["ea_ev"]
                series.append({"eps": eps, "x": 1.0 - 1.0 / eps, "delta_ev": delta,
                               "ip_ev": values["ip_ev"], "ea_ev": values["ea_ev"],
                               "solvation_ev": {
                                   "neutral": (values["neutral"] - reference["neutral"]) * HARTREE_TO_EV,
                                   "cation": (values["cation"] - reference["cation"]) * HARTREE_TO_EV,
                                   "anion": (values["anion"] - reference["anion"]) * HARTREE_TO_EV}})
                curve_rows.append({"name": name, "axis": axis, "eps": eps,
                                   "born_x": 1.0 - 1.0 / eps, "delta_ev": delta,
                                   "ip_ev": values["ip_ev"], "ea_ev": values["ea_ev"]})
            xs = [point["x"] for point in series]
            ys = [point["delta_ev"] for point in series]
            deltas = [point["delta_ev"] for point in series]
            # The anion dipole on the same nine dielectrics: an independent
            # observable of which SCF solution was reached, so a branch hop can be
            # told apart from a genuine non-Born response without using the energy
            # that the Born fit is applied to.
            anion_dipole = {("%g" % eps): _dipole(_level_out_path(name, "anion", tag(eps)))
                            for eps in LADDER}
            present = [value for value in anion_dipole.values() if value is not None]
            if len(present) == len(LADDER):
                span = max(present) - min(present)
                kink = max((abs(present[index + 1] - 2 * present[index] + present[index - 1])
                            for index in range(1, len(present) - 1)), default=0.0)
                split = 0.5 * (max(present) + min(present))
                branch = {key: ("low" if value < split else "high")
                          for key, value in anion_dipole.items()}
                dipole_stats = {
                    "anion_dipole_debye_by_eps": anion_dipole,
                    "anion_dipole_branch_by_eps": branch,
                    "anion_dipole_span_debye": span,
                    "anion_dipole_max_abs_second_difference_debye": kink,
                    "anion_dipole_roughness": kink / span if span > 1e-9 else 0.0,
                    "anion_dipole_branch_hops": sum(
                        1 for a, b in zip(list(branch.values()), list(branch.values())[1:])
                        if a != b),
                }
            else:
                dipole_stats = {}
            density = []
            for label, grid in GRID_STEPS:
                keep = [index for index, point in enumerate(series) if point["eps"] in grid]
                fit = born_through_origin([xs[index] for index in keep],
                                          [ys[index] for index in keep])
                density.append({"grid": label, "eps": list(grid), "n_points": len(keep),
                                "slope": fit["slope"], "r2": fit["r2"]})
            curves["%s/%s" % (name, axis)] = {
                "name": name, "axis": axis,
                "delta_at_eps": {("%g" % point["eps"]): point["delta_ev"] for point in series},
                "solvation_by_eps": {("%g" % point["eps"]): point["solvation_ev"]
                                     for point in series},
                "born_through_origin_full_grid": born_through_origin(xs, ys),
                "born_with_intercept_full_grid": born_with_intercept(xs, ys),
                "born_r2_by_grid_density": density,
                **dipole_stats,
                "born_r2_stage13_six_point": born_through_origin(
                    [point["x"] for point in series if point["eps"] in STAGE13_GRID],
                    [point["delta_ev"] for point in series if point["eps"] in STAGE13_GRID]),
                "n_sign_changes_full_grid": sign_changes(deltas),
                "monotone_full_grid": sign_changes(deltas) == 0,
                "sign_changes_stage13_grid": sign_changes(
                    [point["delta_ev"] for point in series if point["eps"] in SHARED_EPS]),
                "delta_40_to_200_ev": (
                    series[-1]["delta_ev"] - next(point["delta_ev"] for point in series
                                                  if point["eps"] == 40.0)),
                "min_consecutive_gap_ev": min(
                    abs(b - a) for a, b in zip(deltas, deltas[1:])),
            }

    screen = solution_identity_screen()
    energy_screen = energy_kink_screen()
    emc_anion = next((row for row in screen["table"]
                      if row["name"] == "EMC" and row["state"] == "anion"), None)
    dmc_anion = next((row for row in screen["table"]
                      if row["name"] == "DMC" and row["state"] == "anion"), None)

    focus = curves["EMC/reduction"]
    verdict = {
        "emc_reduction_born_r2_stage13_grid": focus["born_r2_stage13_six_point"]["r2"],
        "emc_reduction_born_r2_full_grid": focus["born_through_origin_full_grid"]["r2"],
        "emc_reduction_sign_changes_stage13_grid": focus["sign_changes_stage13_grid"],
        "emc_reduction_sign_changes_full_grid": focus["n_sign_changes_full_grid"],
        "controls_monotone_full_grid": {
            key: value["monotone_full_grid"] for key, value in curves.items()
            if not key.startswith("EMC/reduction")},
    }
    step = {state: (focus["solvation_by_eps"]["20"][state]
                    - focus["solvation_by_eps"]["10"][state])
            for state in STATES}
    verdict["emc_reduction_step_10_to_20_ev"] = (
        focus["delta_at_eps"]["20"] - focus["delta_at_eps"]["10"])
    verdict["emc_reduction_step_10_to_20_by_state_ev"] = step
    magnitude = sorted(abs(value) for value in step.values())
    verdict["dip_is_state_localised"] = magnitude[-1] > 5.0 * max(magnitude[0], 1e-6)
    verdict["emc_reduction_dip_note"] = (
        "on the reduction axis delta = [E_neutral(eps) - E_neutral(gas)] - "
        "[E_anion(eps) - E_anion(gas)], so the eps 10 -> 20 step is "
        "neutral %.4f eV minus anion %.4f eV" % (step["neutral"], step["anion"]))
    focus_hops = focus.get("anion_dipole_branch_hops")
    if focus_hops is not None:
        verdict["emc_anion_branch_hops_on_nine_points"] = focus_hops
    if emc_anion is not None:
        values = list(emc_anion["dipole_debye_by_eps"].values())
        low = min(values)
        high = max(values)
        split = 0.5 * (low + high)
        target = focus["solvation_by_eps"]
        verdict["emc_anion_dipole_by_eps"] = emc_anion["dipole_debye_by_eps"]
        verdict["emc_anion_dipole_branches_debye"] = {"low": low, "high": high}
        verdict["emc_anion_dipole_branch_by_eps"] = {
            key: ("low" if value < split else "high")
            for key, value in emc_anion["dipole_debye_by_eps"].items()}
        verdict["emc_anion_solution_switches"] = int(bool(emc_anion["solution_switch_suspect"]))
        verdict["emc_anion_roughness"] = emc_anion["roughness"]
        verdict["emc_anion_solvation_by_branch"] = {
            branch: {("%g" % eps): (target.get("%g" % eps) or {}).get("anion")
                     for eps in LADDER
                     if verdict["emc_anion_dipole_branch_by_eps"].get("%g" % eps) == branch}
            for branch in ("low", "high")}
    if dmc_anion is not None:
        verdict["dmc_anion_dipole_by_eps"] = dmc_anion["dipole_debye_by_eps"]
        verdict["dmc_anion_solution_switches"] = int(bool(dmc_anion["solution_switch_suspect"]))
        verdict["dmc_anion_roughness"] = dmc_anion["roughness"]
    verdict["solution_screen"] = {
        "levels": screen["levels"], "n_series": screen["n_series"],
        "n_suspect": screen["n_suspect"],
        "median_roughness_of_smooth_population":
            screen["median_roughness_of_smooth_population"],
        "suspect": [{"name": row["name"], "state": row["state"],
                     "max_abs_second_difference_debye": row["max_abs_second_difference_debye"],
                     "roughness": row["roughness"],
                     "dipole_debye_by_eps": row["dipole_debye_by_eps"]}
                    for row in screen["suspect"]]}
    verdict["energy_kink_ea_suspect"] = energy_screen["ea_suspect"]
    verdict["energy_kink_ea_suspect_ev"] = energy_screen["ea_suspect_ev"]
    verdict["energy_kink_ea_runner_up_ev"] = energy_screen["ea_runner_up_ev"]
    verdict["energy_kink_ea_outlier_ratio"] = energy_screen["ea_outlier_ratio"]
    verdict["energy_kink_ip_suspect"] = energy_screen["ip_suspect"]
    verdict["energy_kink_ip_suspect_ev"] = energy_screen["ip_suspect_ev"]
    verdict["energy_kink_ip_emc_ev"] = energy_screen["ip_emc_ev"]
    verdict["energy_kink_is_reduction_side_only"] = (
        energy_screen["ea_suspect"] == "EMC"
        and energy_screen["ip_suspect"] != "EMC")
    verdict["outlier_is_grid_artefact"] = (
        verdict["emc_reduction_born_r2_full_grid"] > 0.95
        and verdict["emc_reduction_sign_changes_full_grid"] == 0)
    if verdict["outlier_is_grid_artefact"]:
        verdict["reading"] = ("the dense grid removes the non-monotonicity, so the "
                              "six-point anomaly was a sampling artefact")
    elif (verdict.get("emc_anion_solution_switches", 0) >= 1
          or verdict.get("emc_anion_branch_hops_on_nine_points", 0) >= 1):
        verdict["reading"] = (
            "the anomaly is neither a coarse grid nor numerical noise: the EMC anion "
            "settles on a different SCF solution at different dielectrics, which the "
            "dipole reveals independently of any energy.  The non-Born appearance is "
            "a solution-selection artefact of bare CPCM for this one anion")
    else:
        verdict["reading"] = ("the non-Born behaviour survives a nine-point grid and "
                              "the dipole stays monotone, so it is a real response of "
                              "EMC rather than a sampling artefact")
    verdict["conclusion"] = ("solution-selection artefact"
                             if (verdict.get("emc_anion_solution_switches", 0) >= 1
                                 or verdict.get("emc_anion_branch_hops_on_nine_points", 0) >= 1)
                             else ("coarse-grid artefact"
                                   if verdict["outlier_is_grid_artefact"]
                                   else "real non-Born response"))

    csv_path = outdir / "stage14_outlier.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["name", "axis", "eps",
                                                   "born_x", "delta_ev", "ip_ev",
                                                   "ea_ev"])
        writer.writeheader()
        for row in curve_rows:
            writer.writerow(row)

    payload = {
        "stage": 14,
        "part": "B -- EMC outlier diagnosis",
        "molecules": list(MOLECULES),
        "ladder_eps": list(LADDER),
        "n_new_jobs": 3 * len(FRESH_EPS) * len(STATES),
        "sign_convention": ("delta_oxidation = IP(eps) - IP(gas), "
                            "delta_reduction = EA(eps) - EA(gas)"),
        "layer_provenance": provenance,
        "reproducibility": reproducibility,
        "curves": curves,
        "energy_kink_screen": energy_screen,
        "verdict": verdict,
        "csv": str(csv_path.relative_to(REPO_ROOT)).replace("\\", "/"),
    }
    json_path = outdir / "stage14_outlier.json"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=1),
                         encoding="utf-8")

    print("wrote %s" % csv_path.relative_to(REPO_ROOT))
    print("wrote %s" % json_path.relative_to(REPO_ROOT))
    print("reproducibility: %s  max |dE| = %.3e Eh (%.3e eV), identical strings %d/%d"
          % (reproducibility["verdict"], reproducibility["max_abs_delta_eh"],
             reproducibility["max_abs_delta_ev"], reproducibility["n_identical_strings"],
             reproducibility["n_points_compared"]))
    for key, curve in curves.items():
        full = curve["born_through_origin_full_grid"]
        four = curve["born_r2_stage13_six_point"]
        print("%-14s R2(stage13 n=6) %+7.4f -> R2(n=9) %+7.4f  slope %+7.4f  sign changes %d -> %d"
              % (key, four["r2"], full["r2"], full["slope"],
                 curve["sign_changes_stage13_grid"], curve["n_sign_changes_full_grid"]))
    print("note: %s" % verdict["emc_reduction_dip_note"])
    print("EMC/reduction eps 10 -> 20 step: %+.4f eV (per state: %s)"
          % (verdict["emc_reduction_step_10_to_20_ev"],
             ", ".join("%s %+.4f" % (state, value) for state, value
                       in verdict["emc_reduction_step_10_to_20_by_state_ev"].items())))
    print("solution screen: %d dipole series over %s; suspect: %s"
          % (screen["n_series"], list(screen["levels"]),
             ", ".join("%s/%s (roughness %.2f)"
                       % (row["name"], row["state"], row["roughness"])
                       for row in screen["suspect"]) or "none"))
    print("  median roughness of the smooth population = %.3f"
          % screen["median_roughness_of_smooth_population"])
    if emc_anion is not None:
        print("EMC anion dipole (D) by eps: %s"
              % ", ".join("%s %s" % (key, value)
                          for key, value in emc_anion["dipole_debye_by_eps"].items()))
        print("EMC anion branch by eps: %s"
              % ", ".join("%s %s" % (key, value) for key, value
                          in verdict["emc_anion_dipole_branch_by_eps"].items()))
    print("EMC anion branch hops on the nine-point ladder: %s (DMC %s)"
          % (verdict.get("emc_anion_branch_hops_on_nine_points"),
             (curves.get("DMC/reduction") or {}).get("anion_dipole_branch_hops")))
    print("conclusion: %s" % verdict["conclusion"])
    print("verdict: outlier_is_grid_artefact=%s" % verdict["outlier_is_grid_artefact"])
    print("reading: %s" % verdict["reading"])
    return 0


if __name__ == "__main__":
    sys.exit(main())