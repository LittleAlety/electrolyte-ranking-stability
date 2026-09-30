"""Stage 20 (week 19), part 2 -- does the second SCF solution survive a *cheap* relaxation?

Motivation
----------
Week 18 (Stage 19) took the 37 ``moread_lower`` cells of the week-17 census -- cells where
ORCA's default SCF guess and a restarted guess (``! MORead``) settle on two different
electronic solutions -- and relaxed *both* arms at r2SCAN-3c/CPCM(epsilon).  Its headline
was that geometry mostly kills the single-point *energy* preference (32/37 flips) while
29/37 endpoints still look like two different electronic states.

All of that answers the question at the *expensive* level of theory.  Practical screening
does not run r2SCAN-3c on every candidate; it runs GFN2-xTB.  This stage asks the cheap
version of the same question, starting from the expensive geometries:

    Take the two r2SCAN-3c relaxed endpoints of a cell, give each one a frozen GFN2-xTB
    relaxation, and ask whether the cheap potential-energy surface still separates them.

Protocol (everything frozen except the method)
----------------------------------------------
* start geometry: the Stage-19 r2SCAN-3c ``Opt`` endpoint of the matching arm, copied
  verbatim into the job directory (one file per arm per cell);
* per arm: one frozen GFN2-xTB single point on that start geometry (the cheap *reading*),
  then one frozen GFN2-xTB ``--opt`` (the cheap *relaxation*);
* no solvent model and no charge change: the cell's own ``charge`` / ``multiplicity`` are
  read from the Stage-19 ledger row, never inferred from the state name.

Determinism and scratch
-----------------------
:func:`electrolyte_ranking.xtb.run_xtb` pins ``OMP_NUM_THREADS=1`` and clears the xTB
scratch files before every call, so a re-run reproduces the same minimum.  xTB writes its
scratch into the current directory, so each job gets its own directory and the start
geometry is copied into it first.

This module only *runs* the jobs and records them; the verdict table lives in
``scripts/analyze_stage20_xtb_arms.py``.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from electrolyte_ranking import toolchain, xtb  # noqa: E402

WEEK18 = REPO_ROOT / "outputs" / "week18"
DEFAULT_OUTDIR = REPO_ROOT / "outputs" / "week19"
DEFAULT_WORKDIR = DEFAULT_OUTDIR / "xtb_relax"
CELLS_CSV = WEEK18 / "stage19_relax_cells.csv"
CORE_SET = REPO_ROOT / "data" / "metadata" / "core_set.csv"

ARMS = ("default", "moread")
SOURCE_LABEL = ("outputs/week18/orca_relax_<arm>/<name>/<name>_<state>_cpcm_<eps>_<arm>.xyz"
                " (the Stage-19 r2SCAN-3c Opt endpoint of that arm)")

#: xTB's own geometry-convergence marker.  ``normal termination of xtb`` is printed even
#: when the optimiser stops short, so the two are recorded as separate columns.
OPT_CONVERGED_MARKER = "GEOMETRY OPTIMIZATION CONVERGED"
OPT_FAILED_MARKER = "GEOMETRY OPTIMIZATION DID NOT CONVERGE"

_GRADIENT_NORM = re.compile(r"GRADIENT NORM\s+([-+]?\d+(?:\.\d+)?(?:[EeDd][-+]?\d+)?)")


def parse_gradient_norm(text):
    """The last ``GRADIENT NORM <x> Eh/alpha`` xTB prints, or ``None``."""

    matches = _GRADIENT_NORM.findall(text or "")
    if not matches:
        return None
    return float(matches[-1].replace("D", "E").replace("d", "e"))


def detect_opt_converged(text):
    """``True`` / ``False`` / ``None`` for xTB's geometry-convergence marker."""

    if not text:
        return None
    if OPT_FAILED_MARKER in text:
        return False
    if OPT_CONVERGED_MARKER in text:
        return True
    return None


def load_core_set():
    """mol_id / family / role / smiles for every core-set molecule."""

    with CORE_SET.open(encoding="utf-8", newline="") as handle:
        return {row["name"]: row for row in csv.DictReader(handle)}


