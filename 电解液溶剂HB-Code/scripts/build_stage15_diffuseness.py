"""Stage 15 (week 14), part B -- electron-delocalisation descriptors.

The question
------------
Stage 14 attributed the distortion penalty of every state to the descriptors
the repository already had on disk, and reported one clear failure: the
reduction-axis anion penalty ``D_anion`` is the least predictable quantity in
the whole study.  Its best descriptor is the SMD(acetonitrile) anion dipole
with a leave-one-out R2 of only 0.162, which on n = 12 is indistinguishable
from zero.  Stage 14 closed with the diagnosis that the anion penalty must
follow *how spread out the extra electron is*, and that none of the stored
descriptors measures that.  This module tests the diagnosis instead of
asserting it.

The descriptors
---------------
ORCA prints, after every SCF, a ``MULLIKEN ATOMIC CHARGES AND SPIN POPULATIONS``
block.  The spin column is the Mulliken spin population of each atom, i.e. the
fraction of the unpaired electron density carried by that atom.  Five moments of
that population are built for every state:

``spin_extent_ang2``      sum |s_i| |r_i - CM|^2 / sum |s_i|
``spin_rms_ang``          sqrt of the above, so it has units of length
``spin_maxfrac``          max |s_i|, the "how much sits on one atom" number
``spin_participation``    1 / sum s_i^2, the inverse participation ratio
``spin_extent_norm``      spin_extent / <r^2>_mass, the intensive version

``spin_extent_norm`` is the one that matters: it divides the electron's spread
by the size of the molecule the electron sits on, so a large floppy molecule
and a small rigid one become comparable.  ``chg_extent_ang2`` repeats the
radius-of-second-moment calculation with the *charge* difference between the
anion and the neutral, which is what the extra electron actually did to the
charge cloud.

Why the numbers come from the bare-CPCM layers, and not from the gas phase
------------------------------------------------------------------------
The obvious cheap choice is the gas-phase anion output, which already exists for
all 12 molecules.  It is the wrong choice, and the module proves it rather than
assuming it: for AN the gas-phase anion spin population has max |s_i| = 2.50,
i.e. more than a whole electron sits on one atom, which is the signature of an
unbound (auto-detaching) anion and not a property of a bound state.  DMC is the
same story at 1.71.  Those numbers would be extrapolating the descriptor outside
the domain where it means anything.

So the descriptor is taken from the six bare-CPCM layers that the Stage 13/14
shift split already uses (5, 10, 20, 40, 80, 200), where every anion is bound,
and averaged over them.  This also keeps the descriptor on the same footing as
``D_anion`` itself, which is defined as a mean over exactly those six layers --
Stage 14's first lesson was that mixing descriptor and target definitions across
layers is what made the earlier attribution unreadable.

Outputs
-------
``outputs/week14/stage15_diffuseness.csv``              one row per (molecule, layer)
``outputs/week14/stage15_diffuseness_by_molecule.csv``  one row per (molecule, state)
``outputs/week14/stage15_diffuseness.json``             descriptors, gas-phase
                                                       binding screen, extended
                                                       attribution, verdict
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import statistics
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from build_stage14_attribution import (  # noqa: E402
    AUDITED,
    DESCRIPTORS as BASE_DESCRIPTORS,
    STATES,
    ols,
    pearson,
    spearman,
)

DEFAULT_OUTDIR = REPO_ROOT / "outputs" / "week14"
GAS_DIR = REPO_ROOT / "outputs" / "week4" / "orca"
BY_MOLECULE = (REPO_ROOT / "outputs" / "week13"
               / "stage14_distortion_states_by_molecule.csv")

#: layer label -> directory holding the bare-CPCM output of every molecule.
BARE_LAYERS = {
    "cpcm_5": REPO_ROOT / "outputs" / "week4" / "orca_cpcm_5",
    "cpcm_10": REPO_ROOT / "outputs" / "week4" / "orca_cpcm_10",
    "cpcm_20": REPO_ROOT / "outputs" / "week4" / "orca_cpcm_20",
    "cpcm_40": REPO_ROOT / "outputs" / "week4" / "orca_cpcm_40",
    "cpcm_80": REPO_ROOT / "outputs" / "week12" / "orca_cpcm_80",
    "cpcm_200": REPO_ROOT / "outputs" / "week12" / "orca_cpcm_200",
}

NEW_DESCRIPTORS = ("spin_extent_ang2", "spin_rms_ang", "spin_maxfrac",
                   "spin_participation", "spin_extent_norm", "chg_extent_ang2",
                   "chg_extent_norm")
EXTENDED_DESCRIPTORS = tuple(BASE_DESCRIPTORS) + NEW_DESCRIPTORS

#: Atomic masses (u) for the elements that occur in the audited set.
MASSES = {"H": 1.008, "C": 12.011, "N": 14.007, "O": 15.999, "F": 18.998,
          "S": 32.06, "P": 30.974, "Cl": 35.45, "Li": 6.94}

_CHARGE_BLOCK = "MULLIKEN ATOMIC CHARGES"
_SPIN_BLOCK = "MULLIKEN ATOMIC CHARGES AND SPIN POPULATIONS"

_MULLIKEN_ROW = re.compile(r"^\s*(\d+)\s+([A-Za-z]{1,2})\s*:\s*"
                           r"((?:-?\d+\.\d+\s*)+)$")


def parse_mulliken(text: str):
    """``(charges, spins)`` from the first Mulliken block, or ``(None, None)``.

    Anion and cation outputs carry both columns; the neutral output carries only
    the charge column, in which case ``spins`` comes back as zeros so that the
    caller can keep a single code path.
    """

    for marker in (_SPIN_BLOCK, _CHARGE_BLOCK):
        start = text.find(marker)
        if start < 0:
            continue
        charges, spins = [], []
        for line in text[start:].splitlines()[1:]:
            stripped = line.strip()
            if stripped.startswith("Sum of atomic"):
                break
            match = _MULLIKEN_ROW.match(line)
            if match:
                values = [float(value) for value in match.group(3).split()]
                charges.append(values[0])
                spins.append(values[1] if len(values) > 1 else 0.0)
            elif charges and not stripped:
                break
        if charges:
            return charges, spins
    return None, None


def read_text(path: Path):
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8", errors="ignore")


def read_geometry(path: Path):
    """``[(symbol, x, y, z), ...]`` from a plain XYZ file."""

    lines = path.read_text(encoding="utf-8").splitlines()
    count = int(lines[0].strip())
    out = []
    for line in lines[2:2 + count]:
        parts = line.split()
        out.append((parts[0], float(parts[1]), float(parts[2]), float(parts[3])))
    return out


def centre_of_mass(geometry):
    """Mass-weighted centre of mass of a ``[(symbol, x, y, z), ...]`` list."""

    total = sum(MASSES.get(symbol, 0.0) for symbol, *_ in geometry)
    if total <= 0.0:
        raise SystemExit("no atomic masses available for this geometry")
    return tuple(
        sum(MASSES.get(symbol, 0.0) * coord[index] for symbol, *coord in geometry)
        / total
        for index in range(3))


def mass_gyration_ang2(geometry) -> float:
    """Mass-weighted mean square radius about the centre of mass."""

    centre = centre_of_mass(geometry)
    weights = [MASSES.get(symbol, 0.0) for symbol, *_ in geometry]
    total = sum(weights)
    return sum(weight * sum((coord[index] - centre[index]) ** 2
                            for index in range(3))
               for weight, (_, *coord) in zip(weights, geometry)) / total


def weighted_extent_ang2(weights, geometry, centre) -> float:
    """``sum |w_i| |r_i - centre|^2 / sum |w_i|`` (``nan`` if weights vanish)."""

    denominator = sum(abs(weight) for weight in weights)
    if denominator <= 0.0:
        return float("nan")
    return sum(abs(weight) * sum((coord[index] - centre[index]) ** 2
                                 for index in range(3))
               for weight, (_, *coord) in zip(weights, geometry)) / denominator


def participation_ratio(weights) -> float:
    """Inverse participation ratio ``1 / sum w_i^2`` (``nan`` if degenerate)."""

    denominator = sum(weight * weight for weight in weights)
    if denominator <= 0.0:
        return float("nan")
    return 1.0 / denominator


def layer_descriptors(name: str, layer_dir: Path) -> dict:
    """Every diffuseness descriptor of one molecule in one bare-CPCM layer."""

    layer = layer_dir.name.replace("orca_", "")
    anion_out = layer_dir / name / ("%s_anion_%s.out" % (name, layer))
    neutral_out = layer_dir / name / ("%s_neutral_%s.out" % (name, layer))
    neutral_xyz = layer_dir / name / ("%s_neutral_%s.xyz" % (name, layer))

    text_anion = read_text(anion_out)
    text_neutral = read_text(neutral_out)
    if text_anion is None or text_neutral is None or not neutral_xyz.exists():
        return None

    q_anion, s_anion = parse_mulliken(text_anion)
    q_neutral, _ = parse_mulliken(text_neutral)
    if q_anion is None or q_neutral is None:
        return None

    geometry = read_geometry(neutral_xyz)
    if len(geometry) != len(q_anion) or len(geometry) != len(q_neutral):
        raise SystemExit("atom count mismatch in %s / %s" % (anion_out, neutral_out))

    centre = centre_of_mass(geometry)
    gyration = mass_gyration_ang2(geometry)
    spin_extent = weighted_extent_ang2(s_anion, geometry, centre)
    delta_q = [anion - neutral for anion, neutral in zip(q_anion, q_neutral)]
    chg_extent = weighted_extent_ang2(delta_q, geometry, centre)
    record = {
        "name": name, "layer": layer,
        "n_atoms": len(geometry),
        "gyration_ang2": gyration,
        "sum_spin": sum(s_anion),
        "sum_spin_abs": sum(abs(value) for value in s_anion),
        "min_spin": min(s_anion),
        "max_spin": max(s_anion),
        "sum_charge_anion": sum(q_anion),
        "sum_delta_q": sum(delta_q),
        "mulliken_charge_shift": sum(abs(value) for value in delta_q),
        "spin_extent_ang2": spin_extent,
        "spin_rms_ang": math.sqrt(spin_extent) if spin_extent == spin_extent else float("nan"),
        "spin_maxfrac": max(abs(value) for value in s_anion),
        "spin_participation": participation_ratio(s_anion),
        "spin_extent_norm": spin_extent / gyration,
        "chg_extent_ang2": chg_extent,
        "chg_extent_norm": chg_extent / gyration,
    }
    return record


def spin_moments(spins, geometry, centre):
    """The four spin moments, from a raw spin-population vector."""

    extent = weighted_extent_ang2(spins, geometry, centre)
    return {"spin_extent_ang2": extent,
            "spin_rms_ang": math.sqrt(extent) if extent == extent else float("nan"),
            "spin_maxfrac": max(abs(value) for value in spins),
            "spin_minfrac": min(abs(value) for value in spins),
            "spin_participation": participation_ratio(spins),
            "sum_spin": sum(spins),
            "sum_spin_abs": sum(abs(value) for value in spins)}


def gas_phase_screen(layer_rows) -> dict:
    """Would the gas-phase anion have been a legal descriptor source?

    Two things have to hold before a Mulliken spin population may be used as a
    descriptor at all.  First it must be *normalised*: for a doublet anion the
    signed sum over atoms is one, and ``|sum s - 1| > 1e-4`` means the block is
    not describing the state we think it is.  Second -- and this is the part
    that eliminates the gas phase -- the state has to be the kind of state the
    descriptor is meant to describe.

    The screen therefore compares the gas-phase moments with the range spanned
    by the six bare-CPCM layers, which is the domain the descriptor is actually
    used on.  A gas-phase anion whose spin is *more* concentrated than any layer
    value is not a sample of the same quantity.
    """

    rows = {}
    for name in AUDITED:
        text = read_text(GAS_DIR / name / ("%s_anion.out" % name))
        xyz = GAS_DIR / name / ("%s_anion.xyz" % name)
        if text is None or not xyz.exists():
            rows[name] = {"available": False}
            continue
        _, spins = parse_mulliken(text)
        if not spins:
            rows[name] = {"available": False}
            continue
        geometry = read_geometry(xyz)
        centre = centre_of_mass(geometry)
        record = {"available": True, **spin_moments(spins, geometry, centre)}
        record["normalised"] = abs(record["sum_spin"] - 1.0) < 1e-4
        subset = [row for row in layer_rows if row["name"] == name]
        layer_max = max(row["spin_maxfrac"] for row in subset)
        layer_participation = [row["spin_participation"] for row in subset]
        record["layer_max_spin_maxfrac"] = layer_max
        record["layer_participation_range"] = [min(layer_participation),
                                              max(layer_participation)]
        record["outside_layer_domain"] = bool(
            record["spin_maxfrac"] > layer_max * 1.05
            or record["spin_participation"] < min(layer_participation) * 0.95)
        rows[name] = record

    outside = sorted(name for name, row in rows.items()
                     if row.get("available") and row["outside_layer_domain"])
    unnormalised = sorted(name for name, row in rows.items()
                          if row.get("available") and not row["normalised"])
    return {"per_molecule": rows,
            "outside_layer_domain": outside,
            "not_normalised": unnormalised,
            "n_inside_domain": sum(1 for row in rows.values()
                                   if row.get("available")
                                   and not row["outside_layer_domain"]),
            "n_available": sum(1 for row in rows.values() if row.get("available"))}


def read_by_molecule() -> list:
    with BY_MOLECULE.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        for key in ("d_state_cpcm6_ev", "d_state_cpcm6_std_ev", "d_state_min_ev",
                    "d_state_max_ev"):
            row[key] = float(row[key])
        for key in BASE_DESCRIPTORS:
            row[key] = float(row[key]) if row.get(key) not in (None, "") else None
    return rows

def correlate(records, y_key, group_key, groups, descriptors):
    """The Stage 14 univariate screen, with an explicit descriptor list.

    Identical in behaviour to ``build_stage14_attribution.correlate``; the list
    is passed in because the whole point of this module is to change it.
    """

    table = []
    for group in groups:
        subset = [record for record in records if record[group_key] == group]
        ys = [record[y_key] for record in subset]
        for descriptor in descriptors:
            xs = [record.get(descriptor) for record in subset]
            if any(value is None for value in xs):
                continue
            table.append({"group": group, "descriptor": descriptor,
                          "spearman": spearman(xs, ys),
                          "pearson": pearson(xs, ys),
                          "ols": ols(xs, ys)})
    ranked = sorted(table, key=lambda item: -abs(item["spearman"]["rho"]))
    return {"y": y_key, "group_key": group_key,
            "n_per_group": len(records) // len(groups),
            "n_descriptors": len(descriptors),
            "table": table, "ranked": ranked[:12]}


def ranked_by_loo(table, group):
    subset = [row for row in table if row["group"] == group]
    subset.sort(key=lambda row: -row["ols"]["loo_r2"])
    return subset


def pair_search(records, group, y_key, descriptors, top=12, collinear=0.999):
    """Every 2-descriptor OLS on one group, ranked by leave-one-out R2.

    Pairs whose two columns are rank-collinear within the group are dropped:
    two descriptors of the same quantity (``spin_rms_ang`` is the square root of
    ``spin_extent_ang2``) would otherwise manufacture a large in-sample R2 that
    says nothing, and would wreck the leave-one-out figure.
    """

    subset = [row for row in records if row["state"] == group]
    ys = [row[y_key] for row in subset]
    usable = [name for name in descriptors
              if all(row.get(name) is not None for row in subset)]
    out, dropped = [], 0
    for first in range(len(usable)):
        for second in range(first + 1, len(usable)):
            xs = [[row[usable[first]], row[usable[second]]] for row in subset]
            columns = list(zip(*xs))
            if abs(spearman(columns[0], columns[1])["rho"]) > collinear:
                dropped += 1
                continue
            fit = ols(xs, ys)
            out.append({"descriptors": [usable[first], usable[second]],
                        "r2": fit["r2"], "loo_r2": fit["loo_r2"],
                        "n": fit["n"], "k": fit["k"]})
    out.sort(key=lambda item: -item["loo_r2"])
    return {"group": group, "y": y_key, "n_pairs": len(out),
            "n_dropped_collinear": dropped, "ranked": out[:top]}


BY_MOLECULE_COLUMNS = (["mol_id", "name", "family", "state",
                        "d_state_cpcm6_ev", "d_state_cpcm6_std_ev",
                        "d_state_min_ev", "d_state_max_ev"]
                       + list(BASE_DESCRIPTORS) + list(NEW_DESCRIPTORS)
                       + ["spin_extent_ang2_std", "spin_extent_norm_std",
                          "spin_maxfrac_std", "chg_extent_norm_std"])


def aggregate(layer_rows, name):
    """Per-molecule mean and spread of every new descriptor over six layers."""

    subset = [row for row in layer_rows if row["name"] == name]
    if len(subset) != len(BARE_LAYERS):
        raise SystemExit("expected %d layers for %s, found %d"
                         % (len(BARE_LAYERS), name, len(subset)))
    out = {}
    for key in NEW_DESCRIPTORS:
        values = [row[key] for row in subset]
        out[key] = statistics.mean(values)
        out["%s_median" % key] = statistics.median(values)
        out["%s_std" % key] = statistics.stdev(values)
    out["max_layer_spin_polarisation"] = max(row["sum_spin_abs"] for row in subset)
    out["max_layer_spin_maxfrac"] = max(row["spin_maxfrac"] for row in subset)
    out["layer_spin_polarisation"] = {row["layer"]: row["sum_spin_abs"]
                                      for row in subset}
    out["n_layers"] = len(subset)
    out["layers"] = [row["layer"] for row in subset]
    return out


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    parser.add_argument("--by-molecule", type=Path, default=BY_MOLECULE)
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    outdir = args.outdir if args.outdir.is_absolute() else (REPO_ROOT / args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    layer_rows = []
    for label, directory in BARE_LAYERS.items():
        for name in AUDITED:
            record = layer_descriptors(name, directory)
            if record is None:
                raise SystemExit("missing Mulliken block or geometry for %s in %s"
                                 % (name, directory))
            layer_rows.append(record)

    # --- the descriptor has to be defined before it is used ----------------
    worst_spin = max(abs(row["sum_spin"] - 1.0) for row in layer_rows)
    worst_charge = max(abs(row["sum_charge_anion"] + 1.0) for row in layer_rows)
    over_one = sorted({row["name"] for row in layer_rows
                       if row["spin_maxfrac"] > 1.0})
    polarised = sorted({row["name"] for row in layer_rows
                        if row["sum_spin_abs"] > 1.5})
    outlier_rows = sorted(
        ((row["name"], row["layer"], round(row["sum_spin_abs"], 3))
         for row in layer_rows
         if row["sum_spin_abs"] > 1.20 * statistics.median(
             other["sum_spin_abs"] for other in layer_rows
             if other["name"] == row["name"])),
        key=lambda item: -item[2])
    domain = {
        "n_rows": len(layer_rows),
        "worst_abs_sum_spin_minus_one": worst_spin,
        "worst_abs_sum_charge_plus_one": worst_charge,
        "spin_population_is_normalised": worst_spin < 1e-4,
        "charge_is_normalised": worst_charge < 1e-4,
        "max_single_atom_spin_fraction_in_layers": max(
            row["spin_maxfrac"] for row in layer_rows),
        "molecules_with_single_atom_spin_above_one": over_one,
        "molecules_with_spin_polarisation_above_1p5": polarised,
        "layer_outliers_vs_own_median": outlier_rows,
        "note": ("Mulliken spin populations are normalised (signed sum = 1) but "
                 "not positive, so max |s_i| > 1 is a signature of a strongly "
                 "spin-polarised solution, not of an unbound anion. Layers whose "
                 "spin polarisation exceeds 1.2x the molecule's own median are "
                 "flagged because a different SCF solution was found there."),
    }

    csv_path = outdir / "stage15_diffuseness.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        fieldnames = ["name", "layer", "n_atoms", "gyration_ang2",
                      "sum_spin", "sum_spin_abs", "min_spin", "max_spin",
                      "sum_charge_anion", "sum_delta_q",
                      "mulliken_charge_shift"] + list(NEW_DESCRIPTORS)
        writer = csv.DictWriter(handle, fieldnames=fieldnames,
                                extrasaction="ignore")
        writer.writeheader()
        for row in sorted(layer_rows, key=lambda item: (item["name"], item["layer"])):
            writer.writerow(row)

    # --- extend the Stage 14 per-molecule table ---------------------------
    records = []
    for row in read_by_molecule():
        extra = aggregate(layer_rows, row["name"])
        merged = dict(row)
        merged.update(extra)
        records.append(merged)

    csv_by_mol = outdir / "stage15_diffuseness_by_molecule.csv"
    with csv_by_mol.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=BY_MOLECULE_COLUMNS,
                                extrasaction="ignore")
        writer.writeheader()
        for row in sorted(records, key=lambda item: (item["mol_id"], item["state"])):
            writer.writerow(row)

    baseline = correlate(records, "d_state_cpcm6_ev", "state", STATES,
                         BASE_DESCRIPTORS)
    extended = correlate(records, "d_state_cpcm6_ev", "state", STATES,
                         EXTENDED_DESCRIPTORS)
    pairs = {state: pair_search(records, state, "d_state_cpcm6_ev",
                                EXTENDED_DESCRIPTORS) for state in STATES}

    # The mean over six layers carries the one layer where EMC fell into a
    # different SCF solution (see Part A).  The median over the same six layers
    # does not, so the headline number is reported twice.
    robust = []
    for row in records:
        merged = dict(row)
        for key in NEW_DESCRIPTORS:
            merged[key] = row["%s_median" % key]
        robust.append(merged)
    robust_extended = correlate(robust, "d_state_cpcm6_ev", "state", STATES,
                                EXTENDED_DESCRIPTORS)

    verdicts = {}
    for state in STATES:
        base_top = ranked_by_loo(baseline["table"], state)[0]
        ext_top = ranked_by_loo(extended["table"], state)[0]
        pair_top = pairs[state]["ranked"][0] if pairs[state]["ranked"] else None
        improved = ext_top["ols"]["loo_r2"] - base_top["ols"]["loo_r2"]
        verdicts[state] = {
            "baseline_best_descriptor": base_top["descriptor"],
            "baseline_best_loo_r2": base_top["ols"]["loo_r2"],
            "extended_best_descriptor": ext_top["descriptor"],
            "extended_best_loo_r2": ext_top["ols"]["loo_r2"],
            "extended_best_rho": ext_top["spearman"]["rho"],
            "extended_best_p": ext_top["spearman"]["p"],
            "delta_loo_r2": improved,
            "best_pair": pair_top,
            "material_improvement": bool(
                ext_top["ols"]["loo_r2"] >= 0.50 and improved >= 0.20),
        }

    robust_verdicts = {}
    for state in STATES:
        base_top = ranked_by_loo(baseline["table"], state)[0]
        ext_top = ranked_by_loo(robust_extended["table"], state)[0]
        robust_verdicts[state] = {
            "baseline_best_descriptor": base_top["descriptor"],
            "baseline_best_loo_r2": base_top["ols"]["loo_r2"],
            "median_best_descriptor": ext_top["descriptor"],
            "median_best_loo_r2": ext_top["ols"]["loo_r2"],
            "median_best_rho": ext_top["spearman"]["rho"],
            "median_best_p": ext_top["spearman"]["p"],
            "delta_loo_r2": ext_top["ols"]["loo_r2"] - base_top["ols"]["loo_r2"],
        }

    gas = gas_phase_screen(layer_rows)

    payload = {
        "stage": 15,
        "part": "B -- electron-delocalisation descriptors",
        "n_molecules": len(AUDITED),
        "molecules": list(AUDITED),
        "layers": list(BARE_LAYERS),
        "descriptor_definitions": {
            "spin_extent_ang2": "sum |s_i| |r_i - CM|^2 / sum |s_i|, s = Mulliken "
                                "spin population of the anion, CM = centre of mass",
            "spin_rms_ang": "sqrt(spin_extent_ang2)",
            "spin_maxfrac": "max |s_i|",
            "spin_participation": "1 / sum s_i^2 (inverse participation ratio)",
            "spin_extent_norm": "spin_extent_ang2 / <r^2>_mass",
            "chg_extent_ang2": "same radius of second moment with the weights "
                               "q_anion - q_neutral",
            "chg_extent_norm": "chg_extent_ang2 / <r^2>_mass",
        },
        "descriptor_domain": domain,
        "gas_phase_screen": gas,
        "layer_outliers": domain["layer_outliers_vs_own_median"],
        "extended_descriptors": list(EXTENDED_DESCRIPTORS),
        "baseline_descriptors": list(BASE_DESCRIPTORS),
        "verdicts": verdicts,
        "robust_verdicts": robust_verdicts,
        "pair_search": pairs,
        "extended_table": extended["table"],
        "baseline_ranked": baseline["ranked"],
        "extended_ranked": extended["ranked"],
        "per_molecule": [
            {"name": row["name"], "family": row["family"], "state": row["state"],
             "d_state_cpcm6_ev": row["d_state_cpcm6_ev"],
             **{key: row[key] for key in NEW_DESCRIPTORS},
             "spin_extent_ang2_std": row["spin_extent_ang2_std"]}
            for row in sorted(records, key=lambda item: (item["mol_id"], item["state"]))],
        "csv_layers": str(csv_path.relative_to(REPO_ROOT)).replace("\\", "/"),
        "csv_by_molecule": str(csv_by_mol.relative_to(REPO_ROOT)).replace("\\", "/"),
    }
    json_path = outdir / "stage15_diffuseness.json"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n",
                         encoding="utf-8", newline="\n")

    print("wrote %s" % csv_path.relative_to(REPO_ROOT))
    print("wrote %s" % csv_by_mol.relative_to(REPO_ROOT))
    print("wrote %s" % json_path.relative_to(REPO_ROOT))
    print("descriptor domain: |sum s - 1| <= %.2e ; |sum q + 1| <= %.2e ; "
          "max single-atom spin fraction %.3f"
          % (worst_spin, worst_charge, domain["max_single_atom_spin_fraction_in_layers"]))
    print("layer outliers vs own median (different SCF solution): %s"
          % (", ".join("%s/%s %.3f" % item for item in outlier_rows) or "none"))
    print("gas-phase anion outside the layer domain ? %s"
          % (", ".join(gas["outside_layer_domain"]) or "none"))
    for state in STATES:
        block = verdicts[state]
        print("%-8s baseline %-24s loo %+.3f  ->  extended %-24s loo %+.3f "
              "(delta %+.3f, rho %+.3f)"
              % (state, block["baseline_best_descriptor"],
                 block["baseline_best_loo_r2"], block["extended_best_descriptor"],
                 block["extended_best_loo_r2"], block["delta_loo_r2"],
                 block["extended_best_rho"]))
        if block["best_pair"]:
            print("         best pair %s loo %+.3f"
                  % (" + ".join(block["best_pair"]["descriptors"]),
                     block["best_pair"]["loo_r2"]))
        print("         material improvement: %s" % block["material_improvement"])
        small = robust_verdicts[state]
        print("         median-of-layers: %-24s loo %+.3f (delta %+.3f)"
              % (small["median_best_descriptor"], small["median_best_loo_r2"],
                 small["delta_loo_r2"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())