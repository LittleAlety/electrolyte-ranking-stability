"""Stage 21 / week 20, Part A -- is the second SCF solution a separate basin?

Stage 19 (week 18) relaxed every ``moread_lower`` cell twice, once from ORCA's own
guess and once from ``! MORead``.  The verdict was read off a single number: the
geometry RMSD between the two relaxed endpoints (<= 0.02 A -> ``same_*``, else
``distinct_*``).  Across 37 cells that produced 6 clean ``same`` cases (RMSD 0.000)
and 2 clean ``distinct`` cases (RMSD > 2 A), but it also put five EC/cation cells in a
*continuous* band 0.021 - 0.100 A and then cut the band in half: eps = 20 and 14
were called ``same_higher`` while eps = 5, 7 and 10 were called ``distinct_lower``.
That is the single most fragile call in the whole project, and an RMSD threshold
cannot settle it: two endpoints 0.03 A apart can be the same basin with a sloppy
optimiser, or two basins with a nearly absent barrier.

The way to settle it is the energy *between* the endpoints.  This stage walks the
straight line in Cartesian space between the two relaxed geometries, freezes the
nuclear frame at each of ``--images`` interior points, and runs one r2SCAN-3c single
point per point, with the cell's own CPCM(epsilon) exactly as in Stage 10/14/15.

The profile answers the question the RMSD cannot:

* monotone, barrier-free profile -> the two endpoints are two shoulders of one basin,
  the "second solution" is a solution-branch artefact, and ``same_*`` is right;
* a genuine hump -> two basins, ``distinct_*`` is right, and the hump height is the
  activation energy that separates them on the frozen surface.

Only three cells are walked, chosen to bracket the argument:

* ``EC/cation/eps=5``   -- RMSD 0.100 A, judged ``distinct_lower`` (long end of the band)
* ``EC/cation/eps=20``  -- RMSD 0.021 A, judged ``same_higher`` (short end, other verdict)
* ``TEGDME/anion/eps=20`` -- RMSD 2.214 A, judged ``distinct_lower`` (unambiguous control)

Both the relaxed (Stage 19 ``Opt``) endpoint energies and the *frozen* endpoint single
points are reported, so the profile is never contaminated by the relaxation.

No geometry is re-optimised: every point is a single point on an interpolated frame,
which keeps the comparison to Stage 19 and Stage 10/14/15 exact.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from electrolyte_ranking import orca  # noqa: E402
from run_orca_job import run_job as run_orca_job  # noqa: E402

DEFAULT_OUTDIR = REPO_ROOT / "outputs" / "week20"
DEFAULT_SCRATCH = REPO_ROOT / "outputs" / "_week20_scratch"
REL_CACHE = REPO_ROOT / "outputs" / "week18" / "stage19_relax_cells.csv"
CORE_SET = REPO_ROOT / "data" / "metadata" / "core_set.csv"

ARMS = ("default", "moread")
ARM_DIR = {"default": "orca_relax_default", "moread": "orca_relax_moread"}

#: (name, state, epsilon) -- the three walked cells, with the Stage 19 verdict and
#: endpoint RMSD carried along so the analysis never has to re-derive them.
CELLS = (
    {"name": "EC", "state": "cation", "epsilon": 5.0,
     "rmsd_a": 0.100, "stage19_verdict": "distinct_lower"},
    {"name": "EC", "state": "cation", "epsilon": 20.0,
     "rmsd_a": 0.021, "stage19_verdict": "same_higher"},
    {"name": "TEGDME", "state": "anion", "epsilon": 20.0,
     "rmsd_a": 2.214, "stage19_verdict": "distinct_lower"},
)

SOURCE_LABEL = ("outputs/week18/orca_relax_{arm}/<name>/<name>_<state>_cpcm_<eps>_"
                "{arm}.xyz (Stage 19 relaxed endpoint, frozen here)")


def load_core_set():
    with CORE_SET.open(encoding="utf-8", newline="") as handle:
        return {row["name"]: row for row in csv.DictReader(handle)}


def load_relax_cache():
    """Stage 19 per-cell rows, keyed by (name, state, epsilon, arm)."""

    with REL_CACHE.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    cache = {}
    for row in rows:
        key = (row["name"], row["state"], float(row["epsilon"]), row["arm"])
        cache[key] = row
    return cache


def read_xyz_frame(path: Path):
    """Return ``(symbols, coords)`` from an ``.xyz`` file."""

    lines = path.read_text(encoding="utf-8").splitlines()
    count = int(lines[0].split()[0])
    symbols, coords = [], []
    for line in lines[2:2 + count]:
        parts = line.split()
        symbols.append(parts[0])
        coords.append(tuple(float(value) for value in parts[1:4]))
    if count != len(coords):
        raise SystemExit("truncated xyz: %s" % path)
    return symbols, coords


def endpoint_path(arm: str, name: str, state: str, epsilon: float) -> Path:
    stem = "%s_%s_cpcm_%g_%s" % (name, state, epsilon, arm)
    return (REPO_ROOT / "outputs" / "week18" / ARM_DIR[arm] / name /
            (stem + ".xyz"))


def interpolate(symbols_a, coords_a, symbols_b, coords_b, fraction: float):
    """Linear interpolation in Cartesian space at ``fraction`` in [0, 1].

    The two endpoints are relaxed structures of the same molecule with the same atom
    ordering (Stage 19 never reorders: both arms start from the same G1 geometry), so
    atom i of one is atom i of the other and no matching step is needed.
    """

    if symbols_a != symbols_b:
        raise SystemExit("symbol mismatch between endpoints: %s vs %s"
                         % (symbols_a, symbols_b))
    blended = []
    for left, right in zip(coords_a, coords_b):
        blended.append(tuple(a + fraction * (b - a) for a, b in zip(left, right)))
    return symbols_a, blended


def write_xyz(path: Path, symbols, coords, comment: str) -> None:
    body = ["%d" % len(symbols), comment]
    for symbol, xyz in zip(symbols, coords):
        body.append("%-2s %18.10f %18.10f %18.10f" % (symbol, xyz[0], xyz[1], xyz[2]))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(body) + "\n", encoding="utf-8", newline="\n")


def image_label(name: str, state: str, epsilon: float, index: int, images: int) -> str:
    steps = images - 1
    return "%s_%s_cpcm_%g_path%02dof%02d" % (name, state, epsilon, index, steps)
def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Stage 21 Part A: frozen single points along the Stage 19 path.")
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    parser.add_argument("--scratch", type=Path, default=DEFAULT_SCRATCH)
    parser.add_argument("--only", default=None,
                        help="comma-separated name/state/epsilon keys to restrict to")
    parser.add_argument("--images", type=int, default=21,
                        help="number of frames per path, endpoints included")
    parser.add_argument("--nprocs", type=int, default=2)
    parser.add_argument("--jobs", type=int, default=6)
    parser.add_argument("--timeout", type=float, default=3600.0)
    parser.add_argument("--seed", type=lambda value: int(value, 0), default=0xC0FFEE)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--plan-only", action="store_true")
    return parser.parse_args(argv)


def cell_key(cell) -> str:
    return "%s/%s/%g" % (cell["name"], cell["state"], cell["epsilon"])


def selected_cells(args):
    cells = list(CELLS)
    if args.only:
        wanted = {item.strip() for item in args.only.split(",") if item.strip()}
        cells = [cell for cell in cells if cell_key(cell) in wanted]
        if not cells:
            raise SystemExit("--only matched no cell")
    return cells


def build_frames(cell, args, scratch_root: Path):
    """Write every interpolated frame and return the job specs."""

    name, state, epsilon = cell["name"], cell["state"], cell["epsilon"]
    start_dir = endpoint_path("default", name, state, epsilon)
    end_dir = endpoint_path("moread", name, state, epsilon)
    for path in (start_dir, end_dir):
        if not path.exists():
            raise SystemExit("missing Stage 19 endpoint: %s" % path.relative_to(REPO_ROOT))
    symbols_a, coords_a = read_xyz_frame(start_dir)
    symbols_b, coords_b = read_xyz_frame(end_dir)

    frame_dir = scratch_root / "path" / ("%s_%s_cpcm_%g" % (name, state, epsilon))
    specs = []
    steps = args.images - 1
    for index in range(args.images):
        fraction = index / steps if steps else 0.0
        symbols, coords = interpolate(symbols_a, coords_a, symbols_b, coords_b, fraction)
        label = image_label(name, state, epsilon, index, args.images)
        frame = frame_dir / (label + ".xyz")
        write_xyz(frame, symbols, coords,
                  "Stage21 path frame %d/%d lambda=%.4f %s" % (index, steps, fraction, label))
        specs.append({"cell": cell, "index": index, "images": args.images,
                      "fraction": fraction, "label": label, "frame": frame})
    return specs


def run_one(spec, args, core, rel_cache):
    cell = spec["cell"]
    name, state, epsilon = cell["name"], cell["state"], cell["epsilon"]
    meta = core.get(name, {})
    reference = rel_cache.get((name, state, epsilon, "default")) or {}
    common = {
        "mol_id": meta.get("mol_id", ""), "name": name,
        "family": meta.get("family", ""), "role": meta.get("role", ""),
        "smiles": meta.get("smiles", ""), "state": state,
        "charge": int(reference.get("charge", 0)),
        "multiplicity": int(reference.get("multiplicity", 1)),
        "epsilon": epsilon, "image_index": spec["index"],
        "image_total": spec["images"], "lambda": round(spec["fraction"], 6),
        "rmsd_a_stage19": cell["rmsd_a"], "stage19_verdict": cell["stage19_verdict"],
        "geometry_source": SOURCE_LABEL.format(arm="default"),
    }

    mol_dir = args.outdir / "orca_path" / name
    mol_dir.mkdir(parents=True, exist_ok=True)
    stored = mol_dir / (spec["label"] + "_orca.json")

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
                    "seconds": result.get("seconds", ""),
                    "qc_flags": ";".join(cached.get("qc_flags", [])),
                    "error": "", "source": "cached", "cached": True}

    started = time.perf_counter()
    try:
        record = run_orca_job(
            name=spec["label"], smiles=None, xyz=spec["frame"],
            charge=common["charge"], multiplicity=common["multiplicity"],
            job=orca.JOB_SINGLE_POINT, outdir=mol_dir, solvent=None, epsilon=epsilon,
            seed=args.seed, timeout_seconds=args.timeout, nprocs=args.nprocs)
    except Exception as exc:  # noqa: BLE001 - a failed job is a result, not a crash
        return {**common, "status": "execution_failed",
                "seconds": round(time.perf_counter() - started, 2),
                "qc_flags": "single_point_failed", "error": repr(exc),
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
            "seconds": elapsed,
            "qc_flags": ";".join(record.get("qc_flags", [])),
            "error": record.get("error", ""), "source": "computed", "cached": False}


FIELDS = ["mol_id", "name", "family", "role", "smiles", "state", "charge",
          "multiplicity", "epsilon", "image_index", "image_total", "lambda",
          "rmsd_a_stage19", "stage19_verdict", "status", "final_energy_eh",
          "scf_converged", "seconds", "qc_flags", "geometry_source", "source",
          "cached", "error"]


def main(argv=None) -> int:
    args = parse_args(argv)
    for attribute in ("outdir", "scratch"):
        value = getattr(args, attribute)
        setattr(args, attribute, (value if value.is_absolute() else Path.cwd() / value).resolve())
    args.outdir.mkdir(parents=True, exist_ok=True)
    args.scratch.mkdir(parents=True, exist_ok=True)
    if args.images < 2:
        raise SystemExit("--images must be at least 2 (both endpoints)")

    core = load_core_set()
    rel_cache = load_relax_cache()
    cells = selected_cells(args)
    specs = []
    for cell in cells:
        specs.extend(build_frames(cell, args, args.scratch))

    plan = {
        "stage": 21, "part": "A", "job": "frozen single point on the Stage 19 path",
        "method": "r2SCAN-3c", "solvent_layer": "bare CPCM(epsilon of the cell)",
        "images": args.images, "cells": [cell_key(cell) for cell in cells],
        "n_jobs": len(specs), "nprocs": args.nprocs, "jobs": args.jobs,
    }
    (args.outdir / "stage21_path_plan.json").write_text(
        json.dumps(plan, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8", newline="\n")
    if args.plan_only:
        print(json.dumps(plan, indent=2, ensure_ascii=False))
        return 0

    rows = []
    started = time.time()
    with ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool:
        futures = [pool.submit(run_one, spec, args, core, rel_cache) for spec in specs]
        for future in futures:
            row = future.result()
            rows.append(row)
            print("%-28s %2d/%2d %-6s %s" % (row["name"], row["image_index"],
                                              row["image_total"] - 1, row["status"],
                                              row["final_energy_eh"]))

    rows.sort(key=lambda row: (row["name"], row["epsilon"], row["image_index"]))
    with (args.outdir / "stage21_path_cells.csv").open("w", encoding="utf-8",
                                                       newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    ok = sum(1 for row in rows if row["status"] == "ok")
    summary = {
        "stage": 21, "part": "A", "generated_utc": datetime.now(timezone.utc).isoformat(),
        "method": "r2SCAN-3c", "images": args.images,
        "n_jobs": len(rows), "n_ok": ok, "n_failed": len(rows) - ok,
        "wall_seconds": round(time.time() - started, 2),
        "n_scf_converged": sum(1 for row in rows if row["scf_converged"] is True),
        "cells": ["%s/%s/%g" % (row["name"], row["state"], row["epsilon"])
                  for row in rows[::args.images]],
    }
    (args.outdir / "stage21_path.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8", newline="\n")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if ok == len(rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())