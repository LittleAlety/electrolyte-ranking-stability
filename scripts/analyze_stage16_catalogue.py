"""Stage 16 (week 15), part A -- reading the two-guess catalogue.

Stage 15 asked the two-guess question on three molecules.  This module reads the
answer for twelve (and, when the validation arm is present, for six more that
were never computed at the continuum level before).

For every cell -- one (molecule, charge state, dielectric) -- the two arms of the
protocol are compared:

    delta = E_moread - E_default

``delta > 0``  the restart is *worse*, i.e. the default guess already had the
               lower solution.  This is the behaviour a single-solution SCF
               should show, up to SCF convergence.
``delta < 0``  the restart reached a solution the default guess never saw.  The
               production protocol therefore reported an energy that is not the
               variational minimum of the model, and the deficit is |delta|.

The material threshold is inherited from Stage 15 unchanged: 1e-3 eV.  It is not
a tuned number.  Stage 15 measured the residual of the two arms on cells where
both converge to the same solution and found the largest residual to be
8.27e-4 eV; 1e-3 eV is the next round decade above that noise band, exactly as
Stage 15 defined it.  Everything is also reported against the full threshold
ladder so the reader can see the number is not knife-edge.

The label is defined on the six dielectrics where the whole twelve-molecule
default arm already existed (5, 10, 20, 40, 80, 200).  Defining it there keeps
the discovery and validation arms on an identical ladder, which a held-out test
requires; the four extra dielectrics (7, 14, 28, 1000) are reported separately as
the fine structure of the discovery set.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

DEFAULT_OUTDIR = REPO_ROOT / "outputs" / "week15"
CORE_SET = REPO_ROOT / "data" / "metadata" / "core_set.csv"

SUBSET = ("EC", "PC", "DMC", "EMC", "DME", "DOL", "GBL", "AN", "SN", "DMSO", "SL", "TMP")
VALIDATION = ("DEC", "EA", "FEC", "MA", "TEGDME", "VC")

#: Inherited from Stage 15 (week 14) and deliberately not re-tuned here.
MATERIAL_THRESHOLD_EV = 1e-3
THRESHOLDS = (1e-8, 1e-7, 1e-6, 1e-5, 1e-4, 1e-3, 1e-2, 1e-1)

#: The six dielectrics that define the full discovery label (see the module docstring).
FOCUS = (5.0, 10.0, 20.0, 40.0, 80.0, 200.0)

#: Named dielectric ladders.  ``core3`` is the one the held-out arm is measured
#: on, so the discovery set is also labelled on it; the other two exist so the
#: report can quantify how much a sparse ladder under-detects rather than
#: assuming a three-point ladder is equivalent to a six-point one.
LADDERS = {
    "core3": (5.0, 20.0, 200.0),
    "focus6": FOCUS,
    "ladder10": None,
}

STATES = ("neutral", "cation", "anion")


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Stage 16 part A: read the two-guess catalogue.")
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    return parser.parse_args(argv)


def load_core_set():
    with CORE_SET.open(encoding="utf-8", newline="") as handle:
        return {row["name"]: row for row in csv.DictReader(handle)}


def read_layer(path: Path):
    """``{(name, state): row}`` for one arm of one dielectric, or ``{}``."""

    if not path.exists():
        return {}
    out = {}
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            out[(row["name"], row["state"])] = row
    return out


def as_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def discover(outdir: Path, prefix: str = ""):
    """Which dielectric layers are present, and for which arm.

    ``prefix`` selects one arm of the study by its file-name prefix: ``""`` is
    the discovery catalogue and ``"holdout"`` is the six-molecule out-of-sample
    arm.  Without the split the held-out run would overwrite the discovery
    layer table with a shorter one and every count in this module would quietly
    describe the wrong set.
    """

    found = {"default": [], "moread": []}
    for path in sorted(outdir.glob("p2_core_set_*.csv")):
        stem = path.stem.replace("p2_core_set_", "")
        if prefix:
            if not stem.startswith(prefix + "_"):
                continue
            stem = stem[len(prefix) + 1:]
        elif stem.startswith("holdout_"):
            continue
        if stem.startswith("moread_"):
            found["moread"].append((float(stem.split("_")[-1]), path))
        elif stem.startswith("cpcm_"):
            found["default"].append((float(stem.split("_")[-1]), path))
    for arm in found:
        found[arm].sort()
    return found


def build_cells(outdir: Path, prefix: str = ""):
    layers = discover(outdir, prefix)
    cells = []
    for eps, default_path in layers["default"]:
        default_rows = read_layer(default_path)
        moread_rows = None
        for cand_eps, cand_path in layers["moread"]:
            if abs(cand_eps - eps) < 1e-9:
                moread_rows = read_layer(cand_path)
                break
        moread_rows = moread_rows or {}
        for (name, state), default_row in sorted(default_rows.items()):
            moread_row = moread_rows.get((name, state), {})
            e_default = as_float(default_row.get("final_energy_eh"))
            e_moread = as_float(moread_row.get("final_energy_eh"))
            delta = (None if e_default is None or e_moread is None
                     else (e_moread - e_default) * 27.211386245988)
            cells.append({
                "name": name, "state": state, "epsilon": eps,
                "e_default_eh": e_default, "e_moread_eh": e_moread,
                "delta_ev": delta,
                "default_status": default_row.get("status", ""),
                "moread_status": moread_row.get("status", ""),
                "default_qc_flags": default_row.get("qc_flags", ""),
                "moread_qc_flags": moread_row.get("qc_flags", ""),
                "default_source": default_row.get("source", ""),
                "moread_source": moread_row.get("source", ""),
                "default_nprocs": default_row.get("nprocs", ""),
                "moread_nprocs": moread_row.get("nprocs", ""),
            })
    return cells, layers

def classify(delta):
    if delta is None:
        return "no_pair"
    if abs(delta) <= MATERIAL_THRESHOLD_EV:
        return "coincident"
    return "moread_lower" if delta < 0 else "moread_higher"


def summarise_group(cells, levels, molecules, states, label):
    """Per (molecule, state) aggregation over one set of dielectrics."""

    rows = []
    for name in molecules:
        for state in states:
            subset = [cell for cell in cells
                      if cell["name"] == name and cell["state"] == state
                      and any(abs(cell["epsilon"] - eps) < 1e-9 for eps in levels)]
            if not subset:
                continue
            subset.sort(key=lambda cell: cell["epsilon"])
            paired = [cell for cell in subset if cell["delta_ev"] is not None]
            flagged = [cell for cell in paired
                       if cell["delta_ev"] < -MATERIAL_THRESHOLD_EV]
            worse = [cell for cell in paired
                     if cell["delta_ev"] > MATERIAL_THRESHOLD_EV]
            worst = min(paired, key=lambda cell: cell["delta_ev"]) if paired else None
            rows.append({
                "ladder": label, "name": name, "state": state,
                "n_probed": len(subset), "n_paired": len(paired),
                "n_coincident": sum(1 for cell in paired
                                    if classify(cell["delta_ev"]) == "coincident"),
                "n_moread_lower": len(flagged),
                "n_moread_higher": len(worse),
                "has_missed_lower_solution": bool(flagged),
                "max_drop_ev": None if worst is None else min(0.0, worst["delta_ev"]),
                "epsilon_at_max_drop": None if worst is None else worst["epsilon"],
                "eps_flagged": ",".join("%g" % cell["epsilon"] for cell in flagged),
                "delta_by_eps": ";".join(
                    "%g:%s" % (cell["epsilon"],
                               "na" if cell["delta_ev"] is None else "%.3e" % cell["delta_ev"])
                    for cell in subset),
            })
    return rows


def family_coverage(rows, core):
    flagged = {row["name"] for row in rows if row["has_missed_lower_solution"]}
    families = {}
    for row in rows:
        family = core.get(row["name"], {}).get("family", "unknown")
        families.setdefault(family, {"n_molecules": 0, "n_flagged": 0, "molecules": []})
    for name in {row["name"] for row in rows}:
        family = core.get(name, {}).get("family", "unknown")
        families[family]["n_molecules"] += 1
        families[family]["molecules"].append(name)
        if name in flagged:
            families[family]["n_flagged"] += 1
    return families


def monotonicity(cells, molecules, states):
    """Is a flagged molecule flagged at *contiguous* dielectrics, or in patches?

    A single solution branch that the default guess sometimes finds and sometimes
    misses would produce an erratic pattern; a genuine second branch produces a
    contiguous band.  Both are recorded, and the raw pattern is kept so that the
    report does not have to re-derive it.
    """

    patterns = []
    for name in molecules:
        for state in states:
            subset = sorted([cell for cell in cells
                             if cell["name"] == name and cell["state"] == state
                             and cell["delta_ev"] is not None],
                            key=lambda cell: cell["epsilon"])
            if not subset:
                continue
            bits = ["1" if cell["delta_ev"] < -MATERIAL_THRESHOLD_EV else "0"
                    for cell in subset]
            if "1" not in bits:
                continue
            first = bits.index("1")
            last = len(bits) - 1 - bits[::-1].index("1")
            patterns.append({
                "name": name, "state": state,
                "eps": [cell["epsilon"] for cell in subset],
                "pattern": "".join(bits),
                "n_flagged": bits.count("1"),
                "contiguous": "0" not in bits[first:last + 1],
                "first_flagged_eps": subset[first]["epsilon"],
                "last_flagged_eps": subset[last]["epsilon"],
                "interior_gaps": bits[first:last + 1].count("0"),
            })
    return patterns


def resolve_ladders(cells):
    """Every named ladder, restricted to the dielectrics actually measured."""

    present = sorted({cell["epsilon"] for cell in cells})
    resolved = {}
    for label, levels in LADDERS.items():
        wanted = present if levels is None else levels
        resolved[label] = [eps for eps in wanted
                           if any(abs(cell["epsilon"] - eps) < 1e-9 for cell in cells)]
    return resolved, present


def label_table(rows, ladder):
    return {(row["name"], row["state"]): bool(row["has_missed_lower_solution"])
            for row in rows if row["ladder"] == ladder}


def main(argv=None) -> int:
    args = parse_args(argv)
    outdir = args.outdir if args.outdir.is_absolute() else (Path.cwd() / args.outdir)
    outdir = outdir.resolve()

    core = load_core_set()
    cells, layers = build_cells(outdir)
    holdout_cells, holdout_layers = build_cells(outdir, prefix="holdout")
    if not cells:
        raise SystemExit("no catalogue layers found in %s" % outdir)
    cells = sorted(cells, key=lambda c: (c["name"], c["state"], c["epsilon"]))
    holdout_cells = sorted(holdout_cells, key=lambda c: (c["name"], c["state"], c["epsilon"]))

    present = sorted({cell["name"] for cell in cells})
    molecules = [name for name in SUBSET if name in present]
    extra = sorted({cell["name"] for cell in holdout_cells})
    states = [state for state in STATES
              if any(cell["state"] == state for cell in cells)]

    paired = [cell for cell in cells if cell["delta_ev"] is not None]
    lower = [cell for cell in paired if cell["delta_ev"] < -MATERIAL_THRESHOLD_EV]
    higher = [cell for cell in paired if cell["delta_ev"] > MATERIAL_THRESHOLD_EV]
    coincident = [cell for cell in paired
                  if abs(cell["delta_ev"]) <= MATERIAL_THRESHOLD_EV]
    unpaired = [cell for cell in cells if cell["delta_ev"] is None]

    histogram = {("%g" % thr): sum(1 for cell in paired if abs(cell["delta_ev"]) > thr)
                 for thr in THRESHOLDS}

    ladders, all_levels = resolve_ladders(cells)

    by_state = []
    for label in ("core3", "focus6", "ladder10"):
        by_state += summarise_group(cells, ladders[label], molecules, states, label)
    holdout_levels = sorted({cell["epsilon"] for cell in holdout_cells})
    validation_rows = summarise_group(holdout_cells, holdout_levels, extra, states,
                                      "validation")
    by_state += validation_rows

    labels = {label: label_table(by_state, label)
              for label in ("core3", "focus6", "ladder10", "validation")}
    agreement = {}
    for left, right in (("core3", "focus6"), ("core3", "ladder10"),
                        ("focus6", "ladder10")):
        shared = sorted(set(labels[left]) & set(labels[right]))
        disagree = ["%s/%s" % key for key in shared
                    if labels[left][key] != labels[right][key]]
        agreement["%s_vs_%s" % (left, right)] = {
            "n_rows": len(shared), "n_disagree": len(disagree),
            "disagreements": disagree,
        }

    def flagged_names(label):
        return sorted({name for (name, _), flag in labels[label].items() if flag})

    per_state_counts = {state: {"n_cells": 0, "n_moread_lower": 0, "n_moread_higher": 0}
                        for state in states}
    for cell in cells:
        per_state_counts[cell["state"]]["n_cells"] += 1
    for cell in lower:
        per_state_counts[cell["state"]]["n_moread_lower"] += 1
    for cell in higher:
        per_state_counts[cell["state"]]["n_moread_higher"] += 1

    worst_negative = min(paired, key=lambda cell: cell["delta_ev"]) if paired else None
    worst_positive = max(paired, key=lambda cell: cell["delta_ev"]) if paired else None

    analysis = {
        "stage": 16,
        "part": "A -- the two-guess catalogue",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "material_threshold_ev": MATERIAL_THRESHOLD_EV,
        "threshold_provenance": (
            "inherited unchanged from Stage 15: the largest residual of the two "
            "arms on cells that share a solution was 8.27e-4 eV, so 1e-3 eV is "
            "the next round decade above the SCF noise band"),
        "magnitude_histogram_thresholds_ev": list(THRESHOLDS),
        "magnitude_histogram": histogram,
        "molecules": molecules,
        "extra_molecules": extra,
        "states": states,
        "ladder_all_eps": all_levels,
        "ladders": ladders,
        "n_cells": len(cells),
        "n_paired": len(paired),
        "n_unpaired": len(unpaired),
        "n_coincident": len(coincident),
        "n_material_differences": len(lower) + len(higher),
        "n_moread_lower": len(lower),
        "n_moread_higher": len(higher),
        "worst_negative_ev": None if worst_negative is None else worst_negative["delta_ev"],
        "worst_negative_at": None if worst_negative is None else
        [worst_negative["name"], worst_negative["state"], worst_negative["epsilon"]],
        "worst_positive_ev": None if worst_positive is None else worst_positive["delta_ev"],
        "worst_positive_at": None if worst_positive is None else
        [worst_positive["name"], worst_positive["state"], worst_positive["epsilon"]],
        "per_state_counts": per_state_counts,
        "label_agreement": agreement,
        "flagged_molecules": {label: flagged_names(label)
                              for label in ("core3", "focus6", "ladder10")},
        "n_flagged_molecules": {label: len(flagged_names(label))
                                for label in ("core3", "focus6", "ladder10")},
        "n_discovery_molecules": len(molecules),
        "family_coverage": {label: family_coverage([row for row in by_state
                                                    if row["ladder"] == label], core)
                            for label in ("core3", "focus6", "ladder10")},
        "monotonicity": monotonicity(cells, molecules, states),
        "unpaired_cells": ["%s/%s/%g" % (cell["name"], cell["state"], cell["epsilon"])
                           for cell in unpaired],
        "layers": {"default": [str(path.relative_to(REPO_ROOT)).replace("\\", "/")
                               for _, path in layers["default"]],
                   "moread": [str(path.relative_to(REPO_ROOT)).replace("\\", "/")
                              for _, path in layers["moread"]]},
        "holdout_layers": {"default": [str(path.relative_to(REPO_ROOT)).replace("\\", "/")
                                       for _, path in holdout_layers["default"]],
                           "moread": [str(path.relative_to(REPO_ROOT)).replace("\\", "/")
                                      for _, path in holdout_layers["moread"]]},
        "csv_cells": "outputs/week15/stage16_cells.csv",
        "csv_validation_cells": "outputs/week15/stage16_validation_cells.csv",
        "csv_by_state": "outputs/week15/stage16_by_state.csv",
    }
    if validation_rows:
        analysis["validation"] = {
            "molecules": extra,
            "ladder_eps": holdout_levels,
            "by_state": validation_rows,
            "n_molecules_with_missed_lower_solution": len(flagged_names("validation")),
            "molecules_with_missed_lower_solution": flagged_names("validation"),
        }

    fieldnames = ["name", "state", "epsilon", "e_default_eh", "e_moread_eh",
                  "delta_ev", "classification", "default_status", "moread_status",
                  "default_qc_flags", "moread_qc_flags", "default_source",
                  "moread_source", "default_nprocs", "moread_nprocs"]
    for filename, group in (("stage16_cells.csv", cells),
                            ("stage16_validation_cells.csv", holdout_cells)):
        if not group:
            continue
        with (outdir / filename).open("w", encoding="utf-8", newline="\n") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for cell in group:
                writer.writerow({**cell, "classification": classify(cell["delta_ev"])})

    state_fields = ["ladder", "name", "state", "n_probed", "n_paired", "n_coincident",
                    "n_moread_lower", "n_moread_higher", "has_missed_lower_solution",
                    "max_drop_ev", "epsilon_at_max_drop", "eps_flagged", "delta_by_eps"]
    with (outdir / "stage16_by_state.csv").open("w", encoding="utf-8", newline="\n") as handle:
        writer = csv.DictWriter(handle, fieldnames=state_fields, extrasaction="ignore")
        writer.writeheader()
        for row in by_state:
            writer.writerow(row)

    (outdir / "stage16_catalogue_analysis.json").write_text(
        json.dumps(analysis, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8", newline="\n")

    print("cells %d (paired %d, unpaired %d)"
          % (len(cells), len(paired), len(unpaired)))
    print("coincident %d | moread lower %d | moread higher %d"
          % (len(coincident), len(lower), len(higher)))
    if worst_negative is not None:
        print("worst drop %.6f eV at %s" % (worst_negative["delta_ev"],
                                            analysis["worst_negative_at"]))
    for label in ("core3", "focus6", "ladder10"):
        print("  ladder %-9s %d eps -> %d/%d molecules flagged: %s"
              % (label, len(ladders[label]), len(flagged_names(label)),
                 len(molecules), flagged_names(label)))
    for key, value in agreement.items():
        print("  label agreement %-22s %d/%d agree (disagree: %s)"
              % (key, value["n_rows"] - value["n_disagree"], value["n_rows"],
                 value["disagreements"] or "none"))
    print("magnitude histogram: %s" % histogram)
    if validation_rows:
        print("validation arm: %d/%d molecules flagged -> %s"
              % (analysis["validation"]["n_molecules_with_missed_lower_solution"],
                 len(extra), flagged_names("validation")))
    print("wrote %s" % (outdir / "stage16_catalogue_analysis.json").relative_to(REPO_ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())