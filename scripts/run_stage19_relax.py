"""Stage 19 (week 18) -- does the second SCF solution survive geometry relaxation?

Motivation
----------
Week 15/16 (Stage 16/17) catalogued, at a *frozen* geometry, every cell where ORCA's
default SCF guess and a restarted guess (``! MORead`` from the gas-phase MOs of the
same charge state) settle on different solutions.  Week 17 (Stage 18) closed the
bookkeeping on that catalogue: over the whole directory the two arms agree on the
electronic structure whenever the energies coincide, and differ whenever they do not,
with a clean gap in ``charge_l1`` at 0.039 (37 misses out of 414 cells).

Every one of those cells is a **single point on the gas-phase G1 geometry**.  Nothing
in the catalogue says whether the lower-energy solution is a genuinely distinct
electronic *state* of the molecule, or a metastable solution of the very same state
that a different initial guess happens to reach.

The discriminator is geometry.  This stage re-runs the 37 ``moread_lower`` cells with
exactly one thing changed -- ``Opt`` replaces the single point -- and relaxes both
arms independently:

* ``default`` : ORCA's own guess, relaxed in CPCM(epsilon)
* ``moread``  : ``! MORead`` + ``%moinp`` <gas-phase gbw>, relaxed in CPCM(epsilon)

If the two arms relax to the same minimum (same energy, same geometry) the "second
solution" was a solution-branch artefact that the geometry washes out.  If they relax
to two different minima, the second solution is a real, distinct state.

Everything else stays frozen: same method (r2SCAN-3c), same implicit solvent (bare
CPCM at the cell's own epsilon), same starting geometry (the week-4 G1 file, reused
verbatim), same ``%pal nprocs``.  The only two variables are the job type and the
initial guess, which is what the stage is about.

ASCII staging
-------------
``%moinp`` must point at a plain-ASCII path: ORCA's ``guess_restart`` module aborts
with ``guess_restart.cpp, line 121`` on a non-ASCII path while the rest of the program
opens the same file happily.  The repository lives under a Chinese directory name, so
every ``.gbw`` is copied into an ASCII staging root first (same fix as Stage 16/17).
"""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import statistics
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from electrolyte_ranking import orca, toolchain  # noqa: E402
from run_core_set_p1 import COLUMNS, select_states  # noqa: E402
from run_orca_job import run_job as run_orca_job  # noqa: E402

DEFAULT_OUTDIR = REPO_ROOT / "outputs" / "week18"
DEFAULT_SCRATCH = REPO_ROOT / "outputs" / "_week18_scratch"
GAS_DIR = REPO_ROOT / "outputs" / "week4" / "orca"
CORE_SET = REPO_ROOT / "data" / "metadata" / "core_set.csv"

#: The week-17 census is the definition of the target set: its ``moread_lower`` rows
#: are exactly the cells whose two single-point solutions differ *and* favour moread.
CENSUS_CSV = REPO_ROOT / "outputs" / "week17" / "stage18_identity_census.csv"

ARMS = ("default", "moread")
GUESS_LABELS = {"default": "ORCA default", "moread": "MORead(gas-phase)"}
SOURCE_LABEL = "outputs/week4/orca/<name>/<name>_<state>.xyz (G1, frozen since T1)"


def load_core_set():
    """mol_id / family / role / smiles for every core-set molecule."""

    with CORE_SET.open(encoding="utf-8", newline="") as handle:
        return {row["name"]: row for row in csv.DictReader(handle)}

def target_cells():
    """The 37 ``moread_lower`` cells of the week-17 census, in a stable order."""

    with CENSUS_CSV.open(encoding="utf-8", newline="") as handle:
        rows = [row for row in csv.DictReader(handle)
                if row["classification"] == "moread_lower"]
    if not rows:
        raise SystemExit("the census has no moread_lower rows: %s" % CENSUS_CSV)
    keys = sorted({(row["name"], row["state"]) for row in rows})
    return sorted(rows, key=lambda row: (row["name"], row["state"], float(row["epsilon"]))), keys


def cell_label(name: str, state: str, epsilon: float, arm: str) -> str:
    return "%s_%s_cpcm_%g_%s" % (name, state, epsilon, arm)


def staging_root(requested=None) -> Path:
    root = Path(tempfile.gettempdir()) if requested is None else requested
    if not str(root).isascii():
        raise SystemExit("staging root is not ASCII-safe: %s" % root)
    root = root / "electrolyte_stage19_gbw"
    root.mkdir(parents=True, exist_ok=True)
    return root


