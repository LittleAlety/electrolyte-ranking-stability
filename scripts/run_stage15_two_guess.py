"""Stage 15 (week 14), part A -- the two-guess protocol.

Why this module exists
----------------------
Stage 14 showed that the EMC/reduction curve is not Born-like (R2 0.8468 on the
six-point grid, 0.6788 on nine points) and that the EMC anion's *dipole*
alternates between ~2.5 D and ~6.3-7.1 D at neighbouring dielectrics.  That is
the signature of two accessible SCF solutions, but it says nothing about which
one the calculation should have found, nor whether the other one is reachable
from ORCA's default guess.

So the same system is run twice at every dielectric:

* ``default`` -- ORCA's own guess.  For the nine Stage 13/14 dielectrics those
  numbers are already on disk; only ``eps = 1000`` is produced here.
* ``moread`` -- the same job restarted from the *gas-phase* MOs of the same
  charge state (``! MORead`` + ``%moinp``).  Ten dielectrics, all produced here.

The comparison ``E_moread - E_default`` is the quantity of interest.  It is zero
whenever the default guess already found the lowest solution, and **negative**
whenever it did not: the restart reached a state the default guess missed, so the
default guess settled on a solution that is not the lowest one.  The gas-phase MOs are the natural restart because they
belong to the same charge state (an anion restart can only be read into an
anion job) and because they are a solution of a *different* potential, so they
carry no information about the continuum solution we are about to look for.

ASCII staging (a real ORCA gotcha)
----------------------------------
``%moinp`` must point at a plain-ASCII path.  ORCA's ``guess_restart`` module
aborts with ``guess_restart.cpp, line 121`` when the path contains non-ASCII
characters, while the rest of the program opens the very same file happily --
the repository lives under a Chinese directory name, so this is not academic.
Every ``.gbw`` is therefore copied into an ASCII staging root before it is
handed to ``%moinp``.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
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
from run_core_set_p1 import COLUMNS, STATES, select_states  # noqa: E402
from run_orca_job import run_job as run_orca_job  # noqa: E402

DEFAULT_OUTDIR = REPO_ROOT / "outputs" / "week14"
DEFAULT_SCRATCH = REPO_ROOT / "outputs" / "_week14_scratch"

MOLECULES = ("EMC", "DMC", "EC")

#: Ten dielectrics.  5/7/10/14/20/28/40/80/200 are the Stage 13/14 ladder;
#: 1000 is new and turns the conductor limit from an extrapolation into a point.
LADDER = (5.0, 7.0, 10.0, 14.0, 20.0, 28.0, 40.0, 80.0, 200.0, 1000.0)

#: Where the gas-phase MOs and the frozen G1 geometries live.
GAS_DIR = REPO_ROOT / "outputs" / "week4" / "orca"

#: The dielectrics whose *default-guess* result already exists, so only eps = 1000
#: needs a fresh default run.  The values are where that result was stored.
DEFAULT_GUESS_HOME = {
    5.0: "outputs/week4/p2_core_set_cpcm_5.csv",
    7.0: "outputs/week13/p2_core_set_cpcm_7.csv",
    10.0: "outputs/week4/p2_core_set_cpcm_10.csv",
    14.0: "outputs/week13/p2_core_set_cpcm_14.csv",
    20.0: "outputs/week4/p2_core_set_cpcm_20.csv",
    28.0: "outputs/week13/p2_core_set_cpcm_28.csv",
    40.0: "outputs/week4/p2_core_set_cpcm_40.csv",
    80.0: "outputs/week12/p2_core_set_cpcm_80.csv",
    200.0: "outputs/week12/p2_core_set_cpcm_200.csv",
    1000.0: None,
}


def tag(eps: float) -> str:
    return "cpcm_%g" % eps


def moread_layer(eps: float) -> str:
    return "moread_%s" % tag(eps)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Stage 15 part A: restart every continuum job from the gas-phase MOs."
    )
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    parser.add_argument("--scratch", type=Path, default=DEFAULT_SCRATCH)
    parser.add_argument("--levels", default=None,
                        help="comma-separated dielectrics (default: the ten-point ladder)")
    parser.add_argument("--molecules", default=",".join(MOLECULES))
    parser.add_argument("--states", default="neutral,cation,anion")
    parser.add_argument("--nprocs", type=int, default=8)
    parser.add_argument("--jobs", type=int, default=2)
    parser.add_argument("--timeout", type=float, default=1800.0)
    parser.add_argument("--seed", type=lambda value: int(value, 0), default=0xC0FFEE)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--moinp-only", action="store_true",
                        help="skip the eps = 1000 default-guess control run")
    return parser.parse_args(argv)


def staging_root(requested: Path | None = None) -> Path:
    """An ASCII-safe directory to copy ``.gbw`` files into (see the module docstring)."""

    root = Path(tempfile.gettempdir()) if requested is None else requested
    if not str(root).isascii():
        raise SystemExit("staging root is not ASCII-safe: %s" % root)
    root = root / "electrolyte_stage15_gbw"
    root.mkdir(parents=True, exist_ok=True)
    return root


def stage_gbw(root: Path, name: str, state: str) -> Path:
    source = GAS_DIR / name / ("%s_%s.gbw" % (name, state))
    if not source.exists():
        raise SystemExit("missing gas-phase MOs: %s" % source.relative_to(REPO_ROOT))
    target = root / ("%s_%s.gbw" % (name, state))
    shutil.copyfile(source, target)
    return target

def read_coords(path: Path):
    lines = path.read_text(encoding="utf-8").splitlines()
    count = int(lines[0].strip())
    return [tuple(line.split()[1:]) for line in lines[2:2 + count]]


def assert_g1_geometry() -> None:
    """The restart must not change the geometry, or two things change at once.

    ``docs/08`` freezes G1; the gas-phase layer and the continuum layers share it,
    so the two files have to be identical atom for atom.
    """

    reference = REPO_ROOT / "outputs" / "week13" / "orca_cpcm_20"
    for name in MOLECULES:
        for state, _, _ in STATES:
            gas = GAS_DIR / name / ("%s_%s.xyz" % (name, state))
            if not gas.exists():
                raise SystemExit("missing geometry: %s" % gas.relative_to(REPO_ROOT))
            other = reference / name / ("%s_%s_cpcm_20.xyz" % (name, state))
            if other.exists() and read_coords(gas) != read_coords(other):
                raise SystemExit("G1 geometry drift between %s and %s" % (gas, other))


def run_one(spec, args, root: Path):
    name, state, charge, multiplicity, eps, layer, wants_moinp = spec
    mol_dir = args.outdir / ("orca_" + layer) / name
    mol_dir.mkdir(parents=True, exist_ok=True)
    job_name = "%s_%s_%s" % (name, state, layer)
    stored = mol_dir / (job_name + "_orca.json")
    moinp = stage_gbw(root, name, state) if wants_moinp else None

    common = {
        "mol_id": name, "name": name, "state": state, "charge": charge,
        "multiplicity": multiplicity, "layer": layer,
        "geometry_source": "cached:G1 (identical to the gas-phase and P2 layers)",
        "solvent": "", "epsilon": eps,
        "guess": "MORead(gas-phase)" if wants_moinp else "ORCA default",
    }
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
                    "orca_version": result.get("version"), "error": "", "cached": True}

    started = time.perf_counter()
    try:
        record = run_orca_job(
            name=job_name, smiles=None, xyz=GAS_DIR / name / ("%s_%s.xyz" % (name, state)),
            charge=charge, multiplicity=multiplicity, job=orca.JOB_SINGLE_POINT,
            outdir=mol_dir, solvent=None, epsilon=eps, seed=args.seed,
            timeout_seconds=args.timeout, nprocs=args.nprocs, moinp=moinp,
        )
    except Exception as exc:  # noqa: BLE001 - a failed job is a result, not a crash
        return {**common, "status": "execution_failed",
                "seconds": round(time.perf_counter() - started, 2),
                "qc_flags": "scf_failed", "error": repr(exc), "cached": False}
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
            "cached": False}


def main(argv=None) -> int:
    args = parse_args(argv)
    for attribute in ("outdir", "scratch"):
        value = getattr(args, attribute)
        setattr(args, attribute, (value if value.is_absolute() else Path.cwd() / value).resolve())
    args.outdir.mkdir(parents=True, exist_ok=True)
    args.scratch.mkdir(parents=True, exist_ok=True)

    levels = ([float(item) for item in args.levels.split(",") if item.strip()]
              if args.levels else list(LADDER))
    wanted = {item.strip() for item in args.molecules.split(",") if item.strip()}
    molecules = [name for name in MOLECULES if name in wanted]
    if not molecules:
        raise SystemExit("no molecules selected")
    states = select_states(args.states)

    assert_g1_geometry()
    root = staging_root()

    ledger = {
        "stage": 15,
        "part": "A -- the two-guess protocol",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "molecules": molecules,
        "ladder_eps": levels,
        "states": [state for state, _, _ in states],
        "guess_protocol": {
            "default": "ORCA's own guess (already on disk for eps <= 200)",
            "moread": "! MORead + %moinp <gas-phase gbw of the same charge state>",
            "staging_root": str(root),
            "staging_reason": ("ORCA guess_restart aborts on a non-ASCII %moinp path; "
                              "the repository lives under a Chinese directory name"),
        },
        "layers": [],
    }

    specs = []
    for eps in levels:
        for name in molecules:
            for state, charge, multiplicity in states:
                specs.append((name, state, charge, multiplicity, eps,
                              moread_layer(eps), True))
    if 1000.0 in levels and not args.moinp_only:
        for name in molecules:
            for state, charge, multiplicity in states:
                specs.append((name, state, charge, multiplicity, 1000.0,
                              tag(1000.0), False))

    print("running %d jobs (%d concurrent, %d procs each)"
          % (len(specs), args.jobs, args.nprocs))
    records = []
    with ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool:
        futures = [pool.submit(run_one, spec, args, root) for spec in specs]
        for future in futures:
            record = future.result()
            records.append(record)
            print("  %-8s %-8s %-22s %-16s %s" % (
                record["name"], record["state"], record["layer"], record["status"],
                "" if record.get("seconds") in (None, "") else "%ss" % record["seconds"]))

    tool = toolchain.find_executable("orca")
    version = None if tool is None else toolchain.read_version(tool.path, "orca")

    for layer in sorted({record["layer"] for record in records}):
        subset = [record for record in records if record["layer"] == layer]
        eps = subset[0]["epsilon"]
        table = args.outdir / ("p2_core_set_%s.csv" % layer)
        with table.open("w", encoding="utf-8", newline="\n") as handle:
            writer = csv.DictWriter(handle, fieldnames=COLUMNS + ["layer", "solvent",
                                                                 "epsilon", "guess"],
                                    extrasaction="ignore")
            writer.writeheader()
            for record in subset:
                writer.writerow(record)
        ok = [record for record in subset if record["status"] == "ok"]
        seconds = [record["seconds"] for record in ok
                   if isinstance(record.get("seconds"), (int, float))]
        summary = {
            "stage": "P2", "engine": "ORCA", "engine_version": version,
            "method": orca.FROZEN_METHOD,
            "environment": "CPCM(epsilon=%g)" % eps,
            "layer": layer, "epsilon": eps,
            "geometry": "G1, reused from T1 (unchanged)",
            "guess": subset[0]["guess"],
            "n_jobs": len(subset), "n_ok": len(ok),
            "n_failed": len(subset) - len(ok),
            "nprocs": args.nprocs,
            "wall_clock_seconds_median": (round(statistics.median(seconds), 2)
                                          if seconds else None),
            "output_csv": str(table.relative_to(REPO_ROOT)).replace("\\", "/"),
            "generated_utc": datetime.now(timezone.utc).isoformat(),
            "command_line": [sys.executable, "scripts/run_stage15_two_guess.py",
                             "--levels", ",".join("%g" % eps for eps in levels)],
        }
        (args.outdir / ("p2_summary_%s.json" % layer)).write_text(
            json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8", newline="\n")
        ledger["layers"].append(summary)
        print("  layer %-22s %d/%d ok" % (layer, len(ok), len(subset)))

    ledger["n_jobs_expected"] = len(specs)
    ledger["jobs"] = args.jobs
    ledger["nprocs"] = args.nprocs
    ledger["failures"] = sum(layer["n_failed"] for layer in ledger["layers"])
    (args.outdir / "stage15_two_guess.json").write_text(
        json.dumps(ledger, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8", newline="\n")
    print("wrote %s" % (args.outdir / "stage15_two_guess.json").relative_to(REPO_ROOT))
    return 0 if ledger["failures"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())