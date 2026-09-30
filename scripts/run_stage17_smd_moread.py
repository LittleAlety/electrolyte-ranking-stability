"""Stage 17 (week 16) -- the two-guess protocol applied to the ladder's own P2 rung.

Why this layer and not another
------------------------------
Week 15 (Stage 16) ran both SCF guesses of the P2 single points over the twelve
molecules of the T3 audit subset and found 32 of 360 paired cells where ORCA's
default guess settles on a solution that is not the lowest one.  Those cells are
CPCM cells -- but the CPCM ladder is a *mechanism* study (week 12/13/14), not the
ladder the project's headline verdicts are built on.

The five-rung ladder of week 9 takes its P1 -> P2 rung from
``outputs/week4/p2_environment_effects.csv``, i.e. from the **SMD(acetonitrile)**
layer.  If the default guess is metastable there too, then every tau_b, Top-k
overlap and robust-inversion fraction published for that rung is computed on an
unknown mixture of ground and excited SCF solutions -- and the size of the error
has never been measured.

This module measures it.  It runs the same 18 molecules x 3 states with the same
frozen method and the same frozen G1 geometry as week 4, changing exactly one
thing: the initial guess, which is restarted from the gas-phase MOs of the same
charge state (``! MORead`` + ``%moinp``).  Nothing is optimised; nothing else is
touched.

ASCII staging (the same ORCA gotcha as Stage 16)
------------------------------------------------
``%moinp`` must point at a plain-ASCII path: ORCA's ``guess_restart`` module
aborts with ``guess_restart.cpp, line 121`` on a non-ASCII path while the rest of
the program opens the same file happily.  The repository lives under a Chinese
directory name, so every ``.gbw`` is copied into an ASCII staging root first.
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

DEFAULT_OUTDIR = REPO_ROOT / "outputs" / "week16"
DEFAULT_SCRATCH = REPO_ROOT / "outputs" / "_week16_scratch"
GAS_DIR = REPO_ROOT / "outputs" / "week4" / "orca"
CORE_SET = REPO_ROOT / "data" / "metadata" / "core_set.csv"

#: The published P2 rung that the week-9 ladder consumes.  This is the *default*
#: arm; the moread arm produced here is compared against it.
REFERENCE_CSV = REPO_ROOT / "outputs" / "week4" / "p2_core_set_smd_acetonitrile.csv"
REFERENCE_ORCA_DIR = REPO_ROOT / "outputs" / "week4" / "orca_smd_acetonitrile"

SOLVENT = "acetonitrile"
LAYER = "moread_smd_acetonitrile"
GUESS_LABEL = "MORead(gas-phase)"
SOURCE_LABEL = "outputs/week4/orca/<name>/<name>_<state>.xyz (G1, frozen since T1)"


def load_core_set():
    """mol_id / family / role / smiles for every core-set molecule."""

    with CORE_SET.open(encoding="utf-8", newline="") as handle:
        return {row["name"]: row for row in csv.DictReader(handle)}


def read_coords(path: Path):
    lines = path.read_text(encoding="utf-8").splitlines()
    count = int(lines[0].strip())
    return [tuple(line.split()[1:]) for line in lines[2:2 + count]]


def audit_geometry(molecules, states):
    """The gas-phase .xyz must equal the SMD .xyz week 4 already used.

    ``docs/08`` freezes G1: every P2 job in the project reuses the T1 geometry
    verbatim.  Restarting an SMD job from gas-phase MOs is only a *guess* change
    if that is still true, so it is asserted rather than assumed.  Where no SMD
    geometry has ever been produced the check is reported as not applicable.
    """

    audit = {}
    for name in molecules:
        reference = REFERENCE_ORCA_DIR / name
        entry = {"name": name, "reference": None, "n_compared": 0,
                 "all_identical": None, "note": ""}
        if not reference.is_dir():
            entry["note"] = ("no SMD geometry on disk; the frozen gas-phase G1 xyz "
                             "is the only geometry source for this molecule")
            audit[name] = entry
            continue
        entry["reference"] = str(reference.relative_to(REPO_ROOT)).replace("\\", "/")
        comparisons = []
        for state, _, _ in states:
            gas = GAS_DIR / name / ("%s_%s.xyz" % (name, state))
            other = reference / ("%s_%s_smd_acetonitrile.xyz" % (name, state))
            if gas.exists() and other.exists():
                comparisons.append(read_coords(gas) == read_coords(other))
        entry["n_compared"] = len(comparisons)
        entry["all_identical"] = bool(comparisons) and all(comparisons)
        if comparisons and not entry["all_identical"]:
            raise SystemExit("G1 geometry drift for %s (vs %s)" % (name, reference))
        audit[name] = entry
    return audit


def staging_root(requested=None) -> Path:
    root = Path(tempfile.gettempdir()) if requested is None else requested
    if not str(root).isascii():
        raise SystemExit("staging root is not ASCII-safe: %s" % root)
    root = root / "electrolyte_stage17_gbw"
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


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Stage 17: the two-guess protocol on the SMD(acetonitrile) P2 rung.")
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    parser.add_argument("--scratch", type=Path, default=DEFAULT_SCRATCH)
    parser.add_argument("--molecules", default=None,
                        help="explicit comma-separated names (default: all 18 core-set molecules)")
    parser.add_argument("--states", default="neutral,cation,anion")
    parser.add_argument("--nprocs", type=int, default=8)
    parser.add_argument("--jobs", type=int, default=2)
    parser.add_argument("--timeout", type=float, default=1800.0)
    parser.add_argument("--seed", type=lambda value: int(value, 0), default=0xC0FFEE)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--plan-only", action="store_true")
    return parser.parse_args(argv)


def reference_rows():
    """The published default arm, keyed by (name, state) for the analysis step."""

    with REFERENCE_CSV.open(encoding="utf-8", newline="") as handle:
        return {(row["name"], row["state"]): row for row in csv.DictReader(handle)}


def run_one(spec, args, root, core):
    name, state, charge, multiplicity = spec
    meta = core.get(name, {})
    common = {
        "mol_id": meta.get("mol_id", ""), "name": name,
        "family": meta.get("family", ""), "role": meta.get("role", ""),
        "smiles": meta.get("smiles", ""), "state": state, "charge": charge,
        "multiplicity": multiplicity, "layer": LAYER, "epsilon": "",
        "solvent": SOLVENT,
        "geometry_source": SOURCE_LABEL,
        "guess": GUESS_LABEL,
    }

    mol_dir = args.outdir / ("orca_" + LAYER) / name
    mol_dir.mkdir(parents=True, exist_ok=True)
    job_name = "%s_%s_%s" % (name, state, LAYER)
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
                    "source": "computed", "cached": True}

    moinp = stage_gbw(root, name, state)
    started = time.perf_counter()
    try:
        record = run_orca_job(
            name=job_name, smiles=None,
            xyz=GAS_DIR / name / ("%s_%s.xyz" % (name, state)),
            charge=charge, multiplicity=multiplicity, job=orca.JOB_SINGLE_POINT,
            outdir=mol_dir, solvent=SOLVENT, epsilon=None, seed=args.seed,
            timeout_seconds=args.timeout, nprocs=args.nprocs, moinp=moinp)
    except Exception as exc:  # noqa: BLE001 - a failed job is a result, not a crash
        return {**common, "status": "execution_failed",
                "seconds": round(time.perf_counter() - started, 2),
                "qc_flags": "scf_failed", "error": repr(exc),
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
    if args.molecules:
        wanted = [item.strip() for item in args.molecules.split(",") if item.strip()]
    else:
        wanted = list(core)
    unknown = [name for name in wanted if name not in core]
    if unknown:
        raise SystemExit("molecules absent from core_set.csv: %s" % unknown)

    states = select_states(args.states)
    geometry_audit = audit_geometry(wanted, states)
    reference = reference_rows()

    specs = [(name, state, charge, multiplicity)
             for name in wanted for state, charge, multiplicity in states]

    missing_reference = [spec for spec in specs
                         if (spec[0], spec[1]) not in reference]
    ledger = {
        "stage": 17,
        "part": "the two-guess protocol on the SMD(acetonitrile) P2 rung",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "set": "core_set (all 18 molecules of the week-9 ladder population)",
        "molecules": wanted,
        "n_molecules": len(wanted),
        "states": [state for state, _, _ in states],
        "layer": LAYER,
        "solvent": SOLVENT,
        "arm": "moread",
        "n_cells": len(specs),
        "reference_csv": str(REFERENCE_CSV.relative_to(REPO_ROOT)).replace("\\", "/"),
        "n_cells_without_reference": len(missing_reference),
        "cells_without_reference": ["%s/%s" % (spec[0], spec[1])
                                    for spec in missing_reference],
        "guess_protocol": {
            "default": ("ORCA's own guess, as frozen in week 4 -- read from the "
                        "reference CSV, never recomputed here"),
            "moread": "! MORead + %moinp <gas-phase gbw of the same charge state>",
            "staging_root": str(staging_root()),
            "staging_reason": ("ORCA guess_restart aborts on a non-ASCII %moinp path; "
                               "the repository lives under a Chinese directory name"),
        },
        "geometry_audit": geometry_audit,
        "layers": [],
    }

    if args.plan_only:
        (args.outdir / "stage17_smd_moread_plan.json").write_text(
            json.dumps(ledger, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8", newline="\n")
        print("plan: %d moread cells to compute over %d molecules x %d states; "
              "%d reference rows available"
              % (len(specs), len(wanted), len(states), len(specs) - len(missing_reference)))
        return 0

    if missing_reference:
        raise SystemExit("reference rows missing for: %s"
                         % ledger["cells_without_reference"])

    root = staging_root()
    print("running %d moread cells (%d concurrent, %d procs each) on the %s layer"
          % (len(specs), args.jobs, args.nprocs, LAYER))

    records = []
    with ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool:
        futures = [pool.submit(run_one, spec, args, root, core) for spec in specs]
        for position, future in enumerate(futures, start=1):
            record = future.result()
            records.append(record)
            if record.get("source") == "computed":
                print("  [%d/%d] %-7s %-8s %-24s %-9s %s" % (
                    position, len(specs), record["name"], record["state"],
                    record["layer"], record["status"],
                    "" if not isinstance(record.get("seconds"), (int, float))
                    else "%.1fs" % record["seconds"]))

    tool = toolchain.find_executable("orca")
    version = None if tool is None else toolchain.read_version(tool.path, "orca")

    table = args.outdir / ("p2_core_set_%s.csv" % LAYER)
    fieldnames = COLUMNS + ["layer", "solvent", "epsilon", "guess", "source"]
    with table.open("w", encoding="utf-8", newline="\n") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for record in records:
            writer.writerow(record)

    ok = [record for record in records if record["status"] == "ok"]
    seconds = [record["seconds"] for record in ok
               if isinstance(record.get("seconds"), (int, float))]
    summary = {
        "stage": "P2", "engine": "ORCA", "engine_version": version,
        "method": orca.FROZEN_METHOD,
        "environment": "SMD(acetonitrile)",
        "layer": LAYER, "epsilon": None, "arm": "moread",
        "geometry": "G1, reused from T1 (unchanged)",
        "guess": GUESS_LABEL,
        "n_jobs": len(records), "n_ok": len(ok), "n_failed": len(records) - len(ok),
        "n_reused": sum(1 for record in records if record.get("cached")),
        "n_computed": sum(1 for record in records if record.get("source") == "computed"),
        "nprocs": args.nprocs,
        "wall_clock_seconds_median": (round(statistics.median(seconds), 2)
                                      if seconds else None),
        "output_csv": str(table.relative_to(REPO_ROOT)).replace("\\", "/"),
        "generated_utc": datetime.now(timezone.utc).isoformat(),
    }
    (args.outdir / ("p2_summary_%s.json" % LAYER)).write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8", newline="\n")
    ledger["layers"].append(summary)
    ledger["jobs"] = args.jobs
    ledger["nprocs"] = args.nprocs
    ledger["n_ok"] = len(ok)
    ledger["n_failed"] = len(records) - len(ok)
    (args.outdir / "stage17_smd_moread.json").write_text(
        json.dumps(ledger, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8", newline="\n")

    print("layer %-26s %d/%d ok (%d reused)"
          % (LAYER, len(ok), len(records), summary["n_reused"]))
    print("wrote %s" % table.relative_to(REPO_ROOT))
    return 0 if ledger["n_failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())