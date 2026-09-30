"""Stage 14A -- quantitative attribution of the distortion term.

The question
------------
Stage 13 split the environment shift of every molecule into four independent
pieces and found that one of them -- the *solute distortion* ``dist_ev`` -- is
strongly channel-asymmetric: averaged over the six bare-CPCM layers it is
+0.0435 eV for oxidation but -0.3025 eV for reduction.  A term seven times
larger on one axis has to be explained, not just reported.

What the term actually is
-------------------------
``scripts/build_stage13_ladder.py`` defines, for a state X in environment t,

    D_X(t) = bare(X, t) - bare(X, gas),      bare = Total Energy - CPCM dielectric - SMD CDS

i.e. the energy penalty the solute pays because its density relaxed in the
solvent field at a *frozen* geometry (``D_X >= 0`` by the variational
principle).  The axis quantities are then differences of two such penalties:

    dist_oxidation = D_cation - D_neutral
    dist_reduction = D_neutral - D_anion

This module verifies that identity numerically, reports the three per-state
penalties on their own, and only then asks the attribution question: *is the
size of a penalty predictable, before the calculation is run, from descriptors
the repository already has on disk* (``outputs/week3/p0_core_set.csv`` plus the
gas-phase ORCA dipole of each state)?  That is the mechanism question, because
the distortion term is the solvent re-shaping the solute's density, so its
leading coupling should be to the solute's charge distribution or to its
frontier-orbital position -- and the answer decides which pre-screening
descriptor a workflow should trust.

Sign convention, frozen here and verified numerically
-----------------------------------------------------
For all 216 rows of ``outputs/week12/stage13_shift_split.csv``,

    d_total_ev = diel_ev + dist_ev + cds_ev + d4gcp_ev + residual_ev

holds with a maximum absolute residual of exactly 0.  ``dist_ev`` is therefore
stored *with* its sign as a contribution to the total environment shift: a
positive value adds to the shift, a negative value gives part of it back.

That convention matters, because ``docs/22`` section 14 quotes the pair
(-0.0465, +0.3272) eV -- the opposite sign convention -- under the label
"distortion".  Enumerating every non-empty subset of the eight non-gas levels
(2**8 - 1 = 255) under both sign conventions yields 510 candidate aggregations,
and *none* reproduces that pair to 1e-6 eV.  The nearest, an ad hoc four-layer
mixture (cpcm_10 + cpcm_20 + cpcm_80 + smd_water), is still off by 1.2 meV.
The fully specified, reproducible values are:

    6 bare-CPCM layers, 12 audited molecules, per-molecule mean of dist_ev
        oxidation  +0.0435 eV      reduction  -0.3025 eV

Both are re-derived here from scratch, and the enumeration that refuted the
published pair is recorded so the correction is auditable rather than asserted.

Outputs
-------
``outputs/week13/stage14_attribution.csv``        one row per (molecule, axis)
``outputs/week13/stage14_distortion_states.csv``  one row per (molecule, state)
``outputs/week13/stage14_attribution.json``       identities, correction record,
                                                 per-state table, correlations
"""

from __future__ import annotations

import argparse
import csv
import itertools
import json
import statistics
import sys
from pathlib import Path

import numpy as np
from scipy import stats

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

SHIFT_SPLIT = REPO_ROOT / "outputs" / "week12" / "stage13_shift_split.csv"
STATE_LEDGER = REPO_ROOT / "outputs" / "week12" / "stage13_state_ledger.csv"
CORE_SET = REPO_ROOT / "outputs" / "week3" / "p0_core_set.csv"
GAS_DIR = REPO_ROOT / "outputs" / "week4" / "orca"
SMD_DIR = REPO_ROOT / "outputs" / "week4" / "orca_smd_acetonitrile"
DEFAULT_OUTDIR = REPO_ROOT / "outputs" / "week13"

AUDITED = ("AN", "DMC", "DME", "DMSO", "DOL", "EC", "GBL", "SL", "SN", "TMP",
           "PC", "EMC")
CPCM6 = ("cpcm_5", "cpcm_10", "cpcm_20", "cpcm_40", "cpcm_80", "cpcm_200")
STATES = ("neutral", "cation", "anion")
AXES = ("oxidation", "reduction")