def load_cells(cells_csv=CELLS_CSV):
    """The 37 target cells of the Stage-19 ledger, charge-resolved per row.

    The charge and multiplicity are read from the ledger instead of being derived from
    the state name: an anion is ``-1 / 2`` and a cation is ``+1 / 2`` *today*, but the
    ledger is the authority and a hard-coded table would silently disagree after any
    change to the census.
    """

    with Path(cells_csv).open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise SystemExit("no rows in %s" % cells_csv)
    cells = {}
    for row in rows:
        key = (row["name"], row["state"], round(float(row["epsilon"]), 6))
        entry = cells.setdefault(key, {
            "name": row["name"], "state": row["state"],
            "epsilon": float(row["epsilon"]), "arm_set": row["census_arm_set"],
            "charges": set(), "arms": set(),
        })
        entry["charges"].add((int(row["charge"]), int(row["multiplicity"])))
        entry["arms"].add(row["arm"])
    for key, entry in cells.items():
        if len(entry["charges"]) != 1:
            raise SystemExit("inconsistent charge/multiplicity for %s: %s"
                             % (key, sorted(entry["charges"])))
        if set(entry["arms"]) != set(ARMS):
            raise SystemExit("cell %s has arms %s, expected %s"
                             % (key, sorted(entry["arms"]), list(ARMS)))
        entry["charge"], entry["multiplicity"] = entry.pop("charges").pop()
        entry.pop("arms")
    return [cells[key] for key in sorted(cells)]


def geom_path(name, state, epsilon, arm, week18=WEEK18):
    """The Stage-19 relaxed ``.xyz`` of one arm of one cell."""

    return (Path(week18) / ("orca_relax_" + arm) / name
            / ("%s_%s_cpcm_%g_%s.xyz" % (name, state, float(epsilon), arm)))


def cell_label(name, state, epsilon, arm):
    return "%s_%s_cpcm_%g_%s" % (name, state, float(epsilon), arm)


def read_xyz(path):
    """An ``.xyz`` file -> the atom rows as strings, comment line dropped."""

    lines = Path(path).read_text(encoding="utf-8").splitlines()
    count = int(lines[0].strip())
    body = lines[2:2 + count]
    if len(body) != count:
        raise ValueError("%s declares %d atoms but carries %d rows"
                         % (path, count, len(body)))
    return [line.strip() for line in body]


def build_specs(cells, wanted_arms, week18=WEEK18):
    """One spec per (cell, arm) with its frozen start geometry resolved on disk."""

    specs = []
    for cell in cells:
        for arm in wanted_arms:
            path = geom_path(cell["name"], cell["state"], cell["epsilon"], arm, week18)
            if not path.exists():
                raise SystemExit("missing Stage-19 relaxed geometry: %s" % path)
            specs.append({**cell, "arm": arm, "start": path,
                          "label": cell_label(cell["name"], cell["state"],
                                              cell["epsilon"], arm)})
    return specs

def build_plan(cells, specs, wanted_arms, exe, version):
    """The pre-run declaration: what will be run, from where, with what settings."""

    return {
        "stage": 20,
        "part": "part 2 -- does the second solution survive a cheap (GFN2-xTB) relaxation?",
        "engine": "xtb",
        "engine_path": str(exe),
        "engine_version": version,
        "gfn": xtb.FROZEN_GFN,
        "method": "GFN2-xTB",
        "job_types": [xtb.JOB_SINGLE_POINT, xtb.JOB_OPTIMIZE],
        "job_note": ("one frozen single point on the start geometry (the cheap reading), "
                     "then one frozen --opt (the cheap relaxation)"),
        "start_geometry": SOURCE_LABEL,
        "source_ledger": "outputs/week18/stage19_relax_cells.csv",
        "molecules": sorted({cell["name"] for cell in cells}),
        "states": sorted({cell["state"] for cell in cells}),
        "epsilons": sorted({cell["epsilon"] for cell in cells}),
        "arm_sets": sorted({cell["arm_set"] for cell in cells}),
        "arms": list(wanted_arms),
        "n_target_cells": len(cells),
        "n_jobs": len(specs),
        "determinism": {"OMP_NUM_THREADS": xtb.DETERMINISTIC_THREADS,
                        "scratch": "cleared before every call (xtb.clear_scratch)"},
        "cells": ["%s/%s/%g" % (cell["name"], cell["state"], cell["epsilon"])
                  for cell in cells],
    }


CELL_COLUMNS = (
    "mol_id", "name", "family", "role", "state", "charge", "multiplicity",
    "epsilon", "arm_set", "arm", "label", "status",
    "start_geometry", "input_geometry", "relaxed_geometry", "n_atoms",
    "start_energy_eh", "start_homo_ev", "start_lumo_ev", "start_hl_gap_ev",
    "relax_energy_eh", "relax_homo_ev", "relax_lumo_ev", "relax_hl_gap_ev",
    "relax_gradient_norm_eh_bohr", "opt_converged", "scf_converged",
    "normal_termination", "qc_flags", "seconds", "seconds_sp", "seconds_opt",
    "xtb_version", "source", "cached", "error",
)