def stage_gbw(root: Path, name: str, state: str) -> Path:
    source = GAS_DIR / name / ("%s_%s.gbw" % (name, state))
    if not source.exists():
        raise SystemExit("missing gas-phase MOs: %s" % source.relative_to(REPO_ROOT))
    target = root / ("%s_%s.gbw" % (name, state))
    if not target.exists() or target.stat().st_size != source.stat().st_size:
        shutil.copyfile(source, target)
    return target


def read_xyz(path: Path):
    lines = path.read_text(encoding="utf-8").splitlines()
    count = int(lines[0].strip())
    return [tuple(float(value) for value in line.split()[1:4])
            for line in lines[2:2 + count]]


def coords_match(left, right, tolerance=1e-6):
    """Element-wise match of two coordinate lists, to ``tolerance`` in angstrom."""

    if not left or len(left) != len(right):
        return False
    return all(abs(a - b) <= tolerance
               for row_left, row_right in zip(left, right)
               for a, b in zip(row_left, row_right))


def outfile_coordinates(path: Path):
    """The last ``CARTESIAN COORDINATES (ANGSTROEM)`` block of an ORCA output."""

    text = path.read_text(encoding="utf-8", errors="replace")
    marker = "CARTESIAN COORDINATES (ANGSTROEM)"
    index = text.rfind(marker)
    if index < 0:
        return []
    block = []
    for line in text[index + len(marker):].splitlines()[1:]:
        parts = line.split()
        if len(parts) == 4:
            try:
                block.append(tuple(float(value) for value in parts[1:4]))
            except ValueError:
                break
        elif block:
            break
    return block


def audit_geometry(cells):
    """Prove that the frozen start really is the geometry the census used.

    For every target cell the week-4 G1 ``.xyz`` must reproduce, to 1e-6
    angstrom, the coordinates printed in the *existing* default single point.
    A mismatch means the census and this stage are not looking at the same object.
    """

    audit = {}
    for row in cells:
        name, state = row["name"], row["state"]
        xyz = GAS_DIR / name / ("%s_%s.xyz" % (name, state))
        reference = Path(row["default_path"])
        if not xyz.exists():
            raise SystemExit("missing G1 geometry: %s" % xyz.relative_to(REPO_ROOT))
        if not reference.exists():
            raise SystemExit("missing census default output: %s" % reference)
        same = coords_match(read_xyz(xyz), outfile_coordinates(reference))
        audit.setdefault(name + "/" + state, {
            "xyz": str(xyz.relative_to(REPO_ROOT)).replace("\\", "/"),
            "reference": str(reference.relative_to(REPO_ROOT)).replace("\\", "/"),
            "n_compared": 0, "all_identical": True,
        })
        entry = audit[name + "/" + state]
        entry["n_compared"] += 1
        entry["all_identical"] = entry["all_identical"] and same
        if not same:
            raise SystemExit("G1 geometry drift for %s/%s vs %s" % (name, state, reference))
    return audit

def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Stage 19: relax the two SCF solutions of every moread_lower cell.")
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    parser.add_argument("--scratch", type=Path, default=DEFAULT_SCRATCH)
    parser.add_argument("--only", default=None,
                        help="comma-separated name/state/epsilon keys to restrict to")
    parser.add_argument("--arms", default="default,moread")
    parser.add_argument("--nprocs", type=int, default=8)
    parser.add_argument("--jobs", type=int, default=2)
    parser.add_argument("--timeout", type=float, default=7200.0)
    parser.add_argument("--seed", type=lambda value: int(value, 0), default=0xC0FFEE)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--plan-only", action="store_true")
    return parser.parse_args(argv)