# Descriptor columns read straight out of the P0 ledger.  The dipole entries
# below them are parsed out of ORCA instead, because P0 stores the xtb dipole
# while the shift split is an r2SCAN-3c quantity; mixing the two methods inside
# one regression would confound the method with the descriptor.
P0_DESCRIPTORS = ("dipole_debye", "aux_alpha_bohr3", "homo_ev", "lumo_ev",
                  "hl_gap_ev", "atom_count", "p0_ox_ev", "p0_red_ev")

_DIPOLE_BLOCK = "Total Dipole Moment"
_DIPOLE_DEBYE = "Magnitude (Debye)"


def parse_dipole_debye(text: str) -> float | None:
    """Magnitude of the last ``Total Dipole Moment`` block, in Debye.

    ORCA prints one such block per SCF solution; a geometry-free single point
    has exactly one, but taking the last is the safe read for any output that
    happens to carry more.
    """

    value = None
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if _DIPOLE_BLOCK in line:
            for probe in lines[index:index + 6]:
                if _DIPOLE_DEBYE in probe:
                    value = float(probe.split(":")[-1].strip())
    return value


def read_dipole(path: Path) -> float | None:
    if not path.exists():
        return None
    return parse_dipole_debye(path.read_text(encoding="utf-8", errors="replace"))