def display(path):
    """Repo-relative POSIX-ish path for anything under the repository root."""

    try:
        return str(Path(path).relative_to(REPO_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def cached_ok(cached, relaxed_path):
    """A cache hit needs a converged record *and* the relaxed geometry still on disk."""

    if not isinstance(cached, dict):
        return False
    record = cached.get("record") or {}
    if cached.get("status") != "ok" or record.get("status") != "ok":
        return False
    for key in ("start_energy_eh", "relax_energy_eh"):
        if not isinstance(record.get(key), (int, float)):
            return False
    return Path(relaxed_path).exists()


def run_one(spec, args, core, exe, version):
    name, state, arm = spec["name"], spec["state"], spec["arm"]
    epsilon = float(spec["epsilon"])
    meta = core.get(name, {})
    label = spec["label"]
    job_dir = args.workdir / label
    job_dir.mkdir(parents=True, exist_ok=True)
    stored = job_dir / (label + "_xtb.json")
    relaxed_path = job_dir / (label + "_relaxed.xyz")

    common = {
        "mol_id": meta.get("mol_id", ""), "name": name,
        "family": meta.get("family", ""), "role": meta.get("role", ""),
        "state": state, "charge": spec["charge"], "multiplicity": spec["multiplicity"],
        "epsilon": epsilon, "arm_set": spec["arm_set"], "arm": arm, "label": label,
        "start_geometry": display(spec["start"]),
        "input_geometry": display(job_dir / (label + ".xyz")),
        "relaxed_geometry": display(relaxed_path),
        "xtb_version": version or "", "error": "",
    }

    if stored.exists() and not args.force:
        try:
            cached = json.loads(stored.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            cached = None
        if cached_ok(cached, relaxed_path):
            return {**common, **(cached.get("record") or {}),
                    "source": "cached", "cached": True}

    input_xyz = job_dir / (label + ".xyz")
    shutil.copyfile(spec["start"], input_xyz)

    started = time.perf_counter()
    try:
        sp = xtb.run_xtb(
            exe, xtb.JOB_SINGLE_POINT, input_name=input_xyz.name,
            charge=spec["charge"], multiplicity=spec["multiplicity"], cwd=job_dir,
            timeout_seconds=args.timeout, required=())
        sp_seconds = time.perf_counter() - started
        (job_dir / "sp.out").write_text(sp.raw_output, encoding="utf-8", newline="\n")
        opt_started = time.perf_counter()
        opt = xtb.run_xtb(
            exe, xtb.JOB_OPTIMIZE, input_name=input_xyz.name,
            charge=spec["charge"], multiplicity=spec["multiplicity"], cwd=job_dir,
            timeout_seconds=args.timeout, required=())
        opt_seconds = time.perf_counter() - opt_started
        (job_dir / "opt.out").write_text(opt.raw_output, encoding="utf-8", newline="\n")
    except Exception as exc:  # noqa: BLE001 - a failed job is a result, not a crash
        return {**common, "status": "execution_failed", "qc_flags": "geometry_failed",
                "n_atoms": "", "seconds": round(time.perf_counter() - started, 2),
                "error": repr(exc), "source": "computed", "cached": False}

    xtbopt = job_dir / "xtbopt.xyz"
    if xtbopt.exists():
        shutil.copyfile(xtbopt, relaxed_path)

    opt_converged = detect_opt_converged(opt.raw_output)
    if sp.total_energy_eh is None or opt.total_energy_eh is None:
        status = "missing_energy"
    elif opt_converged is not True:
        status = "not_converged"
    else:
        status = "ok"

    flags = sorted(set(opt.qc_flags) | set(sp.qc_flags))
    row = {
        **common,
        "n_atoms": len(read_xyz(input_xyz)),
        "start_energy_eh": sp.total_energy_eh,
        "start_homo_ev": sp.homo_ev, "start_lumo_ev": sp.lumo_ev,
        "start_hl_gap_ev": sp.hl_gap_ev,
        "relax_energy_eh": opt.total_energy_eh,
        "relax_homo_ev": opt.homo_ev, "relax_lumo_ev": opt.lumo_ev,
        "relax_hl_gap_ev": opt.hl_gap_ev,
        "relax_gradient_norm_eh_bohr": parse_gradient_norm(opt.raw_output),
        "opt_converged": opt_converged,
        "scf_converged": bool(opt.scf_converged and sp.scf_converged),
        "normal_termination": bool(opt.normal_termination and sp.normal_termination),
        "qc_flags": ";".join(flags), "status": status,
        "seconds": round(sp_seconds + opt_seconds, 2),
        "seconds_sp": round(sp_seconds, 2), "seconds_opt": round(opt_seconds, 2),
        "source": "computed", "cached": False,
    }
    stored.write_text(
        json.dumps({"label": label, "status": status, "qc_flags": flags, "record": row},
                   ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8", newline="\n")
    return row


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Stage 20 part 2: GFN2-xTB relaxation of both Stage-19 endpoints.")
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    parser.add_argument("--workdir", type=Path, default=None)
    parser.add_argument("--cells-csv", type=Path, default=CELLS_CSV)
    parser.add_argument("--only", default=None,
                        help="comma-separated name/state/epsilon (or full job label) keys")
    parser.add_argument("--arms", default="default,moread")
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--timeout", type=float, default=1800.0)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--plan-only", action="store_true")
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    args.outdir = (args.outdir if args.outdir.is_absolute()
                   else Path.cwd() / args.outdir).resolve()
    workdir = args.workdir if args.workdir is not None else args.outdir / "xtb_relax"
    args.workdir = (workdir if workdir.is_absolute() else Path.cwd() / workdir).resolve()
    args.outdir.mkdir(parents=True, exist_ok=True)
    args.workdir.mkdir(parents=True, exist_ok=True)

    core = load_core_set()
    cells = load_cells(args.cells_csv)

    wanted_arms = [item.strip() for item in args.arms.split(",") if item.strip()]
    unknown = [arm for arm in wanted_arms if arm not in ARMS]
    if unknown:
        raise SystemExit("unknown arms: %s (known: %s)" % (unknown, list(ARMS)))

    specs = build_specs(cells, wanted_arms, week18=Path(args.cells_csv).parent)
    if args.only:
        wanted = {item.strip() for item in args.only.split(",") if item.strip()}
        keep = []
        for spec in specs:
            key = "%s/%s/%g" % (spec["name"], spec["state"], spec["epsilon"])
            if key in wanted or spec["label"] in wanted:
                keep.append(spec)
        if not keep:
            raise SystemExit("--only matched none of the %d candidate jobs" % len(specs))
        specs = keep

    located = toolchain.find_executable("xtb")
    if located is None:
        raise SystemExit("xtb not found; set ELECTROLYTE_XTB or drop it under .toolchain/xtb/")
    version = toolchain.read_version(located.path, "xtb")

    plan = build_plan(cells, specs, wanted_arms, located.path, version)
    (args.outdir / "stage20_xtb_arms_plan.json").write_text(
        json.dumps(plan, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8", newline="\n")
    if args.plan_only:
        print("plan: %d cells x %d arms = %d jobs (GFN2-xTB %s on %d molecules x %d states)"
              % (len(cells), len(wanted_arms), len(specs), version or "?",
                 len(plan["molecules"]), len(plan["states"])))
        return 0

    print("running %d GFN2-xTB jobs (%d concurrent, xtb %s) over %d target cells"
          % (len(specs), max(1, args.jobs), version or "?", len(cells)))

    records = []
    with ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool:
        futures = [pool.submit(run_one, spec, args, core, located.path, version)
                   for spec in specs]
        for position, future in enumerate(futures, start=1):
            record = future.result()
            records.append(record)
            if record.get("source") == "computed":
                seconds = record.get("seconds")
                print("  [%d/%d] %-30s %-11s %-7s %s"
                      % (position, len(specs), record["label"], record["status"],
                         "" if not isinstance(seconds, (int, float)) else "%.1fs" % seconds,
                         record.get("error", "")))

    table = args.outdir / "stage20_xtb_arms_cells.csv"
    with table.open("w", encoding="utf-8", newline="\n") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(CELL_COLUMNS), extrasaction="ignore")
        writer.writeheader()
        for record in records:
            writer.writerow(record)

    ok = [record for record in records if record["status"] == "ok"]
    seconds = [record["seconds"] for record in ok
               if isinstance(record.get("seconds"), (int, float))]
    summary = {
        "stage": 20, "part": 2, "engine": "xtb", "engine_version": version,
        "gfn": xtb.FROZEN_GFN, "job_types": [xtb.JOB_SINGLE_POINT, xtb.JOB_OPTIMIZE],
        "n_target_cells": len(cells), "n_jobs": len(records), "n_ok": len(ok),
        "n_failed": len(records) - len(ok),
        "n_reused": sum(1 for record in records if record.get("cached")),
        "n_computed": sum(1 for record in records if record.get("source") == "computed"),
        "jobs": max(1, args.jobs),
        "wall_clock_seconds_median": (round(statistics.median(seconds), 2)
                                      if seconds else None),
        "output_csv": display(table),
        "generated_utc": datetime.now(timezone.utc).isoformat(),
    }
    (args.outdir / "stage20_xtb_arms.json").write_text(
        json.dumps({**plan, "summary": summary, "n_ok": len(ok),
                    "n_failed": len(records) - len(ok), "jobs": max(1, args.jobs),
                    "layers": [summary]}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8", newline="\n")

    print("%d/%d jobs ok (%d cached, %d computed), median %ss"
          % (len(ok), len(records), summary["n_reused"], summary["n_computed"],
             summary["wall_clock_seconds_median"]))
    print("wrote %s" % display(table))
    return 0 if summary["n_failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())