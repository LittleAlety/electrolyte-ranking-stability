"""Stage 2 / P2 -- the environment layer: the same three states, in a continuum solvent.

Why this module exists
----------------------
docs/08 section 1 fixes the "single variable" rule for the three layers:

    P0 -> P1   change the electronic-structure method  (geometry and environment fixed)
    P1 -> P2   change the environment only             (method and geometry fixed)

T1 (``scripts/run_core_set_p1.py``) measured the gas phase. This module measures
the *same* r2SCAN-3c single points on the *same* G1 geometry with a continuum
solvent switched on, so that the only difference between the two data sets is the
environment. Everything else -- functional, basis, dispersion, grid, geometry,
charge, multiplicity -- is identical by construction.

Because the geometry is not allowed to relax, the quantity is the **vertical**
ionisation energy / electron affinity in solution, exactly the twin of the gas
phase number. That is what makes the pair difference interpretable: any change is
the electronic response of the solvent, not a geometry relaxation riding along.

Two solvent settings are supported:

* a named SMD solvent (default ``acetonitrile``, the reference solvent frozen in
  docs/08 section 2), which is the production P2 reference;
* a bare CPCM dielectric (``--epsilon``) for the epsilon scan.

Results are written where a layer is expected: ``outputs/week4/orca_smd/...`` and
``outputs/week4/p2_core_set_smd.csv``.
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from electrolyte_ranking import orca, toolchain  # noqa: E402
from run_core_set_p1 import (  # noqa: E402
    COLUMNS,
    STATES,
    _relative,
    load_core_set,
    resolve_geometry,
    select_states,
)
from run_orca_job import run_job as run_orca_job  # noqa: E402

DEFAULT_OUTDIR = REPO_ROOT / "outputs" / "week4"
DEFAULT_SCRATCH = REPO_ROOT / "outputs" / "_week4_scratch"
DEFAULT_SOLVENT = "acetonitrile"


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="P2: r2SCAN-3c single points for the core set in a continuum solvent."
    )
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    parser.add_argument("--scratch", type=Path, default=DEFAULT_SCRATCH)
    environment = parser.add_mutually_exclusive_group()
    environment.add_argument("--solvent", default=DEFAULT_SOLVENT, help="SMD solvent name")
    environment.add_argument("--epsilon", type=float, default=None, help="bare CPCM dielectric")
    parser.add_argument("--layer", default=None, help="output label (default: smd_<solvent> or cpcm_<eps>)")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--only", default=None, help="comma-separated mol_id allow-list")
    parser.add_argument("--states", default="neutral,cation,anion")
    parser.add_argument("--nprocs", type=int, default=None)
    parser.add_argument("--jobs", type=int, default=2)
    parser.add_argument("--timeout", type=float, default=1800.0)
    parser.add_argument("--seed", type=lambda value: int(value, 0), default=0xC0FFEE)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args(argv)


def layer_label(args) -> str:
    if args.layer:
        return args.layer
    if args.epsilon is not None:
        return "cpcm_%g" % args.epsilon
    return "smd_%s" % str(args.solvent).replace(" ", "_")


def main(argv=None) -> int:
    args = parse_args(argv)
    for attribute in ("outdir", "scratch"):
        value = getattr(args, attribute)
        setattr(args, attribute, (value if value.is_absolute() else Path.cwd() / value).resolve())

    layer = layer_label(args)
    rows = load_core_set(REPO_ROOT / "data" / "metadata" / "core_set.csv")
    if args.only:
        wanted = {item.strip() for item in args.only.split(",") if item.strip()}
        rows = [row for row in rows if row["mol_id"] in wanted or row["name"] in wanted]
    if args.limit is not None:
        rows = rows[: args.limit]
    states = select_states(args.states)

    located = toolchain.find_executable("orca")
    if located is None and not args.dry_run:
        print("error: ORCA 未找到；先跑 scripts/check_environment.py", file=sys.stderr)
        return 2
    version = None if located is None else toolchain.read_version(located.path, "orca")

    geometry_dir = args.outdir / "orca"
    layer_dir = args.outdir / ("orca_" + layer)
    layer_dir.mkdir(parents=True, exist_ok=True)

    # Reuse the exact T1 geometries. Recomputing them would silently make the
    # P1 -> P2 comparison change two things at once, which docs/08 forbids.
    geometries = {}
    for row in rows:
        candidates = [
            (geometry_dir / row["name"] / (row["name"] + "_neutral.xyz"), "cached:T1 geometry"),
        ]
        found = next(((path, label) for path, label in candidates if path.exists()), None)
        if found is None:
            try:
                found = resolve_geometry(
                    row, executable=None, scratch=args.scratch, seed=args.seed, force=False
                )
                found = (found[0], found[1] + " (T1 geometry not found)")
            except Exception as exc:  # noqa: BLE001
                found = (None, "unavailable: %r" % (exc,))
        geometries[row["mol_id"]] = found

    def run_one(row, state, charge, multiplicity):
        name = row["name"]
        mol_dir = layer_dir / name
        mol_dir.mkdir(parents=True, exist_ok=True)
        job_name = "%s_%s_%s" % (name, state, layer)
        stored = mol_dir / (job_name + "_orca.json")
        common = {
            "mol_id": row["mol_id"], "name": name, "family": row.get("family", ""),
            "role": row.get("role", ""), "state": state, "charge": charge,
            "multiplicity": multiplicity, "layer": layer,
            "geometry_source": geometries[row["mol_id"]][1], "smiles": row.get("smiles", ""),
            "solvent": "" if args.epsilon is not None else args.solvent,
            "epsilon": "" if args.epsilon is None else args.epsilon,
        }
        if stored.exists() and not args.force:
            try:
                cached = json.loads(stored.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                cached = None
            # A cached "not_run" record only stands in for a job that was itself a
            # dry run. Reusing it in a real run would silently skip the ORCA call and
            # still report ok (observed: a --dry-run into a live outdir poisoned the
            # subsequent real run with 54/54 "ok" and zero .out files).
            if cached is not None and (
                cached.get("status") == "ok"
                or (cached.get("status") == "not_run" and args.dry_run)
            ):
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
                name=job_name, smiles=None, xyz=geometries[row["mol_id"]][0], charge=charge,
                multiplicity=multiplicity, job=orca.JOB_SINGLE_POINT, outdir=mol_dir,
                solvent=args.solvent if args.epsilon is None else None,
                epsilon=args.epsilon, seed=args.seed, timeout_seconds=args.timeout,
                nprocs=args.nprocs, dry_run=args.dry_run,
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

    records = []
    with ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool:
        futures = []
        for row in rows:
            geometry, source = geometries[row["mol_id"]]
            for state, charge, multiplicity in states:
                if geometry is None:
                    records.append({
                        "mol_id": row["mol_id"], "name": row["name"], "state": state,
                        "charge": charge, "multiplicity": multiplicity, "layer": layer,
                        "status": "geometry_failed", "qc_flags": "geometry_failed",
                        "geometry_source": source, "error": source, "cached": False,
                    })
                    continue
                futures.append(pool.submit(run_one, row, state, charge, multiplicity))
        for future in futures:
            record = future.result()
            records.append(record)
            print("  %-8s %-8s %-12s %s" % (
                record["name"], record["state"], record["status"],
                "" if record.get("seconds") in (None, "") else "%ss" % record["seconds"],
            ))

    table = args.outdir / ("p2_core_set_%s.csv" % layer)
    with table.open("w", encoding="utf-8", newline="\n") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS + ["layer", "solvent", "epsilon"],
                                extrasaction="ignore")
        writer.writeheader()
        for record in records:
            writer.writerow(record)

    # A --dry-run record is "not_run", which is an expected outcome, not a failure;
    # counting it as one would make the dry run look broken.
    ok = [record for record in records if record["status"] in ("ok", "not_run")]
    timings = [record["seconds"] for record in ok if isinstance(record.get("seconds"), (int, float))]
    summary = {
        "stage": "P2",
        "engine": "ORCA",
        "engine_version": version,
        "method": orca.FROZEN_METHOD,
        "environment": (
            "CPCM(epsilon=%g)" % args.epsilon if args.epsilon is not None
            else "CPCM(SMD, %s)" % args.solvent
        ),
        "layer": layer,
        "geometry": "G1, reused from T1 (unchanged)",
        "n_jobs": len(records),
        "n_ok": len(ok),
        "n_failed": len(records) - len(ok),
        "nprocs": orca.resolve_nprocs(args.nprocs),
        "wall_clock_seconds_median": round(statistics.median(timings), 2) if timings else None,
        "output_csv": _relative(table),
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "command_line": [str(sys.executable), "scripts/run_core_set_p2.py", *sys.argv[1:]],
    }
    summary_path = args.outdir / ("p2_summary_%s.json" % layer)
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
                            encoding="utf-8", newline="\n")
    print(json.dumps({"layer": layer, "ok": summary["n_ok"], "failed": summary["n_failed"],
                      "median_seconds": summary["wall_clock_seconds_median"],
                      "csv": summary["output_csv"]}, ensure_ascii=False))
    return 0 if summary["n_failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())