def run_one(spec, args, root, core):
    name, state, arm = spec["name"], spec["state"], spec["arm"]
    epsilon = float(spec["epsilon"])
    meta = core.get(name, {})
    common = {
        "mol_id": meta.get("mol_id", ""), "name": name,
        "family": meta.get("family", ""), "role": meta.get("role", ""),
        "smiles": meta.get("smiles", ""), "state": state,
        "charge": spec["charge"], "multiplicity": spec["multiplicity"],
        "layer": "relax_cpcm_%g" % epsilon, "epsilon": epsilon, "solvent": "",
        "geometry_source": SOURCE_LABEL, "arm": arm, "guess": GUESS_LABELS[arm],
        "census_arm_set": spec["arm_set"], "single_point_delta_ev": spec["delta_ev"],
        "single_point_charge_l1": spec["charge_l1"],
    }

    mol_dir = args.outdir / ("orca_relax_" + arm) / name
    mol_dir.mkdir(parents=True, exist_ok=True)
    job_name = cell_label(name, state, epsilon, arm)
    stored = mol_dir / (job_name + "_orca.json")

    if stored.exists() and not args.force:
        try:
            cached = json.loads(stored.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            cached = None
        if cached is not None and cached.get("status") in ("ok", "not_run"):
            result = cached.get("result") or {}
            return {**common, "status": cached.get("status"),
                    "final_energy_eh": result.get("final_energy_eh"),
                    "scf_converged": result.get("scf_converged"),
                    "n_scf_cycles": result.get("n_scf_cycles"),
                    "terminated_normally": result.get("normal_termination"),
                    "seconds": result.get("seconds", ""), "nprocs": cached.get("nprocs"),
                    "parallel_note": cached.get("parallel_note", ""),
                    "qc_flags": ";".join(cached.get("qc_flags", [])),
                    "orca_version": result.get("version"), "error": "",
                    "source": "cached", "cached": True}

    moinp = stage_gbw(root, name, state) if arm == "moread" else None
    started = time.perf_counter()
    try:
        record = run_orca_job(
            name=job_name, smiles=None,
            xyz=GAS_DIR / name / ("%s_%s.xyz" % (name, state)),
            charge=spec["charge"], multiplicity=spec["multiplicity"],
            job=orca.JOB_OPTIMIZE, outdir=mol_dir, solvent=None, epsilon=epsilon,
            seed=args.seed, timeout_seconds=args.timeout, nprocs=args.nprocs, moinp=moinp)
    except Exception as exc:  # noqa: BLE001 - a failed job is a result, not a crash
        return {**common, "status": "execution_failed",
                "seconds": round(time.perf_counter() - started, 2),
                "qc_flags": "geometry_failed", "error": repr(exc),
                "source": "computed", "cached": False}

    elapsed = round(time.perf_counter() - started, 2)
    result = record.get("result") or {}
    if result:
        result["seconds"] = elapsed
        stored.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n",
                          encoding="utf-8", newline="\n")
    return {**common, "status": record.get("status"),
            "final_energy_eh": result.get("final_energy_eh"),
            "scf_converged": result.get("scf_converged"),
            "n_scf_cycles": result.get("n_scf_cycles"),
            "terminated_normally": result.get("normal_termination"),
            "seconds": elapsed, "nprocs": record.get("nprocs"),
            "parallel_note": record.get("parallel_note", ""),
            "qc_flags": ";".join(record.get("qc_flags", [])),
            "orca_version": result.get("version"), "error": record.get("error", ""),
            "source": "computed", "cached": False}