def number(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def load_core_rows() -> dict:
    with CORE_SET.open(encoding="utf-8", newline="") as handle:
        return {row["name"]: row for row in csv.DictReader(handle)}


def load_shift_rows() -> list:
    with SHIFT_SPLIT.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        for key in ("d_total_ev", "diel_ev", "dist_ev", "cds_ev", "d4gcp_ev",
                    "residual_ev"):
            row[key] = float(row[key])
        row["epsilon"] = float(row["epsilon"])
    return rows


def load_ledger() -> dict:
    """``{(name, level, state): entry}`` with every energy column in eV."""

    with STATE_LEDGER.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    ledger = {}
    for row in rows:
        for key in ("final_single_point_ev", "total_energy_ev",
                    "cpcm_dielectric_ev", "smd_cds_ev", "dispersion_ev",
                    "gcp_ev"):
            row[key] = number(row[key])
        ledger[(row["name"], row["level"], row["state"])] = row
    return ledger


def bare_electronic_ev(entry) -> float | None:
    """Total Energy minus both solvation terms, in eV (``None`` if incomplete)."""

    total = entry.get("total_energy_ev")
    if total is None:
        return None
    return total - (entry.get("cpcm_dielectric_ev") or 0.0) - (entry.get("smd_cds_ev") or 0.0)


def state_penalties(ledger, name, level) -> dict:
    """``D_X(level) = bare(X, level) - bare(X, gas)`` for the three states."""

    out = {}
    for state in STATES:
        env = ledger.get((name, level, state))
        gas = ledger.get((name, "gas", state))
        if env is None or gas is None:
            out[state] = None
            continue
        value = bare_electronic_ev(env)
        base = bare_electronic_ev(gas)
        out[state] = None if value is None or base is None else value - base
    return out


def identity_residual(rows) -> float:
    worst = 0.0
    for row in rows:
        parts = (row["diel_ev"] + row["dist_ev"] + row["cds_ev"]
                 + row["d4gcp_ev"] + row["residual_ev"])
        worst = max(worst, abs(row["d_total_ev"] - parts))
    return worst


def level_subset_search(rows, target):
    """Every non-empty level subset, both sign conventions, against ``target``."""

    levels = sorted({row["level"] for row in rows if row["level"] != "gas"})
    candidates = []
    for size in range(1, len(levels) + 1):
        for combo in itertools.combinations(levels, size):
            chosen = set(combo)
            for sign, label in ((1.0, "dist_ev"), (-1.0, "-dist_ev")):
                means = {}
                for axis in AXES:
                    values = [row["dist_ev"] for row in rows
                              if row["level"] in chosen and row["axis"] == axis]
                    means[axis] = sign * statistics.mean(values)
                error = max(abs(means[axis] - target[axis]) for axis in AXES)
                candidates.append({
                    "layers": list(combo),
                    "sign": label,
                    "oxidation_ev": means["oxidation"],
                    "reduction_ev": means["reduction"],
                    "max_abs_error_ev": error,
                })
    candidates.sort(key=lambda item: item["max_abs_error_ev"])
    return {"n_candidates": len(candidates),
            "n_exact_matches": sum(1 for item in candidates
                                   if item["max_abs_error_ev"] < 1e-6),
            "closest": candidates[:5]}


def per_axis_means(rows, levels):
    out = {}
    for axis in AXES:
        values = [row["dist_ev"] for row in rows
                  if row["level"] in levels and row["axis"] == axis]
        out[axis] = {"mean_ev": statistics.mean(values),
                     "std_ev": statistics.stdev(values),
                     "median_ev": statistics.median(values),
                     "n_negative": sum(1 for value in values if value < 0),
                     "n": len(values)}
    return out


def spearman(xs, ys):
    rho, p = stats.spearmanr(xs, ys)
    return {"rho": float(rho), "p": float(p)}


def pearson(xs, ys):
    r, p = stats.pearsonr(xs, ys)
    return {"r": float(r), "p": float(p)}


def ols(xs, ys):
    """Ordinary least squares with intercept, plus leave-one-out R2."""

    matrix = np.asarray(xs, dtype=float)
    if matrix.ndim == 1:
        matrix = matrix[:, None]
    target = np.asarray(ys, dtype=float)
    design = np.column_stack([np.ones(len(target)), matrix])
    coef, *_ = np.linalg.lstsq(design, target, rcond=None)
    sse = float(np.sum((target - design @ coef) ** 2))
    sst = float(np.sum((target - target.mean()) ** 2))
    loo_sse = 0.0
    for index in range(len(target)):
        keep = np.ones(len(target), dtype=bool)
        keep[index] = False
        local_design = np.column_stack([np.ones(int(keep.sum())), matrix[keep]])
        local_coef, *_ = np.linalg.lstsq(local_design, target[keep], rcond=None)
        prediction = float(np.concatenate([[1.0], matrix[index]]) @ local_coef)
        loo_sse += (target[index] - prediction) ** 2
    return {"intercept": float(coef[0]),
            "coefficients": [float(value) for value in coef[1:]],
            "r2": 1.0 - sse / sst,
            "loo_r2": 1.0 - loo_sse / sst,
            "n": int(len(target)),
            "k": int(matrix.shape[1])}


DESCRIPTORS = ("mu_neutral_debye", "mu_cation_debye", "mu_anion_debye",
               "mu_anion_smd_acn_debye", "dmu_oxidation_debye",
               "dmu_reduction_debye") + P0_DESCRIPTORS


def descriptor_map(core_row, dips, smd_dipole):
    record = {"mu_neutral_debye": dips["neutral"],
              "mu_cation_debye": dips["cation"],
              "mu_anion_debye": dips["anion"],
              "mu_anion_smd_acn_debye": smd_dipole}
    for key in P0_DESCRIPTORS:
        record[key] = number(core_row.get(key))
    record["dmu_oxidation_debye"] = (
        dips["cation"] - dips["neutral"]
        if dips["cation"] is not None and dips["neutral"] is not None else None)
    record["dmu_reduction_debye"] = (
        dips["anion"] - dips["neutral"]
        if dips["anion"] is not None and dips["neutral"] is not None else None)
    return record


ATTRIBUTION_COLUMNS = ["mol_id", "name", "family", "axis",
                       "dist_cpcm6_ev", "dist_cpcm6_std_ev", "dist_smd_acn_ev",
                       "dist_min_ev", "dist_max_ev", "d_cation_cpcm6_ev",
                       "d_neutral_cpcm6_ev", "d_anion_cpcm6_ev"] + list(DESCRIPTORS)

STATE_COLUMNS = ["mol_id", "name", "family", "state", "level",
                 "d_state_ev", "bare_gas_ev", "bare_env_ev"] + list(DESCRIPTORS)

STATE_MOL_COLUMNS = ["mol_id", "name", "family", "state", "d_state_cpcm6_ev",
                     "d_state_cpcm6_std_ev", "d_state_min_ev", "d_state_max_ev"] + list(DESCRIPTORS)


def build_tables(shift_rows, ledger, core, gas_dipoles, smd_dipoles):
    by_key = {}
    for row in shift_rows:
        by_key.setdefault((row["name"], row["axis"]), {})[row["level"]] = row

    axis_rows, state_rows, state_mol_rows = [], [], []
    for name in AUDITED:
        core_row = core[name]
        descriptors = descriptor_map(core_row, gas_dipoles[name], smd_dipoles[name])
        penalties = {level: state_penalties(ledger, name, level) for level in CPCM6}
        for state in STATES:
            for level in CPCM6:
                entry = ledger[(name, level, state)]
                state_rows.append({
                    "mol_id": core_row["mol_id"], "name": name,
                    "family": core_row["family"], "state": state, "level": level,
                    "d_state_ev": penalties[level][state],
                    "bare_gas_ev": bare_electronic_ev(ledger[(name, "gas", state)]),
                    "bare_env_ev": bare_electronic_ev(entry),
                    **descriptors})
            # Collapse to one number per molecule.  The six dielectric layers
            # are not six independent measurements of the same quantity, so a
            # regression on the 72 raw rows would be pseudoreplicated and its
            # p-values would be overstated by roughly a factor of sqrt(6).
            per_molecule = [penalties[level][state] for level in CPCM6]
            state_mol_rows.append({
                "mol_id": core_row["mol_id"], "name": name,
                "family": core_row["family"], "state": state,
                "d_state_cpcm6_ev": statistics.mean(per_molecule),
                "d_state_cpcm6_std_ev": statistics.stdev(per_molecule),
                "d_state_min_ev": min(per_molecule),
                "d_state_max_ev": max(per_molecule),
                **descriptors})
        for axis in AXES:
            levels = by_key[(name, axis)]
            cpcm_values = [levels[level]["dist_ev"] for level in CPCM6]
            axis_rows.append({
                "mol_id": core_row["mol_id"], "name": name,
                "family": core_row["family"], "axis": axis,
                "dist_cpcm6_ev": statistics.mean(cpcm_values),
                "dist_cpcm6_std_ev": statistics.stdev(cpcm_values),
                "dist_smd_acn_ev": levels["smd_acetonitrile"]["dist_ev"],
                "dist_min_ev": min(cpcm_values), "dist_max_ev": max(cpcm_values),
                "d_cation_cpcm6_ev": statistics.mean([penalties[lv]["cation"] for lv in CPCM6]),
                "d_neutral_cpcm6_ev": statistics.mean([penalties[lv]["neutral"] for lv in CPCM6]),
                "d_anion_cpcm6_ev": statistics.mean([penalties[lv]["anion"] for lv in CPCM6]),
                **descriptors})
    return axis_rows, state_rows, state_mol_rows


def correlate(records, y_key, group_key, groups):
    """Univariate screen of every descriptor inside each group of ``records``."""

    table = []
    for group in groups:
        subset = [record for record in records if record[group_key] == group]
        ys = [record[y_key] for record in subset]
        for descriptor in DESCRIPTORS:
            xs = [record[descriptor] for record in subset]
            if any(value is None for value in xs):
                continue
            table.append({"group": group, "descriptor": descriptor,
                          "spearman": spearman(xs, ys),
                          "pearson": pearson(xs, ys),
                          "ols": ols(xs, ys)})
    ranked = sorted(table, key=lambda item: -abs(item["spearman"]["rho"]))
    return {"y": y_key, "group_key": group_key, "n_per_group": len(records) // len(groups),
            "table": table, "ranked": ranked[:10]}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    parser.add_argument("--published-oxidation-ev", type=float, default=-0.0465)
    parser.add_argument("--published-reduction-ev", type=float, default=0.3272)
    args = parser.parse_args(argv)
    outdir = args.outdir if args.outdir.is_absolute() else (REPO_ROOT / args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    shift_rows = load_shift_rows()
    ledger = load_ledger()
    core = load_core_rows()
    missing = [name for name in AUDITED if name not in core]
    if missing:
        raise SystemExit("P0 ledger lacks audited molecule(s): %s" % ", ".join(missing))

    gas_dipoles, smd_dipoles = {}, {}
    for name in AUDITED:
        gas_dipoles[name] = {
            state: read_dipole(GAS_DIR / name / ("%s_%s.out" % (name, state)))
            for state in STATES}
        smd_dipoles[name] = read_dipole(
            SMD_DIR / name / ("%s_anion_smd_acetonitrile.out" % name))
    absent = {name: dips for name, dips in gas_dipoles.items()
              if any(value is None for value in dips.values())}
    if absent:
        raise SystemExit("gas-phase dipole missing for: %s" % ", ".join(sorted(absent)))

    axis_rows, state_rows, state_mol_rows = build_tables(
        shift_rows, ledger, core, gas_dipoles, smd_dipoles)

    # --- identity checks -------------------------------------------------
    identity = identity_residual(shift_rows)
    penalty_identity = 0.0
    penalty_min = {"neutral": None, "cation": None, "anion": None}
    for name in AUDITED:
        for level in CPCM6:
            penalty = state_penalties(ledger, name, level)
            for state in STATES:
                value = penalty[state]
                if penalty_min[state] is None or value < penalty_min[state]:
                    penalty_min[state] = value
            for axis in AXES:
                stored = next(row["dist_ev"] for row in shift_rows
                              if row["name"] == name and row["level"] == level
                              and row["axis"] == axis)
                rebuilt = (penalty["cation"] - penalty["neutral"] if axis == "oxidation"
                           else penalty["neutral"] - penalty["anion"])
                penalty_identity = max(penalty_identity, abs(stored - rebuilt))

    # --- the published pair, put on trial ---------------------------------
    target = {"oxidation": args.published_oxidation_ev,
              "reduction": args.published_reduction_ev}
    search = level_subset_search(shift_rows, target)
    cpcm6 = per_axis_means(shift_rows, CPCM6)
    smd_acn = per_axis_means(shift_rows, {"smd_acetonitrile"})

    correction = {
        "published_pair_ev": target,
        "published_source": "docs/22_week12_report.md section 14",
        "identity_max_abs_residual_ev": identity,
        "identity_holds": identity < 1e-12,
        "penalty_identity_max_abs_residual_ev": penalty_identity,
        "penalty_identity_holds": penalty_identity < 1e-9,
        "sign_convention": (
            "d_total_ev = diel_ev + dist_ev + cds_ev + d4gcp_ev + residual_ev "
            "(verified to 0); dist_ev is stored signed as a contribution to the "
            "environment shift, so a positive dist_ev adds to the shift"),
        "reproducible_values": {
            "aggregation": "per-molecule mean of dist_ev over the six bare-CPCM "
                           "layers (5/10/20/40/80/200), 12 audited molecules",
            "oxidation_ev": cpcm6["oxidation"]["mean_ev"],
            "reduction_ev": cpcm6["reduction"]["mean_ev"],
            "oxidation_std_ev": cpcm6["oxidation"]["std_ev"],
            "reduction_std_ev": cpcm6["reduction"]["std_ev"],
            "smd_acetonitrile_oxidation_ev": smd_acn["oxidation"]["mean_ev"],
            "smd_acetonitrile_reduction_ev": smd_acn["reduction"]["mean_ev"],
        },
        "subset_enumeration": search,
        "verdict": "not reproducible" if search["n_exact_matches"] == 0 else "reproducible",
    }

    # --- per-state attribution -------------------------------------------
    states_summary = {}
    for state in STATES:
        subset = [row for row in state_rows if row["state"] == state]
        values = [row["d_state_ev"] for row in subset]
        states_summary[state] = {
            "mean_ev": statistics.mean(values),
            "std_ev": statistics.stdev(values),
            "median_ev": statistics.median(values),
            "min_ev": min(values), "max_ev": max(values),
            "n_positive": sum(1 for value in values if value > 0),
            "n": len(values),
            "min_over_molecules_ev": penalty_min[state],
        }
    states_summary["variational_check"] = {
        "all_penalties_non_negative": all(
            value >= -1e-9 for value in penalty_min.values()),
        "worst_minimum_ev": min(value for value in penalty_min.values()),
        "note": "D_X >= 0 is required: the solvent-adapted density is not the "
                "minimiser of the bare electronic energy, so relaxing back "
                "cannot lower it.",
    }

    channels = {}
    for axis in AXES:
        values = [row["dist_cpcm6_ev"] for row in axis_rows if row["axis"] == axis]
        channels[axis] = {"mean_ev": statistics.mean(values),
                          "std_ev": statistics.stdev(values),
                          "median_ev": statistics.median(values),
                          "min_ev": min(values), "max_ev": max(values),
                          "n_negative": sum(1 for value in values if value < 0)}
    top_oxidation = sorted((row for row in axis_rows if row["axis"] == "oxidation"),
                           key=lambda row: -row["dist_cpcm6_ev"])[:3]

    correlations = {
        "axis_distortion": correlate(axis_rows, "dist_cpcm6_ev", "axis", AXES),
        "state_penalty": correlate(state_mol_rows, "d_state_cpcm6_ev", "state",
                                   STATES),
    }
    correlations["state_penalty"]["n_independent_points_per_group"] = len(AUDITED)
    correlations["state_penalty"]["pseudoreplication_note"] = (
        "each molecule is one point; the six bare-CPCM layers are averaged "
        "first, because they are not six independent measurements")

    axis_path = outdir / "stage14_attribution.csv"
    with axis_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=ATTRIBUTION_COLUMNS)
        writer.writeheader()
        for row in axis_rows:
            writer.writerow({key: row.get(key) for key in ATTRIBUTION_COLUMNS})

    state_path = outdir / "stage14_distortion_states.csv"
    with state_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=STATE_COLUMNS)
        writer.writeheader()
        for row in state_rows:
            writer.writerow({key: row.get(key) for key in STATE_COLUMNS})

    state_mol_path = outdir / "stage14_distortion_states_by_molecule.csv"
    with state_mol_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=STATE_MOL_COLUMNS)
        writer.writeheader()
        for row in state_mol_rows:
            writer.writerow({key: row.get(key) for key in STATE_MOL_COLUMNS})

    payload = {
        "stage": 14,
        "part": "A -- distortion-term attribution",
        "n_molecules": len(AUDITED),
        "molecules": list(AUDITED),
        "cpcm_layers": list(CPCM6),
        "definition": ("D_X(t) = bare(X,t) - bare(X,gas), "
                       "bare = Total Energy - CPCM dielectric - SMD CDS; "
                       "dist_oxidation = D_cation - D_neutral, "
                       "dist_reduction = D_neutral - D_anion"),
        "correction": correction,
        "state_penalties": states_summary,
        "channel_asymmetry": channels,
        "asymmetry_ratio_reduction_over_oxidation": (
            abs(channels["reduction"]["mean_ev"]) / abs(channels["oxidation"]["mean_ev"])),
        "oxidation_top3_molecules": [
            {"name": row["name"], "family": row["family"],
             "dist_cpcm6_ev": row["dist_cpcm6_ev"],
             "d_cation_cpcm6_ev": row["d_cation_cpcm6_ev"],
             "d_neutral_cpcm6_ev": row["d_neutral_cpcm6_ev"]}
            for row in top_oxidation],
        "correlations": correlations,
        "axis_distortion_by_molecule": [
            {"name": row["name"], "family": row["family"], "axis": row["axis"],
             "dist_cpcm6_ev": row["dist_cpcm6_ev"],
             "dist_cpcm6_std_ev": row["dist_cpcm6_std_ev"]}
            for row in sorted(axis_rows, key=lambda item: (item["name"], item["axis"]))],
        "state_penalties_by_molecule": [
            {"name": row["name"], "family": row["family"], "state": row["state"],
             "d_state_cpcm6_ev": row["d_state_cpcm6_ev"],
             "d_state_cpcm6_std_ev": row["d_state_cpcm6_std_ev"]}
            for row in sorted(state_mol_rows, key=lambda item: (item["name"], item["state"]))],
        "csv_axis": str(axis_path.relative_to(REPO_ROOT)).replace("\\", "/"),
        "csv_states": str(state_path.relative_to(REPO_ROOT)).replace("\\", "/"),
        "csv_states_by_molecule": str(state_mol_path.relative_to(REPO_ROOT)).replace("\\", "/"),
    }
    json_path = outdir / "stage14_attribution.json"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=1),
                         encoding="utf-8")

    print("wrote %s" % axis_path.relative_to(REPO_ROOT))
    print("wrote %s" % state_path.relative_to(REPO_ROOT))
    print("wrote %s" % state_mol_path.relative_to(REPO_ROOT))
    print("wrote %s" % json_path.relative_to(REPO_ROOT))
    print("identity residual %.3e ; penalty identity %.3e ; subset matches %d / %d"
          % (identity, penalty_identity, search["n_exact_matches"], search["n_candidates"]))
    print("cpcm6 dist mean: oxidation %+.4f  reduction %+.4f  (ratio %.2f)"
          % (cpcm6["oxidation"]["mean_ev"], cpcm6["reduction"]["mean_ev"],
             abs(cpcm6["reduction"]["mean_ev"]) / abs(cpcm6["oxidation"]["mean_ev"])))
    for state in STATES:
        block = states_summary[state]
        print("D_%-8s mean %+.4f  std %.4f  min %+.4f  max %+.4f  n_pos %d/%d"
              % (state, block["mean_ev"], block["std_ev"], block["min_ev"],
                 block["max_ev"], block["n_positive"], block["n"]))
    print("variational check: all D >= 0 ? %s (worst minimum %+.3e eV)"
          % (states_summary["variational_check"]["all_penalties_non_negative"],
             states_summary["variational_check"]["worst_minimum_ev"]))
    for label, block in correlations.items():
        top = block["ranked"][0]
        print("best |rho| for %-16s : %-22s rho=%+.3f p=%.3f (group=%s)"
              % (label, top["descriptor"], top["spearman"]["rho"],
                 top["spearman"]["p"], top["group"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())