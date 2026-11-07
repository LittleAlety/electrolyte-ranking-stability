#!/usr/bin/env python
"""Stage 9 / T10 step 2 -- r2SCAN-3c refinement of the [Li(M)2]+ shells.

This is the DFT half of the explicit-microsolvation validation.  It takes the
GFN2-xTB pre-optimised shells of ``scripts/build_microsolvation_shells.py`` and
measures the same three electronic states Week 5 measured for the 1:1 complex,
with the same frozen arm (r2SCAN-3c, gas phase, identical seeds):

    [Li(M)2]+   charge +1, singlet   -- the C1(1:2) reference state
    [Li(M)2]2+  charge +2, doublet   -- C1(1:2) oxidised
    [Li(M)2]0   charge  0, doublet   -- C1(1:2) reduced

The vertical ionisation energy and electron affinity are taken at the
r2SCAN-3c Opt of the reference state so that the only change with respect to
``outputs/week5/c1_coord_shifts.csv`` is the size of the first solvation shell,
not the method, the basis set or the redox-state relaxation convention.  With
``--relax`` the oxidised and reduced states are additionally re-relaxed, so the
relaxation energy can be separated from the shell effect exactly as it was for
1:1.

Failures are results: a failed SCF, a failed Opt or an abnormal termination is
written to the CSV with its QC flag and never dropped.

Outputs
-------
``outputs/week8/stage9_jobs.csv``         one row per (shell, state, job)
``outputs/week8/stage9_summary.json``     run record (counts, timing, version)
``outputs/week8/shells/<NAME>_<motif>/``  raw ORCA inputs, outputs, records
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from electrolyte_ranking import orca, toolchain  # noqa: E402
from build_li_motifs import heavy_graph, parent_bonds_intact, read_xyz, write_xyz  # noqa: E402
from build_microsolvation_shells import ligand_bonds_intact  # noqa: E402
from run_orca_job import run_job as run_orca_job  # noqa: E402
from run_t2_opt_freq import final_geometry  # noqa: E402

DEFAULT_OUTDIR = REPO_ROOT / "outputs" / "week8"
SHELL_JSON = REPO_ROOT / "outputs" / "week8" / "ms_shell_generation.json"
STRUCTDIR = REPO_ROOT / "structures" / "microsolvation"
CORE_SET = REPO_ROOT / "data" / "metadata" / "core_set.csv"

#: (label, charge, multiplicity) of the three electronic states.
STATES = (
    ("cation", 1, 1),
    ("dication", 2, 2),
    ("reduced", 0, 2),
)

#: The state the shell geometry is optimised in; everything else is measured on it.
REFERENCE_STATE = "cation"

CONTACT_CUTOFF = 3.0

COLUMNS = [
    "mol_id",
    "name",
    "family",
    "motif_id",
    "state",
    "charge",
    "multiplicity",
    "job",
    "continuum",
    "status",
    "final_energy_eh",
    "scf_converged",
    "n_scf_cycles",
    "terminated_normally",
    "imaginary_modes",
    "seconds",
    "nprocs",
    "qc_flags",
    "geometry_path",
    "li_contacts",
    "li_min_distance_a",
    "anchor_bonds_intact",
    "second_ligand_intact",
    "error",
    "cached",
]


def relative(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def out_text(target: Path, stem: str):
    path = target / (stem + ".out")
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8", errors="replace")


def load_shells(path: Path = SHELL_JSON) -> list:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return list(payload["shells"])


def load_core_set() -> dict:
    with CORE_SET.open(encoding="utf-8", newline="") as handle:
        return {row["name"]: row for row in csv.DictReader(handle)}


def shell_geometry_path(shell) -> Path:
    return STRUCTDIR / ("%s_%s_shell2.xyz" % (shell["name"], shell["motif_id"]))


def reference_geometry_target(shell, args) -> Path:
    return Path(args.outdir) / "shells" / (
        "%s_%s" % (shell["name"], shell["motif_id"])
    ) / ("%s_%s_shell2_G2Li2.xyz" % (shell["name"], shell["motif_id"]))


def job_stem(shell, state, job) -> str:
    return "%s_%s_shell2_%s_%s" % (shell["name"], shell["motif_id"], state, job)


def is_reference_job(item) -> bool:
    shell, state, charge, multiplicity, job = item
    return state == REFERENCE_STATE and job == orca.JOB_OPTIMIZE


def planned_jobs(shells, args) -> list:
    plan = []
    for shell in shells:
        plan.append((shell, "cation", 1, 1, orca.JOB_OPTIMIZE))
        for state, charge, multiplicity in STATES[1:]:
            plan.append((shell, state, charge, multiplicity, orca.JOB_SINGLE_POINT))
        if not args.skip_relax:
            for state, charge, multiplicity in STATES[1:]:
                plan.append((shell, state, charge, multiplicity, orca.JOB_OPTIMIZE))
    return plan


def geometry_qc(symbols, coords, n_anchor, donors) -> dict:
    """Li contacts and bond integrity, with Li at index ``n_anchor - 1``."""

    li = coords[n_anchor - 1]
    contacts = []
    for index, symbol in enumerate(symbols):
        if index == n_anchor - 1 or symbol not in ("O", "N", "S", "P"):
            continue
        distance = float(np.linalg.norm(coords[index] - li))
        if distance <= CONTACT_CUTOFF:
            contacts.append((index, symbol, distance))
    contacts.sort(key=lambda item: item[2])
    return {
        "li_contacts": ";".join("%d:%s:%.3f" % item for item in contacts),
        "li_min_distance_a": round(contacts[0][2], 4) if contacts else None,
        "anchor_bonds_intact": None,
        "second_ligand_intact": None,
    }

def build_context(shells, core) -> dict:
    context = {}
    for shell in shells:
        symbols, _ = read_xyz(shell_geometry_path(shell))
        n_anchor = (len(symbols) + 1) // 2
        if symbols[n_anchor - 1] != "Li":
            raise RuntimeError(
                "shell geometry does not have Li at index %d: %s"
                % (n_anchor - 1, shell_geometry_path(shell))
            )
        _, neighbours = heavy_graph(core[shell["name"]]["smiles"])
        context[(shell["name"], shell["motif_id"])] = (symbols, neighbours, n_anchor)
    return context


def execute(item, args, context) -> dict:
    shell, state, charge, multiplicity, job = item
    stem = job_stem(shell, state, job)
    target = Path(args.outdir) / "shells" / ("%s_%s" % (shell["name"], shell["motif_id"]))
    target.mkdir(parents=True, exist_ok=True)
    record_path = target / (stem + "_stage9_record.json")
    symbols, neighbours, n_anchor = context[(shell["name"], shell["motif_id"])]

    if is_reference_job(item):
        geometry = shell_geometry_path(shell)
    else:
        geometry = reference_geometry_target(shell, args)
        if not geometry.exists():
            return {
                "mol_id": shell["mol_id"],
                "name": shell["name"],
                "family": shell["family"],
                "motif_id": shell["motif_id"],
                "state": state,
                "charge": charge,
                "multiplicity": multiplicity,
                "job": job,
                "continuum": "gas",
                "status": "skipped_no_reference_geometry",
                "final_energy_eh": None,
                "scf_converged": None,
                "n_scf_cycles": None,
                "terminated_normally": None,
                "imaginary_modes": None,
                "seconds": 0.0,
                "nprocs": None,
                "qc_flags": "geometry_failed",
                "geometry_path": relative(geometry),
                "li_contacts": "",
                "li_min_distance_a": None,
                "anchor_bonds_intact": None,
                "second_ligand_intact": None,
                "error": "the [Li(M)2]+ Opt of this shell produced no geometry",
                "cached": False,
            }

    if not args.force and record_path.exists():
        try:
            cached = json.loads(record_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            cached = None
        if cached is not None and cached.get("status") == "ok":
            cached["cached"] = True
            return cached

    started = time.perf_counter()
    common = {
        "mol_id": shell["mol_id"],
        "name": shell["name"],
        "family": shell["family"],
        "motif_id": shell["motif_id"],
        "state": state,
        "charge": charge,
        "multiplicity": multiplicity,
        "job": job,
        "continuum": "gas",
        "geometry_path": relative(geometry),
    }
    try:
        record = run_orca_job(
            name=stem,
            smiles=None,
            xyz=geometry,
            charge=charge,
            multiplicity=multiplicity,
            job=job,
            outdir=target,
            solvent=None,
            seed=0xC0FFEE,
            timeout_seconds=args.timeout,
            nprocs=args.nprocs,
            dry_run=args.dry_run,
        )
    except Exception as exc:  # noqa: BLE001 - a failed job is a result
        return {
            **common,
            "status": "execution_failed",
            "final_energy_eh": None,
            "scf_converged": None,
            "n_scf_cycles": None,
            "terminated_normally": None,
            "imaginary_modes": None,
            "seconds": round(time.perf_counter() - started, 2),
            "nprocs": args.nprocs,
            "qc_flags": "scf_failed" if job == orca.JOB_SINGLE_POINT else "geometry_failed",
            "li_contacts": "",
            "li_min_distance_a": None,
            "anchor_bonds_intact": None,
            "second_ligand_intact": None,
            "error": repr(exc),
            "cached": False,
        }

    elapsed = round(time.perf_counter() - started, 2)
    result = record.get("result") or {}
    text = None if args.dry_run else out_text(target, stem)
    flags = list(record.get("qc_flags") or [])

    relaxed = None
    if job in (orca.JOB_OPTIMIZE, orca.JOB_OPTIMIZE_FREQUENCY) and text is not None:
        block = final_geometry(text)
        if block is not None:
            relaxed = np.asarray(
                [[float(value) for value in line.split()[1:4]] for line in block.splitlines()]
            )
    if relaxed is None:
        relaxed = read_xyz(geometry)[1]

    qc = geometry_qc(symbols, relaxed, n_anchor, None)
    qc["anchor_bonds_intact"] = parent_bonds_intact(
        symbols[: n_anchor - 1], neighbours, relaxed[: n_anchor - 1]
    )
    qc["second_ligand_intact"] = ligand_bonds_intact(
        symbols[n_anchor:], neighbours, relaxed[n_anchor:]
    )
    if not qc["anchor_bonds_intact"] or not qc["second_ligand_intact"]:
        flags.append("dissociated_optimized_product")
    if not qc["li_contacts"]:
        flags.append("no_intact_minimum_found")

    if is_reference_job(item):
        write_xyz(
            reference_geometry_target(shell, args),
            symbols,
            relaxed,
            "%s %s [Li(M)2]+ G2_Li2 r2SCAN-3c %s"
            % (shell["mol_id"], shell["name"], job),
        )

    payload = {
        **common,
        "status": "ok" if record.get("status") == "ok" else record.get("status", "missing_output"),
        "final_energy_eh": result.get("final_energy_eh"),
        "scf_converged": result.get("scf_converged"),
        "n_scf_cycles": result.get("n_scf_cycles"),
        "terminated_normally": result.get("terminated_normally"),
        "imaginary_modes": result.get("imaginary_modes"),
        "seconds": elapsed,
        "nprocs": record.get("nprocs"),
        "qc_flags": ";".join(sorted(set(flags))),
        **qc,
        "error": record.get("error", ""),
        "cached": False,
    }
    record_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + chr(10),
        encoding="utf-8",
        newline=chr(10),
    )
    return payload

def run_phase(plan, args, context) -> list:
    if not plan:
        return []
    records = []
    with ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool:
        for record in pool.map(lambda item: execute(item, args, context), plan):
            print(
                "  %-20s %-9s %-4s %8.2fs  %s"
                % (
                    record["name"] + "/" + record["motif_id"],
                    record["state"],
                    record["job"],
                    record["seconds"] or 0.0,
                    record["status"],
                ),
                flush=True,
            )
            records.append(record)
    return records


def write_csv(path: Path, records) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        for record in records:
            writer.writerow({column: record.get(column, "") for column in COLUMNS})
    return path


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Stage 9 / T10 step 2: r2SCAN-3c [Li(M)2]+ shell sweep."
    )
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    parser.add_argument("--shells", type=Path, default=SHELL_JSON)
    parser.add_argument("--only", default=None, help="comma-separated name allow-list")
    parser.add_argument("--jobs", type=int, default=2, help="concurrent ORCA processes")
    parser.add_argument("--nprocs", type=int, default=8)
    parser.add_argument("--timeout", type=float, default=3600.0)
    parser.add_argument("--skip-relax", action="store_true",
                        help="skip the oxidised/reduced state Opt jobs")
    parser.add_argument("--rebuild-csv", action="store_true",
                        help="no ORCA: rebuild the CSV from records already on disk")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args(argv)


def rebuild_records(plan, args) -> list:
    records = []
    for item in plan:
        shell, state, charge, multiplicity, job = item
        stem = job_stem(shell, state, job)
        path = Path(args.outdir) / "shells" / (
            "%s_%s" % (shell["name"], shell["motif_id"])
        ) / (stem + "_stage9_record.json")
        if path.exists():
            record = json.loads(path.read_text(encoding="utf-8"))
            record["cached"] = True
            records.append(record)
    return records


def main(argv=None) -> int:
    args = parse_args(argv)
    shells = load_shells(Path(args.shells))
    if args.only:
        wanted = {token.strip() for token in args.only.split(",") if token.strip()}
        shells = [
            shell
            for shell in shells
            if shell["mol_id"] in wanted or shell["name"] in wanted
        ]
    if not shells:
        raise SystemExit("no shells selected; run scripts/build_microsolvation_shells.py first")

    located = toolchain.find_executable("orca")
    if located is None and not args.dry_run:
        raise SystemExit("ORCA not found; see docs/07_orca_setup_and_runner.md")
    version = None if located is None else toolchain.read_version(located.path, "orca")

    core = load_core_set()
    context = build_context(shells, core)
    plan = planned_jobs(shells, args)
    started = time.perf_counter()
    if args.rebuild_csv:
        records = rebuild_records(plan, args)
    else:
        records = run_phase([item for item in plan if is_reference_job(item)], args, context)
        records += run_phase([item for item in plan if not is_reference_job(item)], args, context)
    elapsed = time.perf_counter() - started

    csv_path = write_csv(Path(args.outdir) / "stage9_jobs.csv", records)
    status_counts = {}
    flag_counts = {}
    for record in records:
        status_counts[record["status"]] = status_counts.get(record["status"], 0) + 1
        for flag in (record["qc_flags"] or "").split(";"):
            if flag:
                flag_counts[flag] = flag_counts.get(flag, 0) + 1
    summary = {
        "stage": "T10-step2-explicit-microsolvation-dft",
        "method": "r2SCAN-3c",
        "orca_version": version,
        "states": [list(state) for state in STATES],
        "shells": ["%s/%s" % (shell["name"], shell["motif_id"]) for shell in shells],
        "n_shells": len(shells),
        "n_jobs": len(records),
        "n_ok": sum(1 for record in records if record["status"] == "ok"),
        "status_counts": status_counts,
        "qc_flag_counts": flag_counts,
        "jobs_by_kind": {
            kind: sum(
                1
                for record in records
                if (record["job"] + "|" + record["continuum"]) == kind
            )
            for kind in ("opt|gas", "sp|gas")
        },
        "seconds": round(elapsed, 2),
        "sum_job_seconds": round(sum(record["seconds"] or 0.0 for record in records), 2),
        "command": "scripts/run_stage9_microsolvation.py " + " ".join(sys.argv[1:]),
        "csv": relative(csv_path),
    }
    json_path = Path(args.outdir) / "stage9_summary.json"
    json_path.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + chr(10),
        encoding="utf-8",
        newline=chr(10),
    )
    print(json.dumps(summary, ensure_ascii=False)[:600])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())