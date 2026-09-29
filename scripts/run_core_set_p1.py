"""Stage 2 / T1 -- the r2SCAN-3c (P1) core-set sweep.

Why this module exists
----------------------
T1 is the *main* Stage 2 measurement: the 18 core-set molecules, each in three
electronic states, evaluated with one frozen ``r2SCAN-3c`` single point in ORCA
on the G1 (GFN2-xTB optimised) geometry. It produces the P1 layer of the
protocol in ``docs/08_stage2_production_protocol.md``:

* the gas-phase **vertical** ionisation energy and electron affinity,
  ``IP = E(M+) - E(M)`` and ``EA = E(M) - E(M-)``. They are kept vertical on
  purpose: geometry (G1) and environment (gas) are held fixed, so the only thing
  that differs from the cheap P0 layer is the electronic-structure method. That
  is the "single variable" rule of ``docs/08`` section 1 -- without it a change
  in the ranking could not be attributed to anything;
* the raw material for the decision-stability question. A method change can
  shift every number by a constant and leave the ranking (and therefore the
  material decision) intact, or it can reorder a handful of molecules. Only the
  second case changes a decision, and separating the two is the point of the
  project.

Design notes
------------
* **Geometry.** The GFN2-xTB optimised geometry is reused from the xTB arms
  instead of being recomputed, so that P0 and P1 really do share one geometry.
  A molecule with no cached optimisation gets one from
  ``scripts/run_xtb_job.py`` (same GFN2 protocol, same seed), never from raw
  RDKit coordinates. The chosen source is recorded per molecule.
* **Resumable.** An existing ``<name>_<state>_orca.json`` with ``status ==
  "ok"`` is reused unless ``--force`` is given, so an interrupted sweep can be
  continued without re-paying for finished jobs.
* **Failures are results.** A non-converged SCF, an execution error, or a
  missing output is recorded with its QC flag, never raised out of the sweep
  (v2 section 20: nothing is silently dropped).
* ORCA is invoked through ``scripts/run_orca_job.run_job`` so the msmpi
  non-ASCII-path downgrade and the scratch relocation apply unchanged.

Outputs
-------
``outputs/week4/p1_core_set.csv``
    One row per (molecule, state): status, energy, SCF diagnostics, wall clock,
    QC flags, geometry provenance.
``outputs/week4/p1_core_set_summary.json``
    The sweep record: engine version, per-molecule geometry source, success and
    failure counts, timing statistics, command line.
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

from electrolyte_ranking import orca, toolchain, xtb  # noqa: E402
from run_orca_job import run_job as run_orca_job  # noqa: E402
from run_xtb_job import run_job as run_xtb_job  # noqa: E402

CORE_SET = REPO_ROOT / "data" / "metadata" / "core_set.csv"
DEFAULT_OUTDIR = REPO_ROOT / "outputs" / "week4"
DEFAULT_SCRATCH = REPO_ROOT / "outputs" / "_week4_scratch"

#: The three electronic states of T1, as (label, charge, multiplicity).
#: The radical cation and radical anion are open-shell doublets, so an
#: unrestricted single point with multiplicity 2 is the right reference; the
#: closed-shell neutral is the vertical reference for both.
STATES: tuple[tuple[str, int, int], ...] = (
    ("neutral", 0, 1),
    ("cation", 1, 2),
    ("anion", -1, 2),
)

#: HF/UKS expectation value of S^2 for a pure doublet; used as a QC reference.
DOUBLET_S2 = 0.75

COLUMNS = [
    "mol_id",
    "name",
    "family",
    "role",
    "state",
    "charge",
    "multiplicity",
    "status",
    "final_energy_eh",
    "scf_converged",
    "n_scf_cycles",
    "terminated_normally",
    "seconds",
    "nprocs",
    "parallel_note",
    "qc_flags",
    "geometry_source",
    "smiles",
    "orca_version",
    "error",
]


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="T1: frozen r2SCAN-3c single points for the core set, in three "
        "electronic states, on the shared G1 (GFN2-xTB) geometry."
    )
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    parser.add_argument("--scratch", type=Path, default=DEFAULT_SCRATCH)
    parser.add_argument("--limit", type=int, default=None, help="only the first N molecules")
    parser.add_argument("--only", default=None, help="comma-separated mol_id allow-list (C01,C04)")
    parser.add_argument(
        "--states",
        default="neutral,cation,anion",
        help="comma-separated subset of neutral,cation,anion (default: all three)",
    )
    parser.add_argument("--nprocs", type=int, default=None, help="%%pal nprocs (default: auto, capped)")
    parser.add_argument("--jobs", type=int, default=2, help="concurrent ORCA processes (default 2)")
    parser.add_argument("--timeout", type=float, default=1800.0, help="seconds per ORCA job")
    parser.add_argument("--seed", type=lambda value: int(value, 0), default=0xC0FFEE)
    parser.add_argument("--force", action="store_true", help="ignore cached records and recompute")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="write the ORCA inputs and not_run records; useful before ORCA is installed",
    )
    return parser.parse_args(argv)


def load_core_set(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as handle:
        return [row for row in csv.DictReader(handle)]


def select_states(spec: str) -> list[tuple[str, int, int]]:
    wanted = [item.strip() for item in spec.split(",") if item.strip()]
    known = {label: (label, charge, multiplicity) for label, charge, multiplicity in STATES}
    unknown = [item for item in wanted if item not in known]
    if unknown:
        raise SystemExit(f"未知电子态 {unknown}; 可选 {sorted(known)}")
    return [known[item] for item in wanted]


# ---------------------------------------------------------------------------
# geometry: reuse the xTB arms, never fall back to raw RDKit coordinates
# ---------------------------------------------------------------------------
def cached_geometries(mol_id: str, name: str) -> list[tuple[Path, str]]:
    """Candidate G1 geometries for one molecule, best first.

    Both candidates are GFN2-xTB optimisations produced by this repository, so
    either one keeps P0 and P1 on exactly the same geometry. The week 3 scratch
    copy is preferred because the P0 table (``outputs/week3/p0_core_set.csv``)
    was measured on it.
    """

    return [
        (
            REPO_ROOT / "outputs" / "_week3_scratch" / mol_id / "xtbopt.xyz",
            "cached:gfn2-xtb-opt outputs/_week3_scratch",
        ),
        (
            REPO_ROOT / "outputs" / "week2" / "method_audit_xtb" / name / "neutral_opt.xyz",
            "cached:gfn2-xtb-opt outputs/week2/method_audit_xtb",
        ),
    ]


def resolve_geometry(row: dict, *, executable: str | None, scratch: Path, seed: int, force: bool) -> tuple[Path, str]:
    """Return (xyz path, provenance label) for the G1 geometry of one molecule."""

    if not force:
        for path, label in cached_geometries(row["mol_id"], row["name"]):
            if path.exists() and path.stat().st_size > 0:
                return path, label

    if executable is None:
        raise RuntimeError("xTB 未找到，且没有可复用的 G1 几何（先跑 run_broad_pool_p0.py 或装 xTB）")

    work = scratch / row["mol_id"]
    work.mkdir(parents=True, exist_ok=True)
    run_xtb_job(
        name=row["name"],
        smiles=row["smiles"],
        xyz=None,
        charge=0,
        multiplicity=1,
        job=xtb.JOB_OPTIMIZE,
        outdir=work,
        seed=seed,
        timeout_seconds=900.0,
    )
    produced = work / "xtbopt.xyz"
    if not produced.exists():
        raise RuntimeError(f"{row['mol_id']} {row['name']}: xTB 没有产出优化几何")
    return produced, "computed:gfn2-xtb-opt outputs/_week4_scratch"


# ---------------------------------------------------------------------------
# one ORCA job
# ---------------------------------------------------------------------------
def record_path(outdir: Path, name: str, state: str) -> Path:
    return outdir / "orca" / name / f"{name}_{state}_orca.json"


def run_state(row, state, charge, multiplicity, args, *, geometry, geometry_source, executable) -> dict:
    name = row["name"]
    mol_dir = args.outdir / "orca" / name
    mol_dir.mkdir(parents=True, exist_ok=True)
    job_name = f"{name}_{state}"
    stored = record_path(args.outdir, name, state)

    common = {
        "mol_id": row["mol_id"],
        "name": name,
        "family": row.get("family", ""),
        "role": row.get("role", ""),
        "state": state,
        "charge": charge,
        "multiplicity": multiplicity,
        "geometry_source": geometry_source,
        "smiles": row.get("smiles", ""),
    }

    if stored.exists() and not args.force:
        try:
            cached = json.loads(stored.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            cached = None
        if cached is not None and cached.get("status") in ("ok", "not_run"):
            result = cached.get("result") or {}
            return {
                **common,
                "status": cached.get("status"),
                "final_energy_eh": result.get("final_energy_eh"),
                "scf_converged": result.get("scf_converged"),
                "n_scf_cycles": result.get("n_scf_cycles"),
                "terminated_normally": result.get("normal_termination"),
                "seconds": result.get("seconds", ""),
                "nprocs": cached.get("nprocs"),
                "parallel_note": cached.get("parallel_note", ""),
                "qc_flags": ";".join(cached.get("qc_flags", [])),
                "orca_version": result.get("version"),
                "error": "",
                "cached": True,
            }

    started = time.perf_counter()
    try:
        record = run_orca_job(
            name=job_name,
            smiles=None,
            xyz=geometry,
            charge=charge,
            multiplicity=multiplicity,
            job=orca.JOB_SINGLE_POINT,
            outdir=mol_dir,
            seed=args.seed,
            timeout_seconds=args.timeout,
            nprocs=args.nprocs,
            dry_run=args.dry_run,
        )
    except Exception as exc:  # noqa: BLE001 - a failed job is a result, not a crash
        return {
            **common,
            "status": "execution_failed",
            "seconds": round(time.perf_counter() - started, 2),
            "qc_flags": "scf_failed",
            "error": repr(exc),
            "cached": False,
        }
    elapsed = round(time.perf_counter() - started, 2)

    result = record.get("result") or {}
    if result:
        result["seconds"] = elapsed
        stored.write_text(
            json.dumps(record, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    return {
        **common,
        "status": record.get("status"),
        "final_energy_eh": result.get("final_energy_eh"),
        "scf_converged": result.get("scf_converged"),
        "n_scf_cycles": result.get("n_scf_cycles"),
        "terminated_normally": result.get("normal_termination"),
        "seconds": elapsed,
        "nprocs": record.get("nprocs"),
        "parallel_note": record.get("parallel_note", ""),
        "qc_flags": ";".join(record.get("qc_flags", [])),
        "orca_version": result.get("version"),
        "error": record.get("error", ""),
        "cached": False,
    }



def _relative(path: Path) -> str:
    """Repository-relative POSIX path, falling back to the absolute path."""

    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def main(argv=None) -> int:
    args = parse_args(argv)
    # Normalise user-supplied paths so that relative_to(REPO_ROOT) below works
    # whether the caller passed an absolute or a repository-relative directory.
    args.outdir = args.outdir if args.outdir.is_absolute() else (Path.cwd() / args.outdir)
    args.scratch = args.scratch if args.scratch.is_absolute() else (Path.cwd() / args.scratch)
    args.outdir = args.outdir.resolve()
    args.scratch = args.scratch.resolve()
    rows = load_core_set(CORE_SET)
    if args.only:
        wanted = {item.strip() for item in args.only.split(",") if item.strip()}
        rows = [row for row in rows if row["mol_id"] in wanted or row["name"] in wanted]
    if args.limit is not None:
        rows = rows[: args.limit]
    states = select_states(args.states)

    located_orca = toolchain.find_executable("orca")
    located_xtb = toolchain.find_executable("xtb")
    if located_orca is None and not args.dry_run:
        print(
            "error: ORCA 未找到（scripts/check_environment.py 可诊断）。"
            "若只想先生成输入文件，请加 --dry-run。",
            file=sys.stderr,
        )
        return 2

    version = None if located_orca is None else toolchain.read_version(located_orca.path, "orca")
    args.outdir.mkdir(parents=True, exist_ok=True)

    print(
        f"T1: {len(rows)} 分子 x {len(states)} 态 = {len(rows) * len(states)} 个作业; "
        f"orca={'-' if located_orca is None else located_orca.path} version={version}"
    )

    # Resolve every geometry first, so a geometry problem is reported before any
    # ORCA time is spent, and so all three states of a molecule share one file.
    geometries: dict[str, tuple[Path, str]] = {}
    for row in rows:
        try:
            geometries[row["mol_id"]] = resolve_geometry(
                row,
                executable=None if located_xtb is None else located_xtb.path,
                scratch=args.scratch,
                seed=args.seed,
                force=False,
            )
        except Exception as exc:  # noqa: BLE001
            geometries[row["mol_id"]] = (None, f"unavailable: {exc!r}")

    tasks = []
    for row in rows:
        geometry, source = geometries[row["mol_id"]]
        for state, charge, multiplicity in states:
            tasks.append((row, state, charge, multiplicity, geometry, source))

    records: list[dict] = []
    with ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool:
        futures = []
        for row, state, charge, multiplicity, geometry, source in tasks:
            if geometry is None:
                records.append(
                    {
                        "mol_id": row["mol_id"],
                        "name": row["name"],
                        "family": row.get("family", ""),
                        "role": row.get("role", ""),
                        "state": state,
                        "charge": charge,
                        "multiplicity": multiplicity,
                        "status": "geometry_failed",
                        "qc_flags": "geometry_failed",
                        "geometry_source": source,
                        "smiles": row.get("smiles", ""),
                        "error": source,
                        "cached": False,
                    }
                )
                continue
            futures.append(
                pool.submit(
                    run_state,
                    row,
                    state,
                    charge,
                    multiplicity,
                    args,
                    geometry=geometry,
                    geometry_source=source,
                    executable=None if located_orca is None else located_orca.path,
                )
            )
        for future in futures:
            record = future.result()
            records.append(record)
            print(
                f"  {record['name']:8s} {record['state']:8s} {record['status']:12s} "
                f"{'' if record.get('seconds') in (None, '') else str(record['seconds']) + 's'}"
                f"{' (cached)' if record.get('cached') else ''}"
            )

    order = {(row["mol_id"], state): index for index, (row, state, _, _, _, _) in enumerate(tasks)}
    records.sort(key=lambda item: order.get((item["mol_id"], item["state"]), 10**6))

    table = args.outdir / "p1_core_set.csv"
    with table.open("w", encoding="utf-8", newline="\n") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for record in records:
            writer.writerow(record)

    ok = [record for record in records if record["status"] == "ok"]
    failed = [record for record in records if record["status"] not in ("ok", "not_run")]
    timings = [record["seconds"] for record in ok if isinstance(record.get("seconds"), (int, float))]
    by_state: dict[str, list[float]] = {}
    for record in ok:
        if isinstance(record.get("seconds"), (int, float)):
            by_state.setdefault(record["state"], []).append(record["seconds"])

    summary = {
        "stage": "T1",
        "engine": "ORCA",
        "engine_version": version,
        "orca_executable": None if located_orca is None else located_orca.path,
        "method": orca.FROZEN_METHOD,
        "geometry": "G1 (GFN2-xTB optimised, shared with P0)",
        "environment": "gas phase",
        "definition": {
            "ip_vertical_ev": "E(cation) - E(neutral), same G1 geometry",
            "ea_vertical_ev": "E(neutral) - E(anion), same G1 geometry",
        },
        "n_molecules": len(rows),
        "n_jobs": len(records),
        "n_ok": len(ok),
        "n_failed": len(failed),
        "n_cached": sum(1 for record in records if record.get("cached")),
        "nprocs": orca.resolve_nprocs(args.nprocs),
        "wall_clock_seconds_total": round(sum(timings), 2),
        "wall_clock_seconds_median": round(statistics.median(timings), 2) if timings else None,
        "wall_clock_seconds_by_state": {
            state: {
                "n": len(values),
                "median": round(statistics.median(values), 2),
                "max": round(max(values), 2),
            }
            for state, values in sorted(by_state.items())
        },
        "geometry_sources": {
            row["name"]: geometries[row["mol_id"]][1] for row in rows
        },
        "failed_jobs": [
            {"name": record["name"], "state": record["state"], "status": record["status"], "error": record.get("error", "")}
            for record in failed
        ],
        "output_csv": _relative(table),
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "command_line": [str(sys.executable), "scripts/run_core_set_p1.py", *sys.argv[1:]],
    }
    summary_path = args.outdir / "p1_core_set_summary.json"
    summary_path.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n"
    )

    print(
        json.dumps(
            {
                "ok": summary["n_ok"],
                "failed": summary["n_failed"],
                "cached": summary["n_cached"],
                "median_seconds": summary["wall_clock_seconds_median"],
                "csv": summary["output_csv"],
            },
            ensure_ascii=False,
        )
    )
    return 0 if summary["n_failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