def main(argv=None) -> int:
    args = parse_args(argv)
    for attribute in ("outdir", "scratch"):
        value = getattr(args, attribute)
        setattr(args, attribute, (value if value.is_absolute() else Path.cwd() / value).resolve())
    args.outdir.mkdir(parents=True, exist_ok=True)
    args.scratch.mkdir(parents=True, exist_ok=True)

    core = load_core_set()
    cells, keys = target_cells()
    charges = {label: (charge, multiplicity)
               for label, charge, multiplicity in select_states("neutral,cation,anion")}

    wanted_arms = [item.strip() for item in args.arms.split(",") if item.strip()]
    unknown_arms = [arm for arm in wanted_arms if arm not in ARMS]
    if unknown_arms:
        raise SystemExit("unknown arms: %s (known: %s)" % (unknown_arms, list(ARMS)))

    selected = cells
    if args.only:
        wanted = {item.strip() for item in args.only.split(",") if item.strip()}
        selected = [row for row in cells
                    if "%s/%s/%g" % (row["name"], row["state"], float(row["epsilon"])) in wanted]
        if not selected:
            raise SystemExit("--only matched no cell of the %d-cell target set" % len(cells))

    audit = audit_geometry(selected)

    specs = []
    for row in selected:
        charge, multiplicity = charges[row["state"]]
        for arm in wanted_arms:
            specs.append({"name": row["name"], "state": row["state"],
                          "epsilon": float(row["epsilon"]), "arm": arm,
                          "charge": charge, "multiplicity": multiplicity,
                          "arm_set": row["arm_set"],
                          "delta_ev": float(row["delta_ev"]),
                          "charge_l1": row["charge_l1"]})

    ledger = {
        "stage": 19,
        "part": "does the second SCF solution survive geometry relaxation?",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "set": "the 37 moread_lower cells of the week-17 census",
        "source_census": str(CENSUS_CSV.relative_to(REPO_ROOT)).replace("\\", "/"),
        "molecules": sorted({row["name"] for row in selected}),
        "states": sorted({row["state"] for row in selected}),
        "n_target_cells": len(selected),
        "n_single_points": len(selected),
        "arms": wanted_arms,
        "n_jobs": len(specs),
        "job_type": orca.JOB_OPTIMIZE,
        "method": orca.FROZEN_METHOD,
        "environment": "bare CPCM at each cell's own epsilon (as in the P2 single points)",
        "start_geometry": SOURCE_LABEL,
        "geometry_audit": audit,
        "guess_protocol": {
            "default": "ORCA's own guess, relaxed in CPCM(epsilon)",
            "moread": "! MORead + %moinp <gas-phase gbw of the same charge state>",
            "staging_root": str(staging_root()),
            "staging_reason": ("ORCA guess_restart aborts on a non-ASCII %moinp path; "
                               "the repository lives under a Chinese directory name"),
        },
        "cells": ["%s/%s/%g" % (row["name"], row["state"], float(row["epsilon"]))
                  for row in selected],
        "layers": [],
    }

    if args.plan_only:
        (args.outdir / "stage19_relax_plan.json").write_text(
            json.dumps(ledger, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8", newline="\n")
        print("plan: %d target cells x %d arms = %d Opt jobs over %d molecules x %d states"
              % (len(selected), len(wanted_arms), len(specs),
                 len(ledger["molecules"]), len(ledger["states"])))
        return 0

    root = staging_root()
    print("running %d Opt jobs (%d concurrent, %d procs each) on the %d target cells"
          % (len(specs), args.jobs, args.nprocs, len(selected)))

    records = []
    with ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool:
        futures = [pool.submit(run_one, spec, args, root, core) for spec in specs]
        for position, future in enumerate(futures, start=1):
            record = future.result()
            records.append(record)
            if record.get("source") == "computed":
                print("  [%d/%d] %-8s %-7s %-24s %-9s %s" % (
                    position, len(specs), record["name"], record["state"],
                    record["layer"] + "/" + record["arm"], record["status"],
                    "" if not isinstance(record.get("seconds"), (int, float))
                    else "%.1fs" % record["seconds"]))

    tool = toolchain.find_executable("orca")
    version = None if tool is None else toolchain.read_version(tool.path, "orca")

    table = args.outdir / "stage19_relax_cells.csv"
    fieldnames = []
    for key in list(COLUMNS) + ["layer", "solvent", "epsilon", "arm", "guess",
                                "census_arm_set", "single_point_delta_ev",
                                "single_point_charge_l1", "source"]:
        if key not in fieldnames:
            fieldnames.append(key)
    with table.open("w", encoding="utf-8", newline="\n") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for record in records:
            writer.writerow(record)

    ok = [record for record in records if record["status"] == "ok"]
    seconds = [record["seconds"] for record in ok
               if isinstance(record.get("seconds"), (int, float))]
    summary = {
        "stage": 19, "engine": "ORCA", "engine_version": version,
        "method": orca.FROZEN_METHOD, "job_type": orca.JOB_OPTIMIZE,
        "n_target_cells": len(selected), "n_jobs": len(records), "n_ok": len(ok),
        "n_failed": len(records) - len(ok),
        "n_reused": sum(1 for record in records if record.get("cached")),
        "n_computed": sum(1 for record in records if record.get("source") == "computed"),
        "nprocs": args.nprocs,
        "wall_clock_seconds_median": (round(statistics.median(seconds), 2)
                                      if seconds else None),
        "output_csv": str(table.relative_to(REPO_ROOT)).replace("\\", "/"),
        "generated_utc": datetime.now(timezone.utc).isoformat(),
    }
    (args.outdir / "stage19_relax.json").write_text(
        json.dumps({**ledger, "summary": summary, "n_ok": len(ok),
                    "n_failed": len(records) - len(ok),
                    "jobs": args.jobs, "nprocs": args.nprocs,
                    "layers": [summary]}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8", newline="\n")

    print("%d/%d jobs ok (%d cached, %d computed), median %.1fs"
          % (len(ok), len(records), summary["n_reused"], summary["n_computed"],
             summary["wall_clock_seconds_median"] or 0.0))
    print("wrote %s" % table.relative_to(REPO_ROOT))
    return 0 if summary["n_failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())