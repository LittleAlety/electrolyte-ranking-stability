"""Stage 16 (week 15) -- the two-guess catalogue over the whole core set.

Stage 15 (week 14) ran the two-guess protocol on three molecules (EMC, DMC, EC)
and found that ORCA's default SCF guess occasionally settles on a solution that
is *not* the lowest one: restarting the same job from the gas-phase MOs of the
same charge state recovers a state lower by up to 0.286 eV.  Three molecules
cannot say how common that is, nor whether it can be anticipated.

This module turns the protocol into a catalogue:

* ``--set subset``     -- the twelve molecules of the T3 audit subset.
* ``--set validation`` -- the six core-set molecules outside that subset
  (DEC, EA, FEC, MA, TEGDME, VC).  None of them has ever been computed at the
  continuum level, so they are a genuine out-of-sample set.

Both arms of the protocol are produced for every requested cell:

* ``default`` -- ORCA's own guess.  An identical run already on disk from an
  earlier week is reused verbatim and the CSV records which file it came from;
  every other cell is computed here.
* ``moread``  -- the same job restarted from the gas-phase MOs of the same
  charge state (``! MORead`` + ``%moinp``).

Reuse is never silent: each written row carries a ``source`` column that is
either ``computed`` or ``reused:<path>``, and the layer summaries count both.

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

DEFAULT_OUTDIR = REPO_ROOT / "outputs" / "week15"
DEFAULT_SCRATCH = REPO_ROOT / "outputs" / "_week15_scratch"
GAS_DIR = REPO_ROOT / "outputs" / "week4" / "orca"
CORE_SET = REPO_ROOT / "data" / "metadata" / "core_set.csv"

SUBSET = ("EC", "PC", "DMC", "EMC", "DME", "DOL", "GBL", "AN", "SN", "DMSO", "SL", "TMP")
VALIDATION = ("DEC", "EA", "FEC", "MA", "TEGDME", "VC")
SETS = {"subset": SUBSET, "validation": VALIDATION}

#: The Stage 13/14/15 dielectric ladder, reused verbatim so the new cells are
#: directly comparable with the three-molecule study.
LADDER = (5.0, 7.0, 10.0, 14.0, 20.0, 28.0, 40.0, 80.0, 200.0, 1000.0)

#: The six dielectrics where the whole twelve-molecule default arm already
#: exists.  The primary label of the study is defined on this set so that the
#: discovery and the validation arms are scored on an identical ladder.
FOCUS = (5.0, 10.0, 20.0, 40.0, 80.0, 200.0)

#: Default-guess single points already on disk, indexed as (name, state, eps).
DEFAULT_SOURCES = (
    "outputs/week4/p2_core_set_cpcm_5.csv",
    "outputs/week4/p2_core_set_cpcm_10.csv",
    "outputs/week4/p2_core_set_cpcm_20.csv",
    "outputs/week4/p2_core_set_cpcm_40.csv",
    "outputs/week12/p2_core_set_cpcm_80.csv",
    "outputs/week12/p2_core_set_cpcm_200.csv",
    "outputs/week13/p2_core_set_cpcm_7.csv",
    "outputs/week13/p2_core_set_cpcm_14.csv",
    "outputs/week13/p2_core_set_cpcm_28.csv",
    "outputs/week14/p2_core_set_cpcm_1000.csv",
)

#: Gas-phase-restart single points already on disk (week 14; EMC/DMC/EC only).
MOREAD_SOURCES = tuple("outputs/week14/p2_core_set_moread_cpcm_%g.csv" % eps
                       for eps in LADDER)

ARMS = ("default", "moread")


def tag(eps: float) -> str:
    return "cpcm_%g" % eps


def moread_layer(eps: float) -> str:
    return "moread_%s" % tag(eps)


def load_index(relative_paths):
    """Map (name, state, epsilon) -> (source path, row) for every ok row."""

    index = {}
    for relative in relative_paths:
        path = REPO_ROOT / relative
        if not path.exists():
            continue
        with path.open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                if row.get("status") != "ok":
                    continue
                if not row.get("final_energy_eh"):
                    continue
                key = (row["name"], row["state"], round(float(row["epsilon"]), 6))
                index.setdefault(key, (relative, row))
    return index


def load_core_set():
    """mol_id / family / role / smiles for every core-set molecule."""

    with CORE_SET.open(encoding="utf-8", newline="") as handle:
        return {row["name"]: row for row in csv.DictReader(handle)}


def read_coords(path: Path):
    lines = path.read_text(encoding="utf-8").splitlines()
    count = int(lines[0].strip())
    return [tuple(line.split()[1:]) for line in lines[2:2 + count]]


def audit_geometry(molecules, states):
    """The gas-phase .xyz must equal any continuum .xyz already on disk.

    ``docs/08`` freezes G1.  The continuum arm and the gas-phase arm share that
    geometry, so restarting a continuum job from gas-phase MOs must not change a
    single coordinate.  Where no continuum geometry has ever been produced the
    check is reported as not applicable rather than silently skipped.
    """

    audit = {}
    for name in molecules:
        reference = None
        for week in ("week4", "week12", "week13", "week14"):
            candidate = REPO_ROOT / "outputs" / week / "orca_cpcm_20" / name
            if candidate.is_dir() and reference is None:
                reference = candidate
        entry = {"name": name, "reference": None, "n_compared": 0,
                 "all_identical": None, "note": ""}
        if reference is None:
            entry["note"] = ("no continuum geometry on disk; the frozen gas-phase "
                             "G1 xyz is the only geometry source for this molecule")
            audit[name] = entry
            continue
        entry["reference"] = str(reference.relative_to(REPO_ROOT)).replace("\\", "/")
        comparisons = []
        for state, _, _ in states:
            gas = GAS_DIR / name / ("%s_%s.xyz" % (name, state))
            other = reference / ("%s_%s_cpcm_20.xyz" % (name, state))
            if gas.exists() and other.exists():
                comparisons.append(read_coords(gas) == read_coords(other))
        entry["n_compared"] = len(comparisons)
        entry["all_identical"] = bool(comparisons) and all(comparisons)
        if not entry["all_identical"]:
            raise SystemExit("G1 geometry drift for %s (vs %s)" % (name, reference))
        audit[name] = entry
    return audit


def staging_root(requested=None) -> Path:
    root = Path(tempfile.gettempdir()) if requested is None else requested
    if not str(root).isascii():
        raise SystemExit("staging root is not ASCII-safe: %s" % root)
    root = root / "electrolyte_stage16_gbw"
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
        description="Stage 16: two-guess catalogue over the core set.")
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    parser.add_argument("--scratch", type=Path, default=DEFAULT_SCRATCH)
    parser.add_argument("--set", dest="which_set", default="subset",
                        choices=sorted(SETS))
    parser.add_argument("--molecules", default=None,
                        help="explicit comma-separated names (overrides --set)")
    parser.add_argument("--arms", default="default,moread")
    parser.add_argument("--levels", default=None,
                        help="comma-separated dielectrics (default: the ten-point ladder)")
    parser.add_argument("--states", default="neutral,cation,anion")
    parser.add_argument("--nprocs", type=int, default=8)
    parser.add_argument("--jobs", type=int, default=2)
    parser.add_argument("--timeout", type=float, default=1800.0)
    parser.add_argument("--seed", type=lambda value: int(value, 0), default=0xC0FFEE)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--plan-only", action="store_true")
    parser.add_argument("--tag", default="",
                        help="prefix for the layer tables, e.g. 'holdout'.  The held-out "
                             "arm must not overwrite the discovery arm's layer CSVs, and "
                             "an accidental overwrite is invisible in a diff of numbers")
    return parser.parse_args(argv)

def reuse_row(source_path, row, layer, eps, guess, core):
    """A CSV row copied verbatim from an earlier week, tagged with its origin."""

    meta = core.get(row["name"], {})
    record = {column: row.get(column, "") for column in COLUMNS}
    record.update({
        "mol_id": row.get("mol_id") or meta.get("mol_id", ""),
        "name": row["name"],
        "family": row.get("family") or meta.get("family", ""),
        "role": row.get("role") or meta.get("role", ""),
        "smiles": row.get("smiles") or meta.get("smiles", ""),
        "state": row["state"],
        "layer": layer,
        "epsilon": eps,
        "solvent": "",
        "guess": guess,
        "source": "reused:%s" % source_path,
        "cached": True,
    })
    return record


def run_one(spec, args, root, index, core):
    name, state, charge, multiplicity, eps, layer, arm = spec
    meta = core.get(name, {})
    common = {
        "mol_id": meta.get("mol_id", ""), "name": name,
        "family": meta.get("family", ""), "role": meta.get("role", ""),
        "smiles": meta.get("smiles", ""), "state": state, "charge": charge,
        "multiplicity": multiplicity, "layer": layer, "epsilon": eps,
        "solvent": "",
        "geometry_source": "cached:G1 (identical to the gas-phase and P2 layers)",
        "guess": "MORead(gas-phase)" if arm == "moread" else "ORCA default",
    }

    key = (name, state, round(eps, 6))
    table = index["default"] if arm == "default" else index["moread"]
    if not args.force and key in table:
        source_path, row = table[key]
        return reuse_row(source_path, row, layer, eps, common["guess"], core)

    mol_dir = args.outdir / ("orca_" + layer) / name
    mol_dir.mkdir(parents=True, exist_ok=True)
    job_name = "%s_%s_%s" % (name, state, layer)
    stored = mol_dir / (job_name + "_orca.json")
    moinp = stage_gbw(root, name, state) if arm == "moread" else None

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

    started = time.perf_counter()
    try:
        record = run_orca_job(
            name=job_name, smiles=None,
            xyz=GAS_DIR / name / ("%s_%s.xyz" % (name, state)),
            charge=charge, multiplicity=multiplicity, job=orca.JOB_SINGLE_POINT,
            outdir=mol_dir, solvent=None, epsilon=eps, seed=args.seed,
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

    if args.molecules:
        wanted = [item.strip() for item in args.molecules.split(",") if item.strip()]
    else:
        wanted = list(SETS[args.which_set])
    levels = ([float(item) for item in args.levels.split(",") if item.strip()]
              if args.levels else list(LADDER))
    arms = [item.strip() for item in args.arms.split(",") if item.strip()]
    unknown = [item for item in arms if item not in ARMS]
    if unknown:
        raise SystemExit("unknown arms %s; choose from %s" % (unknown, list(ARMS)))
    states = select_states(args.states)

    core = load_core_set()
    missing_meta = [name for name in wanted if name not in core]
    if missing_meta:
        raise SystemExit("molecules absent from core_set.csv: %s" % missing_meta)
    geometry_audit = audit_geometry(wanted, states)

    index = {"default": load_index(DEFAULT_SOURCES),
             "moread": load_index(MOREAD_SOURCES)}

    prefix = "%s_" % args.tag.strip() if args.tag.strip() else ""
    specs = []
    for arm in arms:
        for eps in levels:
            layer = prefix + (moread_layer(eps) if arm == "moread" else tag(eps))
            for name in wanted:
                for state, charge, multiplicity in states:
                    specs.append((name, state, charge, multiplicity, eps, layer, arm))

    reusable = 0
    for spec in specs:
        table = index["default"] if spec[6] == "default" else index["moread"]
        if (spec[0], spec[1], round(spec[4], 6)) in table:
            reusable += 1

    ledger = {
        "stage": 16,
        "part": ("A -- the two-guess catalogue over the core set"
                 if not args.tag.strip() else
                 "A2 -- the held-out arm of the two-guess catalogue"),
        "tag": args.tag.strip(),
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "set": args.which_set,
        "molecules": wanted,
        "n_molecules": len(wanted),
        "ladder_eps": levels,
        "focus_eps": [eps for eps in FOCUS if eps in levels],
        "states": [state for state, _, _ in states],
        "arms": arms,
        "n_cells": len(specs),
        "n_cells_reused": reusable,
        "n_cells_computed": len(specs) - reusable,
        "guess_protocol": {
            "default": "ORCA's own guess; reused verbatim when an identical run "
                       "already exists from an earlier week",
            "moread": "! MORead + %moinp <gas-phase gbw of the same charge state>",
            "staging_root": str(staging_root()),
            "staging_reason": ("ORCA guess_restart aborts on a non-ASCII %moinp path; "
                               "the repository lives under a Chinese directory name"),
        },
        "geometry_audit": geometry_audit,
        "sources": {"default": list(DEFAULT_SOURCES), "moread": list(MOREAD_SOURCES)},
        "layers": [],
    }

    if args.plan_only:
        (args.outdir / ("stage16_%s_plan.json" % (args.tag.strip() or "catalogue"))).write_text(
            json.dumps(ledger, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8", newline="\n")
        print("plan: %d cells (%d reused, %d to compute) over %d layers"
              % (len(specs), reusable, len(specs) - reusable, len(levels) * len(arms)))
        return 0

    assert_g1 = all(entry["all_identical"] for entry in geometry_audit.values()
                    if entry["all_identical"] is not None)
    if not assert_g1:
        raise SystemExit("geometry audit failed")

    root = staging_root()
    print("running %d cells (%d concurrent, %d procs each); %d reused, %d to compute"
          % (len(specs), args.jobs, args.nprocs, reusable, len(specs) - reusable))

    records = []
    with ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool:
        futures = [pool.submit(run_one, spec, args, root, index, core) for spec in specs]
        for position, future in enumerate(futures, start=1):
            record = future.result()
            records.append(record)
            if record.get("source") == "computed":
                print("  [%d/%d] %-6s %-8s %-22s %-9s %s" % (
                    position, len(specs), record["name"], record["state"],
                    record["layer"], record["status"],
                    "" if not isinstance(record.get("seconds"), (int, float))
                    else "%.1fs" % record["seconds"]))

    tool = toolchain.find_executable("orca")
    version = None if tool is None else toolchain.read_version(tool.path, "orca")

    for layer in sorted({record["layer"] for record in records},
                        key=lambda name: (name.startswith("moread"),
                                          float(name.rsplit("_", 1)[1]))):
        subset = [record for record in records if record["layer"] == layer]
        eps = float(subset[0]["epsilon"])
        arm = "moread" if subset[0]["guess"].startswith("MORead") else "default"
        table = args.outdir / ("p2_core_set_%s.csv" % layer)
        fieldnames = COLUMNS + ["layer", "solvent", "epsilon", "guess", "source"]
        with table.open("w", encoding="utf-8", newline="\n") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames,
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
            "layer": layer, "epsilon": eps, "arm": arm,
            "geometry": "G1, reused from T1 (unchanged)",
            "guess": ("MORead(gas-phase)" if arm == "moread" else "ORCA default"),
            "n_jobs": len(subset), "n_ok": len(ok),
            "n_failed": len(subset) - len(ok),
            "n_reused": sum(1 for record in subset if record.get("cached")),
            "n_computed": sum(1 for record in subset
                              if record.get("source") == "computed"),
            "nprocs": args.nprocs,
            "wall_clock_seconds_median": (round(statistics.median(seconds), 2)
                                          if seconds else None),
            "output_csv": str(table.relative_to(REPO_ROOT)).replace("\\", "/"),
            "generated_utc": datetime.now(timezone.utc).isoformat(),
        }
        (args.outdir / ("p2_summary_%s.json" % layer)).write_text(
            json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8", newline="\n")
        ledger["layers"].append(summary)
        print("  layer %-22s %d/%d ok (%d reused)"
              % (layer, len(ok), len(subset), summary["n_reused"]))

    ledger["jobs"] = args.jobs
    ledger["nprocs"] = args.nprocs
    ledger["n_ok"] = sum(layer["n_ok"] for layer in ledger["layers"])
    ledger["n_failed"] = sum(layer["n_failed"] for layer in ledger["layers"])
    ledger_path = args.outdir / ("stage16_%s.json"
                                 % (args.tag.strip() or "catalogue"))
    ledger_path.write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8", newline="\n")
    print("wrote %s" % ledger_path.relative_to(REPO_ROOT))
    return 0 if ledger["n_failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())